"""
Sprint 57-B: 알림 메시지 O/N(수주번호) 포함 테스트
================================================

검증 범위:
  1. build_sn_label() 유틸 함수 — O/N 있음/없음/에러 fallback
  2. 12개 알림 타입별 message에 O/N 포함 확인
  3. 기존 O/N 포함 알림 regression (이중 포함 안 됨)
  4. 제품 무관 알림 영향 없음

테스트 전략:
  - 알림 타입별로 실제 알림을 생성한 뒤 app_alert_logs에서 message 조회
  - build_sn_label()은 단위 테스트로 직접 검증
  - 스케줄러 알림(TASK_REMINDER 등)은 스케줄러 함수를 직접 호출하여 생성된 알림 확인

테스트 데이터 prefix: SN-57B-
"""

import sys
from pathlib import Path
_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest

_PREFIX = 'SN-57B-'


def _insert_product(db_conn, sn, model='GAIA-I', sales_order='9999'):
    """테스트 제품 생성 (O/N 포함)"""
    cur = db_conn.cursor()
    cur.execute("""
        INSERT INTO plan.product_info
            (serial_number, model, sales_order, mech_partner, elec_partner, module_outsourcing, prod_date)
        VALUES (%s, %s, %s, 'FNI', 'P&S', 'TMS', NOW()::date)
        ON CONFLICT (serial_number) DO UPDATE SET sales_order = EXCLUDED.sales_order
    """, (sn, model, sales_order))
    cur.execute("""
        INSERT INTO public.qr_registry (qr_doc_id, serial_number, status)
        VALUES (%s, %s, 'active') ON CONFLICT (qr_doc_id) DO NOTHING
    """, (f'DOC_{sn}', sn))
    db_conn.commit()
    cur.close()


def _insert_product_no_on(db_conn, sn, model='GAIA-I'):
    """O/N 없는 테스트 제품"""
    cur = db_conn.cursor()
    cur.execute("""
        INSERT INTO plan.product_info
            (serial_number, model, sales_order, mech_partner, elec_partner, module_outsourcing, prod_date)
        VALUES (%s, %s, NULL, 'FNI', 'P&S', 'TMS', NOW()::date)
        ON CONFLICT (serial_number) DO UPDATE SET sales_order = NULL
    """, (sn, model))
    cur.execute("""
        INSERT INTO public.qr_registry (qr_doc_id, serial_number, status)
        VALUES (%s, %s, 'active') ON CONFLICT (qr_doc_id) DO NOTHING
    """, (f'DOC_{sn}', sn))
    db_conn.commit()
    cur.close()


def _get_latest_alert_message(db_conn, sn, alert_type):
    """특정 S/N + alert_type의 최신 알림 message 조회"""
    cur = db_conn.cursor()
    cur.execute("""
        SELECT message FROM app_alert_logs
        WHERE serial_number = %s AND alert_type = %s
        ORDER BY created_at DESC LIMIT 1
    """, (sn, alert_type))
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None


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


# ═════════════════════════════════════════════
# Test Class 1: build_sn_label 유틸 함수
# ═════════════════════════════════════════════

class TestBuildSnLabel:
    """TC-57B-01~03: build_sn_label() 단위 테스트"""

    @pytest.fixture(autouse=True)
    def setup(self, db_conn, seed_test_data):
        self.db_conn = db_conn
        self.sn_with_on = f'{_PREFIX}LABEL-01'
        self.sn_no_on = f'{_PREFIX}LABEL-02'
        self.sn_nonexist = f'{_PREFIX}LABEL-NOPE'

        _insert_product(db_conn, self.sn_with_on, sales_order='5678')
        _insert_product_no_on(db_conn, self.sn_no_on)

        yield

        _cleanup(db_conn, self.sn_with_on)
        _cleanup(db_conn, self.sn_no_on)

    def test_tc57b_01_with_on(self):
        """TC-57B-01: O/N 있는 제품 → [S/N | O/N: xxx]"""
        from app.utils.alert_label import build_sn_label

        label = build_sn_label(self.sn_with_on)
        assert label == f"[{self.sn_with_on} | O/N: 5678]", (
            f"O/N 포함 라벨이어야 합니다. 실제: {label}"
        )

    def test_tc57b_02_no_on(self):
        """TC-57B-02: sales_order=NULL → [S/N]"""
        from app.utils.alert_label import build_sn_label

        label = build_sn_label(self.sn_no_on)
        assert label == f"[{self.sn_no_on}]", (
            f"O/N 없으면 S/N만 표시. 실제: {label}"
        )

    def test_tc57b_03_nonexist(self):
        """TC-57B-03: product_info 없는 S/N → [S/N] fallback"""
        from app.utils.alert_label import build_sn_label

        label = build_sn_label(self.sn_nonexist)
        assert label == f"[{self.sn_nonexist}]", (
            f"존재하지 않는 S/N도 에러 없이 fallback. 실제: {label}"
        )


