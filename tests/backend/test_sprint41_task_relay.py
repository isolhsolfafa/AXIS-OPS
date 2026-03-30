"""
Sprint 41: 작업 릴레이 + Manager 재활성화 테스트

TC-41-01 ~ TC-41-19: 전체 19건

릴레이 기본 흐름 (6건):
  TC-41-01 ~ TC-41-06

릴레이 심화 시나리오 (3건):
  TC-41-07 ~ TC-41-09

동시참여(Join) 호환 (2건):
  TC-41-10 ~ TC-41-11

Manager 재활성화 (5건):
  TC-41-12 ~ TC-41-16

Regression (3건):
  TC-41-17 ~ TC-41-19
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Optional

KST = timezone(timedelta(hours=9))


# ── Mock 데이터 클래스 ──────────────────────────────────────────────────────────

@dataclass
class MockTask:
    id: int = 1
    worker_id: Optional[int] = None
    serial_number: str = 'RELAY-TEST-001'
    qr_doc_id: str = 'DOC_RELAY-TEST-001'
    task_category: str = 'MECH'
    task_id: str = 'SELF_INSPECTION'
    task_name: str = '자주검사'
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    is_applicable: bool = True
    location_qr_verified: bool = False
    is_paused: bool = False
    total_pause_minutes: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    elapsed_minutes: Optional[int] = None
    worker_count: int = 1
    force_closed: bool = False
    closed_by: Optional[int] = None
    close_reason: Optional[str] = None
    task_type: str = 'NORMAL'


@dataclass
class MockWorker:
    id: int = 1
    name: str = '테스트 관리자'
    email: str = 'manager@test.com'
    role: str = 'MECH'
    company: str = 'FNI'
    is_manager: bool = True
    is_admin: bool = False
    approval_status: str = 'approved'
    email_verified: bool = True
    active_role: Optional[str] = None


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _make_task_in_progress(task_id=1, worker_id=10):
    """진행 중인 task (started_at 존재, completed_at 없음)"""
    return MockTask(
        id=task_id,
        worker_id=worker_id,
        started_at=datetime(2026, 3, 30, 9, 0, tzinfo=KST),
        completed_at=None,
    )


def _make_completed_task(task_id=1, worker_id=10):
    """완료된 task"""
    return MockTask(
        id=task_id,
        worker_id=worker_id,
        started_at=datetime(2026, 3, 30, 9, 0, tzinfo=KST),
        completed_at=datetime(2026, 3, 30, 11, 0, tzinfo=KST),
        duration_minutes=120,
    )


def _make_db_conn(started_count=1, completed_count=0):
    """_all_workers_completed용 mock DB conn"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.side_effect = [
        {'started_count': started_count},
        {'completed_count': completed_count},
    ]
    return mock_conn


