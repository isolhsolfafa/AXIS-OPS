"""
GST 검사 공정 라우트 (Sprint 11)
엔드포인트: /api/app/gst/*
GST 사내 PI/QI/SI 작업자 전용 제품 목록 조회
"""

import logging
from flask import Blueprint, request, jsonify, g
from typing import Tuple, Dict, Any

from app.middleware.jwt_auth import jwt_required, get_current_worker_id
from app.models.worker import get_worker_by_id, get_db_connection
from psycopg2 import Error as PsycopgError


logger = logging.getLogger(__name__)

gst_bp = Blueprint("gst", __name__, url_prefix="/api/app/gst")


@gst_bp.route("/products/<string:category>", methods=["GET"])
@jwt_required
def get_gst_products(category: str) -> Tuple[Dict[str, Any], int]:
    """
    GST 검사 공정 대상 제품 목록 조회 (Sprint 11)

    카테고리별(PI/QI/SI) task가 있는 제품 목록을 반환.
    진행 중(not_started, in_progress, paused) 상태의 task만 조회.

    Path Parameters:
        category: PI, QI, SI

    Headers:
        Authorization: Bearer {token}

    Query Parameters:
        status: task 상태 필터 (all, not_started, in_progress, paused, completed)
                기본값: active (not_started + in_progress + paused)

    Response:
        200: {
            "products": [
                {
                    "task_detail_id": int,
                    "serial_number": str,
                    "model": str,
                    "task_id": str,
                    "task_name": str,
                    "task_status": str,   # not_started, in_progress, paused, completed
                    "worker_id": int|null,
                    "worker_name": str|null,
                    "started_at": str|null,
                    "completed_at": str|null,
                    "is_paused": bool,
                    "is_applicable": bool
                },
                ...
            ],
            "total": int,
            "category": str
        }
        400: {"error": "INVALID_CATEGORY", "message": "..."}
        403: {"error": "FORBIDDEN", "message": "..."}
    """
    # 카테고리 검증
    valid_categories = {'PI', 'QI', 'SI'}
    if category.upper() not in valid_categories:
        return jsonify({
            'error': 'INVALID_CATEGORY',
            'message': f'유효하지 않은 카테고리입니다. 허용: {", ".join(sorted(valid_categories))}'
        }), 400

    category = category.upper()

    # 현재 작업자 정보 조회
    worker_id = get_current_worker_id()
    worker = get_worker_by_id(worker_id)
    if not worker:
        return jsonify({
            'error': 'WORKER_NOT_FOUND',
            'message': '작업자 정보를 찾을 수 없습니다.'
        }), 404

    # 접근 제어: GST 소속 작업자 또는 관리자만 허용
    if worker.company != 'GST' and not worker.is_admin:
        return jsonify({
            'error': 'FORBIDDEN',
            'message': 'GST 소속 작업자만 접근할 수 있습니다.'
        }), 403

    # 상태 필터 파라미터
    status_filter = request.args.get('status', 'active').lower()

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # task_status 계산 조건:
        # not_started: started_at IS NULL
        # in_progress: started_at IS NOT NULL AND completed_at IS NULL AND is_paused = FALSE
        # paused: is_paused = TRUE
        # completed: completed_at IS NOT NULL

        if status_filter == 'all':
            status_condition = "t.started_at IS NOT NULL"
        elif status_filter == 'completed':
            status_condition = "t.completed_at IS NOT NULL"
        elif status_filter == 'not_started':
            status_condition = "t.started_at IS NULL"
        elif status_filter == 'in_progress':
            status_condition = "(t.started_at IS NOT NULL AND t.completed_at IS NULL AND t.is_paused = FALSE)"
        elif status_filter == 'paused':
            status_condition = "t.is_paused = TRUE"
        else:
            # default: active = 태깅(작업시작)된 제품만 (in_progress + paused)
            status_condition = "(t.started_at IS NOT NULL AND t.completed_at IS NULL)"

        cur.execute(
            f"""
            SELECT
                t.id AS task_detail_id,
                t.serial_number,
                t.task_id,
                t.task_name,
                t.started_at,
                t.completed_at,
                t.is_paused,
                t.is_applicable,
                t.worker_id,
                t.created_at AS task_created_at,
                w.name AS worker_name,
                p.model
            FROM app_task_details t
            LEFT JOIN workers w ON w.id = t.worker_id
            LEFT JOIN plan.product_info p ON p.serial_number = t.serial_number
            WHERE t.task_category = %s
              AND {status_condition}
            ORDER BY t.created_at DESC
            """,
            (category,)
        )
        rows = cur.fetchall()

        products = []
        task_detail_ids = []
        for row in rows:
            # task_status 계산
            if row['completed_at'] is not None:
                task_status = 'completed'
            elif row['is_paused']:
                task_status = 'paused'
            elif row['started_at'] is not None:
                task_status = 'in_progress'
            else:
                task_status = 'not_started'

            products.append({
                'task_detail_id': row['task_detail_id'],
                'serial_number': row['serial_number'],
                'model': row['model'],
                'task_id': row['task_id'],
                'task_name': row['task_name'],
                'task_status': task_status,
                'worker_id': row['worker_id'],
                'worker_name': row['worker_name'],
                'started_at': row['started_at'].isoformat() if row['started_at'] else None,
                'completed_at': row['completed_at'].isoformat() if row['completed_at'] else None,
                'is_paused': row['is_paused'],
                'is_applicable': row['is_applicable'],
            })
            task_detail_ids.append(row['task_detail_id'])

        # workers 배열 일괄 조회 (N+1 방지)
        workers_by_task: dict = {p['task_detail_id']: [] for p in products}
        if task_detail_ids:
            try:
                cur.execute(
                    """
                    SELECT
                        wsl.task_id,
                        wsl.worker_id,
                        w.name AS worker_name,
                        wsl.started_at,
                        wcl.completed_at,
                        wcl.duration_minutes,
                        CASE WHEN wcl.id IS NOT NULL THEN 'completed' ELSE 'in_progress' END AS status
                    FROM work_start_log wsl
                    JOIN workers w ON wsl.worker_id = w.id
                    LEFT JOIN work_completion_log wcl
                        ON wsl.task_id = wcl.task_id AND wsl.worker_id = wcl.worker_id
                    WHERE wsl.task_id = ANY(%s)
                    ORDER BY wsl.task_id, wsl.started_at ASC
                    """,
                    (task_detail_ids,)
                )
                wrows = cur.fetchall()
                for wrow in wrows:
                    tid = wrow['task_id']
                    if tid in workers_by_task:
                        workers_by_task[tid].append({
                            'worker_id': wrow['worker_id'],
                            'worker_name': wrow['worker_name'],
                            'started_at': wrow['started_at'].isoformat() if wrow['started_at'] else None,
                            'completed_at': wrow['completed_at'].isoformat() if wrow['completed_at'] else None,
                            'duration_minutes': wrow['duration_minutes'],
                            'status': wrow['status'],
                        })
                # BUG-14: 다중 작업자 표시 디버깅
                for tid, wlist in workers_by_task.items():
                    if len(wlist) >= 2:
                        names = [w['worker_name'] for w in wlist]
                        logger.info(f"[BUG-14] GST task_id={tid} has {len(wlist)} workers: {names}")
            except Exception as e:
                logger.warning(f"GST workers batch query failed: {e}")

        # my_status 일괄 조회 (현재 작업자의 참여 상태: not_started / in_progress / completed)
        my_status_map: dict = {}
        if task_detail_ids:
            try:
                cur.execute(
                    """
                    SELECT t.id AS task_id,
                           CASE
                               WHEN wcl.id IS NOT NULL THEN 'completed'
                               WHEN wsl.id IS NOT NULL THEN 'in_progress'
                               ELSE 'not_started'
                           END AS my_status
                    FROM app_task_details t
                    LEFT JOIN work_start_log wsl ON wsl.task_id = t.id AND wsl.worker_id = %s
                    LEFT JOIN work_completion_log wcl ON wcl.task_id = t.id AND wcl.worker_id = %s
                    WHERE t.id = ANY(%s)
                    """,
                    (worker_id, worker_id, task_detail_ids)
                )
                for mrow in cur.fetchall():
                    my_status_map[mrow['task_id']] = mrow['my_status']
            except Exception as e:
                logger.warning(f"GST my_status batch query failed: {e}")

        for product in products:
            tid = product['task_detail_id']
            workers_list = workers_by_task.get(tid, [])
            # legacy fallback: work_start_log 없는 경우 단일 작업자 정보로 보완
            if not workers_list and product.get('worker_id'):
                started = product.get('started_at')
                completed = product.get('completed_at')
                status_str = 'completed' if completed else ('in_progress' if started else 'not_started')
                workers_list = [{
                    'worker_id': product['worker_id'],
                    'worker_name': product.get('worker_name'),
                    'started_at': started,
                    'completed_at': completed,
                    'duration_minutes': None,
                    'status': status_str,
                }]
            product['workers'] = workers_list
            product['my_status'] = my_status_map.get(tid, 'not_started')

        logger.info(
            f"GST products fetched: category={category}, status={status_filter}, "
            f"count={len(products)}, worker_id={worker_id}"
        )

        return jsonify({
            'products': products,
            'total': len(products),
            'category': category,
        }), 200

    except PsycopgError as e:
        logger.error(f"GST products query failed: category={category}, error={e}")
        return jsonify({
            'error': 'DB_ERROR',
            'message': '데이터베이스 조회 실패'
        }), 500
    finally:
        if conn:
            conn.close()
