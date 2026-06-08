"""
S-1 (FEAT-CT-BASIS-ACTIVE-TRUSTCUTOFF, VIEW OPS_API_REQUESTS #82 ⓐ) — CT basis/window pytest

설계서: CT_S1_BASIS_ACTIVE_DESIGN.md (v3, Codex 2라운드 통과본)

전략: test_sprint85 패턴 — 고유 serial prefix(S1CT)로 clean 데이터 seed → 산출 검증 → cleanup.
  - basis=active → active_time_minutes>0 모집단 / basis=duration → duration_minutes (act 필터 미적용)
  - 윈도우 = KST 월경계 반열림 [from월, to월+1). 기본 [2026-05, 현재월].
  - completed_at 은 5월+ KST literal 로 seed (윈도우 안에 들도록).

TC-S1-01~14.
"""
from __future__ import annotations

import re

import pytest

from app.services import statistics_service as ss

_FAKE = "S1_CT_FAKE"   # MECH 카테고리 fake task_id
_PREFIX = "S1CT"
# 윈도우(2026-05 ~ 현재월) 안에 확실히 드는 completed_at (5월 literal)
_MAY = "2026-05-15T10:00:00+09:00"


def _seed_product(db_conn, sn, model="GAIA-I", customer=None,
                  mech_partner=None, elec_partner=None, module_outsourcing=None):
    cur = db_conn.cursor()
    cur.execute(
        "INSERT INTO plan.product_info "
        "(serial_number, model, customer, mech_partner, elec_partner, module_outsourcing) "
        "VALUES (%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (serial_number) DO UPDATE SET model=EXCLUDED.model, customer=EXCLUDED.customer, "
        "mech_partner=EXCLUDED.mech_partner, elec_partner=EXCLUDED.elec_partner, "
        "module_outsourcing=EXCLUDED.module_outsourcing",
        (sn, model, customer, mech_partner, elec_partner, module_outsourcing),
    )
    cur.execute(
        "INSERT INTO qr_registry (qr_doc_id, serial_number, status) VALUES (%s,%s,'active') "
        "ON CONFLICT (qr_doc_id) DO NOTHING",
        (f"DOC_{sn}", sn),
    )
    db_conn.commit()


def _seed_task(db_conn, worker_id, sn, task_id, duration_min, *, source=None,
               category="MECH", completed_at=_MAY, close_reason=None, force_closed=False,
               active_min=None):
    """완료 task seed. completed_at = KST ISO literal (윈도우 검증용). active_min: None/0/양수."""
    cur = db_conn.cursor()
    cur.execute(
        """INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
             started_at, completed_at, duration_minutes, active_time_minutes,
             duration_source, close_reason, force_closed, is_applicable)
            VALUES (%s,%s,%s,%s,%s,%s,
                    %s::timestamptz - interval '3 hours', %s::timestamptz,
                    %s,%s,%s,%s,%s, TRUE)""",
        (worker_id, sn, f"DOC_{sn}", category, task_id, task_id,
         completed_at, completed_at,
         duration_min, active_min, source, close_reason, force_closed),
    )
    db_conn.commit()


def _seed_n(db_conn, worker, task_id, n, duration_min, tag, *, source=None, category="MECH",
            completed_at=_MAY, customer=None, model="GAIA-I", active_min=None,
            mech_partner=None):
    for i in range(n):
        sn = f"{_PREFIX}-{tag}{i:02d}"
        _seed_product(db_conn, sn, model=model, customer=customer, mech_partner=mech_partner)
        _seed_task(db_conn, worker, sn, task_id, duration_min, source=source, category=category,
                   completed_at=completed_at, active_min=active_min)


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
    ss._cache.clear()


@pytest.fixture
def worker(db_conn, create_test_worker):
    if db_conn is None:
        pytest.skip("DB 없음")
    return create_test_worker(email="s1ct@test.axisos.com", password="Test1234!",
                              name="S1CT", role="MECH", company="BAT")


def _find(rows, key, val="task_id"):
    return next((r for r in rows if r[val] == key), None)


# ───────── TC-S1-01: basis=active → act>0만 ─────────

def test_s1_01_active_excludes_zero_and_null(db_conn, worker):
    """basis=active → active_time_minutes>0 행만. act=0/NULL 제외."""
    try:
        _seed_n(db_conn, worker, _FAKE, 5, 120, "ACT", active_min=120)   # act>0
        _seed_n(db_conn, worker, _FAKE, 3, 200, "ZERO", active_min=0)    # act=0 (미추적)
        _seed_n(db_conn, worker, _FAKE, 2, 200, "NULL", active_min=None)  # act NULL (one-action)
        ss._cache.clear()
        r = ss.get_task_ct_stats(basis="active")
        t = _find(r["tasks"], _FAKE)
        assert t is not None and t["sample_size"] == 5, t
        assert r["meta"]["excluded_zero_active"] == 3
        assert r["meta"]["excluded_null_active"] == 2
    finally:
        _cleanup(db_conn)


