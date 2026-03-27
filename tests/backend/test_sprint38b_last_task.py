"""
Sprint 38-B: S/N별 last_task_name / last_task_category 필드 추가
White-box 테스트 4건 (TC-LT-01 ~ TC-LT-04)

get_partner_sn_progress() 서비스 함수를 직접 호출하여
last_task_name / last_task_category 반환 로직을 검증한다.

DB 연결 구조:
  - 테스트 데이터 INSERT: db_conn (autocommit=False) → 반드시 COMMIT
  - 서비스 함수 호출: 내부적으로 get_db_connection() 별도 연결 사용
"""

import sys
from pathlib import Path

_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest
from datetime import datetime, timedelta, timezone

_PREFIX = 'SP38B-'


# ── 공통 헬퍼 ──────────────────────────────────────────────────

def _insert_product(db_conn, serial_number, mech_partner='FNI', elec_partner='P&S'):
    """plan.product_info + qr_registry 삽입"""
    qr_doc_id = f'DOC_{serial_number}'
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO plan.product_info (serial_number, model, mech_partner, elec_partner, ship_plan_date)
        VALUES (%s, %s, %s, %s, '2099-12-31')
        ON CONFLICT (serial_number) DO NOTHING
    """, (serial_number, 'GALLANT-50', mech_partner, elec_partner))
    cursor.execute("""
        INSERT INTO qr_registry (qr_doc_id, serial_number, status)
        VALUES (%s, %s, 'active')
        ON CONFLICT (qr_doc_id) DO NOTHING
    """, (qr_doc_id, serial_number))
    cursor.execute("""
        INSERT INTO completion_status (serial_number)
        VALUES (%s)
        ON CONFLICT (serial_number) DO NOTHING
    """, (serial_number,))
    db_conn.commit()
    cursor.close()
    return qr_doc_id


def _insert_task_detail(db_conn, serial_number, qr_doc_id, worker_id,
                        category='MECH', task_id='SELF_INSPECTION', task_name='자주검사'):
    """app_task_details 레코드 삽입 → 반환: task_detail_id"""
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable)
        VALUES (%s, %s, %s, %s, %s, %s, true)
        ON CONFLICT (serial_number, qr_doc_id, task_category, task_id)
            DO UPDATE SET worker_id = EXCLUDED.worker_id
        RETURNING id
    """, (worker_id, serial_number, qr_doc_id, category, task_id, task_name))
    task_detail_id = cursor.fetchone()[0]
    db_conn.commit()
    cursor.close()
    return task_detail_id


def _insert_start_log(db_conn, task_detail_id, worker_id, serial_number, qr_doc_id,
                      started_at=None, category='MECH', task_id_ref='SELF_INSPECTION',
                      task_name='자주검사'):
    """work_start_log 삽입"""
    if started_at is None:
        started_at = datetime.now(timezone.utc) - timedelta(hours=1)
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO work_start_log
            (task_id, worker_id, serial_number, qr_doc_id, task_category,
             task_id_ref, task_name, started_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (task_detail_id, worker_id, serial_number, qr_doc_id,
          category, task_id_ref, task_name, started_at))
    db_conn.commit()
    cursor.close()


def _insert_completion_log(db_conn, task_detail_id, worker_id, serial_number, qr_doc_id,
                           completed_at=None, duration_minutes=60,
                           category='MECH', task_id_ref='SELF_INSPECTION',
                           task_name='자주검사'):
    """work_completion_log 삽입"""
    if completed_at is None:
        completed_at = datetime.now(timezone.utc)
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO work_completion_log
            (task_id, worker_id, serial_number, qr_doc_id, task_category,
             task_id_ref, task_name, completed_at, duration_minutes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (task_detail_id, worker_id, serial_number, qr_doc_id,
          category, task_id_ref, task_name, completed_at, duration_minutes))
    db_conn.commit()
    cursor.close()


