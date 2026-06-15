"""
Sprint 90-BE (FEAT-TAGGING-COVERAGE-ZEROTAP-DRILLDOWN-20260610)
태깅 커버리지 / 0초탭 드릴다운 — AXIS-VIEW `종료 누락 분석` 페이지 TaggingCoverageCard 실데이터.

  GET /api/ct/tagging-coverage?from=&to=   (read-only, migration 0)

설계서: AGENT_TEAM_LAUNCH.md § Sprint 90-BE (Codex 4라운드 GO, M=3→2→1→0).

핵심 정의 (Codex 합의):
  - 분모 _COVERAGE_WHERE = 완료 + active_time NOT NULL + applicable + force_closed=FALSE,
    TEST/TMS모듈 제외. duration_source 필터 미적용 → 자동마감·admin대행 = 분모 포함(미추적 카운트).
    (사용자 결정 2026-06-10: mock "PI/QI/SI 고 미추적" 신호 재현. CT _CLEAN_WHERE 와 다른 모집단.)
  - 3분류 우선순위 oneClick > zero_tap > tracked (R3 M-3):
      oneClick = task_id IN whitelist (close_reason·active 무관 우선)
      instant(진짜 0초탭) = NOT oneClick AND close_reason IS NULL AND active≤1 (FIX-ZEROTAP 20260615)
      zero_tap(DEPRECATED) = NOT oneClick AND (active≤1 OR close_reason) — 자동마감 포함·과대
      tracked  = NOT oneClick AND active_time_minutes > 1 AND close_reason IS NULL
    → close_reason IS NOT NULL ⟺ 자동마감/admin·ship 대행 (정상완료=close_reason NULL,
      task_service.py L819 / force_closed=FALSE 모집단, Codex R4 전수 검증).
  - DUAL L/R = per-row 단위 (각 -L/-R 행 독립 카운트). well_tracked = serial별 tracked행/전체행 >= 0.8.
  - partners share = largest-remainder(정수 기반) → Σ=100 보장 + 결정적 tie-break.
"""
from __future__ import annotations

import logging
import time
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import psycopg2.extras

from app.db_pool import put_conn
from app.models.worker import get_db_connection
from app.services.statistics_service import (
    CtParamError,
    CT_TRUST_START_MONTH,
    _INSTANT_WHITELIST,
    _resolve_window,
    _TASK_NAME,
    _TUKEY_MIN_N,
    is_instant_whitelisted,
)

logger = logging.getLogger(__name__)
_KST = ZoneInfo("Asia/Seoul")

_PROCESS_ORDER = ["MECH", "ELEC", "PI", "QI", "SI"]
_WELL_TRACKED_THRESHOLD = 0.8  # 추적율 ≥ 80% serial = "잘 잡힌 제품"

# whitelist SQL = is_instant_whitelisted 단일 정의(_INSTANT_WHITELIST frozenset) 미러.
#   programmatic 생성 → SQL/Python 동기화 보장 (수기 나열 drift 차단).
_WHITELIST_SQL = "(" + ",".join("'%s'" % t for t in sorted(_INSTANT_WHITELIST)) + ")"

# 분모 — 완료된 applicable task 전수, force_closed/TEST/TMS모듈만 제외.
#   %% = psycopg2 리터럴 % (LIKE). alias td=app_task_details, p=plan.product_info.
# #92: 윈도우 분리 — _COVERAGE_BASE(윈도우 없음) + 윈도우 조각. _COVERAGE_WHERE 값 불변(아래 합성)
#   → reliability-summary(v2.41.0)가 import 하는 _COVERAGE_WHERE 문자열 동일 = 회귀 0.
_COVERAGE_BASE = (
    "td.completed_at IS NOT NULL "
    "AND td.active_time_minutes IS NOT NULL "
    "AND COALESCE(td.force_closed, FALSE) = FALSE "
    "AND td.is_applicable = TRUE "
    "AND td.task_id NOT IN ('TANK_MODULE','PRESSURE_TEST') "
    "AND COALESCE(p.customer, '') <> 'TEST CUSTOMER' "
    "AND td.serial_number NOT LIKE 'TEST%%' "
    "AND td.task_category IN ('MECH','ELEC','PI','QI','SI')"
)
_COVERAGE_WINDOW_MONTH = (
    " AND (td.completed_at AT TIME ZONE 'Asia/Seoul') >= (%(from_month)s || '-01')::date "
    "AND (td.completed_at AT TIME ZONE 'Asia/Seoul') <  "
    "((%(to_month)s || '-01')::date + interval '1 month')"
)
# 신규 day 윈도우 (period 기반) — start/end = KST naive datetime (_resolve_period_range)
_COVERAGE_WINDOW_DAY = (
    " AND (td.completed_at AT TIME ZONE 'Asia/Seoul') >= %(start)s "
    "AND (td.completed_at AT TIME ZONE 'Asia/Seoul') < %(end)s"
)
# ★ 기존 문자열과 byte 동일 (base + month) → reliability-summary 호환
_COVERAGE_WHERE = _COVERAGE_BASE + _COVERAGE_WINDOW_MONTH

