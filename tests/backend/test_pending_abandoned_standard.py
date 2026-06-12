"""
FEAT-PENDING-DISCIPLINE-REFINE (2026-06-13, Codex 2라운드 GO) — 방치 단일 기준 pytest

ABANDONED_WHERE_SQL (pending_task_standard) 직접 검증 + is_task_active_recent.
TC-AB-01~06: 24h 경계 / 일시정지 제외 / 재개 리셋 / 멀티워커 / audit 판정.
"""
from __future__ import annotations

import pytest

from app.services.pending_task_standard import ABANDONED_WHERE_SQL, is_task_active_recent

_PREFIX = "S91AB"


def _seed_task(db_conn, worker_id, sn, *, start_hours_ago=30):
    cur = db_conn.cursor()
    cur.execute(
        "INSERT INTO plan.product_info (serial_number, model, mech_partner) VALUES (%s,'GAIA-I','BAT') "
        "ON CONFLICT (serial_number) DO NOTHING", (sn,))
    cur.execute(
        "INSERT INTO qr_registry (qr_doc_id, serial_number, status) VALUES (%s,%s,'active') "
        "ON CONFLICT (qr_doc_id) DO NOTHING", (f"DOC_{sn}", sn))
    cur.execute(
        f"""INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
             started_at, completed_at, is_applicable, force_closed)
            VALUES (%s,%s,%s,'MECH','WASTE_GAS_LINE_1','t',
                    now() - interval '{int(start_hours_ago)} hours', NULL, TRUE, FALSE)
            RETURNING id""",
        (worker_id, sn, f"DOC_{sn}"))
    tid = cur.fetchone()[0]
    cur.execute(
        f"INSERT INTO work_start_log (task_id, worker_id, serial_number, qr_doc_id, "
        f"task_category, task_id_ref, task_name, started_at) "
        f"VALUES (%s,%s,%s,%s,'MECH','WASTE_GAS_LINE_1','t', now() - interval '{int(start_hours_ago)} hours')",
        (tid, worker_id, sn, f"DOC_{sn}"))
    db_conn.commit()
    return tid


def _pause(db_conn, tid, worker_id, *, resumed_hours_ago=None):
    cur = db_conn.cursor()
    if resumed_hours_ago is None:
        cur.execute(
            "INSERT INTO work_pause_log (task_detail_id, worker_id, paused_at) "
            "VALUES (%s,%s, now() - interval '1 hour')", (tid, worker_id))
    else:
        cur.execute(
            f"INSERT INTO work_pause_log (task_detail_id, worker_id, paused_at, resumed_at) "
            f"VALUES (%s,%s, now() - interval '{int(resumed_hours_ago)+1} hours', "
            f"now() - interval '{int(resumed_hours_ago)} hours')", (tid, worker_id))
    db_conn.commit()


def _is_abandoned(db_conn, tid) -> bool:
    cur = db_conn.cursor()
    cur.execute(
        f"SELECT 1 FROM app_task_details t WHERE t.id = %s AND {ABANDONED_WHERE_SQL}", (tid,))
    return cur.fetchone() is not None


def _cleanup(db_conn):
    try:
        db_conn.rollback()
    except Exception:
        pass
    cur = db_conn.cursor()
    cur.execute("DELETE FROM work_pause_log WHERE task_detail_id IN "
                "(SELECT id FROM app_task_details WHERE serial_number LIKE %s)", (f"{_PREFIX}%",))
    cur.execute("DELETE FROM work_start_log WHERE serial_number LIKE %s", (f"{_PREFIX}%",))
    cur.execute("DELETE FROM app_task_details WHERE serial_number LIKE %s", (f"{_PREFIX}%",))
    cur.execute("DELETE FROM qr_registry WHERE serial_number LIKE %s", (f"{_PREFIX}%",))
    cur.execute("DELETE FROM plan.product_info WHERE serial_number LIKE %s", (f"{_PREFIX}%",))
    db_conn.commit()


@pytest.fixture
def worker(db_conn, create_test_worker):
    if db_conn is None:
        pytest.skip("DB 없음")
    return create_test_worker(email="s91ab@test.axisos.com", password="Test1234!",
                              name="S91AB", role="MECH", company="BAT")


@pytest.fixture(autouse=True)
def _clean(db_conn):
    if db_conn is None:
        pytest.skip("DB 없음")
    _cleanup(db_conn)
    yield
    _cleanup(db_conn)


def test_ab01_abandoned_after_24h(db_conn, worker):
    tid = _seed_task(db_conn, worker, f"{_PREFIX}-01", start_hours_ago=30)
    assert _is_abandoned(db_conn, tid) is True


def test_ab02_fresh_task_not_abandoned(db_conn, worker):
    tid = _seed_task(db_conn, worker, f"{_PREFIX}-02", start_hours_ago=2)
    assert _is_abandoned(db_conn, tid) is False  # 24h 미만 = 진행중


def test_ab03_paused_excluded(db_conn, worker):
    tid = _seed_task(db_conn, worker, f"{_PREFIX}-03", start_hours_ago=30)
    _pause(db_conn, tid, worker)  # 활성 pause (resumed NULL)
    assert _is_abandoned(db_conn, tid) is False  # 일시정지 = 의도적 hold, 방치 아님


def test_ab04_resume_resets_timer(db_conn, worker):
    tid = _seed_task(db_conn, worker, f"{_PREFIX}-04", start_hours_ago=48)
    _pause(db_conn, tid, worker, resumed_hours_ago=2)  # 2h 전 재개 = 활동
    assert _is_abandoned(db_conn, tid) is False  # 재개가 타이머 리셋 (Codex M-1/M-2)


def test_ab05_old_resume_still_abandoned(db_conn, worker):
    tid = _seed_task(db_conn, worker, f"{_PREFIX}-05", start_hours_ago=72)
    _pause(db_conn, tid, worker, resumed_hours_ago=30)  # 재개 후 또 30h 방치
    assert _is_abandoned(db_conn, tid) is True


def test_ab06_active_recent_audit_flag(db_conn, worker):
    """force-close audit 태그 판정 — 활성+24h내 활동 = True / 방치 = False."""
    cur = db_conn.cursor()
    fresh = _seed_task(db_conn, worker, f"{_PREFIX}-06a", start_hours_ago=2)
    stale = _seed_task(db_conn, worker, f"{_PREFIX}-06b", start_hours_ago=30)
    assert is_task_active_recent(cur, fresh) is True   # 진행중 닫음 → [활동중 종료] 태그
    assert is_task_active_recent(cur, stale) is False  # 방치 닫음 → 태그 없음
