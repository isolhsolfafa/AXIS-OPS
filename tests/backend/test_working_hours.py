"""
BUG-8 근무시간 계산 테스트 (_calculate_working_minutes, _calculate_break_overlap)

task_service.py의 근무시간 계산 로직:
- _calculate_working_minutes(started_at, completed_at) → 휴게시간 자동 차감
- _calculate_break_overlap(work_start, work_end, break_start_str, break_end_str) → 겹침 분

테스트 전략: admin_settings의 get_setting을 mock하여 순수 계산 로직만 검증.

TC-WH-01 ~ TC-WH-10: 10개 테스트 케이스
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from zoneinfo import ZoneInfo

KST = ZoneInfo('Asia/Seoul')

# 기본 휴게시간 설정 (admin_settings mock용)
DEFAULT_BREAK_SETTINGS = {
    'break_morning_start': '10:00',
    'break_morning_end': '10:20',
    'lunch_start': '11:20',
    'lunch_end': '12:20',
    'break_afternoon_start': '15:00',
    'break_afternoon_end': '15:20',
    'dinner_start': '17:00',
    'dinner_end': '18:00',
}

NO_BREAK_SETTINGS = {}


def _mock_get_setting_factory(settings_dict):
    """admin_settings.get_setting mock 팩토리"""
    def _mock_get_setting(key, default=None):
        return settings_dict.get(key, default)
    return _mock_get_setting


class TestCalculateBreakOverlap:
    """_calculate_break_overlap 단위 테스트"""

    def test_wh01_no_overlap(self):
        """TC-WH-01: 08:00~09:00 작업 (휴게시간 없음) → 0분 겹침"""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
        from app.services.task_service import _calculate_break_overlap

        work_start = datetime(2026, 3, 2, 8, 0, tzinfo=KST)
        work_end = datetime(2026, 3, 2, 9, 0, tzinfo=KST)

        overlap = _calculate_break_overlap(work_start, work_end, '10:00', '10:20')
        assert overlap == 0, f"08:00~09:00 vs break 10:00~10:20: expected 0, got {overlap}"

    def test_wh04_work_entirely_within_break(self):
        """TC-WH-04: 작업이 휴게시간 내에 완전히 포함 → 작업시간 전체가 겹침"""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
        from app.services.task_service import _calculate_break_overlap

        # 10:05~10:15 작업, 10:00~10:20 휴게
        work_start = datetime(2026, 3, 2, 10, 5, tzinfo=KST)
        work_end = datetime(2026, 3, 2, 10, 15, tzinfo=KST)

        overlap = _calculate_break_overlap(work_start, work_end, '10:00', '10:20')
        assert overlap == 10, f"10:05~10:15 vs 10:00~10:20: expected 10, got {overlap}"

    def test_wh05_work_starts_during_break(self):
        """TC-WH-05: 작업이 휴게 중 시작, 휴게 후 종료 → 부분 겹침"""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
        from app.services.task_service import _calculate_break_overlap

        # 10:10~10:40 작업, 10:00~10:20 휴게 → 10분 겹침
        work_start = datetime(2026, 3, 2, 10, 10, tzinfo=KST)
        work_end = datetime(2026, 3, 2, 10, 40, tzinfo=KST)

        overlap = _calculate_break_overlap(work_start, work_end, '10:00', '10:20')
        assert overlap == 10, f"10:10~10:40 vs 10:00~10:20: expected 10, got {overlap}"

    def test_wh06_work_ends_during_break(self):
        """TC-WH-06: 작업이 휴게 전 시작, 휴게 중 종료 → 부분 겹침"""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
        from app.services.task_service import _calculate_break_overlap

        # 09:50~10:10 작업, 10:00~10:20 휴게 → 10분 겹침
        work_start = datetime(2026, 3, 2, 9, 50, tzinfo=KST)
        work_end = datetime(2026, 3, 2, 10, 10, tzinfo=KST)

        overlap = _calculate_break_overlap(work_start, work_end, '10:00', '10:20')
        assert overlap == 10, f"09:50~10:10 vs 10:00~10:20: expected 10, got {overlap}"

    def test_wh08_multi_day_overlap(self):
        """TC-WH-08: 다일 작업 (day1 16:00 ~ day2 11:00) → 각 날짜의 휴게시간 차감"""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
        from app.services.task_service import _calculate_break_overlap

        # day1 16:00 ~ day2 11:00 vs dinner 17:00~18:00
        # day1: 17:00~18:00 overlap = 60분
        # day2: 작업 11:00 종료인데 dinner 17:00~18:00 → 0분
        work_start = datetime(2026, 3, 2, 16, 0, tzinfo=KST)
        work_end = datetime(2026, 3, 3, 11, 0, tzinfo=KST)

        overlap = _calculate_break_overlap(work_start, work_end, '17:00', '18:00')
        assert overlap == 60, f"Multi-day dinner overlap: expected 60, got {overlap}"


class TestCalculateWorkingMinutes:
    """_calculate_working_minutes 통합 테스트 (admin_settings mock)"""

    def test_wh01_no_break_overlap(self):
        """TC-WH-01: 08:00~09:00 작업 (아무 휴게시간과 겹치지 않음) → 60분"""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
        from app.services.task_service import _calculate_working_minutes

        work_start = datetime(2026, 3, 2, 8, 0, tzinfo=KST)
        work_end = datetime(2026, 3, 2, 9, 0, tzinfo=KST)

        with patch('app.models.admin_settings.get_setting',
                   side_effect=_mock_get_setting_factory(DEFAULT_BREAK_SETTINGS)):
            result = _calculate_working_minutes(work_start, work_end)

        assert result == 60, f"08:00~09:00, no break overlap: expected 60, got {result}"

    def test_wh02_lunch_overlap(self):
        """TC-WH-02: 08:00~13:00 점심 겹침 → 300 - 60(lunch) = 240분"""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
        from app.services.task_service import _calculate_working_minutes

        work_start = datetime(2026, 3, 2, 8, 0, tzinfo=KST)
        work_end = datetime(2026, 3, 2, 13, 0, tzinfo=KST)

        with patch('app.models.admin_settings.get_setting',
                   side_effect=_mock_get_setting_factory(DEFAULT_BREAK_SETTINGS)):
            result = _calculate_working_minutes(work_start, work_end)

        # raw = 300분, morning_break 10:00~10:20 = 20분, lunch 11:20~12:20 = 60분
        # 총 차감 = 80분, net = 220분
        expected = 300 - 20 - 60
        assert result == expected, f"08:00~13:00: expected {expected}, got {result}"

    def test_wh03_full_day_all_breaks(self):
        """TC-WH-03: 08:00~17:00 전체 근무 → 4개 휴게시간 모두 차감"""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
        from app.services.task_service import _calculate_working_minutes

        work_start = datetime(2026, 3, 2, 8, 0, tzinfo=KST)
        work_end = datetime(2026, 3, 2, 17, 0, tzinfo=KST)

        with patch('app.models.admin_settings.get_setting',
                   side_effect=_mock_get_setting_factory(DEFAULT_BREAK_SETTINGS)):
            result = _calculate_working_minutes(work_start, work_end)

        # raw = 540분
        # morning_break 10:00~10:20 = 20분
        # lunch 11:20~12:20 = 60분
        # afternoon 15:00~15:20 = 20분
        # dinner 17:00~18:00 → 끝이 17:00이므로 0분 (overlap_end = min(17:00, 18:00) = 17:00, start=max(8:00,17:00)=17:00 → 0)
        expected = 540 - 20 - 60 - 20 - 0
        assert result == expected, f"08:00~17:00: expected {expected}, got {result}"

    def test_wh07_no_break_settings(self):
        """TC-WH-07: 휴게시간 설정 없음 → 차감 없이 원본 분 반환"""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
        from app.services.task_service import _calculate_working_minutes

        work_start = datetime(2026, 3, 2, 8, 0, tzinfo=KST)
        work_end = datetime(2026, 3, 2, 17, 0, tzinfo=KST)

        with patch('app.models.admin_settings.get_setting',
                   side_effect=_mock_get_setting_factory(NO_BREAK_SETTINGS)):
            result = _calculate_working_minutes(work_start, work_end)

        assert result == 540, f"No break settings: expected 540, got {result}"

    def test_wh08_multi_day_work(self):
        """TC-WH-08: 다일 작업 (day1 16:00 ~ day2 11:00) → 각 날짜 휴게 차감"""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
        from app.services.task_service import _calculate_working_minutes

        work_start = datetime(2026, 3, 2, 16, 0, tzinfo=KST)
        work_end = datetime(2026, 3, 3, 11, 0, tzinfo=KST)

        with patch('app.models.admin_settings.get_setting',
                   side_effect=_mock_get_setting_factory(DEFAULT_BREAK_SETTINGS)):
            result = _calculate_working_minutes(work_start, work_end)

        # raw = 19시간 = 1140분
        # day1 breaks: dinner 17:00~18:00 → 60분
        # day2 breaks: morning 10:00~10:20 → 20분, lunch 11:00 전이므로 lunch 11:20~12:20 → 0분
        # total deduction = 60 + 20 = 80
        expected = 1140 - 60 - 20
        assert result == expected, f"Multi-day: expected {expected}, got {result}"


class TestRecordCompletionUsesWorkingMinutes:
    """_record_completion_log이 _calculate_working_minutes를 사용하는지 검증"""

    def test_wh09_record_completion_calls_working_minutes(self):
        """TC-WH-09: _record_completion_log에서 _calculate_working_minutes가 호출됨"""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

        mock_task = MagicMock()
        mock_task.id = 1
        mock_task.serial_number = 'SN-TEST'
        mock_task.qr_doc_id = 'DOC-TEST'
        mock_task.task_category = 'MECH'
        mock_task.task_id = 'SELF_INSPECTION'
        mock_task.task_name = 'Test Task'

        started_at = datetime(2026, 3, 2, 8, 0, tzinfo=KST)
        completed_at = datetime(2026, 3, 2, 13, 0, tzinfo=KST)

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # DB에서 started_at 반환 시뮬레이션
        mock_cursor.fetchone.return_value = {'started_at': started_at}

        with patch('app.services.task_service.get_db_connection', return_value=mock_conn), \
             patch('app.services.task_service._calculate_working_minutes', return_value=220) as mock_calc, \
             patch('app.models.work_completion_log.create_work_completion_log'):
            from app.services.task_service import _record_completion_log
            result = _record_completion_log(mock_task, worker_id=1, completed_at=completed_at)

        mock_calc.assert_called_once_with(started_at, completed_at)
        assert result == 220, f"Expected 220 from mock, got {result}"


class TestFinalizeTaskManualPauseOnly:
    """_finalize_task_multi_worker이 수동 pause만 차감하는지 검증"""

    def test_wh10_only_manual_pauses_subtracted(self):
        """TC-WH-10: _finalize_task_multi_worker에서 break auto-pause는 차감 안 함"""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

        completed_at = datetime(2026, 3, 2, 17, 0, tzinfo=KST)
        first_started = datetime(2026, 3, 2, 8, 0, tzinfo=KST)

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # 순서대로 fetchone 결과 세팅:
        # 1. SUM(duration_minutes) from work_completion_log → 480
        # 2. SUM(manual_pause) → 30 (수동 pause만)
        # 3. MIN(started_at), COUNT(DISTINCT worker_id) → first_started, 2
        mock_cursor.fetchone.side_effect = [
            {'duration_minutes': 480},     # raw duration sum
            {'manual_pause': 30},          # manual pause only (break excluded)
            {'first_started': first_started, 'worker_count': 2},
        ]

        with patch('app.services.task_service.get_db_connection', return_value=mock_conn):
            from app.services.task_service import _finalize_task_multi_worker
            result = _finalize_task_multi_worker(task_detail_id=1, completed_at=completed_at)

        # duration = 480 - 30(manual only) = 450
        assert result['duration_minutes'] == 450, (
            f"Expected 450 (480 raw - 30 manual pause), got {result['duration_minutes']}"
        )
        assert result['worker_count'] == 2

        # SQL에서 break 유형 제외 조건이 포함됐는지 확인
        # 두 번째 execute 호출의 SQL에 NOT IN 조건 확인
        calls = mock_cursor.execute.call_args_list
        pause_query = calls[1][0][0]  # 두 번째 쿼리
        assert 'NOT IN' in pause_query, "Manual pause query should exclude break types"
        assert 'break_morning' in pause_query, "Should exclude break_morning"
        assert 'lunch' in pause_query, "Should exclude lunch"


class TestCalculateBreakOverlapEdgeCases:
    """_calculate_break_overlap 엣지 케이스 추가 테스트"""

    def test_wh_invalid_break_time_format(self):
        """TC-WH-11: 잘못된 휴게시간 형식 → 0분 반환 (에러 없음)"""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
        from app.services.task_service import _calculate_break_overlap

        work_start = datetime(2026, 3, 2, 8, 0, tzinfo=KST)
        work_end = datetime(2026, 3, 2, 17, 0, tzinfo=KST)

        # 잘못된 형식
        assert _calculate_break_overlap(work_start, work_end, 'invalid', '10:20') == 0
        assert _calculate_break_overlap(work_start, work_end, '10:00', '') == 0
        assert _calculate_break_overlap(work_start, work_end, None, '10:20') == 0

    def test_wh_zero_duration_work(self):
        """TC-WH-12: 작업시간 0분 (started_at == completed_at) → 0분"""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
        from app.services.task_service import _calculate_working_minutes

        same_time = datetime(2026, 3, 2, 10, 0, tzinfo=KST)

        with patch('app.models.admin_settings.get_setting',
                   side_effect=_mock_get_setting_factory(DEFAULT_BREAK_SETTINGS)):
            result = _calculate_working_minutes(same_time, same_time)

        assert result == 0, f"Zero duration work should return 0, got {result}"

    def test_wh_work_covers_exact_break_period(self):
        """TC-WH-13: 작업 == 정확히 휴게시간 (10:00~10:20) → 차감 후 0분"""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
        from app.services.task_service import _calculate_working_minutes

        work_start = datetime(2026, 3, 2, 10, 0, tzinfo=KST)
        work_end = datetime(2026, 3, 2, 10, 20, tzinfo=KST)

        with patch('app.models.admin_settings.get_setting',
                   side_effect=_mock_get_setting_factory(DEFAULT_BREAK_SETTINGS)):
            result = _calculate_working_minutes(work_start, work_end)

        # raw = 20분, morning break 20분 차감 → 0분
        assert result == 0, f"Work during exact break: expected 0, got {result}"

    def test_wh_negative_duration_returns_zero(self):
        """TC-WH-14: completed_at < started_at → 0분 (음수 방지)"""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
        from app.services.task_service import _calculate_working_minutes

        work_start = datetime(2026, 3, 2, 17, 0, tzinfo=KST)
        work_end = datetime(2026, 3, 2, 8, 0, tzinfo=KST)  # 역전

        with patch('app.models.admin_settings.get_setting',
                   side_effect=_mock_get_setting_factory(DEFAULT_BREAK_SETTINGS)):
            result = _calculate_working_minutes(work_start, work_end)

        assert result == 0, f"Negative duration should return 0, got {result}"

    def test_wh_partial_break_settings_only(self):
        """TC-WH-15: 일부 휴게시간만 설정 → 설정된 것만 차감"""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
        from app.services.task_service import _calculate_working_minutes

        partial_settings = {
            'lunch_start': '11:20',
            'lunch_end': '12:20',
            # 다른 설정 없음
        }

        work_start = datetime(2026, 3, 2, 8, 0, tzinfo=KST)
        work_end = datetime(2026, 3, 2, 17, 0, tzinfo=KST)

        with patch('app.models.admin_settings.get_setting',
                   side_effect=_mock_get_setting_factory(partial_settings)):
            result = _calculate_working_minutes(work_start, work_end)

        # raw = 540분, lunch만 60분 차감 = 480분
        assert result == 480, f"Partial settings: expected 480, got {result}"

    def test_wh_full_day_with_dinner_overlap(self):
        """TC-WH-16: 08:00~18:00 작업 → dinner 17:00~18:00 60분 차감"""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
        from app.services.task_service import _calculate_working_minutes

        work_start = datetime(2026, 3, 2, 8, 0, tzinfo=KST)
        work_end = datetime(2026, 3, 2, 18, 0, tzinfo=KST)

        with patch('app.models.admin_settings.get_setting',
                   side_effect=_mock_get_setting_factory(DEFAULT_BREAK_SETTINGS)):
            result = _calculate_working_minutes(work_start, work_end)

        # raw = 600분
        # morning 20 + lunch 60 + afternoon 20 + dinner 60 = 160분
        expected = 600 - 160
        assert result == expected, f"Full day 08-18: expected {expected}, got {result}"
