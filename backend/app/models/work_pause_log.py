"""
작업 일시정지 로그 모델 및 CRUD 함수
테이블: work_pause_log
Sprint 9: 일시정지/재개 기능
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List

from psycopg2 import Error as PsycopgError

from .worker import get_db_connection


logger = logging.getLogger(__name__)


@dataclass
class WorkPauseLog:
    """
    작업 일시정지 로그 모델

    Attributes:
        id: 로그 ID
        task_detail_id: 작업 ID (FK → app_task_details.id)
        worker_id: 작업자 ID (FK → workers.id)
        paused_at: 일시정지 시각
        resumed_at: 재개 시각 (NULL이면 아직 일시정지 중)
        pause_type: 일시정지 유형 ('manual' | 'break_morning' | 'lunch' | 'break_afternoon' | 'dinner')
        pause_duration_minutes: 일시정지 지속 시간 (분), 재개 후 계산
        created_at: 생성 시각
    """

    id: int
    task_detail_id: int
    worker_id: int
    paused_at: datetime
    resumed_at: Optional[datetime]
    pause_type: str
    pause_duration_minutes: Optional[int]
    created_at: datetime

    @staticmethod
    def from_db_row(row: Dict[str, Any]) -> "WorkPauseLog":
        """
        데이터베이스 행에서 WorkPauseLog 객체 생성

        Args:
            row: RealDictCursor로 조회한 dict 형태의 행

        Returns:
            WorkPauseLog 객체
        """
        return WorkPauseLog(
            id=row['id'],
            task_detail_id=row['task_detail_id'],
            worker_id=row['worker_id'],
            paused_at=row['paused_at'],
            resumed_at=row.get('resumed_at'),
            pause_type=row['pause_type'],
            pause_duration_minutes=row.get('pause_duration_minutes'),
            created_at=row['created_at'],
        )

    def to_dict(self) -> Dict[str, Any]:
        """API 응답용 dict 변환"""
        return {
            'id': self.id,
            'task_detail_id': self.task_detail_id,
            'worker_id': self.worker_id,
            'paused_at': self.paused_at.isoformat() if self.paused_at else None,
            'resumed_at': self.resumed_at.isoformat() if self.resumed_at else None,
            'pause_type': self.pause_type,
            'pause_duration_minutes': self.pause_duration_minutes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


def create_pause(
    task_detail_id: int,
    worker_id: int,
    pause_type: str = 'manual'
) -> Optional[WorkPauseLog]:
    """
    일시정지 로그 생성

    Args:
        task_detail_id: 작업 ID
        worker_id: 작업자 ID
        pause_type: 일시정지 유형 ('manual' | 'break_morning' | 'lunch' | 'break_afternoon' | 'dinner')

    Returns:
        생성된 WorkPauseLog 객체, 실패 시 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO work_pause_log (task_detail_id, worker_id, pause_type)
            VALUES (%s, %s, %s)
            RETURNING *
            """,
            (task_detail_id, worker_id, pause_type)
        )

        row = cur.fetchone()
        conn.commit()

        if row:
            logger.info(
                f"Pause log created: task_detail_id={task_detail_id}, "
                f"worker_id={worker_id}, pause_type={pause_type}"
            )
            return WorkPauseLog.from_db_row(row)
        return None

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to create pause log: {e}")
        return None
    finally:
        if conn:
            conn.close()


def resume_pause(pause_id: int, resumed_at: datetime) -> Optional[WorkPauseLog]:
    """
    일시정지 재개 처리 (pause_duration_minutes 계산 후 업데이트)

    Args:
        pause_id: work_pause_log.id
        resumed_at: 재개 시각 (timezone-aware)

    Returns:
        업데이트된 WorkPauseLog 객체, 실패 시 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 기존 로그 조회 (paused_at 확인용)
        cur.execute(
            "SELECT * FROM work_pause_log WHERE id = %s",
            (pause_id,)
        )
        row = cur.fetchone()
        if not row:
            logger.warning(f"Pause log not found: id={pause_id}")
            return None

        # duration 계산 (분 단위, 소수점 버림)
        paused_at = row['paused_at']
        duration_minutes = int((resumed_at - paused_at).total_seconds() / 60)

        # 업데이트
        cur.execute(
            """
            UPDATE work_pause_log
            SET resumed_at = %s,
                pause_duration_minutes = %s
            WHERE id = %s
            RETURNING *
            """,
            (resumed_at, duration_minutes, pause_id)
        )

        updated_row = cur.fetchone()
        conn.commit()

        if updated_row:
            logger.info(
                f"Pause resumed: id={pause_id}, "
                f"duration={duration_minutes}m, resumed_at={resumed_at}"
            )
            return WorkPauseLog.from_db_row(updated_row)
        return None

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to resume pause log id={pause_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_active_pause(task_detail_id: int) -> Optional[WorkPauseLog]:
    """
    현재 활성 일시정지 조회 (resumed_at IS NULL인 최신 레코드)

    Args:
        task_detail_id: 작업 ID

    Returns:
        활성 WorkPauseLog 객체, 없으면 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT * FROM work_pause_log
            WHERE task_detail_id = %s
              AND resumed_at IS NULL
            ORDER BY paused_at DESC
            LIMIT 1
            """,
            (task_detail_id,)
        )

        row = cur.fetchone()
        if row:
            return WorkPauseLog.from_db_row(row)
        return None

    except PsycopgError as e:
        logger.error(f"Failed to get active pause for task_detail_id={task_detail_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_pauses_by_task(task_detail_id: int) -> List[WorkPauseLog]:
    """
    작업의 전체 일시정지 이력 조회

    Args:
        task_detail_id: 작업 ID

    Returns:
        WorkPauseLog 리스트 (paused_at 오름차순)
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT * FROM work_pause_log
            WHERE task_detail_id = %s
            ORDER BY paused_at ASC
            """,
            (task_detail_id,)
        )

        rows = cur.fetchall()
        return [WorkPauseLog.from_db_row(row) for row in rows]

    except PsycopgError as e:
        logger.error(f"Failed to get pauses for task_detail_id={task_detail_id}: {e}")
        return []
    finally:
        if conn:
            conn.close()
