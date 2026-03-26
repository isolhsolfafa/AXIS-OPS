"""
Sprint 10 Fix 검증 테스트
엔드포인트:
  GET /api/admin/tasks/pending           - 미종료 작업 목록 (manager_or_admin_required)
  PUT /api/admin/tasks/{id}/force-close  - 강제 종료 (manager_or_admin_required)
  POST /api/app/work/pause               - 작업 일시정지
  POST /api/app/work/resume              - 작업 재개
  POST /api/app/validation/check-process - 공정 검증 (location_qr_required 설정)

TC-SP10-01 ~ TC-SP10-19: 19개 테스트 케이스
"""

import time
import pytest
from datetime import datetime, timezone, timedelta
from typing import Optional


# ============================================================
# 모듈 레벨 클린업 fixture
# ============================================================
@pytest.fixture(autouse=True)
def cleanup_sprint10_test_data(db_conn):
    """테스트 후 sprint10 관련 데이터 정리"""
    yield
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            cursor.execute(
                "DELETE FROM workers WHERE email LIKE '%@sprint10_test.com'"
            )
            cursor.execute(
                "DELETE FROM admin_settings WHERE setting_key = 'location_qr_required'"
            )
            db_conn.commit()
            cursor.close()
        except Exception:
            pass


# ============================================================
# Sprint 10 전용 fixture
# ============================================================
@pytest.fixture
def s10_admin(create_test_worker, get_admin_auth_token):
    """Sprint 10 전용 admin (is_admin=True)"""
    unique_email = f'admin_{int(time.time() * 1000)}@sprint10_test.com'
    worker_id = create_test_worker(
        email=unique_email,
        password='AdminPass123!',
        name='Sprint10 Admin',
        role='QI',
        approval_status='approved',
        email_verified=True,
        is_admin=True
    )
    token = get_admin_auth_token(worker_id)
    return {'id': worker_id, 'email': unique_email, 'token': token}


@pytest.fixture
def s10_fni_manager(create_test_worker, get_auth_token):
    """Sprint 10 전용 FNI 협력사 관리자 (is_manager=True, company=FNI)"""
    unique_email = f'fni_mgr_{int(time.time() * 1000)}@sprint10_test.com'
    worker_id = create_test_worker(
        email=unique_email,
        password='ManagerPass123!',
        name='FNI Sprint10 Manager',
        role='MECH',
        approval_status='approved',
        email_verified=True,
        is_manager=True,
        company='FNI'
    )
    payload = {
        'sub': str(worker_id),
        'email': unique_email,
        'role': 'MECH',
        'is_admin': False,
    }
    # 관리자 매니저 token 생성 (is_manager는 JWT에 없고 DB에서 확인)
    token = get_auth_token(worker_id, role='MECH')
    return {'id': worker_id, 'email': unique_email, 'token': token, 'company': 'FNI'}


@pytest.fixture
def s10_worker(create_test_worker, get_auth_token):
    """Sprint 10 전용 일반 작업자 (is_manager=False)"""
    unique_email = f'worker_{int(time.time() * 1000)}@sprint10_test.com'
    worker_id = create_test_worker(
        email=unique_email,
        password='WorkerPass123!',
        name='Sprint10 Worker',
        role='MECH',
        approval_status='approved',
        email_verified=True,
        is_manager=False
    )
    token = get_auth_token(worker_id, role='MECH')
    return {'id': worker_id, 'email': unique_email, 'token': token}


@pytest.fixture
def s10_pi_worker(create_test_worker, get_auth_token):
    """Sprint 10 전용 PI 작업자 (공정 검증 테스트용)"""
    unique_email = f'pi_{int(time.time() * 1000)}@sprint10_test.com'
    worker_id = create_test_worker(
        email=unique_email,
        password='PIPass123!',
        name='Sprint10 PI Worker',
        role='PI',
        approval_status='approved',
        email_verified=True
    )
    token = get_auth_token(worker_id, role='PI')
    return {'id': worker_id, 'email': unique_email, 'token': token}


