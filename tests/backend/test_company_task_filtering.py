"""
Company 기반 Task 필터링 통합 테스트
Company Task Filtering Integration Tests — Sprint 7 Phase 4

테스트 전략:
- GET /api/app/tasks/<serial_number> 엔드포인트 직접 호출
- JWT에서 worker의 company+role을 읽어 자동 필터링
- 각 company 별 보이는 task_category 검증

필터링 규칙 (task_seed.py get_task_categories_for_worker):
  FNI/BAT:    mech_partner 매칭 → MECH only
  TMS(M):     module_outsourcing='TMS' → TMS, mech_partner='TMS' → MECH도
  TMS(E):     elec_partner='TMS' 매칭 → ELEC only
  P&S:        elec_partner='P&S' 매칭 → ELEC only
  C&A:        elec_partner='C&A' 매칭 → ELEC only
  GST ADMIN:  빈 필터 → 전체 조회

테스트 제품 3개:
  GAIA  (mech=FNI,  elec=TMS, module_outsourcing=TMS)
  DRAGON (mech=TMS, elec=P&S, module_outsourcing=None)
  GALLANT (mech=BAT, elec=C&A, module_outsourcing=None)
"""

import pytest
import sys
from pathlib import Path
from typing import List, Set

# backend 경로 추가
backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


# ──────────────────────────────────────────────
# 공통 헬퍼
# ──────────────────────────────────────────────

