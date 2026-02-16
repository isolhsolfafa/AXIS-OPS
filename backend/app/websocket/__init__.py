"""
WebSocket 모듈
TODO: 연결 관리
TODO: 메시지 큐
"""

from typing import Any

from app.websocket.events import register_events

def init_websocket(socketio: Any) -> None:
    """
    WebSocket 이벤트 등록
    
    Args:
        socketio: Flask-SocketIO 인스턴스
    """
    # TODO: 이벤트 핸들러 등록
    register_events(socketio)
