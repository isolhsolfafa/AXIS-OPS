"""
HR 라우트 — 협력사 출퇴근 관리
엔드포인트: /api/hr/*
Sprint 12: partner_attendance 출퇴근 기록 API
Sprint 17: work_site + product_line 분류 체계 추가
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Tuple, Dict, Any

from flask import Blueprint, request, jsonify

from app.middleware.jwt_auth import jwt_required, get_current_worker_id
from app.models.worker import get_db_connection, get_worker_by_id


logger = logging.getLogger(__name__)

hr_bp = Blueprint("hr", __name__, url_prefix="/api/hr")

# KST = UTC+9
_KST = timezone(timedelta(hours=9))


def _kst_today_range():
    """오늘(KST) 자정 ~ 내일 자정의 UTC 범위 반환"""
    now_kst = datetime.now(_KST)
    today_kst_midnight = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_kst_midnight = today_kst_midnight + timedelta(days=1)
    return today_kst_midnight, tomorrow_kst_midnight


@hr_bp.route("/attendance/check", methods=["POST"])
@jwt_required
def attendance_check() -> Tuple[Dict[str, Any], int]:
    """
    출퇴근 체크인/체크아웃

    협력사(company != 'GST') 작업자만 사용 가능.
    당일 중복 체크인 방지, 체크인 없이 체크아웃 불가.

    Headers:
        Authorization: Bearer {token}

    Request Body:
        {
            "check_type": str,  # 'in' / 'out'
            "note": str,        # optional: 비고
            "work_site": str,   # optional: 'GST' | 'HQ' (default 'GST')
            "product_line": str # optional: 'SCR' | 'CHI' (default 'SCR')
        }

    Response:
        201: {"message": "출근 기록이 저장되었습니다.", "record": {...}}
        400: {"error": "INVALID_CHECK_TYPE|ALREADY_CHECKED_IN|NOT_CHECKED_IN|...", "message": "..."}
        403: {"error": "FORBIDDEN", "message": "협력사 작업자만 사용 가능합니다."}
    """
    data = request.get_json()

    if not data or 'check_type' not in data:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'check_type 필드가 필요합니다.'
        }), 400

    check_type = data.get('check_type', '').strip().lower()
    if check_type not in ('in', 'out'):
        return jsonify({
            'error': 'INVALID_CHECK_TYPE',
            'message': "check_type은 'in' 또는 'out'이어야 합니다."
        }), 400

    note = data.get('note')
    work_site = data.get('work_site', 'GST').strip().upper()
    product_line = data.get('product_line', 'SCR').strip().upper()

    worker_id = get_current_worker_id()

    # 작업자 정보 조회 (company 확인)
    worker = get_worker_by_id(worker_id)
    if not worker:
        return jsonify({
            'error': 'WORKER_NOT_FOUND',
            'message': '작업자 정보를 찾을 수 없습니다.'
        }), 404

    # 협력사 전용 (GST 사내 직원 제외)
    if worker.company == 'GST':
        return jsonify({
            'error': 'FORBIDDEN',
            'message': '협력사 작업자만 출퇴근 기록 기능을 사용할 수 있습니다.'
        }), 403

    today_start, today_end = _kst_today_range()

    try:
        conn = get_db_connection()

        # 당일 출퇴근 기록 조회 (KST 날짜 기준)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, check_type, check_time, work_site, product_line
                FROM hr.partner_attendance
                WHERE worker_id = %s
                  AND check_time >= %s
                  AND check_time < %s
                ORDER BY check_time ASC
            """, (worker_id, today_start, today_end))
            today_records = cur.fetchall()

        # 오늘의 'in' / 'out' 목록
        check_ins = [r for r in today_records if r['check_type'] == 'in']
        check_outs = [r for r in today_records if r['check_type'] == 'out']

        if check_type == 'in':
            # 이미 체크아웃 없이 체크인한 상태이면 중복 방지
            # (마지막 in 이후 out이 없으면 현재 체크인 상태)
            if check_ins and len(check_ins) > len(check_outs):
                conn.close()
                return jsonify({
                    'error': 'ALREADY_CHECKED_IN',
                    'message': '이미 출근 기록이 있습니다.'
                }), 400

            # work_site / product_line 유효성 검사 (출근 시만)
            if work_site not in ('GST', 'HQ'):
                conn.close()
                return jsonify({
                    'error': 'INVALID_WORK_SITE',
                    'message': "work_site는 'GST' 또는 'HQ'이어야 합니다."
                }), 400
            if product_line not in ('SCR', 'CHI'):
                conn.close()
                return jsonify({
                    'error': 'INVALID_PRODUCT_LINE',
                    'message': "product_line은 'SCR' 또는 'CHI'이어야 합니다."
                }), 400

        elif check_type == 'out':
            # 체크인 없이 체크아웃 불가
            if not check_ins or len(check_ins) <= len(check_outs):
                conn.close()
                return jsonify({
                    'error': 'NOT_CHECKED_IN',
                    'message': '출근 기록이 없습니다. 먼저 출근 체크를 해주세요.'
                }), 400

            # 퇴근 시: FE 값 무시, 마지막 IN 레코드에서 work_site/product_line 복사
            last_in = None
            for r in reversed(today_records):
                if r['check_type'] == 'in':
                    last_in = r
                    break
            if last_in:
                work_site = last_in.get('work_site', 'GST')
                product_line = last_in.get('product_line', 'SCR')

        # 출퇴근 기록 삽입
        now_utc = datetime.now(timezone.utc)
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO hr.partner_attendance
                        (worker_id, check_type, check_time, method, note, work_site, product_line)
                    VALUES (%s, %s, %s, 'button', %s, %s, %s)
                    RETURNING id, worker_id, check_type, check_time, method, note, work_site, product_line
                """, (worker_id, check_type, now_utc, note, work_site, product_line))
                record = cur.fetchone()
        conn.close()

    except Exception as e:
        logger.error(f"attendance_check DB error: worker_id={worker_id}, error={e}")
        return jsonify({
            'error': 'INTERNAL_ERROR',
            'message': '출퇴근 기록 중 오류가 발생했습니다.'
        }), 500

    label = '출근' if check_type == 'in' else '퇴근'
    logger.info(f"Attendance {check_type}: worker_id={worker_id}")

    return jsonify({
        'message': f'{label} 기록이 저장되었습니다.',
        'record': {
            'id': record['id'],
            'worker_id': record['worker_id'],
            'check_type': record['check_type'],
            'check_time': record['check_time'].isoformat() if record['check_time'] else None,
            'method': record['method'],
            'note': record['note'],
            'work_site': record['work_site'],
            'product_line': record['product_line'],
        }
    }), 201


@hr_bp.route("/attendance/today", methods=["GET"])
@jwt_required
def attendance_today() -> Tuple[Dict[str, Any], int]:
    """
    오늘(KST 기준) 출퇴근 기록 조회

    Headers:
        Authorization: Bearer {token}

    Response:
        200: {
            "status": "not_checked" | "checked_in" | "checked_out",
            "records": [
                {
                    "id": int,
                    "check_type": "in" | "out",
                    "check_time": str (ISO 8601),
                    "method": str,
                    "note": str | null
                }
            ]
        }
    """
    worker_id = get_current_worker_id()
    today_start, today_end = _kst_today_range()

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, check_type, check_time, method, note, work_site, product_line
                FROM hr.partner_attendance
                WHERE worker_id = %s
                  AND check_time >= %s
                  AND check_time < %s
                ORDER BY check_time ASC
            """, (worker_id, today_start, today_end))
            rows = cur.fetchall()
        conn.close()
    except Exception as e:
        logger.error(f"attendance_today DB error: worker_id={worker_id}, error={e}")
        return jsonify({
            'error': 'INTERNAL_ERROR',
            'message': '출퇴근 기록 조회 중 오류가 발생했습니다.'
        }), 500

    records = [
        {
            'id': r['id'],
            'check_type': r['check_type'],
            'check_time': r['check_time'].isoformat() if r['check_time'] else None,
            'method': r['method'],
            'note': r['note'],
            'work_site': r.get('work_site', 'GST'),
            'product_line': r.get('product_line', 'SCR'),
        }
        for r in rows
    ]

    # 현재 출퇴근 상태 계산
    check_ins = [r for r in rows if r['check_type'] == 'in']
    check_outs = [r for r in rows if r['check_type'] == 'out']

    if not check_ins:
        status = 'not_checked'
    elif len(check_ins) > len(check_outs):
        # 마지막 체크인 이후 체크아웃 없음 → 현재 출근 중
        status = 'checked_in'
    else:
        # 체크인/체크아웃 쌍이 맞음 → 퇴근 완료
        status = 'checked_out'

    return jsonify({
        'status': status,
        'records': records,
    }), 200
