"""
체크리스트 라우트 (Sprint 11)
엔드포인트: /api/app/checklist/*, /api/admin/checklist/*
checklist 스키마의 checklist_master + checklist_record CRUD
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Tuple, Dict, Any

from app.middleware.jwt_auth import jwt_required, admin_required, get_current_worker_id
from app.models.worker import get_worker_by_id, get_db_connection
from psycopg2 import Error as PsycopgError
from app.db_pool import put_conn
from app.services import checklist_service


logger = logging.getLogger(__name__)

checklist_bp = Blueprint("checklist", __name__)


@checklist_bp.route("/api/app/checklist/<string:serial_number>/<string:category>", methods=["GET"])
@jwt_required
def get_checklist(serial_number: str, category: str) -> Tuple[Dict[str, Any], int]:
    """
    제품 시리얼 번호 + 카테고리로 체크리스트 항목 조회 (Sprint 11)

    checklist_master를 product_info.product_code로 JOIN,
    checklist_record를 LEFT JOIN으로 체크 현황 포함.

    Path Parameters:
        serial_number: 제품 시리얼 번호
        category: 체크리스트 카테고리 (HOOKUP, MECH, ELEC, PI, QI)

    Headers:
        Authorization: Bearer {token}

    Response:
        200: {
            "items": [
                {
                    "master_id": int,
                    "item_name": str,
                    "item_order": int,
                    "description": str|null,
                    "is_active": bool,
                    "is_checked": bool,
                    "checked_by": int|null,
                    "checked_by_name": str|null,
                    "checked_at": str|null,
                    "note": str|null
                },
                ...
            ],
            "serial_number": str,
            "category": str,
            "total": int
        }
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # product_info에서 product_code 조회
        cur.execute(
            "SELECT product_code FROM plan.product_info WHERE serial_number = %s",
            (serial_number,)
        )
        product_row = cur.fetchone()
        if not product_row or not product_row['product_code']:
            # product_code 없으면 빈 결과 반환 (마스터 데이터 없음)
            return jsonify({
                'items': [],
                'serial_number': serial_number,
                'category': category,
                'total': 0
            }), 200

        product_code = product_row['product_code']

        # checklist_master + checklist_record LEFT JOIN
        cur.execute(
            """
            SELECT
                cm.id AS master_id,
                cm.item_name,
                cm.item_order,
                cm.description,
                cm.is_active,
                COALESCE(cr.is_checked, FALSE) AS is_checked,
                cr.checked_by,
                w.name AS checked_by_name,
                cr.checked_at,
                cr.note
            FROM checklist.checklist_master cm
            LEFT JOIN checklist.checklist_record cr
                ON cr.master_id = cm.id
                AND cr.serial_number = %s
            LEFT JOIN workers w ON w.id = cr.checked_by
            WHERE cm.product_code = %s
              AND cm.category = %s
              AND cm.is_active = TRUE
            ORDER BY cm.item_order ASC, cm.id ASC
            """,
            (serial_number, product_code, category)
        )
        rows = cur.fetchall()

        items = []
        for row in rows:
            items.append({
                'master_id': row['master_id'],
                'item_name': row['item_name'],
                'item_order': row['item_order'],
                'description': row['description'],
                'is_active': row['is_active'],
                'is_checked': row['is_checked'],
                'checked_by': row['checked_by'],
                'checked_by_name': row['checked_by_name'],
                'checked_at': row['checked_at'].isoformat() if row['checked_at'] else None,
                'note': row['note'],
            })

        return jsonify({
            'items': items,
            'serial_number': serial_number,
            'category': category,
            'total': len(items),
        }), 200

    except PsycopgError as e:
        logger.error(f"Checklist GET failed: serial={serial_number}, category={category}, error={e}")
        return jsonify({
            'error': 'DB_ERROR',
            'message': '체크리스트 조회 실패'
        }), 500
    finally:
        if conn:
            put_conn(conn)


