"""
Sprint 85 (FEAT-CT-ANALYSIS-HUB-BE-MVP-20260605) — CT 분석 허브 통계 서비스

MVP = ① 데이터 신뢰도 + ② CT 표준(IQR, man-hour).
설계서: AGENT_TEAM_LAUNCH.md § Sprint 85 / 결정 동결: CT_ANALYSIS_ROADMAP.md §15

핵심 정합 (Codex 라운드 1~2 GO):
  - CT 작업시간 = man-hour(`app_task_details.duration_minutes` = v2.22.0 interval-union SSoT),
    벽시계(elapsed) 아님. box plot = percentile_cont(duration_minutes/60.0).
  - clean 모집단 = duration_source IS NULL OR 'NORMAL_COMPLETION' (ATTENDANCE_OUT/추정 제외).
  - TMS(M) 더러운 task(TANK_MODULE/PRESSURE_TEST) 제외 + TEST 제외.
  - Tukey 1-pass: raw Q1/Q3 fence → fence 내 재집계. min/max = fence 내 실측.
  - 카테고리 = pooled median(참고용, Σ median 폐기) + task_count/sample_size/confidence.
  - 월 경계/교육 cut = KST (AT TIME ZONE 'Asia/Seoul').
"""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import psycopg2.extras

from app.db_pool import put_conn
from app.models.worker import get_db_connection
from app.services.task_seed import _TEMPLATES

logger = logging.getLogger(__name__)
_KST = ZoneInfo("Asia/Seoul")

# ── task_id → task_name 매핑 (task_seed 단일 소스) ──
_TASK_NAME: Dict[str, str] = {}
for _cat_tmpls in _TEMPLATES.values():
    for _t in _cat_tmpls:
        _TASK_NAME.setdefault(_t.task_id, _t.task_name)

_CATEGORY_LABEL_KO: Dict[str, str] = {
    "MECH": "기구",
    "ELEC": "전장",
    "TMS": "Tank Module",
    "PI": "PI (사전 검사)",
    "QI": "QI (품질 검사)",
    "SI": "SI (출하 검사)",
}

# 추정/더러운 source — ② 통계 제외 (① breakdown 에만 표시)
_CLEAN_SOURCES = ("NULL", "NORMAL_COMPLETION")  # 참고용(표기). SQL 은 IS NULL OR = 'NORMAL_COMPLETION'
_ESTIMATED_SOURCES = ("PREV_DAY_CAP", "FALLBACK_TRIGGER_DATE_17", "ATTENDANCE_OUT", "INVALID_WARNING")

# 교육 분기점 (KST 자정 literal — Codex R2 A)
_TRAINING_CUT_KST = "2026-06-02 00:00:00"

_VALID_PERIODS = {"last_90d"}  # MVP: 90일 합산만 (전체기간/단일월은 후속)

# ── S-1 (FEAT-CT-BASIS-ACTIVE-TRUSTCUTOFF, VIEW #82 ⓐ) ──
# 운영 정착 단일 신뢰 기준 (KST). 5월 이전 = 베타 연습(BAT 미온보딩).
CT_TRUST_START_MONTH = "2026-05"
# duration 058 백필 미적용 → 5월 duration 9% raw 잔존 경고 (별도 컷오프 아님, 경고만).
DURATION_STALE_BEFORE = "2026-06-01"
_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")  # 월 01~12 강제 (Codex: 2026-13 → DB cast 500 방지)


