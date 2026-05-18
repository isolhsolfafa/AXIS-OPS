"""
출하 완료 처리 — SI 공정 task 2개(SI_FINISHING + SI_SHIPMENT) 완료 (Sprint 68)

출하 시점엔 작업자가 QR 태깅으로 SI task 완료가 어려움 → admin/manager 가
VIEW/OPS 화면에서 대행. 출하 완료 = 한 S/N 의 SI task 2개 모두 완료.

설계: AGENT_TEAM_LAUNCH.md § Sprint 68 (영역 10 + 11 = 단일 기준)
- SI_FINISHING(FINAL, NORMAL) / SI_SHIPMENT(SINGLE_ACTION) 타입별 완료 경로 분기
- force_closed=FALSE 유지 (정상 종료) — audit 은 close_reason='SHIP_COMPLETE' + closed_by
- completed_at 검증은 force-close 패턴 차용 (write 시맨틱 force_closed 는 차용 안 함)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional

from app.config import Config
from app.models.task_detail import (
    get_tasks_by_serial_number,
    complete_task,
    complete_single_action,
)
from app.models.completion_status import update_process_completion
from app.models.worker import get_db_connection
from app.db_pool import put_conn

logger = logging.getLogger(__name__)

SI_FINISHING = 'SI_FINISHING'
SI_SHIPMENT = 'SI_SHIPMENT'


def _parse_completed_at(raw: Optional[str]) -> Tuple[Optional[datetime], Optional[Tuple[Dict, int]]]:
    """
    completed_at 파싱 + 미래 시각 차단 (force-close 검증 패턴 차용 — v2.9.6).

    Returns:
        (datetime, None) 성공 / (None, (error_dict, status)) 실패
    """
    now_kst = datetime.now(Config.KST)
    if not raw:
        return now_kst, None
    try:
        dt = datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        return None, ({'error': 'INVALID_COMPLETED_AT',
                       'message': 'completed_at 형식이 올바르지 않습니다.'}, 400)
    # naive → KST aware 정규화
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=Config.KST)
    # 미래 시각 차단 (60s clock skew 허용)
    if dt > now_kst + timedelta(seconds=60):
        return None, ({'error': 'INVALID_COMPLETED_AT_FUTURE',
                       'message': '완료 시각이 미래일 수 없습니다.'}, 400)
    return dt, None


def _backfill_orphan_completion_logs(task, completed_at: datetime) -> list:
    """
    SI_FINISHING 멀티작업자 — work_start_log 에 시작 이력은 있으나
    work_completion_log 가 없는 작업자(미완료)에게 completed_at 시각으로 backfill.

    force_closed 아닌 정상 완료 처리 (Codex M-Q4).

    Returns:
        backfill 된 worker_id 목록
    """
    from app.services.task_service import _record_completion_log

    conn = None
    orphan_ids = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT wsl.worker_id
            FROM work_start_log wsl
            LEFT JOIN work_completion_log wcl
              ON wsl.task_id = wcl.task_id AND wsl.worker_id = wcl.worker_id
            WHERE wsl.task_id = %s AND wcl.id IS NULL
            """,
            (task.id,)
        )
        orphan_ids = [r['worker_id'] for r in cur.fetchall()]
    finally:
        if conn:
            put_conn(conn)

    for wid in orphan_ids:
        _record_completion_log(task=task, worker_id=wid, completed_at=completed_at)

    if orphan_ids:
        logger.info(
            f"ship-complete backfill: task_id={task.id}, orphan_workers={orphan_ids}"
        )
    return orphan_ids


