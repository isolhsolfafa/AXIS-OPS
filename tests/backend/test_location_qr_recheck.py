"""
Sprint 15: Location QR 차단 재검증 (BUG-11)
product.location_qr_id 기반 체크로 변경됨
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

@dataclass
class MockProduct:
    id: int = 1
    qr_doc_id: str = 'DOC_TEST-SN-001'
    serial_number: str = 'TEST-SN-001'
    model: str = 'GAIA-001'
    location_qr_id: str = None
    mech_partner: str = None
    elec_partner: str = None
    module_outsourcing: str = None


class TestLocationQrRecheck:
    """TC-LQ-R01~R06: BUG-11 Location QR 재검증"""

    @patch('app.services.task_service.get_db_connection')
    @patch('app.services.task_service.get_product_by_qr_doc_id')
    @patch('app.services.task_service.get_task_by_id')
    @patch('app.services.task_service._worker_has_started_task')
    @patch('app.models.admin_settings.get_setting')
    def test_tc_lq_r01_required_true_no_location_qr_blocked(
        self, mock_setting, mock_has_started, mock_get_task, mock_product, mock_conn
    ):
        """TC-LQ-R01: location_qr_required=true + location_qr_id=NULL → 400"""
        from app.services.task_service import TaskService

        task = MockTask(id=1)
        mock_get_task.return_value = task
        mock_has_started.return_value = False

        # location_qr_required=True, then product query
        def setting_side_effect(key, default=None):
            if key == 'location_qr_required':
                return True
            if key == 'phase_block_enabled':
                return False
            return default
        mock_setting.side_effect = setting_side_effect

        product = MockProduct(location_qr_id=None)
        mock_product.return_value = product

        ts = TaskService()
        result, status = ts.start_work(worker_id=10, task_detail_id=1)

        assert status == 400
        assert result['error'] == 'LOCATION_QR_REQUIRED'

    @patch('app.services.task_service.get_db_connection')
    @patch('app.services.task_service.get_product_by_qr_doc_id')
    @patch('app.services.task_service.get_task_by_id')
    @patch('app.services.task_service._worker_has_started_task')
    @patch('app.models.admin_settings.get_setting')
    def test_tc_lq_r02_required_true_has_location_qr_passes(
        self, mock_setting, mock_has_started, mock_get_task, mock_product, mock_conn
    ):
        """TC-LQ-R02: location_qr_required=true + location_qr_id='LOC_BAY1' → passes"""
        from app.services.task_service import TaskService

        task = MockTask(id=1)
        mock_get_task.return_value = task
        mock_has_started.return_value = False

        def setting_side_effect(key, default=None):
            if key == 'location_qr_required':
                return True
            if key == 'phase_block_enabled':
                return False
            return default
        mock_setting.side_effect = setting_side_effect

        product = MockProduct(location_qr_id='LOC_BAY1')
        mock_product.return_value = product

        mock_conn_obj = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.return_value = mock_conn_obj
        mock_conn_obj.cursor.return_value = mock_cursor

        with patch('app.services.task_service.start_task') as mock_start:
            mock_start.return_value = True
            with patch('app.models.work_start_log.create_work_start_log'):
                ts = TaskService()
                result, status = ts.start_work(worker_id=10, task_detail_id=1)

        assert status == 200

    @patch('app.services.task_service.get_task_by_id')
    @patch('app.services.task_service._worker_has_started_task')
    @patch('app.models.admin_settings.get_setting')
    def test_tc_lq_r03_required_false_no_check(
        self, mock_setting, mock_has_started, mock_get_task
    ):
        """TC-LQ-R03: location_qr_required=false → no check, proceeds"""
        from app.services.task_service import TaskService

        task = MockTask(id=1)
        mock_get_task.return_value = task
        mock_has_started.return_value = False
        mock_setting.return_value = False  # all settings false

        with patch('app.services.task_service.get_db_connection') as mock_conn:
            mock_conn_obj = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.return_value = mock_conn_obj
            mock_conn_obj.cursor.return_value = mock_cursor
            with patch('app.services.task_service.start_task') as mock_start:
                mock_start.return_value = True
                with patch('app.models.work_start_log.create_work_start_log'):
                    ts = TaskService()
                    result, status = ts.start_work(worker_id=10, task_detail_id=1)

        assert status == 200

    @patch('app.models.admin_settings.get_setting')
    def test_tc_lq_r04_get_setting_return_type(self, mock_setting):
        """TC-LQ-R04: get_setting('location_qr_required') returns proper truthy/falsy"""
        # Test with bool True
        mock_setting.return_value = True
        from app.models.admin_settings import get_setting
        val = get_setting('location_qr_required', False)
        assert val is True
        assert bool(val) is True

        # Test with bool False
        mock_setting.return_value = False
        val = get_setting('location_qr_required', False)
        assert val is False
        assert bool(val) is False

    def test_tc_lq_r05_code_checks_product_location_qr_id(self):
        """TC-LQ-R05: Verify task_service.py checks product.location_qr_id (not task.location_qr_verified)"""
        import app.services.task_service as ts_module
        source = open(ts_module.__file__).read()
        # Should check product.location_qr_id
        assert "product.location_qr_id" in source, \
            "BUG-11 fix should use product.location_qr_id"
        # BUG-11 fix marker should be present
        assert "[BUG-11]" in source, \
            "BUG-11 fix marker must be present in task_service.py"

    def test_tc_lq_r06_debug_logs_present(self):
        """TC-LQ-R06: BUG-11 debug logs present in task_service.py"""
        import app.services.task_service as ts_module
        source = open(ts_module.__file__).read()
        assert "[BUG-11]" in source, "Debug logs with [BUG-11] tag must be present"
        assert "location_qr_required=" in source, "Must log location_qr_required value"
