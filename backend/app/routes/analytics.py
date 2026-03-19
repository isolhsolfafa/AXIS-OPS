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
        cur.execute("""
            SELECT
                COUNT(DISTINCT worker_id) AS unique_users,
                COUNT(*) AS total_requests,
                COALESCE(AVG(duration_ms), 0)::int AS avg_duration_ms,
                ROUND(COUNT(*) FILTER (WHERE status_code >= 400)::numeric
                      / NULLIF(COUNT(*), 0) * 100, 1) AS error_rate
            FROM app_access_log
            WHERE created_at >= %s
        """, (since,))
        summary = cur.fetchone()

        # 일별 추이
        cur.execute("""
            SELECT
                created_at::date AS log_date,
                COUNT(DISTINCT worker_id) AS users,
                COUNT(*) AS requests,
                COUNT(*) FILTER (WHERE status_code >= 400) AS errors
            FROM app_access_log
            WHERE created_at >= %s
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

        cur.execute("""
            SELECT
                worker_id,
                MAX(worker_email) AS email,
                MAX(worker_role) AS role,
                COUNT(*) AS total_requests,
                MIN(created_at) AS first_access,
                MAX(created_at) AS last_access,
                EXTRACT(EPOCH FROM (MAX(created_at) - MIN(created_at))) / 60 AS usage_minutes
            FROM app_access_log
            WHERE created_at >= %s AND worker_id IS NOT NULL
            GROUP BY worker_id
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
            top = [r['endpoint'] for r in cur.fetchall()]

            workers.append({
                'worker_id': row['worker_id'],
                'email': row['email'],
                'role': row['role'],
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

        cur.execute("""
            SELECT
                endpoint,
                COUNT(*) AS count,
                COALESCE(AVG(duration_ms), 0)::int AS avg_ms,
                ROUND(COUNT(*) FILTER (WHERE status_code >= 400)::numeric
                      / NULLIF(COUNT(*), 0) * 100, 1) AS error_rate
            FROM app_access_log
            WHERE created_at >= %s
            GROUP BY endpoint
            ORDER BY count DESC
            LIMIT 50
        """, (since,))

        endpoints = [
            {
                'endpoint': row['endpoint'],
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

        cur.execute("""
            SELECT
                EXTRACT(HOUR FROM created_at AT TIME ZONE 'Asia/Seoul')::int AS hour,
                COUNT(*) AS requests,
                COUNT(DISTINCT worker_id) AS users
            FROM app_access_log
            WHERE created_at::date = %s
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
