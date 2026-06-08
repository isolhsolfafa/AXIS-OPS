"""
S-2 (FEAT-CT-TRUE-UNION, VIEW OPS_API_REQUESTS #82 ⓑ) — 진짜 CT(across-worker union) pytest

설계서: CT_S2_TRUE_CT_UNION_DESIGN.md (v2, Codex 3라운드 GO M=0)

산식 (clip 먼저 → union 나중):
  worker_active_mr = (session_union ∩ BH) − (manual_pause ∪ 식사휴게)   ← 작업자별 정제 multirange (060 동일)
  M/H (active)     = Σ_worker FLOOR(length(worker_active_mr))            ← active_time_minutes
  CT  (union)      = FLOOR(length( across-worker UNION of worker_active_mr ))  ← ct_time_minutes
  저장값            = LEAST(FLOOR(union_exact), active_time_minutes)       ← A-1 (CT ≤ M/H)

단일/릴레이 → ct=active / 병렬(세션 겹침) → ct<active.

TC-S2-01~11. 식사휴게 회피 위해 13:00~16:00 KST 구간 사용(점심 11:20-12:20, 저녁 17:00-18:00 밖).
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from app.models.task_detail import compute_task_work, complete_task_unified
from app.services import statistics_service as ss

_KST = timezone(timedelta(hours=9))
_PREFIX = "S2CT"
# 2026-06-08 = 월요일(평일)
_MON = (2026, 6, 8)


def _kst(ymd, hh, mm=0):
    return datetime(ymd[0], ymd[1], ymd[2], hh, mm, tzinfo=_KST)


def _seed_task(db_conn, worker_id, started_at, completed_at=None,
               category="ELEC", task_id="WIRING", tag="A", model="GAIA-I", customer=None):
    """product + qr + app_task_details(started) + work_start_log (+completion_log)."""
    sn = f"{_PREFIX}-{tag}"
    qr = f"DOC_{sn}"
    cur = db_conn.cursor()
    cur.execute("INSERT INTO plan.product_info (serial_number, model, customer) VALUES (%s,%s,%s) "
                "ON CONFLICT (serial_number) DO UPDATE SET model=EXCLUDED.model, customer=EXCLUDED.customer",
                (sn, model, customer))
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


def _add_worker_session(db_conn, tid, sn, qr, worker_id, started_at, completed_at,
                        category="ELEC", task_id="WIRING"):
    """추가 작업자 세션 (멀티워커)."""
    cur = db_conn.cursor()
    cur.execute("""INSERT INTO work_start_log
        (task_id, worker_id, serial_number, qr_doc_id, task_category, task_id_ref, task_name, started_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""", (tid, worker_id, sn, qr, category, task_id, task_id, started_at))
    if completed_at is not None:
        cur.execute("""INSERT INTO work_completion_log
            (task_id, worker_id, serial_number, qr_doc_id, task_category, task_id_ref, task_name, completed_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""", (tid, worker_id, sn, qr, category, task_id, task_id, completed_at))
    db_conn.commit()


def _seed_pause(db_conn, tid, worker_id, paused_at, resumed_at):
    cur = db_conn.cursor()
    cur.execute("""INSERT INTO work_pause_log (task_detail_id, worker_id, paused_at, resumed_at, pause_type)
        VALUES (%s,%s,%s,%s,'manual')""", (tid, worker_id, paused_at, resumed_at))
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
    ss._cache.clear()


@pytest.fixture
def w(db_conn, create_test_worker):
    if db_conn is None:
        pytest.skip("DB 없음")
    return create_test_worker(email="s2ct@test.axisos.com", password="Test1234!",
                              name="S2CT", role="ELEC", company="P&S")


@pytest.fixture
def w2(db_conn, create_test_worker):
    if db_conn is None:
        pytest.skip("DB 없음")
    return create_test_worker(email="s2ctb@test.axisos.com", password="Test1234!",
                              name="S2CTB", role="ELEC", company="P&S")


def _work(db_conn, tid, close_at):
    cur = db_conn.cursor()
    return compute_task_work(cur, tid, close_at)


def _find(rows, key, val="task_id"):
    return next((r for r in rows if r[val] == key), None)


# ───────── TC-S2-01: 단일작업자 → ct = active ─────────

def test_s2_01_single_worker_ct_equals_active(db_conn, w):
    try:
        s, c = _kst(_MON, 13), _kst(_MON, 14)   # 13:00~14:00, 휴게 없음
        tid, *_ = _seed_task(db_conn, w, s, c)
        r = _work(db_conn, tid, c)
        assert r['manhour'] == 60 and r['active'] == 60 and r['ct'] == 60
        assert r['ct'] == r['active']  # 단일 → CT=M/H
    finally:
        _cleanup(db_conn, [w])


# ───────── TC-S2-02: 릴레이(겹침 없음) → ct ≈ active ─────────

def test_s2_02_relay_no_overlap(db_conn, w, w2):
    """A 13-14, B 15-16 → 겹침 0. active=120, ct=120 (union = 두 구간 합)."""
    try:
        a_s, a_c = _kst(_MON, 13), _kst(_MON, 14)
        b_s, b_c = _kst(_MON, 15), _kst(_MON, 16)
        tid, sn, qr = _seed_task(db_conn, w, a_s, a_c)
        _add_worker_session(db_conn, tid, sn, qr, w2, b_s, b_c)
        r = _work(db_conn, tid, c := _kst(_MON, 16))
        assert r['active'] == 120 and r['ct'] == 120
        assert r['ct'] == r['active']  # 릴레이 → CT=M/H
    finally:
        _cleanup(db_conn, [w, w2])


# ───────── TC-S2-03: 완전겹침 2명 → ct = active/2 ─────────

def test_s2_03_full_overlap(db_conn, w, w2):
    """A 13-15, B 13-15 → active 240(2×120), ct 120(union 1구간)."""
    try:
        s, c = _kst(_MON, 13), _kst(_MON, 15)
        tid, sn, qr = _seed_task(db_conn, w, s, c)
        _add_worker_session(db_conn, tid, sn, qr, w2, s, c)
        r = _work(db_conn, tid, c)
        assert r['active'] == 240, r
        assert r['ct'] == 120, r   # union = 13~15 = 120분
        assert r['ct'] == r['active'] // 2
    finally:
        _cleanup(db_conn, [w, w2])


# ───────── TC-S2-04: 부분겹침 → active 240, ct 180 ─────────

def test_s2_04_partial_overlap(db_conn, w, w2):
    """A 13:00-15:00, B 14:00-16:00 → active 240, ct 180(겹친 1h 1회)."""
    try:
        a_s, a_c = _kst(_MON, 13), _kst(_MON, 15)
        b_s, b_c = _kst(_MON, 14), _kst(_MON, 16)
        tid, sn, qr = _seed_task(db_conn, w, a_s, a_c)
        _add_worker_session(db_conn, tid, sn, qr, w2, b_s, b_c)
        r = _work(db_conn, tid, _kst(_MON, 16))
        assert r['active'] == 240, r
        assert r['ct'] == 180, r   # union = 13~16 = 180분
    finally:
        _cleanup(db_conn, [w, w2])


# ───────── TC-S2-04b: 0분 접점 → ct = active ─────────

def test_s2_04b_zero_touch_boundary(db_conn, w, w2):
    """A 13-14, B 14-15 → 경계 안 겹침 [). active 120, ct 120."""
    try:
        a_s, a_c = _kst(_MON, 13), _kst(_MON, 14)
        b_s, b_c = _kst(_MON, 14), _kst(_MON, 15)
        tid, sn, qr = _seed_task(db_conn, w, a_s, a_c)
        _add_worker_session(db_conn, tid, sn, qr, w2, b_s, b_c)
        r = _work(db_conn, tid, _kst(_MON, 15))
        assert r['active'] == 120 and r['ct'] == 120, r
    finally:
        _cleanup(db_conn, [w, w2])


# ───────── TC-S2-05: ct ≤ active 불변식 + 저장 LEAST ─────────

def test_s2_05_invariant_and_storage_least(db_conn, w, w2):
    """전 케이스 ct ≤ active. complete_task_unified 저장값 = LEAST(union, active)."""
    try:
        a_s, a_c = _kst(_MON, 13), _kst(_MON, 15)
        b_s, b_c = _kst(_MON, 14), _kst(_MON, 16)
        tid, sn, qr = _seed_task(db_conn, w, a_s, a_c)
        _add_worker_session(db_conn, tid, sn, qr, w2, b_s, b_c)
        c = _kst(_MON, 16)
        r = _work(db_conn, tid, c)
        assert r['ct'] <= r['active']
        # 저장 경로
        res = complete_task_unified(tid, c, duration_source='NORMAL_COMPLETION')
        assert res is not None
        cur = db_conn.cursor()
        cur.execute("SELECT active_time_minutes, ct_time_minutes FROM app_task_details WHERE id=%s", (tid,))
        act, ct = cur.fetchone()
        assert ct <= act
        assert ct == 180 and act == 240
    finally:
        _cleanup(db_conn, [w, w2])


# ───────── TC-S2-05b: 멀티데이 병렬 span ─────────

def test_s2_05b_multiday_overlap(db_conn, w, w2):
    """멀티데이 attendance 영업창 — 이틀 각각 출퇴근 등록 후 2일 병렬 union.

    attendance 없으면 세션이 시작일 17시로 cap 되므로, 진짜 2일 span 은
    각 날 [in,out] attendance 로 영업창을 열어줘야 한다.
    """
    tue = (2026, 6, 9)
    try:
        # 두 워커 모두 6/8 13~15, 6/9 13~15 두 세션 (완전겹침)
        a_s, a_c = _kst(_MON, 13), _kst(_MON, 15)
        tid, sn, qr = _seed_task(db_conn, w, a_s, a_c)
        _add_worker_session(db_conn, tid, sn, qr, w2, a_s, a_c)
        _add_worker_session(db_conn, tid, sn, qr, w, _kst(tue, 13), _kst(tue, 15))
        _add_worker_session(db_conn, tid, sn, qr, w2, _kst(tue, 13), _kst(tue, 15))
        for wid in (w, w2):
            cur = db_conn.cursor()
            cur.execute("INSERT INTO hr.partner_attendance (worker_id, check_type, check_time) VALUES (%s,'in',%s),(%s,'out',%s)",
                        (wid, _kst(_MON, 8), wid, _kst(_MON, 20)))
            cur.execute("INSERT INTO hr.partner_attendance (worker_id, check_type, check_time) VALUES (%s,'in',%s),(%s,'out',%s)",
                        (wid, _kst(tue, 8), wid, _kst(tue, 20)))
            db_conn.commit()
        r = _work(db_conn, tid, _kst(tue, 15))
        # 각 워커 2일 × 2h = 240, Σ active 480. 완전겹침 → ct = 240 (= active/2)
        assert r['ct'] <= r['active']
        assert r['active'] == 480, r
        assert r['ct'] == 240, r   # 2일 union, 완전겹침
    finally:
        _cleanup(db_conn, [w, w2])


# ───────── TC-S2-05c: 세션상한 캡(17시 fallback) 후 union ─────────

def test_s2_05c_session_cap_then_union(db_conn, w):
    """완료기록 없는 워커 → 시작일 17시 fallback cap. cap 후 union."""
    try:
        s = _kst(_MON, 13)   # 13:00 시작, 완료기록 없음 → 17시 cap (4h)
        tid, sn, qr = _seed_task(db_conn, w, s, completed_at=None)
        close = _kst(_MON, 20)   # close_at 늦지만 cap 17시
        r = _work(db_conn, tid, close)
        # session [13,17] (cap) ∩ BH[08,20] = 4h, 식사 17:00~ 경계밖 → active 240
        assert r['active'] == 240, r
        assert r['ct'] == 240, r   # 단일 → ct=active
    finally:
        _cleanup(db_conn, [w])


# ───────── TC-S2-05d: pause·식사 겹침 후 union ─────────

def test_s2_05d_pause_meal_then_union(db_conn, w, w2):
    """정제 multirange(pause/식사 제외) 를 union. 점심 겹침 1회 차감 검증."""
    try:
        # A 11:00-13:00 (점심 11:20-12:20 60 차감), B 11:00-13:00 동일 → 완전겹침
        s, c = _kst(_MON, 11), _kst(_MON, 13)
        tid, sn, qr = _seed_task(db_conn, w, s, c)
        _add_worker_session(db_conn, tid, sn, qr, w2, s, c)
        r = _work(db_conn, tid, c)
        # 각 워커 active = 120 − lunch 60 = 60 → Σ active 120
        # 정제구간(11~11:20, 12:20~13)을 across-worker union → 동일 구간 겹침 → ct = 60
        assert r['active'] == 120, r
        assert r['ct'] == 60, r
        assert r['ct'] <= r['active']
    finally:
        _cleanup(db_conn, [w, w2])


# ───────── TC-S2-06: basis=ct 모집단 + meta ─────────

def test_s2_06_basis_ct_population_and_meta(db_conn, w):
    """basis=ct → ct>0 모집단 + meta ct_available/basis_label + coverage 일반화."""
    _FAKE = "S2_CT_FAKE"
    try:
        # ct>0 5건 (단일작업자 → ct=active=60)
        for i in range(5):
            s, c = _kst(_MON, 13), _kst(_MON, 14)
            sn = f"{_PREFIX}-CT{i:02d}"
            qr = f"DOC_{sn}"
            cur = db_conn.cursor()
            cur.execute("INSERT INTO plan.product_info (serial_number, model) VALUES (%s,'GAIA-I') "
                        "ON CONFLICT (serial_number) DO NOTHING", (sn,))
            cur.execute("INSERT INTO qr_registry (qr_doc_id, serial_number, status) VALUES (%s,%s,'active') "
                        "ON CONFLICT (qr_doc_id) DO NOTHING", (qr, sn))
            cur.execute("""INSERT INTO app_task_details
                (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
                 started_at, completed_at, duration_minutes, active_time_minutes, ct_time_minutes, is_applicable)
                VALUES (%s,%s,%s,'MECH',%s,%s,%s,%s,60,60,60,TRUE)""",
                (w, sn, qr, _FAKE, _FAKE, s, c))
            db_conn.commit()
        # ct=0 (병렬로 0 가능성 — 명시 0) + ct NULL (미백필) 제외
        sn0 = f"{_PREFIX}-CTZERO"
        cur = db_conn.cursor()
        cur.execute("INSERT INTO plan.product_info (serial_number, model) VALUES (%s,'GAIA-I') ON CONFLICT DO NOTHING", (sn0,))
        cur.execute("INSERT INTO qr_registry (qr_doc_id, serial_number, status) VALUES (%s,%s,'active') ON CONFLICT DO NOTHING", (f"DOC_{sn0}", sn0))
        cur.execute("""INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
             started_at, completed_at, duration_minutes, active_time_minutes, ct_time_minutes, is_applicable)
            VALUES (%s,%s,%s,'MECH',%s,%s,%s,%s,200,200,0,TRUE)""",
            (w, sn0, f"DOC_{sn0}", _FAKE, _FAKE, _kst(_MON, 13), _kst(_MON, 14)))
        snN = f"{_PREFIX}-CTNULL"
        cur.execute("INSERT INTO plan.product_info (serial_number, model) VALUES (%s,'GAIA-I') ON CONFLICT DO NOTHING", (snN,))
        cur.execute("INSERT INTO qr_registry (qr_doc_id, serial_number, status) VALUES (%s,%s,'active') ON CONFLICT DO NOTHING", (f"DOC_{snN}", snN))
        cur.execute("""INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
             started_at, completed_at, duration_minutes, active_time_minutes, ct_time_minutes, is_applicable)
            VALUES (%s,%s,%s,'MECH',%s,%s,%s,%s,200,200,NULL,TRUE)""",
            (w, snN, f"DOC_{snN}", _FAKE, _FAKE, _kst(_MON, 13), _kst(_MON, 14)))
        db_conn.commit()
        ss._cache.clear()
        r = ss.get_task_ct_stats(basis="ct")
        t = _find(r["tasks"], _FAKE)
        assert t is not None and t["sample_size"] == 5, t  # ct>0 만 (zero/null 제외)
        m = r["meta"]
        assert m["basis"] == "ct"
        assert m["basis_label"] == "true CT(union)"
        assert "ct_available" in m
        # M-1: n_total = clean eligible 전체(ct 필터 전, Tukey 전) = 7
        #      n_used = ct>0 모집단(Tukey 전) = 7 − ct_zero(1) − ct_null(1) = 5
        #      n_sample = Tukey 후 산출 표본 = 5 (이상치 없음) / total_sample 하위호환
        assert m["n_total"] == 7, m["n_total"]
        assert m["n_used"] == 5, m["n_used"]
        assert m["n_sample"] == 5, m["n_sample"]
        assert m["total_sample"] == m["n_sample"]  # 하위호환 키
        assert "tracking_coverage_by_partner" in m  # coverage 일반화 (active,ct)
    finally:
        _cleanup(db_conn, [w])


# ───────── TC-S2-07: effective_concurrency_median + 0div 가드 + avg_workers ─────────

def test_s2_07_effective_concurrency_median(db_conn, w):
    """instance별 active/NULLIF(ct,0) 의 median. 완전병렬 2.0, 단일 1.0."""
    _FAKE = "S2_CC_FAKE"
    try:
        cur = db_conn.cursor()
        # 3건 완전병렬(active=240, ct=120 → ratio 2.0) + 2건 단일(active=60, ct=60 → 1.0)
        # median of [2.0,2.0,2.0,1.0,1.0] = 2.0
        specs = [(240, 120, 2)] * 3 + [(60, 60, 1)] * 2
        for i, (act, ct, wc) in enumerate(specs):
            sn = f"{_PREFIX}-CC{i:02d}"
            cur.execute("INSERT INTO plan.product_info (serial_number, model) VALUES (%s,'GAIA-I') ON CONFLICT DO NOTHING", (sn,))
            cur.execute("INSERT INTO qr_registry (qr_doc_id, serial_number, status) VALUES (%s,%s,'active') ON CONFLICT DO NOTHING", (f"DOC_{sn}", sn))
            cur.execute("""INSERT INTO app_task_details
                (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
                 started_at, completed_at, duration_minutes, active_time_minutes, ct_time_minutes, worker_count, is_applicable)
                VALUES (%s,%s,%s,'MECH',%s,%s,%s,%s,%s,%s,%s,%s,TRUE)""",
                (w, sn, f"DOC_{sn}", _FAKE, _FAKE, _kst(_MON, 13), _kst(_MON, 14), act, act, ct, wc))
        db_conn.commit()
        ss._cache.clear()
        m = ss.get_task_ct_stats(basis="ct")["meta"]
        assert m["effective_concurrency_median"] == 2.0, m["effective_concurrency_median"]
        # avg_workers = (3*2 + 2*1)/5 = 1.6
        assert m["avg_workers"] == 1.6, m["avg_workers"]
    finally:
        _cleanup(db_conn, [w])


# ───────── TC-S2-08: 백필 set-based = compute_task_work per-task 일치 + A-2 preflight ─────────

def test_s2_08_backfill_matches_compute(db_conn, w, w2):
    """migration 061 백필 산식(set-based) = compute_task_work per-task 결과 일치."""
    try:
        # 부분겹침 → ct 180, active 240
        a_s, a_c = _kst(_MON, 13), _kst(_MON, 15)
        b_s, b_c = _kst(_MON, 14), _kst(_MON, 16)
        tid, sn, qr = _seed_task(db_conn, w, a_s, a_c)
        _add_worker_session(db_conn, tid, sn, qr, w2, b_s, b_c)
        c = _kst(_MON, 16)
        # 먼저 active_time_minutes 만 채워둠 (백필 전제 — 060 적용 상태 모사)
        per = _work(db_conn, tid, c)
        cur = db_conn.cursor()
        cur.execute("UPDATE app_task_details SET completed_at=%s, duration_minutes=%s, active_time_minutes=%s WHERE id=%s",
                    (c, per['manhour'], per['active'], tid))
        db_conn.commit()
        # 백필 SQL (061 핵심 — cleaned → across-worker union, LEAST(ct, active), WHERE ct IS NULL)
        cur.execute(_BACKFILL_SQL, (sn + "%", sn + "%"))
        db_conn.commit()
        cur.execute("SELECT active_time_minutes, ct_time_minutes FROM app_task_details WHERE id=%s", (tid,))
        act, ct = cur.fetchone()
        assert act == per['active'] and ct == per['ct'], (act, ct, per)
        assert ct == 180 and act == 240
    finally:
        _cleanup(db_conn, [w, w2])


# ───────── TC-S2-09: TANK_DOCKING ct NULL (active NULL → ct NULL) ─────────

def test_s2_09_active_null_keeps_ct_null(db_conn, w):
    """active_time_minutes NULL 행 → 백필 ct 미적용(NULL 유지)."""
    try:
        sn = f"{_PREFIX}-DOCK"
        qr = f"DOC_{sn}"
        cur = db_conn.cursor()
        cur.execute("INSERT INTO plan.product_info (serial_number, model) VALUES (%s,'GAIA-I') ON CONFLICT DO NOTHING", (sn,))
        cur.execute("INSERT INTO qr_registry (qr_doc_id, serial_number, status) VALUES (%s,%s,'active') ON CONFLICT DO NOTHING", (qr, sn))
        # one-action 형태 — active NULL, ct NULL
        cur.execute("""INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
             started_at, completed_at, duration_minutes, active_time_minutes, ct_time_minutes, is_applicable)
            VALUES (%s,%s,%s,'MECH','TANK_DOCKING','TANK_DOCKING',%s,%s,0,NULL,NULL,TRUE) RETURNING id""",
            (w, sn, qr, _kst(_MON, 13), _kst(_MON, 13)))
        tid = cur.fetchone()[0]
        db_conn.commit()
        cur.execute(_BACKFILL_SQL, (sn + "%", sn + "%"))
        db_conn.commit()
        cur.execute("SELECT ct_time_minutes FROM app_task_details WHERE id=%s", (tid,))
        assert cur.fetchone()[0] is None
    finally:
        _cleanup(db_conn, [w])


# ───────── TC-S2-09b: active=0 → ct=0 (M-2: LEFT JOIN COALESCE, NULL 방치 금지) ─────────

def test_s2_09b_active_zero_backfills_ct_zero(db_conn, w):
    """M-2: active_time_minutes=0 (미추적 완료, ct_per_task 누락) → 백필 ct=0 (NULL 아님).

    이전 INNER JOIN 버전은 ct_per_task 에 tid 가 없어 active=0 행을 ct NULL 로 방치 →
    compute_task_work(live) 의 LEAST(ct_raw, active=0)=0 과 불일치. LEFT JOIN+COALESCE 0 으로 정합.
    """
    try:
        sn = f"{_PREFIX}-AZERO"
        qr = f"DOC_{sn}"
        cur = db_conn.cursor()
        cur.execute("INSERT INTO plan.product_info (serial_number, model) VALUES (%s,'GAIA-I') ON CONFLICT DO NOTHING", (sn,))
        cur.execute("INSERT INTO qr_registry (qr_doc_id, serial_number, status) VALUES (%s,%s,'active') ON CONFLICT DO NOTHING", (qr, sn))
        # active=0 완료 (영업창 밖/미추적), ct NULL 상태 → 백필 대상
        cur.execute("""INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
             started_at, completed_at, duration_minutes, active_time_minutes, ct_time_minutes, is_applicable)
            VALUES (%s,%s,%s,'MECH','WASTE_GAS_LINE_1','WASTE_GAS_LINE_1',%s,%s,30,0,NULL,TRUE) RETURNING id""",
            (w, sn, qr, _kst(_MON, 13), _kst(_MON, 14)))
        tid = cur.fetchone()[0]
        db_conn.commit()
        cur.execute(_BACKFILL_SQL, (sn + "%", sn + "%"))
        db_conn.commit()
        cur.execute("SELECT ct_time_minutes FROM app_task_details WHERE id=%s", (tid,))
        assert cur.fetchone()[0] == 0  # active=0 → ct=0 (NULL 방치 금지)
    finally:
        _cleanup(db_conn, [w])


# ───────── TC-S2-10: 회귀 — active/duration/man-hour 불변 ─────────

def test_s2_10_regression_manhour_active_unchanged(db_conn, w, w2):
    """ct 추가가 man-hour/active 산식에 영향 0."""
    try:
        # 부분겹침 — Sprint 86 active 산식 검증값과 동일해야
        a_s, a_c = _kst(_MON, 13), _kst(_MON, 15)
        b_s, b_c = _kst(_MON, 14), _kst(_MON, 16)
        tid, sn, qr = _seed_task(db_conn, w, a_s, a_c)
        _add_worker_session(db_conn, tid, sn, qr, w2, b_s, b_c)
        r = _work(db_conn, tid, _kst(_MON, 16))
        # 각 2h, 휴게 없음 → man-hour 240, active 240 (Sprint 86 불변)
        assert r['manhour'] == 240
        assert r['active'] == 240
        # ct 만 신규 (180)
        assert r['ct'] == 180
    finally:
        _cleanup(db_conn, [w, w2])


# ───────── TC-S2-11: 운영 staging smoke (PANEL 병렬 / UTIL 릴레이) ─────────

def test_s2_11_staging_smoke(db_conn, w):
    """운영 패턴 SQL 재현 — 병렬(ct<active) / 릴레이(ct≈active) compute 재현."""
    w_ids = [w]
    try:
        # PANEL_WORK 패턴: 4명 완전병렬 → ct = active/4
        s, c = _kst(_MON, 13), _kst(_MON, 17)   # 4h (식사 17:00~ 경계밖)
        tid, sn, qr = _seed_task(db_conn, w, s, c, category="ELEC", task_id="PANEL_WORK")
        for i in range(3):
            wn = _ensure_extra_worker(db_conn, i)
            w_ids.append(wn)
            _add_worker_session(db_conn, tid, sn, qr, wn, s, c, category="ELEC", task_id="PANEL_WORK")
        r = _work(db_conn, tid, c)
        # 4명 완전병렬 → active = 4 × 240 = 960, ct = 240 (union 1구간)
        assert r['active'] == 960, r
        assert r['ct'] == 240, r
        assert r['ct'] < r['active']  # 병렬 = CT < M/H

        # UTIL_LINE 릴레이 패턴: 겹침 없는 4명 교대 → ct ≈ active
        u_tid, u_sn, u_qr = _seed_task(db_conn, w, _kst(_MON, 13), _kst(_MON, 14),
                                       category="ELEC", task_id="UTIL_LINE", tag="UTIL")
        hours = [(14, 15), (15, 16), (16, 17)]
        for i, (hs, he) in enumerate(hours):
            wn = w_ids[i + 1]
            _add_worker_session(db_conn, u_tid, u_sn, u_qr, wn, _kst(_MON, hs), _kst(_MON, he),
                                category="ELEC", task_id="UTIL_LINE")
        ru = _work(db_conn, u_tid, _kst(_MON, 17))
        # 4명 × 1h 릴레이(겹침 0) → active 240, ct 240
        assert ru['active'] == 240, ru
        assert ru['ct'] == 240, ru   # 릴레이 = CT ≈ M/H
    finally:
        _cleanup(db_conn, w_ids)
        _cleanup_extra_workers(db_conn)


# ── staging smoke helper ──
_EXTRA_WORKER_EMAILS = []


def _ensure_extra_worker(db_conn, idx):
    """PANEL smoke 용 추가 작업자 직접 INSERT (worker fixture 외)."""
    cur = db_conn.cursor()
    email = f"s2ct_extra{idx}@test.axisos.com"
    cur.execute("SELECT id FROM workers WHERE email=%s", (email,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        "INSERT INTO workers (name, email, password_hash, role, company, approval_status, email_verified) "
        "VALUES (%s,%s,'x','ELEC','P&S','approved',TRUE) RETURNING id",
        (f"S2EX{idx}", email),
    )
    wid = cur.fetchone()[0]
    db_conn.commit()
    _EXTRA_WORKER_EMAILS.append(email)
    return wid


def _cleanup_extra_workers(db_conn):
    if not _EXTRA_WORKER_EMAILS:
        return
    cur = db_conn.cursor()
    cur.execute("DELETE FROM workers WHERE email = ANY(%s)", (_EXTRA_WORKER_EMAILS,))
    db_conn.commit()
    _EXTRA_WORKER_EMAILS.clear()


# 백필 SQL (migration 061 핵심 — 단일 S/N prefix 대상으로 좁힌 버전).
# cleaned(작업자별 정제 multirange) → across-worker range_agg union 길이 → LEAST(ct, active).
_BACKFILL_SQL = """
WITH starts AS (
  SELECT td.id AS tid, td.completed_at AS close_at, ws.worker_id, ws.started_at,
         LEAD(ws.started_at) OVER (PARTITION BY td.id, ws.worker_id ORDER BY ws.started_at) AS next_start,
         (SELECT MIN(wc.completed_at) FROM work_completion_log wc
            WHERE wc.task_id = td.id AND wc.worker_id = ws.worker_id
              AND wc.completed_at >= ws.started_at) AS comp,
         (SELECT MAX(pa.check_time) FROM hr.partner_attendance pa
            WHERE pa.worker_id = ws.worker_id AND pa.check_type = 'out'
              AND DATE(pa.check_time AT TIME ZONE 'Asia/Seoul')
                  = DATE(ws.started_at AT TIME ZONE 'Asia/Seoul')) AS checkout
  FROM app_task_details td
  JOIN work_start_log ws ON ws.task_id = td.id
  WHERE td.completed_at IS NOT NULL
    AND ws.started_at < td.completed_at
    AND td.serial_number LIKE %s
),
sessions AS (
  SELECT tid, close_at, worker_id,
         tstzrange(started_at,
           GREATEST(started_at, LEAST(
             COALESCE(comp, 'infinity'::timestamptz),
             COALESCE(checkout, 'infinity'::timestamptz),
             CASE WHEN checkout IS NULL
                  THEN (date_trunc('day', started_at AT TIME ZONE 'Asia/Seoul') + interval '17 hours') AT TIME ZONE 'Asia/Seoul'
                  ELSE 'infinity'::timestamptz END,
             COALESCE(next_start, 'infinity'::timestamptz),
             close_at
           )), '[)') AS sess
  FROM starts
),
sess_union AS (SELECT tid, close_at, worker_id, range_agg(sess) AS mr FROM sessions GROUP BY tid, close_at, worker_id),
pauses AS (
  SELECT su.tid, wpl.worker_id, tstzrange(wpl.paused_at, COALESCE(wpl.resumed_at, su.close_at), '[)') AS pr
  FROM sess_union su
  JOIN work_pause_log wpl ON wpl.task_detail_id = su.tid AND wpl.worker_id = su.worker_id
  WHERE wpl.pause_type = 'manual' AND wpl.paused_at < su.close_at
    AND COALESCE(wpl.resumed_at, su.close_at) > wpl.paused_at
),
pause_union AS (SELECT tid, worker_id, range_agg(pr) AS mr FROM pauses GROUP BY tid, worker_id),
days AS (
  SELECT su.tid, su.worker_id,
         generate_series(date_trunc('day', lower(su.mr) AT TIME ZONE 'Asia/Seoul'),
                         date_trunc('day', upper(su.mr) AT TIME ZONE 'Asia/Seoul'),
                         interval '1 day')::date AS d
  FROM sess_union su
),
att_day AS (
  SELECT dd.tid, dd.worker_id, dd.d,
    MIN(pa.check_time) FILTER (WHERE pa.check_type='in')  AS cin,
    MAX(pa.check_time) FILTER (WHERE pa.check_type='out') AS cout
  FROM days dd
  LEFT JOIN hr.partner_attendance pa
    ON pa.worker_id = dd.worker_id AND DATE(pa.check_time AT TIME ZONE 'Asia/Seoul') = dd.d
  GROUP BY dd.tid, dd.worker_id, dd.d
),
bh_day AS (
  SELECT tid, worker_id,
    CASE
      WHEN cin IS NOT NULL AND cout IS NOT NULL AND cin < cout THEN tstzrange(cin, cout, '[)')
      WHEN extract(dow from d) IN (0,6)
        THEN tstzrange((d + time '08:00') AT TIME ZONE 'Asia/Seoul', (d + time '17:00') AT TIME ZONE 'Asia/Seoul', '[)')
      ELSE tstzrange((d + time '08:00') AT TIME ZONE 'Asia/Seoul', (d + time '20:00') AT TIME ZONE 'Asia/Seoul', '[)')
    END AS bhr
  FROM att_day
),
bh_union AS (SELECT tid, worker_id, range_agg(bhr) AS mr FROM bh_day GROUP BY tid, worker_id),
breaks_day AS (
  SELECT tid, worker_id, unnest(ARRAY[
    tstzrange((d + time '11:20') AT TIME ZONE 'Asia/Seoul', (d + time '12:20') AT TIME ZONE 'Asia/Seoul','[)'),
    tstzrange((d + time '17:00') AT TIME ZONE 'Asia/Seoul', (d + time '18:00') AT TIME ZONE 'Asia/Seoul','[)')
  ]) AS br
  FROM days
),
breaks_union AS (SELECT tid, worker_id, range_agg(br) AS mr FROM breaks_day GROUP BY tid, worker_id),
cleaned AS (
  SELECT su.tid, su.worker_id,
    ( (su.mr * COALESCE(bh.mr, '{}'::tstzmultirange))
      - (COALESCE(pu.mr,'{}'::tstzmultirange) + COALESCE(bk.mr,'{}'::tstzmultirange)) ) AS amr
  FROM sess_union su
  LEFT JOIN pause_union pu USING(tid, worker_id)
  LEFT JOIN bh_union bh USING(tid, worker_id)
  LEFT JOIN breaks_union bk USING(tid, worker_id)
),
ranges AS (SELECT tid, r FROM cleaned, unnest(amr) r),
ct_per_task AS (
  SELECT tid,
    COALESCE((SELECT SUM(EXTRACT(EPOCH FROM (upper(g)-lower(g)))/60)
              FROM unnest(range_agg(r)) g),0)::numeric AS ct_raw_min
  FROM ranges GROUP BY tid
)
UPDATE app_task_details td
SET ct_time_minutes = LEAST(COALESCE(FLOOR(cpt.ct_raw_min)::int, 0), td.active_time_minutes)
FROM (SELECT id FROM app_task_details
      WHERE serial_number LIKE %s
        AND active_time_minutes IS NOT NULL AND ct_time_minutes IS NULL) elig
LEFT JOIN ct_per_task cpt ON cpt.tid = elig.id
WHERE td.id = elig.id
"""
