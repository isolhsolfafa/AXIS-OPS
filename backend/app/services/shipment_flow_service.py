"""
출하 흐름 3단계 + 미종료 분류 + 출하 미처리 알림 service (Sprint 79, v2.19.0)

핵심:
- SI 마무리 공정 화면 영역 탭 3개 catch (출하 확정 / 출하 예정 / 미종료)
- 메인 메뉴 미종료 작업 분류 catch (협력사별 + GST 공정별)
- 출하 미처리 메일 대상 list catch (admin + recipients chip)

설계서: AGENT_TEAM_LAUNCH.md § Sprint 79 (FEAT-SI-SHIPMENT-FLOW-3PHASE-20260527)
Codex 라운드 1 (M=7/A=2/N=4) 모두 반영.

규칙:
- actual_date COALESCE 헬퍼 재사용 (shipment_history_service._get_actual_date_subquery)
- TEST CUSTOMER 제외 (v2.18.32 패턴 정합)
- N+1 회피 — UNION ALL + GROUP BY single query (Codex Q6 N)
"""

import logging
from datetime import date, datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.db_pool import get_conn, put_conn
from app.services.shipment_history_service import _get_actual_date_subquery

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))


# ─── 1. 출하 확정 / 출하 예정 (SI 화면 탭 2/3) ────────────────────────

def get_shipment_by_status(
    status: str,
    q: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
) -> Tuple[List[Dict[str, Any]], int]:
    """출하 확정/예정 list catch (SI 화면 영역 사용).

    Args:
        status: 'confirmed' (today) | 'planned' (future)
        q: search query (S/N or sales_order, 'planned' 영역 검색용 권장)
        page, per_page

    Returns:
        (items, total)

    Codex 라운드 1 catch:
    - Q1 M: _get_actual_date_subquery() 헬퍼 재사용 (DRY)
    - Q7 M: 호출자 영역 @gst_or_admin_required 보장
    - Q8 M (사용자 결정 나): is_si_finishing_in_progress 필드 응답 추가
    - A-추가1 (사용자 결정 가): TEST CUSTOMER 제외
    """
    if status not in ('confirmed', 'planned'):
        raise ValueError(f"status는 'confirmed' 또는 'planned' 이어야 합니다. (입력: {status})")

    actual_date_expr = _get_actual_date_subquery('p')
    offset = max(0, (page - 1) * per_page)

    # 출하 확정 = ship_plan_date == today
    # 출하 예정 = ship_plan_date > today
    if status == 'confirmed':
        date_filter = "p.ship_plan_date = CURRENT_DATE"
    else:
        date_filter = "p.ship_plan_date > CURRENT_DATE"

    # 검색 query (option)
    search_filter = ""
    params: List[Any] = []
    if q and q.strip():
        search_filter = "AND (p.serial_number ILIKE %s OR p.sales_order ILIKE %s)"
        like = f"%{q.strip()}%"
        params.extend([like, like])

    base_sql = f"""
        FROM plan.product_info p
        WHERE COALESCE(p.customer, '') <> 'TEST CUSTOMER'
          AND {date_filter}
          AND p.ship_plan_date IS NOT NULL
          AND ({actual_date_expr}) IS NULL
          {search_filter}
    """

    conn = get_conn()
    try:
        cur = conn.cursor()

        # total catch
        cur.execute(f"SELECT COUNT(*) AS cnt {base_sql}", params)
        row = cur.fetchone()
        total = int(row['cnt'] or 0) if row else 0

        # items catch (Codex Q8 — is_si_finishing_in_progress 필드 추가)
        # v2.19.5: si_finishing_task_id + worker_id 추가 ([내 작업 완료] 버튼 carrier)
        cur.execute(
            f"""
            SELECT p.serial_number, p.sales_order, p.model, p.customer,
                   p.mech_partner, p.elec_partner,
                   p.ship_plan_date,
                   sif.task_id AS si_finishing_task_id,
                   sif.worker_id AS si_finishing_worker_id,
                   sif.worker_name AS si_finishing_worker_name,
                   (sif.task_id IS NOT NULL) AS is_si_finishing_in_progress
            FROM plan.product_info p
            LEFT JOIN LATERAL (
                SELECT t.id AS task_id,
                       wsl.worker_id,
                       w.name AS worker_name
                FROM app_task_details t
                LEFT JOIN LATERAL (
                    SELECT wsl2.worker_id FROM work_start_log wsl2
                    WHERE wsl2.task_id = t.id ORDER BY wsl2.started_at DESC LIMIT 1
                ) wsl ON TRUE
                LEFT JOIN workers w ON wsl.worker_id = w.id
                WHERE t.serial_number = p.serial_number
                  AND t.task_id = 'SI_FINISHING'
                  AND t.started_at IS NOT NULL
                  AND t.completed_at IS NULL
                  AND COALESCE(t.force_closed, FALSE) = FALSE
                LIMIT 1
            ) sif ON TRUE
            WHERE COALESCE(p.customer, '') <> 'TEST CUSTOMER'
              AND {date_filter}
              AND p.ship_plan_date IS NOT NULL
              AND ({actual_date_expr}) IS NULL
              {search_filter}
            ORDER BY p.ship_plan_date ASC, p.sales_order ASC
            LIMIT %s OFFSET %s
            """,
            params + [per_page, offset],
        )
        items = []
        for r in cur.fetchall():
            items.append({
                'serial_number': r['serial_number'],
                'sales_order': r['sales_order'],
                'model': r['model'],
                'customer': r['customer'],
                'mech_partner': r['mech_partner'],
                'elec_partner': r['elec_partner'],
                'ship_plan_date': r['ship_plan_date'].isoformat() if r['ship_plan_date'] else None,
                'is_si_finishing_in_progress': bool(r['is_si_finishing_in_progress']),
                'si_finishing_task_id': r.get('si_finishing_task_id'),
                'si_finishing_worker_id': r.get('si_finishing_worker_id'),
                'si_finishing_worker_name': r.get('si_finishing_worker_name'),
            })

        return items, total

    finally:
        put_conn(conn)


