"""
Sprint 36: TMS confirmable TANK_MODULE only 로직 테스트
- White-box: _calc_sn_progress task_id 레벨 확장 검증
- White-box: _is_process_confirmable TMS→TANK_MODULE 분기 검증
- Gray-box: API 레벨 TMS confirmable 통합 검증
- Regression: MECH/ELEC 기존 confirmable 영향 없음 확인

설계 원칙:
  실적확인(confirmable) = TANK_MODULE만
  progress/알람 = TANK_MODULE + PRESSURE_TEST 전체
"""

import sys
from pathlib import Path

# conftest.py의 app fixture가 로드되기 전에도 backend import가 가능하도록
_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest
from datetime import date, timedelta


# ── 테스트 데이터 prefix ──────────────────────────
_PREFIX = 'SN-SP36-'


# ── Admin 토큰 픽스처 ──────────────────────────────
@pytest.fixture
def admin_token(db_conn, seed_test_data, get_auth_token):
    """Seed admin의 실제 worker_id로 JWT 토큰 생성"""
    cursor = db_conn.cursor()
    cursor.execute("SELECT id FROM workers WHERE email = 'seed_admin@test.axisos.com'")
    row = cursor.fetchone()
    cursor.close()
    return get_auth_token(row[0], role='ADMIN', is_admin=True)


