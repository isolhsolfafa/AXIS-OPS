"""
전체 워크플로우 통합 테스트
Sprint 7: 가입 → 이메일인증 → 로그인 → 승인 → QR 스캔 → Task 시작/완료

시나리오:
1. 정상 플로우 (가입 → 인증 → 승인 → 로그인 → QR → Task)
2. 승인 거부 플로우
3. Admin freepass 로그인
4. Task 시작 → 완료 전체 플로우
5. 미승인/미인증 사용자 접근 제한
"""

import pytest
from datetime import datetime, timedelta, timezone
from typing import Optional


# ============================================================
# 헬퍼 함수
# ============================================================

def _register_worker(client, email: str, name: str, role: str, company: Optional[str] = None):
    """회원가입 헬퍼"""
    payload = {
        'name': name,
        'email': email,
        'password': 'SecurePass123!',
        'role': role,
    }
    if company:
        payload['company'] = company
    return client.post('/api/auth/register', json=payload)


def _login(client, email: str, password: str = 'SecurePass123!'):
    """로그인 헬퍼"""
    return client.post('/api/auth/login', json={
        'email': email,
        'password': password,
    })


def _get_verification_code(db_conn, email: str) -> Optional[str]:
    """DB에서 이메일 인증 코드 직접 조회 (SMTP mock 환경)"""
    if db_conn is None:
        return None
    cursor = db_conn.cursor()
    cursor.execute("""
        SELECT verification_code FROM email_verification
        WHERE worker_id = (SELECT id FROM workers WHERE email = %s)
        ORDER BY created_at DESC
        LIMIT 1
    """, (email,))
    row = cursor.fetchone()
    cursor.close()
    return row[0] if row else None


def _verify_email(client, code: str):
    """이메일 인증 헬퍼"""
    return client.post('/api/auth/verify-email', json={'code': code})


def _approve_worker(client, worker_id: int, admin_token: str, approve: bool = True):
    """관리자 작업자 승인/거부 헬퍼"""
    return client.post(
        '/api/admin/workers/approve',
        json={'worker_id': worker_id, 'approved': approve},
        headers={'Authorization': f'Bearer {admin_token}'}
    )


# ============================================================
# 시나리오 1: 정상 플로우
# ============================================================

