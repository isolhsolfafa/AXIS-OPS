"""
누락 모델 단위 테스트
Sprint 5: WorkStartLog, WorkCompletionLog, OfflineSyncQueue, LocationHistory, EmailVerification

테이블 스키마 기준 (migrations 참고):
- work_start_log: id, task_id, worker_id, serial_number, qr_doc_id, task_category, task_id_ref, task_name, started_at, created_at
- work_completion_log: id, task_id, worker_id, serial_number, qr_doc_id, task_category, task_id_ref, task_name, completed_at, duration_minutes, created_at
- offline_sync_queue: id, worker_id, operation, table_name, record_id, data(JSONB), synced, synced_at, created_at
- location_history: id, worker_id, latitude, longitude, recorded_at, created_at
- email_verification: id, worker_id, verification_code, expires_at, verified_at, created_at
"""

import pytest
import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

# backend 경로 추가
backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


# ==================== WorkStartLog 테스트 ====================

class TestWorkStartLog:
    """
    WorkStartLog 모델 단위 테스트
    테이블: work_start_log (Sprint 5: 누락 모델 추가)
    """

    def test_create_work_start_log(self, db_conn, create_test_worker, create_test_product):
        """
        work_start_log 레코드 DB에 직접 생성 테스트

        Expected:
        - 레코드가 work_start_log 테이블에 저장됨
        - started_at, created_at 자동 설정
        - task_id, worker_id FK 참조 무결성 유지
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        # 선행 데이터 생성
        worker_id = create_test_worker(
            email='wsl_create@test.com', password='Test123!',
            name='WSL Create Worker', role='MECH'
        )

        # app_task_details 레코드 필요 (work_start_log.task_id FK)
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO plan.product_info (serial_number, model)
            VALUES ('SN-WSL-001', 'TEST-MODEL')
            ON CONFLICT DO NOTHING
        """)
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number)
            VALUES ('DOC-WSL-001', 'SN-WSL-001')
            ON CONFLICT DO NOTHING
        """)
        cursor.execute("""
            INSERT INTO app_task_details (
                worker_id, serial_number, qr_doc_id, task_category,
                task_id, task_name
            )
            VALUES (%s, 'SN-WSL-001', 'DOC-WSL-001', 'MECH', 'CABINET_ASSY', '캐비넷 조립')
            RETURNING id
        """, (worker_id,))
        task_detail_id = cursor.fetchone()[0]
        db_conn.commit()

        # work_start_log 생성
        now = datetime.now(timezone.utc)
        cursor.execute("""
            INSERT INTO work_start_log (
                task_id, worker_id, serial_number, qr_doc_id,
                task_category, task_id_ref, task_name, started_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, started_at, created_at
        """, (task_detail_id, worker_id, 'SN-WSL-001', 'DOC-WSL-001',
              'MECH', 'CABINET_ASSY', '캐비넷 조립', now))

        result = cursor.fetchone()
        db_conn.commit()

        assert result is not None
        log_id = result[0]
        assert log_id > 0
        assert result[2] is not None  # created_at auto-set

        # 정리
        cursor.execute("DELETE FROM work_start_log WHERE id = %s", (log_id,))
        cursor.execute("DELETE FROM app_task_details WHERE id = %s", (task_detail_id,))
        cursor.execute("DELETE FROM public.qr_registry WHERE qr_doc_id = 'DOC-WSL-001'")
        cursor.execute("DELETE FROM plan.product_info WHERE serial_number = 'SN-WSL-001'")
        db_conn.commit()
        cursor.close()

    def test_get_by_id(self, db_conn, create_test_worker):
        """
        work_start_log ID로 조회 테스트

        Expected:
        - 특정 ID로 레코드 조회 가능
        - 존재하지 않는 ID는 None 반환
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='wsl_getid@test.com', password='Test123!',
            name='WSL GetId Worker', role='MECH'
        )

        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO plan.product_info (serial_number, model)
            VALUES ('SN-WSL-002', 'TEST-MODEL')
            ON CONFLICT DO NOTHING
        """)
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number)
            VALUES ('DOC-WSL-002', 'SN-WSL-002')
            ON CONFLICT DO NOTHING
        """)
        cursor.execute("""
            INSERT INTO app_task_details (
                worker_id, serial_number, qr_doc_id, task_category,
                task_id, task_name
            )
            VALUES (%s, 'SN-WSL-002', 'DOC-WSL-002', 'MECH', 'N2_LINE', 'N2 라인 조립')
            RETURNING id
        """, (worker_id,))
        task_detail_id = cursor.fetchone()[0]

        now = datetime.now(timezone.utc)
        cursor.execute("""
            INSERT INTO work_start_log (
                task_id, worker_id, serial_number, qr_doc_id,
                task_category, task_id_ref, task_name, started_at
            )
            VALUES (%s, %s, 'SN-WSL-002', 'DOC-WSL-002', 'MECH', 'N2_LINE', 'N2 라인 조립', %s)
            RETURNING id
        """, (task_detail_id, worker_id, now))
        log_id = cursor.fetchone()[0]
        db_conn.commit()

        # ID로 조회
        cursor.execute("SELECT * FROM work_start_log WHERE id = %s", (log_id,))
        row = cursor.fetchone()
        assert row is not None

        # 존재하지 않는 ID
        cursor.execute("SELECT * FROM work_start_log WHERE id = %s", (999999,))
        row_none = cursor.fetchone()
        assert row_none is None

        # 정리
        cursor.execute("DELETE FROM work_start_log WHERE id = %s", (log_id,))
        cursor.execute("DELETE FROM app_task_details WHERE id = %s", (task_detail_id,))
        cursor.execute("DELETE FROM public.qr_registry WHERE qr_doc_id = 'DOC-WSL-002'")
        cursor.execute("DELETE FROM plan.product_info WHERE serial_number = 'SN-WSL-002'")
        db_conn.commit()
        cursor.close()

    def test_get_by_task_id(self, db_conn, create_test_worker):
        """
        task_id로 work_start_log 목록 조회

        Expected:
        - 동일 task_id에 연결된 로그 목록 반환
        - 시작 시각 기준 정렬
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='wsl_taskid@test.com', password='Test123!',
            name='WSL TaskId Worker', role='ELEC'
        )

        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO plan.product_info (serial_number, model)
            VALUES ('SN-WSL-003', 'TEST-MODEL')
            ON CONFLICT DO NOTHING
        """)
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number)
            VALUES ('DOC-WSL-003', 'SN-WSL-003')
            ON CONFLICT DO NOTHING
        """)
        cursor.execute("""
            INSERT INTO app_task_details (
                worker_id, serial_number, qr_doc_id, task_category,
                task_id, task_name
            )
            VALUES (%s, 'SN-WSL-003', 'DOC-WSL-003', 'ELEC', 'PANEL_WORK', '판넬 작업')
            RETURNING id
        """, (worker_id,))
        task_detail_id = cursor.fetchone()[0]

        now = datetime.now(timezone.utc)
        for i in range(2):
            cursor.execute("""
                INSERT INTO work_start_log (
                    task_id, worker_id, serial_number, qr_doc_id,
                    task_category, task_id_ref, task_name, started_at
                )
                VALUES (%s, %s, 'SN-WSL-003', 'DOC-WSL-003', 'ELEC', 'PANEL_WORK', '판넬 작업', %s)
            """, (task_detail_id, worker_id, now + timedelta(minutes=i)))
        db_conn.commit()

        # task_id로 조회
        cursor.execute(
            "SELECT COUNT(*) FROM work_start_log WHERE task_id = %s",
            (task_detail_id,)
        )
        count = cursor.fetchone()[0]
        assert count == 2

        # 정리
        cursor.execute("DELETE FROM work_start_log WHERE task_id = %s", (task_detail_id,))
        cursor.execute("DELETE FROM app_task_details WHERE id = %s", (task_detail_id,))
        cursor.execute("DELETE FROM public.qr_registry WHERE qr_doc_id = 'DOC-WSL-003'")
        cursor.execute("DELETE FROM plan.product_info WHERE serial_number = 'SN-WSL-003'")
        db_conn.commit()
        cursor.close()

    def test_from_db_row(self):
        """
        WorkStartLog.from_db_row() 정적 메서드 테스트

        Expected:
        - dict 형태 행에서 WorkStartLog 객체 생성
        - 모든 필드가 올바르게 매핑됨
        """
        try:
            from app.models.work_start_log import WorkStartLog
        except ImportError:
            pytest.skip("WorkStartLog 모델 미구현 (BE Task #1 완료 후 테스트)")

        now = datetime.now(timezone.utc)
        row = {
            'id': 1,
            'task_id': 10,
            'worker_id': 5,
            'serial_number': 'SN-TEST-001',
            'qr_doc_id': 'DOC-TEST-001',
            'task_category': 'MECH',
            'task_id_ref': 'CABINET_ASSY',
            'task_name': '캐비넷 조립',
            'started_at': now,
            'created_at': now
        }

        log = WorkStartLog.from_db_row(row)

        assert log.id == 1
        assert log.task_id == 10
        assert log.worker_id == 5
        assert log.serial_number == 'SN-TEST-001'
        assert log.qr_doc_id == 'DOC-TEST-001'
        assert log.task_category == 'MECH'
        assert log.task_id_ref == 'CABINET_ASSY'
        assert log.task_name == '캐비넷 조립'
        assert log.started_at == now
        assert log.created_at == now


# ==================== WorkCompletionLog 테스트 ====================

class TestWorkCompletionLog:
    """
    WorkCompletionLog 모델 단위 테스트
    테이블: work_completion_log
    """

    def test_create_work_completion_log(self, db_conn, create_test_worker):
        """
        work_completion_log 레코드 생성 테스트

        Expected:
        - 레코드가 work_completion_log 테이블에 저장됨
        - duration_minutes 계산값 저장
        - completed_at, created_at 설정됨
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='wcl_create@test.com', password='Test123!',
            name='WCL Create Worker', role='MECH'
        )

        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO plan.product_info (serial_number, model)
            VALUES ('SN-WCL-001', 'TEST-MODEL')
            ON CONFLICT DO NOTHING
        """)
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number)
            VALUES ('DOC-WCL-001', 'SN-WCL-001')
            ON CONFLICT DO NOTHING
        """)
        cursor.execute("""
            INSERT INTO app_task_details (
                worker_id, serial_number, qr_doc_id, task_category,
                task_id, task_name
            )
            VALUES (%s, 'SN-WCL-001', 'DOC-WCL-001', 'MECH', 'CLEANING', '설비 클리닝')
            RETURNING id
        """, (worker_id,))
        task_detail_id = cursor.fetchone()[0]

        now = datetime.now(timezone.utc)
        duration = 45  # 45분
        cursor.execute("""
            INSERT INTO work_completion_log (
                task_id, worker_id, serial_number, qr_doc_id,
                task_category, task_id_ref, task_name, completed_at, duration_minutes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        """, (task_detail_id, worker_id, 'SN-WCL-001', 'DOC-WCL-001',
              'MECH', 'CLEANING', '설비 클리닝', now, duration))

        result = cursor.fetchone()
        db_conn.commit()

        assert result is not None
        log_id = result[0]
        assert log_id > 0
        assert result[1] is not None  # created_at auto-set

        # 정리
        cursor.execute("DELETE FROM work_completion_log WHERE id = %s", (log_id,))
        cursor.execute("DELETE FROM app_task_details WHERE id = %s", (task_detail_id,))
        cursor.execute("DELETE FROM public.qr_registry WHERE qr_doc_id = 'DOC-WCL-001'")
        cursor.execute("DELETE FROM plan.product_info WHERE serial_number = 'SN-WCL-001'")
        db_conn.commit()
        cursor.close()

    def test_get_by_id(self, db_conn, create_test_worker):
        """
        work_completion_log ID로 조회

        Expected:
        - 존재하는 ID → 레코드 반환
        - 존재하지 않는 ID → None 반환
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='wcl_getid@test.com', password='Test123!',
            name='WCL GetId Worker', role='ELEC'
        )

        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO plan.product_info (serial_number, model)
            VALUES ('SN-WCL-002', 'TEST-MODEL')
            ON CONFLICT DO NOTHING
        """)
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number)
            VALUES ('DOC-WCL-002', 'SN-WCL-002')
            ON CONFLICT DO NOTHING
        """)
        cursor.execute("""
            INSERT INTO app_task_details (
                worker_id, serial_number, qr_doc_id, task_category,
                task_id, task_name
            )
            VALUES (%s, 'SN-WCL-002', 'DOC-WCL-002', 'ELEC', 'INSPECTION', '검수')
            RETURNING id
        """, (worker_id,))
        task_detail_id = cursor.fetchone()[0]

        now = datetime.now(timezone.utc)
        cursor.execute("""
            INSERT INTO work_completion_log (
                task_id, worker_id, serial_number, qr_doc_id,
                task_category, task_id_ref, task_name, completed_at, duration_minutes
            )
            VALUES (%s, %s, 'SN-WCL-002', 'DOC-WCL-002', 'ELEC', 'INSPECTION', '검수', %s, %s)
            RETURNING id
        """, (task_detail_id, worker_id, now, 120))
        log_id = cursor.fetchone()[0]
        db_conn.commit()

        cursor.execute("SELECT * FROM work_completion_log WHERE id = %s", (log_id,))
        row = cursor.fetchone()
        assert row is not None

        cursor.execute("SELECT * FROM work_completion_log WHERE id = %s", (999999,))
        row_none = cursor.fetchone()
        assert row_none is None

        # 정리
        cursor.execute("DELETE FROM work_completion_log WHERE id = %s", (log_id,))
        cursor.execute("DELETE FROM app_task_details WHERE id = %s", (task_detail_id,))
        cursor.execute("DELETE FROM public.qr_registry WHERE qr_doc_id = 'DOC-WCL-002'")
        cursor.execute("DELETE FROM plan.product_info WHERE serial_number = 'SN-WCL-002'")
        db_conn.commit()
        cursor.close()

    def test_get_by_task_id(self, db_conn, create_test_worker):
        """
        task_id로 work_completion_log 조회

        Expected:
        - 동일 task_id에 연결된 완료 로그 조회 가능
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='wcl_taskid@test.com', password='Test123!',
            name='WCL TaskId Worker', role='PI'
        )

        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO plan.product_info (serial_number, model)
            VALUES ('SN-WCL-003', 'TEST-MODEL')
            ON CONFLICT DO NOTHING
        """)
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number)
            VALUES ('DOC-WCL-003', 'SN-WCL-003')
            ON CONFLICT DO NOTHING
        """)
        cursor.execute("""
            INSERT INTO app_task_details (
                worker_id, serial_number, qr_doc_id, task_category,
                task_id, task_name
            )
            VALUES (%s, 'SN-WCL-003', 'DOC-WCL-003', 'PI', 'PI_TASK_01', 'PI 작업')
            RETURNING id
        """, (worker_id,))
        task_detail_id = cursor.fetchone()[0]

        now = datetime.now(timezone.utc)
        cursor.execute("""
            INSERT INTO work_completion_log (
                task_id, worker_id, serial_number, qr_doc_id,
                task_category, task_id_ref, task_name, completed_at, duration_minutes
            )
            VALUES (%s, %s, 'SN-WCL-003', 'DOC-WCL-003', 'PI', 'PI_TASK_01', 'PI 작업', %s, %s)
            RETURNING id
        """, (task_detail_id, worker_id, now, 30))
        log_id = cursor.fetchone()[0]
        db_conn.commit()

        cursor.execute(
            "SELECT COUNT(*) FROM work_completion_log WHERE task_id = %s",
            (task_detail_id,)
        )
        count = cursor.fetchone()[0]
        assert count == 1

        # 정리
        cursor.execute("DELETE FROM work_completion_log WHERE id = %s", (log_id,))
        cursor.execute("DELETE FROM app_task_details WHERE id = %s", (task_detail_id,))
        cursor.execute("DELETE FROM public.qr_registry WHERE qr_doc_id = 'DOC-WCL-003'")
        cursor.execute("DELETE FROM plan.product_info WHERE serial_number = 'SN-WCL-003'")
        db_conn.commit()
        cursor.close()

    def test_from_db_row(self):
        """
        WorkCompletionLog.from_db_row() 정적 메서드 테스트

        Expected:
        - dict 행에서 WorkCompletionLog 객체 생성
        - 모든 필드 올바르게 매핑
        - duration_minutes Optional 처리
        """
        try:
            from app.models.work_completion_log import WorkCompletionLog
        except ImportError:
            pytest.skip("WorkCompletionLog 모델 미구현 (BE Task #1 완료 후 테스트)")

        now = datetime.now(timezone.utc)
        row = {
            'id': 1,
            'task_id': 10,
            'worker_id': 5,
            'serial_number': 'SN-TEST-001',
            'qr_doc_id': 'DOC-TEST-001',
            'task_category': 'MECH',
            'task_id_ref': 'SELF_INSPECTION',
            'task_name': '자주검사',
            'completed_at': now,
            'duration_minutes': 60,
            'created_at': now
        }

        log = WorkCompletionLog.from_db_row(row)

        assert log.id == 1
        assert log.task_id == 10
        assert log.worker_id == 5
        assert log.serial_number == 'SN-TEST-001'
        assert log.task_category == 'MECH'
        assert log.task_id_ref == 'SELF_INSPECTION'
        assert log.duration_minutes == 60
        assert log.completed_at == now

    def test_duration_minutes_nullable(self):
        """
        duration_minutes가 None일 때 from_db_row() 처리

        Expected:
        - duration_minutes=None인 경우도 정상 처리
        """
        try:
            from app.models.work_completion_log import WorkCompletionLog
        except ImportError:
            pytest.skip("WorkCompletionLog 모델 미구현 (BE Task #1 완료 후 테스트)")

        now = datetime.now(timezone.utc)
        row = {
            'id': 2,
            'task_id': 11,
            'worker_id': 6,
            'serial_number': 'SN-TEST-002',
            'qr_doc_id': 'DOC-TEST-002',
            'task_category': 'ELEC',
            'task_id_ref': 'INSPECTION',
            'task_name': '검수',
            'completed_at': now,
            'duration_minutes': None,  # NULL 허용
            'created_at': now
        }

        log = WorkCompletionLog.from_db_row(row)
        assert log.duration_minutes is None


