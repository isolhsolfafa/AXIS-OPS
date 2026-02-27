"""
test_scheduler_integration.py
Sprint 7: 스케줄러 통합 테스트

검증 대상 (scheduler_service.py):
  TC-01: 진행 중인 Task 존재 → task_reminder_job() → TASK_REMINDER 알림 생성
  TC-02: 여러 진행 중인 Task → 각각 TASK_REMINDER 알림 생성 (3건)
  TC-03: 진행 중인 Task 없음 → task_reminder_job() → 알림 0건
  TC-04: shift_end_reminder_job() → SHIFT_END_REMINDER 알림 생성 (작업자 중복 제거)
  TC-05: 같은 작업자가 여러 Task 진행 중 → SHIFT_END_REMINDER 1건만
  TC-06: task_escalation_job() → 전일 미종료 Task의 동일 company 관리자에게 TASK_ESCALATION
  TC-07: task_escalation_job() → 다른 company 관리자에게는 미전송
  TC-08: 오늘 시작한 Task → task_escalation_job() 대상 아님 (전일 미종료만)

테스트 실행 방법:
  pytest tests/integration/test_scheduler_integration.py -v

주의:
  - DB 연결 필요 (staging DB)
  - 각 테스트에서 생성한 Task/Alert는 cleanup 필수
  - 실제 스케줄러 실행 없이 job 함수를 직접 호출하여 검증
  - datetime mock을 사용하여 "어제/오늘" 경계 시각 제어
"""

import sys
import os
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from typing import Optional, List, Dict
from psycopg2.extras import RealDictCursor

# 프로젝트 경로 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from app.services.scheduler_service import (
    task_reminder_job,
    shift_end_reminder_job,
    task_escalation_job,
)


# ──────────────────────────────────────────────
# KST 시간대
# ──────────────────────────────────────────────
KST = timezone(timedelta(hours=9))


# ──────────────────────────────────────────────
# 헬퍼 함수
# ──────────────────────────────────────────────

def _get_alert_count(db_conn, alert_type: str, serial_number: str) -> int:
    """특정 타입 + 제품의 알림 수 조회"""
    cursor = db_conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) FROM app_alert_logs
        WHERE alert_type = %s AND serial_number = %s
        """,
        (alert_type, serial_number)
    )
    count = cursor.fetchone()[0]
    cursor.close()
    return count


def _get_alerts_for_worker(
    db_conn,
    target_worker_id: int,
    alert_type: str,
    serial_number: Optional[str] = None
) -> List[Dict]:
    """특정 작업자 대상 알림 목록 조회"""
    cursor = db_conn.cursor(cursor_factory=RealDictCursor)
    if serial_number:
        cursor.execute(
            """
            SELECT * FROM app_alert_logs
            WHERE target_worker_id = %s AND alert_type = %s AND serial_number = %s
            ORDER BY created_at DESC
            """,
            (target_worker_id, alert_type, serial_number)
        )
    else:
        cursor.execute(
            """
            SELECT * FROM app_alert_logs
            WHERE target_worker_id = %s AND alert_type = %s
            ORDER BY created_at DESC
            """,
            (target_worker_id, alert_type)
        )
    rows = cursor.fetchall()
    cursor.close()
    return [dict(r) for r in rows]


def _insert_task(
    db_conn,
    serial_number: str,
    qr_doc_id: str,
    worker_id: int,
    task_category: str,
    task_id: str,
    task_name: str,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    is_applicable: bool = True
) -> int:
    """테스트용 Task 삽입 → 생성된 id 반환"""
    cursor = db_conn.cursor()
    cursor.execute(
        """
        INSERT INTO app_task_details (
            serial_number, qr_doc_id, worker_id,
            task_category, task_id, task_name,
            started_at, completed_at, is_applicable
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (serial_number, qr_doc_id, worker_id,
         task_category, task_id, task_name,
         started_at, completed_at, is_applicable)
    )
    task_db_id = cursor.fetchone()[0]
    db_conn.commit()
    cursor.close()
    return task_db_id


