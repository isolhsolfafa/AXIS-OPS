"""
관리자 라우트
엔드포인트: /api/admin/*
Sprint 4: 관리자 전용 API (승인, 대시보드, 작업 수정)
Sprint 6 Phase C: PUT /api/admin/tasks/{task_id}/force-close 추가
Sprint 19-E: VIEW용 Admin 출퇴근 API 3개 추가
"""

import logging
import re
from flask import Blueprint, request, jsonify, g
from typing import Tuple, Dict, Any, List, Optional
from datetime import date, datetime, timezone, timedelta
from collections import defaultdict

from app.config import Config
from app.middleware.jwt_auth import jwt_required, admin_required, manager_or_admin_required, view_access_required
from app.models.worker import (
    get_db_connection, update_approval_status, get_worker_by_id,
    get_inactive_workers, get_deactivated_workers, deactivate_worker, reactivate_worker,
)
from app.models.admin_settings import get_all_settings, update_setting
from app.services.alert_service import create_and_broadcast_alert

# ─── Sprint 34: 설정 키 레지스트리 ───────────────────────────────
SETTING_KEYS: Dict[str, Dict[str, Any]] = {
    # bool
    'heating_jacket_enabled':     {'type': 'bool', 'default': False},
    'phase_block_enabled':        {'type': 'bool', 'default': False},
    'location_qr_required':       {'type': 'bool', 'default': True},
    'auto_pause_enabled':         {'type': 'bool', 'default': True},
    'geo_check_enabled':          {'type': 'bool', 'default': False},
    'geo_strict_mode':            {'type': 'bool', 'default': False},
    'confirm_mech_enabled':       {'type': 'bool', 'default': True},
    'confirm_elec_enabled':       {'type': 'bool', 'default': True},
    'confirm_tm_enabled':         {'type': 'bool', 'default': True},
    'confirm_pi_enabled':         {'type': 'bool', 'default': False},
    'confirm_qi_enabled':         {'type': 'bool', 'default': False},
    'confirm_si_enabled':         {'type': 'bool', 'default': False},
    'confirm_checklist_required': {'type': 'bool', 'default': False},
    # time (HH:MM)
    'break_morning_start':    {'type': 'time', 'default': '10:00', 'pair': 'break_morning_end'},
    'break_morning_end':      {'type': 'time', 'default': '10:20', 'pair': 'break_morning_start'},
    'break_afternoon_start':  {'type': 'time', 'default': '15:00', 'pair': 'break_afternoon_end'},
    'break_afternoon_end':    {'type': 'time', 'default': '15:20', 'pair': 'break_afternoon_start'},
    'lunch_start':            {'type': 'time', 'default': '11:20', 'pair': 'lunch_end'},
    'lunch_end':              {'type': 'time', 'default': '12:20', 'pair': 'lunch_start'},
    'dinner_start':           {'type': 'time', 'default': '17:00', 'pair': 'dinner_end'},
    'dinner_end':             {'type': 'time', 'default': '18:00', 'pair': 'dinner_start'},
    # number
    'geo_latitude':           {'type': 'number', 'default': 35.1796},
    'geo_longitude':          {'type': 'number', 'default': 129.0756},
    'geo_radius_meters':      {'type': 'number', 'default': 200, 'min': 50, 'max': 5000},
    # bool — Sprint 37-A TM 가압검사 옵션
    'tm_pressure_test_required': {'type': 'bool', 'default': True},
    # string_list (JSON 배열) — Sprint 31C PI 위임
    'pi_capable_mech_partners': {'type': 'string_list', 'default': []},
    'pi_gst_override_lines':    {'type': 'string_list', 'default': []},
    # string — Sprint 52 TM 체크리스트 옵션
    'tm_checklist_1st_checker': {'type': 'string', 'default': 'is_manager', 'allowed': ['is_manager', 'user']},
    'tm_checklist_issue_alert': {'type': 'bool', 'default': True},
    'tm_checklist_scope':       {'type': 'string', 'default': 'all', 'allowed': ['product_code', 'all']},
    # bool — Sprint 54 알림 트리거 on/off
    'alert_tm_to_mech_enabled':              {'type': 'bool', 'default': True},
    'alert_mech_to_elec_enabled':            {'type': 'bool', 'default': True},
    'alert_elec_to_pi_enabled':              {'type': 'bool', 'default': False},
    'alert_mech_pressure_to_qi_enabled':     {'type': 'bool', 'default': False},
    'alert_tm_tank_module_to_elec_enabled':  {'type': 'bool', 'default': False},
}

ALLOWED_KEYS = set(SETTING_KEYS.keys())

_TIME_PATTERN = re.compile(r'^([01]\d|2[0-3]):[0-5]\d$')


def _validate_setting(key: str, value: Any) -> str | None:
    """설정 값 타입 검증. 에러 시 메시지 반환, 정상이면 None."""
    meta = SETTING_KEYS.get(key)
    if not meta:
        return f'허용되지 않은 설정 키: {key}'

    stype = meta['type']

    if stype == 'bool':
        if not isinstance(value, bool):
            return f'{key}: bool 타입이어야 합니다.'

    elif stype == 'time':
        if not isinstance(value, str) or not _TIME_PATTERN.match(value):
            return f'{key}: HH:MM 형식이어야 합니다. (예: "10:00")'

    elif stype == 'number':
        if not isinstance(value, (int, float)):
            return f'{key}: 숫자 타입이어야 합니다.'
        if 'min' in meta and value < meta['min']:
            return f'{key}: 최소값은 {meta["min"]}입니다.'
        if 'max' in meta and value > meta['max']:
            return f'{key}: 최대값은 {meta["max"]}입니다.'

    elif stype == 'string_list':
        if not isinstance(value, list):
            return f'{key}: 배열 타입이어야 합니다. (예: ["TMS"])'
        for i, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                return f'{key}[{i}]: 빈 문자열이 아닌 문자열이어야 합니다.'
        if len(value) != len(set(value)):
            return f'{key}: 중복 값이 포함되어 있습니다.'

    elif stype == 'string':
        allowed = meta.get('allowed')
        if allowed and value not in allowed:
            return f'{key}는 {allowed} 중 하나여야 합니다. (입력값: {value})'
        return None

    return None
from app.services.scheduler_service import trigger_unfinished_task_check_manually
from app.services.task_service import _calculate_working_minutes
from psycopg2 import Error as PsycopgError
from app.db_pool import put_conn


logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.route("/workers/approve", methods=["POST"])
@jwt_required
@admin_required
def approve_worker() -> Tuple[Dict[str, Any], int]:
    """
    작업자 승인/거부

    Request Body:
        {
            "worker_id": int,
            "approved": bool
        }

    Headers:
        Authorization: Bearer {token}

    Returns:
        200: {"message": "작업자 승인 완료", "worker_id": int, "status": str}
        400: {"error": "INVALID_REQUEST", "message": "..."}
        404: {"error": "WORKER_NOT_FOUND", "message": "..."}
        500: {"error": "INTERNAL_SERVER_ERROR", "message": "..."}
    """
    data = request.get_json()

    if not data:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': '요청 본문이 필요합니다.'
        }), 400

    worker_id = data.get('worker_id')
    approved = data.get('approved')

    if worker_id is None or approved is None:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'worker_id와 approved 필드가 필요합니다.'
        }), 400

    # worker 존재 확인
    worker = get_worker_by_id(worker_id)
    if not worker:
        return jsonify({
            'error': 'WORKER_NOT_FOUND',
            'message': '작업자를 찾을 수 없습니다.'
        }), 404

    # 승인 상태 업데이트
    status = 'approved' if approved else 'rejected'
    success = update_approval_status(worker_id, status)

    if not success:
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '승인 상태 업데이트에 실패했습니다.'
        }), 500

    # 알림 생성
    alert_type = 'WORKER_APPROVED' if approved else 'WORKER_REJECTED'
    message = f"가입 신청이 {'승인' if approved else '거부'}되었습니다."

    create_and_broadcast_alert({
        'alert_type': alert_type,
        'message': message,
        'triggered_by_worker_id': g.worker_id,  # 관리자
        'target_worker_id': worker_id
    })

    logger.info(f"Worker approval updated: worker_id={worker_id}, status={status}, by_admin={g.worker_id}")

    return jsonify({
        'message': f"작업자 {'승인' if approved else '거부'} 완료",
        'worker_id': worker_id,
        'status': status
    }), 200


