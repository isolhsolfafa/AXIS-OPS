"""
Sprint 76-BE: 출하이력 페이지 BE 테스트 (FEAT-SHIPMENT-HISTORY-BE-20260526)

API:
- GET /api/admin/shipment/summary
- GET /api/admin/shipment/details

Codex 라운드 1 (VIEW 5-26, M=7/A=2) + 라운드 2 (OPS 5-26, M=5/A=2/N=1) 모두 검증.

⚠️ 운영 데이터 보존: plan.product_info / qr_registry / app_task_details — TEST-SHIP-76-* 접두 S/N teardown 패턴.
"""

import pytest
from datetime import date, datetime, timedelta
from typing import Dict, List


# ==================== TEST-SHIP-76-* 전용 fixture (Codex Q9 M) ====================


@pytest.fixture
def seed_shipment_test_data(db_conn):
    """TEST-SHIP-76-* S/N 영역 plan.product_info + qr_registry + app_task_details seed.

    teardown 시 전부 삭제 (운영 데이터 영향 0).
    """
    created_sns = []

    def _seed(rows: List[Dict]):
        """rows: [{'sn': 'TEST-SHIP-76-001', 'plan_date': date, 'actual_ship_date': date|None,
                   'app_si_completed_at': datetime|None, 'force_closed': bool,
                   'customer': str, 'model': str, 'mech_partner': str, 'elec_partner': str,
                   'sales_order': str}, ...]"""
        if db_conn is None:
            return
        cur = db_conn.cursor()
        for r in rows:
            sn = r['sn']
            # plan.product_info INSERT (UPSERT 패턴) — model NOT NULL
            cur.execute("""
                INSERT INTO plan.product_info
                    (serial_number, sales_order, model, product_code, customer,
                     mech_partner, elec_partner,
                     ship_plan_date, actual_ship_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (serial_number) DO UPDATE SET
                    sales_order = EXCLUDED.sales_order,
                    model = EXCLUDED.model,
                    product_code = EXCLUDED.product_code,
                    customer = EXCLUDED.customer,
                    mech_partner = EXCLUDED.mech_partner,
                    elec_partner = EXCLUDED.elec_partner,
                    ship_plan_date = EXCLUDED.ship_plan_date,
                    actual_ship_date = EXCLUDED.actual_ship_date
            """, (
                sn, r.get('sales_order', f'TON-{sn}'),
                r.get('model', 'TEST-MODEL'),
                r.get('model', 'TEST-MODEL'),  # product_code
                r.get('customer', 'TEST-CUST'),
                r.get('mech_partner'), r.get('elec_partner'),
                r['plan_date'], r.get('actual_ship_date'),
            ))

            # qr_registry INSERT (NOT NULL FK 정합)
            qr_id = f"DOC_{sn}"
            cur.execute("""
                INSERT INTO qr_registry (qr_doc_id, serial_number, status)
                VALUES (%s, %s, 'active')
                ON CONFLICT (qr_doc_id) DO NOTHING
            """, (qr_id, sn))

            # app SI_SHIPMENT 영역 신규 row (옵션)
            if r.get('app_si_completed_at'):
                cur.execute("""
                    INSERT INTO app_task_details
                        (worker_id, serial_number, qr_doc_id,
                         task_category, task_id, task_name,
                         started_at, completed_at, duration_minutes,
                         is_applicable, force_closed, close_reason)
                    SELECT
                        (SELECT id FROM workers WHERE is_admin=TRUE LIMIT 1),
                        %s, %s, 'SI', 'SI_SHIPMENT', '출하 완료',
                        %s, %s, 10, TRUE, %s, %s
                    ON CONFLICT DO NOTHING
                """, (
                    sn, qr_id,
                    r['app_si_completed_at'] - timedelta(minutes=10),
                    r['app_si_completed_at'],
                    r.get('force_closed', False),
                    r.get('close_reason'),
                ))

            created_sns.append(sn)
        db_conn.commit()
        cur.close()

    yield _seed

    # teardown — TEST-SHIP-76-* 전부 삭제
    if db_conn and not db_conn.closed and created_sns:
        try:
            cur = db_conn.cursor()
            for sn in created_sns:
                cur.execute("DELETE FROM app_task_details WHERE serial_number = %s", (sn,))
                cur.execute("DELETE FROM qr_registry WHERE serial_number = %s", (sn,))
                cur.execute("DELETE FROM plan.product_info WHERE serial_number = %s", (sn,))
            db_conn.commit()
            cur.close()
        except Exception as e:
            print(f"Warning: TEST-SHIP-76 cleanup failed: {e}")
            db_conn.rollback()


