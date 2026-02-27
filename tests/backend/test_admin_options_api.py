"""
관리자 옵션 API 테스트 (Sprint 7 신규 엔드포인트)
엔드포인트:
  GET  /api/admin/managers               - 승인된 작업자 목록 (협력사 필터)
  PUT  /api/admin/workers/{id}/manager   - is_manager 토글
  GET  /api/admin/settings               - 설정 전체 조회
  PUT  /api/admin/settings               - 설정 UPSERT
  GET  /api/admin/tasks/pending          - 미종료 작업 목록
"""

import time
import pytest
from datetime import datetime, timezone


@pytest.fixture(autouse=True)
def cleanup_admin_options_test_data(db_conn):
    """테스트 후 관련 데이터 정리"""
    yield
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            cursor.execute(
                "DELETE FROM workers WHERE email LIKE '%@admin_options_test.com'"
            )
            cursor.execute(
                "DELETE FROM admin_settings WHERE setting_key LIKE 'test_%'"
            )
            db_conn.commit()
            cursor.close()
        except Exception:
            pass


@pytest.fixture
def options_admin(create_test_worker, get_admin_auth_token):
    """
    이 테스트 모듈 전용 admin fixture.
    매 테스트마다 고유한 이메일을 사용하여 DB unique constraint 충돌 방지.
    admin_options_test.com 도메인으로 생성하여 autouse cleanup에서 정리됨.
    """
    unique_email = f'admin_{int(time.time() * 1000)}@admin_options_test.com'
    worker_id = create_test_worker(
        email=unique_email,
        password='AdminPass123!',
        name='Options Test Admin',
        role='QI',
        approval_status='approved',
        email_verified=True,
        is_admin=True
    )
    token = get_admin_auth_token(worker_id)
    return {'id': worker_id, 'email': unique_email, 'token': token}


# ============================================================
# TestGetManagers: GET /api/admin/managers
# ============================================================

