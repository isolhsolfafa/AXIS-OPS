"""
#83 (FEAT-CT-PARTNER-BREAKDOWN, VIEW OPS_API_REQUESTS #83) — partner-breakdown pytest

설계서: CT_PARTNER_BREAKDOWN_DESIGN.md (Codex 2라운드 GO).

전략: 고유 serial prefix(PBCT)로 clean ct>0 데이터 직접 INSERT → 집계 검증 → cleanup.
  - basis=ct (ct_time_minutes>0) box plot + active median 병기.
  - partner = mech_partner/elec_partner/module_outsourcing 별 seed → 정규화 검증.
  - rollup median = 독립 GROUP BY (raw 합산 ≠ rollup median 입증, TC-PB-04).
  - completed_at = 5월+ KST literal (윈도우 안).

TC-PB-01~12 (+04/05/09b/10b 핵심).
"""
from __future__ import annotations

import pytest

from app.services import statistics_service as ss

_PREFIX = "PBCT"
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


def _seed_ct(db_conn, worker, sn, task_id, ct_min, active_min, *, category="MECH",
             completed_at=_MAY, duration_min=None, worker_count=1):
    """완료 task — ct/active 직접 INSERT (basis=ct 모집단)."""
    cur = db_conn.cursor()
    dur = duration_min if duration_min is not None else (active_min if active_min is not None else ct_min)
    cur.execute(
        """INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
             started_at, completed_at, duration_minutes, active_time_minutes, ct_time_minutes,
             worker_count, is_applicable)
            VALUES (%s,%s,%s,%s,%s,%s,
                    %s::timestamptz - interval '3 hours', %s::timestamptz,
                    %s,%s,%s,%s, TRUE) RETURNING id""",
        (worker, sn, f"DOC_{sn}", category, task_id, task_id,
         completed_at, completed_at, dur, active_min, ct_min, worker_count),
    )
    tid = cur.fetchone()[0]
    db_conn.commit()
    return tid


def _seed_unstarted(db_conn, worker, sn, task_id, *, category="MECH"):
    """applicable 인데 미시작 (started_at NULL) — 품질누락 모집단."""
    cur = db_conn.cursor()
    cur.execute(
        """INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable)
            VALUES (%s,%s,%s,%s,%s,%s, TRUE)""",
        (worker, sn, f"DOC_{sn}", category, task_id, task_id),
    )
    db_conn.commit()


def _seed_n(db_conn, worker, task_id, n, ct_min, active_min, tag, *, category="MECH",
            model="GAIA-I", mech_partner=None, elec_partner=None, module_outsourcing=None,
            customer=None, completed_at=_MAY, worker_count=1):
    for i in range(n):
        sn = f"{_PREFIX}-{tag}{i:03d}"
        _seed_product(db_conn, sn, model=model, customer=customer,
                      mech_partner=mech_partner, elec_partner=elec_partner,
                      module_outsourcing=module_outsourcing)
        _seed_ct(db_conn, worker, sn, task_id, ct_min, active_min, category=category,
                 completed_at=completed_at, worker_count=worker_count)


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
    return create_test_worker(email="pbct@test.axisos.com", password="Test1234!",
                              name="PBCT", role="MECH", company="BAT")


def _find_row(rows, **kw):
    for r in rows:
        if all(r.get(k) == v for k, v in kw.items()):
            return r
    return None


def _pt(rollups, partner_display, task_id, dual):
    return _find_row(rollups["partner_task"], partner_display=partner_display, task_id=task_id, dual=dual)


def _pm(rollups, partner_display, model):
    return _find_row(rollups["partner_model"], partner_display=partner_display, model=model)


# ───────── TC-PB-01: rows 4축 키 + standard_status 게이트 ─────────