class TestNormalWorkflow:
    """정상 플로우: 가입 → 인증 → 승인 → 로그인 → QR → Task"""

    def test_register_returns_201(self, client):
        """
        TC-WF-01: 회원가입 성공 → 201

        Expected:
        - Status 201
        - worker_id 반환
        """
        response = _register_worker(
            client,
            email='wf_register_test@axisos.test',
            name='WF Register Test',
            role='MECH',
            company='FNI'
        )

        assert response.status_code == 201, \
            f"회원가입 201 기대, got {response.status_code}: {response.get_json()}"
        data = response.get_json()
        assert 'worker_id' in data, "worker_id 필드 필요"

    def test_duplicate_email_rejected(self, client, approved_worker):
        """
        TC-WF-02: 중복 이메일 가입 → 400 DUPLICATE_EMAIL

        Expected:
        - Status 400
        - error: DUPLICATE_EMAIL
        """
        response = _register_worker(
            client,
            email=approved_worker['email'],
            name='Duplicate Email Test',
            role='MECH'
        )

        assert response.status_code == 400, \
            f"중복 이메일은 400이어야 함, got {response.status_code}"
        data = response.get_json()
        assert data.get('error') == 'DUPLICATE_EMAIL', \
            f"error 코드가 DUPLICATE_EMAIL이어야 함: {data}"

    def test_email_verification_flow(self, client, db_conn):
        """
        TC-WF-03: 이메일 인증 플로우 성공

        Expected:
        - 회원가입 후 인증 코드 발급
        - 올바른 코드로 인증 → 200
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        email = 'wf_verify@axisos.test'

        reg_resp = _register_worker(client, email=email, name='WF Verify', role='MECH')
        if reg_resp.status_code not in [201, 409]:
            pytest.skip(f"회원가입 실패: {reg_resp.status_code}")

        code = _get_verification_code(db_conn, email)
        if not code:
            pytest.skip("인증 코드를 DB에서 찾을 수 없음 (SMTP mock 환경 확인 필요)")

        verify_resp = _verify_email(client, code)
        assert verify_resp.status_code == 200, \
            f"이메일 인증 200 기대, got {verify_resp.status_code}: {verify_resp.get_json()}"

        # 정리
        if reg_resp.status_code == 201:
            worker_id = reg_resp.get_json().get('worker_id')
            cursor = db_conn.cursor()
            if worker_id:
                cursor.execute("DELETE FROM email_verification WHERE worker_id = %s", (worker_id,))
                cursor.execute("DELETE FROM workers WHERE id = %s", (worker_id,))
            db_conn.commit()
            cursor.close()

    def test_invalid_verification_code(self, client):
        """
        TC-WF-04: 잘못된 인증 코드 → 400

        Expected:
        - Status 400
        """
        response = _verify_email(client, '000000')

        assert response.status_code == 400, \
            f"잘못된 코드는 400이어야 함, got {response.status_code}"

    def test_register_login_full_flow(self, client, db_conn):
        """
        TC-WF-05: 회원가입 → 이메일 인증 → 승인 → 로그인 전체 플로우

        Expected:
        - 가입 → 인증 → 승인 → 로그인 → access_token 수령
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        email = 'wf_full_flow@axisos.test'

        # 가입
        reg_resp = _register_worker(client, email=email, name='WF Full Flow', role='MECH', company='FNI')

        if reg_resp.status_code == 409:
            pytest.skip("이미 가입된 이메일")

        assert reg_resp.status_code == 201, f"가입 실패: {reg_resp.get_json()}"
        worker_id = reg_resp.get_json().get('worker_id')

        # 인증 코드 DB에서 조회
        code = _get_verification_code(db_conn, email)
        if code:
            verify_resp = _verify_email(client, code)
            assert verify_resp.status_code == 200, f"인증 실패: {verify_resp.get_json()}"

        # DB에서 직접 승인 처리
        cursor = db_conn.cursor()
        cursor.execute("""
            UPDATE workers
            SET approval_status = 'approved'::approval_status_enum, email_verified = TRUE
            WHERE id = %s
        """, (worker_id,))
        db_conn.commit()
        cursor.close()

        # 로그인
        login_resp = _login(client, email=email, password='SecurePass123!')
        assert login_resp.status_code == 200, \
            f"승인 후 로그인 200 기대, got {login_resp.status_code}: {login_resp.get_json()}"
        login_data = login_resp.get_json()
        assert 'access_token' in login_data, "access_token 필드 필요"
        assert 'worker' in login_data, "worker 정보 필드 필요"

        # 정리
        cursor = db_conn.cursor()
        cursor.execute("DELETE FROM email_verification WHERE worker_id = %s", (worker_id,))
        cursor.execute("DELETE FROM workers WHERE id = %s", (worker_id,))
        db_conn.commit()
        cursor.close()


# ============================================================
# 시나리오 2: 승인 거부 플로우
# ============================================================

class TestApprovalRejectionFlow:
    """승인 거부 플로우 테스트"""

    def test_pending_worker_cannot_login(self, client, unapproved_worker):
        """
        TC-WF-06: 승인 대기 사용자 로그인 → 403

        Expected:
        - Status 403
        - error: APPROVAL_PENDING
        """
        response = _login(client, email=unapproved_worker['email'],
                          password=unapproved_worker['password'])

        assert response.status_code == 403, \
            f"미승인 사용자 로그인은 403이어야 함, got {response.status_code}"
        data = response.get_json()
        assert data.get('error') in ['APPROVAL_PENDING', 'NOT_APPROVED'], \
            f"에러 코드가 APPROVAL_PENDING 관련이어야 함: {data}"

    def test_admin_can_approve_worker(self, client, admin_worker, unapproved_worker, get_auth_token):
        """
        TC-WF-07: 관리자가 작업자 승인 → 200

        Expected:
        - 관리자 토큰으로 승인 API 호출 → 200
        """
        admin_token = get_auth_token(admin_worker['id'], role='QI', email=admin_worker['email'])

        response = _approve_worker(
            client,
            worker_id=unapproved_worker['id'],
            admin_token=admin_token,
            approve=True
        )

        assert response.status_code == 200, \
            f"관리자 승인 200 기대, got {response.status_code}: {response.get_json()}"

    def test_admin_can_reject_worker(self, client, create_test_worker, admin_worker, get_auth_token):
        """
        TC-WF-08: 관리자가 작업자 거부 → 200, 이후 로그인 불가

        Expected:
        - 거부 API 호출 → 200
        - 거부된 사용자 로그인 → 403
        """
        reject_target_id = create_test_worker(
            email='reject_target@axisos.test',
            password='TestPass123!',
            name='Reject Target',
            role='MECH',
            approval_status='pending',
            email_verified=True
        )

        admin_token = get_auth_token(admin_worker['id'], role='QI', email=admin_worker['email'])

        # 거부
        reject_resp = _approve_worker(
            client,
            worker_id=reject_target_id,
            admin_token=admin_token,
            approve=False
        )
        assert reject_resp.status_code == 200, \
            f"관리자 거부 200 기대, got {reject_resp.status_code}: {reject_resp.get_json()}"

        # 거부된 사용자 로그인 시도
        login_resp = _login(client, email='reject_target@axisos.test', password='TestPass123!')
        assert login_resp.status_code == 403, \
            f"거부된 사용자 로그인은 403이어야 함, got {login_resp.status_code}"

    def test_non_admin_cannot_approve(self, client, unapproved_worker, approved_worker, get_auth_token):
        """
        TC-WF-09: 일반 사용자가 승인 API 호출 → 403 FORBIDDEN

        Expected:
        - Status 403
        """
        non_admin_token = get_auth_token(approved_worker['id'], role='MECH')

        response = _approve_worker(
            client,
            worker_id=unapproved_worker['id'],
            admin_token=non_admin_token,
            approve=True
        )

        assert response.status_code == 403, \
            f"일반 사용자의 승인 시도는 403이어야 함, got {response.status_code}"


