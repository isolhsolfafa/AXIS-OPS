"""
작업 서비스
Sprint 2: 작업 시작/완료 + completion_status 업데이트 + 공정 검증
Sprint 6 Phase B: 알림 트리거 추가
  - TMS PRESSURE_TEST 완료 → TMS_TANK_COMPLETE → MECH 관리자 알림
  - MECH TANK_DOCKING 완료 → TANK_DOCKING_COMPLETE → ELEC 관리자 알림
Sprint 6 Phase C: 멀티 작업자 duration 계산
  - SUM(worker별 개인 duration) = man-hour (duration_minutes)
  - MAX(completed_at) - MIN(started_at) = 실경과시간 (elapsed_minutes)
  - 마지막 작업자가 완료해야 Task 전체 완료
Sprint 9: 일시정지 중인 작업 완료 시 자동 재개 + duration에서 pause 시간 차감
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta

from app.config import Config
from app.models.task_detail import (
    create_task,
    get_task_by_id,
    get_task_by_serial_and_id,
    get_tasks_by_serial_number,
    start_task,
    complete_task,
    get_incomplete_tasks,
)
from app.models.completion_status import (
    get_or_create_completion_status,
    update_process_completion,
    update_all_completed,
    check_all_processes_completed,
)
from app.models.product_info import (
    get_product_by_qr_doc_id,
)
from app.models.worker import get_db_connection
from psycopg2 import Error as PsycopgError
from app.db_pool import put_conn


logger = logging.getLogger(__name__)

# 유효한 공정 유형 (Sprint 6: MM→MECH, EE→ELEC)
VALID_PROCESS_TYPES = {'MECH', 'ELEC', 'TM', 'PI', 'QI', 'SI'}

# Sprint 41-B: FINAL phase task ID 목록 — 완료 시 릴레이 미완료 task 자동 마감 트리거
FINAL_TASK_IDS = {
    'SELF_INSPECTION',  # MECH 자주검사
    'IF_2',             # ELEC I.F 2 (Sprint 57: INSPECTION→IF_2)
    'PRESSURE_TEST',    # TMS 가압검사
    'PI_CHAMBER',       # PI CHAMBER 가압검사
    'QI_INSPECTION',    # QI 공정검사
    'SI_SHIPMENT',      # SI 출하완료
}


class TaskService:
    """작업 관련 비즈니스 로직"""

    def start_work(
        self,
        worker_id: int,
        task_detail_id: int
    ) -> Tuple[Dict[str, Any], int]:
        """
        작업 시작 처리

        Args:
            worker_id: 작업자 ID
            task_detail_id: 작업 ID

        Returns:
            (response dict, status code)
        """
        # 작업 조회
        task = get_task_by_id(task_detail_id)
        if not task:
            return {
                'error': 'TASK_NOT_FOUND',
                'message': '작업을 찾을 수 없습니다.'
            }, 404

        # Task 적용 여부 확인
        if not task.is_applicable:
            return {
                'error': 'TASK_NOT_APPLICABLE',
                'message': '비활성화된 작업입니다.'
            }, 400

        # Sprint 10: phase_block_enabled — POST_DOCKING task 시작 시 TANK_DOCKING 완료 확인
        # IF_2는 ELEC category이므로 MECH 조건에 걸리지 않음 (차단 대상 아님)
        POST_DOCKING_TASK_IDS = {'WASTE_GAS_LINE_2', 'UTIL_LINE_2', 'IF_2'}
        if task.task_category == 'MECH' and task.task_id in POST_DOCKING_TASK_IDS:
            from app.models.admin_settings import get_setting
            phase_block = get_setting('phase_block_enabled', False)
            if phase_block:
                docking_task = get_task_by_serial_and_id(
                    task.serial_number, 'MECH', 'TANK_DOCKING'
                )
                if docking_task and not docking_task.completed_at:
                    return {
                        'error': 'PHASE_BLOCKED',
                        'message': 'Tank Docking이 완료되지 않았습니다. POST_DOCKING 공정을 시작할 수 없습니다.'
                    }, 400

        # BUG-11 Fix: Location QR 인증 필수 여부 확인
        # task.location_qr_verified는 업데이트되지 않으므로 product.location_qr_id로 체크
        from app.models.admin_settings import get_setting as _get_admin_setting
        location_qr_required = _get_admin_setting('location_qr_required', False)
        logger.info(f"[BUG-11] location_qr_required={location_qr_required}, type={type(location_qr_required)}")
        if location_qr_required:
            product = get_product_by_qr_doc_id(task.qr_doc_id)
            logger.info(
                f"[BUG-11] product.location_qr_id={product.location_qr_id if product else 'NO_PRODUCT'}"
            )
            if product and not product.location_qr_id:
                return {
                    'error': 'LOCATION_QR_REQUIRED',
                    'message': 'Location QR이 등록되지 않았습니다. QR 스캔 화면에서 Location QR을 먼저 스캔해주세요.'
                }, 400

        # 이미 완료된 작업인지 확인
        if task.completed_at:
            return {
                'error': 'TASK_ALREADY_COMPLETED',
                'message': '이미 완료된 작업입니다.'
            }, 400

        # Sprint 6 Phase C: 멀티 작업자 지원
        # Sprint 41: 릴레이 재시작 허용 — 이미 완료한 작업자는 재시작 가능
        if _worker_has_started_task(task.id, worker_id):
            # 릴레이: 이 worker가 이미 완료한 경우 → 재시작 허용
            if _worker_already_completed_task(task.id, worker_id):
                logger.info(
                    f"Relay re-start: task_id={task.id}, worker_id={worker_id}"
                )
            else:
                # 아직 완료 안 한 상태에서 중복 시작 → 차단 (기존 동작)
                return {
                    'error': 'TASK_ALREADY_STARTED',
                    'message': '이미 시작한 작업입니다.'
                }, 400

        # 작업 시작 처리 (KST 기준)
        started_at = datetime.now(Config.KST)

        # 최초 시작자: app_task_details의 started_at, worker_id 설정
        # 2번째+ 작업자: started_at/worker_id는 건드리지 않고 work_start_log에만 기록
        is_first_worker = task.started_at is None

        from app.models.work_start_log import create_work_start_log
        create_work_start_log(
            task_id=task.id,
            worker_id=worker_id,
            serial_number=task.serial_number,
            qr_doc_id=task.qr_doc_id,
            task_category=task.task_category,
            task_id_ref=task.task_id,
            task_name=task.task_name,
            started_at=started_at,
        )

        if is_first_worker:
            if not start_task(task_detail_id, started_at):
                return {
                    'error': 'START_FAILED',
                    'message': '작업 시작 실패'
                }, 500

            # Sprint 63-BE: MECH 체크리스트 1차 입력 토스트 (UTIL_LINE_1/UTIL_LINE_2/WASTE_GAS_LINE_2)
            self._trigger_mech_checklist_alert(task, worker_id)

        logger.info(
            f"Work started: task_id={task_detail_id}, worker_id={worker_id}, "
            f"is_first_worker={is_first_worker}"
        )

        return {
            'message': '작업이 시작되었습니다.',
            'task_id': task_detail_id,
            'started_at': started_at.isoformat()
        }, 200

    def complete_work(
        self,
        worker_id: int,
        task_detail_id: int,
        finalize: bool = True
    ) -> Tuple[Dict[str, Any], int]:
        """
        작업 완료 처리 (duration 자동 계산 + completion_status 업데이트)
        Sprint 3: duration_validator 연동
        Sprint 41: finalize 파라미터 추가 (릴레이 모드 지원)
          finalize=True  (기본): 기존 동작 — 전원 종료 시 task 완료
          finalize=False (릴레이): 내 작업만 종료, task는 열린 상태 유지

        Args:
            worker_id: 작업자 ID
            task_detail_id: 작업 ID
            finalize: True이면 기존 동작, False이면 릴레이 종료

        Returns:
            (response dict, status code)
        """
        # 작업 조회
        task = get_task_by_id(task_detail_id)
        if not task:
            return {
                'error': 'TASK_NOT_FOUND',
                'message': '작업을 찾을 수 없습니다.'
            }, 404

        # Sprint 6 Phase C: 멀티 작업자 지원
        # 이 작업자가 work_start_log에 시작 기록이 있는지 확인
        # (task.worker_id는 최초 시작자만 가리키므로, 2번째+ 작업자는 별도 체크)
        if not _worker_has_started_task(task.id, worker_id):
            # Sprint 11: GST 작업자 간 cross-worker 완료 허용
            from app.models.worker import get_worker_by_id as _get_worker_by_id
            current_worker = _get_worker_by_id(worker_id)
            gst_cross_allowed = False
            if current_worker and current_worker.company == 'GST':
                task_worker = _get_worker_by_id(task.worker_id) if task.worker_id else None
                if task_worker and task_worker.company == 'GST':
                    gst_cross_allowed = True
            if not gst_cross_allowed:
                return {
                    'error': 'FORBIDDEN',
                    'message': '이 작업을 시작하지 않은 작업자입니다.'
                }, 403

        # 시작되지 않은 작업인지 확인
        if not task.started_at:
            return {
                'error': 'TASK_NOT_STARTED',
                'message': '아직 시작되지 않은 작업입니다.'
            }, 400

        # 이미 완료된 작업인지 확인
        if task.completed_at:
            return {
                'error': 'TASK_ALREADY_COMPLETED',
                'message': '이미 완료된 작업입니다.'
            }, 400

        # 이 작업자가 이미 완료 기록을 남긴 경우 확인
        # Sprint 41 Fix: 릴레이 재시작한 경우(last_start > last_completion)는 재완료 허용
        if _worker_already_completed_task(task.id, worker_id):
            if not _worker_restarted_after_completion(task.id, worker_id):
                return {
                    'error': 'TASK_ALREADY_COMPLETED',
                    'message': '이미 완료한 작업입니다.'
                }, 400
            logger.info(
                f"Relay re-completion allowed: task_id={task.id}, worker_id={worker_id}"
            )

        # 완료 시간 (KST 기준)
        completed_at = datetime.now(Config.KST)

        # Sprint 55 (3-C): FINAL task는 finalize=true 강제 (릴레이 불가)
        if task.task_id in FINAL_TASK_IDS and not finalize:
            logger.info(
                f"FINAL task forced finalize: task_id={task_detail_id}, "
                f"task_name={task.task_id}"
            )
            finalize = True

        # Sprint 55 (3-D): 본인의 개인 pause 자동 resume
        # 기존: task.is_paused 기준 (task 전체 pause 여부)
        # 변경: get_active_pause_by_worker() — 본인의 pause만 resume
        from app.models.work_pause_log import get_active_pause_by_worker, resume_pause
        from app.models.task_detail import set_paused
        my_pause = get_active_pause_by_worker(task_detail_id, worker_id)
        if my_pause:
            updated_pause = resume_pause(my_pause.id, completed_at)
            if updated_pause:
                pause_duration = updated_pause.pause_duration_minutes or 0
                new_total_pause_minutes = task.total_pause_minutes + pause_duration
                set_paused(task_detail_id, is_paused=False, total_pause_minutes=new_total_pause_minutes)
                # task 객체 갱신
                task = get_task_by_id(task_detail_id)
            else:
                set_paused(task_detail_id, is_paused=False)
                task = get_task_by_id(task_detail_id)

        # Sprint 6 Phase C: work_completion_log에 이 작업자의 완료 기록 추가
        # (단일 작업자: 직접 complete_task / 멀티 작업자: 로그에만 기록, 마지막이면 complete_task)
        this_worker_duration = _record_completion_log(
            task=task,
            worker_id=worker_id,
            completed_at=completed_at,
        )

        # Sprint 55 (3-B): auto-finalize — 전원 completion_log 도달 시 자동 finalize
        # Sprint 41: 릴레이 모드 — 내 completion_log만 기록하고 task는 열린 상태 유지
        auto_finalized = False
        if not finalize:
            all_workers_done = _all_workers_completed(task.id)
            if all_workers_done:
                # 전원 completion_log 있음 → auto-finalize
                auto_finalized = True
                logger.info(
                    f"Auto-finalize triggered: all workers completed via relay, "
                    f"task_id={task_detail_id}, last_worker={worker_id}"
                )
                # fall-through to finalize logic below (return 하지 않음)
            else:
                logger.info(
                    f"Worker session ended (relay mode): "
                    f"task_id={task_detail_id}, worker_id={worker_id}"
                )
                return {
                    'message': '내 작업이 종료되었습니다. 다른 작업자가 이어서 작업할 수 있습니다.',
                    'task_id': task_detail_id,
                    'completed_at': completed_at.isoformat(),
                    'duration_minutes': this_worker_duration,
                    'category_completed': False,
                    'task_finished': False,
                    'relay_mode': True,
                }, 200

        # 아직 완료 안 된 다른 작업자가 있는지 확인 (work_start_log 기준)
        # auto-finalize된 경우 이미 all_workers_done=True이므로 재호출 스킵
        if auto_finalized:
            all_workers_done = True
        else:
            all_workers_done = _all_workers_completed(task.id)

        if not all_workers_done:
            # 마지막 작업자가 아직 아님 → Task 자체는 미완료 유지
            logger.info(
                f"Work completion logged but task not finished yet: "
                f"task_id={task_detail_id}, worker_id={worker_id}"
            )
            return {
                'message': '작업 완료가 기록되었습니다. 다른 작업자가 완료해야 Task가 종료됩니다.',
                'task_id': task_detail_id,
                'completed_at': completed_at.isoformat(),
                'duration_minutes': this_worker_duration,
                'category_completed': False,
                'task_finished': False,
            }, 200

        # 마지막 작업자 완료 → Task 전체 완료 처리 (멀티 작업자 집계)
        multi_result = _finalize_task_multi_worker(task.id, completed_at)
        duration_minutes = multi_result['duration_minutes']
        elapsed_minutes = multi_result['elapsed_minutes']
        worker_count = multi_result['worker_count']

        # app_task_details 업데이트
        if not complete_task(task_detail_id, completed_at):
            return {
                'error': 'COMPLETE_FAILED',
                'message': '작업 완료 실패'
            }, 500

        logger.info(
            f"Work completed: task_id={task_detail_id}, "
            f"duration={duration_minutes}m, elapsed={elapsed_minutes}m, workers={worker_count}"
        )

        # Sprint 3: duration 검증 (비정상 duration 감지)
        from app.services.duration_validator import validate_duration
        duration_validation = validate_duration(task_detail_id)
        duration_warnings = duration_validation.get('warnings', [])
        if duration_warnings:
            logger.warning(f"Duration validation warnings: task_id={task_detail_id}, warnings={duration_warnings}")

        # Sprint 41-B: FINAL phase task 완료 시 → 릴레이 미완료 task 자동 마감
        if task.task_id in FINAL_TASK_IDS:
            from app.models.task_detail import get_orphan_relay_tasks, auto_close_relay_task
            orphans = get_orphan_relay_tasks(task.serial_number, task.task_category)
            auto_closed_count = 0
            for orphan in orphans:
                success = auto_close_relay_task(
                    task_detail_id=orphan['task_detail_id'],
                    last_completion_at=orphan['last_completion_at'],
                    worker_count=orphan['worker_count'],
                )
                if success:
                    auto_closed_count += 1
                    logger.info(
                        f"Auto-closed relay task: task_detail_id={orphan['task_detail_id']}, "
                        f"task_name={orphan['task_name']}, "
                        f"last_completion_at={orphan['last_completion_at']}"
                    )
            if auto_closed_count > 0:
                logger.info(
                    f"Sprint 41-B auto-close: serial_number={task.serial_number}, "
                    f"category={task.task_category}, closed={auto_closed_count}/{len(orphans)}"
                )

            # Sprint 61-BE: ORPHAN_ON_FINAL — 미시작 task 잔존 알림
            # v2.10.3 FIX-ORPHAN-ON-FINAL-DELIVERY (HOTFIX-ALERT-SCHEDULER-DELIVERY 누락 4번째 경로):
            # 2026-04-22 HOTFIX 에서 scheduler_service.py 3곳은 수정했으나 본 경로 누락 →
            # target_worker_id 미지정으로 `role_TMS`/`role_ELEC` room broadcast → 구독자 0
            # → 8건/4일 legacy NULL (2026-04-23~24). scheduler 3곳 표준 패턴 적용.
            from app.models.admin_settings import get_setting as _get_setting_61
            if _get_setting_61('alert_orphan_on_final_enabled', True):
                from app.models.task_detail import get_not_started_tasks
                not_started = get_not_started_tasks(task.serial_number, task.task_category)
                if not_started:
                    from app.services.alert_service import sn_label as _sn_label_61
                    from app.services.alert_service import create_and_broadcast_alert as _create_alert_61
                    from app.services.process_validator import resolve_managers_for_category
                    label = _sn_label_61(task.serial_number)
                    task_names = ', '.join([t['task_name'] for t in not_started])
                    msg = (
                        f"{label} {task.task_category} {task.task_name} 완료 — "
                        f"미시작 작업 {len(not_started)}건 존재: {task_names}"
                    )
                    managers = resolve_managers_for_category(task.serial_number, task.task_category)
                    for manager_id in managers:
                        _create_alert_61({
                            'alert_type': 'ORPHAN_ON_FINAL',
                            'message': msg,
                            'serial_number': task.serial_number,
                            'qr_doc_id': task.qr_doc_id,
                            'triggered_by_worker_id': worker_id,
                            'target_worker_id': manager_id,
                            'target_role': task.task_category,
                        })
                    logger.info(
                        f"ORPHAN_ON_FINAL: sn={task.serial_number}, "
                        f"not_started={len(not_started)}, managers={len(managers)}"
                    )

        # 카테고리 전체 완료 확인 (같은 serial_number + task_category)
        # BUG-36: TMS DUAL은 qr_doc_id 기준으로 탱크별 독립 완료 판정
        _qr_filter = task.qr_doc_id if task.task_category == 'TMS' else None
        incomplete_tasks = get_incomplete_tasks(task.serial_number, task.task_category, qr_doc_id=_qr_filter)
        category_completed = len(incomplete_tasks) == 0

        # completion_status 업데이트 (카테고리 전체 완료 시, serial_number 기준)
        if category_completed:
            update_process_completion(task.serial_number, task.task_category, True)
            logger.info(f"Category completed: serial_number={task.serial_number}, process={task.task_category}")

            # 모든 공정 완료 확인
            if check_all_processes_completed(task.serial_number):
                update_all_completed(task.serial_number, True, completed_at)
                logger.info(f"All processes completed: serial_number={task.serial_number}")

        # Sprint 6 Phase B: 알림 트리거 (GAIA 전용)
        # TMS PRESSURE_TEST 완료 → MECH 관리자에게 TMS_TANK_COMPLETE 알림
        # MECH TANK_DOCKING 완료 → ELEC 관리자에게 TANK_DOCKING_COMPLETE 알림
        self._trigger_completion_alerts(task)

        # Sprint 52: TM TANK_MODULE 완료 → 체크리스트 준비 알림
        checklist_ready = False
        if task.task_category == 'TMS' and task.task_id == 'TANK_MODULE':
            checklist_ready = self._trigger_tm_checklist_alert(task, worker_id)

        # Sprint 57: ELEC IF_2 완료 → ELEC 닫기 판정 (Dual-Trigger 경로 1)
        elec_close_blocked = False
        if task.task_category == 'ELEC' and task.task_id == 'IF_2':
            from app.services.checklist_service import check_elec_completion
            elec_checklist_complete = check_elec_completion(task.serial_number)
            if elec_checklist_complete:
                logger.info(
                    f"ELEC close triggered (path 1: IF_2 last): "
                    f"serial={task.serial_number}, task_id={task_detail_id}"
                )
            else:
                elec_close_blocked = True
                logger.info(
                    f"ELEC IF_2 completed but checklist incomplete (waiting path 2): "
                    f"serial={task.serial_number}, task_id={task_detail_id}"
                )

        response = {
            'message': '작업이 완료되었습니다.',
            'task_id': task_detail_id,
            'completed_at': completed_at.isoformat(),
            'duration_minutes': duration_minutes,
            'elapsed_minutes': elapsed_minutes,
            'worker_count': worker_count,
            'category_completed': category_completed,
            'task_finished': True,
        }

        # Sprint 55 (3-B): auto-finalize 플래그 — FE가 릴레이 모드와 구분 가능
        if auto_finalized:
            response['auto_finalized'] = True

        # Sprint 52: Manager가 직접 완료한 경우 FE에서 체크리스트 화면 진입 유도
        if checklist_ready:
            response['checklist_ready'] = True

        # Sprint 57: ELEC IF_2 완료 응답에 체크리스트 상태 포함
        if task.task_category == 'ELEC' and task.task_id == 'IF_2':
            response['elec_close_blocked'] = elec_close_blocked
            if elec_close_blocked:
                response['message'] = 'I.F 2 완료 — 체크리스트 미완료 항목이 있습니다.'
                response['checklist_ready'] = True
                response['checklist_category'] = 'ELEC'

        # Sprint 3 / FIX-26: duration 경고는 항상 응답에 포함 (빈 리스트라도 키 존재 보장).
        # API 계약 명확화 — FE 가 data.duration_warnings 키 존재 가정 가능.
        response['duration_warnings'] = duration_warnings

        return response, 200

    def _trigger_completion_alerts(self, task) -> None:
        """
        특정 Task 완료 시 연계 알림 트리거
        Sprint 54: partner 기반 분기 + admin_settings on/off

        트리거 규칙 (공정 흐름 순서):
          trigger①: TMS 완료 → mech_partner company 매니저
            - TMS PRESSURE_TEST 완료 (가압완료)
            - 단, mech_partner = module_outsourcing 회사면 같은 회사이므로 스킵
            - admin_settings: alert_tm_to_mech_enabled
          trigger②: MECH TANK_DOCKING 완료 → elec_partner company 매니저
            - admin_settings: alert_mech_to_elec_enabled
          trigger③: ELEC 자주검사 전체 완료 → PI 매니저 (GST)
            - admin_settings: alert_elec_to_pi_enabled

        Args:
            task: 완료된 TaskDetail 객체
        """
        from app.models.alert_log import create_alert
        from app.services.process_validator import get_managers_by_partner, get_managers_for_role
        from app.models.admin_settings import get_setting
        from app.models.product_info import get_product_by_serial_number
        from app.services.alert_service import sn_label

        trigger = None  # (alert_type, partner_field_or_role, action_label, settings_key)

        # ─── trigger① TMS → MECH (가압완료) ───
        if task.task_id == 'PRESSURE_TEST':
            if task.task_category == 'TMS':
                if self._is_dual_pressure_all_done(task.serial_number):
                    trigger = ('TMS_TANK_COMPLETE', 'mech_partner', 'TMS 가압검사 완료', 'alert_tm_to_mech_enabled')
            elif task.task_category == 'MECH':
                # DRAGON: MECH 가압검사 완료 → QI 매니저
                trigger = ('TMS_TANK_COMPLETE', 'QI', 'MECH 가압검사 완료', 'alert_mech_pressure_to_qi_enabled')

        # Sprint 37-A: TANK_MODULE 완료 + tm_pressure_test_required=false → elec_partner (admin_settings on/off)
        elif task.task_id == 'TANK_MODULE' and task.task_category == 'TMS':
            if not self._is_tm_pressure_test_required():
                trigger = ('TMS_TANK_COMPLETE', 'elec_partner', 'TMS 탱크모듈 완료 (가압검사 제외)', 'alert_tm_tank_module_to_elec_enabled')

        # ─── trigger②: MECH TANK_DOCKING → ELEC (도킹완료) ───
        elif task.task_category == 'MECH' and task.task_id == 'TANK_DOCKING':
            trigger = ('TANK_DOCKING_COMPLETE', 'elec_partner', 'Tank Docking 완료', 'alert_mech_to_elec_enabled')

        # ─── trigger③: ELEC 자주검사 전체 완료 → PI (GST) ───
        elif task.task_category == 'ELEC':
            incomplete_elec = get_incomplete_tasks(task.serial_number, 'ELEC')
            if len(incomplete_elec) == 0:
                trigger = ('ELEC_COMPLETE', 'PI', 'ELEC 자주검사 완료', 'alert_elec_to_pi_enabled')

        if trigger is None:
            return

        alert_type, target_source, action_label, settings_key = trigger

        try:
            # admin_settings on/off 체크
            if not get_setting(settings_key, True):
                logger.info(f"Alert trigger disabled: {settings_key}=false, skipping {alert_type}")
                return

            # partner 기반 매니저 조회 vs role 기반 (QI 등)
            if target_source in ('mech_partner', 'elec_partner', 'module_outsourcing'):
                # ── 같은 회사 스킵 로직 (trigger①) ──
                # mech_partner = module_outsourcing 회사면 같은 협력사 → 알림 불필요
                if target_source == 'mech_partner':
                    product = get_product_by_serial_number(task.serial_number)
                    if product:
                        mech = (product.mech_partner or '').upper()
                        module = (product.module_outsourcing or '').upper()
                        if mech and module and mech == module:
                            logger.info(
                                f"Same company skip: mech_partner={mech} == module_outsourcing={module}, "
                                f"sn={task.serial_number}"
                            )
                            return

                managers = get_managers_by_partner(task.serial_number, target_source)
                target_role_label = target_source  # 로그용
            else:
                # QI, PI 등 role 기반 (GST 단일 회사)
                managers = get_managers_for_role(target_source)
                target_role_label = target_source

            label = sn_label(task.serial_number)
            for manager_id in managers:
                alert_id = create_alert(
                    alert_type=alert_type,
                    message=(
                        f"{label} {action_label}: "
                        f"{task.task_name} 작업이 완료되었습니다."
                    ),
                    serial_number=task.serial_number,
                    qr_doc_id=task.qr_doc_id,
                    triggered_by_worker_id=task.worker_id,
                    target_worker_id=manager_id,
                    target_role=target_role_label
                )
                if alert_id:
                    logger.info(
                        f"Completion alert: type={alert_type}, sn={task.serial_number}, "
                        f"manager={manager_id}, source={target_source}"
                    )

        except Exception as e:
            logger.error(f"Failed to trigger completion alert: {e}")

    def _is_dual_pressure_all_done(self, serial_number: str) -> bool:
        """
        DUAL 모델의 PRESSURE_TEST가 L+R 모두 완료인지 확인.
        SINGLE 모델이면 1건만 있으므로 완료 즉시 True 반환.

        Returns:
            True = 모든 PRESSURE_TEST 완료 (알람 발송 가능)
            False = 아직 미완료 PRESSURE_TEST 있음 (알람 대기)
        """
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT COUNT(*) as incomplete
                FROM app_task_details
                WHERE serial_number = %s
                  AND task_category = 'TMS'
                  AND task_id = 'PRESSURE_TEST'
                  AND completed_at IS NULL
                  AND is_applicable = TRUE
            """, (serial_number,))
            row = cur.fetchone()
            return row['incomplete'] == 0
        except Exception as e:
            logger.error(f"Failed to check dual pressure status: {e}")
            return True  # 에러 시 알람 발송 (안전 방향)
        finally:
            if conn:
                put_conn(conn)

    def _is_tm_pressure_test_required(self) -> bool:
        """admin_settings에서 tm_pressure_test_required 조회"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT setting_value FROM admin_settings
                WHERE setting_key = 'tm_pressure_test_required'
            """)
            row = cur.fetchone()
            if row is None:
                return True
            val = row['setting_value']
            return val.lower() in ('true', '1') if isinstance(val, str) else bool(val)
        except Exception as e:
            logger.error(f"Failed to check tm_pressure_test_required: {e}")
            return True  # default: 가압검사 포함
        finally:
            if conn:
                put_conn(conn)

    def _trigger_tm_checklist_alert(self, task, completing_worker_id: int) -> bool:
        """
        TMS TANK_MODULE 완료 시 체크리스트 준비 알림 처리 (Sprint 52)

        Case A: 완료자(completing_worker_id)가 is_manager=True
          → 알림 미발송, checklist_ready=True 반환 (FE에서 바로 체크리스트 화면으로 이동)

        Case B: 완료자가 일반 작업자(is_manager=False)
          → TMS is_manager에게 CHECKLIST_TM_READY 알림 발송
          → checklist_ready=False 반환

        ⚠️ try-except로 감싸기 — 알림 실패해도 task 완료 정상 처리

        Args:
            task: 완료된 TaskDetail 객체
            completing_worker_id: 완료 요청한 작업자 ID

        Returns:
            True: 완료자가 manager (FE에서 checklist_ready 팝업 표시)
            False: 일반 작업자 또는 알림 처리 완료
        """
        try:
            from app.models.worker import get_worker_by_id as _get_worker_by_id

            completing_worker = _get_worker_by_id(completing_worker_id)
            is_completing_manager = completing_worker and completing_worker.is_manager

            if is_completing_manager:
                # Manager가 직접 완료 → FE에 checklist_ready 플래그만 전달
                logger.info(
                    f"TM TANK_MODULE completed by manager: task_id={task.id}, "
                    f"worker_id={completing_worker_id}, checklist_ready=True"
                )
                return True
            else:
                # 일반 작업자 완료 → module_outsourcing company 매니저에게 알림
                from app.services.process_validator import get_managers_by_partner
                tms_managers = get_managers_by_partner(task.serial_number, 'module_outsourcing')
                from app.models.alert_log import create_alert
                from app.services.alert_service import sn_label as _sn_label
                label = _sn_label(task.serial_number)
                for manager_id in tms_managers:
                    alert_id = create_alert(
                        alert_type='CHECKLIST_TM_READY',
                        message=(
                            f"{label} Tank Module 작업 완료 — "
                            f"체크리스트 검수가 필요합니다"
                        ),
                        serial_number=task.serial_number,
                        qr_doc_id=task.qr_doc_id,
                        triggered_by_worker_id=completing_worker_id,
                        target_worker_id=manager_id,
                        target_role='module_outsourcing',
                    )
                    if alert_id:
                        logger.info(
                            f"CHECKLIST_TM_READY alert: task_id={task.id}, "
                            f"manager_id={manager_id}, alert_id={alert_id}"
                        )
                return False

        except Exception as e:
            # 알림 실패해도 task 완료는 정상 처리
            logger.error(f"_trigger_tm_checklist_alert failed (non-blocking): {e}")
            return False

    def _trigger_mech_checklist_alert(self, task, worker_id: int) -> None:
        """MECH 체크리스트 1차 입력 토스트 알림 (Sprint 63-BE).

        UTIL_LINE_1 / UTIL_LINE_2 / WASTE_GAS_LINE_2 task 시작 시점에 발화.
        매칭 master 항목 (trigger_task_id = 해당 task_id) 1개 이상 존재 시
        시작한 작업자 본인에게 alert INSERT + WebSocket emit.

        ⚠️ try-except 로 감싸기 — 알림 실패해도 task 시작 정상 처리.
        """
        MECH_TRIGGER_TASK_IDS = {'UTIL_LINE_1', 'UTIL_LINE_2', 'WASTE_GAS_LINE_2'}
        if task.task_category != 'MECH' or task.task_id not in MECH_TRIGGER_TASK_IDS:
            return

        try:
            from app.models.worker import get_db_connection
            from app.db_pool import put_conn
            from app.models.alert_log import create_alert
            from app.services.alert_service import sn_label as _sn_label

            conn = get_db_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM checklist.checklist_master
                    WHERE category = 'MECH'
                      AND trigger_task_id = %s
                      AND is_active = TRUE
                    """,
                    (task.task_id,)
                )
                row = cur.fetchone()
                item_count = row['cnt'] if row else 0
            finally:
                put_conn(conn)

            if item_count == 0:
                return

            label = _sn_label(task.serial_number)
            alert_id = create_alert(
                alert_type='CHECKLIST_MECH_READY',
                message=(
                    f"{label} {task.task_name} 작업 시작 — "
                    f"MECH 체크리스트 {item_count}개 항목 입력 가능"
                ),
                serial_number=task.serial_number,
                qr_doc_id=task.qr_doc_id,
                triggered_by_worker_id=worker_id,
                target_worker_id=worker_id,
                target_role='MECH',
            )
            if alert_id:
                logger.info(
                    f"CHECKLIST_MECH_READY alert: task_id={task.id}, "
                    f"worker_id={worker_id}, items={item_count}, alert_id={alert_id}"
                )

        except Exception as e:
            logger.error(f"_trigger_mech_checklist_alert failed (non-blocking): {e}")

    def get_tasks_by_product(
        self,
        qr_doc_id: str,
        task_category: Optional[str] = None
    ) -> Tuple[Dict[str, Any], int]:
        """
        제품별 작업 목록 조회 (역할별 필터링 가능)

        Args:
            qr_doc_id: QR 문서 ID
            task_category: Task 카테고리 (MM, EE, TM, PI, QI, SI), None이면 전체 조회

        Returns:
            (response dict with tasks, status code)
        """
        # 제품 조회
        product = get_product_by_qr_doc_id(qr_doc_id)
        if not product:
            return {
                'error': 'PRODUCT_NOT_FOUND',
                'message': '제품을 찾을 수 없습니다.'
            }, 404

        # task_category 검증
        if task_category and task_category not in VALID_PROCESS_TYPES:
            return {
                'error': 'INVALID_TASK_CATEGORY',
                'message': '유효하지 않은 Task 카테고리입니다.'
            }, 400

        # 작업 목록 조회
        tasks = get_tasks_by_serial_number(product.serial_number, task_category)

        # Task 목록을 dict로 변환
        task_list = []
        for task in tasks:
            task_list.append({
                'id': task.id,
                'task_category': task.task_category,
                'task_id': task.task_id,
                'task_name': task.task_name,
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'duration_minutes': task.duration_minutes,
                'is_applicable': task.is_applicable,
                'task_type': getattr(task, 'task_type', 'NORMAL')
            })

        return {
            'qr_doc_id': qr_doc_id,
            'serial_number': product.serial_number,
            'task_category': task_category,
            'tasks': task_list,
            'total': len(task_list)
        }, 200

    def get_completion_status(self, qr_doc_id: str) -> Tuple[Dict[str, Any], int]:
        """
        제품의 공정 완료 상태 조회

        Args:
            qr_doc_id: QR 문서 ID

        Returns:
            (response dict with completion status, status code)
        """
        # 제품 조회
        product = get_product_by_qr_doc_id(qr_doc_id)
        if not product:
            return {
                'error': 'PRODUCT_NOT_FOUND',
                'message': '제품을 찾을 수 없습니다.'
            }, 404

        # 완료 상태 조회 또는 생성 (serial_number 기준)
        status = get_or_create_completion_status(product.serial_number)
        if not status:
            return {
                'error': 'STATUS_ERROR',
                'message': '완료 상태 조회 실패'
            }, 500

        return {
            'qr_doc_id': qr_doc_id,
            'serial_number': product.serial_number,
            'mech_completed': status.mech_completed,
            'elec_completed': status.elec_completed,
            'tm_completed': status.tm_completed,
            'pi_completed': status.pi_completed,
            'qi_completed': status.qi_completed,
            'si_completed': status.si_completed,
            'all_completed': status.all_completed,
            'all_completed_at': status.all_completed_at.isoformat() if status.all_completed_at else None
        }, 200

    def check_process_prerequisites(
        self,
        qr_doc_id: str,
        process_type: str
    ) -> Tuple[Dict[str, Any], int]:
        """
        공정 시작 전 선행 공정 완료 확인 (PI/QI/SI용)

        Args:
            qr_doc_id: QR 문서 ID
            process_type: 공정 유형 (PI, QI, SI)

        Returns:
            (response dict with validation result, status code)
        """
        # 검사 공정만 검증 필요
        if process_type not in ['PI', 'QI', 'SI']:
            return {
                'message': '선행 공정 검증이 필요하지 않습니다.',
                'can_proceed': True
            }, 200

        # 제품 조회
        product = get_product_by_qr_doc_id(qr_doc_id)
        if not product:
            return {
                'error': 'PRODUCT_NOT_FOUND',
                'message': '제품을 찾을 수 없습니다.'
            }, 404

        # 완료 상태 조회 (serial_number 기준)
        status = get_or_create_completion_status(product.serial_number)
        if not status:
            return {
                'error': 'STATUS_ERROR',
                'message': '완료 상태 조회 실패'
            }, 500

        # 경고 메시지 리스트
        warnings = []

        # MECH(기구) 완료 확인
        if not status.mech_completed:
            warnings.append({
                'type': 'missing_process',
                'process': 'MECH',
                'message': '기구 작업이 아직 완료되지 않았습니다.'
            })

        # ELEC(전장) 완료 확인
        if not status.elec_completed:
            warnings.append({
                'type': 'missing_process',
                'process': 'ELEC',
                'message': '전장 작업이 아직 완료되지 않았습니다.'
            })

        # 경고가 있으면 진행 불가
        can_proceed = len(warnings) == 0

        return {
            'qr_doc_id': qr_doc_id,
            'process_type': process_type,
            'can_proceed': can_proceed,
            'warnings': warnings
        }, 200


# ──────────────────────────────────────────────────────────────
# BUG-8 Fix: 근무시간 계산 (휴게시간 자동 차감)
# ──────────────────────────────────────────────────────────────

# 휴게시간 설정 키 매핑 (admin_settings)
_BREAK_PERIOD_KEYS = [
    ('break_morning_start', 'break_morning_end'),
    ('lunch_start', 'lunch_end'),
    ('break_afternoon_start', 'break_afternoon_end'),
    ('dinner_start', 'dinner_end'),
]


def _calculate_working_minutes(started_at: datetime, completed_at: datetime) -> int:
    """
    근무시간 계산: 총 경과시간에서 휴게시간 겹침을 자동 차감.

    admin_settings에서 4개 휴게시간 구간을 읽어
    [started_at, completed_at] 구간과의 overlap(분)을 계산하고
    raw_minutes에서 차감.

    Args:
        started_at: 작업 시작 시각 (timezone-aware, KST)
        completed_at: 작업 완료 시각 (timezone-aware, KST)

    Returns:
        휴게시간이 차감된 실근무시간(분), 최소 0
    """
    from app.models.admin_settings import get_setting

    raw_minutes = int((completed_at - started_at).total_seconds() / 60)
    if raw_minutes <= 0:
        return 0

    total_break_overlap = 0

    for start_key, end_key in _BREAK_PERIOD_KEYS:
        break_start_str = get_setting(start_key, None)
        break_end_str = get_setting(end_key, None)
        if not break_start_str or not break_end_str:
            continue

        overlap = _calculate_break_overlap(
            started_at, completed_at, break_start_str, break_end_str
        )
        if overlap > 0:
            logger.info(
                f"[WORKING_HOURS] break={start_key}: "
                f"{break_start_str}~{break_end_str}, overlap={overlap}m"
            )
        total_break_overlap += overlap

    net_working_minutes = max(0, raw_minutes - total_break_overlap)
    logger.info(
        f"[WORKING_HOURS] started={started_at}, completed={completed_at}, "
        f"raw_minutes={raw_minutes}, break_overlap={total_break_overlap}, "
        f"net_working_minutes={net_working_minutes}"
    )
    return net_working_minutes


def _calculate_break_overlap(
    work_start: datetime,
    work_end: datetime,
    break_start_str: str,
    break_end_str: str
) -> int:
    """
    작업 구간 [work_start, work_end]과 휴게시간 [break_start, break_end]의
    겹침 시간(분)을 계산.

    작업이 여러 날에 걸치는 경우 각 날의 휴게시간과 개별적으로 겹침을 계산.

    Args:
        work_start: 작업 시작 (timezone-aware)
        work_end: 작업 완료 (timezone-aware)
        break_start_str: 휴게 시작 "HH:MM"
        break_end_str: 휴게 종료 "HH:MM"

    Returns:
        겹침 시간(분), 없으면 0
    """
    try:
        bh, bm = map(int, break_start_str.split(':'))
        eh, em = map(int, break_end_str.split(':'))
    except (ValueError, AttributeError):
        return 0

    total_overlap = 0

    # 작업 시작일부터 완료일까지 각 날짜의 휴게시간과 overlap 계산
    current_date = work_start.date()
    end_date = work_end.date()

    while current_date <= end_date:
        # 해당 날짜의 휴게시간 구간 (KST)
        break_start_dt = work_start.tzinfo.localize(
            datetime(current_date.year, current_date.month, current_date.day, bh, bm)
        ) if hasattr(work_start.tzinfo, 'localize') else datetime(
            current_date.year, current_date.month, current_date.day, bh, bm,
            tzinfo=work_start.tzinfo
        )
        break_end_dt = work_start.tzinfo.localize(
            datetime(current_date.year, current_date.month, current_date.day, eh, em)
        ) if hasattr(work_start.tzinfo, 'localize') else datetime(
            current_date.year, current_date.month, current_date.day, eh, em,
            tzinfo=work_start.tzinfo
        )

        # overlap = max(0, min(work_end, break_end) - max(work_start, break_start))
        overlap_start = max(work_start, break_start_dt)
        overlap_end = min(work_end, break_end_dt)

        if overlap_end > overlap_start:
            total_overlap += int((overlap_end - overlap_start).total_seconds() / 60)

        current_date += timedelta(days=1)

    return total_overlap


# ──────────────────────────────────────────────────────────────
# Sprint 6 Phase C: 멀티 작업자 duration 헬퍼 함수
# ──────────────────────────────────────────────────────────────

def _record_completion_log(task, worker_id: int, completed_at: datetime) -> Optional[int]:
    """
    work_completion_log에 이 작업자의 완료 기록을 추가하고
    이 작업자의 개인 duration(분)을 반환.

    work_start_log에서 이 작업자의 started_at을 찾아 duration 계산.

    Args:
        task: TaskDetail 객체
        worker_id: 완료 작업자 ID
        completed_at: 완료 시각 (timezone-aware)

    Returns:
        이 작업자의 duration_minutes (int), 계산 불가 시 None
    """
    from app.models.work_completion_log import create_work_completion_log

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 이 작업자가 이 task에 대해 시작한 시각 조회
        cur.execute(
            """
            SELECT started_at
            FROM work_start_log
            WHERE task_id = %s AND worker_id = %s
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (task.id, worker_id)
        )
        row = cur.fetchone()
        if row and row['started_at']:
            # BUG-8 Fix: 휴게시간 자동 차감된 실근무시간 계산
            personal_duration = _calculate_working_minutes(row['started_at'], completed_at)
        else:
            personal_duration = None

        create_work_completion_log(
            task_id=task.id,
            worker_id=worker_id,
            serial_number=task.serial_number,
            qr_doc_id=task.qr_doc_id,
            task_category=task.task_category,
            task_id_ref=task.task_id,
            task_name=task.task_name,
            completed_at=completed_at,
            duration_minutes=personal_duration,
        )

        return personal_duration

    except PsycopgError as e:
        logger.error(f"_record_completion_log failed: task_id={task.id}, worker_id={worker_id}, error={e}")
        return None
    finally:
        if conn:
            put_conn(conn)


