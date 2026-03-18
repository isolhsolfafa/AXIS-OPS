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
from app.models.worker import get_worker_by_id
from app.services.task_service import TaskService
from app.services.task_seed import initialize_product_tasks
from app.services.progress_service import get_partner_sn_progress


logger = logging.getLogger(__name__)

product_bp = Blueprint("product", __name__, url_prefix="/api/app/product")
task_service = TaskService()


@product_bp.route("/progress", methods=["GET"])
@jwt_required
def get_sn_progress() -> Tuple[Dict[str, Any], int]:
    """
    협력사별 S/N 작업 진행률 조회 (Sprint 18)

    Query Parameters:
        company: (admin 전용) 특정 회사 필터
        days: 완료 후 N일 이내 포함 (기본 1)

    Headers:
        Authorization: Bearer {token}

    Response:
        200: { "products": [...], "summary": { "total", "in_progress", "completed_recent" } }
    """
    worker = get_worker_by_id(get_current_worker_id())
    if not worker:
        return jsonify({'error': 'WORKER_NOT_FOUND', 'message': '작업자를 찾을 수 없습니다.'}), 404

    # admin이면 company 파라미터 허용
    company_override = request.args.get('company') if worker.is_admin else None
    days = request.args.get('days', 1, type=int)

    try:
        result = get_partner_sn_progress(
            worker_company=worker.company,
            worker_role=worker.role,
            is_admin=worker.is_admin,
            include_completed_within_days=days,
            company_override=company_override,
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Progress query failed: {e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': '진행률 조회 실패'}), 500


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
    # 제품 조회 (active 상태만)
    product = get_product_by_qr_doc_id(qr_doc_id, include_shipped=False)
    if not product:
        # active에서 못 찾으면 shipped 확인 (모든 사용자 공통)
        shipped_product = get_product_by_qr_doc_id(qr_doc_id, include_shipped=True)
        if shipped_product:
            return jsonify({
                'error': 'PRODUCT_SHIPPED',
                'message': '출고 완료된 제품입니다.',
                'serial_number': shipped_product.serial_number,
                'model': shipped_product.model,
            }), 200
        return jsonify({
            'error': 'PRODUCT_NOT_FOUND',
            'message': '제품을 찾을 수 없습니다.'
        }), 404

    # Sprint 31A: TANK QR 스캔 시 PRODUCT QR로 task_seed 실행
    # TANK QR의 parent_qr_doc_id = PRODUCT QR의 qr_doc_id
    seed_qr_doc_id = product.qr_doc_id
    try:
        from app.models.worker import get_db_connection
        from app.db_pool import put_conn as _put_conn
        _conn = get_db_connection()
        _cur = _conn.cursor()
        _cur.execute(
            "SELECT parent_qr_doc_id FROM qr_registry WHERE qr_doc_id = %s",
            (qr_doc_id,)
        )
        _qr_row = _cur.fetchone()
        if _qr_row and _qr_row.get('parent_qr_doc_id'):
            seed_qr_doc_id = _qr_row['parent_qr_doc_id']
        _put_conn(_conn)
    except Exception:
        pass  # fallback: 스캔한 QR 그대로 사용

    # Task Seed 자동 초기화 (ON CONFLICT DO NOTHING — 이미 있으면 무시)
    try:
        seed_result = initialize_product_tasks(
            serial_number=product.serial_number,
            qr_doc_id=seed_qr_doc_id,
            model_name=product.model
        )
        if seed_result.get('created', 0) > 0:
            logger.info(
                f"Task seed auto-initialized: serial={product.serial_number}, "
                f"created={seed_result['created']}, skipped={seed_result['skipped']}"
            )
    except Exception as e:
        import traceback
        logger.error(
            f"Task seed FAILED: serial={product.serial_number}, "
            f"model={product.model}, error={e}\n"
            f"Traceback: {traceback.format_exc()}"
        )

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
        'sales_order': product.sales_order,
        'customer': product.customer,
        'title_number': product.title_number,
        'mech_start': product.mech_start.isoformat() if product.mech_start else None,
        'mech_end': product.mech_end.isoformat() if product.mech_end else None,
        'elec_start': product.elec_start.isoformat() if product.elec_start else None,
        'elec_end': product.elec_end.isoformat() if product.elec_end else None,
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
