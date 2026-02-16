"""
작업 시간 검증 테스트
Sprint 3: complete_work → duration_validator 연동
엔드포인트: POST /api/app/work/complete (duration 검증 내장)
"""

import pytest
from datetime import datetime, timezone, timedelta


@pytest.fixture(autouse=True)
def cleanup_duration_alerts(db_conn):
    """테스트 후 duration 검증으로 생성된 알림 정리"""
    yield
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            cursor.execute(
                "DELETE FROM app_alert_logs WHERE serial_number LIKE 'SN-DUR%%'"
            )
            db_conn.commit()
            cursor.close()
        except Exception:
            pass


class TestNormalDuration:
    """정상 작업 시간 (1분 ~ 14시간)"""

    def test_normal_duration_no_warnings(
        self, client, create_test_worker, create_test_product,
        create_test_task, create_test_completion_status, get_auth_token
    ):
        """
        2시간 작업 → duration_warnings 없음

        Expected:
        - Status 200
        - completed_at 설정됨
        - duration_warnings 키가 없음 (경고 없으므로)
        """
        worker_id = create_test_worker(
            email='dur_normal@test.com', password='Test123!',
            name='Normal Duration Worker', role='MM'
        )

        create_test_product(
            qr_doc_id='DOC-DUR-001',
            serial_number='SN-DUR-001',
            model='GBWS-50'
        )

        create_test_completion_status(serial_number='SN-DUR-001')

        started_at = datetime.now(timezone.utc) - timedelta(hours=2)
        task_id = create_test_task(
            worker_id=worker_id,
            serial_number='SN-DUR-001',
            qr_doc_id='DOC-DUR-001',
            task_category='MM',
            task_id='CABINET_ASSY',
            task_name='캐비넷 조립',
            started_at=started_at
        )

        token = get_auth_token(worker_id, role='MM')
        response = client.post(
            '/api/app/work/complete',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['completed_at'] is not None
        assert 'duration_warnings' not in data


class TestExceededDuration:
    """14시간 초과 작업 시간"""

    def test_duration_over_14h(
        self, client, create_test_worker, create_test_product,
        create_test_task, create_test_completion_status, get_auth_token
    ):
        """
        15시간 작업 → DURATION_EXCEEDED 경고 + 관리자 알림 생성

        Expected:
        - Status 200
        - duration_warnings에 '초과' 메시지 포함
        """
        worker_id = create_test_worker(
            email='dur_exceeded@test.com', password='Test123!',
            name='Exceeded Duration Worker', role='MM'
        )

        # MM 관리자 생성 (알림 대상)
        create_test_worker(
            email='dur_mm_mgr@test.com', password='Test123!',
            name='MM Duration Manager', role='MM', is_manager=True
        )

        create_test_product(
            qr_doc_id='DOC-DUR-002',
            serial_number='SN-DUR-002',
            model='GBWS-50'
        )

        create_test_completion_status(serial_number='SN-DUR-002')

        # 15시간 전 시작
        started_at = datetime.now(timezone.utc) - timedelta(hours=15)
        task_id = create_test_task(
            worker_id=worker_id,
            serial_number='SN-DUR-002',
            qr_doc_id='DOC-DUR-002',
            task_category='MM',
            task_id='CABINET_ASSY',
            task_name='캐비넷 조립',
            started_at=started_at
        )

        token = get_auth_token(worker_id, role='MM')
        response = client.post(
            '/api/app/work/complete',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'duration_warnings' in data
        assert len(data['duration_warnings']) > 0
        assert any('초과' in w for w in data['duration_warnings'])


class TestShortDuration:
    """매우 짧은 작업 시간 (< 1분)"""

    def test_very_short_duration(
        self, client, create_test_worker, create_test_product,
        create_test_task, create_test_completion_status, get_auth_token
    ):
        """
        10초 작업 → 경고 (알림은 생성 안함)

        Expected:
        - Status 200
        - duration_warnings에 '짧' 메시지 포함
        """
        worker_id = create_test_worker(
            email='dur_short@test.com', password='Test123!',
            name='Short Duration Worker', role='EE'
        )

        create_test_product(
            qr_doc_id='DOC-DUR-003',
            serial_number='SN-DUR-003',
            model='GBWS-50'
        )

        create_test_completion_status(serial_number='SN-DUR-003')

        # 10초 전 시작
        started_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        task_id = create_test_task(
            worker_id=worker_id,
            serial_number='SN-DUR-003',
            qr_doc_id='DOC-DUR-003',
            task_category='EE',
            task_id='WIRING',
            task_name='배선 작업',
            started_at=started_at
        )

        token = get_auth_token(worker_id, role='EE')
        response = client.post(
            '/api/app/work/complete',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'duration_warnings' in data
        assert any('짧' in w for w in data['duration_warnings'])


class TestReverseDuration:
    """역순 시간 (completed_at < started_at)"""

    def test_reverse_completion(
        self, client, create_test_worker, create_test_product,
        create_test_task, create_test_completion_status, get_auth_token
    ):
        """
        started_at이 미래 → completed_at(now) < started_at
        → REVERSE_COMPLETION 경고 + 관리자 알림

        Expected:
        - Status 200
        - duration_warnings에 역전 경고 포함
        """
        worker_id = create_test_worker(
            email='dur_reverse@test.com', password='Test123!',
            name='Reverse Duration Worker', role='MM'
        )

        # MM 관리자 생성 (알림 대상)
        create_test_worker(
            email='dur_rev_mgr@test.com', password='Test123!',
            name='Reverse Manager', role='MM', is_manager=True
        )

        create_test_product(
            qr_doc_id='DOC-DUR-004',
            serial_number='SN-DUR-004',
            model='GBWS-50'
        )

        create_test_completion_status(serial_number='SN-DUR-004')

        # 1시간 후 (미래) started_at → complete 호출 시 completed_at(now) < started_at
        started_at = datetime.now(timezone.utc) + timedelta(hours=1)
        task_id = create_test_task(
            worker_id=worker_id,
            serial_number='SN-DUR-004',
            qr_doc_id='DOC-DUR-004',
            task_category='MM',
            task_id='CABINET_ASSY',
            task_name='캐비넷 조립',
            started_at=started_at
        )

        token = get_auth_token(worker_id, role='MM')
        response = client.post(
            '/api/app/work/complete',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'duration_warnings' in data
        assert any('시작 시간' in w or '이릅니다' in w for w in data['duration_warnings'])
