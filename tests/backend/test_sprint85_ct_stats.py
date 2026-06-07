"""
Sprint 85 (FEAT-CT-ANALYSIS-HUB-BE-MVP-20260605) — CT 분석 허브 BE pytest

①데이터신뢰도 + ②CT표준(IQR, man-hour). 설계서: AGENT_TEAM_LAUNCH.md § Sprint 85

전략: 테스트 DB 는 운영 데이터가 없으므로 각 테스트가 고유 serial prefix(S85CT)로
clean 데이터를 seed → 산출 검증 → cleanup. man-hour = duration_minutes/60 SSoT.
clean = NULL/NORMAL only. TMS(M)·TEST·ATTENDANCE_OUT·추정 source 제외.

TC CT-01~15.
"""
from __future__ import annotations

import pytest

from app.services import statistics_service as ss

_FAKE = "S85_CT_FAKE"   # MECH 카테고리 fake task_id
_PREFIX = "S85CT"


def _seed_product(db_conn, sn, model="GAIA-I", customer=None):
    cur = db_conn.cursor()
    cur.execute(
        "INSERT INTO plan.product_info (serial_number, model, customer) VALUES (%s,%s,%s) "
        "ON CONFLICT (serial_number) DO UPDATE SET model=EXCLUDED.model, customer=EXCLUDED.customer",
        (sn, model, customer),
    )
    cur.execute(
        "INSERT INTO qr_registry (qr_doc_id, serial_number, status) VALUES (%s,%s,'active') "
        "ON CONFLICT (qr_doc_id) DO NOTHING",
        (f"DOC_{sn}", sn),
    )
    db_conn.commit()


def _seed_task(db_conn, worker_id, sn, task_id, duration_min, source=None,
               category="MECH", completed_at=None, close_reason=None, force_closed=False):
    """완료 task seed. completed_at=None → now(). 아니면 KST ISO literal."""
    cur = db_conn.cursor()
    if completed_at is None:
        comp_sql, started_sql, ts_params = "now()", "now() - interval '3 hours'", ()
    else:
        comp_sql = "%s::timestamptz"
        started_sql = "%s::timestamptz - interval '3 hours'"
        ts_params = (completed_at, completed_at)
    cur.execute(
        f"""INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
             started_at, completed_at, duration_minutes, duration_source, close_reason, force_closed, is_applicable)
            VALUES (%s,%s,%s,%s,%s,%s, {started_sql}, {comp_sql}, %s, %s, %s, %s, TRUE)""",
        (worker_id, sn, f"DOC_{sn}", category, task_id, task_id, *ts_params,
         duration_min, source, close_reason, force_closed),
    )
    db_conn.commit()


def _seed_n(db_conn, worker, task_id, n, duration_min, tag, *, source=None, category="MECH",
            completed_at=None, close_reason=None, force_closed=False, customer=None, model="GAIA-I"):
    """n개 인스턴스 seed (serial = S85CT-{tag}{i})."""
    for i in range(n):
        sn = f"{_PREFIX}-{tag}{i:02d}"
        _seed_product(db_conn, sn, model=model, customer=customer)
        _seed_task(db_conn, worker, sn, task_id, duration_min, source=source, category=category,
                   completed_at=completed_at, close_reason=close_reason, force_closed=force_closed)


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
    return create_test_worker(email="s85@test.axisos.com", password="Test1234!",
                              name="S85", role="MECH", company="BAT")


def _find(rows, key, val="task_id"):
    return next((r for r in rows if r[val] == key), None)


# ───────── ② CT 표준 (man-hour box plot) ─────────

