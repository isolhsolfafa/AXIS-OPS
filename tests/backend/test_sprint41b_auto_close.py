"""
Sprint 41-B: 릴레이 미완료 task 자동 마감 + Manager 알림 테스트
TC-41B-01 ~ TC-41B-14 (14건)
"""

import pytest
import psycopg2
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# backend 경로 추가
backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _create_product(cursor, serial_number: str, model: str = 'GALLANT-50') -> str:
    """plan.product_info + qr_registry 생성 헬퍼, qr_doc_id 반환"""
    qr_doc_id = f'DOC_{serial_number}'
    cursor.execute("""
        INSERT INTO plan.product_info (serial_number, model, prod_date)
        VALUES (%s, %s, NOW()::date)
        ON CONFLICT (serial_number) DO NOTHING
    """, (serial_number, model))
    cursor.execute("""
        INSERT INTO public.qr_registry (qr_doc_id, serial_number)
        VALUES (%s, %s)
        ON CONFLICT (qr_doc_id) DO NOTHING
    """, (qr_doc_id, serial_number))
    return qr_doc_id


def _create_task(cursor, serial_number: str, qr_doc_id: str,
                 task_category: str, task_id: str, task_name: str,
                 worker_id: int, started_at: datetime = None) -> int:
    """app_task_details 생성 헬퍼, task_detail_id 반환"""
    if started_at is None:
        started_at = datetime.now(tz=__import__('pytz').timezone('Asia/Seoul')) - timedelta(hours=2)

    cursor.execute("""
        INSERT INTO app_task_details (
            worker_id, serial_number, qr_doc_id, task_category,
            task_id, task_name, started_at, is_applicable
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
        RETURNING id
    """, (worker_id, serial_number, qr_doc_id, task_category,
          task_id, task_name, started_at))
    return cursor.fetchone()[0]


