"""
협력사별 S/N 작업 진행률 조회 서비스
Sprint 18: 협력사 관리자가 자사 담당 S/N들의 작업 진행률을 종합 조회
"""

import logging
from typing import Dict, Any, List, Optional

from app.models.worker import get_db_connection
from app.db_pool import put_conn

logger = logging.getLogger(__name__)


def get_partner_sn_progress(
    worker_company: Optional[str],
    worker_role: str,
    is_admin: bool,
    include_completed_within_days: int = 1,
    company_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    협력사별 S/N 작업 진행률 조회

    Args:
        worker_company: 작업자 소속 회사 (FNI, BAT, TMS(M), TMS(E), P&S, C&A, GST)
        worker_role: 작업자 역할
        is_admin: 관리자 여부
        include_completed_within_days: 완료 후 N일 이내 제품도 포함 (기본 1일)
        company_override: admin일 때 특정 회사 필터 (선택)

    Returns:
        {
            "products": [...],
            "summary": { "total": int, "in_progress": int, "completed_recent": int }
        }
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 회사 결정: admin이면 company_override 허용
        effective_company = company_override if (is_admin and company_override) else worker_company

        # Step 1: 협력사별 S/N 필터링 WHERE 절 구성
        where_clause, params = _build_company_filter(effective_company, is_admin)

        # Step 2: 완료 필터
        completion_filter = (
            "(cs.all_completed = false OR cs.all_completed_at > NOW() - INTERVAL '%s days')"
        )
        params.append(include_completed_within_days)

        # Step 3: 메인 쿼리 — S/N별 카테고리별 진행률
        query = f"""
            WITH sn_list AS (
                SELECT
                    qr.serial_number,
                    qr.qr_doc_id,
                    pi.model,
                    pi.customer,
                    pi.ship_plan_date,
                    pi.sales_order,
                    pi.mech_partner,
                    pi.elec_partner,
                    pi.module_outsourcing,
                    COALESCE(cs.all_completed, false) AS all_completed,
                    cs.all_completed_at
                FROM qr_registry qr
                JOIN plan.product_info pi ON qr.serial_number = pi.serial_number
                LEFT JOIN completion_status cs ON qr.serial_number = cs.serial_number
                WHERE qr.status = 'active'
                    {('AND ' + where_clause) if where_clause else ''}
                    AND {completion_filter}
                ORDER BY pi.ship_plan_date ASC NULLS LAST, pi.serial_number ASC
            ),
            task_progress AS (
                SELECT
                    atd.serial_number,
                    atd.task_category,
                    COUNT(*) FILTER (WHERE atd.is_applicable = true) AS total_tasks,
                    COUNT(*) FILTER (WHERE atd.is_applicable = true AND atd.completed_at IS NOT NULL) AS done_tasks
                FROM app_task_details atd
                WHERE atd.serial_number IN (SELECT serial_number FROM sn_list)
                GROUP BY atd.serial_number, atd.task_category
            )
            SELECT
                sn.serial_number,
                sn.qr_doc_id,
                sn.model,
                sn.customer,
                sn.ship_plan_date,
                sn.sales_order,
                sn.mech_partner,
                sn.elec_partner,
                sn.module_outsourcing,
                sn.all_completed,
                sn.all_completed_at,
                tp.task_category,
                COALESCE(tp.total_tasks, 0) AS total_tasks,
                COALESCE(tp.done_tasks, 0) AS done_tasks
            FROM sn_list sn
            LEFT JOIN task_progress tp ON sn.serial_number = tp.serial_number
            ORDER BY sn.ship_plan_date ASC NULLS LAST, sn.serial_number ASC, tp.task_category ASC
        """

        cur.execute(query, params)
        rows = cur.fetchall()

        # Step 4: 결과 조립 — S/N별 그룹핑
        products = _aggregate_products(rows, effective_company, is_admin)

        # Step 5: last_activity 서브쿼리 — S/N별 최근 태깅 작업자/시간 1건씩 조회 (N+1 방지)
        sn_list = [p['serial_number'] for p in products]
        last_activity_map: Dict[str, Any] = {}
        if sn_list:
            last_activity_query = """
                SELECT DISTINCT ON (combined.serial_number)
                       combined.serial_number,
                       w.name AS last_worker,
                       combined.activity_at AS last_activity_at,
                       combined.task_name AS last_task_name,
                       combined.task_category AS last_task_category
                FROM (
                    SELECT wsl.serial_number,
                           wsl.worker_id,
                           wsl.started_at AS activity_at,
                           wsl.task_name,
                           wsl.task_category
                    FROM work_start_log wsl
                    WHERE wsl.serial_number = ANY(%s)
                    UNION ALL
                    SELECT wcl.serial_number,
                           wcl.worker_id,
                           wcl.completed_at AS activity_at,
                           wcl.task_name,
                           wcl.task_category
                    FROM work_completion_log wcl
                    WHERE wcl.serial_number = ANY(%s)
                      AND wcl.completed_at IS NOT NULL
                ) combined
                JOIN workers w ON w.id = combined.worker_id
                ORDER BY combined.serial_number, combined.activity_at DESC
            """
            cur.execute(last_activity_query, [sn_list, sn_list])
            for la_row in cur.fetchall():
                last_activity_map[la_row['serial_number']] = {
                    'last_worker': la_row['last_worker'],
                    'last_activity_at': la_row['last_activity_at'],
                    'last_task_name': la_row['last_task_name'],
                    'last_task_category': la_row['last_task_category'],
                }

        # Step 6: products 배열에 last_worker / last_activity_at / last_task_name / last_task_category 필드 추가
        for p in products:
            activity = last_activity_map.get(p['serial_number'])
            p['last_worker'] = activity['last_worker'] if activity else None
            p['last_activity_at'] = (
                activity['last_activity_at'].isoformat()
                if activity and activity.get('last_activity_at') else None
            )
            p['last_task_name'] = activity['last_task_name'] if activity else None
            p['last_task_category'] = activity['last_task_category'] if activity else None

        # Summary 계산
        total = len(products)
        in_progress = sum(1 for p in products if not p['all_completed'])
        completed_recent = sum(1 for p in products if p['all_completed'])

        return {
            'products': products,
            'summary': {
                'total': total,
                'in_progress': in_progress,
                'completed_recent': completed_recent,
            }
        }

    except Exception as e:
        logger.error(f"Failed to get partner SN progress: {e}")
        raise
    finally:
        if conn:
            put_conn(conn)


def _build_company_filter(
    company: Optional[str], is_admin: bool
) -> tuple:
    """
    협력사별 WHERE 절 구성

    Returns:
        (where_clause_str, params_list)
    """
    if is_admin and not company:
        # GST admin → 전체
        return ('', [])

    if not company:
        return ('1=0', [])

    if company == 'GST':
        # GST 사내직원 → 전체 (PI/QI/SI 검사 담당)
        return ('', [])

    if company in ('FNI', 'BAT'):
        return ('pi.mech_partner = %s', [company])

    if company == 'TMS(M)':
        return (
            "(pi.mech_partner = 'TMS' OR pi.module_outsourcing = 'TMS')",
            [],
        )

    if company == 'TMS(E)':
        return ("pi.elec_partner = 'TMS'", [])

    if company in ('P&S', 'C&A'):
        return ('pi.elec_partner = %s', [company])

    # 알 수 없는 회사 → 빈 결과
    return ('1=0', [])


def _aggregate_products(
    rows: list, company: Optional[str], is_admin: bool
) -> List[Dict[str, Any]]:
    """
    쿼리 결과를 S/N별로 그룹핑하여 진행률 계산

    Returns:
        [
            {
                "serial_number": str,
                "qr_doc_id": str,
                "model": str,
                "customer": str,
                "ship_plan_date": str|null,
                "all_completed": bool,
                "all_completed_at": str|null,
                "categories": { "MECH": {"total": n, "done": n, "percent": n}, ... },
                "overall_percent": int,
                "my_category": str|null  # 자사 담당 카테고리 강조용
            },
            ...
        ]
    """
    # S/N별 그룹핑
    sn_map: Dict[str, Dict[str, Any]] = {}

    for row in rows:
        sn = row['serial_number']
        if sn not in sn_map:
            sn_map[sn] = {
                'serial_number': sn,
                'qr_doc_id': row['qr_doc_id'],
                'model': row['model'],
                'customer': row['customer'],
                'ship_plan_date': row['ship_plan_date'].isoformat() if row['ship_plan_date'] else None,
                'sales_order': row['sales_order'],
                'all_completed': row['all_completed'],
                'all_completed_at': row['all_completed_at'].isoformat() if row['all_completed_at'] else None,
                'mech_partner': row['mech_partner'],
                'elec_partner': row['elec_partner'],
                'module_outsourcing': row['module_outsourcing'],
                'categories': {},
            }

        cat = row['task_category']
        if cat:
            total = row['total_tasks']
            done = row['done_tasks']
            percent = round((done / total) * 100) if total > 0 else 0
            sn_map[sn]['categories'][cat] = {
                'total': total,
                'done': done,
                'percent': percent,
            }

    # overall_percent 계산 + my_category 결정
    products = []
    for sn_data in sn_map.values():
        cats = sn_data['categories']
        total_all = sum(c['total'] for c in cats.values())
        done_all = sum(c['done'] for c in cats.values())
        sn_data['overall_percent'] = round((done_all / total_all) * 100) if total_all > 0 else 0

        # my_category: 자사 담당 공정 카테고리
        sn_data['my_category'] = _resolve_my_category(
            company, is_admin, sn_data.get('mech_partner'), sn_data.get('elec_partner'),
            sn_data.get('module_outsourcing'),
        )

        # 응답에서 partner 필드 제거 (내부용)
        sn_data.pop('mech_partner', None)
        sn_data.pop('elec_partner', None)
        sn_data.pop('module_outsourcing', None)

        products.append(sn_data)

    return products


def _resolve_my_category(
    company: Optional[str],
    is_admin: bool,
    mech_partner: Optional[str],
    elec_partner: Optional[str],
    module_outsourcing: Optional[str],
) -> Optional[str]:
    """자사 담당 카테고리 결정"""
    if is_admin or not company or company == 'GST':
        return None  # 전체 보기 → 강조 없음

    if company in ('FNI', 'BAT'):
        return 'MECH'

    if company == 'TMS(M)':
        # TMS(M)은 TMS + MECH (mech_partner가 TMS일 때) 모두 담당
        return 'TMS'  # 주 카테고리는 TMS

    if company == 'TMS(E)':
        return 'ELEC'

    if company in ('P&S', 'C&A'):
        return 'ELEC'

    return None
