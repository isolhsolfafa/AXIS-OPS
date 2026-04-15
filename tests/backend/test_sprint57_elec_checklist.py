"""
Sprint 57 ELEC 체크리스트 + 공정 시퀀스 변경 테스트
운영 DB 동일 seed 데이터 사용 (ELEC 31항목: WORKER 24 + QI 7)
"""

import sys
from pathlib import Path
_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest

_PREFIX = 'SN-SP57-'


def _insert_product(db_conn, sn, model='GAIA-I'):
    cur = db_conn.cursor()
    cur.execute("""
        INSERT INTO plan.product_info (serial_number, model, mech_partner, elec_partner, module_outsourcing, prod_date)
        VALUES (%s, %s, 'FNI', 'P&S', 'TMS', NOW()::date)
        ON CONFLICT (serial_number) DO NOTHING
    """, (sn, model))
    cur.execute("""
        INSERT INTO public.qr_registry (qr_doc_id, serial_number, status)
        VALUES (%s, %s, 'active') ON CONFLICT (qr_doc_id) DO NOTHING
    """, (f'DOC_{sn}', sn))
    db_conn.commit()
    cur.close()


def _insert_task(db_conn, sn, category, task_id, task_name, worker_id):
    cur = db_conn.cursor()
    cur.execute("""
        INSERT INTO app_task_details (serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable, worker_id)
        VALUES (%s, %s, %s, %s, %s, TRUE, %s)
        ON CONFLICT (serial_number, qr_doc_id, task_category, task_id) DO NOTHING RETURNING id
    """, (sn, f'DOC_{sn}', category, task_id, task_name, worker_id))
    row = cur.fetchone()
    db_conn.commit()
    cur.close()
    return row[0] if row else None


def _get_elec_master_ids(db_conn, checker_role=None):
    cur = db_conn.cursor()
    q = "SELECT id FROM checklist.checklist_master WHERE product_code='COMMON' AND category='ELEC' AND is_active=TRUE"
    p = []
    if checker_role:
        q += " AND checker_role=%s"
        p.append(checker_role)
    q += " ORDER BY item_group, item_order"
    cur.execute(q, p)
    ids = [row[0] for row in cur.fetchall()]
    cur.close()
    return ids


def _cleanup(db_conn, sn):
    cur = db_conn.cursor()
    try:
        cur.execute("DELETE FROM app_alert_logs WHERE serial_number=%s", (sn,))
        cur.execute("DELETE FROM checklist.checklist_record WHERE serial_number=%s", (sn,))
        cur.execute("DELETE FROM work_completion_log WHERE serial_number=%s", (sn,))
        cur.execute("DELETE FROM work_start_log WHERE serial_number=%s", (sn,))
        cur.execute("DELETE FROM work_pause_log WHERE task_id IN (SELECT id FROM app_task_details WHERE serial_number=%s)", (sn,))
        cur.execute("DELETE FROM app_task_details WHERE serial_number=%s", (sn,))
        cur.execute("DELETE FROM completion_status WHERE serial_number=%s", (sn,))
        cur.execute("DELETE FROM qr_registry WHERE serial_number=%s", (sn,))
        cur.execute("DELETE FROM plan.product_info WHERE serial_number=%s", (sn,))
        db_conn.commit()
    except Exception:
        db_conn.rollback()
    finally:
        cur.close()