@checklist_bp.route("/api/app/checklist/check", methods=["PUT"])
@jwt_required
def upsert_checklist_record() -> Tuple[Dict[str, Any], int]:
    """
    체크리스트 항목 체크/해제 (UPSERT) (Sprint 11)

    Request Body:
        {
            "serial_number": str,
            "master_id": int,
            "is_checked": bool,
            "note": str  # optional
        }

    Headers:
        Authorization: Bearer {token}

    Response:
        200: {
            "message": "체크리스트가 업데이트되었습니다.",
            "serial_number": str,
            "master_id": int,
            "is_checked": bool,
            "checked_at": str|null
        }
        400: {"error": "INVALID_REQUEST", "message": "..."}
        404: {"error": "MASTER_NOT_FOUND", "message": "..."}
    """
    data = request.get_json()

    if not data or not all(k in data for k in ['serial_number', 'master_id', 'is_checked']):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': '필수 필드가 누락되었습니다. (serial_number, master_id, is_checked)'
        }), 400

    serial_number = data['serial_number']
    master_id = data['master_id']
    is_checked = bool(data['is_checked'])
    note = data.get('note')
    worker_id = get_current_worker_id()

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
            return jsonify({
                'error': 'MASTER_NOT_FOUND',
                'message': '체크리스트 마스터 항목을 찾을 수 없습니다.'
            }), 404

        # UPSERT
        if is_checked:
            checked_by = worker_id
            checked_at_expr = "NOW()"
        else:
            checked_by = None
            checked_at_expr = "NULL"

        cur.execute(
            f"""
            INSERT INTO checklist.checklist_record
                (serial_number, master_id, judgment_phase, is_checked, checked_by, checked_at, note, updated_at)
            VALUES (%s, %s, 1, %s, %s, {checked_at_expr}, %s, NOW())
            ON CONFLICT (serial_number, master_id, judgment_phase) DO UPDATE
            SET is_checked  = EXCLUDED.is_checked,
                checked_by  = EXCLUDED.checked_by,
                checked_at  = EXCLUDED.checked_at,
                note        = EXCLUDED.note,
                updated_at  = NOW()
            RETURNING id, checked_at
            """,
            (serial_number, master_id, is_checked, checked_by, note)
        )
        result_row = cur.fetchone()
        conn.commit()

        checked_at_val = result_row['checked_at'].isoformat() if result_row and result_row['checked_at'] else None

        logger.info(
            f"Checklist record upserted: serial={serial_number}, master_id={master_id}, "
            f"is_checked={is_checked}, worker_id={worker_id}"
        )

        return jsonify({
            'message': '체크리스트가 업데이트되었습니다.',
            'serial_number': serial_number,
            'master_id': master_id,
            'is_checked': is_checked,
            'checked_at': checked_at_val,
        }), 200

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Checklist PUT failed: serial={serial_number}, master_id={master_id}, error={e}")
        return jsonify({
            'error': 'DB_ERROR',
            'message': '체크리스트 업데이트 실패'
        }), 500
    finally:
        if conn:
            put_conn(conn)


@checklist_bp.route("/api/admin/checklist/master", methods=["GET"])
@jwt_required
@admin_required
def list_checklist_master() -> Tuple[Dict[str, Any], int]:
    """
    체크리스트 마스터 항목 목록 조회 (관리자 전용, Sprint 52)

    Query Parameters:
        category: str (필수) — 'TM', 'MECH', 'ELEC' 등
        product_code: str (선택) — 미지정 시 전체
        include_inactive: bool (선택, 기본 false) — 비활성 항목 포함 여부

    Headers:
        Authorization: Bearer {token}

    Response:
        200: {
            "items": [
                {
                    "id": int,
                    "product_code": str,
                    "category": str,
                    "item_group": str|null,
                    "item_name": str,
                    "item_order": int,
                    "description": str|null,
                    "is_active": bool
                }, ...
            ],
            "total": int
        }
    """
    category = request.args.get('category', '').strip()
    if not category:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'category 파라미터가 필요합니다.'
        }), 400

    product_code = request.args.get('product_code', '').strip() or None
    include_inactive_raw = request.args.get('include_inactive', 'false').lower()
    include_inactive = include_inactive_raw in ('true', '1', 'yes')

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        conditions = ['cm.category = %s']
        params: list = [category]

        if product_code:
            conditions.append('cm.product_code = %s')
            params.append(product_code)

        if not include_inactive:
            conditions.append('cm.is_active = TRUE')

        where_clause = ' AND '.join(conditions)

        cur.execute(
            f"""
            SELECT
                cm.id,
                cm.product_code,
                cm.category,
                cm.item_group,
                cm.item_name,
                cm.item_order,
                cm.description,
                cm.is_active
            FROM checklist.checklist_master cm
            WHERE {where_clause}
            ORDER BY cm.item_order ASC, cm.id ASC
            """,
            params
        )
        rows = cur.fetchall()

        items = [
            {
                'id': row['id'],
                'product_code': row['product_code'],
                'category': row['category'],
                'item_group': row['item_group'],
                'item_name': row['item_name'],
                'item_order': row['item_order'],
                'description': row['description'],
                'is_active': row['is_active'],
            }
            for row in rows
        ]

        return jsonify({'items': items, 'total': len(items)}), 200

    except PsycopgError as e:
        logger.error(f"Checklist master list failed: category={category}, error={e}")
        return jsonify({'error': 'DB_ERROR', 'message': '체크리스트 목록 조회 실패'}), 500
    finally:
        if conn:
            put_conn(conn)


