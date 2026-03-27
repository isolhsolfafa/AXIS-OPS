"""
Issue #46: 상세뷰 workers 매핑 — task_id fallback 테스트
TC-46-01 ~ TC-46-05 (5건)

배경:
  상세뷰 API (GET /api/app/tasks/{sn}?all=true) workers 조회를
  task_id 단독 매핑 → serial_number 기준 + task_id/task_ref fallback 복합 매핑으로 변경.
  task seed 재실행으로 app_task_details.id가 변경되어도 작업자 누락 방지.

테스트 방식:
  - API 엔드포인트를 직접 호출 (client fixture)
  - DB에 app_task_details + work_start_log + work_completion_log 직접 삽입
  - fallback 케이스: work_start_log.task_id를 존재하지 않는 id로 강제 설정
"""

import sys
from pathlib import Path

_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest
import psycopg2
from datetime import datetime, timedelta, timezone

_PREFIX = 'ISS46-'


# ── 공통 헬퍼 ──────────────────────────────────────────────────

def _insert_product(db_conn, serial_number, mech_partner='FNI', elec_partner='P&S'):
    """plan.product_info + qr_registry + completion_status 삽입"""
    qr_doc_id = f'DOC_{serial_number}'
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO plan.product_info (serial_number, model, mech_partner, elec_partner, ship_plan_date)
        VALUES (%s, %s, %s, %s, '2099-12-31')
        ON CONFLICT (serial_number) DO NOTHING
    """, (serial_number, 'GALLANT-50', mech_partner, elec_partner))
    cursor.execute("""
        INSERT INTO qr_registry (qr_doc_id, serial_number, status)
        VALUES (%s, %s, 'active')
        ON CONFLICT (qr_doc_id) DO NOTHING
    """, (qr_doc_id, serial_number))
    cursor.execute("""
        INSERT INTO completion_status (serial_number)
        VALUES (%s)
        ON CONFLICT (serial_number) DO NOTHING
    """, (serial_number,))
    db_conn.commit()
    cursor.close()
    return qr_doc_id


def _insert_task_detail(db_conn, serial_number, qr_doc_id, worker_id,
                        category='ELEC', task_id='WIRING', task_name='배선 포설'):
    """app_task_details 레코드 삽입 → 반환: task_detail_id"""
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable)
        VALUES (%s, %s, %s, %s, %s, %s, true)
        ON CONFLICT (serial_number, qr_doc_id, task_category, task_id)
            DO UPDATE SET worker_id = EXCLUDED.worker_id
        RETURNING id
    """, (worker_id, serial_number, qr_doc_id, category, task_id, task_name))
    task_detail_id = cursor.fetchone()[0]
    db_conn.commit()
    cursor.close()
    return task_detail_id


def _insert_start_log(db_conn, task_detail_id, worker_id, serial_number, qr_doc_id,
                      started_at=None, category='ELEC', task_id_ref='WIRING',
                      task_name='배선 포설'):
    """work_start_log 삽입"""
    if started_at is None:
        started_at = datetime.now(timezone.utc) - timedelta(hours=1)
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO work_start_log
            (task_id, worker_id, serial_number, qr_doc_id, task_category,
             task_id_ref, task_name, started_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (task_detail_id, worker_id, serial_number, qr_doc_id,
          category, task_id_ref, task_name, started_at))
    log_id = cursor.fetchone()[0]
    db_conn.commit()
    cursor.close()
    return log_id


def _insert_completion_log(db_conn, task_detail_id, worker_id, serial_number, qr_doc_id,
                           started_at, completed_at=None, duration_minutes=60,
                           category='ELEC', task_id_ref='WIRING', task_name='배선 포설'):
    """work_completion_log 삽입"""
    if completed_at is None:
        completed_at = datetime.now(timezone.utc)
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO work_completion_log
            (task_id, worker_id, serial_number, qr_doc_id, task_category,
             task_id_ref, task_name, completed_at, duration_minutes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (task_detail_id, worker_id, serial_number, qr_doc_id,
          category, task_id_ref, task_name, completed_at, duration_minutes))
    log_id = cursor.fetchone()[0]
    db_conn.commit()
    cursor.close()
    return log_id


