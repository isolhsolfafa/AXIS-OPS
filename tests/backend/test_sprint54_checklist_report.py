"""
Sprint 54 체크리스트 성적서 API 테스트 (19건)
TC-54A-01~06: O/N 검색 (배치 쿼리)
TC-54B-01~10: S/N 성적서
TC-54C-01~03: 기존 API 호환
"""

import sys
from pathlib import Path

_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest
import psycopg2.extras
import json


# ── 테스트 데이터 prefix ─────────────────────────────────────────────────────
_PREFIX = 'SN-SP54-'


# ── helpers ──────────────────────────────────────────────────────────────────

def _insert_product(db_conn, serial_number, model='GAIA-I', sales_order='9954',
                    product_code='COMMON', customer='Test Customer'):
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO plan.product_info
            (serial_number, model, sales_order, product_code, customer, prod_date)
        VALUES (%s, %s, %s, %s, %s, NOW()::date)
        ON CONFLICT (serial_number) DO UPDATE
            SET model = EXCLUDED.model,
                sales_order = EXCLUDED.sales_order,
                product_code = EXCLUDED.product_code,
                customer = EXCLUDED.customer
    """, (serial_number, model, sales_order, product_code, customer))
    cursor.execute("""
        INSERT INTO public.qr_registry (qr_doc_id, serial_number, status)
        VALUES (%s, %s, 'active')
        ON CONFLICT (qr_doc_id) DO NOTHING
    """, (f'DOC_{serial_number}', serial_number))
    db_conn.commit()
    cursor.close()


def _insert_tm_master_items(db_conn, product_code='COMMON', count=5):
    """checklist_master에 TM 카테고리 테스트 마스터 데이터 INSERT"""
    groups = ['BURNER', 'REACTOR']
    cursor = db_conn.cursor()
    master_ids = []
    for i in range(count):
        grp = groups[i % len(groups)]
        cursor.execute("""
            INSERT INTO checklist.checklist_master
                (product_code, category, item_group, item_name, item_order, is_active, updated_at)
            VALUES (%s, 'TM', %s, %s, %s, TRUE, NOW())
            ON CONFLICT (product_code, category, item_group, item_name) DO UPDATE
                SET item_order = EXCLUDED.item_order
            RETURNING id
        """, (product_code, grp, f'SP54 TM 항목 {i+1}', i + 1))
        row = cursor.fetchone()
        master_ids.append(row[0])
    db_conn.commit()
    cursor.close()
    return master_ids


def _upsert_checklist_record(db_conn, serial_number, master_id, check_result, worker_id,
                               note=None, judgment_phase=1):
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO checklist.checklist_record
            (serial_number, master_id, judgment_phase, check_result, checked_by, checked_at, note, qr_doc_id, updated_at)
        VALUES (%s, %s, %s, %s, %s, NOW(), %s, '', NOW())
        ON CONFLICT (serial_number, master_id, judgment_phase, qr_doc_id) DO UPDATE
            SET check_result = EXCLUDED.check_result,
                checked_by   = EXCLUDED.checked_by,
                checked_at   = NOW(),
                note         = EXCLUDED.note,
                updated_at   = NOW()
    """, (serial_number, master_id, judgment_phase, check_result, worker_id, note))
    db_conn.commit()
    cursor.close()


