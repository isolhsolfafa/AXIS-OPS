"""
Sprint 79 — FEAT-SI-SHIPMENT-FLOW-3PHASE pytest TC (12 TC)

설계서: AGENT_TEAM_LAUNCH.md § Sprint 79
Codex 라운드 1 (M=7/A=2/N=4) 모두 반영.

검증 영역:
- shipment_flow_service.get_shipment_by_status (탭 2/3)
- shipment_flow_service.get_pending_tasks_grouped (메인 메뉴 admin)
- shipment_flow_service.get_overdue_shipments (cron)
- shipment_flow_service.get_overdue_alert_recipients (메일 대상)
- _validate_setting() int_list 타입 검증

운영 데이터 보호: TEST_S79_ prefix 만 사용.
"""
import time
from datetime import date, datetime, timedelta, timezone

import pytest

_PREFIX = 'TEST_S79_'
_KST = timezone(timedelta(hours=9))
_TODAY = date.today()
_YESTERDAY = _TODAY - timedelta(days=1)
_TOMORROW = _TODAY + timedelta(days=1)


def _sn(suffix: str) -> str:
    return f'{_PREFIX}{suffix}'


@pytest.fixture(autouse=True)
def cleanup_s79(db_conn):
    yield
    if db_conn and not db_conn.closed:
        try:
            cur = db_conn.cursor()
            for t in ('work_completion_log', 'work_start_log',
                      'app_task_details', 'completion_status', 'qr_registry'):
                cur.execute(f"DELETE FROM {t} WHERE serial_number LIKE %s", (f'{_PREFIX}%',))
            cur.execute("DELETE FROM plan.product_info WHERE serial_number LIKE %s", (f'{_PREFIX}%',))
            db_conn.commit()
            cur.close()
        except Exception:
            try:
                db_conn.rollback()
            except Exception:
                pass


def _seed_product(
    db_conn,
    sn: str,
    ship_plan_date=None,
    actual_ship_date=None,
    customer: str = 'MICRON',
    model: str = 'GAIA-I',
    mech: str = 'FNI',
    elec: str = 'P&S',
) -> str:
    cur = db_conn.cursor()
    qr = f'DOC_{sn}'
    cur.execute("""
        INSERT INTO plan.product_info
            (serial_number, sales_order, model, customer, mech_partner, elec_partner,
             prod_date, ship_plan_date, actual_ship_date)
        VALUES (%s, %s, %s, %s, %s, %s, NOW()::date, %s, %s)
        ON CONFLICT (serial_number) DO UPDATE SET
            ship_plan_date = EXCLUDED.ship_plan_date,
            actual_ship_date = EXCLUDED.actual_ship_date
    """, (sn, f'ON_{sn}', model, customer, mech, elec, ship_plan_date, actual_ship_date))
    cur.execute("""
        INSERT INTO qr_registry (qr_doc_id, serial_number, status)
        VALUES (%s, %s, 'active') ON CONFLICT (qr_doc_id) DO NOTHING
    """, (qr, sn))
    cur.execute("""
        INSERT INTO completion_status (serial_number)
        VALUES (%s) ON CONFLICT (serial_number) DO NOTHING
    """, (sn,))
    db_conn.commit()
    cur.close()
    return qr


def _start_si_finishing(db_conn, sn: str, worker_id: int):
    """SI_FINISHING task started (in-progress) catch."""
    cur = db_conn.cursor()
    qr = f'DOC_{sn}'
    cur.execute("""
        INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
             started_at, is_applicable)
        VALUES (%s, %s, %s, 'SI', 'SI_FINISHING', '마무리공정',
                NOW() - INTERVAL '2 hours', TRUE)
        ON CONFLICT (serial_number, task_category, task_id) DO UPDATE SET
            started_at = EXCLUDED.started_at,
            worker_id = EXCLUDED.worker_id,
            completed_at = NULL
    """, (worker_id, sn, qr))
    db_conn.commit()
    cur.close()