@admin_bp.route("/workers/pending", methods=["GET"])
@jwt_required
@admin_required
def get_pending_workers() -> Tuple[Dict[str, Any], int]:
    """
    승인 대기 중인 작업자 목록

    Query Parameters:
        limit: int (default: 50)

    Headers:
        Authorization: Bearer {token}

    Returns:
        200: {
            "workers": [{
                "id": int,
                "name": str,
                "email": str,
                "role": str,
                "is_manager": bool,
                "created_at": str
            }],
            "total": int
        }
    """
    limit = request.args.get('limit', 50, type=int)

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT id, name, email, role, company, is_manager, created_at
            FROM workers
            WHERE approval_status = 'pending'
              AND email_verified = TRUE
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,)
        )

        rows = cur.fetchall()

        workers = [
            {
                'id': row['id'],
                'name': row['name'],
                'email': row['email'],
                'role': row['role'],
                'company': row['company'],
                'is_manager': row['is_manager'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None
            }
            for row in rows
        ]

        return jsonify({
            'workers': workers,
            'total': len(workers)
        }), 200

    except PsycopgError as e:
        logger.error(f"Failed to get pending workers: {e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '승인 대기 목록 조회에 실패했습니다.'
        }), 500
    finally:
        if conn:
            put_conn(conn)


@admin_bp.route("/workers", methods=["GET"])
@jwt_required
@manager_or_admin_required
def get_workers() -> Tuple[Dict[str, Any], int]:
    """
    작업자 목록 조회 (필터링 지원)

    Query Parameters:
        approval_status: str (optional: pending, approved, rejected)
        role: str (optional: MM, EE, TM, PI, QI, SI)
        limit: int (default: 50)

    Headers:
        Authorization: Bearer {token}

    Returns:
        200: {
            "workers": [{
                "id": int,
                "name": str,
                "email": str,
                "role": str,
                "approval_status": str,
                "email_verified": bool,
                "is_manager": bool,
                "is_admin": bool,
                "created_at": str
            }],
            "total": int
        }
    """
    approval_status = request.args.get('approval_status')
    role = request.args.get('role')
    company_filter = request.args.get('company')
    is_manager_filter = request.args.get('is_manager')
    limit = min(500, request.args.get('limit', 200, type=int))

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 동적 쿼리 생성
        where_clauses = []
        params: List[Any] = []

        # Manager: 자사 소속만 필터
        current_worker = get_worker_by_id(g.worker_id)
        if current_worker and current_worker.is_manager and not current_worker.is_admin:
            where_clauses.append("company = %s")
            params.append(current_worker.company)

        if approval_status:
            where_clauses.append("approval_status = %s")
            params.append(approval_status)

        if role:
            where_clauses.append("role = %s")
            params.append(role)

        # Sprint 34: company 필터
        if company_filter:
            where_clauses.append("company = %s")
            params.append(company_filter)

        # Sprint 34: is_manager 필터
        if is_manager_filter is not None:
            if is_manager_filter.lower() in ('true', '1'):
                where_clauses.append("(is_manager = TRUE OR is_admin = TRUE)")
            elif is_manager_filter.lower() in ('false', '0'):
                where_clauses.append("is_manager = FALSE AND is_admin = FALSE")

        where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"
        params.append(limit)

        query = f"""
            SELECT id, name, email, role, company, approval_status,
                   email_verified, is_manager, is_admin, created_at
            FROM workers
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT %s
        """

        cur.execute(query, tuple(params))
        rows = cur.fetchall()

        workers = [
            {
                'id': row['id'],
                'name': row['name'],
                'email': row['email'],
                'role': row['role'],
                'company': row.get('company'),
                'approval_status': row['approval_status'],
                'email_verified': row['email_verified'],
                'is_manager': row['is_manager'],
                'is_admin': row['is_admin'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None
            }
            for row in rows
        ]

        return jsonify({
            'workers': workers,
            'total': len(workers)
        }), 200

    except PsycopgError as e:
        logger.error(f"Failed to get workers: {e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '작업자 목록 조회에 실패했습니다.'
        }), 500
    finally:
        if conn:
            put_conn(conn)


@admin_bp.route("/dashboard/process-summary", methods=["GET"])
@jwt_required
@admin_required
def get_process_summary() -> Tuple[Dict[str, Any], int]:
    """
    공정별 작업 요약 통계

    Query Parameters:
        date: str (optional, YYYY-MM-DD, default: today)

    Headers:
        Authorization: Bearer {token}

    Returns:
        200: {
            "summary": [{
                "process_type": str,  // MECH, ELEC, TM, PI, QI, SI
                "total_tasks": int,
                "completed_tasks": int,
                "in_progress_tasks": int,
                "not_started_tasks": int,
                "completion_rate": float  // 0-100
            }],
            "date": str
        }
    """
    date_param = request.args.get('date')

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 날짜 조건 (지정되지 않으면 오늘)
        if date_param:
            try:
                date_filter = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'error': 'INVALID_REQUEST',
                    'message': '날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)'
                }), 400
        else:
            date_filter = datetime.now(Config.KST).date()

        cur.execute(
            """
            SELECT
                task_category,
                COUNT(*) as total_tasks,
                COUNT(CASE WHEN completed_at IS NOT NULL THEN 1 END) as completed_tasks,
                COUNT(CASE WHEN started_at IS NOT NULL AND completed_at IS NULL THEN 1 END) as in_progress_tasks,
                COUNT(CASE WHEN started_at IS NULL THEN 1 END) as not_started_tasks
            FROM app_task_details
            WHERE DATE(created_at) = %s AND is_applicable = TRUE
            GROUP BY task_category
            ORDER BY task_category
            """,
            (date_filter,)
        )

        rows = cur.fetchall()

        summary = []
        for row in rows:
            total = row['total_tasks']
            completed = row['completed_tasks']
            completion_rate = (completed / total * 100) if total > 0 else 0.0

            summary.append({
                'process_type': row['task_category'],
                'total_tasks': total,
                'completed_tasks': completed,
                'in_progress_tasks': row['in_progress_tasks'],
                'not_started_tasks': row['not_started_tasks'],
                'completion_rate': round(completion_rate, 1)
            })

        return jsonify({
            'summary': summary,
            'date': date_filter.isoformat()
        }), 200

    except PsycopgError as e:
        logger.error(f"Failed to get process summary: {e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '공정 요약 조회에 실패했습니다.'
        }), 500
    finally:
        if conn:
            put_conn(conn)


