"""
알림 로그 모델 및 CRUD 함수
테이블: app_alert_logs
Sprint 3: 공정 검증 + 알림 시스템
Sprint 5: read_at 필드 추가
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

from psycopg2 import Error as PsycopgError

from .worker import get_db_connection


logger = logging.getLogger(__name__)


@dataclass
class AlertLog:
    """
    알림 로그 모델

    Attributes:
        id: 알림 ID
        alert_type: 알림 타입 (PROCESS_READY, UNFINISHED_AT_CLOSING, DURATION_EXCEEDED, etc.)
        serial_number: 시리얼 번호
        qr_doc_id: QR 문서 ID
        triggered_by_worker_id: 알림 발생시킨 작업자 ID
        target_worker_id: 알림 대상 작업자 ID (NULL이면 target_role 기반)
        target_role: 알림 대상 역할 (MM, EE, PI, QI, SI)
        message: 알림 메시지
        is_read: 읽음 여부
        read_at: 읽은 시각
        created_at: 생성 시간
        updated_at: 수정 시간
    """

    id: int
    alert_type: str
    serial_number: Optional[str]
    qr_doc_id: Optional[str]
    triggered_by_worker_id: Optional[int]
    target_worker_id: Optional[int]
    target_role: Optional[str]
    message: str
    is_read: bool
    created_at: datetime
    updated_at: datetime
    read_at: Optional[datetime] = None

    @staticmethod
    def from_db_row(row: Dict[str, Any]) -> "AlertLog":
        """
        데이터베이스 행에서 AlertLog 객체 생성

        Args:
            row: RealDictCursor로 조회한 dict 형태의 행

        Returns:
            AlertLog 객체
        """
        return AlertLog(
            id=row['id'],
            alert_type=row['alert_type'],
            serial_number=row.get('serial_number'),
            qr_doc_id=row.get('qr_doc_id'),
            triggered_by_worker_id=row.get('triggered_by_worker_id'),
            target_worker_id=row.get('target_worker_id'),
            target_role=row.get('target_role'),
            message=row['message'],
            is_read=row['is_read'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            read_at=row.get('read_at')
        )


def create_alert(
    alert_type: str,
    message: str,
    serial_number: Optional[str] = None,
    qr_doc_id: Optional[str] = None,
    triggered_by_worker_id: Optional[int] = None,
    target_worker_id: Optional[int] = None,
    target_role: Optional[str] = None
) -> Optional[int]:
    """
    새 알림 생성

    Args:
        alert_type: 알림 타입 (PROCESS_READY, UNFINISHED_AT_CLOSING, DURATION_EXCEEDED, etc.)
        message: 알림 메시지
        serial_number: 시리얼 번호
        qr_doc_id: QR 문서 ID
        triggered_by_worker_id: 알림 발생시킨 작업자 ID
        target_worker_id: 알림 대상 작업자 ID (지정된 경우)
        target_role: 알림 대상 역할 (target_worker_id가 없을 때 역할 기반 알림)

    Returns:
        생성된 알림 ID, 실패 시 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO app_alert_logs (
                alert_type, serial_number, qr_doc_id,
                triggered_by_worker_id, target_worker_id, target_role, message
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (alert_type, serial_number, qr_doc_id,
             triggered_by_worker_id, target_worker_id, target_role, message)
        )

        alert_id = cur.fetchone()['id']
        conn.commit()

        logger.info(f"Alert created: id={alert_id}, type={alert_type}, target_worker={target_worker_id}, target_role={target_role}")
        return alert_id

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Alert creation failed: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_alerts_by_worker(
    worker_id: int,
    unread_only: bool = False,
    limit: int = 50
) -> List[AlertLog]:
    """
    작업자별 알림 목록 조회

    Args:
        worker_id: 작업자 ID
        unread_only: True면 읽지 않은 알림만 조회
        limit: 조회 제한 (기본 50개)

    Returns:
        AlertLog 리스트 (최신순)
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if unread_only:
            cur.execute(
                """
                SELECT * FROM app_alert_logs
                WHERE target_worker_id = %s AND is_read = FALSE
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (worker_id, limit)
            )
        else:
            cur.execute(
                """
                SELECT * FROM app_alert_logs
                WHERE target_worker_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (worker_id, limit)
            )

        rows = cur.fetchall()
        return [AlertLog.from_db_row(row) for row in rows]

    except PsycopgError as e:
        logger.error(f"Failed to get alerts for worker_id={worker_id}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_alert_by_id(alert_id: int) -> Optional[AlertLog]:
    """
    ID로 알림 조회

    Args:
        alert_id: 알림 ID

    Returns:
        AlertLog 객체, 없으면 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM app_alert_logs WHERE id = %s",
            (alert_id,)
        )

        row = cur.fetchone()
        if row:
            return AlertLog.from_db_row(row)
        return None

    except PsycopgError as e:
        logger.error(f"Failed to get alert by id={alert_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()


def mark_alert_read(alert_id: int) -> bool:
    """
    알림을 읽음 상태로 변경

    Args:
        alert_id: 알림 ID

    Returns:
        성공 시 True, 실패 시 False
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE app_alert_logs
            SET is_read = TRUE, read_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (alert_id,)
        )

        updated = cur.rowcount > 0
        conn.commit()

        if updated:
            logger.info(f"Alert marked as read: id={alert_id}")
        return updated

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to mark alert as read: {e}")
        return False
    finally:
        if conn:
            conn.close()


def get_unread_count(worker_id: int) -> int:
    """
    작업자의 읽지 않은 알림 개수 조회

    Args:
        worker_id: 작업자 ID

    Returns:
        읽지 않은 알림 개수
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT COUNT(*) as count
            FROM app_alert_logs
            WHERE target_worker_id = %s AND is_read = FALSE
            """,
            (worker_id,)
        )

        result = cur.fetchone()
        return result['count'] if result else 0

    except PsycopgError as e:
        logger.error(f"Failed to get unread count for worker_id={worker_id}: {e}")
        return 0
    finally:
        if conn:
            conn.close()
