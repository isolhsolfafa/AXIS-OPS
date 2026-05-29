"""
Sprint 71 (FEAT-MANAGER-DASHBOARD-AUTO-CLOSE-20260521) — v3.1 freeze 정합

Manager Dashboard 자동 마감 분석 — 종료 누락 task 분석 + 협력사별 추적.
설계서: AGENT_TEAM_LAUNCH.md § Sprint 71 v3.1

분류 규칙 (close_reason LIKE):
  AUTO_CLOSED_BY_FIRST_FINAL_TRIGGER:*   → 자동 (Sprint 41-D FIRST close)
  AUTO_CLOSED_BY_SECOND_FINAL_TRIGGER:*  → 자동 (Sprint 41-D SECOND close)
  MANUAL_FORCE_CLOSE                     → 수동
  SHIP_COMPLETE / ADMIN_COMPLETE / NULL  → 분류 제외 (자연 close / 출하)

모집단 3분리 (Codex Q7):
  started_task_count   = work_start_log 있는 task 자동 마감 (task-row)
  unstarted_task_count = work_start_log 없는 task 자동 마감 (task-row)
  missed_worker_count  = 종료 누락 worker 인스턴스 (worker-miss, 한 task 2명 누락 시 2)

invariant check (Codex Q-Freeze-3):
  5분포 합계 + 4 합산 invariant → InvariantViolationError raise → 500 + Sentry capture
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.db_pool import put_conn
from app.models.worker import get_db_connection

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class InvariantViolationError(Exception):
    """5분포 합계 정합 위반 — routes/dashboard.py 가 500 응답으로 변환."""

    def __init__(self, issues: List[str]):
        self.issues = issues
        super().__init__("; ".join(issues))


# ---------------------------------------------------------------------------
# Period helper
# ---------------------------------------------------------------------------

def _resolve_period_range(
    period: str,
    reference_date: Optional[date] = None,
) -> Tuple[datetime, datetime, datetime, datetime, str]:
    """period 영역 [start, end) + 직전 period [prev_start, prev_end) + label 반환.

    KST 기준 + completed_at 이 timestamptz UTC 라서 SQL 쪽에서 변환 처리.
    """
    if reference_date is None:
        reference_date = date.today()

    if period == "today":
        start = datetime.combine(reference_date, datetime.min.time())
        end = start + timedelta(days=1)
        prev_start = start - timedelta(days=1)
        prev_end = start
        label = reference_date.isoformat()
    elif period == "week":
        weekday = reference_date.weekday()
        monday = reference_date - timedelta(days=weekday)
        start = datetime.combine(monday, datetime.min.time())
        end = start + timedelta(days=7)
        prev_start = start - timedelta(days=7)
        prev_end = start
        label = f"{monday.isoformat()}~W"
    elif period == "quarter":
        q_month = ((reference_date.month - 1) // 3) * 3 + 1
        q_start = date(reference_date.year, q_month, 1)
        start = datetime.combine(q_start, datetime.min.time())
        next_q_year = q_start.year + (1 if q_month == 10 else 0)
        next_q_month = 1 if q_month == 10 else q_month + 3
        end = datetime.combine(date(next_q_year, next_q_month, 1), datetime.min.time())
        prev_q_month_total = q_month - 3 if q_month > 3 else 10
        prev_q_year = q_start.year if q_month > 3 else q_start.year - 1
        prev_start = datetime.combine(date(prev_q_year, prev_q_month_total, 1), datetime.min.time())
        prev_end = start
        label = f"{q_start.year}-Q{(q_month - 1) // 3 + 1}"
    else:  # month (default)
        m_start = date(reference_date.year, reference_date.month, 1)
        start = datetime.combine(m_start, datetime.min.time())
        if reference_date.month == 12:
            next_m = date(reference_date.year + 1, 1, 1)
        else:
            next_m = date(reference_date.year, reference_date.month + 1, 1)
        end = datetime.combine(next_m, datetime.min.time())
        if reference_date.month == 1:
            prev_m_start = date(reference_date.year - 1, 12, 1)
        else:
            prev_m_start = date(reference_date.year, reference_date.month - 1, 1)
        prev_start = datetime.combine(prev_m_start, datetime.min.time())
        prev_end = start
        label = f"{reference_date.year}-{reference_date.month:02d}"

    return start, end, prev_start, prev_end, label


def _format_delta(count: int, prev_count: int) -> str:
    """delta 영역 +N / -N / 0 형식 catch."""
    diff = count - prev_count
    if diff == 0:
        return "0"
    return f"{diff:+d}"


def _improvement_pct(count: int, prev_count: int) -> Optional[float]:
    """개선율 — prev=0 시 None (Codex 결정 2)."""
    if prev_count == 0:
        return None
    return round((prev_count - count) / prev_count * 100, 1)


def _trend(count: int, prev_count: int) -> str:
    diff = count - prev_count
    if diff > 0:
        return "increased"
    if diff < 0:
        return "decreased"
    return "unchanged"


# ---------------------------------------------------------------------------
# Partner filter (manager 자기 회사)
# ---------------------------------------------------------------------------

def _build_partner_filter(
    partner: Optional[str],
    is_admin: bool,
    worker_company: Optional[str],
) -> Tuple[str, List[Any]]:
    """manager 영역 자기 회사 catch / admin 영역 전체 또는 query partner.

    Sprint 71 v3.1 결정 6 정합 (Codex M1 fix 2026-05-28):
      - admin + partner 지정 → product_info partner OR (unstarted task 포함)
      - manager → work_start_log + workers.company (자기 회사 worker 참여 task만)
        → unstarted task 자동 제외 (work_start_log 없으니 매칭 X)
      - admin + partner 미지정 → 전체 catch

    Returns: (additional_where_sql, params_list)

    ⚠️ 호출 query 영역 `t.id` 영역 alias 의무 (subquery EXISTS catch).
    """
    if is_admin:
        if partner:
            # v2.20.11: 매트릭스 셀 ↔ details 정합 — company 결정 표준 식 (_COMPANY_SQL)
            # 으로 통일. TMS(M)/TMS(E) 구분 + '(미지정)' + 일반 협력사 모두 동일 기준.
            # (이전: category-blind OR 매칭 → 매트릭스 셀(27) vs details(327) 불일치)
            return (f" AND {_COMPANY_SQL} = %s ", [partner])
        return ("", [])
    # manager — 자기 회사 worker 참여 task (work_start_log + workers.company)
    if worker_company:
        return (
            " AND EXISTS (SELECT 1 FROM work_start_log wsl_f "
            "JOIN workers w_f ON w_f.id = wsl_f.worker_id "
            "WHERE wsl_f.task_id = t.id AND w_f.company = %s) ",
            [worker_company],
        )
    return ("", [])


# ---------------------------------------------------------------------------
# SQL helpers — Summary
# ---------------------------------------------------------------------------

_AUTO_LIKE = "AUTO_CLOSED_BY_%"
_MANUAL_EQ = "MANUAL_FORCE_CLOSE"
_UNASSIGNED = "(미지정)"  # partner 매칭 불가 (PI/QI/SI category 또는 partner NULL)

# v2.20.11: company 결정 표준 SQL 식 — matrix / details / partner_filter 공통 사용.
# 도메인 규칙 (Twin파파 2026-05-29):
#   DB partner 컬럼엔 'TMS' 단일 저장이나 의미 분리 —
#     mech_partner='TMS'        → TMS(M)  (MECH category)
#     module_outsourcing='TMS'  → TMS(M)  (TMS category)
#     elec_partner='TMS'        → TMS(E)  (ELEC category)
#   즉 ELEC 의 TMS 만 TMS(E), 나머지(MECH/TMS) 의 TMS 는 TMS(M).
# 그 외 협력사(FNI/BAT/P&S/C&A 등)는 그대로. partner NULL / PI·QI·SI → '(미지정)'.
# 표준 식 (alias t = app_task_details, pi = plan.product_info).
_COMPANY_SQL = (
    "COALESCE(NULLIF(TRIM(CASE "
    "WHEN t.task_category = 'MECH' THEN "
    "CASE WHEN pi.mech_partner = 'TMS' THEN 'TMS(M)' ELSE pi.mech_partner END "
    "WHEN t.task_category = 'ELEC' THEN "
    "CASE WHEN pi.elec_partner = 'TMS' THEN 'TMS(E)' ELSE pi.elec_partner END "
    "WHEN t.task_category = 'TMS' THEN "
    "CASE WHEN pi.module_outsourcing = 'TMS' THEN 'TMS(M)' ELSE pi.module_outsourcing END "
    "ELSE NULL END), ''), '(미지정)')"
)


def _resolve_company_py(task_category, mech_partner, elec_partner, module_outsourcing):
    """company 결정 Python 버전 (details row 후처리용 — _COMPANY_SQL 과 1:1 정합)."""
    if task_category == "MECH":
        raw = mech_partner
        if raw == "TMS":
            return "TMS(M)"
    elif task_category == "ELEC":
        raw = elec_partner
        if raw == "TMS":
            return "TMS(E)"
    elif task_category == "TMS":
        raw = module_outsourcing
        if raw == "TMS":
            return "TMS(M)"
    else:
        raw = None
    if raw is None or str(raw).strip() == "":
        return "(미지정)"
    return raw


def _query_kpi_counts(
    cur, start, end, partner_sql, partner_params
) -> Dict[str, int]:
    """auto/manual/force count + 모집단 3분리 (started/unstarted/worker-miss).

    v2.20.7 (VIEW #77): 옵션 X 채택 — force_closed=TRUE 카운트 추가.
    - auto_closed   = close_reason LIKE 'AUTO_CLOSED_BY_%' AND force_closed=FALSE
    - manual_closed = close_reason = 'MANUAL_FORCE_CLOSE' AND force_closed=FALSE (legacy, 운영 0건)
    - force_closed  = force_closed = TRUE (매니저 명시적 [강제 종료] 버튼)
    - total_missed_close = auto + manual + force 합
    """
    sql = f"""
        WITH base AS (
            SELECT t.id, t.close_reason, t.task_category, t.force_closed
            FROM app_task_details t
            LEFT JOIN plan.product_info pi ON pi.serial_number = t.serial_number
            WHERE t.completed_at >= %s AND t.completed_at < %s
              {partner_sql}
        ),
        auto AS (
            SELECT id FROM base WHERE close_reason LIKE %s AND force_closed = FALSE
        ),
        manual AS (
            SELECT id FROM base WHERE close_reason = %s AND force_closed = FALSE
        ),
        force AS (
            SELECT id FROM base WHERE force_closed = TRUE
        ),
        auto_started AS (
            SELECT DISTINCT a.id
            FROM auto a
            JOIN work_start_log wsl ON wsl.task_id = a.id
        ),
        auto_unstarted AS (
            SELECT a.id FROM auto a
            WHERE NOT EXISTS (
                SELECT 1 FROM work_start_log wsl WHERE wsl.task_id = a.id
            )
        ),
        missed_workers AS (
            SELECT wsl.task_id, wsl.worker_id
            FROM work_start_log wsl
            JOIN auto a ON a.id = wsl.task_id
            LEFT JOIN work_completion_log wcl
              ON wcl.task_id = wsl.task_id AND wcl.worker_id = wsl.worker_id
            WHERE wcl.id IS NULL
        )
        SELECT
            (SELECT COUNT(*) FROM auto) AS auto_count,
            (SELECT COUNT(*) FROM manual) AS manual_count,
            (SELECT COUNT(*) FROM force) AS force_count,
            (SELECT COUNT(*) FROM auto_started) AS started_task_count,
            (SELECT COUNT(*) FROM auto_unstarted) AS unstarted_task_count,
            (SELECT COUNT(*) FROM missed_workers) AS missed_worker_count
    """
    params = [start, end] + partner_params + [_AUTO_LIKE, _MANUAL_EQ]
    cur.execute(sql, params)
    row = cur.fetchone()
    return {
        "auto_count": int(row["auto_count"] or 0),
        "manual_count": int(row["manual_count"] or 0),
        "force_count": int(row["force_count"] or 0),
        "started_task_count": int(row["started_task_count"] or 0),
        "unstarted_task_count": int(row["unstarted_task_count"] or 0),
        "missed_worker_count": int(row["missed_worker_count"] or 0),
    }


def _query_trigger_distribution(
    cur, start, end, partner_sql, partner_params
) -> List[Dict[str, Any]]:
    """trigger_task_id 분포 — close_reason prefix 후 task_id 추출."""
    sql = f"""
        SELECT
            SUBSTRING(t.close_reason FROM ':([^:]+)$') AS trigger_task_id,
            COUNT(*) AS cnt
        FROM app_task_details t
        LEFT JOIN plan.product_info pi ON pi.serial_number = t.serial_number
        WHERE t.completed_at >= %s AND t.completed_at < %s
          AND t.close_reason LIKE %s
              AND t.force_closed = FALSE
          {partner_sql}
        GROUP BY 1
        ORDER BY cnt DESC, trigger_task_id ASC
    """
    params = [start, end, _AUTO_LIKE] + partner_params
    cur.execute(sql, params)
    rows = cur.fetchall()
    total = sum(int(r["cnt"]) for r in rows) or 1
    trigger_name_map = {
        "IF_2": "ELEC IF_2 시작",
        "TANK_DOCKING": "MECH TANK_DOCKING",
        "SELF_INSPECTION": "MECH SELF_INSPECTION 완료",
        "INSPECTION": "ELEC INSPECTION 완료",
    }
    return [
        {
            "trigger_task_id": r["trigger_task_id"] or "UNKNOWN",
            "trigger_name": trigger_name_map.get(r["trigger_task_id"], r["trigger_task_id"] or "—"),
            "count": int(r["cnt"]),
            "pct": round(int(r["cnt"]) / total * 100, 1),
        }
        for r in rows
    ]


def _query_task_distribution(
    cur, start, end, partner_sql, partner_params
) -> List[Dict[str, Any]]:
    """마감 대상 task 분포 + 평균 대비 (옵션 A: 지난 30일 일평균).

    모집단 = task-row started (work_start_log 있는 자동 마감 task).
    """
    sql = f"""
        WITH started_auto AS (
            SELECT t.task_id, t.task_name
            FROM app_task_details t
            LEFT JOIN plan.product_info pi ON pi.serial_number = t.serial_number
            WHERE t.completed_at >= %s AND t.completed_at < %s
              AND t.close_reason LIKE %s
              AND t.force_closed = FALSE
              {partner_sql}
              AND EXISTS (SELECT 1 FROM work_start_log wsl WHERE wsl.task_id = t.id)
        ),
        cur_count AS (
            SELECT task_id, task_name, COUNT(*) AS cnt
            FROM started_auto
            GROUP BY task_id, task_name
        ),
        avg_30d AS (
            SELECT t.task_id,
                   COUNT(*)::float / 30.0 AS avg_daily
            FROM app_task_details t
            WHERE t.completed_at >= (CURRENT_DATE - INTERVAL '30 days')
              AND t.completed_at < CURRENT_DATE
              AND t.close_reason LIKE %s
              AND t.force_closed = FALSE
            GROUP BY t.task_id
        )
        SELECT c.task_id, c.task_name, c.cnt,
               a.avg_daily,
               CASE
                 WHEN a.avg_daily IS NULL OR a.avg_daily = 0 THEN NULL
                 ELSE ROUND(((c.cnt / a.avg_daily) - 1) * 100)::int
               END AS avg_compare_pct
        FROM cur_count c
        LEFT JOIN avg_30d a ON a.task_id = c.task_id
        ORDER BY c.cnt DESC, c.task_id ASC
    """
    params = [start, end, _AUTO_LIKE] + partner_params + [_AUTO_LIKE]
    cur.execute(sql, params)
    rows = cur.fetchall()
    result = []
    for r in rows:
        pct = r["avg_compare_pct"]
        alert = "above_avg" if pct is not None and pct >= 50 else None
        result.append({
            "task_id": r["task_id"],
            "task_name": r["task_name"],
            "count": int(r["cnt"]),
            "avg_compare_pct": float(pct) if pct is not None else None,
            "alert": alert,
        })
    return result


def _query_partner_distribution(
    cur, start, end, partner_sql, partner_params
) -> List[Dict[str, Any]]:
    """협력사 분포 — worker-miss 모집단 (Codex Q3 + Q7).

    work_start_log 있고 work_completion_log 없는 worker 의 company 카운트.
    같은 task 2명 다른 회사 누락 시 양쪽 모두 +1.
    """
    sql = f"""
        SELECT w.company, COUNT(*) AS cnt
        FROM app_task_details t
        JOIN work_start_log wsl ON wsl.task_id = t.id
        JOIN workers w ON w.id = wsl.worker_id
        LEFT JOIN work_completion_log wcl
          ON wcl.task_id = wsl.task_id AND wcl.worker_id = wsl.worker_id
        LEFT JOIN plan.product_info pi ON pi.serial_number = t.serial_number
        WHERE t.completed_at >= %s AND t.completed_at < %s
          AND t.close_reason LIKE %s
              AND t.force_closed = FALSE
          AND wcl.id IS NULL
          {partner_sql}
        GROUP BY w.company
        ORDER BY cnt DESC, w.company ASC
    """
    params = [start, end, _AUTO_LIKE] + partner_params
    cur.execute(sql, params)
    rows = cur.fetchall()
    total = sum(int(r["cnt"]) for r in rows) or 1
    return [
        {
            "company": r["company"] or "UNKNOWN",
            "count": int(r["cnt"]),
            "pct": round(int(r["cnt"]) / total * 100, 1),
            "alert": (int(r["cnt"]) / total) >= 0.3,
        }
        for r in rows
    ]


def _query_hourly_distribution(
    cur, start, end, partner_sql, partner_params
) -> List[Dict[str, Any]]:
    """V1 — 24h backfill 강제 + KST 변환."""
    sql = f"""
        WITH hours AS (SELECT generate_series(0, 23) AS hour),
             counts AS (
                 SELECT EXTRACT(HOUR FROM t.completed_at AT TIME ZONE 'Asia/Seoul')::int AS hour,
                        COUNT(*) AS cnt
                 FROM app_task_details t
                 LEFT JOIN plan.product_info pi ON pi.serial_number = t.serial_number
                 WHERE t.completed_at >= %s AND t.completed_at < %s
                   AND t.close_reason LIKE %s
              AND t.force_closed = FALSE
                   {partner_sql}
                 GROUP BY 1
             )
        SELECT h.hour, COALESCE(c.cnt, 0)::int AS count
        FROM hours h LEFT JOIN counts c USING (hour)
        ORDER BY h.hour
    """
    params = [start, end, _AUTO_LIKE] + partner_params
    cur.execute(sql, params)
    return [{"hour": int(r["hour"]), "count": int(r["count"])} for r in cur.fetchall()]


def _query_force_close_reason_distribution(
    cur, start, end, partner_sql, partner_params
) -> List[Dict[str, Any]]:
    """v2.20.7 (VIEW #77): 강제 종료 close_reason 분포 (매니저 free-text)."""
    sql = f"""
        SELECT
            COALESCE(NULLIF(TRIM(t.close_reason), ''), '(미입력)') AS close_reason,
            COUNT(*) AS cnt
        FROM app_task_details t
        LEFT JOIN plan.product_info pi ON pi.serial_number = t.serial_number
        WHERE t.completed_at >= %s AND t.completed_at < %s
          AND t.force_closed = TRUE
          {partner_sql}
        GROUP BY 1
        ORDER BY cnt DESC, close_reason ASC
    """
    params = [start, end] + partner_params
    cur.execute(sql, params)
    return [
        {"close_reason": r["close_reason"], "count": int(r["cnt"])}
        for r in cur.fetchall()
    ]


def _query_unstarted_task_distribution(
    cur, start, end, partner_sql, partner_params
) -> List[Dict[str, Any]]:
    """미시작 자동 마감 task — work_start_log 없는 자동 마감."""
    sql = f"""
        SELECT t.task_id, t.task_name, COUNT(*) AS cnt
        FROM app_task_details t
        LEFT JOIN plan.product_info pi ON pi.serial_number = t.serial_number
        WHERE t.completed_at >= %s AND t.completed_at < %s
          AND t.close_reason LIKE %s
              AND t.force_closed = FALSE
          {partner_sql}
          AND NOT EXISTS (SELECT 1 FROM work_start_log wsl WHERE wsl.task_id = t.id)
        GROUP BY t.task_id, t.task_name
        ORDER BY cnt DESC, t.task_id ASC
    """
    params = [start, end, _AUTO_LIKE] + partner_params
    cur.execute(sql, params)
    return [
        {"task_id": r["task_id"], "task_name": r["task_name"], "count": int(r["cnt"])}
        for r in cur.fetchall()
    ]


def _query_partner_task_matrix(
    cur, start, end, partner_sql, partner_params, started_task_count: int
) -> Dict[str, Any]:
    """V6 — 협력사 × task 매트릭스 (Codex Q6 canonical + grand_total assertion).

    모집단 = task-row started — 한 task 1회 카운트, 협력사 = task_category 기반.

    v2.20.1 fix (2026-05-28 VIEW catch — Sprint 76 패턴 정합):
      - 이전: HAVING ... IS NOT NULL 영역 NULL partner 제외 → grand_total 부족
      - 이후: COALESCE(NULLIF(TRIM(partner), ''), '(미지정)') 영역 통합 group
      - PI/QI/SI category (ELSE NULL) + product_info partner NULL → '(미지정)' 분류
      - grand_total = started_task_count 정합 보장 (invariant violation 해소)
    """
    # v2.20.11: company 결정 _COMPANY_SQL 통일 (TMS(M)/TMS(E) 구분 + details/filter 정합)
    sql = f"""
        WITH started_auto AS (
            SELECT DISTINCT ON (t.id)
                t.id, t.task_id, t.task_name,
                {_COMPANY_SQL} AS company
            FROM app_task_details t
            LEFT JOIN plan.product_info pi ON pi.serial_number = t.serial_number
            WHERE t.completed_at >= %s AND t.completed_at < %s
              AND t.close_reason LIKE %s
              AND t.force_closed = FALSE
              {partner_sql}
              AND EXISTS (SELECT 1 FROM work_start_log wsl WHERE wsl.task_id = t.id)
        )
        SELECT company, task_id, task_name, COUNT(*) AS cnt
        FROM started_auto
        GROUP BY 1, task_id, task_name
        ORDER BY company, task_id
    """
    params = [start, end, _AUTO_LIKE] + partner_params
    cur.execute(sql, params)
    raw = cur.fetchall()

    # canonical task_columns (Codex Q6 — ORDER BY task_name, task_id)
    task_id_to_name = {r["task_id"]: r["task_name"] for r in raw}
    unique_tasks = sorted(
        task_id_to_name.keys(),
        key=lambda tid: (task_id_to_name[tid], tid),
    )
    task_columns = [
        {"task_id": tid, "task_name": task_id_to_name[tid]} for tid in unique_tasks
    ]
    task_idx = {tid: i for i, tid in enumerate(unique_tasks)}

    by_company: Dict[str, List[int]] = defaultdict(lambda: [0] * len(unique_tasks))
    for r in raw:
        by_company[r["company"]][task_idx[r["task_id"]]] = int(r["cnt"])

    column_totals = [
        sum(counts[i] for counts in by_company.values())
        for i in range(len(unique_tasks))
    ]
    grand_total = sum(column_totals)

    rows = []
    for c in sorted(by_company.keys()):
        counts = by_company[c]
        total = sum(counts)
        rows.append({
            "company": c,
            "counts": counts,
            "total": total,
            "alert": (total / grand_total >= 0.3) if grand_total else False,
        })

    return {
        "task_columns": task_columns,
        "rows": rows,
        "column_totals": column_totals,
        "grand_total": grand_total,
    }


# ---------------------------------------------------------------------------
# Invariant check (Codex Q-Freeze-3)
# ---------------------------------------------------------------------------

def _assert_invariants(response: Dict[str, Any]) -> None:
    """5분포 합계 + 4 합산 invariant 검증. 위반 시 InvariantViolationError."""
    ac = response["auto_closed"]
    mc = response["manual_closed"]
    tm = response["total_missed_close"]
    issues: List[str] = []

    if ac["count"] != ac["started_task_count"] + ac["unstarted_task_count"]:
        issues.append(
            f"auto_closed.count {ac['count']} != started+unstarted "
            f"{ac['started_task_count'] + ac['unstarted_task_count']}"
        )

    td_sum = sum(t["count"] for t in response.get("task_distribution", []))
    if td_sum != ac["started_task_count"]:
        issues.append(
            f"task_distribution sum {td_sum} != started_task_count {ac['started_task_count']}"
        )

    pd_sum = sum(p["count"] for p in response.get("partner_distribution", []))
    if pd_sum != ac["missed_worker_count"]:
        issues.append(
            f"partner_distribution sum {pd_sum} != missed_worker_count {ac['missed_worker_count']}"
        )

    gt = response.get("partner_task_matrix", {}).get("grand_total", 0)
    if gt != ac["started_task_count"]:
        issues.append(
            f"partner_task_matrix.grand_total {gt} != started_task_count {ac['started_task_count']}"
        )

    hd_sum = sum(h["count"] for h in response.get("hourly_distribution", []))
    if hd_sum != ac["count"]:
        issues.append(
            f"hourly_distribution sum {hd_sum} != auto_closed.count {ac['count']}"
        )

    ud_sum = sum(u["count"] for u in response.get("unstarted_task_distribution", []))
    if ud_sum != ac["unstarted_task_count"]:
        issues.append(
            f"unstarted_task_distribution sum {ud_sum} != unstarted_task_count "
            f"{ac['unstarted_task_count']}"
        )

    # total_missed_close 4 invariant
    # v2.20.7 (#77): force_closed 합산 추가 — total = auto + manual + force
    fc = response.get("force_closed", {"count": 0, "prev_period_count": 0})
    expected_total = ac["count"] + mc["count"] + fc.get("count", 0)
    if tm["count"] != expected_total:
        issues.append(
            f"total_missed_close.count {tm['count']} != auto+manual+force "
            f"{expected_total}"
        )
    expected_prev = (
        ac["prev_period_count"] + mc["prev_period_count"]
        + fc.get("prev_period_count", 0)
    )
    if tm["prev_period_count"] != expected_prev:
        issues.append(
            f"total_missed_close.prev {tm['prev_period_count']} != "
            f"auto.prev+manual.prev+force.prev {expected_prev}"
        )
    expected_delta = _format_delta(tm["count"], tm["prev_period_count"])
    if tm["delta"] != expected_delta:
        issues.append(
            f"total_missed_close.delta {tm['delta']} != expected {expected_delta}"
        )
    if tm["prev_period_count"] == 0 and tm.get("improvement_pct") is not None:
        issues.append(
            f"total_missed_close.improvement_pct must be None when prev=0, "
            f"got {tm.get('improvement_pct')}"
        )

    if issues:
        logger.error(
            "[Sprint71] invariant violation: %s",
            "; ".join(issues),
            extra={"period": response.get("period")},
        )
        try:
            import sentry_sdk
            sentry_sdk.capture_message(
                "Sprint71 invariant violation",
                level="error",
                extras={"issues": issues, "period": response.get("period")},
            )
        except Exception:
            pass
        raise InvariantViolationError(issues)


# ---------------------------------------------------------------------------
# Main builders
# ---------------------------------------------------------------------------

def build_auto_close_summary(
    period: str = "month",
    partner: Optional[str] = None,
    reference_date: Optional[date] = None,
    is_admin: bool = False,
    worker_company: Optional[str] = None,
) -> Dict[str, Any]:
    """`/auto-close-summary` 응답 본문 구성."""
    start, end, prev_start, prev_end, label = _resolve_period_range(period, reference_date)
    partner_sql, partner_params = _build_partner_filter(partner, is_admin, worker_company)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur_kpi = _query_kpi_counts(cur, start, end, partner_sql, partner_params)
            prev_kpi = _query_kpi_counts(cur, prev_start, prev_end, partner_sql, partner_params)

            trigger_distribution = _query_trigger_distribution(
                cur, start, end, partner_sql, partner_params
            )
            task_distribution = _query_task_distribution(
                cur, start, end, partner_sql, partner_params
            )
            partner_distribution = _query_partner_distribution(
                cur, start, end, partner_sql, partner_params
            )
            hourly_distribution = _query_hourly_distribution(
                cur, start, end, partner_sql, partner_params
            )
            unstarted_task_distribution = _query_unstarted_task_distribution(
                cur, start, end, partner_sql, partner_params
            )
            partner_task_matrix = _query_partner_task_matrix(
                cur, start, end, partner_sql, partner_params,
                cur_kpi["started_task_count"],
            )
            # v2.20.7 (#77): 강제 종료 close_reason 분포
            force_close_reason_distribution = _query_force_close_reason_distribution(
                cur, start, end, partner_sql, partner_params
            )
    finally:
        put_conn(conn)

    auto_count = cur_kpi["auto_count"]
    manual_count = cur_kpi["manual_count"]
    force_count = cur_kpi["force_count"]
    # v2.20.7 (#77): total = auto + manual + force
    total_count = auto_count + manual_count + force_count
    prev_total = prev_kpi["auto_count"] + prev_kpi["manual_count"] + prev_kpi["force_count"]

    response: Dict[str, Any] = {
        "period": label,
        "auto_closed": {
            "count": auto_count,
            "started_task_count": cur_kpi["started_task_count"],
            "missed_worker_count": cur_kpi["missed_worker_count"],
            "unstarted_task_count": cur_kpi["unstarted_task_count"],
            "prev_period_count": prev_kpi["auto_count"],
            "delta": _format_delta(auto_count, prev_kpi["auto_count"]),
            "trend": _trend(auto_count, prev_kpi["auto_count"]),
        },
        "manual_closed": {
            "count": manual_count,
            "prev_period_count": prev_kpi["manual_count"],
            "delta": _format_delta(manual_count, prev_kpi["manual_count"]),
            "improvement_pct": _improvement_pct(manual_count, prev_kpi["manual_count"]),
        },
        # v2.20.7 (#77): 강제 종료 block (옵션 X — force_closed=TRUE only)
        "force_closed": {
            "count": force_count,
            "prev_period_count": prev_kpi["force_count"],
            "delta": _format_delta(force_count, prev_kpi["force_count"]),
            "trend": _trend(force_count, prev_kpi["force_count"]),
            "improvement_pct": _improvement_pct(force_count, prev_kpi["force_count"]),
            "by_reason": force_close_reason_distribution,
        },
        "total_missed_close": {
            "count": total_count,
            "prev_period_count": prev_total,
            "delta": _format_delta(total_count, prev_total),
            "trend": _trend(total_count, prev_total),
            "improvement_pct": _improvement_pct(total_count, prev_total),
        },
        "trigger_distribution": trigger_distribution,
        "task_distribution": task_distribution,
        "partner_distribution": partner_distribution,
        "hourly_distribution": hourly_distribution,
        "unstarted_task_distribution": unstarted_task_distribution,
        "partner_task_matrix": partner_task_matrix,
    }

    _assert_invariants(response)
    return response


def build_auto_close_details(
    period: str = "today",
    partner: Optional[str] = None,
    trigger_task_id: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    is_admin: bool = False,
    worker_company: Optional[str] = None,
    reference_date: Optional[date] = None,
) -> Dict[str, Any]:
    """`/auto-close-details` 응답 본문 구성 (drill-down 상세 카드)."""
    start, end, _, _, _ = _resolve_period_range(period, reference_date)
    partner_sql, partner_params = _build_partner_filter(partner, is_admin, worker_company)

    trigger_sql = ""
    trigger_params: List[Any] = []
    if trigger_task_id:
        trigger_sql = " AND t.close_reason LIKE %s "
        trigger_params = [f"%:{trigger_task_id}"]

    page = max(1, page)
    per_page = max(1, min(100, per_page))
    offset = (page - 1) * per_page

    # v2.20.7 (#77): 분류 영역 — auto / manual / force 합집합 (총 종료 누락)
    # close_filter: (AUTO_CLOSED_BY_% AND force=FALSE) OR (MANUAL_FORCE_CLOSE AND force=FALSE) OR (force=TRUE)
    close_filter = (
        "((t.close_reason LIKE %s AND t.force_closed = FALSE) "
        "OR (t.close_reason = %s AND t.force_closed = FALSE) "
        "OR t.force_closed = TRUE)"
    )
    close_filter_params = [_AUTO_LIKE, _MANUAL_EQ]

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            count_sql = f"""
                SELECT COUNT(*) AS total
                FROM app_task_details t
                LEFT JOIN plan.product_info pi ON pi.serial_number = t.serial_number
                WHERE t.completed_at >= %s AND t.completed_at < %s
                  AND {close_filter}
                  {partner_sql}
                  {trigger_sql}
            """
            cur.execute(
                count_sql,
                [start, end] + close_filter_params + partner_params + trigger_params,
            )
            total = int(cur.fetchone()["total"] or 0)

            # v2.20.6 fix (VIEW #76 HOTFIX, 2026-05-29): plan.product_info alias 영역
            # count_sql (pi) 과 item_sql (p) 불일치 → partner_sql 의 하드코딩 pi.mech_partner
            # 가 item_sql 안에서 undefined alias → 500. alias 'pi' 로 통일.
            # v2.20.6 (#76 fix): plan.product_info alias 'pi' 통일
            # v2.20.7 (#77): close_filter + force_closed / closed_by 컬럼 추가
            item_sql = f"""
                SELECT
                    t.id AS task_detail_id,
                    t.completed_at, t.serial_number, t.task_id, t.task_name,
                    t.close_reason, t.duration_minutes, t.elapsed_minutes,
                    t.task_category,
                    t.force_closed, t.closed_by,
                    pi.model, pi.sales_order,
                    w_trigger.id AS trigger_worker_id,
                    w_trigger.name AS trigger_worker_name,
                    w_trigger.company AS trigger_worker_company,
                    pi.mech_partner, pi.elec_partner, pi.module_outsourcing,
                    (SELECT json_agg(json_build_object(
                        'worker_id', wsl.worker_id,
                        'worker_name', w_orig.name,
                        'company', w_orig.company,
                        'status', '종료 누락'
                      ))
                     FROM work_start_log wsl
                     LEFT JOIN workers w_orig ON w_orig.id = wsl.worker_id
                     LEFT JOIN work_completion_log wcl
                       ON wcl.task_id = wsl.task_id AND wcl.worker_id = wsl.worker_id
                     WHERE wsl.task_id = t.id AND wcl.id IS NULL
                    ) AS original_workers
                FROM app_task_details t
                LEFT JOIN plan.product_info pi ON pi.serial_number = t.serial_number
                LEFT JOIN workers w_trigger ON w_trigger.id = t.closed_by
                WHERE t.completed_at >= %s AND t.completed_at < %s
                  AND {close_filter}
                  {partner_sql}
                  {trigger_sql}
                ORDER BY t.completed_at DESC
                LIMIT %s OFFSET %s
            """
            cur.execute(
                item_sql,
                [start, end] + close_filter_params + partner_params + trigger_params + [per_page, offset],
            )
            rows = cur.fetchall()
    finally:
        put_conn(conn)

    items = []
    for r in rows:
        # company 결정 — _resolve_company_py (_COMPANY_SQL 과 1:1 정합)
        # v2.20.11: TMS(M)/TMS(E) 구분 (mech/module TMS → TMS(M), elec TMS → TMS(E))
        company = _resolve_company_py(
            r["task_category"], r["mech_partner"],
            r["elec_partner"], r["module_outsourcing"],
        )

        # trigger task_id 추출
        trigger_tid = None
        if r["close_reason"] and ":" in r["close_reason"]:
            trigger_tid = r["close_reason"].rsplit(":", 1)[-1]

        # v2.20.7 (#77): close_type 분류
        if r.get("force_closed"):
            close_type = "force"
        elif r["close_reason"] and r["close_reason"].startswith("AUTO_CLOSED_BY_"):
            close_type = "auto"
        elif r["close_reason"] == "MANUAL_FORCE_CLOSE":
            close_type = "manual"
        else:
            close_type = "auto"  # 보수적 fallback

        items.append({
            "task_detail_id": r["task_detail_id"],
            "closed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
            "serial_number": r["serial_number"],
            "model": r["model"],
            "sales_order": r["sales_order"],
            "company": company,
            "close_type": close_type,
            "closed_tasks": [{"task_id": r["task_id"], "task_name": r["task_name"]}],
            "task_count": 1,
            "trigger": {
                "task_id": trigger_tid,
                "task_name": trigger_tid,
                "worker_id": r["trigger_worker_id"],
                "worker_name": r["trigger_worker_name"],
                "company": r["trigger_worker_company"],
            },
            "original_workers": r["original_workers"] or [],
            "close_reason": r["close_reason"],
            "duration_minutes": r["duration_minutes"],
            "elapsed_minutes": r["elapsed_minutes"],
            "duration_status": "normal",
            "duration_validator_alerts": [],
        })

    total_pages = (total + per_page - 1) // per_page if per_page else 1
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }
