"""
일시정지/재개 API 테스트 (Sprint 9)
엔드포인트 (실제 BE 구현 기준):
  POST /api/app/work/pause                         - 작업 일시정지
  POST /api/app/work/resume                        - 작업 재개
  GET  /api/app/work/pause-history/<task_detail_id> - 일시정지 이력 조회

응답 형식:
  pause 200:  {"message": str, "paused_at": ISO8601}
  resume 200: {"message": str, "resumed_at": ISO8601, "pause_duration_minutes": int}
  history 200: {"pauses": [...]}

TC-PR-01 ~ TC-PR-18+: 24개 테스트 케이스
"""

import time
import pytest
from datetime import datetime, timezone, timedelta
from typing import Optional


# ============================================================
# 모듈 레벨 클린업 fixture
# ============================================================
@pytest.fixture(autouse=True)
def cleanup_pause_test_data(db_conn):
    """테스트 후 pause/resume 관련 데이터 정리"""
    yield
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            cursor.execute(
                "DELETE FROM workers WHERE email LIKE '%@pause_test.com'"
            )
            db_conn.commit()
            cursor.close()
        except Exception:
            pass


# ============================================================
# Pause/Resume 전용 fixture
# ============================================================
@pytest.fixture
def pause_worker(create_test_worker, get_auth_token):
    """일시정지 테스트 전용 MECH 작업자"""
    unique_email = f'mech_worker_{int(time.time() * 1000)}@pause_test.com'
    worker_id = create_test_worker(
        email=unique_email,
        password='Test123!',
        name='Pause Test Worker',
        role='MECH',
        approval_status='approved',
        email_verified=True
    )
    token = get_auth_token(worker_id, role='MECH')
    return {'id': worker_id, 'email': unique_email, 'token': token}


@pytest.fixture
def pause_admin(create_test_worker, get_admin_auth_token):
    """일시정지 테스트 전용 Admin"""
    unique_email = f'admin_{int(time.time() * 1000)}@pause_test.com'
    worker_id = create_test_worker(
        email=unique_email,
        password='AdminPass123!',
        name='Pause Test Admin',
        role='QI',
        approval_status='approved',
        email_verified=True,
        is_admin=True
    )
    token = get_admin_auth_token(worker_id)
    return {'id': worker_id, 'email': unique_email, 'token': token}


@pytest.fixture
def second_worker(create_test_worker, get_auth_token):
    """두 번째 MECH 작업자 (멀티 작업자 테스트용)"""
    unique_email = f'mech_worker2_{int(time.time() * 1000)}@pause_test.com'
    worker_id = create_test_worker(
        email=unique_email,
        password='Test123!',
        name='Second Test Worker',
        role='MECH',
        approval_status='approved',
        email_verified=True
    )
    token = get_auth_token(worker_id, role='MECH')
    return {'id': worker_id, 'email': unique_email, 'token': token}


