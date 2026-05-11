"""
Work Batch 서비스 레이어 (Sprint 64-BE v3)

기존 task_service.TaskService.start_work() / complete_work() helper 재사용 —
best-effort sequential pattern. audit log (work_start_log / work_completion_log) +
start guards (is_applicable / phase_block / Location QR) + complete logic (pause/resume /
duration_validator / finalize) 모두 helper 안에서 자동 흡수.

task_service.py 1,551 LOC (⛔ 1,200줄+ CLAUDE.md L545 God File 영역) 분리 정책 정합.
"""
import logging
from typing import Tuple, Dict, Any, List, Optional

from app.db_pool import put_conn
from app.models.worker import get_db_connection

logger = logging.getLogger(__name__)


# ── error 코드 → batch skipped reason 매핑 표 ─────────────

_START_ERROR_TO_REASON = {
    'TASK_NOT_FOUND': 'NOT_FOUND',
    'TASK_NOT_APPLICABLE': 'NOT_APPLICABLE',
    'TASK_ALREADY_STARTED': 'ALREADY_STARTED',
    'TASK_ALREADY_COMPLETED': 'ALREADY_COMPLETED',
    'PHASE_BLOCKED': 'PHASE_BLOCKED',
    'LOCATION_QR_REQUIRED': 'LOCATION_QR_REQUIRED',
    'START_FAILED': 'INTERNAL_ERROR',
}

_COMPLETE_ERROR_TO_REASON = {
    'TASK_NOT_FOUND': 'NOT_FOUND',
    'TASK_NOT_STARTED': 'NOT_STARTED',
    'TASK_ALREADY_COMPLETED': 'ALREADY_COMPLETED',
    'FORBIDDEN': 'FORBIDDEN_WORKER',
    'COMPLETE_FAILED': 'INTERNAL_ERROR',
}


# ── 보조 helper ─────────────────────────────────────────

