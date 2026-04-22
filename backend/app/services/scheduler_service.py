"""
스케줄러 서비스
Sprint 4: APScheduler를 사용한 cron 작업
Sprint 6 Phase C: 3단계 알림 스케줄러 추가
  - [1단계] TASK_REMINDER: 매 1시간 cron → 진행 중인 작업자에게 리마인더
  - [2단계] SHIFT_END_REMINDER: 17:00, 20:00 KST → 미종료 작업 보유 작업자 알림
  - [3단계] TASK_ESCALATION: 익일 09:00 KST → 전일 미종료 → company 관리자 에스컬레이션
Sprint 9: 휴게시간 자동 일시정지
  - check_break_time: 매 분 → 휴게시간 시작/종료 감지 → 자동 일시정지/알림
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import Config
from app.services.duration_validator import check_unfinished_tasks
from app.services.alert_service import sn_label
from app.db_pool import put_conn


logger = logging.getLogger(__name__)

# HOTFIX-ALERT-SCHEDULER-DELIVERY-20260422:
# task_category → partner_field 매핑 (task_service.py L524-548 동일 규약 재사용)
_CATEGORY_PARTNER_FIELD = {
    'TMS':  'module_outsourcing',
    'MECH': 'mech_partner',
    'ELEC': 'elec_partner',
}


def _resolve_managers_for_category(serial_number: str, category: str) -> list:
    """
    task_category → 해당 관리자 worker_id 리스트.
    Partner 기반 (TMS/MECH/ELEC) 또는 Role 기반 (PI/QI/SI) 자동 분기.
    task_service.py L571 의 표준 알람 수신자 결정 패턴을 scheduler 에 적용.
    """
    from app.services.process_validator import get_managers_by_partner, get_managers_for_role
    if category in _CATEGORY_PARTNER_FIELD:
        return get_managers_by_partner(serial_number, _CATEGORY_PARTNER_FIELD[category])
    return get_managers_for_role(category)

# 전역 스케줄러 인스턴스
_scheduler: Optional[BackgroundScheduler] = None


def init_scheduler() -> BackgroundScheduler:
    """
    스케줄러 초기화 및 작업 등록 (KST 기준)

    등록 작업:
      1. check_unfinished_tasks_job     — 매 1시간 (14h+ 초과 체크)
      2. task_reminder_job              — 매 1시간 (진행 중인 작업자 리마인더)
      3. shift_end_reminder_job_17      — 17:00 KST (1차 퇴근 알림)
      4. shift_end_reminder_job_20      — 20:00 KST (2차 퇴근 알림)
      5. task_escalation_job            — 매일 09:00 KST (전일 미종료 에스컬레이션)

    Returns:
        BackgroundScheduler 인스턴스
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("Scheduler already initialized")
        return _scheduler

    _scheduler = BackgroundScheduler(timezone=Config.KST)

    # ── 1단계: TASK_REMINDER — 매 1시간 ─────────────────────────
    _scheduler.add_job(
        func=task_reminder_job,
        trigger=CronTrigger(minute=0),  # 매 정각
        id='task_reminder',
        name='작업자 리마인더 (매 1시간)',
        replace_existing=True
    )

    # ── 기존: 미완료 작업 14h+ 체크 (매일 18:00 KST) ─────────────
    _scheduler.add_job(
        func=run_unfinished_task_check,
        trigger=CronTrigger(hour=18, minute=0),
        id='check_unfinished_tasks',
        name='미완료 작업 체크 (정규 퇴근시간)',
        replace_existing=True
    )

    # ── 2단계: SHIFT_END_REMINDER — 17:00, 20:00 KST ─────────────
    _scheduler.add_job(
        func=shift_end_reminder_job,
        trigger=CronTrigger(hour=17, minute=0),
        id='shift_end_reminder_17',
        name='퇴근 알림 (17:00 KST)',
        replace_existing=True
    )
    _scheduler.add_job(
        func=shift_end_reminder_job,
        trigger=CronTrigger(hour=20, minute=0),
        id='shift_end_reminder_20',
        name='퇴근 알림 (20:00 KST)',
        replace_existing=True
    )

    # ── 3단계: TASK_ESCALATION — 익일 09:00 KST ──────────────────
    _scheduler.add_job(
        func=task_escalation_job,
        trigger=CronTrigger(hour=9, minute=0),
        id='task_escalation',
        name='미종료 Task 에스컬레이션 (09:00 KST)',
        replace_existing=True
    )

    # ── Sprint 9: 휴게시간 자동 일시정지 — 매 분 (정확히 HH:MM:00에 실행) ──
    _scheduler.add_job(
        func=check_break_time_job,
        trigger=CronTrigger(second=0),  # 매 분 정각(HH:MM:00)에 실행 → current_time == start_time 비교 보장
        id='check_break_time',
        name='휴게시간 자동 일시정지 (매 분)',
        replace_existing=True
    )

    # ── Sprint 32: Access Log 정리 — 매일 03:00 (30일 이상 삭제) ──
    _scheduler.add_job(
        func=_cleanup_access_logs,
        trigger=CronTrigger(hour=3, minute=0),
        id='cleanup_access_logs',
        name='Access Log 정리 (30일+)',
        replace_existing=True
    )

    # ── Sprint 41-B: 릴레이 미완료 감지 — 매 1시간 (task_reminder와 동일 주기) ──
    _scheduler.add_job(
        func=check_orphan_relay_tasks_job,
        trigger=CronTrigger(minute=0),
        id='check_orphan_relay_tasks',
        name='릴레이 미완료 task 감지 (매 1시간)',
        replace_existing=True
    )

    # ── Sprint 61-BE: 미시작 task 에스컬레이션 — 매일 09:00 KST ──
    _scheduler.add_job(
        func=_check_not_started_tasks,
        trigger=CronTrigger(hour=9, minute=0),
        id='check_not_started_tasks',
        name='미시작 Task 에스컬레이션 (09:00 KST)',
        replace_existing=True
    )

    # ── Sprint 61-BE: 체크리스트 완료 + task 미종료 감지 — 매일 09:00 KST ──
    _scheduler.add_job(
        func=_check_checklist_done_task_open,
        trigger=CronTrigger(hour=9, minute=0),
        id='check_checklist_done_task_open_09',
        name='체크리스트 완료 task 미종료 감지 (09:00 KST)',
        replace_existing=True
    )

    # ── Sprint 61-BE: 체크리스트 완료 + task 미종료 감지 — 매일 15:00 KST ──
    _scheduler.add_job(
        func=_check_checklist_done_task_open,
        trigger=CronTrigger(hour=15, minute=0),
        id='check_checklist_done_task_open_15',
        name='체크리스트 완료 task 미종료 감지 (15:00 KST)',
        replace_existing=True
    )

    logger.info("Scheduler initialized with 11 jobs")
    return _scheduler


