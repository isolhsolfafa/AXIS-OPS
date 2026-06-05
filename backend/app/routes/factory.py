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
    'pi_start', 'qi_start', 'si_start', 'mech_start',
    'finishing_plan_end', 'ship_plan_date', 'actual_ship_date'
}
# monthly-kpi 전용 — 출하 기준 date만 (pi_start 제외)
_ALLOWED_DATE_FIELDS_MONTHLY_KPI = {
    'mech_start', 'finishing_plan_end', 'ship_plan_date', 'actual_ship_date'
}

# v2.20.13 (#78 — #69 확장): 공장 대시보드 TEST 데이터 전역 제외.
# 운영 검증 (2026-05-29): TEST S/N 17건 중 12건이 customer != 'TEST CUSTOMER'
# (SEC 등 실고객사명) → #69 customer 제외만으로는 12건 누락 → serial_number prefix OR 통합.
# 표준 제외 조건 (alias 'p' = plan.product_info). 모든 집계 쿼리 WHERE 에 AND 결합.
# ⚠️ psycopg2 %% 이스케이프 — 'TEST%' 의 % 가 파라미터 플레이스홀더로 오인되면
#    tuple index out of range. LIKE 패턴 % → %% (리터럴 % 로 인식).
_TEST_EXCLUDE_SQL = (
    "COALESCE(p.customer, '') <> 'TEST CUSTOMER' AND p.serial_number NOT LIKE 'TEST%%'"
)


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
                 AND (p.actual_ship_date IS NOT NULL OR t.completed_at IS NOT NULL)
                 AND """ + _TEST_EXCLUDE_SQL,
            (start, end)
        )
    elif basis == 'actual':
        cur.execute(
            """SELECT COUNT(*) AS cnt FROM plan.product_info p
               WHERE p.actual_ship_date >= %s AND p.actual_ship_date < %s
                 AND """ + _TEST_EXCLUDE_SQL,
            (start, end)
        )
    elif basis == 'best':
        # v2.4 (2026-04-28) reality 경계 = actual_ship_date / 주간 귀속 = SI_SHIPMENT 우선
        # 해석 A (si ⊆ actual) — 배포 시점 0건 검증 완료.
        #
        # v2.18.4 (#70, 2026-05-21) 엑셀 게이트 제거 — SI 공정 5-19 시행 후 app SI 데이터 유입 시작
        # 기존 의도(설계): "app 출하완료 + 엑셀 actual 중복 제거 합집합" (app 100% 주력)
        # 기존 코드 실제: `WHERE p.actual_ship_date IS NOT NULL` 엑셀 게이트 → app-only 출하 누락
        # 정정: 합집합 OR — COUNT(DISTINCT p.serial_number) 가 중복 자동 제거,
        #       COALESCE(DATE(t.completed_at), p.actual_ship_date) 가 app 우선 날짜 귀속.
        # 영향: 현재 갭 0건 (운영자 동시 입력 중) — 응답값 즉시 변경 0,
        #       SI 정착 후 app-only 출하 발생 시 자동 정확 카운트.
        cur.execute(
            """SELECT COUNT(DISTINCT p.serial_number) AS cnt
               FROM plan.product_info p
               LEFT JOIN app_task_details t
                 ON p.serial_number = t.serial_number
                AND t.task_id       = 'SI_SHIPMENT'
                AND t.completed_at  IS NOT NULL
                AND COALESCE(t.force_closed, FALSE) = FALSE
               WHERE (p.actual_ship_date IS NOT NULL OR t.completed_at IS NOT NULL)
                 AND COALESCE(DATE(t.completed_at), p.actual_ship_date) >= %s
                 AND COALESCE(DATE(t.completed_at), p.actual_ship_date) <  %s
                 AND """ + _TEST_EXCLUDE_SQL,
            (start, end)
        )
    else:
        raise ValueError(f"Invalid basis: {basis} (must be 'plan' | 'actual' | 'best')")
    row = cur.fetchone()
    if row is None:
        return 0
    return row['cnt'] if isinstance(row, dict) else row[0]


# ── Sprint 83 (FEAT-FACTORY-COMPLETION-ROLLUP): 공정별 완료율 ──
# 공장 대시보드(외부 손님 보여주기) 전용. completion_status 플래그 lag 무력화 —
# 실제 task 완료(app_task_details) + 하위완료→상위 cascade rollup 으로 재계산.
# 근본 data 무변경(read-time). 생산현황/실적/S/N 상세뷰는 미적용(정밀 유지).
# tier: 작을수록 앞 공정. 도달한 가장 뒤 tier 보다 앞 공정은 강제 100%(체크리스트 무관).
# 실제 공정 순서 (사용자 확정 2026-06-05): 전장외부 → 반제품(TM) → 기구(MECH) → 전장(ELEC)
#   → 가압(PI) → 공정검사(QI) → 마무리(SI). 반제품이 기구/전장보다 선행 (병렬 아님).
_STAGE_TIER = {'tm': 0, 'mech': 1, 'elec': 2, 'pi': 3, 'qi': 4, 'si': 5}
_CAT_TO_STAGE = {'MECH': 'mech', 'ELEC': 'elec', 'TMS': 'tm',
                 'PI': 'pi', 'QI': 'qi', 'SI': 'si'}
_STAGE_ORDER = ('mech', 'elec', 'tm', 'pi', 'qi', 'si')
# SI 완료 판정 = 출하(SI_SHIPMENT) 제외, 마무리공정(SI_FINISHING) 기준 (사용자 확정 2026-06-05)
_SI_FINISH_TASK_ID = 'SI_FINISHING'


def _compute_stage_completion(cur, serial_numbers: list, model_by_sn: dict) -> dict:
    """Sprint 83 — 실제 task 완료 + cascade rollup 기반 공정별 완료 판정 (read-time, 보여주기).

    근본 data 무변경. 공장 대시보드 전용 (생산현황 백킹 `_get_task_progress_by_serial` 과 별개).
      · 카테고리 완료 = applicable task 전부 completed (SI 는 SI_FINISHING task 기준)
      · 도달 = 카테고리에 완료 task ≥1
      · rollup = 도달한 가장 뒤 tier 보다 앞 공정 전부 True (체크리스트/잔여 task 무관)
      · TM = GAIA 모델만 (non-GAIA None)
      · DUAL(L/R) = task_id 동일 2행이 카테고리 집계에서 합산 → L+R 둘 다 완료여야 완료

    Returns: {sn: {'mech':bool,'elec':bool,'tm':bool|None,'pi':bool,'qi':bool,'si':bool}}
    """
    if not serial_numbers:
        return {}
    cur.execute(
        """SELECT serial_number, task_category, task_id,
                  COUNT(*) FILTER (WHERE is_applicable) AS appl,
                  COUNT(*) FILTER (WHERE is_applicable AND completed_at IS NOT NULL) AS done
           FROM app_task_details
           WHERE serial_number = ANY(%s)
           GROUP BY serial_number, task_category, task_id""",
        (serial_numbers,),
    )
    agg: dict = {}
    for r in cur.fetchall():
        stage = _CAT_TO_STAGE.get(r['task_category'])
        if stage is None:
            continue
        appl = r['appl'] or 0
        done = r['done'] or 0
        c = agg.setdefault(r['serial_number'], {}).setdefault(
            stage, {'appl': 0, 'done': 0, 'si_finish_appl': 0, 'si_finish_done': 0})
        c['appl'] += appl
        c['done'] += done
        if stage == 'si' and r['task_id'] == _SI_FINISH_TASK_ID:
            c['si_finish_appl'] += appl
            c['si_finish_done'] += done

    result: dict = {}
    for sn in serial_numbers:
        cats = agg.get(sn, {})

        done_map: dict = {}
        reached_map: dict = {}
        present_map: dict = {}
        for stage in _STAGE_ORDER:
            c = cats.get(stage)
            if not c or c['appl'] == 0:
                # 모델에 해당 공정 task 없음(seed 안 됨) → 해당 없음.
                # non-GAIA 의 TM(TMS 미생성) + O3 등 비표준(MECH/ELEC 일부 없음) 자연 처리.
                present_map[stage] = False
                done_map[stage] = False
                reached_map[stage] = False
                continue
            present_map[stage] = True
            reached_map[stage] = c['done'] >= 1
            if stage == 'si':
                done_map[stage] = (c['si_finish_appl'] > 0
                                   and c['si_finish_done'] == c['si_finish_appl'])
            else:
                done_map[stage] = (c['done'] == c['appl'])

        furthest = -1
        for stage, reached in reached_map.items():
            if reached:
                furthest = max(furthest, _STAGE_TIER[stage])

        final: dict = {}
        for stage in _STAGE_ORDER:
            if not present_map[stage]:
                final[stage] = None  # 해당 없음 (분모/카운트 제외)
                continue
            final[stage] = True if _STAGE_TIER[stage] < furthest else done_map[stage]
        result[sn] = final
    return result


def _progress_from_stages(stages: dict) -> float:
    """공정 완료 dict → 진행률 % (None=해당없음 제외). 기존 _calc_progress 대체."""
    vals = [v for v in stages.values() if v is not None]
    if not vals:
        return 0.0
    return round(sum(1 for v in vals if v) / len(vals) * 100, 1)


# Sprint 84: 1차/2차 마일스톤 (A안, 사용자 확정 2026-06-05)
#   1차 = 전장외부→반제품(TM)→기구(MECH)→전장(ELEC)→가압(PI). 1차완료 = pi.
#   2차 = 공정검사(QI)→마무리(SI). 2차완료 = si(SI_FINISHING).
#   ⚠️ QI 는 app 미입력(검사자동화시스템 별 시스템, 추후 API) → 2차 진행률은 현재 SI binary.
#      QI API 연동 시 _PHASE2_KEYS 에 'qi' 추가 (코드 1줄).
_PHASE1_KEYS = ['tm', 'mech', 'elec', 'pi']
_PHASE2_KEYS = ['si']  # QI 미입력 → SI 기준. QI 연동 시 ['qi','si']


def _phase_pct(stages: dict, keys: list) -> float:
    """지정 공정 키 중 None(해당없음) 제외 완료 비율 %."""
    vals = [stages.get(k) for k in keys]
    vals = [v for v in vals if v is not None]
    if not vals:
        return 0.0
    return round(sum(1 for v in vals if v) / len(vals) * 100, 1)


def _build_phase(sc: dict) -> dict:
    """Sprint 84 — 1차/2차 마일스톤 진행 dict (rollup 기반, 보여주기)."""
    p1_done = bool(sc.get('pi'))
    p2_done = bool(sc.get('si'))
    return {
        'p1_done': p1_done,
        'p2_done': p2_done,
        'p1_pct': _phase_pct(sc, _PHASE1_KEYS),
        'p2_pct': _phase_pct(sc, _PHASE2_KEYS),
        'status': '2차완료' if p2_done else ('2차진행중' if p1_done else '1차진행중'),
    }


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
    date_str = request.args.get('date')  # v2.19.10 (#74 옵션 C) — 단일 일자 fetch (month 무관)
    page = max(1, request.args.get('page', 1, type=int))
    per_page = min(500, max(1, request.args.get('per_page', 50, type=int)))

    # date_field 화이트리스트 검증
    if date_field not in _ALLOWED_DATE_FIELDS:
        return jsonify({
            'error': 'INVALID_DATE_FIELD',
            'message': f'date_field는 {", ".join(sorted(_ALLOWED_DATE_FIELDS))} 중 하나여야 합니다.'
        }), 400

    # v2.19.10 (#74): date parameter 영역 단일 일자 fetch (month 무관, 공정 카드 today 영역)
    from datetime import datetime
    kst = timezone(timedelta(hours=9))
    today = datetime.now(kst).date()

    where_sql = ""
    where_params: tuple = ()
    target_date_val = None

    if date_str:
        # 단일 일자 mode (VIEW Sprint 78 공정 카드 today 영역)
        try:
            target_date_val = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return jsonify({
                'error': 'INVALID_DATE',
                'message': 'date 형식은 YYYY-MM-DD이어야 합니다.'
            }), 400
        where_sql = f"WHERE p.{date_field} = %s AND {_TEST_EXCLUDE_SQL}"
        where_params = (target_date_val,)
        # month_str 영역 catch (응답 호환 — date 영역 month 표시)
        month_str = target_date_val.strftime('%Y-%m')
    else:
        # 기존 — month range mode
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
        where_sql = f"WHERE p.{date_field} >= %s AND p.{date_field} < %s AND {_TEST_EXCLUDE_SQL}"
        where_params = (start_date, end_date)

    offset = (page - 1) * per_page
    conn = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # COUNT 쿼리 (v2.19.10 #74: where_sql/where_params 통합)
        cur.execute(
            f"SELECT COUNT(*) AS cnt FROM plan.product_info p {where_sql}",
            where_params,
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
                {where_sql}
                ORDER BY p.{date_field} DESC
                LIMIT %s OFFSET %s""",
            where_params + (per_page, offset),
        )
        rows = cur.fetchall()

        # by_model 집계 쿼리
        cur.execute(
            f"""SELECT p.model, COUNT(*) AS count
                FROM plan.product_info p
                {where_sql}
                GROUP BY p.model
                ORDER BY count DESC""",
            where_params,
        )
        by_model = [{'model': r['model'], 'count': r['count']} for r in cur.fetchall()]

        # by_customer 집계 쿼리 (#68 — 공장 대시보드 월간 고객사 도넛)
        cur.execute(
            f"""SELECT p.customer, COUNT(*) AS count
                FROM plan.product_info p
                {where_sql}
                GROUP BY p.customer
                ORDER BY count DESC, p.customer ASC""",
            where_params,
        )
        by_customer = [{'customer': r['customer'], 'count': r['count']} for r in cur.fetchall()]

        # Sprint 31B: 태스크 레벨 진행률 조회 (생산현황 백킹 — 정밀, rollup 미적용)
        serial_numbers = [row['serial_number'] for row in rows if row.get('serial_number')]
        task_progress = _get_task_progress_by_serial(cur, serial_numbers)

        # Sprint 83: completion/progress_pct 는 대시보드 보여주기(rollup) — task_progress(정밀)와 별개
        model_by_sn = {row['serial_number']: row.get('model')
                       for row in rows if row.get('serial_number')}
        stage_comp = _compute_stage_completion(cur, serial_numbers, model_by_sn)

        # items 변환
        items = []
        for row in rows:
            sc = stage_comp.get(row.get('serial_number'), {})
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
                    'mech': bool(sc.get('mech')),
                    'elec': bool(sc.get('elec')),
                    'tm': sc.get('tm'),  # 헬퍼가 non-GAIA 는 None 반환
                    'pi': bool(sc.get('pi')),
                    'qi': bool(sc.get('qi')),
                    'si': bool(sc.get('si')),
                },
                'progress_pct': _progress_from_stages(sc),
                # Sprint 84: 1차/2차 마일스톤 (rollup 기반 보여주기, additive)
                'phase': _build_phase(sc),
                'task_progress': task_progress.get(row.get('serial_number'), {
                    'total': 0, 'completed': 0, 'progress_pct': 0.0, 'by_category': {}
                }),
            })

        return jsonify({
            'month': month_str,
            'items': items,
            'by_model': by_model,
            'by_customer': by_customer,
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
               WHERE p.finishing_plan_end >= %s AND p.finishing_plan_end <= %s
                 AND """ + _TEST_EXCLUDE_SQL,
            (week_start, week_end)
        )
        rows = cur.fetchall()

        production_count = len(rows)

        # Sprint 83: 실제 task 완료 + cascade rollup (보여주기). completion_status 플래그 미사용.
        serial_numbers = [r['serial_number'] for r in rows if r.get('serial_number')]
        model_by_sn = {r['serial_number']: r.get('model')
                       for r in rows if r.get('serial_number')}
        stage_comp = _compute_stage_completion(cur, serial_numbers, model_by_sn)

        # completion_rate: 각 S/N의 progress_pct 평균 (rollup 기반)
        if production_count > 0:
            total_progress = sum(
                _progress_from_stages(stage_comp.get(sn, {})) for sn in serial_numbers)
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

        # by_stage 집계 (Sprint 83: rollup 기반 — 플래그 lag 무력화)
        gaia_count = sum(1 for r in rows if (r.get('model') or '').upper().startswith('GAIA'))

        def _stage_pct(key: str) -> float:
            return round(
                sum(1 for sn in serial_numbers if stage_comp.get(sn, {}).get(key))
                / production_count * 100, 1)

        if production_count > 0:
            by_stage = {
                'mech': _stage_pct('mech'),
                'elec': _stage_pct('elec'),
                # tm 은 GAIA 만 해당 → 분모 gaia_count (기존 의미 보존)
                'tm': round(
                    sum(1 for sn in serial_numbers
                        if (model_by_sn.get(sn) or '').upper().startswith('GAIA')
                        and stage_comp.get(sn, {}).get('tm'))
                    / gaia_count * 100, 1
                ) if gaia_count > 0 else 0.0,
                'pi': _stage_pct('pi'),
                'qi': _stage_pct('qi'),
                'si': _stage_pct('si'),
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
        # #69: TEST CUSTOMER 제외 → #78 (v2.20.13): serial_number LIKE 'TEST%' OR 통합
        #   (TEST S/N 17건 중 12건이 customer != 'TEST CUSTOMER' = SEC 등 → customer만으로 누락)
        cur.execute(
            f"SELECT COUNT(*) AS cnt FROM plan.product_info p "
            f"WHERE p.{date_field} >= %s AND p.{date_field} < %s "
            f"AND {_TEST_EXCLUDE_SQL}",
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
