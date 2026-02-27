"""
휴게시간 자동 일시정지 스케줄러 테스트 (Sprint 9)

실제 BE 구현 기준:
  check_break_time_job()              - 매 분 실행 (orchestrator)
  force_pause_all_active_tasks(pause_type, message)  - 강제 일시정지
  send_break_end_notifications(pause_type, message)  - 휴게 종료 알림

휴게시간 정의 (admin_settings 기본값):
  오전 휴게: break_morning (10:00 ~ 10:20)
  점심시간: lunch (11:20 ~ 12:20)
  오후 휴게: break_afternoon (15:00 ~ 15:20)
  저녁시간: dinner (17:00 ~ 18:00)

TC-SCHED-01 ~ TC-SCHED-14: 14개 테스트 케이스
"""

import time
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch


# ============================================================
# 스케줄러 테스트 전용 fixture
# ============================================================
@pytest.fixture(autouse=True)
def cleanup_scheduler_test_data(db_conn):
    """테스트 후 관련 데이터 정리"""
    yield
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            cursor.execute(
                "DELETE FROM workers WHERE email LIKE '%@scheduler_test.com'"
            )
            cursor.execute(
                "DELETE FROM app_alert_logs WHERE alert_type IN ('BREAK_TIME_PAUSE', 'BREAK_TIME_END')"
            )
            db_conn.commit()
            cursor.close()
        except Exception:
            pass


@pytest.fixture
def sched_worker(create_test_worker, get_auth_token):
    """스케줄러 테스트 전용 작업자"""
    unique_email = f'sched_worker_{int(time.time() * 1000)}@scheduler_test.com'
    worker_id = create_test_worker(
        email=unique_email,
        password='Test123!',
        name='Scheduler Test Worker',
        role='MECH',
        approval_status='approved',
        email_verified=True
    )
    token = get_auth_token(worker_id, role='MECH')
    return {'id': worker_id, 'email': unique_email, 'token': token}


@pytest.fixture
def active_task(create_test_task, create_test_product, sched_worker):
    """진행 중인 작업 fixture (스케줄러 테스트용 — 매 호출마다 고유 ID 사용)"""
    suffix = int(time.time() * 1000)
    qr_doc_id = f'DOC-SCHED-{suffix}'
    serial_number = f'SN-SCHED-{suffix}'
    # qr_registry에 제품 먼저 등록 (FK 제약 충족)
    create_test_product(
        qr_doc_id=qr_doc_id,
        serial_number=serial_number
    )
    task_id = create_test_task(
        worker_id=sched_worker['id'],
        serial_number=serial_number,
        qr_doc_id=qr_doc_id,
        task_category='MECH',
        task_id='CABINET_ASSY',
        task_name='캐비넷 조립',
        started_at=datetime.now(timezone.utc)
    )
    return task_id


def _get_task_is_paused(db_conn, task_id) -> bool:
    """DB에서 is_paused 직접 조회"""
    if not db_conn:
        return False
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT is_paused FROM app_task_details WHERE id = %s",
        (task_id,)
    )
    row = cursor.fetchone()
    cursor.close()
    return bool(row[0]) if row else False


def _get_pause_log_count(db_conn, task_id, pause_type=None) -> int:
    """work_pause_log에서 레코드 수 조회"""
    if not db_conn:
        return 0
    cursor = db_conn.cursor()
    if pause_type:
        cursor.execute(
            "SELECT COUNT(*) FROM work_pause_log WHERE task_detail_id = %s AND pause_type = %s",
            (task_id, pause_type)
        )
    else:
        cursor.execute(
            "SELECT COUNT(*) FROM work_pause_log WHERE task_detail_id = %s",
            (task_id,)
        )
    row = cursor.fetchone()
    cursor.close()
    return row[0] if row else 0


def _get_alert_count(db_conn, worker_id, alert_type) -> int:
    """app_alert_logs에서 알림 수 조회"""
    if not db_conn:
        return 0
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM app_alert_logs WHERE target_worker_id = %s AND alert_type = %s",
        (worker_id, alert_type)
    )
    row = cursor.fetchone()
    cursor.close()
    return row[0] if row else 0


