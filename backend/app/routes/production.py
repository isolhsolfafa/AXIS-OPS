"""
생산실적 라우트 (Sprint 33)
엔드포인트: /api/admin/production/*
VIEW 생산실적 페이지 전용 — O/N 단위 공정별 progress + 실적확인 처리
"""

import logging
import math
from collections import defaultdict
from datetime import date, timedelta, timezone, datetime
from typing import Tuple, Dict, Any, List, Optional

from flask import Blueprint, request, jsonify, g
from psycopg2 import Error as PsycopgError

from app.middleware.jwt_auth import jwt_required, admin_required, view_access_required
from app.db_pool import get_conn, put_conn

logger = logging.getLogger(__name__)

production_bp = Blueprint("production", __name__, url_prefix="/api/admin/production")


def _get_week_range(year: int, week: int):
    """ISO 주차 → (월요일, 다음주 월요일) 반환"""
    jan4 = date(year, 1, 4)
    start = jan4 - timedelta(days=jan4.isoweekday() - 1) + timedelta(weeks=week - 1)
    return start, start + timedelta(days=7)


def _get_month_range(year: int, month: int):
    """월 → (1일, 다음달 1일)"""
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def _current_iso_week():
    """현재 KST 기준 ISO 주차 반환 (year, week)"""
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst).date()
    return now.isocalendar()[0], now.isocalendar()[1]


def _get_confirm_settings(cur) -> Dict[str, bool]:
    """admin_settings에서 실적확인 관련 설정 조회"""
    cur.execute("""
        SELECT setting_key, setting_value
        FROM admin_settings
        WHERE setting_key LIKE 'confirm_%'
    """)
    settings = {}
    for row in cur.fetchall():
        val = row['setting_value']
        if isinstance(val, str):
            settings[row['setting_key']] = val.lower() in ('true', '1')
        elif isinstance(val, bool):
            settings[row['setting_key']] = val
        else:
            settings[row['setting_key']] = bool(val)
    return settings


def _calc_sn_progress(cur, serial_numbers: List[str]) -> Dict[str, Dict]:
    """S/N 목록에 대해 카테고리별 태스크 진행률 조회"""
    if not serial_numbers:
        return {}

    cur.execute("""
        SELECT serial_number, task_category,
               COUNT(*) AS total,
               COUNT(completed_at) AS completed
        FROM app_task_details
        WHERE serial_number = ANY(%s) AND is_applicable = TRUE
        GROUP BY serial_number, task_category
    """, (serial_numbers,))

    result = {}
    for row in cur.fetchall():
        sn = row['serial_number']
        if sn not in result:
            result[sn] = {}
        cat = row['task_category']
        total = row['total']
        completed = row['completed']
        result[sn][cat] = {
            'total': total,
            'completed': completed,
            'pct': round(completed / total * 100, 1) if total > 0 else 0.0,
        }
    return result


def _is_process_confirmable(
    sns_progress: Dict[str, Dict],
    process_type: str,
    settings: Dict[str, bool],
    proc_key: Optional[str] = None,
    serial_numbers: Optional[List[str]] = None,
) -> bool:
    """O/N 전체 S/N이 해당 공정 100% 완료인지 판정

    Args:
        sns_progress: 전체 S/N progress (여러 O/N 포함 가능)
        process_type: DB task_category (MECH, ELEC, TMS 등)
        settings: confirm_*_enabled 설정값
        proc_key: 시스템 표준 공정키 (TM 등). 없으면 process_type 사용
        serial_numbers: 현재 O/N에 속하는 S/N 목록. 없으면 전체 순회 (하위호환)
    """
    key = f'confirm_{(proc_key or process_type).lower()}_enabled'
    if not settings.get(key, False):
        return False

    # 현재 O/N의 S/N만 필터링하여 판정
    check_sns = serial_numbers or list(sns_progress.keys())
    has_data = False
    for sn in check_sns:
        cat_data = sns_progress.get(sn, {}).get(process_type, {})
        if cat_data.get('total', 0) == 0:
            continue
        has_data = True
        if cat_data.get('completed', 0) < cat_data.get('total', 0):
            return False
    return has_data