def _insert_product(db_conn, serial_number, qr_doc_id, model, sales_order,
                    mech_start=None, mech_partner='GST', elec_partner='GST',
                    has_docking=False):
    """테스트용 제품 + QR 등록
    주의: has_docking은 plan.product_info에 없음 → model_config 테이블에서 관리.
    model_prefix(GAIA→has_docking=True)로 자동 결정되므로 파라미터는 무시됨.
    mech_end = mech_start로 설정하여 production performance API 쿼리 범위에 포함.
    """
    if mech_start is None:
        mech_start = date.today()
    mech_end = mech_start  # 같은 날 → performance API 주간/월간 필터 통과
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO plan.product_info
            (serial_number, model, sales_order, mech_start, mech_end, mech_partner, elec_partner)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (serial_number) DO NOTHING
    """, (serial_number, model, sales_order, mech_start, mech_end, mech_partner, elec_partner))
    cursor.execute("""
        INSERT INTO public.qr_registry (qr_doc_id, serial_number, status)
        VALUES (%s, %s, 'active')
        ON CONFLICT (qr_doc_id) DO NOTHING
    """, (qr_doc_id, serial_number))
    db_conn.commit()
    cursor.close()


def _insert_task(db_conn, serial_number, qr_doc_id, category, task_id,
                 task_name, completed=False, is_applicable=True):
    """테스트용 태스크 등록"""
    cursor = db_conn.cursor()
    completed_at = 'NOW()' if completed else 'NULL'
    cursor.execute(f"""
        INSERT INTO app_task_details
            (serial_number, qr_doc_id, task_category, task_id, task_name,
             is_applicable, completed_at)
        VALUES (%s, %s, %s, %s, %s, %s, {completed_at})
        ON CONFLICT (serial_number, qr_doc_id, task_category, task_id) DO NOTHING
    """, (serial_number, qr_doc_id, category, task_id, task_name, is_applicable))
    db_conn.commit()
    cursor.close()


def _enable_confirm_settings(db_conn, process_types=None):
    """admin_settings에 confirm_*_enabled = true 설정"""
    if process_types is None:
        process_types = ['mech', 'elec', 'tm', 'pi', 'qi', 'si']
    cursor = db_conn.cursor()
    for pt in process_types:
        key = f'confirm_{pt}_enabled'
        cursor.execute("""
            INSERT INTO admin_settings (setting_key, setting_value, description)
            VALUES (%s, 'true', 'test')
            ON CONFLICT (setting_key) DO UPDATE SET setting_value = 'true'
        """, (key,))
    db_conn.commit()
    cursor.close()


def _cleanup(db_conn, prefix=_PREFIX):
    """테스트 데이터 정리"""
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM plan.production_confirm WHERE sales_order LIKE %s",
                   (f'ON-{prefix}%',))
    cursor.execute("DELETE FROM app_task_details WHERE serial_number LIKE %s",
                   (f'{prefix}%',))
    cursor.execute("DELETE FROM completion_status WHERE serial_number LIKE %s",
                   (f'{prefix}%',))
    cursor.execute("DELETE FROM qr_registry WHERE serial_number LIKE %s",
                   (f'{prefix}%',))
    cursor.execute("DELETE FROM plan.product_info WHERE serial_number LIKE %s",
                   (f'{prefix}%',))
    db_conn.commit()
    cursor.close()


# ══════════════════════════════════════════════════════════════
# White-box: _calc_sn_progress — task_id 레벨 데이터 반환 검증
# ══════════════════════════════════════════════════════════════

class TestCalcSnProgressTaskLevel:
    """_calc_sn_progress()가 task_id 레벨 데이터를 정확히 반환하는지 검증"""

    def test_tms_tasks_dict_contains_both_tasks(self, db_conn):
        """WB-01: TMS 카테고리에 TANK_MODULE + PRESSURE_TEST → tasks dict에 둘 다 존재"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        sn = f'{_PREFIX}WB01'
        qr = f'DOC-{sn}'

        _insert_product(db_conn, sn, qr, 'GAIA-I', f'ON-{sn}', has_docking=True)
        _insert_task(db_conn, sn, qr, 'TMS', 'TANK_MODULE', '탱크모듈', completed=True)
        _insert_task(db_conn, sn, qr, 'TMS', 'PRESSURE_TEST', '가압검사', completed=False)

        # 직접 SQL 실행하여 _calc_sn_progress 결과와 동일한 구조 확인
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT task_category, task_id,
                   COUNT(*) AS total,
                   COUNT(completed_at) AS completed
            FROM app_task_details
            WHERE serial_number = %s AND is_applicable = TRUE
            GROUP BY task_category, task_id
        """, (sn,))
        rows = cursor.fetchall()
        cursor.close()

        task_ids = {(r[0], r[1]) for r in rows}
        assert ('TMS', 'TANK_MODULE') in task_ids
        assert ('TMS', 'PRESSURE_TEST') in task_ids

        # TANK_MODULE: completed=1, PRESSURE_TEST: completed=0
        for r in rows:
            if r[0] == 'TMS' and r[1] == 'TANK_MODULE':
                assert r[3] == 1  # completed
            if r[0] == 'TMS' and r[1] == 'PRESSURE_TEST':
                assert r[3] == 0  # completed

        _cleanup(db_conn)

    def test_mech_tasks_no_filter(self, db_conn):
        """WB-02: MECH 카테고리는 task_id 레벨 데이터 존재하되, confirmable은 전체 카테고리 체크"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        sn = f'{_PREFIX}WB02'
        qr = f'DOC-{sn}'

        _insert_product(db_conn, sn, qr, 'GAIA-I', f'ON-{sn}')
        _insert_task(db_conn, sn, qr, 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)
        _insert_task(db_conn, sn, qr, 'MECH', 'WELDING', '용접', completed=False)

        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT task_category, task_id,
                   COUNT(*) AS total,
                   COUNT(completed_at) AS completed
            FROM app_task_details
            WHERE serial_number = %s AND is_applicable = TRUE
            GROUP BY task_category, task_id
        """, (sn,))
        rows = cursor.fetchall()
        cursor.close()

        # MECH에 2개 task_id 존재
        mech_tasks = [(r[1], r[2], r[3]) for r in rows if r[0] == 'MECH']
        assert len(mech_tasks) == 2

        _cleanup(db_conn)


# ══════════════════════════════════════════════════════════════
# White-box: _is_process_confirmable — TMS TANK_MODULE only 분기
# ══════════════════════════════════════════════════════════════

class TestIsProcessConfirmable:
    """_is_process_confirmable() 함수 직접 호출 테스트 (단위 테스트)"""

    def test_tms_tank_module_done_pressure_not_done(self):
        """WB-03: TMS — TANK_MODULE 완료 + PRESSURE_TEST 미완료 → confirmable=True"""
        from app.routes.production import _is_process_confirmable

        sns_progress = {
            'SN-001': {
                'TMS': {
                    'total': 10, 'completed': 5, 'pct': 50.0,
                    'tasks': {
                        'TANK_MODULE': {'total': 5, 'completed': 5},
                        'PRESSURE_TEST': {'total': 5, 'completed': 0},
                    }
                }
            }
        }
        settings = {'confirm_tm_enabled': True}

        result = _is_process_confirmable(
            sns_progress, 'TMS', settings,
            proc_key='TM', serial_numbers=['SN-001']
        )
        assert result is True

    def test_tms_tank_module_not_done(self):
        """WB-04: TMS — TANK_MODULE 미완료 → confirmable=False"""
        from app.routes.production import _is_process_confirmable

        sns_progress = {
            'SN-001': {
                'TMS': {
                    'total': 10, 'completed': 8, 'pct': 80.0,
                    'tasks': {
                        'TANK_MODULE': {'total': 5, 'completed': 3},
                        'PRESSURE_TEST': {'total': 5, 'completed': 5},
                    }
                }
            }
        }
        settings = {'confirm_tm_enabled': True}

        result = _is_process_confirmable(
            sns_progress, 'TMS', settings,
            proc_key='TM', serial_numbers=['SN-001']
        )
        assert result is False

    def test_tms_both_done(self):
        """WB-05: TMS — 둘 다 완료 → confirmable=True"""
        from app.routes.production import _is_process_confirmable

        sns_progress = {
            'SN-001': {
                'TMS': {
                    'total': 10, 'completed': 10, 'pct': 100.0,
                    'tasks': {
                        'TANK_MODULE': {'total': 5, 'completed': 5},
                        'PRESSURE_TEST': {'total': 5, 'completed': 5},
                    }
                }
            }
        }
        settings = {'confirm_tm_enabled': True}

        result = _is_process_confirmable(
            sns_progress, 'TMS', settings,
            proc_key='TM', serial_numbers=['SN-001']
        )
        assert result is True

    def test_tms_setting_disabled(self):
        """WB-06: confirm_tm_enabled=False → confirmable=False (설정 우선)"""
        from app.routes.production import _is_process_confirmable

        sns_progress = {
            'SN-001': {
                'TMS': {
                    'total': 10, 'completed': 10, 'pct': 100.0,
                    'tasks': {
                        'TANK_MODULE': {'total': 5, 'completed': 5},
                        'PRESSURE_TEST': {'total': 5, 'completed': 5},
                    }
                }
            }
        }
        settings = {'confirm_tm_enabled': False}

        result = _is_process_confirmable(
            sns_progress, 'TMS', settings,
            proc_key='TM', serial_numbers=['SN-001']
        )
        assert result is False

    def test_tms_no_task_data(self):
        """WB-07: TMS에 task 데이터 없음 (has_docking=false 모델) → confirmable=False"""
        from app.routes.production import _is_process_confirmable

        sns_progress = {
            'SN-001': {
                'MECH': {'total': 5, 'completed': 5, 'pct': 100.0, 'tasks': {}}
            }
        }
        settings = {'confirm_tm_enabled': True}

        result = _is_process_confirmable(
            sns_progress, 'TMS', settings,
            proc_key='TM', serial_numbers=['SN-001']
        )
        assert result is False

    def test_tms_multi_sn_one_incomplete(self):
        """WB-08: 다대 S/N — 1대 TANK_MODULE 미완료 → confirmable=False"""
        from app.routes.production import _is_process_confirmable

        sns_progress = {
            'SN-001': {
                'TMS': {
                    'total': 10, 'completed': 10, 'pct': 100.0,
                    'tasks': {
                        'TANK_MODULE': {'total': 5, 'completed': 5},
                        'PRESSURE_TEST': {'total': 5, 'completed': 5},
                    }
                }
            },
            'SN-002': {
                'TMS': {
                    'total': 10, 'completed': 6, 'pct': 60.0,
                    'tasks': {
                        'TANK_MODULE': {'total': 5, 'completed': 1},  # 미완료
                        'PRESSURE_TEST': {'total': 5, 'completed': 5},
                    }
                }
            },
        }
        settings = {'confirm_tm_enabled': True}

        result = _is_process_confirmable(
            sns_progress, 'TMS', settings,
            proc_key='TM', serial_numbers=['SN-001', 'SN-002']
        )
        assert result is False

    def test_mech_category_level_check(self):
        """WB-09: MECH — _CONFIRM_TASK_FILTER 미등록 → 카테고리 전체 체크 (Regression)"""
        from app.routes.production import _is_process_confirmable

        sns_progress = {
            'SN-001': {
                'MECH': {
                    'total': 5, 'completed': 5, 'pct': 100.0,
                    'tasks': {
                        'SELF_INSPECTION': {'total': 3, 'completed': 3},
                        'WELDING': {'total': 2, 'completed': 2},
                    }
                }
            }
        }
        settings = {'confirm_mech_enabled': True}

        result = _is_process_confirmable(
            sns_progress, 'MECH', settings,
            serial_numbers=['SN-001']
        )
        assert result is True

    def test_mech_partial_incomplete(self):
        """WB-10: MECH — 일부 task 미완료 → confirmable=False (Regression)"""
        from app.routes.production import _is_process_confirmable

        sns_progress = {
            'SN-001': {
                'MECH': {
                    'total': 5, 'completed': 3, 'pct': 60.0,
                    'tasks': {
                        'SELF_INSPECTION': {'total': 3, 'completed': 3},
                        'WELDING': {'total': 2, 'completed': 0},
                    }
                }
            }
        }
        settings = {'confirm_mech_enabled': True}

        result = _is_process_confirmable(
            sns_progress, 'MECH', settings,
            serial_numbers=['SN-001']
        )
        assert result is False


# ══════════════════════════════════════════════════════════════
# Gray-box: API 레벨 TMS confirmable 통합 테스트
# ══════════════════════════════════════════════════════════════

class TestTmsConfirmableApi:
    """GET /api/admin/production/performance — TMS confirmable 검증"""

    def test_tm_confirmable_tank_module_done(self, client, db_conn, get_auth_token, admin_token):
        """GB-01: TANK_MODULE 완료 + PRESSURE_TEST 미완료 → TM confirmable=True"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn, ['tm'])
        today = date.today()
        sn = f'{_PREFIX}GB01'
        qr = f'DOC-{sn}'

        _insert_product(db_conn, sn, qr, 'GAIA-I', f'ON-{sn}', today,
                        mech_partner='TMS', has_docking=True)
        _insert_task(db_conn, sn, qr, 'TMS', 'TANK_MODULE', '탱크모듈', completed=True)
        _insert_task(db_conn, sn, qr, 'TMS', 'PRESSURE_TEST', '가압검사', completed=False)

        iso_week = today.isocalendar()[1]
        token = admin_token

        resp = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        order = next(
            (o for o in data['orders'] if o['sales_order'] == f'ON-{sn}'), None
        )
        assert order is not None, f"Order ON-{sn} not found in response"

        tm_proc = order['processes'].get('TM', {})
        # TM 프로세스는 sn_confirms 구조 → all_confirmable 키 사용
        all_confirmable = tm_proc.get('all_confirmable', tm_proc.get('confirmable'))
        assert all_confirmable is True, (
            f"TM all_confirmable should be True (TANK_MODULE done), got: {tm_proc}"
        )
        # progress는 전체 포함 (TANK_MODULE + PRESSURE_TEST)
        assert tm_proc['total'] == 2
        assert tm_proc['completed'] == 1  # TANK_MODULE만 완료
        assert tm_proc['pct'] == 50.0

        _cleanup(db_conn)

    def test_tm_not_confirmable_tank_module_incomplete(self, client, db_conn, get_auth_token, admin_token):
        """GB-02: TANK_MODULE 미완료 → TM confirmable=False"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn, ['tm'])
        today = date.today()
        sn = f'{_PREFIX}GB02'
        qr = f'DOC-{sn}'

        _insert_product(db_conn, sn, qr, 'GAIA-I', f'ON-{sn}', today,
                        mech_partner='TMS', has_docking=True)
        _insert_task(db_conn, sn, qr, 'TMS', 'TANK_MODULE', '탱크모듈', completed=False)
        _insert_task(db_conn, sn, qr, 'TMS', 'PRESSURE_TEST', '가압검사', completed=True)

        iso_week = today.isocalendar()[1]
        token = admin_token

        resp = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        order = next(
            (o for o in data['orders'] if o['sales_order'] == f'ON-{sn}'), None
        )
        assert order is not None

        tm_proc = order['processes'].get('TM', {})
        # TM 프로세스는 sn_confirms 구조 → all_confirmable 키 사용
        all_confirmable = tm_proc.get('all_confirmable', tm_proc.get('confirmable'))
        assert all_confirmable is False, (
            f"TM all_confirmable should be False (TANK_MODULE not done), got: {tm_proc}"
        )

        _cleanup(db_conn)

    def test_tm_confirm_endpoint_success(self, client, db_conn, get_auth_token, admin_token):
        """GB-03: POST confirm TM — TANK_MODULE 완료 → 201 성공"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn, ['tm'])
        today = date.today()
        iso_week = today.isocalendar()[1]
        sn = f'{_PREFIX}GB03'
        qr = f'DOC-{sn}'

        _insert_product(db_conn, sn, qr, 'GAIA-I', f'ON-{sn}', today,
                        mech_partner='TMS', has_docking=True)
        _insert_task(db_conn, sn, qr, 'TMS', 'TANK_MODULE', '탱크모듈', completed=True)
        _insert_task(db_conn, sn, qr, 'TMS', 'PRESSURE_TEST', '가압검사', completed=False)

        token = admin_token

        resp = client.post('/api/admin/production/confirm', json={
            'sales_order': f'ON-{sn}',
            'process_type': 'TM',
            'serial_numbers': [sn],
            'confirmed_week': f'W{iso_week:02d}',
            'confirmed_month': f'{today.year}-{today.month:02d}',
        }, headers={'Authorization': f'Bearer {token}'})

        assert resp.status_code == 201, (
            f"TM confirm should succeed (TANK_MODULE done), got: {resp.status_code} {resp.get_json()}"
        )
        data = resp.get_json()
        # 응답: { confirmed: [{id, serial_number, confirmed_at}], count, message }
        assert data.get('confirmed') is not None
        assert len(data['confirmed']) >= 1
        assert data['confirmed'][0].get('id') is not None

        _cleanup(db_conn)

    def test_tm_confirm_endpoint_rejected(self, client, db_conn, get_auth_token, admin_token):
        """GB-04: POST confirm TM — TANK_MODULE 미완료 → 400 NOT_CONFIRMABLE"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn, ['tm'])
        today = date.today()
        iso_week = today.isocalendar()[1]
        sn = f'{_PREFIX}GB04'
        qr = f'DOC-{sn}'

        _insert_product(db_conn, sn, qr, 'GAIA-I', f'ON-{sn}', today,
                        mech_partner='TMS', has_docking=True)
        _insert_task(db_conn, sn, qr, 'TMS', 'TANK_MODULE', '탱크모듈', completed=False)
        _insert_task(db_conn, sn, qr, 'TMS', 'PRESSURE_TEST', '가압검사', completed=True)

        token = admin_token

        resp = client.post('/api/admin/production/confirm', json={
            'sales_order': f'ON-{sn}',
            'process_type': 'TM',
            'serial_numbers': [sn],
            'confirmed_week': f'W{iso_week:02d}',
            'confirmed_month': f'{today.year}-{today.month:02d}',
        }, headers={'Authorization': f'Bearer {token}'})

        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'NOT_CONFIRMABLE'

        _cleanup(db_conn)

    def test_tm_progress_includes_all_tasks(self, client, db_conn, get_auth_token, admin_token):
        """GB-05: TM progress pct — TANK_MODULE + PRESSURE_TEST 전체 포함"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn, ['tm'])
        today = date.today()
        sn = f'{_PREFIX}GB05'
        qr = f'DOC-{sn}'

        _insert_product(db_conn, sn, qr, 'GAIA-I', f'ON-{sn}', today,
                        mech_partner='TMS', has_docking=True)
        # 3개 task 중 2개 완료
        _insert_task(db_conn, sn, qr, 'TMS', 'TANK_MODULE', '탱크모듈', completed=True)
        _insert_task(db_conn, sn, qr, 'TMS', 'PRESSURE_TEST', '가압검사', completed=True)

        iso_week = today.isocalendar()[1]
        token = admin_token

        resp = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        order = next(
            (o for o in data['orders'] if o['sales_order'] == f'ON-{sn}'), None
        )
        assert order is not None

        tm_proc = order['processes'].get('TM', {})
        # progress는 전체 task 포함
        assert tm_proc['total'] == 2
        assert tm_proc['completed'] == 2
        assert tm_proc['pct'] == 100.0

        _cleanup(db_conn)


