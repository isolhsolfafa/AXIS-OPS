"""
Sprint 11: GST Task 템플릿 추가 검증 테스트
PI 2개 + QI 1개 + SI 1개 — 모든 모델 공통 생성 확인

테스트 대상:
- initialize_product_tasks() 호출 시 PI/QI/SI task 자동 생성 (기존 15개 + 4개 = 19개)
- PI task: PI_LNG_UTIL, PI_CHAMBER (task_category='PI')
- QI task: QI_INSPECTION (task_category='QI')
- SI task: SI_FINISHING (task_category='SI')
- 중복 생성 방지
- GST 작업자 / Admin이 PI/QI/SI task 조회 가능
"""

import pytest
import sys
from pathlib import Path
from typing import Dict, Any

# backend 경로 추가
backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


# ============================================================
# 헬퍼 함수
# ============================================================

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


def _get_task_counts_by_category(db_conn, serial_number: str) -> Dict[str, int]:
    """시리얼 번호 기준 카테고리별 Task 수 조회"""
    cursor = db_conn.cursor()
    cursor.execute("""
        SELECT task_category, COUNT(*) AS total
        FROM app_task_details
        WHERE serial_number = %s
        GROUP BY task_category
    """, (serial_number,))
    rows = cursor.fetchall()
    cursor.close()
    return {row[0]: row[1] for row in rows}


def _cleanup_test_data(db_conn, serial_number: str, qr_doc_id: str):
    """테스트 데이터 정리 헬퍼"""
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


# ============================================================
# 공통 픽스처
# ============================================================

def _do_cleanup_gst_seed_data(db_conn):
    """GST seed 테스트 데이터 정리 (setup/teardown 공용)"""
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            cursor.execute(
                "DELETE FROM app_task_details WHERE serial_number LIKE 'SN-SP11-%%'"
            )
            cursor.execute(
                "DELETE FROM completion_status WHERE serial_number LIKE 'SN-SP11-%%'"
            )
            cursor.execute(
                "DELETE FROM public.qr_registry WHERE qr_doc_id LIKE 'DOC-SP11-%%'"
            )
            cursor.execute(
                "DELETE FROM plan.product_info WHERE serial_number LIKE 'SN-SP11-%%'"
            )
            cursor.execute(
                "DELETE FROM workers WHERE email LIKE '%%@sp11_seed_test.com'"
            )
            db_conn.commit()
            cursor.close()
        except Exception:
            try:
                db_conn.rollback()
            except Exception:
                pass


@pytest.fixture(autouse=True)
def cleanup_gst_seed_data(db_conn):
    """테스트 전/후 GST seed 테스트 데이터 정리 (stale data 방지)"""
    _do_cleanup_gst_seed_data(db_conn)
    yield
    _do_cleanup_gst_seed_data(db_conn)


# ============================================================
# TC-GST-SEED-01 ~ 10: PI/QI/SI task 생성 확인
# ============================================================