def test_pb_01_standard_status_gate(db_conn, worker):
    """n<5 reject / 5~29 provisional(tukey 미적용) / 30+ standard."""
    try:
        _seed_n(db_conn, worker, "FNI_T1", 3, 120, 120, "R", mech_partner="FNI", model="GAIA")    # reject
        _seed_n(db_conn, worker, "FNI_T2", 10, 120, 120, "P", mech_partner="FNI", model="GAIA")   # provisional
        _seed_n(db_conn, worker, "FNI_T3", 35, 120, 120, "S", mech_partner="FNI", model="GAIA")   # standard
        ss._cache.clear()
        r = ss.get_partner_breakdown()
        rows = r["rows"]
        reject = _find_row(rows, task_id="FNI_T1")
        prov = _find_row(rows, task_id="FNI_T2")
        std = _find_row(rows, task_id="FNI_T3")
        assert reject["standard_status"] == "reject" and reject["n_raw"] == 3
        assert prov["standard_status"] == "provisional" and prov["tukey_applied"] is False
        assert std["standard_status"] == "standard" and std["tukey_applied"] is True
        # 4축 키 존재
        for k in ("partner_display", "partner_raw", "partner_scope", "model", "task_id", "dual"):
            assert k in std
        assert std["partner_display"] == "FNI" and std["partner_scope"] == "MECH"
    finally:
        _cleanup(db_conn)


# ───────── TC-PB-02: partner 정규화 — TMS → TMS(M)/TMS(E) ─────────

def test_pb_02_partner_normalization_tms(db_conn, worker):
    """mech_partner='TMS' → TMS(M) / elec_partner='TMS' → TMS(E). raw/display/scope."""
    try:
        _seed_n(db_conn, worker, "MTASK", 6, 120, 120, "M", category="MECH", mech_partner="TMS")
        _seed_n(db_conn, worker, "ETASK", 6, 120, 120, "E", category="ELEC", elec_partner="TMS")
        _seed_n(db_conn, worker, "MODTASK", 6, 120, 120, "MO", category="TMS", module_outsourcing="TMS")
        ss._cache.clear()
        r = ss.get_partner_breakdown()
        m = _find_row(r["rows"], task_id="MTASK")
        e = _find_row(r["rows"], task_id="ETASK")
        mo = _find_row(r["rows"], task_id="MODTASK")
        assert m["partner_display"] == "TMS(M)" and m["partner_raw"] == "TMS" and m["partner_scope"] == "MECH"
        assert e["partner_display"] == "TMS(E)" and e["partner_raw"] == "TMS" and e["partner_scope"] == "ELEC"
        assert mo["partner_display"] == "TMS(M)" and mo["partner_scope"] == "TMS"
    finally:
        _cleanup(db_conn)


# ───────── TC-PB-03: partner NULL — 자연제외 vs 품질누락 meta 분리 ─────────

def test_pb_03_meta_partner_missing_vs_quality_missing(db_conn, worker):
    """partner_display='(미지정)' = 자연제외(PI/QI/SI). 미시작 applicable = 품질누락."""
    try:
        # PI 검사 task → partner '(미지정)' (자연 제외)
        _seed_n(db_conn, worker, "PI_CHECK", 6, 90, 90, "PI", category="PI")
        # 정상 MECH ct>0
        _seed_n(db_conn, worker, "FNI_OK", 6, 120, 120, "OK", mech_partner="FNI")
        # applicable 미시작 (품질누락) — ct 없음
        for i in range(4):
            sn = f"{_PREFIX}-UNSTART{i:03d}"
            _seed_product(db_conn, sn, model="GAIA-I", mech_partner="FNI")
            _seed_unstarted(db_conn, worker, sn, "FNI_OK")
        ss._cache.clear()
        r = ss.get_partner_breakdown()
        meta = r["meta"]
        # PI 6건 → '(미지정)' partner_missing
        assert meta["excluded_partner_missing"] >= 6
        assert meta["excluded_quality_missing"] >= 4
        # PI 는 rows 에 partner_display='(미지정)' 로 등장
        pi = _find_row(r["rows"], task_id="PI_CHECK")
        assert pi["partner_display"] == "(미지정)"
    finally:
        _cleanup(db_conn)


# ───────── TC-PB-04: rollup 독립 median ≠ raw 합산 (M-1) ─────────