def start_scheduler() -> None:
    """스케줄러 시작"""
    global _scheduler

    if _scheduler is None:
        _scheduler = init_scheduler()

    if not _scheduler.running:
        _scheduler.start()
        logger.info("Scheduler started")
    else:
        logger.warning("Scheduler is already running")


def stop_scheduler() -> None:
    """스케줄러 종료"""
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")
    else:
        logger.warning("Scheduler is not running")


def get_scheduler() -> Optional[BackgroundScheduler]:
    """현재 스케줄러 인스턴스 반환"""
    return _scheduler


# ──────────────────────────────────────────────────────────────
# Cron Job 함수들
# ──────────────────────────────────────────────────────────────

def run_unfinished_task_check() -> None:
    """
    미완료 작업 체크 (cron job — 매일 18:00 KST)
    started_at IS NOT NULL AND completed_at IS NULL + duration > 14시간 → 관리자 알림
    """
    try:
        logger.info("Starting unfinished task check job")
        unfinished_tasks = check_unfinished_tasks()

        if unfinished_tasks:
            logger.info(f"Found {len(unfinished_tasks)} unfinished tasks exceeding 14 hours")
            for task in unfinished_tasks:
                logger.info(
                    f"Unfinished task: task_id={task['task_id']}, "
                    f"serial_number={task['serial_number']}, "
                    f"duration={task['duration_hours']}h, "
                    f"alert_id={task.get('alert_id')}"
                )
        else:
            logger.info("No unfinished tasks found")

    except Exception as e:
        logger.error(f"Unfinished task check job failed: {e}", exc_info=True)


def task_reminder_job() -> None:
    """
    [1단계] TASK_REMINDER — 매 1시간
    현재 진행 중인 작업(started_at IS NOT NULL AND completed_at IS NULL)을 가진
    작업자 본인에게 리마인더 알림 발송.
    """
    try:
        logger.info("Running task_reminder_job")
        tasks = _get_active_tasks()

        from app.services.alert_service import create_and_broadcast_alert
        for t in tasks:
            duration_hours = round(t['duration_minutes'] / 60, 1)
            create_and_broadcast_alert({
                'alert_type': 'TASK_REMINDER',
                'message': (
                    f"{sn_label(t['serial_number'])} {t['task_category']} - "
                    f"{t['task_name']}: 작업 시작 후 {duration_hours}시간 경과, "
                    f"아직 완료 전입니다."
                ),
                'serial_number': t['serial_number'],
                'qr_doc_id': t['qr_doc_id'],
                'triggered_by_worker_id': None,
                'target_worker_id': t['worker_id'],
                'target_role': None,
            })

        logger.info(f"task_reminder_job: {len(tasks)} reminders sent")

    except Exception as e:
        logger.error(f"task_reminder_job failed: {e}", exc_info=True)