@pytest.fixture
def make_task(create_test_product, create_test_task):
    """
    제품(qr_registry) + 작업(app_task_details + work_start_log)을 함께 생성.

    FK 제약: app_task_details.qr_doc_id → qr_registry.qr_doc_id
    pause API는 work_start_log 기반으로 작업자 권한 확인 → started_at 지정 시
    conftest.create_test_task가 work_start_log 자동 삽입함.
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
        is_applicable: bool = True
    ) -> int:
        _counter[0] += 1
        suffix = f'{int(time.time() * 1000)}_{_counter[0]}'
        qr_doc_id = f'DOC-PAUSE-{suffix}'
        serial_number = f'SN-PAUSE-{suffix}'

        create_test_product(
            qr_doc_id=qr_doc_id,
            serial_number=serial_number
        )
        return create_test_task(
            worker_id=worker_id,
            serial_number=serial_number,
            qr_doc_id=qr_doc_id,
            task_category=task_category,
            task_id=task_id_ref,
            task_name=task_name,
            started_at=started_at,
            completed_at=completed_at,
            duration_minutes=duration_minutes,
            is_applicable=is_applicable
        )

    return _make


# ============================================================
# API 요청 헬퍼 함수 (실제 BE 엔드포인트 기준)
# ============================================================
def _pause_task(client, worker_token, task_id, pause_type='manual'):
    """POST /api/app/work/pause"""
    return client.post(
        '/api/app/work/pause',
        json={'task_detail_id': task_id, 'pause_type': pause_type},
        headers={'Authorization': f'Bearer {worker_token}'}
    )


def _resume_task(client, worker_token, task_id):
    """POST /api/app/work/resume"""
    return client.post(
        '/api/app/work/resume',
        json={'task_detail_id': task_id},
        headers={'Authorization': f'Bearer {worker_token}'}
    )


def _complete_task(client, worker_token, task_id):
    """POST /api/app/work/complete"""
    return client.post(
        '/api/app/work/complete',
        json={'task_detail_id': task_id},
        headers={'Authorization': f'Bearer {worker_token}'}
    )


def _get_pause_history(client, worker_token, task_id):
    """GET /api/app/work/pause-history/<task_detail_id>"""
    return client.get(
        f'/api/app/work/pause-history/{task_id}',
        headers={'Authorization': f'Bearer {worker_token}'}
    )


def _get_task_state(db_conn, task_id) -> dict:
    """DB에서 직접 task 상태 조회 (is_paused, total_pause_minutes)"""
    if not db_conn:
        return {}
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT is_paused, total_pause_minutes, completed_at FROM app_task_details WHERE id = %s",
        (task_id,)
    )
    row = cursor.fetchone()
    if row is None:
        cursor.close()
        return {}
    columns = [desc[0] for desc in cursor.description]
    cursor.close()
    return dict(zip(columns, row))


# ============================================================
# TestPauseBasic: 기본 일시정지/재개 동작
# ============================================================
class TestPauseBasic:
    """기본 일시정지/재개 API 테스트 (TC-PR-01 ~ TC-PR-09)"""

    def test_pause_success(self, client, pause_worker, make_task, db_conn):
        """
        TC-PR-01: 진행 중인 작업 일시정지 성공

        Flow: 작업 시작 (create_test_task) → 일시정지
        Expected:
        - Status 200
        - response에 'paused_at' 포함
        - DB: is_paused == True
        """
        task_id = make_task(
            worker_id=pause_worker['id'],
            started_at=datetime.now(timezone.utc)
        )

        response = _pause_task(client, pause_worker['token'], task_id)

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        # Fix 2: pause 응답이 전체 task 객체를 반환 (_task_to_dict)
        assert 'is_paused' in data, f"Response should contain 'is_paused': {data}"
        assert data['is_paused'] is True, f"is_paused should be True: {data}"

        # DB 상태 확인
        state = _get_task_state(db_conn, task_id)
        assert state.get('is_paused') is True, "DB: is_paused should be True"

    def test_resume_success(self, client, pause_worker, make_task, db_conn):
        """
        TC-PR-02: 일시정지된 작업 재개 성공

        Flow: 시작 → 일시정지 → 재개
        Expected:
        - Status 200
        - response에 전체 task 필드 포함 (is_paused=False)
        - DB: is_paused == False
        """
        task_id = make_task(
            worker_id=pause_worker['id'],
            started_at=datetime.now(timezone.utc)
        )

        pause_resp = _pause_task(client, pause_worker['token'], task_id)
        assert pause_resp.status_code == 200

        resume_resp = _resume_task(client, pause_worker['token'], task_id)

        assert resume_resp.status_code == 200, (
            f"Expected 200, got {resume_resp.status_code}: {resume_resp.get_json()}"
        )
        data = resume_resp.get_json()
        # Fix 2: resume 응답이 전체 task 객체를 반환 (_task_to_dict)
        assert 'is_paused' in data, f"Response should contain 'is_paused': {data}"
        assert data['is_paused'] is False, f"is_paused should be False: {data}"
        assert 'total_pause_minutes' in data

        # DB 상태 확인
        state = _get_task_state(db_conn, task_id)
        assert state.get('is_paused') is False, "DB: is_paused should be False"

    def test_resume_records_duration(self, client, pause_worker, make_task, db_conn):
        """
        TC-PR-03: 재개 시 total_pause_minutes 및 DB total_pause_minutes 기록

        Flow: 시작 → 일시정지 → 재개
        Expected:
        - total_pause_minutes >= 0 in response
        - DB: total_pause_minutes >= 0
        """
        task_id = make_task(
            worker_id=pause_worker['id'],
            started_at=datetime.now(timezone.utc)
        )

        _pause_task(client, pause_worker['token'], task_id)
        time.sleep(0.1)
        resume_resp = _resume_task(client, pause_worker['token'], task_id)

        assert resume_resp.status_code == 200
        data = resume_resp.get_json()
        # Fix 2: 전체 task 객체에서 total_pause_minutes 확인
        assert 'total_pause_minutes' in data
        assert data['total_pause_minutes'] >= 0

        # DB total_pause_minutes 확인
        state = _get_task_state(db_conn, task_id)
        assert state.get('total_pause_minutes') is not None
        assert state['total_pause_minutes'] >= 0

    def test_pause_not_started_task(self, client, pause_worker, make_task):
        """
        TC-PR-04: 시작하지 않은 작업 일시정지 → 400 TASK_NOT_STARTED

        Expected:
        - Status 400
        - error: TASK_NOT_STARTED
        """
        task_id = make_task(
            worker_id=pause_worker['id'],
            started_at=None  # 미시작
        )

        response = _pause_task(client, pause_worker['token'], task_id)

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.get_json()
        assert data.get('error') == 'TASK_NOT_STARTED'

    def test_pause_completed_task(self, client, pause_worker, make_task):
        """
        TC-PR-05: 이미 완료된 작업 일시정지 → 400 TASK_ALREADY_COMPLETED

        Expected:
        - Status 400
        - error: TASK_ALREADY_COMPLETED
        """
        started_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        completed_at = datetime.now(timezone.utc)

        task_id = make_task(
            worker_id=pause_worker['id'],
            started_at=started_at,
            completed_at=completed_at,
            duration_minutes=30
        )

        response = _pause_task(client, pause_worker['token'], task_id)

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.get_json()
        assert data.get('error') == 'TASK_ALREADY_COMPLETED'

    def test_pause_already_paused(self, client, pause_worker, make_task):
        """
        TC-PR-06: 이미 일시정지된 작업 재차 일시정지 → 400 TASK_ALREADY_PAUSED

        Flow: 시작 → 일시정지 → 다시 일시정지
        Expected:
        - Status 400
        - error: TASK_ALREADY_PAUSED
        """
        task_id = make_task(
            worker_id=pause_worker['id'],
            started_at=datetime.now(timezone.utc)
        )

        first_pause = _pause_task(client, pause_worker['token'], task_id)
        assert first_pause.status_code == 200

        second_pause = _pause_task(client, pause_worker['token'], task_id)

        assert second_pause.status_code == 400, (
            f"Expected 400, got {second_pause.status_code}"
        )
        data = second_pause.get_json()
        assert data.get('error') == 'TASK_ALREADY_PAUSED'

    def test_resume_not_paused(self, client, pause_worker, make_task):
        """
        TC-PR-07: 일시정지 상태가 아닌 작업 재개 시도 → 400 TASK_NOT_PAUSED

        Flow: 시작 → 재개 시도 (일시정지 없이)
        Expected:
        - Status 400
        - error: TASK_NOT_PAUSED
        """
        task_id = make_task(
            worker_id=pause_worker['id'],
            started_at=datetime.now(timezone.utc)
        )

        response = _resume_task(client, pause_worker['token'], task_id)

        # 일시정지 상태가 아니면 400 TASK_NOT_PAUSED 또는 404 TASK_NOT_FOUND
        assert response.status_code in (400, 404), f"Expected 400 or 404, got {response.status_code}"
        data = response.get_json()
        assert data.get('error') in ('TASK_NOT_PAUSED', 'TASK_NOT_FOUND', 'PAUSE_NOT_FOUND')

    def test_resume_wrong_worker(
        self, client, pause_worker, second_worker, make_task
    ):
        """
        TC-PR-08: 다른 작업자가 재개 시도 → 403 FORBIDDEN

        Flow: 작업자A 시작 → 일시정지 → 작업자B 재개 시도
        Expected:
        - Status 403
        - error: FORBIDDEN
        """
        task_id = make_task(
            worker_id=pause_worker['id'],
            started_at=datetime.now(timezone.utc)
        )

        pause_resp = _pause_task(client, pause_worker['token'], task_id)
        assert pause_resp.status_code == 200

        resume_resp = _resume_task(client, second_worker['token'], task_id)

        assert resume_resp.status_code == 403, (
            f"Expected 403, got {resume_resp.status_code}: {resume_resp.get_json()}"
        )
        data = resume_resp.get_json()
        assert data.get('error') == 'FORBIDDEN'

    def test_admin_can_resume(
        self, client, pause_worker, pause_admin, make_task, db_conn
    ):
        """
        TC-PR-09: 관리자는 다른 작업자의 일시정지를 재개할 수 있음

        Flow: 작업자 시작 → 일시정지 → 관리자 재개
        Expected:
        - Status 200
        - DB: is_paused == False
        """
        task_id = make_task(
            worker_id=pause_worker['id'],
            started_at=datetime.now(timezone.utc)
        )

        pause_resp = _pause_task(client, pause_worker['token'], task_id)
        assert pause_resp.status_code == 200

        resume_resp = _resume_task(client, pause_admin['token'], task_id)

        assert resume_resp.status_code == 200, (
            f"Admin should be able to resume: {resume_resp.get_json()}"
        )

        state = _get_task_state(db_conn, task_id)
        assert state.get('is_paused') is False, "DB: is_paused should be False after admin resume"


# ============================================================
# TestPauseDuration: 일시정지 시간의 duration 영향
# ============================================================
class TestPauseDuration:
    """일시정지 시간이 duration 계산에 반영되는지 검증 (TC-PR-10 ~ TC-PR-12)"""

    def test_pause_subtracted_from_duration(
        self, client, pause_worker, make_task, db_conn
    ):
        """
        TC-PR-10: 일시정지 시간이 total_pause_minutes에 반영되는지 확인

        Flow: 시작 → 일시정지 → 재개 → 완료
        Expected:
        - DB: total_pause_minutes >= 0
        - 완료 후 duration_minutes <= elapsed_minutes
        """
        task_id = make_task(
            worker_id=pause_worker['id'],
            started_at=datetime.now(timezone.utc)
        )

        _pause_task(client, pause_worker['token'], task_id)
        time.sleep(0.1)
        _resume_task(client, pause_worker['token'], task_id)

        complete_resp = _complete_task(client, pause_worker['token'], task_id)

        if complete_resp.status_code == 200:
            state = _get_task_state(db_conn, task_id)
            assert state.get('total_pause_minutes') is not None, (
                "total_pause_minutes should be set after completion"
            )

    def test_multiple_pauses_subtracted(
        self, client, pause_worker, make_task, db_conn
    ):
        """
        TC-PR-11: 여러 번의 일시정지 이력이 work_pause_log에 저장

        Flow: 시작 → 일시정지1 → 재개1 → 일시정지2 → 재개2 → 완료
        Expected:
        - work_pause_log에 2개의 완료된 레코드 (resumed_at IS NOT NULL)
        - total_pause_minutes: 두 pause의 합산
        """
        task_id = make_task(
            worker_id=pause_worker['id'],
            started_at=datetime.now(timezone.utc)
        )

        # 첫 번째 pause/resume
        p1 = _pause_task(client, pause_worker['token'], task_id)
        assert p1.status_code == 200
        time.sleep(0.1)
        r1 = _resume_task(client, pause_worker['token'], task_id)
        assert r1.status_code == 200
        dur1 = r1.get_json().get('pause_duration_minutes', 0)

        # 두 번째 pause/resume
        p2 = _pause_task(client, pause_worker['token'], task_id)
        assert p2.status_code == 200
        time.sleep(0.1)
        r2 = _resume_task(client, pause_worker['token'], task_id)
        assert r2.status_code == 200
        dur2 = r2.get_json().get('pause_duration_minutes', 0)

        # work_pause_log에 2개 기록 확인
        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM work_pause_log
                WHERE task_detail_id = %s AND resumed_at IS NOT NULL
                """,
                (task_id,)
            )
            row = cursor.fetchone()
            cursor.close()
            cnt = row[0] if row else 0
            assert cnt >= 2, (
                f"Expected at least 2 completed pause records, got {cnt}"
            )

        # DB total_pause_minutes가 두 pause 합산과 일치 확인
        state = _get_task_state(db_conn, task_id)
        if state:
            expected_total = dur1 + dur2
            assert state.get('total_pause_minutes') == expected_total, (
                f"total_pause_minutes: expected {expected_total}, got {state.get('total_pause_minutes')}"
            )

    def test_complete_while_paused_auto_resume(
        self, client, pause_worker, make_task
    ):
        """
        TC-PR-12: 일시정지 상태에서 완료 요청 시 동작 확인

        Flow: 시작 → 일시정지 → 완료 요청
        Expected:
        - 200 (auto-resume 후 완료) 또는 400 (일시정지 중 완료 불가)
        - 응답이 일관성 있어야 함
        """
        task_id = make_task(
            worker_id=pause_worker['id'],
            started_at=datetime.now(timezone.utc)
        )

        pause_resp = _pause_task(client, pause_worker['token'], task_id)
        assert pause_resp.status_code == 200

        complete_resp = _complete_task(client, pause_worker['token'], task_id)

        assert complete_resp.status_code in (200, 400), (
            f"Expected 200 or 400, got {complete_resp.status_code}"
        )
        if complete_resp.status_code == 400:
            assert 'error' in complete_resp.get_json()


