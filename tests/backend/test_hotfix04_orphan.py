"""
HOTFIX-04: Orphan work_start_log + 미시작 강제종료 표시 검증
- Case 1 (Orphan): wsl 있음 + wcl 없음 + task.completed_at 세팅 → status='completed' + is_orphan=true
- Case 2 (NS 강제종료): wsl 자체 없음 + force_closed=true → close_reason/closed_by_name 노출

API: GET /api/app/tasks/{serial_number}
"""
import pytest
from datetime import datetime, timedelta, timezone


@pytest.fixture(autouse=True)
def cleanup_hotfix04(db_conn):
    yield
    if db_conn and not db_conn.closed:
        try:
            cur = db_conn.cursor()
            cur.execute("DELETE FROM work_completion_log WHERE serial_number LIKE 'SN-H04-%%'")
            cur.execute("DELETE FROM work_start_log       WHERE serial_number LIKE 'SN-H04-%%'")
            cur.execute("DELETE FROM app_task_details     WHERE serial_number LIKE 'SN-H04-%%'")
            cur.execute("DELETE FROM completion_status    WHERE serial_number LIKE 'SN-H04-%%'")
            cur.execute("DELETE FROM public.qr_registry   WHERE qr_doc_id LIKE 'DOC-H04-%%'")
            cur.execute("DELETE FROM plan.product_info    WHERE serial_number LIKE 'SN-H04-%%'")
            db_conn.commit()
            cur.close()
        except Exception:
            pass


def _find_worker_entry(workers, worker_id):
    for w in workers:
        if w.get('worker_id') == worker_id:
            return w
    return None


def _find_task(tasks, task_id):
    for t in tasks:
        if t.get('id') == task_id:
            return t
    return None


