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
    get_data_quality,
    get_task_ct_stats,
)

logger = logging.getLogger(__name__)

ct_analysis_bp = Blueprint("ct_analysis", __name__, url_prefix="/api/ct")

_VALID_PERIODS = {"last_90d"}  # MVP: 90일 합산만
_PERIOD_LOOKBACK = {"last_90d": 90}


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
    """② task별 box plot(man-hour) + 카테고리 요약 + meta."""
    period = (request.args.get("period") or "last_90d").strip()
    if period not in _VALID_PERIODS:
        return jsonify({
            "error": "INVALID_PERIOD",
            "message": f"period 는 {sorted(_VALID_PERIODS)} 중 하나여야 합니다.",
        }), 400

    model = request.args.get("model")
    category = request.args.get("category")
    lookback = _PERIOD_LOOKBACK[period]

    try:
        return jsonify(get_task_ct_stats(lookback_days=lookback, model=model, category=category)), 200
    except Exception:
        logger.exception("[ct] task-stats 산출 실패")
        return jsonify({"error": "INTERNAL_ERROR", "message": "CT 표준 산출 실패"}), 500
