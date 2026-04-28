"""
작업 시간 검증 서비스
Sprint 3: 비정상 duration 검증
APP_PLAN_v4 § 2.5 구현
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

from psycopg2 import Error as PsycopgError

from app.models.worker import get_db_connection
from app.models.task_detail import get_task_by_id
from app.models.alert_log import create_alert
from app.services.process_validator import resolve_managers_for_category
from app.services.alert_service import sn_label
from app.db_pool import put_conn


logger = logging.getLogger(__name__)


# 작업 시간 임계값
MAX_DURATION_MINUTES = 14 * 60  # 14시간 = 840분
MIN_DURATION_MINUTES = 1  # 1분


def validate_duration(task_detail_id: int) -> Dict[str, Any]:
    """
    작업 완료 시 duration 검증 (APP_PLAN_v4 § 2.5)

    검증 규칙:
    1. completed_at < started_at → 역전 오류 (REVERSE_COMPLETION 알림)
    2. duration > 14시간 (840분) → 비정상 (DURATION_EXCEEDED 알림)
    3. duration < 1분 → 경고 (실수 터치 가능성, 알림 생성은 선택)

    Args:
        task_detail_id: 작업 ID

    Returns:
        {
            "valid": bool,              # 유효 여부
            "warnings": List[str],      # 경고 메시지 목록
            "alerts_created": int       # 생성된 알림 개수
        }
    """
    warnings = []
    alerts_created = 0

    # Task 조회
    task = get_task_by_id(task_detail_id)
    if not task:
        warnings.append("작업 정보를 찾을 수 없습니다.")
        return {
            "valid": False,
            "warnings": warnings,
            "alerts_created": 0
        }

    if not task.started_at or not task.completed_at:
        warnings.append("시작 또는 완료 시간이 없습니다.")
        return {
            "valid": False,
            "warnings": warnings,
            "alerts_created": 0
        }

    # 1. 역전 오류 체크 (completed_at < started_at)
    if task.completed_at < task.started_at:
        warnings.append("완료 시간이 시작 시간보다 이릅니다.")

        # 관리자에게 알림 생성 (TMS 등 partner-based 매핑 표준 함수)
        managers = resolve_managers_for_category(task.serial_number, task.task_category)
        for manager_id in managers:
            alert_id = create_alert(
                alert_type='REVERSE_COMPLETION',
                message=f"{sn_label(task.serial_number)} {task.task_category} - {task.task_name}: 완료 시간이 시작 시간보다 이릅니다.",
                serial_number=task.serial_number,
                qr_doc_id=task.qr_doc_id,
                triggered_by_worker_id=task.worker_id,
                target_worker_id=manager_id,
                target_role=task.task_category
            )
            if alert_id:
                alerts_created += 1
                logger.warning(f"REVERSE_COMPLETION alert created: task_id={task_detail_id}, alert_id={alert_id}")

        return {
            "valid": False,
            "warnings": warnings,
            "alerts_created": alerts_created
        }

    # 2. 비정상 duration 체크 (> 14시간)
    if task.duration_minutes and task.duration_minutes > MAX_DURATION_MINUTES:
        warnings.append(f"작업 시간이 {MAX_DURATION_MINUTES // 60}시간을 초과했습니다. ({task.duration_minutes}분)")

        # 관리자에게 알림 생성 (TMS 등 partner-based 매핑 표준 함수)
        managers = resolve_managers_for_category(task.serial_number, task.task_category)
        for manager_id in managers:
            alert_id = create_alert(
                alert_type='DURATION_EXCEEDED',
                message=f"{sn_label(task.serial_number)} {task.task_category} - {task.task_name}: 작업 시간 {task.duration_minutes}분 (14시간 초과)",
                serial_number=task.serial_number,
                qr_doc_id=task.qr_doc_id,
                triggered_by_worker_id=task.worker_id,
                target_worker_id=manager_id,
                target_role=task.task_category
            )
            if alert_id:
                alerts_created += 1
                logger.warning(f"DURATION_EXCEEDED alert created: task_id={task_detail_id}, duration={task.duration_minutes}min, alert_id={alert_id}")

    # 3. 너무 짧은 duration 체크 (< 1분)
    if task.duration_minutes is not None and task.duration_minutes < MIN_DURATION_MINUTES:
        warnings.append(f"작업 시간이 매우 짧습니다. ({task.duration_minutes}분) 실수로 터치한 것은 아닌지 확인하세요.")
        # 너무 짧은 경우는 경고만 출력, 알림 생성은 하지 않음 (선택)

    # valid는 역전 오류가 아니면 True (duration 초과는 경고만)
    valid = task.completed_at >= task.started_at

    return {
        "valid": valid,
        "warnings": warnings,
        "alerts_created": alerts_created
    }


def check_unfinished_tasks() -> List[Dict[str, Any]]:
    """
    미완료 작업 체크 (정규 퇴근시간 체크용)

    started_at IS NOT NULL AND completed_at IS NULL인 Task 조회
    duration = NOW() - started_at > 14시간이면 알림 생성

    현재 Sprint에서는 함수만 구현, cron 연동은 Sprint 4

    Returns:
        List of {task_id, serial_number, task_name, duration_hours, alert_id}
    """
    conn = None
    unfinished_tasks = []

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 미완료 작업 조회 (started_at 있고 completed_at 없음)
        cur.execute(
            """
            SELECT id, worker_id, serial_number, qr_doc_id, task_category,
                   task_id, task_name, started_at,
                   EXTRACT(EPOCH FROM (NOW() - started_at)) / 60 AS duration_minutes
            FROM app_task_details
            WHERE started_at IS NOT NULL
              AND completed_at IS NULL
              AND is_applicable = TRUE
            """
        )

        rows = cur.fetchall()

        for row in rows:
            task_detail_id = row['id']
            duration_minutes = int(row['duration_minutes']) if row['duration_minutes'] else 0

            # 14시간 초과한 경우
            if duration_minutes > MAX_DURATION_MINUTES:
                task_info = {
                    "task_id": task_detail_id,
                    "serial_number": row['serial_number'],
                    "task_name": row['task_name'],
                    "duration_hours": round(duration_minutes / 60, 1),
                    "alert_id": None
                }

                # 관리자에게 알림 생성 (TMS 등 partner-based 매핑 표준 함수)
                managers = resolve_managers_for_category(row['serial_number'], row['task_category'])
                for manager_id in managers:
                    alert_id = create_alert(
                        alert_type='UNFINISHED_AT_CLOSING',
                        message=f"{sn_label(row['serial_number'])} {row['task_category']} - {row['task_name']}: 작업 시작 후 {task_info['duration_hours']}시간 경과, 미완료 상태",
                        serial_number=row['serial_number'],
                        qr_doc_id=row['qr_doc_id'],
                        triggered_by_worker_id=row['worker_id'],
                        target_worker_id=manager_id,
                        target_role=row['task_category']
                    )
                    if alert_id:
                        task_info['alert_id'] = alert_id
                        logger.info(f"UNFINISHED_AT_CLOSING alert created: task_id={task_detail_id}, duration={task_info['duration_hours']}h, alert_id={alert_id}")
                        break  # 첫 번째 알림 ID만 저장

                unfinished_tasks.append(task_info)

        return unfinished_tasks

    except PsycopgError as e:
        logger.error(f"Failed to check unfinished tasks: {e}")
        return []
    finally:
        if conn:
            put_conn(conn)
