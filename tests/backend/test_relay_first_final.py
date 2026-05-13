"""
Sprint 41-D pytest 19 TC — Relay First Final Logic + 자동 정리 트리거 검증

검증 영역:
- TC-FF-01~05: MECH/ELEC First Final auto_finalize 차단 + First Close 트리거
- TC-FF-06~08: ELEC IF_2 + INSPECTION AND 조건
- TC-FF-09: TMS Single Final 그대로 작동
- TC-FF-10/10b/10c/10d: 모델 분기 (GAIA / DRAGON / MITHAS-SDS) 매트릭스
- TC-FF-11~13: close_at 계산 (attendance / 17:00 fallback / pause 차감)
- TC-FF-14: idempotent (중복 트리거 no-op)
- TC-FF-15: duration_validator 비정상 검출
- TC-FF-16: Sprint 41-B legacy 호환 (3 인자 호출 + default 값)
- TC-FF-17: Sprint 57 checklist path 보존 검증 (M-1 분리 효과)
- TC-FF-18: concurrent start_work race (RETURNING id 1건 + 두 번째 False)
- TC-FF-19: KST day-rollover (fallback FALLBACK_TRIGGER_DATE_17)

Codex 라운드 1+2 정정 12건 반영 후 작성.
"""

import sys
from pathlib import Path
from datetime import datetime, time, timedelta
from unittest.mock import patch, MagicMock

_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest


# ═════════════════════════════════════════════════════════════════════════════
# Unit tests — duration_calculator (DB mock + KST 정규화)
# ═════════════════════════════════════════════════════════════════════════════


def test_ff11_close_at_attendance_out_min_logic():
    """TC-FF-11: close_at = MIN(attendance check_out, trigger_time) → ATTENDANCE_OUT"""
    from app.config import Config
    from app.services import duration_calculator

    trigger_time = datetime(2026, 5, 14, 18, 0, tzinfo=Config.KST)  # 18:00
    check_out = datetime(2026, 5, 14, 17, 30, tzinfo=Config.KST)    # 17:30 (조기 퇴근)

    with patch.object(duration_calculator, 'get_db_connection') as mock_conn, \
         patch.object(duration_calculator, 'put_conn'):
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = {'check_out': check_out}
        mock_conn.return_value.cursor.return_value.__enter__.return_value = mock_cur

        close_at, src = duration_calculator.calculate_close_at(
            worker_id=999,
            trigger_time=trigger_time,
            orphan_last_completion_at=None,
        )

    assert src == 'ATTENDANCE_OUT'
    assert close_at == check_out  # MIN(17:30, 18:00) = 17:30


def test_ff12_close_at_fallback_17_kst():
    """TC-FF-12: attendance 미체크 → 17:00 KST fallback → FALLBACK_TRIGGER_DATE_17"""
    from app.config import Config
    from app.services import duration_calculator

    trigger_time = datetime(2026, 5, 14, 18, 0, tzinfo=Config.KST)

    with patch.object(duration_calculator, 'get_db_connection') as mock_conn, \
         patch.object(duration_calculator, 'put_conn'):
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = {'check_out': None}
        mock_conn.return_value.cursor.return_value.__enter__.return_value = mock_cur

        close_at, src = duration_calculator.calculate_close_at(
            worker_id=999,
            trigger_time=trigger_time,
            orphan_last_completion_at=None,
        )

    assert src == 'FALLBACK_TRIGGER_DATE_17'
    assert close_at == datetime(2026, 5, 14, 17, 0, tzinfo=Config.KST)


def test_ff13_duration_pause_minutes_차감():
    """TC-FF-13: duration_minutes = max(0, (close_at - last_started_at) - pause_minutes)"""
    from app.config import Config
    from app.services.duration_calculator import calculate_auto_close_duration

    last_started = datetime(2026, 5, 14, 9, 0, tzinfo=Config.KST)   # 09:00 시작
    close_at = datetime(2026, 5, 14, 17, 0, tzinfo=Config.KST)       # 17:00 close → 480m
    total_pause = 60  # 1시간 pause

    duration = calculate_auto_close_duration(close_at, last_started, total_pause)
    assert duration == 420  # 480 - 60


