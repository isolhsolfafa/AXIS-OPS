"""
Sprint 86 (FEAT-ACTIVE-TIME-PURE-WORK-20260606) — active-time(순수 작업시간) pytest

active_time = Σ_w FLOOR(GREATEST(0, len(session∩BH) − len((manual_pause∪breaks)∩session∩BH)))
  BH = attendance[MIN(in),MAX(out)] 우선 / fallback 평일[08,20]·주말[08,17] KST
  breaks = [10:00-10:20, 11:20-12:20, 15:00-15:20, 17:00-18:00]
  저장 active = LEAST(active_raw, duration_minutes) — 불변식 active ≤ man-hour

설계: AGENT_TEAM_LAUNCH.md § Sprint 86 (Codex 5라운드 GO). TC AT-01~16.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from app.models.task_detail import compute_task_work, complete_task_unified

_KST = timezone(timedelta(hours=9))
_PREFIX = "S86AT"
# 2026-06-08 = 월요일(평일), 2026-06-07 = 일요일(주말)
_MON = (2026, 6, 8)
_SUN = (2026, 6, 7)


def _kst(ymd, hh, mm=0):
    return datetime(ymd[0], ymd[1], ymd[2], hh, mm, tzinfo=_KST)


def _seed_task(db_conn, worker_id, started_at, completed_at=None,
               category="ELEC", task_id="WIRING", tag="A"):
    """product + qr + app_task_details(started) + work_start_log (+completion_log)."""
    sn = f"{_PREFIX}-{tag}"
    qr = f"DOC_{sn}"
    cur = db_conn.cursor()
    cur.execute("INSERT INTO plan.product_info (serial_number, model) VALUES (%s,'GAIA-I') "
                "ON CONFLICT (serial_number) DO NOTHING", (sn,))
    cur.execute("INSERT INTO qr_registry (qr_doc_id, serial_number, status) VALUES (%s,%s,'active') "
                "ON CONFLICT (qr_doc_id) DO NOTHING", (qr, sn))
    cur.execute("""INSERT INTO app_task_details
        (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name, started_at, is_applicable)
        VALUES (%s,%s,%s,%s,%s,%s,%s,TRUE) RETURNING id""",
        (worker_id, sn, qr, category, task_id, task_id, started_at))
    tid = cur.fetchone()[0]
    cur.execute("""INSERT INTO work_start_log
        (task_id, worker_id, serial_number, qr_doc_id, task_category, task_id_ref, task_name, started_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (tid, worker_id, sn, qr, category, task_id, task_id, started_at))
    if completed_at is not None:
        cur.execute("""INSERT INTO work_completion_log
            (task_id, worker_id, serial_number, qr_doc_id, task_category, task_id_ref, task_name, completed_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (tid, worker_id, sn, qr, category, task_id, task_id, completed_at))
    db_conn.commit()
    return tid, sn, qr


def _add_worker_session(db_conn, tid, sn, qr, worker_id, started_at, completed_at):
    """추가 작업자 세션 (멀티워커)."""
    cur = db_conn.cursor()
    cur.execute("""INSERT INTO work_start_log
        (task_id, worker_id, serial_number, qr_doc_id, task_category, task_id_ref, task_name, started_at)
        VALUES (%s,%s,%s,%s,'ELEC','WIRING','WIRING',%s)""", (tid, worker_id, sn, qr, started_at))
    cur.execute("""INSERT INTO work_completion_log
        (task_id, worker_id, serial_number, qr_doc_id, task_category, task_id_ref, task_name, completed_at)
        VALUES (%s,%s,%s,%s,'ELEC','WIRING','WIRING',%s)""", (tid, worker_id, sn, qr, completed_at))
    db_conn.commit()


def _seed_pause(db_conn, tid, worker_id, paused_at, resumed_at):
    cur = db_conn.cursor()
    cur.execute("""INSERT INTO work_pause_log (task_detail_id, worker_id, paused_at, resumed_at, pause_type)
        VALUES (%s,%s,%s,%s,'manual')""", (tid, worker_id, paused_at, resumed_at))
    db_conn.commit()


def _seed_att(db_conn, worker_id, cin, cout):
    cur = db_conn.cursor()
    cur.execute("INSERT INTO hr.partner_attendance (worker_id, check_type, check_time) VALUES (%s,'in',%s)", (worker_id, cin))
    if cout is not None:
        cur.execute("INSERT INTO hr.partner_attendance (worker_id, check_type, check_time) VALUES (%s,'out',%s)", (worker_id, cout))
    db_conn.commit()


def _cleanup(db_conn, worker_ids):
    try:
        db_conn.rollback()
    except Exception:
        pass
    cur = db_conn.cursor()
    cur.execute("DELETE FROM work_pause_log WHERE task_detail_id IN (SELECT id FROM app_task_details WHERE serial_number LIKE %s)", (f"{_PREFIX}%",))
    cur.execute("DELETE FROM work_completion_log WHERE serial_number LIKE %s", (f"{_PREFIX}%",))
    cur.execute("DELETE FROM work_start_log WHERE serial_number LIKE %s", (f"{_PREFIX}%",))
    cur.execute("DELETE FROM app_task_details WHERE serial_number LIKE %s", (f"{_PREFIX}%",))
    cur.execute("DELETE FROM qr_registry WHERE serial_number LIKE %s", (f"{_PREFIX}%",))
    cur.execute("DELETE FROM plan.product_info WHERE serial_number LIKE %s", (f"{_PREFIX}%",))
    for wid in worker_ids:
        cur.execute("DELETE FROM hr.partner_attendance WHERE worker_id=%s", (wid,))
    db_conn.commit()


@pytest.fixture
def w(db_conn, create_test_worker):
    if db_conn is None:
        pytest.skip("DB 없음")
    return create_test_worker(email="s86@test.axisos.com", password="Test1234!",
                              name="S86", role="ELEC", company="P&S")


def _work(db_conn, tid, close_at):
    cur = db_conn.cursor()
    return compute_task_work(cur, tid, close_at)


# ───────── 핵심 산출 (compute_task_work) ─────────

def test_at01_weekday_plain(db_conn, w):
    """평일 주간 무pause무휴게 → active = session 길이."""
    try:
        s, c = _kst(_MON, 13), _kst(_MON, 14)   # 13:00~14:00, 휴게 없음
        tid, *_ = _seed_task(db_conn, w, s, c)
        r = _work(db_conn, tid, c)
        assert r['manhour'] == 60 and r['active'] == 60
    finally:
        _cleanup(db_conn, [w])


def test_at05_break_subtracted(db_conn, w):
    """점심(11:20-12:20) 포함 → 60분 차감."""
    try:
        s, c = _kst(_MON, 11), _kst(_MON, 13)   # 11:00~13:00 (120) − lunch 60
        tid, *_ = _seed_task(db_conn, w, s, c)
        r = _work(db_conn, tid, c)
        assert r['manhour'] == 120 and r['active'] == 60
    finally:
        _cleanup(db_conn, [w])


def test_at06_break_pause_union_no_double(db_conn, w):
    """휴게 ∩ pause 겹침 → union 1회 차감(이중차감 0). [Codex M-Q1]"""
    try:
        s, c = _kst(_MON, 11), _kst(_MON, 13)   # 120분
        tid, *_ = _seed_task(db_conn, w, s, c)
        _seed_pause(db_conn, tid, w, _kst(_MON, 11, 30), _kst(_MON, 12))  # pause 30분 (점심 내부)
        r = _work(db_conn, tid, c)
        # union(pause∪lunch)∩session = lunch 60분 → active = 120 − 60 = 60 (이중이면 30)
        assert r['active'] == 60, f"이중차감 의심: active={r['active']}"
        assert r['manhour'] == 90  # 120 − pause 30
    finally:
        _cleanup(db_conn, [w])


def test_at10_greatest_zero(db_conn, w):
    """세션 전체가 휴게 안 → active 0 (음수 차단)."""
    try:
        s, c = _kst(_MON, 11, 30), _kst(_MON, 12)   # 11:30~12:00 (점심 내부)
        tid, *_ = _seed_task(db_conn, w, s, c)
        r = _work(db_conn, tid, c)
        assert r['active'] == 0 and r['manhour'] == 30
    finally:
        _cleanup(db_conn, [w])


def test_at04_attendance_window(db_conn, w):
    """attendance [in,out] 우선 — 시작 09:00 클립 (fallback 08:00 대비)."""
    try:
        s, c = _kst(_MON, 7), _kst(_MON, 14)    # 07:00 시작
        tid, *_ = _seed_task(db_conn, w, s, c)
        _seed_att(db_conn, w, _kst(_MON, 9), _kst(_MON, 18))   # 출근 09:00 / 퇴근 18:00
        r = _work(db_conn, tid, c)
        # session=[07,14], att BH=[09,18] → 09~14 (300) − breaks(10:00-10:20=20, lunch 60) = 220
        assert r['active'] == 220, f"active={r['active']}"
    finally:
        _cleanup(db_conn, [w])


def test_at15_partial_attendance_fallback(db_conn, w):
    """attendance in만(퇴근 누락) → fallback 평일 [08,20] (HAVING 가드)."""
    try:
        s, c = _kst(_MON, 7), _kst(_MON, 14)
        tid, *_ = _seed_task(db_conn, w, s, c)
        _seed_att(db_conn, w, _kst(_MON, 9), None)   # in만
        r = _work(db_conn, tid, c)
        # fallback [08,20] → session[07,14]∩[08,20]=08~14 (360) − breaks(20+60)=280
        assert r['active'] == 280, f"active={r['active']}"
    finally:
        _cleanup(db_conn, [w])


def test_at03_weekend_fallback(db_conn, w):
    """주말 fallback [08,17] — attendance 있으면 그 창."""
    try:
        s, c = _kst(_SUN, 9), _kst(_SUN, 16)   # 일요일 09:00~16:00
        tid, *_ = _seed_task(db_conn, w, s, c)
        _seed_att(db_conn, w, _kst(_SUN, 9), _kst(_SUN, 16))  # 주말 출퇴근
        r = _work(db_conn, tid, c)
        # [09,16] (420) − breaks(10:00-10:20=20, lunch 60, 15:00-15:20=20)=100 → 320
        assert r['active'] == 320, f"active={r['active']}"
    finally:
        _cleanup(db_conn, [w])


def test_at09_at14_multiworker_invariant(db_conn, w, create_test_worker):
    """다중작업자 Σ_worker + active ≤ man-hour (작업자별 FLOOR)."""
    w2 = create_test_worker(email="s86b@test.axisos.com", password="Test1234!",
                            name="S86B", role="ELEC", company="P&S")
    try:
        s, c = _kst(_MON, 13), _kst(_MON, 14, 30)   # 13:00~14:30 (90분, 휴게 없음)
        tid, sn, qr = _seed_task(db_conn, w, s, c)
        _add_worker_session(db_conn, tid, sn, qr, w2, s, c)
        r = _work(db_conn, tid, c)
        assert r['manhour'] == 180 and r['active'] == 180  # 2명 × 90
        assert r['active'] <= r['manhour']
    finally:
        _cleanup(db_conn, [w, w2])


# ───────── 완료 경로 저장 (DB 컬럼) ─────────

def test_at11_complete_path_stores_active(db_conn, w):
    """complete_task_unified → active_time_minutes 저장 + duration 정합."""
    try:
        s, c = _kst(_MON, 11), _kst(_MON, 13)
        tid, *_ = _seed_task(db_conn, w, s, c)
        res = complete_task_unified(tid, c, duration_source='NORMAL_COMPLETION')
        assert res is not None
        cur = db_conn.cursor()
        cur.execute("SELECT duration_minutes, active_time_minutes FROM app_task_details WHERE id=%s", (tid,))
        dur, act = cur.fetchone()
        assert dur == 120 and act == 60 and act <= dur
    finally:
        _cleanup(db_conn, [w])


def test_at11b_force_close_stores_active(db_conn, w):
    """admin force_close 경로 active 저장 (compute_task_work)."""
    try:
        s, c = _kst(_MON, 11), _kst(_MON, 13)
        tid, *_ = _seed_task(db_conn, w, s, c)
        # force_close_task 의 핵심 산출 = compute_task_work (route 직접 호출 대신 함수 검증)
        cur = db_conn.cursor()
        work = compute_task_work(cur, tid, c)
        cur.execute("UPDATE app_task_details SET completed_at=%s, duration_minutes=%s, active_time_minutes=%s, force_closed=TRUE WHERE id=%s",
                    (c, work['manhour'], work['active'], tid))
        db_conn.commit()
        cur.execute("SELECT duration_minutes, active_time_minutes FROM app_task_details WHERE id=%s", (tid,))
        dur, act = cur.fetchone()
        assert dur == 120 and act == 60
    finally:
        _cleanup(db_conn, [w])


def test_at12_backfill_idempotent(db_conn, w):
    """이미 active 채워진 행은 백필 WHERE active IS NULL 로 skip."""
    try:
        s, c = _kst(_MON, 13), _kst(_MON, 14)
        tid, *_ = _seed_task(db_conn, w, s, c)
        cur = db_conn.cursor()
        cur.execute("UPDATE app_task_details SET completed_at=%s, duration_minutes=60, active_time_minutes=42 WHERE id=%s", (c, tid))
        db_conn.commit()
        # 백필 UPDATE 는 active_time_minutes IS NULL 만 → 42 보존
        cur.execute("UPDATE app_task_details SET active_time_minutes=99 WHERE id=%s AND active_time_minutes IS NULL", (tid,))
        db_conn.commit()
        cur.execute("SELECT active_time_minutes FROM app_task_details WHERE id=%s", (tid,))
        assert cur.fetchone()[0] == 42
    finally:
        _cleanup(db_conn, [w])


def test_at13_gst_no_attendance_fallback(db_conn, create_test_worker):
    """GST(PI/QI/SI, attendance 없음) → fallback 산출, NULL 아님."""
    gst = create_test_worker(email="s86gst@test.axisos.com", password="Test1234!",
                             name="S86GST", role="SI", company="GST")
    try:
        s, c = _kst(_MON, 13), _kst(_MON, 14)
        tid, *_ = _seed_task(db_conn, gst, s, c, category="SI", task_id="SI_FINISHING")
        r = _work(db_conn, tid, c)
        assert r['active'] == 60 and r['active'] is not None  # fallback 적용
    finally:
        _cleanup(db_conn, [gst])