def _insert_worker(
    db_conn,
    email: str,
    name: str,
    role: str,
    company: str,
    is_manager: bool = False,
    approval_status: str = 'approved'
) -> int:
    """테스트용 작업자 삽입 → id 반환"""
    from werkzeug.security import generate_password_hash
    pw_hash = generate_password_hash('test1234')

    cursor = db_conn.cursor()
    # role_enum 확인
    cursor.execute("SELECT unnest(enum_range(NULL::role_enum))")
    existing_roles = {r[0] for r in cursor.fetchall()}
    role_fallback = {'MECH': 'MM', 'ELEC': 'EE', 'ADMIN': 'PI'}
    db_role = role if role in existing_roles else role_fallback.get(role, role)

    cursor.execute(
        """
        INSERT INTO workers (
            email, name, password_hash, role, company,
            approval_status, email_verified, is_admin, is_manager
        )
        VALUES (%s, %s, %s, %s::role_enum, %s,
                %s::approval_status_enum, TRUE, FALSE, %s)
        ON CONFLICT (email) DO UPDATE
            SET name = EXCLUDED.name,
                is_manager = EXCLUDED.is_manager
        RETURNING id
        """,
        (email, name, pw_hash, db_role, company,
         approval_status, is_manager)
    )
    worker_id = cursor.fetchone()[0]
    db_conn.commit()
    cursor.close()
    return worker_id


def _cleanup_alerts(db_conn, alert_ids: List[int]) -> None:
    """테스트 알림 삭제"""
    if not alert_ids:
        return
    cursor = db_conn.cursor()
    cursor.execute(
        "DELETE FROM app_alert_logs WHERE id = ANY(%s)",
        (alert_ids,)
    )
    db_conn.commit()
    cursor.close()


def _cleanup_tasks(db_conn, task_ids: List[int]) -> None:
    """테스트 Task 삭제"""
    if not task_ids:
        return
    cursor = db_conn.cursor()
    cursor.execute(
        "DELETE FROM app_task_details WHERE id = ANY(%s)",
        (task_ids,)
    )
    db_conn.commit()
    cursor.close()


def _cleanup_workers(db_conn, emails: List[str]) -> None:
    """테스트 작업자 삭제"""
    if not emails:
        return
    cursor = db_conn.cursor()
    for email in emails:
        cursor.execute("DELETE FROM workers WHERE email = %s", (email,))
    db_conn.commit()
    cursor.close()


def _to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """datetime을 UTC aware로 변환 (naive이면 UTC 가정)"""
    if dt is None:
        return dt
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _get_created_alert_ids(
    db_conn,
    alert_type: str,
    serial_number: str,
    after: datetime
) -> List[int]:
    """특정 시각 이후 생성된 알림 ID 목록 조회 (cleanup용)"""
    cursor = db_conn.cursor()
    cursor.execute(
        """
        SELECT id FROM app_alert_logs
        WHERE alert_type = %s AND serial_number = %s AND created_at >= %s
        """,
        (alert_type, serial_number, after)
    )
    ids = [r[0] for r in cursor.fetchall()]
    cursor.close()
    return ids


# ──────────────────────────────────────────────
# TC-01~TC-03: task_reminder_job 테스트
# ──────────────────────────────────────────────