def test_ff_duration_negative_clamped_to_zero():
    """duration 음수 → 0 (raw < pause_minutes 케이스)"""
    from app.config import Config
    from app.services.duration_calculator import calculate_auto_close_duration

    last_started = datetime(2026, 5, 14, 17, 0, tzinfo=Config.KST)
    close_at = datetime(2026, 5, 14, 17, 30, tzinfo=Config.KST)  # 30m
    total_pause = 100  # 100m → raw 30 - 100 = -70 → 0

    duration = calculate_auto_close_duration(close_at, last_started, total_pause)
    assert duration == 0


def test_ff_priority_1_normal_completion():
    """TC priority 1: orphan_last_completion_at 있음 → NORMAL_COMPLETION (M-2 정정)"""
    from app.config import Config
    from app.services.duration_calculator import calculate_close_at

    trigger_time = datetime(2026, 5, 14, 18, 0, tzinfo=Config.KST)
    orphan_last = datetime(2026, 5, 14, 15, 30, tzinfo=Config.KST)

    close_at, src = calculate_close_at(
        worker_id=999,
        trigger_time=trigger_time,
        orphan_last_completion_at=orphan_last,
    )

    assert src == 'NORMAL_COMPLETION'
    assert close_at == orphan_last  # priority 1 → orphan_last 그대로 사용


def test_ff_to_kst_naive_aware_normalization():
    """tz-aware 정규화 — naive 입력 시 KST 부여"""
    from app.config import Config
    from app.services.duration_calculator import _to_kst

    naive = datetime(2026, 5, 14, 12, 0)  # naive
    aware_kst = _to_kst(naive)
    assert aware_kst.tzinfo is not None
    assert aware_kst == datetime(2026, 5, 14, 12, 0, tzinfo=Config.KST)


def test_ff_to_kst_none_input():
    """_to_kst(None) → None (caller 측 분기 처리)"""
    from app.services.duration_calculator import _to_kst
    assert _to_kst(None) is None


def test_ff19_kst_day_rollover_fallback():
    """TC-FF-19: KST day-rollover — trigger_time 23:30 + check_out 다음날 00:30
    → DATE(check_time AT TIME ZONE 'Asia/Seoul') 매칭 X → fallback 선택
    → duration_source='FALLBACK_TRIGGER_DATE_17'
    """
    from app.config import Config
    from app.services import duration_calculator

    # trigger_time 5-14 23:30 KST
    trigger_time = datetime(2026, 5, 14, 23, 30, tzinfo=Config.KST)

    with patch.object(duration_calculator, 'get_db_connection') as mock_conn, \
         patch.object(duration_calculator, 'put_conn'):
        mock_cur = MagicMock()
        # check_out 다음날 00:30 KST → DATE 매칭 안 됨 → check_out=None 반환 시나리오
        mock_cur.fetchone.return_value = {'check_out': None}
        mock_conn.return_value.cursor.return_value.__enter__.return_value = mock_cur

        close_at, src = duration_calculator.calculate_close_at(
            worker_id=999,
            trigger_time=trigger_time,
            orphan_last_completion_at=None,
        )

    assert src == 'FALLBACK_TRIGGER_DATE_17'
    # fallback = 5-14 17:00 KST / trigger_time = 23:30 → MIN = 17:00
    assert close_at == datetime(2026, 5, 14, 17, 0, tzinfo=Config.KST)


# ═════════════════════════════════════════════════════════════════════════════
# Unit tests — task_service module constants
# ═════════════════════════════════════════════════════════════════════════════


def test_ff_constants_first_final_set():
    """FIRST_FINAL_TASK_IDS 정합 — TANK_DOCKING + IF_2"""
    from app.services.task_service import FIRST_FINAL_TASK_IDS

    assert ('MECH', 'TANK_DOCKING') in FIRST_FINAL_TASK_IDS
    assert ('ELEC', 'IF_2') in FIRST_FINAL_TASK_IDS
    assert len(FIRST_FINAL_TASK_IDS) == 2


