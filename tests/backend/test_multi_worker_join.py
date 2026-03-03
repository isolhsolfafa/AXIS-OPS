"""
Sprint 15: 다중 작업자 참여 테스트 (BUG-12)
my_status API 필드 + 멀티 작업자 시작/완료 로직 검증
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

KST = timezone(timedelta(hours=9))

@dataclass
class MockTask:
    id: int = 1
    worker_id: int = None
    serial_number: str = 'TEST-SN-001'
    qr_doc_id: str = 'DOC_TEST-SN-001'
    task_category: str = 'MECH'
    task_id: str = 'SELF_INSPECTION'
    task_name: str = '자주검사'
    started_at: datetime = None
    completed_at: datetime = None
    duration_minutes: int = None
    is_applicable: bool = True
    location_qr_verified: bool = False
    is_paused: bool = False
    total_pause_minutes: int = 0
    created_at: datetime = None
    updated_at: datetime = None
    elapsed_minutes: int = None
    worker_count: int = 1
    force_closed: bool = False


class TestMultiWorkerJoin:
    """TC-MW-01~10: 다중 작업자 참여 테스트"""

    @patch('app.services.task_service.get_db_connection')
    @patch('app.services.task_service.get_product_by_qr_doc_id')
    @patch('app.services.task_service.get_task_by_id')
    @patch('app.services.task_service._worker_has_started_task')
    @patch('app.models.admin_settings.get_setting')
    def test_tc_mw_01_worker2_can_start_same_task(self, mock_setting, mock_has_started, mock_get_task, mock_product, mock_conn):
        """TC-MW-01: Worker1 starts → Worker2 starts same task → success"""
        from app.services.task_service import TaskService

        task = MockTask(id=1, started_at=datetime(2026, 3, 2, 9, 0, tzinfo=KST), worker_id=10)
        mock_get_task.return_value = task
        mock_has_started.return_value = False  # Worker2 has NOT started this task
        mock_setting.return_value = False  # location_qr_required = False

        mock_conn_obj = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.return_value = mock_conn_obj
        mock_conn_obj.cursor.return_value = mock_cursor

        with patch('app.services.task_service.start_task') as mock_start:
            mock_start.return_value = True
            with patch('app.models.work_start_log.create_work_start_log'):
                ts = TaskService()
                result, status = ts.start_work(worker_id=20, task_detail_id=1)

        assert status == 200
        assert 'started_at' in result

    @patch('app.services.task_service.get_task_by_id')
    @patch('app.services.task_service._worker_has_started_task')
    @patch('app.models.admin_settings.get_setting')
    def test_tc_mw_02_same_worker_start_twice_rejected(self, mock_setting, mock_has_started, mock_get_task):
        """TC-MW-02: Worker1 starts → Worker1 starts again → 400 TASK_ALREADY_STARTED"""
        from app.services.task_service import TaskService

        task = MockTask(id=1, started_at=datetime(2026, 3, 2, 9, 0, tzinfo=KST), worker_id=10)
        mock_get_task.return_value = task
        mock_has_started.return_value = True  # Worker1 already started
        mock_setting.return_value = False

        ts = TaskService()
        result, status = ts.start_work(worker_id=10, task_detail_id=1)

        assert status == 400
        assert result['error'] == 'TASK_ALREADY_STARTED'

    def test_tc_mw_03_my_status_not_started(self):
        """TC-MW-03: my_status='not_started' for non-participating worker"""
        # _task_to_dict doesn't include my_status; it's added in route
        # Test the logic: if worker has no start_log, status is not_started
        from app.services.task_service import _worker_has_started_task
        with patch('app.services.task_service.get_db_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value = MagicMock(cursor=MagicMock(return_value=mock_cursor))
            mock_cursor.fetchone.return_value = None

            result = _worker_has_started_task(task_detail_id=1, worker_id=99)
            assert result is False  # not_started

    def test_tc_mw_04_my_status_in_progress(self):
        """TC-MW-04: my_status='in_progress' for participating worker (started but not completed)"""
        from app.services.task_service import _worker_has_started_task
        with patch('app.services.task_service.get_db_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value = MagicMock(cursor=MagicMock(return_value=mock_cursor))
            mock_cursor.fetchone.return_value = {'id': 1}

            result = _worker_has_started_task(task_detail_id=1, worker_id=10)
            assert result is True  # in_progress (has started)

    def test_tc_mw_05_my_status_completed(self):
        """TC-MW-05: my_status='completed' for worker who completed"""
        from app.services.task_service import _worker_already_completed_task
        with patch('app.services.task_service.get_db_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value = MagicMock(cursor=MagicMock(return_value=mock_cursor))
            mock_cursor.fetchone.return_value = {'id': 1}

            result = _worker_already_completed_task(task_detail_id=1, worker_id=10)
            assert result is True  # completed

    @patch('app.services.task_service.get_db_connection')
    def test_tc_mw_06_worker1_done_worker2_pending_task_not_finished(self, mock_conn):
        """TC-MW-06: Worker1 completes + Worker2 not complete → task not finished"""
        from app.services.task_service import _all_workers_completed

        mock_cursor = MagicMock()
        mock_conn.return_value = MagicMock(cursor=MagicMock(return_value=mock_cursor))
        mock_cursor.fetchone.side_effect = [
            {'started_count': 2},   # 2 workers started
            {'completed_count': 1}, # only 1 completed
        ]

        result = _all_workers_completed(task_detail_id=1)
        assert result is False

    @patch('app.services.task_service.get_db_connection')
    def test_tc_mw_07_all_workers_done_task_finishes(self, mock_conn):
        """TC-MW-07: All workers complete → task finishes"""
        from app.services.task_service import _all_workers_completed

        mock_cursor = MagicMock()
        mock_conn.return_value = MagicMock(cursor=MagicMock(return_value=mock_cursor))
        mock_cursor.fetchone.side_effect = [
            {'started_count': 2},   # 2 workers started
            {'completed_count': 2}, # 2 completed
        ]

        result = _all_workers_completed(task_detail_id=1)
        assert result is True

    @patch('app.services.task_service.get_db_connection')
    def test_tc_mw_08_three_workers_two_done_not_finished(self, mock_conn):
        """TC-MW-08: 3 started, 2 completed, 1 pending → not finished"""
        from app.services.task_service import _all_workers_completed

        mock_cursor = MagicMock()
        mock_conn.return_value = MagicMock(cursor=MagicMock(return_value=mock_cursor))
        mock_cursor.fetchone.side_effect = [
            {'started_count': 3},
            {'completed_count': 2},
        ]

        result = _all_workers_completed(task_detail_id=1)
        assert result is False

    def test_tc_mw_09_gst_api_my_status(self):
        """TC-MW-09: GST API response includes my_status field"""
        # Verify that gst.py adds my_status to product dict
        # This is a structural test - verify the code path exists
        import app.routes.gst as gst_module
        source = open(gst_module.__file__).read()
        assert "my_status" in source, "gst.py must include my_status in response"
        assert "my_status_map" in source, "gst.py must use my_status_map for batch query"

    def test_tc_mw_10_legacy_task_my_status_fallback(self):
        """TC-MW-10: Legacy task (no work_start_log) → my_status='not_started' fallback"""
        # In work.py, when task_db_ids exist but no start_log entries:
        # my_status_map won't have the task_id → defaults to 'not_started'
        import app.routes.work as work_module
        source = open(work_module.__file__).read()
        assert "my_status_map.get(tid, 'not_started')" in source, \
            "work.py must default my_status to 'not_started'"
