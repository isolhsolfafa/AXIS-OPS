"""
모델별 Task Seed 통합 테스트
Model Task Seed Integration Tests — Sprint 7 Phase 3

대상:
- initialize_product_tasks(serial_number, qr_doc_id, model_name) 직접 호출
- GET /api/app/product/<qr_doc_id>  — 제품 조회 시 자동 seed 트리거
- 6개 모델별 MECH/ELEC/TMS/PI/QI/SI 행 수 + is_applicable 수 검증

실제 DB model_config 값 (2026-03-26 기준):
  GAIA:    has_docking=T, is_tms=T,  tank_in_mech=F, pi_lng_util=T, pi_chamber=T
  DRAGON:  has_docking=F, is_tms=F,  tank_in_mech=T, pi_lng_util=T, pi_chamber=T
  GALLANT: has_docking=F, is_tms=F,  tank_in_mech=T, pi_lng_util=T, pi_chamber=F
  MITHAS:  has_docking=F, is_tms=F,  tank_in_mech=F, pi_lng_util=T, pi_chamber=T
  SDS:     has_docking=F, is_tms=F,  tank_in_mech=F, pi_lng_util=T, pi_chamber=T
  SWS:     has_docking=F, is_tms=F,  tank_in_mech=T, pi_lng_util=F, pi_chamber=T

모델별 예상 Task 수 (heating_jacket_enabled=false 기본값 기준):
  ※ SI는 2개(SI_FINISHING + SI_SHIPMENT), PI는 2개, QI는 1개

  GAIA SINGLE (has_docking=T, is_tms=T, tank_in_mech=F):
    MECH 7행 / active 6 (HEATING_JACKET=F)
    ELEC 6행 / active 6
    TMS  2행 / active 2
    PI   2행, QI 1행, SI 2행
    합계 20행

  GAIA SINGLE: MECH 7행, ELEC 6행, TMS 2행, PI 2행, QI 1행, SI 2행
    합계 20행

  DRAGON (tank_in_mech=T, pi_lng_util=T → TANK_MODULE only extra):
    MECH 7+1=8행 / active 6 (TANK_DOCKING=F, HEATING_JACKET=F)
    ELEC 6행, TMS 0행, PI 2행, QI 1행, SI 2행
    합계 19행

  GALLANT (tank_in_mech=T, pi_lng_util=T, pi_chamber=F → TANK_MODULE only):
    MECH 7+1=8행 / active 6 (TANK_DOCKING=F, HEATING_JACKET=F; 나머지 docking 4개+SI+TM 활성)
    ELEC 6행, TMS 0행, PI 2행, QI 1행, SI 2행
    합계 19행

  MITHAS/SDS (tank_in_mech=F):
    MECH 7행 / active 1 (SELF_INSPECTION만)
    ELEC 6행, TMS 0행, PI 2행, QI 1행, SI 2행
    합계 18행

  SWS (tank_in_mech=T, pi_lng_util=F, pi_chamber=T → TANK_MODULE only):
    MECH 7+1=8행 / active 2 (SELF_INSPECTION + TANK_MODULE)
    ELEC 6행, TMS 0행, PI 2행, QI 1행, SI 2행
    합계 19행
"""

import pytest
import sys
from pathlib import Path
from typing import Dict, Tuple

# backend 경로 추가
backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


# ──────────────────────────────────────────────
# 공통 헬퍼
# ──────────────────────────────────────────────

