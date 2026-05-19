"""
PI/QI admin-complete + cross-worker 차단 테스트 — Sprint 69 (FEAT-PIQI-COMPLETE-OWNER-LOCK)
- BE-1: POST /api/app/work/complete — PI/QI cross-worker 차단
- BE-2: POST /api/app/work/admin-complete — PI/QI 공정 admin/manager 정상 완료

설계: AGENT_TEAM_LAUNCH.md § Sprint 69 (영역 10 Codex 검증 반영)
프로덕션 데이터 보호: TEST_AC_ prefix만 사용.
"""
import time
from datetime import datetime, timedelta, timezone

import pytest

_PREFIX = 'TEST_AC_'
_KST = timezone(timedelta(hours=9))
_TS = lambda: str(int(time.time() * 1000))


def _sn(suffix: str) -> str:
    return f'{_PREFIX}{suffix}'


@pytest.fixture(autouse=True)
def cleanup_ac(db_conn):
    yield
    if db_conn and not db_conn.closed:
        try:
            cur = db_conn.cursor()
            for t in ('work_completion_log', 'work_start_log',
                      'app_task_details', 'completion_status', 'qr_registry'):
                cur.execute(f"DELETE FROM {t} WHERE serial_number LIKE %s", (f'{_PREFIX}%',))
            cur.execute("DELETE FROM plan.product_info WHERE serial_number LIKE %s", (f'{_PREFIX}%',))
            db_conn.commit()
            cur.close()
        except Exception:
            try:
                db_conn.rollback()
            except Exception:
                pass


def _seed_product(db_conn, sn: str, model: str = 'GAIA-I') -> str:
    cur = db_conn.cursor()
    qr = f'DOC_{sn}'
    cur.execute("""
        INSERT INTO plan.product_info (serial_number, model, mech_partner, elec_partner, prod_date)
        VALUES (%s, %s, 'FNI', 'P&S', NOW()::date)
        ON CONFLICT (serial_number) DO NOTHING
    """, (sn, model))
    cur.execute("""
        INSERT INTO qr_registry (qr_doc_id, serial_number, status)
        VALUES (%s, %s, 'active') ON CONFLICT (qr_doc_id) DO NOTHING
    """, (qr, sn))
    cur.execute("""
        INSERT INTO completion_status (serial_number)
        VALUES (%s) ON CONFLICT (serial_number) DO NOTHING
    """, (sn,))
    db_conn.commit()
    cur.close()
    return qr


def _seed_task(db_conn, sn, qr, category, task_id, worker_id,
               started_at=None, completed_at=None):
    """PI/QI task INSERT → task_detail_id. (NORMAL task)"""
    cur = db_conn.cursor()
    s = started_at if started_at else 'NULL'
    c = completed_at if completed_at else 'NULL'
    cur.execute(f"""
        INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
             is_applicable, task_type, started_at, completed_at)
        VALUES (%s, %s, %s, %s, %s, %s, TRUE, 'NORMAL', {s}, {c})
        RETURNING id
    """, (worker_id, sn, qr, category, task_id, task_id))
    tid = cur.fetchone()[0]
    db_conn.commit()
    cur.close()
    return tid


def _seed_wsl(db_conn, tid, sn, qr, worker_id, category, task_id,
              started="NOW() - INTERVAL '2 hours'"):
    cur = db_conn.cursor()
    cur.execute(f"""
        INSERT INTO work_start_log
            (task_id, worker_id, serial_number, qr_doc_id, task_category,
             task_id_ref, task_name, started_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, {started})
    """, (tid, worker_id, sn, qr, category, task_id, task_id))
    db_conn.commit()
    cur.close()


def _seed_wcl(db_conn, tid, sn, qr, worker_id, category, task_id,
              completed='NOW()', duration=60):
    cur = db_conn.cursor()
    cur.execute(f"""
        INSERT INTO work_completion_log
            (task_id, worker_id, serial_number, qr_doc_id, task_category,
             task_id_ref, task_name, completed_at, duration_minutes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, {completed}, %s)
    """, (tid, worker_id, sn, qr, category, task_id, task_id, duration))
    db_conn.commit()
    cur.close()


