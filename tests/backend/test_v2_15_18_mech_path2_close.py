"""v2.15.18 pytest 신규 TC — MECH Dual-Trigger 경로 2 (체크리스트가 마지막) fix 검증.

Sprint: POST-REVIEW-OPS-65-PATH2-REOPEN-20260515
도입: 2026-05-15

배경 (AXIS-VIEW 측 #65 리뷰 catch):
- M-A4: `_try_mech_close()` 영역 `UPDATE completion_status SET mech_completed=TRUE` 누락
        → 경로 2 close 후 mech_completed=FALSE 잔존 → VIEW 생산현황 "미완료" 표시
- M-A7: `upsert_mech_check()` close 게이트 = `check_mech_completion(sn, judgment_phase)` 단독
        → 1차 검수만 채워도 close → v2.15.16 catch 1 의 경로 2 잔존분
        → `check_mech_completion_all()` (Phase 1+2 합산) 로 게이트 분리

검증 영역:
- TC-P2-A4-01: `_try_mech_close()` 영역 completion_status UPDATE 호출 확인 (M-A4)
- TC-P2-A4-02: UPDATE WHERE mech_completed=FALSE idempotent 가드 확인
- TC-P2-A4-03: SELF_INSPECTION wcl 없음 → close 안 함 + completion_status UPDATE 미발동
- TC-P2-A7-01: upsert_mech_check close 게이트 — check_mech_completion_all() 호출 확인 (M-A7)

Codex 라운드 1 M=2 (M-A4 + M-A7) 합의 후 작성.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest


# ═════════════════════════════════════════════════════════════════════════════
# M-A4 — _try_mech_close() completion_status UPDATE
# ═════════════════════════════════════════════════════════════════════════════


def _make_mech_close_mocks(si_row, orphan_rows):
    """_try_mech_close() 영역 cursor mock — SELECT 2회 (si_row + orphan_rows) 응답."""
    mock_cur = MagicMock()
    # fetchone (si_row), fetchall (orphan_rows) 순서
    mock_cur.fetchone.return_value = si_row
    mock_cur.fetchall.return_value = orphan_rows
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    return mock_conn, mock_cur


def test_p2_a4_01_try_mech_close_updates_completion_status():
    """TC-P2-A4-01: _try_mech_close() 영역 completion_status SET mech_completed=TRUE UPDATE 호출 (M-A4)."""
    from app.services import checklist_service

    si_row = {
        'task_detail_id': 100, 'started_at': None, 'last_completion_at': None,
        'worker_count': 1, 'unfinished_workers_count': 0, 'last_completion_worker_id': 42,
    }
    mock_conn, mock_cur = _make_mech_close_mocks(si_row, [])

    with patch.object(checklist_service, 'get_db_connection', return_value=mock_conn), \
         patch.object(checklist_service, 'put_conn'), \
         patch('app.models.task_detail.auto_close_relay_task', return_value=True):
        result = checklist_service._try_mech_close('TEST-SN-P2-01')

    assert result is True
    # cursor.execute 호출 영역 영역 UPDATE completion_status 포함 확인
    executed_sqls = [str(call.args[0]) for call in mock_cur.execute.call_args_list]
    update_cs = [s for s in executed_sqls if 'UPDATE completion_status' in s and 'mech_completed' in s]
    assert len(update_cs) == 1, \
        f"_try_mech_close() 영역 completion_status mech_completed UPDATE 1회 호출 기대, got {len(update_cs)}"


def test_p2_a4_02_completion_status_update_has_idempotent_guard():
    """TC-P2-A4-02: completion_status UPDATE 영역 WHERE mech_completed=FALSE idempotent 가드 확인."""
    from app.services import checklist_service

    si_row = {
        'task_detail_id': 100, 'started_at': None, 'last_completion_at': None,
        'worker_count': 1, 'unfinished_workers_count': 0, 'last_completion_worker_id': 42,
    }
    mock_conn, mock_cur = _make_mech_close_mocks(si_row, [])

    with patch.object(checklist_service, 'get_db_connection', return_value=mock_conn), \
         patch.object(checklist_service, 'put_conn'), \
         patch('app.models.task_detail.auto_close_relay_task', return_value=True):
        checklist_service._try_mech_close('TEST-SN-P2-02')

    executed_sqls = [str(call.args[0]) for call in mock_cur.execute.call_args_list]
    update_cs = [s for s in executed_sqls if 'UPDATE completion_status' in s][0]
    assert 'mech_completed = FALSE' in update_cs, \
        "completion_status UPDATE 영역 WHERE mech_completed=FALSE idempotent 가드 필요 (ELEC 패턴 정합)"


def test_p2_a4_03_no_self_inspection_wcl_skips_close_and_update():
    """TC-P2-A4-03: SELF_INSPECTION wcl 없음 (si_row None) → close 안 함 + completion_status UPDATE 미발동."""
    from app.services import checklist_service

    mock_conn, mock_cur = _make_mech_close_mocks(None, [])  # si_row None

    with patch.object(checklist_service, 'get_db_connection', return_value=mock_conn), \
         patch.object(checklist_service, 'put_conn'):
        result = checklist_service._try_mech_close('TEST-SN-P2-03')

    assert result is False
    executed_sqls = [str(call.args[0]) for call in mock_cur.execute.call_args_list]
    update_cs = [s for s in executed_sqls if 'UPDATE completion_status' in s]
    assert len(update_cs) == 0, \
        "SELF_INSPECTION wcl 없으면 completion_status UPDATE 미발동 (early return)"


# ═════════════════════════════════════════════════════════════════════════════
# M-A7 — upsert_mech_check() close 게이트 분리
# ═════════════════════════════════════════════════════════════════════════════


def test_p2_a7_01_close_gate_uses_check_mech_completion_all():
    """TC-P2-A7-01: upsert_mech_check close 게이트 — check_mech_completion_all() 호출 확인 (M-A7).

    경로 2 게이트 영역 Phase 1+2 합산 검증. 1차 검수만 채워도 close 되던 버그 fix.
    소스 검증: upsert_mech_check 영역 mech_closed 분기 영역 check_mech_completion_all 사용.
    """
    import inspect
    from app.services import checklist_service

    src = inspect.getsource(checklist_service.upsert_mech_check)
    # close 게이트 영역 check_mech_completion_all 호출 확인
    assert 'check_mech_completion_all(serial_number)' in src, \
        "upsert_mech_check close 게이트 = check_mech_completion_all() (M-A7 — Phase 1+2 합산)"
    # is_complete (FE 진행률 표시용) 영역 phase별 check_mech_completion 유지 확인
    assert 'check_mech_completion(serial_number, judgment_phase)' in src, \
        "is_complete (FE 진행률 표시용) 영역 phase별 check_mech_completion 유지"


def test_p2_a7_02_check_mech_completion_all_gates_path2():
    """TC-P2-A7-02: check_mech_completion_all() — Phase 1 통과 + Phase 2 미완료 → False (경로 2 close 차단)."""
    from app.services import checklist_service

    with patch.object(checklist_service, 'check_mech_completion') as mock_check:
        # phase 1 통과, phase 2 미완료
        mock_check.side_effect = [True, False]
        result = checklist_service.check_mech_completion_all('TEST-SN-P2-A7')

    assert result is False, "1차만 완료 + 2차 미완료 → check_mech_completion_all False → 경로 2 close 차단"
