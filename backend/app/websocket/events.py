"""
WebSocket 이벤트 핸들러
Sprint 3: 클라이언트 연결 관리 + 알림 브로드캐스팅
"""

import logging
from typing import Any, Dict, Optional
from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room

from app.middleware.jwt_auth import decode_jwt


logger = logging.getLogger(__name__)

# SocketIO 인스턴스는 create_app에서 주입됨
socketio_instance: Optional[SocketIO] = None


def register_events(socketio: SocketIO) -> None:
    """
    WebSocket 이벤트 핸들러 등록

    Room 전략:
    - worker_{id}: 개인 room (특정 작업자에게 알림)
    - role_{role}: 역할별 room (MM, EE, PI, QI, SI 관리자들에게 알림)

    Args:
        socketio: Flask-SocketIO 인스턴스
    """
    global socketio_instance
    socketio_instance = socketio

    @socketio.on("connect")
    def handle_connect() -> None:
        """
        클라이언트 연결

        Query params:
            token: JWT 토큰 (선택)
        """
        try:
            # JWT 토큰 추출 (query param 또는 auth)
            token = request.args.get('token')
            if not token:
                auth = request.headers.get('Authorization', '')
                if auth.startswith('Bearer '):
                    token = auth[7:]

            if token:
                # JWT 검증 및 worker_id, role 추출
                payload = decode_jwt(token)
                worker_id = int(payload['sub'])
                role = payload.get('role')

                # 개인 room 조인
                worker_room = f"worker_{worker_id}"
                join_room(worker_room)
                logger.info(f"Worker {worker_id} joined room: {worker_room}")

                # 역할별 room 조인 (관리자는 추가 room)
                if role:
                    role_room = f"role_{role}"
                    join_room(role_room)
                    logger.info(f"Worker {worker_id} ({role}) joined room: {role_room}")

                emit("connected", {
                    "message": "Connected to server",
                    "worker_id": worker_id,
                    "role": role
                })
            else:
                emit("connected", {"message": "Connected to server (anonymous)"})

        except Exception as e:
            logger.error(f"Connect error: {e}")
            emit("error", {"message": "Authentication failed"})

    @socketio.on("disconnect")
    def handle_disconnect() -> None:
        """클라이언트 연결 해제"""
        logger.info("Client disconnected")

    @socketio.on("join")
    def handle_join(data: Dict[str, Any]) -> None:
        """
        특정 room 조인 (수동)

        Args:
            data: {"room": str}
        """
        room = data.get('room')
        if room:
            join_room(room)
            logger.info(f"Client joined room: {room}")
            emit("joined", {"room": room})

    @socketio.on("leave")
    def handle_leave(data: Dict[str, Any]) -> None:
        """
        특정 room 퇴장 (수동)

        Args:
            data: {"room": str}
        """
        room = data.get('room')
        if room:
            leave_room(room)
            logger.info(f"Client left room: {room}")
            emit("left", {"room": room})


def emit_task_completed(serial_number: str, task_category: str, worker_id: int) -> None:
    """
    작업 완료 이벤트 브로드캐스트 (서버 → 클라이언트)

    Args:
        serial_number: 시리얼 번호
        task_category: Task 카테고리 (MM, EE, TM, PI, QI, SI)
        worker_id: 작업자 ID
    """
    if not socketio_instance:
        logger.warning("SocketIO not initialized")
        return

    data = {
        "serial_number": serial_number,
        "task_category": task_category,
        "worker_id": worker_id
    }

    socketio_instance.emit("task_completed", data, broadcast=True)
    logger.info(f"Emitted task_completed: {data}")


def emit_process_alert(alert_data: Dict[str, Any]) -> None:
    """
    공정 알림 이벤트 브로드캐스트 (role 기반 room)

    Args:
        alert_data: {
            "alert_id": int,
            "alert_type": str,
            "serial_number": str,
            "message": str,
            "target_role": str (optional)
        }
    """
    if not socketio_instance:
        logger.warning("SocketIO not initialized")
        return

    target_role = alert_data.get('target_role')
    if target_role:
        # 특정 역할의 관리자들에게만 전송
        room = f"role_{target_role}"
        socketio_instance.emit("process_alert", alert_data, room=room)
        logger.info(f"Emitted process_alert to room {room}: {alert_data}")
    else:
        # 모든 관리자에게 브로드캐스트
        socketio_instance.emit("process_alert", alert_data, broadcast=True)
        logger.info(f"Emitted process_alert (broadcast): {alert_data}")


def emit_new_alert(worker_id: int, alert_data: Dict[str, Any]) -> None:
    """
    새 알림 이벤트 전송 (특정 worker room)

    Args:
        worker_id: 대상 작업자 ID
        alert_data: {
            "alert_id": int,
            "alert_type": str,
            "serial_number": str,
            "qr_doc_id": str,
            "message": str,
            "created_at": str
        }
    """
    if not socketio_instance:
        logger.warning("SocketIO not initialized")
        return

    room = f"worker_{worker_id}"
    socketio_instance.emit("new_alert", alert_data, room=room)
    logger.info(f"Emitted new_alert to worker {worker_id}: {alert_data}")
