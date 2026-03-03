"""
작업자 모델 및 CRUD 함수
테이블: workers, email_verification
Sprint 5: EmailVerification dataclass 추가
Sprint 11: active_role 컬럼 추가 (GST 작업자 역할 전환)
"""

import random
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import psycopg2
import psycopg2.extras
from psycopg2 import Error as PsycopgError

from ..config import Config


logger = logging.getLogger(__name__)


@dataclass
class Worker:
    """
    작업자 모델

    Attributes:
        id: 작업자 ID
        name: 작업자 이름
        email: 이메일
        password_hash: 비밀번호 해시
        role: 역할 (MECH, ELEC, TM, PI, QI, SI, ADMIN)
        approval_status: 승인 상태 (pending, approved, rejected)
        email_verified: 이메일 인증 완료 여부
        is_manager: 협력사 관리자 여부
        is_admin: 시스템 관리자 여부
        company: 소속 회사 (FNI, BAT, TMS(M), TMS(E), P&S, C&A, GST)
        created_at: 생성 시간
        updated_at: 수정 시간
    """

    id: int
    name: str
    email: str
    password_hash: str
    role: str
    approval_status: str
    email_verified: bool
    is_manager: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime
    company: Optional[str] = None
    active_role: Optional[str] = None  # Sprint 11: GST 작업자 역할 전환용

    @staticmethod
    def from_db_row(row: Dict[str, Any]) -> "Worker":
        """
        데이터베이스 행에서 Worker 객체 생성

        Args:
            row: RealDictCursor로 조회한 dict 형태의 행

        Returns:
            Worker 객체
        """
        return Worker(
            id=row['id'],
            name=row['name'],
            email=row['email'],
            password_hash=row['password_hash'],
            role=row['role'],
            approval_status=row['approval_status'],
            email_verified=row['email_verified'],
            is_manager=row['is_manager'],
            is_admin=row['is_admin'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            company=row.get('company'),
            active_role=row.get('active_role')  # Sprint 11
        )


@dataclass
class EmailVerification:
    """
    이메일 인증 모델

    Attributes:
        id: 인증 레코드 ID
        worker_id: 작업자 ID (FK → workers.id)
        verification_code: 6자리 인증 코드 (UNIQUE)
        expires_at: 만료 시각
        verified_at: 인증 완료 시각 (NULL이면 미완료)
        created_at: 생성 시각
    """

    id: int
    worker_id: int
    verification_code: str
    expires_at: datetime
    verified_at: Optional[datetime]
    created_at: datetime

    @staticmethod
    def from_db_row(row: Dict[str, Any]) -> "EmailVerification":
        """
        데이터베이스 행에서 EmailVerification 객체 생성

        Args:
            row: RealDictCursor로 조회한 dict 형태의 행

        Returns:
            EmailVerification 객체
        """
        return EmailVerification(
            id=row['id'],
            worker_id=row['worker_id'],
            verification_code=row['verification_code'],
            expires_at=row['expires_at'],
            verified_at=row.get('verified_at'),
            created_at=row['created_at']
        )


def get_db_connection() -> psycopg2.extensions.connection:
    """
    데이터베이스 연결 생성

    Returns:
        psycopg2 connection 객체

    Raises:
        psycopg2.Error: DB 연결 실패 시
    """
    try:
        conn = psycopg2.connect(
            Config.DATABASE_URL,
            cursor_factory=psycopg2.extras.RealDictCursor,
            options="-c timezone=Asia/Seoul"
        )
        return conn
    except PsycopgError as e:
        logger.error(f"Database connection failed: {e}")
        raise


def create_worker(
    name: str,
    email: str,
    password_hash: str,
    role: str,
    is_manager: bool = False,
    is_admin: bool = False,
    company: Optional[str] = None
) -> Optional[int]:
    """
    새 작업자 생성

    Args:
        name: 작업자 이름
        email: 이메일 (unique)
        password_hash: 암호화된 비밀번호
        role: 역할 (MECH, ELEC, TM, PI, QI, SI, ADMIN)
        is_manager: 협력사 관리자 여부
        is_admin: 시스템 관리자 여부
        company: 소속 회사 (FNI, BAT, TMS(M), TMS(E), P&S, C&A, GST)

    Returns:
        생성된 작업자 ID, 실패 시 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO workers (name, email, password_hash, role, is_manager, is_admin, company)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (name, email, password_hash, role, is_manager, is_admin, company)
        )

        worker_id = cur.fetchone()['id']
        conn.commit()

        logger.info(f"Worker created: id={worker_id}, email={email}, role={role}")
        return worker_id

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        logger.warning(f"Worker creation failed (duplicate email?): {e}")
        return None
    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Worker creation failed: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_worker_by_id(worker_id: int) -> Optional[Worker]:
    """
    ID로 작업자 조회

    Args:
        worker_id: 작업자 ID

    Returns:
        Worker 객체, 없으면 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM workers WHERE id = %s",
            (worker_id,)
        )

        row = cur.fetchone()
        if row:
            return Worker.from_db_row(row)
        return None

    except PsycopgError as e:
        logger.error(f"Failed to get worker by id={worker_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_worker_by_email(email: str) -> Optional[Worker]:
    """
    이메일로 작업자 조회 (로그인 시 사용)

    Args:
        email: 이메일 주소

    Returns:
        Worker 객체, 없으면 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM workers WHERE email = %s",
            (email,)
        )

        row = cur.fetchone()
        if row:
            return Worker.from_db_row(row)
        return None

    except PsycopgError as e:
        logger.error(f"Failed to get worker by email={email}: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_admin_by_email_prefix(prefix: str) -> Optional[Worker]:
    """
    이메일 prefix로 관리자 조회 (Admin 간편 로그인용)

    'admin' 입력 시 'admin@gst-in.com' 매칭.
    매칭 결과가 정확히 1명일 때만 반환, 0명/2명+ → None.

    Args:
        prefix: 이메일 @ 앞부분 (예: 'dkkim1', 'admin')

    Returns:
        Worker 객체 (매칭 1명), 없거나 2명+ 시 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM workers WHERE email LIKE %s AND is_admin = TRUE",
            (prefix + '@%',)
        )

        rows = cur.fetchall()
        if len(rows) == 1:
            return Worker.from_db_row(rows[0])
        return None

    except PsycopgError as e:
        logger.error(f"Failed to get admin by email prefix={prefix}: {e}")
        return None
    finally:
        if conn:
            conn.close()


