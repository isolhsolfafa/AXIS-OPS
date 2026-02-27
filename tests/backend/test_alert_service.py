"""
알림 API 테스트
엔드포인트: /api/app/alerts/*
Sprint 3: 알림 목록 조회 + 읽음 처리 + 안 읽은 알림 개수
"""

import pytest
from datetime import datetime, timezone


class TestGetAlerts:
    """GET /api/app/alerts 테스트"""

    def test_get_alerts_success(
        self, client, create_test_worker, create_test_alert, get_auth_token
    ):
        """
        알림 목록 조회 성공

        Expected:
        - Status 200
        - alerts 배열에 생성된 알림 포함
        - total, unread_count, page, limit 필드 포함
        """
        worker_id = create_test_worker(
            email='alert_get@test.com', password='Test123!',
            name='Alert Get Worker', role='MECH'
        )

        create_test_alert(
            alert_type='PROCESS_READY',
            message='[SN-ALERT-001] MECH 공정 미완료',
            serial_number='SN-ALERT-001',
            qr_doc_id='DOC-ALERT-001',
            target_worker_id=worker_id,
            target_role='MECH'
        )
        create_test_alert(
            alert_type='DURATION_EXCEEDED',
            message='[SN-ALERT-001] 작업 시간 초과',
            serial_number='SN-ALERT-001',
            qr_doc_id='DOC-ALERT-001',
            target_worker_id=worker_id,
            target_role='MECH'
        )

        token = get_auth_token(worker_id, role='MECH')
        response = client.get(
            '/api/app/alerts',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'alerts' in data
        assert data['total'] >= 2
        assert 'unread_count' in data
        assert data['page'] == 1
        assert data['limit'] == 50

    def test_get_alerts_empty(
        self, client, create_test_worker, get_auth_token
    ):
        """
        알림 없는 워커 조회

        Expected:
        - Status 200
        - alerts 빈 배열
        - total == 0
        """
        worker_id = create_test_worker(
            email='alert_empty@test.com', password='Test123!',
            name='Alert Empty Worker', role='ELEC'
        )

        token = get_auth_token(worker_id, role='ELEC')
        response = client.get(
            '/api/app/alerts',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['alerts'] == []
        assert data['total'] == 0

    def test_get_alerts_unread_only(
        self, client, create_test_worker, create_test_alert, get_auth_token, db_conn
    ):
        """
        unread_only=true 필터 테스트

        Expected:
        - Status 200
        - 읽지 않은 알림만 반환
        """
        worker_id = create_test_worker(
            email='alert_unread@test.com', password='Test123!',
            name='Alert Unread Worker', role='MECH'
        )

        alert1 = create_test_alert(
            alert_type='PROCESS_READY',
            message='[SN-ALERT-002] 읽을 알림',
            serial_number='SN-ALERT-002',
            target_worker_id=worker_id
        )
        alert2 = create_test_alert(
            alert_type='DURATION_EXCEEDED',
            message='[SN-ALERT-002] 안 읽은 알림',
            serial_number='SN-ALERT-002',
            target_worker_id=worker_id
        )

        # alert1을 읽음 처리 (DB 직접)
        cursor = db_conn.cursor()
        cursor.execute(
            "UPDATE app_alert_logs SET is_read = TRUE WHERE id = %s",
            (alert1,)
        )
        db_conn.commit()
        cursor.close()

        token = get_auth_token(worker_id, role='MECH')
        response = client.get(
            '/api/app/alerts?unread_only=true',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['alerts']) == 1
        assert data['alerts'][0]['id'] == alert2

    def test_get_alerts_unauthorized(self, client):
        """
        JWT 없이 알림 조회 → 401

        Expected:
        - Status 401
        """
        response = client.get('/api/app/alerts')
        assert response.status_code == 401


class TestMarkAlertRead:
    """PUT /api/app/alerts/<id>/read 테스트"""

    def test_mark_read_success(
        self, client, create_test_worker, create_test_alert, get_auth_token
    ):
        """
        개별 알림 읽음 처리 성공

        Expected:
        - Status 200
        - 읽음 처리 확인 메시지
        """
        worker_id = create_test_worker(
            email='mark_read@test.com', password='Test123!',
            name='Mark Read Worker', role='MECH'
        )

        alert_id = create_test_alert(
            alert_type='PROCESS_READY',
            message='[SN-ALERT-003] 읽을 알림',
            serial_number='SN-ALERT-003',
            target_worker_id=worker_id
        )

        token = get_auth_token(worker_id, role='MECH')
        response = client.put(
            f'/api/app/alerts/{alert_id}/read',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert '읽음' in data['message']

    def test_mark_read_not_owner(
        self, client, create_test_worker, create_test_alert, get_auth_token
    ):
        """
        다른 워커의 알림 읽음 처리 → 404

        Expected:
        - Status 404 (NOT_FOUND_OR_FORBIDDEN)
        """
        owner_id = create_test_worker(
            email='alert_owner@test.com', password='Test123!',
            name='Alert Owner', role='MECH'
        )
        other_id = create_test_worker(
            email='alert_other@test.com', password='Test123!',
            name='Alert Other', role='ELEC'
        )

        alert_id = create_test_alert(
            alert_type='PROCESS_READY',
            message='[SN-ALERT-004] Owner 전용',
            serial_number='SN-ALERT-004',
            target_worker_id=owner_id
        )

        token = get_auth_token(other_id, role='ELEC')
        response = client.put(
            f'/api/app/alerts/{alert_id}/read',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 404

    def test_mark_read_not_found(
        self, client, create_test_worker, get_auth_token
    ):
        """
        존재하지 않는 알림 읽음 처리 → 404

        Expected:
        - Status 404
        """
        worker_id = create_test_worker(
            email='alert_nf@test.com', password='Test123!',
            name='Alert NF Worker', role='MECH'
        )

        token = get_auth_token(worker_id, role='MECH')
        response = client.put(
            '/api/app/alerts/999999/read',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 404


class TestMarkAllRead:
    """PUT /api/app/alerts/read-all 테스트"""

    def test_mark_all_read_success(
        self, client, create_test_worker, create_test_alert, get_auth_token
    ):
        """
        전체 읽음 처리 성공

        Expected:
        - Status 200
        - count == 생성한 알림 수
        """
        worker_id = create_test_worker(
            email='readall@test.com', password='Test123!',
            name='ReadAll Worker', role='PI'
        )

        for i in range(3):
            create_test_alert(
                alert_type='PROCESS_READY',
                message=f'[SN-ALERT-005] 알림 {i}',
                serial_number='SN-ALERT-005',
                target_worker_id=worker_id
            )

        token = get_auth_token(worker_id, role='PI')
        response = client.put(
            '/api/app/alerts/read-all',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 3

    def test_mark_all_read_empty(
        self, client, create_test_worker, get_auth_token
    ):
        """
        읽을 알림 없을 때

        Expected:
        - Status 200
        - count == 0
        """
        worker_id = create_test_worker(
            email='readall_empty@test.com', password='Test123!',
            name='ReadAll Empty Worker', role='QI'
        )

        token = get_auth_token(worker_id, role='QI')
        response = client.put(
            '/api/app/alerts/read-all',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 0


class TestGetUnreadCount:
    """GET /api/app/alerts/unread-count 테스트"""

    def test_unread_count_with_alerts(
        self, client, create_test_worker, create_test_alert, get_auth_token
    ):
        """
        안 읽은 알림 개수 조회

        Expected:
        - Status 200
        - unread_count == 생성한 알림 수
        """
        worker_id = create_test_worker(
            email='unreadcount@test.com', password='Test123!',
            name='UnreadCount Worker', role='MECH'
        )

        create_test_alert(
            alert_type='PROCESS_READY',
            message='[SN-ALERT-006] 알림 1',
            serial_number='SN-ALERT-006',
            target_worker_id=worker_id
        )
        create_test_alert(
            alert_type='DURATION_EXCEEDED',
            message='[SN-ALERT-006] 알림 2',
            serial_number='SN-ALERT-006',
            target_worker_id=worker_id
        )

        token = get_auth_token(worker_id, role='MECH')
        response = client.get(
            '/api/app/alerts/unread-count',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['unread_count'] == 2

    def test_unread_count_zero(
        self, client, create_test_worker, get_auth_token
    ):
        """
        알림 없을 때 0

        Expected:
        - Status 200
        - unread_count == 0
        """
        worker_id = create_test_worker(
            email='zero_count@test.com', password='Test123!',
            name='Zero Count Worker', role='SI'
        )

        token = get_auth_token(worker_id, role='SI')
        response = client.get(
            '/api/app/alerts/unread-count',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['unread_count'] == 0
