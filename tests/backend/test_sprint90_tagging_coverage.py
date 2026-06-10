"""
Sprint 90-BE (FEAT-TAGGING-COVERAGE-ZEROTAP-DRILLDOWN-20260610) — pytest

태깅 커버리지 / 0초탭 드릴다운. 설계서: AGENT_TEAM_LAUNCH.md § Sprint 90-BE (Codex 4라운드 GO).

전략: 테스트 DB seed (prefix S90TC) → get_tagging_coverage 산출 검증 → cleanup.
  - 분모 = 완료+active NOT NULL+applicable+force_closed=FALSE (자동/admin완료=미추적 포함).
  - 3분류 oneClick>zero_tap>tracked. zero_tap = active≤1 OR close_reason 존재.
TC-TC-01~16.
"""
from __future__ import annotations

import pytest

from app.services import tagging_coverage_service as tcs
from app.services.statistics_service import CtParamError

_PREFIX = "S90TC"


def _seed_product(db_conn, sn, *, model="GAIA-I", customer=None, mech="BAT", elec="C&A"):
    cur = db_conn.cursor()
    cur.execute(
        "INSERT INTO plan.product_info (serial_number, model, customer, mech_partner, elec_partner) "
        "VALUES (%s,%s,%s,%s,%s) ON CONFLICT (serial_number) DO UPDATE SET "
        "model=EXCLUDED.model, customer=EXCLUDED.customer, "
        "mech_partner=EXCLUDED.mech_partner, elec_partner=EXCLUDED.elec_partner",
        (sn, model, customer, mech, elec),
    )
    cur.execute(
        "INSERT INTO qr_registry (qr_doc_id, serial_number, status) VALUES (%s,%s,'active') "
        "ON CONFLICT (qr_doc_id) DO NOTHING",
        (f"DOC_{sn}", sn),
    )
    db_conn.commit()


def _seed_task(db_conn, worker_id, sn, task_id, *, category="MECH", active=120,
               close_reason=None, force_closed=False, is_applicable=True,
               duration_source=None, completed=True):
    """완료 task seed. active=active_time_minutes. completed=False → completed_at NULL."""
    cur = db_conn.cursor()
    if completed:
        comp_sql, started_sql = "now()", "now() - interval '3 hours'"
    else:
        comp_sql, started_sql = "NULL", "now() - interval '3 hours'"
    cur.execute(
        f"""INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
             started_at, completed_at, duration_minutes, active_time_minutes,
             duration_source, close_reason, force_closed, is_applicable)
            VALUES (%s,%s,%s,%s,%s,%s, {started_sql}, {comp_sql}, %s, %s, %s, %s, %s, %s)""",
        (worker_id, sn, f"DOC_{sn}", category, task_id, task_id,
         active if active is not None else 0, active,
         duration_source, close_reason, force_closed, is_applicable),
    )
    db_conn.commit()


def _one(db_conn, worker, tag, task_id, *, category="MECH", active=120, close_reason=None,
         force_closed=False, is_applicable=True, duration_source=None, customer=None,
         mech="BAT", elec="C&A", model="GAIA-I", completed=True):
    sn = f"{_PREFIX}-{tag}"
    _seed_product(db_conn, sn, model=model, customer=customer, mech=mech, elec=elec)
    _seed_task(db_conn, worker, sn, task_id, category=category, active=active,
               close_reason=close_reason, force_closed=force_closed,
               is_applicable=is_applicable, duration_source=duration_source, completed=completed)
    return sn


def _cleanup(db_conn):
    try:
        db_conn.rollback()
    except Exception:
        pass
    cur = db_conn.cursor()
    cur.execute("DELETE FROM app_task_details WHERE serial_number LIKE %s", (f"{_PREFIX}%",))
    cur.execute("DELETE FROM qr_registry WHERE serial_number LIKE %s", (f"{_PREFIX}%",))
    cur.execute("DELETE FROM plan.product_info WHERE serial_number LIKE %s", (f"{_PREFIX}%",))
    db_conn.commit()
    tcs._cache.clear()