def test_pb_04_rollup_independent_median(db_conn, worker):
    """rollup median = 독립 GROUP BY percentile. raw rows median 합산과 다른 값.

    seed: 같은 (partner,task,dual) 안에 model A(n=3, ct=2h) + model B(n=3, ct=10h).
      - rows: model A median=2, model B median=10 (셀 분리)
      - partner_task rollup(model 무관): pooled 6개 median = (2,2,2,10,10,10) median=6
      - raw 합산(잘못된 방식): (2+10)/2 = 6 우연 일치 회피 위해 비대칭 n 사용.
    비대칭: model A n=5(ct=2), model B n=1(ct=20).
      - rows: A median=2, B median=20
      - rollup pooled (2,2,2,2,2,20) median=2  ← 독립 산출
      - raw 합산(평균식): (2+20)/2=11  ≠ 2  → 합산 금지 입증
    """
    try:
        _seed_n(db_conn, worker, "BAT_SPLIT", 5, 120, 120, "A", mech_partner="BAT", model="GAIA")    # 2h
        _seed_n(db_conn, worker, "BAT_SPLIT", 1, 1200, 1200, "B", mech_partner="BAT", model="DRAGON")  # 20h
        ss._cache.clear()
        r = ss.get_partner_breakdown()
        # rows 셀 분리
        row_a = _find_row(r["rows"], task_id="BAT_SPLIT", model="GAIA")
        row_b = _find_row(r["rows"], task_id="BAT_SPLIT", model="DRAGON")
        assert row_a["ct_median_hours"] == 2.0
        assert row_b["ct_median_hours"] == 20.0
        # rollup pooled median = 독립 산출 = 2.0 (NOT (2+20)/2=11)
        pt = _pt(r["rollups"], "BAT", "BAT_SPLIT", "SINGLE")
        assert pt is not None
        assert pt["ct_median_hours"] == 2.0, pt["ct_median_hours"]
        assert pt["ct_median_hours"] != round((2.0 + 20.0) / 2, 1)  # raw 합산 ≠ rollup
        assert pt["n"] == 6
    finally:
        _cleanup(db_conn)


# ───────── TC-PB-05: vs_task_standard_ratio (M-2) ─────────

def test_pb_05_vs_task_standard_ratio(db_conn, worker):
    """(task,dual) 표준 기준 비율. 표준 n<5 → null + insufficient_standard + standard_n."""
    try:
        # 표준 충분: WIRING SINGLE 모집단 = FNI 10개(ct=4h) + P&S 10개(ct=8h)
        #   (task,dual) pooled 20개 median ≈ 6h. FNI rollup median=4 → ratio≈0.67
        _seed_n(db_conn, worker, "WIRING", 10, 240, 240, "WF", category="ELEC", elec_partner="FNI")
        _seed_n(db_conn, worker, "WIRING", 10, 480, 480, "WP", category="ELEC", elec_partner="P&S")
        # 표준 부족: RARE_TASK SINGLE 2개만 → insufficient_standard
        _seed_n(db_conn, worker, "RARE_TASK", 2, 120, 120, "RT", category="ELEC", elec_partner="C&A")
        ss._cache.clear()
        r = ss.get_partner_breakdown()
        fni = _pt(r["rollups"], "FNI", "WIRING", "SINGLE")
        assert fni["vs_task_standard_status"] == "ok"
        assert fni["vs_task_standard_ratio"] is not None
        assert fni["vs_task_standard_ratio"] < 1.0  # FNI 4h < 표준 6h
        assert fni["standard_n"] == 20
        rare = _pt(r["rollups"], "C&A", "RARE_TASK", "SINGLE")
        assert rare["vs_task_standard_ratio"] is None
        assert rare["vs_task_standard_status"] == "insufficient_standard"
        assert rare["standard_n"] == 2
    finally:
        _cleanup(db_conn)


# ───────── TC-PB-06: instant_completion — one-click 화이트리스트 제외 ─────────

def test_pb_06_instant_whitelist(db_conn, worker):
    """TANK_DOCKING 등 화이트리스트 → instant_completion_applicable=false."""
    try:
        _seed_n(db_conn, worker, "TANK_DOCKING", 6, 5, 0, "TD", mech_partner="FNI")
        _seed_n(db_conn, worker, "FNI_NORMAL", 6, 120, 120, "NM", mech_partner="FNI")
        ss._cache.clear()
        r = ss.get_partner_breakdown()
        td = _find_row(r["rows"], task_id="TANK_DOCKING")
        nm = _find_row(r["rows"], task_id="FNI_NORMAL")
        assert td["instant_completion_applicable"] is False
        assert td["instant_excluded_reason"] == "one_click_whitelist"
        assert nm["instant_completion_applicable"] is True
        assert nm["instant_excluded_reason"] is None
        # rollup instant_completion_rate 는 substantive(화이트리스트 제외) 만 반영
        pt = _pt(r["rollups"], "FNI", "FNI_NORMAL", "SINGLE")
        assert pt["instant_completion_rate"] is not None
    finally:
        _cleanup(db_conn)


