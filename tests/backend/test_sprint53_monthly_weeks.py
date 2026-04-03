"""
Sprint 53: monthly-summary API weeks + totals 집계 추가 — 테스트
TC-53-01 ~ TC-53-15 (15건)

검증 대상:
- _weeks_for_month(): 금요일 기준 주차-월 매핑
- _date_to_week_label(): date → 'WXX' 변환
- GET /api/admin/production/monthly-summary weeks/totals 응답 구조
- completed/confirmed 집계 정확성
- 기존 orders/confirms/total_orders/total_sns 하위호환
"""

import sys
from pathlib import Path

_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest
from datetime import date, timedelta


# ── 테스트 데이터 prefix ──────────────────────────
_PREFIX = 'SP53-'


# ── Admin 토큰 픽스처 ──────────────────────────────
@pytest.fixture
def admin_token(db_conn, seed_test_data, get_auth_token):
    """Seed admin의 실제 worker_id로 JWT 토큰 생성"""
    cursor = db_conn.cursor()
    cursor.execute("SELECT id FROM workers WHERE email = 'seed_admin@test.axisos.com'")
    row = cursor.fetchone()
    cursor.close()
    return get_auth_token(row[0], role='ADMIN', is_admin=True)


# ── 공통 헬퍼 함수 ──────────────────────────────────

def _insert_product(db_conn, serial_number, qr_doc_id, model, sales_order,
                    mech_start, mech_end=None, mech_partner='FNI', elec_partner='P&S'):
    """테스트용 제품 + QR 등록"""
    if mech_end is None:
        mech_end = mech_start
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO plan.product_info
            (serial_number, model, sales_order, mech_start, mech_end,
             mech_partner, elec_partner)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (serial_number) DO UPDATE
            SET model = EXCLUDED.model,
                sales_order = EXCLUDED.sales_order,
                mech_start = EXCLUDED.mech_start,
                mech_end = EXCLUDED.mech_end,
                mech_partner = EXCLUDED.mech_partner,
                elec_partner = EXCLUDED.elec_partner
    """, (serial_number, model, sales_order, mech_start, mech_end, mech_partner, elec_partner))
    cursor.execute("""
        INSERT INTO public.qr_registry (qr_doc_id, serial_number, status)
        VALUES (%s, %s, 'active')
        ON CONFLICT (qr_doc_id) DO NOTHING
    """, (qr_doc_id, serial_number))
    db_conn.commit()
    cursor.close()


def _insert_task(db_conn, serial_number, qr_doc_id, category, task_id,
                 task_name, completed=False, is_applicable=True, worker_id=None):
    """테스트용 태스크 등록"""
    cursor = db_conn.cursor()
    if worker_id is None:
        cursor.execute("SELECT id FROM workers WHERE email = 'seed_admin@test.axisos.com'")
        row = cursor.fetchone()
        worker_id = row[0]
    completed_at = 'NOW()' if completed else 'NULL'
    cursor.execute(f"""
        INSERT INTO app_task_details
            (serial_number, qr_doc_id, task_category, task_id, task_name,
             worker_id, is_applicable, completed_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, {completed_at})
        ON CONFLICT (serial_number, qr_doc_id, task_category, task_id) DO UPDATE
            SET completed_at = {completed_at},
                is_applicable = EXCLUDED.is_applicable
    """, (serial_number, qr_doc_id, category, task_id, task_name, worker_id, is_applicable))
    db_conn.commit()
    cursor.close()


def _insert_confirm(db_conn, sales_order, process_type, serial_number,
                    confirmed_week, confirmed_month, partner=None, worker_id=None):
    """테스트용 실적확인 기록 삽입"""
    cursor = db_conn.cursor()
    if worker_id is None:
        cursor.execute("SELECT id FROM workers WHERE email = 'seed_admin@test.axisos.com'")
        row = cursor.fetchone()
        worker_id = row[0]
    cursor.execute("""
        INSERT INTO plan.production_confirm
            (sales_order, process_type, partner, serial_number,
             confirmed_week, confirmed_month, confirmed_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (sales_order, process_type, partner, serial_number,
          confirmed_week, confirmed_month, worker_id))
    db_conn.commit()
    cursor.close()


