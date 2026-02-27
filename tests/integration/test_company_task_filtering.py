"""
test_company_task_filtering.py
Sprint 7: Company 기반 Task 필터링 통합 테스트

검증 대상 (task_seed.py get_task_categories_for_worker):
  GAIA 제품 (mech_partner=FNI, elec_partner=TMS, module_outsourcing=TMS):
    FNI 작업자    → ['MECH']
    BAT 작업자    → []  (mech_partner 불일치)
    TMS(M) 작업자 → ['TMS', 'MECH']? or ['TMS'] (module_outsourcing=TMS + mech_partner=FNI ≠ TMS)
    TMS(E) 작업자 → ['ELEC']  (elec_partner=TMS)
    P&S 작업자    → []   (elec_partner 불일치)
    C&A 작업자    → []   (elec_partner 불일치)
    GST ADMIN     → []   (필터 없음 = 전체)

  DRAGON 제품 (mech_partner=TMS, elec_partner=P&S, module_outsourcing=None):
    TMS(M) 작업자 → ['MECH'] (mech_partner=TMS 매칭 → MECH)
    FNI 작업자    → []  (mech_partner 불일치)
    P&S 작업자    → ['ELEC'] (elec_partner=P&S 매칭)
    TMS(E) 작업자 → []  (elec_partner=TMS, 실제 elec_partner=P&S → 불일치)

  GALLANT 제품 (mech_partner=BAT, elec_partner=C&A, module_outsourcing=None):
    BAT 작업자    → ['MECH']
    C&A 작업자    → ['ELEC']
    FNI 작업자    → []

  GST 사내 역할 기반:
    PI 역할       → ['PI']
    QI 역할       → ['QI']
    SI 역할       → ['SI']
    ADMIN 역할    → [] (필터 없음)

테스트 실행 방법:
  pytest tests/integration/test_company_task_filtering.py -v
"""

import sys
import os
import pytest
from typing import List, Optional, Dict, Any

# 프로젝트 경로 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from app.services.task_seed import (
    get_task_categories_for_worker,
    filter_tasks_for_worker,
)


# ──────────────────────────────────────────────
# 헬퍼 — 제품 정보 더미 객체 (ProductInfo 대체)
# ──────────────────────────────────────────────

class _MockProduct:
    """
    filter_tasks_for_worker에 전달할 간이 제품 정보 객체.
    ProductInfo dataclass와 동일한 속성 제공.
    """
    def __init__(
        self,
        mech_partner: Optional[str],
        elec_partner: Optional[str],
        module_outsourcing: Optional[str]
    ):
        self.mech_partner = mech_partner
        self.elec_partner = elec_partner
        self.module_outsourcing = module_outsourcing


class _MockTask:
    """filter_tasks_for_worker에 전달할 간이 Task 객체"""
    def __init__(self, task_category: str, task_id: str):
        self.task_category = task_category
        self.task_id = task_id

    def __repr__(self):
        return f"Task({self.task_category}/{self.task_id})"


# 테스트용 제품 정보
GAIA_PRODUCT    = _MockProduct(mech_partner='FNI', elec_partner='TMS', module_outsourcing='TMS')
DRAGON_PRODUCT  = _MockProduct(mech_partner='TMS', elec_partner='P&S', module_outsourcing=None)
GALLANT_PRODUCT = _MockProduct(mech_partner='BAT', elec_partner='C&A', module_outsourcing=None)
MITHAS_PRODUCT  = _MockProduct(mech_partner='FNI', elec_partner='P&S', module_outsourcing=None)