def _cleanup_test_data(db_conn, serial_numbers, worker_ids=None):
    """테스트 데이터 정리 — FK 역순 삭제"""
    cursor = db_conn.cursor()
    for sn in serial_numbers:
        try:
            cursor.execute("DELETE FROM work_completion_log WHERE serial_number = %s", (sn,))
            cursor.execute("DELETE FROM work_start_log WHERE serial_number = %s", (sn,))
            cursor.execute("DELETE FROM app_task_details WHERE serial_number = %s", (sn,))
            cursor.execute("DELETE FROM completion_status WHERE serial_number = %s", (sn,))
            cursor.execute("DELETE FROM qr_registry WHERE serial_number = %s", (sn,))
            cursor.execute("DELETE FROM plan.product_info WHERE serial_number = %s", (sn,))
        except Exception as e:
            db_conn.rollback()
    if worker_ids:
        for wid in worker_ids:
            try:
                cursor.execute("DELETE FROM work_completion_log WHERE worker_id = %s", (wid,))
                cursor.execute("DELETE FROM work_start_log WHERE worker_id = %s", (wid,))
                cursor.execute("DELETE FROM app_task_details WHERE worker_id = %s", (wid,))
                cursor.execute("DELETE FROM workers WHERE id = %s", (wid,))
            except Exception as e:
                db_conn.rollback()
    db_conn.commit()
    cursor.close()


def _create_worker_direct(db_conn, email, name, role='ELEC', company='TMS(E)'):
    """작업자 직접 삽입 (DB 레벨) → worker_id 반환"""
    from werkzeug.security import generate_password_hash
    cursor = db_conn.cursor()
    # 기존 잔여 데이터 정리
    cursor.execute("DELETE FROM work_completion_log WHERE worker_id IN (SELECT id FROM workers WHERE email = %s)", (email,))
    cursor.execute("DELETE FROM work_start_log WHERE worker_id IN (SELECT id FROM workers WHERE email = %s)", (email,))
    cursor.execute("DELETE FROM app_task_details WHERE worker_id IN (SELECT id FROM workers WHERE email = %s)", (email,))
    cursor.execute("DELETE FROM workers WHERE email = %s", (email,))
    db_conn.commit()

    pw_hash = generate_password_hash('TestPass123!')
    cursor.execute("""
        INSERT INTO workers (name, email, password_hash, role, company,
                             approval_status, email_verified, is_manager, is_admin)
        VALUES (%s, %s, %s, %s::role_enum, %s, 'approved', true, false, false)
        RETURNING id
    """, (name, email, pw_hash, role, company))
    worker_id = cursor.fetchone()[0]
    db_conn.commit()
    cursor.close()
    return worker_id


# ── TC-46-01: 정상 매핑 — task_id 일치 → workers 배열에 포함 ──────

def test_tc46_01_normal_task_id_mapping(client, db_conn, get_auth_token, seed_test_data):
    """
    TC-46-01: 정상 매핑 케이스.
    work_start_log.task_id = app_task_details.id 일치 → workers 배열에 작업자 포함.
    """
    sn = f'{_PREFIX}SN-01'
    email = f'iss46_w01@test.axisos.com'

    # 데이터 준비
    qr_doc_id = _insert_product(db_conn, sn)
    worker_id = _create_worker_direct(db_conn, email, 'ISS46 Worker01')

    task_detail_id = _insert_task_detail(db_conn, sn, qr_doc_id, worker_id,
                                          category='ELEC', task_id='WIRING', task_name='배선 포설')
    # task_id = task_detail_id (정상 매핑)
    _insert_start_log(db_conn, task_detail_id, worker_id, sn, qr_doc_id,
                      category='ELEC', task_id_ref='WIRING')

    try:
        # 관리자 토큰으로 all=true 조회
        admin_token = get_auth_token(worker_id=worker_id, role='ELEC', is_admin=True)
        resp = client.get(
            f'/api/app/tasks/{sn}?all=true',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.get_json()}"
        data = resp.get_json()
        tasks = data if isinstance(data, list) else data.get('tasks', [])

        # ELEC WIRING task 찾기
        wiring_task = next((t for t in tasks
                            if t.get('task_category') == 'ELEC' and t.get('task_id') == 'WIRING'), None)
        assert wiring_task is not None, f"WIRING task not found in tasks: {[t.get('task_id') for t in tasks]}"

        workers = wiring_task.get('workers', [])
        assert len(workers) >= 1, f"Expected at least 1 worker, got {workers}"
        worker_ids_in_response = [w['worker_id'] for w in workers]
        assert worker_id in worker_ids_in_response, \
            f"worker_id={worker_id} not in response workers: {worker_ids_in_response}"

    finally:
        _cleanup_test_data(db_conn, [sn], [worker_id])


