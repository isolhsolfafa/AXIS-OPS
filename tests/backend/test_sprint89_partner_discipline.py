"""
Sprint 89-BE (#87) — 협력사 규율 종합 대시보드 Phase 1 검증.

대상:
  - services/partner_discipline_service.py
      _month_range_kst / _envelope / _group_avg (순수 — DB-free)
      build_discipline_summary / build_open_tasks (monkeypatch — DB-free 결정론)
  - routes/admin_discipline.py (HTTP wiring — 인증 게이트)

공정성(게이밍 방지) 핵심 불변식:
  - group_avg = peer-only(자사 제외) + peer_n>=3 충족 시만 (소표본 역추론 차단).
    현 협력사 수(MECH 3 / ELEC 3) → 협력사 매니저 peer=2<3 → 항상 suppress (정상·의도).
    admin/GST(global) → peer_n=3 → group_avg 노출.
  - 협력사 매니저 응답 = 자사 row만 (타사 raw 미노출).
  - Phase 2 지표(taggingRate/checkinNoTag/zeroTap/checklist) = placeholder(available=false, raw=null).
  - 모집단 = MECH/ELEC only.

운영 데이터 보존: 본 파일은 DB 미접근 (monkeypatch + 순수 함수). read-only.
"""
from datetime import datetime, timedelta

import pytest

from app.middleware.jwt_auth import CompanyScope
import app.services.partner_discipline_service as svc
from app.services.partner_discipline_service import (
    KST,
    _envelope,
    _group_avg,
    _month_range_kst,
    build_discipline_summary,
    build_open_tasks,
)

ADMIN_SCOPE = CompanyScope(is_global=True, company=None)
BAT_SCOPE = CompanyScope(is_global=False, company="BAT")

# 현 운영 협력사 구성 (MECH 3 / ELEC 3) — TMS(M)/(E) 분리.
_GROUPS = [
    ("BAT", "MECH"), ("FNI", "MECH"), ("TMS(M)", "MECH"),
    ("C&A", "ELEC"), ("P&S", "ELEC"), ("TMS(E)", "ELEC"),
]
_OPEN = {("BAT", "MECH"): 5, ("FNI", "MECH"): 1, ("TMS(M)", "MECH"): 0,
         ("C&A", "ELEC"): 2, ("P&S", "ELEC"): 3, ("TMS(E)", "ELEC"): 4}
_AUTO = {("BAT", "MECH"): 2, ("FNI", "MECH"): 0, ("TMS(M)", "MECH"): 1,
         ("C&A", "ELEC"): 1, ("P&S", "ELEC"): 1, ("TMS(E)", "ELEC"): 0}


# ============================================================
# 1) _month_range_kst (순수)
# ============================================================
class TestMonthRange:
    def test_basic_month(self):
        start, end, first, last = _month_range_kst("2026-06")
        assert (first.year, first.month, first.day) == (2026, 6, 1)
        assert (last.year, last.month, last.day) == (2026, 7, 1)  # exclusive
        assert start.tzinfo is not None and end.tzinfo is not None

    def test_december_rolls_to_next_year(self):
        _s, _e, first, last = _month_range_kst("2026-12")
        assert (last.year, last.month) == (2027, 1)


# ============================================================
# 2) _envelope (순수) — 공정성 계약
# ============================================================
class TestEnvelope:
    def test_phase2_placeholder(self):
        env = _envelope("zeroTap", None, available=False, phase="phase2")
        assert env["available"] is False
        assert env["raw"] is None
        assert env["phase"] == "phase2"
        assert env["grade_eligible"] is False

    def test_normal_eligible(self):
        env = _envelope("openTasks", 5.0, available=True, phase="phase1")
        assert env["grade_eligible"] is True
        assert env["raw"] == 5.0
        assert env["lower_better"] is True

    def test_tracking_below_70_ineligible(self):
        env = _envelope("taggingRate", 80.0, available=True, phase="phase1",
                        tracking_coverage=0.5)
        assert env["grade_eligible"] is False
        assert env["ineligibility_reason"] == "tracking_below_70"

    def test_tracking_above_70_eligible(self):
        env = _envelope("taggingRate", 80.0, available=True, phase="phase1",
                        tracking_coverage=0.9)
        assert env["grade_eligible"] is True
        assert env["ineligibility_reason"] is None


