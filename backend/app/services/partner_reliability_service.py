"""
FEAT-PARTNER-RELIABILITY (#93, 2026-06-15) — 협력사×모델×공정 추적률 분해 + 월별 추이

  GET /api/ct/partner-reliability?process=MECH|ELEC&model=&from=&to=   (read-only, migration 0)

reliability-summary(v2.41.0)는 추적률을 모델 단위(협력사 합산)로만 줌 → 협력사로 분해해
"표준 가능 입력=FNI / 교육 타겟=BAT" 행동 가능. v2.42.1(whitelist 자주검사 제거) 추적률 base 정정 후.

핵심 정합 (Codex 라운드 1 GO, M-Q4 반영):
  - 추적률 분자 = _TRACKED_SQL / 분모 = _COVERAGE_BASE (tagging-coverage/reliability-summary 동일 basis)
    → by_model_process invariant = reliability-summary 모델공정추적률 일치.
  - 협력사 정규화 = _COV_PARTNER_SQL (MECH→mech_partner TMS→TMS(M), ELEC→elec_partner TMS→TMS(E)).
  - GST·SH·(미지정) 명시 제외 (M-Q4, close-type-trend 패턴).
  - model_prefix 정규화 = _norm_model_prefix (Python, raw Σtracked/Σn 합산 — pct 평균 금지).
  - batch = TMS(M)(일괄 garbage): 합산 포함(invariant 보존) + by_model_process batch_n 노출(Q2-A), trend omit.
  - 각 row confidence (n>=30 trusted / provisional, Q5-A). 설계: AGENT_TEAM_LAUNCH.md § FEAT-PARTNER-RELIABILITY.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import psycopg2.extras

from app.db_pool import put_conn
from app.models.worker import get_db_connection
from app.services.statistics_service import (
    CT_TRUST_START_MONTH,
    CtParamError,
    _INSTANT_WHITELIST,
    _norm_model_prefix,
    _resolve_window,
)

_KST = ZoneInfo("Asia/Seoul")
_GATE = 70          # 추적률 게이트 (사용자 결정, reliability-summary 정합)
_N_MIN = 30         # 표본 신뢰 최소
_CACHE_TTL_SEC = 3600
_cache: Dict[str, Tuple[float, Any]] = {}


def _pct(tracked: int, n: int) -> float:
    return round(100 * tracked / n, 1) if n else 0.0


def _conf(n: int) -> str:
    return "trusted" if n >= _N_MIN else "provisional"


def get_partner_reliability(
    process: Optional[str] = None,
    model: Optional[str] = None,
    from_month: Optional[str] = None,
    to_month: Optional[str] = None,
) -> Dict[str, Any]:
    """협력사×모델×공정 추적률 분해 (by_cell/by_model_process/by_partner/trend + meta).

    추적률 = _TRACKED_SQL / _COVERAGE_BASE (reliability-summary 동일 basis). MECH/ELEC only,
    GST·SH 제외. batch(TMS(M)) 합산 포함·trend omit. raw Σ 합산(pct 평균 금지).
    """
    # 함수 내부 import — tagging_coverage_service ↔ statistics 순환 회피
    from app.services.tagging_coverage_service import (
        _COVERAGE_BASE,
        _COVERAGE_WINDOW_MONTH,
        _COV_PARTNER_SQL,
        _TRACKED_SQL,
    )

    if process is not None and process not in ("MECH", "ELEC"):
        raise CtParamError("INVALID_PROCESS", "process 는 MECH|ELEC 중 하나여야 합니다.")
    from_month, to_month = _resolve_window(from_month, to_month)

    cache_key = f"partner_rel:{process or ''}:{model or ''}:{from_month}:{to_month}"
    hit = _cache.get(cache_key)
    if hit and (time.time() - hit[0]) < _CACHE_TTL_SEC:
        return hit[1]

    proc_sql = " AND td.task_category = %(process)s" if process else " AND td.task_category IN ('MECH','ELEC')"
    model_sql = " AND p.model ILIKE %(model)s" if model else ""
    params: Dict[str, Any] = {"from_month": from_month, "to_month": to_month}
    if process:
        params["process"] = process
    if model:
        params["model"] = f"{model}%"

    # (partner, model_full, process, month) 단위 분모 n + 분자 tracked. GST·SH·(미지정) 제외 (M-Q4).
    sql = f"""
        WITH base AS (
            SELECT {_COV_PARTNER_SQL} AS partner,
                   p.model            AS model_full,
                   td.task_category   AS process,
                   to_char(td.completed_at AT TIME ZONE 'Asia/Seoul', 'YYYY-MM') AS month,
                   (CASE WHEN {_TRACKED_SQL} THEN 1 ELSE 0 END) AS tracked
            FROM app_task_details td
            JOIN plan.product_info p ON p.serial_number = td.serial_number
            WHERE {_COVERAGE_BASE}{_COVERAGE_WINDOW_MONTH}{proc_sql}{model_sql}
        )
        SELECT partner, model_full, process, month,
               COUNT(*) AS n, SUM(tracked) AS tracked
        FROM base
        WHERE partner NOT IN ('GST', 'SH', '(미지정)')
        GROUP BY 1, 2, 3, 4
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT model_prefix FROM model_config ORDER BY LENGTH(model_prefix) DESC")
            prefixes = [r["model_prefix"] for r in cur.fetchall()]
            cur.execute(sql, params)
            rows = cur.fetchall()
    finally:
        put_conn(conn)

    # ── raw 누적 (pct 평균 금지 — Σtracked/Σn) ──
    cell: Dict[tuple, List[int]] = {}      # (partner, prefix, process) -> [n, tracked]
    mp: Dict[tuple, List[int]] = {}        # (prefix, process) -> [n, tracked, batch_n]
    part: Dict[tuple, List[int]] = {}      # (partner, process) -> [n, tracked]
    tr: Dict[tuple, List[int]] = {}        # (month, partner, process) -> [n, tracked]
    for r in rows:
        partner = r["partner"]
        prefix = _norm_model_prefix(r["model_full"], prefixes)
        proc = r["process"]
        n = int(r["n"])
        tracked = int(r["tracked"] or 0)
        is_batch = partner == "TMS(M)"

        c = cell.setdefault((partner, prefix, proc), [0, 0])
        c[0] += n
        c[1] += tracked

        m = mp.setdefault((prefix, proc), [0, 0, 0])
        m[0] += n
        m[1] += tracked
        if is_batch:
            m[2] += n  # batch_n (Q2-A: garbage 포함량 노출)

        p = part.setdefault((partner, proc), [0, 0])
        p[0] += n
        p[1] += tracked

        # trend = batch(TMS(M)) omit
        if not is_batch:
            t = tr.setdefault((r["month"], partner, proc), [0, 0])
            t[0] += n
            t[1] += tracked

    by_cell = [
        {
            "partner": pt, "model": pf, "process": pr,
            "tracking_pct": _pct(v[1], v[0]), "n": v[0],
            "confidence": _conf(v[0]),
            **({"batch": True} if pt == "TMS(M)" else {}),
        }
        for (pt, pf, pr), v in cell.items() if v[0] >= 1
    ]
    by_cell.sort(key=lambda x: (x["process"], x["model"], x["partner"]))

    by_model_process = [
        {
            "model": pf, "process": pr,
            "tracking_pct": _pct(v[1], v[0]), "n": v[0],
            "batch_n": v[2], "confidence": _conf(v[0]),
        }
        for (pf, pr), v in mp.items() if v[0] >= 1
    ]
    by_model_process.sort(key=lambda x: (x["process"], x["model"]))

    by_partner = [
        {
            "partner": pt, "process": pr,
            "tracking_pct": _pct(v[1], v[0]), "n": v[0],
            "confidence": _conf(v[0]),
            **({"batch": True} if pt == "TMS(M)" else {}),
        }
        for (pt, pr), v in part.items() if v[0] >= 1
    ]
    by_partner.sort(key=lambda x: (x["process"], -x["tracking_pct"]))

    trend = [
        {
            "month": mo, "partner": pt, "process": pr,
            "tracking_pct": _pct(v[1], v[0]), "n": v[0],
            "confidence": _conf(v[0]),
        }
        for (mo, pt, pr), v in tr.items() if v[0] >= 1
    ]
    trend.sort(key=lambda x: (x["month"], x["process"], x["partner"]))

    result = {
        "by_cell": by_cell,
        "by_model_process": by_model_process,
        "by_partner": by_partner,
        "trend": trend,
        "meta": {
            "from": from_month,
            "to": to_month,
            "gate": _GATE,
            "n_min": _N_MIN,
            "trust_start": CT_TRUST_START_MONTH,
            "whitelist": sorted(_INSTANT_WHITELIST),
            "scope": "MECH/ELEC, GST·SH 제외. batch(TMS(M))=일괄 — 합산 포함·trend omit.",
            "generated_at": datetime.now(_KST).isoformat(),
        },
    }
    _cache[cache_key] = (time.time(), result)
    return result
