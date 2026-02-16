"""
인증 서비스
Sprint 1: 회원가입, 로그인, 이메일 인증
"""

import logging
from typing import Dict, Any, Tuple
from datetime import datetime, timedelta

import bcrypt
import jwt

from app.config import Config
from app.models.worker import (
    create_worker,
    get_worker_by_email,
    update_email_verified,
    create_verification_code,
    get_verification_code,
    mark_code_as_verified,
)


logger = logging.getLogger(__name__)

# 유효한 역할 목록
VALID_ROLES = {'MM', 'EE', 'TM', 'PI', 'QI', 'SI'}


class AuthService:
    """인증 관련 비즈니스 로직"""

    def hash_password(self, password: str) -> str:
        """
        비밀번호 해싱

        Args:
            password: 평문 비밀번호

        Returns:
            해시된 비밀번호 (문자열)
        """
        salt = bcrypt.gensalt()
        password_bytes = password.encode('utf-8')
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')

    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        비밀번호 검증

        Args:
            password: 평문 비밀번호
            password_hash: 해시된 비밀번호

        Returns:
            일치 여부
        """
        try:
            password_bytes = password.encode('utf-8')
            hash_bytes = password_hash.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hash_bytes)
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False

    def create_access_token(self, worker_id: int, email: str, role: str) -> str:
        """
        JWT 액세스 토큰 생성

        Args:
            worker_id: 작업자 ID
            email: 이메일
            role: 역할

        Returns:
            JWT 토큰
        """
        now = datetime.utcnow()
        payload = {
            'sub': str(worker_id),
            'email': email,
            'role': role,
            'iat': now,
            'exp': now + Config.JWT_ACCESS_TOKEN_EXPIRES
        }
        token = jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm='HS256')
        return token

    def register(
        self,
        name: str,
        email: str,
        password: str,
        role: str
    ) -> Tuple[Dict[str, Any], int]:
        """
        사용자 회원가입

        Args:
            name: 사용자 이름
            email: 이메일
            password: 비밀번호 (평문)
            role: 역할 (MM, EE, TM, PI, QI, SI)

        Returns:
            (response dict, status code)
        """
        # 역할 검증
        if role not in VALID_ROLES:
            return {
                'error': 'INVALID_ROLE',
                'message': '유효하지 않은 역할입니다.'
            }, 400

        # 비밀번호 해싱
        password_hash = self.hash_password(password)

        # 작업자 생성
        worker_id = create_worker(
            name=name,
            email=email,
            password_hash=password_hash,
            role=role
        )

        # 중복 이메일 체크
        if worker_id is None:
            return {
                'error': 'DUPLICATE_EMAIL',
                'message': '이미 사용 중인 이메일입니다.'
            }, 400

        # 이메일 인증 코드 생성
        verification_code = create_verification_code(worker_id)

        if verification_code is None:
            logger.error(f"Failed to create verification code for worker_id={worker_id}")
            return {
                'error': 'REGISTRATION_FAILED',
                'message': '회원가입 실패'
            }, 400

        # TODO Sprint 2: 실제 이메일 발송 (현재는 로그만)
        logger.info(f"[EMAIL] Send verification code to {email}: {verification_code}")

        return {
            'message': '회원가입 성공. 이메일로 발송된 인증 코드를 입력하세요.',
            'worker_id': worker_id,
            'verification_code': verification_code  # Sprint 1 디버깅용
        }, 201

    def login(self, email: str, password: str) -> Tuple[Dict[str, Any], int]:
        """
        로그인

        Args:
            email: 이메일
            password: 비밀번호 (평문)

        Returns:
            (response dict with access_token, status code)
        """
        # 사용자 조회
        worker = get_worker_by_email(email)

        if worker is None:
            return {
                'error': 'INVALID_CREDENTIALS',
                'message': '이메일 또는 비밀번호가 잘못되었습니다.'
            }, 401

        # 비밀번호 검증
        if not self.verify_password(password, worker.password_hash):
            return {
                'error': 'INVALID_CREDENTIALS',
                'message': '이메일 또는 비밀번호가 잘못되었습니다.'
            }, 401

        # 이메일 인증 확인
        if not worker.email_verified:
            return {
                'error': 'EMAIL_NOT_VERIFIED',
                'message': '이메일 인증을 먼저 완료하세요.'
            }, 403

        # 승인 상태 확인 (정책 A: 미승인 로그인 차단)
        if worker.approval_status == 'pending':
            return {
                'error': 'APPROVAL_PENDING',
                'message': '관리자 승인 대기 중입니다.'
            }, 403

        if worker.approval_status == 'rejected':
            return {
                'error': 'APPROVAL_REJECTED',
                'message': '가입 승인이 거부되었습니다.'
            }, 403

        # JWT 토큰 생성
        access_token = self.create_access_token(
            worker_id=worker.id,
            email=worker.email,
            role=worker.role
        )

        return {
            'access_token': access_token,
            'worker': {
                'id': worker.id,
                'name': worker.name,
                'email': worker.email,
                'role': worker.role,
                'approval_status': worker.approval_status,
                'is_manager': worker.is_manager,
                'is_admin': worker.is_admin
            }
        }, 200

    def verify_email(self, code: str) -> Tuple[Dict[str, Any], int]:
        """
        이메일 인증

        Args:
            code: 6자리 인증 코드

        Returns:
            (response dict, status code)
        """
        # 인증 코드 조회 및 만료 확인
        verification = get_verification_code(code)

        if verification is None:
            return {
                'error': 'INVALID_CODE',
                'message': '유효하지 않거나 만료된 인증 코드입니다.'
            }, 400

        worker_id = verification['worker_id']

        # 인증 코드 사용 완료 처리
        if not mark_code_as_verified(code):
            return {
                'error': 'VERIFICATION_FAILED',
                'message': '인증 처리 실패'
            }, 400

        # 작업자 이메일 인증 완료 처리
        if not update_email_verified(worker_id):
            return {
                'error': 'VERIFICATION_FAILED',
                'message': '인증 처리 실패'
            }, 400

        logger.info(f"Email verified successfully: worker_id={worker_id}")

        return {
            'message': '이메일 인증이 완료되었습니다. 관리자 승인 후 로그인 가능합니다.'
        }, 200
