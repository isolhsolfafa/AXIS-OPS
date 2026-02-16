"""
작업 서비스
Sprint 2: 작업 시작/완료 + completion_status 업데이트 + 공정 검증
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone

from app.models.task_detail import (
    create_task,
    get_task_by_id,
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


logger = logging.getLogger(__name__)

# 유효한 공정 유형
VALID_PROCESS_TYPES = {'MM', 'EE', 'TM', 'PI', 'QI', 'SI'}


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

        # 소유권 확인
        if task.worker_id != worker_id:
            return {
                'error': 'FORBIDDEN',
                'message': '다른 작업자의 작업입니다.'
            }, 403

        # 이미 시작된 작업인지 확인
        if task.started_at:
            return {
                'error': 'TASK_ALREADY_STARTED',
                'message': '이미 시작된 작업입니다.'
            }, 400

        # Task 적용 여부 확인
        if not task.is_applicable:
            return {
                'error': 'TASK_NOT_APPLICABLE',
                'message': '비활성화된 작업입니다.'
            }, 400

        # 작업 시작 처리
        started_at = datetime.now(timezone.utc)
        if not start_task(task_detail_id, started_at):
            return {
                'error': 'START_FAILED',
                'message': '작업 시작 실패'
            }, 500

        logger.info(f"Work started: task_id={task_detail_id}, worker_id={worker_id}")

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

        # 소유권 확인
        if task.worker_id != worker_id:
            return {
                'error': 'FORBIDDEN',
                'message': '다른 작업자의 작업입니다.'
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

        # 작업 완료 처리 (duration 자동 계산)
        completed_at = datetime.now(timezone.utc)
        if not complete_task(task_detail_id, completed_at):
            return {
                'error': 'COMPLETE_FAILED',
                'message': '작업 완료 실패'
            }, 500

        # duration 계산 (분 단위)
        duration_minutes = int((completed_at - task.started_at).total_seconds() / 60)

        logger.info(f"Work completed: task_id={task_detail_id}, duration={duration_minutes}m")

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

        response = {
            'message': '작업이 완료되었습니다.',
            'task_id': task_detail_id,
            'completed_at': completed_at.isoformat(),
            'duration_minutes': duration_minutes,
            'category_completed': category_completed
        }

        # Sprint 3: duration 경고가 있으면 응답에 포함
        if duration_warnings:
            response['duration_warnings'] = duration_warnings

        return response, 200

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
                'is_applicable': task.is_applicable
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
            'mm_completed': status.mm_completed,
            'ee_completed': status.ee_completed,
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

        # MM(기구) 완료 확인
        if not status.mm_completed:
            warnings.append({
                'type': 'missing_process',
                'process': 'MM',
                'message': '기구 작업이 아직 완료되지 않았습니다.'
            })

        # EE(전장) 완료 확인
        if not status.ee_completed:
            warnings.append({
                'type': 'missing_process',
                'process': 'EE',
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
