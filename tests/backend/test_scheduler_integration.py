"""
Sprint 7 Phase 6: 스케줄러 통합 테스트

mock datetime을 사용하여 스케줄러 job 함수를 직접 호출:
  1시간 경과 → TASK_REMINDER 생성
  3시간 경과 → 3건 누적 (별도 tasks)
  17:00 / 20:00 KST → SHIFT_END_REMINDER (작업자 per 1건, 중복 제거)
  익일 09:00 KST → TASK_ESCALATION (같은 company is_manager에게만)

TC-SCHEDULER-01 ~ TC-SCHEDULER-08
"""

import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

backend_path = str(Path(__file__).parent.parent.parent / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# KST 타임존
KST = timezone(timedelta(hours=9))


# ──────────────────────────────────────────────────────────────
# 내부 헬퍼
# ──────────────────────────────────────────────────────────────

def _insert_product(db_conn, serial_number: str, qr_doc_id: str,
                    model: str = "GALLANT-III",
                    mech_partner: str = None, elec_partner: str = None,
                    module_outsourcing: str = None) -> None:
    """plan.product_info 및 public.qr_registry 삽입"""
    cur = db_conn.cursor()
    cur.execute("""
        INSERT INTO plan.product_info (serial_number, model, prod_date, mech_partner, elec_partner, module_outsourcing)
        VALUES (%s, %s, CURRENT_DATE, %s, %s, %s)
        ON CONFLICT (serial_number) DO NOTHING
    """, (serial_number, model, mech_partner, elec_partner, module_outsourcing))
    cur.execute("""
        INSERT INTO public.qr_registry (qr_doc_id, serial_number)
        VALUES (%s, %s)
        ON CONFLICT (qr_doc_id) DO NOTHING
    """, (qr_doc_id, serial_number))
    db_conn.commit()
    cur.close()


def _insert_active_task(db_conn, worker_id: int, serial_number: str, qr_doc_id: str,
                        task_category: str = "MECH",
                        task_id_ref: str = "CABINET_ASSY",
                        task_name: str = "캐비넷 조립",
                        started_at: datetime = None) -> int:
    """
    진행 중인 task(started_at IS NOT NULL, completed_at IS NULL) 삽입.
    work_start_log에도 기록하여 실제 BE 로직과 일치.
    """
    if started_at is None:
        started_at = datetime.now(KST) - timedelta(hours=1)

    cur = db_conn.cursor()
    cur.execute("""
        INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
             started_at, is_applicable)
        VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
        RETURNING id
    """, (worker_id, serial_number, qr_doc_id, task_category, task_id_ref, task_name, started_at))
    task_id = cur.fetchone()[0]

    # work_start_log에도 기록
    cur.execute("""
        INSERT INTO work_start_log
            (task_id, worker_id, serial_number, qr_doc_id, task_category, task_id_ref, task_name, started_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (task_id, worker_id, serial_number, qr_doc_id, task_category, task_id_ref, task_name, started_at))

    db_conn.commit()
    cur.close()
    return task_id


def _cleanup(db_conn, serial_number: str, qr_doc_id: str = None) -> None:
    cur = db_conn.cursor()
    try:
        cur.execute("DELETE FROM app_alert_logs WHERE serial_number = %s", (serial_number,))
        cur.execute("DELETE FROM work_completion_log WHERE serial_number = %s", (serial_number,))
        cur.execute("DELETE FROM work_start_log WHERE serial_number = %s", (serial_number,))
        cur.execute("DELETE FROM public.app_task_details WHERE serial_number = %s", (serial_number,))
        if qr_doc_id:
            cur.execute("DELETE FROM public.qr_registry WHERE qr_doc_id = %s", (qr_doc_id,))
        cur.execute("DELETE FROM plan.product_info WHERE serial_number = %s", (serial_number,))
        db_conn.commit()
    except Exception as e:
        db_conn.rollback()
        print(f"Cleanup warning: {e}")
    finally:
        cur.close()


def _cleanup_alerts_by_type(db_conn, alert_type: str) -> None:
    cur = db_conn.cursor()
    try:
        cur.execute("DELETE FROM app_alert_logs WHERE alert_type = %s", (alert_type,))
        db_conn.commit()
    except Exception:
        db_conn.rollback()
    finally:
        cur.close()


def _count_alerts(db_conn, alert_type: str, serial_number: str = None) -> int:
    cur = db_conn.cursor()
    if serial_number:
        cur.execute("""
            SELECT COUNT(*) FROM app_alert_logs
            WHERE alert_type = %s AND serial_number = %s
        """, (alert_type, serial_number))
    else:
        cur.execute("""
            SELECT COUNT(*) FROM app_alert_logs WHERE alert_type = %s
        """, (alert_type,))
    count = cur.fetchone()[0]
    cur.close()
    return count


def _count_target_alerts(db_conn, alert_type: str, target_worker_id: int) -> int:
    """특정 작업자를 대상으로 한 알림 수"""
    cur = db_conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM app_alert_logs
        WHERE alert_type = %s AND target_worker_id = %s
    """, (alert_type, target_worker_id))
    count = cur.fetchone()[0]
    cur.close()
    return count


# ──────────────────────────────────────────────────────────────
# TC-SCHEDULER-01~03: task_reminder_job — TASK_REMINDER
# ──────────────────────────────────────────────────────────────

class TestTaskReminderJob:
    """task_reminder_job 직접 호출 → TASK_REMINDER 알림 생성"""

    SN = "SCHEDULER-REMIND-001"
    QR = "DOC_SCHEDULER-REMIND-001"

    @pytest.fixture(autouse=True)
    def setup(self, db_conn):
        _insert_product(db_conn, self.SN, self.QR)
        yield
        _cleanup(db_conn, self.SN, self.QR)

    def test_tc_scheduler_01_task_reminder_creates_alert_for_active_task(
        self, db_conn, create_test_worker
    ):
        """TC-SCHEDULER-01: 진행 중인 task 1개 → task_reminder_job 호출 시 TASK_REMINDER 1건"""
        worker_id = create_test_worker(
            email="sched_remind1@test.axisos.com", password="Pass1!",
            name="Sched Remind Worker 1", role="MECH"
        )

        # 1시간 전 시작한 task
        started_at = datetime.now(KST) - timedelta(hours=1)
        _insert_active_task(db_conn, worker_id, self.SN, self.QR, started_at=started_at)

        # 이전 TASK_REMINDER 알림 개수 확인
        before_count = _count_alerts(db_conn, "TASK_REMINDER", self.SN)

        from app.services.scheduler_service import task_reminder_job
        task_reminder_job()

        after_count = _count_alerts(db_conn, "TASK_REMINDER", self.SN)
        assert after_count > before_count, \
            f"Expected TASK_REMINDER to be created (before={before_count}, after={after_count})"

    def test_tc_scheduler_02_task_reminder_targets_worker(
        self, db_conn, create_test_worker
    ):
        """TC-SCHEDULER-02: TASK_REMINDER 알림이 작업자 본인(target_worker_id)을 대상으로 생성"""
        worker_id = create_test_worker(
            email="sched_remind2@test.axisos.com", password="Pass1!",
            name="Sched Remind Worker 2", role="MECH"
        )
        started_at = datetime.now(KST) - timedelta(hours=2)
        _insert_active_task(db_conn, worker_id, self.SN, self.QR, started_at=started_at)

        from app.services.scheduler_service import task_reminder_job
        task_reminder_job()

        # target_worker_id가 작업자 본인이어야 함
        count = _count_target_alerts(db_conn, "TASK_REMINDER", worker_id)
        assert count >= 1, \
            f"TASK_REMINDER should target worker_id={worker_id}, but got {count} alerts"

    def test_tc_scheduler_03_multiple_active_tasks_get_multiple_reminders(
        self, db_conn, create_test_worker
    ):
        """TC-SCHEDULER-03: 진행 중인 task 3개 → 3건의 TASK_REMINDER 생성"""
        # 세 명의 작업자, 각각 별도 시리얼번호
        sns = [f"SCHEDULER-REMIND-00{i}" for i in range(2, 5)]
        qrs = [f"DOC_SCHEDULER-REMIND-00{i}" for i in range(2, 5)]

        worker_ids = []
        for i, (sn, qr) in enumerate(zip(sns, qrs)):
            _insert_product(db_conn, sn, qr)
            w_id = create_test_worker(
                email=f"sched_remind3_{i}@test.axisos.com", password="Pass1!",
                name=f"Sched Remind Worker 3-{i}", role="MECH"
            )
            worker_ids.append(w_id)
            started_at = datetime.now(KST) - timedelta(hours=3)
            _insert_active_task(db_conn, w_id, sn, qr, started_at=started_at)

        from app.services.scheduler_service import task_reminder_job

        # 각 작업자의 alert 이전 개수 기록
        before_counts = {
            w_id: _count_target_alerts(db_conn, "TASK_REMINDER", w_id)
            for w_id in worker_ids
        }

        task_reminder_job()

        # 각 작업자에게 최소 1건 이상의 TASK_REMINDER가 생성되었는지 확인
        for w_id in worker_ids:
            after = _count_target_alerts(db_conn, "TASK_REMINDER", w_id)
            assert after > before_counts[w_id], \
                f"Worker {w_id} should receive TASK_REMINDER"

        # 정리
        for sn, qr in zip(sns, qrs):
            _cleanup(db_conn, sn, qr)


# ──────────────────────────────────────────────────────────────
# TC-SCHEDULER-04~05: shift_end_reminder_job — SHIFT_END_REMINDER
# ──────────────────────────────────────────────────────────────

class TestShiftEndReminderJob:
    """shift_end_reminder_job 직접 호출 → SHIFT_END_REMINDER 알림 생성"""

    SN = "SCHEDULER-SHIFT-001"
    QR = "DOC_SCHEDULER-SHIFT-001"

    @pytest.fixture(autouse=True)
    def setup(self, db_conn):
        _insert_product(db_conn, self.SN, self.QR)
        yield
        _cleanup(db_conn, self.SN, self.QR)

    def test_tc_scheduler_04_shift_end_reminder_creates_alert(
        self, db_conn, create_test_worker
    ):
        """TC-SCHEDULER-04: 진행 중인 task → shift_end_reminder_job 호출 시 SHIFT_END_REMINDER 생성"""
        worker_id = create_test_worker(
            email="sched_shift4@test.axisos.com", password="Pass1!",
            name="Sched Shift Worker 4", role="MECH"
        )
        started_at = datetime.now(KST) - timedelta(hours=4)
        _insert_active_task(db_conn, worker_id, self.SN, self.QR, started_at=started_at)

        before_count = _count_alerts(db_conn, "SHIFT_END_REMINDER", self.SN)

        from app.services.scheduler_service import shift_end_reminder_job
        shift_end_reminder_job()

        after_count = _count_alerts(db_conn, "SHIFT_END_REMINDER", self.SN)
        assert after_count > before_count, \
            f"Expected SHIFT_END_REMINDER (before={before_count}, after={after_count})"

    def test_tc_scheduler_05_shift_end_reminder_no_duplicate_per_worker(
        self, db_conn, create_test_worker
    ):
        """TC-SCHEDULER-05: 같은 작업자의 task가 여러 개여도 SHIFT_END_REMINDER는 1건만"""
        worker_id = create_test_worker(
            email="sched_shift5@test.axisos.com", password="Pass1!",
            name="Sched Shift Worker 5", role="MECH"
        )
        # 같은 작업자가 두 개의 task를 진행 중
        for i, task_id_ref in enumerate(["CABINET_ASSY", "N2_LINE"]):
            _insert_active_task(
                db_conn, worker_id, self.SN, self.QR,
                task_id_ref=task_id_ref,
                task_name=f"Task {i}",
                started_at=datetime.now(KST) - timedelta(hours=2)
            )

        before_count = _count_target_alerts(db_conn, "SHIFT_END_REMINDER", worker_id)

        from app.services.scheduler_service import shift_end_reminder_job
        shift_end_reminder_job()

        after_count = _count_target_alerts(db_conn, "SHIFT_END_REMINDER", worker_id)
        # 작업자 per 1건 (중복 제거 로직)
        new_alerts = after_count - before_count
        assert new_alerts == 1, \
            f"Expected 1 SHIFT_END_REMINDER per worker (got {new_alerts} new alerts)"


# ──────────────────────────────────────────────────────────────
# TC-SCHEDULER-06~08: task_escalation_job — TASK_ESCALATION
# ──────────────────────────────────────────────────────────────

class TestTaskEscalationJob:
    """task_escalation_job 직접 호출 → 전일 미종료 task에 대해 TASK_ESCALATION 생성"""

    SN = "SCHEDULER-ESCAL-001"
    QR = "DOC_SCHEDULER-ESCAL-001"

    @pytest.fixture(autouse=True)
    def setup(self, db_conn):
        _insert_product(db_conn, self.SN, self.QR)
        yield
        _cleanup(db_conn, self.SN, self.QR)

    def test_tc_scheduler_06_escalation_created_for_previous_day_task(
        self, db_conn, create_test_worker
    ):
        """TC-SCHEDULER-06: 전일 시작 미완료 task → TASK_ESCALATION 생성"""
        # 작업자 (같은 company)
        worker_id = create_test_worker(
            email="sched_escal6_worker@test.axisos.com", password="Pass1!",
            name="Escal Worker 6", role="MECH", company="FNI"
        )
        # 같은 company 관리자
        manager_id = create_test_worker(
            email="sched_escal6_mgr@test.axisos.com", password="Pass1!",
            name="Escal Manager 6", role="MECH", company="FNI", is_manager=True
        )

        # 어제 시작한 task (전일 미종료)
        yesterday = datetime.now(KST) - timedelta(days=1)
        yesterday_kst = yesterday.replace(hour=10, minute=0, second=0, microsecond=0)
        _insert_active_task(db_conn, worker_id, self.SN, self.QR, started_at=yesterday_kst)

        before_count = _count_target_alerts(db_conn, "TASK_ESCALATION", manager_id)

        from app.services.scheduler_service import task_escalation_job
        task_escalation_job()

        after_count = _count_target_alerts(db_conn, "TASK_ESCALATION", manager_id)
        assert after_count > before_count, \
            f"Expected TASK_ESCALATION to manager (before={before_count}, after={after_count})"

    def test_tc_scheduler_07_escalation_only_targets_same_company_manager(
        self, db_conn, create_test_worker
    ):
        """TC-SCHEDULER-07: TASK_ESCALATION은 같은 company is_manager=True 에게만"""
        # FNI 작업자
        fni_worker_id = create_test_worker(
            email="sched_escal7_fni_w@test.axisos.com", password="Pass1!",
            name="FNI Worker 7", role="MECH", company="FNI"
        )
        # FNI 관리자
        fni_mgr_id = create_test_worker(
            email="sched_escal7_fni_mgr@test.axisos.com", password="Pass1!",
            name="FNI Manager 7", role="MECH", company="FNI", is_manager=True
        )
        # 다른 company 관리자 (BAT) - 에스컬레이션 받으면 안 됨
        bat_mgr_id = create_test_worker(
            email="sched_escal7_bat_mgr@test.axisos.com", password="Pass1!",
            name="BAT Manager 7", role="MECH", company="BAT", is_manager=True
        )

        yesterday = datetime.now(KST) - timedelta(days=1)
        yesterday_kst = yesterday.replace(hour=10, minute=0, second=0, microsecond=0)
        _insert_active_task(db_conn, fni_worker_id, self.SN, self.QR, started_at=yesterday_kst)

        before_fni = _count_target_alerts(db_conn, "TASK_ESCALATION", fni_mgr_id)
        before_bat = _count_target_alerts(db_conn, "TASK_ESCALATION", bat_mgr_id)

        from app.services.scheduler_service import task_escalation_job
        task_escalation_job()

        after_fni = _count_target_alerts(db_conn, "TASK_ESCALATION", fni_mgr_id)
        after_bat = _count_target_alerts(db_conn, "TASK_ESCALATION", bat_mgr_id)

        assert after_fni > before_fni, "FNI manager should receive TASK_ESCALATION"
        assert after_bat == before_bat, "BAT manager should NOT receive TASK_ESCALATION for FNI worker"

    def test_tc_scheduler_08_today_task_not_escalated(
        self, db_conn, create_test_worker
    ):
        """TC-SCHEDULER-08: 오늘 시작된 미완료 task는 에스컬레이션 대상 아님"""
        worker_id = create_test_worker(
            email="sched_escal8_w@test.axisos.com", password="Pass1!",
            name="Escal Worker 8", role="MECH", company="FNI"
        )
        mgr_id = create_test_worker(
            email="sched_escal8_mgr@test.axisos.com", password="Pass1!",
            name="Escal Manager 8", role="MECH", company="FNI", is_manager=True
        )

        # 오늘 시작한 task (에스컬레이션 대상 아님)
        today_kst = datetime.now(KST).replace(hour=8, minute=0, second=0, microsecond=0)
        _insert_active_task(db_conn, worker_id, self.SN, self.QR, started_at=today_kst)

        before_count = _count_target_alerts(db_conn, "TASK_ESCALATION", mgr_id)

        from app.services.scheduler_service import task_escalation_job
        task_escalation_job()

        after_count = _count_target_alerts(db_conn, "TASK_ESCALATION", mgr_id)
        assert after_count == before_count, \
            f"Today's task should NOT be escalated (before={before_count}, after={after_count})"


# ──────────────────────────────────────────────────────────────
# TC-SCHEDULER-09: mock datetime으로 스케줄러 job 함수 시뮬레이션
# ──────────────────────────────────────────────────────────────

class TestSchedulerWithMockDatetime:
    """
    datetime.now()를 mock하여 특정 시각에 스케줄러 job이 실행되는 상황 시뮬레이션.
    BE 소스 코드 변경 없이 테스트 내에서 시각을 제어.
    """

    SN = "SCHEDULER-MOCK-001"
    QR = "DOC_SCHEDULER-MOCK-001"

    @pytest.fixture(autouse=True)
    def setup(self, db_conn):
        _insert_product(db_conn, self.SN, self.QR)
        yield
        _cleanup(db_conn, self.SN, self.QR)

    def test_tc_scheduler_09_escalation_job_uses_today_midnight_cutoff(
        self, db_conn, create_test_worker
    ):
        """TC-SCHEDULER-09: task_escalation_job의 before=오늘 00:00 KST 기준 검증"""
        worker_id = create_test_worker(
            email="sched_mock9_w@test.axisos.com", password="Pass1!",
            name="Mock Worker 9", role="MECH", company="FNI"
        )
        mgr_id = create_test_worker(
            email="sched_mock9_mgr@test.axisos.com", password="Pass1!",
            name="Mock Manager 9", role="MECH", company="FNI", is_manager=True
        )

        # 어제 23:59 시작 (오늘 00:00 KST 이전 → 에스컬레이션 대상)
        now_kst = datetime.now(KST)
        today_midnight = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
        # 어제 23:59 = today_midnight - 1분
        before_midnight = today_midnight - timedelta(minutes=1)

        _insert_active_task(db_conn, worker_id, self.SN, self.QR,
                            started_at=before_midnight)

        before_count = _count_target_alerts(db_conn, "TASK_ESCALATION", mgr_id)

        from app.services.scheduler_service import task_escalation_job
        task_escalation_job()

        after_count = _count_target_alerts(db_conn, "TASK_ESCALATION", mgr_id)
        assert after_count > before_count, \
            "Task started before today midnight should be escalated"