def _all_workers_completed(task_detail_id: int) -> bool:
    """
    전원 최종 완료 여부 확인 (릴레이 재시작 안전).

    Sprint 55: COUNT(*) 방식 → MAX 타임스탬프 방식으로 변경.
    릴레이 재시작 시 동일 worker가 completion_log 2건 생성해도 정확히 판정.

    판정 기준: 각 worker의 MAX(completed_at) >= MAX(started_at)
    - completion 없음 → 미완료
    - MAX(start) > MAX(completion) → 재시작함 → 미완료
    - MAX(completion) >= MAX(start) → 최종 완료

    Args:
        task_detail_id: app_task_details.id

    Returns:
        모든 작업자 최종 완료 시 True
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            WITH worker_final_status AS (
                SELECT wsl.worker_id,
                       MAX(wsl.started_at) AS last_start,
                       MAX(wcl.completed_at) AS last_complete
                FROM work_start_log wsl
                LEFT JOIN work_completion_log wcl
                    ON wsl.task_id = wcl.task_id AND wsl.worker_id = wcl.worker_id
                WHERE wsl.task_id = %s
                GROUP BY wsl.worker_id
            )
            SELECT
                COUNT(*) AS total_workers,
                COUNT(CASE
                    WHEN last_complete IS NOT NULL
                     AND last_complete >= last_start
                    THEN 1
                END) AS completed_workers
            FROM worker_final_status
            """,
            (task_detail_id,)
        )
        row = cur.fetchone()
        if not row:
            return True  # 시작 기록 없음 → 단일 작업자 완료로 처리

        total_workers = row['total_workers']
        completed_workers = row['completed_workers']

        # 시작한 작업자가 없으면 단일 작업자 완료로 처리
        if total_workers == 0:
            return True

        return total_workers == completed_workers

    except PsycopgError as e:
        logger.error(f"_all_workers_completed failed: task_id={task_detail_id}, error={e}")
        return True  # 오류 시 완료로 처리 (작업 블로킹 방지)
    finally:
        if conn:
            put_conn(conn)