def _create_completion_log(cursor, task_id: int, worker_id: int,
                           serial_number: str, qr_doc_id: str,
                           task_category: str, task_id_ref: str,
                           task_name: str, completed_at: datetime) -> int:
    """work_completion_log 생성 헬퍼, log_id 반환"""
    started_at = completed_at - timedelta(hours=1)
    duration = 60
    cursor.execute("""
        INSERT INTO work_completion_log (
            task_id, worker_id, serial_number, qr_doc_id,
            task_category, task_id_ref, task_name,
            completed_at, duration_minutes
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (task_id, worker_id, serial_number, qr_doc_id,
          task_category, task_id_ref, task_name,
          completed_at, duration))
    return cursor.fetchone()[0]


def _create_start_log(cursor, task_id: int, worker_id: int,
                      serial_number: str, qr_doc_id: str,
                      task_category: str, task_id_ref: str,
                      task_name: str, started_at: datetime) -> int:
    """work_start_log 생성 헬퍼"""
    cursor.execute("""
        INSERT INTO work_start_log (
            task_id, worker_id, serial_number, qr_doc_id,
            task_category, task_id_ref, task_name, started_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (task_id, worker_id, serial_number, qr_doc_id,
          task_category, task_id_ref, task_name, started_at))
    return cursor.fetchone()[0]


def _setup_test_workers(db_conn):
    """테스트용 작업자 2명 생성 (MECH), mech_worker_id, elec_worker_id 반환"""
    from werkzeug.security import generate_password_hash
    pw = generate_password_hash('Test1234!')
    cursor = db_conn.cursor()

    for email in ('tb41b_w1@test.axisos.com', 'tb41b_w2@test.axisos.com'):
        cursor.execute("DELETE FROM work_completion_log WHERE worker_id IN (SELECT id FROM workers WHERE email = %s)", (email,))
        cursor.execute("DELETE FROM work_start_log WHERE worker_id IN (SELECT id FROM workers WHERE email = %s)", (email,))
        cursor.execute("DELETE FROM app_task_details WHERE worker_id IN (SELECT id FROM workers WHERE email = %s)", (email,))
        cursor.execute("DELETE FROM app_alert_logs WHERE triggered_by_worker_id IN (SELECT id FROM workers WHERE email = %s)", (email,))
        cursor.execute("DELETE FROM workers WHERE email = %s", (email,))
    db_conn.commit()

    cursor.execute("""
        INSERT INTO workers (name, email, password_hash, role, company,
            approval_status, email_verified, is_manager, is_admin)
        VALUES (%s, %s, %s, 'MECH'::role_enum, 'FNI', 'approved'::approval_status_enum, TRUE, FALSE, FALSE)
        RETURNING id
    """, ('TB41B Worker1', 'tb41b_w1@test.axisos.com', pw))
    w1 = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO workers (name, email, password_hash, role, company,
            approval_status, email_verified, is_manager, is_admin)
        VALUES (%s, %s, %s, 'MECH'::role_enum, 'FNI', 'approved'::approval_status_enum, TRUE, FALSE, FALSE)
        RETURNING id
    """, ('TB41B Worker2', 'tb41b_w2@test.axisos.com', pw))
    w2 = cursor.fetchone()[0]

    db_conn.commit()
    cursor.close()
    return w1, w2


def _cleanup_test_data(db_conn, serial_numbers: list, worker_ids: list):
    """테스트 데이터 정리"""
    cursor = db_conn.cursor()
    try:
        for sn in serial_numbers:
            cursor.execute("DELETE FROM app_alert_logs WHERE serial_number = %s", (sn,))
            cursor.execute("DELETE FROM work_completion_log WHERE serial_number = %s", (sn,))
            cursor.execute("DELETE FROM work_start_log WHERE serial_number = %s", (sn,))
            cursor.execute("DELETE FROM app_task_details WHERE serial_number = %s", (sn,))
            cursor.execute("DELETE FROM completion_status WHERE serial_number = %s", (sn,))
            cursor.execute("DELETE FROM public.qr_registry WHERE serial_number = %s", (sn,))
            cursor.execute("DELETE FROM plan.product_info WHERE serial_number = %s", (sn,))
        for wid in worker_ids:
            cursor.execute("DELETE FROM workers WHERE id = %s", (wid,))
        db_conn.commit()
    except Exception as e:
        db_conn.rollback()
        print(f"Cleanup failed: {e}")
    finally:
        cursor.close()


# ──────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────

class TestAutoCloseRelayTask:
    """TC-41B-01~07: 자동 마감 로직"""

    def test_tc41b_01_self_inspection_auto_closes_relay_tasks(self, db_conn, seed_test_data):
        """
        TC-41B-01: MECH task A, B relay 종료 후 SELF_INSPECTION finalize
        → A, B 모두 자동 마감 확인 (completed_at = last_completion_log 기준)
        """
        import pytz
        from app.models.task_detail import get_orphan_relay_tasks, auto_close_relay_task

        kst = pytz.timezone('Asia/Seoul')
        sn = 'TC41B01-TEST'
        w1, w2 = _setup_test_workers(db_conn)
        serial_numbers = [sn]
        worker_ids = [w1, w2]

        try:
            cursor = db_conn.cursor()
            qr_doc_id = _create_product(cursor, sn)
            db_conn.commit()

            now = datetime.now(kst)
            started = now - timedelta(hours=3)
            completed_a = now - timedelta(hours=2)
            completed_b = now - timedelta(hours=1)

            # Task A (MECH WASTE_GAS_LINE_1)
            task_a_id = _create_task(cursor, sn, qr_doc_id, 'MECH', 'WASTE_GAS_LINE_1',
                                     'Waste Gas LINE 1', w1, started)
            _create_start_log(cursor, task_a_id, w1, sn, qr_doc_id,
                               'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1', started)
            _create_completion_log(cursor, task_a_id, w1, sn, qr_doc_id,
                                   'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1', completed_a)

            # Task B (MECH UTIL_LINE_1)
            task_b_id = _create_task(cursor, sn, qr_doc_id, 'MECH', 'UTIL_LINE_1',
                                     'Util LINE 1', w2, started)
            _create_start_log(cursor, task_b_id, w2, sn, qr_doc_id,
                               'MECH', 'UTIL_LINE_1', 'Util LINE 1', started)
            _create_completion_log(cursor, task_b_id, w2, sn, qr_doc_id,
                                   'MECH', 'UTIL_LINE_1', 'Util LINE 1', completed_b)
            db_conn.commit()

            # 자동 마감 실행 (SELF_INSPECTION finalize 시뮬레이션)
            orphans = get_orphan_relay_tasks(sn, 'MECH')
            assert len(orphans) == 2, f"Expected 2 orphan tasks, got {len(orphans)}"

            closed = 0
            for orphan in orphans:
                success = auto_close_relay_task(
                    task_detail_id=orphan['task_detail_id'],
                    last_completion_at=orphan['last_completion_at'],
                    worker_count=orphan['worker_count'],
                )
                if success:
                    closed += 1

            assert closed == 2, f"Expected 2 tasks auto-closed, got {closed}"

            # 자동 마감 후 completed_at 설정 확인
            cursor.execute("""
                SELECT id, completed_at FROM app_task_details
                WHERE serial_number = %s AND task_category = 'MECH'
                  AND task_id IN ('WASTE_GAS_LINE_1', 'UTIL_LINE_1')
            """, (sn,))
            rows = cursor.fetchall()
            assert len(rows) == 2
            for row in rows:
                assert row[1] is not None, f"task {row[0]} should have completed_at set"

        finally:
            cursor.close()
            _cleanup_test_data(db_conn, serial_numbers, worker_ids)

    def test_tc41b_02_duration_minutes_calculated_correctly(self, db_conn, seed_test_data):
        """
        TC-41B-02: 자동 마감된 task의 duration_minutes = (started_at ~ last_completion_at) 계산 확인
        """
        import pytz
        from app.models.task_detail import get_orphan_relay_tasks, auto_close_relay_task

        kst = pytz.timezone('Asia/Seoul')
        sn = 'TC41B02-TEST'
        w1, w2 = _setup_test_workers(db_conn)

        try:
            cursor = db_conn.cursor()
            qr_doc_id = _create_product(cursor, sn)
            db_conn.commit()

            now = datetime.now(kst)
            started = now - timedelta(hours=3)
            completed = now - timedelta(hours=1)  # 2시간 duration

            task_id = _create_task(cursor, sn, qr_doc_id, 'MECH', 'WASTE_GAS_LINE_1',
                                   'Waste Gas LINE 1', w1, started)
            _create_start_log(cursor, task_id, w1, sn, qr_doc_id,
                               'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1', started)
            _create_completion_log(cursor, task_id, w1, sn, qr_doc_id,
                                   'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1', completed)
            db_conn.commit()

            orphans = get_orphan_relay_tasks(sn, 'MECH')
            assert len(orphans) == 1

            auto_close_relay_task(
                task_detail_id=orphans[0]['task_detail_id'],
                last_completion_at=orphans[0]['last_completion_at'],
                worker_count=orphans[0]['worker_count'],
            )

            cursor.execute("""
                SELECT duration_minutes FROM app_task_details WHERE id = %s
            """, (task_id,))
            duration = cursor.fetchone()[0]
            # started ~ completed = 2시간 = 120분 (±5분 허용)
            assert duration is not None
            assert 115 <= duration <= 125, f"Expected ~120 minutes, got {duration}"

        finally:
            cursor.close()
            _cleanup_test_data(db_conn, [sn], [w1, w2])

    def test_tc41b_03_worker_count_set_correctly(self, db_conn, seed_test_data):
        """
        TC-41B-03: 자동 마감된 task의 worker_count = completion_log의 DISTINCT worker_id 수 확인
        """
        import pytz
        from app.models.task_detail import get_orphan_relay_tasks, auto_close_relay_task

        kst = pytz.timezone('Asia/Seoul')
        sn = 'TC41B03-TEST'
        w1, w2 = _setup_test_workers(db_conn)

        try:
            cursor = db_conn.cursor()
            qr_doc_id = _create_product(cursor, sn)
            db_conn.commit()

            now = datetime.now(kst)
            started = now - timedelta(hours=4)

            task_id = _create_task(cursor, sn, qr_doc_id, 'MECH', 'UTIL_LINE_1',
                                   'Util LINE 1', w1, started)
            # 2명이 각각 완료 기록
            _create_start_log(cursor, task_id, w1, sn, qr_doc_id,
                               'MECH', 'UTIL_LINE_1', 'Util LINE 1', started)
            _create_completion_log(cursor, task_id, w1, sn, qr_doc_id,
                                   'MECH', 'UTIL_LINE_1', 'Util LINE 1',
                                   now - timedelta(hours=2))
            _create_start_log(cursor, task_id, w2, sn, qr_doc_id,
                               'MECH', 'UTIL_LINE_1', 'Util LINE 1',
                               now - timedelta(hours=1, minutes=30))
            _create_completion_log(cursor, task_id, w2, sn, qr_doc_id,
                                   'MECH', 'UTIL_LINE_1', 'Util LINE 1',
                                   now - timedelta(minutes=30))
            db_conn.commit()

            orphans = get_orphan_relay_tasks(sn, 'MECH')
            assert len(orphans) == 1
            assert orphans[0]['worker_count'] == 2

            auto_close_relay_task(
                task_detail_id=orphans[0]['task_detail_id'],
                last_completion_at=orphans[0]['last_completion_at'],
                worker_count=orphans[0]['worker_count'],
            )

            cursor.execute("""
                SELECT worker_count FROM app_task_details WHERE id = %s
            """, (task_id,))
            worker_count = cursor.fetchone()[0]
            assert worker_count == 2

        finally:
            cursor.close()
            _cleanup_test_data(db_conn, [sn], [w1, w2])

    def test_tc41b_04_category_completed_after_auto_close(self, db_conn, seed_test_data):
        """
        TC-41B-04: SELF_INSPECTION finalize 후 category_completed 정상 판단
        (자동 마감된 task가 incomplete에서 제외)
        """
        import pytz
        from app.models.task_detail import (
            get_orphan_relay_tasks, auto_close_relay_task, get_incomplete_tasks
        )

        kst = pytz.timezone('Asia/Seoul')
        sn = 'TC41B04-TEST'
        w1, w2 = _setup_test_workers(db_conn)

        try:
            cursor = db_conn.cursor()
            qr_doc_id = _create_product(cursor, sn)
            db_conn.commit()

            now = datetime.now(kst)
            started = now - timedelta(hours=3)

            # 릴레이 미완료 task (WASTE_GAS_LINE_1)
            relay_task_id = _create_task(cursor, sn, qr_doc_id, 'MECH', 'WASTE_GAS_LINE_1',
                                         'Waste Gas LINE 1', w1, started)
            _create_start_log(cursor, relay_task_id, w1, sn, qr_doc_id,
                               'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1', started)
            _create_completion_log(cursor, relay_task_id, w1, sn, qr_doc_id,
                                   'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1',
                                   now - timedelta(hours=1))
            db_conn.commit()

            # 자동 마감 전 incomplete = 1
            incomplete_before = get_incomplete_tasks(sn, 'MECH')
            assert len(incomplete_before) == 1

            # 자동 마감 실행
            orphans = get_orphan_relay_tasks(sn, 'MECH')
            for orphan in orphans:
                auto_close_relay_task(
                    task_detail_id=orphan['task_detail_id'],
                    last_completion_at=orphan['last_completion_at'],
                    worker_count=orphan['worker_count'],
                )

            # 자동 마감 후 incomplete = 0
            incomplete_after = get_incomplete_tasks(sn, 'MECH')
            assert len(incomplete_after) == 0, \
                f"Expected 0 incomplete tasks after auto-close, got {len(incomplete_after)}"

        finally:
            cursor.close()
            _cleanup_test_data(db_conn, [sn], [w1, w2])

    def test_tc41b_05_no_relay_tasks_regression(self, db_conn, seed_test_data):
        """
        TC-41B-05: 릴레이 없는 S/N에서 SELF_INSPECTION finalize → orphans = [] (regression)
        """
        import pytz
        from app.models.task_detail import get_orphan_relay_tasks

        kst = pytz.timezone('Asia/Seoul')
        sn = 'TC41B05-TEST'
        w1, w2 = _setup_test_workers(db_conn)

        try:
            cursor = db_conn.cursor()
            qr_doc_id = _create_product(cursor, sn)
            db_conn.commit()

            # 일반 완료된 task (completed_at 설정됨)
            now = datetime.now(kst)
            started = now - timedelta(hours=2)
            completed = now - timedelta(hours=1)

            cursor.execute("""
                INSERT INTO app_task_details (
                    worker_id, serial_number, qr_doc_id, task_category,
                    task_id, task_name, started_at, completed_at, is_applicable
                ) VALUES (%s, %s, %s, 'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1', %s, %s, TRUE)
                RETURNING id
            """, (w1, sn, qr_doc_id, started, completed))
            task_id = cursor.fetchone()[0]
            db_conn.commit()

            # orphan 없음 (completed_at 설정됨)
            orphans = get_orphan_relay_tasks(sn, 'MECH')
            assert orphans == [], f"Expected no orphans, got {orphans}"

        finally:
            cursor.close()
            _cleanup_test_data(db_conn, [sn], [w1, w2])

    def test_tc41b_06_elec_inspection_auto_closes_elec_relay(self, db_conn, seed_test_data):
        """
        TC-41B-06: ELEC INSPECTION finalize → ELEC 카테고리 릴레이 task 자동 마감 확인
        """
        import pytz
        from app.models.task_detail import get_orphan_relay_tasks, auto_close_relay_task

        kst = pytz.timezone('Asia/Seoul')
        sn = 'TC41B06-TEST'
        w1, w2 = _setup_test_workers(db_conn)

        try:
            cursor = db_conn.cursor()
            qr_doc_id = _create_product(cursor, sn)
            db_conn.commit()

            now = datetime.now(kst)
            started = now - timedelta(hours=3)

            # ELEC relay task
            task_id = _create_task(cursor, sn, qr_doc_id, 'ELEC', 'PANEL_WORK',
                                   '판넬 작업', w1, started)
            _create_start_log(cursor, task_id, w1, sn, qr_doc_id,
                               'ELEC', 'PANEL_WORK', '판넬 작업', started)
            _create_completion_log(cursor, task_id, w1, sn, qr_doc_id,
                                   'ELEC', 'PANEL_WORK', '판넬 작업',
                                   now - timedelta(hours=1))
            db_conn.commit()

            orphans = get_orphan_relay_tasks(sn, 'ELEC')
            assert len(orphans) == 1

            success = auto_close_relay_task(
                task_detail_id=orphans[0]['task_detail_id'],
                last_completion_at=orphans[0]['last_completion_at'],
                worker_count=orphans[0]['worker_count'],
            )
            assert success is True

            cursor.execute("SELECT completed_at FROM app_task_details WHERE id = %s", (task_id,))
            completed_at = cursor.fetchone()[0]
            assert completed_at is not None

        finally:
            cursor.close()
            _cleanup_test_data(db_conn, [sn], [w1, w2])

    def test_tc41b_07_tms_pressure_test_auto_closes_tms_relay(self, db_conn, seed_test_data):
        """
        TC-41B-07: TMS PRESSURE_TEST finalize → TMS 카테고리 릴레이 task 자동 마감 확인
        """
        import pytz
        from app.models.task_detail import get_orphan_relay_tasks, auto_close_relay_task

        kst = pytz.timezone('Asia/Seoul')
        sn = 'TC41B07-TEST'
        w1, w2 = _setup_test_workers(db_conn)

        try:
            cursor = db_conn.cursor()
            qr_doc_id = _create_product(cursor, sn)
            db_conn.commit()

            now = datetime.now(kst)
            started = now - timedelta(hours=5)

            # TMS relay task (TANK_MODULE)
            task_id = _create_task(cursor, sn, qr_doc_id, 'TMS', 'TANK_MODULE',
                                   'Tank Module', w1, started)
            _create_start_log(cursor, task_id, w1, sn, qr_doc_id,
                               'TMS', 'TANK_MODULE', 'Tank Module', started)
            _create_completion_log(cursor, task_id, w1, sn, qr_doc_id,
                                   'TMS', 'TANK_MODULE', 'Tank Module',
                                   now - timedelta(hours=1))
            db_conn.commit()

            orphans = get_orphan_relay_tasks(sn, 'TMS')
            assert len(orphans) == 1

            success = auto_close_relay_task(
                task_detail_id=orphans[0]['task_detail_id'],
                last_completion_at=orphans[0]['last_completion_at'],
                worker_count=orphans[0]['worker_count'],
            )
            assert success is True

        finally:
            cursor.close()
            _cleanup_test_data(db_conn, [sn], [w1, w2])


class TestRelayOrphanAlert:
    """TC-41B-08~11: Manager 알림"""

    def test_tc41b_08_alert_created_for_orphan_after_4_hours(self, db_conn, seed_test_data):
        """
        TC-41B-08: MECH task relay 종료 후 4시간 경과 → check_orphan_relay_tasks_job 실행
        → RELAY_ORPHAN 알림 생성 확인
        """
        import pytz
        from unittest.mock import patch
        from app.services.scheduler_service import check_orphan_relay_tasks_job

        kst = pytz.timezone('Asia/Seoul')
        sn = 'TC41B08-TEST'
        w1, w2 = _setup_test_workers(db_conn)

        try:
            cursor = db_conn.cursor()
            qr_doc_id = _create_product(cursor, sn)
            db_conn.commit()

            now = datetime.now(kst)
            # 5시간 전 relay 완료 (4시간 threshold 초과)
            started = now - timedelta(hours=6)
            completed = now - timedelta(hours=5)

            task_id = _create_task(cursor, sn, qr_doc_id, 'MECH', 'WASTE_GAS_LINE_1',
                                   'Waste Gas LINE 1', w1, started)
            _create_start_log(cursor, task_id, w1, sn, qr_doc_id,
                               'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1', started)
            _create_completion_log(cursor, task_id, w1, sn, qr_doc_id,
                                   'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1', completed)
            db_conn.commit()

            # 스케줄러 job 실행
            check_orphan_relay_tasks_job()

            # 알림 생성 확인
            cursor.execute("""
                SELECT id, message FROM app_alert_logs
                WHERE alert_type = 'RELAY_ORPHAN'
                  AND serial_number = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (sn,))
            alert = cursor.fetchone()
            assert alert is not None, "RELAY_ORPHAN alert should have been created"

        finally:
            cursor.close()
            _cleanup_test_data(db_conn, [sn], [w1, w2])

    def test_tc41b_09_alert_message_contains_required_fields(self, db_conn, seed_test_data):
        """
        TC-41B-09: 알림 메시지에 serial_number, task_name, worker_count 포함 확인
        """
        import pytz
        from app.services.scheduler_service import check_orphan_relay_tasks_job

        kst = pytz.timezone('Asia/Seoul')
        sn = 'TC41B09-TEST'
        w1, w2 = _setup_test_workers(db_conn)

        try:
            cursor = db_conn.cursor()
            qr_doc_id = _create_product(cursor, sn)
            db_conn.commit()

            now = datetime.now(kst)
            started = now - timedelta(hours=6)
            completed = now - timedelta(hours=5)

            task_id = _create_task(cursor, sn, qr_doc_id, 'MECH', 'WASTE_GAS_LINE_1',
                                   'Waste Gas LINE 1', w1, started)
            _create_start_log(cursor, task_id, w1, sn, qr_doc_id,
                               'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1', started)
            _create_completion_log(cursor, task_id, w1, sn, qr_doc_id,
                                   'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1', completed)
            # 두 번째 작업자도 완료
            _create_start_log(cursor, task_id, w2, sn, qr_doc_id,
                               'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1',
                               started + timedelta(minutes=30))
            _create_completion_log(cursor, task_id, w2, sn, qr_doc_id,
                                   'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1',
                                   completed + timedelta(minutes=30))
            db_conn.commit()

            # 기존 알림 제거 후 job 실행
            cursor.execute("DELETE FROM app_alert_logs WHERE serial_number = %s AND alert_type = 'RELAY_ORPHAN'", (sn,))
            db_conn.commit()

            check_orphan_relay_tasks_job()

            cursor.execute("""
                SELECT message FROM app_alert_logs
                WHERE alert_type = 'RELAY_ORPHAN' AND serial_number = %s
                ORDER BY created_at DESC LIMIT 1
            """, (sn,))
            row = cursor.fetchone()
            assert row is not None
            message = row[0]
            assert sn in message, f"serial_number not in message: {message}"
            assert 'Waste Gas LINE 1' in message, f"task_name not in message: {message}"
            assert '2' in message, f"worker_count not in message: {message}"

        finally:
            cursor.close()
            _cleanup_test_data(db_conn, [sn], [w1, w2])

    def test_tc41b_10_no_duplicate_alert_within_24_hours(self, db_conn, seed_test_data):
        """
        TC-41B-10: 24시간 내 동일 task에 대해 중복 알림 미발송 확인
        """
        import pytz
        from app.services.scheduler_service import check_orphan_relay_tasks_job

        kst = pytz.timezone('Asia/Seoul')
        sn = 'TC41B10-TEST'
        w1, w2 = _setup_test_workers(db_conn)

        try:
            cursor = db_conn.cursor()
            qr_doc_id = _create_product(cursor, sn)
            db_conn.commit()

            now = datetime.now(kst)
            started = now - timedelta(hours=8)
            completed = now - timedelta(hours=7)

            task_id = _create_task(cursor, sn, qr_doc_id, 'MECH', 'WASTE_GAS_LINE_1',
                                   'Waste Gas LINE 1', w1, started)
            _create_start_log(cursor, task_id, w1, sn, qr_doc_id,
                               'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1', started)
            _create_completion_log(cursor, task_id, w1, sn, qr_doc_id,
                                   'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1', completed)
            db_conn.commit()

            # 기존 알림 제거
            cursor.execute("DELETE FROM app_alert_logs WHERE serial_number = %s AND alert_type = 'RELAY_ORPHAN'", (sn,))
            db_conn.commit()

            # 1차 실행
            check_orphan_relay_tasks_job()

            cursor.execute("""
                SELECT COUNT(*) FROM app_alert_logs
                WHERE alert_type = 'RELAY_ORPHAN' AND serial_number = %s
            """, (sn,))
            count_after_first = cursor.fetchone()[0]
            assert count_after_first == 1

            # 2차 실행 (중복 발송 안 되어야 함)
            check_orphan_relay_tasks_job()

            cursor.execute("""
                SELECT COUNT(*) FROM app_alert_logs
                WHERE alert_type = 'RELAY_ORPHAN' AND serial_number = %s
            """, (sn,))
            count_after_second = cursor.fetchone()[0]
            assert count_after_second == 1, \
                f"Duplicate alert should not be sent within 24h. count={count_after_second}"

        finally:
            cursor.close()
            _cleanup_test_data(db_conn, [sn], [w1, w2])

    def test_tc41b_11_completed_task_excluded_from_orphan_alert(self, db_conn, seed_test_data):
        """
        TC-41B-11: completed_at이 설정된 task(자동 마감 완료)는 알림 대상 제외 확인
        """
        import pytz
        from app.services.scheduler_service import check_orphan_relay_tasks_job

        kst = pytz.timezone('Asia/Seoul')
        sn = 'TC41B11-TEST'
        w1, w2 = _setup_test_workers(db_conn)

        try:
            cursor = db_conn.cursor()
            qr_doc_id = _create_product(cursor, sn)
            db_conn.commit()

            now = datetime.now(kst)
            started = now - timedelta(hours=8)
            completed = now - timedelta(hours=7)

            # 이미 완료된 task (completed_at 설정됨)
            cursor.execute("""
                INSERT INTO app_task_details (
                    worker_id, serial_number, qr_doc_id, task_category,
                    task_id, task_name, started_at, completed_at, is_applicable
                ) VALUES (%s, %s, %s, 'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1', %s, %s, TRUE)
                RETURNING id
            """, (w1, sn, qr_doc_id, started, completed))
            task_id = cursor.fetchone()[0]
            # completion_log도 추가 (5시간 전)
            _create_completion_log(cursor, task_id, w1, sn, qr_doc_id,
                                   'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1',
                                   now - timedelta(hours=5))
            db_conn.commit()

            # 기존 알림 제거
            cursor.execute("DELETE FROM app_alert_logs WHERE serial_number = %s AND alert_type = 'RELAY_ORPHAN'", (sn,))
            db_conn.commit()

            check_orphan_relay_tasks_job()

            cursor.execute("""
                SELECT COUNT(*) FROM app_alert_logs
                WHERE alert_type = 'RELAY_ORPHAN' AND serial_number = %s
            """, (sn,))
            count = cursor.fetchone()[0]
            assert count == 0, f"Completed task should not trigger RELAY_ORPHAN alert, got {count}"

        finally:
            cursor.close()
            _cleanup_test_data(db_conn, [sn], [w1, w2])