class TestGetManagers:
    """GET /api/admin/managers 테스트"""

    def test_get_all_managers(
        self, client, create_test_worker, options_admin
    ):
        """
        승인된 작업자 전체 목록 반환

        Expected:
        - Status 200
        - workers 배열 포함
        - total 포함
        - 각 항목에 id, name, email, role, is_manager, is_admin 키 포함
        """
        create_test_worker(
            email='fni1@admin_options_test.com',
            password='Test123!',
            name='FNI Worker 1',
            role='MECH',
            approval_status='approved',
            company='FNI'
        )
        create_test_worker(
            email='ps1@admin_options_test.com',
            password='Test123!',
            name='PS Worker 1',
            role='ELEC',
            approval_status='approved',
            company='P&S'
        )

        response = client.get(
            '/api/admin/managers',
            headers={'Authorization': f'Bearer {options_admin["token"]}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'workers' in data
        assert 'total' in data
        assert data['total'] >= 2
        for worker in data['workers']:
            assert 'id' in worker
            assert 'name' in worker
            assert 'email' in worker
            assert 'role' in worker
            assert 'is_manager' in worker
            assert 'is_admin' in worker

    def test_get_managers_filter_by_company_fni(
        self, client, create_test_worker, options_admin
    ):
        """
        company=FNI 필터 → FNI 소속 작업자만 반환

        Expected:
        - Status 200
        - 반환된 모든 작업자의 company == 'FNI'
        """
        create_test_worker(
            email='fni2@admin_options_test.com',
            password='Test123!',
            name='FNI Worker 2',
            role='MECH',
            approval_status='approved',
            company='FNI'
        )
        create_test_worker(
            email='bat1@admin_options_test.com',
            password='Test123!',
            name='BAT Worker 1',
            role='MECH',
            approval_status='approved',
            company='BAT'
        )

        response = client.get(
            '/api/admin/managers?company=FNI',
            headers={'Authorization': f'Bearer {options_admin["token"]}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'workers' in data
        for worker in data['workers']:
            assert worker.get('company') == 'FNI'

    def test_get_managers_filter_tms_m(
        self, client, create_test_worker, options_admin
    ):
        """
        company=TMS(M) 필터 → TMS(M) 소속만 반환

        Expected:
        - Status 200
        - 반환된 모든 작업자의 company == 'TMS(M)'
        """
        create_test_worker(
            email='tmsm1@admin_options_test.com',
            password='Test123!',
            name='TMS M Worker 1',
            role='MECH',
            approval_status='approved',
            company='TMS(M)'
        )

        response = client.get(
            '/api/admin/managers?company=TMS(M)',
            headers={'Authorization': f'Bearer {options_admin["token"]}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'workers' in data
        for worker in data['workers']:
            assert worker.get('company') == 'TMS(M)'

    def test_get_managers_no_token(self, client):
        """
        인증 없이 접근 → 401

        Expected:
        - Status 401
        """
        response = client.get('/api/admin/managers')
        assert response.status_code == 401

    def test_get_managers_non_admin_forbidden(
        self, client, create_test_worker, get_auth_token
    ):
        """
        일반 작업자로 접근 → 403

        Expected:
        - Status 403
        - error == FORBIDDEN
        """
        worker_id = create_test_worker(
            email='regular1@admin_options_test.com',
            password='Test123!',
            name='Regular Worker',
            role='MECH',
            is_admin=False
        )
        token = get_auth_token(worker_id, role='MECH')

        response = client.get(
            '/api/admin/managers',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 403
        data = response.get_json()
        assert data['error'] == 'FORBIDDEN'


# ============================================================
# TestToggleManager: PUT /api/admin/workers/{id}/manager
# ============================================================

class TestToggleManager:
    """PUT /api/admin/workers/{id}/manager 테스트"""

    def test_set_manager_true(
        self, client, create_test_worker, options_admin
    ):
        """
        is_manager=True 설정 성공

        Expected:
        - Status 200
        - is_manager == True 반환
        - worker_id 반환
        """
        worker_id = create_test_worker(
            email='toggle1@admin_options_test.com',
            password='Test123!',
            name='Toggle Worker 1',
            role='MECH',
            approval_status='approved',
            is_manager=False
        )

        response = client.put(
            f'/api/admin/workers/{worker_id}/manager',
            json={'is_manager': True},
            headers={'Authorization': f'Bearer {options_admin["token"]}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['worker_id'] == worker_id
        assert data['is_manager'] is True

    def test_set_manager_false(
        self, client, create_test_worker, options_admin
    ):
        """
        is_manager=False 설정 성공 (관리자 해제)

        Expected:
        - Status 200
        - is_manager == False 반환
        """
        worker_id = create_test_worker(
            email='toggle2@admin_options_test.com',
            password='Test123!',
            name='Toggle Worker 2',
            role='ELEC',
            approval_status='approved',
            is_manager=True
        )

        response = client.put(
            f'/api/admin/workers/{worker_id}/manager',
            json={'is_manager': False},
            headers={'Authorization': f'Bearer {options_admin["token"]}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['worker_id'] == worker_id
        assert data['is_manager'] is False

    def test_toggle_manager_worker_not_found(
        self, client, options_admin
    ):
        """
        존재하지 않는 작업자 → 404

        Expected:
        - Status 404
        - error == WORKER_NOT_FOUND
        """
        response = client.put(
            '/api/admin/workers/999999/manager',
            json={'is_manager': True},
            headers={'Authorization': f'Bearer {options_admin["token"]}'}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data['error'] == 'WORKER_NOT_FOUND'

    def test_toggle_manager_missing_field(
        self, client, create_test_worker, options_admin
    ):
        """
        is_manager 필드 누락 → 400

        Expected:
        - Status 400
        - error == INVALID_REQUEST
        """
        worker_id = create_test_worker(
            email='toggle3@admin_options_test.com',
            password='Test123!',
            name='Toggle Worker 3',
            role='MECH'
        )

        response = client.put(
            f'/api/admin/workers/{worker_id}/manager',
            json={},  # is_manager 누락
            headers={'Authorization': f'Bearer {options_admin["token"]}'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'INVALID_REQUEST'

    def test_non_admin_cannot_toggle(
        self, client, create_test_worker, get_auth_token
    ):
        """
        일반 작업자로 PUT manager → 403

        Expected:
        - Status 403
        """
        worker_id = create_test_worker(
            email='regular2@admin_options_test.com',
            password='Test123!',
            name='Regular Worker 2',
            role='MECH',
            is_admin=False
        )
        target_worker_id = create_test_worker(
            email='target1@admin_options_test.com',
            password='Test123!',
            name='Target Worker 1',
            role='ELEC'
        )
        token = get_auth_token(worker_id, role='MECH')

        response = client.put(
            f'/api/admin/workers/{target_worker_id}/manager',
            json={'is_manager': True},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 403


# ============================================================
# TestAdminSettings: GET/PUT /api/admin/settings
# ============================================================

class TestAdminSettings:
    """GET /api/admin/settings, PUT /api/admin/settings 테스트"""

    def test_get_settings(self, client, options_admin):
        """
        설정 전체 조회

        Expected:
        - Status 200
        - heating_jacket_enabled 키 포함 (기본값 보장)
        - phase_block_enabled 키 포함 (기본값 보장)
        """
        response = client.get(
            '/api/admin/settings',
            headers={'Authorization': f'Bearer {options_admin["token"]}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'heating_jacket_enabled' in data
        assert 'phase_block_enabled' in data

    def test_update_setting(self, client, options_admin):
        """
        heating_jacket_enabled 설정 업데이트

        Expected:
        - Status 200
        - updated_keys에 'heating_jacket_enabled' 포함

        Note: 테스트 후 heating_jacket_enabled를 False로 복원
        """
        token = options_admin['token']

        response = client.put(
            '/api/admin/settings',
            json={'heating_jacket_enabled': True},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'updated_keys' in data
        assert 'heating_jacket_enabled' in data['updated_keys']

        # 원복
        client.put(
            '/api/admin/settings',
            json={'heating_jacket_enabled': False},
            headers={'Authorization': f'Bearer {token}'}
        )

    def test_update_then_get(self, client, options_admin):
        """
        PUT 후 GET → 값이 반영되어 있어야 함

        Expected:
        - PUT Status 200
        - GET Status 200
        - phase_block_enabled 값이 PUT한 값과 일치

        Note: 테스트 종료 시 phase_block_enabled를 False로 복원
        (다른 테스트에서 기본값 False를 기대할 수 있으므로)
        """
        token = options_admin['token']

        # False로 설정
        put_response = client.put(
            '/api/admin/settings',
            json={'phase_block_enabled': False},
            headers={'Authorization': f'Bearer {token}'}
        )
        assert put_response.status_code == 200

        # GET으로 확인
        get_response = client.get(
            '/api/admin/settings',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert get_response.status_code == 200
        assert get_response.get_json()['phase_block_enabled'] is False

        # True로 변경 후 재확인
        put_response2 = client.put(
            '/api/admin/settings',
            json={'phase_block_enabled': True},
            headers={'Authorization': f'Bearer {token}'}
        )
        assert put_response2.status_code == 200

        get_response2 = client.get(
            '/api/admin/settings',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert get_response2.status_code == 200
        assert get_response2.get_json()['phase_block_enabled'] is True

        # 원복: False로 복원 (다른 테스트 격리)
        client.put(
            '/api/admin/settings',
            json={'phase_block_enabled': False},
            headers={'Authorization': f'Bearer {token}'}
        )

    def test_update_settings_invalid_key(self, client, options_admin):
        """
        허용되지 않은 키만 전달 → 400

        Expected:
        - Status 400
        - error == INVALID_REQUEST
        """
        response = client.put(
            '/api/admin/settings',
            json={'unknown_key': True, 'another_invalid': 'value'},
            headers={'Authorization': f'Bearer {options_admin["token"]}'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'INVALID_REQUEST'

    def test_settings_unauthenticated(self, client):
        """
        인증 없이 설정 조회 → 401

        Expected:
        - Status 401
        """
        response = client.get('/api/admin/settings')
        assert response.status_code == 401


# ============================================================
# TestPendingTasks: GET /api/admin/tasks/pending
# ============================================================

class TestPendingTasks:
    """GET /api/admin/tasks/pending 테스트"""

    def test_get_pending_tasks(
        self, client, create_test_worker, create_test_task,
        create_test_product, options_admin
    ):
        """
        미종료 작업 목록 조회 (started_at IS NOT NULL AND completed_at IS NULL)

        Expected:
        - Status 200
        - tasks 배열 포함
        - total 포함
        - 생성한 미종료 작업이 포함됨
        - 각 항목에 id, worker_id, worker_name, serial_number,
          started_at, elapsed_minutes 포함
        """
        worker_id = create_test_worker(
            email='pending_task_worker@admin_options_test.com',
            password='Test123!',
            name='Pending Task Worker',
            role='MECH',
            approval_status='approved'
        )

        create_test_product(
            qr_doc_id='DOC-OPTIONS-001',
            serial_number='SN-OPTIONS-001'
        )

        create_test_task(
            worker_id=worker_id,
            serial_number='SN-OPTIONS-001',
            qr_doc_id='DOC-OPTIONS-001',
            task_category='MECH',
            task_id='MM-OPT-001',
            task_name='Pending Task 1',
            started_at=datetime.now(timezone.utc),
            completed_at=None  # 미종료
        )

        response = client.get(
            '/api/admin/tasks/pending',
            headers={'Authorization': f'Bearer {options_admin["token"]}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'tasks' in data
        assert 'total' in data
        assert data['total'] >= 1

        if data['tasks']:
            task = data['tasks'][0]
            assert 'id' in task
            assert 'worker_id' in task
            assert 'worker_name' in task
            assert 'serial_number' in task
            assert 'started_at' in task
            assert 'elapsed_minutes' in task

    def test_no_pending_tasks(
        self, client, options_admin, db_conn
    ):
        """
        미종료 작업 없을 때 → 빈 목록 반환

        Expected:
        - Status 200
        - total == 0 또는 tasks 빈 배열
        """
        # 모든 진행 중 작업을 완료 처리
        if db_conn and not db_conn.closed:
            cursor = db_conn.cursor()
            cursor.execute(
                """
                UPDATE app_task_details
                SET completed_at = NOW(), updated_at = NOW()
                WHERE started_at IS NOT NULL AND completed_at IS NULL
                """
            )
            db_conn.commit()
            cursor.close()

        response = client.get(
            '/api/admin/tasks/pending',
            headers={'Authorization': f'Bearer {options_admin["token"]}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 0 or len(data['tasks']) == 0

    def test_pending_tasks_limit_param(self, client, options_admin):
        """
        limit 파라미터 적용 확인

        Expected:
        - Status 200
        - tasks 배열 길이 <= limit
        """
        response = client.get(
            '/api/admin/tasks/pending?limit=3',
            headers={'Authorization': f'Bearer {options_admin["token"]}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['tasks']) <= 3

    def test_pending_tasks_non_admin_forbidden(
        self, client, create_test_worker, get_auth_token
    ):
        """
        일반 작업자로 접근 → 403

        Expected:
        - Status 403
        """
        worker_id = create_test_worker(
            email='regular3@admin_options_test.com',
            password='Test123!',
            name='Regular Worker 3',
            role='PI',
            is_admin=False
        )
        token = get_auth_token(worker_id, role='PI')

        response = client.get(
            '/api/admin/tasks/pending',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 403


# ============================================================
# TestAdminAuth: 인증/권한 공통 테스트
# ============================================================

class TestAdminAuth:
    """관리자 API 인증/권한 공통 테스트"""

    def test_unauthenticated_get_managers(self, client):
        """
        토큰 없이 GET /api/admin/managers → 401

        Expected:
        - Status 401
        """
        response = client.get('/api/admin/managers')
        assert response.status_code == 401

    def test_unauthenticated_toggle_manager(self, client):
        """
        토큰 없이 PUT /api/admin/workers/1/manager → 401

        Expected:
        - Status 401
        """
        response = client.put(
            '/api/admin/workers/1/manager',
            json={'is_manager': True}
        )
        assert response.status_code == 401

    def test_unauthenticated_get_pending_tasks(self, client):
        """
        토큰 없이 GET /api/admin/tasks/pending → 401

        Expected:
        - Status 401
        """
        response = client.get('/api/admin/tasks/pending')
        assert response.status_code == 401

    def test_expired_token_rejected(
        self, client, create_test_worker, get_admin_auth_token
    ):
        """
        만료된 토큰으로 접근 → 401

        Expected:
        - Status 401
        """
        # 만료 토큰 전용 워커 생성
        worker_id = create_test_worker(
            email='expired_token@admin_options_test.com',
            password='Test123!',
            name='Expired Token Worker',
            role='QI',
            approval_status='approved',
            is_admin=True
        )
        # expires_in_hours=-1 → 이미 만료된 토큰
        expired_token = get_admin_auth_token(
            worker_id,
            expires_in_hours=-1
        )

        response = client.get(
            '/api/admin/managers',
            headers={'Authorization': f'Bearer {expired_token}'}
        )

        assert response.status_code == 401
