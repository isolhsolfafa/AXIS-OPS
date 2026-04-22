"""
알림 서비스
Sprint 3: 알림 생성 + 조회 + 읽음 처리 + WebSocket broadcast
HOTFIX-SCHEDULER-PHASE1.5 (2026-04-22): alert silent fail ERROR 로깅 추가
"""

import logging
from typing import Dict, Any, Optional, List

from app.models.alert_log import (
    create_alert,
    get_alerts_by_worker,
    get_alert_by_id,
    mark_alert_read as mark_alert_read_model,
    get_unread_count as get_unread_count_model
)
from psycopg2 import Error as PsycopgError
from app.models.worker import get_db_connection
from app.models.product_info import get_product_by_serial_number
from app.db_pool import put_conn


logger = logging.getLogger(__name__)

# HOTFIX-SCHEDULER-PHASE1.5: Sentry SDK 선택적 import (패키지 미설치 시 조용히 건너뛰기)
try:
    import sentry_sdk
    _SENTRY_AVAILABLE = True
except ImportError:
    _SENTRY_AVAILABLE = False


def sn_label(serial_number: str) -> str:
    """[S/N | O/N: xxx] 포맷 생성 — 전체 알람 메시지 공통"""
    product = get_product_by_serial_number(serial_number)
    on = product.sales_order if product and product.sales_order else None
    return f"[{serial_number} | O/N: {on}]" if on else f"[{serial_number}]"


def create_and_broadcast_alert(alert_data: Dict[str, Any]) -> Optional[int]:
    """
    알림 생성 + WebSocket broadcast

    Args:
        alert_data: {
            "alert_type": str,
            "message": str,
            "serial_number": str (optional),
            "qr_doc_id": str (optional),
            "triggered_by_worker_id": int (optional),
            "target_worker_id": int (optional),
            "target_role": str (optional)
        }

    Returns:
        alert_id, 실패 시 None
    """
    # HOTFIX-SCHEDULER-PHASE1.5: 전체 경로 ERROR 로깅 승격 (가능성 3 / G.3 silent fail 포착)
    try:
        alert_id = create_alert(
            alert_type=alert_data['alert_type'],
            message=alert_data['message'],
            serial_number=alert_data.get('serial_number'),
            qr_doc_id=alert_data.get('qr_doc_id'),
            triggered_by_worker_id=alert_data.get('triggered_by_worker_id'),
            target_worker_id=alert_data.get('target_worker_id'),
            target_role=alert_data.get('target_role'),
            task_detail_id=alert_data.get('task_detail_id')
        )

        if alert_id is None:
            logger.error(
                "[alert_create_none] create_alert returned None: alert_data=%s",
                alert_data
            )
            return None

        # WebSocket broadcast (Sprint 3) — 개별 try/except 로 DB insert 결과 보존
        try:
            from app.websocket.events import emit_new_alert, emit_process_alert
            from datetime import datetime
            from app.config import Config

            ws_alert_data = {
                "alert_id": alert_id,
                "alert_type": alert_data['alert_type'],
                "serial_number": alert_data.get('serial_number'),
                "qr_doc_id": alert_data.get('qr_doc_id'),
                "message": alert_data['message'],
                "created_at": datetime.now(Config.KST).isoformat()
            }

            # 특정 작업자에게 전송
            if alert_data.get('target_worker_id'):
                emit_new_alert(alert_data['target_worker_id'], ws_alert_data)
            # 역할 기반 전송 (공정 알림)
            elif alert_data.get('target_role'):
                ws_alert_data['target_role'] = alert_data['target_role']
                emit_process_alert(ws_alert_data)

            logger.info(f"Alert created and broadcasted: alert_id={alert_id}")
        except Exception as ws_exc:
            logger.error(
                f"[alert_silent_fail] WebSocket broadcast failed: "
                f"alert_id={alert_id}, alert_data={alert_data}, error={ws_exc}",
                exc_info=True
            )
            if _SENTRY_AVAILABLE:
                sentry_sdk.capture_exception(ws_exc)
            # broadcast 실패여도 DB insert 는 성공했으므로 alert_id 반환 유지

        return alert_id

    except Exception as e:
        logger.error(
            f"[alert_silent_fail] create_and_broadcast_alert exception: "
            f"alert_data={alert_data}, error={e}",
            exc_info=True
        )
        if _SENTRY_AVAILABLE:
            sentry_sdk.capture_exception(e)
        return None


def get_worker_alerts(
    worker_id: int,
    unread_only: bool = False,
    page: int = 1,
    limit: int = 50
) -> Dict[str, Any]:
    """
    작업자별 알림 목록 조회 (페이지네이션)

    Args:
        worker_id: 작업자 ID
        unread_only: True면 읽지 않은 알림만 조회
        page: 페이지 번호 (1부터 시작)
        limit: 페이지당 알림 수

    Returns:
        {
            "alerts": List[dict],
            "total": int,
            "unread_count": int,
            "page": int,
            "limit": int
        }
    """
    # 알림 목록 조회 (limit * page만큼 조회)
    alerts = get_alerts_by_worker(worker_id, unread_only=unread_only, limit=limit * page)

    # 페이지네이션 처리
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_alerts = alerts[start_idx:end_idx]

    # dict 변환
    alerts_dict = [
        {
            'id': alert.id,
            'alert_type': alert.alert_type,
            'serial_number': alert.serial_number,
            'qr_doc_id': alert.qr_doc_id,
            'message': alert.message,
            'is_read': alert.is_read,
            'created_at': alert.created_at.isoformat() if alert.created_at else None,
        }
        for alert in paginated_alerts
    ]

    # 읽지 않은 알림 개수 조회
    unread_count = get_unread_count_model(worker_id)

    return {
        "alerts": alerts_dict,
        "total": len(alerts),
        "unread_count": unread_count,
        "page": page,
        "limit": limit
    }


def mark_as_read(alert_id: int, worker_id: int) -> bool:
    """
    개별 알림 읽음 처리 (소유권 확인)

    Args:
        alert_id: 알림 ID
        worker_id: 작업자 ID (소유권 확인용)

    Returns:
        성공 시 True, 실패 시 False
    """
    # 알림 조회 (소유권 확인)
    alert = get_alert_by_id(alert_id)
    if not alert:
        logger.warning(f"Alert not found: alert_id={alert_id}")
        return False

    if alert.target_worker_id != worker_id:
        logger.warning(f"Permission denied: alert_id={alert_id}, worker_id={worker_id}, target_worker_id={alert.target_worker_id}")
        return False

    # 읽음 처리
    return mark_alert_read_model(alert_id)


def mark_all_read(worker_id: int) -> int:
    """
    작업자의 모든 알림 읽음 처리

    Args:
        worker_id: 작업자 ID

    Returns:
        읽음 처리한 알림 개수
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE app_alert_logs
            SET is_read = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE target_worker_id = %s AND is_read = FALSE
            """,
            (worker_id,)
        )

        count = cur.rowcount
        conn.commit()

        logger.info(f"Marked {count} alerts as read for worker_id={worker_id}")
        return count

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to mark all alerts as read: {e}")
        return 0
    finally:
        if conn:
            put_conn(conn)