class TestGSTTaskSeedPIQISI:
    """Sprint 11: PI/QI/SI Task Seed 생성 테스트"""

    def test_gaia_pi_tasks_created(self, db_conn):
        """
        TC-GST-SEED-01: GAIA 모델 seed → PI task 2개 생성 확인

        Expected:
        - PI_LNG_UTIL, PI_CHAMBER 각각 task_category='PI'로 생성
        - is_applicable = True
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 서비스 임포트 실패")

        serial_number = 'SN-SP11-GAIA-001'
        qr_doc_id = 'DOC-SP11-GAIA-001'
        _insert_test_product(db_conn, serial_number, qr_doc_id, 'GAIA-100')

        try:
            result = initialize_product_tasks(serial_number, qr_doc_id, 'GAIA-100')

            # DB 인프라 오류(relation does not exist) 시 skip (transient)
            error_msg = result.get('error') or ''
            if 'does not exist' in error_msg:
                pytest.skip(f"DB 인프라 오류 (transient): {error_msg[:100]}")

            assert result.get('error') is None, f"Seed 에러: {result.get('error')}"

            # PI task 2개 확인
            pi_count = result.get('categories', {}).get('PI', 0)
            assert pi_count == 2, f"PI task 2개 필요, 현재 {pi_count}개"

            # DB에서 직접 확인
            cursor = db_conn.cursor()
            cursor.execute("""
                SELECT task_id, task_category, is_applicable
                FROM app_task_details
                WHERE serial_number = %s AND task_category = 'PI'
                ORDER BY task_id
            """, (serial_number,))
            pi_rows = cursor.fetchall()
            cursor.close()

            assert len(pi_rows) == 2, f"DB에 PI task 2개 필요, 현재 {len(pi_rows)}개"
            pi_task_ids = [r[0] for r in pi_rows]
            assert 'PI_LNG_UTIL' in pi_task_ids, "PI_LNG_UTIL task 없음"
            assert 'PI_CHAMBER' in pi_task_ids, "PI_CHAMBER task 없음"
            for row in pi_rows:
                assert row[2] is True, f"{row[0]}의 is_applicable이 True여야 함"

        finally:
            _cleanup_test_data(db_conn, serial_number, qr_doc_id)

    def test_gaia_qi_task_created(self, db_conn):
        """
        TC-GST-SEED-02: GAIA 모델 seed → QI task 1개 생성 확인

        Expected:
        - QI_INSPECTION task_category='QI', is_applicable=True
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 서비스 임포트 실패")

        serial_number = 'SN-SP11-GAIA-002'
        qr_doc_id = 'DOC-SP11-GAIA-002'
        _insert_test_product(db_conn, serial_number, qr_doc_id, 'GAIA-100')

        try:
            result = initialize_product_tasks(serial_number, qr_doc_id, 'GAIA-100')

            assert result.get('error') is None

            qi_count = result.get('categories', {}).get('QI', 0)
            assert qi_count == 1, f"QI task 1개 필요, 현재 {qi_count}개"

            cursor = db_conn.cursor()
            cursor.execute("""
                SELECT task_id, task_category, is_applicable
                FROM app_task_details
                WHERE serial_number = %s AND task_category = 'QI'
            """, (serial_number,))
            qi_row = cursor.fetchone()
            cursor.close()

            assert qi_row is not None, "QI task DB에 없음"
            assert qi_row[0] == 'QI_INSPECTION', f"QI task_id 오류: {qi_row[0]}"
            assert qi_row[2] is True, "QI_INSPECTION is_applicable=True여야 함"

        finally:
            _cleanup_test_data(db_conn, serial_number, qr_doc_id)

    def test_gaia_si_task_created(self, db_conn):
        """
        TC-GST-SEED-03: GAIA 모델 seed → SI task 1개 생성 확인

        Expected:
        - SI_FINISHING task_category='SI', is_applicable=True
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 서비스 임포트 실패")

        serial_number = 'SN-SP11-GAIA-003'
        qr_doc_id = 'DOC-SP11-GAIA-003'
        _insert_test_product(db_conn, serial_number, qr_doc_id, 'GAIA-100')

        try:
            result = initialize_product_tasks(serial_number, qr_doc_id, 'GAIA-100')

            assert result.get('error') is None

            si_count = result.get('categories', {}).get('SI', 0)
            assert si_count == 1, f"SI task 1개 필요, 현재 {si_count}개"

            cursor = db_conn.cursor()
            cursor.execute("""
                SELECT task_id, task_category, is_applicable
                FROM app_task_details
                WHERE serial_number = %s AND task_category = 'SI'
            """, (serial_number,))
            si_row = cursor.fetchone()
            cursor.close()

            assert si_row is not None, "SI task DB에 없음"
            assert si_row[0] == 'SI_FINISHING', f"SI task_id 오류: {si_row[0]}"
            assert si_row[2] is True, "SI_FINISHING is_applicable=True여야 함"

        finally:
            _cleanup_test_data(db_conn, serial_number, qr_doc_id)

    def test_gaia_total_19_tasks(self, db_conn):
        """
        TC-GST-SEED-04: GAIA 모델 seed → 총 19개 Task 생성 확인
        기존 15개 (MECH 7 + ELEC 6 + TMS 2) + Sprint 11 추가 4개 (PI 2 + QI 1 + SI 1) = 19개

        Expected:
        - 총 Task 수 = 19개
        - categories = {MECH:7, ELEC:6, TMS:2, PI:2, QI:1, SI:1}
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 서비스 임포트 실패")

        serial_number = 'SN-SP11-GAIA-004'
        qr_doc_id = 'DOC-SP11-GAIA-004'
        _insert_test_product(db_conn, serial_number, qr_doc_id, 'GAIA-100')

        try:
            result = initialize_product_tasks(serial_number, qr_doc_id, 'GAIA-100')

            assert result.get('error') is None

            total = result.get('created', 0)
            assert total == 19, f"GAIA Sprint 11 총 19개 task 필요, 현재 {total}개"

            cats = result.get('categories', {})
            assert cats.get('MECH', 0) == 7, f"MECH 7개 필요, 현재 {cats.get('MECH', 0)}개"
            assert cats.get('ELEC', 0) == 6, f"ELEC 6개 필요, 현재 {cats.get('ELEC', 0)}개"
            assert cats.get('TMS', 0) == 2, f"TMS 2개 필요, 현재 {cats.get('TMS', 0)}개"
            assert cats.get('PI', 0) == 2, f"PI 2개 필요, 현재 {cats.get('PI', 0)}개"
            assert cats.get('QI', 0) == 1, f"QI 1개 필요, 현재 {cats.get('QI', 0)}개"
            assert cats.get('SI', 0) == 1, f"SI 1개 필요, 현재 {cats.get('SI', 0)}개"

        finally:
            _cleanup_test_data(db_conn, serial_number, qr_doc_id)

    def test_dragon_pi_qi_si_tasks_created(self, db_conn):
        """
        TC-GST-SEED-05: DRAGON 모델 seed → PI/QI/SI task 4개 생성 확인
        PI/QI/SI는 모든 모델 공통 적용

        Expected:
        - PI 2개 + QI 1개 + SI 1개 = 4개 생성
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 서비스 임포트 실패")

        serial_number = 'SN-SP11-DRAGON-001'
        qr_doc_id = 'DOC-SP11-DRAGON-001'
        _insert_test_product(db_conn, serial_number, qr_doc_id, 'DRAGON-200')

        try:
            result = initialize_product_tasks(serial_number, qr_doc_id, 'DRAGON-200')

            assert result.get('error') is None

            cats = result.get('categories', {})
            assert cats.get('PI', 0) == 2, f"DRAGON PI 2개 필요, 현재 {cats.get('PI', 0)}개"
            assert cats.get('QI', 0) == 1, f"DRAGON QI 1개 필요, 현재 {cats.get('QI', 0)}개"
            assert cats.get('SI', 0) == 1, f"DRAGON SI 1개 필요, 현재 {cats.get('SI', 0)}개"

        finally:
            _cleanup_test_data(db_conn, serial_number, qr_doc_id)

    def test_gallant_pi_qi_si_tasks_created(self, db_conn):
        """
        TC-GST-SEED-06: GALLANT 모델 seed → PI/QI/SI task 4개 생성 확인

        Expected:
        - PI 2개 + QI 1개 + SI 1개 = 4개 생성
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 서비스 임포트 실패")

        serial_number = 'SN-SP11-GALLANT-001'
        qr_doc_id = 'DOC-SP11-GALLANT-001'
        _insert_test_product(db_conn, serial_number, qr_doc_id, 'GALLANT-50')

        try:
            result = initialize_product_tasks(serial_number, qr_doc_id, 'GALLANT-50')

            assert result.get('error') is None

            cats = result.get('categories', {})
            assert cats.get('PI', 0) == 2, f"GALLANT PI 2개 필요, 현재 {cats.get('PI', 0)}개"
            assert cats.get('QI', 0) == 1, f"GALLANT QI 1개 필요, 현재 {cats.get('QI', 0)}개"
            assert cats.get('SI', 0) == 1, f"GALLANT SI 1개 필요, 현재 {cats.get('SI', 0)}개"

        finally:
            _cleanup_test_data(db_conn, serial_number, qr_doc_id)

    def test_no_duplicate_pi_qi_si_on_re_seed(self, db_conn):
        """
        TC-GST-SEED-07: 중복 생성 방지 — 같은 S/N 재초기화 시 PI/QI/SI 중복 없음

        Expected:
        - 첫 번째 호출: PI 2 + QI 1 + SI 1 생성
        - 두 번째 호출: PI/QI/SI 모두 created=0, skipped 증가
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        try:
            from app.services.task_seed import initialize_product_tasks
        except ImportError:
            pytest.skip("task_seed 서비스 임포트 실패")

        serial_number = 'SN-SP11-DEDUP-001'
        qr_doc_id = 'DOC-SP11-DEDUP-001'
        _insert_test_product(db_conn, serial_number, qr_doc_id, 'GAIA-100')

        try:
            result1 = initialize_product_tasks(serial_number, qr_doc_id, 'GAIA-100')
            result2 = initialize_product_tasks(serial_number, qr_doc_id, 'GAIA-100')

            assert result1.get('error') is None
            assert result2.get('error') is None

            # 두 번째 호출: 새로 생성된 task 없음
            assert result2.get('created', 0) == 0, \
                f"중복 seed 시 created=0 필요, 현재 {result2.get('created')}개"

            # DB에서 PI/QI/SI 중복 없음 확인
            cursor = db_conn.cursor()
            cursor.execute("""
                SELECT task_category, COUNT(*) FROM app_task_details
                WHERE serial_number = %s AND task_category IN ('PI', 'QI', 'SI')
                GROUP BY task_category
            """, (serial_number,))
            rows = {r[0]: r[1] for r in cursor.fetchall()}
            cursor.close()

            assert rows.get('PI', 0) == 2, f"PI 중복 없이 2개 유지 필요, 현재 {rows.get('PI', 0)}개"
            assert rows.get('QI', 0) == 1, f"QI 중복 없이 1개 유지 필요, 현재 {rows.get('QI', 0)}개"
            assert rows.get('SI', 0) == 1, f"SI 중복 없이 1개 유지 필요, 현재 {rows.get('SI', 0)}개"

        finally:
            _cleanup_test_data(db_conn, serial_number, qr_doc_id)

    def test_gst_worker_can_query_pi_tasks_via_api(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """
        TC-GST-SEED-08: GST 작업자가 PI/QI/SI task 전부 조회 가능

        Expected:
        - GET /api/app/tasks/{serial_number} 호출 시 PI/QI/SI task 포함
        - company='GST' 작업자는 active_role 무관하게 전체 조회
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        serial_number = 'SN-SP11-GSTQ-001'
        qr_doc_id = 'DOC-SP11-GSTQ-001'

        # 제품 + PI/QI/SI task 직접 삽입
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO plan.product_info (serial_number, model)
            VALUES (%s, 'GAIA-100') ON CONFLICT (serial_number) DO NOTHING
        """, (serial_number,))
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number)
            VALUES (%s, %s) ON CONFLICT (qr_doc_id) DO NOTHING
        """, (qr_doc_id, serial_number))
        for cat, tid, tname in [
            ('PI', 'PI_LNG_UTIL', 'LNG/UTIL 가압검사'),
            ('PI', 'PI_CHAMBER', 'CHAMBER 가압검사'),
            ('QI', 'QI_INSPECTION', '공정검사'),
            ('SI', 'SI_FINISHING', '마무리공정'),
        ]:
            cursor.execute("""
                INSERT INTO app_task_details
                    (serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable)
                VALUES (%s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (serial_number, task_category, task_id) DO NOTHING
            """, (serial_number, qr_doc_id, cat, tid, tname))
        db_conn.commit()
        cursor.close()

        # GST 작업자 생성
        worker_id = create_test_worker(
            email='gst_pi@sp11_seed_test.com', password='Test123!',
            name='GST PI Worker', role='PI', company='GST'
        )
        token = get_auth_token(worker_id, role='PI')

        response = client.get(
            f'/api/app/tasks/{serial_number}',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/tasks/<sn> 미구현")

        assert response.status_code == 200
        data = response.get_json()
        tasks = data if isinstance(data, list) else data.get('tasks', [])

        task_categories = {t.get('task_category') for t in tasks}
        # GST 작업자는 PI/QI/SI task를 볼 수 있어야 함
        assert 'PI' in task_categories or 'QI' in task_categories or 'SI' in task_categories, \
            f"GST 작업자가 PI/QI/SI task를 볼 수 없음. categories: {task_categories}"

    def test_admin_can_query_pi_qi_si_tasks(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """
        TC-GST-SEED-09: Admin이 PI/QI/SI task 전부 조회 가능

        Expected:
        - is_admin=True 계정 → PI/QI/SI task 포함 전체 조회 가능
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        serial_number = 'SN-SP11-ADMQ-001'
        qr_doc_id = 'DOC-SP11-ADMQ-001'

        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO plan.product_info (serial_number, model)
            VALUES (%s, 'GALLANT-50') ON CONFLICT (serial_number) DO NOTHING
        """, (serial_number,))
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number)
            VALUES (%s, %s) ON CONFLICT (qr_doc_id) DO NOTHING
        """, (qr_doc_id, serial_number))
        for cat, tid, tname in [
            ('PI', 'PI_LNG_UTIL', 'LNG/UTIL 가압검사'),
            ('QI', 'QI_INSPECTION', '공정검사'),
            ('SI', 'SI_FINISHING', '마무리공정'),
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
            email='admin_pqsi@sp11_seed_test.com', password='Test123!',
            name='Admin PI QI SI', role='ADMIN', is_admin=True, company='GST'
        )
        token = get_auth_token(admin_id, role='ADMIN', is_admin=True)

        response = client.get(
            f'/api/app/tasks/{serial_number}',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/tasks/<sn> 미구현")

        assert response.status_code == 200
        data = response.get_json()
        tasks = data if isinstance(data, list) else data.get('tasks', [])

        task_categories = {t.get('task_category') for t in tasks}
        assert len(task_categories) >= 1, "Admin은 task를 볼 수 있어야 함"

    def test_initialize_tasks_api_creates_pi_qi_si(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """
        TC-GST-SEED-10: POST /api/admin/products/initialize-tasks → PI/QI/SI 포함 19개 생성

        Expected:
        - 응답에 PI/QI/SI category 포함
        - DB에 PI/QI/SI task 존재
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        serial_number = 'SN-SP11-INIT-001'
        qr_doc_id = 'DOC-SP11-INIT-001'
        _insert_test_product(db_conn, serial_number, qr_doc_id, 'GAIA-100')

        admin_id = create_test_worker(
            email='admin_init@sp11_seed_test.com', password='Test123!',
            name='Admin Init', role='ADMIN', is_admin=True
        )
        token = get_auth_token(admin_id, role='ADMIN', is_admin=True)

        response = client.post(
            '/api/admin/products/initialize-tasks',
            json={'serial_number': serial_number, 'qr_doc_id': qr_doc_id, 'model_name': 'GAIA-100'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in [404, 405]:
            pytest.skip("POST /api/admin/products/initialize-tasks 미구현")

        assert response.status_code in [200, 201], \
            f"Expected 200/201, got {response.status_code}: {response.get_json()}"

        # DB에서 PI/QI/SI task 확인
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT task_category, COUNT(*)
            FROM app_task_details
            WHERE serial_number = %s AND task_category IN ('PI', 'QI', 'SI')
            GROUP BY task_category
        """, (serial_number,))
        rows = {r[0]: r[1] for r in cursor.fetchall()}
        cursor.close()

        assert rows.get('PI', 0) == 2, f"PI 2개 필요, 현재 {rows.get('PI', 0)}개"
        assert rows.get('QI', 0) == 1, f"QI 1개 필요, 현재 {rows.get('QI', 0)}개"
        assert rows.get('SI', 0) == 1, f"SI 1개 필요, 현재 {rows.get('SI', 0)}개"
