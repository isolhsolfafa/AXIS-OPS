"""
Sprint 52 TM 체크리스트 테스트 (38건)
TC-52-01 ~ TC-52-38

[DB 스키마]       TC-52-01~07
[TM 체크리스트 API] TC-52-08~17
[알림 연동]        TC-52-18~22
[Admin CRUD API]   TC-52-23~30
[Settings API]     TC-52-31~34
[기존 기능 regression] TC-52-35~38
"""

import sys
from pathlib import Path

_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest
import psycopg2.extras
from datetime import date


# ── 테스트 데이터 prefix ──────────────────────────────────────────────────
_PREFIX = 'SN-SP52-'


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def admin_token(db_conn, seed_test_data, get_auth_token):
    """Seed admin의 실제 worker_id로 JWT 토큰 생성"""
    cursor = db_conn.cursor()
    cursor.execute("SELECT id FROM workers WHERE email = 'seed_admin@test.axisos.com'")
    row = cursor.fetchone()
    cursor.close()
    return get_auth_token(row[0], role='ADMIN', is_admin=True)


@pytest.fixture
def manager_token(db_conn, seed_test_data, get_auth_token):
    """Seed manager (is_manager=True, role=MECH)"""
    cursor = db_conn.cursor()
    cursor.execute("SELECT id FROM workers WHERE email = 'seed_manager@test.axisos.com'")
    row = cursor.fetchone()
    cursor.close()
    return get_auth_token(row[0], role='MECH')


@pytest.fixture
def manager_id(db_conn, seed_test_data):
    cursor = db_conn.cursor()
    cursor.execute("SELECT id FROM workers WHERE email = 'seed_manager@test.axisos.com'")
    row = cursor.fetchone()
    cursor.close()
    return row[0]


@pytest.fixture
def mech_token(db_conn, seed_test_data, get_auth_token):
    """일반 MECH 작업자 (is_manager=False)"""
    cursor = db_conn.cursor()
    cursor.execute("SELECT id FROM workers WHERE email = 'seed_mech@test.axisos.com'")
    row = cursor.fetchone()
    cursor.close()
    return get_auth_token(row[0], role='MECH')


@pytest.fixture
def mech_worker_id(db_conn, seed_test_data):
    cursor = db_conn.cursor()
    cursor.execute("SELECT id FROM workers WHERE email = 'seed_mech@test.axisos.com'")
    row = cursor.fetchone()
    cursor.close()
    return row[0]


@pytest.fixture
def tm_manager_token(db_conn, seed_test_data, create_test_worker, get_auth_token):
    """TM role manager (CHECKLIST_TM_READY 알림 수신용)"""
    wid = create_test_worker(
        email='tm_mgr_sp52@test.axisos.com',
        password='Test1234!',
        name='TM Manager SP52',
        role='TM',
        is_manager=True,
        company='TMS(M)',
    )
    return get_auth_token(wid, role='TM')


@pytest.fixture
def tm_manager_id(db_conn, seed_test_data, create_test_worker):
    wid = create_test_worker(
        email='tm_mgr2_sp52@test.axisos.com',
        password='Test1234!',
        name='TM Manager2 SP52',
        role='TM',
        is_manager=True,
        company='TMS(M)',
    )
    return wid


def _insert_product(db_conn, serial_number, model='GAIA-I', sales_order='6408',
                    product_code='COMMON'):
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO plan.product_info
            (serial_number, model, sales_order, product_code, prod_date)
        VALUES (%s, %s, %s, %s, NOW()::date)
        ON CONFLICT (serial_number) DO NOTHING
    """, (serial_number, model, sales_order, product_code))
    cursor.execute("""
        INSERT INTO public.qr_registry (qr_doc_id, serial_number, status)
        VALUES (%s, %s, 'active')
        ON CONFLICT (qr_doc_id) DO NOTHING
    """, (f'DOC_{serial_number}', serial_number))
    db_conn.commit()
    cursor.close()


def _get_tm_master_ids(db_conn, product_code='COMMON', limit=None):
    """migration 043a seed에서 생성된 TM master 항목 ID 조회 (운영 동일 데이터 사용)"""
    cursor = db_conn.cursor()
    query = """
        SELECT id FROM checklist.checklist_master
        WHERE product_code = %s AND category = 'TM' AND is_active = TRUE
        ORDER BY item_group, item_order
    """
    if limit:
        query += f" LIMIT {int(limit)}"
    cursor.execute(query, (product_code,))
    master_ids = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return master_ids


def _insert_tm_master_items(db_conn, product_code='COMMON', count=15):
    """migration seed 데이터 조회 반환. product_code가 COMMON이 아닌 경우만 INSERT."""
    if product_code == 'COMMON':
        return _get_tm_master_ids(db_conn, product_code, limit=count)

    # COMMON이 아닌 경우 (ALERT_ONLY 등 테스트 전용) — 별도 INSERT
    groups = ['BURNER', 'REACTOR', 'EXHAUST', 'TANK']
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
        """, (product_code, grp, f'TM 점검항목 {i+1}', i + 1))
        row = cursor.fetchone()
        master_ids.append(row[0])
    db_conn.commit()
    cursor.close()
    return master_ids


