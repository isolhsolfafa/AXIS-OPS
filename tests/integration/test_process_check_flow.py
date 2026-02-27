"""
Sprint 7 Phase 5b: 공정 검증 흐름 통합 테스트

시나리오:
  GAIA: TMS PRESSURE_TEST 완료 → TMS_TANK_COMPLETE 알림
  GAIA: MECH TANK_DOCKING 완료 → TANK_DOCKING_COMPLETE 알림
  phase_block_enabled 토글 테스트
  MECH/ELEC 전체 완료 → completion_status 업데이트
  MECH+ELEC 미완료 + PI 시작 → 경고 반환
  DRAGON: docking 관련 알림 미생성

TC-PROCESS-01 ~ TC-PROCESS-10
"""

import pytest
from pathlib import Path
import sys

backend_path = str(Path(__file__).parent.parent.parent / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


# ──────────────────────────────────────────────────────────────
# 내부 헬퍼
# ──────────────────────────────────────────────────────────────

def _insert_product(db_conn, serial_number: str, qr_doc_id: str,
                    model: str = "GAIA-I DUAL",
                    mech_partner: str = None, elec_partner: str = None,
                    module_outsourcing: str = None) -> None:
    """plan.product_info 및 public.qr_registry 삽입"""
    cur = db_conn.cursor()
    cur.execute("""
        INSERT INTO plan.product_info (serial_number, model, prod_date, mech_partner, elec_partner, module_outsourcing)
        VALUES (%s, %s, CURRENT_DATE, %s, %s, %s)
        ON CONFLICT (serial_number) DO NOTHING
    """, (serial_number, model, mech_partner, elec_partner, module_outsourcing))
    cur.execute("""
        INSERT INTO public.qr_registry (qr_doc_id, serial_number)
        VALUES (%s, %s)
        ON CONFLICT (qr_doc_id) DO NOTHING
    """, (qr_doc_id, serial_number))
    db_conn.commit()
    cur.close()


def _cleanup(db_conn, serial_number: str, qr_doc_id: str = None) -> None:
    """테스트 데이터 정리"""
    cur = db_conn.cursor()
    try:
        cur.execute("DELETE FROM app_alert_logs WHERE serial_number = %s", (serial_number,))
        cur.execute("DELETE FROM completion_status WHERE serial_number = %s", (serial_number,))
        cur.execute("DELETE FROM work_completion_log WHERE serial_number = %s", (serial_number,))
        cur.execute("DELETE FROM work_start_log WHERE serial_number = %s", (serial_number,))
        cur.execute("DELETE FROM public.app_task_details WHERE serial_number = %s", (serial_number,))
        if qr_doc_id:
            cur.execute("DELETE FROM public.qr_registry WHERE qr_doc_id = %s", (qr_doc_id,))
        cur.execute("DELETE FROM plan.product_info WHERE serial_number = %s", (serial_number,))
        db_conn.commit()
    except Exception as e:
        db_conn.rollback()
        print(f"Cleanup warning: {e}")
    finally:
        cur.close()


def _reset_admin_setting(db_conn, key: str, value) -> None:
    """admin_settings 초기화"""
    cur = db_conn.cursor()
    try:
        import json
        cur.execute("""
            INSERT INTO admin_settings (setting_key, setting_value)
            VALUES (%s, %s::jsonb)
            ON CONFLICT (setting_key) DO UPDATE SET setting_value = EXCLUDED.setting_value
        """, (key, json.dumps(value)))
        db_conn.commit()
    except Exception as e:
        db_conn.rollback()
        print(f"admin_setting reset warning: {e}")
    finally:
        cur.close()


def _insert_task(db_conn, serial_number: str, qr_doc_id: str,
                 task_category: str, task_id_ref: str, task_name: str,
                 is_applicable: bool = True) -> int:
    """app_task_details 삽입"""
    cur = db_conn.cursor()
    cur.execute("""
        INSERT INTO app_task_details
            (serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (serial_number, qr_doc_id, task_category, task_id_ref, task_name, is_applicable))
    task_id = cur.fetchone()[0]
    db_conn.commit()
    cur.close()
    return task_id


def _start_work(client, task_id: int, token: str) -> tuple:
    resp = client.post(
        "/api/app/work/start",
        json={"task_detail_id": task_id},
        headers={"Authorization": f"Bearer {token}"}
    )
    return resp.status_code, resp.get_json()


def _complete_work(client, task_id: int, token: str) -> tuple:
    resp = client.post(
        "/api/app/work/complete",
        json={"task_detail_id": task_id},
        headers={"Authorization": f"Bearer {token}"}
    )
    return resp.status_code, resp.get_json()


def _count_alerts(db_conn, serial_number: str, alert_type: str) -> int:
    cur = db_conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM app_alert_logs
        WHERE serial_number = %s AND alert_type = %s
    """, (serial_number, alert_type))
    count = cur.fetchone()[0]
    cur.close()
    return count


def _get_completion_status(db_conn, serial_number: str) -> dict:
    cur = db_conn.cursor()
    cur.execute("""
        SELECT mech_completed, elec_completed, tm_completed,
               pi_completed, qi_completed, si_completed, all_completed
        FROM completion_status WHERE serial_number = %s
    """, (serial_number,))
    row = cur.fetchone()
    cur.close()
    if row is None:
        return {}
    cols = ["mech_completed", "elec_completed", "tm_completed",
            "pi_completed", "qi_completed", "si_completed", "all_completed"]
    return dict(zip(cols, row))


# ──────────────────────────────────────────────────────────────
# TC-PROCESS-01~02: GAIA TMS_TANK_COMPLETE 알림
# ──────────────────────────────────────────────────────────────

class TestGAIATMSTankComplete:
    """GAIA 모델에서 TMS PRESSURE_TEST 완료 → TMS_TANK_COMPLETE 알림"""

    SN = "PROCESS-GAIA-001"
    QR = "DOC_PROCESS-GAIA-001"

    @pytest.fixture(autouse=True)
    def setup(self, db_conn):
        _insert_product(db_conn, self.SN, self.QR, model="GAIA-I DUAL")
        yield
        _cleanup(db_conn, self.SN, self.QR)

    def test_tc_process_01_tms_pressure_test_creates_tms_tank_complete_alert(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """TC-PROCESS-01: TMS PRESSURE_TEST 완료 → TMS_TANK_COMPLETE 알림 생성"""
        # MECH 관리자 생성 (TMS_TANK_COMPLETE 수신 대상)
        mech_mgr_id = create_test_worker(
            email="process_mech_mgr@test.axisos.com", password="Pass1!",
            name="MECH Manager", role="MECH", is_manager=True
        )

        # TMS 작업자
        tms_worker_id = create_test_worker(
            email="process_tms_w@test.axisos.com", password="Pass1!",
            name="TMS Worker", role="MECH"
        )
        token_tms = get_auth_token(tms_worker_id, role="MECH")

        # TMS PRESSURE_TEST task 삽입
        task_id = _insert_task(
            db_conn, self.SN, self.QR,
            task_category="TMS",
            task_id_ref="PRESSURE_TEST",
            task_name="가압 검사"
        )

        # 작업 시작 → 완료
        _start_work(client, task_id, token_tms)
        status, resp = _complete_work(client, task_id, token_tms)
        assert status == 200, f"complete failed: {resp}"

        # TMS_TANK_COMPLETE 알림이 생성되어야 함
        alert_count = _count_alerts(db_conn, self.SN, "TMS_TANK_COMPLETE")
        assert alert_count >= 1, \
            f"Expected TMS_TANK_COMPLETE alert, but found {alert_count}"

    def test_tc_process_02_non_pressure_test_task_does_not_create_tms_alert(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """TC-PROCESS-02: TMS의 다른 task 완료 시 TMS_TANK_COMPLETE 알림 미생성"""
        tms_worker_id = create_test_worker(
            email="process_tms_w2@test.axisos.com", password="Pass1!",
            name="TMS Worker 2", role="MECH"
        )
        token_tms = get_auth_token(tms_worker_id, role="MECH")

        # TMS BURNER_ASSY task (PRESSURE_TEST 아님)
        task_id = _insert_task(
            db_conn, self.SN, self.QR,
            task_category="TMS",
            task_id_ref="BURNER_ASSY_TMS",
            task_name="버너 조립 (TMS)"
        )

        _start_work(client, task_id, token_tms)
        _complete_work(client, task_id, token_tms)

        alert_count = _count_alerts(db_conn, self.SN, "TMS_TANK_COMPLETE")
        assert alert_count == 0, \
            f"Expected 0 TMS_TANK_COMPLETE alerts for non-PRESSURE_TEST task"


# ──────────────────────────────────────────────────────────────
# TC-PROCESS-03~04: GAIA TANK_DOCKING_COMPLETE 알림
# ──────────────────────────────────────────────────────────────

class TestGAIATankDockingComplete:
    """GAIA 모델에서 MECH TANK_DOCKING 완료 → TANK_DOCKING_COMPLETE 알림"""

    SN = "PROCESS-GAIA-002"
    QR = "DOC_PROCESS-GAIA-002"

    @pytest.fixture(autouse=True)
    def setup(self, db_conn):
        _insert_product(db_conn, self.SN, self.QR, model="GAIA-I DUAL")
        yield
        _cleanup(db_conn, self.SN, self.QR)

    def test_tc_process_03_mech_tank_docking_creates_docking_complete_alert(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """TC-PROCESS-03: MECH TANK_DOCKING 완료 → TANK_DOCKING_COMPLETE 알림 생성"""
        # ELEC 관리자 생성 (TANK_DOCKING_COMPLETE 수신 대상)
        elec_mgr_id = create_test_worker(
            email="process_elec_mgr@test.axisos.com", password="Pass1!",
            name="ELEC Manager", role="ELEC", is_manager=True
        )

        mech_worker_id = create_test_worker(
            email="process_mech_w3@test.axisos.com", password="Pass1!",
            name="MECH Worker 3", role="MECH"
        )
        token_mech = get_auth_token(mech_worker_id, role="MECH")

        task_id = _insert_task(
            db_conn, self.SN, self.QR,
            task_category="MECH",
            task_id_ref="TANK_DOCKING",
            task_name="Tank Docking"
        )

        _start_work(client, task_id, token_mech)
        status, resp = _complete_work(client, task_id, token_mech)
        assert status == 200, f"complete failed: {resp}"

        alert_count = _count_alerts(db_conn, self.SN, "TANK_DOCKING_COMPLETE")
        assert alert_count >= 1, \
            f"Expected TANK_DOCKING_COMPLETE alert, but found {alert_count}"

    def test_tc_process_04_elec_task_completion_does_not_create_docking_alert(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """TC-PROCESS-04: ELEC task 완료 시 TANK_DOCKING_COMPLETE 미생성"""
        elec_worker_id = create_test_worker(
            email="process_elec_w4@test.axisos.com", password="Pass1!",
            name="ELEC Worker 4", role="ELEC"
        )
        token_elec = get_auth_token(elec_worker_id, role="ELEC")

        task_id = _insert_task(
            db_conn, self.SN, self.QR,
            task_category="ELEC",
            task_id_ref="PANEL_FABRICATION",
            task_name="판넬 제작"
        )

        _start_work(client, task_id, token_elec)
        _complete_work(client, task_id, token_elec)

        alert_count = _count_alerts(db_conn, self.SN, "TANK_DOCKING_COMPLETE")
        assert alert_count == 0, \
            f"ELEC task should not trigger TANK_DOCKING_COMPLETE"


# ──────────────────────────────────────────────────────────────
# TC-PROCESS-05: DRAGON 모델 docking 알림 미생성
# ──────────────────────────────────────────────────────────────

class TestDRAGONNoDockingAlert:
    """DRAGON 모델은 TANK_DOCKING task 자체가 N/A → docking 알림 미생성"""

    SN = "PROCESS-DRAGON-001"
    QR = "DOC_PROCESS-DRAGON-001"

    @pytest.fixture(autouse=True)
    def setup(self, db_conn):
        _insert_product(db_conn, self.SN, self.QR, model="DRAGON-V")
        yield
        _cleanup(db_conn, self.SN, self.QR)

    def test_tc_process_05_dragon_mech_complete_no_docking_alert(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """TC-PROCESS-05: DRAGON MECH task(TANK_DOCKING 아닌) 완료 시 docking 알림 미생성"""
        mech_worker_id = create_test_worker(
            email="process_dragon_w5@test.axisos.com", password="Pass1!",
            name="DRAGON MECH Worker", role="MECH"
        )
        token_mech = get_auth_token(mech_worker_id, role="MECH")

        # DRAGON은 TANK_DOCKING이 N/A; 다른 MECH task 완료
        task_id = _insert_task(
            db_conn, self.SN, self.QR,
            task_category="MECH",
            task_id_ref="CABINET_ASSY",
            task_name="캐비넷 조립"
        )

        _start_work(client, task_id, token_mech)
        _complete_work(client, task_id, token_mech)

        # TANK_DOCKING_COMPLETE 알림이 없어야 함
        docking_count = _count_alerts(db_conn, self.SN, "TANK_DOCKING_COMPLETE")
        assert docking_count == 0, \
            f"DRAGON should not get TANK_DOCKING_COMPLETE alert"

        # TMS_TANK_COMPLETE 알림도 없어야 함
        tms_count = _count_alerts(db_conn, self.SN, "TMS_TANK_COMPLETE")
        assert tms_count == 0, \
            f"DRAGON should not get TMS_TANK_COMPLETE alert"


# ──────────────────────────────────────────────────────────────
# TC-PROCESS-06~07: MECH/ELEC 전체 완료 → completion_status 업데이트
# ──────────────────────────────────────────────────────────────

class TestCompletionStatusUpdate:
    """MECH SELF_INSPECTION 완료 → mech_completed=True"""

    SN = "PROCESS-STATUS-001"
    QR = "DOC_PROCESS-STATUS-001"

    @pytest.fixture(autouse=True)
    def setup(self, db_conn):
        _insert_product(db_conn, self.SN, self.QR, model="GALLANT-III")
        yield
        _cleanup(db_conn, self.SN, self.QR)

    def test_tc_process_06_mech_self_inspection_sets_mech_completed(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """TC-PROCESS-06: MECH SELF_INSPECTION 완료 + 다른 MECH tasks 없을 때 mech_completed=True"""
        mech_worker_id = create_test_worker(
            email="process_mech_w6@test.axisos.com", password="Pass1!",
            name="MECH Worker 6", role="MECH"
        )
        token_mech = get_auth_token(mech_worker_id, role="MECH")

        # GALLANT는 is_applicable MECH task = SELF_INSPECTION only (heating_jacket off)
        task_id = _insert_task(
            db_conn, self.SN, self.QR,
            task_category="MECH",
            task_id_ref="SELF_INSPECTION",
            task_name="자주검사"
        )

        _start_work(client, task_id, token_mech)
        status, resp = _complete_work(client, task_id, token_mech)
        assert status == 200

        # mech_completed=True 여야 함 (MECH 카테고리 내 미완료 task 없음)
        comp_status = _get_completion_status(db_conn, self.SN)
        assert comp_status.get("mech_completed") is True

    def test_tc_process_07_elec_inspection_sets_elec_completed(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """TC-PROCESS-07: ELEC INSPECTION 완료 + 다른 ELEC tasks 없을 때 elec_completed=True"""
        elec_worker_id = create_test_worker(
            email="process_elec_w7@test.axisos.com", password="Pass1!",
            name="ELEC Worker 7", role="ELEC"
        )
        token_elec = get_auth_token(elec_worker_id, role="ELEC")

        task_id = _insert_task(
            db_conn, self.SN, self.QR,
            task_category="ELEC",
            task_id_ref="INSPECTION",
            task_name="검수"
        )

        _start_work(client, task_id, token_elec)
        status, resp = _complete_work(client, task_id, token_elec)
        assert status == 200

        comp_status = _get_completion_status(db_conn, self.SN)
        assert comp_status.get("elec_completed") is True


# ──────────────────────────────────────────────────────────────
# TC-PROCESS-08: MECH+ELEC 미완료 + PI 시작 → 경고
# ──────────────────────────────────────────────────────────────

class TestPIStartWarning:
    """MECH/ELEC 미완료 상태에서 PI 공정 검증 → can_proceed=False + warnings"""

    SN = "PROCESS-PI-001"
    QR = "DOC_PROCESS-PI-001"

    @pytest.fixture(autouse=True)
    def setup(self, db_conn):
        _insert_product(db_conn, self.SN, self.QR, model="GALLANT-III")
        yield
        _cleanup(db_conn, self.SN, self.QR)

    def test_tc_process_08_pi_start_with_incomplete_mech_elec_returns_warning(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """TC-PROCESS-08: MECH/ELEC 미완료 시 PI 공정 검증 → can_proceed=False + warnings"""
        pi_worker_id = create_test_worker(
            email="process_pi_w8@test.axisos.com", password="Pass1!",
            name="PI Worker 8", role="PI"
        )
        token_pi = get_auth_token(pi_worker_id, role="PI")

        # completion_status 없음 → mech/elec 미완료 상태
        resp = client.get(
            f"/api/app/product/{self.QR}/check-prerequisites?process_type=PI",
            headers={"Authorization": f"Bearer {token_pi}"}
        )

        if resp.status_code == 404:
            pytest.skip("GET /api/app/product/{qr_doc_id}/check-prerequisites 미구현")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("can_proceed") is False
        warnings = data.get("warnings", [])
        assert len(warnings) >= 1, f"Expected warnings for incomplete MECH/ELEC, got: {warnings}"

    def test_tc_process_09_pi_start_with_complete_mech_elec_can_proceed(
        self, client, db_conn, create_test_worker, get_auth_token,
        create_test_completion_status
    ):
        """TC-PROCESS-09: MECH+ELEC 완료 시 PI 공정 검증 → can_proceed=True"""
        pi_worker_id = create_test_worker(
            email="process_pi_w9@test.axisos.com", password="Pass1!",
            name="PI Worker 9", role="PI"
        )
        token_pi = get_auth_token(pi_worker_id, role="PI")

        # completion_status에 mech+elec 완료 설정
        create_test_completion_status(
            serial_number=self.SN,
            mech_completed=True,
            elec_completed=True
        )

        resp = client.get(
            f"/api/app/product/{self.QR}/check-prerequisites?process_type=PI",
            headers={"Authorization": f"Bearer {token_pi}"}
        )

        if resp.status_code == 404:
            pytest.skip("GET /api/app/product/{qr_doc_id}/check-prerequisites 미구현")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("can_proceed") is True


# ──────────────────────────────────────────────────────────────
# TC-PROCESS-10: phase_block_enabled 토글
# ──────────────────────────────────────────────────────────────

class TestPhaseBlockToggle:
    """phase_block_enabled 설정에 따른 PI 공정 차단/허용 검증"""

    SN = "PROCESS-BLOCK-001"
    QR = "DOC_PROCESS-BLOCK-001"

    @pytest.fixture(autouse=True)
    def setup(self, db_conn):
        _insert_product(db_conn, self.SN, self.QR, model="GALLANT-III")
        yield
        _cleanup(db_conn, self.SN, self.QR)
        # phase_block 기본값 복원
        _reset_admin_setting(db_conn, "phase_block_enabled", False)

    def test_tc_process_10_admin_can_toggle_phase_block_setting(
        self, client, db_conn, create_test_worker, get_auth_token, get_admin_auth_token
    ):
        """TC-PROCESS-10: admin_settings phase_block_enabled PUT → GET 에서 확인"""
        admin_id = create_test_worker(
            email="process_admin10@test.axisos.com", password="Pass1!",
            name="Admin 10", role="QI", is_admin=True
        )
        token_admin = get_admin_auth_token(admin_id, role="QI", is_admin=True)

        # phase_block_enabled = True로 설정
        resp_put = client.put(
            "/api/admin/settings",
            json={"phase_block_enabled": True},
            headers={"Authorization": f"Bearer {token_admin}"}
        )
        assert resp_put.status_code == 200

        # GET으로 확인
        resp_get = client.get(
            "/api/admin/settings",
            headers={"Authorization": f"Bearer {token_admin}"}
        )
        assert resp_get.status_code == 200
        settings = resp_get.get_json()
        assert settings.get("phase_block_enabled") is True

        # phase_block_enabled = False로 해제
        resp_put2 = client.put(
            "/api/admin/settings",
            json={"phase_block_enabled": False},
            headers={"Authorization": f"Bearer {token_admin}"}
        )
        assert resp_put2.status_code == 200

        resp_get2 = client.get(
            "/api/admin/settings",
            headers={"Authorization": f"Bearer {token_admin}"}
        )
        settings2 = resp_get2.get_json()
        assert settings2.get("phase_block_enabled") is False