def shift_end_reminder_job() -> None:
    """
    [2단계] SHIFT_END_REMINDER — 17:00 / 20:00 KST
    미종료 작업을 보유한 작업자에게 퇴근 전 완료 요청 알림.
    """
    try:
        logger.info("Running shift_end_reminder_job")
        tasks = _get_active_tasks()

        from app.services.alert_service import create_and_broadcast_alert
        notified_workers = set()
        for t in tasks:
            worker_id = t['worker_id']
            if worker_id in notified_workers:
                continue  # 같은 작업자에 중복 발송 방지
            notified_workers.add(worker_id)

            create_and_broadcast_alert({
                'alert_type': 'SHIFT_END_REMINDER',
                'message': (
                    f"퇴근 전 미완료 작업이 있습니다. "
                    f"{sn_label(t['serial_number'])} {t['task_category']} - {t['task_name']}. "
                    f"작업을 완료하거나 관리자에게 보고해주세요."
                ),
                'serial_number': t['serial_number'],
                'qr_doc_id': t['qr_doc_id'],
                'triggered_by_worker_id': None,
                'target_worker_id': worker_id,
                'target_role': None,
            })

        logger.info(f"shift_end_reminder_job: {len(notified_workers)} workers notified")

    except Exception as e:
        logger.error(f"shift_end_reminder_job failed: {e}", exc_info=True)


def task_escalation_job() -> None:
    """
    [3단계] TASK_ESCALATION — 매일 09:00 KST
    전일(started_at < 오늘 00:00 KST) 미종료 Task를 해당 작업자의
    company 관리자(is_manager=true + 같은 company)에게 에스컬레이션.
    """
    try:
        logger.info("Running task_escalation_job")

        # 오늘 00:00 KST
        now_kst = datetime.now(Config.KST)
        today_midnight = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)

        overdue_tasks = _get_overdue_tasks(before=today_midnight)

        from app.services.alert_service import create_and_broadcast_alert
        escalated = 0

        for t in overdue_tasks:
            # 작업자의 company 관리자 목록 조회
            managers = _get_company_managers(t['worker_id'])
            for manager_id in managers:
                create_and_broadcast_alert({
                    'alert_type': 'TASK_ESCALATION',
                    'message': (
                        f"[에스컬레이션] {sn_label(t['serial_number'])} "
                        f"{t['task_category']} - {t['task_name']}: "
                        f"전일({t['started_date']}) 시작 후 미완료. "
                        f"작업자: {t['worker_name']} ({t['worker_company'] or '-'})"
                    ),
                    'serial_number': t['serial_number'],
                    'qr_doc_id': t['qr_doc_id'],
                    'triggered_by_worker_id': t['worker_id'],
                    'target_worker_id': manager_id,
                    'target_role': t['task_category'],
                })
                escalated += 1

        logger.info(f"task_escalation_job: {escalated} escalation alerts sent for {len(overdue_tasks)} overdue tasks")

    except Exception as e:
        logger.error(f"task_escalation_job failed: {e}", exc_info=True)


# ──────────────────────────────────────────────────────────────
# 내부 헬퍼 — DB 조회
# ──────────────────────────────────────────────────────────────

def _get_active_tasks() -> List[Dict[str, Any]]:
    """
    현재 진행 중인 작업(started_at IS NOT NULL, completed_at IS NULL) 조회.

    Returns:
        [{ task_id, worker_id, serial_number, qr_doc_id,
           task_category, task_name, started_at, duration_minutes }]
    """
    from app.models.worker import get_db_connection
    from psycopg2 import Error as PsycopgError

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                t.id AS task_id,
                t.worker_id,
                t.serial_number,
                t.qr_doc_id,
                t.task_category,
                t.task_name,
                t.started_at,
                EXTRACT(EPOCH FROM (NOW() - t.started_at)) / 60 AS duration_minutes
            FROM app_task_details t
            WHERE t.started_at IS NOT NULL
              AND t.completed_at IS NULL
              AND t.is_applicable = TRUE
              AND t.worker_id IS NOT NULL
            """
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]

    except PsycopgError as e:
        logger.error(f"_get_active_tasks failed: {e}")
        return []
    finally:
        if conn:
            put_conn(conn)


def _get_overdue_tasks(before: datetime) -> List[Dict[str, Any]]:
    """
    전일 미종료 작업 조회 (started_at < before 이고 completed_at IS NULL).

    Args:
        before: 기준 시각 (오늘 00:00 KST)

    Returns:
        [{ task_id, worker_id, worker_name, worker_company,
           serial_number, qr_doc_id, task_category, task_name, started_date }]
    """
    from app.models.worker import get_db_connection
    from psycopg2 import Error as PsycopgError

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                t.id AS task_id,
                t.worker_id,
                w.name AS worker_name,
                w.company AS worker_company,
                t.serial_number,
                t.qr_doc_id,
                t.task_category,
                t.task_name,
                DATE(t.started_at AT TIME ZONE 'Asia/Seoul') AS started_date
            FROM app_task_details t
            JOIN workers w ON t.worker_id = w.id
            WHERE t.started_at < %s
              AND t.completed_at IS NULL
              AND t.is_applicable = TRUE
              AND t.worker_id IS NOT NULL
            """,
            (before,)
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]

    except PsycopgError as e:
        logger.error(f"_get_overdue_tasks failed: {e}")
        return []
    finally:
        if conn:
            put_conn(conn)


