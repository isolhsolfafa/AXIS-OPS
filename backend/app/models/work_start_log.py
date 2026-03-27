"""
작업 시작 로그 모델 및 CRUD 함수
테이블: work_start_log
감사(audit) 목적: 작업 시작 이벤트를 별도 로그 테이블에 기록
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

from psycopg2 import Error as PsycopgError

from .worker import get_db_connection
from app.db_pool import put_conn


logger = logging.getLogger(__name__)


@dataclass
class WorkStartLog:
    """
    작업 시작 로그 모델

    Attributes:
        id: 로그 ID
        task_id: app_task_details의 작업 ID (FK)
        worker_id: 작업자 ID (FK)
        serial_number: 시리얼 번호
        qr_doc_id: QR 문서 ID
        task_category: Task 카테고리 (MM, EE, TM, PI, QI, SI)
        task_id_ref: Task 식별자 (예: CABINET_ASSY) — task_id 컬럼과 충돌 방지로 _ref 접미사
        task_name: Task 이름 (예: 캐비넷 조립)
        started_at: 시작 시간
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
    started_at: datetime
    created_at: datetime

    @staticmethod
    def from_db_row(row: Dict[str, Any]) -> "WorkStartLog":
        """
        데이터베이스 행에서 WorkStartLog 객체 생성

        Args:
            row: RealDictCursor로 조회한 dict 형태의 행

        Returns:
            WorkStartLog 객체
        """
        return WorkStartLog(
            id=row['id'],
            task_id=row['task_id'],
            worker_id=row['worker_id'],
            serial_number=row['serial_number'],
            qr_doc_id=row['qr_doc_id'],
            task_category=row['task_category'],
            task_id_ref=row['task_id_ref'],
            task_name=row['task_name'],
            started_at=row['started_at'],
            created_at=row['created_at']
        )


def create_work_start_log(
    task_id: int,
    worker_id: int,
    serial_number: str,
    qr_doc_id: str,
    task_category: str,
    task_id_ref: str,
    task_name: str,
    started_at: datetime
) -> Optional[int]:
    """
    작업 시작 로그 기록

    Args:
        task_id: app_task_details의 작업 ID
        worker_id: 작업자 ID
        serial_number: 시리얼 번호
        qr_doc_id: QR 문서 ID
        task_category: Task 카테고리
        task_id_ref: Task 식별자
        task_name: Task 이름
        started_at: 시작 시간 (timezone-aware)

    Returns:
        생성된 로그 ID, 실패 시 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO work_start_log (
                task_id, worker_id, serial_number, qr_doc_id,
                task_category, task_id_ref, task_name, started_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (task_id, worker_id, serial_number, qr_doc_id,
             task_category, task_id_ref, task_name, started_at)
        )

        log_id = cur.fetchone()['id']
        conn.commit()

        logger.info(
            f"WorkStartLog created: id={log_id}, task_id={task_id}, "
            f"worker_id={worker_id}, serial_number={serial_number}"
        )
        return log_id

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"WorkStartLog creation failed: {e}")
        return None
    finally:
        if conn:
            put_conn(conn)


def get_work_start_log_by_id(log_id: int) -> Optional[WorkStartLog]:
    """
    ID로 작업 시작 로그 조회

    Args:
        log_id: 로그 ID

    Returns:
        WorkStartLog 객체, 없으면 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM work_start_log WHERE id = %s",
            (log_id,)
        )

        row = cur.fetchone()
        if row:
            return WorkStartLog.from_db_row(row)
        return None

    except PsycopgError as e:
        logger.error(f"Failed to get work_start_log by id={log_id}: {e}")
        return None
    finally:
        if conn:
            put_conn(conn)


def get_work_start_logs_by_serial(
    serial_number: str,
    limit: int = 100
) -> List[WorkStartLog]:
    """
    시리얼 번호로 작업 시작 로그 목록 조회

    Args:
        serial_number: 시리얼 번호
        limit: 조회 제한 (기본 100개)

    Returns:
        WorkStartLog 리스트 (최신순)
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT * FROM work_start_log
            WHERE serial_number = %s
            ORDER BY started_at DESC
            LIMIT %s
            """,
            (serial_number, limit)
        )

        rows = cur.fetchall()
        return [WorkStartLog.from_db_row(row) for row in rows]

    except PsycopgError as e:
        logger.error(f"Failed to get work_start_logs for serial_number={serial_number}: {e}")
        return []
    finally:
        if conn:
            put_conn(conn)


def get_work_start_logs_by_worker(
    worker_id: int,
    limit: int = 100
) -> List[WorkStartLog]:
    """
    작업자별 작업 시작 로그 목록 조회

    Args:
        worker_id: 작업자 ID
        limit: 조회 제한 (기본 100개)

    Returns:
        WorkStartLog 리스트 (최신순)
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT * FROM work_start_log
            WHERE worker_id = %s
            ORDER BY started_at DESC
            LIMIT %s
            """,
            (worker_id, limit)
        )

        rows = cur.fetchall()
        return [WorkStartLog.from_db_row(row) for row in rows]

    except PsycopgError as e:
        logger.error(f"Failed to get work_start_logs for worker_id={worker_id}: {e}")
        return []
    finally:
        if conn:
            put_conn(conn)


def get_today_tags_by_worker(worker_id: int) -> list:
    """
    오늘 날짜 기준 해당 작업자의 태깅 QR 목록 (DISTINCT, 최신순)

    KST(Asia/Seoul) 기준 오늘 날짜의 태깅 이력을 qr_doc_id별 중복 제거 후 반환.

    Args:
        worker_id: 작업자 ID

    Returns:
        [{'qr_doc_id': str, 'serial_number': str, 'last_tagged_at': str (ISO 8601)}, ...]
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT DISTINCT ON (wsl.qr_doc_id)
                   wsl.qr_doc_id,
                   wsl.serial_number,
                   wsl.started_at AS last_tagged_at
            FROM work_start_log wsl
            WHERE wsl.worker_id = %s
              AND wsl.started_at >= (CURRENT_DATE AT TIME ZONE 'Asia/Seoul')
            ORDER BY wsl.qr_doc_id, wsl.started_at DESC
            """,
            (worker_id,)
        )

        rows = cur.fetchall()
        result = []
        for row in rows:
            last_tagged_at = row['last_tagged_at']
            result.append({
                'qr_doc_id': row['qr_doc_id'],
                'serial_number': row['serial_number'],
                'last_tagged_at': last_tagged_at.isoformat() if last_tagged_at else None,
            })
        return result

    except PsycopgError as e:
        logger.error(f"Failed to get today tags for worker_id={worker_id}: {e}")
        return []
    finally:
        if conn:
            put_conn(conn)