# ───────── TC-S1-02: basis=duration → act 필터 미적용 (현행) ─────────

def test_s1_02_duration_ignores_active_filter(db_conn, worker):
    """basis=duration → active=0/NULL 이어도 duration 기반 전부 산출."""
    try:
        _seed_n(db_conn, worker, _FAKE, 4, 120, "D1", active_min=120)
        _seed_n(db_conn, worker, _FAKE, 4, 130, "D2", active_min=0)
        _seed_n(db_conn, worker, _FAKE, 4, 140, "D3", active_min=None)
        ss._cache.clear()
        r = ss.get_task_ct_stats(basis="duration")
        t = _find(r["tasks"], _FAKE)
        assert t is not None and t["sample_size"] == 12  # act 필터 미적용
        assert r["meta"]["basis"] == "duration"
        assert "excluded_zero_active" not in r["meta"]
    finally:
        _cleanup(db_conn)


# ───────── TC-S1-03: 기본 윈도우 (무파라미터) = 2026-05~현재월 ─────────

def test_s1_03_default_window(db_conn, worker):
    """기본 윈도우 = [2026-05, 현재월]. 4월(윈도우 밖) 제외 / 5월 포함."""
    try:
        _seed_n(db_conn, worker, _FAKE, 5, 120, "IN", completed_at="2026-05-10T10:00:00+09:00")
        _seed_n(db_conn, worker, _FAKE, 3, 999, "OUT", completed_at="2026-04-10T10:00:00+09:00")
        ss._cache.clear()
        r = ss.get_task_ct_stats()
        assert r["meta"]["window"]["from"] == "2026-05"
        assert re.match(r"^\d{4}-\d{2}$", r["meta"]["window"]["to"])
        t = _find(r["tasks"], _FAKE)
        assert t is not None and t["sample_size"] == 5  # 4월 제외
    finally:
        _cleanup(db_conn)


# ───────── TC-S1-04: 부분 from/to ─────────

def test_s1_04_partial_window(db_conn, worker):
    """from만 → to=현재월 / to만 → from=2026-05."""
    try:
        ss._cache.clear()
        r1 = ss.get_task_ct_stats(from_month="2026-06")
        assert r1["meta"]["window"]["from"] == "2026-06"
        assert re.match(r"^\d{4}-\d{2}$", r1["meta"]["window"]["to"])
        ss._cache.clear()
        r2 = ss.get_task_ct_stats(to_month="2026-06")
        assert r2["meta"]["window"]["from"] == "2026-05"
        assert r2["meta"]["window"]["to"] == "2026-06"
    finally:
        _cleanup(db_conn)


# ───────── TC-S1-05: 단월 from===to + KST 경계 반열림 ─────────

def test_s1_05_single_month_kst_boundary(db_conn, worker):
    """from=to=2026-05 → 5월만. 6/1 00:00 KST 는 반열림으로 5월 윈도우 밖."""
    try:
        _seed_n(db_conn, worker, _FAKE, 4, 120, "M5", completed_at="2026-05-31T23:00:00+09:00")
        # 2026-06-01 00:00 KST → 5월 윈도우 [.., 6/1 00:00) 밖
        _seed_n(db_conn, worker, _FAKE, 2, 999, "M6", completed_at="2026-06-01T00:30:00+09:00")
        ss._cache.clear()
        r = ss.get_task_ct_stats(from_month="2026-05", to_month="2026-05")
        t = _find(r["tasks"], _FAKE)
        assert t is not None and t["sample_size"] == 4  # 6/1 제외
    finally:
        _cleanup(db_conn)


# ───────── TC-S1-06: immature_window (from < 2026-05) ─────────

def test_s1_06_immature_window(db_conn, worker):
    try:
        ss._cache.clear()
        r = ss.get_task_ct_stats(from_month="2026-03")
        assert r["meta"]["immature_window"] is True
        ss._cache.clear()
        r2 = ss.get_task_ct_stats(from_month="2026-05")
        assert r2["meta"]["immature_window"] is False
    finally:
        _cleanup(db_conn)


# ───────── TC-S1-07: standard_status provisional (n<30) ─────────

def test_s1_07_standard_status(db_conn, worker):
    try:
        _seed_n(db_conn, worker, "S1_PROV", 5, 120, "PV")    # n<30
        _seed_n(db_conn, worker, "S1_STD", 32, 180, "ST")    # n>=30
        ss._cache.clear()
        tasks = ss.get_task_ct_stats()["tasks"]
        assert _find(tasks, "S1_PROV")["standard_status"] == "provisional"
        assert _find(tasks, "S1_STD")["standard_status"] == "standard"
    finally:
        _cleanup(db_conn)


