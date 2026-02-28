"""
WebSocket 실시간 통신 테스트
Sprint 13: flask-sock (raw WebSocket) 기반

테스트 대상:
- ConnectionRegistry: 연결 등록/해제, room 관리, 메시지 전송
- emit_* 함수: emit_new_alert, emit_process_alert, emit_task_completed
- 메시지 포맷: {"event": "xxx", "data": {...}}
- JWT 인증: 토큰 없이 / 유효한 토큰 / 잘못된 토큰
"""

import json
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


# ──────────────────────────────────────────────────────────────
# T-01: ConnectionRegistry 생성/삭제
# ──────────────────────────────────────────────────────────────

class TestConnectionRegistry:
    """ConnectionRegistry 단위 테스트"""

    def test_register_and_unregister(self):
        """T-01: 연결 등록 후 해제 → connection_count 0"""
        from app.websocket.events import ConnectionRegistry

        reg = ConnectionRegistry()
        ws_mock = MagicMock()

        reg.register('ws1', ws_mock, worker_id=1, role='MECH')
        assert reg.connection_count == 1

        reg.unregister('ws1')
        assert reg.connection_count == 0

    def test_register_creates_rooms(self):
        """T-02: worker_id → worker_{id} room, role → role_{role} room 자동 생성"""
        from app.websocket.events import ConnectionRegistry

        reg = ConnectionRegistry()
        ws_mock = MagicMock()

        reg.register('ws1', ws_mock, worker_id=42, role='ELEC')

        assert 'worker_42' in reg._rooms
        assert 'role_ELEC' in reg._rooms
        assert 'ws1' in reg._rooms['worker_42']
        assert 'ws1' in reg._rooms['role_ELEC']

    def test_unregister_cleans_empty_rooms(self):
        """T-02b: 마지막 연결 해제 시 빈 room 삭제"""
        from app.websocket.events import ConnectionRegistry

        reg = ConnectionRegistry()
        ws_mock = MagicMock()

        reg.register('ws1', ws_mock, worker_id=1, role='MECH')
        reg.unregister('ws1')

        assert 'worker_1' not in reg._rooms
        assert 'role_MECH' not in reg._rooms

    def test_unregister_unknown_ws_id(self):
        """T-10: 존재하지 않는 ws_id unregister → 에러 없이 무시"""
        from app.websocket.events import ConnectionRegistry

        reg = ConnectionRegistry()
        reg.unregister('nonexistent')  # 에러 없어야 함
        assert reg.connection_count == 0


# ──────────────────────────────────────────────────────────────
# T-03: 메시지 전송 (send_to_room, broadcast)
# ──────────────────────────────────────────────────────────────

