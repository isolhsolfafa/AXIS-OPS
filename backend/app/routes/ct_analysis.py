"""
Sprint 85 (FEAT-CT-ANALYSIS-HUB-BE-MVP-20260605) — CT 분석 허브 endpoint 2개

  GET /api/ct/data-quality                          — ① 데이터 신뢰도
  GET /api/ct/task-stats?period=&model=&category=    — ② CT 표준(IQR, man-hour)

권한: admin OR GST manager (@jwt_required + @gst_or_admin_required, Sprint 27 표준)
설계서: AGENT_TEAM_LAUNCH.md § Sprint 85
"""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from app.middleware.jwt_auth import gst_or_admin_required, jwt_required
from app.services.statistics_service import (
    CtParamError,
    get_data_quality,
    get_task_ct_stats,
)

logger = logging.getLogger(__name__)

ct_analysis_bp = Blueprint("ct_analysis", __name__, url_prefix="/api/ct")


@ct_analysis_bp.route("/data-quality", methods=["GET"])
@jwt_required
@gst_or_admin_required
def data_quality():
    """① duration_source 분포 + 자동마감 추이 + 교육 전후."""
    try:
        return jsonify(get_data_quality()), 200
    except Exception:
        logger.exception("[ct] data-quality 산출 실패")
        return jsonify({"error": "INTERNAL_ERROR", "message": "데이터 신뢰도 산출 실패"}), 500


@ct_analysis_bp.route("/task-stats", methods=["GET"])
@jwt_required
@gst_or_admin_required
def task_stats():
    """② task별 box plot(basis=duration|active) + 카테고리 요약 + meta.

    S-1 (VIEW #82 ⓐ): period 제거 → basis/from/to(YYYY-MM, KST 윈도우).
    """
    basis = (request.args.get("basis") or "duration").strip().lower()
    from_month = request.args.get("from")
    to_month = request.args.get("to")
    model = request.args.get("model")
    category = request.args.get("category")

    # VIEW #81: dual = dual/single (미지정 = 합산 하위호환). 화이트리스트.
    dual = (request.args.get("dual") or "").strip().lower() or None
    if dual is not None and dual not in ("dual", "single"):
        return jsonify({
            "error": "INVALID_DUAL",
            "message": "dual 은 'dual' | 'single' 중 하나여야 합니다.",
        }), 400

    try:
        return jsonify(get_task_ct_stats(
            basis=basis, from_month=from_month, to_month=to_month,
            model=model, category=category, dual=dual,
        )), 200
    except CtParamError as e:
        return jsonify({"error": e.code, "message": e.message}), 400
    except Exception:
        logger.exception("[ct] task-stats 산출 실패")
        return jsonify({"error": "INTERNAL_ERROR", "message": "CT 표준 산출 실패"}), 500