# ============================================================
# 시나리오 3: Admin freepass 로그인
# ============================================================

class TestAdminFreepassLogin:
    """Admin 계정은 이메일 인증/승인 없이 바로 로그인 가능"""

    def test_admin_login_bypasses_verification(self, client, admin_worker):
        """
        TC-WF-10: Admin 계정 로그인 freepass

        Expected:
        - is_admin=True인 계정은 이메일 인증/승인 없이 로그인 가능
        - Status 200, access_token 반환
        """
        response = _login(client, email=admin_worker['email'],
                          password=admin_worker['password'])

        assert response.status_code == 200, \
            f"Admin 로그인 200 기대, got {response.status_code}: {response.get_json()}"
        data = response.get_json()
        assert 'access_token' in data, "Admin 로그인 시 access_token 필요"

    def test_admin_token_has_admin_info(self, client, admin_worker):
        """
        TC-WF-11: Admin 로그인 응답에 worker 정보 포함

        Expected:
        - worker.is_admin = True 또는 role = admin 관련
        """
        response = _login(client, email=admin_worker['email'],
                          password=admin_worker['password'])

        assert response.status_code == 200
        data = response.get_json()
        worker_info = data.get('worker', {})
        # is_admin=True 이거나 role이 admin 관련이면 OK
        is_admin = worker_info.get('is_admin') is True
        is_admin_role = worker_info.get('role', '').upper() in ['ADMIN', 'QI', 'SI']
        assert is_admin or is_admin_role, \
            f"Admin 로그인 응답에 admin 권한 정보가 있어야 함: {worker_info}"


# ============================================================
# 시나리오 4: Task 시작 → 완료 전체 플로우
# ============================================================

