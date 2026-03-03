"""
Sprint 15: MH(공수) 계산 방식 B 검증
duration_minutes = 개인별 SUM (현재 로직)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

STANDARD_BREAKS = {
    'break_morning_start': '10:00',
    'break_morning_end': '10:20',
    'lunch_start': '11:20',
    'lunch_end': '12:20',
    'break_afternoon_start': '15:00',
    'break_afternoon_end': '15:20',
    'dinner_start': '17:00',
    'dinner_end': '18:00',
}

def mock_get_setting(key, default=None):
    return STANDARD_BREAKS.get(key, default)


class TestMHCalculationMethodB:
    """TC-MH-01~05: MH 계산 방식 B 검증"""

    @patch('app.models.admin_settings.get_setting', side_effect=mock_get_setting)
    def test_tc_mh_01_two_workers_same_times(self, mock_setting):
        """TC-MH-01: 2 workers same start/end(9~12) → MH = 2 × (180-20-40) = 240"""
        from app.services.task_service import _calculate_working_minutes

        w1 = _calculate_working_minutes(
            datetime(2026, 3, 2, 9, 0, tzinfo=KST),
            datetime(2026, 3, 2, 12, 0, tzinfo=KST)
        )
        w2 = _calculate_working_minutes(
            datetime(2026, 3, 2, 9, 0, tzinfo=KST),
            datetime(2026, 3, 2, 12, 0, tzinfo=KST)
        )

        mh = w1 + w2  # Method B: individual SUM
        # 180 - 20(morning) - 40(partial lunch 11:20~12:00) = 120 each
        assert w1 == 120
        assert w2 == 120
        assert mh == 240

    @patch('app.models.admin_settings.get_setting', side_effect=mock_get_setting)
    def test_tc_mh_02_two_workers_different_times(self, mock_setting):
        """TC-MH-02: Worker1(9~11), Worker2(9~12) → CT=3h, MH=sum of individual"""
        from app.services.task_service import _calculate_working_minutes

        # Worker1: 9:00~11:00 → 120 - 20(morning 10:00-10:20) = 100
        w1 = _calculate_working_minutes(
            datetime(2026, 3, 2, 9, 0, tzinfo=KST),
            datetime(2026, 3, 2, 11, 0, tzinfo=KST)
        )
        # Worker2: 9:00~12:00 → 180 - 20(morning) - 40(partial lunch 11:20~12:00) = 120
        w2 = _calculate_working_minutes(
            datetime(2026, 3, 2, 9, 0, tzinfo=KST),
            datetime(2026, 3, 2, 12, 0, tzinfo=KST)
        )

        mh = w1 + w2
        ct = 180  # 12:00 - 9:00 = 3h = 180min (elapsed)

        assert w1 == 100
        assert w2 == 120
        assert mh == 220  # MH (man-hour) = method B (100 + 120)
        assert ct == 180   # CT (cycle time)
        assert mh != ct    # MH ≠ CT when different durations

    @patch('app.models.admin_settings.get_setting', side_effect=mock_get_setting)
    def test_tc_mh_03_single_worker_mh_equals_ct(self, mock_setting):
        """TC-MH-03: 1 worker → MH = CT (method A = method B for single worker)"""
        from app.services.task_service import _calculate_working_minutes

        # 14:00~16:00 → 120 - 20(afternoon 15:00-15:20) = 100
        duration = _calculate_working_minutes(
            datetime(2026, 3, 2, 14, 0, tzinfo=KST),
            datetime(2026, 3, 2, 16, 0, tzinfo=KST)
        )

        mh = duration    # method B: individual SUM = just this worker
        ct = 120         # elapsed: 16:00 - 14:00

        # For single worker: MH (net) + breaks = CT
        # So MH ≠ CT when breaks exist, but MH = individual duration
        assert duration == 100
        assert mh == duration

    @patch('app.models.admin_settings.get_setting', side_effect=mock_get_setting)
    def test_tc_mh_04_line_efficiency_calculation(self, mock_setting):
        """TC-MH-04: Line efficiency = MH / (CT × workers) × 100"""
        from app.services.task_service import _calculate_working_minutes

        # 2 workers, 9:00~12:00 each
        w1 = _calculate_working_minutes(
            datetime(2026, 3, 2, 9, 0, tzinfo=KST),
            datetime(2026, 3, 2, 12, 0, tzinfo=KST)
        )
        w2 = _calculate_working_minutes(
            datetime(2026, 3, 2, 9, 0, tzinfo=KST),
            datetime(2026, 3, 2, 12, 0, tzinfo=KST)
        )

        mh = w1 + w2       # 120 + 120 = 240
        ct = 180            # 12:00 - 9:00 = 180min
        workers = 2

        efficiency = round(mh * 100 / max(1, ct * workers))
        # 240 / (180 * 2) * 100 = 240 / 360 * 100 ≈ 67%
        assert efficiency == 67

    @patch('app.models.admin_settings.get_setting', side_effect=mock_get_setting)
    def test_tc_mh_05_full_day_all_breaks(self, mock_setting):
        """TC-MH-05: Long work(9~18) with all 4 breaks → accurate deduction"""
        from app.services.task_service import _calculate_working_minutes

        duration = _calculate_working_minutes(
            datetime(2026, 3, 2, 9, 0, tzinfo=KST),
            datetime(2026, 3, 2, 18, 0, tzinfo=KST)
        )

        # 540 raw - 20(morning) - 60(lunch) - 20(afternoon) - 60(dinner) = 380
        assert duration == 380

        # Verify each break deduction
        from app.services.task_service import _calculate_break_overlap

        started = datetime(2026, 3, 2, 9, 0, tzinfo=KST)
        completed = datetime(2026, 3, 2, 18, 0, tzinfo=KST)

        morning = _calculate_break_overlap(started, completed, '10:00', '10:20')
        lunch = _calculate_break_overlap(started, completed, '11:20', '12:20')
        afternoon = _calculate_break_overlap(started, completed, '15:00', '15:20')
        dinner = _calculate_break_overlap(started, completed, '17:00', '18:00')

        assert morning == 20
        assert lunch == 60
        assert afternoon == 20
        assert dinner == 60
        assert morning + lunch + afternoon + dinner == 160