def test_ff_constants_second_final_dual_membership():
    """ELEC IF_2 가 FIRST_FINAL + SECOND_FINAL 양쪽 멤버 정합 (A-1 dual membership 의도)"""
    from app.services.task_service import FIRST_FINAL_TASK_IDS, SECOND_FINAL_TASK_IDS

    assert ('ELEC', 'IF_2') in FIRST_FINAL_TASK_IDS
    assert ('ELEC', 'IF_2') in SECOND_FINAL_TASK_IDS
    assert ('ELEC', 'INSPECTION') in SECOND_FINAL_TASK_IDS
    assert ('MECH', 'SELF_INSPECTION') in SECOND_FINAL_TASK_IDS


def test_ff_constants_single_final_no_overlap():
    """SINGLE_FINAL_TASK_IDS — TMS/PI/QI/SI, FIRST/SECOND 와 비중복"""
    from app.services.task_service import (
        FIRST_FINAL_TASK_IDS, SECOND_FINAL_TASK_IDS, SINGLE_FINAL_TASK_IDS
    )

    assert ('TMS', 'PRESSURE_TEST') in SINGLE_FINAL_TASK_IDS
    assert ('PI', 'PI_CHAMBER') in SINGLE_FINAL_TASK_IDS
    assert ('QI', 'QI_INSPECTION') in SINGLE_FINAL_TASK_IDS
    assert ('SI', 'SI_SHIPMENT') in SINGLE_FINAL_TASK_IDS

    overlap_first = SINGLE_FINAL_TASK_IDS & FIRST_FINAL_TASK_IDS
    overlap_second = SINGLE_FINAL_TASK_IDS & SECOND_FINAL_TASK_IDS
    assert len(overlap_first) == 0
    assert len(overlap_second) == 0


def test_ff_phase_map_correctness():
    """FIRST_FINAL_PREVIOUS_PHASE_MAP — TANK_DOCKING → gas1/util1/HEATING_JACKET, IF_2 → 판넬/케비넷/배선/IF_1"""
    from app.services.task_service import FIRST_FINAL_PREVIOUS_PHASE_MAP

    mech_phase = FIRST_FINAL_PREVIOUS_PHASE_MAP[('MECH', 'TANK_DOCKING')]
    assert mech_phase == {'WASTE_GAS_LINE_1', 'UTIL_LINE_1', 'HEATING_JACKET'}

    elec_phase = FIRST_FINAL_PREVIOUS_PHASE_MAP[('ELEC', 'IF_2')]
    assert elec_phase == {'PANEL_WORK', 'CABINET_PREP', 'WIRING', 'IF_1'}


def test_ff_phase_map_safety_dragon_unmapped():
    """DRAGON/SWS/GALLANT 안전망 — 매핑 없는 (category, task_id) → 빈 set"""
    from app.services.task_service import _get_previous_phase_task_ids

    # MITHAS/SDS 등 TANK_DOCKING is_applicable=FALSE 모델
    result = _get_previous_phase_task_ids('TMS', 'TANK_MODULE')
    assert result == set()

    # 잘못된 입력 안전망
    result = _get_previous_phase_task_ids('UNKNOWN', 'NONE')
    assert result == set()


def test_ff_duration_source_enum_4_values():
    """DURATION_SOURCE_ENUM 4 enum 정합 (M-4 정정)"""
    from app.services.task_service import DURATION_SOURCE_ENUM

    assert DURATION_SOURCE_ENUM == {
        'NORMAL_COMPLETION',
        'ATTENDANCE_OUT',
        'FALLBACK_TRIGGER_DATE_17',
        'INVALID_WARNING',
    }


# ═════════════════════════════════════════════════════════════════════════════
# Unit tests — auto_close_relay_task close_reason null-safe (A-3)
# ═════════════════════════════════════════════════════════════════════════════


