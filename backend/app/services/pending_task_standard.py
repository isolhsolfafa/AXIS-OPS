"""
방치(미종료) 단일 기준 — FEAT-PENDING-DISCIPLINE-REFINE (2026-06-13, Codex 2라운드 GO)

배경: BAT 매니저가 미종료 메뉴에서 갓 시작한 진행중 task 까지 일괄 강제종료(98건 사태).
원인 = 미종료 정의가 일시정지/진행중/방치를 구분 안 함. → "방치"만 미종료로 통일.

방치(abandoned) = 기존 canonical(started + 미완 + applicable + force_closed=FALSE + TEST 제외)
  + ① 활성(미pause) 작업 세션 ≥ 1  (전원 완료/일시정지 = 제외 — 의도적 hold 는 방치 아님)
  + ② 마지막 활동(시작/재개) ≥ 24h 경과
       마지막 활동 = GREATEST(MAX(work_start_log.started_at), MAX(work_pause_log.resumed_at))
       ⚠️ resume 은 work_pause_log.resumed_at 만 update (work_start_log 새 row 없음, Codex R1 M-1/M-2)
       → 밤샘 일시정지 후 재개 = 타이머 리셋(멀티데이 정상 작업 보호).

적용처(단일 정의 공유): discipline openTasks/_query_open_tasks_count + build_open_tasks 큐
  + 대시보드 get_pending_tasks_grouped + OPS 메뉴 admin.get_pending_tasks.
alias 계약: t = app_task_details. PG GREATEST 는 NULL 무시.
"""
from __future__ import annotations

ABANDONED_HOURS = 24

# 마지막 활동 시각 expression (alias t). wsl 없으면 t.started_at fallback.
LAST_ACTIVITY_SQL = (
    "GREATEST("
    "COALESCE((SELECT MAX(wsl_la.started_at) FROM work_start_log wsl_la "
    "WHERE wsl_la.task_id = t.id), t.started_at), "
    "(SELECT MAX(wpl_la.resumed_at) FROM work_pause_log wpl_la "
    "WHERE wpl_la.task_detail_id = t.id)"
    ")"
)

# 활성(미pause) 세션 ≥1 — per-worker: 최신 start > 최신 complete AND 활성 pause 없음
#   (task_service._all_active_workers_paused 패턴 미러, set-based EXISTS)
ACTIVE_UNPAUSED_EXISTS_SQL = (
    "EXISTS ("
    "SELECT 1 FROM work_start_log wsl_ac "
    "WHERE wsl_ac.task_id = t.id "
    "GROUP BY wsl_ac.worker_id "
    "HAVING MAX(wsl_ac.started_at) > COALESCE("
    "(SELECT MAX(wcl_ac.completed_at) FROM work_completion_log wcl_ac "
    "WHERE wcl_ac.task_id = t.id AND wcl_ac.worker_id = wsl_ac.worker_id), "
    "'-infinity'::timestamptz) "
    "AND NOT EXISTS ("
    "SELECT 1 FROM work_pause_log wpl_ac "
    "WHERE wpl_ac.task_detail_id = t.id AND wpl_ac.worker_id = wsl_ac.worker_id "
    "AND wpl_ac.resumed_at IS NULL)"
    ")"
)

# 방치 WHERE 조각 — 기존 canonical 뒤에 AND 로 결합 (caller 가 canonical 적용 책임)
ABANDONED_WHERE_SQL = (
    f"{ACTIVE_UNPAUSED_EXISTS_SQL} "
    f"AND {LAST_ACTIVITY_SQL} < now() - interval '{ABANDONED_HOURS} hours'"
)


def is_task_active_recent(cur, task_detail_id: int) -> bool:
    """force-close audit 태그 판정 — 활성(미pause) 세션 존재 + 마지막 활동 24h 미만.

    True = "진행중 task 를 닫는 중" → close_reason prefix '[활동중 종료]' (차단 X, 추적 O).
    ⚠️ force_closed=TRUE write 와 함께만 사용 (Codex R2 Q4 — 비-force 행 prefix 금지).
    """
    cur.execute(
        f"""
        SELECT 1 FROM app_task_details t
        WHERE t.id = %s
          AND {ACTIVE_UNPAUSED_EXISTS_SQL}
          AND {LAST_ACTIVITY_SQL} >= now() - interval '{ABANDONED_HOURS} hours'
        """,
        (task_detail_id,),
    )
    return cur.fetchone() is not None