def test_ct02_boxplot_monotonic(db_conn, worker):
    try:
        for i, d in enumerate([60, 90, 110, 120, 140, 180, 240, 300]):
            sn = f"{_PREFIX}-B{i}"
            _seed_product(db_conn, sn)
            _seed_task(db_conn, worker, sn, _FAKE, d)
        ss._cache.clear()
        t = _find(ss.get_task_ct_stats()["tasks"], _FAKE)
        assert t is not None
        assert t["min_hours"] <= t["q1_hours"] <= t["median_hours"] <= t["q3_hours"] <= t["max_hours"]
        assert t["iqr_hours"] == round(t["q3_hours"] - t["q1_hours"], 1)
    finally:
        _cleanup(db_conn)


def test_ct01_tms_excluded(db_conn, worker):
    """TMS(M) dirty task(TANK_MODULE) + TMS 카테고리 제외, 정상 MECH 는 표시."""
    try:
        _seed_n(db_conn, worker, "TANK_MODULE", 4, 30, "TM", category="TMS")
        _seed_n(db_conn, worker, _FAKE, 5, 120, "OK")
        ss._cache.clear()
        r = ss.get_task_ct_stats()
        ids = {t["task_id"] for t in r["tasks"]}
        assert "TANK_MODULE" not in ids and _FAKE in ids
        assert "TMS" not in {c["category"] for c in r["categories"]}
    finally:
        _cleanup(db_conn)


def test_ct03_tukey_outlier_clipped(db_conn, worker):
    """극단 outlier(200h) → fence 밖 → max_hours 미반영."""
    try:
        _seed_n(db_conn, worker, _FAKE, 12, 120, "T")
        _seed_product(db_conn, f"{_PREFIX}-OUT")
        _seed_task(db_conn, worker, f"{_PREFIX}-OUT", _FAKE, 12000)
        ss._cache.clear()
        t = _find(ss.get_task_ct_stats()["tasks"], _FAKE)
        assert t is not None and t["max_hours"] < 50, f"outlier 미제거 max={t['max_hours'] if t else None}"
    finally:
        _cleanup(db_conn)


def test_ct04_confidence_threshold(db_conn, worker):
    """n<30 low / 30~99 medium."""
    try:
        _seed_n(db_conn, worker, "S85_LOW", 5, 120, "L")
        _seed_n(db_conn, worker, "S85_MED", 32, 180, "M")
        ss._cache.clear()
        tasks = ss.get_task_ct_stats()["tasks"]
        assert _find(tasks, "S85_LOW")["confidence"] == "low"
        assert _find(tasks, "S85_MED")["confidence"] == "medium"
    finally:
        _cleanup(db_conn)


def test_ct05_instance_level_count(db_conn, worker):
    try:
        for i in range(6):
            sn = f"{_PREFIX}-I{i}"
            _seed_product(db_conn, sn)
            _seed_task(db_conn, worker, sn, _FAKE, 120 + i)
        ss._cache.clear()
        t = _find(ss.get_task_ct_stats()["tasks"], _FAKE)
        assert t is not None and t["sample_size"] == 6
    finally:
        _cleanup(db_conn)


def test_ct06_category_pooled_median(db_conn, worker):
    try:
        _seed_n(db_conn, worker, _FAKE, 6, 120, "C")
        ss._cache.clear()
        cats = ss.get_task_ct_stats()["categories"]
        mech = _find(cats, "MECH", "category")
        assert mech is not None
        assert "pooled_median_hours" in mech and "total_iqr_hours" not in mech
        assert set(mech) >= {"category", "label_ko", "task_count", "sample_size", "confidence"}
    finally:
        _cleanup(db_conn)


def test_ct07_meta_keys_and_cache(db_conn, worker):
    try:
        _seed_n(db_conn, worker, _FAKE, 5, 120, "MK")
        ss._cache.clear()
        r1 = ss.get_task_ct_stats()
        m = r1["meta"]
        for k in ("as_of", "lookback_days", "total_sample", "model_distribution",
                  "excluded_by_source", "excluded_pct", "median_basis", "confidence_scope"):
            assert k in m, k
        assert m["median_basis"] == "pooled_clean_instances"
        assert ss.get_task_ct_stats()["meta"]["as_of"] == r1["meta"]["as_of"]  # 캐시 hit
    finally:
        _cleanup(db_conn)