# ============================================================
# TestBreakTimeForcePause: 휴게시간 자동 일시정지
# ============================================================
class TestBreakTimeForcePause:
    """force_pause_all_active_tasks 직접 호출 테스트 (TC-SCHED-01 ~ TC-SCHED-06)"""

    def test_force_pause_during_morning_break(
        self, app, sched_worker, active_task, db_conn
    ):
        """
        TC-SCHED-01: 오전 휴게시간 강제 일시정지

        force_pause_all_active_tasks('break_morning', ...) 직접 호출.
        Expected:
        - app_task_details.is_paused == True
        - work_pause_log에 pause_type='break_morning' 레코드 생성
        """
        from app.services.scheduler_service import force_pause_all_active_tasks

        force_pause_all_active_tasks(
            'break_morning',
            '오전 휴게시간이 시작되었습니다. 작업이 자동으로 일시정지됩니다.'
        )

        assert _get_task_is_paused(db_conn, active_task) is True, (
            "Task should be paused after force_pause_all_active_tasks"
        )
        assert _get_pause_log_count(db_conn, active_task, 'break_morning') >= 1, (
            "work_pause_log should have 'break_morning' record"
        )

    def test_force_pause_during_lunch(
        self, app, sched_worker, active_task, db_conn
    ):
        """
        TC-SCHED-02: 점심시간 강제 일시정지

        Expected:
        - work_pause_log.pause_type == 'lunch'
        """
        from app.services.scheduler_service import force_pause_all_active_tasks

        force_pause_all_active_tasks(
            'lunch',
            '점심시간이 시작되었습니다. 작업이 자동으로 일시정지됩니다.'
        )

        assert _get_task_is_paused(db_conn, active_task) is True
        assert _get_pause_log_count(db_conn, active_task, 'lunch') >= 1, (
            "work_pause_log should have 'lunch' record"
        )

    def test_force_pause_during_afternoon_break(
        self, app, sched_worker, active_task, db_conn
    ):
        """
        TC-SCHED-03: 오후 휴게시간 강제 일시정지

        Expected:
        - work_pause_log.pause_type == 'break_afternoon'
        """
        from app.services.scheduler_service import force_pause_all_active_tasks

        force_pause_all_active_tasks(
            'break_afternoon',
            '오후 휴게시간이 시작되었습니다. 작업이 자동으로 일시정지됩니다.'
        )

        assert _get_task_is_paused(db_conn, active_task) is True
        assert _get_pause_log_count(db_conn, active_task, 'break_afternoon') >= 1

    def test_force_pause_during_dinner(
        self, app, sched_worker, active_task, db_conn
    ):
        """
        TC-SCHED-04: 저녁시간 강제 일시정지

        Expected:
        - work_pause_log.pause_type == 'dinner'
        """
        from app.services.scheduler_service import force_pause_all_active_tasks

        force_pause_all_active_tasks(
            'dinner',
            '저녁시간이 시작되었습니다. 작업이 자동으로 일시정지됩니다.'
        )

        assert _get_task_is_paused(db_conn, active_task) is True
        assert _get_pause_log_count(db_conn, active_task, 'dinner') >= 1

    def test_no_duplicate_pause_if_already_paused(
        self, client, sched_worker, active_task, db_conn
    ):
        """
        TC-SCHED-05: 이미 일시정지된 작업은 중복 pause 생성 안 함

        Flow: 수동 pause → force_pause_all_active_tasks 호출
        Expected:
        - 추가 pause 로그 생성 없음 (is_paused=TRUE 작업은 쿼리에서 제외됨)
        """
        from app.services.scheduler_service import force_pause_all_active_tasks

        # 수동으로 먼저 일시정지
        pause_resp = client.post(
            '/api/app/work/pause',
            json={'task_detail_id': active_task},
            headers={'Authorization': f'Bearer {sched_worker["token"]}'}
        )
        assert pause_resp.status_code == 200

        count_before = _get_pause_log_count(db_conn, active_task)

        # 자동 일시정지 시도 (이미 paused 상태)
        force_pause_all_active_tasks(
            'break_morning',
            '오전 휴게시간이 시작되었습니다.'
        )

        count_after = _get_pause_log_count(db_conn, active_task)
        assert count_after == count_before, (
            f"Already-paused task should not get additional pause log: "
            f"before={count_before}, after={count_after}"
        )

    def test_auto_pause_disabled_setting(
        self, app, sched_worker, active_task, db_conn
    ):
        """
        TC-SCHED-06: auto_pause_enabled=false 설정 시 check_break_time_job이 일시정지 안 함

        Expected:
        - is_paused == False 유지
        """
        from app.services.scheduler_service import check_break_time_job

        # auto_pause_enabled를 false로 설정
        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute(
                "UPDATE admin_settings SET setting_value = 'false' "
                "WHERE setting_key = 'auto_pause_enabled'"
            )
            db_conn.commit()
            cursor.close()

        try:
            from zoneinfo import ZoneInfo
            kst = ZoneInfo('Asia/Seoul')
            with patch('app.services.scheduler_service.datetime') as mock_dt:
                mock_now = datetime(2026, 2, 23, 10, 0, 0, tzinfo=kst)
                mock_dt.now.return_value = mock_now
                mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
                check_break_time_job()

            assert _get_task_is_paused(db_conn, active_task) is False, (
                "Task should NOT be paused when auto_pause_enabled=false"
            )
        finally:
            # 원복
            if db_conn and not db_conn.closed:
                cursor = db_conn.cursor()
                cursor.execute(
                    "UPDATE admin_settings SET setting_value = 'true' "
                    "WHERE setting_key = 'auto_pause_enabled'"
                )
                db_conn.commit()
                cursor.close()


