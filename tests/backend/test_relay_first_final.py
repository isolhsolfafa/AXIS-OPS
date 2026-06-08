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
         patch.object(task_detail, 'put_conn'), \
         patch.object(task_detail, 'compute_task_work', return_value={'manhour': 120, 'active': 100, 'ct': 100}):
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
         patch.object(task_detail, 'put_conn'), \
         patch.object(task_detail, 'compute_task_work', return_value={'manhour': 180, 'active': 150, 'ct': 150}):
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
         patch.object(task_detail, 'put_conn'), \
         patch.object(task_detail, 'compute_task_work', return_value={'manhour': 240, 'active': 200, 'ct': 200}):
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
         patch.object(task_detail, 'put_conn'), \
         patch.object(task_detail, 'compute_task_work', return_value={'manhour': 120, 'active': 100, 'ct': 100}):
        mock_cur = MagicMock()
        # 첫 번째 호출: RETURNING id 1건 / 두 번째: None
        # (Sprint 86: compute_task_work mock → UPDATE RETURNING fetchone 만 side_effect 소비)
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


# ═════════════════════════════════════════════════════════════════════════════
# HOTFIX-SPRINT41D-AUTO-FINALIZE-NOT-BLOCKED (v2.15.2, 2026-05-14)
# v2.15.0 결함 catch: complete_work() L363-369 logger.info only + finalize 그대로 유지
#                     → L408 auto_finalize 분기에서 _all_workers_completed=True 시 task close 발생
# 정정 검증: First Final + finalize=False + 한 명 참여 → 즉시 return (relay_mode) 작동
# ═════════════════════════════════════════════════════════════════════════════


def test_ff01b_first_final_solo_worker_auto_finalize_blocked():
    """
    TC-FF-01b (HOTFIX v2.15.2): First Final + 한 명 참여 + finalize=False
      → auto_finalize 분기 진입 X
      → 응답: first_final_blocked=True + relay_mode=True + task_finished=False
      → app_task_details.completed_at = NULL 유지 (재참여 가능)

    v2.15.0 결함 회귀 차단용 TC. L363-378 의 즉시 return 분기 실제 작동 검증.
    """
    from unittest.mock import patch, MagicMock
    from datetime import datetime
    from app.config import Config
    from app.services.task_service import TaskService

    # Mock task — ELEC IF_2 (First Final + Second Final 양쪽 멤버)
    mock_task = MagicMock()
    mock_task.id = 12345
    mock_task.task_category = 'ELEC'
    mock_task.task_id = 'IF_2'
    mock_task.task_name = 'I.F 2 (도킹 후)'
    mock_task.serial_number = 'TEST-SN-001'
    mock_task.qr_doc_id = 'DOC_TEST-SN-001'
    mock_task.worker_id = 100
    mock_task.started_at = datetime(2026, 5, 14, 9, 0, tzinfo=Config.KST)
    mock_task.completed_at = None
    mock_task.is_paused = False
    mock_task.total_pause_minutes = 0

    service = TaskService()

    with patch('app.services.task_service.get_task_by_id', return_value=mock_task), \
         patch('app.services.task_service._worker_has_started_task', return_value=True), \
         patch('app.services.task_service._worker_already_completed_task', return_value=False), \
         patch('app.services.task_service._record_completion_log', return_value=45) as mock_record, \
         patch('app.models.work_pause_log.get_active_pause_by_worker', return_value=None), \
         patch('app.services.task_service._all_workers_completed', return_value=True) as mock_all_done:
        # 핵심: _all_workers_completed=True (한 명 참여 시뮬레이션)
        # v2.15.0 결함이면 → auto_finalize 트리거 → task close
        # v2.15.2 정정 → 즉시 return → task open 유지

        response, status_code = service.complete_work(
            worker_id=100,
            task_detail_id=12345,
            finalize=False,   # ⭐ 핵심 입력
        )

    # 검증 1: status 200
    assert status_code == 200

    # 검증 2: HOTFIX v2.15.3 신규 플래그 (auto_finalize_blocked 범용)
    assert response.get('auto_finalize_blocked') is True, \
        "❌ v2.15.3 옵션 B 회귀 — AUTO_FINALIZE_BLOCKED_TASK_IDS 분기 미작동"
    # v2.15.2 호환 — ELEC IF_2 는 FIRST_FINAL 멤버
    assert response.get('first_final_blocked') is True, \
        "❌ v2.15.2 호환 회귀 — IF_2 는 FIRST_FINAL 멤버"

    # 검증 3: relay_mode 응답
    assert response.get('relay_mode') is True
    assert response.get('task_finished') is False
    assert response.get('category_completed') is False

    # 검증 4: work_completion_log 본인 row 기록 (duration 측정 보장)
    mock_record.assert_called_once()

    # 검증 5: _all_workers_completed 호출 안 됨 (auto_finalize 분기 진입 X)
    mock_all_done.assert_not_called(), \
        "❌ v2.15.0 결함 회귀 — auto_finalize 분기 진입함 (즉시 return 누락)"


