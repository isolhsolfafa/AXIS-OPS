"""
출하이력 페이지 API 라우트 (Sprint 76-BE, v2.18.28)

엔드포인트: /api/admin/shipment/*
- summary: KPI + 분포 통합 응답
- details: S/N 단위 1:1 + 페이지네이션 + 필터

권한: @jwt_required + @gst_or_admin_required (Codex Q6 M — GST only)
설계서: AGENT_TEAM_LAUNCH.md § Sprint 76-BE
"""

import logging

from flask import Blueprint, jsonify, request

from app.middleware.jwt_auth import jwt_required, gst_or_admin_required
from app.services.shipment_history_service import (
    InvariantViolationError,
    get_shipment_summary,
    get_shipment_details,
)

logger = logging.getLogger(__name__)

shipment_history_bp = Blueprint("shipment_history", __name__, url_prefix="/api/admin/shipment")


@shipment_history_bp.route('/summary', methods=['GET'])
@jwt_required
@gst_or_admin_required
def shipment_summary():
    """GET /api/admin/shipment/summary"""
    period = request.args.get('period', 'month')
    reference_date = request.args.get('reference_date')
    # partner = request.args.get('partner')  # Sprint 72 연계 (현재 무의미)

    if period not in ('month', 'quarter', 'year'):
        return jsonify({
            'error': 'INVALID_PERIOD',
            'message': "period 는 month/quarter/year 중 하나",
        }), 400

    try:
        response = get_shipment_summary(period=period, reference_date=reference_date)
        return jsonify(response), 200
    except InvariantViolationError as e:
        return jsonify({
            'error': 'INVARIANT_VIOLATION',
            'message': '데이터 정합 오류',
            'detail': e.issues,
        }), 500
    except ValueError as e:
        return jsonify({
            'error': 'INVALID_PARAMS',
            'message': str(e),
        }), 400


@shipment_history_bp.route('/details', methods=['GET'])
@jwt_required
@gst_or_admin_required
def shipment_details():
    """GET /api/admin/shipment/details"""
    period = request.args.get('period', 'month')
    reference_date = request.args.get('reference_date')
    target_date = request.args.get('date')
    status = request.args.get('status')
    partner = request.args.get('partner')
    q = request.args.get('q')

    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
    except ValueError:
        return jsonify({
            'error': 'INVALID_PARAMS',
            'message': 'page / per_page 는 정수',
        }), 400

    if period not in ('month', 'quarter', 'year'):
        return jsonify({
            'error': 'INVALID_PERIOD',
            'message': "period 는 month/quarter/year 중 하나",
        }), 400

    if status and status not in ('shipped', 'pending', 'delayed'):
        return jsonify({
            'error': 'INVALID_STATUS',
            'message': "status 는 shipped/pending/delayed 중 하나 또는 미지정",
        }), 400

    if page < 1 or per_page < 1 or per_page > 200:
        return jsonify({
            'error': 'INVALID_PARAMS',
            'message': 'page >= 1, 1 <= per_page <= 200',
        }), 400

    try:
        response = get_shipment_details(
            period=period,
            reference_date=reference_date,
            target_date=target_date,
            status=status,
            partner=partner,
            q=q,
            page=page,
            per_page=per_page,
        )
        return jsonify(response), 200
    except ValueError as e:
        return jsonify({
            'error': 'INVALID_PARAMS',
            'message': str(e),
        }), 400