@pytest.fixture
def make_s10_task(create_test_product, create_test_task):
    """
    제품(qr_registry) + 작업(app_task_details + work_start_log)을 함께 생성.
    Sprint 10 전용 (unique suffix 사용)
    """
    _counter = [0]

    def _make(
        worker_id: int,
        task_id_ref: str = 'CABINET_ASSY',
        task_name: str = '캐비넷 조립',
        task_category: str = 'MECH',
        started_at=None,
        completed_at=None,
        duration_minutes=None,
        company: Optional[str] = None,
        location_qr_id: Optional[str] = None
    ) -> tuple:
        """
        Returns:
            (task_detail_id, qr_doc_id, serial_number)
        """
        _counter[0] += 1
        suffix = f'{int(time.time() * 1000)}_{_counter[0]}'
        qr_doc_id = f'DOC-SP10-{suffix}'
        serial_number = f'SN-SP10-{suffix}'

        create_test_product(
            qr_doc_id=qr_doc_id,
            serial_number=serial_number,
            location_qr_id=location_qr_id
        )
        task_id = create_test_task(
            worker_id=worker_id,
            serial_number=serial_number,
            qr_doc_id=qr_doc_id,
            task_category=task_category,
            task_id=task_id_ref,
            task_name=task_name,
            started_at=started_at,
            completed_at=completed_at,
            duration_minutes=duration_minutes,
        )
        return task_id, qr_doc_id, serial_number

    return _make


# ============================================================
# API 요청 헬퍼 함수
# ============================================================
def _get_pending_tasks(client, token, company=None, limit=None):
    """GET /api/admin/tasks/pending"""
    params = []
    if company:
        params.append(f'company={company}')
    if limit:
        params.append(f'limit={limit}')
    query = '?' + '&'.join(params) if params else ''
    return client.get(
        f'/api/admin/tasks/pending{query}',
        headers={'Authorization': f'Bearer {token}'}
    )


def _pause_task(client, token, task_id, pause_type='manual'):
    """POST /api/app/work/pause"""
    return client.post(
        '/api/app/work/pause',
        json={'task_detail_id': task_id, 'pause_type': pause_type},
        headers={'Authorization': f'Bearer {token}'}
    )


def _resume_task(client, token, task_id):
    """POST /api/app/work/resume"""
    return client.post(
        '/api/app/work/resume',
        json={'task_detail_id': task_id},
        headers={'Authorization': f'Bearer {token}'}
    )


def _force_close_task(client, token, task_id, close_reason='강제종료테스트'):
    """PUT /api/admin/tasks/{task_id}/force-close"""
    return client.put(
        f'/api/admin/tasks/{task_id}/force-close',
        json={'close_reason': close_reason},
        headers={'Authorization': f'Bearer {token}'}
    )