def test_ct16_dual_filter(db_conn, worker):
    """VIEW #81 — dual/single 분리 (model ILIKE '%DUAL%')."""
    try:
        for i in range(5):  # 단일 모델
            _seed_product(db_conn, f"{_PREFIX}-S{i}", model="GAIA-I")
            _seed_task(db_conn, worker, f"{_PREFIX}-S{i}", _FAKE, 120)
        for i in range(5):  # DUAL 모델
            _seed_product(db_conn, f"{_PREFIX}-U{i}", model="GAIA-I DUAL")
            _seed_task(db_conn, worker, f"{_PREFIX}-U{i}", _FAKE, 300)
        ss._cache.clear()
        single = _find(ss.get_task_ct_stats(dual="single")["tasks"], _FAKE)
        ss._cache.clear()
        dual = _find(ss.get_task_ct_stats(dual="dual")["tasks"], _FAKE)
        ss._cache.clear()
        allr = ss.get_task_ct_stats(dual=None)
        # single=GAIA-I 5건만 / dual=GAIA-I DUAL 5건만 / 합산 meta dual_scope
        assert single is not None and single["sample_size"] == 5
        assert dual is not None and dual["sample_size"] == 5
        assert single["median_hours"] < dual["median_hours"]  # 단일(2h) < DUAL(5h)
        assert allr["meta"]["dual_scope"] == "all"
    finally:
        _cleanup(db_conn)


def test_ct12_model_filter(db_conn, worker):
    try:
        for i in range(4):
            _seed_product(db_conn, f"{_PREFIX}-G{i}", model="GAIA-I")
            _seed_task(db_conn, worker, f"{_PREFIX}-G{i}", _FAKE, 120)
        for i in range(4):
            _seed_product(db_conn, f"{_PREFIX}-D{i}", model="DRAGON")
            _seed_task(db_conn, worker, f"{_PREFIX}-D{i}", _FAKE, 300)
        ss._cache.clear()
        r = ss.get_task_ct_stats(model="GAIA")
        assert r["meta"]["confidence_scope"] == "filtered"
        assert all(md["model"].upper().startswith("GAIA") for md in r["meta"]["model_distribution"])
        t = _find(r["tasks"], _FAKE)
        assert t is not None and t["sample_size"] == 4  # DRAGON 제외
    finally:
        _cleanup(db_conn)


def test_ct13_attendance_out_excluded(db_conn, worker):
    """clean = NULL/NORMAL only — ATTENDANCE_OUT 제외(Codex M-Q3)."""
    try:
        _seed_n(db_conn, worker, _FAKE, 5, 120, "CL")            # clean
        _seed_n(db_conn, worker, _FAKE, 5, 600, "AO", source="ATTENDANCE_OUT")
        ss._cache.clear()
        t = _find(ss.get_task_ct_stats()["tasks"], _FAKE)
        assert t is not None and t["sample_size"] == 5
    finally:
        _cleanup(db_conn)


def test_ct15_excluded_source_meta(db_conn, worker):
    """추정 source(PREV_DAY_CAP) → 통계 제외 + meta excluded_by_source 노출."""
    try:
        _seed_n(db_conn, worker, _FAKE, 8, 120, "CL")
        _seed_n(db_conn, worker, _FAKE, 2, 1000, "PD", source="PREV_DAY_CAP")
        ss._cache.clear()
        r = ss.get_task_ct_stats()
        t = _find(r["tasks"], _FAKE)
        assert t is not None and t["sample_size"] == 8           # 추정 2건 통계 제외
        assert r["meta"]["excluded_by_source"].get("PREV_DAY_CAP") == 2
        assert 0.0 <= r["meta"]["excluded_pct"] <= 100.0
    finally:
        _cleanup(db_conn)


# ───────── ① 데이터 신뢰도 ─────────

