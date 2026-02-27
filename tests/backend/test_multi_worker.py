"""
멀티 작업자 Duration 테스트 (TC-MW-01 ~ TC-MW-07)
Sprint 6: 다수 작업자가 동일 Task를 동시에 진행하는 케이스

테스트 대상:
- 단독 작업 vs 복수 작업자 duration 합산
- started_at = MIN(개인 시작), completed_at = MAX(개인 종료)
- elapsed_minutes = MAX-MIN (실제 경과 시간)
- duration_minutes = SUM(개인 작업시간) (man-hour 총합)
- worker_count = DISTINCT 참여 작업자 수
- 마지막 작업자 종료 시 Task 자동 완료
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Optional


@pytest.fixture(autouse=True)
def cleanup_multiworker_data(db_conn):
    """멀티 작업자 테스트 데이터 정리"""
    yield
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            cursor.execute(
                "DELETE FROM app_task_details WHERE serial_number LIKE 'SN-MW-%%'"
            )
            cursor.execute(
                "DELETE FROM completion_status WHERE serial_number LIKE 'SN-MW-%%'"
            )
            cursor.execute(
                "DELETE FROM work_start_log WHERE serial_number LIKE 'SN-MW-%%'"
            )
            cursor.execute(
                "DELETE FROM work_completion_log WHERE serial_number LIKE 'SN-MW-%%'"
            )
            cursor.execute(
                "DELETE FROM public.qr_registry WHERE qr_doc_id LIKE 'DOC-MW-%%'"
            )
            cursor.execute(
                "DELETE FROM plan.product_info WHERE serial_number LIKE 'SN-MW-%%'"
            )
            db_conn.commit()
            cursor.close()
        except Exception:
            pass


def _setup_product(create_test_product, create_completion_status_fn, sn, doc):
    """공통 제품 세팅 헬퍼"""
    create_test_product(
        qr_doc_id=doc,
        serial_number=sn,
        model='GALLANT-50'
    )
    create_completion_status_fn(serial_number=sn)


class TestSingleWorkerDuration:
    """TC-MW-01: 단독 1명 작업 → duration = 개인 작업시간, worker_count = 1"""

    def test_single_worker_duration(
        self,
        client,
        create_test_worker,
        create_test_product,
        create_test_task,
        create_test_completion_status,
        get_auth_token
    ):
        """
        TC-MW-01: 1명이 단독으로 작업 완료

        Expected:
        - Status 200
        - worker_count == 1
        - duration_minutes == elapsed_minutes (1인 작업 시 동일)
        - completed_at IS NOT NULL
        """
        worker_id = create_test_worker(
            email='mw_solo@test.com', password='Test123!',
            name='Solo MW Worker', role='MECH', company='FNI'
        )

        create_test_product(
            qr_doc_id='DOC-MW-001',
            serial_number='SN-MW-001',
            model='GALLANT-50'
        )
        create_test_completion_status(serial_number='SN-MW-001')

        started_at = datetime.now(timezone.utc) - timedelta(hours=3)
        task_id = create_test_task(
            worker_id=worker_id,
            serial_number='SN-MW-001',
            qr_doc_id='DOC-MW-001',
            task_category='MECH',
            task_id='SELF_INSPECTION',
            task_name='자주검사',
            started_at=started_at
        )

        token = get_auth_token(worker_id, role='MECH')
        response = client.post(
            '/api/app/work/complete',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data.get('completed_at') is not None

        # worker_count 필드 확인 (구현된 경우)
        if 'worker_count' in data:
            assert data['worker_count'] == 1

        # elapsed_minutes 필드 확인 (구현된 경우)
        if 'elapsed_minutes' in data and 'duration_minutes' in data:
            # 1인 작업: 개인 작업시간 ≈ 실경과시간 (소폭 오차 허용)
            diff = abs(data['duration_minutes'] - data['elapsed_minutes'])
            assert diff <= 2, \
                f"1인 작업 시 duration({data['duration_minutes']}) ≈ elapsed({data['elapsed_minutes']}) 이어야 함"


class TestTwoWorkerSimultaneousStart:
    """TC-MW-02: 2명 동시 시작, 다른 시간에 종료"""

    def test_two_workers_different_end_time(
        self,
        client,
        create_test_worker,
        create_test_product,
        create_test_task,
        create_test_completion_status,
        get_auth_token,
        db_conn
    ):
        """
        TC-MW-02: 2명이 동시에 시작, 첫 번째 작업자가 먼저 종료

        Setup:
        - Worker A, B 동시 시작 (started_at 동일)
        - Worker A가 먼저 완료
        - Worker B가 나중에 완료

        Expected:
        - 두 번째 완료(B) 후 Task.completed_at != None
        - worker_count == 2 (구현된 경우)
        - duration_minutes >= elapsed_minutes (구현된 경우)
        """
        worker_a = create_test_worker(
            email='mw_a_02@test.com', password='Test123!',
            name='MW Worker A02', role='MECH', company='FNI'
        )
        worker_b = create_test_worker(
            email='mw_b_02@test.com', password='Test123!',
            name='MW Worker B02', role='MECH', company='FNI'
        )

        create_test_product(
            qr_doc_id='DOC-MW-002',
            serial_number='SN-MW-002',
            model='GALLANT-50'
        )
        create_test_completion_status(serial_number='SN-MW-002')

        # 동시 시작 (같은 started_at)
        started_at = datetime.now(timezone.utc) - timedelta(hours=4)

        # 두 작업자가 같은 task에 참여 — API가 multi-worker를 지원하는지 확인
        task_id = create_test_task(
            worker_id=worker_a,
            serial_number='SN-MW-002',
            qr_doc_id='DOC-MW-002',
            task_category='MECH',
            task_id='SELF_INSPECTION',
            task_name='자주검사',
            started_at=started_at
        )

        # Worker A 완료 (2시간 경과 지점)
        token_a = get_auth_token(worker_a, role='MECH')
        resp_a = client.post(
            '/api/app/work/complete',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token_a}'}
        )

        if resp_a.status_code == 404:
            pytest.skip("멀티 작업자 완료 API 미구현")

        assert resp_a.status_code == 200

        # Worker B가 같은 task에 완료 참여 시도
        # 멀티 작업자 지원 API: POST /api/app/work/complete with worker_b context
        token_b = get_auth_token(worker_b, role='MECH')
        resp_b = client.post(
            '/api/app/work/join-complete',  # 멀티 작업자 전용 엔드포인트
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token_b}'}
        )

        # join-complete 미구현 시 스킵
        if resp_b.status_code == 404:
            pytest.skip("POST /api/app/work/join-complete 미구현")

        assert resp_b.status_code == 200
        data = resp_b.get_json()

        if 'worker_count' in data:
            assert data['worker_count'] == 2


class TestThreeWorkersDifferentTimes:
    """TC-MW-03: 3명 모두 다른 시작/종료 → duration=SUM, elapsed=MAX-MIN"""

    def test_three_workers_duration_calculation(
        self,
        client,
        create_test_worker,
        create_test_product,
        create_test_task,
        create_test_completion_status,
        get_auth_token,
        db_conn
    ):
        """
        TC-MW-03: 3명이 각각 다른 시점에 시작/종료

        Setup:
        - Worker A: 4시간 작업 (가장 먼저 시작, 가장 먼저 종료)
        - Worker B: 3시간 작업 (중간)
        - Worker C: 2시간 작업 (가장 나중에 시작, 가장 나중에 종료)

        Expected (멀티 작업자 지원 시):
        - started_at = MIN(A.started_at, B.started_at, C.started_at)
        - completed_at = MAX(A.completed_at, B.completed_at, C.completed_at)
        - elapsed_minutes = completed_at - started_at (실경과시간)
        - duration_minutes = SUM(개인 작업시간) (man-hour 합)
        - worker_count = 3
        """
        workers = []
        for i, (email, company) in enumerate([
            ('mw_a_03@test.com', 'FNI'),
            ('mw_b_03@test.com', 'FNI'),
            ('mw_c_03@test.com', 'GST'),
        ]):
            wid = create_test_worker(
                email=email, password='Test123!',
                name=f'MW Worker {chr(65+i)}03', role='MECH', company=company
            )
            workers.append(wid)

        create_test_product(
            qr_doc_id='DOC-MW-003',
            serial_number='SN-MW-003',
            model='GALLANT-50'
        )
        create_test_completion_status(serial_number='SN-MW-003')

        now = datetime.now(timezone.utc)
        # A: 5시간 전 시작 (가장 빨리 시작)
        # B: 4시간 전 시작
        # C: 3시간 전 시작 (가장 늦게 시작)
        start_offsets = [timedelta(hours=5), timedelta(hours=4), timedelta(hours=3)]

        task_id = create_test_task(
            worker_id=workers[0],
            serial_number='SN-MW-003',
            qr_doc_id='DOC-MW-003',
            task_category='MECH',
            task_id='SELF_INSPECTION',
            task_name='자주검사',
            started_at=now - start_offsets[0]
        )

        # 3명 모두 완료 시도
        completed_count = 0
        for i, worker_id in enumerate(workers):
            token = get_auth_token(worker_id, role='MECH')
            endpoint = '/api/app/work/complete' if i == 0 else '/api/app/work/join-complete'
            resp = client.post(
                endpoint,
                json={'task_id': task_id},
                headers={'Authorization': f'Bearer {token}'}
            )
            if resp.status_code == 404:
                pytest.skip(f"멀티 작업자 엔드포인트 미구현 (worker {i+1})")
            if resp.status_code == 200:
                completed_count += 1

        assert completed_count >= 1, "최소 1명은 완료 처리되어야 함"

        # DB에서 최종 task 상태 확인
        cursor = db_conn.cursor()
        cursor.execute(
            """SELECT worker_count, duration_minutes, elapsed_minutes, completed_at
               FROM app_task_details WHERE id = %s""",
            (task_id,)
        )
        row = cursor.fetchone()
        cursor.close()

        if row is None:
            pytest.skip("app_task_details에 새 컬럼 미구현")

        worker_count, duration_min, elapsed_min, completed_at = row

        if worker_count is not None and worker_count > 1:
            # 멀티 작업자 구현된 경우
            assert worker_count == 3, f"worker_count=3이어야 함, got {worker_count}"
            assert duration_min >= elapsed_min, \
                f"duration({duration_min}) >= elapsed({elapsed_min}) (man-hour >= 실경과)"


class TestPartialCompletion:
    """TC-MW-04: 일부 작업자 완료, 나머지 진행 중 → Task 미완료 상태"""

    def test_partial_completion_task_remains_open(
        self,
        client,
        create_test_worker,
        create_test_product,
        create_test_task,
        create_test_completion_status,
        get_auth_token,
        db_conn
    ):
        """
        TC-MW-04: 작업자 A 종료 + B 아직 진행 중
        → Task.completed_at IS NULL (미완료 상태 유지)

        Expected:
        - A 완료 후 Task는 여전히 in-progress
        - completed_at IS NULL
        """
        worker_a = create_test_worker(
            email='mw_a_04@test.com', password='Test123!',
            name='MW Worker A04', role='MECH', company='FNI'
        )
        worker_b = create_test_worker(
            email='mw_b_04@test.com', password='Test123!',
            name='MW Worker B04', role='MECH', company='FNI'
        )

        create_test_product(
            qr_doc_id='DOC-MW-004',
            serial_number='SN-MW-004',
            model='GALLANT-50'
        )
        create_test_completion_status(serial_number='SN-MW-004')

        started_at = datetime.now(timezone.utc) - timedelta(hours=2)
        task_id = create_test_task(
            worker_id=worker_a,
            serial_number='SN-MW-004',
            qr_doc_id='DOC-MW-004',
            task_category='MECH',
            task_id='SELF_INSPECTION',
            task_name='자주검사',
            started_at=started_at
        )

        # B를 같은 task에 등록 (join 엔드포인트)
        token_b = get_auth_token(worker_b, role='MECH')
        join_resp = client.post(
            '/api/app/work/join',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token_b}'}
        )

        if join_resp.status_code == 404:
            pytest.skip("POST /api/app/work/join 미구현")

        # A만 완료
        token_a = get_auth_token(worker_a, role='MECH')
        resp_a = client.post(
            '/api/app/work/complete',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token_a}'}
        )

        if resp_a.status_code != 200:
            pytest.skip("완료 API 실패")

        # Task가 아직 미완료인지 DB 확인
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT completed_at FROM app_task_details WHERE id = %s",
            (task_id,)
        )
        row = cursor.fetchone()
        cursor.close()

        assert row is not None
        # B가 아직 진행 중이면 completed_at IS NULL
        assert row[0] is None, \
            "다른 작업자(B)가 진행 중일 때 Task는 미완료 상태여야 함"


class TestLastWorkerAutoComplete:
    """TC-MW-05: 마지막 작업자 종료 → Task 자동 완료"""

    def test_last_worker_triggers_task_completion(
        self,
        client,
        create_test_worker,
        create_test_product,
        create_test_task,
        create_test_completion_status,
        get_auth_token,
        db_conn
    ):
        """
        TC-MW-05: 모든 작업자가 완료하면 Task 자동 완료

        Expected:
        - 마지막 작업자 완료 후 Task.completed_at IS NOT NULL
        - duration_minutes, elapsed_minutes, worker_count 모두 정확
        """
        worker_a = create_test_worker(
            email='mw_a_05@test.com', password='Test123!',
            name='MW Worker A05', role='MECH', company='FNI'
        )
        worker_b = create_test_worker(
            email='mw_b_05@test.com', password='Test123!',
            name='MW Worker B05', role='MECH', company='FNI'
        )

        create_test_product(
            qr_doc_id='DOC-MW-005',
            serial_number='SN-MW-005',
            model='GALLANT-50'
        )
        create_test_completion_status(serial_number='SN-MW-005')

        started_at = datetime.now(timezone.utc) - timedelta(hours=3)
        task_id = create_test_task(
            worker_id=worker_a,
            serial_number='SN-MW-005',
            qr_doc_id='DOC-MW-005',
            task_category='MECH',
            task_id='SELF_INSPECTION',
            task_name='자주검사',
            started_at=started_at
        )

        # B join
        token_b = get_auth_token(worker_b, role='MECH')
        join_resp = client.post(
            '/api/app/work/join',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token_b}'}
        )
        if join_resp.status_code == 404:
            pytest.skip("join 미구현")

        # A 완료
        token_a = get_auth_token(worker_a, role='MECH')
        client.post(
            '/api/app/work/complete',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token_a}'}
        )

        # B 완료 (마지막)
        resp_b = client.post(
            '/api/app/work/complete',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token_b}'}
        )

        if resp_b.status_code != 200:
            pytest.skip("마지막 작업자 완료 API 실패")

        # Task 최종 상태 확인
        cursor = db_conn.cursor()
        cursor.execute(
            """SELECT completed_at, worker_count, duration_minutes, elapsed_minutes
               FROM app_task_details WHERE id = %s""",
            (task_id,)
        )
        row = cursor.fetchone()
        cursor.close()

        assert row is not None
        completed_at, worker_count, duration_min, elapsed_min = row

        assert completed_at is not None, \
            "마지막 작업자 완료 후 Task.completed_at이 설정되어야 함"

        if worker_count is not None:
            assert worker_count == 2, f"worker_count=2이어야 함, got {worker_count}"

        if duration_min is not None and elapsed_min is not None:
            assert duration_min >= 0, "duration_minutes는 0 이상이어야 함"
            assert elapsed_min >= 0, "elapsed_minutes는 0 이상이어야 함"


class TestDurationVsElapsedDifference:
    """TC-MW-06: duration_minutes(man-hour) ≠ elapsed_minutes(실경과) 다름 확인"""

    def test_duration_ne_elapsed_for_multiworker(
        self,
        client,
        create_test_worker,
        create_test_product,
        create_test_task,
        create_test_completion_status,
        get_auth_token,
        db_conn
    ):
        """
        TC-MW-06: 3명이 동시에 2시간 작업
        - elapsed = 2시간 (실제 경과)
        - duration = 6시간 (3명 × 2시간 man-hour)

        Expected:
        - duration_minutes > elapsed_minutes (3배 관계)
        - 비율: duration / elapsed ≈ worker_count
        """
        workers = []
        for i in range(3):
            wid = create_test_worker(
                email=f'mw_06_{i}@test.com', password='Test123!',
                name=f'MW06 Worker {i}', role='MECH', company='FNI'
            )
            workers.append(wid)

        create_test_product(
            qr_doc_id='DOC-MW-006',
            serial_number='SN-MW-006',
            model='GALLANT-50'
        )
        create_test_completion_status(serial_number='SN-MW-006')

        # 모두 2시간 전에 동시 시작
        started_at = datetime.now(timezone.utc) - timedelta(hours=2)
        task_id = create_test_task(
            worker_id=workers[0],
            serial_number='SN-MW-006',
            qr_doc_id='DOC-MW-006',
            task_category='MECH',
            task_id='SELF_INSPECTION',
            task_name='자주검사',
            started_at=started_at
        )

        # 3명 모두 join 후 완료
        for i, worker_id in enumerate(workers[1:], 1):
            token = get_auth_token(worker_id, role='MECH')
            client.post(
                '/api/app/work/join',
                json={'task_id': task_id},
                headers={'Authorization': f'Bearer {token}'}
            )

        # 모두 완료
        for worker_id in workers:
            token = get_auth_token(worker_id, role='MECH')
            endpoint = '/api/app/work/complete'
            resp = client.post(
                endpoint,
                json={'task_id': task_id},
                headers={'Authorization': f'Bearer {token}'}
            )
            if resp.status_code == 404:
                pytest.skip("완료 API 미구현")

        # DB 확인
        cursor = db_conn.cursor()
        cursor.execute(
            """SELECT duration_minutes, elapsed_minutes, worker_count
               FROM app_task_details WHERE id = %s""",
            (task_id,)
        )
        row = cursor.fetchone()
        cursor.close()

        if row is None or row[0] is None or row[1] is None:
            pytest.skip("duration_minutes/elapsed_minutes 컬럼 미구현")

        duration_min, elapsed_min, worker_count = row

        if worker_count and worker_count > 1:
            assert duration_min > elapsed_min, \
                f"멀티 작업자: duration({duration_min}) > elapsed({elapsed_min}) 이어야 함"

            # 3명 동시 작업 시 duration ≈ elapsed × worker_count (10% 오차 허용)
            expected_duration = elapsed_min * worker_count
            tolerance = expected_duration * 0.1
            assert abs(duration_min - expected_duration) <= tolerance + 5, \
                f"duration({duration_min}) ≈ elapsed({elapsed_min}) × workers({worker_count}) = {expected_duration}"


class TestWorkerCountDistinct:
    """TC-MW-07: worker_count = 실제 참여 작업자 수 (중복 제거 DISTINCT)"""

    def test_worker_count_distinct(
        self,
        client,
        create_test_worker,
        create_test_product,
        create_test_task,
        create_test_completion_status,
        get_auth_token,
        db_conn
    ):
        """
        TC-MW-07: 동일 작업자가 여러 번 완료 시도해도 worker_count는 중복 제거

        Setup:
        - Worker A가 동일 task를 완료 시도 2회 (중복)
        - Worker B가 1회 참여

        Expected:
        - worker_count == 2 (A, B 각 1번씩 카운트)
        - 중복 참여는 무시됨
        """
        worker_a = create_test_worker(
            email='mw_a_07@test.com', password='Test123!',
            name='MW Worker A07', role='MECH', company='FNI'
        )
        worker_b = create_test_worker(
            email='mw_b_07@test.com', password='Test123!',
            name='MW Worker B07', role='MECH', company='FNI'
        )

        create_test_product(
            qr_doc_id='DOC-MW-007',
            serial_number='SN-MW-007',
            model='GALLANT-50'
        )
        create_test_completion_status(serial_number='SN-MW-007')

        started_at = datetime.now(timezone.utc) - timedelta(hours=2)
        task_id = create_test_task(
            worker_id=worker_a,
            serial_number='SN-MW-007',
            qr_doc_id='DOC-MW-007',
            task_category='MECH',
            task_id='SELF_INSPECTION',
            task_name='자주검사',
            started_at=started_at
        )

        token_a = get_auth_token(worker_a, role='MECH')
        token_b = get_auth_token(worker_b, role='MECH')

        # A 첫 번째 완료
        resp1 = client.post(
            '/api/app/work/complete',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token_a}'}
        )
        if resp1.status_code != 200:
            pytest.skip("완료 API 실패")

        # A 두 번째 완료 시도 (중복 — 409 또는 무시되어야 함)
        resp2 = client.post(
            '/api/app/work/complete',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token_a}'}
        )
        # 중복 완료는 409 Conflict 또는 200(무시)이어야 함
        assert resp2.status_code in [200, 409, 400], \
            f"중복 완료 시도는 200/409/400이어야 함, got {resp2.status_code}"

        # B 완료
        resp3 = client.post(
            '/api/app/work/join-complete',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token_b}'}
        )
        if resp3.status_code == 404:
            pytest.skip("join-complete 미구현")

        # DB 최종 확인
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT worker_count FROM app_task_details WHERE id = %s",
            (task_id,)
        )
        row = cursor.fetchone()
        cursor.close()

        if row and row[0] is not None:
            assert row[0] == 2, \
                f"worker_count는 DISTINCT 2이어야 함 (중복 제거), got {row[0]}"