@pytest.fixture
def worker(db_conn, create_test_worker):
    if db_conn is None:
        pytest.skip("DB 없음")
    return create_test_worker(email="s90@test.axisos.com", password="Test1234!",
                              name="S90", role="MECH", company="BAT")


@pytest.fixture(autouse=True)
def _clean(db_conn):
    if db_conn is None:
        pytest.skip("DB 없음")
    _cleanup(db_conn)
    yield
    _cleanup(db_conn)


def _proc(result, process):
    return next((c for c in result["coverage"] if c["process"] == process), None)


def _task(result, process, task_id):
    return next((t for t in result["zero_tap_tasks"].get(process, []) if t["task_id"] == task_id), None)


# ── TC-TC-01 3분류 합 = 100% ──
def test_tc01_three_class_sums_to_population(db_conn, worker):
    _one(db_conn, worker, "t01a", "WASTE_GAS_LINE_1", active=120)            # tracked
    _one(db_conn, worker, "t01b", "UTIL_LINE_1", active=0)                   # zero_tap
    _one(db_conn, worker, "t01c", "TANK_DOCKING", active=0)                  # oneClick
    r = tcs.get_tagging_coverage()
    m = _proc(r, "MECH")
    assert m["n"] == 3
    # tracked 1/3=33, zero_tap 1/3=33, oneClick(remainder) → 합산 검증
    assert m["tracking_pct"] == 33 and m["zero_tap_pct"] == 33


# ── TC-TC-02 oneClick task는 zero_tap 집계 제외 + oneClick=true ──
def test_tc02_oneclick_excluded_from_process_zerotap(db_conn, worker):
    for i in range(3):
        _one(db_conn, worker, f"t02d{i}", "TANK_DOCKING", active=0)
    r = tcs.get_tagging_coverage()
    m = _proc(r, "MECH")
    assert m["zero_tap_pct"] == 0  # 전부 oneClick → process zero_tap 0
    td = _task(r, "MECH", "TANK_DOCKING")
    assert td["oneClick"] is True and td["zero_pct"] == 100  # 드릴다운 raw 는 100


# ── TC-TC-03 active>1=tracked, active<=1 비whitelist=zero_tap ──
def test_tc03_active_threshold(db_conn, worker):
    _one(db_conn, worker, "t03a", "WASTE_GAS_LINE_1", active=2)   # tracked (>1)
    _one(db_conn, worker, "t03b", "UTIL_LINE_1", active=1)        # zero_tap (<=1)
    r = tcs.get_tagging_coverage()
    m = _proc(r, "MECH")
    assert m["tracking_pct"] == 50 and m["zero_tap_pct"] == 50


# ── TC-TC-04 well_tracked_pct 경계 80% 포함 ──
def test_tc04_well_tracked_boundary(db_conn, worker):
    # serial A: 4 tracked / 5 = 0.8 → well (>=0.8 포함)
    sn = f"{_PREFIX}-t04A"
    _seed_product(db_conn, sn)
    for i, act in enumerate([120, 120, 120, 120, 0]):
        _seed_task(db_conn, worker, sn, f"MECH_T{i}", category="MECH", active=act)
    # serial B: 3/5 = 0.6 → not well
    sn2 = f"{_PREFIX}-t04B"
    _seed_product(db_conn, sn2)
    for i, act in enumerate([120, 120, 120, 0, 0]):
        _seed_task(db_conn, worker, sn2, f"MECH_T{i}", category="MECH", active=act)
    r = tcs.get_tagging_coverage()
    assert r["well_tracked_pct"] == 50  # 2 serial 중 1 well


# ── TC-TC-05 partners share 합100 + 내림차순 + PI/QI/SI=GST ──
def test_tc05_partner_share(db_conn, worker):
    # MECH PANEL zero-tap: BAT 2건 + FNI 1건
    for i in range(2):
        _one(db_conn, worker, f"t05b{i}", "WASTE_GAS_LINE_1", active=0, mech="BAT")
    _one(db_conn, worker, "t05f", "WASTE_GAS_LINE_1", active=0, mech="FNI")
    # PI zero-tap → GST 100
    _one(db_conn, worker, "t05pi", "PI_CHAMBER", category="PI", active=0)
    r = tcs.get_tagging_coverage()
    mech = _task(r, "MECH", "WASTE_GAS_LINE_1")
    assert sum(p["share"] for p in mech["partners"]) == 100
    assert mech["partners"][0]["partner"] == "BAT"  # 2건 = 1위 (내림차순)
    assert mech["partners"][0]["share"] >= mech["partners"][1]["share"]
    pi = _task(r, "PI", "PI_CHAMBER")
    assert pi["partners"] == [{"partner": "GST", "share": 100}]


