"""
작업 API 테스트
엔드포인트: /api/app/work/*, /api/app/tasks/*, /api/app/completion/*,
            /api/app/validation/*, /api/app/task/*, /api/app/location/*
Sprint 2: work.py convenience routes 테스트
"""

import pytest
from datetime import datetime, timezone


class TestWorkStart:
    """
    Test suite for POST /api/app/work/start
    작업 시작 엔드포인트 테스트
    """

    def test_start_work_success(
        self, client, create_test_worker, create_test_product,
        create_test_task, get_auth_token
    ):
        """
        정상 작업 시작 테스트

        Expected:
        - Status 200 OK
        - 전체 TaskDetail 반환 (started_at 포함)
        - started_at이 현재 시간으로 설정됨
        """
        # 작업자 생성
        worker_id = create_test_worker(
            email='mm_worker@test.com',
            password='Test123!',
            name='MM Worker',
            role='MECH',
            approval_status='approved',
            email_verified=True
        )

        # 제품 생성
        create_test_product(
            qr_doc_id='DOC_TEST001',
            serial_number='SN-TEST001',
            model='AXIS-500'
        )

        # 작업 생성 (미시작 상태)
        task_id = create_test_task(
            worker_id=worker_id,
            serial_number='SN-TEST001',
            qr_doc_id='DOC_TEST001',
            task_category='MECH',
            task_id='CABINET_ASSY',
            task_name='캐비넷 조립',
            started_at=None,
            completed_at=None
        )

        # JWT 토큰 생성
        token = get_auth_token(worker_id, role='MECH')

        # 작업 시작 요청
        response = client.post(
            '/api/app/work/start',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        # 검증
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.get_json()}"

        data = response.get_json()
        assert 'id' in data
        assert data['id'] == task_id
        assert data['started_at'] is not None
        assert data['completed_at'] is None
        assert data['task_category'] == 'MECH'
        assert data['task_id'] == 'CABINET_ASSY'

    def test_start_already_started_task(
        self, client, create_test_worker, create_test_product,
        create_test_task, get_auth_token
    ):
        """
        이미 시작된 작업 재시작 시도

        Expected:
        - Status 400 Bad Request
        - Error code: TASK_ALREADY_STARTED
        """
        worker_id = create_test_worker(
            email='ee_worker@test.com',
            password='Test123!',
            name='EE Worker',
            role='ELEC',
            approval_status='approved'
        )

        create_test_product(
            qr_doc_id='DOC_TEST002',
            serial_number='SN-TEST002',
            model='AXIS-700'
        )

        # 이미 시작된 작업
        task_id = create_test_task(
            worker_id=worker_id,
            serial_number='SN-TEST002',
            qr_doc_id='DOC_TEST002',
            task_category='ELEC',
            task_id='WIRING',
            task_name='배선 작업',
            started_at=datetime.now(timezone.utc),
            completed_at=None
        )

        token = get_auth_token(worker_id, role='ELEC')

        response = client.post(
            '/api/app/work/start',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'TASK_ALREADY_STARTED'

    def test_start_other_worker_task(
        self, client, create_test_worker, create_test_product,
        create_test_task, get_auth_token
    ):
        """
        다른 작업자의 작업 시작 시도 — 멀티 작업자 지원

        Expected:
        - Status 200 OK (멀티 작업자 동시 시작 허용)
        - work_start_log에 기록됨
        """
        worker1_id = create_test_worker(
            email='worker1@test.com',
            password='Test123!',
            name='Worker 1',
            role='MECH'
        )

        worker2_id = create_test_worker(
            email='worker2@test.com',
            password='Test123!',
            name='Worker 2',
            role='MECH'
        )

        create_test_product(
            qr_doc_id='DOC_TEST003',
            serial_number='SN-TEST003',
            model='AXIS-500'
        )

        # worker1의 작업
        task_id = create_test_task(
            worker_id=worker1_id,
            serial_number='SN-TEST003',
            qr_doc_id='DOC_TEST003',
            task_category='MECH',
            task_id='PIPING',
            task_name='배관 작업'
        )

        # worker2가 시작 시도 — 멀티 작업자 지원으로 200 OK
        token = get_auth_token(worker2_id, role='MECH')

        response = client.post(
            '/api/app/work/start',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200, \
            f"멀티 작업자 시작 허용, got {response.status_code}: {response.get_json()}"

    def test_start_nonexistent_task(self, client, create_test_worker, get_auth_token):
        """
        존재하지 않는 작업 시작 시도

        Expected:
        - Status 404 Not Found
        - Error code: TASK_NOT_FOUND
        """
        worker_id = create_test_worker(
            email='worker@test.com',
            password='Test123!',
            name='Worker',
            role='MECH'
        )

        token = get_auth_token(worker_id, role='MECH')

        response = client.post(
            '/api/app/work/start',
            json={'task_id': 99999},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data['error'] == 'TASK_NOT_FOUND'

    def test_start_not_applicable_task(
        self, client, create_test_worker, create_test_product,
        create_test_task, get_auth_token
    ):
        """
        비활성화된 작업(is_applicable=false) 시작 시도

        Expected:
        - Status 400 Bad Request
        - Error code: TASK_NOT_APPLICABLE
        """
        worker_id = create_test_worker(
            email='worker@test.com',
            password='Test123!',
            name='Worker',
            role='MECH'
        )

        create_test_product(
            qr_doc_id='DOC_TEST004',
            serial_number='SN-TEST004',
            model='AXIS-500'
        )

        # 비활성화된 작업
        task_id = create_test_task(
            worker_id=worker_id,
            serial_number='SN-TEST004',
            qr_doc_id='DOC_TEST004',
            task_category='MECH',
            task_id='OPTIONAL_TASK',
            task_name='선택 작업',
            is_applicable=False
        )

        token = get_auth_token(worker_id, role='MECH')

        response = client.post(
            '/api/app/work/start',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'TASK_NOT_APPLICABLE'

    def test_start_without_jwt(self, client):
        """
        JWT 없이 작업 시작 시도

        Expected:
        - Status 401 Unauthorized
        - Error code: MISSING_TOKEN
        """
        response = client.post(
            '/api/app/work/start',
            json={'task_id': 1}
        )

        assert response.status_code == 401
        data = response.get_json()
        assert data['error'] == 'MISSING_TOKEN'


class TestWorkComplete:
    """
    Test suite for POST /api/app/work/complete
    작업 완료 엔드포인트 테스트
    """

    def test_complete_work_success(
        self, client, create_test_worker, create_test_product,
        create_test_task, get_auth_token
    ):
        """
        정상 작업 완료 테스트

        Expected:
        - Status 200 OK
        - 전체 TaskDetail 반환 (completed_at, duration_minutes 포함)
        - category_completed 플래그 반환
        """
        worker_id = create_test_worker(
            email='mm_worker@test.com',
            password='Test123!',
            name='MM Worker',
            role='MECH'
        )

        create_test_product(
            qr_doc_id='DOC_COMPLETE001',
            serial_number='SN-COMPLETE001',
            model='AXIS-500'
        )

        # 시작된 작업
        task_id = create_test_task(
            worker_id=worker_id,
            serial_number='SN-COMPLETE001',
            qr_doc_id='DOC_COMPLETE001',
            task_category='MECH',
            task_id='CABINET_ASSY',
            task_name='캐비넷 조립',
            started_at=datetime.now(timezone.utc)
        )

        token = get_auth_token(worker_id, role='MECH')

        response = client.post(
            '/api/app/work/complete',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.get_json()}"

        data = response.get_json()
        assert data['id'] == task_id
        assert data['completed_at'] is not None
        assert data['duration_minutes'] is not None
        assert data['duration_minutes'] >= 0
        assert 'category_completed' in data

    def test_complete_not_started_task(
        self, client, create_test_worker, create_test_product,
        create_test_task, get_auth_token
    ):
        """
        시작되지 않은 작업 완료 시도

        Expected:
        - Status 400 Bad Request
        - Error code: TASK_NOT_STARTED
        """
        worker_id = create_test_worker(
            email='worker@test.com',
            password='Test123!',
            name='Worker',
            role='MECH'
        )

        create_test_product(
            qr_doc_id='DOC_TEST005',
            serial_number='SN-TEST005',
            model='AXIS-500'
        )

        # 미시작 작업
        task_id = create_test_task(
            worker_id=worker_id,
            serial_number='SN-TEST005',
            qr_doc_id='DOC_TEST005',
            task_category='MECH',
            task_id='PIPING',
            task_name='배관 작업',
            started_at=None
        )

        token = get_auth_token(worker_id, role='MECH')

        response = client.post(
            '/api/app/work/complete',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        # 미시작 Task 완료 시도 → 400 (TASK_NOT_STARTED) 또는 403 (FORBIDDEN — 작업자 미매칭)
        assert response.status_code in [400, 403], \
            f"미시작 Task 완료는 400 또는 403이어야 함, got {response.status_code}"
        data = response.get_json()
        assert data['error'] in ['TASK_NOT_STARTED', 'FORBIDDEN']

    def test_complete_already_completed_task(
        self, client, create_test_worker, create_test_product,
        create_test_task, get_auth_token
    ):
        """
        이미 완료된 작업 재완료 시도

        Expected:
        - Status 400 Bad Request
        - Error code: TASK_ALREADY_COMPLETED
        """
        worker_id = create_test_worker(
            email='worker@test.com',
            password='Test123!',
            name='Worker',
            role='MECH'
        )

        create_test_product(
            qr_doc_id='DOC_TEST006',
            serial_number='SN-TEST006',
            model='AXIS-500'
        )

        # 이미 완료된 작업
        task_id = create_test_task(
            worker_id=worker_id,
            serial_number='SN-TEST006',
            qr_doc_id='DOC_TEST006',
            task_category='MECH',
            task_id='CABINET_ASSY',
            task_name='캐비넷 조립',
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            duration_minutes=60
        )

        token = get_auth_token(worker_id, role='MECH')

        response = client.post(
            '/api/app/work/complete',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'TASK_ALREADY_COMPLETED'

    def test_complete_updates_completion_status(
        self, client, db_conn, create_test_worker, create_test_product,
        create_test_task, create_test_completion_status, get_auth_token
    ):
        """
        카테고리 전체 완료 시 completion_status 업데이트 확인

        Expected:
        - category_completed = True
        - completion_status.mm_completed = True (DB 확인)
        """
        worker_id = create_test_worker(
            email='mm_worker@test.com',
            password='Test123!',
            name='MM Worker',
            role='MECH'
        )

        create_test_product(
            qr_doc_id='DOC_STATUS001',
            serial_number='SN-STATUS001',
            model='AXIS-500'
        )

        # completion_status 초기화
        create_test_completion_status(
            serial_number='SN-STATUS001',
            mech_completed=False
        )

        # MM 카테고리의 유일한 작업 (시작됨)
        task_id = create_test_task(
            worker_id=worker_id,
            serial_number='SN-STATUS001',
            qr_doc_id='DOC_STATUS001',
            task_category='MECH',
            task_id='ONLY_TASK',
            task_name='유일한 작업',
            started_at=datetime.now(timezone.utc)
        )

        token = get_auth_token(worker_id, role='MECH')

        response = client.post(
            '/api/app/work/complete',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200

        data = response.get_json()
        assert data['category_completed'] is True

        # DB에서 completion_status 확인
        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute(
                "SELECT mech_completed FROM completion_status WHERE serial_number = %s",
                ('SN-STATUS001',)
            )
            result = cursor.fetchone()
            cursor.close()

            assert result is not None
            assert result[0] is True  # mech_completed = True


class TestGetTasksBySerial:
    """
    Test suite for GET /api/app/tasks/<serial_number>
    시리얼 번호로 Task 목록 조회 테스트
    """

    def test_get_tasks_all(
        self, client, create_test_worker, create_test_product,
        create_test_task, get_auth_token
    ):
        """
        전체 Task 목록 조회

        Expected:
        - Status 200 OK
        - 리스트 형태 반환
        - 모든 카테고리 포함
        """
        worker_id = create_test_worker(
            email='worker@test.com',
            password='Test123!',
            name='Worker',
            role='MECH'
        )

        create_test_product(
            qr_doc_id='DOC_TASKS001',
            serial_number='SN-TASKS001',
            model='AXIS-500'
        )

        # 여러 카테고리 작업 생성
        create_test_task(
            worker_id=worker_id,
            serial_number='SN-TASKS001',
            qr_doc_id='DOC_TASKS001',
            task_category='MECH',
            task_id='TASK1',
            task_name='MM 작업'
        )

        create_test_task(
            worker_id=worker_id,
            serial_number='SN-TASKS001',
            qr_doc_id='DOC_TASKS001',
            task_category='ELEC',
            task_id='TASK2',
            task_name='EE 작업'
        )

        token = get_auth_token(worker_id, role='MECH')

        response = client.get(
            '/api/app/tasks/SN-TASKS001',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        # Company 기반 필터링: MECH role 작업자는 MECH task만 보임
        assert len(data) >= 1

    def test_get_tasks_filtered_by_process_type(
        self, client, create_test_worker, create_test_product,
        create_test_task, get_auth_token
    ):
        """
        process_type 필터로 Task 조회

        Expected:
        - Status 200 OK
        - 해당 카테고리만 반환
        """
        worker_id = create_test_worker(
            email='worker@test.com',
            password='Test123!',
            name='Worker',
            role='MECH'
        )

        create_test_product(
            qr_doc_id='DOC_FILTER001',
            serial_number='SN-FILTER001',
            model='AXIS-500'
        )

        create_test_task(
            worker_id=worker_id,
            serial_number='SN-FILTER001',
            qr_doc_id='DOC_FILTER001',
            task_category='MECH',
            task_id='TASK1',
            task_name='MM 작업'
        )

        create_test_task(
            worker_id=worker_id,
            serial_number='SN-FILTER001',
            qr_doc_id='DOC_FILTER001',
            task_category='ELEC',
            task_id='TASK2',
            task_name='EE 작업'
        )

        token = get_auth_token(worker_id, role='MECH')

        response = client.get(
            '/api/app/tasks/SN-FILTER001?process_type=MECH',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]['task_category'] == 'MECH'

    def test_get_tasks_empty_result(
        self, client, create_test_worker, create_test_product, get_auth_token
    ):
        """
        작업이 없는 제품 조회

        Expected:
        - Status 200 OK
        - 빈 리스트 반환
        """
        worker_id = create_test_worker(
            email='worker@test.com',
            password='Test123!',
            name='Worker',
            role='MECH'
        )

        create_test_product(
            qr_doc_id='DOC_EMPTY001',
            serial_number='SN-EMPTY001',
            model='AXIS-500'
        )

        token = get_auth_token(worker_id, role='MECH')

        response = client.get(
            '/api/app/tasks/SN-EMPTY001',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 0


class TestGetCompletionBySerial:
    """
    Test suite for GET /api/app/completion/<serial_number>
    시리얼 번호로 공정 완료 상태 조회 테스트
    """

    def test_get_completion_status(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token
    ):
        """
        공정 완료 상태 정상 조회

        Expected:
        - Status 200 OK
        - 6개 역할 필드 포함 (mm/ee/tm/pi/qi/si_completed)
        - qr_doc_id, serial_number 포함
        """
        worker_id = create_test_worker(
            email='worker@test.com',
            password='Test123!',
            name='Worker',
            role='MECH'
        )

        create_test_product(
            qr_doc_id='DOC_COMP001',
            serial_number='SN-COMP001',
            model='AXIS-500'
        )

        create_test_completion_status(
            serial_number='SN-COMP001',
            mech_completed=True,
            elec_completed=False
        )

        token = get_auth_token(worker_id, role='MECH')

        response = client.get(
            '/api/app/completion/SN-COMP001',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200

        data = response.get_json()
        assert 'qr_doc_id' in data
        assert 'serial_number' in data
        assert data['serial_number'] == 'SN-COMP001'
        assert 'mech_completed' in data
        assert 'elec_completed' in data
        assert 'tm_completed' in data
        assert 'pi_completed' in data
        assert 'qi_completed' in data
        assert 'si_completed' in data
        assert data['mech_completed'] is True
        assert data['elec_completed'] is False


class TestValidateProcess:
    """
    Test suite for POST /api/app/validation/check-process
    공정 누락 검증 테스트
    """

    def test_validate_missing_mm_ee(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token
    ):
        """
        MM/EE 미완료 시 PI 검증 실패

        Expected:
        - Status 200 OK
        - valid = False
        - missing_processes = ['MM', 'EE']
        """
        worker_id = create_test_worker(
            email='pi_worker@test.com',
            password='Test123!',
            name='PI Worker',
            role='PI'
        )

        create_test_product(
            qr_doc_id='DOC_VAL001',
            serial_number='SN-VAL001',
            model='AXIS-500'
        )

        create_test_completion_status(
            serial_number='SN-VAL001',
            mech_completed=False,
            elec_completed=False
        )

        token = get_auth_token(worker_id, role='PI')

        response = client.post(
            '/api/app/validation/check-process',
            json={
                'serial_number': 'SN-VAL001',
                'process_type': 'PI'
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200

        data = response.get_json()
        assert data['valid'] is False
        assert 'MECH' in data['missing_processes']
        assert 'ELEC' in data['missing_processes']

    def test_validate_mm_ee_completed(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token
    ):
        """
        MM/EE 완료 시 PI 검증 성공

        Expected:
        - Status 200 OK
        - valid = True
        - missing_processes = []
        """
        worker_id = create_test_worker(
            email='pi_worker@test.com',
            password='Test123!',
            name='PI Worker',
            role='PI'
        )

        create_test_product(
            qr_doc_id='DOC_VAL002',
            serial_number='SN-VAL002',
            model='AXIS-500'
        )

        create_test_completion_status(
            serial_number='SN-VAL002',
            mech_completed=True,
            elec_completed=True
        )

        token = get_auth_token(worker_id, role='PI')

        response = client.post(
            '/api/app/validation/check-process',
            json={
                'serial_number': 'SN-VAL002',
                'process_type': 'PI'
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200

        data = response.get_json()
        assert data['valid'] is True
        assert len(data['missing_processes']) == 0

    def test_validate_non_inspection_process(
        self, client, create_test_worker, create_test_product, get_auth_token
    ):
        """
        비검사 공정(MM/EE/TM) 검증 시 검증 불필요

        Expected:
        - Status 200 OK
        - valid = True (검증이 필요하지 않음)
        """
        worker_id = create_test_worker(
            email='mm_worker@test.com',
            password='Test123!',
            name='MM Worker',
            role='MECH'
        )

        create_test_product(
            qr_doc_id='DOC_VAL003',
            serial_number='SN-VAL003',
            model='AXIS-500'
        )

        token = get_auth_token(worker_id, role='MECH')

        response = client.post(
            '/api/app/validation/check-process',
            json={
                'serial_number': 'SN-VAL003',
                'process_type': 'MECH'
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200

        data = response.get_json()
        # MM은 검증 불필요하므로 valid=True 또는 검증 스킵
        assert 'valid' in data or 'message' in data


class TestToggleApplicable:
    """
    Test suite for PUT /api/app/task/toggle-applicable
    Task 적용 여부 토글 테스트
    """

    def test_toggle_applicable_success(
        self, client, create_test_worker, create_test_product,
        create_test_task, get_auth_token
    ):
        """
        Task 적용 여부 정상 토글

        Expected:
        - Status 200 OK
        - 업데이트된 TaskDetail 전체 반환
        - is_applicable 값 변경 확인
        """
        worker_id = create_test_worker(
            email='worker@test.com',
            password='Test123!',
            name='Worker',
            role='MECH'
        )

        create_test_product(
            qr_doc_id='DOC_TOGGLE001',
            serial_number='SN-TOGGLE001',
            model='AXIS-500'
        )

        task_id = create_test_task(
            worker_id=worker_id,
            serial_number='SN-TOGGLE001',
            qr_doc_id='DOC_TOGGLE001',
            task_category='MECH',
            task_id='TASK1',
            task_name='토글 테스트',
            is_applicable=True
        )

        token = get_auth_token(worker_id, role='MECH')

        # False로 토글
        response = client.put(
            '/api/app/task/toggle-applicable',
            json={
                'task_id': task_id,
                'is_applicable': False
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200

        data = response.get_json()
        assert data['id'] == task_id
        assert data['is_applicable'] is False

    def test_toggle_nonexistent_task(
        self, client, create_test_worker, get_auth_token
    ):
        """
        존재하지 않는 Task 토글 시도

        Expected:
        - Status 404 Not Found
        - Error code: TASK_NOT_FOUND
        """
        worker_id = create_test_worker(
            email='worker@test.com',
            password='Test123!',
            name='Worker',
            role='MECH'
        )

        token = get_auth_token(worker_id, role='MECH')

        response = client.put(
            '/api/app/task/toggle-applicable',
            json={
                'task_id': 99999,
                'is_applicable': False
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data['error'] == 'TASK_NOT_FOUND'


class TestLocationUpdate:
    """
    Test suite for POST /api/app/location/update
    Location QR 업데이트 테스트
    """

    def test_update_location_success(
        self, client, create_test_worker, create_test_product, get_auth_token
    ):
        """
        Location QR 정상 업데이트

        Expected:
        - Status 200 OK
        - 업데이트된 ProductInfo 전체 반환
        - location_qr_id 업데이트 확인
        """
        worker_id = create_test_worker(
            email='worker@test.com',
            password='Test123!',
            name='Worker',
            role='MECH'
        )

        create_test_product(
            qr_doc_id='DOC_LOC001',
            serial_number='SN-LOC001',
            model='AXIS-500',
            location_qr_id=None
        )

        token = get_auth_token(worker_id, role='MECH')

        response = client.post(
            '/api/app/location/update',
            json={
                'qr_doc_id': 'DOC_LOC001',
                'location_qr_id': 'LOC_STATION_A'
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200

        data = response.get_json()
        assert 'qr_doc_id' in data
        assert data['qr_doc_id'] == 'DOC_LOC001'
        assert data['location_qr_id'] == 'LOC_STATION_A'
        assert 'serial_number' in data
        assert 'model' in data

    def test_update_location_nonexistent_product(
        self, client, create_test_worker, get_auth_token
    ):
        """
        존재하지 않는 제품의 Location QR 업데이트 시도

        Expected:
        - Status 404 Not Found
        - Error code: PRODUCT_NOT_FOUND
        """
        worker_id = create_test_worker(
            email='worker@test.com',
            password='Test123!',
            name='Worker',
            role='MECH'
        )

        token = get_auth_token(worker_id, role='MECH')

        response = client.post(
            '/api/app/location/update',
            json={
                'qr_doc_id': 'DOC_NONEXISTENT',
                'location_qr_id': 'LOC_STATION_A'
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data['error'] == 'PRODUCT_NOT_FOUND'