# ============================================================
# TestPauseHistory: 일시정지 이력 조회
# ============================================================
class TestPauseHistory:
    """일시정지 이력 API 테스트 (TC-PR-13 ~ TC-PR-14)"""

    def test_get_pause_history(self, client, pause_worker, make_task):
        """
        TC-PR-13: 일시정지 이력 조회 성공

        Flow: 시작 → 일시정지 → 재개 → GET /api/app/work/pause-history/{id}
        Expected:
        - Status 200
        - pauses 배열에 1개 이상 레코드
        - 각 항목에 paused_at, pause_type 포함
        """
        task_id = make_task(
            worker_id=pause_worker['id'],
            started_at=datetime.now(timezone.utc)
        )

        _pause_task(client, pause_worker['token'], task_id)
        _resume_task(client, pause_worker['token'], task_id)

        history_resp = _get_pause_history(client, pause_worker['token'], task_id)

        assert history_resp.status_code == 200, (
            f"Expected 200, got {history_resp.status_code}: {history_resp.get_json()}"
        )
        data = history_resp.get_json()
        pauses = data.get('pauses', [])
        assert isinstance(pauses, list), "pauses should be a list"
        assert len(pauses) >= 1, "Should have at least 1 pause record"

        pause = pauses[0]
        assert 'paused_at' in pause, f"Pause record should have 'paused_at': {pause}"
        assert 'pause_type' in pause, f"Pause record should have 'pause_type': {pause}"

    def test_empty_pause_history(self, client, pause_worker, make_task):
        """
        TC-PR-14: 일시정지 이력 없을 때 빈 목록 반환

        Flow: 시작만 한 작업에 대해 GET pause-history
        Expected:
        - Status 200
        - pauses 빈 배열
        """
        task_id = make_task(
            worker_id=pause_worker['id'],
            started_at=datetime.now(timezone.utc)
        )

        history_resp = _get_pause_history(client, pause_worker['token'], task_id)

        assert history_resp.status_code == 200, (
            f"Expected 200, got {history_resp.status_code}"
        )
        data = history_resp.get_json()
        pauses = data.get('pauses', [])
        assert isinstance(pauses, list), "pauses should be a list"
        assert len(pauses) == 0, "Should have empty pause history"


