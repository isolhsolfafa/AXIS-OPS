"""
작업 라우트
엔드포인트: /api/app/work/*
Sprint 2: 작업 시작/완료 처리 + Task 목록/완료상태/검증/토글
"""

import logging
from flask import Blueprint, request, jsonify, g
from typing import Tuple, Dict, Any

from app.middleware.jwt_auth import jwt_required, get_current_worker_id
from app.services.task_service import TaskService
from app.models.task_detail import get_task_by_id, get_tasks_by_serial_number
from app.models.completion_status import get_or_create_completion_status
from app.models.product_info import get_product_by_serial_number


logger = logging.getLogger(__name__)

work_bp = Blueprint("work", __name__, url_prefix="/api/app")
task_service = TaskService()


def _task_to_dict(task) -> Dict[str, Any]:
    """TaskDetail 객체를 API 응답용 dict로 변환"""
    return {
        'id': task.id,
        'worker_id': task.worker_id,
        'serial_number': task.serial_number,
        'qr_doc_id': task.qr_doc_id,
        'task_category': task.task_category,
        'task_id': task.task_id,
        'task_name': task.task_name,
        'process_type': task.task_category,  # FE 호환: task_category를 process_type으로도 제공
        'started_at': task.started_at.isoformat() if task.started_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
        'duration': task.duration_minutes,  # FE 호환: duration_minutes를 duration으로도 제공
        'duration_minutes': task.duration_minutes,
        'is_applicable': task.is_applicable,
        'location_qr_verified': task.location_qr_verified,
        'created_at': task.created_at.isoformat() if task.created_at else None,
        'updated_at': task.updated_at.isoformat() if task.updated_at else None,
    }


@work_bp.route("/work/start", methods=["POST"])
@jwt_required
def start_work() -> Tuple[Dict[str, Any], int]:
    """
    작업 시작

    Request Body:
        {
            "task_detail_id": int  (또는 "task_id": int)
        }

    Headers:
        Authorization: Bearer {token}

    Response:
        200: 업데이트된 TaskDetail 전체 정보
        400: {"error": "TASK_ALREADY_STARTED", "message": "..."}
        403: {"error": "FORBIDDEN", "message": "..."}
        404: {"error": "TASK_NOT_FOUND", "message": "..."}
    """
    data = request.get_json()

    # 필수 필드 확인 (task_detail_id 또는 task_id 허용)
    task_detail_id = None
    if data:
        task_detail_id = data.get('task_detail_id') or data.get('task_id')

    if not task_detail_id:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'task_detail_id 또는 task_id가 필요합니다.'
        }), 400

    # 현재 작업자 ID 추출 (JWT에서)
    worker_id = get_current_worker_id()

    # task_service 호출
    response, status_code = task_service.start_work(
        worker_id=worker_id,
        task_detail_id=task_detail_id
    )

    # 성공 시 업데이트된 전체 TaskDetail 반환
    if status_code == 200:
        updated_task = get_task_by_id(task_detail_id)
        if updated_task:
            return jsonify(_task_to_dict(updated_task)), 200

    return jsonify(response), status_code


@work_bp.route("/work/complete", methods=["POST"])
@jwt_required
def complete_work() -> Tuple[Dict[str, Any], int]:
    """
    작업 완료

    Request Body:
        {
            "task_detail_id": int  (또는 "task_id": int)
        }

    Headers:
        Authorization: Bearer {token}

    Response:
        200: 업데이트된 TaskDetail 전체 정보 + category_completed 플래그
        400: {"error": "TASK_NOT_STARTED|TASK_ALREADY_COMPLETED", "message": "..."}
        403: {"error": "FORBIDDEN", "message": "..."}
        404: {"error": "TASK_NOT_FOUND", "message": "..."}
    """
    data = request.get_json()

    # 필수 필드 확인 (task_detail_id 또는 task_id 허용)
    task_detail_id = None
    if data:
        task_detail_id = data.get('task_detail_id') or data.get('task_id')

    if not task_detail_id:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'task_detail_id 또는 task_id가 필요합니다.'
        }), 400

    # 현재 작업자 ID 추출 (JWT에서)
    worker_id = get_current_worker_id()

    # task_service 호출
    response, status_code = task_service.complete_work(
        worker_id=worker_id,
        task_detail_id=task_detail_id
    )

    # 성공 시 업데이트된 전체 TaskDetail 반환
    if status_code == 200:
        updated_task = get_task_by_id(task_detail_id)
        if updated_task:
            result = _task_to_dict(updated_task)
            result['category_completed'] = response.get('category_completed', False)
            if 'duration_warnings' in response:
                result['duration_warnings'] = response['duration_warnings']
            return jsonify(result), 200

    return jsonify(response), status_code


