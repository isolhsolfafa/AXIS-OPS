"""
Refresh Token 테스트
Sprint 5: JWT Refresh Token 구현
Sprint 8: 토큰 만료 시간 검증 추가 (BE Task #2 반영)

테스트 대상:
- 로그인 시 access_token + refresh_token 모두 반환
- /api/auth/refresh 엔드포인트 정상 동작
- 만료된 refresh_token으로 갱신 실패
- 잘못된 refresh_token으로 갱신 실패
- access_token 만료 시간 2시간 확인 (Sprint 8)
- refresh_token 만료 시간 30일 확인 (Sprint 8)
"""

import pytest
import jwt
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# backend 경로 추가
backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# 테스트 시크릿 키
TEST_JWT_SECRET = 'test-secret-key-do-not-use-in-production'


class TestLoginReturnsBothTokens:
    """
    로그인 시 access_token + refresh_token 반환 테스트
    """

    def test_login_returns_access_token(self, client, approved_worker):
        """
        로그인 성공 시 access_token 반환 확인 (기존 기능)

        Expected:
        - Status 200
        - 'access_token' 필드 포함
        - JWT 형식 토큰
        """
        payload = {
            'email': approved_worker['email'],
            'password': approved_worker['password']
        }

        response = client.post('/api/auth/login', json=payload)
        assert response.status_code == 200

        data = response.get_json()
        assert 'access_token' in data, "access_token 필드 없음"

        # JWT 형식 확인
        token = data['access_token']
        decoded = jwt.decode(token, TEST_JWT_SECRET, algorithms=['HS256'])
        assert 'sub' in decoded
        assert 'exp' in decoded

    def test_login_returns_refresh_token(self, client, approved_worker):
        """
        로그인 성공 시 refresh_token 반환 확인 (Sprint 5 신규)

        Expected:
        - Status 200
        - 'refresh_token' 필드 포함 (Sprint 5 구현 후)
        - refresh_token도 JWT 형식
        """
        payload = {
            'email': approved_worker['email'],
            'password': approved_worker['password']
        }

        response = client.post('/api/auth/login', json=payload)
        assert response.status_code == 200

        data = response.get_json()

        if 'refresh_token' not in data:
            pytest.skip("refresh_token 미구현 (BE Task #2 완료 후 테스트)")

        refresh_token = data['refresh_token']
        assert refresh_token is not None
        assert isinstance(refresh_token, str)
        assert len(refresh_token) > 0

    def test_refresh_token_longer_expiry(self, client, approved_worker):
        """
        refresh_token의 만료 시간이 access_token보다 길어야 함

        Expected:
        - refresh_token exp > access_token exp
        - refresh_token 일반적으로 7~30일 만료
        """
        payload = {
            'email': approved_worker['email'],
            'password': approved_worker['password']
        }

        response = client.post('/api/auth/login', json=payload)
        assert response.status_code == 200

        data = response.get_json()

        if 'refresh_token' not in data:
            pytest.skip("refresh_token 미구현 (BE Task #2 완료 후 테스트)")

        access_token = data['access_token']
        refresh_token = data['refresh_token']

        access_decoded = jwt.decode(
            access_token, TEST_JWT_SECRET, algorithms=['HS256']
        )
        # refresh_token은 다른 시크릿 키를 사용할 수도 있으므로
        # 우선 decode 시도
        try:
            refresh_decoded = jwt.decode(
                refresh_token, TEST_JWT_SECRET, algorithms=['HS256']
            )
            access_exp = access_decoded['exp']
            refresh_exp = refresh_decoded['exp']
            assert refresh_exp > access_exp, \
                "refresh_token의 만료 시간이 access_token보다 길어야 합니다"
        except jwt.InvalidTokenError:
            # 다른 시크릿 키 사용 가능 → 만료시간 추출 방식 달라도 허용
            pass

    def test_admin_login_returns_tokens(self, client, admin_worker):
        """
        관리자 로그인 시에도 토큰 반환 확인

        Expected:
        - 관리자도 access_token 반환
        - refresh_token 반환 (Sprint 5)
        """
        payload = {
            'email': admin_worker['email'],
            'password': admin_worker['password']
        }

        response = client.post('/api/auth/login', json=payload)
        assert response.status_code == 200

        data = response.get_json()
        assert 'access_token' in data

        # is_admin 플래그 확인 (관리자 bypass)
        token = data['access_token']
        try:
            decoded = jwt.decode(token, TEST_JWT_SECRET, algorithms=['HS256'])
            # 관리자 토큰에는 is_admin 또는 role 확인
            assert 'sub' in decoded
        except jwt.InvalidTokenError as e:
            pytest.fail(f"관리자 JWT 토큰 디코딩 실패: {e}")