def _insert_product(db_conn, serial_number: str, qr_doc_id: str, model: str) -> None:
    """plan.product_info + qr_registry 삽입 헬퍼"""
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO plan.product_info (serial_number, model)
        VALUES (%s, %s)
        ON CONFLICT (serial_number) DO NOTHING
    """, (serial_number, model))
    cursor.execute("""
        INSERT INTO public.qr_registry (qr_doc_id, serial_number)
        VALUES (%s, %s)
        ON CONFLICT (qr_doc_id) DO NOTHING
    """, (qr_doc_id, serial_number))
    db_conn.commit()
    cursor.close()


def _cleanup(db_conn, serial_number: str, qr_doc_id: str) -> None:
    """테스트 데이터 정리"""
    if db_conn is None or db_conn.closed:
        return
    try:
        cursor = db_conn.cursor()
        cursor.execute("DELETE FROM app_task_details WHERE serial_number = %s", (serial_number,))
        cursor.execute("DELETE FROM completion_status WHERE serial_number = %s", (serial_number,))
        cursor.execute("DELETE FROM public.qr_registry WHERE qr_doc_id = %s", (qr_doc_id,))
        cursor.execute("DELETE FROM plan.product_info WHERE serial_number = %s", (serial_number,))
        db_conn.commit()
        cursor.close()
    except Exception:
        pass


def _get_seed_summary(db_conn, serial_number: str) -> Dict[str, Dict[str, int]]:
    """
    시리얼 번호 기준 카테고리별 (total, active) 반환
    Returns: {'MECH': {'total': 7, 'active': 6}, 'ELEC': {...}, 'TMS': {...}}
    """
    cursor = db_conn.cursor()
    cursor.execute("""
        SELECT task_category,
               COUNT(*)                                         AS total,
               COUNT(*) FILTER (WHERE is_applicable = TRUE)    AS active
        FROM app_task_details
        WHERE serial_number = %s
        GROUP BY task_category
    """, (serial_number,))
    rows = cursor.fetchall()
    cursor.close()
    return {r[0]: {'total': r[1], 'active': r[2]} for r in rows}


def _set_heating_jacket(db_conn, enabled: bool) -> None:
    """admin_settings.heating_jacket_enabled 값 설정"""
    cursor = db_conn.cursor()
    cursor.execute("""
        UPDATE admin_settings
        SET setting_value = %s::jsonb
        WHERE setting_key = 'heating_jacket_enabled'
    """, ('true' if enabled else 'false',))
    db_conn.commit()
    cursor.close()


def _reset_heating_jacket(db_conn) -> None:
    """admin_settings.heating_jacket_enabled 기본값 복원"""
    _set_heating_jacket(db_conn, False)


def _run_seed(serial_number: str, qr_doc_id: str, model_name: str) -> Dict:
    """initialize_product_tasks 직접 호출 헬퍼"""
    from app.services.task_seed import initialize_product_tasks
    return initialize_product_tasks(serial_number, qr_doc_id, model_name)


# ──────────────────────────────────────────────
# GAIA 모델 Task Seed 검증
# ──────────────────────────────────────────────

class TestGAIATaskSeed:
    """
    GAIA-I (SINGLE): has_docking=True, is_tms=True
    결과: MECH 7 + ELEC 6 + TMS 2 + PI 2 + QI 1 + SI 2 = 20행
    heating_jacket_enabled=false 기준
    """

    def test_gaia_total_rows(self, db_conn):
        """TC-SEED-GAIA-01: GAIA-I seed → 총 20행 생성"""
        if db_conn is None:
            pytest.skip("DB 연결 없음")
        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        sn, qr = 'SN-INT-GAIA-001', 'DOC-INT-GAIA-001'
        # 이전 테스트 잔여 데이터 선제 정리 (ON CONFLICT DO NOTHING이 created 수를 줄이지 않도록)
        _cleanup(db_conn, sn, qr)
        _insert_product(db_conn, sn, qr, 'GAIA-I')
        try:
            result = _run_seed(sn, qr, 'GAIA-I')
            # TMS -L/-R qr_doc_id FK 위반으로 error가 날 수 있음 (non-blocking)
            # error가 없거나 FK 위반만 있으면 정상
            error = result.get('error')
            if error and 'foreign key' not in str(error).lower() and 'does not exist' not in str(error).lower():
                assert False, f"Seed 예상치 못한 에러: {error}"
            # GAIA-I SINGLE: MECH7+ELEC6+TMS2+PI2+QI1+SI2 = 20행
            created = result.get('created', 0)
            assert created == 20, \
                f"GAIA-I 총 20행 필요, got {created}"
        finally:
            _cleanup(db_conn, sn, qr)

    def test_gaia_mech_row_count(self, db_conn):
        """TC-SEED-GAIA-02: GAIA MECH → 7행 생성"""
        if db_conn is None:
            pytest.skip("DB 연결 없음")
        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        sn, qr = 'SN-INT-GAIA-002', 'DOC-INT-GAIA-002'
        _cleanup(db_conn, sn, qr)
        _insert_product(db_conn, sn, qr, 'GAIA-I')
        try:
            _run_seed(sn, qr, 'GAIA-I')
            summary = _get_seed_summary(db_conn, sn)
            mech = summary.get('MECH', {})
            assert mech.get('total') == 7, \
                f"GAIA MECH 7행 필요, got {mech.get('total')}"
        finally:
            _cleanup(db_conn, sn, qr)

    def test_gaia_mech_active_count_hj_disabled(self, db_conn):
        """
        TC-SEED-GAIA-03: GAIA MECH active 6개 (heating_jacket_enabled=false)
        HEATING_JACKET=F, 나머지 5개 docking + SELF_INSPECTION = 6 active
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")
        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        sn, qr = 'SN-INT-GAIA-003', 'DOC-INT-GAIA-003'
        _cleanup(db_conn, sn, qr)
        _insert_product(db_conn, sn, qr, 'GAIA-I')
        _set_heating_jacket(db_conn, False)
        try:
            _run_seed(sn, qr, 'GAIA-I')
            summary = _get_seed_summary(db_conn, sn)
            mech = summary.get('MECH', {})
            assert mech.get('active') == 6, \
                f"GAIA MECH active 6 필요 (HJ disabled), got {mech.get('active')}"
        finally:
            _cleanup(db_conn, sn, qr)
            _reset_heating_jacket(db_conn)

    def test_gaia_tms_rows(self, db_conn):
        """
        TC-SEED-GAIA-04: GAIA-I SINGLE → TMS 2행 생성
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")
        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        sn, qr = 'SN-INT-GAIA-004', 'DOC-INT-GAIA-004'
        _cleanup(db_conn, sn, qr)
        _insert_product(db_conn, sn, qr, 'GAIA-I')
        try:
            _run_seed(sn, qr, 'GAIA-I')
            summary = _get_seed_summary(db_conn, sn)
            tms = summary.get('TMS', {})
            assert tms.get('total', 0) == 2, \
                f"GAIA-I SINGLE: TMS 2행 필요, got {tms.get('total', 0)}"
        finally:
            _cleanup(db_conn, sn, qr)

    def test_gaia_elec_all_active(self, db_conn):
        """TC-SEED-GAIA-05: GAIA ELEC → 6행 전부 active"""
        if db_conn is None:
            pytest.skip("DB 연결 없음")
        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        sn, qr = 'SN-INT-GAIA-005', 'DOC-INT-GAIA-005'
        _cleanup(db_conn, sn, qr)
        _insert_product(db_conn, sn, qr, 'GAIA-I')
        try:
            _run_seed(sn, qr, 'GAIA-I')
            summary = _get_seed_summary(db_conn, sn)
            elec = summary.get('ELEC', {})
            assert elec.get('total') == 6, \
                f"GAIA ELEC 6행 필요, got {elec.get('total')}"
            assert elec.get('active') == 6, \
                f"GAIA ELEC active 6 필요, got {elec.get('active')}"
        finally:
            _cleanup(db_conn, sn, qr)

    def test_gaia_tank_docking_applicable(self, db_conn):
        """TC-SEED-GAIA-06: GAIA TANK_DOCKING → is_applicable=True (has_docking=True)"""
        if db_conn is None:
            pytest.skip("DB 연결 없음")
        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        sn, qr = 'SN-INT-GAIA-006', 'DOC-INT-GAIA-006'
        _cleanup(db_conn, sn, qr)
        _insert_product(db_conn, sn, qr, 'GAIA-I')
        try:
            _run_seed(sn, qr, 'GAIA-I')
            cursor = db_conn.cursor()
            cursor.execute("""
                SELECT is_applicable FROM app_task_details
                WHERE serial_number = %s AND task_id = 'TANK_DOCKING'
            """, (sn,))
            row = cursor.fetchone()
            cursor.close()
            assert row is not None, "GAIA TANK_DOCKING task 없음"
            assert row[0] is True, "GAIA TANK_DOCKING is_applicable=True 필요"
        finally:
            _cleanup(db_conn, sn, qr)


# ──────────────────────────────────────────────
# DRAGON 모델 Task Seed 검증
# ──────────────────────────────────────────────

class TestDRAGONTaskSeed:
    """
    DRAGON-V: tank_in_mech=True, is_tms=False, has_docking=False
    DB: pi_lng_util=True, pi_chamber=True → tank_in_mech extra = TANK_MODULE only (+1 MECH)
    예상: MECH 8행(7+1 TANK_MODULE) / active 6 (TANK_DOCKING=F, HEATING_JACKET=F)
          ELEC 6행, TMS 0행, PI 2행, QI 1행, SI 2행
    합계 19행 total
    """

    def test_dragon_total_rows(self, db_conn):
        """TC-SEED-DRAGON-01: DRAGON seed → 총 19행 (TMS 없음, MECH 8)"""
        if db_conn is None:
            pytest.skip("DB 연결 없음")
        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        sn, qr = 'SN-INT-DRAGON-001', 'DOC-INT-DRAGON-001'
        _cleanup(db_conn, sn, qr)
        _insert_product(db_conn, sn, qr, 'DRAGON-V')
        try:
            result = _run_seed(sn, qr, 'DRAGON-V')
            assert result.get('error') is None
            assert result.get('created') == 19, \
                f"DRAGON 총 19행 필요 (MECH8+ELEC6+PI2+QI1+SI2), got {result.get('created')}"
            assert result.get('categories', {}).get('TMS', 0) == 0, \
                "DRAGON TMS 0 필요"
        finally:
            _cleanup(db_conn, sn, qr)

    def test_dragon_tank_docking_not_applicable(self, db_conn):
        """TC-SEED-DRAGON-02: DRAGON TANK_DOCKING → is_applicable=False"""
        if db_conn is None:
            pytest.skip("DB 연결 없음")
        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        sn, qr = 'SN-INT-DRAGON-002', 'DOC-INT-DRAGON-002'
        _cleanup(db_conn, sn, qr)
        _insert_product(db_conn, sn, qr, 'DRAGON-V')
        try:
            _run_seed(sn, qr, 'DRAGON-V')
            cursor = db_conn.cursor()
            cursor.execute("""
                SELECT is_applicable FROM app_task_details
                WHERE serial_number = %s AND task_id = 'TANK_DOCKING'
            """, (sn,))
            row = cursor.fetchone()
            cursor.close()
            assert row is not None, "DRAGON TANK_DOCKING task 없음"
            assert row[0] is False, "DRAGON TANK_DOCKING is_applicable=False 필요"
        finally:
            _cleanup(db_conn, sn, qr)

    def test_dragon_mech_active_count(self, db_conn):
        """
        TC-SEED-DRAGON-03: DRAGON MECH active 6개
        MECH 8행 = 기본 7 + TANK_MODULE(tank_in_mech extra)
        active: WASTE_GAS_LINE_1, UTIL_LINE_1, WASTE_GAS_LINE_2, UTIL_LINE_2,
                SELF_INSPECTION, TANK_MODULE = 6개
        비활성: TANK_DOCKING=F, HEATING_JACKET=F
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")
        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        sn, qr = 'SN-INT-DRAGON-003', 'DOC-INT-DRAGON-003'
        _cleanup(db_conn, sn, qr)
        _insert_product(db_conn, sn, qr, 'DRAGON-V')
        _set_heating_jacket(db_conn, False)
        try:
            _run_seed(sn, qr, 'DRAGON-V')
            summary = _get_seed_summary(db_conn, sn)
            mech = summary.get('MECH', {})
            assert mech.get('total') == 8, f"DRAGON MECH 8행 필요 (7+TANK_MODULE), got {mech.get('total')}"
            assert mech.get('active') == 6, \
                f"DRAGON MECH active 6 필요, got {mech.get('active')}"
        finally:
            _cleanup(db_conn, sn, qr)
            _reset_heating_jacket(db_conn)

    def test_dragon_other_docking_tasks_applicable(self, db_conn):
        """
        TC-SEED-DRAGON-04: DRAGON WASTE_GAS_LINE_1/2, UTIL_LINE_1/2 → is_applicable=True
        (tank_in_mech=True이므로 TANK_DOCKING 빼고 나머지 docking 활성)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")
        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        sn, qr = 'SN-INT-DRAGON-004', 'DOC-INT-DRAGON-004'
        _cleanup(db_conn, sn, qr)
        _insert_product(db_conn, sn, qr, 'DRAGON-V')
        try:
            _run_seed(sn, qr, 'DRAGON-V')
            cursor = db_conn.cursor()
            cursor.execute("""
                SELECT task_id, is_applicable FROM app_task_details
                WHERE serial_number = %s
                  AND task_id IN ('WASTE_GAS_LINE_1','UTIL_LINE_1',
                                  'WASTE_GAS_LINE_2','UTIL_LINE_2')
            """, (sn,))
            rows = cursor.fetchall()
            cursor.close()
            assert len(rows) == 4, f"4개 docking task 필요, got {len(rows)}"
            for task_id, is_app in rows:
                assert is_app is True, \
                    f"DRAGON {task_id}은 is_applicable=True 필요"
        finally:
            _cleanup(db_conn, sn, qr)


# ──────────────────────────────────────────────
# GALLANT 모델 Task Seed 검증
# ──────────────────────────────────────────────

class TestGALLANTTaskSeed:
    """
    GALLANT-III: has_docking=False, tank_in_mech=True, is_tms=False
    DB: pi_lng_util=True, pi_chamber=False → tank_in_mech extra = TANK_MODULE only (+1 MECH)
    예상: MECH 8행(7+1 TANK_MODULE) / active 6 (HEATING_JACKET=F, TANK_DOCKING=F)
          tank_in_mech=True → WASTE_GAS_LINE_1, UTIL_LINE_1, WASTE_GAS_LINE_2, UTIL_LINE_2
                               SELF_INSPECTION, TANK_MODULE 모두 활성 (TANK_DOCKING만 비활성)
          ELEC 6행, TMS 0행, PI 2행, QI 1행, SI 2행
    합계 19행 total
    heating_jacket_enabled=false → MECH active 6
    heating_jacket_enabled=true  → MECH active 7 (+HEATING_JACKET)
    """

    def test_gallant_total_rows(self, db_conn):
        """TC-SEED-GALLANT-01: GALLANT seed → 총 19행 (MECH 8 + ELEC 6 + PI 2 + QI 1 + SI 2)"""
        if db_conn is None:
            pytest.skip("DB 연결 없음")
        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        sn, qr = 'SN-INT-GALLANT-001', 'DOC-INT-GALLANT-001'
        _cleanup(db_conn, sn, qr)
        _insert_product(db_conn, sn, qr, 'GALLANT-III')
        try:
            result = _run_seed(sn, qr, 'GALLANT-III')
            assert result.get('error') is None
            assert result.get('created') == 19, \
                f"GALLANT 총 19행 필요 (MECH8+ELEC6+PI2+QI1+SI2), got {result.get('created')}"
            assert result.get('categories', {}).get('TMS', 0) == 0
        finally:
            _cleanup(db_conn, sn, qr)

    def test_gallant_mech_active_6_hj_disabled(self, db_conn):
        """
        TC-SEED-GALLANT-02: GALLANT MECH active 6 (heating_jacket_enabled=false)
        tank_in_mech=True → WASTE_GAS_LINE_1, UTIL_LINE_1, WASTE_GAS_LINE_2, UTIL_LINE_2 활성
        + SELF_INSPECTION + TANK_MODULE = 6 active
        TANK_DOCKING=False, HEATING_JACKET=False
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")
        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        sn, qr = 'SN-INT-GALLANT-002', 'DOC-INT-GALLANT-002'
        _cleanup(db_conn, sn, qr)
        _insert_product(db_conn, sn, qr, 'GALLANT-III')
        _set_heating_jacket(db_conn, False)
        try:
            _run_seed(sn, qr, 'GALLANT-III')
            summary = _get_seed_summary(db_conn, sn)
            mech = summary.get('MECH', {})
            assert mech.get('total') == 8, f"GALLANT MECH 8행 필요 (7+TANK_MODULE), got {mech.get('total')}"
            assert mech.get('active') == 6, \
                f"GALLANT MECH active 6 (HJ disabled: 4 docking+SELF_INSPECTION+TANK_MODULE), got {mech.get('active')}"
        finally:
            _cleanup(db_conn, sn, qr)
            _reset_heating_jacket(db_conn)

    def test_gallant_mech_active_7_hj_enabled(self, db_conn):
        """
        TC-SEED-GALLANT-03: GALLANT MECH active 7 (heating_jacket_enabled=true)
        4 docking tasks + SELF_INSPECTION + TANK_MODULE + HEATING_JACKET = 7 active
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")
        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        sn, qr = 'SN-INT-GALLANT-003', 'DOC-INT-GALLANT-003'
        _cleanup(db_conn, sn, qr)
        _insert_product(db_conn, sn, qr, 'GALLANT-III')
        _set_heating_jacket(db_conn, True)
        try:
            _run_seed(sn, qr, 'GALLANT-III')
            summary = _get_seed_summary(db_conn, sn)
            mech = summary.get('MECH', {})
            assert mech.get('active') == 7, \
                f"GALLANT MECH active 7 (HJ enabled: 4 docking+SELF_INSPECTION+TANK_MODULE+HJ), got {mech.get('active')}"
            # HEATING_JACKET is_applicable=True 확인
            cursor = db_conn.cursor()
            cursor.execute("""
                SELECT is_applicable FROM app_task_details
                WHERE serial_number = %s AND task_id = 'HEATING_JACKET'
            """, (sn,))
            hj_row = cursor.fetchone()
            cursor.close()
            assert hj_row is not None and hj_row[0] is True, \
                "HJ enabled 시 HEATING_JACKET is_applicable=True 필요"
        finally:
            _cleanup(db_conn, sn, qr)
            _reset_heating_jacket(db_conn)

    def test_gallant_docking_tasks_applicable(self, db_conn):
        """
        TC-SEED-GALLANT-04: GALLANT docking 관련 Task 분기 확인
        has_docking=False, tank_in_mech=True →
          TANK_DOCKING: is_applicable=False (TANK_DOCKING만 비활성)
          WASTE_GAS_LINE_1, UTIL_LINE_1, WASTE_GAS_LINE_2, UTIL_LINE_2: is_applicable=True
            (tank_in_mech=True이므로 TANK_DOCKING 제외 나머지 docking tasks 활성)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")
        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        sn, qr = 'SN-INT-GALLANT-004', 'DOC-INT-GALLANT-004'
        _cleanup(db_conn, sn, qr)
        _insert_product(db_conn, sn, qr, 'GALLANT-III')
        try:
            _run_seed(sn, qr, 'GALLANT-III')
            cursor = db_conn.cursor()
            cursor.execute("""
                SELECT task_id, is_applicable FROM app_task_details
                WHERE serial_number = %s
                  AND task_id IN ('WASTE_GAS_LINE_1','UTIL_LINE_1','TANK_DOCKING',
                                  'WASTE_GAS_LINE_2','UTIL_LINE_2')
            """, (sn,))
            rows = cursor.fetchall()
            cursor.close()
            assert len(rows) == 5, f"5개 docking task 필요, got {len(rows)}"
            applicability = {task_id: is_app for task_id, is_app in rows}
            # TANK_DOCKING은 tank_in_mech=True여도 비활성
            assert applicability.get('TANK_DOCKING') is False, \
                "GALLANT TANK_DOCKING은 is_applicable=False 필요"
            # 나머지 4개 docking task는 tank_in_mech=True로 활성
            for tid in ['WASTE_GAS_LINE_1', 'UTIL_LINE_1', 'WASTE_GAS_LINE_2', 'UTIL_LINE_2']:
                assert applicability.get(tid) is True, \
                    f"GALLANT {tid}은 tank_in_mech=True → is_applicable=True 필요"
        finally:
            _cleanup(db_conn, sn, qr)