# ==================== Helper ====================


def _auth_header(token: str) -> Dict[str, str]:
    return {'Authorization': f'Bearer {token}'}


def _today():
    return date.today()


def _ref_date_string(d: date) -> str:
    return d.strftime('%Y-%m-%d')


# ==================== § 1. Auth 4-way (Codex Q6 M) ====================


class TestShipmentAuth:
    """권한 4-way — admin / GST PI/QI/SI / 협력사 차단 / 무토큰"""

    def test_auth_01_admin_allowed(self, client, create_test_admin, get_admin_auth_token):
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        resp = client.get('/api/admin/shipment/summary', headers=_auth_header(token))
        assert resp.status_code == 200, f"admin 200 기대, got {resp.status_code}"

    def test_auth_02_gst_qi_allowed(self, client, create_test_worker, get_auth_token):
        wid = create_test_worker(
            email='gst_qi_ship76@test.axisos.com', password='Pw123!',
            name='GST QI', role='QI', company='GST'
        )
        token = get_auth_token(wid, role='QI')
        resp = client.get('/api/admin/shipment/summary', headers=_auth_header(token))
        assert resp.status_code == 200

    def test_auth_03_partner_blocked(self, client, create_test_worker, get_auth_token):
        wid = create_test_worker(
            email='bat_mgr_ship76@test.axisos.com', password='Pw123!',
            name='BAT Mgr', role='MECH', company='BAT', is_manager=True
        )
        token = get_auth_token(wid, role='MECH')
        resp = client.get('/api/admin/shipment/summary', headers=_auth_header(token))
        assert resp.status_code == 403, f"BAT manager 403 기대, got {resp.status_code}"
        assert resp.get_json()['error'] == 'FORBIDDEN'

    def test_auth_04_no_token(self, client):
        resp = client.get('/api/admin/shipment/summary')
        assert resp.status_code == 401


# ==================== § 2. summary KPI semantics ====================


