"""
Sprint 55-B: Task 목록 API에 my_pause_status 반환 검증
화면 재진입 시 일시정지 상태가 소실되는 버그 수정 테스트

TC-55B-01: 일시정지 → task 목록 재조회 → my_pause_status='paused'
TC-55B-02: 일시정지 → QR 재스캔(제품조회) → my_pause_status='paused' 유지
TC-55B-03: task A 일시정지 + task B 진행 중 → A만 paused, B는 working
TC-55B-04: 일시정지 안 한 상태 → my_pause_status='working' (기본값)
TC-55B-05: 일시정지 → 재개 → task 목록 재조회 → my_pause_status='working'
"""

import sys
from pathlib import Path
_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest


def _start_task(client, token, qr_doc_id, category, task_id):
    return client.post('/api/app/work/start', json={
        'qr_doc_id': qr_doc_id,
        'task_category': category,
        'task_id': task_id,
    }, headers={'Authorization': f'Bearer {token}'})


def _get_task_detail_id(db_conn, serial_number, task_id):
    cur = db_conn.cursor()
    cur.execute(
        "SELECT id FROM app_task_details WHERE serial_number = %s AND task_id = %s",
        (serial_number, task_id)
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        return None
    return row[0] if isinstance(row, tuple) else row['id']


def _pause_task(client, token, task_detail_id):
    return client.post('/api/app/work/pause', json={
        'task_detail_id': task_detail_id,
    }, headers={'Authorization': f'Bearer {token}'})


def _resume_task(client, token, task_detail_id):
    return client.post('/api/app/work/resume', json={
        'task_detail_id': task_detail_id,
    }, headers={'Authorization': f'Bearer {token}'})


def _get_tasks_by_sn(client, token, serial_number):
    """화면 재진입 시 호출되는 task 목록 API"""
    return client.get(
        f'/api/app/tasks/{serial_number}',
        headers={'Authorization': f'Bearer {token}'}
    )


@pytest.fixture
def setup_55b(db_conn, seed_test_data, create_test_worker, get_auth_token,
              create_test_product, client):
    """Sprint 55-B 테스트 공통 셋업"""
    sn = 'SN-55B-TEST-01'
    qr = f'DOC_{sn}'

    worker_id = create_test_worker(
        email='s55b_worker@test.axisos.com',
        password='Test1234!', name='55B Worker',
        role='MECH', company='FNI'
    )
    token = get_auth_token(worker_id, role='MECH')

    create_test_product(serial_number=sn, qr_doc_id=qr, model='GAIA-I')

    # task seed
    cur = db_conn.cursor()
    for tid, tname in [('TANK_DOCKING', 'Tank Docking'), ('SELF_INSPECTION', 'Self Inspection')]:
        cur.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, worker_id)
            VALUES (%s, %s, 'MECH', %s, %s, TRUE, %s)
            ON CONFLICT (serial_number, qr_doc_id, task_category, task_id) DO NOTHING
        """, (sn, qr, tid, tname, worker_id))
    db_conn.commit()
    cur.close()

    yield {
        'sn': sn, 'qr': qr,
        'worker_id': worker_id, 'token': token,
        'client': client, 'db_conn': db_conn,
    }

    # cleanup
    cur = db_conn.cursor()
    try:
        cur.execute("DELETE FROM work_pause_log WHERE task_id IN "
                    "(SELECT id FROM app_task_details WHERE serial_number = %s)", (sn,))
        cur.execute("DELETE FROM work_completion_log WHERE task_id IN "
                    "(SELECT id FROM app_task_details WHERE serial_number = %s)", (sn,))
        cur.execute("DELETE FROM work_start_log WHERE task_id IN "
                    "(SELECT id FROM app_task_details WHERE serial_number = %s)", (sn,))
        cur.execute("DELETE FROM app_alert_logs WHERE serial_number = %s", (sn,))
        cur.execute("DELETE FROM app_task_details WHERE serial_number = %s", (sn,))
        db_conn.commit()
    except Exception:
        db_conn.rollback()
    finally:
        cur.close()


class TestTaskListPauseStatus:
    """Sprint 55-B: GET /api/app/tasks/{sn} 에 my_pause_status 반환 검증"""

    def test_55b_01_pause_then_reload_shows_paused(self, setup_55b):
        """TC-55B-01: 일시정지 → task 목록 재조회 → my_pause_status='paused'"""
        ctx = setup_55b
        client, token, sn, qr = ctx['client'], ctx['token'], ctx['sn'], ctx['qr']

        # 작업 시작
        resp = _start_task(client, token, qr, 'MECH', 'TANK_DOCKING')
        assert resp.status_code == 200, f"start failed: {resp.get_json()}"

        # task_detail_id 조회
        tid = _get_task_detail_id(ctx['db_conn'], sn, 'TANK_DOCKING')
        assert tid is not None

        # 일시정지
        resp = _pause_task(client, token, tid)
        assert resp.status_code == 200, f"pause failed: {resp.get_json()}"

        # 화면 재진입 (task 목록 API 호출)
        resp = _get_tasks_by_sn(client, token, sn)
        assert resp.status_code == 200

        tasks = resp.get_json()
        paused_task = next((t for t in tasks if t.get('task_id') == 'TANK_DOCKING'), None)
        assert paused_task is not None, "TANK_DOCKING task not found in response"
        assert paused_task.get('my_pause_status') == 'paused', (
            f"화면 재진입 시 my_pause_status가 'paused'여야 합니다. "
            f"got: {paused_task.get('my_pause_status')}"
        )

    def test_55b_02_pause_then_qr_rescan_shows_paused(self, setup_55b):
        """TC-55B-02: 일시정지 → QR 재스캔 → my_pause_status='paused' 유지"""
        ctx = setup_55b
        client, token, sn, qr = ctx['client'], ctx['token'], ctx['sn'], ctx['qr']

        resp = _start_task(client, token, qr, 'MECH', 'TANK_DOCKING')
        assert resp.status_code == 200

        tid = _get_task_detail_id(ctx['db_conn'], sn, 'TANK_DOCKING')
        _pause_task(client, token, tid)

        # QR 재스캔 = task 목록 재조회
        resp = _get_tasks_by_sn(client, token, sn)
        assert resp.status_code == 200

        tasks = resp.get_json()
        paused_task = next((t for t in tasks if t.get('task_id') == 'TANK_DOCKING'), None)
        assert paused_task.get('my_pause_status') == 'paused'

    def test_55b_03_mixed_pause_and_working(self, setup_55b):
        """TC-55B-03: task A 일시정지 + task B 진행 중 → A만 paused, B는 working"""
        ctx = setup_55b
        client, token, sn, qr = ctx['client'], ctx['token'], ctx['sn'], ctx['qr']

        # task A (TANK_DOCKING) 시작 + 일시정지
        resp = _start_task(client, token, qr, 'MECH', 'TANK_DOCKING')
        assert resp.status_code == 200
        tid_a = _get_task_detail_id(ctx['db_conn'], sn, 'TANK_DOCKING')
        _pause_task(client, token, tid_a)

        # task B (SELF_INSPECTION) 시작 (일시정지 안 함)
        resp = _start_task(client, token, qr, 'MECH', 'SELF_INSPECTION')
        assert resp.status_code == 200

        # 화면 재진입
        resp = _get_tasks_by_sn(client, token, sn)
        assert resp.status_code == 200

        tasks = resp.get_json()
        task_a = next((t for t in tasks if t.get('task_id') == 'TANK_DOCKING'), None)
        task_b = next((t for t in tasks if t.get('task_id') == 'SELF_INSPECTION'), None)

        assert task_a.get('my_pause_status') == 'paused', \
            f"task A should be paused, got: {task_a.get('my_pause_status')}"
        assert task_b.get('my_pause_status') == 'working', \
            f"task B should be working, got: {task_b.get('my_pause_status')}"

    def test_55b_04_no_pause_shows_working(self, setup_55b):
        """TC-55B-04: 일시정지 안 한 상태 → my_pause_status='working'"""
        ctx = setup_55b
        client, token, sn, qr = ctx['client'], ctx['token'], ctx['sn'], ctx['qr']

        # 작업 시작만 (일시정지 안 함)
        resp = _start_task(client, token, qr, 'MECH', 'TANK_DOCKING')
        assert resp.status_code == 200

        resp = _get_tasks_by_sn(client, token, sn)
        assert resp.status_code == 200

        tasks = resp.get_json()
        task = next((t for t in tasks if t.get('task_id') == 'TANK_DOCKING'), None)
        assert task.get('my_pause_status') == 'working', \
            f"일시정지 안 했으면 working이어야 합니다. got: {task.get('my_pause_status')}"

    def test_55b_05_pause_resume_then_reload_shows_working(self, setup_55b):
        """TC-55B-05: 일시정지 → 재개 → 재진입 → my_pause_status='working'"""
        ctx = setup_55b
        client, token, sn, qr = ctx['client'], ctx['token'], ctx['sn'], ctx['qr']

        resp = _start_task(client, token, qr, 'MECH', 'TANK_DOCKING')
        assert resp.status_code == 200

        tid = _get_task_detail_id(ctx['db_conn'], sn, 'TANK_DOCKING')

        # 일시정지
        resp = _pause_task(client, token, tid)
        assert resp.status_code == 200

        # 재개
        resp = _resume_task(client, token, tid)
        assert resp.status_code == 200

        # 화면 재진입
        resp = _get_tasks_by_sn(client, token, sn)
        assert resp.status_code == 200

        tasks = resp.get_json()
        task = next((t for t in tasks if t.get('task_id') == 'TANK_DOCKING'), None)
        assert task.get('my_pause_status') == 'working', \
            f"재개 후에는 working이어야 합니다. got: {task.get('my_pause_status')}"
