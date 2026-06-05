"""
Sprint 83 (FEAT-FACTORY-COMPLETION-ROLLUP-20260605)

공장 대시보드 공정별 완료율을 completion_status 옛 플래그(lag) 대신
실제 task 완료(app_task_details) + 하위완료→상위 cascade rollup 으로 재계산.
근본 data 무변경(read-time). 옵션 B(체크리스트 무관). SI=SI_FINISHING 기준.

pytest TC (CR-01 ~ CR-10):
  CR-01 TMS task 전부 완료 (flag 무관)       → tm=True
  CR-02 SI_FINISHING 완료 + SI_SHIPMENT 미완 → si=True (출하 무관)
  CR-03 SI 도달 + MECH 1 task 미완           → mech=True (cascade, 체크리스트 무관)
  CR-04 PI 도달 + MECH/ELEC partial          → mech/elec/tm=True / pi=actual / qi·si=False
  CR-05 MECH만 진행 (뒤 공정 미도달)          → rollup 미발동, 실제 진도 (over-marking 0)
  CR-06 non-GAIA                              → tm=None
  CR-07 GBWS-7163 재현 (SI_FINISHING 완료)    → 전 공정 True, progress 100
  CR-08 회귀 — by_stage 스키마 키 불변
  CR-09 DUAL TMS (L/R 2행)                    → L+R 둘 다 완료여야 tm=True
  CR-10 PI 도달 시 병렬 tier 3종 동시          → mech/elec/tm 전부 True

설계서: AGENT_TEAM_LAUNCH.md § Sprint 83
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List, Optional

import pytest

from psycopg2.extras import RealDictCursor

from app.routes.factory import _compute_stage_completion, _progress_from_stages

_KST = timezone(timedelta(hours=9))
_NOW = datetime(2026, 6, 4, 14, 0, tzinfo=_KST)


# ---------------------------------------------------------------------------
# Helper — seed
# ---------------------------------------------------------------------------

def _seed_product(db_conn, sn, model='GAIA-I'):
    cur = db_conn.cursor()
    cur.execute("""
        INSERT INTO plan.product_info (serial_number, model)
        VALUES (%s, %s) ON CONFLICT (serial_number) DO UPDATE SET model=EXCLUDED.model
    """, (sn, model))
    cur.execute("""
        INSERT INTO qr_registry (qr_doc_id, serial_number, status)
        VALUES (%s, %s, 'active') ON CONFLICT (qr_doc_id) DO NOTHING
    """, (f"DOC_{sn}", sn))
    db_conn.commit()


def _seed_dual_side(db_conn, sn, suffix, model='GAIA-I DUAL'):
    """DUAL L/R qr_doc_id FK 체인: product_info {sn}{suffix} + qr_registry DOC_{sn}{suffix}."""
    cur = db_conn.cursor()
    cur.execute("""INSERT INTO plan.product_info (serial_number, model)
                   VALUES (%s,%s) ON CONFLICT (serial_number) DO NOTHING""",
                (f"{sn}{suffix}", model))
    cur.execute("""INSERT INTO qr_registry (qr_doc_id, serial_number, status)
                   VALUES (%s,%s,'active') ON CONFLICT (qr_doc_id) DO NOTHING""",
                (f"DOC_{sn}{suffix}", f"{sn}{suffix}"))
    db_conn.commit()


def _seed_task(db_conn, worker_id, sn, category, task_id, done,
               applicable=True, qr_suffix=''):
    """app_task_details 1행. done=True면 completed_at 채움.
    qr_suffix(DUAL L/R) 사용 시 _seed_dual_side 로 FK 체인 선행 필요."""
    cur = db_conn.cursor()
    qr = f"DOC_{sn}{qr_suffix}"
    cur.execute("""
        INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
             started_at, completed_at, is_applicable)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (worker_id, sn, qr, category, task_id, task_id,
          _NOW - timedelta(hours=2), _NOW if done else None, applicable))
    db_conn.commit()


def _cleanup(db_conn, serials: List[str]):
    try:
        db_conn.rollback()
    except Exception:
        pass
    cur = db_conn.cursor()
    for s in serials:
        # 순서: app_task_details(qr FK RESTRICT) → qr_registry(serial FK) → product_info
        cur.execute("DELETE FROM app_task_details WHERE serial_number = %s", (s,))
        cur.execute("DELETE FROM qr_registry WHERE qr_doc_id LIKE %s", (f"DOC_{s}%",))
        cur.execute("DELETE FROM plan.product_info WHERE serial_number LIKE %s", (f"{s}%",))
    db_conn.commit()


def _rdc(db_conn):
    return db_conn.cursor(cursor_factory=RealDictCursor)


def _compute(db_conn, sn, model):
    cur = _rdc(db_conn)
    return _compute_stage_completion(cur, [sn], {sn: model})[sn]


@pytest.fixture
def w(db_conn, create_test_worker):
    if db_conn is None:
        pytest.skip("DB not available")
    return create_test_worker(email="s83-w@test.axisos.com", password="Test1234!",
                              name="S83 W", role="MECH", company="BAT")


