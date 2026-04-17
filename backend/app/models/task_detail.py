"""
작업 상세 모델 및 CRUD 함수
테이블: app_task_details
Sprint 2: 작업 시작/완료 + duration 자동 계산
Sprint 6 Phase C: elapsed_minutes, worker_count, force_closed, closed_by, close_reason 필드 추가
Sprint 9: is_paused, total_pause_minutes 필드 추가 + set_paused 함수
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List

from psycopg2 import Error as PsycopgError

from .worker import get_db_connection
from app.db_pool import put_conn


logger = logging.getLogger(__name__)


@dataclass
class TaskDetail:
    """
    작업 상세 모델

    Attributes:
        id: 작업 ID
        worker_id: 작업자 ID (Seed 시점엔 NULL, 작업 시작 시 설정)
        serial_number: 시리얼 번호
        qr_doc_id: QR 문서 ID
        task_category: Task 카테고리 (MECH, ELEC, TM, PI, QI, SI)
        task_id: Task 식별자 (예: CABINET_ASSY)
        task_name: Task 이름 (예: 캐비넷 조립)
        started_at: 시작 시간 (멀티 작업자 시 최초 시작 시간)
        completed_at: 완료 시간 (마지막 작업자 완료 시간)
        duration_minutes: man-hour 합계 (작업자별 duration 합산)
        elapsed_minutes: 실경과시간 (최초 started_at ~ 마지막 completed_at)
        worker_count: 투입된 작업자 수
        force_closed: 강제 종료 여부
        closed_by: 강제 종료한 관리자 ID
        close_reason: 강제 종료 사유
        is_applicable: Task 적용 여부
        location_qr_verified: 위치 QR 검증 여부
        created_at: 생성 시간
        updated_at: 수정 시간
    """

    id: int
    worker_id: Optional[int]  # Seed 시점엔 NULL 가능, 작업 시작 시 설정
    serial_number: str
    qr_doc_id: str
    task_category: str
    task_id: str
    task_name: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_minutes: Optional[int]  # man-hour 합계 (분)
    is_applicable: bool
    location_qr_verified: bool
    created_at: datetime
    updated_at: datetime
    # Sprint 6 Phase C: 멀티 작업자 + 강제 종료 필드
    elapsed_minutes: Optional[int] = None    # 실경과시간 (분)
    worker_count: int = 1                    # 투입 인원 수
    force_closed: bool = False               # 강제 종료 여부
    closed_by: Optional[int] = None         # 강제 종료한 관리자 ID
    close_reason: Optional[str] = None      # 강제 종료 사유
    # Sprint 9: 일시정지 필드
    is_paused: bool = False                  # 현재 일시정지 여부
    total_pause_minutes: int = 0             # 누적 일시정지 시간 (분)
    # Sprint 27: 단일 액션 Task 지원
    task_type: str = 'NORMAL'  # 'NORMAL' 또는 'SINGLE_ACTION'

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
            updated_at=row['updated_at'],
            elapsed_minutes=row.get('elapsed_minutes'),
            worker_count=row.get('worker_count') or 1,
            force_closed=row.get('force_closed') or False,
            closed_by=row.get('closed_by'),
            close_reason=row.get('close_reason'),
            is_paused=row.get('is_paused') or False,
            total_pause_minutes=row.get('total_pause_minutes') or 0,
            task_type=row.get('task_type') or 'NORMAL',
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
        task_category: Task 카테고리 (MECH, ELEC, TM, PI, QI, SI)
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
            put_conn(conn)


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
            put_conn(conn)


def get_task_by_serial_and_id(serial_number: str, task_category: str, task_id: str) -> Optional[TaskDetail]:
    """
    serial_number + task_category + task_id로 단일 task 조회

    Args:
        serial_number: 시리얼 번호
        task_category: Task 카테고리
        task_id: Task 식별자

    Returns:
        TaskDetail 객체, 없으면 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM app_task_details WHERE serial_number = %s AND task_category = %s AND task_id = %s",
            (serial_number, task_category, task_id)
        )
        row = cur.fetchone()
        if row:
            return TaskDetail.from_db_row(row)
        return None
    except PsycopgError as e:
        logger.error(f"Failed to get task by serial_and_id: {e}")
        return None
    finally:
        if conn:
            put_conn(conn)


