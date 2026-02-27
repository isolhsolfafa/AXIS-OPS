"""
JWT 인증 미들웨어
Sprint 1: JWT 토큰 검증 및 관리자 권한 확인
"""

import logging
from typing import Callable, Any
from functools import wraps

from flask import request, jsonify, g
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from app.config import Config
from app.models.worker import get_worker_by_id


logger = logging.getLogger(__name__)


def jwt_required(f: Callable) -> Callable:
    """
    JWT 토큰 검증 데코레이터

    Authorization 헤더에서 Bearer 토큰을 추출하고 검증합니다.
    유효한 토큰의 경우 worker_id, email, role을 g 객체에 저장합니다.

    Args:
        f: 래핑할 함수

    Returns:
        래핑된 함수

    Usage:
        @app.route('/api/protected')
        @jwt_required
        def protected_route():
            worker_id = g.worker_id
            ...
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        """JWT 검증 로직"""
        # Authorization 헤더 추출
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({
                'error': 'MISSING_TOKEN',
                'message': '인증 토큰이 없습니다.'
            }), 401

        # Bearer 토큰 파싱
        parts = auth_header.split(' ')
        if len(parts) != 2 or parts[0] != 'Bearer':
            return jsonify({
                'error': 'INVALID_TOKEN',
                'message': '잘못된 토큰 형식입니다.'
            }), 401

        token = parts[1]

        # JWT 토큰 검증
        try:
            payload = jwt.decode(
                token,
                Config.JWT_SECRET_KEY,
                algorithms=['HS256']
            )

            # payload에서 worker 정보 추출 (sub는 str이므로 int 변환)
            g.worker_id = int(payload['sub'])
            g.worker_email = payload['email']
            g.worker_role = payload['role']

            logger.debug(f"JWT authenticated: worker_id={g.worker_id}, role={g.worker_role}")

        except ExpiredSignatureError:
            return jsonify({
                'error': 'EXPIRED_TOKEN',
                'message': '토큰이 만료되었습니다.'
            }), 401

        except InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return jsonify({
                'error': 'INVALID_TOKEN',
                'message': '유효하지 않은 토큰입니다.'
            }), 401

        return f(*args, **kwargs)

    return decorated_function


def decode_jwt(token: str) -> dict:
    """JWT 토큰 디코딩 (WebSocket 연결 시 사용)"""
    return jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])


def get_current_worker_id() -> int:
    """
    현재 인증된 작업자 ID 반환

    jwt_required 데코레이터가 먼저 실행되어야 합니다.

    Returns:
        현재 작업자 ID
    """
    return g.worker_id


def admin_required(f: Callable) -> Callable:
    """
    관리자 권한 검증 데코레이터

    jwt_required와 함께 사용되어야 합니다.
    g.worker_id를 기반으로 workers 테이블에서 is_admin을 확인합니다.

    Args:
        f: 래핑할 함수

    Returns:
        래핑된 함수

    Usage:
        @app.route('/api/admin/approve')
        @jwt_required
        @admin_required
        def admin_only_route():
            ...
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        """관리자 권한 검증 로직"""
        # jwt_required 선행 확인
        if not hasattr(g, 'worker_id'):
            return jsonify({
                'error': 'UNAUTHORIZED',
                'message': '인증이 필요합니다.'
            }), 401

        # 작업자 조회
        worker = get_worker_by_id(g.worker_id)

        if not worker or not worker.is_admin:
            logger.warning(f"Forbidden: worker_id={g.worker_id} attempted admin access")
            return jsonify({
                'error': 'FORBIDDEN',
                'message': '관리자 권한이 필요합니다.'
            }), 403

        logger.debug(f"Admin access granted: worker_id={g.worker_id}")
        return f(*args, **kwargs)

    return decorated_function


def manager_or_admin_required(f: Callable) -> Callable:
    """
    관리자(is_admin) 또는 매니저(is_manager) 권한 검증 데코레이터.
    Sprint 6 Phase C: 강제 종료 API 권한 (관리자 또는 매니저)

    jwt_required와 함께 사용되어야 합니다.

    Usage:
        @app.route('/api/admin/tasks/<int:task_id>/force-close', methods=['PUT'])
        @jwt_required
        @manager_or_admin_required
        def force_close_task(task_id: int):
            ...
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        """관리자 또는 매니저 권한 검증 로직"""
        if not hasattr(g, 'worker_id'):
            return jsonify({
                'error': 'UNAUTHORIZED',
                'message': '인증이 필요합니다.'
            }), 401

        worker = get_worker_by_id(g.worker_id)

        if not worker or (not worker.is_admin and not worker.is_manager):
            logger.warning(
                f"Forbidden: worker_id={g.worker_id} attempted manager/admin access"
            )
            return jsonify({
                'error': 'FORBIDDEN',
                'message': '관리자 또는 매니저 권한이 필요합니다.'
            }), 403

        logger.debug(f"Manager/admin access granted: worker_id={g.worker_id}")
        return f(*args, **kwargs)

    return decorated_function