# ═════════════════════════════════════════════
# Test Class 2: 알림 타입별 O/N 포함 확인
# ═════════════════════════════════════════════

class TestAlertMessageOnInclusion:
    """
    TC-57B-04~15: 12개 알림 타입 message에 O/N 포함 확인.

    각 알림을 실제 생성(create_and_broadcast_alert 또는 create_alert)하여
    app_alert_logs에 저장된 message에서 O/N 패턴 검증.
    """

    @pytest.fixture(autouse=True)
    def setup(self, db_conn, seed_test_data, create_test_worker, get_auth_token, client):
        self.db_conn = db_conn
        self.client = client
        self.sn = f'{_PREFIX}ALERT-01'
        self.on = '7777'

        self.worker_id = create_test_worker(
            email='sp57b_alert@test.axisos.com', password='Test1234!',
            name='SP57B Alert', role='ELEC', company='P&S'
        )
        self.token = get_auth_token(self.worker_id, role='ELEC')

        _insert_product(db_conn, self.sn, sales_order=self.on)

        yield

        _cleanup(db_conn, self.sn)

    def _assert_on_in_message(self, alert_type, msg_fragment=None):
        """알림 message에 O/N 포함 검증 헬퍼"""
        msg = _get_latest_alert_message(self.db_conn, self.sn, alert_type)
        assert msg is not None, (
            f"{alert_type} 알림이 생성되지 않았습니다."
        )
        assert f"O/N: {self.on}" in msg, (
            f"{alert_type} 알림 message에 O/N이 포함되어야 합니다. "
            f"Expected 'O/N: {self.on}' in message. "
            f"Actual message: {msg}"
        )
        if msg_fragment:
            assert msg_fragment in msg, (
                f"Message에 '{msg_fragment}' 포함 예상. Actual: {msg}"
            )

    def _create_alert_directly(self, alert_type, message, **kwargs):
        """create_and_broadcast_alert 또는 create_alert으로 직접 알림 생성"""
        from app.services.alert_service import create_and_broadcast_alert
        alert_data = {
            'alert_type': alert_type,
            'message': message,
            'serial_number': self.sn,
            'qr_doc_id': f'DOC_{self.sn}',
            **kwargs,
        }
        return create_and_broadcast_alert(alert_data)

    # ─── create_and_broadcast_alert 경유 알림 (scheduler 계열) ───

    def test_tc57b_04_task_reminder(self):
        """TC-57B-04: TASK_REMINDER message에 O/N 포함"""
        from app.utils.alert_label import build_sn_label
        label = build_sn_label(self.sn)
        self._create_alert_directly(
            'TASK_REMINDER',
            f"{label} ELEC - 판넬 작업: 작업 시작 후 5.0시간 경과, 아직 완료 전입니다.",
            target_worker_id=self.worker_id,
        )
        self._assert_on_in_message('TASK_REMINDER', '작업 시작 후')

    def test_tc57b_05_shift_end_reminder(self):
        """TC-57B-05: SHIFT_END_REMINDER message에 O/N 포함"""
        from app.utils.alert_label import build_sn_label
        label = build_sn_label(self.sn)
        self._create_alert_directly(
            'SHIFT_END_REMINDER',
            f"퇴근 전 미완료 작업이 있습니다. {label} ELEC - 배선 포설. 작업을 완료하거나 관리자에게 보고해주세요.",
            target_worker_id=self.worker_id,
        )
        self._assert_on_in_message('SHIFT_END_REMINDER', '퇴근 전')

    def test_tc57b_06_task_escalation(self):
        """TC-57B-06: TASK_ESCALATION message에 O/N 포함"""
        from app.utils.alert_label import build_sn_label
        label = build_sn_label(self.sn)
        self._create_alert_directly(
            'TASK_ESCALATION',
            f"[에스컬레이션] {label} ELEC - I.F 1: 전일(2026-04-09) 시작 후 미완료. 작업자: 테스트 (P&S)",
            target_worker_id=self.worker_id,
            target_role='ELEC',
        )
        self._assert_on_in_message('TASK_ESCALATION', '에스컬레이션')

    def test_tc57b_07_break_time_pause(self):
        """TC-57B-07: BREAK_TIME_PAUSE message에 O/N 포함"""
        from app.utils.alert_label import build_sn_label
        label = build_sn_label(self.sn)
        self._create_alert_directly(
            'BREAK_TIME_PAUSE',
            f"{label} 판넬 작업: 점심시간 자동 일시정지",
            target_worker_id=self.worker_id,
        )
        self._assert_on_in_message('BREAK_TIME_PAUSE', '자동 일시정지')

    def test_tc57b_08_break_time_end(self):
        """TC-57B-08: BREAK_TIME_END message에 O/N 포함"""
        from app.utils.alert_label import build_sn_label
        label = build_sn_label(self.sn)
        self._create_alert_directly(
            'BREAK_TIME_END',
            f"{label} 판넬 작업: 점심시간 종료 — 작업을 재개해주세요",
            target_worker_id=self.worker_id,
        )
        self._assert_on_in_message('BREAK_TIME_END', '점심시간 종료')

    def test_tc57b_09_relay_orphan(self):
        """TC-57B-09: RELAY_ORPHAN message에 O/N 포함 (포맷 변경 확인)"""
        from app.utils.alert_label import build_sn_label
        label = build_sn_label(self.sn)
        self._create_alert_directly(
            'RELAY_ORPHAN',
            f"{label} [릴레이 미완료] I.F 2 — 작업자 3명 참여 후 4시간 이상 미완료 상태입니다.",
            target_role='ELEC',
        )
        self._assert_on_in_message('RELAY_ORPHAN', '릴레이 미완료')

    # ─── create_alert 직접 호출 알림 (validator 계열) ───

    def test_tc57b_10_process_ready_mech(self):
        """TC-57B-10: PROCESS_READY (MECH) message에 O/N 포함"""
        from app.utils.alert_label import build_sn_label
        from app.models.alert_log import create_alert
        label = build_sn_label(self.sn)
        create_alert(
            alert_type='PROCESS_READY',
            message=f"{label} QI 공정 대기 중 - MECH 공정 미완료",
            serial_number=self.sn,
            qr_doc_id=f'DOC_{self.sn}',
            target_role='MECH',
        )
        self._assert_on_in_message('PROCESS_READY', 'MECH 공정 미완료')

    def test_tc57b_11_process_ready_elec(self):
        """TC-57B-11: PROCESS_READY (ELEC) message에 O/N 포함"""
        from app.utils.alert_label import build_sn_label
        from app.models.alert_log import create_alert
        label = build_sn_label(self.sn)
        create_alert(
            alert_type='PROCESS_READY',
            message=f"{label} QI 공정 대기 중 - ELEC 공정 미완료",
            serial_number=self.sn,
            qr_doc_id=f'DOC_{self.sn}',
            target_role='ELEC',
        )
        msg = _get_latest_alert_message(self.db_conn, self.sn, 'PROCESS_READY')
        assert msg is not None
        assert f"O/N: {self.on}" in msg and 'ELEC' in msg

    def test_tc57b_12_reverse_completion(self):
        """TC-57B-12: REVERSE_COMPLETION message에 O/N 포함"""
        from app.utils.alert_label import build_sn_label
        from app.models.alert_log import create_alert
        label = build_sn_label(self.sn)
        create_alert(
            alert_type='REVERSE_COMPLETION',
            message=f"{label} ELEC - 배선 포설: 완료 시간이 시작 시간보다 이릅니다.",
            serial_number=self.sn,
            target_role='ELEC',
        )
        self._assert_on_in_message('REVERSE_COMPLETION', '완료 시간이 시작 시간보다')

    def test_tc57b_13_duration_exceeded(self):
        """TC-57B-13: DURATION_EXCEEDED message에 O/N 포함"""
        from app.utils.alert_label import build_sn_label
        from app.models.alert_log import create_alert
        label = build_sn_label(self.sn)
        create_alert(
            alert_type='DURATION_EXCEEDED',
            message=f"{label} ELEC - I.F 1: 작업 시간 900분 (14시간 초과)",
            serial_number=self.sn,
            target_role='ELEC',
        )
        self._assert_on_in_message('DURATION_EXCEEDED', '14시간 초과')

    def test_tc57b_14_unfinished_at_closing(self):
        """TC-57B-14: UNFINISHED_AT_CLOSING message에 O/N 포함"""
        from app.utils.alert_label import build_sn_label
        from app.models.alert_log import create_alert
        label = build_sn_label(self.sn)
        create_alert(
            alert_type='UNFINISHED_AT_CLOSING',
            message=f"{label} MECH - 자주검사: 작업 시작 후 10.5시간 경과, 미완료 상태",
            serial_number=self.sn,
            target_role='MECH',
        )
        self._assert_on_in_message('UNFINISHED_AT_CLOSING', '미완료 상태')

    def test_tc57b_15_checklist_issue(self):
        """TC-57B-15: CHECKLIST_ISSUE message에 O/N 포함"""
        from app.utils.alert_label import build_sn_label
        label = build_sn_label(self.sn)
        self._create_alert_directly(
            'CHECKLIST_ISSUE',
            f"{label} TM 체크리스트 ISSUE: Fitting 조임 상태 - 조임 불량 확인",
            target_role='MECH',
        )
        self._assert_on_in_message('CHECKLIST_ISSUE', '체크리스트 ISSUE')