def update_approval_status(worker_id: int, status: str) -> bool:
    """
    작업자 승인 상태 업데이트 (관리자 전용)

    Args:
        worker_id: 작업자 ID
        status: 승인 상태 ('approved' | 'rejected')

    Returns:
        성공 시 True, 실패 시 False
    """
    if status not in ('approved', 'rejected'):
        logger.warning(f"Invalid approval status: {status}")
        return False

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "UPDATE workers SET approval_status = %s WHERE id = %s",
            (status, worker_id)
        )

        updated = cur.rowcount > 0
        conn.commit()

        if updated:
            logger.info(f"Worker approval status updated: id={worker_id}, status={status}")
        return updated

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to update approval status: {e}")
        return False
    finally:
        if conn:
            conn.close()


def update_email_verified(worker_id: int) -> bool:
    """
    이메일 인증 완료 처리

    Args:
        worker_id: 작업자 ID

    Returns:
        성공 시 True, 실패 시 False
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "UPDATE workers SET email_verified = TRUE WHERE id = %s",
            (worker_id,)
        )

        updated = cur.rowcount > 0
        conn.commit()

        if updated:
            logger.info(f"Worker email verified: id={worker_id}")
        return updated

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to update email_verified: {e}")
        return False
    finally:
        if conn:
            conn.close()


def create_verification_code(worker_id: int) -> Optional[str]:
    """
    이메일 인증 코드 생성 (6자리 숫자, 10분 만료)

    Args:
        worker_id: 작업자 ID

    Returns:
        생성된 인증 코드 (6자리 숫자), 실패 시 None
    """
    conn = None

    # 중복 코드 발생 시 최대 3회 재시도
    for attempt in range(3):
        code = str(random.randint(100000, 999999))

        try:
            conn = get_db_connection()
            cur = conn.cursor()

            # 만료 시간: 현재 시각(KST) + 10분
            expires_at = datetime.now(Config.KST) + timedelta(minutes=10)

            cur.execute(
                """
                INSERT INTO email_verification (worker_id, verification_code, expires_at)
                VALUES (%s, %s, %s)
                RETURNING verification_code
                """,
                (worker_id, code, expires_at)
            )

            result = cur.fetchone()
            conn.commit()

            logger.info(f"Verification code created: worker_id={worker_id}, code={code}")
            return result['verification_code']

        except psycopg2.IntegrityError:
            # 중복 코드 발생 (UNIQUE 제약 위반)
            if conn:
                conn.rollback()
                conn.close()
            logger.warning(f"Duplicate verification code, retrying... (attempt {attempt + 1}/3)")
            continue
        except PsycopgError as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to create verification code: {e}")
            return None
        finally:
            if conn and not conn.closed:
                conn.close()

    logger.error("Failed to create verification code after 3 attempts")
    return None


def get_verification_code(code: str) -> Optional[Dict[str, Any]]:
    """
    인증 코드 조회 및 만료 확인

    Args:
        code: 6자리 인증 코드

    Returns:
        인증 정보 dict (id, worker_id, expires_at, verified_at), 없거나 만료 시 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT id, worker_id, expires_at, verified_at
            FROM email_verification
            WHERE verification_code = %s
            """,
            (code,)
        )

        row = cur.fetchone()
        if not row:
            return None

        # 만료 확인 (KST 기준)
        if row['expires_at'] < datetime.now(Config.KST):
            logger.warning(f"Verification code expired: code={code}")
            return None

        return dict(row)

    except PsycopgError as e:
        logger.error(f"Failed to get verification code: {e}")
        return None
    finally:
        if conn:
            conn.close()


def create_password_reset_code(worker_id: int) -> Optional[str]:
    """
    비밀번호 재설정 인증 코드 생성 (6자리 숫자, 30분 만료)

    Args:
        worker_id: 작업자 ID

    Returns:
        생성된 인증 코드 (6자리 숫자), 실패 시 None
    """
    conn = None

    # 중복 코드 발생 시 최대 3회 재시도
    for attempt in range(3):
        code = str(random.randint(100000, 999999))

        try:
            conn = get_db_connection()
            cur = conn.cursor()

            # 만료 시간: 현재 시각(KST) + 30분
            expires_at = datetime.now(Config.KST) + timedelta(minutes=30)

            cur.execute(
                """
                INSERT INTO email_verification (worker_id, verification_code, expires_at)
                VALUES (%s, %s, %s)
                RETURNING verification_code
                """,
                (worker_id, code, expires_at)
            )

            result = cur.fetchone()
            conn.commit()

            logger.info(f"Password reset code created: worker_id={worker_id}")
            return result['verification_code']

        except psycopg2.IntegrityError:
            # 중복 코드 발생 (UNIQUE 제약 위반)
            if conn:
                conn.rollback()
                conn.close()
            logger.warning(f"Duplicate reset code, retrying... (attempt {attempt + 1}/3)")
            continue
        except PsycopgError as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to create password reset code: {e}")
            return None
        finally:
            if conn and not conn.closed:
                conn.close()

    logger.error("Failed to create password reset code after 3 attempts")
    return None


def update_password_hash(worker_id: int, password_hash: str) -> bool:
    """
    작업자 비밀번호 해시 업데이트

    Args:
        worker_id: 작업자 ID
        password_hash: 새 bcrypt 해시

    Returns:
        성공 시 True, 실패 시 False
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "UPDATE workers SET password_hash = %s WHERE id = %s",
            (password_hash, worker_id)
        )

        updated = cur.rowcount > 0
        conn.commit()

        if updated:
            logger.info(f"Password hash updated: worker_id={worker_id}")
        return updated

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to update password hash: {e}")
        return False
    finally:
        if conn:
            conn.close()


