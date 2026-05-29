"""
출하 완료 (ship-complete) 테스트 — Sprint 68 (FEAT-SHIPMENT-COMPLETE)
엔드포인트: POST /api/app/work/ship-complete

SI task 2개(SI_FINISHING=NORMAL / SI_SHIPMENT=SINGLE_ACTION) 완료 처리.
설계: AGENT_TEAM_LAUNCH.md § Sprint 68 (영역 10 Codex 검증 + 영역 11 audit)

프로덕션 데이터 보호: TEST_SHIP_ prefix만 사용, teardown에서 prefix만 삭제.
"""
import time
from datetime import datetime, timedelta, timezone

import pytest

_PREFIX = 'TEST_SHIP_'
_KST = timezone(timedelta(hours=9))
_TS = lambda: str(int(time.time() * 1000))


def _sn(suffix: str) -> str:
    return f'{_PREFIX}{suffix}'


@pytest.fixture(autouse=True)
def cleanup_ship_data(db_conn):
    """각 테스트 후 TEST_SHIP_ prefix 데이터만 삭제 (FK 역순)."""
    yield
    if db_conn and not db_conn.closed:
        try:
            cur = db_conn.cursor()
            cur.execute("DELETE FROM work_completion_log WHERE serial_number LIKE %s", (f'{_PREFIX}%',))
            cur.execute("DELETE FROM work_start_log WHERE serial_number LIKE %s", (f'{_PREFIX}%',))
            cur.execute("DELETE FROM app_task_details WHERE serial_number LIKE %s", (f'{_PREFIX}%',))
            cur.execute("DELETE FROM completion_status WHERE serial_number LIKE %s", (f'{_PREFIX}%',))
            cur.execute("DELETE FROM qr_registry WHERE serial_number LIKE %s", (f'{_PREFIX}%',))
            cur.execute("DELETE FROM plan.product_info WHERE serial_number LIKE %s", (f'{_PREFIX}%',))
            db_conn.commit()
            cur.close()
        except Exception:
            try:
                db_conn.rollback()
            except Exception:
                pass


def _seed_product(db_conn, sn: str) -> str:
    cur = db_conn.cursor()
    qr = f'DOC_{sn}'
    cur.execute("""
        INSERT INTO plan.product_info (serial_number, model, mech_partner, elec_partner, prod_date)
        VALUES (%s, 'GAIA-I', 'FNI', 'P&S', NOW()::date)
        ON CONFLICT (serial_number) DO NOTHING
    """, (sn,))
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


def _seed_si_task(db_conn, sn, qr, task_id, task_type, worker_id,
                  started_at=None, completed_at=None, is_applicable=True):
    """SI task INSERT → task_detail_id. started_at/completed_at은 SQL 표현식 문자열 or None."""
    cur = db_conn.cursor()
    started_sql = started_at if started_at else 'NULL'
    completed_sql = completed_at if completed_at else 'NULL'
    cur.execute(f"""
        INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
             is_applicable, task_type, started_at, completed_at)
        VALUES (%s, %s, %s, 'SI', %s, %s, %s, %s, {started_sql}, {completed_sql})
        RETURNING id
    """, (worker_id, sn, qr, task_id, task_id, is_applicable, task_type))
    tid = cur.fetchone()[0]
    db_conn.commit()
    cur.close()
    return tid


def _seed_wsl(db_conn, task_detail_id, sn, qr, worker_id, started_at="NOW() - INTERVAL '2 hours'"):
    cur = db_conn.cursor()
    cur.execute(f"""
        INSERT INTO work_start_log
            (task_id, worker_id, serial_number, qr_doc_id, task_category,
             task_id_ref, task_name, started_at)
        VALUES (%s, %s, %s, %s, 'SI', 'SI_FINISHING', '마무리공정', {started_at})
    """, (task_detail_id, worker_id, sn, qr))
    db_conn.commit()
    cur.close()