# 전체 Task 목록 (필터링 테스트용)
ALL_TASKS = [
    _MockTask('MECH', 'WASTE_GAS_LINE_1'),
    _MockTask('MECH', 'UTIL_LINE_1'),
    _MockTask('MECH', 'TANK_DOCKING'),
    _MockTask('MECH', 'WASTE_GAS_LINE_2'),
    _MockTask('MECH', 'UTIL_LINE_2'),
    _MockTask('MECH', 'HEATING_JACKET'),
    _MockTask('MECH', 'SELF_INSPECTION'),
    _MockTask('ELEC', 'PANEL_WORK'),
    _MockTask('ELEC', 'CABINET_PREP'),
    _MockTask('ELEC', 'WIRING'),
    _MockTask('ELEC', 'IF_1'),
    _MockTask('ELEC', 'IF_2'),
    _MockTask('ELEC', 'INSPECTION'),
    _MockTask('TMS',  'TANK_MODULE'),
    _MockTask('TMS',  'PRESSURE_TEST'),
]


# ──────────────────────────────────────────────
# TC-01~TC-07: GAIA 제품 기준 필터링
# ──────────────────────────────────────────────

class TestGAIAProductFiltering:
    """
    TC-01~TC-07: GAIA 제품 (FNI/TMS/TMS) 기준 회사별 Task 카테고리 필터링
    """

    def test_fni_worker_sees_mech_for_gaia(self):
        """TC-01: FNI 작업자 → GAIA mech_partner=FNI 매칭 → MECH만"""
        categories = get_task_categories_for_worker(
            worker_company='FNI',
            worker_role='MECH',
            product_mech_partner=GAIA_PRODUCT.mech_partner,
            product_elec_partner=GAIA_PRODUCT.elec_partner,
            product_module_outsourcing=GAIA_PRODUCT.module_outsourcing,
        )
        assert categories == ['MECH'], f"FNI/GAIA: expected=['MECH'], actual={categories}"

    def test_bat_worker_sees_nothing_for_gaia(self):
        """TC-02: BAT 작업자 → GAIA mech_partner=FNI ≠ BAT → 빈 리스트"""
        categories = get_task_categories_for_worker(
            worker_company='BAT',
            worker_role='MECH',
            product_mech_partner=GAIA_PRODUCT.mech_partner,
            product_elec_partner=GAIA_PRODUCT.elec_partner,
            product_module_outsourcing=GAIA_PRODUCT.module_outsourcing,
        )
        assert categories == [], f"BAT/GAIA: expected=[], actual={categories}"

    def test_tms_m_worker_sees_tms_for_gaia(self):
        """TC-03: TMS(M) 작업자 → GAIA module_outsourcing=TMS 매칭 → TMS 포함"""
        categories = get_task_categories_for_worker(
            worker_company='TMS(M)',
            worker_role='MECH',
            product_mech_partner=GAIA_PRODUCT.mech_partner,  # FNI (≠ TMS)
            product_elec_partner=GAIA_PRODUCT.elec_partner,
            product_module_outsourcing=GAIA_PRODUCT.module_outsourcing,  # TMS
        )
        # module_outsourcing=TMS → TMS 포함
        assert 'TMS' in categories, f"TMS(M)/GAIA: 'TMS' 카테고리 없음, actual={categories}"

    def test_tms_e_worker_sees_elec_for_gaia(self):
        """TC-04: TMS(E) 작업자 → GAIA elec_partner=TMS 매칭 → ELEC만"""
        categories = get_task_categories_for_worker(
            worker_company='TMS(E)',
            worker_role='ELEC',
            product_mech_partner=GAIA_PRODUCT.mech_partner,
            product_elec_partner=GAIA_PRODUCT.elec_partner,  # TMS
            product_module_outsourcing=GAIA_PRODUCT.module_outsourcing,
        )
        assert 'ELEC' in categories, f"TMS(E)/GAIA: 'ELEC' 없음, actual={categories}"

    def test_ps_worker_sees_nothing_for_gaia(self):
        """TC-05: P&S 작업자 → GAIA elec_partner=TMS ≠ P&S → 빈 리스트"""
        categories = get_task_categories_for_worker(
            worker_company='P&S',
            worker_role='ELEC',
            product_mech_partner=GAIA_PRODUCT.mech_partner,
            product_elec_partner=GAIA_PRODUCT.elec_partner,  # TMS ≠ P&S
            product_module_outsourcing=GAIA_PRODUCT.module_outsourcing,
        )
        assert categories == [], f"P&S/GAIA: expected=[], actual={categories}"

    def test_ca_worker_sees_nothing_for_gaia(self):
        """TC-06: C&A 작업자 → GAIA elec_partner=TMS ≠ C&A → 빈 리스트"""
        categories = get_task_categories_for_worker(
            worker_company='C&A',
            worker_role='ELEC',
            product_mech_partner=GAIA_PRODUCT.mech_partner,
            product_elec_partner=GAIA_PRODUCT.elec_partner,
            product_module_outsourcing=GAIA_PRODUCT.module_outsourcing,
        )
        assert categories == [], f"C&A/GAIA: expected=[], actual={categories}"

    def test_gst_admin_sees_all_for_gaia(self):
        """TC-07: GST ADMIN → 필터 없음 (빈 리스트 또는 None = 전체 표시)"""
        categories = get_task_categories_for_worker(
            worker_company='GST',
            worker_role='ADMIN',
            product_mech_partner=GAIA_PRODUCT.mech_partner,
            product_elec_partner=GAIA_PRODUCT.elec_partner,
            product_module_outsourcing=GAIA_PRODUCT.module_outsourcing,
        )
        # ADMIN → 빈 리스트 또는 None (필터 없음 = 전체 조회)
        # filter_tasks_for_worker에서 not visible_categories → 전체 반환
        assert not categories, f"GST ADMIN: 필터 없음 expected (falsy), actual={categories}"


