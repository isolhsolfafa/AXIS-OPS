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

    # ⭐ v2.11.5 R1: phase=2 GET 시 phase=1 record 의 input_value/selected_value 가
    #    cr (phase=2) LEFT JOIN 결과에서 NULL 응답되는 문제 수정 (2차 read-only inherit).
    #    옵션 A 채택 — phase=1 record 별도 LEFT JOIN (cr_p1) + COALESCE 우선.
    #    Codex 라운드 1 M-A2: cr_p1 조인 4개 조건 (master_id + serial_number + judgment_phase=1 + qr_doc_id) 모두 포함 — DUAL L/R 오상속 차단.
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
            COALESCE(cm.phase1_applicable, TRUE) AS phase1_applicable,
            COALESCE(cm.qi_check_required, FALSE) AS qi_check_required,
            cm.select_options,
            cm.scope_rule,
            cm.trigger_task_id,
            cr.check_result,
            cr.checked_by,
            w.name         AS checked_by_name,
            cr.checked_at,
            cr.note,
            -- ⭐ v2.11.5 R1: phase=1 record 의 input/select 우선 (1차 데이터 inherit)
            COALESCE(cr.selected_value, cr_p1.selected_value) AS selected_value,
            COALESCE(cr.input_value,    cr_p1.input_value)    AS input_value
        FROM checklist.checklist_master cm
        LEFT JOIN checklist.checklist_record cr
            ON cr.master_id      = cm.id
           AND cr.serial_number  = %s
           AND cr.judgment_phase = %s
           AND cr.qr_doc_id     = %s
        -- ⭐ v2.11.5 R1: phase=1 record 별도 LEFT JOIN (4개 조건 — DUAL L/R 분리 보장)
        LEFT JOIN checklist.checklist_record cr_p1
            ON cr_p1.master_id      = cm.id
           AND cr_p1.serial_number  = %s
           AND cr_p1.judgment_phase = 1
           AND cr_p1.qr_doc_id     = %s
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
    # ⭐ v2.11.5 R1: cr_p1 위해 serial_number + qr_doc_id 2개 추가 (params placeholder 정합)
    params: list = [
        serial_number, judgment_phase, qr_doc_id,  # cr (phase=current)
        serial_number, qr_doc_id,                   # cr_p1 (phase=1 고정)
    ] + master_params
    cur.execute(query, params)
    rows = cur.fetchall()

    items = []
    total = 0
    checked = 0

    for row in rows:
        check_result = row['check_result']
        # item_type 컬럼이 없는 경우 fallback
        item_type = row['item_type'] if 'item_type' in row.keys() else 'CHECK'
        # Sprint 60: phase1_applicable 컬럼 기반 (phase1_na는 FE 하위호환)
        phase1_applicable = row.get('phase1_applicable', True)
        phase1_na = not phase1_applicable  # FE 하위호환
        if not phase1_applicable and judgment_phase == 1 and check_result is None:
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
            'phase1_applicable': phase1_applicable,
            'qi_check_required': row.get('qi_check_required', False),
            'select_options': select_options,
            'scope_rule': row.get('scope_rule'),
            'trigger_task_id': row.get('trigger_task_id'),
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