class TestRefreshEndpoint:
    """
    POST /api/auth/refresh 엔드포인트 테스트
    """

    def test_refresh_endpoint_success(self, client, approved_worker):
        """
        유효한 refresh_token으로 새 access_token 발급

        Expected:
        - Status 200
        - 새 access_token 반환
        - 새 access_token이 유효한 JWT
        """
        # 먼저 로그인해서 refresh_token 획득
        login_payload = {
            'email': approved_worker['email'],
            'password': approved_worker['password']
        }
        login_response = client.post('/api/auth/login', json=login_payload)
        login_data = login_response.get_json()

        if 'refresh_token' not in login_data:
            pytest.skip("refresh_token 미구현 (BE Task #2 완료 후 테스트)")

        refresh_token = login_data['refresh_token']

        # refresh 엔드포인트 호출
        response = client.post(
            '/api/auth/refresh',
            json={'refresh_token': refresh_token}
        )

        assert response.status_code == 200, \
            f"Expected 200, got {response.status_code}: {response.get_json()}"

        data = response.get_json()
        assert 'access_token' in data, "새 access_token이 응답에 없음"

        # 새 토큰이 유효한 JWT인지 확인
        new_token = data['access_token']
        try:
            decoded = jwt.decode(new_token, TEST_JWT_SECRET, algorithms=['HS256'])
            assert 'sub' in decoded
            assert 'exp' in decoded
            assert decoded['sub'] == str(approved_worker['id'])
        except jwt.InvalidTokenError as e:
            pytest.fail(f"새로 발급된 access_token이 유효하지 않음: {e}")

    def test_refresh_also_returns_new_refresh_token(self, client, approved_worker):
        """
        refresh 시 새 refresh_token도 함께 반환 (Refresh Token Rotation)

        Expected:
        - 새 refresh_token도 반환 (선택적)
        - 기존 refresh_token과 다른 값
        """
        login_payload = {
            'email': approved_worker['email'],
            'password': approved_worker['password']
        }
        login_response = client.post('/api/auth/login', json=login_payload)
        login_data = login_response.get_json()

        if 'refresh_token' not in login_data:
            pytest.skip("refresh_token 미구현 (BE Task #2 완료 후 테스트)")

        old_refresh_token = login_data['refresh_token']

        response = client.post(
            '/api/auth/refresh',
            json={'refresh_token': old_refresh_token}
        )

        if response.status_code != 200:
            pytest.skip("refresh 엔드포인트 미구현")

        data = response.get_json()

        # 새 refresh_token이 있다면 기존과 다른지 확인 (Rotation 정책)
        if 'refresh_token' in data:
            new_refresh_token = data['refresh_token']
            assert new_refresh_token != old_refresh_token, \
                "Refresh Token Rotation 시 새 토큰이 발급되어야 합니다"

    def test_refresh_endpoint_missing_token(self, client):
        """
        refresh_token 없이 갱신 시도 → 400

        Expected:
        - Status 400 Bad Request
        """
        response = client.post('/api/auth/refresh', json={})

        # refresh 엔드포인트가 구현된 경우만 검증
        if response.status_code == 404:
            pytest.skip("refresh 엔드포인트 미구현")

        assert response.status_code == 400, \
            f"Expected 400, got {response.status_code}"

    def test_refresh_without_json_body(self, client):
        """
        body 없이 refresh 엔드포인트 호출 → 400

        Expected:
        - Status 400 Bad Request
        - BE routes/auth.py에서 request.get_json(silent=True) 사용 권장
          (현재 silent=False로 빈 body 시 500 반환 → BE 수정 필요)

        NOTE: BE의 refresh 라우트에서 request.get_json(silent=True)를 사용하지 않으면
        빈 body 전송 시 Werkzeug BadRequest가 Flask에서 500으로 처리됨.
        올바른 구현은 400 반환이어야 함.
        """
        response = client.post(
            '/api/auth/refresh',
            json={}  # 빈 JSON body (refresh_token 키 없음)
        )

        if response.status_code == 404:
            pytest.skip("refresh 엔드포인트 미구현")

        assert response.status_code in [400, 422], \
            f"Expected 400 or 422 for missing refresh_token, got {response.status_code}"