# ============================================================
# 3) _group_avg (순수) — peer-only + k>=3 핵심
# ============================================================
class TestGroupAvg:
    def test_global_shows_full_group_avg(self):
        # admin: MECH 전체 평균 (5+1+0)/3 = 2.0, peer_n=3
        ga, pn, sr = _group_avg(_OPEN, "MECH", _GROUPS, ADMIN_SCOPE)
        assert ga == 2.0
        assert pn == 3
        assert sr is None

    def test_manager_peer_below_3_suppressed(self):
        # 협력사 매니저 BAT: peer = FNI/TMS(M) = 2 < 3 → suppress
        ga, pn, sr = _group_avg(_OPEN, "MECH", _GROUPS, BAT_SCOPE)
        assert ga is None
        assert pn == 2
        assert sr == "insufficient_peers"

    def test_manager_peer_at_3_boundary_shown(self):
        # 가상: MECH 4사 → BAT peer=3 → 노출 (k>=3 경계)
        groups4 = _GROUPS + [("EXTRA", "MECH")]
        open4 = dict(_OPEN)
        open4[("EXTRA", "MECH")] = 6
        # peer(BAT 제외) = FNI(1)+TMS(M)(0)+EXTRA(6) = 7/3 ≈ 2.33
        ga, pn, sr = _group_avg(open4, "MECH", groups4, BAT_SCOPE)
        assert pn == 3
        assert sr is None
        assert ga == pytest.approx(2.33, abs=0.01)

    def test_global_below_3_suppressed(self):
        groups2 = [("X", "MECH"), ("Y", "MECH")]
        open2 = {("X", "MECH"): 1, ("Y", "MECH"): 3}
        ga, pn, sr = _group_avg(open2, "MECH", groups2, ADMIN_SCOPE)
        assert ga is None and pn == 2 and sr == "insufficient_peers"


# ============================================================
# 3b) _PARTNER_SQL 정규화 (Codex 라운드3 M-6) — '' / 공백 partner 제외 가드
# ============================================================
class TestPartnerSqlNormalization:
    def test_partner_sql_wraps_nullif_trim(self):
        # NULLIF(TRIM(...), '') 래핑 → NULL/빈문자열/공백 단일 IS NOT NULL 제외 보장
        sql = svc._PARTNER_SQL
        assert sql.startswith("NULLIF(TRIM(")
        assert sql.rstrip().endswith(", '')")
        assert "TMS(M)" in sql and "TMS(E)" in sql  # 정규화 보존


# ============================================================
# 4) build_discipline_summary (monkeypatch — DB-free)
# ============================================================
class _FakeCur:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeConn:
    def cursor(self):
        return _FakeCur()


@pytest.fixture
def patch_summary(monkeypatch):
    monkeypatch.setattr(svc, "get_db_connection", lambda: _FakeConn())
    monkeypatch.setattr(svc, "put_conn", lambda c: None)
    monkeypatch.setattr(svc, "_query_partner_groups", lambda cur: list(_GROUPS))
    monkeypatch.setattr(svc, "_query_open_tasks_count", lambda cur, cf: dict(_OPEN))
    monkeypatch.setattr(svc, "_query_auto_close_count", lambda cur, s, e, cf: dict(_AUTO))


class TestDisciplineSummary:
    def test_admin_global_all_rows_with_group_avg(self, patch_summary):
        resp = build_discipline_summary("2026-06", ADMIN_SCOPE)
        assert resp["scope"] == "global"
        assert resp["company"] is None
        assert len(resp["rows"]) == 6  # 전체 partner×group
        # MECH BAT openTasks group_avg = 2.0 (전체 평균)
        bat = next(r for r in resp["rows"] if r["partner"] == "BAT")
        assert bat["metrics"]["openTasks"]["raw"] == 5.0
        assert bat["metrics"]["openTasks"]["group_avg"] == 2.0
        assert bat["metrics"]["openTasks"]["peer_n"] == 3

    def test_manager_self_only_rows(self, patch_summary):
        resp = build_discipline_summary("2026-06", BAT_SCOPE)
        assert resp["scope"] == "self"
        assert resp["company"] == "BAT"
        # 자사 row만 (BAT MECH 1개) — 타사 미노출
        assert len(resp["rows"]) == 1
        assert resp["rows"][0]["partner"] == "BAT"
        assert resp["rows"][0]["group"] == "MECH"

    def test_manager_group_avg_suppressed(self, patch_summary):
        resp = build_discipline_summary("2026-06", BAT_SCOPE)
        ot = resp["rows"][0]["metrics"]["openTasks"]
        assert ot["raw"] == 5.0  # 자사 raw 는 노출
        assert ot["group_avg"] is None  # peer=2<3 → suppress
        assert ot["suppressed_reason"] == "insufficient_peers"
        assert ot["peer_n"] == 2

    def test_phase2_metrics_are_placeholders(self, patch_summary):
        resp = build_discipline_summary("2026-06", ADMIN_SCOPE)
        m = resp["rows"][0]["metrics"]
        for key in ("taggingRate", "checkinNoTag", "zeroTap", "checklist"):
            assert m[key]["available"] is False
            assert m[key]["raw"] is None
            assert m[key]["phase"] == "phase2"
        # Phase 1 실측 지표는 available
        assert m["openTasks"]["available"] is True
        assert m["autoClose"]["available"] is True

    def test_meta_fairness_and_phase(self, patch_summary):
        resp = build_discipline_summary("2026-06", ADMIN_SCOPE)
        meta = resp["meta"]
        assert meta["phase1_metrics"] == ["openTasks", "autoClose"]
        assert set(meta["phase2_pending"]) == {"taggingRate", "checkinNoTag", "zeroTap", "checklist"}
        assert meta["min_peers"] == 3
        assert "근태" in meta["fairness_note"]  # 근태 평가 제외 명시


