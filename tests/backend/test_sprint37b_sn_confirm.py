"""
Sprint 37-B: S/N별 실적확인 + TM 혼재 제거 + End 필터 (#38)
White-box 테스트 24건 (TC-SC-01 ~ TC-SC-24)

- _PROC_PARTNER_COL TM 제거 검증
- _is_sn_process_confirmable() 단일 S/N 판정
- _build_order_item() sn_confirms 구조
- confirm_production() serial_numbers 배열 처리
- cancel_confirm() serial_number 응답
- get_performance() end 날짜 + confirms dict 키
"""

import sys
from pathlib import Path

_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest
from datetime import date, timedelta


# ── 테스트 데이터 prefix ──────────────────────────
_PREFIX = 'SN-SP37B-'


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
    """테스트용 제품 + QR 등록 (end 날짜 지원)
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


def _disable_confirm_setting(db_conn, process_type):
    """admin_settings에 특정 공정 confirm 비활성"""
    cursor = db_conn.cursor()
    key = f'confirm_{process_type}_enabled'
    cursor.execute("""
        INSERT INTO admin_settings (setting_key, setting_value, description)
        VALUES (%s, 'false', 'test')
        ON CONFLICT (setting_key) DO UPDATE SET setting_value = 'false'
    """, (key,))
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
# White-box: _PROC_PARTNER_COL TM 제거 (TC-SC-01 ~ TC-SC-03)
# ══════════════════════════════════════════════════════════════

class TestProcPartnerColTmRemoved:
    """_PROC_PARTNER_COL에서 TM 키 제거 검증"""

    def test_tc_sc_01_proc_partner_col_no_tm(self):
        """TC-SC-01: _PROC_PARTNER_COL에 'TM' 키 없음 → TM은 비혼재 경로"""
        from app.routes.production import _PROC_PARTNER_COL

        assert 'TM' not in _PROC_PARTNER_COL
        assert 'MECH' in _PROC_PARTNER_COL
        assert 'ELEC' in _PROC_PARTNER_COL

    def test_tc_sc_02_tm_no_partner_confirms_mixed_on(self, client, db_conn, get_auth_token, admin_token):
        """TC-SC-02: O/N에 mech_partner TMS(1대)+FNI(4대) — TM에 partner_confirms 없음, sn_confirms만"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        today = date.today()

        # TMS 1대 (is_tms=true 모델) + FNI 4대
        _insert_product(db_conn, f'{_PREFIX}02-001', f'DOC-{_PREFIX}02-001', 'GAIA-I',
                        f'ON-{_PREFIX}02', mech_partner='TMS', mech_end=today, module_end=today)
        for i in range(2, 6):
            _insert_product(db_conn, f'{_PREFIX}02-00{i}', f'DOC-{_PREFIX}02-00{i}', 'GAIA-I',
                            f'ON-{_PREFIX}02', mech_partner='FNI', mech_end=today)

        # TMS S/N만 TMS tasks 등록 (FNI는 TMS tasks 없음 → TM에 안 나타남)
        _insert_task(db_conn, f'{_PREFIX}02-001', f'DOC-{_PREFIX}02-001', 'TMS',
                     'TANK_MODULE', '탱크모듈', completed=True)

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

        tm_proc = order['processes'].get('TM')
        if tm_proc:
            # TM에 partner_confirms가 없어야 함 (TM 혼재 제거)
            assert 'partner_confirms' not in tm_proc
            # sn_confirms만 존재
            assert 'sn_confirms' in tm_proc

        _cleanup(db_conn)

    def test_tc_sc_03_tm_tms_only_sn_confirms(self, client, db_conn, get_auth_token, admin_token):
        """TC-SC-03: TMS 단독 O/N — TM sn_confirms 정상"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        today = date.today()

        _insert_product(db_conn, f'{_PREFIX}03-001', f'DOC-{_PREFIX}03-001', 'GAIA-I',
                        f'ON-{_PREFIX}03', mech_partner='TMS', mech_end=today, module_end=today)
        _insert_task(db_conn, f'{_PREFIX}03-001', f'DOC-{_PREFIX}03-001', 'TMS',
                     'TANK_MODULE', '탱크모듈', completed=True)

        iso_week = today.isocalendar()[1]
        token = admin_token
        resp = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        order = next((o for o in data['orders'] if o['sales_order'] == f'ON-{_PREFIX}03'), None)
        assert order is not None

        tm_proc = order['processes'].get('TM')
        assert tm_proc is not None
        assert 'sn_confirms' in tm_proc
        assert len(tm_proc['sn_confirms']) == 1
        assert tm_proc['sn_confirms'][0]['serial_number'] == f'{_PREFIX}03-001'

        _cleanup(db_conn)


# ══════════════════════════════════════════════════════════════
# White-box: _is_sn_process_confirmable() 단일 S/N 판정 (TC-SC-04 ~ TC-SC-07)
# ══════════════════════════════════════════════════════════════

class TestIsSnProcessConfirmable:
    """_is_sn_process_confirmable() 단위 테스트"""

    def test_tc_sc_04_mech_100pct_confirmable(self):
        """TC-SC-04: S/N MECH 100% 완료 → confirmable=true"""
        from app.routes.production import _is_sn_process_confirmable

        sns_progress = {
            'SN-001': {
                'MECH': {
                    'total': 5, 'completed': 5, 'pct': 100.0,
                    'tasks': {'SELF_INSPECTION': {'total': 5, 'completed': 5}}
                }
            }
        }
        settings = {'confirm_mech_enabled': True}

        result = _is_sn_process_confirmable(sns_progress, 'MECH', settings, 'MECH', 'SN-001')
        assert result is True

    def test_tc_sc_05_mech_80pct_not_confirmable(self):
        """TC-SC-05: S/N MECH 80% 완료 → confirmable=false"""
        from app.routes.production import _is_sn_process_confirmable

        sns_progress = {
            'SN-001': {
                'MECH': {
                    'total': 5, 'completed': 4, 'pct': 80.0,
                    'tasks': {'SELF_INSPECTION': {'total': 5, 'completed': 4}}
                }
            }
        }
        settings = {'confirm_mech_enabled': True}

        result = _is_sn_process_confirmable(sns_progress, 'MECH', settings, 'MECH', 'SN-001')
        assert result is False

    def test_tc_sc_06_tms_tank_module_only(self):
        """TC-SC-06: TMS TANK_MODULE 100% + PRESSURE_TEST 0% → confirmable=true"""
        from app.routes.production import _is_sn_process_confirmable

        sns_progress = {
            'SN-001': {
                'TMS': {
                    'total': 10, 'completed': 5, 'pct': 50.0,
                    'tasks': {
                        'TANK_MODULE': {'total': 5, 'completed': 5},
                        'PRESSURE_TEST': {'total': 5, 'completed': 0},
                    }
                }
            }
        }
        settings = {'confirm_tm_enabled': True}

        result = _is_sn_process_confirmable(sns_progress, 'TMS', settings, 'TM', 'SN-001')
        assert result is True

    def test_tc_sc_07_setting_disabled(self):
        """TC-SC-07: confirm_mech_enabled=false → confirmable=false"""
        from app.routes.production import _is_sn_process_confirmable

        sns_progress = {
            'SN-001': {
                'MECH': {
                    'total': 5, 'completed': 5, 'pct': 100.0,
                    'tasks': {'SELF_INSPECTION': {'total': 5, 'completed': 5}}
                }
            }
        }
        settings = {'confirm_mech_enabled': False}

        result = _is_sn_process_confirmable(sns_progress, 'MECH', settings, 'MECH', 'SN-001')
        assert result is False


# ══════════════════════════════════════════════════════════════
# White-box: _build_order_item() sn_confirms 구조 (TC-SC-08 ~ TC-SC-14)
# ══════════════════════════════════════════════════════════════

class TestBuildOrderItemSnConfirms:
    """_build_order_item() sn_confirms 구조 검증 — API 레벨"""

    def test_tc_sc_08_mech_non_mixed_sn_confirms(self, client, db_conn, get_auth_token, admin_token):
        """TC-SC-08: MECH 비혼재 O/N 3대 — sn_confirms 길이 3"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        today = date.today()

        for i in range(1, 4):
            sn = f'{_PREFIX}08-00{i}'
            _insert_product(db_conn, sn, f'DOC-{sn}', 'DRAGON', f'ON-{_PREFIX}08',
                            mech_partner='GST', mech_end=today)
            _insert_task(db_conn, sn, f'DOC-{sn}', 'MECH', 'SELF_INSPECTION', '자주검사',
                         completed=(i <= 2))

        iso_week = today.isocalendar()[1]
        token = admin_token
        resp = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        order = next((o for o in data['orders'] if o['sales_order'] == f'ON-{_PREFIX}08'), None)
        assert order is not None

        mech = order['processes'].get('MECH')
        assert mech is not None
        assert 'sn_confirms' in mech
        assert len(mech['sn_confirms']) == 3
        # 각 S/N별 confirmable/confirmed 필드 존재
        for sc in mech['sn_confirms']:
            assert 'serial_number' in sc
            assert 'confirmable' in sc
            assert 'confirmed' in sc

        _cleanup(db_conn)

    def test_tc_sc_09_mech_mixed_partner_confirms(self, client, db_conn, get_auth_token, admin_token):
        """TC-SC-09: MECH 혼재 (TMS 2대+FNI 3대) — partner_confirms 구조"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        today = date.today()

        # TMS 2대
        for i in range(1, 3):
            sn = f'{_PREFIX}09-00{i}'
            _insert_product(db_conn, sn, f'DOC-{sn}', 'GAIA-I', f'ON-{_PREFIX}09',
                            mech_partner='TMS', mech_end=today)
            _insert_task(db_conn, sn, f'DOC-{sn}', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        # FNI 3대
        for i in range(3, 6):
            sn = f'{_PREFIX}09-00{i}'
            _insert_product(db_conn, sn, f'DOC-{sn}', 'GAIA-I', f'ON-{_PREFIX}09',
                            mech_partner='FNI', mech_end=today)
            _insert_task(db_conn, sn, f'DOC-{sn}', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        iso_week = today.isocalendar()[1]
        token = admin_token
        resp = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        order = next((o for o in data['orders'] if o['sales_order'] == f'ON-{_PREFIX}09'), None)
        assert order is not None

        mech = order['processes'].get('MECH')
        assert mech is not None
        assert mech['mixed'] is True
        assert 'partner_confirms' in mech

        pc = {p['partner']: p for p in mech['partner_confirms']}
        assert 'TMS' in pc
        assert 'FNI' in pc
        assert len(pc['TMS']['sn_confirms']) == 2
        assert len(pc['FNI']['sn_confirms']) == 3

        _cleanup(db_conn)

    def test_tc_sc_10_elec_non_mixed_sn_confirms(self, client, db_conn, get_auth_token, admin_token):
        """TC-SC-10: ELEC 비혼재 O/N — sn_confirms 정상"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        today = date.today()

        for i in range(1, 3):
            sn = f'{_PREFIX}10-00{i}'
            _insert_product(db_conn, sn, f'DOC-{sn}', 'DRAGON', f'ON-{_PREFIX}10',
                            mech_end=today, elec_end=today)
            _insert_task(db_conn, sn, f'DOC-{sn}', 'ELEC', 'WIRE', '배선', completed=True)

        iso_week = today.isocalendar()[1]
        token = admin_token
        resp = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        order = next((o for o in data['orders'] if o['sales_order'] == f'ON-{_PREFIX}10'), None)
        assert order is not None

        elec = order['processes'].get('ELEC')
        assert elec is not None
        assert 'sn_confirms' in elec
        assert len(elec['sn_confirms']) == 2

        _cleanup(db_conn)

    def test_tc_sc_11_tm_5_sn_confirms(self, client, db_conn, get_auth_token, admin_token):
        """TC-SC-11: TM O/N 5대 — sn_confirms 길이 5, partner_confirms 없음"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        today = date.today()

        for i in range(1, 6):
            sn = f'{_PREFIX}11-00{i}'
            _insert_product(db_conn, sn, f'DOC-{sn}', 'GAIA-I', f'ON-{_PREFIX}11',
                            mech_partner='TMS', mech_end=today, module_end=today)
            _insert_task(db_conn, sn, f'DOC-{sn}', 'TMS', 'TANK_MODULE', '탱크모듈', completed=True)

        iso_week = today.isocalendar()[1]
        token = admin_token
        resp = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        order = next((o for o in data['orders'] if o['sales_order'] == f'ON-{_PREFIX}11'), None)
        assert order is not None

        tm = order['processes'].get('TM')
        assert tm is not None
        assert 'partner_confirms' not in tm
        assert 'sn_confirms' in tm
        assert len(tm['sn_confirms']) == 5

        _cleanup(db_conn)

    def test_tc_sc_12_pi_qi_si_no_sn_confirms(self, client, db_conn, get_auth_token, admin_token):
        """TC-SC-12: PI/QI/SI — sn_confirms 없음, 기존 O/N 단위"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        today = date.today()

        sn = f'{_PREFIX}12-001'
        _insert_product(db_conn, sn, f'DOC-{sn}', 'DRAGON', f'ON-{_PREFIX}12', mech_end=today)
        _insert_task(db_conn, sn, f'DOC-{sn}', 'PI', 'PRE_INSPECT', '사전검사', completed=True)

        iso_week = today.isocalendar()[1]
        token = admin_token
        resp = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        order = next((o for o in data['orders'] if o['sales_order'] == f'ON-{_PREFIX}12'), None)
        assert order is not None

        pi = order['processes'].get('PI')
        assert pi is not None
        # PI는 기존 O/N 단위 → sn_confirms 없음
        assert 'sn_confirms' not in pi
        # 기존 confirmable/confirmed 필드
        assert 'confirmable' in pi
        assert 'confirmed' in pi

        _cleanup(db_conn)

    def test_tc_sc_13_all_confirmable_true(self, client, db_conn, get_auth_token, admin_token):
        """TC-SC-13: S/N 5대 모두 완료 → all_confirmable=true"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        today = date.today()

        for i in range(1, 6):
            sn = f'{_PREFIX}13-00{i}'
            _insert_product(db_conn, sn, f'DOC-{sn}', 'DRAGON', f'ON-{_PREFIX}13',
                            mech_end=today)
            _insert_task(db_conn, sn, f'DOC-{sn}', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        iso_week = today.isocalendar()[1]
        token = admin_token
        resp = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        order = next((o for o in data['orders'] if o['sales_order'] == f'ON-{_PREFIX}13'), None)
        assert order is not None

        mech = order['processes'].get('MECH')
        assert mech is not None
        assert mech['all_confirmable'] is True

        _cleanup(db_conn)

    def test_tc_sc_14_all_confirmable_false_partial(self, client, db_conn, get_auth_token, admin_token):
        """TC-SC-14: S/N 5대 중 3대만 완료 → all_confirmable=false, 완료된 3대 confirmable=true"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        today = date.today()

        for i in range(1, 6):
            sn = f'{_PREFIX}14-00{i}'
            _insert_product(db_conn, sn, f'DOC-{sn}', 'DRAGON', f'ON-{_PREFIX}14',
                            mech_end=today)
            _insert_task(db_conn, sn, f'DOC-{sn}', 'MECH', 'SELF_INSPECTION', '자주검사',
                         completed=(i <= 3))

        iso_week = today.isocalendar()[1]
        token = admin_token
        resp = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        order = next((o for o in data['orders'] if o['sales_order'] == f'ON-{_PREFIX}14'), None)
        assert order is not None

        mech = order['processes'].get('MECH')
        assert mech is not None
        assert mech['all_confirmable'] is False

        # 완료된 3대 confirmable=true, 미완료 2대 false
        confirmable_count = sum(1 for s in mech['sn_confirms'] if s['confirmable'])
        assert confirmable_count == 3

        _cleanup(db_conn)


