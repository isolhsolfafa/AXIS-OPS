"""
Sprint 64-BE v3: Work Batch 엔드포인트 pytest TC (16+ TC)

검증 영역:
  - Unit: _match_manager_company() 12 case 전수 (TC-MATCH-UNIT-01 C1~C12)
  - 입력 검증: 빈 / >30 / 비-정수
  - 화이트리스트: NOT_TANK_MODULE 영역 분류
  - Manager 매핑: TMS(M) / FNI / BAT 영역 매트릭스
  - Audit log 1:1 정합: work_start_log / work_completion_log
  - 응답 shape: _task_to_dict() 전체 필드
"""
import pytest


# ── Unit test — _match_manager_company() 12 case 전수 (TC-MATCH-UNIT-01) ─

class TestMatchManagerCompanyUnit:
    """C1~C12 영역 + 보조 substring case (A-1 BACKLOG).

    ⚠️ `app` fixture 영역 의존: conftest L356 `app` fixture 영역 영역 sys.path 영역 영역 보장.
    """

    @pytest.fixture(autouse=True)
    def _import_helper(self, app):  # app fixture 영역 의존 → sys.path 영역 영역 보장
        from app.services.task_service_batch import _match_manager_company
        self.match = _match_manager_company

    def test_c1_tms_module_outsourcing_match(self):
        """TMS = module_outsourcing match (manager='TMS' vs mod='TMS')"""
        assert self.match('TMS', 'TMS', 'TMS', 'FNI') is True

    def test_c2_tms_or_mech_partner_match(self):
        """TMS OR mech_partner match (work.py L355 정합)"""
        assert self.match('TMS', 'TMS', None, 'TMS') is True

    def test_c3_tms_null_fallback(self):
        """TMS NULL fallback → False"""
        assert self.match('TMS', 'TMS', None, None) is False

    def test_c4_mech_partner_match(self):
        """MECH = mech_partner match"""
        assert self.match('TMS', 'MECH', None, 'TMS') is True

    def test_c5_mech_module_outsourcing_ignored(self):
        """MECH = mech_partner only, module_outsourcing 무시"""
        assert self.match('FNI', 'MECH', 'TMS', 'BAT') is False

    def test_c6_mech_null_fallback(self):
        """MECH NULL fallback → False"""
        assert self.match('FNI', 'MECH', None, None) is False

    def test_c7_tms_m_suffix_removed(self):
        """TMS(M) suffix 제거 후 매칭"""
        assert self.match('TMS(M)', 'TMS', 'TMS', 'FNI') is True

    def test_c8_tms_e_suffix_removed(self):
        """TMS(E) suffix 제거 후 매칭"""
        assert self.match('TMS(E)', 'TMS', 'TMS', 'FNI') is True

    def test_c9_empty_company(self):
        """empty company → False"""
        assert self.match('', 'TMS', 'TMS', 'FNI') is False

    def test_c10_pi_category_excluded(self):
        """PI 카테고리 → 영역 외, 무조건 False"""
        assert self.match('FNI', 'PI', 'TMS', 'FNI') is False

    def test_c11_qi_category_excluded(self):
        """QI 카테고리 → 영역 외, 무조건 False"""
        assert self.match('FNI', 'QI', 'TMS', 'FNI') is False

    def test_c12_si_category_excluded(self):
        """SI 카테고리 → 영역 외, 무조건 False"""
        assert self.match('FNI', 'SI', 'TMS', 'FNI') is False

    def test_a1_substring_false_positive_backlog(self):
        """⚠️ substring 영역 — BAT vs COMBAT (A-1 BACKLOG, 운영 미발생)"""
        # work.py L347 reactivate 패턴 정합 보존 — boundary-safe 영역 별 sprint
        assert self.match('BAT', 'MECH', None, 'COMBAT') is True


# ── Integration test 영역 ─────────────────────────────────────

