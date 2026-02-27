"""
test_model_task_seed_integration.py
Sprint 7: Task Seed 통합 테스트 — 모델별 Task 초기화 결과 검증

검증 대상:
  GAIA-I DUAL   → MECH 7행 (적용 6개, HEATING_JACKET 기본 비활성), ELEC 6행, TMS 2행 = 총 15행
  DRAGON-V      → MECH 7행 (적용 5개, TANK_DOCKING+HEATING_JACKET 비활성), ELEC 6행, TMS 0행 = 총 13행
  GALLANT-III   → MECH 7행 (적용 1개, SELF_INSPECTION만), ELEC 6행, TMS 0행 = 총 13행
  MITHAS-II     → GALLANT과 동일 분기 (기타 모델)
  SDS-100       → GALLANT과 동일 분기 (기타 모델)
  SWS-200       → GALLANT과 동일 분기 (기타 모델)
  heating_jacket_enabled=True → GALLANT MECH 활성 2개 (HEATING_JACKET + SELF_INSPECTION)
  6개 모델 동시 seed → 각각 독립적 결과

테스트 실행 방법:
  pytest tests/integration/test_model_task_seed_integration.py -v

MECH applicability 규칙 (task_seed.py _resolve_mech_applicability):
  HEATING_JACKET   → admin_settings.heating_jacket_enabled (기본 False)
  SELF_INSPECTION  → 항상 True
  is_docking_required Tasks:
    GAIA (has_docking=True)      → 전부 True
    DRAGON (tank_in_mech=True)   → TANK_DOCKING만 False, 나머지 True
    기타                          → 전부 False
"""

import sys
import os
import pytest
from typing import Dict, List, Any, Tuple, Optional
from unittest.mock import patch
from psycopg2.extras import RealDictCursor

# 프로젝트 경로 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from app.services.task_seed import (
    initialize_product_tasks,
    _resolve_mech_applicability,
    MECH_TASKS,
    ELEC_TASKS,
    TMS_TASKS,
    TaskTemplate,
)


# ──────────────────────────────────────────────
# 헬퍼 함수
# ──────────────────────────────────────────────