@admin_bp.route("/dashboard/active-tasks", methods=["GET"])
@jwt_required
@admin_required
def get_active_tasks() -> Tuple[Dict[str, Any], int]:
    """
    현재 진행 중인 작업 목록

    Query Parameters:
        limit: int (default: 20)

    Headers:
        Authorization: Bearer {token}

    Returns:
        200: {
            "tasks": [{
                "id": int,
                "worker_id": int,
                "worker_name": str,
                "serial_number": str,
                "qr_doc_id": str,
                "task_category": str,
                "task_name": str,
                "started_at": str,
                "duration_minutes": int  // 현재까지 경과 시간
            }],
            "total": int
        }
    """
    limit = request.args.get('limit', 20, type=int)

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                t.id,
                t.worker_id,
                w.name as worker_name,
                t.serial_number,
                t.qr_doc_id,
                t.task_category,
                t.task_name,
                t.started_at,
                EXTRACT(EPOCH FROM (NOW() - t.started_at)) / 60 AS duration_minutes
            FROM app_task_details t
            JOIN workers w ON t.worker_id = w.id
            WHERE t.started_at IS NOT NULL
              AND t.completed_at IS NULL
              AND t.is_applicable = TRUE
            ORDER BY t.started_at DESC
            LIMIT %s
            """,
            (limit,)
        )

        rows = cur.fetchall()

        tasks = [
            {
                'id': row['id'],
                'worker_id': row['worker_id'],
                'worker_name': row['worker_name'],
                'serial_number': row['serial_number'],
                'qr_doc_id': row['qr_doc_id'],
                'task_category': row['task_category'],
                'task_name': row['task_name'],
                'started_at': row['started_at'].isoformat() if row['started_at'] else None,
                'duration_minutes': int(row['duration_minutes']) if row['duration_minutes'] else 0
            }
            for row in rows
        ]

        return jsonify({
            'tasks': tasks,
            'total': len(tasks)
        }), 200

    except PsycopgError as e:
        logger.error(f"Failed to get active tasks: {e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '진행 중인 작업 조회에 실패했습니다.'
        }), 500
    finally:
        if conn:
            put_conn(conn)


@admin_bp.route("/dashboard/alerts-summary", methods=["GET"])
@jwt_required
@admin_required
def get_alerts_summary() -> Tuple[Dict[str, Any], int]:
    """
    알림 요약 통계

    Query Parameters:
        start_date: str (optional, YYYY-MM-DD)
        end_date: str (optional, YYYY-MM-DD)

    Headers:
        Authorization: Bearer {token}

    Returns:
        200: {
            "summary": {
                "total": int,
                "unread": int,
                "by_type": {
                    "PROCESS_READY": int,
                    "UNFINISHED_AT_CLOSING": int,
                    "DURATION_EXCEEDED": int,
                    "REVERSE_COMPLETION": int,
                    "DUPLICATE_COMPLETION": int,
                    "LOCATION_QR_FAILED": int,
                    "WORKER_APPROVED": int,
                    "WORKER_REJECTED": int
                }
            },
            "start_date": str,
            "end_date": str
        }
    """
    start_date_param = request.args.get('start_date')
    end_date_param = request.args.get('end_date')

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 날짜 범위 설정
        params = []
        date_filter = ""

        if start_date_param:
            try:
                start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
                date_filter += " AND DATE(created_at) >= %s"
                params.append(start_date)
            except ValueError:
                return jsonify({
                    'error': 'INVALID_REQUEST',
                    'message': 'start_date 형식이 올바르지 않습니다. (YYYY-MM-DD)'
                }), 400
        else:
            start_date = None

        if end_date_param:
            try:
                end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()
                date_filter += " AND DATE(created_at) <= %s"
                params.append(end_date)
            except ValueError:
                return jsonify({
                    'error': 'INVALID_REQUEST',
                    'message': 'end_date 형식이 올바르지 않습니다. (YYYY-MM-DD)'
                }), 400
        else:
            end_date = None

        # 총 알림 수
        cur.execute(
            f"SELECT COUNT(*) as total FROM app_alert_logs WHERE TRUE {date_filter}",
            tuple(params)
        )
        total = cur.fetchone()['total']

        # 읽지 않은 알림 수
        cur.execute(
            f"SELECT COUNT(*) as unread FROM app_alert_logs WHERE is_read = FALSE {date_filter}",
            tuple(params)
        )
        unread = cur.fetchone()['unread']

        # 타입별 알림 수
        cur.execute(
            f"""
            SELECT alert_type, COUNT(*) as count
            FROM app_alert_logs
            WHERE TRUE {date_filter}
            GROUP BY alert_type
            """,
            tuple(params)
        )
        type_rows = cur.fetchall()

        by_type = {row['alert_type']: row['count'] for row in type_rows}

        return jsonify({
            'summary': {
                'total': total,
                'unread': unread,
                'by_type': by_type
            },
            'start_date': start_date.isoformat() if start_date else None,
            'end_date': end_date.isoformat() if end_date else None
        }), 200

    except PsycopgError as e:
        logger.error(f"Failed to get alerts summary: {e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '알림 요약 조회에 실패했습니다.'
        }), 500
    finally:
        if conn:
            put_conn(conn)


@admin_bp.route("/task-corrections", methods=["GET"])
@jwt_required
@admin_required
def get_task_corrections() -> Tuple[Dict[str, Any], int]:
    """
    수정이 필요한 작업 목록 조회

    문제 유형:
    - REVERSE_COMPLETION: 완료 시간이 시작 시간보다 이름
    - DURATION_EXCEEDED: 작업 시간 14시간 초과
    - UNFINISHED_AT_CLOSING: 미완료 상태로 14시간 경과
    - DUPLICATE_COMPLETION: 중복 완료

    Query Parameters:
        qr_doc_id: str (optional, 특정 제품 필터링)
        issue_type: str (optional, 문제 유형 필터링)
        limit: int (default: 50)

    Headers:
        Authorization: Bearer {token}

    Returns:
        200: {
            "corrections": [{
                "task_id": int,
                "worker_id": int,
                "worker_name": str,
                "serial_number": str,
                "qr_doc_id": str,
                "task_category": str,
                "task_name": str,
                "started_at": str,
                "completed_at": str,
                "duration_minutes": int,
                "issue_type": str,
                "issue_description": str
            }],
            "total": int
        }
    """
    qr_doc_id = request.args.get('qr_doc_id')
    issue_type = request.args.get('issue_type')
    limit = request.args.get('limit', 50, type=int)

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 기본 쿼리: 문제가 있는 작업 조회
        where_clauses = ["t.is_applicable = TRUE"]
        params: List[Any] = []

        if qr_doc_id:
            where_clauses.append("t.qr_doc_id = %s")
            params.append(qr_doc_id)

        # 문제 유형별 필터링
        if issue_type:
            if issue_type == 'REVERSE_COMPLETION':
                where_clauses.append("t.completed_at < t.started_at")
            elif issue_type == 'DURATION_EXCEEDED':
                where_clauses.append("t.duration_minutes > 840")  # 14시간 = 840분
            elif issue_type == 'UNFINISHED_AT_CLOSING':
                where_clauses.append("t.started_at IS NOT NULL")
                where_clauses.append("t.completed_at IS NULL")
                where_clauses.append("EXTRACT(EPOCH FROM (NOW() - t.started_at)) / 60 > 840")
        else:
            # 전체 문제 조회: 역전 OR 초과 OR 미완료(14시간+)
            where_clauses.append(
                """(
                    (t.completed_at < t.started_at) OR
                    (t.duration_minutes > 840) OR
                    (t.started_at IS NOT NULL AND t.completed_at IS NULL AND
                     EXTRACT(EPOCH FROM (NOW() - t.started_at)) / 60 > 840)
                )"""
            )

        where_sql = " AND ".join(where_clauses)
        params.append(limit)

        query = f"""
            SELECT
                t.id as task_id,
                t.worker_id,
                w.name as worker_name,
                t.serial_number,
                t.qr_doc_id,
                t.task_category,
                t.task_name,
                t.started_at,
                t.completed_at,
                t.duration_minutes,
                CASE
                    WHEN t.completed_at < t.started_at THEN 'REVERSE_COMPLETION'
                    WHEN t.duration_minutes > 840 THEN 'DURATION_EXCEEDED'
                    WHEN t.started_at IS NOT NULL AND t.completed_at IS NULL AND
                         EXTRACT(EPOCH FROM (NOW() - t.started_at)) / 60 > 840 THEN 'UNFINISHED_AT_CLOSING'
                    ELSE 'UNKNOWN'
                END as issue_type,
                CASE
                    WHEN t.completed_at < t.started_at THEN '완료 시간이 시작 시간보다 이릅니다.'
                    WHEN t.duration_minutes > 840 THEN CONCAT('작업 시간 ', t.duration_minutes, '분 (14시간 초과)')
                    WHEN t.started_at IS NOT NULL AND t.completed_at IS NULL THEN
                        CONCAT('작업 시작 후 ',
                               ROUND(EXTRACT(EPOCH FROM (NOW() - t.started_at)) / 3600, 1),
                               '시간 경과, 미완료 상태')
                    ELSE '알 수 없는 문제'
                END as issue_description
            FROM app_task_details t
            JOIN workers w ON t.worker_id = w.id
            WHERE {where_sql}
            ORDER BY t.created_at DESC
            LIMIT %s
        """

        cur.execute(query, tuple(params))
        rows = cur.fetchall()

        corrections = [
            {
                'task_id': row['task_id'],
                'worker_id': row['worker_id'],
                'worker_name': row['worker_name'],
                'serial_number': row['serial_number'],
                'qr_doc_id': row['qr_doc_id'],
                'task_category': row['task_category'],
                'task_name': row['task_name'],
                'started_at': row['started_at'].isoformat() if row['started_at'] else None,
                'completed_at': row['completed_at'].isoformat() if row['completed_at'] else None,
                'duration_minutes': row['duration_minutes'],
                'issue_type': row['issue_type'],
                'issue_description': row['issue_description']
            }
            for row in rows
        ]

        return jsonify({
            'corrections': corrections,
            'total': len(corrections)
        }), 200

    except PsycopgError as e:
        logger.error(f"Failed to get task corrections: {e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '작업 수정 목록 조회에 실패했습니다.'
        }), 500
    finally:
        if conn:
            put_conn(conn)


@admin_bp.route("/tasks/<int:task_id>/force-complete", methods=["POST"])
@jwt_required
@admin_required
def force_complete_task(task_id: int) -> Tuple[Dict[str, Any], int]:
    """
    작업 강제 완료 (관리자 수동 처리)

    Path Parameters:
        task_id: int (작업 ID)

    Request Body:
        {
            "completed_at": str (optional, ISO 8601 형식, 미지정 시 현재 시각)
        }

    Headers:
        Authorization: Bearer {token}

    Returns:
        200: {"message": "작업이 강제 완료되었습니다.", "task_id": int}
        404: {"error": "TASK_NOT_FOUND", "message": "..."}
        500: {"error": "INTERNAL_SERVER_ERROR", "message": "..."}
    """
    data = request.get_json(silent=True) or {}
    completed_at_param = data.get('completed_at')

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 작업 존재 확인
        cur.execute(
            "SELECT id, started_at FROM app_task_details WHERE id = %s",
            (task_id,)
        )
        row = cur.fetchone()

        if not row:
            return jsonify({
                'error': 'TASK_NOT_FOUND',
                'message': '작업을 찾을 수 없습니다.'
            }), 404

        # completed_at 설정
        if completed_at_param:
            try:
                completed_at = datetime.fromisoformat(completed_at_param)
            except ValueError:
                return jsonify({
                    'error': 'INVALID_REQUEST',
                    'message': 'completed_at 형식이 올바르지 않습니다. (ISO 8601)'
                }), 400
        else:
            completed_at = datetime.now(Config.KST)

        # duration 계산 (started_at이 있을 경우)
        started_at = row['started_at']
        if started_at:
            duration_minutes = int((completed_at - started_at).total_seconds() / 60)
        else:
            duration_minutes = 0

        # 작업 완료 처리
        cur.execute(
            """
            UPDATE app_task_details
            SET completed_at = %s,
                duration_minutes = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (completed_at, duration_minutes, task_id)
        )

        conn.commit()

        logger.info(f"Task force completed by admin: task_id={task_id}, admin_id={g.worker_id}, completed_at={completed_at}")

        return jsonify({
            'message': '작업이 강제 완료되었습니다.',
            'task_id': task_id
        }), 200

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to force complete task: {e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '작업 강제 완료에 실패했습니다.'
        }), 500
    finally:
        if conn:
            put_conn(conn)


