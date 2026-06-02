"""
FIX-DURATION-MANUAL-PAUSE-RAW-20260602 (v2.22.0) — man-hour interval-union 검증

man-hour = per-worker interval-union(세션) − (수동 pause ∩ session_union)
  · 휴게(break_*) 미차감 (원본 데이터 적재)
  · pause_type='manual' 만 차감 (positive 필터)
  · auto-close 미완 세션/미완 pause 는 close_at clamp
  · worker 별 FLOOR 후 합산

설계: AGENT_TEAM_LAUNCH.md § FIX-DURATION-MANUAL-PAUSE-RAW (Codex 라운드 1~8 GO)
프로덕션 데이터 보호: TEST_DUR_ prefix 만 사용.
"""
import time
from datetime import datetime, timedelta, timezone

import pytest

from app.models.task_detail import compute_task_manhour, complete_task_unified

_PREFIX = 'TEST_DUR_'
_KST = timezone(timedelta(hours=9))
_TS = lambda: str(int(time.time() * 1000))


def _sn(suffix: str) -> str:
    return f'{_PREFIX}{suffix}'


def _dt(y=2026, mo=6, d=2, h=0, mi=0, s=0):
    return datetime(y, mo, d, h, mi, s, tzinfo=_KST)


@pytest.fixture(autouse=True)
def cleanup_dur(db_conn):
    yield
    if db_conn and not db_conn.closed:
        try:
            cur = db_conn.cursor()
            # work_pause_log 는 serial_number 없음 → task_detail_id 기준 삭제
            cur.execute("""
                DELETE FROM work_pause_log WHERE task_detail_id IN (
                    SELECT id FROM app_task_details WHERE serial_number LIKE %s)
            """, (f'{_PREFIX}%',))
            for t in ('work_completion_log', 'work_start_log',
                      'app_task_details', 'completion_status', 'qr_registry'):
                cur.execute(f"DELETE FROM {t} WHERE serial_number LIKE %s", (f'{_PREFIX}%',))
            cur.execute("DELETE FROM plan.product_info WHERE serial_number LIKE %s", (f'{_PREFIX}%',))
            # 테스트 전용 worker 정리 (실계정은 email prefix 로 격리 — 9000+ id)
            cur.execute("DELETE FROM workers WHERE email LIKE %s", (f'{_PREFIX}%',))
            db_conn.commit()
            cur.close()
        except Exception:
            try:
                db_conn.rollback()
            except Exception:
                pass


# ─── seed helpers ───────────────────────────────────────────────

def _ensure_worker(db_conn, wid, role='MECH'):
    """테스트 worker 보장 (9000+ id, TEST_DUR_ email — 실계정과 격리)."""
    cur = db_conn.cursor()
    cur.execute("""
        INSERT INTO workers (id, name, email, password_hash, role, company,
                             approval_status, email_verified)
        VALUES (%s, %s, %s, 'x', %s, 'FNI', 'approved', TRUE)
        ON CONFLICT (id) DO NOTHING
    """, (wid, f'durw{wid}', f'{_PREFIX}{wid}@test.com', role))
    db_conn.commit()
    cur.close()


def _seed_product(db_conn, sn, model='GAIA-I'):
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


def _seed_task(db_conn, sn, qr, worker_id, started_at=None, category='MECH', task_id='UTIL_LINE_1'):
    _ensure_worker(db_conn, worker_id)
    cur = db_conn.cursor()
    cur.execute("""
        INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
             is_applicable, task_type, started_at)
        VALUES (%s, %s, %s, %s, %s, %s, TRUE, 'NORMAL', %s)
        RETURNING id
    """, (worker_id, sn, qr, category, task_id, task_id, started_at))
    tid = cur.fetchone()[0]
    db_conn.commit()
    cur.close()
    return tid