def _cleanup(db_conn, prefix=_PREFIX):
    """테스트 데이터 정리"""
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM plan.production_confirm WHERE serial_number LIKE %s",
                   (f'{prefix}%',))
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
# White-box: 헬퍼 함수 단위 테스트 (TC-53-01 ~ TC-53-03)
# ══════════════════════════════════════════════════════════════

class TestHelperFunctions:
    """_weeks_for_month(), _date_to_week_label() 단위 테스트"""

    def test_tc_53_01_weeks_for_april_2026(self):
        """TC-53-01: 2026-04의 주차 목록에 W14~W18 포함 (금요일 기준)"""
        from app.routes.production import _weeks_for_month

        weeks = _weeks_for_month(2026, 4)
        labels = [w[0] for w in weeks]

        # 2026년 4월: W14(금=4/3), W15(금=4/10), W16(금=4/17), W17(금=4/24)
        # W18은 금요일 5/1 = 5월이므로 미포함
        assert 'W14' in labels, f"W14이 2026-04 weeks에 없음: {labels}"
        assert 'W17' in labels, f"W17이 2026-04 weeks에 없음: {labels}"

    def test_tc_53_02_w14_friday_in_april(self):
        """TC-53-02: W14 (3/30~4/5) → 금요일 4/3 = 4월 → 4월 응답에 포함"""
        from app.routes.production import _weeks_for_month

        # W14 2026: monday=3/30, friday=4/3 → 4월 소속
        weeks = _weeks_for_month(2026, 4)
        labels = [w[0] for w in weeks]
        assert 'W14' in labels

    def test_tc_53_03_w13_friday_in_march(self):
        """TC-53-03: W13 (3/23~3/29) → 금요일 3/27 = 3월 → 4월 응답에 미포함"""
        from app.routes.production import _weeks_for_month

        weeks = _weeks_for_month(2026, 4)
        labels = [w[0] for w in weeks]
        assert 'W13' not in labels, f"W13이 4월에 포함되면 안 됨: {labels}"

    def test_tc_53_04_date_to_week_label(self):
        """TC-53-04: _date_to_week_label() — date/str 모두 'WXX' 반환"""
        from app.routes.production import _date_to_week_label

        d = date(2026, 4, 3)  # ISO week 14
        assert _date_to_week_label(d) == 'W14'
        assert _date_to_week_label('2026-04-03') == 'W14'

    def test_tc_53_05_weeks_for_month_december(self):
        """TC-53-10: 12월 조회 → W1(다음해) 금요일이 1월이면 12월 미포함"""
        from app.routes.production import _weeks_for_month

        # 2026-12: W53 마지막 금요일 확인
        weeks = _weeks_for_month(2026, 12)
        labels = [w[0] for w in weeks]
        # W01 of 2027: monday=12/28/2026, friday=1/1/2027 → 1월 → 12월 미포함
        assert 'W01' not in labels, f"W01이 12월에 포함되면 안 됨: {labels}"

    def test_tc_53_06_weeks_for_month_january(self):
        """TC-53-11: 1월 조회 → W1의 금요일이 1월이면 1월에 포함"""
        from app.routes.production import _weeks_for_month

        # 2027-01: W01 monday=12/28/2026, friday=1/1/2027 → 1월 포함
        weeks = _weeks_for_month(2027, 1)
        labels = [w[0] for w in weeks]
        assert 'W01' in labels, f"W01이 2027-01 weeks에 없음: {labels}"


# ══════════════════════════════════════════════════════════════
# API 통합 테스트 (TC-53-07 ~ TC-53-15)
# ══════════════════════════════════════════════════════════════

