"""
출하 완료 엔드포인트 (Sprint 68 — FEAT-SHIPMENT-COMPLETE)

POST /api/app/work/ship-complete — 한 S/N 의 SI task 2개
(SI_FINISHING + SI_SHIPMENT)를 완료 처리. admin/manager 가 작업자 대신 대행.

work.py 1,355 LOC (🔴 CLAUDE.md L545 필수 분할 영역) 분리 정책 정합 — 신규 파일.
work_bp blueprint 재사용 (url_prefix='/api/app').

설계: AGENT_TEAM_LAUNCH.md § Sprint 68
"""
import logging
from typing import Tuple, Any

from flask import request, jsonify

from app.routes.work import work_bp  # 기존 blueprint 재사용
from app.middleware.jwt_auth import (
    jwt_required,
    manager_or_admin_required,
    get_current_worker,
)
from app.services import shipment_service

logger = logging.getLogger(__name__)


@work_bp.route("/work/ship-complete", methods=["POST"])
@jwt_required
@manager_or_admin_required
def ship_complete_route() -> Tuple[Any, int]:
    """출하 완료 — 한 S/N 의 SI task 2개(SI_FINISHING + SI_SHIPMENT) 완료.

    Request Body: { "serial_number": str, "completed_at": str|null(옵션 ISO8601) }
    Response 200: { serial_number, completed_tasks, si_completed,
                    completed_at, already_completed }
    Response 400: INVALID_REQUEST | INVALID_COMPLETED_AT* | SI_FINISHING_NOT_STARTED
    Response 404: SI_TASK_NOT_FOUND
    Response 403: @manager_or_admin_required 영역 처리
    """
    data = request.get_json() or {}
    serial_number = data.get('serial_number')
    if not serial_number or not isinstance(serial_number, str):
        return jsonify({'error': 'INVALID_REQUEST',
                        'message': 'serial_number 가 필요합니다.'}), 400

    completed_at_raw = data.get('completed_at')
    worker = get_current_worker()
    response, status_code = shipment_service.ship_complete(
        serial_number=serial_number,
        admin_worker_id=worker.id,
        completed_at_raw=completed_at_raw,
    )
    return jsonify(response), status_code


@work_bp.route("/work/admin-complete", methods=["POST"])
@jwt_required
@manager_or_admin_required
def admin_complete_route() -> Tuple[Any, int]:
    """PI/QI 공정 admin/manager 정상 완료 (Sprint 69 — FEAT-PIQI-COMPLETE-OWNER-LOCK).

    PI/QI 검사는 시작한 본인만 완료(complete_work cross 차단). 불가피 시
    admin/manager 가 종료 시각을 지정해 해당 공정 미완료 task 전수 정상 완료.

    Request Body: { serial_number, task_category('PI'|'QI'), completed_at?(옵션 ISO8601) }
    Response 200: { serial_number, task_category, completed_tasks, completed_at, already_completed }
    Response 400: INVALID_REQUEST | INVALID_CATEGORY | INVALID_COMPLETED_AT* | TASK_NOT_STARTED
    Response 404: TASK_NOT_FOUND
    """
    data = request.get_json() or {}
    serial_number = data.get('serial_number')
    task_category = data.get('task_category')
    if not serial_number or not isinstance(serial_number, str):
        return jsonify({'error': 'INVALID_REQUEST',
                        'message': 'serial_number 가 필요합니다.'}), 400
    if task_category not in ('PI', 'QI'):
        return jsonify({'error': 'INVALID_REQUEST',
                        'message': 'task_category 는 PI 또는 QI 여야 합니다.'}), 400

    worker = get_current_worker()
    response, status_code = shipment_service.admin_complete(
        serial_number=serial_number,
        task_category=task_category,
        admin_worker_id=worker.id,
        completed_at_raw=data.get('completed_at'),
    )
    return jsonify(response), status_code
