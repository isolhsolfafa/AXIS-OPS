"""
이메일 알림 서비스
Sprint 20-A: 신규 가입 시 Admin 이메일 알림
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta

from app.config import Config
from app.models.worker import get_db_connection

logger = logging.getLogger(__name__)

_KST = timezone(timedelta(hours=9))


def get_admin_emails():
    """DB에서 is_admin=true인 사용자 이메일 목록 조회"""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT email FROM workers WHERE is_admin = true AND email IS NOT NULL")
        return [row['email'] for row in cur.fetchall()]
    finally:
        conn.close()


def _send_email(to_email: str, subject: str, html_body: str) -> bool:
    """smtplib로 이메일 발송 (auth_service.py와 동일한 SMTP 패턴)"""
    if not Config.SMTP_USER:
        logger.info(f"[DEV] Admin notification (SMTP not configured): to={to_email}")
        return True

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
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

        logger.info(f"Email sent: to={to_email}, subject={subject}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed — SMTP_USER/SMTP_PASSWORD 설정을 확인하세요.")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error while sending to {to_email}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error while sending email to {to_email}: {e}")
        return False


def render_register_notification(name: str, email: str, role: str, company: str = None) -> str:
    """신규 가입 알림 HTML 템플릿 생성"""
    now_kst = datetime.now(_KST).strftime('%Y-%m-%d %H:%M')
    company_display = company or '-'

    return f"""
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"></head>
<body style="font-family: sans-serif; background-color: #f5f5f5; padding: 20px;">
  <div style="max-width: 480px; margin: 0 auto; background: #ffffff;
              border-radius: 8px; padding: 32px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
    <h2 style="color: #1a1a2e; margin-bottom: 8px;">AXIS-OPS 신규 가입 알림</h2>
    <p style="color: #555; margin-bottom: 24px;">새로운 작업자가 가입했습니다. 승인 여부를 확인해주세요.</p>
    <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
      <tr>
        <td style="padding: 8px 12px; color: #888; border-bottom: 1px solid #eee;">이름</td>
        <td style="padding: 8px 12px; font-weight: bold; border-bottom: 1px solid #eee;">{name}</td>
      </tr>
      <tr>
        <td style="padding: 8px 12px; color: #888; border-bottom: 1px solid #eee;">이메일</td>
        <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{email}</td>
      </tr>
      <tr>
        <td style="padding: 8px 12px; color: #888; border-bottom: 1px solid #eee;">역할</td>
        <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{role}</td>
      </tr>
      <tr>
        <td style="padding: 8px 12px; color: #888; border-bottom: 1px solid #eee;">협력사</td>
        <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{company_display}</td>
      </tr>
      <tr>
        <td style="padding: 8px 12px; color: #888;">가입일시</td>
        <td style="padding: 8px 12px;">{now_kst}</td>
      </tr>
    </table>
    <p style="color: #888; font-size: 13px;">AXIS-OPS 앱에서 가입 승인 대기 목록을 확인하세요.</p>
  </div>
</body>
</html>
"""


def send_register_notification(name: str, email: str, role: str, company: str = None):
    """신규 가입 시 Admin 전원에게 알림 이메일 발송 (best-effort)"""
    admin_emails = get_admin_emails()
    if not admin_emails:
        logger.warning("Admin 이메일 수신자 없음 (is_admin=true 사용자 없음)")
        return

    subject = f"[AXIS-OPS] 신규 가입: {name} ({company or role})"
    html_body = render_register_notification(name, email, role, company)

    for admin_email in admin_emails:
        try:
            _send_email(to_email=admin_email, subject=subject, html_body=html_body)
        except Exception as e:
            logger.error(f"Admin 알림 발송 실패: {admin_email} — {e}")