def _build_order_item(
    sales_order: str,
    products: List[Dict],
    sns_progress: Dict[str, Dict],
    confirms: Dict[str, Dict],
    settings: Dict[str, bool],
) -> Dict:
    """O/N 단위 응답 아이템 구성"""
    serial_numbers = [p['serial_number'] for p in products]
    model = products[0]['model'] if products else ''
    mech_partner = products[0].get('mech_partner', '')
    elec_partner = products[0].get('elec_partner', '')

    # 공정별 상태
    # DB task_category → API 응답 키 매핑 (TMS→TM: 시스템 표준 통일)
    _CAT_TO_PROC = {'TMS': 'TM'}
    process_types = ['MECH', 'ELEC', 'TMS', 'PI', 'QI', 'SI']
    processes = {}

    for pt in process_types:
        total = 0
        completed = 0
        for sn in serial_numbers:
            cat = sns_progress.get(sn, {}).get(pt, {})
            total += cat.get('total', 0)
            completed += cat.get('completed', 0)

        if total == 0:
            continue

        proc_key = _CAT_TO_PROC.get(pt, pt)
        confirm_key = f"{sales_order}:{proc_key}"
        confirm = confirms.get(confirm_key)

        processes[proc_key] = {
            'total': total,
            'completed': completed,
            'ready': completed,
            'pct': round(completed / total * 100, 1),
            'confirmable': _is_process_confirmable(sns_progress, pt, settings, proc_key, serial_numbers),
            'confirmed': confirm is not None,
            'confirmed_at': confirm['confirmed_at'].isoformat() if confirm and confirm.get('confirmed_at') else None,
            'confirm_id': confirm['id'] if confirm else None,
        }

    # S/N 상세 배열 구성 (FE expand용)
    sns_detail = []
    for p in products:
        sn = p['serial_number']
        sn_prog = {}
        for pt in process_types:
            cat = sns_progress.get(sn, {}).get(pt, {})
            if cat.get('total', 0) > 0:
                sn_prog[_CAT_TO_PROC.get(pt, pt)] = {
                    'total': cat['total'],
                    'done': cat['completed'],
                    'pct': cat.get('pct', 0.0),
                }
        sns_detail.append({
            'serial_number': sn,
            'mech_partner': p.get('mech_partner', ''),
            'elec_partner': p.get('elec_partner', ''),
            'progress': sn_prog,
        })

    # sn_summary: 첫 S/N 표시 (2대 이상이면 "외 N대")
    if len(serial_numbers) == 1:
        sn_summary = serial_numbers[0]
    else:
        sn_summary = f"{serial_numbers[0]} 외 {len(serial_numbers) - 1}대"

    # 전체 진행률
    all_total = sum(p.get('total', 0) for p in processes.values())
    all_completed = sum(p.get('completed', 0) for p in processes.values())

    return {
        'sales_order': sales_order,
        'model': model,
        'mech_partner': mech_partner,
        'elec_partner': elec_partner,
        'sn_count': len(serial_numbers),
        'sn_summary': sn_summary,
        'serial_numbers': serial_numbers,
        'sns': sns_detail,
        'progress_pct': round(all_completed / all_total * 100, 1) if all_total > 0 else 0.0,
        'processes': processes,
    }


# ──────────────────────────────────────────────
# API 엔드포인트
# ──────────────────────────────────────────────

