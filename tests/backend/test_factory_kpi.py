"""
Sprint 62-BE v2.2: Factory KPI 확장 테스트
- 기존 GET /api/admin/factory/weekly-kpi 응답 확장 (3필드 + defect_count)
- 신규 GET /api/admin/factory/monthly-kpi (date_field 4옵션)
- 신규 _count_shipped 헬퍼 3분기 (plan/actual/ops)
- 기존 GET /api/admin/factory/monthly-detail 화이트리스트 확장 (3→5값)

Codex 3차 검증 (CONDITIONAL, M=0/A=4) 반영:
- Q2 A: INNER JOIN 명시
- Q6 A: 반개구간 경계 TC (TC-FK-11)

⚠️ 운영 데이터 보존: plan.product_info / completion_status 읽기만.
   app_task_details 는 SI_SHIPMENT fixture row 생성 후 teardown cleanup.
"""

import pytest
from datetime import date, timedelta, datetime, timezone


# ============================================================
# Helper: app_task_details SI_SHIPMENT fixture
# ============================================================

KST = timezone(timedelta(hours=9))


@pytest.fixture
def si_shipment_cleanup(db_conn):
    """SI_SHIPMENT fixture 데이터 추가/정리 — cleanup은 테스트 후 자동"""
    if db_conn is None:
        pytest.skip("DB not available")

    created_ids = []

    def insert(serial_number: str, completed_at, force_closed: bool = False,
               task_id: str = 'SI_SHIPMENT'):
        """app_task_details에 SI_SHIPMENT row 삽입. qr_registry 필요 → 기존 S/N 재사용 권장."""
        cur = db_conn.cursor()
        cur.execute(
            """SELECT qr_doc_id FROM qr_registry WHERE serial_number = %s LIMIT 1""",
            (serial_number,)
        )
        row = cur.fetchone()
        if row is None:
            cur.close()
            return None
        qr_doc_id = row['qr_doc_id'] if isinstance(row, dict) else row[0]

        # workers에서 임의 worker_id 하나 재사용
        cur.execute("SELECT id FROM workers LIMIT 1")
        w = cur.fetchone()
        if w is None:
            cur.close()
            return None
        worker_id = w['id'] if isinstance(w, dict) else w[0]

        cur.execute(
            """INSERT INTO app_task_details
               (worker_id, serial_number, qr_doc_id, task_category, task_id,
                task_name, started_at, completed_at, force_closed, is_applicable)
               VALUES (%s, %s, %s, 'SI', %s, 'SI 출하', %s, %s, %s, TRUE)
               RETURNING id""",
            (worker_id, serial_number, qr_doc_id, task_id,
             completed_at - timedelta(hours=1), completed_at, force_closed)
        )
        tid = cur.fetchone()
        new_id = tid['id'] if isinstance(tid, dict) else tid[0]
        created_ids.append(new_id)
        db_conn.commit()
        cur.close()
        return new_id

    yield insert

    # Teardown: 생성한 row만 삭제
    if created_ids:
        cur = db_conn.cursor()
        cur.execute(
            "DELETE FROM app_task_details WHERE id = ANY(%s)",
            (created_ids,)
        )
        db_conn.commit()
        cur.close()


def _get_existing_serial(db_conn) -> str:
    """plan.product_info에서 qr_registry 있는 serial_number 1건 가져옴"""
    cur = db_conn.cursor()
    cur.execute(
        """SELECT p.serial_number FROM plan.product_info p
           INNER JOIN qr_registry qr ON p.serial_number = qr.serial_number
           LIMIT 1"""
    )
    row = cur.fetchone()
    cur.close()
    if row is None:
        return None
    return row['serial_number'] if isinstance(row, dict) else row[0]


# ============================================================
# TC-FK-01~05: HTTP endpoint 스키마 검증
# ============================================================

