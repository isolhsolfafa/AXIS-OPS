"""
v2.18.20 통합 변경 pytest

Codex M-Q8 (라운드 1) 권고 — 신규 경로 단위/통합 TC.

대상:
1. get_worker_by_email_prefix() — 0명/1명/2명+ 분기
2. login() prefix 확장 — 일반 사용자 prefix 매칭
3. send_approval_notification() — HTML escape (XSS 방지)
4. send_approval_notification_async() — thread 생성 catch
"""

import html
import pytest
from unittest.mock import patch, MagicMock

from app.models.worker import get_worker_by_email_prefix
from app.services.auth_service import AuthService
from app.services.notification_service import (
    _render_approval_html,
    send_approval_notification,
    send_approval_notification_async,
)


# ──────────────────────────────────────────────────────────────────────
# 1. get_worker_by_email_prefix 단위 TC
# ──────────────────────────────────────────────────────────────────────

class TestGetWorkerByEmailPrefix:
    """get_worker_by_email_prefix 영역 0명/1명/2명+ 분기 검증."""

    def test_prefix_0_match_returns_none(self):
        """존재하지 않는 prefix → None"""
        result = get_worker_by_email_prefix('nonexistent_prefix_xyz123')
        assert result is None

    def test_prefix_admin_matches(self, db_admin_worker):
        """admin (dkkim1@gst-in.com) prefix 매칭 → Worker 객체"""
        # conftest.py 영역 admin seed 가정 (id=1, email='dkkim1@gst-in.com')
        result = get_worker_by_email_prefix('dkkim1')
        assert result is not None
        assert result.email == 'dkkim1@gst-in.com'

    def test_prefix_ambiguous_returns_none(self, multi_domain_workers):
        """동일 prefix 2개 도메인 가입 시 → None (모호)"""
        # fixture: kdkyu_test@gst-in.com + kdkyu_test@naver.com 2명 등록
        result = get_worker_by_email_prefix('kdkyu_test')
        assert result is None  # 모호 매칭 → None


# ──────────────────────────────────────────────────────────────────────
# 2. login prefix 확장 통합 TC
# ──────────────────────────────────────────────────────────────────────

class TestLoginPrefixExtension:
    """auth_service.login() prefix 확장 (admin/일반 사용자/이름) chain 검증."""

    def test_login_with_full_email(self, regular_worker):
        """전체 이메일 입력 → 정상 매칭"""
        auth = AuthService()
        response, status = auth.login(regular_worker.email, 'TestPass123!', device_id='test')
        assert status == 200 or status == 403  # 승인 상태에 따라 다름

    def test_login_with_prefix_general_user(self, regular_worker):
        """일반 사용자 prefix 입력 → 매칭 (v2.18.20 신규)"""
        prefix = regular_worker.email.split('@')[0]
        auth = AuthService()
        response, status = auth.login(prefix, 'TestPass123!', device_id='test')
        # 200 OR 403 (email_verified/approval 영역 catch)
        assert status in (200, 403), f"prefix 매칭 실패: {response}"

    def test_login_with_nonexistent_prefix(self):
        """존재하지 않는 prefix → ACCOUNT_NOT_FOUND"""
        auth = AuthService()
        response, status = auth.login('nonexistent_xyz', 'anypass', device_id='test')
        assert status == 404
        assert response.get('error') == 'ACCOUNT_NOT_FOUND'


# ──────────────────────────────────────────────────────────────────────
# 3. send_approval_notification HTML escape TC (Codex M-Q1)
# ──────────────────────────────────────────────────────────────────────

class TestApprovalNotificationXSS:
    """Codex M-Q1: HTML escape XSS 방지 검증."""

    def test_render_escapes_script_in_name(self):
        """name 영역 <script> 태그 → HTML escape"""
        body = _render_approval_html(
            name='<script>alert(1)</script>',
            role='MECH',
            company='FNI',
        )
        # raw <script> 영역 본문 X
        assert '<script>alert(1)</script>' not in body
        # escaped 형태 영역 본문 ✅
        assert '&lt;script&gt;alert(1)&lt;/script&gt;' in body

    def test_render_escapes_quotes_in_role(self):
        """role 영역 quote → escape"""
        body = _render_approval_html(name='홍길동', role='MECH"onclick="x"', company='FNI')
        assert 'onclick="x"' not in body
        assert '&quot;' in body

    def test_render_handles_none_company(self):
        """company None → '-' 표시 (예외 없음)"""
        body = _render_approval_html(name='홍길동', role='MECH', company=None)
        assert '<strong>소속:</strong> -' in body


# ──────────────────────────────────────────────────────────────────────
# 4. send_approval_notification_async thread catch
# ──────────────────────────────────────────────────────────────────────

class TestApprovalNotificationAsync:
    """Codex M-Q4: thread 생성 캡슐화 검증."""

    @patch('app.services.notification_service.send_approval_notification')
    def test_async_calls_send_in_background(self, mock_send):
        """async 호출 → background thread 영역 send_approval_notification 실행"""
        import time
        mock_send.return_value = True
        send_approval_notification_async(
            name='홍길동', email='test@gst-in.com', role='MECH', company='FNI',
            worker_id=999,
        )
        # thread 영역 짧은 시간 대기 (실제 호출 검증)
        time.sleep(0.1)
        mock_send.assert_called_once_with(
            name='홍길동', email='test@gst-in.com', role='MECH', company='FNI',
        )

    @patch('app.services.notification_service.send_approval_notification')
    def test_async_swallows_exception(self, mock_send):
        """send 영역 raise → thread 영역 swallow (caller 영향 0)"""
        import time
        mock_send.side_effect = Exception("SMTP down")
        # raise 발생해서는 안 됨
        send_approval_notification_async(
            name='홍길동', email='test@gst-in.com', role='MECH', worker_id=999,
        )
        time.sleep(0.1)
        # caller 영역 정상 진행 — 별도 assert 없음 (예외 안 났으면 OK)