@production_bp.route("/performance", methods=["GET"])
@jwt_required
@view_access_required
def get_performance() -> Tuple[Dict[str, Any], int]:
    """
    생산실적 조회 — O/N 단위 공정별 progress + 실적확인 이력

    Query: week=W10, month=2026-03, view=weekly|monthly
    """
    view = request.args.get('view', 'weekly')
    month_str = request.args.get('month')
    week_str = request.args.get('week')

    kst = timezone(timedelta(hours=9))
    today = datetime.now(kst).date()

    # 날짜 범위 계산
    if view == 'monthly':
        if month_str:
            try:
                parts = month_str.split('-')
                year_val, month_val = int(parts[0]), int(parts[1])
            except (ValueError, IndexError):
                return jsonify({'error': 'INVALID_MONTH', 'message': 'month 형식: YYYY-MM'}), 400
        else:
            year_val, month_val = today.year, today.month
            month_str = f"{year_val}-{month_val:02d}"
        start_date, end_date = _get_month_range(year_val, month_val)
    else:
        if week_str:
            try:
                week_num = int(week_str.replace('W', '').replace('w', ''))
                year_val = int(request.args.get('year', today.year))
            except ValueError:
                return jsonify({'error': 'INVALID_WEEK', 'message': 'week 형식: W10'}), 400
        else:
            year_val, week_num = _current_iso_week()
            week_str = f"W{week_num:02d}"
        start_date, end_date = _get_week_range(year_val, week_num)
        month_str = f"{start_date.year}-{start_date.month:02d}"

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        # 1. 대상 제품 조회 (mech_start 기준)
        cur.execute("""
            SELECT p.sales_order, p.serial_number, p.model,
                   p.mech_partner, p.elec_partner, p.line
            FROM plan.product_info p
            WHERE p.mech_start >= %s AND p.mech_start < %s
            ORDER BY p.sales_order, p.serial_number
        """, (start_date, end_date))
        product_rows = cur.fetchall()

        if not product_rows:
            return jsonify({
                'view': view,
                'week': week_str if view == 'weekly' else None,
                'month': month_str,
                'orders': [],
                'total_orders': 0,
            }), 200

        # O/N 그룹핑
        orders = defaultdict(list)
        for row in product_rows:
            orders[row['sales_order']].append(dict(row))

        serial_numbers = [row['serial_number'] for row in product_rows]

        # 2. S/N별 공정 progress
        sns_progress = _calc_sn_progress(cur, serial_numbers)

        # 3. 실적확인 이력
        order_list = list(orders.keys())
        cur.execute("""
            SELECT id, sales_order, process_type, confirmed_week, confirmed_month,
                   sn_count, confirmed_by, confirmed_at
            FROM plan.production_confirm
            WHERE sales_order = ANY(%s) AND deleted_at IS NULL
        """, (order_list,))
        confirms = {}
        for row in cur.fetchall():
            key = f"{row['sales_order']}:{row['process_type']}"
            confirms[key] = dict(row)

        # 4. 설정
        settings = _get_confirm_settings(cur)

        # 5. 응답 빌드
        order_items = []
        for so, products in orders.items():
            item = _build_order_item(so, products, sns_progress, confirms, settings)
            order_items.append(item)

        order_items.sort(key=lambda x: x['sales_order'])

        return jsonify({
            'view': view,
            'week': week_str if view == 'weekly' else None,
            'month': month_str,
            'orders': order_items,
            'total_orders': len(order_items),
        }), 200

    except PsycopgError as e:
        logger.error(f"production performance error: {e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': '데이터 조회 실패'}), 500
    finally:
        if conn:
            put_conn(conn)


@production_bp.route("/confirm", methods=["POST"])
@jwt_required
@view_access_required
def confirm_production() -> Tuple[Dict[str, Any], int]:
    """
    실적확인 처리 — 조건 재검증 후 INSERT

    Body: { sales_order, process_type, confirmed_week, confirmed_month }
    """
    data = request.get_json()
    if not data or not all(k in data for k in ['sales_order', 'process_type', 'confirmed_week', 'confirmed_month']):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': '필수 필드: sales_order, process_type, confirmed_week, confirmed_month'
        }), 400

    sales_order = data['sales_order']
    process_type = data['process_type'].upper()
    confirmed_week = data['confirmed_week']
    confirmed_month = data['confirmed_month']

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        # 1. 대상 S/N 조회
        cur.execute("""
            SELECT serial_number FROM plan.product_info
            WHERE sales_order = %s
        """, (sales_order,))
        sn_rows = cur.fetchall()
        serial_numbers = [r['serial_number'] for r in sn_rows]

        if not serial_numbers:
            return jsonify({'error': 'NOT_FOUND', 'message': 'O/N에 해당하는 제품이 없습니다.'}), 404

        # 2. confirmable 조건 재검증
        # FE는 시스템 표준 키(TM)를 전송하지만, sns_progress는 DB category(TMS) 기준
        _PROC_TO_CAT = {'TM': 'TMS'}  # _CAT_TO_PROC의 역방향
        db_category = _PROC_TO_CAT.get(process_type, process_type)

        sns_progress = _calc_sn_progress(cur, serial_numbers)
        settings = _get_confirm_settings(cur)

        if not _is_process_confirmable(sns_progress, db_category, settings, proc_key=process_type, serial_numbers=serial_numbers):
            return jsonify({
                'error': 'NOT_CONFIRMABLE',
                'message': f'{process_type} 공정이 아직 완료되지 않은 S/N이 있습니다.',
            }), 400

        # 3. INSERT
        cur.execute("""
            INSERT INTO plan.production_confirm
                (sales_order, process_type, confirmed_week, confirmed_month, sn_count, confirmed_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, confirmed_at
        """, (sales_order, process_type, confirmed_week, confirmed_month, len(serial_numbers), g.worker_id))
        row = cur.fetchone()
        conn.commit()

        logger.info(f"Production confirmed: O/N={sales_order}, {process_type}, {confirmed_week}")

        return jsonify({
            'message': '실적확인 완료',
            'confirm_id': row['id'],
            'confirmed_at': row['confirmed_at'].isoformat(),
        }), 201

    except PsycopgError as e:
        if conn:
            conn.rollback()
        error_msg = str(e)
        if 'unique' in error_msg.lower() or 'duplicate' in error_msg.lower():
            return jsonify({'error': 'ALREADY_CONFIRMED', 'message': '이미 실적확인된 항목입니다.'}), 409
        logger.error(f"production confirm error: {e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': '실적확인 처리 실패'}), 500
    finally:
        if conn:
            put_conn(conn)


@production_bp.route("/confirm/<int:confirm_id>", methods=["DELETE"])
@jwt_required
@admin_required
def cancel_confirm(confirm_id: int) -> Tuple[Dict[str, Any], int]:
    """
    실적확인 취소 — soft delete (이력 보존)
    """
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            UPDATE plan.production_confirm
            SET deleted_at = NOW(), deleted_by = %s
            WHERE id = %s AND deleted_at IS NULL
            RETURNING id, sales_order, process_type
        """, (g.worker_id, confirm_id))
        row = cur.fetchone()
        conn.commit()

        if not row:
            return jsonify({'error': 'NOT_FOUND', 'message': '확인 이력을 찾을 수 없습니다.'}), 404

        logger.info(f"Production confirm cancelled: id={confirm_id}, O/N={row['sales_order']}, {row['process_type']}")

        return jsonify({'message': '실적확인이 취소되었습니다.'}), 200

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"production cancel error: {e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': '취소 처리 실패'}), 500
    finally:
        if conn:
            put_conn(conn)


@production_bp.route("/monthly-summary", methods=["GET"])
@jwt_required
@view_access_required
def get_monthly_summary() -> Tuple[Dict[str, Any], int]:
    """
    월마감 집계 — 주차별 완료/확인 카운트

    Query: month=YYYY-MM
    """
    month_str = request.args.get('month')
    kst = timezone(timedelta(hours=9))
    today = datetime.now(kst).date()

    if month_str:
        try:
            parts = month_str.split('-')
            year_val, month_val = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            return jsonify({'error': 'INVALID_MONTH', 'message': 'month 형식: YYYY-MM'}), 400
    else:
        year_val, month_val = today.year, today.month
        month_str = f"{year_val}-{month_val:02d}"

    start_date, end_date = _get_month_range(year_val, month_val)

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        # 월간 O/N별 S/N 수
        cur.execute("""
            SELECT p.sales_order, COUNT(*) AS sn_count, MAX(p.model) AS model
            FROM plan.product_info p
            WHERE p.mech_start >= %s AND p.mech_start < %s
            GROUP BY p.sales_order
            ORDER BY p.sales_order
        """, (start_date, end_date))
        order_rows = cur.fetchall()

        total_orders = len(order_rows)
        total_sns = sum(r['sn_count'] for r in order_rows)

        # 실적확인 이력 (해당 월)
        cur.execute("""
            SELECT process_type, confirmed_week, COUNT(*) AS confirm_count,
                   SUM(sn_count) AS confirmed_sn_count
            FROM plan.production_confirm
            WHERE confirmed_month = %s AND deleted_at IS NULL
            GROUP BY process_type, confirmed_week
            ORDER BY confirmed_week, process_type
        """, (month_str,))
        confirm_rows = cur.fetchall()

        # 주차별 집계
        weekly = defaultdict(lambda: {'orders': 0, 'sns': 0, 'confirms': {}})
        for row in order_rows:
            # S/N의 mech_start 기준 주차 계산 (이미 월 범위 내)
            # 간단히 O/N 단위로 첫 주차 배정
            pass

        confirms_by_week = defaultdict(dict)
        for row in confirm_rows:
            confirms_by_week[row['confirmed_week']][row['process_type']] = {
                'count': row['confirm_count'],
                'sn_count': row['confirmed_sn_count'],
            }

        return jsonify({
            'month': month_str,
            'total_orders': total_orders,
            'total_sns': total_sns,
            'confirms': dict(confirms_by_week),
            'orders': [
                {
                    'sales_order': r['sales_order'],
                    'sn_count': r['sn_count'],
                    'model': r['model'],
                }
                for r in order_rows
            ],
        }), 200

    except PsycopgError as e:
        logger.error(f"production monthly-summary error: {e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': '데이터 조회 실패'}), 500
    finally:
        if conn:
            put_conn(conn)
