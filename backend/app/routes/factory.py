"""
공장 API 라우트 (Sprint 29)
엔드포인트: /api/admin/factory/*
VIEW 생산일정 + 공장 대시보드 전용

#10 monthly-detail: 월간 생산 현황 상세 (생산일정 페이지 테이블)
#9 weekly-kpi: 주간 공장 KPI (대시보드 카드 + 차트)
"""

import logging
import math
from datetime import date, timedelta
from flask import Blueprint, request, jsonify
from typing import Tuple, Dict, Any, Optional

from app.middleware.jwt_auth import (
    jwt_required,
    gst_or_admin_required,
    view_access_required,
)
from app.models.worker import get_db_connection
from psycopg2 import Error as PsycopgError

logger = logging.getLogger(__name__)

factory_bp = Blueprint("factory", __name__, url_prefix="/api/admin/factory")

# date_field 화이트리스트 (SQL 인젝션 방지)
_ALLOWED_DATE_FIELDS = {'pi_start', 'mech_start'}


def _calc_progress(row: dict) -> float:
    """완료 단계 수 / 해당 단계 수 * 100"""
    is_gaia = (row.get('model') or '').upper().startswith('GAIA')
    stages = ['mech_completed', 'elec_completed', 'pi_completed', 'qi_completed', 'si_completed']
    if is_gaia:
        stages.append('tm_completed')
    completed = sum(1 for s in stages if row.get(s))
    return round(completed / len(stages) * 100, 1)


def _date_to_iso(val) -> Optional[str]:
    """date/datetime → ISO string, None → None"""
    if val is None:
        return None
    if hasattr(val, 'isoformat'):
        return val.isoformat()
    return str(val)