def _get_company_managers(worker_id: int) -> List[int]:
    """
    해당 작업자와 같은 company를 가진 관리자(is_manager=True) ID 목록 조회.

    Args:
        worker_id: 작업자 ID

    Returns:
        관리자 ID 리스트
    """
    from app.models.worker import get_db_connection
    from psycopg2 import Error as PsycopgError

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 작업자의 company 조회
        cur.execute(
            "SELECT company FROM workers WHERE id = %s",
            (worker_id,)
        )
        row = cur.fetchone()
        if not row or not row['company']:
            # company 없으면 ADMIN 권한자에게 에스컬레이션
            cur.execute(
                """
                SELECT id FROM workers
                WHERE is_admin = TRUE AND approval_status = 'approved'
                LIMIT 5
                """
            )
        else:
            company = row['company']
            cur.execute(
                """
                SELECT id FROM workers
                WHERE company = %s
                  AND is_manager = TRUE
                  AND approval_status = 'approved'
                """,
                (company,)
            )

        manager_rows = cur.fetchall()
        return [r['id'] for r in manager_rows]

    except PsycopgError as e:
        logger.error(f"_get_company_managers failed: worker_id={worker_id}, error={e}")
        return []
    finally:
        if conn:
            put_conn(conn)


# ──────────────────────────────────────────────────────────────
# 수동 실행 (관리자용)
# ──────────────────────────────────────────────────────────────

def trigger_unfinished_task_check_manually() -> dict:
    """
    미완료 작업 체크 수동 실행 (관리자용)

    Returns:
        {
            "message": str,
            "unfinished_count": int,
            "tasks": List[dict]
        }
    """
    try:
        logger.info("Manual trigger: unfinished task check")
        unfinished_tasks = check_unfinished_tasks()

        return {
            "message": "미완료 작업 체크 완료",
            "unfinished_count": len(unfinished_tasks),
            "tasks": unfinished_tasks
        }

    except Exception as e:
        logger.error(f"Manual unfinished task check failed: {e}", exc_info=True)
        return {
            "message": "미완료 작업 체크 실패",
            "unfinished_count": 0,
            "tasks": [],
            "error": str(e)
        }


def trigger_task_escalation_manually() -> dict:
    """
    TASK_ESCALATION 수동 실행 (관리자용)

    Returns:
        {
            "message": str,
            "overdue_count": int
        }
    """
    try:
        logger.info("Manual trigger: task escalation")
        task_escalation_job()
        return {"message": "에스컬레이션 알림 발송 완료", "overdue_count": -1}  # count 계산은 내부에서
    except Exception as e:
        logger.error(f"Manual task escalation failed: {e}", exc_info=True)
        return {"message": "에스컬레이션 실패", "error": str(e)}


# ──────────────────────────────────────────────────────────────
# Sprint 9: 휴게시간 자동 일시정지
# ──────────────────────────────────────────────────────────────

# 휴게시간 설정 키와 알림 메시지 매핑
BREAK_PERIODS = [
    {
        'start_key': 'break_morning_start',
        'end_key':   'break_morning_end',
        'pause_type': 'break_morning',
        'start_msg': '오전 휴게시간이 시작되었습니다. 작업이 자동으로 일시정지됩니다.',
        'end_msg':   '오전 휴게시간이 종료되었습니다. 작업을 재개해주세요.',
    },
    {
        'start_key': 'lunch_start',
        'end_key':   'lunch_end',
        'pause_type': 'lunch',
        'start_msg': '점심시간이 시작되었습니다. 작업이 자동으로 일시정지됩니다.',
        'end_msg':   '점심시간이 종료되었습니다. 작업을 재개해주세요.',
    },
    {
        'start_key': 'break_afternoon_start',
        'end_key':   'break_afternoon_end',
        'pause_type': 'break_afternoon',
        'start_msg': '오후 휴게시간이 시작되었습니다. 작업이 자동으로 일시정지됩니다.',
        'end_msg':   '오후 휴게시간이 종료되었습니다. 작업을 재개해주세요.',
    },
    {
        'start_key': 'dinner_start',
        'end_key':   'dinner_end',
        'pause_type': 'dinner',
        'start_msg': '저녁시간이 시작되었습니다. 작업이 자동으로 일시정지됩니다.',
        'end_msg':   '저녁시간이 종료되었습니다. 작업을 재개해주세요.',
    },
]


