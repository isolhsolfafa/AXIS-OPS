"""
JWT 인증 미들웨어
Sprint 1: JWT 토큰 검증 및 관리자 권한 확인
Sprint 32: 요청 시작 시각 기록 (access log용)
"""

import time
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
        g.request_start_time = time.time()  # Sprint 32: access log 측정용

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


def jwt_optional(f: Callable) -> Callable:
    """
    JWT 토큰 선택적 검증 데코레이터 (BUG-22 Logout Storm 방지)

    토큰이 있으면 g.worker_id 설정, 없거나 무효하면 g.worker_id = None으로 진행.
    logout처럼 토큰 없이도 호출 가능해야 하는 엔드포인트에 사용.
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            g.worker_id = None
            g.worker_email = None
            g.worker_role = None
            return f(*args, **kwargs)

        parts = auth_header.split(' ')
        if len(parts) != 2 or parts[0] != 'Bearer':
            g.worker_id = None
            g.worker_email = None
            g.worker_role = None
            return f(*args, **kwargs)

        token = parts[1]
        try:
            payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
            g.worker_id = int(payload['sub'])
            g.worker_email = payload['email']
            g.worker_role = payload['role']
        except (ExpiredSignatureError, InvalidTokenError):
            g.worker_id = None
            g.worker_email = None
            g.worker_role = None

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


def get_current_worker():
    """
    현재 인증된 작업자 객체를 반환 (request 당 1회 DB 조회, 이후 캐시).

    jwt_required 데코레이터 실행 후 호출 가능.
    g.current_worker에 캐시하여 동일 request 내 중복 DB 쿼리 방지.

    Returns:
        Worker 객체 또는 None (미인증 시)
    """
    if hasattr(g, 'current_worker') and g.current_worker is not None:
        return g.current_worker

    if not hasattr(g, 'worker_id'):
        return None

    worker = get_worker_by_id(g.worker_id)
    g.current_worker = worker
    return worker


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

        # 작업자 조회 (캐싱)
        worker = get_current_worker()

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

        worker = get_current_worker()

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


def gst_or_admin_required(f: Callable) -> Callable:
    """
    GST 소속 전직원 또는 Admin만 허용.

    용도: 공장 대시보드 KPI, 불량 분석, CT 분석 등 GST 전용 페이지 API.
    AXIS-VIEW 접근 가능 사용자 중 협력사 manager를 차단.

    조건: worker.company == 'GST' OR worker.is_admin == True

    jwt_required와 함께 사용되어야 합니다.

    Usage:
        @app.route('/api/admin/factory/weekly-kpi')
        @jwt_required
        @gst_or_admin_required
        def factory_kpi():
            ...
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if not hasattr(g, 'worker_id'):
            return jsonify({
                'error': 'UNAUTHORIZED',
                'message': '인증이 필요합니다.'
            }), 401

        worker = get_current_worker()

        if not worker or (worker.company != 'GST' and not worker.is_admin):
            logger.warning(
                f"Forbidden: worker_id={g.worker_id} attempted GST-only access"
            )
            return jsonify({
                'error': 'FORBIDDEN',
                'message': 'GST 소속 또는 관리자 권한이 필요합니다.'
            }), 403

        logger.debug(f"GST/admin access granted: worker_id={g.worker_id}")
        return f(*args, **kwargs)

    return decorated_function


def view_access_required(f: Callable) -> Callable:
    """
    AXIS-VIEW 접근 가능 사용자만 허용.

    조건: worker.company == 'GST' OR worker.is_admin OR worker.is_manager
    (= AXIS-VIEW 로그인 게이트와 동일 조건)

    용도: QR 관리, 생산관리, ETL 변경이력 등 VIEW 사용자 전체 공개 API.

    jwt_required와 함께 사용되어야 합니다.

    Usage:
        @app.route('/api/admin/qr/list')
        @jwt_required
        @view_access_required
        def qr_list():
            ...
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if not hasattr(g, 'worker_id'):
            return jsonify({
                'error': 'UNAUTHORIZED',
                'message': '인증이 필요합니다.'
            }), 401

        worker = get_current_worker()

        if not worker or (
            worker.company != 'GST'
            and not worker.is_admin
            and not worker.is_manager
        ):
            logger.warning(
                f"Forbidden: worker_id={g.worker_id} attempted VIEW access"
            )
            return jsonify({
                'error': 'FORBIDDEN',
                'message': 'AXIS-VIEW 접근 권한이 필요합니다.'
            }), 403

        logger.debug(f"VIEW access granted: worker_id={g.worker_id}")
        return f(*args, **kwargs)

    return decorated_function