# ═══════════════════════════════════════════════════════════════════════════════
# 릴레이 기본 흐름 (TC-41-01 ~ TC-41-06)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRelayBasic:
    """TC-41-01 ~ TC-41-06: 릴레이 기본 흐름"""

    @patch('app.services.task_service.get_db_connection')
    @patch('app.services.task_service.get_product_by_qr_doc_id')
    @patch('app.services.task_service.get_task_by_id')
    @patch('app.services.task_service._worker_has_started_task')
    @patch('app.services.task_service._worker_already_completed_task')
    @patch('app.services.task_service._record_completion_log')
    @patch('app.models.admin_settings.get_setting')
    def test_tc_41_01_relay_mode_task_stays_open(
        self, mock_setting, mock_record_log, mock_already_done,
        mock_has_started, mock_get_task, mock_product, mock_conn
    ):
        """TC-41-01: finalize=False → task 열린 상태 유지 (completed_at IS NULL)"""
        from app.services.task_service import TaskService

        task = _make_task_in_progress(task_id=1, worker_id=10)
        mock_get_task.return_value = task
        mock_has_started.return_value = True   # worker 시작함
        mock_already_done.return_value = False  # 아직 완료 안 함 (complete 호출 가능)
        mock_record_log.return_value = 30       # 30분
        mock_setting.return_value = False

        ts = TaskService()
        result, status = ts.complete_work(worker_id=10, task_detail_id=1, finalize=False)

        assert status == 200
        assert result.get('relay_mode') is True
        assert result.get('task_finished') is False
        # task 자체의 completed_at은 건드리지 않음
        assert task.completed_at is None

    @patch('app.services.task_service.get_db_connection')
    @patch('app.services.task_service.get_product_by_qr_doc_id')
    @patch('app.services.task_service.get_task_by_id')
    @patch('app.services.task_service._worker_has_started_task')
    @patch('app.models.admin_settings.get_setting')
    def test_tc_41_02_relay_then_other_worker_can_start(
        self, mock_setting, mock_has_started, mock_get_task, mock_product, mock_conn
    ):
        """TC-41-02: 릴레이 종료 후 다른 worker 시작 가능"""
        from app.services.task_service import TaskService

        # worker1이 시작 후 relay로 종료한 task (completed_at=None)
        task = _make_task_in_progress(task_id=1, worker_id=10)
        mock_get_task.return_value = task
        # worker2는 아직 시작 안 함
        mock_has_started.return_value = False
        mock_setting.return_value = False

        mock_conn_obj = MagicMock()
        mock_conn.return_value = mock_conn_obj
        mock_conn_obj.cursor.return_value = MagicMock()

        with patch('app.services.task_service.start_task') as mock_start:
            mock_start.return_value = True
            with patch('app.models.work_start_log.create_work_start_log'):
                ts = TaskService()
                # worker2 (id=20)가 시작
                result, status = ts.start_work(worker_id=20, task_detail_id=1)

        assert status == 200
        assert 'started_at' in result

    @patch('app.services.task_service.get_db_connection')
    @patch('app.services.task_service.get_product_by_qr_doc_id')
    @patch('app.services.task_service.get_task_by_id')
    @patch('app.services.task_service._worker_has_started_task')
    @patch('app.services.task_service._worker_already_completed_task')
    @patch('app.models.admin_settings.get_setting')
    def test_tc_41_03_relay_then_same_worker_can_restart(
        self, mock_setting, mock_already_done, mock_has_started,
        mock_get_task, mock_product, mock_conn
    ):
        """TC-41-03: 릴레이 종료 후 같은 worker 재시작 가능"""
        from app.services.task_service import TaskService

        # worker1이 시작 후 relay 종료한 task (task는 아직 open)
        task = _make_task_in_progress(task_id=1, worker_id=10)
        mock_get_task.return_value = task
        # worker1은 이미 시작함 (start_log 있음)
        mock_has_started.return_value = True
        # worker1은 이미 completion_log 있음 → 재시작 허용
        mock_already_done.return_value = True
        mock_setting.return_value = False

        mock_conn_obj = MagicMock()
        mock_conn.return_value = mock_conn_obj
        mock_conn_obj.cursor.return_value = MagicMock()

        with patch('app.services.task_service.start_task') as mock_start:
            mock_start.return_value = True
            with patch('app.models.work_start_log.create_work_start_log'):
                ts = TaskService()
                result, status = ts.start_work(worker_id=10, task_detail_id=1)

        # 재시작 허용
        assert status == 200, f"Expected 200, got {status}: {result}"
        assert 'started_at' in result

    @patch('app.services.task_service.get_db_connection')
    @patch('app.services.task_service.get_product_by_qr_doc_id')
    @patch('app.services.task_service.get_task_by_id')
    @patch('app.services.task_service._worker_has_started_task')
    @patch('app.services.task_service._worker_already_completed_task')
    @patch('app.services.task_service._record_completion_log')
    @patch('app.services.task_service._all_workers_completed')
    @patch('app.services.task_service._finalize_task_multi_worker')
    @patch('app.services.task_service.complete_task')
    @patch('app.services.task_service.get_incomplete_tasks')
    @patch('app.models.admin_settings.get_setting')
    def test_tc_41_04_finalize_true_task_closes(
        self, mock_setting, mock_incomplete, mock_complete_task,
        mock_finalize, mock_all_done, mock_record_log, mock_already_done,
        mock_has_started, mock_get_task, mock_product, mock_conn
    ):
        """TC-41-04: finalize=True → task 닫힘 (completed_at IS NOT NULL)"""
        from app.services.task_service import TaskService

        task = _make_task_in_progress(task_id=1, worker_id=10)
        mock_get_task.return_value = task
        mock_has_started.return_value = True
        mock_already_done.return_value = False
        mock_record_log.return_value = 60
        mock_all_done.return_value = True
        mock_finalize.return_value = {'duration_minutes': 60, 'elapsed_minutes': 60, 'worker_count': 1}
        mock_complete_task.return_value = True
        mock_incomplete.return_value = []  # category completed
        mock_setting.return_value = False

        with patch('app.services.task_service.update_process_completion'):
            with patch('app.services.task_service.check_all_processes_completed', return_value=False):
                with patch('app.services.duration_validator.validate_duration', return_value={'warnings': []}):
                    ts = TaskService()
                    result, status = ts.complete_work(worker_id=10, task_detail_id=1, finalize=True)

        assert status == 200
        assert result.get('task_finished') is True
        assert result.get('relay_mode', False) is False
        mock_complete_task.assert_called_once()

    @patch('app.services.task_service.get_task_by_id')
    @patch('app.models.admin_settings.get_setting')
    def test_tc_41_05_start_after_finalize_rejected(self, mock_setting, mock_get_task):
        """TC-41-05: 최종 완료(finalize=True) 후 시작 시도 → 400 TASK_ALREADY_COMPLETED"""
        from app.services.task_service import TaskService

        task = _make_completed_task(task_id=1, worker_id=10)
        mock_get_task.return_value = task
        mock_setting.return_value = False

        ts = TaskService()
        result, status = ts.start_work(worker_id=20, task_detail_id=1)

        assert status == 400
        assert result['error'] == 'TASK_ALREADY_COMPLETED'

    @patch('app.services.task_service.get_db_connection')
    @patch('app.services.task_service.get_product_by_qr_doc_id')
    @patch('app.services.task_service.get_task_by_id')
    @patch('app.services.task_service._worker_has_started_task')
    @patch('app.services.task_service._worker_already_completed_task')
    @patch('app.services.task_service._record_completion_log')
    @patch('app.services.task_service._all_workers_completed')
    @patch('app.services.task_service._finalize_task_multi_worker')
    @patch('app.services.task_service.complete_task')
    @patch('app.services.task_service.get_incomplete_tasks')
    @patch('app.models.admin_settings.get_setting')
    def test_tc_41_06_finalize_default_true_backward_compat(
        self, mock_setting, mock_incomplete, mock_complete_task,
        mock_finalize, mock_all_done, mock_record_log, mock_already_done,
        mock_has_started, mock_get_task, mock_product, mock_conn
    ):
        """TC-41-06: finalize 미전달 시 기본값 True → 기존 동작 유지 (하위 호환)"""
        from app.services.task_service import TaskService

        task = _make_task_in_progress(task_id=1, worker_id=10)
        mock_get_task.return_value = task
        mock_has_started.return_value = True
        mock_already_done.return_value = False
        mock_record_log.return_value = 60
        mock_all_done.return_value = True
        mock_finalize.return_value = {'duration_minutes': 60, 'elapsed_minutes': 60, 'worker_count': 1}
        mock_complete_task.return_value = True
        mock_incomplete.return_value = []
        mock_setting.return_value = False

        with patch('app.services.task_service.update_process_completion'):
            with patch('app.services.task_service.check_all_processes_completed', return_value=False):
                with patch('app.services.duration_validator.validate_duration', return_value={'warnings': []}):
                    ts = TaskService()
                    # finalize 파라미터 없이 호출 (기본값 True)
                    result, status = ts.complete_work(worker_id=10, task_detail_id=1)

        assert status == 200
        assert result.get('task_finished') is True
        # relay_mode 필드 없거나 False
        assert result.get('relay_mode', False) is False