# ─── 2. 미종료 작업 분류 (메인 메뉴 admin only) ────────────────────────

def get_pending_tasks_grouped() -> Dict[str, Any]:
    """미종료 작업 분류 catch (admin only, 메인 메뉴 영역 사용).

    Codex 라운드 1 catch:
    - Q6 N: UNION ALL + GROUP BY single query (N+1 회피)
    - A-추가1: TEST CUSTOMER 제외

    Returns:
        {
            "total": int,
            "partners": [{"name": "FNI", "category": "MECH", "count": int}, ...],
            "gst_processes": [{"category": "PI", "label": "가압검사", "count": int}, ...]
        }
    """
    conn = get_conn()
    try:
        cur = conn.cursor()

        # 단일 query — pending_tasks CTE + UNION ALL GROUP BY
        cur.execute(
            """
            WITH pending_tasks AS (
                SELECT t.id, t.serial_number, t.task_category,
                       p.mech_partner, p.elec_partner, p.module_outsourcing
                FROM app_task_details t
                JOIN plan.product_info p ON t.serial_number = p.serial_number
                WHERE t.started_at IS NOT NULL
                  AND t.completed_at IS NULL
                  AND COALESCE(t.force_closed, FALSE) = FALSE
                  AND COALESCE(p.customer, '') <> 'TEST CUSTOMER'
                  AND t.is_applicable = TRUE
            ),
            partner_groups AS (
                SELECT 'partner' AS group_type,
                       mech_partner AS name,
                       'MECH' AS category,
                       COUNT(*) AS count
                FROM pending_tasks
                WHERE task_category = 'MECH' AND mech_partner IS NOT NULL
                GROUP BY mech_partner
                UNION ALL
                SELECT 'partner' AS group_type,
                       elec_partner AS name,
                       'ELEC' AS category,
                       COUNT(*) AS count
                FROM pending_tasks
                WHERE task_category = 'ELEC' AND elec_partner IS NOT NULL
                GROUP BY elec_partner
                UNION ALL
                SELECT 'partner' AS group_type,
                       module_outsourcing AS name,
                       'TM' AS category,
                       COUNT(*) AS count
                FROM pending_tasks
                WHERE task_category = 'TMS' AND module_outsourcing IS NOT NULL
                GROUP BY module_outsourcing
            ),
            gst_groups AS (
                SELECT 'gst_process' AS group_type,
                       NULL::text AS name,
                       task_category AS category,
                       COUNT(*) AS count
                FROM pending_tasks
                WHERE task_category IN ('PI', 'QI', 'SI')
                GROUP BY task_category
            )
            SELECT * FROM partner_groups
            UNION ALL
            SELECT * FROM gst_groups
            ORDER BY group_type, category, name
            """
        )
        rows = cur.fetchall()

        partners = []
        gst_processes = []
        total = 0
        gst_labels = {'PI': '가압검사', 'QI': '공정검사', 'SI': '마무리공정'}

        for r in rows:
            count = int(r['count'])
            total += count
            if r['group_type'] == 'partner':
                partners.append({
                    'name': r['name'],
                    'category': r['category'],
                    'count': count,
                })
            else:
                gst_processes.append({
                    'category': r['category'],
                    'label': gst_labels.get(r['category'], r['category']),
                    'count': count,
                })

        return {
            'total': total,
            'partners': partners,
            'gst_processes': gst_processes,
        }

    finally:
        put_conn(conn)