@admin_bp.route("/products/initialize-tasks", methods=["POST"])
@jwt_required
@admin_required
def initialize_product_tasks() -> Tuple[Dict[str, Any], int]:
    """
    제품 Task 초기화 (Task Seed)
    Sprint 6 Phase B: MECH 7 + ELEC 6 + TMS 2 = 최대 15개 자동 생성

    Request Body:
        {
            "serial_number": str,
            "qr_doc_id": str,
            "model_name": str   # plan.product_info.model 값 (예: 'GAIA-1234')
        }

    Headers:
        Authorization: Bearer {token}  (admin_required)

    Returns:
        200: {
            "message": str,
            "serial_number": str,
            "created": int,
            "skipped": int,
            "categories": {"MECH": int, "ELEC": int, "TMS": int}
        }
        400: {"error": "INVALID_REQUEST", "message": "..."}
        500: {"error": "SEED_FAILED", "message": "..."}
    """
    data = request.get_json()
    if not data or not all(k in data for k in ['serial_number', 'qr_doc_id', 'model_name']):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'serial_number, qr_doc_id, model_name 필드가 필요합니다.'
        }), 400

    serial_number = data['serial_number']
    qr_doc_id = data['qr_doc_id']
    model_name = data['model_name']

    from app.services.task_seed import initialize_product_tasks as _seed
    result = _seed(
        serial_number=serial_number,
        qr_doc_id=qr_doc_id,
        model_name=model_name
    )

    if result.get('error'):
        logger.error(
            f"Task seed failed: serial_number={serial_number}, error={result['error']}"
        )
        return jsonify({
            'error': 'SEED_FAILED',
            'message': f"Task 초기화 실패: {result['error']}"
        }), 500

    logger.info(
        f"Task seed completed by admin: serial_number={serial_number}, "
        f"created={result['created']}, admin_id={g.worker_id}"
    )

    return jsonify({
        'message': f"Task 초기화 완료 ({result['created']}개 생성, {result['skipped']}개 건너뜀)",
        'serial_number': serial_number,
        'created': result['created'],
        'skipped': result['skipped'],
        'categories': result['categories']
    }), 200


