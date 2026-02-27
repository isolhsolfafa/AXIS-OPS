"""
인증 라우트
엔드포인트: /api/auth/*
Sprint 1: register, verify-email, login, approve
Sprint 5: refresh 엔드포인트 구현
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Tuple, Dict, Any

from app.services.auth_service import AuthService
from app.middleware.jwt_auth import jwt_required, admin_required
from app.models.worker import update_approval_status, update_active_role, get_worker_by_id
from app.middleware.jwt_auth import get_current_worker_id


logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
auth_service = AuthService()


@auth_bp.route("/register", methods=["POST"])
def register() -> Tuple[Dict[str, Any], int]:
    """
    사용자 회원가입

    Request Body:
        {
            "name": str,
            "email": str,
            "password": str,
            "role": str,     # MECH, ELEC, TM, PI, QI, SI
            "company": str   # optional: FNI, BAT, TMS(M), TMS(E), P&S, C&A, GST
        }

    Response:
        201: {"message": "...", "worker_id": int, "verification_code": str}
        400: {"error": "DUPLICATE_EMAIL|INVALID_ROLE|INVALID_COMPANY|COMPANY_ROLE_MISMATCH", "message": "..."}
    """
    data = request.get_json()

    # 필수 필드 확인
    if not data or not all(k in data for k in ['name', 'email', 'password', 'role']):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': '필수 필드가 누락되었습니다. (name, email, password, role)'
        }), 400

    # auth_service.register 호출 (company는 optional)
    response, status_code = auth_service.register(
        name=data['name'],
        email=data['email'],
        password=data['password'],
        role=data['role'],
        company=data.get('company')  # optional
    )
    return jsonify(response), status_code


@auth_bp.route("/verify-email", methods=["POST"])
def verify_email() -> Tuple[Dict[str, Any], int]:
    """
    이메일 인증

    Request Body:
        {
            "code": str  # 6자리 인증 코드
        }

    Response:
        200: {"message": "이메일 인증이 완료되었습니다. ..."}
        400: {"error": "INVALID_CODE", "message": "..."}
    """
    data = request.get_json()

    # 필수 필드 확인
    if not data or 'code' not in data:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': '인증 코드가 필요합니다.'
        }), 400

    # auth_service.verify_email 호출
    response, status_code = auth_service.verify_email(code=data['code'])
    return jsonify(response), status_code


@auth_bp.route("/login", methods=["POST"])
def login() -> Tuple[Dict[str, Any], int]:
    """
    로그인

    Request Body:
        {
            "email": str,
            "password": str
        }

    Response:
        200: {"access_token": str, "worker": {...}}
        401: {"error": "INVALID_CREDENTIALS", "message": "..."}
        403: {"error": "EMAIL_NOT_VERIFIED|APPROVAL_PENDING|APPROVAL_REJECTED", "message": "..."}
    """
    data = request.get_json()

    # 필수 필드 확인
    if not data or not all(k in data for k in ['email', 'password']):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': '이메일과 비밀번호가 필요합니다.'
        }), 400

    # auth_service.login 호출
    response, status_code = auth_service.login(
        email=data['email'],
        password=data['password']
    )
    return jsonify(response), status_code


@auth_bp.route("/approve", methods=["POST"])
@jwt_required
@admin_required
def approve() -> Tuple[Dict[str, Any], int]:
    """
    작업자 승인/거절 (관리자 전용)

    Request Body:
        {
            "worker_id": int,
            "approve": bool  # true: 승인, false: 거절
        }

    Response:
        200: {"message": "승인/거절 완료"}
        400: {"error": "INVALID_REQUEST", "message": "..."}
        403: {"error": "FORBIDDEN", "message": "관리자 권한이 필요합니다."}
    """
    data = request.get_json()

    # 필수 필드 확인
    if not data or not all(k in data for k in ['worker_id', 'approve']):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'worker_id와 approve 필드가 필요합니다.'
        }), 400

    worker_id = data['worker_id']
    approve = data['approve']

    # 승인 상태 업데이트
    status = 'approved' if approve else 'rejected'
    success = update_approval_status(worker_id, status)

    if not success:
        return jsonify({
            'error': 'UPDATE_FAILED',
            'message': '승인 상태 업데이트 실패'
        }), 400

    message = '작업자가 승인되었습니다.' if approve else '작업자가 거절되었습니다.'
    logger.info(f"Worker approval: worker_id={worker_id}, status={status}")

    return jsonify({'message': message}), 200


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password() -> Tuple[Dict[str, Any], int]:
    """
    비밀번호 재설정 코드 요청

    보안상 이메일 존재 여부와 무관하게 항상 200 반환.

    Request Body:
        {
            "email": str
        }

    Response:
        200: {"message": "입력하신 이메일로 재설정 코드를 발송했습니다."}
        400: {"error": "INVALID_REQUEST", "message": "..."}
    """
    data = request.get_json()

    if not data or 'email' not in data:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': '이메일이 필요합니다.'
        }), 400

    response, status_code = auth_service.send_password_reset_code(
        email=data['email']
    )
    return jsonify(response), status_code


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password() -> Tuple[Dict[str, Any], int]:
    """
    비밀번호 재설정

    Request Body:
        {
            "email": str,
            "code": str,       # 6자리 재설정 코드
            "new_password": str
        }

    Response:
        200: {"message": "비밀번호가 성공적으로 재설정되었습니다."}
        400: {"error": "INVALID_RESET_CODE|INVALID_REQUEST", "message": "..."}
        500: {"error": "RESET_FAILED", "message": "..."}
    """
    data = request.get_json()

    if not data or not all(k in data for k in ['email', 'code', 'new_password']):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': '필수 필드가 누락되었습니다. (email, code, new_password)'
        }), 400

    response, status_code = auth_service.reset_password(
        email=data['email'],
        code=data['code'],
        new_password=data['new_password']
    )
    return jsonify(response), status_code


@auth_bp.route("/me", methods=["GET"])
@jwt_required
def get_me() -> Tuple[Dict[str, Any], int]:
    """
    현재 로그인 작업자 정보 조회 (Sprint 11)

    Headers:
        Authorization: Bearer {token}

    Response:
        200: {"id": int, "name": str, "email": str, "role": str,
               "company": str|null, "is_admin": bool, "is_manager": bool,
               "active_role": str|null, ...}
        404: {"error": "WORKER_NOT_FOUND", "message": "..."}
    """
    worker_id = get_current_worker_id()
    worker = get_worker_by_id(worker_id)
    if not worker:
        return jsonify({
            'error': 'WORKER_NOT_FOUND',
            'message': '작업자 정보를 찾을 수 없습니다.'
        }), 404

    return jsonify({
        'id': worker.id,
        'name': worker.name,
        'email': worker.email,
        'role': worker.role,
        'company': worker.company,
        'is_admin': worker.is_admin,
        'is_manager': worker.is_manager,
        'approval_status': worker.approval_status,
        'email_verified': worker.email_verified,
        'active_role': worker.active_role,
        'created_at': worker.created_at.isoformat() if worker.created_at else None,
        'updated_at': worker.updated_at.isoformat() if worker.updated_at else None,
    }), 200


@auth_bp.route("/active-role", methods=["PUT"])
@jwt_required
def update_active_role_endpoint() -> Tuple[Dict[str, Any], int]:
    """
    GST 작업자 활성 역할 전환 (Sprint 11)

    GST 소속 작업자가 현장에서 역할을 전환할 때 사용 (PI/QI/SI).

    Headers:
        Authorization: Bearer {token}

    Request Body:
        {
            "active_role": str  # PI, QI, SI
        }

    Response:
        200: {"message": "활성 역할이 변경되었습니다.", "active_role": "PI"}
        400: {"error": "INVALID_ROLE|INVALID_REQUEST", "message": "..."}
        403: {"error": "FORBIDDEN", "message": "GST 소속 작업자만 역할 전환이 가능합니다."}
    """
    data = request.get_json()

    if not data or 'active_role' not in data:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'active_role 필드가 필요합니다.'
        }), 400

    new_active_role = data['active_role']

    # 유효한 역할 확인
    valid_roles = {'PI', 'QI', 'SI', 'ADMIN'}
    if new_active_role not in valid_roles:
        return jsonify({
            'error': 'INVALID_ROLE',
            'message': f'유효하지 않은 역할입니다. 허용: {", ".join(sorted(valid_roles))}'
        }), 400

    worker_id = get_current_worker_id()
    worker = get_worker_by_id(worker_id)

    if not worker:
        return jsonify({
            'error': 'WORKER_NOT_FOUND',
            'message': '작업자 정보를 찾을 수 없습니다.'
        }), 404

    # GST 소속 또는 관리자만 역할 전환 가능
    if worker.company != 'GST' and not worker.is_admin:
        return jsonify({
            'error': 'FORBIDDEN',
            'message': 'GST 소속 작업자만 역할 전환이 가능합니다.'
        }), 403

    success = update_active_role(worker_id, new_active_role)
    if not success:
        return jsonify({
            'error': 'UPDATE_FAILED',
            'message': '활성 역할 변경 실패'
        }), 500

    logger.info(f"Active role updated: worker_id={worker_id}, active_role={new_active_role}")

    return jsonify({
        'message': '활성 역할이 변경되었습니다.',
        'active_role': new_active_role
    }), 200


@auth_bp.route("/refresh", methods=["POST"])
def refresh() -> Tuple[Dict[str, Any], int]:
    """
    Refresh Token으로 새 Access Token 발급

    Request Body:
        {
            "refresh_token": str
        }

    Response:
        200: {"access_token": str}
        401: {"error": "INVALID_REFRESH_TOKEN", "message": "..."}
        403: {"error": "ACCOUNT_INACTIVE", "message": "..."}
    """
    data = request.get_json()

    if not data or 'refresh_token' not in data:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'refresh_token 필드가 필요합니다.'
        }), 400

    response, status_code = auth_service.refresh_access_token(
        refresh_token=data['refresh_token']
    )
    return jsonify(response), status_code
