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
        # 이 작업자가 이미 이 task를 시작한 경우
        if _worker_has_started_task(task.id, worker_id):
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
        task_detail_id: int
    ) -> Tuple[Dict[str, Any], int]:
        """
        작업 완료 처리 (duration 자동 계산 + completion_status 업데이트)
        Sprint 3: duration_validator 연동

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
        if _worker_already_completed_task(task.id, worker_id):
            return {
                'error': 'TASK_ALREADY_COMPLETED',
                'message': '이미 완료한 작업입니다.'
            }, 400

        # 완료 시간 (KST 기준)
        completed_at = datetime.now(Config.KST)

        # Sprint 9: 일시정지 중인 작업이면 자동 재개 처리
        if task.is_paused:
            from app.models.work_pause_log import get_active_pause, resume_pause
            from app.models.task_detail import set_paused
            active_pause = get_active_pause(task_detail_id)
            if active_pause:
                updated_pause = resume_pause(active_pause.id, completed_at)
                if updated_pause:
                    pause_duration = updated_pause.pause_duration_minutes or 0
                    new_total_pause_minutes = task.total_pause_minutes + pause_duration
                    set_paused(task_detail_id, is_paused=False, total_pause_minutes=new_total_pause_minutes)
                    # task 객체 갱신
                    task = get_task_by_id(task_detail_id)
                else:
                    set_paused(task_detail_id, is_paused=False)
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

        # 아직 완료 안 된 다른 작업자가 있는지 확인 (work_start_log 기준)
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

        # 카테고리 전체 완료 확인 (같은 serial_number + task_category)
        incomplete_tasks = get_incomplete_tasks(task.serial_number, task.task_category)
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

        # Sprint 3: duration 경고가 있으면 응답에 포함
        if duration_warnings:
            response['duration_warnings'] = duration_warnings

        return response, 200

    def _trigger_completion_alerts(self, task) -> None:
        """
        특정 Task 완료 시 연계 알림 트리거 (GAIA 전용)

        트리거 규칙 (CLAUDE.md):
          - TMS PRESSURE_TEST 완료
            → alert_type: TMS_TANK_COMPLETE
            → 수신: 해당 제품의 MECH 관리자 (is_manager=True, role=MECH, 같은 제품)
          - MECH TANK_DOCKING 완료
            → alert_type: TANK_DOCKING_COMPLETE
            → 수신: 해당 제품의 ELEC 관리자

        Args:
            task: 완료된 TaskDetail 객체
        """
        trigger = None

        if task.task_category == 'TMS' and task.task_id == 'PRESSURE_TEST':
            trigger = ('TMS_TANK_COMPLETE', 'MECH', 'TMS 가압검사 완료')
        elif task.task_category == 'MECH' and task.task_id == 'TANK_DOCKING':
            trigger = ('TANK_DOCKING_COMPLETE', 'ELEC', 'Tank Docking 완료')

        if trigger is None:
            return

        alert_type, target_role, action_label = trigger

        try:
            from app.models.alert_log import create_alert
            from app.services.process_validator import get_managers_for_role

            managers = get_managers_for_role(target_role)
            for manager_id in managers:
                alert_id = create_alert(
                    alert_type=alert_type,
                    message=(
                        f"[{task.serial_number}] {action_label}: "
                        f"{task.task_name} 작업이 완료되었습니다."
                    ),
                    serial_number=task.serial_number,
                    qr_doc_id=task.qr_doc_id,
                    triggered_by_worker_id=task.worker_id,
                    target_worker_id=manager_id,
                    target_role=target_role
                )
                if alert_id:
                    logger.info(
                        f"Completion alert created: type={alert_type}, "
                        f"task_id={task.id}, manager_id={manager_id}, alert_id={alert_id}"
                    )
        except Exception as e:
            # 알림 실패가 작업 완료 자체를 방해하지 않도록 로그만 남김
            logger.error(f"Failed to trigger completion alert: {e}")

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
    work_start_log에 기록된 모든 작업자가 work_completion_log에도
    완료 기록이 있는지 확인.

    Args:
        task_detail_id: app_task_details.id

    Returns:
        모든 작업자 완료 시 True
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT COUNT(*) AS started_count
            FROM work_start_log
            WHERE task_id = %s
            """,
            (task_detail_id,)
        )
        started_count = cur.fetchone()['started_count']

        cur.execute(
            """
            SELECT COUNT(*) AS completed_count
            FROM work_completion_log
            WHERE task_id = %s
            """,
            (task_detail_id,)
        )
        completed_count = cur.fetchone()['completed_count']

        # 시작한 작업자가 없으면 단일 작업자 완료로 처리
        if started_count == 0:
            return True

        return completed_count >= started_count

    except PsycopgError as e:
        logger.error(f"_all_workers_completed failed: task_id={task_detail_id}, error={e}")
        return True  # 오류 시 완료로 처리 (작업 블로킹 방지)
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