# ───────── TC-S1-08: meta n_total/n_used/excluded 정합 ─────────

def test_s1_08_meta_population_keys(db_conn, worker):
    """active basis: n_total(clean 전체) >= n_used(산출) / excluded_zero+null 정합."""
    try:
        _seed_n(db_conn, worker, _FAKE, 6, 120, "U", active_min=120)
        _seed_n(db_conn, worker, _FAKE, 2, 200, "Z", active_min=0)
        _seed_n(db_conn, worker, _FAKE, 2, 200, "N", active_min=None)
        ss._cache.clear()
        m = ss.get_task_ct_stats(basis="active")["meta"]
        assert m["n_total"] == 10                       # clean eligible 전체 (act 필터 전, Tukey 전)
        # M-1: n_used = act>0 모집단(Tukey 전) = 10 − zero(2) − null(2) = 6
        assert m["n_used"] == 6
        # n_sample = Tukey 후 산출 표본 (이상치 없음 → 6). 하위호환 total_sample 동일.
        assert m["n_sample"] == 6, m["n_sample"]
        assert m["total_sample"] == m["n_sample"]
        assert m["excluded_zero_active"] == 2
        assert m["excluded_null_active"] == 2
        assert m["n_used"] <= m["n_total"]
    finally:
        _cleanup(db_conn)


# ───────── TC-S1-09: Tukey base_n>clipped_n → tukey_clipped ─────────

def test_s1_09_tukey_clipped_flag(db_conn, worker):
    try:
        _seed_n(db_conn, worker, _FAKE, 12, 120, "T")
        _seed_product(db_conn, f"{_PREFIX}-OUT")
        _seed_task(db_conn, worker, f"{_PREFIX}-OUT", _FAKE, 12000)  # outlier
        ss._cache.clear()
        r = ss.get_task_ct_stats()
        t = _find(r["tasks"], _FAKE)
        assert t is not None and t["max_hours"] < 50   # outlier 제거
        assert r["meta"]["tukey_clipped"] is True
    finally:
        _cleanup(db_conn)


# ───────── TC-S1-10: tracking_coverage_by_partner (FNI 고 / BAT 저) ─────────

def test_s1_10_tracking_coverage_by_partner(db_conn, worker):
    """basis=active 시 협력사별 추적 커버리지 노출 (생존편향 방어)."""
    try:
        # FNI: 5건 전부 act>0 (rate 1.0)
        _seed_n(db_conn, worker, _FAKE, 5, 120, "FNI", active_min=120, mech_partner="FNI")
        # BAT: 2건만 act>0, 3건 act=0 (rate 0.4)
        _seed_n(db_conn, worker, _FAKE, 2, 120, "BATa", active_min=120, mech_partner="BAT")
        _seed_n(db_conn, worker, _FAKE, 3, 120, "BATb", active_min=0, mech_partner="BAT")
        ss._cache.clear()
        m = ss.get_task_ct_stats(basis="active")["meta"]
        cov = {c["partner"]: c for c in m["tracking_coverage_by_partner"]}
        assert cov["FNI"]["n_total"] == 5 and cov["FNI"]["n_used"] == 5
        assert cov["FNI"]["tracked_rate"] == 1.0
        assert cov["BAT"]["n_total"] == 5 and cov["BAT"]["n_used"] == 2
        assert cov["BAT"]["tracked_rate"] == 0.4
        # duration basis 에는 coverage 없음
        ss._cache.clear()
        m2 = ss.get_task_ct_stats(basis="duration")["meta"]
        assert "tracking_coverage_by_partner" not in m2
    finally:
        _cleanup(db_conn)


# ───────── TC-S1-10b: coverage 슬라이스 정렬 (M-5) ─────────

def test_s1_10b_coverage_slice_aligned(db_conn, worker):
    """category 필터 시 coverage denominator 도 동일 필터 적용."""
    try:
        _seed_n(db_conn, worker, _FAKE, 4, 120, "MECH", active_min=120,
                mech_partner="FNI", category="MECH")
        _seed_n(db_conn, worker, "S1_ELEC", 6, 120, "ELEC", active_min=120, category="ELEC")
        ss._cache.clear()
        m = ss.get_task_ct_stats(basis="active", category="MECH")["meta"]
        total = sum(c["n_total"] for c in m["tracking_coverage_by_partner"])
        assert total == 4, m["tracking_coverage_by_partner"]  # ELEC 6건 제외
    finally:
        _cleanup(db_conn)


# ───────── TC-S1-11: 캐시 키 — 다른 basis/월 → 다른 결과 ─────────