def test_ct08_duration_source_dist(db_conn, worker):
    try:
        _seed_n(db_conn, worker, _FAKE, 6, 120, "N")                                  # NULL
        _seed_n(db_conn, worker, _FAKE, 2, 1000, "P", source="PREV_DAY_CAP")
        ss._cache.clear()
        dist = ss.get_data_quality()["duration_source_dist"]
        assert dist and abs(sum(x["pct"] for x in dist) - 100.0) < 1.0
        for x in dist:
            assert x["clean"] == (x["source"] in ("NULL", "NORMAL_COMPLETION"))
        assert _find(dist, "NULL", "source")["clean"] is True
        assert _find(dist, "PREV_DAY_CAP", "source")["clean"] is False
    finally:
        _cleanup(db_conn)


def test_ct09_auto_close_trend_invariant(db_conn, worker):
    try:
        _seed_n(db_conn, worker, _FAKE, 6, 120, "NM")                                  # normal
        _seed_n(db_conn, worker, _FAKE, 2, 120, "AU", close_reason="AUTO_CLOSED_BY_FIRST_FINAL_TRIGGER:X")
        _seed_n(db_conn, worker, _FAKE, 1, 120, "FC", force_closed=True, close_reason="MANUAL_FORCE_CLOSE")
        ss._cache.clear()
        trend = ss.get_data_quality()["auto_close_trend"]
        assert trend
        for x in trend:
            assert len(x["month"]) == 7 and x["month"][4] == "-"   # YYYY-MM (KST)
            assert x["normal"] + x["auto"] + x["force"] == x["total"]
            assert x["auto_rate"] == (round(x["auto"] / x["total"] * 100, 1) if x["total"] else 0.0)
    finally:
        _cleanup(db_conn)


def test_ct10_training_pre_post(db_conn, worker):
    """6/2 KST 전후 분리 + post n<30 → insufficient_sample."""
    try:
        _seed_n(db_conn, worker, _FAKE, 6, 1500, "PRE", completed_at="2026-05-20T10:00:00+09:00")  # 25h pre
        _seed_n(db_conn, worker, _FAKE, 6, 480, "POST", completed_at="2026-06-03T10:00:00+09:00")  # 8h post
        ss._cache.clear()
        row = _find(ss.get_data_quality()["training_impact"], _FAKE)
        assert row is not None
        assert row["pre_n"] == 6 and row["post_n"] == 6
        assert row["pre_mh"] > row["post_mh"]                 # 교육 후 단축
        assert row["confidence"] == "insufficient_sample"    # post 6 < 30
    finally:
        _cleanup(db_conn)


# ───────── route (권한 / period) ─────────

def test_ct11_authz(client, db_conn, create_test_worker, create_test_admin, get_admin_auth_token, get_auth_token):
    if db_conn is None:
        pytest.skip("DB 없음")
    admin = create_test_admin
    gst = create_test_worker(email="s85gst@test.axisos.com", password="Test1234!",
                             name="GST검사", role="QI", company="GST")
    partner = create_test_worker(email="s85bat@test.axisos.com", password="Test1234!",
                                 name="협력", role="MECH", company="BAT", is_manager=True)
    h = lambda tok: {"Authorization": f"Bearer {tok}"}
    assert client.get("/api/ct/task-stats", headers=h(get_admin_auth_token(admin["id"]))).status_code == 200
    assert client.get("/api/ct/task-stats", headers=h(get_auth_token(gst))).status_code == 200
    assert client.get("/api/ct/task-stats", headers=h(get_auth_token(partner))).status_code == 403


def test_ct14_period_whitelist(client, db_conn, create_test_admin, get_admin_auth_token):
    if db_conn is None:
        pytest.skip("DB 없음")
    admin = create_test_admin
    h = {"Authorization": f"Bearer {get_admin_auth_token(admin['id'])}"}
    assert client.get("/api/ct/task-stats?period=last_90d", headers=h).status_code == 200
    assert client.get("/api/ct/task-stats?period=all", headers=h).status_code == 400