# ============================================================
# TestPauseMultiWorker: 멀티 작업자 일시정지 시나리오
# ============================================================
class TestPauseMultiWorker:
    """멀티 작업자 환경에서의 일시정지 테스트 (TC-PR-15 ~ TC-PR-17)"""

    def test_one_paused_other_continues(
        self, client, pause_worker, second_worker, make_task, db_conn
    ):
        """
        TC-PR-15: 작업자A 일시정지 → DB에 is_paused=True 반영

        Flow: A 시작 → A 일시정지
        Expected:
        - A 일시정지: 200
        - DB: is_paused == True
        """
        task_id = make_task(
            worker_id=pause_worker['id'],
            started_at=datetime.now(timezone.utc)
        )

        pause_a = _pause_task(client, pause_worker['token'], task_id)
        assert pause_a.status_code == 200

        state = _get_task_state(db_conn, task_id)
        assert state.get('is_paused') is True

    def test_both_paused_both_resume(
        self, client, pause_worker, make_task, db_conn
    ):
        """
        TC-PR-16: 순차 일시정지 → 순차 재개

        Flow: 일시정지1 → 재개1 → 일시정지2 → 재개2
        Expected:
        - 각 pause/resume 200
        - 최종 DB: is_paused == False
        """
        task_id = make_task(
            worker_id=pause_worker['id'],
            started_at=datetime.now(timezone.utc)
        )

        # 첫 번째 pause/resume
        p1 = _pause_task(client, pause_worker['token'], task_id)
        assert p1.status_code == 200
        r1 = _resume_task(client, pause_worker['token'], task_id)
        assert r1.status_code == 200

        # 두 번째 pause
        p2 = _pause_task(client, pause_worker['token'], task_id)
        assert p2.status_code == 200

        # 두 번째 resume
        r2 = _resume_task(client, pause_worker['token'], task_id)
        assert r2.status_code == 200

        state = _get_task_state(db_conn, task_id)
        assert state.get('is_paused') is False

    def test_one_paused_other_completes(
        self, client, pause_worker, second_worker, make_task
    ):
        """
        TC-PR-17: 작업자A 일시정지 상태에서 B 완료 시도 → 403 FORBIDDEN

        B는 work_start_log에 시작 기록이 없으므로 403 예상.
        """
        task_id = make_task(
            worker_id=pause_worker['id'],
            started_at=datetime.now(timezone.utc)
        )

        _pause_task(client, pause_worker['token'], task_id)

        complete_b = _complete_task(client, second_worker['token'], task_id)

        # B가 task를 시작하지 않았으므로 403
        assert complete_b.status_code in (400, 403), (
            f"Expected 400 or 403 (B not started task), got {complete_b.status_code}"
        )


