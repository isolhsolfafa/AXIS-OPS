"""
관리자 API 테스트
엔드포인트: /api/admin/*
Sprint 4: 관리자 전용 API (승인, 대시보드, 작업 수정)
"""

import pytest
from datetime import datetime, timedelta, timezone


@pytest.fixture(autouse=True)
def cleanup_admin_test_data(db_conn):
    """테스트 후 관리자 테스트 데이터 정리"""
    yield
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            # 테스트 알림 삭제 (관리자 승인 알림)
            cursor.execute(
                "DELETE FROM app_alert_logs WHERE alert_type IN ('WORKER_APPROVED', 'WORKER_REJECTED')"
            )
            # 테스트 작업자 삭제 (SN-ADMIN- 접두사)
            cursor.execute(
                "DELETE FROM workers WHERE email LIKE 'admin_test_%@test.com'"
            )
            db_conn.commit()
            cursor.close()
        except Exception:
            pass


class TestWorkerApproval:
    """POST /api/admin/workers/approve 테스트"""

    def test_approve_worker_success(
        self, client, create_test_worker, create_test_admin, get_admin_auth_token
    ):
        """
        작업자 승인 성공

        Expected:
        - Status 200
        - message 포함
        - worker_id, status='approved' 반환
        - 알림 생성됨
        """
        # 승인 대기 작업자 생성
        pending_worker_id = create_test_worker(
            email='admin_test_pending1@test.com',
            password='Test123!',
            name='Pending Worker 1',
            role='MECH',
            approval_status='pending'
        )

        # 관리자 생성
        admin_data = create_test_admin
        token = get_admin_auth_token(admin_data['id'])

        response = client.post(
            '/api/admin/workers/approve',
            json={'worker_id': pending_worker_id, 'approved': True},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert '승인' in data['message']
        assert data['worker_id'] == pending_worker_id
        assert data['status'] == 'approved'

    def test_reject_worker_success(
        self, client, create_test_worker, create_test_admin, get_admin_auth_token
    ):
        """
        작업자 거부 성공

        Expected:
        - Status 200
        - status='rejected' 반환
        """
        pending_worker_id = create_test_worker(
            email='admin_test_pending2@test.com',
            password='Test123!',
            name='Pending Worker 2',
            role='ELEC',
            approval_status='pending'
        )

        admin_data = create_test_admin
        token = get_admin_auth_token(admin_data['id'])

        response = client.post(
            '/api/admin/workers/approve',
            json={'worker_id': pending_worker_id, 'approved': False},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert '거부' in data['message']
        assert data['status'] == 'rejected'

    def test_approve_nonexistent_worker(
        self, client, create_test_admin, get_admin_auth_token
    ):
        """
        존재하지 않는 작업자 승인 → 404

        Expected:
        - Status 404
        - error == WORKER_NOT_FOUND
        """
        admin_data = create_test_admin
        token = get_admin_auth_token(admin_data['id'])

        response = client.post(
            '/api/admin/workers/approve',
            json={'worker_id': 999999, 'approved': True},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data['error'] == 'WORKER_NOT_FOUND'

    def test_approve_without_admin(
        self, client, create_test_worker, get_auth_token
    ):
        """
        비관리자 접근 → 403

        Expected:
        - Status 403
        - error == FORBIDDEN
        """
        # 일반 작업자 (is_admin=False)
        worker_id = create_test_worker(
            email='admin_test_nonadmin@test.com',
            password='Test123!',
            name='Non Admin',
            role='MECH',
            is_admin=False
        )

        token = get_auth_token(worker_id, role='MECH')

        response = client.post(
            '/api/admin/workers/approve',
            json={'worker_id': 1, 'approved': True},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 403
        data = response.get_json()
        assert data['error'] == 'FORBIDDEN'

    def test_approve_without_jwt(self, client):
        """
        JWT 없이 접근 → 401

        Expected:
        - Status 401
        """
        response = client.post(
            '/api/admin/workers/approve',
            json={'worker_id': 1, 'approved': True}
        )

        assert response.status_code == 401


class TestPendingWorkers:
    """GET /api/admin/workers/pending 테스트"""

    def test_get_pending_workers(
        self, client, create_test_worker, create_test_admin, get_admin_auth_token
    ):
        """
        승인 대기 작업자 목록 조회

        Expected:
        - Status 200
        - workers 배열 포함
        - total >= 생성한 작업자 수
        """
        # 승인 대기 작업자 2명 생성
        create_test_worker(
            email='admin_test_pending3@test.com',
            password='Test123!',
            name='Pending Worker 3',
            role='PI',
            approval_status='pending'
        )
        create_test_worker(
            email='admin_test_pending4@test.com',
            password='Test123!',
            name='Pending Worker 4',
            role='QI',
            approval_status='pending'
        )

        admin_data = create_test_admin
        token = get_admin_auth_token(admin_data['id'])

        response = client.get(
            '/api/admin/workers/pending',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'workers' in data
        assert 'total' in data
        assert data['total'] >= 2

    def test_get_pending_workers_empty(
        self, client, create_test_admin, get_admin_auth_token, db_conn
    ):
        """
        승인 대기 작업자 없음

        Expected:
        - Status 200
        - workers 빈 배열 또는 total == 0
        """
        admin_data = create_test_admin
        token = get_admin_auth_token(admin_data['id'])

        # 모든 pending 작업자 승인 처리
        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute(
                "UPDATE workers SET approval_status = 'approved' WHERE approval_status = 'pending'"
            )
            db_conn.commit()
            cursor.close()

        response = client.get(
            '/api/admin/workers/pending',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        # total == 0 OR workers 빈 배열
        assert data['total'] == 0 or len(data['workers']) == 0

    def test_get_pending_workers_pagination(
        self, client, create_test_admin, get_admin_auth_token
    ):
        """
        페이지네이션 파라미터 테스트

        Expected:
        - Status 200
        - limit 파라미터 적용됨
        """
        admin_data = create_test_admin
        token = get_admin_auth_token(admin_data['id'])

        response = client.get(
            '/api/admin/workers/pending?limit=5',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['workers']) <= 5


class TestWorkersList:
    """GET /api/admin/workers 테스트"""

    def test_get_workers_with_filter(
        self, client, create_test_worker, create_test_admin, get_admin_auth_token
    ):
        """
        작업자 목록 조회 (필터링)

        Expected:
        - Status 200
        - approval_status, role 필터 적용
        """
        # 승인된 MECH 작업자 생성
        create_test_worker(
            email='admin_test_mech_approved@test.com',
            password='Test123!',
            name='MECH Approved Worker',
            role='MECH',
            approval_status='approved'
        )

        admin_data = create_test_admin
        token = get_admin_auth_token(admin_data['id'])

        response = client.get(
            '/api/admin/workers?approval_status=approved&role=MECH',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'workers' in data
        assert data['total'] >= 1


class TestAdminDashboard:
    """관리자 대시보드 API 테스트"""

    def test_get_process_summary(
        self, client, create_test_admin, create_test_worker, create_test_product,
        create_test_task, get_admin_auth_token
    ):
        """
        공정별 작업 요약 조회

        Expected:
        - Status 200
        - summary 배열 포함
        - date 필드 포함
        """
        # 테스트 데이터 생성
        worker_id = create_test_worker(
            email='admin_test_dashboard@test.com',
            password='Test123!',
            name='Dashboard Worker',
            role='MECH'
        )

        create_test_product(
            qr_doc_id='DOC-ADMIN-001',
            serial_number='SN-ADMIN-001'
        )

        create_test_task(
            worker_id=worker_id,
            serial_number='SN-ADMIN-001',
            qr_doc_id='DOC-ADMIN-001',
            task_category='MECH',
            task_id='MM-001',
            task_name='Test Task',
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc)
        )

        admin_data = create_test_admin
        token = get_admin_auth_token(admin_data['id'])

        response = client.get(
            '/api/admin/dashboard/process-summary',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'summary' in data
        assert 'date' in data

    def test_get_active_tasks(
        self, client, create_test_admin, create_test_worker, create_test_product,
        create_test_task, get_admin_auth_token
    ):
        """
        현재 진행 중인 작업 목록 조회

        Expected:
        - Status 200
        - tasks 배열 포함
        - 진행 중인 작업 (started_at != NULL, completed_at == NULL)
        """
        worker_id = create_test_worker(
            email='admin_test_active@test.com',
            password='Test123!',
            name='Active Worker',
            role='ELEC'
        )

        create_test_product(
            qr_doc_id='DOC-ADMIN-002',
            serial_number='SN-ADMIN-002'
        )

        # 진행 중인 작업 생성
        create_test_task(
            worker_id=worker_id,
            serial_number='SN-ADMIN-002',
            qr_doc_id='DOC-ADMIN-002',
            task_category='ELEC',
            task_id='EE-001',
            task_name='Active Task',
            started_at=datetime.now(timezone.utc),
            completed_at=None  # 진행 중
        )

        admin_data = create_test_admin
        token = get_admin_auth_token(admin_data['id'])

        response = client.get(
            '/api/admin/dashboard/active-tasks',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'tasks' in data
        assert 'total' in data

    def test_get_alerts_summary(
        self, client, create_test_admin, get_admin_auth_token
    ):
        """
        알림 요약 통계 조회

        Expected:
        - Status 200
        - summary.total, summary.unread, summary.by_type 포함
        """
        admin_data = create_test_admin
        token = get_admin_auth_token(admin_data['id'])

        response = client.get(
            '/api/admin/dashboard/alerts-summary',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'summary' in data
        assert 'total' in data['summary']
        assert 'unread' in data['summary']
        assert 'by_type' in data['summary']

    def test_dashboard_without_admin(
        self, client, create_test_worker, get_auth_token
    ):
        """
        비관리자의 대시보드 접근 → 403

        Expected:
        - Status 403
        """
        worker_id = create_test_worker(
            email='admin_test_nonadmin2@test.com',
            password='Test123!',
            name='Non Admin 2',
            role='PI',
            is_admin=False
        )

        token = get_auth_token(worker_id, role='PI')

        response = client.get(
            '/api/admin/dashboard/process-summary',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 403


class TestTaskCorrection:
    """작업 수정 API 테스트"""

    def test_get_task_corrections(
        self, client, create_test_admin, create_test_worker, create_test_product,
        create_test_task, get_admin_auth_token
    ):
        """
        수정이 필요한 작업 목록 조회

        Expected:
        - Status 200
        - corrections 배열 포함
        - issue_type, issue_description 포함
        """
        worker_id = create_test_worker(
            email='admin_test_correction@test.com',
            password='Test123!',
            name='Correction Worker',
            role='TM'
        )

        create_test_product(
            qr_doc_id='DOC-ADMIN-003',
            serial_number='SN-ADMIN-003'
        )

        # 시간 역전 작업 생성 (completed_at < started_at)
        started_at = datetime.now(timezone.utc)
        completed_at = started_at - timedelta(hours=1)  # 1시간 전 완료 (역전)

        create_test_task(
            worker_id=worker_id,
            serial_number='SN-ADMIN-003',
            qr_doc_id='DOC-ADMIN-003',
            task_category='TM',
            task_id='TM-001',
            task_name='Reversed Task',
            started_at=started_at,
            completed_at=completed_at,
            duration_minutes=-60
        )

        admin_data = create_test_admin
        token = get_admin_auth_token(admin_data['id'])

        response = client.get(
            '/api/admin/task-corrections',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'corrections' in data
        assert 'total' in data

    def test_force_complete_task_success(
        self, client, create_test_admin, create_test_worker, create_test_product,
        create_test_task, get_admin_auth_token
    ):
        """
        작업 강제 완료 성공

        Expected:
        - Status 200
        - message 포함
        - task_id 반환
        """
        worker_id = create_test_worker(
            email='admin_test_force@test.com',
            password='Test123!',
            name='Force Worker',
            role='PI'
        )

        create_test_product(
            qr_doc_id='DOC-ADMIN-004',
            serial_number='SN-ADMIN-004'
        )

        # 미완료 작업 생성
        task_id = create_test_task(
            worker_id=worker_id,
            serial_number='SN-ADMIN-004',
            qr_doc_id='DOC-ADMIN-004',
            task_category='PI',
            task_id='PI-001',
            task_name='Incomplete Task',
            started_at=datetime.now(timezone.utc),
            completed_at=None
        )

        admin_data = create_test_admin
        token = get_admin_auth_token(admin_data['id'])

        response = client.post(
            f'/api/admin/tasks/{task_id}/force-complete',
            json={},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert '강제 완료' in data['message']
        assert data['task_id'] == task_id

    def test_force_complete_nonexistent_task(
        self, client, create_test_admin, get_admin_auth_token
    ):
        """
        존재하지 않는 작업 강제 완료 → 404

        Expected:
        - Status 404
        - error == TASK_NOT_FOUND
        """
        admin_data = create_test_admin
        token = get_admin_auth_token(admin_data['id'])

        response = client.post(
            '/api/admin/tasks/999999/force-complete',
            json={},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data['error'] == 'TASK_NOT_FOUND'


class TestUnfinishedCheck:
    """미완료 작업 체크 API 테스트"""

    def test_manual_unfinished_check(
        self, client, create_test_admin, get_admin_auth_token
    ):
        """
        미완료 작업 체크 수동 실행

        Expected:
        - Status 200
        - message, unfinished_count 포함
        """
        admin_data = create_test_admin
        token = get_admin_auth_token(admin_data['id'])

        response = client.post(
            '/api/admin/cron/check-unfinished-tasks',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        assert 'unfinished_count' in data

    def test_unfinished_check_without_admin(
        self, client, create_test_worker, get_auth_token
    ):
        """
        비관리자의 미완료 체크 실행 → 403

        Expected:
        - Status 403
        """
        worker_id = create_test_worker(
            email='admin_test_nonadmin3@test.com',
            password='Test123!',
            name='Non Admin 3',
            role='QI',
            is_admin=False
        )

        token = get_auth_token(worker_id, role='QI')

        response = client.post(
            '/api/admin/cron/check-unfinished-tasks',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 403