def _all_active_workers_paused(task_detail_id: int) -> bool:
    """
    현재 active worker 전원이 paused 상태인지 확인.

    Sprint 55: 개인별 pause 판정 — task.is_paused = 전원 paused일 때만 true.

    ⚠️ active worker 판정 기준 (릴레이 재시작 안전):
    - completion_log가 없거나
    - MAX(start_log.started_at) > MAX(completion_log.completed_at) (재시작한 경우)

    단독작업자(1인): 본인 pause = task pause (기존 동작 유지)

    Args:
        task_detail_id: app_task_details.id

    Returns:
        active worker 전원이 paused이면 True (active worker 없으면 False)
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            WITH worker_status AS (
                SELECT wsl.worker_id,
                       MAX(wsl.started_at) AS last_start,
                       MAX(wcl.completed_at) AS last_complete
                FROM work_start_log wsl
                LEFT JOIN work_completion_log wcl
                    ON wsl.task_id = wcl.task_id AND wsl.worker_id = wcl.worker_id
                WHERE wsl.task_id = %s
                GROUP BY wsl.worker_id
            ),
            active_workers AS (
                SELECT worker_id
                FROM worker_status
                WHERE last_complete IS NULL
                   OR last_start > last_complete
            ),
            paused_workers AS (
                SELECT DISTINCT worker_id
                FROM work_pause_log
                WHERE task_detail_id = %s AND resumed_at IS NULL
            )
            SELECT
                COUNT(aw.worker_id) AS active_count,
                COUNT(pw.worker_id) AS paused_active_count
            FROM active_workers aw
            LEFT JOIN paused_workers pw ON aw.worker_id = pw.worker_id
            """,
            (task_detail_id, task_detail_id)
        )
        row = cur.fetchone()
        if not row:
            return False

        active_count = row['active_count']
        paused_active_count = row['paused_active_count']

        # active worker가 없으면 False (빈 task에 is_paused=true 방지)
        if active_count == 0:
            return False

        return active_count == paused_active_count

    except PsycopgError as e:
        logger.error(f"_all_active_workers_paused failed: task_id={task_detail_id}, error={e}")
        return False
    finally:
        if conn:
            put_conn(conn)