# ──────────────────────────────────────────────
# TC-08~TC-11: DRAGON 제품 기준 필터링
# ──────────────────────────────────────────────

class TestDRAGONProductFiltering:
    """
    TC-08~TC-11: DRAGON 제품 (TMS/P&S/None) 기준 회사별 Task 카테고리 필터링
    """

    def test_tms_m_worker_sees_mech_for_dragon(self):
        """TC-08: TMS(M) 작업자 → DRAGON mech_partner=TMS 매칭 → MECH 포함"""
        categories = get_task_categories_for_worker(
            worker_company='TMS(M)',
            worker_role='MECH',
            product_mech_partner=DRAGON_PRODUCT.mech_partner,   # TMS
            product_elec_partner=DRAGON_PRODUCT.elec_partner,
            product_module_outsourcing=DRAGON_PRODUCT.module_outsourcing,  # None
        )
        # mech_partner=TMS → MECH 포함
        assert 'MECH' in categories, f"TMS(M)/DRAGON: 'MECH' 없음, actual={categories}"

    def test_fni_worker_sees_nothing_for_dragon(self):
        """TC-09: FNI 작업자 → DRAGON mech_partner=TMS ≠ FNI → 빈 리스트"""
        categories = get_task_categories_for_worker(
            worker_company='FNI',
            worker_role='MECH',
            product_mech_partner=DRAGON_PRODUCT.mech_partner,   # TMS ≠ FNI
            product_elec_partner=DRAGON_PRODUCT.elec_partner,
            product_module_outsourcing=DRAGON_PRODUCT.module_outsourcing,
        )
        assert categories == [], f"FNI/DRAGON: expected=[], actual={categories}"

    def test_ps_worker_sees_elec_for_dragon(self):
        """TC-10: P&S 작업자 → DRAGON elec_partner=P&S 매칭 → ELEC만"""
        categories = get_task_categories_for_worker(
            worker_company='P&S',
            worker_role='ELEC',
            product_mech_partner=DRAGON_PRODUCT.mech_partner,
            product_elec_partner=DRAGON_PRODUCT.elec_partner,   # P&S
            product_module_outsourcing=DRAGON_PRODUCT.module_outsourcing,
        )
        assert categories == ['ELEC'], f"P&S/DRAGON: expected=['ELEC'], actual={categories}"

    def test_tms_e_sees_nothing_for_dragon(self):
        """TC-11: TMS(E) 작업자 → DRAGON elec_partner=P&S ≠ TMS → 빈 리스트"""
        categories = get_task_categories_for_worker(
            worker_company='TMS(E)',
            worker_role='ELEC',
            product_mech_partner=DRAGON_PRODUCT.mech_partner,
            product_elec_partner=DRAGON_PRODUCT.elec_partner,   # P&S ≠ TMS
            product_module_outsourcing=DRAGON_PRODUCT.module_outsourcing,
        )
        assert categories == [], f"TMS(E)/DRAGON: expected=[], actual={categories}"