def test_ff01c_mech_tank_docking_solo_worker_blocked():
    """TC-FF-01c (HOTFIX v2.15.2): MECH TANK_DOCKING 도 동일 분기 — First Final 만 (SECOND 멤버 아님)"""
    from unittest.mock import patch, MagicMock
    from datetime import datetime
    from app.config import Config
    from app.services.task_service import TaskService

    mock_task = MagicMock()
    mock_task.id = 22222
    mock_task.task_category = 'MECH'
    mock_task.task_id = 'TANK_DOCKING'
    mock_task.task_name = 'Tank Docking'
    mock_task.serial_number = 'GAIA-TEST-001'
    mock_task.qr_doc_id = 'DOC_GAIA-TEST-001'
    mock_task.worker_id = 200
    mock_task.started_at = datetime(2026, 5, 14, 10, 0, tzinfo=Config.KST)
    mock_task.completed_at = None
    mock_task.is_paused = False
    mock_task.total_pause_minutes = 0

    service = TaskService()

    with patch('app.services.task_service.get_task_by_id', return_value=mock_task), \
         patch('app.services.task_service._worker_has_started_task', return_value=True), \
         patch('app.services.task_service._worker_already_completed_task', return_value=False), \
         patch('app.services.task_service._record_completion_log', return_value=15), \
         patch('app.models.work_pause_log.get_active_pause_by_worker', return_value=None), \
         patch('app.services.task_service._all_workers_completed', return_value=True) as mock_all_done:
        response, status_code = service.complete_work(
            worker_id=200,
            task_detail_id=22222,
            finalize=False,
        )

    assert status_code == 200
    # v2.15.3 옵션 B — auto_finalize_blocked 범용 플래그
    assert response.get('auto_finalize_blocked') is True
    # v2.15.2 호환 — TANK_DOCKING 은 FIRST_FINAL 멤버
    assert response.get('first_final_blocked') is True
    assert response.get('relay_mode') is True
    assert response.get('task_finished') is False
    # v2.15.0 결함 회귀 차단 — auto_finalize 분기 미진입
    mock_all_done.assert_not_called()


def test_ff01d_single_final_not_blocked_normal_close():
    """TC-FF-01d (HOTFIX v2.15.2): SINGLE_FINAL (TMS PRESSURE_TEST) 은 차단 X — 정상 종료
       (회귀 방지 — Single Final 영역까지 차단되면 안 됨)"""
    from unittest.mock import patch, MagicMock
    from datetime import datetime
    from app.config import Config
    from app.services.task_service import TaskService

    mock_task = MagicMock()
    mock_task.id = 33333
    mock_task.task_category = 'TMS'
    mock_task.task_id = 'PRESSURE_TEST'
    mock_task.serial_number = 'TEST-SN-003'
    mock_task.qr_doc_id = 'DOC_TEST-SN-003'
    mock_task.worker_id = 300
    mock_task.started_at = datetime(2026, 5, 14, 11, 0, tzinfo=Config.KST)
    mock_task.completed_at = None
    mock_task.is_paused = False
    mock_task.total_pause_minutes = 0

    service = TaskService()

    # Single Final 영역은 finalize=False 호출 시 강제 True 변환 → 정상 close
    with patch('app.services.task_service.get_task_by_id', return_value=mock_task), \
         patch('app.services.task_service._worker_has_started_task', return_value=True), \
         patch('app.services.task_service._worker_already_completed_task', return_value=False), \
         patch('app.services.task_service._record_completion_log', return_value=120), \
         patch('app.models.work_pause_log.get_active_pause_by_worker', return_value=None), \
         patch('app.services.task_service._all_workers_completed', return_value=True), \
         patch('app.services.task_service._finalize_task_multi_worker',
               return_value={'duration_minutes': 120, 'elapsed_minutes': 120, 'worker_count': 1}), \
         patch('app.services.task_service.complete_task', return_value=True), \
         patch('app.services.task_service.complete_task_unified',
               return_value={'duration_minutes': 120, 'elapsed_minutes': 120, 'worker_count': 1}), \
         patch('app.services.duration_validator.validate_duration', return_value={'warnings': []}), \
         patch.object(service, '_trigger_second_close'):
        response, status_code = service.complete_work(
            worker_id=300,
            task_detail_id=33333,
            finalize=False,
        )

    assert status_code == 200
    # Single Final 은 차단 플래그 없음 + 정상 종료
    assert response.get('first_final_blocked') is None
    # v2.15.3 옵션 B — Single Final 영역은 auto_finalize_blocked 미발동
    assert response.get('auto_finalize_blocked') is None
    assert response.get('task_finished') is True