@pytest.fixture
def admin_auth(get_auth_token, seed_manager_company_matrix):
    """Admin Bearer header"""
    token = get_auth_token(
        worker_id=seed_manager_company_matrix['admin'],
        email='batch-admin@test.axisos.com',
        role='QI', is_admin=True,
    )
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def tms_m_auth(get_auth_token, seed_manager_company_matrix):
    """TMS(M) manager Bearer header"""
    token = get_auth_token(
        worker_id=seed_manager_company_matrix['tms_m'],
        email='batch-tms-m@test.axisos.com',
        role='MECH',
    )
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def fni_auth(get_auth_token, seed_manager_company_matrix):
    """FNI manager Bearer header"""
    token = get_auth_token(
        worker_id=seed_manager_company_matrix['fni_m'],
        email='batch-fni-m@test.axisos.com',
        role='MECH',
    )
    return {'Authorization': f'Bearer {token}'}


class TestInputValidation:
    """입력 검증 영역 — 빈 / >30 / 비-정수"""

    def test_empty_array_400(self, client, admin_auth):
        resp = client.post('/api/app/work/start-batch',
                           headers=admin_auth, json={'task_detail_ids': []})
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'INVALID_REQUEST'

    def test_missing_field_400(self, client, admin_auth):
        resp = client.post('/api/app/work/start-batch',
                           headers=admin_auth, json={})
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'INVALID_REQUEST'

    def test_over_30_400(self, client, admin_auth):
        resp = client.post('/api/app/work/start-batch',
                           headers=admin_auth,
                           json={'task_detail_ids': list(range(1, 32))})  # 31개
        assert resp.status_code == 400
        assert '30' in resp.get_json()['message']

    def test_non_integer_400(self, client, admin_auth):
        resp = client.post('/api/app/work/start-batch',
                           headers=admin_auth,
                           json={'task_detail_ids': [1, 'invalid', 3]})
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'INVALID_REQUEST'


class TestWhitelistAndManager:
    """화이트리스트 + Manager 매트릭스"""

    def test_admin_30_tank_module_succeeded(
        self, client, admin_auth, seed_tank_module_tasks_batch
    ):
        """admin: 30 TANK_MODULE 시작 → 30 succeeded / 0 skipped"""
        task_ids = seed_tank_module_tasks_batch(n=30, partner='TMS', task_category='TMS')
        resp = client.post('/api/app/work/start-batch',
                           headers=admin_auth,
                           json={'task_detail_ids': task_ids})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['total'] == 30
        assert len(body['succeeded']) == 30
        assert len(body['skipped']) == 0

    def test_tms_m_manager_matching_company_succeeded(
        self, client, tms_m_auth, seed_tank_module_tasks_batch
    ):
        """TMS(M) manager: TMS task + module_outsourcing='TMS' → succeeded"""
        task_ids = seed_tank_module_tasks_batch(n=3, partner='TMS', task_category='TMS')
        resp = client.post('/api/app/work/start-batch',
                           headers=tms_m_auth,
                           json={'task_detail_ids': task_ids})
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body['succeeded']) == 3
        assert len(body['skipped']) == 0

    def test_fni_manager_other_company_forbidden(
        self, client, fni_auth, seed_tank_module_tasks_batch
    ):
        """FNI manager: TMS task (module_outsourcing='TMS') → FORBIDDEN_COMPANY"""
        task_ids = seed_tank_module_tasks_batch(n=3, partner='TMS', task_category='TMS')
        resp = client.post('/api/app/work/start-batch',
                           headers=fni_auth,
                           json={'task_detail_ids': task_ids})
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body['succeeded']) == 0
        assert len(body['skipped']) == 3
        assert all(s['reason'] == 'FORBIDDEN_COMPANY' for s in body['skipped'])

    def test_fni_manager_mech_partner_match_succeeded(
        self, client, fni_auth, seed_tank_module_tasks_batch
    ):
        """FNI manager: MECH TANK_MODULE + mech_partner='FNI' → succeeded"""
        task_ids = seed_tank_module_tasks_batch(n=3, partner='FNI', task_category='MECH')
        resp = client.post('/api/app/work/start-batch',
                           headers=fni_auth,
                           json={'task_detail_ids': task_ids})
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body['succeeded']) == 3

    def test_all_not_tank_module_400(
        self, client, admin_auth, db_conn, create_test_worker
    ):
        """모두 SELF_INSPECTION (non-TANK_MODULE) → 400 NOT_TANK_MODULE_ANY"""
        worker_id = create_test_worker(
            email='nottm-worker@test.axisos.com',
            password='Test123!', name='Not TM Worker', role='MECH',
        )
        cur = db_conn.cursor()
        cur.execute("""
            INSERT INTO plan.product_info (serial_number, model)
            VALUES ('NOTTM-001', 'GAIA') ON CONFLICT DO NOTHING
        """)
        cur.execute("""
            INSERT INTO qr_registry (qr_doc_id, serial_number, status)
            VALUES ('DOC_NOTTM-001', 'NOTTM-001', 'active') ON CONFLICT DO NOTHING
        """)
        cur.execute("""
            INSERT INTO app_task_details
                (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable)
            VALUES (%s, 'NOTTM-001', 'DOC_NOTTM-001', 'MECH', 'SELF_INSPECTION', '자주검사', TRUE)
            RETURNING id
        """, (worker_id,))
        task_id = cur.fetchone()[0]
        db_conn.commit()

        resp = client.post('/api/app/work/start-batch',
                           headers=admin_auth,
                           json={'task_detail_ids': [task_id]})
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'NOT_TANK_MODULE_ANY'

        # Cleanup
        cur.execute("DELETE FROM app_task_details WHERE id = %s", (task_id,))
        cur.execute("DELETE FROM qr_registry WHERE qr_doc_id = 'DOC_NOTTM-001'")
        cur.execute("DELETE FROM plan.product_info WHERE serial_number = 'NOTTM-001'")
        db_conn.commit()