@factory_bp.route("/monthly-detail", methods=["GET"])
@jwt_required
@view_access_required
def get_monthly_detail() -> Tuple[Dict[str, Any], int]:
    """
    월간 생산 현황 상세 (OPS_API_REQUESTS #10)

    Query Parameters:
        month: YYYY-MM (기본: 현재 월)
        date_field: pi_start | mech_start (기본: pi_start)
        page: 페이지 번호 (기본: 1)
        per_page: 페이지당 건수, max 200 (기본: 50)
    """
    # 파라미터 파싱
    month_str = request.args.get('month')
    date_field = request.args.get('date_field', 'pi_start')
    page = max(1, request.args.get('page', 1, type=int))
    per_page = min(200, max(1, request.args.get('per_page', 50, type=int)))

    # date_field 화이트리스트 검증
    if date_field not in _ALLOWED_DATE_FIELDS:
        return jsonify({
            'error': 'INVALID_DATE_FIELD',
            'message': f'date_field는 {", ".join(_ALLOWED_DATE_FIELDS)} 중 하나여야 합니다.'
        }), 400

    # month 파싱
    today = date.today()
    if month_str:
        try:
            parts = month_str.split('-')
            if len(parts) != 2:
                raise ValueError
            year_val = int(parts[0])
            month_val = int(parts[1])
            if month_val < 1 or month_val > 12:
                raise ValueError
            start_date = date(year_val, month_val, 1)
        except (ValueError, IndexError):
            return jsonify({
                'error': 'INVALID_MONTH',
                'message': 'month 형식은 YYYY-MM이어야 합니다.'
            }), 400
    else:
        year_val = today.year
        month_val = today.month
        start_date = date(year_val, month_val, 1)
        month_str = f"{year_val}-{month_val:02d}"

    # end_date 계산 (다음 달 1일)
    if month_val == 12:
        end_date = date(year_val + 1, 1, 1)
    else:
        end_date = date(year_val, month_val + 1, 1)

    offset = (page - 1) * per_page
    conn = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # COUNT 쿼리
        cur.execute(
            f"SELECT COUNT(*) AS cnt FROM plan.product_info p "
            f"WHERE p.{date_field} >= %s AND p.{date_field} < %s",
            (start_date, end_date)
        )
        total = cur.fetchone()['cnt']
        total_pages = math.ceil(total / per_page) if total > 0 else 0

        # 데이터 쿼리
        cur.execute(
            f"""SELECT p.sales_order, p.product_code, p.serial_number, p.model,
                       p.customer, p.line, p.mech_partner, p.elec_partner,
                       p.mech_start, p.mech_end, p.elec_start, p.elec_end,
                       p.pi_start, p.qi_start, p.si_start, p.finishing_plan_end,
                       cs.mech_completed, cs.elec_completed, cs.tm_completed,
                       cs.pi_completed, cs.qi_completed, cs.si_completed
                FROM plan.product_info p
                LEFT JOIN completion_status cs ON p.serial_number = cs.serial_number
                WHERE p.{date_field} >= %s AND p.{date_field} < %s
                ORDER BY p.{date_field} DESC
                LIMIT %s OFFSET %s""",
            (start_date, end_date, per_page, offset)
        )
        rows = cur.fetchall()

        # by_model 집계 쿼리
        cur.execute(
            f"""SELECT p.model, COUNT(*) AS count
                FROM plan.product_info p
                WHERE p.{date_field} >= %s AND p.{date_field} < %s
                GROUP BY p.model
                ORDER BY count DESC""",
            (start_date, end_date)
        )
        by_model = [{'model': r['model'], 'count': r['count']} for r in cur.fetchall()]

        # items 변환
        items = []
        for row in rows:
            is_gaia = (row.get('model') or '').upper().startswith('GAIA')
            items.append({
                'sales_order': row.get('sales_order'),
                'product_code': row.get('product_code'),
                'serial_number': row.get('serial_number'),
                'model': row.get('model'),
                'customer': row.get('customer'),
                'line': row.get('line'),
                'mech_partner': row.get('mech_partner'),
                'elec_partner': row.get('elec_partner'),
                'mech_start': _date_to_iso(row.get('mech_start')),
                'mech_end': _date_to_iso(row.get('mech_end')),
                'elec_start': _date_to_iso(row.get('elec_start')),
                'elec_end': _date_to_iso(row.get('elec_end')),
                'pi_start': _date_to_iso(row.get('pi_start')),
                'qi_start': _date_to_iso(row.get('qi_start')),
                'si_start': _date_to_iso(row.get('si_start')),
                'finishing_plan_end': _date_to_iso(row.get('finishing_plan_end')),
                'completion': {
                    'mech': bool(row.get('mech_completed')),
                    'elec': bool(row.get('elec_completed')),
                    'tm': bool(row.get('tm_completed')) if is_gaia else None,
                    'pi': bool(row.get('pi_completed')),
                    'qi': bool(row.get('qi_completed')),
                    'si': bool(row.get('si_completed')),
                },
                'progress_pct': _calc_progress(row),
            })

        return jsonify({
            'month': month_str,
            'items': items,
            'by_model': by_model,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
        }), 200

    except PsycopgError as e:
        logger.error(f"monthly-detail DB error: {e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': '데이터 조회 실패'}), 500
    finally:
        if conn:
            conn.close()


@factory_bp.route("/weekly-kpi", methods=["GET"])
@jwt_required
@gst_or_admin_required
def get_weekly_kpi() -> Tuple[Dict[str, Any], int]:
    """
    주간 공장 KPI (OPS_API_REQUESTS #9)

    Query Parameters:
        week: ISO week 번호 1~53 (기본: 현재 주)
        year: 연도 (기본: 현재 연도)
    """
    today = date.today()
    year = request.args.get('year', today.year, type=int)
    week = request.args.get('week', today.isocalendar()[1], type=int)

    # 파라미터 검증
    if year < 2020 or year > 2100:
        return jsonify({
            'error': 'INVALID_YEAR',
            'message': 'year는 2020~2100 범위여야 합니다.'
        }), 400

    if week < 1 or week > 53:
        return jsonify({
            'error': 'INVALID_WEEK',
            'message': 'week는 1~53 범위여야 합니다.'
        }), 400

    # ISO week → 날짜 범위 변환
    try:
        week_start = date.fromisocalendar(year, week, 1)  # Monday
        week_end = date.fromisocalendar(year, week, 7)     # Sunday
    except ValueError:
        return jsonify({
            'error': 'INVALID_WEEK',
            'message': f'{year}년에 {week}주차가 존재하지 않습니다.'
        }), 400

    conn = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """SELECT p.serial_number, p.model, p.finishing_plan_end,
                      cs.mech_completed, cs.elec_completed, cs.tm_completed,
                      cs.pi_completed, cs.qi_completed, cs.si_completed
               FROM plan.product_info p
               LEFT JOIN completion_status cs ON p.serial_number = cs.serial_number
               WHERE p.finishing_plan_end >= %s AND p.finishing_plan_end <= %s""",
            (week_start, week_end)
        )
        rows = cur.fetchall()

        production_count = len(rows)

        # completion_rate: 각 S/N의 progress_pct 평균
        if production_count > 0:
            total_progress = sum(_calc_progress(r) for r in rows)
            completion_rate = round(total_progress / production_count, 1)
        else:
            completion_rate = 0.0

        # by_model 집계
        model_counts: Dict[str, int] = {}
        for r in rows:
            m = r.get('model') or 'UNKNOWN'
            model_counts[m] = model_counts.get(m, 0) + 1
        by_model = sorted(
            [{'model': m, 'count': c} for m, c in model_counts.items()],
            key=lambda x: x['count'], reverse=True
        )

        # by_stage 집계
        gaia_count = sum(1 for r in rows if (r.get('model') or '').upper().startswith('GAIA'))
        if production_count > 0:
            by_stage = {
                'mech': round(sum(1 for r in rows if r.get('mech_completed')) / production_count * 100, 1),
                'elec': round(sum(1 for r in rows if r.get('elec_completed')) / production_count * 100, 1),
                'tm': round(
                    sum(1 for r in rows if r.get('tm_completed') and (r.get('model') or '').upper().startswith('GAIA'))
                    / gaia_count * 100, 1
                ) if gaia_count > 0 else 0.0,
                'pi': round(sum(1 for r in rows if r.get('pi_completed')) / production_count * 100, 1),
                'qi': round(sum(1 for r in rows if r.get('qi_completed')) / production_count * 100, 1),
                'si': round(sum(1 for r in rows if r.get('si_completed')) / production_count * 100, 1),
            }
        else:
            by_stage = {'mech': 0.0, 'elec': 0.0, 'tm': 0.0, 'pi': 0.0, 'qi': 0.0, 'si': 0.0}

        # pipeline 집계
        # shipped 판정: finishing_plan_end(출하 예정일) 기반 추정.
        # actual_ship_date(qr_registry)가 더 정확하나 현재 JOIN 범위 밖 — 추후 VIEW 연동 시 검토.
        pipeline = {'pi': 0, 'qi': 0, 'si': 0, 'shipped': 0}
        for r in rows:
            if r.get('pi_completed') and not r.get('qi_completed'):
                pipeline['pi'] += 1
            if r.get('qi_completed') and not r.get('si_completed'):
                pipeline['qi'] += 1
            if r.get('si_completed'):
                fpe = r.get('finishing_plan_end')
                if fpe and fpe > today:
                    pipeline['si'] += 1
                else:
                    pipeline['shipped'] += 1

        return jsonify({
            'week': week,
            'year': year,
            'week_range': {
                'start': week_start.isoformat(),
                'end': week_end.isoformat(),
            },
            'production_count': production_count,
            'completion_rate': completion_rate,
            'by_model': by_model,
            'by_stage': by_stage,
            'pipeline': pipeline,
        }), 200

    except PsycopgError as e:
        logger.error(f"weekly-kpi DB error: {e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': '데이터 조회 실패'}), 500
    finally:
        if conn:
            conn.close()
