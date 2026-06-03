"""
Sprint 81 (FEAT-FORCE-CLOSED-PARTNER-MATRIX-2AXIS-20260602, #79)

강제 종료(force_closed=TRUE) 협력사 2축 매트릭스:
  - partner_task_matrix    — 협력사 × 공정
  - partner_elapsed_matrix — 협력사 × 처리 기간 버킷 (미시작/1일내/1~3일/3~7일/7일+)

pytest TC catalog (FM-01 ~ FM-10):
  FM-01 force 0건            → 두 매트릭스 rows:[] / grand_total:0
  FM-02 force N건            → grand_total == force_count (두 매트릭스 + invariant)
  FM-03 미시작 force         → '미시작' 버킷 집계
  FM-04 미시작 + elapsed=0   → '미시작' 버킷 (원안 '1일내' 오분류 차단, 핵심 TC)
  FM-05 elapsed 경계값       → 1439/1440/4319/4320/10079/10080 버킷 분류
  FM-06 company 분기         → BAT/TMS(M)/TMS(E) _COMPANY_SQL 정합
  FM-07 GST 자사(QI/SI)      → '(미지정)' 분류
  FM-08 invariant 위반       → _assert_invariants 500
  FM-09 manager partner 격리 → 자기 회사 force 만
  FM-10 회귀                 → auto 매트릭스 / KPI 3분류 불변

설계서: AGENT_TEAM_LAUNCH.md § Sprint 81 (#79)
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

import pytest

from app.services import dashboard_service as ds
from app.services.dashboard_service import (
    build_auto_close_summary,
    _assert_invariants,
    InvariantViolationError,
)


# ---------------------------------------------------------------------------
# Helper — DB seed (force_closed 전용)
# ---------------------------------------------------------------------------

def _seed_product(db_conn, sn, mech_partner=None, elec_partner=None,
                  module_outsourcing=None):
    cur = db_conn.cursor()
    cur.execute("""
        INSERT INTO plan.product_info
            (serial_number, model, mech_partner, elec_partner, module_outsourcing)
        VALUES (%s, 'GAIA', %s, %s, %s)
        ON CONFLICT (serial_number) DO UPDATE SET
            mech_partner = EXCLUDED.mech_partner,
            elec_partner = EXCLUDED.elec_partner,
            module_outsourcing = EXCLUDED.module_outsourcing
    """, (sn, mech_partner, elec_partner, module_outsourcing))
    cur.execute("""
        INSERT INTO qr_registry (qr_doc_id, serial_number, status)
        VALUES (%s, %s, 'active')
        ON CONFLICT (qr_doc_id) DO NOTHING
    """, (f"DOC_{sn}", sn))
    db_conn.commit()


def _seed_force_task(
    db_conn, worker_id, sn, task_id, task_name, task_category,
    completed_at, started_at=None, elapsed_minutes=None,
    closed_by=None, workers_started: Optional[List[int]] = None,
    force_closed: bool = True,
    close_reason: str = "MANUAL_FORCE_CLOSE",
) -> int:
    """강제 종료 task seed — force_closed/elapsed_minutes/started_at 명시."""
    cur = db_conn.cursor()
    cur.execute("""
        INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
             started_at, completed_at, elapsed_minutes, close_reason, closed_by,
             force_closed, is_applicable)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE)
        RETURNING id
    """, (worker_id, sn, f"DOC_{sn}", task_category, task_id, task_name,
          started_at, completed_at, elapsed_minutes, close_reason, closed_by,
          force_closed))
    tid = cur.fetchone()[0]
    if workers_started:
        for wid in workers_started:
            cur.execute("""
                INSERT INTO work_start_log
                    (task_id, worker_id, serial_number, qr_doc_id,
                     task_category, task_id_ref, task_name, started_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (tid, wid, sn, f"DOC_{sn}", task_category, task_id, task_name,
                  started_at or completed_at - timedelta(hours=4)))
    db_conn.commit()
    return tid