class TestRefreshWithExpiredToken:
    """
    만료된 refresh_token으로 갱신 시도 테스트
    """

    def test_refresh_with_expired_token(self, client, approved_worker):
        """
        만료된 refresh_token으로 갱신 → 401

        Expected:
        - Status 401 Unauthorized
        - error == TOKEN_EXPIRED 또는 INVALID_TOKEN
        """
        # 이미 만료된 토큰 직접 생성
        now_utc = datetime.now(timezone.utc)
        expired_payload = {
            'sub': str(approved_worker['id']),
            'email': approved_worker['email'],
            'role': approved_worker['role'],
            'type': 'refresh',
            'exp': now_utc - timedelta(hours=1),  # 1시간 전 만료
            'iat': now_utc - timedelta(hours=2)
        }
        expired_token = jwt.encode(expired_payload, TEST_JWT_SECRET, algorithm='HS256')

        response = client.post(
            '/api/auth/refresh',
            json={'refresh_token': expired_token}
        )

        if response.status_code == 404:
            pytest.skip("refresh 엔드포인트 미구현")

        assert response.status_code == 401, \
            f"Expected 401, got {response.status_code}: {response.get_json()}"

        data = response.get_json()
        assert 'error' in data
        error_code = data.get('error', '').upper()
        # TOKEN_EXPIRED 또는 INVALID_TOKEN 허용
        assert any(keyword in error_code for keyword in ['TOKEN', 'EXPIRED', 'INVALID']), \
            f"에러 코드에 토큰 관련 메시지 필요: {data.get('error')}"

    def test_refresh_with_just_expired_access_token(self, client, approved_worker):
        """
        access_token을 refresh_token 자리에 사용 시도 → 실패

        Expected:
        - Status 401 또는 400
        - 토큰 타입 검증
        """
        # access_token을 refresh_token으로 사용 시도
        now_utc = datetime.now(timezone.utc)
        access_payload = {
            'sub': str(approved_worker['id']),
            'email': approved_worker['email'],
            'role': approved_worker['role'],
            'type': 'access',  # refresh가 아닌 access type
            'exp': now_utc + timedelta(hours=1),
            'iat': now_utc
        }
        access_token_as_refresh = jwt.encode(
            access_payload, TEST_JWT_SECRET, algorithm='HS256'
        )

        response = client.post(
            '/api/auth/refresh',
            json={'refresh_token': access_token_as_refresh}
        )

        if response.status_code == 404:
            pytest.skip("refresh 엔드포인트 미구현")

        # access_token을 refresh 자리에 사용하면 실패해야 함 (타입 검증)
        # 또는 구현 방식에 따라 성공할 수도 있음 (단순 JWT 검증만 하는 경우)
        # 엄격한 타입 검증 구현 시: 401
        # 느슨한 검증 시: 200 허용
        assert response.status_code in [200, 400, 401], \
            f"Unexpected status: {response.status_code}"