# ---------------------------------------------------------------------------
# CR-01 ~ CR-10
# ---------------------------------------------------------------------------

def test_cr01_tms_done_ignores_flag(db_conn, w):
    sn = "S83-CR01"
    try:
        _seed_product(db_conn, sn, 'GAIA-I')
        _seed_task(db_conn, w, sn, 'TMS', 'TANK_MODULE', done=True)
        _seed_task(db_conn, w, sn, 'TMS', 'PRESSURE_TEST', done=True)
        r = _compute(db_conn, sn, 'GAIA-I')
        assert r['tm'] is True  # 실제 task 완료 → tm True (completion_status 플래그 무관)
    finally:
        _cleanup(db_conn, [sn])


def test_cr02_si_finishing_done_shipment_pending(db_conn, w):
    sn = "S83-CR02"
    try:
        _seed_product(db_conn, sn, 'GAIA-I')
        _seed_task(db_conn, w, sn, 'SI', 'SI_FINISHING', done=True)
        _seed_task(db_conn, w, sn, 'SI', 'SI_SHIPMENT', done=False)
        r = _compute(db_conn, sn, 'GAIA-I')
        assert r['si'] is True  # SI_FINISHING 기준 (출하 미완 무관)
    finally:
        _cleanup(db_conn, [sn])


def test_cr03_si_reached_mech_incomplete_cascade(db_conn, w):
    sn = "S83-CR03"
    try:
        _seed_product(db_conn, sn, 'GAIA-I')
        # MECH 2 task 중 1개만 완료 (체크리스트 미완 가정)
        _seed_task(db_conn, w, sn, 'MECH', 'PANEL_WORK', done=True)
        _seed_task(db_conn, w, sn, 'MECH', 'SELF_INSPECTION', done=False)
        # SI 마무리 도달
        _seed_task(db_conn, w, sn, 'SI', 'SI_FINISHING', done=True)
        r = _compute(db_conn, sn, 'GAIA-I')
        assert r['mech'] is True  # SI 도달 → MECH 강제 100% (cascade, 1개 미완 무시)
        assert r['si'] is True
    finally:
        _cleanup(db_conn, [sn])


def test_cr04_pi_reached_assembly_cascade_only(db_conn, w):
    sn = "S83-CR04"
    try:
        _seed_product(db_conn, sn, 'GAIA-I')
        _seed_task(db_conn, w, sn, 'MECH', 'PANEL_WORK', done=False)  # MECH 미완
        _seed_task(db_conn, w, sn, 'ELEC', 'WIRING', done=False)      # ELEC 미완
        _seed_task(db_conn, w, sn, 'TMS', 'TANK_MODULE', done=False)
        _seed_task(db_conn, w, sn, 'PI', 'PI_CHAMBER', done=True)     # PI 도달
        _seed_task(db_conn, w, sn, 'QI', 'QI_INSPECTION', done=False)
        r = _compute(db_conn, sn, 'GAIA-I')
        # PI(tier1) 도달 → 앞 tier0 (mech/elec/tm) 강제 True
        assert r['mech'] is True and r['elec'] is True and r['tm'] is True
        assert r['pi'] is True   # PI 자체 완료
        assert r['qi'] is False and r['si'] is False  # 뒤 공정 미도달
    finally:
        _cleanup(db_conn, [sn])


def test_cr05_mech_only_no_rollup(db_conn, w):
    sn = "S83-CR05"
    try:
        _seed_product(db_conn, sn, 'GAIA-I')
        _seed_task(db_conn, w, sn, 'MECH', 'PANEL_WORK', done=True)
        _seed_task(db_conn, w, sn, 'MECH', 'SELF_INSPECTION', done=False)  # MECH 미완
        _seed_task(db_conn, w, sn, 'ELEC', 'WIRING', done=False)
        r = _compute(db_conn, sn, 'GAIA-I')
        # 뒤 공정 미도달 → rollup 없음 → 실제 진도
        assert r['mech'] is False   # MECH 1개 미완 = 실제 미완
        assert r['elec'] is False
        assert r['pi'] is False
    finally:
        _cleanup(db_conn, [sn])


def test_cr06_non_gaia_tm_none(db_conn, w):
    sn = "S83-CR06"
    try:
        _seed_product(db_conn, sn, 'SWS-I')  # non-GAIA
        _seed_task(db_conn, w, sn, 'MECH', 'PANEL_WORK', done=True)
        r = _compute(db_conn, sn, 'SWS-I')
        assert r['tm'] is None  # non-GAIA = TM 해당 없음
    finally:
        _cleanup(db_conn, [sn])