# ─── 3. 출하 미처리 알림 — 어제 미처리 list catch ───────────────────

def get_overdue_shipments(yesterday: Optional[date] = None) -> List[Dict[str, Any]]:
    """어제 출하 미처리 list catch (07:30 KST cron 영역 호출).

    조건: ship_plan_date < today (어제 또는 그 이전) AND actual_date IS NULL
    (실제 운영 영역 = 어제만 catch + actual_date IS NULL — best_ship CTE 영역 동일 base)

    Args:
        yesterday: 기준 날짜 (테스트용, 기본 = 오늘 KST 영역 -1일)

    Returns:
        [{serial_number, sales_order, model, customer, ship_plan_date, ...}, ...]
    """
    if yesterday is None:
        today_kst = datetime.now(KST).date()
        yesterday = today_kst - timedelta(days=1)

    actual_date_expr = _get_actual_date_subquery('p')

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT p.serial_number, p.sales_order, p.model, p.customer,
                   p.mech_partner, p.elec_partner,
                   p.ship_plan_date
            FROM plan.product_info p
            WHERE COALESCE(p.customer, '') <> 'TEST CUSTOMER'
              AND p.ship_plan_date = %s
              AND ({actual_date_expr}) IS NULL
            ORDER BY p.sales_order ASC, p.serial_number ASC
            """,
            (yesterday,),
        )
        items = []
        for r in cur.fetchall():
            items.append({
                'serial_number': r['serial_number'],
                'sales_order': r['sales_order'],
                'model': r['model'],
                'customer': r['customer'],
                'mech_partner': r['mech_partner'],
                'elec_partner': r['elec_partner'],
                'ship_plan_date': r['ship_plan_date'].isoformat() if r['ship_plan_date'] else None,
            })
        return items
    finally:
        put_conn(conn)


# ─── 4. 출하 알림 메일 대상 list catch ──────────────────────────────

def get_overdue_alert_recipients(extra_names: List[str]) -> List[Dict[str, Any]]:
    """출하 미처리 알림 메일 대상 list catch.

    v2.19.8 (사용자 catch 5-28): worker_id list → worker name list 변경 (chip 영역 name display 정합).
    - is_admin=TRUE 무조건 catch (gmail 도메인 포함)
    - extra_names = admin_settings.shipment_alert_recipients (worker name list — GST 매니저)
    - 매칭 base: name = ANY(%s) AND company='GST' (동명이인 영역 모두 catch, 안전)
    - workers JOIN — approval_status='approved' AND is_active=TRUE AND email NOT NULL

    Args:
        extra_names: admin_settings.shipment_alert_recipients (chip list, name base)

    Returns:
        [{id, name, email}, ...] (중복 제거)
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, name, email
            FROM workers
            WHERE (is_admin = TRUE OR (name = ANY(%s) AND company = 'GST'))
              AND approval_status = 'approved'
              AND is_active = TRUE
              AND email IS NOT NULL
              AND email <> ''
            ORDER BY id ASC
            """,
            (extra_names or [],),
        )
        return [
            {'id': r['id'], 'name': r['name'], 'email': r['email']}
            for r in cur.fetchall()
        ]
    finally:
        put_conn(conn)
