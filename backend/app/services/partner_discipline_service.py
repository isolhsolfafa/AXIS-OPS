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
Phase 2a: taggingRate / zeroTap 실측(평가) + checkoutMiss(퇴근미체크율, 참고) + trend endpoint.
Phase 2b(placeholder): checklist (applicable resolver 추출, 별도 Codex 라운드).

⚠️ 근태 평가 제외 (2026-06-10 Twin파파 결정): 출근율·퇴근미체크는 협력사 **평가** 지표로
   사용하지 않음 (줄세우기 방지). 단 checkoutMiss(퇴근미체크율)는 근태 페이지 동일 기준으로
   **참고(reference_only)** 표시 — 평가/등급/group 줄세우기 미반영. 출근 데이터는 taggingRate 분모로도 사용.
   ⚠️ checkinNoTag(출근O·미태깅)는 taggingRate 와 중복(=onsite−tagged)이라 폐기 → checkoutMiss 로 교체.

Phase 2a 의미론 (Codex 라운드1 판정):
- (A) taggingRate "tagged" = 월 DISTINCT worker (월 1회+ 태깅=tagged). 일 단위 정착률은 보류.
- (B) 분모 gst_onsite = work_site='GST' 출근자만 (HQ-only·월 무출근 제외).
- (C) zeroTap 기준 = active_time_minutes<=1 (#83 미추적 정의 정합, duration=0 아님).
- (D) row universe = task파생(_PARTNER_SQL) ∪ worker파생(workers.company) — 누락 방지 + provenance meta.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone, date
from typing import Any, Dict, List, Optional, Tuple

from app.models.worker import get_db_connection, put_conn
from app.services.statistics_service import is_instant_whitelisted

KST = timezone(timedelta(hours=9))

_TRACKING_THRESHOLD = 0.70
_MIN_PEERS = 3                  # group_avg 노출 최소 peer 수 (소표본 역추론 차단, A7)
_REPEAT_WINDOW_DAYS = 30        # open-tasks repeat 판정 윈도우 (라운드2 #3)
_REPEAT_MIN_COUNT = 2           # repeat 판정 최소 누적 미종료 횟수
_TREND_MAX_MONTHS = 12          # trend endpoint 최대 조회 개월
_PHASE2B_PENDING = ('checklist',)  # Phase 2b 미구현 (placeholder 유지)

# partner_display 정규화 (v2.20.11 _COMPANY_SQL 정합) — MECH/ELEC 만. group = category.
#   MECH: mech_partner ('TMS'→TMS(M)) / ELEC: elec_partner ('TMS'→TMS(E))
#   ⚠️ NULLIF(TRIM(...), '') 래핑 (Codex 라운드3 M-6): NULL/빈문자열/공백 partner 를
#      단일 IS NOT NULL 조건으로 일괄 제외 → SELECT·WHERE·GROUP BY·company_filter 전부 정합.
#   ⚠️ 비협력사 제외 (_EXCLUDED_PARTNERS): 'GST'(자체수행) + 'SH'(비협력사/구데이터, 2026-06-10
#      Twin파파 제외 지시) → NULL → IS NOT NULL 로 일괄 제외. worker 파생도 동일 set 제외.
_EXCLUDED_PARTNERS = ('GST', 'SH')  # 협력사 아님 — task/worker 파생 양쪽 제외
_PARTNER_SQL = (
    "NULLIF(NULLIF(NULLIF(TRIM(CASE "
    "WHEN t.task_category = 'MECH' THEN CASE WHEN pi.mech_partner = 'TMS' THEN 'TMS(M)' ELSE pi.mech_partner END "
    "WHEN t.task_category = 'ELEC' THEN CASE WHEN pi.elec_partner = 'TMS' THEN 'TMS(E)' ELSE pi.elec_partner END "
    "ELSE NULL END), ''), 'GST'), 'SH')"
)

_METRIC_LABEL = {
    'openTasks': '미종료', 'autoClose': '자동마감', 'zeroTap': '0초탭%',
    'taggingRate': '태깅율%', 'checkoutMiss': '퇴근미체크율%', 'checklist': '체크리스트완료%',
}
_METRIC_NOTE = {
    'taggingRate': '미태깅 = 데이터 누락(작업 부재 아님)',
    'zeroTap': '0초탭 = 미추적(정상 즉시완료 제외)',
    'checkoutMiss': '퇴근미체크율 = 참고 지표(평가 제외, 근태 페이지 동일 기준). 출근 후 퇴근 미체크 비율',
}
# 낮을수록 좋음(true) / 높을수록 좋음(false=taggingRate)
_LOWER_BETTER = {
    'openTasks': True, 'autoClose': True, 'zeroTap': True, 'taggingRate': False,
    'checkoutMiss': True, 'checklist': False,
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
    sample_n: Optional[int] = None, reference_only: bool = False,
) -> Dict[str, Any]:
    """지표 1개 표준 envelope (공정성 계약 강제, A1).

    reference_only=True: 참고 지표(평가/등급/줄세우기 제외). 근태 평가 제외 결정 정합 —
      checkoutMiss(퇴근미체크율)는 근태 페이지 동일값을 참고로만 표시(평가 X). grade_eligible=False.
    """
    grade_eligible = available and raw is not None and not reference_only
    ineligibility_reason: Optional[str] = None
    if reference_only:
        ineligibility_reason = 'reference_only'
    elif available and tracking_coverage is not None and tracking_coverage < _TRACKING_THRESHOLD:
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
        'reference_only': reference_only,
        'phase': phase,
        'label': _METRIC_LABEL.get(metric, metric),
        'label_note': _METRIC_NOTE.get(metric),
        'lower_better': _LOWER_BETTER.get(metric),
    }


