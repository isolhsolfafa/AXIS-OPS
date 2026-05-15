"""v2.15.16 pytest 신규 TC — Codex 라운드 1 Q1/Q2/Q3 검증.

Sprint: SPRINT-V2-15-16-MECH-FORCE-CLOSED-PREV-DAY-CAP-20260515
도입: 2026-05-15

검증 영역:
- Q1 (FIX-A X-β): check_mech_completion_all() Phase 1+2 합산 검증
    · TC-V216-08: Phase 1 fail → False
    · TC-V216-09: Phase 2 fail → False
    · TC-V216-10: Phase 1+2 GREEN → True
- Q3 (FIX-C PREV_DAY_CAP): calculate_close_at() 전일 경계 cap
    · TC-V216-01: 시나리오 C (익일 trigger) → started.date() 17:00 cap
    · TC-V216-02: 시나리오 D (주말 후 trigger) → started.date() 17:00 cap
    · TC-V216-03: 시나리오 A (같은 날 정상 근무) → fallback 우선
    · TC-V216-04: 시나리오 B (같은 날 야간) → fallback 우선
    · TC-V216-05: priority 0 > priority 1 (cap 발동 시 orphan_last 무시)
    · TC-V216-06: started 17:00 이후 시작 → 음수 duration 방지 (started 그대로)
    · TC-V216-07: last_started_at=None → cap skip → 기존 동작 보존

Codex 라운드 1 M=5 전수 반영 후 작성.
"""

import sys
from pathlib import Path
from datetime import datetime, time
from unittest.mock import patch, MagicMock

_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest


# ═════════════════════════════════════════════════════════════════════════════
# Q3 — PREV_DAY_CAP (시나리오 A/B/C/D + priority 검증)
# ═════════════════════════════════════════════════════════════════════════════


def test_v216_01_prev_day_cap_scenario_c_next_day_trigger():
    """TC-V216-01 시나리오 C: started 5-14 14:00 + trigger 5-15 09:00 → cap 5-14 17:00 발동."""
    from app.config import Config
    from app.services.duration_calculator import calculate_close_at

    started = datetime(2026, 5, 14, 14, 0, tzinfo=Config.KST)
    trigger = datetime(2026, 5, 15, 9, 0, tzinfo=Config.KST)  # 다음 날 trigger

    close_at, src = calculate_close_at(
        worker_id=999,
        trigger_time=trigger,
        orphan_last_completion_at=None,
        last_started_at=started,
    )

    assert src == 'PREV_DAY_CAP'
    assert close_at == datetime(2026, 5, 14, 17, 0, tzinfo=Config.KST)


def test_v216_02_prev_day_cap_scenario_d_weekend_skip():
    """TC-V216-02 시나리오 D: started 5-10 (금) 14:00 + trigger 5-13 (월) 09:00 → cap 5-10 17:00."""
    from app.config import Config
    from app.services.duration_calculator import calculate_close_at

    started = datetime(2026, 5, 10, 14, 0, tzinfo=Config.KST)  # 금요일
    trigger = datetime(2026, 5, 13, 9, 0, tzinfo=Config.KST)   # 월요일 (3일 후)

    close_at, src = calculate_close_at(
        worker_id=999,
        trigger_time=trigger,
        orphan_last_completion_at=None,
        last_started_at=started,
    )

    assert src == 'PREV_DAY_CAP'
    assert close_at == datetime(2026, 5, 10, 17, 0, tzinfo=Config.KST)


def test_v216_03_prev_day_cap_skipped_same_day_normal():
    """TC-V216-03 시나리오 A (같은 날 정상): cap skip → fallback 우선 (FALLBACK_TRIGGER_DATE_17)."""
    from app.config import Config
    from app.services import duration_calculator

    started = datetime(2026, 5, 14, 9, 0, tzinfo=Config.KST)
    trigger = datetime(2026, 5, 14, 14, 0, tzinfo=Config.KST)  # 같은 날

    with patch.object(duration_calculator, 'get_db_connection') as mock_conn, \
         patch.object(duration_calculator, 'put_conn'):
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = {'check_out': None}
        mock_conn.return_value.cursor.return_value.__enter__.return_value = mock_cur

        close_at, src = duration_calculator.calculate_close_at(
            worker_id=999,
            trigger_time=trigger,
            orphan_last_completion_at=None,
            last_started_at=started,
        )

    # 같은 날 → cap skip → fallback (MIN(17:00, 14:00) = 14:00)
    assert src == 'FALLBACK_TRIGGER_DATE_17'
    assert close_at == datetime(2026, 5, 14, 14, 0, tzinfo=Config.KST)