# ══════════════════════════════════════════════════════════════
# Regression: MECH/ELEC 기존 confirmable 동작 유지
# ══════════════════════════════════════════════════════════════

class TestRegressionMechElecConfirmable:
    """MECH/ELEC confirmable — #36 변경에 의한 사이드이펙트 없음 확인"""

    def test_mech_all_done_confirmable(self, client, db_conn, get_auth_token, admin_token):
        """REG-01: MECH 전체 완료 → confirmable=True (기존 동작 유지)"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn, ['mech'])
        today = date.today()
        sn = f'{_PREFIX}REG01'
        qr = f'DOC-{sn}'

        _insert_product(db_conn, sn, qr, 'GAIA-I', f'ON-{sn}', today)
        _insert_task(db_conn, sn, qr, 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)
        _insert_task(db_conn, sn, qr, 'MECH', 'WELDING', '용접', completed=True)

        iso_week = today.isocalendar()[1]
        token = admin_token

        resp = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        order = next(
            (o for o in data['orders'] if o['sales_order'] == f'ON-{sn}'), None
        )
        assert order is not None
        # MECH는 partner-level process → sn_confirms + all_confirmable 구조
        mech_proc = order['processes'].get('MECH', {})
        assert mech_proc.get('all_confirmable', mech_proc.get('confirmable')) is True

        _cleanup(db_conn)

    def test_mech_partial_not_confirmable(self, client, db_conn, get_auth_token, admin_token):
        """REG-02: MECH 일부 미완료 → confirmable=False (기존 동작 유지)"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn, ['mech'])
        today = date.today()
        sn = f'{_PREFIX}REG02'
        qr = f'DOC-{sn}'

        _insert_product(db_conn, sn, qr, 'GAIA-I', f'ON-{sn}', today)
        _insert_task(db_conn, sn, qr, 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)
        _insert_task(db_conn, sn, qr, 'MECH', 'WELDING', '용접', completed=False)

        iso_week = today.isocalendar()[1]
        token = admin_token

        resp = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        order = next(
            (o for o in data['orders'] if o['sales_order'] == f'ON-{sn}'), None
        )
        assert order is not None
        # MECH는 partner-level process → sn_confirms + all_confirmable 구조
        mech_proc = order['processes'].get('MECH', {})
        assert mech_proc.get('all_confirmable', mech_proc.get('confirmable')) is False

        _cleanup(db_conn)

    def test_elec_confirm_still_works(self, client, db_conn, get_auth_token, admin_token):
        """REG-03: ELEC 실적확인도 정상 동작"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn, ['elec'])
        today = date.today()
        iso_week = today.isocalendar()[1]
        sn = f'{_PREFIX}REG03'
        qr = f'DOC-{sn}'

        _insert_product(db_conn, sn, qr, 'GAIA-I', f'ON-{sn}', today)
        _insert_task(db_conn, sn, qr, 'ELEC', 'CABLE_CHECK', '배선검사', completed=True)

        token = admin_token

        resp = client.post('/api/admin/production/confirm', json={
            'sales_order': f'ON-{sn}',
            'process_type': 'ELEC',
            'serial_numbers': [sn],
            'confirmed_week': f'W{iso_week:02d}',
            'confirmed_month': f'{today.year}-{today.month:02d}',
        }, headers={'Authorization': f'Bearer {token}'})

        assert resp.status_code == 201

        _cleanup(db_conn)

    def test_multi_sn_order_tms_and_mech_independent(self, client, db_conn, get_auth_token, admin_token):
        """REG-04: 같은 O/N에서 TM confirmable과 MECH confirmable이 독립 판정"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        _enable_confirm_settings(db_conn, ['mech', 'tm'])
        today = date.today()
        sn = f'{_PREFIX}REG04'
        qr = f'DOC-{sn}'

        _insert_product(db_conn, sn, qr, 'GAIA-I', f'ON-{sn}', today,
                        mech_partner='TMS', has_docking=True)

        # MECH: 미완료, TMS: TANK_MODULE 완료
        _insert_task(db_conn, sn, qr, 'MECH', 'SELF_INSPECTION', '자주검사', completed=False)
        _insert_task(db_conn, sn, qr, 'TMS', 'TANK_MODULE', '탱크모듈', completed=True)
        _insert_task(db_conn, sn, qr, 'TMS', 'PRESSURE_TEST', '가압검사', completed=False)

        iso_week = today.isocalendar()[1]
        token = admin_token

        resp = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        order = next(
            (o for o in data['orders'] if o['sales_order'] == f'ON-{sn}'), None
        )
        assert order is not None

        # MECH: 미완료 → False (partner-level process uses all_confirmable)
        mech_proc = order['processes'].get('MECH', {})
        assert mech_proc.get('all_confirmable', mech_proc.get('confirmable')) is False
        # TM: TANK_MODULE 완료 → True (partner-level process uses all_confirmable)
        tm_proc = order['processes'].get('TM', {})
        assert tm_proc.get('all_confirmable', tm_proc.get('confirmable')) is True

        _cleanup(db_conn)
