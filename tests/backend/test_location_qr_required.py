"""
BUG-11 Location QR 인증 필수 체크 테스트

task_service.py의 start_work()에서:
  admin_settings.location_qr_required = True 이고
  task.location_qr_verified = False 이면 400 LOCATION_QR_REQUIRED 에러.

TC-LQ-01 ~ TC-LQ-05: 5개 테스트 케이스
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def cleanup_lq_test_data(db_conn):
    """테스트 후 관련 데이터 정리"""
    yield
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            cursor.execute(
                "DELETE FROM work_start_log WHERE serial_number LIKE 'SN-LQ-%%'"
            )
            cursor.execute(
                "DELETE FROM app_task_details WHERE serial_number LIKE 'SN-LQ-%%'"
            )
            cursor.execute(
                "DELETE FROM completion_status WHERE serial_number LIKE 'SN-LQ-%%'"
            )
            cursor.execute(
                "DELETE FROM public.qr_registry WHERE qr_doc_id LIKE 'DOC-LQ-%%'"
            )
            cursor.execute(
                "DELETE FROM plan.product_info WHERE serial_number LIKE 'SN-LQ-%%'"
            )
            db_conn.commit()
            cursor.close()
        except Exception:
            pass


@pytest.fixture
def lq_worker(create_test_worker, get_auth_token):
    """Location QR 테스트 전용 작업자"""
    unique_suffix = int(time.time() * 1000)
    email = f'lq_worker_{unique_suffix}@lqtest.com'
    worker_id = create_test_worker(
        email=email,
        password='Test123!',
        name='LQ Test Worker',
        role='MECH',
        company='FNI',
        approval_status='approved',
        email_verified=True,
    )
    token = get_auth_token(worker_id, role='MECH')
    return {'id': worker_id, 'email': email, 'token': token}


def _create_task_with_location_qr(
    db_conn, worker_id, suffix, location_qr_verified=False
):
    """location_qr_verified 플래그가 설정된 Task 생성 헬퍼"""
    qr_doc_id = f'DOC-LQ-{suffix}'
    serial_number = f'SN-LQ-{suffix}'

    cursor = db_conn.cursor()

    # product_info + qr_registry
    cursor.execute("""
        INSERT INTO plan.product_info (serial_number, model, mech_partner)
        VALUES (%s, 'GALLANT-50', 'FNI')
        ON CONFLICT (serial_number) DO NOTHING
    """, (serial_number,))
    cursor.execute("""
        INSERT INTO public.qr_registry (qr_doc_id, serial_number)
        VALUES (%s, %s) ON CONFLICT (qr_doc_id) DO NOTHING
    """, (qr_doc_id, serial_number))

    # task (started_at NULL = 시작 전)
    cursor.execute("""
        INSERT INTO app_task_details (
            worker_id, serial_number, qr_doc_id, task_category,
            task_id, task_name, is_applicable, location_qr_verified
        )
        VALUES (%s, %s, %s, 'MECH', 'SELF_INSPECTION', '자주검사', TRUE, %s)
        RETURNING id
    """, (worker_id, serial_number, qr_doc_id, location_qr_verified))

    task_id = cursor.fetchone()[0]
    db_conn.commit()
    cursor.close()
    return task_id


def _set_admin_setting(db_conn, key, value):
    """admin_settings에 값 설정 (없으면 INSERT, 있으면 UPDATE)"""
    cursor = db_conn.cursor()
    import json
    json_value = json.dumps(value)
    cursor.execute("""
        INSERT INTO admin_settings (setting_key, setting_value)
        VALUES (%s, %s::jsonb)
        ON CONFLICT (setting_key) DO UPDATE SET setting_value = %s::jsonb
    """, (key, json_value, json_value))
    db_conn.commit()
    cursor.close()


def _cleanup_admin_setting(db_conn, key):
    """admin_settings에서 키 삭제"""
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM admin_settings WHERE setting_key = %s", (key,))
    db_conn.commit()
    cursor.close()


class TestLocationQrRequired:
    """Location QR 인증 필수 체크 (BUG-11)"""

    def test_lq01_required_true_verified_false_returns_400(
        self, client, app, lq_worker, db_conn
    ):
        """
        TC-LQ-01: location_qr_required=True + location_qr_verified=False → 400

        Expected:
        - HTTP 400
        - error == 'LOCATION_QR_REQUIRED'
        """
        suffix = int(time.time() * 1000)

        _set_admin_setting(db_conn, 'location_qr_required', True)

        try:
            task_id = _create_task_with_location_qr(
                db_conn, lq_worker['id'], suffix, location_qr_verified=False
            )

            response = client.post(
                '/api/app/work/start',
                json={'task_id': task_id},
                headers={'Authorization': f'Bearer {lq_worker["token"]}'}
            )

            assert response.status_code == 400, (
                f"Expected 400 LOCATION_QR_REQUIRED, got {response.status_code}"
            )
            data = response.get_json()
            assert data.get('error') == 'LOCATION_QR_REQUIRED', (
                f"Expected LOCATION_QR_REQUIRED error, got {data}"
            )
        finally:
            _cleanup_admin_setting(db_conn, 'location_qr_required')

    def test_lq02_required_true_verified_true_returns_200(
        self, client, app, lq_worker, db_conn
    ):
        """
        TC-LQ-02: location_qr_required=True + location_qr_verified=True → 200

        Expected:
        - HTTP 200 (작업 시작 성공)
        """
        suffix = int(time.time() * 1000) + 1

        _set_admin_setting(db_conn, 'location_qr_required', True)

        try:
            task_id = _create_task_with_location_qr(
                db_conn, lq_worker['id'], suffix, location_qr_verified=True
            )

            response = client.post(
                '/api/app/work/start',
                json={'task_id': task_id},
                headers={'Authorization': f'Bearer {lq_worker["token"]}'}
            )

            assert response.status_code == 200, (
                f"Expected 200 success, got {response.status_code}: {response.get_json()}"
            )
        finally:
            _cleanup_admin_setting(db_conn, 'location_qr_required')

    def test_lq03_required_false_verified_false_returns_200(
        self, client, app, lq_worker, db_conn
    ):
        """
        TC-LQ-03: location_qr_required=False + location_qr_verified=False → 200 (체크 생략)

        Expected:
        - HTTP 200 (location QR 체크 비활성화)
        """
        suffix = int(time.time() * 1000) + 2

        _set_admin_setting(db_conn, 'location_qr_required', False)

        try:
            task_id = _create_task_with_location_qr(
                db_conn, lq_worker['id'], suffix, location_qr_verified=False
            )

            response = client.post(
                '/api/app/work/start',
                json={'task_id': task_id},
                headers={'Authorization': f'Bearer {lq_worker["token"]}'}
            )

            assert response.status_code == 200, (
                f"Expected 200 (check skipped), got {response.status_code}: {response.get_json()}"
            )
        finally:
            _cleanup_admin_setting(db_conn, 'location_qr_required')

    def test_lq04_setting_not_present_defaults_false(
        self, client, app, lq_worker, db_conn
    ):
        """
        TC-LQ-04: admin_settings에 location_qr_required 키 없음 → default False → 200

        Expected:
        - HTTP 200 (설정 없으면 기본값 False)
        """
        suffix = int(time.time() * 1000) + 3

        # 해당 설정이 없는지 확인 (삭제)
        _cleanup_admin_setting(db_conn, 'location_qr_required')

        task_id = _create_task_with_location_qr(
            db_conn, lq_worker['id'], suffix, location_qr_verified=False
        )

        response = client.post(
            '/api/app/work/start',
            json={'task_id': task_id},
            headers={'Authorization': f'Bearer {lq_worker["token"]}'}
        )

        assert response.status_code == 200, (
            f"Expected 200 (default False), got {response.status_code}: {response.get_json()}"
        )

    def test_lq05_error_code_format(
        self, client, app, lq_worker, db_conn
    ):
        """
        TC-LQ-05: LOCATION_QR_REQUIRED 에러 메시지 포맷 검증

        Expected:
        - error 필드가 'LOCATION_QR_REQUIRED' 문자열
        - message 필드에 'Location QR' 관련 안내 메시지 포함
        """
        suffix = int(time.time() * 1000) + 4

        _set_admin_setting(db_conn, 'location_qr_required', True)

        try:
            task_id = _create_task_with_location_qr(
                db_conn, lq_worker['id'], suffix, location_qr_verified=False
            )

            response = client.post(
                '/api/app/work/start',
                json={'task_id': task_id},
                headers={'Authorization': f'Bearer {lq_worker["token"]}'}
            )

            assert response.status_code == 400
            data = response.get_json()
            assert data['error'] == 'LOCATION_QR_REQUIRED', (
                f"Error code should be LOCATION_QR_REQUIRED, got {data.get('error')}"
            )
            assert 'Location QR' in data.get('message', '') or 'QR' in data.get('message', ''), (
                f"Message should mention QR: {data.get('message')}"
            )
        finally:
            _cleanup_admin_setting(db_conn, 'location_qr_required')
