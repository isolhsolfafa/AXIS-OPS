"""
인증 라우트
엔드포인트: /api/auth/*
Sprint 1: register, verify-email, login, approve
Sprint 5: refresh 엔드포인트 구현
Sprint 12: PIN 설정/변경/로그인/상태 엔드포인트 추가
"""

import logging
import re
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from typing import Tuple, Dict, Any
from werkzeug.security import generate_password_hash, check_password_hash

from app.services.auth_service import AuthService
from app.middleware.jwt_auth import jwt_required, admin_required
from app.models.worker import update_approval_status, update_active_role, get_worker_by_id
from app.middleware.jwt_auth import get_current_worker_id
from app.models.worker import get_db_connection


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

    # Sprint 19-B: device_id를 auth_service.login에 전달 (DB 저장)
    device_id = data.get('device_id', 'unknown')

    response, status_code = auth_service.login(
        email=data['email'],
        password=data['password'],
        device_id=device_id,
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

    # Sprint 19-B: device_id를 auth_service에 전달 (DB 저장)
    device_id = data.get('device_id', 'unknown')

    response, status_code = auth_service.refresh_access_token(
        refresh_token=data['refresh_token'],
        device_id=device_id,
    )

    return jsonify(response), status_code


# ──────────────────────────────────────────────────────────────────
# Sprint 19-B: 로그아웃 (토큰 무효화)
# ──────────────────────────────────────────────────────────────────

@auth_bp.route("/logout", methods=["POST"])
@jwt_required
def logout() -> Tuple[Dict[str, Any], int]:
    """
    로그아웃 — 현재 refresh_token DB에서 무효화

    Headers:
        Authorization: Bearer {token}

    Request Body:
        {
            "refresh_token": str  # optional — 무효화할 refresh_token
        }

    Response:
        200: {"message": "로그아웃 완료"}
    """
    data = request.get_json() or {}
    refresh_token = data.get('refresh_token')

    if refresh_token:
        auth_service.revoke_refresh_token(refresh_token, reason='logout')
        logger.info(f"Logout with token revocation: worker_id={get_current_worker_id()}")
    else:
        # refresh_token 미전송 시 해당 worker 전체 토큰 무효화
        worker_id = get_current_worker_id()
        auth_service.revoke_all_worker_tokens(worker_id, reason='logout')
        logger.info(f"Logout all tokens: worker_id={worker_id}")

    return jsonify({'message': '로그아웃 완료'}), 200


# ──────────────────────────────────────────────────────────────────
# Sprint 12: PIN 인증 엔드포인트
# ──────────────────────────────────────────────────────────────────

_PIN_REGEX = re.compile(r'^\d{4}$')
_PIN_LOCK_DURATION_SECONDS = 300   # 5분
_PIN_MAX_FAIL_COUNT = 3


@auth_bp.route("/set-pin", methods=["POST"])
@jwt_required
def set_pin() -> Tuple[Dict[str, Any], int]:
    """
    PIN 최초 등록 (또는 덮어쓰기)

    Headers:
        Authorization: Bearer {token}

    Request Body:
        {
            "pin": str  # 4자리 숫자
        }

    Response:
        200: {"message": "PIN이 등록되었습니다."}
        400: {"error": "INVALID_PIN", "message": "..."}
    """
    data = request.get_json()

    if not data or 'pin' not in data:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'pin 필드가 필요합니다.'
        }), 400

    pin: str = str(data['pin'])

    # 4자리 숫자 유효성 검사
    if not _PIN_REGEX.match(pin):
        return jsonify({
            'error': 'INVALID_PIN',
            'message': 'PIN은 4자리 숫자여야 합니다.'
        }), 400

    worker_id = get_current_worker_id()
    pin_hash = generate_password_hash(pin)

    try:
        conn = get_db_connection()
        with conn:
            with conn.cursor() as cur:
                # UPSERT — 이미 존재하면 업데이트, 없으면 삽입
                cur.execute("""
                    INSERT INTO hr.worker_auth_settings
                        (worker_id, pin_hash, pin_fail_count, pin_locked_until, updated_at)
                    VALUES (%s, %s, 0, NULL, NOW())
                    ON CONFLICT (worker_id) DO UPDATE
                        SET pin_hash       = EXCLUDED.pin_hash,
                            pin_fail_count = 0,
                            pin_locked_until = NULL,
                            updated_at     = NOW()
                """, (worker_id, pin_hash))
        conn.close()
    except Exception as e:
        logger.error(f"set_pin DB error: worker_id={worker_id}, error={e}")
        return jsonify({
            'error': 'INTERNAL_ERROR',
            'message': 'PIN 등록 중 오류가 발생했습니다.'
        }), 500

    logger.info(f"PIN set: worker_id={worker_id}")
    return jsonify({'message': 'PIN이 등록되었습니다.'}), 200