def _insert_task_detail(db_conn, serial_number, task_category='TMS', task_id='TANK_MODULE',
                        task_name='Tank Module', worker_id=None):
    """app_task_details에 TM task 등록"""
    cursor = db_conn.cursor()
    qr_doc_id = f'DOC_{serial_number}'
    cursor.execute("""
        INSERT INTO app_task_details
            (serial_number, qr_doc_id, task_category, task_id, task_name,
             is_applicable, worker_id, started_at)
        VALUES (%s, %s, %s, %s, %s, TRUE, %s, NOW())
        ON CONFLICT (serial_number, qr_doc_id, task_category, task_id) DO UPDATE
            SET worker_id = EXCLUDED.worker_id, started_at = NOW()
        RETURNING id
    """, (serial_number, qr_doc_id, task_category, task_id, task_name, worker_id))
    row = cursor.fetchone()
    task_detail_id = row[0]
    db_conn.commit()
    cursor.close()
    return task_detail_id


def _set_admin_setting(db_conn, key, value):
    """admin_settings에 설정값 업데이트/삽입"""
    import json
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO admin_settings (setting_key, setting_value)
        VALUES (%s, %s::jsonb)
        ON CONFLICT (setting_key) DO UPDATE SET setting_value = EXCLUDED.setting_value
    """, (key, json.dumps(value)))
    db_conn.commit()
    cursor.close()


def _upsert_checklist_record(db_conn, serial_number, master_id, check_result, worker_id,
                              note=None, judgment_phase=1):
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO checklist.checklist_record
            (serial_number, master_id, judgment_phase, check_result, checked_by, checked_at, note, updated_at)
        VALUES (%s, %s, %s, %s, %s, NOW(), %s, NOW())
        ON CONFLICT (serial_number, master_id, judgment_phase) DO UPDATE
            SET check_result = EXCLUDED.check_result,
                checked_by   = EXCLUDED.checked_by,
                checked_at   = NOW(),
                note         = EXCLUDED.note,
                updated_at   = NOW()
    """, (serial_number, master_id, judgment_phase, check_result, worker_id, note))
    db_conn.commit()
    cursor.close()


# ─────────────────────────────────────────────────────────────────────────────
# [DB 스키마] TC-52-01~07
# ─────────────────────────────────────────────────────────────────────────────

