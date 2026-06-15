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
      <p style="margin:0;color:#555;line-height:1.6;">
        앱 로그인 후 상단 <strong>[📖 매뉴얼]</strong> 버튼을 통해 접근 가능합니다.<br>
        <span style="font-size:11px;color:#888;">보안상 직접 URL 접근은 차단되어 있습니다.</span>
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


# ─── Sprint 79: 출하 미처리 알림 메일 ──────────────────────────────────

def _render_completed_section(completed_items: list) -> str:
    """Sprint 95: 어제 출하 완료 섹션 (참고) — 항상 표시(health check, 0건도 표시)."""
    completed = completed_items or []
    ccount = len(completed)
    crows = ""
    for item in completed:
        cs_sn = html.escape(str(item.get('serial_number', '-')), quote=True)
        cs_so = html.escape(str(item.get('sales_order', '-') or '-'), quote=True)
        cs_model = html.escape(str(item.get('model', '-') or '-'), quote=True)
        crows += (
            f'<tr><td style="padding:6px;border-bottom:1px solid #d1fae5;font-weight:600;">{cs_sn}</td>'
            f'<td style="padding:6px;border-bottom:1px solid #d1fae5;color:#555;">{cs_so}</td>'
            f'<td style="padding:6px;border-bottom:1px solid #d1fae5;color:#555;">{cs_model}</td></tr>'
        )
    inner = (
        '<table style="width:100%;border-collapse:collapse;font-size:12px;"><thead>'
        '<tr style="background:#d1fae5;">'
        '<th style="padding:6px;text-align:left;font-size:11px;color:#065f46;">S/N</th>'
        '<th style="padding:6px;text-align:left;font-size:11px;color:#065f46;">O/N</th>'
        '<th style="padding:6px;text-align:left;font-size:11px;color:#065f46;">모델</th>'
        f'</tr></thead><tbody>{crows}</tbody></table>'
    ) if ccount else '<p style="margin:0;color:#888;">어제 출하 완료된 건이 없습니다.</p>'
    return f"""
    <div style="background:#ecfdf5;border-radius:8px;padding:14px 16px;margin:16px 0;font-size:13px;">
      <p style="margin:0 0 8px 0;font-weight:600;color:#059669;">✅ 어제 출하 완료 — {ccount}건</p>
      {inner}
    </div>"""


