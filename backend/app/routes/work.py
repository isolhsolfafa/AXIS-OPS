"""
작업 라우트
엔드포인트: /api/app/work/*
Sprint 2: 작업 시작/완료 처리 + Task 목록/완료상태/검증/토글
Sprint 9: 일시정지/재개 엔드포인트 추가
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from typing import Tuple, Dict, Any

from app.config import Config
from app.middleware.jwt_auth import jwt_required, get_current_worker_id, get_current_worker
from app.services.task_service import TaskService
from app.models.task_detail import (
    get_task_by_id, get_tasks_by_serial_number, get_tasks_by_qr_doc_id,
    get_task_by_qr_category_id,
)
from app.models.completion_status import get_or_create_completion_status
from app.models.product_info import get_product_by_serial_number
from app.models.work_pause_log import (
    create_pause,
    resume_pause,
    get_active_pause,
    get_active_pause_by_worker,
    get_pauses_by_task,
)
from app.models.task_detail import set_paused
from app.models.admin_settings import get_all_settings
from app.models.worker import get_worker_by_id, deactivate_worker
from app.db_pool import put_conn


logger = logging.getLogger(__name__)

work_bp = Blueprint("work", __name__, url_prefix="/api/app")
task_service = TaskService()


@work_bp.route("/settings", methods=["GET"])
@jwt_required
def get_app_settings() -> Tuple[Dict[str, Any], int]:
    """
    앱 동작에 필요한 설정값 조회 (일반 작업자 접근 가능)

    admin_required 없이 jwt_required만 적용하여
    QR 스캔 시 location_qr_required 등 앱 설정을 확인할 수 있음

    Headers:
        Authorization: Bearer {token}

    Returns:
        200: {
            "location_qr_required": bool,
            "heating_jacket_enabled": bool,
            "phase_block_enabled": bool,
            "auto_pause_enabled": bool
        }
    """
    settings_list = get_all_settings()

    result: Dict[str, Any] = {}
    for s in settings_list:
        result[s.setting_key] = s.setting_value

    # 앱에 필요한 기본값 보장
    result.setdefault('location_qr_required', True)
    result.setdefault('heating_jacket_enabled', False)
    result.setdefault('phase_block_enabled', False)
    result.setdefault('auto_pause_enabled', True)

    return jsonify(result), 200



def _task_to_dict(task) -> Dict[str, Any]:
    """TaskDetail 객체를 API 응답용 dict로 변환"""
    return {
        'id': task.id,
        'worker_id': task.worker_id or 0,  # Task Seed 초기 상태: NULL → 0
        'serial_number': task.serial_number,
        'qr_doc_id': task.qr_doc_id,
        'task_category': task.task_category,
        'task_id': task.task_id,
        'task_name': task.task_name,
        'process_type': task.task_category,  # FE 호환: task_category를 process_type으로도 제공
        'started_at': task.started_at.isoformat() if task.started_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
        'duration': task.duration_minutes,  # FE 호환: duration_minutes를 duration으로도 제공
        'duration_minutes': task.duration_minutes,
        'is_applicable': task.is_applicable,
        'location_qr_verified': task.location_qr_verified,
        'created_at': task.created_at.isoformat() if task.created_at else None,
        'updated_at': task.updated_at.isoformat() if task.updated_at else None,
        # Sprint 9: 일시정지 상태
        'is_paused': task.is_paused,
        'total_pause_minutes': task.total_pause_minutes,
        # Sprint 27: 단일 액션 Task
        'task_type': getattr(task, 'task_type', 'NORMAL'),
    }


@work_bp.route("/work/start", methods=["POST"])
@jwt_required
def start_work() -> Tuple[Dict[str, Any], int]:
    """
    작업 시작

    Request Body:
        {
            "task_detail_id": int  (또는 "task_id": int)
        }

    Headers:
        Authorization: Bearer {token}

    Response:
        200: 업데이트된 TaskDetail 전체 정보
        400: {"error": "TASK_ALREADY_STARTED", "message": "..."}
        403: {"error": "FORBIDDEN", "message": "..."}
        404: {"error": "TASK_NOT_FOUND", "message": "..."}
    """
    data = request.get_json()

    # 필수 필드 확인
    # - task_detail_id: int (DB PK) → 직접 사용
    # - task_id: int (DB PK 별칭) → 직접 사용
    # - qr_doc_id + task_category + task_id(string) → Sprint 54: qr 기반 task 조회
    task_detail_id = None
    if data:
        raw = data.get('task_detail_id') or data.get('task_id')
        # task_detail_id/task_id가 정수(또는 숫자 문자열)인 경우만 직접 사용
        if raw is not None and str(raw).isdigit():
            task_detail_id = int(raw)

    # qr 기반 조회 분기: task_detail_id가 없고 qr_doc_id + task_category + task_id(문자열) 제공 시
    if not task_detail_id and data:
        qr_doc_id = data.get('qr_doc_id')
        task_category = data.get('task_category')
        task_id_str = data.get('task_id')  # 문자열 task_id (PRESSURE_TEST 등)
        if qr_doc_id and task_category and task_id_str and not str(task_id_str).isdigit():
            task_obj = get_task_by_qr_category_id(qr_doc_id, task_category, task_id_str)
            if task_obj:
                task_detail_id = task_obj.id
            else:
                return jsonify({
                    'error': 'TASK_NOT_FOUND',
                    'message': f'작업을 찾을 수 없습니다: qr_doc_id={qr_doc_id}, category={task_category}, task_id={task_id_str}'
                }), 404

    if not task_detail_id:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'task_detail_id 또는 (qr_doc_id + task_category + task_id)가 필요합니다.'
        }), 400

    # 현재 작업자 ID 추출 (JWT에서)
    worker_id = get_current_worker_id()

    # task_service 호출
    response, status_code = task_service.start_work(
        worker_id=worker_id,
        task_detail_id=task_detail_id
    )

    # 성공 시 업데이트된 전체 TaskDetail 반환
    if status_code == 200:
        updated_task = get_task_by_id(task_detail_id)
        if updated_task:
            result = _task_to_dict(updated_task)
            # Sprint 57: ELEC INSPECTION 시작 → 체크리스트 팝업
            if updated_task.task_category == 'ELEC' and updated_task.task_id == 'INSPECTION':
                result['checklist_ready'] = True
                result['checklist_category'] = 'ELEC'
            return jsonify(result), 200

    return jsonify(response), status_code


@work_bp.route("/work/complete", methods=["POST"])
@jwt_required
def complete_work() -> Tuple[Dict[str, Any], int]:
    """
    작업 완료

    Request Body:
        {
            "task_detail_id": int  (또는 "task_id": int)
        }

    Headers:
        Authorization: Bearer {token}

    Response:
        200: 업데이트된 TaskDetail 전체 정보 + category_completed 플래그
        400: {"error": "TASK_NOT_STARTED|TASK_ALREADY_COMPLETED", "message": "..."}
        403: {"error": "FORBIDDEN", "message": "..."}
        404: {"error": "TASK_NOT_FOUND", "message": "..."}
    """
    data = request.get_json()

    # 필수 필드 확인
    # - task_detail_id: int (DB PK) → 직접 사용
    # - task_id: int (DB PK 별칭) → 직접 사용
    # - qr_doc_id + task_category + task_id(string) → Sprint 54: qr 기반 task 조회
    task_detail_id = None
    if data:
        raw = data.get('task_detail_id') or data.get('task_id')
        # task_detail_id/task_id가 정수(또는 숫자 문자열)인 경우만 직접 사용
        if raw is not None and str(raw).isdigit():
            task_detail_id = int(raw)

    # qr 기반 조회 분기: task_detail_id가 없고 qr_doc_id + task_category + task_id(문자열) 제공 시
    if not task_detail_id and data:
        qr_doc_id = data.get('qr_doc_id')
        task_category = data.get('task_category')
        task_id_str = data.get('task_id')  # 문자열 task_id (PRESSURE_TEST 등)
        if qr_doc_id and task_category and task_id_str and not str(task_id_str).isdigit():
            task_obj = get_task_by_qr_category_id(qr_doc_id, task_category, task_id_str)
            if task_obj:
                task_detail_id = task_obj.id
            else:
                return jsonify({
                    'error': 'TASK_NOT_FOUND',
                    'message': f'작업을 찾을 수 없습니다: qr_doc_id={qr_doc_id}, category={task_category}, task_id={task_id_str}'
                }), 404

    if not task_detail_id:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'task_detail_id 또는 (qr_doc_id + task_category + task_id)가 필요합니다.'
        }), 400

    # Sprint 41: finalize 파라미터 수신 (기본값 True — 하위 호환)
    finalize = data.get('finalize', True) if data else True

    # 현재 작업자 ID 추출 (JWT에서)
    worker_id = get_current_worker_id()

    # task_service 호출
    response, status_code = task_service.complete_work(
        worker_id=worker_id,
        task_detail_id=task_detail_id,
        finalize=finalize
    )

    # 성공 시 업데이트된 전체 TaskDetail 반환
    if status_code == 200:
        updated_task = get_task_by_id(task_detail_id)
        if updated_task:
            result = _task_to_dict(updated_task)
            result['category_completed'] = response.get('category_completed', False)
            result['task_finished'] = response.get('task_finished', True)
            result['relay_mode'] = response.get('relay_mode', False)
            if 'duration_warnings' in response:
                result['duration_warnings'] = response['duration_warnings']
            # Sprint 52: Manager가 TM TANK_MODULE 직접 완료 시 FE 체크리스트 진입 유도
            if response.get('checklist_ready'):
                result['checklist_ready'] = True
            if response.get('checklist_category'):
                result['checklist_category'] = response['checklist_category']
            # Sprint 57: ELEC IF_2 완료 시 체크리스트 상태
            if 'elec_close_blocked' in response:
                result['elec_close_blocked'] = response['elec_close_blocked']
            return jsonify(result), 200

    return jsonify(response), status_code


@work_bp.route("/work/reactivate-task", methods=["POST"])
@jwt_required
def reactivate_task_route() -> Tuple[Dict[str, Any], int]:
    """
    Sprint 41: Manager/Admin이 실수로 완료된 task를 재활성화.

    - app_task_details.completed_at / started_at / worker_id / duration 등 초기화
    - completion_status 롤백 (해당 카테고리 + 전체 완료)
    - production_confirm soft-delete (정합성 유지)
    - work_start_log / work_completion_log 보존 (이력 유지)

    Request Body:
        {"task_detail_id": int}

    Response:
        200: 재활성화 성공
        400: 파라미터 누락 / 이미 진행 중인 task
        403: 권한 없음 (Manager/Admin만)
        404: task 미발견
    """
    data = request.get_json()
    task_detail_id = data.get('task_detail_id') if data else None

    if not task_detail_id:
        return jsonify({'error': 'MISSING_PARAM', 'message': 'task_detail_id 필수'}), 400

    # 권한 체크: Manager 또는 Admin만 허용
    worker = get_current_worker()
    if not worker or (not worker.is_manager and not worker.is_admin):
        return jsonify({'error': 'FORBIDDEN', 'message': '권한이 없습니다.'}), 403

    # task 조회
    task = get_task_by_id(task_detail_id)
    if not task:
        return jsonify({'error': 'TASK_NOT_FOUND', 'message': '작업을 찾을 수 없습니다.'}), 404

    if not task.completed_at:
        return jsonify({'error': 'TASK_NOT_COMPLETED', 'message': '이미 진행 중인 작업입니다.'}), 400

    # Manager: 같은 company 소속 task만 재활성화 가능
    # Fix Sprint 48: company_base 추출 + 비교 방향 수정 (progress_service.py 패턴 일치)
    if worker.is_manager and not worker.is_admin:
        from app.models.product_info import get_product_by_serial_number as _get_product
        product = _get_product(task.serial_number)
        if product:
            company = worker.company or ''
            # TMS(M) → TMS, TMS(E) → TMS 등 접미사 제거
            company_base = company.upper().replace('(M)', '').replace('(E)', '')
            mech_partner = (getattr(product, 'mech_partner', None) or '').upper()
            elec_partner = (getattr(product, 'elec_partner', None) or '').upper()
            module_outsourcing = (getattr(product, 'module_outsourcing', None) or '').upper()
            category = task.task_category
            allowed = False

            if category == 'MECH' and company_base:
                allowed = company_base == mech_partner or company_base in mech_partner

            elif category == 'ELEC' and company_base:
                allowed = company_base == elec_partner or company_base in elec_partner

            elif category == 'TMS' and company_base:
                allowed = (
                    company_base == module_outsourcing or company_base in module_outsourcing
                    or company_base == mech_partner or company_base in mech_partner
                )

            elif category in ('PI', 'QI', 'SI') and company == 'GST':
                allowed = True

            if not allowed:
                return jsonify({'error': 'FORBIDDEN', 'message': '자사 제품이 아닙니다.'}), 403

    # 1. app_task_details 재활성화 (completed_at + started_at 등 초기화)
    from app.models.task_detail import reactivate_task as _reactivate_task
    if not _reactivate_task(task_detail_id):
        return jsonify({'error': 'REACTIVATE_FAILED', 'message': '재활성화 실패'}), 500

    # 2. completion_status 롤백 (카테고리 + 전체 완료)
    from app.models.completion_status import (
        update_process_completion, update_all_completed, check_all_processes_completed
    )
    update_process_completion(task.serial_number, task.task_category, False)
    if not check_all_processes_completed(task.serial_number):
        update_all_completed(task.serial_number, False, None)

    # 3. production_confirm 정합성 — 해당 S/N+공정의 실적확인 soft-delete
    from app.db_pool import get_conn
    conn = get_conn()
    confirm_invalidated = 0
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE plan.production_confirm
            SET deleted_at = NOW(), deleted_by = %s
            WHERE serial_number = %s
              AND process_type = %s
              AND deleted_at IS NULL
        """, (worker.id, task.serial_number, task.task_category))
        confirm_invalidated = cur.rowcount
        conn.commit()
    except Exception as e:
        logger.warning(f"production_confirm soft-delete failed (non-critical): {e}")
        conn.rollback()
    finally:
        put_conn(conn)

    logger.info(
        f"Task reactivated: task_id={task_detail_id}, "
        f"by worker_id={worker.id} (is_manager={worker.is_manager}), "
        f"confirms_invalidated={confirm_invalidated}"
    )

    return jsonify({
        'message': '작업이 재활성화되었습니다.',
        'task_id': task_detail_id,
        'serial_number': task.serial_number,
        'task_category': task.task_category,
        'confirms_invalidated': confirm_invalidated,
    }), 200