def _seed_wcl(db_conn, task_detail_id, sn, qr, worker_id, completed_at='NOW()', duration=60):
    cur = db_conn.cursor()
    cur.execute(f"""
        INSERT INTO work_completion_log
            (task_id, worker_id, serial_number, qr_doc_id, task_category,
             task_id_ref, task_name, completed_at, duration_minutes)
        VALUES (%s, %s, %s, %s, 'SI', 'SI_FINISHING', '마무리공정', {completed_at}, %s)
    """, (task_detail_id, worker_id, sn, qr, duration))
    db_conn.commit()
    cur.close()


def _admin(create_test_worker, get_auth_token, tag):
    wid = create_test_worker(
        email=f'ship_admin_{tag}_{_TS()}@test.com', password='Test123!',
        name=f'Admin {tag}', role='ADMIN', company='GST', is_admin=True,
    )
    return get_auth_token(wid), wid


def _worker(create_test_worker, tag):
    return create_test_worker(
        email=f'ship_w_{tag}_{_TS()}@test.com', password='Test123!',
        name=f'Worker {tag}', role='SI', company='GST',
    )


def _task_row(db_conn, task_detail_id):
    cur = db_conn.cursor()
    cur.execute("""
        SELECT started_at, completed_at, duration_minutes, worker_id,
               force_closed, closed_by, close_reason, task_type
        FROM app_task_details WHERE id = %s
    """, (task_detail_id,))
    row = cur.fetchone()
    cur.close()
    return row