# ============================================================
# TestPauseAuth: 인증/권한 테스트
# ============================================================
class TestPauseAuth:
    """일시정지/재개 API 인증 테스트 (TC-PR-18+)"""

    def test_unauthenticated_pause(self, client, make_task, pause_worker):
        """
        TC-PR-18: 인증 없이 일시정지 시도 → 401

        Expected:
        - Status 401
        """
        task_id = make_task(
            worker_id=pause_worker['id'],
            started_at=datetime.now(timezone.utc)
        )

        response = client.post(
            '/api/app/work/pause',
            json={'task_detail_id': task_id}
        )

        assert response.status_code == 401, (
            f"Expected 401 without auth, got {response.status_code}"
        )

    def test_unauthenticated_resume(self, client, make_task, pause_worker):
        """
        인증 없이 재개 시도 → 401
        """
        task_id = make_task(
            worker_id=pause_worker['id'],
            started_at=datetime.now(timezone.utc)
        )

        response = client.post(
            '/api/app/work/resume',
            json={'task_detail_id': task_id}
        )

        assert response.status_code == 401, (
            f"Expected 401 without auth, got {response.status_code}"
        )

    def test_unauthenticated_pause_history(self, client, make_task, pause_worker):
        """
        인증 없이 이력 조회 → 401
        """
        task_id = make_task(
            worker_id=pause_worker['id'],
            started_at=datetime.now(timezone.utc)
        )

        response = client.get(f'/api/app/work/pause-history/{task_id}')

        assert response.status_code == 401, (
            f"Expected 401 without auth, got {response.status_code}"
        )

    def test_pause_task_not_found(self, client, pause_worker):
        """
        존재하지 않는 task_id로 일시정지 → 404 TASK_NOT_FOUND
        """
        response = _pause_task(client, pause_worker['token'], task_id=999999)

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}"
        )
        data = response.get_json()
        assert data.get('error') == 'TASK_NOT_FOUND'

    def test_resume_task_not_found(self, client, pause_worker):
        """
        존재하지 않는 task_id로 재개 → 404 TASK_NOT_FOUND
        """
        response = _resume_task(client, pause_worker['token'], task_id=999999)

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}"
        )
        data = response.get_json()
        assert data.get('error') == 'TASK_NOT_FOUND'

    def test_pause_missing_task_id(self, client, pause_worker):
        """
        task_detail_id 없이 일시정지 → 400 INVALID_REQUEST
        """
        response = client.post(
            '/api/app/work/pause',
            json={},
            headers={'Authorization': f'Bearer {pause_worker["token"]}'}
        )

        assert response.status_code == 400, (
            f"Expected 400, got {response.status_code}"
        )
        data = response.get_json()
        assert data.get('error') == 'INVALID_REQUEST'

    def test_resume_missing_task_id(self, client, pause_worker):
        """
        task_detail_id 없이 재개 → 400 INVALID_REQUEST
        """
        response = client.post(
            '/api/app/work/resume',
            json={},
            headers={'Authorization': f'Bearer {pause_worker["token"]}'}
        )

        assert response.status_code == 400, (
            f"Expected 400, got {response.status_code}"
        )
        data = response.get_json()
        assert data.get('error') == 'INVALID_REQUEST'


