"""
Sprint 90-BE-C (#90, FEAT-CLOSE-TYPE-TREND-PARTNER-20260612)
협력사 차원 마감유형 월별 추이 — VIEW CloseTrendChart [비교] 오버레이 실데이터.

  GET /api/ct/close-type-trend?from=&to=&partner=&group=   (read-only, migration 0)

설계서: AGENT_TEAM_LAUNCH.md § Sprint 90-BE-C / #90 (Codex 라운드1 GO).

핵심:
  - partner×group×month × {auto, zerotap, force} (단위=건). flat series → VIEW 가 피벗.
  - zerotap 정의 = 90-BE-B(statistics_service trend) 동일: NOT whitelist AND force=FALSE
    AND (active_time_minutes<=1 OR close_reason IS NOT NULL).
  - partner = MECH→mech_partner(TMS→TMS(M)) / ELEC→elec_partner(TMS→TMS(E)), GST+SH+NULL 제외.
  - group = task_category (MECH/ELEC only — 협력사 작업, PI/QI/SI=GST 제외).
  - 빈 달 zero-fill (라인 끊김 방지). ?partner/?group = 표시 필터(서버).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import psycopg2.extras

from app.db_pool import put_conn
from app.models.worker import get_db_connection
from app.services.statistics_service import (
    CT_TRUST_START_MONTH,
    _INSTANT_WHITELIST,
    _resolve_window,
)

logger = logging.getLogger(__name__)
_KST = ZoneInfo("Asia/Seoul")

# whitelist SQL = is_instant_whitelisted 단일 정의 미러 (90-BE-B 패턴).
_WHITELIST_SQL = "(" + ",".join("'%s'" % t for t in sorted(_INSTANT_WHITELIST)) + ")"

# partner 정규화 — MECH→mech_partner / ELEC→elec_partner (TMS→TMS(M)/(E)), GST+SH+NULL 제외.
#   NULLIF 중첩 → GST/SH/빈값 → NULL → WHERE partner IS NOT NULL 로 제외 (#87 _EXCLUDED_PARTNERS 정합).
_PARTNER_SQL = (
    "NULLIF(NULLIF(NULLIF(TRIM(CASE "
    "WHEN td.task_category = 'MECH' THEN "
    "CASE WHEN p.mech_partner = 'TMS' THEN 'TMS(M)' ELSE p.mech_partner END "
    "WHEN td.task_category = 'ELEC' THEN "
    "CASE WHEN p.elec_partner = 'TMS' THEN 'TMS(E)' ELSE p.elec_partner END "
    "ELSE NULL END), ''), 'GST'), 'SH')"
)


def _month_range(from_month: str, to_month: str) -> List[str]:
    """[from, to] 월 inclusive 'YYYY-MM' 리스트 (zero-fill grid 용)."""
    y, m = int(from_month[:4]), int(from_month[5:7])
    ty, tm = int(to_month[:4]), int(to_month[5:7])
    out: List[str] = []
    while (y, m) <= (ty, tm):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


def get_close_type_trend(
    from_month: Optional[str] = None, to_month: Optional[str] = None,
    partner: Optional[str] = None, group: Optional[str] = None,
) -> Dict[str, Any]:
    """협력사×그룹×월 마감유형 추이 (auto/zerotap/force, 단위=건).

    flat series + zero-fill. ?partner/?group 미지정=전체. from/to 기본 [CT_TRUST_START_MONTH, 현재월].
    """
    fm, tm = _resolve_window(from_month, to_month)
    params = {"from_month": fm, "to_month": tm}

    sql = f"""
        WITH base AS (
            SELECT {_PARTNER_SQL} AS partner,
                   td.task_category AS grp,
                   to_char(date_trunc('month', td.completed_at AT TIME ZONE 'Asia/Seoul'), 'YYYY-MM') AS month,
                   td.close_reason, td.force_closed, td.task_id, td.active_time_minutes
            FROM app_task_details td
            JOIN plan.product_info p ON p.serial_number = td.serial_number
            WHERE td.completed_at IS NOT NULL
              AND td.task_category IN ('MECH','ELEC')
              AND td.task_id NOT IN ('TANK_MODULE','PRESSURE_TEST')
              AND COALESCE(p.customer, '') <> 'TEST CUSTOMER'
              AND td.serial_number NOT LIKE 'TEST%%'
              AND (td.completed_at AT TIME ZONE 'Asia/Seoul') >= (%(from_month)s || '-01')::date
              AND (td.completed_at AT TIME ZONE 'Asia/Seoul') <  ((%(to_month)s || '-01')::date + interval '1 month')
        )
        SELECT partner, grp, month,
               COUNT(*) FILTER (WHERE close_reason LIKE 'AUTO_CLOSED_BY_%%' AND force_closed = FALSE) AS auto,
               COUNT(*) FILTER (WHERE force_closed = TRUE) AS force,
               COUNT(*) FILTER (
                   WHERE task_id NOT IN {_WHITELIST_SQL}
                     AND COALESCE(force_closed, FALSE) = FALSE
                     AND (active_time_minutes <= 1 OR close_reason IS NOT NULL)
               ) AS zerotap
        FROM base
        WHERE partner IS NOT NULL
        GROUP BY partner, grp, month
    """

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    finally:
        put_conn(conn)

    # 관측된 (partner, group) + 월 grid → zero-fill
    months = _month_range(fm, tm)
    observed: Dict[tuple, Dict[str, Dict[str, int]]] = {}
    pg_set = set()
    for r in rows:
        key = (r["partner"], r["grp"])
        pg_set.add(key)
        observed.setdefault(key, {})[r["month"]] = {
            "auto": int(r["auto"]), "zerotap": int(r["zerotap"]), "force": int(r["force"]),
        }

    series: List[Dict[str, Any]] = []
    for (pt, gp) in sorted(pg_set):
        if partner and pt != partner:
            continue
        if group and gp != group:
            continue
        for mo in months:
            cell = observed.get((pt, gp), {}).get(mo, {"auto": 0, "zerotap": 0, "force": 0})
            series.append({
                "partner": pt, "group": gp, "month": mo,
                "auto": cell["auto"], "zerotap": cell["zerotap"], "force": cell["force"],
            })

    return {
        "series": series,
        "scope": {"partner": partner or None, "group": group or None},
        "meta": {
            "from": fm, "to": tm,
            "generated_at": datetime.now(_KST).isoformat(),
            "window": "trust",
            "note": "단위=건. auto=AUTO_CLOSED_BY_*(force_closed=FALSE) / force=force_closed=TRUE / "
                    "zerotap=NOT one-click·force=FALSE·(active≤1 또는 close_reason). GST+SH 제외. 빈 달 zero-fill.",
        },
    }