# ───────── TC-PB-07: tracking_coverage 동봉 + 속도 짝 ─────────

def test_pb_07_tracking_coverage(db_conn, worker):
    """n_used(ct>0)/n_total(clean eligible). 미추적 완료(ct=0)도 분모 포함."""
    try:
        # ct>0 6개 + ct=0 4개 (미추적) → coverage 6/10 = 0.6
        _seed_n(db_conn, worker, "BAT_COV", 6, 120, 120, "U", mech_partner="BAT")
        _seed_n(db_conn, worker, "BAT_COV", 4, 0, 0, "Z", mech_partner="BAT")  # ct=0 미추적
        ss._cache.clear()
        r = ss.get_partner_breakdown()
        pt = _pt(r["rollups"], "BAT", "BAT_COV", "SINGLE")
        cov = pt["tracking_coverage"]
        assert cov["n_total"] == 10
        assert cov["n_used"] == 6
        assert cov["tracked_rate"] == 0.6
    finally:
        _cleanup(db_conn)


# ───────── TC-PB-08: side_applicable — TANK_MODULE만 true ─────────

def test_pb_08_side_applicable(db_conn, worker):
    """TANK_MODULE side_applicable=true, 그 외 false."""
    try:
        # TANK_MODULE 은 _CLEAN_CORE 제외 → ct>0 로도 rows 미등장.
        # side_applicable 로직만 검증 — 일반 task false 확인 + 상수 검증.
        _seed_n(db_conn, worker, "FNI_TASK", 6, 120, 120, "F", mech_partner="FNI")
        ss._cache.clear()
        r = ss.get_partner_breakdown()
        f = _find_row(r["rows"], task_id="FNI_TASK")
        assert f["side_applicable"] is False
        assert "TANK_MODULE" in ss._SIDE_APPLICABLE_TASKS
    finally:
        _cleanup(db_conn)


# ───────── TC-PB-09: dual 분리 — SINGLE/DUAL 셀 분리 ─────────

def test_pb_09_dual_separation(db_conn, worker):
    """DUAL 모델 vs 단일 → 별 셀. 섞임 없음."""
    try:
        _seed_n(db_conn, worker, "FNI_D", 6, 120, 120, "S", mech_partner="FNI", model="GAIA")             # SINGLE
        _seed_n(db_conn, worker, "FNI_D", 6, 240, 240, "D", mech_partner="FNI", model="GAIA-I DUAL PUMP")  # DUAL
        ss._cache.clear()
        r = ss.get_partner_breakdown()
        single = _find_row(r["rows"], task_id="FNI_D", dual="SINGLE")
        dual = _find_row(r["rows"], task_id="FNI_D", dual="DUAL")
        assert single is not None and dual is not None
        assert single["ct_median_hours"] == 2.0
        assert dual["ct_median_hours"] == 4.0
        # rollup 도 dual 별 분리
        pt_s = _pt(r["rollups"], "FNI", "FNI_D", "SINGLE")
        pt_d = _pt(r["rollups"], "FNI", "FNI_D", "DUAL")
        assert pt_s["n"] == 6 and pt_d["n"] == 6
    finally:
        _cleanup(db_conn)


# ───────── TC-PB-09b: partner_display rollup 키 (M-3) + GST category_mix ─────────

def test_pb_09b_partner_display_rollup_and_gst_mix(db_conn, worker):
    """TMS raw → TMS(M)/TMS(E) 분리 rollup. GST(PI+QI+SI) → category_mix 다중."""
    try:
        # TMS mech + TMS elec → display 분리
        _seed_n(db_conn, worker, "TMS_M_TASK", 6, 120, 120, "TM", category="MECH", mech_partner="TMS")
        _seed_n(db_conn, worker, "TMS_E_TASK", 6, 120, 120, "TE", category="ELEC", elec_partner="TMS")
        # GST 내부검사 PI/QI/SI → partner '(미지정)' multi-category
        _seed_n(db_conn, worker, "PI_T", 6, 90, 90, "QPI", category="PI")
        _seed_n(db_conn, worker, "QI_T", 6, 90, 90, "QQI", category="QI")
        ss._cache.clear()
        r = ss.get_partner_breakdown()
        # partner_model rollup 에서 TMS(M)/TMS(E) 분리
        pm_keys = {(x["partner_display"]) for x in r["rollups"]["partner_model"]}
        assert "TMS(M)" in pm_keys and "TMS(E)" in pm_keys
        # '(미지정)' rollup category_mix 에 PI/QI 둘 다
        misc = [x for x in r["rollups"]["partner_model"] if x["partner_display"] == "(미지정)"]
        assert misc, "GST/(미지정) rollup 없음"
        mix = set()
        for x in misc:
            mix.update(x["category_mix"])
        assert "PI" in mix and "QI" in mix
    finally:
        _cleanup(db_conn)