class TestMixedScenarios:
    """TC-41B-12~14: 혼합 시나리오"""

    def test_tc41b_12_alert_then_auto_close_flow(self, db_conn, seed_test_data):
        """
        TC-41B-12: worker1 relay → 3시간 후 worker2 relay → 4시간 후 알림 발생
        → SELF_INSPECTION finalize → 자동 마감 (알림 후 마감 정상 동작)
        """
        import pytz
        from app.models.task_detail import get_orphan_relay_tasks, auto_close_relay_task
        from app.services.scheduler_service import check_orphan_relay_tasks_job

        kst = pytz.timezone('Asia/Seoul')
        sn = 'TC41B12-TEST'
        w1, w2 = _setup_test_workers(db_conn)

        try:
            cursor = db_conn.cursor()
            qr_doc_id = _create_product(cursor, sn)
            db_conn.commit()

            now = datetime.now(kst)
            started = now - timedelta(hours=8)
            completed_w1 = now - timedelta(hours=7)   # w1 relay 완료 (7시간 전)
            completed_w2 = now - timedelta(hours=4, minutes=30)  # w2 relay 완료 (4.5시간 전 — threshold 초과)

            task_id = _create_task(cursor, sn, qr_doc_id, 'MECH', 'WASTE_GAS_LINE_1',
                                   'Waste Gas LINE 1', w1, started)
            _create_start_log(cursor, task_id, w1, sn, qr_doc_id,
                               'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1', started)
            _create_completion_log(cursor, task_id, w1, sn, qr_doc_id,
                                   'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1', completed_w1)
            _create_start_log(cursor, task_id, w2, sn, qr_doc_id,
                               'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1',
                               completed_w1 + timedelta(minutes=30))
            _create_completion_log(cursor, task_id, w2, sn, qr_doc_id,
                                   'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1', completed_w2)
            db_conn.commit()

            # 기존 알림 제거 후 알림 job 실행
            cursor.execute("DELETE FROM app_alert_logs WHERE serial_number = %s AND alert_type = 'RELAY_ORPHAN'", (sn,))
            db_conn.commit()
            check_orphan_relay_tasks_job()

            # 알림 생성 확인
            cursor.execute("""
                SELECT COUNT(*) FROM app_alert_logs
                WHERE alert_type = 'RELAY_ORPHAN' AND serial_number = %s
            """, (sn,))
            alert_count = cursor.fetchone()[0]
            assert alert_count >= 1, "Alert should have been created"

            # SELF_INSPECTION finalize 시뮬레이션 → 자동 마감
            orphans = get_orphan_relay_tasks(sn, 'MECH')
            assert len(orphans) == 1
            success = auto_close_relay_task(
                task_detail_id=orphans[0]['task_detail_id'],
                last_completion_at=orphans[0]['last_completion_at'],
                worker_count=orphans[0]['worker_count'],
            )
            assert success is True

            # 자동 마감 후 completed_at 설정 확인
            cursor.execute("SELECT completed_at FROM app_task_details WHERE id = %s", (task_id,))
            completed_at = cursor.fetchone()[0]
            assert completed_at is not None

        finally:
            cursor.close()
            _cleanup_test_data(db_conn, [sn], [w1, w2])

    def test_tc41b_13_different_task_finalize_does_not_close_relay(self, db_conn, seed_test_data):
        """
        TC-41B-13: worker1 relay → worker2 finalize(다른 task) → 해당 relay task는 열린 상태 유지
        (다른 task의 finalize로 닫히지 않음 — FINAL task만 트리거)
        """
        import pytz
        from app.models.task_detail import get_orphan_relay_tasks

        kst = pytz.timezone('Asia/Seoul')
        sn = 'TC41B13-TEST'
        w1, w2 = _setup_test_workers(db_conn)

        try:
            cursor = db_conn.cursor()
            qr_doc_id = _create_product(cursor, sn)
            db_conn.commit()

            now = datetime.now(kst)
            started = now - timedelta(hours=3)
            completed = now - timedelta(hours=1)

            # relay task A
            task_a_id = _create_task(cursor, sn, qr_doc_id, 'MECH', 'WASTE_GAS_LINE_1',
                                     'Waste Gas LINE 1', w1, started)
            _create_start_log(cursor, task_a_id, w1, sn, qr_doc_id,
                               'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1', started)
            _create_completion_log(cursor, task_a_id, w1, sn, qr_doc_id,
                                   'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1', completed)
            db_conn.commit()

            # 다른 task (UTIL_LINE_1) — non-FINAL → 자동 마감 안 됨
            # get_orphan_relay_tasks는 FINAL task 완료 시에만 호출됨
            # 여기서는 UTIL_LINE_1로 finalize해도 orphan 로직이 적용 안 됨을 확인
            # (FINAL_TASK_IDS에 UTIL_LINE_1 없음)
            from app.services.task_service import FINAL_TASK_IDS
            assert 'UTIL_LINE_1' not in FINAL_TASK_IDS, \
                "UTIL_LINE_1 should NOT be in FINAL_TASK_IDS"

            # relay task A는 여전히 미완료
            orphans = get_orphan_relay_tasks(sn, 'MECH')
            task_a_still_open = any(o['task_detail_id'] == task_a_id for o in orphans)
            assert task_a_still_open, "Relay task A should still be open"

        finally:
            cursor.close()
            _cleanup_test_data(db_conn, [sn], [w1, w2])

    def test_tc41b_14_normal_finalize_no_orphan_regression(self, db_conn, seed_test_data):
        """
        TC-41B-14: 기존 단독 작업 start→complete (finalize=True) → orphan 검색 0건
        → 자동 마감 미실행 (regression)
        """
        import pytz
        from app.models.task_detail import get_orphan_relay_tasks

        kst = pytz.timezone('Asia/Seoul')
        sn = 'TC41B14-TEST'
        w1, w2 = _setup_test_workers(db_conn)

        try:
            cursor = db_conn.cursor()
            qr_doc_id = _create_product(cursor, sn)
            db_conn.commit()

            now = datetime.now(kst)
            started = now - timedelta(hours=2)
            completed = now - timedelta(hours=1)

            # 단독 작업 — completed_at 설정됨
            cursor.execute("""
                INSERT INTO app_task_details (
                    worker_id, serial_number, qr_doc_id, task_category,
                    task_id, task_name, started_at, completed_at, is_applicable
                ) VALUES (%s, %s, %s, 'MECH', 'WASTE_GAS_LINE_1', 'Waste Gas LINE 1', %s, %s, TRUE)
                RETURNING id
            """, (w1, sn, qr_doc_id, started, completed))
            task_id = cursor.fetchone()[0]
            db_conn.commit()

            # orphan 없음 (completed_at 설정됨 → work_completion_log JOIN 조건 미충족)
            orphans = get_orphan_relay_tasks(sn, 'MECH')
            assert orphans == [], \
                f"Normal finalized task should have no orphans, got {orphans}"

        finally:
            cursor.close()
            _cleanup_test_data(db_conn, [sn], [w1, w2])
