"""
Refresh Token Rotation + Device ID 테스트 (Sprint 19-A)
엔드포인트:
  POST /api/auth/refresh  — rotation: access_token + refresh_token 반환
  POST /api/auth/login    — device_id 수신
  POST /api/auth/pin-login — device_id 수신
"""

import time
import pytest


class TestTokenRotation:
    """Refresh Token Rotation 테스트 (TC-ROT-01 ~ TC-ROT-06)"""

    # ------------------------------------------------------------------
    # TC-ROT-01: /auth/refresh → 응답에 access_token + refresh_token 둘 다 포함
    # ------------------------------------------------------------------
    def test_refresh_returns_both_tokens(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-ROT-01: refresh 응답에 access_token + refresh_token 모두 포함"""
        worker_id = create_test_worker(
            email=f'rot01_{int(time.time()*1000)}@test.com',
            password='Test123!', name='Rotation Test',
            role='MECH', company='FNI'
        )

        # 로그인해서 refresh_token 획득
        login_resp = client.post('/api/auth/login', json={
            'email': f'rot01_{int(time.time()*1000)}@test.com',
            'password': 'Test123!',
        })
        # login이 실패할 수 있으니 conftest의 get_auth_token + 직접 refresh_token 생성
        from app.services.auth_service import AuthService
        auth_svc = AuthService()
        from app.models.worker import get_worker_by_id
        worker = get_worker_by_id(worker_id)
        refresh_token = auth_svc.create_refresh_token(
            worker_id=worker.id,
            email=worker.email
        )

        response = client.post('/api/auth/refresh', json={
            'refresh_token': refresh_token,
        })
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert data['refresh_token'] != refresh_token  # 새 토큰은 다를 수 있음

    # ------------------------------------------------------------------
    # TC-ROT-02: 새 refresh_token으로 다시 refresh → 성공
    # ------------------------------------------------------------------
    def test_new_refresh_token_works(self, client, create_test_worker, db_conn):
        """TC-ROT-02: rotation으로 받은 새 refresh_token으로 재차 refresh 성공"""
        worker_id = create_test_worker(
            email=f'rot02_{int(time.time()*1000)}@test.com',
            password='Test123!', name='Rotation Chain',
            role='MECH', company='FNI'
        )

        from app.services.auth_service import AuthService
        from app.models.worker import get_worker_by_id
        auth_svc = AuthService()
        worker = get_worker_by_id(worker_id)
        refresh_token = auth_svc.create_refresh_token(
            worker_id=worker.id,
            email=worker.email
        )

        # 1차 refresh
        resp1 = client.post('/api/auth/refresh', json={
            'refresh_token': refresh_token,
        })
        assert resp1.status_code == 200
        new_refresh = resp1.get_json()['refresh_token']

        # 2차 refresh (새 토큰으로)
        resp2 = client.post('/api/auth/refresh', json={
            'refresh_token': new_refresh,
        })
        assert resp2.status_code == 200
        assert 'access_token' in resp2.get_json()
        assert 'refresh_token' in resp2.get_json()

    # ------------------------------------------------------------------
    # TC-ROT-03: 이전 refresh_token으로도 refresh 가능 (Phase C에서 차단 예정)
    # ------------------------------------------------------------------
    def test_old_refresh_token_still_works(self, client, create_test_worker, db_conn):
        """TC-ROT-03: Phase A에서는 이전 refresh_token도 유효 (stateless JWT)"""
        worker_id = create_test_worker(
            email=f'rot03_{int(time.time()*1000)}@test.com',
            password='Test123!', name='Old Token Test',
            role='MECH', company='FNI'
        )

        from app.services.auth_service import AuthService
        from app.models.worker import get_worker_by_id
        auth_svc = AuthService()
        worker = get_worker_by_id(worker_id)
        old_refresh = auth_svc.create_refresh_token(
            worker_id=worker.id,
            email=worker.email
        )

        # rotation 수행
        resp1 = client.post('/api/auth/refresh', json={
            'refresh_token': old_refresh,
        })
        assert resp1.status_code == 200

        # 이전 토큰으로 다시 시도 → Phase A에서는 여전히 유효
        resp2 = client.post('/api/auth/refresh', json={
            'refresh_token': old_refresh,
        })
        assert resp2.status_code == 200

    # ------------------------------------------------------------------
    # TC-ROT-04: login 요청에 device_id 포함 → 정상 200 (에러 아님)
    # ------------------------------------------------------------------
    def test_login_with_device_id(self, client, create_test_worker, db_conn):
        """TC-ROT-04: login에 device_id 포함 시 정상 처리"""
        ts = int(time.time() * 1000)
        email = f'rot04_{ts}@test.com'
        create_test_worker(
            email=email,
            password='Test123!', name='Device ID Login',
            role='MECH', company='FNI'
        )

        response = client.post('/api/auth/login', json={
            'email': email,
            'password': 'Test123!',
            'device_id': 'test-device-uuid-1234',
        })
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data

    # ------------------------------------------------------------------
    # TC-ROT-05: device_id 미전송 → 에러 아님 (기본 'unknown' 처리)
    # ------------------------------------------------------------------
    def test_login_without_device_id(self, client, create_test_worker, db_conn):
        """TC-ROT-05: device_id 없이 로그인해도 정상 처리"""
        ts = int(time.time() * 1000)
        email = f'rot05_{ts}@test.com'
        create_test_worker(
            email=email,
            password='Test123!', name='No Device ID',
            role='MECH', company='FNI'
        )

        response = client.post('/api/auth/login', json={
            'email': email,
            'password': 'Test123!',
            # device_id 없음
        })
        assert response.status_code == 200

    # ------------------------------------------------------------------
    # TC-ROT-06: refresh 요청에 device_id 포함 → 정상 처리
    # ------------------------------------------------------------------
    def test_refresh_with_device_id(self, client, create_test_worker, db_conn):
        """TC-ROT-06: refresh에 device_id 포함 시 정상 처리 + rotation"""
        worker_id = create_test_worker(
            email=f'rot06_{int(time.time()*1000)}@test.com',
            password='Test123!', name='Device Refresh',
            role='MECH', company='FNI'
        )

        from app.services.auth_service import AuthService
        from app.models.worker import get_worker_by_id
        auth_svc = AuthService()
        worker = get_worker_by_id(worker_id)
        refresh_token = auth_svc.create_refresh_token(
            worker_id=worker.id,
            email=worker.email
        )

        response = client.post('/api/auth/refresh', json={
            'refresh_token': refresh_token,
            'device_id': 'test-device-uuid-5678',
        })
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
        assert 'refresh_token' in data