@work_bp.route("/work/complete-single", methods=["POST"])
@jwt_required
def complete_single_action_route() -> Tuple[Dict[str, Any], int]:
    """
    단일 액션 Task 완료 API (Sprint 27).

    SINGLE_ACTION type Task는 시작 없이 바로 완료 체크만 수행.
    started_at = completed_at 동시 설정, duration = 0.

    Request Body:
        {"task_detail_id": int}

    Returns:
        200: 완료된 TaskDetail + category_completed
        400: task_type 불일치 / 이미 완료
        404: Task 미발견
    """
    data = request.get_json()
    if not data or 'task_detail_id' not in data:
        return jsonify({
            'error': 'VALIDATION_ERROR',
            'message': 'task_detail_id가 필요합니다.'
        }), 400

    task_detail_id = data['task_detail_id']
    task = get_task_by_id(task_detail_id)

    if not task:
        return jsonify({'error': 'NOT_FOUND', 'message': 'Task를 찾을 수 없습니다.'}), 404

    if task.task_type != 'SINGLE_ACTION':
        return jsonify({
            'error': 'INVALID_TASK_TYPE',
            'message': '단일 액션 Task가 아닙니다.'
        }), 400

    if task.completed_at is not None:
        return jsonify({
            'error': 'ALREADY_COMPLETED',
            'message': '이미 완료된 Task입니다.'
        }), 400

    from datetime import timezone
    from app.models.task_detail import complete_single_action
    from app.models.completion_status import update_process_completion, check_all_processes_completed, update_all_completed
    from app.models.task_detail import get_incomplete_tasks

    completed_at = datetime.now(timezone.utc)
    worker_id = get_current_worker_id()

    success = complete_single_action(task_detail_id, completed_at, worker_id)
    if not success:
        return jsonify({'error': 'COMPLETE_FAILED', 'message': '완료 처리에 실패했습니다.'}), 500

    # work_completion_log 기록
    try:
        from app.models.worker import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO work_completion_log (
                task_id, worker_id, serial_number, qr_doc_id,
                task_category, task_id_ref, task_name,
                completed_at, duration_minutes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)
            """,
            (task.id, worker_id, task.serial_number, task.qr_doc_id,
             task.task_category, task.task_id, task.task_name, completed_at)
        )
        conn.commit()
        put_conn(conn)
    except Exception as e:
        logger.error(f"Failed to log single action completion: {e}")

    # completion_status 업데이트
    incomplete = get_incomplete_tasks(task.serial_number, task.task_category)
    category_completed = len(incomplete) == 0
    if category_completed:
        update_process_completion(task.serial_number, task.task_category, True)
        if check_all_processes_completed(task.serial_number):
            update_all_completed(task.serial_number, True, completed_at)

    # Sprint 27: 완료 연쇄 알림 트리거 (TANK_DOCKING → ELEC 관리자 등)
    try:
        from app.services.task_service import TaskService
        task_service = TaskService()
        task_service._trigger_completion_alerts(task)
    except Exception as e:
        logger.error(f"Failed to trigger completion alerts for single action: {e}")

    updated_task = get_task_by_id(task_detail_id)
    result = _task_to_dict(updated_task) if updated_task else {}
    result['category_completed'] = category_completed

    return jsonify(result), 200


# === 편의 라우트: FE task_service.dart 호환 ===


@work_bp.route("/tasks/<serial_number>", methods=["GET"])
@jwt_required
def get_tasks_by_serial(serial_number: str) -> Tuple[Dict[str, Any], int]:
    """
    시리얼 번호로 Task 목록 조회 (company 기반 자동 필터링)

    Path Parameters:
        serial_number: 제품 시리얼 번호

    Query Parameters:
        process_type: 공정 유형 강제 필터 (MECH, ELEC, TM, PI, QI, SI) — 미지정 시 company 기반 자동 필터
        all: 'true'이면 필터 없이 전체 조회 (관리자용)

    Response:
        200: Task 목록 (리스트 형태)
    """
    from app.models.worker import get_worker_by_id
    from app.middleware.jwt_auth import get_current_worker_id
    from app.services.task_seed import filter_tasks_for_worker

    task_category = request.args.get('process_type')
    fetch_all = request.args.get('all', '').lower() == 'true'
    qr_doc_id = request.args.get('qr_doc_id')  # Sprint 31A: QR 기반 필터링

    # Sprint 31A: QR 기반 태스크 필터링
    # all=true (관리자): serial_number 기준 전체 조회 (TANK L/R 포함)
    # qr_doc_id 지정 (작업자): 해당 QR의 태스크만 (PRODUCT → 본체, TANK → L/R만)
    # 둘 다 없으면: serial_number 기준 (기존 호환)
    if fetch_all or not qr_doc_id:
        tasks = get_tasks_by_serial_number(serial_number, task_category)
    else:
        tasks = get_tasks_by_qr_doc_id(qr_doc_id, task_category)

    # all=true이면 필터 없이 반환 (관리자 전체 조회)
    if not fetch_all and task_category is None:
        # company 기반 자동 필터링: JWT에서 worker 정보 조회
        try:
            current_worker_id = get_current_worker_id()
            worker = get_worker_by_id(current_worker_id)
            product = get_product_by_serial_number(serial_number)
            if worker:
                tasks = filter_tasks_for_worker(
                    tasks, worker.company, worker.role, product,
                    worker_active_role=worker.active_role  # Sprint 11
                )
        except Exception as e:
            logger.warning(f"Company-based task filter failed, returning all: {e}")

    task_list = [_task_to_dict(task) for task in tasks]

    # worker_name 일괄 조회 (작업자명 표시용)
    worker_ids = list(set(t.worker_id for t in tasks if t.worker_id))
    if worker_ids:
        try:
            from app.models.worker import get_db_connection as get_conn
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, name FROM workers WHERE id = ANY(%s)",
                (worker_ids,)
            )
            worker_map = {row['id']: row['name'] for row in cur.fetchall()}
            put_conn(conn)
            for item in task_list:
                wid = item.get('worker_id')
                item['worker_name'] = worker_map.get(wid) if wid else None
        except Exception as e:
            logger.warning(f"Worker name lookup failed: {e}")
            for item in task_list:
                item['worker_name'] = None
    else:
        for item in task_list:
            item['worker_name'] = None

    # workers 배열 일괄 조회 (N+1 방지)
    # #46: task_id 단독 매핑 → serial_number 기준 조회 + task_id/task_ref fallback 복합 매핑
    # task seed 재실행으로 app_task_details.id가 변경되어도 작업자 누락 방지
    task_db_ids = [item['id'] for item in task_list if item.get('id')]
    workers_by_task: Dict[int, list] = {item['id']: [] for item in task_list if item.get('id')}
    if task_db_ids:
        try:
            from app.models.worker import get_db_connection as get_conn
            conn = get_conn()
            cur = conn.cursor()

            # task_list에서 task_id_ref → db_id 매핑 생성 (fallback용)
            task_ref_to_id = {}
            for item in task_list:
                key = (item.get('task_category', ''), item.get('task_id', ''))  # task_id = task_id_ref
                task_ref_to_id[key] = item['id']

            cur.execute(
                """
                SELECT
                    wsl.task_id,
                    wsl.task_category,
                    wsl.task_id_ref,
                    wsl.worker_id,
                    w.name AS worker_name,
                    wsl.started_at,
                    wcl.completed_at,
                    wcl.duration_minutes,
                    CASE WHEN wcl.id IS NOT NULL THEN 'completed' ELSE 'in_progress' END AS status
                FROM work_start_log wsl
                JOIN workers w ON wsl.worker_id = w.id
                LEFT JOIN work_completion_log wcl
                    ON wsl.task_id = wcl.task_id AND wsl.worker_id = wcl.worker_id
                WHERE wsl.serial_number = %s
                ORDER BY wsl.task_category, wsl.started_at ASC
                """,
                (serial_number,)
            )
            rows = cur.fetchall()
            for row in rows:
                tid = row['task_id']
                worker_entry = {
                    'worker_id': row['worker_id'],
                    'worker_name': row['worker_name'],
                    'started_at': row['started_at'].isoformat() if row['started_at'] else None,
                    'completed_at': row['completed_at'].isoformat() if row['completed_at'] else None,
                    'duration_minutes': row['duration_minutes'],
                    'status': row['status'],
                }
                if tid in workers_by_task:
                    # 1차: task_id로 직접 매핑 (정상 경우)
                    workers_by_task[tid].append(worker_entry)
                else:
                    # 2차 fallback: task_category + task_id_ref로 매핑
                    # (task seed 재실행으로 app_task_details.id가 변경된 경우 대응)
                    ref_key = (row['task_category'], row['task_id_ref'])
                    fallback_tid = task_ref_to_id.get(ref_key)
                    if fallback_tid and fallback_tid in workers_by_task:
                        workers_by_task[fallback_tid].append(worker_entry)
                        logger.info(
                            f"[#46-fallback] worker={row['worker_name']} matched via "
                            f"ref_key={ref_key} instead of task_id={tid}"
                        )
            for tid, wlist in workers_by_task.items():
                if len(wlist) >= 2:
                    names = [w['worker_name'] for w in wlist]
                    logger.info(f"[BUG-14] task_id={tid} has {len(wlist)} workers: {names}")
            put_conn(conn)
        except Exception as e:
            logger.warning(f"Workers batch query failed: {e}")

    # my_status + my_pause_status 일괄 조회 (Sprint 55-B: 화면 재진입 시 pause 상태 유지)
    my_status_map: Dict[int, str] = {}
    my_pause_map: Dict[int, str] = {}
    if task_db_ids:
        try:
            worker_id = get_current_worker_id()
            from app.models.worker import get_db_connection as get_conn
            conn2 = get_conn()
            cur2 = conn2.cursor()
            cur2.execute(
                """
                SELECT t.id AS task_id,
                       CASE
                           WHEN wcl.id IS NOT NULL THEN 'completed'
                           WHEN wsl.id IS NOT NULL THEN 'in_progress'
                           ELSE 'not_started'
                       END AS my_status,
                       CASE
                           WHEN wpl.id IS NOT NULL THEN 'paused'
                           ELSE 'working'
                       END AS my_pause_status
                FROM app_task_details t
                LEFT JOIN work_start_log wsl ON wsl.task_id = t.id AND wsl.worker_id = %s
                LEFT JOIN work_completion_log wcl ON wcl.task_id = t.id AND wcl.worker_id = %s
                LEFT JOIN work_pause_log wpl ON wpl.task_detail_id = t.id AND wpl.worker_id = %s
                                                AND wpl.resumed_at IS NULL
                WHERE t.id = ANY(%s)
                """,
                (worker_id, worker_id, worker_id, task_db_ids)
            )
            for row in cur2.fetchall():
                my_status_map[row['task_id']] = row['my_status']
                my_pause_map[row['task_id']] = row['my_pause_status']
            conn2.close()
        except Exception as e:
            logger.warning(f"my_status batch query failed: {e}")

    for item in task_list:
        tid = item.get('id')
        workers_list = workers_by_task.get(tid, []) if tid else []
        # legacy fallback: work_start_log 없는 경우 단일 작업자 정보로 보완
        if not workers_list and item.get('worker_id') and item.get('worker_id') != 0:
            started = item.get('started_at')
            completed = item.get('completed_at')
            status_str = 'completed' if completed else ('in_progress' if started else 'not_started')
            workers_list = [{
                'worker_id': item['worker_id'],
                'worker_name': item.get('worker_name'),
                'started_at': started,
                'completed_at': completed,
                'duration_minutes': item.get('duration_minutes'),
                'status': status_str,
            }]
        item['workers'] = workers_list
        item['my_status'] = my_status_map.get(tid, 'not_started') if tid else 'not_started'
        item['my_pause_status'] = my_pause_map.get(tid, 'working') if tid else 'working'

    return jsonify(task_list), 200


@work_bp.route("/completion/<serial_number>", methods=["GET"])
@jwt_required
def get_completion_by_serial(serial_number: str) -> Tuple[Dict[str, Any], int]:
    """
    시리얼 번호로 공정 완료 상태 조회

    Path Parameters:
        serial_number: 제품 시리얼 번호

    Response:
        200: 완료 상태 정보
        404: 시리얼 번호에 해당하는 완료 상태 없음
    """
    status = get_or_create_completion_status(serial_number)
    if not status:
        return jsonify({
            'error': 'STATUS_ERROR',
            'message': '완료 상태 조회 실패'
        }), 500

    product = get_product_by_serial_number(serial_number)

    return jsonify({
        'qr_doc_id': product.qr_doc_id if product else None,
        'serial_number': serial_number,
        'mech_completed': status.mech_completed,
        'elec_completed': status.elec_completed,
        'tm_completed': status.tm_completed,
        'pi_completed': status.pi_completed,
        'qi_completed': status.qi_completed,
        'si_completed': status.si_completed,
        'all_completed': status.all_completed,
        'all_completed_at': status.all_completed_at.isoformat() if status.all_completed_at else None,
    }), 200


@work_bp.route("/validation/check-process", methods=["POST"])
@jwt_required
def validate_process() -> Tuple[Dict[str, Any], int]:
    """
    공정 누락 검증 (PI/QI/SI용)
    Sprint 3: process_validator 연동

    Request Body:
        {
            "serial_number": str,
            "process_type": str (PI, QI, SI)
        }

    Response:
        200: {"valid": bool, "missing_processes": [...], "message": str, "alerts_created": int}
    """
    data = request.get_json()
    if not data or not all(k in data for k in ['serial_number', 'process_type']):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'serial_number와 process_type이 필요합니다.'
        }), 400

    serial_number = data['serial_number']
    process_type = data['process_type']

    # JWT에서 worker_id 추출
    worker_id = get_current_worker_id()

    # serial_number로 제품 조회 → qr_doc_id 획득
    product = get_product_by_serial_number(serial_number)
    if not product:
        return jsonify({
            'error': 'PRODUCT_NOT_FOUND',
            'message': '제품을 찾을 수 없습니다.'
        }), 404

    # Sprint 3: process_validator 사용 (알림 생성 포함)
    from app.services.process_validator import validate_process_start
    validation_result = validate_process_start(
        serial_number=serial_number,
        process_type=process_type,
        qr_doc_id=product.qr_doc_id,
        triggered_by_worker_id=worker_id
    )

    # FE 호환 응답 형식으로 변환 (Sprint 6: MM→MECH, EE→ELEC)
    warnings = validation_result.get('warnings', [])
    missing_processes = []
    for warning in warnings:
        if 'MECH' in warning:
            missing_processes.append('MECH')
        if 'ELEC' in warning:
            missing_processes.append('ELEC')

    return jsonify({
        'valid': validation_result.get('can_proceed', True),
        'missing_processes': missing_processes,
        'location_qr_verified': product.location_qr_id is not None,
        'message': warnings[0] if warnings else None,
        'alerts_created': validation_result.get('alerts_created', 0)
    }), 200


@work_bp.route("/task/toggle-applicable", methods=["PUT"])
@jwt_required
def toggle_task_applicable() -> Tuple[Dict[str, Any], int]:
    """
    Task 적용 여부 토글 (관리자/사내직원 전용)

    Request Body:
        {
            "task_id": int,
            "is_applicable": bool
        }

    Response:
        200: 업데이트된 TaskDetail 전체 정보
        404: Task를 찾을 수 없음
    """
    data = request.get_json()
    if not data or 'task_id' not in data or 'is_applicable' not in data:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'task_id와 is_applicable이 필요합니다.'
        }), 400

    task_id = data['task_id']
    is_applicable = data['is_applicable']

    task = get_task_by_id(task_id)
    if not task:
        return jsonify({
            'error': 'TASK_NOT_FOUND',
            'message': '작업을 찾을 수 없습니다.'
        }), 404

    # toggle_task_applicable CRUD 함수 호출
    from app.models.task_detail import toggle_task_applicable as db_toggle
    success = db_toggle(task_id, is_applicable)

    if not success:
        return jsonify({
            'error': 'UPDATE_FAILED',
            'message': 'Task 적용 여부 업데이트 실패'
        }), 500

    updated_task = get_task_by_id(task_id)
    return jsonify(_task_to_dict(updated_task)), 200


@work_bp.route("/location/update", methods=["POST"])
@jwt_required
def update_location_compat() -> Tuple[Dict[str, Any], int]:
    """
    Location QR 업데이트 (FE 호환 경로)

    Request Body:
        {
            "qr_doc_id": str,
            "location_qr_id": str
        }

    Response:
        200: 업데이트된 ProductInfo 전체 정보
    """
    from app.models.product_info import get_product_by_qr_doc_id, update_location_qr

    data = request.get_json()
    if not data or not all(k in data for k in ['qr_doc_id', 'location_qr_id']):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'qr_doc_id와 location_qr_id가 필요합니다.'
        }), 400

    qr_doc_id = data['qr_doc_id']
    location_qr_id = data['location_qr_id']

    product = get_product_by_qr_doc_id(qr_doc_id)
    if not product:
        return jsonify({
            'error': 'PRODUCT_NOT_FOUND',
            'message': '제품을 찾을 수 없습니다.'
        }), 404

    success = update_location_qr(qr_doc_id, location_qr_id)
    if not success:
        return jsonify({
            'error': 'UPDATE_FAILED',
            'message': '위치 정보 업데이트 실패'
        }), 500

    # 업데이트된 제품 정보 반환 (FE가 ProductInfo.fromJson 기대)
    updated_product = get_product_by_qr_doc_id(qr_doc_id)
    return jsonify({
        'id': updated_product.id,
        'qr_doc_id': updated_product.qr_doc_id,
        'serial_number': updated_product.serial_number,
        'model': updated_product.model,
        'prod_date': updated_product.prod_date.isoformat() if updated_product.prod_date else None,
        'location_qr_id': updated_product.location_qr_id,
        'mech_partner': updated_product.mech_partner,
        'elec_partner': updated_product.elec_partner,
        'module_outsourcing': updated_product.module_outsourcing,
        'sales_order': updated_product.sales_order,
        'customer': updated_product.customer,
        'title_number': updated_product.title_number,
        'mech_start': updated_product.mech_start.isoformat() if updated_product.mech_start else None,
        'mech_end': updated_product.mech_end.isoformat() if updated_product.mech_end else None,
        'elec_start': updated_product.elec_start.isoformat() if updated_product.elec_start else None,
        'elec_end': updated_product.elec_end.isoformat() if updated_product.elec_end else None,
        'created_at': updated_product.created_at.isoformat(),
        'updated_at': updated_product.updated_at.isoformat(),
    }), 200


# ============================================================
# Sprint 9: 일시정지/재개 엔드포인트
# ============================================================


@work_bp.route("/work/pause", methods=["POST"])
@jwt_required
def pause_work() -> Tuple[Dict[str, Any], int]:
    """
    작업 일시정지

    Request Body:
        {
            "task_detail_id": int
        }

    Headers:
        Authorization: Bearer {token}

    Response:
        200: {"message": str, "paused_at": ISO8601}
        400: {"error": "INVALID_REQUEST|TASK_NOT_STARTED|TASK_ALREADY_COMPLETED|TASK_ALREADY_PAUSED", "message": str}
        403: {"error": "FORBIDDEN", "message": str}
        404: {"error": "TASK_NOT_FOUND", "message": str}
    """
    data = request.get_json(silent=True) or {}
    task_detail_id = data.get('task_detail_id')
    # Sprint 55: pause_type을 요청 본문에서 읽기 (기본값: 'manual')
    pause_type = data.get('pause_type', 'manual')

    if not task_detail_id:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'task_detail_id가 필요합니다.'
        }), 400

    worker_id = get_current_worker_id()

    # 작업 조회
    task = get_task_by_id(task_detail_id)
    if not task:
        return jsonify({
            'error': 'TASK_NOT_FOUND',
            'message': '작업을 찾을 수 없습니다.'
        }), 404

    # 시작되지 않은 작업
    if not task.started_at:
        return jsonify({
            'error': 'TASK_NOT_STARTED',
            'message': '아직 시작되지 않은 작업입니다.'
        }), 400

    # 이미 완료된 작업
    if task.completed_at:
        return jsonify({
            'error': 'TASK_ALREADY_COMPLETED',
            'message': '이미 완료된 작업입니다.'
        }), 400

    # Sprint 55: 개인별 pause — is_paused(task 전체) 대신 본인의 활성 pause 여부 확인
    from app.services.task_service import _is_worker_paused, _all_active_workers_paused
    if _is_worker_paused(task_detail_id, worker_id):
        return jsonify({
            'error': 'TASK_ALREADY_PAUSED',
            'message': '이미 일시정지된 작업입니다.'
        }), 400

    # 이 작업자가 작업을 시작했는지 확인 (work_start_log 기준)
    from app.services.task_service import _worker_has_started_task
    from app.models.worker import get_worker_by_id
    if not _worker_has_started_task(task_detail_id, worker_id):
        # Sprint 11: GST 작업자 간 cross-worker 제어 허용
        current_worker = get_worker_by_id(worker_id)
        gst_cross_allowed = False
        if current_worker and current_worker.company == 'GST':
            task_worker = get_worker_by_id(task.worker_id) if task.worker_id else None
            if task_worker and task_worker.company == 'GST':
                gst_cross_allowed = True
        if not gst_cross_allowed:
            return jsonify({
                'error': 'FORBIDDEN',
                'message': '이 작업을 시작하지 않은 작업자입니다.'
            }), 403

    # 일시정지 로그 생성
    pause_log = create_pause(task_detail_id, worker_id, pause_type=pause_type)
    if not pause_log:
        return jsonify({
            'error': 'PAUSE_FAILED',
            'message': '일시정지 처리에 실패했습니다.'
        }), 500

    # Sprint 55: task.is_paused = 전원 paused일 때만 true
    all_paused = _all_active_workers_paused(task_detail_id)
    set_paused(task_detail_id, is_paused=all_paused)

    logger.info(
        f"Task paused: task_id={task_detail_id}, worker_id={worker_id}, "
        f"task_is_paused={all_paused}"
    )

    # 업데이트된 전체 TaskDetail 반환 (FE TaskItem.fromJson 호환)
    updated_task = get_task_by_id(task_detail_id)
    if updated_task:
        result = _task_to_dict(updated_task)
        result['my_pause_status'] = 'paused'
        return jsonify(result), 200

    return jsonify({
        'message': '작업이 일시정지되었습니다.',
        'paused_at': pause_log.paused_at.isoformat(),
        'my_pause_status': 'paused',
    }), 200


@work_bp.route("/work/resume", methods=["POST"])
@jwt_required
def resume_work() -> Tuple[Dict[str, Any], int]:
    """
    작업 재개

    Request Body:
        {
            "task_detail_id": int
        }

    Headers:
        Authorization: Bearer {token}

    Response:
        200: {"message": str, "resumed_at": ISO8601, "pause_duration_minutes": int}
        400: {"error": "INVALID_REQUEST|TASK_NOT_PAUSED", "message": str}
        403: {"error": "FORBIDDEN", "message": str}
        404: {"error": "TASK_NOT_FOUND|PAUSE_NOT_FOUND", "message": str}
    """
    data = request.get_json(silent=True) or {}
    task_detail_id = data.get('task_detail_id')

    if not task_detail_id:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'task_detail_id가 필요합니다.'
        }), 400

    worker_id = get_current_worker_id()

    # 작업 조회
    task = get_task_by_id(task_detail_id)
    if not task:
        return jsonify({
            'error': 'TASK_NOT_FOUND',
            'message': '작업을 찾을 수 없습니다.'
        }), 404

    # Sprint 55: 본인의 활성 pause 조회 (task 전체 is_paused 상태 무관)
    from app.models.worker import get_worker_by_id
    from app.services.task_service import _all_active_workers_paused, _is_worker_paused
    current_worker = get_worker_by_id(worker_id)
    is_admin = current_worker and (current_worker.is_admin or current_worker.is_manager)

    # 본인의 활성 pause 조회
    active_pause = get_active_pause_by_worker(task_detail_id, worker_id)

    if not active_pause:
        # admin/manager는 임의 작업자의 pause도 resume 가능 (override)
        if is_admin:
            active_pause = get_active_pause(task_detail_id)
            if not active_pause:
                return jsonify({
                    'error': 'PAUSE_NOT_FOUND',
                    'message': '활성 일시정지 로그를 찾을 수 없습니다.'
                }), 404
        else:
            return jsonify({
                'error': 'PAUSE_NOT_FOUND',
                'message': '본인의 활성 일시정지를 찾을 수 없습니다.'
            }), 404

    logger.info(
        f"Resume permission check: pause_worker={active_pause.worker_id}, "
        f"jwt_worker={worker_id}, is_admin={is_admin}"
    )

    # 재개 처리
    resumed_at = datetime.now(Config.KST)
    updated_pause = resume_pause(active_pause.id, resumed_at)
    if not updated_pause:
        return jsonify({
            'error': 'RESUME_FAILED',
            'message': '재개 처리에 실패했습니다.'
        }), 500

    # 누적 일시정지 시간 업데이트
    pause_duration = updated_pause.pause_duration_minutes or 0
    new_total_pause_minutes = task.total_pause_minutes + pause_duration

    # Sprint 55: task.is_paused 재판정 (전원 paused 여부)
    all_paused = _all_active_workers_paused(task_detail_id)
    set_paused(task_detail_id, is_paused=all_paused, total_pause_minutes=new_total_pause_minutes)

    logger.info(
        f"Task resumed: task_id={task_detail_id}, worker_id={worker_id}, "
        f"pause_duration={pause_duration}m, total_pause={new_total_pause_minutes}m, "
        f"task_is_paused={all_paused}"
    )

    # 업데이트된 전체 TaskDetail 반환 (FE TaskItem.fromJson 호환)
    updated_task = get_task_by_id(task_detail_id)
    if updated_task:
        result = _task_to_dict(updated_task)
        result['my_pause_status'] = 'paused' if _is_worker_paused(task_detail_id, worker_id) else 'working'
        return jsonify(result), 200

    return jsonify({
        'message': '작업이 재개되었습니다.',
        'resumed_at': resumed_at.isoformat(),
        'pause_duration_minutes': pause_duration,
        'my_pause_status': 'working',
    }), 200


@work_bp.route("/work/pause-history/<int:task_detail_id>", methods=["GET"])
@jwt_required
def get_pause_history(task_detail_id: int) -> Tuple[Dict[str, Any], int]:
    """
    작업 일시정지 이력 조회

    Path Parameters:
        task_detail_id: 작업 ID

    Headers:
        Authorization: Bearer {token}

    Response:
        200: {"pauses": [...]}
        404: {"error": "TASK_NOT_FOUND", "message": str}
    """
    # 작업 존재 확인
    task = get_task_by_id(task_detail_id)
    if not task:
        return jsonify({
            'error': 'TASK_NOT_FOUND',
            'message': '작업을 찾을 수 없습니다.'
        }), 404

    pauses = get_pauses_by_task(task_detail_id)

    return jsonify({
        'pauses': [p.to_dict() for p in pauses]
    }), 200


@work_bp.route("/work/today-tags", methods=["GET"])
@jwt_required
def get_today_tags() -> Tuple[Dict[str, Any], int]:
    """
    오늘 날짜 태깅 QR 목록 (현재 작업자 기준, Sprint 40-A)

    KST(Asia/Seoul) 기준 오늘 태깅한 QR 목록을 반환.
    qr_doc_id별 중복 제거(DISTINCT), 마지막 태깅 시각(last_tagged_at) 포함.

    Headers:
        Authorization: Bearer {token}

    Response:
        200: {"tags": [{"qr_doc_id": str, "serial_number": str, "last_tagged_at": str}, ...]}
    """
    from app.models.work_start_log import get_today_tags_by_worker

    worker_id = g.worker_id
    tags = get_today_tags_by_worker(worker_id)

    return jsonify({'tags': tags}), 200


@work_bp.route("/work/request-deactivation", methods=["POST"])
@jwt_required
def request_deactivation() -> Tuple[Dict[str, Any], int]:
    """
    협력사 관리자(manager)가 같은 company 작업자 비활성화 요청 (Sprint 40-C)

    Request Body:
        {
            "worker_id": int,
            "reason": str
        }

    Headers:
        Authorization: Bearer {manager_token}

    Returns:
        200: {"message": "비활성화 요청 완료", "worker_id": N}
        400: {"error": "INVALID_REQUEST", "message": "..."}
        403: {"error": "FORBIDDEN", "message": "..."}
        404: {"error": "WORKER_NOT_FOUND", "message": "..."}
        422: {"error": "NO_CHANGE", "message": "..."}
    """
    data = request.get_json()

    if not data:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': '요청 본문이 필요합니다.'
        }), 400

    worker_id = data.get('worker_id')
    reason = data.get('reason', '')

    if not worker_id or not isinstance(worker_id, int):
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'worker_id(int)가 필요합니다.'
        }), 400

    # 요청자 확인 (manager 체크)
    requester_id = g.worker_id
    requester = get_worker_by_id(requester_id)

    if not requester or not requester.is_manager:
        return jsonify({
            'error': 'FORBIDDEN',
            'message': '협력사 관리자만 비활성화 요청을 할 수 있습니다.'
        }), 403

    # 대상 사용자 확인
    target = get_worker_by_id(worker_id)
    if not target:
        return jsonify({
            'error': 'WORKER_NOT_FOUND',
            'message': '해당 사용자를 찾을 수 없습니다.'
        }), 404

    # 같은 company인지 확인
    if target.company != requester.company:
        return jsonify({
            'error': 'FORBIDDEN',
            'message': '같은 소속 회사의 작업자만 비활성화할 수 있습니다.'
        }), 403

    success = deactivate_worker(worker_id)

    if not success:
        return jsonify({
            'error': 'NO_CHANGE',
            'message': '이미 비활성화된 사용자이거나 변경에 실패했습니다.'
        }), 422

    logger.info(
        f"Deactivation requested: requester={requester_id}, target={worker_id}, reason={reason}"
    )

    # 비활성화 성공 후 알림 발송 (non-blocking — 실패해도 비활성화는 유지)
    try:
        from app.services.alert_service import create_and_broadcast_alert
        from app.models.worker import get_db_connection
        from app.db_pool import put_conn as _put_conn

        # Admin ID 목록 조회
        _conn = None
        admin_ids = []
        try:
            _conn = get_db_connection()
            _cur = _conn.cursor()
            _cur.execute("SELECT id FROM workers WHERE is_admin = TRUE AND is_active = TRUE")
            admin_ids = [row['id'] for row in _cur.fetchall()]
        finally:
            if _conn:
                _put_conn(_conn)

        alert_message = (
            f"{requester.name}({requester.company})이 "
            f"{target.name} 비활성화를 요청했습니다."
        )

        for admin_id in admin_ids:
            create_and_broadcast_alert({
                'alert_type': 'WORKER_DEACTIVATION_REQUEST',
                'message': alert_message,
                'triggered_by_worker_id': requester_id,
                'target_worker_id': admin_id,
            })
    except Exception as _e:
        logger.warning(f"비활성화 앱 알림 발송 실패 (non-blocking): {_e}")

    # Admin 이메일 알림 (non-blocking)
    try:
        import threading
        from app.services.email_service import send_deactivation_notification

        def _send_email_async():
            try:
                send_deactivation_notification(
                    manager_name=requester.name,
                    manager_company=requester.company or '',
                    target_name=target.name,
                    target_email=target.email,
                    target_role=target.role,
                    reason=reason,
                )
            except Exception as _ex:
                logger.warning(f"비활성화 이메일 알림 발송 실패 (non-blocking): {_ex}")

        threading.Thread(target=_send_email_async, daemon=True).start()
    except Exception as _e:
        logger.warning(f"비활성화 이메일 스레드 시작 실패 (non-blocking): {_e}")

    return jsonify({
        'message': '비활성화 요청 완료',
        'worker_id': worker_id,
    }), 200
