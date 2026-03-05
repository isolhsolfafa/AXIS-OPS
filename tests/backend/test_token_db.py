"""
Sprint 19-B: DB 기반 Refresh Token 관리 + 탈취 감지 테스트
엔드포인트:
  POST /api/auth/refresh  — DB 저장 + 탈취 감지
  POST /api/auth/login    — refresh_token DB 저장
  POST /api/auth/logout   — refresh_token DB 무효화
"""

import time
import pytest
from psycopg2.extras import RealDictCursor


class TestTokenDB:
    """Refresh Token DB 관리 테스트 (TC-TDB-01 ~ TC-TDB-10)"""

    # ------------------------------------------------------------------
    # TC-TDB-01: 로그인 시 refresh_token이 DB에 저장됨
    # ------------------------------------------------------------------
    def test_login_stores_token_in_db(self, client, create_test_worker, db_conn):
        """TC-TDB-01: 로그인 시 auth.refresh_tokens에 토큰 해시 저장"""
        ts = int(time.time() * 1000)
        email = f'tdb01_{ts}@test.com'
        worker_id = create_test_worker(
            email=email, password='Test123!', name='TDB01',
            role='MECH', company='FNI'
        )

        response = client.post('/api/auth/login', json={
            'email': email,
            'password': 'Test123!',
            'device_id': 'test-device-tdb01',
        })
        assert response.status_code == 200

        # DB에 토큰 저장 확인
        cursor = db_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT worker_id, device_id, revoked FROM auth.refresh_tokens "
            "WHERE worker_id = %s ORDER BY id DESC LIMIT 1",
            (worker_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row['worker_id'] == worker_id
        assert row['device_id'] == 'test-device-tdb01'
        assert row['revoked'] is False

    # ------------------------------------------------------------------
    # TC-TDB-02: refresh 시 이전 토큰 revoked + 새 토큰 저장
    # ------------------------------------------------------------------
    def test_refresh_rotates_token_in_db(self, client, create_test_worker, db_conn):
        """TC-TDB-02: refresh 시 이전 토큰 revoked, 새 토큰 저장"""
        ts = int(time.time() * 1000)
        email = f'tdb02_{ts}@test.com'
        worker_id = create_test_worker(
            email=email, password='Test123!', name='TDB02',
            role='MECH', company='FNI'
        )

        # 로그인
        login_resp = client.post('/api/auth/login', json={
            'email': email, 'password': 'Test123!',
            'device_id': 'test-device-tdb02',
        })
        assert login_resp.status_code == 200
        refresh_token = login_resp.get_json()['refresh_token']

        # refresh
        refresh_resp = client.post('/api/auth/refresh', json={
            'refresh_token': refresh_token,
            'device_id': 'test-device-tdb02',
        })
        assert refresh_resp.status_code == 200

        # DB 확인: 이전 토큰 revoked, 새 토큰 active
        cursor = db_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT revoked, revoked_reason FROM auth.refresh_tokens "
            "WHERE worker_id = %s ORDER BY id ASC",
            (worker_id,)
        )
        rows = cursor.fetchall()
        assert len(rows) >= 2
        assert rows[-2]['revoked'] is True
        assert rows[-2]['revoked_reason'] == 'rotation'
        assert rows[-1]['revoked'] is False

    # ------------------------------------------------------------------
    # TC-TDB-03: 탈취 감지 — revoked 토큰 재사용 시 전체 무효화
    # ------------------------------------------------------------------
    def test_theft_detection_revokes_all(self, client, create_test_worker, db_conn):
        """TC-TDB-03: revoked 토큰 재사용 시 전체 토큰 무효화"""
        ts = int(time.time() * 1000)
        email = f'tdb03_{ts}@test.com'
        worker_id = create_test_worker(
            email=email, password='Test123!', name='TDB03',
            role='MECH', company='FNI'
        )

        # 로그인 → refresh_token_v1
        login_resp = client.post('/api/auth/login', json={
            'email': email, 'password': 'Test123!',
            'device_id': 'test-device-tdb03',
        })
        token_v1 = login_resp.get_json()['refresh_token']

        # 정상 rotation → token_v1 revoked, token_v2 발급
        refresh_resp = client.post('/api/auth/refresh', json={
            'refresh_token': token_v1,
            'device_id': 'test-device-tdb03',
        })
        assert refresh_resp.status_code == 200
        token_v2 = refresh_resp.get_json()['refresh_token']

        # 공격자가 token_v1(이미 revoked)으로 refresh 시도 → 탈취 감지
        theft_resp = client.post('/api/auth/refresh', json={
            'refresh_token': token_v1,
            'device_id': 'attacker-device',
        })
        assert theft_resp.status_code == 401
        assert theft_resp.get_json()['error'] == 'TOKEN_THEFT_DETECTED'

        # token_v2도 무효화됨 — 정상 사용자도 재로그인 필요
        retry_resp = client.post('/api/auth/refresh', json={
            'refresh_token': token_v2,
            'device_id': 'test-device-tdb03',
        })
        assert retry_resp.status_code == 401

    # ------------------------------------------------------------------
    # TC-TDB-04: 로그아웃 시 refresh_token DB 무효화
    # ------------------------------------------------------------------
    def test_logout_revokes_token(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-TDB-04: POST /auth/logout → refresh_token 무효화"""
        ts = int(time.time() * 1000)
        email = f'tdb04_{ts}@test.com'
        worker_id = create_test_worker(
            email=email, password='Test123!', name='TDB04',
            role='MECH', company='FNI'
        )

        # 로그인
        login_resp = client.post('/api/auth/login', json={
            'email': email, 'password': 'Test123!',
            'device_id': 'test-device-tdb04',
        })
        assert login_resp.status_code == 200
        data = login_resp.get_json()
        access_token = data['access_token']
        refresh_token = data['refresh_token']

        # 로그아웃
        logout_resp = client.post('/api/auth/logout',
            json={'refresh_token': refresh_token},
            headers={'Authorization': f'Bearer {access_token}'}
        )
        assert logout_resp.status_code == 200

        # DB 확인: revoked + reason='logout'
        cursor = db_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT revoked, revoked_reason FROM auth.refresh_tokens "
            "WHERE worker_id = %s ORDER BY id DESC LIMIT 1",
            (worker_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row['revoked'] is True
        assert row['revoked_reason'] == 'logout'

    # ------------------------------------------------------------------
    # TC-TDB-05: 로그아웃 후 refresh_token 사용 불가 (탈취 감지)
    # ------------------------------------------------------------------
    def test_logout_token_cannot_refresh(self, client, create_test_worker, db_conn):
        """TC-TDB-05: 로그아웃 후 해당 refresh_token으로 refresh 시도 → 탈취 감지"""
        ts = int(time.time() * 1000)
        email = f'tdb05_{ts}@test.com'
        worker_id = create_test_worker(
            email=email, password='Test123!', name='TDB05',
            role='MECH', company='FNI'
        )

        # 로그인
        login_resp = client.post('/api/auth/login', json={
            'email': email, 'password': 'Test123!',
        })
        data = login_resp.get_json()
        access_token = data['access_token']
        refresh_token = data['refresh_token']

        # 로그아웃 (refresh_token 전송)
        client.post('/api/auth/logout',
            json={'refresh_token': refresh_token},
            headers={'Authorization': f'Bearer {access_token}'}
        )

        # 로그아웃된 토큰으로 refresh 시도 → 탈취 감지
        resp = client.post('/api/auth/refresh', json={
            'refresh_token': refresh_token,
        })
        assert resp.status_code == 401
        assert resp.get_json()['error'] == 'TOKEN_THEFT_DETECTED'

    # ------------------------------------------------------------------
    # TC-TDB-06: 로그아웃 시 refresh_token 미전송 → 전체 토큰 무효화
    # ------------------------------------------------------------------
    def test_logout_without_token_revokes_all(self, client, create_test_worker, db_conn):
        """TC-TDB-06: refresh_token 없이 로그아웃 → 해당 worker 전체 토큰 무효화"""
        ts = int(time.time() * 1000)
        email = f'tdb06_{ts}@test.com'
        worker_id = create_test_worker(
            email=email, password='Test123!', name='TDB06',
            role='MECH', company='FNI'
        )

        # 기기 2개에서 로그인
        resp1 = client.post('/api/auth/login', json={
            'email': email, 'password': 'Test123!',
            'device_id': 'device-A',
        })
        resp2 = client.post('/api/auth/login', json={
            'email': email, 'password': 'Test123!',
            'device_id': 'device-B',
        })
        access_token = resp1.get_json()['access_token']

        # refresh_token 없이 로그아웃
        logout_resp = client.post('/api/auth/logout',
            json={},
            headers={'Authorization': f'Bearer {access_token}'}
        )
        assert logout_resp.status_code == 200

        # DB 확인: 모든 토큰 revoked
        cursor = db_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM auth.refresh_tokens "
            "WHERE worker_id = %s AND revoked = FALSE",
            (worker_id,)
        )
        row = cursor.fetchone()
        assert row['cnt'] == 0

    # ------------------------------------------------------------------
    # TC-TDB-07: device_id 기반 rotation — 다른 기기 토큰 유지
    # ------------------------------------------------------------------
    def test_rotation_per_device(self, client, create_test_worker, db_conn):
        """TC-TDB-07: device A refresh 시 device B 토큰은 유지"""
        ts = int(time.time() * 1000)
        email = f'tdb07_{ts}@test.com'
        worker_id = create_test_worker(
            email=email, password='Test123!', name='TDB07',
            role='MECH', company='FNI'
        )

        # device-A, device-B 각각 로그인
        resp_a = client.post('/api/auth/login', json={
            'email': email, 'password': 'Test123!',
            'device_id': 'device-A',
        })
        resp_b = client.post('/api/auth/login', json={
            'email': email, 'password': 'Test123!',
            'device_id': 'device-B',
        })
        token_a = resp_a.get_json()['refresh_token']
        token_b = resp_b.get_json()['refresh_token']

        # device-A에서 refresh → device-A 이전 토큰만 revoked
        client.post('/api/auth/refresh', json={
            'refresh_token': token_a,
            'device_id': 'device-A',
        })

        # device-B 토큰은 여전히 유효
        resp_b2 = client.post('/api/auth/refresh', json={
            'refresh_token': token_b,
            'device_id': 'device-B',
        })
        assert resp_b2.status_code == 200

    # ------------------------------------------------------------------
    # TC-TDB-08: token_hash가 SHA256 형식 (64자 hex)
    # ------------------------------------------------------------------
    def test_token_hash_format(self, client, create_test_worker, db_conn):
        """TC-TDB-08: DB에 저장된 token_hash가 SHA256 해시 (64자 hex)"""
        ts = int(time.time() * 1000)
        email = f'tdb08_{ts}@test.com'
        worker_id = create_test_worker(
            email=email, password='Test123!', name='TDB08',
            role='MECH', company='FNI'
        )

        client.post('/api/auth/login', json={
            'email': email, 'password': 'Test123!',
        })

        cursor = db_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT token_hash FROM auth.refresh_tokens "
            "WHERE worker_id = %s LIMIT 1",
            (worker_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert len(row['token_hash']) == 64  # SHA256 hex digest
        # 올바른 hex 문자만 포함
        int(row['token_hash'], 16)

    # ------------------------------------------------------------------
    # TC-TDB-09: PIN 로그인 시에도 refresh_token DB 저장
    # ------------------------------------------------------------------
    def test_pin_login_stores_token(self, client, create_test_worker, db_conn):
        """TC-TDB-09: PIN 로그인 시 auth.refresh_tokens에 토큰 저장"""
        ts = int(time.time() * 1000)
        email = f'tdb09_{ts}@test.com'
        worker_id = create_test_worker(
            email=email, password='Test123!', name='TDB09',
            role='MECH', company='FNI'
        )

        # PIN 등록 (DB 직접)
        from werkzeug.security import generate_password_hash
        pin_hash = generate_password_hash('1234')

        cursor = db_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            INSERT INTO hr.worker_auth_settings (worker_id, pin_hash)
            VALUES (%s, %s)
            ON CONFLICT (worker_id) DO UPDATE SET pin_hash = EXCLUDED.pin_hash
        """, (worker_id, pin_hash))
        db_conn.commit()

        # 기존 토큰 수 확인
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM auth.refresh_tokens WHERE worker_id = %s",
            (worker_id,)
        )
        before_count = cursor.fetchone()['cnt']

        # PIN 로그인
        resp = client.post('/api/auth/pin-login', json={
            'worker_id': worker_id,
            'pin': '1234',
            'device_id': 'pin-device-tdb09',
        })
        assert resp.status_code == 200

        # DB에 새 토큰 저장 확인
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM auth.refresh_tokens WHERE worker_id = %s",
            (worker_id,)
        )
        after_count = cursor.fetchone()['cnt']
        assert after_count > before_count

    # ------------------------------------------------------------------
    # TC-TDB-10: 로그아웃 엔드포인트 — 인증 없이 호출 시 401
    # ------------------------------------------------------------------
    def test_logout_requires_auth(self, client):
        """TC-TDB-10: POST /auth/logout — JWT 없이 호출 시 401"""
        resp = client.post('/api/auth/logout', json={})
        assert resp.status_code == 401
