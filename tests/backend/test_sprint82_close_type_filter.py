"""
Sprint 82 (FEAT-AUTOCLOSE-DETAILS-CLOSE-TYPE-FILTER-20260604, VIEW #80)

`/auto-close-details` 에 close_type(auto|manual|force) + task_id(마감 공정) 필터 추가.
응답 스키마 0 변경 (요청 파라미터 additive). per_page cap 100→500.

pytest TC catalog (CT-01 ~ CT-10):
  CT-01 close_type=force            → force_closed=TRUE 만
  CT-02 close_type=auto             → AUTO_CLOSED_BY_% AND force=FALSE 만
  CT-03 close_type=manual           → MANUAL_FORCE_CLOSE AND force=FALSE 만
  CT-04 close_type 미지정           → 현행 union 하위호환
  CT-05 close_type=force + partner  → AND 결합 (특정 협력사 force 전수)
  CT-06 close_type=force + task_id  → 협력사+공정 정밀 (t.task_id)
  CT-07 per_page=200                → 100 clamp 안 됨 (cap 500) + total/total_pages 정합
  CT-08 task_id 단독                → union 중 t.task_id 매칭만
  CT-09 route close_type 검증       → 잘못된 값 400 / 빈 문자열 = None(union)
  CT-10 manager 격리 + force        → 자기 회사 force 만 (미시작 force 제외 정책)

설계서: AGENT_TEAM_LAUNCH.md § Sprint 82 (#80)
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

import pytest

from app.services.dashboard_service import build_auto_close_details


# ---------------------------------------------------------------------------
# Helper — DB seed
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
        VALUES (%s, %s, 'active') ON CONFLICT (qr_doc_id) DO NOTHING
    """, (f"DOC_{sn}", sn))
    db_conn.commit()


def _seed_task(db_conn, worker_id, sn, task_id, task_name, task_category,
               completed_at, close_reason, force_closed, started_at=None,
               closed_by=None, workers_started: Optional[List[int]] = None):
    cur = db_conn.cursor()
    cur.execute("""
        INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
             started_at, completed_at, close_reason, closed_by, force_closed, is_applicable)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE)
        RETURNING id
    """, (worker_id, sn, f"DOC_{sn}", task_category, task_id, task_name,
          started_at, completed_at, close_reason, closed_by, force_closed))
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
    for tbl in ("work_completion_log", "work_start_log", "app_task_details", "qr_registry"):
        cur.execute(f"DELETE FROM {tbl} WHERE serial_number = ANY(%s)", (serials,))
    cur.execute("DELETE FROM plan.product_info WHERE serial_number = ANY(%s)", (serials,))
    db_conn.commit()


_AUTO = "AUTO_CLOSED_BY_FIRST_FINAL_TRIGGER:IF_2"


@pytest.fixture
def seed_s82(db_conn, create_test_worker):
    if db_conn is None:
        pytest.skip("DB not available")
    w_bat = create_test_worker(email="s82-bat@test.axisos.com", password="Test1234!",
                               name="S82 BAT", role="MECH", company="BAT")
    w_fni = create_test_worker(email="s82-fni@test.axisos.com", password="Test1234!",
                               name="S82 FNI", role="MECH", company="FNI")
    admin = create_test_worker(email="s82-admin@test.axisos.com", password="Test1234!",
                               name="S82 Admin", role="QI", is_admin=True)
    today = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
    started = today - timedelta(hours=4)
    serials: List[str] = []

    def P(sn, **kw):
        serials.append(sn); _seed_product(db_conn, sn, **kw); return sn

    # BAT MECH — force (PANEL_WORK), started
    sn1 = P("S82-SN-001", mech_partner="BAT")
    _seed_task(db_conn, w_bat, sn1, "PANEL_WORK", "판넬 작업", "MECH", today,
               "MANUAL_FORCE_CLOSE", True, started, closed_by=admin, workers_started=[w_bat])
    # BAT MECH — auto (gas1)
    sn2 = P("S82-SN-002", mech_partner="BAT")
    _seed_task(db_conn, w_bat, sn2, "gas1", "Gas 1", "MECH", today, _AUTO, False,
               started, workers_started=[w_bat])
    # BAT MECH — manual (UTIL_LINE_1), force_closed=FALSE
    sn3 = P("S82-SN-003", mech_partner="BAT")
    _seed_task(db_conn, w_bat, sn3, "UTIL_LINE_1", "Util 1", "MECH", today,
               "MANUAL_FORCE_CLOSE", False, started, workers_started=[w_bat])
    # FNI MECH — force (PANEL_WORK), started
    sn4 = P("S82-SN-004", mech_partner="FNI")
    _seed_task(db_conn, w_fni, sn4, "PANEL_WORK", "판넬 작업", "MECH", today,
               "MANUAL_FORCE_CLOSE", True, started, closed_by=admin, workers_started=[w_fni])
    # BAT MECH — force 미시작 (started_at NULL, work_start_log 없음)
    sn5 = P("S82-SN-005", mech_partner="BAT")
    _seed_task(db_conn, w_bat, sn5, "gas2", "Gas 2", "MECH", today,
               "MANUAL_FORCE_CLOSE", True, None, closed_by=admin)

    data = {"admin": admin, "w_bat": w_bat, "w_fni": w_fni,
            "serials": serials, "ref": today.date()}
    yield data
    try:
        _cleanup(db_conn, serials)
    except Exception:
        db_conn.rollback()