def test_v216_04_prev_day_cap_skipped_same_day_overtime():
    """TC-V216-04 시나리오 B (같은 날 야간): cap skip → fallback MIN(17:00, 19:00) = 17:00."""
    from app.config import Config
    from app.services import duration_calculator

    started = datetime(2026, 5, 14, 9, 0, tzinfo=Config.KST)
    trigger = datetime(2026, 5, 14, 19, 0, tzinfo=Config.KST)  # 같은 날 야간

    with patch.object(duration_calculator, 'get_db_connection') as mock_conn, \
         patch.object(duration_calculator, 'put_conn'):
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = {'check_out': None}
        mock_conn.return_value.cursor.return_value.__enter__.return_value = mock_cur

        close_at, src = duration_calculator.calculate_close_at(
            worker_id=999,
            trigger_time=trigger,
            orphan_last_completion_at=None,
            last_started_at=started,
        )

    # 같은 날 → cap skip → fallback (MIN(17:00, 19:00) = 17:00)
    assert src == 'FALLBACK_TRIGGER_DATE_17'
    assert close_at == datetime(2026, 5, 14, 17, 0, tzinfo=Config.KST)


def test_v216_05_prev_day_cap_priority_over_normal_completion():
    """TC-V216-05: cap (priority 0) > orphan_last_completion (priority 1).

    익일 trigger 시 orphan_last_completion 있어도 cap 우선.
    이유: orphan_last 가 비정상 시각 (예: 익일) 일 수 있음 → cap 으로 강제 정정.
    """
    from app.config import Config
    from app.services.duration_calculator import calculate_close_at

    started = datetime(2026, 5, 14, 14, 0, tzinfo=Config.KST)
    trigger = datetime(2026, 5, 15, 9, 0, tzinfo=Config.KST)
    orphan_last = datetime(2026, 5, 15, 8, 30, tzinfo=Config.KST)  # 익일

    close_at, src = calculate_close_at(
        worker_id=999,
        trigger_time=trigger,
        orphan_last_completion_at=orphan_last,
        last_started_at=started,
    )

    assert src == 'PREV_DAY_CAP'
    assert close_at == datetime(2026, 5, 14, 17, 0, tzinfo=Config.KST)


def test_v216_06_prev_day_cap_after_17_started_no_negative_duration():
    """TC-V216-06: started 17:00 이후 시작 → cap = started 그대로 (음수 duration 방지).

    예: worker 5-14 18:00 시작 + trigger 5-15 09:00 → cap 5-14 17:00 → started 보다 이전
        → close_at = started 그대로 (duration = 0 보장).
    """
    from app.config import Config
    from app.services.duration_calculator import calculate_close_at, calculate_auto_close_duration

    started = datetime(2026, 5, 14, 18, 0, tzinfo=Config.KST)  # 18:00 야간 시작
    trigger = datetime(2026, 5, 15, 9, 0, tzinfo=Config.KST)

    close_at, src = calculate_close_at(
        worker_id=999,
        trigger_time=trigger,
        orphan_last_completion_at=None,
        last_started_at=started,
    )

    assert src == 'PREV_DAY_CAP'
    # cap (5-14 17:00) < started (5-14 18:00) → started 그대로 사용 (음수 차단)
    assert close_at == started
    # duration = 0 (cap = started → 차이 0)
    duration = calculate_auto_close_duration(close_at, started, 0)
    assert duration == 0


