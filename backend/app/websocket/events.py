"""
WebSocket 이벤트 핸들러 (raw WebSocket — flask-sock)
Sprint 13: Flask-SocketIO → flask-sock 마이그레이션
  - ConnectionRegistry: thread-safe 연결/room 관리
  - ws_handler: /ws 라우트 핸들러 (JWT 인증 + 메시지 루프)
  - emit_* 함수: 기존 시그니처 유지 (alert_service.py 호환)
"""

import json
import logging
import threading
import uuid
from typing import Any, Dict, List, Optional, Set

from app.middleware.jwt_auth import decode_jwt


logger = logging.getLogger(__name__)


class ConnectionRegistry:
    """
    Thread-safe WebSocket 연결 레지스트리

    구조:
      connections: { ws_id: { ws, worker_id, role, rooms } }
      rooms: { room_name: set(ws_id, ...) }
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._connections: Dict[str, Dict[str, Any]] = {}
        self._rooms: Dict[str, Set[str]] = {}

    def register(self, ws_id: str, ws: Any, worker_id: Optional[int] = None,
                 role: Optional[str] = None) -> None:
        """연결 등록 + 자동 room 조인"""
        with self._lock:
            rooms: Set[str] = set()

            if worker_id:
                worker_room = f"worker_{worker_id}"
                rooms.add(worker_room)
                self._rooms.setdefault(worker_room, set()).add(ws_id)

            if role:
                role_room = f"role_{role}"
                rooms.add(role_room)
                self._rooms.setdefault(role_room, set()).add(ws_id)

            self._connections[ws_id] = {
                'ws': ws,
                'worker_id': worker_id,
                'role': role,
                'rooms': rooms,
            }

        logger.info(f"WS registered: ws_id={ws_id}, worker_id={worker_id}, role={role}, rooms={rooms}")

    def unregister(self, ws_id: str) -> None:
        """연결 해제 + room 정리"""
        with self._lock:
            conn = self._connections.pop(ws_id, None)
            if conn:
                for room in conn.get('rooms', set()):
                    room_set = self._rooms.get(room)
                    if room_set:
                        room_set.discard(ws_id)
                        if not room_set:
                            del self._rooms[room]

        if conn:
            logger.info(f"WS unregistered: ws_id={ws_id}, worker_id={conn.get('worker_id')}")

    def send_to_room(self, room: str, message: str) -> int:
        """특정 room의 모든 연결에 메시지 전송. 전송 성공 수 반환."""
        sent = 0
        with self._lock:
            ws_ids = list(self._rooms.get(room, set()))
            targets = [(ws_id, self._connections[ws_id]['ws'])
                       for ws_id in ws_ids if ws_id in self._connections]

        for ws_id, ws in targets:
            try:
                ws.send(message)
                sent += 1
            except Exception as e:
                logger.warning(f"Send failed to ws_id={ws_id}: {e}")
        return sent

    def broadcast(self, message: str) -> int:
        """모든 연결에 메시지 전송. 전송 성공 수 반환."""
        sent = 0
        with self._lock:
            targets = [(ws_id, info['ws'])
                       for ws_id, info in self._connections.items()]

        for ws_id, ws in targets:
            try:
                ws.send(message)
                sent += 1
            except Exception as e:
                logger.warning(f"Broadcast failed to ws_id={ws_id}: {e}")
        return sent

    @property
    def connection_count(self) -> int:
        with self._lock:
            return len(self._connections)


# 전역 레지스트리 (앱 전체에서 공유)
registry = ConnectionRegistry()


def ws_handler(ws):
    """
    /ws 라우트 핸들러 (flask-sock)

    플로우:
    1. query param에서 JWT 토큰 추출
    2. worker_id, role 파싱 → registry 등록
    3. connected 이벤트 전송
    4. 메시지 수신 루프 (ping → pong)
    5. disconnect 시 registry 정리
    """
    from flask import request

    ws_id = str(uuid.uuid4())[:8]
    worker_id = None
    role = None

    try:
        # JWT 토큰 추출 (query param)
        token = request.args.get('token')
        if token:
            try:
                payload = decode_jwt(token)
                worker_id = int(payload['sub'])
                role = payload.get('role')
            except Exception as e:
                logger.warning(f"WS JWT decode failed: {e}")

        # 레지스트리 등록
        registry.register(ws_id, ws, worker_id=worker_id, role=role)

        # connected 이벤트 전송
        connected_msg = json.dumps({
            'event': 'connected',
            'data': {
                'message': 'Connected to server',
                'worker_id': worker_id,
                'role': role,
            }
        })
        ws.send(connected_msg)

        # 메시지 수신 루프
        while True:
            try:
                data = ws.receive(timeout=60)  # 60초 타임아웃
            except Exception:
                break  # 연결 종료

            if data is None:
                break  # 연결 종료

            # 메시지 파싱
            try:
                msg = json.loads(data) if isinstance(data, str) else {}
            except (json.JSONDecodeError, TypeError):
                msg = {}

            event = msg.get('event', '')

            # ping → pong
            if event == 'ping' or data == 'ping':
                try:
                    ws.send(json.dumps({'event': 'pong', 'data': {}}))
                except Exception:
                    break

    except Exception as e:
        logger.error(f"WS handler error: ws_id={ws_id}, error={e}")
    finally:
        registry.unregister(ws_id)


# ──────────────────────────────────────────────────────────────
# emit 함수들 (기존 시그니처 유지 — alert_service.py 호환)
# ──────────────────────────────────────────────────────────────

def emit_task_completed(serial_number: str, task_category: str, worker_id: int) -> None:
    """
    작업 완료 이벤트 브로드캐스트 (서버 → 전체 클라이언트)

    Args:
        serial_number: 시리얼 번호
        task_category: Task 카테고리
        worker_id: 작업자 ID
    """
    message = json.dumps({
        'event': 'task_completed',
        'data': {
            'serial_number': serial_number,
            'task_category': task_category,
            'worker_id': worker_id,
        }
    })
    sent = registry.broadcast(message)
    logger.info(f"Emitted task_completed: serial={serial_number}, sent={sent}")


def emit_process_alert(alert_data: Dict[str, Any]) -> None:
    """
    공정 알림 이벤트 (role 기반 room 또는 broadcast)

    Args:
        alert_data: alert_type, serial_number, message, target_role(optional) 등
    """
    message = json.dumps({
        'event': 'process_alert',
        'data': alert_data,
    })

    target_role = alert_data.get('target_role')
    if target_role:
        room = f"role_{target_role}"
        sent = registry.send_to_room(room, message)
        logger.info(f"Emitted process_alert to room {room}: sent={sent}")
    else:
        sent = registry.broadcast(message)
        logger.info(f"Emitted process_alert (broadcast): sent={sent}")


def emit_new_alert(worker_id: int, alert_data: Dict[str, Any]) -> None:
    """
    새 알림 이벤트 전송 (특정 worker room)

    Args:
        worker_id: 대상 작업자 ID
        alert_data: alert_id, alert_type, message 등
    """
    message = json.dumps({
        'event': 'new_alert',
        'data': alert_data,
    })

    room = f"worker_{worker_id}"
    sent = registry.send_to_room(room, message)
    logger.info(f"Emitted new_alert to worker {worker_id}: sent={sent}")
