"""
Sprint 38: last_worker / last_activity_at 필드 추가
Regression 테스트 5건 (TC-LR-01 ~ TC-LR-05)

Sprint 38 변경(last_activity 필드 추가) 이후에도
progress_service의 기존 기능이 깨지지 않았는지 검증한다.
"""

import sys
from pathlib import Path

_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest
import time

_PREFIX = 'SP38-RG-'
_TS = lambda: str(int(time.time() * 1000))


# ── 공통 헬퍼 ────────────────────────────────────────────────────

def _insert_product(db_conn, serial_number,
                    mech_partner='FNI', elec_partner='P&S',
                    module_outsourcing='',
                    days_offset=0):
    """plan.product_info + qr_registry + completion_status 삽입"""
    from datetime import date, timedelta
    qr_doc_id = f'DOC_{serial_number}'
    ship_date = (date.today() + timedelta(days=days_offset)).isoformat()
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO plan.product_info
            (serial_number, model, mech_partner, elec_partner, module_outsourcing, ship_plan_date)
        VALUES (%s, 'GALLANT-50', %s, %s, %s, %s)
        ON CONFLICT (serial_number) DO NOTHING
    """, (serial_number, mech_partner, elec_partner, module_outsourcing, ship_date))
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


def _insert_task(db_conn, serial_number, qr_doc_id, worker_id,
                 category='MECH', task_id='SELF_INSPECTION', task_name='자주검사',
                 completed=False, is_applicable=True):
    """app_task_details 삽입"""
    cursor = db_conn.cursor()
    completed_clause = 'NOW()' if completed else 'NULL'
    cursor.execute(f"""
        INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
             is_applicable, completed_at, duration_minutes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, {completed_clause},
                {'60' if completed else 'NULL'})
        ON CONFLICT (serial_number, qr_doc_id, task_category, task_id) DO NOTHING
    """, (worker_id, serial_number, qr_doc_id, category, task_id, task_name, is_applicable))
    db_conn.commit()
    cursor.close()


def _mark_all_completed(db_conn, serial_number):
    """completion_status.all_completed = true 설정"""
    cursor = db_conn.cursor()
    cursor.execute("""
        UPDATE completion_status
        SET all_completed = true, all_completed_at = NOW()
        WHERE serial_number = %s
    """, (serial_number,))
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


# ── 테스트 클래스 ──────────────────────────────────────────────

class TestProgressRegression:
    """TC-LR-01 ~ TC-LR-05: 기존 progress 기능 regression 검증"""

    def test_tc_lr_01_build_company_filter_variants(self, db_conn, seed_test_data):
        """TC-LR-01: _build_company_filter() — admin/GST/협력사 필터 정상 동작"""
        from app.services.progress_service import _build_company_filter

        # admin + 회사 없음 → 전체 (빈 WHERE)
        clause, params = _build_company_filter(company=None, is_admin=True)
        assert clause == ''
        assert params == []

        # GST 사내직원 → 전체
        clause, params = _build_company_filter(company='GST', is_admin=False)
        assert clause == ''

        # FNI → mech_partner 필터
        clause, params = _build_company_filter(company='FNI', is_admin=False)
        assert 'mech_partner' in clause
        assert 'FNI' in params

        # BAT → mech_partner 필터
        clause, params = _build_company_filter(company='BAT', is_admin=False)
        assert 'mech_partner' in clause
        assert 'BAT' in params

        # TMS(M) → mech_partner OR module_outsourcing 복합 필터
        clause, params = _build_company_filter(company='TMS(M)', is_admin=False)
        assert 'TMS' in clause

        # TMS(E) → elec_partner 필터
        clause, params = _build_company_filter(company='TMS(E)', is_admin=False)
        assert 'elec_partner' in clause

        # P&S → elec_partner 필터
        clause, params = _build_company_filter(company='P&S', is_admin=False)
        assert 'elec_partner' in clause
        assert 'P&S' in params

        # 알 수 없는 회사 → 빈 결과 필터
        clause, params = _build_company_filter(company='UNKNOWN_CO', is_admin=False)
        assert '1=0' in clause

        # company=None, is_admin=False → 빈 결과
        clause, params = _build_company_filter(company=None, is_admin=False)
        assert '1=0' in clause

    def test_tc_lr_02_completed_within_days_filter(
        self, db_conn, seed_test_data, create_test_worker
    ):
        """TC-LR-02: completion_status 완료 후 N일 필터 정상 동작"""
        from app.services.progress_service import get_partner_sn_progress

        _cleanup(db_conn)

        worker_id = create_test_worker(
            email='sp38_rg02@test.axisos.com',
            password='Test123!', name='RG02 Worker',
            role='MECH', company='FNI'
        )

        # 완료된 S/N (현재 시각 완료)
        sn_recent = f'{_PREFIX}RG02-RECENT'
        qr_recent = _insert_product(db_conn, sn_recent, days_offset=0)
        _insert_task(db_conn, sn_recent, qr_recent, worker_id, completed=True)
        _mark_all_completed(db_conn, sn_recent)

        # 진행 중 S/N
        sn_in_progress = f'{_PREFIX}RG02-INPROG'
        qr_in_progress = _insert_product(db_conn, sn_in_progress, days_offset=1)
        _insert_task(db_conn, sn_in_progress, qr_in_progress, worker_id, completed=False)

        # include_completed_within_days=1 → 당일 완료 포함
        result = get_partner_sn_progress(
            worker_company='FNI', worker_role='MECH', is_admin=False,
            include_completed_within_days=1
        )

        sns = [p['serial_number'] for p in result['products']]
        assert sn_in_progress in sns, "진행중 S/N이 결과에 없음"
        assert sn_recent in sns, "당일 완료 S/N이 결과에 없음 (within_days=1)"

        # include_completed_within_days=0 → 완료 제품 미포함
        result_no_completed = get_partner_sn_progress(
            worker_company='FNI', worker_role='MECH', is_admin=False,
            include_completed_within_days=0
        )
        sns_no_completed = [p['serial_number'] for p in result_no_completed['products']]
        assert sn_in_progress in sns_no_completed

        _cleanup(db_conn)

    def test_tc_lr_03_resolve_my_category(self, db_conn, seed_test_data):
        """TC-LR-03: _resolve_my_category() — 자사 담당 카테고리 정상 반환"""
        from app.services.progress_service import _resolve_my_category

        # Admin / GST → None (전체 보기)
        assert _resolve_my_category('GST', False, 'FNI', 'P&S', None) is None
        assert _resolve_my_category(None, True, 'FNI', 'P&S', None) is None

        # FNI / BAT → MECH
        assert _resolve_my_category('FNI', False, 'FNI', 'P&S', None) == 'MECH'
        assert _resolve_my_category('BAT', False, 'BAT', 'C&A', None) == 'MECH'

        # TMS(M) → TMS
        assert _resolve_my_category('TMS(M)', False, 'TMS', 'TMS', 'TMS') == 'TMS'

        # TMS(E) → ELEC
        assert _resolve_my_category('TMS(E)', False, 'FNI', 'TMS', None) == 'ELEC'

        # P&S / C&A → ELEC
        assert _resolve_my_category('P&S', False, 'FNI', 'P&S', None) == 'ELEC'
        assert _resolve_my_category('C&A', False, 'FNI', 'C&A', None) == 'ELEC'

        # 알 수 없는 회사 → None
        assert _resolve_my_category('UNKNOWN', False, 'FNI', 'P&S', None) is None

    def test_tc_lr_04_categories_progress_calculation(
        self, db_conn, seed_test_data, create_test_worker
    ):
        """TC-LR-04: categories 진행률 계산 정상 (total/done/percent)"""
        from app.services.progress_service import get_partner_sn_progress

        _cleanup(db_conn)

        worker_id = create_test_worker(
            email='sp38_rg04@test.axisos.com',
            password='Test123!', name='RG04 Worker',
            role='MECH', company='FNI'
        )

        sn = f'{_PREFIX}RG04-001'
        qr = _insert_product(db_conn, sn)

        # MECH tasks: 3개 중 2개 완료 → 67%
        _insert_task(db_conn, sn, qr, worker_id, 'MECH', 'TASK_A', 'Task A', completed=True)
        _insert_task(db_conn, sn, qr, worker_id, 'MECH', 'TASK_B', 'Task B', completed=True)
        _insert_task(db_conn, sn, qr, worker_id, 'MECH', 'TASK_C', 'Task C', completed=False)

        # ELEC tasks: 2개 중 1개 완료 → 50%
        _insert_task(db_conn, sn, qr, worker_id, 'ELEC', 'TASK_D', 'Task D', completed=True)
        _insert_task(db_conn, sn, qr, worker_id, 'ELEC', 'TASK_E', 'Task E', completed=False)

        # is_applicable=False → 집계 제외
        _insert_task(db_conn, sn, qr, worker_id, 'MECH', 'TASK_F', 'Task F', is_applicable=False)

        result = get_partner_sn_progress(
            worker_company='FNI', worker_role='MECH', is_admin=False
        )

        products = result['products']
        product = next((p for p in products if p['serial_number'] == sn), None)
        assert product is not None, f"S/N {sn}이 결과에 없음"

        mech = product['categories'].get('MECH', {})
        elec = product['categories'].get('ELEC', {})

        assert mech['total'] == 3, f"MECH total: expected 3, got {mech['total']}"
        assert mech['done'] == 2, f"MECH done: expected 2, got {mech['done']}"
        assert mech['percent'] == 67, f"MECH percent: expected 67, got {mech['percent']}"

        assert elec['total'] == 2, f"ELEC total: expected 2, got {elec['total']}"
        assert elec['done'] == 1, f"ELEC done: expected 1, got {elec['done']}"
        assert elec['percent'] == 50, f"ELEC percent: expected 50, got {elec['percent']}"

        # overall: 3/5 = 60%
        assert product['overall_percent'] == 60, (
            f"overall_percent: expected 60, got {product['overall_percent']}"
        )

        _cleanup(db_conn)

    def test_tc_lr_05_summary_counts(
        self, db_conn, seed_test_data, create_test_worker
    ):
        """TC-LR-05: summary (total/in_progress/completed_recent) 카운트 정상"""
        from app.services.progress_service import get_partner_sn_progress

        _cleanup(db_conn)

        worker_id = create_test_worker(
            email='sp38_rg05@test.axisos.com',
            password='Test123!', name='RG05 Worker',
            role='MECH', company='FNI'
        )

        # 진행 중 2대
        for i in range(1, 3):
            sn = f'{_PREFIX}RG05-IN{i:02d}'
            qr = _insert_product(db_conn, sn)
            _insert_task(db_conn, sn, qr, worker_id, completed=False)

        # 최근 완료 1대 (within_days=1 범위)
        sn_done = f'{_PREFIX}RG05-DONE01'
        qr_done = _insert_product(db_conn, sn_done)
        _insert_task(db_conn, sn_done, qr_done, worker_id, completed=True)
        _mark_all_completed(db_conn, sn_done)

        result = get_partner_sn_progress(
            worker_company='FNI', worker_role='MECH', is_admin=False,
            include_completed_within_days=1
        )

        summary = result['summary']
        # 이 테스트에서 생성한 S/N들이 결과에 포함되어야 함
        products = result['products']
        our_sns = {
            f'{_PREFIX}RG05-IN01',
            f'{_PREFIX}RG05-IN02',
            f'{_PREFIX}RG05-DONE01',
        }
        found_sns = {p['serial_number'] for p in products}
        assert our_sns.issubset(found_sns), f"일부 S/N이 결과에 없음: {our_sns - found_sns}"

        # summary 카운트 검증: total = in_progress + completed_recent
        assert summary['total'] == summary['in_progress'] + summary['completed_recent'], (
            f"summary 합계 불일치: total={summary['total']}, "
            f"in_progress={summary['in_progress']}, "
            f"completed_recent={summary['completed_recent']}"
        )

        # 우리 S/N 기준으로 in_progress >= 2, completed_recent >= 1
        our_in_progress = sum(
            1 for p in products if p['serial_number'] in our_sns and not p['all_completed']
        )
        our_completed = sum(
            1 for p in products if p['serial_number'] in our_sns and p['all_completed']
        )
        assert our_in_progress == 2, f"in_progress expected >=2, got {our_in_progress}"
        assert our_completed == 1, f"completed_recent expected >=1, got {our_completed}"

        _cleanup(db_conn)