# ──────────────────────────────────────────────
# MITHAS / SDS / SWS (GALLANT 패턴)
# ──────────────────────────────────────────────

class TestOtherModelTaskSeed:
    """
    MITHAS/SDS: tank_in_mech=False → MECH 7행, active 1 (SELF_INSPECTION만)
    SWS: tank_in_mech=True, pi_lng_util=False, pi_chamber=True → MECH 8행(+TANK_MODULE),
         active 2 (SELF_INSPECTION + TANK_MODULE)

    DB model_config 기준:
    - MITHAS: tank_in_mech=F, pi_lng_util=T, pi_chamber=T → 총 18행
    - SDS:    tank_in_mech=F, pi_lng_util=T, pi_chamber=T → 총 18행
    - SWS:    tank_in_mech=T, pi_lng_util=F, pi_chamber=T → 총 19행 (MECH 8)
    """

    def test_mithas_total_rows(self, db_conn):
        """TC-SEED-MITHAS-01: MITHAS-II seed → 18행, TMS 없음 (MECH7+ELEC6+PI2+QI1+SI2)"""
        if db_conn is None:
            pytest.skip("DB 연결 없음")
        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        sn, qr = 'SN-INT-MITHAS-001', 'DOC-INT-MITHAS-001'
        _cleanup(db_conn, sn, qr)
        _insert_product(db_conn, sn, qr, 'MITHAS-II')
        try:
            result = _run_seed(sn, qr, 'MITHAS-II')
            assert result.get('error') is None
            assert result.get('created') == 18, \
                f"MITHAS 18행 필요 (MECH7+ELEC6+PI2+QI1+SI2), got {result.get('created')}"
            assert result.get('categories', {}).get('TMS', 0) == 0
        finally:
            _cleanup(db_conn, sn, qr)

    def test_sds_total_rows(self, db_conn):
        """TC-SEED-SDS-01: SDS-100 seed → 18행, TMS 없음 (MECH7+ELEC6+PI2+QI1+SI2)"""
        if db_conn is None:
            pytest.skip("DB 연결 없음")
        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        sn, qr = 'SN-INT-SDS-001', 'DOC-INT-SDS-001'
        _cleanup(db_conn, sn, qr)
        _insert_product(db_conn, sn, qr, 'SDS-100')
        try:
            result = _run_seed(sn, qr, 'SDS-100')
            assert result.get('error') is None
            assert result.get('created') == 18, \
                f"SDS 18행 필요 (MECH7+ELEC6+PI2+QI1+SI2), got {result.get('created')}"
        finally:
            _cleanup(db_conn, sn, qr)

    def test_sws_total_rows(self, db_conn):
        """TC-SEED-SWS-01: SWS-200 seed → 19행, TMS 없음 (MECH8+ELEC6+PI2+QI1+SI2)"""
        if db_conn is None:
            pytest.skip("DB 연결 없음")
        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        sn, qr = 'SN-INT-SWS-001', 'DOC-INT-SWS-001'
        _cleanup(db_conn, sn, qr)
        _insert_product(db_conn, sn, qr, 'SWS-200')
        try:
            result = _run_seed(sn, qr, 'SWS-200')
            assert result.get('error') is None
            assert result.get('created') == 19, \
                f"SWS 19행 필요 (MECH8+ELEC6+PI2+QI1+SI2, tank_in_mech TANK_MODULE), got {result.get('created')}"
        finally:
            _cleanup(db_conn, sn, qr)

    def test_mithas_sds_mech_self_inspection_only_active(self, db_conn):
        """
        TC-SEED-OTHER-01: MITHAS/SDS MECH → SELF_INSPECTION만 active
        tank_in_mech=F → docking 5개 비활성, HJ 비활성, SELF_INSPECTION만 활성
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")
        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        for model_name, sn_suffix in [('MITHAS-II', 'MITHAS'), ('SDS-100', 'SDS')]:
            sn = f'SN-INT-{sn_suffix}-SI'
            qr = f'DOC-INT-{sn_suffix}-SI'
            _insert_product(db_conn, sn, qr, model_name)
            try:
                _run_seed(sn, qr, model_name)
                cursor = db_conn.cursor()
                cursor.execute("""
                    SELECT task_id, is_applicable FROM app_task_details
                    WHERE serial_number = %s AND task_category = 'MECH'
                    ORDER BY task_id
                """, (sn,))
                rows = cursor.fetchall()
                cursor.close()

                applicable_tasks = sorted([r[0] for r in rows if r[1] is True])
                assert applicable_tasks == ['SELF_INSPECTION'], \
                    f"{model_name} MECH active task = SELF_INSPECTION만, got {applicable_tasks}"
            finally:
                _cleanup(db_conn, sn, qr)

    def test_sws_mech_active_includes_tank_module(self, db_conn):
        """
        TC-SEED-OTHER-02: SWS MECH → SELF_INSPECTION + TANK_MODULE active (tank_in_mech=True)
        SWS: tank_in_mech=True, pi_lng_util=False, pi_chamber=True → TANK_MODULE only extra
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")
        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        sn, qr = 'SN-INT-SWS-ACT', 'DOC-INT-SWS-ACT'
        _insert_product(db_conn, sn, qr, 'SWS-200')
        try:
            _run_seed(sn, qr, 'SWS-200')
            cursor = db_conn.cursor()
            cursor.execute("""
                SELECT task_id, is_applicable FROM app_task_details
                WHERE serial_number = %s AND task_category = 'MECH'
                ORDER BY task_id
            """, (sn,))
            rows = cursor.fetchall()
            cursor.close()

            applicable_tasks = sorted([r[0] for r in rows if r[1] is True])
            assert 'SELF_INSPECTION' in applicable_tasks, \
                f"SWS MECH: SELF_INSPECTION 활성 필요, got {applicable_tasks}"
            assert 'TANK_MODULE' in applicable_tasks, \
                f"SWS MECH: TANK_MODULE 활성 필요 (tank_in_mech=True), got {applicable_tasks}"
        finally:
            _cleanup(db_conn, sn, qr)


