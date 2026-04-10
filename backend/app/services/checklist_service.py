"""
체크리스트 서비스 (Sprint 52 TM + Sprint 57 ELEC)
체크리스트 조회 / 항목 체크 / 완료 판정 + 알림
Sprint 54: _get_checklist_by_category() 추출, get_checklist_report() 추가
Sprint 57: ELEC 체크리스트 + Dual-Trigger 닫기 + checker_role
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from psycopg2 import Error as PsycopgError

from app.models.worker import get_db_connection
from app.db_pool import put_conn


logger = logging.getLogger(__name__)


def _get_checklist_by_category(
    cur,
    serial_number: str,
    category: str,
    product_code: Optional[str],
    scope: str,
    judgment_phase: int = 1,
    qr_doc_id: str = '',
) -> Dict[str, Any]:
    """카테고리별 체크리스트 조회 — 공통 로직 (Sprint 54)

    get_tm_checklist() 내부 로직을 추출. master+record LEFT JOIN + 그룹핑 + summary.
    TM/MECH/ELEC 모두 동일 패턴.

    Args:
        cur: DB cursor (외부에서 connection 관리)
        serial_number: S/N
        category: 'TM', 'MECH', 'ELEC' 등
        product_code: 제품 코드 (scope='product_code' 시 사용)
        scope: 'all' | 'product_code'
        judgment_phase: 판정 차수

    Returns:
        {
            "category": str,
            "items": [
                {
                    "item_group": str,
                    "item_name": str,
                    "item_type": str,
                    "description": str|null,
                    "check_result": "PASS"|"NA"|null,
                    "checked_by_name": str|null,
                    "checked_at": str|null,
                    "note": str|null
                }, ...
            ],
            "summary": { "total": int, "checked": int, "percent": float }
        }
    """
    # master 필터 조건 (기존 get_tm_checklist 패턴)
    if scope == 'all' or not product_code:
        master_filter_sql = "cm.product_code = 'COMMON' AND cm.category = %s"
        master_params: list = [category]
    else:
        master_filter_sql = "cm.product_code = %s AND cm.category = %s"
        master_params = [product_code, category]

    query = f"""
        SELECT
            cm.id          AS master_id,
            cm.item_group,
            cm.item_name,
            cm.item_type,
            cm.item_order,
            cm.description,
            COALESCE(cm.checker_role, 'WORKER') AS checker_role,
            COALESCE(cm.phase1_na, FALSE) AS phase1_na,
            cm.select_options,
            cr.check_result,
            cr.checked_by,
            w.name         AS checked_by_name,
            cr.checked_at,
            cr.note,
            cr.selected_value,
            cr.input_value
        FROM checklist.checklist_master cm
        LEFT JOIN checklist.checklist_record cr
            ON cr.master_id      = cm.id
           AND cr.serial_number  = %s
           AND cr.judgment_phase = %s
           AND cr.qr_doc_id     = %s
        LEFT JOIN workers w ON w.id = cr.checked_by
        WHERE {master_filter_sql}
          AND cm.is_active = TRUE
        ORDER BY
            CASE cm.item_group
                WHEN 'BURNER' THEN 1 WHEN 'REACTOR' THEN 2 WHEN 'EXHAUST' THEN 3 WHEN 'TANK' THEN 4
                WHEN 'PANEL 검사' THEN 1 WHEN '조립 검사' THEN 2 WHEN 'JIG 검사 및 특별관리 POINT' THEN 3
                ELSE 99
            END ASC,
            cm.item_order ASC, cm.id ASC
    """
    params: list = [serial_number, judgment_phase, qr_doc_id] + master_params
    cur.execute(query, params)
    rows = cur.fetchall()

    items = []
    total = 0
    checked = 0

    for row in rows:
        check_result = row['check_result']
        # item_type 컬럼이 없는 경우 fallback
        item_type = row['item_type'] if 'item_type' in row.keys() else 'CHECK'
        # Sprint 57-FE: phase1_na 자동 N.A (1차 배선 — 현장 조립 전 검사 불가 항목)
        phase1_na = row.get('phase1_na', False)
        if phase1_na and judgment_phase == 1 and check_result is None:
            check_result = 'NA'
        # select_options JSON 파싱
        select_options = row.get('select_options')
        if select_options and isinstance(select_options, str):
            import json
            try:
                select_options = json.loads(select_options)
            except Exception:
                pass
        items.append({
            'master_id': row['master_id'],
            'item_group': row['item_group'] or '기타',
            'item_name': row['item_name'],
            'item_type': item_type,
            'description': row['description'],
            'checker_role': row.get('checker_role', 'WORKER'),
            'phase1_na': phase1_na,
            'select_options': select_options,
            'check_result': check_result,
            'checked_by_name': row['checked_by_name'],
            'checked_at': row['checked_at'].isoformat() if row['checked_at'] else None,
            'note': row['note'],
            'selected_value': row.get('selected_value'),
            'input_value': row.get('input_value'),
        })
        total += 1
        if check_result in ('PASS', 'NA'):
            checked += 1

    percent = round(checked / total * 100, 1) if total > 0 else 0.0

    return {
        'category': category,
        'items': items,
        'summary': {
            'total': total,
            'checked': checked,
            'percent': percent,
        },
    }


def get_tm_checklist(serial_number: str, judgment_phase: int = 1, qr_doc_id: str = '') -> Dict[str, Any]:
    """
    TM 체크리스트 조회 (item_group별 그룹핑 응답) — 기존 API 호환 유지 (Sprint 54 wrapper)

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
                            "item_group": str,
                            "item_name": str,
                            "item_type": str,
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

        # 공통 함수 호출
        cat_data = _get_checklist_by_category(
            cur, serial_number, 'TM', product_code, scope, judgment_phase, qr_doc_id=qr_doc_id
        )

        # 기존 응답 형태 유지: groups 배열 (item_group별 그룹핑)
        groups_dict: Dict[str, list] = {}
        for item in cat_data['items']:
            gname = item['item_group']
            if gname not in groups_dict:
                groups_dict[gname] = []
            groups_dict[gname].append(item)

        groups = [{'group_name': gn, 'items': items} for gn, items in groups_dict.items()]

        total = cat_data['summary']['total']
        checked = cat_data['summary']['checked']

        return {
            'serial_number': serial_number,
            'sales_order': sales_order,
            'model': model,
            'groups': groups,
            'summary': {
                'total': total,
                'checked': checked,
                'remaining': total - checked,
                'is_complete': total > 0 and checked == total,
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


def _is_report_dual_model(model: Optional[str]) -> bool:
    """성적서용 DUAL 모델 감지 — model명에 'DUAL' 포함 여부"""
    if not model:
        return False
    return 'DUAL' in model.upper().split()


def get_checklist_report(serial_number: str, judgment_phase: int = 1) -> Dict[str, Any]:
    """S/N 전체 체크리스트 성적서 조회 (#54-B, Sprint 54)

    모든 활성 카테고리를 순회하여 성적서 데이터 반환.
    현재 TM만 master 데이터 존재. MECH/ELEC 마스터 확정 시 자동 포함.

    Args:
        serial_number: 제품 시리얼 번호
        judgment_phase: 판정 차수 (기본 1)

    Returns:
        {
            "serial_number": str,
            "model": str|null,
            "sales_order": str|null,
            "customer": str|null,
            "categories": [
                {
                    "category": str,
                    "items": [...],
                    "summary": {"total": int, "checked": int, "percent": float}
                }, ...
            ],
            "generated_at": str  -- KST ISO 형식
        }
        또는 {"error": "PRODUCT_NOT_FOUND", "message": "..."} (404)
        또는 {"error": "INTERNAL_ERROR", "message": "..."} (500)
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # product_info 조회
        cur.execute(
            """
            SELECT product_code, sales_order, model, customer
            FROM plan.product_info WHERE serial_number = %s
            """,
            (serial_number,)
        )
        product_row = cur.fetchone()
        if not product_row:
            return {'error': 'PRODUCT_NOT_FOUND', 'message': f'S/N {serial_number} 없음'}

        product_code = product_row['product_code']
        sales_order = product_row['sales_order']
        model = product_row['model']
        customer = product_row['customer']

        # scope 조회
        cur.execute(
            "SELECT setting_value FROM admin_settings WHERE setting_key = 'tm_checklist_scope'"
        )
        scope_row = cur.fetchone()
        scope = 'product_code'
        if scope_row:
            sv = scope_row['setting_value']
            scope = sv if isinstance(sv, str) else str(sv)

        # 활성 카테고리 목록 조회 (master에 존재하는 것만)
        if scope == 'all' or not product_code:
            cur.execute(
                """
                SELECT DISTINCT category FROM checklist.checklist_master
                WHERE product_code = 'COMMON' AND is_active = TRUE
                ORDER BY category
                """
            )
        else:
            cur.execute(
                """
                SELECT DISTINCT category FROM checklist.checklist_master
                WHERE product_code = %s AND is_active = TRUE
                ORDER BY category
                """,
                (product_code,)
            )
        cat_rows = cur.fetchall()

        # Sprint 30-BE: DUAL 모델 감지 (TM L/R 분기용)
        is_dual = _is_report_dual_model(model)

        categories = []
        for cat_row in cat_rows:
            cat = cat_row['category']

            if cat == 'ELEC':
                # ── ELEC: Phase 1(1차 배선) + Phase 2(2차 배선) 각각 조회 ──
                for phase_num, phase_label in [(1, '1차 배선'), (2, '2차 배선')]:
                    p_data = _get_checklist_by_category(
                        cur, serial_number, cat, product_code, scope, phase_num
                    )
                    # Phase 1: JIG 그룹 제외 (get_elec_checklist 동일 로직)
                    if phase_num == 1:
                        p_data['items'] = [
                            i for i in p_data['items']
                            if i['item_group'] != 'JIG 검사 및 특별관리 POINT'
                        ]
                    items = p_data['items']
                    total = len(items)
                    checked = sum(1 for i in items if i.get('check_result') in ('PASS', 'NA'))
                    p_data['summary'] = {
                        'total': total,
                        'checked': checked,
                        'percent': round(checked / total * 100, 1) if total > 0 else 0.0,
                    }
                    p_data['phase'] = phase_num
                    p_data['phase_label'] = phase_label
                    if total > 0:
                        categories.append(p_data)

            elif cat == 'TM' and is_dual:
                # ── TM DUAL: L/R 탱크별 분리 조회 ──
                cur.execute(
                    """
                    SELECT DISTINCT qr_doc_id
                    FROM app_task_details
                    WHERE serial_number = %s
                      AND task_category = 'TMS'
                      AND qr_doc_id != ''
                    ORDER BY qr_doc_id
                    """,
                    (serial_number,)
                )
                tank_rows = cur.fetchall()
                for tank_row in tank_rows:
                    tank_qr = tank_row['qr_doc_id']
                    if tank_qr.endswith('-L'):
                        tank_label = 'L Tank'
                    elif tank_qr.endswith('-R'):
                        tank_label = 'R Tank'
                    else:
                        tank_label = tank_qr
                    t_data = _get_checklist_by_category(
                        cur, serial_number, cat, product_code, scope,
                        judgment_phase, qr_doc_id=tank_qr
                    )
                    t_data['qr_doc_id'] = tank_qr
                    t_data['phase_label'] = tank_label
                    if t_data['summary']['total'] > 0:
                        categories.append(t_data)

            else:
                # ── MECH / TM(SINGLE) 등: 기존 동일 ──
                cat_data = _get_checklist_by_category(
                    cur, serial_number, cat, product_code, scope, judgment_phase
                )
                if cat_data['summary']['total'] > 0:
                    categories.append(cat_data)

        kst = timezone(timedelta(hours=9))

        return {
            'serial_number': serial_number,
            'model': model,
            'sales_order': sales_order,
            'customer': customer,
            'categories': categories,
            'generated_at': datetime.now(kst).isoformat(),
        }

    except PsycopgError as e:
        logger.error(f"get_checklist_report failed: serial={serial_number}, error={e}")
        return {'error': 'INTERNAL_ERROR', 'message': '데이터 조회 실패'}
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
    qr_doc_id: str = '',
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

        # UPSERT checklist_record (Sprint 57-C: UNIQUE에 qr_doc_id 포함)
        cur.execute(
            """
            INSERT INTO checklist.checklist_record
                (serial_number, master_id, judgment_phase, check_result, checked_by, checked_at, note, qr_doc_id, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s, NOW())
            ON CONFLICT (serial_number, master_id, judgment_phase, qr_doc_id) DO UPDATE
            SET check_result = EXCLUDED.check_result,
                checked_by   = EXCLUDED.checked_by,
                checked_at   = EXCLUDED.checked_at,
                note         = EXCLUDED.note,
                updated_at   = NOW()
            RETURNING id
            """,
            (serial_number, master_id, judgment_phase, check_result, worker_id, note, qr_doc_id)
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
            master_filter = "cm.product_code = 'COMMON' AND cm.category = 'TM'"
            master_params: list = []
        else:
            master_filter = "cm.product_code = %s AND cm.category = 'TM'"
            master_params = [product_code]

        # NULL인 항목 수 확인 (Sprint 57-C: qr_doc_id='' 기본 — TM SINGLE/ELEC 호환)
        null_check_query = f"""
            SELECT COUNT(*) AS null_count
            FROM checklist.checklist_master cm
            LEFT JOIN checklist.checklist_record cr
                ON cr.master_id      = cm.id
               AND cr.serial_number  = %s
               AND cr.judgment_phase = %s
               AND cr.qr_doc_id     = ''
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
            master_filter = "cm.product_code = 'COMMON' AND cm.category = 'TM'"
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


# ═══════════════════════════════════════════════════════
#  Sprint 57: ELEC 체크리스트
# ═══════════════════════════════════════════════════════

def get_elec_checklist(serial_number: str, judgment_phase: int = 1, qr_doc_id: str = '') -> Dict[str, Any]:
    """ELEC 체크리스트 조회 (Sprint 57/57-C) — TM과 동일 패턴 + qr_doc_id"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT pi.product_code, pi.sales_order, pi.model "
            "FROM plan.product_info pi WHERE pi.serial_number = %s",
            (serial_number,)
        )
        product_row = cur.fetchone()
        product_code = product_row['product_code'] if product_row else None
        sales_order = product_row['sales_order'] if product_row else None
        model = product_row['model'] if product_row else None

        data = _get_checklist_by_category(
            cur, serial_number, 'ELEC', product_code, 'all', judgment_phase, qr_doc_id=qr_doc_id
        )

        # Sprint 57-C: Phase 1에서 JIG 그룹 제외 (2차 배선에서만 표시)
        items = data['items']
        if judgment_phase == 1:
            items = [i for i in items if i['item_group'] != 'JIG 검사 및 특별관리 POINT']

        from collections import OrderedDict
        groups_dict: OrderedDict = OrderedDict()
        for item in items:
            g = item['item_group']
            if g not in groups_dict:
                groups_dict[g] = []
            groups_dict[g].append(item)

        groups = [{'group_name': k, 'items': v} for k, v in groups_dict.items()]

        # summary 재계산 (Phase 1 JIG 제외 반영)
        total = len(items)
        checked = sum(1 for i in items if i['check_result'] in ('PASS', 'NA'))
        percent = round(checked / total * 100, 1) if total > 0 else 0.0
        summary = {
            'total': total,
            'checked': checked,
            'percent': percent,
            'remaining': total - checked,
            'is_complete': (total - checked == 0 and total > 0),
        }

        return {
            'serial_number': serial_number,
            'sales_order': sales_order,
            'model': model,
            'judgment_phase': judgment_phase,
            'groups': groups,
            'summary': summary,
        }

    except PsycopgError as e:
        logger.error(f"get_elec_checklist failed: serial={serial_number}, error={e}")
        raise
    finally:
        if conn:
            put_conn(conn)


def upsert_elec_check(
    serial_number: str,
    master_id: int,
    check_result: str,
    note: Optional[str],
    worker_id: int,
    judgment_phase: int = 1,
    selected_value: Optional[str] = None,
    input_value: Optional[str] = None,
    qr_doc_id: str = '',
) -> Dict[str, Any]:
    """ELEC 체크리스트 항목 체크 (UPSERT) — Sprint 57/57-C. manager 제한 없음."""
    if check_result not in ('PASS', 'NA'):
        raise ValueError(f"INVALID_CHECK_RESULT: '{check_result}'")

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT id FROM checklist.checklist_master WHERE id = %s AND category = 'ELEC'",
            (master_id,)
        )
        if not cur.fetchone():
            raise ValueError(f"MASTER_NOT_FOUND: master_id={master_id} (ELEC)")

        cur.execute(
            """
            INSERT INTO checklist.checklist_record
                (serial_number, master_id, judgment_phase, check_result,
                 checked_by, checked_at, note, selected_value, input_value,
                 qr_doc_id, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s, %s, %s, NOW())
            ON CONFLICT (serial_number, master_id, judgment_phase, qr_doc_id) DO UPDATE
            SET check_result   = EXCLUDED.check_result,
                checked_by     = EXCLUDED.checked_by,
                checked_at     = EXCLUDED.checked_at,
                note           = EXCLUDED.note,
                selected_value = EXCLUDED.selected_value,
                input_value    = EXCLUDED.input_value,
                updated_at     = NOW()
            RETURNING id
            """,
            (serial_number, master_id, judgment_phase, check_result, worker_id,
             note, selected_value, input_value, qr_doc_id)
        )
        conn.commit()

        is_complete = check_elec_completion(serial_number, judgment_phase)

        # Dual-Trigger 경로 2: 체크리스트 완료 + IF_2 이미 완료 → ELEC 닫기
        elec_closed = False
        if is_complete:
            elec_closed = _try_elec_close(serial_number)

        return {
            'master_id': master_id,
            'check_result': check_result,
            'is_complete': is_complete,
            'elec_closed': elec_closed,
        }

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"upsert_elec_check failed: serial={serial_number}, error={e}")
        raise
    finally:
        if conn:
            put_conn(conn)


def check_elec_completion(serial_number: str, judgment_phase: int = 1) -> bool:
    """ELEC 체크리스트 완료 판정 — GST(QI) 항목 제외. 중복 알림 방지 포함."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # NULL인 항목 수 (GST 전용 항목 제외, Sprint 57-C: qr_doc_id='' 기본)
        cur.execute(
            """
            SELECT COUNT(*) AS null_count
            FROM checklist.checklist_master cm
            LEFT JOIN checklist.checklist_record cr
                ON cr.master_id      = cm.id
               AND cr.serial_number  = %s
               AND cr.judgment_phase = %s
               AND cr.qr_doc_id     = ''
            WHERE cm.category   = 'ELEC'
              AND cm.is_active  = TRUE
              AND COALESCE(cm.checker_role, 'WORKER') != 'QI'
              AND cr.check_result IS NULL
            """,
            (serial_number, judgment_phase)
        )
        null_count = cur.fetchone()['null_count']
        if null_count > 0:
            return False

        # 전체 항목 수 (GST 제외)
        cur.execute(
            """
            SELECT COUNT(*) AS total_count
            FROM checklist.checklist_master cm
            WHERE cm.category = 'ELEC'
              AND cm.is_active = TRUE
              AND COALESCE(cm.checker_role, 'WORKER') != 'QI'
            """
        )
        total_count = cur.fetchone()['total_count']
        if total_count == 0:
            return False

        # ISSUE note 알림 (중복 방지: 동일 S/N ELEC CHECKLIST_ISSUE 이미 존재 시 스킵)
        cur.execute(
            "SELECT setting_value FROM admin_settings WHERE setting_key = 'elec_checklist_issue_alert'"
        )
        alert_row = cur.fetchone()
        issue_alert_enabled = True
        if alert_row:
            sv = alert_row['setting_value']
            if isinstance(sv, str):
                issue_alert_enabled = sv.lower() in ('true', '1')

        if issue_alert_enabled:
            cur.execute(
                """
                SELECT id FROM app_alert_logs
                WHERE alert_type = 'CHECKLIST_ISSUE'
                  AND serial_number = %s
                  AND message LIKE '[[]' || %s || '%%ELEC%%'
                LIMIT 1
                """,
                (serial_number, serial_number)
            )
            already_alerted = cur.fetchone() is not None

            if not already_alerted:
                cur.execute(
                    """
                    SELECT cr.note, cm.item_name
                    FROM checklist.checklist_record cr
                    JOIN checklist.checklist_master cm ON cm.id = cr.master_id
                    WHERE cr.serial_number  = %s
                      AND cr.judgment_phase = %s
                      AND cr.note IS NOT NULL AND cr.note != ''
                      AND cm.category = 'ELEC'
                      AND cm.is_active = TRUE
                    """,
                    (serial_number, judgment_phase)
                )
                issue_rows = cur.fetchall()

                if issue_rows:
                    from app.services.alert_service import create_and_broadcast_alert
                    for issue_row in issue_rows:
                        try:
                            create_and_broadcast_alert({
                                'alert_type': 'CHECKLIST_ISSUE',
                                'message': f'[{serial_number}] ELEC 체크리스트 ISSUE: {issue_row["item_name"]} - {issue_row["note"]}',
                                'serial_number': serial_number,
                                'target_role': 'ELEC',
                            })
                        except Exception as ae:
                            logger.error(f"check_elec_completion: CHECKLIST_ISSUE alert failed: {ae}")

        return True

    except PsycopgError as e:
        logger.error(f"check_elec_completion failed: serial={serial_number}, error={e}")
        return False
    finally:
        if conn:
            put_conn(conn)


def _try_elec_close(serial_number: str) -> bool:
    """Dual-Trigger 경로 2: 체크리스트 완료 시 IF_2 확인 → 양쪽 완료면 ELEC 닫기."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT td.id
            FROM app_task_details td
            JOIN work_completion_log wcl ON wcl.task_id = td.id
            WHERE td.serial_number = %s
              AND td.task_id = 'IF_2'
              AND td.task_category = 'ELEC'
            LIMIT 1
            """,
            (serial_number,)
        )
        if_2_completed = cur.fetchone() is not None

        if not if_2_completed:
            logger.info(
                f"ELEC checklist complete but IF_2 not yet done (waiting path 1): "
                f"serial={serial_number}"
            )
            return False

        cur.execute(
            """
            UPDATE completion_status
            SET elec_completed = TRUE,
                updated_at = NOW()
            WHERE serial_number = %s
              AND elec_completed = FALSE
            """,
            (serial_number,)
        )
        conn.commit()

        logger.info(
            f"ELEC close triggered (path 2: checklist last): serial={serial_number}"
        )
        return True

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"_try_elec_close failed (non-blocking): serial={serial_number}, error={e}")
        return False
    finally:
        if conn:
            put_conn(conn)