# ───────── TC-PB-10: 회귀 — task-stats/data-quality 응답 불변 ─────────

def test_pb_10_regression_task_stats_unchanged(db_conn, worker):
    """get_partner_breakdown 신규 함수 — task-stats/data-quality 키 구조 불변."""
    try:
        _seed_n(db_conn, worker, "FNI_REG", 6, 120, 120, "R", mech_partner="FNI")
        ss._cache.clear()
        ts = ss.get_task_ct_stats(basis="ct")
        assert set(ts.keys()) == {"tasks", "categories", "meta"}
        assert "rows" not in ts and "rollups" not in ts
        dq = ss.get_data_quality()
        assert set(dq.keys()) == {"duration_source_dist", "auto_close_trend", "training_impact", "meta"}
    finally:
        _cleanup(db_conn)


# ───────── TC-PB-10b: BE composite 미합성 (A-3) ─────────

def test_pb_10b_no_composite_score(db_conn, worker):
    """rollup 에 즉시완료율·coverage·vs_std 단독만. 통합 score 키 부재."""
    try:
        _seed_n(db_conn, worker, "FNI_NC", 8, 120, 120, "N", mech_partner="FNI")
        ss._cache.clear()
        r = ss.get_partner_breakdown()
        pt = _pt(r["rollups"], "FNI", "FNI_NC", "SINGLE")
        # 단독 지표 존재
        for k in ("instant_completion_rate", "tracking_coverage", "vs_task_standard_ratio"):
            assert k in pt
        # 통합 score 류 키 부재
        for bad in ("score", "composite", "composite_score", "rank", "overall_score", "weighted_score"):
            assert bad not in pt, f"composite 키 노출: {bad}"
    finally:
        _cleanup(db_conn)


# ───────── TC-PB-11: meta 진단 + 재현성 ─────────

def test_pb_11_meta_diagnostics(db_conn, worker):
    """excluded_* 카운트 + exclusion_ver/garbage_excluded=false/dag_ver."""
    try:
        _seed_n(db_conn, worker, "FNI_M", 6, 120, 120, "OK", mech_partner="FNI")
        _seed_n(db_conn, worker, "FNI_M", 3, 0, 0, "Z", mech_partner="FNI")  # ct=0
        ss._cache.clear()
        r = ss.get_partner_breakdown()
        m = r["meta"]
        for k in ("excluded_partner_missing", "excluded_quality_missing",
                  "excluded_null_ct", "excluded_zero_ct", "exclusion_ver",
                  "dag_ver", "garbage_excluded", "calendar_ver", "basis", "window"):
            assert k in m, f"meta 키 누락: {k}"
        assert m["basis"] == "ct"
        assert m["garbage_excluded"] is False
        assert m["dag_ver"] == "none"
        assert m["excluded_zero_ct"] >= 3
    finally:
        _cleanup(db_conn)


# ───────── TC-PB-12: 입력검증 — from/to YYYY-MM / from>to → CtParamError ─────────

def test_pb_12_input_validation(db_conn, worker):
    """S-1 _resolve_window 재사용 — 형식 위반/역전 → CtParamError."""
    try:
        with pytest.raises(ss.CtParamError) as e1:
            ss.get_partner_breakdown(from_month="2026-13")
        assert e1.value.code == "INVALID_MONTH"
        with pytest.raises(ss.CtParamError) as e2:
            ss.get_partner_breakdown(from_month="2026-06", to_month="2026-05")
        assert e2.value.code == "INVALID_RANGE"
        with pytest.raises(ss.CtParamError):
            ss.get_partner_breakdown(from_month="bad")
    finally:
        _cleanup(db_conn)
