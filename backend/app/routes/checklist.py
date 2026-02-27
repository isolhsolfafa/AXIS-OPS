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
            conn.close()


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
                (serial_number, master_id, is_checked, checked_by, checked_at, note, updated_at)
            VALUES (%s, %s, %s, %s, {checked_at_expr}, %s, NOW())
            ON CONFLICT (serial_number, master_id) DO UPDATE
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
            conn.close()


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
            conn.close()

    logger.info(f"Checklist import done: imported={imported}, updated={updated}, errors={len(errors)}")

    return jsonify({
        'message': f'체크리스트 마스터 데이터가 가져와졌습니다. (신규: {imported}, 업데이트: {updated})',
        'imported': imported,
        'updated': updated,
        'errors': errors,
    }), 200
