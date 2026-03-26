"""
Sprint 37-B: S/N별 실적확인 + TM 혼재 제거 + End 필터 (#38)
Regression 테스트 7건 (TC-SR-01 ~ TC-SR-07)

- MECH/ELEC partner 혼재 기존 동작 유지
- tm_pressure_test_required=false 유지
- _CONFIRM_TASK_FILTER TMS→TANK_MODULE only
- _is_process_confirmable() 기존 O/N 전체 판정 (PI/QI/SI용)
- _calc_sn_progress() task_id 레벨 GROUP BY
- cancel_confirm() soft delete 기존 동작
- admin_settings confirm_*_enabled=false 차단
"""

import sys
from pathlib import Path

_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest
from datetime import date, timedelta


_PREFIX = 'SN-SR37B-'


# ── Admin 토큰 픽스처 ──────────────────────────────
@pytest.fixture
def admin_token(db_conn, seed_test_data, get_auth_token):
    """Seed admin의 실제 worker_id로 JWT 토큰 생성"""
    cursor = db_conn.cursor()
    cursor.execute("SELECT id FROM workers WHERE email = 'seed_admin@test.axisos.com'")
    row = cursor.fetchone()
    cursor.close()
    return get_auth_token(row[0], role='ADMIN', is_admin=True)


def _insert_product(db_conn, serial_number, qr_doc_id, model, sales_order,
                    mech_start=None, mech_partner='GST', elec_partner='GST',
                    mech_end=None, elec_end=None, module_end=None):
    """테스트용 제품 + QR 등록
    주의: plan.product_info에는 module_end 컬럼이 없음.
    BE가 COALESCE(module_end, module_start)를 사용하므로 module_start에 저장.
    """
    if mech_start is None:
        mech_start = date.today()
    if mech_end is None:
        mech_end = mech_start
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO plan.product_info
            (serial_number, model, sales_order, mech_start, mech_end,
             elec_end, module_start, mech_partner, elec_partner)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (serial_number) DO NOTHING
    """, (serial_number, model, sales_order, mech_start, mech_end,
          elec_end, module_end, mech_partner, elec_partner))
    cursor.execute("""
        INSERT INTO public.qr_registry (qr_doc_id, serial_number, status)
        VALUES (%s, %s, 'active')
        ON CONFLICT (qr_doc_id) DO NOTHING
    """, (qr_doc_id, serial_number))
    db_conn.commit()
    cursor.close()


def _insert_task(db_conn, serial_number, qr_doc_id, category, task_id,
                 task_name, completed=False, is_applicable=True):
    """테스트용 태스크 등록"""
    cursor = db_conn.cursor()
    completed_at = 'NOW()' if completed else 'NULL'
    cursor.execute(f"""
        INSERT INTO app_task_details
            (serial_number, qr_doc_id, task_category, task_id, task_name,
             is_applicable, completed_at)
        VALUES (%s, %s, %s, %s, %s, %s, {completed_at})
        ON CONFLICT (serial_number, qr_doc_id, task_category, task_id) DO NOTHING
    """, (serial_number, qr_doc_id, category, task_id, task_name, is_applicable))
    db_conn.commit()
    cursor.close()


def _enable_confirm_settings(db_conn, process_types=None):
    """admin_settings에 confirm_*_enabled = true 설정"""
    if process_types is None:
        process_types = ['mech', 'elec', 'tm', 'pi', 'qi', 'si']
    cursor = db_conn.cursor()
    for pt in process_types:
        key = f'confirm_{pt}_enabled'
        cursor.execute("""
            INSERT INTO admin_settings (setting_key, setting_value, description)
            VALUES (%s, 'true', 'test')
            ON CONFLICT (setting_key) DO UPDATE SET setting_value = 'true'
        """, (key,))
    db_conn.commit()
    cursor.close()


def _set_tm_pressure_test(db_conn, required=True):
    """tm_pressure_test_required 설정"""
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO admin_settings (setting_key, setting_value, description)
        VALUES ('tm_pressure_test_required', %s, 'test')
        ON CONFLICT (setting_key) DO UPDATE SET setting_value = %s
    """, (str(required).lower(), str(required).lower()))
    db_conn.commit()
    cursor.close()


def _cleanup(db_conn, prefix=_PREFIX):
    """테스트 데이터 정리"""
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM plan.production_confirm WHERE sales_order LIKE %s",
                   (f'ON-{prefix}%',))
    cursor.execute("DELETE FROM app_task_details WHERE serial_number LIKE %s",
                   (f'{prefix}%',))
    cursor.execute("DELETE FROM completion_status WHERE serial_number LIKE %s",
                   (f'{prefix}%',))
    cursor.execute("DELETE FROM qr_registry WHERE serial_number LIKE %s",
                   (f'{prefix}%',))
    cursor.execute("DELETE FROM plan.product_info WHERE serial_number LIKE %s",
                   (f'{prefix}%',))
    db_conn.commit()
    cursor.close()


