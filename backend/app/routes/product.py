"""
제품 라우트
엔드포인트: /api/app/product/*
Sprint 2: QR 스캔 + 제품 조회 + Location 업데이트
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Tuple, Dict, Any

from app.middleware.jwt_auth import jwt_required, get_current_worker_id
from app.models.product_info import (
    get_product_by_qr_doc_id,
    update_location_qr,
    is_tms_product,
)
from app.services.task_service import TaskService
from app.services.task_seed import initialize_product_tasks


logger = logging.getLogger(__name__)

product_bp = Blueprint("product", __name__, url_prefix="/api/app/product")
task_service = TaskService()


@product_bp.route("/<qr_doc_id>", methods=["GET"])
@jwt_required
def get_product(qr_doc_id: str) -> Tuple[Dict[str, Any], int]:
    """
    QR 코드로 제품 조회

    Path Parameters:
        qr_doc_id: QR 문서 ID (예: DOC_GBWS-6408)

    Headers:
        Authorization: Bearer {token}

    Response:
        200: {
            "qr_doc_id": str,
            "serial_number": str,
            "model": str,
            "prod_date": str,
            "location_qr_id": str|null,
            "is_tms": bool
        }
        404: {"error": "PRODUCT_NOT_FOUND", "message": "..."}
    """
    # 제품 조회
    product = get_product_by_qr_doc_id(qr_doc_id)
    if not product:
        return jsonify({
            'error': 'PRODUCT_NOT_FOUND',
            'message': '제품을 찾을 수 없습니다.'
        }), 404

    # Task Seed 자동 초기화 (ON CONFLICT DO NOTHING — 이미 있으면 무시)
    try:
        seed_result = initialize_product_tasks(
            serial_number=product.serial_number,
            qr_doc_id=product.qr_doc_id,
            model_name=product.model
        )
        if seed_result.get('created', 0) > 0:
            logger.info(
                f"Task seed auto-initialized: serial={product.serial_number}, "
                f"created={seed_result['created']}, skipped={seed_result['skipped']}"
            )
    except Exception as e:
        logger.warning(f"Task seed failed (non-blocking): {e}")

    # TMS 제품 여부 확인
    is_tms = is_tms_product(product)

    return jsonify({
        'id': product.id,
        'qr_doc_id': product.qr_doc_id,
        'serial_number': product.serial_number,
        'model': product.model,
        'prod_date': product.prod_date.isoformat() if product.prod_date else None,
        'location_qr_id': product.location_qr_id,
        'mech_partner': product.mech_partner,
        'elec_partner': product.elec_partner,
        'module_outsourcing': product.module_outsourcing,
        'created_at': product.created_at.isoformat() if product.created_at else None,
        'updated_at': product.updated_at.isoformat() if product.updated_at else None,
        'is_tms': is_tms
    }), 200


@product_bp.route("/location/update", methods=["POST"])
@jwt_required
def update_location() -> Tuple[Dict[str, Any], int]:
    """
    제품의 Location QR 업데이트

    Request Body:
        {
            "qr_doc_id": str,
            "location_qr_id": str
        }

    Headers:
        Authorization: Bearer {token}

    Response:
        200: {"message": "위치 정보가 업데이트되었습니다."}
        400: {"error": "INVALID_REQUEST", "message": "..."}
        404: {"error": "PRODUCT_NOT_FOUND", "message": "..."}
    """
    data = request.get_json()

    # 필수 필드 확인
    if not data or not all(k in data for k in ['qr_doc_id', 'location_qr_id']):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'qr_doc_id와 location_qr_id가 필요합니다.'
        }), 400

    qr_doc_id = data['qr_doc_id']
    location_qr_id = data['location_qr_id']

    # 제품 존재 확인
    product = get_product_by_qr_doc_id(qr_doc_id)
    if not product:
        return jsonify({
            'error': 'PRODUCT_NOT_FOUND',
            'message': '제품을 찾을 수 없습니다.'
        }), 404

    # Location QR 업데이트
    success = update_location_qr(qr_doc_id, location_qr_id)
    if not success:
        return jsonify({
            'error': 'UPDATE_FAILED',
            'message': '위치 정보 업데이트 실패'
        }), 500

    logger.info(f"Location updated: qr_doc_id={qr_doc_id}, location_qr_id={location_qr_id}")

    return jsonify({
        'message': '위치 정보가 업데이트되었습니다.',
        'qr_doc_id': qr_doc_id,
        'location_qr_id': location_qr_id
    }), 200


@product_bp.route("/<qr_doc_id>/tasks", methods=["GET"])
@jwt_required
def get_product_tasks(qr_doc_id: str) -> Tuple[Dict[str, Any], int]:
    """
    제품의 작업 목록 조회 (역할별 필터링 가능)

    Path Parameters:
        qr_doc_id: QR 문서 ID

    Query Parameters:
        task_category: Task 카테고리 (MM, EE, TM, PI, QI, SI), 없으면 전체 조회

    Headers:
        Authorization: Bearer {token}

    Response:
        200: {
            "qr_doc_id": str,
            "serial_number": str,
            "task_category": str|null,
            "tasks": [{...}],
            "total": int
        }
        404: {"error": "PRODUCT_NOT_FOUND", "message": "..."}
    """
    # Query parameter 추출
    task_category = request.args.get('task_category')

    # task_service 호출
    response, status_code = task_service.get_tasks_by_product(qr_doc_id, task_category)
    return jsonify(response), status_code


@product_bp.route("/<qr_doc_id>/completion", methods=["GET"])
@jwt_required
def get_completion_status(qr_doc_id: str) -> Tuple[Dict[str, Any], int]:
    """
    제품의 공정 완료 상태 조회

    Path Parameters:
        qr_doc_id: QR 문서 ID

    Headers:
        Authorization: Bearer {token}

    Response:
        200: {
            "qr_doc_id": str,
            "serial_number": str,
            "mech_completed": bool,
            "elec_completed": bool,
            ...
        }
        404: {"error": "PRODUCT_NOT_FOUND", "message": "..."}
    """
    # task_service 호출
    response, status_code = task_service.get_completion_status(qr_doc_id)
    return jsonify(response), status_code


@product_bp.route("/<qr_doc_id>/check-prerequisites", methods=["GET"])
@jwt_required
def check_prerequisites(qr_doc_id: str) -> Tuple[Dict[str, Any], int]:
    """
    공정 시작 전 선행 공정 완료 확인 (PI/QI/SI용)

    Path Parameters:
        qr_doc_id: QR 문서 ID

    Query Parameters:
        process_type: 공정 유형 (PI, QI, SI)

    Headers:
        Authorization: Bearer {token}

    Response:
        200: {
            "qr_doc_id": str,
            "process_type": str,
            "can_proceed": bool,
            "warnings": [{...}]
        }
        400: {"error": "INVALID_REQUEST", "message": "..."}
    """
    # Query parameter 추출
    process_type = request.args.get('process_type')

    if not process_type:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'process_type 파라미터가 필요합니다.'
        }), 400

    # task_service 호출
    response, status_code = task_service.check_process_prerequisites(qr_doc_id, process_type)
    return jsonify(response), status_code