def test_s1_11_cache_key_separation(db_conn, worker):
    try:
        _seed_n(db_conn, worker, _FAKE, 5, 120, "D", active_min=60)
        ss._cache.clear()
        rd = ss.get_task_ct_stats(basis="duration")
        ra = ss.get_task_ct_stats(basis="active")
        # duration median(2h) != active median(1h) → 캐시 혼선 없음
        td = _find(rd["tasks"], _FAKE)
        ta = _find(ra["tasks"], _FAKE)
        assert td["median_hours"] != ta["median_hours"]
        # 다른 윈도우 → 별 캐시 (as_of 갱신)
        r1 = ss.get_task_ct_stats(from_month="2026-05")
        r2 = ss.get_task_ct_stats(from_month="2026-06")
        assert r1["meta"]["window"]["from"] != r2["meta"]["window"]["from"]
    finally:
        _cleanup(db_conn)


# ───────── TC-S1-12: 입력검증 (CtParamError) ─────────

def test_s1_12_param_validation(db_conn, worker):
    with pytest.raises(ss.CtParamError) as e1:
        ss.get_task_ct_stats(basis="bogus")
    assert e1.value.code == "INVALID_BASIS"
    with pytest.raises(ss.CtParamError) as e2:
        ss.get_task_ct_stats(from_month="2026-5")  # YYYY-MM 위반
    assert e2.value.code == "INVALID_MONTH"
    with pytest.raises(ss.CtParamError) as e3:
        ss.get_task_ct_stats(from_month="2026-07", to_month="2026-05")
    assert e3.value.code == "INVALID_RANGE"


# ───────── TC-S1-13: TMS dirty / TEST 제외 회귀 ─────────

def test_s1_13_tms_test_excluded(db_conn, worker):
    try:
        _seed_n(db_conn, worker, "TANK_MODULE", 4, 30, "TM", category="TMS", active_min=30)
        _seed_n(db_conn, worker, _FAKE, 5, 120, "OK", active_min=120)
        # TEST CUSTOMER 제외
        _seed_n(db_conn, worker, _FAKE, 3, 120, "TC", active_min=120, customer="TEST CUSTOMER")
        ss._cache.clear()
        r = ss.get_task_ct_stats(basis="active")
        ids = {t["task_id"] for t in r["tasks"]}
        assert "TANK_MODULE" not in ids and _FAKE in ids
        t = _find(r["tasks"], _FAKE)
        assert t["sample_size"] == 5  # TEST CUSTOMER 3건 제외
    finally:
        _cleanup(db_conn)


# ───────── TC-S1-14: duration_stale_before 존재/부재 ─────────

def test_s1_14_duration_stale_before(db_conn, worker):
    """basis=duration + 5월 포함 → duration_stale_before 존재. basis=active → 부재."""
    try:
        ss._cache.clear()
        rd = ss.get_task_ct_stats(basis="duration", from_month="2026-05")
        assert rd["meta"].get("duration_stale_before") == "2026-06-01"
        ss._cache.clear()
        ra = ss.get_task_ct_stats(basis="active", from_month="2026-05")
        assert "duration_stale_before" not in ra["meta"]
        # Codex 최종 M-A: duration + 윈도우가 6월 이후만 → 경고 부재 (stale 경계 안 걸침)
        ss._cache.clear()
        rd2 = ss.get_task_ct_stats(basis="duration", from_month="2026-06")
        assert "duration_stale_before" not in rd2["meta"]
    finally:
        _cleanup(db_conn)


def test_s1_15_invalid_month_value(client, db_conn, create_test_admin, get_admin_auth_token):
    """Codex 최종 M-B: 2026-13 등 잘못된 월 → 400 (DB cast 500 방지)."""
    if db_conn is None:
        pytest.skip("DB 없음")
    admin = create_test_admin
    h = {"Authorization": f"Bearer {get_admin_auth_token(admin['id'])}"}
    assert client.get("/api/ct/task-stats?from=2026-13", headers=h).status_code == 400
    assert client.get("/api/ct/task-stats?from=2026-00", headers=h).status_code == 400


# ───────── route: basis/from/to 400 매핑 ─────────

def test_s1_route_param_errors(client, db_conn, create_test_admin, get_admin_auth_token):
    if db_conn is None:
        pytest.skip("DB 없음")
    admin = create_test_admin
    h = {"Authorization": f"Bearer {get_admin_auth_token(admin['id'])}"}
    assert client.get("/api/ct/task-stats?basis=active", headers=h).status_code == 200
    assert client.get("/api/ct/task-stats?basis=bogus", headers=h).status_code == 400
    assert client.get("/api/ct/task-stats?from=2026-5", headers=h).status_code == 400
    assert client.get("/api/ct/task-stats?from=2026-07&to=2026-05", headers=h).status_code == 400
    # period 는 무시 (제거됨) → 200
    assert client.get("/api/ct/task-stats?period=all", headers=h).status_code == 200
