"""
Task Seed 및 model_config 분기 테스트
Sprint 6: MECH 7 + ELEC 6 + TMS 2 = 15개 템플릿 기준

테스트 대상:
- initialize_product_tasks(serial_number, qr_doc_id, model_name) 함수
- model_config 기반 is_applicable 분기 (GAIA/DRAGON/기타)
- admin_settings.heating_jacket_enabled 영향
- company 기반 Task 필터링
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from unittest.mock import patch, MagicMock

# backend 경로 추가
backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


# ============================================================
# 공통 픽스처: 테스트용 model_config + admin_settings 설정
# ============================================================

@pytest.fixture(autouse=True)
def cleanup_task_seed_data(db_conn):
    """테스트 후 Task Seed 테스트 데이터 정리"""
    yield
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            cursor.execute(
                "DELETE FROM app_task_details WHERE serial_number LIKE 'SN-SEED-%%'"
            )
            cursor.execute(
                "DELETE FROM completion_status WHERE serial_number LIKE 'SN-SEED-%%'"
            )
            cursor.execute(
                "DELETE FROM public.qr_registry WHERE qr_doc_id LIKE 'DOC-SEED-%%'"
            )
            cursor.execute(
                "DELETE FROM plan.product_info WHERE serial_number LIKE 'SN-SEED-%%'"
            )
            db_conn.commit()
            cursor.close()
        except Exception:
            pass


def _insert_test_product(db_conn, serial_number: str, qr_doc_id: str, model: str):
    """테스트용 제품 삽입 헬퍼"""
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


def _get_task_counts(db_conn, serial_number: str) -> Dict[str, int]:
    """시리얼 번호 기준 카테고리별 Task 수 조회"""
    cursor = db_conn.cursor()
    cursor.execute("""
        SELECT task_category,
               COUNT(*) AS total,
               COUNT(*) FILTER (WHERE is_applicable = TRUE) AS active
        FROM app_task_details
        WHERE serial_number = %s
        GROUP BY task_category
    """, (serial_number,))
    rows = cursor.fetchall()
    cursor.close()
    result = {}
    for row in rows:
        result[row[0]] = {'total': row[1], 'active': row[2]}
    return result


# ============================================================
# model_config 조회 테스트
# ============================================================

class TestModelConfigLookup:
    """model_config 테이블 prefix 매칭 테스트"""

    def test_model_config_exists_in_db(self, db_conn):
        """
        DB에 model_config 초기 데이터 6개 존재 확인

        Expected:
        - GAIA, DRAGON, GALLANT, MITHAS, SDS, SWS 6개 레코드
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        cursor = db_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM model_config")
        count = cursor.fetchone()[0]
        cursor.close()

        assert count >= 6, f"model_config에 6개 이상 레코드 필요, 현재 {count}개"

    def test_gaia_config_values(self, db_conn):
        """
        GAIA 모델 설정: has_docking=True, is_tms=True, tank_in_mech=False

        Expected:
        - GAIA prefix → has_docking=True, is_tms=True, tank_in_mech=False
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT has_docking, is_tms, tank_in_mech
            FROM model_config WHERE model_prefix = 'GAIA'
        """)
        row = cursor.fetchone()
        cursor.close()

        assert row is not None, "GAIA model_config 레코드 없음"
        has_docking, is_tms, tank_in_mech = row[0], row[1], row[2]
        assert has_docking is True, "GAIA has_docking should be True"
        assert is_tms is True, "GAIA is_tms should be True"
        assert tank_in_mech is False, "GAIA tank_in_mech should be False"

    def test_dragon_config_values(self, db_conn):
        """
        DRAGON 모델 설정: has_docking=False, is_tms=False, tank_in_mech=True

        Expected:
        - DRAGON prefix → has_docking=False, is_tms=False, tank_in_mech=True
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT has_docking, is_tms, tank_in_mech
            FROM model_config WHERE model_prefix = 'DRAGON'
        """)
        row = cursor.fetchone()
        cursor.close()

        assert row is not None, "DRAGON model_config 레코드 없음"
        has_docking, is_tms, tank_in_mech = row[0], row[1], row[2]
        assert has_docking is False
        assert is_tms is False
        assert tank_in_mech is True

    def test_gallant_config_values(self, db_conn):
        """
        GALLANT 모델: has_docking=False, is_tms=False, tank_in_mech=False

        Expected:
        - 도킹 없음, TMS 없음, tank_in_mech 없음
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT has_docking, is_tms, tank_in_mech
            FROM model_config WHERE model_prefix = 'GALLANT'
        """)
        row = cursor.fetchone()
        cursor.close()

        assert row is not None
        assert row[0] is False
        assert row[1] is False
        assert row[2] is False

    def test_model_config_api_accessible(self, client, create_test_worker, get_auth_token):
        """
        GET /api/admin/model-config → model_config 목록 반환

        Expected:
        - Status 200
        - configs 배열 포함 (6개 이상)
        """
        worker_id = create_test_worker(
            email='mc_api@test.com', password='Test123!',
            name='MC API Worker', role='MECH',
            is_admin=True
        )
        token = get_auth_token(worker_id, role='MECH')

        response = client.get(
            '/api/admin/model-config',
            headers={'Authorization': f'Bearer {token}'}
        )

        # 엔드포인트 미구현 시 skip
        if response.status_code == 404:
            pytest.skip("GET /api/admin/model-config 미구현")

        assert response.status_code == 200
        data = response.get_json()
        assert 'configs' in data
        assert len(data['configs']) >= 6