def _is_worker_paused(task_detail_id: int, worker_id: int) -> bool:
    """
    특정 작업자가 현재 paused 상태인지 확인.

    Sprint 55: 개인별 pause 상태 조회 (my_pause_status 응답용)

    Args:
        task_detail_id: app_task_details.id
        worker_id: 작업자 ID

    Returns:
        해당 worker의 활성 pause가 있으면 True
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT 1 FROM work_pause_log
            WHERE task_detail_id = %s
              AND worker_id = %s
              AND resumed_at IS NULL
            LIMIT 1
            """,
            (task_detail_id, worker_id)
        )
        return cur.fetchone() is not None

    except PsycopgError as e:
        logger.error(
            f"_is_worker_paused failed: task_id={task_detail_id}, "
            f"worker_id={worker_id}, error={e}"
        )
        return False
    finally:
        if conn:
            put_conn(conn)


def _finalize_task_multi_worker(task_detail_id: int, completed_at: datetime) -> Dict[str, Any]:
    """
    멀티 작업자 집계 후 app_task_details 업데이트.

    집계:
      duration_minutes = SUM(work_completion_log.duration_minutes) - total_pause_minutes  ← 순수 man-hour
      elapsed_minutes  = MAX(completed_at) - MIN(started_at)         ← 실경과시간
      worker_count     = COUNT(DISTINCT worker_id FROM work_start_log)

    Sprint 9: duration에서 total_pause_minutes 차감 (최소 0분)

    Args:
        task_detail_id: app_task_details.id
        completed_at: 최종 완료 시각 (timezone-aware)

    Returns:
        {'duration_minutes': int, 'elapsed_minutes': int, 'worker_count': int}
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # man-hour 합계 (work_completion_log)
        cur.execute(
            """
            SELECT COALESCE(SUM(duration_minutes), 0) AS duration_minutes
            FROM work_completion_log
            WHERE task_id = %s
            """,
            (task_detail_id,)
        )
        raw_duration_minutes = int(cur.fetchone()['duration_minutes'])

        # BUG-8 Fix: 수동 pause만 차감 (break auto-pause는 _calculate_working_minutes에서 이미 차감됨)
        # break 자동 일시정지 유형: break_morning, lunch, break_afternoon, dinner
        cur.execute(
            """
            SELECT COALESCE(SUM(pause_duration_minutes), 0) AS manual_pause
            FROM work_pause_log
            WHERE task_detail_id = %s
              AND pause_type NOT IN ('break_morning', 'lunch', 'break_afternoon', 'dinner')
              AND resumed_at IS NOT NULL
            """,
            (task_detail_id,)
        )
        manual_pause_row = cur.fetchone()
        manual_pause_minutes = int(manual_pause_row['manual_pause']) if manual_pause_row else 0
        duration_minutes = max(0, raw_duration_minutes - manual_pause_minutes)

        # 최초 시작 시각 (work_start_log)
        cur.execute(
            """
            SELECT MIN(started_at) AS first_started,
                   COUNT(DISTINCT worker_id) AS worker_count
            FROM work_start_log
            WHERE task_id = %s
            """,
            (task_detail_id,)
        )
        row = cur.fetchone()
        worker_count = int(row['worker_count']) if row['worker_count'] else 1
        first_started = row['first_started']

        if first_started:
            elapsed_minutes = int(
                (completed_at - first_started).total_seconds() / 60
            )
        else:
            elapsed_minutes = duration_minutes  # fallback

        # app_task_details 집계 컬럼 업데이트
        cur.execute(
            """
            UPDATE app_task_details
            SET duration_minutes = %s,
                elapsed_minutes  = %s,
                worker_count     = %s,
                updated_at       = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (duration_minutes, elapsed_minutes, worker_count, task_detail_id)
        )
        conn.commit()

        logger.info(
            f"_finalize_task_multi_worker: task_id={task_detail_id}, "
            f"MH(duration)={duration_minutes}m, CT(elapsed)={elapsed_minutes}m, "
            f"workers={worker_count}, "
            f"line_efficiency={round(duration_minutes * 100 / max(1, elapsed_minutes * worker_count))}%"
        )

        return {
            'duration_minutes': duration_minutes,
            'elapsed_minutes': elapsed_minutes,
            'worker_count': worker_count,
        }

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"_finalize_task_multi_worker failed: task_id={task_detail_id}, error={e}")
        return {
            'duration_minutes': 0,
            'elapsed_minutes': 0,
            'worker_count': 1,
        }
    finally:
        if conn:
            put_conn(conn)