def check_break_time_job() -> None:
    """
    Sprint 9: 휴게시간 자동 일시정지 (매 분 실행)

    admin_settings에서 휴게시간 설정을 읽어 현재 시각(KST HH:MM)과 비교.
    - 시작 시각 일치 → 진행 중인 모든 작업 강제 일시정지 + 알림
    - 종료 시각 일치 → 휴게시간 종료 알림 (재개는 작업자 수동)
    """
    try:
        from app.models.admin_settings import get_setting

        # 자동 일시정지 비활성화 확인
        auto_pause_enabled = get_setting('auto_pause_enabled', True)
        if not auto_pause_enabled:
            return

        # 현재 KST 시각 HH:MM
        now_kst = datetime.now(Config.KST)
        current_time = now_kst.strftime('%H:%M')

        for period in BREAK_PERIODS:
            start_time = get_setting(period['start_key'], None)
            end_time = get_setting(period['end_key'], None)

            if not start_time or not end_time:
                continue

            if current_time == start_time:
                logger.info(f"Break start detected: {period['pause_type']} at {current_time}")
                force_pause_all_active_tasks(period['pause_type'], period['start_msg'])

            elif current_time == end_time:
                logger.info(f"Break end detected: {period['pause_type']} at {current_time}")
                send_break_end_notifications(period['pause_type'], period['end_msg'])

    except Exception as e:
        logger.error(f"check_break_time_job failed: {e}", exc_info=True)


def force_pause_all_active_tasks(pause_type: str, message: str) -> None:
    """
    현재 진행 중인 모든 작업을 강제 일시정지.
    Sprint 9: 휴게시간 시작 시 호출
    BUG-7 Fix: 멀티 작업자 지원 — work_start_log 기준으로 모든 활성 작업자에 pause 생성

    Args:
        pause_type: 일시정지 유형 ('break_morning' | 'lunch' | 'break_afternoon' | 'dinner')
        message: 알림 메시지
    """
    from app.models.worker import get_db_connection
    from app.models.work_pause_log import create_pause
    from app.models.task_detail import set_paused
    from app.services.alert_service import create_and_broadcast_alert
    from psycopg2 import Error as PsycopgError

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 현재 진행 중이고 일시정지되지 않은 작업 조회
        cur.execute(
            """
            SELECT t.id AS task_detail_id,
                   t.serial_number,
                   t.qr_doc_id,
                   t.task_category,
                   t.task_name
            FROM app_task_details t
            WHERE t.started_at IS NOT NULL
              AND t.completed_at IS NULL
              AND t.is_paused = FALSE
              AND t.is_applicable = TRUE
            """
        )
        active_tasks = cur.fetchall()

        # BUG-7 Fix: 각 task에 대해 모든 활성 작업자(시작 O, 완료 X) 조회
        task_active_workers = {}
        for task_row in active_tasks:
            task_id = task_row['task_detail_id']
            cur.execute(
                """
                SELECT DISTINCT wsl.worker_id
                FROM work_start_log wsl
                LEFT JOIN work_completion_log wcl
                       ON wsl.task_id = wcl.task_id AND wsl.worker_id = wcl.worker_id
                WHERE wsl.task_id = %s AND wcl.id IS NULL
                """,
                (task_id,)
            )
            worker_rows = cur.fetchall()
            active_worker_ids = [r['worker_id'] for r in worker_rows]
            task_active_workers[task_id] = active_worker_ids

    except PsycopgError as e:
        logger.error(f"force_pause_all_active_tasks query failed: {e}")
        return
    finally:
        if conn:
            put_conn(conn)

    paused_count = 0
    for task_row in active_tasks:
        task_id = task_row['task_detail_id']
        active_worker_ids = task_active_workers.get(task_id, [])

        if not active_worker_ids:
            continue  # 활성 작업자가 없으면 건너뜀

        task_paused = False
        for worker_id in active_worker_ids:
            # 각 활성 작업자마다 일시정지 로그 생성
            pause_log = create_pause(task_id, worker_id, pause_type=pause_type)
            if pause_log:
                task_paused = True
                paused_count += 1

                # 작업자에게 알림
                try:
                    create_and_broadcast_alert({
                        'alert_type': 'BREAK_TIME_PAUSE',
                        'message': f"{sn_label(task_row['serial_number'])} {task_row['task_name']}: {message}",
                        'serial_number': task_row['serial_number'],
                        'qr_doc_id': task_row['qr_doc_id'],
                        'triggered_by_worker_id': None,
                        'target_worker_id': worker_id,
                        'target_role': None,
                    })
                except Exception as e:
                    logger.warning(f"Failed to create BREAK_TIME_PAUSE alert for worker_id={worker_id}: {e}")

        # Sprint 55: task.is_paused = 전원 paused일 때만 true (재판정)
        if task_paused:
            from app.services.task_service import _all_active_workers_paused
            all_paused = _all_active_workers_paused(task_id)
            set_paused(task_id, is_paused=all_paused)

    logger.info(f"force_pause_all_active_tasks: created {paused_count} pause logs (pause_type={pause_type})")