# ============================================================
# TestBreakTimeAutoResume: 휴게시간 종료 알림
# ============================================================
class TestBreakTimeAutoResume:
    """send_break_end_notifications 테스트 (TC-SCHED-07 ~ TC-SCHED-10)

    NOTE: BE 구현에서 재개는 작업자가 수동으로 하며,
    send_break_end_notifications는 BREAK_TIME_END 알림만 발송함.
    """

    def test_break_end_notification_after_morning_pause(
        self, app, sched_worker, active_task, db_conn
    ):
        """
        TC-SCHED-07: 오전 휴게 종료 시 BREAK_TIME_END 알림 발송

        Flow: force_pause('break_morning') → send_break_end_notifications('break_morning')
        Expected:
        - app_alert_logs에 BREAK_TIME_END 알림 생성 (target_worker_id == sched_worker.id)
        """
        from app.services.scheduler_service import (
            force_pause_all_active_tasks,
            send_break_end_notifications,
        )

        # 오전 휴게 시작
        force_pause_all_active_tasks(
            'break_morning',
            '오전 휴게시간이 시작되었습니다.'
        )

        alert_before = _get_alert_count(db_conn, sched_worker['id'], 'BREAK_TIME_END')

        # 오전 휴게 종료 알림
        send_break_end_notifications(
            'break_morning',
            '오전 휴게시간이 종료되었습니다. 작업을 재개해주세요.'
        )

        alert_after = _get_alert_count(db_conn, sched_worker['id'], 'BREAK_TIME_END')
        assert alert_after > alert_before, (
            "BREAK_TIME_END alert should be created after morning break ends"
        )

    def test_break_end_notification_after_lunch(
        self, app, sched_worker, active_task, db_conn
    ):
        """
        TC-SCHED-08: 점심시간 종료 알림

        Expected:
        - BREAK_TIME_END 알림 생성
        """
        from app.services.scheduler_service import (
            force_pause_all_active_tasks,
            send_break_end_notifications,
        )

        force_pause_all_active_tasks('lunch', '점심시간이 시작되었습니다.')
        alert_before = _get_alert_count(db_conn, sched_worker['id'], 'BREAK_TIME_END')

        send_break_end_notifications('lunch', '점심시간이 종료되었습니다. 작업을 재개해주세요.')

        alert_after = _get_alert_count(db_conn, sched_worker['id'], 'BREAK_TIME_END')
        assert alert_after > alert_before

    def test_break_notification_sent_on_pause(
        self, app, sched_worker, active_task, db_conn
    ):
        """
        TC-SCHED-09: 휴게시간 진입 시 BREAK_TIME_PAUSE 알림 발송 확인

        Expected:
        - app_alert_logs에 alert_type='BREAK_TIME_PAUSE' 레코드 생성
        - target_worker_id == sched_worker.id
        """
        from app.services.scheduler_service import force_pause_all_active_tasks

        alert_before = _get_alert_count(db_conn, sched_worker['id'], 'BREAK_TIME_PAUSE')

        force_pause_all_active_tasks(
            'break_morning',
            '오전 휴게시간이 시작되었습니다.'
        )

        alert_after = _get_alert_count(db_conn, sched_worker['id'], 'BREAK_TIME_PAUSE')
        assert alert_after > alert_before, (
            "BREAK_TIME_PAUSE alert should be created when task is force-paused"
        )

    def test_no_end_notification_without_pause(
        self, app, sched_worker, active_task, db_conn
    ):
        """
        TC-SCHED-10: 일시정지되지 않은 작업에는 종료 알림 없음

        Flow: force_pause 없이 send_break_end_notifications 호출
        Expected:
        - BREAK_TIME_END 알림 미생성 (work_pause_log에 레코드 없으므로)
        """
        from app.services.scheduler_service import send_break_end_notifications

        alert_before = _get_alert_count(db_conn, sched_worker['id'], 'BREAK_TIME_END')

        # pause 없이 종료 알림 시도
        send_break_end_notifications(
            'break_morning',
            '오전 휴게시간이 종료되었습니다.'
        )

        alert_after = _get_alert_count(db_conn, sched_worker['id'], 'BREAK_TIME_END')
        assert alert_after == alert_before, (
            "No BREAK_TIME_END alert should be sent when task was not paused"
        )


