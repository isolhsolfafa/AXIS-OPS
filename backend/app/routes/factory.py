"""
공장 API 라우트 (Sprint 29)
엔드포인트: /api/admin/factory/*
VIEW 생산일정 + 공장 대시보드 전용

#10 monthly-detail: 월간 생산 현황 상세 (생산일정 페이지 테이블)
#9 weekly-kpi: 주간 공장 KPI (대시보드 카드 + 차트)
"""

import logging
import math
from datetime import date, timedelta, timezone
from flask import Blueprint, request, jsonify
from typing import Tuple, Dict, Any, Optional

from app.middleware.jwt_auth import (
    jwt_required,
    view_access_required,
)
from app.models.worker import get_db_connection
from psycopg2 import Error as PsycopgError
from app.db_pool import put_conn

logger = logging.getLogger(__name__)

factory_bp = Blueprint("factory", __name__, url_prefix="/api/admin/factory")

# date_field 화이트리스트 (SQL 인젝션 방지)
# Sprint 62-BE v2.2: monthly-detail 전용 — pi_start 포함 5값 (ProductionPlanPage 토글 호환)
_ALLOWED_DATE_FIELDS = {
    'pi_start', 'mech_start', 'finishing_plan_end', 'ship_plan_date', 'actual_ship_date'
}
# monthly-kpi 전용 — 출하 기준 date만 (pi_start 제외)
_ALLOWED_DATE_FIELDS_MONTHLY_KPI = {
    'mech_start', 'finishing_plan_end', 'ship_plan_date', 'actual_ship_date'
}


def _count_shipped(conn, start, end, basis: str) -> int:
    """주간/월간 출하 카운트 3분기 헬퍼 (Sprint 62-BE v2.4 — FIX-FACTORY-KPI-SHIPPED-V2.4-AMENDMENT-20260428).

    basis: 'plan' | 'actual' | 'best'

    3개 소스는 자동 합산되지 않음 — FE 또는 경영 대시보드 레이어에서 비교 분석.
      - plan   : ship_plan_date + (actual_ship_date OR SI_SHIPMENT) (계획 대비 실제 출하)
      - actual : actual_ship_date (Teams 엑셀 수기 → cron, 진실의 source)
      - best   : reality 경계 = actual_ship_date 있는 전체 / 주간 귀속 = si 우선 (해석 A: si ⊆ actual)

    v2.3 → v2.4 변경 근거:
      - shipped_plan 의 cs.si_completed=TRUE AND 조건이 app SI 도입률 ≈0% 환경에서 무효 → OR 로 교정.
      - shipped_ops 폐기 (app SI 100% 도입 후 ops=actual 수렴, 영구 무의미) → shipped_best 신설.
      - task_id 'SI_SHIPMENT' 대문자 (실 DB 값, task_seed.py L115).

    반개구간 [start, end) 사용 — 경계 중복 제거.
    """
    cur = conn.cursor()
    if basis == 'plan':
        # v2.4: si_completed 의존 제거 → actual_ship_date OR SI_SHIPMENT 둘 중 하나라도 있으면 카운트
        cur.execute(
            """SELECT COUNT(DISTINCT p.serial_number) AS cnt
               FROM plan.product_info p
               LEFT JOIN app_task_details t
                 ON p.serial_number = t.serial_number
                AND t.task_id       = 'SI_SHIPMENT'
                AND t.completed_at  IS NOT NULL
                AND COALESCE(t.force_closed, FALSE) = FALSE
               WHERE p.ship_plan_date >= %s AND p.ship_plan_date < %s
                 AND (p.actual_ship_date IS NOT NULL OR t.completed_at IS NOT NULL)""",
            (start, end)
        )
    elif basis == 'actual':
        cur.execute(
            """SELECT COUNT(*) AS cnt FROM plan.product_info
               WHERE actual_ship_date >= %s AND actual_ship_date < %s""",
            (start, end)
        )
    elif basis == 'best':
        # v2.4 신규: reality 경계 = actual_ship_date 있는 전체 / 주간 귀속 = SI_SHIPMENT 우선
        # 해석 A (si ⊆ actual) — Pre-deploy Gate ③ 0건 검증 완료 (2026-04-28).
        cur.execute(
            """SELECT COUNT(DISTINCT p.serial_number) AS cnt
               FROM plan.product_info p
               LEFT JOIN app_task_details t
                 ON p.serial_number = t.serial_number
                AND t.task_id       = 'SI_SHIPMENT'
                AND t.completed_at  IS NOT NULL
                AND COALESCE(t.force_closed, FALSE) = FALSE
               WHERE p.actual_ship_date IS NOT NULL
                 AND COALESCE(DATE(t.completed_at), p.actual_ship_date) >= %s
                 AND COALESCE(DATE(t.completed_at), p.actual_ship_date) <  %s""",
            (start, end)
        )
    else:
        raise ValueError(f"Invalid basis: {basis} (must be 'plan' | 'actual' | 'best')")
    row = cur.fetchone()
    if row is None:
        return 0
    return row['cnt'] if isinstance(row, dict) else row[0]