# ══════════════════════════════════════════════════════════════
# Regression: 기존 동작 유지 확인 (TC-SR-01 ~ TC-SR-07)
# ══════════════════════════════════════════════════════════════

class TestProcPartnerColRegression:
    """_PROC_PARTNER_COL 변경 후 기존 MECH/ELEC 동작 유지"""

    def test_tc_sr_01_mech_elec_mixed_still_works(self, client, db_conn, get_auth_token, admin_token):
        """TC-SR-01: MECH/ELEC partner 혼재 기존 동작 유지 (TM만 제거)"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        today = date.today()

        # MECH 혼재: TMS 1대 + FNI 1대
        _insert_product(db_conn, f'{_PREFIX}01-001', f'DOC-{_PREFIX}01-001', 'GAIA-I',
                        f'ON-{_PREFIX}01', mech_partner='TMS', mech_end=today)
        _insert_product(db_conn, f'{_PREFIX}01-002', f'DOC-{_PREFIX}01-002', 'GAIA-I',
                        f'ON-{_PREFIX}01', mech_partner='FNI', mech_end=today)
        _insert_task(db_conn, f'{_PREFIX}01-001', f'DOC-{_PREFIX}01-001', 'MECH',
                     'SELF_INSPECTION', '자주검사', completed=True)
        _insert_task(db_conn, f'{_PREFIX}01-002', f'DOC-{_PREFIX}01-002', 'MECH',
                     'SELF_INSPECTION', '자주검사', completed=True)

        iso_week = today.isocalendar()[1]
        token = admin_token
        resp = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        order = next((o for o in data['orders'] if o['sales_order'] == f'ON-{_PREFIX}01'), None)
        assert order is not None

        mech = order['processes'].get('MECH')
        assert mech is not None
        assert mech['mixed'] is True
        assert 'partner_confirms' in mech

        _cleanup(db_conn)


class TestTmPressureTestRegression:
    """Sprint 37-A tm_pressure_test_required 기존 동작 유지"""

    def test_tc_sr_02_tm_pressure_false_tank_module_only(self, client, db_conn, get_auth_token, admin_token):
        """TC-SR-02: tm_pressure_test_required=false → TMS progress TANK_MODULE only"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        _set_tm_pressure_test(db_conn, required=False)
        today = date.today()

        sn = f'{_PREFIX}02-001'
        _insert_product(db_conn, sn, f'DOC-{sn}', 'GAIA-I', f'ON-{_PREFIX}02',
                        mech_partner='TMS', mech_end=today, module_end=today)
        _insert_task(db_conn, sn, f'DOC-{sn}', 'TMS', 'TANK_MODULE', '탱크모듈', completed=True)
        _insert_task(db_conn, sn, f'DOC-{sn}', 'TMS', 'PRESSURE_TEST', '가압검사', completed=False)

        iso_week = today.isocalendar()[1]
        token = admin_token
        resp = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        order = next((o for o in data['orders'] if o['sales_order'] == f'ON-{_PREFIX}02'), None)
        assert order is not None

        tm = order['processes'].get('TM')
        assert tm is not None
        # TANK_MODULE only → 100%
        assert tm['pct'] == 100.0

        # 원래 설정 복구
        _set_tm_pressure_test(db_conn, required=True)
        _cleanup(db_conn)


class TestConfirmTaskFilterRegression:
    """_CONFIRM_TASK_FILTER 미변경 확인"""

    def test_tc_sr_03_tms_tank_module_only_confirmable(self):
        """TC-SR-03: _CONFIRM_TASK_FILTER TMS→TANK_MODULE only confirmable"""
        from app.routes.production import _CONFIRM_TASK_FILTER

        assert 'TMS' in _CONFIRM_TASK_FILTER
        assert _CONFIRM_TASK_FILTER['TMS'] == 'TANK_MODULE'