# ═════════════════════════════════════════════════════════════════════════════
# HOTFIX-SPRINT41D-AUTO-FINALIZE-RANGE-EXTENSION (v2.15.3, 2026-05-14)
# 옵션 B Allowlist — AUTO_FINALIZE_BLOCKED_TASK_IDS 11 task 전수 검증
# Codex 라운드 1 A-1 정합 — parametrize 패턴으로 효율적 커버
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize('task_category,task_id,is_first_final_expected', [
    # FIRST_FINAL (2)
    ('MECH', 'TANK_DOCKING', True),
    ('ELEC', 'IF_2', True),
    # MECH 일반 phase (5)
    ('MECH', 'WASTE_GAS_LINE_1', False),
    ('MECH', 'UTIL_LINE_1', False),
    ('MECH', 'WASTE_GAS_LINE_2', False),
    ('MECH', 'UTIL_LINE_2', False),
    ('MECH', 'HEATING_JACKET', False),
    # ELEC 일반 phase (4)
    ('ELEC', 'PANEL_WORK', False),
    ('ELEC', 'CABINET_PREP', False),
    ('ELEC', 'WIRING', False),
    ('ELEC', 'IF_1', False),
])
def test_ff_v2153_auto_finalize_blocked_set_coverage(task_category, task_id, is_first_final_expected):
    """TC-FF-01e~01o (HOTFIX v2.15.3 Issue A): AUTO_FINALIZE_BLOCKED_TASK_IDS 11 task 전수 검증.

    각 task 에 대해:
    1. response.get('auto_finalize_blocked') is True — 범용 플래그
    2. response.get('first_final_blocked') == is_first_final_expected — 호환성 보존
    3. response.get('task_finished') is False — task open 유지
    4. response.get('relay_mode') is True
    5. mock_all_done.assert_not_called() — auto_finalize 분기 미진입 (v2.15.0 결함 회귀 차단)
    """
    from unittest.mock import patch, MagicMock
    from datetime import datetime
    from app.config import Config
    from app.services.task_service import TaskService

    mock_task = MagicMock()
    mock_task.id = 99999
    mock_task.task_category = task_category
    mock_task.task_id = task_id
    mock_task.task_name = f'Test {task_id}'
    mock_task.serial_number = 'TEST-V2153'
    mock_task.qr_doc_id = 'DOC_TEST-V2153'
    mock_task.worker_id = 100
    mock_task.started_at = datetime(2026, 5, 14, 9, 0, tzinfo=Config.KST)
    mock_task.completed_at = None
    mock_task.is_paused = False
    mock_task.total_pause_minutes = 0

    service = TaskService()

    with patch('app.services.task_service.get_task_by_id', return_value=mock_task), \
         patch('app.services.task_service._worker_has_started_task', return_value=True), \
         patch('app.services.task_service._worker_already_completed_task', return_value=False), \
         patch('app.services.task_service._record_completion_log', return_value=45), \
         patch('app.models.work_pause_log.get_active_pause_by_worker', return_value=None), \
         patch('app.services.task_service._all_workers_completed', return_value=True) as mock_all_done:

        response, status_code = service.complete_work(
            worker_id=100,
            task_detail_id=99999,
            finalize=False,
        )

    # 검증 1: status 200
    assert status_code == 200, f"❌ {task_category}/{task_id} status 200 실패"

    # 검증 2: 범용 플래그 (v2.15.3 신규)
    assert response.get('auto_finalize_blocked') is True, \
        f"❌ {task_category}/{task_id} — auto_finalize_blocked 미발동 (옵션 B 회귀)"

    # 검증 3: 호환성 플래그 (v2.15.2 — FIRST_FINAL 영역만 True)
    assert response.get('first_final_blocked') is is_first_final_expected, \
        f"❌ {task_category}/{task_id} — first_final_blocked 호환성 회귀 (기대 {is_first_final_expected})"

    # 검증 4: relay_mode 응답
    assert response.get('relay_mode') is True
    assert response.get('task_finished') is False
    assert response.get('category_completed') is False

    # 검증 5: auto_finalize 분기 미진입 (v2.15.0 결함 회귀 차단)
    mock_all_done.assert_not_called(), \
        f"❌ {task_category}/{task_id} — v2.15.0 결함 회귀 (auto_finalize 분기 진입)"