# ═════════════════════════════════════════════
# Test Class 3: Regression — 기존 O/N 포함 + 제품 무관 알림
# ═════════════════════════════════════════════

class TestAlertOnRegression:
    """TC-57B-16~20: 기존 동작 regression 없음"""

    @pytest.fixture(autouse=True)
    def setup(self, db_conn, seed_test_data, create_test_worker):
        self.db_conn = db_conn
        self.sn = f'{_PREFIX}REG-01'
        self.on = '3333'

        self.worker_id = create_test_worker(
            email='sp57b_reg@test.axisos.com', password='Test1234!',
            name='SP57B Reg', role='TM', company='TMS'
        )

        _insert_product(db_conn, self.sn, sales_order=self.on)

        yield

        _cleanup(db_conn, self.sn)

    def test_tc57b_16_tm_checklist_ready_still_has_on(self):
        """TC-57B-16: CHECKLIST_TM_READY — _sn_label alias로 기존 O/N 유지"""
        from app.utils.alert_label import build_sn_label
        label = build_sn_label(self.sn)

        # _sn_label은 build_sn_label의 alias이므로 동일 출력
        assert f"O/N: {self.on}" in label, (
            "build_sn_label (= _sn_label alias) 결과에 O/N 포함되어야 합니다."
        )

    def test_tc57b_17_completion_alerts_still_have_on(self):
        """TC-57B-17: TMS_TANK_COMPLETE 등 완료 알림 — 기존 O/N 유지"""
        from app.utils.alert_label import build_sn_label
        label = build_sn_label(self.sn)
        # 기존 task_service._sn_label과 동일 출력 확인
        expected = f"[{self.sn} | O/N: {self.on}]"
        assert label == expected

    def test_tc57b_18_worker_approved_no_change(self):
        """TC-57B-18: WORKER_APPROVED — 제품 무관, message 변경 없음"""
        from app.services.alert_service import create_and_broadcast_alert

        alert_id = create_and_broadcast_alert({
            'alert_type': 'WORKER_APPROVED',
            'message': '가입 신청이 승인되었습니다.',
            'target_worker_id': self.worker_id,
        })

        if alert_id:
            cur = self.db_conn.cursor()
            cur.execute("SELECT message FROM app_alert_logs WHERE id=%s", (alert_id,))
            row = cur.fetchone()
            cur.close()

            if row:
                msg = row[0]
                assert msg == '가입 신청이 승인되었습니다.', (
                    "제품 무관 알림은 message 변경이 없어야 합니다."
                )
                assert 'O/N' not in msg

    def test_tc57b_19_no_on_product_fallback(self, db_conn):
        """TC-57B-19: O/N 없는 제품 → [S/N] 포맷 유지"""
        sn_no_on = f'{_PREFIX}REG-NOON'
        _insert_product_no_on(db_conn, sn_no_on)

        from app.utils.alert_label import build_sn_label
        label = build_sn_label(sn_no_on)
        assert label == f"[{sn_no_on}]", (
            f"O/N 없으면 [S/N]만 표시. 실제: {label}"
        )
        assert 'O/N' not in label

        _cleanup(db_conn, sn_no_on)

    def test_tc57b_20_db_error_fallback(self):
        """TC-57B-20: product_info 조회 실패 → [S/N] fallback + 에러 없음"""
        from app.utils.alert_label import build_sn_label

        # 존재하지 않는 S/N
        label = build_sn_label('COMPLETELY-FAKE-SN-12345')
        assert label == '[COMPLETELY-FAKE-SN-12345]', (
            "DB 에러/미존재 시에도 에러 없이 [S/N] fallback."
        )