# === 편의 라우트: FE task_service.dart 호환 ===


@work_bp.route("/tasks/<serial_number>", methods=["GET"])
@jwt_required
def get_tasks_by_serial(serial_number: str) -> Tuple[Dict[str, Any], int]:
    """
    시리얼 번호로 Task 목록 조회

    Path Parameters:
        serial_number: 제품 시리얼 번호

    Query Parameters:
        worker_id: 작업자 ID (선택, 현재는 미사용)
        process_type: 공정 유형 필터 (MM, EE, TM, PI, QI, SI)

    Response:
        200: Task 목록 (리스트 형태)
    """
    task_category = request.args.get('process_type')

    tasks = get_tasks_by_serial_number(serial_number, task_category)
    task_list = [_task_to_dict(task) for task in tasks]

    return jsonify(task_list), 200


@work_bp.route("/completion/<serial_number>", methods=["GET"])
@jwt_required
def get_completion_by_serial(serial_number: str) -> Tuple[Dict[str, Any], int]:
    """
    시리얼 번호로 공정 완료 상태 조회

    Path Parameters:
        serial_number: 제품 시리얼 번호

    Response:
        200: 완료 상태 정보
        404: 시리얼 번호에 해당하는 완료 상태 없음
    """
    status = get_or_create_completion_status(serial_number)
    if not status:
        return jsonify({
            'error': 'STATUS_ERROR',
            'message': '완료 상태 조회 실패'
        }), 500

    product = get_product_by_serial_number(serial_number)

    return jsonify({
        'qr_doc_id': product.qr_doc_id if product else None,
        'serial_number': serial_number,
        'mm_completed': status.mm_completed,
        'ee_completed': status.ee_completed,
        'tm_completed': status.tm_completed,
        'pi_completed': status.pi_completed,
        'qi_completed': status.qi_completed,
        'si_completed': status.si_completed,
        'all_completed': status.all_completed,
        'all_completed_at': status.all_completed_at.isoformat() if status.all_completed_at else None,
    }), 200


@work_bp.route("/validation/check-process", methods=["POST"])
@jwt_required
def validate_process() -> Tuple[Dict[str, Any], int]:
    """
    공정 누락 검증 (PI/QI/SI용)
    Sprint 3: process_validator 연동

    Request Body:
        {
            "serial_number": str,
            "process_type": str (PI, QI, SI)
        }

    Response:
        200: {"valid": bool, "missing_processes": [...], "message": str, "alerts_created": int}
    """
    data = request.get_json()
    if not data or not all(k in data for k in ['serial_number', 'process_type']):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'serial_number와 process_type이 필요합니다.'
        }), 400

    serial_number = data['serial_number']
    process_type = data['process_type']

    # JWT에서 worker_id 추출
    worker_id = get_current_worker_id()

    # serial_number로 제품 조회 → qr_doc_id 획득
    product = get_product_by_serial_number(serial_number)
    if not product:
        return jsonify({
            'error': 'PRODUCT_NOT_FOUND',
            'message': '제품을 찾을 수 없습니다.'
        }), 404

    # Sprint 3: process_validator 사용 (알림 생성 포함)
    from app.services.process_validator import validate_process_start
    validation_result = validate_process_start(
        serial_number=serial_number,
        process_type=process_type,
        qr_doc_id=product.qr_doc_id,
        triggered_by_worker_id=worker_id
    )

    # FE 호환 응답 형식으로 변환
    warnings = validation_result.get('warnings', [])
    missing_processes = []
    for warning in warnings:
        if 'MM' in warning:
            missing_processes.append('MM')
        if 'EE' in warning:
            missing_processes.append('EE')

    return jsonify({
        'valid': validation_result.get('can_proceed', True),
        'missing_processes': missing_processes,
        'location_qr_verified': product.location_qr_id is not None,
        'message': warnings[0] if warnings else None,
        'alerts_created': validation_result.get('alerts_created', 0)
    }), 200


