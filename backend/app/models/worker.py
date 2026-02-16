"""
작업자 모델 및 CRUD 함수
테이블: workers, email_verification
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
        role: 역할 (MM, EE, TM, PI, QI, SI)
        approval_status: 승인 상태 (pending, approved, rejected)
        email_verified: 이메일 인증 완료 여부
        is_manager: 협력사 관리자 여부
        is_admin: 시스템 관리자 여부
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
            updated_at=row['updated_at']
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
            cursor_factory=psycopg2.extras.RealDictCursor
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
    is_admin: bool = False
) -> Optional[int]:
    """
    새 작업자 생성

    Args:
        name: 작업자 이름
        email: 이메일 (unique)
        password_hash: 암호화된 비밀번호
        role: 역할 (MM, EE, TM, PI, QI, SI)
        is_manager: 협력사 관리자 여부
        is_admin: 시스템 관리자 여부

    Returns:
        생성된 작업자 ID, 실패 시 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO workers (name, email, password_hash, role, is_manager, is_admin)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (name, email, password_hash, role, is_manager, is_admin)
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

            # 만료 시간: 현재 시각 + 10분
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

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

        # 만료 확인 (DB는 timezone-aware이므로 aware datetime 사용)
        if row['expires_at'] < datetime.now(timezone.utc):
            logger.warning(f"Verification code expired: code={code}")
            return None

        return dict(row)

    except PsycopgError as e:
        logger.error(f"Failed to get verification code: {e}")
        return None
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