# ============================================================
# TestBreakTimeSchedulerJobs: 스케줄러 등록 확인
# ============================================================
class TestBreakTimeSchedulerJobs:
    """스케줄러에 휴게시간 job이 등록되어 있는지 확인 (TC-SCHED-11 ~ TC-SCHED-14)"""

    def test_scheduler_has_check_break_time_job(self, app):
        """
        TC-SCHED-11: 스케줄러에 'check_break_time' job 등록 확인

        Expected:
        - job id 'check_break_time' 존재
        """
        try:
            from app.services.scheduler_service import init_scheduler
        except ImportError:
            pytest.skip("scheduler_service not available")

        scheduler = init_scheduler()

        try:
            job_ids = {job.id for job in scheduler.get_jobs()}
            assert 'check_break_time' in job_ids, (
                f"'check_break_time' job not found. Registered jobs: {job_ids}"
            )
        finally:
            if scheduler.running:
                scheduler.shutdown()

    def test_scheduler_break_period_count(self, app):
        """
        TC-SCHED-12: BREAK_PERIODS에 4개 시간대 정의 확인

        Expected:
        - break_morning, lunch, break_afternoon, dinner 4개
        """
        try:
            from app.services.scheduler_service import BREAK_PERIODS
        except ImportError:
            pytest.skip("BREAK_PERIODS not exported")

        assert len(BREAK_PERIODS) == 4, (
            f"Expected 4 break periods, got {len(BREAK_PERIODS)}"
        )

        pause_types = {p['pause_type'] for p in BREAK_PERIODS}
        expected_types = {'break_morning', 'lunch', 'break_afternoon', 'dinner'}
        assert pause_types == expected_types, (
            f"Expected pause_types {expected_types}, got {pause_types}"
        )

    def test_force_pause_callable_without_tasks(self, app):
        """
        TC-SCHED-13: force_pause_all_active_tasks 빈 상태에서 예외 없이 실행

        Expected:
        - 진행 중인 작업이 없어도 예외 발생 없음
        """
        try:
            from app.services.scheduler_service import force_pause_all_active_tasks
        except ImportError:
            pytest.skip("force_pause_all_active_tasks not available")

        try:
            force_pause_all_active_tasks('break_morning', '테스트 메시지')
        except Exception as e:
            pytest.fail(f"force_pause_all_active_tasks raised exception: {e}")

    def test_check_break_time_job_callable(self, app):
        """
        TC-SCHED-14: check_break_time_job 직접 호출 가능 (예외 없이)

        Expected:
        - 예외 없이 실행 완료
        """
        try:
            from app.services.scheduler_service import check_break_time_job
        except ImportError:
            pytest.skip("check_break_time_job not available")

        try:
            check_break_time_job()
        except Exception as e:
            pytest.fail(f"check_break_time_job raised exception: {e}")
