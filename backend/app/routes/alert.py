"""
알림 라우트
엔드포인트: /api/app/alerts/*
Sprint 3: 알림 목록 조회 + 읽음 처리
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Tuple, Dict, Any

from app.middleware.jwt_auth import jwt_required, get_current_worker_id
from app.services.alert_service import (
    get_worker_alerts,
    mark_as_read,
    mark_all_read
)


logger = logging.getLogger(__name__)

alert_bp = Blueprint("alert", __name__, url_prefix="/api/app/alerts")


@alert_bp.route("", methods=["GET"])
@jwt_required
def get_alerts() -> Tuple[Dict[str, Any], int]:
    """
    내 알림 목록 조회 (JWT에서 worker_id 추출)

    Query Parameters:
        - unread_only: bool (default: false) - true면 읽지 않은 알림만 조회
        - page: int (default: 1) - 페이지 번호 (1부터 시작)
        - limit: int (default: 50) - 페이지당 알림 수

    Headers:
        - Authorization: Bearer {token}

    Response:
        200: {
            "alerts": [
                {
                    "id": int,
                    "alert_type": str,
                    "serial_number": str,
                    "qr_doc_id": str,
                    "message": str,
                    "is_read": bool,
                    "created_at": str (ISO 8601)
                }
            ],
            "total": int,
            "unread_count": int,
            "page": int,
            "limit": int
        }
    """
    try:
        # JWT에서 worker_id 추출
        worker_id = get_current_worker_id()

        # Query parameters
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))

        # 알림 목록 조회
        result = get_worker_alerts(
            worker_id=worker_id,
            unread_only=unread_only,
            page=page,
            limit=limit
        )

        return jsonify(result), 200

    except ValueError as e:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': f'잘못된 파라미터: {str(e)}'
        }), 400
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        return jsonify({
            'error': 'INTERNAL_ERROR',
            'message': '알림 목록 조회 실패'
        }), 500


@alert_bp.route("/<int:alert_id>/read", methods=["PUT"])
@jwt_required
def mark_alert_read(alert_id: int) -> Tuple[Dict[str, Any], int]:
    """
    개별 알림 읽음 처리

    Path Parameters:
        - alert_id: int

    Headers:
        - Authorization: Bearer {token}

    Response:
        200: {"message": "읽음 처리 완료"}
        403: {"error": "FORBIDDEN", "message": "..."}
        404: {"error": "NOT_FOUND", "message": "..."}
    """
    try:
        # JWT에서 worker_id 추출
        worker_id = get_current_worker_id()

        # 읽음 처리 (소유권 확인 포함)
        success = mark_as_read(alert_id, worker_id)

        if not success:
            return jsonify({
                'error': 'NOT_FOUND_OR_FORBIDDEN',
                'message': '알림을 찾을 수 없거나 권한이 없습니다.'
            }), 404

        return jsonify({'message': '읽음 처리 완료'}), 200

    except Exception as e:
        logger.error(f"Failed to mark alert as read: {e}")
        return jsonify({
            'error': 'INTERNAL_ERROR',
            'message': '읽음 처리 실패'
        }), 500


@alert_bp.route("/read-all", methods=["PUT"])
@jwt_required
def mark_all_alerts_read() -> Tuple[Dict[str, Any], int]:
    """
    내 모든 알림 읽음 처리

    Headers:
        - Authorization: Bearer {token}

    Response:
        200: {"message": "N건 읽음 처리", "count": int}
    """
    try:
        # JWT에서 worker_id 추출
        worker_id = get_current_worker_id()

        # 모든 알림 읽음 처리
        count = mark_all_read(worker_id)

        return jsonify({
            'message': f'{count}건 읽음 처리',
            'count': count
        }), 200

    except Exception as e:
        logger.error(f"Failed to mark all alerts as read: {e}")
        return jsonify({
            'error': 'INTERNAL_ERROR',
            'message': '읽음 처리 실패'
        }), 500


@alert_bp.route("/unread-count", methods=["GET"])
@jwt_required
def get_unread_count() -> Tuple[Dict[str, Any], int]:
    """
    안 읽은 알림 개수 조회

    Headers:
        - Authorization: Bearer {token}

    Response:
        200: {"unread_count": int}
    """
    try:
        # JWT에서 worker_id 추출
        worker_id = get_current_worker_id()

        # 읽지 않은 알림 개수 조회
        from app.models.alert_log import get_unread_count as get_unread_count_model
        unread_count = get_unread_count_model(worker_id)

        return jsonify({'unread_count': unread_count}), 200

    except Exception as e:
        logger.error(f"Failed to get unread count: {e}")
        return jsonify({
            'error': 'INTERNAL_ERROR',
            'message': '읽지 않은 알림 개수 조회 실패'
        }), 500