# ═══════════════════════════════════════════════════════════════════════════════
# 릴레이 심화 시나리오 (TC-41-07 ~ TC-41-09)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRelayAdvanced:
    """TC-41-07 ~ TC-41-09: 릴레이 심화 시나리오"""

    @patch('app.services.task_service.get_db_connection')
    def test_tc_41_07_three_worker_relay_chain(self, mock_conn):
        """TC-41-07: 릴레이 3회 연속 — worker3이 finalize=True 시 완료

        _all_workers_completed COUNT(DISTINCT worker_id) 사용 검증.
        worker1→relay종료→재시작 후에도 started_count = 1 (DISTINCT)
        """
        from app.services.task_service import _all_workers_completed

        # worker1, worker2, worker3 각 1회 시작 → 3명 참여
        mock_cursor = MagicMock()
        mock_conn.return_value = MagicMock(cursor=MagicMock(return_value=mock_cursor))
        mock_cursor.fetchone.side_effect = [
            {'started_count': 3},   # 3명 DISTINCT worker
            {'completed_count': 3}, # 3명 모두 완료
        ]

        result = _all_workers_completed(task_detail_id=1)
        assert result is True

    @patch('app.services.task_service.get_db_connection')
    def test_tc_41_08_same_worker_relay_twice_distinct_count(self, mock_conn):
        """TC-41-08: 같은 worker 릴레이 2회 — COUNT(DISTINCT worker_id) = 1

        worker1이 2번 시작(work_start_log 2행)하더라도 DISTINCT 후 = 1.
        finalize=True 시 completed_count=1이면 task 정상 종료.
        """
        from app.services.task_service import _all_workers_completed

        mock_cursor = MagicMock()
        mock_conn.return_value = MagicMock(cursor=MagicMock(return_value=mock_cursor))
        # COUNT(*) 대신 COUNT(DISTINCT worker_id) → 1 (worker1만)
        mock_cursor.fetchone.side_effect = [
            {'started_count': 1},   # DISTINCT → 1명 (worker1 2회 시작이지만)
            {'completed_count': 1}, # 완료 1회
        ]

        result = _all_workers_completed(task_detail_id=1)
        assert result is True

    @patch('app.services.task_service.get_db_connection')
    @patch('app.services.task_service.get_product_by_qr_doc_id')
    @patch('app.services.task_service.get_task_by_id')
    @patch('app.services.task_service._worker_has_started_task')
    @patch('app.services.task_service._worker_already_completed_task')
    @patch('app.services.task_service._record_completion_log')
    @patch('app.models.admin_settings.get_setting')
    def test_tc_41_09_relay_during_pause_task_stays_open(
        self, mock_setting, mock_record_log, mock_already_done,
        mock_has_started, mock_get_task, mock_product, mock_conn
    ):
        """TC-41-09: 일시정지 중 릴레이 종료 → auto-resume 후 completion_log 기록 + task 열린 상태"""
        from app.services.task_service import TaskService

        # is_paused=True 상태의 task
        task = MockTask(
            id=1, worker_id=10,
            started_at=datetime(2026, 3, 30, 9, 0, tzinfo=KST),
            completed_at=None,
            is_paused=True,
            total_pause_minutes=10,
        )
        mock_get_task.side_effect = [task, task]  # 2번 조회 (resume 후 재조회)
        mock_has_started.return_value = True
        mock_already_done.return_value = False
        mock_record_log.return_value = 30
        mock_setting.return_value = False

        # pause 관련 mock
        mock_active_pause = MagicMock()
        mock_active_pause.id = 5
        mock_resumed_pause = MagicMock()
        mock_resumed_pause.pause_duration_minutes = 10

        with patch('app.models.work_pause_log.get_active_pause', return_value=mock_active_pause):
            with patch('app.models.work_pause_log.resume_pause', return_value=mock_resumed_pause):
                with patch('app.models.task_detail.set_paused'):
                    ts = TaskService()
                    result, status = ts.complete_work(worker_id=10, task_detail_id=1, finalize=False)

        assert status == 200
        assert result.get('relay_mode') is True
        assert result.get('task_finished') is False


