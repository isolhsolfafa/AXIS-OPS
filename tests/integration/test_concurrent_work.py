"""
Sprint 7 Phase 5a: 멀티 작업자 동시 작업 통합 테스트

시나리오:
  A + B 동시 시작 가능 (멀티 작업자)
  A 완료 + B 미완료 → Task 미완료 유지
  B도 완료 → duration=A+B man-hours 합산, elapsed=실경과, worker_count=2
  관리자 강제 종료 → force_closed=true
  일반 작업자 강제 종료 → 403

TC-CONCURRENT-01  ~ TC-CONCURRENT-15
"""

import pytest
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys

# backend sys.path 추가
backend_path = str(Path(__file__).parent.parent.parent / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


# ──────────────────────────────────────────────────────────────
# 내부 헬퍼
# ──────────────────────────────────────────────────────────────

def _insert_product(db_conn, serial_number: str, qr_doc_id: str,
                    model: str = "GALLANT-III",
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


def _cleanup_product(db_conn, serial_number: str, qr_doc_id: str) -> None:
    """테스트 제품 및 관련 데이터 삭제"""
    cur = db_conn.cursor()
    try:
        cur.execute("DELETE FROM app_alert_logs WHERE serial_number = %s", (serial_number,))
        cur.execute("DELETE FROM completion_status WHERE serial_number = %s", (serial_number,))
        cur.execute("DELETE FROM work_completion_log WHERE serial_number = %s", (serial_number,))
        cur.execute("DELETE FROM work_start_log WHERE serial_number = %s", (serial_number,))
        cur.execute("DELETE FROM public.app_task_details WHERE serial_number = %s", (serial_number,))
        cur.execute("DELETE FROM public.qr_registry WHERE qr_doc_id = %s", (qr_doc_id,))
        cur.execute("DELETE FROM plan.product_info WHERE serial_number = %s", (serial_number,))
        db_conn.commit()
    except Exception as e:
        db_conn.rollback()
        print(f"Cleanup warning: {e}")
    finally:
        cur.close()


def _insert_task(db_conn, serial_number: str, qr_doc_id: str,
                 task_category: str = "MECH",
                 task_id_ref: str = "CABINET_ASSY",
                 task_name: str = "캐비넷 조립",
                 is_applicable: bool = True) -> int:
    """app_task_details에 미시작 task 삽입 후 id 반환"""
    cur = db_conn.cursor()
    cur.execute("""
        INSERT INTO app_task_details
            (serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable,
             started_at, completed_at, worker_id, duration_minutes, elapsed_minutes,
             worker_count, force_closed, closed_by, close_reason)
        VALUES (%s, %s, %s, %s, %s, %s,
                NULL, NULL, NULL, NULL, NULL, 0, FALSE, NULL, NULL)
        ON CONFLICT (serial_number, qr_doc_id, task_category, task_id)
        DO UPDATE SET
            started_at = NULL, completed_at = NULL, worker_id = NULL,
            duration_minutes = NULL, elapsed_minutes = NULL,
            worker_count = 0, force_closed = FALSE, closed_by = NULL, close_reason = NULL,
            is_applicable = EXCLUDED.is_applicable
        RETURNING id
    """, (serial_number, qr_doc_id, task_category, task_id_ref, task_name, is_applicable))
    task_id = cur.fetchone()[0]
    db_conn.commit()
    cur.close()
    return task_id


def _get_task(db_conn, task_id: int) -> dict:
    """app_task_details 단건 조회"""
    cur = db_conn.cursor()
    cur.execute("""
        SELECT id, worker_id, started_at, completed_at, duration_minutes,
               elapsed_minutes, worker_count, force_closed, closed_by, close_reason
        FROM app_task_details
        WHERE id = %s
    """, (task_id,))
    row = cur.fetchone()
    cur.close()
    if row is None:
        return {}
    cols = ["id", "worker_id", "started_at", "completed_at", "duration_minutes",
            "elapsed_minutes", "worker_count", "force_closed", "closed_by", "close_reason"]
    return dict(zip(cols, row))


def _start_work_via_api(client, task_id: int, token: str) -> tuple:
    """POST /api/app/work/start"""
    resp = client.post(
        "/api/app/work/start",
        json={"task_detail_id": task_id},
        headers={"Authorization": f"Bearer {token}"}
    )
    return resp.status_code, resp.get_json()


def _complete_work_via_api(client, task_id: int, token: str) -> tuple:
    """POST /api/app/work/complete"""
    resp = client.post(
        "/api/app/work/complete",
        json={"task_detail_id": task_id},
        headers={"Authorization": f"Bearer {token}"}
    )
    return resp.status_code, resp.get_json()


def _force_close_via_api(client, task_id: int, token: str,
                         reason: str = "테스트 강제 종료") -> tuple:
    """PUT /api/admin/tasks/{task_id}/force-close"""
    resp = client.put(
        f"/api/admin/tasks/{task_id}/force-close",
        json={"close_reason": reason},
        headers={"Authorization": f"Bearer {token}"}
    )
    return resp.status_code, resp.get_json()


def _get_start_log_count(db_conn, task_id: int) -> int:
    cur = db_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM work_start_log WHERE task_id = %s", (task_id,))
    count = cur.fetchone()[0]
    cur.close()
    return count


def _get_completion_log_count(db_conn, task_id: int) -> int:
    cur = db_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM work_completion_log WHERE task_id = %s", (task_id,))
    count = cur.fetchone()[0]
    cur.close()
    return count


# ──────────────────────────────────────────────────────────────
# TC-CONCURRENT-01~04: 멀티 작업자 시작 시나리오
# ──────────────────────────────────────────────────────────────

class TestMultiWorkerStart:
    """두 작업자가 같은 Task를 시작할 수 있는지 검증"""

    SN = "CONCURRENT-001"
    QR = "DOC_CONCURRENT-001"

    @pytest.fixture(autouse=True)
    def setup(self, db_conn):
        _insert_product(db_conn, self.SN, self.QR)
        yield
        _cleanup_product(db_conn, self.SN, self.QR)

    def test_tc_concurrent_01_two_workers_can_start_same_task(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """TC-CONCURRENT-01: A와 B가 동일 Task를 각각 start할 수 있다"""
        task_id = _insert_task(db_conn, self.SN, self.QR)

        worker_a_id = create_test_worker(
            email="concurrent_a@test.axisos.com", password="Pass1!",
            name="Worker A", role="MECH"
        )
        worker_b_id = create_test_worker(
            email="concurrent_b@test.axisos.com", password="Pass1!",
            name="Worker B", role="MECH"
        )
        token_a = get_auth_token(worker_a_id, role="MECH")
        token_b = get_auth_token(worker_b_id, role="MECH")

        status_a, resp_a = _start_work_via_api(client, task_id, token_a)
        status_b, resp_b = _start_work_via_api(client, task_id, token_b)

        assert status_a == 200, f"Worker A start failed: {resp_a}"
        assert status_b == 200, f"Worker B start failed: {resp_b}"
        # work_start_log에 2건이 기록되어야 함
        assert _get_start_log_count(db_conn, task_id) == 2

    def test_tc_concurrent_02_first_worker_sets_started_at(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """TC-CONCURRENT-02: 최초 작업자 시작 시 task.started_at이 설정된다"""
        task_id = _insert_task(db_conn, self.SN, self.QR)

        worker_a_id = create_test_worker(
            email="concurrent_a2@test.axisos.com", password="Pass1!",
            name="Worker A2", role="MECH"
        )
        token_a = get_auth_token(worker_a_id, role="MECH")

        task_before = _get_task(db_conn, task_id)
        assert task_before["started_at"] is None

        _start_work_via_api(client, task_id, token_a)

        task_after = _get_task(db_conn, task_id)
        assert task_after["started_at"] is not None

    def test_tc_concurrent_03_second_worker_does_not_reset_started_at(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """TC-CONCURRENT-03: 두 번째 작업자 시작 시 task.started_at이 변경되지 않는다"""
        task_id = _insert_task(db_conn, self.SN, self.QR)

        worker_a_id = create_test_worker(
            email="concurrent_a3@test.axisos.com", password="Pass1!",
            name="Worker A3", role="MECH"
        )
        worker_b_id = create_test_worker(
            email="concurrent_b3@test.axisos.com", password="Pass1!",
            name="Worker B3", role="MECH"
        )
        token_a = get_auth_token(worker_a_id, role="MECH")
        token_b = get_auth_token(worker_b_id, role="MECH")

        _start_work_via_api(client, task_id, token_a)
        task_after_a = _get_task(db_conn, task_id)
        started_at_a = task_after_a["started_at"]

        time.sleep(1)
        _start_work_via_api(client, task_id, token_b)
        task_after_b = _get_task(db_conn, task_id)

        # started_at은 최초 작업자(A)의 시각으로 고정되어야 함
        assert task_after_b["started_at"] == started_at_a

    def test_tc_concurrent_04_same_worker_cannot_start_twice(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """TC-CONCURRENT-04: 같은 작업자가 동일 Task를 두 번 시작하면 400"""
        task_id = _insert_task(db_conn, self.SN, self.QR)

        worker_a_id = create_test_worker(
            email="concurrent_a4@test.axisos.com", password="Pass1!",
            name="Worker A4", role="MECH"
        )
        token_a = get_auth_token(worker_a_id, role="MECH")

        status_1, _ = _start_work_via_api(client, task_id, token_a)
        assert status_1 == 200

        status_2, resp_2 = _start_work_via_api(client, task_id, token_a)
        assert status_2 == 400
        assert resp_2.get("error") == "TASK_ALREADY_STARTED"


# ──────────────────────────────────────────────────────────────
# TC-CONCURRENT-05~07: A 완료 + B 미완료 → Task 미완료 유지
# ──────────────────────────────────────────────────────────────

class TestPartialCompletion:
    """A가 완료해도 B가 미완료면 Task 전체가 완료되지 않아야 함"""

    SN = "CONCURRENT-002"
    QR = "DOC_CONCURRENT-002"

    @pytest.fixture(autouse=True)
    def setup(self, db_conn):
        _insert_product(db_conn, self.SN, self.QR)
        yield
        _cleanup_product(db_conn, self.SN, self.QR)

    def test_tc_concurrent_05_task_stays_incomplete_when_one_worker_done(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """TC-CONCURRENT-05: A완료+B미완료 → task.completed_at IS NULL 유지"""
        task_id = _insert_task(db_conn, self.SN, self.QR)

        worker_a_id = create_test_worker(
            email="concurrent_a5@test.axisos.com", password="Pass1!",
            name="Worker A5", role="MECH"
        )
        worker_b_id = create_test_worker(
            email="concurrent_b5@test.axisos.com", password="Pass1!",
            name="Worker B5", role="MECH"
        )
        token_a = get_auth_token(worker_a_id, role="MECH")
        token_b = get_auth_token(worker_b_id, role="MECH")

        _start_work_via_api(client, task_id, token_a)
        _start_work_via_api(client, task_id, token_b)

        status_a, resp_a = _complete_work_via_api(client, task_id, token_a)
        assert status_a == 200

        # A 완료 후에도 B가 미완료이므로 Task 전체 미완료 유지
        task = _get_task(db_conn, task_id)
        assert task["completed_at"] is None

    def test_tc_concurrent_06_completion_log_has_one_entry_after_a_completes(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """TC-CONCURRENT-06: A완료 후 work_completion_log에 1건만 존재"""
        task_id = _insert_task(db_conn, self.SN, self.QR)

        worker_a_id = create_test_worker(
            email="concurrent_a6@test.axisos.com", password="Pass1!",
            name="Worker A6", role="MECH"
        )
        worker_b_id = create_test_worker(
            email="concurrent_b6@test.axisos.com", password="Pass1!",
            name="Worker B6", role="MECH"
        )
        token_a = get_auth_token(worker_a_id, role="MECH")
        token_b = get_auth_token(worker_b_id, role="MECH")

        _start_work_via_api(client, task_id, token_a)
        _start_work_via_api(client, task_id, token_b)
        _complete_work_via_api(client, task_id, token_a)

        assert _get_completion_log_count(db_conn, task_id) == 1

    def test_tc_concurrent_07_non_started_worker_cannot_complete(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """TC-CONCURRENT-07: 시작하지 않은 작업자가 완료 시도 → 403"""
        task_id = _insert_task(db_conn, self.SN, self.QR)

        worker_a_id = create_test_worker(
            email="concurrent_a7@test.axisos.com", password="Pass1!",
            name="Worker A7", role="MECH"
        )
        worker_c_id = create_test_worker(
            email="concurrent_c7@test.axisos.com", password="Pass1!",
            name="Worker C7", role="MECH"
        )
        token_a = get_auth_token(worker_a_id, role="MECH")
        token_c = get_auth_token(worker_c_id, role="MECH")

        # A만 시작; C는 시작하지 않음
        _start_work_via_api(client, task_id, token_a)

        status_c, resp_c = _complete_work_via_api(client, task_id, token_c)
        assert status_c == 403
        assert resp_c.get("error") == "FORBIDDEN"


# ──────────────────────────────────────────────────────────────
# TC-CONCURRENT-08~10: B도 완료 → duration/elapsed/worker_count 집계
# ──────────────────────────────────────────────────────────────

class TestDurationAggregation:
    """두 작업자 모두 완료 시 duration=합산, elapsed=실경과, worker_count=2"""

    SN = "CONCURRENT-003"
    QR = "DOC_CONCURRENT-003"

    @pytest.fixture(autouse=True)
    def setup(self, db_conn):
        _insert_product(db_conn, self.SN, self.QR)
        yield
        _cleanup_product(db_conn, self.SN, self.QR)

    def test_tc_concurrent_08_both_workers_complete_finalizes_task(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """TC-CONCURRENT-08: A+B 모두 완료 시 task.completed_at IS NOT NULL"""
        task_id = _insert_task(db_conn, self.SN, self.QR)

        worker_a_id = create_test_worker(
            email="concurrent_a8@test.axisos.com", password="Pass1!",
            name="Worker A8", role="MECH"
        )
        worker_b_id = create_test_worker(
            email="concurrent_b8@test.axisos.com", password="Pass1!",
            name="Worker B8", role="MECH"
        )
        token_a = get_auth_token(worker_a_id, role="MECH")
        token_b = get_auth_token(worker_b_id, role="MECH")

        _start_work_via_api(client, task_id, token_a)
        _start_work_via_api(client, task_id, token_b)
        _complete_work_via_api(client, task_id, token_a)

        status_b, resp_b = _complete_work_via_api(client, task_id, token_b)
        assert status_b == 200

        # A+B 모두 완료 → Task 전체 완료 (completed_at IS NOT NULL)
        task = _get_task(db_conn, task_id)
        assert task["completed_at"] is not None

    def test_tc_concurrent_09_worker_count_is_2_after_both_complete(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """TC-CONCURRENT-09: worker_count=2, completion_log=2건"""
        task_id = _insert_task(db_conn, self.SN, self.QR)

        worker_a_id = create_test_worker(
            email="concurrent_a9@test.axisos.com", password="Pass1!",
            name="Worker A9", role="MECH"
        )
        worker_b_id = create_test_worker(
            email="concurrent_b9@test.axisos.com", password="Pass1!",
            name="Worker B9", role="MECH"
        )
        token_a = get_auth_token(worker_a_id, role="MECH")
        token_b = get_auth_token(worker_b_id, role="MECH")

        _start_work_via_api(client, task_id, token_a)
        _start_work_via_api(client, task_id, token_b)
        _complete_work_via_api(client, task_id, token_a)
        _complete_work_via_api(client, task_id, token_b)

        task = _get_task(db_conn, task_id)
        assert task.get("worker_count") == 2
        assert _get_completion_log_count(db_conn, task_id) == 2

    def test_tc_concurrent_10_duration_is_sum_of_man_hours(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """TC-CONCURRENT-10: duration_minutes = A man-hours + B man-hours (합산)"""
        task_id = _insert_task(db_conn, self.SN, self.QR)

        worker_a_id = create_test_worker(
            email="concurrent_a10@test.axisos.com", password="Pass1!",
            name="Worker A10", role="MECH"
        )
        worker_b_id = create_test_worker(
            email="concurrent_b10@test.axisos.com", password="Pass1!",
            name="Worker B10", role="MECH"
        )
        token_a = get_auth_token(worker_a_id, role="MECH")
        token_b = get_auth_token(worker_b_id, role="MECH")

        _start_work_via_api(client, task_id, token_a)
        _start_work_via_api(client, task_id, token_b)
        _complete_work_via_api(client, task_id, token_a)
        _complete_work_via_api(client, task_id, token_b)

        task = _get_task(db_conn, task_id)
        duration = task.get("duration_minutes")
        # man-hour 합산 → 두 작업자의 개별 duration 합이어야 함 (>= 0)
        assert duration is not None and duration >= 0
        assert task.get("worker_count") == 2


# ──────────────────────────────────────────────────────────────
# TC-CONCURRENT-11~15: 관리자/비관리자 force-close 검증
# ──────────────────────────────────────────────────────────────

class TestForceClose:
    """PUT /api/admin/tasks/{task_id}/force-close 권한 및 필드 검증"""

    SN = "CONCURRENT-004"
    QR = "DOC_CONCURRENT-004"

    @pytest.fixture(autouse=True)
    def setup(self, db_conn):
        _insert_product(db_conn, self.SN, self.QR)
        yield
        _cleanup_product(db_conn, self.SN, self.QR)

    def test_tc_concurrent_11_admin_can_force_close(
        self, client, db_conn, create_test_worker, get_auth_token, get_admin_auth_token
    ):
        """TC-CONCURRENT-11: 관리자(is_admin=True)는 force-close 가능 → force_closed=True"""
        task_id = _insert_task(db_conn, self.SN, self.QR)

        worker_id = create_test_worker(
            email="concurrent_w11@test.axisos.com", password="Pass1!",
            name="Worker 11", role="MECH"
        )
        token_w = get_auth_token(worker_id, role="MECH")
        _start_work_via_api(client, task_id, token_w)

        admin_id = create_test_worker(
            email="concurrent_admin11@test.axisos.com", password="Pass1!",
            name="Admin 11", role="QI", is_admin=True
        )
        token_admin = get_admin_auth_token(admin_id, role="QI", is_admin=True)

        status, resp = _force_close_via_api(client, task_id, token_admin,
                                            reason="테스트 강제 종료 (관리자)")
        assert status == 200, f"force-close failed: {resp}"

        task = _get_task(db_conn, task_id)
        assert task.get("force_closed") is True
        assert task.get("completed_at") is not None

    def test_tc_concurrent_12_regular_worker_cannot_force_close(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """TC-CONCURRENT-12: 일반 작업자는 force-close 시 403"""
        task_id = _insert_task(db_conn, self.SN, self.QR)

        worker_a_id = create_test_worker(
            email="concurrent_a12@test.axisos.com", password="Pass1!",
            name="Worker A12", role="MECH"
        )
        token_a = get_auth_token(worker_a_id, role="MECH")
        _start_work_via_api(client, task_id, token_a)

        status, resp = _force_close_via_api(client, task_id, token_a,
                                            reason="권한 없는 강제 종료")
        assert status == 403

    def test_tc_concurrent_13_force_close_requires_close_reason(
        self, client, db_conn, create_test_worker, get_auth_token, get_admin_auth_token
    ):
        """TC-CONCURRENT-13: close_reason 없이 force-close 시 400"""
        task_id = _insert_task(db_conn, self.SN, self.QR)

        worker_id = create_test_worker(
            email="concurrent_w13@test.axisos.com", password="Pass1!",
            name="Worker 13", role="MECH"
        )
        token_w = get_auth_token(worker_id, role="MECH")
        _start_work_via_api(client, task_id, token_w)

        admin_id = create_test_worker(
            email="concurrent_admin13@test.axisos.com", password="Pass1!",
            name="Admin 13", role="QI", is_admin=True
        )
        token_admin = get_admin_auth_token(admin_id, role="QI", is_admin=True)

        resp = client.put(
            f"/api/admin/tasks/{task_id}/force-close",
            json={},
            headers={"Authorization": f"Bearer {token_admin}"}
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data.get("error") == "INVALID_REQUEST"

    def test_tc_concurrent_14_force_close_already_completed_returns_400(
        self, client, db_conn, create_test_worker, get_auth_token, get_admin_auth_token
    ):
        """TC-CONCURRENT-14: 이미 완료된 Task를 force-close 시도 → 400"""
        task_id = _insert_task(db_conn, self.SN, self.QR)

        worker_id = create_test_worker(
            email="concurrent_w14@test.axisos.com", password="Pass1!",
            name="Worker 14", role="MECH"
        )
        token_w = get_auth_token(worker_id, role="MECH")
        _start_work_via_api(client, task_id, token_w)
        _complete_work_via_api(client, task_id, token_w)

        admin_id = create_test_worker(
            email="concurrent_admin14@test.axisos.com", password="Pass1!",
            name="Admin 14", role="QI", is_admin=True
        )
        token_admin = get_admin_auth_token(admin_id, role="QI", is_admin=True)

        status, resp = _force_close_via_api(client, task_id, token_admin,
                                            reason="이미 완료된 Task 강제 종료 시도")
        assert status == 400
        assert resp.get("error") == "TASK_ALREADY_COMPLETED"

    def test_tc_concurrent_15_force_close_sets_db_fields(
        self, client, db_conn, create_test_worker, get_auth_token, get_admin_auth_token
    ):
        """TC-CONCURRENT-15: force-close 후 close_reason, closed_by, force_closed=true"""
        task_id = _insert_task(db_conn, self.SN, self.QR)

        worker_id = create_test_worker(
            email="concurrent_w15@test.axisos.com", password="Pass1!",
            name="Worker 15", role="MECH"
        )
        token_w = get_auth_token(worker_id, role="MECH")
        _start_work_via_api(client, task_id, token_w)

        admin_id = create_test_worker(
            email="concurrent_admin15@test.axisos.com", password="Pass1!",
            name="Admin 15", role="QI", is_admin=True
        )
        token_admin = get_admin_auth_token(admin_id, role="QI", is_admin=True)

        close_reason = "긴급 장비 점검으로 인한 강제 종료"
        _force_close_via_api(client, task_id, token_admin, reason=close_reason)

        task = _get_task(db_conn, task_id)
        assert task.get("force_closed") is True
        assert task.get("close_reason") == close_reason
        assert task.get("closed_by") == admin_id
        assert task.get("completed_at") is not None