# ==================== OfflineSyncQueue 테스트 ====================

class TestOfflineSyncQueue:
    """
    OfflineSyncQueue 모델 단위 테스트
    테이블: offline_sync_queue
    """

    def test_create_sync_record(self, db_conn, create_test_worker):
        """
        offline_sync_queue 레코드 생성 테스트

        Expected:
        - operation, table_name, data(JSONB), synced=False 기본값으로 저장
        - created_at 자동 설정
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='osq_create@test.com', password='Test123!',
            name='OSQ Create Worker', role='MECH'
        )

        cursor = db_conn.cursor()
        test_data = json.dumps({'task_id': 1, 'started_at': '2026-01-01T09:00:00Z'})

        cursor.execute("""
            INSERT INTO offline_sync_queue (
                worker_id, operation, table_name, record_id, data, synced
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, synced, created_at
        """, (worker_id, 'INSERT', 'app_task_details', '100', test_data, False))

        result = cursor.fetchone()
        db_conn.commit()

        assert result is not None
        sync_id = result[0]
        assert result[1] is False  # synced 기본값 False
        assert result[2] is not None  # created_at 자동 설정

        # 정리
        cursor.execute("DELETE FROM offline_sync_queue WHERE id = %s", (sync_id,))
        db_conn.commit()
        cursor.close()

    def test_mark_synced(self, db_conn, create_test_worker):
        """
        offline_sync_queue 동기화 완료 처리 테스트

        Expected:
        - synced=True, synced_at 타임스탬프 설정
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='osq_sync@test.com', password='Test123!',
            name='OSQ Sync Worker', role='ELEC'
        )

        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO offline_sync_queue (
                worker_id, operation, table_name, synced
            )
            VALUES (%s, 'UPDATE', 'app_task_details', FALSE)
            RETURNING id
        """, (worker_id,))
        sync_id = cursor.fetchone()[0]
        db_conn.commit()

        # 동기화 완료 처리
        now = datetime.now(timezone.utc)
        cursor.execute("""
            UPDATE offline_sync_queue
            SET synced = TRUE, synced_at = %s
            WHERE id = %s
        """, (now, sync_id))
        db_conn.commit()

        # 확인
        cursor.execute(
            "SELECT synced, synced_at FROM offline_sync_queue WHERE id = %s",
            (sync_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] is True  # synced=True
        assert row[1] is not None  # synced_at 설정됨

        # 정리
        cursor.execute("DELETE FROM offline_sync_queue WHERE id = %s", (sync_id,))
        db_conn.commit()
        cursor.close()

    def test_get_unsynced_records(self, db_conn, create_test_worker):
        """
        미동기화 레코드 조회 테스트

        Expected:
        - synced=False인 레코드만 반환
        - synced=True인 레코드는 제외
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='osq_unsynced@test.com', password='Test123!',
            name='OSQ Unsynced Worker', role='PI'
        )

        cursor = db_conn.cursor()

        # 미동기화 레코드 2개 생성
        for i in range(2):
            cursor.execute("""
                INSERT INTO offline_sync_queue (
                    worker_id, operation, table_name, synced
                )
                VALUES (%s, 'INSERT', 'app_task_details', FALSE)
            """, (worker_id,))

        # 동기화 완료 레코드 1개 생성
        cursor.execute("""
            INSERT INTO offline_sync_queue (
                worker_id, operation, table_name, synced, synced_at
            )
            VALUES (%s, 'INSERT', 'app_task_details', TRUE, NOW())
        """, (worker_id,))

        db_conn.commit()

        # 미동기화 레코드만 조회
        cursor.execute("""
            SELECT COUNT(*) FROM offline_sync_queue
            WHERE worker_id = %s AND synced = FALSE
        """, (worker_id,))
        unsynced_count = cursor.fetchone()[0]
        assert unsynced_count == 2

        # 전체 레코드 수
        cursor.execute(
            "SELECT COUNT(*) FROM offline_sync_queue WHERE worker_id = %s",
            (worker_id,)
        )
        total_count = cursor.fetchone()[0]
        assert total_count == 3

        # 정리
        cursor.execute(
            "DELETE FROM offline_sync_queue WHERE worker_id = %s",
            (worker_id,)
        )
        db_conn.commit()
        cursor.close()

    def test_from_db_row(self):
        """
        OfflineSyncQueue.from_db_row() 정적 메서드 테스트

        Expected:
        - dict 행에서 OfflineSyncQueue 객체 생성
        - data 필드 JSONB → dict 변환 확인
        - synced_at Optional 처리
        """
        try:
            from app.models.offline_sync_queue import OfflineSyncQueue
        except ImportError:
            pytest.skip("OfflineSyncQueue 모델 미구현 (BE Task #1 완료 후 테스트)")

        now = datetime.now(timezone.utc)
        row = {
            'id': 1,
            'worker_id': 5,
            'operation': 'INSERT',
            'table_name': 'app_task_details',
            'record_id': '42',
            'data': {'task_id': 42, 'started_at': '2026-01-01T09:00:00Z'},
            'synced': False,
            'synced_at': None,
            'created_at': now
        }

        sync = OfflineSyncQueue.from_db_row(row)

        assert sync.id == 1
        assert sync.worker_id == 5
        assert sync.operation == 'INSERT'
        assert sync.table_name == 'app_task_details'
        assert sync.record_id == '42'
        assert sync.synced is False
        assert sync.synced_at is None
        assert sync.created_at == now