def _render_shipment_overdue_html(overdue_items: list, target_date, completed_items: list = None) -> str:
    """출하 미처리 알림 HTML 템플릿 (Sprint 79, v2.19.10).

    v2.19.10: 회원가입 승인 메일 컨셉 정합 (사용자 catch 5-28).
    v2.20.5: overdue_items=[] 분기 추가 — "전일 출하 모두 완료" 메일 (daily health check).
    Sprint 95: completed_items(어제 출하 완료) 섹션 추가 — 출하 현황 종합.
    """
    target_str = target_date.strftime('%Y-%m-%d') if hasattr(target_date, 'strftime') else str(target_date)
    now_kst = datetime.now(_KST).strftime('%Y-%m-%d %H:%M')
    safe_date = html.escape(target_str, quote=True)
    count = len(overdue_items)
    completed_section = _render_completed_section(completed_items)

    # v2.20.5: 0건 분기 — "전일 출하 모두 완료" 메일 (daily health check)
    if count == 0:
        return f"""\
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:600px;margin:0 auto;padding:24px;background:#f5f5f7;color:#1d1d1f;">
  <div style="background:#fff;border-radius:12px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
    <h2 style="margin-top:0;color:#059669;">✅ 출하 완료 알림</h2>
    <p>어제 ({safe_date}) 출하 계획이 <strong style="color:#059669;">모두 정상 처리</strong> 되었습니다.</p>

    <div style="background:#f9fafb;border-radius:8px;padding:14px 16px;margin:16px 0;font-size:13px;">
      <p style="margin:4px 0;"><strong>대상 일자:</strong> {safe_date} (어제)</p>
      <p style="margin:4px 0;"><strong>미처리 건수:</strong> <strong style="color:#059669;">0건 ✅</strong></p>
      <p style="margin:4px 0;color:#888;"><strong>발송 시각:</strong> {now_kst} KST</p>
    </div>
{completed_section}
    <p style="margin-top:18px;">이 메일은 출하 알림 시스템이 매일 정상 작동 중임을 확인하는 메일입니다.</p>

    <hr style="border:none;border-top:1px solid #e5e5e7;margin:24px 0;">
    <p style="font-size:11px;color:#888;">이 메일은 매일 07:30 KST 자동 발송됩니다. 수신자 변경: OPS 관리자 옵션 → 출하 미처리 알림. 문의: dkkim1@gst-in.com</p>
  </div>
</body>
</html>
"""

    rows_html = ""
    for item in overdue_items:
        safe_sn = html.escape(str(item.get('serial_number', '-')), quote=True)
        safe_so = html.escape(str(item.get('sales_order', '-') or '-'), quote=True)
        safe_model = html.escape(str(item.get('model', '-') or '-'), quote=True)
        safe_customer = html.escape(str(item.get('customer', '-') or '-'), quote=True)
        safe_mech = html.escape(str(item.get('mech_partner', '-') or '-'), quote=True)
        safe_elec = html.escape(str(item.get('elec_partner', '-') or '-'), quote=True)
        rows_html += f"""
        <tr>
          <td style="padding:8px 6px;border-bottom:1px solid #e5e7eb;font-weight:600;color:#1d1d1f;">{safe_sn}</td>
          <td style="padding:8px 6px;border-bottom:1px solid #e5e7eb;color:#555;">{safe_so}</td>
          <td style="padding:8px 6px;border-bottom:1px solid #e5e7eb;color:#555;">{safe_model}</td>
          <td style="padding:8px 6px;border-bottom:1px solid #e5e7eb;color:#555;">{safe_customer}</td>
          <td style="padding:8px 6px;border-bottom:1px solid #e5e7eb;color:#888;font-size:11px;">{safe_mech} / {safe_elec}</td>
        </tr>"""

    return f"""\
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:600px;margin:0 auto;padding:24px;background:#f5f5f7;color:#1d1d1f;">
  <div style="background:#fff;border-radius:12px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
    <h2 style="margin-top:0;color:#d97706;">⚠️ 출하 미처리 알림</h2>
    <p>어제 ({safe_date}) 출하 계획 <strong style="color:#d97706;">{count}건</strong>이 미처리 상태입니다. 즉시 확인 부탁드립니다.</p>

    <div style="background:#f9fafb;border-radius:8px;padding:14px 16px;margin:16px 0;font-size:13px;">
      <p style="margin:4px 0;"><strong>대상 일자:</strong> {safe_date} (어제)</p>
      <p style="margin:4px 0;"><strong>미처리 건수:</strong> <strong style="color:#d97706;">{count}건</strong></p>
      <p style="margin:4px 0;color:#888;"><strong>발송 시각:</strong> {now_kst} KST</p>
    </div>

    <div style="background:#f9fafb;border-radius:8px;padding:14px 16px;margin:16px 0;font-size:13px;">
      <p style="margin:0 0 10px 0;font-weight:600;color:#1d1d1f;">📋 미처리 list</p>
      <table style="width:100%;border-collapse:collapse;font-size:12px;">
        <thead>
          <tr style="background:#f3f4f6;">
            <th style="padding:8px 6px;text-align:left;font-size:11px;color:#888;border-bottom:1px solid #e5e7eb;">S/N</th>
            <th style="padding:8px 6px;text-align:left;font-size:11px;color:#888;border-bottom:1px solid #e5e7eb;">O/N</th>
            <th style="padding:8px 6px;text-align:left;font-size:11px;color:#888;border-bottom:1px solid #e5e7eb;">모델</th>
            <th style="padding:8px 6px;text-align:left;font-size:11px;color:#888;border-bottom:1px solid #e5e7eb;">고객사</th>
            <th style="padding:8px 6px;text-align:left;font-size:11px;color:#888;border-bottom:1px solid #e5e7eb;">협력사 M/E</th>
          </tr>
        </thead>
        <tbody>{rows_html}
        </tbody>
      </table>
    </div>
{completed_section}
    <p style="margin-top:18px;">OPS 앱에서 출하 처리 부탁드립니다.</p>
    <p style="margin-top:12px;"><a href="https://gaxis-ops.netlify.app" style="display:inline-block;padding:10px 18px;background:#007aff;color:#fff;text-decoration:none;border-radius:6px;font-weight:600;">앱 열기</a></p>

    <div style="background:#eef2ff;border-radius:8px;padding:14px 16px;margin:18px 0;font-size:13px;">
      <p style="margin:0 0 6px 0;font-weight:600;color:#1d1d1f;">📍 OPS 접속 경로</p>
      <p style="margin:0;color:#555;line-height:1.6;">
        앱 로그인 후 <strong>[SI 마무리공정]</strong> → <strong>[출하 확정]</strong> 탭에서 직접 출고 완료 처리.<br>
        <span style="font-size:11px;color:#888;">검색이 필요한 경우 [출하 예정] 탭에서 S/N · O/N 검색 후 처리 가능합니다.</span>
      </p>
    </div>

    <hr style="border:none;border-top:1px solid #e5e5e7;margin:24px 0;">
    <p style="font-size:11px;color:#888;">이 메일은 매일 07:30 KST 자동 발송됩니다. 수신자 변경: OPS 관리자 옵션 → 출하 미처리 알림. 문의: dkkim1@gst-in.com</p>
  </div>
</body>
</html>
"""