class TestShipComplete:
    """출하 완료 — SI task 2개 완료 처리 (Sprint 68)"""

    def test_both_si_tasks_completed_when_both_incomplete(
            self, client, create_test_worker, get_auth_token, db_conn):
        """TC-SHIP-01: SI_FINISHING 진행중 + SI_SHIPMENT 미시작 → 둘 다 완료"""
        sn = _sn(f'01_{_TS()}')
        qr = _seed_product(db_conn, sn)
        token, admin_id = _admin(create_test_worker, get_auth_token, '01')
        wid = _worker(create_test_worker, '01')
        fin_id = _seed_si_task(db_conn, sn, qr, 'SI_FINISHING', 'NORMAL', wid,
                               started_at="NOW() - INTERVAL '2 hours'")
        ship_id = _seed_si_task(db_conn, sn, qr, 'SI_SHIPMENT', 'SINGLE_ACTION', wid)
        _seed_wsl(db_conn, fin_id, sn, qr, wid)

        resp = client.post('/api/app/work/ship-complete',
                            json={'serial_number': sn},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()
        assert set(data['completed_tasks']) == {'SI_FINISHING', 'SI_SHIPMENT'}
        assert data['si_completed'] is True
        assert _task_row(db_conn, fin_id)[1] is not None   # finishing.completed_at
        assert _task_row(db_conn, ship_id)[1] is not None  # shipment.completed_at

    def test_si_shipment_single_action_semantics(
            self, client, create_test_worker, get_auth_token, db_conn):
        """TC-SHIP-02: SI_SHIPMENT(SINGLE_ACTION) 완료 → started_at=completed_at, duration=0"""
        sn = _sn(f'02_{_TS()}')
        qr = _seed_product(db_conn, sn)
        token, admin_id = _admin(create_test_worker, get_auth_token, '02')
        wid = _worker(create_test_worker, '02')
        fin_id = _seed_si_task(db_conn, sn, qr, 'SI_FINISHING', 'NORMAL', wid,
                               started_at="NOW() - INTERVAL '2 hours'")
        ship_id = _seed_si_task(db_conn, sn, qr, 'SI_SHIPMENT', 'SINGLE_ACTION', wid)
        _seed_wsl(db_conn, fin_id, sn, qr, wid)

        resp = client.post('/api/app/work/ship-complete', json={'serial_number': sn},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200, resp.get_json()
        ship = _task_row(db_conn, ship_id)
        assert ship[0] is not None and ship[1] is not None  # started_at, completed_at
        assert ship[0] == ship[1]                           # started == completed
        assert ship[2] == 0                                 # duration_minutes

    def test_rejects_completed_at_before_si_finishing_started_at(
            self, client, create_test_worker, get_auth_token, db_conn):
        """TC-SHIP-03: completed_at < SI_FINISHING.started_at → 400"""
        sn = _sn(f'03_{_TS()}')
        qr = _seed_product(db_conn, sn)
        token, _ = _admin(create_test_worker, get_auth_token, '03')
        wid = _worker(create_test_worker, '03')
        fin_id = _seed_si_task(db_conn, sn, qr, 'SI_FINISHING', 'NORMAL', wid,
                               started_at="NOW() - INTERVAL '2 hours'")
        _seed_si_task(db_conn, sn, qr, 'SI_SHIPMENT', 'SINGLE_ACTION', wid)
        _seed_wsl(db_conn, fin_id, sn, qr, wid)

        before = (datetime.now(_KST) - timedelta(hours=5)).isoformat()
        resp = client.post('/api/app/work/ship-complete',
                            json={'serial_number': sn, 'completed_at': before},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'INVALID_COMPLETED_AT_BEFORE_START'

    def test_rejects_future_completed_at(
            self, client, create_test_worker, get_auth_token, db_conn):
        """TC-SHIP-04: completed_at 미래 → 400"""
        sn = _sn(f'04_{_TS()}')
        qr = _seed_product(db_conn, sn)
        token, _ = _admin(create_test_worker, get_auth_token, '04')
        wid = _worker(create_test_worker, '04')
        fin_id = _seed_si_task(db_conn, sn, qr, 'SI_FINISHING', 'NORMAL', wid,
                               started_at="NOW() - INTERVAL '2 hours'")
        _seed_si_task(db_conn, sn, qr, 'SI_SHIPMENT', 'SINGLE_ACTION', wid)
        _seed_wsl(db_conn, fin_id, sn, qr, wid)

        future = (datetime.now(_KST) + timedelta(days=1)).isoformat()
        resp = client.post('/api/app/work/ship-complete',
                            json={'serial_number': sn, 'completed_at': future},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'INVALID_COMPLETED_AT_FUTURE'

    def test_si_completed_set_after_both_si_tasks_done(
            self, client, create_test_worker, get_auth_token, db_conn):
        """TC-SHIP-05: 출하완료 후 completion_status.si_completed=TRUE"""
        sn = _sn(f'05_{_TS()}')
        qr = _seed_product(db_conn, sn)
        token, _ = _admin(create_test_worker, get_auth_token, '05')
        wid = _worker(create_test_worker, '05')
        fin_id = _seed_si_task(db_conn, sn, qr, 'SI_FINISHING', 'NORMAL', wid,
                               started_at="NOW() - INTERVAL '2 hours'")
        _seed_si_task(db_conn, sn, qr, 'SI_SHIPMENT', 'SINGLE_ACTION', wid)
        _seed_wsl(db_conn, fin_id, sn, qr, wid)

        resp = client.post('/api/app/work/ship-complete', json={'serial_number': sn},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200, resp.get_json()
        cur = db_conn.cursor()
        cur.execute("SELECT si_completed FROM completion_status WHERE serial_number=%s", (sn,))
        assert cur.fetchone()[0] is True
        cur.close()

    def test_preserves_existing_si_finishing_completed_at(
            self, client, create_test_worker, get_auth_token, db_conn):
        """TC-SHIP-06: SI_FINISHING 이미 완료 → completed_at 보존, SHIPMENT만 처리"""
        sn = _sn(f'06_{_TS()}')
        qr = _seed_product(db_conn, sn)
        token, _ = _admin(create_test_worker, get_auth_token, '06')
        wid = _worker(create_test_worker, '06')
        fin_id = _seed_si_task(db_conn, sn, qr, 'SI_FINISHING', 'NORMAL', wid,
                               started_at="NOW() - INTERVAL '1 day'",
                               completed_at="NOW() - INTERVAL '20 hours'")
        ship_id = _seed_si_task(db_conn, sn, qr, 'SI_SHIPMENT', 'SINGLE_ACTION', wid)
        fin_before = _task_row(db_conn, fin_id)[1]

        resp = client.post('/api/app/work/ship-complete', json={'serial_number': sn},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()
        assert data['completed_tasks'] == ['SI_SHIPMENT']  # finishing은 이미 완료
        assert _task_row(db_conn, fin_id)[1] == fin_before  # finishing.completed_at 불변
        assert _task_row(db_conn, ship_id)[1] is not None   # shipment 완료됨

    def test_idempotent_when_both_already_done(
            self, client, create_test_worker, get_auth_token, db_conn):
        """TC-SHIP-07: 둘 다 완료된 S/N 재호출 → 200 already_completed:true"""
        sn = _sn(f'07_{_TS()}')
        qr = _seed_product(db_conn, sn)
        token, _ = _admin(create_test_worker, get_auth_token, '07')
        wid = _worker(create_test_worker, '07')
        _seed_si_task(db_conn, sn, qr, 'SI_FINISHING', 'NORMAL', wid,
                      started_at="NOW() - INTERVAL '1 day'", completed_at="NOW() - INTERVAL '20 hours'")
        _seed_si_task(db_conn, sn, qr, 'SI_SHIPMENT', 'SINGLE_ACTION', wid,
                      started_at="NOW() - INTERVAL '20 hours'", completed_at="NOW() - INTERVAL '20 hours'")

        resp = client.post('/api/app/work/ship-complete', json={'serial_number': sn},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['already_completed'] is True
        assert data['completed_tasks'] == []

    def test_multi_worker_backfills_orphan_completion_logs(
            self, client, create_test_worker, get_auth_token, db_conn):
        """TC-SHIP-08: SI_FINISHING 멀티작업자 — 미완료 작업자 work_completion_log backfill"""
        sn = _sn(f'08_{_TS()}')
        qr = _seed_product(db_conn, sn)
        token, _ = _admin(create_test_worker, get_auth_token, '08')
        wa = _worker(create_test_worker, '08a')
        wb = _worker(create_test_worker, '08b')
        fin_id = _seed_si_task(db_conn, sn, qr, 'SI_FINISHING', 'NORMAL', wa,
                               started_at="NOW() - INTERVAL '3 hours'")
        _seed_si_task(db_conn, sn, qr, 'SI_SHIPMENT', 'SINGLE_ACTION', wa)
        # 작업자 A: 시작 + 완료 / 작업자 B: 시작만 (미완료)
        _seed_wsl(db_conn, fin_id, sn, qr, wa)
        _seed_wcl(db_conn, fin_id, sn, qr, wa)
        _seed_wsl(db_conn, fin_id, sn, qr, wb)

        resp = client.post('/api/app/work/ship-complete', json={'serial_number': sn},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200, resp.get_json()
        # 작업자 B의 work_completion_log가 backfill 되었는지
        cur = db_conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM work_completion_log
            WHERE task_id=%s AND worker_id=%s
        """, (fin_id, wb))
        assert cur.fetchone()[0] == 1, "작업자 B completion_log backfill 누락"
        cur.close()

    def test_does_not_set_force_closed_true(
            self, client, create_test_worker, get_auth_token, db_conn):
        """TC-SHIP-09: 출하완료는 정상 종료 — force_closed=FALSE 유지"""
        sn = _sn(f'09_{_TS()}')
        qr = _seed_product(db_conn, sn)
        token, _ = _admin(create_test_worker, get_auth_token, '09')
        wid = _worker(create_test_worker, '09')
        fin_id = _seed_si_task(db_conn, sn, qr, 'SI_FINISHING', 'NORMAL', wid,
                               started_at="NOW() - INTERVAL '2 hours'")
        ship_id = _seed_si_task(db_conn, sn, qr, 'SI_SHIPMENT', 'SINGLE_ACTION', wid)
        _seed_wsl(db_conn, fin_id, sn, qr, wid)

        resp = client.post('/api/app/work/ship-complete', json={'serial_number': sn},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200, resp.get_json()
        assert _task_row(db_conn, fin_id)[4] is False   # finishing.force_closed
        assert _task_row(db_conn, ship_id)[4] is False  # shipment.force_closed

    def test_audit_records_close_reason_and_closed_by(
            self, client, create_test_worker, get_auth_token, db_conn):
        """TC-SHIP-10: audit — close_reason='SHIP_COMPLETE' + closed_by=실행 관리자 (영역 11)"""
        sn = _sn(f'10_{_TS()}')
        qr = _seed_product(db_conn, sn)
        token, admin_id = _admin(create_test_worker, get_auth_token, '10')
        wid = _worker(create_test_worker, '10')
        fin_id = _seed_si_task(db_conn, sn, qr, 'SI_FINISHING', 'NORMAL', wid,
                               started_at="NOW() - INTERVAL '2 hours'")
        ship_id = _seed_si_task(db_conn, sn, qr, 'SI_SHIPMENT', 'SINGLE_ACTION', wid)
        _seed_wsl(db_conn, fin_id, sn, qr, wid)

        resp = client.post('/api/app/work/ship-complete', json={'serial_number': sn},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200, resp.get_json()
        for tid in (fin_id, ship_id):
            row = _task_row(db_conn, tid)
            assert row[6] == 'SHIP_COMPLETE'  # close_reason
            assert row[5] == admin_id         # closed_by
            assert row[4] is False            # force_closed

    def test_non_manager_permission_denied(
            self, client, create_test_worker, get_auth_token, db_conn):
        """TC-SHIP-11: 일반 작업자(비 SI/manager/admin) → 403.

        v2.20.15: SI 인원은 이제 허용되므로 비-SI 작업자(PI)로 거부 검증.
        (이전엔 _worker(role='SI') 사용 → SI 확장 후 200이 되어 깨짐)"""
        sn = _sn(f'11_{_TS()}')
        qr = _seed_product(db_conn, sn)
        wid = create_test_worker(
            email=f'ship_w_pi11_{_TS()}@test.com', password='Test123!',
            name='Worker PI 11', role='PI', company='GST',
        )
        token = get_auth_token(wid)
        fin_id = _seed_si_task(db_conn, sn, qr, 'SI_FINISHING', 'NORMAL', wid,
                               started_at="NOW() - INTERVAL '2 hours'")
        _seed_si_task(db_conn, sn, qr, 'SI_SHIPMENT', 'SINGLE_ACTION', wid)
        _seed_wsl(db_conn, fin_id, sn, qr, wid)

        resp = client.post('/api/app/work/ship-complete', json={'serial_number': sn},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 403

    def test_missing_si_task_returns_404(
            self, client, create_test_worker, get_auth_token, db_conn):
        """TC-SHIP-12: SI task 쌍이 없는 S/N → 404"""
        sn = _sn(f'12_{_TS()}')
        _seed_product(db_conn, sn)  # 제품만, SI task 없음
        token, _ = _admin(create_test_worker, get_auth_token, '12')

        resp = client.post('/api/app/work/ship-complete', json={'serial_number': sn},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 404
        assert resp.get_json()['error'] == 'SI_TASK_NOT_FOUND'


# ---------------------------------------------------------------------------
# v2.20.15 — SI 인원 출고완료 권한 확장 (manager/admin → + role='SI')
# ---------------------------------------------------------------------------

def _si_worker_token(create_test_worker, get_auth_token, tag):
    wid = create_test_worker(
        email=f'ship_si_{tag}_{_TS()}@test.com', password='Test123!',
        name=f'SI {tag}', role='SI', company='GST',
    )
    return get_auth_token(wid), wid


def _pi_worker_token(create_test_worker, get_auth_token, tag):
    wid = create_test_worker(
        email=f'ship_pi_{tag}_{_TS()}@test.com', password='Test123!',
        name=f'PI {tag}', role='PI', company='GST',
    )
    return get_auth_token(wid), wid


def _partner_manager_token(create_test_worker, get_auth_token, tag):
    wid = create_test_worker(
        email=f'ship_mgr_{tag}_{_TS()}@test.com', password='Test123!',
        name=f'MECH Manager {tag}', role='MECH', company='FNI',
        is_manager=True,
    )
    return get_auth_token(wid), wid


class TestShipCompletePermission:
    """v2.20.15 — SI 인원(role='SI', non-manager)도 출고완료 허용.
    admin-complete(PI/QI 종료)은 manager/admin 유지 → ship-complete만 SI 확장."""

    def test_si_worker_can_ship_complete(
            self, client, create_test_worker, get_auth_token, db_conn):
        """TC-SHIP-PERM-01: SI 인원(role='SI', is_manager=False)도 출고완료 200"""
        sn = _sn(f'perm01_{_TS()}')
        qr = _seed_product(db_conn, sn)
        token, wid = _si_worker_token(create_test_worker, get_auth_token, 'p01')
        fin_id = _seed_si_task(db_conn, sn, qr, 'SI_FINISHING', 'NORMAL', wid,
                               started_at="NOW() - INTERVAL '2 hours'")
        _seed_si_task(db_conn, sn, qr, 'SI_SHIPMENT', 'SINGLE_ACTION', wid)
        _seed_wsl(db_conn, fin_id, sn, qr, wid)

        resp = client.post('/api/app/work/ship-complete',
                            json={'serial_number': sn},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200, resp.get_json()
        assert resp.get_json()['si_completed'] is True

    def test_pi_worker_forbidden_ship_complete(
            self, client, create_test_worker, get_auth_token, db_conn):
        """TC-SHIP-PERM-02: PI 인원(role='PI', non-manager)은 출고완료 403"""
        sn = _sn(f'perm02_{_TS()}')
        qr = _seed_product(db_conn, sn)
        token, wid = _pi_worker_token(create_test_worker, get_auth_token, 'p02')
        fin_id = _seed_si_task(db_conn, sn, qr, 'SI_FINISHING', 'NORMAL', wid,
                               started_at="NOW() - INTERVAL '2 hours'")
        _seed_si_task(db_conn, sn, qr, 'SI_SHIPMENT', 'SINGLE_ACTION', wid)
        _seed_wsl(db_conn, fin_id, sn, qr, wid)

        resp = client.post('/api/app/work/ship-complete',
                            json={'serial_number': sn},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 403, resp.get_json()

    def test_partner_manager_can_ship_complete(
            self, client, create_test_worker, get_auth_token, db_conn):
        """TC-SHIP-PERM-03: 협력사 manager(role='MECH') 기존 출고완료 권한 유지"""
        sn = _sn(f'perm03_{_TS()}')
        qr = _seed_product(db_conn, sn)
        token, _ = _partner_manager_token(create_test_worker, get_auth_token, 'p03')
        wid = _worker(create_test_worker, 'p03')
        fin_id = _seed_si_task(db_conn, sn, qr, 'SI_FINISHING', 'NORMAL', wid,
                               started_at="NOW() - INTERVAL '2 hours'")
        _seed_si_task(db_conn, sn, qr, 'SI_SHIPMENT', 'SINGLE_ACTION', wid)
        _seed_wsl(db_conn, fin_id, sn, qr, wid)

        resp = client.post('/api/app/work/ship-complete',
                            json={'serial_number': sn},
                            headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200, resp.get_json()
        assert resp.get_json()['si_completed'] is True
