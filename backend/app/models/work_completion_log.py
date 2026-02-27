"""
작업 완료 로그 모델 및 CRUD 함수
테이블: work_completion_log
감사(audit) 목적: 작업 완료 이벤트를 별도 로그 테이블에 기록
duration_minutes = completed_at - started_at (app_task_details에서 계산)
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

from psycopg2 import Error as PsycopgError

from .worker import get_db_connection


logger = logging.getLogger(__name__)


@dataclass
class WorkCompletionLog:
    """
    작업 완료 로그 모델

    Attributes:
        id: 로그 ID
        task_id: app_task_details의 작업 ID (FK)
        worker_id: 작업자 ID (FK)
        serial_number: 시리얼 번호
        qr_doc_id: QR 문서 ID
        task_category: Task 카테고리 (MM, EE, TM, PI, QI, SI)
        task_id_ref: Task 식별자 (예: CABINET_ASSY) — task_id 컬럼과 충돌 방지로 _ref 접미사
        task_name: Task 이름 (예: 캐비넷 조립)
        completed_at: 완료 시간
        duration_minutes: 소요 시간 (분 단위, completed_at - started_at)
        created_at: 로그 생성 시간
    """

    id: int
    task_id: int
    worker_id: int
    serial_number: str
    qr_doc_id: str
    task_category: str
    task_id_ref: str
    task_name: str
    completed_at: datetime
    duration_minutes: Optional[int]
    created_at: datetime

    @staticmethod
    def from_db_row(row: Dict[str, Any]) -> "WorkCompletionLog":
        """
        데이터베이스 행에서 WorkCompletionLog 객체 생성

        Args:
            row: RealDictCursor로 조회한 dict 형태의 행

        Returns:
            WorkCompletionLog 객체
        """
        return WorkCompletionLog(
            id=row['id'],
            task_id=row['task_id'],
            worker_id=row['worker_id'],
            serial_number=row['serial_number'],
            qr_doc_id=row['qr_doc_id'],
            task_category=row['task_category'],
            task_id_ref=row['task_id_ref'],
            task_name=row['task_name'],
            completed_at=row['completed_at'],
            duration_minutes=row.get('duration_minutes'),
            created_at=row['created_at']
        )


def create_work_completion_log(
    task_id: int,
    worker_id: int,
    serial_number: str,
    qr_doc_id: str,
    task_category: str,
    task_id_ref: str,
    task_name: str,
    completed_at: datetime,
    duration_minutes: Optional[int] = None
) -> Optional[int]:
    """
    작업 완료 로그 기록

    Args:
        task_id: app_task_details의 작업 ID
        worker_id: 작업자 ID
        serial_number: 시리얼 번호
        qr_doc_id: QR 문서 ID
        task_category: Task 카테고리
        task_id_ref: Task 식별자
        task_name: Task 이름
        completed_at: 완료 시간 (timezone-aware)
        duration_minutes: 소요 시간 (분), None이면 DB 계산 결과를 사용

    Returns:
        생성된 로그 ID, 실패 시 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO work_completion_log (
                task_id, worker_id, serial_number, qr_doc_id,
                task_category, task_id_ref, task_name,
                completed_at, duration_minutes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (task_id, worker_id, serial_number, qr_doc_id,
             task_category, task_id_ref, task_name,
             completed_at, duration_minutes)
        )

        log_id = cur.fetchone()['id']
        conn.commit()

        logger.info(
            f"WorkCompletionLog created: id={log_id}, task_id={task_id}, "
            f"worker_id={worker_id}, serial_number={serial_number}, "
            f"duration_minutes={duration_minutes}"
        )
        return log_id

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"WorkCompletionLog creation failed: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_work_completion_log_by_id(log_id: int) -> Optional[WorkCompletionLog]:
    """
    ID로 작업 완료 로그 조회

    Args:
        log_id: 로그 ID

    Returns:
        WorkCompletionLog 객체, 없으면 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM work_completion_log WHERE id = %s",
            (log_id,)
        )

        row = cur.fetchone()
        if row:
            return WorkCompletionLog.from_db_row(row)
        return None

    except PsycopgError as e:
        logger.error(f"Failed to get work_completion_log by id={log_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_work_completion_logs_by_serial(
    serial_number: str,
    limit: int = 100
) -> List[WorkCompletionLog]:
    """
    시리얼 번호로 작업 완료 로그 목록 조회

    Args:
        serial_number: 시리얼 번호
        limit: 조회 제한 (기본 100개)

    Returns:
        WorkCompletionLog 리스트 (최신순)
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT * FROM work_completion_log
            WHERE serial_number = %s
            ORDER BY completed_at DESC
            LIMIT %s
            """,
            (serial_number, limit)
        )

        rows = cur.fetchall()
        return [WorkCompletionLog.from_db_row(row) for row in rows]

    except PsycopgError as e:
        logger.error(f"Failed to get work_completion_logs for serial_number={serial_number}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_work_completion_logs_by_worker(
    worker_id: int,
    limit: int = 100
) -> List[WorkCompletionLog]:
    """
    작업자별 작업 완료 로그 목록 조회

    Args:
        worker_id: 작업자 ID
        limit: 조회 제한 (기본 100개)

    Returns:
        WorkCompletionLog 리스트 (최신순)
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT * FROM work_completion_log
            WHERE worker_id = %s
            ORDER BY completed_at DESC
            LIMIT %s
            """,
            (worker_id, limit)
        )

        rows = cur.fetchall()
        return [WorkCompletionLog.from_db_row(row) for row in rows]

    except PsycopgError as e:
        logger.error(f"Failed to get work_completion_logs for worker_id={worker_id}: {e}")
        return []
    finally:
        if conn:
            conn.close()