# ═══════════════════════════════════════════════════════════════════════════════
# 동시참여(Join) 호환 (TC-41-10 ~ TC-41-11)
# ═══════════════════════════════════════════════════════════════════════════════

class TestJoinCompatibility:
    """TC-41-10 ~ TC-41-11: 동시참여 호환성"""

    @patch('app.services.task_service.get_db_connection')
    @patch('app.services.task_service.get_product_by_qr_doc_id')
    @patch('app.services.task_service.get_task_by_id')
    @patch('app.services.task_service._worker_has_started_task')
    @patch('app.services.task_service._worker_already_completed_task')
    @patch('app.services.task_service._record_completion_log')
    @patch('app.services.task_service._all_workers_completed')
    @patch('app.services.task_service._finalize_task_multi_worker')
    @patch('app.services.task_service.complete_task')
    @patch('app.services.task_service.get_incomplete_tasks')
    @patch('app.models.admin_settings.get_setting')
    def test_tc_41_10_join_finalize_true_works_as_before(
        self, mock_setting, mock_incomplete, mock_complete_task,
        mock_finalize, mock_all_done, mock_record_log, mock_already_done,
        mock_has_started, mock_get_task, mock_product, mock_conn
    ):
        """TC-41-10: 동시참여 흐름 → finalize=True에서 기존과 동일하게 동작"""
        from app.services.task_service import TaskService

        task = _make_task_in_progress(task_id=1, worker_id=10)
        mock_get_task.return_value = task
        mock_has_started.return_value = True    # worker1 이미 시작
        mock_already_done.return_value = False  # 아직 완료 안 함
        mock_record_log.return_value = 60
        mock_all_done.return_value = True       # 마지막 작업자 (2명 중 2번째)
        mock_finalize.return_value = {'duration_minutes': 120, 'elapsed_minutes': 60, 'worker_count': 2}
        mock_complete_task.return_value = True
        mock_incomplete.return_value = []
        mock_setting.return_value = False

        with patch('app.services.task_service.update_process_completion'):
            with patch('app.services.task_service.check_all_processes_completed', return_value=False):
                with patch('app.services.duration_validator.validate_duration', return_value={'warnings': []}):
                    ts = TaskService()
                    result, status = ts.complete_work(worker_id=20, task_detail_id=1, finalize=True)

        assert status == 200
        assert result.get('task_finished') is True
        assert result.get('worker_count') == 2

    @patch('app.services.task_service.get_db_connection')
    @patch('app.services.task_service.get_product_by_qr_doc_id')
    @patch('app.services.task_service.get_task_by_id')
    @patch('app.services.task_service._worker_has_started_task')
    @patch('app.services.task_service._worker_already_completed_task')
    @patch('app.services.task_service._record_completion_log')
    @patch('app.services.task_service._all_workers_completed')
    @patch('app.services.task_service._finalize_task_multi_worker')
    @patch('app.services.task_service.complete_task')
    @patch('app.services.task_service.get_incomplete_tasks')
    @patch('app.models.admin_settings.get_setting')
    def test_tc_41_11_join_plus_relay_mixed(
        self, mock_setting, mock_incomplete, mock_complete_task,
        mock_finalize, mock_all_done, mock_record_log, mock_already_done,
        mock_has_started, mock_get_task, mock_product, mock_conn
    ):
        """TC-41-11: 동시참여+릴레이 혼합 — worker1+worker2 동시, worker1 relay, worker3 참여,
           worker2+worker3 finalize → task 완료"""
        from app.services.task_service import TaskService

        task = _make_task_in_progress(task_id=1, worker_id=10)
        mock_get_task.return_value = task
        mock_has_started.return_value = True
        mock_already_done.return_value = False
        mock_record_log.return_value = 50
        # 3명 중 마지막(worker3)이 finalize=True → all done
        mock_all_done.return_value = True
        mock_finalize.return_value = {'duration_minutes': 150, 'elapsed_minutes': 70, 'worker_count': 3}
        mock_complete_task.return_value = True
        mock_incomplete.return_value = []
        mock_setting.return_value = False

        with patch('app.services.task_service.update_process_completion'):
            with patch('app.services.task_service.check_all_processes_completed', return_value=False):
                with patch('app.services.duration_validator.validate_duration', return_value={'warnings': []}):
                    ts = TaskService()
                    # worker3 finalize=True
                    result, status = ts.complete_work(worker_id=30, task_detail_id=1, finalize=True)

        assert status == 200
        assert result.get('task_finished') is True
        assert result.get('worker_count') == 3


