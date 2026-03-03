"""
Working Hours (근무시간) 재검증 테스트
Sprint 15: _calculate_working_minutes() 함수의 break time 차감 검증

테스트 대상: backend/app/services/task_service.py
- _calculate_working_minutes(started_at, completed_at)
- _calculate_break_overlap(work_start, work_end, break_start_str, break_end_str)

_calculate_working_minutes 내부에서 get_setting은 로컬 임포트로 불러오기 때문에
올바른 mock 경로는 'app.models.admin_settings.get_setting' 임.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta

# KST 타임존 (UTC+9)
KST = timezone(timedelta(hours=9))

# 표준 휴게시간 설정 (admin_settings mock용)
_DEFAULT_BREAK_SETTINGS = {
    'break_morning_start': '10:00',
    'break_morning_end': '10:20',
    'lunch_start': '11:20',
    'lunch_end': '12:20',
    'break_afternoon_start': '15:00',
    'break_afternoon_end': '15:20',
    'dinner_start': '17:00',
    'dinner_end': '18:00',
}


def _make_break_side_effect(settings: dict):
    """get_setting mock의 side_effect 팩토리 함수"""
    def side_effect(key, default=None):
        return settings.get(key, default)
    return side_effect


class TestWorkingHoursCalculation:
    """근무시간 계산 — 휴게시간 차감 검증 (7개 테스트)"""

    @patch('app.models.admin_settings.get_setting')
    def test_no_break_overlap(self, mock_get_setting):
        """
        작업시간이 휴게시간과 겹치지 않으면 raw_minutes 그대로 반환

        Work: 08:00 ~ 09:30 KST (90분)
        Break: 10:00~10:20, 11:20~12:20, 15:00~15:20, 17:00~18:00
        → 모든 휴게시간이 작업 종료(09:30) 이후 → 겹침 없음
        Expected: 90분 (차감 없음)
        """
        from app.services.task_service import _calculate_working_minutes

        mock_get_setting.side_effect = _make_break_side_effect(_DEFAULT_BREAK_SETTINGS)

        started = datetime(2026, 3, 1, 8, 0, tzinfo=KST)
        completed = datetime(2026, 3, 1, 9, 30, tzinfo=KST)

        result = _calculate_working_minutes(started, completed)

        assert result == 90, (
            f"휴게시간 미겹침 → raw_minutes=90이어야 함, got {result}"
        )

    @patch('app.models.admin_settings.get_setting')
    def test_full_lunch_overlap(self, mock_get_setting):
        """
        점심시간(11:20~12:20) 완전 포함 → 60분 차감

        Work: 10:30 ~ 14:00 KST (210분)
        오전 휴게(10:00~10:20) → 작업 시작(10:30) 이전 종료 → 겹침 없음
        Lunch(11:20~12:20) → 완전 포함 → 60분 차감
        오후/저녁 → 작업 내 미포함
        Expected: 210 - 60 = 150분
        """
        from app.services.task_service import _calculate_working_minutes

        mock_get_setting.side_effect = _make_break_side_effect(_DEFAULT_BREAK_SETTINGS)

        started = datetime(2026, 3, 1, 10, 30, tzinfo=KST)
        completed = datetime(2026, 3, 1, 14, 0, tzinfo=KST)

        result = _calculate_working_minutes(started, completed)

        # 10:30~14:00 = 210분, 점심(11:20~12:20) 60분 차감 = 150분
        assert result == 150, (
            f"점심시간(60분) 완전 포함 시 150분이어야 함, got {result}"
        )

    @patch('app.models.admin_settings.get_setting')
    def test_partial_break_overlap(self, mock_get_setting):
        """
        오전 휴게(10:00~10:20) 부분 겹침 → 겹치는 만큼만 차감

        Work: 10:10 ~ 11:00 KST (50분)
        Morning break: 10:00~10:20, overlap = 10:10~10:20 = 10분
        Expected: 50 - 10 = 40분
        """
        from app.services.task_service import _calculate_working_minutes

        mock_get_setting.side_effect = _make_break_side_effect(_DEFAULT_BREAK_SETTINGS)

        started = datetime(2026, 3, 1, 10, 10, tzinfo=KST)
        completed = datetime(2026, 3, 1, 11, 0, tzinfo=KST)

        result = _calculate_working_minutes(started, completed)

        assert result == 40, (
            f"오전 휴게 부분 겹침(10분) 차감 후 40분이어야 함, got {result}"
        )

    @patch('app.models.admin_settings.get_setting')
    def test_multiple_breaks_overlap(self, mock_get_setting):
        """
        오전+점심+오후 모두 겹침 → 합산 차감

        Work: 09:00 ~ 16:00 KST (420분)
        Morning: 10:00~10:20 (20분 겹침)
        Lunch: 11:20~12:20 (60분 겹침)
        Afternoon: 15:00~15:20 (20분 겹침)
        Dinner: 17:00~18:00 → 작업 종료(16:00) 이후 → 겹침 없음
        Total break deduction: 100분
        Expected: 420 - 100 = 320분
        """
        from app.services.task_service import _calculate_working_minutes

        mock_get_setting.side_effect = _make_break_side_effect(_DEFAULT_BREAK_SETTINGS)

        started = datetime(2026, 3, 1, 9, 0, tzinfo=KST)
        completed = datetime(2026, 3, 1, 16, 0, tzinfo=KST)

        result = _calculate_working_minutes(started, completed)

        assert result == 320, (
            f"3개 휴게 합산 차감(100분) 후 320분이어야 함, got {result}"
        )

    @patch('app.models.admin_settings.get_setting')
    def test_all_four_breaks_overlap(self, mock_get_setting):
        """
        4개 휴게시간 전부 겹침 (풀데이 작업)

        Work: 08:00 ~ 19:00 KST (660분)
        Morning: 10:00~10:20 (20분)
        Lunch: 11:20~12:20 (60분)
        Afternoon: 15:00~15:20 (20분)
        Dinner: 17:00~18:00 (60분)
        Total: 160분
        Expected: 660 - 160 = 500분
        """
        from app.services.task_service import _calculate_working_minutes

        mock_get_setting.side_effect = _make_break_side_effect(_DEFAULT_BREAK_SETTINGS)

        started = datetime(2026, 3, 1, 8, 0, tzinfo=KST)
        completed = datetime(2026, 3, 1, 19, 0, tzinfo=KST)

        result = _calculate_working_minutes(started, completed)

        assert result == 500, (
            f"4개 휴게 합산 차감(160분) 후 500분이어야 함, got {result}"
        )

    @patch('app.models.admin_settings.get_setting')
    def test_zero_or_negative_duration(self, mock_get_setting):
        """
        완료 시간이 시작 시간과 같거나 이전 → 0 반환

        Case 1: started == completed (0분)
        Case 2: completed < started (음수 → 0)
        Expected: 0
        """
        from app.services.task_service import _calculate_working_minutes

        mock_get_setting.side_effect = _make_break_side_effect(_DEFAULT_BREAK_SETTINGS)

        # Case 1: 동일 시각 (raw_minutes = 0)
        same_time = datetime(2026, 3, 1, 10, 0, tzinfo=KST)
        result_zero = _calculate_working_minutes(same_time, same_time)
        assert result_zero == 0, (
            f"시작=완료 시 0분이어야 함, got {result_zero}"
        )

        # Case 2: 완료가 시작보다 이전 (raw_minutes < 0)
        started = datetime(2026, 3, 1, 12, 0, tzinfo=KST)
        completed_before = datetime(2026, 3, 1, 9, 0, tzinfo=KST)  # 시작보다 3시간 전
        result_negative = _calculate_working_minutes(started, completed_before)
        assert result_negative == 0, (
            f"완료<시작 (음수 duration) 시 0분이어야 함, got {result_negative}"
        )

    @patch('app.models.admin_settings.get_setting')
    def test_missing_break_settings(self, mock_get_setting):
        """
        admin_settings에 break 설정 없으면 차감 없이 raw_minutes 반환

        Work: 10:00 ~ 14:00 KST (240분)
        Break settings: 모두 None (미설정)
        Expected: 240분 (차감 없음)
        """
        from app.services.task_service import _calculate_working_minutes

        # 모든 설정 키에 None 반환 (미설정 시뮬레이션)
        mock_get_setting.return_value = None

        started = datetime(2026, 3, 1, 10, 0, tzinfo=KST)
        completed = datetime(2026, 3, 1, 14, 0, tzinfo=KST)

        result = _calculate_working_minutes(started, completed)

        assert result == 240, (
            f"break 설정 없음 → raw_minutes=240 그대로 반환되어야 함, got {result}"
        )