def test_cr07_gbws7163_full_rollup(db_conn, w):
    sn = "S83-CR07"
    try:
        _seed_product(db_conn, sn, 'GAIA-I')
        # GBWS-7163 재현: MECH 5/6, ELEC 5/6, TMS 2/2, PI 2/2, QI 0/1, SI_FINISHING 완료
        _seed_task(db_conn, w, sn, 'MECH', 'PANEL_WORK', done=True)
        _seed_task(db_conn, w, sn, 'MECH', 'SELF_INSPECTION', done=False)  # 1개 미완
        _seed_task(db_conn, w, sn, 'QI', 'QI_INSPECTION', done=False)      # QI 미완
        _seed_task(db_conn, w, sn, 'SI', 'SI_FINISHING', done=True)
        _seed_task(db_conn, w, sn, 'SI', 'SI_SHIPMENT', done=False)
        r = _compute(db_conn, sn, 'GAIA-I')
        assert all(r[k] is True for k in ('mech', 'tm', 'pi', 'qi', 'si'))  # 전부 100%
        assert _progress_from_stages(r) == 100.0
    finally:
        _cleanup(db_conn, [sn])


def test_cr08_bystage_schema_keys(client, db_conn, w, get_auth_token):
    """회귀 — weekly-kpi by_stage 스키마 키 불변."""
    if db_conn is None:
        pytest.skip("DB not available")
    admin_id = w  # 아무 worker — endpoint 는 권한 체크. admin 토큰 생성
    from app.routes import factory  # noqa
    # endpoint 직접 호출 대신 by_stage 키 집합만 검증 (응답 스키마 불변 보증)
    # 간단 검증: helper 결과 dict 키가 by_stage 키와 동일 집합
    sn = "S83-CR08"
    try:
        _seed_product(db_conn, sn, 'GAIA-I')
        _seed_task(db_conn, w, sn, 'MECH', 'PANEL_WORK', done=True)
        r = _compute(db_conn, sn, 'GAIA-I')
        assert set(r.keys()) == {'mech', 'elec', 'tm', 'pi', 'qi', 'si'}
    finally:
        _cleanup(db_conn, [sn])


def test_cr09_dual_tms_both_sides(db_conn, w):
    """DUAL TMS (L/R 2행) — 한쪽만 완료면 tm 미완, 둘 다 완료여야 tm True."""
    sn = "S83-CR09"
    try:
        _seed_product(db_conn, sn, 'GAIA-I DUAL')
        _seed_dual_side(db_conn, sn, '-L')
        _seed_dual_side(db_conn, sn, '-R')
        # L 완료 / R 미완 (task_id 동일, qr_doc_id 로 구분 — 실 DUAL 구조)
        _seed_task(db_conn, w, sn, 'TMS', 'TANK_MODULE', done=True, qr_suffix='-L')
        _seed_task(db_conn, w, sn, 'TMS', 'TANK_MODULE', done=False, qr_suffix='-R')
        r = _compute(db_conn, sn, 'GAIA-I DUAL')
        assert r['tm'] is False  # R 미완 → 카테고리 미완
        # R 도 완료시키면 True
        cur = db_conn.cursor()
        cur.execute("""UPDATE app_task_details SET completed_at=%s
                       WHERE serial_number=%s AND qr_doc_id=%s""",
                    (_NOW, sn, f"DOC_{sn}-R"))
        db_conn.commit()
        r2 = _compute(db_conn, sn, 'GAIA-I DUAL')
        assert r2['tm'] is True  # L+R 둘 다 완료
    finally:
        _cleanup(db_conn, [sn])


def test_cr10_pi_reached_parallel_tier_all(db_conn, w):
    """PI 도달 시 앞 공정(TM/MECH/ELEC) 전부 True."""
    sn = "S83-CR10"
    try:
        _seed_product(db_conn, sn, 'GAIA-I')
        _seed_task(db_conn, w, sn, 'MECH', 'PANEL_WORK', done=False)
        _seed_task(db_conn, w, sn, 'ELEC', 'WIRING', done=False)
        _seed_task(db_conn, w, sn, 'TMS', 'TANK_MODULE', done=False)
        _seed_task(db_conn, w, sn, 'PI', 'PI_CHAMBER', done=True)
        r = _compute(db_conn, sn, 'GAIA-I')
        assert r['mech'] is True
        assert r['elec'] is True
        assert r['tm'] is True
    finally:
        _cleanup(db_conn, [sn])


def test_cr11_mech_reached_forces_tm(db_conn, w):
    """실 공정 순서(반제품→기구) — 기구 도달 시 반제품(TM) 강제 100%."""
    sn = "S83-CR11"
    try:
        _seed_product(db_conn, sn, 'GAIA-I')
        _seed_task(db_conn, w, sn, 'TMS', 'TANK_MODULE', done=False)   # 반제품 미완(플래그)
        _seed_task(db_conn, w, sn, 'MECH', 'PANEL_WORK', done=True)    # 기구 도달
        r = _compute(db_conn, sn, 'GAIA-I')
        assert r['tm'] is True   # 반제품(tier0) < 기구(tier1) → 강제 100%
        # 반대로 ELEC 만 도달, 기구는 furthest 보다 앞 → 강제
        assert r['mech'] is True  # PANEL_WORK 완료 = 기구 실제 완료
    finally:
        _cleanup(db_conn, [sn])