def _details(ref, **kw):
    kw.setdefault("per_page", 500)
    return build_auto_close_details(period="month", reference_date=ref,
                                    is_admin=True, worker_company=None, **kw)


def _types(resp):
    return [it["close_type"] for it in resp["items"]]


def _sns(resp):
    return {it["serial_number"] for it in resp["items"]}


# ---------------------------------------------------------------------------
# CT-01 ~ CT-08 (service level)
# ---------------------------------------------------------------------------

class TestCloseTypeFilter:

    def test_ct01_force_only(self, seed_s82):
        r = _details(seed_s82["ref"], close_type="force")
        assert _types(r), "force 결과 존재"
        assert all(t == "force" for t in _types(r))
        # seed force 3건(BAT 2 + FNI 1) 포함
        assert {"S82-SN-001", "S82-SN-004", "S82-SN-005"} <= _sns(r)
        assert "S82-SN-002" not in _sns(r)  # auto 제외
        assert "S82-SN-003" not in _sns(r)  # manual 제외

    def test_ct02_auto_only(self, seed_s82):
        r = _details(seed_s82["ref"], close_type="auto")
        assert all(t == "auto" for t in _types(r))
        assert "S82-SN-002" in _sns(r)
        assert "S82-SN-001" not in _sns(r)  # force 제외

    def test_ct03_manual_only(self, seed_s82):
        r = _details(seed_s82["ref"], close_type="manual")
        assert all(t == "manual" for t in _types(r))
        assert "S82-SN-003" in _sns(r)
        assert "S82-SN-001" not in _sns(r)  # force(MANUAL_FORCE_CLOSE+force=TRUE) 제외

    def test_ct04_union_default(self, seed_s82):
        r = _details(seed_s82["ref"])  # close_type 미지정
        sns = _sns(r)
        # auto + manual + force 모두 포함
        assert {"S82-SN-001", "S82-SN-002", "S82-SN-003", "S82-SN-004", "S82-SN-005"} <= sns
        assert set(_types(r)) <= {"auto", "manual", "force"}

    def test_ct05_force_and_partner(self, seed_s82):
        r = _details(seed_s82["ref"], close_type="force", partner="BAT")
        sns = _sns(r)
        assert "S82-SN-001" in sns and "S82-SN-005" in sns  # BAT force
        assert "S82-SN-004" not in sns                       # FNI 제외
        assert all(it["company"] == "BAT" for it in r["items"])

    def test_ct06_force_and_task_id(self, seed_s82):
        r = _details(seed_s82["ref"], close_type="force", task_id="PANEL_WORK")
        sns = _sns(r)
        # PANEL_WORK force = BAT(sn1) + FNI(sn4), gas2(sn5)는 task_id 다름 → 제외
        assert "S82-SN-001" in sns and "S82-SN-004" in sns
        assert "S82-SN-005" not in sns
        assert all(it["closed_tasks"][0]["task_id"] == "PANEL_WORK" for it in r["items"])

    def test_ct07_per_page_not_clamped_and_pagination(self, seed_s82):
        r = _details(seed_s82["ref"], per_page=200)
        assert r["per_page"] == 200          # 100 clamp 안 됨 (cap 500)
        # total / total_pages / len(items) 정합
        assert r["total"] == len(r["items"]) if r["total"] <= 200 else len(r["items"]) == 200
        expected_pages = (r["total"] + 200 - 1) // 200
        assert r["total_pages"] == expected_pages

    def test_ct08_task_id_only_union(self, seed_s82):
        r = build_auto_close_details(period="month", reference_date=seed_s82["ref"],
                                     is_admin=True, per_page=500, task_id="PANEL_WORK")
        # close_type 미지정 + task_id → union 중 PANEL_WORK 만
        assert all(it["closed_tasks"][0]["task_id"] == "PANEL_WORK" for it in r["items"])
        assert {"S82-SN-001", "S82-SN-004"} <= _sns(r)


