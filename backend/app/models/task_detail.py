"""
작업 상세 모델 및 CRUD 함수
테이블: app_task_details
Sprint 2: 작업 시작/완료 + duration 자동 계산
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List

from psycopg2 import Error as PsycopgError

from .worker import get_db_connection


logger = logging.getLogger(__name__)


@dataclass
class TaskDetail:
    """
    작업 상세 모델

    Attributes:
        id: 작업 ID
        worker_id: 작업자 ID
        serial_number: 시리얼 번호
        qr_doc_id: QR 문서 ID
        task_category: Task 카테고리 (MM, EE, TM, PI, QI, SI)
        task_id: Task 식별자 (예: CABINET_ASSY)
        task_name: Task 이름 (예: 캐비넷 조립)
        started_at: 시작 시간
        completed_at: 완료 시간
        duration_minutes: 작업 소요 시간 (분 단위, completed_at - started_at)
        is_applicable: Task 적용 여부
        location_qr_verified: 위치 QR 검증 여부
        created_at: 생성 시간
        updated_at: 수정 시간
    """

    id: int
    worker_id: int
    serial_number: str
    qr_doc_id: str
    task_category: str
    task_id: str
    task_name: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_minutes: Optional[int]  # minutes
    is_applicable: bool
    location_qr_verified: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_db_row(row: Dict[str, Any]) -> "TaskDetail":
        """
        데이터베이스 행에서 TaskDetail 객체 생성

        Args:
            row: RealDictCursor로 조회한 dict 형태의 행

        Returns:
            TaskDetail 객체
        """
        return TaskDetail(
            id=row['id'],
            worker_id=row['worker_id'],
            serial_number=row['serial_number'],
            qr_doc_id=row['qr_doc_id'],
            task_category=row['task_category'],
            task_id=row['task_id'],
            task_name=row['task_name'],
            started_at=row.get('started_at'),
            completed_at=row.get('completed_at'),
            duration_minutes=row.get('duration_minutes'),
            is_applicable=row['is_applicable'],
            location_qr_verified=row['location_qr_verified'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )


def create_task(
    worker_id: int,
    serial_number: str,
    qr_doc_id: str,
    task_category: str,
    task_id: str,
    task_name: str,
    is_applicable: bool = True
) -> Optional[int]:
    """
    새 작업 생성 (Task 레코드 초기화)

    Args:
        worker_id: 작업자 ID
        serial_number: 시리얼 번호
        qr_doc_id: QR 문서 ID
        task_category: Task 카테고리 (MM, EE, TM, PI, QI, SI)
        task_id: Task 식별자
        task_name: Task 이름
        is_applicable: Task 적용 여부

    Returns:
        생성된 작업 ID, 실패 시 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO app_task_details (
                worker_id, serial_number, qr_doc_id, task_category,
                task_id, task_name, is_applicable
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (worker_id, serial_number, qr_doc_id, task_category,
             task_id, task_name, is_applicable)
        )

        task_detail_id = cur.fetchone()['id']
        conn.commit()

        logger.info(f"Task created: id={task_detail_id}, serial_number={serial_number}, task_id={task_id}")
        return task_detail_id

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Task creation failed: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_task_by_id(task_detail_id: int) -> Optional[TaskDetail]:
    """
    ID로 작업 조회

    Args:
        task_detail_id: 작업 ID

    Returns:
        TaskDetail 객체, 없으면 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM app_task_details WHERE id = %s",
            (task_detail_id,)
        )

        row = cur.fetchone()
        if row:
            return TaskDetail.from_db_row(row)
        return None

    except PsycopgError as e:
        logger.error(f"Failed to get task by id={task_detail_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_tasks_by_serial_number(
    serial_number: str,
    task_category: Optional[str] = None
) -> List[TaskDetail]:
    """
    시리얼 번호로 작업 목록 조회 (역할별 필터링 가능)

    Args:
        serial_number: 시리얼 번호
        task_category: Task 카테고리 (MM, EE, TM, PI, QI, SI), None이면 전체 조회

    Returns:
        TaskDetail 리스트
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if task_category:
            cur.execute(
                """
                SELECT * FROM app_task_details
                WHERE serial_number = %s AND task_category = %s
                ORDER BY id
                """,
                (serial_number, task_category)
            )
        else:
            cur.execute(
                """
                SELECT * FROM app_task_details
                WHERE serial_number = %s
                ORDER BY id
                """,
                (serial_number,)
            )

        rows = cur.fetchall()
        return [TaskDetail.from_db_row(row) for row in rows]

    except PsycopgError as e:
        logger.error(f"Failed to get tasks by serial_number={serial_number}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def start_task(task_detail_id: int, started_at: datetime) -> bool:
    """
    작업 시작 처리

    Args:
        task_detail_id: 작업 ID
        started_at: 시작 시간 (timezone-aware)

    Returns:
        성공 시 True, 실패 시 False
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "UPDATE app_task_details SET started_at = %s WHERE id = %s",
            (started_at, task_detail_id)
        )

        updated = cur.rowcount > 0
        conn.commit()

        if updated:
            logger.info(f"Task started: id={task_detail_id}, started_at={started_at}")
        return updated

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to start task: {e}")
        return False
    finally:
        if conn:
            conn.close()


def complete_task(task_detail_id: int, completed_at: datetime) -> bool:
    """
    작업 완료 처리 (duration_minutes 자동 계산)

    Args:
        task_detail_id: 작업 ID
        completed_at: 완료 시간 (timezone-aware)

    Returns:
        성공 시 True, 실패 시 False
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # duration_minutes 자동 계산: EXTRACT(EPOCH FROM (completed_at - started_at)) / 60
        cur.execute(
            """
            UPDATE app_task_details
            SET completed_at = %s,
                duration_minutes = (EXTRACT(EPOCH FROM (%s - started_at)) / 60)::INTEGER
            WHERE id = %s AND started_at IS NOT NULL
            """,
            (completed_at, completed_at, task_detail_id)
        )

        updated = cur.rowcount > 0
        conn.commit()

        if updated:
            logger.info(f"Task completed: id={task_detail_id}, completed_at={completed_at}")
        return updated

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to complete task: {e}")
        return False
    finally:
        if conn:
            conn.close()


def get_incomplete_tasks(serial_number: str, task_category: str) -> List[TaskDetail]:
    """
    미완료 작업 목록 조회 (completed_at IS NULL)

    Args:
        serial_number: 시리얼 번호
        task_category: Task 카테고리

    Returns:
        미완료 TaskDetail 리스트
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT * FROM app_task_details
            WHERE serial_number = %s
              AND task_category = %s
              AND completed_at IS NULL
              AND is_applicable = TRUE
            ORDER BY id
            """,
            (serial_number, task_category)
        )

        rows = cur.fetchall()
        return [TaskDetail.from_db_row(row) for row in rows]

    except PsycopgError as e:
        logger.error(f"Failed to get incomplete tasks: {e}")
        return []
    finally:
        if conn:
            conn.close()


def toggle_task_applicable(task_detail_id: int, is_applicable: bool) -> bool:
    """
    Task 적용 여부 토글

    Args:
        task_detail_id: 작업 ID
        is_applicable: 적용 여부

    Returns:
        성공 시 True, 실패 시 False
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "UPDATE app_task_details SET is_applicable = %s WHERE id = %s",
            (is_applicable, task_detail_id)
        )

        updated = cur.rowcount > 0
        conn.commit()

        if updated:
            logger.info(f"Task applicable toggled: id={task_detail_id}, is_applicable={is_applicable}")
        return updated

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to toggle task applicable: {e}")
        return False
    finally:
        if conn:
            conn.close()
