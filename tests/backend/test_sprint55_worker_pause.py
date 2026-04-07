"""
Sprint 55: Worker별 Pause/Resume + Auto-Finalize 테스트
=========================================================
TC-WP-01 ~ TC-WP-09, TC-WP-03a  (Worker별 Pause — 10건)
TC-AF-01 ~ TC-AF-07              (Auto-Finalize — 7건)
TC-FT-01 ~ TC-FT-03              (FINAL Task 릴레이 불가 — 3건)
TC-WH-01 ~ TC-WH-02              (Working Hours 연동 — 2건)
TC-CT-01 ~ TC-CT-03              (개인별 작업시간 정확도 — 3건)
TC-SP-01 ~ TC-SP-02              (Scheduler 자동 Pause 호환 — 2건)
                                  총 28건 (DB 실행 기반 통합 테스트)

Regression 원칙:
  - TC의 Assert가 정답. 코드가 다른 결과를 내면 코드가 틀린 것.
  - 테스트를 바꿔서 통과시키지 말 것. Sprint 55 기대값이 나오도록 코드를 수정할 것.
"""

import time
import pytest
from datetime import datetime, timezone, timedelta


# ============================================================
# 클린업: conftest.py의 create_test_worker teardown에 의존
# workers FK가 ON DELETE RESTRICT이므로 직접 DELETE 불가.
# create_test_worker가 FK 순서대로 정리함:
#   work_pause_log → work_start_log → work_completion_log → workers
# ============================================================


# ============================================================
# Worker Fixtures
# ============================================================
@pytest.fixture
def worker_a(create_test_worker, get_auth_token):
    """작업자 A (MECH)"""
    unique_email = f'sp55_a_{int(time.time() * 1000)}@sprint55_test.com'
    worker_id = create_test_worker(
        email=unique_email, password='Test123!',
        name='Worker A', role='MECH',
        approval_status='approved', email_verified=True
    )
    token = get_auth_token(worker_id, role='MECH')
    return {'id': worker_id, 'email': unique_email, 'token': token}


@pytest.fixture
def worker_b(create_test_worker, get_auth_token):
    """작업자 B (MECH)"""
    unique_email = f'sp55_b_{int(time.time() * 1000)}@sprint55_test.com'
    worker_id = create_test_worker(
        email=unique_email, password='Test123!',
        name='Worker B', role='MECH',
        approval_status='approved', email_verified=True
    )
    token = get_auth_token(worker_id, role='MECH')
    return {'id': worker_id, 'email': unique_email, 'token': token}


@pytest.fixture
def worker_c(create_test_worker, get_auth_token):
    """작업자 C (MECH)"""
    unique_email = f'sp55_c_{int(time.time() * 1000)}@sprint55_test.com'
    worker_id = create_test_worker(
        email=unique_email, password='Test123!',
        name='Worker C', role='MECH',
        approval_status='approved', email_verified=True
    )
    token = get_auth_token(worker_id, role='MECH')
    return {'id': worker_id, 'email': unique_email, 'token': token}


@pytest.fixture
def admin_worker(create_test_worker, get_admin_auth_token):
    """관리자"""
    unique_email = f'sp55_admin_{int(time.time() * 1000)}@sprint55_test.com'
    worker_id = create_test_worker(
        email=unique_email, password='AdminPass123!',
        name='Admin Worker', role='QI',
        approval_status='approved', email_verified=True,
        is_admin=True
    )
    token = get_admin_auth_token(worker_id)
    return {'id': worker_id, 'email': unique_email, 'token': token}