class TestIsProcessConfirmableRegression:
    """_is_process_confirmable() 기존 O/N 전체 판정 유지"""

    def test_tc_sr_04_pi_on_level_confirmable(self):
        """TC-SR-04: PI O/N 전체 판정 — 기존 로직 미변경"""
        from app.routes.production import _is_process_confirmable

        # 2 S/N 모두 PI 완료
        sns_progress = {
            'SN-001': {
                'PI': {
                    'total': 3, 'completed': 3, 'pct': 100.0,
                    'tasks': {'PRE_INSPECT': {'total': 3, 'completed': 3}}
                }
            },
            'SN-002': {
                'PI': {
                    'total': 3, 'completed': 3, 'pct': 100.0,
                    'tasks': {'PRE_INSPECT': {'total': 3, 'completed': 3}}
                }
            }
        }
        settings = {'confirm_pi_enabled': True}

        result = _is_process_confirmable(
            sns_progress, 'PI', settings,
            proc_key='PI', serial_numbers=['SN-001', 'SN-002']
        )
        assert result is True

        # 1 S/N만 미완료 → O/N 전체 False
        sns_progress['SN-002']['PI']['completed'] = 1
        result = _is_process_confirmable(
            sns_progress, 'PI', settings,
            proc_key='PI', serial_numbers=['SN-001', 'SN-002']
        )
        assert result is False


class TestCalcSnProgressRegression:
    """_calc_sn_progress() task_id 레벨 GROUP BY 정상"""

    def test_tc_sr_05_task_id_level_groupby(self, db_conn):
        """TC-SR-05: task_id 레벨 GROUP BY 정상"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        sn = f'{_PREFIX}05-001'
        _insert_product(db_conn, sn, f'DOC-{sn}', 'GAIA-I', f'ON-{_PREFIX}05',
                        mech_partner='TMS', module_end=date.today())
        _insert_task(db_conn, sn, f'DOC-{sn}', 'TMS', 'TANK_MODULE', '탱크모듈', completed=True)
        _insert_task(db_conn, sn, f'DOC-{sn}', 'TMS', 'PRESSURE_TEST', '가압검사', completed=False)
        _insert_task(db_conn, sn, f'DOC-{sn}', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        from app.routes.production import _calc_sn_progress
        from app.db_pool import get_conn, put_conn

        conn = get_conn()
        try:
            cur = conn.cursor()
            result = _calc_sn_progress(cur, [sn])

            assert sn in result
            tms = result[sn]['TMS']
            assert 'tasks' in tms
            assert 'TANK_MODULE' in tms['tasks']
            assert 'PRESSURE_TEST' in tms['tasks']
            assert tms['tasks']['TANK_MODULE']['completed'] == 1
            assert tms['tasks']['PRESSURE_TEST']['completed'] == 0

            mech = result[sn]['MECH']
            assert mech['completed'] == 1
        finally:
            put_conn(conn)

        _cleanup(db_conn)


class TestCancelConfirmRegression:
    """cancel_confirm() soft delete 기존 동작 유지"""

    def test_tc_sr_06_cancel_soft_delete(self, client, db_conn, get_auth_token, admin_token):
        """TC-SR-06: cancel_confirm() id 기반 soft delete 유지"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        today = date.today()
        iso_week = today.isocalendar()[1]

        sn = f'{_PREFIX}06-001'
        _insert_product(db_conn, sn, f'DOC-{sn}', 'DRAGON', f'ON-{_PREFIX}06', mech_end=today)
        _insert_task(db_conn, sn, f'DOC-{sn}', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        token = admin_token

        resp = client.post('/api/admin/production/confirm', json={
            'sales_order': f'ON-{_PREFIX}06',
            'process_type': 'MECH',
            'serial_numbers': [sn],
            'confirmed_week': f'W{iso_week:02d}',
            'confirmed_month': f'{today.year}-{today.month:02d}',
        }, headers={'Authorization': f'Bearer {token}'})
        confirm_id = resp.get_json()['confirmed'][0]['id']

        # 취소
        resp2 = client.delete(
            f'/api/admin/production/confirm/{confirm_id}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp2.status_code == 200

        # soft delete 확인
        cursor = db_conn.cursor()
        cursor.execute("SELECT deleted_at FROM plan.production_confirm WHERE id = %s", (confirm_id,))
        row = cursor.fetchone()
        cursor.close()
        assert row[0] is not None

        _cleanup(db_conn)


class TestSettingsDisabledRegression:
    """admin_settings confirm_*_enabled=false 차단"""

    def test_tc_sr_07_setting_disabled_blocks_confirm(self):
        """TC-SR-07: confirm_mech_enabled=false → confirmable=false"""
        from app.routes.production import _is_process_confirmable

        sns_progress = {
            'SN-001': {
                'MECH': {
                    'total': 5, 'completed': 5, 'pct': 100.0,
                    'tasks': {'SELF_INSPECTION': {'total': 5, 'completed': 5}}
                }
            }
        }
        settings = {'confirm_mech_enabled': False}

        result = _is_process_confirmable(
            sns_progress, 'MECH', settings,
            proc_key='MECH', serial_numbers=['SN-001']
        )
        assert result is False
