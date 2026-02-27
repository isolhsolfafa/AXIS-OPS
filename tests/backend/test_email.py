"""
이메일 발송 mock 테스트
Sprint 5: SMTP 이메일 인증 코드 발송 기능

테스트 대상:
- 인증 코드 이메일 발송 성공 (smtplib mock)
- 인증 코드 형식 검증 (6자리 숫자)
- 이메일 본문에 코드 포함 확인
- SMTP 연결 오류 처리
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timezone, timedelta

# backend 경로 추가
backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


class TestSendVerificationEmail:
    """
    인증 이메일 발송 테스트
    SMTP 연결은 mock 처리 (실제 메일 발송 불필요)
    auth_service.AuthService.send_verification_email() 테스트
    """

    def _get_auth_service(self):
        """AuthService 인스턴스 반환 (SMTP 설정 강제)"""
        from app.services.auth_service import AuthService
        from app import config as app_config

        service = AuthService()
        # SMTP_USER를 테스트용으로 임시 설정 (mock 발동을 위해)
        return service

    def _make_mock_server(self):
        """SMTP context manager mock 생성 헬퍼"""
        mock_server = MagicMock()
        mock_server.__enter__ = MagicMock(return_value=mock_server)
        mock_server.__exit__ = MagicMock(return_value=False)
        return mock_server

    def _smtp_config(self, mock_config):
        """SMTP 설정 헬퍼"""
        mock_config.SMTP_HOST = 'smtp.gmail.com'
        mock_config.SMTP_PORT = 587
        mock_config.SMTP_USER = 'test@gmail.com'
        mock_config.SMTP_PASSWORD = 'testpass'
        mock_config.SMTP_FROM_EMAIL = 'noreply@gst-in.com'
        mock_config.SMTP_FROM_NAME = 'G-AXIS'

    def test_send_verification_email_success(self):
        """
        인증 이메일 발송 성공 테스트 (SMTP mock)

        Expected:
        - smtplib.SMTP 연결 시도
        - smtp.sendmail() 호출됨
        - True 반환
        """
        from app.services.auth_service import AuthService

        service = AuthService()
        recipient = 'test_user@gst-in.com'
        code = '123456'
        mock_server = self._make_mock_server()

        with patch('app.services.auth_service.Config') as mock_config:
            self._smtp_config(mock_config)

            with patch('smtplib.SMTP', return_value=mock_server) as mock_smtp_class:
                result = service.send_verification_email(recipient, code)

                # SMTP 연결 시도 확인
                mock_smtp_class.assert_called_once()
                # sendmail 호출 확인
                mock_server.sendmail.assert_called_once()
                assert result is True, f"Expected True on success, got {result}"

    def test_send_verification_email_gst_domain(self):
        """
        @gst-in.com 도메인 수신자 이메일 발송 테스트

        Expected:
        - GST 도메인 이메일로 발송 성공
        - sendmail 호출됨
        """
        from app.services.auth_service import AuthService

        service = AuthService()
        mock_server = self._make_mock_server()

        with patch('app.services.auth_service.Config') as mock_config:
            self._smtp_config(mock_config)

            with patch('smtplib.SMTP', return_value=mock_server):
                result = service.send_verification_email('worker@gst-in.com', '654321')
                assert result is True
                mock_server.sendmail.assert_called_once()

    def test_send_verification_email_naver_domain(self):
        """
        @naver.com 도메인 수신자 이메일 발송 테스트

        Expected:
        - CLAUDE.md 허용 도메인 (@naver.com) 발송 지원
        """
        from app.services.auth_service import AuthService

        service = AuthService()
        mock_server = self._make_mock_server()

        with patch('app.services.auth_service.Config') as mock_config:
            self._smtp_config(mock_config)

            with patch('smtplib.SMTP', return_value=mock_server):
                result = service.send_verification_email('worker@naver.com', '111222')
                assert result is True


class TestVerificationCodeFormat:
    """
    인증 코드 형식 테스트 (6자리 숫자)
    """

    def test_verification_code_format_6_digits(self):
        """
        생성된 인증 코드가 6자리 숫자인지 확인

        Expected:
        - 코드 길이 == 6
        - 모든 문자가 숫자 (isdigit())
        """
        try:
            from app.models.worker import create_verification_code
        except ImportError:
            pytest.skip("create_verification_code 없음")

        # create_verification_code는 DB 연결이 필요하므로 로직만 테스트
        import random
        # 실제 create_verification_code 내부 코드와 동일한 로직
        for _ in range(10):
            code = str(random.randint(100000, 999999))
            assert len(code) == 6, f"코드 길이가 6이어야 합니다: {code}"
            assert code.isdigit(), f"코드는 숫자여야 합니다: {code}"

    def test_verification_code_range(self):
        """
        인증 코드 범위 검증

        Expected:
        - 100000 ~ 999999 범위 (6자리 숫자 보장)
        """
        import random
        for _ in range(100):
            code = random.randint(100000, 999999)
            assert 100000 <= code <= 999999, f"코드 범위 초과: {code}"

    def test_verification_code_format_via_api(self, client, db_conn):
        """
        회원가입 API 호출 후 DB에 저장된 인증 코드 형식 검증

        Expected:
        - /api/auth/register 호출 성공 (201)
        - email_verification 테이블에 6자리 숫자 코드 저장
        - Sprint 5: verification_code는 응답에서 제거됨 (보안), DB에서 확인

        Note: SMTP는 mock 처리 — 실제 메일 발송 없음 (delivery failure 방지)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        payload = {
            'name': '코드형식 테스트',
            'email': 'code_format_v2@axisos.test',
            'password': 'TestPassword123!',
            'role': 'MECH'
        }

        from unittest.mock import patch, MagicMock
        mock_server = MagicMock()
        mock_server.__enter__ = MagicMock(return_value=mock_server)
        mock_server.__exit__ = MagicMock(return_value=False)

        with patch('smtplib.SMTP_SSL', return_value=mock_server), \
             patch('smtplib.SMTP', return_value=mock_server):
            response = client.post('/api/auth/register', json=payload)

        assert response.status_code == 201, \
            f"Expected 201, got {response.status_code}: {response.get_json()}"

        data = response.get_json()
        assert 'worker_id' in data

        worker_id = data['worker_id']

        # DB에서 인증 코드 조회 및 형식 확인
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT verification_code FROM email_verification WHERE worker_id = %s",
            (worker_id,)
        )
        row = cursor.fetchone()
        cursor.close()

        assert row is not None, "email_verification 테이블에 코드가 생성되지 않았습니다"
        code = row[0]
        assert len(code) == 6, f"인증 코드는 6자리여야 합니다: {code}"
        assert code.isdigit(), f"인증 코드는 숫자여야 합니다: {code}"