# ──────────────────────────────────────────────
# 6개 모델 동시 Seed 독립성 검증
# ──────────────────────────────────────────────

class TestAllModelsSimultaneousSeed:
    """
    6개 모델 동시 seed → 각각 독립적으로 정확한 수량 생성
    """

    # (model_name, serial_number, qr_doc_id, expected_total, expected_tms_count)
    # 실제 DB model_config 기준:
    # GAIA-I SINGLE: MECH7+ELEC6+TMS2+PI2+QI1+SI2 → 20행
    # DRAGON-V:    tank_in_mech=T, pi_lng_util=T → MECH8(+TANK_MODULE) → 19행
    # GALLANT-III: tank_in_mech=T, pi_lng_util=T, pi_chamber=F → MECH8 → 19행
    # MITHAS-II:   tank_in_mech=F → MECH7 → 18행
    # SDS-100:     tank_in_mech=F → MECH7 → 18행
    # SWS-200:     tank_in_mech=T, pi_lng_util=F, pi_chamber=T → MECH8 → 19행
    ALL_MODELS = [
        ('GAIA-I',  'SN-SIM-GAIA',    'DOC-SIM-GAIA',    20, 2),
        ('DRAGON-V',     'SN-SIM-DRAGON',  'DOC-SIM-DRAGON',  19, 0),
        ('GALLANT-III',  'SN-SIM-GALLANT', 'DOC-SIM-GALLANT', 19, 0),
        ('MITHAS-II',    'SN-SIM-MITHAS',  'DOC-SIM-MITHAS',  18, 0),
        ('SDS-100',      'SN-SIM-SDS',     'DOC-SIM-SDS',     18, 0),
        ('SWS-200',      'SN-SIM-SWS',     'DOC-SIM-SWS',     19, 0),
    ]

    def test_six_models_seeded_correctly(self, db_conn):
        """
        TC-SEED-SIM-01: 6개 모델 동시 seed → 각 모델 독립 정확 수량

        Expected (실제 DB model_config 기준, SI=2개):
        - GAIA-I: 20행 (MECH7+ELEC6+TMS2+PI2+QI1+SI2)
        - DRAGON-V:    19행 (MECH8+ELEC6+PI2+QI1+SI2)
        - GALLANT-III: 19행 (MECH8+ELEC6+PI2+QI1+SI2)
        - MITHAS-II:   18행 (MECH7+ELEC6+PI2+QI1+SI2)
        - SDS-100:     18행 (MECH7+ELEC6+PI2+QI1+SI2)
        - SWS-200:     19행 (MECH8+ELEC6+PI2+QI1+SI2)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")
        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        seeded = []
        # 이전 테스트 실행의 stale 데이터 선제 cleanup
        for _, sn, qr, _, _ in self.ALL_MODELS:
            _cleanup(db_conn, sn, qr)
        try:
            for model_name, sn, qr, expected_total, expected_tms in self.ALL_MODELS:
                _insert_product(db_conn, sn, qr, model_name)
                result = _run_seed(sn, qr, model_name)
                assert result.get('error') is None, \
                    f"{model_name} seed 에러: {result.get('error')}"
                assert result.get('created') == expected_total, \
                    f"{model_name} total {expected_total} 필요, got {result.get('created')}"
                assert result.get('categories', {}).get('TMS', 0) == expected_tms, \
                    f"{model_name} TMS {expected_tms} 필요"
                seeded.append((sn, qr))
        finally:
            for sn, qr in seeded:
                _cleanup(db_conn, sn, qr)

    def test_gaia_seed_does_not_affect_dragon(self, db_conn):
        """
        TC-SEED-SIM-02: GAIA seed 후 DRAGON seed → DRAGON에 TMS 없음

        Expected:
        - DRAGON serial_number에 TMS task = 0개
        - GAIA seed가 DRAGON serial에 영향 없음
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")
        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        sn_gaia, qr_gaia = 'SN-SIM-ISOL-GAIA', 'DOC-SIM-ISOL-GAIA'
        sn_dragon, qr_dragon = 'SN-SIM-ISOL-DRAGON', 'DOC-SIM-ISOL-DRAGON'
        _insert_product(db_conn, sn_gaia, qr_gaia, 'GAIA-I')
        _insert_product(db_conn, sn_dragon, qr_dragon, 'DRAGON-V')
        try:
            _run_seed(sn_gaia, qr_gaia, 'GAIA-I')
            _run_seed(sn_dragon, qr_dragon, 'DRAGON-V')

            cursor = db_conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM app_task_details
                WHERE serial_number = %s AND task_category = 'TMS'
            """, (sn_dragon,))
            dragon_tms = cursor.fetchone()[0]
            cursor.close()

            assert dragon_tms == 0, \
                f"DRAGON에 TMS task 0 필요, got {dragon_tms}"
        finally:
            _cleanup(db_conn, sn_gaia, qr_gaia)
            _cleanup(db_conn, sn_dragon, qr_dragon)