# ── TC-TC-06 force_closed=TRUE 제외 / 자동·admin(force_closed=FALSE) 포함=미추적 ──
def test_tc06_force_excluded_auto_admin_included(db_conn, worker):
    _one(db_conn, worker, "t06fc", "WASTE_GAS_LINE_1", active=120, force_closed=True,
         close_reason="MANUAL_FORCE_CLOSE")  # 제외
    _one(db_conn, worker, "t06auto", "UTIL_LINE_1", active=120,
         close_reason="AUTO_CLOSED_BY_SECOND_FINAL_TRIGGER:SI")  # 포함 = zero_tap
    _one(db_conn, worker, "t06adm", "IF_1", category="ELEC", active=120,
         close_reason="ADMIN_COMPLETE")  # 포함 = zero_tap
    r = tcs.get_tagging_coverage()
    m = _proc(r, "MECH")
    assert m["n"] == 1  # force 제외, auto 1건만
    assert m["zero_tap_pct"] == 100 and m["tracking_pct"] == 0  # auto = 미추적
    e = _proc(r, "ELEC")
    assert e["n"] == 1 and e["zero_tap_pct"] == 100  # admin = 미추적


# ── TC-TC-07 TEST CUSTOMER / TEST% serial 제외 ──
def test_tc07_test_data_excluded(db_conn, worker):
    _one(db_conn, worker, "t07real", "WASTE_GAS_LINE_1", active=120, customer="GST")
    _one(db_conn, worker, "t07cust", "UTIL_LINE_1", active=0, customer="TEST CUSTOMER")
    # TEST% serial
    sn = "TEST-S90-X"
    _seed_product(db_conn, sn, customer="GST")
    _seed_task(db_conn, worker, sn, "IF_1", category="ELEC", active=0)
    r = tcs.get_tagging_coverage()
    assert _proc(r, "MECH")["n"] == 1   # TEST CUSTOMER 제외
    assert _proc(r, "ELEC")["n"] == 0   # TEST% serial 제외
    # cleanup TEST- serial (prefix 밖)
    cur = db_conn.cursor()
    cur.execute("DELETE FROM app_task_details WHERE serial_number='TEST-S90-X'")
    cur.execute("DELETE FROM qr_registry WHERE serial_number='TEST-S90-X'")
    cur.execute("DELETE FROM plan.product_info WHERE serial_number='TEST-S90-X'")
    db_conn.commit()


# ── TC-TC-08 confidence N>=30 trusted / <30 provisional ──
def test_tc08_confidence(db_conn, worker):
    for i in range(30):
        _one(db_conn, worker, f"t08m{i:02d}", "WASTE_GAS_LINE_1", active=120)
    for i in range(5):
        _one(db_conn, worker, f"t08e{i:02d}", "IF_1", category="ELEC", active=120)
    r = tcs.get_tagging_coverage()
    assert _proc(r, "MECH")["confidence"] == "trusted"      # n=30
    assert _proc(r, "ELEC")["confidence"] == "provisional"  # n=5


# ── TC-TC-09 5공정 고정 순서 + 빈 공정 N=0 포함 ──
def test_tc09_five_process_fixed_order(db_conn, worker):
    _one(db_conn, worker, "t09", "WASTE_GAS_LINE_1", active=120)
    r = tcs.get_tagging_coverage()
    assert [c["process"] for c in r["coverage"]] == ["MECH", "ELEC", "PI", "QI", "SI"]
    assert _proc(r, "QI")["n"] == 0 and _proc(r, "QI")["tracking_pct"] == 0