@auth_bp.route("/change-pin", methods=["PUT"])
@jwt_required
def change_pin() -> Tuple[Dict[str, Any], int]:
    """
    PIN 변경 (현재 PIN 검증 후 새 PIN 설정)

    Headers:
        Authorization: Bearer {token}

    Request Body:
        {
            "current_pin": str,  # 현재 4자리 PIN
            "new_pin": str       # 새 4자리 PIN
        }

    Response:
        200: {"message": "PIN이 변경되었습니다."}
        400: {"error": "INVALID_PIN|INVALID_REQUEST", "message": "..."}
        401: {"error": "WRONG_PIN", "message": "..."}
        404: {"error": "PIN_NOT_SET", "message": "..."}
    """
    data = request.get_json()

    if not data or not all(k in data for k in ['current_pin', 'new_pin']):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'current_pin과 new_pin 필드가 필요합니다.'
        }), 400

    current_pin = str(data['current_pin'])
    new_pin = str(data['new_pin'])

    # 새 PIN 형식 검증
    if not _PIN_REGEX.match(new_pin):
        return jsonify({
            'error': 'INVALID_PIN',
            'message': 'new_pin은 4자리 숫자여야 합니다.'
        }), 400

    worker_id = get_current_worker_id()

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pin_hash FROM hr.worker_auth_settings WHERE worker_id = %s",
                (worker_id,)
            )
            row = cur.fetchone()

        if not row or not row['pin_hash']:
            conn.close()
            return jsonify({
                'error': 'PIN_NOT_SET',
                'message': 'PIN이 등록되어 있지 않습니다. 먼저 PIN을 등록하세요.'
            }), 404

        # 현재 PIN 검증
        if not check_password_hash(row['pin_hash'], current_pin):
            conn.close()
            return jsonify({
                'error': 'WRONG_PIN',
                'message': '현재 PIN이 올바르지 않습니다.'
            }), 401

        # 새 PIN으로 업데이트
        new_hash = generate_password_hash(new_pin)
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE hr.worker_auth_settings
                    SET pin_hash = %s, pin_fail_count = 0,
                        pin_locked_until = NULL, updated_at = NOW()
                    WHERE worker_id = %s
                """, (new_hash, worker_id))
        conn.close()
    except Exception as e:
        logger.error(f"change_pin DB error: worker_id={worker_id}, error={e}")
        return jsonify({
            'error': 'INTERNAL_ERROR',
            'message': 'PIN 변경 중 오류가 발생했습니다.'
        }), 500

    logger.info(f"PIN changed: worker_id={worker_id}")
    return jsonify({'message': 'PIN이 변경되었습니다.'}), 200


@auth_bp.route("/pin-login", methods=["POST"])
def pin_login() -> Tuple[Dict[str, Any], int]:
    """
    PIN으로 로그인 — JWT (access + refresh) 발급

    인증 토큰 없이 사용 가능 (JWT 불필요).
    3회 실패 시 5분간 PIN 잠금 (pin_locked_until).

    Request Body:
        {
            "worker_id": int,
            "pin": str  # 4자리 숫자
        }

    Response:
        200: {"access_token": str, "refresh_token": str, "worker": {...}}
        400: {"error": "INVALID_REQUEST|INVALID_PIN", "message": "..."}
        403: {"error": "PIN_LOCKED", "message": "..."}
        404: {"error": "PIN_NOT_SET|WORKER_NOT_FOUND", "message": "..."}
        401: {"error": "WRONG_PIN", "message": "..."}
    """
    data = request.get_json()

    if not data or not all(k in data for k in ['worker_id', 'pin']):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'worker_id와 pin 필드가 필요합니다.'
        }), 400

    try:
        worker_id = int(data['worker_id'])
    except (ValueError, TypeError):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'worker_id는 정수여야 합니다.'
        }), 400

    pin = str(data['pin'])

    # PIN 형식 검증
    if not _PIN_REGEX.match(pin):
        return jsonify({
            'error': 'INVALID_PIN',
            'message': 'PIN은 4자리 숫자여야 합니다.'
        }), 400

    try:
        conn = get_db_connection()

        # 1. 작업자 조회
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, email, role, company, is_admin, is_manager,"
                "       approval_status, email_verified"
                " FROM workers WHERE id = %s",
                (worker_id,)
            )
            worker_row = cur.fetchone()

        if not worker_row:
            conn.close()
            return jsonify({
                'error': 'WORKER_NOT_FOUND',
                'message': '작업자를 찾을 수 없습니다.'
            }), 404

        # 2. PIN 설정 조회
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pin_hash, pin_fail_count, pin_locked_until"
                " FROM hr.worker_auth_settings WHERE worker_id = %s",
                (worker_id,)
            )
            pin_row = cur.fetchone()

        if not pin_row or not pin_row['pin_hash']:
            conn.close()
            return jsonify({
                'error': 'PIN_NOT_SET',
                'message': 'PIN이 등록되어 있지 않습니다. ID/PW로 로그인 후 PIN을 등록하세요.'
            }), 404

        # 3. 잠금 여부 확인
        now_utc = datetime.now(timezone.utc)
        if pin_row['pin_locked_until'] and pin_row['pin_locked_until'] > now_utc:
            remaining = int((pin_row['pin_locked_until'] - now_utc).total_seconds())
            conn.close()
            return jsonify({
                'error': 'PIN_LOCKED',
                'message': f'PIN이 잠겼습니다. {remaining}초 후에 다시 시도하세요.'
            }), 403

        # 4. PIN 검증
        if not check_password_hash(pin_row['pin_hash'], pin):
            # 실패 횟수 증가
            new_fail = (pin_row['pin_fail_count'] or 0) + 1
            locked_until = None
            if new_fail >= _PIN_MAX_FAIL_COUNT:
                locked_until = now_utc + timedelta(seconds=_PIN_LOCK_DURATION_SECONDS)

            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE hr.worker_auth_settings
                        SET pin_fail_count = %s, pin_locked_until = %s, updated_at = NOW()
                        WHERE worker_id = %s
                    """, (new_fail, locked_until, worker_id))
            conn.close()

            if locked_until:
                return jsonify({
                    'error': 'PIN_LOCKED',
                    'message': f'PIN을 {_PIN_MAX_FAIL_COUNT}회 잘못 입력하여 5분간 잠겼습니다.'
                }), 403

            remaining_tries = _PIN_MAX_FAIL_COUNT - new_fail
            return jsonify({
                'error': 'WRONG_PIN',
                'message': f'PIN이 올바르지 않습니다. ({remaining_tries}회 남음)'
            }), 401

        # 5. 성공 — 실패 횟수 초기화
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE hr.worker_auth_settings
                    SET pin_fail_count = 0, pin_locked_until = NULL, updated_at = NOW()
                    WHERE worker_id = %s
                """, (worker_id,))
        conn.close()

    except Exception as e:
        logger.error(f"pin_login DB error: worker_id={worker_id}, error={e}")
        return jsonify({
            'error': 'INTERNAL_ERROR',
            'message': 'PIN 로그인 중 오류가 발생했습니다.'
        }), 500

    # 6. JWT 발급 (auth_service 재사용)
    access_token = auth_service.create_access_token(
        worker_id=worker_row['id'],
        email=worker_row['email'],
        role=worker_row['role']
    )
    refresh_token = auth_service.create_refresh_token(
        worker_id=worker_row['id'],
        email=worker_row['email']
    )

    # Sprint 19-B: refresh token DB 저장
    device_id = data.get('device_id', 'unknown')
    now = datetime.now(timezone.utc)
    auth_service._store_refresh_token(
        worker_id=worker_row['id'],
        device_id=device_id,
        token=refresh_token,
        expires_at=now + timedelta(days=30),
    )
    logger.info(f"PIN login success: worker_id={worker_id}, device_id={device_id}")
    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'worker': {
            'id': worker_row['id'],
            'name': worker_row['name'],
            'email': worker_row['email'],
            'role': worker_row['role'],
            'company': worker_row['company'],
            'approval_status': worker_row['approval_status'],
            'is_manager': worker_row['is_manager'],
            'is_admin': worker_row['is_admin'],
            'email_verified': worker_row['email_verified'],
        }
    }), 200


@auth_bp.route("/pin-status", methods=["GET"])
@jwt_required
def pin_status() -> Tuple[Dict[str, Any], int]:
    """
    현재 작업자의 PIN 등록 여부 및 생체인증 상태 조회

    Headers:
        Authorization: Bearer {token}

    Response:
        200: {"pin_registered": bool, "biometric_enabled": bool}
    """
    worker_id = get_current_worker_id()

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pin_hash, biometric_enabled"
                " FROM hr.worker_auth_settings WHERE worker_id = %s",
                (worker_id,)
            )
            row = cur.fetchone()
        conn.close()
    except Exception as e:
        logger.error(f"pin_status DB error: worker_id={worker_id}, error={e}")
        return jsonify({
            'error': 'INTERNAL_ERROR',
            'message': 'PIN 상태 조회 중 오류가 발생했습니다.'
        }), 500

    pin_registered = bool(row and row['pin_hash'])
    biometric_enabled = bool(row and row['biometric_enabled'])

    return jsonify({
        'pin_registered': pin_registered,
        'biometric_enabled': biometric_enabled,
    }), 200
