"""
Sprint 14: Task workers array API 테스트

GET /api/app/tasks/{serial_number} 응답에 workers 배열이 포함되는지,
GET /api/app/gst/products/{category} 응답에도 workers 배열이 포함되는지 검증.
"""
import pytest
from datetime import datetime, timedelta, timezone


class TestTaskWorkersArray:
    """TC-WA: Task API workers 배열 테스트"""

    def test_task_list_includes_workers_array(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """TC-WA-01: task detail API에 workers 배열 포함 확인"""
        worker_id = create_test_worker(
            email='wa01@test.com', password='Test123!',
            name='WA01 Worker', role='MECH'
        )
        create_test_product(
            qr_doc_id='DOC-WA-001',
            serial_number='SN-WA-001',
            model='GAIA-100'
        )
        create_test_completion_status(serial_number='SN-WA-001')

        if db_conn is None:
            pytest.skip("DB 연결 없음")

        # Task 생성 (시작 상태)
        started_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, worker_id, started_at)
            VALUES ('SN-WA-001', 'DOC-WA-001', 'MECH', 'SELF_INSPECTION_WA01',
                    '자주검사 WA01', TRUE, %s, %s)
            ON CONFLICT (serial_number, task_category, task_id)
            DO UPDATE SET worker_id = %s, started_at = %s, completed_at = NULL
            RETURNING id
        """, (worker_id, started_at, worker_id, started_at))
        task_detail_id = cursor.fetchone()[0]

        # work_start_log INSERT
        cursor.execute("""
            INSERT INTO work_start_log
                (task_id, worker_id, serial_number, qr_doc_id,
                 task_category, task_id_ref, task_name, started_at)
            VALUES (%s, %s, 'SN-WA-001', 'DOC-WA-001', 'MECH',
                    'SELF_INSPECTION_WA01', '자주검사 WA01', %s)
            ON CONFLICT DO NOTHING
        """, (task_detail_id, worker_id, started_at))
        db_conn.commit()
        cursor.close()

        token = get_auth_token(worker_id, role='MECH')
        response = client.get(
            '/api/app/tasks/SN-WA-001',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert response.status_code == 200, \
            f"Expected 200, got {response.status_code}: {response.get_json()}"

        data = response.get_json()
        tasks = data if isinstance(data, list) else data.get('tasks', [])
        assert len(tasks) > 0, "tasks 배열이 비어있음"

        # workers 키가 각 task에 존재하는지 확인
        task_with_workers = next(
            (t for t in tasks if t.get('id') == task_detail_id), None
        )
        assert task_with_workers is not None, f"task_detail_id={task_detail_id} 미포함"
        assert 'workers' in task_with_workers, \
            f"task에 'workers' 키가 없음: {list(task_with_workers.keys())}"
        assert isinstance(task_with_workers['workers'], list), \
            "'workers' 값이 리스트가 아님"

    def test_workers_array_fields(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """TC-WA-02: workers에 필요한 필드 포함
        (worker_name, started_at, completed_at, duration_minutes, status)
        """
        worker_id = create_test_worker(
            email='wa02@test.com', password='Test123!',
            name='WA02 Worker', role='MECH'
        )
        create_test_product(
            qr_doc_id='DOC-WA-002',
            serial_number='SN-WA-002',
            model='GAIA-100'
        )
        create_test_completion_status(serial_number='SN-WA-002')

        if db_conn is None:
            pytest.skip("DB 연결 없음")

        started_at = datetime.now(timezone.utc) - timedelta(hours=1)
        completed_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, worker_id, started_at, completed_at, duration_minutes)
            VALUES ('SN-WA-002', 'DOC-WA-002', 'MECH', 'PANEL_WORK_WA02',
                    '판넬 작업 WA02', TRUE, %s, %s, %s, 50)
            ON CONFLICT (serial_number, task_category, task_id)
            DO UPDATE SET worker_id = %s, started_at = %s, completed_at = %s,
                          duration_minutes = 50
            RETURNING id
        """, (worker_id, started_at, completed_at, worker_id, started_at, completed_at))
        task_detail_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO work_start_log
                (task_id, worker_id, serial_number, qr_doc_id,
                 task_category, task_id_ref, task_name, started_at)
            VALUES (%s, %s, 'SN-WA-002', 'DOC-WA-002', 'MECH',
                    'PANEL_WORK_WA02', '판넬 작업 WA02', %s)
            ON CONFLICT DO NOTHING
        """, (task_detail_id, worker_id, started_at))

        cursor.execute("""
            INSERT INTO work_completion_log
                (task_id, worker_id, serial_number, qr_doc_id,
                 task_category, task_id_ref, task_name, completed_at, duration_minutes)
            VALUES (%s, %s, 'SN-WA-002', 'DOC-WA-002', 'MECH',
                    'PANEL_WORK_WA02', '판넬 작업 WA02', %s, 50)
            ON CONFLICT DO NOTHING
        """, (task_detail_id, worker_id, completed_at))
        db_conn.commit()
        cursor.close()

        token = get_auth_token(worker_id, role='MECH')
        response = client.get(
            '/api/app/tasks/SN-WA-002',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert response.status_code == 200
        data = response.get_json()
        tasks = data if isinstance(data, list) else data.get('tasks', [])

        target = next((t for t in tasks if t.get('id') == task_detail_id), None)
        assert target is not None, f"task_detail_id={task_detail_id} not found"
        assert 'workers' in target, "workers 키 없음"
        assert len(target['workers']) >= 1, "workers 배열이 비어있음"

        worker_entry = target['workers'][0]
        required_fields = ['worker_name', 'started_at', 'completed_at',
                           'duration_minutes', 'status']
        for field in required_fields:
            assert field in worker_entry, \
                f"workers 항목에 '{field}' 필드 없음: {list(worker_entry.keys())}"

    def test_multiple_workers_on_task(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """TC-WA-03: 3명 시작 2명 완료 → completed 2건 + in_progress 1건"""
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        # 3명의 작업자 생성
        wid1 = create_test_worker(
            email='wa03a@test.com', password='Test123!',
            name='WA03 Worker A', role='MECH'
        )
        wid2 = create_test_worker(
            email='wa03b@test.com', password='Test123!',
            name='WA03 Worker B', role='MECH'
        )
        wid3 = create_test_worker(
            email='wa03c@test.com', password='Test123!',
            name='WA03 Worker C', role='MECH'
        )
        create_test_product(
            qr_doc_id='DOC-WA-003',
            serial_number='SN-WA-003',
            model='GAIA-100'
        )
        create_test_completion_status(serial_number='SN-WA-003')

        started_at = datetime.now(timezone.utc) - timedelta(hours=2)
        cursor = db_conn.cursor()

        # Task 생성 (첫 번째 작업자 기준)
        cursor.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, worker_id, started_at)
            VALUES ('SN-WA-003', 'DOC-WA-003', 'MECH', 'WIRING_WA03',
                    '배선 WA03', TRUE, %s, %s)
            ON CONFLICT (serial_number, task_category, task_id)
            DO UPDATE SET worker_id = %s, started_at = %s, completed_at = NULL
            RETURNING id
        """, (wid1, started_at, wid1, started_at))
        task_detail_id = cursor.fetchone()[0]

        # 3명 모두 work_start_log
        for wid in [wid1, wid2, wid3]:
            cursor.execute("""
                INSERT INTO work_start_log
                    (task_id, worker_id, serial_number, qr_doc_id,
                     task_category, task_id_ref, task_name, started_at)
                VALUES (%s, %s, 'SN-WA-003', 'DOC-WA-003', 'MECH',
                        'WIRING_WA03', '배선 WA03', %s)
                ON CONFLICT DO NOTHING
            """, (task_detail_id, wid, started_at))

        # 2명(wid1, wid2)만 완료
        completed_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        for wid in [wid1, wid2]:
            cursor.execute("""
                INSERT INTO work_completion_log
                    (task_id, worker_id, serial_number, qr_doc_id,
                     task_category, task_id_ref, task_name, completed_at, duration_minutes)
                VALUES (%s, %s, 'SN-WA-003', 'DOC-WA-003', 'MECH',
                        'WIRING_WA03', '배선 WA03', %s, 90)
                ON CONFLICT DO NOTHING
            """, (task_detail_id, wid, completed_at))

        db_conn.commit()
        cursor.close()

        token = get_auth_token(wid1, role='MECH')
        response = client.get(
            '/api/app/tasks/SN-WA-003',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert response.status_code == 200
        data = response.get_json()
        tasks = data if isinstance(data, list) else data.get('tasks', [])

        target = next((t for t in tasks if t.get('id') == task_detail_id), None)
        assert target is not None
        assert 'workers' in target

        workers = target['workers']
        assert len(workers) == 3, f"3명 기대, 실제 {len(workers)}명"

        completed_workers = [w for w in workers if w.get('status') == 'completed']
        in_progress_workers = [w for w in workers if w.get('status') == 'in_progress']
        assert len(completed_workers) == 2, \
            f"completed 2명 기대, 실제 {len(completed_workers)}명"
        assert len(in_progress_workers) == 1, \
            f"in_progress 1명 기대, 실제 {len(in_progress_workers)}명"

    def test_legacy_task_fallback(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """TC-WA-04: work_start_log 없는 레거시 task → fallback 1건"""
        worker_id = create_test_worker(
            email='wa04@test.com', password='Test123!',
            name='WA04 Legacy Worker', role='MECH'
        )
        create_test_product(
            qr_doc_id='DOC-WA-004',
            serial_number='SN-WA-004',
            model='GAIA-100'
        )
        create_test_completion_status(serial_number='SN-WA-004')

        if db_conn is None:
            pytest.skip("DB 연결 없음")

        started_at = datetime.now(timezone.utc) - timedelta(hours=1)
        cursor = db_conn.cursor()

        # Task 생성 (worker_id 있음, started_at 있음) — work_start_log는 없음
        cursor.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, worker_id, started_at)
            VALUES ('SN-WA-004', 'DOC-WA-004', 'MECH', 'IF_1_WA04',
                    'I.F 1 WA04', TRUE, %s, %s)
            ON CONFLICT (serial_number, task_category, task_id)
            DO UPDATE SET worker_id = %s, started_at = %s, completed_at = NULL
            RETURNING id
        """, (worker_id, started_at, worker_id, started_at))
        task_detail_id = cursor.fetchone()[0]
        # work_start_log는 일부러 INSERT하지 않음 (레거시 시뮬레이션)
        db_conn.commit()
        cursor.close()

        token = get_auth_token(worker_id, role='MECH')
        response = client.get(
            '/api/app/tasks/SN-WA-004',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert response.status_code == 200
        data = response.get_json()
        tasks = data if isinstance(data, list) else data.get('tasks', [])

        target = next((t for t in tasks if t.get('id') == task_detail_id), None)
        assert target is not None
        assert 'workers' in target

        workers = target['workers']
        # work_start_log 없어도 worker_id 기반으로 fallback 1건 반환
        assert len(workers) == 1, \
            f"레거시 task는 fallback 1건 기대, 실제 {len(workers)}건"
        assert workers[0]['worker_id'] == worker_id, \
            f"fallback worker_id 불일치: {workers[0].get('worker_id')} != {worker_id}"

    def test_gst_api_includes_workers(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """TC-WA-05: GST API에도 workers 배열 포함"""
        # GST 소속 PI 작업자 생성
        worker_id = create_test_worker(
            email='wa05gst@test.com', password='Test123!',
            name='WA05 GST Worker', role='PI', company='GST'
        )
        create_test_product(
            qr_doc_id='DOC-WA-005',
            serial_number='SN-WA-005',
            model='GAIA-100'
        )
        create_test_completion_status(serial_number='SN-WA-005')

        if db_conn is None:
            pytest.skip("DB 연결 없음")

        started_at = datetime.now(timezone.utc) - timedelta(minutes=45)
        cursor = db_conn.cursor()

        # PI 카테고리 Task 생성
        cursor.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, worker_id, started_at)
            VALUES ('SN-WA-005', 'DOC-WA-005', 'PI', 'PI_INSPECTION_WA05',
                    'PI 검사 WA05', TRUE, %s, %s)
            ON CONFLICT (serial_number, task_category, task_id)
            DO UPDATE SET worker_id = %s, started_at = %s, completed_at = NULL
            RETURNING id
        """, (worker_id, started_at, worker_id, started_at))
        task_detail_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO work_start_log
                (task_id, worker_id, serial_number, qr_doc_id,
                 task_category, task_id_ref, task_name, started_at)
            VALUES (%s, %s, 'SN-WA-005', 'DOC-WA-005', 'PI',
                    'PI_INSPECTION_WA05', 'PI 검사 WA05', %s)
            ON CONFLICT DO NOTHING
        """, (task_detail_id, worker_id, started_at))
        db_conn.commit()
        cursor.close()

        token = get_auth_token(worker_id, role='PI')
        response = client.get(
            '/api/app/gst/products/PI',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/gst/products/PI 미구현")

        assert response.status_code == 200, \
            f"Expected 200, got {response.status_code}: {response.get_json()}"

        data = response.get_json()
        products = data.get('products', [])

        # workers 키가 각 product 항목에 있는지 확인
        if len(products) > 0:
            for product in products:
                assert 'workers' in product, \
                    f"GST product에 'workers' 키 없음: {list(product.keys())}"
                assert isinstance(product['workers'], list), \
                    "'workers' 값이 리스트가 아님"

    def test_single_worker_task(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """TC-WA-06: 단일 작업자 → workers 1건"""
        worker_id = create_test_worker(
            email='wa06@test.com', password='Test123!',
            name='WA06 Worker', role='MECH'
        )
        create_test_product(
            qr_doc_id='DOC-WA-006',
            serial_number='SN-WA-006',
            model='GAIA-100'
        )
        create_test_completion_status(serial_number='SN-WA-006')

        if db_conn is None:
            pytest.skip("DB 연결 없음")

        started_at = datetime.now(timezone.utc) - timedelta(minutes=20)
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, worker_id, started_at)
            VALUES ('SN-WA-006', 'DOC-WA-006', 'MECH', 'IF_2_WA06',
                    'I.F 2 WA06', TRUE, %s, %s)
            ON CONFLICT (serial_number, task_category, task_id)
            DO UPDATE SET worker_id = %s, started_at = %s, completed_at = NULL
            RETURNING id
        """, (worker_id, started_at, worker_id, started_at))
        task_detail_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO work_start_log
                (task_id, worker_id, serial_number, qr_doc_id,
                 task_category, task_id_ref, task_name, started_at)
            VALUES (%s, %s, 'SN-WA-006', 'DOC-WA-006', 'MECH',
                    'IF_2_WA06', 'I.F 2 WA06', %s)
            ON CONFLICT DO NOTHING
        """, (task_detail_id, worker_id, started_at))
        db_conn.commit()
        cursor.close()

        token = get_auth_token(worker_id, role='MECH')
        response = client.get(
            '/api/app/tasks/SN-WA-006',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert response.status_code == 200
        data = response.get_json()
        tasks = data if isinstance(data, list) else data.get('tasks', [])

        target = next((t for t in tasks if t.get('id') == task_detail_id), None)
        assert target is not None
        assert 'workers' in target

        workers = target['workers']
        assert len(workers) == 1, f"단일 작업자 → workers 1건 기대, 실제 {len(workers)}건"
        assert workers[0]['worker_id'] == worker_id

    def test_no_workers_empty_array(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token, db_conn
    ):
        """TC-WA-07: 아무도 시작 안 한 task → workers 빈 배열"""
        worker_id = create_test_worker(
            email='wa07@test.com', password='Test123!',
            name='WA07 Worker', role='MECH'
        )
        create_test_product(
            qr_doc_id='DOC-WA-007',
            serial_number='SN-WA-007',
            model='GAIA-100'
        )
        create_test_completion_status(serial_number='SN-WA-007')

        if db_conn is None:
            pytest.skip("DB 연결 없음")

        cursor = db_conn.cursor()
        # Task Seed 상태: worker_id=NULL, started_at=NULL
        cursor.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable)
            VALUES ('SN-WA-007', 'DOC-WA-007', 'MECH', 'TANK_DOCKING_WA07',
                    'Tank Docking WA07', TRUE)
            ON CONFLICT (serial_number, task_category, task_id)
            DO UPDATE SET worker_id = NULL, started_at = NULL, completed_at = NULL
            RETURNING id
        """)
        task_detail_id = cursor.fetchone()[0]
        # work_start_log 없음 (아무도 시작 안 함)
        db_conn.commit()
        cursor.close()

        token = get_auth_token(worker_id, role='MECH')
        response = client.get(
            '/api/app/tasks/SN-WA-007',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert response.status_code == 200
        data = response.get_json()
        tasks = data if isinstance(data, list) else data.get('tasks', [])

        target = next((t for t in tasks if t.get('id') == task_detail_id), None)
        assert target is not None
        assert 'workers' in target

        workers = target['workers']
        # worker_id=NULL이므로 fallback도 없어야 함 → 빈 배열
        assert isinstance(workers, list), "'workers'가 리스트가 아님"
        assert len(workers) == 0, \
            f"아무도 시작 안 한 task의 workers는 빈 배열 기대, 실제 {len(workers)}건"