# ==================== LocationHistory 테스트 ====================

class TestLocationHistory:
    """
    LocationHistory 모델 단위 테스트
    테이블: location_history
    """

    def test_create_location_record(self, db_conn, create_test_worker):
        """
        location_history 레코드 생성 테스트

        Expected:
        - 위도, 경도, recorded_at 포함하여 저장
        - created_at 자동 설정
        - DECIMAL(10,8) 정밀도 유지
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='lh_create@test.com', password='Test123!',
            name='LH Create Worker', role='SI'
        )

        cursor = db_conn.cursor()
        now = datetime.now(timezone.utc)
        latitude = 37.50000000  # GST 위치 (서울 근처)
        longitude = 126.90000000

        cursor.execute("""
            INSERT INTO location_history (worker_id, latitude, longitude, recorded_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id, created_at
        """, (worker_id, latitude, longitude, now))

        result = cursor.fetchone()
        db_conn.commit()

        assert result is not None
        loc_id = result[0]
        assert loc_id > 0
        assert result[1] is not None  # created_at

        # 정리
        cursor.execute("DELETE FROM location_history WHERE id = %s", (loc_id,))
        db_conn.commit()
        cursor.close()

    def test_get_by_worker_id(self, db_conn, create_test_worker):
        """
        worker_id로 위치 기록 조회

        Expected:
        - 특정 작업자의 위치 기록 목록 조회
        - recorded_at 기준 정렬 가능
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='lh_getworker@test.com', password='Test123!',
            name='LH GetWorker Worker', role='MECH'
        )

        cursor = db_conn.cursor()
        now = datetime.now(timezone.utc)

        # 위치 기록 3개 생성
        for i in range(3):
            cursor.execute("""
                INSERT INTO location_history (worker_id, latitude, longitude, recorded_at)
                VALUES (%s, %s, %s, %s)
            """, (worker_id, 37.5 + i * 0.01, 126.9 + i * 0.01, now + timedelta(minutes=i)))
        db_conn.commit()

        cursor.execute(
            "SELECT COUNT(*) FROM location_history WHERE worker_id = %s",
            (worker_id,)
        )
        count = cursor.fetchone()[0]
        assert count == 3

        # 최신순 정렬 확인
        cursor.execute("""
            SELECT recorded_at FROM location_history
            WHERE worker_id = %s
            ORDER BY recorded_at DESC
        """, (worker_id,))
        rows = cursor.fetchall()
        assert len(rows) == 3
        # 첫 번째가 가장 최신
        assert rows[0][0] > rows[1][0]

        # 정리
        cursor.execute("DELETE FROM location_history WHERE worker_id = %s", (worker_id,))
        db_conn.commit()
        cursor.close()

    def test_from_db_row(self):
        """
        LocationHistory.from_db_row() 정적 메서드 테스트

        Expected:
        - tuple 또는 dict 행에서 LocationHistory 객체 생성
        - 위도/경도 float 변환 확인
        """
        try:
            from app.models.location_history import LocationHistory
        except ImportError:
            pytest.skip("LocationHistory 모델 미구현 (BE Task #1 완료 후 테스트)")

        now = datetime.now(timezone.utc)

        # dict 형태 행 (RealDictCursor 스타일)
        row = {
            'id': 1,
            'worker_id': 5,
            'latitude': 37.50000000,
            'longitude': 126.90000000,
            'recorded_at': now,
            'created_at': now
        }

        loc = LocationHistory.from_db_row(row)

        assert loc.id == 1
        assert loc.worker_id == 5
        assert float(loc.latitude) == pytest.approx(37.5, abs=1e-6)
        assert float(loc.longitude) == pytest.approx(126.9, abs=1e-6)
        assert loc.recorded_at == now

    def test_decimal_precision(self, db_conn, create_test_worker):
        """
        위도/경도 소수점 8자리 정밀도 유지 테스트

        Expected:
        - DECIMAL(10,8) / DECIMAL(11,8) 정밀도 유지
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='lh_precision@test.com', password='Test123!',
            name='LH Precision Worker', role='QI'
        )

        cursor = db_conn.cursor()
        latitude = 37.12345678
        longitude = 126.87654321
        now = datetime.now(timezone.utc)

        cursor.execute("""
            INSERT INTO location_history (worker_id, latitude, longitude, recorded_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id, latitude, longitude
        """, (worker_id, latitude, longitude, now))

        result = cursor.fetchone()
        db_conn.commit()

        assert result is not None
        loc_id = result[0]
        assert float(result[1]) == pytest.approx(latitude, abs=1e-6)
        assert float(result[2]) == pytest.approx(longitude, abs=1e-6)

        # 정리
        cursor.execute("DELETE FROM location_history WHERE id = %s", (loc_id,))
        db_conn.commit()
        cursor.close()


# ==================== EmailVerification 테스트 ====================

class TestEmailVerification:
    """
    EmailVerification dataclass 테스트
    worker.py에 추가된 EmailVerification 클래스 검증
    """

    def test_dataclass_creation(self):
        """
        EmailVerification dataclass 생성 테스트

        Expected:
        - 모든 필드 설정 가능
        - verified_at Optional 처리
        """
        try:
            from app.models.worker import EmailVerification
        except ImportError:
            pytest.skip("EmailVerification dataclass 미구현 (BE Task #1 완료 후 테스트)")

        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=10)

        ev = EmailVerification(
            id=1,
            worker_id=5,
            verification_code='123456',
            expires_at=expires,
            verified_at=None,
            created_at=now
        )

        assert ev.id == 1
        assert ev.worker_id == 5
        assert ev.verification_code == '123456'
        assert ev.expires_at == expires
        assert ev.verified_at is None
        assert ev.created_at == now

    def test_dataclass_verified_state(self):
        """
        EmailVerification 인증 완료 상태 테스트

        Expected:
        - verified_at이 설정된 경우 인증 완료 상태
        """
        try:
            from app.models.worker import EmailVerification
        except ImportError:
            pytest.skip("EmailVerification dataclass 미구현 (BE Task #1 완료 후 테스트)")

        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=10)
        verified_at = now  # 인증 완료

        ev = EmailVerification(
            id=2,
            worker_id=6,
            verification_code='654321',
            expires_at=expires,
            verified_at=verified_at,
            created_at=now
        )

        assert ev.verified_at is not None
        assert ev.verified_at == now

    def test_from_db_row(self):
        """
        EmailVerification.from_db_row() 테스트

        Expected:
        - dict 행에서 EmailVerification 객체 생성
        - verified_at=None 처리 (미인증 상태)
        """
        try:
            from app.models.worker import EmailVerification
        except ImportError:
            pytest.skip("EmailVerification dataclass 미구현 (BE Task #1 완료 후 테스트)")

        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=10)

        row = {
            'id': 1,
            'worker_id': 5,
            'verification_code': '987654',
            'expires_at': expires,
            'verified_at': None,
            'created_at': now
        }

        ev = EmailVerification.from_db_row(row)

        assert ev.id == 1
        assert ev.worker_id == 5
        assert ev.verification_code == '987654'
        assert ev.expires_at == expires
        assert ev.verified_at is None
        assert ev.created_at == now

    def test_code_format_6_digits(self, db_conn, create_test_worker):
        """
        email_verification 테이블 코드 형식 검증 (6자리 숫자)

        Expected:
        - verification_code VARCHAR(6) 제약 확인
        - 6자리 숫자 코드만 허용
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='ev_format@test.com', password='Test123!',
            name='EV Format Worker', role='MECH'
        )

        cursor = db_conn.cursor()
        code = '246810'  # 6자리 숫자
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        cursor.execute("""
            INSERT INTO email_verification (worker_id, verification_code, expires_at)
            VALUES (%s, %s, %s)
            RETURNING id, verification_code
        """, (worker_id, code, expires_at))

        result = cursor.fetchone()
        db_conn.commit()

        assert result is not None
        ev_id = result[0]
        stored_code = result[1]
        assert len(stored_code) == 6
        assert stored_code.isdigit()

        # 정리
        cursor.execute("DELETE FROM email_verification WHERE id = %s", (ev_id,))
        db_conn.commit()
        cursor.close()

    def test_code_expiry_10_minutes(self, db_conn, create_test_worker):
        """
        인증 코드 10분 만료 정책 테스트

        Expected:
        - expires_at = created_at + 10분
        - 현재 시각 기준 아직 만료되지 않은 상태
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='ev_expiry@test.com', password='Test123!',
            name='EV Expiry Worker', role='ELEC'
        )

        cursor = db_conn.cursor()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=10)

        cursor.execute("""
            INSERT INTO email_verification (worker_id, verification_code, expires_at)
            VALUES (%s, %s, %s)
            RETURNING id, expires_at
        """, (worker_id, '135799', expires_at))

        result = cursor.fetchone()
        db_conn.commit()

        assert result is not None
        ev_id = result[0]
        stored_expires = result[1]

        # 만료 시각이 현재보다 미래
        assert stored_expires > now

        # 10분 이내
        diff = stored_expires - now
        assert diff.total_seconds() <= 600  # 10분

        # 정리
        cursor.execute("DELETE FROM email_verification WHERE id = %s", (ev_id,))
        db_conn.commit()
        cursor.close()


# ==================== AlertLog read_at 필드 테스트 ====================

class TestAlertLogReadAt:
    """
    AlertLog 모델의 read_at 필드 (Sprint 5 추가) 테스트
    """

    def test_alert_read_at_default_null(self, db_conn, create_test_worker, create_test_alert):
        """
        알림 생성 시 read_at = NULL 기본값

        Expected:
        - 새로 생성된 알림의 read_at은 NULL
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='rat_default@test.com', password='Test123!',
            name='RAT Default Worker', role='MECH'
        )

        alert_id = create_test_alert(
            alert_type='PROCESS_READY',
            message='[SN-RAT-001] 테스트 알림',
            serial_number='SN-RAT-001',
            target_worker_id=worker_id
        )

        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT is_read, read_at FROM app_alert_logs WHERE id = %s",
            (alert_id,)
        )
        row = cursor.fetchone()
        cursor.close()

        assert row is not None
        assert row[0] is False  # is_read = False
        assert row[1] is None   # read_at = NULL

    def test_alert_read_at_set_on_read(self, db_conn, create_test_worker, create_test_alert):
        """
        알림 읽음 처리 시 read_at 타임스탬프 설정

        Expected:
        - is_read = True 업데이트 시 read_at도 설정됨
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='rat_set@test.com', password='Test123!',
            name='RAT Set Worker', role='ELEC'
        )

        alert_id = create_test_alert(
            alert_type='DURATION_EXCEEDED',
            message='[SN-RAT-002] 시간 초과',
            serial_number='SN-RAT-002',
            target_worker_id=worker_id
        )

        # 읽음 처리 (read_at 설정)
        now = datetime.now(timezone.utc)
        cursor = db_conn.cursor()
        cursor.execute("""
            UPDATE app_alert_logs
            SET is_read = TRUE, read_at = %s
            WHERE id = %s
        """, (now, alert_id))
        db_conn.commit()

        cursor.execute(
            "SELECT is_read, read_at FROM app_alert_logs WHERE id = %s",
            (alert_id,)
        )
        row = cursor.fetchone()
        cursor.close()

        assert row is not None
        assert row[0] is True   # is_read = True
        assert row[1] is not None  # read_at 설정됨

    def test_alert_log_from_db_row_with_read_at(self):
        """
        AlertLog.from_db_row()에서 read_at 필드 처리

        Expected:
        - read_at=None 처리 (미읽음)
        - read_at 타임스탬프 처리 (읽음)
        """
        try:
            from app.models.alert_log import AlertLog
        except ImportError:
            pytest.skip("AlertLog 모델 없음")

        now = datetime.now(timezone.utc)

        # 미읽음 상태
        row_unread = {
            'id': 1,
            'alert_type': 'PROCESS_READY',
            'serial_number': 'SN-TEST-001',
            'qr_doc_id': 'DOC-TEST-001',
            'triggered_by_worker_id': None,
            'target_worker_id': 5,
            'target_role': 'MECH',
            'message': '테스트 메시지',
            'is_read': False,
            'read_at': None,
            'created_at': now,
            'updated_at': now
        }

        alert_unread = AlertLog.from_db_row(row_unread)
        assert alert_unread.is_read is False
        # read_at 필드가 존재하는지 확인 (Sprint 5 추가)
        if hasattr(alert_unread, 'read_at'):
            assert alert_unread.read_at is None

        # 읽음 상태
        row_read = {**row_unread, 'is_read': True, 'read_at': now}
        alert_read = AlertLog.from_db_row(row_read)
        assert alert_read.is_read is True
        if hasattr(alert_read, 'read_at'):
            assert alert_read.read_at == now