def _worker_has_started_task(task_detail_id: int, worker_id: int) -> bool:
    """
    work_start_log에 이 작업자가 이 task를 시작한 기록이 있는지 확인.
    멀티 작업자 지원: 1번째 이외의 작업자도 완료 가능하도록.

    Args:
        task_detail_id: app_task_details.id
        worker_id: 작업자 ID

    Returns:
        시작 기록 있으면 True
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT 1 FROM work_start_log
            WHERE task_id = %s AND worker_id = %s
            LIMIT 1
            """,
            (task_detail_id, worker_id)
        )
        return cur.fetchone() is not None

    except PsycopgError as e:
        logger.error(f"_worker_has_started_task failed: task_id={task_detail_id}, worker_id={worker_id}, error={e}")
        return False
    finally:
        if conn:
            put_conn(conn)


def _worker_already_completed_task(task_detail_id: int, worker_id: int) -> bool:
    """
    work_completion_log에 이 작업자의 완료 기록이 이미 있는지 확인.

    Args:
        task_detail_id: app_task_details.id
        worker_id: 작업자 ID

    Returns:
        완료 기록 있으면 True
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT 1 FROM work_completion_log
            WHERE task_id = %s AND worker_id = %s
            LIMIT 1
            """,
            (task_detail_id, worker_id)
        )
        return cur.fetchone() is not None

    except PsycopgError as e:
        logger.error(f"_worker_already_completed_task failed: task_id={task_detail_id}, worker_id={worker_id}, error={e}")
        return False
    finally:
        if conn:
            put_conn(conn)