@work_bp.route("/task/toggle-applicable", methods=["PUT"])
@jwt_required
def toggle_task_applicable() -> Tuple[Dict[str, Any], int]:
    """
    Task 적용 여부 토글 (관리자/사내직원 전용)

    Request Body:
        {
            "task_id": int,
            "is_applicable": bool
        }

    Response:
        200: 업데이트된 TaskDetail 전체 정보
        404: Task를 찾을 수 없음
    """
    data = request.get_json()
    if not data or 'task_id' not in data or 'is_applicable' not in data:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'task_id와 is_applicable이 필요합니다.'
        }), 400

    task_id = data['task_id']
    is_applicable = data['is_applicable']

    task = get_task_by_id(task_id)
    if not task:
        return jsonify({
            'error': 'TASK_NOT_FOUND',
            'message': '작업을 찾을 수 없습니다.'
        }), 404

    # toggle_task_applicable CRUD 함수 호출
    from app.models.task_detail import toggle_task_applicable as db_toggle
    success = db_toggle(task_id, is_applicable)

    if not success:
        return jsonify({
            'error': 'UPDATE_FAILED',
            'message': 'Task 적용 여부 업데이트 실패'
        }), 500

    updated_task = get_task_by_id(task_id)
    return jsonify(_task_to_dict(updated_task)), 200


@work_bp.route("/location/update", methods=["POST"])
@jwt_required
def update_location_compat() -> Tuple[Dict[str, Any], int]:
    """
    Location QR 업데이트 (FE 호환 경로)

    Request Body:
        {
            "qr_doc_id": str,
            "location_qr_id": str
        }

    Response:
        200: 업데이트된 ProductInfo 전체 정보
    """
    from app.models.product_info import get_product_by_qr_doc_id, update_location_qr

    data = request.get_json()
    if not data or not all(k in data for k in ['qr_doc_id', 'location_qr_id']):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'qr_doc_id와 location_qr_id가 필요합니다.'
        }), 400

    qr_doc_id = data['qr_doc_id']
    location_qr_id = data['location_qr_id']

    product = get_product_by_qr_doc_id(qr_doc_id)
    if not product:
        return jsonify({
            'error': 'PRODUCT_NOT_FOUND',
            'message': '제품을 찾을 수 없습니다.'
        }), 404

    success = update_location_qr(qr_doc_id, location_qr_id)
    if not success:
        return jsonify({
            'error': 'UPDATE_FAILED',
            'message': '위치 정보 업데이트 실패'
        }), 500

    # 업데이트된 제품 정보 반환 (FE가 ProductInfo.fromJson 기대)
    updated_product = get_product_by_qr_doc_id(qr_doc_id)
    return jsonify({
        'id': updated_product.id,
        'qr_doc_id': updated_product.qr_doc_id,
        'serial_number': updated_product.serial_number,
        'model': updated_product.model,
        'production_date': updated_product.production_date.isoformat(),
        'location_qr_id': updated_product.location_qr_id,
        'mech_partner': updated_product.mech_partner,
        'module_outsourcing': updated_product.module_outsourcing,
        'created_at': updated_product.created_at.isoformat(),
        'updated_at': updated_product.updated_at.isoformat(),
    }), 200