def get_task_by_qr_category_id(
    qr_doc_id: str,
    task_category: str,
    task_id: str,
) -> Optional['TaskDetail']:
    """
    qr_doc_id + task_category + task_id 조합으로 단일 task 조회.
    Sprint 54: 테스트 헬퍼 및 API에서 qr 기반 task 특정 시 사용.

    Args:
        qr_doc_id: QR 문서 ID
        task_category: Task 카테고리 (MECH, ELEC, TMS, ...)
        task_id: Task 식별자 (PRESSURE_TEST, TANK_DOCKING, ...)

    Returns:
        TaskDetail 객체, 없으면 None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT * FROM app_task_details
            WHERE qr_doc_id = %s AND task_category = %s AND task_id = %s
            ORDER BY id
            LIMIT 1
            """,
            (qr_doc_id, task_category, task_id),
        )
        row = cur.fetchone()
        if row:
            return TaskDetail.from_db_row(row)
        return None
    except PsycopgError as e:
        logger.error(
            f"Failed to get task by qr_doc_id={qr_doc_id}, "
            f"task_category={task_category}, task_id={task_id}: {e}"
        )
        return None
    finally:
        if conn:
            put_conn(conn)


def get_tasks_by_serial_number(
    serial_number: str,
    task_category: Optional[str] = None
) -> List[TaskDetail]:
    """
    시리얼 번호로 작업 목록 조회 (역할별 필터링 가능)

    Args:
        serial_number: 시리얼 번호
        task_category: Task 카테고리 (MECH, ELEC, TM, PI, QI, SI), None이면 전체 조회

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
                WHERE serial_number = %s AND task_category = %s AND is_applicable = TRUE
                ORDER BY id
                """,
                (serial_number, task_category)
            )
        else:
            cur.execute(
                """
                SELECT * FROM app_task_details
                WHERE serial_number = %s AND is_applicable = TRUE
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
            put_conn(conn)


def get_tasks_by_qr_doc_id(
    qr_doc_id: str,
    task_category: Optional[str] = None
) -> List[TaskDetail]:
    """
    QR 문서 ID로 작업 목록 조회.
    Sprint 31A: DUAL L/R 분리 — 스캔한 QR에 해당하는 태스크만 반환.

    PRODUCT QR 스캔 → 해당 qr_doc_id의 MECH/ELEC/PI/QI/SI (+SINGLE TMS)
    TANK QR L 스캔 → 해당 qr_doc_id의 TMS L만
    TANK QR R 스캔 → 해당 qr_doc_id의 TMS R만

    Args:
        qr_doc_id: QR 문서 ID (DOC_xxx 또는 DOC_xxx-L/R)
        task_category: Task 카테고리, None이면 전체

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
                WHERE qr_doc_id = %s AND task_category = %s AND is_applicable = TRUE
                ORDER BY id
                """,
                (qr_doc_id, task_category)
            )
        else:
            cur.execute(
                """
                SELECT * FROM app_task_details
                WHERE qr_doc_id = %s AND is_applicable = TRUE
                ORDER BY id
                """,
                (qr_doc_id,)
            )

        rows = cur.fetchall()
        return [TaskDetail.from_db_row(row) for row in rows]

    except PsycopgError as e:
        logger.error(f"Failed to get tasks by qr_doc_id={qr_doc_id}: {e}")
        return []
    finally:
        if conn:
            put_conn(conn)


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
            put_conn(conn)


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
            put_conn(conn)


def complete_single_action(task_detail_id: int, completed_at: datetime, worker_id: int) -> bool:
    """
    단일 액션 Task 완료 처리 (started_at 없이 바로 완료).

    SINGLE_ACTION Task는 시작 단계 없이 "완료 체크"만 수행.
    started_at = completed_at (동시), duration_minutes = 0으로 설정.

    Args:
        task_detail_id: 작업 ID
        completed_at: 완료 시간 (timezone-aware)
        worker_id: 완료 처리한 작업자 ID

    Returns:
        성공 시 True, 실패 시 False
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE app_task_details
            SET started_at = %s,
                completed_at = %s,
                duration_minutes = 0,
                worker_id = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
              AND task_type = 'SINGLE_ACTION'
              AND completed_at IS NULL
            """,
            (completed_at, completed_at, worker_id, task_detail_id)
        )

        updated = cur.rowcount > 0
        conn.commit()

        if updated:
            logger.info(f"Single action completed: id={task_detail_id}, worker_id={worker_id}")
        return updated

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to complete single action: {e}")
        return False
    finally:
        if conn:
            put_conn(conn)


def get_incomplete_tasks(serial_number: str, task_category: str, qr_doc_id: str = None) -> List[TaskDetail]:
    """
    미완료 작업 목록 조회 (completed_at IS NULL)
    qr_doc_id 지정 시 해당 QR 범위만 조회 (DUAL L/R 분리).

    Args:
        serial_number: 시리얼 번호
        task_category: Task 카테고리
        qr_doc_id: QR 문서 ID (옵션 — DUAL L/R 분리 판정용)

    Returns:
        미완료 TaskDetail 리스트
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if qr_doc_id:
            cur.execute(
                """
                SELECT * FROM app_task_details
                WHERE serial_number = %s
                  AND task_category = %s
                  AND qr_doc_id = %s
                  AND completed_at IS NULL
                  AND is_applicable = TRUE
                ORDER BY id
                """,
                (serial_number, task_category, qr_doc_id)
            )
        else:
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
            put_conn(conn)


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
            put_conn(conn)


def reactivate_task(task_detail_id: int) -> bool:
    """
    Sprint 41: 완료된 task를 재활성화.

    completed_at, started_at, worker_id, duration_minutes, elapsed_minutes,
    worker_count 모두 NULL로 초기화.

    started_at도 초기화하는 이유: is_first_worker 판단이 started_at IS NULL
    기준이므로, 재활성화 후 새 worker가 시작하면 정상적으로 "최초 시작자"로
    인식되어야 함.

    work_start_log / work_completion_log는 절대 삭제하지 않음 (이력 보존).

    Args:
        task_detail_id: 재활성화할 app_task_details.id

    Returns:
        성공 시 True (완료된 task가 존재하여 업데이트됨), 실패 시 False
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE app_task_details
            SET completed_at = NULL,
                started_at = NULL,
                worker_id = NULL,
                duration_minutes = NULL,
                elapsed_minutes = NULL,
                worker_count = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND completed_at IS NOT NULL
            RETURNING id
        """, (task_detail_id,))
        result = cur.fetchone()
        conn.commit()
        if result:
            logger.info(f"Task reactivated: id={task_detail_id}")
        return result is not None
    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to reactivate task id={task_detail_id}: {e}")
        return False
    finally:
        if conn:
            put_conn(conn)


