"""
인증 서비스
Sprint 1: 회원가입, 로그인, 이메일 인증
Sprint 5: SMTP 실제 발송, Refresh Token, Admin freepass 정책
"""

import logging
import smtplib
import time
import uuid
from collections import defaultdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timezone

import bcrypt
import jwt

from app.config import Config
from app.models.worker import (
    create_worker,
    get_worker_by_email,
    get_admin_by_email_prefix,
    update_email_verified,
    create_verification_code,
    create_password_reset_code,
    get_verification_code,
    mark_code_as_verified,
    update_password_hash,
)


logger = logging.getLogger(__name__)

# 유효한 역할 목록 (ADMIN은 DB Seed 전용 — 일반 회원가입 불가)
# Sprint 6: MM→MECH, EE→ELEC 네이밍 변경
VALID_ROLES = {'MECH', 'ELEC', 'TM', 'PI', 'QI', 'SI'}

# 회사 ↔ 역할 매핑 (회원가입 시 company↔role 검증용)
COMPANY_ROLE_MAP: Dict[str, set] = {
    'FNI':    {'MECH'},
    'BAT':    {'MECH'},
    'TMS(M)': {'MECH'},
    'TMS(E)': {'ELEC'},
    'P&S':    {'ELEC'},
    'C&A':    {'ELEC'},
    'GST':    {'PI', 'QI', 'SI', 'ADMIN'},
}

# 이메일 발송 Rate Limiter (DoS 방지)
_email_rate_log: dict = defaultdict(list)
_MAX_EMAILS_PER_HOUR = 5


def _check_email_rate_limit(email: str) -> bool:
    """1시간 내 이메일 발송 횟수 제한 (DoS 방지)

    Args:
        email: 수신자 이메일

    Returns:
        발송 가능하면 True, 한도 초과 시 False
    """
    now = time.time()
    _email_rate_log[email] = [t for t in _email_rate_log[email] if now - t < 3600]
    if len(_email_rate_log[email]) >= _MAX_EMAILS_PER_HOUR:
        return False
    _email_rate_log[email].append(now)
    return True


