"""
Sprint 40-C: 비활성 사용자 관리 테스트 (9건)

1. Migration: is_active, deactivated_at, last_login_at 컬럼 존재 확인
2. Login: is_active=FALSE인 사용자 → 403 ACCOUNT_DEACTIVATED
3. Login: 정상 사용자 → last_login_at 갱신 확인
4. GET /api/admin/inactive-workers → 30일 미로그인 목록 반환
5. GET /api/admin/deactivated-workers → 비활성 사용자 목록
6. POST /api/admin/worker-status → deactivate/reactivate 동작
7. POST /api/app/work/request-deactivation → manager 요청
8. POST /api/app/work/request-deactivation → 다른 company 사용자 거부
9. Regression: 기존 login/approve 흐름 영향 없음
"""

import sys
from pathlib import Path

_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest
import psycopg2
from datetime import datetime, timedelta, timezone
import bcrypt

# ── 테스트 데이터 prefix ────────────────────────────────────────────────────
_PREFIX = 'sp40c_'


# ── 공통 헬퍼 ────────────────────────────────────────────────────────────────

def _create_worker(
    db_conn,
    email: str,
    name: str,
    role: str = 'MECH',
    company: str = 'FNI',
    is_manager: bool = False,
    is_admin: bool = False,
    approval_status: str = 'approved',
    email_verified: bool = True,
    is_active: bool = True,
) -> int:
    """테스트용 작업자 생성, worker_id 반환"""
    pw_hash = bcrypt.hashpw('TestPass123!'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO workers (
            name, email, password_hash, role, company,
            approval_status, email_verified, is_manager, is_admin, is_active
        )
        VALUES (%s, %s, %s, %s::role_enum, %s, %s::approval_status_enum,
                %s, %s, %s, %s)
        RETURNING id
    """, (name, email, pw_hash, role, company,
          approval_status, email_verified, is_manager, is_admin, is_active))
    row = cursor.fetchone()
    db_conn.commit()
    cursor.close()
    return row[0]


def _cleanup_workers(db_conn, emails: list):
    """테스트 작업자 정리"""
    cursor = db_conn.cursor()
    for email in emails:
        cursor.execute("DELETE FROM workers WHERE email = %s", (email,))
    db_conn.commit()
    cursor.close()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def admin_token(db_conn, seed_test_data, get_auth_token):
    """Seed admin의 JWT 토큰"""
    cursor = db_conn.cursor()
    cursor.execute("SELECT id FROM workers WHERE email = 'seed_admin@test.axisos.com'")
    row = cursor.fetchone()
    cursor.close()
    return get_auth_token(row[0], role='ADMIN', is_admin=True)


@pytest.fixture
def sp40c_workers(db_conn):
    """Sprint 40-C 전용 테스트 작업자 생성 + teardown"""
    emails = []

    def _make(suffix, **kwargs):
        email = f'{_PREFIX}{suffix}@test.axisos.com'
        name = f'SP40C {suffix}'
        emails.append(email)
        return _create_worker(db_conn, email=email, name=name, **kwargs)

    yield _make

    _cleanup_workers(db_conn, emails)


# ═══════════════════════════════════════════════════════════════════════════════
# TC-01: Migration — 컬럼 존재 확인
# ═══════════════════════════════════════════════════════════════════════════════

def test_migration_columns_exist(db_conn, db_schema):
    """TC-01: workers 테이블에 is_active, deactivated_at, last_login_at 컬럼 존재"""
    cursor = db_conn.cursor()
    cursor.execute("""
        SELECT column_name, data_type, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'workers'
          AND column_name  IN ('is_active', 'deactivated_at', 'last_login_at')
        ORDER BY column_name
    """)
    rows = cursor.fetchall()
    cursor.close()

    col_names = {r[0] for r in rows}
    assert 'is_active' in col_names, "is_active 컬럼 없음"
    assert 'deactivated_at' in col_names, "deactivated_at 컬럼 없음"
    assert 'last_login_at' in col_names, "last_login_at 컬럼 없음"

    # is_active 기본값 TRUE 확인
    for row in rows:
        if row[0] == 'is_active':
            assert row[2] is not None, "is_active 기본값 없음"
            assert 'true' in str(row[2]).lower(), f"is_active 기본값이 TRUE가 아님: {row[2]}"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-02: 비활성 사용자 로그인 → 403 ACCOUNT_DEACTIVATED
# ═══════════════════════════════════════════════════════════════════════════════

def test_login_deactivated_user_rejected(client, db_conn, seed_test_data, sp40c_workers):
    """TC-02: is_active=FALSE인 사용자 로그인 시 403 ACCOUNT_DEACTIVATED"""
    sp40c_workers('inactive01', role='MECH', company='FNI', is_active=False)

    response = client.post('/api/auth/login', json={
        'email': f'{_PREFIX}inactive01@test.axisos.com',
        'password': 'TestPass123!',
    })

    assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.get_json()}"
    data = response.get_json()
    assert data.get('error') == 'ACCOUNT_DEACTIVATED', f"에러 코드 불일치: {data}"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-03: 정상 사용자 로그인 → last_login_at 갱신
# ═══════════════════════════════════════════════════════════════════════════════

def test_login_updates_last_login_at(client, db_conn, seed_test_data, sp40c_workers):
    """TC-03: 정상 로그인 성공 후 workers.last_login_at이 갱신됨"""
    worker_id = sp40c_workers('active01', role='MECH', company='FNI', is_active=True)

    # 로그인 전 last_login_at 확인
    cursor = db_conn.cursor()
    cursor.execute("SELECT last_login_at FROM workers WHERE id = %s", (worker_id,))
    before = cursor.fetchone()[0]
    cursor.close()

    response = client.post('/api/auth/login', json={
        'email': f'{_PREFIX}active01@test.axisos.com',
        'password': 'TestPass123!',
    })

    assert response.status_code == 200, f"로그인 실패: {response.get_json()}"

    # 새 연결로 갱신 확인 (Flask 테스트 클라이언트가 동일 연결 사용할 수 있어 새 연결 필요)
    from tests.conftest import TestConfig, _parse_db_url
    params = _parse_db_url(TestConfig.DATABASE_URL)
    new_conn = psycopg2.connect(**params)
    new_conn.autocommit = True
    new_cur = new_conn.cursor()
    new_cur.execute("SELECT last_login_at FROM workers WHERE id = %s", (worker_id,))
    after = new_cur.fetchone()[0]
    new_cur.close()
    new_conn.close()

    assert after is not None, "last_login_at이 NULL — 갱신되지 않음"
    # before가 None이거나 after > before 이면 갱신된 것
    if before is not None:
        assert after >= before, "last_login_at이 이전 값보다 작음"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-04: GET /api/admin/inactive-workers → 30일 미로그인 목록
# ═══════════════════════════════════════════════════════════════════════════════

def test_get_inactive_workers(client, db_conn, seed_test_data, admin_token, sp40c_workers):
    """TC-04: last_login_at이 30일 이전이거나 NULL인 approved 사용자 목록 반환"""
    # 31일 전 last_login_at으로 작업자 생성
    inactive_id = sp40c_workers('inactive_old01', role='MECH', company='FNI')

    cursor = db_conn.cursor()
    cursor.execute(
        "UPDATE workers SET last_login_at = NOW() - INTERVAL '31 days' WHERE id = %s",
        (inactive_id,)
    )
    db_conn.commit()
    cursor.close()

    response = client.get(
        '/api/admin/inactive-workers?days=30',
        headers={'Authorization': f'Bearer {admin_token}'}
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.get_json()}"
    data = response.get_json()
    assert 'inactive_workers' in data
    assert 'count' in data
    assert 'threshold_days' in data
    assert data['threshold_days'] == 30

    ids = [w['id'] for w in data['inactive_workers']]
    assert inactive_id in ids, f"31일 전 로그인 사용자({inactive_id})가 목록에 없음"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-05: GET /api/admin/deactivated-workers → 비활성 목록
# ═══════════════════════════════════════════════════════════════════════════════

def test_get_deactivated_workers(client, db_conn, seed_test_data, admin_token, sp40c_workers):
    """TC-05: is_active=FALSE인 사용자 목록 반환"""
    deact_id = sp40c_workers('deact01', role='MECH', company='FNI', is_active=False)

    response = client.get(
        '/api/admin/deactivated-workers',
        headers={'Authorization': f'Bearer {admin_token}'}
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.get_json()}"
    data = response.get_json()
    assert 'deactivated_workers' in data
    assert 'count' in data

    ids = [w['id'] for w in data['deactivated_workers']]
    assert deact_id in ids, f"비활성 사용자({deact_id})가 목록에 없음"


# ═══════════════════════════════════════════════════════════════════════════════
# TC-06: POST /api/admin/worker-status → deactivate/reactivate 동작
# ═══════════════════════════════════════════════════════════════════════════════

def test_admin_worker_status_deactivate_and_reactivate(
    client, db_conn, seed_test_data, admin_token, sp40c_workers
):
    """TC-06: admin이 deactivate → reactivate 순서로 상태 변경"""
    worker_id = sp40c_workers('status_test01', role='MECH', company='FNI', is_active=True)

    # Deactivate
    resp = client.post(
        '/api/admin/worker-status',
        json={'worker_id': worker_id, 'action': 'deactivate'},
        headers={'Authorization': f'Bearer {admin_token}'}
    )
    assert resp.status_code == 200, f"Deactivate failed: {resp.get_json()}"
    data = resp.get_json()
    assert data['action'] == 'deactivate'
    assert data['worker_id'] == worker_id

    # DB에서 is_active=FALSE 확인
    from tests.conftest import TestConfig, _parse_db_url
    params = _parse_db_url(TestConfig.DATABASE_URL)
    conn2 = psycopg2.connect(**params)
    conn2.autocommit = True
    cur2 = conn2.cursor()
    cur2.execute("SELECT is_active, deactivated_at FROM workers WHERE id = %s", (worker_id,))
    row = cur2.fetchone()
    cur2.close()
    conn2.close()

    assert row[0] is False, "is_active가 FALSE로 변경되지 않음"
    assert row[1] is not None, "deactivated_at이 설정되지 않음"

    # Reactivate
    resp2 = client.post(
        '/api/admin/worker-status',
        json={'worker_id': worker_id, 'action': 'reactivate'},
        headers={'Authorization': f'Bearer {admin_token}'}
    )
    assert resp2.status_code == 200, f"Reactivate failed: {resp2.get_json()}"
    data2 = resp2.get_json()
    assert data2['action'] == 'reactivate'


# ═══════════════════════════════════════════════════════════════════════════════
# TC-07: POST /api/app/work/request-deactivation → manager 요청 성공
# ═══════════════════════════════════════════════════════════════════════════════

def test_manager_request_deactivation_success(
    client, db_conn, seed_test_data, get_auth_token, sp40c_workers
):
    """TC-07: 같은 company manager가 하위 작업자 비활성화 요청"""
    manager_id = sp40c_workers(
        'mgr01', role='MECH', company='BAT', is_manager=True
    )
    target_id = sp40c_workers(
        'mgr_target01', role='MECH', company='BAT', is_manager=False
    )

    token = get_auth_token(manager_id, role='MECH', is_admin=False)

    resp = client.post(
        '/api/app/work/request-deactivation',
        json={'worker_id': target_id, 'reason': '퇴사 처리'},
        headers={'Authorization': f'Bearer {token}'}
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.get_json()}"
    data = resp.get_json()
    assert data['worker_id'] == target_id
    assert '비활성화' in data.get('message', '')


# ═══════════════════════════════════════════════════════════════════════════════
# TC-08: POST /api/app/work/request-deactivation → 다른 company 거부
# ═══════════════════════════════════════════════════════════════════════════════

def test_manager_request_deactivation_different_company_rejected(
    client, db_conn, seed_test_data, get_auth_token, sp40c_workers
):
    """TC-08: 다른 company 사용자 비활성화 요청 → 403 FORBIDDEN"""
    manager_id = sp40c_workers(
        'mgr02', role='MECH', company='FNI', is_manager=True
    )
    other_company_target_id = sp40c_workers(
        'other_co_target01', role='MECH', company='BAT', is_manager=False
    )

    token = get_auth_token(manager_id, role='MECH', is_admin=False)

    resp = client.post(
        '/api/app/work/request-deactivation',
        json={'worker_id': other_company_target_id, 'reason': '다른 회사'},
        headers={'Authorization': f'Bearer {token}'}
    )

    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.get_json()}"
    data = resp.get_json()
    assert data.get('error') == 'FORBIDDEN'


# ═══════════════════════════════════════════════════════════════════════════════
# TC-09: Regression — 기존 login/approve 흐름 영향 없음
# ═══════════════════════════════════════════════════════════════════════════════

def test_regression_normal_login_unaffected(client, db_conn, seed_test_data, sp40c_workers):
    """TC-09: is_active=TRUE 사용자의 로그인/승인 흐름은 그대로 동작"""
    sp40c_workers('regression01', role='MECH', company='FNI', is_active=True)

    # 정상 로그인
    resp = client.post('/api/auth/login', json={
        'email': f'{_PREFIX}regression01@test.axisos.com',
        'password': 'TestPass123!',
    })

    assert resp.status_code == 200, f"정상 사용자 로그인 실패: {resp.get_json()}"
    data = resp.get_json()
    assert 'access_token' in data
    assert 'worker' in data

    # approval_status=pending 사용자는 403 APPROVAL_PENDING (기존 동작 유지)
    sp40c_workers('regression_pending01', role='MECH', company='FNI',
                  approval_status='pending', is_active=True)

    resp2 = client.post('/api/auth/login', json={
        'email': f'{_PREFIX}regression_pending01@test.axisos.com',
        'password': 'TestPass123!',
    })

    assert resp2.status_code == 403
    data2 = resp2.get_json()
    assert data2.get('error') == 'APPROVAL_PENDING'