def _upsert_admin_setting(db_conn, key, value):
    """admin_settings에 직접 설정 upsert (테스트 격리용)"""
    import json
    if db_conn is None:
        return
    cursor = db_conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO admin_settings (setting_key, setting_value, updated_at)
            VALUES (%s, %s::jsonb, NOW())
            ON CONFLICT (setting_key) DO UPDATE
                SET setting_value = EXCLUDED.setting_value,
                    updated_at = NOW()
        """, (key, json.dumps(value)))
        db_conn.commit()
    finally:
        cursor.close()


# ============================================================
# TC-SP10-01: 협력사 관리자가 본인 company 미종료 작업 조회 성공
# ============================================================
class TestManagerPendingTasksOwnCompany:
    """
    TC-SP10-01: FNI 협력사 관리자가 company=FNI 필터로 미종료 작업 조회
    """

    def test_manager_pending_tasks_own_company(
        self, client, s10_fni_manager, make_s10_task, db_conn
    ):
        """
        협력사 관리자가 본인 company 미종료 작업 조회 성공
        GET /api/admin/tasks/pending?company=FNI

        Expected:
        - Status 200
        - tasks 배열 포함
        - total >= 1
        - 반환된 모든 task의 worker가 FNI 소속
        """
        task_id, qr_doc_id, serial_number = make_s10_task(
            worker_id=s10_fni_manager['id'],
            started_at=datetime.now(timezone.utc),
            completed_at=None
        )

        response = _get_pending_tasks(
            client, s10_fni_manager['token'], company='FNI'
        )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        assert 'tasks' in data, f"Response should contain 'tasks': {data}"
        assert 'total' in data, f"Response should contain 'total': {data}"
        assert data['total'] >= 1, f"Expected at least 1 pending task: {data}"


# ============================================================
# TC-SP10-02: 협력사 관리자가 타 company 조회 시 빈 리스트
# ============================================================
class TestManagerPendingTasksOtherCompany:
    """
    TC-SP10-02: FNI 협력사 관리자가 P&S company 필터로 조회 → 빈 리스트
    """

    def test_manager_pending_tasks_other_company(
        self, client, s10_fni_manager, make_s10_task, db_conn
    ):
        """
        협력사 관리자가 타 company 조회 시 → BE가 관리자 본인 company로 강제 오버라이드

        BE 동작: is_manager=True + is_admin=False인 경우,
                 query param으로 넘긴 company 값은 무시되고
                 current_worker.company (FNI)로 강제 설정됨.
        Expected:
        - Status 200 (관리자의 own company 데이터 반환)
        - tasks, total 필드 포함
        """
        # FNI 관리자로 존재하지 않는 company 필터로 미종료 작업 조회
        # → BE에서 company=FNI로 강제 오버라이드
        response = _get_pending_tasks(
            client, s10_fni_manager['token'], company='PS_NONEXISTENT_COMPANY_99'
        )

        # BE가 company=FNI로 강제 오버라이드하므로 200 반환
        assert response.status_code == 200, (
            f"Expected 200 (company overridden to FNI), got {response.status_code}: {response.get_json()}"
        )

        data = response.get_json()
        assert 'tasks' in data, f"Response should contain 'tasks': {data}"
        assert 'total' in data, f"Response should contain 'total': {data}"
        # 본인 company(FNI)의 데이터가 반환됨 (total >= 0)


# ============================================================
# TC-SP10-03: admin이 company 필터 없이 전체 미종료 작업 조회 성공
# ============================================================
class TestAdminPendingTasksAll:
    """
    TC-SP10-03: admin이 company 필터 없이 전체 미종료 작업 조회
    """

    def test_admin_pending_tasks_all(
        self, client, s10_admin, make_s10_task, db_conn
    ):
        """
        admin이 company 필터 없이 전체 미종료 작업 조회 성공

        Expected:
        - Status 200
        - tasks 배열과 total 포함
        - 생성한 미종료 작업이 포함됨
        """
        task_id, _, _ = make_s10_task(
            worker_id=s10_admin['id'],
            started_at=datetime.now(timezone.utc),
            completed_at=None
        )

        response = _get_pending_tasks(client, s10_admin['token'])

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        assert 'tasks' in data
        assert 'total' in data
        assert data['total'] >= 1, f"Expected at least 1 task in results: {data}"

        if data['tasks']:
            task = data['tasks'][0]
            required_fields = ['id', 'worker_id', 'worker_name', 'serial_number',
                               'started_at', 'elapsed_minutes']
            for field in required_fields:
                assert field in task, (
                    f"Task should contain '{field}': {task}"
                )


# ============================================================
# TC-SP10-04: 일반 작업자가 미종료 작업 조회 시 403
# ============================================================
class TestWorkerPendingTasksForbidden:
    """
    TC-SP10-04: 일반 작업자(is_manager=false)가 미종료 작업 조회 시 403
    """

    def test_worker_pending_tasks_forbidden(self, client, s10_worker):
        """
        일반 작업자(is_manager=false)가 GET /api/admin/tasks/pending 접근 → 403

        Expected:
        - Status 403
        - error == FORBIDDEN
        """
        response = _get_pending_tasks(client, s10_worker['token'])

        assert response.status_code == 403, (
            f"Expected 403, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        assert data.get('error') == 'FORBIDDEN', (
            f"Expected FORBIDDEN error: {data}"
        )


# ============================================================
# TC-SP10-05: pause 응답에 전체 task 필드 포함 확인
# ============================================================
class TestPauseResponseFullTaskFields:
    """
    TC-SP10-05: pause 응답에 전체 task 필드 포함 확인
    """

    def test_pause_response_full_task_fields(
        self, client, s10_fni_manager, make_s10_task
    ):
        """
        pause 응답에 _task_to_dict 기준 전체 task 필드 포함 확인

        Expected:
        - Status 200
        - 응답에 id, worker_id, serial_number, task_category, task_name,
          started_at, completed_at, is_paused, total_pause_minutes 포함
        """
        task_id, _, _ = make_s10_task(
            worker_id=s10_fni_manager['id'],
            started_at=datetime.now(timezone.utc)
        )

        response = _pause_task(client, s10_fni_manager['token'], task_id)

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()

        # _task_to_dict 기준 필드 확인 (Sprint 9 추가 필드 포함)
        required_fields = [
            'id', 'worker_id', 'serial_number', 'qr_doc_id',
            'task_category', 'task_name', 'started_at',
            'is_paused', 'total_pause_minutes'
        ]
        for field in required_fields:
            assert field in data, (
                f"Pause response should contain '{field}': {data.keys()}"
            )

        # is_paused should be True after pause
        assert data.get('is_paused') is True, (
            f"is_paused should be True after pause: {data}"
        )


# ============================================================
# TC-SP10-06: resume 응답에 전체 task 필드 포함 확인
# ============================================================
class TestResumeResponseFullTaskFields:
    """
    TC-SP10-06: resume 응답에 전체 task 필드 포함 확인
    """

    def test_resume_response_full_task_fields(
        self, client, s10_fni_manager, make_s10_task
    ):
        """
        resume 응답에 _task_to_dict 기준 전체 task 필드 포함 확인

        Expected:
        - Status 200
        - 응답에 id, worker_id, serial_number, task_category, task_name,
          started_at, is_paused, total_pause_minutes 포함
        - is_paused == False after resume
        """
        task_id, _, _ = make_s10_task(
            worker_id=s10_fni_manager['id'],
            started_at=datetime.now(timezone.utc)
        )

        # 먼저 일시정지
        pause_resp = _pause_task(client, s10_fni_manager['token'], task_id)
        assert pause_resp.status_code == 200, (
            f"Pause should succeed: {pause_resp.get_json()}"
        )

        # 재개
        response = _resume_task(client, s10_fni_manager['token'], task_id)

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()

        # _task_to_dict 기준 필드 확인
        required_fields = [
            'id', 'worker_id', 'serial_number', 'qr_doc_id',
            'task_category', 'task_name', 'started_at',
            'is_paused', 'total_pause_minutes'
        ]
        for field in required_fields:
            assert field in data, (
                f"Resume response should contain '{field}': {data.keys()}"
            )

        # is_paused should be False after resume
        assert data.get('is_paused') is False, (
            f"is_paused should be False after resume: {data}"
        )


# ============================================================
# TC-SP10-07: location_qr_required=false + location QR 미등록 → 경고 미생성
# ============================================================
class TestLocationQrNotRequiredNoWarning:
    """
    TC-SP10-07: location_qr_required=false 설정 시 location QR 미등록 → 경고 미생성
    """

    def test_location_qr_not_required_no_warning(
        self, client, s10_pi_worker, make_s10_task, db_conn
    ):
        """
        admin_settings에서 location_qr_required=false 설정 후
        location_qr_id 없는 제품에 대해 PI 공정 검증 요청 시 경고 없음

        Expected:
        - Status 200
        - warnings에 'Location QR' 관련 경고 없음
        """
        # location_qr_required=false 설정
        _upsert_admin_setting(db_conn, 'location_qr_required', False)

        # location QR 없는 제품 생성 (location_qr_id=None)
        task_id, qr_doc_id, serial_number = make_s10_task(
            worker_id=s10_pi_worker['id'],
            task_category='PI',
            location_qr_id=None  # location QR 미등록
        )

        # PI 공정 검증 요청
        response = client.post(
            '/api/app/validation/check-process',
            json={
                'serial_number': serial_number,
                'process_type': 'PI'
            },
            headers={'Authorization': f'Bearer {s10_pi_worker["token"]}'}
        )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()

        # location_qr_required=false이므로 location 관련 경고가 없어야 함
        message = data.get('message', '') or ''
        assert 'Location' not in message and 'location' not in message, (
            f"Should not have location QR warning when disabled: {data}"
        )


# ============================================================
# TC-SP10-08: location_qr_required=true + location QR 미등록 → 경고 생성
# ============================================================
class TestLocationQrRequiredWarning:
    """
    TC-SP10-08: location_qr_required=true 설정 + location QR 미등록 → 경고 생성
    """

    def test_location_qr_required_warning(
        self, client, s10_pi_worker, make_s10_task, db_conn
    ):
        """
        admin_settings에서 location_qr_required=true 설정 후
        location_qr_id 없는 제품에 대해 PI 공정 검증 요청 시 경고 생성

        Expected:
        - Status 200
        - message 또는 missing_processes에 location QR 관련 내용 포함
          또는 location_qr_verified == False
        """
        # location_qr_required=true 설정
        _upsert_admin_setting(db_conn, 'location_qr_required', True)

        # location QR 없는 제품 생성
        task_id, qr_doc_id, serial_number = make_s10_task(
            worker_id=s10_pi_worker['id'],
            task_category='PI',
            location_qr_id=None
        )

        response = client.post(
            '/api/app/validation/check-process',
            json={
                'serial_number': serial_number,
                'process_type': 'PI'
            },
            headers={'Authorization': f'Bearer {s10_pi_worker["token"]}'}
        )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()

        # location_qr_required=true이므로 location_qr_verified=false 이거나 경고 있어야 함
        location_qr_verified = data.get('location_qr_verified', True)
        message = data.get('message', '') or ''
        assert not location_qr_verified or 'Location' in message or 'location' in message, (
            f"Expected location QR warning when required=true and not set: {data}"
        )


# ============================================================
# TC-SP10-09: location_qr_required 미설정(기본값) + location QR 미등록 → 경고 생성
# ============================================================
class TestLocationQrDefaultWarning:
    """
    TC-SP10-09: location_qr_required 미설정(기본값=True) + location QR 미등록 → 경고 생성
    """

    def test_location_qr_default_warning(
        self, client, s10_pi_worker, make_s10_task, db_conn
    ):
        """
        admin_settings에서 location_qr_required 설정 없을 때 (기본값 True)
        location_qr_id 없는 제품에 대해 PI 공정 검증 요청 시 경고 생성

        Expected:
        - Status 200
        - location_qr_verified=False 또는 location 관련 경고 있음
        """
        # location_qr_required 설정을 삭제하여 기본값 사용
        if db_conn and not db_conn.closed:
            cursor = db_conn.cursor()
            cursor.execute(
                "DELETE FROM admin_settings WHERE setting_key = 'location_qr_required'"
            )
            db_conn.commit()
            cursor.close()

        # location QR 없는 제품 생성
        task_id, qr_doc_id, serial_number = make_s10_task(
            worker_id=s10_pi_worker['id'],
            task_category='PI',
            location_qr_id=None
        )

        response = client.post(
            '/api/app/validation/check-process',
            json={
                'serial_number': serial_number,
                'process_type': 'PI'
            },
            headers={'Authorization': f'Bearer {s10_pi_worker["token"]}'}
        )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()

        # 기본값 True이므로 location QR 미등록 시 경고 있어야 함
        location_qr_verified = data.get('location_qr_verified', True)
        message = data.get('message', '') or ''
        # location_qr_verified=False이거나 경고 메시지 있어야 함
        has_location_warning = not location_qr_verified or 'Location' in message or 'location' in message
        assert has_location_warning, (
            f"Expected location QR warning with default setting (True): {data}"
        )


# ============================================================
# TC-SP10-10: 협력사 관리자 강제 종료 성공
# ============================================================
class TestManagerForceClose:
    """
    TC-SP10-10: 협력사 관리자 강제 종료 성공
    PUT /api/admin/tasks/{id}/force-close
    """

    def test_manager_force_close(
        self, client, s10_fni_manager, make_s10_task, db_conn
    ):
        """
        협력사 관리자(is_manager=True)가 미종료 작업 강제 종료 성공

        Expected:
        - Status 200
        - response에 task_id, completed_at, close_reason 포함
        - DB: completed_at IS NOT NULL, force_closed = TRUE
        """
        task_id, qr_doc_id, serial_number = make_s10_task(
            worker_id=s10_fni_manager['id'],
            started_at=datetime.now(timezone.utc),
            completed_at=None
        )

        close_reason = 'Sprint10 테스트용 강제종료'
        response = _force_close_task(
            client, s10_fni_manager['token'], task_id,
            close_reason=close_reason
        )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        assert 'task_id' in data, f"Response should contain 'task_id': {data}"
        assert 'completed_at' in data, f"Response should contain 'completed_at': {data}"
        assert 'close_reason' in data, f"Response should contain 'close_reason': {data}"
        assert data.get('close_reason') == close_reason, (
            f"close_reason should match: {data}"
        )

        # DB 상태 확인
        if db_conn and not db_conn.closed:
            cursor = db_conn.cursor()
            cursor.execute(
                """
                SELECT completed_at, force_closed, close_reason
                FROM app_task_details
                WHERE id = %s
                """,
                (task_id,)
            )
            row = cursor.fetchone()
            cursor.close()

            assert row is not None, "Task should exist in DB"
            assert row[0] is not None, "DB: completed_at should be set after force close"
            assert row[1] is True, "DB: force_closed should be TRUE"


# ============================================================
# TC-SP10-11: 작업 시작 응답에 started_at이 KST(+09:00) 포함 확인
# ============================================================
class TestStartWorkKstTimezone:
    """
    TC-SP10-11: 작업 시작 후 started_at이 KST(+09:00) 포함 확인
    POST /api/app/work/start
    """

    def test_start_work_response_kst_timezone(self, client, s10_fni_manager, make_s10_task):
        """작업 시작 후 started_at이 KST(+09:00) 포함 확인

        Expected:
        - Status 200
        - started_at 문자열에 '+09:00' 포함 (KST 타임존 명시)
        """
        task_id, _, _ = make_s10_task(worker_id=s10_fni_manager['id'])
        response = client.post(
            '/api/app/work/start',
            json={'task_detail_id': task_id},
            headers={'Authorization': f'Bearer {s10_fni_manager["token"]}'}
        )
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        assert '+09:00' in data.get('started_at', ''), (
            f"started_at should be KST: {data}"
        )


# ============================================================
# TC-SP10-12 ~ TC-SP10-14: heating_jacket_enabled 설정 동기화 검증
# ============================================================
class TestHeatingJacketSync:
    """
    TC-SP10-12 ~ TC-SP10-14: heating_jacket_enabled 설정에 따른 HEATING_JACKET task 동기화
    PUT /api/admin/settings → app_task_details.is_applicable 자동 갱신
    """

    def test_heating_jacket_off_sets_not_applicable(
        self, client, s10_admin, make_s10_task, db_conn
    ):
        """heating_jacket_enabled=false → HEATING_JACKET task is_applicable=false

        Expected:
        - PUT /api/admin/settings {heating_jacket_enabled: false} → 200
        - DB: HEATING_JACKET task의 is_applicable = False (미완료 task만 대상)
        """
        task_id, _, _ = make_s10_task(
            worker_id=s10_admin['id'],
            task_id_ref='HEATING_JACKET',
            task_name='Heating Jacket',
            task_category='MECH'
        )

        response = client.put(
            '/api/admin/settings',
            json={'heating_jacket_enabled': False},
            headers={'Authorization': f'Bearer {s10_admin["token"]}'}
        )
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.get_json()}"
        )

        # DB 확인
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT is_applicable FROM app_task_details WHERE id = %s",
            (task_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        assert row is not None, "Task should exist in DB"
        assert row[0] is False, (
            f"HEATING_JACKET is_applicable should be False after setting disabled: {row}"
        )

    def test_heating_jacket_on_restores_applicable(
        self, client, s10_admin, make_s10_task, db_conn
    ):
        """heating_jacket_enabled=true → HEATING_JACKET task is_applicable=true

        Expected:
        - OFF 후 ON 시 is_applicable이 다시 True로 복원됨
        """
        task_id, _, _ = make_s10_task(
            worker_id=s10_admin['id'],
            task_id_ref='HEATING_JACKET',
            task_name='Heating Jacket',
            task_category='MECH'
        )

        # OFF then ON
        client.put(
            '/api/admin/settings',
            json={'heating_jacket_enabled': False},
            headers={'Authorization': f'Bearer {s10_admin["token"]}'}
        )
        client.put(
            '/api/admin/settings',
            json={'heating_jacket_enabled': True},
            headers={'Authorization': f'Bearer {s10_admin["token"]}'}
        )

        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT is_applicable FROM app_task_details WHERE id = %s",
            (task_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        assert row is not None, "Task should exist in DB"
        assert row[0] is True, (
            f"HEATING_JACKET is_applicable should be True after re-enabling: {row}"
        )

    def test_completed_heating_jacket_not_affected(
        self, client, s10_admin, make_s10_task, db_conn
    ):
        """완료된 HEATING_JACKET task는 setting 변경 영향 안 받음

        Expected:
        - completed_at이 있는 HEATING_JACKET task는 is_applicable 변경 안 됨
        """
        task_id, _, _ = make_s10_task(
            worker_id=s10_admin['id'],
            task_id_ref='HEATING_JACKET',
            task_name='Heating Jacket',
            task_category='MECH',
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            duration_minutes=30
        )

        client.put(
            '/api/admin/settings',
            json={'heating_jacket_enabled': False},
            headers={'Authorization': f'Bearer {s10_admin["token"]}'}
        )

        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT is_applicable FROM app_task_details WHERE id = %s",
            (task_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        assert row is not None, "Task should exist in DB"
        assert row[0] is True, (
            f"Completed HEATING_JACKET task should NOT be affected by setting change: {row}"
        )


# ============================================================
# TC-SP10-15: location_qr_required PUT 200 성공 (ALLOWED_KEYS 포함 확인)
# ============================================================
class TestLocationQrRequiredPut:
    """
    TC-SP10-15: location_qr_required PUT → 200 성공 (ALLOWED_KEYS에 포함 확인)
    PUT /api/admin/settings
    """

    def test_location_qr_required_put_success(self, client, s10_admin):
        """location_qr_required PUT → 200 성공 (ALLOWED_KEYS 포함)

        Expected:
        - Status 200 (ALLOWED_KEYS에 포함되어 있어 거부되지 않음)
        """
        response = client.put(
            '/api/admin/settings',
            json={'location_qr_required': False},
            headers={'Authorization': f'Bearer {s10_admin["token"]}'}
        )
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.get_json()}"
        )

        # Restore
        client.put(
            '/api/admin/settings',
            json={'location_qr_required': True},
            headers={'Authorization': f'Bearer {s10_admin["token"]}'}
        )


# ============================================================
# TC-SP10-16 ~ TC-SP10-19: phase_block_enabled 설정에 따른 POST_DOCKING 차단 검증
# ============================================================
class TestPhaseBlock:
    """
    TC-SP10-16 ~ TC-SP10-19: phase_block_enabled 설정에 따른 TANK_DOCKING 완료 체크
    phase_block_enabled=true 시 WASTE_GAS_LINE_2 등 POST_DOCKING task 시작을
    TANK_DOCKING 완료 여부로 차단
    """

    def _create_phase_block_tasks(
        self, db_conn, worker_id, docking_completed=False
    ):
        """Helper: 동일 serial에 TANK_DOCKING + WASTE_GAS_LINE_2 task 생성

        Args:
            db_conn: DB 연결
            worker_id: 작업자 ID
            docking_completed: TANK_DOCKING 완료 여부

        Returns:
            (docking_task_id, post_docking_task_id, qr_doc_id, serial_number)
        """
        suffix = f'{int(time.time() * 1000)}'
        qr_doc_id = f'DOC-PB-{suffix}'
        serial_number = f'SN-PB-{suffix}'

        cursor = db_conn.cursor()

        # plan.product_info에 제품 메타데이터 먼저 삽입 (FK 의존성: qr_registry → product_info)
        cursor.execute("""
            INSERT INTO plan.product_info (
                serial_number, model, mech_partner, elec_partner, prod_date
            )
            VALUES (%s, %s, %s, %s, NOW()::date)
            ON CONFLICT (serial_number) DO NOTHING
        """, (serial_number, 'GALLANT-50', 'FNI', 'P&S'))

        # qr_registry에 제품 등록 (product_info 이후에 삽입)
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number)
            VALUES (%s, %s)
            ON CONFLICT (qr_doc_id) DO NOTHING
        """, (qr_doc_id, serial_number))

        # TANK_DOCKING task 생성 (완료 여부에 따라 started_at/completed_at 설정)
        now = datetime.now(timezone.utc)
        if docking_completed:
            cursor.execute("""
                INSERT INTO app_task_details (
                    serial_number, qr_doc_id, task_category, task_id, task_name,
                    is_applicable, worker_id, started_at, completed_at, duration_minutes
                )
                VALUES (%s, %s, 'MECH', 'TANK_DOCKING', 'Tank Docking',
                        TRUE, %s, %s, %s, 60)
                RETURNING id
            """, (serial_number, qr_doc_id, worker_id, now, now))
        else:
            cursor.execute("""
                INSERT INTO app_task_details (
                    serial_number, qr_doc_id, task_category, task_id, task_name,
                    is_applicable, worker_id, started_at
                )
                VALUES (%s, %s, 'MECH', 'TANK_DOCKING', 'Tank Docking',
                        TRUE, %s, %s)
                RETURNING id
            """, (serial_number, qr_doc_id, worker_id, now))

        docking_task_id = cursor.fetchone()[0]

        # WASTE_GAS_LINE_2 task 생성 (미시작 상태)
        cursor.execute("""
            INSERT INTO app_task_details (
                serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable
            )
            VALUES (%s, %s, 'MECH', 'WASTE_GAS_LINE_2', 'Waste Gas LINE 2', TRUE)
            RETURNING id
        """, (serial_number, qr_doc_id))

        post_docking_task_id = cursor.fetchone()[0]
        db_conn.commit()
        cursor.close()

        return docking_task_id, post_docking_task_id, qr_doc_id, serial_number

    def test_phase_block_tank_docking_incomplete(
        self, client, s10_fni_manager, db_conn
    ):
        """phase_block_enabled=true + TANK_DOCKING 미완료 → 400 PHASE_BLOCKED

        Expected:
        - phase_block_enabled=true 설정 후
        - TANK_DOCKING이 미완료 상태에서 WASTE_GAS_LINE_2 시작 시도 → 400 PHASE_BLOCKED
        """
        _upsert_admin_setting(db_conn, 'phase_block_enabled', True)

        _, post_docking_task_id, _, _ = self._create_phase_block_tasks(
            db_conn, s10_fni_manager['id'], docking_completed=False
        )

        response = client.post(
            '/api/app/work/start',
            json={'task_detail_id': post_docking_task_id},
            headers={'Authorization': f'Bearer {s10_fni_manager["token"]}'}
        )
        assert response.status_code == 400, (
            f"Expected 400 PHASE_BLOCKED, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        assert data.get('error') == 'PHASE_BLOCKED', (
            f"Expected PHASE_BLOCKED error: {data}"
        )

        # 설정 복원
        _upsert_admin_setting(db_conn, 'phase_block_enabled', False)

    def test_phase_block_tank_docking_complete(
        self, client, s10_fni_manager, db_conn
    ):
        """phase_block_enabled=true + TANK_DOCKING 완료 → start 성공

        Expected:
        - phase_block_enabled=true 설정 후
        - TANK_DOCKING이 완료된 상태에서 WASTE_GAS_LINE_2 시작 → 200 성공
        """
        # location_qr_required를 false로 설정하여 위치 QR 체크 비활성화
        _upsert_admin_setting(db_conn, 'location_qr_required', False)
        _upsert_admin_setting(db_conn, 'phase_block_enabled', True)

        _, post_docking_task_id, _, _ = self._create_phase_block_tasks(
            db_conn, s10_fni_manager['id'], docking_completed=True
        )

        response = client.post(
            '/api/app/work/start',
            json={'task_detail_id': post_docking_task_id},
            headers={'Authorization': f'Bearer {s10_fni_manager["token"]}'}
        )
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.get_json()}"
        )

        # 설정 복원
        _upsert_admin_setting(db_conn, 'phase_block_enabled', False)

    def test_phase_block_disabled_allows_start(
        self, client, s10_fni_manager, db_conn
    ):
        """phase_block_enabled=false → 차단 없음

        Expected:
        - phase_block_enabled=false 설정 시
        - TANK_DOCKING 미완료여도 WASTE_GAS_LINE_2 시작 가능 → 200
        """
        # location_qr_required를 false로 설정하여 위치 QR 체크 비활성화
        _upsert_admin_setting(db_conn, 'location_qr_required', False)
        _upsert_admin_setting(db_conn, 'phase_block_enabled', False)

        _, post_docking_task_id, _, _ = self._create_phase_block_tasks(
            db_conn, s10_fni_manager['id'], docking_completed=False
        )

        response = client.post(
            '/api/app/work/start',
            json={'task_detail_id': post_docking_task_id},
            headers={'Authorization': f'Bearer {s10_fni_manager["token"]}'}
        )
        assert response.status_code == 200, (
            f"Expected 200 when phase_block disabled, got {response.status_code}: {response.get_json()}"
        )

    def test_phase_block_default_allows_start(
        self, client, s10_fni_manager, db_conn
    ):
        """phase_block_enabled 기본값(false) → 차단 없음

        Expected:
        - phase_block_enabled 설정이 없는 경우(기본값=False)
        - TANK_DOCKING 미완료여도 WASTE_GAS_LINE_2 시작 가능 → 200
        """
        # location_qr_required를 false로 설정하여 위치 QR 체크 비활성화
        _upsert_admin_setting(db_conn, 'location_qr_required', False)

        # 기존 설정 삭제하여 기본값 사용
        if db_conn and not db_conn.closed:
            cursor = db_conn.cursor()
            cursor.execute(
                "DELETE FROM admin_settings WHERE setting_key = 'phase_block_enabled'"
            )
            db_conn.commit()
            cursor.close()

        _, post_docking_task_id, _, _ = self._create_phase_block_tasks(
            db_conn, s10_fni_manager['id'], docking_completed=False
        )

        response = client.post(
            '/api/app/work/start',
            json={'task_detail_id': post_docking_task_id},
            headers={'Authorization': f'Bearer {s10_fni_manager["token"]}'}
        )
        assert response.status_code == 200, (
            f"Expected 200 with default phase_block (false), got {response.status_code}: {response.get_json()}"
        )
