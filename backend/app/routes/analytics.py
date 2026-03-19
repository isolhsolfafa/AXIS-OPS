"""
사용자 분석 API (Sprint 32)
엔드포인트: /api/admin/analytics/*
"""

import logging
from datetime import date, timedelta, timezone, datetime
from typing import Tuple, Dict, Any

from flask import Blueprint, request, jsonify
from psycopg2 import Error as PsycopgError

from app.middleware.jwt_auth import jwt_required, admin_required
from app.db_pool import get_conn, put_conn

logger = logging.getLogger(__name__)

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/admin/analytics")

# 엔드포인트 → 한글 라벨 매핑
_ENDPOINT_LABELS = {
    'product.get_product_by_qr': 'QR 제품 조회',
    'product.get_product': '제품 조회',
    'product.get_sn_progress': 'S/N 진행률',
    'work.get_tasks_by_serial': '작업 목록',
    'work.get_app_settings': '앱 설정',
    'work.start_work': '작업 시작',
    'work.complete_work': '작업 완료',
    'work.complete_single_action': '단일 작업 완료',
    'work.pause_work': '작업 일시정지',
    'work.resume_work': '작업 재개',
    'work.get_completion_by_serial': '공정 완료 현황',
    'auth.get_me': '내 정보',
    'auth.login': '로그인',
    'auth.logout': '로그아웃',
    'auth.pin_login': 'PIN 로그인',
    'auth.pin_status': 'PIN 상태',
    'auth.set_pin': 'PIN 등록',
    'auth.refresh': '토큰 갱신',
    'auth.update_active_role_endpoint': '담당공정 변경',
    'alert.get_alerts': '알림 조회',
    'alert.get_unread_count': '미읽음 알림 수',
    'alert.mark_alert_read': '알림 읽음',
    'alert.mark_all_alerts_read': '전체 알림 읽음',
    'hr.check_attendance': '출퇴근 체크',
    'hr.attendance_check': '출퇴근 체크',
    'hr.get_today_attendance': '오늘 출퇴근',
    'hr.attendance_today': '오늘 출퇴근',
    'admin.get_etl_changes': 'ETL 변경이력',
    'admin.get_pending_workers': '승인 대기 목록',
    'admin.get_workers': '작업자 목록',
    'admin.approve_worker': '작업자 승인',
    'admin.get_admin_settings': '관리자 설정',
    'admin.update_admin_settings': '설정 변경',
    'admin.get_managers': '관리자 목록',
    'admin.toggle_manager': '매니저 권한',
    'admin.force_close_task': '강제 종료',
    'admin.get_attendance_today': '출퇴근 현황',
    'admin.get_attendance_summary': '출퇴근 요약',
    'notices.get_notices': '공지사항',
    'notices.create_notice': '공지 작성',
    'qr.get_qr_list': 'QR 목록',
    'factory.get_monthly_detail': '생산일정',
    'factory.get_weekly_kpi': '주간 KPI',
    'gst.get_gst_products': 'GST 제품 목록',
    'analytics.get_summary': '분석 요약',
    'analytics.get_by_worker': '사용자별 분석',
    'analytics.get_by_endpoint': '기능별 분석',
    'analytics.get_hourly': '시간대별 분석',
}


# ADMIN 요청 제외 조건 (모든 analytics 쿼리에 적용)
_EXCLUDE_ADMIN = "AND worker_role != 'ADMIN'"


def _parse_period(period_str: str) -> int:
    """'7d', '30d' → 일수 반환. 기본 7."""
    try:
        if period_str.endswith('d'):
            return int(period_str[:-1])
    except (ValueError, AttributeError):
        pass
    return 7