def send_shipment_overdue_alert(recipients: list, overdue_items: list, target_date, completed_items: list = None) -> bool:
    """출하 미처리 알림 메일 발송 (Sprint 79 + Sprint 95 출하 완료 리스트).

    Args:
        recipients: 수신자 email list
        overdue_items: get_overdue_shipments() 결과
        target_date: 어제 날짜 (date)

    Returns:
        True = 모든 수신자 발송 성공, False = 일부 실패

    Codex Q3 A: retry catch X — 실패 로그 + Sentry capture (LoggingIntegration ERROR).
    """
    # v2.20.5: overdue_items=0건 이어도 발송 (daily health check 메일)
    if not recipients:
        logger.info(f"[shipment_overdue_alert] skip — recipients=0")
        return False

    target_str = target_date.strftime('%Y-%m-%d') if hasattr(target_date, 'strftime') else str(target_date)
    overdue_count = len(overdue_items)
    completed_count = len(completed_items or [])
    # Sprint 95: 기존 prefix(⚠️/✅) 유지(메일 필터 호환) + 완료 정보 부가
    if overdue_count > 0:
        subject = f"⚠️ [G-AXIS] 출하 미처리 {overdue_count}건 (완료 {completed_count}건) ({target_str})"
    else:
        subject = f"✅ [G-AXIS] 출하 완료 {completed_count}건 ({target_str})"
    html_body = _render_shipment_overdue_html(overdue_items, target_date, completed_items)

    success_count = 0
    fail_count = 0

    for email in recipients:
        if not email or '@' not in email:
            logger.warning(f"[shipment_overdue_alert] invalid email skip: {email}")
            fail_count += 1
            continue

        try:
            ok = _send_smtp(to_email=email, subject=subject, html_body=html_body)
            if ok:
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            logger.error(f"[shipment_overdue_alert] send error: to={email}, error={e}")
            fail_count += 1

    logger.info(
        f"[shipment_overdue_alert] sent: success={success_count}, fail={fail_count}, "
        f"target_date={target_str}, overdue={len(overdue_items)}"
    )
    return fail_count == 0
