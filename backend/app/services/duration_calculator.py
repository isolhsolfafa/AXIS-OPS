"""
Sprint 41-D: Relay First Final Logic — close_at 계산 + duration 산출
2026-05-14

v2.15.16 (2026-05-15) — Codex 라운드 1 Q3 M 반영:
- calculate_close_at() 에 last_started_at 인자 추가 (선택)
- 익일/주말 trigger 시 전일 경계 cap 발동 → close_at = started_at 날짜의 17:00 KST
- duration_source enum 'PREV_DAY_CAP' 추가 (migration 056 CHECK constraint 확장 필요)

핵심 함수:
- _to_kst(): naive/aware datetime → KST aware 정규화
- calculate_close_at(): close_at 결정 + duration_source 반환
    priority 0: trigger.date() > started.date() → started.date() 17:00 KST cap → PREV_DAY_CAP
    priority 1: orphan_last_completion_at (work_completion_log 본인 row) → NORMAL_COMPLETION
    priority 2: hr.partner_attendance check_out (해당 worker + trigger_date) → ATTENDANCE_OUT
    priority 3: trigger_date 17:00 KST fallback → FALLBACK_TRIGGER_DATE_17
- calculate_auto_close_duration(): (close_at - last_started_at) - pause_minutes, 음수 차단

Codex 라운드 1+2 정정 반영 (Sprint 41-D):
- M-2 priority 1 (orphan_last_completion_at) + tz-aware 정규화
- M-4 duration_source enum 4종 명시
"""

import logging
from datetime import datetime, time
from typing import Optional, Tuple

from app.config import Config
from app.models.worker import get_db_connection
from app.db_pool import put_conn


logger = logging.getLogger(__name__)


def _to_kst(dt: Optional[datetime]) -> Optional[datetime]:
    """naive datetime → KST aware / aware datetime → KST 변환.

    Sprint 41-D M-2: tz-aware MIN 비교 race 안전성 보장.
    None 입력 → None 반환 (caller 측 분기 처리).
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=Config.KST)
    return dt.astimezone(Config.KST)


def calculate_close_at(
    worker_id: int,
    trigger_time: datetime,
    orphan_last_completion_at: Optional[datetime] = None,
    last_started_at: Optional[datetime] = None,
) -> Tuple[datetime, str]:
    """close_at 결정 + duration_source 반환.

    우선순위 (v2.15.16 — Codex 라운드 1 Q3 cap 추가):
    0️⃣ trigger.date() > started.date() → started.date() 17:00 KST cap (PREV_DAY_CAP)
        — 익일/주말 trigger 시 전일 정규 퇴근시간으로 cap, 18h+ 비정상 duration 차단
    1️⃣ orphan_last_completion_at 있음 (work_completion_log 본인 row) → 그대로 사용 (NORMAL_COMPLETION)
    2️⃣ hr.partner_attendance check_out 있음 → MIN(check_out, trigger_time) (ATTENDANCE_OUT)
    3️⃣ 없으면 → MIN(trigger 발생일 17:00 KST, trigger_time) (FALLBACK_TRIGGER_DATE_17)

    Args:
        worker_id: orphan task 의 worker_id
        trigger_time: trigger task 의 start/complete 시각 (KST aware 권장)
        orphan_last_completion_at: orphan 의 work_completion_log MAX(completed_at) (priority 1 source)
        last_started_at: orphan 의 마지막 시작 시각 (priority 0 cap 판정용, v2.15.16 신규).
                          None 이면 cap skip.

    Returns:
        (close_at, duration_source)
    """
    trigger_time_kst = _to_kst(trigger_time)

    # 0️⃣ v2.15.16 PREV_DAY_CAP — trigger 날짜 > started 날짜 → started 날짜 17:00 KST cap
    if last_started_at is not None:
        last_started_kst = _to_kst(last_started_at)
        if trigger_time_kst.date() > last_started_kst.date():
            cap_at = datetime.combine(last_started_kst.date(), time(17, 0), tzinfo=Config.KST)
            # cap 이 started 보다 이전이면 (예: started 가 17:00 이후) started 시각 그대로 사용 (음수 duration 방지)
            if cap_at <= last_started_kst:
                cap_at = last_started_kst
            return cap_at, 'PREV_DAY_CAP'

    # 1️⃣ orphan 의 work_completion_log 본인 row timestamp 있음 → 그대로 사용 (priority 최우선)
    if orphan_last_completion_at is not None:
        return _to_kst(orphan_last_completion_at), 'NORMAL_COMPLETION'

    # 2️⃣ attendance check_out 조회 (worker_id + trigger_date)
    trigger_date = trigger_time_kst.date()
    conn = None
    check_out = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT MAX(check_time) AS check_out
                  FROM hr.partner_attendance
                 WHERE worker_id = %s
                   AND check_type = 'out'
                   AND DATE(check_time AT TIME ZONE 'Asia/Seoul') = %s
                """,
                (worker_id, trigger_date)
            )
            row = cur.fetchone()
            if row:
                # row 형식 호환 (dict / tuple)
                check_out = row.get('check_out') if isinstance(row, dict) else row[0]
    except Exception as e:
        logger.error(
            f"calculate_close_at attendance query failed: worker_id={worker_id}, "
            f"trigger_date={trigger_date}, error={e}"
        )
        # attendance 조회 실패 → 3️⃣ fallback 으로 자연 fallthrough
    finally:
        if conn is not None:
            put_conn(conn)

    if check_out is not None:
        # MIN(check_out, trigger_time) — 미래 시간 차단, 양쪽 tz-aware 보장
        check_out_kst = _to_kst(check_out)
        close_at = min(check_out_kst, trigger_time_kst)
        return close_at, 'ATTENDANCE_OUT'

    # 3️⃣ 17:00 KST fallback (trigger 발생일 기준)
    fallback_17 = datetime.combine(trigger_date, time(17, 0), tzinfo=Config.KST)
    close_at = min(fallback_17, trigger_time_kst)
    return close_at, 'FALLBACK_TRIGGER_DATE_17'


def calculate_auto_close_duration(
    close_at: datetime,
    last_started_at: Optional[datetime],
    total_pause_minutes: int = 0,
) -> int:
    """auto-close 시 duration_minutes 계산.

    duration_minutes = max(0, (close_at - last_started_at) - total_pause_minutes)
    Sprint 9 pause_minutes 차감 로직 정합.
    duration_validator 가 비정상 검출 시 warning + 별 처리.
    """
    if last_started_at is None:
        return 0
    close_at_kst = _to_kst(close_at)
    last_started_kst = _to_kst(last_started_at)
    raw_minutes = int((close_at_kst - last_started_kst).total_seconds() / 60)
    return max(0, raw_minutes - (total_pause_minutes or 0))
