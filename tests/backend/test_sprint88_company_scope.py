"""
Sprint 88-BE (#86) — 협력사 데이터 접근 RBAC resolver 검증.

대상:
  - app.middleware.jwt_auth.resolve_company_scope() (공통 RBAC SSoT)
  - 근태 라우트 (admin.py): /api/admin/hr/attendance*
  - 자동마감 라우트 (admin_dashboard.py): /api/admin/dashboard/auto-close-*

핵심 보안 불변식:
  - admin / GST 소속      → 전체 (is_global=True)
  - 협력사 매니저(company) → 자기 회사 한정 (is_global=False, company exact)
  - company 없는 매니저     → 403 (전체 누수 차단)  ← 본 sprint 의 fix

운영 데이터 보존: 신규 워커만 생성/정리 (conftest create_test_worker fixture).
"""
from types import SimpleNamespace

import pytest

from app.middleware.jwt_auth import (
    CompanyScope,
    CompanyScopeError,
    resolve_company_scope,
)


def _worker(**kw):
    """경량 worker stub — DB 불요. 기본값은 협력사 일반 작업자."""
    base = dict(id=1, is_admin=False, is_manager=False, company=None, role="MECH")
    base.update(kw)
    return SimpleNamespace(**base)


# ============================================================
# 1) resolver 단위 (DB-free) — 보안 로직 핵심
# ============================================================

class TestResolveCompanyScope:
    def test_admin_is_global(self):
        scope = resolve_company_scope(_worker(is_admin=True, company=None))
        assert scope == CompanyScope(is_global=True, company=None)

    def test_admin_with_company_still_global(self):
        # admin 이면 company 값과 무관하게 전체
        scope = resolve_company_scope(_worker(is_admin=True, company="BAT"))
        assert scope.is_global is True
        assert scope.company is None

    def test_gst_manager_is_global(self):
        scope = resolve_company_scope(_worker(is_manager=True, company="GST"))
        assert scope == CompanyScope(is_global=True, company=None)

    def test_gst_non_manager_is_global(self):
        # GST 소속이면 매니저 아니어도 전체 (decorator 가 막지만 defense-in-depth)
        scope = resolve_company_scope(_worker(is_manager=False, company="GST"))
        assert scope.is_global is True

    def test_partner_manager_scoped(self):
        scope = resolve_company_scope(_worker(is_manager=True, company="C&A"))
        assert scope == CompanyScope(is_global=False, company="C&A")

    def test_partner_manager_tms_m_exact(self):
        # TMS(M)/TMS(E) 분리 저장 — exact 보존 (migration 불요 검증)
        scope = resolve_company_scope(_worker(is_manager=True, company="TMS(M)"))
        assert scope.company == "TMS(M)"
        scope2 = resolve_company_scope(_worker(is_manager=True, company="TMS(E)"))
        assert scope2.company == "TMS(E)"

    # ---- 누수 차단 (본 sprint fix) ----

    def test_null_company_manager_raises(self):
        with pytest.raises(CompanyScopeError):
            resolve_company_scope(_worker(is_manager=True, company=None))

    def test_empty_company_manager_raises(self):
        with pytest.raises(CompanyScopeError):
            resolve_company_scope(_worker(is_manager=True, company=""))

    def test_whitespace_company_manager_raises(self):
        with pytest.raises(CompanyScopeError):
            resolve_company_scope(_worker(is_manager=True, company="   "))

    def test_none_worker_raises(self):
        with pytest.raises(CompanyScopeError):
            resolve_company_scope(None)

    def test_partner_non_manager_raises(self):
        # 협력사 일반 작업자 (decorator 가 막지만 resolver 도 차단)
        with pytest.raises(CompanyScopeError):
            resolve_company_scope(_worker(is_manager=False, company="C&A"))


# ============================================================
# 2) 라우트 RBAC 통합 — errorhandler 403 매핑 + 스코핑 동작
# ============================================================

_PW = "Test1234!"
_ATT_TODAY = "/api/admin/hr/attendance/today"
_AUTO_SUMMARY = "/api/admin/dashboard/auto-close-summary"


@pytest.mark.skipif(
    "config.getoption('--no-db', default=False)", reason="DB 필요"
)
class TestAttendanceRbacRoutes:
    def test_null_company_manager_403(
        self, client, create_test_worker, get_auth_token
    ):
        """company 없는 매니저 → 403 (전체 누수 차단)."""
        wid = create_test_worker(
            email="scope_nullmgr@test.com", password=_PW,
            name="Null Mgr", role="MECH", is_manager=True, company=None,
        )
        token = get_auth_token(wid)
        resp = client.get(_ATT_TODAY, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
        assert resp.get_json()["error"] == "FORBIDDEN"

    def test_partner_manager_scoped_to_own_company(
        self, client, create_test_worker, get_auth_token
    ):
        """협력사 매니저 → 자기 회사 레코드만 (다른 회사 누수 없음)."""
        mgr = create_test_worker(
            email="scope_camgr@test.com", password=_PW,
            name="CA Mgr", role="ELEC", is_manager=True, company="C&A",
        )
        fni = create_test_worker(
            email="scope_fni@test.com", password=_PW,
            name="FNI W", role="MECH", is_manager=False, company="FNI",
        )
        token = get_auth_token(mgr)
        resp = client.get(_ATT_TODAY, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        records = resp.get_json()["records"]
        # 스코프 불변식: 모든 레코드가 C&A
        assert all(r["company"] == "C&A" for r in records)
        # 다른 회사(FNI) 워커는 노출 안 됨
        assert all(r["worker_id"] != fni for r in records)

    def test_admin_sees_all_companies(
        self, client, create_test_worker, create_test_admin, get_admin_auth_token
    ):
        """admin → 전체 협력사 (FNI 워커 노출)."""
        fni = create_test_worker(
            email="scope_fni_admin@test.com", password=_PW,
            name="FNI W2", role="MECH", is_manager=False, company="FNI",
        )
        token = get_admin_auth_token(create_test_admin["id"])
        resp = client.get(_ATT_TODAY, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        records = resp.get_json()["records"]
        companies = {r["company"] for r in records}
        # admin 은 자기 회사 격리 없음 — 최소 FNI 포함 (전체 조회)
        assert fni in {r["worker_id"] for r in records}
        assert "C&A" not in companies or "FNI" in companies or len(companies) >= 1


@pytest.mark.skipif(
    "config.getoption('--no-db', default=False)", reason="DB 필요"
)
class TestAutoCloseRbacRoutes:
    def test_null_company_manager_403(
        self, client, create_test_worker, get_auth_token
    ):
        """자동마감 — company 없는 매니저 → 403 (DB 쿼리 전 차단)."""
        wid = create_test_worker(
            email="scope_nullmgr_ac@test.com", password=_PW,
            name="Null Mgr AC", role="MECH", is_manager=True, company=None,
        )
        token = get_auth_token(wid)
        resp = client.get(
            _AUTO_SUMMARY + "?period=today",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.get_json()["error"] == "FORBIDDEN"

    def test_partner_manager_200(
        self, client, create_test_worker, get_auth_token
    ):
        """자동마감 — 협력사 매니저 → 200 (스코프 정상)."""
        mgr = create_test_worker(
            email="scope_camgr_ac@test.com", password=_PW,
            name="CA Mgr AC", role="ELEC", is_manager=True, company="C&A",
        )
        token = get_auth_token(mgr)
        resp = client.get(
            _AUTO_SUMMARY + "?period=today",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
