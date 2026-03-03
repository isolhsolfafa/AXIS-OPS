"""
Sprint 16: /api/app/settings 접근 권한 테스트
TC-AS-01 ~ TC-AS-04: 일반 작업자도 앱 설정 조회 가능 확인

엔드포인트:
  GET /api/app/settings  — jwt_required만 (admin 불필요)
  GET /api/admin/settings — admin_required (admin 전용)
"""

import pytest
import time


# 고유 이메일 접미사 (테스트 격리)
_SUFFIX = f"sp16as_{int(time.time() * 1000)}"


@pytest.fixture(autouse=True)
def cleanup_sprint16_as_data(db_conn):
    """테스트 후 sprint16 app settings 관련 데이터 정리"""
    yield
    if db_conn and not db_conn.closed:
        try:
            cur = db_conn.cursor()
            cur.execute(
                "DELETE FROM email_verification WHERE worker_id IN "
                "(SELECT id FROM workers WHERE email LIKE %s)",
                (f'%@{_SUFFIX}.com',)
            )
            cur.execute(
                "DELETE FROM workers WHERE email LIKE %s",
                (f'%@{_SUFFIX}.com',)
            )
            db_conn.commit()
        except Exception:
            db_conn.rollback()


@pytest.fixture
def s16as_admin(create_test_worker, get_auth_token):
    """Admin 계정"""
    worker_id = create_test_worker(
        email=f'as_admin@{_SUFFIX}.com',
        password='TestAdmin123!',
        name='AS Admin',
        role='ADMIN',
        is_admin=True,
        email_verified=True,
        approval_status='approved',
        company='GST',
    )
    token = get_auth_token(worker_id)
    return {'id': worker_id, 'token': token}


@pytest.fixture
def s16as_worker(create_test_worker, get_auth_token):
    """일반 작업자 (non-admin)"""
    worker_id = create_test_worker(
        email=f'as_worker@{_SUFFIX}.com',
        password='TestWorker123!',
        name='AS Worker',
        role='MECH',
        is_admin=False,
        email_verified=True,
        approval_status='approved',
        company='FNI',
    )
    token = get_auth_token(worker_id)
    return {'id': worker_id, 'token': token}


class TestAdminCanAccessAppSettings:
    """TC-AS-01: Admin이 /api/app/settings 접근 가능"""

    def test_admin_access_app_settings(self, client, s16as_admin):
        response = client.get(
            '/api/app/settings',
            headers={'Authorization': f'Bearer {s16as_admin["token"]}'},
        )
        assert response.status_code == 200
        data = response.get_json()
        # 기본값 보장 필드 존재 확인
        assert 'location_qr_required' in data
        assert 'heating_jacket_enabled' in data
        assert 'phase_block_enabled' in data


class TestWorkerCanAccessAppSettings:
    """TC-AS-02: 일반 작업자도 /api/app/settings 접근 가능"""

    def test_worker_access_app_settings(self, client, s16as_worker):
        response = client.get(
            '/api/app/settings',
            headers={'Authorization': f'Bearer {s16as_worker["token"]}'},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'location_qr_required' in data


class TestUnauthenticatedDenied:
    """TC-AS-03: 미인증 요청 거부 (401)"""

    def test_unauthenticated_denied(self, client):
        response = client.get('/api/app/settings')
        assert response.status_code == 401


class TestAdminSettingsAdminOnly:
    """TC-AS-04: /api/admin/settings는 admin만 접근 가능"""

    def test_admin_settings_worker_denied(self, client, s16as_worker):
        response = client.get(
            '/api/admin/settings',
            headers={'Authorization': f'Bearer {s16as_worker["token"]}'},
        )
        assert response.status_code == 403

    def test_admin_settings_admin_allowed(self, client, s16as_admin):
        response = client.get(
            '/api/admin/settings',
            headers={'Authorization': f'Bearer {s16as_admin["token"]}'},
        )
        assert response.status_code == 200