# ── TC-46-02: task_id 불일치 — fallback으로 매핑 성공 ──────────────

def test_tc46_02_fallback_task_ref_mapping(client, db_conn, get_auth_token, seed_test_data):
    """
    TC-46-02: task_id 불일치 fallback 케이스.
    work_start_log.task_id를 존재하지 않는 id(999999)로 강제 설정 →
    2차 fallback(task_category + task_id_ref)으로 작업자 매핑 성공.
    """
    sn = f'{_PREFIX}SN-02'
    email = f'iss46_w02@test.axisos.com'

    qr_doc_id = _insert_product(db_conn, sn)
    worker_id = _create_worker_direct(db_conn, email, 'ISS46 Worker02')

    task_detail_id = _insert_task_detail(db_conn, sn, qr_doc_id, worker_id,
                                          category='ELEC', task_id='PANEL_WORK', task_name='판넬 작업')

    # 다른 S/N에 dummy task_detail 생성 (FK 충족용) → 이 id를 work_start_log에 사용
    dummy_sn = f'{_PREFIX}SN-02-DUMMY'
    dummy_qr = _insert_product(db_conn, dummy_sn)
    dummy_task_id = _insert_task_detail(db_conn, dummy_sn, dummy_qr, worker_id,
                                         category='ELEC', task_id='DUMMY_TASK', task_name='Dummy')

    # work_start_log에 다른 S/N의 task_id를 사용하여 삽입 — 현재 S/N task와 id 불일치 시뮬레이션
    started_at = datetime.now(timezone.utc) - timedelta(hours=2)
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO work_start_log
            (task_id, worker_id, serial_number, qr_doc_id, task_category,
             task_id_ref, task_name, started_at)
        VALUES (%s, %s, %s, %s, 'ELEC', 'PANEL_WORK', '판넬 작업', %s)
        RETURNING id
    """, (dummy_task_id, worker_id, sn, qr_doc_id, started_at))
    db_conn.commit()
    cursor.close()

    try:
        admin_token = get_auth_token(worker_id=worker_id, role='ELEC', is_admin=True)
        resp = client.get(
            f'/api/app/tasks/{sn}?all=true',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.get_json()}"
        data = resp.get_json()
        tasks = data if isinstance(data, list) else data.get('tasks', [])

        panel_task = next((t for t in tasks
                           if t.get('task_category') == 'ELEC' and t.get('task_id') == 'PANEL_WORK'), None)
        assert panel_task is not None, \
            f"PANEL_WORK task not found: {[t.get('task_id') for t in tasks]}"

        workers = panel_task.get('workers', [])
        assert len(workers) >= 1, \
            f"Fallback should have mapped worker, got workers={workers}"
        worker_ids_in_response = [w['worker_id'] for w in workers]
        assert worker_id in worker_ids_in_response, \
            f"Fallback failed: worker_id={worker_id} not in {worker_ids_in_response}"

    finally:
        # work_start_log에 dummy_task_id로 삽입했으므로 별도 정리
        cursor = db_conn.cursor()
        cursor.execute("DELETE FROM work_start_log WHERE serial_number = %s AND task_id = %s", (sn, dummy_task_id))
        db_conn.commit()
        cursor.close()
        _cleanup_test_data(db_conn, [sn, dummy_sn], [worker_id])


# ── TC-46-03: 다른 S/N의 work_start_log 혼입 안 됨 ──────────────────

def test_tc46_03_serial_number_isolation(client, db_conn, get_auth_token, seed_test_data):
    """
    TC-46-03: serial_number 필터 격리 검증.
    다른 S/N(SN-03B)의 work_start_log가 SN-03A 조회 결과에 혼입되지 않음.
    """
    sn_a = f'{_PREFIX}SN-03A'
    sn_b = f'{_PREFIX}SN-03B'
    email_a = f'iss46_w03a@test.axisos.com'
    email_b = f'iss46_w03b@test.axisos.com'

    qr_a = _insert_product(db_conn, sn_a)
    qr_b = _insert_product(db_conn, sn_b)
    worker_a = _create_worker_direct(db_conn, email_a, 'ISS46 Worker03A')
    worker_b = _create_worker_direct(db_conn, email_b, 'ISS46 Worker03B')

    # SN-03A: SELF_INSPECTION task + worker_a 시작
    task_id_a = _insert_task_detail(db_conn, sn_a, qr_a, worker_a,
                                     category='MECH', task_id='SELF_INSPECTION', task_name='자주검사')
    _insert_start_log(db_conn, task_id_a, worker_a, sn_a, qr_a,
                      category='MECH', task_id_ref='SELF_INSPECTION', task_name='자주검사')

    # SN-03B: 같은 task_id로 worker_b 시작 (다른 S/N)
    task_id_b = _insert_task_detail(db_conn, sn_b, qr_b, worker_b,
                                     category='MECH', task_id='SELF_INSPECTION', task_name='자주검사')
    _insert_start_log(db_conn, task_id_b, worker_b, sn_b, qr_b,
                      category='MECH', task_id_ref='SELF_INSPECTION', task_name='자주검사')

    try:
        admin_token = get_auth_token(worker_id=worker_a, role='MECH', is_admin=True)
        resp = client.get(
            f'/api/app/tasks/{sn_a}?all=true',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert resp.status_code == 200
        data = resp.get_json()
        tasks = data if isinstance(data, list) else data.get('tasks', [])

        self_insp_task = next((t for t in tasks
                               if t.get('task_category') == 'MECH'
                               and t.get('task_id') == 'SELF_INSPECTION'), None)
        assert self_insp_task is not None

        workers = self_insp_task.get('workers', [])
        worker_ids_in_response = [w['worker_id'] for w in workers]

        # SN-03A의 worker_a만 포함, SN-03B의 worker_b는 혼입 안 됨
        assert worker_a in worker_ids_in_response, \
            f"worker_a={worker_a} should be in response"
        assert worker_b not in worker_ids_in_response, \
            f"worker_b={worker_b} from different S/N should NOT be in response (got {worker_ids_in_response})"

    finally:
        _cleanup_test_data(db_conn, [sn_a, sn_b], [worker_a, worker_b])


# ── TC-46-04: completion_log JOIN 정상 (completed_at, duration_minutes) ──

def test_tc46_04_completion_log_join(client, db_conn, get_auth_token, seed_test_data):
    """
    TC-46-04: work_completion_log JOIN 정상 동작.
    completed_at, duration_minutes가 응답에 정상 반환됨.
    """
    sn = f'{_PREFIX}SN-04'
    email = f'iss46_w04@test.axisos.com'

    qr_doc_id = _insert_product(db_conn, sn)
    worker_id = _create_worker_direct(db_conn, email, 'ISS46 Worker04')

    task_detail_id = _insert_task_detail(db_conn, sn, qr_doc_id, worker_id,
                                          category='ELEC', task_id='IF_1', task_name='I.F 1')
    started_at = datetime.now(timezone.utc) - timedelta(hours=3)
    completed_at = datetime.now(timezone.utc) - timedelta(hours=1)
    duration = 120

    _insert_start_log(db_conn, task_detail_id, worker_id, sn, qr_doc_id,
                      started_at=started_at, category='ELEC', task_id_ref='IF_1', task_name='I.F 1')
    _insert_completion_log(db_conn, task_detail_id, worker_id, sn, qr_doc_id,
                           started_at=started_at, completed_at=completed_at,
                           duration_minutes=duration,
                           category='ELEC', task_id_ref='IF_1', task_name='I.F 1')

    try:
        admin_token = get_auth_token(worker_id=worker_id, role='ELEC', is_admin=True)
        resp = client.get(
            f'/api/app/tasks/{sn}?all=true',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert resp.status_code == 200
        data = resp.get_json()
        tasks = data if isinstance(data, list) else data.get('tasks', [])

        if1_task = next((t for t in tasks
                         if t.get('task_category') == 'ELEC' and t.get('task_id') == 'IF_1'), None)
        assert if1_task is not None, \
            f"IF_1 task not found: {[(t.get('task_category'), t.get('task_id')) for t in tasks]}"

        workers = if1_task.get('workers', [])
        assert len(workers) >= 1, f"No workers found in IF_1 task"

        worker_entry = next((w for w in workers if w['worker_id'] == worker_id), None)
        assert worker_entry is not None, f"worker_id={worker_id} not in workers"

        # completed_at 반환 확인
        assert worker_entry.get('completed_at') is not None, \
            f"completed_at should not be None: {worker_entry}"
        assert worker_entry.get('duration_minutes') == duration, \
            f"Expected duration={duration}, got {worker_entry.get('duration_minutes')}"
        assert worker_entry.get('status') == 'completed', \
            f"Expected status='completed', got {worker_entry.get('status')}"

    finally:
        _cleanup_test_data(db_conn, [sn], [worker_id])


# ── TC-46-05: 동시작업 (multi-worker) — 같은 task에 2명 → workers 2건 ──

def test_tc46_05_multi_worker_same_task(client, db_conn, get_auth_token, seed_test_data):
    """
    TC-46-05: 멀티 작업자 동시 작업.
    같은 task에 2명이 각각 시작 → workers 배열에 2건 반환.
    """
    sn = f'{_PREFIX}SN-05'
    email_a = f'iss46_w05a@test.axisos.com'
    email_b = f'iss46_w05b@test.axisos.com'

    qr_doc_id = _insert_product(db_conn, sn)
    worker_a = _create_worker_direct(db_conn, email_a, 'ISS46 Worker05A')
    worker_b = _create_worker_direct(db_conn, email_b, 'ISS46 Worker05B')

    # 동일 task에 worker_a를 owner로 등록
    task_detail_id = _insert_task_detail(db_conn, sn, qr_doc_id, worker_a,
                                          category='MECH', task_id='SELF_INSPECTION', task_name='자주검사')

    # 두 작업자 모두 같은 task_detail_id로 시작
    started_a = datetime.now(timezone.utc) - timedelta(hours=2)
    started_b = datetime.now(timezone.utc) - timedelta(hours=1, minutes=30)

    _insert_start_log(db_conn, task_detail_id, worker_a, sn, qr_doc_id,
                      started_at=started_a, category='MECH', task_id_ref='SELF_INSPECTION', task_name='자주검사')
    _insert_start_log(db_conn, task_detail_id, worker_b, sn, qr_doc_id,
                      started_at=started_b, category='MECH', task_id_ref='SELF_INSPECTION', task_name='자주검사')

    try:
        admin_token = get_auth_token(worker_id=worker_a, role='MECH', is_admin=True)
        resp = client.get(
            f'/api/app/tasks/{sn}?all=true',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert resp.status_code == 200
        data = resp.get_json()
        tasks = data if isinstance(data, list) else data.get('tasks', [])

        self_insp = next((t for t in tasks
                          if t.get('task_category') == 'MECH'
                          and t.get('task_id') == 'SELF_INSPECTION'), None)
        assert self_insp is not None

        workers = self_insp.get('workers', [])
        assert len(workers) == 2, \
            f"Expected 2 workers for multi-worker task, got {len(workers)}: {workers}"

        worker_ids_in_response = {w['worker_id'] for w in workers}
        assert worker_a in worker_ids_in_response, \
            f"worker_a={worker_a} not in response"
        assert worker_b in worker_ids_in_response, \
            f"worker_b={worker_b} not in response"

    finally:
        _cleanup_test_data(db_conn, [sn], [worker_a, worker_b])