def _cleanup(db_conn, serials: List[str]):
    cur = db_conn.cursor()
    for tbl in ("work_completion_log", "work_start_log", "app_task_details",
                "qr_registry"):
        cur.execute(f"DELETE FROM {tbl} WHERE serial_number = ANY(%s)", (serials,))
    cur.execute("DELETE FROM plan.product_info WHERE serial_number = ANY(%s)", (serials,))
    db_conn.commit()


def _row_for(matrix, company):
    for r in matrix["rows"]:
        if r["company"] == company:
            return r
    return None


def _bucket_idx(matrix, key):
    for i, c in enumerate(matrix["task_columns"]):
        if c["task_id"] == key:
            return i
    raise AssertionError(f"bucket {key} not in columns {matrix['task_columns']}")


# ---------------------------------------------------------------------------
# Fixture — 메인 force 데이터 (admin 뷰 검증용)
# ---------------------------------------------------------------------------

@pytest.fixture
def seed_s81_main(db_conn, create_test_worker):
    if db_conn is None:
        pytest.skip("DB not available")

    w_bat = create_test_worker(
        email="s81-bat-w@test.axisos.com", password="Test1234!",
        name="S81 BAT W", role="MECH", company="BAT")
    w_fni = create_test_worker(
        email="s81-fni-w@test.axisos.com", password="Test1234!",
        name="S81 FNI W", role="MECH", company="FNI")
    w_tms = create_test_worker(
        email="s81-tms-w@test.axisos.com", password="Test1234!",
        name="S81 TMS W", role="MECH", company="TMS(M)")
    w_ca = create_test_worker(
        email="s81-ca-w@test.axisos.com", password="Test1234!",
        name="S81 C&A W", role="ELEC", company="C&A")
    w_gst = create_test_worker(
        email="s81-gst-w@test.axisos.com", password="Test1234!",
        name="S81 GST W", role="QI", company="GST")
    admin = create_test_worker(
        email="s81-admin@test.axisos.com", password="Test1234!",
        name="S81 Admin", role="QI", is_admin=True)

    today = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
    started = today - timedelta(hours=4)
    serials: List[str] = []

    def add(sn, **kw):
        serials.append(sn)
        return sn

    # BAT MECH — started, 1일내 (elapsed 600)
    sn1 = add("S81-SN-001")
    _seed_product(db_conn, sn1, mech_partner="BAT")
    _seed_force_task(db_conn, w_bat, sn1, "PANEL_WORK", "판넬 작업", "MECH",
                     today, started, elapsed_minutes=600, closed_by=admin,
                     workers_started=[w_bat])

    # BAT MECH — started, 1~3일 (elapsed 2000)
    sn2 = add("S81-SN-002")
    _seed_product(db_conn, sn2, mech_partner="BAT")
    _seed_force_task(db_conn, w_bat, sn2, "gas1", "Gas 1", "MECH",
                     today, started, elapsed_minutes=2000, closed_by=admin,
                     workers_started=[w_bat])

    # FNI MECH — 미시작 (started_at NULL)
    sn3 = add("S81-SN-003")
    _seed_product(db_conn, sn3, mech_partner="FNI")
    _seed_force_task(db_conn, w_fni, sn3, "gas2", "Gas 2", "MECH",
                     today, None, elapsed_minutes=None, closed_by=admin)

    # TMS(M) MECH — started, 3~7일 (elapsed 5000)
    sn4 = add("S81-SN-004")
    _seed_product(db_conn, sn4, mech_partner="TMS")
    _seed_force_task(db_conn, w_tms, sn4, "TANK_MODULE", "Tank Module", "MECH",
                     today, started, elapsed_minutes=5000, closed_by=admin,
                     workers_started=[w_tms])

    # C&A ELEC — started, 7일+ (elapsed 11000)
    sn5 = add("S81-SN-005")
    _seed_product(db_conn, sn5, elec_partner="C&A")
    _seed_force_task(db_conn, w_ca, sn5, "WIRING", "배선 포설", "ELEC",
                     today, started, elapsed_minutes=11000, closed_by=admin,
                     workers_started=[w_ca])

    # GST QI — started, 1일내 → (미지정) 분류
    sn6 = add("S81-SN-006")
    _seed_product(db_conn, sn6, mech_partner="BAT")  # QI category → partner 무관 (미지정)
    _seed_force_task(db_conn, w_gst, sn6, "QI_CHECK", "공정검사", "QI",
                     today, started, elapsed_minutes=100, closed_by=admin,
                     workers_started=[w_gst])

    data = {
        "admin": admin, "w_bat": w_bat, "w_fni": w_fni, "w_tms": w_tms,
        "w_ca": w_ca, "w_gst": w_gst, "serials": serials,
        "ref_date": today.date(), "force_count": len(serials),
    }
    yield data
    try:
        _cleanup(db_conn, serials)
    except Exception:
        db_conn.rollback()


