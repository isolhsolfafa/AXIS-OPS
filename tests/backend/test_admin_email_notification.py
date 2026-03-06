"""
Admin 이메일 알림 테스트
Sprint 20-A: 신규 가입 시 Admin 이메일 알림
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def cleanup_email_test_data(db_conn):
    """테스트 전후 데이터 정리"""
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            cursor.execute("DELETE FROM email_verification WHERE worker_id IN (SELECT id FROM workers WHERE email LIKE 'mail_test_%@test.com')")
            cursor.execute("DELETE FROM workers WHERE email LIKE 'mail_test_%@test.com'")
            db_conn.commit()
            cursor.close()
        except Exception:
            db_conn.rollback()

    yield

    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            cursor.execute("DELETE FROM email_verification WHERE worker_id IN (SELECT id FROM workers WHERE email LIKE 'mail_test_%@test.com')")
            cursor.execute("DELETE FROM workers WHERE email LIKE 'mail_test_%@test.com'")
            db_conn.commit()
            cursor.close()
        except Exception:
            pass


class TestRegisterNotification:
    """가입 시 Admin 알림 이메일 테스트"""

    def test_mail01_register_triggers_admin_notification(self, client):
        """MAIL-01: 정상 가입 → send_register_notification 호출 확인"""
        # auth.py의 lazy import를 패치: import 시점의 모듈 경로
        with patch('app.services.email_service.send_register_notification') as mock_notify:
            response = client.post('/api/auth/register', json={
                'name': 'Mail Test Worker',
                'email': 'mail_test_01@test.com',
                'password': 'Test123!',
                'role': 'MECH',
                'company': 'FNI',
            })

            assert response.status_code == 201
            mock_notify.assert_called_once_with(
                name='Mail Test Worker',
                email='mail_test_01@test.com',
                role='MECH',
                company='FNI',
            )

    def test_mail02_smtp_not_configured_register_succeeds(self, client):
        """MAIL-02: SMTP 미설정 → 가입 성공, 이메일 스킵"""
        with patch('app.services.email_service.Config') as mock_config:
            mock_config.SMTP_USER = ''
            mock_config.SMTP_HOST = ''
            mock_config.SMTP_PORT = 587
            mock_config.SMTP_PASSWORD = ''
            mock_config.SMTP_FROM_NAME = 'G-AXIS'
            mock_config.SMTP_FROM_EMAIL = 'test@test.com'

            response = client.post('/api/auth/register', json={
                'name': 'Mail Test Worker 2',
                'email': 'mail_test_02@test.com',
                'password': 'Test123!',
                'role': 'MECH',
                'company': 'FNI',
            })

            assert response.status_code == 201

    def test_mail03_smtp_failure_register_succeeds(self, client):
        """MAIL-03: SMTP 연결 실패 → 가입 성공, 이메일 실패"""
        with patch('app.services.email_service._send_email', side_effect=Exception("SMTP connection failed")):
            response = client.post('/api/auth/register', json={
                'name': 'Mail Test Worker 3',
                'email': 'mail_test_03@test.com',
                'password': 'Test123!',
                'role': 'ELEC',
                'company': 'C&A',
            })

            # 이메일 실패해도 가입은 성공
            assert response.status_code == 201

    def test_mail04_notification_contains_worker_info(self):
        """MAIL-04: 이메일 내용에 가입자 정보 포함"""
        from app.services.email_service import render_register_notification

        html = render_register_notification(
            name='테스트 작업자',
            email='test@test.com',
            role='MECH',
            company='FNI',
        )

        assert '테스트 작업자' in html
        assert 'test@test.com' in html
        assert 'MECH' in html
        assert 'FNI' in html

    def test_mail05_multiple_admins_each_receive(self, db_conn):
        """MAIL-05: Admin 여러 명 → 각각에게 개별 발송"""
        from app.services.email_service import send_register_notification

        with patch('app.services.email_service.get_admin_emails') as mock_get, \
             patch('app.services.email_service._send_email') as mock_send:
            mock_get.return_value = ['admin1@test.com', 'admin2@test.com']
            mock_send.return_value = True

            send_register_notification(
                name='테스트', email='new@test.com', role='MECH', company='FNI'
            )

            assert mock_send.call_count == 2
            emails_sent_to = [call.kwargs['to_email'] for call in mock_send.call_args_list]
            assert 'admin1@test.com' in emails_sent_to
            assert 'admin2@test.com' in emails_sent_to