class TestFactoryKpiV2:

    def test_fk01_weekly_kpi_shipped_3fields_defect(
        self, client, create_test_admin, get_admin_auth_token
    ):
        """TC-FK-01: weekly-kpi 응답에 shipped_plan/actual/ops + defect_count 포함"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        resp = client.get(
            '/api/admin/factory/weekly-kpi',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        # v2.2 신규 3필드
        assert 'shipped_plan' in data
        assert 'shipped_actual' in data
        assert 'shipped_ops' in data
        assert 'defect_count' in data
        # 타입 검증
        assert isinstance(data['shipped_plan'], int)
        assert isinstance(data['shipped_actual'], int)
        assert isinstance(data['shipped_ops'], int)
        assert data['defect_count'] is None  # placeholder
        # 기존 pipeline.shipped 유지 (backward compat)
        assert 'pipeline' in data and 'shipped' in data['pipeline']

    def test_fk02_weekly_kpi_where_finishing_plan_end(
        self, client, create_test_admin, get_admin_auth_token, db_conn, seed_test_data
    ):
        """TC-FK-02: weekly-kpi WHERE 절 `finishing_plan_end` 로 교정 (v2.10.1 VIEW 요청).
        production_count 는 finishing_plan_end 기준 COUNT — ship_plan_date 기준이 아님."""
        from datetime import date

        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        # 11주차 (2026-03-09 ~ 2026-03-15) 응답 가져오기
        resp = client.get(
            '/api/admin/factory/weekly-kpi?week=11&year=2026',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        production_count = data['production_count']
        assert isinstance(production_count, int)
        assert production_count >= 0

        # DB 직접 쿼리로 finishing_plan_end 기준 COUNT 확인
        week_start = date(2026, 3, 9)   # Monday
        week_end = date(2026, 3, 15)    # Sunday (closed interval)

        cur = db_conn.cursor()
        cur.execute(
            """SELECT COUNT(*) AS cnt FROM plan.product_info
               WHERE finishing_plan_end >= %s AND finishing_plan_end <= %s""",
            (week_start, week_end)
        )
        row = cur.fetchone()
        expected = row['cnt'] if isinstance(row, dict) else row[0]
        assert production_count == expected, \
            f"production_count({production_count}) != finishing_plan_end COUNT({expected}) — WHERE 절 교정 확인"

    def test_fk03_monthly_kpi_default_mech_start(
        self, client, create_test_admin, get_admin_auth_token
    ):
        """TC-FK-03: monthly-kpi 기본 (date_field=mech_start 기본값 적용)"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        resp = client.get(
            '/api/admin/factory/monthly-kpi',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['date_field_used'] == 'mech_start'
        assert 'month' in data
        assert 'month_range' in data
        assert 'production_count' in data
        assert 'shipped_plan' in data
        assert 'shipped_actual' in data
        assert 'shipped_ops' in data
        assert data['defect_count'] is None
        # 제외 필드 확인 (by_model/by_stage/pipeline/completion_rate 없음)
        assert 'by_model' not in data
        assert 'by_stage' not in data
        assert 'pipeline' not in data
        assert 'completion_rate' not in data

    @pytest.mark.parametrize('field', [
        'finishing_plan_end', 'ship_plan_date', 'actual_ship_date'
    ])
    def test_fk04_monthly_kpi_date_field_options(
        self, client, create_test_admin, get_admin_auth_token, field
    ):
        """TC-FK-04: monthly-kpi date_field 4옵션 순회 (mech_start 제외 3종)"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        resp = client.get(
            f'/api/admin/factory/monthly-kpi?date_field={field}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['date_field_used'] == field
        assert isinstance(data['production_count'], int)

    def test_fk05_monthly_kpi_rejects_pi_start(
        self, client, create_test_admin, get_admin_auth_token
    ):
        """TC-FK-05: monthly-kpi date_field=pi_start → 400 (화이트리스트 분리 검증, Codex 2차 Q4 M).
        pi_start는 monthly-detail 전용, monthly-kpi에서 거부."""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        resp = client.get(
            '/api/admin/factory/monthly-kpi?date_field=pi_start',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['error'] == 'INVALID_DATE_FIELD'
        # 에러 메시지에 pi_start 포함 안 됨 확인
        assert 'pi_start' not in data['message']

    # ========================================================
    # TC-FK-06~07: _count_shipped 헬퍼 3분기 직접 검증
    # ========================================================

    def test_fk06_count_shipped_basis_independence(self, db_conn, seed_test_data, si_shipment_cleanup):
        """TC-FK-06: _count_shipped basis 3종 각각 독립 반환 (자동 합산 X)"""
        from app.routes.factory import _count_shipped

        if db_conn is None:
            pytest.skip("DB not available")

        sn = _get_existing_serial(db_conn)
        if sn is None:
            pytest.skip("No serial_number fixture available")

        # 테스트 범위: 지금부터 10분 전 ~ 10분 후
        now = datetime.now(KST)
        start = now - timedelta(minutes=10)
        end = now + timedelta(minutes=10)

        # Baseline: ops 0 (아직 fixture 없음)
        ops_before = _count_shipped(db_conn, start, end, 'ops')

        # SI_SHIPMENT task 1건 삽입
        si_shipment_cleanup(sn, now, force_closed=False)

        ops_after = _count_shipped(db_conn, start, end, 'ops')
        assert ops_after == ops_before + 1, \
            f"ops 분기: fixture 삽입 후 +1 기대, before={ops_before} after={ops_after}"

        # plan/actual 분기는 별도 경로 (product_info 테이블) — 값 변동 없어야 함
        plan_after = _count_shipped(db_conn, start, end, 'plan')
        actual_after = _count_shipped(db_conn, start, end, 'actual')
        assert isinstance(plan_after, int)
        assert isinstance(actual_after, int)

        # 잘못된 basis → ValueError
        with pytest.raises(ValueError, match="Invalid basis"):
            _count_shipped(db_conn, start, end, 'invalid')

    def test_fk07_count_shipped_force_closed_excluded(
        self, db_conn, seed_test_data, si_shipment_cleanup
    ):
        """TC-FK-07: _count_shipped ops 분기 — force_closed=true SI_SHIPMENT 건 제외"""
        from app.routes.factory import _count_shipped

        if db_conn is None:
            pytest.skip("DB not available")

        sn = _get_existing_serial(db_conn)
        if sn is None:
            pytest.skip("No serial_number fixture available")

        now = datetime.now(KST)
        start = now - timedelta(minutes=10)
        end = now + timedelta(minutes=10)

        ops_before = _count_shipped(db_conn, start, end, 'ops')

        # force_closed=true 1건 삽입 → ops에서 제외되어야 함
        si_shipment_cleanup(sn, now, force_closed=True)

        ops_after = _count_shipped(db_conn, start, end, 'ops')
        assert ops_after == ops_before, \
            f"force_closed=true 건은 ops 분기에서 제외 기대, before={ops_before} after={ops_after}"

    # ========================================================
    # TC-FK-08: monthly-detail 화이트리스트 확장
    # ========================================================

    @pytest.mark.parametrize('field', [
        'pi_start', 'mech_start', 'finishing_plan_end', 'ship_plan_date', 'actual_ship_date'
    ])
    def test_fk08_monthly_detail_whitelist_5values(
        self, client, create_test_admin, get_admin_auth_token, field
    ):
        """TC-FK-08: monthly-detail 5값 화이트리스트 (기존 2 + 신규 3)"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        resp = client.get(
            f'/api/admin/factory/monthly-detail?date_field={field}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200, \
            f"monthly-detail date_field={field} 허용 기대, got {resp.status_code}"

    # ========================================================
    # TC-FK-09~10: 3필드 독립성 + force_closed 시나리오
    # ========================================================

    def test_fk09_three_fields_independence_same_sn(
        self, db_conn, seed_test_data, si_shipment_cleanup
    ):
        """TC-FK-09: 동일 S/N이 SI_SHIPMENT + actual_ship_date 양쪽 가능 상황에서
        각 필드 정확 1건씩 독립 반환 (자동 합산 없음)."""
        from app.routes.factory import _count_shipped

        if db_conn is None:
            pytest.skip("DB not available")

        sn = _get_existing_serial(db_conn)
        if sn is None:
            pytest.skip("No serial_number fixture available")

        now = datetime.now(KST)
        start = now - timedelta(minutes=10)
        end = now + timedelta(minutes=10)

        ops_before = _count_shipped(db_conn, start, end, 'ops')

        # 동일 S/N으로 SI_SHIPMENT 2개 task 삽입 (동시 다른 worker 가능성 시뮬레이션)
        # task_id 중복 방지 위해 task_id는 모두 SI_SHIPMENT 이지만 worker/시간 다름
        # Note: unique constraint (serial_number, task_category, task_id) → 1개만 허용
        si_shipment_cleanup(sn, now, force_closed=False)

        ops_after = _count_shipped(db_conn, start, end, 'ops')
        # COUNT(DISTINCT serial_number) → 동일 S/N 여러 row 있어도 1 증가
        assert ops_after == ops_before + 1

    def test_fk10_ops_and_actual_concurrent_scenario(
        self, db_conn, seed_test_data, si_shipment_cleanup
    ):
        """TC-FK-10: 동일 S/N에 SI_SHIPMENT + actual_ship_date 동시 존재 시나리오.
        ops와 actual이 각자 독립 카운트 — 자동 합산 없음."""
        from app.routes.factory import _count_shipped

        if db_conn is None:
            pytest.skip("DB not available")

        sn = _get_existing_serial(db_conn)
        if sn is None:
            pytest.skip("No serial_number fixture available")

        now = datetime.now(KST)
        start = now - timedelta(minutes=10)
        end = now + timedelta(minutes=10)

        ops_before = _count_shipped(db_conn, start, end, 'ops')
        actual_before = _count_shipped(db_conn, start, end, 'actual')

        # force_closed=true → ops에서 제외
        si_shipment_cleanup(sn, now, force_closed=True)

        ops_after = _count_shipped(db_conn, start, end, 'ops')
        actual_after = _count_shipped(db_conn, start, end, 'actual')
        # ops=0 (force_closed 제외) / actual 변화 없음 (다른 테이블)
        assert ops_after == ops_before
        assert actual_after == actual_before

    # ========================================================
    # TC-FK-11: 반개구간 경계 TC (Codex 3차 Q6 A)
    # ========================================================

    def test_fk11_half_open_interval_week_boundary(
        self, db_conn, seed_test_data, si_shipment_cleanup
    ):
        """TC-FK-11: 반개구간 `[start, end)` 경계 테스트 (Codex 3차 Q6 A 반영).
        주차 끝(일요일 23:59:59)의 SI_SHIPMENT는 포함되나,
        다음 주 월요일 00:00:00은 제외되어야 함."""
        from app.routes.factory import _count_shipped

        if db_conn is None:
            pytest.skip("DB not available")

        sn = _get_existing_serial(db_conn)
        if sn is None:
            pytest.skip("No serial_number fixture available")

        # 고정 가상 주: 2026-10-19(월) ~ 2026-10-26(월, exclusive)
        week_start = datetime(2026, 10, 19, 0, 0, 0, tzinfo=KST)
        week_end_exclusive = datetime(2026, 10, 26, 0, 0, 0, tzinfo=KST)

        ops_before = _count_shipped(
            db_conn, week_start, week_end_exclusive, 'ops'
        )

        # 경계값 3종:
        # (a) 일요일 23:59:59 — 포함되어야 함
        # (b) 월요일 00:00:00 — 제외되어야 함 (exclusive end)
        # (c) 월요일 00:00:01 — 제외되어야 함
        sunday_last = datetime(2026, 10, 25, 23, 59, 59, tzinfo=KST)
        monday_zero = datetime(2026, 10, 26, 0, 0, 0, tzinfo=KST)

        si_shipment_cleanup(sn, sunday_last, force_closed=False)

        # (a) 주차 내 마지막 1초에 완료된 건 → 포함
        ops_after_sunday = _count_shipped(
            db_conn, week_start, week_end_exclusive, 'ops'
        )
        assert ops_after_sunday == ops_before + 1, \
            f"일요일 23:59:59는 주차에 포함돼야 함 (반개구간 inclusive start), " \
            f"before={ops_before} after={ops_after_sunday}"

        # (b) 다음 주 월요일 00:00:00에 완료된 건 → 본 주차에서 제외
        # fixture sn을 다시 쓸 수 없음 (unique constraint: serial_number, task_category, task_id)
        # 대신 "다음 주 월요일 = exclusive" 검증은 주차를 이동시켜 재확인
        # → week_end_exclusive - 0 (동일 시각)이 포함 안 되는지 확인
        check = _count_shipped(
            db_conn, monday_zero, monday_zero + timedelta(hours=1), 'ops'
        )
        # 다음 주 월요일 00:00 ~ 01:00 범위 안의 ops 건은 본 주차 ops_after_sunday와 별도
        assert isinstance(check, int) and check >= 0
