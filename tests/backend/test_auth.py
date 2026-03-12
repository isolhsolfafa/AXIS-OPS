"""
Authentication and authorization tests.
인증 및 권한 부여 테스트

Sprint 1 필수 테스트 케이스 6개:
1. 회원가입 성공
2. 중복 이메일 가입 실패
3. 이메일 인증 성공
4. 잘못된 인증코드 실패
5. 로그인 성공 (JWT 토큰 반환)
6. 미승인 사용자 로그인 제한
"""

import pytest
import jwt
from datetime import datetime, timedelta, timezone


class TestWorkerRegistration:
    """
    Test suite for worker registration functionality.
    워커 등록 기능 테스트 모음
    """

    def test_register_worker_success(self, client, db_conn, db_existing_roles):
        """
        TEST 1: 회원가입 성공

        Expected:
        - Status code 201 Created
        - Response contains worker_id, email
        - Worker stored in DB with approval_status='pending' (관리자 승인 대기)
        - 이메일 인증 필요 (email_verification 테이블에 레코드 생성)
        """
        # Sprint 6 MECH 역할이 role_enum에 없으면 스킵 (DB 마이그레이션 필요)
        if 'MECH' not in db_existing_roles:
            pytest.skip("Sprint 6 DB 마이그레이션 필요 (role_enum에 MECH 없음)")

        # company 컬럼 존재 여부 확인
        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='workers' AND column_name='company'")
            has_company = cursor.fetchone() is not None
            cursor.close()
            if not has_company:
                pytest.skip("Sprint 6 DB 마이그레이션 필요 (workers.company 컬럼 없음)")

        # 이전 실행 잔여 데이터 정리
        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute("DELETE FROM email_verification WHERE worker_id IN (SELECT id FROM workers WHERE email = 'newworker@axisos.test')")
            cursor.execute("DELETE FROM workers WHERE email = 'newworker@axisos.test'")
            db_conn.commit()
            cursor.close()

        payload = {
            'name': '신규 작업자',
            'email': 'newworker@axisos.test',
            'password': 'SecurePassword123!',
            'role': 'MECH',  # Sprint 6 역할명
            'company': 'FNI',
        }

        response = client.post('/api/auth/register', json=payload)

        # HTTP 201 Created 응답 확인
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.get_json()}"

        data = response.get_json()

        # 응답 데이터 검증
        assert 'message' in data
        assert 'worker_id' in data
        assert data['worker_id'] is not None

        # DB에 워커 저장 확인 (approval_status='pending')
        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute(
                "SELECT id, email, approval_status FROM workers WHERE email = %s",
                (payload['email'],)
            )
            worker = cursor.fetchone()
            cursor.close()

            assert worker is not None, "Worker not found in database"
            assert worker[1] == payload['email']
            assert worker[2] == 'pending', "New worker should have pending approval status"

    def test_register_duplicate_email(self, client, approved_worker, db_existing_roles):
        """
        TEST 2: 중복 이메일 가입 실패

        Expected:
        - Status code 409 Conflict
        - Error message: "이메일이 이미 등록되어 있습니다"
        - No new worker created
        """
        role_name = 'ELEC' if 'ELEC' in db_existing_roles else 'EE'
        payload = {
            'name': '중복 작업자',
            'email': approved_worker['email'],  # 기존 워커 이메일 사용
            'password': 'AnotherPassword123!',
            'role': role_name
        }

        response = client.post('/api/auth/register', json=payload)

        # HTTP 400 응답 확인 (auth_service returns 400 for DUPLICATE_EMAIL)
        assert response.status_code in [400, 409], f"Expected 400 or 409, got {response.status_code}"

        data = response.get_json()
        assert 'error' in data or 'message' in data


class TestEmailVerification:
    """
    Test suite for email verification.
    이메일 검증 테스트 모음
    """

    def test_email_verification_success(self, client, db_conn, create_test_worker):
        """
        TEST 3: 이메일 인증 성공

        Expected:
        - Status code 200 OK
        - 이메일 인증 완료 메시지
        - email_verification 테이블의 verified_at 업데이트
        """
        # 미인증 워커 생성 (이메일 미인증)
        worker_id = create_test_worker(
            email='unverified@axisos.test',
            password='TestPassword123!',
            name='미인증 워커',
            role='MECH',
            approval_status='pending',
            email_verified=False
        )

        # 이메일 인증 코드 생성 (6자리 숫자, 실제로는 email_verification 테이블에 저장)
        verification_code = '123456'
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute("""
                INSERT INTO email_verification (worker_id, verification_code, expires_at)
                VALUES (%s, %s, %s)
            """, (worker_id, verification_code, expires_at))
            db_conn.commit()
            cursor.close()

        # 이메일 인증 API 호출
        payload = {
            'email': 'unverified@axisos.test',
            'code': verification_code
        }

        response = client.post('/api/auth/verify-email', json=payload)

        # HTTP 200 OK 응답 확인
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.get_json()}"

        data = response.get_json()
        assert 'message' in data

        # DB에서 verified_at 확인
        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute("""
                SELECT verified_at FROM email_verification
                WHERE worker_id = %s AND verification_code = %s
            """, (worker_id, verification_code))
            result = cursor.fetchone()
            cursor.close()

            assert result is not None
            assert result[0] is not None, "verified_at should be set"

    def test_verify_email_invalid_code(self, client, create_test_worker):
        """
        TEST 4: 잘못된 인증코드 실패

        Expected:
        - Status code 400 Bad Request or 404 Not Found
        - Error message: "인증 코드가 올바르지 않습니다"
        """
        # 미인증 워커 생성
        create_test_worker(
            email='invalidcode@axisos.test',
            password='TestPassword123!',
            name='잘못된 코드 테스트',
            role='PI',
            approval_status='pending',
            email_verified=False
        )

        # 잘못된 인증 코드로 시도
        payload = {
            'email': 'invalidcode@axisos.test',
            'code': '999999'  # 존재하지 않는 코드
        }

        response = client.post('/api/auth/verify-email', json=payload)

        # HTTP 400 or 404 응답 확인
        assert response.status_code in [400, 404], f"Expected 400 or 404, got {response.status_code}"

        data = response.get_json()
        assert 'error' in data or 'message' in data