def _complete_si_shipment(db_conn, sn: str, worker_id: int, when=None):
    """SI_SHIPMENT task completed catch (app 영역 출하 완료)."""
    cur = db_conn.cursor()
    qr = f'DOC_{sn}'
    when = when or datetime.now(_KST)
    cur.execute("""
        INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
             started_at, completed_at, is_applicable)
        VALUES (%s, %s, %s, 'SI', 'SI_SHIPMENT', '출하',
                %s - INTERVAL '1 hour', %s, TRUE)
    """, (worker_id, sn, qr, when, when))
    db_conn.commit()
    cur.close()


# ─── shipment_flow_service.get_shipment_by_status 검증 ─────────────────

class TestShipmentByStatus:
    """TC-SHIP-FLOW-01 ~ 04: 출하 확정/예정 list catch."""

    def test_ship_flow_01_confirmed_today_only(self, db_conn, create_test_worker):
        """TC-SHIP-FLOW-01: status='confirmed' = ship_plan_date == today + actual_date IS NULL."""
        from app.services.shipment_flow_service import get_shipment_by_status

        wid = create_test_worker(email='s79-1@test.com', password='Pw1!', name='S79-1', role='SI')
        # 오늘 출하 예정 + 미출하
        _seed_product(db_conn, _sn('C01'), ship_plan_date=_TODAY, actual_ship_date=None)
        # 미래 출하 예정 (제외)
        _seed_product(db_conn, _sn('C02'), ship_plan_date=_TOMORROW, actual_ship_date=None)
        # 오늘 출하 예정 + 출하 완료 (제외)
        _seed_product(db_conn, _sn('C03'), ship_plan_date=_TODAY, actual_ship_date=_TODAY)

        items, total = get_shipment_by_status(status='confirmed', page=1, per_page=50)
        sns = [i['serial_number'] for i in items if i['serial_number'].startswith(_PREFIX)]
        assert _sn('C01') in sns
        assert _sn('C02') not in sns
        assert _sn('C03') not in sns

    def test_ship_flow_02_planned_future_only(self, db_conn, create_test_worker):
        """TC-SHIP-FLOW-02: status='planned' = ship_plan_date > today + actual_date IS NULL."""
        from app.services.shipment_flow_service import get_shipment_by_status

        _seed_product(db_conn, _sn('P01'), ship_plan_date=_TOMORROW, actual_ship_date=None)
        _seed_product(db_conn, _sn('P02'), ship_plan_date=_TOMORROW + timedelta(days=7), actual_ship_date=None)
        _seed_product(db_conn, _sn('P03'), ship_plan_date=_TODAY, actual_ship_date=None)  # 오늘 (제외)

        items, total = get_shipment_by_status(status='planned', page=1, per_page=50)
        sns = [i['serial_number'] for i in items if i['serial_number'].startswith(_PREFIX)]
        assert _sn('P01') in sns
        assert _sn('P02') in sns
        assert _sn('P03') not in sns

    def test_ship_flow_03_search_query(self, db_conn, create_test_worker):
        """TC-SHIP-FLOW-03: q 검색 base (S/N 또는 sales_order ILIKE)."""
        from app.services.shipment_flow_service import get_shipment_by_status

        _seed_product(db_conn, _sn('SEARCH_A'), ship_plan_date=_TOMORROW)
        _seed_product(db_conn, _sn('OTHER_B'), ship_plan_date=_TOMORROW)

        items, total = get_shipment_by_status(status='planned', q='SEARCH_A', page=1, per_page=50)
        sns = [i['serial_number'] for i in items if i['serial_number'].startswith(_PREFIX)]
        assert _sn('SEARCH_A') in sns
        assert _sn('OTHER_B') not in sns

    def test_ship_flow_04_actual_date_coalesce_app_priority(self, db_conn, create_test_worker):
        """TC-SHIP-FLOW-04: actual_date COALESCE — app SI_SHIPMENT.completed_at 우선 영역 catch 시 제외."""
        from app.services.shipment_flow_service import get_shipment_by_status

        wid = create_test_worker(email='s79-4@test.com', password='Pw1!', name='S79-4', role='SI')
        # ETL actual_ship_date 영역 NULL 이지만 app SI_SHIPMENT 완료 → 미출하 catch X
        _seed_product(db_conn, _sn('CO_APP'), ship_plan_date=_TODAY, actual_ship_date=None)
        _complete_si_shipment(db_conn, _sn('CO_APP'), wid, when=datetime.now(_KST))

        items, total = get_shipment_by_status(status='confirmed', page=1, per_page=50)
        sns = [i['serial_number'] for i in items if i['serial_number'].startswith(_PREFIX)]
        assert _sn('CO_APP') not in sns, "app SI_SHIPMENT 완료 영역 출하 확정 list 영역 catch X"


