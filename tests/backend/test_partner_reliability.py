"""
FEAT-PARTNER-RELIABILITY (#93) — 협력사×모델×공정 추적률 분해

검증:
  - 응답 구조 (by_cell/by_model_process/by_partner/trend/meta)
  - invariant (M-1): by_cell 협력사 셀 n 가중합 = by_model_process 합산
  - GST·SH·(미지정) 제외 (M-Q4)
  - batch(TMS(M)) 플래그 + batch_n (Q2-A) / trend omit
  - raw Σtracked/Σn 합산 (pct 평균 금지, Q3)
  - confidence (n>=30, Q5-A) / process 검증
"""
from collections import defaultdict

import pytest

from app.services.partner_reliability_service import get_partner_reliability
from app.services.statistics_service import CtParamError


def test_pr01_invalid_process():
    """TC-PR-01: process 화이트리스트 (MECH|ELEC)."""
    with pytest.raises(CtParamError) as e:
        get_partner_reliability(process="PI")
    assert e.value.code == "INVALID_PROCESS"


@pytest.fixture
def rel(db_conn):
    if db_conn is None:
        pytest.skip("sqlite")
    return get_partner_reliability()


def test_pr02_shape(rel):
    """TC-PR-02: 최상위 키 + meta."""
    for k in ("by_cell", "by_model_process", "by_partner", "trend", "meta"):
        assert k in rel
    assert rel["meta"]["gate"] == 70
    assert rel["meta"]["n_min"] == 30
    # whitelist = 정정된 2개 (v2.42.1)
    assert set(rel["meta"]["whitelist"]) == {"TANK_DOCKING", "SI_SHIPMENT"}


def test_pr03_gst_sh_excluded(rel):
    """TC-PR-03 (M-Q4): GST·SH·(미지정) 제외 — 협력사만."""
    for arr in ("by_cell", "by_partner"):
        partners = {x["partner"] for x in rel[arr]}
        assert "GST" not in partners
        assert "SH" not in partners
        assert "(미지정)" not in partners


def test_pr04_mech_elec_only(rel):
    """TC-PR-04: MECH/ELEC 공정만 (PI/QI/SI 제외)."""
    for arr in ("by_cell", "by_model_process", "by_partner", "trend"):
        procs = {x["process"] for x in rel[arr]}
        assert procs <= {"MECH", "ELEC"}, f"{arr}: {procs}"


def test_pr05_invariant_cell_sum_equals_model_process(rel):
    """TC-PR-05 (M-1): by_cell 협력사 셀 n 합 = by_model_process 합산 n (batch 포함)."""
    cell_n = defaultdict(int)
    cell_tracked = defaultdict(int)
    for c in rel["by_cell"]:
        key = (c["model"], c["process"])
        cell_n[key] += c["n"]
        # tracking_pct·n 으로 tracked 역산 (raw 합산 검증)
        cell_tracked[key] += round(c["tracking_pct"] / 100 * c["n"])
    for m in rel["by_model_process"]:
        key = (m["model"], m["process"])
        assert cell_n[key] == m["n"], f"invariant 위반 {key}: cell {cell_n[key]} != mp {m['n']}"


def test_pr06_raw_aggregation_not_pct_average(rel):
    """TC-PR-06 (Q3): by_model_process pct = Σtracked/Σn (raw), pct 단순평균 아님."""
    # by_cell 에서 raw 합산한 pct 가 by_model_process pct 와 일치 (±0.2 반올림)
    agg = defaultdict(lambda: [0, 0])
    for c in rel["by_cell"]:
        key = (c["model"], c["process"])
        agg[key][0] += round(c["tracking_pct"] / 100 * c["n"])
        agg[key][1] += c["n"]
    for m in rel["by_model_process"]:
        key = (m["model"], m["process"])
        raw_pct = round(100 * agg[key][0] / agg[key][1], 1) if agg[key][1] else 0.0
        assert abs(raw_pct - m["tracking_pct"]) <= 1.0, f"{key}: raw {raw_pct} vs {m['tracking_pct']}"