# ──────────────────────────────────────────────
# TC-12~TC-14: GALLANT 제품 기준 필터링
# ──────────────────────────────────────────────

class TestGALLANTProductFiltering:
    """
    TC-12~TC-14: GALLANT 제품 (BAT/C&A/None) 기준 회사별 Task 카테고리 필터링
    """

    def test_bat_worker_sees_mech_for_gallant(self):
        """TC-12: BAT 작업자 → GALLANT mech_partner=BAT 매칭 → MECH만"""
        categories = get_task_categories_for_worker(
            worker_company='BAT',
            worker_role='MECH',
            product_mech_partner=GALLANT_PRODUCT.mech_partner,  # BAT
            product_elec_partner=GALLANT_PRODUCT.elec_partner,
            product_module_outsourcing=GALLANT_PRODUCT.module_outsourcing,
        )
        assert categories == ['MECH'], f"BAT/GALLANT: expected=['MECH'], actual={categories}"

    def test_ca_worker_sees_elec_for_gallant(self):
        """TC-13: C&A 작업자 → GALLANT elec_partner=C&A 매칭 → ELEC만"""
        categories = get_task_categories_for_worker(
            worker_company='C&A',
            worker_role='ELEC',
            product_mech_partner=GALLANT_PRODUCT.mech_partner,
            product_elec_partner=GALLANT_PRODUCT.elec_partner,  # C&A
            product_module_outsourcing=GALLANT_PRODUCT.module_outsourcing,
        )
        assert categories == ['ELEC'], f"C&A/GALLANT: expected=['ELEC'], actual={categories}"

    def test_fni_worker_sees_nothing_for_gallant(self):
        """TC-14: FNI 작업자 → GALLANT mech_partner=BAT ≠ FNI → 빈 리스트"""
        categories = get_task_categories_for_worker(
            worker_company='FNI',
            worker_role='MECH',
            product_mech_partner=GALLANT_PRODUCT.mech_partner,  # BAT ≠ FNI
            product_elec_partner=GALLANT_PRODUCT.elec_partner,
            product_module_outsourcing=GALLANT_PRODUCT.module_outsourcing,
        )
        assert categories == [], f"FNI/GALLANT: expected=[], actual={categories}"


# ──────────────────────────────────────────────
# TC-15~TC-17: GST 사내 역할 기반 필터링
# ──────────────────────────────────────────────

class TestGSTRoleBasedFiltering:
    """
    TC-15~TC-17: GST 사내직원 role 기반 필터링 (PI, QI, SI, ADMIN)
    """

    def test_pi_role_sees_pi_category(self):
        """TC-15: GST PI 역할 → ['PI'] 카테고리"""
        categories = get_task_categories_for_worker(
            worker_company='GST',
            worker_role='PI',
            product_mech_partner='FNI',
            product_elec_partner='TMS',
            product_module_outsourcing='TMS',
        )
        assert categories == ['PI'], f"GST PI: expected=['PI'], actual={categories}"

    def test_qi_role_sees_qi_category(self):
        """TC-16: GST QI 역할 → ['QI'] 카테고리"""
        categories = get_task_categories_for_worker(
            worker_company='GST',
            worker_role='QI',
            product_mech_partner='FNI',
            product_elec_partner='TMS',
            product_module_outsourcing='TMS',
        )
        assert categories == ['QI'], f"GST QI: expected=['QI'], actual={categories}"

    def test_si_role_sees_si_category(self):
        """TC-17: GST SI 역할 → ['SI'] 카테고리"""
        categories = get_task_categories_for_worker(
            worker_company='GST',
            worker_role='SI',
            product_mech_partner='FNI',
            product_elec_partner='TMS',
            product_module_outsourcing='TMS',
        )
        assert categories == ['SI'], f"GST SI: expected=['SI'], actual={categories}"


