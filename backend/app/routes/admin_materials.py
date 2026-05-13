"""
Admin 자재 마스터 관리 라우트 — Sprint 66-BE Step 4 (v2.12.3)
엔드포인트: /api/admin/materials/*

권한: @jwt_required + @gst_or_admin_required (Sprint 27 v1.7.4 표준)
- admin (is_admin=TRUE) OR GST 회사 직원

기능:
- GET /api/admin/materials — 자재 목록 검색 + 페이지네이션 (category / keyword / description filter)
- POST /api/admin/materials — 신규 자재 등록 (ON CONFLICT DO UPDATE)
- PATCH /api/admin/materials/<id> — 자재 사양 수정
- PATCH /api/admin/materials/<id>/deactivate — 자재 비활성화 (soft delete, RESTRICT FK 안전)

후속 BACKLOG: /api/admin/materials/upload (Excel 일괄 업로드 — generator script 패턴 차용)
"""
import logging
from typing import Any, Dict, List, Optional

from flask import Blueprint, request, jsonify, g
from psycopg2 import Error as PsycopgError
from psycopg2.extras import RealDictCursor

from app.middleware.jwt_auth import jwt_required, gst_or_admin_required
from app.models.worker import get_db_connection
from app.db_pool import put_conn


logger = logging.getLogger(__name__)

admin_materials_bp = Blueprint(
    'admin_materials',
    __name__,
    url_prefix='/api/admin/materials',
)


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/admin/materials — 자재 목록 검색 + 페이지네이션
# ═════════════════════════════════════════════════════════════════════════════