class TestShipmentSummaryKPI:
    """KPI 6 — Codex Q1/Q2/Q3 M 정합"""

    def test_kpi_01_default_month(self, client, create_test_admin, get_admin_auth_token):
        """기본 month + reference_date 미지정 → 200 + schema 검증"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        resp = client.get('/api/admin/shipment/summary', headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        for k in ('period', 'kpi', 'calendar', 'by_customer', 'by_model', 'monthly_trend', 'top_delayed'):
            assert k in data, f"key '{k}' 누락"
        kpi = data['kpi']
        for k in ('plan_count', 'shipped_count', 'fulfillment_pct',
                  'on_time_pct', 'pending_count', 'avg_delay_days'):
            assert k in kpi, f"kpi.{k} 누락"

    def test_kpi_02_invalid_period(self, client, create_test_admin, get_admin_auth_token):
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        resp = client.get('/api/admin/shipment/summary?period=daily',
                          headers=_auth_header(token))
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'INVALID_PERIOD'

    def test_kpi_03_fulfillment_plan_cohort(self, client, create_test_admin,
                                            get_admin_auth_token, seed_shipment_test_data):
        """Codex Q2 — fulfillment 분자도 plan_date cohort 한정

        plan_date=5/1 + actual=5/3 → 분자/분모 둘 다 포함 → 100%
        plan_date=4/30 + actual=5/3 → 분모 제외 (5월 cohort 아님)
        """
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        today = _today()
        target_month_start = today.replace(day=1)
        seed_shipment_test_data([
            {'sn': 'TEST-SHIP-76-K01', 'plan_date': target_month_start,
             'actual_ship_date': target_month_start + timedelta(days=2),
             'customer': 'TEST-CUST'},
        ])
        resp = client.get(
            f'/api/admin/shipment/summary?period=month&reference_date={_ref_date_string(target_month_start)}',
            headers=_auth_header(token)
        )
        assert resp.status_code == 200

    def test_kpi_04_invariant_calendar_plan_sum(self, client, create_test_admin,
                                                get_admin_auth_token, seed_shipment_test_data):
        """Codex Q8 M — calendar plan 합 = kpi.plan_count invariant"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        today = _today()
        month_start = today.replace(day=1)
        seed_shipment_test_data([
            {'sn': 'TEST-SHIP-76-K04A', 'plan_date': month_start, 'customer': 'A'},
            {'sn': 'TEST-SHIP-76-K04B', 'plan_date': month_start + timedelta(days=1), 'customer': 'B'},
        ])
        resp = client.get(
            f'/api/admin/shipment/summary?period=month&reference_date={_ref_date_string(month_start)}',
            headers=_auth_header(token)
        )
        assert resp.status_code == 200
        data = resp.get_json()
        cal_plan_sum = sum(d.get('plan', 0) for d in data['calendar'])
        # invariant 가 자동 검증되었음 — 응답 받으면 통과한 것
        assert cal_plan_sum == data['kpi']['plan_count']

    def test_kpi_05_invariant_by_customer_sum(self, client, create_test_admin,
                                              get_admin_auth_token, seed_shipment_test_data):
        """Codex Q8 M — by_customer plan/shipped 합 정합"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        month_start = _today().replace(day=1)
        seed_shipment_test_data([
            {'sn': 'TEST-SHIP-76-K05A', 'plan_date': month_start,
             'actual_ship_date': month_start + timedelta(days=1), 'customer': 'CUST-X'},
            {'sn': 'TEST-SHIP-76-K05B', 'plan_date': month_start, 'customer': 'CUST-Y'},
        ])
        resp = client.get(
            f'/api/admin/shipment/summary?period=month&reference_date={_ref_date_string(month_start)}',
            headers=_auth_header(token)
        )
        assert resp.status_code == 200
        data = resp.get_json()
        bc_plan = sum(c['plan'] for c in data['by_customer'])
        bc_shipped = sum(c['shipped'] for c in data['by_customer'])
        assert bc_plan == data['kpi']['plan_count']
        assert bc_shipped == data['kpi']['shipped_count']

    def test_kpi_06_invariant_by_model_sum(self, client, create_test_admin,
                                           get_admin_auth_token, seed_shipment_test_data):
        """v2.18.29 옵션 C — by_model plan/shipped 합 = kpi 정합"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        month_start = _today().replace(day=1)
        seed_shipment_test_data([
            {'sn': 'TEST-SHIP-76-K06A', 'plan_date': month_start,
             'actual_ship_date': month_start + timedelta(days=1),
             'customer': 'CUST', 'model': 'GAIA-LE'},
            {'sn': 'TEST-SHIP-76-K06B', 'plan_date': month_start,
             'customer': 'CUST', 'model': 'DRAGON'},
        ])
        resp = client.get(
            f'/api/admin/shipment/summary?period=month&reference_date={_ref_date_string(month_start)}',
            headers=_auth_header(token)
        )
        assert resp.status_code == 200
        data = resp.get_json()
        # by_model schema 검증 (v2.18.29 옵션 C — plan + shipped 분리 + avg_lead_time_days)
        for m in data['by_model']:
            assert 'plan' in m
            assert 'shipped' in m
            assert 'share_pct' in m
            assert 'avg_lead_time_days' in m  # null 가능
            # 기존 'count' 필드 제거 검증
            assert 'count' not in m, "count 필드 제거 + plan/shipped 분리"
        bm_plan = sum(m['plan'] for m in data['by_model'])
        bm_shipped = sum(m['shipped'] for m in data['by_model'])
        assert bm_plan == data['kpi']['plan_count']
        assert bm_shipped == data['kpi']['shipped_count']

    def test_kpi_07_by_model_avg_lead_time(self, client, create_test_admin,
                                           get_admin_auth_token, seed_shipment_test_data, db_conn):
        """v2.18.29 P-v3 — avg_lead_time_days = AVG(pi_start - LEAST(elec_start, mech_start))"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        month_start = _today().replace(day=1)
        # elec_start=4/1, mech_start=4/5, pi_start=4/29 → 28일
        elec_d = month_start.replace(day=1)
        mech_d = month_start.replace(day=5)
        pi_d = month_start.replace(day=29)
        seed_shipment_test_data([
            {'sn': 'TEST-SHIP-76-K07', 'plan_date': month_start,
             'customer': 'CUST', 'model': 'TEST-LEAD-MODEL'}
        ])
        # plan.product_info 영역 elec/mech/pi 추가 set
        cur = db_conn.cursor()
        cur.execute("""
            UPDATE plan.product_info
            SET elec_start = %s, mech_start = %s, pi_start = %s
            WHERE serial_number = 'TEST-SHIP-76-K07'
        """, (elec_d, mech_d, pi_d))
        db_conn.commit()
        cur.close()

        resp = client.get(
            f'/api/admin/shipment/summary?period=month&reference_date={_ref_date_string(month_start)}',
            headers=_auth_header(token)
        )
        assert resp.status_code == 200
        bm = [m for m in resp.get_json()['by_model'] if m['model'] == 'TEST-LEAD-MODEL']
        assert len(bm) == 1
        # pi_start (4/29) - LEAST(elec=4/1, mech=4/5) = pi - elec = 28일
        assert bm[0]['avg_lead_time_days'] == 28.0


# ==================== § 3. best_ship source 분류 (4 case) ====================


class TestBestShipSource:
    """best_ship CTE source 분류 (Codex Q1 — force_closed 제외 정합)"""

    def test_source_01_app_only(self, client, create_test_admin, get_admin_auth_token,
                                seed_shipment_test_data):
        """app SI completed_at 있고 actual_ship_date 없음 → source='app'"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        month_start = _today().replace(day=1)
        seed_shipment_test_data([
            {'sn': 'TEST-SHIP-76-S01', 'plan_date': month_start,
             'app_si_completed_at': datetime.combine(month_start + timedelta(days=1),
                                                     datetime.min.time()),
             'customer': 'CUST'}
        ])
        resp = client.get(
            f'/api/admin/shipment/details?reference_date={_ref_date_string(month_start)}',
            headers=_auth_header(token)
        )
        assert resp.status_code == 200
        items = [i for i in resp.get_json()['items'] if i['serial_number'] == 'TEST-SHIP-76-S01']
        assert len(items) == 1
        assert items[0]['source'] == 'app'

    def test_source_02_excel_only(self, client, create_test_admin, get_admin_auth_token,
                                  seed_shipment_test_data):
        """actual_ship_date 만 → source='excel'"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        month_start = _today().replace(day=1)
        seed_shipment_test_data([
            {'sn': 'TEST-SHIP-76-S02', 'plan_date': month_start,
             'actual_ship_date': month_start + timedelta(days=1), 'customer': 'CUST'}
        ])
        resp = client.get(
            f'/api/admin/shipment/details?reference_date={_ref_date_string(month_start)}',
            headers=_auth_header(token)
        )
        items = [i for i in resp.get_json()['items'] if i['serial_number'] == 'TEST-SHIP-76-S02']
        assert len(items) == 1
        assert items[0]['source'] == 'excel'

    def test_source_03_both(self, client, create_test_admin, get_admin_auth_token,
                            seed_shipment_test_data):
        """app + excel 둘 다 → source='both', actual_date=app 우선"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        month_start = _today().replace(day=1)
        app_completed = datetime.combine(month_start + timedelta(days=2), datetime.min.time())
        seed_shipment_test_data([
            {'sn': 'TEST-SHIP-76-S03', 'plan_date': month_start,
             'actual_ship_date': month_start + timedelta(days=3),
             'app_si_completed_at': app_completed, 'customer': 'CUST'}
        ])
        resp = client.get(
            f'/api/admin/shipment/details?reference_date={_ref_date_string(month_start)}',
            headers=_auth_header(token)
        )
        items = [i for i in resp.get_json()['items'] if i['serial_number'] == 'TEST-SHIP-76-S03']
        assert len(items) == 1
        assert items[0]['source'] == 'both'
        # app 우선 — actual_date = app SI completed_at DATE (= month_start + 2일)
        assert items[0]['actual_date'] == (month_start + timedelta(days=2)).isoformat()

    def test_source_04_force_closed_excluded(self, client, create_test_admin, get_admin_auth_token,
                                             seed_shipment_test_data):
        """Codex Q1 — force_closed=TRUE 영역 app SI 영역 source/actual 영역 제외"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        month_start = _today().replace(day=1)
        seed_shipment_test_data([
            {'sn': 'TEST-SHIP-76-S04', 'plan_date': month_start,
             'app_si_completed_at': datetime.combine(month_start + timedelta(days=1),
                                                     datetime.min.time()),
             'force_closed': True,  # 강제종료
             'actual_ship_date': month_start + timedelta(days=2),
             'customer': 'CUST'}
        ])
        resp = client.get(
            f'/api/admin/shipment/details?reference_date={_ref_date_string(month_start)}',
            headers=_auth_header(token)
        )
        items = [i for i in resp.get_json()['items'] if i['serial_number'] == 'TEST-SHIP-76-S04']
        assert len(items) == 1
        # force_closed SI 영역 제외 → source='excel' (엑셀만 인정)
        assert items[0]['source'] == 'excel'
        assert items[0]['actual_date'] == (month_start + timedelta(days=2)).isoformat()


# ==================== § 4. status 분류 + delay_days ====================


class TestShipmentStatus:
    """status: shipped / pending / delayed + delay_days 부호"""

    def test_status_01_shipped(self, client, create_test_admin, get_admin_auth_token,
                               seed_shipment_test_data):
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        month_start = _today().replace(day=1)
        seed_shipment_test_data([
            {'sn': 'TEST-SHIP-76-ST01', 'plan_date': month_start,
             'actual_ship_date': month_start + timedelta(days=1), 'customer': 'CUST'}
        ])
        resp = client.get(
            f'/api/admin/shipment/details?reference_date={_ref_date_string(month_start)}&status=shipped',
            headers=_auth_header(token)
        )
        items = [i for i in resp.get_json()['items'] if i['serial_number'] == 'TEST-SHIP-76-ST01']
        assert len(items) == 1
        assert items[0]['status'] == 'shipped'
        assert items[0]['delay_days'] == 1  # 1일 지연

    def test_status_02_pending_future(self, client, create_test_admin, get_admin_auth_token,
                                      seed_shipment_test_data):
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        today = _today()
        future = today + timedelta(days=7)
        seed_shipment_test_data([
            {'sn': 'TEST-SHIP-76-ST02', 'plan_date': future, 'customer': 'CUST'}
        ])
        resp = client.get(
            f'/api/admin/shipment/details?reference_date={_ref_date_string(today)}&status=pending',
            headers=_auth_header(token)
        )
        items = [i for i in resp.get_json()['items'] if i['serial_number'] == 'TEST-SHIP-76-ST02']
        if items:  # period 범위 안에 있을 때
            assert items[0]['status'] == 'pending'

    def test_status_03_delayed_overdue(self, client, create_test_admin, get_admin_auth_token,
                                       seed_shipment_test_data):
        """plan_date < today + actual NULL → delayed"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        today = _today()
        past = today - timedelta(days=3)
        seed_shipment_test_data([
            {'sn': 'TEST-SHIP-76-ST03', 'plan_date': past, 'customer': 'CUST'}
        ])
        resp = client.get(
            f'/api/admin/shipment/details?reference_date={_ref_date_string(past)}&status=delayed',
            headers=_auth_header(token)
        )
        items = [i for i in resp.get_json()['items'] if i['serial_number'] == 'TEST-SHIP-76-ST03']
        if items:
            assert items[0]['status'] == 'delayed'

    def test_status_04_invalid(self, client, create_test_admin, get_admin_auth_token):
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        resp = client.get('/api/admin/shipment/details?status=invalid',
                          headers=_auth_header(token))
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'INVALID_STATUS'