def _admin(create_test_worker, get_auth_token, tag):
    wid = create_test_worker(
        email=f'ac_admin_{tag}_{_TS()}@test.com', password='Test123!',
        name=f'Admin {tag}', role='ADMIN', company='GST', is_admin=True,
    )
    return get_auth_token(wid), wid


def _worker(create_test_worker, tag, role='PI'):
    return create_test_worker(
        email=f'ac_w_{tag}_{_TS()}@test.com', password='Test123!',
        name=f'W {tag}', role=role, company='GST',
    )


def _task_row(db_conn, tid):
    cur = db_conn.cursor()
    cur.execute("""
        SELECT started_at, completed_at, force_closed, closed_by, close_reason
        FROM app_task_details WHERE id=%s
    """, (tid,))
    r = cur.fetchone()
    cur.close()
    return r


class TestPiqiCrossWorkerBlock:
    """BE-1: PI/QI cross-worker 완료 차단 — 시작한 본인만 완료"""

    def test_cross_worker_block_PI(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-AC-01: worker1 시작한 PI task를 worker2가 완료 시도 → 403"""
        sn = _sn(f'01_{_TS()}')
        qr = _seed_product(db_conn, sn)
        w1 = _worker(create_test_worker, '01a', role='PI')
        w2 = _worker(create_test_worker, '01b', role='PI')
        tid = _seed_task(db_conn, sn, qr, 'PI', 'PI_LNG_UTIL', w1,
                         started_at="NOW() - INTERVAL '2 hours'")
        _seed_wsl(db_conn, tid, sn, qr, w1, 'PI', 'PI_LNG_UTIL')

        token_w2 = get_auth_token(w2)
        resp = client.post('/api/app/work/complete',
                            json={'task_id': tid, 'worker_id': w2, 'finalize': False},
                            headers={'Authorization': f'Bearer {token_w2}'})
        assert resp.status_code == 403, resp.get_json()
        assert resp.get_json()['error'] == 'FORBIDDEN'

    def test_cross_worker_block_QI(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-AC-02: worker1 시작한 QI task를 worker2가 완료 시도 → 403"""
        sn = _sn(f'02_{_TS()}')
        qr = _seed_product(db_conn, sn)
        w1 = _worker(create_test_worker, '02a', role='QI')
        w2 = _worker(create_test_worker, '02b', role='QI')
        tid = _seed_task(db_conn, sn, qr, 'QI', 'QI_INSPECTION', w1,
                         started_at="NOW() - INTERVAL '2 hours'")
        _seed_wsl(db_conn, tid, sn, qr, w1, 'QI', 'QI_INSPECTION')

        token_w2 = get_auth_token(w2)
        resp = client.post('/api/app/work/complete',
                            json={'task_id': tid, 'worker_id': w2, 'finalize': False},
                            headers={'Authorization': f'Bearer {token_w2}'})
        assert resp.status_code == 403, resp.get_json()
        assert resp.get_json()['error'] == 'FORBIDDEN'


class TestAdminComplete:
    """BE-2: PI/QI admin-complete — admin/manager 정상 완료"""

    def test_admin_complete_PI_success(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-AC-03: PI 공정 미완료 task 2개 전수 완료 + pi_completed + audit"""
        sn = _sn(f'03_{_TS()}')
        qr = _seed_product(db_conn, sn)
        token, admin_id = _admin(create_test_worker, get_auth_token, '03')
        w = _worker(create_test_worker, '03', role='PI')
        t1 = _seed_task(db_conn, sn, qr, 'PI', 'PI_LNG_UTIL', w,
                        started_at="NOW() - INTERVAL '2 hours'")
        t2 = _seed_task(db_conn, sn, qr, 'PI', 'PI_CHAMBER', w,
                        started_at="NOW() - INTERVAL '2 hours'")
        _seed_wsl(db_conn, t1, sn, qr, w, 'PI', 'PI_LNG_UTIL')
        _seed_wsl(db_conn, t2, sn, qr, w, 'PI', 'PI_CHAMBER')

        resp = client.post('/api/app/work/admin-complete',
                            json={'serial_number': sn, 'task_category': 'PI'},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()
        assert set(data['completed_tasks']) == {'PI_LNG_UTIL', 'PI_CHAMBER'}
        for tid in (t1, t2):
            row = _task_row(db_conn, tid)
            assert row[1] is not None              # completed_at
            assert row[2] is False                 # force_closed
            assert row[3] == admin_id              # closed_by
            assert row[4] == 'ADMIN_COMPLETE'      # close_reason
        cur = db_conn.cursor()
        cur.execute("SELECT pi_completed FROM completion_status WHERE serial_number=%s", (sn,))
        assert cur.fetchone()[0] is True
        cur.close()

    def test_admin_complete_QI_success(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-AC-04: QI 공정 완료 + qi_completed + force_closed=FALSE"""
        sn = _sn(f'04_{_TS()}')
        qr = _seed_product(db_conn, sn)
        token, admin_id = _admin(create_test_worker, get_auth_token, '04')
        w = _worker(create_test_worker, '04', role='QI')
        tid = _seed_task(db_conn, sn, qr, 'QI', 'QI_INSPECTION', w,
                         started_at="NOW() - INTERVAL '2 hours'")
        _seed_wsl(db_conn, tid, sn, qr, w, 'QI', 'QI_INSPECTION')

        resp = client.post('/api/app/work/admin-complete',
                            json={'serial_number': sn, 'task_category': 'QI'},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200, resp.get_json()
        row = _task_row(db_conn, tid)
        assert row[1] is not None and row[2] is False
        cur = db_conn.cursor()
        cur.execute("SELECT qi_completed FROM completion_status WHERE serial_number=%s", (sn,))
        assert cur.fetchone()[0] is True
        cur.close()

    def test_partial_idempotency(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-AC-05: PI 한 개 이미 완료 → 미완료만 처리 + 기존 completed_at 보존"""
        sn = _sn(f'05_{_TS()}')
        qr = _seed_product(db_conn, sn)
        token, _ = _admin(create_test_worker, get_auth_token, '05')
        w = _worker(create_test_worker, '05', role='PI')
        t1 = _seed_task(db_conn, sn, qr, 'PI', 'PI_LNG_UTIL', w,
                        started_at="NOW() - INTERVAL '1 day'",
                        completed_at="NOW() - INTERVAL '20 hours'")
        t2 = _seed_task(db_conn, sn, qr, 'PI', 'PI_CHAMBER', w,
                        started_at="NOW() - INTERVAL '2 hours'")
        _seed_wsl(db_conn, t2, sn, qr, w, 'PI', 'PI_CHAMBER')
        t1_before = _task_row(db_conn, t1)[1]

        resp = client.post('/api/app/work/admin-complete',
                            json={'serial_number': sn, 'task_category': 'PI'},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200, resp.get_json()
        assert resp.get_json()['completed_tasks'] == ['PI_CHAMBER']  # 미완료만
        assert _task_row(db_conn, t1)[1] == t1_before                # 기존 보존
        assert _task_row(db_conn, t2)[1] is not None

    def test_all_done_idempotency(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-AC-06: PI 전부 완료된 S/N 재호출 → 200 already_completed:true"""
        sn = _sn(f'06_{_TS()}')
        qr = _seed_product(db_conn, sn)
        token, _ = _admin(create_test_worker, get_auth_token, '06')
        w = _worker(create_test_worker, '06', role='PI')
        _seed_task(db_conn, sn, qr, 'PI', 'PI_LNG_UTIL', w,
                   started_at="NOW() - INTERVAL '1 day'", completed_at="NOW() - INTERVAL '20 hours'")
        _seed_task(db_conn, sn, qr, 'PI', 'PI_CHAMBER', w,
                   started_at="NOW() - INTERVAL '1 day'", completed_at="NOW() - INTERVAL '20 hours'")

        resp = client.post('/api/app/work/admin-complete',
                            json={'serial_number': sn, 'task_category': 'PI'},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['already_completed'] is True
        assert data['completed_tasks'] == []

    def test_completed_at_future_rejected(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-AC-07: completed_at 미래 → 400"""
        sn = _sn(f'07_{_TS()}')
        qr = _seed_product(db_conn, sn)
        token, _ = _admin(create_test_worker, get_auth_token, '07')
        w = _worker(create_test_worker, '07', role='QI')
        tid = _seed_task(db_conn, sn, qr, 'QI', 'QI_INSPECTION', w,
                         started_at="NOW() - INTERVAL '2 hours'")
        _seed_wsl(db_conn, tid, sn, qr, w, 'QI', 'QI_INSPECTION')

        future = (datetime.now(_KST) + timedelta(days=1)).isoformat()
        resp = client.post('/api/app/work/admin-complete',
                            json={'serial_number': sn, 'task_category': 'QI', 'completed_at': future},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'INVALID_COMPLETED_AT_FUTURE'

    def test_completed_at_before_started_rejected(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-AC-08: completed_at < task.started_at → 400"""
        sn = _sn(f'08_{_TS()}')
        qr = _seed_product(db_conn, sn)
        token, _ = _admin(create_test_worker, get_auth_token, '08')
        w = _worker(create_test_worker, '08', role='QI')
        tid = _seed_task(db_conn, sn, qr, 'QI', 'QI_INSPECTION', w,
                         started_at="NOW() - INTERVAL '2 hours'")
        _seed_wsl(db_conn, tid, sn, qr, w, 'QI', 'QI_INSPECTION')

        before = (datetime.now(_KST) - timedelta(hours=5)).isoformat()
        resp = client.post('/api/app/work/admin-complete',
                            json={'serial_number': sn, 'task_category': 'QI', 'completed_at': before},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'INVALID_COMPLETED_AT_BEFORE_START'

    def test_multi_worker_backfill(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-AC-09: PI 멀티작업자 — 미완료 작업자 work_completion_log backfill"""
        sn = _sn(f'09_{_TS()}')
        qr = _seed_product(db_conn, sn)
        token, _ = _admin(create_test_worker, get_auth_token, '09')
        wa = _worker(create_test_worker, '09a', role='PI')
        wb = _worker(create_test_worker, '09b', role='PI')
        tid = _seed_task(db_conn, sn, qr, 'PI', 'PI_LNG_UTIL', wa,
                         started_at="NOW() - INTERVAL '3 hours'")
        # 작업자 A: 시작+완료 / 작업자 B: 시작만 (미완료)
        _seed_wsl(db_conn, tid, sn, qr, wa, 'PI', 'PI_LNG_UTIL')
        _seed_wcl(db_conn, tid, sn, qr, wa, 'PI', 'PI_LNG_UTIL')
        _seed_wsl(db_conn, tid, sn, qr, wb, 'PI', 'PI_LNG_UTIL')

        resp = client.post('/api/app/work/admin-complete',
                            json={'serial_number': sn, 'task_category': 'PI'},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200, resp.get_json()
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM work_completion_log WHERE task_id=%s AND worker_id=%s",
                    (tid, wb))
        assert cur.fetchone()[0] == 1, "작업자 B completion_log backfill 누락"
        cur.close()

    def test_admin_complete_PI_delegated_model(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-AC-10: PI 위임 모델(DRAGON) — admin-complete 정상 동작 (regression, Twin파파 catch)"""
        sn = _sn(f'10_{_TS()}')
        qr = _seed_product(db_conn, sn, model='DRAGON-50')
        token, _ = _admin(create_test_worker, get_auth_token, '10')
        w = _worker(create_test_worker, '10', role='PI')
        t1 = _seed_task(db_conn, sn, qr, 'PI', 'PI_LNG_UTIL', w,
                        started_at="NOW() - INTERVAL '2 hours'")
        _seed_wsl(db_conn, t1, sn, qr, w, 'PI', 'PI_LNG_UTIL')

        resp = client.post('/api/app/work/admin-complete',
                            json={'serial_number': sn, 'task_category': 'PI'},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200, resp.get_json()
        # PI 위임 모델이어도 admin-complete는 task 단위 처리 — applicable PI task 완료
        assert _task_row(db_conn, t1)[1] is not None
        cur = db_conn.cursor()
        cur.execute("SELECT pi_completed FROM completion_status WHERE serial_number=%s", (sn,))
        assert cur.fetchone()[0] is True
        cur.close()
