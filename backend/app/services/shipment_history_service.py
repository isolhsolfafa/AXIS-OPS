"""
출하이력 페이지 BE service (Sprint 76-BE, v2.18.28)

read-only 출하 이력 조회 + 집계. mutation 영역 (ship-complete) 은 별도 shipment_service.py.

설계서: AGENT_TEAM_LAUNCH.md § Sprint 76-BE
Codex 라운드 1 (VIEW 5-26, M=7/A=2) + 라운드 2 (OPS 5-26, M=5/A=2/N=1) 모두 반영.

핵심:
- best_ship CTE = factory.py _count_shipped(basis='best') 와 동일 패턴 (단일 best 정의)
- 반개구간 (>= AND <) 사용 — 월말/월초 중복 회피 (Codex Q5 M)
- N+1 방지 — top_delayed 5건 batch 조회 (Codex Q3 M)
- invariant 3건 — calendar plan / by_customer plan / by_customer shipped (Codex Q8 M)
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.db_pool import get_conn, put_conn

logger = logging.getLogger(__name__)

# Sprint 71 close_reason → friendly root_cause 변환 (Codex Q3 M)
CATEGORY_KO = {
    'MECH': '기구',
    'ELEC': '전장',
    'TM': '모듈',
    'PI': 'PI',
    'QI': 'QI',
    'SI': 'SI',
}


class InvariantViolationError(Exception):
    """Sprint 76 응답 정합 검증 실패 — 500 + Sentry capture."""
    def __init__(self, issues: List[str]):
        self.issues = issues
        super().__init__("; ".join(issues))


def _resolve_period_range(
    period: str,
    reference_date: Optional[str] = None,
) -> Tuple[date, date]:
    """period + reference_date → (start, end_exclusive) 반개구간.

    Codex Q5 M — `>= start AND < end_exclusive` 사용 (BETWEEN 월말 중복 회피).
    """
    if reference_date:
        try:
            ref = datetime.strptime(reference_date, '%Y-%m-%d').date()
        except ValueError:
            ref = date.today()
    else:
        ref = date.today()

    if period == 'month':
        start = ref.replace(day=1)
        # 다음 월 1일
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
    elif period == 'quarter':
        q = (ref.month - 1) // 3
        start = ref.replace(month=q * 3 + 1, day=1)
        # 다음 분기 1일
        if q == 3:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=q * 3 + 4)
    elif period == 'year':
        start = ref.replace(month=1, day=1)
        end = start.replace(year=start.year + 1)
    else:
        raise ValueError(f"Invalid period: {period} (must be 'month' | 'quarter' | 'year')")

    return start, end


def _best_ship_sql_select() -> str:
    """best_ship CTE SELECT 절 (재사용).

    factory.py _count_shipped(basis='best') 와 동일 패턴.
    SI_SHIPMENT only + force_closed=FALSE (OPS #70 v2.18.4 정합).

    v2.18.30 (사용자 catch 5-26): model source = `p.model` 칼럼 (분류 이름).
    `product_code` 는 숫자 SKU (예: '41200152') — by_model 그룹핑에 부적합.
    `model` 은 분류 이름 (예: 'GAIA-I DUAL') — 매니저 직관 + NOT NULL constraint 보장.
    운영 2026 1199건 검증: product_code/model 다른 값 1194건 (의미 완전 분리).
    """
    return """
        p.serial_number,
        p.sales_order,
        p.model AS model,
        p.customer,
        p.mech_partner AS partner_mech,
        p.elec_partner AS partner_elec,
        p.ship_plan_date AS plan_date,
        COALESCE(
            (SELECT DATE(t.completed_at)
             FROM app_task_details t
             WHERE t.serial_number = p.serial_number
               AND t.task_id = 'SI_SHIPMENT'
               AND t.completed_at IS NOT NULL
               AND COALESCE(t.force_closed, FALSE) = FALSE
             ORDER BY t.completed_at DESC LIMIT 1),
            p.actual_ship_date
        ) AS actual_date,
        CASE
            WHEN EXISTS (
                SELECT 1 FROM app_task_details t
                WHERE t.serial_number = p.serial_number
                  AND t.task_id = 'SI_SHIPMENT'
                  AND t.completed_at IS NOT NULL
                  AND COALESCE(t.force_closed, FALSE) = FALSE
            ) AND p.actual_ship_date IS NOT NULL THEN 'both'
            WHEN EXISTS (
                SELECT 1 FROM app_task_details t
                WHERE t.serial_number = p.serial_number
                  AND t.task_id = 'SI_SHIPMENT'
                  AND t.completed_at IS NOT NULL
                  AND COALESCE(t.force_closed, FALSE) = FALSE
            ) THEN 'app'
            WHEN p.actual_ship_date IS NOT NULL THEN 'excel'
            ELSE NULL
        END AS source
    """


def _build_best_ship_cte(start: date, end: date) -> Tuple[str, Tuple]:
    """best_ship CTE 빌더 (반개구간 정합).

    v2.18.32 (사용자 catch 5-27): TEST CUSTOMER 제외 (factory.py v2.15.21 #69 패턴 정합).
    TEST 데이터 (TEST-1112~1116, customer='TEST CUSTOMER', model='GAIA', plan=5/shipped=0)
    영역 운영 정합도 catch — 5월 영역 153 → 148 정정 (fulfillment 79.7% → 82.4%).

    Returns:
        (sql_with_cte, params) 튜플.
    """
    cte = f"""
        WITH best_ship AS (
            SELECT {_best_ship_sql_select()}
            FROM plan.product_info p
            WHERE COALESCE(p.customer, '') <> 'TEST CUSTOMER'
              AND (p.ship_plan_date >= %s AND p.ship_plan_date < %s
                   OR p.actual_ship_date >= %s AND p.actual_ship_date < %s
                   OR EXISTS (
                       SELECT 1 FROM app_task_details t
                       WHERE t.serial_number = p.serial_number
                         AND t.task_id = 'SI_SHIPMENT'
                         AND COALESCE(t.force_closed, FALSE) = FALSE
                         AND DATE(t.completed_at) >= %s
                         AND DATE(t.completed_at) < %s
                   ))
        )
    """
    params = (start, end, start, end, start, end)
    return cte, params


def _fetch_plan_change_warning(cur, start: date, end: date) -> Dict[str, Any]:
    """계획 변경 hint (v2.18.33 사용자 catch — 자기 충족 catch 신호).

    fulfillment_pct / avg_delay_days 영역 "계획일 수정 시 100% 정시 트릭" 영역 catch.
    etl.change_log 영역 `field_name = 'ship_plan_date'` 영역 변경 횟수 catch.

    5월 운영 검증 (5-27): 148건 중 89건 (60%) ship_plan_date 변경됨 — catch 정합.

    ⚠️ etl.change_log 영역 test DB 영역 없음 — try/except fallback (운영 안전망).

    Returns:
        { count: int, share_pct: float, hint: str }
    """
    # 2단계 SQL — etl.change_log 영역 존재 catch 후 분기
    # (PostgreSQL CASE WHEN lazy eval 안 됨 — parse 시점 reference catch 회피)
    cur.execute("SELECT to_regclass('etl.change_log') IS NOT NULL AS has_table")
    has_etl_change_log = cur.fetchone()['has_table']

    # total plan_count 영역 항상 catch
    cur.execute(
        """
        SELECT COUNT(*) AS total
        FROM plan.product_info p
        WHERE p.ship_plan_date >= %s AND p.ship_plan_date < %s
          AND COALESCE(p.customer, '') <> 'TEST CUSTOMER'
        """,
        (start, end),
    )
    total = int(cur.fetchone()['total'] or 0)

    # etl.change_log 영역 있으면 변경 catch, 없으면 0
    changed = 0
    if has_etl_change_log:
        cur.execute(
            """
            SELECT COUNT(DISTINCT cl.serial_number) AS changed
            FROM etl.change_log cl
            WHERE cl.field_name = 'ship_plan_date'
              AND cl.serial_number IN (
                  SELECT p.serial_number FROM plan.product_info p
                  WHERE p.ship_plan_date >= %s AND p.ship_plan_date < %s
                    AND COALESCE(p.customer, '') <> 'TEST CUSTOMER'
              )
            """,
            (start, end),
        )
        changed = int(cur.fetchone()['changed'] or 0)
    share = round(100.0 * changed / total, 1) if total > 0 else 0.0

    return {
        'count': changed,
        'share_pct': share,
        'hint': (
            f"{changed}건 계획 변경됨 (전체 {total}건 중 {share}%) — "
            f"납기 준수율/평균 지연 영역 자기 충족 catch 가능"
            if changed > 0 else None
        ),
    }


def _fetch_kpi(cur, start: date, end: date) -> Dict[str, Any]:
    """KPI 6 — plan/shipped/fulfillment/on_time/pending/avg_delay (Codex Q2/Q3 M)."""
    cte, params = _build_best_ship_cte(start, end)
    sql = cte + """
        SELECT
            COUNT(*) FILTER (WHERE plan_date >= %s AND plan_date < %s) AS plan_count,
            COUNT(*) FILTER (WHERE actual_date IS NOT NULL
                              AND actual_date >= %s AND actual_date < %s) AS shipped_count,
            ROUND(100.0 * COUNT(*) FILTER (WHERE plan_date >= %s AND plan_date < %s
                                            AND actual_date IS NOT NULL)
                        / NULLIF(COUNT(*) FILTER (WHERE plan_date >= %s AND plan_date < %s), 0), 1)
                                                                            AS fulfillment_pct,
            ROUND(100.0 * COUNT(*) FILTER (WHERE actual_date IS NOT NULL
                                            AND actual_date <= plan_date)
                        / NULLIF(COUNT(*) FILTER (WHERE actual_date IS NOT NULL), 0), 1)
                                                                            AS on_time_pct,
            COUNT(*) FILTER (WHERE actual_date IS NULL
                              AND plan_date >= CURRENT_DATE
                              AND plan_date >= %s AND plan_date < %s)        AS pending_count,
            ROUND((AVG(actual_date - plan_date)
                   FILTER (WHERE actual_date IS NOT NULL))::numeric, 1)      AS avg_delay_days
        FROM best_ship;
    """
    cur.execute(sql, params + (start, end, start, end, start, end, start, end, start, end))
    row = cur.fetchone()
    if row is None:
        return {
            'plan_count': 0, 'shipped_count': 0,
            'fulfillment_pct': None, 'on_time_pct': None,
            'pending_count': 0, 'avg_delay_days': None,
        }
    return {
        'plan_count': int(row['plan_count'] or 0),
        'shipped_count': int(row['shipped_count'] or 0),
        'fulfillment_pct': float(row['fulfillment_pct']) if row['fulfillment_pct'] is not None else None,
        'on_time_pct': float(row['on_time_pct']) if row['on_time_pct'] is not None else None,
        'pending_count': int(row['pending_count'] or 0),
        'avg_delay_days': float(row['avg_delay_days']) if row['avg_delay_days'] is not None else None,
    }


def _fetch_calendar(cur, start: date, end: date) -> List[Dict[str, Any]]:
    """캘린더 (Codex Q4 M — 두 쿼리 분리 + BE merge)."""
    cte, params = _build_best_ship_cte(start, end)

    # Query 1: plan
    sql_plan = cte + """
        SELECT plan_date AS date, COUNT(*) AS plan
        FROM best_ship
        WHERE plan_date >= %s AND plan_date < %s
        GROUP BY plan_date;
    """
    cur.execute(sql_plan, params + (start, end))
    plan_rows = {r['date']: int(r['plan']) for r in cur.fetchall()}

    # Query 2: shipped (반개구간)
    sql_shipped = cte + """
        SELECT actual_date AS date, COUNT(*) AS shipped
        FROM best_ship
        WHERE actual_date IS NOT NULL
          AND actual_date >= %s AND actual_date < %s
        GROUP BY actual_date;
    """
    cur.execute(sql_shipped, params + (start, end))
    shipped_rows = {r['date']: int(r['shipped']) for r in cur.fetchall()}

    # BE merge
    all_dates = sorted(set(plan_rows.keys()) | set(shipped_rows.keys()))
    return [
        {
            'date': d.isoformat(),
            'plan': plan_rows.get(d, 0),
            'shipped': shipped_rows.get(d, 0),
        }
        for d in all_dates
    ]


def _fetch_by_customer(cur, start: date, end: date) -> List[Dict[str, Any]]:
    """by_customer — 고객사별 plan / shipped / fulfillment / on_time / share."""
    cte, params = _build_best_ship_cte(start, end)
    sql = cte + """
        SELECT
            customer,
            COUNT(*) FILTER (WHERE plan_date >= %s AND plan_date < %s) AS plan,
            COUNT(*) FILTER (WHERE actual_date IS NOT NULL
                              AND actual_date >= %s AND actual_date < %s) AS shipped,
            ROUND(100.0 * COUNT(*) FILTER (WHERE plan_date >= %s AND plan_date < %s
                                            AND actual_date IS NOT NULL)
                        / NULLIF(COUNT(*) FILTER (WHERE plan_date >= %s AND plan_date < %s), 0), 1)
                                                                            AS fulfillment_pct,
            ROUND(100.0 * COUNT(*) FILTER (WHERE actual_date IS NOT NULL
                                            AND actual_date <= plan_date)
                        / NULLIF(COUNT(*) FILTER (WHERE actual_date IS NOT NULL), 0), 1)
                                                                            AS on_time_pct
        FROM best_ship
        WHERE customer IS NOT NULL
        GROUP BY customer
        ORDER BY plan DESC, customer ASC;
    """
    cur.execute(sql, params + (start, end, start, end, start, end, start, end))
    rows = cur.fetchall()
    # share_pct 후처리
    total_plan = sum(int(r['plan'] or 0) for r in rows)
    return [
        {
            'customer': r['customer'],
            'plan': int(r['plan'] or 0),
            'shipped': int(r['shipped'] or 0),
            'fulfillment_pct': float(r['fulfillment_pct']) if r['fulfillment_pct'] is not None else None,
            'on_time_pct': float(r['on_time_pct']) if r['on_time_pct'] is not None else None,
            'share_pct': round(100.0 * int(r['plan'] or 0) / total_plan, 1) if total_plan > 0 else 0.0,
        }
        for r in rows
    ]


def _fetch_by_model(cur, start: date, end: date) -> List[Dict[str, Any]]:
    """by_model — 모델별 plan/shipped 분리 + avg_lead_time_days (Sprint 76-BE v2.18.29).

    옵션 C — by_customer 영역과 동일 패턴 (plan + shipped 분리):
    - plan = ship_plan_date 기준 (Master Plan ETL)
    - shipped = best 패턴 (factory.py _count_shipped basis='best' 정합)
    - share_pct = plan 기준 (by_customer 영역 정합)
    - avg_lead_time_days = P-v3 standard (협력사 작업 lead, Plan ETL 기준)
        AVG(pi_start - LEAST(elec_start, mech_start))
        · 시작 = elec_start (실 운영 1352/1357 정합) + mech_first 예외 5건 catch
        · 끝 = pi_start (협력사 작업 끝 = 검사 진입)
        · ship_plan_date 변동 영향 0 (standard value)
    """
    cte, params = _build_best_ship_cte(start, end)
    sql = cte + """
        SELECT
            b.model,
            COUNT(*) FILTER (WHERE b.plan_date >= %s AND b.plan_date < %s) AS plan_count,
            COUNT(*) FILTER (WHERE b.actual_date IS NOT NULL
                              AND b.actual_date >= %s AND b.actual_date < %s) AS shipped_count,
            ROUND((AVG(p.pi_start - LEAST(p.elec_start, p.mech_start))
                   FILTER (WHERE p.pi_start IS NOT NULL
                            AND (p.elec_start IS NOT NULL OR p.mech_start IS NOT NULL)))::numeric, 1)
                                                                              AS avg_lead_time_days
        FROM best_ship b
        JOIN plan.product_info p ON p.serial_number = b.serial_number
        WHERE b.model IS NOT NULL
        GROUP BY b.model
        ORDER BY plan_count DESC, b.model ASC;
    """
    cur.execute(sql, params + (start, end, start, end))
    rows = cur.fetchall()
    total_plan = sum(int(r['plan_count'] or 0) for r in rows)
    return [
        {
            'model': r['model'],
            'plan': int(r['plan_count'] or 0),
            'shipped': int(r['shipped_count'] or 0),
            'share_pct': round(100.0 * int(r['plan_count'] or 0) / total_plan, 1) if total_plan > 0 else 0.0,
            'avg_lead_time_days': float(r['avg_lead_time_days']) if r['avg_lead_time_days'] is not None else None,
        }
        for r in rows
    ]


def _fetch_monthly_trend(cur, reference_date: date) -> List[Dict[str, Any]]:
    """Monthly Trend — current-month 포함 trailing 6개월 (Codex Q5 M).

    plan/shipped 분리 집계 (4월 plan / 5월 shipped 각 month 분리).
    """
    # reference month 의 1일 ~ 5개월 전 1일
    cur_month_start = reference_date.replace(day=1)
    # 5개월 전 1일
    if cur_month_start.month <= 5:
        start_month = cur_month_start.replace(
            year=cur_month_start.year - 1,
            month=cur_month_start.month + 12 - 5,
        )
    else:
        start_month = cur_month_start.replace(month=cur_month_start.month - 5)

    # 다음 월 1일 (end exclusive)
    if cur_month_start.month == 12:
        end_month = cur_month_start.replace(year=cur_month_start.year + 1, month=1)
    else:
        end_month = cur_month_start.replace(month=cur_month_start.month + 1)

    # Query 1: 월별 plan (v2.18.32: TEST CUSTOMER 제외)
    cur.execute(
        """
        SELECT DATE_TRUNC('month', ship_plan_date)::date AS month, COUNT(*) AS plan
        FROM plan.product_info
        WHERE ship_plan_date >= %s AND ship_plan_date < %s
          AND COALESCE(customer, '') <> 'TEST CUSTOMER'
        GROUP BY month;
        """,
        (start_month, end_month),
    )
    plan_rows = {r['month']: int(r['plan']) for r in cur.fetchall()}

    # Query 2: 월별 shipped (best 합집합, 6개월 범위)
    cte, params = _build_best_ship_cte(start_month, end_month)
    sql_shipped = cte + """
        SELECT DATE_TRUNC('month', actual_date)::date AS month, COUNT(*) AS shipped
        FROM best_ship
        WHERE actual_date IS NOT NULL
          AND actual_date >= %s AND actual_date < %s
        GROUP BY month;
    """
    cur.execute(sql_shipped, params + (start_month, end_month))
    shipped_rows = {r['month']: int(r['shipped']) for r in cur.fetchall()}

    # 6 month zero-fill
    result = []
    month_cursor = start_month
    while month_cursor < end_month:
        result.append({
            'month': month_cursor.strftime('%Y-%m'),
            'plan': plan_rows.get(month_cursor, 0),
            'shipped': shipped_rows.get(month_cursor, 0),
        })
        if month_cursor.month == 12:
            month_cursor = month_cursor.replace(year=month_cursor.year + 1, month=1)
        else:
            month_cursor = month_cursor.replace(month=month_cursor.month + 1)
    return result


def format_root_cause(close_reason: Optional[str], task_category: Optional[str]) -> Optional[str]:
    """Sprint 71 close_reason → friendly root_cause 변환 (Codex Q3 M).

    Args:
        close_reason: 'AUTO_CLOSED_BY_FIRST_FINAL_TRIGGER:IF_2' 형식 또는 None
        task_category: DB 조회 'MECH' / 'ELEC' / 'TM' / 'PI' / 'QI' / 'SI'

    Returns:
        '<task_id> (<카테고리>) 종료 지연' 또는 None (FE 블러)
    """
    if not close_reason or not task_category:
        return None
    if ':' not in close_reason:
        return None
    task_id = close_reason.split(':', 1)[1]
    category_ko = CATEGORY_KO.get(task_category, task_category)
    return f"{task_id} ({category_ko}) 종료 지연"


def _fetch_top_delayed(cur, start: date, end: date) -> List[Dict[str, Any]]:
    """Top 5 지연 출하 + root_cause (Codex Q3 M — batch 조회).

    1) best_ship 영역 delay > 0 Top 5 조회
    2) 5건 S/N batch — `WHERE serial_number = ANY(%s)` 1회 조회로 close_reason + task_category
    """
    cte, params = _build_best_ship_cte(start, end)
    sql = cte + """
        SELECT serial_number, sales_order, model, customer,
               (actual_date - plan_date) AS delay_days
        FROM best_ship
        WHERE actual_date IS NOT NULL
          AND plan_date IS NOT NULL
          AND actual_date > plan_date
        ORDER BY delay_days DESC, serial_number ASC
        LIMIT 5;
    """
    cur.execute(sql, params)
    delayed_rows = cur.fetchall()

    if not delayed_rows:
        return []

    sn_list = [r['serial_number'] for r in delayed_rows]

    # batch 조회 — N+1 회피
    cur.execute(
        """
        SELECT DISTINCT ON (t.serial_number)
               t.serial_number, t.close_reason, t.task_category
        FROM app_task_details t
        WHERE t.serial_number = ANY(%s::text[])
          AND t.close_reason LIKE 'AUTO_CLOSED_BY_%%'
        ORDER BY t.serial_number, t.completed_at DESC;
        """,
        (sn_list,),
    )
    reason_map = {
        r['serial_number']: (r['close_reason'], r['task_category'])
        for r in cur.fetchall()
    }

    return [
        {
            'serial_number': r['serial_number'],
            'sales_order': r['sales_order'],
            'model': r['model'],
            'customer': r['customer'],
            'delay_days': int(r['delay_days']),
            'root_cause': format_root_cause(*reason_map.get(r['serial_number'], (None, None))),
        }
        for r in delayed_rows
    ]


def _assert_invariants(response: Dict[str, Any]) -> None:
    """Sprint 76 출하이력 응답 정합 검증 (Codex Q8 M).

    실패 시 InvariantViolationError → routes 가 500 + Sentry capture.
    """
    kpi = response['kpi']
    issues = []

    # ① calendar plan 합 = kpi.plan_count
    cal_plan_sum = sum(d.get('plan', 0) for d in response.get('calendar', []))
    if cal_plan_sum != kpi['plan_count']:
        issues.append(
            f"calendar plan sum {cal_plan_sum} != kpi.plan_count {kpi['plan_count']}"
        )

    # ② by_customer plan 합 = kpi.plan_count
    bc_plan_sum = sum(c['plan'] for c in response.get('by_customer', []))
    if bc_plan_sum != kpi['plan_count']:
        issues.append(
            f"by_customer plan sum {bc_plan_sum} != kpi.plan_count {kpi['plan_count']}"
        )

    # ③ by_customer shipped 합 = kpi.shipped_count
    bc_shipped_sum = sum(c['shipped'] for c in response.get('by_customer', []))
    if bc_shipped_sum != kpi['shipped_count']:
        issues.append(
            f"by_customer shipped sum {bc_shipped_sum} != kpi.shipped_count {kpi['shipped_count']}"
        )

    # ④ by_model plan 합 = kpi.plan_count (v2.18.29 옵션 C 추가)
    bm_plan_sum = sum(m['plan'] for m in response.get('by_model', []))
    if bm_plan_sum != kpi['plan_count']:
        issues.append(
            f"by_model plan sum {bm_plan_sum} != kpi.plan_count {kpi['plan_count']}"
        )

    # ⑤ by_model shipped 합 = kpi.shipped_count (v2.18.29 옵션 C 추가)
    bm_shipped_sum = sum(m['shipped'] for m in response.get('by_model', []))
    if bm_shipped_sum != kpi['shipped_count']:
        issues.append(
            f"by_model shipped sum {bm_shipped_sum} != kpi.shipped_count {kpi['shipped_count']}"
        )

    if issues:
        logger.error(
            "[Sprint76] invariant violation: %s",
            "; ".join(issues),
            extra={'period': response.get('period')},
        )
        try:
            import sentry_sdk
            sentry_sdk.capture_message(
                "Sprint76 invariant violation",
                level='error',
                extras={'issues': issues, 'period': response.get('period')},
            )
        except ImportError:
            pass
        raise InvariantViolationError(issues)


def get_shipment_summary(
    period: str = 'month',
    reference_date: Optional[str] = None,
) -> Dict[str, Any]:
    """API #1 — `GET /api/admin/shipment/summary` 응답 생성.

    Returns: { period, kpi, calendar, by_customer, by_model, monthly_trend, top_delayed }
    """
    start, end = _resolve_period_range(period, reference_date)
    ref_date = (
        datetime.strptime(reference_date, '%Y-%m-%d').date()
        if reference_date else date.today()
    )

    # period 표시 형식
    if period == 'month':
        period_label = start.strftime('%Y-%m')
    elif period == 'quarter':
        period_label = f"{start.year}-Q{(start.month - 1) // 3 + 1}"
    else:
        period_label = str(start.year)

    conn = get_conn()
    try:
        cur = conn.cursor()
        kpi = _fetch_kpi(cur, start, end)
        # v2.18.33 (사용자 catch 5-27): 계획 변경 hint — 자기 충족 catch 신호
        kpi['plan_change_warning'] = _fetch_plan_change_warning(cur, start, end)
        calendar = _fetch_calendar(cur, start, end)
        by_customer = _fetch_by_customer(cur, start, end)
        by_model = _fetch_by_model(cur, start, end)
        monthly_trend = _fetch_monthly_trend(cur, ref_date)
        top_delayed = _fetch_top_delayed(cur, start, end)
        cur.close()

        response = {
            'period': period_label,
            'kpi': kpi,
            'calendar': calendar,
            'by_customer': by_customer,
            'by_model': by_model,
            'monthly_trend': monthly_trend,
            'top_delayed': top_delayed,
        }
        _assert_invariants(response)
        return response
    finally:
        put_conn(conn)


def get_shipment_details(
    period: str = 'month',
    reference_date: Optional[str] = None,
    target_date: Optional[str] = None,
    status: Optional[str] = None,
    partner: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
) -> Dict[str, Any]:
    """API #2 — `GET /api/admin/shipment/details` 응답 생성.

    Returns: { items, total, page, per_page, total_pages }
    """
    start, end = _resolve_period_range(period, reference_date)
    cte, params = _build_best_ship_cte(start, end)

    # WHERE 조립
    where_clauses = []
    where_params: List[Any] = []

    # 기본: period 영역 안에 plan_date OR actual_date
    where_clauses.append(
        "((plan_date >= %s AND plan_date < %s) OR (actual_date >= %s AND actual_date < %s))"
    )
    where_params.extend([start, end, start, end])

    if target_date:
        try:
            td = datetime.strptime(target_date, '%Y-%m-%d').date()
            where_clauses.append("(plan_date = %s OR actual_date = %s)")
            where_params.extend([td, td])
        except ValueError:
            pass

    if status == 'shipped':
        where_clauses.append("actual_date IS NOT NULL")
    elif status == 'pending':
        where_clauses.append("actual_date IS NULL AND plan_date >= CURRENT_DATE")
    elif status == 'delayed':
        where_clauses.append("actual_date IS NULL AND plan_date < CURRENT_DATE")

    if partner:
        where_clauses.append("(partner_mech = %s OR partner_elec = %s)")
        where_params.extend([partner, partner])

    if q:
        like = f"%{q}%"
        where_clauses.append(
            "(serial_number ILIKE %s OR sales_order ILIKE %s OR model ILIKE %s OR customer ILIKE %s)"
        )
        where_params.extend([like, like, like, like])

    where_sql = " AND ".join(where_clauses)

    # offset / limit
    offset = max(0, (page - 1) * per_page)

    conn = get_conn()
    try:
        cur = conn.cursor()

        # total
        sql_count = cte + f"SELECT COUNT(*) AS total FROM best_ship WHERE {where_sql};"
        cur.execute(sql_count, params + tuple(where_params))
        row = cur.fetchone()
        total = int(row['total'] or 0) if row else 0

        # items
        sql_items = cte + f"""
            SELECT serial_number, sales_order, model, customer,
                   partner_mech, partner_elec, plan_date, actual_date, source,
                   CASE
                       WHEN actual_date IS NOT NULL THEN 'shipped'
                       WHEN plan_date >= CURRENT_DATE THEN 'pending'
                       ELSE 'delayed'
                   END AS status,
                   CASE
                       WHEN actual_date IS NOT NULL AND plan_date IS NOT NULL
                           THEN (actual_date - plan_date)
                       ELSE NULL
                   END AS delay_days
            FROM best_ship
            WHERE {where_sql}
            ORDER BY COALESCE(actual_date, plan_date) DESC NULLS LAST, serial_number ASC
            LIMIT %s OFFSET %s;
        """
        cur.execute(sql_items, params + tuple(where_params) + (per_page, offset))
        items = []
        for r in cur.fetchall():
            items.append({
                'serial_number': r['serial_number'],
                'sales_order': r['sales_order'],
                'model': r['model'],
                'customer': r['customer'],
                'partner_mech': r['partner_mech'],
                'partner_elec': r['partner_elec'],
                'plan_date': r['plan_date'].isoformat() if r['plan_date'] else None,
                'actual_date': r['actual_date'].isoformat() if r['actual_date'] else None,
                'status': r['status'],
                'source': r['source'],
                'delay_days': int(r['delay_days']) if r['delay_days'] is not None else None,
            })
        cur.close()

        total_pages = (total + per_page - 1) // per_page if total > 0 else 0
        return {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
        }
    finally:
        put_conn(conn)