def test_ff_v2153_second_final_self_inspection_normal_close():
    """TC-FF-01i (HOTFIX v2.15.3): MECH SELF_INSPECTION (SECOND_FINAL) 은 차단 X
    → Sprint 55 (3-C) 강제 finalize=true → 정상 close (Second Close 트리거 호출)
    회귀 방지 — Second Final 영역까지 차단되면 안 됨"""
    from unittest.mock import patch, MagicMock
    from datetime import datetime
    from app.config import Config
    from app.services.task_service import TaskService

    mock_task = MagicMock()
    mock_task.id = 44444
    mock_task.task_category = 'MECH'
    mock_task.task_id = 'SELF_INSPECTION'
    mock_task.serial_number = 'TEST-SECOND'
    mock_task.qr_doc_id = 'DOC_TEST-SECOND'
    mock_task.worker_id = 400
    mock_task.started_at = datetime(2026, 5, 14, 14, 0, tzinfo=Config.KST)
    mock_task.completed_at = None
    mock_task.is_paused = False
    mock_task.total_pause_minutes = 0

    service = TaskService()

    with patch('app.services.task_service.get_task_by_id', return_value=mock_task), \
         patch('app.services.task_service._worker_has_started_task', return_value=True), \
         patch('app.services.task_service._worker_already_completed_task', return_value=False), \
         patch('app.services.task_service._record_completion_log', return_value=60), \
         patch('app.models.work_pause_log.get_active_pause_by_worker', return_value=None), \
         patch('app.services.task_service._all_workers_completed', return_value=True), \
         patch('app.services.task_service._finalize_task_multi_worker',
               return_value={'duration_minutes': 60, 'elapsed_minutes': 60, 'worker_count': 1}), \
         patch('app.services.task_service.complete_task', return_value=True), \
         patch('app.services.task_service.complete_task_unified',
               return_value={'duration_minutes': 120, 'elapsed_minutes': 120, 'worker_count': 1}), \
         patch('app.services.duration_validator.validate_duration', return_value={'warnings': []}), \
         patch('app.services.task_service.check_category_close_eligible', return_value=True), \
         patch.object(service, '_trigger_second_close'):
        # v2.15.6: check_category_close_eligible=True mock (체크리스트 100% 충족 시나리오)
        # → Sprint 55 (3-C) 강제 finalize=true → 정상 close 검증
        response, status_code = service.complete_work(
            worker_id=400,
            task_detail_id=44444,
            finalize=False,
        )

    assert status_code == 200
    # SECOND_FINAL — 차단 플래그 없음 + 정상 close
    assert response.get('auto_finalize_blocked') is None, \
        "❌ SELF_INSPECTION 영역 차단됨 — Sprint 55 (3-C) 분기 도달 실패 회귀"
    assert response.get('first_final_blocked') is None
    assert response.get('task_finished') is True