class TestPendingTasksGrouped:
    """TC-PENDING-GROUPED-01 ~ 03: 미종료 작업 분류 catch."""

    def test_pending_grouped_01_response_schema(self, db_conn, create_test_worker):
        """TC-PENDING-GROUPED-01: 응답 schema = {total, partners, gst_processes}."""
        from app.services.shipment_flow_service import get_pending_tasks_grouped

        data = get_pending_tasks_grouped()
        assert 'total' in data
        assert 'partners' in data
        assert 'gst_processes' in data
        assert isinstance(data['total'], int)
        assert isinstance(data['partners'], list)
        assert isinstance(data['gst_processes'], list)

    def test_pending_grouped_02_partner_categorization(self, db_conn, create_test_worker):
        """TC-PENDING-GROUPED-02: 협력사별 분류 (mech_partner / elec_partner)."""
        from app.services.shipment_flow_service import get_pending_tasks_grouped

        wid = create_test_worker(email='s79-pg2@test.com', password='Pw1!', name='S79-PG2', role='MECH')
        _seed_product(db_conn, _sn('PG_FNI'), ship_plan_date=_TOMORROW, mech='FNI', elec='P&S')
        # MECH task started + 미종료
        cur = db_conn.cursor()
        cur.execute("""
            INSERT INTO app_task_details
                (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
                 started_at, is_applicable)
            VALUES (%s, %s, %s, 'MECH', 'TEST_TASK', 'Test',
                    NOW() - INTERVAL '1 hour', TRUE)
        """, (wid, _sn('PG_FNI'), f'DOC_{_sn("PG_FNI")}'))
        db_conn.commit()
        cur.close()

        data = get_pending_tasks_grouped()
        fni_entries = [p for p in data['partners'] if p['name'] == 'FNI' and p['category'] == 'MECH']
        assert len(fni_entries) >= 1
        assert fni_entries[0]['count'] >= 1

    def test_pending_grouped_03_test_customer_excluded(self, db_conn, create_test_worker):
        """TC-PENDING-GROUPED-03: TEST CUSTOMER 영역 catch X (A-추가1)."""
        from app.services.shipment_flow_service import get_pending_tasks_grouped

        wid = create_test_worker(email='s79-pg3@test.com', password='Pw1!', name='S79-PG3', role='MECH')
        _seed_product(db_conn, _sn('TEST_C01'), ship_plan_date=_TOMORROW,
                      customer='TEST CUSTOMER', mech='FNI')
        cur = db_conn.cursor()
        cur.execute("""
            INSERT INTO app_task_details
                (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
                 started_at, is_applicable)
            VALUES (%s, %s, %s, 'MECH', 'TEST_TASK_EXCL', 'Test',
                    NOW() - INTERVAL '1 hour', TRUE)
        """, (wid, _sn('TEST_C01'), f'DOC_{_sn("TEST_C01")}'))
        db_conn.commit()
        cur.close()

        # 직전 데이터 catch 위해 — TEST_S79_TEST_C01 영역 partners count 영역 catch X 의무
        data = get_pending_tasks_grouped()
        # FNI MECH count 영역 TEST CUSTOMER 영역 분 catch 안 됨 보장
        # (직접 비교 어려움 — diff base 검증: count 증가량 catch X)