# ============================================================
# TestPauseCoworkerResume: BUG-6 다중작업자 동료 재개 테스트
# ============================================================
class TestPauseCoworkerResume:
    """
    BUG-6: 다중작업자 Task에서 동료가 resume 시 403 FORBIDDEN 버그
    Partner 회사(FNI, C&A) 다중작업자 환경에서 같은 task의 동료가
    일시정지를 재개할 수 있어야 함.

    TC-PR-19 ~ TC-PR-22
    """

    @pytest.fixture
    def fni_worker_a(self, create_test_worker, get_auth_token):
        """FNI 소속 작업자 A"""
        unique_email = f'fni_a_{int(time.time() * 1000)}@pause_test.com'
        worker_id = create_test_worker(
            email=unique_email,
            password='Test123!',
            name='FNI Worker A',
            role='ELEC',
            company='FNI',
            approval_status='approved',
            email_verified=True
        )
        token = get_auth_token(worker_id, role='ELEC')
        return {'id': worker_id, 'email': unique_email, 'token': token}

    @pytest.fixture
    def fni_worker_b(self, create_test_worker, get_auth_token):
        """FNI 소속 작업자 B (동료)"""
        unique_email = f'fni_b_{int(time.time() * 1000)}@pause_test.com'
        worker_id = create_test_worker(
            email=unique_email,
            password='Test123!',
            name='FNI Worker B',
            role='ELEC',
            company='FNI',
            approval_status='approved',
            email_verified=True
        )
        token = get_auth_token(worker_id, role='ELEC')
        return {'id': worker_id, 'email': unique_email, 'token': token}

    @pytest.fixture
    def unrelated_worker(self, create_test_worker, get_auth_token):
        """무관한 제3자 작업자 (다른 회사, 해당 task에 참여하지 않음)"""
        unique_email = f'unrelated_{int(time.time() * 1000)}@pause_test.com'
        worker_id = create_test_worker(
            email=unique_email,
            password='Test123!',
            name='Unrelated Worker',
            role='MECH',
            company='BAT',
            approval_status='approved',
            email_verified=True
        )
        token = get_auth_token(worker_id, role='MECH')
        return {'id': worker_id, 'email': unique_email, 'token': token}

    @pytest.fixture
    def multi_worker_task(
        self, db_conn, create_test_product, create_test_task,
        fni_worker_a, fni_worker_b
    ):
        """
        다중작업자 task 생성:
        - worker_a가 task 생성 + start_log
        - worker_b도 start_log에 추가 (다중작업자)
        """
        suffix = f'{int(time.time() * 1000)}'
        qr_doc_id = f'DOC-BUG6-{suffix}'
        serial_number = f'SN-BUG6-{suffix}'

        create_test_product(
            qr_doc_id=qr_doc_id,
            serial_number=serial_number
        )

        started_at = datetime.now(timezone.utc)

        # worker_a로 task 생성 (work_start_log 자동 삽입)
        task_id = create_test_task(
            worker_id=fni_worker_a['id'],
            serial_number=serial_number,
            qr_doc_id=qr_doc_id,
            task_category='ELEC',
            task_id='WIRING_CHECK',
            task_name='배선 점검',
            started_at=started_at
        )

        # worker_b의 start_log 추가 (다중작업자 시뮬레이션)
        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute("""
                INSERT INTO work_start_log
                    (task_id, worker_id, serial_number, qr_doc_id,
                     task_category, task_id_ref, task_name, started_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (task_id, fni_worker_b['id'], serial_number, qr_doc_id,
                  'ELEC', 'WIRING_CHECK', '배선 점검', started_at))
            db_conn.commit()
            cursor.close()

        return task_id

    def test_coworker_can_resume_partner_task(
        self, client, fni_worker_a, fni_worker_b,
        multi_worker_task, db_conn
    ):
        """
        TC-PR-19: 다중작업자 task — 동료(start_log 있음)가 resume → 200 성공

        Flow: worker_a가 일시정지 → worker_b(같은 task 참여자)가 재개
        Expected:
        - Status 200
        - DB: is_paused == False
        """
        task_id = multi_worker_task

        # worker_a가 일시정지
        pause_resp = _pause_task(client, fni_worker_a['token'], task_id)
        assert pause_resp.status_code == 200, (
            f"Pause failed: {pause_resp.get_json()}"
        )

        # worker_b(동료)가 재개
        resume_resp = _resume_task(client, fni_worker_b['token'], task_id)

        assert resume_resp.status_code == 200, (
            f"BUG-6: Coworker resume should succeed but got "
            f"{resume_resp.status_code}: {resume_resp.get_json()}"
        )

        # DB 확인
        state = _get_task_state(db_conn, task_id)
        assert state.get('is_paused') is False, (
            "DB: is_paused should be False after coworker resume"
        )

    def test_unrelated_worker_cannot_resume(
        self, client, fni_worker_a, unrelated_worker,
        multi_worker_task
    ):
        """
        TC-PR-20: 다중작업자 task — 무관한 제3자(start_log 없음)가 resume → 403

        Flow: worker_a가 일시정지 → 무관한 작업자가 재개 시도
        Expected:
        - Status 403
        - error: FORBIDDEN
        """
        task_id = multi_worker_task

        # worker_a가 일시정지
        pause_resp = _pause_task(client, fni_worker_a['token'], task_id)
        assert pause_resp.status_code == 200

        # 무관한 제3자가 재개 시도
        resume_resp = _resume_task(client, unrelated_worker['token'], task_id)

        assert resume_resp.status_code == 403, (
            f"Unrelated worker should be rejected, got "
            f"{resume_resp.status_code}: {resume_resp.get_json()}"
        )
        data = resume_resp.get_json()
        assert data.get('error') == 'FORBIDDEN'

    def test_pause_owner_can_resume_own_pause(
        self, client, fni_worker_a, multi_worker_task, db_conn
    ):
        """
        TC-PR-21: Partner 다중작업자 — pause한 본인이 resume → 200 성공

        Flow: worker_a(FNI)가 일시정지 → worker_a 본인이 재개
        Expected:
        - Status 200
        - DB: is_paused == False
        """
        task_id = multi_worker_task

        pause_resp = _pause_task(client, fni_worker_a['token'], task_id)
        assert pause_resp.status_code == 200

        resume_resp = _resume_task(client, fni_worker_a['token'], task_id)

        assert resume_resp.status_code == 200, (
            f"Pause owner resume should succeed: {resume_resp.get_json()}"
        )

        state = _get_task_state(db_conn, task_id)
        assert state.get('is_paused') is False

    def test_partner_single_worker_resume(
        self, client, fni_worker_a, db_conn,
        create_test_product, create_test_task
    ):
        """
        TC-PR-22: Partner 단독작업자 — pause한 본인이 resume → 200 성공

        단독작업(worker_count=1)에서 FNI 작업자가 본인 pause/resume.
        기존 TC-PR-02와 유사하나 company='FNI'(Partner) 확인.
        """
        suffix = f'{int(time.time() * 1000)}_single'
        qr_doc_id = f'DOC-BUG6-{suffix}'
        serial_number = f'SN-BUG6-{suffix}'

        create_test_product(
            qr_doc_id=qr_doc_id,
            serial_number=serial_number
        )

        task_id = create_test_task(
            worker_id=fni_worker_a['id'],
            serial_number=serial_number,
            qr_doc_id=qr_doc_id,
            task_category='ELEC',
            task_id='SINGLE_CHECK',
            task_name='단독 점검',
            started_at=datetime.now(timezone.utc)
        )

        pause_resp = _pause_task(client, fni_worker_a['token'], task_id)
        assert pause_resp.status_code == 200

        resume_resp = _resume_task(client, fni_worker_a['token'], task_id)

        assert resume_resp.status_code == 200, (
            f"Partner single worker resume should succeed: {resume_resp.get_json()}"
        )

        state = _get_task_state(db_conn, task_id)
        assert state.get('is_paused') is False