def _calc_progress(row: dict) -> float:
    """완료 단계 수 / 해당 단계 수 * 100 (공정 단위)"""
    is_gaia = (row.get('model') or '').upper().startswith('GAIA')
    stages = ['mech_completed', 'elec_completed', 'pi_completed', 'qi_completed', 'si_completed']
    if is_gaia:
        stages.append('tm_completed')
    completed = sum(1 for s in stages if row.get(s))
    return round(completed / len(stages) * 100, 1)


def _get_task_progress_by_serial(cur, serial_numbers: list) -> dict:
    """
    serial_number 목록에 대해 카테고리별 태스크 진행률 조회.
    Sprint 31B: OPS 앱처럼 태스크 레벨 진행률 제공.

    Returns:
        {
            'GBWS-6899': {
                'total': 20, 'completed': 5, 'progress_pct': 25.0,
                'by_category': {
                    'MECH': {'total': 7, 'completed': 3, 'pct': 42.9},
                    'ELEC': {'total': 6, 'completed': 0, 'pct': 0.0},
                    ...
                }
            }
        }
    """
    if not serial_numbers:
        return {}

    cur.execute(
        """
        SELECT serial_number, task_category,
               COUNT(*) AS total,
               COUNT(completed_at) AS completed
        FROM app_task_details
        WHERE serial_number = ANY(%s) AND is_applicable = TRUE
        GROUP BY serial_number, task_category
        ORDER BY serial_number, task_category
        """,
        (serial_numbers,)
    )
    rows = cur.fetchall()

    result = {}
    for row in rows:
        sn = row['serial_number']
        if sn not in result:
            result[sn] = {'total': 0, 'completed': 0, 'progress_pct': 0.0, 'by_category': {}}
        cat = row['task_category']
        total = row['total']
        completed = row['completed']
        pct = round(completed / total * 100, 1) if total > 0 else 0.0

        result[sn]['by_category'][cat] = {
            'total': total,
            'completed': completed,
            'pct': pct,
        }
        result[sn]['total'] += total
        result[sn]['completed'] += completed

    # 전체 progress_pct 계산
    for sn, data in result.items():
        if data['total'] > 0:
            data['progress_pct'] = round(data['completed'] / data['total'] * 100, 1)

    return result


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
    per_page = min(500, max(1, request.args.get('per_page', 50, type=int)))

    # date_field 화이트리스트 검증
    if date_field not in _ALLOWED_DATE_FIELDS:
        return jsonify({
            'error': 'INVALID_DATE_FIELD',
            'message': f'date_field는 {", ".join(sorted(_ALLOWED_DATE_FIELDS))} 중 하나여야 합니다.'
        }), 400

    # month 파싱 (KST 기준)
    from datetime import datetime
    kst = timezone(timedelta(hours=9))
    today = datetime.now(kst).date()
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
                       p.pi_start, p.qi_start, p.si_start, p.ship_plan_date,
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

        # Sprint 31B: 태스크 레벨 진행률 조회
        serial_numbers = [row['serial_number'] for row in rows if row.get('serial_number')]
        task_progress = _get_task_progress_by_serial(cur, serial_numbers)

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
                'ship_plan_date': _date_to_iso(row.get('ship_plan_date')),
                'completion': {
                    'mech': bool(row.get('mech_completed')),
                    'elec': bool(row.get('elec_completed')),
                    'tm': bool(row.get('tm_completed')) if is_gaia else None,
                    'pi': bool(row.get('pi_completed')),
                    'qi': bool(row.get('qi_completed')),
                    'si': bool(row.get('si_completed')),
                },
                'progress_pct': _calc_progress(row),
                'task_progress': task_progress.get(row.get('serial_number'), {
                    'total': 0, 'completed': 0, 'progress_pct': 0.0, 'by_category': {}
                }),
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
            put_conn(conn)


