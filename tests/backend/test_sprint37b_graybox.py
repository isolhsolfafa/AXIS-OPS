"""
Sprint 37-B: S/N별 실적확인 + TM 혼재 제거 + End 필터 (#38)
Gray-box 테스트 5건 (TC-SG-01 ~ TC-SG-05)

- Migration 032 스키마 검증
- S/N별 confirm → cancel → 재confirm E2E
- 혼재 O/N 복합 시나리오
- TM S/N 부분 확인
- duplicate INSERT unique constraint
"""

import sys
from pathlib import Path

_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest
from datetime import date, timedelta


_PREFIX = 'SN-SG37B-'


def _insert_product(db_conn, serial_number, qr_doc_id, model, sales_order,
                    mech_start=None, mech_partner='GST', elec_partner='GST',
                    mech_end=None, elec_end=None, module_end=None):
    """테스트용 제품 + QR 등록"""
    if mech_start is None:
        mech_start = date.today()
    if mech_end is None:
        mech_end = mech_start
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO plan.product_info
            (serial_number, model, sales_order, mech_start, mech_end,
             elec_end, module_end, mech_partner, elec_partner)
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
# Gray-box: Migration 032 스키마 검증 (TC-SG-01)
# ══════════════════════════════════════════════════════════════

class TestMigration032Schema:
    """Migration 032 적용 후 스키마 검증"""

    def test_tc_sg_01_serial_number_column_exists(self, db_conn):
        """TC-SG-01: serial_number 컬럼 존재 + unique index 정상"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        cursor = db_conn.cursor()

        # serial_number 컬럼 존재 확인
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = 'plan' AND table_name = 'production_confirm'
              AND column_name = 'serial_number'
        """)
        row = cursor.fetchone()
        assert row is not None, "serial_number 컬럼이 없습니다"
        assert row[1] == 'character varying'

        # unique index 존재 확인
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'production_confirm'
              AND indexdef LIKE '%serial_number%'
              AND indexdef LIKE '%UNIQUE%'
        """)
        idx_row = cursor.fetchone()
        assert idx_row is not None, "serial_number 포함 unique index가 없습니다"

        cursor.close()


# ══════════════════════════════════════════════════════════════
# Gray-box: E2E 흐름 (TC-SG-02 ~ TC-SG-04)
# ══════════════════════════════════════════════════════════════

class TestE2EFlow:
    """S/N별 confirm → cancel → 재confirm E2E"""

    def test_tc_sg_02_confirm_cancel_reconfirm(self, client, db_conn, get_auth_token):
        """TC-SG-02: S/N별 confirm → cancel → 재confirm 전체 흐름"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        today = date.today()
        iso_week = today.isocalendar()[1]

        sn = f'{_PREFIX}SG02-001'
        _insert_product(db_conn, sn, f'DOC-{sn}', 'DRAGON', f'ON-{_PREFIX}SG02', mech_end=today)
        _insert_task(db_conn, sn, f'DOC-{sn}', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        token = get_auth_token(819, role='ADMIN')
        body = {
            'sales_order': f'ON-{_PREFIX}SG02',
            'process_type': 'MECH',
            'serial_numbers': [sn],
            'confirmed_week': f'W{iso_week:02d}',
            'confirmed_month': f'{today.year}-{today.month:02d}',
        }

        # 1. Confirm
        resp1 = client.post('/api/admin/production/confirm', json=body,
                            headers={'Authorization': f'Bearer {token}'})
        assert resp1.status_code == 201
        confirm_id = resp1.get_json()['confirmed'][0]['id']

        # 2. Performance에서 confirmed=true 확인
        resp_perf = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        order = next(o for o in resp_perf.get_json()['orders']
                     if o['sales_order'] == f'ON-{_PREFIX}SG02')
        mech = order['processes']['MECH']
        assert mech['sn_confirms'][0]['confirmed'] is True

        # 3. Cancel
        resp2 = client.delete(f'/api/admin/production/confirm/{confirm_id}',
                              headers={'Authorization': f'Bearer {token}'})
        assert resp2.status_code == 200

        # 4. Performance에서 confirmed=false 확인
        resp_perf2 = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        order2 = next(o for o in resp_perf2.get_json()['orders']
                      if o['sales_order'] == f'ON-{_PREFIX}SG02')
        mech2 = order2['processes']['MECH']
        assert mech2['sn_confirms'][0]['confirmed'] is False

        # 5. Re-confirm
        resp3 = client.post('/api/admin/production/confirm', json=body,
                            headers={'Authorization': f'Bearer {token}'})
        assert resp3.status_code == 201

        _cleanup(db_conn)

    def test_tc_sg_03_mixed_on_partial_confirm(self, client, db_conn, get_auth_token):
        """TC-SG-03: 혼재 O/N — TMS 2대 일괄 → FNI 1대 개별 → 응답 검증"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        today = date.today()
        iso_week = today.isocalendar()[1]

        # TMS 2대
        for i in range(1, 3):
            sn = f'{_PREFIX}SG03-00{i}'
            _insert_product(db_conn, sn, f'DOC-{sn}', 'GAIA-I', f'ON-{_PREFIX}SG03',
                            mech_partner='TMS', mech_end=today)
            _insert_task(db_conn, sn, f'DOC-{sn}', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        # FNI 3대
        for i in range(3, 6):
            sn = f'{_PREFIX}SG03-00{i}'
            _insert_product(db_conn, sn, f'DOC-{sn}', 'GAIA-I', f'ON-{_PREFIX}SG03',
                            mech_partner='FNI', mech_end=today)
            _insert_task(db_conn, sn, f'DOC-{sn}', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        token = get_auth_token(819, role='ADMIN')

        # TMS 2대 일괄확인
        resp1 = client.post('/api/admin/production/confirm', json={
            'sales_order': f'ON-{_PREFIX}SG03',
            'process_type': 'MECH',
            'partner': 'TMS',
            'serial_numbers': [f'{_PREFIX}SG03-001', f'{_PREFIX}SG03-002'],
            'confirmed_week': f'W{iso_week:02d}',
            'confirmed_month': f'{today.year}-{today.month:02d}',
        }, headers={'Authorization': f'Bearer {token}'})
        assert resp1.status_code == 201

        # FNI 1대 개별확인
        resp2 = client.post('/api/admin/production/confirm', json={
            'sales_order': f'ON-{_PREFIX}SG03',
            'process_type': 'MECH',
            'partner': 'FNI',
            'serial_numbers': [f'{_PREFIX}SG03-003'],
            'confirmed_week': f'W{iso_week:02d}',
            'confirmed_month': f'{today.year}-{today.month:02d}',
        }, headers={'Authorization': f'Bearer {token}'})
        assert resp2.status_code == 201

        # Performance 검증
        resp_perf = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        order = next(o for o in resp_perf.get_json()['orders']
                     if o['sales_order'] == f'ON-{_PREFIX}SG03')
        mech = order['processes']['MECH']
        pc = {p['partner']: p for p in mech['partner_confirms']}

        # TMS 2대 all confirmed
        assert pc['TMS']['all_confirmed'] is True
        assert len(pc['TMS']['sn_confirms']) == 2

        # FNI: 1대 confirmed + 2대 미확인
        assert pc['FNI']['all_confirmed'] is False
        fni_confirmed = sum(1 for s in pc['FNI']['sn_confirms'] if s['confirmed'])
        assert fni_confirmed == 1

        _cleanup(db_conn)

    def test_tc_sg_04_tm_partial_confirm_no_fni(self, client, db_conn, get_auth_token):
        """TC-SG-04: TM 5대 중 3대 확인 → 3대 confirmed + 2대 미확인 + FNI 미포함"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        today = date.today()
        iso_week = today.isocalendar()[1]

        # 5대 (mech_partner 다양 — TMS 3대 + FNI 2대, 하지만 TM은 혼재 무관)
        for i in range(1, 4):
            sn = f'{_PREFIX}SG04-00{i}'
            _insert_product(db_conn, sn, f'DOC-{sn}', 'GAIA-I', f'ON-{_PREFIX}SG04',
                            mech_partner='TMS', mech_end=today, module_end=today)
            _insert_task(db_conn, sn, f'DOC-{sn}', 'TMS', 'TANK_MODULE', '탱크모듈', completed=True)

        for i in range(4, 6):
            sn = f'{_PREFIX}SG04-00{i}'
            _insert_product(db_conn, sn, f'DOC-{sn}', 'GAIA-I', f'ON-{_PREFIX}SG04',
                            mech_partner='FNI', mech_end=today)
            # FNI S/N에는 TMS tasks 없음 → TM에 안 나타남

        token = get_auth_token(819, role='ADMIN')

        # TM 3대 개별확인
        resp = client.post('/api/admin/production/confirm', json={
            'sales_order': f'ON-{_PREFIX}SG04',
            'process_type': 'TM',
            'serial_numbers': [f'{_PREFIX}SG04-001', f'{_PREFIX}SG04-002', f'{_PREFIX}SG04-003'],
            'confirmed_week': f'W{iso_week:02d}',
            'confirmed_month': f'{today.year}-{today.month:02d}',
        }, headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 201
        assert resp.get_json()['count'] == 3

        # Performance 검증
        resp_perf = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        order = next(o for o in resp_perf.get_json()['orders']
                     if o['sales_order'] == f'ON-{_PREFIX}SG04')

        tm = order['processes'].get('TM')
        assert tm is not None
        # TM에 partner_confirms 없음 (TM 혼재 제거)
        assert 'partner_confirms' not in tm
        # sn_confirms에 TMS tasks 있는 3대만
        assert len(tm['sn_confirms']) == 3
        # 3대 모두 confirmed
        assert all(s['confirmed'] for s in tm['sn_confirms'])

        _cleanup(db_conn)


# ══════════════════════════════════════════════════════════════
# Gray-box: duplicate INSERT (TC-SG-05)
# ══════════════════════════════════════════════════════════════

class TestDuplicateConfirm:
    """duplicate INSERT unique constraint 처리"""

    def test_tc_sg_05_duplicate_confirm_409(self, client, db_conn, get_auth_token):
        """TC-SG-05: 동일 sales_order+process_type+partner+serial_number → 409"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn)
        today = date.today()
        iso_week = today.isocalendar()[1]

        sn = f'{_PREFIX}SG05-001'
        _insert_product(db_conn, sn, f'DOC-{sn}', 'DRAGON', f'ON-{_PREFIX}SG05', mech_end=today)
        _insert_task(db_conn, sn, f'DOC-{sn}', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        token = get_auth_token(819, role='ADMIN')
        body = {
            'sales_order': f'ON-{_PREFIX}SG05',
            'process_type': 'MECH',
            'serial_numbers': [sn],
            'confirmed_week': f'W{iso_week:02d}',
            'confirmed_month': f'{today.year}-{today.month:02d}',
        }

        # 첫 번째 확인
        resp1 = client.post('/api/admin/production/confirm', json=body,
                            headers={'Authorization': f'Bearer {token}'})
        assert resp1.status_code == 201

        # 중복 확인
        resp2 = client.post('/api/admin/production/confirm', json=body,
                            headers={'Authorization': f'Bearer {token}'})
        assert resp2.status_code == 409

        _cleanup(db_conn)