class TestTaskReminderJob:
    """
    TC-01~TC-03: task_reminder_job() — 매 1시간 TASK_REMINDER 알림
    """

    def test_active_task_creates_reminder_alert(self, db_conn, seed_test_products, seed_test_workers):
        """TC-01: 진행 중인 Task 1개 → TASK_REMINDER 알림 1건 생성"""
        if db_conn is None:
            pytest.skip("DB 연결 없음 — staging DB 필요")

        product = next(p for p in seed_test_products if 'GAIA' in p['model'])
        worker = next(w for w in seed_test_workers
                      if w.get('company') == 'FNI' and w.get('id') is not None)

        serial_number = product['serial_number']
        qr_doc_id = product['qr_doc_id']
        worker_id = worker['id']

        started_at = datetime.now(timezone.utc) - timedelta(hours=2)
        task_id = None
        alert_ids = []
        test_start = datetime.now(timezone.utc)

        try:
            task_id = _insert_task(
                db_conn, serial_number, qr_doc_id, worker_id,
                'MECH', 'SCHED_TEST_REMINDER_TC01', 'TC01 리마인더 테스트',
                started_at=started_at, completed_at=None
            )

            # job 직접 실행
            task_reminder_job()

            # 알림 생성 확인
            alert_ids = _get_created_alert_ids(
                db_conn, 'TASK_REMINDER', serial_number, test_start
            )
            assert len(alert_ids) >= 1, (
                f"TC-01: TASK_REMINDER 알림이 생성되지 않음 (got {len(alert_ids)}건)"
            )

        finally:
            _cleanup_alerts(db_conn, alert_ids)
            if task_id:
                _cleanup_tasks(db_conn, [task_id])

    def test_multiple_active_tasks_create_multiple_reminders(
        self, db_conn, seed_test_products, seed_test_workers
    ):
        """TC-02: 진행 중인 Task 3개 → TASK_REMINDER 알림 3건 이상 생성"""
        if db_conn is None:
            pytest.skip("DB 연결 없음 — staging DB 필요")

        product = next(p for p in seed_test_products if 'GAIA' in p['model'])
        worker = next(w for w in seed_test_workers
                      if w.get('company') == 'FNI' and w.get('id') is not None)

        serial_number = product['serial_number']
        qr_doc_id = product['qr_doc_id']
        worker_id = worker['id']

        started_at = datetime.now(timezone.utc) - timedelta(hours=1, minutes=30)
        task_ids = []
        alert_ids = []
        test_start = datetime.now(timezone.utc)

        try:
            for i in range(3):
                tid = _insert_task(
                    db_conn, serial_number, qr_doc_id, worker_id,
                    'MECH', f'SCHED_TC02_TASK_{i}', f'TC02 리마인더 테스트 {i}',
                    started_at=started_at, completed_at=None
                )
                task_ids.append(tid)

            task_reminder_job()

            alert_ids = _get_created_alert_ids(
                db_conn, 'TASK_REMINDER', serial_number, test_start
            )
            assert len(alert_ids) >= 3, (
                f"TC-02: TASK_REMINDER 알림 수 부족: expected>=3, actual={len(alert_ids)}"
            )

        finally:
            _cleanup_alerts(db_conn, alert_ids)
            _cleanup_tasks(db_conn, task_ids)

    def test_no_active_tasks_no_reminder(self, db_conn, seed_test_products, seed_test_workers):
        """TC-03: 진행 중인 Task 없음 → TASK_REMINDER 알림 0건"""
        if db_conn is None:
            pytest.skip("DB 연결 없음 — staging DB 필요")

        product = next(p for p in seed_test_products if 'SWS' in p['model'])
        serial_number = product['serial_number']

        test_start = datetime.now(timezone.utc)

        # 진행 중인 Task를 삽입하지 않고 job 실행
        task_reminder_job()

        alert_ids = _get_created_alert_ids(
            db_conn, 'TASK_REMINDER', serial_number, test_start
        )
        # SWS 제품의 진행 중인 Task가 없으면 알림 없음
        assert len(alert_ids) == 0, (
            f"TC-03: Task 없는 제품에 TASK_REMINDER 알림 생성됨: {len(alert_ids)}건"
        )


# ──────────────────────────────────────────────
# TC-04~TC-05: shift_end_reminder_job 테스트
# ──────────────────────────────────────────────

