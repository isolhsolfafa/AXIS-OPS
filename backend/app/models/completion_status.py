"""
작업 완료 상태 모델 및 CRUD 함수
테이블: completion_status
Sprint 2: 공정별 완료 상태 업데이트 + 전체 완료 추적
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from psycopg2 import Error as PsycopgError

from .worker import get_db_connection


logger = logging.getLogger(__name__)


@dataclass
class CompletionStatus:
    """
    작업 완료 상태 모델

    Attributes:
        serial_number: 시리얼 번호 (PRIMARY KEY)
        mm_completed: MM 공정 완료 여부
        ee_completed: EE 공정 완료 여부
        tm_completed: TM 공정 완료 여부
        pi_completed: PI 공정 완료 여부
        qi_completed: QI 공정 완료 여부
        si_completed: SI 공정 완료 여부
        all_completed: 모든 공정 완료 여부
        all_completed_at: 전체 완료 시각
        created_at: 생성 시간
        updated_at: 수정 시간
    """

    serial_number: str
    mm_completed: bool
    ee_completed: bool
    tm_completed: bool
    pi_completed: bool
    qi_completed: bool
    si_completed: bool
    all_completed: bool
    all_completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_db_row(row: Dict[str, Any]) -> "CompletionStatus":
        """
        데이터베이스 행에서 CompletionStatus 객체 생성

        Args:
            row: RealDictCursor로 조회한 dict 형태의 행

        Returns:
            CompletionStatus 객체
        """
        return CompletionStatus(
            serial_number=row['serial_number'],
            mm_completed=row['mm_completed'],
            ee_completed=row['ee_completed'],
            tm_completed=row['tm_completed'],
            pi_completed=row['pi_completed'],
            qi_completed=row['qi_completed'],
            si_completed=row['si_completed'],
            all_completed=row['all_completed'],
            all_completed_at=row.get('all_completed_at'),
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )


def get_or_create_completion_status(serial_number: str) -> Optional[CompletionStatus]:
    """
    완료 상태 조회 또는 생성

    Args:
        serial_number: 시리얼 번호

    Returns:
        CompletionStatus 객체, 실패 시 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 먼저 조회 시도
        cur.execute(
            "SELECT * FROM completion_status WHERE serial_number = %s",
            (serial_number,)
        )
        row = cur.fetchone()

        if row:
            return CompletionStatus.from_db_row(row)

        # 없으면 생성
        cur.execute(
            """
            INSERT INTO completion_status (serial_number)
            VALUES (%s)
            RETURNING *
            """,
            (serial_number,)
        )

        row = cur.fetchone()
        conn.commit()

        logger.info(f"Completion status created: serial_number={serial_number}")
        return CompletionStatus.from_db_row(row)

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to get or create completion status: {e}")
        return None
    finally:
        if conn:
            conn.close()


def update_process_completion(serial_number: str, process_type: str, completed: bool) -> bool:
    """
    특정 공정 완료 상태 업데이트

    Args:
        serial_number: 시리얼 번호
        process_type: 공정 유형 (MM, EE, TM, PI, QI, SI)
        completed: 완료 여부

    Returns:
        성공 시 True, 실패 시 False
    """
    process_map = {
        'MM': 'mm_completed',
        'EE': 'ee_completed',
        'TM': 'tm_completed',
        'PI': 'pi_completed',
        'QI': 'qi_completed',
        'SI': 'si_completed'
    }

    column = process_map.get(process_type)
    if not column:
        logger.warning(f"Invalid process_type: {process_type}")
        return False

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 먼저 레코드가 없으면 생성
        cur.execute(
            """
            INSERT INTO completion_status (serial_number)
            VALUES (%s)
            ON CONFLICT (serial_number) DO NOTHING
            """,
            (serial_number,)
        )

        # 공정 완료 상태 업데이트
        query = f"""
            UPDATE completion_status
            SET {column} = %s
            WHERE serial_number = %s
        """
        cur.execute(query, (completed, serial_number))

        updated = cur.rowcount > 0
        conn.commit()

        if updated:
            logger.info(f"Process completion updated: serial_number={serial_number}, {column}={completed}")
        return updated

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to update process completion: {e}")
        return False
    finally:
        if conn:
            conn.close()


def update_all_completed(serial_number: str, all_completed: bool, completed_at: Optional[datetime] = None) -> bool:
    """
    전체 공정 완료 상태 업데이트

    Args:
        serial_number: 시리얼 번호
        all_completed: 전체 완료 여부
        completed_at: 완료 시각 (timezone-aware)

    Returns:
        성공 시 True, 실패 시 False
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE completion_status
            SET all_completed = %s, all_completed_at = %s
            WHERE serial_number = %s
            """,
            (all_completed, completed_at, serial_number)
        )

        updated = cur.rowcount > 0
        conn.commit()

        if updated:
            logger.info(f"All completed updated: serial_number={serial_number}, all_completed={all_completed}")
        return updated

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to update all_completed: {e}")
        return False
    finally:
        if conn:
            conn.close()


def check_all_processes_completed(serial_number: str) -> bool:
    """
    모든 공정 완료 여부 확인

    Args:
        serial_number: 시리얼 번호

    Returns:
        모든 공정 완료 시 True, 아니면 False
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT mm_completed, ee_completed, tm_completed,
                   pi_completed, qi_completed, si_completed
            FROM completion_status
            WHERE serial_number = %s
            """,
            (serial_number,)
        )

        row = cur.fetchone()
        if not row:
            return False

        # 모든 공정이 완료되었는지 확인
        return all([
            row['mm_completed'],
            row['ee_completed'],
            row['tm_completed'],
            row['pi_completed'],
            row['qi_completed'],
            row['si_completed']
        ])

    except PsycopgError as e:
        logger.error(f"Failed to check all processes completed: {e}")
        return False
    finally:
        if conn:
            conn.close()