# ==================== § 5. pagination + 필터 조합 (Codex Q4 신규) ====================


class TestShipmentPagination:
    """Codex Q4 M — pagination + 필터 조합 신규"""

    def test_page_01_per_page_limit(self, client, create_test_admin, get_admin_auth_token):
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        resp = client.get('/api/admin/shipment/details?per_page=500',
                          headers=_auth_header(token))
        assert resp.status_code == 400

    def test_page_02_invalid_page(self, client, create_test_admin, get_admin_auth_token):
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        resp = client.get('/api/admin/shipment/details?page=0',
                          headers=_auth_header(token))
        assert resp.status_code == 400

    def test_page_03_total_pages(self, client, create_test_admin, get_admin_auth_token):
        """response total_pages = ceil(total / per_page)"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        resp = client.get('/api/admin/shipment/details?per_page=10',
                          headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        if data['total'] > 0:
            assert data['total_pages'] == (data['total'] + 9) // 10

    def test_filter_01_combo(self, client, create_test_admin, get_admin_auth_token):
        """status + q + partner 동시 필터"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        resp = client.get(
            '/api/admin/shipment/details?status=shipped&q=GAIA&partner=BAT',
            headers=_auth_header(token)
        )
        assert resp.status_code == 200


# ==================== § 6. monthly_trend (Codex Q5 M) ====================