class TestOrphanCase1:
    """Case 1: Orphan work_start_log → status='completed' + is_orphan=true"""

    def test_tc_orphan_01_task_closed_without_wcl(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """TC-ORPHAN-01: task.completed_at 세팅 + wcl 없음 → status='completed', is_orphan=true, duration_minutes IS NULL"""
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        import time
        suffix = int(time.time() * 1000)

        worker_id = create_test_worker(
            email=f'h04_w01_{suffix}@test.com', password='Test123!',
            name='H04 Worker 01', role='MECH', company='FNI'
        )
        admin_id = create_test_worker(
            email=f'h04_admin_{suffix}@test.com', password='Test123!',
            name='김관리', role='ADMIN', company='GST', is_admin=True
        )

        qr_doc_id = f'DOC-H04-01-{suffix}'
        serial_number = f'SN-H04-01-{suffix}'
        create_test_product(qr_doc_id=qr_doc_id, serial_number=serial_number, model='GALLANT-50')
        create_test_completion_status(serial_number=serial_number)

        started_at = datetime.now(timezone.utc) - timedelta(hours=5)
        task_closed_at = datetime.now(timezone.utc) - timedelta(hours=1)

        cur = db_conn.cursor()
        cur.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, started_at, completed_at, force_closed, closed_by, close_reason)
            VALUES (%s, %s, 'MECH', 'SELF_INSPECTION', '자주검사',
                    TRUE, %s, %s, TRUE, %s, '관리자 강제종료')
            RETURNING id
        """, (serial_number, qr_doc_id, started_at, task_closed_at, admin_id))
        task_db_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO work_start_log
                (task_id, worker_id, serial_number, qr_doc_id, task_category, task_id_ref, task_name, started_at)
            VALUES (%s, %s, %s, %s, 'MECH', 'SELF_INSPECTION', '자주검사', %s)
        """, (task_db_id, worker_id, serial_number, qr_doc_id, started_at))
        db_conn.commit()
        cur.close()

        token = get_auth_token(worker_id, role='MECH')
        resp = client.get(
            f'/api/app/tasks/{serial_number}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200, resp.get_json()
        tasks = resp.get_json()  # BE L727: jsonify(task_list) — list 직접 반환

        task = _find_task(tasks, task_db_id)
        assert task is not None, "task row not returned"
        workers = task.get('workers') or []
        w = _find_worker_entry(workers, worker_id)
        assert w is not None, f"worker entry missing: workers={workers}"
        assert w['status'] == 'completed', f"expected status='completed', got {w['status']}"
        assert w['is_orphan'] is True, f"expected is_orphan=true, got {w['is_orphan']}"
        assert w['duration_minutes'] is None, f"orphan duration must be NULL, got {w['duration_minutes']}"
        assert w['completed_at'] is not None, "completed_at should be populated from task_closed_at"
        assert w['task_closed_at'] is not None

    def test_tc_orphan_02_wcl_takes_priority(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """TC-ORPHAN-02: wcl 있음 + task.completed_at 있음 → wcl.completed_at 우선, is_orphan=false"""
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        import time
        suffix = int(time.time() * 1000) + 2

        worker_id = create_test_worker(
            email=f'h04_w02_{suffix}@test.com', password='Test123!',
            name='H04 Worker 02', role='MECH', company='FNI'
        )

        qr_doc_id = f'DOC-H04-02-{suffix}'
        serial_number = f'SN-H04-02-{suffix}'
        create_test_product(qr_doc_id=qr_doc_id, serial_number=serial_number, model='GALLANT-50')
        create_test_completion_status(serial_number=serial_number)

        started_at = datetime.now(timezone.utc) - timedelta(hours=5)
        wcl_completed_at = datetime.now(timezone.utc) - timedelta(hours=2)
        task_completed_at = datetime.now(timezone.utc) - timedelta(hours=1)

        cur = db_conn.cursor()
        cur.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, started_at, completed_at)
            VALUES (%s, %s, 'MECH', 'SELF_INSPECTION', '자주검사',
                    TRUE, %s, %s)
            RETURNING id
        """, (serial_number, qr_doc_id, started_at, task_completed_at))
        task_db_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO work_start_log
                (task_id, worker_id, serial_number, qr_doc_id, task_category, task_id_ref, task_name, started_at)
            VALUES (%s, %s, %s, %s, 'MECH', 'SELF_INSPECTION', '자주검사', %s)
        """, (task_db_id, worker_id, serial_number, qr_doc_id, started_at))
        cur.execute("""
            INSERT INTO work_completion_log
                (task_id, worker_id, serial_number, qr_doc_id, task_category, task_id_ref, task_name,
                 completed_at, duration_minutes)
            VALUES (%s, %s, %s, %s, 'MECH', 'SELF_INSPECTION', '자주검사', %s, 180)
        """, (task_db_id, worker_id, serial_number, qr_doc_id, wcl_completed_at))
        db_conn.commit()
        cur.close()

        token = get_auth_token(worker_id, role='MECH')
        resp = client.get(
            f'/api/app/tasks/{serial_number}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        tasks = resp.get_json()  # BE L727: jsonify(task_list) — list 직접 반환

        task = _find_task(tasks, task_db_id)
        w = _find_worker_entry(task.get('workers') or [], worker_id)
        assert w is not None
        assert w['status'] == 'completed'
        assert w['is_orphan'] is False
        assert w['duration_minutes'] == 180, f"wcl.duration_minutes should be returned, got {w['duration_minutes']}"
        # completed_at은 wcl.completed_at(실제 worker 종료 시각)이 우선
        assert w['completed_at'] is not None

    def test_tc_orphan_03_in_progress_stays_normal(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """TC-ORPHAN-03: wcl 없음 + task.completed_at NULL → status='in_progress', is_orphan=false"""
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        import time
        suffix = int(time.time() * 1000) + 3

        worker_id = create_test_worker(
            email=f'h04_w03_{suffix}@test.com', password='Test123!',
            name='H04 Worker 03', role='MECH', company='FNI'
        )

        qr_doc_id = f'DOC-H04-03-{suffix}'
        serial_number = f'SN-H04-03-{suffix}'
        create_test_product(qr_doc_id=qr_doc_id, serial_number=serial_number, model='GALLANT-50')
        create_test_completion_status(serial_number=serial_number)

        started_at = datetime.now(timezone.utc) - timedelta(hours=1)

        cur = db_conn.cursor()
        cur.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, started_at)
            VALUES (%s, %s, 'MECH', 'SELF_INSPECTION', '자주검사', TRUE, %s)
            RETURNING id
        """, (serial_number, qr_doc_id, started_at))
        task_db_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO work_start_log
                (task_id, worker_id, serial_number, qr_doc_id, task_category, task_id_ref, task_name, started_at)
            VALUES (%s, %s, %s, %s, 'MECH', 'SELF_INSPECTION', '자주검사', %s)
        """, (task_db_id, worker_id, serial_number, qr_doc_id, started_at))
        db_conn.commit()
        cur.close()

        token = get_auth_token(worker_id, role='MECH')
        resp = client.get(
            f'/api/app/tasks/{serial_number}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        tasks = resp.get_json()  # BE L727: jsonify(task_list) — list 직접 반환

        task = _find_task(tasks, task_db_id)
        w = _find_worker_entry(task.get('workers') or [], worker_id)
        assert w is not None
        assert w['status'] == 'in_progress'
        assert w['is_orphan'] is False
        assert w['task_closed_at'] is None

    def test_tc_orphan_04_mixed_workers(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """TC-ORPHAN-04: 복수 worker 중 일부만 wcl 존재 + task.completed_at 세팅 → row별 독립 판정"""
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        import time
        suffix = int(time.time() * 1000) + 4

        w1_id = create_test_worker(
            email=f'h04_w04a_{suffix}@test.com', password='Test123!',
            name='H04 W4A', role='MECH', company='FNI'
        )
        w2_id = create_test_worker(
            email=f'h04_w04b_{suffix}@test.com', password='Test123!',
            name='H04 W4B', role='MECH', company='FNI'
        )

        qr_doc_id = f'DOC-H04-04-{suffix}'
        serial_number = f'SN-H04-04-{suffix}'
        create_test_product(qr_doc_id=qr_doc_id, serial_number=serial_number, model='GALLANT-50')
        create_test_completion_status(serial_number=serial_number)

        started_at = datetime.now(timezone.utc) - timedelta(hours=5)
        w1_completed_at = datetime.now(timezone.utc) - timedelta(hours=2)
        task_completed_at = datetime.now(timezone.utc) - timedelta(hours=1)

        cur = db_conn.cursor()
        cur.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, started_at, completed_at)
            VALUES (%s, %s, 'MECH', 'SELF_INSPECTION', '자주검사', TRUE, %s, %s)
            RETURNING id
        """, (serial_number, qr_doc_id, started_at, task_completed_at))
        task_db_id = cur.fetchone()[0]

        # W1: wsl + wcl (정상 완료)
        cur.execute("""
            INSERT INTO work_start_log
                (task_id, worker_id, serial_number, qr_doc_id, task_category, task_id_ref, task_name, started_at)
            VALUES (%s, %s, %s, %s, 'MECH', 'SELF_INSPECTION', '자주검사', %s)
        """, (task_db_id, w1_id, serial_number, qr_doc_id, started_at))
        cur.execute("""
            INSERT INTO work_completion_log
                (task_id, worker_id, serial_number, qr_doc_id, task_category, task_id_ref, task_name,
                 completed_at, duration_minutes)
            VALUES (%s, %s, %s, %s, 'MECH', 'SELF_INSPECTION', '자주검사', %s, 120)
        """, (task_db_id, w1_id, serial_number, qr_doc_id, w1_completed_at))

        # W2: wsl만 (orphan)
        cur.execute("""
            INSERT INTO work_start_log
                (task_id, worker_id, serial_number, qr_doc_id, task_category, task_id_ref, task_name, started_at)
            VALUES (%s, %s, %s, %s, 'MECH', 'SELF_INSPECTION', '자주검사', %s)
        """, (task_db_id, w2_id, serial_number, qr_doc_id, started_at))
        db_conn.commit()
        cur.close()

        token = get_auth_token(w1_id, role='MECH')
        resp = client.get(
            f'/api/app/tasks/{serial_number}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        tasks = resp.get_json()  # BE L727: jsonify(task_list) — list 직접 반환

        task = _find_task(tasks, task_db_id)
        workers = task.get('workers') or []
        w1 = _find_worker_entry(workers, w1_id)
        w2 = _find_worker_entry(workers, w2_id)

        assert w1 is not None and w2 is not None
        # W1 정상 완료
        assert w1['status'] == 'completed'
        assert w1['is_orphan'] is False
        assert w1['duration_minutes'] == 120
        # W2 orphan
        assert w2['status'] == 'completed'
        assert w2['is_orphan'] is True
        assert w2['duration_minutes'] is None  # M1 미반영 — garbage 방지


class TestForceCloseNoStart:
    """Case 2: wsl 자체 없는 task 강제종료 시 close_reason/closed_by_name 응답 노출"""

    def test_tc_forceclose_ns_01_metadata_exposed(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """TC-FORCECLOSE-NS-01: wsl 없음 + force_closed=true → close_reason/closed_by_name 응답 포함"""
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        import time
        suffix = int(time.time() * 1000) + 5

        admin_id = create_test_worker(
            email=f'h04_adm_ns_{suffix}@test.com', password='Test123!',
            name='김관리', role='ADMIN', company='GST', is_admin=True
        )
        viewer_id = create_test_worker(
            email=f'h04_view_{suffix}@test.com', password='Test123!',
            name='H04 Viewer', role='MECH', company='FNI'
        )

        qr_doc_id = f'DOC-H04-NS-{suffix}'
        serial_number = f'SN-H04-NS-{suffix}'
        create_test_product(qr_doc_id=qr_doc_id, serial_number=serial_number, model='GAIA-100')
        create_test_completion_status(serial_number=serial_number)

        task_completed_at = datetime.now(timezone.utc) - timedelta(hours=1)

        cur = db_conn.cursor()
        cur.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, completed_at, force_closed, closed_by, close_reason)
            VALUES (%s, %s, 'TMS', 'PRESSURE_TEST', '가압검사',
                    TRUE, %s, TRUE, %s, '작성안함')
            RETURNING id
        """, (serial_number, qr_doc_id, task_completed_at, admin_id))
        task_db_id = cur.fetchone()[0]
        db_conn.commit()
        cur.close()

        token = get_auth_token(viewer_id, role='MECH')
        resp = client.get(
            f'/api/app/tasks/{serial_number}?all=true',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200, resp.get_json()
        tasks = resp.get_json()  # BE L727: jsonify(task_list) — list 직접 반환

        task = _find_task(tasks, task_db_id)
        assert task is not None, "force-closed task must be returned"
        assert task.get('force_closed') is True
        assert task.get('close_reason') == '작성안함'
        assert task.get('closed_by') == admin_id
        assert task.get('closed_by_name') == '김관리'
        # workers 배열은 빈 배열
        assert (task.get('workers') or []) == []

    def test_tc_forceclose_ns_02_completed_at_iso_kst(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """TC-FORCECLOSE-NS-02: task.completed_at이 ISO8601 형식으로 응답되는지"""
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        import time
        suffix = int(time.time() * 1000) + 6

        admin_id = create_test_worker(
            email=f'h04_adm2_{suffix}@test.com', password='Test123!',
            name='이관리', role='ADMIN', company='GST', is_admin=True
        )
        viewer_id = create_test_worker(
            email=f'h04_view2_{suffix}@test.com', password='Test123!',
            name='H04 Viewer2', role='MECH', company='FNI'
        )

        qr_doc_id = f'DOC-H04-NS2-{suffix}'
        serial_number = f'SN-H04-NS2-{suffix}'
        create_test_product(qr_doc_id=qr_doc_id, serial_number=serial_number, model='GAIA-100')
        create_test_completion_status(serial_number=serial_number)

        task_completed_at = datetime.now(timezone.utc) - timedelta(minutes=30)

        cur = db_conn.cursor()
        cur.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, completed_at, force_closed, closed_by, close_reason)
            VALUES (%s, %s, 'TMS', 'PRESSURE_TEST', '가압검사',
                    TRUE, %s, TRUE, %s, '관리자 강제종료')
            RETURNING id
        """, (serial_number, qr_doc_id, task_completed_at, admin_id))
        task_db_id = cur.fetchone()[0]
        db_conn.commit()
        cur.close()

        token = get_auth_token(viewer_id, role='MECH')
        resp = client.get(
            f'/api/app/tasks/{serial_number}?all=true',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        tasks = resp.get_json()  # BE L727: jsonify(task_list) — list 직접 반환

        task = _find_task(tasks, task_db_id)
        assert task is not None
        completed_str = task.get('completed_at')
        assert completed_str is not None
        # ISO8601 형식 확인 — fromisoformat 파싱 가능
        parsed = datetime.fromisoformat(completed_str)
        assert parsed is not None

    def test_tc_forceclose_ns_03_mixed_with_active_wsl(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """TC-FORCECLOSE-NS-03: 같은 S/N 안에 Case 2(wsl 없는 강제종료) + 정상 진행중 task 혼재 → 각 응답 독립"""
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        import time
        suffix = int(time.time() * 1000) + 7

        admin_id = create_test_worker(
            email=f'h04_adm3_{suffix}@test.com', password='Test123!',
            name='박관리', role='ADMIN', company='GST', is_admin=True
        )
        worker_id = create_test_worker(
            email=f'h04_w3_{suffix}@test.com', password='Test123!',
            name='H04 W3', role='MECH', company='FNI'
        )

        qr_doc_id = f'DOC-H04-NS3-{suffix}'
        serial_number = f'SN-H04-NS3-{suffix}'
        create_test_product(qr_doc_id=qr_doc_id, serial_number=serial_number, model='GAIA-100')
        create_test_completion_status(serial_number=serial_number)

        task_completed_at = datetime.now(timezone.utc) - timedelta(hours=1)
        started_at = datetime.now(timezone.utc) - timedelta(hours=2)

        cur = db_conn.cursor()
        # Task A: Case 2 (wsl 없음 + force_closed)
        cur.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, completed_at, force_closed, closed_by, close_reason)
            VALUES (%s, %s, 'TMS', 'PRESSURE_TEST', '가압검사',
                    TRUE, %s, TRUE, %s, '작성안함')
            RETURNING id
        """, (serial_number, qr_doc_id, task_completed_at, admin_id))
        task_a_id = cur.fetchone()[0]

        # Task B: 정상 진행중 (wsl 있음, force_closed=false)
        cur.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, started_at)
            VALUES (%s, %s, 'MECH', 'SELF_INSPECTION', '자주검사',
                    TRUE, %s)
            RETURNING id
        """, (serial_number, qr_doc_id, started_at))
        task_b_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO work_start_log
                (task_id, worker_id, serial_number, qr_doc_id, task_category, task_id_ref, task_name, started_at)
            VALUES (%s, %s, %s, %s, 'MECH', 'SELF_INSPECTION', '자주검사', %s)
        """, (task_b_id, worker_id, serial_number, qr_doc_id, started_at))
        db_conn.commit()
        cur.close()

        token = get_auth_token(worker_id, role='MECH')
        resp = client.get(
            f'/api/app/tasks/{serial_number}?all=true',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        tasks = resp.get_json()

        task_a = _find_task(tasks, task_a_id)
        task_b = _find_task(tasks, task_b_id)
        assert task_a is not None
        assert task_b is not None

        # Task A: Case 2 — force_closed, close_reason, closed_by_name 노출
        assert task_a['force_closed'] is True
        assert task_a['close_reason'] == '작성안함'
        assert task_a['closed_by_name'] == '박관리'
        assert (task_a.get('workers') or []) == []

        # Task B: 정상 진행중 — force_closed=false, close_reason/closed_by_name=None
        assert task_b['force_closed'] is False
        assert task_b['close_reason'] is None
        assert task_b['closed_by_name'] is None
        wb = _find_worker_entry(task_b.get('workers') or [], worker_id)
        assert wb is not None and wb['status'] == 'in_progress'

    def test_tc_forceclose_ns_04_legacy_backward_compat(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """TC-FORCECLOSE-NS-04: 일반 미시작 task (force_closed=false, closed_by=None) → closed_by_name=None backward-compat"""
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        import time
        suffix = int(time.time() * 1000) + 8

        viewer_id = create_test_worker(
            email=f'h04_w4_{suffix}@test.com', password='Test123!',
            name='H04 W4', role='MECH', company='FNI'
        )

        qr_doc_id = f'DOC-H04-NS4-{suffix}'
        serial_number = f'SN-H04-NS4-{suffix}'
        create_test_product(qr_doc_id=qr_doc_id, serial_number=serial_number, model='GAIA-100')
        create_test_completion_status(serial_number=serial_number)

        cur = db_conn.cursor()
        cur.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable)
            VALUES (%s, %s, 'MECH', 'SELF_INSPECTION', '자주검사', TRUE)
            RETURNING id
        """, (serial_number, qr_doc_id))
        task_db_id = cur.fetchone()[0]
        db_conn.commit()
        cur.close()

        token = get_auth_token(viewer_id, role='MECH')
        resp = client.get(
            f'/api/app/tasks/{serial_number}?all=true',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        tasks = resp.get_json()

        task = _find_task(tasks, task_db_id)
        assert task is not None
        assert task['force_closed'] is False
        assert task['closed_by'] is None
        assert task['closed_by_name'] is None  # LEFT JOIN 결과 자연 None
        assert task['close_reason'] is None

    def test_tc_forceclose_ns_05_case1_case2_combined(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """TC-FORCECLOSE-NS-05: force_closed=true + wsl 존재 (Case 1 중첩) → Case 1 로직 우선, closed_by_name도 노출"""
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        import time
        suffix = int(time.time() * 1000) + 9

        admin_id = create_test_worker(
            email=f'h04_adm5_{suffix}@test.com', password='Test123!',
            name='최관리', role='ADMIN', company='GST', is_admin=True
        )
        worker_id = create_test_worker(
            email=f'h04_w5_{suffix}@test.com', password='Test123!',
            name='H04 W5', role='MECH', company='FNI'
        )

        qr_doc_id = f'DOC-H04-NS5-{suffix}'
        serial_number = f'SN-H04-NS5-{suffix}'
        create_test_product(qr_doc_id=qr_doc_id, serial_number=serial_number, model='GAIA-100')
        create_test_completion_status(serial_number=serial_number)

        started_at = datetime.now(timezone.utc) - timedelta(hours=4)
        task_completed_at = datetime.now(timezone.utc) - timedelta(hours=1)

        cur = db_conn.cursor()
        cur.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, started_at, completed_at,
                 force_closed, closed_by, close_reason)
            VALUES (%s, %s, 'MECH', 'SELF_INSPECTION', '자주검사',
                    TRUE, %s, %s, TRUE, %s, '관리자 강제종료')
            RETURNING id
        """, (serial_number, qr_doc_id, started_at, task_completed_at, admin_id))
        task_db_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO work_start_log
                (task_id, worker_id, serial_number, qr_doc_id, task_category, task_id_ref, task_name, started_at)
            VALUES (%s, %s, %s, %s, 'MECH', 'SELF_INSPECTION', '자주검사', %s)
        """, (task_db_id, worker_id, serial_number, qr_doc_id, started_at))
        db_conn.commit()
        cur.close()

        token = get_auth_token(worker_id, role='MECH')
        resp = client.get(
            f'/api/app/tasks/{serial_number}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        tasks = resp.get_json()

        task = _find_task(tasks, task_db_id)
        assert task is not None
        # Case 2 메타데이터 노출
        assert task['force_closed'] is True
        assert task['close_reason'] == '관리자 강제종료'
        assert task['closed_by_name'] == '최관리'

        # Case 1 orphan 판정 (wsl 있음 + wcl 없음)
        w = _find_worker_entry(task.get('workers') or [], worker_id)
        assert w is not None
        assert w['status'] == 'completed'
        assert w['is_orphan'] is True
