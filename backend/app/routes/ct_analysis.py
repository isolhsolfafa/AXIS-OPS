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
    get_partner_breakdown,
    get_task_ct_stats,
)
from app.services.tagging_coverage_service import get_tagging_coverage
from app.services.close_type_trend_service import get_close_type_trend

logger = logging.getLogger(__name__)

ct_analysis_bp = Blueprint("ct_analysis", __name__, url_prefix="/api/ct")


@ct_analysis_bp.route("/data-quality", methods=["GET"])
@jwt_required
@gst_or_admin_required
def data_quality():
    """① duration_source 분포 + 자동마감 추이 + 교육 전후.

    S-1 정합(VIEW #82): from/to(YYYY-MM, KST 트러스트 윈도우). 미지정=2026-05~현재월.
    """
    from_month = request.args.get("from")
    to_month = request.args.get("to")
    try:
        return jsonify(get_data_quality(from_month=from_month, to_month=to_month)), 200
    except CtParamError as e:
        return jsonify({"error": e.code, "message": e.message}), 400
    except Exception:
        logger.exception("[ct] data-quality 산출 실패")
        return jsonify({"error": "INTERNAL_ERROR", "message": "데이터 신뢰도 산출 실패"}), 500


@ct_analysis_bp.route("/task-stats", methods=["GET"])
@jwt_required
@gst_or_admin_required
def task_stats():
    """② task별 box plot(basis=duration|active|ct) + 카테고리 요약 + meta.

    S-1 (VIEW #82 ⓐ): period 제거 → basis/from/to(YYYY-MM, KST 윈도우).
    S-2 (VIEW #82 ⓑ): basis=ct (진짜 CT=across-worker union) + effective_concurrency_median.
    INVALID_BASIS 검증은 service(get_task_ct_stats) 에서 400 매핑.
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


@ct_analysis_bp.route("/partner-breakdown", methods=["GET"])
@jwt_required
@gst_or_admin_required
def partner_breakdown():
    """#83 — 협력사 × 모델 × task × 구분(dual) CT 분해 집계 (read-only).

    응답 = {rows, rollups: {partner_task, partner_model}, meta}.
      - basis=ct (ct_time_minutes>0) + active median 병기.
      - partner 정규화 = _COMPANY_SQL (TMS(M)/TMS(E)).
      - rollup median = 독립 GROUP BY (raw 합산 금지, M-1).
      - vs_task_standard_ratio = (task, dual) pooled median 기준 (표준 n<5 → null, M-2).
    from/to(YYYY-MM, KST 윈도우, 미지정=2026-05~현재월) + category + model.
    """
    from_month = request.args.get("from")
    to_month = request.args.get("to")
    category = request.args.get("category")
    model = request.args.get("model")
    try:
        return jsonify(get_partner_breakdown(
            from_month=from_month, to_month=to_month,
            category=category, model=model,
        )), 200
    except CtParamError as e:
        return jsonify({"error": e.code, "message": e.message}), 400
    except Exception:
        logger.exception("[ct] partner-breakdown 산출 실패")
        return jsonify({"error": "INTERNAL_ERROR", "message": "협력사 분해 집계 실패"}), 500


@ct_analysis_bp.route("/tagging-coverage", methods=["GET"])
@jwt_required
@gst_or_admin_required
def tagging_coverage():
    """Sprint 90-BE — 공정별 태깅 추적율 + 0초탭 드릴다운 (read-only).

    응답 = {coverage[], well_tracked_pct, zero_tap_tasks{공정:[...]}, meta}.
      - 분모 = 완료+active NOT NULL+applicable+force_closed=FALSE (자동/admin완료=미추적 포함).
      - 3분류 oneClick>zero_tap>tracked (zero_tap = active≤1 OR close_reason 존재).
      - PI/QI/SI partner='GST' 단일. DUAL L/R per-row. share = largest-remainder.
    from/to(YYYY-MM, KST 윈도우, 미지정=2026-05~현재월).
    설계서: AGENT_TEAM_LAUNCH.md § Sprint 90-BE (Codex 4라운드 GO).
    """
    from_month = request.args.get("from")
    to_month = request.args.get("to")
    try:
        return jsonify(get_tagging_coverage(from_month=from_month, to_month=to_month)), 200
    except CtParamError as e:
        return jsonify({"error": e.code, "message": e.message}), 400
    except Exception:
        logger.exception("[ct] tagging-coverage 산출 실패")
        return jsonify({"error": "INTERNAL_ERROR", "message": "태깅 커버리지 산출 실패"}), 500


@ct_analysis_bp.route("/close-type-trend", methods=["GET"])
@jwt_required
@gst_or_admin_required
def close_type_trend():
    """#90 — 협력사×그룹 마감유형 월별 추이 (auto/zerotap/force, 단위=건, read-only).

    VIEW CloseTrendChart [비교] 오버레이용 flat series → VIEW 가 metric/by 피벗.
    partner=MECH/ELEC(TMS(M)/(E)), GST+SH 제외. from/to(YYYY-MM) 기본 [2026-05, 현재월], 빈 달 zero-fill.
    ?partner/?group = 표시 필터. 설계서: AGENT_TEAM_LAUNCH.md § Sprint 90-BE-C.
    """
    from_month = request.args.get("from")
    to_month = request.args.get("to")
    partner = (request.args.get("partner") or "").strip() or None
    group = (request.args.get("group") or "").strip() or None
    bucket = (request.args.get("bucket") or "month").strip().lower()  # #90b: week|month
    try:
        return jsonify(get_close_type_trend(
            from_month=from_month, to_month=to_month, partner=partner, group=group,
            bucket=bucket,
        )), 200
    except CtParamError as e:
        return jsonify({"error": e.code, "message": e.message}), 400
    except Exception:
        logger.exception("[ct] close-type-trend 산출 실패")
        return jsonify({"error": "INTERNAL_ERROR", "message": "마감유형 추이 산출 실패"}), 500
