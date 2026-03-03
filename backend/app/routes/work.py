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
from app.middleware.jwt_auth import jwt_required, get_current_worker_id
from app.services.task_service import TaskService
from app.models.task_detail import get_task_by_id, get_tasks_by_serial_number
from app.models.completion_status import get_or_create_completion_status
from app.models.product_info import get_product_by_serial_number
from app.models.work_pause_log import create_pause, resume_pause, get_active_pause, get_pauses_by_task
from app.models.task_detail import set_paused


logger = logging.getLogger(__name__)

work_bp = Blueprint("work", __name__, url_prefix="/api/app")
task_service = TaskService()


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

    # 필수 필드 확인 (task_detail_id 또는 task_id 허용)
    task_detail_id = None
    if data:
        task_detail_id = data.get('task_detail_id') or data.get('task_id')

    if not task_detail_id:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'task_detail_id 또는 task_id가 필요합니다.'
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
            return jsonify(_task_to_dict(updated_task)), 200

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

    # 필수 필드 확인 (task_detail_id 또는 task_id 허용)
    task_detail_id = None
    if data:
        task_detail_id = data.get('task_detail_id') or data.get('task_id')

    if not task_detail_id:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': 'task_detail_id 또는 task_id가 필요합니다.'
        }), 400

    # 현재 작업자 ID 추출 (JWT에서)
    worker_id = get_current_worker_id()

    # task_service 호출
    response, status_code = task_service.complete_work(
        worker_id=worker_id,
        task_detail_id=task_detail_id
    )

    # 성공 시 업데이트된 전체 TaskDetail 반환
    if status_code == 200:
        updated_task = get_task_by_id(task_detail_id)
        if updated_task:
            result = _task_to_dict(updated_task)
            result['category_completed'] = response.get('category_completed', False)
            if 'duration_warnings' in response:
                result['duration_warnings'] = response['duration_warnings']
            return jsonify(result), 200

    return jsonify(response), status_code


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

    tasks = get_tasks_by_serial_number(serial_number, task_category)

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
            conn.close()
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

    # workers 배열 일괄 조회 (N+1 방지: task_id 배열로 한 번에 조회)
    task_db_ids = [item['id'] for item in task_list if item.get('id')]
    workers_by_task: Dict[int, list] = {item['id']: [] for item in task_list if item.get('id')}
    if task_db_ids:
        try:
            from app.models.worker import get_db_connection as get_conn
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    wsl.task_id,
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
                WHERE wsl.task_id = ANY(%s)
                ORDER BY wsl.task_id, wsl.started_at ASC
                """,
                (task_db_ids,)
            )
            for row in cur.fetchall():
                tid = row['task_id']
                if tid in workers_by_task:
                    workers_by_task[tid].append({
                        'worker_id': row['worker_id'],
                        'worker_name': row['worker_name'],
                        'started_at': row['started_at'].isoformat() if row['started_at'] else None,
                        'completed_at': row['completed_at'].isoformat() if row['completed_at'] else None,
                        'duration_minutes': row['duration_minutes'],
                        'status': row['status'],
                    })
            conn.close()
        except Exception as e:
            logger.warning(f"Workers batch query failed: {e}")

    # my_status 일괄 조회 (현재 작업자의 참여 상태: not_started / in_progress / completed)
    my_status_map: Dict[int, str] = {}
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
                       END AS my_status
                FROM app_task_details t
                LEFT JOIN work_start_log wsl ON wsl.task_id = t.id AND wsl.worker_id = %s
                LEFT JOIN work_completion_log wcl ON wcl.task_id = t.id AND wcl.worker_id = %s
                WHERE t.id = ANY(%s)
                """,
                (worker_id, worker_id, task_db_ids)
            )
            for row in cur2.fetchall():
                my_status_map[row['task_id']] = row['my_status']
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

    # 이미 일시정지 중
    if task.is_paused:
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
    pause_log = create_pause(task_detail_id, worker_id, pause_type='manual')
    if not pause_log:
        return jsonify({
            'error': 'PAUSE_FAILED',
            'message': '일시정지 처리에 실패했습니다.'
        }), 500

    # 작업 상태 업데이트
    set_paused(task_detail_id, is_paused=True)

    logger.info(f"Task paused: task_id={task_detail_id}, worker_id={worker_id}")

    # 업데이트된 전체 TaskDetail 반환 (FE TaskItem.fromJson 호환)
    updated_task = get_task_by_id(task_detail_id)
    if updated_task:
        return jsonify(_task_to_dict(updated_task)), 200

    return jsonify({
        'message': '작업이 일시정지되었습니다.',
        'paused_at': pause_log.paused_at.isoformat(),
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

    # 일시정지 상태가 아닌 경우
    if not task.is_paused:
        return jsonify({
            'error': 'TASK_NOT_PAUSED',
            'message': '일시정지 중인 작업이 아닙니다.'
        }), 400

    # 활성 일시정지 로그 조회
    active_pause = get_active_pause(task_detail_id)
    if not active_pause:
        return jsonify({
            'error': 'PAUSE_NOT_FOUND',
            'message': '활성 일시정지 로그를 찾을 수 없습니다.'
        }), 404

    # 권한 확인: 일시정지한 작업자 본인 또는 관리자 또는 GST 동료
    from app.models.worker import get_worker_by_id
    current_worker = get_worker_by_id(worker_id)
    is_admin = current_worker and (current_worker.is_admin or current_worker.is_manager)
    # Sprint 11: GST 작업자 간 cross-worker 재개 허용
    gst_cross_allowed = False
    if current_worker and current_worker.company == 'GST':
        pause_worker = get_worker_by_id(active_pause.worker_id) if active_pause.worker_id else None
        if pause_worker and pause_worker.company == 'GST':
            gst_cross_allowed = True
    if active_pause.worker_id != worker_id and not is_admin and not gst_cross_allowed:
        return jsonify({
            'error': 'FORBIDDEN',
            'message': '일시정지를 해제할 권한이 없습니다.'
        }), 403

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
    set_paused(task_detail_id, is_paused=False, total_pause_minutes=new_total_pause_minutes)

    logger.info(
        f"Task resumed: task_id={task_detail_id}, worker_id={worker_id}, "
        f"pause_duration={pause_duration}m, total_pause={new_total_pause_minutes}m"
    )

    # 업데이트된 전체 TaskDetail 반환 (FE TaskItem.fromJson 호환)
    updated_task = get_task_by_id(task_detail_id)
    if updated_task:
        return jsonify(_task_to_dict(updated_task)), 200

    return jsonify({
        'message': '작업이 재개되었습니다.',
        'resumed_at': resumed_at.isoformat(),
        'pause_duration_minutes': pause_duration,
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