@admin_bp.route("/tasks/<int:task_id>/force-close", methods=["PUT"])
@jwt_required
@manager_or_admin_required
def force_close_task(task_id: int) -> Tuple[Dict[str, Any], int]:
    """
    작업 강제 종료 (관리자 또는 매니저)
    Sprint 6 Phase C: close_reason 필수, 이미 완료된 Task 거부

    Path Parameters:
        task_id: int (작업 ID)

    Request Body:
        {
            "completed_at": str (optional, ISO 8601, 미지정 시 현재 시각),
            "close_reason": str (필수, 강제 종료 사유)
        }

    Headers:
        Authorization: Bearer {token}  (is_manager 또는 is_admin)

    Returns:
        200: {
            "message": str,
            "task_id": int,
            "completed_at": str,
            "duration_minutes": int,
            "elapsed_minutes": int,
            "close_reason": str
        }
        400: {"error": "INVALID_REQUEST", "message": "..."}
        400: {"error": "TASK_ALREADY_COMPLETED", "message": "..."}
        404: {"error": "TASK_NOT_FOUND", "message": "..."}
        500: {"error": "INTERNAL_SERVER_ERROR", "message": "..."}
    """
    data = request.get_json(silent=True) or {}

    # close_reason 필수
    close_reason = data.get('close_reason', '').strip()
    if not close_reason:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'close_reason(강제 종료 사유)은 필수입니다.'
        }), 400

    completed_at_param = data.get('completed_at')

    # 협력사 관리자는 본인 company의 작업만 강제 종료 가능
    current_worker = get_worker_by_id(g.worker_id)
    manager_company = None
    if current_worker and current_worker.is_manager and not current_worker.is_admin:
        manager_company = current_worker.company

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 작업 존재 확인 (worker company 포함)
        cur.execute(
            """
            SELECT t.id, t.started_at, t.completed_at, t.force_closed, w.company AS worker_company
            FROM app_task_details t
            LEFT JOIN workers w ON t.worker_id = w.id
            WHERE t.id = %s
            """,
            (task_id,)
        )
        row = cur.fetchone()

        if not row:
            return jsonify({
                'error': 'TASK_NOT_FOUND',
                'message': '작업을 찾을 수 없습니다.'
            }), 404

        # 협력사 관리자 company 일치 여부 확인
        if manager_company and row['worker_company'] != manager_company:
            return jsonify({
                'error': 'FORBIDDEN',
                'message': '본인 소속 협력사의 작업만 강제 종료할 수 있습니다.'
            }), 403

        # 이미 완료된 Task → 거부
        if row['completed_at'] is not None:
            return jsonify({
                'error': 'TASK_ALREADY_COMPLETED',
                'message': '이미 완료된 작업은 강제 종료할 수 없습니다.'
            }), 400

        # completed_at 설정
        if completed_at_param:
            try:
                completed_at = datetime.fromisoformat(completed_at_param)
            except ValueError:
                return jsonify({
                    'error': 'INVALID_REQUEST',
                    'message': 'completed_at 형식이 올바르지 않습니다. (ISO 8601)'
                }), 400
        else:
            completed_at = datetime.now(Config.KST)

        # duration / elapsed 계산
        started_at = row['started_at']
        if started_at:
            elapsed_minutes = int((completed_at - started_at).total_seconds() / 60)
        else:
            elapsed_minutes = 0

        # duration_minutes = man-hour (work_completion_log 합계 + 현재 작업자)
        cur.execute(
            """
            SELECT COALESCE(SUM(duration_minutes), 0) AS duration_sum
            FROM work_completion_log
            WHERE task_id = %s
            """,
            (task_id,)
        )
        existing_duration = int(cur.fetchone()['duration_sum'])
        # 아직 미완료인 작업자의 duration도 합산 (현재 시각 기준)
        # BUG-9 Fix: _calculate_working_minutes로 휴게시간 자동 차감
        cur.execute(
            """
            SELECT wsl.worker_id, wsl.started_at
            FROM work_start_log wsl
            LEFT JOIN work_completion_log wcl
                   ON wsl.task_id = wcl.task_id AND wsl.worker_id = wcl.worker_id
            WHERE wsl.task_id = %s AND wcl.id IS NULL
            """,
            (task_id,)
        )
        pending_workers = cur.fetchall()
        pending_duration = 0
        for pw in pending_workers:
            if pw['started_at']:
                pending_duration += _calculate_working_minutes(pw['started_at'], completed_at)
        duration_minutes = existing_duration + pending_duration

        # BUG-9 Fix: 수동 pause만 차감 (break auto-pause는 _calculate_working_minutes에서 이미 차감)
        cur.execute(
            """
            SELECT COALESCE(SUM(pause_duration_minutes), 0) AS manual_pause
            FROM work_pause_log
            WHERE task_detail_id = %s
              AND pause_type NOT IN ('break_morning', 'lunch', 'break_afternoon', 'dinner')
              AND resumed_at IS NOT NULL
            """,
            (task_id,)
        )
        manual_pause_minutes = int(cur.fetchone()['manual_pause'])
        duration_minutes = max(0, duration_minutes - manual_pause_minutes)

        if duration_minutes == 0 and elapsed_minutes > 0:
            duration_minutes = elapsed_minutes  # fallback

        # app_task_details 강제 종료 업데이트
        cur.execute(
            """
            UPDATE app_task_details
            SET completed_at    = %s,
                duration_minutes = %s,
                elapsed_minutes  = %s,
                force_closed     = TRUE,
                closed_by        = %s,
                close_reason     = %s,
                updated_at       = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (completed_at, duration_minutes, elapsed_minutes,
             g.worker_id, close_reason, task_id)
        )

        conn.commit()

        logger.info(
            f"Task force-closed: task_id={task_id}, by={g.worker_id}, "
            f"reason='{close_reason}', completed_at={completed_at}"
        )

        return jsonify({
            'message': '작업이 강제 종료되었습니다.',
            'task_id': task_id,
            'completed_at': completed_at.isoformat(),
            'duration_minutes': duration_minutes,
            'elapsed_minutes': elapsed_minutes,
            'close_reason': close_reason
        }), 200

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to force-close task: {e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '작업 강제 종료에 실패했습니다.'
        }), 500
    finally:
        if conn:
            put_conn(conn)


@admin_bp.route("/cron/check-unfinished-tasks", methods=["POST"])
@jwt_required
@admin_required
def manual_check_unfinished_tasks() -> Tuple[Dict[str, Any], int]:
    """
    미완료 작업 체크 수동 실행

    Headers:
        Authorization: Bearer {token}

    Returns:
        200: {
            "message": str,
            "unfinished_count": int,
            "tasks": [{
                "task_id": int,
                "serial_number": str,
                "task_name": str,
                "duration_hours": float,
                "alert_id": int
            }]
        }
    """
    result = trigger_unfinished_task_check_manually()

    logger.info(f"Manual unfinished task check triggered by admin: admin_id={g.worker_id}")

    return jsonify(result), 200


# ============================================================
# Sprint 7: 누락 엔드포인트 5개 구현
# ============================================================

@admin_bp.route("/managers", methods=["GET"])
@jwt_required
@manager_or_admin_required
def get_managers() -> Tuple[Dict[str, Any], int]:
    """
    승인된 작업자 목록 조회 (관리자 권한 부여용)

    - Admin: 전체 작업자 목록 (company 파라미터로 필터 가능)
    - Manager: 같은 회사 소속만 자동 필터 (company 파라미터 무시)

    Query Parameters:
        company: str (optional, Admin만 사용 가능)

    Headers:
        Authorization: Bearer {token}

    Returns:
        200: {
            "workers": [{
                "id": int,
                "name": str,
                "email": str,
                "role": str,
                "company": str|null,
                "is_manager": bool,
                "is_admin": bool,
                "created_at": str
            }],
            "total": int
        }
    """
    requester = get_worker_by_id(g.worker_id)

    # Manager는 같은 회사만 자동 필터, Admin은 파라미터 사용 가능
    if requester and not requester.is_admin:
        company = requester.company
    else:
        company = request.args.get('company')

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        where_clauses = ["approval_status = 'approved'"]
        params: List[Any] = []

        if company:
            where_clauses.append("company = %s")
            params.append(company)

        where_sql = " AND ".join(where_clauses)

        cur.execute(
            f"""
            SELECT id, name, email, role, company, is_manager, is_admin, created_at
            FROM workers
            WHERE {where_sql}
            ORDER BY company NULLS LAST, name
            """,
            tuple(params)
        )

        rows = cur.fetchall()
        workers = [
            {
                'id': row['id'],
                'name': row['name'],
                'email': row['email'],
                'role': row['role'],
                'company': row.get('company'),
                'is_manager': row['is_manager'],
                'is_admin': row['is_admin'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
            }
            for row in rows
        ]

        return jsonify({'workers': workers, 'total': len(workers)}), 200

    except PsycopgError as e:
        logger.error(f"Failed to get managers list: {e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '작업자 목록 조회에 실패했습니다.'
        }), 500
    finally:
        if conn:
            put_conn(conn)


@admin_bp.route("/workers/<int:worker_id>/manager", methods=["PUT"])
@jwt_required
@manager_or_admin_required
def toggle_manager(worker_id: int) -> Tuple[Dict[str, Any], int]:
    """
    작업자의 is_manager 토글

    - Admin: 전체 작업자 is_manager 부여/해제 (제한 없음)
    - Manager: 같은 회사(company) 소속 작업자만 is_manager 부여/해제
      - Admin 권한 변경 불가 (상위 권한 보호)
      - 다른 회사 작업자 변경 불가

    Path Parameters:
        worker_id: int

    Request Body:
        {"is_manager": bool}

    Headers:
        Authorization: Bearer {token}

    Returns:
        200: {"message": str, "worker_id": int, "is_manager": bool}
        400: {"error": "INVALID_REQUEST", "message": "..."}
        403: {"error": "FORBIDDEN", "message": "..."}
        404: {"error": "WORKER_NOT_FOUND", "message": "..."}
        500: {"error": "INTERNAL_SERVER_ERROR", "message": "..."}
    """
    data = request.get_json(silent=True) or {}
    is_manager = data.get('is_manager')

    if is_manager is None or not isinstance(is_manager, bool):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'is_manager 필드(bool)가 필요합니다.'
        }), 400

    # 대상 작업자 조회
    target_worker = get_worker_by_id(worker_id)
    if not target_worker:
        return jsonify({
            'error': 'WORKER_NOT_FOUND',
            'message': '작업자를 찾을 수 없습니다.'
        }), 404

    # 요청자 정보 조회 (Manager 권한 검증용)
    requester = get_worker_by_id(g.worker_id)

    # Manager인 경우 추가 검증 (Admin이 아닌 경우)
    if not requester.is_admin:
        # Admin 권한 변경 불가 (상위 권한 보호)
        if target_worker.is_admin:
            return jsonify({
                'error': 'FORBIDDEN',
                'message': 'Admin 계정의 권한은 변경할 수 없습니다.'
            }), 403

        # 같은 회사 소속만 변경 가능
        if requester.company != target_worker.company:
            return jsonify({
                'error': 'FORBIDDEN',
                'message': '같은 회사 소속 작업자만 관리자 지정/해제할 수 있습니다.'
            }), 403

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE workers
            SET is_manager = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (is_manager, worker_id)
        )
        conn.commit()

        action = '관리자 지정' if is_manager else '관리자 해제'
        logger.info(f"Worker manager toggled: worker_id={worker_id}, is_manager={is_manager}, by={g.worker_id}")

        return jsonify({
            'message': f'{action} 완료',
            'worker_id': worker_id,
            'is_manager': is_manager
        }), 200

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to toggle manager: worker_id={worker_id}, error={e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '관리자 설정 변경에 실패했습니다.'
        }), 500
    finally:
        if conn:
            put_conn(conn)


@admin_bp.route("/settings", methods=["GET"])
@jwt_required
@admin_required
def get_settings() -> Tuple[Dict[str, Any], int]:
    """
    admin_settings 전체 조회

    Headers:
        Authorization: Bearer {token}

    Returns:
        200: {
            "heating_jacket_enabled": bool,
            "phase_block_enabled": bool,
            ...  # admin_settings 테이블의 모든 키를 flat dict으로 반환
        }
    """
    settings_list = get_all_settings()

    # key-value flat dict으로 변환 (FE 기대 형식)
    result: Dict[str, Any] = {}
    for s in settings_list:
        result[s.setting_key] = s.setting_value

    # Sprint 34: SETTING_KEYS 기반 기본값 자동 적용
    for key, meta in SETTING_KEYS.items():
        result.setdefault(key, meta['default'])

    return jsonify(result), 200


@admin_bp.route("/settings", methods=["PUT"])
@jwt_required
@manager_or_admin_required
def update_settings() -> Tuple[Dict[str, Any], int]:
    """
    admin_settings UPSERT (여러 키 동시 업데이트 가능)

    Request Body:
        {
            "heating_jacket_enabled": bool,   # (optional)
            "phase_block_enabled": bool        # (optional)
        }

    Headers:
        Authorization: Bearer {token}

    Returns:
        200: {"message": str, "updated_keys": [str]}
        400: {"error": "INVALID_REQUEST", "message": "..."}
        500: {"error": "INTERNAL_SERVER_ERROR", "message": "..."}
    """
    data = request.get_json(silent=True) or {}

    # Sprint 52: 단일 키-값 형식 지원 {"setting_key": "key", "setting_value": value}
    if 'setting_key' in data and 'setting_value' in data and len(data) == 2:
        single_key = data['setting_key']
        single_val = data['setting_value']
        if single_key not in ALLOWED_KEYS:
            return jsonify({
                'error': 'INVALID_REQUEST',
                'message': f'허용되지 않은 설정 키: {single_key}'
            }), 400
        error = _validate_setting(single_key, single_val)
        if error:
            return jsonify({'error': 'VALIDATION_ERROR', 'message': error}), 400
        success = update_setting(single_key, single_val, updated_by=g.worker_id)
        if not success:
            return jsonify({'error': 'INTERNAL_SERVER_ERROR', 'message': '설정 저장 실패'}), 500
        return jsonify({'message': '설정이 저장되었습니다.', 'updated_keys': [single_key]}), 200

    # Sprint 34: SETTING_KEYS 레지스트리 기반 검증
    update_pairs = {k: v for k, v in data.items() if k in ALLOWED_KEYS}

    if not update_pairs:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': '업데이트할 유효한 설정 키가 없습니다.'
        }), 400

    # 타입별 검증 (통합)
    for key, value in update_pairs.items():
        error = _validate_setting(key, value)
        if error:
            return jsonify({'error': 'VALIDATION_ERROR', 'message': error}), 400

    # 시간 쌍 검증 (start < end)
    from app.models.admin_settings import get_setting as _get_setting
    checked_pairs = set()
    for tk in update_pairs:
        meta = SETTING_KEYS.get(tk, {})
        if meta.get('type') != 'time':
            continue
        pair_key = meta.get('pair')
        if not pair_key or frozenset({tk, pair_key}) in checked_pairs:
            continue
        checked_pairs.add(frozenset({tk, pair_key}))
        if tk.endswith('_start'):
            start_val = update_pairs.get(tk) or _get_setting(tk)
            end_val = update_pairs.get(pair_key) or _get_setting(pair_key)
        else:
            start_val = update_pairs.get(pair_key) or _get_setting(pair_key)
            end_val = update_pairs.get(tk) or _get_setting(tk)
        if start_val and end_val and start_val >= end_val:
            return jsonify({
                'error': 'INVALID_TIME_RANGE',
                'message': f'시작 시간({start_val})이 종료 시간({end_val})보다 이전이어야 합니다.'
            }), 400

    failed_keys = []
    for key, value in update_pairs.items():
        success = update_setting(key, value, updated_by=g.worker_id)
        if not success:
            failed_keys.append(key)

    if failed_keys:
        logger.error(f"Admin settings update failed for keys: {failed_keys}, by_admin={g.worker_id}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': f'설정 저장 실패: {", ".join(failed_keys)}'
        }), 500

    updated_keys = list(update_pairs.keys())
    logger.info(f"Admin settings updated: keys={updated_keys}, by_admin={g.worker_id}")

    # heating_jacket_enabled 변경 시 → 기존 HEATING_JACKET task의 is_applicable 동기화
    if 'heating_jacket_enabled' in update_pairs:
        new_val = bool(update_pairs['heating_jacket_enabled'])
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE app_task_details
                SET is_applicable = %s, updated_at = NOW()
                WHERE task_category = 'MECH'
                  AND task_id = 'HEATING_JACKET'
                  AND completed_at IS NULL
                """,
                (new_val,)
            )
            affected = cur.rowcount
            conn.commit()
            logger.info(f"HEATING_JACKET is_applicable → {new_val}, affected={affected} tasks")
        except Exception as e:
            logger.error(f"Failed to sync HEATING_JACKET tasks: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                put_conn(conn)

    return jsonify({
        'message': '설정이 저장되었습니다.',
        'updated_keys': updated_keys
    }), 200


@admin_bp.route("/tasks/pending", methods=["GET"])
@jwt_required
@manager_or_admin_required
def get_pending_tasks() -> Tuple[Dict[str, Any], int]:
    """
    미종료 작업 목록 조회
    (started_at IS NOT NULL AND completed_at IS NULL)

    Query Parameters:
        limit: int (default: 50)

    Headers:
        Authorization: Bearer {token}

    Returns:
        200: {
            "tasks": [{
                "id": int,
                "worker_id": int,
                "worker_name": str,
                "serial_number": str,
                "qr_doc_id": str,
                "task_category": str,
                "task_name": str,
                "started_at": str,
                "elapsed_minutes": int
            }],
            "total": int
        }
    """
    limit = request.args.get('limit', 50, type=int)
    company = request.args.get('company', None, type=str)

    # 협력사 관리자는 본인 company로 강제 제한 (admin은 모든 company 조회 가능)
    current_worker = get_worker_by_id(g.worker_id)
    if current_worker and current_worker.is_manager and not current_worker.is_admin:
        company = current_worker.company

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                t.id,
                t.worker_id,
                w.name AS worker_name,
                t.serial_number,
                t.qr_doc_id,
                t.task_category,
                t.task_name,
                t.started_at,
                EXTRACT(EPOCH FROM (NOW() - t.started_at)) / 60 AS elapsed_minutes
            FROM app_task_details t
            JOIN workers w ON t.worker_id = w.id
            WHERE t.started_at IS NOT NULL
              AND t.completed_at IS NULL
              AND t.is_applicable = TRUE
            
              AND (w.company = %s OR %s IS NULL)
            ORDER BY t.started_at ASC
            LIMIT %s
            """,
            (company, company, limit)
        )

        rows = cur.fetchall()
        tasks = [
            {
                'id': row['id'],
                'worker_id': row['worker_id'],
                'worker_name': row['worker_name'],
                'serial_number': row['serial_number'],
                'qr_doc_id': row['qr_doc_id'],
                'task_category': row['task_category'],
                'task_name': row['task_name'],
                'started_at': row['started_at'].isoformat() if row['started_at'] else None,
                'elapsed_minutes': int(row['elapsed_minutes']) if row['elapsed_minutes'] else 0,
            }
            for row in rows
        ]

        return jsonify({'tasks': tasks, 'total': len(tasks)}), 200

    except PsycopgError as e:
        logger.error(f"Failed to get pending tasks: {e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '미종료 작업 목록 조회에 실패했습니다.'
        }), 500
    finally:
        if conn:
            put_conn(conn)


# ============================================================
# Sprint 19-E: VIEW용 Admin 출퇴근 API
# ============================================================

_KST = timezone(timedelta(hours=9))


def _kst_date_range(target_date=None):
    """KST 기준 날짜의 시작/끝 범위 반환 (target_date=None이면 오늘)"""
    if target_date is None:
        now_kst = datetime.now(_KST)
        target_date = now_kst.date()
    start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=_KST)
    end = start + timedelta(days=1)
    return start, end


def _get_attendance_data(target_start_kst, target_end_kst, company_filter=None):
    """출퇴근 데이터 조회 공통 함수 — records + summary 반환

    Args:
        target_start_kst: KST 기준 조회 시작 시간
        target_end_kst: KST 기준 조회 종료 시간
        company_filter: Manager 자사 필터 (None이면 전체)
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = """
            SELECT
              w.id AS worker_id,
              w.name AS worker_name,
              w.company,
              w.role,
              MAX(CASE WHEN pa.check_type = 'in'  THEN pa.check_time END) AS check_in_time,
              MAX(CASE WHEN pa.check_type = 'out' THEN pa.check_time END) AS check_out_time,
              MAX(CASE WHEN pa.check_type = 'in'  THEN pa.work_site END) AS work_site,
              MAX(CASE WHEN pa.check_type = 'in'  THEN pa.product_line END) AS product_line
            FROM workers w
            LEFT JOIN hr.partner_attendance pa
              ON w.id = pa.worker_id
              AND pa.check_time >= %s
              AND pa.check_time <  %s
            WHERE w.company != 'GST'
              AND w.approval_status = 'approved'
        """
        params = [target_start_kst, target_end_kst]

        if company_filter:
            query += " AND w.company = %s"
            params.append(company_filter)

        query += """
            GROUP BY w.id, w.name, w.company, w.role
            ORDER BY w.company, w.name
        """
        cur.execute(query, params)

        rows = cur.fetchall()

        records = []
        summary = {
            'total_registered': 0,
            'checked_in': 0,
            'checked_out': 0,
            'currently_working': 0,
            'not_checked': 0,
        }

        for row in rows:
            check_in = row['check_in_time']
            check_out = row['check_out_time']

            if check_in is None:
                status = 'not_checked'
            elif check_out is None:
                status = 'working'
            else:
                status = 'left'

            records.append({
                'worker_id': row['worker_id'],
                'worker_name': row['worker_name'],
                'company': row['company'],
                'role': row['role'],
                'check_in_time': check_in.isoformat() if check_in else None,
                'check_out_time': check_out.isoformat() if check_out else None,
                'status': status,
                'work_site': row['work_site'],
                'product_line': row['product_line'],
            })

            summary['total_registered'] += 1
            if status == 'not_checked':
                summary['not_checked'] += 1
            else:
                summary['checked_in'] += 1
                if status == 'left':
                    summary['checked_out'] += 1
                else:
                    summary['currently_working'] += 1

        return records, summary

    finally:
        if conn:
            put_conn(conn)


def _get_manager_company_filter():
    """Manager인 경우 자사 company 반환, Admin 또는 GST면 None (전체)"""
    worker = get_worker_by_id(g.worker_id)
    if worker and worker.is_manager and not worker.is_admin:
        if worker.company == 'GST':
            return None  # GST 직원은 전체 협력사 데이터 접근
        return worker.company
    return None


@admin_bp.route("/hr/attendance/today", methods=["GET"])
@jwt_required
@manager_or_admin_required
def get_attendance_today() -> Tuple[Dict[str, Any], int]:
    """
    오늘 전체 출퇴근 현황 (KST 기준)

    Headers:
        Authorization: Bearer {token}

    Returns:
        200: {"date": str, "records": [...], "summary": {...}}
    """
    try:
        start, end = _kst_date_range()
        company_filter = _get_manager_company_filter()
        records, summary = _get_attendance_data(start, end, company_filter=company_filter)

        return jsonify({
            'date': datetime.now(_KST).strftime('%Y-%m-%d'),
            'records': records,
            'summary': summary,
        }), 200
    except Exception as e:
        logger.error(f"Failed to get today attendance: {e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '오늘 출퇴근 현황 조회에 실패했습니다.'
        }), 500


