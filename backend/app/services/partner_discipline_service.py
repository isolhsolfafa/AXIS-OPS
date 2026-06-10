"""
협력사 규율 종합 대시보드 — 집계 서비스 (#87 Sprint 89-BE, Phase 1).

VIEW PartnerDashboardPage(협력사 규율 공유) 실데이터. read-only, migration 0.

공정성(게이밍 방지, #83 Codex 정합):
- MECH/ELEC 협력사만 (PI/QI/SI = GST 자체공정 제외).
- 평가 = 그룹평균 대비 상대값. BE는 raw + group_avg(peer-only)만, 등급/composite 미산출(VIEW).
- group_avg = 같은 group 내 **타사** 평균, peer_n>=3 충족 시만 (소표본 역추론 차단).
- 협력사 매니저 = 자사 raw만 / by_partner·타사 raw = admin/GST 전용.
- 추적율<70% → grade_eligible=false. 미태깅=데이터누락(작업부재 아님) 라벨.

Phase 1: openTasks / autoClose (재사용) + envelope + RBAC + group_avg + open-tasks 큐.
Phase 2(placeholder): taggingRate / checkinNoTag / zeroTap / checklist + trend.

⚠️ 근태 평가 제외 (2026-06-10 Twin파파 결정): 출근율(attendance)·퇴근미체크(checkoutMiss)는
   협력사 평가 지표로 사용하지 않음 (줄세우기 방지). 출근 데이터는 Phase 2 taggingRate/
   checkinNoTag 의 분모로만 사용. #86 checkout_status 는 근태 페이지 전용으로 유지.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone, date
from typing import Any, Dict, List, Optional, Tuple

from app.models.worker import get_db_connection, put_conn

KST = timezone(timedelta(hours=9))

_TRACKING_THRESHOLD = 0.70
_MIN_PEERS = 3                  # group_avg 노출 최소 peer 수 (소표본 역추론 차단, A7)
_REPEAT_WINDOW_DAYS = 30        # open-tasks repeat 판정 윈도우 (라운드2 #3)
_REPEAT_MIN_COUNT = 2           # repeat 판정 최소 누적 미종료 횟수
_PHASE2_METRICS = ('taggingRate', 'checkinNoTag', 'zeroTap', 'checklist')

# partner_display 정규화 (v2.20.11 _COMPANY_SQL 정합) — MECH/ELEC 만. group = category.
#   MECH: mech_partner ('TMS'→TMS(M)) / ELEC: elec_partner ('TMS'→TMS(E))
#   ⚠️ NULLIF(TRIM(...), '') 래핑 (Codex 라운드3 M-6): NULL/빈문자열/공백 partner 를
#      단일 IS NOT NULL 조건으로 일괄 제외 → SELECT·WHERE·GROUP BY·company_filter 전부 정합
#      (A-spec 4 = partner_display 미지정 제외, raw·peer_n 모집단 일치 보장).
_PARTNER_SQL = (
    "NULLIF(TRIM(CASE "
    "WHEN t.task_category = 'MECH' THEN CASE WHEN pi.mech_partner = 'TMS' THEN 'TMS(M)' ELSE pi.mech_partner END "
    "WHEN t.task_category = 'ELEC' THEN CASE WHEN pi.elec_partner = 'TMS' THEN 'TMS(E)' ELSE pi.elec_partner END "
    "ELSE NULL END), '')"
)

_METRIC_LABEL = {
    'openTasks': '미종료', 'autoClose': '자동마감', 'zeroTap': '0초탭%',
    'taggingRate': '태깅율%', 'checkinNoTag': '출근O·미체크', 'attendance': '출근율%',
    'checkoutMiss': '퇴근미체크%', 'checklist': '체크리스트완료%',
}
_METRIC_NOTE = {
    'taggingRate': '미태깅 = 데이터 누락(작업 부재 아님)',
    'checkinNoTag': '출근O·미체크 = 앱 태깅 미정착 신호(근태 불량 아님)',
    'zeroTap': '0초탭 = 미추적(정상 즉시완료 제외)',
}
# 낮을수록 좋음(true) / 높을수록 좋음(false=taggingRate, attendance)
_LOWER_BETTER = {
    'openTasks': True, 'autoClose': True, 'zeroTap': True, 'taggingRate': False,
    'checkinNoTag': True, 'attendance': False, 'checkoutMiss': True, 'checklist': False,
}


def _month_range_kst(month: str) -> Tuple[datetime, datetime, date, date]:
    """'YYYY-MM' → (start_kst, end_kst tstz, first_date, last_date)."""
    y, m = int(month[:4]), int(month[5:7])
    first = date(y, m, 1)
    last = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)  # exclusive
    start = datetime(first.year, first.month, first.day, tzinfo=KST)
    end = datetime(last.year, last.month, last.day, tzinfo=KST)
    return start, end, first, last


def _envelope(
    metric: str, raw: Optional[float], *, available: bool, phase: str,
    group_avg: Optional[float] = None, peer_n: Optional[int] = None,
    tracking_coverage: Optional[float] = None, suppressed_reason: Optional[str] = None,
    sample_n: Optional[int] = None,
) -> Dict[str, Any]:
    """지표 1개 표준 envelope (공정성 계약 강제, A1)."""
    grade_eligible = available and raw is not None
    ineligibility_reason: Optional[str] = None
    if available and tracking_coverage is not None and tracking_coverage < _TRACKING_THRESHOLD:
        grade_eligible = False
        ineligibility_reason = 'tracking_below_70'
    return {
        'metric': metric,
        'raw': raw,
        'group_avg': group_avg,
        'peer_n': peer_n,
        'tracking_coverage': tracking_coverage,
        'grade_eligible': grade_eligible,
        'ineligibility_reason': ineligibility_reason,
        'suppressed_reason': suppressed_reason,
        'sample_n': sample_n,
        'available': available,
        'phase': phase,
        'label': _METRIC_LABEL.get(metric, metric),
        'label_note': _METRIC_NOTE.get(metric),
        'lower_better': _LOWER_BETTER.get(metric),
    }


# ---------------------------------------------------------------------------
# Phase 1 raw 집계 (partner_display × group) — MECH/ELEC only, 미지정 제외
# ---------------------------------------------------------------------------

def _query_open_tasks_count(cur, company_filter: Optional[str]) -> Dict[Tuple[str, str], int]:
    """미종료(started·미완) task 수 — partner×group. 실시간(현재 열린 것)."""
    sql = f"""
        SELECT {_PARTNER_SQL} AS partner, t.task_category AS grp, COUNT(*) AS n
        FROM app_task_details t
        JOIN plan.product_info pi ON pi.serial_number = t.serial_number
        WHERE t.task_category IN ('MECH','ELEC')
          AND t.started_at IS NOT NULL AND t.completed_at IS NULL
          AND {_PARTNER_SQL} IS NOT NULL
    """
    params: List[Any] = []
    if company_filter:
        sql += f" AND {_PARTNER_SQL} = %s"
        params.append(company_filter)
    sql += f" GROUP BY {_PARTNER_SQL}, t.task_category"
    cur.execute(sql, params)
    return {(r['partner'], r['grp']): r['n'] for r in cur.fetchall()}


def _query_auto_close_count(cur, start, end, company_filter: Optional[str]) -> Dict[Tuple[str, str], int]:
    """월 자동마감(close_reason LIKE 'AUTO_CLOSED%') 수 — partner×group."""
    sql = f"""
        SELECT {_PARTNER_SQL} AS partner, t.task_category AS grp, COUNT(*) AS n
        FROM app_task_details t
        JOIN plan.product_info pi ON pi.serial_number = t.serial_number
        WHERE t.task_category IN ('MECH','ELEC')
          AND t.close_reason LIKE 'AUTO_CLOSED%%'
          AND t.completed_at >= %s AND t.completed_at < %s
          AND {_PARTNER_SQL} IS NOT NULL
    """
    params: List[Any] = [start, end]
    if company_filter:
        sql += f" AND {_PARTNER_SQL} = %s"
        params.append(company_filter)
    sql += f" GROUP BY {_PARTNER_SQL}, t.task_category"
    cur.execute(sql, params)
    return {(r['partner'], r['grp']): r['n'] for r in cur.fetchall()}


def _query_partner_groups(cur) -> List[Tuple[str, str]]:
    """대상 partner×group 목록 (MECH/ELEC, 미지정 제외) — app_task_details 기준."""
    sql = f"""
        SELECT DISTINCT {_PARTNER_SQL} AS partner, t.task_category AS grp
        FROM app_task_details t
        JOIN plan.product_info pi ON pi.serial_number = t.serial_number
        WHERE t.task_category IN ('MECH','ELEC') AND {_PARTNER_SQL} IS NOT NULL
        ORDER BY 2, 1
    """
    cur.execute(sql)
    return [(r['partner'], r['grp']) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# group_avg (peer-only, k>=3) — A7 / 라운드2 #1
# ---------------------------------------------------------------------------

def _group_avg(
    counts: Dict[Tuple[str, str], int], grp: str,
    all_groups: List[Tuple[str, str]], scope,
) -> Tuple[Optional[float], int, Optional[str]]:
    """같은 group 내 peer 평균 (자사 제외, peer_n>=3 충족 시만).

    - admin/global: peer = group 내 전체 협력사 (자사 개념 없음). peer_n = 협력사 수.
    - 협력사 매니저: peer = 자사 제외 타사. peer_n = 타사 수.
    미달(peer_n<_MIN_PEERS) → (None, peer_n, 'insufficient_peers') 로 suppress.
    누락 협력사 raw=0 (정상 운영 = 미종료/자동마감 0건) 으로 분모 포함.
    """
    partners = [p for (p, g) in all_groups if g == grp]
    raw_by_partner = {p: float(counts.get((p, grp), 0)) for p in partners}
    if scope.is_global:
        vals = list(raw_by_partner.values())
    else:
        vals = [v for p, v in raw_by_partner.items() if p != scope.company]
    peer_n = len(vals)
    if peer_n < _MIN_PEERS:
        return None, peer_n, 'insufficient_peers'
    return round(sum(vals) / peer_n, 2), peer_n, None


# ---------------------------------------------------------------------------
# summary endpoint builder — Phase 1 (openTasks + autoClose 실측, 나머지 placeholder)
# ---------------------------------------------------------------------------

def build_discipline_summary(month: str, scope) -> Dict[str, Any]:
    """월 협력사 규율 요약 — partner×group row + 지표 envelope.

    scope.is_global=True(admin/GST): 전체 partner row + group_avg(전체 평균).
    scope.is_global=False(협력사 매니저): 자사 row만 + group_avg(타사 평균, 현 3사 → suppress).
    """
    start, end, _first, _last = _month_range_kst(month)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            all_groups = _query_partner_groups(cur)            # 전체 partner×group (group_avg 분모)
            open_counts = _query_open_tasks_count(cur, None)   # 전체 (자사 노출은 row 필터로)
            auto_counts = _query_auto_close_count(cur, start, end, None)
    finally:
        put_conn(conn)

    # 노출 대상 row: admin=전체 / manager=자사만
    target = [
        (p, g) for (p, g) in all_groups
        if scope.is_global or p == scope.company
    ]

    rows: List[Dict[str, Any]] = []
    for partner, grp in target:
        metrics: Dict[str, Any] = {}

        raw_open = float(open_counts.get((partner, grp), 0))
        ga, pn, sr = _group_avg(open_counts, grp, all_groups, scope)
        metrics['openTasks'] = _envelope(
            'openTasks', raw_open, available=True, phase='phase1',
            group_avg=ga, peer_n=pn, suppressed_reason=sr, sample_n=int(raw_open),
        )

        raw_auto = float(auto_counts.get((partner, grp), 0))
        ga2, pn2, sr2 = _group_avg(auto_counts, grp, all_groups, scope)
        metrics['autoClose'] = _envelope(
            'autoClose', raw_auto, available=True, phase='phase1',
            group_avg=ga2, peer_n=pn2, suppressed_reason=sr2, sample_n=int(raw_auto),
        )

        # Phase 2 지표 = placeholder (VIEW 오해 차단, A9)
        for m in _PHASE2_METRICS:
            metrics[m] = _envelope(m, None, available=False, phase='phase2')

        rows.append({'partner': partner, 'group': grp, 'metrics': metrics})

    return {
        'month': month,
        'scope': 'global' if scope.is_global else 'self',
        'company': None if scope.is_global else scope.company,
        'rows': rows,
        'meta': {
            'phase1_metrics': ['openTasks', 'autoClose'],
            'phase2_pending': list(_PHASE2_METRICS),
            'min_peers': _MIN_PEERS,
            'groups_present': sorted({g for _, g in target}),
            'window': {'month': month, 'start': start.isoformat(), 'end': end.isoformat()},
            'generated_at': datetime.now(KST).isoformat(),
            'fairness_note': (
                'BE는 raw + group_avg(peer-only, k>=3)만 제공. 등급·줄세우기 = VIEW. '
                '근태(출근율·퇴근미체크)는 협력사 평가 지표에서 제외.'
            ),
        },
    }


# ---------------------------------------------------------------------------
# open-tasks endpoint builder — 미종료 즉시조치 큐 (실시간) + repeat 플래그
# ---------------------------------------------------------------------------

def build_open_tasks(scope) -> Dict[str, Any]:
    """미종료(시작·미완) MECH/ELEC task 큐. manager=자사 worker 실명만, 타사 row 미반환.

    repeat = 최근 _REPEAT_WINDOW_DAYS(30)일 내 동일 worker OR 동일 S/N+task 가
             _REPEAT_MIN_COUNT(2)회+ 미종료 (라운드2 #3).
    """
    company_filter = None if scope.is_global else scope.company
    now = datetime.now(KST)
    window_start = now - timedelta(days=_REPEAT_WINDOW_DAYS)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            queue_sql = f"""
                SELECT t.id, t.serial_number, t.task_id, t.task_name,
                       t.task_category AS grp, t.worker_id, t.started_at,
                       {_PARTNER_SQL} AS partner, w.name AS worker_name
                FROM app_task_details t
                JOIN plan.product_info pi ON pi.serial_number = t.serial_number
                LEFT JOIN workers w ON w.id = t.worker_id
                WHERE t.task_category IN ('MECH','ELEC')
                  AND t.started_at IS NOT NULL AND t.completed_at IS NULL
                  AND {_PARTNER_SQL} IS NOT NULL
            """
            q_params: List[Any] = []
            if company_filter:
                queue_sql += f" AND {_PARTNER_SQL} = %s"
                q_params.append(company_filter)
            queue_sql += " ORDER BY t.started_at ASC"
            cur.execute(queue_sql, q_params)
            queue = cur.fetchall()

            repeat_sql = f"""
                SELECT t.worker_id, t.serial_number, t.task_id
                FROM app_task_details t
                JOIN plan.product_info pi ON pi.serial_number = t.serial_number
                WHERE t.task_category IN ('MECH','ELEC')
                  AND t.started_at IS NOT NULL AND t.completed_at IS NULL
                  AND t.started_at >= %s
                  AND {_PARTNER_SQL} IS NOT NULL
            """
            r_params: List[Any] = [window_start]
            if company_filter:
                repeat_sql += f" AND {_PARTNER_SQL} = %s"
                r_params.append(company_filter)
            cur.execute(repeat_sql, r_params)
            repeat_rows = cur.fetchall()
    finally:
        put_conn(conn)

    worker_open: Dict[int, int] = {}
    sntask_open: Dict[Tuple[str, str], int] = {}
    for r in repeat_rows:
        wid = r['worker_id']
        if wid is not None:
            worker_open[wid] = worker_open.get(wid, 0) + 1
        key = (r['serial_number'], r['task_id'])
        sntask_open[key] = sntask_open.get(key, 0) + 1

    tasks: List[Dict[str, Any]] = []
    repeat_count = 0
    for r in queue:
        wid = r['worker_id']
        key = (r['serial_number'], r['task_id'])
        by_worker = wid is not None and worker_open.get(wid, 0) >= _REPEAT_MIN_COUNT
        by_sntask = sntask_open.get(key, 0) >= _REPEAT_MIN_COUNT
        repeat = bool(by_worker or by_sntask)
        if repeat:
            repeat_count += 1
        started = r['started_at']
        hours_open = round((now - started).total_seconds() / 3600.0, 1) if started else None
        reasons = []
        if by_worker:
            reasons.append('worker')
        if by_sntask:
            reasons.append('sn_task')
        tasks.append({
            'id': r['id'],
            'serial_number': r['serial_number'],
            'task_id': r['task_id'],
            'task_name': r['task_name'],
            'group': r['grp'],
            'partner': r['partner'],
            'worker_id': wid,
            'worker_name': r['worker_name'],
            'started_at': started.isoformat() if started else None,
            'hours_open': hours_open,
            'repeat': repeat,
            'repeat_reason': reasons or None,
        })

    return {
        'scope': 'global' if scope.is_global else 'self',
        'company': None if scope.is_global else scope.company,
        'tasks': tasks,
        'meta': {
            'count': len(tasks),
            'repeat_count': repeat_count,
            'repeat_window_days': _REPEAT_WINDOW_DAYS,
            'repeat_min_count': _REPEAT_MIN_COUNT,
            'generated_at': now.isoformat(),
        },
    }
