"""협력사 규율 종합 대시보드 — admin/manager endpoint (#87 Sprint 89-BE, Phase 1).

VIEW PartnerDashboardPage 실데이터 공급. read-only.

권한: `@jwt_required + @manager_or_admin_required` + `resolve_company_scope(worker)`.
  - admin / GST          → 전체 협력사 (is_global)
  - 협력사 매니저(company) → 자사 한정 (self scope)
  - company 없는 매니저 / None → CompanyScopeError → 403 (#86 누수 차단)

네임스페이스 `/api/admin/discipline/*` (admin 통일 — #86 A′ 정합).
"""
import logging
import re
from datetime import datetime

from flask import Blueprint, jsonify, request

from app.middleware.jwt_auth import (
    get_current_worker,
    jwt_required,
    manager_or_admin_required,
    resolve_company_scope,
)
from app.services.partner_discipline_service import (
    KST,
    build_discipline_summary,
    build_open_tasks,
    build_trend,
)

logger = logging.getLogger(__name__)

admin_discipline_bp = Blueprint(
    "admin_discipline", __name__, url_prefix="/api/admin/discipline"
)

_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


def _resolve_month(raw: str) -> str:
    """`YYYY-MM` 검증. 빈값 → 현재 KST 월. 잘못된 형식 → ValueError."""
    raw = (raw or "").strip()
    if not raw:
        now = datetime.now(KST)
        return f"{now.year:04d}-{now.month:02d}"
    if not _MONTH_RE.match(raw) or not (1 <= int(raw[5:7]) <= 12):
        raise ValueError(raw)
    return raw


@admin_discipline_bp.route("/summary", methods=["GET"])
@jwt_required
@manager_or_admin_required
def get_discipline_summary():
    """월 협력사 규율 요약 — partner×group row + 지표 envelope + group_avg."""
    try:
        month = _resolve_month(request.args.get("month", ""))
    except ValueError:
        return jsonify({
            "error": "INVALID_MONTH",
            "message": "month 는 YYYY-MM 형식이어야 합니다.",
        }), 400

    worker = get_current_worker()
    if not worker:
        return jsonify({"error": "UNAUTHORIZED", "message": "인증이 필요합니다."}), 401

    # #86: 협력사 스코프 강제 — 반드시 try 밖 (except Exception 이 삼키면 errorhandler 우회).
    scope = resolve_company_scope(worker)

    try:
        response = build_discipline_summary(month, scope)
    except Exception as exc:
        logger.exception("[Sprint89] discipline summary failed: %s", exc)
        return jsonify({
            "error": "INTERNAL_ERROR",
            "message": "협력사 규율 요약 조회 실패",
        }), 500

    return jsonify(response), 200


@admin_discipline_bp.route("/open-tasks", methods=["GET"])
@jwt_required
@manager_or_admin_required
def get_discipline_open_tasks():
    """미종료 즉시조치 큐 (실시간) — manager=자사 worker 실명만, repeat 플래그."""
    worker = get_current_worker()
    if not worker:
        return jsonify({"error": "UNAUTHORIZED", "message": "인증이 필요합니다."}), 401

    scope = resolve_company_scope(worker)  # try 밖

    try:
        response = build_open_tasks(scope)
    except Exception as exc:
        logger.exception("[Sprint89] discipline open-tasks failed: %s", exc)
        return jsonify({
            "error": "INTERNAL_ERROR",
            "message": "미종료 작업 큐 조회 실패",
        }), 500

    return jsonify(response), 200


@admin_discipline_bp.route("/trend", methods=["GET"])
@jwt_required
@manager_or_admin_required
def get_discipline_trend():
    """월별 규율 추이 (Phase 2a) — autoClose/taggingRate/zeroTap. openTasks 제외."""
    raw = request.args.get("months", "6").strip()
    try:
        months = int(raw)
    except ValueError:
        return jsonify({
            "error": "INVALID_MONTHS",
            "message": "months 는 1~12 정수여야 합니다.",
        }), 400
    if months < 1 or months > 12:
        return jsonify({
            "error": "INVALID_MONTHS",
            "message": "months 는 1~12 범위여야 합니다.",
        }), 400

    worker = get_current_worker()
    if not worker:
        return jsonify({"error": "UNAUTHORIZED", "message": "인증이 필요합니다."}), 401

    scope = resolve_company_scope(worker)  # try 밖

    try:
        response = build_trend(months, scope)
    except Exception as exc:
        logger.exception("[Sprint89] discipline trend failed: %s", exc)
        return jsonify({
            "error": "INTERNAL_ERROR",
            "message": "규율 추이 조회 실패",
        }), 500

    return jsonify(response), 200
