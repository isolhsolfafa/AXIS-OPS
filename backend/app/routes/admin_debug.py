"""
v2.20.2 — Admin debug endpoints (scheduler 진단 + cron job 강제 실행)

배경: 5-29 07:30 KST 출하 미처리 알림 cron이 fire되지 않은 사건 후속.
Railway 로그에서 다른 cron 4종은 정상 실행 / `alert_shipment_overdue`만 0건.
root cause 즉시 진단 + 운영 중 cron 누락 의심 시 임시 복구 수단.

권한: admin 전용 (관리자 ID 토큰만 허용).
"""
from __future__ import annotations

import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List

from flask import Blueprint, g, jsonify

from app.middleware.jwt_auth import admin_required, jwt_required
from app.services.scheduler_service import get_scheduler

logger = logging.getLogger(__name__)

admin_debug_bp = Blueprint("admin_debug", __name__, url_prefix="/api/admin/debug")


@admin_debug_bp.route("/scheduler", methods=["GET"])
@jwt_required
@admin_required
def list_scheduler_jobs():
    """현재 등록된 cron job 전체 목록 + 다음 실행 시각 반환."""
    sched = get_scheduler()
    if sched is None:
        return jsonify({
            "error": "SCHEDULER_NOT_INITIALIZED",
            "message": "스케줄러 인스턴스가 존재하지 않습니다.",
            "running": False,
            "jobs": [],
        }), 200

    jobs: List[Dict[str, Any]] = []
    try:
        for job in sched.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "trigger": str(job.trigger),
                "next_run_time": (
                    job.next_run_time.isoformat() if job.next_run_time else None
                ),
                "func": f"{job.func.__module__}.{job.func.__name__}" if job.func else None,
                "misfire_grace_time": job.misfire_grace_time,
            })
    except Exception as exc:
        logger.exception("[admin_debug] list jobs failed")
        return jsonify({
            "error": "LIST_JOBS_FAILED",
            "message": str(exc),
        }), 500

    return jsonify({
        "running": sched.running,
        "timezone": str(sched.timezone),
        "job_count": len(jobs),
        "jobs": jobs,
    }), 200


@admin_debug_bp.route("/run-job/<string:job_id>", methods=["POST"])
@jwt_required
@admin_required
def run_job_now(job_id: str):
    """등록된 cron job을 즉시 강제 실행.

    Args:
        job_id: scheduler 에 등록된 job id (예: alert_shipment_overdue)
    """
    sched = get_scheduler()
    if sched is None:
        return jsonify({
            "error": "SCHEDULER_NOT_INITIALIZED",
            "message": "스케줄러 인스턴스가 존재하지 않습니다.",
        }), 500

    job = sched.get_job(job_id)
    if job is None:
        return jsonify({
            "error": "JOB_NOT_FOUND",
            "message": f"job_id={job_id} 가 스케줄러에 등록되어 있지 않습니다.",
            "registered_job_ids": [j.id for j in sched.get_jobs()],
        }), 404

    started_at = datetime.utcnow().isoformat() + "Z"
    logger.warning(
        "[admin_debug] manual run-job: job_id=%s by worker_id=%s",
        job_id, getattr(g, 'worker_id', None),
    )

    try:
        # 동기 실행 (admin 응답 안에서 결과 확인 가능)
        # v2.20.3: cron 함수가 dict 반환하면 응답에 포함 (실제 메일 발송 결과 등)
        job_result = job.func()
        return jsonify({
            "success": True,
            "job_id": job_id,
            "job_name": job.name,
            "started_at": started_at,
            "finished_at": datetime.utcnow().isoformat() + "Z",
            "message": "job 실행 완료 (예외 없이 종료).",
            "job_result": job_result if isinstance(job_result, dict) else None,
        }), 200
    except Exception as exc:
        tb = traceback.format_exc()
        logger.exception("[admin_debug] run-job failed: job_id=%s", job_id)
        return jsonify({
            "success": False,
            "job_id": job_id,
            "error": exc.__class__.__name__,
            "message": str(exc),
            "traceback": tb.splitlines()[-10:],
        }), 500
