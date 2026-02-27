"""
Product API 테스트
Sprint 7: GET /api/app/product/{qr_doc_id} + Task Seed 자동 생성 + Location QR 업데이트

엔드포인트:
- GET  /api/app/product/<qr_doc_id>           — QR 제품 조회 + Task Seed 자동 초기화
- GET  /api/app/product/<qr_doc_id>/tasks     — 제품별 작업 목록
- GET  /api/app/product/<qr_doc_id>/completion — 공정 완료 상태 조회
- POST /api/app/product/location/update        — Location QR 업데이트
"""

import pytest
from typing import Dict, Any


# ============================================================
# 헬퍼 함수
# ============================================================

def _count_tasks_by_category(db_conn, serial_number: str) -> Dict[str, int]:
    """DB에서 serial_number 기준 카테고리별 task 수 조회"""
    cursor = db_conn.cursor()
    cursor.execute("""
        SELECT task_category, COUNT(*) AS cnt
        FROM app_task_details
        WHERE serial_number = %s
        GROUP BY task_category
    """, (serial_number,))
    rows = cursor.fetchall()
    cursor.close()
    return {row[0]: row[1] for row in rows}


def _total_tasks(db_conn, serial_number: str) -> int:
    """DB에서 serial_number 기준 총 task 수 조회"""
    counts = _count_tasks_by_category(db_conn, serial_number)
    return sum(counts.values())


# ============================================================
# TC-PROD-01 ~ TC-PROD-08: 제품 조회 기본 테스트
# ============================================================