# 협력사 정규화 — MECH→mech_partner, ELEC→elec_partner (TMS→TMS(M)/(E)), PI/QI/SI→'GST'.
_COV_PARTNER_SQL = (
    "CASE td.task_category "
    "WHEN 'MECH' THEN CASE WHEN p.mech_partner = 'TMS' THEN 'TMS(M)' "
    "ELSE COALESCE(NULLIF(TRIM(p.mech_partner), ''), '(미지정)') END "
    "WHEN 'ELEC' THEN CASE WHEN p.elec_partner = 'TMS' THEN 'TMS(E)' "
    "ELSE COALESCE(NULLIF(TRIM(p.elec_partner), ''), '(미지정)') END "
    "ELSE 'GST' END"
)

# #92 partner 표시 필터 — 지정 시 그 협력사 task 만 (4 SQL 분모 포함). PI/QI/SI=GST 고정.
_COVERAGE_PARTNER_FILTER = f" AND {_COV_PARTNER_SQL} = %(partner)s"

# 분류 SQL 조각 (oneClick > zero_tap > tracked).
_TRACKED_SQL = (
    f"td.task_id NOT IN {_WHITELIST_SQL} "
    "AND td.active_time_minutes > 1 AND td.close_reason IS NULL"
)
# ── FIX-ZEROTAP-AUTOCLOSE-SEPARATION (#94, 2026-06-15) — 진짜 0초탭 = close NULL AND active≤1 ──
#   기존 _ZEROTAP_SQL(active≤1 OR close_reason)은 자동마감(close_reason, 평균 8h 방치)을 0초탭에 섞어
#   76% 부풀림 → 신규 instant 정의. close NULL = 작업자 정상 종료(active 신뢰), 자동마감은 별 분류.
_CLOSED_SQL = f"td.task_id NOT IN {_WHITELIST_SQL} AND td.close_reason IS NULL"   # 분모(작업자 종료)
_INSTANT_SQL = f"{_CLOSED_SQL} AND td.active_time_minutes <= 1"                   # 분자(즉시탭)
_AUTOCLOSE_SQL = f"td.task_id NOT IN {_WHITELIST_SQL} AND td.close_reason IS NOT NULL"  # 자동마감(별, reserved)
# 기존 zero_* = DEPRECATED (자동마감 포함·과대). FE 전환 후 제거 — 신규 consumer 는 instant_* 사용.
_ZEROTAP_SQL = (
    f"td.task_id NOT IN {_WHITELIST_SQL} "
    "AND (td.active_time_minutes <= 1 OR td.close_reason IS NOT NULL)"
)
# 드릴다운용 raw zero (oneClick task 포함, oneClick 플래그로 정상 구분). DEPRECATED.
_ZERO_RAW_SQL = "(td.active_time_minutes <= 1 OR td.close_reason IS NOT NULL)"

_CACHE_TTL_SEC = 3600
_cache: Dict[str, Tuple[float, Any]] = {}


def _pct(num: int, den: int) -> int:
    return round(100 * num / den) if den else 0


def _shares(partner_counts: List[Tuple[str, int]]) -> List[Dict[str, Any]]:
    """largest-remainder(정수 기반) — Σshare=100 보장 + 결정적 tie-break.

    partner_counts = (partner, cnt) 리스트, **cnt 내림차순→partner명 사전순 정렬 선행** 가정.
    base=(cnt*100)//total, rem=(cnt*100)%total. 잔여(100−Σbase)를 rem 큰 순(동률 시 idx 우선) +1.
    """
    total = sum(c for _, c in partner_counts)
    if total == 0:
        return []
    rows = []
    for idx, (partner, cnt) in enumerate(partner_counts):
        base = (cnt * 100) // total
        rem = (cnt * 100) % total
        rows.append({"partner": partner, "share": base, "_rem": rem, "_idx": idx})
    leftover = 100 - sum(r["share"] for r in rows)
    order = sorted(range(len(rows)), key=lambda i: (-rows[i]["_rem"], rows[i]["_idx"]))
    for i in range(leftover):
        rows[order[i]]["share"] += 1
    return [{"partner": r["partner"], "share": r["share"]} for r in rows]


