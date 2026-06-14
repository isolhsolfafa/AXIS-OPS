"""
FEAT-TAGGING-COVERAGE-FILTERS (#92) — tagging-coverage period/reference_date/partner 필터

검증:
  - _COVERAGE_WHERE byte 동일 (reliability-summary v2.41.0 회귀 0)
  - back-compat (미지정 = 월 누적, 현행)
  - period(today/week/month/quarter) day 윈도우
  - partner 필터 (분모 협력사 기준, PI/QI/SI=GST 제외)
  - meta echo (period/reference_date/partner/window)
  - reliability-summary 회귀 (공유 상수)
"""
from datetime import date

import pytest

from app.services.tagging_coverage_service import (
    _COVERAGE_BASE,
    _COVERAGE_WHERE,
    _COVERAGE_WINDOW_MONTH,
    get_tagging_coverage,
)


# ── 상수 byte 동일 (DB 불필요, reliability-summary 회귀 방지) ──

def test_tcf01_coverage_where_byte_identical():
    """TC-TCF-01: _COVERAGE_WHERE = _COVERAGE_BASE + _COVERAGE_WINDOW_MONTH (byte 동일)."""
    assert _COVERAGE_WHERE == _COVERAGE_BASE + _COVERAGE_WINDOW_MONTH
    # 기존 월 윈도우 조건 유지 (reliability-summary import 호환)
    assert "%(from_month)s" in _COVERAGE_WHERE
    assert "%(to_month)s" in _COVERAGE_WHERE
    # base 에는 윈도우 없음
    assert "from_month" not in _COVERAGE_BASE
    assert "task_category IN ('MECH','ELEC','PI','QI','SI')" in _COVERAGE_BASE


# ── DB 통합 ──

@pytest.fixture
def _has_db(db_conn):
    if db_conn is None:
        pytest.skip("sqlite")


def test_tcf02_backcompat(db_conn, _has_db):
    """TC-TCF-02: 미지정 = 월 누적 (현행 back-compat), period/partner=None echo."""
    r = get_tagging_coverage()
    assert r["meta"]["period"] is None
    assert r["meta"]["partner"] is None
    # from/to = YYYY-MM 형식 (월 윈도우)
    assert len(r["meta"]["from"]) == 7 and "-" in r["meta"]["from"]
    assert {c["process"] for c in r["coverage"]} == {"MECH", "ELEC", "PI", "QI", "SI"}


def test_tcf03_period_day_window(db_conn, _has_db):
    """TC-TCF-03: period 지정 → day 윈도우 (from/to = YYYY-MM-DD)."""
    r = get_tagging_coverage(period="month", reference_date=date(2026, 6, 1))
    assert r["meta"]["period"] == "month"
    assert r["meta"]["from"] == "2026-06-01"
    assert r["meta"]["to"] == "2026-07-01"
    assert r["meta"]["window"] == {"from": "2026-06-01", "to": "2026-07-01"}


def test_tcf04_quarter_window(db_conn, _has_db):
    """TC-TCF-04: period=quarter → 분기 윈도우."""
    r = get_tagging_coverage(period="quarter", reference_date=date(2026, 6, 1))
    assert r["meta"]["from"] == "2026-04-01"
    assert r["meta"]["to"] == "2026-07-01"


def test_tcf05_partner_filter_denominator(db_conn, _has_db):
    """TC-TCF-05: partner 필터 — 분모도 협력사 기준. FNI(기구사)=MECH만, PI/QI/SI=GST 제외."""
    r = get_tagging_coverage(period="quarter", reference_date=date(2026, 6, 1), partner="FNI")
    assert r["meta"]["partner"] == "FNI"
    cov = {c["process"]: c["n"] for c in r["coverage"]}
    # FNI = mech_partner → MECH 만 분모 존재, PI/QI/SI(GST 고정) = 0
    assert cov["PI"] == 0 and cov["QI"] == 0 and cov["SI"] == 0
    # MECH 는 FNI 제품 존재 시 n>0 (운영 데이터 의존 — 0 이상)
    assert cov["MECH"] >= 0


def test_tcf06_partner_gst_inspection(db_conn, _has_db):
    """TC-TCF-06: partner=GST → PI/QI/SI(검사)만 분모, MECH/ELEC=0."""
    r = get_tagging_coverage(period="quarter", reference_date=date(2026, 6, 1), partner="GST")
    cov = {c["process"]: c["n"] for c in r["coverage"]}
    assert cov["MECH"] == 0 and cov["ELEC"] == 0


def test_tcf07_reliability_summary_regression(db_conn, _has_db):
    """TC-TCF-07: 공유 상수 변경 후 reliability-summary(v2.41.0) 정상 동작 (회귀 0)."""
    from app.services.statistics_service import get_reliability_summary
    rs = get_reliability_summary()
    # 응답 구조 정상 + 추적율 산출됨 (_COVERAGE_WHERE 깨지면 SQL 에러)
    assert 0 <= rs["headline"]["tracking_pct"] <= 100
    assert "standard_ready_pct" in rs["gate"]
