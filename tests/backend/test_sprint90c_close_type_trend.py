"""
Sprint 90-BE-C (#90, FEAT-CLOSE-TYPE-TREND-PARTNER-20260612) — pytest

협력사×그룹×월 마감유형 추이 (auto/zerotap/force). 설계: AGENT_TEAM_LAUNCH.md § Sprint 90-BE-C.
전략: 테스트 DB seed(prefix S90CTT) → get_close_type_trend 검증 → cleanup.
TC-CTT-01~07.
"""
from __future__ import annotations

import pytest

from app.services import close_type_trend_service as cts
from app.services.statistics_service import CtParamError

_PREFIX = "S90CTT"


def _seed(db_conn, worker, suffix, category, task_id, *, mech="BAT", elec="C&A",
          active=120, close_reason=None, force_closed=False, month="2026-06", customer=None):
    sn = f"{_PREFIX}-{suffix}"
    cur = db_conn.cursor()
    cur.execute(
        "INSERT INTO plan.product_info (serial_number, model, customer, mech_partner, elec_partner) "
        "VALUES (%s,'GAIA-I',%s,%s,%s) ON CONFLICT (serial_number) DO UPDATE SET "
        "mech_partner=EXCLUDED.mech_partner, elec_partner=EXCLUDED.elec_partner, customer=EXCLUDED.customer",
        (sn, customer, mech, elec),
    )
    cur.execute(
        "INSERT INTO qr_registry (qr_doc_id, serial_number, status) VALUES (%s,%s,'active') "
        "ON CONFLICT (qr_doc_id) DO NOTHING", (f"DOC_{sn}", sn),
    )
    comp = f"{month}-15T10:00:00+09:00"
    cur.execute(
        """INSERT INTO app_task_details
           (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
            started_at, completed_at, duration_minutes, active_time_minutes,
            close_reason, force_closed, is_applicable)
           VALUES (%s,%s,%s,%s,%s,%s, %s::timestamptz - interval '3 hours', %s::timestamptz,
                   120, %s, %s, %s, TRUE)""",
        (worker, sn, f"DOC_{sn}", category, task_id, task_id, comp, comp,
         active, close_reason, force_closed),
    )
    db_conn.commit()


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


@pytest.fixture
def worker(db_conn, create_test_worker):
    if db_conn is None:
        pytest.skip("DB 없음")
    return create_test_worker(email="s90ctt@test.axisos.com", password="Test1234!",
                              name="S90CTT", role="MECH", company="BAT")


@pytest.fixture(autouse=True)
def _clean(db_conn):
    if db_conn is None:
        pytest.skip("DB 없음")
    _cleanup(db_conn)
    yield
    _cleanup(db_conn)


def _cell(res, partner, group, month):
    return next((s for s in res["series"]
                 if s["partner"] == partner and s["group"] == group and s["month"] == month), None)


# ── TC-CTT-01 auto/zerotap/force 분류 (BAT MECH 2026-06) ──
def test_ctt01_close_type_counts(db_conn, worker):
    _seed(db_conn, worker, "a", "MECH", "WASTE_GAS_LINE_1", active=0)                    # zerotap(active≤1)
    _seed(db_conn, worker, "b", "MECH", "UTIL_LINE_1", active=120,
          close_reason="AUTO_CLOSED_BY_SECOND_FINAL_TRIGGER:X")                          # auto + zerotap(close_reason)
    _seed(db_conn, worker, "c", "MECH", "WASTE_GAS_LINE_2", active=120, force_closed=True)  # force
    _seed(db_conn, worker, "d", "MECH", "HEATING_JACKET", active=120)                    # none(tracked)
    res = cts.get_close_type_trend(from_month="2026-06", to_month="2026-06")
    c = _cell(res, "BAT", "MECH", "2026-06")
    assert c is not None
    assert c["auto"] == 1 and c["force"] == 1 and c["zerotap"] == 2  # auto⊆zerotap (a+b)


# ── TC-CTT-02 GST/SH 제외 ──
def test_ctt02_gst_sh_excluded(db_conn, worker):
    _seed(db_conn, worker, "bat", "MECH", "WASTE_GAS_LINE_1", active=0, mech="BAT")
    _seed(db_conn, worker, "gst", "MECH", "WASTE_GAS_LINE_1", active=0, mech="GST")
    _seed(db_conn, worker, "sh", "MECH", "WASTE_GAS_LINE_1", active=0, mech="SH")
    res = cts.get_close_type_trend(from_month="2026-06", to_month="2026-06")
    partners = {s["partner"] for s in res["series"]}
    assert "BAT" in partners
    assert "GST" not in partners and "SH" not in partners