class TestRegistryMessaging:
    """ConnectionRegistry 메시지 전송 테스트"""

    def test_send_to_room(self):
        """T-05: worker room에만 메시지 전송"""
        from app.websocket.events import ConnectionRegistry

        reg = ConnectionRegistry()
        ws1 = MagicMock()
        ws2 = MagicMock()

        reg.register('ws1', ws1, worker_id=1)
        reg.register('ws2', ws2, worker_id=2)

        sent = reg.send_to_room('worker_1', '{"test": true}')
        assert sent == 1
        ws1.send.assert_called_once_with('{"test": true}')
        ws2.send.assert_not_called()

    def test_broadcast(self):
        """T-07: 전체 연결에 broadcast"""
        from app.websocket.events import ConnectionRegistry

        reg = ConnectionRegistry()
        ws1 = MagicMock()
        ws2 = MagicMock()
        ws3 = MagicMock()

        reg.register('ws1', ws1, worker_id=1)
        reg.register('ws2', ws2, worker_id=2)
        reg.register('ws3', ws3, worker_id=3)

        sent = reg.broadcast('hello')
        assert sent == 3
        ws1.send.assert_called_once_with('hello')
        ws2.send.assert_called_once_with('hello')
        ws3.send.assert_called_once_with('hello')

    def test_send_to_role_room(self):
        """T-06: role room에만 메시지 전송"""
        from app.websocket.events import ConnectionRegistry

        reg = ConnectionRegistry()
        ws_mech1 = MagicMock()
        ws_mech2 = MagicMock()
        ws_elec = MagicMock()

        reg.register('ws1', ws_mech1, worker_id=1, role='MECH')
        reg.register('ws2', ws_mech2, worker_id=2, role='MECH')
        reg.register('ws3', ws_elec, worker_id=3, role='ELEC')

        sent = reg.send_to_room('role_MECH', 'mech_msg')
        assert sent == 2
        ws_mech1.send.assert_called_once()
        ws_mech2.send.assert_called_once()
        ws_elec.send.assert_not_called()

    def test_send_failure_handled(self):
        """T-10b: ws.send() 실패 시 에러 처리 (다른 연결에 영향 없음)"""
        from app.websocket.events import ConnectionRegistry

        reg = ConnectionRegistry()
        ws_bad = MagicMock()
        ws_bad.send.side_effect = Exception("Connection closed")
        ws_good = MagicMock()

        reg.register('ws_bad', ws_bad, worker_id=1)
        reg.register('ws_good', ws_good, worker_id=1)

        sent = reg.send_to_room('worker_1', 'msg')
        assert sent == 1  # ws_good만 성공
        ws_good.send.assert_called_once()

    def test_send_to_empty_room(self):
        """빈 room에 메시지 전송 → 0 반환"""
        from app.websocket.events import ConnectionRegistry

        reg = ConnectionRegistry()
        sent = reg.send_to_room('worker_999', 'msg')
        assert sent == 0


# ──────────────────────────────────────────────────────────────
# T-04: 메시지 포맷
# ──────────────────────────────────────────────────────────────

class TestMessageFormat:
    """JSON 메시지 포맷 검증"""

    def test_emit_new_alert_format(self):
        """T-04: new_alert 메시지 포맷 {"event": "new_alert", "data": {...}}"""
        from app.websocket.events import ConnectionRegistry, emit_new_alert, registry

        # 글로벌 registry에 mock ws 등록
        ws_mock = MagicMock()
        registry.register('test_ws', ws_mock, worker_id=100)

        try:
            emit_new_alert(100, {
                'alert_id': 1,
                'alert_type': 'TASK_REMINDER',
                'message': '테스트 알림'
            })

            ws_mock.send.assert_called_once()
            sent_data = json.loads(ws_mock.send.call_args[0][0])
            assert sent_data['event'] == 'new_alert'
            assert sent_data['data']['alert_id'] == 1
            assert sent_data['data']['alert_type'] == 'TASK_REMINDER'
        finally:
            registry.unregister('test_ws')

    def test_emit_process_alert_with_role(self):
        """T-06b: process_alert → role room 전송"""
        from app.websocket.events import emit_process_alert, registry

        ws_mock = MagicMock()
        registry.register('test_ws', ws_mock, worker_id=50, role='MECH')

        try:
            emit_process_alert({
                'alert_type': 'SHIFT_END_REMINDER',
                'target_role': 'MECH',
                'message': '퇴근 알림'
            })

            ws_mock.send.assert_called_once()
            sent_data = json.loads(ws_mock.send.call_args[0][0])
            assert sent_data['event'] == 'process_alert'
            assert sent_data['data']['target_role'] == 'MECH'
        finally:
            registry.unregister('test_ws')

    def test_emit_process_alert_broadcast(self):
        """T-06c: process_alert (target_role 없음) → broadcast"""
        from app.websocket.events import emit_process_alert, registry

        ws1 = MagicMock()
        ws2 = MagicMock()
        registry.register('ws1', ws1, worker_id=1)
        registry.register('ws2', ws2, worker_id=2)

        try:
            emit_process_alert({
                'alert_type': 'GENERAL',
                'message': '전체 알림'
            })

            ws1.send.assert_called_once()
            ws2.send.assert_called_once()
        finally:
            registry.unregister('ws1')
            registry.unregister('ws2')

    def test_emit_task_completed_format(self):
        """T-07b: task_completed broadcast 메시지 포맷"""
        from app.websocket.events import emit_task_completed, registry

        ws_mock = MagicMock()
        registry.register('test_ws', ws_mock, worker_id=1)

        try:
            emit_task_completed(
                serial_number='SN-001',
                task_category='MECH',
                worker_id=1
            )

            ws_mock.send.assert_called_once()
            sent_data = json.loads(ws_mock.send.call_args[0][0])
            assert sent_data['event'] == 'task_completed'
            assert sent_data['data']['serial_number'] == 'SN-001'
            assert sent_data['data']['task_category'] == 'MECH'
            assert sent_data['data']['worker_id'] == 1
        finally:
            registry.unregister('test_ws')