def _normalize_qr_doc_id(serial_number: str, hint: Optional[str] = None) -> str:
    """qr_doc_id 정규화 — SINGLE/DUAL 모델 일관 처리 (Sprint 63-BE).

    TM/ELEC/MECH 공유 normalizer (Sprint 59-BE 재발 방지).

    Rules:
      - SINGLE: 'DOC_{serial_number}'   (예: DOC_GBWS-6905)
      - DUAL Left:  'DOC_{serial_number}-L'
      - DUAL Right: 'DOC_{serial_number}-R'

    Args:
      serial_number: S/N (예: 'GBWS-6905')
      hint: 클라이언트 전송 hint ('L' / 'R' / None / 'DOC_GBWS-7043-L' 같은 full id)

    Returns:
      정규화된 qr_doc_id (string).

    Examples:
      _normalize_qr_doc_id('GBWS-6905')                      → 'DOC_GBWS-6905'
      _normalize_qr_doc_id('GBWS-7043', 'L')                 → 'DOC_GBWS-7043-L'
      _normalize_qr_doc_id('GBWS-7043', 'DOC_GBWS-7043-R')   → 'DOC_GBWS-7043-R' (idempotent)
    """
    if not serial_number:
        return ''

    sn = serial_number.strip()
    if not sn:
        return ''

    if hint:
        h = hint.strip()
        # 이미 정규화 형태면 그대로 (idempotent)
        if h.startswith(f'DOC_{sn}'):
            return h
        # 'L' / 'R' suffix only
        if h.upper() in ('L', 'R'):
            return f'DOC_{sn}-{h.upper()}'

    # 기본 SINGLE
    return f'DOC_{sn}'


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
                    # Phase 1: phase1_applicable=False 항목 제외 (컬럼 기반)
                    if phase_num == 1:
                        p_data['items'] = [
                            i for i in p_data['items']
                            if i.get('phase1_applicable', True)
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

            elif cat == 'TM':
                # ── Sprint 59-BE: TM DUAL/SINGLE 통합 — qr_doc_id 문자열 계산 ──
                if is_dual:
                    qr_doc_ids = [
                        (f'DOC_{serial_number}-L', 'L Tank'),
                        (f'DOC_{serial_number}-R', 'R Tank'),
                    ]
                else:
                    qr_doc_ids = [(f'DOC_{serial_number}', None)]

                for tank_qr, tank_label in qr_doc_ids:
                    t_data = _get_checklist_by_category(
                        cur, serial_number, cat, product_code, scope,
                        judgment_phase, qr_doc_id=tank_qr
                    )
                    t_data['qr_doc_id'] = tank_qr
                    if tank_label:
                        t_data['phase_label'] = tank_label
                    if t_data['summary']['total'] > 0:
                        categories.append(t_data)

            elif cat == 'MECH':
                # ── Sprint 65-BE hotfix (2026-05-06, v2.11.7): ELEC 패턴 + qr_doc_id 명시 ──
                # 모바일 앱 _normalizeQrDocId(sn) = 'DOC_<sn>' 와 정확히 일치 매칭.
                # 이전 else 분기는 qr_doc_id='' 로 SELECT → DB record (DOC_<sn>) 매칭 0건 →
                #   VIEW 성적서 input_value '—' 표시 (5-05 운영 catch).
                #
                # TODO (다음 응용): DUAL INLET S/N L/R 분리 처리
                #   - 현재 운영 데이터 0건 (모든 record SINGLE-style 'DOC_<sn>')
                #   - 향후 worker 가 INLET L/R 별도 입력 시 또는 DRAGON DUAL INLET 분리 시:
                #     qr_doc_ids = [(_normalize_qr_doc_id(sn, 'L'), 'L'), (_normalize_qr_doc_id(sn, 'R'), 'R'), ...]
                #     → TM 패턴 (L463-482) 차용
                #   - BACKLOG: FIX-MECH-DUAL-INLET-L-R-SEPARATION (운영 데이터 발생 시)
                qr_doc_id_for_mech = _normalize_qr_doc_id(serial_number)

                for phase_num, phase_label in [(1, '1차 입력'), (2, '2차 검수')]:
                    p_data = _get_checklist_by_category(
                        cur, serial_number, cat, product_code, scope, phase_num,
                        qr_doc_id=qr_doc_id_for_mech,
                    )
                    # Phase 1: phase1_applicable=False 항목 제외 (Sprint 60-BE 컬럼 기반)
                    if phase_num == 1:
                        p_data['items'] = [
                            i for i in p_data['items']
                            if i.get('phase1_applicable', True)
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

            else:
                # 잠재 신규 카테고리(PI/QI/SI 등) — 기본 fallback (qr_doc_id='')
                # ⚠️ 신규 카테고리 도입 시 ADR-026 표준 검토 후 명시 분기 추가 권장
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
    UPSERT 후 check_tm_completion() 호출하여 전체 완료 여부 판정.

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
        is_complete = check_tm_completion(serial_number, judgment_phase)

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


def check_tm_completion(serial_number: str, judgment_phase: int = 1) -> bool:
    """
    TM 체크리스트 전체 완료 여부 판정 (Sprint 59-BE: qr_doc_id 리스트 기반).

    DUAL 모델: qr_doc_id='DOC_{S/N}-L', 'DOC_{S/N}-R' 두 개 모두 완료돼야 True
    SINGLE 모델: qr_doc_id='DOC_{S/N}' 한 개 완료하면 True
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # product_info 조회 (모델 + 스코프 필터 결정)
        cur.execute(
            "SELECT product_code, model FROM plan.product_info WHERE serial_number = %s",
            (serial_number,)
        )
        product_row = cur.fetchone()
        if not product_row:
            return False
        product_code = product_row['product_code']
        model = product_row['model']

        # tm_checklist_scope 확인
        cur.execute(
            "SELECT setting_value FROM admin_settings WHERE setting_key = 'tm_checklist_scope'"
        )
        scope_row = cur.fetchone()
        scope = 'product_code'
        if scope_row:
            sv = scope_row['setting_value']
            scope = sv if isinstance(sv, str) else str(sv)

        if scope == 'all' or not product_code:
            master_filter = "cm.product_code = 'COMMON' AND cm.category = 'TM'"
            master_params: list = []
        else:
            master_filter = "cm.product_code = %s AND cm.category = 'TM'"
            master_params = [product_code]

        # DUAL 판별 → qr_doc_id 리스트 구성
        is_dual = _is_report_dual_model(model)
        if is_dual:
            qr_doc_ids = [f'DOC_{serial_number}-L', f'DOC_{serial_number}-R']
        else:
            qr_doc_ids = [f'DOC_{serial_number}']

        # qr_doc_id별 루프 — 각각 완료돼야 함
        for qr in qr_doc_ids:
            null_check_query = f"""
                SELECT COUNT(*) AS null_count
                FROM checklist.checklist_master cm
                LEFT JOIN checklist.checklist_record cr
                    ON cr.master_id      = cm.id
                   AND cr.serial_number  = %s
                   AND cr.judgment_phase = %s
                   AND cr.qr_doc_id      = %s
                WHERE {master_filter}
                  AND cm.is_active = TRUE
                  AND cr.check_result IS NULL
            """
            params = [serial_number, judgment_phase, qr] + master_params
            cur.execute(null_check_query, params)
            if cur.fetchone()['null_count'] > 0:
                return False

        # 전체 항목 수 확인 (0건이면 마스터 없음)
        total_query = f"""
            SELECT COUNT(*) AS total_count
            FROM checklist.checklist_master cm
            WHERE {master_filter} AND cm.is_active = TRUE
        """
        cur.execute(total_query, master_params)
        if cur.fetchone()['total_count'] == 0:
            return False

        # 완료! ISSUE note 존재 여부 확인 (qr_doc_id 조건 없이 전체 스캔)
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
            cur.execute(
                "SELECT setting_value FROM admin_settings WHERE setting_key = 'tm_checklist_issue_alert'"
            )
            alert_row = cur.fetchone()
            issue_alert = True
            if alert_row:
                sv = alert_row['setting_value']
                if isinstance(sv, bool):
                    issue_alert = sv
                elif isinstance(sv, str):
                    issue_alert = sv.lower() in ('true', '1')
                else:
                    issue_alert = bool(sv)

            if issue_alert:
                from app.services.alert_service import create_and_broadcast_alert, sn_label
                for issue_row in issue_rows:
                    try:
                        create_and_broadcast_alert({
                            'alert_type': 'CHECKLIST_ISSUE',
                            'message': f'{sn_label(serial_number)} TM 체크리스트 ISSUE: {issue_row["item_name"]} - {issue_row["note"]}',
                            'serial_number': serial_number,
                            'target_role': 'MECH',
                        })
                    except Exception as ae:
                        logger.error(f"check_tm_completion: CHECKLIST_ISSUE alert failed: {ae}")

        return True

    except PsycopgError as e:
        logger.error(f"check_tm_completion failed: serial={serial_number}, error={e}")
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

        # Sprint 60: Phase 1에서 phase1_applicable=False 항목 제외 (컬럼 기반)
        items = data['items']
        if judgment_phase == 1:
            items = [i for i in items if i.get('phase1_applicable', True)]

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

        is_complete = check_elec_completion(serial_number)

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


def check_elec_completion(serial_number: str) -> bool:
    """ELEC 체크리스트 전체 완료 확인 — Phase 1+2 합산 (Sprint 58-BE).
    Phase 1: JIG 제외 WORKER, Phase 2: 전체 WORKER. QI 항상 제외.
    judgment_phase 파라미터 폐기 — 항상 Phase 1+2 전체 확인."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # === Phase 1 확인 (JIG 그룹 제외) ===
        cur.execute(
            """
            SELECT COUNT(*) AS null_count
            FROM checklist.checklist_master cm
            LEFT JOIN checklist.checklist_record cr
                ON cr.master_id      = cm.id
               AND cr.serial_number  = %s
               AND cr.judgment_phase = 1
               AND cr.qr_doc_id     = ''
            WHERE cm.category   = 'ELEC'
              AND cm.is_active  = TRUE
              AND COALESCE(cm.checker_role, 'WORKER') = 'WORKER'
              AND cm.phase1_applicable = TRUE
              AND cr.check_result IS NULL
            """,
            (serial_number,)
        )
        phase1_null = cur.fetchone()['null_count']
        if phase1_null > 0:
            return False

        # === Phase 2 확인 (JIG 포함, 전체 WORKER) ===
        cur.execute(
            """
            SELECT COUNT(*) AS null_count
            FROM checklist.checklist_master cm
            LEFT JOIN checklist.checklist_record cr
                ON cr.master_id      = cm.id
               AND cr.serial_number  = %s
               AND cr.judgment_phase = 2
               AND cr.qr_doc_id     = ''
            WHERE cm.category   = 'ELEC'
              AND cm.is_active  = TRUE
              AND COALESCE(cm.checker_role, 'WORKER') = 'WORKER'
              AND cr.check_result IS NULL
            """,
            (serial_number,)
        )
        phase2_null = cur.fetchone()['null_count']
        if phase2_null > 0:
            return False

        # Phase 1+2 전체 WORKER 항목 수 확인 (0건이면 마스터 없음)
        cur.execute(
            """
            SELECT COUNT(*) AS total_count
            FROM checklist.checklist_master cm
            WHERE cm.category = 'ELEC'
              AND cm.is_active = TRUE
              AND COALESCE(cm.checker_role, 'WORKER') = 'WORKER'
            """
        )
        total_count = cur.fetchone()['total_count']
        if total_count == 0:
            return False

        # ISSUE note 알림 (중복 방지 + Phase 1+2 모두 스캔)
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
                      AND cr.note IS NOT NULL AND cr.note != ''
                      AND cm.category = 'ELEC'
                      AND cm.is_active = TRUE
                    """,
                    (serial_number,)
                )
                issue_rows = cur.fetchall()

                if issue_rows:
                    from app.services.alert_service import create_and_broadcast_alert, sn_label
                    for issue_row in issue_rows:
                        try:
                            create_and_broadcast_alert({
                                'alert_type': 'CHECKLIST_ISSUE',
                                'message': f'{sn_label(serial_number)} ELEC 체크리스트 ISSUE: {issue_row["item_name"]} - {issue_row["note"]}',
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


# ═══════════════════════════════════════════════════════
#  Sprint 63-BE: MECH 체크리스트 (양식 73항목 / 20그룹)
# ═══════════════════════════════════════════════════════

def _resolve_active_master_ids(serial_number: str, judgment_phase: int = 1) -> List[int]:
    """MECH 체크리스트 활성 master id list 반환 (Sprint 63-BE).

    scope_rule + phase1_applicable 필터 적용:
      - scope='all': 모든 모델 활성
      - scope='tank_in_mech': model_config.tank_in_mech=TRUE 모델 (DRAGON/GALLANT/SWS) 만
      - scope='DRAGON' (또는 직접 모델명): model.startswith(scope.upper()) 매칭
      - judgment_phase=1: phase1_applicable=TRUE 항목만
      - judgment_phase=2: 전체 (관리자 (c)안)

    HOTFIX-08 표준: SELECT 후 conn.rollback() 으로 INTRANS 정리.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # (1) model + tank_in_mech 한 번에 조회 (longest-prefix-first)
        cur.execute(
            """
            SELECT pi.model, COALESCE(mc.tank_in_mech, FALSE) AS tank_in_mech
            FROM plan.product_info pi
            LEFT JOIN model_config mc ON pi.model LIKE mc.model_prefix || '%%'
            WHERE pi.serial_number = %s
            ORDER BY length(mc.model_prefix) DESC NULLS LAST
            LIMIT 1
            """,
            (serial_number,)
        )
        row = cur.fetchone()
        conn.rollback()  # HOTFIX-08
        if not row:
            return []
        model = (row['model'] or '').upper()
        tank_in_mech = bool(row['tank_in_mech'])

        # (2) MECH 활성 항목 list
        cur.execute(
            """
            SELECT cm.id, cm.scope_rule, cm.phase1_applicable
            FROM checklist.checklist_master cm
            WHERE cm.category = 'MECH'
              AND cm.product_code = 'COMMON'
              AND cm.is_active = TRUE
            """
        )
        rows = cur.fetchall()
        conn.rollback()  # HOTFIX-08

        # (3) Python 측 필터링
        out: List[int] = []
        for r in rows:
            if judgment_phase == 1 and not r['phase1_applicable']:
                continue
            scope = (r['scope_rule'] or 'all').lower()
            if scope == 'all':
                out.append(r['id'])
            elif scope == 'tank_in_mech':
                if tank_in_mech:
                    out.append(r['id'])
            else:
                # 직접 모델 매칭 (예: scope_rule='DRAGON')
                if model.startswith(scope.upper()):
                    out.append(r['id'])
        return out

    except PsycopgError as e:
        logger.error(f"_resolve_active_master_ids failed: serial={serial_number}, error={e}")
        return []
    finally:
        if conn:
            put_conn(conn)


def check_mech_completion(serial_number: str, judgment_phase: int = 1) -> bool:
    """MECH 체크리스트 완료 여부 (Sprint 63-BE).

    judgment_phase=1: phase1_applicable=TRUE 19개 (v2 INLET 8개 분리 후) scope 적용분 모두 입력 완료.
    judgment_phase=2: 관리자 phase=2 record 충족만 판정 ((c)안 2026-05-01).
                     - 1차 미입력 항목도 관리자가 phase=2 record 입력 시 cover.
                     - 1차 record 강제 안 함.

    SINGLE/DUAL 분기:
      - SINGLE: qr_doc_id='DOC_{S/N}' 한 개 record 만 검증
      - DUAL: 'DOC_{S/N}-L', 'DOC_{S/N}-R' 두 개 모두 완료 시 True
    """
    active_ids = _resolve_active_master_ids(serial_number, judgment_phase)
    if not active_ids:
        return False

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # SINGLE/DUAL 판별 (TM 패턴 차용)
        cur.execute(
            "SELECT model FROM plan.product_info WHERE serial_number = %s",
            (serial_number,)
        )
        product_row = cur.fetchone()
        if not product_row:
            return False
        model = product_row['model']

        is_dual = _is_report_dual_model(model)
        if is_dual:
            qr_doc_ids = [
                _normalize_qr_doc_id(serial_number, 'L'),
                _normalize_qr_doc_id(serial_number, 'R'),
            ]
        else:
            qr_doc_ids = [_normalize_qr_doc_id(serial_number)]

        # qr_doc_id별 loop — 각각 active_ids 모두 채워져야 함
        for qr in qr_doc_ids:
            cur.execute(
                """
                SELECT COUNT(*) AS checked
                FROM checklist.checklist_record
                WHERE master_id = ANY(%(ids)s)
                  AND serial_number = %(serial_number)s
                  AND judgment_phase = %(judgment_phase)s
                  AND qr_doc_id = %(qr_doc_id)s
                  AND check_result IS NOT NULL
                """,
                {
                    'ids': active_ids,
                    'serial_number': serial_number,
                    'judgment_phase': judgment_phase,
                    'qr_doc_id': qr,
                }
            )
            row = cur.fetchone()
            checked = row['checked'] if row else 0
            if checked < len(active_ids):
                return False

        return True

    except PsycopgError as e:
        logger.error(f"check_mech_completion failed: serial={serial_number}, error={e}")
        return False
    finally:
        if conn:
            put_conn(conn)


def get_mech_checklist(serial_number: str, judgment_phase: int = 1, qr_doc_id: str = '') -> Dict[str, Any]:
    """MECH 체크리스트 조회 (Sprint 63-BE + R2-1 patch v2.11.1) — ELEC 패턴 + scope_rule + tank_in_mech 응답.

    73 항목 모두 반환 (FE 가 scope_rule 보고 disabled NA 처리).
    judgment_phase=1 시 phase1_applicable=False 항목은 자동 NA 처리 (기존 ELEC 동작 동일).
    qr_doc_id 빈 문자열 시 _normalize_qr_doc_id() 로 'DOC_{S/N}' SINGLE 자동 채움.
    R2-1 patch (Codex 라운드 2, 2026-05-04): 응답에 tank_in_mech bool 추가 — FE 별도 model_config 호출 회피.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # R2-1 patch: model + tank_in_mech 한 번에 lookup (FE _isScopeMatched 활용)
        cur.execute(
            """
            SELECT pi.product_code, pi.sales_order, pi.model,
                   COALESCE(mc.tank_in_mech, FALSE) AS tank_in_mech
            FROM plan.product_info pi
            LEFT JOIN model_config mc ON pi.model LIKE mc.model_prefix || '%%'
            WHERE pi.serial_number = %s
            ORDER BY length(mc.model_prefix) DESC NULLS LAST
            LIMIT 1
            """,
            (serial_number,)
        )
        product_row = cur.fetchone()
        conn.rollback()  # HOTFIX-08
        product_code = product_row['product_code'] if product_row else None
        sales_order = product_row['sales_order'] if product_row else None
        model = product_row['model'] if product_row else None
        tank_in_mech = bool(product_row['tank_in_mech']) if product_row else False  # R2-1

        # qr_doc_id 정규화 (Sprint 59-BE 재발 방지)
        normalized_qr = _normalize_qr_doc_id(serial_number, qr_doc_id) if qr_doc_id else _normalize_qr_doc_id(serial_number)

        data = _get_checklist_by_category(
            cur, serial_number, 'MECH', product_code, 'all', judgment_phase,
            qr_doc_id=normalized_qr
        )

        # Phase 1: phase1_applicable=False 항목 제외 (Sprint 60 ELEC 패턴 동일)
        items = data['items']
        if judgment_phase == 1:
            items = [i for i in items if i.get('phase1_applicable', True)]

        from collections import OrderedDict
        groups_dict: OrderedDict = OrderedDict()
        for item in items:
            g = item['item_group']
            if g not in groups_dict:
                groups_dict[g] = []
            groups_dict[g].append(item)

        groups = [{'group_name': k, 'items': v} for k, v in groups_dict.items()]

        # summary 재계산 (Phase 1 제외 반영)
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
            'tank_in_mech': tank_in_mech,  # R2-1 patch (Codex 라운드 2): FE _isScopeMatched 활용
            'judgment_phase': judgment_phase,
            'qr_doc_id': normalized_qr,
            'groups': groups,
            'summary': summary,
        }

    except PsycopgError as e:
        logger.error(f"get_mech_checklist failed: serial={serial_number}, error={e}")
        raise
    finally:
        if conn:
            put_conn(conn)


def upsert_mech_check(
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
    """MECH 체크리스트 항목 체크 UPSERT (Sprint 63-BE) — ELEC 패턴 복제.

    item_type='CHECK': PASS/NA 라디오
    item_type='SELECT': selected_value (드롭다운 값)
    item_type='INPUT': input_value (자유 텍스트)
    """
    if check_result not in ('PASS', 'NA'):
        raise ValueError(f"INVALID_CHECK_RESULT: '{check_result}'")

    # qr_doc_id 정규화
    normalized_qr = _normalize_qr_doc_id(serial_number, qr_doc_id) if qr_doc_id else _normalize_qr_doc_id(serial_number)

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT id FROM checklist.checklist_master WHERE id = %s AND category = 'MECH'",
            (master_id,)
        )
        if not cur.fetchone():
            raise ValueError(f"MASTER_NOT_FOUND: master_id={master_id} (MECH)")

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
            (serial_number, master_id, judgment_phase, check_result,
             worker_id, note, selected_value, input_value, normalized_qr)
        )
        conn.commit()

        logger.info(
            f"MECH checklist upserted: serial={serial_number}, master_id={master_id}, "
            f"check_result={check_result}, worker_id={worker_id}, phase={judgment_phase}, "
            f"qr_doc_id={normalized_qr}"
        )

        is_complete = check_mech_completion(serial_number, judgment_phase)

        return {
            'master_id': master_id,
            'check_result': check_result,
            'is_complete': is_complete,
            'qr_doc_id': normalized_qr,
        }

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"upsert_mech_check failed: serial={serial_number}, master_id={master_id}, error={e}")
        raise
    finally:
        if conn:
            put_conn(conn)