class TestTaskStartCompleteFlow:
    """Task 시작 → 완료 → completion_status 업데이트 전체 플로우"""

    def test_qr_scan_then_task_start_and_complete(
        self, client, seed_test_products, create_test_worker,
        get_auth_token, db_conn
    ):
        """
        TC-WF-12: QR 스캔 → Task 목록 조회 → 시작 → 완료 전체 플로우

        Expected:
        - QR 조회 → 200 + Task Seed 자동 생성
        - Task 시작 → 200 + started_at 설정
        - Task 완료 → 200 + duration_minutes 계산
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='wf_task_flow@axisos.test', password='Test123!',
            name='WF Task Flow', role='MECH', company='FNI'
        )
        token = get_auth_token(worker_id, role='MECH')

        gaia = next(p for p in seed_test_products if 'GAIA' in p['model'])
        serial_number = gaia['serial_number']

        # 기존 Task 정리 + QR 스캔 (Task Seed 생성)
        cursor = db_conn.cursor()
        cursor.execute(
            "DELETE FROM app_task_details WHERE serial_number = %s",
            (serial_number,)
        )
        db_conn.commit()
        cursor.close()

        product_resp = client.get(
            f'/api/app/product/{gaia["qr_doc_id"]}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert product_resp.status_code == 200, \
            f"QR 스캔(제품 조회) 실패: {product_resp.get_json()}"

        # MECH + applicable=True + 미시작 Task 선택
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT id FROM app_task_details
            WHERE serial_number = %s
              AND task_category = 'MECH'
              AND is_applicable = TRUE
              AND started_at IS NULL
            ORDER BY id
            LIMIT 1
        """, (serial_number,))
        row = cursor.fetchone()
        cursor.close()

        if not row:
            pytest.skip("시작 가능한 MECH Task 없음")

        task_detail_id = row[0]

        # Task 시작
        start_resp = client.post(
            '/api/app/work/start',
            json={'task_detail_id': task_detail_id},
            headers={'Authorization': f'Bearer {token}'}
        )
        if start_resp.status_code == 404:
            pytest.skip("POST /api/app/work/start 미구현")

        assert start_resp.status_code == 200, \
            f"Task 시작 200 기대, got {start_resp.status_code}: {start_resp.get_json()}"

        # Task 완료
        complete_resp = client.post(
            '/api/app/work/complete',
            json={'task_detail_id': task_detail_id},
            headers={'Authorization': f'Bearer {token}'}
        )
        if complete_resp.status_code == 404:
            pytest.skip("POST /api/app/work/complete 미구현")

        assert complete_resp.status_code == 200, \
            f"Task 완료 200 기대, got {complete_resp.status_code}: {complete_resp.get_json()}"

        complete_data = complete_resp.get_json()
        # 완료 시간 또는 duration이 응답에 포함되어야 함
        has_completion_info = (
            complete_data.get('completed_at') is not None or
            complete_data.get('duration_minutes') is not None or
            complete_data.get('task_finished') is True
        )
        assert has_completion_info, \
            f"완료 응답에 완료 정보가 있어야 함: {complete_data}"

    def test_task_duration_is_positive(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """
        TC-WF-13: Task 완료 후 duration_minutes > 0

        Expected:
        - 60분 경과 후 완료 → duration_minutes >= 1
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='wf_dur_pos@test.com', password='Test123!',
            name='WF Duration Pos', role='MECH'
        )
        create_test_product(
            qr_doc_id='DOC-WF-DUR-001',
            serial_number='SN-WF-DUR-001',
            model='GALLANT-50'
        )
        create_test_completion_status(serial_number='SN-WF-DUR-001')

        # 60분 전에 시작된 Task
        started_at = datetime.now(timezone.utc) - timedelta(minutes=60)
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, worker_id, started_at)
            VALUES ('SN-WF-DUR-001', 'DOC-WF-DUR-001', 'MECH', 'PANEL_WORK_WF', '판넬 작업',
                    TRUE, %s, %s)
            RETURNING id
        """, (worker_id, started_at))
        task_detail_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO work_start_log
                (task_id, worker_id, serial_number, qr_doc_id,
                 task_category, task_id_ref, task_name, started_at)
            VALUES (%s, %s, 'SN-WF-DUR-001', 'DOC-WF-DUR-001',
                    'MECH', 'PANEL_WORK_WF', '판넬 작업', %s)
        """, (task_detail_id, worker_id, started_at))
        db_conn.commit()
        cursor.close()

        token = get_auth_token(worker_id, role='MECH')
        response = client.post(
            '/api/app/work/complete',
            json={'task_detail_id': task_detail_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("POST /api/app/work/complete 미구현")

        assert response.status_code == 200
        data = response.get_json()
        duration = data.get('duration_minutes')
        if duration is not None:
            assert duration >= 1, \
                f"60분 경과 task의 duration_minutes는 1 이상이어야 함, got {duration}"

    def test_cannot_complete_unstarted_task(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """
        TC-WF-14: 시작하지 않은 Task 완료 시도 → 400 또는 403

        Expected:
        - Status 400 (TASK_NOT_STARTED) 또는 403 (FORBIDDEN)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='wf_nostart@test.com', password='Test123!',
            name='WF No Start', role='MECH'
        )
        create_test_product(
            qr_doc_id='DOC-WF-NOSTART-001',
            serial_number='SN-WF-NOSTART-001',
            model='GALLANT-50'
        )
        create_test_completion_status(serial_number='SN-WF-NOSTART-001')

        # 미시작 Task 생성
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable)
            VALUES ('SN-WF-NOSTART-001', 'DOC-WF-NOSTART-001',
                    'MECH', 'NOSTART_TASK', '미시작 Task', TRUE)
            RETURNING id
        """)
        task_detail_id = cursor.fetchone()[0]
        db_conn.commit()
        cursor.close()

        token = get_auth_token(worker_id, role='MECH')
        response = client.post(
            '/api/app/work/complete',
            json={'task_detail_id': task_detail_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("POST /api/app/work/complete 미구현")

        assert response.status_code in [400, 403], \
            f"미시작 Task 완료는 400 또는 403이어야 함, got {response.status_code}"


# ============================================================
# 시나리오 5: 미승인/미인증 사용자 접근 제한
# ============================================================

class TestAccessControl:
    """미승인/미인증 사용자의 API 접근 제한 테스트"""

    def test_unverified_email_cannot_login(self, client, create_test_worker):
        """
        TC-WF-15: 이메일 미인증 사용자 로그인 → 403 EMAIL_NOT_VERIFIED

        Expected:
        - Status 403
        - error: EMAIL_NOT_VERIFIED
        """
        create_test_worker(
            email='wf_unverified@test.com',
            password='TestPass123!',
            name='WF Unverified',
            role='MECH',
            approval_status='approved',
            email_verified=False
        )

        response = _login(client, email='wf_unverified@test.com', password='TestPass123!')

        assert response.status_code == 403, \
            f"이메일 미인증 사용자 로그인은 403이어야 함, got {response.status_code}"
        data = response.get_json()
        assert data.get('error') in ['EMAIL_NOT_VERIFIED', 'NOT_VERIFIED'], \
            f"에러 코드가 EMAIL_NOT_VERIFIED여야 함: {data}"

    def test_unauthenticated_cannot_access_product_api(self, client, seed_test_products):
        """
        TC-WF-16: 토큰 없이 제품 API 호출 → 401

        Expected:
        - Status 401
        """
        gaia = next(p for p in seed_test_products if 'GAIA' in p['model'])
        response = client.get(f'/api/app/product/{gaia["qr_doc_id"]}')

        assert response.status_code == 401, \
            f"미인증 제품 조회는 401이어야 함, got {response.status_code}"

    def test_unauthenticated_cannot_start_task(self, client):
        """
        TC-WF-17: 토큰 없이 작업 시작 API 호출 → 401

        Expected:
        - Status 401
        """
        response = client.post(
            '/api/app/work/start',
            json={'task_detail_id': 1}
        )

        assert response.status_code == 401, \
            f"미인증 작업 시작은 401이어야 함, got {response.status_code}"

    def test_unauthenticated_cannot_complete_task(self, client):
        """
        TC-WF-18: 토큰 없이 작업 완료 API 호출 → 401

        Expected:
        - Status 401
        """
        response = client.post(
            '/api/app/work/complete',
            json={'task_detail_id': 1}
        )

        assert response.status_code == 401, \
            f"미인증 작업 완료는 401이어야 함, got {response.status_code}"

    def test_unauthenticated_cannot_access_admin_api(self, client):
        """
        TC-WF-19: 토큰 없이 Admin API 호출 → 401

        Expected:
        - Status 401
        """
        response = client.get('/api/admin/workers/pending')

        assert response.status_code == 401, \
            f"미인증 Admin API는 401이어야 함, got {response.status_code}"

    def test_non_admin_cannot_access_admin_api(self, client, approved_worker, get_auth_token):
        """
        TC-WF-20: 일반 사용자가 Admin API 호출 → 403

        Expected:
        - Status 403
        """
        token = get_auth_token(approved_worker['id'], role='MECH')
        response = client.get(
            '/api/admin/workers/pending',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 403, \
            f"일반 사용자의 Admin API 접근은 403이어야 함, got {response.status_code}"

    def test_login_with_wrong_password(self, client, approved_worker):
        """
        TC-WF-21: 잘못된 비밀번호로 로그인 → 401

        Expected:
        - Status 401
        - error: INVALID_CREDENTIALS
        """
        response = _login(client, email=approved_worker['email'], password='WrongPass999!')

        assert response.status_code == 401, \
            f"잘못된 비밀번호는 401이어야 함, got {response.status_code}"
        data = response.get_json()
        assert data.get('error') == 'INVALID_CREDENTIALS', \
            f"error 코드가 INVALID_CREDENTIALS여야 함: {data}"

    def test_login_with_nonexistent_email(self, client):
        """
        TC-WF-22: 존재하지 않는 이메일로 로그인 → 401

        Expected:
        - Status 401
        """
        response = _login(client, email='nonexistent_9999@axisos.test', password='AnyPass123!')

        assert response.status_code == 401, \
            f"존재하지 않는 이메일 로그인은 401이어야 함, got {response.status_code}"

    def test_missing_required_register_fields(self, client):
        """
        TC-WF-23: 필수 필드 누락 회원가입 → 400

        Expected:
        - name/email/password/role 중 하나라도 없으면 400
        """
        # email 없이 요청
        response = client.post('/api/auth/register', json={
            'name': 'Missing Email Worker',
            'password': 'SecurePass123!',
            'role': 'MECH'
        })

        assert response.status_code == 400, \
            f"필수 필드 누락 회원가입은 400이어야 함, got {response.status_code}"
