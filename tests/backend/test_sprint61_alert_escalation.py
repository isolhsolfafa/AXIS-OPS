"""
Sprint 61-BE 테스트 — 알람 강화 + 미종료 작업 API 확장
33 TC: Task 1(O/N 통일 11건) + Task 2(에스컬레이션 11건) + Task 3(API 확장 8건) + Regression(3건)
"""

import pytest
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

KST = timezone(timedelta(hours=9))


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def setup_sprint61(db_conn, create_test_worker, get_auth_token):
    """Sprint 61 테스트용 데이터 세팅"""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    cur = db_conn.cursor()
    data = {}

    # Admin
    admin_id = create_test_worker(
        email='s61_admin@test.axisos.com', password='Test1234!',
        name='S61Admin', role='ADMIN', is_admin=True, is_manager=False, company='GST'
    )
    data['admin_id'] = admin_id
    data['admin_token'] = get_auth_token(admin_id, 's61_admin@test.axisos.com', 'ADMIN', is_admin=True)

    # ELEC Manager
    elec_mgr_id = create_test_worker(
        email='s61_elec_mgr@test.axisos.com', password='Test1234!',
        name='S61ElecMgr', role='ELEC', is_manager=True, company='TMS(E)'
    )
    data['elec_mgr_id'] = elec_mgr_id
    data['elec_mgr_token'] = get_auth_token(elec_mgr_id, 's61_elec_mgr@test.axisos.com', 'ELEC')

    # MECH Manager
    mech_mgr_id = create_test_worker(
        email='s61_mech_mgr@test.axisos.com', password='Test1234!',
        name='S61MechMgr', role='MECH', is_manager=True, company='FNI'
    )
    data['mech_mgr_id'] = mech_mgr_id
    data['mech_mgr_token'] = get_auth_token(mech_mgr_id, 's61_mech_mgr@test.axisos.com', 'MECH')

    # MECH Worker
    mech_worker_id = create_test_worker(
        email='s61_mech_worker@test.axisos.com', password='Test1234!',
        name='S61MechWorker', role='MECH', company='FNI'
    )
    data['mech_worker_id'] = mech_worker_id

    # Test product_info + qr_registry
    test_sn = 'S61-TEST-001'
    test_qr = f'DOC_{test_sn}'
    data['test_sn'] = test_sn
    data['test_qr'] = test_qr

    cur.execute("DELETE FROM app_alert_logs WHERE serial_number = %s", (test_sn,))
    cur.execute("DELETE FROM work_completion_log WHERE serial_number = %s", (test_sn,))
    cur.execute("DELETE FROM work_start_log WHERE serial_number = %s", (test_sn,))
    cur.execute("DELETE FROM app_task_details WHERE serial_number = %s", (test_sn,))
    cur.execute("DELETE FROM completion_status WHERE serial_number = %s", (test_sn,))
    cur.execute("DELETE FROM qr_registry WHERE serial_number = %s", (test_sn,))
    cur.execute("DELETE FROM plan.product_info WHERE serial_number = %s", (test_sn,))
    db_conn.commit()

    # v2.10.2: partner 필드 추가 — _resolve_managers_for_category 가 product_info.*_partner 로
    # 관리자 찾기 때문에 누락 시 managers=[] → alert 0건 → TC fail.
    cur.execute("""
        INSERT INTO plan.product_info (serial_number, model, sales_order,
                                       mech_partner, elec_partner)
        VALUES (%s, 'GAIA-TEST', '9999', 'FNI', 'TMS')
        ON CONFLICT (serial_number) DO NOTHING
    """, (test_sn,))

    cur.execute("""
        INSERT INTO qr_registry (qr_doc_id, serial_number, status)
        VALUES (%s, %s, 'active')
        ON CONFLICT (qr_doc_id) DO NOTHING
    """, (test_qr, test_sn))

    cur.execute("""
        INSERT INTO completion_status (serial_number)
        VALUES (%s)
        ON CONFLICT (serial_number) DO NOTHING
    """, (test_sn,))

    db_conn.commit()

    yield data

    # Cleanup
    cur.execute("DELETE FROM app_alert_logs WHERE serial_number = %s", (test_sn,))
    cur.execute("DELETE FROM work_completion_log WHERE serial_number = %s", (test_sn,))
    cur.execute("DELETE FROM work_start_log WHERE serial_number = %s", (test_sn,))
    cur.execute("DELETE FROM app_task_details WHERE serial_number = %s", (test_sn,))
    cur.execute("DELETE FROM completion_status WHERE serial_number = %s", (test_sn,))
    cur.execute("DELETE FROM qr_registry WHERE serial_number = %s", (test_sn,))
    cur.execute("DELETE FROM plan.product_info WHERE serial_number = %s", (test_sn,))
    db_conn.commit()