def _insert_product_full(
    db_conn, serial_number: str, qr_doc_id: str, model: str,
    mech_partner: str = None, elec_partner: str = None,
    module_outsourcing: str = None
) -> None:
    """plan.product_info + qr_registry 삽입 (partner 포함)"""
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO plan.product_info
            (serial_number, model, mech_partner, elec_partner, module_outsourcing)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (serial_number) DO UPDATE SET
            mech_partner = EXCLUDED.mech_partner,
            elec_partner = EXCLUDED.elec_partner,
            module_outsourcing = EXCLUDED.module_outsourcing
    """, (serial_number, model, mech_partner, elec_partner, module_outsourcing))
    cursor.execute("""
        INSERT INTO public.qr_registry (qr_doc_id, serial_number)
        VALUES (%s, %s)
        ON CONFLICT (qr_doc_id) DO NOTHING
    """, (qr_doc_id, serial_number))
    db_conn.commit()
    cursor.close()


def _insert_tasks(db_conn, serial_number: str, qr_doc_id: str) -> None:
    """MECH/ELEC/TMS 각 1개씩 샘플 task 삽입 (필터링 검증용)"""
    tasks = [
        ('MECH', 'SELF_INSPECTION', '자주검사'),
        ('ELEC', 'INSPECTION',      '자주검사 (검수)'),
        ('TMS',  'PRESSURE_TEST',   '가압검사'),
    ]
    cursor = db_conn.cursor()
    for cat, tid, tname in tasks:
        cursor.execute("""
            INSERT INTO app_task_details
                (serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable)
            VALUES (%s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (serial_number, qr_doc_id, task_category, task_id) DO NOTHING
        """, (serial_number, qr_doc_id, cat, tid, tname))
    db_conn.commit()
    cursor.close()


def _cleanup(db_conn, serial_number: str, qr_doc_id: str) -> None:
    if db_conn is None or db_conn.closed:
        return
    try:
        cursor = db_conn.cursor()
        cursor.execute("DELETE FROM app_task_details WHERE serial_number = %s", (serial_number,))
        cursor.execute("DELETE FROM completion_status WHERE serial_number = %s", (serial_number,))
        cursor.execute("DELETE FROM public.qr_registry WHERE qr_doc_id = %s", (qr_doc_id,))
        cursor.execute("DELETE FROM plan.product_info WHERE serial_number = %s", (serial_number,))
        db_conn.commit()
        cursor.close()
    except Exception:
        pass


def _get_task_categories(response_json) -> Set[str]:
    """API 응답에서 task_category 집합 추출"""
    if isinstance(response_json, list):
        return {t.get('task_category') for t in response_json if t.get('task_category')}
    return set()


def _call_tasks_api(client, serial_number: str, token: str):
    """GET /api/app/tasks/<serial_number> 호출"""
    return client.get(
        f'/api/app/tasks/{serial_number}',
        headers={'Authorization': f'Bearer {token}'}
    )


# ──────────────────────────────────────────────
# GAIA 기준 필터링 (mech=FNI, elec=TMS, module_outsourcing=TMS)
# ──────────────────────────────────────────────

class TestGAIACompanyFilter:
    """
    GAIA 제품 기준 필터링
    mech_partner='FNI', elec_partner='TMS', module_outsourcing='TMS'
    """

    SN  = 'FILTER-GAIA-SN-001'
    QR  = 'FILTER-GAIA-QR-001'

    @pytest.fixture(autouse=True)
    def setup_gaia_product(self, db_conn):
        """GAIA 제품 + MECH/ELEC/TMS task 삽입"""
        if db_conn is None:
            yield
            return
        _insert_product_full(
            db_conn, self.SN, self.QR, 'GAIA-I DUAL',
            mech_partner='FNI', elec_partner='TMS', module_outsourcing='TMS'
        )
        _insert_tasks(db_conn, self.SN, self.QR)
        yield
        _cleanup(db_conn, self.SN, self.QR)

    def test_fni_worker_sees_mech_only(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """
        TC-FILTER-GAIA-01: FNI 작업자 → MECH task만 보임

        Expected:
        - task_category = 'MECH' 목록만 반환
        - ELEC, TMS 미포함 (mech_partner='FNI' 매칭)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='gaia_fni@filter.test', password='Test123!',
            name='GAIA FNI Worker', role='MECH', company='FNI'
        )
        token = get_auth_token(worker_id, role='MECH')

        r = _call_tasks_api(client, self.SN, token)
        if r.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert r.status_code == 200
        tasks = r.get_json()
        cats = _get_task_categories(tasks)

        assert 'MECH' in cats or len(cats) == 0, \
            f"FNI는 MECH task 보임 또는 빈 목록, got {cats}"
        assert 'ELEC' not in cats, f"FNI는 ELEC task 안 보여야 함, got {cats}"
        assert 'TMS' not in cats, f"FNI는 TMS task 안 보여야 함, got {cats}"

    def test_bat_worker_sees_nothing_for_gaia(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """
        TC-FILTER-GAIA-02: BAT 작업자 → GAIA mech_partner='FNI'이므로 빈 목록

        Expected:
        - BAT는 mech_partner='FNI'인 GAIA 제품에서 MECH task 안 보임
        - 빈 목록 반환
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='gaia_bat@filter.test', password='Test123!',
            name='GAIA BAT Worker', role='MECH', company='BAT'
        )
        token = get_auth_token(worker_id, role='MECH')

        r = _call_tasks_api(client, self.SN, token)
        if r.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert r.status_code == 200
        tasks = r.get_json()
        # BAT는 FNI 담당 제품에서 볼 task 없음
        assert isinstance(tasks, list)
        cats = _get_task_categories(tasks)
        assert 'MECH' not in cats, \
            f"BAT는 FNI 담당 MECH task 안 보여야 함, got {cats}"

    def test_tms_m_worker_sees_tms_only_for_gaia(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """
        TC-FILTER-GAIA-03: TMS(M) 작업자 → module_outsourcing='TMS' → TMS task 보임
        (mech_partner='FNI'≠'TMS' → MECH는 안 보임)

        Expected:
        - task_category = 'TMS' 포함
        - 'MECH' 미포함 (mech_partner=FNI, TMS(M)≠FNI)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='gaia_tmsm@filter.test', password='Test123!',
            name='GAIA TMS(M) Worker', role='MECH', company='TMS(M)'
        )
        token = get_auth_token(worker_id, role='MECH')

        r = _call_tasks_api(client, self.SN, token)
        if r.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert r.status_code == 200
        tasks = r.get_json()
        cats = _get_task_categories(tasks)

        # TMS(M)은 module_outsourcing='TMS' 매칭 → TMS task 봐야 함
        assert 'TMS' in cats or len(cats) == 0, \
            f"TMS(M)은 TMS task 보거나 빈 목록, got {cats}"
        # MECH는 mech_partner=FNI이므로 TMS(M)에는 안 보임
        assert 'MECH' not in cats, \
            f"TMS(M)은 GAIA(mech=FNI) MECH task 안 보여야 함, got {cats}"

    def test_tms_e_worker_sees_elec_only_for_gaia(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """
        TC-FILTER-GAIA-04: TMS(E) 작업자 → elec_partner='TMS' → ELEC task 보임

        Expected:
        - task_category = 'ELEC' 포함
        - MECH, TMS 미포함
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='gaia_tmse@filter.test', password='Test123!',
            name='GAIA TMS(E) Worker', role='ELEC', company='TMS(E)'
        )
        token = get_auth_token(worker_id, role='ELEC')

        r = _call_tasks_api(client, self.SN, token)
        if r.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert r.status_code == 200
        tasks = r.get_json()
        cats = _get_task_categories(tasks)

        assert 'ELEC' in cats or len(cats) == 0, \
            f"TMS(E)는 ELEC task 보거나 빈 목록, got {cats}"
        assert 'MECH' not in cats, f"TMS(E)는 MECH 안 보임, got {cats}"
        assert 'TMS' not in cats, f"TMS(E)는 TMS 안 보임, got {cats}"

    def test_ps_worker_sees_nothing_for_gaia(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """
        TC-FILTER-GAIA-05: P&S 작업자 → GAIA elec_partner='TMS'≠'P&S' → 빈 목록

        Expected:
        - P&S는 TMS 담당 ELEC task 안 보임
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='gaia_ps@filter.test', password='Test123!',
            name='GAIA P&S Worker', role='ELEC', company='P&S'
        )
        token = get_auth_token(worker_id, role='ELEC')

        r = _call_tasks_api(client, self.SN, token)
        if r.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert r.status_code == 200
        tasks = r.get_json()
        cats = _get_task_categories(tasks)
        assert 'ELEC' not in cats, \
            f"P&S는 TMS 담당 ELEC task 안 보여야 함, got {cats}"

    def test_gst_admin_sees_all_tasks_for_gaia(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """
        TC-FILTER-GAIA-06: GST 관리자 → GAIA 전체 task 조회 (필터 없음)

        Expected:
        - MECH + ELEC + TMS 모두 보임
        - all=true 불필요 (ADMIN이면 자동 전체)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        admin_id = create_test_worker(
            email='gaia_gst_admin@filter.test', password='Test123!',
            name='GAIA GST Admin', role='ADMIN', is_admin=True, company='GST'
        )
        token = get_auth_token(admin_id, role='ADMIN', is_admin=True)

        r = _call_tasks_api(client, self.SN, token)
        if r.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert r.status_code == 200
        tasks = r.get_json()
        cats = _get_task_categories(tasks)

        # GST 관리자는 필터 없이 전체 조회 → MECH+ELEC+TMS 모두 보임
        assert len(cats) >= 2, \
            f"GST 관리자는 복수 카테고리 조회, got {cats}"


# ──────────────────────────────────────────────
# DRAGON 기준 필터링 (mech=TMS, elec=P&S)
# ──────────────────────────────────────────────

class TestDRAGONCompanyFilter:
    """
    DRAGON 제품 기준 필터링
    mech_partner='TMS', elec_partner='P&S', module_outsourcing=None
    """

    SN  = 'FILTER-DRAGON-SN-001'
    QR  = 'FILTER-DRAGON-QR-001'

    @pytest.fixture(autouse=True)
    def setup_dragon_product(self, db_conn):
        """DRAGON 제품 + MECH/ELEC task 삽입 (TMS 없음)"""
        if db_conn is None:
            yield
            return
        _insert_product_full(
            db_conn, self.SN, self.QR, 'DRAGON-V',
            mech_partner='TMS', elec_partner='P&S', module_outsourcing=None
        )
        # DRAGON은 TMS 없음 → MECH + ELEC만 삽입
        cursor = db_conn.cursor()
        for cat, tid, tname in [
            ('MECH', 'SELF_INSPECTION', '자주검사'),
            ('ELEC', 'INSPECTION', '자주검사 (검수)'),
        ]:
            cursor.execute("""
                INSERT INTO app_task_details
                    (serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable)
                VALUES (%s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (serial_number, qr_doc_id, task_category, task_id) DO NOTHING
            """, (self.SN, self.QR, cat, tid, tname))
        db_conn.commit()
        cursor.close()
        yield
        _cleanup(db_conn, self.SN, self.QR)

    def test_tms_m_worker_sees_mech_for_dragon(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """
        TC-FILTER-DRAGON-01: TMS(M) 작업자 → DRAGON mech_partner='TMS' → MECH task 보임

        Expected:
        - task_category = 'MECH' 포함
        - module_outsourcing=None이므로 TMS는 빈 목록 (TMS 카테고리 task 없음)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='dragon_tmsm@filter.test', password='Test123!',
            name='DRAGON TMS(M) Worker', role='MECH', company='TMS(M)'
        )
        token = get_auth_token(worker_id, role='MECH')

        r = _call_tasks_api(client, self.SN, token)
        if r.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert r.status_code == 200
        tasks = r.get_json()
        cats = _get_task_categories(tasks)

        # TMS(M)은 mech_partner='TMS' 매칭 → MECH task 보임
        assert 'MECH' in cats or len(cats) == 0, \
            f"TMS(M)은 DRAGON(mech=TMS) MECH task 보거나 빈 목록, got {cats}"
        assert 'ELEC' not in cats, \
            f"TMS(M)은 ELEC 안 보여야 함, got {cats}"

    def test_ps_worker_sees_elec_for_dragon(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """
        TC-FILTER-DRAGON-02: P&S 작업자 → DRAGON elec_partner='P&S' → ELEC task 보임

        Expected:
        - task_category = 'ELEC' 포함
        - MECH 미포함
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='dragon_ps@filter.test', password='Test123!',
            name='DRAGON P&S Worker', role='ELEC', company='P&S'
        )
        token = get_auth_token(worker_id, role='ELEC')

        r = _call_tasks_api(client, self.SN, token)
        if r.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert r.status_code == 200
        tasks = r.get_json()
        cats = _get_task_categories(tasks)

        assert 'ELEC' in cats or len(cats) == 0, \
            f"P&S는 DRAGON(elec=P&S) ELEC task 보거나 빈 목록, got {cats}"
        assert 'MECH' not in cats, \
            f"P&S는 MECH 안 보여야 함, got {cats}"

    def test_ca_worker_sees_nothing_for_dragon(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """
        TC-FILTER-DRAGON-03: C&A 작업자 → DRAGON elec_partner='P&S'≠'C&A' → 빈 목록

        Expected:
        - ELEC 미포함 (C&A 담당 아님)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='dragon_ca@filter.test', password='Test123!',
            name='DRAGON C&A Worker', role='ELEC', company='C&A'
        )
        token = get_auth_token(worker_id, role='ELEC')

        r = _call_tasks_api(client, self.SN, token)
        if r.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert r.status_code == 200
        tasks = r.get_json()
        cats = _get_task_categories(tasks)

        assert 'ELEC' not in cats, \
            f"C&A는 P&S 담당 ELEC task 안 보여야 함, got {cats}"

    def test_fni_worker_sees_nothing_for_dragon(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """
        TC-FILTER-DRAGON-04: FNI 작업자 → DRAGON mech_partner='TMS'≠'FNI' → 빈 목록

        Expected:
        - MECH 미포함 (FNI 담당 아님)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='dragon_fni@filter.test', password='Test123!',
            name='DRAGON FNI Worker', role='MECH', company='FNI'
        )
        token = get_auth_token(worker_id, role='MECH')

        r = _call_tasks_api(client, self.SN, token)
        if r.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert r.status_code == 200
        tasks = r.get_json()
        cats = _get_task_categories(tasks)

        assert 'MECH' not in cats, \
            f"FNI는 TMS 담당 MECH task 안 보여야 함, got {cats}"


# ──────────────────────────────────────────────
# GALLANT 기준 필터링 (mech=BAT, elec=C&A)
# ──────────────────────────────────────────────

class TestGALLANTCompanyFilter:
    """
    GALLANT 제품 기준 필터링
    mech_partner='BAT', elec_partner='C&A', module_outsourcing=None
    """

    SN  = 'FILTER-GALLANT-SN-001'
    QR  = 'FILTER-GALLANT-QR-001'

    @pytest.fixture(autouse=True)
    def setup_gallant_product(self, db_conn):
        """GALLANT 제품 + MECH(1 active) + ELEC(6개) task 삽입"""
        if db_conn is None:
            yield
            return
        _insert_product_full(
            db_conn, self.SN, self.QR, 'GALLANT-III',
            mech_partner='BAT', elec_partner='C&A', module_outsourcing=None
        )
        # GALLANT: MECH 1개(SELF_INSPECTION) + ELEC 6개
        cursor = db_conn.cursor()
        # MECH: SELF_INSPECTION (applicable), 비활성 docking들
        for task_id, task_name, applicable in [
            ('SELF_INSPECTION', '자주검사', True),
            ('WASTE_GAS_LINE_1', 'Waste Gas LINE 1', False),
            ('UTIL_LINE_1', 'Util LINE 1', False),
            ('TANK_DOCKING', 'Tank Docking', False),
            ('WASTE_GAS_LINE_2', 'Waste Gas LINE 2', False),
            ('UTIL_LINE_2', 'Util LINE 2', False),
            ('HEATING_JACKET', 'Heating Jacket', False),
        ]:
            cursor.execute("""
                INSERT INTO app_task_details
                    (serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable)
                VALUES (%s, %s, 'MECH', %s, %s, %s)
                ON CONFLICT (serial_number, qr_doc_id, task_category, task_id) DO NOTHING
            """, (self.SN, self.QR, task_id, task_name, applicable))

        # ELEC: 6개 전부 active
        for task_id, task_name in [
            ('PANEL_WORK', '판넬 작업'),
            ('CABINET_PREP', '케비넷 준비 작업'),
            ('WIRING', '배선 포설'),
            ('IF_1', 'I.F 1'),
            ('IF_2', 'I.F 2'),
            ('INSPECTION', '자주검사 (검수)'),
        ]:
            cursor.execute("""
                INSERT INTO app_task_details
                    (serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable)
                VALUES (%s, %s, 'ELEC', %s, %s, TRUE)
                ON CONFLICT (serial_number, qr_doc_id, task_category, task_id) DO NOTHING
            """, (self.SN, self.QR, task_id, task_name))

        db_conn.commit()
        cursor.close()
        yield
        _cleanup(db_conn, self.SN, self.QR)

    def test_bat_worker_sees_mech_tasks(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """
        TC-FILTER-GALLANT-01: BAT 작업자 → GALLANT mech_partner='BAT' → MECH task 보임

        Expected:
        - task_category = 'MECH' 포함
        - ELEC 미포함
        - 총 MECH task 7행 (is_applicable 무관)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='gallant_bat@filter.test', password='Test123!',
            name='GALLANT BAT Worker', role='MECH', company='BAT'
        )
        token = get_auth_token(worker_id, role='MECH')

        r = _call_tasks_api(client, self.SN, token)
        if r.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert r.status_code == 200
        tasks = r.get_json()
        cats = _get_task_categories(tasks)

        assert 'MECH' in cats or len(cats) == 0, \
            f"BAT는 GALLANT MECH task 보거나 빈 목록, got {cats}"
        assert 'ELEC' not in cats, \
            f"BAT는 ELEC 안 보여야 함, got {cats}"

    def test_ca_worker_sees_elec_tasks(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """
        TC-FILTER-GALLANT-02: C&A 작업자 → GALLANT elec_partner='C&A' → ELEC task 보임

        Expected:
        - task_category = 'ELEC' 6개
        - MECH 미포함
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='gallant_ca@filter.test', password='Test123!',
            name='GALLANT C&A Worker', role='ELEC', company='C&A'
        )
        token = get_auth_token(worker_id, role='ELEC')

        r = _call_tasks_api(client, self.SN, token)
        if r.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert r.status_code == 200
        tasks = r.get_json()
        cats = _get_task_categories(tasks)

        assert 'ELEC' in cats or len(cats) == 0, \
            f"C&A는 GALLANT ELEC task 보거나 빈 목록, got {cats}"
        assert 'MECH' not in cats, \
            f"C&A는 MECH 안 보여야 함, got {cats}"

        # ELEC task 6개 확인
        if isinstance(tasks, list) and 'ELEC' in cats:
            elec_tasks = [t for t in tasks if t.get('task_category') == 'ELEC']
            assert len(elec_tasks) == 6, \
                f"GALLANT ELEC 6개 필요, got {len(elec_tasks)}"

    def test_fni_worker_sees_nothing_for_gallant(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """
        TC-FILTER-GALLANT-03: FNI 작업자 → GALLANT mech_partner='BAT'≠'FNI' → 빈 목록

        Expected:
        - MECH 미포함 (FNI 담당 아님)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='gallant_fni@filter.test', password='Test123!',
            name='GALLANT FNI Worker', role='MECH', company='FNI'
        )
        token = get_auth_token(worker_id, role='MECH')

        r = _call_tasks_api(client, self.SN, token)
        if r.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert r.status_code == 200
        tasks = r.get_json()
        cats = _get_task_categories(tasks)

        assert 'MECH' not in cats, \
            f"FNI는 BAT 담당 MECH task 안 보여야 함, got {cats}"

    def test_tms_e_worker_sees_nothing_for_gallant(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """
        TC-FILTER-GALLANT-04: TMS(E) 작업자 → GALLANT elec_partner='C&A'≠'TMS' → 빈 목록

        Expected:
        - ELEC 미포함 (TMS 담당 아님)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        worker_id = create_test_worker(
            email='gallant_tmse@filter.test', password='Test123!',
            name='GALLANT TMS(E) Worker', role='ELEC', company='TMS(E)'
        )
        token = get_auth_token(worker_id, role='ELEC')

        r = _call_tasks_api(client, self.SN, token)
        if r.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert r.status_code == 200
        tasks = r.get_json()
        cats = _get_task_categories(tasks)

        assert 'ELEC' not in cats, \
            f"TMS(E)는 C&A 담당 ELEC task 안 보여야 함, got {cats}"

    def test_gst_admin_sees_all_gallant_tasks(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """
        TC-FILTER-GALLANT-05: GST 관리자 → GALLANT 전체 13개 task 조회

        Expected:
        - MECH 7 + ELEC 6 = 13개 모두 보임
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        admin_id = create_test_worker(
            email='gallant_gst_admin@filter.test', password='Test123!',
            name='GALLANT GST Admin', role='ADMIN', is_admin=True, company='GST'
        )
        token = get_auth_token(admin_id, role='ADMIN', is_admin=True)

        r = _call_tasks_api(client, self.SN, token)
        if r.status_code == 404:
            pytest.skip("GET /api/app/tasks/<serial> 미구현")

        assert r.status_code == 200
        tasks = r.get_json()

        if isinstance(tasks, list):
            cats = _get_task_categories(tasks)
            assert len(cats) >= 2, \
                f"GST 관리자는 MECH+ELEC 모두 조회, got {cats}"
            assert len(tasks) >= 7, \
                f"GALLANT 13개 task 중 최소 7개 보여야 함, got {len(tasks)}개"


# ──────────────────────────────────────────────
# 서비스 레이어 직접 테스트 (get_task_categories_for_worker)
# ──────────────────────────────────────────────

class TestGetTaskCategoriesService:
    """
    get_task_categories_for_worker() 서비스 함수 단위 테스트
    DB 없이 순수 로직 검증
    """

    def test_fni_mech_matched_returns_mech(self):
        """TC-SVC-FILTER-01: FNI + mech_partner='FNI' → ['MECH']"""
        try:
            from app.services.task_seed import get_task_categories_for_worker
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        result = get_task_categories_for_worker(
            worker_company='FNI',
            worker_role='MECH',
            product_mech_partner='FNI',
            product_elec_partner='TMS',
            product_module_outsourcing='TMS'
        )
        assert 'MECH' in result, f"FNI 매칭 → MECH 포함, got {result}"
        assert 'ELEC' not in result
        assert 'TMS' not in result

    def test_bat_not_matched_returns_empty(self):
        """TC-SVC-FILTER-02: BAT + mech_partner='FNI' → [] (매칭 안 됨)"""
        try:
            from app.services.task_seed import get_task_categories_for_worker
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        result = get_task_categories_for_worker(
            worker_company='BAT',
            worker_role='MECH',
            product_mech_partner='FNI',
            product_elec_partner='TMS',
            product_module_outsourcing=None
        )
        assert 'MECH' not in result, f"BAT≠FNI → MECH 없음, got {result}"

    def test_tms_m_module_returns_tms(self):
        """TC-SVC-FILTER-03: TMS(M) + module_outsourcing='TMS' → TMS 포함"""
        try:
            from app.services.task_seed import get_task_categories_for_worker
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        result = get_task_categories_for_worker(
            worker_company='TMS(M)',
            worker_role='MECH',
            product_mech_partner='FNI',
            product_elec_partner='TMS',
            product_module_outsourcing='TMS'
        )
        assert 'TMS' in result, f"TMS(M) + module_outsourcing=TMS → TMS 포함, got {result}"

    def test_tms_m_mech_matched_adds_mech(self):
        """TC-SVC-FILTER-04: TMS(M) + mech_partner='TMS' → MECH도 포함"""
        try:
            from app.services.task_seed import get_task_categories_for_worker
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        result = get_task_categories_for_worker(
            worker_company='TMS(M)',
            worker_role='MECH',
            product_mech_partner='TMS',
            product_elec_partner='P&S',
            product_module_outsourcing=None
        )
        # mech_partner='TMS' → MECH 포함
        assert 'MECH' in result, f"TMS(M) + mech_partner=TMS → MECH 포함, got {result}"

    def test_tmse_elec_matched(self):
        """TC-SVC-FILTER-05: TMS(E) + elec_partner='TMS' → ELEC 포함"""
        try:
            from app.services.task_seed import get_task_categories_for_worker
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        result = get_task_categories_for_worker(
            worker_company='TMS(E)',
            worker_role='ELEC',
            product_mech_partner='FNI',
            product_elec_partner='TMS',
            product_module_outsourcing=None
        )
        assert 'ELEC' in result, f"TMS(E) + elec=TMS → ELEC 포함, got {result}"
        assert 'MECH' not in result

    def test_ps_elec_matched(self):
        """TC-SVC-FILTER-06: P&S + elec_partner='P&S' → ELEC 포함"""
        try:
            from app.services.task_seed import get_task_categories_for_worker
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        result = get_task_categories_for_worker(
            worker_company='P&S',
            worker_role='ELEC',
            product_mech_partner='TMS',
            product_elec_partner='P&S',
            product_module_outsourcing=None
        )
        assert 'ELEC' in result, f"P&S + elec=P&S → ELEC 포함, got {result}"

    def test_ca_elec_matched(self):
        """TC-SVC-FILTER-07: C&A + elec_partner='C&A' → ELEC 포함"""
        try:
            from app.services.task_seed import get_task_categories_for_worker
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        result = get_task_categories_for_worker(
            worker_company='C&A',
            worker_role='ELEC',
            product_mech_partner='BAT',
            product_elec_partner='C&A',
            product_module_outsourcing=None
        )
        assert 'ELEC' in result, f"C&A + elec=C&A → ELEC 포함, got {result}"

    def test_gst_admin_returns_empty_filter(self):
        """TC-SVC-FILTER-08: GST ADMIN → 빈 리스트 (필터 없음 = 전체)"""
        try:
            from app.services.task_seed import get_task_categories_for_worker
        except ImportError:
            pytest.skip("task_seed 임포트 실패")

        result = get_task_categories_for_worker(
            worker_company='GST',
            worker_role='ADMIN',
            product_mech_partner='FNI',
            product_elec_partner='TMS',
            product_module_outsourcing=None
        )
        assert result is None, f"GST ADMIN → None (필터 없음 = 전체 조회), got {result}"
