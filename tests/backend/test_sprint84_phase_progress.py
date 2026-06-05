"""
Sprint 84 (FEAT-FACTORY-PHASE-1-2-PROGRESS-20260605)

생산현황 상세 1차/2차 마일스톤 진행률 (A안, rollup 기반 보여주기):
  1차 = 전장외부 → 반제품(TM) → 기구(MECH) → 전장(ELEC) → 가압(PI). 1차완료 = pi.
  2차 = 공정검사(QI) → 마무리(SI). 2차완료 = si(SI_FINISHING).
  ⚠️ QI app 미입력(검사자동화시스템) → 2차 진행률 = SI binary (QI 연동 시 확장).

pytest TC (PH-01 ~ PH-06):
  PH-01 가압(PI) 완료        → p1_done=True, p1_pct=100, status='2차진행중'
  PH-02 마무리(SI) 완료      → p2_done=True, status='2차완료'
  PH-03 기구만 진행          → p1_done=False, status='1차진행중', p1_pct 부분
  PH-04 QI 미입력 + SI 완료  → p2_pct=100 (SI binary, QI 무관) / SI_SHIPMENT-only → p2 오염 없음
  PH-05 non-GAIA (TM 없음)   → p1_pct 분모에서 tm(None) 제외
  PH-06 회귀                 → phase 키 5종 + 기존 필드 무영향

설계서: AGENT_TEAM_LAUNCH.md § Sprint 84
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List

import pytest
from psycopg2.extras import RealDictCursor

from app.routes.factory import _compute_stage_completion, _build_phase

_KST = timezone(timedelta(hours=9))
_NOW = datetime(2026, 6, 4, 14, 0, tzinfo=_KST)


def _seed_product(db_conn, sn, model='GAIA-I'):
    cur = db_conn.cursor()
    cur.execute("INSERT INTO plan.product_info (serial_number, model) VALUES (%s,%s) "
                "ON CONFLICT (serial_number) DO UPDATE SET model=EXCLUDED.model", (sn, model))
    cur.execute("INSERT INTO qr_registry (qr_doc_id, serial_number, status) VALUES (%s,%s,'active') "
                "ON CONFLICT (qr_doc_id) DO NOTHING", (f"DOC_{sn}", sn))
    db_conn.commit()


def _seed_task(db_conn, worker_id, sn, category, task_id, done):
    cur = db_conn.cursor()
    cur.execute("""INSERT INTO app_task_details
        (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
         started_at, completed_at, is_applicable)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,TRUE)""",
        (worker_id, sn, f"DOC_{sn}", category, task_id, task_id,
         _NOW - timedelta(hours=2), _NOW if done else None))
    db_conn.commit()


def _cleanup(db_conn, serials: List[str]):
    try:
        db_conn.rollback()
    except Exception:
        pass
    cur = db_conn.cursor()
    for s in serials:
        cur.execute("DELETE FROM app_task_details WHERE serial_number=%s", (s,))
        cur.execute("DELETE FROM qr_registry WHERE qr_doc_id LIKE %s", (f"DOC_{s}%",))
        cur.execute("DELETE FROM plan.product_info WHERE serial_number LIKE %s", (f"{s}%",))
    db_conn.commit()


def _phase(db_conn, sn, model):
    cur = db_conn.cursor(cursor_factory=RealDictCursor)
    sc = _compute_stage_completion(cur, [sn], {sn: model})[sn]
    return _build_phase(sc), sc


@pytest.fixture
def w(db_conn, create_test_worker):
    if db_conn is None:
        pytest.skip("DB not available")
    return create_test_worker(email="s84-w@test.axisos.com", password="Test1234!",
                              name="S84 W", role="MECH", company="BAT")


def test_ph01_pi_done(db_conn, w):
    sn = "S84-PH01"
    try:
        _seed_product(db_conn, sn, 'GAIA-I')
        for c, t in [('TMS', 'TANK_MODULE'), ('MECH', 'PANEL_WORK'),
                     ('ELEC', 'WIRING'), ('PI', 'PI_CHAMBER')]:
            _seed_task(db_conn, w, sn, c, t, done=True)
        _seed_task(db_conn, w, sn, 'SI', 'SI_FINISHING', done=False)  # SI present 미완
        ph, _ = _phase(db_conn, sn, 'GAIA-I')
        assert ph['p1_done'] is True
        assert ph['p1_pct'] == 100.0
        assert ph['status'] == '2차진행중'
        assert ph['p2_done'] is False
    finally:
        _cleanup(db_conn, [sn])


def test_ph02_si_done(db_conn, w):
    sn = "S84-PH02"
    try:
        _seed_product(db_conn, sn, 'GAIA-I')
        _seed_task(db_conn, w, sn, 'PI', 'PI_CHAMBER', done=True)
        _seed_task(db_conn, w, sn, 'SI', 'SI_FINISHING', done=True)
        ph, _ = _phase(db_conn, sn, 'GAIA-I')
        assert ph['p2_done'] is True
        assert ph['p2_pct'] == 100.0
        assert ph['status'] == '2차완료'
    finally:
        _cleanup(db_conn, [sn])


def test_ph03_mech_only(db_conn, w):
    sn = "S84-PH03"
    try:
        _seed_product(db_conn, sn, 'GAIA-I')
        _seed_task(db_conn, w, sn, 'TMS', 'TANK_MODULE', done=False)
        _seed_task(db_conn, w, sn, 'MECH', 'PANEL_WORK', done=True)
        _seed_task(db_conn, w, sn, 'MECH', 'SELF_INSPECTION', done=False)  # 기구 미완
        _seed_task(db_conn, w, sn, 'ELEC', 'WIRING', done=False)
        _seed_task(db_conn, w, sn, 'PI', 'PI_CHAMBER', done=False)
        ph, _ = _phase(db_conn, sn, 'GAIA-I')
        assert ph['p1_done'] is False
        assert ph['status'] == '1차진행중'
        assert 0 < ph['p1_pct'] < 100  # 일부만 (tm rollup True, 나머지 미완)
    finally:
        _cleanup(db_conn, [sn])


def test_ph04_qi_not_entered_si_done(db_conn, w):
    """QI app 미입력 — SI 완료 시 p2_pct=100 (QI 무관, SI binary)."""
    sn = "S84-PH04"
    try:
        _seed_product(db_conn, sn, 'GAIA-I')
        _seed_task(db_conn, w, sn, 'PI', 'PI_CHAMBER', done=True)
        _seed_task(db_conn, w, sn, 'QI', 'QI_INSPECTION', done=False)  # QI 영구 미입력
        _seed_task(db_conn, w, sn, 'SI', 'SI_FINISHING', done=True)
        ph, _ = _phase(db_conn, sn, 'GAIA-I')
        assert ph['p2_pct'] == 100.0  # QI 미입력이어도 SI 기준 100
        assert ph['p2_done'] is True
    finally:
        _cleanup(db_conn, [sn])


def test_ph04b_si_shipment_only_no_pollution(db_conn, w):
    """M-2 검증 — SI_SHIPMENT만 완료(SI_FINISHING 미완) → p2 오염 없음(0)."""
    sn = "S84-PH04B"
    try:
        _seed_product(db_conn, sn, 'GAIA-I')
        _seed_task(db_conn, w, sn, 'PI', 'PI_CHAMBER', done=True)
        _seed_task(db_conn, w, sn, 'SI', 'SI_FINISHING', done=False)  # 마무리공정 미완
        _seed_task(db_conn, w, sn, 'SI', 'SI_SHIPMENT', done=True)    # 출하만 완료(엣지)
        ph, sc = _phase(db_conn, sn, 'GAIA-I')
        assert sc['si'] is False        # SI = SI_FINISHING 기준 → 미완
        assert ph['p2_done'] is False
        assert ph['p2_pct'] == 0.0      # 50% 오염 없음 (M-2 fix)
    finally:
        _cleanup(db_conn, [sn])


def test_ph05_non_gaia_tm_excluded(db_conn, w):
    """non-GAIA — 1차 분모에서 tm(None) 제외."""
    sn = "S84-PH05"
    try:
        _seed_product(db_conn, sn, 'SWS-I')  # non-GAIA, TMS 없음
        _seed_task(db_conn, w, sn, 'MECH', 'PANEL_WORK', done=True)
        _seed_task(db_conn, w, sn, 'ELEC', 'WIRING', done=True)
        _seed_task(db_conn, w, sn, 'PI', 'PI_CHAMBER', done=True)
        ph, sc = _phase(db_conn, sn, 'SWS-I')
        assert sc['tm'] is None              # TM 해당 없음
        assert ph['p1_pct'] == 100.0         # mech/elec/pi 3개 전부 완료 (tm 제외)
        assert ph['p1_done'] is True
    finally:
        _cleanup(db_conn, [sn])


def test_ph06_phase_keys(db_conn, w):
    """회귀 — phase 5키 구조."""
    sn = "S84-PH06"
    try:
        _seed_product(db_conn, sn, 'GAIA-I')
        _seed_task(db_conn, w, sn, 'MECH', 'PANEL_WORK', done=True)
        ph, _ = _phase(db_conn, sn, 'GAIA-I')
        assert set(ph.keys()) == {'p1_done', 'p2_done', 'p1_pct', 'p2_pct', 'status'}
    finally:
        _cleanup(db_conn, [sn])