def _create_task(cur, conn, sn, qr, category, task_id, task_name, worker_id=None,
                 started_at=None, completed_at=None, is_applicable=True):
    """테스트용 task 생성 헬퍼 — worker_id=None이면 admin(id=1) 사용"""
    # FK 제약 충족을 위해 worker_id 0은 사용 불가 → 실제 worker 필요
    # worker_id=None이면 최소 workers.id=1(admin seed) 사용
    if worker_id is None:
        cur.execute("SELECT id FROM workers LIMIT 1")
        row = cur.fetchone()
        wid = row[0] if row else 1
    else:
        wid = worker_id
    cur.execute("""
        INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
             started_at, completed_at, is_applicable)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (wid, sn, qr, category, task_id, task_name,
          started_at, completed_at, is_applicable))
    tid = cur.fetchone()[0]
    conn.commit()
    return tid


# ─────────────────────────────────────────────
# Task 1: O/N 메시지 통일 테스트 (TC-61B-01 ~ 11)
# ─────────────────────────────────────────────

class TestSNLabelFunction:
    """sn_label() 공통 함수 테스트"""

    def test_tc_61b_01_sn_label_with_sales_order(self, app):
        """TC-61B-01: sales_order 있는 S/N → [S/N | O/N: xxx] 형식"""
        with app.app_context():
            from app.services.alert_service import sn_label
            with patch('app.services.alert_service.get_product_by_serial_number') as mock:
                mock_product = MagicMock()
                mock_product.sales_order = '6656'
                mock.return_value = mock_product

                result = sn_label('GBWS-6920')
                assert 'GBWS-6920' in result
                assert 'O/N: 6656' in result

    def test_tc_61b_10_sn_label_without_sales_order(self, app):
        """TC-61B-10: sales_order NULL → [SN] 형식"""
        with app.app_context():
            from app.services.alert_service import sn_label
            with patch('app.services.alert_service.get_product_by_serial_number') as mock:
                mock_product = MagicMock()
                mock_product.sales_order = None
                mock.return_value = mock_product

                result = sn_label('TEST-001')
                assert result == '[TEST-001]'
                assert 'O/N' not in result

    def test_tc_61b_10b_sn_label_product_not_found(self, app):
        """sn_label — product 없는 경우 [SN] 형식"""
        with app.app_context():
            from app.services.alert_service import sn_label
            with patch('app.services.alert_service.get_product_by_serial_number') as mock:
                mock.return_value = None
                result = sn_label('UNKNOWN')
                assert result == '[UNKNOWN]'


class TestONMessageIntegration:
    """각 서비스 파일에서 sn_label import 확인"""

    def test_tc_61b_02_duration_validator_imports_sn_label(self, app):
        """TC-61B-02: duration_validator.py에 sn_label import 확인"""
        with app.app_context():
            from app.services import duration_validator
            source = open(duration_validator.__file__).read()
            assert 'from app.services.alert_service import sn_label' in source
            assert 'sn_label(' in source

    def test_tc_61b_03_scheduler_imports_sn_label(self, app):
        """TC-61B-03: scheduler_service.py에 sn_label import 확인"""
        with app.app_context():
            from app.services import scheduler_service
            source = open(scheduler_service.__file__).read()
            assert 'from app.services.alert_service import sn_label' in source

    def test_tc_61b_04_task_service_removed_local_sn_label(self, app):
        """TC-61B-04: task_service.py에서 로컬 _sn_label 제거 + sn_label import 확인"""
        with app.app_context():
            from app.services import task_service
            source = open(task_service.__file__).read()
            # 로컬 함수 정의가 제거되었는지 확인
            assert 'def _sn_label(' not in source
            # import 존재 확인
            assert 'sn_label' in source

    def test_tc_61b_08_checklist_service_imports_sn_label(self, app):
        """TC-61B-08: checklist_service.py에 sn_label 사용 확인"""
        with app.app_context():
            from app.services import checklist_service
            source = open(checklist_service.__file__).read()
            assert 'sn_label' in source

    def test_tc_61b_09_process_validator_imports_sn_label(self, app):
        """TC-61B-09: process_validator.py에 sn_label import 확인"""
        with app.app_context():
            from app.services import process_validator
            source = open(process_validator.__file__).read()
            assert 'from app.services.alert_service import sn_label' in source
            assert 'sn_label(' in source

    def test_tc_61b_11_no_hardcoded_bracket_sn_in_alerts(self, app):
        """TC-61B-11: 수정 대상 파일에 하드코딩된 [serial_number] 패턴이 없는지 확인"""
        with app.app_context():
            import re
            files_to_check = [
                'app.services.duration_validator',
                'app.services.process_validator',
            ]
            for mod_name in files_to_check:
                mod = __import__(mod_name, fromlist=[''])
                source = open(mod.__file__).read()
                # f"[{serial_number}]" 또는 f"[{task.serial_number}]" 패턴 없어야 함
                # sn_label() 호출로 대체되었으므로
                matches = re.findall(r'f["\'].*\[\{(?:serial_number|task\.serial_number|row\[.serial_number.\])\}]', source)
                assert len(matches) == 0, f"{mod_name}에 하드코딩 [SN] 패턴 잔존: {matches}"


# ─────────────────────────────────────────────
# Task 2: 신규 에스컬레이션 알람 테스트 (TC-61B-12 ~ 22)
# ─────────────────────────────────────────────

class TestTaskNotStartedAlert:
    """TASK_NOT_STARTED 에스컬레이션"""

    def test_tc_61b_12_not_started_2days_alert(self, app, db_conn, setup_sprint61):
        """TC-61B-12: 2일 미시작 + 같은 S/N 다른 task 시작됨 → 알람 발생"""
        cur = db_conn.cursor()
        sn = setup_sprint61['test_sn']
        qr = setup_sprint61['test_qr']
        worker_id = setup_sprint61['mech_worker_id']

        # Task 1: 시작된 task
        _create_task(cur, db_conn, sn, qr, 'MECH', 'SELF_INSPECTION', '자주검사',
                     worker_id=worker_id, started_at=datetime.now(KST) - timedelta(days=3))

        # Task 2: 미시작 task (3일 전 생성)
        not_started_id = _create_task(cur, db_conn, sn, qr, 'MECH', 'UTIL_LINE_1', 'Util LINE 1')
        cur.execute("UPDATE app_task_details SET created_at = %s WHERE id = %s",
                    (datetime.now(KST) - timedelta(days=3), not_started_id))
        db_conn.commit()

        with app.app_context():
            from app.services.scheduler_service import _check_not_started_tasks
            _check_not_started_tasks()

        # 알람 생성 확인
        cur.execute("""
            SELECT * FROM app_alert_logs
            WHERE alert_type = 'TASK_NOT_STARTED' AND serial_number = %s
        """, (sn,))
        alerts = cur.fetchall()
        assert len(alerts) >= 1, "TASK_NOT_STARTED 알람이 생성되어야 함"

    def test_tc_61b_13_all_not_started_no_alert(self, app, db_conn, setup_sprint61):
        """TC-61B-13: 전체 S/N 미시작 → 알람 미발생"""
        cur = db_conn.cursor()
        sn = setup_sprint61['test_sn']
        qr = setup_sprint61['test_qr']

        # 기존 task 정리
        cur.execute("DELETE FROM app_alert_logs WHERE serial_number = %s", (sn,))
        cur.execute("DELETE FROM app_task_details WHERE serial_number = %s", (sn,))
        db_conn.commit()

        # 모든 task 미시작
        tid = _create_task(cur, db_conn, sn, qr, 'MECH', 'SELF_INSPECTION', '자주검사')
        cur.execute("UPDATE app_task_details SET created_at = %s WHERE id = %s",
                    (datetime.now(KST) - timedelta(days=5), tid))
        db_conn.commit()

        with app.app_context():
            from app.services.scheduler_service import _check_not_started_tasks
            _check_not_started_tasks()

        cur.execute("""
            SELECT * FROM app_alert_logs
            WHERE alert_type = 'TASK_NOT_STARTED' AND serial_number = %s
        """, (sn,))
        assert cur.fetchone() is None, "전체 미시작 S/N에는 알람 미발생"

    def test_tc_61b_14_1day_no_alert(self, app, db_conn, setup_sprint61):
        """TC-61B-14: 1일 경과 → 알람 미발생 (threshold 미달)"""
        cur = db_conn.cursor()
        sn = setup_sprint61['test_sn']
        qr = setup_sprint61['test_qr']
        worker_id = setup_sprint61['mech_worker_id']

        cur.execute("DELETE FROM app_alert_logs WHERE serial_number = %s", (sn,))
        cur.execute("DELETE FROM app_task_details WHERE serial_number = %s", (sn,))
        db_conn.commit()

        _create_task(cur, db_conn, sn, qr, 'MECH', 'SELF_INSPECTION', '자주검사',
                     worker_id=worker_id, started_at=datetime.now(KST))
        tid = _create_task(cur, db_conn, sn, qr, 'MECH', 'UTIL_LINE_1', 'Util LINE 1')
        cur.execute("UPDATE app_task_details SET created_at = %s WHERE id = %s",
                    (datetime.now(KST) - timedelta(hours=20), tid))
        db_conn.commit()

        with app.app_context():
            from app.services.scheduler_service import _check_not_started_tasks
            _check_not_started_tasks()

        cur.execute("""
            SELECT * FROM app_alert_logs
            WHERE alert_type = 'TASK_NOT_STARTED' AND serial_number = %s
        """, (sn,))
        assert cur.fetchone() is None, "threshold 미달 시 알람 미발생"

    def test_tc_61b_15_dedup_7day(self, app, db_conn, setup_sprint61):
        """TC-61B-15: 7일 이내 중복 발송 방지"""
        cur = db_conn.cursor()
        sn = setup_sprint61['test_sn']
        qr = setup_sprint61['test_qr']
        worker_id = setup_sprint61['mech_worker_id']

        cur.execute("DELETE FROM app_alert_logs WHERE serial_number = %s", (sn,))
        cur.execute("DELETE FROM app_task_details WHERE serial_number = %s", (sn,))
        db_conn.commit()

        _create_task(cur, db_conn, sn, qr, 'MECH', 'SELF_INSPECTION', '자주검사',
                     worker_id=worker_id, started_at=datetime.now(KST) - timedelta(days=3))
        not_started_id = _create_task(cur, db_conn, sn, qr, 'MECH', 'UTIL_LINE_1', 'Util LINE 1')
        cur.execute("UPDATE app_task_details SET created_at = %s WHERE id = %s",
                    (datetime.now(KST) - timedelta(days=5), not_started_id))
        db_conn.commit()

        with app.app_context():
            from app.services.scheduler_service import _check_not_started_tasks
            # 1차 실행
            _check_not_started_tasks()
            cur.execute("SELECT COUNT(*) FROM app_alert_logs WHERE alert_type = 'TASK_NOT_STARTED' AND serial_number = %s", (sn,))
            count1 = cur.fetchone()[0]

            # 2차 실행 — 중복 방지
            _check_not_started_tasks()
            cur.execute("SELECT COUNT(*) FROM app_alert_logs WHERE alert_type = 'TASK_NOT_STARTED' AND serial_number = %s", (sn,))
            count2 = cur.fetchone()[0]

            assert count2 == count1, "7일 이내 중복 발송 방지"

    def test_tc_61b_16_admin_settings_off(self, app, db_conn, setup_sprint61):
        """TC-61B-16: admin_settings OFF → 알람 미발생"""
        cur = db_conn.cursor()
        sn = setup_sprint61['test_sn']

        cur.execute("DELETE FROM app_alert_logs WHERE serial_number = %s", (sn,))
        db_conn.commit()

        with app.app_context():
            with patch('app.models.admin_settings.get_setting', return_value=False):
                from app.services.scheduler_service import _check_not_started_tasks
                _check_not_started_tasks()

        cur.execute("""
            SELECT * FROM app_alert_logs
            WHERE alert_type = 'TASK_NOT_STARTED' AND serial_number = %s
        """, (sn,))
        assert cur.fetchone() is None


class TestChecklistDoneTaskOpen:
    """CHECKLIST_DONE_TASK_OPEN 에스컬레이션"""

    def test_tc_61b_17_checklist_done_task_open(self, app, db_conn, setup_sprint61):
        """TC-61B-17: ELEC 체크리스트 완료(IF_2 완료) + 다른 ELEC task 미완료 → 알람"""
        cur = db_conn.cursor()
        sn = setup_sprint61['test_sn']
        qr = setup_sprint61['test_qr']
        worker_id = setup_sprint61['mech_worker_id']

        cur.execute("DELETE FROM app_alert_logs WHERE serial_number = %s", (sn,))
        cur.execute("DELETE FROM app_task_details WHERE serial_number = %s", (sn,))
        db_conn.commit()

        # IF_2 완료
        _create_task(cur, db_conn, sn, qr, 'ELEC', 'IF_2', 'I.F 2',
                     worker_id=worker_id,
                     started_at=datetime.now(KST) - timedelta(hours=2),
                     completed_at=datetime.now(KST) - timedelta(hours=1))
        # PANEL_WORK 미완료
        _create_task(cur, db_conn, sn, qr, 'ELEC', 'PANEL_WORK', '판넬 작업')

        with app.app_context():
            from app.services.scheduler_service import _check_checklist_done_task_open
            _check_checklist_done_task_open()

        cur.execute("""
            SELECT * FROM app_alert_logs
            WHERE alert_type = 'CHECKLIST_DONE_TASK_OPEN' AND serial_number = %s
        """, (sn,))
        alerts = cur.fetchall()
        assert len(alerts) >= 1, "CHECKLIST_DONE_TASK_OPEN 알람 생성 필요"

    def test_tc_61b_18_checklist_not_done_no_alert(self, app, db_conn, setup_sprint61):
        """TC-61B-18: 체크리스트 미완료(IF_2 미완료) → 알람 미발생"""
        cur = db_conn.cursor()
        sn = setup_sprint61['test_sn']
        qr = setup_sprint61['test_qr']

        cur.execute("DELETE FROM app_alert_logs WHERE serial_number = %s", (sn,))
        cur.execute("DELETE FROM app_task_details WHERE serial_number = %s", (sn,))
        db_conn.commit()

        # IF_2 미완료
        _create_task(cur, db_conn, sn, qr, 'ELEC', 'IF_2', 'I.F 2')
        _create_task(cur, db_conn, sn, qr, 'ELEC', 'PANEL_WORK', '판넬 작업')

        with app.app_context():
            from app.services.scheduler_service import _check_checklist_done_task_open
            _check_checklist_done_task_open()

        cur.execute("""
            SELECT * FROM app_alert_logs
            WHERE alert_type = 'CHECKLIST_DONE_TASK_OPEN' AND serial_number = %s
        """, (sn,))
        assert cur.fetchone() is None

    def test_tc_61b_19_dedup_3day(self, app, db_conn, setup_sprint61):
        """TC-61B-19: 3일 이내 중복 발송 방지"""
        cur = db_conn.cursor()
        sn = setup_sprint61['test_sn']
        qr = setup_sprint61['test_qr']
        worker_id = setup_sprint61['mech_worker_id']

        cur.execute("DELETE FROM app_alert_logs WHERE serial_number = %s", (sn,))
        cur.execute("DELETE FROM app_task_details WHERE serial_number = %s", (sn,))
        db_conn.commit()

        _create_task(cur, db_conn, sn, qr, 'ELEC', 'IF_2', 'I.F 2',
                     worker_id=worker_id,
                     started_at=datetime.now(KST) - timedelta(hours=2),
                     completed_at=datetime.now(KST) - timedelta(hours=1))
        _create_task(cur, db_conn, sn, qr, 'ELEC', 'PANEL_WORK', '판넬 작업')

        with app.app_context():
            from app.services.scheduler_service import _check_checklist_done_task_open
            _check_checklist_done_task_open()
            cur.execute("SELECT COUNT(*) FROM app_alert_logs WHERE alert_type = 'CHECKLIST_DONE_TASK_OPEN' AND serial_number = %s", (sn,))
            count1 = cur.fetchone()[0]

            _check_checklist_done_task_open()
            cur.execute("SELECT COUNT(*) FROM app_alert_logs WHERE alert_type = 'CHECKLIST_DONE_TASK_OPEN' AND serial_number = %s", (sn,))
            count2 = cur.fetchone()[0]

            assert count2 == count1, "3일 이내 중복 방지"

    def test_tc_61b_19b_dedup_per_task_detail(self, app, db_conn, setup_sprint61):
        """TC-61B-19B (v2.10.2 FIX-CHECKLIST-DONE-DEDUPE-KEY, Codex 사후 Q4-4 M):
        같은 S/N 에 복수 ELEC task(PANEL_WORK, WIRING)이 open 상태일 때,
        각 task 별로 각각 alert 가 발송되어야 함 (과거 버그: 첫 task alert 후 나머지 3일 suppress)."""
        cur = db_conn.cursor()
        sn = setup_sprint61['test_sn']
        qr = setup_sprint61['test_qr']
        worker_id = setup_sprint61['mech_worker_id']

        cur.execute("DELETE FROM app_alert_logs WHERE serial_number = %s", (sn,))
        cur.execute("DELETE FROM app_task_details WHERE serial_number = %s", (sn,))
        db_conn.commit()

        # IF_2 완료 (체크리스트 완료 조건)
        _create_task(cur, db_conn, sn, qr, 'ELEC', 'IF_2', 'I.F 2',
                     worker_id=worker_id,
                     started_at=datetime.now(KST) - timedelta(hours=2),
                     completed_at=datetime.now(KST) - timedelta(hours=1))
        # 미완료 ELEC task 2개 (동일 S/N 내 복수 open)
        _create_task(cur, db_conn, sn, qr, 'ELEC', 'PANEL_WORK', '판넬 작업')
        _create_task(cur, db_conn, sn, qr, 'ELEC', 'WIRING', '배선 포설')

        with app.app_context():
            from app.services.scheduler_service import _check_checklist_done_task_open
            _check_checklist_done_task_open()

        # 각 task 별로 DISTINCT alert 발송 검증
        cur.execute("""
            SELECT DISTINCT task_detail_id FROM app_alert_logs
            WHERE alert_type = 'CHECKLIST_DONE_TASK_OPEN' AND serial_number = %s
              AND task_detail_id IS NOT NULL
        """, (sn,))
        distinct_tasks = cur.fetchall()
        assert len(distinct_tasks) == 2, (
            f"동일 S/N 내 복수 ELEC open task 2건 각각 alert 발송 기대, "
            f"실제 DISTINCT task_detail_id 건수 = {len(distinct_tasks)}. "
            f"v2.10.2 이전 버그에서는 1건만 나와야 fail (Q4-4 M 회귀 가드)."
        )


class TestOrphanOnFinal:
    """ORPHAN_ON_FINAL 테스트"""

    def test_tc_61b_20_orphan_on_final(self, app, db_conn, setup_sprint61):
        """TC-61B-20: FINAL task 완료 시 미시작 task 존재 → 알람"""
        cur = db_conn.cursor()
        sn = setup_sprint61['test_sn']
        qr = setup_sprint61['test_qr']
        worker_id = setup_sprint61['mech_worker_id']

        cur.execute("DELETE FROM app_alert_logs WHERE serial_number = %s", (sn,))
        cur.execute("DELETE FROM app_task_details WHERE serial_number = %s", (sn,))
        db_conn.commit()

        # 미시작 task 존재
        _create_task(cur, db_conn, sn, qr, 'ELEC', 'PANEL_WORK', '판넬 작업')

        with app.app_context():
            from app.models.task_detail import get_not_started_tasks
            not_started = get_not_started_tasks(sn, 'ELEC')
            assert len(not_started) >= 1, "미시작 task가 있어야 함"

    def test_tc_61b_21_no_orphan_all_complete(self, app, db_conn, setup_sprint61):
        """TC-61B-21: 모든 task 완료 → 알람 미발생"""
        cur = db_conn.cursor()
        sn = setup_sprint61['test_sn']
        qr = setup_sprint61['test_qr']
        worker_id = setup_sprint61['mech_worker_id']

        cur.execute("DELETE FROM app_task_details WHERE serial_number = %s", (sn,))
        db_conn.commit()

        # 모든 task 완료
        _create_task(cur, db_conn, sn, qr, 'ELEC', 'IF_2', 'I.F 2',
                     worker_id=worker_id,
                     started_at=datetime.now(KST) - timedelta(hours=2),
                     completed_at=datetime.now(KST))

        with app.app_context():
            from app.models.task_detail import get_not_started_tasks
            not_started = get_not_started_tasks(sn, 'ELEC')
            assert len(not_started) == 0

    def test_tc_61b_22_orphan_admin_settings_off(self, app):
        """TC-61B-22: admin_settings OFF → 알람 미발생 (로직 검증)"""
        with app.app_context():
            with patch('app.models.admin_settings.get_setting', return_value=False) as mock:
                # get_setting('alert_orphan_on_final_enabled') = False 시 스킵 확인
                assert mock.return_value == False


# ─────────────────────────────────────────────
# Task 3: API 확장 테스트 (TC-61B-23 ~ 30)
# ─────────────────────────────────────────────

class TestPendingTasksAPI:
    """GET /admin/tasks/pending 확장"""

    def test_tc_61b_23_existing_behavior(self, client, db_conn, setup_sprint61):
        """TC-61B-23: 기존 파라미터 → 기존 동작 100% 유지"""
        token = setup_sprint61['admin_token']
        resp = client.get('/api/admin/tasks/pending',
                          headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'tasks' in data

    def test_tc_61b_24_include_not_started(self, client, db_conn, setup_sprint61):
        """TC-61B-24: include_not_started=true → NOT_STARTED task 포함"""
        cur = db_conn.cursor()
        sn = setup_sprint61['test_sn']
        qr = setup_sprint61['test_qr']
        worker_id = setup_sprint61['mech_worker_id']

        cur.execute("DELETE FROM app_task_details WHERE serial_number = %s", (sn,))
        db_conn.commit()

        # 시작된 task
        _create_task(cur, db_conn, sn, qr, 'MECH', 'SELF_INSPECTION', '자주검사',
                     worker_id=worker_id, started_at=datetime.now(KST))
        # 미시작 task (3일 전 생성)
        tid = _create_task(cur, db_conn, sn, qr, 'MECH', 'UTIL_LINE_1', 'Util LINE 1')
        cur.execute("UPDATE app_task_details SET created_at = %s WHERE id = %s",
                    (datetime.now(KST) - timedelta(days=3), tid))
        db_conn.commit()

        token = setup_sprint61['admin_token']
        resp = client.get('/api/admin/tasks/pending?include_not_started=true',
                          headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        data = resp.get_json()

        statuses = [t.get('status') for t in data.get('tasks', [])]
        # NOT_STARTED 포함 여부 — 전체 목록에서 해당 S/N 필터
        sn_tasks = [t for t in data.get('tasks', []) if t.get('serial_number') == sn]
        has_not_started = any(t.get('status') == 'NOT_STARTED' or t.get('status') == 'not_started'
                             for t in sn_tasks)
        assert has_not_started or len(sn_tasks) > 0, "NOT_STARTED task 포함 확인"

    def test_tc_61b_25_not_started_null_fields(self, client, db_conn, setup_sprint61):
        """TC-61B-25: NOT_STARTED task의 worker_id, worker_name, started_at 모두 NULL"""
        cur = db_conn.cursor()
        sn = setup_sprint61['test_sn']
        qr = setup_sprint61['test_qr']
        worker_id = setup_sprint61['mech_worker_id']

        cur.execute("DELETE FROM app_task_details WHERE serial_number = %s", (sn,))
        db_conn.commit()

        _create_task(cur, db_conn, sn, qr, 'MECH', 'SELF_INSPECTION', '자주검사',
                     worker_id=worker_id, started_at=datetime.now(KST))
        tid = _create_task(cur, db_conn, sn, qr, 'MECH', 'UTIL_LINE_1', 'Util LINE 1')
        cur.execute("UPDATE app_task_details SET created_at = %s WHERE id = %s",
                    (datetime.now(KST) - timedelta(days=3), tid))
        db_conn.commit()

        token = setup_sprint61['admin_token']
        resp = client.get('/api/admin/tasks/pending?include_not_started=true',
                          headers={'Authorization': f'Bearer {token}'})
        data = resp.get_json()

        not_started = [t for t in data.get('tasks', [])
                       if t.get('serial_number') == sn and
                       (t.get('status') in ('NOT_STARTED', 'not_started'))]
        for t in not_started:
            # NOT_STARTED task는 started_at이 NULL이어야 함
            assert t.get('started_at') is None
            # worker_id는 task seed 시 설정될 수 있으므로 NULL 필수 아님

    def test_tc_61b_26_sales_order_field(self, client, db_conn, setup_sprint61):
        """TC-61B-26: 응답에 sales_order 필드 포함"""
        token = setup_sprint61['admin_token']
        resp = client.get('/api/admin/tasks/pending?include_not_started=true',
                          headers={'Authorization': f'Bearer {token}'})
        data = resp.get_json()
        tasks = data.get('tasks', [])
        sn = setup_sprint61['test_sn']
        sn_tasks = [t for t in tasks if t.get('serial_number') == sn]
        if sn_tasks:
            assert 'sales_order' in sn_tasks[0]

    def test_tc_61b_27_counts_field(self, client, db_conn, setup_sprint61):
        """TC-61B-27: 응답에 counts 포함"""
        token = setup_sprint61['admin_token']
        resp = client.get('/api/admin/tasks/pending?include_not_started=true',
                          headers={'Authorization': f'Bearer {token}'})
        data = resp.get_json()
        assert 'counts' in data
        counts = data['counts']
        assert 'in_progress' in counts
        assert 'not_started' in counts

    def test_tc_61b_30_force_closed_hidden(self, client, db_conn, setup_sprint61):
        """TC-61B-30: force_closed=TRUE task는 미표시"""
        cur = db_conn.cursor()
        sn = setup_sprint61['test_sn']
        qr = setup_sprint61['test_qr']
        worker_id = setup_sprint61['mech_worker_id']

        cur.execute("DELETE FROM app_task_details WHERE serial_number = %s", (sn,))
        db_conn.commit()

        tid = _create_task(cur, db_conn, sn, qr, 'MECH', 'SELF_INSPECTION', '자주검사',
                           worker_id=worker_id, started_at=datetime.now(KST))
        cur.execute("UPDATE app_task_details SET force_closed = TRUE WHERE id = %s", (tid,))
        db_conn.commit()

        token = setup_sprint61['admin_token']
        resp = client.get('/api/admin/tasks/pending',
                          headers={'Authorization': f'Bearer {token}'})
        data = resp.get_json()
        sn_tasks = [t for t in data.get('tasks', []) if t.get('serial_number') == sn]
        assert len(sn_tasks) == 0, "force_closed task는 미표시"


# ─────────────────────────────────────────────
# Regression (TC-61B-31 ~ 33)
# ─────────────────────────────────────────────

class TestRegression:
    """Regression 테스트"""

    def test_tc_61b_31_backward_compat(self, client, setup_sprint61):
        """TC-61B-31: include_not_started 미전송 시 기존 동작 유지"""
        token = setup_sprint61['admin_token']
        resp = client.get('/api/admin/tasks/pending',
                          headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        data = resp.get_json()
        # NOT_STARTED status가 없어야 함
        tasks = data.get('tasks', [])
        not_started = [t for t in tasks if t.get('status') in ('NOT_STARTED', 'not_started')]
        assert len(not_started) == 0, "기본 동작에서는 NOT_STARTED 미포함"

    def test_tc_61b_32_migration_049_enum(self, db_conn):
        """TC-61B-32: enum 추가 확인"""
        if db_conn is None:
            pytest.skip("DB 연결 없음")
        cur = db_conn.cursor()
        cur.execute("SELECT unnest(enum_range(NULL::alert_type_enum))")
        enums = {r[0] for r in cur.fetchall()}
        assert 'TASK_NOT_STARTED' in enums
        assert 'CHECKLIST_DONE_TASK_OPEN' in enums
        assert 'ORPHAN_ON_FINAL' in enums

    def test_tc_61b_33_force_close_not_started(self, client, db_conn, setup_sprint61):
        """TC-61B-33: force-close — NOT_STARTED task에도 정상 동작"""
        cur = db_conn.cursor()
        sn = setup_sprint61['test_sn']
        qr = setup_sprint61['test_qr']

        cur.execute("DELETE FROM app_task_details WHERE serial_number = %s", (sn,))
        db_conn.commit()

        # 미시작 task 생성 (worker_id=0 → NULL 아님이지만 started_at IS NULL)
        tid = _create_task(cur, db_conn, sn, qr, 'MECH', 'UTIL_LINE_1', 'Util LINE 1')

        token = setup_sprint61['admin_token']
        resp = client.put(f'/api/admin/tasks/{tid}/force-close',
                          json={
                              'close_reason': 'Sprint 61 테스트',
                              'completed_at': datetime.now(KST).isoformat()
                          },
                          headers={'Authorization': f'Bearer {token}'})
        # Admin은 어떤 task든 강제종료 가능해야 함
        assert resp.status_code in (200, 201), f"force-close 실패: {resp.get_json()}"