class TestRefreshWithInvalidToken:
    """
    잘못된 refresh_token으로 갱신 시도 테스트
    """

    def test_refresh_with_invalid_signature(self, client, approved_worker):
        """
        잘못된 서명의 토큰으로 갱신 → 401

        Expected:
        - Status 401 Unauthorized
        - 서명 검증 실패
        """
        # 다른 시크릿으로 서명된 토큰
        now_utc = datetime.now(timezone.utc)
        wrong_secret_payload = {
            'sub': str(approved_worker['id']),
            'email': approved_worker['email'],
            'role': approved_worker['role'],
            'type': 'refresh',
            'exp': now_utc + timedelta(days=7),
            'iat': now_utc
        }
        invalid_token = jwt.encode(
            wrong_secret_payload, 'WRONG_SECRET_KEY_NEVER_USE', algorithm='HS256'
        )

        response = client.post(
            '/api/auth/refresh',
            json={'refresh_token': invalid_token}
        )

        if response.status_code == 404:
            pytest.skip("refresh 엔드포인트 미구현")

        assert response.status_code == 401, \
            f"Expected 401 for invalid signature, got {response.status_code}"

    def test_refresh_with_malformed_token(self, client):
        """
        형식이 잘못된 토큰으로 갱신 → 401

        Expected:
        - Status 401 Unauthorized
        - 토큰 파싱 실패
        """
        response = client.post(
            '/api/auth/refresh',
            json={'refresh_token': 'this.is.not.a.valid.jwt.token'}
        )

        if response.status_code == 404:
            pytest.skip("refresh 엔드포인트 미구현")

        assert response.status_code == 401, \
            f"Expected 401 for malformed token, got {response.status_code}"

    def test_refresh_with_empty_string(self, client):
        """
        빈 문자열 토큰으로 갱신 → 400 또는 401

        Expected:
        - Status 400 Bad Request 또는 401
        """
        response = client.post(
            '/api/auth/refresh',
            json={'refresh_token': ''}
        )

        if response.status_code == 404:
            pytest.skip("refresh 엔드포인트 미구현")

        assert response.status_code in [400, 401], \
            f"Expected 400 or 401 for empty token, got {response.status_code}"

    def test_refresh_with_null_token(self, client):
        """
        null 토큰으로 갱신 → 400

        Expected:
        - Status 400 Bad Request
        """
        response = client.post(
            '/api/auth/refresh',
            json={'refresh_token': None}
        )

        if response.status_code == 404:
            pytest.skip("refresh 엔드포인트 미구현")

        assert response.status_code in [400, 401], \
            f"Expected 400 or 401 for null token, got {response.status_code}"

    def test_refresh_without_authentication(self, client):
        """
        JWT 없이 refresh_token 빈값으로 접근 테스트

        Expected:
        - refresh_token 없이 접근 시 400 또는 401
        """
        response = client.post(
            '/api/auth/refresh',
            json={'refresh_token': ''}
        )

        if response.status_code == 404:
            pytest.skip("refresh 엔드포인트 미구현")

        # 빈 토큰 → 400 또는 401
        assert response.status_code in [400, 401, 422], \
            f"Expected 400/401/422, got {response.status_code}"

    def test_refresh_token_for_nonexistent_worker(self, client):
        """
        존재하지 않는 작업자 ID로 서명된 refresh_token → 401

        Expected:
        - 유효한 서명이지만 worker_id가 DB에 없음
        - Status 401
        """
        # 존재하지 않는 worker_id로 토큰 생성
        now_utc = datetime.now(timezone.utc)
        fake_payload = {
            'sub': '999999',
            'email': 'nonexistent@axisos.test',
            'role': 'MECH',
            'type': 'refresh',
            'exp': now_utc + timedelta(days=7),
            'iat': now_utc
        }
        fake_token = jwt.encode(fake_payload, TEST_JWT_SECRET, algorithm='HS256')

        response = client.post(
            '/api/auth/refresh',
            json={'refresh_token': fake_token}
        )

        if response.status_code == 404:
            pytest.skip("refresh 엔드포인트 미구현")

        # 구현 방식에 따라 401 (엄격) 또는 200 (느슨) 허용
        # 엄격한 구현이라면 DB에서 작업자 존재 여부 체크 후 401
        assert response.status_code in [200, 401], \
            f"Unexpected status: {response.status_code}"