@checklist_bp.route("/api/admin/checklist/master", methods=["POST"])
@jwt_required
@admin_required
def create_checklist_master() -> Tuple[Dict[str, Any], int]:
    """
    체크리스트 마스터 항목 개별 추가 (관리자 전용, Sprint 52)

    Request Body:
        {
            "product_code": str,    — 필수 (예: "ALL" 또는 특정 코드)
            "category": str,        — 필수 (예: "TM", "MECH")
            "item_group": str,      — 선택 (TM 전용: BURNER, REACTOR 등)
            "item_name": str,       — 필수
            "item_order": int,      — 선택, 기본 0
            "description": str      — 선택
        }

    Headers:
        Authorization: Bearer {token}

    Response:
        201: {"id": int, "message": "항목이 추가되었습니다."}
        400: {"error": "INVALID_REQUEST", "message": "..."}
        409: {"error": "CONFLICT", "message": "이미 존재하는 항목입니다."}
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'INVALID_REQUEST', 'message': '요청 본문이 없습니다.'}), 400

    product_code = (data.get('product_code') or '').strip()
    category = (data.get('category') or '').strip()
    item_name = (data.get('item_name') or '').strip()

    if not product_code or not category or not item_name:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': '필수 필드가 누락되었습니다. (product_code, category, item_name)'
        }), 400

    item_group = (data.get('item_group') or '').strip() or None
    item_order = data.get('item_order', 0)
    description = (data.get('description') or '').strip() or None

    try:
        item_order = int(item_order)
    except (ValueError, TypeError):
        item_order = 0

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO checklist.checklist_master
                (product_code, category, item_group, item_name, item_order, description, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            RETURNING id
            """,
            (product_code, category, item_group, item_name, item_order, description)
        )
        result = cur.fetchone()
        conn.commit()

        new_id = result['id']
        logger.info(f"Checklist master created: id={new_id}, category={category}, product_code={product_code}")

        return jsonify({'id': new_id, 'message': '항목이 추가되었습니다.'}), 201

    except PsycopgError as e:
        if conn:
            conn.rollback()
        err_str = str(e)
        # UNIQUE 제약 위반 (product_code + category + item_name)
        if 'unique' in err_str.lower() or 'duplicate' in err_str.lower():
            return jsonify({'error': 'CONFLICT', 'message': '이미 존재하는 항목입니다.'}), 409
        logger.error(f"Checklist master create failed: {e}")
        return jsonify({'error': 'DB_ERROR', 'message': '체크리스트 항목 추가 실패'}), 500
    finally:
        if conn:
            put_conn(conn)