# ── TC-TC-10 INVALID_MONTH / INVALID_RANGE 400 ──
def test_tc10_param_validation(db_conn, worker):
    with pytest.raises(CtParamError) as e1:
        tcs.get_tagging_coverage(from_month="2026-13")
    assert e1.value.code == "INVALID_MONTH"
    with pytest.raises(CtParamError) as e2:
        tcs.get_tagging_coverage(from_month="2026-06", to_month="2026-05")
    assert e2.value.code == "INVALID_RANGE"


# ── TC-TC-11 빈 윈도우 → coverage 5행 0 + zero_tap_tasks {} + well 0 ──
def test_tc11_empty_window(db_conn, worker):
    r = tcs.get_tagging_coverage()
    assert len(r["coverage"]) == 5
    assert all(c["n"] == 0 for c in r["coverage"])
    assert r["zero_tap_tasks"] == {}
    assert r["well_tracked_pct"] == 0


# ── TC-TC-12 force_closed=TRUE AND duration_source IS NULL 제외 ──
def test_tc12_force_with_null_source_excluded(db_conn, worker):
    _one(db_conn, worker, "t12", "WASTE_GAS_LINE_1", active=120,
         force_closed=True, duration_source=None, close_reason=None)
    r = tcs.get_tagging_coverage()
    assert _proc(r, "MECH")["n"] == 0  # force_closed=FALSE 가드가 잡음 (duration_source 무관)


# ── TC-TC-13 DUAL/멀티행 per-row — 같은 serial tracked+zero → ratio 0.5 ──
def test_tc13_per_row_serial_ratio(db_conn, worker):
    sn = f"{_PREFIX}-t13"
    _seed_product(db_conn, sn)
    _seed_task(db_conn, worker, sn, "WASTE_GAS_LINE_1", category="MECH", active=120)  # tracked
    _seed_task(db_conn, worker, sn, "UTIL_LINE_1", category="MECH", active=0)         # zero_tap
    r = tcs.get_tagging_coverage()
    assert _proc(r, "MECH")["n"] == 2  # per-row 2건
    assert r["well_tracked_pct"] == 0  # 0.5 < 0.8 → not well


# ── TC-TC-14 HEATING_JACKET is_applicable=FALSE 제외 ──
def test_tc14_non_applicable_excluded(db_conn, worker):
    _one(db_conn, worker, "t14a", "WASTE_GAS_LINE_1", active=120, is_applicable=True)
    _one(db_conn, worker, "t14h", "HEATING_JACKET", active=0, is_applicable=False)
    r = tcs.get_tagging_coverage()
    assert _proc(r, "MECH")["n"] == 1  # is_applicable=FALSE 제외


# ── TC-TC-15 share largest-remainder 1/3씩 → Σ=100 ──
def test_tc15_largest_remainder(db_conn, worker):
    for mp in ("BAT", "FNI", "TMS"):
        _one(db_conn, worker, f"t15{mp}", "WASTE_GAS_LINE_1", active=0, mech=mp)
    r = tcs.get_tagging_coverage()
    t = _task(r, "MECH", "WASTE_GAS_LINE_1")
    shares = sorted([p["share"] for p in t["partners"]], reverse=True)
    assert sum(shares) == 100        # 33+33+34
    assert shares == [34, 33, 33]
    # 결정적 tie-break: 사전순 첫(BAT)이 34
    assert next(p["share"] for p in t["partners"] if p["partner"] == "BAT") == 34


# ── TC-TC-16 close_reason override — active>1 + close_reason 존재 → zero_tap ──
def test_tc16_close_reason_override(db_conn, worker):
    _one(db_conn, worker, "t16auto", "WASTE_GAS_LINE_1", active=200,
         close_reason="AUTO_CLOSED_BY_FIRST_FINAL_TRIGGER:SI")  # active>1 but close_reason → zero_tap
    _one(db_conn, worker, "t16norm", "UTIL_LINE_1", active=200, close_reason=None)  # tracked
    r = tcs.get_tagging_coverage()
    m = _proc(r, "MECH")
    assert m["n"] == 2
    assert m["tracking_pct"] == 50 and m["zero_tap_pct"] == 50  # auto=zero_tap, norm=tracked
