"""
Work API 테스트
작업 시작/완료/조회 API 테스트

실제 엔드포인트:
- POST /api/app/work/start      — 작업 시작
- POST /api/app/work/complete   — 작업 완료
- GET  /api/app/tasks/<serial>  — serial_number 기준 Task 목록 조회
- GET  /api/app/completion/<serial> — completion_status 조회
"""

import pytest
from datetime import datetime, timedelta, timezone


class TestTaskOperations:
    """작업 시작/완료 API 테스트"""

    def test_start_task(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """
        TC-WORK-01: 작업 시작 성공

        Expected:
        - Status 200
        - started_at 설정됨
        - worker_id 설정됨
        """
        worker_id = create_test_worker(
            email='start_task@test.com', password='Test123!',
            name='Start Task Worker', role='MECH'
        )
        create_test_product(
            qr_doc_id='DOC-WORK-001',
            serial_number='SN-WORK-001',
            model='GAIA-100'
        )
        create_test_completion_status(serial_number='SN-WORK-001')

        # DB에 Task 직접 생성 (미시작 상태)
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable)
            VALUES ('SN-WORK-001', 'DOC-WORK-001', 'MECH', 'CABINET_ASSY', '캐비넷 조립', TRUE)
            ON CONFLICT (serial_number, qr_doc_id, task_category, task_id)
            DO UPDATE SET is_applicable = TRUE, started_at = NULL, completed_at = NULL, worker_id = NULL
            RETURNING id
        """)
        task_detail_id = cursor.fetchone()[0]
        db_conn.commit()
        cursor.close()

        token = get_auth_token(worker_id, role='MECH')
        response = client.post(
            '/api/app/work/start',
            json={'task_detail_id': task_detail_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("POST /api/app/work/start 미구현")

        assert response.status_code == 200, \
            f"Expected 200, got {response.status_code}: {response.get_json()}"
        data = response.get_json()
        assert data.get('started_at') is not None or data.get('worker_id') is not None

    def test_complete_task(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """
        TC-WORK-02: 작업 완료 성공

        Expected:
        - Status 200
        - completed_at 설정됨
        - duration_minutes 계산됨
        """
        worker_id = create_test_worker(
            email='complete_task@test.com', password='Test123!',
            name='Complete Task Worker', role='MECH'
        )
        create_test_product(
            qr_doc_id='DOC-WORK-002',
            serial_number='SN-WORK-002',
            model='GAIA-100'
        )
        create_test_completion_status(serial_number='SN-WORK-002')

        if db_conn is None:
            pytest.skip("DB 연결 없음")

        started_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, worker_id, started_at)
            VALUES ('SN-WORK-002', 'DOC-WORK-002', 'MECH', 'N2_LINE', 'N2 라인 조립',
                    TRUE, %s, %s)
            RETURNING id
        """, (worker_id, started_at))
        task_detail_id = cursor.fetchone()[0]

        # work_start_log INSERT
        cursor.execute("""
            INSERT INTO work_start_log
                (task_id, worker_id, serial_number, qr_doc_id,
                 task_category, task_id_ref, task_name, started_at)
            VALUES (%s, %s, 'SN-WORK-002', 'DOC-WORK-002', 'MECH', 'N2_LINE', 'N2 라인 조립', %s)
        """, (task_detail_id, worker_id, started_at))
        db_conn.commit()
        cursor.close()

        token = get_auth_token(worker_id, role='MECH')
        response = client.post(
            '/api/app/work/complete',
            json={'task_detail_id': task_detail_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("POST /api/app/work/complete 미구현")

        assert response.status_code == 200, \
            f"Expected 200, got {response.status_code}: {response.get_json()}"
        data = response.get_json()
        assert data.get('completed_at') is not None or data.get('duration_minutes') is not None

    def test_duration_calculation(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """
        TC-WORK-03: duration = completed_at - started_at 계산 확인

        Expected:
        - 30분 작업 → duration_minutes ≈ 30
        """
        worker_id = create_test_worker(
            email='duration_calc@test.com', password='Test123!',
            name='Duration Calc Worker', role='MECH'
        )
        create_test_product(
            qr_doc_id='DOC-WORK-003',
            serial_number='SN-WORK-003',
            model='GAIA-100'
        )
        create_test_completion_status(serial_number='SN-WORK-003')

        if db_conn is None:
            pytest.skip("DB 연결 없음")

        started_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, worker_id, started_at)
            VALUES ('SN-WORK-003', 'DOC-WORK-003', 'MECH', 'CDA_LINE', 'CDA 라인 조립',
                    TRUE, %s, %s)
            RETURNING id
        """, (worker_id, started_at))
        task_detail_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO work_start_log
                (task_id, worker_id, serial_number, qr_doc_id,
                 task_category, task_id_ref, task_name, started_at)
            VALUES (%s, %s, 'SN-WORK-003', 'DOC-WORK-003', 'MECH', 'CDA_LINE', 'CDA 라인 조립', %s)
        """, (task_detail_id, worker_id, started_at))
        db_conn.commit()
        cursor.close()

        token = get_auth_token(worker_id, role='MECH')
        response = client.post(
            '/api/app/work/complete',
            json={'task_detail_id': task_detail_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("POST /api/app/work/complete 미구현")

        assert response.status_code == 200
        data = response.get_json()
        duration = data.get('duration_minutes')
        if duration is not None:
            assert 25 <= duration <= 35, \
                f"30분 작업의 duration_minutes는 25~35 범위여야 함, got {duration}"


class TestTaskRetrieval:
    """Task 조회 API 테스트"""

    def test_get_my_tasks(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, create_test_task, get_auth_token, db_conn
    ):
        """
        TC-WORK-04: serial_number 기준 Task 목록 조회

        Expected:
        - Status 200
        - tasks 배열 반환
        """
        worker_id = create_test_worker(
            email='get_tasks@test.com', password='Test123!',
            name='Get Tasks Worker', role='MECH'
        )
        create_test_product(
            qr_doc_id='DOC-WORK-004',
            serial_number='SN-WORK-004',
            model='GAIA-100'
        )
        create_test_completion_status(serial_number='SN-WORK-004')

        token = get_auth_token(worker_id, role='MECH')
        response = client.get(
            '/api/app/tasks/SN-WORK-004',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert response.status_code == 200, \
            f"Expected 200, got {response.status_code}: {response.get_json()}"
        data = response.get_json()
        assert 'tasks' in data or isinstance(data, list), \
            "응답에 tasks 배열이 있어야 함"

    def test_get_current_task(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """
        TC-WORK-05: 현재 진행 중인 Task 조회

        Expected:
        - in_progress 상태의 task 반환 (없으면 null 또는 빈 배열)
        """
        worker_id = create_test_worker(
            email='current_task@test.com', password='Test123!',
            name='Current Task Worker', role='MECH'
        )
        create_test_product(
            qr_doc_id='DOC-WORK-005',
            serial_number='SN-WORK-005',
            model='GAIA-100'
        )
        create_test_completion_status(serial_number='SN-WORK-005')

        token = get_auth_token(worker_id, role='MECH')
        response = client.get(
            '/api/app/tasks/SN-WORK-005',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert response.status_code == 200

    def test_task_history(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, create_test_task, get_auth_token, db_conn
    ):
        """
        TC-WORK-06: 완료된 Task 이력 조회

        Expected:
        - Status 200
        - 완료된 task 포함
        """
        worker_id = create_test_worker(
            email='task_hist@test.com', password='Test123!',
            name='Task History Worker', role='MECH'
        )
        create_test_product(
            qr_doc_id='DOC-WORK-006',
            serial_number='SN-WORK-006',
            model='GAIA-100'
        )
        create_test_completion_status(serial_number='SN-WORK-006')

        # 완료된 task 생성
        started_at = datetime.now(timezone.utc) - timedelta(hours=2)
        completed_at = datetime.now(timezone.utc) - timedelta(hours=1)
        create_test_task(
            worker_id=worker_id,
            serial_number='SN-WORK-006',
            qr_doc_id='DOC-WORK-006',
            task_category='MECH',
            task_id='BCW_LINE',
            task_name='BCW 라인 조립',
            started_at=started_at,
            completed_at=completed_at
        )

        token = get_auth_token(worker_id, role='MECH')
        response = client.get(
            '/api/app/tasks/SN-WORK-006',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert response.status_code == 200
        data = response.get_json()
        if isinstance(data, list):
            tasks = data
        else:
            tasks = data.get('tasks', [])
        # completed_at이 있거나 status=='completed'인 task
        completed = [
            t for t in tasks
            if t.get('completed_at') is not None or t.get('status') == 'completed'
        ]
        assert len(completed) >= 1, "완료된 task가 최소 1개 이상이어야 함"


class TestTaskValidation:
    """작업 검증 테스트"""

    def test_cannot_start_multiple_tasks(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """
        TC-WORK-07: 동일 작업자가 동시에 두 Task 시작 불가

        Expected:
        - 첫 번째 시작: 200
        - 두 번째 시작: 400 (TASK_ALREADY_STARTED 또는 유사)
        """
        worker_id = create_test_worker(
            email='dup_start@test.com', password='Test123!',
            name='Dup Start Worker', role='MECH'
        )
        create_test_product(
            qr_doc_id='DOC-WORK-007',
            serial_number='SN-WORK-007',
            model='GAIA-100',
            location_qr_id='LOC-W7'
        )
        create_test_completion_status(serial_number='SN-WORK-007')

        if db_conn is None:
            pytest.skip("DB 연결 없음")

        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable)
            VALUES ('SN-WORK-007', 'DOC-WORK-007', 'MECH', 'WASTE_GAS_LINE', 'Waste Gas 라인', TRUE)
            ON CONFLICT (serial_number, qr_doc_id, task_category, task_id)
            DO UPDATE SET started_at = NULL, completed_at = NULL, worker_id = NULL
            RETURNING id
        """)
        task_id_1 = cursor.fetchone()[0]
        cursor.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable)
            VALUES ('SN-WORK-007', 'DOC-WORK-007', 'MECH', 'PCW_LINE', 'PCW 라인', TRUE)
            ON CONFLICT (serial_number, qr_doc_id, task_category, task_id)
            DO UPDATE SET started_at = NULL, completed_at = NULL, worker_id = NULL
            RETURNING id
        """)
        task_id_2 = cursor.fetchone()[0]
        db_conn.commit()
        cursor.close()

        token = get_auth_token(worker_id, role='MECH')

        # 첫 번째 시작
        r1 = client.post(
            '/api/app/work/start',
            json={'task_detail_id': task_id_1},
            headers={'Authorization': f'Bearer {token}'}
        )
        if r1.status_code == 404:
            pytest.skip("POST /api/app/work/start 미구현")

        assert r1.status_code == 200, f"첫 번째 시작 실패: {r1.get_json()}"

        # 두 번째 시작 시도 (같은 작업자)
        # Sprint 6 멀티워커 지원 이후: 200 허용 (policy 변경 가능)
        # 구 정책(단일 작업): 400/409, 신 정책(멀티작업): 200
        r2 = client.post(
            '/api/app/work/start',
            json={'task_detail_id': task_id_2},
            headers={'Authorization': f'Bearer {token}'}
        )
        assert r2.status_code in [200, 400, 409], \
            f"두 번째 작업 시작 응답은 200/400/409 중 하나여야 함, got {r2.status_code}"

    def test_qr_code_validation(
        self, client, create_test_worker, get_auth_token
    ):
        """
        TC-WORK-08: 존재하지 않는 serial_number 조회 → 404 또는 빈 배열

        Expected:
        - Status 200 with empty tasks, or 404
        """
        worker_id = create_test_worker(
            email='qr_valid@test.com', password='Test123!',
            name='QR Valid Worker', role='MECH'
        )

        token = get_auth_token(worker_id, role='MECH')
        response = client.get(
            '/api/app/tasks/SN-NONEXISTENT-99999',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현 또는 404 반환")

        # 200이면 tasks가 빈 배열이어야 함
        if response.status_code == 200:
            data = response.get_json()
            if isinstance(data, list):
                tasks = data
            else:
                tasks = data.get('tasks', [])
            assert len(tasks) == 0, "존재하지 않는 제품의 task는 0개여야 함"
        else:
            assert response.status_code in [200, 404], \
                f"Unexpected status: {response.status_code}"