@admin_materials_bp.route('', methods=['GET'])
@admin_materials_bp.route('/', methods=['GET'])
@jwt_required
@gst_or_admin_required
def list_materials():
    """자재 마스터 검색 + 페이지네이션.

    Query params:
        category: str (optional) — 카테고리 필터 (정확 일치)
        keyword: str (optional) — item_name + item_code ILIKE 검색
        description: str (optional) — description ILIKE 검색 (가스 종류 LNG/CDA/O2/N2)
        is_active: 'true' | 'false' | 'all' (default: 'true')
        page: int (default 1)
        per_page: int (default 50, max 200)

    Returns:
        {
            "items": [{material dict}, ...],
            "total": int,
            "page": int,
            "per_page": int
        }
    """
    category = request.args.get('category', '').strip() or None
    keyword = request.args.get('keyword', '').strip() or None
    description = request.args.get('description', '').strip() or None
    is_active = request.args.get('is_active', 'true').lower()
    page = max(1, int(request.args.get('page', 1)))
    per_page = min(200, max(1, int(request.args.get('per_page', 50))))
    offset = (page - 1) * per_page

    # WHERE 절 동적 조립
    where_clauses: List[str] = []
    params: List[Any] = []

    if is_active == 'true':
        where_clauses.append("is_active = TRUE")
    elif is_active == 'false':
        where_clauses.append("is_active = FALSE")
    # 'all' → 필터 없음

    if category:
        where_clauses.append("category ILIKE %s")
        params.append(f'%{category}%')

    if keyword:
        where_clauses.append("(item_name ILIKE %s OR item_code ILIKE %s)")
        params.extend([f'%{keyword}%', f'%{keyword}%'])

    if description:
        where_clauses.append("description ILIKE %s")
        params.append(f'%{description}%')

    where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 전체 건수
            cur.execute(
                f"SELECT COUNT(*) AS cnt FROM checklist.material_master WHERE {where_sql}",
                params,
            )
            total = cur.fetchone()['cnt']

            # 목록 조회
            cur.execute(
                f"""
                SELECT id, item_code, item_name, category, spec_1, spec_2, unit,
                       description, is_active, created_at, updated_at
                  FROM checklist.material_master
                 WHERE {where_sql}
                 ORDER BY item_code
                 LIMIT %s OFFSET %s
                """,
                params + [per_page, offset],
            )
            rows = cur.fetchall()

        items = [
            {
                'id': r['id'],
                'item_code': r['item_code'],
                'item_name': r['item_name'],
                'category': r['category'],
                'spec_1': r['spec_1'],
                'spec_2': r['spec_2'],
                'unit': r['unit'],
                'description': r['description'],
                'is_active': r['is_active'],
                'created_at': r['created_at'].isoformat() if r['created_at'] else None,
                'updated_at': r['updated_at'].isoformat() if r['updated_at'] else None,
            }
            for r in rows
        ]
        return jsonify({
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
        }), 200

    except PsycopgError as e:
        logger.error(f"list_materials failed: error={e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': '자재 조회 실패'}), 500
    finally:
        if conn:
            put_conn(conn)


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/admin/materials — 신규 자재 등록 (ON CONFLICT DO UPDATE)
# ═════════════════════════════════════════════════════════════════════════════

@admin_materials_bp.route('', methods=['POST'])
@admin_materials_bp.route('/', methods=['POST'])
@jwt_required
@gst_or_admin_required
def create_material():
    """직접 입력 자재 추가 (item_code UNIQUE → ON CONFLICT DO UPDATE idempotent).

    Body:
        {
            "item_code": str (required),
            "item_name": str (required),
            "category": str (optional),
            "spec_1": str (optional),
            "spec_2": str (optional),
            "unit": str (optional),
            "description": str (optional)
        }

    Returns:
        201 — {"id": int, "item_code": str, "created": bool}
        400 — INVALID_REQUEST
    """
    payload = request.get_json() or {}
    item_code = (payload.get('item_code') or '').strip()
    item_name = (payload.get('item_name') or '').strip()

    if not item_code or not item_name:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'item_code 와 item_name 은 필수입니다',
        }), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO checklist.material_master
                    (item_code, item_name, category, spec_1, spec_2, unit, description, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (item_code) DO UPDATE SET
                    item_name   = EXCLUDED.item_name,
                    category    = EXCLUDED.category,
                    spec_1      = EXCLUDED.spec_1,
                    spec_2      = EXCLUDED.spec_2,
                    unit        = EXCLUDED.unit,
                    description = EXCLUDED.description,
                    is_active   = TRUE,
                    updated_at  = CURRENT_TIMESTAMP
                RETURNING id, (xmax = 0) AS created
                """,
                (
                    item_code,
                    item_name,
                    payload.get('category'),
                    payload.get('spec_1'),
                    payload.get('spec_2'),
                    payload.get('unit'),
                    payload.get('description'),
                ),
            )
            row = cur.fetchone()
            # RealDictCursor (db_pool default) — dict key access
            new_id = row['id']
            created = bool(row['created'])
            conn.commit()

        logger.info(
            f"Material upserted: id={new_id} code={item_code} created={created} "
            f"by worker_id={g.worker_id}"
        )
        return jsonify({
            'id': new_id,
            'item_code': item_code,
            'created': created,
        }), 201

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"create_material failed: code={item_code}, error={e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': '자재 등록 실패'}), 500
    finally:
        if conn:
            put_conn(conn)


# ═════════════════════════════════════════════════════════════════════════════
# PATCH /api/admin/materials/<id> — 자재 사양 수정
# ═════════════════════════════════════════════════════════════════════════════

@admin_materials_bp.route('/<int:material_id>', methods=['PATCH'])
@jwt_required
@gst_or_admin_required
def update_material(material_id: int):
    """자재 사양 수정 (item_code 영역은 변경 불가, 식별자 영역).

    Body (모든 필드 optional, 제공된 것만 갱신):
        {
            "item_name": str,
            "category": str,
            "spec_1": str,
            "spec_2": str,
            "unit": str,
            "description": str
        }

    Returns:
        200 — {"updated": True, "id": int}
        404 — NOT_FOUND
    """
    payload = request.get_json() or {}

    # 갱신 가능 필드 화이트리스트
    allowed = {'item_name', 'category', 'spec_1', 'spec_2', 'unit', 'description'}
    updates: Dict[str, Any] = {k: v for k, v in payload.items() if k in allowed}

    if not updates:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': '갱신할 필드가 없습니다 (item_name/category/spec_1/spec_2/unit/description)',
        }), 400

    set_clauses = ', '.join(f"{k} = %s" for k in updates.keys())
    params = list(updates.values()) + [material_id]

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE checklist.material_master
                   SET {set_clauses}, updated_at = CURRENT_TIMESTAMP
                 WHERE id = %s
                 RETURNING id
                """,
                params,
            )
            row = cur.fetchone()
            if not row:
                return jsonify({'error': 'NOT_FOUND', 'message': '자재 미존재'}), 404
            conn.commit()

        logger.info(
            f"Material updated: id={material_id} fields={list(updates.keys())} "
            f"by worker_id={g.worker_id}"
        )
        return jsonify({'updated': True, 'id': material_id}), 200

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"update_material failed: id={material_id}, error={e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': '자재 수정 실패'}), 500
    finally:
        if conn:
            put_conn(conn)


# ═════════════════════════════════════════════════════════════════════════════
# PATCH /api/admin/materials/<id>/deactivate — 자재 비활성화 (soft delete)
# ═════════════════════════════════════════════════════════════════════════════

@admin_materials_bp.route('/<int:material_id>/deactivate', methods=['PATCH'])
@jwt_required
@gst_or_admin_required
def deactivate_material(material_id: int):
    """자재 비활성화 (실 삭제 X — RESTRICT FK 안전).

    효과:
    - admin UI 검색 자동 제외 (is_active=TRUE 필터 default)
    - select_options 매핑된 항목은 BE override (Step 3 _enrich_select_options) 에서 자동 제외
      → 작업자 dropdown 에서 자동 비표시 (WARN log + skip)
    - 기존 checklist_record.selected_material_id FK 영역 영향 0 (RESTRICT 차단 안 함, 비활성만)

    Returns:
        200 — {"deactivated": True, "id": int}
        404 — NOT_FOUND
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE checklist.material_master
                   SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                 WHERE id = %s
                 RETURNING id
                """,
                (material_id,),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({'error': 'NOT_FOUND', 'message': '자재 미존재'}), 404
            conn.commit()

        logger.info(
            f"Material deactivated: id={material_id} by worker_id={g.worker_id}"
        )
        return jsonify({'deactivated': True, 'id': material_id}), 200

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"deactivate_material failed: id={material_id}, error={e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': '자재 비활성화 실패'}), 500
    finally:
        if conn:
            put_conn(conn)


