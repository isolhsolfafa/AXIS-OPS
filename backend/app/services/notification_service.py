"""
알림 서비스 — 가입 승인/거부 등 사용자 알림 통합 관리

v2.18.20 신규 — admin.py God File 정합 catch + CLAUDE.md L477 정책 준수.
Sprint 22-A (가입 Admin 알림) 패턴 정합.
"""

import html
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime, timezone, timedelta

from app.config import Config

logger = logging.getLogger(__name__)

_KST = timezone(timedelta(hours=9))


def _send_smtp(to_email: str, subject: str, html_body: str) -> bool:
    """smtplib 로 이메일 발송 (email_service.py 와 동일 패턴)."""
    if not Config.SMTP_USER:
        logger.info(f"[DEV] notification (SMTP not configured): to={to_email}")
        return True

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = f"{Config.SMTP_FROM_NAME} <{Config.SMTP_FROM_EMAIL}>"
        msg['To'] = to_email
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        if Config.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10) as server:
                server.ehlo()
                server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
                server.sendmail(Config.SMTP_FROM_EMAIL, to_email, msg.as_string())
        else:
            with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
                server.sendmail(Config.SMTP_FROM_EMAIL, to_email, msg.as_string())

        logger.info(f"Notification email sent: to={to_email}, subject={subject}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed — SMTP_USER/SMTP_PASSWORD 설정 확인")
        return False
    except smtplib.SMTPRecipientsRefused as e:
        logger.warning(f"SMTP recipient refused: to={to_email}, detail={e.recipients}")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error while sending notification to {to_email}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error while sending notification to {to_email}: {e}")
        return False


def _render_approval_html(name: str, role: str, company: str = None) -> str:
    """가입 승인 안내 HTML 템플릿 (Codex M-Q1: html.escape 적용 XSS 방지)."""
    now_kst = datetime.now(_KST).strftime('%Y-%m-%d %H:%M')
    # Codex M-Q1: XSS 방지 — 사용자 입력값 모두 escape
    safe_name = html.escape(str(name), quote=True)
    safe_role = html.escape(str(role), quote=True)
    safe_company = html.escape(str(company or '-'), quote=True)
    return f"""\
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:600px;margin:0 auto;padding:24px;background:#f5f5f7;color:#1d1d1f;">
  <div style="background:#fff;border-radius:12px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
    <h2 style="margin-top:0;color:#16a34a;">🎉 가입 승인 완료</h2>
    <p>{safe_name}님, GST G-AXIS OPS 가입이 <strong style="color:#16a34a;">승인</strong>되었습니다.</p>

    <div style="background:#f9fafb;border-radius:8px;padding:14px 16px;margin:16px 0;font-size:13px;">
      <p style="margin:4px 0;"><strong>이름:</strong> {safe_name}</p>
      <p style="margin:4px 0;"><strong>역할:</strong> {safe_role}</p>
      <p style="margin:4px 0;"><strong>소속:</strong> {safe_company}</p>
      <p style="margin:4px 0;color:#888;"><strong>승인 시각:</strong> {now_kst} KST</p>
    </div>

    <p style="margin-top:18px;">이제 G-AXIS OPS 앱에 로그인하여 작업을 시작할 수 있습니다.</p>
    <p style="margin-top:12px;"><a href="https://gaxis-ops.netlify.app" style="display:inline-block;padding:10px 18px;background:#007aff;color:#fff;text-decoration:none;border-radius:6px;font-weight:600;">앱 열기</a></p>

    <div style="background:#f3f4f6;border-radius:8px;padding:14px 16px;margin:18px 0;font-size:13px;">
      <p style="margin:0 0 8px 0;font-weight:600;color:#1d1d1f;">🔑 로그인 방법</p>
      <ul style="margin:0;padding-left:18px;color:#555;line-height:1.7;">
        <li>이메일 전체 (예: user@gst-in.com)</li>
        <li>이메일 앞부분 (예: user)</li>
        <li>PIN 4자리 (사전 등록 시)</li>
      </ul>
      <p style="margin:8px 0 0 0;font-size:11px;color:#888;">PIN 설정: 로그인 후 [프로필] → [PIN 설정]</p>
    </div>

    <div style="background:#eef2ff;border-radius:8px;padding:14px 16px;margin:12px 0;font-size:13px;">
      <p style="margin:0 0 6px 0;font-weight:600;color:#1d1d1f;">📖 사용 매뉴얼</p>
      <p style="margin:0;color:#555;">자세한 사용법은 매뉴얼 페이지에서 확인하세요.</p>
      <p style="margin:8px 0 0 0;">
        <a href="https://axis-manual.netlify.app/" style="color:#4f46e5;text-decoration:underline;font-weight:500;">https://axis-manual.netlify.app/</a>
      </p>
    </div>

    <hr style="border:none;border-top:1px solid #e5e5e7;margin:24px 0;">
    <p style="font-size:11px;color:#888;">이 메일은 자동 발송되었습니다. 문의: dkkim1@gst-in.com</p>
  </div>
</body>
</html>
"""


def send_approval_notification(name: str, email: str, role: str, company: str = None) -> bool:
    """
    가입 승인 시 사용자에게 환영 메일 발송 (동기 호출).

    실패해도 승인 처리 자체에는 영향 없음.

    Args:
        name: 사용자 이름
        email: 수신 이메일
        role: 역할 (MECH, ELEC, PI, ...)
        company: 소속 (옵션)

    Returns:
        True: 발송 성공 / False: 실패
    """
    subject = "[G-AXIS OPS] 가입이 승인되었습니다 🎉"
    html_body = _render_approval_html(name=name, role=role, company=company)
    return _send_smtp(to_email=email, subject=subject, html_body=html_body)


def send_approval_notification_async(name: str, email: str, role: str, company: str = None,
                                      worker_id: int = None) -> None:
    """
    가입 승인 메일 발송 (background thread).

    Codex M-Q4 (v2.18.20): admin.py God File 정책 회피 — thread 생성 로직 캡슐화.
    admin.py 라우트에서는 호출 1줄만 사용.

    Args:
        worker_id: 로깅용 (선택)
    """
    import threading

    def _run():
        try:
            send_approval_notification(name=name, email=email, role=role, company=company)
        except Exception as e:
            logger.error(f"승인 메일 발송 실패: worker_id={worker_id}, error={e}")

    try:
        threading.Thread(target=_run, daemon=True).start()
    except Exception as e:
        logger.error(f"승인 메일 스레드 생성 실패: worker_id={worker_id}, error={e}")