# ============================================================
# 5) build_open_tasks (monkeypatch — repeat 플래그 + 자사 필터)
# ============================================================
class _SeqCur:
    """execute 호출 기록 + fetchall 순차 반환 (queue → repeat)."""

    def __init__(self, results):
        self._results = list(results)
        self._i = 0
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        self.calls.append((sql, list(params or [])))

    def fetchall(self):
        r = self._results[self._i]
        self._i += 1
        return r


def _started(hours_ago):
    return datetime.now(KST) - timedelta(hours=hours_ago)


@pytest.fixture
def patch_open_tasks(monkeypatch):
    # queue: worker 10 이 2건 (UTIL_LINE_1 SN1 / WASTE SN2) → repeat by worker
    queue_rows = [
        {"id": 1, "serial_number": "SN1", "task_id": "UTIL_LINE_1", "task_name": "Util 1",
         "grp": "MECH", "worker_id": 10, "started_at": _started(5), "partner": "BAT",
         "worker_name": "홍길동"},
        {"id": 2, "serial_number": "SN2", "task_id": "WASTE_GAS_LINE_2", "task_name": "Waste 2",
         "grp": "MECH", "worker_id": 10, "started_at": _started(3), "partner": "BAT",
         "worker_name": "홍길동"},
        {"id": 3, "serial_number": "SN3", "task_id": "PANEL_WORK", "task_name": "Panel",
         "grp": "ELEC", "worker_id": 20, "started_at": _started(1), "partner": "C&A",
         "worker_name": "김철수"},
    ]
    # repeat (30d open): worker 10 이 2건 → by_worker repeat. worker 20 = 1건.
    repeat_rows = [
        {"worker_id": 10, "serial_number": "SN1", "task_id": "UTIL_LINE_1"},
        {"worker_id": 10, "serial_number": "SN2", "task_id": "WASTE_GAS_LINE_2"},
        {"worker_id": 20, "serial_number": "SN3", "task_id": "PANEL_WORK"},
    ]
    cur = _SeqCur([queue_rows, repeat_rows])

    class _Conn:
        def cursor(self):
            return cur

    monkeypatch.setattr(svc, "get_db_connection", lambda: _Conn())
    monkeypatch.setattr(svc, "put_conn", lambda c: None)
    return cur


class TestOpenTasks:
    def test_global_returns_all_with_repeat_flag(self, patch_open_tasks):
        resp = build_open_tasks(ADMIN_SCOPE)
        assert resp["scope"] == "global"
        assert resp["company"] is None
        assert resp["meta"]["count"] == 3
        # worker 10 = 2건 → repeat True (by_worker)
        w10 = [t for t in resp["tasks"] if t["worker_id"] == 10]
        assert all(t["repeat"] is True for t in w10)
        assert all("worker" in (t["repeat_reason"] or []) for t in w10)
        # worker 20 = 1건 → repeat False
        w20 = next(t for t in resp["tasks"] if t["worker_id"] == 20)
        assert w20["repeat"] is False
        assert w20["repeat_reason"] is None
        assert resp["meta"]["repeat_count"] == 2
        assert resp["meta"]["repeat_window_days"] == 30
        assert resp["meta"]["repeat_min_count"] == 2

    def test_hours_open_and_worker_name(self, patch_open_tasks):
        resp = build_open_tasks(ADMIN_SCOPE)
        t1 = next(t for t in resp["tasks"] if t["id"] == 1)
        assert t1["worker_name"] == "홍길동"
        assert t1["hours_open"] >= 4.5  # ~5h
        assert t1["started_at"] is not None

    def test_manager_applies_company_filter_in_sql(self, patch_open_tasks):
        resp = build_open_tasks(BAT_SCOPE)
        assert resp["scope"] == "self"
        assert resp["company"] == "BAT"
        # 자사 필터가 SQL params 로 전달됐는지 (타사 미반환 보장 — 누수 차단)
        queue_call = patch_open_tasks.calls[0]
        repeat_call = patch_open_tasks.calls[1]
        assert "BAT" in queue_call[1]
        assert "BAT" in repeat_call[1]


# ============================================================
# 6) HTTP wiring — 인증 게이트 (blueprint 등록 + jwt_required)
# ============================================================
class TestEndpointWiring:
    def test_summary_requires_auth(self, client):
        res = client.get("/api/admin/discipline/summary?month=2026-06")
        assert res.status_code == 401

    def test_open_tasks_requires_auth(self, client):
        res = client.get("/api/admin/discipline/open-tasks")
        assert res.status_code == 401

    def test_summary_invalid_month_400_with_auth(self, client, create_test_worker, get_auth_token):
        email = "disc_admin@test.axisos.com"
        wid = create_test_worker(
            email=email, password="Test1234!", name="규율admin",
            role="ADMIN", is_admin=True, is_manager=True, company="GST",
        )
        token = get_auth_token(wid, email=email, role="ADMIN", is_admin=True)
        res = client.get("/api/admin/discipline/summary?month=2026-13",
                         headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 400
        assert res.get_json()["error"] == "INVALID_MONTH"