def update_active_role(worker_id: int, active_role: str) -> bool:
    """
    Sprint 11: GST 작업자의 활성 역할 업데이트

    Args:
        worker_id: 작업자 ID
        active_role: 변경할 역할 (PI, QI, SI)

    Returns:
        성공 시 True, 실패 시 False
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "UPDATE workers SET active_role = %s, updated_at = NOW() WHERE id = %s",
            (active_role, worker_id)
        )

        updated = cur.rowcount > 0
        conn.commit()

        if updated:
            logger.info(f"Worker active_role updated: id={worker_id}, active_role={active_role}")
        return updated

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to update active_role: {e}")
        return False
    finally:
        if conn:
            conn.close()


def mark_code_as_verified(code: str) -> bool:
    """
    인증 코드를 사용 완료 처리

    Args:
        code: 6자리 인증 코드

    Returns:
        성공 시 True, 실패 시 False
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 이미 verified된 경우 체크
        cur.execute(
            "SELECT verified_at FROM email_verification WHERE verification_code = %s",
            (code,)
        )
        row = cur.fetchone()

        if not row:
            return False

        if row['verified_at'] is not None:
            logger.warning(f"Verification code already used: code={code}")
            return False

        # verified_at 업데이트
        cur.execute(
            "UPDATE email_verification SET verified_at = NOW() WHERE verification_code = %s",
            (code,)
        )

        updated = cur.rowcount > 0
        conn.commit()

        if updated:
            logger.info(f"Verification code marked as verified: code={code}")
        return updated

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to mark code as verified: {e}")
        return False
    finally:
        if conn:
            conn.close()