def send_break_end_notifications(pause_type: str, message: str) -> None:
    """
    휴게시간 종료 알림 발송 + 자동 재개 처리.
    Sprint 9: 휴게시간 종료 시 호출
    BUG-7 Fix: 알림뿐 아니라 paused 작업을 실제로 auto-resume

    Args:
        pause_type: 일시정지 유형 (break_morning | lunch | break_afternoon | dinner)
        message: 알림 메시지
    """
    from app.models.worker import get_db_connection
    from app.models.work_pause_log import resume_pause
    from app.models.task_detail import set_paused
    from app.services.alert_service import create_and_broadcast_alert
    from psycopg2 import Error as PsycopgError

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 아직 재개되지 않은 해당 pause_type의 일시정지 로그 조회
        # BUG-7 Fix: task_detail_id, total_pause_minutes도 함께 조회 (자동 재개용)
        cur.execute(
            """
            SELECT wpl.id AS pause_log_id,
                   wpl.worker_id,
                   wpl.task_detail_id,
                   t.serial_number,
                   t.qr_doc_id,
                   t.task_name,
                   t.id AS task_id,
                   t.total_pause_minutes
            FROM work_pause_log wpl
            JOIN app_task_details t ON wpl.task_detail_id = t.id
            WHERE wpl.pause_type = %s
              AND wpl.resumed_at IS NULL
            """,
            (pause_type,)
        )
        rows = cur.fetchall()

    except PsycopgError as e:
        logger.error(f"send_break_end_notifications query failed: {e}")
        return
    finally:
        if conn:
            put_conn(conn)

    now_kst = datetime.now(Config.KST)
    notified_workers = set()
    resumed_count = 0

    for row in rows:
        worker_id = row['worker_id']
        pause_log_id = row['pause_log_id']
        task_detail_id = row['task_detail_id']
        current_total_pause = row['total_pause_minutes'] or 0

        # BUG-7 Fix: 자동 재개 처리 — pause_log resume + task is_paused 재판정
        try:
            updated_pause = resume_pause(pause_log_id, now_kst)
            if updated_pause:
                pause_duration = updated_pause.pause_duration_minutes or 0
                new_total_pause_minutes = current_total_pause + pause_duration
                # Sprint 55: is_paused 재판정 (전원 paused 여부)
                from app.services.task_service import _all_active_workers_paused
                all_paused = _all_active_workers_paused(task_detail_id)
                set_paused(task_detail_id, is_paused=all_paused, total_pause_minutes=new_total_pause_minutes)
                resumed_count += 1
            else:
                # resume 실패해도 is_paused는 재판정
                from app.services.task_service import _all_active_workers_paused
                all_paused = _all_active_workers_paused(task_detail_id)
                set_paused(task_detail_id, is_paused=all_paused)
        except Exception as e:
            logger.warning(f"Failed to auto-resume pause_log_id={pause_log_id}: {e}")
            # resume 실패해도 알림은 계속 발송
            try:
                from app.services.task_service import _all_active_workers_paused
                all_paused = _all_active_workers_paused(task_detail_id)
                set_paused(task_detail_id, is_paused=all_paused)
            except Exception:
                pass

        # 알림 발송 (작업자당 1회)
        if worker_id not in notified_workers:
            notified_workers.add(worker_id)
            try:
                create_and_broadcast_alert({
                    'alert_type': 'BREAK_TIME_END',
                    'message': f"{sn_label(row['serial_number'])} {row['task_name']}: {message}",
                    'serial_number': row['serial_number'],
                    'qr_doc_id': row['qr_doc_id'],
                    'triggered_by_worker_id': None,
                    'target_worker_id': worker_id,
                    'target_role': None,
                })
            except Exception as e:
                logger.warning(f"Failed to create BREAK_TIME_END alert for worker_id={worker_id}: {e}")

    logger.info(
        f"send_break_end_notifications: notified {len(notified_workers)} workers, "
        f"auto-resumed {resumed_count} pause logs (pause_type={pause_type})"
    )