@admin_bp.route("/hr/attendance", methods=["GET"])
@jwt_required
@manager_or_admin_required
def get_attendance_by_date() -> Tuple[Dict[str, Any], int]:
    """
    날짜별 출퇴근 현황 조회

    Query Parameters:
        date: str (YYYY-MM-DD, optional — 없으면 오늘)

    Headers:
        Authorization: Bearer {token}

    Returns:
        200: {"date": str, "records": [...], "summary": {...}}
        400: {"error": "INVALID_DATE", "message": "..."}
    """
    date_str = request.args.get('date')

    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'error': 'INVALID_DATE',
                'message': 'date 형식: YYYY-MM-DD'
            }), 400
    else:
        target_date = datetime.now(_KST).date()

    try:
        start, end = _kst_date_range(target_date)
        company_filter = _get_manager_company_filter()
        records, summary = _get_attendance_data(start, end, company_filter=company_filter)

        return jsonify({
            'date': target_date.strftime('%Y-%m-%d'),
            'records': records,
            'summary': summary,
        }), 200
    except Exception as e:
        logger.error(f"Failed to get attendance by date: {e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '출퇴근 현황 조회에 실패했습니다.'
        }), 500


@admin_bp.route("/hr/attendance/summary", methods=["GET"])
@jwt_required
@manager_or_admin_required
def get_attendance_summary() -> Tuple[Dict[str, Any], int]:
    """
    회사별 출퇴근 요약

    Query Parameters:
        date: str (YYYY-MM-DD, optional — 없으면 오늘)

    Headers:
        Authorization: Bearer {token}

    Returns:
        200: {"date": str, "by_company": [...]}
        400: {"error": "INVALID_DATE", "message": "..."}
    """
    date_str = request.args.get('date')

    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'error': 'INVALID_DATE',
                'message': 'date 형식: YYYY-MM-DD'
            }), 400
    else:
        target_date = datetime.now(_KST).date()

    try:
        start, end = _kst_date_range(target_date)
        company_filter = _get_manager_company_filter()
        records, _ = _get_attendance_data(start, end, company_filter=company_filter)

        # company별 그룹핑
        company_data = defaultdict(lambda: {
            'total_workers': 0,
            'checked_in': 0,
            'checked_out': 0,
            'currently_working': 0,
            'not_checked': 0,
        })

        for r in records:
            company = r['company'] or 'UNKNOWN'
            cd = company_data[company]
            cd['total_workers'] += 1
            if r['status'] == 'not_checked':
                cd['not_checked'] += 1
            elif r['status'] == 'working':
                cd['checked_in'] += 1
                cd['currently_working'] += 1
            else:  # left
                cd['checked_in'] += 1
                cd['checked_out'] += 1

        by_company = [
            {'company': company, **stats}
            for company, stats in sorted(company_data.items())
        ]

        return jsonify({
            'date': target_date.strftime('%Y-%m-%d'),
            'by_company': by_company,
        }), 200
    except Exception as e:
        logger.error(f"Failed to get attendance summary: {e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '출퇴근 요약 조회에 실패했습니다.'
        }), 500


