"""
Sprint 85 (FEAT-CT-ANALYSIS-HUB-BE-MVP-20260605) — CT 분석 허브 통계 서비스

MVP = ① 데이터 신뢰도 + ② CT 표준(IQR, man-hour).
설계서: AGENT_TEAM_LAUNCH.md § Sprint 85 / 결정 동결: CT_ANALYSIS_ROADMAP.md §15

핵심 정합 (Codex 라운드 1~2 GO):
  - CT 작업시간 = man-hour(`app_task_details.duration_minutes` = v2.22.0 interval-union SSoT),
    벽시계(elapsed) 아님. box plot = percentile_cont(duration_minutes/60.0).
  - clean 모집단 = duration_source IS NULL OR 'NORMAL_COMPLETION' (ATTENDANCE_OUT/추정 제외).
  - TMS(M) 더러운 task(TANK_MODULE/PRESSURE_TEST) 제외 + TEST 제외.
  - Tukey 1-pass: raw Q1/Q3 fence → fence 내 재집계. min/max = fence 내 실측.
  - 카테고리 = pooled median(참고용, Σ median 폐기) + task_count/sample_size/confidence.
  - 월 경계/교육 cut = KST (AT TIME ZONE 'Asia/Seoul').
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import psycopg2.extras

from app.db_pool import put_conn
from app.models.worker import get_db_connection
from app.services.task_seed import _TEMPLATES

logger = logging.getLogger(__name__)
_KST = ZoneInfo("Asia/Seoul")

# ── task_id → task_name 매핑 (task_seed 단일 소스) ──
_TASK_NAME: Dict[str, str] = {}
for _cat_tmpls in _TEMPLATES.values():
    for _t in _cat_tmpls:
        _TASK_NAME.setdefault(_t.task_id, _t.task_name)

_CATEGORY_LABEL_KO: Dict[str, str] = {
    "MECH": "기구",
    "ELEC": "전장",
    "TMS": "Tank Module",
    "PI": "PI (사전 검사)",
    "QI": "QI (품질 검사)",
    "SI": "SI (출하 검사)",
}

# 추정/더러운 source — ② 통계 제외 (① breakdown 에만 표시)
_CLEAN_SOURCES = ("NULL", "NORMAL_COMPLETION")  # 참고용(표기). SQL 은 IS NULL OR = 'NORMAL_COMPLETION'
_ESTIMATED_SOURCES = ("PREV_DAY_CAP", "FALLBACK_TRIGGER_DATE_17", "ATTENDANCE_OUT", "INVALID_WARNING")

# 교육 분기점 (KST 자정 literal — Codex R2 A)
_TRAINING_CUT_KST = "2026-06-02 00:00:00"

_VALID_PERIODS = {"last_90d"}  # MVP: 90일 합산만 (전체기간/단일월은 후속)

# 모듈 레벨 TTL 캐시 (1h) — 기준 흔들림 방지(§15.3)
_CACHE_TTL_SEC = 3600
_cache: Dict[str, tuple] = {}  # key -> (ts, value)


def _cache_get(key: str) -> Optional[Any]:
    hit = _cache.get(key)
    if hit and (time.time() - hit[0]) < _CACHE_TTL_SEC:
        return hit[1]
    return None


def _cache_put(key: str, value: Any) -> None:
    _cache[key] = (time.time(), value)


def _confidence(n: int) -> str:
    if n >= 100:
        return "high"
    if n >= 30:
        return "medium"
    return "low"


def _r(v: Optional[float], nd: int = 1) -> float:
    return round(float(v), nd) if v is not None else 0.0


# clean 모집단 WHERE (alias td=app_task_details, p=plan.product_info)
# %% = psycopg2 리터럴 % (LIKE). _CLEAN_CORE = lookback 없는 공통 조건(교육 전후는 전기간 필요).
_CLEAN_CORE = (
    "td.completed_at IS NOT NULL "
    "AND td.duration_minutes IS NOT NULL "
    "AND (td.duration_source IS NULL OR td.duration_source = 'NORMAL_COMPLETION') "
    "AND td.task_id NOT IN ('TANK_MODULE','PRESSURE_TEST') "
    "AND COALESCE(p.customer, '') <> 'TEST CUSTOMER' "
    "AND td.serial_number NOT LIKE 'TEST%%'"
)
_CLEAN_WHERE = (
    _CLEAN_CORE
    + " AND td.completed_at >= now() - (%(lookback_days)s || ' days')::interval"
)


def _model_clause(model: Optional[str]) -> str:
    if model and model not in ("전체 모델", "ALL", ""):
        return " AND p.model ILIKE %(model_prefix)s"
    return ""


def _category_clause(category: Optional[str]) -> str:
    if category and category not in ("ALL", ""):
        return " AND td.task_category = %(category)s"
    return ""


def _stats_params(lookback_days: int, model: Optional[str], category: Optional[str]) -> Dict[str, Any]:
    p: Dict[str, Any] = {"lookback_days": lookback_days}
    if model and model not in ("전체 모델", "ALL", ""):
        p["model_prefix"] = f"{model}%"
    if category and category not in ("ALL", ""):
        p["category"] = category
    return p


def get_task_ct_stats(
    lookback_days: int = 90,
    model: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """② CT 표준 — task별 box plot(man-hour, Tukey) + 카테고리 pooled median + meta."""
    cache_key = f"task_stats:{lookback_days}:{model}:{category}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    params = _stats_params(lookback_days, model, category)
    mc = _model_clause(model)
    cc = _category_clause(category)

    # Tukey 1-pass CTE: base → fence(raw Q1/Q3) → clipped(fence 내) → 집계
    cte = f"""
        WITH base AS (
            SELECT td.task_category AS category, td.task_id,
                   td.duration_minutes / 60.0 AS dh
            FROM app_task_details td
            JOIN plan.product_info p ON p.serial_number = td.serial_number
            WHERE {_CLEAN_WHERE}{mc}{cc}
        ),
        fence AS (
            SELECT task_id,
                   percentile_cont(0.25) WITHIN GROUP (ORDER BY dh) AS q1,
                   percentile_cont(0.75) WITHIN GROUP (ORDER BY dh) AS q3
            FROM base GROUP BY task_id
        ),
        clipped AS (
            SELECT b.category, b.task_id, b.dh
            FROM base b JOIN fence f ON f.task_id = b.task_id
            WHERE b.dh BETWEEN (f.q1 - 1.5*(f.q3-f.q1)) AND (f.q3 + 1.5*(f.q3-f.q1))
        )
    """

    task_sql = cte + """
        SELECT category, task_id,
               COUNT(*) AS n,
               MIN(dh) AS min_h, MAX(dh) AS max_h, AVG(dh) AS mean_h,
               percentile_cont(0.25) WITHIN GROUP (ORDER BY dh) AS q1,
               percentile_cont(0.5)  WITHIN GROUP (ORDER BY dh) AS median,
               percentile_cont(0.75) WITHIN GROUP (ORDER BY dh) AS q3
        FROM clipped
        GROUP BY category, task_id
        ORDER BY category, task_id
    """
    # 카테고리 pooled median (Σ median 폐기 — Codex M-Q5)
    cat_sql = cte + """
        SELECT category,
               COUNT(DISTINCT task_id) AS task_count,
               COUNT(*) AS sample_size,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY dh) AS pooled_median
        FROM clipped
        GROUP BY category
        ORDER BY category
    """
    # meta — 모델 분포 + 추정 source 제외 비율 (편향 노출, Codex A-Q4)
    model_dist_sql = f"""
        SELECT p.model AS model, COUNT(*) AS n
        FROM app_task_details td
        JOIN plan.product_info p ON p.serial_number = td.serial_number
        WHERE {_CLEAN_WHERE}{mc}{cc}
        GROUP BY p.model ORDER BY n DESC
    """
    excl_sql = f"""
        SELECT COALESCE(td.duration_source, 'NULL') AS source, COUNT(*) AS n
        FROM app_task_details td
        JOIN plan.product_info p ON p.serial_number = td.serial_number
        WHERE td.completed_at IS NOT NULL
          AND td.duration_minutes IS NOT NULL
          AND td.task_id NOT IN ('TANK_MODULE','PRESSURE_TEST')
          AND COALESCE(p.customer, '') <> 'TEST CUSTOMER'
          AND td.serial_number NOT LIKE 'TEST%%'
          AND td.completed_at >= now() - (%(lookback_days)s || ' days')::interval
          {mc}{cc}
        GROUP BY COALESCE(td.duration_source, 'NULL')
    """

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(task_sql, params)
            task_rows = cur.fetchall()
            cur.execute(cat_sql, params)
            cat_rows = cur.fetchall()
            cur.execute(model_dist_sql, params)
            model_rows = cur.fetchall()
            cur.execute(excl_sql, params)
            excl_rows = cur.fetchall()
    finally:
        put_conn(conn)

    tasks: List[Dict[str, Any]] = []
    for r in task_rows:
        n = int(r["n"])
        q1, q3 = _r(r["q1"]), _r(r["q3"])
        tasks.append({
            "task_id": r["task_id"],
            "task_name": _TASK_NAME.get(r["task_id"], r["task_id"]),
            "category": r["category"],
            "min_hours": _r(r["min_h"]),
            "q1_hours": q1,
            "median_hours": _r(r["median"]),
            "q3_hours": q3,
            "max_hours": _r(r["max_h"]),
            "mean_hours": _r(r["mean_h"]),
            "iqr_hours": _r(q3 - q1),
            "sample_size": n,
            "confidence": _confidence(n),
        })

    categories: List[Dict[str, Any]] = []
    for r in cat_rows:
        n = int(r["sample_size"])
        categories.append({
            "category": r["category"],
            "label_ko": _CATEGORY_LABEL_KO.get(r["category"], r["category"]),
            "task_count": int(r["task_count"]),
            "sample_size": n,
            "confidence": _confidence(n),
            "pooled_median_hours": _r(r["pooled_median"]),
        })

    total_sample = sum(t["sample_size"] for t in tasks)
    excluded_by_source = {
        r["source"]: int(r["n"]) for r in excl_rows if r["source"] in _ESTIMATED_SOURCES
    }
    total_window = sum(int(r["n"]) for r in excl_rows)
    excluded_n = sum(excluded_by_source.values())
    is_filtered = bool(model and model not in ("전체 모델", "ALL", ""))

    result = {
        "tasks": tasks,
        "categories": categories,
        "meta": {
            "as_of": datetime.now(_KST).isoformat(),
            "lookback_days": lookback_days,
            "total_sample": total_sample,
            "model_distribution": [
                {"model": r["model"], "n": int(r["n"])} for r in model_rows
            ],
            "excluded_by_source": excluded_by_source,
            "excluded_pct": _r((excluded_n / total_window * 100) if total_window else 0.0),
            "median_basis": "pooled_clean_instances",  # 표준공수합 아님 (Codex R2 A)
            "confidence_scope": "filtered" if is_filtered else "all",
            "low_sample_warning": is_filtered and total_sample < 100,
        },
    }
    _cache_put(cache_key, result)
    return result


def get_data_quality(lookback_days: int = 90) -> Dict[str, Any]:
    """① 데이터 신뢰도 — duration_source 분포 + 자동마감 추이(월별 KST) + 교육 전후."""
    cache_key = f"data_quality:{lookback_days}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    # [1] duration_source 분포 (완료, TMS(M)·TEST 제외, lookback)
    src_sql = """
        SELECT COALESCE(td.duration_source, 'NULL') AS source, COUNT(*) AS n
        FROM app_task_details td
        JOIN plan.product_info p ON p.serial_number = td.serial_number
        WHERE td.completed_at IS NOT NULL
          AND td.task_id NOT IN ('TANK_MODULE','PRESSURE_TEST')
          AND COALESCE(p.customer, '') <> 'TEST CUSTOMER'
          AND td.serial_number NOT LIKE 'TEST%%'
          AND td.completed_at >= now() - (%(lookback_days)s || ' days')::interval
        GROUP BY COALESCE(td.duration_source, 'NULL')
        ORDER BY n DESC
    """
    # [2] 월별 마감유형 추이 — KST 월 경계 (Codex M-Q8). 추이는 lookback 무관 고정 6개월 윈도우(의도).
    #     close_reason LIKE 'AUTO_CLOSED_BY_%%' = dashboard_service._AUTO_LIKE 와 동치 (분류 규칙 변경 시 동기화).
    trend_sql = """
        SELECT to_char(date_trunc('month', td.completed_at AT TIME ZONE 'Asia/Seoul'), 'YYYY-MM') AS month,
               COUNT(*) AS total,
               COUNT(*) FILTER (
                   WHERE td.close_reason LIKE 'AUTO_CLOSED_BY_%%' AND td.force_closed = FALSE
               ) AS auto,
               COUNT(*) FILTER (WHERE td.force_closed = TRUE) AS force
        FROM app_task_details td
        JOIN plan.product_info p ON p.serial_number = td.serial_number
        WHERE td.completed_at IS NOT NULL
          AND td.task_id NOT IN ('TANK_MODULE','PRESSURE_TEST')
          AND COALESCE(p.customer, '') <> 'TEST CUSTOMER'
          AND td.serial_number NOT LIKE 'TEST%%'
          AND td.completed_at >= now() - INTERVAL '6 months'
        GROUP BY 1 ORDER BY 1
    """
    # [5] 교육(6/2 KST) 전후 task별 man-hour (clean only)
    train_sql = f"""
        SELECT td.task_id,
               AVG(td.duration_minutes / 60.0) FILTER (
                   WHERE (td.completed_at AT TIME ZONE 'Asia/Seoul') < TIMESTAMP '{_TRAINING_CUT_KST}'
               ) AS pre_mh,
               COUNT(*) FILTER (
                   WHERE (td.completed_at AT TIME ZONE 'Asia/Seoul') < TIMESTAMP '{_TRAINING_CUT_KST}'
               ) AS pre_n,
               AVG(td.duration_minutes / 60.0) FILTER (
                   WHERE (td.completed_at AT TIME ZONE 'Asia/Seoul') >= TIMESTAMP '{_TRAINING_CUT_KST}'
               ) AS post_mh,
               COUNT(*) FILTER (
                   WHERE (td.completed_at AT TIME ZONE 'Asia/Seoul') >= TIMESTAMP '{_TRAINING_CUT_KST}'
               ) AS post_n
        FROM app_task_details td
        JOIN plan.product_info p ON p.serial_number = td.serial_number
        WHERE {_CLEAN_CORE}
        GROUP BY td.task_id
        HAVING COUNT(*) FILTER (
                   WHERE (td.completed_at AT TIME ZONE 'Asia/Seoul') < TIMESTAMP '{_TRAINING_CUT_KST}'
               ) >= 5
        ORDER BY pre_n DESC
        LIMIT 10
    """

    params = {"lookback_days": lookback_days}
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(src_sql, params)
            src_rows = cur.fetchall()
            cur.execute(trend_sql, {})
            trend_rows = cur.fetchall()
            cur.execute(train_sql, {})
            train_rows = cur.fetchall()
    finally:
        put_conn(conn)

    src_total = sum(int(r["n"]) for r in src_rows) or 1
    duration_source_dist = [
        {
            "source": r["source"],
            "n": int(r["n"]),
            "pct": _r(int(r["n"]) / src_total * 100),
            "clean": r["source"] in _CLEAN_SOURCES,
        }
        for r in src_rows
    ]

    auto_close_trend = []
    for r in trend_rows:
        total = int(r["total"])
        auto = int(r["auto"])
        force = int(r["force"])
        auto_close_trend.append({
            "month": r["month"],
            "total": total,
            "normal": total - auto - force,
            "auto": auto,
            "force": force,
            "auto_rate": _r(auto / total * 100) if total else 0.0,
        })

    training_impact = []
    for r in train_rows:
        post_n = int(r["post_n"])
        training_impact.append({
            "task_id": r["task_id"],
            "task": _TASK_NAME.get(r["task_id"], r["task_id"]),
            "pre_mh": _r(r["pre_mh"]),
            "post_mh": _r(r["post_mh"]),
            "pre_n": int(r["pre_n"]),
            "post_n": post_n,
            # post 표본 부족 표기 (Codex M-Q8)
            "confidence": "insufficient_sample" if post_n < 30 else "ok",
        })

    result = {
        "duration_source_dist": duration_source_dist,
        "auto_close_trend": auto_close_trend,
        "training_impact": training_impact,
        "meta": {
            "as_of": datetime.now(_KST).isoformat(),
            "lookback_days": lookback_days,
            "training_cut_kst": _TRAINING_CUT_KST,
        },
    }
    _cache_put(cache_key, result)
    return result
