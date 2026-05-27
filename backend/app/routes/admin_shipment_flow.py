"""
출하 흐름 + 미종료 분류 admin route (Sprint 79, v2.19.0)

endpoint 2개:
- GET /api/admin/shipment/by-status?status=confirmed|planned
- GET /api/admin/tasks/pending/grouped

설계서: AGENT_TEAM_LAUNCH.md § Sprint 79
Codex 라운드 1 (M=7/A=2/N=4) 모두 반영.

권한 catch (Codex Q7 M):
- shipment/by-status = @gst_or_admin_required (SI RBAC 정합)
- tasks/pending/grouped = @admin_required (admin only, 메인 메뉴)
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Tuple, Dict, Any

from app.middleware.jwt_auth import jwt_required, admin_required, gst_or_admin_required
from app.services.shipment_flow_service import (
    get_shipment_by_status,
    get_pending_tasks_grouped,
)
from psycopg2 import Error as PsycopgError

logger = logging.getLogger(__name__)

# admin Blueprint url_prefix='/api/admin' 정합 (admin.py 영역 동일)
admin_shipment_flow_bp = Blueprint("admin_shipment_flow", __name__, url_prefix="/api/admin")


@admin_shipment_flow_bp.route("/shipment/by-status", methods=["GET"])
@jwt_required
@gst_or_admin_required
def get_shipment_by_status_route() -> Tuple[Dict[str, Any], int]:
    """
    출하 확정/예정 list catch (SI 화면 영역 사용).

    Codex Q7 M: @gst_or_admin_required (SI RBAC 정합 — GST 자사 + admin).

    Query Parameters:
        status: 'confirmed' (today) | 'planned' (future)
        q: search query (option, S/N or sales_order)
        page: 페이지 번호 (기본 1)
        per_page: 페이지당 건수 (기본 50, max 200)

    Returns:
        200: {"items": [...], "total": int, "page": int, "per_page": int}
        400: {"error": "INVALID_STATUS", "message": str}
        500: {"error": "INTERNAL_ERROR", "message": str}
    """
    status = request.args.get('status', 'confirmed')
    q = request.args.get('q')
    page = max(1, request.args.get('page', 1, type=int))
    per_page = min(200, max(1, request.args.get('per_page', 50, type=int)))

    if status not in ('confirmed', 'planned'):
        return jsonify({
            'error': 'INVALID_STATUS',
            'message': "status는 'confirmed' 또는 'planned' 이어야 합니다."
        }), 400

    try:
        items, total = get_shipment_by_status(status=status, q=q, page=page, per_page=per_page)
        return jsonify({
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
        }), 200
    except PsycopgError as e:
        logger.error(f"shipment/by-status DB error: {e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': 'DB 조회 실패'}), 500
    except Exception as e:
        logger.error(f"shipment/by-status error: {e}", exc_info=True)
        return jsonify({'error': 'INTERNAL_ERROR', 'message': str(e)}), 500


@admin_shipment_flow_bp.route("/tasks/pending/grouped", methods=["GET"])
@jwt_required
@admin_required
def get_pending_tasks_grouped_route() -> Tuple[Dict[str, Any], int]:
    """
    미종료 작업 분류 catch (admin only, 메인 메뉴 영역 사용).

    Codex Q6 N: UNION ALL + GROUP BY single query (N+1 회피).

    Returns:
        200: {
            "total": int,
            "partners": [{"name": "FNI", "category": "MECH", "count": int}, ...],
            "gst_processes": [{"category": "PI", "label": "가압검사", "count": int}, ...]
        }
        500: {"error": "INTERNAL_ERROR", "message": str}
    """
    try:
        data = get_pending_tasks_grouped()
        return jsonify(data), 200
    except PsycopgError as e:
        logger.error(f"tasks/pending/grouped DB error: {e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': 'DB 조회 실패'}), 500
    except Exception as e:
        logger.error(f"tasks/pending/grouped error: {e}", exc_info=True)
        return jsonify({'error': 'INTERNAL_ERROR', 'message': str(e)}), 500