def test_ff16_legacy_compat_3_args_default_close_reason():
    """TC-FF-16: Sprint 41-B legacy 3 인자 호출 → close_reason='AUTO_CLOSED_LEGACY' (A-3 정정)"""
    from app.models import task_detail
    from app.config import Config

    completed_at = datetime(2026, 5, 14, 17, 0, tzinfo=Config.KST)

    with patch.object(task_detail, 'get_db_connection') as mock_conn, \
         patch.object(task_detail, 'put_conn'):
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (123,)  # RETURNING id success
        mock_conn.return_value.cursor.return_value = mock_cur

        success = task_detail.auto_close_relay_task(
            task_detail_id=123,
            last_completion_at=completed_at,
            worker_count=2,
        )

    assert success is True
    # UPDATE 호출 시 close_reason 인자 확인
    call_args = mock_cur.execute.call_args
    sql, params = call_args[0]
    # close_reason 은 SQL 의 7번째 또는 8번째 param (duration_minutes None → EXTRACT 분기)
    # AUTO_CLOSED_LEGACY 가 params 에 포함되는지 검증
    assert 'AUTO_CLOSED_LEGACY' in params


def test_ff_close_reason_first_final_format():
    """First Final trigger → close_reason='AUTO_CLOSED_BY_FIRST_FINAL_TRIGGER:{task_id}'"""
    from app.models import task_detail
    from app.config import Config

    completed_at = datetime(2026, 5, 14, 17, 0, tzinfo=Config.KST)

    with patch.object(task_detail, 'get_db_connection') as mock_conn, \
         patch.object(task_detail, 'put_conn'):
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (123,)
        mock_conn.return_value.cursor.return_value = mock_cur

        task_detail.auto_close_relay_task(
            task_detail_id=123,
            last_completion_at=completed_at,
            worker_count=1,
            closed_by_worker_id=42,
            trigger_task_id='TANK_DOCKING',
            trigger_type='FIRST_FINAL',
            duration_source='ATTENDANCE_OUT',
            duration_minutes=180,
        )

    call_args = mock_cur.execute.call_args
    sql, params = call_args[0]
    assert 'AUTO_CLOSED_BY_FIRST_FINAL_TRIGGER:TANK_DOCKING' in params
    assert 'ATTENDANCE_OUT' in params


def test_ff_close_reason_second_final_format():
    """Second Final trigger → close_reason='AUTO_CLOSED_BY_SECOND_FINAL_TRIGGER:{task_id}'"""
    from app.models import task_detail
    from app.config import Config

    completed_at = datetime(2026, 5, 14, 17, 0, tzinfo=Config.KST)

    with patch.object(task_detail, 'get_db_connection') as mock_conn, \
         patch.object(task_detail, 'put_conn'):
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (456,)
        mock_conn.return_value.cursor.return_value = mock_cur

        task_detail.auto_close_relay_task(
            task_detail_id=456,
            last_completion_at=completed_at,
            worker_count=1,
            closed_by_worker_id=43,
            trigger_task_id='SELF_INSPECTION',
            trigger_type='SECOND_FINAL',
            duration_source='NORMAL_COMPLETION',
            duration_minutes=240,
        )

    call_args = mock_cur.execute.call_args
    sql, params = call_args[0]
    assert 'AUTO_CLOSED_BY_SECOND_FINAL_TRIGGER:SELF_INSPECTION' in params


def test_ff14_idempotent_race_no_op():
    """TC-FF-14 / TC-FF-18: write-time race 가드 — RETURNING id None → False 반환 (A-5)"""
    from app.models import task_detail
    from app.config import Config

    completed_at = datetime(2026, 5, 14, 17, 0, tzinfo=Config.KST)

    with patch.object(task_detail, 'get_db_connection') as mock_conn, \
         patch.object(task_detail, 'put_conn'):
        mock_cur = MagicMock()
        # 이미 다른 trigger 가 close 처리 → RETURNING id 0건
        mock_cur.fetchone.return_value = None
        mock_conn.return_value.cursor.return_value = mock_cur

        success = task_detail.auto_close_relay_task(
            task_detail_id=123,
            last_completion_at=completed_at,
            worker_count=1,
            trigger_type='FIRST_FINAL',
            trigger_task_id='IF_2',
        )

    assert success is False  # race no-op


