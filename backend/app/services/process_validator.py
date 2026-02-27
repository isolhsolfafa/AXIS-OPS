"""
공정 검증 서비스
Sprint 3: 공정 누락 검증 + 알림 생성
Sprint 6: MM→MECH, EE→ELEC 네이밍 변경
APP_PLAN_v4 § 2.3 구현
"""

import logging
from typing import Dict, Any, List

from psycopg2 import Error as PsycopgError

from app.models.worker import get_db_connection
from app.models.completion_status import get_or_create_completion_status
from app.models.product_info import get_product_by_qr_doc_id
from app.models.alert_log import create_alert
from app.models.admin_settings import get_setting


logger = logging.getLogger(__name__)


def validate_process_start(
    serial_number: str,
    process_type: str,
    qr_doc_id: str,
    triggered_by_worker_id: int
) -> Dict[str, Any]:
    """
    PI/QI/SI 작업 시작 전 공정 검증 (APP_PLAN_v4 § 2.3)

    검증 순서:
    1. Location QR 등록 여부 체크 → 미등록 시 경고 메시지
    2. MECH(기구) 완료 체크 → 미완료 시 app_alert_logs INSERT + MECH 관리자 대상 알림
    3. ELEC(전장) 완료 체크 → 미완료 시 app_alert_logs INSERT + ELEC 관리자 대상 알림

    Args:
        serial_number: 시리얼 번호
        process_type: 공정 유형 (PI, QI, SI)
        qr_doc_id: QR 문서 ID
        triggered_by_worker_id: 검증 트리거한 작업자 ID

    Returns:
        {
            "can_proceed": bool,           # 작업 진행 가능 여부
            "warnings": List[str],         # 경고 메시지 목록
            "alerts_created": int          # 생성된 알림 개수
        }
    """
    warnings = []
    alerts_created = 0

    # PI/QI/SI만 검증 대상
    if process_type not in ['PI', 'QI', 'SI']:
        return {
            "can_proceed": True,
            "warnings": [],
            "alerts_created": 0
        }

    # 1. Location QR 등록 여부 체크
    product = get_product_by_qr_doc_id(qr_doc_id)
    if not product:
        warnings.append("제품 정보를 찾을 수 없습니다.")
        return {
            "can_proceed": False,
            "warnings": warnings,
            "alerts_created": 0
        }

    # location_qr_required admin setting 체크 (false면 경고 스킵)
    location_qr_required = get_setting('location_qr_required', True)
    if location_qr_required and not product.location_qr_id:
        warnings.append("Location QR이 등록되지 않았습니다.")

    # 2. MECH/ELEC 완료 체크
    completion_status = get_or_create_completion_status(serial_number)
    if not completion_status:
        warnings.append("완료 상태를 확인할 수 없습니다.")
        return {
            "can_proceed": False,
            "warnings": warnings,
            "alerts_created": 0
        }

    # MECH 미완료 시 알림 생성
    if not completion_status.mech_completed:
        warnings.append("MECH(기구) 공정이 완료되지 않았습니다.")

        # MECH 관리자들에게 알림 생성
        mech_managers = get_managers_for_role('MECH')
        for manager_id in mech_managers:
            alert_id = create_alert(
                alert_type='PROCESS_READY',
                message=f"[{serial_number}] {process_type} 공정 대기 중 - MECH 공정 미완료",
                serial_number=serial_number,
                qr_doc_id=qr_doc_id,
                triggered_by_worker_id=triggered_by_worker_id,
                target_worker_id=manager_id,
                target_role='MECH'
            )
            if alert_id:
                alerts_created += 1
                logger.info(f"Alert created for MECH manager {manager_id}: alert_id={alert_id}")

    # ELEC 미완료 시 알림 생성
    if not completion_status.elec_completed:
        warnings.append("ELEC(전장) 공정이 완료되지 않았습니다.")

        # ELEC 관리자들에게 알림 생성
        elec_managers = get_managers_for_role('ELEC')
        for manager_id in elec_managers:
            alert_id = create_alert(
                alert_type='PROCESS_READY',
                message=f"[{serial_number}] {process_type} 공정 대기 중 - ELEC 공정 미완료",
                serial_number=serial_number,
                qr_doc_id=qr_doc_id,
                triggered_by_worker_id=triggered_by_worker_id,
                target_worker_id=manager_id,
                target_role='ELEC'
            )
            if alert_id:
                alerts_created += 1
                logger.info(f"Alert created for ELEC manager {manager_id}: alert_id={alert_id}")

    # MECH와 ELEC 둘 다 완료되어야 진행 가능
    can_proceed = completion_status.mech_completed and completion_status.elec_completed

    return {
        "can_proceed": can_proceed,
        "warnings": warnings,
        "alerts_created": alerts_created
    }


def get_managers_for_role(role: str) -> List[int]:
    """
    특정 역할의 관리자 목록 조회

    Args:
        role: 역할 (MECH, ELEC, TM, PI, QI, SI)

    Returns:
        관리자 worker_id 리스트
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT id FROM workers
            WHERE role = %s
              AND is_manager = TRUE
              AND approval_status = 'approved'
            """,
            (role,)
        )

        rows = cur.fetchall()
        return [row['id'] for row in rows]

    except PsycopgError as e:
        logger.error(f"Failed to get managers for role={role}: {e}")
        return []
    finally:
        if conn:
            conn.close()
