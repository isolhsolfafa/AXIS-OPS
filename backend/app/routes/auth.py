"""
인증 라우트
엔드포인트: /api/auth/*
Sprint 1: register, verify-email, login, approve
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Tuple, Dict, Any

from app.services.auth_service import AuthService
from app.middleware.jwt_auth import jwt_required, admin_required
from app.models.worker import update_approval_status


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
            "role": str  # MM, EE, TM, PI, QI, SI
        }

    Response:
        201: {"message": "...", "worker_id": int, "verification_code": str}
        400: {"error": "DUPLICATE_EMAIL|INVALID_ROLE", "message": "..."}
    """
    data = request.get_json()

    # 필수 필드 확인
    if not data or not all(k in data for k in ['name', 'email', 'password', 'role']):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': '필수 필드가 누락되었습니다. (name, email, password, role)'
        }), 400

    # auth_service.register 호출
    response, status_code = auth_service.register(
        name=data['name'],
        email=data['email'],
        password=data['password'],
        role=data['role']
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


# Sprint 2에서 구현 예정
@auth_bp.route("/refresh-token", methods=["POST"])
def refresh_token() -> Tuple[Dict[str, Any], int]:
    """
    JWT 토큰 갱신 (Sprint 2)

    Request Body:
        - refresh_token: str

    Returns:
        {"access_token": str}
    """
    # TODO Sprint 2: refresh token 검증 및 새 access token 생성
    return jsonify({"message": "Sprint 2에서 구현 예정"}), 501