class TestShiftEndReminderJob:
    """
    TC-04~TC-05: shift_end_reminder_job() — 17:00/20:00 SHIFT_END_REMINDER
    """

    def test_shift_end_reminder_created_for_active_task(
        self, db_conn, seed_test_products, seed_test_workers
    ):
        """TC-04: 진행 중인 Task 보유 작업자 → SHIFT_END_REMINDER 알림 1건"""
        if db_conn is None:
            pytest.skip("DB 연결 없음 — staging DB 필요")

        product = next(p for p in seed_test_products if 'DRAGON' in p['model'])
        worker = next(w for w in seed_test_workers
                      if w.get('company') == 'TMS(M)' and w.get('id') is not None)

        serial_number = product['serial_number']
        qr_doc_id = product['qr_doc_id']
        worker_id = worker['id']

        started_at = datetime.now(timezone.utc) - timedelta(hours=3)
        task_id = None
        alert_ids = []
        test_start = datetime.now(timezone.utc)

        try:
            task_id = _insert_task(
                db_conn, serial_number, qr_doc_id, worker_id,
                'MECH', 'SCHED_TC04_SHIFT', 'TC04 퇴근 알림 테스트',
                started_at=started_at, completed_at=None
            )

            shift_end_reminder_job()

            alert_ids = _get_created_alert_ids(
                db_conn, 'SHIFT_END_REMINDER', serial_number, test_start
            )
            assert len(alert_ids) >= 1, (
                f"TC-04: SHIFT_END_REMINDER 알림 생성 안됨 (got {len(alert_ids)}건)"
            )

        finally:
            _cleanup_alerts(db_conn, alert_ids)
            if task_id:
                _cleanup_tasks(db_conn, [task_id])

    def test_shift_end_reminder_dedup_per_worker(
        self, db_conn, seed_test_products, seed_test_workers
    ):
        """TC-05: 같은 작업자 여러 Task 진행 중 → SHIFT_END_REMINDER 1건만 (중복 제거)"""
        if db_conn is None:
            pytest.skip("DB 연결 없음 — staging DB 필요")

        product = next(p for p in seed_test_products if 'GALLANT' in p['model'])
        worker = next(w for w in seed_test_workers
                      if w.get('company') == 'BAT' and w.get('id') is not None)

        serial_number = product['serial_number']
        qr_doc_id = product['qr_doc_id']
        worker_id = worker['id']

        started_at = datetime.now(timezone.utc) - timedelta(hours=2)
        task_ids = []
        alert_ids = []
        test_start = datetime.now(timezone.utc)

        try:
            # 같은 작업자가 2개의 Task를 동시 진행
            for i in range(2):
                tid = _insert_task(
                    db_conn, serial_number, qr_doc_id, worker_id,
                    'MECH', f'SCHED_TC05_DEDUP_{i}', f'TC05 중복제거 테스트 {i}',
                    started_at=started_at, completed_at=None
                )
                task_ids.append(tid)

            shift_end_reminder_job()

            # target_worker_id로 필터링 — 같은 작업자에 1건만
            worker_alerts = _get_alerts_for_worker(
                db_conn, worker_id, 'SHIFT_END_REMINDER', serial_number
            )
            # test_start 이후 생성된 것만 카운트 (timezone-aware 안전 비교)
            def _to_utc(dt):
                if dt is None:
                    return dt
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)

            new_alerts = [
                a for a in worker_alerts
                if _to_utc(a['created_at']) >= test_start
            ]
            assert len(new_alerts) == 1, (
                f"TC-05: 같은 작업자에 SHIFT_END_REMINDER 중복 발송: expected=1, actual={len(new_alerts)}"
            )

            alert_ids = [a['id'] for a in new_alerts]

        finally:
            _cleanup_alerts(db_conn, alert_ids)
            _cleanup_tasks(db_conn, task_ids)


# ──────────────────────────────────────────────
# TC-06~TC-08: task_escalation_job 테스트
# ──────────────────────────────────────────────