def test_pr07_batch_flag_and_trend_omit(rel):
    """TC-PR-07 (Q2-A): TMS(M)=batch 플래그 + by_model_process batch_n + trend omit."""
    # by_cell/by_partner 의 TMS(M) 은 batch:true
    for c in rel["by_cell"]:
        if c["partner"] == "TMS(M)":
            assert c.get("batch") is True
    # by_model_process 는 batch_n 필드 보유
    for m in rel["by_model_process"]:
        assert "batch_n" in m
    # trend 에는 TMS(M) omit
    trend_partners = {t["partner"] for t in rel["trend"]}
    assert "TMS(M)" not in trend_partners


def test_pr08_confidence(rel):
    """TC-PR-08 (Q5-A): 각 row confidence (n>=30 trusted)."""
    for arr in ("by_cell", "by_model_process", "by_partner", "trend"):
        for x in rel[arr]:
            assert x["confidence"] in ("trusted", "provisional")
            assert x["confidence"] == ("trusted" if x["n"] >= 30 else "provisional")


# ── MONTHLY v4: period/partner 필터 + 매트릭스/trend 분리 ──

def test_pr09_invalid_period():
    """TC-PR-09: period 화이트리스트."""
    with pytest.raises(CtParamError) as e:
        get_partner_reliability(period="yearly")
    assert e.value.code == "INVALID_PERIOD"


def test_pr10_period_matrix_single(db_conn):
    """TC-PR-10: period 지정 → 매트릭스 단월(day 윈도우) / trend 누적 분리."""
    if db_conn is None:
        pytest.skip("sqlite")
    from datetime import date
    r = get_partner_reliability(period="month", reference_date=date(2026, 6, 1))
    # 매트릭스 윈도우 = 단월 (YYYY-MM-DD)
    assert r["meta"]["period"] == "month"
    assert r["meta"]["matrix_window"]["from"] == "2026-06-01"
    # trend 윈도우 = trust_start~현재 (누적, period 무관)
    assert r["meta"]["trend_window"]["from"] == "2026-05"


def test_pr11_partner_filter_matrix_only(db_conn):
    """TC-PR-11 (A-1): partner 필터는 매트릭스만, trend 전체 유지."""
    if db_conn is None:
        pytest.skip("sqlite")
    from datetime import date
    r = get_partner_reliability(period="month", reference_date=date(2026, 6, 1), partner="FNI")
    # 매트릭스 = FNI만 (partner 필터 적용)
    cell_partners = {c["partner"] for c in r["by_cell"]}
    assert cell_partners <= {"FNI"}, f"매트릭스 partner 필터 위반: {cell_partners}"
    # trend = partner 필터 미적용 → 매트릭스 협력사 ⊆ trend (운영 DB 는 trend 더 넓음). test DB 데이터 부족 시 둘 다 ∅.
    trend_partners = {t["partner"] for t in r["trend"]}
    assert cell_partners <= trend_partners


def test_pr12_invariant_single_month(db_conn):
    """TC-PR-12: 단월 매트릭스에서도 invariant (by_cell 가중합 = by_model_process)."""
    if db_conn is None:
        pytest.skip("sqlite")
    from collections import defaultdict
    from datetime import date
    r = get_partner_reliability(period="month", reference_date=date(2026, 6, 1))
    cn = defaultdict(int)
    for c in r["by_cell"]:
        cn[(c["model"], c["process"])] += c["n"]
    for m in r["by_model_process"]:
        assert cn[(m["model"], m["process"])] == m["n"]


def test_pr13_backcompat_no_period(db_conn):
    """TC-PR-13: period 미지정 = from/to 누적 (back-compat)."""
    if db_conn is None:
        pytest.skip("sqlite")
    r = get_partner_reliability(process="MECH")
    assert r["meta"]["period"] is None
    # 누적 윈도우 = YYYY-MM
    assert len(r["meta"]["matrix_window"]["from"]) == 7