class AuthService:
    """인증 관련 비즈니스 로직"""

    # ------------------------------------------------------------------
    # 비밀번호 관련
    # ------------------------------------------------------------------

    def hash_password(self, password: str) -> str:
        """
        비밀번호 해싱

        Args:
            password: 평문 비밀번호

        Returns:
            해시된 비밀번호 (문자열)
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
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
            return bcrypt.checkpw(
                password.encode('utf-8'),
                password_hash.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False

    # ------------------------------------------------------------------
    # JWT 토큰 생성
    # ------------------------------------------------------------------

    def create_access_token(self, worker_id: int, email: str, role: str) -> str:
        """
        JWT 액세스 토큰 생성 (2시간 만료)

        Args:
            worker_id: 작업자 ID
            email: 이메일
            role: 역할

        Returns:
            JWT 액세스 토큰
        """
        now = datetime.now(timezone.utc)
        payload = {
            'sub': str(worker_id),
            'email': email,
            'role': role,
            'type': 'access',
            'iat': now,
            'exp': now + Config.JWT_ACCESS_TOKEN_EXPIRES,
        }
        return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm='HS256')

    def create_refresh_token(self, worker_id: int, email: str) -> str:
        """
        JWT 리프레시 토큰 생성 (30일 만료)

        Access Token이 만료되었을 때 새 Access Token을 발급받기 위해 사용.
        Refresh Token 전용 시크릿 키(JWT_REFRESH_SECRET_KEY)를 사용하여
        Access Token과 완전히 분리.

        Args:
            worker_id: 작업자 ID
            email: 이메일

        Returns:
            JWT 리프레시 토큰
        """
        now = datetime.now(timezone.utc)
        payload = {
            'sub': str(worker_id),
            'email': email,
            'type': 'refresh',
            'jti': str(uuid.uuid4()),  # Sprint 19-A: rotation 시 고유성 보장
            'iat': now,
            'exp': now + Config.JWT_REFRESH_TOKEN_EXPIRES,
        }
        return jwt.encode(
            payload,
            Config.JWT_REFRESH_SECRET_KEY,
            algorithm='HS256'
        )

    def verify_refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        리프레시 토큰 검증

        Args:
            refresh_token: 리프레시 토큰 문자열

        Returns:
            payload dict (sub, email, type), 유효하지 않으면 None
        """
        try:
            payload = jwt.decode(
                refresh_token,
                Config.JWT_REFRESH_SECRET_KEY,
                algorithms=['HS256']
            )
            # type 클레임이 'refresh'인지 확인
            if payload.get('type') != 'refresh':
                logger.warning("Token type is not 'refresh'")
                return None
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Refresh token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid refresh token: {e}")
            return None

    # ------------------------------------------------------------------
    # 이메일 발송
    # ------------------------------------------------------------------

    def send_verification_email(self, to_email: str, code: str) -> bool:
        """
        이메일 인증 코드 발송 (smtplib SMTP_SSL/STARTTLS)

        SMTP 설정이 없으면(SMTP_USER 미설정) 로그만 출력하고 True 반환
        (개발 환경 fallback).

        Args:
            to_email: 수신자 이메일
            code: 6자리 인증 코드

        Returns:
            발송 성공 시 True, 실패 시 False
        """
        # Rate limit 체크 (DoS 방지)
        if not _check_email_rate_limit(to_email):
            logger.warning(f"Email rate limit exceeded: {to_email}")
            return False

        # SMTP 미설정 시 개발 환경 fallback
        if not Config.SMTP_USER:
            logger.info(
                f"[DEV] Verification email (SMTP not configured): "
                f"to={to_email}, code={code}"
            )
            return True

        try:
            # HTML + Plain 멀티파트 메일 구성
            msg = MIMEMultipart('alternative')
            msg['Subject'] = '[G-AXIS] 이메일 인증 코드'
            msg['From'] = f"{Config.SMTP_FROM_NAME} <{Config.SMTP_FROM_EMAIL}>"
            msg['To'] = to_email

            # Plain text 본문
            plain_body = (
                f"G-AXIS 이메일 인증 코드\n\n"
                f"인증 코드: {code}\n\n"
                f"이 코드는 10분 후 만료됩니다.\n"
                f"본인이 요청하지 않은 경우 이 메일을 무시하세요."
            )

            # HTML 본문
            html_body = f"""
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"></head>
<body style="font-family: sans-serif; background-color: #f5f5f5; padding: 20px;">
  <div style="max-width: 480px; margin: 0 auto; background: #ffffff;
              border-radius: 8px; padding: 32px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
    <h2 style="color: #1a1a2e; margin-bottom: 8px;">G-AXIS 이메일 인증</h2>
    <p style="color: #555; margin-bottom: 24px;">아래 인증 코드를 앱에 입력하세요.</p>
    <div style="font-size: 36px; font-weight: bold; letter-spacing: 8px;
                color: #1a1a2e; text-align: center; padding: 16px;
                background: #f0f4ff; border-radius: 8px; margin-bottom: 24px;">
      {code}
    </div>
    <p style="color: #888; font-size: 13px;">이 코드는 <strong>10분</strong> 후 만료됩니다.</p>
    <p style="color: #888; font-size: 13px;">본인이 요청하지 않은 경우 이 메일을 무시하세요.</p>
  </div>
</body>
</html>
"""

            msg.attach(MIMEText(plain_body, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))

            # 포트에 따라 SSL 직접 연결(465) 또는 STARTTLS(587) 사용
            if Config.SMTP_PORT == 465:
                with smtplib.SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10) as server:
                    server.ehlo()
                    server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
                    server.sendmail(Config.SMTP_FROM_EMAIL, to_email, msg.as_string())
            else:
                with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
                    server.sendmail(Config.SMTP_FROM_EMAIL, to_email, msg.as_string())

            logger.info(f"Verification email sent: to={to_email}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error(
                "SMTP authentication failed — "
                "SMTP_USER/SMTP_PASSWORD 설정을 확인하세요."
            )
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error while sending to {to_email}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error while sending email to {to_email}: {e}")
            return False

    # ------------------------------------------------------------------
    # 비즈니스 로직
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        email: str,
        password: str,
        role: str,
        company: Optional[str] = None
    ) -> Tuple[Dict[str, Any], int]:
        """
        사용자 회원가입

        1. 역할 검증 (ADMIN은 회원가입 불가 — DB Seed 전용)
        2. company↔role 일치 검증 (company 입력 시)
        3. 비밀번호 해싱 + 작업자 생성
        4. 이메일 인증 코드 생성
        5. 인증 코드를 이메일로 발송 (SMTP 연동)

        Args:
            name: 사용자 이름
            email: 이메일
            password: 비밀번호 (평문)
            role: 역할 (MECH, ELEC, TM, PI, QI, SI)
            company: 소속 회사 (FNI, BAT, TMS(M), TMS(E), P&S, C&A, GST)

        Returns:
            (response dict, status code)
        """
        # 역할 검증
        if role not in VALID_ROLES:
            return {
                'error': 'INVALID_ROLE',
                'message': f"유효하지 않은 역할입니다. 가능한 역할: {', '.join(sorted(VALID_ROLES))}"
            }, 400

        # company↔role 일치 검증 (company 입력 시)
        if company is not None:
            allowed_roles = COMPANY_ROLE_MAP.get(company)
            if allowed_roles is None:
                return {
                    'error': 'INVALID_COMPANY',
                    'message': f"유효하지 않은 회사입니다. 가능한 회사: {', '.join(sorted(COMPANY_ROLE_MAP.keys()))}"
                }, 400
            if role not in allowed_roles:
                return {
                    'error': 'COMPANY_ROLE_MISMATCH',
                    'message': f"{company} 소속은 {', '.join(sorted(allowed_roles))} 역할만 선택 가능합니다."
                }, 400

        # 비밀번호 해싱
        password_hash = self.hash_password(password)

        # 작업자 생성
        worker_id = create_worker(
            name=name,
            email=email,
            password_hash=password_hash,
            role=role,
            company=company
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
            logger.error(
                f"Failed to create verification code for worker_id={worker_id}"
            )
            return {
                'error': 'REGISTRATION_FAILED',
                'message': '회원가입 처리 중 오류가 발생했습니다.'
            }, 500

        # 인증 메일 발송 (실패해도 회원가입은 성공 처리 — 재발송 기능으로 대응)
        email_sent = self.send_verification_email(email, verification_code)
        if not email_sent:
            logger.warning(
                f"Verification email failed for worker_id={worker_id}, "
                f"email={email}. Code logged for debugging: {verification_code}"
            )

        response: Dict[str, Any] = {
            'message': '회원가입 성공. 이메일로 발송된 인증 코드를 입력하세요.',
            'worker_id': worker_id,
        }

        # 개발 환경(SMTP 미설정)에서만 코드 노출
        if not Config.SMTP_USER:
            response['verification_code'] = verification_code

        return response, 201

    def login(self, email: str, password: str) -> Tuple[Dict[str, Any], int]:
        """
        로그인

        Admin 정책: is_admin=True이면 이메일 인증 / 승인 상태 체크 건너뜀.
        일반 사용자: 이메일 인증 완료 + 승인(approved) 상태 필수.

        Args:
            email: 이메일
            password: 비밀번호 (평문)

        Returns:
            (response dict with access_token + refresh_token, status code)
        """
        # 사용자 조회 (Admin prefix 매칭: '@' 없으면 admin prefix 우선 시도)
        if '@' in email:
            worker = get_worker_by_email(email)
        else:
            worker = get_admin_by_email_prefix(email)
            if worker is None:
                worker = get_worker_by_email(email)  # fallback

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

        # Admin freepass: 이메일 인증 / 승인 체크 건너뜀
        if not worker.is_admin:
            # 이메일 인증 확인
            if not worker.email_verified:
                return {
                    'error': 'EMAIL_NOT_VERIFIED',
                    'message': '이메일 인증을 먼저 완료하세요.'
                }, 403

            # 승인 상태 확인
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

        # JWT 토큰 생성 (access + refresh)
        access_token = self.create_access_token(
            worker_id=worker.id,
            email=worker.email,
            role=worker.role
        )
        refresh_token = self.create_refresh_token(
            worker_id=worker.id,
            email=worker.email
        )

        logger.info(f"Login success: worker_id={worker.id}, email={email}, role={worker.role}")

        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'worker': {
                'id': worker.id,
                'name': worker.name,
                'email': worker.email,
                'role': worker.role,
                'company': worker.company,
                'approval_status': worker.approval_status,
                'is_manager': worker.is_manager,
                'is_admin': worker.is_admin,
                'email_verified': worker.email_verified,
            }
        }, 200

    def refresh_access_token(
        self,
        refresh_token: str
    ) -> Tuple[Dict[str, Any], int]:
        """
        Refresh Token으로 새 Access Token 발급

        Args:
            refresh_token: 리프레시 토큰 문자열

        Returns:
            (response dict with new access_token, status code)
        """
        payload = self.verify_refresh_token(refresh_token)

        if payload is None:
            return {
                'error': 'INVALID_REFRESH_TOKEN',
                'message': '유효하지 않거나 만료된 리프레시 토큰입니다.'
            }, 401

        worker_id = int(payload['sub'])
        email = payload['email']

        # 작업자 최신 정보 조회 (비활성화/탈퇴 여부 재확인)
        worker = get_worker_by_email(email)
        if worker is None or worker.id != worker_id:
            return {
                'error': 'USER_NOT_FOUND',
                'message': '사용자를 찾을 수 없습니다.'
            }, 401

        # 일반 사용자는 승인 상태도 재확인
        if not worker.is_admin and worker.approval_status != 'approved':
            return {
                'error': 'ACCOUNT_INACTIVE',
                'message': '계정이 비활성화되었습니다.'
            }, 403

        new_access_token = self.create_access_token(
            worker_id=worker.id,
            email=worker.email,
            role=worker.role
        )

        # Sprint 19-A: Refresh Token Rotation — 새 refresh_token도 함께 발급
        new_refresh_token = self.create_refresh_token(
            worker_id=worker.id,
            email=worker.email
        )

        logger.info(f"Token rotation: worker_id={worker_id}, new refresh_token issued")

        return {
            'access_token': new_access_token,
            'refresh_token': new_refresh_token,
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
                'message': '이미 사용된 인증 코드입니다.'
            }, 400

        # 작업자 이메일 인증 완료 처리
        if not update_email_verified(worker_id):
            return {
                'error': 'VERIFICATION_FAILED',
                'message': '인증 처리 실패'
            }, 500

        logger.info(f"Email verified successfully: worker_id={worker_id}")

        return {
            'message': '이메일 인증이 완료되었습니다. 관리자 승인 후 로그인 가능합니다.'
        }, 200

    def send_password_reset_email(self, to_email: str, code: str) -> bool:
        """
        비밀번호 재설정 코드 이메일 발송

        send_verification_email과 동일한 SMTP 패턴을 사용하되
        제목과 본문만 비밀번호 재설정용으로 변경.

        Args:
            to_email: 수신자 이메일
            code: 6자리 재설정 코드

        Returns:
            발송 성공 시 True, 실패 시 False
        """
        # Rate limit 체크 (DoS 방지)
        if not _check_email_rate_limit(to_email):
            logger.warning(f"Email rate limit exceeded: {to_email}")
            return False

        # SMTP 미설정 시 개발 환경 fallback
        if not Config.SMTP_USER:
            logger.info(
                f"[DEV] Password reset email (SMTP not configured): "
                f"to={to_email}, code={code}"
            )
            return True

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = '[G-AXIS] 비밀번호 재설정 코드'
            msg['From'] = f"{Config.SMTP_FROM_NAME} <{Config.SMTP_FROM_EMAIL}>"
            msg['To'] = to_email

            plain_body = (
                f"G-AXIS 비밀번호 재설정 코드\n\n"
                f"재설정 코드: {code}\n\n"
                f"이 코드는 30분 후 만료됩니다.\n"
                f"본인이 요청하지 않은 경우 이 메일을 무시하세요."
            )

            html_body = f"""
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"></head>
<body style="font-family: sans-serif; background-color: #f5f5f5; padding: 20px;">
  <div style="max-width: 480px; margin: 0 auto; background: #ffffff;
              border-radius: 8px; padding: 32px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
    <h2 style="color: #1a1a2e; margin-bottom: 8px;">G-AXIS 비밀번호 재설정</h2>
    <p style="color: #555; margin-bottom: 24px;">아래 코드를 앱에 입력하여 비밀번호를 재설정하세요.</p>
    <div style="font-size: 36px; font-weight: bold; letter-spacing: 8px;
                color: #1a1a2e; text-align: center; padding: 16px;
                background: #f0f4ff; border-radius: 8px; margin-bottom: 24px;">
      {code}
    </div>
    <p style="color: #888; font-size: 13px;">이 코드는 <strong>30분</strong> 후 만료됩니다.</p>
    <p style="color: #888; font-size: 13px;">본인이 요청하지 않은 경우 이 메일을 무시하세요.</p>
  </div>
</body>
</html>
"""

            msg.attach(MIMEText(plain_body, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))

            if Config.SMTP_PORT == 465:
                with smtplib.SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10) as server:
                    server.ehlo()
                    server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
                    server.sendmail(Config.SMTP_FROM_EMAIL, to_email, msg.as_string())
            else:
                with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
                    server.sendmail(Config.SMTP_FROM_EMAIL, to_email, msg.as_string())

            logger.info(f"Password reset email sent: to={to_email}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error(
                "SMTP authentication failed — "
                "SMTP_USER/SMTP_PASSWORD 설정을 확인하세요."
            )
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error while sending to {to_email}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error while sending email to {to_email}: {e}")
            return False

    def send_password_reset_code(self, email: str) -> Tuple[Dict[str, Any], int]:
        """
        비밀번호 재설정 코드 발송

        보안상 이메일이 존재하지 않아도 동일한 성공 응답 반환 (이메일 열거 공격 방지).
        코드 유효기간: 30분.

        Args:
            email: 가입된 이메일 주소

        Returns:
            (response dict, status code)
        """
        worker = get_worker_by_email(email)

        if worker is None:
            # 보안: 이메일 존재 여부를 노출하지 않음
            logger.info(f"Password reset requested for non-existent email: {email}")
            return {
                'message': '입력하신 이메일로 재설정 코드를 발송했습니다.'
            }, 200

        reset_code = create_password_reset_code(worker.id)

        if reset_code is None:
            logger.error(f"Failed to create password reset code for worker_id={worker.id}")
            return {
                'error': 'RESET_CODE_FAILED',
                'message': '재설정 코드 생성 중 오류가 발생했습니다.'
            }, 500

        email_sent = self.send_password_reset_email(email, reset_code)
        if not email_sent:
            logger.warning(
                f"Password reset email failed for worker_id={worker.id}, "
                f"email={email}. Code logged for debugging: {reset_code}"
            )

        response: Dict[str, Any] = {
            'message': '입력하신 이메일로 재설정 코드를 발송했습니다.'
        }

        # 개발 환경(SMTP 미설정)에서만 코드 노출
        if not Config.SMTP_USER:
            response['reset_code'] = reset_code

        logger.info(f"Password reset code sent: worker_id={worker.id}, email={email}")
        return response, 200

    def reset_password(
        self,
        email: str,
        code: str,
        new_password: str
    ) -> Tuple[Dict[str, Any], int]:
        """
        비밀번호 재설정

        1. 이메일로 작업자 조회
        2. 재설정 코드 검증 (코드 일치 + 만료 여부)
        3. 새 비밀번호 bcrypt 해싱 후 DB 업데이트
        4. 코드 사용 완료 처리

        Args:
            email: 가입된 이메일 주소
            code: 6자리 재설정 코드
            new_password: 새 비밀번호 (평문)

        Returns:
            (response dict, status code)
        """
        worker = get_worker_by_email(email)

        if worker is None:
            return {
                'error': 'INVALID_RESET_CODE',
                'message': '유효하지 않거나 만료된 재설정 코드입니다.'
            }, 400

        # 인증 코드 조회 및 만료 확인 (get_verification_code는 만료 코드 None 반환)
        verification = get_verification_code(code)

        if verification is None:
            return {
                'error': 'INVALID_RESET_CODE',
                'message': '유효하지 않거나 만료된 재설정 코드입니다.'
            }, 400

        # 코드가 해당 작업자의 것인지 확인
        if verification['worker_id'] != worker.id:
            return {
                'error': 'INVALID_RESET_CODE',
                'message': '유효하지 않거나 만료된 재설정 코드입니다.'
            }, 400

        # 코드 사용 완료 처리 (이미 사용된 코드 방지)
        if not mark_code_as_verified(code):
            return {
                'error': 'INVALID_RESET_CODE',
                'message': '이미 사용된 재설정 코드입니다.'
            }, 400

        # 새 비밀번호 해싱 후 업데이트
        new_hash = self.hash_password(new_password)
        if not update_password_hash(worker.id, new_hash):
            return {
                'error': 'RESET_FAILED',
                'message': '비밀번호 재설정 중 오류가 발생했습니다.'
            }, 500

        logger.info(f"Password reset successful: worker_id={worker.id}, email={email}")

        return {
            'message': '비밀번호가 성공적으로 재설정되었습니다.'
        }, 200