class TestTaskEscalationJob:
    """
    TC-06~TC-08: task_escalation_job() — 09:00 KST 에스컬레이션
    전일 미종료 Task → 같은 company is_manager=True 작업자에게만 알림
    """

    def test_escalation_sent_to_same_company_manager(
        self, db_conn, seed_test_products, seed_test_workers
    ):
        """TC-06: 전일 미종료 Task → 같은 company 관리자에게 TASK_ESCALATION"""
        if db_conn is None:
            pytest.skip("DB 연결 없음 — staging DB 필요")

        product = next(p for p in seed_test_products if 'MITHAS' in p['model'])
        serial_number = product['serial_number']
        qr_doc_id = product['qr_doc_id']

        test_start = datetime.now(timezone.utc)

        # 테스트 작업자 (FNI 일반 작업자)
        worker_email = 'sched_tc06_worker@test.com'
        manager_email = 'sched_tc06_manager@test.com'
        other_manager_email = 'sched_tc06_other_mgr@test.com'

        task_ids = []
        alert_ids = []
        worker_emails_to_cleanup = [worker_email, manager_email, other_manager_email]

        try:
            # FNI 일반 작업자
            worker_id = _insert_worker(
                db_conn, worker_email, 'TC06 FNI 작업자', 'MECH', 'FNI',
                is_manager=False
            )
            # FNI 관리자
            manager_id = _insert_worker(
                db_conn, manager_email, 'TC06 FNI 관리자', 'MECH', 'FNI',
                is_manager=True
            )
            # 다른 회사 관리자 (BAT)
            other_mgr_id = _insert_worker(
                db_conn, other_manager_email, 'TC06 BAT 관리자', 'MECH', 'BAT',
                is_manager=True
            )

            # 전일(어제) 시작된 Task (오늘 자정 이전)
            yesterday_started = datetime.now(KST).replace(
                hour=9, minute=0, second=0, microsecond=0, tzinfo=KST
            ) - timedelta(days=1)

            task_id = _insert_task(
                db_conn, serial_number, qr_doc_id, worker_id,
                'MECH', 'SCHED_TC06_ESCALATION', 'TC06 에스컬레이션 테스트',
                started_at=yesterday_started.astimezone(timezone.utc),
                completed_at=None
            )
            task_ids.append(task_id)

            # 오늘 자정 KST 기준으로 에스컬레이션 실행
            today_midnight_kst = datetime.now(KST).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            with patch(
                'app.services.scheduler_service.datetime'
            ) as mock_dt:
                mock_dt.now.return_value = today_midnight_kst.replace(hour=9)
                mock_dt.now.side_effect = lambda tz=None: (
                    today_midnight_kst.replace(hour=9) if tz else datetime.now()
                )
                task_escalation_job()

            # FNI 관리자에게 TASK_ESCALATION 알림 확인
            mgr_alerts = _get_alerts_for_worker(
                db_conn, manager_id, 'TASK_ESCALATION', serial_number
            )
            new_mgr_alerts = [
                a for a in mgr_alerts
                if _to_utc(a['created_at']) >= test_start
            ]
            assert len(new_mgr_alerts) >= 1, (
                f"TC-06: FNI 관리자에게 TASK_ESCALATION 미전송 (got {len(new_mgr_alerts)}건)"
            )
            alert_ids.extend([a['id'] for a in new_mgr_alerts])

        finally:
            _cleanup_alerts(db_conn, alert_ids)
            _cleanup_tasks(db_conn, task_ids)
            _cleanup_workers(db_conn, worker_emails_to_cleanup)

    def test_escalation_not_sent_to_different_company_manager(
        self, db_conn, seed_test_products, seed_test_workers
    ):
        """TC-07: 전일 미종료 Task → 다른 company 관리자에게는 TASK_ESCALATION 미전송"""
        if db_conn is None:
            pytest.skip("DB 연결 없음 — staging DB 필요")

        product = next(p for p in seed_test_products if 'SDS' in p['model'])
        serial_number = product['serial_number']
        qr_doc_id = product['qr_doc_id']

        test_start = datetime.now(timezone.utc)

        worker_email = 'sched_tc07_worker@test.com'
        bat_manager_email = 'sched_tc07_bat_mgr@test.com'

        task_ids = []
        alert_ids = []

        try:
            # BAT 일반 작업자
            worker_id = _insert_worker(
                db_conn, worker_email, 'TC07 BAT 작업자', 'MECH', 'BAT',
                is_manager=False
            )
            # 다른 회사(FNI) 관리자
            bat_mgr_id = _insert_worker(
                db_conn, bat_manager_email, 'TC07 FNI 관리자', 'MECH', 'FNI',
                is_manager=True
            )

            # 전일 시작된 Task
            yesterday_started = datetime.now(KST).replace(
                hour=10, minute=0, second=0, microsecond=0, tzinfo=KST
            ) - timedelta(days=1)

            task_id = _insert_task(
                db_conn, serial_number, qr_doc_id, worker_id,
                'MECH', 'SCHED_TC07_NO_ESCALATION', 'TC07 다른 회사 에스컬레이션 테스트',
                started_at=yesterday_started.astimezone(timezone.utc),
                completed_at=None
            )
            task_ids.append(task_id)

            task_escalation_job()

            # FNI 관리자(다른 회사)에게는 알림 없음
            other_mgr_alerts = _get_alerts_for_worker(
                db_conn, bat_mgr_id, 'TASK_ESCALATION', serial_number
            )
            new_alerts = [
                a for a in other_mgr_alerts
                if _to_utc(a['created_at']) >= test_start
            ]
            assert len(new_alerts) == 0, (
                f"TC-07: 다른 company 관리자에게 TASK_ESCALATION 발송됨 (got {len(new_alerts)}건)"
            )

            # 혹시 생성된 alert 정리
            alert_ids.extend([a['id'] for a in new_alerts])

        finally:
            _cleanup_alerts(db_conn, alert_ids)
            _cleanup_tasks(db_conn, task_ids)
            _cleanup_workers(db_conn, [worker_email, bat_manager_email])

    def test_today_task_not_escalated(self, db_conn, seed_test_products, seed_test_workers):
        """TC-08: 오늘 시작한 Task → task_escalation_job() 대상 아님 (전일 미종료만)"""
        if db_conn is None:
            pytest.skip("DB 연결 없음 — staging DB 필요")

        product = next(p for p in seed_test_products if 'SWS' in p['model'])
        serial_number = product['serial_number']
        qr_doc_id = product['qr_doc_id']

        test_start = datetime.now(timezone.utc)

        worker_email = 'sched_tc08_worker@test.com'
        manager_email = 'sched_tc08_manager@test.com'

        task_ids = []
        alert_ids = []

        try:
            worker_id = _insert_worker(
                db_conn, worker_email, 'TC08 FNI 작업자', 'MECH', 'FNI',
                is_manager=False
            )
            manager_id = _insert_worker(
                db_conn, manager_email, 'TC08 FNI 관리자', 'MECH', 'FNI',
                is_manager=True
            )

            # 오늘 시작한 Task (자정 이후)
            today_started = datetime.now(KST).replace(
                hour=8, minute=0, second=0, microsecond=0, tzinfo=KST
            )

            task_id = _insert_task(
                db_conn, serial_number, qr_doc_id, worker_id,
                'MECH', 'SCHED_TC08_TODAY', 'TC08 오늘 시작 Task',
                started_at=today_started.astimezone(timezone.utc),
                completed_at=None
            )
            task_ids.append(task_id)

            task_escalation_job()

            # 오늘 시작한 Task는 에스컬레이션 대상 아님
            mgr_alerts = _get_alerts_for_worker(
                db_conn, manager_id, 'TASK_ESCALATION', serial_number
            )
            new_mgr_alerts = [
                a for a in mgr_alerts
                if _to_utc(a['created_at']) >= test_start
            ]
            assert len(new_mgr_alerts) == 0, (
                f"TC-08: 오늘 시작한 Task가 에스컬레이션 대상이 됨 (got {len(new_mgr_alerts)}건)"
            )

            alert_ids.extend([a['id'] for a in new_mgr_alerts])

        finally:
            _cleanup_alerts(db_conn, alert_ids)
            _cleanup_tasks(db_conn, task_ids)
            _cleanup_workers(db_conn, [worker_email, manager_email])


# ──────────────────────────────────────────────
# TC-09 (보너스): 스케줄러 함수 직접 실행 가능 여부
# ──────────────────────────────────────────────

class TestSchedulerFunctionCallable:
    """
    TC-09: 스케줄러 job 함수들이 예외 없이 직접 호출 가능한지 스모크 테스트
    (DB 연결 실패 시에도 예외가 전파되지 않아야 함)
    """

    def test_task_reminder_job_callable(self):
        """TC-09a: task_reminder_job() 직접 호출 시 예외 없이 실행"""
        try:
            task_reminder_job()
        except Exception as e:
            pytest.fail(f"task_reminder_job() 예외 발생: {e}")

    def test_shift_end_reminder_job_callable(self):
        """TC-09b: shift_end_reminder_job() 직접 호출 시 예외 없이 실행"""
        try:
            shift_end_reminder_job()
        except Exception as e:
            pytest.fail(f"shift_end_reminder_job() 예외 발생: {e}")

    def test_task_escalation_job_callable(self):
        """TC-09c: task_escalation_job() 직접 호출 시 예외 없이 실행"""
        try:
            task_escalation_job()
        except Exception as e:
            pytest.fail(f"task_escalation_job() 예외 발생: {e}")