def test_v216_07_last_started_at_none_cap_skipped():
    """TC-V216-07: last_started_at=None → cap skip → 기존 동작 보존 (Q3 회귀 방지)."""
    from app.config import Config
    from app.services.duration_calculator import calculate_close_at

    trigger = datetime(2026, 5, 15, 9, 0, tzinfo=Config.KST)
    orphan_last = datetime(2026, 5, 14, 15, 30, tzinfo=Config.KST)

    close_at, src = calculate_close_at(
        worker_id=999,
        trigger_time=trigger,
        orphan_last_completion_at=orphan_last,
        last_started_at=None,  # 명시적 None
    )

    # cap skip → priority 1 NORMAL_COMPLETION 그대로
    assert src == 'NORMAL_COMPLETION'
    assert close_at == orphan_last


# ═════════════════════════════════════════════════════════════════════════════
# Q1 — check_mech_completion_all() X-β 검증
# ═════════════════════════════════════════════════════════════════════════════


def test_v216_08_check_mech_completion_all_phase1_fail_returns_false():
    """TC-V216-08: Phase 1 미완료 → check_mech_completion_all() False."""
    from app.services import checklist_service

    with patch.object(checklist_service, 'check_mech_completion') as mock_check:
        # 첫 호출 (phase=1) → False, 두 번째 호출은 발생 X
        mock_check.return_value = False
        result = checklist_service.check_mech_completion_all('TEST-SN-001')

    assert result is False
    # Phase 1 fail → Phase 2 호출 skip (short-circuit)
    assert mock_check.call_count == 1
    mock_check.assert_called_with('TEST-SN-001', judgment_phase=1)


def test_v216_09_check_mech_completion_all_phase2_fail_returns_false():
    """TC-V216-09: Phase 1 통과 + Phase 2 미완료 → check_mech_completion_all() False."""
    from app.services import checklist_service

    with patch.object(checklist_service, 'check_mech_completion') as mock_check:
        # 첫 호출 (phase=1) True, 두 번째 호출 (phase=2) False
        mock_check.side_effect = [True, False]
        result = checklist_service.check_mech_completion_all('TEST-SN-002')

    assert result is False
    assert mock_check.call_count == 2
    mock_check.assert_any_call('TEST-SN-002', judgment_phase=1)
    mock_check.assert_any_call('TEST-SN-002', judgment_phase=2)


def test_v216_10_check_mech_completion_all_both_pass_returns_true():
    """TC-V216-10: Phase 1 + Phase 2 모두 통과 → check_mech_completion_all() True."""
    from app.services import checklist_service

    with patch.object(checklist_service, 'check_mech_completion') as mock_check:
        mock_check.side_effect = [True, True]
        result = checklist_service.check_mech_completion_all('TEST-SN-003')

    assert result is True
    assert mock_check.call_count == 2


# ═════════════════════════════════════════════════════════════════════════════
# Q2 — force_closed=False 항상 (signature 호환 검증)
# ═════════════════════════════════════════════════════════════════════════════


def test_v216_11_auto_close_relay_task_force_closed_false_signature():
    """TC-V216-11: auto_close_relay_task signature 보존 — force_closed=False 명시 전달 가능."""
    from app.models import task_detail
    import inspect

    sig = inspect.signature(task_detail.auto_close_relay_task)
    assert 'force_closed' in sig.parameters
    # v2.15.14 default=True 유지 (signature 보존), v2.15.16 호출자 영역 명시 False 전달
    assert sig.parameters['force_closed'].default is True


def test_v216_12_duration_source_enum_includes_prev_day_cap():
    """TC-V216-12: migration 057 영역 PREV_DAY_CAP enum 추가 (코드 영역 사용 가능)."""
    from app.services.duration_calculator import calculate_close_at
    from app.config import Config

    started = datetime(2026, 5, 14, 9, 0, tzinfo=Config.KST)
    trigger = datetime(2026, 5, 15, 9, 0, tzinfo=Config.KST)

    _, src = calculate_close_at(
        worker_id=999,
        trigger_time=trigger,
        orphan_last_completion_at=None,
        last_started_at=started,
    )

    assert src == 'PREV_DAY_CAP'
    # 5 enum 영역 (NORMAL_COMPLETION / ATTENDANCE_OUT / FALLBACK_TRIGGER_DATE_17 / INVALID_WARNING / PREV_DAY_CAP)
    assert src in {
        'NORMAL_COMPLETION', 'ATTENDANCE_OUT',
        'FALLBACK_TRIGGER_DATE_17', 'INVALID_WARNING', 'PREV_DAY_CAP',
    }