class TestAuditLog:
    """Audit log 1:1 정합 — TC-AUDIT-01 / TC-AUDIT-02"""

    def test_audit_01_start_work_log_count_match(
        self, client, admin_auth, seed_tank_module_tasks_batch, assert_audit_log_count
    ):
        """TC-AUDIT-01: 5 start → work_start_log row +5 = succeeded 건수"""
        task_ids = seed_tank_module_tasks_batch(n=5, partner='TMS', task_category='TMS')
        resp = client.post('/api/app/work/start-batch',
                           headers=admin_auth,
                           json={'task_detail_ids': task_ids})
        assert resp.status_code == 200
        succeeded_count = len(resp.get_json()['succeeded'])
        assert_audit_log_count('work_start_log', task_ids, succeeded_count)

    def test_audit_02_complete_work_log_count_match(
        self, client, admin_auth, seed_tank_module_tasks_batch, assert_audit_log_count
    ):
        """TC-AUDIT-02: 5 start + 5 complete → work_completion_log row +5 (대칭)"""
        task_ids = seed_tank_module_tasks_batch(n=5, partner='TMS', task_category='TMS')
        # 1) Start 영역
        start_resp = client.post('/api/app/work/start-batch',
                                 headers=admin_auth,
                                 json={'task_detail_ids': task_ids})
        assert start_resp.status_code == 200
        # 2) Complete 영역
        complete_resp = client.post('/api/app/work/complete-batch',
                                    headers=admin_auth,
                                    json={'task_detail_ids': task_ids})
        assert complete_resp.status_code == 200
        succeeded_count = len(complete_resp.get_json()['succeeded'])
        assert_audit_log_count('work_completion_log', task_ids, succeeded_count)


class TestResponseShape:
    """응답 shape — TC-SHAPE-01 / TC-SHAPE-02"""

    EXPECTED_KEYS = {
        'id', 'task_category', 'task_id', 'task_name',
        'started_at', 'completed_at', 'is_applicable',
        'is_paused', 'total_pause_minutes',
        'force_closed', 'close_reason', 'closed_by_name',
    }

    def test_shape_01_start_updated_full_fields(
        self, client, admin_auth, seed_tank_module_tasks_batch
    ):
        """TC-SHAPE-01: start succeeded[i].updated 전체 shape"""
        task_ids = seed_tank_module_tasks_batch(n=2, partner='TMS', task_category='TMS')
        resp = client.post('/api/app/work/start-batch',
                           headers=admin_auth,
                           json={'task_detail_ids': task_ids})
        assert resp.status_code == 200
        for entry in resp.get_json()['succeeded']:
            updated = entry['updated']
            # 핵심 keys 영역 보유 검증 — _task_to_dict() 전체 영역 정합
            missing = self.EXPECTED_KEYS - set(updated.keys())
            assert not missing, f"누락 키 영역: {missing}"

    def test_shape_02_complete_updated_full_fields(
        self, client, admin_auth, seed_tank_module_tasks_batch
    ):
        """TC-SHAPE-02: complete succeeded[i].updated 전체 shape (start 대칭)"""
        task_ids = seed_tank_module_tasks_batch(n=2, partner='TMS', task_category='TMS')
        client.post('/api/app/work/start-batch',
                    headers=admin_auth, json={'task_detail_ids': task_ids})
        resp = client.post('/api/app/work/complete-batch',
                           headers=admin_auth, json={'task_detail_ids': task_ids})
        assert resp.status_code == 200
        for entry in resp.get_json()['succeeded']:
            updated = entry['updated']
            missing = self.EXPECTED_KEYS - set(updated.keys())
            assert not missing, f"누락 키 영역: {missing}"