# ============================================================
# Sprint 35: 기간별 출입 추이 API
# ============================================================

def _get_attendance_trend_data(
    date_from: date,
    date_to: date,
    company_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """기간별 일별 출입 집계 — 단일 SQL"""
    range_start = datetime(date_from.year, date_from.month, date_from.day, tzinfo=_KST)
    range_end = datetime(date_to.year, date_to.month, date_to.day, tzinfo=_KST) + timedelta(days=1)

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 일별 출근 집계
        checkin_query = """
            SELECT
                DATE(pa.check_time AT TIME ZONE 'Asia/Seoul') AS check_date,
                COUNT(DISTINCT pa.worker_id) AS checked_in,
                COUNT(DISTINCT CASE WHEN pa.work_site = 'HQ' THEN pa.worker_id END) AS hq_count,
                COUNT(DISTINCT CASE WHEN pa.work_site != 'HQ' THEN pa.worker_id END) AS site_count
            FROM hr.partner_attendance pa
            INNER JOIN workers w ON w.id = pa.worker_id
            WHERE pa.check_type = 'in'
              AND pa.check_time >= %s AND pa.check_time < %s
              AND w.company != 'GST'
              AND w.approval_status = 'approved'
        """
        params: List[Any] = [range_start, range_end]
        if company_filter:
            checkin_query += " AND w.company = %s"
            params.append(company_filter)
        checkin_query += " GROUP BY check_date ORDER BY check_date"

        cur.execute(checkin_query, params)
        checkin_rows = {row['check_date']: row for row in cur.fetchall()}

        # 전체 등록 인원
        reg_query = "SELECT COUNT(*) AS cnt FROM workers WHERE company != 'GST' AND approval_status = 'approved'"
        reg_params: List[Any] = []
        if company_filter:
            reg_query += " AND company = %s"
            reg_params.append(company_filter)
        cur.execute(reg_query, reg_params)
        total_registered = cur.fetchone()['cnt']

        # 빈 날짜 채우기
        trend = []
        current = date_from
        while current <= date_to:
            row = checkin_rows.get(current)
            trend.append({
                'date': current.strftime('%Y-%m-%d'),
                'total_registered': total_registered,
                'checked_in': row['checked_in'] if row else 0,
                'hq_count': row['hq_count'] if row else 0,
                'site_count': row['site_count'] if row else 0,
            })
            current += timedelta(days=1)
        return trend
    finally:
        if conn:
            put_conn(conn)


@admin_bp.route("/hr/attendance/trend", methods=["GET"])
@jwt_required
@manager_or_admin_required
def get_attendance_trend() -> Tuple[Dict[str, Any], int]:
    """
    기간별 일별 출입 인원 추이

    Query: date_from=YYYY-MM-DD&date_to=YYYY-MM-DD (필수, 최대 90일)
    """
    date_from_str = request.args.get('date_from')
    date_to_str = request.args.get('date_to')

    if not date_from_str or not date_to_str:
        return jsonify({
            'error': 'INVALID_PARAMS',
            'message': 'date_from, date_to 파라미터가 필요합니다. (YYYY-MM-DD)'
        }), 400

    try:
        dt_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
        dt_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'INVALID_DATE', 'message': 'date 형식: YYYY-MM-DD'}), 400

    if dt_from > dt_to:
        return jsonify({'error': 'INVALID_PARAMS', 'message': 'date_from은 date_to보다 이전이어야 합니다.'}), 400

    if (dt_to - dt_from).days > 90:
        return jsonify({'error': 'INVALID_PARAMS', 'message': '조회 범위는 최대 90일입니다.'}), 400

    company_filter = _get_manager_company_filter()

    try:
        trend = _get_attendance_trend_data(dt_from, dt_to, company_filter)
        return jsonify({
            'date_from': date_from_str,
            'date_to': date_to_str,
            'trend': trend,
        }), 200
    except Exception as e:
        logger.error(f"attendance trend error: {e}")
        return jsonify({'error': 'INTERNAL_SERVER_ERROR', 'message': '출입 추이 조회 실패'}), 500