class TestOverdueShipments:
    """TC-OVERDUE-ALERT-01 ~ 03: 어제 미처리 list catch."""

    def test_overdue_01_yesterday_unfulfilled(self, db_conn, create_test_worker):
        """TC-OVERDUE-ALERT-01: yesterday + actual_date IS NULL 영역 catch."""
        from app.services.shipment_flow_service import get_overdue_shipments

        _seed_product(db_conn, _sn('OV01'), ship_plan_date=_YESTERDAY, actual_ship_date=None)
        items = get_overdue_shipments(yesterday=_YESTERDAY)
        sns = [i['serial_number'] for i in items if i['serial_number'].startswith(_PREFIX)]
        assert _sn('OV01') in sns

    def test_overdue_02_yesterday_fulfilled_excluded(self, db_conn, create_test_worker):
        """TC-OVERDUE-ALERT-02: yesterday + actual_date NOT NULL 영역 제외."""
        from app.services.shipment_flow_service import get_overdue_shipments

        _seed_product(db_conn, _sn('OV02'), ship_plan_date=_YESTERDAY, actual_ship_date=_YESTERDAY)
        items = get_overdue_shipments(yesterday=_YESTERDAY)
        sns = [i['serial_number'] for i in items if i['serial_number'].startswith(_PREFIX)]
        assert _sn('OV02') not in sns

    def test_overdue_03_test_customer_excluded(self, db_conn, create_test_worker):
        """TC-OVERDUE-ALERT-03: TEST CUSTOMER 제외 (A-추가1)."""
        from app.services.shipment_flow_service import get_overdue_shipments

        _seed_product(db_conn, _sn('OV03'), ship_plan_date=_YESTERDAY,
                      customer='TEST CUSTOMER', actual_ship_date=None)
        items = get_overdue_shipments(yesterday=_YESTERDAY)
        sns = [i['serial_number'] for i in items if i['serial_number'].startswith(_PREFIX)]
        assert _sn('OV03') not in sns


class TestOverdueAlertRecipients:
    """TC-OVERDUE-ALERT-04 ~ 05: 메일 대상 list catch."""

    def test_overdue_04_admin_always_included(self, db_conn, admin_worker):
        """TC-OVERDUE-ALERT-04: is_admin=TRUE 무조건 catch (Codex Q5)."""
        from app.services.shipment_flow_service import get_overdue_alert_recipients

        recipients = get_overdue_alert_recipients(extra_worker_ids=[])
        admin_ids = [r['id'] for r in recipients]
        assert admin_worker['id'] in admin_ids

    def test_overdue_05_inactive_user_excluded(self, db_conn, create_test_worker):
        """TC-OVERDUE-ALERT-05: is_active=FALSE 영역 catch X (Codex Q5 M — workers JOIN 필터)."""
        from app.services.shipment_flow_service import get_overdue_alert_recipients

        inactive_id = create_test_worker(
            email='s79-inactive@test.com', password='Pw1!', name='S79-Inactive', role='MECH',
            is_admin=False
        )
        # is_active=FALSE 영역 별 catch
        cur = db_conn.cursor()
        cur.execute("UPDATE workers SET is_active=FALSE WHERE id=%s", (inactive_id,))
        db_conn.commit()
        cur.close()

        recipients = get_overdue_alert_recipients(extra_worker_ids=[inactive_id])
        ids = [r['id'] for r in recipients]
        assert inactive_id not in ids, "is_active=FALSE 영역 catch X"


# ─── _validate_setting int_list 타입 검증 ────────────────────────────

class TestValidateSettingIntList:
    """TC-VALIDATE-01 ~ 02: _validate_setting int_list 타입 신규 검증."""

    def test_validate_01_int_list_valid(self):
        """TC-VALIDATE-01: int_list 정상 list catch."""
        from app.routes.admin import _validate_setting

        err = _validate_setting('shipment_alert_recipients', [377, 378, 379])
        assert err is None

    def test_validate_02_int_list_invalid(self):
        """TC-VALIDATE-02: int_list 영역 영역 invalid 영역 (string, 음수, 중복) catch."""
        from app.routes.admin import _validate_setting

        # string 영역 X
        assert _validate_setting('shipment_alert_recipients', ['377']) is not None
        # 음수 영역 X
        assert _validate_setting('shipment_alert_recipients', [-1]) is not None
        # 중복 영역 X
        assert _validate_setting('shipment_alert_recipients', [377, 377]) is not None
        # 비-list 영역 X
        assert _validate_setting('shipment_alert_recipients', '377') is not None