@analytics_bp.route("/summary", methods=["GET"])
@jwt_required
@admin_required
def get_summary() -> Tuple[Dict[str, Any], int]:
    """
    기간별 요약 — 접속자 수, 총 요청, 평균 응답시간, 에러율, 일별 추이

    Query: ?period=7d (기본 7d, 최대 90d)
    """
    days = min(90, _parse_period(request.args.get('period', '7d')))
    since = date.today() - timedelta(days=days)
    conn = None

    try:
        conn = get_conn()
        cur = conn.cursor()

        # 전체 요약
        cur.execute(f"""
            SELECT
                COUNT(DISTINCT worker_id) AS unique_users,
                COUNT(*) AS total_requests,
                COALESCE(AVG(duration_ms), 0)::int AS avg_duration_ms,
                ROUND(COUNT(*) FILTER (WHERE status_code >= 400)::numeric
                      / NULLIF(COUNT(*), 0) * 100, 1) AS error_rate
            FROM app_access_log
            WHERE created_at >= %s {_EXCLUDE_ADMIN}
        """, (since,))
        summary = cur.fetchone()

        # 일별 추이
        cur.execute(f"""
            SELECT
                created_at::date AS log_date,
                COUNT(DISTINCT worker_id) AS users,
                COUNT(*) AS requests,
                COUNT(*) FILTER (WHERE status_code >= 400) AS errors
            FROM app_access_log
            WHERE created_at >= %s {_EXCLUDE_ADMIN}
            GROUP BY log_date
            ORDER BY log_date
        """, (since,))
        daily = [
            {
                'date': row['log_date'].isoformat(),
                'users': row['users'],
                'requests': row['requests'],
                'errors': row['errors'],
            }
            for row in cur.fetchall()
        ]

        return jsonify({
            'period': f'{days}d',
            'unique_users': summary['unique_users'],
            'total_requests': summary['total_requests'],
            'avg_duration_ms': summary['avg_duration_ms'],
            'error_rate': float(summary['error_rate'] or 0),
            'daily': daily,
        }), 200

    except PsycopgError as e:
        logger.error(f"analytics summary error: {e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': '데이터 조회 실패'}), 500
    finally:
        if conn:
            put_conn(conn)


@analytics_bp.route("/by-worker", methods=["GET"])
@jwt_required
@admin_required
def get_by_worker() -> Tuple[Dict[str, Any], int]:
    """
    작업자별 사용량 — 요청 수, 첫/마지막 접속, 사용시간, 주요 엔드포인트

    Query: ?period=30d
    """
    days = min(90, _parse_period(request.args.get('period', '30d')))
    since = date.today() - timedelta(days=days)
    conn = None

    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(f"""
            SELECT
                a.worker_id,
                MAX(a.worker_email) AS email,
                MAX(a.worker_role) AS role,
                MAX(w.name) AS name,
                MAX(w.company) AS company,
                COUNT(*) AS total_requests,
                MIN(a.created_at) AS first_access,
                MAX(a.created_at) AS last_access,
                EXTRACT(EPOCH FROM (MAX(a.created_at) - MIN(a.created_at))) / 60 AS usage_minutes
            FROM app_access_log a
            LEFT JOIN workers w ON a.worker_id = w.id
            WHERE a.created_at >= %s AND a.worker_id IS NOT NULL {_EXCLUDE_ADMIN}
            GROUP BY a.worker_id
            ORDER BY total_requests DESC
            LIMIT 100
        """, (since,))
        rows = cur.fetchall()

        workers = []
        for row in rows:
            # 상위 엔드포인트
            cur.execute("""
                SELECT endpoint, COUNT(*) AS cnt
                FROM app_access_log
                WHERE worker_id = %s AND created_at >= %s
                GROUP BY endpoint
                ORDER BY cnt DESC
                LIMIT 5
            """, (row['worker_id'], since))
            top = [_ENDPOINT_LABELS.get(r['endpoint'], r['endpoint']) for r in cur.fetchall()]

            workers.append({
                'worker_id': row['worker_id'],
                'name': row['name'],
                'email': row['email'],
                'role': row['role'],
                'company': row['company'],
                'total_requests': row['total_requests'],
                'first_access': row['first_access'].isoformat() if row['first_access'] else None,
                'last_access': row['last_access'].isoformat() if row['last_access'] else None,
                'usage_minutes': round(row['usage_minutes'] or 0, 1),
                'top_endpoints': top,
            })

        return jsonify({'period': f'{days}d', 'workers': workers}), 200

    except PsycopgError as e:
        logger.error(f"analytics by-worker error: {e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': '데이터 조회 실패'}), 500
    finally:
        if conn:
            put_conn(conn)


@analytics_bp.route("/by-endpoint", methods=["GET"])
@jwt_required
@admin_required
def get_by_endpoint() -> Tuple[Dict[str, Any], int]:
    """
    엔드포인트별 사용량 — 호출 수, 평균 응답시간, 에러율

    Query: ?period=7d
    """
    days = min(90, _parse_period(request.args.get('period', '7d')))
    since = date.today() - timedelta(days=days)
    conn = None

    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(f"""
            SELECT
                endpoint,
                COUNT(*) AS count,
                COALESCE(AVG(duration_ms), 0)::int AS avg_ms,
                ROUND(COUNT(*) FILTER (WHERE status_code >= 400)::numeric
                      / NULLIF(COUNT(*), 0) * 100, 1) AS error_rate
            FROM app_access_log
            WHERE created_at >= %s {_EXCLUDE_ADMIN}
            GROUP BY endpoint
            ORDER BY count DESC
            LIMIT 50
        """, (since,))

        endpoints = [
            {
                'endpoint': row['endpoint'],
                'label': _ENDPOINT_LABELS.get(row['endpoint'], row['endpoint']),
                'count': row['count'],
                'avg_ms': row['avg_ms'],
                'error_rate': float(row['error_rate'] or 0),
            }
            for row in cur.fetchall()
        ]

        return jsonify({'period': f'{days}d', 'endpoints': endpoints}), 200

    except PsycopgError as e:
        logger.error(f"analytics by-endpoint error: {e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': '데이터 조회 실패'}), 500
    finally:
        if conn:
            put_conn(conn)


@analytics_bp.route("/hourly", methods=["GET"])
@jwt_required
@admin_required
def get_hourly() -> Tuple[Dict[str, Any], int]:
    """
    시간대별 요청 분포 (특정 날짜)

    Query: ?date=2026-03-18 (기본: 오늘)
    """
    date_str = request.args.get('date')
    try:
        target_date = date.fromisoformat(date_str) if date_str else date.today()
    except ValueError:
        return jsonify({'error': 'INVALID_DATE', 'message': 'date 형식은 YYYY-MM-DD'}), 400

    conn = None

    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(f"""
            SELECT
                EXTRACT(HOUR FROM created_at AT TIME ZONE 'Asia/Seoul')::int AS hour,
                COUNT(*) AS requests,
                COUNT(DISTINCT worker_id) AS users
            FROM app_access_log
            WHERE created_at::date = %s {_EXCLUDE_ADMIN}
            GROUP BY hour
            ORDER BY hour
        """, (target_date,))

        hours = [
            {'hour': row['hour'], 'requests': row['requests'], 'users': row['users']}
            for row in cur.fetchall()
        ]

        return jsonify({'date': target_date.isoformat(), 'hours': hours}), 200

    except PsycopgError as e:
        logger.error(f"analytics hourly error: {e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': '데이터 조회 실패'}), 500
    finally:
        if conn:
            put_conn(conn)