def _set_ship_audit(task_detail_id: int, closed_by: int) -> None:
    """
    출하완료 audit 기록 (영역 11) — force_closed=FALSE 유지 (정상 종료).

    close_reason='SHIP_COMPLETE' + closed_by(실행 관리자). 강제종료가 아니므로
    force_closed 는 FALSE 로 명시 유지 — DB 에서 close_reason 으로 출하완료 추적.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE app_task_details
            SET close_reason = 'SHIP_COMPLETE',
                closed_by = %s,
                force_closed = FALSE,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (closed_by, task_detail_id)
        )
        conn.commit()
    finally:
        if conn:
            put_conn(conn)


def ship_complete(
    serial_number: str,
    admin_worker_id: int,
    completed_at_raw: Optional[str] = None,
) -> Tuple[Dict[str, Any], int]:
    """
    출하 완료 — 한 S/N 의 SI task 2개(SI_FINISHING + SI_SHIPMENT) 완료 처리.

    Args:
        serial_number: 대상 S/N
        admin_worker_id: 출하 완료를 실행한 admin/manager (g.worker_id)
        completed_at_raw: 완료 시각 ISO8601 (옵션 — 없으면 서버 now KST)

    Returns:
        (response dict, status code)
    """
    completed_at, err = _parse_completed_at(completed_at_raw)
    if err:
        return err

    # SI task 2개 조회
    si_tasks = get_tasks_by_serial_number(serial_number, task_category='SI')
    finishing = next(
        (t for t in si_tasks if t.task_id == SI_FINISHING and t.is_applicable), None
    )
    shipment = next(
        (t for t in si_tasks if t.task_id == SI_SHIPMENT and t.is_applicable), None
    )
    if not finishing or not shipment:
        return {
            'error': 'SI_TASK_NOT_FOUND',
            'message': 'SI 공정 task(SI_FINISHING/SI_SHIPMENT)를 찾을 수 없습니다.'
        }, 404

    # 멱등성 — 둘 다 이미 완료된 경우 no-op 성공 (Codex A-Q6)
    if finishing.completed_at and shipment.completed_at:
        return {
            'serial_number': serial_number,
            'already_completed': True,
            'completed_tasks': [],
            'si_completed': True,
            'message': '이미 출하 완료된 S/N 입니다.'
        }, 200

    completed_tasks = []

    # ── SI_FINISHING (FINAL, NORMAL task — 멀티작업자 가능) ──
    if not finishing.completed_at:
        if not finishing.started_at:
            return {
                'error': 'SI_FINISHING_NOT_STARTED',
                'message': 'SI 마무리공정이 아직 시작되지 않았습니다.'
            }, 400
        # completed_at >= started_at 검증 (Codex M-Q5 — 닫히는 task 기준)
        if completed_at < finishing.started_at:
            return {
                'error': 'INVALID_COMPLETED_AT_BEFORE_START',
                'message': '완료 시각이 마무리공정 시작 시각보다 빠를 수 없습니다.'
            }, 400
        # 미완료 작업자 backfill (force_closed 아닌 정상 완료)
        _backfill_orphan_completion_logs(finishing, completed_at)
        # 멀티작업자 집계 (duration/elapsed/worker_count)
        from app.services.task_service import _finalize_task_multi_worker
        _finalize_task_multi_worker(finishing.id, completed_at)
        # completed_at set
        if not complete_task(finishing.id, completed_at):
            return {
                'error': 'SHIP_COMPLETE_FAILED',
                'message': 'SI 마무리공정 완료 처리에 실패했습니다.'
            }, 500
        _set_ship_audit(finishing.id, admin_worker_id)
        completed_tasks.append(SI_FINISHING)

    # ── SI_SHIPMENT (SINGLE_ACTION task) ──
    if not shipment.completed_at:
        # SINGLE_ACTION 은 started_at 이 완료 시점에 set → started_at 이전 검증 불요
        if not complete_single_action(shipment.id, completed_at, admin_worker_id):
            return {
                'error': 'SHIP_COMPLETE_FAILED',
                'message': 'SI 출하완료 task 완료 처리에 실패했습니다.'
            }, 500
        _set_ship_audit(shipment.id, admin_worker_id)
        completed_tasks.append(SI_SHIPMENT)

    # SI 공정 전체 완료 → completion_status.si_completed 갱신
    update_process_completion(serial_number, 'SI', True)

    logger.info(
        f"Ship complete: serial_number={serial_number}, "
        f"completed_tasks={completed_tasks}, completed_at={completed_at.isoformat()}, "
        f"by admin_worker_id={admin_worker_id}"
    )

    return {
        'serial_number': serial_number,
        'completed_tasks': completed_tasks,
        'si_completed': True,
        'completed_at': completed_at.isoformat(),
        'already_completed': False,
    }, 200