def _summary_admin(ref_date, partner=None):
    return build_auto_close_summary(
        period="month", partner=partner, reference_date=ref_date,
        is_admin=True, worker_company=None)


# ---------------------------------------------------------------------------
# FM-02 / FM-03 / FM-06 / FM-07 — 메인 데이터 기반
# ---------------------------------------------------------------------------

class TestForceMatrixMain:

    def test_fm02_grand_total_equals_force_count(self, seed_s81_main):
        resp = _summary_admin(seed_s81_main["ref_date"])
        fc = resp["force_closed"]
        n = fc["count"]
        assert n >= seed_s81_main["force_count"]  # 다른 테스트 데이터 가능
        assert fc["partner_task_matrix"]["grand_total"] == n
        assert fc["partner_elapsed_matrix"]["grand_total"] == n
        # by_reason 합도 동일
        assert sum(r["count"] for r in fc["by_reason"]) == n

    def test_fm03_unstarted_force_in_unknown_bucket(self, seed_s81_main):
        resp = _summary_admin(seed_s81_main["ref_date"])
        em = resp["force_closed"]["partner_elapsed_matrix"]
        fni = _row_for(em, "FNI")
        assert fni is not None
        ui = _bucket_idx(em, "elapsed_unknown")
        d1 = _bucket_idx(em, "elapsed_1d")
        assert fni["counts"][ui] == 1   # 미시작 버킷
        assert fni["counts"][d1] == 0   # 1일내 미오염

    def test_fm06_company_classification(self, seed_s81_main):
        resp = _summary_admin(seed_s81_main["ref_date"])
        tm = resp["force_closed"]["partner_task_matrix"]
        companies = {r["company"] for r in tm["rows"]}
        assert "BAT" in companies
        assert "TMS(M)" in companies   # mech_partner='TMS' → TMS(M)
        assert "C&A" in companies

    def test_fm07_gst_inspection_unassigned(self, seed_s81_main):
        resp = _summary_admin(seed_s81_main["ref_date"])
        tm = resp["force_closed"]["partner_task_matrix"]
        unassigned = _row_for(tm, "(미지정)")
        assert unassigned is not None      # QI force → (미지정)
        assert unassigned["total"] >= 1

    def test_fm_elapsed_bucket_columns_fixed_5(self, seed_s81_main):
        resp = _summary_admin(seed_s81_main["ref_date"])
        em = resp["force_closed"]["partner_elapsed_matrix"]
        keys = [c["task_id"] for c in em["task_columns"]]
        assert keys == [
            "elapsed_unknown", "elapsed_1d", "elapsed_1_3d",
            "elapsed_3_7d", "elapsed_7d",
        ]


# ---------------------------------------------------------------------------
# FM-04 — 미시작 + elapsed=0 (핵심 TC, 원안 버그 재현 차단)
# ---------------------------------------------------------------------------