def _fetch_task_product_map(task_detail_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """pre-loop 단일 JOIN 쿼리 — task_details + product_info (Codex A1 N+1 제거).

    Returns:
        { task_detail_id: { id, task_category, task_id, serial_number, qr_doc_id,
                            started_at, completed_at, is_applicable,
                            mech_partner, module_outsourcing } }
    """
    if not task_detail_ids:
        return {}

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.id, t.task_category, t.task_id, t.serial_number, t.qr_doc_id,
                   t.started_at, t.completed_at, t.is_applicable,
                   p.mech_partner, p.module_outsourcing
              FROM app_task_details t
              LEFT JOIN qr_registry qr ON qr.qr_doc_id = t.qr_doc_id
              LEFT JOIN plan.product_info p ON p.serial_number = qr.serial_number
             WHERE t.id = ANY(%s)
        """, (task_detail_ids,))
        return {row['id']: dict(row) for row in cur.fetchall()}
    finally:
        put_conn(conn)


def _match_manager_company(
    manager_company: Optional[str],
    task_category: str,
    module_outsourcing: Optional[str],
    mech_partner: Optional[str],
) -> bool:
    """Manager 회사 매핑 검증 — work.py L340-356 reactivate 패턴 정합 (Codex M2 정정).

    TMS 카테고리: module_outsourcing OR mech_partner (둘 다 허용)
    MECH 카테고리: mech_partner only
    NULL fallback: 둘 다 NULL → False 반환 (FORBIDDEN_COMPANY 분류)
    PI/QI/SI 영역: 영역 외 → False (whitelist 영역에서 차단되므로 발생 X, 안전 영역)

    ⚠️ substring 매칭 영역 (A-1 BACKLOG): `base in mech` 영역 보존.
       work.py L347 reactivate 패턴 정합 유지. boundary-safe 영역은 별 sprint.
    """
    base = (manager_company or '').upper().replace('(M)', '').replace('(E)', '')
    if not base:
        return False
    mech = (mech_partner or '').upper()
    mod = (module_outsourcing or '').upper()
    if task_category == 'MECH':
        return base == mech or (bool(mech) and base in mech)
    if task_category == 'TMS':
        return (base == mod or (bool(mod) and base in mod)) \
            or (base == mech or (bool(mech) and base in mech))
    return False


def _filter_eligible_ids(
    task_detail_ids: List[int],
    task_map: Dict[int, Dict[str, Any]],
    manager_company: Optional[str],
    skipped: List[Dict[str, Any]],
) -> List[int]:
    """pre-loop 영역 검증 — NOT_FOUND / NOT_TANK_MODULE / FORBIDDEN_COMPANY 분류.

    helper 호출 전 빠른 차단. helper 안의 추가 guards (NOT_APPLICABLE /
    PHASE_BLOCKED / LOCATION_QR_REQUIRED 등) 영역은 main loop 시점에 처리.
    """
    eligible_ids: List[int] = []
    for tid in task_detail_ids:
        row = task_map.get(tid)
        if not row:
            skipped.append({'task_detail_id': tid, 'reason': 'NOT_FOUND'})
            continue
        # Whitelist (Sprint 40 P2): TANK_MODULE in (TMS, MECH)
        if row['task_id'] != 'TANK_MODULE' or row['task_category'] not in ('TMS', 'MECH'):
            skipped.append({'task_detail_id': tid, 'reason': 'NOT_TANK_MODULE'})
            continue
        # Manager 회사 매핑 (Codex M2 — TMS = OR mech_partner)
        if manager_company:
            if not _match_manager_company(
                manager_company, row['task_category'],
                row['module_outsourcing'], row['mech_partner']
            ):
                skipped.append({'task_detail_id': tid, 'reason': 'FORBIDDEN_COMPANY'})
                continue
        eligible_ids.append(tid)
    return eligible_ids


def _is_all_not_tank_module(eligible_ids: List[int], skipped: List[Dict[str, Any]]) -> bool:
    """모두 NOT_TANK_MODULE 영역 차단 — 400 NOT_TANK_MODULE_ANY 반환 조건."""
    return (not eligible_ids and skipped and
            all(s['reason'] == 'NOT_TANK_MODULE' for s in skipped))


# ── main batch endpoint ─────────────────────────────────────

def start_work_batch(
    worker_id: int,
    task_detail_ids: List[int],
    is_admin: bool,
    manager_company: Optional[str],
) -> Tuple[Dict[str, Any], int]:
    """TM Tank Module 일괄 시작 — best-effort sequential helper reuse (v3).

    각 task 마다 기존 TaskService.start_work() 호출 — audit log + start guards +
    alert + worker tracking 모두 자동 흡수. skipped reason 은 helper error 코드 영역
    batch 매핑 표 영역 변환.
    """
    succeeded: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    # 1️⃣ pre-loop: task_details + product_info batch 조회 (N+1 제거)
    task_map = _fetch_task_product_map(task_detail_ids)

    # 2️⃣ pre-loop 검증 (helper 호출 전 빠른 차단)
    eligible_ids = _filter_eligible_ids(
        task_detail_ids, task_map, manager_company, skipped
    )

    # 3️⃣ 모두 NOT_TANK_MODULE 이면 400
    if _is_all_not_tank_module(eligible_ids, skipped):
        return ({'error': 'NOT_TANK_MODULE_ANY',
                 'message': '모든 task 가 TM Tank Module 이 아닙니다.'}, 400)

    # 4️⃣ main loop — helper 재사용 (Codex M1/M3/M4 정합)
    from app.services.task_service import TaskService
    from app.routes.work import _task_to_dict
    from app.models.task_detail import get_task_by_id
    svc = TaskService()

    for tid in eligible_ids:
        result, code = svc.start_work(worker_id=worker_id, task_detail_id=tid)
        if code == 200:
            updated_task = get_task_by_id(tid)
            succeeded.append({
                'task_detail_id': tid,
                'updated': _task_to_dict(updated_task) if updated_task else {},
            })
        else:
            reason = _START_ERROR_TO_REASON.get(result.get('error'), 'UNKNOWN_ERROR')
            skipped.append({'task_detail_id': tid, 'reason': reason})

    return ({
        'succeeded': succeeded,
        'skipped': skipped,
        'total': len(task_detail_ids),
    }, 200)


def complete_work_batch(
    worker_id: int,
    task_detail_ids: List[int],
    is_admin: bool,
    manager_company: Optional[str],
) -> Tuple[Dict[str, Any], int]:
    """TM Tank Module 일괄 완료 — start_work_batch 대칭 (Codex M-4 정정)."""
    succeeded: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    task_map = _fetch_task_product_map(task_detail_ids)

    eligible_ids = _filter_eligible_ids(
        task_detail_ids, task_map, manager_company, skipped
    )

    if _is_all_not_tank_module(eligible_ids, skipped):
        return ({'error': 'NOT_TANK_MODULE_ANY',
                 'message': '모든 task 가 TM Tank Module 이 아닙니다.'}, 400)

    from app.services.task_service import TaskService
    from app.routes.work import _task_to_dict
    from app.models.task_detail import get_task_by_id
    svc = TaskService()

    for tid in eligible_ids:
        result, code = svc.complete_work(
            worker_id=worker_id, task_detail_id=tid, finalize=True
        )
        if code == 200:
            updated_task = get_task_by_id(tid)
            succeeded.append({
                'task_detail_id': tid,
                'updated': _task_to_dict(updated_task) if updated_task else {},
            })
        else:
            reason = _COMPLETE_ERROR_TO_REASON.get(result.get('error'), 'UNKNOWN_ERROR')
            skipped.append({'task_detail_id': tid, 'reason': reason})

    return ({
        'succeeded': succeeded,
        'skipped': skipped,
        'total': len(task_detail_ids),
    }, 200)


def get_tasks_by_order(
    sales_order: str,
    task_categories: List[str],
    task_id: str,
) -> Tuple[Dict[str, Any], int]:
    """FE Sprint 40 prefetch — 같은 O/N TANK_MODULE task 일괄 조회 (N+1 제거)."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.*
              FROM app_task_details t
              LEFT JOIN qr_registry qr ON qr.qr_doc_id = t.qr_doc_id
              LEFT JOIN plan.product_info p ON p.serial_number = qr.serial_number
             WHERE p.sales_order = %s
               AND t.task_category = ANY(%s)
               AND t.task_id = %s
               AND t.is_applicable = TRUE
        """, (sales_order, task_categories, task_id))
        rows = cur.fetchall()
    finally:
        put_conn(conn)

    from app.routes.work import _task_to_dict
    from app.models.task_detail import TaskDetail
    tasks = [_task_to_dict(TaskDetail.from_db_row(r)) for r in rows]
    return ({'tasks': tasks, 'total': len(tasks)}, 200)
