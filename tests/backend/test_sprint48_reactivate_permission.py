"""
Sprint 48: reactivate-task 권한 검증 테스트

TC-48-01 ~ TC-48-10 (10건)

TMS 회사 분기 (Sprint 48 신규):
  TC-48-01: TMS(M) Manager → mech_partner='TMS' MECH task → 200 허용
  TC-48-02: TMS(M) Manager → module_outsourcing='TMS' TMS task → 200 허용
  TC-48-03: TMS(M) Manager → elec_partner='P&S' ELEC task → 403 차단 (타사)

  TC-48-04: TMS(E) Manager → elec_partner='TMS' ELEC task → 200 허용
  TC-48-05: TMS(E) Manager → mech_partner='FNI' MECH task → 403 차단

기존 회사 Regression:
  TC-48-06: FNI Manager → mech_partner='FNI' MECH task → 200 허용
  TC-48-07: P&S Manager → elec_partner='P&S' ELEC task → 200 허용
  TC-48-08: GST Manager → PI task → 200 허용
  TC-48-09: BAT Manager → elec_partner='P&S' ELEC task → 403 차단 (타사)
  TC-48-10: Admin → 모든 카테고리 → 200 허용 (is_admin 분기)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

import pytest
from datetime import date

# ── 테스트 데이터 prefix ──────────────────────────
_PREFIX = 'SP48-'


# ── 헬퍼 함수 ─────────────────────────────────────

def _insert_product(db_conn, serial_number, qr_doc_id,
                    mech_partner=None, elec_partner=None, module_outsourcing=None):
    """테스트용 product_info + qr_registry 삽입"""
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO plan.product_info (
            serial_number, model, sales_order,
            mech_partner, elec_partner, module_outsourcing,
            prod_date
        )
        VALUES (%s, 'GAIA-I', 'SP48-TEST', %s, %s, %s, NOW()::date)
        ON CONFLICT (serial_number) DO NOTHING
    """, (serial_number, mech_partner, elec_partner, module_outsourcing))

    cursor.execute("""
        INSERT INTO public.qr_registry (qr_doc_id, serial_number, status)
        VALUES (%s, %s, 'active')
        ON CONFLICT (qr_doc_id) DO NOTHING
    """, (qr_doc_id, serial_number))
    db_conn.commit()
    cursor.close()