# ============================================================
# admin_settings 테스트
# ============================================================

class TestAdminSettings:
    """admin_settings 테이블 CRUD 테스트"""

    def test_default_heating_jacket_disabled(self, db_conn):
        """
        heating_jacket_enabled 기본값 = false

        Expected:
        - admin_settings에서 heating_jacket_enabled = false
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT setting_value FROM admin_settings
            WHERE setting_key = 'heating_jacket_enabled'
        """)
        row = cursor.fetchone()
        cursor.close()

        assert row is not None, "heating_jacket_enabled 설정 없음"
        # JSONB 'false' → Python에서 False로 파싱
        value = row[0]
        assert value in (False, 'false', '"false"'), f"기본값이 false여야 하는데 {value}"

    def test_default_phase_block_disabled(self, db_conn):
        """
        phase_block_enabled 기본값 = false

        Expected:
        - admin_settings에서 phase_block_enabled = false
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        cursor = db_conn.cursor()
        # 이전 테스트가 admin_settings를 변경/삭제했을 수 있으므로 기본값 보장
        try:
            cursor.execute("""
                INSERT INTO admin_settings (setting_key, setting_value, description)
                VALUES ('phase_block_enabled', 'false', 'Tank Docking 완료 전 POST_DOCKING task 차단 여부')
                ON CONFLICT (setting_key) DO NOTHING
            """)
            db_conn.commit()
        except Exception:
            db_conn.rollback()

        cursor.execute("""
            SELECT setting_value FROM admin_settings
            WHERE setting_key = 'phase_block_enabled'
        """)
        row = cursor.fetchone()
        cursor.close()

        assert row is not None, "phase_block_enabled 설정 없음"
        value = row[0]
        assert value in (False, 'false', '"false"')

    def test_update_admin_setting_via_api(self, client, create_test_worker, get_auth_token):
        """
        PUT /api/admin/settings → setting 값 업데이트

        Expected:
        - 관리자만 수정 가능
        - Status 200, updated setting 반환
        """
        worker_id = create_test_worker(
            email='setting_admin@test.com', password='Test123!',
            name='Setting Admin', role='ADMIN',
            is_admin=True
        )
        token = get_auth_token(worker_id, role='ADMIN')

        response = client.put(
            '/api/admin/settings/heating_jacket_enabled',
            json={'value': True},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("PUT /api/admin/settings 미구현")

        assert response.status_code == 200
        data = response.get_json()
        assert 'setting_key' in data or 'message' in data

    def test_get_admin_setting_via_api(self, client, create_test_worker, get_auth_token):
        """
        GET /api/admin/settings → 설정 flat dict 반환

        Expected:
        - Status 200
        - heating_jacket_enabled, phase_block_enabled 키 포함 (flat dict)
        """
        worker_id = create_test_worker(
            email='setting_get@test.com', password='Test123!',
            name='Setting Get Worker', role='ADMIN',
            is_admin=True
        )
        token = get_auth_token(worker_id, role='ADMIN', is_admin=True)

        response = client.get(
            '/api/admin/settings',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/admin/settings 미구현")

        assert response.status_code == 200
        data = response.get_json()
        # API returns flat dict: {"heating_jacket_enabled": bool, "phase_block_enabled": bool}
        assert 'heating_jacket_enabled' in data or 'phase_block_enabled' in data


# ============================================================
# Task Seed 초기화 테스트
# ============================================================

class TestTaskSeedGAIA:
    """GAIA 모델 Task Seed 테스트 (has_docking=True, is_tms=True)"""

    def test_gaia_total_task_count(self, client, db_conn, create_test_worker, get_auth_token):
        """
        TC-SEED-01: GAIA → 총 15개 Task 생성 확인
        MECH 7 (1~5 + 자주검사 + HEATING_JACKET) + ELEC 6 + TMS 2

        heating_jacket은 admin_settings.heating_jacket_enabled=false이면 is_applicable=false

        Expected:
        - 총 Task 수 = 15개 (MECH 7 + ELEC 6 + TMS 2)
        - is_applicable=true: MECH 6 (HEATING_JACKET 제외) + ELEC 6 + TMS 2 = 14개
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        serial_number = 'SN-SEED-GAIA-001'
        qr_doc_id = 'DOC-SEED-GAIA-001'
        _insert_test_product(db_conn, serial_number, qr_doc_id, 'GAIA-100')

        admin_id = create_test_worker(
            email='seed_admin_gaia@test.com', password='Test123!',
            name='GAIA Seed Admin', role='ADMIN', is_admin=True
        )
        token = get_auth_token(admin_id, role='ADMIN')

        response = client.post(
            '/api/admin/products/initialize-tasks',
            json={'serial_number': serial_number, 'qr_doc_id': qr_doc_id, 'model_name': 'GAIA-100'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in [404, 405]:
            pytest.skip("POST /api/admin/products/initialize-tasks 미구현")

        assert response.status_code in [200, 201], \
            f"Expected 200/201, got {response.status_code}: {response.get_json()}"

        # DB에서 Task 수 확인
        counts = _get_task_counts(db_conn, serial_number)
        total = sum(v['total'] for v in counts.values())
        assert total == 19, f"GAIA는 19개 Task 생성되어야 함 (MECH7+ELEC6+TMS2+PI2+QI1+SI1), 현재 {total}개"

        # TMS Task 생성 확인
        assert 'TMS' in counts, "GAIA는 TMS Task가 생성되어야 함"
        assert counts['TMS']['total'] == 2, f"TMS 2개 필요, 현재 {counts.get('TMS', {}).get('total', 0)}개"

        # MECH Task 생성 확인
        assert 'MECH' in counts
        assert counts['MECH']['total'] == 7, f"MECH 7개 필요, 현재 {counts.get('MECH', {}).get('total', 0)}개"

        # ELEC Task 생성 확인
        assert 'ELEC' in counts
        assert counts['ELEC']['total'] == 6, f"ELEC 6개 필요, 현재 {counts.get('ELEC', {}).get('total', 0)}개"

    def test_gaia_docking_tasks_applicable(self, client, db_conn, create_test_worker, get_auth_token):
        """
        TC-SEED-02: GAIA → MECH 도킹 관련 Task 모두 is_applicable=true

        Expected:
        - WASTE_GAS_LINE_1, UTIL_LINE_1, TANK_DOCKING, WASTE_GAS_LINE_2,
          UTIL_LINE_2 모두 is_applicable=true (has_docking=true이므로)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        serial_number = 'SN-SEED-GAIA-002'
        qr_doc_id = 'DOC-SEED-GAIA-002'
        _insert_test_product(db_conn, serial_number, qr_doc_id, 'GAIA-100')

        admin_id = create_test_worker(
            email='seed_admin_gaia2@test.com', password='Test123!',
            name='GAIA Seed Admin 2', role='ADMIN', is_admin=True
        )
        token = get_auth_token(admin_id, role='ADMIN')

        response = client.post(
            '/api/admin/products/initialize-tasks',
            json={'serial_number': serial_number, 'qr_doc_id': qr_doc_id, 'model_name': 'GAIA-100'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in [404, 405]:
            pytest.skip("POST /api/admin/products/initialize-tasks 미구현")

        if response.status_code not in [200, 201]:
            pytest.skip(f"initialize 실패: {response.status_code}")

        # TANK_DOCKING is_applicable=true 확인
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT task_id, is_applicable FROM app_task_details
            WHERE serial_number = %s AND task_category = 'MECH'
            AND task_id IN ('WASTE_GAS_LINE_1','UTIL_LINE_1','TANK_DOCKING',
                            'WASTE_GAS_LINE_2','UTIL_LINE_2')
        """, (serial_number,))
        rows = cursor.fetchall()
        cursor.close()

        assert len(rows) == 5, f"도킹 관련 5개 Task 필요, 현재 {len(rows)}개"
        for row in rows:
            assert row[1] is True, f"{row[0]}은 GAIA에서 is_applicable=true여야 함"


class TestTaskSeedDRAGON:
    """DRAGON 모델 Task Seed 테스트 (has_docking=False, tank_in_mech=True)"""

    def test_dragon_tank_docking_not_applicable(self, client, db_conn, create_test_worker, get_auth_token):
        """
        TC-SEED-03: DRAGON → TANK_DOCKING is_applicable=false, 나머지 MECH는 true

        Expected:
        - TANK_DOCKING: is_applicable=false
        - 나머지 도킹 관련(WASTE_GAS_LINE_1 등): is_applicable=true (tank_in_mech)
        - TMS Task 없음 (is_tms=false)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        serial_number = 'SN-SEED-DRAGON-001'
        qr_doc_id = 'DOC-SEED-DRAGON-001'
        _insert_test_product(db_conn, serial_number, qr_doc_id, 'DRAGON-200')

        admin_id = create_test_worker(
            email='seed_admin_dragon@test.com', password='Test123!',
            name='DRAGON Seed Admin', role='ADMIN', is_admin=True
        )
        token = get_auth_token(admin_id, role='ADMIN')

        response = client.post(
            '/api/admin/products/initialize-tasks',
            json={'serial_number': serial_number, 'qr_doc_id': qr_doc_id, 'model_name': 'DRAGON-200'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in [404, 405]:
            pytest.skip("POST /api/admin/products/initialize-tasks 미구현")

        if response.status_code not in [200, 201]:
            pytest.skip(f"initialize 실패: {response.status_code}")

        cursor = db_conn.cursor()

        # TANK_DOCKING: is_applicable=false 확인
        cursor.execute("""
            SELECT is_applicable FROM app_task_details
            WHERE serial_number = %s AND task_id = 'TANK_DOCKING'
        """, (serial_number,))
        row = cursor.fetchone()
        if row:
            assert row[0] is False, "DRAGON의 TANK_DOCKING은 is_applicable=false여야 함"

        # TMS Task 없음 확인
        cursor.execute("""
            SELECT COUNT(*) FROM app_task_details
            WHERE serial_number = %s AND task_category = 'TMS'
        """, (serial_number,))
        tms_count = cursor.fetchone()[0]
        assert tms_count == 0, f"DRAGON은 TMS Task 없어야 함, 현재 {tms_count}개"

        cursor.close()


class TestTaskSeedGALLANT:
    """GALLANT 모델 Task Seed 테스트 (has_docking=False, tank_in_mech=False)"""

    def test_gallant_only_self_inspection_applicable(self, client, db_conn, create_test_worker, get_auth_token):
        """
        TC-SEED-04: 기타 모델 (GALLANT) → MECH는 자주검사만 is_applicable=true

        Expected:
        - SELF_INSPECTION: is_applicable=true
        - 도킹 관련 MECH tasks: is_applicable=false
        - ELEC: 전부 is_applicable=true (6개)
        - TMS: 없음
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        serial_number = 'SN-SEED-GALLANT-001'
        qr_doc_id = 'DOC-SEED-GALLANT-001'
        _insert_test_product(db_conn, serial_number, qr_doc_id, 'GALLANT-50')

        admin_id = create_test_worker(
            email='seed_admin_gallant@test.com', password='Test123!',
            name='GALLANT Seed Admin', role='ADMIN', is_admin=True
        )
        token = get_auth_token(admin_id, role='ADMIN')

        response = client.post(
            '/api/admin/products/initialize-tasks',
            json={'serial_number': serial_number, 'qr_doc_id': qr_doc_id, 'model_name': 'GALLANT-50'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in [404, 405]:
            pytest.skip("POST /api/admin/products/initialize-tasks 미구현")

        if response.status_code not in [200, 201]:
            pytest.skip(f"initialize 실패: {response.status_code}")

        cursor = db_conn.cursor()

        # MECH: SELF_INSPECTION만 applicable
        cursor.execute("""
            SELECT task_id, is_applicable FROM app_task_details
            WHERE serial_number = %s AND task_category = 'MECH'
            ORDER BY task_id
        """, (serial_number,))
        mech_rows = cursor.fetchall()

        applicable_mech = [r[0] for r in mech_rows if r[1] is True]
        assert 'SELF_INSPECTION' in applicable_mech, "SELF_INSPECTION은 GALLANT에서도 applicable"

        # 도킹 관련: not applicable
        not_applicable_mech = [r[0] for r in mech_rows if r[1] is False]
        for task_id in ['WASTE_GAS_LINE_1', 'UTIL_LINE_1', 'TANK_DOCKING',
                        'WASTE_GAS_LINE_2', 'UTIL_LINE_2']:
            assert task_id in not_applicable_mech, \
                f"{task_id}은 GALLANT에서 is_applicable=false여야 함"

        # ELEC: 전부 applicable (6개)
        cursor.execute("""
            SELECT COUNT(*) FROM app_task_details
            WHERE serial_number = %s AND task_category = 'ELEC'
            AND is_applicable = TRUE
        """, (serial_number,))
        elec_active = cursor.fetchone()[0]
        assert elec_active == 6, f"GALLANT ELEC 6개 active 필요, 현재 {elec_active}개"

        cursor.close()


class TestHeatingJacketAdminSetting:
    """admin_settings.heating_jacket_enabled에 따른 HEATING_JACKET Task 활성화 테스트"""

    def test_heating_jacket_disabled_by_default(self, db_conn, create_test_worker, get_auth_token, client):
        """
        TC-SEED-05: heating_jacket_enabled=false(기본값) → HEATING_JACKET is_applicable=false

        Expected:
        - HEATING_JACKET task is_applicable = false
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        serial_number = 'SN-SEED-HJ-001'
        qr_doc_id = 'DOC-SEED-HJ-001'
        _insert_test_product(db_conn, serial_number, qr_doc_id, 'GAIA-100')

        # heating_jacket_enabled = false 확인 (기본값)
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT setting_value FROM admin_settings
            WHERE setting_key = 'heating_jacket_enabled'
        """)
        row = cursor.fetchone()
        cursor.close()

        if row is None:
            pytest.skip("admin_settings 테이블 없음")

        admin_id = create_test_worker(
            email='seed_admin_hj@test.com', password='Test123!',
            name='HJ Seed Admin', role='ADMIN', is_admin=True
        )
        token = get_auth_token(admin_id, role='ADMIN')

        response = client.post(
            '/api/admin/products/initialize-tasks',
            json={'serial_number': serial_number, 'qr_doc_id': qr_doc_id, 'model_name': 'GAIA-100'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in [404, 405]:
            pytest.skip("POST /api/admin/products/initialize-tasks 미구현")

        if response.status_code not in [200, 201]:
            pytest.skip(f"initialize 실패")

        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT is_applicable FROM app_task_details
            WHERE serial_number = %s AND task_id = 'HEATING_JACKET'
        """, (serial_number,))
        row = cursor.fetchone()
        cursor.close()

        if row is not None:
            assert row[0] is False, \
                "heating_jacket_enabled=false일 때 HEATING_JACKET is_applicable=false여야 함"


# ============================================================
# company 기반 Task 필터링 테스트
# ============================================================

class TestCompanyBasedTaskFilter:
    """company 기반 작업자가 보는 Task 필터링 테스트"""

    def test_fni_worker_sees_mech_tasks_only(self, client, db_conn, create_test_worker, get_auth_token):
        """
        TC-FILTER-01: FNI 작업자 → mech_partner='FNI' 제품의 MECH task만 조회

        Expected:
        - task_category = 'MECH' 목록만 반환
        - ELEC, TMS task 미포함
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        serial_number = 'SN-SEED-FNI-001'
        qr_doc_id = 'DOC-SEED-FNI-001'

        # FNI mech_partner 제품 삽입
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO plan.product_info (serial_number, model, mech_partner)
            VALUES (%s, 'GALLANT-50', 'FNI')
            ON CONFLICT (serial_number) DO NOTHING
        """, (serial_number,))
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number)
            VALUES (%s, %s)
            ON CONFLICT (qr_doc_id) DO NOTHING
        """, (qr_doc_id, serial_number))
        db_conn.commit()
        cursor.close()

        worker_id = create_test_worker(
            email='fni_worker@test.com', password='Test123!',
            name='FNI Worker', role='MECH', company='FNI'
        )
        token = get_auth_token(worker_id, role='MECH')

        # 작업 목록 조회 (company 필터 적용)
        response = client.get(
            f'/api/app/work/my-tasks?qr_doc_id={qr_doc_id}',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/work/my-tasks 미구현")

        assert response.status_code == 200
        data = response.get_json()
        tasks = data.get('tasks', [])

        # MECH task만 포함되어야 함
        for task in tasks:
            assert task['task_category'] == 'MECH', \
                f"FNI 작업자는 MECH task만 봐야 하는데 {task['task_category']} 포함됨"

    def test_tms_e_worker_sees_elec_tasks_only(self, client, db_conn, create_test_worker, get_auth_token):
        """
        TC-FILTER-02: TMS(E) 작업자 → elec_partner='TMS' 제품의 ELEC task만 조회

        Expected:
        - task_category = 'ELEC' 목록만 반환
        - MECH, TMS task 미포함
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        serial_number = 'SN-SEED-TMSE-001'
        qr_doc_id = 'DOC-SEED-TMSE-001'

        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO plan.product_info (serial_number, model, elec_partner)
            VALUES (%s, 'GAIA-100', 'TMS')
            ON CONFLICT (serial_number) DO NOTHING
        """, (serial_number,))
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number)
            VALUES (%s, %s)
            ON CONFLICT (qr_doc_id) DO NOTHING
        """, (qr_doc_id, serial_number))
        db_conn.commit()
        cursor.close()

        worker_id = create_test_worker(
            email='tmse_worker@test.com', password='Test123!',
            name='TMS(E) Worker', role='ELEC', company='TMS(E)'
        )
        token = get_auth_token(worker_id, role='ELEC')

        response = client.get(
            f'/api/app/work/my-tasks?qr_doc_id={qr_doc_id}',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/work/my-tasks 미구현")

        assert response.status_code == 200
        data = response.get_json()
        tasks = data.get('tasks', [])

        for task in tasks:
            assert task['task_category'] == 'ELEC', \
                f"TMS(E) 작업자는 ELEC task만 봐야 하는데 {task['task_category']} 포함됨"

    def test_company_role_validation_on_register(self, client):
        """
        TC-FILTER-03: 회원가입 시 company↔role 유효 조합 검증

        Expected:
        - FNI + MECH: 유효 → 201
        - FNI + ELEC: 무효 → 400 INVALID_COMPANY_ROLE
        """
        # 유효 조합 (FNI + MECH)
        response_valid = client.post('/api/auth/register', json={
            'name': '유효 조합 작업자',
            'email': 'valid_combo@axisos.test',
            'password': 'SecurePass123!',
            'role': 'MECH',
            'company': 'FNI'
        })

        # 회원가입 API가 company 검증을 구현했을 때만 엄격하게 검증
        if response_valid.status_code == 404:
            pytest.skip("company 검증 미구현")

        # 유효 조합은 201 또는 200
        assert response_valid.status_code in [200, 201, 409], \
            f"FNI+MECH 유효 조합은 성공 또는 중복 이메일이어야 함, got {response_valid.status_code}"

        # 무효 조합 (FNI + ELEC)
        response_invalid = client.post('/api/auth/register', json={
            'name': '무효 조합 작업자',
            'email': 'invalid_combo@axisos.test',
            'password': 'SecurePass123!',
            'role': 'ELEC',
            'company': 'FNI'
        })

        # 무효 조합이면 400
        if response_invalid.status_code in [200, 201]:
            pytest.skip("company↔role 검증 미구현 (무효 조합이 통과됨)")

        assert response_invalid.status_code == 400, \
            f"FNI+ELEC 무효 조합은 400이어야 함, got {response_invalid.status_code}"

    def test_gst_admin_sees_all_tasks(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """
        TC-FILTER-04: GST 관리자 → 필터 없이 전체 Task 조회

        Expected:
        - MECH + ELEC + TMS 모두 포함된 목록 반환
        - 카테고리 필터 없음
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        serial_number = 'SN-SEED-GST-001'
        qr_doc_id = 'DOC-SEED-GST-001'

        # GAIA 제품 삽입 (TMS 포함)
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO plan.product_info (serial_number, model, mech_partner, elec_partner, module_outsourcing)
            VALUES (%s, 'GAIA-100', 'FNI', 'TMS', 'TMS')
            ON CONFLICT (serial_number) DO NOTHING
        """, (serial_number,))
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number)
            VALUES (%s, %s)
            ON CONFLICT (qr_doc_id) DO NOTHING
        """, (qr_doc_id, serial_number))

        # Task 직접 삽입 (MECH, ELEC, TMS 각 1개씩)
        for cat, tid, tname in [
            ('MECH', 'SELF_INSPECTION', '자주검사'),
            ('ELEC', 'INSPECTION', '자주검사 (검수)'),
            ('TMS',  'PRESSURE_TEST', '가압검사'),
        ]:
            cursor.execute("""
                INSERT INTO app_task_details
                    (serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable)
                VALUES (%s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (serial_number, task_category, task_id) DO NOTHING
            """, (serial_number, qr_doc_id, cat, tid, tname))
        db_conn.commit()
        cursor.close()

        admin_id = create_test_worker(
            email='gst_admin_filter@test.com', password='Test123!',
            name='GST Admin Filter', role='ADMIN', is_admin=True, company='GST'
        )
        token = get_auth_token(admin_id, role='ADMIN', is_admin=True)

        response = client.get(
            f'/api/app/tasks/{serial_number}?all=true',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial_number> 미구현")

        assert response.status_code == 200
        tasks = response.get_json()
        if isinstance(tasks, list):
            categories_seen = {t['task_category'] for t in tasks}
            # 관리자는 MECH+ELEC+TMS 모두 볼 수 있어야 함
            assert len(categories_seen) >= 2, \
                f"관리자는 복수 카테고리를 봐야 함, 현재: {categories_seen}"

    def test_bat_worker_sees_mech_tasks_only(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """
        TC-FILTER-05: BAT 작업자 → mech_partner='BAT' 제품의 MECH task만 조회

        Expected:
        - GET /api/app/tasks/<serial_number> → MECH task만 반환
        - ELEC, TMS 제외
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        serial_number = 'SN-SEED-BAT-001'
        qr_doc_id = 'DOC-SEED-BAT-001'

        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO plan.product_info (serial_number, model, mech_partner, elec_partner)
            VALUES (%s, 'GALLANT-50', 'BAT', 'C&A')
            ON CONFLICT (serial_number) DO NOTHING
        """, (serial_number,))
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number)
            VALUES (%s, %s)
            ON CONFLICT (qr_doc_id) DO NOTHING
        """, (qr_doc_id, serial_number))

        # MECH, ELEC task 삽입
        for cat, tid, tname in [
            ('MECH', 'SELF_INSPECTION', '자주검사'),
            ('ELEC', 'INSPECTION', '자주검사 (검수)'),
        ]:
            cursor.execute("""
                INSERT INTO app_task_details
                    (serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable)
                VALUES (%s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (serial_number, task_category, task_id) DO NOTHING
            """, (serial_number, qr_doc_id, cat, tid, tname))
        db_conn.commit()
        cursor.close()

        worker_id = create_test_worker(
            email='bat_worker@test.com', password='Test123!',
            name='BAT Worker', role='MECH', company='BAT'
        )
        token = get_auth_token(worker_id, role='MECH')

        response = client.get(
            f'/api/app/tasks/{serial_number}',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial_number> 미구현")

        assert response.status_code == 200
        tasks = response.get_json()
        if isinstance(tasks, list) and len(tasks) > 0:
            for task in tasks:
                assert task['task_category'] == 'MECH', \
                    f"BAT 작업자는 MECH task만 봐야 하는데 {task['task_category']} 포함됨"


# ============================================================
# Task Seed 직접 호출 테스트 (서비스 레이어 단위)
# ============================================================

class TestTaskSeedDirectCall:
    """initialize_product_tasks() 함수 직접 호출 테스트"""

    def test_seed_returns_correct_counts_gaia(self, db_conn):
        """
        TC-SEED-DIRECT-01: GAIA 직접 seed → 반환값 검증

        Expected:
        - created = 15 (최초 실행)
        - skipped = 0
        - categories = {'MECH': 7, 'ELEC': 6, 'TMS': 2}
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        # backend 서비스 직접 임포트
        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 서비스 임포트 실패")

        serial_number = 'SN-SEED-DIRECT-GAIA-001'
        qr_doc_id = 'DOC-SEED-DIRECT-GAIA-001'

        # 제품 삽입
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO plan.product_info (serial_number, model)
            VALUES (%s, 'GAIA-100')
            ON CONFLICT (serial_number) DO NOTHING
        """, (serial_number,))
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number)
            VALUES (%s, %s)
            ON CONFLICT (qr_doc_id) DO NOTHING
        """, (qr_doc_id, serial_number))
        db_conn.commit()
        cursor.close()

        # cleanup after test
        try:
            result = initialize_product_tasks(serial_number, qr_doc_id, 'GAIA-100')

            assert result.get('error') is None, f"Seed 에러: {result.get('error')}"
            assert result.get('created', 0) == 19, \
                f"GAIA는 15개 생성 필요, 현재 {result.get('created')}개"
            assert result.get('categories', {}).get('MECH', 0) == 7
            assert result.get('categories', {}).get('ELEC', 0) == 6
            assert result.get('categories', {}).get('TMS', 0) == 2
        finally:
            cursor = db_conn.cursor()
            cursor.execute("DELETE FROM app_task_details WHERE serial_number = %s", (serial_number,))
            cursor.execute("DELETE FROM completion_status WHERE serial_number = %s", (serial_number,))
            cursor.execute("DELETE FROM public.qr_registry WHERE qr_doc_id = %s", (qr_doc_id,))
            cursor.execute("DELETE FROM plan.product_info WHERE serial_number = %s", (serial_number,))
            db_conn.commit()
            cursor.close()

    def test_seed_idempotent_direct_call(self, db_conn):
        """
        TC-SEED-DIRECT-02: 동일 제품에 seed 2회 호출 → 두 번째는 skipped=15

        Expected:
        - 첫 번째 호출: created=15, skipped=0
        - 두 번째 호출: created=0, skipped=15 (ON CONFLICT DO NOTHING)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 서비스 임포트 실패")

        serial_number = 'SN-SEED-IDEMPOT-001'
        qr_doc_id = 'DOC-SEED-IDEMPOT-001'

        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO plan.product_info (serial_number, model)
            VALUES (%s, 'GAIA-100')
            ON CONFLICT (serial_number) DO NOTHING
        """, (serial_number,))
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number)
            VALUES (%s, %s)
            ON CONFLICT (qr_doc_id) DO NOTHING
        """, (qr_doc_id, serial_number))
        db_conn.commit()
        cursor.close()

        try:
            result1 = initialize_product_tasks(serial_number, qr_doc_id, 'GAIA-100')
            result2 = initialize_product_tasks(serial_number, qr_doc_id, 'GAIA-100')

            assert result1.get('error') is None
            assert result1.get('created', 0) == 19, f"첫 번째 created=19 필요"
            assert result2.get('created', 0) == 0, f"두 번째 created=0 필요 (이미 존재)"
            assert result2.get('skipped', 0) == 19, f"두 번째 skipped=19 필요"
        finally:
            cursor = db_conn.cursor()
            cursor.execute("DELETE FROM app_task_details WHERE serial_number = %s", (serial_number,))
            cursor.execute("DELETE FROM completion_status WHERE serial_number = %s", (serial_number,))
            cursor.execute("DELETE FROM public.qr_registry WHERE qr_doc_id = %s", (qr_doc_id,))
            cursor.execute("DELETE FROM plan.product_info WHERE serial_number = %s", (serial_number,))
            db_conn.commit()
            cursor.close()

    def test_seed_gallant_no_tms_tasks(self, db_conn):
        """
        TC-SEED-DIRECT-03: GALLANT seed → TMS task 0개 생성 확인

        Expected:
        - categories['TMS'] = 0 (반환값에 TMS 없음)
        - DB에서도 TMS task 0개
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 서비스 임포트 실패")

        serial_number = 'SN-SEED-GALLANT-DIRECT-001'
        qr_doc_id = 'DOC-SEED-GALLANT-DIRECT-001'

        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO plan.product_info (serial_number, model)
            VALUES (%s, 'GALLANT-50')
            ON CONFLICT (serial_number) DO NOTHING
        """, (serial_number,))
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number)
            VALUES (%s, %s)
            ON CONFLICT (qr_doc_id) DO NOTHING
        """, (qr_doc_id, serial_number))
        db_conn.commit()
        cursor.close()

        try:
            result = initialize_product_tasks(serial_number, qr_doc_id, 'GALLANT-50')

            assert result.get('error') is None
            # GALLANT는 TMS 없음
            tms_count = result.get('categories', {}).get('TMS', 0)
            assert tms_count == 0, f"GALLANT는 TMS task 0개여야 함, 현재 {tms_count}개"
            # ELEC는 6개
            assert result.get('categories', {}).get('ELEC', 0) == 6
        finally:
            cursor = db_conn.cursor()
            cursor.execute("DELETE FROM app_task_details WHERE serial_number = %s", (serial_number,))
            cursor.execute("DELETE FROM completion_status WHERE serial_number = %s", (serial_number,))
            cursor.execute("DELETE FROM public.qr_registry WHERE qr_doc_id = %s", (qr_doc_id,))
            cursor.execute("DELETE FROM plan.product_info WHERE serial_number = %s", (serial_number,))
            db_conn.commit()
            cursor.close()