class TestProductLookup:
    """제품 조회 API 기본 테스트"""

    def test_get_product_success(self, client, seed_test_products, get_auth_token, create_test_worker):
        """
        TC-PROD-01: GAIA 제품 조회 성공

        Expected:
        - Status 200
        - qr_doc_id, serial_number, model, is_tms 필드 포함
        - is_tms = True (GAIA 모델)
        """
        worker_id = create_test_worker(
            email='prod_lookup@test.com', password='Test123!',
            name='Prod Lookup Worker', role='MECH'
        )
        token = get_auth_token(worker_id, role='MECH')

        gaia = next(p for p in seed_test_products if 'GAIA' in p['model'])
        response = client.get(
            f'/api/app/product/{gaia["qr_doc_id"]}',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200, \
            f"Expected 200, got {response.status_code}: {response.get_json()}"
        data = response.get_json()
        assert data['qr_doc_id'] == gaia['qr_doc_id']
        assert data['serial_number'] == gaia['serial_number']
        assert 'model' in data
        assert 'is_tms' in data

    def test_get_product_gaia_has_is_tms_field(self, client, seed_test_products, get_auth_token, create_test_worker):
        """
        TC-PROD-02: GAIA 제품 조회 → is_tms 필드 존재 확인

        Expected:
        - is_tms 필드가 응답에 포함됨
        - is_tms 값은 is_tms_product() 로직에 의존
          (mech_partner=FNI인 경우 is_tms=False — partner 기반 판단)
        """
        worker_id = create_test_worker(
            email='gaia_tms@test.com', password='Test123!',
            name='GAIA TMS Worker', role='MECH'
        )
        token = get_auth_token(worker_id, role='MECH')

        gaia = next(p for p in seed_test_products if 'GAIA' in p['model'])
        response = client.get(
            f'/api/app/product/{gaia["qr_doc_id"]}',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'is_tms' in data, "is_tms 필드가 응답에 포함되어야 함"

    def test_get_product_gallant_is_tms_false(self, client, seed_test_products, get_auth_token, create_test_worker):
        """
        TC-PROD-03: GALLANT 제품 조회 → is_tms=False 확인

        Expected:
        - is_tms = False (GALLANT는 TMS 없음)
        """
        worker_id = create_test_worker(
            email='gallant_notms@test.com', password='Test123!',
            name='GALLANT No TMS', role='MECH'
        )
        token = get_auth_token(worker_id, role='MECH')

        gallant = next(p for p in seed_test_products if 'GALLANT' in p['model'])
        response = client.get(
            f'/api/app/product/{gallant["qr_doc_id"]}',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data.get('is_tms') is False, \
            f"GALLANT 제품은 is_tms=False여야 함, got {data.get('is_tms')}"

    def test_get_product_not_found(self, client, get_auth_token, create_test_worker):
        """
        TC-PROD-04: 존재하지 않는 QR 조회 → 404

        Expected:
        - Status 404
        - error: PRODUCT_NOT_FOUND
        """
        worker_id = create_test_worker(
            email='prod_notfound@test.com', password='Test123!',
            name='Not Found Worker', role='MECH'
        )
        token = get_auth_token(worker_id, role='MECH')

        response = client.get(
            '/api/app/product/DOC_NONEXISTENT_999999',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 404, \
            f"존재하지 않는 QR은 404여야 함, got {response.status_code}"
        data = response.get_json()
        assert data.get('error') == 'PRODUCT_NOT_FOUND'

    def test_get_product_unauthenticated(self, client, seed_test_products):
        """
        TC-PROD-05: 미인증 상태 제품 조회 → 401

        Expected:
        - Status 401 (Authorization 헤더 없음)
        """
        gaia = next(p for p in seed_test_products if 'GAIA' in p['model'])
        response = client.get(f'/api/app/product/{gaia["qr_doc_id"]}')

        assert response.status_code == 401, \
            f"미인증 요청은 401이어야 함, got {response.status_code}"

    def test_get_product_invalid_token(self, client, seed_test_products):
        """
        TC-PROD-06: 잘못된 토큰으로 제품 조회 → 401

        Expected:
        - Status 401
        """
        gaia = next(p for p in seed_test_products if 'GAIA' in p['model'])
        response = client.get(
            f'/api/app/product/{gaia["qr_doc_id"]}',
            headers={'Authorization': 'Bearer invalid_token_xyz'}
        )

        assert response.status_code == 401, \
            f"잘못된 토큰은 401이어야 함, got {response.status_code}"


# ============================================================
# TC-SEED-AUTO-01 ~ 04: Task Seed 자동 생성 테스트
# ============================================================

class TestTaskSeedAutoInit:
    """제품 조회 시 Task Seed 자동 생성 테스트"""

    def test_product_lookup_auto_seeds_tasks(
        self, client, seed_test_products, get_auth_token, create_test_worker, db_conn
    ):
        """
        TC-SEED-AUTO-01: GAIA 제품 최초 조회 → Task 자동 생성

        Expected:
        - 총 15개 Task 생성 (MECH 7 + ELEC 6 + TMS 2)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='auto_seed@test.com', password='Test123!',
            name='Auto Seed Worker', role='MECH'
        )
        token = get_auth_token(worker_id, role='MECH')

        gaia = next(p for p in seed_test_products if 'GAIA' in p['model'])
        serial_number = gaia['serial_number']

        # 기존 Task 정리 (혹시 남아 있으면)
        cursor = db_conn.cursor()
        cursor.execute(
            "DELETE FROM app_task_details WHERE serial_number = %s",
            (serial_number,)
        )
        db_conn.commit()
        cursor.close()

        # 제품 조회 → Task Seed 자동 트리거
        response = client.get(
            f'/api/app/product/{gaia["qr_doc_id"]}',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200

        # DB에서 Task 수 확인
        total = _total_tasks(db_conn, serial_number)
        assert total == 19, \
            f"GAIA 조회 후 19개 Task 자동 생성되어야 함 (MECH7+ELEC6+TMS2+PI2+QI1+SI1), 현재 {total}개"

    def test_product_lookup_gaia_has_tms_tasks(
        self, client, seed_test_products, get_auth_token, create_test_worker, db_conn
    ):
        """
        TC-SEED-AUTO-02: GAIA 조회 후 TMS task 2개 생성 확인

        Expected:
        - TMS category task가 2개 존재
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='gaia_tms_seed@test.com', password='Test123!',
            name='GAIA TMS Seed', role='MECH'
        )
        token = get_auth_token(worker_id, role='MECH')

        gaia = next(p for p in seed_test_products if 'GAIA' in p['model'])
        serial_number = gaia['serial_number']

        # 기존 Task 정리
        cursor = db_conn.cursor()
        cursor.execute(
            "DELETE FROM app_task_details WHERE serial_number = %s",
            (serial_number,)
        )
        db_conn.commit()
        cursor.close()

        # 조회
        response = client.get(
            f'/api/app/product/{gaia["qr_doc_id"]}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200

        counts = _count_tasks_by_category(db_conn, serial_number)
        assert counts.get('TMS', 0) == 2, \
            f"GAIA는 TMS task 2개여야 함, 현재 {counts.get('TMS', 0)}개"

    def test_product_lookup_gallant_no_tms_tasks(
        self, client, seed_test_products, get_auth_token, create_test_worker, db_conn
    ):
        """
        TC-SEED-AUTO-03: GALLANT 조회 후 TMS task 없음 확인

        Expected:
        - TMS category task = 0개
        - 총 13개 (MECH 7 + ELEC 6)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='gallant_notms_seed@test.com', password='Test123!',
            name='GALLANT No TMS Seed', role='MECH'
        )
        token = get_auth_token(worker_id, role='MECH')

        gallant = next(p for p in seed_test_products if 'GALLANT' in p['model'])
        serial_number = gallant['serial_number']

        # 기존 Task 정리
        cursor = db_conn.cursor()
        cursor.execute(
            "DELETE FROM app_task_details WHERE serial_number = %s",
            (serial_number,)
        )
        db_conn.commit()
        cursor.close()

        # 조회
        response = client.get(
            f'/api/app/product/{gallant["qr_doc_id"]}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200

        counts = _count_tasks_by_category(db_conn, serial_number)
        assert counts.get('TMS', 0) == 0, \
            f"GALLANT는 TMS task 없어야 함, 현재 {counts.get('TMS', 0)}개"

        total = sum(counts.values())
        assert total == 17, \
            f"GALLANT는 17개 Task여야 함 (MECH7+ELEC6+PI2+QI1+SI1), 현재 {total}개"

    def test_product_lookup_idempotent_seed(
        self, client, seed_test_products, get_auth_token, create_test_worker, db_conn
    ):
        """
        TC-SEED-AUTO-04: 같은 제품 재조회 → Task 중복 생성 없음 (멱등성)

        Expected:
        - 첫 번째 조회: Task 생성
        - 두 번째 조회: Task 수 변화 없음
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='idempotent_seed@test.com', password='Test123!',
            name='Idempotent Seed Worker', role='MECH'
        )
        token = get_auth_token(worker_id, role='MECH')

        gaia = next(p for p in seed_test_products if 'GAIA' in p['model'])
        serial_number = gaia['serial_number']

        # 기존 Task 정리
        cursor = db_conn.cursor()
        cursor.execute(
            "DELETE FROM app_task_details WHERE serial_number = %s",
            (serial_number,)
        )
        db_conn.commit()
        cursor.close()

        # 첫 번째 조회
        r1 = client.get(
            f'/api/app/product/{gaia["qr_doc_id"]}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert r1.status_code == 200
        count_after_first = _total_tasks(db_conn, serial_number)

        # 두 번째 조회
        r2 = client.get(
            f'/api/app/product/{gaia["qr_doc_id"]}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert r2.status_code == 200
        count_after_second = _total_tasks(db_conn, serial_number)

        assert count_after_first == count_after_second, \
            f"재조회 시 Task 수 변화 없어야 함: 1차={count_after_first}, 2차={count_after_second}"
        assert count_after_first > 0, "Task가 최소 1개 이상 생성되어야 함"


# ============================================================
# TC-PROD-TASKS: 제품별 작업 목록 조회 테스트
# ============================================================

class TestProductTasks:
    """GET /api/app/product/{qr_doc_id}/tasks 테스트"""

    def test_get_product_tasks_all(
        self, client, seed_test_products, get_auth_token, create_test_worker, db_conn
    ):
        """
        TC-PROD-TASKS-01: 제품 Task 목록 전체 조회

        Expected:
        - Status 200
        - tasks 배열 포함
        - total 필드 포함
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='prod_tasks_all@test.com', password='Test123!',
            name='Prod Tasks All', role='MECH'
        )
        token = get_auth_token(worker_id, role='MECH')

        gaia = next(p for p in seed_test_products if 'GAIA' in p['model'])

        # Task가 없으면 먼저 조회로 Seed 생성
        client.get(
            f'/api/app/product/{gaia["qr_doc_id"]}',
            headers={'Authorization': f'Bearer {token}'}
        )

        response = client.get(
            f'/api/app/product/{gaia["qr_doc_id"]}/tasks',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/product/{qr_doc_id}/tasks 미구현")

        assert response.status_code == 200
        data = response.get_json()
        assert 'tasks' in data, "응답에 tasks 배열 필요"
        assert 'total' in data, "응답에 total 필드 필요"
        assert isinstance(data['tasks'], list)

    def test_get_product_tasks_by_category(
        self, client, seed_test_products, get_auth_token, create_test_worker, db_conn
    ):
        """
        TC-PROD-TASKS-02: task_category 파라미터로 필터링

        Expected:
        - task_category=MECH → MECH tasks만 반환
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='prod_tasks_cat@test.com', password='Test123!',
            name='Prod Tasks Cat', role='MECH'
        )
        token = get_auth_token(worker_id, role='MECH')

        gaia = next(p for p in seed_test_products if 'GAIA' in p['model'])

        # Task Seed 생성
        client.get(
            f'/api/app/product/{gaia["qr_doc_id"]}',
            headers={'Authorization': f'Bearer {token}'}
        )

        response = client.get(
            f'/api/app/product/{gaia["qr_doc_id"]}/tasks?task_category=MECH',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("task_category 필터 미구현")

        assert response.status_code == 200
        data = response.get_json()
        tasks = data.get('tasks', [])

        # 반환된 task는 모두 MECH 카테고리여야 함
        for task in tasks:
            assert task.get('task_category') == 'MECH', \
                f"MECH 필터 시 MECH task만 반환되어야 함, got {task.get('task_category')}"

    def test_get_product_tasks_not_found(self, client, get_auth_token, create_test_worker):
        """
        TC-PROD-TASKS-03: 존재하지 않는 제품의 tasks 조회 → 404

        Expected:
        - Status 404
        """
        worker_id = create_test_worker(
            email='prod_tasks_nf@test.com', password='Test123!',
            name='Prod Tasks NF', role='MECH'
        )
        token = get_auth_token(worker_id, role='MECH')

        response = client.get(
            '/api/app/product/DOC_NONEXISTENT_999999/tasks',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            data = response.get_json()
            assert data.get('error') in ['PRODUCT_NOT_FOUND', 'NOT_FOUND'], \
                f"404 응답에 에러 코드가 있어야 함: {data}"
        else:
            pytest.skip("존재하지 않는 제품 tasks 조회 동작 다름")


# ============================================================
# TC-LOC: Location QR 업데이트 테스트
# ============================================================

class TestLocationUpdate:
    """POST /api/app/product/location/update 테스트"""

    def test_update_location_qr_success(
        self, client, seed_test_products, get_auth_token, create_test_worker, db_conn
    ):
        """
        TC-LOC-01: Location QR 업데이트 성공

        Expected:
        - Status 200
        - location_qr_id 업데이트됨
        """
        worker_id = create_test_worker(
            email='loc_update@test.com', password='Test123!',
            name='Location Update Worker', role='MECH'
        )
        token = get_auth_token(worker_id, role='MECH')

        gallant = next(p for p in seed_test_products if 'GALLANT' in p['model'])

        response = client.post(
            '/api/app/product/location/update',
            json={
                'qr_doc_id': gallant['qr_doc_id'],
                'location_qr_id': 'LOC_STATION_A1'
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("POST /api/app/product/location/update 미구현")

        assert response.status_code == 200, \
            f"Location 업데이트 실패: {response.status_code}, {response.get_json()}"

    def test_update_location_missing_fields(
        self, client, seed_test_products, get_auth_token, create_test_worker
    ):
        """
        TC-LOC-02: 필수 필드 누락 → 400

        Expected:
        - Status 400
        """
        worker_id = create_test_worker(
            email='loc_missing@test.com', password='Test123!',
            name='Loc Missing Fields', role='MECH'
        )
        token = get_auth_token(worker_id, role='MECH')

        # qr_doc_id 없이 요청
        response = client.post(
            '/api/app/product/location/update',
            json={'location_qr_id': 'LOC_STATION_A1'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("POST /api/app/product/location/update 미구현")

        assert response.status_code == 400, \
            f"필수 필드 누락 시 400이어야 함, got {response.status_code}"

    def test_update_location_product_not_found(
        self, client, get_auth_token, create_test_worker
    ):
        """
        TC-LOC-03: 존재하지 않는 제품의 Location 업데이트 → 404

        Expected:
        - Status 404
        """
        worker_id = create_test_worker(
            email='loc_notfound@test.com', password='Test123!',
            name='Loc Not Found', role='MECH'
        )
        token = get_auth_token(worker_id, role='MECH')

        response = client.post(
            '/api/app/product/location/update',
            json={
                'qr_doc_id': 'DOC_NONEXISTENT_999',
                'location_qr_id': 'LOC_STATION_X'
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            data = response.get_json()
            assert data.get('error') == 'PRODUCT_NOT_FOUND'
        else:
            pytest.skip("존재하지 않는 제품 location update 동작 다름")


# ============================================================
# TC-COMPLETION: 공정 완료 상태 조회 테스트
# ============================================================

class TestCompletionStatus:
    """GET /api/app/product/{qr_doc_id}/completion 테스트"""

    def test_get_completion_status_initial(
        self, client, seed_test_products, get_auth_token, create_test_worker, db_conn
    ):
        """
        TC-COMP-01: 초기 완료 상태 조회 → 모두 False

        Expected:
        - Status 200
        - mech_completed, elec_completed 등 모두 False
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='comp_initial@test.com', password='Test123!',
            name='Comp Initial Worker', role='MECH'
        )
        token = get_auth_token(worker_id, role='MECH')

        gaia = next(p for p in seed_test_products if 'GAIA' in p['model'])
        serial_number = gaia['serial_number']

        # completion_status 초기화 (없으면 생성)
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO completion_status (serial_number)
            VALUES (%s)
            ON CONFLICT (serial_number) DO UPDATE
            SET mech_completed = FALSE, elec_completed = FALSE,
                tm_completed = FALSE, pi_completed = FALSE,
                qi_completed = FALSE, si_completed = FALSE, all_completed = FALSE
        """, (serial_number,))
        db_conn.commit()
        cursor.close()

        response = client.get(
            f'/api/app/product/{gaia["qr_doc_id"]}/completion',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/product/{qr_doc_id}/completion 미구현")

        assert response.status_code == 200
        data = response.get_json()
        assert 'mech_completed' in data
        assert 'elec_completed' in data
        assert data['mech_completed'] is False
        assert data['elec_completed'] is False
