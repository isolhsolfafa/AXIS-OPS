"""
공정 검증 API 테스트
엔드포인트: POST /api/app/validation/check-process
Sprint 3: 공정 누락 검증 + 알림 생성
"""

import pytest
from datetime import datetime, timezone


@pytest.fixture(autouse=True)
def cleanup_process_alerts(db_conn):
    """테스트 후 공정 검증으로 생성된 알림 정리"""
    yield
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            cursor.execute(
                "DELETE FROM app_alert_logs WHERE serial_number LIKE 'SN-PROC%%'"
            )
            db_conn.commit()
            cursor.close()
        except Exception:
            pass


class TestProcessValidationMMIncomplete:
    """MM 미완료 시 PI 공정 검증"""

    def test_pi_mm_incomplete(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token
    ):
        """
        PI 작업자가 MM 미완료 제품을 검증
        → can_proceed=false, MM in missing_processes, 알림 생성

        Expected:
        - Status 200
        - valid == false
        - missing_processes에 'MM' 포함
        - alerts_created >= 1 (MM 관리자가 있을 때)
        """
        pi_worker_id = create_test_worker(
            email='pi_proc@test.com', password='Test123!',
            name='PI Proc Worker', role='PI'
        )
        # MM 관리자 생성 (알림 대상)
        create_test_worker(
            email='mm_mgr_proc@test.com', password='Test123!',
            name='MM Manager Proc', role='MM', is_manager=True
        )

        create_test_product(
            qr_doc_id='DOC-PROC-001',
            serial_number='SN-PROC-001',
            model='GBWS-50',
            location_qr_id='LOC_A'
        )

        create_test_completion_status(
            serial_number='SN-PROC-001',
            mm_completed=False,
            ee_completed=True
        )

        token = get_auth_token(pi_worker_id, role='PI')
        response = client.post(
            '/api/app/validation/check-process',
            json={
                'serial_number': 'SN-PROC-001',
                'process_type': 'PI'
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is False
        assert 'MM' in data['missing_processes']
        assert data['alerts_created'] >= 1


class TestProcessValidationEEIncomplete:
    """EE 미완료 시 QI 공정 검증"""

    def test_qi_ee_incomplete(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token
    ):
        """
        QI 작업자가 EE 미완료 제품을 검증
        → can_proceed=false, EE in missing_processes

        Expected:
        - Status 200
        - valid == false
        - missing_processes에 'EE' 포함
        """
        qi_worker_id = create_test_worker(
            email='qi_proc@test.com', password='Test123!',
            name='QI Proc Worker', role='QI'
        )
        create_test_worker(
            email='ee_mgr_proc@test.com', password='Test123!',
            name='EE Manager Proc', role='EE', is_manager=True
        )

        create_test_product(
            qr_doc_id='DOC-PROC-002',
            serial_number='SN-PROC-002',
            model='GBWS-50',
            location_qr_id='LOC_B'
        )

        create_test_completion_status(
            serial_number='SN-PROC-002',
            mm_completed=True,
            ee_completed=False
        )

        token = get_auth_token(qi_worker_id, role='QI')
        response = client.post(
            '/api/app/validation/check-process',
            json={
                'serial_number': 'SN-PROC-002',
                'process_type': 'QI'
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is False
        assert 'EE' in data['missing_processes']


class TestProcessValidationBothComplete:
    """MM + EE 모두 완료 → 공정 진행 가능"""

    def test_pi_both_complete(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token
    ):
        """
        MM + EE 완료 → can_proceed=true, 알림 없음

        Expected:
        - Status 200
        - valid == true
        - missing_processes 빈 배열
        - alerts_created == 0
        """
        pi_worker_id = create_test_worker(
            email='pi_pass@test.com', password='Test123!',
            name='PI Pass Worker', role='PI'
        )

        create_test_product(
            qr_doc_id='DOC-PROC-003',
            serial_number='SN-PROC-003',
            model='GBWS-50',
            location_qr_id='LOC_C'
        )

        create_test_completion_status(
            serial_number='SN-PROC-003',
            mm_completed=True,
            ee_completed=True
        )

        token = get_auth_token(pi_worker_id, role='PI')
        response = client.post(
            '/api/app/validation/check-process',
            json={
                'serial_number': 'SN-PROC-003',
                'process_type': 'PI'
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is True
        assert data['missing_processes'] == []
        assert data['alerts_created'] == 0


class TestProcessValidationNonInspection:
    """비검사 공정 (MM, EE, TM) 검증 불필요"""

    def test_mm_skips_validation(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token
    ):
        """
        MM 공정 타입 → 검증 건너뜀, valid=true

        Expected:
        - Status 200
        - valid == true (검사 공정이 아니므로)
        """
        mm_worker_id = create_test_worker(
            email='mm_skip@test.com', password='Test123!',
            name='MM Skip Worker', role='MM'
        )

        create_test_product(
            qr_doc_id='DOC-PROC-004',
            serial_number='SN-PROC-004',
            model='GBWS-50'
        )

        create_test_completion_status(serial_number='SN-PROC-004')

        token = get_auth_token(mm_worker_id, role='MM')
        response = client.post(
            '/api/app/validation/check-process',
            json={
                'serial_number': 'SN-PROC-004',
                'process_type': 'MM'
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is True


class TestProcessValidationNoProduct:
    """존재하지 않는 제품"""

    def test_product_not_found(
        self, client, create_test_worker, get_auth_token
    ):
        """
        존재하지 않는 serial_number → 404

        Expected:
        - Status 404
        - error == PRODUCT_NOT_FOUND
        """
        worker_id = create_test_worker(
            email='proc_404@test.com', password='Test123!',
            name='NotFound Worker', role='PI'
        )

        token = get_auth_token(worker_id, role='PI')
        response = client.post(
            '/api/app/validation/check-process',
            json={
                'serial_number': 'SN-NONEXISTENT',
                'process_type': 'PI'
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data['error'] == 'PRODUCT_NOT_FOUND'


class TestLocationQRCheck:
    """Location QR 미등록 검증"""

    def test_no_location_qr(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token
    ):
        """
        Location QR 미등록 제품 → location_qr_verified=false

        Expected:
        - Status 200
        - location_qr_verified == false
        """
        worker_id = create_test_worker(
            email='loc_check@test.com', password='Test123!',
            name='Location Check Worker', role='PI'
        )

        create_test_product(
            qr_doc_id='DOC-PROC-005',
            serial_number='SN-PROC-005',
            model='GBWS-50',
            location_qr_id=None
        )

        create_test_completion_status(
            serial_number='SN-PROC-005',
            mm_completed=True,
            ee_completed=True
        )

        token = get_auth_token(worker_id, role='PI')
        response = client.post(
            '/api/app/validation/check-process',
            json={
                'serial_number': 'SN-PROC-005',
                'process_type': 'PI'
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['location_qr_verified'] is False