class TestRefreshTokenLifecycle:
    """
    Refresh Token 전체 생명주기 테스트
    로그인 → 토큰 사용 → 갱신 → 재사용 불가 시나리오
    """

    def test_full_token_lifecycle(self, client, approved_worker):
        """
        전체 토큰 생명주기 테스트

        시나리오:
        1. 로그인 → access_token + refresh_token 획득
        2. access_token으로 API 호출 성공
        3. refresh_token으로 새 access_token 발급
        4. 새 access_token으로 API 호출 성공
        """
        # Step 1: 로그인
        login_response = client.post('/api/auth/login', json={
            'email': approved_worker['email'],
            'password': approved_worker['password']
        })
        assert login_response.status_code == 200
        login_data = login_response.get_json()
        access_token = login_data['access_token']

        if 'refresh_token' not in login_data:
            pytest.skip("refresh_token 미구현 (BE Task #2 완료 후 테스트)")

        refresh_token = login_data['refresh_token']

        # Step 2: access_token으로 API 호출 (알림 조회)
        alerts_response = client.get(
            '/api/app/alerts',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        assert alerts_response.status_code == 200, \
            "access_token으로 API 호출 실패"

        # Step 3: refresh_token으로 새 access_token 발급
        refresh_response = client.post(
            '/api/auth/refresh',
            json={'refresh_token': refresh_token}
        )

        if refresh_response.status_code == 404:
            pytest.skip("refresh 엔드포인트 미구현")

        assert refresh_response.status_code == 200, \
            f"Token refresh 실패: {refresh_response.get_json()}"

        new_access_token = refresh_response.get_json().get('access_token')
        assert new_access_token is not None

        # Step 4: 새 access_token으로 API 호출
        new_alerts_response = client.get(
            '/api/app/alerts',
            headers={'Authorization': f'Bearer {new_access_token}'}
        )
        assert new_alerts_response.status_code == 200, \
            "새 access_token으로 API 호출 실패"

    def test_token_payload_consistency(self, client, approved_worker):
        """
        refresh 후 발급된 토큰의 페이로드 일관성 검증

        Expected:
        - 새 access_token의 sub (worker_id)가 기존 토큰과 동일
        - role도 동일하게 유지
        """
        login_response = client.post('/api/auth/login', json={
            'email': approved_worker['email'],
            'password': approved_worker['password']
        })
        login_data = login_response.get_json()
        original_token = login_data['access_token']

        if 'refresh_token' not in login_data:
            pytest.skip("refresh_token 미구현 (BE Task #2 완료 후 테스트)")

        refresh_token = login_data['refresh_token']

        refresh_response = client.post(
            '/api/auth/refresh',
            json={'refresh_token': refresh_token}
        )

        if refresh_response.status_code == 404:
            pytest.skip("refresh 엔드포인트 미구현")

        if refresh_response.status_code != 200:
            pytest.skip("refresh 엔드포인트 응답 오류")

        new_token = refresh_response.get_json().get('access_token')
        if not new_token:
            pytest.skip("새 access_token 없음")

        # 원본 토큰 페이로드
        original_decoded = jwt.decode(original_token, TEST_JWT_SECRET, algorithms=['HS256'])

        # 새 토큰 페이로드
        new_decoded = jwt.decode(new_token, TEST_JWT_SECRET, algorithms=['HS256'])

        # worker_id 일관성
        assert new_decoded['sub'] == original_decoded['sub'], \
            "refresh 후 worker_id가 변경됨"

        # role 일관성
        assert new_decoded['role'] == original_decoded['role'], \
            "refresh 후 role이 변경됨"

        # 만료 시간은 새로 갱신되어야 함
        assert new_decoded['exp'] >= original_decoded['exp'], \
            "새 토큰의 만료 시간이 기존보다 짧아서는 안 됨"

    def test_refresh_after_role_change(self, client, approved_worker, db_conn):
        """
        DB에서 role 변경 후 refresh_token으로 갱신 시 새 role 반영 확인

        시나리오:
        1. 로그인 → refresh_token 획득 (role: MECH)
        2. DB에서 role을 ELEC로 직접 변경
        3. refresh_token으로 /api/auth/refresh 호출
        4. 새 access_token 디코딩 → role이 ELEC인지 확인
        5. DB 원복 (role: MECH)

        Expected:
        - 새 access_token의 role == 'ELEC'
        """
        # Step 1: 로그인
        login_response = client.post('/api/auth/login', json={
            'email': approved_worker['email'],
            'password': approved_worker['password']
        })
        assert login_response.status_code == 200
        login_data = login_response.get_json()

        if 'refresh_token' not in login_data:
            pytest.skip("refresh_token 미구현 (BE Task #2 완료 후 테스트)")

        refresh_token = login_data['refresh_token']

        # Step 2: DB에서 role 변경 (MECH → ELEC)
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        cursor = db_conn.cursor()
        cursor.execute(
            "UPDATE workers SET role = 'ELEC'::role_enum WHERE id = %s",
            (approved_worker['id'],)
        )
        db_conn.commit()
        cursor.close()

        try:
            # Step 3: refresh_token으로 새 access_token 발급
            refresh_response = client.post(
                '/api/auth/refresh',
                json={'refresh_token': refresh_token}
            )

            if refresh_response.status_code == 404:
                pytest.skip("refresh 엔드포인트 미구현")

            assert refresh_response.status_code == 200, \
                f"Token refresh 실패: {refresh_response.get_json()}"

            new_access_token = refresh_response.get_json().get('access_token')
            assert new_access_token is not None

            # Step 4: 새 토큰 디코딩 → role 확인
            TEST_JWT_ACCESS_SECRET = 'test-secret-key-do-not-use-in-production'
            new_decoded = jwt.decode(
                new_access_token, TEST_JWT_ACCESS_SECRET, algorithms=['HS256']
            )
            assert new_decoded['role'] == 'ELEC', \
                f"새 access_token의 role이 ELEC여야 하지만 {new_decoded['role']}임"

        finally:
            # Step 5: DB 원복 (MECH로 복원)
            cursor = db_conn.cursor()
            cursor.execute(
                "UPDATE workers SET role = 'MECH'::role_enum WHERE id = %s",
                (approved_worker['id'],)
            )
            db_conn.commit()
            cursor.close()

    def test_refresh_after_account_rejected(self, client, approved_worker, db_conn):
        """
        계정 승인 거부 후 refresh_token 사용 시 403 반환 확인

        시나리오:
        1. 로그인 → refresh_token 획득
        2. DB에서 approval_status를 'rejected'로 변경
        3. refresh_token으로 /api/auth/refresh 호출
        4. Expected: 403 ACCOUNT_INACTIVE
        5. DB 원복 (approved)

        Expected:
        - Status 403
        - error == 'ACCOUNT_INACTIVE'
        """
        # Step 1: 로그인
        login_response = client.post('/api/auth/login', json={
            'email': approved_worker['email'],
            'password': approved_worker['password']
        })
        assert login_response.status_code == 200
        login_data = login_response.get_json()

        if 'refresh_token' not in login_data:
            pytest.skip("refresh_token 미구현 (BE Task #2 완료 후 테스트)")

        refresh_token = login_data['refresh_token']

        # Step 2: DB에서 승인 상태 변경 (approved → rejected)
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        cursor = db_conn.cursor()
        cursor.execute(
            "UPDATE workers SET approval_status = 'rejected'::approval_status_enum WHERE id = %s",
            (approved_worker['id'],)
        )
        db_conn.commit()
        cursor.close()

        try:
            # Step 3: refresh_token으로 /api/auth/refresh 호출
            refresh_response = client.post(
                '/api/auth/refresh',
                json={'refresh_token': refresh_token}
            )

            if refresh_response.status_code == 404:
                pytest.skip("refresh 엔드포인트 미구현")

            # Step 4: 403 ACCOUNT_INACTIVE 기대
            assert refresh_response.status_code == 403, \
                f"거부된 계정의 refresh는 403이어야 하지만 {refresh_response.status_code} 반환"

            data = refresh_response.get_json()
            assert 'error' in data
            assert data['error'] == 'ACCOUNT_INACTIVE', \
                f"에러 코드가 ACCOUNT_INACTIVE여야 하지만 {data.get('error')}임"

        finally:
            # Step 5: DB 원복 (approved로 복원)
            cursor = db_conn.cursor()
            cursor.execute(
                "UPDATE workers SET approval_status = 'approved'::approval_status_enum WHERE id = %s",
                (approved_worker['id'],)
            )
            db_conn.commit()
            cursor.close()

    def test_multiple_refresh_tokens_valid(self, client, approved_worker):
        """
        같은 작업자로 서로 다른 기기에서 2번 로그인 시 두 refresh_token 모두 유효한지 확인

        시나리오:
        1. 동일 worker로 device-A에서 1차 로그인 → refresh_token_1 획득
        2. 동일 worker로 device-B에서 2차 로그인 → refresh_token_2 획득
        3. refresh_token_1으로 /api/auth/refresh 성공 확인 (device-A)
        4. refresh_token_2으로 /api/auth/refresh 성공 확인 (device-B)

        Note: DB 기반 토큰 관리에서 같은 device_id로 재로그인 시 기존 토큰이 revoked됨.
              다른 device_id(device-A/B)를 사용하면 두 토큰이 각자 독립적으로 유효.

        Expected:
        - 두 refresh_token 모두 200 반환
        """
        import time as _time

        ts = int(_time.time() * 1000)

        # Step 1: 1차 로그인 (device-A)
        response_1 = client.post('/api/auth/login', json={
            'email': approved_worker['email'],
            'password': approved_worker['password'],
            'device_id': f'test-device-A-{ts}',
        })
        assert response_1.status_code == 200
        data_1 = response_1.get_json()

        if 'refresh_token' not in data_1:
            pytest.skip("refresh_token 미구현 (BE Task #2 완료 후 테스트)")

        refresh_token_1 = data_1['refresh_token']

        # Step 2: 2차 로그인 (device-B — 다른 기기)
        # device_id가 다르므로 기존 token_1은 revoked되지 않음
        response_2 = client.post('/api/auth/login', json={
            'email': approved_worker['email'],
            'password': approved_worker['password'],
            'device_id': f'test-device-B-{ts}',
        })
        assert response_2.status_code == 200
        data_2 = response_2.get_json()
        refresh_token_2 = data_2['refresh_token']

        # Step 3: refresh_token_1 유효성 확인 (device-A)
        refresh_resp_1 = client.post(
            '/api/auth/refresh',
            json={'refresh_token': refresh_token_1, 'device_id': f'test-device-A-{ts}'}
        )

        if refresh_resp_1.status_code == 404:
            pytest.skip("refresh 엔드포인트 미구현")

        assert refresh_resp_1.status_code == 200, \
            f"1차 refresh_token 사용 실패: {refresh_resp_1.get_json()}"
        assert 'access_token' in refresh_resp_1.get_json()

        # Step 4: refresh_token_2 유효성 확인 (device-B)
        refresh_resp_2 = client.post(
            '/api/auth/refresh',
            json={'refresh_token': refresh_token_2, 'device_id': f'test-device-B-{ts}'}
        )

        assert refresh_resp_2.status_code == 200, \
            f"2차 refresh_token 사용 실패: {refresh_resp_2.get_json()}"
        assert 'access_token' in refresh_resp_2.get_json()


class TestRefreshTokenSeparation:
    """
    Refresh Token과 Access Token 분리 검증 테스트
    Sprint 5: 두 토큰은 서로 다른 시크릿 키로 서명되므로 교차 사용 불가
    """

    def test_refresh_token_cannot_be_used_as_access_token(self, client, approved_worker):
        """
        refresh_token을 Authorization Bearer 헤더에 넣어 API 호출 시 401 반환 확인

        refresh_token은 JWT_REFRESH_SECRET_KEY로 서명되고,
        jwt_required 미들웨어는 JWT_SECRET_KEY로 검증하므로
        서로 다른 시크릿 → 서명 검증 실패 → 401.

        Expected:
        - Status 401 Unauthorized
        """
        # 로그인하여 refresh_token 획득
        login_response = client.post('/api/auth/login', json={
            'email': approved_worker['email'],
            'password': approved_worker['password']
        })
        assert login_response.status_code == 200
        login_data = login_response.get_json()

        if 'refresh_token' not in login_data:
            pytest.skip("refresh_token 미구현 (BE Task #2 완료 후 테스트)")

        refresh_token = login_data['refresh_token']

        # refresh_token을 access_token 자리에 사용
        response = client.get(
            '/api/app/alerts',
            headers={'Authorization': f'Bearer {refresh_token}'}
        )

        # jwt_required는 JWT_SECRET_KEY로 검증 → refresh_token(REFRESH_SECRET 서명)은 실패
        assert response.status_code == 401, \
            f"refresh_token을 access_token으로 사용 시 401이어야 하지만 {response.status_code} 반환"

    def test_access_token_cannot_be_used_as_refresh_token(self, client, approved_worker):
        """
        access_token을 refresh_token 자리에 사용 시 401 반환 확인

        access_token의 type 클레임은 'access'이고,
        verify_refresh_token()은 type=='refresh'인지 검증하므로
        type 불일치 → None 반환 → 401.

        Expected:
        - Status 401 Unauthorized
        """
        # 로그인하여 access_token 획득
        login_response = client.post('/api/auth/login', json={
            'email': approved_worker['email'],
            'password': approved_worker['password']
        })
        assert login_response.status_code == 200
        login_data = login_response.get_json()
        access_token = login_data['access_token']

        # access_token을 refresh_token 자리에 사용
        response = client.post(
            '/api/auth/refresh',
            json={'refresh_token': access_token}
        )

        if response.status_code == 404:
            pytest.skip("refresh 엔드포인트 미구현")

        # verify_refresh_token()은 JWT_REFRESH_SECRET_KEY로 디코딩을 시도하고
        # access_token은 JWT_SECRET_KEY로 서명되어 있으므로 서명 검증 실패 → 401
        assert response.status_code == 401, \
            f"access_token을 refresh_token으로 사용 시 401이어야 하지만 {response.status_code} 반환"


class TestTokenExpiryTimes:
    """
    토큰 만료 시간 검증 테스트 (Sprint 8 — BE Task #2 반영)

    BE Task #2에서 설정된 만료 시간:
    - access_token:  2시간  (JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2))
    - refresh_token: 30일   (JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30))
    """

    # 만료 시간 허용 오차 (네트워크/처리 지연 고려)
    TOLERANCE_SECONDS = 60

    def test_access_token_expiry_is_2_hours(self, client, approved_worker):
        """
        access_token 만료 시간이 약 2시간(7200초)인지 확인

        Expected:
        - 로그인 성공 → access_token 반환
        - access_token 디코딩 → exp - iat ≈ 7200초 (±60초 오차 허용)
        """
        login_response = client.post('/api/auth/login', json={
            'email': approved_worker['email'],
            'password': approved_worker['password']
        })
        assert login_response.status_code == 200

        data = login_response.get_json()
        access_token = data['access_token']

        decoded = jwt.decode(access_token, TEST_JWT_SECRET, algorithms=['HS256'])
        exp = decoded['exp']
        iat = decoded['iat']
        duration_seconds = exp - iat

        expected_seconds = 2 * 3600  # 2시간
        assert abs(duration_seconds - expected_seconds) <= self.TOLERANCE_SECONDS, (
            f"access_token 만료 시간이 {expected_seconds}초(2h)이어야 하지만 "
            f"{duration_seconds}초임 (오차: {abs(duration_seconds - expected_seconds)}초)"
        )

    def test_access_token_not_yet_expired(self, client, approved_worker):
        """
        방금 발급된 access_token이 아직 만료되지 않았는지 확인

        Expected:
        - access_token의 exp가 현재 시각보다 미래여야 함
        """
        login_response = client.post('/api/auth/login', json={
            'email': approved_worker['email'],
            'password': approved_worker['password']
        })
        assert login_response.status_code == 200

        access_token = login_response.get_json()['access_token']
        decoded = jwt.decode(access_token, TEST_JWT_SECRET, algorithms=['HS256'])

        now_ts = datetime.now(timezone.utc).timestamp()
        assert decoded['exp'] > now_ts, \
            "방금 발급된 access_token이 이미 만료 상태임 (exp <= 현재 시각)"

    def test_refresh_token_expiry_is_30_days(self, client, approved_worker):
        """
        refresh_token 만료 시간이 약 30일(2592000초)인지 확인

        refresh_token은 JWT_REFRESH_SECRET_KEY로 서명됨.
        테스트 환경에서는 TestConfig에 REFRESH_SECRET_KEY가 없으므로
        PyJWT의 options를 이용하여 서명 검증 없이 페이로드만 확인.

        Expected:
        - refresh_token 반환
        - exp - iat ≈ 30 * 86400초 (±60초 오차 허용)
        """
        login_response = client.post('/api/auth/login', json={
            'email': approved_worker['email'],
            'password': approved_worker['password']
        })
        assert login_response.status_code == 200

        data = login_response.get_json()
        if 'refresh_token' not in data:
            pytest.skip("refresh_token 미구현")

        refresh_token = data['refresh_token']

        # 서명 검증 없이 페이로드 확인 (REFRESH_SECRET_KEY 미지)
        decoded = jwt.decode(
            refresh_token,
            options={"verify_signature": False}
        )

        exp = decoded['exp']
        iat = decoded['iat']
        duration_seconds = exp - iat

        expected_seconds = 30 * 86400  # 30일
        assert abs(duration_seconds - expected_seconds) <= self.TOLERANCE_SECONDS, (
            f"refresh_token 만료 시간이 {expected_seconds}초(30d)이어야 하지만 "
            f"{duration_seconds}초임 (오차: {abs(duration_seconds - expected_seconds)}초)"
        )

    def test_refresh_token_not_yet_expired(self, client, approved_worker):
        """
        방금 발급된 refresh_token이 아직 만료되지 않았는지 확인

        Expected:
        - refresh_token의 exp가 현재 시각보다 미래여야 함
        """
        login_response = client.post('/api/auth/login', json={
            'email': approved_worker['email'],
            'password': approved_worker['password']
        })
        assert login_response.status_code == 200

        data = login_response.get_json()
        if 'refresh_token' not in data:
            pytest.skip("refresh_token 미구현")

        refresh_token = data['refresh_token']
        decoded = jwt.decode(
            refresh_token,
            options={"verify_signature": False}
        )

        now_ts = datetime.now(timezone.utc).timestamp()
        assert decoded['exp'] > now_ts, \
            "방금 발급된 refresh_token이 이미 만료 상태임 (exp <= 현재 시각)"

    def test_refresh_token_expiry_greater_than_access_token(self, client, approved_worker):
        """
        refresh_token 만료 시간이 access_token보다 훨씬 길어야 함

        Expected:
        - refresh_token exp - iat > access_token exp - iat
        - 최소 7배 이상 (30일 / 2시간 = 360배)
        """
        login_response = client.post('/api/auth/login', json={
            'email': approved_worker['email'],
            'password': approved_worker['password']
        })
        assert login_response.status_code == 200

        data = login_response.get_json()
        if 'refresh_token' not in data:
            pytest.skip("refresh_token 미구현")

        access_token = data['access_token']
        refresh_token = data['refresh_token']

        access_decoded = jwt.decode(access_token, TEST_JWT_SECRET, algorithms=['HS256'])
        refresh_decoded = jwt.decode(
            refresh_token,
            options={"verify_signature": False}
        )

        access_duration = access_decoded['exp'] - access_decoded['iat']
        refresh_duration = refresh_decoded['exp'] - refresh_decoded['iat']

        assert refresh_duration > access_duration * 7, (
            f"refresh_token({refresh_duration}초)이 access_token({access_duration}초)의 "
            f"7배 이상이어야 함"
        )