def _insert_completed_task(db_conn, serial_number, qr_doc_id,
                           category, task_id_str, task_name,
                           worker_id):
    """완료 상태(completed_at 설정) app_task_details 삽입 후 task_detail_id 반환"""
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO app_task_details (
            serial_number, qr_doc_id, task_category, task_id, task_name,
            worker_id, is_applicable, started_at, completed_at, duration_minutes
        )
        VALUES (%s, %s, %s, %s, %s, %s, TRUE, NOW() - INTERVAL '60 minutes', NOW(), 60)
        ON CONFLICT (serial_number, qr_doc_id, task_category, task_id)
        DO UPDATE SET completed_at = NOW(), started_at = NOW() - INTERVAL '60 minutes'
        RETURNING id
    """, (serial_number, qr_doc_id, category, task_id_str, task_name, worker_id))
    row = cursor.fetchone()
    if row is None:
        cursor.execute("""
            SELECT id FROM app_task_details
            WHERE serial_number=%s AND task_category=%s AND task_id=%s
        """, (serial_number, category, task_id_str))
        row = cursor.fetchone()
    task_detail_id = row[0]
    db_conn.commit()
    cursor.close()
    return task_detail_id


def _insert_completion_status(db_conn, serial_number, category):
    """completion_status에 해당 카테고리를 완료 상태로 삽입"""
    col_map = {
        'MECH': 'mech_completed',
        'ELEC': 'ee_completed',
        'TMS':  'tm_completed',
        'PI':   'pi_completed',
        'QI':   'qi_completed',
        'SI':   'si_completed',
    }
    col = col_map.get(category, 'mech_completed')
    cursor = db_conn.cursor()
    try:
        cursor.execute(f"""
            INSERT INTO completion_status (serial_number, {col})
            VALUES (%s, TRUE)
            ON CONFLICT (serial_number) DO UPDATE SET {col} = TRUE
        """, (serial_number,))
        db_conn.commit()
    except Exception:
        db_conn.rollback()
    finally:
        cursor.close()


def _cleanup(db_conn, serial_numbers):
    """테스트 데이터 정리 (FK 순서 준수)"""
    cursor = db_conn.cursor()
    try:
        for sn in serial_numbers:
            cursor.execute(
                "DELETE FROM work_completion_log WHERE serial_number=%s", (sn,))
            cursor.execute(
                "DELETE FROM work_start_log WHERE serial_number=%s", (sn,))
            cursor.execute(
                "DELETE FROM app_task_details WHERE serial_number=%s", (sn,))
            cursor.execute(
                "DELETE FROM completion_status WHERE serial_number=%s", (sn,))
            qr = f'DOC_{sn}'
            cursor.execute(
                "DELETE FROM public.qr_registry WHERE qr_doc_id=%s", (qr,))
            cursor.execute(
                "DELETE FROM plan.product_info WHERE serial_number=%s", (sn,))
        db_conn.commit()
    except Exception as e:
        db_conn.rollback()
        print(f"[SP48 cleanup] 실패: {e}")
    finally:
        cursor.close()


# ── 테스트 클래스 ──────────────────────────────────

class TestSprint48ReactivatePermission:
    """Sprint 48: reactivate-task 권한 — 10건"""

    def test_tc_48_01_tms_m_manager_mech_task_allowed(
        self, client, seed_test_data, get_auth_token, create_test_worker, db_conn
    ):
        """TC-48-01: TMS(M) Manager → mech_partner='TMS' 제품의 MECH task → 200 허용"""
        sn = f'{_PREFIX}TC01'
        qr = f'DOC_{sn}'
        _insert_product(db_conn, sn, qr, mech_partner='TMS', elec_partner='P&S', module_outsourcing='TMS')

        # TMS(M) Manager 생성
        mgr_id = create_test_worker(
            email='sp48_tc01_mgr@test.axisos.com',
            password='Pass123!',
            name='SP48 TMS-M Manager',
            role='MECH',
            company='TMS(M)',
            is_manager=True,
        )
        # worker 자신의 완료된 task 삽입
        task_detail_id = _insert_completed_task(
            db_conn, sn, qr, 'MECH', 'SELF_INSPECTION', '자주검사', mgr_id
        )
        _insert_completion_status(db_conn, sn, 'MECH')

        token = get_auth_token(mgr_id, role='MECH', is_admin=False)
        resp = client.post(
            '/api/app/work/reactivate-task',
            json={'task_detail_id': task_detail_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        _cleanup(db_conn, [sn])
        assert resp.status_code == 200, (
            f"TC-48-01 FAILED: expected 200, got {resp.status_code} — {resp.get_json()}"
        )

    def test_tc_48_02_tms_m_manager_tms_task_allowed(
        self, client, seed_test_data, get_auth_token, create_test_worker, db_conn
    ):
        """TC-48-02: TMS(M) Manager → module_outsourcing='TMS' 제품의 TMS task → 200 허용"""
        sn = f'{_PREFIX}TC02'
        qr = f'DOC_{sn}'
        _insert_product(db_conn, sn, qr, mech_partner='FNI', elec_partner='P&S', module_outsourcing='TMS')

        mgr_id = create_test_worker(
            email='sp48_tc02_mgr@test.axisos.com',
            password='Pass123!',
            name='SP48 TMS-M Manager TC02',
            role='MECH',
            company='TMS(M)',
            is_manager=True,
        )
        task_detail_id = _insert_completed_task(
            db_conn, sn, qr, 'TMS', 'TANK_MODULE', 'Tank Module', mgr_id
        )
        _insert_completion_status(db_conn, sn, 'TMS')

        token = get_auth_token(mgr_id, role='MECH', is_admin=False)
        resp = client.post(
            '/api/app/work/reactivate-task',
            json={'task_detail_id': task_detail_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        _cleanup(db_conn, [sn])
        assert resp.status_code == 200, (
            f"TC-48-02 FAILED: expected 200, got {resp.status_code} — {resp.get_json()}"
        )

    def test_tc_48_03_tms_m_manager_elec_task_forbidden(
        self, client, seed_test_data, get_auth_token, create_test_worker, db_conn
    ):
        """TC-48-03: TMS(M) Manager → elec_partner='P&S' 제품의 ELEC task → 403 차단 (타사)"""
        sn = f'{_PREFIX}TC03'
        qr = f'DOC_{sn}'
        _insert_product(db_conn, sn, qr, mech_partner='TMS', elec_partner='P&S', module_outsourcing='TMS')

        mgr_id = create_test_worker(
            email='sp48_tc03_mgr@test.axisos.com',
            password='Pass123!',
            name='SP48 TMS-M Manager TC03',
            role='MECH',
            company='TMS(M)',
            is_manager=True,
        )
        # ELEC task (타사 P&S 제품) 를 완료 상태로 삽입
        task_detail_id = _insert_completed_task(
            db_conn, sn, qr, 'ELEC', 'WIRING', '배선 포설', mgr_id
        )
        _insert_completion_status(db_conn, sn, 'ELEC')

        token = get_auth_token(mgr_id, role='MECH', is_admin=False)
        resp = client.post(
            '/api/app/work/reactivate-task',
            json={'task_detail_id': task_detail_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        _cleanup(db_conn, [sn])
        assert resp.status_code == 403, (
            f"TC-48-03 FAILED: expected 403, got {resp.status_code} — {resp.get_json()}"
        )

    def test_tc_48_04_tms_e_manager_elec_task_allowed(
        self, client, seed_test_data, get_auth_token, create_test_worker, db_conn
    ):
        """TC-48-04: TMS(E) Manager → elec_partner='TMS' 제품의 ELEC task → 200 허용"""
        sn = f'{_PREFIX}TC04'
        qr = f'DOC_{sn}'
        _insert_product(db_conn, sn, qr, mech_partner='FNI', elec_partner='TMS', module_outsourcing=None)

        mgr_id = create_test_worker(
            email='sp48_tc04_mgr@test.axisos.com',
            password='Pass123!',
            name='SP48 TMS-E Manager TC04',
            role='ELEC',
            company='TMS(E)',
            is_manager=True,
        )
        task_detail_id = _insert_completed_task(
            db_conn, sn, qr, 'ELEC', 'WIRING', '배선 포설', mgr_id
        )
        _insert_completion_status(db_conn, sn, 'ELEC')

        token = get_auth_token(mgr_id, role='ELEC', is_admin=False)
        resp = client.post(
            '/api/app/work/reactivate-task',
            json={'task_detail_id': task_detail_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        _cleanup(db_conn, [sn])
        assert resp.status_code == 200, (
            f"TC-48-04 FAILED: expected 200, got {resp.status_code} — {resp.get_json()}"
        )

    def test_tc_48_05_tms_e_manager_mech_task_forbidden(
        self, client, seed_test_data, get_auth_token, create_test_worker, db_conn
    ):
        """TC-48-05: TMS(E) Manager → mech_partner='FNI' 제품의 MECH task → 403 차단"""
        sn = f'{_PREFIX}TC05'
        qr = f'DOC_{sn}'
        _insert_product(db_conn, sn, qr, mech_partner='FNI', elec_partner='TMS', module_outsourcing=None)

        mgr_id = create_test_worker(
            email='sp48_tc05_mgr@test.axisos.com',
            password='Pass123!',
            name='SP48 TMS-E Manager TC05',
            role='ELEC',
            company='TMS(E)',
            is_manager=True,
        )
        task_detail_id = _insert_completed_task(
            db_conn, sn, qr, 'MECH', 'SELF_INSPECTION', '자주검사', mgr_id
        )
        _insert_completion_status(db_conn, sn, 'MECH')

        token = get_auth_token(mgr_id, role='ELEC', is_admin=False)
        resp = client.post(
            '/api/app/work/reactivate-task',
            json={'task_detail_id': task_detail_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        _cleanup(db_conn, [sn])
        assert resp.status_code == 403, (
            f"TC-48-05 FAILED: expected 403, got {resp.status_code} — {resp.get_json()}"
        )

    def test_tc_48_06_fni_manager_mech_task_allowed(
        self, client, seed_test_data, get_auth_token, create_test_worker, db_conn
    ):
        """TC-48-06: FNI Manager → mech_partner='FNI' 제품의 MECH task → 200 허용 (regression)"""
        sn = f'{_PREFIX}TC06'
        qr = f'DOC_{sn}'
        _insert_product(db_conn, sn, qr, mech_partner='FNI', elec_partner='P&S', module_outsourcing=None)

        mgr_id = create_test_worker(
            email='sp48_tc06_mgr@test.axisos.com',
            password='Pass123!',
            name='SP48 FNI Manager TC06',
            role='MECH',
            company='FNI',
            is_manager=True,
        )
        task_detail_id = _insert_completed_task(
            db_conn, sn, qr, 'MECH', 'SELF_INSPECTION', '자주검사', mgr_id
        )
        _insert_completion_status(db_conn, sn, 'MECH')

        token = get_auth_token(mgr_id, role='MECH', is_admin=False)
        resp = client.post(
            '/api/app/work/reactivate-task',
            json={'task_detail_id': task_detail_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        _cleanup(db_conn, [sn])
        assert resp.status_code == 200, (
            f"TC-48-06 FAILED: expected 200, got {resp.status_code} — {resp.get_json()}"
        )

    def test_tc_48_07_ps_manager_elec_task_allowed(
        self, client, seed_test_data, get_auth_token, create_test_worker, db_conn
    ):
        """TC-48-07: P&S Manager → elec_partner='P&S' 제품의 ELEC task → 200 허용 (regression)"""
        sn = f'{_PREFIX}TC07'
        qr = f'DOC_{sn}'
        _insert_product(db_conn, sn, qr, mech_partner='FNI', elec_partner='P&S', module_outsourcing=None)

        mgr_id = create_test_worker(
            email='sp48_tc07_mgr@test.axisos.com',
            password='Pass123!',
            name='SP48 P&S Manager TC07',
            role='ELEC',
            company='P&S',
            is_manager=True,
        )
        task_detail_id = _insert_completed_task(
            db_conn, sn, qr, 'ELEC', 'WIRING', '배선 포설', mgr_id
        )
        _insert_completion_status(db_conn, sn, 'ELEC')

        token = get_auth_token(mgr_id, role='ELEC', is_admin=False)
        resp = client.post(
            '/api/app/work/reactivate-task',
            json={'task_detail_id': task_detail_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        _cleanup(db_conn, [sn])
        assert resp.status_code == 200, (
            f"TC-48-07 FAILED: expected 200, got {resp.status_code} — {resp.get_json()}"
        )

    def test_tc_48_08_gst_manager_pi_task_allowed(
        self, client, seed_test_data, get_auth_token, create_test_worker, db_conn
    ):
        """TC-48-08: GST Manager → PI task → 200 허용 (regression)"""
        sn = f'{_PREFIX}TC08'
        qr = f'DOC_{sn}'
        _insert_product(db_conn, sn, qr, mech_partner='FNI', elec_partner='P&S', module_outsourcing=None)

        mgr_id = create_test_worker(
            email='sp48_tc08_mgr@test.axisos.com',
            password='Pass123!',
            name='SP48 GST Manager TC08',
            role='PI',
            company='GST',
            is_manager=True,
        )
        task_detail_id = _insert_completed_task(
            db_conn, sn, qr, 'PI', 'PI_CHECK', 'PI 검사', mgr_id
        )
        _insert_completion_status(db_conn, sn, 'PI')

        token = get_auth_token(mgr_id, role='PI', is_admin=False)
        resp = client.post(
            '/api/app/work/reactivate-task',
            json={'task_detail_id': task_detail_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        _cleanup(db_conn, [sn])
        assert resp.status_code == 200, (
            f"TC-48-08 FAILED: expected 200, got {resp.status_code} — {resp.get_json()}"
        )

    def test_tc_48_09_bat_manager_ps_elec_task_forbidden(
        self, client, seed_test_data, get_auth_token, create_test_worker, db_conn
    ):
        """TC-48-09: BAT Manager → elec_partner='P&S' 제품의 ELEC task → 403 차단 (타사)"""
        sn = f'{_PREFIX}TC09'
        qr = f'DOC_{sn}'
        _insert_product(db_conn, sn, qr, mech_partner='BAT', elec_partner='P&S', module_outsourcing=None)

        mgr_id = create_test_worker(
            email='sp48_tc09_mgr@test.axisos.com',
            password='Pass123!',
            name='SP48 BAT Manager TC09',
            role='MECH',
            company='BAT',
            is_manager=True,
        )
        # BAT Manager가 타사(P&S) ELEC task 재활성화 시도
        task_detail_id = _insert_completed_task(
            db_conn, sn, qr, 'ELEC', 'WIRING', '배선 포설', mgr_id
        )
        _insert_completion_status(db_conn, sn, 'ELEC')

        token = get_auth_token(mgr_id, role='MECH', is_admin=False)
        resp = client.post(
            '/api/app/work/reactivate-task',
            json={'task_detail_id': task_detail_id},
            headers={'Authorization': f'Bearer {token}'}
        )

        _cleanup(db_conn, [sn])
        assert resp.status_code == 403, (
            f"TC-48-09 FAILED: expected 403, got {resp.status_code} — {resp.get_json()}"
        )

    def test_tc_48_10_admin_all_categories_allowed(
        self, client, seed_test_data, get_auth_token, create_test_worker, db_conn
    ):
        """TC-48-10: Admin → 모든 카테고리 재활성화 → 200 허용 (is_admin 분기 미진입)"""
        categories = [
            ('MECH', 'SELF_INSPECTION', '자주검사'),
            ('ELEC', 'WIRING', '배선 포설'),
            ('TMS',  'TANK_MODULE', 'Tank Module'),
        ]
        # Admin worker 생성
        admin_id = create_test_worker(
            email='sp48_tc10_admin@test.axisos.com',
            password='Pass123!',
            name='SP48 Admin TC10',
            role='ADMIN',
            company='GST',
            is_manager=False,
            is_admin=True,
        )
        token = get_auth_token(admin_id, role='ADMIN', is_admin=True)

        all_sns = []
        results = {}

        cursor = db_conn.cursor()
        for cat, tid, tname in categories:
            sn = f'{_PREFIX}TC10-{cat}'
            qr = f'DOC_{sn}'
            all_sns.append(sn)

            _insert_product(
                db_conn, sn, qr,
                mech_partner='FNI', elec_partner='P&S', module_outsourcing='TMS'
            )
            task_detail_id = _insert_completed_task(
                db_conn, sn, qr, cat, tid, tname, admin_id
            )
            _insert_completion_status(db_conn, sn, cat)

            resp = client.post(
                '/api/app/work/reactivate-task',
                json={'task_detail_id': task_detail_id},
                headers={'Authorization': f'Bearer {token}'}
            )
            results[cat] = resp.status_code

        cursor.close()
        _cleanup(db_conn, all_sns)

        for cat, code in results.items():
            assert code == 200, (
                f"TC-48-10 FAILED [{cat}]: expected 200, got {code}"
            )