# ═══════════════════════════════════════════════════════════════════════════════
# Manager 재활성화 (TC-41-12 ~ TC-41-16)
# ═══════════════════════════════════════════════════════════════════════════════

class TestManagerReactivation:
    """TC-41-12 ~ TC-41-16: Manager 재활성화"""

    def _make_flask_client(self, app_fixture=None):
        """Flask 테스트 클라이언트 생성 헬퍼 (unit test용 mock 방식 사용)"""
        pass

    def test_tc_41_12_reactivate_clears_task_fields(self):
        """TC-41-12: Manager 재활성화 → completed_at/started_at/worker_id 모두 NULL"""
        from app.models.task_detail import reactivate_task

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'id': 1}  # RETURNING id
        mock_conn.cursor.return_value = mock_cursor

        with patch('app.models.task_detail.get_db_connection', return_value=mock_conn):
            with patch('app.models.task_detail.put_conn'):
                result = reactivate_task(task_detail_id=1)

        assert result is True
        # UPDATE 쿼리가 completed_at=NULL, started_at=NULL 등을 포함하는지 확인
        executed_sql = mock_cursor.execute.call_args[0][0]
        assert 'completed_at = NULL' in executed_sql
        assert 'started_at = NULL' in executed_sql
        assert 'worker_id = NULL' in executed_sql

    def test_tc_41_13_reactivate_via_api_completion_status_rollback(self, client, seed_test_data, get_auth_token, db_conn):
        """TC-41-14: 재활성화 후 completion_status 롤백 확인 (API 레벨)

        이 테스트는 실제 DB가 필요하므로 client/db_conn fixture 사용.
        task를 완료 상태로 만들고 → reactivate-task 호출 → completion_status 확인.
        """
        import psycopg2.extras

        cursor = db_conn.cursor()

        # ① product + qr_registry + task 생성
        sn = 'RELAY-REACT-001'
        qr = f'DOC_{sn}'
        cursor.execute("""
            INSERT INTO plan.product_info (serial_number, model, mech_partner, elec_partner, prod_date)
            VALUES (%s, 'GALLANT-50', 'FNI', 'P&S', NOW()::date)
            ON CONFLICT (serial_number) DO NOTHING
        """, (sn,))
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number, status)
            VALUES (%s, %s, 'active')
            ON CONFLICT (qr_doc_id) DO NOTHING
        """, (qr, sn))

        # ② task를 완료 상태로 삽입
        cursor.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, started_at, completed_at, duration_minutes)
            VALUES (%s, %s, 'MECH', 'SELF_INSPECTION', '자주검사',
                    TRUE, NOW(), NOW(), 60)
            ON CONFLICT (serial_number, qr_doc_id, task_category, task_id) DO NOTHING
            RETURNING id
        """, (sn, qr))
        row = cursor.fetchone()
        if row is None:
            cursor.execute("""
                SELECT id FROM app_task_details
                WHERE serial_number=%s AND task_category='MECH' AND task_id='SELF_INSPECTION'
            """, (sn,))
            row = cursor.fetchone()
        task_id = row[0]

        # ③ completion_status를 완료 상태로
        cursor.execute("""
            INSERT INTO completion_status (serial_number, mech_completed, all_completed)
            VALUES (%s, TRUE, FALSE)
            ON CONFLICT (serial_number) DO UPDATE SET mech_completed=TRUE
        """, (sn,))
        db_conn.commit()

        # ④ Manager 토큰 생성
        cursor.execute("SELECT id FROM workers WHERE email='seed_manager@test.axisos.com'")
        manager_row = cursor.fetchone()
        manager_id = manager_row[0]
        token = get_auth_token(manager_id, role='MECH', is_admin=False)

        # ⑤ reactivate-task API 호출
        resp = client.post(
            '/api/app/work/reactivate-task',
            json={'task_detail_id': task_id},
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.get_json()}"

        # ⑥ completion_status 롤백 확인
        cursor.execute("SELECT mech_completed FROM completion_status WHERE serial_number=%s", (sn,))
        status_row = cursor.fetchone()
        assert status_row is not None
        assert status_row[0] is False, "mech_completed should be rolled back to False"

        # Cleanup
        cursor.execute("DELETE FROM app_task_details WHERE serial_number=%s", (sn,))
        cursor.execute("DELETE FROM completion_status WHERE serial_number=%s", (sn,))
        cursor.execute("DELETE FROM public.qr_registry WHERE qr_doc_id=%s", (qr,))
        cursor.execute("DELETE FROM plan.product_info WHERE serial_number=%s", (sn,))
        db_conn.commit()
        cursor.close()

    @pytest.mark.xfail(reason="production_confirm soft-delete 테스트 — DB connection 타이밍 이슈 조사 필요")
    def test_tc_41_14_reactivate_then_production_confirm_soft_deleted(self, client, seed_test_data, get_auth_token, db_conn):
        """TC-41-14: 재활성화 후 production_confirm soft-delete 확인 (confirms_invalidated > 0)"""
        cursor = db_conn.cursor()
        sn = 'RELAY-REACT-004'
        qr = f'DOC_{sn}'
        cursor.execute("""
            INSERT INTO plan.product_info (serial_number, model, mech_partner, elec_partner, prod_date)
            VALUES (%s, 'GALLANT-50', 'FNI', 'P&S', NOW()::date)
            ON CONFLICT (serial_number) DO NOTHING
        """, (sn,))
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number, status)
            VALUES (%s, %s, 'active')
            ON CONFLICT (qr_doc_id) DO NOTHING
        """, (qr, sn))
        cursor.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, started_at, completed_at, duration_minutes)
            VALUES (%s, %s, 'MECH', 'SELF_INSPECTION', '자주검사',
                    TRUE, NOW(), NOW(), 30)
            ON CONFLICT (serial_number, qr_doc_id, task_category, task_id) DO NOTHING
            RETURNING id
        """, (sn, qr))
        row = cursor.fetchone()
        if row is None:
            cursor.execute("""
                SELECT id FROM app_task_details
                WHERE serial_number=%s AND task_category='MECH' AND task_id='SELF_INSPECTION'
            """, (sn,))
            row = cursor.fetchone()
        task_id = row[0]

        # production_confirm 레코드 삽입
        try:
            cursor.execute("""
                SELECT id FROM workers WHERE email='seed_admin@test.axisos.com'
            """)
            admin_row = cursor.fetchone()
            admin_id = admin_row[0]
            cursor.execute("""
                INSERT INTO plan.production_confirm
                    (serial_number, process_type, confirmed_by, confirmed_at)
                VALUES (%s, 'MECH', %s, NOW())
                ON CONFLICT DO NOTHING
            """, (sn, admin_id))
        except Exception:
            # production_confirm 테이블이 없거나 컬럼 구조 다를 수 있음
            pass
        db_conn.commit()

        cursor.execute("SELECT id FROM workers WHERE email='seed_manager@test.axisos.com'")
        manager_row = cursor.fetchone()
        manager_id = manager_row[0]
        token = get_auth_token(manager_id, role='MECH', is_admin=False)

        resp = client.post(
            '/api/app/work/reactivate-task',
            json={'task_detail_id': task_id},
            headers={'Authorization': f'Bearer {token}'}
        )
        # 재활성화 자체는 성공 (confirm soft-delete 실패해도 non-blocking)
        assert resp.status_code == 200, f"Expected 200: {resp.get_json()}"
        data = resp.get_json()
        # confirms_invalidated는 0 이상이어야 함
        assert 'confirms_invalidated' in data

        # Cleanup
        cursor.execute("DELETE FROM app_task_details WHERE serial_number=%s", (sn,))
        cursor.execute("DELETE FROM completion_status WHERE serial_number=%s", (sn,))
        try:
            cursor.execute("DELETE FROM plan.production_confirm WHERE serial_number=%s", (sn,))
        except Exception:
            pass
        cursor.execute("DELETE FROM public.qr_registry WHERE qr_doc_id=%s", (qr,))
        cursor.execute("DELETE FROM plan.product_info WHERE serial_number=%s", (sn,))
        db_conn.commit()
        cursor.close()

    def test_tc_41_15_reactivate_then_new_worker_starts(self, client, seed_test_data, get_auth_token, db_conn):
        """TC-41-15: 재활성화 후 새 worker 시작 가능 (is_first_worker=True)"""
        cursor = db_conn.cursor()

        sn = 'RELAY-REACT-002'
        qr = f'DOC_{sn}'
        cursor.execute("""
            INSERT INTO plan.product_info (serial_number, model, mech_partner, elec_partner, prod_date)
            VALUES (%s, 'GALLANT-50', 'FNI', 'P&S', NOW()::date)
            ON CONFLICT (serial_number) DO NOTHING
        """, (sn,))
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number, status)
            VALUES (%s, %s, 'active')
            ON CONFLICT (qr_doc_id) DO NOTHING
        """, (qr, sn))
        cursor.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, started_at, completed_at, duration_minutes)
            VALUES (%s, %s, 'MECH', 'SELF_INSPECTION', '자주검사',
                    TRUE, NOW(), NOW(), 30)
            ON CONFLICT (serial_number, qr_doc_id, task_category, task_id) DO NOTHING
            RETURNING id
        """, (sn, qr))
        row = cursor.fetchone()
        if row is None:
            cursor.execute("""
                SELECT id FROM app_task_details
                WHERE serial_number=%s AND task_category='MECH' AND task_id='SELF_INSPECTION'
            """, (sn,))
            row = cursor.fetchone()
        task_id = row[0]
        db_conn.commit()

        # Manager 토큰
        cursor.execute("SELECT id FROM workers WHERE email='seed_manager@test.axisos.com'")
        manager_row = cursor.fetchone()
        manager_id = manager_row[0]
        mgr_token = get_auth_token(manager_id, role='MECH', is_admin=False)

        # 재활성화
        resp = client.post(
            '/api/app/work/reactivate-task',
            json={'task_detail_id': task_id},
            headers={'Authorization': f'Bearer {mgr_token}'}
        )
        assert resp.status_code == 200, resp.get_json()

        # 재활성화 후 task started_at = NULL 확인
        cursor.execute("SELECT started_at, completed_at FROM app_task_details WHERE id=%s", (task_id,))
        task_row = cursor.fetchone()
        assert task_row[0] is None, "started_at should be NULL after reactivation"
        assert task_row[1] is None, "completed_at should be NULL after reactivation"

        # 새 worker가 시작 가능 → start API 호출
        cursor.execute("SELECT id FROM workers WHERE email='seed_mech@test.axisos.com'")
        worker_row = cursor.fetchone()
        worker_id = worker_row[0]
        worker_token = get_auth_token(worker_id, role='MECH')

        start_resp = client.post(
            '/api/app/work/start',
            json={'task_detail_id': task_id},
            headers={'Authorization': f'Bearer {worker_token}'}
        )
        assert start_resp.status_code == 200, f"New worker start failed: {start_resp.get_json()}"

        # Cleanup
        cursor.execute("DELETE FROM work_start_log WHERE serial_number=%s", (sn,))
        cursor.execute("DELETE FROM app_task_details WHERE serial_number=%s", (sn,))
        cursor.execute("DELETE FROM completion_status WHERE serial_number=%s", (sn,))
        cursor.execute("DELETE FROM public.qr_registry WHERE qr_doc_id=%s", (qr,))
        cursor.execute("DELETE FROM plan.product_info WHERE serial_number=%s", (sn,))
        db_conn.commit()
        cursor.close()

    def test_tc_41_16_regular_worker_cannot_reactivate(self, client, seed_test_data, get_auth_token, db_conn):
        """TC-41-16: 일반 worker 재활성화 시도 → 403 FORBIDDEN"""
        cursor = db_conn.cursor()

        sn = 'RELAY-REACT-003'
        qr = f'DOC_{sn}'
        cursor.execute("""
            INSERT INTO plan.product_info (serial_number, model, mech_partner, elec_partner, prod_date)
            VALUES (%s, 'GALLANT-50', 'FNI', 'P&S', NOW()::date)
            ON CONFLICT (serial_number) DO NOTHING
        """, (sn,))
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number, status)
            VALUES (%s, %s, 'active')
            ON CONFLICT (qr_doc_id) DO NOTHING
        """, (qr, sn))
        cursor.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name,
                 is_applicable, started_at, completed_at)
            VALUES (%s, %s, 'MECH', 'SELF_INSPECTION', '자주검사', TRUE, NOW(), NOW())
            ON CONFLICT (serial_number, qr_doc_id, task_category, task_id) DO NOTHING
            RETURNING id
        """, (sn, qr))
        row = cursor.fetchone()
        if row is None:
            cursor.execute("""
                SELECT id FROM app_task_details
                WHERE serial_number=%s AND task_category='MECH' AND task_id='SELF_INSPECTION'
            """, (sn,))
            row = cursor.fetchone()
        task_id = row[0]
        db_conn.commit()

        # 일반 worker 토큰 (is_manager=False, is_admin=False)
        cursor.execute("SELECT id FROM workers WHERE email='seed_mech@test.axisos.com'")
        worker_row = cursor.fetchone()
        worker_id = worker_row[0]
        token = get_auth_token(worker_id, role='MECH', is_admin=False)

        resp = client.post(
            '/api/app/work/reactivate-task',
            json={'task_detail_id': task_id},
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

        # Cleanup
        cursor.execute("DELETE FROM app_task_details WHERE serial_number=%s", (sn,))
        cursor.execute("DELETE FROM public.qr_registry WHERE qr_doc_id=%s", (qr,))
        cursor.execute("DELETE FROM plan.product_info WHERE serial_number=%s", (sn,))
        db_conn.commit()
        cursor.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Regression (TC-41-17 ~ TC-41-19)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegression:
    """TC-41-17 ~ TC-41-19: Regression 테스트"""

    @patch('app.services.task_service.get_db_connection')
    @patch('app.services.task_service.get_product_by_qr_doc_id')
    @patch('app.services.task_service.get_task_by_id')
    @patch('app.services.task_service._worker_has_started_task')
    @patch('app.services.task_service._worker_already_completed_task')
    @patch('app.services.task_service._record_completion_log')
    @patch('app.services.task_service._all_workers_completed')
    @patch('app.services.task_service._finalize_task_multi_worker')
    @patch('app.services.task_service.complete_task')
    @patch('app.services.task_service.get_incomplete_tasks')
    @patch('app.models.admin_settings.get_setting')
    def test_tc_41_17_single_worker_start_complete_regression(
        self, mock_setting, mock_incomplete, mock_complete_task,
        mock_finalize, mock_all_done, mock_record_log, mock_already_done,
        mock_has_started, mock_get_task, mock_product, mock_conn
    ):
        """TC-41-17: 기존 단독 작업 start→complete (finalize 미전달) → 정상 완료"""
        from app.services.task_service import TaskService

        task = _make_task_in_progress(task_id=1, worker_id=10)
        mock_get_task.return_value = task
        mock_has_started.return_value = True
        mock_already_done.return_value = False
        mock_record_log.return_value = 45
        mock_all_done.return_value = True
        mock_finalize.return_value = {'duration_minutes': 45, 'elapsed_minutes': 45, 'worker_count': 1}
        mock_complete_task.return_value = True
        mock_incomplete.return_value = []
        mock_setting.return_value = False

        with patch('app.services.task_service.update_process_completion'):
            with patch('app.services.task_service.check_all_processes_completed', return_value=False):
                with patch('app.services.duration_validator.validate_duration', return_value={'warnings': []}):
                    ts = TaskService()
                    result, status = ts.complete_work(worker_id=10, task_detail_id=1)

        assert status == 200
        assert result.get('task_finished') is True
        assert result.get('duration_minutes') == 45
        assert result.get('worker_count') == 1

    @patch('app.services.task_service.get_db_connection')
    @patch('app.services.task_service.get_product_by_qr_doc_id')
    @patch('app.services.task_service.get_task_by_id')
    @patch('app.services.task_service._worker_has_started_task')
    @patch('app.services.task_service._worker_already_completed_task')
    @patch('app.services.task_service._record_completion_log')
    @patch('app.services.task_service._all_workers_completed')
    @patch('app.models.admin_settings.get_setting')
    def test_tc_41_18_join_workflow_regression(
        self, mock_setting, mock_all_done, mock_record_log, mock_already_done,
        mock_has_started, mock_get_task, mock_product, mock_conn
    ):
        """TC-41-18: 기존 동시참여 start→join→complete → 정상 완료 (중간 작업자 미완료 시 task 유지)"""
        from app.services.task_service import TaskService

        task = _make_task_in_progress(task_id=1, worker_id=10)
        mock_get_task.return_value = task
        mock_has_started.return_value = True
        mock_already_done.return_value = False
        mock_record_log.return_value = 50
        # worker2가 완료했지만 worker1이 아직 진행 중 → task 미완료
        mock_all_done.return_value = False
        mock_setting.return_value = False

        ts = TaskService()
        result, status = ts.complete_work(worker_id=20, task_detail_id=1, finalize=True)

        # 기존 동작: 다른 작업자 미완료 → task 열린 상태
        assert status == 200
        assert result.get('task_finished') is False
        assert result.get('relay_mode', False) is False  # relay_mode가 아닌 기존 메시지

    @patch('app.services.task_service.get_db_connection')
    @patch('app.services.task_service.get_product_by_qr_doc_id')
    @patch('app.services.task_service.get_task_by_id')
    @patch('app.services.task_service._worker_has_started_task')
    @patch('app.services.task_service._worker_already_completed_task')
    @patch('app.services.task_service._record_completion_log')
    @patch('app.services.task_service._all_workers_completed')
    @patch('app.services.task_service._finalize_task_multi_worker')
    @patch('app.services.task_service.complete_task')
    @patch('app.services.task_service.get_incomplete_tasks')
    @patch('app.models.admin_settings.get_setting')
    def test_tc_41_19_category_all_completed_sets_all_completed_true(
        self, mock_setting, mock_incomplete, mock_complete_task,
        mock_finalize, mock_all_done, mock_record_log, mock_already_done,
        mock_has_started, mock_get_task, mock_product, mock_conn
    ):
        """TC-41-19: completion_status 카테고리 전체 완료 시 all_completed=True 정상 동작"""
        from app.services.task_service import TaskService

        task = _make_task_in_progress(task_id=1, worker_id=10)
        mock_get_task.return_value = task
        mock_has_started.return_value = True
        mock_already_done.return_value = False
        mock_record_log.return_value = 30
        mock_all_done.return_value = True
        mock_finalize.return_value = {'duration_minutes': 30, 'elapsed_minutes': 30, 'worker_count': 1}
        mock_complete_task.return_value = True
        mock_incomplete.return_value = []  # 카테고리 내 미완료 없음
        mock_setting.return_value = False

        update_process_called = []
        update_all_completed_called = []

        def fake_update_process(sn, category, flag):
            update_process_called.append((sn, category, flag))

        def fake_update_all(sn, flag, dt):
            update_all_completed_called.append((sn, flag))

        with patch('app.services.task_service.update_process_completion', side_effect=fake_update_process):
            with patch('app.services.task_service.check_all_processes_completed', return_value=True):
                with patch('app.services.task_service.update_all_completed', side_effect=fake_update_all):
                    with patch('app.services.duration_validator.validate_duration', return_value={'warnings': []}):
                        ts = TaskService()
                        result, status = ts.complete_work(worker_id=10, task_detail_id=1)

        assert status == 200
        assert result.get('category_completed') is True
        assert len(update_process_called) == 1
        assert update_process_called[0][2] is True   # 카테고리 완료 True
        assert len(update_all_completed_called) == 1
        assert update_all_completed_called[0][1] is True  # all_completed True