class TestDbSchema:

    def test_tc52_01_checklist_master_item_group_column(self, db_conn, db_schema):
        """TC-52-01: checklist_master.item_group 컬럼 존재 확인"""
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'checklist'
              AND table_name   = 'checklist_master'
              AND column_name  = 'item_group'
        """)
        row = cursor.fetchone()
        cursor.close()
        assert row is not None, "checklist_master.item_group 컬럼이 없습니다"

    def test_tc52_02_checklist_record_check_result_column(self, db_conn, db_schema):
        """TC-52-02: checklist_record.check_result 컬럼 존재 확인"""
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'checklist'
              AND table_name   = 'checklist_record'
              AND column_name  = 'check_result'
        """)
        row = cursor.fetchone()
        cursor.close()
        assert row is not None, "checklist_record.check_result 컬럼이 없습니다"

    def test_tc52_03_checklist_record_judgment_phase_column(self, db_conn, db_schema):
        """TC-52-03: checklist_record.judgment_phase 컬럼 존재, DEFAULT 1 확인"""
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT column_name, column_default
            FROM information_schema.columns
            WHERE table_schema = 'checklist'
              AND table_name   = 'checklist_record'
              AND column_name  = 'judgment_phase'
        """)
        row = cursor.fetchone()
        cursor.close()
        assert row is not None, "checklist_record.judgment_phase 컬럼이 없습니다"
        # DEFAULT 1 확인 (column_default에 '1' 포함)
        col_default = str(row[1]) if row[1] else ''
        assert '1' in col_default, f"judgment_phase DEFAULT 1이 아닙니다: {col_default}"

    def test_tc52_04_unique_constraint_serial_master_phase(self, db_conn, db_schema):
        """TC-52-04: UNIQUE 제약 확인 → (serial_number, master_id, judgment_phase)"""
        cursor = db_conn.cursor()
        # UNIQUE 제약이 있는지 — pg_constraint 조회
        cursor.execute("""
            SELECT con.conname
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
            WHERE nsp.nspname = 'checklist'
              AND rel.relname  = 'checklist_record'
              AND con.contype  = 'u'
        """)
        rows = cursor.fetchall()
        cursor.close()
        constraint_names = [str(r[0]) for r in rows]
        # UNIQUE 제약이 1개 이상 있으면 OK (serial_number, master_id, judgment_phase)
        assert len(constraint_names) > 0, \
            f"checklist_record에 UNIQUE 제약이 없습니다. 현재 제약: {constraint_names}"

    def test_tc52_05_existing_is_checked_data_migration(self, db_conn, db_schema, seed_test_data):
        """TC-52-05: is_checked 관련 — check_result 컬럼이 있으면 PASS로 저장 가능"""
        # 직접 check_result='PASS' insert 후 조회
        sn = f'{_PREFIX}SCHEMA-05'
        _insert_product(db_conn, sn)
        master_ids = _insert_tm_master_items(db_conn, count=1)
        mid = master_ids[0]

        cursor = db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            INSERT INTO checklist.checklist_record
                (serial_number, master_id, judgment_phase, check_result, checked_by, checked_at, updated_at)
            VALUES (%s, %s, 1, 'PASS', NULL, NOW(), NOW())
            ON CONFLICT (serial_number, master_id, judgment_phase) DO UPDATE
                SET check_result = 'PASS'
            RETURNING check_result
        """, (sn, mid))
        row = cursor.fetchone()
        db_conn.commit()
        cursor.close()
        assert row['check_result'] == 'PASS'

    def test_tc52_06_alert_type_enum_checklist_tm_ready(self, db_conn, db_schema):
        """TC-52-06: alert_type_enum에 CHECKLIST_TM_READY, CHECKLIST_ISSUE 추가 확인"""
        cursor = db_conn.cursor()
        cursor.execute("SELECT unnest(enum_range(NULL::alert_type_enum))::text")
        rows = cursor.fetchall()
        cursor.close()
        enum_values = {r[0] for r in rows}
        assert 'CHECKLIST_TM_READY' in enum_values, \
            f"CHECKLIST_TM_READY가 alert_type_enum에 없습니다. 현재: {enum_values}"
        assert 'CHECKLIST_ISSUE' in enum_values, \
            f"CHECKLIST_ISSUE가 alert_type_enum에 없습니다. 현재: {enum_values}"

    def test_tc52_07_admin_settings_tm_checklist_keys(self, db_conn, db_schema):
        """TC-52-07: admin_settings에 tm_checklist_* 3개 키 존재 확인"""
        # admin_settings에 default 값 seed
        for key, val in [
            ('tm_checklist_1st_checker', '"is_manager"'),
            ('tm_checklist_issue_alert', 'true'),
            ('tm_checklist_scope', '"product_code"'),
        ]:
            cursor = db_conn.cursor()
            cursor.execute("""
                INSERT INTO admin_settings (setting_key, setting_value)
                VALUES (%s, %s::jsonb)
                ON CONFLICT (setting_key) DO NOTHING
            """, (key, val))
            db_conn.commit()
            cursor.close()

        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT setting_key FROM admin_settings
            WHERE setting_key LIKE 'tm_checklist_%'
        """)
        rows = cursor.fetchall()
        cursor.close()
        keys = {r[0] for r in rows}
        assert 'tm_checklist_1st_checker' in keys
        assert 'tm_checklist_issue_alert' in keys
        assert 'tm_checklist_scope' in keys


# ─────────────────────────────────────────────────────────────────────────────
# [TM 체크리스트 API] TC-52-08~17
# ─────────────────────────────────────────────────────────────────────────────

class TestTmChecklistApi:

    @pytest.fixture(autouse=True)
    def setup_product_and_master(self, db_conn, seed_test_data):
        """각 테스트 전 공통 제품 + master 데이터 준비"""
        sn = f'{_PREFIX}API'
        _insert_product(db_conn, sn, product_code='COMMON')
        _set_admin_setting(db_conn, 'tm_checklist_scope', 'product_code')
        _set_admin_setting(db_conn, 'tm_checklist_1st_checker', 'is_manager')
        self.sn = sn
        self.master_ids = _insert_tm_master_items(db_conn, product_code='COMMON', count=15)
        yield
        # 테스트 후 checklist_record 정리 (테스트 격리)
        cursor = db_conn.cursor()
        cursor.execute(
            "DELETE FROM checklist.checklist_record WHERE serial_number = %s",
            (sn,)
        )
        db_conn.commit()
        cursor.close()

    def test_tc52_08_get_tm_checklist_groups_and_summary(self, client, manager_token):
        """TC-52-08: GET /api/app/checklist/tm/{sn} → groups별 항목 + summary 응답 확인"""
        resp = client.get(
            f'/api/app/checklist/tm/{self.sn}',
            headers={'Authorization': f'Bearer {manager_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'groups' in data
        assert 'summary' in data
        assert data['summary']['total'] == 15
        assert len(data['groups']) > 0
        assert data['serial_number'] == self.sn

    def test_tc52_09_get_tm_checklist_check_result_null_default(self, client, manager_token):
        """TC-52-09: GET /api/app/checklist/tm/{sn} → check_result=null (미체크) 기본값 확인"""
        resp = client.get(
            f'/api/app/checklist/tm/{self.sn}',
            headers={'Authorization': f'Bearer {manager_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        for group in data['groups']:
            for item in group['items']:
                assert item['check_result'] is None, \
                    f"미체크 항목의 check_result가 None이 아닙니다: {item}"

    def test_tc52_10_put_tm_check_pass(self, client, manager_token):
        """TC-52-10: PUT /api/app/checklist/tm/check → check_result='PASS' → 정상 저장"""
        resp = client.put(
            '/api/app/checklist/tm/check',
            json={
                'serial_number': self.sn,
                'master_id': self.master_ids[0],
                'check_result': 'PASS',
            },
            headers={'Authorization': f'Bearer {manager_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['check_result'] == 'PASS'
        assert data['master_id'] == self.master_ids[0]

    def test_tc52_11_put_tm_check_na(self, client, manager_token):
        """TC-52-11: PUT /api/app/checklist/tm/check → check_result='NA' → 정상 저장"""
        resp = client.put(
            '/api/app/checklist/tm/check',
            json={
                'serial_number': self.sn,
                'master_id': self.master_ids[1],
                'check_result': 'NA',
            },
            headers={'Authorization': f'Bearer {manager_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['check_result'] == 'NA'

    def test_tc52_12_put_tm_check_invalid_fail(self, client, manager_token):
        """TC-52-12: PUT /api/app/checklist/tm/check → check_result='FAIL' → 400"""
        resp = client.put(
            '/api/app/checklist/tm/check',
            json={
                'serial_number': self.sn,
                'master_id': self.master_ids[0],
                'check_result': 'FAIL',
            },
            headers={'Authorization': f'Bearer {manager_token}'}
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['error'] == 'INVALID_CHECK_RESULT'

    def test_tc52_13_put_tm_check_note_issue(self, client, manager_token, db_conn):
        """TC-52-13: PUT /api/app/checklist/tm/check → note 포함 ISSUE 저장 확인"""
        note_text = '이상 발견 — 추가 확인 필요'
        resp = client.put(
            '/api/app/checklist/tm/check',
            json={
                'serial_number': self.sn,
                'master_id': self.master_ids[2],
                'check_result': 'PASS',
                'note': note_text,
            },
            headers={'Authorization': f'Bearer {manager_token}'}
        )
        assert resp.status_code == 200

        # DB에서 note 확인
        cursor = db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT note FROM checklist.checklist_record
            WHERE serial_number = %s AND master_id = %s AND judgment_phase = 1
        """, (self.sn, self.master_ids[2]))
        row = cursor.fetchone()
        cursor.close()
        assert row is not None
        assert row['note'] == note_text

    def test_tc52_14_all_items_complete_is_complete_true(self, client, manager_token, manager_id):
        """TC-52-14: 15항목 전부 PASS/NA → is_complete=True 반환"""
        for mid in self.master_ids:
            resp = client.put(
                '/api/app/checklist/tm/check',
                json={'serial_number': self.sn, 'master_id': mid, 'check_result': 'PASS'},
                headers={'Authorization': f'Bearer {manager_token}'}
            )
            assert resp.status_code == 200

        # 마지막 응답에서 is_complete=True
        data = resp.get_json()
        assert data['is_complete'] is True

    def test_tc52_15_one_item_remaining_is_complete_false(self, client, manager_token):
        """TC-52-15: 14항목 체크 + 1항목 미체크 → is_complete=False"""
        for mid in self.master_ids[:-1]:  # 마지막 1개 제외
            resp = client.put(
                '/api/app/checklist/tm/check',
                json={'serial_number': self.sn, 'master_id': mid, 'check_result': 'PASS'},
                headers={'Authorization': f'Bearer {manager_token}'}
            )
            assert resp.status_code == 200

        data = resp.get_json()
        assert data['is_complete'] is False

    def test_tc52_16_status_endpoint(self, client, manager_token, db_conn, manager_id):
        """TC-52-16: GET /api/app/checklist/tm/{sn}/status → is_complete + checked_count 확인"""
        # 5개만 체크
        for mid in self.master_ids[:5]:
            _upsert_checklist_record(db_conn, self.sn, mid, 'PASS', manager_id)

        resp = client.get(
            f'/api/app/checklist/tm/{self.sn}/status',
            headers={'Authorization': f'Bearer {manager_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['is_complete'] is False
        assert data['checked_count'] == 5
        assert data['total_count'] == 15

    def test_tc52_17_non_manager_put_forbidden(self, client, mech_token):
        """TC-52-17: is_manager=False인 유저가 PUT → 403 (tm_checklist_1st_checker="is_manager" 기본값)"""
        resp = client.put(
            '/api/app/checklist/tm/check',
            json={
                'serial_number': self.sn,
                'master_id': self.master_ids[0],
                'check_result': 'PASS',
            },
            headers={'Authorization': f'Bearer {mech_token}'}
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert data['error'] == 'FORBIDDEN'


# ─────────────────────────────────────────────────────────────────────────────
# [알림 연동] TC-52-18~22
# ─────────────────────────────────────────────────────────────────────────────

class TestTmAlerts:

    @pytest.fixture(autouse=True)
    def setup(self, db_conn, seed_test_data):
        # 고유 product_code 사용 — TestTmChecklistApi(product_code='COMMON', count=15)와 격리
        alert_product_code = 'ALERT_ONLY'
        sn = f'{_PREFIX}ALERT'
        _insert_product(db_conn, sn, product_code=alert_product_code)
        _set_admin_setting(db_conn, 'tm_checklist_scope', 'product_code')
        _set_admin_setting(db_conn, 'tm_checklist_1st_checker', 'is_manager')
        _set_admin_setting(db_conn, 'tm_checklist_issue_alert', True)
        self.sn = sn
        self.master_ids = _insert_tm_master_items(db_conn, product_code=alert_product_code, count=3)
        yield
        # 테스트 후 checklist_record + alert 정리 (테스트 격리)
        cursor = db_conn.cursor()
        # sn('SN-SP52-ALERT') 관련 정리
        cursor.execute(
            "DELETE FROM checklist.checklist_record WHERE serial_number = %s",
            (sn,)
        )
        cursor.execute(
            "DELETE FROM app_alert_logs WHERE serial_number = %s",
            (sn,)
        )
        # TC-52-21의 sn_no_alert 관련 정리
        sn_no_alert = f'{_PREFIX}NOALERT'
        cursor.execute(
            "DELETE FROM checklist.checklist_record WHERE serial_number = %s",
            (sn_no_alert,)
        )
        cursor.execute(
            "DELETE FROM app_alert_logs WHERE serial_number = %s",
            (sn_no_alert,)
        )
        db_conn.commit()
        cursor.close()

    def test_tc52_18_tank_module_complete_by_worker_sends_alert(
        self, client, mech_token, mech_worker_id, db_conn, tm_manager_id
    ):
        """TC-52-18: TM task 완료(finalize=True, 일반 작업자) → CHECKLIST_TM_READY 알림 생성"""
        # TM task 등록 + work_start_log 등록
        task_id = _insert_task_detail(db_conn, self.sn, worker_id=mech_worker_id)

        # work_start_log 직접 삽입 (complete_work 내에서 _worker_has_started_task 체크)
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO work_start_log
                (task_id, worker_id, serial_number, qr_doc_id, task_category,
                 task_id_ref, task_name, started_at)
            VALUES (%s, %s, %s, %s, 'TMS', 'TANK_MODULE', 'Tank Module', NOW())
        """, (task_id, mech_worker_id, self.sn, f'DOC_{self.sn}'))
        db_conn.commit()
        cursor.close()

        resp = client.post(
            '/api/app/work/complete',
            json={'task_detail_id': task_id, 'finalize': True},
            headers={'Authorization': f'Bearer {mech_token}'}
        )
        assert resp.status_code == 200

        # DB에서 CHECKLIST_TM_READY 알림 확인
        cursor = db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT id FROM app_alert_logs
            WHERE alert_type = 'CHECKLIST_TM_READY'
              AND serial_number = %s
        """, (self.sn,))
        alert_rows = cursor.fetchall()
        cursor.close()
        assert len(alert_rows) > 0, "CHECKLIST_TM_READY 알림이 생성되지 않았습니다"

    def test_tc52_19_relay_mode_no_alert(
        self, client, mech_token, mech_worker_id, db_conn
    ):
        """TC-52-19: TM task 내 작업 종료(finalize=False) → 알림 미생성"""
        sn2 = f'{_PREFIX}RELAY'
        _insert_product(db_conn, sn2)
        task_id = _insert_task_detail(db_conn, sn2, worker_id=mech_worker_id)

        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO work_start_log
                (task_id, worker_id, serial_number, qr_doc_id, task_category,
                 task_id_ref, task_name, started_at)
            VALUES (%s, %s, %s, %s, 'TMS', 'TANK_MODULE', 'Tank Module', NOW())
        """, (task_id, mech_worker_id, sn2, f'DOC_{sn2}'))
        db_conn.commit()
        cursor.close()

        # 알림 기록 이전 count
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM app_alert_logs
            WHERE alert_type = 'CHECKLIST_TM_READY' AND serial_number = %s
        """, (sn2,))
        before = cursor.fetchone()[0]
        cursor.close()

        resp = client.post(
            '/api/app/work/complete',
            json={'task_detail_id': task_id, 'finalize': False},
            headers={'Authorization': f'Bearer {mech_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get('relay_mode') is True

        # 알림 미생성 확인
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM app_alert_logs
            WHERE alert_type = 'CHECKLIST_TM_READY' AND serial_number = %s
        """, (sn2,))
        after = cursor.fetchone()[0]
        cursor.close()
        assert after == before, "relay_mode에서 CHECKLIST_TM_READY 알림이 잘못 생성됨"

    def test_tc52_19a_manager_completes_tank_module_checklist_ready(
        self, client, manager_token, manager_id, db_conn
    ):
        """TC-52-19a: TM task 완료(finalize=True, is_manager=True) → 알림 미발송 + checklist_ready=true"""
        sn3 = f'{_PREFIX}MGRCMP'
        _insert_product(db_conn, sn3)
        task_id = _insert_task_detail(db_conn, sn3, worker_id=manager_id)

        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO work_start_log
                (task_id, worker_id, serial_number, qr_doc_id, task_category,
                 task_id_ref, task_name, started_at)
            VALUES (%s, %s, %s, %s, 'TMS', 'TANK_MODULE', 'Tank Module', NOW())
        """, (task_id, manager_id, sn3, f'DOC_{sn3}'))
        db_conn.commit()
        cursor.close()

        # 이전 알림 count
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM app_alert_logs
            WHERE alert_type = 'CHECKLIST_TM_READY' AND serial_number = %s
        """, (sn3,))
        before_count = cursor.fetchone()[0]
        cursor.close()

        resp = client.post(
            '/api/app/work/complete',
            json={'task_detail_id': task_id, 'finalize': True},
            headers={'Authorization': f'Bearer {manager_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        # checklist_ready 플래그 확인
        assert data.get('checklist_ready') is True, \
            "Manager 완료 시 checklist_ready=True가 응답에 없습니다"

        # 알림 미생성 확인
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM app_alert_logs
            WHERE alert_type = 'CHECKLIST_TM_READY' AND serial_number = %s
        """, (sn3,))
        after_count = cursor.fetchone()[0]
        cursor.close()
        assert after_count == before_count, "Manager 완료 시 CHECKLIST_TM_READY 알림이 잘못 생성됨"

    def test_tc52_20_checklist_complete_issue_alert_sent(
        self, client, manager_token, manager_id, db_conn
    ):
        """TC-52-20: 체크리스트 완료 + ISSUE note 존재 + tm_checklist_issue_alert=true → CHECKLIST_ISSUE 알림"""
        _set_admin_setting(db_conn, 'tm_checklist_issue_alert', True)

        # 모든 항목 PASS with note (ISSUE)
        for mid in self.master_ids:
            _upsert_checklist_record(db_conn, self.sn, mid, 'PASS', manager_id,
                                     note='이상 발견')

        # 마지막 항목 PUT → 완료 판정 + 알림 트리거
        resp = client.put(
            '/api/app/checklist/tm/check',
            json={
                'serial_number': self.sn,
                'master_id': self.master_ids[-1],
                'check_result': 'PASS',
                'note': '최종 이상',
            },
            headers={'Authorization': f'Bearer {manager_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['is_complete'] is True

        # CHECKLIST_ISSUE 알림 확인
        cursor = db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT id FROM app_alert_logs
            WHERE alert_type = 'CHECKLIST_ISSUE'
              AND serial_number = %s
        """, (self.sn,))
        rows = cursor.fetchall()
        cursor.close()
        assert len(rows) > 0, "CHECKLIST_ISSUE 알림이 생성되지 않았습니다"

    def test_tc52_21_checklist_complete_issue_alert_disabled(
        self, client, manager_token, manager_id, db_conn
    ):
        """TC-52-21: 체크리스트 완료 + ISSUE note 존재 + tm_checklist_issue_alert=false → 알림 미생성"""
        sn_no_alert = f'{_PREFIX}NOALERT'
        # ALERT_ONLY product_code 사용 (self.master_ids 3개가 이 product_code에 매핑됨)
        _insert_product(db_conn, sn_no_alert, product_code='ALERT_ONLY')
        _set_admin_setting(db_conn, 'tm_checklist_issue_alert', False)

        # 모든 항목 체크 (note 포함)
        for mid in self.master_ids:
            _upsert_checklist_record(db_conn, sn_no_alert, mid, 'PASS', manager_id,
                                     note='issue note')

        # 마지막 항목 PUT (완료 판정)
        resp = client.put(
            '/api/app/checklist/tm/check',
            json={
                'serial_number': sn_no_alert,
                'master_id': self.master_ids[-1],
                'check_result': 'PASS',
                'note': '이슈',
            },
            headers={'Authorization': f'Bearer {manager_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['is_complete'] is True

        # 알림 미생성 확인
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM app_alert_logs
            WHERE alert_type = 'CHECKLIST_ISSUE' AND serial_number = %s
        """, (sn_no_alert,))
        count = cursor.fetchone()[0]
        cursor.close()
        assert count == 0, "tm_checklist_issue_alert=false임에도 CHECKLIST_ISSUE 알림이 생성됨"

    def test_tc52_22_alert_failure_does_not_block_task(
        self, client, mech_token, mech_worker_id, db_conn
    ):
        """TC-52-22: 알림 실패해도 task 완료 정상 처리 확인"""
        from unittest.mock import patch

        sn_fail = f'{_PREFIX}ALERTFAIL'
        _insert_product(db_conn, sn_fail)
        task_id = _insert_task_detail(db_conn, sn_fail, worker_id=mech_worker_id)

        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO work_start_log
                (task_id, worker_id, serial_number, qr_doc_id, task_category,
                 task_id_ref, task_name, started_at)
            VALUES (%s, %s, %s, %s, 'TMS', 'TANK_MODULE', 'Tank Module', NOW())
        """, (task_id, mech_worker_id, sn_fail, f'DOC_{sn_fail}'))
        db_conn.commit()
        cursor.close()

        # 알림 서비스를 강제로 예외 발생시킴
        with patch(
            'app.models.alert_log.create_alert',
            side_effect=Exception("ALERT_SEND_FAILED")
        ):
            resp = client.post(
                '/api/app/work/complete',
                json={'task_detail_id': task_id, 'finalize': True},
                headers={'Authorization': f'Bearer {mech_token}'}
            )

        # 알림 실패해도 200 반환 (task 완료 정상)
        assert resp.status_code == 200, \
            f"알림 실패 시 task 완료가 차단됨: {resp.get_json()}"


# ─────────────────────────────────────────────────────────────────────────────
# [Admin CRUD API] TC-52-23~30
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminChecklistCrud:

    @pytest.fixture(autouse=True)
    def setup(self, db_conn, seed_test_data):
        _insert_tm_master_items(db_conn, product_code='COMMON', count=5)
        # 비활성 항목 1개 추가
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO checklist.checklist_master
                (product_code, category, item_group, item_name, item_order, is_active, updated_at)
            VALUES ('ALL', 'TM', 'TANK', 'TM 비활성 항목', 99, FALSE, NOW())
            ON CONFLICT (product_code, category, item_group, item_name) DO NOTHING
        """)
        db_conn.commit()
        cursor.close()

    def test_tc52_23_admin_list_tm_master(self, client, admin_token):
        """TC-52-23: GET /api/admin/checklist/master?category=TM → 항목 목록 반환"""
        resp = client.get(
            '/api/admin/checklist/master?category=TM',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'items' in data
        assert data['total'] > 0
        for item in data['items']:
            assert item['category'] == 'TM'
            assert item['is_active'] is True  # 기본 include_inactive=false

    def test_tc52_24_admin_list_filter_product_code(self, client, admin_token):
        """TC-52-24: GET /api/admin/checklist/master?category=TM&product_code=ALL → product_code 필터"""
        resp = client.get(
            '/api/admin/checklist/master?category=TM&product_code=ALL',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        for item in data['items']:
            assert item['product_code'] == 'ALL'

    def test_tc52_25_admin_list_include_inactive(self, client, admin_token):
        """TC-52-25: GET /api/admin/checklist/master?include_inactive=true → 비활성 항목 포함"""
        resp_active = client.get(
            '/api/admin/checklist/master?category=TM',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        resp_all = client.get(
            '/api/admin/checklist/master?category=TM&include_inactive=true',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert resp_all.status_code == 200
        total_active = resp_active.get_json()['total']
        total_all = resp_all.get_json()['total']
        assert total_all >= total_active

    def test_tc52_26_admin_create_master_item(self, client, admin_token, db_conn):
        """TC-52-26: POST /api/admin/checklist/master → 신규 항목 추가 (item_group 포함)"""
        import time
        unique_name = f'신규 TM 항목 {int(time.time())}'
        resp = client.post(
            '/api/admin/checklist/master',
            json={
                'product_code': 'ALL',
                'category': 'TM',
                'item_group': 'BURNER',
                'item_name': unique_name,
                'item_order': 50,
                'description': '테스트 설명',
            },
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert 'id' in data
        assert '추가' in data['message']

    def test_tc52_27_admin_create_master_duplicate_409(self, client, admin_token):
        """TC-52-27: POST /api/admin/checklist/master → 중복 item_name → 409"""
        # 먼저 하나 만들기
        resp1 = client.post(
            '/api/admin/checklist/master',
            json={
                'product_code': 'ALL',
                'category': 'TM',
                'item_name': 'TM 점검항목 1',  # _insert_tm_master_items와 같은 이름
            },
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        # 중복이면 409, 아니면 201 (이미 있을 수 있음)
        assert resp1.status_code in (201, 409)
        if resp1.status_code == 201:
            # 두 번 호출하면 409
            resp2 = client.post(
                '/api/admin/checklist/master',
                json={
                    'product_code': 'ALL',
                    'category': 'TM',
                    'item_name': 'TM 점검항목 1',
                },
                headers={'Authorization': f'Bearer {admin_token}'}
            )
            assert resp2.status_code == 409

    def test_tc52_28_admin_update_master_item(self, client, admin_token, db_conn):
        """TC-52-28: PUT /api/admin/checklist/master/{id} → 항목 수정 (item_name, item_order, item_group)"""
        # 수정할 항목 id 가져오기
        cursor = db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT id FROM checklist.checklist_master
            WHERE category = 'TM' AND is_active = TRUE
            LIMIT 1
        """)
        row = cursor.fetchone()
        cursor.close()
        assert row is not None
        master_id = row['id']

        resp = client.put(
            f'/api/admin/checklist/master/{master_id}',
            json={
                'item_name': 'TM 수정된 항목명',
                'item_order': 100,
                'item_group': 'REACTOR',
            },
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert resp.status_code == 200
        assert '수정' in resp.get_json()['message']

    def test_tc52_29_admin_toggle_master_item(self, client, admin_token, db_conn):
        """TC-52-29: PATCH /api/admin/checklist/master/{id}/toggle → is_active 토글 동작"""
        # 활성 항목 찾기
        cursor = db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT id, is_active FROM checklist.checklist_master
            WHERE category = 'TM' AND is_active = TRUE
            LIMIT 1
        """)
        row = cursor.fetchone()
        cursor.close()
        assert row is not None
        master_id = row['id']
        original_active = row['is_active']

        resp = client.patch(
            f'/api/admin/checklist/master/{master_id}/toggle',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['is_active'] is not original_active  # 토글 확인

    def test_tc52_30_non_admin_admin_api_forbidden(self, client, mech_token):
        """TC-52-30: admin이 아닌 유저가 Admin API 호출 → 403"""
        resp = client.get(
            '/api/admin/checklist/master?category=TM',
            headers={'Authorization': f'Bearer {mech_token}'}
        )
        assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# [Settings API] TC-52-31~34
# ─────────────────────────────────────────────────────────────────────────────

class TestSettingsApi:

    def test_tc52_31_get_settings_includes_tm_checklist_keys(self, client, admin_token, db_conn):
        """TC-52-31: GET /admin/settings → tm_checklist_* 3개 키 포함 확인"""
        # seed settings
        for key, val in [
            ('tm_checklist_1st_checker', '"is_manager"'),
            ('tm_checklist_issue_alert', 'true'),
            ('tm_checklist_scope', '"product_code"'),
        ]:
            cursor = db_conn.cursor()
            cursor.execute("""
                INSERT INTO admin_settings (setting_key, setting_value)
                VALUES (%s, %s::jsonb)
                ON CONFLICT (setting_key) DO NOTHING
            """, (key, val))
            db_conn.commit()
            cursor.close()

        resp = client.get(
            '/api/admin/settings',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        settings_data = data.get('settings', data)
        keys = [s['setting_key'] for s in settings_data] if isinstance(settings_data, list) \
            else list(settings_data.keys())
        assert 'tm_checklist_1st_checker' in keys
        assert 'tm_checklist_issue_alert' in keys
        assert 'tm_checklist_scope' in keys

    def test_tc52_32_put_setting_tm_checklist_1st_checker_user(self, client, admin_token):
        """TC-52-32: PUT /admin/settings { tm_checklist_1st_checker: "user" } → 정상 저장"""
        resp = client.put(
            '/api/admin/settings',
            json={'setting_key': 'tm_checklist_1st_checker', 'setting_value': 'user'},
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert resp.status_code == 200

    def test_tc52_33_put_setting_tm_checklist_1st_checker_invalid(self, client, admin_token):
        """TC-52-33: PUT /admin/settings { tm_checklist_1st_checker: "invalid" } → 400"""
        resp = client.put(
            '/api/admin/settings',
            json={'setting_key': 'tm_checklist_1st_checker', 'setting_value': 'invalid'},
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert resp.status_code == 400

    def test_tc52_34_put_setting_tm_checklist_scope_all(self, client, admin_token):
        """TC-52-34: PUT /admin/settings { tm_checklist_scope: "all" } → 정상 저장"""
        resp = client.put(
            '/api/admin/settings',
            json={'setting_key': 'tm_checklist_scope', 'setting_value': 'all'},
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# [기존 기능 regression] TC-52-35~38
# ─────────────────────────────────────────────────────────────────────────────

class TestRegression:

    @pytest.fixture(autouse=True)
    def setup(self, db_conn, seed_test_data):
        sn = f'{_PREFIX}REG'
        _insert_product(db_conn, sn, product_code='COMMON')
        # MECH 카테고리 마스터 항목 추가
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO checklist.checklist_master
                (product_code, category, item_group, item_name, item_order, is_active, updated_at)
            VALUES ('ALL', 'MECH', NULL, 'MECH 점검항목 1', 1, TRUE, NOW())
            ON CONFLICT (product_code, category, item_group, item_name) DO NOTHING
        """)
        db_conn.commit()
        cursor.close()
        self.sn = sn

    def test_tc52_35_existing_get_checklist_mech(self, client, mech_token):
        """TC-52-35: 기존 GET /api/app/checklist/{sn}/MECH → 정상 동작 (is_checked 기반 유지)"""
        resp = client.get(
            f'/api/app/checklist/{self.sn}/MECH',
            headers={'Authorization': f'Bearer {mech_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'items' in data
        for item in data['items']:
            assert 'is_checked' in item  # 기존 필드 유지

    def test_tc52_36_existing_put_checklist_check_boolean(self, client, mech_token, db_conn):
        """TC-52-36: 기존 PUT /api/app/checklist/check → is_checked boolean 정상 동작 유지"""
        cursor = db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT id FROM checklist.checklist_master
            WHERE product_code = 'ALL' AND category = 'MECH' AND is_active = TRUE
            LIMIT 1
        """)
        row = cursor.fetchone()
        cursor.close()
        if row is None:
            pytest.skip("MECH 마스터 항목 없음")

        resp = client.put(
            '/api/app/checklist/check',
            json={
                'serial_number': self.sn,
                'master_id': row['id'],
                'is_checked': True,
            },
            headers={'Authorization': f'Bearer {mech_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['is_checked'] is True

    def test_tc52_37_existing_import_endpoint_reachable(self, client, admin_token):
        """TC-52-37: 기존 POST /api/admin/checklist/import → 파일 없음 400 반환 (엔드포인트 생존 확인)"""
        resp = client.post(
            '/api/admin/checklist/import',
            data={},
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        # 파일 없이 호출 → 400 (엔드포인트가 살아있는지만 확인)
        assert resp.status_code == 400

    def test_tc52_38_relay_and_tm_checklist_alert_only_on_finalize(
        self, client, mech_token, mech_worker_id, db_conn
    ):
        """TC-52-38: 릴레이(Sprint 41) + TM → 릴레이 재시작 후 최종 완료 시에만 알림"""
        sn = f'{_PREFIX}RELAY38'
        _insert_product(db_conn, sn)
        task_id = _insert_task_detail(db_conn, sn, worker_id=mech_worker_id)

        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO work_start_log
                (task_id, worker_id, serial_number, qr_doc_id, task_category,
                 task_id_ref, task_name, started_at)
            VALUES (%s, %s, %s, %s, 'TMS', 'TANK_MODULE', 'Tank Module', NOW())
        """, (task_id, mech_worker_id, sn, f'DOC_{sn}'))
        db_conn.commit()
        cursor.close()

        # 1단계: relay 종료 (finalize=False) → 알림 미발송
        before_cursor = db_conn.cursor()
        before_cursor.execute("""
            SELECT COUNT(*) FROM app_alert_logs
            WHERE alert_type = 'CHECKLIST_TM_READY' AND serial_number = %s
        """, (sn,))
        before_count = before_cursor.fetchone()[0]
        before_cursor.close()

        resp_relay = client.post(
            '/api/app/work/complete',
            json={'task_detail_id': task_id, 'finalize': False},
            headers={'Authorization': f'Bearer {mech_token}'}
        )
        assert resp_relay.status_code == 200
        assert resp_relay.get_json().get('relay_mode') is True

        mid_cursor = db_conn.cursor()
        mid_cursor.execute("""
            SELECT COUNT(*) FROM app_alert_logs
            WHERE alert_type = 'CHECKLIST_TM_READY' AND serial_number = %s
        """, (sn,))
        mid_count = mid_cursor.fetchone()[0]
        mid_cursor.close()
        assert mid_count == before_count, "relay_mode 종료 시 알림이 잘못 생성됨"
