"""
Work Batch 엔드포인트 (Sprint 64-BE v3)

TM Tank Module 일괄 시작/완료 처리 — FE Sprint 40 v1.40.0 contract 정합.
work.py 1,355 LOC (🔴 800줄+ CLAUDE.md L545 필수 분할 영역) 분리 정책 정합.

엔드포인트 영역 (3건):
  POST /api/app/work/start-batch     — TM Tank Module 일괄 시작 (최대 30건)
  POST /api/app/work/complete-batch  — TM Tank Module 일괄 완료 (최대 30건)
  GET  /api/app/tasks/by-order/<sales_order>  — FE Sprint 40 prefetch (N+1 제거)

work_bp blueprint 재사용 (url_prefix='/api/app' 단일 영역, prefix 중복 회피).
"""
import logging
from typing import Tuple, Dict, Any

from flask import request, jsonify

from app.routes.work import work_bp  # 기존 blueprint 재사용 (url_prefix='/api/app')
from app.middleware.jwt_auth import (
    jwt_required,
    manager_or_admin_required,
    get_current_worker,
)
from app.services import task_service_batch

logger = logging.getLogger(__name__)


# ── 입력 검증 helper ─────────────────────────────────────────

def _validate_batch_input(data: Any) -> Tuple[bool, Any]:
    """task_detail_ids 배열 검증 — 빈 / 30 초과 / 비-정수 영역 차단.

    Returns:
        (is_valid, payload_or_error_response)
    """
    task_detail_ids = data.get('task_detail_ids') if data else None

    if not task_detail_ids or not isinstance(task_detail_ids, list):
        return (False, ({'error': 'INVALID_REQUEST',
                         'message': 'task_detail_ids 배열이 필요합니다.'}, 400))
    if len(task_detail_ids) > 30:
        return (False, ({'error': 'INVALID_REQUEST',
                         'message': '최대 30개까지 일괄 처리 가능합니다.'}, 400))
    if not all(isinstance(i, int) for i in task_detail_ids):
        return (False, ({'error': 'INVALID_REQUEST',
                         'message': 'task_detail_ids 는 정수 배열이어야 합니다.'}, 400))

    return (True, task_detail_ids)


# ── 엔드포인트 영역 ─────────────────────────────────────────

@work_bp.route("/work/start-batch", methods=["POST"])
@jwt_required
@manager_or_admin_required
def start_work_batch_route() -> Tuple[Any, int]:
    """TM Tank Module 일괄 시작 (Sprint 40 FE / 64-BE v3 BE).

    Request Body: { "task_detail_ids": [int, ...] }  // 최소 1개, 최대 30개
    Response 200: { succeeded: [...], skipped: [...], total: int }
    Response 400: INVALID_REQUEST | NOT_TANK_MODULE_ANY
    Response 403: @manager_or_admin_required 영역 처리
    """
    is_valid, payload = _validate_batch_input(request.get_json())
    if not is_valid:
        response, status_code = payload
        return jsonify(response), status_code

    task_detail_ids = payload
    worker = get_current_worker()
    response, status_code = task_service_batch.start_work_batch(
        worker_id=worker.id,
        task_detail_ids=task_detail_ids,
        is_admin=worker.is_admin,
        manager_company=worker.company if (worker.is_manager and not worker.is_admin) else None,
    )
    return jsonify(response), status_code


@work_bp.route("/work/complete-batch", methods=["POST"])
@jwt_required
@manager_or_admin_required
def complete_work_batch_route() -> Tuple[Any, int]:
    """TM Tank Module 일괄 완료 — start-batch 대칭 구조."""
    is_valid, payload = _validate_batch_input(request.get_json())
    if not is_valid:
        response, status_code = payload
        return jsonify(response), status_code

    task_detail_ids = payload
    worker = get_current_worker()
    response, status_code = task_service_batch.complete_work_batch(
        worker_id=worker.id,
        task_detail_ids=task_detail_ids,
        is_admin=worker.is_admin,
        manager_company=worker.company if (worker.is_manager and not worker.is_admin) else None,
    )
    return jsonify(response), status_code


@work_bp.route("/tasks/by-order/<sales_order>", methods=["GET"])
@jwt_required
def tasks_by_order_route(sales_order: str) -> Tuple[Any, int]:
    """FE Sprint 40 prefetch — 동일 O/N TANK_MODULE task 일괄 조회 (N+1 제거)."""
    task_categories = request.args.get('task_categories', 'TMS,MECH').split(',')
    task_id = request.args.get('task_id', 'TANK_MODULE')
    response, status_code = task_service_batch.get_tasks_by_order(
        sales_order=sales_order,
        task_categories=task_categories,
        task_id=task_id,
    )
    return jsonify(response), status_code
