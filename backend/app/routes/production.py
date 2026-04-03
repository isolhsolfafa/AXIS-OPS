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


def _weeks_for_month(year: int, month: int) -> List[Tuple[str, date, date]]:
    """해당 월에 포함되는 ISO 주차 목록 반환 (금요일 기준)

    Returns: [("W14", monday, next_monday), ...]
    금요일이 해당 월에 속하는 주차만 포함
    """
    from calendar import monthrange
    _, last_day = monthrange(year, month)
    month_start = date(year, month, 1)
    month_end = date(year, month, last_day)

    weeks = []
    monday = month_start - timedelta(days=month_start.weekday())

    while True:
        friday = monday + timedelta(days=4)
        if friday > month_end:
            break
        if friday.year == year and friday.month == month:
            week_label = f"W{monday.isocalendar()[1]:02d}"
            weeks.append((week_label, monday, monday + timedelta(days=7)))
        monday += timedelta(days=7)
        if monday > month_end + timedelta(days=7):
            break

    return weeks


def _date_to_week_label(d) -> str:
    """date → 'W14' 형식 주차 라벨"""
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return f"W{d.isocalendar()[1]:02d}"


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
    """admin_settings에서 실적확인 + TM 가압검사 설정 조회"""
    cur.execute("""
        SELECT setting_key, setting_value
        FROM admin_settings
        WHERE setting_key LIKE 'confirm_%'
           OR setting_key = 'tm_pressure_test_required'
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
    """S/N 목록에 대해 카테고리별·태스크별 진행률 조회

    Returns:
        {sn: {category: {total, completed, pct, tasks: {task_id: {total, completed}}}}}
        task_id 레벨 데이터는 confirmable 판정, 추후 tm_pressure_test_required
        옵션 등에서 개별 태스크 필터링에 사용.
    """
    if not serial_numbers:
        return {}

    cur.execute("""
        SELECT serial_number, task_category, task_id,
               COUNT(*) AS total,
               COUNT(completed_at) AS completed
        FROM app_task_details
        WHERE serial_number = ANY(%s) AND is_applicable = TRUE
        GROUP BY serial_number, task_category, task_id
    """, (serial_numbers,))

    result = {}
    for row in cur.fetchall():
        sn = row['serial_number']
        if sn not in result:
            result[sn] = {}
        cat = row['task_category']
        task_id = row['task_id']
        total = row['total']
        completed = row['completed']

        if cat not in result[sn]:
            result[sn][cat] = {'total': 0, 'completed': 0, 'tasks': {}}

        result[sn][cat]['total'] += total
        result[sn][cat]['completed'] += completed
        result[sn][cat]['tasks'][task_id] = {
            'total': total,
            'completed': completed,
        }

    # 카테고리 레벨 pct 계산
    for sn_data in result.values():
        for cat_data in sn_data.values():
            t = cat_data['total']
            c = cat_data['completed']
            cat_data['pct'] = round(c / t * 100, 1) if t > 0 else 0.0

    return result


# 실적확인(confirmable) 판정 시 특정 task_id만 체크하는 매핑
# TMS: TANK_MODULE만 (PRESSURE_TEST는 progress/알람 전용, 실적확인 대상 아님)
# 추후 다른 카테고리도 task_id별 분리 필요 시 여기에 추가
_CONFIRM_TASK_FILTER: Dict[str, str] = {
    'TMS': 'TANK_MODULE',
}

# 혼재 판정 대상 공정 → product_info partner 컬럼 매핑 (#37)
# PI/QI/SI는 분리 안 함 (기존 O/N 단위 유지)
_PROC_PARTNER_COL: Dict[str, str] = {
    'MECH': 'mech_partner',
    'ELEC': 'elec_partner',
    # TM 제거 (#38): TMS tasks 유무로 자연 필터링, mech_partner 기준 혼재는 FNI 혼입 버그 유발
}


def _is_process_confirmable(
    sns_progress: Dict[str, Dict],
    process_type: str,
    settings: Dict[str, bool],
    proc_key: Optional[str] = None,
    serial_numbers: Optional[List[str]] = None,
) -> bool:
    """O/N 전체 S/N이 해당 공정의 실적확인 대상 태스크를 100% 완료했는지 판정

    Args:
        sns_progress: {sn: {category: {total, completed, pct, tasks: {task_id: ...}}}}
        process_type: DB task_category (MECH, ELEC, TMS 등)
        settings: confirm_*_enabled 설정값
        proc_key: 시스템 표준 공정키 (TM 등). 없으면 process_type 사용
        serial_numbers: 현재 O/N에 속하는 S/N 목록. 없으면 전체 순회 (하위호환)

    동작:
        _CONFIRM_TASK_FILTER에 등록된 카테고리 → 지정 task_id만 체크
        미등록 카테고리 → 카테고리 전체 체크 (기존 동작)
    """
    key = f'confirm_{(proc_key or process_type).lower()}_enabled'
    if not settings.get(key, False):
        return False

    # 현재 O/N의 S/N만 필터링하여 판정
    check_sns = serial_numbers or list(sns_progress.keys())
    confirm_task = _CONFIRM_TASK_FILTER.get(process_type)

    has_data = False
    for sn in check_sns:
        cat_data = sns_progress.get(sn, {}).get(process_type, {})

        if confirm_task:
            # task_id 레벨 체크 (예: TMS → TANK_MODULE만)
            task_data = cat_data.get('tasks', {}).get(confirm_task, {})
            if task_data.get('total', 0) == 0:
                continue
            has_data = True
            if task_data.get('completed', 0) < task_data.get('total', 0):
                return False
        else:
            # 카테고리 전체 체크 (MECH, ELEC, PI, QI, SI 등)
            if cat_data.get('total', 0) == 0:
                continue
            has_data = True
            if cat_data.get('completed', 0) < cat_data.get('total', 0):
                return False

    return has_data


def _is_sn_process_confirmable(
    sns_progress: Dict[str, Dict],
    process_type: str,
    settings: Dict[str, bool],
    proc_key: str,
    serial_number: str,
) -> bool:
    """단일 S/N의 해당 공정 confirmable 판정"""
    key = f'confirm_{proc_key.lower()}_enabled'
    if not settings.get(key, False):
        return False

    cat_data = sns_progress.get(serial_number, {}).get(process_type, {})
    confirm_task = _CONFIRM_TASK_FILTER.get(process_type)

    if confirm_task:
        task_data = cat_data.get('tasks', {}).get(confirm_task, {})
        if task_data.get('total', 0) == 0:
            return False
        return task_data.get('completed', 0) >= task_data.get('total', 0)
    else:
        if cat_data.get('total', 0) == 0:
            return False
        return cat_data.get('completed', 0) >= cat_data.get('total', 0)


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

    # TMS progress 집계: tm_pressure_test_required=false → TANK_MODULE만 합산
    tm_pt_required = settings.get('tm_pressure_test_required', True)

    for pt in process_types:
        total = 0
        completed = 0
        for sn in serial_numbers:
            cat = sns_progress.get(sn, {}).get(pt, {})
            if pt == 'TMS' and not tm_pt_required:
                tm_task = cat.get('tasks', {}).get('TANK_MODULE', {})
                total += tm_task.get('total', 0)
                completed += tm_task.get('completed', 0)
            else:
                total += cat.get('total', 0)
                completed += cat.get('completed', 0)

        if total == 0:
            continue

        proc_key = _CAT_TO_PROC.get(pt, pt)
        partner_col = _PROC_PARTNER_COL.get(proc_key)

        # 혼재 판정 (MECH/ELEC만 — TM은 #38에서 제거)
        mixed = False
        if partner_col:
            partners = list(set(p.get(partner_col, '') or '' for p in products))
            partners = [p for p in partners if p]
            mixed = len(partners) >= 2

        # S/N별 confirm 조회 헬퍼
        def _sn_confirm(ptnr, sn):
            return confirms.get(f"{sales_order}:{proc_key}:{ptnr or ''}:{sn}")

        # S/N별 progress 계산 헬퍼
        def _sn_progress_vals(sn):
            cat = sns_progress.get(sn, {}).get(pt, {})
            if pt == 'TMS' and not tm_pt_required:
                t = cat.get('tasks', {}).get('TANK_MODULE', {})
                return t.get('total', 0), t.get('completed', 0)
            return cat.get('total', 0), cat.get('completed', 0)

        # PI/QI/SI: 기존 O/N 단위 (sn_confirms 없음)
        if proc_key not in _PROC_PARTNER_COL and proc_key != 'TM':
            confirm_key = f"{sales_order}:{proc_key}::"
            confirm = confirms.get(confirm_key)
            processes[proc_key] = {
                'total': total, 'completed': completed, 'ready': completed,
                'pct': round(completed / total * 100, 1),
                'mixed': False,
                'confirmable': _is_process_confirmable(sns_progress, pt, settings, proc_key, serial_numbers),
                'confirmed': confirm is not None,
                'confirmed_at': confirm['confirmed_at'].isoformat() if confirm and confirm.get('confirmed_at') else None,
                'confirm_id': confirm['id'] if confirm else None,
            }
        elif mixed and partner_col:
            # 혼재 MECH/ELEC: partner → sn_confirms
            partner_confirms_list = []
            for ptnr in sorted(partners):
                ptnr_sns = [p['serial_number'] for p in products if (p.get(partner_col, '') or '') == ptnr]
                sn_confs = []
                for sn in ptnr_sns:
                    sn_t, sn_c = _sn_progress_vals(sn)
                    sc = _sn_confirm(ptnr, sn)
                    sn_confs.append({
                        'serial_number': sn,
                        'total': sn_t, 'completed': sn_c, 'ready': sn_c,
                        'pct': round(sn_c / sn_t * 100, 1) if sn_t > 0 else 0.0,
                        'confirmable': _is_sn_process_confirmable(sns_progress, pt, settings, proc_key, sn),
                        'confirmed': sc is not None,
                        'confirmed_at': sc['confirmed_at'].isoformat() if sc and sc.get('confirmed_at') else None,
                        'confirm_id': sc['id'] if sc else None,
                    })
                partner_confirms_list.append({
                    'partner': ptnr,
                    'sn_confirms': sn_confs,
                    'all_confirmable': all(s['confirmable'] for s in sn_confs),
                    'all_confirmed': all(s['confirmed'] for s in sn_confs),
                })
            processes[proc_key] = {
                'total': total, 'completed': completed, 'ready': completed,
                'pct': round(completed / total * 100, 1),
                'mixed': True,
                'partner_confirms': partner_confirms_list,
            }
        else:
            # 비혼재 MECH/ELEC + TM: sn_confirms 직접
            sn_confs = []
            for sn in serial_numbers:
                sn_t, sn_c = _sn_progress_vals(sn)
                if sn_t == 0:
                    continue
                sc = _sn_confirm('', sn)
                sn_confs.append({
                    'serial_number': sn,
                    'total': sn_t, 'completed': sn_c, 'ready': sn_c,
                    'pct': round(sn_c / sn_t * 100, 1) if sn_t > 0 else 0.0,
                    'confirmable': _is_sn_process_confirmable(sns_progress, pt, settings, proc_key, sn),
                    'confirmed': sc is not None,
                    'confirmed_at': sc['confirmed_at'].isoformat() if sc and sc.get('confirmed_at') else None,
                    'confirm_id': sc['id'] if sc else None,
                })
            processes[proc_key] = {
                'total': total, 'completed': completed, 'ready': completed,
                'pct': round(completed / total * 100, 1),
                'mixed': False,
                'sn_confirms': sn_confs,
                'all_confirmable': all(s['confirmable'] for s in sn_confs) if sn_confs else False,
                'all_confirmed': all(s['confirmed'] for s in sn_confs) if sn_confs else False,
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
            'mech_end': p['mech_end'].isoformat() if p.get('mech_end') else None,
            'elec_end': p['elec_end'].isoformat() if p.get('elec_end') else None,
            'module_end': p['module_end'].isoformat() if p.get('module_end') else None,
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

        # 1. 대상 제품 조회 (공정 종료일 기준 — 해당 기간에 어떤 공정이든 완료되는 O/N)
        # mech_end, elec_end, module_start 중 하나라도 기간 내 → 표시
        cur.execute("""
            SELECT p.sales_order, p.serial_number, p.model,
                   p.mech_partner, p.elec_partner, p.line,
                   p.mech_end, p.elec_end,
                   p.module_start AS module_end
            FROM plan.product_info p
            WHERE (p.mech_end >= %s AND p.mech_end < %s)
               OR (p.elec_end >= %s AND p.elec_end < %s)
               OR (p.module_start >= %s AND p.module_start < %s)
            ORDER BY p.sales_order, p.serial_number
        """, (start_date, end_date, start_date, end_date, start_date, end_date))
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
            SELECT id, sales_order, process_type, partner, serial_number,
                   confirmed_week, confirmed_month, confirmed_by, confirmed_at
            FROM plan.production_confirm
            WHERE sales_order = ANY(%s) AND deleted_at IS NULL
        """, (order_list,))
        confirms = {}
        for row in cur.fetchall():
            r = dict(row)
            ptnr = r.get('partner') or ''
            sn = r.get('serial_number') or ''
            key = f"{r['sales_order']}:{r['process_type']}:{ptnr}:{sn}"
            confirms[key] = r

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
    실적확인 처리 — S/N별 조건 재검증 후 multi-row INSERT

    Body: { sales_order, process_type, serial_numbers: [str], partner?, confirmed_week, confirmed_month }
    """
    data = request.get_json()
    if not data or not all(k in data for k in ['sales_order', 'process_type', 'serial_numbers', 'confirmed_week', 'confirmed_month']):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': '필수 필드: sales_order, process_type, serial_numbers, confirmed_week, confirmed_month'
        }), 400

    sales_order = data['sales_order']
    process_type = data['process_type'].upper()
    serial_numbers_req = data.get('serial_numbers', [])
    confirmed_week = data['confirmed_week']
    confirmed_month = data['confirmed_month']
    partner = data.get('partner')

    if not serial_numbers_req:
        return jsonify({'error': 'INVALID_REQUEST', 'message': 'serial_numbers 필수'}), 400

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        # 1. S/N별 confirmable 검증
        _PROC_TO_CAT = {'TM': 'TMS'}
        db_category = _PROC_TO_CAT.get(process_type, process_type)

        sns_progress = _calc_sn_progress(cur, serial_numbers_req)
        settings = _get_confirm_settings(cur)

        for sn in serial_numbers_req:
            if not _is_sn_process_confirmable(sns_progress, db_category, settings, process_type, sn):
                return jsonify({
                    'error': 'NOT_CONFIRMABLE',
                    'message': f'{sn}: {process_type} 공정 미완료',
                }), 400

        # 2. multi-row INSERT
        values = [(sales_order, process_type, partner, sn,
                    confirmed_week, confirmed_month, g.worker_id)
                   for sn in serial_numbers_req]

        cur.executemany("""
            INSERT INTO plan.production_confirm
                (sales_order, process_type, partner, serial_number,
                 confirmed_week, confirmed_month, confirmed_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, values)

        # 3. 결과 조회 (executemany는 RETURNING 미지원)
        cur.execute("""
            SELECT id, serial_number, confirmed_at
            FROM plan.production_confirm
            WHERE sales_order = %s AND process_type = %s
              AND COALESCE(partner, '') = COALESCE(%s, '')
              AND serial_number = ANY(%s)
              AND deleted_at IS NULL
            ORDER BY serial_number
        """, (sales_order, process_type, partner, serial_numbers_req))
        confirmed_rows = [dict(r) for r in cur.fetchall()]
        conn.commit()

        logger.info(f"Production confirmed: O/N={sales_order}, {process_type}, partner={partner}, sns={serial_numbers_req}")

        return jsonify({
            'message': '실적확인 완료',
            'confirmed': [{
                'id': r['id'],
                'serial_number': r['serial_number'],
                'confirmed_at': r['confirmed_at'].isoformat() if r.get('confirmed_at') else None,
            } for r in confirmed_rows],
            'count': len(serial_numbers_req),
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
            RETURNING id, sales_order, process_type, partner, serial_number
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
                   COUNT(*) AS confirmed_sn_count
            FROM plan.production_confirm
            WHERE confirmed_month = %s AND deleted_at IS NULL
            GROUP BY process_type, confirmed_week
            ORDER BY confirmed_week, process_type
        """, (month_str,))
        confirm_rows = cur.fetchall()

        confirms_by_week = defaultdict(dict)
        for row in confirm_rows:
            confirms_by_week[row['confirmed_week']][row['process_type']] = {
                'count': row['confirm_count'],
                'sn_count': row['confirmed_sn_count'],
            }

        # ── weeks/totals 집계 ──────────────────────────────────────────
        # S/N별 MECH/ELEC/TM 공정 완료 여부 LATERAL JOIN 쿼리
        cur.execute("""
            SELECT p.serial_number, p.mech_end,
                   CASE WHEN mech.total > 0 AND mech.total = mech.done THEN 1 ELSE 0 END AS mech_completed,
                   CASE WHEN elec.total > 0 AND elec.total = elec.done THEN 1 ELSE 0 END AS elec_completed,
                   CASE WHEN tm.total > 0 AND tm.total = tm.done  THEN 1 ELSE 0 END AS tm_completed
            FROM plan.product_info p
            LEFT JOIN LATERAL (
                SELECT COUNT(*) AS total, COUNT(completed_at) AS done
                FROM app_task_details WHERE serial_number = p.serial_number
                AND task_category = 'MECH' AND is_applicable = TRUE
            ) mech ON TRUE
            LEFT JOIN LATERAL (
                SELECT COUNT(*) AS total, COUNT(completed_at) AS done
                FROM app_task_details WHERE serial_number = p.serial_number
                AND task_category = 'ELEC' AND is_applicable = TRUE
            ) elec ON TRUE
            LEFT JOIN LATERAL (
                SELECT COUNT(*) AS total, COUNT(completed_at) AS done
                FROM app_task_details WHERE serial_number = p.serial_number
                AND task_category = 'TMS' AND task_id = 'TANK_MODULE' AND is_applicable = TRUE
            ) tm ON TRUE
            WHERE p.mech_start >= %s AND p.mech_start < %s
        """, (start_date, end_date))
        sn_rows = cur.fetchall()

        # 주차 목록 초기화
        weeks_info = _weeks_for_month(year_val, month_val)
        week_labels = [w[0] for w in weeks_info]

        week_data: Dict[str, Dict] = {}
        for label, _mon, _next_mon in weeks_info:
            week_data[label] = {
                'mech': {'completed': 0, 'confirmed': 0},
                'elec': {'completed': 0, 'confirmed': 0},
                'tm':   {'completed': 0, 'confirmed': 0},
            }

        # S/N별 mech_end 기준 주차 배정 → completed 집계
        for row in sn_rows:
            if not row['mech_end']:
                continue
            sn_week = _date_to_week_label(row['mech_end'])
            if sn_week not in week_data:
                continue
            if row['mech_completed']:
                week_data[sn_week]['mech']['completed'] += 1
            if row['elec_completed']:
                week_data[sn_week]['elec']['completed'] += 1
            if row['tm_completed']:
                week_data[sn_week]['tm']['completed'] += 1

        # confirmed: production_confirm 기록 기준 (confirmed_week 키 매핑)
        for label in week_labels:
            week_confirms = confirms_by_week.get(label, {})
            for proc_type in ('MECH', 'ELEC', 'TM'):
                if proc_type in week_confirms:
                    week_data[label][proc_type.lower()]['confirmed'] = week_confirms[proc_type]['sn_count']

        # totals = weeks 합계
        totals: Dict[str, Dict] = {
            'mech': {'completed': 0, 'confirmed': 0},
            'elec': {'completed': 0, 'confirmed': 0},
            'tm':   {'completed': 0, 'confirmed': 0},
        }
        for wd in week_data.values():
            for proc in ('mech', 'elec', 'tm'):
                totals[proc]['completed'] += wd[proc]['completed']
                totals[proc]['confirmed'] += wd[proc]['confirmed']

        return jsonify({
            'month': month_str,
            'total_orders': total_orders,
            'total_sns': total_sns,
            'weeks': [
                {'week': label, **week_data[label]}
                for label in week_labels
            ],
            'totals': totals,
            'confirms': dict(confirms_by_week),  # 기존 유지
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
