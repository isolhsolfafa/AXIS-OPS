"""
오프라인 동기화 큐 모델 및 CRUD 함수
테이블: offline_sync_queue
오프라인 상태에서 발생한 작업을 서버에 동기화할 때 사용
"""

import logging
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

from psycopg2 import Error as PsycopgError
import psycopg2.extras

from .worker import get_db_connection


logger = logging.getLogger(__name__)


@dataclass
class OfflineSyncQueue:
    """
    오프라인 동기화 큐 모델

    Attributes:
        id: 큐 항목 ID
        worker_id: 작업자 ID (FK)
        operation: 작업 유형 (INSERT, UPDATE, DELETE)
        table_name: 대상 테이블 이름
        record_id: 대상 레코드 ID
        data: 동기화 데이터 (JSONB)
        synced: 동기화 완료 여부
        synced_at: 동기화 완료 시각
        created_at: 큐 항목 생성 시각
    """

    id: int
    worker_id: int
    operation: str
    table_name: str
    record_id: Optional[str]
    data: Optional[Dict[str, Any]]
    synced: bool
    synced_at: Optional[datetime]
    created_at: datetime

    @staticmethod
    def from_db_row(row: Dict[str, Any]) -> "OfflineSyncQueue":
        """
        데이터베이스 행에서 OfflineSyncQueue 객체 생성

        Args:
            row: RealDictCursor로 조회한 dict 형태의 행

        Returns:
            OfflineSyncQueue 객체
        """
        # psycopg2는 JSONB를 자동으로 dict로 파싱함
        data = row.get('data')
        if isinstance(data, str):
            data = json.loads(data)

        return OfflineSyncQueue(
            id=row['id'],
            worker_id=row['worker_id'],
            operation=row['operation'],
            table_name=row['table_name'],
            record_id=row.get('record_id'),
            data=data,
            synced=row['synced'],
            synced_at=row.get('synced_at'),
            created_at=row['created_at']
        )


def create_sync_item(
    worker_id: int,
    operation: str,
    table_name: str,
    record_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None
) -> Optional[int]:
    """
    오프라인 동기화 큐 항목 생성

    Args:
        worker_id: 작업자 ID
        operation: 작업 유형 ('INSERT', 'UPDATE', 'DELETE')
        table_name: 대상 테이블 이름
        record_id: 대상 레코드 ID (선택)
        data: 동기화 데이터 dict (선택)

    Returns:
        생성된 큐 항목 ID, 실패 시 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # data dict를 JSON 문자열로 직렬화 (psycopg2.extras.Json 사용)
        json_data = psycopg2.extras.Json(data) if data is not None else None

        cur.execute(
            """
            INSERT INTO offline_sync_queue (worker_id, operation, table_name, record_id, data)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (worker_id, operation, table_name, record_id, json_data)
        )

        item_id = cur.fetchone()['id']
        conn.commit()

        logger.info(
            f"SyncQueue item created: id={item_id}, worker_id={worker_id}, "
            f"operation={operation}, table_name={table_name}"
        )
        return item_id

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"SyncQueue item creation failed: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_sync_item_by_id(item_id: int) -> Optional[OfflineSyncQueue]:
    """
    ID로 동기화 큐 항목 조회

    Args:
        item_id: 큐 항목 ID

    Returns:
        OfflineSyncQueue 객체, 없으면 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM offline_sync_queue WHERE id = %s",
            (item_id,)
        )

        row = cur.fetchone()
        if row:
            return OfflineSyncQueue.from_db_row(row)
        return None

    except PsycopgError as e:
        logger.error(f"Failed to get sync_item by id={item_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_pending_sync_items(worker_id: int) -> List[OfflineSyncQueue]:
    """
    작업자의 미동기화 항목 목록 조회 (synced=FALSE)

    Args:
        worker_id: 작업자 ID

    Returns:
        OfflineSyncQueue 리스트 (생성순)
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT * FROM offline_sync_queue
            WHERE worker_id = %s AND synced = FALSE
            ORDER BY created_at ASC
            """,
            (worker_id,)
        )

        rows = cur.fetchall()
        return [OfflineSyncQueue.from_db_row(row) for row in rows]

    except PsycopgError as e:
        logger.error(f"Failed to get pending sync items for worker_id={worker_id}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def mark_sync_item_done(item_id: int) -> bool:
    """
    동기화 큐 항목을 완료 처리

    Args:
        item_id: 큐 항목 ID

    Returns:
        성공 시 True, 실패 시 False
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE offline_sync_queue
            SET synced = TRUE, synced_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (item_id,)
        )

        updated = cur.rowcount > 0
        conn.commit()

        if updated:
            logger.info(f"SyncQueue item marked as done: id={item_id}")
        return updated

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to mark sync item as done: {e}")
        return False
    finally:
        if conn:
            conn.close()