# ---------------------------------------------------------------------------
# Phase 1 raw 집계 (partner_display × group) — MECH/ELEC only, 미지정 제외
# ---------------------------------------------------------------------------

def _query_open_tasks_count(cur, start, end, company_filter: Optional[str]) -> Dict[Tuple[str, str], int]:
    """미종료 task 수 — partner×group, **월단위**(A: started_at ∈ [start,end) AND 미완).

    미종료 기준 = 정식 `/tasks/pending/grouped` 정합 (B): is_applicable=TRUE +
    force_closed=FALSE + TEST CUSTOMER 제외. (autoClose 가 completed_at 으로 월 자르듯
    openTasks 는 started_at 기준 — "그 달 시작됐는데 아직 미종료").
    """
    sql = f"""
        SELECT {_PARTNER_SQL} AS partner, t.task_category AS grp, COUNT(*) AS n
        FROM app_task_details t
        JOIN plan.product_info pi ON pi.serial_number = t.serial_number
        WHERE t.task_category IN ('MECH','ELEC')
          AND t.started_at >= %s AND t.started_at < %s
          AND t.completed_at IS NULL
          AND COALESCE(t.force_closed, FALSE) = FALSE
          AND t.is_applicable = TRUE
          AND COALESCE(pi.customer, '') <> 'TEST CUSTOMER'
          AND {_PARTNER_SQL} IS NOT NULL
    """
    params: List[Any] = [start, end]
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
          AND t.is_applicable = TRUE
          AND COALESCE(pi.customer, '') <> 'TEST CUSTOMER'
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
        WHERE t.task_category IN ('MECH','ELEC')
          AND t.is_applicable = TRUE
          AND COALESCE(pi.customer, '') <> 'TEST CUSTOMER'
          AND {_PARTNER_SQL} IS NOT NULL
        ORDER BY 2, 1
    """
    cur.execute(sql)
    return [(r['partner'], r['grp']) for r in cur.fetchall()]


def _query_worker_partner_groups(cur, company_filter: Optional[str]) -> List[Tuple[str, str]]:
    """worker 파생 partner×group (workers.company × role) — MECH/ELEC 협력사 worker 기준.

    Phase 2a taggingRate 의 partner 출처. task 파생(_query_partner_groups)과 union 하여
    row universe 누락 방지 (Codex 라운드1 D). TMS(M)/(E) 는 workers.company 에 분리 저장됨.
    """
    sql = """
        SELECT DISTINCT w.company AS partner, w.role::text AS grp
        FROM workers w
        WHERE w.company IS NOT NULL AND w.company NOT IN ('GST', 'SH')
          AND w.role::text IN ('MECH','ELEC')
          AND COALESCE(w.is_active, TRUE) = TRUE
    """
    params: List[Any] = []
    if company_filter:
        sql += " AND w.company = %s"
        params.append(company_filter)
    sql += " ORDER BY 2, 1"
    cur.execute(sql, params)
    return [(r['partner'], r['grp']) for r in cur.fetchall()]


def _query_tagging(cur, start, end, company_filter: Optional[str]) -> Dict[Tuple[str, str], Tuple[int, int]]:
    """태깅 참여 (월 DISTINCT worker) — (company, role) → (gst_onsite, tagged).

    (B) gst_onsite = work_site='GST' 출근 worker (HQ-only·무출근 제외).
    (A) tagged = gst_onsite 중 work_start_log(task_category=role) 1건+ DISTINCT worker.
    """
    sql = """
        WITH onsite AS (
            SELECT DISTINCT w.id, w.company AS partner, w.role::text AS grp
            FROM workers w
            JOIN hr.partner_attendance pa ON pa.worker_id = w.id
            WHERE w.company IS NOT NULL AND w.company NOT IN ('GST', 'SH')
              AND w.role::text IN ('MECH','ELEC')
              AND COALESCE(w.is_active, TRUE) = TRUE
              AND pa.check_type = 'in' AND pa.work_site = 'GST'
              AND pa.check_time >= %s AND pa.check_time < %s
              {company_clause}
        ),
        tagged AS (
            SELECT DISTINCT o.id
            FROM onsite o
            JOIN work_start_log wsl ON wsl.worker_id = o.id
              AND wsl.task_category = o.grp
              AND wsl.started_at >= %s AND wsl.started_at < %s
        )
        SELECT o.partner, o.grp,
               COUNT(DISTINCT o.id) AS gst_onsite,
               COUNT(DISTINCT t.id) AS tagged
        FROM onsite o
        LEFT JOIN tagged t ON t.id = o.id
        GROUP BY o.partner, o.grp
    """
    company_clause = "AND w.company = %s" if company_filter else ""
    sql = sql.format(company_clause=company_clause)
    params: List[Any] = [start, end]
    if company_filter:
        params.append(company_filter)
    params += [start, end]
    cur.execute(sql, params)
    return {(r['partner'], r['grp']): (r['gst_onsite'], r['tagged']) for r in cur.fetchall()}


def _query_zerotap(cur, start, end, company_filter: Optional[str]) -> Dict[Tuple[str, str], Tuple[int, int]]:
    """0초탭(미추적) — partner×group → (substantive_n, zerotap_n).

    (C) active_time_minutes<=1 = 미추적. one-click 화이트리스트(is_instant_whitelisted)는
    substantive 모집단에서 제외 (Python 후처리, SQL private whitelist 금지 — Codex A3).
    active_time_minutes IS NULL(미측정, 예: one-action) 은 모집단 제외.
    """
    sql = f"""
        SELECT {_PARTNER_SQL} AS partner, t.task_category AS grp, t.task_id,
               COUNT(*) AS n,
               COUNT(*) FILTER (WHERE t.active_time_minutes <= 1) AS zero_n
        FROM app_task_details t
        JOIN plan.product_info pi ON pi.serial_number = t.serial_number
        WHERE t.task_category IN ('MECH','ELEC')
          AND t.completed_at >= %s AND t.completed_at < %s
          AND t.active_time_minutes IS NOT NULL
          AND t.is_applicable = TRUE
          AND COALESCE(pi.customer, '') <> 'TEST CUSTOMER'
          AND {_PARTNER_SQL} IS NOT NULL
    """
    params: List[Any] = [start, end]
    if company_filter:
        sql += f" AND {_PARTNER_SQL} = %s"
        params.append(company_filter)
    sql += f" GROUP BY {_PARTNER_SQL}, t.task_category, t.task_id"
    cur.execute(sql, params)
    acc: Dict[Tuple[str, str], List[int]] = {}
    for r in cur.fetchall():
        if is_instant_whitelisted(r['task_id']):
            continue  # 정상 즉시완료 task 제외 (미추적 아님)
        key = (r['partner'], r['grp'])
        a = acc.setdefault(key, [0, 0])
        a[0] += int(r['n'])
        a[1] += int(r['zero_n'])
    return {k: (v[0], v[1]) for k, v in acc.items()}


def _query_checkout_miss(cur, start, end, company_filter: Optional[str]) -> Dict[Tuple[str, str], Tuple[int, int]]:
    """퇴근 미체크율 (참고 지표) — (company, role) → (checked_in_days, missed_days).

    #86 checkout_status 정의(일별 cutoff = (D+1) 02:00 KST)를 월×협력사로 가중 집계.
    miss_rate = SUM(미체크 worker-day) / SUM(출근 worker-day) (A4 일별 합산).
    ⚠️ 단순화: #86 의 next_day_in LEAST 보정(back-to-back 0.04%)은 생략 — 참고 지표라 무시 가능.
    근태 평가 제외 정합 → 평가 X 참고(reference_only).
    """
    company_clause = "AND w.company = %(company)s" if company_filter else ""
    sql = f"""
        WITH checkins AS (
            SELECT pa.worker_id, w.company AS partner, w.role::text AS grp,
                   (pa.check_time AT TIME ZONE 'Asia/Seoul')::date AS d,
                   MIN(pa.check_time) AS cin
            FROM hr.partner_attendance pa
            JOIN workers w ON w.id = pa.worker_id
            WHERE pa.check_type = 'in'
              AND pa.check_time >= %(start)s AND pa.check_time < %(end)s
              AND w.company IS NOT NULL AND w.company NOT IN ('GST', 'SH')
              AND w.role::text IN ('MECH','ELEC')
              AND w.approval_status = 'approved' AND COALESCE(w.is_active, TRUE) = TRUE
              {company_clause}
            GROUP BY pa.worker_id, w.company, w.role, d
        ),
        co AS (
            SELECT c.worker_id, c.partner, c.grp, c.d, c.cin,
                   ((c.d + 1)::timestamp AT TIME ZONE 'Asia/Seoul') + INTERVAL '2 hours' AS cutoff
            FROM checkins c
        ),
        done AS (
            SELECT co.worker_id, co.d, MAX(pa.check_time) AS cout
            FROM co
            JOIN hr.partner_attendance pa
              ON pa.worker_id = co.worker_id AND pa.check_type = 'out'
             AND pa.check_time > co.cin AND pa.check_time < co.cutoff
            GROUP BY co.worker_id, co.d
        )
        SELECT co.partner, co.grp,
               COUNT(*) AS checked_in_days,
               COUNT(*) FILTER (WHERE d2.cout IS NULL) AS missed_days
        FROM co
        LEFT JOIN done d2 ON d2.worker_id = co.worker_id AND d2.d = co.d
        GROUP BY co.partner, co.grp
    """
    params: Dict[str, Any] = {'start': start, 'end': end}
    if company_filter:
        params['company'] = company_filter
    cur.execute(sql, params)
    return {(r['partner'], r['grp']): (r['checked_in_days'], r['missed_days']) for r in cur.fetchall()}


# ---------------------------------------------------------------------------
# group_avg (peer-only, k>=3) — A7 / 라운드2 #1
# ---------------------------------------------------------------------------

def _group_avg(
    value_by_partner: Dict[Tuple[str, str], Any], grp: str,
    all_groups: List[Tuple[str, str]], scope, *, missing: Optional[float] = 0.0,
) -> Tuple[Optional[float], int, Optional[str]]:
    """같은 group 의 **그룹평균** (자사 포함, 기여 협력사≥_MIN_PEERS 충족 시만).

    #91(2026-06-12): 협력사 매니저도 group_avg 노출 — `cand=partners`(admin·협력사 동일, 자사 포함).
      - 이전: 협력사는 자사 제외 peer 평균 → group 3곳서 자사 제외 2<3 → 영구 suppress 였음.
      - 변경: admin·협력사 모두 group 전체(자사 포함) 평균 = **동일 값**.
      - 역추론 가드: len(vals)>=3(자사 포함 기여≥3 → 자사 외 미지수≥2) → "avg+자기값"으로 타사
        개별값 역산 불가. 기여<3(예: 3곳 중 1곳 데이터 누락 → vals=2 → 자사+1타사면 그 1곳 역산 가능)
        시 suppress 로 정확히 차단. (3곳 노출 시 타사 2곳 '합계'는 도출 가능 — 개별값 아님, 허용 수준.)

    `missing` (불변식: raw 가 None 가능한 지표 ⟺ missing=None):
    - 0.0 (openTasks/autoClose): raw 항상 count(≥0) → 누락 협력사 = 정상 0건 → 분모 포함.
    - None (taggingRate/zeroTap/checkoutMiss 등 rate): 분모 없으면 raw=None → 측정 불가 협력사 제외.
    """
    partners = [p for (p, g) in all_groups if g == grp]
    cand = partners   # #91: 협력사도 자사 포함 group-wide avg (admin 과 동일 값)
    vals: List[float] = []
    for p in cand:
        v = value_by_partner.get((p, grp), missing)
        if v is not None:
            vals.append(float(v))
    peer_n = len(vals)
    if peer_n < _MIN_PEERS:
        return None, peer_n, 'insufficient_peers'
    return round(sum(vals) / peer_n, 4), peer_n, None


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
            task_groups = _query_partner_groups(cur)               # task 파생 partner×group
            worker_groups = _query_worker_partner_groups(cur, None)  # worker 파생 (taggingRate)
            open_counts = _query_open_tasks_count(cur, start, end, None)  # 월단위 (started_at ∈ month)
            auto_counts = _query_auto_close_count(cur, start, end, None)
            tagging = _query_tagging(cur, start, end, None)         # {(p,g):(onsite,tagged)}
            zerotap = _query_zerotap(cur, start, end, None)         # {(p,g):(sub,zero)}
            checkout_miss = _query_checkout_miss(cur, start, end, None)  # {(p,g):(in_days,miss_days)} 참고
    finally:
        put_conn(conn)

    # row universe = task ∪ worker (D: 누락 방지)
    task_set = set(task_groups)
    worker_set = set(worker_groups)
    all_groups = sorted(task_set | worker_set, key=lambda x: (x[1], x[0]))

    # rate 지표 group_avg 용 by-partner dict (분모0/누락 = None → peer 제외)
    tagrate_by: Dict[Tuple[str, str], Optional[float]] = {
        k: (round(tagged / onsite, 4) if onsite > 0 else None) for k, (onsite, tagged) in tagging.items()
    }
    zerorate_by: Dict[Tuple[str, str], Optional[float]] = {
        k: (round(zero / sub, 4) if sub > 0 else None) for k, (sub, zero) in zerotap.items()
    }
    checkoutmiss_by: Dict[Tuple[str, str], Optional[float]] = {
        k: (round(miss / ind, 4) if ind > 0 else None) for k, (ind, miss) in checkout_miss.items()
    }

    # 노출 대상 row: admin=전체 / manager=자사만
    target = [(p, g) for (p, g) in all_groups if scope.is_global or p == scope.company]

    rows: List[Dict[str, Any]] = []
    for partner, grp in target:
        metrics: Dict[str, Any] = {}

        # ── Phase 1: openTasks / autoClose (count, 누락=0) ──
        raw_open = float(open_counts.get((partner, grp), 0))
        ga, pn, sr = _group_avg(open_counts, grp, all_groups, scope, missing=0.0)
        metrics['openTasks'] = _envelope(
            'openTasks', raw_open, available=True, phase='phase1',
            group_avg=ga, peer_n=pn, suppressed_reason=sr, sample_n=int(raw_open))

        raw_auto = float(auto_counts.get((partner, grp), 0))
        ga2, pn2, sr2 = _group_avg(auto_counts, grp, all_groups, scope, missing=0.0)
        metrics['autoClose'] = _envelope(
            'autoClose', raw_auto, available=True, phase='phase1',
            group_avg=ga2, peer_n=pn2, suppressed_reason=sr2, sample_n=int(raw_auto))

        # ── Phase 2a: taggingRate (분모 gst_onsite, 평가) ──
        onsite, tagged = tagging.get((partner, grp), (0, 0))
        tag_raw = round(tagged / onsite, 4) if onsite > 0 else None
        ga_t, pn_t, sr_t = _group_avg(tagrate_by, grp, all_groups, scope, missing=None)
        metrics['taggingRate'] = _envelope(
            'taggingRate', tag_raw, available=True, phase='phase2',
            group_avg=ga_t, peer_n=pn_t, suppressed_reason=sr_t, sample_n=onsite)

        # ── Phase 2a: checkoutMiss (퇴근미체크율, 참고 지표 — 평가 제외) ──
        in_days, miss_days = checkout_miss.get((partner, grp), (0, 0))
        cm_raw = round(miss_days / in_days, 4) if in_days > 0 else None
        ga_c, pn_c, sr_c = _group_avg(checkoutmiss_by, grp, all_groups, scope, missing=None)
        metrics['checkoutMiss'] = _envelope(
            'checkoutMiss', cm_raw, available=True, phase='phase2', reference_only=True,
            group_avg=ga_c, peer_n=pn_c, suppressed_reason=sr_c, sample_n=in_days)

        # ── Phase 2a: zeroTap (substantive 모집단, one-click 제외) ──
        sub, zero = zerotap.get((partner, grp), (0, 0))
        z_raw = round(zero / sub, 4) if sub > 0 else None
        ga_z, pn_z, sr_z = _group_avg(zerorate_by, grp, all_groups, scope, missing=None)
        metrics['zeroTap'] = _envelope(
            'zeroTap', z_raw, available=True, phase='phase2',
            group_avg=ga_z, peer_n=pn_z, suppressed_reason=sr_z, sample_n=sub)

        # ── Phase 2b: checklist = placeholder (별 Codex 라운드) ──
        for m in _PHASE2B_PENDING:
            metrics[m] = _envelope(m, None, available=False, phase='phase2')

        rows.append({'partner': partner, 'group': grp, 'metrics': metrics})

    # provenance (D 진단): 각 노출 row 가 task/worker 어느 출처에서 왔는지
    provenance: Dict[str, List[str]] = {}
    for (p, g) in target:
        srcs: List[str] = []
        if (p, g) in task_set:
            srcs.append('task')
        if (p, g) in worker_set:
            srcs.append('worker')
        provenance[f"{p}|{g}"] = srcs

    return {
        'month': month,
        'scope': 'global' if scope.is_global else 'self',
        'company': None if scope.is_global else scope.company,
        'rows': rows,
        'meta': {
            'phase1_metrics': ['openTasks', 'autoClose'],
            'phase2a_metrics': ['taggingRate', 'zeroTap', 'checkoutMiss'],
            'reference_metrics': ['checkoutMiss'],  # 평가 제외 참고 (근태 동일값)
            'phase2b_pending': list(_PHASE2B_PENDING),
            # 집계 anchor 명시 (Advisory): openTasks=월(started 기준)·autoClose/zeroTap=월(completed)·
            #   taggingRate/checkoutMiss=월(출근). /open-tasks 큐는 realtime_all_open (값 다름, 의도).
            'openTasks_basis': 'monthly_started_open',
            'missed_task_standard': 'is_applicable=TRUE, force_closed=FALSE, TEST 제외 (정식 미종료 현황 정합)',
            'min_peers': _MIN_PEERS,
            'groups_present': sorted({g for _, g in target}),
            'partner_provenance': provenance,
            'window': {'month': month, 'start': start.isoformat(), 'end': end.isoformat()},
            'generated_at': datetime.now(KST).isoformat(),
            'fairness_note': (
                'BE는 raw + group_avg(peer-only, k>=3)만 제공. 등급·줄세우기 = VIEW. '
                '근태(출근율·퇴근미체크)는 협력사 평가 지표에서 제외(출근=taggingRate 분모로만).'
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
                       {_PARTNER_SQL} AS partner, w.name AS worker_name,
                       w.company AS worker_company
                FROM app_task_details t
                JOIN plan.product_info pi ON pi.serial_number = t.serial_number
                LEFT JOIN workers w ON w.id = t.worker_id
                WHERE t.task_category IN ('MECH','ELEC')
                  AND t.started_at IS NOT NULL AND t.completed_at IS NULL
                  AND COALESCE(t.force_closed, FALSE) = FALSE
                  AND t.is_applicable = TRUE
                  AND COALESCE(pi.customer, '') <> 'TEST CUSTOMER'
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
                  AND COALESCE(t.force_closed, FALSE) = FALSE
                  AND t.is_applicable = TRUE
                  AND COALESCE(pi.customer, '') <> 'TEST CUSTOMER'
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
        # M-Q8 누수 차단: 협력사 매니저는 자사 worker 실명만. task partner=자사 이지만
        #   실제 작업자(worker.company)가 타사면 실명 마스킹 (cross-company tagging 방어).
        #   ⚠️ M-Q8-NULL: worker_company IS NULL(회사 미지정)도 != company_filter → True → 마스킹
        #      (truthy 체크 제거 — NULL 이 자사 아님으로 안전하게 처리).
        worker_name = r['worker_name']
        worker_masked = bool(
            company_filter and r.get('worker_company') != company_filter
        )
        if worker_masked:
            worker_name = None
        tasks.append({
            'id': r['id'],
            'serial_number': r['serial_number'],
            'task_id': r['task_id'],
            'task_name': r['task_name'],
            'group': r['grp'],
            'partner': r['partner'],
            'worker_id': wid if not worker_masked else None,
            'worker_name': worker_name,
            'worker_masked': worker_masked,
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
            'basis': 'realtime_all_open',  # 현재 backlog 전체 (summary openTasks=월단위와 다름, 의도)
            'missed_task_standard': 'is_applicable=TRUE, force_closed=FALSE, TEST 제외',
            'generated_at': now.isoformat(),
        },
    }


# ---------------------------------------------------------------------------
# trend endpoint builder — 월별 추이 (Phase 2a). openTasks 제외(실시간).
# ---------------------------------------------------------------------------

def build_trend(months_back: int, scope) -> Dict[str, Any]:
    """월별 autoClose / taggingRate / zeroTap 시계열 — partner×group.

    openTasks 는 실시간 스냅이라 월별 추이 무의미 → 제외 (Codex 라운드1).
    협력사 매니저 = 자사 series만 (타사 미노출). group_avg 는 summary endpoint 참조.
    """
    months_back = max(1, min(int(months_back), _TREND_MAX_MONTHS))
    now = datetime.now(KST)

    # 월 목록 (오래된→최근)
    ym: List[Tuple[int, int]] = []
    y, m = now.year, now.month
    for _ in range(months_back):
        ym.append((y, m))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    ym.reverse()
    month_strs = [f"{yy:04d}-{mm:02d}" for (yy, mm) in ym]

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            task_groups = _query_partner_groups(cur)
            worker_groups = _query_worker_partner_groups(cur, None)
            all_groups = sorted(set(task_groups) | set(worker_groups), key=lambda x: (x[1], x[0]))
            per_month: List[Tuple[Dict, Dict, Dict]] = []
            for ms in month_strs:
                start, end, _f, _l = _month_range_kst(ms)
                auto = _query_auto_close_count(cur, start, end, None)
                tag = _query_tagging(cur, start, end, None)
                zt = _query_zerotap(cur, start, end, None)
                per_month.append((auto, tag, zt))
    finally:
        put_conn(conn)

    target = [(p, g) for (p, g) in all_groups if scope.is_global or p == scope.company]
    series: List[Dict[str, Any]] = []
    for (p, g) in target:
        autoc: List[int] = []
        tagr: List[Optional[float]] = []
        zeror: List[Optional[float]] = []
        for (auto, tag, zt) in per_month:
            autoc.append(int(auto.get((p, g), 0)))
            onsite, tagged = tag.get((p, g), (0, 0))
            tagr.append(round(tagged / onsite, 4) if onsite > 0 else None)
            sub, zero = zt.get((p, g), (0, 0))
            zeror.append(round(zero / sub, 4) if sub > 0 else None)
        series.append({
            'partner': p, 'group': g,
            'autoClose': autoc, 'taggingRate': tagr, 'zeroTap': zeror,
        })

    return {
        'scope': 'global' if scope.is_global else 'self',
        'company': None if scope.is_global else scope.company,
        'months': month_strs,
        'series': series,
        'meta': {
            'months_back': months_back,
            'metrics': ['autoClose', 'taggingRate', 'zeroTap'],
            'note': ('openTasks 는 실시간 지표라 trend 제외. group_avg 는 summary 참조. '
                     '협력사 매니저=자사 series만.'),
            'generated_at': now.isoformat(),
        },
    }
