"""
위치 기록 모델 및 CRUD 함수
테이블: location_history
Sprint 5: from_db_row 구현 + CRUD 함수 추가
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

from psycopg2 import Error as PsycopgError

from .worker import get_db_connection


logger = logging.getLogger(__name__)


@dataclass
class LocationHistory:
    """
    위치 기록 모델

    Attributes:
        id: 기록 ID
        worker_id: 작업자 ID
        latitude: 위도
        longitude: 경도
        recorded_at: 기록 시간
        created_at: 생성 시간
    """

    id: int
    worker_id: int
    latitude: float
    longitude: float
    recorded_at: datetime
    created_at: datetime

    @staticmethod
    def from_db_row(row: Dict[str, Any]) -> "LocationHistory":
        """
        데이터베이스 행에서 LocationHistory 객체 생성

        Args:
            row: RealDictCursor로 조회한 dict 형태의 행

        Returns:
            LocationHistory 객체
        """
        return LocationHistory(
            id=row['id'],
            worker_id=row['worker_id'],
            latitude=float(row['latitude']),
            longitude=float(row['longitude']),
            recorded_at=row['recorded_at'],
            created_at=row['created_at']
        )


def create_location_record(
    worker_id: int,
    latitude: float,
    longitude: float,
    recorded_at: datetime
) -> Optional[int]:
    """
    위치 기록 생성

    Args:
        worker_id: 작업자 ID
        latitude: 위도 (소수점 8자리)
        longitude: 경도 (소수점 8자리)
        recorded_at: 기록 시간 (timezone-aware)

    Returns:
        생성된 기록 ID, 실패 시 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO location_history (worker_id, latitude, longitude, recorded_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (worker_id, latitude, longitude, recorded_at)
        )

        record_id = cur.fetchone()['id']
        conn.commit()

        logger.info(f"Location recorded: id={record_id}, worker_id={worker_id}")
        return record_id

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Location record creation failed: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_location_by_id(record_id: int) -> Optional[LocationHistory]:
    """
    ID로 위치 기록 조회

    Args:
        record_id: 기록 ID

    Returns:
        LocationHistory 객체, 없으면 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM location_history WHERE id = %s",
            (record_id,)
        )

        row = cur.fetchone()
        if row:
            return LocationHistory.from_db_row(row)
        return None

    except PsycopgError as e:
        logger.error(f"Failed to get location by id={record_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_locations_by_worker(
    worker_id: int,
    limit: int = 100
) -> List[LocationHistory]:
    """
    작업자별 위치 기록 목록 조회 (최신순)

    Args:
        worker_id: 작업자 ID
        limit: 조회 제한 (기본 100개)

    Returns:
        LocationHistory 리스트
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT * FROM location_history
            WHERE worker_id = %s
            ORDER BY recorded_at DESC
            LIMIT %s
            """,
            (worker_id, limit)
        )

        rows = cur.fetchall()
        return [LocationHistory.from_db_row(row) for row in rows]

    except PsycopgError as e:
        logger.error(f"Failed to get locations for worker_id={worker_id}: {e}")
        return []
    finally:
        if conn:
            conn.close()