def _cleanup(db_conn, prefix=_PREFIX):
    """테스트 데이터 정리"""
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM work_start_log WHERE serial_number LIKE %s", (f'{prefix}%',))
    cursor.execute("DELETE FROM work_completion_log WHERE serial_number LIKE %s", (f'{prefix}%',))
    cursor.execute("DELETE FROM app_task_details WHERE serial_number LIKE %s", (f'{prefix}%',))
    cursor.execute("DELETE FROM completion_status WHERE serial_number LIKE %s", (f'{prefix}%',))
    cursor.execute("DELETE FROM qr_registry WHERE serial_number LIKE %s", (f'{prefix}%',))
    cursor.execute("DELETE FROM plan.product_info WHERE serial_number LIKE %s", (f'{prefix}%',))
    db_conn.commit()
    cursor.close()


def _get_product(result, serial_number):
    """products 배열에서 해당 S/N 찾기"""
    for p in result['products']:
        if p['serial_number'] == serial_number:
            return p
    return None


# ── 테스트 클래스 ──────────────────────────────────────────────

class TestLastTask:
    """TC-LT-01 ~ TC-LT-04: last_task_name / last_task_category 반환 검증"""

    def test_tc_lt_01_start_log_only_returns_start_task_fields(
        self, db_conn, seed_test_data, create_test_worker
    ):
        """TC-LT-01: start 로그만 있는 S/N → last_task_name, last_task_category가 해당 start 로그의 값과 일치"""
        from app.services.progress_service import get_partner_sn_progress

        _cleanup(db_conn)
        sn = f'{_PREFIX}LT01-001'
        qr = _insert_product(db_conn, sn)

        worker_id = create_test_worker(
            email='sp38b_lt01@test.axisos.com',
            password='Test123!', name='LT01 Worker',
            role='MECH', company='FNI'
        )
        task_id = _insert_task_detail(
            db_conn, sn, qr, worker_id,
            category='MECH', task_id='SELF_INSPECTION', task_name='자주검사'
        )
        _insert_start_log(
            db_conn, task_id, worker_id, sn, qr,
            category='MECH', task_id_ref='SELF_INSPECTION', task_name='자주검사'
        )
        # work_completion_log 없음 → start 로그가 last_activity

        result = get_partner_sn_progress(
            worker_company='GST', worker_role='ADMIN', is_admin=True
        )
        product = _get_product(result, sn)

        assert product is not None, f"S/N {sn} not found in result"
        assert product['last_task_name'] == '자주검사', (
            f"Expected '자주검사', got {product['last_task_name']}"
        )
        assert product['last_task_category'] == 'MECH', (
            f"Expected 'MECH', got {product['last_task_category']}"
        )

        _cleanup(db_conn)

    def test_tc_lt_02_completion_log_more_recent_returns_completion_task(
        self, db_conn, seed_test_data, create_test_worker
    ):
        """TC-LT-02: start + completion 로그 (completion이 최신) → 최신 로그(completion)의 task_name, task_category 반환"""
        from app.services.progress_service import get_partner_sn_progress

        _cleanup(db_conn)
        sn = f'{_PREFIX}LT02-001'
        qr = _insert_product(db_conn, sn)

        worker_id = create_test_worker(
            email='sp38b_lt02@test.axisos.com',
            password='Test123!', name='LT02 Worker',
            role='ELEC', company='P&S'
        )

        # start 로그: MECH/자주검사 (오래됨)
        task_mech = _insert_task_detail(
            db_conn, sn, qr, worker_id,
            category='MECH', task_id='SELF_INSPECTION', task_name='자주검사'
        )
        old_time = datetime.now(timezone.utc) - timedelta(hours=3)
        _insert_start_log(
            db_conn, task_mech, worker_id, sn, qr,
            started_at=old_time,
            category='MECH', task_id_ref='SELF_INSPECTION', task_name='자주검사'
        )

        # completion 로그: ELEC/판넬 작업 (최신)
        task_elec = _insert_task_detail(
            db_conn, sn, qr, worker_id,
            category='ELEC', task_id='PANEL_WORK', task_name='판넬 작업'
        )
        recent_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        _insert_completion_log(
            db_conn, task_elec, worker_id, sn, qr,
            completed_at=recent_time,
            category='ELEC', task_id_ref='PANEL_WORK', task_name='판넬 작업'
        )

        result = get_partner_sn_progress(
            worker_company='GST', worker_role='ADMIN', is_admin=True
        )
        product = _get_product(result, sn)

        assert product is not None, f"S/N {sn} not found in result"
        # completion 로그가 더 최신 → ELEC/판넬 작업이 반환되어야 함
        assert product['last_task_name'] == '판넬 작업', (
            f"Expected '판넬 작업', got {product['last_task_name']}"
        )
        assert product['last_task_category'] == 'ELEC', (
            f"Expected 'ELEC', got {product['last_task_category']}"
        )

        _cleanup(db_conn)

    def test_tc_lt_03_multiple_logs_returns_most_recent_only(
        self, db_conn, seed_test_data, create_test_worker
    ):
        """TC-LT-03: 여러 태깅 이력 → 가장 최근 것만 반환 (DISTINCT ON + DESC)"""
        from app.services.progress_service import get_partner_sn_progress

        _cleanup(db_conn)
        sn = f'{_PREFIX}LT03-001'
        qr = _insert_product(db_conn, sn)

        worker_id = create_test_worker(
            email='sp38b_lt03@test.axisos.com',
            password='Test123!', name='LT03 Worker',
            role='MECH', company='FNI'
        )

        base_time = datetime.now(timezone.utc)

        # 로그 1 (가장 오래됨): MECH/자주검사 start
        task1 = _insert_task_detail(
            db_conn, sn, qr, worker_id,
            category='MECH', task_id='SELF_INSPECTION', task_name='자주검사'
        )
        _insert_start_log(
            db_conn, task1, worker_id, sn, qr,
            started_at=base_time - timedelta(hours=4),
            category='MECH', task_id_ref='SELF_INSPECTION', task_name='자주검사'
        )

        # 로그 2 (중간): ELEC/배선 포설 completion
        task2 = _insert_task_detail(
            db_conn, sn, qr, worker_id,
            category='ELEC', task_id='WIRING', task_name='배선 포설'
        )
        _insert_completion_log(
            db_conn, task2, worker_id, sn, qr,
            completed_at=base_time - timedelta(hours=2),
            category='ELEC', task_id_ref='WIRING', task_name='배선 포설'
        )

        # 로그 3 (가장 최근): TMS/Tank Module start
        task3 = _insert_task_detail(
            db_conn, sn, qr, worker_id,
            category='TMS', task_id='TANK_MODULE', task_name='Tank Module'
        )
        _insert_start_log(
            db_conn, task3, worker_id, sn, qr,
            started_at=base_time - timedelta(minutes=10),
            category='TMS', task_id_ref='TANK_MODULE', task_name='Tank Module'
        )

        result = get_partner_sn_progress(
            worker_company='GST', worker_role='ADMIN', is_admin=True
        )
        product = _get_product(result, sn)

        assert product is not None, f"S/N {sn} not found in result"
        # 가장 최근 로그: TMS/Tank Module
        assert product['last_task_name'] == 'Tank Module', (
            f"Expected 'Tank Module', got {product['last_task_name']}"
        )
        assert product['last_task_category'] == 'TMS', (
            f"Expected 'TMS', got {product['last_task_category']}"
        )

        _cleanup(db_conn)

    def test_tc_lt_04_no_log_returns_null_task_fields(
        self, db_conn, seed_test_data
    ):
        """TC-LT-04: 태깅 이력 없는 S/N → last_task_name, last_task_category 모두 None"""
        from app.services.progress_service import get_partner_sn_progress

        _cleanup(db_conn)
        sn = f'{_PREFIX}LT04-001'
        _insert_product(db_conn, sn)
        # 작업 로그 없이 제품만 등록

        result = get_partner_sn_progress(
            worker_company='GST', worker_role='ADMIN', is_admin=True
        )
        product = _get_product(result, sn)

        assert product is not None, f"S/N {sn} not found in result"
        assert product['last_task_name'] is None, (
            f"Expected None, got {product['last_task_name']}"
        )
        assert product['last_task_category'] is None, (
            f"Expected None, got {product['last_task_category']}"
        )

        _cleanup(db_conn)