def get_orphan_relay_tasks(serial_number: str, task_category: str) -> List[Dict]:
    """
    릴레이 미완료 task 조회.
    - completed_at IS NULL (task 미완료)
    - work_completion_log에 1건 이상 존재 (누군가 작업은 했음)
    - is_applicable = TRUE

    Sprint 41-B: FINAL task 완료 시 자동 마감 대상 조회에 사용.

    Args:
        serial_number: 시리얼 번호
        task_category: Task 카테고리 (MECH, ELEC, TMS 등)

    Returns:
        [{ task_detail_id, task_id, task_name, started_at,
           last_completion_at, worker_count }]
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT atd.id AS task_detail_id,
                   atd.task_id,
                   atd.task_name,
                   atd.started_at,
                   MAX(wcl.completed_at) AS last_completion_at,
                   COUNT(DISTINCT wcl.worker_id) AS worker_count
            FROM app_task_details atd
            JOIN work_completion_log wcl ON wcl.task_id = atd.id
            WHERE atd.serial_number = %s
              AND atd.task_category = %s
              AND atd.completed_at IS NULL
              AND atd.is_applicable = TRUE
            GROUP BY atd.id, atd.task_id, atd.task_name, atd.started_at
        """, (serial_number, task_category))
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        put_conn(conn)