class TestForceMatrixUnstartedZero:

    def test_fm04_unstarted_with_zero_elapsed_goes_to_unknown(
        self, db_conn, create_test_worker
    ):
        if db_conn is None:
            pytest.skip("DB not available")
        admin = create_test_worker(
            email="s81-fm04-admin@test.axisos.com", password="Test1234!",
            name="FM04 Admin", role="QI", is_admin=True)
        w = create_test_worker(
            email="s81-fm04-w@test.axisos.com", password="Test1234!",
            name="FM04 W", role="MECH", company="BAT")
        today = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
        sn = "S81-FM04-001"
        serials = [sn]
        try:
            _seed_product(db_conn, sn, mech_partner="BAT")
            # 미시작(started_at NULL) 인데 elapsed_minutes=0 — 원안 'elapsed IS NULL'
            # 기준이면 '1일내' 오분류 / 본 설계 'started_at IS NULL' 우선이면 '미시작'
            _seed_force_task(db_conn, w, sn, "PANEL_WORK", "판넬 작업", "MECH",
                             today, started_at=None, elapsed_minutes=0,
                             closed_by=admin)
            resp = _summary_admin(today.date())
            em = resp["force_closed"]["partner_elapsed_matrix"]
            bat = _row_for(em, "BAT")
            assert bat is not None
            ui = _bucket_idx(em, "elapsed_unknown")
            d1 = _bucket_idx(em, "elapsed_1d")
            assert bat["counts"][ui] >= 1   # 미시작 버킷 귀속 (핵심)
            # 이 task 가 1일내로 새지 않았는지 — BAT 1일내엔 이 SN 기여 0
            # (다른 BAT 1일내 데이터 있을 수 있어 절대값 대신 grand_total invariant 로 보강)
            assert em["grand_total"] == resp["force_closed"]["count"]
        finally:
            _cleanup(db_conn, serials)


# ---------------------------------------------------------------------------
# FM-05 — elapsed 경계값
# ---------------------------------------------------------------------------

class TestForceMatrixElapsedBoundary:

    @pytest.mark.parametrize("elapsed,expected", [
        (1439, "elapsed_1d"),
        (1440, "elapsed_1_3d"),
        (4319, "elapsed_1_3d"),
        (4320, "elapsed_3_7d"),
        (10079, "elapsed_3_7d"),
        (10080, "elapsed_7d"),
    ])
    def test_fm05_elapsed_boundary_bucket(
        self, db_conn, create_test_worker, elapsed, expected
    ):
        if db_conn is None:
            pytest.skip("DB not available")
        admin = create_test_worker(
            email="s81-fm05-admin@test.axisos.com", password="Test1234!",
            name="FM05 Admin", role="QI", is_admin=True)
        # company 격리 위해 partner 지정 조회로 1건만 모집단화
        w = create_test_worker(
            email=f"s81-fm05-w{elapsed}@test.axisos.com", password="Test1234!",
            name="FM05 W", role="MECH", company="P&S")
        today = datetime.now().replace(hour=13, minute=0, second=0, microsecond=0)
        started = today - timedelta(days=20)
        sn = f"S81-FM05-{elapsed}"
        serials = [sn]
        try:
            # P&S 는 ELEC partner — elec_partner='P&S' 로 격리
            _seed_product(db_conn, sn, elec_partner="P&S")
            _seed_force_task(db_conn, w, sn, "WIRING", "배선 포설", "ELEC",
                             today, started_at=started, elapsed_minutes=elapsed,
                             closed_by=admin, workers_started=[w])
            resp = build_auto_close_summary(
                period="month", partner="P&S", reference_date=today.date(),
                is_admin=True, worker_company=None)
            em = resp["force_closed"]["partner_elapsed_matrix"]
            row = _row_for(em, "P&S")
            assert row is not None, f"P&S row missing for elapsed={elapsed}"
            idx = _bucket_idx(em, expected)
            assert row["counts"][idx] >= 1, (
                f"elapsed={elapsed} expected bucket {expected}, got {row['counts']}"
            )
            assert em["grand_total"] == resp["force_closed"]["count"]
        finally:
            _cleanup(db_conn, serials)


# ---------------------------------------------------------------------------
# FM-01 — force 0건
# ---------------------------------------------------------------------------