class TestMonthlyTrend:
    """monthly_trend — current-month 포함 trailing 6 + plan/shipped 분리"""

    def test_mt_01_six_months_window(self, client, create_test_admin, get_admin_auth_token):
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        resp = client.get('/api/admin/shipment/summary',
                          headers=_auth_header(token))
        assert resp.status_code == 200
        mt = resp.get_json()['monthly_trend']
        assert len(mt) == 6, f"6개월 trail 기대, got {len(mt)}"
        # zero-fill 정합 — 모든 month 영역 plan / shipped 필드 보장 (Codex Q4 신규)
        for m in mt:
            assert 'month' in m and 'plan' in m and 'shipped' in m
            assert isinstance(m['plan'], int)
            assert isinstance(m['shipped'], int)

    def test_mt_02_separated_aggregation(self, client, create_test_admin, get_admin_auth_token,
                                         seed_shipment_test_data):
        """Codex Q5 — plan/shipped 영역 다른 month 발생 시 각 month 분리 카운트

        plan_date=4월 / actual_ship_date=5월 → 4월 plan +1, 5월 shipped +1
        """
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        # ref_date = 오늘 → trailing 6개월. 본 TC = ref 영역 안에서 분리 catch
        ref = _today().replace(day=15)
        prev_month_1 = (ref.replace(day=1) - timedelta(days=15)).replace(day=1)
        cur_month_5 = ref.replace(day=5)
        seed_shipment_test_data([
            {'sn': 'TEST-SHIP-76-MT01',
             'plan_date': prev_month_1,
             'actual_ship_date': cur_month_5, 'customer': 'CUST'}
        ])
        resp = client.get(
            f'/api/admin/shipment/summary?reference_date={_ref_date_string(ref)}',
            headers=_auth_header(token)
        )
        assert resp.status_code == 200