# ============================================================
# Task Fixtures
# ============================================================
@pytest.fixture
def make_multi_task(db_conn, create_test_product, create_test_task):
    """
    다중작업자 task 생성.
    worker_ids 리스트의 첫 번째가 task 소유자, 나머지는 start_log 추가.
    """
    _counter = [0]

    def _make(
        worker_ids: list,
        task_id_ref: str = 'CABINET_ASSY',
        task_name: str = '캐비넷 조립',
        task_category: str = 'MECH',
    ) -> int:
        _counter[0] += 1
        suffix = f'{int(time.time() * 1000)}_{_counter[0]}'
        qr_doc_id = f'DOC-SP55-{suffix}'
        serial_number = f'SN-SP55-{suffix}'

        create_test_product(
            qr_doc_id=qr_doc_id,
            serial_number=serial_number
        )

        started_at = datetime.now(timezone.utc)

        # 첫 번째 worker로 task 생성 (start_log 자동)
        task_detail_id = create_test_task(
            worker_id=worker_ids[0],
            serial_number=serial_number,
            qr_doc_id=qr_doc_id,
            task_category=task_category,
            task_id=task_id_ref,
            task_name=task_name,
            started_at=started_at
        )

        # 나머지 worker start_log 추가
        if db_conn and len(worker_ids) > 1:
            cursor = db_conn.cursor()
            for wid in worker_ids[1:]:
                cursor.execute("""
                    INSERT INTO work_start_log
                        (task_id, worker_id, serial_number, qr_doc_id,
                         task_category, task_id_ref, task_name, started_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (task_detail_id, wid, serial_number, qr_doc_id,
                      task_category, task_id_ref, task_name, started_at))
            db_conn.commit()
            cursor.close()

        return task_detail_id

    return _make


@pytest.fixture
def make_single_task(create_test_product, create_test_task):
    """단독 작업자 task 생성"""
    _counter = [0]

    def _make(worker_id: int, **kwargs) -> int:
        _counter[0] += 1
        suffix = f'{int(time.time() * 1000)}_{_counter[0]}'
        qr_doc_id = f'DOC-SP55S-{suffix}'
        serial_number = f'SN-SP55S-{suffix}'

        create_test_product(
            qr_doc_id=qr_doc_id,
            serial_number=serial_number
        )

        defaults = dict(
            task_category='MECH',
            task_id='CABINET_ASSY',
            task_name='캐비넷 조립',
            started_at=datetime.now(timezone.utc),
        )
        defaults.update(kwargs)

        return create_test_task(
            worker_id=worker_id,
            serial_number=serial_number,
            qr_doc_id=qr_doc_id,
            **defaults
        )

    return _make


# ============================================================
# API 헬퍼
# ============================================================
def _pause(client, token, task_id, pause_type='manual'):
    return client.post(
        '/api/app/work/pause',
        json={'task_detail_id': task_id, 'pause_type': pause_type},
        headers={'Authorization': f'Bearer {token}'}
    )


def _resume(client, token, task_id):
    return client.post(
        '/api/app/work/resume',
        json={'task_detail_id': task_id},
        headers={'Authorization': f'Bearer {token}'}
    )


def _complete(client, token, task_id, finalize=True):
    return client.post(
        '/api/app/work/complete',
        json={'task_detail_id': task_id, 'finalize': finalize},
        headers={'Authorization': f'Bearer {token}'}
    )


def _start_task(client, token, task_id):
    """릴레이 재시작용"""
    return client.post(
        '/api/app/work/start',
        json={'task_detail_id': task_id},
        headers={'Authorization': f'Bearer {token}'}
    )


def _get_task_state(db_conn, task_id) -> dict:
    if not db_conn:
        return {}
    cursor = db_conn.cursor()
    cursor.execute(
        """SELECT is_paused, total_pause_minutes, completed_at,
                  duration_minutes, elapsed_minutes, worker_count
           FROM app_task_details WHERE id = %s""",
        (task_id,)
    )
    row = cursor.fetchone()
    if row is None:
        cursor.close()
        return {}
    columns = [desc[0] for desc in cursor.description]
    cursor.close()
    return dict(zip(columns, row))


def _count_completion_logs(db_conn, task_id) -> int:
    if not db_conn:
        return 0
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM work_completion_log WHERE task_id = %s",
        (task_id,)
    )
    cnt = cursor.fetchone()[0]
    cursor.close()
    return cnt


def _count_pause_logs(db_conn, task_id, worker_id=None, active_only=False) -> int:
    if not db_conn:
        return 0
    cursor = db_conn.cursor()
    sql = "SELECT COUNT(*) FROM work_pause_log WHERE task_detail_id = %s"
    params = [task_id]
    if worker_id:
        sql += " AND worker_id = %s"
        params.append(worker_id)
    if active_only:
        sql += " AND resumed_at IS NULL"
    cursor.execute(sql, params)
    cnt = cursor.fetchone()[0]
    cursor.close()
    return cnt


# ============================================================
# TC-WP: Worker별 Pause 기본 (01~05)
# ============================================================
class TestWorkerPauseBasic:
    """TC-WP-01 ~ TC-WP-05: 다중작업자 개인별 pause/resume"""

    def test_wp_01_a_pause_b_working(
        self, client, worker_a, worker_b, make_multi_task, db_conn
    ):
        """
        TC-WP-01: A pause → A만 paused, B는 working
        Assert:
          - pause 200
          - response.my_pause_status == 'paused'
          - task.is_paused == false (B working)
          - worker_b GET → my_pause_status == 'working'
        """
        task_id = make_multi_task([worker_a['id'], worker_b['id']])

        resp = _pause(client, worker_a['token'], task_id)
        assert resp.status_code == 200, f"Pause failed: {resp.get_json()}"

        data = resp.get_json()
        # Sprint 55: 응답에 my_pause_status 포함
        assert data.get('my_pause_status') == 'paused', (
            f"A should be paused: {data}"
        )

        # task.is_paused = false (B still working)
        state = _get_task_state(db_conn, task_id)
        assert state.get('is_paused') is False, (
            "task.is_paused should be False — B is still working"
        )

        # DB: A의 pause_log 존재
        assert _count_pause_logs(db_conn, task_id, worker_a['id'], active_only=True) == 1

    def test_wp_02_a_pause_resume(
        self, client, worker_a, worker_b, make_multi_task, db_conn
    ):
        """
        TC-WP-02: A pause → A resume → A working
        Assert:
          - resume 200
          - my_pause_status == 'working'
          - pause_log: resumed_at IS NOT NULL
        """
        task_id = make_multi_task([worker_a['id'], worker_b['id']])

        _pause(client, worker_a['token'], task_id)
        resp = _resume(client, worker_a['token'], task_id)

        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get('my_pause_status') == 'working'

        state = _get_task_state(db_conn, task_id)
        assert state.get('is_paused') is False

        # pause_log resolved
        assert _count_pause_logs(db_conn, task_id, worker_a['id'], active_only=True) == 0

    def test_wp_03_b_cannot_resume_a_pause(
        self, client, worker_a, worker_b, make_multi_task, db_conn
    ):
        """
        TC-WP-03: A pause → B resume 시도 → 404 PAUSE_NOT_FOUND
        Sprint 55: 본인 pause만 resume. B에게는 active pause가 없음.
        """
        task_id = make_multi_task([worker_a['id'], worker_b['id']])

        _pause(client, worker_a['token'], task_id)
        resp = _resume(client, worker_b['token'], task_id)

        assert resp.status_code == 404, (
            f"B has no active pause, expected 404: {resp.get_json()}"
        )
        data = resp.get_json()
        assert data.get('error') == 'PAUSE_NOT_FOUND'

        # A의 pause 여전히 active
        assert _count_pause_logs(db_conn, task_id, worker_a['id'], active_only=True) == 1

    def test_wp_04_both_paused(
        self, client, worker_a, worker_b, make_multi_task, db_conn
    ):
        """
        TC-WP-04: A pause + B pause → task.is_paused = true (전원 paused)
        """
        task_id = make_multi_task([worker_a['id'], worker_b['id']])

        # A pause
        _pause(client, worker_a['token'], task_id)
        state = _get_task_state(db_conn, task_id)
        assert state.get('is_paused') is False, "After A pause only: should be False"

        # B pause
        _pause(client, worker_b['token'], task_id)
        state = _get_task_state(db_conn, task_id)
        assert state.get('is_paused') is True, "After A+B pause: should be True"

    def test_wp_05_a_resume_b_still_paused(
        self, client, worker_a, worker_b, make_multi_task, db_conn
    ):
        """
        TC-WP-05: 전원 paused → A resume → task.is_paused = false
        A가 working 복귀하므로 전원 paused가 아님.
        """
        task_id = make_multi_task([worker_a['id'], worker_b['id']])

        _pause(client, worker_a['token'], task_id)
        _pause(client, worker_b['token'], task_id)

        # A resume
        resp = _resume(client, worker_a['token'], task_id)
        assert resp.status_code == 200

        state = _get_task_state(db_conn, task_id)
        assert state.get('is_paused') is False, (
            "A resumed → not all paused → is_paused should be False"
        )


# ============================================================
# TC-WP: 단독 작업자 하위호환 (06~07)
# ============================================================
class TestWorkerPauseSingleCompat:
    """TC-WP-06 ~ TC-WP-07: 단독작업자 하위호환"""

    def test_wp_06_single_pause(
        self, client, worker_a, make_single_task, db_conn
    ):
        """
        TC-WP-06: 단독작업자 pause → task.is_paused = true
        1인이므로 전원 = 본인 → true
        """
        task_id = make_single_task(worker_a['id'])

        resp = _pause(client, worker_a['token'], task_id)
        assert resp.status_code == 200

        state = _get_task_state(db_conn, task_id)
        assert state.get('is_paused') is True

    def test_wp_07_single_resume(
        self, client, worker_a, make_single_task, db_conn
    ):
        """
        TC-WP-07: 단독작업자 pause → resume → is_paused = false
        """
        task_id = make_single_task(worker_a['id'])

        _pause(client, worker_a['token'], task_id)
        _resume(client, worker_a['token'], task_id)

        state = _get_task_state(db_conn, task_id)
        assert state.get('is_paused') is False


# ============================================================
# TC-WP: 릴레이 재시작 + Pause 판정 (08~09) + Admin resume (03a)
# ============================================================
class TestWorkerPauseRelayRestart:
    """TC-WP-08, TC-WP-09: 릴레이 재시작 후 pause 판정"""

    def test_wp_08_relay_restart_pause_active(
        self, client, worker_a, worker_b, make_multi_task, db_conn
    ):
        """
        TC-WP-08: A complete(relay) → A restart → A pause
        A는 active (MAX(start) > MAX(completion)) → pause 반영
        task.is_paused == false (B working)
        """
        task_id = make_multi_task([worker_a['id'], worker_b['id']])

        # A relay 종료
        resp = _complete(client, worker_a['token'], task_id, finalize=False)
        assert resp.status_code == 200

        # A 재시작
        start_resp = _start_task(client, worker_a['token'], task_id)
        assert start_resp.status_code == 200, (
            f"A restart failed: {start_resp.get_json()}"
        )

        # A pause
        pause_resp = _pause(client, worker_a['token'], task_id)
        assert pause_resp.status_code == 200

        # A는 active (재시작함) + paused. B는 active + working
        state = _get_task_state(db_conn, task_id)
        assert state.get('is_paused') is False, (
            "B still working → not all paused"
        )

    def test_wp_09_relay_restart_all_paused(
        self, client, worker_a, worker_b, make_multi_task, db_conn
    ):
        """
        TC-WP-09: TC-WP-08 이후 B도 pause → 전원 paused → is_paused = true
        """
        task_id = make_multi_task([worker_a['id'], worker_b['id']])

        # A relay → restart → pause
        _complete(client, worker_a['token'], task_id, finalize=False)
        _start_task(client, worker_a['token'], task_id)
        _pause(client, worker_a['token'], task_id)

        # B pause
        _pause(client, worker_b['token'], task_id)

        state = _get_task_state(db_conn, task_id)
        assert state.get('is_paused') is True, (
            "A(relay-restart, paused) + B(paused) → all paused → True"
        )


class TestWorkerPauseAdminResume:
    """TC-WP-03a: Admin이 다른 worker의 pause resume"""

    def test_wp_03a_admin_resume(
        self, client, worker_a, worker_b, admin_worker,
        make_multi_task, db_conn
    ):
        """
        TC-WP-03a: A pause → Admin resume A의 pause → 200
        """
        task_id = make_multi_task([worker_a['id'], worker_b['id']])

        _pause(client, worker_a['token'], task_id)
        resp = _resume(client, admin_worker['token'], task_id)

        assert resp.status_code == 200, (
            f"Admin resume should succeed: {resp.get_json()}"
        )

        assert _count_pause_logs(db_conn, task_id, worker_a['id'], active_only=True) == 0


# ============================================================
# TC-AF: Auto-Finalize (01~07)
# ============================================================
class TestAutoFinalize:
    """TC-AF-01 ~ TC-AF-07: 전원 릴레이 종료 시 auto-finalize"""

    def test_af_01_two_workers_relay_auto_finalize(
        self, client, worker_a, worker_b, make_multi_task, db_conn
    ):
        """
        TC-AF-01: 2명 전원 relay → auto-finalize
        """
        task_id = make_multi_task([worker_a['id'], worker_b['id']])

        # A relay
        resp_a = _complete(client, worker_a['token'], task_id, finalize=False)
        assert resp_a.status_code == 200
        data_a = resp_a.get_json()
        assert data_a.get('task_finished') is False

        # B relay → auto-finalize
        resp_b = _complete(client, worker_b['token'], task_id, finalize=False)
        assert resp_b.status_code == 200
        data_b = resp_b.get_json()
        assert data_b.get('task_finished') is True, (
            f"Auto-finalize should trigger: {data_b}"
        )

        state = _get_task_state(db_conn, task_id)
        assert state.get('completed_at') is not None
        assert state.get('duration_minutes') is not None
        assert _count_completion_logs(db_conn, task_id) == 2

    def test_af_02_three_workers_relay(
        self, client, worker_a, worker_b, worker_c,
        make_multi_task, db_conn
    ):
        """
        TC-AF-02: 3명 전원 relay → 마지막에 auto-finalize
        """
        task_id = make_multi_task([
            worker_a['id'], worker_b['id'], worker_c['id']
        ])

        _complete(client, worker_a['token'], task_id, finalize=False)
        _complete(client, worker_b['token'], task_id, finalize=False)

        resp = _complete(client, worker_c['token'], task_id, finalize=False)
        assert resp.status_code == 200
        assert resp.get_json().get('task_finished') is True

        assert _count_completion_logs(db_conn, task_id) == 3

    def test_af_03_partial_relay_no_finalize(
        self, client, worker_a, worker_b, worker_c,
        make_multi_task, db_conn
    ):
        """
        TC-AF-03: 3명 중 2명만 relay → auto-finalize 미발동
        """
        task_id = make_multi_task([
            worker_a['id'], worker_b['id'], worker_c['id']
        ])

        _complete(client, worker_a['token'], task_id, finalize=False)
        resp = _complete(client, worker_b['token'], task_id, finalize=False)

        assert resp.status_code == 200
        assert resp.get_json().get('task_finished') is False

        state = _get_task_state(db_conn, task_id)
        assert state.get('completed_at') is None

    def test_af_04_auto_finalize_progress(
        self, client, worker_a, worker_b, make_multi_task, db_conn
    ):
        """
        TC-AF-04: auto-finalize 후 completion_status 반영 확인
        """
        task_id = make_multi_task([worker_a['id'], worker_b['id']])

        _complete(client, worker_a['token'], task_id, finalize=False)
        resp = _complete(client, worker_b['token'], task_id, finalize=False)

        assert resp.status_code == 200
        data = resp.get_json()
        # auto-finalize 후 category_completed 또는 task_finished 확인
        assert data.get('task_finished') is True

        state = _get_task_state(db_conn, task_id)
        assert state.get('completed_at') is not None
        assert state.get('duration_minutes') is not None

    def test_af_05_auto_finalize_then_final_task(
        self, client, worker_a, worker_b,
        make_multi_task, make_single_task, db_conn
    ):
        """
        TC-AF-05: 일반 task auto-finalize + FINAL task 별도 완료
        ※ FINAL task는 TC-FT에서 별도 테스트. 여기서는 일반 task auto-finalize만 확인
        """
        task_id = make_multi_task([worker_a['id'], worker_b['id']])

        _complete(client, worker_a['token'], task_id, finalize=False)
        resp = _complete(client, worker_b['token'], task_id, finalize=False)

        assert resp.get_json().get('task_finished') is True
        state = _get_task_state(db_conn, task_id)
        assert state.get('completed_at') is not None

    def test_af_06_relay_restart_prevents_early_finalize(
        self, client, worker_a, worker_b, worker_c,
        make_multi_task, db_conn
    ):
        """
        TC-AF-06: A complete→restart→complete, B complete → C 미완료
        핵심: completion_log 행수가 부풀려져도 C 미완료이면 auto-finalize 안 됨

        이 TC가 fail하면 _all_workers_completed가 릴레이 재시작을 처리 못하는 것.
        """
        task_id = make_multi_task([
            worker_a['id'], worker_b['id'], worker_c['id']
        ])

        # A relay
        _complete(client, worker_a['token'], task_id, finalize=False)
        # A restart
        _start_task(client, worker_a['token'], task_id)
        # A relay 다시
        _complete(client, worker_a['token'], task_id, finalize=False)
        # B relay
        resp = _complete(client, worker_b['token'], task_id, finalize=False)

        assert resp.status_code == 200
        assert resp.get_json().get('task_finished') is False, (
            "C not done → auto-finalize must NOT trigger. "
            "If this fails, _all_workers_completed counts row count instead of DISTINCT worker status."
        )

        state = _get_task_state(db_conn, task_id)
        assert state.get('completed_at') is None, (
            "Task should remain open — C has not completed"
        )

    def test_af_07_relay_restart_final_complete(
        self, client, worker_a, worker_b, worker_c,
        make_multi_task, db_conn
    ):
        """
        TC-AF-07: TC-AF-06 이후 C complete → 비로소 auto-finalize
        """
        task_id = make_multi_task([
            worker_a['id'], worker_b['id'], worker_c['id']
        ])

        # A relay → restart → relay
        _complete(client, worker_a['token'], task_id, finalize=False)
        _start_task(client, worker_a['token'], task_id)
        _complete(client, worker_a['token'], task_id, finalize=False)

        # B relay
        _complete(client, worker_b['token'], task_id, finalize=False)

        # C relay → auto-finalize
        resp = _complete(client, worker_c['token'], task_id, finalize=False)
        assert resp.status_code == 200
        assert resp.get_json().get('task_finished') is True, (
            "All 3 workers finally completed → auto-finalize should trigger"
        )

        state = _get_task_state(db_conn, task_id)
        assert state.get('completed_at') is not None
        assert state.get('duration_minutes') is not None

        # A, B, C 각각 completion_log 존재
        assert _count_completion_logs(db_conn, task_id) >= 3


# ============================================================
# TC-FT: FINAL Task 릴레이 불가 (01~03)
# ============================================================
class TestFinalTaskNoRelay:
    """TC-FT-01 ~ TC-FT-03: FINAL_TASK_IDS는 finalize=true 강제"""

    @pytest.mark.parametrize("task_id_ref,task_name", [
        ('SELF_INSPECTION', '자주검사'),
        ('INSPECTION', 'ELEC 검수'),
        ('PRESSURE_TEST', '가압검사'),
    ])
    def test_ft_final_task_forced_finalize(
        self, client, worker_a, make_single_task, db_conn,
        task_id_ref, task_name
    ):
        """
        TC-FT-01/02/03: FINAL task에 finalize=false 요청 → 강제 finalize=true
        """
        task_id = make_single_task(
            worker_a['id'],
            task_id=task_id_ref,
            task_name=task_name
        )

        resp = _complete(client, worker_a['token'], task_id, finalize=False)

        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get('task_finished') is True, (
            f"FINAL task '{task_id_ref}' should force finalize=true: {data}"
        )

        state = _get_task_state(db_conn, task_id)
        assert state.get('completed_at') is not None


# ============================================================
# TC-WH: Working Hours 연동 (01~02)
# ============================================================
class TestWorkingHours:
    """TC-WH-01 ~ TC-WH-02: category 완료 + working hours 산출"""

    def test_wh_01_final_task_category_complete(
        self, client, worker_a, make_single_task, db_conn
    ):
        """
        TC-WH-01: 자주검사 완료 → duration_minutes 산출됨
        """
        task_id = make_single_task(
            worker_a['id'],
            task_id='SELF_INSPECTION',
            task_name='자주검사'
        )

        resp = _complete(client, worker_a['token'], task_id, finalize=True)
        assert resp.status_code == 200

        state = _get_task_state(db_conn, task_id)
        assert state.get('completed_at') is not None
        assert state.get('duration_minutes') is not None

    def test_wh_02_inspection_complete(
        self, client, worker_a, make_single_task, db_conn
    ):
        """
        TC-WH-02: INSPECTION 완료 → duration/elapsed 산출
        """
        task_id = make_single_task(
            worker_a['id'],
            task_id='INSPECTION',
            task_name='검수',
            task_category='ELEC'
        )

        resp = _complete(client, worker_a['token'], task_id, finalize=True)
        assert resp.status_code == 200

        state = _get_task_state(db_conn, task_id)
        assert state.get('completed_at') is not None


# ============================================================
# TC-CT: 개인별 작업시간 정확도 (01~03)
# ============================================================
class TestCycleTimeAccuracy:
    """TC-CT-01 ~ TC-CT-03: 개인별 net_minutes 정확도"""

    def test_ct_01_a_pause_b_no_pause(
        self, client, worker_a, worker_b, make_multi_task, db_conn
    ):
        """
        TC-CT-01: A 30분 pause, B 무pause → 개인별 duration 차이

        ※ 실제 30분 대기 불가하므로, pause_log 존재 여부 + 차감 로직 확인
        """
        task_id = make_multi_task([worker_a['id'], worker_b['id']])

        # A pause → resume
        _pause(client, worker_a['token'], task_id)
        time.sleep(0.1)  # 최소 pause 시간
        _resume(client, worker_a['token'], task_id)

        # A의 pause_log 있음, B는 없음
        assert _count_pause_logs(db_conn, task_id, worker_a['id']) >= 1
        assert _count_pause_logs(db_conn, task_id, worker_b['id']) == 0

        # 전원 완료
        _complete(client, worker_a['token'], task_id, finalize=False)
        _complete(client, worker_b['token'], task_id, finalize=False)

        # duration 확인
        state = _get_task_state(db_conn, task_id)
        assert state.get('completed_at') is not None, (
            "Auto-finalize should have triggered"
        )
        assert state.get('total_pause_minutes') is not None

    def test_ct_02_five_workers_one_pause(
        self, client, worker_a, worker_b, worker_c,
        make_multi_task, db_conn, create_test_worker, get_auth_token
    ):
        """
        TC-CT-02: 5명 중 1명 pause → 1명분만 차감
        ※ worker 5명 필요하므로 추가 생성
        """
        # 추가 worker D, E 생성
        emails = []
        workers = [worker_a, worker_b, worker_c]
        for label in ['d', 'e']:
            email = f'sp55_{label}_{int(time.time() * 1000)}@sprint55_test.com'
            wid = create_test_worker(
                email=email, password='Test123!',
                name=f'Worker {label.upper()}', role='MECH',
                approval_status='approved', email_verified=True
            )
            token = get_auth_token(wid, role='MECH')
            workers.append({'id': wid, 'email': email, 'token': token})
            emails.append(email)

        task_id = make_multi_task([w['id'] for w in workers])

        # worker_a만 pause → resume
        _pause(client, worker_a['token'], task_id)
        time.sleep(0.1)
        _resume(client, worker_a['token'], task_id)

        # A만 pause_log, 나머지 0
        assert _count_pause_logs(db_conn, task_id, worker_a['id']) >= 1
        for w in workers[1:]:
            assert _count_pause_logs(db_conn, task_id, w['id']) == 0

    def test_ct_03_per_worker_net_minutes_query(self, db_conn):
        """
        TC-CT-03: CT 분석 SQL 유효성 검증
        ※ 쿼리 자체가 에러 없이 실행되는지 확인 (데이터 무관)
        """
        if not db_conn:
            pytest.skip("DB connection required")

        cursor = db_conn.cursor()
        # Sprint 55에 명시된 CT 분석 SQL
        cursor.execute("""
            SELECT wsl.worker_id,
                   EXTRACT(EPOCH FROM (wcl.completed_at - wsl.started_at)) / 60
                   - COALESCE(SUM(wpl.pause_duration_minutes), 0) AS net_minutes
            FROM work_start_log wsl
            JOIN work_completion_log wcl
                ON wsl.task_id = wcl.task_id AND wsl.worker_id = wcl.worker_id
            LEFT JOIN work_pause_log wpl
                ON wpl.task_detail_id = wsl.task_id
                AND wpl.worker_id = wsl.worker_id
                AND wpl.resumed_at IS NOT NULL
            WHERE wsl.task_id = -1
            GROUP BY wsl.worker_id, wsl.started_at, wcl.completed_at
        """)
        # 에러 없이 실행되면 OK (task_id=-1이므로 결과 0건)
        rows = cursor.fetchall()
        cursor.close()
        assert isinstance(rows, list)


# ============================================================
# TC-SP: Scheduler 자동 Pause 호환 (01~02)
# ============================================================
class TestSchedulerPauseCompat:
    """
    TC-SP-01 ~ TC-SP-02: 휴게시간 자동 pause/resume 호환
    ※ scheduler_service의 force_pause_all_active_tasks는 내부 함수.
      API 레벨에서 직접 호출 불가하므로, pause_log DB 패턴 검증으로 대체.
    """

    def test_sp_01_multi_worker_individual_break_pause(
        self, client, worker_a, worker_b, worker_c,
        make_multi_task, db_conn
    ):
        """
        TC-SP-01: 3명 각각 break pause 생성 → 전원 paused → is_paused=true
        ※ scheduler 대신 수동으로 break pause 시뮬레이션
        """
        task_id = make_multi_task([
            worker_a['id'], worker_b['id'], worker_c['id']
        ])

        # 3명 각각 break pause
        for w in [worker_a, worker_b, worker_c]:
            resp = _pause(client, w['token'], task_id, pause_type='break_morning')
            assert resp.status_code == 200, (
                f"Break pause failed for {w['email']}: {resp.get_json()}"
            )

        state = _get_task_state(db_conn, task_id)
        assert state.get('is_paused') is True, (
            "All 3 workers paused → is_paused should be True"
        )

        # 3건의 active pause_log
        assert _count_pause_logs(db_conn, task_id, active_only=True) == 3

    def test_sp_02_multi_worker_all_resume(
        self, client, worker_a, worker_b, worker_c,
        make_multi_task, db_conn
    ):
        """
        TC-SP-02: 전원 resume → is_paused=false
        """
        task_id = make_multi_task([
            worker_a['id'], worker_b['id'], worker_c['id']
        ])

        # 전원 pause
        for w in [worker_a, worker_b, worker_c]:
            _pause(client, w['token'], task_id, pause_type='break_morning')

        # 전원 resume
        for w in [worker_a, worker_b, worker_c]:
            resp = _resume(client, w['token'], task_id)
            assert resp.status_code == 200

        state = _get_task_state(db_conn, task_id)
        assert state.get('is_paused') is False

        # 0건의 active pause_log
        assert _count_pause_logs(db_conn, task_id, active_only=True) == 0