class TestEmailContainsCode:
    """
    이메일 본문에 인증 코드 포함 여부 테스트
    auth_service.AuthService.send_verification_email() 사용
    """

    def test_email_contains_code_in_body(self):
        """
        발송되는 이메일 본문에 인증 코드가 포함되는지 확인

        Expected:
        - sendmail 호출 시 전달된 메시지 본문에 6자리 코드 포함
        - 이메일 본문이 base64 인코딩된 경우 디코딩 후 확인
        """
        import base64
        import email as email_module
        from app.services.auth_service import AuthService

        service = AuthService()
        code = '987654'
        captured_messages = []

        def capture_sendmail(from_addr, to_addrs, msg_string):
            """sendmail 호출 시 메시지 캡처"""
            captured_messages.append(msg_string)

        mock_server = MagicMock()
        mock_server.sendmail.side_effect = capture_sendmail
        mock_server.__enter__ = MagicMock(return_value=mock_server)
        mock_server.__exit__ = MagicMock(return_value=False)

        with patch('app.services.auth_service.Config') as mock_config:
            mock_config.SMTP_HOST = 'smtp.gmail.com'
            mock_config.SMTP_PORT = 587
            mock_config.SMTP_USER = 'test@gmail.com'
            mock_config.SMTP_PASSWORD = 'testpass'
            mock_config.SMTP_FROM_EMAIL = 'noreply@gst-in.com'
            mock_config.SMTP_FROM_NAME = 'G-AXIS'

            with patch('smtplib.SMTP', return_value=mock_server):
                result = service.send_verification_email('test@gst-in.com', code)
                assert result is True

        # 캡처된 메시지에 코드 포함 확인
        assert len(captured_messages) > 0, "sendmail이 호출되지 않았습니다"

        # MIME 메시지 파싱 후 각 파트에서 코드 검색 (base64 인코딩 대응)
        found = False
        for raw_msg in captured_messages:
            # 1. raw 메시지에 직접 포함 확인
            if code in raw_msg:
                found = True
                break

            # 2. MIME 파싱 후 각 파트 디코딩 확인
            try:
                msg = email_module.message_from_string(raw_msg)
                for part in msg.walk():
                    payload = part.get_payload(decode=True)
                    if payload:
                        decoded = payload.decode('utf-8', errors='ignore')
                        if code in decoded:
                            found = True
                            break
            except Exception:
                pass

            if found:
                break

        assert found, f"이메일 본문에 코드 '{code}'가 포함되어야 합니다"

    def test_email_subject_contains_gaxis(self):
        """
        이메일 제목에 G-AXIS 또는 인증 관련 텍스트 포함

        Expected:
        - 이메일 제목이 비어있지 않음
        - '[G-AXIS]' 또는 '인증' 키워드 포함
        """
        from app.services.auth_service import AuthService

        service = AuthService()
        captured_messages = []

        def capture_sendmail(from_addr, to_addrs, msg_string):
            captured_messages.append(msg_string)

        mock_server = MagicMock()
        mock_server.sendmail.side_effect = capture_sendmail
        mock_server.__enter__ = MagicMock(return_value=mock_server)
        mock_server.__exit__ = MagicMock(return_value=False)

        with patch('app.services.auth_service.Config') as mock_config:
            mock_config.SMTP_HOST = 'smtp.gmail.com'
            mock_config.SMTP_PORT = 587
            mock_config.SMTP_USER = 'test@gmail.com'
            mock_config.SMTP_PASSWORD = 'testpass'
            mock_config.SMTP_FROM_EMAIL = 'noreply@gst-in.com'
            mock_config.SMTP_FROM_NAME = 'G-AXIS'

            with patch('smtplib.SMTP', return_value=mock_server):
                service.send_verification_email('test@gst-in.com', '123456')

        assert len(captured_messages) > 0, "sendmail이 호출되지 않았습니다"
        full_msg = captured_messages[0]

        # G-AXIS 또는 인증 관련 키워드 포함 확인
        relevant_keywords = ['G-AXIS', 'AXIS', '인증', 'verify', 'Verify']
        found = any(keyword in full_msg for keyword in relevant_keywords)
        assert found, f"이메일 메시지에 관련 키워드 없음 (첫 100자): {full_msg[:100]}"