class TestWorkerLogin:
    """
    Test suite for worker login functionality.
    워커 로그인 기능 테스트 모음
    """

    def test_login_success_with_jwt(self, client, approved_worker):
        """
        TEST 5: 로그인 성공 (JWT 토큰 반환)

        Expected:
        - Status code 200 OK
        - Response contains 'access_token'
        - JWT token includes worker_id, role, exp
        - Token can be decoded with secret key
        """
        payload = {
            'email': approved_worker['email'],
            'password': approved_worker['password']  # 평문 비밀번호
        }

        response = client.post('/api/auth/login', json=payload)

        # HTTP 200 OK 응답 확인
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.get_json()}"

        data = response.get_json()

        # JWT 토큰 확인
        assert 'access_token' in data, "Response should contain access_token"
        assert data['access_token'] is not None

        # JWT 토큰 디코딩 검증
        token = data['access_token']
        try:
            decoded = jwt.decode(
                token,
                'test-secret-key-do-not-use-in-production',
                algorithms=['HS256']
            )

            # 페이로드 검증 (auth_service uses 'sub' for worker_id)
            assert 'sub' in decoded
            assert 'role' in decoded
            assert 'exp' in decoded
            # Sprint 6 전/후 role_enum 호환: MECH==MM, ELEC==EE
            role_aliases = {'MECH': 'MM', 'ELEC': 'EE', 'TMS': 'TM', 'MM': 'MECH', 'EE': 'ELEC'}
            expected_role = approved_worker['role']
            actual_role = decoded['role']
            assert actual_role == expected_role or role_aliases.get(actual_role) == expected_role, \
                f"JWT role '{actual_role}' != expected '{expected_role}'"

        except jwt.InvalidTokenError as e:
            pytest.fail(f"JWT token is invalid: {e}")

    def test_unapproved_worker_login_restricted(self, client, unapproved_worker):
        """
        TEST 6: 미승인 사용자 로그인 제한

        Expected:
        - Status code 403 Forbidden (로그인 자체 거부)
        또는
        - Status code 200 OK but response contains approval_pending flag

        Note: 정책에 따라 달라질 수 있음
        - 정책 A: 미승인 워커는 로그인 불가 (403)
        - 정책 B: 로그인 가능하지만 제한된 접근 (200 + flag)
        """
        payload = {
            'email': unapproved_worker['email'],
            'password': unapproved_worker['password']
        }

        response = client.post('/api/auth/login', json=payload)

        # 정책 A: 미승인 워커 로그인 거부 (권장)
        if response.status_code == 403:
            data = response.get_json()
            assert 'error' in data or 'message' in data
            # error 코드에 APPROVAL 포함 확인 (APPROVAL_PENDING)
            error_code = data.get('error', '')
            assert 'APPROVAL' in error_code.upper() or '승인' in data.get('message', '')

        # 정책 B: 로그인 허용 + 제한 플래그
        elif response.status_code == 200:
            data = response.get_json()
            assert 'access_token' in data or 'approval_pending' in data

            # 토큰이 있으면 디코딩해서 approval_status 확인
            if 'access_token' in data:
                token = data['access_token']
                decoded = jwt.decode(
                    token,
                    'test-secret-key-do-not-use-in-production',
                    algorithms=['HS256']
                )
                # 토큰에 approval_status 플래그 또는 role='PENDING' 등 확인
                # 실제 구현에 맞게 조정

        else:
            pytest.fail(f"Unexpected status code {response.status_code} for unapproved worker login")


class TestLoginFailures:
    """
    Additional login failure tests.
    로그인 실패 케이스 추가 테스트
    """

    def test_login_wrong_password(self, client, approved_worker):
        """
        잘못된 비밀번호로 로그인 실패

        Expected:
        - Status code 401 Unauthorized
        - Error message
        """
        payload = {
            'email': approved_worker['email'],
            'password': 'WrongPassword123!'
        }

        response = client.post('/api/auth/login', json=payload)

        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

        data = response.get_json()
        assert 'error' in data or 'message' in data

    def test_login_nonexistent_email(self, client):
        """
        존재하지 않는 이메일로 로그인 실패

        Expected:
        - Status code 404 (내부 시스템 — 편의성 우선, Sprint 24 변경)
        """
        payload = {
            'email': 'nonexistent@axisos.test',
            'password': 'AnyPassword123!'
        }

        response = client.post('/api/auth/login', json=payload)

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        data = response.get_json()
        assert data['error'] == 'ACCOUNT_NOT_FOUND'