class TestForceMatrixEmpty:

    def test_fm01_no_force_empty_matrices(self, db_conn, create_test_worker):
        if db_conn is None:
            pytest.skip("DB not available")
        create_test_worker(
            email="s81-fm01-admin@test.axisos.com", password="Test1234!",
            name="FM01 Admin", role="QI", is_admin=True)
        # 과거(데이터 없는 기간) 조회 → force 0건
        old = datetime(2020, 1, 15).date()
        resp = build_auto_close_summary(
            period="month", reference_date=old, is_admin=True, worker_company=None)
        fc = resp["force_closed"]
        assert fc["count"] == 0
        assert fc["partner_task_matrix"]["rows"] == []
        assert fc["partner_task_matrix"]["grand_total"] == 0
        assert fc["partner_elapsed_matrix"]["rows"] == []
        assert fc["partner_elapsed_matrix"]["grand_total"] == 0
        # 빈 데이터라도 elapsed 컬럼 5칸 고정
        assert len(fc["partner_elapsed_matrix"]["task_columns"]) == 5


# ---------------------------------------------------------------------------
# FM-08 — invariant 위반 시 500
# ---------------------------------------------------------------------------

class TestForceMatrixInvariant:

    def _base_response(self):
        """invariant 통과하는 최소 정상 응답."""
        empty_matrix = {
            "task_columns": [], "rows": [], "column_totals": [], "grand_total": 0,
        }
        return {
            "period": "테스트",
            "auto_closed": {
                "count": 0, "started_task_count": 0, "missed_worker_count": 0,
                "unstarted_task_count": 0, "prev_period_count": 0,
                "delta": "0", "trend": "unchanged",
            },
            "manual_closed": {
                "count": 0, "prev_period_count": 0, "delta": "0",
                "improvement_pct": None,
            },
            "force_closed": {
                "count": 1, "prev_period_count": 0, "delta": "+1",
                "trend": "increased", "improvement_pct": None, "by_reason": [],
                "partner_task_matrix": {**empty_matrix, "grand_total": 1},
                "partner_elapsed_matrix": {**empty_matrix, "grand_total": 1},
            },
            "total_missed_close": {
                "count": 1, "prev_period_count": 0, "delta": "+1",
                "trend": "increased", "improvement_pct": None,
            },
            "trigger_distribution": [],
            "task_distribution": [],
            "partner_distribution": [],
            "hourly_distribution": [{"hour": h, "count": 0} for h in range(24)],
            "unstarted_task_distribution": [],
            "partner_task_matrix": {**empty_matrix},
        }

    def test_fm08_force_task_matrix_mismatch_raises(self):
        resp = self._base_response()
        resp["force_closed"]["partner_task_matrix"]["grand_total"] = 99  # 불일치
        with pytest.raises(InvariantViolationError):
            _assert_invariants(resp)

    def test_fm08_force_elapsed_matrix_mismatch_raises(self):
        resp = self._base_response()
        resp["force_closed"]["partner_elapsed_matrix"]["grand_total"] = 0  # != count 1
        with pytest.raises(InvariantViolationError):
            _assert_invariants(resp)

    def test_fm08_consistent_passes(self):
        resp = self._base_response()
        _assert_invariants(resp)  # 정합 → 예외 없음


# ---------------------------------------------------------------------------
# FM-09 — manager partner 격리
# ---------------------------------------------------------------------------

class TestForceMatrixManagerIsolation:

    def test_fm09_manager_sees_only_own_company(self, seed_s81_main):
        # BAT 매니저 → 자기 회사 force 만 (work_start_log + company=BAT EXISTS)
        resp = build_auto_close_summary(
            period="month", partner=None, reference_date=seed_s81_main["ref_date"],
            is_admin=False, worker_company="BAT")
        fc = resp["force_closed"]
        tm = fc["partner_task_matrix"]
        companies = {r["company"] for r in tm["rows"]}
        # BAT 만 (FNI/TMS(M)/C&A/(미지정) 제외)
        assert companies <= {"BAT"}
        # invariant — manager 격리 모집단에서도 grand_total == force_count
        assert tm["grand_total"] == fc["count"]
        assert fc["partner_elapsed_matrix"]["grand_total"] == fc["count"]