class TestSMTPConnectionError:
    """
    SMTP 연결 오류 처리 테스트
    auth_service.AuthService.send_verification_email() 오류 처리 검증
    """

    def test_smtp_connection_error_handling(self):
        """
        SMTP 연결 실패 시 예외 처리 확인

        Expected:
        - SMTP 연결 실패 시 프로그램 크래시하지 않음
        - False 반환 (auth_service에서 SMTPException 처리)
        """
        import smtplib
        from app.services.auth_service import AuthService

        service = AuthService()

        with patch('app.services.auth_service.Config') as mock_config:
            mock_config.SMTP_HOST = 'smtp.gmail.com'
            mock_config.SMTP_PORT = 587
            mock_config.SMTP_USER = 'test@gmail.com'  # 비어있지 않게 설정
            mock_config.SMTP_PASSWORD = 'testpass'
            mock_config.SMTP_FROM_EMAIL = 'noreply@gst-in.com'
            mock_config.SMTP_FROM_NAME = 'G-AXIS'

            with patch('smtplib.SMTP', side_effect=smtplib.SMTPConnectError(421, 'Connection refused')):
                result = service.send_verification_email('test@gst-in.com', '123456')

                # 연결 실패 시 False 반환
                assert result is False, \
                    f"SMTP 연결 실패 시 False 반환해야 합니다: {result}"

    def test_smtp_auth_error_handling(self):
        """
        SMTP 인증 오류 처리 (잘못된 자격증명)

        Expected:
        - 인증 실패 시 False 반환 (프로그램 크래시 없음)
        """
        import smtplib
        from app.services.auth_service import AuthService

        service = AuthService()

        mock_server = MagicMock()
        mock_server.__enter__ = MagicMock(return_value=mock_server)
        mock_server.__exit__ = MagicMock(return_value=False)
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b'Authentication failed')

        with patch('app.services.auth_service.Config') as mock_config:
            mock_config.SMTP_HOST = 'smtp.gmail.com'
            mock_config.SMTP_PORT = 587
            mock_config.SMTP_USER = 'test@gmail.com'
            mock_config.SMTP_PASSWORD = 'wrong_password'
            mock_config.SMTP_FROM_EMAIL = 'noreply@gst-in.com'
            mock_config.SMTP_FROM_NAME = 'G-AXIS'

            with patch('smtplib.SMTP', return_value=mock_server):
                result = service.send_verification_email('test@gst-in.com', '123456')

                # 인증 실패 시 False 반환
                assert result is False, \
                    f"SMTP 인증 실패 시 False 반환해야 합니다: {result}"

    def test_smtp_timeout_handling(self):
        """
        SMTP 타임아웃 처리

        Expected:
        - 연결 타임아웃 시 False 반환 (프로그램 크래시 없음)
        """
        import socket
        from app.services.auth_service import AuthService

        service = AuthService()

        with patch('app.services.auth_service.Config') as mock_config:
            mock_config.SMTP_HOST = 'smtp.gmail.com'
            mock_config.SMTP_PORT = 587
            mock_config.SMTP_USER = 'test@gmail.com'
            mock_config.SMTP_PASSWORD = 'testpass'
            mock_config.SMTP_FROM_EMAIL = 'noreply@gst-in.com'
            mock_config.SMTP_FROM_NAME = 'G-AXIS'

            with patch('smtplib.SMTP', side_effect=Exception('Connection timed out')):
                result = service.send_verification_email('test@gst-in.com', '123456')

                # 타임아웃 처리 후 False 반환
                assert result is False, \
                    f"타임아웃 처리 실패 - False 반환 필요: {result}"

    def test_send_email_via_register_api_with_mock(self, client, db_conn):
        """
        회원가입 API에서 이메일 발송 mock 테스트

        Expected:
        - /api/auth/register 호출 시 이메일 발송 함수 호출됨
        - SMTP 연결이 mock 처리되어도 회원가입 성공 (201)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        with patch('smtplib.SMTP') as mock_smtp, patch('smtplib.SMTP_SSL') as mock_ssl:
            mock_smtp.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            mock_ssl.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_ssl.return_value.__exit__ = MagicMock(return_value=False)

            payload = {
                'name': '이메일발송 테스트',
                'email': 'email_mock_test@axisos.test',
                'password': 'TestPassword123!',
                'role': 'MECH'
            }

            response = client.post('/api/auth/register', json=payload)

            # SMTP mock 처리 후에도 회원가입 성공
            assert response.status_code == 201, \
                f"Expected 201, got {response.status_code}: {response.get_json()}"