class TestElecBasic:

    @pytest.fixture(autouse=True)
    def setup(self, db_conn, seed_test_data, create_test_worker, get_auth_token, client):
        self.db_conn = db_conn
        self.client = client
        self.sn = f'{_PREFIX}BASIC-01'
        self.worker_id = create_test_worker(
            email='sp57_elec@test.axisos.com', password='Test1234!',
            name='SP57 ELEC', role='ELEC', company='P&S'
        )
        self.token = get_auth_token(self.worker_id, role='ELEC')
        _insert_product(db_conn, self.sn)
        yield
        _cleanup(db_conn, self.sn)

    def test_tc57_01_final_task_ids(self):
        """TC-57-01: FINAL_TASK_IDS에 IF_2 포함, INSPECTION 미포함"""
        from app.services.task_service import FINAL_TASK_IDS
        assert 'IF_2' in FINAL_TASK_IDS
        assert 'INSPECTION' not in FINAL_TASK_IDS

    def test_tc57_02_inspection_start_checklist_ready(self):
        """TC-57-02: ELEC INSPECTION start -> checklist_ready=true"""
        _insert_task(self.db_conn, self.sn, 'ELEC', 'INSPECTION', '자주검사 (검수)', self.worker_id)
        resp = self.client.post('/api/app/work/start', json={
            'qr_doc_id': f'DOC_{self.sn}', 'task_category': 'ELEC', 'task_id': 'INSPECTION',
        }, headers={'Authorization': f'Bearer {self.token}'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get('checklist_ready') is True
        assert data.get('checklist_category') == 'ELEC'

    def test_tc57_04_get_elec_checklist_phase1_17_items(self):
        """TC-57-04: GET checklist/elec/{sn} phase=1 -> 17항목 (JIG 제외)"""
        resp = self.client.get(
            f'/api/app/checklist/elec/{self.sn}?phase=1',
            headers={'Authorization': f'Bearer {self.token}'}
        )
        assert resp.status_code == 200
        assert resp.get_json()['summary']['total'] == 16  # PANEL 11 + 조립 5 (버너 위 배선 phase1_applicable=FALSE)

    def test_tc57_04a_get_elec_checklist_phase2_31_items(self):
        """TC-57-04a: GET checklist/elec/{sn} phase=2 -> 31항목 (전체)"""
        resp = self.client.get(
            f'/api/app/checklist/elec/{self.sn}?phase=2',
            headers={'Authorization': f'Bearer {self.token}'}
        )
        assert resp.status_code == 200
        assert resp.get_json()['summary']['total'] == 31

    def test_tc57_04b_checker_role_in_response(self):
        """TC-57-04b: Phase 2 응답에 checker_role 포함 (WORKER + QI)"""
        resp = self.client.get(
            f'/api/app/checklist/elec/{self.sn}?phase=2',
            headers={'Authorization': f'Bearer {self.token}'}
        )
        items = [i for g in resp.get_json()['groups'] for i in g['items']]
        roles = {i['checker_role'] for i in items}
        assert 'WORKER' in roles
        assert 'QI' in roles

    def test_tc57_07_upsert_elec_check(self):
        """TC-57-07: PUT elec/check -> PASS"""
        mids = _get_elec_master_ids(self.db_conn, 'WORKER')
        resp = self.client.put('/api/app/checklist/elec/check', json={
            'serial_number': self.sn, 'master_id': mids[0], 'check_result': 'PASS',
        }, headers={'Authorization': f'Bearer {self.token}'})
        assert resp.status_code == 200
        assert resp.get_json()['check_result'] == 'PASS'

    def test_tc57_08_worker_can_check(self):
        """TC-57-08: 일반 작업자도 체크 가능"""
        mids = _get_elec_master_ids(self.db_conn, 'WORKER')
        resp = self.client.put('/api/app/checklist/elec/check', json={
            'serial_number': self.sn, 'master_id': mids[0], 'check_result': 'PASS',
        }, headers={'Authorization': f'Bearer {self.token}'})
        assert resp.status_code == 200


class TestElecCompletion:

    @pytest.fixture(autouse=True)
    def setup(self, db_conn, seed_test_data, create_test_worker, get_auth_token, client):
        self.db_conn = db_conn
        self.client = client
        self.sn = f'{_PREFIX}COMP-01'
        self.worker_id = create_test_worker(
            email='sp57_comp@test.axisos.com', password='Test1234!',
            name='SP57 Comp', role='ELEC', company='P&S'
        )
        self.token = get_auth_token(self.worker_id, role='ELEC')
        _insert_product(db_conn, self.sn)
        yield
        _cleanup(db_conn, self.sn)

    def test_tc58_01_phase1_and_phase2_complete(self):
        """TC-58B-01: Phase 1(17) + Phase 2(24) 모두 완료 -> True"""
        wids = _get_elec_master_ids(self.db_conn, 'WORKER')
        assert len(wids) == 24
        # Phase 1: 전체 WORKER (JIG 포함해도 PUT은 가능, completion은 JIG 제외 17건만 확인)
        for mid in wids:
            self.client.put('/api/app/checklist/elec/check', json={
                'serial_number': self.sn, 'master_id': mid, 'check_result': 'PASS',
                'judgment_phase': 1,
            }, headers={'Authorization': f'Bearer {self.token}'})
        # Phase 2: 전체 WORKER
        for mid in wids:
            self.client.put('/api/app/checklist/elec/check', json={
                'serial_number': self.sn, 'master_id': mid, 'check_result': 'PASS',
                'judgment_phase': 2,
            }, headers={'Authorization': f'Bearer {self.token}'})
        from app.services.checklist_service import check_elec_completion
        assert check_elec_completion(self.sn) is True

    def test_tc58_02_phase1_done_phase2_incomplete(self):
        """TC-58B-02: Phase 1 완료 + Phase 2 1건 미완 -> False"""
        wids = _get_elec_master_ids(self.db_conn, 'WORKER')
        for mid in wids:
            self.client.put('/api/app/checklist/elec/check', json={
                'serial_number': self.sn, 'master_id': mid, 'check_result': 'PASS',
                'judgment_phase': 1,
            }, headers={'Authorization': f'Bearer {self.token}'})
        # Phase 2: 23/24만 체크
        for mid in wids[:-1]:
            self.client.put('/api/app/checklist/elec/check', json={
                'serial_number': self.sn, 'master_id': mid, 'check_result': 'PASS',
                'judgment_phase': 2,
            }, headers={'Authorization': f'Bearer {self.token}'})
        from app.services.checklist_service import check_elec_completion
        assert check_elec_completion(self.sn) is False

    def test_tc58_03_phase1_incomplete_phase2_done(self):
        """TC-58B-03: Phase 1 1건 미완 + Phase 2 완료 -> False"""
        wids = _get_elec_master_ids(self.db_conn, 'WORKER')
        # Phase 1: PANEL만 (11개) — 조립 6개 미완
        panel_ids = [mid for mid in wids[:11]]  # 대략 PANEL 순서
        for mid in panel_ids:
            self.client.put('/api/app/checklist/elec/check', json={
                'serial_number': self.sn, 'master_id': mid, 'check_result': 'PASS',
                'judgment_phase': 1,
            }, headers={'Authorization': f'Bearer {self.token}'})
        # Phase 2: 전체
        for mid in wids:
            self.client.put('/api/app/checklist/elec/check', json={
                'serial_number': self.sn, 'master_id': mid, 'check_result': 'PASS',
                'judgment_phase': 2,
            }, headers={'Authorization': f'Bearer {self.token}'})
        from app.services.checklist_service import check_elec_completion
        assert check_elec_completion(self.sn) is False

    def test_tc58_04_qi_excluded_from_completion(self):
        """TC-58B-04: QI 미완 + WORKER Phase 1+2 전부 완료 -> True"""
        wids = _get_elec_master_ids(self.db_conn, 'WORKER')
        qids = _get_elec_master_ids(self.db_conn, 'QI')
        assert len(qids) == 7
        for phase in [1, 2]:
            for mid in wids:
                self.client.put('/api/app/checklist/elec/check', json={
                    'serial_number': self.sn, 'master_id': mid, 'check_result': 'PASS',
                    'judgment_phase': phase,
                }, headers={'Authorization': f'Bearer {self.token}'})
        # QI 항목 미체크
        from app.services.checklist_service import check_elec_completion
        assert check_elec_completion(self.sn) is True

    def test_tc58_08_no_master_returns_false(self):
        """TC-58B-08: ELEC 마스터 없는 S/N -> False"""
        from app.services.checklist_service import check_elec_completion
        assert check_elec_completion('NONEXISTENT-SN-99999') is False


class TestSprint60Normalization:
    """Sprint 60-BE: phase1_applicable 컬럼 기반 검증"""

    def test_tc60_01_phase1_applicable_column_exists(self, db_conn, seed_test_data):
        """TC-60B-01: phase1_applicable 컬럼 존재"""
        cur = db_conn.cursor()
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema='checklist' AND table_name='checklist_master'
              AND column_name IN ('phase1_applicable','qi_check_required','remarks')
        """)
        cols = {row[0] for row in cur.fetchall()}
        cur.close()
        assert cols == {'phase1_applicable', 'qi_check_required', 'remarks'}

    def test_tc60_02_jig_phase1_false_qi_true(self, db_conn, seed_test_data):
        """TC-60B-02: JIG 그룹 phase1_applicable=FALSE, qi_check_required=TRUE"""
        cur = db_conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM checklist.checklist_master
            WHERE category='ELEC' AND item_group='JIG 검사 및 특별관리 POINT'
              AND phase1_applicable=FALSE AND qi_check_required=TRUE AND is_active=TRUE
        """)
        assert cur.fetchone()[0] == 14  # WORKER 7 + QI 7
        cur.close()

    def test_tc60_03_burner_phase1_false(self, db_conn, seed_test_data):
        """TC-60B-03: 버너 위 배선상태 phase1_applicable=FALSE"""
        cur = db_conn.cursor()
        cur.execute("""
            SELECT phase1_applicable FROM checklist.checklist_master
            WHERE category='ELEC' AND item_name='버너 위 배선상태'
        """)
        row = cur.fetchone()
        cur.close()
        assert row is not None
        assert row[0] is False

    def test_tc60_04_panel_phase1_true(self, db_conn, seed_test_data):
        """TC-60B-04: PANEL 항목 기본값 phase1_applicable=TRUE"""
        cur = db_conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM checklist.checklist_master
            WHERE category='ELEC' AND item_group='PANEL 검사'
              AND phase1_applicable=TRUE AND qi_check_required=FALSE AND is_active=TRUE
        """)
        assert cur.fetchone()[0] == 11
        cur.close()

    def test_tc60_05_total_31_rows(self, db_conn, seed_test_data):
        """TC-60B-06: 전체 31 row 유지 (물리 삭제 없음)"""
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM checklist.checklist_master WHERE category='ELEC' AND is_active=TRUE")
        assert cur.fetchone()[0] == 31
        cur.close()

    def test_tc60_06_api_response_has_new_fields(self, db_conn, seed_test_data, create_test_worker, get_auth_token, client):
        """TC-60B-17: GET 마스터 API에 phase1_applicable, qi_check_required 포함"""
        admin_id = create_test_worker(
            email='sp60_admin@test.axisos.com', password='Test1234!',
            name='SP60 Admin', role='QI', is_admin=True, company='GST'
        )
        token = get_auth_token(admin_id, role='QI', is_admin=True)
        resp = client.get(
            '/api/admin/checklist/master?category=ELEC',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] > 0
        item = data['items'][0]
        assert 'phase1_applicable' in item
        assert 'qi_check_required' in item


class TestFreerollRegression:

    def test_tc57_18_inspection_not_final(self):
        from app.services.task_service import FINAL_TASK_IDS
        assert 'INSPECTION' not in FINAL_TASK_IDS

    def test_tc57_19_self_inspection_still_final(self):
        from app.services.task_service import FINAL_TASK_IDS
        assert 'SELF_INSPECTION' in FINAL_TASK_IDS

    def test_tc57_20_pressure_test_still_final(self):
        from app.services.task_service import FINAL_TASK_IDS
        assert 'PRESSURE_TEST' in FINAL_TASK_IDS

    def test_tc57_25_tm_checker_role_worker(self, db_conn, seed_test_data):
        """TC-57-25: TM 조회 시 checker_role='WORKER' (하위호환)"""
        cur = db_conn.cursor()
        cur.execute("""
            SELECT COALESCE(checker_role, 'WORKER') AS cr
            FROM checklist.checklist_master
            WHERE category='TM' AND product_code='COMMON' AND is_active=TRUE
        """)
        roles = {row[0] for row in cur.fetchall()}
        cur.close()
        assert roles == {'WORKER'}