def _worker_restarted_after_completion(task_detail_id: int, worker_id: int) -> bool:
    """
    Sprint 41 Fix: 릴레이 재시작 여부 확인.
    최신 work_start_log.started_at > 최신 work_completion_log.completed_at이면
    릴레이 재시작한 것으로 판단.

    Args:
        task_detail_id: app_task_details.id
        worker_id: 작업자 ID

    Returns:
        릴레이 재시작한 경우 True
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                (SELECT MAX(started_at) FROM work_start_log
                 WHERE task_id = %s AND worker_id = %s) AS last_start,
                (SELECT MAX(completed_at) FROM work_completion_log
                 WHERE task_id = %s AND worker_id = %s) AS last_completion
        """, (task_detail_id, worker_id, task_detail_id, worker_id))

        row = cur.fetchone()
        if not row:
            return False
        last_start = row.get('last_start') if isinstance(row, dict) else row[0]
        last_completion = row.get('last_completion') if isinstance(row, dict) else row[1]
        if not last_start or not last_completion:
            return False

        return last_start > last_completion  # last_start > last_completion → 재시작함

    except PsycopgError as e:
        logger.error(
            f"_worker_restarted_after_completion failed: "
            f"task_id={task_detail_id}, worker_id={worker_id}, error={e}"
        )
        return False
    finally:
        if conn:
            put_conn(conn)