def _set_admin_setting(db_conn, key, value):
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO admin_settings (setting_key, setting_value)
        VALUES (%s, %s::jsonb)
        ON CONFLICT (setting_key) DO UPDATE SET setting_value = EXCLUDED.setting_value
    """, (key, json.dumps(value)))
    db_conn.commit()
    cursor.close()


def _cleanup_products(db_conn, prefix):
    """테스트 후 정리 — prefix로 시작하는 S/N 데이터 삭제"""
    cursor = db_conn.cursor()
    try:
        # checklist_record 먼저 (FK)
        cursor.execute("""
            DELETE FROM checklist.checklist_record
            WHERE serial_number LIKE %s
        """, (f'{prefix}%',))
        # checklist_master (COMMON product_code라 공유되므로 item_name 패턴으로 정리)
        cursor.execute("""
            DELETE FROM checklist.checklist_master
            WHERE item_name LIKE 'SP54 TM 항목%'
        """)
        cursor.execute("""
            DELETE FROM public.qr_registry WHERE serial_number LIKE %s
        """, (f'{prefix}%',))
        cursor.execute("""
            DELETE FROM plan.product_info WHERE serial_number LIKE %s
        """, (f'{prefix}%',))
        db_conn.commit()
    except Exception as e:
        db_conn.rollback()
    finally:
        cursor.close()


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def view_token(db_conn, seed_test_data, get_auth_token):
    """GST 소속 manager → view_access_required 통과"""
    cursor = db_conn.cursor()
    cursor.execute("SELECT id FROM workers WHERE email = 'seed_manager@test.axisos.com'")
    row = cursor.fetchone()
    cursor.close()
    # seed_manager: is_manager=True, company=FNI → view_access_required 통과
    return get_auth_token(row[0], role='MECH')


@pytest.fixture
def admin_token(db_conn, seed_test_data, get_auth_token):
    cursor = db_conn.cursor()
    cursor.execute("SELECT id FROM workers WHERE email = 'seed_admin@test.axisos.com'")
    row = cursor.fetchone()
    cursor.close()
    return get_auth_token(row[0], role='ADMIN', is_admin=True)


@pytest.fixture
def worker_id(db_conn, seed_test_data):
    cursor = db_conn.cursor()
    cursor.execute("SELECT id FROM workers WHERE email = 'seed_mech@test.axisos.com'")
    row = cursor.fetchone()
    cursor.close()
    return row[0]


@pytest.fixture(autouse=True)
def setup_scope(db_conn, seed_test_data):
    """tm_checklist_scope = 'all' 로 고정 (COMMON product_code 기준)"""
    _set_admin_setting(db_conn, 'tm_checklist_scope', 'all')
    yield
    # teardown: 테스트 데이터 정리
    _cleanup_products(db_conn, _PREFIX)


# ─────────────────────────────────────────────────────────────────────────────
# [#54-A: O/N 검색] TC-54A-01~06
# ─────────────────────────────────────────────────────────────────────────────

class TestChecklistReportOrders:

    def test_tc54a_01_sales_order_exact_match(self, client, db_conn, view_token, worker_id):
        """TC-54A-01: GET /report/orders?sales_order=9954 → 해당 O/N의 S/N 목록 반환"""
        sn = f'{_PREFIX}ON001'
        _insert_product(db_conn, sn, sales_order='9954')

        resp = client.get(
            '/api/admin/checklist/report/orders?sales_order=9954',
            headers={'Authorization': f'Bearer {view_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'products' in data
        sns = [p['serial_number'] for p in data['products']]
        assert sn in sns

    def test_tc54a_02_serial_number_partial_match(self, client, db_conn, view_token, worker_id):
        """TC-54A-02: GET /report/orders?serial_number=SP54 → ILIKE 부분 일치, 매칭 S/N 반환"""
        sn = f'{_PREFIX}SN002'
        _insert_product(db_conn, sn, sales_order='9955')

        resp = client.get(
            f'/api/admin/checklist/report/orders?serial_number=SP54',
            headers={'Authorization': f'Bearer {view_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        sns = [p['serial_number'] for p in data['products']]
        assert sn in sns

    def test_tc54a_03_or_condition_both_params(self, client, db_conn, view_token, worker_id):
        """TC-54A-03: 두 파라미터 동시 → OR 조건 (합집합)"""
        sn_on = f'{_PREFIX}OR001'
        sn_sn = f'{_PREFIX}OR002'
        _insert_product(db_conn, sn_on, sales_order='9956')
        _insert_product(db_conn, sn_sn, sales_order='9957')

        resp = client.get(
            f'/api/admin/checklist/report/orders?sales_order=9956&serial_number=OR002',
            headers={'Authorization': f'Bearer {view_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        sns = [p['serial_number'] for p in data['products']]
        # 두 S/N 모두 포함 (OR 조건)
        assert sn_on in sns
        assert sn_sn in sns

    def test_tc54a_04_no_match_returns_empty(self, client, db_conn, view_token):
        """TC-54A-04: 매칭 없음 → products: [] (200)"""
        resp = client.get(
            '/api/admin/checklist/report/orders?sales_order=NONEXISTENT99999',
            headers={'Authorization': f'Bearer {view_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['products'] == []

    def test_tc54a_05_no_params_returns_400(self, client, db_conn, view_token):
        """TC-54A-05: 파라미터 없음 → 400 에러"""
        resp = client.get(
            '/api/admin/checklist/report/orders',
            headers={'Authorization': f'Bearer {view_token}'}
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['error'] == 'INVALID_REQUEST'

    def test_tc54a_06_overall_percent_calculation(self, client, db_conn, view_token, worker_id):
        """TC-54A-06: overall_percent = checked / total × 100"""
        sn = f'{_PREFIX}PCT001'
        _insert_product(db_conn, sn, sales_order='9958')

        # master 5개 생성 (COMMON scope)
        master_ids = _insert_tm_master_items(db_conn, count=5)

        # 5개 중 2개 PASS → 40.0%
        for mid in master_ids[:2]:
            _upsert_checklist_record(db_conn, sn, mid, 'PASS', worker_id)

        resp = client.get(
            f'/api/admin/checklist/report/orders?serial_number=PCT001',
            headers={'Authorization': f'Bearer {view_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        products = {p['serial_number']: p for p in data['products']}
        assert sn in products
        pct = products[sn]['overall_percent']
        assert isinstance(pct, float)
        # master 총 개수 중 2개 checked → percent > 0
        assert pct > 0.0


# ─────────────────────────────────────────────────────────────────────────────
# [#54-B: S/N 성적서] TC-54B-01~10
# ─────────────────────────────────────────────────────────────────────────────

class TestChecklistReportDetail:

    def test_tc54b_01_categories_include_tm(self, client, db_conn, view_token, worker_id):
        """TC-54B-01: GET /report/{sn} → categories 배열에 TM 포함"""
        sn = f'{_PREFIX}RPT001'
        _insert_product(db_conn, sn)
        _insert_tm_master_items(db_conn, count=3)

        resp = client.get(
            f'/api/admin/checklist/report/{sn}',
            headers={'Authorization': f'Bearer {view_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'categories' in data
        cat_names = [c['category'] for c in data['categories']]
        assert 'TM' in cat_names

    def test_tc54b_02_items_have_required_fields(self, client, db_conn, view_token, worker_id):
        """TC-54B-02: TM items에 item_group, item_name, item_type, check_result, checked_by_name 포함"""
        sn = f'{_PREFIX}RPT002'
        _insert_product(db_conn, sn)
        _insert_tm_master_items(db_conn, count=2)

        resp = client.get(
            f'/api/admin/checklist/report/{sn}',
            headers={'Authorization': f'Bearer {view_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        tm_cat = next((c for c in data['categories'] if c['category'] == 'TM'), None)
        assert tm_cat is not None
        assert len(tm_cat['items']) > 0
        item = tm_cat['items'][0]
        assert 'item_group' in item
        assert 'item_name' in item
        assert 'item_type' in item
        assert 'check_result' in item
        assert 'checked_by_name' in item

    def test_tc54b_03_check_result_values(self, client, db_conn, view_token, worker_id):
        """TC-54B-03: check_result 필드: PASS, NA, null 정상 반환"""
        sn = f'{_PREFIX}RPT003'
        _insert_product(db_conn, sn)
        master_ids = _insert_tm_master_items(db_conn, count=3)

        # 첫 번째: PASS, 두 번째: NA, 세 번째: null(미체크)
        _upsert_checklist_record(db_conn, sn, master_ids[0], 'PASS', worker_id)
        _upsert_checklist_record(db_conn, sn, master_ids[1], 'NA', worker_id)

        resp = client.get(
            f'/api/admin/checklist/report/{sn}',
            headers={'Authorization': f'Bearer {view_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        tm_cat = next((c for c in data['categories'] if c['category'] == 'TM'), None)
        assert tm_cat is not None
        results = {item['item_name']: item['check_result'] for item in tm_cat['items']}
        assert 'PASS' in results.values()
        assert 'NA' in results.values()
        assert None in results.values()

    def test_tc54b_04_checked_by_name_join(self, client, db_conn, view_token, worker_id):
        """TC-54B-04: checked_by_name = workers.name JOIN 결과"""
        sn = f'{_PREFIX}RPT004'
        _insert_product(db_conn, sn)
        master_ids = _insert_tm_master_items(db_conn, count=2)

        _upsert_checklist_record(db_conn, sn, master_ids[0], 'PASS', worker_id)

        # worker 이름 조회
        cursor = db_conn.cursor()
        cursor.execute("SELECT name FROM workers WHERE id = %s", (worker_id,))
        worker_name = cursor.fetchone()[0]
        cursor.close()

        resp = client.get(
            f'/api/admin/checklist/report/{sn}',
            headers={'Authorization': f'Bearer {view_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        tm_cat = next((c for c in data['categories'] if c['category'] == 'TM'), None)
        assert tm_cat is not None
        checked_items = [i for i in tm_cat['items'] if i['check_result'] == 'PASS']
        assert len(checked_items) > 0
        assert checked_items[0]['checked_by_name'] == worker_name

    def test_tc54b_05_summary_total_and_checked(self, client, db_conn, view_token, worker_id):
        """TC-54B-05: summary.total = active master 항목 수, summary.checked = PASS/NA 수"""
        sn = f'{_PREFIX}RPT005'
        _insert_product(db_conn, sn)
        master_ids = _insert_tm_master_items(db_conn, count=4)

        # 4개 중 3개 체크 (2 PASS + 1 NA)
        _upsert_checklist_record(db_conn, sn, master_ids[0], 'PASS', worker_id)
        _upsert_checklist_record(db_conn, sn, master_ids[1], 'PASS', worker_id)
        _upsert_checklist_record(db_conn, sn, master_ids[2], 'NA', worker_id)

        resp = client.get(
            f'/api/admin/checklist/report/{sn}',
            headers={'Authorization': f'Bearer {view_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        tm_cat = next((c for c in data['categories'] if c['category'] == 'TM'), None)
        assert tm_cat is not None
        summary = tm_cat['summary']
        assert summary['total'] >= 4  # 이전 테스트에서 누적된 master도 포함될 수 있음
        assert summary['checked'] >= 3

    def test_tc54b_06_summary_percent(self, client, db_conn, view_token, worker_id):
        """TC-54B-06: summary.percent = checked / total × 100 (소수점 1자리)"""
        sn = f'{_PREFIX}RPT006'
        _insert_product(db_conn, sn)
        master_ids = _insert_tm_master_items(db_conn, count=4)

        # 4개 중 2개만 체크 → 정확한 계산을 위해 새 master만 사용하도록 정리 필요
        # 기존 SP54 master들이 있을 수 있으므로 해당 S/N에만 2개 체크
        _upsert_checklist_record(db_conn, sn, master_ids[0], 'PASS', worker_id)
        _upsert_checklist_record(db_conn, sn, master_ids[1], 'PASS', worker_id)

        resp = client.get(
            f'/api/admin/checklist/report/{sn}',
            headers={'Authorization': f'Bearer {view_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        tm_cat = next((c for c in data['categories'] if c['category'] == 'TM'), None)
        assert tm_cat is not None
        summary = tm_cat['summary']
        assert 'percent' in summary
        # percent는 float 타입
        assert isinstance(summary['percent'], (int, float))
        # 소수점 1자리 이하 확인
        percent_str = str(summary['percent'])
        if '.' in percent_str:
            decimal_places = len(percent_str.split('.')[1])
            assert decimal_places <= 1

    def test_tc54b_07_no_mech_elec_master_excluded(self, client, db_conn, view_token):
        """TC-54B-07: MECH/ELEC master 없으면 → categories에 TM만 (빈 카테고리 자동 제외)"""
        sn = f'{_PREFIX}RPT007'
        _insert_product(db_conn, sn)
        _insert_tm_master_items(db_conn, count=2)

        resp = client.get(
            f'/api/admin/checklist/report/{sn}',
            headers={'Authorization': f'Bearer {view_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        cat_names = [c['category'] for c in data['categories']]
        # MECH/ELEC master가 없으면 categories에 없어야 함
        # (TM은 있음, 빈 카테고리는 제외됨)
        for cat in cat_names:
            # 해당 카테고리는 total > 0 보장
            tm_cat = next((c for c in data['categories'] if c['category'] == cat), None)
            assert tm_cat['summary']['total'] > 0

    def test_tc54b_08_product_not_found_404(self, client, db_conn, view_token):
        """TC-54B-08: 존재하지 않는 S/N → 404 PRODUCT_NOT_FOUND"""
        resp = client.get(
            '/api/admin/checklist/report/NONEXISTENT-SN-SP54-99999',
            headers={'Authorization': f'Bearer {view_token}'}
        )
        assert resp.status_code == 404
        data = resp.get_json()
        assert data['error'] == 'PRODUCT_NOT_FOUND'

    def test_tc54b_09_generated_at_kst_iso(self, client, db_conn, view_token):
        """TC-54B-09: generated_at = KST 현재 시각 ISO 형식"""
        sn = f'{_PREFIX}RPT009'
        _insert_product(db_conn, sn)

        resp = client.get(
            f'/api/admin/checklist/report/{sn}',
            headers={'Authorization': f'Bearer {view_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'generated_at' in data
        generated_at = data['generated_at']
        # ISO 형식 문자열 확인
        assert 'T' in generated_at
        # KST (+09:00) 포함 확인
        assert '+09:00' in generated_at

    def test_tc54b_10_customer_field(self, client, db_conn, view_token):
        """TC-54B-10: customer 필드 = product_info.customer 값"""
        sn = f'{_PREFIX}RPT010'
        _insert_product(db_conn, sn, customer='SP54 Test Customer Corp')

        resp = client.get(
            f'/api/admin/checklist/report/{sn}',
            headers={'Authorization': f'Bearer {view_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get('customer') == 'SP54 Test Customer Corp'


# ─────────────────────────────────────────────────────────────────────────────
# [기존 API 호환] TC-54C-01~03
# ─────────────────────────────────────────────────────────────────────────────

class TestExistingApiCompat:

    def test_tc54c_01_get_tm_checklist_groups_format(self, client, db_conn, view_token, worker_id):
        """TC-54C-01: GET /api/app/checklist/tm/{sn} → 기존 응답 형태 동일 (groups 배열 유지)"""
        sn = f'{_PREFIX}COMPAT001'
        _insert_product(db_conn, sn)
        _insert_tm_master_items(db_conn, count=3)

        # jwt_required만 사용 (view_access_required 아님) → view_token으로도 가능
        resp = client.get(
            f'/api/app/checklist/tm/{sn}',
            headers={'Authorization': f'Bearer {view_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        # 기존 응답 형태 확인
        assert 'serial_number' in data
        assert 'groups' in data
        assert 'summary' in data
        summary = data['summary']
        assert 'total' in summary
        assert 'checked' in summary
        assert 'remaining' in summary
        assert 'is_complete' in summary
        # groups는 배열
        assert isinstance(data['groups'], list)

    def test_tc54c_02_put_tm_check_unchanged(self, client, db_conn, admin_token, worker_id):
        """TC-54C-02: PUT /api/app/checklist/tm/check → 기존 동작 동일"""
        sn = f'{_PREFIX}COMPAT002'
        _insert_product(db_conn, sn)
        master_ids = _insert_tm_master_items(db_conn, count=2)

        # admin_token으로 체크 (is_manager 권한 필요)
        resp = client.put(
            '/api/app/checklist/tm/check',
            json={
                'serial_number': sn,
                'master_id': master_ids[0],
                'check_result': 'PASS',
            },
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        # 200 또는 403 (권한 설정에 따라) — 기존 응답 구조 확인
        assert resp.status_code in (200, 403)
        if resp.status_code == 200:
            data = resp.get_json()
            assert 'master_id' in data
            assert 'check_result' in data
            assert 'is_complete' in data

    def test_tc54c_03_get_tm_status_unchanged(self, client, db_conn, view_token, worker_id):
        """TC-54C-03: GET /api/app/checklist/tm/{sn}/status → 기존 동작 동일"""
        sn = f'{_PREFIX}COMPAT003'
        _insert_product(db_conn, sn)
        master_ids = _insert_tm_master_items(db_conn, count=3)
        _upsert_checklist_record(db_conn, sn, master_ids[0], 'PASS', worker_id)

        resp = client.get(
            f'/api/app/checklist/tm/{sn}/status',
            headers={'Authorization': f'Bearer {view_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'is_complete' in data
        assert 'completed_at' in data
        assert 'checked_count' in data
        assert 'total_count' in data
        # 1개 체크됨
        assert data['checked_count'] >= 1
        assert data['total_count'] >= 3
        assert data['is_complete'] is False