@checklist_bp.route("/api/admin/checklist/master/<int:master_id>", methods=["PUT"])
@jwt_required
@admin_required
def update_checklist_master(master_id: int) -> Tuple[Dict[str, Any], int]:
    """
    체크리스트 마스터 항목 수정 (관리자 전용, Sprint 52)

    ⚠️ product_code, category는 수정 불가 (PK 구성 요소)

    Request Body (모든 필드 선택):
        {
            "item_name": str,
            "item_group": str,
            "item_order": int,
            "description": str
        }

    Headers:
        Authorization: Bearer {token}

    Response:
        200: {"message": "항목이 수정되었습니다."}
        400: {"error": "INVALID_REQUEST", "message": "..."}
        404: {"error": "NOT_FOUND", "message": "..."}
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'INVALID_REQUEST', 'message': '요청 본문이 없습니다.'}), 400

    # 수정 가능 필드만 추출
    updates: Dict[str, Any] = {}
    if 'item_name' in data:
        v = (data['item_name'] or '').strip()
        if not v:
            return jsonify({'error': 'INVALID_REQUEST', 'message': 'item_name은 빈 값일 수 없습니다.'}), 400
        updates['item_name'] = v
    if 'item_group' in data:
        updates['item_group'] = (data['item_group'] or '').strip() or None
    if 'item_order' in data:
        try:
            updates['item_order'] = int(data['item_order'])
        except (ValueError, TypeError):
            return jsonify({'error': 'INVALID_REQUEST', 'message': 'item_order는 정수여야 합니다.'}), 400
    if 'description' in data:
        updates['description'] = (data['description'] or '').strip() or None

    if not updates:
        return jsonify({'error': 'INVALID_REQUEST', 'message': '수정할 필드가 없습니다.'}), 400

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 존재 확인
        cur.execute("SELECT id FROM checklist.checklist_master WHERE id = %s", (master_id,))
        if not cur.fetchone():
            return jsonify({'error': 'NOT_FOUND', 'message': '체크리스트 항목을 찾을 수 없습니다.'}), 404

        set_clauses = ', '.join(f'{col} = %s' for col in updates)
        values = list(updates.values()) + [master_id]

        cur.execute(
            f"UPDATE checklist.checklist_master SET {set_clauses}, updated_at = NOW() WHERE id = %s",
            values
        )
        conn.commit()

        logger.info(f"Checklist master updated: id={master_id}, fields={list(updates.keys())}")
        return jsonify({'message': '항목이 수정되었습니다.'}), 200

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Checklist master update failed: id={master_id}, error={e}")
        return jsonify({'error': 'DB_ERROR', 'message': '체크리스트 항목 수정 실패'}), 500
    finally:
        if conn:
            put_conn(conn)


@checklist_bp.route("/api/admin/checklist/master/<int:master_id>/toggle", methods=["PATCH"])
@jwt_required
@admin_required
def toggle_checklist_master(master_id: int) -> Tuple[Dict[str, Any], int]:
    """
    체크리스트 마스터 항목 활성/비활성 토글 (관리자 전용, Sprint 52)

    비활성화해도 기존 checklist_record는 유지 (삭제 아님).

    Headers:
        Authorization: Bearer {token}

    Response:
        200: {"id": int, "is_active": bool, "message": "..."}
        404: {"error": "NOT_FOUND", "message": "..."}
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE checklist.checklist_master
            SET is_active = NOT is_active, updated_at = NOW()
            WHERE id = %s
            RETURNING id, is_active
            """,
            (master_id,)
        )
        result = cur.fetchone()
        if not result:
            return jsonify({'error': 'NOT_FOUND', 'message': '체크리스트 항목을 찾을 수 없습니다.'}), 404

        conn.commit()

        new_active = result['is_active']
        status_label = '활성화' if new_active else '비활성화'
        logger.info(f"Checklist master toggled: id={master_id}, is_active={new_active}")

        return jsonify({
            'id': master_id,
            'is_active': new_active,
            'message': f'항목이 {status_label}되었습니다.',
        }), 200

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Checklist master toggle failed: id={master_id}, error={e}")
        return jsonify({'error': 'DB_ERROR', 'message': '체크리스트 항목 토글 실패'}), 500
    finally:
        if conn:
            put_conn(conn)


@checklist_bp.route("/api/admin/checklist/import", methods=["POST"])
@jwt_required
@admin_required
def import_checklist_master() -> Tuple[Dict[str, Any], int]:
    """
    체크리스트 마스터 데이터 Excel 가져오기 (관리자 전용, Sprint 11)

    Excel 파일 형식:
        - 컬럼: product_code, category, item_name, item_order (optional), description (optional)

    Form Data:
        file: Excel 파일 (.xlsx, .xls)

    Headers:
        Authorization: Bearer {token}

    Response:
        200: {"message": "...", "imported": int, "updated": int, "errors": [...]}
        400: {"error": "INVALID_FILE|INVALID_REQUEST", "message": "..."}
    """
    if 'file' not in request.files:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'Excel 파일이 필요합니다. (form-data: file)'
        }), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({
            'error': 'INVALID_FILE',
            'message': '파일명이 없습니다.'
        }), 400

    filename_lower = file.filename.lower()
    if not (filename_lower.endswith('.xlsx') or filename_lower.endswith('.xls')):
        return jsonify({
            'error': 'INVALID_FILE',
            'message': 'Excel 파일(.xlsx, .xls)만 허용됩니다.'
        }), 400

    try:
        import openpyxl
        wb = openpyxl.load_workbook(file, read_only=True, data_only=True)
        ws = wb.active
    except Exception as e:
        logger.error(f"Excel parsing failed: {e}")
        return jsonify({
            'error': 'INVALID_FILE',
            'message': f'Excel 파일 파싱 실패: {str(e)}'
        }), 400

    rows_data = list(ws.iter_rows(values_only=True))
    if not rows_data:
        return jsonify({
            'error': 'INVALID_FILE',
            'message': 'Excel 파일이 비어있습니다.'
        }), 400

    # 헤더 행 파싱 (첫 번째 행)
    header = [str(h).strip().lower() if h else '' for h in rows_data[0]]
    required_cols = {'product_code', 'category', 'item_name'}
    missing_cols = required_cols - set(header)
    if missing_cols:
        return jsonify({
            'error': 'INVALID_FILE',
            'message': f'필수 컬럼이 누락되었습니다: {", ".join(missing_cols)}'
        }), 400

    col_idx = {col: i for i, col in enumerate(header) if col}

    imported = 0
    updated = 0
    errors = []

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        for row_num, row in enumerate(rows_data[1:], start=2):
            try:
                product_code = str(row[col_idx['product_code']]).strip() if row[col_idx['product_code']] else None
                category = str(row[col_idx['category']]).strip() if row[col_idx['category']] else None
                item_name = str(row[col_idx['item_name']]).strip() if row[col_idx['item_name']] else None

                if not product_code or not category or not item_name:
                    errors.append(f'Row {row_num}: product_code, category, item_name 값이 없습니다.')
                    continue

                item_order = 0
                if 'item_order' in col_idx and row[col_idx['item_order']] is not None:
                    try:
                        item_order = int(row[col_idx['item_order']])
                    except (ValueError, TypeError):
                        item_order = 0

                description = None
                if 'description' in col_idx and row[col_idx['description']]:
                    description = str(row[col_idx['description']]).strip()

                cur.execute(
                    """
                    INSERT INTO checklist.checklist_master
                        (product_code, category, item_name, item_order, description, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (product_code, category, item_name) DO UPDATE
                    SET item_order  = EXCLUDED.item_order,
                        description = EXCLUDED.description,
                        updated_at  = NOW()
                    RETURNING id,
                              (xmax = 0) AS is_new
                    """,
                    (product_code, category, item_name, item_order, description)
                )
                result = cur.fetchone()
                if result and result['is_new']:
                    imported += 1
                else:
                    updated += 1

            except Exception as row_e:
                errors.append(f'Row {row_num}: {str(row_e)}')

        conn.commit()

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Checklist import DB error: {e}")
        return jsonify({
            'error': 'DB_ERROR',
            'message': f'데이터베이스 오류: {str(e)}'
        }), 500
    finally:
        if conn:
            put_conn(conn)

    logger.info(f"Checklist import done: imported={imported}, updated={updated}, errors={len(errors)}")

    return jsonify({
        'message': f'체크리스트 마스터 데이터가 가져와졌습니다. (신규: {imported}, 업데이트: {updated})',
        'imported': imported,
        'updated': updated,
        'errors': errors,
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 52: TM 전용 체크리스트 API
# ─────────────────────────────────────────────────────────────────────────────

@checklist_bp.route("/api/app/checklist/tm/<string:serial_number>", methods=["GET"])
@jwt_required
def get_tm_checklist(serial_number: str) -> Tuple[Dict[str, Any], int]:
    """
    TM 체크리스트 조회 — item_group별 그룹핑 응답 (Sprint 52)

    기존 GET /api/app/checklist/<sn>/<category>와 다른 점:
      - item_group별 그룹핑 응답
      - check_result (PASS/NA/null) 반환 (is_checked 대신)
      - summary (total, checked, remaining, is_complete) 포함
      - O/N(sales_order) 포함

    Path Parameters:
        serial_number: 제품 시리얼 번호

    Query Parameters:
        phase: 판정 차수 (기본 1)

    Headers:
        Authorization: Bearer {token}

    Response:
        200: {
            "serial_number": str,
            "sales_order": str|null,
            "model": str|null,
            "groups": [{"group_name": str, "items": [...]}],
            "summary": {"total": int, "checked": int, "remaining": int, "is_complete": bool}
        }
    """
    try:
        phase = int(request.args.get('phase', 1))
    except (ValueError, TypeError):
        phase = 1

    result = checklist_service.get_tm_checklist(serial_number, judgment_phase=phase)
    return jsonify(result), 200


@checklist_bp.route("/api/app/checklist/tm/check", methods=["PUT"])
@jwt_required
def upsert_tm_checklist_record() -> Tuple[Dict[str, Any], int]:
    """
    TM 체크리스트 항목 체크 (UPSERT) (Sprint 52)

    check_result: 'PASS' 또는 'NA'만 허용 (boolean is_checked 대신 문자열).
    권한 체크: admin_settings.tm_checklist_1st_checker
      - 'is_manager': 호출자가 is_manager=True인지 확인
      - 'user': 모든 인증 유저 허용

    Request Body:
        {
            "serial_number": str,
            "master_id": int,
            "check_result": "PASS" | "NA",
            "note": str  (optional — ISSUE 내용)
        }

    Headers:
        Authorization: Bearer {token}

    Response:
        200: {"master_id": int, "check_result": str, "is_complete": bool}
        400: {"error": "INVALID_REQUEST"|"INVALID_CHECK_RESULT", "message": "..."}
        403: {"error": "FORBIDDEN", "message": "..."}
        404: {"error": "MASTER_NOT_FOUND", "message": "..."}
    """
    data = request.get_json()
    if not data or not all(k in data for k in ['serial_number', 'master_id', 'check_result']):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': '필수 필드가 누락되었습니다. (serial_number, master_id, check_result)'
        }), 400

    check_result = data.get('check_result', '').strip().upper()
    if check_result not in ('PASS', 'NA'):
        return jsonify({
            'error': 'INVALID_CHECK_RESULT',
            'message': "check_result는 'PASS' 또는 'NA'만 허용됩니다."
        }), 400

    worker_id = get_current_worker_id()

    # 권한 체크: tm_checklist_1st_checker 설정 확인
    conn_check = None
    try:
        conn_check = get_db_connection()
        cur_check = conn_check.cursor()
        cur_check.execute(
            "SELECT setting_value FROM admin_settings WHERE setting_key = 'tm_checklist_1st_checker'"
        )
        row_check = cur_check.fetchone()
        checker_setting = 'is_manager'  # default
        if row_check:
            sv = row_check['setting_value']
            checker_setting = sv if isinstance(sv, str) else str(sv)
    except Exception as e:
        logger.warning(f"Failed to read tm_checklist_1st_checker: {e}")
        checker_setting = 'is_manager'
    finally:
        if conn_check:
            put_conn(conn_check)

    if checker_setting == 'is_manager':
        # 호출자 is_manager 확인
        worker = get_worker_by_id(worker_id)
        if not worker or not worker.is_manager:
            return jsonify({
                'error': 'FORBIDDEN',
                'message': 'TM 체크리스트 검수는 관리자(is_manager)만 수행할 수 있습니다.'
            }), 403

    serial_number = data['serial_number']
    master_id = data['master_id']
    note = data.get('note') or None
    try:
        phase = int(data.get('phase', 1))
    except (ValueError, TypeError):
        phase = 1

    try:
        result = checklist_service.upsert_tm_check(
            serial_number=serial_number,
            master_id=master_id,
            check_result=check_result,
            note=note,
            worker_id=worker_id,
            judgment_phase=phase,
        )
        return jsonify(result), 200

    except ValueError as ve:
        err_str = str(ve)
        if 'MASTER_NOT_FOUND' in err_str:
            return jsonify({'error': 'MASTER_NOT_FOUND', 'message': '체크리스트 항목을 찾을 수 없습니다.'}), 404
        return jsonify({'error': 'INVALID_CHECK_RESULT', 'message': err_str}), 400

    except PsycopgError as e:
        logger.error(f"TM checklist PUT failed: serial={serial_number}, master_id={master_id}, error={e}")
        return jsonify({'error': 'DB_ERROR', 'message': 'TM 체크리스트 업데이트 실패'}), 500


@checklist_bp.route("/api/app/checklist/tm/<string:serial_number>/status", methods=["GET"])
@jwt_required
def get_tm_checklist_status(serial_number: str) -> Tuple[Dict[str, Any], int]:
    """
    TM 체크리스트 완료 상태 요약 조회 (Sprint 52)

    실적 조건 연동 시 다른 서비스에서 체크리스트 완료 여부 확인에도 활용.

    Path Parameters:
        serial_number: 제품 시리얼 번호

    Query Parameters:
        phase: 판정 차수 (기본 1)

    Headers:
        Authorization: Bearer {token}

    Response:
        200: {
            "is_complete": bool,
            "completed_at": str|null,
            "checked_count": int,
            "total_count": int
        }
    """
    try:
        phase = int(request.args.get('phase', 1))
    except (ValueError, TypeError):
        phase = 1

    result = checklist_service.get_tm_checklist_status(serial_number, judgment_phase=phase)
    return jsonify(result), 200
