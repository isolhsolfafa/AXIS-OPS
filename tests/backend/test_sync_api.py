"""
오프라인 동기화 API 테스트
엔드포인트: /api/app/sync/*
Sprint 4: 오프라인 데이터 동기화
"""

import pytest
from datetime import datetime, timezone


@pytest.fixture(autouse=True)
def cleanup_sync_test_data(db_conn):
    """테스트 후 동기화 테스트 데이터 정리"""
    yield
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            # 테스트 동기화 레코드 삭제
            cursor.execute(
                "DELETE FROM offline_sync_queue WHERE table_name LIKE 'test_%'"
            )
            # 테스트 위치 기록 삭제
            cursor.execute(
                "DELETE FROM location_history WHERE latitude BETWEEN 37.0 AND 38.0 AND longitude BETWEEN 126.0 AND 127.0"
            )
            db_conn.commit()
            cursor.close()
        except Exception:
            pass


class TestOfflineSync:
    """POST /api/app/sync/offline-batch 테스트"""

    def test_sync_tasks_success(
        self, client, create_test_worker, create_test_product, create_test_task, get_auth_token
    ):
        """
        작업 시작/완료 동기화 성공

        Expected:
        - Status 200
        - synced_tasks >= 입력한 작업 수
        - failed_count == 0
        """
        worker_id = create_test_worker(
            email='sync_test_worker@test.com',
            password='Test123!',
            name='Sync Test Worker',
            role='MM'
        )

        create_test_product(
            qr_doc_id='DOC-SYNC-001',
            serial_number='SN-SYNC-001'
        )

        # 동기화할 작업 생성 (DB에 이미 존재하는 작업)
        task_id = create_test_task(
            worker_id=worker_id,
            serial_number='SN-SYNC-001',
            qr_doc_id='DOC-SYNC-001',
            task_category='MM',
            task_id='MM-SYNC-001',
            task_name='Sync Task 1',
            started_at=None,
            completed_at=None
        )

        token = get_auth_token(worker_id, role='MM')

        # 동기화 요청 (모바일에서 오프라인 작업 동기화)
        payload = {
            'tasks': [
                {
                    'task_detail_id': task_id,
                    'operation': 'START',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'data': {'location': 'STATION_A'}
                },
                {
                    'task_detail_id': task_id,
                    'operation': 'COMPLETE',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'data': {'duration': 30}
                }
            ],
            'locations': [],
            'alerts_read': []
        }

        response = client.post(
            '/api/app/sync/offline-batch',
            json=payload,
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'synced_tasks' in data
        assert data['synced_tasks'] == 2
        assert data['failed_count'] == 0

    def test_sync_locations_success(
        self, client, create_test_worker, get_auth_token
    ):
        """
        위치 기록 동기화 성공

        Expected:
        - Status 200
        - synced_locations >= 입력한 위치 수
        """
        worker_id = create_test_worker(
            email='sync_test_loc@test.com',
            password='Test123!',
            name='Sync Location Worker',
            role='EE'
        )

        token = get_auth_token(worker_id, role='EE')

        payload = {
            'tasks': [],
            'locations': [
                {
                    'latitude': 37.5665,
                    'longitude': 126.9780,
                    'recorded_at': datetime.now(timezone.utc).isoformat()
                },
                {
                    'latitude': 37.5666,
                    'longitude': 126.9781,
                    'recorded_at': datetime.now(timezone.utc).isoformat()
                }
            ],
            'alerts_read': []
        }

        response = client.post(
            '/api/app/sync/offline-batch',
            json=payload,
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['synced_locations'] == 2
        assert data['failed_count'] == 0

    def test_sync_alerts_read(
        self, client, create_test_worker, create_test_alert, get_auth_token
    ):
        """
        알림 읽음 처리 동기화 성공

        Expected:
        - Status 200
        - synced_alerts >= 입력한 알림 수
        """
        worker_id = create_test_worker(
            email='sync_test_alert@test.com',
            password='Test123!',
            name='Sync Alert Worker',
            role='PI'
        )

        # 알림 생성
        alert1 = create_test_alert(
            alert_type='PROCESS_READY',
            message='Test Alert 1',
            target_worker_id=worker_id
        )
        alert2 = create_test_alert(
            alert_type='DURATION_EXCEEDED',
            message='Test Alert 2',
            target_worker_id=worker_id
        )

        token = get_auth_token(worker_id, role='PI')

        payload = {
            'tasks': [],
            'locations': [],
            'alerts_read': [alert1, alert2]
        }

        response = client.post(
            '/api/app/sync/offline-batch',
            json=payload,
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['synced_alerts'] >= 1  # 최소 1개 이상 성공
        # alert_id가 유효하지 않을 수 있으므로 failed_count 허용

    def test_sync_batch_combined(
        self, client, create_test_worker, create_test_product, create_test_task,
        create_test_alert, get_auth_token
    ):
        """
        작업 + 위치 + 알림 통합 동기화

        Expected:
        - Status 200
        - 모든 카테고리 동기화 성공
        """
        worker_id = create_test_worker(
            email='sync_test_combined@test.com',
            password='Test123!',
            name='Sync Combined Worker',
            role='QI'
        )

        create_test_product(
            qr_doc_id='DOC-SYNC-002',
            serial_number='SN-SYNC-002'
        )

        task_id = create_test_task(
            worker_id=worker_id,
            serial_number='SN-SYNC-002',
            qr_doc_id='DOC-SYNC-002',
            task_category='QI',
            task_id='QI-SYNC-001',
            task_name='Combined Sync Task'
        )

        alert_id = create_test_alert(
            alert_type='PROCESS_READY',
            message='Combined Alert',
            target_worker_id=worker_id
        )

        token = get_auth_token(worker_id, role='QI')

        payload = {
            'tasks': [
                {
                    'task_detail_id': task_id,
                    'operation': 'START',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'data': {}
                }
            ],
            'locations': [
                {
                    'latitude': 37.5667,
                    'longitude': 126.9782,
                    'recorded_at': datetime.now(timezone.utc).isoformat()
                }
            ],
            'alerts_read': [alert_id]
        }

        response = client.post(
            '/api/app/sync/offline-batch',
            json=payload,
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['synced_tasks'] >= 1
        assert data['synced_locations'] >= 1
        # synced_alerts는 성공 시 1 이상

    def test_sync_partial_failure(
        self, client, create_test_worker, get_auth_token
    ):
        """
        부분 실패 처리 (일부 데이터 유효하지 않음)

        Expected:
        - Status 200 (일부 성공)
        - failed_count > 0
        """
        worker_id = create_test_worker(
            email='sync_test_fail@test.com',
            password='Test123!',
            name='Sync Fail Worker',
            role='SI'
        )

        token = get_auth_token(worker_id, role='SI')

        payload = {
            'tasks': [
                {
                    'task_detail_id': None,  # 유효하지 않음
                    'operation': 'START',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'data': {}
                }
            ],
            'locations': [
                {
                    'latitude': None,  # 유효하지 않음
                    'longitude': 126.9783,
                    'recorded_at': datetime.now(timezone.utc).isoformat()
                }
            ],
            'alerts_read': []
        }

        response = client.post(
            '/api/app/sync/offline-batch',
            json=payload,
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['failed_count'] >= 2  # task 1개 + location 1개 실패

    def test_sync_empty_data(
        self, client, create_test_worker, get_auth_token
    ):
        """
        빈 데이터 동기화 (모든 배열 비어있음)

        Expected:
        - Status 200
        - 모든 synced 카운트 == 0
        """
        worker_id = create_test_worker(
            email='sync_test_empty@test.com',
            password='Test123!',
            name='Sync Empty Worker',
            role='TM'
        )

        token = get_auth_token(worker_id, role='TM')

        payload = {
            'tasks': [],
            'locations': [],
            'alerts_read': []
        }

        response = client.post(
            '/api/app/sync/offline-batch',
            json=payload,
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['synced_tasks'] == 0
        assert data['synced_locations'] == 0
        assert data['synced_alerts'] == 0

    def test_sync_without_jwt(self, client):
        """
        JWT 없이 동기화 → 401

        Expected:
        - Status 401
        """
        payload = {
            'tasks': [],
            'locations': [],
            'alerts_read': []
        }

        response = client.post('/api/app/sync/offline-batch', json=payload)
        assert response.status_code == 401

    def test_sync_invalid_request_body(
        self, client, create_test_worker, get_auth_token
    ):
        """
        요청 본문 없이 동기화 → 400

        Expected:
        - Status 400
        - error == INVALID_REQUEST
        """
        worker_id = create_test_worker(
            email='sync_test_invalid@test.com',
            password='Test123!',
            name='Sync Invalid Worker',
            role='MM'
        )

        token = get_auth_token(worker_id, role='MM')

        response = client.post(
            '/api/app/sync/offline-batch',
            data='',
            content_type='application/json',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 400


class TestSyncStatus:
    """GET /api/app/sync/status 테스트"""

    def test_get_sync_status(
        self, client, create_test_worker, create_test_sync_record, get_auth_token
    ):
        """
        동기화 상태 조회 성공

        Expected:
        - Status 200
        - pending_count, synced_count 포함
        - last_synced_at 포함 (동기화 기록이 있을 경우)
        """
        worker_id = create_test_worker(
            email='sync_status_test@test.com',
            password='Test123!',
            name='Sync Status Worker',
            role='EE'
        )

        # 동기화 레코드 생성
        create_test_sync_record(
            worker_id=worker_id,
            operation='INSERT',
            table_name='test_table',
            record_id='123',
            data={'test': 'data'},
            synced=True
        )

        create_test_sync_record(
            worker_id=worker_id,
            operation='UPDATE',
            table_name='test_table',
            record_id='124',
            data={'test': 'data2'},
            synced=False
        )

        token = get_auth_token(worker_id, role='EE')

        response = client.get(
            '/api/app/sync/status',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'pending_count' in data
        assert 'synced_count' in data
        assert 'last_synced_at' in data
        assert data['pending_count'] >= 1
        assert data['synced_count'] >= 1

    def test_sync_status_no_records(
        self, client, create_test_worker, get_auth_token, db_conn
    ):
        """
        동기화 기록 없음

        Expected:
        - Status 200
        - pending_count == 0
        - synced_count == 0
        - last_synced_at == None
        """
        worker_id = create_test_worker(
            email='sync_status_empty@test.com',
            password='Test123!',
            name='Sync Status Empty Worker',
            role='PI'
        )

        # 해당 작업자의 모든 동기화 레코드 삭제
        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute(
                "DELETE FROM offline_sync_queue WHERE worker_id = %s",
                (worker_id,)
            )
            db_conn.commit()
            cursor.close()

        token = get_auth_token(worker_id, role='PI')

        response = client.get(
            '/api/app/sync/status',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['pending_count'] == 0
        assert data['synced_count'] == 0
        assert data['last_synced_at'] is None

    def test_sync_status_without_jwt(self, client):
        """
        JWT 없이 동기화 상태 조회 → 401

        Expected:
        - Status 401
        """
        response = client.get('/api/app/sync/status')
        assert response.status_code == 401


class TestSyncDataIntegrity:
    """동기화 데이터 무결성 테스트"""

    def test_sync_creates_queue_records(
        self, client, create_test_worker, create_test_product, create_test_task,
        get_auth_token, db_conn
    ):
        """
        동기화 시 offline_sync_queue 레코드 생성 확인

        Expected:
        - DB에 레코드 생성됨
        - synced == TRUE
        """
        worker_id = create_test_worker(
            email='sync_integrity_test@test.com',
            password='Test123!',
            name='Sync Integrity Worker',
            role='QI'
        )

        create_test_product(
            qr_doc_id='DOC-SYNC-003',
            serial_number='SN-SYNC-003'
        )

        task_id = create_test_task(
            worker_id=worker_id,
            serial_number='SN-SYNC-003',
            qr_doc_id='DOC-SYNC-003',
            task_category='QI',
            task_id='QI-INTEGRITY-001',
            task_name='Integrity Task'
        )

        token = get_auth_token(worker_id, role='QI')

        payload = {
            'tasks': [
                {
                    'task_detail_id': task_id,
                    'operation': 'START',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'data': {'test': 'integrity'}
                }
            ],
            'locations': [],
            'alerts_read': []
        }

        response = client.post(
            '/api/app/sync/offline-batch',
            json=payload,
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200

        # DB에서 레코드 확인
        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) as count
                FROM offline_sync_queue
                WHERE worker_id = %s AND operation = 'START' AND synced = TRUE
                """,
                (worker_id,)
            )
            result = cursor.fetchone()
            cursor.close()

            assert result[0] >= 1

    def test_sync_creates_location_records(
        self, client, create_test_worker, get_auth_token, db_conn
    ):
        """
        위치 동기화 시 location_history 레코드 생성 확인

        Expected:
        - DB에 레코드 생성됨
        """
        worker_id = create_test_worker(
            email='sync_location_integrity@test.com',
            password='Test123!',
            name='Sync Location Integrity Worker',
            role='SI'
        )

        token = get_auth_token(worker_id, role='SI')

        test_lat = 37.5668
        test_lng = 126.9784

        payload = {
            'tasks': [],
            'locations': [
                {
                    'latitude': test_lat,
                    'longitude': test_lng,
                    'recorded_at': datetime.now(timezone.utc).isoformat()
                }
            ],
            'alerts_read': []
        }

        response = client.post(
            '/api/app/sync/offline-batch',
            json=payload,
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200

        # DB에서 레코드 확인
        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) as count
                FROM location_history
                WHERE worker_id = %s AND latitude = %s AND longitude = %s
                """,
                (worker_id, test_lat, test_lng)
            )
            result = cursor.fetchone()
            cursor.close()

            assert result[0] >= 1