# ═════════════════════════════════════════════════════════════════════════════
# PATCH /api/admin/materials/<id>/reactivate — 비활성 자재 재활성화
# ═════════════════════════════════════════════════════════════════════════════

@admin_materials_bp.route('/<int:material_id>/reactivate', methods=['PATCH'])
@jwt_required
@gst_or_admin_required
def reactivate_material(material_id: int):
    """비활성화된 자재를 다시 활성화 (admin 실수 복구 영역).

    Returns:
        200 — {"reactivated": True, "id": int}
        404 — NOT_FOUND
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE checklist.material_master
                   SET is_active = TRUE, updated_at = CURRENT_TIMESTAMP
                 WHERE id = %s
                 RETURNING id
                """,
                (material_id,),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({'error': 'NOT_FOUND', 'message': '자재 미존재'}), 404
            conn.commit()

        logger.info(
            f"Material reactivated: id={material_id} by worker_id={g.worker_id}"
        )
        return jsonify({'reactivated': True, 'id': material_id}), 200

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"reactivate_material failed: id={material_id}, error={e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': '자재 재활성화 실패'}), 500
    finally:
        if conn:
            put_conn(conn)


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/admin/materials/upload — Excel/CSV 일괄 업로드 (Sprint 66-BE-FOLLOWUP v3)
# ═════════════════════════════════════════════════════════════════════════════

@admin_materials_bp.route('/upload', methods=['POST'])
@jwt_required
@gst_or_admin_required
def upload_materials():
    """자재 마스터 + product_bom Excel/CSV 일괄 업로드 (Sprint 66-BE-FOLLOWUP v3).

    Content-Type: multipart/form-data
    Body:
      file: File (CSV / xlsx)  # .xls drop (v3)
      mode: 'preview' | 'commit'
      strategy: 'all' | 'selected' | 'skip' (mode=commit 시 필수)
      selected_item_codes: JSON string of string[] (strategy=selected 시 필수)

    Response 200 (mode=preview): UploadPreview
    Response 200 (mode=commit):  UploadResult
    Response 400: ENCODING_DETECTION_FAILED | INVALID_HEADER | PARSE_ERROR | INVALID_REQUEST
    """
    import json as _json
    from app.utils.material_parser import parse_upload_file
    from app.services.material_upload_service import diff_with_db, commit_upload

    # 1) 입력 검증
    if 'file' not in request.files:
        return jsonify({'error': 'INVALID_REQUEST', 'message': 'file 영역 필수입니다.'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'error': 'INVALID_REQUEST', 'message': 'file 영역 비어있습니다.'}), 400

    mode = (request.form.get('mode') or '').strip().lower()
    if mode not in ('preview', 'commit'):
        return jsonify({'error': 'INVALID_REQUEST',
                        'message': "mode 영역 'preview' 또는 'commit' 영역 영역 영역."}), 400

    # 2) Phase 1+2: 파싱 + 검증 (DB 변경 0)
    try:
        parsed_rows, rejected_rows = parse_upload_file(file)
    except ValueError as e:
        error_code = str(e)
        return jsonify({'error': error_code,
                        'message': f'파일 파싱 실패: {error_code}'}), 400

    try:
        diff = diff_with_db(parsed_rows)
    except Exception as e:
        logger.error(f'diff_with_db failed: {e}')
        return jsonify({'error': 'INTERNAL_ERROR',
                        'message': 'DB 대조 실패'}), 500

    diff['rejected_rows'] = rejected_rows

    # 3) Phase 3: mode 분기
    if mode == 'preview':
        return jsonify(diff), 200

    # commit mode — strategy 검증
    strategy = (request.form.get('strategy') or '').strip().lower()
    if strategy not in ('all', 'selected', 'skip'):
        return jsonify({'error': 'INVALID_REQUEST',
                        'message': "strategy 영역 'all'/'selected'/'skip' 영역 영역 영역."}), 400

    selected_item_codes: Optional[List[str]] = None
    if strategy == 'selected':
        raw_selected = request.form.get('selected_item_codes', '[]')
        try:
            selected_item_codes = _json.loads(raw_selected)
            if not isinstance(selected_item_codes, list):
                raise ValueError('not a list')
        except (ValueError, TypeError) as e:
            return jsonify({'error': 'INVALID_REQUEST',
                            'message': f'selected_item_codes JSON 파싱 실패: {e}'}), 400

    # Phase 3: commit 트랜잭션
    try:
        result = commit_upload(parsed_rows, strategy, selected_item_codes)
    except Exception as e:
        logger.error(f'commit_upload failed: {e}')
        return jsonify({'error': 'INTERNAL_ERROR',
                        'message': 'commit 실패 (트랜잭션 ROLLBACK)'}), 500

    result['rejected'] = len(rejected_rows)
    return jsonify(result), 200
