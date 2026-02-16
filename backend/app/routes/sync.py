"""
동기화 라우트
엔드포인트: /api/app/sync
Sprint 4: 오프라인 데이터 동기화
"""

import json
import logging
from flask import Blueprint, request, jsonify, g
from typing import Tuple, Dict, Any, List
from datetime import datetime

from app.middleware.jwt_auth import jwt_required
from app.models.worker import get_db_connection
from app.models.alert_log import mark_alert_read
from psycopg2 import Error as PsycopgError


logger = logging.getLogger(__name__)

sync_bp = Blueprint("sync", __name__, url_prefix="/api/app/sync")


@sync_bp.route("/offline-batch", methods=["POST"])
@jwt_required
def sync_offline_batch() -> Tuple[Dict[str, Any], int]:
    """
    오프라인 데이터 배치 동기화

    모바일 앱이 오프라인 상태에서 축적한 데이터를 서버에 동기화합니다.

    Request Body:
        {
            "tasks": [
                {
                    "task_detail_id": int,
                    "operation": str,  // "START", "COMPLETE"
                    "timestamp": str,  // ISO 8601
                    "data": dict       // 추가 데이터 (location, duration 등)
                }
            ],
            "locations": [
                {
                    "latitude": float,
                    "longitude": float,
                    "recorded_at": str  // ISO 8601
                }
            ],
            "alerts_read": [int]  // 읽음 처리할 alert_id 목록
        }

    Headers:
        Authorization: Bearer {token}

    Returns:
        200: {
            "message": "동기화 완료",
            "synced_tasks": int,
            "synced_locations": int,
            "synced_alerts": int,
            "failed_count": int
        }
    """
    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': '요청 본문이 필요합니다.'
        }), 400

    worker_id = g.worker_id
    tasks = data.get('tasks', [])
    locations = data.get('locations', [])
    alerts_read = data.get('alerts_read', [])

    synced_tasks = 0
    synced_locations = 0
    synced_alerts = 0
    failed_count = 0

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Tasks 동기화
        for task_item in tasks:
            try:
                task_detail_id = task_item.get('task_detail_id')
                operation = task_item.get('operation')
                timestamp_str = task_item.get('timestamp')
                task_data = task_item.get('data', {})

                if not task_detail_id or not operation or not timestamp_str:
                    logger.warning(f"Invalid task item: {task_item}")
                    failed_count += 1
                    continue

                timestamp = datetime.fromisoformat(timestamp_str)

                # offline_sync_queue에 레코드 생성
                cur.execute(
                    """
                    INSERT INTO offline_sync_queue
                        (worker_id, operation, table_name, record_id, data, synced, synced_at)
                    VALUES (%s, %s, %s, %s, %s, TRUE, CURRENT_TIMESTAMP)
                    """,
                    (worker_id, operation, 'app_task_details', str(task_detail_id),
                     json.dumps(task_data))
                )

                synced_tasks += 1

            except Exception as e:
                logger.error(f"Failed to sync task: {e}")
                failed_count += 1

        # 2. Locations 동기화
        for location_item in locations:
            try:
                latitude = location_item.get('latitude')
                longitude = location_item.get('longitude')
                recorded_at_str = location_item.get('recorded_at')

                if latitude is None or longitude is None or not recorded_at_str:
                    logger.warning(f"Invalid location item: {location_item}")
                    failed_count += 1
                    continue

                recorded_at = datetime.fromisoformat(recorded_at_str)

                # location_history에 삽입
                cur.execute(
                    """
                    INSERT INTO location_history
                        (worker_id, latitude, longitude, recorded_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (worker_id, latitude, longitude, recorded_at)
                )

                synced_locations += 1

            except Exception as e:
                logger.error(f"Failed to sync location: {e}")
                failed_count += 1

        # 3. Alerts 읽음 처리
        for alert_id in alerts_read:
            try:
                if mark_alert_read(alert_id):
                    synced_alerts += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Failed to mark alert as read: {e}")
                failed_count += 1

        conn.commit()

        logger.info(
            f"Offline sync completed: worker_id={worker_id}, "
            f"tasks={synced_tasks}, locations={synced_locations}, "
            f"alerts={synced_alerts}, failed={failed_count}"
        )

        return jsonify({
            'message': '동기화 완료',
            'synced_tasks': synced_tasks,
            'synced_locations': synced_locations,
            'synced_alerts': synced_alerts,
            'failed_count': failed_count
        }), 200

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Offline sync failed: {e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '동기화에 실패했습니다.'
        }), 500
    finally:
        if conn:
            conn.close()


@sync_bp.route("/status", methods=["GET"])
@jwt_required
def get_sync_status() -> Tuple[Dict[str, Any], int]:
    """
    동기화 상태 조회

    현재 작업자의 동기화 큐 상태를 반환합니다.

    Headers:
        Authorization: Bearer {token}

    Returns:
        200: {
            "pending_count": int,
            "synced_count": int,
            "last_synced_at": str
        }
    """
    worker_id = g.worker_id

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 미동기화 레코드 수
        cur.execute(
            """
            SELECT COUNT(*) as count
            FROM offline_sync_queue
            WHERE worker_id = %s AND synced = FALSE
            """,
            (worker_id,)
        )
        pending_count = cur.fetchone()['count']

        # 동기화 완료 레코드 수
        cur.execute(
            """
            SELECT COUNT(*) as count
            FROM offline_sync_queue
            WHERE worker_id = %s AND synced = TRUE
            """,
            (worker_id,)
        )
        synced_count = cur.fetchone()['count']

        # 마지막 동기화 시간
        cur.execute(
            """
            SELECT MAX(synced_at) as last_synced_at
            FROM offline_sync_queue
            WHERE worker_id = %s AND synced = TRUE
            """,
            (worker_id,)
        )
        row = cur.fetchone()
        last_synced_at = row['last_synced_at'].isoformat() if row['last_synced_at'] else None

        return jsonify({
            'pending_count': pending_count,
            'synced_count': synced_count,
            'last_synced_at': last_synced_at
        }), 200

    except PsycopgError as e:
        logger.error(f"Failed to get sync status: {e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '동기화 상태 조회에 실패했습니다.'
        }), 500
    finally:
        if conn:
            conn.close()
