"""
Sprint 16: Admin 로그인 간소화 테스트
TC-AL-01 ~ TC-AL-04: 이메일 prefix 매칭 로그인

엔드포인트: POST /api/auth/login
"""

import pytest
import time


# 고유 이메일 접미사 (테스트 격리)
_SUFFIX = f"sp16al_{int(time.time() * 1000)}"


@pytest.fixture(autouse=True)
def cleanup_sprint16_al_data(db_conn):
    """테스트 후 sprint16 admin login 관련 데이터 정리"""
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
def s16_admin(create_test_worker, get_auth_token):
    """Admin 계정 (full email: sp16adm@{SUFFIX}.com — prefix 유일성 보장)"""
    worker_id = create_test_worker(
        email=f'sp16adm@{_SUFFIX}.com',
        password='TestAdmin123!',
        name='Sprint16 Admin',
        role='ADMIN',
        is_admin=True,
        email_verified=True,
        approval_status='approved',
        company='GST',
    )
    token = get_auth_token(worker_id)
    return {'id': worker_id, 'token': token, 'email': f'sp16adm@{_SUFFIX}.com'}


@pytest.fixture
def s16_regular_worker(create_test_worker, get_auth_token):
    """일반 작업자 (full email: worker@{SUFFIX}.com)"""
    worker_id = create_test_worker(
        email=f'worker@{_SUFFIX}.com',
        password='TestWorker123!',
        name='Sprint16 Worker',
        role='MECH',
        is_admin=False,
        email_verified=True,
        approval_status='approved',
        company='FNI',
    )
    token = get_auth_token(worker_id)
    return {'id': worker_id, 'token': token, 'email': f'worker@{_SUFFIX}.com'}


class TestAdminFullEmailLogin:
    """TC-AL-01: Admin이 full email로 로그인 — 정상 동작"""

    def test_admin_full_email_login(self, client, s16_admin):
        response = client.post('/api/auth/login', json={
            'email': f'sp16adm@{_SUFFIX}.com',
            'password': 'TestAdmin123!',
        })
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert data['worker']['is_admin'] is True


class TestAdminPrefixLogin:
    """TC-AL-02: Admin이 prefix만으로 로그인 (유일한 prefix)"""

    def test_admin_prefix_login(self, client, s16_admin):
        response = client.post('/api/auth/login', json={
            'email': 'sp16adm',  # @ 없이 prefix만 — DB에서 유일한 admin
            'password': 'TestAdmin123!',
        })
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
        assert data['worker']['is_admin'] is True
        assert data['worker']['email'] == f'sp16adm@{_SUFFIX}.com'


class TestRegularWorkerPrefixDenied:
    """TC-AL-03: 일반 사용자는 prefix 로그인 불가 (admin이 아니므로)"""

    def test_regular_worker_prefix_denied(self, client, s16_regular_worker):
        response = client.post('/api/auth/login', json={
            'email': 'worker',  # @ 없이 prefix만 — is_admin=False이므로 매칭 안됨
            'password': 'TestWorker123!',
        })
        assert response.status_code == 401
        data = response.get_json()
        assert data['error'] == 'INVALID_CREDENTIALS'


class TestFullEmailExactMatch:
    """TC-AL-04: @포함 시 정확 매칭 (prefix 로직 우회)"""

    def test_full_email_exact_match(self, client, s16_regular_worker):
        response = client.post('/api/auth/login', json={
            'email': f'worker@{_SUFFIX}.com',  # @ 포함 — 정확 매칭
            'password': 'TestWorker123!',
        })
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
        assert data['worker']['is_admin'] is False