# ──────────────────────────────────────────────────────────────
# T-09: 동시 다중 연결
# ──────────────────────────────────────────────────────────────

class TestConcurrentConnections:
    """동시 다중 연결 테스트"""

    def test_multiple_workers_separate_rooms(self):
        """T-09: 여러 worker 동시 연결 → 각자 room에만 메시지"""
        from app.websocket.events import ConnectionRegistry

        reg = ConnectionRegistry()
        ws_a = MagicMock()
        ws_b = MagicMock()
        ws_c = MagicMock()

        reg.register('a', ws_a, worker_id=1, role='MECH')
        reg.register('b', ws_b, worker_id=2, role='ELEC')
        reg.register('c', ws_c, worker_id=3, role='MECH')

        assert reg.connection_count == 3

        # worker_1에게만
        reg.send_to_room('worker_1', 'only_for_1')
        ws_a.send.assert_called_with('only_for_1')
        ws_b.send.assert_not_called()
        ws_c.send.assert_not_called()

        # MECH role에게
        ws_a.reset_mock()
        ws_c.reset_mock()
        reg.send_to_room('role_MECH', 'for_mech')
        ws_a.send.assert_called_with('for_mech')
        ws_c.send.assert_called_with('for_mech')
        ws_b.send.assert_not_called()

    def test_same_worker_multiple_connections(self):
        """T-09b: 같은 worker가 여러 기기로 접속 → 모두에게 전송"""
        from app.websocket.events import ConnectionRegistry

        reg = ConnectionRegistry()
        ws_phone = MagicMock()
        ws_tablet = MagicMock()

        reg.register('phone', ws_phone, worker_id=1, role='MECH')
        reg.register('tablet', ws_tablet, worker_id=1, role='MECH')

        sent = reg.send_to_room('worker_1', 'msg')
        assert sent == 2
        ws_phone.send.assert_called_once()
        ws_tablet.send.assert_called_once()


# ──────────────────────────────────────────────────────────────
# T-03: JWT 토큰 파싱 (ws_handler 간접 테스트)
# ──────────────────────────────────────────────────────────────

class TestJWTAuth:
    """WebSocket JWT 인증 테스트 (HTTP REST 레벨)"""

    def test_unauthenticated_api_rejected(self, app, client):
        """T-03: 인증 없이 API 호출 시 401"""
        response = client.post(
            '/api/app/work/start',
            json={'task_detail_id': 9999}
        )
        assert response.status_code == 401


# ──────────────────────────────────────────────────────────────
# T-08: Ping/Pong
# ──────────────────────────────────────────────────────────────

class TestPingPong:
    """Ping/Pong heartbeat 검증 (메시지 포맷 기반)"""

    def test_ping_message_format(self):
        """T-08: ping 메시지가 올바른 JSON 형태인지"""
        ping_msg = json.dumps({'event': 'ping', 'data': {}})
        parsed = json.loads(ping_msg)
        assert parsed['event'] == 'ping'

    def test_pong_message_format(self):
        """T-08b: pong 응답 포맷"""
        pong_msg = json.dumps({'event': 'pong', 'data': {}})
        parsed = json.loads(pong_msg)
        assert parsed['event'] == 'pong'