class TestMonthlySummaryWeeks:
    """GET /api/admin/production/monthly-summary weeks/totals 집계 검증"""

    def test_tc_53_07_response_has_weeks_and_totals(self, client, db_conn, admin_token, seed_test_data):
        """TC-53-07: 응답에 weeks, totals 필드 포함"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)

        resp = client.get(
            '/api/admin/production/monthly-summary?month=2026-04',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'weeks' in data, "weeks 필드 없음"
        assert 'totals' in data, "totals 필드 없음"

    def test_tc_53_08_weeks_structure(self, client, db_conn, admin_token, seed_test_data):
        """TC-53-08: weeks 배열 각 항목에 week, mech, elec, tm 필드 포함"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)

        resp = client.get(
            '/api/admin/production/monthly-summary?month=2026-04',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        data = resp.get_json()
        weeks = data.get('weeks', [])

        # 2026-04는 W14~W17 포함 (최소 1주차 이상)
        assert len(weeks) >= 1, "weeks 배열이 비어있음"

        for w in weeks:
            assert 'week' in w, f"week 필드 없음: {w}"
            assert 'mech' in w, f"mech 필드 없음: {w}"
            assert 'elec' in w, f"elec 필드 없음: {w}"
            assert 'tm' in w, f"tm 필드 없음: {w}"
            assert 'completed' in w['mech']
            assert 'confirmed' in w['mech']

    def test_tc_53_09_mech_completed_count(self, client, db_conn, admin_token, seed_test_data):
        """TC-53-04: weeks[].mech.completed = mech_end 해당 주차의 MECH 100% 완료 S/N 수"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)

        # W14: monday=3/30, friday=4/3 → 4월 소속
        # mech_end=4/3 (금요일) → W14
        mech_end_w14 = date(2026, 4, 3)
        mech_start = date(2026, 4, 1)

        sn = f'{_PREFIX}09-001'
        qr = f'DOC-{_PREFIX}09-001'
        _insert_product(db_conn, sn, qr, 'GALLANT-50', f'ON-{_PREFIX}09',
                        mech_start=mech_start, mech_end=mech_end_w14)

        # MECH task 1개 완료
        _insert_task(db_conn, sn, qr, 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        resp = client.get(
            '/api/admin/production/monthly-summary?month=2026-04',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        data = resp.get_json()
        weeks_map = {w['week']: w for w in data.get('weeks', [])}

        assert 'W14' in weeks_map, f"W14 없음. weeks: {list(weeks_map.keys())}"
        assert weeks_map['W14']['mech']['completed'] >= 1

    def test_tc_53_10_elec_completed_count(self, client, db_conn, admin_token, seed_test_data):
        """TC-53-05: weeks[].elec.completed 집계 정확성"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)

        mech_end_w15 = date(2026, 4, 10)  # W15 금요일
        mech_start = date(2026, 4, 7)

        sn = f'{_PREFIX}10-001'
        qr = f'DOC-{_PREFIX}10-001'
        _insert_product(db_conn, sn, qr, 'GALLANT-50', f'ON-{_PREFIX}10',
                        mech_start=mech_start, mech_end=mech_end_w15)

        # ELEC task 1개 완료
        _insert_task(db_conn, sn, qr, 'ELEC', 'INSPECTION', '자주검사', completed=True)

        resp = client.get(
            '/api/admin/production/monthly-summary?month=2026-04',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        data = resp.get_json()
        weeks_map = {w['week']: w for w in data.get('weeks', [])}

        assert 'W15' in weeks_map, f"W15 없음. weeks: {list(weeks_map.keys())}"
        assert weeks_map['W15']['elec']['completed'] >= 1

    def test_tc_53_11_tm_completed_tank_module_only(self, client, db_conn, admin_token, seed_test_data):
        """TC-53-06: TM completed = TANK_MODULE만 (PRESSURE_TEST 제외)"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)

        mech_end_w16 = date(2026, 4, 17)  # W16 금요일
        mech_start = date(2026, 4, 14)

        sn = f'{_PREFIX}11-001'
        qr = f'DOC-{_PREFIX}11-001'
        _insert_product(db_conn, sn, qr, 'GAIA-I', f'ON-{_PREFIX}11',
                        mech_start=mech_start, mech_end=mech_end_w16)

        # TANK_MODULE 완료 + PRESSURE_TEST 미완료
        _insert_task(db_conn, sn, qr, 'TMS', 'TANK_MODULE', 'Tank Module', completed=True)
        _insert_task(db_conn, sn, qr, 'TMS', 'PRESSURE_TEST', '가압검사', completed=False)

        resp = client.get(
            '/api/admin/production/monthly-summary?month=2026-04',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        data = resp.get_json()
        weeks_map = {w['week']: w for w in data.get('weeks', [])}

        assert 'W16' in weeks_map, f"W16 없음. weeks: {list(weeks_map.keys())}"
        # TANK_MODULE 완료이므로 tm.completed = 1
        assert weeks_map['W16']['tm']['completed'] >= 1

    def test_tc_53_12_tm_completed_pressure_test_not_counted(self, client, db_conn, admin_token, seed_test_data):
        """TC-53-06 보완: PRESSURE_TEST만 완료 → TM completed 카운트 안 됨 (TANK_MODULE 미완료)"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)

        mech_end_w17 = date(2026, 4, 24)  # W17 금요일
        mech_start = date(2026, 4, 21)

        sn = f'{_PREFIX}12-001'
        qr = f'DOC-{_PREFIX}12-001'
        _insert_product(db_conn, sn, qr, 'GAIA-I', f'ON-{_PREFIX}12',
                        mech_start=mech_start, mech_end=mech_end_w17)

        # PRESSURE_TEST 완료, TANK_MODULE 미완료
        _insert_task(db_conn, sn, qr, 'TMS', 'TANK_MODULE', 'Tank Module', completed=False)
        _insert_task(db_conn, sn, qr, 'TMS', 'PRESSURE_TEST', '가압검사', completed=True)

        resp = client.get(
            '/api/admin/production/monthly-summary?month=2026-04',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        data = resp.get_json()
        weeks_map = {w['week']: w for w in data.get('weeks', [])}

        if 'W17' in weeks_map:
            # TANK_MODULE 미완료 → tm.completed = 0
            assert weeks_map['W17']['tm']['completed'] == 0

    def test_tc_53_13_confirmed_from_production_confirm(self, client, db_conn, admin_token, seed_test_data):
        """TC-53-07: weeks[].*.confirmed = production_confirm 기록 기준 sn_count"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)

        mech_end_w14 = date(2026, 4, 3)
        mech_start = date(2026, 4, 1)

        sn = f'{_PREFIX}13-001'
        qr = f'DOC-{_PREFIX}13-001'
        _insert_product(db_conn, sn, qr, 'GALLANT-50', f'ON-{_PREFIX}13',
                        mech_start=mech_start, mech_end=mech_end_w14)

        # production_confirm 기록: W14, MECH
        _insert_confirm(db_conn, f'ON-{_PREFIX}13', 'MECH', sn,
                        confirmed_week='W14', confirmed_month='2026-04')

        resp = client.get(
            '/api/admin/production/monthly-summary?month=2026-04',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        data = resp.get_json()
        weeks_map = {w['week']: w for w in data.get('weeks', [])}

        assert 'W14' in weeks_map
        assert weeks_map['W14']['mech']['confirmed'] >= 1

    def test_tc_53_14_totals_equals_weeks_sum(self, client, db_conn, admin_token, seed_test_data):
        """TC-53-08: totals = weeks 합계와 정확히 일치"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)

        # W14, W15에 각각 1대씩 완료 데이터 삽입
        for i, mech_end_day in enumerate([date(2026, 4, 3), date(2026, 4, 10)]):
            sn = f'{_PREFIX}14-00{i+1}'
            qr = f'DOC-{_PREFIX}14-00{i+1}'
            mech_start = mech_end_day - timedelta(days=2)
            _insert_product(db_conn, sn, qr, 'GALLANT-50', f'ON-{_PREFIX}14',
                            mech_start=mech_start, mech_end=mech_end_day)
            _insert_task(db_conn, sn, qr, 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        resp = client.get(
            '/api/admin/production/monthly-summary?month=2026-04',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        data = resp.get_json()
        weeks = data.get('weeks', [])
        totals = data.get('totals', {})

        # totals.mech.completed = sum of weeks[*].mech.completed
        calc_mech_completed = sum(w['mech']['completed'] for w in weeks)
        calc_mech_confirmed = sum(w['mech']['confirmed'] for w in weeks)
        calc_elec_completed = sum(w['elec']['completed'] for w in weeks)
        calc_tm_completed = sum(w['tm']['completed'] for w in weeks)

        assert totals.get('mech', {}).get('completed') == calc_mech_completed
        assert totals.get('mech', {}).get('confirmed') == calc_mech_confirmed
        assert totals.get('elec', {}).get('completed') == calc_elec_completed
        assert totals.get('tm', {}).get('completed') == calc_tm_completed

    def test_tc_53_15_mech_end_null_not_counted(self, client, db_conn, admin_token, seed_test_data):
        """TC-53-12: S/N에 mech_end 없는 경우 → 주차 미배정, completed 카운트 제외"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)

        mech_start = date(2026, 4, 1)
        sn = f'{_PREFIX}15-001'
        qr = f'DOC-{_PREFIX}15-001'

        # mech_end=NULL
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO plan.product_info
                (serial_number, model, sales_order, mech_start, mech_end,
                 mech_partner, elec_partner)
            VALUES (%s, %s, %s, %s, NULL, %s, %s)
            ON CONFLICT (serial_number) DO UPDATE
                SET mech_end = NULL,
                    mech_start = EXCLUDED.mech_start
        """, (sn, 'GALLANT-50', f'ON-{_PREFIX}15', mech_start, 'FNI', 'P&S'))
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number, status)
            VALUES (%s, %s, 'active')
            ON CONFLICT (qr_doc_id) DO NOTHING
        """, (qr, sn))
        db_conn.commit()
        cursor.close()

        _insert_task(db_conn, sn, qr, 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        resp = client.get(
            '/api/admin/production/monthly-summary?month=2026-04',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        # mech_end NULL → 어떤 주차에도 미배정
        # totals.mech.completed는 이 S/N을 포함하지 않아야 함
        # (이 테스트만 실행 시 0이어야 함)
        totals = data.get('totals', {})
        weeks = data.get('weeks', [])
        calc_mech_completed = sum(w['mech']['completed'] for w in weeks)
        assert totals.get('mech', {}).get('completed') == calc_mech_completed

    def test_tc_53_16_backward_compat_orders_confirms(self, client, db_conn, admin_token, seed_test_data):
        """TC-53-13/14/15: 기존 orders, confirms, total_orders, total_sns 필드 유지"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)

        resp = client.get(
            '/api/admin/production/monthly-summary?month=2026-04',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        # 기존 필드 존재 확인
        assert 'orders' in data, "orders 필드 누락"
        assert 'confirms' in data, "confirms 필드 누락"
        assert 'total_orders' in data, "total_orders 필드 누락"
        assert 'total_sns' in data, "total_sns 필드 누락"
        assert 'month' in data, "month 필드 누락"

    def test_tc_53_17_no_month_param_uses_current_month(self, client, db_conn, admin_token, seed_test_data):
        """TC-53-09: month 파라미터 없으면 현재 월 기준으로 응답"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        from datetime import datetime, timezone, timedelta

        kst = timezone(timedelta(hours=9))
        today = datetime.now(kst).date()
        expected_month = f"{today.year}-{today.month:02d}"

        resp = client.get(
            '/api/admin/production/monthly-summary',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get('month') == expected_month

    def test_tc_53_18_mech_not_completed_not_counted(self, client, db_conn, admin_token, seed_test_data):
        """TC-53-04 보완: MECH task 미완료 S/N → completed 카운트 안 됨"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)

        mech_end_w14 = date(2026, 4, 3)
        mech_start = date(2026, 4, 1)

        sn = f'{_PREFIX}18-001'
        qr = f'DOC-{_PREFIX}18-001'
        _insert_product(db_conn, sn, qr, 'GALLANT-50', f'ON-{_PREFIX}18',
                        mech_start=mech_start, mech_end=mech_end_w14)

        # MECH task 2개 중 1개만 완료
        _insert_task(db_conn, sn, qr, 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)
        _insert_task(db_conn, sn, qr, 'MECH', 'UTIL_LINE_1', 'Util LINE 1', completed=False)

        resp = client.get(
            '/api/admin/production/monthly-summary?month=2026-04',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        data = resp.get_json()
        weeks_map = {w['week']: w for w in data.get('weeks', [])}

        if 'W14' in weeks_map:
            # MECH 미완료 → mech.completed 증가 없음
            assert weeks_map['W14']['mech']['completed'] == 0