def get_tagging_coverage(
    from_month: Optional[str] = None, to_month: Optional[str] = None,
    period: Optional[str] = None, reference_date: Optional[date] = None,
    partner: Optional[str] = None,
) -> Dict[str, Any]:
    """태깅 커버리지 + 0초탭 드릴다운 (3블록 = coverageMock.ts 1:1).

    coverage[] (공정별 추적율/0초탭/신뢰도) + well_tracked_pct + zero_tap_tasks{공정:[...]} + meta.
    #92: period(today|week|month|quarter)+reference_date → day 윈도우 / partner(company) → 협력사 필터(분모 포함).
         미지정 = from/to(YYYY-MM, KST) 월 누적 [CT_TRUST_START_MONTH, 현재월] (back-compat).
    """
    # 윈도우: period 지정 → day(_resolve_period_range) / else → month(현행)
    if period:
        from app.services.dashboard_service import _resolve_period_range
        start, end, _ps, _pe, _label = _resolve_period_range(period, reference_date)
        win_sql = _COVERAGE_WINDOW_DAY
        params = {"start": start, "end": end}
        win_from, win_to = start.date().isoformat(), end.date().isoformat()
    else:
        fm, tm = _resolve_window(from_month, to_month)
        win_sql = _COVERAGE_WINDOW_MONTH
        params = {"from_month": fm, "to_month": tm}
        win_from, win_to = fm, tm

    # partner 표시 필터 (분모 포함)
    part_sql = ""
    if partner:
        part_sql = _COVERAGE_PARTNER_FILTER
        params["partner"] = partner

    _where = _COVERAGE_BASE + win_sql + part_sql

    cache_key = (
        f"tagcov:{period or ''}:{reference_date.isoformat() if reference_date else ''}:"
        f"{partner or ''}:{win_from}:{win_to}"
    )
    hit = _cache.get(cache_key)
    if hit and (time.time() - hit[0]) < _CACHE_TTL_SEC:
        return hit[1]

    # ① 공정별 — tracked/instant(#94)/zero_tap(deprecated)/autoclose 카운트
    coverage_sql = f"""
        SELECT td.task_category AS process,
               COUNT(*) AS n,
               COUNT(*) FILTER (WHERE {_TRACKED_SQL}) AS tracked,
               COUNT(*) FILTER (WHERE {_INSTANT_SQL}) AS instant_n,
               COUNT(*) FILTER (WHERE {_CLOSED_SQL}) AS closed_n,
               COUNT(*) FILTER (WHERE {_AUTOCLOSE_SQL}) AS autoclose_n,
               COUNT(*) FILTER (WHERE {_ZEROTAP_SQL}) AS zero_tap
        FROM app_task_details td
        JOIN plan.product_info p ON p.serial_number = td.serial_number
        WHERE {_where}
        GROUP BY td.task_category
    """

    # ② well_tracked_pct — serial별 tracked행/전체행 (per-row, DUAL L/R 독립)
    well_sql = f"""
        WITH per_serial AS (
            SELECT td.serial_number,
                   COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE {_TRACKED_SQL}) AS tracked
            FROM app_task_details td
            JOIN plan.product_info p ON p.serial_number = td.serial_number
            WHERE {_where}
            GROUP BY td.serial_number
        )
        SELECT COUNT(*) AS serials,
               COUNT(*) FILTER (
                   WHERE total > 0 AND tracked::numeric / total >= {_WELL_TRACKED_THRESHOLD}
               ) AS well
        FROM per_serial
    """

    # ③ 드릴다운 — task별 n + instant_n/closed_n(#94) + zero_n(raw, deprecated)
    task_sql = f"""
        SELECT td.task_category AS process, td.task_id,
               COUNT(*) AS n,
               COUNT(*) FILTER (WHERE {_INSTANT_SQL}) AS instant_n,
               COUNT(*) FILTER (WHERE {_CLOSED_SQL}) AS closed_n,
               COUNT(*) FILTER (WHERE {_ZERO_RAW_SQL}) AS zero_n
        FROM app_task_details td
        JOIN plan.product_info p ON p.serial_number = td.serial_number
        WHERE {_where}
        GROUP BY td.task_category, td.task_id
    """

    # ③ partners — instant(진짜 0초탭) 인스턴스 협력사 점유 (#94 M-4: instant 기준)
    partner_sql = f"""
        SELECT td.task_category AS process, td.task_id,
               {_COV_PARTNER_SQL} AS partner,
               COUNT(*) AS cnt
        FROM app_task_details td
        JOIN plan.product_info p ON p.serial_number = td.serial_number
        WHERE {_where} AND {_INSTANT_SQL}
        GROUP BY td.task_category, td.task_id, partner
    """

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(coverage_sql, params)
            cov_rows = cur.fetchall()
            cur.execute(well_sql, params)
            well_row = cur.fetchone()
            cur.execute(task_sql, params)
            task_rows = cur.fetchall()
            cur.execute(partner_sql, params)
            partner_rows = cur.fetchall()
    finally:
        put_conn(conn)

    # ── ① coverage[] (5공정 고정 순서, 빈 공정 N=0 포함) ──
    cov_by_proc = {r["process"]: r for r in cov_rows}
    coverage: List[Dict[str, Any]] = []
    total_tasks = 0
    for proc in _PROCESS_ORDER:
        r = cov_by_proc.get(proc)
        n = int(r["n"]) if r else 0
        total_tasks += n
        tracked = int(r["tracked"]) if r else 0
        zero_tap = int(r["zero_tap"]) if r else 0
        instant_n = int(r["instant_n"]) if r else 0
        closed_n = int(r["closed_n"]) if r else 0
        autoclose_n = int(r["autoclose_n"]) if r else 0
        coverage.append({
            "process": proc,
            "tracking_pct": _pct(tracked, n),
            # #94 진짜 0초탭: 분모=closed_n(작업자 종료). closed_n=0 → null(데이터 없음, A-1)
            "instant_pct": (_pct(instant_n, closed_n) if closed_n else None),
            "instant_n": instant_n,
            "closed_n": closed_n,
            "autoclose_n": autoclose_n,
            "zero_tap_pct": _pct(zero_tap, n),   # DEPRECATED (자동마감 포함·과대)
            "confidence": "trusted" if n >= _TUKEY_MIN_N else "provisional",
            "n": n,
        })

    # ── ② well_tracked_pct ──
    serials = int(well_row["serials"]) if well_row else 0
    well = int(well_row["well"]) if well_row else 0
    well_tracked_pct = _pct(well, serials)

    # ── ③ zero_tap_tasks{공정:[...]} ──
    #   partner 묶기: (process, task_id) → [(partner, cnt) cnt desc, partner asc]
    pmap: Dict[Tuple[str, str], List[Tuple[str, int]]] = {}
    for r in partner_rows:
        pmap.setdefault((r["process"], r["task_id"]), []).append((r["partner"], int(r["cnt"])))
    for key in pmap:
        pmap[key].sort(key=lambda x: (-x[1], x[0]))

    zero_tap_tasks: Dict[str, List[Dict[str, Any]]] = {}
    for r in task_rows:
        proc = r["process"]
        task_id = r["task_id"]
        n = int(r["n"])
        if n < 1:
            continue
        zero_n = int(r["zero_n"])
        instant_n = int(r["instant_n"])
        closed_n = int(r["closed_n"])
        # partners = instant 기준(#94 M-4). instant_n=0 → partners=[] (share 분할 없음)
        partners = _shares(pmap.get((proc, task_id), [])) if instant_n > 0 else []
        zero_tap_tasks.setdefault(proc, []).append({
            "task_id": task_id,
            "ko": _TASK_NAME.get(task_id, task_id),
            # #94 진짜 0초탭: 분모=closed_n. closed_n=0 → null
            "instant_pct": (_pct(instant_n, closed_n) if closed_n else None),
            "instant_n": instant_n,
            "closed_n": closed_n,
            "zero_pct": _pct(zero_n, n),   # DEPRECATED
            "n": n,
            "oneClick": is_instant_whitelisted(task_id),
            "partners": partners,
        })
    for proc in zero_tap_tasks:
        zero_tap_tasks[proc].sort(key=lambda t: (-(t["instant_pct"] or 0), t["task_id"]))

    result = {
        "coverage": coverage,
        "well_tracked_pct": well_tracked_pct,
        "zero_tap_tasks": zero_tap_tasks,
        "meta": {
            "from": win_from,
            "to": win_to,
            "period": period,
            "reference_date": reference_date.isoformat() if reference_date else None,
            "partner": partner,
            "window": {"from": win_from, "to": win_to},
            "trust_start": CT_TRUST_START_MONTH,
            "total_tasks": total_tasks,
            "total_serials": serials,
            "confidence_threshold_n": _TUKEY_MIN_N,
            "denominator_basis": "completed_applicable_non_force",
            "coverage_partition": {
                "instant": "close_reason IS NULL AND active≤1 (진짜 0초탭, 분모=closed_n)",
                "tracked": "close_reason IS NULL AND active>1 (실작업 추적)",
                "autoclose": "close_reason IS NOT NULL (자동마감·admin/ship 대행, active 신뢰불가·reserved)",
                "oneClick": "whitelist (탱크도킹/출하완료, act=0 정상)",
            },
            "generated_at": datetime.now(_KST).isoformat(),
            "note": (
                "#94: 진짜 0초탭(instant)=close_reason NULL(작업자 종료) AND active≤1. 분모=closed_n. "
                "자동마감(close_reason, 평균 8h 방치)은 0초탭 아님 → autoclose_n 별 분류. "
                "⚠️ zero_tap_pct/zero_n=DEPRECATED(자동마감 포함·과대) — 신규 consumer 는 instant_* 사용."
            ),
        },
    }
    _cache[cache_key] = (time.time(), result)
    return result