# ============================================================
# ETL Change Log: GET /api/admin/etl/changes
# Sprint 2 (CORE-ETL) — Task 4: 변경 이력 조회 API
# ============================================================

# 필드명 → 한글 라벨 매핑
_FIELD_LABELS = {
    'sales_order': '판매오더',
    'ship_plan_date': '출하예정',
    'mech_start': '기구시작',
    'pi_start': '가압시작',
    'finishing_plan_end': '마무리계획일',
    'mech_partner': '기구외주',
    'elec_partner': '전장외주',
}


@admin_bp.route("/etl/changes", methods=["GET"])
@jwt_required
@view_access_required
def get_etl_changes() -> Tuple[Dict[str, Any], int]:
    """
    ETL 변경 이력 조회

    Query Parameters:
        days: int — 최근 N일 (기본 7)
        field: string — 특정 필드만 필터 (sales_order, ship_plan_date, mech_start, mech_partner, elec_partner)
        serial_number: string — 특정 S/N만
        limit: int — 최대 건수 (기본 100)

    Returns:
        200: {"changes": [...], "summary": {"total_changes": int, "by_field": {...}}}
    """
    days = request.args.get('days', 7, type=int)
    field = request.args.get('field', '', type=str).strip()
    serial_number = request.args.get('serial_number', '', type=str).strip()
    limit = request.args.get('limit', 100, type=int)

    # 입력값 범위 제한
    days = max(1, min(days, 365))
    limit = max(1, min(limit, 500))

    # 허용된 필드명 검증
    valid_fields = set(_FIELD_LABELS.keys())
    if field and field not in valid_fields:
        return jsonify({
            'error': 'INVALID_FIELD',
            'message': f'허용된 필드: {", ".join(sorted(valid_fields))}'
        }), 400

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 동적 WHERE 절 구성
        conditions = ["cl.changed_at >= NOW() - INTERVAL '%s days'"]
        params: list = [days]

        if field:
            conditions.append("cl.field_name = %s")
            params.append(field)

        if serial_number:
            conditions.append("cl.serial_number ILIKE %s")
            params.append(f'%{serial_number}%')

        where_clause = " AND ".join(conditions)

        # summary 쿼리 (limit 무관 — 전체 건수 + 필드별 건수)
        cur.execute(f"""
            SELECT cl.field_name, COUNT(*) AS cnt
            FROM etl.change_log cl
            WHERE {where_clause}
            GROUP BY cl.field_name
        """, tuple(params))
        summary_rows = cur.fetchall()
        by_field: dict = {}
        total_changes = 0
        for sr in summary_rows:
            by_field[sr['field_name']] = sr['cnt']
            total_changes += sr['cnt']

        # 변경 이력 조회 (product_info JOIN으로 model 포함)
        cur.execute(f"""
            SELECT cl.id, cl.serial_number, pi.sales_order, pi.model,
                   cl.field_name, cl.old_value, cl.new_value, cl.changed_at
            FROM etl.change_log cl
            LEFT JOIN plan.product_info pi ON cl.serial_number = pi.serial_number
            WHERE {where_clause}
            ORDER BY cl.changed_at DESC
            LIMIT %s
        """, tuple(params) + (limit,))

        rows = cur.fetchall()

        changes = []
        for row in rows:
            field_name = row['field_name']
            changed_at = row['changed_at']
            changes.append({
                'id': row['id'],
                'serial_number': row['serial_number'],
                'sales_order': row['sales_order'],
                'model': row['model'],
                'field_name': field_name,
                'field_label': _FIELD_LABELS.get(field_name, field_name),
                'old_value': row['old_value'],
                'new_value': row['new_value'],
                'changed_at': changed_at.isoformat() if changed_at else None,
            })

        return jsonify({
            'changes': changes,
            'summary': {
                'total_changes': total_changes,
                'by_field': by_field,
            }
        }), 200

    except Exception as e:
        logger.error(f"Failed to get ETL change log: {e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': 'ETL 변경 이력 조회에 실패했습니다.'
        }), 500
    finally:
        if conn:
            put_conn(conn)


# ─── Sprint 40-C: 비활성 사용자 관리 API ────────────────────────────────────


@admin_bp.route("/inactive-workers", methods=["GET"])
@jwt_required
@admin_required
def get_inactive_workers_api() -> Tuple[Dict[str, Any], int]:
    """
    30일 이상 미로그인(또는 last_login_at NULL) 사용자 목록 조회 (Sprint 40-C)

    Query Params:
        days (int, optional): 미로그인 기준 일수 (기본 30)

    Headers:
        Authorization: Bearer {admin_token}

    Returns:
        200: {
            "inactive_workers": [...],
            "count": N,
            "threshold_days": 30
        }
    """
    try:
        days = int(request.args.get('days', 30))
        if days < 1:
            days = 30
    except (ValueError, TypeError):
        days = 30

    workers = get_inactive_workers(days=days)

    # datetime 직렬화
    result = []
    for w in workers:
        result.append({
            'id': w['id'],
            'name': w['name'],
            'email': w['email'],
            'role': w['role'],
            'company': w['company'],
            'is_active': w['is_active'],
            'last_login_at': w['last_login_at'].isoformat() if w['last_login_at'] else None,
            'deactivated_at': w['deactivated_at'].isoformat() if w['deactivated_at'] else None,
            'created_at': w['created_at'].isoformat() if w['created_at'] else None,
        })

    return jsonify({
        'inactive_workers': result,
        'count': len(result),
        'threshold_days': days,
    }), 200


@admin_bp.route("/deactivated-workers", methods=["GET"])
@jwt_required
@admin_required
def get_deactivated_workers_api() -> Tuple[Dict[str, Any], int]:
    """
    비활성화된 사용자 목록 조회 (Sprint 40-C)

    Headers:
        Authorization: Bearer {admin_token}

    Returns:
        200: {
            "deactivated_workers": [...],
            "count": N
        }
    """
    workers = get_deactivated_workers()

    result = []
    for w in workers:
        result.append({
            'id': w['id'],
            'name': w['name'],
            'email': w['email'],
            'role': w['role'],
            'company': w['company'],
            'last_login_at': w['last_login_at'].isoformat() if w['last_login_at'] else None,
            'deactivated_at': w['deactivated_at'].isoformat() if w['deactivated_at'] else None,
            'created_at': w['created_at'].isoformat() if w['created_at'] else None,
        })

    return jsonify({
        'deactivated_workers': result,
        'count': len(result),
    }), 200


@admin_bp.route("/worker-status", methods=["POST"])
@jwt_required
@admin_required
def update_worker_status() -> Tuple[Dict[str, Any], int]:
    """
    사용자 활성/비활성 상태 변경 (Sprint 40-C)

    Request Body:
        {
            "worker_id": int,
            "action": "deactivate" | "reactivate"
        }

    Headers:
        Authorization: Bearer {admin_token}

    Returns:
        200: {"message": "...", "worker_id": N, "action": "..."}
        400: {"error": "INVALID_REQUEST", "message": "..."}
        404: {"error": "WORKER_NOT_FOUND", "message": "..."}
        422: {"error": "NO_CHANGE", "message": "..."}
    """
    data = request.get_json()

    if not data:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': '요청 본문이 필요합니다.'
        }), 400

    worker_id = data.get('worker_id')
    action = data.get('action')

    if not worker_id or not isinstance(worker_id, int):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'worker_id(int)가 필요합니다.'
        }), 400

    if action not in ('deactivate', 'reactivate'):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'action은 "deactivate" 또는 "reactivate"여야 합니다.'
        }), 400

    # 대상 사용자 존재 확인
    target = get_worker_by_id(worker_id)
    if not target:
        return jsonify({
            'error': 'WORKER_NOT_FOUND',
            'message': '해당 사용자를 찾을 수 없습니다.'
        }), 404

    if action == 'deactivate':
        success = deactivate_worker(worker_id)
        msg = '비활성화 완료'
    else:
        success = reactivate_worker(worker_id)
        msg = '재활성화 완료'

    if not success:
        return jsonify({
            'error': 'NO_CHANGE',
            'message': '이미 해당 상태이거나 변경에 실패했습니다.'
        }), 422

    return jsonify({
        'message': msg,
        'worker_id': worker_id,
        'action': action,
    }), 200