# ── TC-CTT-03 빈 달 zero-fill ──
def test_ctt03_zero_fill(db_conn, worker):
    _seed(db_conn, worker, "a", "MECH", "WASTE_GAS_LINE_1", active=0, month="2026-06")  # 6월만
    res = cts.get_close_type_trend(from_month="2026-05", to_month="2026-06")
    may = _cell(res, "BAT", "MECH", "2026-05")
    assert may is not None and may["auto"] == 0 and may["zerotap"] == 0 and may["force"] == 0  # 빈 달 0


# ── TC-CTT-04 ?partner 필터 ──
def test_ctt04_partner_filter(db_conn, worker):
    _seed(db_conn, worker, "bat", "MECH", "WASTE_GAS_LINE_1", active=0, mech="BAT")
    _seed(db_conn, worker, "fni", "MECH", "UTIL_LINE_1", active=0, mech="FNI")
    res = cts.get_close_type_trend(from_month="2026-06", to_month="2026-06", partner="BAT")
    partners = {s["partner"] for s in res["series"]}
    assert partners == {"BAT"} and res["scope"]["partner"] == "BAT"


# ── TC-CTT-05 ?group 필터 (MECH/ELEC) ──
def test_ctt05_group_filter(db_conn, worker):
    _seed(db_conn, worker, "m", "MECH", "WASTE_GAS_LINE_1", active=0, mech="BAT")
    _seed(db_conn, worker, "e", "ELEC", "PANEL_WORK", active=0, elec="C&A")
    res = cts.get_close_type_trend(from_month="2026-06", to_month="2026-06", group="ELEC")
    groups = {s["group"] for s in res["series"]}
    assert groups == {"ELEC"} and res["scope"]["group"] == "ELEC"


# ── TC-CTT-06 ELEC partner = elec_partner (TMS→TMS(E)) ──
def test_ctt06_elec_partner_tms(db_conn, worker):
    _seed(db_conn, worker, "tms", "ELEC", "PANEL_WORK", active=0, elec="TMS")
    res = cts.get_close_type_trend(from_month="2026-06", to_month="2026-06")
    c = _cell(res, "TMS(E)", "ELEC", "2026-06")
    assert c is not None and c["zerotap"] == 1


# ── TC-CTT-07 INVALID_MONTH 400 ──
def test_ctt07_invalid_month(db_conn, worker):
    with pytest.raises(CtParamError) as e:
        cts.get_close_type_trend(from_month="2026-13")
    assert e.value.code == "INVALID_MONTH"


# ── #90b TC-CTT-08 bucket=week — ISO 라벨 + 주 zero-fill + meta ──
def test_ctt08_week_bucket(db_conn, worker):
    _seed(db_conn, worker, "wk", "MECH", "WASTE_GAS_LINE_1", active=0, month="2026-06")
    res = cts.get_close_type_trend(from_month="2026-06", to_month="2026-06", bucket="week")
    assert res["meta"]["bucket"] == "week"
    import re
    labels = {s["month"] for s in res["series"]}
    assert all(re.match(r"^\d{4}-W\d{2}$", m) for m in labels)
    # 6-15 완료 → 2026-W25 셀에 zerotap 1
    c = next((s for s in res["series"] if s["month"] == "2026-W25" and s["partner"] == "BAT"), None)
    assert c is not None and c["zerotap"] == 1
    # 6월 윈도우 = W23~W27 5개 주 zero-fill
    assert len(labels) >= 4


# ── #90b TC-CTT-09 기본 month 회귀 + INVALID_BUCKET ──
def test_ctt09_month_default_and_invalid(db_conn, worker):
    _seed(db_conn, worker, "mo", "MECH", "UTIL_LINE_1", active=0, month="2026-06")
    res = cts.get_close_type_trend(from_month="2026-06", to_month="2026-06")
    assert res["meta"]["bucket"] == "month"
    assert any(s["month"] == "2026-06" for s in res["series"])
    with pytest.raises(CtParamError) as e:
        cts.get_close_type_trend(bucket="day")
    assert e.value.code == "INVALID_BUCKET"