# ---------------------------------------------------------------------------
# CT-10 — manager 격리 + force (서비스 레벨)
# ---------------------------------------------------------------------------

class TestManagerIsolationForce:

    def test_ct10_manager_force_own_company_only(self, seed_s82):
        # BAT 매니저 → 자기 회사 worker 가 시작한 force 만 (미시작 force sn5 제외)
        r = build_auto_close_details(
            period="month", reference_date=seed_s82["ref"],
            is_admin=False, worker_company="BAT", close_type="force", per_page=500)
        sns = _sns(r)
        assert "S82-SN-001" in sns          # BAT force (started by BAT)
        assert "S82-SN-004" not in sns      # FNI force 제외
        # 미시작 force(sn5, work_start_log 없음) → 협력사 매니저 격리 정책상 제외
        assert "S82-SN-005" not in sns
        assert all(it["close_type"] == "force" for it in r["items"])


# ---------------------------------------------------------------------------
# CT-09 — route close_type 검증 (HTTP)
# ---------------------------------------------------------------------------

class TestRouteCloseTypeValidation:

    def _admin_token(self, client, get_auth_token, db_conn, create_test_worker):
        wid = create_test_worker(email="s82-rt-admin@test.axisos.com", password="Test1234!",
                                 name="S82 RT Admin", role="QI", is_admin=True)
        return get_auth_token(wid, email="s82-rt-admin@test.axisos.com",
                              role="QI", is_admin=True)

    def test_ct09_invalid_close_type_400(self, client, db_conn, create_test_worker, get_auth_token):
        if db_conn is None:
            pytest.skip("DB not available")
        token = self._admin_token(client, get_auth_token, db_conn, create_test_worker)
        resp = client.get(
            "/api/admin/dashboard/auto-close-details?period=month&close_type=bogus",
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "INVALID_CLOSE_TYPE"

    def test_ct09_empty_close_type_is_union(self, client, db_conn, create_test_worker, get_auth_token):
        if db_conn is None:
            pytest.skip("DB not available")
        token = self._admin_token(client, get_auth_token, db_conn, create_test_worker)
        # 빈 문자열 → None(union) → 200
        resp = client.get(
            "/api/admin/dashboard/auto-close-details?period=month&close_type=",
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_ct09_valid_force_200(self, client, db_conn, create_test_worker, get_auth_token):
        if db_conn is None:
            pytest.skip("DB not available")
        token = self._admin_token(client, get_auth_token, db_conn, create_test_worker)
        resp = client.get(
            "/api/admin/dashboard/auto-close-details?period=month&close_type=FORCE",
            headers={"Authorization": f"Bearer {token}"})
        # 대문자 → lower 정규화 → 200
        assert resp.status_code == 200

    def test_ct11_quarter_period_supported(self, client, db_conn, create_test_worker, get_auth_token):
        """v2.24.1 (#80 후속) — details 가 quarter 지원 (summary 매트릭스 기간 정합)."""
        if db_conn is None:
            pytest.skip("DB not available")
        token = self._admin_token(client, get_auth_token, db_conn, create_test_worker)
        resp = client.get(
            "/api/admin/dashboard/auto-close-details?period=quarter&close_type=force&per_page=500",
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200   # 이전엔 400 INVALID_PERIOD
        body = resp.get_json()
        assert "items" in body and "total" in body
