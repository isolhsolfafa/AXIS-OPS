"""
FEAT-PARTNER-RELIABILITY (#93, 2026-06-15) — 협력사×모델×공정 추적률 분해 + 월별 추이
  + MONTHLY v4 (2026-06-15) — 매트릭스 period/협력사 필터 + 추이 분리

  GET /api/ct/partner-reliability?period=today|week|month|quarter&reference_date=&partner=&process=&model=&from=&to=
  (read-only, migration 0)

설계: AGENT_TEAM_LAUNCH.md § FEAT-PARTNER-RELIABILITY (+ MONTHLY v1~v4). Codex 라운드 3 GO.

핵심:
  - 추적률 분자 = _TRACKED_SQL / 분모 = _COVERAGE_BASE (reliability-summary 동일 basis, whitelist 2개 정정).
  - **매트릭스**(by_cell/by_model_process/by_partner) = period 윈도우(미지정=from/to month) + partner/process/model 필터.
  - **trend** = trust_start~현재월 월별, process/model 적용 / period·partner 제외(시계열, 사용자 결정).
  - 협력사 정규화 _COV_PARTNER_SQL. GST·SH·(미지정) 제외. model_prefix _norm_model_prefix(Python raw Σ, pct 평균 금지).
  - batch(TMS(M))=일괄: 매트릭스 합산 포함+batch_n, trend omit. confidence(n>=30).
  - 2 쿼리(매트릭스 day GROUP BY partner/model/process / trend 월별 +month). Codex M-1(day 못 자름) 해소.
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
_GATE = 70          # 추적률 게이트 (reliability-summary 정합)
_N_MIN = 30         # 표본 신뢰 최소
_VALID_PERIODS = ("today", "week", "month", "quarter")
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
    period: Optional[str] = None,
    reference_date=None,
    partner: Optional[str] = None,
) -> Dict[str, Any]:
    """협력사×모델×공정 추적률 분해 — 매트릭스(period/partner 필터) + trend(시계열).

    매트릭스 = period 윈도우(미지정=from/to 누적) + partner/process/model 필터.
    trend = trust_start~현재월 월별, process/model 적용·period/partner 제외 (사용자 결정).
    """
    # 함수 내부 import — 순환 회피
    from app.services.tagging_coverage_service import (
        _COVERAGE_BASE,
        _COVERAGE_PARTNER_FILTER,
        _COVERAGE_WINDOW_DAY,
        _COVERAGE_WINDOW_MONTH,
        _COV_PARTNER_SQL,
        _TRACKED_SQL,
    )

    if process is not None and process not in ("MECH", "ELEC"):
        raise CtParamError("INVALID_PROCESS", "process 는 MECH|ELEC 중 하나여야 합니다.")
    if period is not None and period not in _VALID_PERIODS:
        raise CtParamError("INVALID_PERIOD", "period 는 today|week|month|quarter 중 하나여야 합니다.")

    # ── 매트릭스 윈도우: period 지정 → day / 미지정 → from/to month ──
    matrix_params: Dict[str, Any] = {}
    if period:
        from app.services.dashboard_service import _resolve_period_range
        m_start, m_end, _ps, _pe, _label = _resolve_period_range(period, reference_date)
        matrix_window = _COVERAGE_WINDOW_DAY
        matrix_params["start"] = m_start
        matrix_params["end"] = m_end
        matrix_win_echo = {"from": m_start.date().isoformat(), "to": m_end.date().isoformat()}
    else:
        fm, tm = _resolve_window(from_month, to_month)
        matrix_window = _COVERAGE_WINDOW_MONTH
        matrix_params["from_month"] = fm
        matrix_params["to_month"] = tm
        matrix_win_echo = {"from": fm, "to": tm}

    # process/model/partner 필터 (매트릭스)
    proc_sql = " AND td.task_category = %(process)s" if process else " AND td.task_category IN ('MECH','ELEC')"
    model_sql = " AND p.model ILIKE %(model)s" if model else ""
    partner_sql = _COVERAGE_PARTNER_FILTER if partner else ""
    if process:
        matrix_params["process"] = process
    if model:
        matrix_params["model"] = f"{model}%"
    if partner:
        matrix_params["partner"] = partner

    ref_echo = reference_date.isoformat() if reference_date else None
    cache_key = (
        f"partner_rel:{period or ''}:{ref_echo or ''}:{partner or ''}:"
        f"{process or ''}:{model or ''}:{matrix_win_echo['from']}:{matrix_win_echo['to']}"
    )
    hit = _cache.get(cache_key)
    if hit and (time.time() - hit[0]) < _CACHE_TTL_SEC:
        return hit[1]

    # 매트릭스 SQL — period 윈도우 + partner/process/model. (partner, model_full, process) GROUP BY (month 집계 X).
    matrix_sql = f"""
        SELECT {_COV_PARTNER_SQL} AS partner, p.model AS model_full, td.task_category AS process,
               COUNT(*) AS n, SUM(CASE WHEN {_TRACKED_SQL} THEN 1 ELSE 0 END) AS tracked
        FROM app_task_details td
        JOIN plan.product_info p ON p.serial_number = td.serial_number
        WHERE {_COVERAGE_BASE}{matrix_window}{proc_sql}{model_sql}{partner_sql}
          AND {_COV_PARTNER_SQL} NOT IN ('GST', 'SH', '(미지정)')
        GROUP BY 1, 2, 3
    """
    # trend SQL — trust_start~현재월 월별. process/model 적용, partner/period 제외.
    trend_params: Dict[str, Any] = {"trust_start": f"{CT_TRUST_START_MONTH}-01"}
    trend_proc = " AND td.task_category = %(process)s" if process else " AND td.task_category IN ('MECH','ELEC')"
    trend_model = " AND p.model ILIKE %(model)s" if model else ""
    if process:
        trend_params["process"] = process
    if model:
        trend_params["model"] = f"{model}%"
    trend_sql = f"""
        SELECT {_COV_PARTNER_SQL} AS partner, p.model AS model_full, td.task_category AS process,
               to_char(td.completed_at AT TIME ZONE 'Asia/Seoul', 'YYYY-MM') AS month,
               COUNT(*) AS n, SUM(CASE WHEN {_TRACKED_SQL} THEN 1 ELSE 0 END) AS tracked
        FROM app_task_details td
        JOIN plan.product_info p ON p.serial_number = td.serial_number
        WHERE {_COVERAGE_BASE}
          AND (td.completed_at AT TIME ZONE 'Asia/Seoul') >= %(trust_start)s::date
          AND (td.completed_at AT TIME ZONE 'Asia/Seoul')
              < (date_trunc('month', now() AT TIME ZONE 'Asia/Seoul') + interval '1 month')
          {trend_proc}{trend_model}
          AND {_COV_PARTNER_SQL} NOT IN ('GST', 'SH', '(미지정)')
        GROUP BY 1, 2, 3, 4
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT model_prefix FROM model_config ORDER BY LENGTH(model_prefix) DESC")
            prefixes = [r["model_prefix"] for r in cur.fetchall()]
            cur.execute(matrix_sql, matrix_params)
            matrix_rows = cur.fetchall()
            cur.execute(trend_sql, trend_params)
            trend_rows = cur.fetchall()
    finally:
        put_conn(conn)

    # ── 매트릭스 raw 누적 (pct 평균 금지) ──
    cell: Dict[tuple, List[int]] = {}   # (partner, prefix, process) -> [n, tracked]
    mp: Dict[tuple, List[int]] = {}     # (prefix, process) -> [n, tracked, batch_n]
    part: Dict[tuple, List[int]] = {}   # (partner, process) -> [n, tracked]
    for r in matrix_rows:
        pt = r["partner"]
        pf = _norm_model_prefix(r["model_full"], prefixes)
        pr = r["process"]
        n = int(r["n"])
        tracked = int(r["tracked"] or 0)
        c = cell.setdefault((pt, pf, pr), [0, 0])
        c[0] += n
        c[1] += tracked
        m = mp.setdefault((pf, pr), [0, 0, 0])
        m[0] += n
        m[1] += tracked
        if pt == "TMS(M)":
            m[2] += n
        p = part.setdefault((pt, pr), [0, 0])
        p[0] += n
        p[1] += tracked

    # ── trend raw 누적 (batch omit) ──
    tr: Dict[tuple, List[int]] = {}     # (month, partner, process) -> [n, tracked]
    for r in trend_rows:
        pt = r["partner"]
        if pt == "TMS(M)":   # batch omit (trend)
            continue
        pr = r["process"]
        t = tr.setdefault((r["month"], pt, pr), [0, 0])
        t[0] += int(r["n"])
        t[1] += int(r["tracked"] or 0)

    by_cell = [
        {"partner": pt, "model": pf, "process": pr,
         "tracking_pct": _pct(v[1], v[0]), "n": v[0], "confidence": _conf(v[0]),
         **({"batch": True} if pt == "TMS(M)" else {})}
        for (pt, pf, pr), v in cell.items() if v[0] >= 1
    ]
    by_cell.sort(key=lambda x: (x["process"], x["model"], x["partner"]))

    by_model_process = [
        {"model": pf, "process": pr,
         "tracking_pct": _pct(v[1], v[0]), "n": v[0], "batch_n": v[2], "confidence": _conf(v[0])}
        for (pf, pr), v in mp.items() if v[0] >= 1
    ]
    by_model_process.sort(key=lambda x: (x["process"], x["model"]))

    by_partner = [
        {"partner": pt, "process": pr,
         "tracking_pct": _pct(v[1], v[0]), "n": v[0], "confidence": _conf(v[0]),
         **({"batch": True} if pt == "TMS(M)" else {})}
        for (pt, pr), v in part.items() if v[0] >= 1
    ]
    by_partner.sort(key=lambda x: (x["process"], -x["tracking_pct"]))

    trend = [
        {"month": mo, "partner": pt, "process": pr,
         "tracking_pct": _pct(v[1], v[0]), "n": v[0], "confidence": _conf(v[0])}
        for (mo, pt, pr), v in tr.items() if v[0] >= 1
    ]
    trend.sort(key=lambda x: (x["month"], x["process"], x["partner"]))

    result = {
        "by_cell": by_cell,
        "by_model_process": by_model_process,
        "by_partner": by_partner,
        "trend": trend,
        "meta": {
            "gate": _GATE,
            "n_min": _N_MIN,
            "trust_start": CT_TRUST_START_MONTH,
            "whitelist": sorted(_INSTANT_WHITELIST),
            "period": period,
            "reference_date": ref_echo,
            "partner": partner,
            "matrix_window": matrix_win_echo,
            "trend_window": {"from": CT_TRUST_START_MONTH, "to": datetime.now(_KST).strftime("%Y-%m")},
            "scope": ("매트릭스=period+partner+process+model 필터 / "
                      "trend=process+model 적용·period·partner 무관(시계열). "
                      "MECH/ELEC, GST·SH 제외. batch(TMS(M))=일괄 매트릭스 합산포함·trend omit."),
            "generated_at": datetime.now(_KST).isoformat(),
        },
    }
    _cache[cache_key] = (time.time(), result)
    return result
