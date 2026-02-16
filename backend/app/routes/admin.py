"""
관리자 라우트
엔드포인트: /api/admin/*
Sprint 4: 관리자 전용 API (승인, 대시보드, 작업 수정)
"""

import logging
from flask import Blueprint, request, jsonify, g
from typing import Tuple, Dict, Any, List
from datetime import datetime, timezone

from app.middleware.jwt_auth import jwt_required, admin_required
from app.models.worker import get_db_connection, update_approval_status, get_worker_by_id
from app.services.alert_service import create_and_broadcast_alert
from app.services.scheduler_service import trigger_unfinished_task_check_manually
from psycopg2 import Error as PsycopgError


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
            SELECT id, name, email, role, is_manager, created_at
            FROM workers
            WHERE approval_status = 'pending'
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
            conn.close()


@admin_bp.route("/workers", methods=["GET"])
@jwt_required
@admin_required
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
    limit = request.args.get('limit', 50, type=int)

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 동적 쿼리 생성
        where_clauses = []
        params: List[Any] = []

        if approval_status:
            where_clauses.append("approval_status = %s")
            params.append(approval_status)

        if role:
            where_clauses.append("role = %s")
            params.append(role)

        where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"
        params.append(limit)

        query = f"""
            SELECT id, name, email, role, approval_status,
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
            conn.close()


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
                "process_type": str,  // MM, EE, TM, PI, QI, SI
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
            date_filter = datetime.now().date()

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
            conn.close()


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
            conn.close()


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
            conn.close()


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
            conn.close()


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
            completed_at = datetime.now(timezone.utc)

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
            conn.close()


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