# ──────────────────────────────────────────────
# TC-18~TC-19: filter_tasks_for_worker 통합 테스트
# ──────────────────────────────────────────────

class TestFilterTasksForWorker:
    """
    TC-18~TC-19: filter_tasks_for_worker() 함수로 실제 Task 목록 필터링 검증
    """

    def test_fni_worker_filtered_tasks_for_gaia(self):
        """TC-18: FNI 작업자 → GAIA 제품에서 MECH Task만 반환"""
        filtered = filter_tasks_for_worker(
            tasks=ALL_TASKS,
            worker_company='FNI',
            worker_role='MECH',
            product=GAIA_PRODUCT,
        )
        categories = {t.task_category for t in filtered}
        assert categories == {'MECH'}, (
            f"FNI/GAIA 필터 결과 카테고리: expected={{'MECH'}}, actual={categories}"
        )
        # MECH Task 수 = 7
        assert len(filtered) == 7, f"FNI/GAIA MECH Task 수: expected=7, actual={len(filtered)}"

    def test_admin_sees_all_tasks(self):
        """TC-19: GST ADMIN → 모든 Task 반환 (필터 없음)"""
        filtered = filter_tasks_for_worker(
            tasks=ALL_TASKS,
            worker_company='GST',
            worker_role='ADMIN',
            product=GAIA_PRODUCT,
        )
        # ADMIN은 필터 없음 → 전체 15개 반환
        assert len(filtered) == len(ALL_TASKS), (
            f"ADMIN 필터 결과: expected={len(ALL_TASKS)}, actual={len(filtered)}"
        )

    def test_ps_worker_sees_elec_tasks_for_dragon(self):
        """TC-20 (보너스): P&S 작업자 → DRAGON 제품에서 ELEC Task만"""
        filtered = filter_tasks_for_worker(
            tasks=ALL_TASKS,
            worker_company='P&S',
            worker_role='ELEC',
            product=DRAGON_PRODUCT,
        )
        categories = {t.task_category for t in filtered}
        assert categories == {'ELEC'}, (
            f"P&S/DRAGON 필터 결과: expected={{'ELEC'}}, actual={categories}"
        )
        # ELEC Task 수 = 6
        assert len(filtered) == 6, f"P&S/DRAGON ELEC Task 수: expected=6, actual={len(filtered)}"

    def test_bat_worker_sees_mech_tasks_for_gallant(self):
        """TC-21 (보너스): BAT 작업자 → GALLANT 제품에서 MECH Task만"""
        filtered = filter_tasks_for_worker(
            tasks=ALL_TASKS,
            worker_company='BAT',
            worker_role='MECH',
            product=GALLANT_PRODUCT,
        )
        categories = {t.task_category for t in filtered}
        assert categories == {'MECH'}, (
            f"BAT/GALLANT 필터 결과: expected={{'MECH'}}, actual={categories}"
        )

    def test_mismatched_worker_sees_no_tasks(self):
        """TC-22 (보너스): 매칭되지 않는 회사 작업자 → 빈 Task 목록"""
        filtered = filter_tasks_for_worker(
            tasks=ALL_TASKS,
            worker_company='BAT',
            worker_role='MECH',
            product=GAIA_PRODUCT,  # mech_partner=FNI ≠ BAT
        )
        assert filtered == [], (
            f"BAT/GAIA (mismatch) 필터 결과: expected=[], actual={filtered}"
        )