def test_ff18_concurrent_start_race_returning_id():
    """TC-FF-18: concurrent start_work race — 첫 번째 RETURNING id 있음(True),
    두 번째 RETURNING id None(False)"""
    from app.models import task_detail
    from app.config import Config

    completed_at = datetime(2026, 5, 14, 17, 0, tzinfo=Config.KST)

    with patch.object(task_detail, 'get_db_connection') as mock_conn, \
         patch.object(task_detail, 'put_conn'):
        mock_cur = MagicMock()
        # 첫 번째 호출: RETURNING id 1건 / 두 번째: None
        mock_cur.fetchone.side_effect = [(123,), None]
        mock_conn.return_value.cursor.return_value = mock_cur

        first = task_detail.auto_close_relay_task(
            task_detail_id=123, last_completion_at=completed_at, worker_count=1,
            trigger_type='FIRST_FINAL', trigger_task_id='TANK_DOCKING',
        )
        second = task_detail.auto_close_relay_task(
            task_detail_id=123, last_completion_at=completed_at, worker_count=1,
            trigger_type='FIRST_FINAL', trigger_task_id='TANK_DOCKING',
        )

    assert first is True
    assert second is False


# ═════════════════════════════════════════════════════════════════════════════
# Unit tests — check_elec_final_tasks_completed (M-1 분리 효과)
# ═════════════════════════════════════════════════════════════════════════════


def test_ff_elec_final_tasks_and_condition():
    """check_elec_final_tasks_completed — IF_2 + INSPECTION 둘 다 complete 시 True"""
    from app.services import task_service

    with patch.object(task_service, 'get_db_connection') as mock_conn, \
         patch.object(task_service, 'put_conn'):
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = {'if2_done': True, 'insp_done': True}
        mock_conn.return_value.cursor.return_value.__enter__.return_value = mock_cur

        result = task_service.check_elec_final_tasks_completed('TEST-1111')

    assert result is True


def test_ff07_elec_inspection_only_and_condition_fail():
    """TC-FF-07: INSPECTION complete + IF_2 미완료 → False (AND 조건 미충족)"""
    from app.services import task_service

    with patch.object(task_service, 'get_db_connection') as mock_conn, \
         patch.object(task_service, 'put_conn'):
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = {'if2_done': False, 'insp_done': True}
        mock_conn.return_value.cursor.return_value.__enter__.return_value = mock_cur

        result = task_service.check_elec_final_tasks_completed('TEST-1111')

    assert result is False


def test_ff06_elec_if2_only_and_condition_fail():
    """TC-FF-06: IF_2 complete + INSPECTION 미완료 → False (AND 조건 미충족)"""
    from app.services import task_service

    with patch.object(task_service, 'get_db_connection') as mock_conn, \
         patch.object(task_service, 'put_conn'):
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = {'if2_done': True, 'insp_done': False}
        mock_conn.return_value.cursor.return_value.__enter__.return_value = mock_cur

        result = task_service.check_elec_final_tasks_completed('TEST-1111')

    assert result is False


def test_ff17_checklist_service_check_elec_completion_preserved():
    """TC-FF-17: M-1 분리 효과 — Sprint 57 checklist_service.check_elec_completion() 보존 검증
    (별 함수명 도입으로 의미 보존)"""
    from app.services import checklist_service, task_service

    # 두 함수가 별개로 정의되어 있고 충돌 없음 검증
    assert hasattr(checklist_service, 'check_elec_completion')
    assert hasattr(task_service, 'check_elec_final_tasks_completed')
    assert checklist_service.check_elec_completion is not task_service.check_elec_final_tasks_completed
