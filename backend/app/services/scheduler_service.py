"""
스케줄러 서비스
Sprint 4: APScheduler를 사용한 cron 작업
"""

import logging
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.duration_validator import check_unfinished_tasks


logger = logging.getLogger(__name__)

# 전역 스케줄러 인스턴스
_scheduler: Optional[BackgroundScheduler] = None


def init_scheduler() -> BackgroundScheduler:
    """
    스케줄러 초기화 및 작업 등록

    Returns:
        BackgroundScheduler 인스턴스
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("Scheduler already initialized")
        return _scheduler

    _scheduler = BackgroundScheduler()

    # 미완료 작업 체크 (매일 오후 6시 실행)
    _scheduler.add_job(
        func=run_unfinished_task_check,
        trigger=CronTrigger(hour=18, minute=0),
        id='check_unfinished_tasks',
        name='미완료 작업 체크 (정규 퇴근시간)',
        replace_existing=True
    )

    logger.info("Scheduler initialized with jobs")
    return _scheduler


def start_scheduler() -> None:
    """
    스케줄러 시작
    """
    global _scheduler

    if _scheduler is None:
        _scheduler = init_scheduler()

    if not _scheduler.running:
        _scheduler.start()
        logger.info("Scheduler started")
    else:
        logger.warning("Scheduler is already running")


def stop_scheduler() -> None:
    """
    스케줄러 종료
    """
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")
    else:
        logger.warning("Scheduler is not running")


def get_scheduler() -> Optional[BackgroundScheduler]:
    """
    현재 스케줄러 인스턴스 반환

    Returns:
        BackgroundScheduler 인스턴스 또는 None
    """
    return _scheduler


def run_unfinished_task_check() -> None:
    """
    미완료 작업 체크 실행 (cron job)

    started_at IS NOT NULL AND completed_at IS NULL인 Task 중
    duration > 14시간인 경우 관리자에게 알림 생성
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