def check_orphan_relay_tasks_job() -> None:
    """
    Sprint 41-B: 릴레이 미완료 task 감지 → Manager 알림 (매 1시간 실행)

    조건: work_completion_log 마지막 기록 후 4시간 이상 경과 + completed_at IS NULL
    대상: MECH, ELEC, TMS 카테고리 (협력사 교대 작업 대상)
    중복 방지: 동일 task에 대해 24시간 내 이미 RELAY_ORPHAN 알림이 있으면 발송 안 함
    """
    conn = None
    try:
        logger.info("Running check_orphan_relay_tasks_job")
        from app.models.worker import get_db_connection as _get_db_connection
        conn = _get_db_connection()
        cur = conn.cursor()

        # 4시간 이상 경과된 릴레이 미완료 task 조회
        cur.execute("""
            SELECT atd.id AS task_detail_id,
                   atd.serial_number,
                   atd.qr_doc_id,
                   atd.task_category,
                   atd.task_name,
                   MAX(wcl.completed_at) AS last_completion_at,
                   COUNT(DISTINCT wcl.worker_id) AS worker_count
            FROM app_task_details atd
            JOIN work_completion_log wcl ON wcl.task_id = atd.id
            WHERE atd.completed_at IS NULL
              AND atd.is_applicable = TRUE
              AND atd.task_category IN ('MECH', 'ELEC', 'TMS')
            GROUP BY atd.id
            HAVING MAX(wcl.completed_at) < NOW() - INTERVAL '4 hours'
        """)
        orphans = cur.fetchall()

        from app.services.alert_service import create_and_broadcast_alert
        alert_count = 0

        for orphan in orphans:
            # HOTFIX-ALERT-SCHEDULER-DELIVERY-20260422:
            # 배치 dedupe (M2 수용) — target_worker_id 지정된 row 만 고려 (legacy NULL 제외)
            # 기존 query 는 target_worker_id 구분 없이 any row 체크하여 legacy 가 새 배송 차단
            cur.execute("""
                SELECT DISTINCT target_worker_id FROM app_alert_logs
                WHERE alert_type = 'RELAY_ORPHAN'
                  AND serial_number = %s
                  AND target_worker_id IS NOT NULL
                  AND message LIKE %s
                  AND created_at > NOW() - INTERVAL '24 hours'
            """, (orphan['serial_number'], f"%{orphan['task_name']}%"))
            already_sent = {row['target_worker_id'] for row in cur.fetchall()}

            # 표준 패턴 (task_service.py L571) — 관리자별 개별 INSERT
            managers = _resolve_managers_for_category(
                orphan['serial_number'], orphan['task_category']
            )
            message = (
                f"[릴레이 미완료] {sn_label(orphan['serial_number'])} "
                f"{orphan['task_name']} — "
                f"작업자 {orphan['worker_count']}명 참여 후 "
                f"4시간 이상 미완료 상태입니다."
            )
            for manager_id in managers:
                if manager_id in already_sent:
                    continue
                create_and_broadcast_alert({
                    'alert_type': 'RELAY_ORPHAN',
                    'message': message,
                    'serial_number': orphan['serial_number'],
                    'qr_doc_id': orphan['qr_doc_id'],
                    'target_worker_id': manager_id,
                    'target_role': orphan['task_category'],  # 라벨용 유지
                })
                alert_count += 1

            if managers:
                logger.info(
                    f"Relay orphan alert sent: task_id={orphan['task_detail_id']}, "
                    f"serial_number={orphan['serial_number']}, "
                    f"managers={len(managers)}, already_sent={len(already_sent)}"
                )

        logger.info(f"check_orphan_relay_tasks_job: {alert_count} alerts sent (orphans={len(orphans)})")

    except Exception as e:
        logger.error(f"check_orphan_relay_tasks_job failed: {e}", exc_info=True)
    finally:
        if conn:
            put_conn(conn)