class CtParamError(ValueError):
    """CT endpoint 입력 검증 실패 — 라우트에서 400 으로 매핑."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _current_month_kst() -> str:
    return datetime.now(_KST).strftime("%Y-%m")


def _resolve_window(from_month: Optional[str], to_month: Optional[str]) -> tuple:
    """월 범위 해소 (YYYY-MM, KST). 기본 = [CT_TRUST_START_MONTH, 현재월].

    부분 지정: from만 → to=현재월 / to만 → from=trust_start.
    검증: YYYY-MM 형식 위반 → INVALID_MONTH / from>to → INVALID_RANGE.
    """
    cur = _current_month_kst()
    for label, v in (("from", from_month), ("to", to_month)):
        if v is not None and not _MONTH_RE.match(v):
            raise CtParamError("INVALID_MONTH", f"{label} 은 YYYY-MM 형식이어야 합니다.")
    fm = from_month or CT_TRUST_START_MONTH
    tm = to_month or cur
    if fm > tm:
        raise CtParamError("INVALID_RANGE", "from 은 to 보다 클 수 없습니다.")
    return fm, tm

# 모듈 레벨 TTL 캐시 (1h) — 기준 흔들림 방지(§15.3)
_CACHE_TTL_SEC = 3600
_cache: Dict[str, tuple] = {}  # key -> (ts, value)


def _cache_get(key: str) -> Optional[Any]:
    hit = _cache.get(key)
    if hit and (time.time() - hit[0]) < _CACHE_TTL_SEC:
        return hit[1]
    return None


def _cache_put(key: str, value: Any) -> None:
    _cache[key] = (time.time(), value)


def _confidence(n: int) -> str:
    if n >= 100:
        return "high"
    if n >= 30:
        return "medium"
    return "low"


def _r(v: Optional[float], nd: int = 1) -> float:
    return round(float(v), nd) if v is not None else 0.0


# clean 모집단 WHERE (alias td=app_task_details, p=plan.product_info)
# %% = psycopg2 리터럴 % (LIKE). _CLEAN_CORE = lookback 없는 공통 조건(교육 전후는 전기간 필요).
_CLEAN_CORE = (
    "td.completed_at IS NOT NULL "
    "AND td.duration_minutes IS NOT NULL "
    "AND (td.duration_source IS NULL OR td.duration_source = 'NORMAL_COMPLETION') "
    "AND td.task_id NOT IN ('TANK_MODULE','PRESSURE_TEST') "
    "AND COALESCE(p.customer, '') <> 'TEST CUSTOMER' "
    "AND td.serial_number NOT LIKE 'TEST%%'"
)
# S-1: KST 월경계 반열림 윈도우 [from월 1일, to월+1 1일) — lookback predicate 대체.
_WINDOW_WHERE = (
    " AND (td.completed_at AT TIME ZONE 'Asia/Seoul') >= (%(from_month)s || '-01')::date"
    " AND (td.completed_at AT TIME ZONE 'Asia/Seoul') <  ((%(to_month)s || '-01')::date + interval '1 month')"
)
_CLEAN_WHERE = _CLEAN_CORE + _WINDOW_WHERE


def _model_clause(model: Optional[str]) -> str:
    if model and model not in ("전체 모델", "ALL", ""):
        return " AND p.model ILIKE %(model_prefix)s"
    return ""


def _category_clause(category: Optional[str]) -> str:
    if category and category not in ("ALL", ""):
        return " AND td.task_category = %(category)s"
    return ""


def _dual_clause(dual: Optional[str]) -> str:
    # Sprint 86-FU (VIEW #81): DUAL/단일 분리. model 명에 'DUAL' 포함(중간 포함, iVAS...DUAL... 엣지 커버).
    if dual == "dual":
        return " AND p.model ILIKE '%%DUAL%%'"
    if dual == "single":
        return " AND p.model NOT ILIKE '%%DUAL%%'"
    return ""  # 미지정 = 합산 (하위호환)


def _stats_params(
    from_month: str, to_month: str, model: Optional[str], category: Optional[str]
) -> Dict[str, Any]:
    p: Dict[str, Any] = {"from_month": from_month, "to_month": to_month}
    if model and model not in ("전체 모델", "ALL", ""):
        p["model_prefix"] = f"{model}%"
    if category and category not in ("ALL", ""):
        p["category"] = category
    return p


def get_task_ct_stats(
    basis: str = "duration",
    from_month: Optional[str] = None,
    to_month: Optional[str] = None,
    model: Optional[str] = None,
    category: Optional[str] = None,
    dual: Optional[str] = None,
) -> Dict[str, Any]:
    """② CT 표준 — task별 box plot(Tukey) + 카테고리 pooled median + meta.

    S-1 (VIEW #82 ⓐ):
      - basis='duration'(기본, man-hour) / 'active'(active_time_minutes, act>0만).
      - 윈도우 = KST 월경계 반열림 [from월, to월+1). 기본 [2026-05, 현재월].
      - 생존편향 방어: basis=active 시 tracking_coverage_by_partner 동반 노출.
    dual: 'dual'(DUAL 모델만) / 'single'(단일만) / None(합산, 하위호환) — VIEW #81.
    """
    if basis not in ("duration", "active"):
        raise CtParamError("INVALID_BASIS", "basis 는 duration|active 중 하나여야 합니다.")
    from_month, to_month = _resolve_window(from_month, to_month)

    cache_key = f"task_stats:{basis}:{from_month}:{to_month}:{model}:{category}:{dual}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    params = _stats_params(from_month, to_month, model, category)
    mc = _model_clause(model) + _dual_clause(dual)
    cc = _category_clause(category)

    # basis 분기 — 값 식 + 모집단 추가 필터(active 시 act>0)
    val_expr = "td.active_time_minutes / 60.0" if basis == "active" else "td.duration_minutes / 60.0"
    pop_extra = " AND td.active_time_minutes > 0" if basis == "active" else ""

    # Tukey 1-pass CTE: base → fence(raw Q1/Q3) → clipped(fence 내) → 집계.
    # base_n(Tukey 전) 보존하여 tukey_clipped 판정 (A-3).
    cte = f"""
        WITH base AS (
            SELECT td.task_category AS category, td.task_id,
                   {val_expr} AS dh
            FROM app_task_details td
            JOIN plan.product_info p ON p.serial_number = td.serial_number
            WHERE {_CLEAN_WHERE}{mc}{cc}{pop_extra}
        ),
        fence AS (
            SELECT task_id,
                   COUNT(*) AS base_n,
                   percentile_cont(0.25) WITHIN GROUP (ORDER BY dh) AS q1,
                   percentile_cont(0.75) WITHIN GROUP (ORDER BY dh) AS q3
            FROM base GROUP BY task_id
        ),
        clipped AS (
            SELECT b.category, b.task_id, b.dh
            FROM base b JOIN fence f ON f.task_id = b.task_id
            WHERE b.dh BETWEEN (f.q1 - 1.5*(f.q3-f.q1)) AND (f.q3 + 1.5*(f.q3-f.q1))
        )
    """

    task_sql = cte + """
        SELECT c.category, c.task_id,
               COUNT(*) AS n,
               MAX(f.base_n) AS base_n,
               MIN(c.dh) AS min_h, MAX(c.dh) AS max_h, AVG(c.dh) AS mean_h,
               percentile_cont(0.25) WITHIN GROUP (ORDER BY c.dh) AS q1,
               percentile_cont(0.5)  WITHIN GROUP (ORDER BY c.dh) AS median,
               percentile_cont(0.75) WITHIN GROUP (ORDER BY c.dh) AS q3
        FROM clipped c JOIN fence f ON f.task_id = c.task_id
        GROUP BY c.category, c.task_id
        ORDER BY c.category, c.task_id
    """
    # 보조 active-time box plot — 항상 active_time_minutes>0 모집단 (basis 무관, 별 필드 유지).
    active_cte = f"""
        WITH base AS (
            SELECT td.task_id, td.active_time_minutes / 60.0 AS dh
            FROM app_task_details td
            JOIN plan.product_info p ON p.serial_number = td.serial_number
            WHERE {_CLEAN_WHERE}{mc}{cc} AND td.active_time_minutes > 0
        ),
        fence AS (
            SELECT task_id,
                   percentile_cont(0.25) WITHIN GROUP (ORDER BY dh) AS q1,
                   percentile_cont(0.75) WITHIN GROUP (ORDER BY dh) AS q3
            FROM base GROUP BY task_id
        ),
        clipped AS (
            SELECT b.task_id, b.dh FROM base b JOIN fence f ON f.task_id = b.task_id
            WHERE b.dh BETWEEN (f.q1 - 1.5*(f.q3-f.q1)) AND (f.q3 + 1.5*(f.q3-f.q1))
        )
    """
    active_task_sql = active_cte + """
        SELECT task_id, COUNT(*) AS n,
               MIN(dh) AS min_h, MAX(dh) AS max_h, AVG(dh) AS mean_h,
               percentile_cont(0.25) WITHIN GROUP (ORDER BY dh) AS q1,
               percentile_cont(0.5)  WITHIN GROUP (ORDER BY dh) AS median,
               percentile_cont(0.75) WITHIN GROUP (ORDER BY dh) AS q3
        FROM clipped GROUP BY task_id
    """
    # 카테고리 pooled median (Σ median 폐기 — Codex M-Q5)
    cat_sql = cte + """
        SELECT category,
               COUNT(DISTINCT task_id) AS task_count,
               COUNT(*) AS sample_size,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY dh) AS pooled_median
        FROM clipped
        GROUP BY category
        ORDER BY category
    """
    # meta — 모델 분포 + 추정 source 제외 비율 (편향 노출, Codex A-Q4)
    model_dist_sql = f"""
        SELECT p.model AS model, COUNT(*) AS n
        FROM app_task_details td
        JOIN plan.product_info p ON p.serial_number = td.serial_number
        WHERE {_CLEAN_WHERE}{mc}{cc}{pop_extra}
        GROUP BY p.model ORDER BY n DESC
    """
    # active 채움 비율 + active=0/NULL 카운트 — clean 모집단 전체(window/필터 적용, Tukey 전)
    fill_sql = f"""
        SELECT COUNT(*) AS clean_total,
               COUNT(*) FILTER (WHERE td.active_time_minutes IS NOT NULL) AS active_filled,
               COUNT(*) FILTER (WHERE td.active_time_minutes = 0) AS active_zero,
               COUNT(*) FILTER (WHERE td.active_time_minutes IS NULL) AS active_null
        FROM app_task_details td
        JOIN plan.product_info p ON p.serial_number = td.serial_number
        WHERE {_CLEAN_WHERE}{mc}{cc}
    """
    # 추정 source 제외 분포 — window 적용 (lookback predicate 제거, M-6)
    excl_sql = f"""
        SELECT COALESCE(td.duration_source, 'NULL') AS source, COUNT(*) AS n
        FROM app_task_details td
        JOIN plan.product_info p ON p.serial_number = td.serial_number
        WHERE td.completed_at IS NOT NULL
          AND td.duration_minutes IS NOT NULL
          AND td.task_id NOT IN ('TANK_MODULE','PRESSURE_TEST')
          AND COALESCE(p.customer, '') <> 'TEST CUSTOMER'
          AND td.serial_number NOT LIKE 'TEST%%'
          {_WINDOW_WHERE}
          {mc}{cc}
        GROUP BY COALESCE(td.duration_source, 'NULL')
    """
    # M-1/M-5: 협력사별 추적 커버리지 (basis=active 전용) — 표시통계와 동일 슬라이스
    #   (model/category/dual + clean/TMS/TEST/window 적용, act>0 제외 전 + Tukey 전).
    coverage_sql = f"""
        SELECT COALESCE(
                   CASE td.task_category
                       WHEN 'MECH' THEN p.mech_partner
                       WHEN 'ELEC' THEN p.elec_partner
                       WHEN 'TMS'  THEN p.module_outsourcing
                       ELSE 'GST'
                   END, '(미지정)') AS partner,
               COUNT(*) AS n_total,
               COUNT(*) FILTER (WHERE td.active_time_minutes > 0) AS n_used
        FROM app_task_details td
        JOIN plan.product_info p ON p.serial_number = td.serial_number
        WHERE {_CLEAN_WHERE}{mc}{cc}
        GROUP BY 1
        ORDER BY n_total DESC
    """

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(task_sql, params)
            task_rows = cur.fetchall()
            cur.execute(active_task_sql, params)
            active_rows = cur.fetchall()
            cur.execute(cat_sql, params)
            cat_rows = cur.fetchall()
            cur.execute(model_dist_sql, params)
            model_rows = cur.fetchall()
            cur.execute(fill_sql, params)
            fill_row = cur.fetchone()
            cur.execute(excl_sql, params)
            excl_rows = cur.fetchall()
            coverage_rows = []
            if basis == "active":
                cur.execute(coverage_sql, params)
                coverage_rows = cur.fetchall()
    finally:
        put_conn(conn)

    # task_id → active box plot 매핑 (보조 필드)
    active_by_task = {r["task_id"]: r for r in active_rows}

    tasks: List[Dict[str, Any]] = []
    tukey_clipped = False
    for r in task_rows:
        n = int(r["n"])
        base_n = int(r["base_n"])
        if n < base_n:
            tukey_clipped = True
        q1, q3 = _r(r["q1"]), _r(r["q3"])
        item = {
            "task_id": r["task_id"],
            "task_name": _TASK_NAME.get(r["task_id"], r["task_id"]),
            "category": r["category"],
            "min_hours": _r(r["min_h"]),
            "q1_hours": q1,
            "median_hours": _r(r["median"]),
            "q3_hours": q3,
            "max_hours": _r(r["max_h"]),
            "mean_hours": _r(r["mean_h"]),
            "iqr_hours": _r(q3 - q1),
            "sample_size": n,
            "confidence": _confidence(n),
            "standard_status": "provisional" if n < 30 else "standard",  # A-2
        }
        # 보조 active-time box plot (별 필드)
        a = active_by_task.get(r["task_id"])
        if a:
            an = int(a["n"])
            aq1, aq3 = _r(a["q1"]), _r(a["q3"])
            item.update({
                "active_min_hours": _r(a["min_h"]),
                "active_q1_hours": aq1,
                "active_median_hours": _r(a["median"]),
                "active_q3_hours": aq3,
                "active_max_hours": _r(a["max_h"]),
                "active_mean_hours": _r(a["mean_h"]),
                "active_iqr_hours": _r(aq3 - aq1),
                "active_sample_size": an,
            })
        tasks.append(item)

    categories: List[Dict[str, Any]] = []
    for r in cat_rows:
        n = int(r["sample_size"])
        categories.append({
            "category": r["category"],
            "label_ko": _CATEGORY_LABEL_KO.get(r["category"], r["category"]),
            "task_count": int(r["task_count"]),
            "sample_size": n,
            "confidence": _confidence(n),
            "pooled_median_hours": _r(r["pooled_median"]),
        })

    total_sample = sum(t["sample_size"] for t in tasks)  # n_used = 산출 모집단(Tukey 후)
    _clean_total = int(fill_row["clean_total"]) if fill_row else 0
    _active_filled = int(fill_row["active_filled"]) if fill_row else 0
    _active_zero = int(fill_row["active_zero"]) if fill_row else 0
    _active_null = int(fill_row["active_null"]) if fill_row else 0
    excluded_by_source = {
        r["source"]: int(r["n"]) for r in excl_rows if r["source"] in _ESTIMATED_SOURCES
    }
    total_window = sum(int(r["n"]) for r in excl_rows)
    excluded_n = sum(excluded_by_source.values())
    is_filtered = bool(model and model not in ("전체 모델", "ALL", ""))

    meta: Dict[str, Any] = {
        "as_of": datetime.now(_KST).isoformat(),
        "basis": basis,
        "trust_start": "2026-05-01",
        "window": {"from": from_month, "to": to_month},
        "immature_window": from_month < CT_TRUST_START_MONTH,
        "basis_label": "active_time(순수 작업시간)" if basis == "active" else "man-hour(공수)",
        "trust_reason": "운영 정착 2026-05+ 단일 기준 (5월 이전 = 베타 연습)",
        "n_total": _clean_total,    # clean 모집단 전체(window/필터 적용, Tukey 전)
        "n_used": total_sample,     # 산출 모집단(Tukey 후 Σ sample_size)
        "tukey_clipped": tukey_clipped,  # A-3
        "total_sample": total_sample,
        "model_distribution": [
            {"model": r["model"], "n": int(r["n"])} for r in model_rows
        ],
        "excluded_by_source": excluded_by_source,
        "excluded_pct": _r((excluded_n / total_window * 100) if total_window else 0.0),
        "median_basis": "pooled_clean_instances",  # 표준공수합 아님 (Codex R2 A)
        "confidence_scope": "filtered" if is_filtered else "all",
        "low_sample_warning": is_filtered and total_sample < 100,
        "dual_scope": dual or "all",  # VIEW #81 — dual/single/all

        # Sprint 86: active-time(순수 작업시간) 표준 — man-hour 와 병행 (VIEW active 우선 권고)
        "standard_basis": "active_time",
        "active_available": _r((_active_filled / _clean_total * 100) if _clean_total else 0.0),
        "active_basis_note": (
            "active_time 은 운영 표준 근무/휴게 시간표(현재 admin_settings) 기준 — "
            "백필·신규 완료 동일 적용. 시간표는 운영상 고정(변경 이력 없음). "
            "향후 변경 시 전체 재백필 필요."
        ),
    }
    # duration_stale 경고는 윈도우가 stale 경계(6/1) 이전을 포함할 때만 (Codex: from>=2026-06 → 부재)
    if basis == "duration" and from_month < "2026-06":
        meta["duration_stale_before"] = DURATION_STALE_BEFORE  # 058 미적용 경고 (단일 5/1 유지)
    if basis == "active":
        meta["excluded_zero_active"] = _active_zero
        meta["excluded_null_active"] = _active_null
        meta["tracking_coverage_by_partner"] = [
            {
                "partner": r["partner"],
                "n_total": int(r["n_total"]),
                "n_used": int(r["n_used"]),
                "tracked_rate": round(int(r["n_used"]) / int(r["n_total"]), 2) if int(r["n_total"]) else 0.0,
            }
            for r in coverage_rows
        ]

    result = {"tasks": tasks, "categories": categories, "meta": meta}
    _cache_put(cache_key, result)
    return result


def get_data_quality(from_month: Optional[str] = None, to_month: Optional[str] = None) -> Dict[str, Any]:
    """① 데이터 신뢰도 — duration_source 분포 + 자동마감 추이(월별 KST) + 교육 전후.

    S-1 정합(VIEW #82): lookback_days(90일) → CT_TRUST_START_MONTH 윈도우([from,to] 반열림 KST).
    duration_source 분포만 윈도우 적용(task-stats reliability 와 동일 구간). 추이(6mo 고정)·교육 전후(전기간)는 의도상 유지.
    """
    from_month, to_month = _resolve_window(from_month, to_month)
    cache_key = f"data_quality:{from_month}:{to_month}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    # [1] duration_source 분포 (완료, TMS(M)·TEST 제외, 트러스트 윈도우 [from,to])
    src_sql = f"""
        SELECT COALESCE(td.duration_source, 'NULL') AS source, COUNT(*) AS n
        FROM app_task_details td
        JOIN plan.product_info p ON p.serial_number = td.serial_number
        WHERE td.completed_at IS NOT NULL
          AND td.task_id NOT IN ('TANK_MODULE','PRESSURE_TEST')
          AND COALESCE(p.customer, '') <> 'TEST CUSTOMER'
          AND td.serial_number NOT LIKE 'TEST%%'
          {_WINDOW_WHERE}
        GROUP BY COALESCE(td.duration_source, 'NULL')
        ORDER BY n DESC
    """
    # [2] 월별 마감유형 추이 — KST 월 경계 (Codex M-Q8). 추이는 lookback 무관 고정 6개월 윈도우(의도).
    #     close_reason LIKE 'AUTO_CLOSED_BY_%%' = dashboard_service._AUTO_LIKE 와 동치 (분류 규칙 변경 시 동기화).
    trend_sql = """
        SELECT to_char(date_trunc('month', td.completed_at AT TIME ZONE 'Asia/Seoul'), 'YYYY-MM') AS month,
               COUNT(*) AS total,
               COUNT(*) FILTER (
                   WHERE td.close_reason LIKE 'AUTO_CLOSED_BY_%%' AND td.force_closed = FALSE
               ) AS auto,
               COUNT(*) FILTER (WHERE td.force_closed = TRUE) AS force
        FROM app_task_details td
        JOIN plan.product_info p ON p.serial_number = td.serial_number
        WHERE td.completed_at IS NOT NULL
          AND td.task_id NOT IN ('TANK_MODULE','PRESSURE_TEST')
          AND COALESCE(p.customer, '') <> 'TEST CUSTOMER'
          AND td.serial_number NOT LIKE 'TEST%%'
          AND td.completed_at >= now() - INTERVAL '6 months'
        GROUP BY 1 ORDER BY 1
    """
    # [5] 교육(6/2 KST) 전후 task별 man-hour (clean only)
    train_sql = f"""
        SELECT td.task_id,
               AVG(td.duration_minutes / 60.0) FILTER (
                   WHERE (td.completed_at AT TIME ZONE 'Asia/Seoul') < TIMESTAMP '{_TRAINING_CUT_KST}'
               ) AS pre_mh,
               COUNT(*) FILTER (
                   WHERE (td.completed_at AT TIME ZONE 'Asia/Seoul') < TIMESTAMP '{_TRAINING_CUT_KST}'
               ) AS pre_n,
               AVG(td.duration_minutes / 60.0) FILTER (
                   WHERE (td.completed_at AT TIME ZONE 'Asia/Seoul') >= TIMESTAMP '{_TRAINING_CUT_KST}'
               ) AS post_mh,
               COUNT(*) FILTER (
                   WHERE (td.completed_at AT TIME ZONE 'Asia/Seoul') >= TIMESTAMP '{_TRAINING_CUT_KST}'
               ) AS post_n
        FROM app_task_details td
        JOIN plan.product_info p ON p.serial_number = td.serial_number
        WHERE {_CLEAN_CORE}
        GROUP BY td.task_id
        HAVING COUNT(*) FILTER (
                   WHERE (td.completed_at AT TIME ZONE 'Asia/Seoul') < TIMESTAMP '{_TRAINING_CUT_KST}'
               ) >= 5
        ORDER BY pre_n DESC
        LIMIT 10
    """

    params = {"from_month": from_month, "to_month": to_month}
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(src_sql, params)
            src_rows = cur.fetchall()
            cur.execute(trend_sql, {})
            trend_rows = cur.fetchall()
            cur.execute(train_sql, {})
            train_rows = cur.fetchall()
    finally:
        put_conn(conn)

    src_total = sum(int(r["n"]) for r in src_rows) or 1
    duration_source_dist = [
        {
            "source": r["source"],
            "n": int(r["n"]),
            "pct": _r(int(r["n"]) / src_total * 100),
            "clean": r["source"] in _CLEAN_SOURCES,
        }
        for r in src_rows
    ]

    auto_close_trend = []
    for r in trend_rows:
        total = int(r["total"])
        auto = int(r["auto"])
        force = int(r["force"])
        auto_close_trend.append({
            "month": r["month"],
            "total": total,
            "normal": total - auto - force,
            "auto": auto,
            "force": force,
            "auto_rate": _r(auto / total * 100) if total else 0.0,
        })

    training_impact = []
    for r in train_rows:
        post_n = int(r["post_n"])
        training_impact.append({
            "task_id": r["task_id"],
            "task": _TASK_NAME.get(r["task_id"], r["task_id"]),
            "pre_mh": _r(r["pre_mh"]),
            "post_mh": _r(r["post_mh"]),
            "pre_n": int(r["pre_n"]),
            "post_n": post_n,
            # post 표본 부족 표기 (Codex M-Q8)
            "confidence": "insufficient_sample" if post_n < 30 else "ok",
        })

    result = {
        "duration_source_dist": duration_source_dist,
        "auto_close_trend": auto_close_trend,
        "training_impact": training_impact,
        "meta": {
            "as_of": datetime.now(_KST).isoformat(),
            "window": {"from": from_month, "to": to_month},   # S-1 정합 — FE 동적 라벨용
            "trust_start": "2026-05-01",
            "immature_window": from_month < CT_TRUST_START_MONTH,
            "training_cut_kst": _TRAINING_CUT_KST,
        },
    }
    _cache_put(cache_key, result)
    return result