@factory_bp.route("/weekly-kpi", methods=["GET"])
@jwt_required
@view_access_required
def get_weekly_kpi() -> Tuple[Dict[str, Any], int]:
    """
    주간 공장 KPI (OPS_API_REQUESTS #9)

    Query Parameters:
        week: ISO week 번호 1~53 (기본: 현재 주)
        year: 연도 (기본: 현재 연도)
    """
    # KST 기준 오늘 (Railway 서버는 UTC → KST 변환 필요)
    from datetime import datetime
    kst = timezone(timedelta(hours=9))
    today = datetime.now(kst).date()
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

        # v2.10.1 교정 (VIEW 요청 2026-04-23): 주간 생산량은 완료 기준 — ship_plan_date(출하계획일)
        # → finishing_plan_end(마무리계획일) 로 교정. 라벨 [Planned Finish] 와 의미 일치.
        # 숫자 변동 예상: ~50-70% 증가 (ship_plan_date 는 출하 시점이라 주간 생산 완료 수를 저평가했음)
        cur.execute(
            """SELECT p.serial_number, p.model, p.ship_plan_date,
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
        # shipped 판정: ship_plan_date(출하 예정일) 기준 — 주간 생산량 관리 기준일.
        # ⚠️ pipeline.shipped는 `today` 제한 있음 (deprecated, backward compat 유지).
        # ⚠️ shipped_plan (아래 _count_shipped 'plan' basis)은 today 제한 없음 — 의미 다름.
        pipeline = {'pi': 0, 'qi': 0, 'si': 0, 'shipped': 0}
        for r in rows:
            if r.get('pi_completed') and not r.get('qi_completed'):
                pipeline['pi'] += 1
            if r.get('qi_completed') and not r.get('si_completed'):
                pipeline['qi'] += 1
            if r.get('si_completed'):
                spd = r.get('ship_plan_date')
                if spd and spd > today:
                    pipeline['si'] += 1
                else:
                    pipeline['shipped'] += 1

        # Sprint 62-BE v2.2: shipped 3필드 (plan/actual/ops) + defect_count placeholder
        # 반개구간 [start, end) 사용 — week_end(일요일) + 1일 = 다음 월요일이 exclusive end
        week_end_exclusive = week_end + timedelta(days=1)
        shipped_plan = _count_shipped(conn, week_start, week_end_exclusive, 'plan')
        shipped_actual = _count_shipped(conn, week_start, week_end_exclusive, 'actual')
        shipped_best = _count_shipped(conn, week_start, week_end_exclusive, 'best')

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
            'shipped_plan': shipped_plan,
            'shipped_actual': shipped_actual,
            'shipped_best': shipped_best,
            'defect_count': None,
        }), 200

    except PsycopgError as e:
        logger.error(f"weekly-kpi DB error: {e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': '데이터 조회 실패'}), 500
    finally:
        if conn:
            put_conn(conn)


@factory_bp.route("/monthly-kpi", methods=["GET"])
@jwt_required
@view_access_required
def get_monthly_kpi() -> Tuple[Dict[str, Any], int]:
    """월간 공장 KPI (Sprint 62-BE v2.2 신설)

    Query Parameters:
        month: YYYY-MM (기본: 현재 월, KST)
        date_field: mech_start | finishing_plan_end | ship_plan_date | actual_ship_date
                    (기본: mech_start) — pi_start 불허 (monthly-detail 전용)
    """
    month_str = request.args.get('month')
    date_field = request.args.get('date_field', 'mech_start')

    # Codex 2차 Q4 M 반영: monthly-kpi 전용 화이트리스트 (pi_start 제외)
    if date_field not in _ALLOWED_DATE_FIELDS_MONTHLY_KPI:
        return jsonify({
            'error': 'INVALID_DATE_FIELD',
            'message': f'date_field는 {", ".join(sorted(_ALLOWED_DATE_FIELDS_MONTHLY_KPI))} 중 하나여야 합니다.'
        }), 400

    # month 파싱 (KST 기준)
    from datetime import datetime
    kst = timezone(timedelta(hours=9))
    today = datetime.now(kst).date()
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

    # end_date 계산 (다음 달 1일, 반개구간 [start, end))
    if month_val == 12:
        end_date = date(year_val + 1, 1, 1)
    else:
        end_date = date(year_val, month_val + 1, 1)

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # production_count: date_field 기준 COUNT (화이트리스트 검증 완료, f-string 안전)
        cur.execute(
            f"SELECT COUNT(*) AS cnt FROM plan.product_info p "
            f"WHERE p.{date_field} >= %s AND p.{date_field} < %s",
            (start_date, end_date)
        )
        row = cur.fetchone()
        production_count = row['cnt'] if isinstance(row, dict) else row[0]

        # shipped 3필드 (plan/actual/ops)
        shipped_plan = _count_shipped(conn, start_date, end_date, 'plan')
        shipped_actual = _count_shipped(conn, start_date, end_date, 'actual')
        shipped_best = _count_shipped(conn, start_date, end_date, 'best')

        return jsonify({
            'month': month_str,
            'month_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),   # [1일, 다음달 1일) — 반개구간 exclusive end
            },
            'date_field_used': date_field,
            'production_count': production_count,
            'shipped_plan': shipped_plan,
            'shipped_actual': shipped_actual,
            'shipped_best': shipped_best,
            'defect_count': None,
        }), 200

    except PsycopgError as e:
        logger.error(f"monthly-kpi DB error: {e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': '데이터 조회 실패'}), 500
    finally:
        if conn:
            put_conn(conn)