# ---------------------------------------------------------------------------
# FM-10 — 회귀 (auto 매트릭스 / KPI 3분류 불변)
# ---------------------------------------------------------------------------

class TestForceMatrixRegression:

    def test_fm10_auto_matrix_and_kpi_intact(self, seed_s81_main):
        resp = _summary_admin(seed_s81_main["ref_date"])
        # auto 매트릭스 여전히 존재 + grand_total == started_task_count
        assert "partner_task_matrix" in resp
        assert (resp["partner_task_matrix"]["grand_total"]
                == resp["auto_closed"]["started_task_count"])
        # KPI 3분류 키 존재
        for k in ("auto_closed", "manual_closed", "force_closed", "total_missed_close"):
            assert k in resp
        # total = auto + manual + force
        assert (resp["total_missed_close"]["count"]
                == resp["auto_closed"]["count"]
                + resp["manual_closed"]["count"]
                + resp["force_closed"]["count"])


# ---------------------------------------------------------------------------
# Codex 라운드 2 A-1 — 3자 동시 정합 + 헬퍼 방어 단위 TC
# ---------------------------------------------------------------------------

class TestForceMatrixCodexR2:

    def test_three_way_consistency_admin(self, seed_s81_main):
        """force_count == task_matrix.grand_total == elapsed_matrix.grand_total (admin)."""
        resp = _summary_admin(seed_s81_main["ref_date"])
        fc = resp["force_closed"]
        assert (fc["count"]
                == fc["partner_task_matrix"]["grand_total"]
                == fc["partner_elapsed_matrix"]["grand_total"])

    def test_three_way_consistency_gst_full_access(self, seed_s81_main):
        """GST 매니저(full-access) 도 3자 동시 정합."""
        resp = build_auto_close_summary(
            period="month", partner=None, reference_date=seed_s81_main["ref_date"],
            is_admin=False, worker_company="GST")
        fc = resp["force_closed"]
        assert (fc["count"]
                == fc["partner_task_matrix"]["grand_total"]
                == fc["partner_elapsed_matrix"]["grand_total"])

    def test_three_way_consistency_partner_manager(self, seed_s81_main):
        """협력사 매니저(격리) 도 3자 동시 정합."""
        resp = build_auto_close_summary(
            period="month", partner=None, reference_date=seed_s81_main["ref_date"],
            is_admin=False, worker_company="BAT")
        fc = resp["force_closed"]
        assert (fc["count"]
                == fc["partner_task_matrix"]["grand_total"]
                == fc["partner_elapsed_matrix"]["grand_total"])

    def test_assemble_matrix_out_of_bound_key_dropped(self):
        """fixed_columns 밖 키는 방어적으로 무시 (현 스키마 발생 불가, 방어 코드 검증)."""
        raw = [
            {"company": "BAT", "col_key": "elapsed_1d", "cnt": 3},
            {"company": "BAT", "col_key": "GHOST_BUCKET", "cnt": 99},  # 밖 키
        ]
        m = ds._assemble_company_matrix(raw, fixed_columns=ds._ELAPSED_BUCKETS)
        bat = next(r for r in m["rows"] if r["company"] == "BAT")
        d1 = _bucket_idx(m, "elapsed_1d")
        assert bat["counts"][d1] == 3
        assert bat["total"] == 3           # GHOST 99 누락 (방어)
        assert m["grand_total"] == 3
        assert len(m["task_columns"]) == 5  # 5칸 고정 유지

    def test_assemble_matrix_dynamic_columns_sorted(self):
        """동적 컬럼 — col_name, col_key 정렬."""
        raw = [
            {"company": "BAT", "col_key": "B", "col_name": "Beta", "cnt": 1},
            {"company": "BAT", "col_key": "A", "col_name": "Alpha", "cnt": 2},
        ]
        m = ds._assemble_company_matrix(raw)
        keys = [c["task_id"] for c in m["task_columns"]]
        assert keys == ["A", "B"]          # Alpha < Beta
        assert m["grand_total"] == 3