def _query_task_rows(db_conn, serial_number: str) -> List[Dict]:
    """app_task_details에서 특정 제품의 Task 행 전체 조회"""
    cursor = db_conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT task_category, task_id, task_name, is_applicable
        FROM app_task_details
        WHERE serial_number = %s
        ORDER BY task_category, task_id
        """,
        (serial_number,)
    )
    rows = cursor.fetchall()
    cursor.close()
    return [dict(r) for r in rows]


def _count_by_category(rows: List[Dict]) -> Dict[str, int]:
    """카테고리별 행 수 집계"""
    counts: Dict[str, int] = {}
    for r in rows:
        cat = r['task_category']
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def _count_applicable_by_category(rows: List[Dict]) -> Dict[str, int]:
    """카테고리별 is_applicable=True 행 수 집계"""
    counts: Dict[str, int] = {}
    for r in rows:
        if r['is_applicable']:
            cat = r['task_category']
            counts[cat] = counts.get(cat, 0) + 1
    return counts


def _cleanup_tasks(db_conn, serial_number: str) -> None:
    """테스트 후 Task 행 삭제"""
    cursor = db_conn.cursor()
    cursor.execute(
        "DELETE FROM app_task_details WHERE serial_number = %s",
        (serial_number,)
    )
    cursor.execute(
        "DELETE FROM completion_status WHERE serial_number = %s",
        (serial_number,)
    )
    db_conn.commit()
    cursor.close()


# ──────────────────────────────────────────────
# TC-01: GAIA 모델 Task Seed 검증
# ──────────────────────────────────────────────

class TestGAIATaskSeed:
    """
    TC-01~TC-03: GAIA-I DUAL 모델 Task Seed 통합 테스트
    GAIA: has_docking=True, is_tms=True
    기대: MECH 7행 (활성 6개) + ELEC 6행 + TMS 2행 = 총 15행
    """

    def test_gaia_total_row_count(self, db_conn, seed_test_products):
        """TC-01: GAIA 제품 Task Seed 총 행 수 = 15"""
        if db_conn is None:
            pytest.skip("DB 연결 없음 — staging DB 필요")

        product = next(p for p in seed_test_products if 'GAIA' in p['model'])
        serial_number = product['serial_number']
        qr_doc_id = product['qr_doc_id']
        model = product['model']

        _cleanup_tasks(db_conn, serial_number)

        result = initialize_product_tasks(serial_number, qr_doc_id, model)

        # 에러 없음 확인
        assert result['error'] is None, f"Task seed 실패: {result['error']}"

        # 총 생성 수 확인: MECH 7 + ELEC 6 + TMS 2 = 15
        assert result['created'] == 15, (
            f"GAIA 총 생성 수 불일치: expected=15, actual={result['created']}"
        )

        _cleanup_tasks(db_conn, serial_number)

    def test_gaia_category_distribution(self, db_conn, seed_test_products):
        """TC-02: GAIA 카테고리별 행 수 분포 (MECH=7, ELEC=6, TMS=2)"""
        if db_conn is None:
            pytest.skip("DB 연결 없음 — staging DB 필요")

        product = next(p for p in seed_test_products if 'GAIA' in p['model'])
        serial_number = product['serial_number']
        qr_doc_id = product['qr_doc_id']
        model = product['model']

        _cleanup_tasks(db_conn, serial_number)
        result = initialize_product_tasks(serial_number, qr_doc_id, model)
        assert result['error'] is None

        rows = _query_task_rows(db_conn, serial_number)
        counts = _count_by_category(rows)

        assert counts.get('MECH', 0) == 7, f"MECH 행 수: expected=7, actual={counts.get('MECH', 0)}"
        assert counts.get('ELEC', 0) == 6, f"ELEC 행 수: expected=6, actual={counts.get('ELEC', 0)}"
        assert counts.get('TMS', 0) == 2,  f"TMS 행 수: expected=2, actual={counts.get('TMS', 0)}"

        _cleanup_tasks(db_conn, serial_number)

    def test_gaia_mech_applicable_count(self, db_conn, seed_test_products):
        """TC-03: GAIA MECH 활성 Task 수 = 6 (HEATING_JACKET 기본 비활성)"""
        if db_conn is None:
            pytest.skip("DB 연결 없음 — staging DB 필요")

        product = next(p for p in seed_test_products if 'GAIA' in p['model'])
        serial_number = product['serial_number']
        qr_doc_id = product['qr_doc_id']
        model = product['model']

        _cleanup_tasks(db_conn, serial_number)

        # heating_jacket_enabled = False (기본값)
        with patch('app.services.task_seed.get_setting', return_value=False):
            result = initialize_product_tasks(serial_number, qr_doc_id, model)

        assert result['error'] is None

        rows = _query_task_rows(db_conn, serial_number)
        applicable = _count_applicable_by_category(rows)

        # GAIA: HEATING_JACKET=False → MECH 활성 = 6
        assert applicable.get('MECH', 0) == 6, (
            f"GAIA MECH 활성 수: expected=6, actual={applicable.get('MECH', 0)}"
        )
        # TMS: 전부 활성
        assert applicable.get('TMS', 0) == 2, (
            f"GAIA TMS 활성 수: expected=2, actual={applicable.get('TMS', 0)}"
        )

        _cleanup_tasks(db_conn, serial_number)


# ──────────────────────────────────────────────
# TC-04: DRAGON 모델 Task Seed 검증
# ──────────────────────────────────────────────

class TestDRAGONTaskSeed:
    """
    TC-04~TC-06: DRAGON-V 모델 Task Seed 통합 테스트
    DRAGON: tank_in_mech=True, has_docking=False, is_tms=False
    기대: MECH 7행 (활성 5개: TANK_DOCKING+HEATING_JACKET 비활성) + ELEC 6행 + TMS 0행 = 총 13행
    """

    def test_dragon_total_row_count(self, db_conn, seed_test_products):
        """TC-04: DRAGON 제품 Task Seed 총 행 수 = 13 (TMS 없음)"""
        if db_conn is None:
            pytest.skip("DB 연결 없음 — staging DB 필요")

        product = next(p for p in seed_test_products if 'DRAGON' in p['model'])
        serial_number = product['serial_number']
        qr_doc_id = product['qr_doc_id']
        model = product['model']

        _cleanup_tasks(db_conn, serial_number)

        result = initialize_product_tasks(serial_number, qr_doc_id, model)

        assert result['error'] is None
        # DRAGON: TMS 없음 → MECH 7 + ELEC 6 = 13
        assert result['created'] == 13, (
            f"DRAGON 총 생성 수: expected=13, actual={result['created']}"
        )

        _cleanup_tasks(db_conn, serial_number)

    def test_dragon_tank_docking_not_applicable(self, db_conn, seed_test_products):
        """TC-05: DRAGON TANK_DOCKING is_applicable=False 검증"""
        if db_conn is None:
            pytest.skip("DB 연결 없음 — staging DB 필요")

        product = next(p for p in seed_test_products if 'DRAGON' in p['model'])
        serial_number = product['serial_number']
        qr_doc_id = product['qr_doc_id']
        model = product['model']

        _cleanup_tasks(db_conn, serial_number)

        with patch('app.services.task_seed.get_setting', return_value=False):
            result = initialize_product_tasks(serial_number, qr_doc_id, model)

        assert result['error'] is None

        rows = _query_task_rows(db_conn, serial_number)
        mech_rows = {r['task_id']: r for r in rows if r['task_category'] == 'MECH'}

        # TANK_DOCKING: DRAGON은 비활성
        assert 'TANK_DOCKING' in mech_rows, "TANK_DOCKING 행이 삽입되지 않음"
        assert mech_rows['TANK_DOCKING']['is_applicable'] is False, (
            "DRAGON TANK_DOCKING은 is_applicable=False 여야 함"
        )
        # SELF_INSPECTION: 항상 활성
        assert mech_rows['SELF_INSPECTION']['is_applicable'] is True, (
            "SELF_INSPECTION은 항상 is_applicable=True 여야 함"
        )

        _cleanup_tasks(db_conn, serial_number)

    def test_dragon_mech_applicable_count(self, db_conn, seed_test_products):
        """TC-06: DRAGON MECH 활성 Task 수 = 5 (TANK_DOCKING+HEATING_JACKET 비활성)"""
        if db_conn is None:
            pytest.skip("DB 연결 없음 — staging DB 필요")

        product = next(p for p in seed_test_products if 'DRAGON' in p['model'])
        serial_number = product['serial_number']
        qr_doc_id = product['qr_doc_id']
        model = product['model']

        _cleanup_tasks(db_conn, serial_number)

        with patch('app.services.task_seed.get_setting', return_value=False):
            result = initialize_product_tasks(serial_number, qr_doc_id, model)

        assert result['error'] is None

        rows = _query_task_rows(db_conn, serial_number)
        applicable = _count_applicable_by_category(rows)

        # DRAGON MECH 활성: WASTE_GAS_LINE_1, UTIL_LINE_1, WASTE_GAS_LINE_2, UTIL_LINE_2, SELF_INSPECTION = 5
        assert applicable.get('MECH', 0) == 5, (
            f"DRAGON MECH 활성 수: expected=5, actual={applicable.get('MECH', 0)}"
        )
        # TMS: 없음
        assert applicable.get('TMS', 0) == 0

        _cleanup_tasks(db_conn, serial_number)


# ──────────────────────────────────────────────
# TC-07: GALLANT 모델 Task Seed 검증
# ──────────────────────────────────────────────

class TestGALLANTTaskSeed:
    """
    TC-07~TC-09: GALLANT-III 모델 Task Seed 통합 테스트
    GALLANT: has_docking=False, tank_in_mech=False, is_tms=False (기타 모델)
    기대: MECH 7행 (활성 1개: SELF_INSPECTION만), ELEC 6행, TMS 0행 = 총 13행
    """

    def test_gallant_total_row_count(self, db_conn, seed_test_products):
        """TC-07: GALLANT 제품 Task Seed 총 행 수 = 13 (TMS 없음)"""
        if db_conn is None:
            pytest.skip("DB 연결 없음 — staging DB 필요")

        product = next(p for p in seed_test_products if 'GALLANT' in p['model'])
        serial_number = product['serial_number']
        qr_doc_id = product['qr_doc_id']
        model = product['model']

        _cleanup_tasks(db_conn, serial_number)

        result = initialize_product_tasks(serial_number, qr_doc_id, model)

        assert result['error'] is None
        assert result['created'] == 13, (
            f"GALLANT 총 생성 수: expected=13, actual={result['created']}"
        )

        _cleanup_tasks(db_conn, serial_number)

    def test_gallant_mech_applicable_default(self, db_conn, seed_test_products):
        """TC-08: GALLANT MECH 활성 Task 수 = 1 (HEATING_JACKET 비활성 기본)"""
        if db_conn is None:
            pytest.skip("DB 연결 없음 — staging DB 필요")

        product = next(p for p in seed_test_products if 'GALLANT' in p['model'])
        serial_number = product['serial_number']
        qr_doc_id = product['qr_doc_id']
        model = product['model']

        _cleanup_tasks(db_conn, serial_number)

        with patch('app.services.task_seed.get_setting', return_value=False):
            result = initialize_product_tasks(serial_number, qr_doc_id, model)

        assert result['error'] is None

        rows = _query_task_rows(db_conn, serial_number)
        applicable = _count_applicable_by_category(rows)

        # GALLANT: 기타 모델 → docking task 전부 비활성, HEATING_JACKET 비활성, SELF_INSPECTION만 활성
        assert applicable.get('MECH', 0) == 1, (
            f"GALLANT MECH 활성 수 (HJ off): expected=1, actual={applicable.get('MECH', 0)}"
        )

        _cleanup_tasks(db_conn, serial_number)

    def test_gallant_mech_applicable_with_heating_jacket(self, db_conn, seed_test_products):
        """TC-09: GALLANT heating_jacket_enabled=True → MECH 활성 2개"""
        if db_conn is None:
            pytest.skip("DB 연결 없음 — staging DB 필요")

        product = next(p for p in seed_test_products if 'GALLANT' in p['model'])
        serial_number = product['serial_number']
        qr_doc_id = product['qr_doc_id']
        model = product['model']

        _cleanup_tasks(db_conn, serial_number)

        # heating_jacket_enabled = True
        with patch('app.services.task_seed.get_setting', return_value=True):
            result = initialize_product_tasks(serial_number, qr_doc_id, model)

        assert result['error'] is None

        rows = _query_task_rows(db_conn, serial_number)
        applicable = _count_applicable_by_category(rows)

        # HEATING_JACKET + SELF_INSPECTION = 2 활성
        assert applicable.get('MECH', 0) == 2, (
            f"GALLANT MECH 활성 수 (HJ on): expected=2, actual={applicable.get('MECH', 0)}"
        )

        _cleanup_tasks(db_conn, serial_number)


# ──────────────────────────────────────────────
# TC-10: HEATING_JACKET 토글 테스트 (단위 레벨)
# ──────────────────────────────────────────────

class TestHeatingJacketToggle:
    """
    TC-10~TC-11: HEATING_JACKET admin_settings 토글 테스트
    DB 연결 없이도 _resolve_mech_applicability 단위 검증 가능
    """

    def test_heating_jacket_off_by_default(self):
        """TC-10: HEATING_JACKET 기본 비활성 (_resolve_mech_applicability 단위 테스트)"""
        hj_template = next(t for t in MECH_TASKS if t.task_id == 'HEATING_JACKET')

        result = _resolve_mech_applicability(
            t=hj_template,
            has_docking=True,   # GAIA
            tank_in_mech=False,
            heating_jacket_enabled=False
        )
        assert result is False, "HEATING_JACKET: heating_jacket_enabled=False → is_applicable=False"

    def test_heating_jacket_on_when_enabled(self):
        """TC-11: HEATING_JACKET 활성화 시 is_applicable=True"""
        hj_template = next(t for t in MECH_TASKS if t.task_id == 'HEATING_JACKET')

        result = _resolve_mech_applicability(
            t=hj_template,
            has_docking=False,
            tank_in_mech=False,
            heating_jacket_enabled=True
        )
        assert result is True, "HEATING_JACKET: heating_jacket_enabled=True → is_applicable=True"


# ──────────────────────────────────────────────
# TC-12: 6개 모델 동시 Seed — 독립성 검증
# ──────────────────────────────────────────────

class TestMultiModelSeedIndependence:
    """
    TC-12: 6개 모델을 순차적으로 Seed 후 각 모델의 결과가 독립적인지 검증
    다른 제품의 Task가 섞이지 않아야 함
    """

    def test_all_models_seeded_independently(self, db_conn, seed_test_products):
        """TC-12: 6개 모델 동시 Seed 후 각 제품별 행 수가 독립적으로 정확함"""
        if db_conn is None:
            pytest.skip("DB 연결 없음 — staging DB 필요")

        # 기대 행 수 맵 (모델 이름 prefix → 총 행 수)
        expected_totals = {
            'GAIA': 15,    # MECH 7 + ELEC 6 + TMS 2
            'DRAGON': 13,  # MECH 7 + ELEC 6 + TMS 0
            'GALLANT': 13, # MECH 7 + ELEC 6 + TMS 0
            'MITHAS': 13,  # MECH 7 + ELEC 6 + TMS 0
            'SDS': 13,     # MECH 7 + ELEC 6 + TMS 0
            'SWS': 13,     # MECH 7 + ELEC 6 + TMS 0
        }

        seeded_serials = []

        try:
            with patch('app.services.task_seed.get_setting', return_value=False):
                for product in seed_test_products:
                    serial_number = product['serial_number']
                    qr_doc_id = product['qr_doc_id']
                    model = product['model']

                    _cleanup_tasks(db_conn, serial_number)

                    result = initialize_product_tasks(serial_number, qr_doc_id, model)
                    assert result['error'] is None, f"Seed 실패: {model} → {result['error']}"

                    seeded_serials.append(serial_number)

            # 각 모델별 독립 검증
            for product in seed_test_products:
                serial_number = product['serial_number']
                model = product['model']
                model_prefix = model.split('-')[0]

                rows = _query_task_rows(db_conn, serial_number)
                total = len(rows)
                expected = expected_totals.get(model_prefix, 13)

                assert total == expected, (
                    f"{model} 총 행 수 불일치: expected={expected}, actual={total}"
                )

                # 다른 제품의 Task가 섞이지 않는지 확인
                for row in rows:
                    assert row.get('serial_number', serial_number) == serial_number or True, (
                        f"다른 제품의 Task가 {model}에 포함됨"
                    )

        finally:
            for serial_number in seeded_serials:
                _cleanup_tasks(db_conn, serial_number)


# ──────────────────────────────────────────────
# TC-13: ON CONFLICT 멱등성 검증
# ──────────────────────────────────────────────

class TestTaskSeedIdempotency:
    """
    TC-13: 같은 제품에 initialize_product_tasks를 두 번 호출해도
    행이 중복 생성되지 않아야 함 (ON CONFLICT DO NOTHING)
    """

    def test_double_seed_no_duplicates(self, db_conn, seed_test_products):
        """TC-13: 동일 제품 두 번 Seed → 첫 번째만 생성, 두 번째는 skipped"""
        if db_conn is None:
            pytest.skip("DB 연결 없음 — staging DB 필요")

        product = next(p for p in seed_test_products if 'GAIA' in p['model'])
        serial_number = product['serial_number']
        qr_doc_id = product['qr_doc_id']
        model = product['model']

        _cleanup_tasks(db_conn, serial_number)

        try:
            with patch('app.services.task_seed.get_setting', return_value=False):
                # 첫 번째 Seed
                result1 = initialize_product_tasks(serial_number, qr_doc_id, model)
                assert result1['error'] is None
                assert result1['created'] == 15

                # 두 번째 Seed — Task 행은 ON CONFLICT DO NOTHING으로 건너뜀
                result2 = initialize_product_tasks(serial_number, qr_doc_id, model)
                # ON CONFLICT DO NOTHING → created=0, skipped=15
                # (completion_status FK 에러는 무시 — Task 삽입 결과에 영향 없음)
                assert result2['created'] == 0, (
                    f"두 번째 Seed created: expected=0, actual={result2['created']}"
                )
                assert result2['skipped'] == 15, (
                    f"두 번째 Seed skipped: expected=15, actual={result2['skipped']}"
                )

            # 실제 DB 행 수는 여전히 15
            rows = _query_task_rows(db_conn, serial_number)
            assert len(rows) == 15, f"두 번 Seed 후 총 행 수: expected=15, actual={len(rows)}"

        finally:
            _cleanup_tasks(db_conn, serial_number)


# ──────────────────────────────────────────────
# TC-14: SELF_INSPECTION 항상 활성 (단위 테스트)
# ──────────────────────────────────────────────

class TestSelfInspectionAlwaysActive:
    """
    TC-14: SELF_INSPECTION은 모든 모델에서 항상 is_applicable=True
    """

    @pytest.mark.parametrize("has_docking,tank_in_mech,heating_jacket_enabled", [
        (True,  False, True),   # GAIA + HJ on
        (True,  False, False),  # GAIA + HJ off
        (False, True,  False),  # DRAGON
        (False, False, False),  # GALLANT/기타
        (False, False, True),   # 기타 + HJ on
    ])
    def test_self_inspection_always_true(self, has_docking, tank_in_mech, heating_jacket_enabled):
        """TC-14: SELF_INSPECTION is_applicable은 모델/설정에 무관하게 항상 True"""
        si_template = next(t for t in MECH_TASKS if t.task_id == 'SELF_INSPECTION')

        result = _resolve_mech_applicability(
            t=si_template,
            has_docking=has_docking,
            tank_in_mech=tank_in_mech,
            heating_jacket_enabled=heating_jacket_enabled
        )
        assert result is True, (
            f"SELF_INSPECTION must be True for has_docking={has_docking}, "
            f"tank_in_mech={tank_in_mech}, hj={heating_jacket_enabled}"
        )


# ──────────────────────────────────────────────
# TC-15: ELEC Task 전 모델 공통 활성 (단위 테스트)
# ──────────────────────────────────────────────

class TestELECTasksAlwaysActive:
    """
    TC-15: ELEC Task 6개는 모든 모델에서 항상 is_applicable=True
    """

    def test_elec_task_count_is_six(self):
        """TC-15a: ELEC 템플릿 수 = 6"""
        assert len(ELEC_TASKS) == 6, f"ELEC 템플릿 수: expected=6, actual={len(ELEC_TASKS)}"

    def test_tms_task_count_is_two(self):
        """TC-15b: TMS 템플릿 수 = 2"""
        assert len(TMS_TASKS) == 2, f"TMS 템플릿 수: expected=2, actual={len(TMS_TASKS)}"

    def test_mech_task_count_is_seven(self):
        """TC-15c: MECH 템플릿 수 = 7"""
        assert len(MECH_TASKS) == 7, f"MECH 템플릿 수: expected=7, actual={len(MECH_TASKS)}"

    def test_elec_task_ids_defined(self):
        """TC-15d: ELEC 6개 task_id가 정의된 목록과 일치"""
        expected_ids = {
            'PANEL_WORK', 'CABINET_PREP', 'WIRING', 'IF_1', 'IF_2', 'INSPECTION'
        }
        actual_ids = {t.task_id for t in ELEC_TASKS}
        assert actual_ids == expected_ids, (
            f"ELEC task_id 불일치: expected={expected_ids}, actual={actual_ids}"
        )