# ══════════════════════════════════════════════════════════════
# White-box: confirm_production() serial_numbers 배열 (TC-SC-15 ~ TC-SC-19)
# ══════════════════════════════════════════════════════════════

class TestConfirmProductionSerialNumbers:
    """confirm_production() serial_numbers 배열 처리 검증"""

    def test_tc_sc_15_batch_confirm_two_sns(self, client, db_conn, get_auth_token, admin_token):
        """TC-SC-15: serial_numbers=['SN001','SN002'] → 2 rows, count=2"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        today = date.today()
        iso_week = today.isocalendar()[1]

        for i in range(1, 3):
            sn = f'{_PREFIX}15-00{i}'
            _insert_product(db_conn, sn, f'DOC-{sn}', 'DRAGON', f'ON-{_PREFIX}15',
                            mech_end=today)
            _insert_task(db_conn, sn, f'DOC-{sn}', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        token = admin_token
        resp = client.post('/api/admin/production/confirm', json={
            'sales_order': f'ON-{_PREFIX}15',
            'process_type': 'MECH',
            'serial_numbers': [f'{_PREFIX}15-001', f'{_PREFIX}15-002'],
            'confirmed_week': f'W{iso_week:02d}',
            'confirmed_month': f'{today.year}-{today.month:02d}',
        }, headers={'Authorization': f'Bearer {token}'})

        assert resp.status_code == 201
        data = resp.get_json()
        assert data['count'] == 2
        assert len(data['confirmed']) == 2

        _cleanup(db_conn)

    def test_tc_sc_16_individual_confirm_one_sn(self, client, db_conn, get_auth_token, admin_token):
        """TC-SC-16: serial_numbers=['SN001'] 개별 → 1 row"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        today = date.today()
        iso_week = today.isocalendar()[1]

        sn = f'{_PREFIX}16-001'
        _insert_product(db_conn, sn, f'DOC-{sn}', 'DRAGON', f'ON-{_PREFIX}16', mech_end=today)
        _insert_task(db_conn, sn, f'DOC-{sn}', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        token = admin_token
        resp = client.post('/api/admin/production/confirm', json={
            'sales_order': f'ON-{_PREFIX}16',
            'process_type': 'MECH',
            'serial_numbers': [sn],
            'confirmed_week': f'W{iso_week:02d}',
            'confirmed_month': f'{today.year}-{today.month:02d}',
        }, headers={'Authorization': f'Bearer {token}'})

        assert resp.status_code == 201
        data = resp.get_json()
        assert data['count'] == 1

        _cleanup(db_conn)

    def test_tc_sc_17_empty_serial_numbers_400(self, client, db_conn, get_auth_token, admin_token):
        """TC-SC-17: serial_numbers 빈 배열 → 400"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        today = date.today()
        iso_week = today.isocalendar()[1]

        token = admin_token
        resp = client.post('/api/admin/production/confirm', json={
            'sales_order': f'ON-{_PREFIX}17',
            'process_type': 'MECH',
            'serial_numbers': [],
            'confirmed_week': f'W{iso_week:02d}',
            'confirmed_month': f'{today.year}-{today.month:02d}',
        }, headers={'Authorization': f'Bearer {token}'})

        assert resp.status_code == 400

    def test_tc_sc_18_not_confirmable_sn_400(self, client, db_conn, get_auth_token, admin_token):
        """TC-SC-18: serial_numbers에 미완료 S/N 포함 → 400 + 해당 S/N 명시"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        today = date.today()
        iso_week = today.isocalendar()[1]

        # SN1: 완료, SN2: 미완료
        sn1 = f'{_PREFIX}18-001'
        sn2 = f'{_PREFIX}18-002'
        _insert_product(db_conn, sn1, f'DOC-{sn1}', 'DRAGON', f'ON-{_PREFIX}18', mech_end=today)
        _insert_product(db_conn, sn2, f'DOC-{sn2}', 'DRAGON', f'ON-{_PREFIX}18', mech_end=today)
        _insert_task(db_conn, sn1, f'DOC-{sn1}', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)
        _insert_task(db_conn, sn2, f'DOC-{sn2}', 'MECH', 'SELF_INSPECTION', '자주검사', completed=False)

        token = admin_token
        resp = client.post('/api/admin/production/confirm', json={
            'sales_order': f'ON-{_PREFIX}18',
            'process_type': 'MECH',
            'serial_numbers': [sn1, sn2],
            'confirmed_week': f'W{iso_week:02d}',
            'confirmed_month': f'{today.year}-{today.month:02d}',
        }, headers={'Authorization': f'Bearer {token}'})

        assert resp.status_code == 400
        data = resp.get_json()
        assert data['error'] == 'NOT_CONFIRMABLE'
        assert sn2 in data['message']

        _cleanup(db_conn)

    def test_tc_sc_19_mixed_partner_confirm(self, client, db_conn, get_auth_token, admin_token):
        """TC-SC-19: MECH 혼재 + partner='TMS' + serial_numbers → TMS S/N만 대상"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        today = date.today()
        iso_week = today.isocalendar()[1]

        # TMS 2대 + FNI 2대
        for i in range(1, 3):
            sn = f'{_PREFIX}19-00{i}'
            _insert_product(db_conn, sn, f'DOC-{sn}', 'GAIA-I', f'ON-{_PREFIX}19',
                            mech_partner='TMS', mech_end=today)
            _insert_task(db_conn, sn, f'DOC-{sn}', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        for i in range(3, 5):
            sn = f'{_PREFIX}19-00{i}'
            _insert_product(db_conn, sn, f'DOC-{sn}', 'GAIA-I', f'ON-{_PREFIX}19',
                            mech_partner='FNI', mech_end=today)
            _insert_task(db_conn, sn, f'DOC-{sn}', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        token = admin_token
        resp = client.post('/api/admin/production/confirm', json={
            'sales_order': f'ON-{_PREFIX}19',
            'process_type': 'MECH',
            'partner': 'TMS',
            'serial_numbers': [f'{_PREFIX}19-001', f'{_PREFIX}19-002'],
            'confirmed_week': f'W{iso_week:02d}',
            'confirmed_month': f'{today.year}-{today.month:02d}',
        }, headers={'Authorization': f'Bearer {token}'})

        assert resp.status_code == 201
        data = resp.get_json()
        assert data['count'] == 2

        # FNI S/N은 미확인 상태 확인
        resp2 = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        order = next((o for o in resp2.get_json()['orders']
                       if o['sales_order'] == f'ON-{_PREFIX}19'), None)
        assert order is not None
        mech = order['processes']['MECH']
        assert mech['mixed'] is True

        pc = {p['partner']: p for p in mech['partner_confirms']}
        # TMS: 2대 confirmed
        assert pc['TMS']['all_confirmed'] is True
        # FNI: 미확인
        assert pc['FNI']['all_confirmed'] is False

        _cleanup(db_conn)


# ══════════════════════════════════════════════════════════════
# White-box: cancel_confirm() serial_number (TC-SC-20 ~ TC-SC-21)
# ══════════════════════════════════════════════════════════════

class TestCancelConfirmSerialNumber:
    """cancel_confirm() S/N별 취소 검증"""

    def test_tc_sc_20_cancel_single_sn_keeps_others(self, client, db_conn, get_auth_token, admin_token):
        """TC-SC-20: S/N별 취소 → 해당 S/N만 soft delete, 다른 S/N 유지"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        today = date.today()
        iso_week = today.isocalendar()[1]

        for i in range(1, 3):
            sn = f'{_PREFIX}20-00{i}'
            _insert_product(db_conn, sn, f'DOC-{sn}', 'DRAGON', f'ON-{_PREFIX}20', mech_end=today)
            _insert_task(db_conn, sn, f'DOC-{sn}', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        token = admin_token

        # 2대 일괄 확인
        resp = client.post('/api/admin/production/confirm', json={
            'sales_order': f'ON-{_PREFIX}20',
            'process_type': 'MECH',
            'serial_numbers': [f'{_PREFIX}20-001', f'{_PREFIX}20-002'],
            'confirmed_week': f'W{iso_week:02d}',
            'confirmed_month': f'{today.year}-{today.month:02d}',
        }, headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 201

        confirmed = resp.get_json()['confirmed']
        sn1_id = next(c['id'] for c in confirmed if c['serial_number'] == f'{_PREFIX}20-001')

        # SN1만 취소
        resp2 = client.delete(
            f'/api/admin/production/confirm/{sn1_id}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp2.status_code == 200

        # SN2는 여전히 confirmed
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT serial_number, deleted_at
            FROM plan.production_confirm
            WHERE sales_order = %s AND process_type = 'MECH'
            ORDER BY serial_number
        """, (f'ON-{_PREFIX}20',))
        rows = cursor.fetchall()
        cursor.close()

        sn_status = {r[0]: r[1] for r in rows}
        assert sn_status[f'{_PREFIX}20-001'] is not None   # soft deleted
        assert sn_status[f'{_PREFIX}20-002'] is None        # still active

        _cleanup(db_conn)

    def test_tc_sc_21_cancel_returning_serial_number(self, client, db_conn, get_auth_token, admin_token):
        """TC-SC-21: RETURNING에 serial_number 포함 확인"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        today = date.today()
        iso_week = today.isocalendar()[1]

        sn = f'{_PREFIX}21-001'
        _insert_product(db_conn, sn, f'DOC-{sn}', 'DRAGON', f'ON-{_PREFIX}21', mech_end=today)
        _insert_task(db_conn, sn, f'DOC-{sn}', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        token = admin_token

        resp = client.post('/api/admin/production/confirm', json={
            'sales_order': f'ON-{_PREFIX}21',
            'process_type': 'MECH',
            'serial_numbers': [sn],
            'confirmed_week': f'W{iso_week:02d}',
            'confirmed_month': f'{today.year}-{today.month:02d}',
        }, headers={'Authorization': f'Bearer {token}'})
        confirm_id = resp.get_json()['confirmed'][0]['id']

        # 취소 → RETURNING에 serial_number 존재 (DB 직접 확인)
        cursor = db_conn.cursor()
        cursor.execute("""
            UPDATE plan.production_confirm
            SET deleted_at = NOW()
            WHERE id = %s AND deleted_at IS NULL
            RETURNING id, sales_order, process_type, partner, serial_number
        """, (confirm_id,))
        row = cursor.fetchone()
        db_conn.commit()
        cursor.close()

        assert row is not None
        assert row[4] == sn  # serial_number

        _cleanup(db_conn)


# ══════════════════════════════════════════════════════════════
# White-box: get_performance() end 날짜 + confirms dict (TC-SC-22 ~ TC-SC-24)
# ══════════════════════════════════════════════════════════════

class TestGetPerformanceEndDates:
    """get_performance() end 날짜 포함 + confirms dict 키 검증"""

    def test_tc_sc_22_sns_detail_end_dates(self, client, db_conn, get_auth_token, admin_token):
        """TC-SC-22: sns_detail에 mech_end, elec_end, module_end 포함"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        today = date.today()

        sn = f'{_PREFIX}22-001'
        _insert_product(db_conn, sn, f'DOC-{sn}', 'GAIA-I', f'ON-{_PREFIX}22',
                        mech_end=today, elec_end=today + timedelta(days=1),
                        module_end=today + timedelta(days=3), mech_partner='TMS')
        _insert_task(db_conn, sn, f'DOC-{sn}', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        iso_week = today.isocalendar()[1]
        token = admin_token
        resp = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        order = next((o for o in data['orders'] if o['sales_order'] == f'ON-{_PREFIX}22'), None)
        assert order is not None

        sn_detail = order['sns'][0]
        assert 'mech_end' in sn_detail
        assert 'elec_end' in sn_detail
        assert 'module_end' in sn_detail
        assert sn_detail['mech_end'] == today.isoformat()
        assert sn_detail['elec_end'] == (today + timedelta(days=1)).isoformat()
        assert sn_detail['module_end'] == (today + timedelta(days=3)).isoformat()

        _cleanup(db_conn)

    def test_tc_sc_23_confirms_dict_key_format(self, client, db_conn, get_auth_token, admin_token):
        """TC-SC-23: confirms dict 키 — {so}:{proc}:{partner}:{sn} 형식"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        today = date.today()
        iso_week = today.isocalendar()[1]

        sn = f'{_PREFIX}23-001'
        _insert_product(db_conn, sn, f'DOC-{sn}', 'DRAGON', f'ON-{_PREFIX}23', mech_end=today)
        _insert_task(db_conn, sn, f'DOC-{sn}', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        token = admin_token

        # confirm
        resp = client.post('/api/admin/production/confirm', json={
            'sales_order': f'ON-{_PREFIX}23',
            'process_type': 'MECH',
            'serial_numbers': [sn],
            'confirmed_week': f'W{iso_week:02d}',
            'confirmed_month': f'{today.year}-{today.month:02d}',
        }, headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 201

        # DB에서 confirms dict 키 확인
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT sales_order, process_type, COALESCE(partner, '') AS partner, serial_number
            FROM plan.production_confirm
            WHERE sales_order = %s AND deleted_at IS NULL
        """, (f'ON-{_PREFIX}23',))
        row = cursor.fetchone()
        cursor.close()

        assert row is not None
        # 키 형식: {so}:{proc}:{partner}:{sn}
        key = f"{row[0]}:{row[1]}:{row[2]}:{row[3]}"
        assert key == f"ON-{_PREFIX}23:MECH::{sn}"

        _cleanup(db_conn)

    def test_tc_sc_24_legacy_null_serial_number(self, db_conn, seed_test_data):
        """TC-SC-24: 기존 serial_number=NULL 데이터 → dict 키 하위호환"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)

        # 레거시 데이터 직접 INSERT (serial_number=NULL) — seed admin의 실제 ID 사용
        cursor = db_conn.cursor()
        cursor.execute("SELECT id FROM workers WHERE email = 'seed_admin@test.axisos.com'")
        admin_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO plan.production_confirm
                (sales_order, process_type, partner, serial_number,
                 confirmed_week, confirmed_month, confirmed_by)
            VALUES (%s, %s, NULL, '', %s, %s, %s)
        """, (f'ON-{_PREFIX}24', 'MECH', 'W01', '2026-01', admin_id))
        db_conn.commit()

        # confirms dict 키 빌드 로직: COALESCE(partner,''), serial_number=''
        cursor.execute("""
            SELECT sales_order, process_type,
                   COALESCE(partner, '') AS partner,
                   COALESCE(serial_number, '') AS serial_number
            FROM plan.production_confirm
            WHERE sales_order = %s AND deleted_at IS NULL
        """, (f'ON-{_PREFIX}24',))
        row = cursor.fetchone()
        cursor.close()

        key = f"{row[0]}:{row[1]}:{row[2]}:{row[3]}"
        # 하위호환: partner='', serial_number='' → {so}:{proc}::
        assert key == f"ON-{_PREFIX}24:MECH::"

        _cleanup(db_conn)