class TestSkippedReasonMatrix:
    """skipped reason 매트릭스 — NOT_FOUND / ALREADY_STARTED / NOT_STARTED / ALREADY_COMPLETED"""

    def test_not_found_reason(self, client, admin_auth):
        """존재하지 않는 task_detail_id → NOT_FOUND"""
        resp = client.post('/api/app/work/start-batch',
                           headers=admin_auth,
                           json={'task_detail_ids': [999999999]})
        # 모두 NOT_FOUND → NOT_TANK_MODULE_ANY 영역 아님 (NOT_FOUND 영역 분리)
        # → 응답 200 + skipped 1건 (NOT_FOUND)
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body['skipped']) == 1
        assert body['skipped'][0]['reason'] == 'NOT_FOUND'

    def test_already_started_skip(
        self, client, admin_auth, seed_tank_module_tasks_batch
    ):
        """이미 시작된 task → 두 번째 호출 시 ALREADY_STARTED skip"""
        task_ids = seed_tank_module_tasks_batch(n=2, partner='TMS', task_category='TMS')
        client.post('/api/app/work/start-batch',
                    headers=admin_auth, json={'task_detail_ids': task_ids})
        # 두 번째 호출 영역
        resp = client.post('/api/app/work/start-batch',
                           headers=admin_auth, json={'task_detail_ids': task_ids})
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body['skipped']) == 2
        assert all(s['reason'] == 'ALREADY_STARTED' for s in body['skipped'])

    def test_complete_not_started_skip(
        self, client, admin_auth, seed_tank_module_tasks_batch
    ):
        """TC-COMPLETE-01: complete 시 시작 안 한 admin → FORBIDDEN_WORKER skip

        ⚠️ 실 helper 동작 검증: complete_work() L217 `_worker_has_started_task` False 분기가
        L233 `task.started_at` None 분기보다 먼저 발동. admin 이 cross-worker GST 영역 아닌
        경우 FORBIDDEN 반환 → `_COMPLETE_ERROR_TO_REASON['FORBIDDEN'] = 'FORBIDDEN_WORKER'`.
        NOT_STARTED 분기 도달은 cross-worker GST 영역에서만 가능 (실제로는 도달 거의 X).
        """
        task_ids = seed_tank_module_tasks_batch(n=2, partner='TMS', task_category='TMS')
        resp = client.post('/api/app/work/complete-batch',
                           headers=admin_auth, json={'task_detail_ids': task_ids})
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body['skipped']) == 2
        assert all(s['reason'] == 'FORBIDDEN_WORKER' for s in body['skipped'])

    def test_complete_already_completed_skip(
        self, client, admin_auth, seed_tank_module_tasks_batch
    ):
        """TC-COMPLETE-02: 이미 완료된 task → ALREADY_COMPLETED skip"""
        task_ids = seed_tank_module_tasks_batch(n=2, partner='TMS', task_category='TMS')
        client.post('/api/app/work/start-batch',
                    headers=admin_auth, json={'task_detail_ids': task_ids})
        client.post('/api/app/work/complete-batch',
                    headers=admin_auth, json={'task_detail_ids': task_ids})
        # 두 번째 complete 호출 영역
        resp = client.post('/api/app/work/complete-batch',
                           headers=admin_auth, json={'task_detail_ids': task_ids})
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body['skipped']) == 2
        assert all(s['reason'] == 'ALREADY_COMPLETED' for s in body['skipped'])
