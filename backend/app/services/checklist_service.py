"""
TM 체크리스트 서비스 (Sprint 52)
체크리스트 조회 / 항목 체크 / 완료 판정 + 알림
"""

import logging
from typing import Dict, Any, List, Optional

from psycopg2 import Error as PsycopgError

from app.models.worker import get_db_connection
from app.db_pool import put_conn


logger = logging.getLogger(__name__)


def get_tm_checklist(serial_number: str, judgment_phase: int = 1) -> Dict[str, Any]:
    """
    TM 체크리스트 조회 (item_group별 그룹핑 응답)

    checklist_master (category='TM') + checklist_record LEFT JOIN.
    admin_settings.tm_checklist_scope 에 따라 master 필터링:
      - 'product_code': 해당 product_code로 master 필터
      - 'all': product_code 무시, category='TM' 전체

    Args:
        serial_number: 제품 시리얼 번호
        judgment_phase: 판정 차수 (기본 1)

    Returns:
        {
            "serial_number": str,
            "sales_order": str|null,
            "model": str|null,
            "groups": [
                {
                    "group_name": str,
                    "items": [
                        {
                            "master_id": int,
                            "item_name": str,
                            "item_order": int,
                            "description": str|null,
                            "check_result": "PASS"|"NA"|null,
                            "checked_by_name": str|null,
                            "checked_at": str|null,
                            "note": str|null
                        }, ...
                    ]
                }, ...
            ],
            "summary": {
                "total": int,
                "checked": int,
                "remaining": int,
                "is_complete": bool
            }
        }
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # product_info에서 product_code, sales_order, model 조회
        cur.execute(
            """
            SELECT pi.product_code, pi.sales_order, pi.model
            FROM plan.product_info pi
            WHERE pi.serial_number = %s
            """,
            (serial_number,)
        )
        product_row = cur.fetchone()
        product_code = product_row['product_code'] if product_row else None
        sales_order = product_row['sales_order'] if product_row else None
        model = product_row['model'] if product_row else None

        # admin_settings.tm_checklist_scope 확인
        cur.execute(
            "SELECT setting_value FROM admin_settings WHERE setting_key = 'tm_checklist_scope'"
        )
        scope_row = cur.fetchone()
        scope = 'product_code'
        if scope_row:
            sv = scope_row['setting_value']
            scope = sv if isinstance(sv, str) else str(sv)

        # master 필터 조건 결정
        if scope == 'all' or not product_code:
            master_filter_sql = "cm.category = 'TM'"
            master_params: list = []
        else:
            master_filter_sql = "cm.product_code = %s AND cm.category = 'TM'"
            master_params = [product_code]

        # checklist_master + checklist_record LEFT JOIN
        query = f"""
            SELECT
                cm.id          AS master_id,
                cm.item_group,
                cm.item_name,
                cm.item_order,
                cm.description,
                cr.check_result,
                cr.checked_by,
                w.name         AS checked_by_name,
                cr.checked_at,
                cr.note
            FROM checklist.checklist_master cm
            LEFT JOIN checklist.checklist_record cr
                ON cr.master_id      = cm.id
               AND cr.serial_number  = %s
               AND cr.judgment_phase = %s
            LEFT JOIN workers w ON w.id = cr.checked_by
            WHERE {master_filter_sql}
              AND cm.is_active = TRUE
            ORDER BY cm.item_group ASC NULLS LAST, cm.item_order ASC, cm.id ASC
        """
        params: list = [serial_number, judgment_phase] + master_params
        cur.execute(query, params)
        rows = cur.fetchall()

        # item_group별 그룹핑
        groups_dict: Dict[str, list] = {}
        total = 0
        checked = 0

        for row in rows:
            group_name = row['item_group'] or '기타'
            if group_name not in groups_dict:
                groups_dict[group_name] = []

            check_result = row['check_result']
            item = {
                'master_id': row['master_id'],
                'item_name': row['item_name'],
                'item_order': row['item_order'],
                'description': row['description'],
                'check_result': check_result,
                'checked_by_name': row['checked_by_name'],
                'checked_at': row['checked_at'].isoformat() if row['checked_at'] else None,
                'note': row['note'],
            }
            groups_dict[group_name].append(item)
            total += 1
            if check_result in ('PASS', 'NA'):
                checked += 1

        groups = [
            {'group_name': gname, 'items': items}
            for gname, items in groups_dict.items()
        ]

        remaining = total - checked
        is_complete = (total > 0 and remaining == 0)

        return {
            'serial_number': serial_number,
            'sales_order': sales_order,
            'model': model,
            'groups': groups,
            'summary': {
                'total': total,
                'checked': checked,
                'remaining': remaining,
                'is_complete': is_complete,
            },
        }

    except PsycopgError as e:
        logger.error(f"get_tm_checklist failed: serial={serial_number}, error={e}")
        return {
            'serial_number': serial_number,
            'sales_order': None,
            'model': None,
            'groups': [],
            'summary': {'total': 0, 'checked': 0, 'remaining': 0, 'is_complete': False},
        }
    finally:
        if conn:
            put_conn(conn)


def upsert_tm_check(
    serial_number: str,
    master_id: int,
    check_result: str,
    note: Optional[str],
    worker_id: int,
    judgment_phase: int = 1,
) -> Dict[str, Any]:
    """
    TM 체크리스트 항목 체크 (UPSERT)

    check_result는 'PASS' 또는 'NA'만 허용.
    UPSERT 후 _check_tm_completion() 호출하여 전체 완료 여부 판정.

    Args:
        serial_number: 제품 시리얼 번호
        master_id: 체크리스트 마스터 항목 ID
        check_result: 'PASS' 또는 'NA'
        note: ISSUE 내용 (선택)
        worker_id: 체크를 수행하는 작업자 ID
        judgment_phase: 판정 차수 (기본 1)

    Returns:
        {
            "master_id": int,
            "check_result": str,
            "is_complete": bool
        }

    Raises:
        ValueError: check_result가 PASS/NA가 아닌 경우
    """
    if check_result not in ('PASS', 'NA'):
        raise ValueError(f"INVALID_CHECK_RESULT: check_result는 'PASS' 또는 'NA'만 허용됩니다. (입력값: {check_result})")

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # master_id 존재 확인
        cur.execute(
            "SELECT id FROM checklist.checklist_master WHERE id = %s",
            (master_id,)
        )
        if not cur.fetchone():
            raise ValueError(f"MASTER_NOT_FOUND: master_id={master_id} 없음")

        # UPSERT checklist_record (serial_number, master_id, judgment_phase)
        cur.execute(
            """
            INSERT INTO checklist.checklist_record
                (serial_number, master_id, judgment_phase, check_result, checked_by, checked_at, note, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), %s, NOW())
            ON CONFLICT (serial_number, master_id, judgment_phase) DO UPDATE
            SET check_result = EXCLUDED.check_result,
                checked_by   = EXCLUDED.checked_by,
                checked_at   = EXCLUDED.checked_at,
                note         = EXCLUDED.note,
                updated_at   = NOW()
            RETURNING id
            """,
            (serial_number, master_id, judgment_phase, check_result, worker_id, note)
        )
        conn.commit()

        logger.info(
            f"TM checklist upserted: serial={serial_number}, master_id={master_id}, "
            f"check_result={check_result}, worker_id={worker_id}, phase={judgment_phase}"
        )

        # 완료 판정
        is_complete = _check_tm_completion(serial_number, judgment_phase)

        return {
            'master_id': master_id,
            'check_result': check_result,
            'is_complete': is_complete,
        }

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"upsert_tm_check failed: serial={serial_number}, master_id={master_id}, error={e}")
        raise
    finally:
        if conn:
            put_conn(conn)


def _check_tm_completion(serial_number: str, judgment_phase: int = 1) -> bool:
    """
    TM 체크리스트 전체 완료 여부 판정.

    해당 S/N의 TM 체크리스트 항목 중 check_result IS NULL인 항목이 0개이면 완료.
    완료 시 ISSUE note가 있고 tm_checklist_issue_alert=true이면 CHECKLIST_ISSUE 알림 발송.

    Args:
        serial_number: 제품 시리얼 번호
        judgment_phase: 판정 차수 (기본 1)

    Returns:
        True: 전체 완료, False: 미완료
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # tm_checklist_scope 확인 (product_code 필터 결정)
        cur.execute(
            "SELECT setting_value FROM admin_settings WHERE setting_key = 'tm_checklist_scope'"
        )
        scope_row = cur.fetchone()
        scope = 'product_code'
        if scope_row:
            sv = scope_row['setting_value']
            scope = sv if isinstance(sv, str) else str(sv)

        # product_code 조회
        cur.execute(
            "SELECT product_code FROM plan.product_info WHERE serial_number = %s",
            (serial_number,)
        )
        product_row = cur.fetchone()
        product_code = product_row['product_code'] if product_row else None

        if scope == 'all' or not product_code:
            master_filter = "cm.category = 'TM'"
            master_params: list = []
        else:
            master_filter = "cm.product_code = %s AND cm.category = 'TM'"
            master_params = [product_code]

        # NULL인 항목 수 확인
        null_check_query = f"""
            SELECT COUNT(*) AS null_count
            FROM checklist.checklist_master cm
            LEFT JOIN checklist.checklist_record cr
                ON cr.master_id      = cm.id
               AND cr.serial_number  = %s
               AND cr.judgment_phase = %s
            WHERE {master_filter}
              AND cm.is_active = TRUE
              AND cr.check_result IS NULL
        """
        params: list = [serial_number, judgment_phase] + master_params
        cur.execute(null_check_query, params)
        null_count = cur.fetchone()['null_count']

        if null_count > 0:
            return False

        # 전체 항목 수 확인 (0건이면 미완료)
        total_query = f"""
            SELECT COUNT(*) AS total_count
            FROM checklist.checklist_master cm
            WHERE {master_filter}
              AND cm.is_active = TRUE
        """
        cur.execute(total_query, master_params)
        total_count = cur.fetchone()['total_count']

        if total_count == 0:
            return False

        # 완료! ISSUE note 존재 여부 확인
        cur.execute(
            """
            SELECT cr.note, cm.item_name
            FROM checklist.checklist_record cr
            JOIN checklist.checklist_master cm ON cm.id = cr.master_id
            WHERE cr.serial_number  = %s
              AND cr.judgment_phase = %s
              AND cr.note IS NOT NULL
              AND cr.note != ''
              AND cm.is_active = TRUE
            """,
            (serial_number, judgment_phase)
        )
        issue_rows = cur.fetchall()

        if issue_rows:
            # tm_checklist_issue_alert 설정 확인
            cur.execute(
                "SELECT setting_value FROM admin_settings WHERE setting_key = 'tm_checklist_issue_alert'"
            )
            alert_row = cur.fetchone()
            issue_alert = True  # default
            if alert_row:
                sv = alert_row['setting_value']
                if isinstance(sv, bool):
                    issue_alert = sv
                elif isinstance(sv, str):
                    issue_alert = sv.lower() in ('true', '1')
                else:
                    issue_alert = bool(sv)

            if issue_alert:
                from app.services.alert_service import create_and_broadcast_alert
                for issue_row in issue_rows:
                    try:
                        create_and_broadcast_alert({
                            'alert_type': 'CHECKLIST_ISSUE',
                            'message': f'[{serial_number}] TM 체크리스트 ISSUE: {issue_row["item_name"]} - {issue_row["note"]}',
                            'serial_number': serial_number,
                            'target_role': 'MECH',
                        })
                    except Exception as ae:
                        logger.error(f"_check_tm_completion: CHECKLIST_ISSUE alert failed: {ae}")

        return True

    except PsycopgError as e:
        logger.error(f"_check_tm_completion failed: serial={serial_number}, error={e}")
        return False
    finally:
        if conn:
            put_conn(conn)