def _check_not_started_tasks():
    """
    Sprint 61-BE: 미시작 task 에스컬레이션 — 매일 09:00 KST

    조건: 같은 S/N에 시작된 task가 하나라도 있는데, 본 task는 미시작 + 생성 후 N일 경과
    중복방지: 같은 task_detail_id로 7일 이내 발송 이력 있으면 스킵
    """
    try:
        from app.models.admin_settings import get_setting

        if not get_setting('alert_task_not_started_enabled', True):
            return

        threshold_days = int(get_setting('task_not_started_threshold_days', 2))

        from app.models.worker import get_db_connection as _get_db
        conn = _get_db()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT td.id, td.serial_number, td.task_category, td.task_name, td.created_at
                FROM app_task_details td
                WHERE td.started_at IS NULL
                  AND td.completed_at IS NULL
                  AND td.is_applicable = TRUE
                  AND td.force_closed = FALSE
                  AND td.created_at < NOW() - (%s * INTERVAL '1 day')
                  AND EXISTS (
                    SELECT 1 FROM app_task_details td2
                    WHERE td2.serial_number = td.serial_number
                      AND td2.started_at IS NOT NULL
                  )
            """, (threshold_days,))
            tasks = cur.fetchall()

            from app.services.alert_service import create_and_broadcast_alert

            alert_count = 0
            for task_row in tasks:
                sn = task_row['serial_number']
                td_id = task_row['id']

                # HOTFIX-ALERT-SCHEDULER-DELIVERY-20260422:
                # 배치 dedupe (M2) — target_worker_id 지정된 row 만 legacy 제외
                cur.execute("""
                    SELECT DISTINCT target_worker_id FROM app_alert_logs
                    WHERE alert_type = 'TASK_NOT_STARTED'
                      AND serial_number = %s
                      AND task_detail_id = %s
                      AND target_worker_id IS NOT NULL
                      AND created_at > NOW() - INTERVAL '7 days'
                """, (sn, td_id))
                already_sent = {row['target_worker_id'] for row in cur.fetchall()}

                days_elapsed = (datetime.now(Config.KST) - task_row['created_at']).days
                label = sn_label(sn)
                message = (
                    f"{label} {task_row['task_category']} - {task_row['task_name']}: "
                    f"생성 후 {days_elapsed}일 경과, 아직 시작되지 않았습니다."
                )

                managers = _resolve_managers_for_category(sn, task_row['task_category'])
                for manager_id in managers:
                    if manager_id in already_sent:
                        continue
                    create_and_broadcast_alert({
                        'alert_type': 'TASK_NOT_STARTED',
                        'message': message,
                        'serial_number': sn,
                        'target_worker_id': manager_id,
                        'target_role': task_row['task_category'],
                        'task_detail_id': td_id,
                    })
                    alert_count += 1
                if managers:
                    logger.info(
                        f"TASK_NOT_STARTED alert: sn={sn}, task={task_row['task_name']}, "
                        f"days={days_elapsed}, managers={len(managers)}, already_sent={len(already_sent)}"
                    )

            logger.info(f"_check_not_started_tasks: {alert_count} alerts sent (candidates={len(tasks)})")
        finally:
            put_conn(conn)

    except Exception as e:
        logger.error(f"Failed to check not-started tasks: {e}", exc_info=True)


def _check_checklist_done_task_open():
    """
    Sprint 61-BE: 체크리스트 완료 + task 미종료 감지 — 매일 09:00/15:00 KST

    ELEC 체크리스트 완료(IF_2 완료) S/N 중 ELEC task가 아직 미완료인 건 감지.
    중복방지: 같은 serial_number로 3일 이내 발송 이력 있으면 스킵
    """
    try:
        from app.models.admin_settings import get_setting

        if not get_setting('alert_checklist_done_task_open_enabled', True):
            return

        from app.models.worker import get_db_connection as _get_db
        conn = _get_db()
        try:
            cur = conn.cursor()
            # ELEC IF_2 완료 S/N 중 ELEC task 미완료 존재
            cur.execute("""
                SELECT td.id, td.serial_number, td.task_category, td.task_name
                FROM app_task_details td
                WHERE td.task_category = 'ELEC'
                  AND td.completed_at IS NULL
                  AND td.is_applicable = TRUE
                  AND td.force_closed = FALSE
                  AND td.serial_number IN (
                    SELECT DISTINCT td2.serial_number
                    FROM app_task_details td2
                    WHERE td2.task_category = 'ELEC'
                      AND td2.task_id = 'IF_2'
                      AND td2.completed_at IS NOT NULL
                  )
            """)
            tasks = cur.fetchall()

            from app.services.alert_service import create_and_broadcast_alert

            alert_count = 0
            for task_row in tasks:
                sn = task_row['serial_number']
                td_id = task_row['id']

                # HOTFIX-ALERT-SCHEDULER-DELIVERY-20260422:
                # 배치 dedupe (M2) — target_worker_id 지정된 row 만 legacy 제외
                cur.execute("""
                    SELECT DISTINCT target_worker_id FROM app_alert_logs
                    WHERE alert_type = 'CHECKLIST_DONE_TASK_OPEN'
                      AND serial_number = %s
                      AND target_worker_id IS NOT NULL
                      AND created_at > NOW() - INTERVAL '3 days'
                """, (sn,))
                already_sent = {row['target_worker_id'] for row in cur.fetchall()}

                label = sn_label(sn)
                message = (
                    f"{label} ELEC 체크리스트 완료 — "
                    f"{task_row['task_name']} 미종료 상태입니다. 완료 처리가 필요합니다."
                )

                managers = _resolve_managers_for_category(sn, 'ELEC')
                for manager_id in managers:
                    if manager_id in already_sent:
                        continue
                    create_and_broadcast_alert({
                        'alert_type': 'CHECKLIST_DONE_TASK_OPEN',
                        'message': message,
                        'serial_number': sn,
                        'target_worker_id': manager_id,
                        'target_role': 'ELEC',
                        'task_detail_id': td_id,
                    })
                    alert_count += 1
                if managers:
                    logger.info(
                        f"CHECKLIST_DONE_TASK_OPEN alert: sn={sn}, task={task_row['task_name']}, "
                        f"managers={len(managers)}, already_sent={len(already_sent)}"
                    )

            logger.info(f"_check_checklist_done_task_open: {alert_count} alerts sent (candidates={len(tasks)})")
        finally:
            put_conn(conn)

    except Exception as e:
        logger.error(f"Failed to check checklist-done-task-open: {e}", exc_info=True)


def _cleanup_access_logs():
    """Sprint 32: 30일 이상 된 access log 삭제"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM app_access_log WHERE created_at < NOW() - INTERVAL '30 days'")
        deleted = cur.rowcount
        conn.commit()
        logger.info(f"[cleanup] Access log: {deleted} rows deleted (30d+)")
    except Exception as e:
        logger.error(f"[cleanup] Access log cleanup failed: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            put_conn(conn)