def auto_close_relay_task(task_detail_id: int, last_completion_at, worker_count: int) -> bool:
    """
    릴레이 미완료 task 자동 마감.
    마지막 work_completion_log 기준으로 completed_at 설정.

    Sprint 41-B: FINAL task 완료 시 열린 릴레이 task를 자동 마감.
    work_start_log / work_completion_log는 절대 삭제하지 않음 (이력 보존).

    Args:
        task_detail_id: app_task_details.id
        last_completion_at: 마지막 completion_log의 completed_at
        worker_count: 참여 작업자 수

    Returns:
        True if 업데이트 성공
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE app_task_details
            SET completed_at = %s,
                duration_minutes = EXTRACT(EPOCH FROM (%s - started_at)) / 60,
                elapsed_minutes = EXTRACT(EPOCH FROM (%s - started_at)) / 60,
                worker_count = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
              AND completed_at IS NULL
            RETURNING id
        """, (last_completion_at, last_completion_at, last_completion_at,
              worker_count, task_detail_id))
        result = cur.fetchone()
        conn.commit()
        if result:
            logger.info(f"auto_close_relay_task: task_detail_id={task_detail_id} closed")
        return result is not None
    except Exception as e:
        conn.rollback()
        logger.error(f"auto_close_relay_task failed: task_id={task_detail_id}, error={e}")
        return False
    finally:
        put_conn(conn)


def set_paused(
    task_detail_id: int,
    is_paused: bool,
    total_pause_minutes: Optional[int] = None
) -> bool:
    """
    작업 일시정지 상태 업데이트
    Sprint 9: 일시정지/재개 처리

    Args:
        task_detail_id: 작업 ID
        is_paused: 일시정지 여부
        total_pause_minutes: 누적 일시정지 시간 (None이면 변경하지 않음)

    Returns:
        성공 시 True, 실패 시 False
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if total_pause_minutes is not None:
            cur.execute(
                """
                UPDATE app_task_details
                SET is_paused = %s,
                    total_pause_minutes = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (is_paused, total_pause_minutes, task_detail_id)
            )
        else:
            cur.execute(
                """
                UPDATE app_task_details
                SET is_paused = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (is_paused, task_detail_id)
            )

        updated = cur.rowcount > 0
        conn.commit()

        if updated:
            logger.info(
                f"Task pause state updated: id={task_detail_id}, "
                f"is_paused={is_paused}, total_pause_minutes={total_pause_minutes}"
            )
        return updated

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to set task paused state: {e}")
        return False
    finally:
        if conn:
            put_conn(conn)


def get_not_started_tasks(serial_number: str, task_category: str) -> list:
    """미시작 task 목록 (started_at IS NULL, completed_at IS NULL, applicable, not force_closed)"""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, task_id, task_name
            FROM app_task_details
            WHERE serial_number = %s
              AND task_category = %s
              AND started_at IS NULL
              AND completed_at IS NULL
              AND is_applicable = TRUE
              AND force_closed = FALSE
            """,
            (serial_number, task_category)
        )
        return cur.fetchall()
    finally:
        put_conn(conn)