def get_tm_checklist_status(serial_number: str, judgment_phase: int = 1) -> Dict[str, Any]:
    """
    TM 체크리스트 완료 상태 요약 조회.

    GET /api/app/checklist/tm/<serial_number>/status 에서 사용.
    다른 서비스에서 체크리스트 완료 여부 확인 시에도 활용 가능.

    Args:
        serial_number: 제품 시리얼 번호
        judgment_phase: 판정 차수 (기본 1)

    Returns:
        {
            "is_complete": bool,
            "completed_at": str|null,
            "checked_count": int,
            "total_count": int
        }
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # tm_checklist_scope 확인
        cur.execute(
            "SELECT setting_value FROM admin_settings WHERE setting_key = 'tm_checklist_scope'"
        )
        scope_row = cur.fetchone()
        scope = 'product_code'
        if scope_row:
            sv = scope_row['setting_value']
            scope = sv if isinstance(sv, str) else str(sv)

        cur.execute(
            "SELECT product_code FROM plan.product_info WHERE serial_number = %s",
            (serial_number,)
        )
        product_row = cur.fetchone()
        product_code = product_row['product_code'] if product_row else None

        if scope == 'all' or not product_code:
            master_filter = "cm.category = 'TM'"
            master_params: list = []
        else:
            master_filter = "cm.product_code = %s AND cm.category = 'TM'"
            master_params = [product_code]

        # 전체 / 체크 완료 항목 수
        stats_query = f"""
            SELECT
                COUNT(cm.id)                                      AS total_count,
                COUNT(cr.id) FILTER (WHERE cr.check_result IN ('PASS','NA')) AS checked_count,
                MAX(cr.checked_at)                                AS last_checked_at
            FROM checklist.checklist_master cm
            LEFT JOIN checklist.checklist_record cr
                ON cr.master_id      = cm.id
               AND cr.serial_number  = %s
               AND cr.judgment_phase = %s
            WHERE {master_filter}
              AND cm.is_active = TRUE
        """
        params: list = [serial_number, judgment_phase] + master_params
        cur.execute(stats_query, params)
        row = cur.fetchone()

        total_count = row['total_count'] if row else 0
        checked_count = row['checked_count'] if row else 0
        last_checked_at = row['last_checked_at'] if row else None

        is_complete = total_count > 0 and (total_count == checked_count)

        return {
            'is_complete': is_complete,
            'completed_at': last_checked_at.isoformat() if (is_complete and last_checked_at) else None,
            'checked_count': checked_count,
            'total_count': total_count,
        }

    except PsycopgError as e:
        logger.error(f"get_tm_checklist_status failed: serial={serial_number}, error={e}")
        return {
            'is_complete': False,
            'completed_at': None,
            'checked_count': 0,
            'total_count': 0,
        }
    finally:
        if conn:
            put_conn(conn)