def _seed_wsl(db_conn, tid, sn, qr, worker_id, started_at, category='MECH', task_id='UTIL_LINE_1'):
    _ensure_worker(db_conn, worker_id)
    cur = db_conn.cursor()
    cur.execute("""
        INSERT INTO work_start_log
            (task_id, worker_id, serial_number, qr_doc_id, task_category,
             task_id_ref, task_name, started_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (tid, worker_id, sn, qr, category, task_id, task_id, started_at))
    db_conn.commit()
    cur.close()


def _seed_wcl(db_conn, tid, sn, qr, worker_id, completed_at, duration=0,
              category='MECH', task_id='UTIL_LINE_1'):
    cur = db_conn.cursor()
    cur.execute("""
        INSERT INTO work_completion_log
            (task_id, worker_id, serial_number, qr_doc_id, task_category,
             task_id_ref, task_name, completed_at, duration_minutes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (tid, worker_id, sn, qr, category, task_id, task_id, completed_at, duration))
    db_conn.commit()
    cur.close()


def _seed_pause(db_conn, tid, worker_id, paused_at, resumed_at, pause_type='manual'):
    cur = db_conn.cursor()
    dur = None
    if resumed_at is not None:
        dur = int((resumed_at - paused_at).total_seconds() / 60)
    cur.execute("""
        INSERT INTO work_pause_log
            (task_detail_id, worker_id, paused_at, resumed_at, pause_type, pause_duration_minutes)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (tid, worker_id, paused_at, resumed_at, pause_type, dur))
    db_conn.commit()
    cur.close()


def _manhour(db_conn, tid, close_at):
    cur = db_conn.cursor()
    v = compute_task_manhour(cur, tid, close_at)
    cur.close()
    return v


# ─── 그룹 1: 기본 공식 (단일 작업자) ───────────────────────────────

def test_dp01_pause_clamped_in_session(db_conn):
    """DP-01: 08:00 시작→09:00 정지→15:00 재개→16:00 완료 → 480−360=120"""
    sn = _sn('01'); qr = _seed_product(db_conn, sn); w = 9001
    st, ct = _dt(h=8), _dt(h=16)
    tid = _seed_task(db_conn, sn, qr, w, started_at=st)
    _seed_wsl(db_conn, tid, sn, qr, w, st)
    _seed_wcl(db_conn, tid, sn, qr, w, ct)
    _seed_pause(db_conn, tid, w, _dt(h=9), _dt(h=15))  # 360분 manual
    assert _manhour(db_conn, tid, ct) == 120


def test_dp02_single_session_no_pause(db_conn):
    """DP-02: 10:00~12:00, pause 없음 → raw 120"""
    sn = _sn('02'); qr = _seed_product(db_conn, sn); w = 9002
    st, ct = _dt(h=10), _dt(h=12)
    tid = _seed_task(db_conn, sn, qr, w, started_at=st)
    _seed_wsl(db_conn, tid, sn, qr, w, st)
    _seed_wcl(db_conn, tid, sn, qr, w, ct)
    assert _manhour(db_conn, tid, ct) == 120


def test_dp03_three_sessions_reactivation(db_conn):
    """DP-03: 재활성화 3세션 (TEST-1111 패턴) → FLOOR 합산 13"""
    sn = _sn('03'); qr = _seed_product(db_conn, sn); w = 9003
    ct = _dt(h=10, mi=15, s=14)
    tid = _seed_task(db_conn, sn, qr, w, started_at=_dt(h=10, mi=4, s=6))
    # 세션1 10:04:06~10:04:38 (32s), 세션2 10:05:48~10:07:55 (2m7s), 세션3 10:08:55~10:15:14 (6m19s→11분 패턴 재현 대신 실측)
    _seed_wsl(db_conn, tid, sn, qr, w, _dt(h=10, mi=4, s=6))
    _seed_wcl(db_conn, tid, sn, qr, w, _dt(h=10, mi=4, s=38))
    _seed_wsl(db_conn, tid, sn, qr, w, _dt(h=10, mi=5, s=48))
    _seed_wcl(db_conn, tid, sn, qr, w, _dt(h=10, mi=7, s=55))
    _seed_wsl(db_conn, tid, sn, qr, w, _dt(h=10, mi=8, s=55))
    _seed_wcl(db_conn, tid, sn, qr, w, ct)  # 10:08:55~10:15:14 = 6m19s
    # 합 = 32s + 2m7s + 6m19s = 8m58s → FLOOR(8.96)=8
    assert _manhour(db_conn, tid, ct) == 8


def test_dp05_break_pause_not_deducted(db_conn):
    """DP-05: break_lunch auto-pause 존재 → 차감 0 (휴게 미차감)"""
    sn = _sn('05'); qr = _seed_product(db_conn, sn); w = 9005
    st, ct = _dt(h=10), _dt(h=14)  # 240분 세션
    tid = _seed_task(db_conn, sn, qr, w, started_at=st)
    _seed_wsl(db_conn, tid, sn, qr, w, st)
    _seed_wcl(db_conn, tid, sn, qr, w, ct)
    _seed_pause(db_conn, tid, w, _dt(h=11, mi=20), _dt(h=12, mi=20), pause_type='lunch')
    assert _manhour(db_conn, tid, ct) == 240  # 휴게 미차감


def test_dp08_pause_exceeds_session_clamps_zero(db_conn):
    """DP-08: manual pause > session → GREATEST(0)=0"""
    sn = _sn('08'); qr = _seed_product(db_conn, sn); w = 9008
    st, ct = _dt(h=10), _dt(h=11)  # 60분 세션
    tid = _seed_task(db_conn, sn, qr, w, started_at=st)
    _seed_wsl(db_conn, tid, sn, qr, w, st)
    _seed_wcl(db_conn, tid, sn, qr, w, ct)
    _seed_pause(db_conn, tid, w, _dt(h=10), _dt(h=11))  # 전체 세션 pause
    assert _manhour(db_conn, tid, ct) == 0


def test_dp13_pause_outside_session(db_conn):
    """DP-13: manual pause 가 세션 밖(완료~재활성 gap) → 차감 0"""
    sn = _sn('13'); qr = _seed_product(db_conn, sn); w = 9013
    ct = _dt(h=15)
    tid = _seed_task(db_conn, sn, qr, w, started_at=_dt(h=8))
    # 세션1 08:00~09:00, 세션2 14:00~15:00 (gap 09:00~14:00)
    _seed_wsl(db_conn, tid, sn, qr, w, _dt(h=8))
    _seed_wcl(db_conn, tid, sn, qr, w, _dt(h=9))
    _seed_wsl(db_conn, tid, sn, qr, w, _dt(h=14))
    _seed_wcl(db_conn, tid, sn, qr, w, ct)
    # pause 10:00~11:00 = gap 안 (세션 밖) → 교집합 0
    _seed_pause(db_conn, tid, w, _dt(h=10), _dt(h=11))
    # man-hour = (60 + 60) − 0 = 120
    assert _manhour(db_conn, tid, ct) == 120


def test_dp14_pause_spans_session_boundary(db_conn):
    """DP-14: manual pause 가 세션 경계 걸침 → 겹친 부분만 차감"""
    sn = _sn('14'); qr = _seed_product(db_conn, sn); w = 9014
    ct = _dt(h=15)
    tid = _seed_task(db_conn, sn, qr, w, started_at=_dt(h=8))
    # 세션1 08:00~09:00, 세션2 14:00~15:00
    _seed_wsl(db_conn, tid, sn, qr, w, _dt(h=8))
    _seed_wcl(db_conn, tid, sn, qr, w, _dt(h=9))
    _seed_wsl(db_conn, tid, sn, qr, w, _dt(h=14))
    _seed_wcl(db_conn, tid, sn, qr, w, ct)
    # pause 08:30~14:30 → 세션1 겹침 08:30~09:00(30분) + 세션2 겹침 14:00~14:30(30분) = 60분만 차감
    _seed_pause(db_conn, tid, w, _dt(h=8, mi=30), _dt(h=14, mi=30))
    # man-hour = 120 − 60 = 60
    assert _manhour(db_conn, tid, ct) == 60


# ─── 그룹 2: 멀티 작업자 ────────────────────────────────────────

def test_dp06_multi_worker_parallel(db_conn):
    """DP-06: 2명 병렬(동시간대) → man-hour = 각자 합 (> elapsed)"""
    sn = _sn('06'); qr = _seed_product(db_conn, sn)
    wa, wb = 9061, 9062
    ct = _dt(h=12)
    tid = _seed_task(db_conn, sn, qr, wa, started_at=_dt(h=8))
    # A 08:00~12:00 (240), B 09:00~11:00 (120) — 병렬
    _seed_wsl(db_conn, tid, sn, qr, wa, _dt(h=8))
    _seed_wcl(db_conn, tid, sn, qr, wa, _dt(h=12))
    _seed_wsl(db_conn, tid, sn, qr, wb, _dt(h=9))
    _seed_wcl(db_conn, tid, sn, qr, wb, _dt(h=11))
    # man-hour = 240 + 120 = 360 (elapsed 는 240)
    assert _manhour(db_conn, tid, ct) == 360


def test_dp28_per_worker_pause_independent(db_conn):
    """DP-28: 1명 pause / 다른 1명 정상 → worker별 독립 pause 차감"""
    sn = _sn('28'); qr = _seed_product(db_conn, sn)
    wa, wb = 9281, 9282
    ct = _dt(h=12)
    tid = _seed_task(db_conn, sn, qr, wa, started_at=_dt(h=8))
    _seed_wsl(db_conn, tid, sn, qr, wa, _dt(h=8))
    _seed_wcl(db_conn, tid, sn, qr, wa, _dt(h=12))  # A 240
    _seed_wsl(db_conn, tid, sn, qr, wb, _dt(h=8))
    _seed_wcl(db_conn, tid, sn, qr, wb, _dt(h=12))  # B 240
    _seed_pause(db_conn, tid, wb, _dt(h=9), _dt(h=10))  # B만 60분 pause
    # man-hour = A 240 + B (240−60=180) = 420
    assert _manhour(db_conn, tid, ct) == 420


# ─── 그룹 3: 자동마감 / pause 익일 close (가상 close_at) ──────────

def test_dp22_unresumed_pause_autoclose_clamp(db_conn):
    """DP-22: 08:00 시작/09:00 미완 pause/익일 close_at=17:00 → 540−480=60"""
    sn = _sn('22'); qr = _seed_product(db_conn, sn); w = 9022
    st = _dt(h=8)
    close_at = _dt(h=17)  # PREV_DAY_CAP 가정
    tid = _seed_task(db_conn, sn, qr, w, started_at=st)
    _seed_wsl(db_conn, tid, sn, qr, w, st)
    # 완료기록 없음 (미완 세션) → close_at 으로 clamp
    # manual pause 09:00~ (미완, resumed_at NULL) → close_at clamp
    _seed_pause(db_conn, tid, w, _dt(h=9), None)
    # session = [08:00, 17:00]=540, pause∩session=[09:00,17:00]=480 → 60
    assert _manhour(db_conn, tid, close_at) == 60


def test_dp15_autoclose_virtual_interval_no_wcl(db_conn):
    """DP-15: auto-close 미완세션 — completion_log 없이 [start, close_at] 가상구간"""
    sn = _sn('15'); qr = _seed_product(db_conn, sn); w = 9015
    st = _dt(h=10)
    close_at = _dt(h=13)  # 180분
    tid = _seed_task(db_conn, sn, qr, w, started_at=st)
    _seed_wsl(db_conn, tid, sn, qr, w, st)
    # wcl 없음, pause 없음 → 가상구간 180
    assert _manhour(db_conn, tid, close_at) == 180


# ─── 그룹 4: 3경로 + 단일 UPDATE 원자성 ─────────────────────────

def test_dp26_unified_update_atomicity(db_conn):
    """DP-26: complete_task_unified — completed_at+duration+elapsed+audit 단일 UPDATE 원자 기록"""
    sn = _sn('26'); qr = _seed_product(db_conn, sn); w = 9026
    st, ct = _dt(h=8), _dt(h=16)
    tid = _seed_task(db_conn, sn, qr, w, started_at=st)
    _seed_wsl(db_conn, tid, sn, qr, w, st)
    _seed_wcl(db_conn, tid, sn, qr, w, ct)
    _seed_pause(db_conn, tid, w, _dt(h=9), _dt(h=15))  # 360
    result = complete_task_unified(
        tid, ct, force_closed=False, closed_by=None,
        close_reason=None, duration_source=None,
    )
    assert result is not None
    assert result['duration_minutes'] == 120  # 480−360
    # DB 동시 기록 확인 (partial write 불가)
    cur = db_conn.cursor()
    cur.execute("""SELECT completed_at, duration_minutes, elapsed_minutes, worker_count,
                          force_closed, closed_by, close_reason
                   FROM app_task_details WHERE id=%s""", (tid,))
    row = cur.fetchone()
    cur.close()
    assert row[0] is not None          # completed_at
    assert row[1] == 120               # duration
    assert row[2] == 480               # elapsed (raw)
    assert row[3] == 1                 # worker_count
    assert row[4] is False             # force_closed
    assert row[5] is None              # closed_by
    assert row[6] is None              # close_reason


def test_dp33_manual_force_close_free_reason_preserved(db_conn):
    """DP-33: 수동강제 자유입력 close_reason 보존 + force_closed=TRUE + manual 차감"""
    sn = _sn('33'); qr = _seed_product(db_conn, sn); w = 9033
    st, ct = _dt(h=8), _dt(h=12)
    tid = _seed_task(db_conn, sn, qr, w, started_at=st)
    _seed_wsl(db_conn, tid, sn, qr, w, st)
    _seed_wcl(db_conn, tid, sn, qr, w, ct)
    mgr = 9042
    _ensure_worker(db_conn, mgr, role='MECH')
    result = complete_task_unified(
        tid, ct, force_closed=True, closed_by=mgr,
        close_reason='작업자 미처리 강제종료', duration_source=None,
    )
    assert result is not None
    assert result['duration_minutes'] == 240  # raw, pause 없음
    cur = db_conn.cursor()
    cur.execute("SELECT force_closed, closed_by, close_reason FROM app_task_details WHERE id=%s", (tid,))
    row = cur.fetchone()
    cur.close()
    assert row[0] is True
    assert row[1] == mgr
    assert row[2] == '작업자 미처리 강제종료'


def test_dp30_race_guard_noop_when_already_closed(db_conn):
    """DP-30: race_guard=True 이고 이미 completed_at 있으면 no-op (None)"""
    sn = _sn('30'); qr = _seed_product(db_conn, sn); w = 9030
    st, ct = _dt(h=8), _dt(h=12)
    tid = _seed_task(db_conn, sn, qr, w, started_at=st)
    _seed_wsl(db_conn, tid, sn, qr, w, st)
    _seed_wcl(db_conn, tid, sn, qr, w, ct)
    # 1차 완료
    assert complete_task_unified(tid, ct, race_guard=True) is not None
    # 2차 race_guard → completed_at NOT NULL → no-op
    assert complete_task_unified(tid, ct, race_guard=True) is None


# ─── 그룹 5 일부: 미시작 task ──────────────────────────────────

def test_started_at_null_no_op(db_conn):
    """started_at NULL task → complete_task_unified no-op (WHERE started_at IS NOT NULL)"""
    sn = _sn('NULL'); qr = _seed_product(db_conn, sn); w = 9099
    tid = _seed_task(db_conn, sn, qr, w, started_at=None)
    assert complete_task_unified(tid, _dt(h=12)) is None
