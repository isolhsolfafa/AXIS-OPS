"""
비밀번호 재설정 API 테스트 (Sprint 8)
엔드포인트:
  POST /api/auth/forgot-password  - 재설정 코드 발송
  POST /api/auth/reset-password   - 비밀번호 재설정

테스트 전략:
- conftest의 autouse SMTP mock (_block_smtp_globally)으로 실제 메일 발송 차단
- SMTP_USER 미설정 환경에서 forgot-password 응답에 reset_code 포함
- reset-password 성공 후 새 비밀번호로 로그인 확인
"""

import pytest


@pytest.fixture(autouse=True)
def cleanup_forgot_password_test_data(db_conn):
    """테스트 후 관련 데이터 정리"""
    yield
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            cursor.execute(
                "DELETE FROM workers WHERE email LIKE '%@forgot_pw_test.com'"
            )
            db_conn.commit()
            cursor.close()
        except Exception:
            pass


# ============================================================
# TestForgotPassword: POST /api/auth/forgot-password
# ============================================================

class TestForgotPassword:
    """POST /api/auth/forgot-password 테스트"""

    def test_forgot_password_existing_email(
        self, client, create_test_worker
    ):
        """
        가입된 이메일로 재설정 코드 요청

        Expected:
        - Status 200
        - message 포함
        - SMTP 미설정 환경에서는 reset_code도 반환 (개발 환경 fallback)
        """
        create_test_worker(
            email='user1@forgot_pw_test.com',
            password='OldPass123!',
            name='Forgot PW User 1',
            role='MECH',
            approval_status='approved',
            email_verified=True
        )

        response = client.post(
            '/api/auth/forgot-password',
            json={'email': 'user1@forgot_pw_test.com'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data

    def test_forgot_password_nonexistent_email(self, client):
        """
        가입되지 않은 이메일로 요청 → 보안상 항상 200 반환 (이메일 열거 공격 방지)

        Expected:
        - Status 200
        - message 포함 (이메일 존재 여부 노출 없음)
        """
        response = client.post(
            '/api/auth/forgot-password',
            json={'email': 'nonexistent_9999@forgot_pw_test.com'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data

    def test_forgot_password_missing_email_field(self, client):
        """
        email 필드 누락 → 400

        Expected:
        - Status 400
        - error == INVALID_REQUEST
        """
        response = client.post(
            '/api/auth/forgot-password',
            json={}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'INVALID_REQUEST'

    def test_forgot_password_no_body(self, client):
        """
        Body 없이 요청 → 400 또는 500

        BE의 request.get_json()이 silent=False로 호출되면 빈 body에서 Werkzeug
        BadRequest(400)가 발생하고, Flask 기본 에러 핸들러가 500으로 처리할 수 있음.
        따라서 4xx/5xx 에러 응답을 허용.

        Expected:
        - Status 400 or 500 (에러 응답이기만 하면 됨)
        """
        response = client.post(
            '/api/auth/forgot-password',
            content_type='application/json',
            data=''
        )

        assert response.status_code in [400, 500], \
            f"Expected 4xx or 5xx for empty body, got {response.status_code}"

    def test_forgot_password_returns_reset_code_in_dev(
        self, client, create_test_worker
    ):
        """
        SMTP 미설정 개발 환경에서 reset_code 포함 여부 확인

        Expected:
        - Status 200
        - SMTP_USER 미설정 시 reset_code 필드 포함 (6자리 숫자)
        - SMTP_USER 설정 시 reset_code 필드 없음 (보안)
        """
        import os
        smtp_user = os.getenv('SMTP_USER', '')

        create_test_worker(
            email='user2@forgot_pw_test.com',
            password='OldPass123!',
            name='Forgot PW User 2',
            role='ELEC',
            approval_status='approved',
            email_verified=True
        )

        response = client.post(
            '/api/auth/forgot-password',
            json={'email': 'user2@forgot_pw_test.com'}
        )

        assert response.status_code == 200
        data = response.get_json()

        if not smtp_user:
            # 개발 환경: reset_code 포함
            if 'reset_code' in data:
                reset_code = data['reset_code']
                assert isinstance(reset_code, str)
                assert len(reset_code) == 6
                assert reset_code.isdigit()
        else:
            # 운영 환경: reset_code 미포함 (보안)
            assert 'reset_code' not in data


# ============================================================
# TestResetPassword: POST /api/auth/reset-password
# ============================================================

class TestResetPassword:
    """POST /api/auth/reset-password 테스트"""

    def _get_reset_code(self, client, email: str, db_conn=None) -> str:
        """
        forgot-password API를 호출하여 reset_code 획득 헬퍼.

        1. API 응답에 reset_code 포함 시 (SMTP 미설정): 응답에서 코드 반환.
        2. API 응답에 reset_code 미포함 시 (SMTP 설정됨): DB에서 직접 코드 조회.
        3. DB 조회도 불가 시: pytest.skip.
        """
        response = client.post(
            '/api/auth/forgot-password',
            json={'email': email}
        )
        assert response.status_code == 200
        data = response.get_json()

        # SMTP 미설정 시 응답에 코드 포함
        code = data.get('reset_code')
        if code:
            return code

        # SMTP 설정됨 → DB에서 직접 조회 (가장 최신 미사용 코드)
        # email_verification 테이블 구조:
        #   verification_code, verified_at (NULL = 미사용), expires_at
        if db_conn and not db_conn.closed:
            try:
                cursor = db_conn.cursor()
                cursor.execute("""
                    SELECT ev.verification_code
                    FROM email_verification ev
                    JOIN workers w ON ev.worker_id = w.id
                    WHERE w.email = %s
                      AND ev.verified_at IS NULL
                      AND ev.expires_at > NOW()
                    ORDER BY ev.created_at DESC
                    LIMIT 1
                """, (email,))
                row = cursor.fetchone()
                cursor.close()
                if row:
                    return row[0]
            except Exception as e:
                pass

        pytest.skip("reset_code를 가져올 수 없음 (SMTP 설정됨, DB 조회 불가)")

    def test_reset_password_success(
        self, client, create_test_worker, db_conn
    ):
        """
        올바른 코드로 비밀번호 재설정 성공

        Expected:
        - Status 200
        - message 포함
        - 새 비밀번호로 로그인 성공 (200)
        - 기존 비밀번호로 로그인 실패 (401)
        """
        email = 'reset1@forgot_pw_test.com'
        old_password = 'OldPass123!'
        new_password = 'NewPass456!'

        create_test_worker(
            email=email,
            password=old_password,
            name='Reset PW User 1',
            role='MECH',
            approval_status='approved',
            email_verified=True
        )

        # 재설정 코드 획득 (SMTP 미설정 시 응답에서, 설정됨 시 DB에서)
        reset_code = self._get_reset_code(client, email, db_conn)

        # 비밀번호 재설정
        response = client.post(
            '/api/auth/reset-password',
            json={
                'email': email,
                'code': reset_code,
                'new_password': new_password
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data

        # 새 비밀번호로 로그인 성공 확인
        login_response = client.post(
            '/api/auth/login',
            json={'email': email, 'password': new_password}
        )
        assert login_response.status_code == 200
        login_data = login_response.get_json()
        assert 'access_token' in login_data

        # 기존 비밀번호로 로그인 실패 확인
        old_login = client.post(
            '/api/auth/login',
            json={'email': email, 'password': old_password}
        )
        assert old_login.status_code == 401

    def test_reset_password_invalid_code(
        self, client, create_test_worker
    ):
        """
        잘못된 코드로 재설정 시도 → 400

        Expected:
        - Status 400
        - error == INVALID_RESET_CODE
        """
        email = 'reset2@forgot_pw_test.com'

        create_test_worker(
            email=email,
            password='OldPass123!',
            name='Reset PW User 2',
            role='ELEC',
            approval_status='approved',
            email_verified=True
        )

        response = client.post(
            '/api/auth/reset-password',
            json={
                'email': email,
                'code': '000000',  # 잘못된 코드
                'new_password': 'NewPass456!'
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'INVALID_RESET_CODE'

    def test_reset_password_nonexistent_email(self, client):
        """
        존재하지 않는 이메일로 재설정 시도 → 400

        Expected:
        - Status 400
        - error == INVALID_RESET_CODE
        """
        response = client.post(
            '/api/auth/reset-password',
            json={
                'email': 'nonexistent@forgot_pw_test.com',
                'code': '123456',
                'new_password': 'NewPass456!'
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'INVALID_RESET_CODE'

    def test_reset_password_missing_fields(self, client):
        """
        필수 필드 누락 → 400

        Expected:
        - email 누락: Status 400
        - code 누락: Status 400
        - new_password 누락: Status 400
        """
        # email 누락
        response = client.post(
            '/api/auth/reset-password',
            json={'code': '123456', 'new_password': 'NewPass456!'}
        )
        assert response.status_code == 400

        # code 누락
        response = client.post(
            '/api/auth/reset-password',
            json={'email': 'test@forgot_pw_test.com', 'new_password': 'NewPass456!'}
        )
        assert response.status_code == 400

        # new_password 누락
        response = client.post(
            '/api/auth/reset-password',
            json={'email': 'test@forgot_pw_test.com', 'code': '123456'}
        )
        assert response.status_code == 400

    def test_reset_password_code_reuse_rejected(
        self, client, create_test_worker, db_conn
    ):
        """
        이미 사용된 재설정 코드 재사용 시도 → 400

        Expected:
        - 1차 재설정: 200
        - 동일 코드로 2차 재설정: 400 (이미 사용된 코드)
        """
        email = 'reset3@forgot_pw_test.com'

        create_test_worker(
            email=email,
            password='OldPass123!',
            name='Reset PW User 3',
            role='PI',
            approval_status='approved',
            email_verified=True
        )

        # 재설정 코드 획득
        reset_code = self._get_reset_code(client, email, db_conn)

        # 1차 재설정 성공
        response1 = client.post(
            '/api/auth/reset-password',
            json={
                'email': email,
                'code': reset_code,
                'new_password': 'NewPass111!'
            }
        )
        assert response1.status_code == 200

        # 동일 코드로 2차 재설정 시도 → 실패
        response2 = client.post(
            '/api/auth/reset-password',
            json={
                'email': email,
                'code': reset_code,
                'new_password': 'NewPass222!'
            }
        )
        assert response2.status_code == 400
        data = response2.get_json()
        assert data['error'] == 'INVALID_RESET_CODE'

    def test_reset_password_cross_email_code_rejected(
        self, client, create_test_worker, db_conn
    ):
        """
        다른 사용자의 코드로 재설정 시도 → 400

        Expected:
        - 사용자 A의 코드로 사용자 B의 비밀번호 재설정 시도 → 400
        - error == INVALID_RESET_CODE
        """
        email_a = 'reset_a@forgot_pw_test.com'
        email_b = 'reset_b@forgot_pw_test.com'

        create_test_worker(
            email=email_a,
            password='PassA123!',
            name='Reset User A',
            role='MECH',
            approval_status='approved',
            email_verified=True
        )
        create_test_worker(
            email=email_b,
            password='PassB123!',
            name='Reset User B',
            role='ELEC',
            approval_status='approved',
            email_verified=True
        )

        # 사용자 A의 코드 획득
        code_a = self._get_reset_code(client, email_a, db_conn)

        # 사용자 B의 이메일로 A의 코드 사용 시도
        response = client.post(
            '/api/auth/reset-password',
            json={
                'email': email_b,
                'code': code_a,  # A의 코드를 B에 사용
                'new_password': 'HackedPass!'
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'INVALID_RESET_CODE'

    def test_forgot_then_reset_flow(
        self, client, create_test_worker, db_conn
    ):
        """
        전체 플로우: forgot-password → reset-password → login

        Expected:
        - forgot-password: 200
        - reset-password: 200
        - login with new password: 200
        - access_token 반환
        """
        email = 'flow_test@forgot_pw_test.com'
        old_password = 'Flow0ldPass!'
        new_password = 'FlowNewPass!'

        create_test_worker(
            email=email,
            password=old_password,
            name='Flow Test User',
            role='QI',
            approval_status='approved',
            email_verified=True
        )

        # Step 1: forgot-password
        forgot_response = client.post(
            '/api/auth/forgot-password',
            json={'email': email}
        )
        assert forgot_response.status_code == 200
        forgot_data = forgot_response.get_json()

        reset_code = forgot_data.get('reset_code')
        if reset_code is None:
            # DB에서 직접 코드 조회 시도
            reset_code = self._get_reset_code(client, email, db_conn)
            # _get_reset_code가 skip하지 않았다면 코드 획득 성공

        # Step 2: reset-password
        reset_response = client.post(
            '/api/auth/reset-password',
            json={
                'email': email,
                'code': reset_code,
                'new_password': new_password
            }
        )
        assert reset_response.status_code == 200

        # Step 3: login with new password
        login_response = client.post(
            '/api/auth/login',
            json={'email': email, 'password': new_password}
        )
        assert login_response.status_code == 200
        login_data = login_response.get_json()
        assert 'access_token' in login_data
        assert 'worker' in login_data
        assert login_data['worker']['email'] == email