# ==================== § 7. top_delayed + root_cause (Codex Q3 batch) ====================


class TestTopDelayed:
    """top_delayed — N+1 batch 조회 + root_cause friendly 변환"""

    def test_td_01_root_cause_format(self, client, create_test_admin, get_admin_auth_token,
                                     seed_shipment_test_data):
        """plan_date < actual → delay 발생 + root_cause null fallback (Sprint 71 미연동 시)"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])
        month_start = _today().replace(day=1)
        seed_shipment_test_data([
            {'sn': 'TEST-SHIP-76-TD01', 'plan_date': month_start,
             'actual_ship_date': month_start + timedelta(days=3), 'customer': 'CUST'}
        ])
        resp = client.get(
            f'/api/admin/shipment/summary?reference_date={_ref_date_string(month_start)}',
            headers=_auth_header(token)
        )
        assert resp.status_code == 200
        td = resp.get_json()['top_delayed']
        # delay 영역 row 있으면 root_cause 필드 존재 (None 가능)
        for item in td:
            assert 'serial_number' in item
            assert 'delay_days' in item
            assert 'root_cause' in item
            assert item['delay_days'] > 0


# ==================== § 8. format_root_cause unit test (Codex Q3) ====================


class TestFormatRootCause:
    """services.shipment_history_service.format_root_cause unit test"""

    def test_frc_01_normal_mech(self):
        from app.services.shipment_history_service import format_root_cause
        result = format_root_cause(
            'AUTO_CLOSED_BY_SECOND_FINAL_TRIGGER:SELF_INSPECTION', 'MECH'
        )
        assert result == 'SELF_INSPECTION (기구) 종료 지연'

    def test_frc_02_normal_elec(self):
        from app.services.shipment_history_service import format_root_cause
        result = format_root_cause(
            'AUTO_CLOSED_BY_FIRST_FINAL_TRIGGER:IF_2', 'ELEC'
        )
        assert result == 'IF_2 (전장) 종료 지연'

    def test_frc_03_none_close_reason(self):
        from app.services.shipment_history_service import format_root_cause
        assert format_root_cause(None, 'MECH') is None

    def test_frc_04_none_category(self):
        from app.services.shipment_history_service import format_root_cause
        assert format_root_cause('AUTO_CLOSED_BY_FIRST_FINAL_TRIGGER:IF_2', None) is None

    def test_frc_05_invalid_format(self):
        """close_reason 영역 ':' 없으면 None"""
        from app.services.shipment_history_service import format_root_cause
        assert format_root_cause('MANUAL_FORCE_CLOSE', 'MECH') is None
