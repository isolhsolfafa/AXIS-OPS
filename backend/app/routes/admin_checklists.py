"""
Admin 체크리스트 매핑 라우트 — Sprint 66-BE Step 4 (v2.12.3)
엔드포인트: /api/admin/checklists/master/<id>/options

권한: @jwt_required + @gst_or_admin_required (Sprint 27 v1.7.4 표준)

기능:
- GET /api/admin/checklists/master/<master_id>/options — 현재 매핑 + material spec 정보 조회 (admin UI 표시용)
- PATCH /api/admin/checklists/master/<master_id>/options — material_id 배열 매핑 갱신 (admin/GST 권한)
"""
import json
import logging
from typing import Any, Dict, List

from flask import Blueprint, request, jsonify, g
from psycopg2 import Error as PsycopgError
from psycopg2.extras import RealDictCursor

from app.middleware.jwt_auth import jwt_required, gst_or_admin_required
from app.models.worker import get_db_connection
from app.db_pool import put_conn


logger = logging.getLogger(__name__)

admin_checklists_bp = Blueprint(
    'admin_checklists',
    __name__,
    url_prefix='/api/admin/checklists',
)


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/admin/checklists/master/<master_id>/options
# ═════════════════════════════════════════════════════════════════════════════

@admin_checklists_bp.route('/master/<int:master_id>/options', methods=['GET'])
@jwt_required
@gst_or_admin_required
def get_select_options(master_id: int):
    """현재 매핑 + material spec 정보 조회 (admin UI 매핑 화면 표시용).

    dual-format 처리 (Codex D4-01):
    - 신규 양식 (material_id int 배열) → material_master JOIN + 순서 보존 (array_position)
    - 옛 양식 (legacy string 배열) → 그대로 표시 + legacy_string flag

    Returns:
        200 — {
            "master_id": int,
            "item_name": str,
            "category": str,
            "item_type": str,
            "select_options_raw": [...],         # JSON 그대로
            "materials": [{...}, ...]            # 신규 양식 시 material spec dict 배열, legacy 시 {legacy_string: str}
        }
        404 — NOT_FOUND
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. master 조회
            cur.execute(
                """
                SELECT id, item_name, category, item_type, select_options
                  FROM checklist.checklist_master
                 WHERE id = %s
                """,
                (master_id,),
            )
            master = cur.fetchone()
            if not master:
                return jsonify({'error': 'NOT_FOUND', 'message': '체크리스트 항목 미존재'}), 404

            select_options_raw = master['select_options'] or []
            materials: List[Dict[str, Any]] = []

            # 2. dual-format 분기 (Python 측, Codex D4-01)
            if select_options_raw and all(
                isinstance(x, int) and not isinstance(x, bool) for x in select_options_raw
            ):
                # 신규 양식 (material_id int 배열)
                cur.execute(
                    """
                    SELECT id, item_code, item_name, category, spec_1, spec_2, unit,
                           description, is_active
                      FROM checklist.material_master
                     WHERE id = ANY(%s)
                     ORDER BY array_position(%s::int[], id)
                    """,
                    (select_options_raw, select_options_raw),
                )
                materials = [
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
                    }
                    for r in cur.fetchall()
                ]
            elif select_options_raw and all(isinstance(x, str) for x in select_options_raw):
                # 옛 placeholder string 배열 — 그대로 표시 (legacy 호환)
                materials = [{'legacy_string': s} for s in select_options_raw]

        return jsonify({
            'master_id': master['id'],
            'item_name': master['item_name'],
            'category': master['category'],
            'item_type': master['item_type'],
            'select_options_raw': select_options_raw,
            'materials': materials,
        }), 200

    except PsycopgError as e:
        logger.error(f"get_select_options failed: master_id={master_id}, error={e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': '매핑 조회 실패'}), 500
    finally:
        if conn:
            put_conn(conn)


# ═════════════════════════════════════════════════════════════════════════════
# PATCH /api/admin/checklists/master/<master_id>/options
# ═════════════════════════════════════════════════════════════════════════════

@admin_checklists_bp.route('/master/<int:master_id>/options', methods=['PATCH'])
@jwt_required
@gst_or_admin_required
def update_select_options(master_id: int):
    """checklist_master.select_options 매핑 갱신 (material_id 배열).

    5-07 사용자 결정: 옵션 Y full spec, admin/GST 매핑 권한.
    item_type='SELECT' 만 허용.

    Body:
        {"material_ids": [12, 14, 18, 22, 24, 30]}

    Validation:
        - material_ids 가 list 인지
        - 모든 element 가 int 인지
        - material_master 에 모두 존재 + is_active=TRUE 인지
        - master_id 의 item_type='SELECT' 인지

    Returns:
        200 — {"master_id": int, "material_ids": [int, ...], "updated": True}
        400 — INVALID_REQUEST / INVALID_MATERIAL_IDS / NOT_SELECT_TYPE
        404 — NOT_FOUND (master)
    """
    payload = request.get_json() or {}
    material_ids = payload.get('material_ids')

    # 1. 형식 검증
    if not isinstance(material_ids, list):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'material_ids 는 list 여야 합니다',
        }), 400

    if not all(isinstance(x, int) and not isinstance(x, bool) for x in material_ids):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'material_ids 의 모든 element 는 정수여야 합니다',
        }), 400

    # 중복 차단 (admin UI 측에서도 차단되어야 하지만 안전망)
    if len(material_ids) != len(set(material_ids)):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'material_ids 에 중복 영역 존재',
        }), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 2. master 존재 + item_type='SELECT' 검증
            cur.execute(
                "SELECT item_type FROM checklist.checklist_master WHERE id = %s",
                (master_id,),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({'error': 'NOT_FOUND', 'message': '체크리스트 항목 미존재'}), 404
            # RealDictCursor (db_pool default) — dict key access
            item_type = row['item_type']
            if item_type != 'SELECT':
                return jsonify({
                    'error': 'NOT_SELECT_TYPE',
                    'message': f"item_type='SELECT' 만 매핑 가능 (현재: {item_type})",
                }), 400

            # 3. material_master 존재 + is_active=TRUE 검증
            if material_ids:
                cur.execute(
                    """
                    SELECT id FROM checklist.material_master
                     WHERE id = ANY(%s) AND is_active = TRUE
                    """,
                    (material_ids,),
                )
                valid_ids = {r['id'] for r in cur.fetchall()}
                missing = [mid for mid in material_ids if mid not in valid_ids]
                if missing:
                    return jsonify({
                        'error': 'INVALID_MATERIAL_IDS',
                        'message': f'미존재 또는 비활성 material_id: {missing}',
                        'missing_ids': missing,
                    }), 400

            # 4. UPDATE select_options
            cur.execute(
                """
                UPDATE checklist.checklist_master
                   SET select_options = %s::jsonb,
                       updated_at = CURRENT_TIMESTAMP
                 WHERE id = %s
                """,
                (json.dumps(material_ids), master_id),
            )
            conn.commit()

        logger.info(
            f"checklist_master select_options updated: master_id={master_id} "
            f"material_ids={material_ids} by worker_id={g.worker_id}"
        )
        return jsonify({
            'master_id': master_id,
            'material_ids': material_ids,
            'updated': True,
        }), 200

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"update_select_options failed: master_id={master_id}, error={e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': '매핑 갱신 실패'}), 500
    finally:
        if conn:
            put_conn(conn)
