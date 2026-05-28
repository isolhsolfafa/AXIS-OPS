"""
Sprint 71 (FEAT-MANAGER-DASHBOARD-AUTO-CLOSE-20260521) — v3.1 freeze 정합

Manager Dashboard 자동 마감 분석 API 2개:
  GET /api/admin/dashboard/auto-close-summary   — KPI 3 + 분포 7종 + matrix
  GET /api/admin/dashboard/auto-close-details   — drill-down 상세 카드

설계서: AGENT_TEAM_LAUNCH.md § Sprint 71 v3.1
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Optional

from flask import Blueprint, g, jsonify, request

from app.middleware.jwt_auth import (
    get_current_worker,
    jwt_required,
    manager_or_admin_required,
)
from app.services.dashboard_service import (
    InvariantViolationError,
    build_auto_close_details,
    build_auto_close_summary,
)

logger = logging.getLogger(__name__)

admin_dashboard_bp = Blueprint("admin_dashboard", __name__, url_prefix="/api/admin/dashboard")


_VALID_PERIODS_SUMMARY = {"today", "week", "month", "quarter"}
_VALID_PERIODS_DETAILS = {"today", "week", "month"}


def _parse_reference_date(raw: Optional[str]) -> Optional[date]:
    """`YYYY-MM-DD` 영역 date 객체 변환. 잘못된 형식 시 None."""
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


@admin_dashboard_bp.route("/auto-close-summary", methods=["GET"])
@jwt_required
@manager_or_admin_required
def get_auto_close_summary():
    """Sprint 71 — 자동 마감 분석 KPI + 분포 7종 + matrix."""
    period = request.args.get("period", "month").strip()
    if period not in _VALID_PERIODS_SUMMARY:
        return jsonify({
            "error": "INVALID_PERIOD",
            "message": f"period must be one of {sorted(_VALID_PERIODS_SUMMARY)}",
        }), 400

    partner = request.args.get("partner")
    if partner:
        partner = partner.strip() or None

    reference_date = _parse_reference_date(request.args.get("reference_date"))

    worker = get_current_worker()
    if not worker:
        return jsonify({"error": "UNAUTHORIZED", "message": "인증이 필요합니다."}), 401

    is_admin = bool(worker.is_admin)
    worker_company = worker.company

    try:
        response = build_auto_close_summary(
            period=period,
            partner=partner,
            reference_date=reference_date,
            is_admin=is_admin,
            worker_company=worker_company,
        )
    except InvariantViolationError as exc:
        return jsonify({
            "error": "INVARIANT_VIOLATION",
            "message": "데이터 정합 오류",
            "detail": exc.issues,
        }), 500
    except Exception as exc:
        logger.exception("[Sprint71] auto-close-summary failed: %s", exc)
        return jsonify({
            "error": "INTERNAL_ERROR",
            "message": "자동 마감 요약 조회 실패",
        }), 500

    return jsonify(response), 200


@admin_dashboard_bp.route("/auto-close-details", methods=["GET"])
@jwt_required
@manager_or_admin_required
def get_auto_close_details():
    """Sprint 71 — 자동 마감 상세 카드 drill-down (페이지네이션)."""
    period = request.args.get("period", "today").strip()
    if period not in _VALID_PERIODS_DETAILS:
        return jsonify({
            "error": "INVALID_PERIOD",
            "message": f"period must be one of {sorted(_VALID_PERIODS_DETAILS)}",
        }), 400

    partner = request.args.get("partner")
    if partner:
        partner = partner.strip() or None

    trigger_task_id = request.args.get("trigger_task_id")
    if trigger_task_id:
        trigger_task_id = trigger_task_id.strip() or None

    try:
        page = int(request.args.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = int(request.args.get("per_page", 20))
    except (TypeError, ValueError):
        per_page = 20

    reference_date = _parse_reference_date(request.args.get("reference_date"))

    worker = get_current_worker()
    if not worker:
        return jsonify({"error": "UNAUTHORIZED", "message": "인증이 필요합니다."}), 401

    is_admin = bool(worker.is_admin)
    worker_company = worker.company

    try:
        response = build_auto_close_details(
            period=period,
            partner=partner,
            trigger_task_id=trigger_task_id,
            page=page,
            per_page=per_page,
            is_admin=is_admin,
            worker_company=worker_company,
            reference_date=reference_date,
        )
    except Exception as exc:
        logger.exception("[Sprint71] auto-close-details failed: %s", exc)
        return jsonify({
            "error": "INTERNAL_ERROR",
            "message": "자동 마감 상세 조회 실패",
        }), 500

    return jsonify(response), 200
