"""
Sprint 33: 생산실적 API 테스트
- O/N 단위 그룹핑
- confirmable 판정 (완료/미완료/혼합)
- 실적확인 처리/취소/재확인
- 월마감 집계
"""

import pytest
from datetime import date, timedelta


# ── 헬퍼 함수 ──────────────────────────────────

def _insert_product(db_conn, serial_number, qr_doc_id, model, sales_order, mech_start=None):
    """테스트용 제품 + QR 등록"""
    if mech_start is None:
        mech_start = date.today()
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO plan.product_info (serial_number, model, sales_order, mech_start)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (serial_number) DO NOTHING
    """, (serial_number, model, sales_order, mech_start))
    cursor.execute("""
        INSERT INTO public.qr_registry (qr_doc_id, serial_number, status)
        VALUES (%s, %s, 'active')
        ON CONFLICT (qr_doc_id) DO NOTHING
    """, (qr_doc_id, serial_number))
    db_conn.commit()
    cursor.close()


def _insert_task(db_conn, serial_number, qr_doc_id, category, task_id, task_name, completed=False):
    """테스트용 태스크 등록"""
    cursor = db_conn.cursor()
    completed_at = 'NOW()' if completed else 'NULL'
    cursor.execute(f"""
        INSERT INTO app_task_details
            (serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable,
             completed_at)
        VALUES (%s, %s, %s, %s, %s, TRUE, {completed_at})
        ON CONFLICT (serial_number, qr_doc_id, task_category, task_id) DO NOTHING
    """, (serial_number, qr_doc_id, category, task_id, task_name))
    db_conn.commit()
    cursor.close()


def _cleanup_test_data(db_conn, prefix='SN-PROD-33'):
    """테스트 데이터 정리"""
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM plan.production_confirm WHERE sales_order LIKE %s", (f'ON-{prefix}%',))
    cursor.execute("DELETE FROM app_task_details WHERE serial_number LIKE %s", (f'{prefix}%',))
    cursor.execute("DELETE FROM completion_status WHERE serial_number LIKE %s", (f'{prefix}%',))
    cursor.execute("DELETE FROM qr_registry WHERE serial_number LIKE %s", (f'{prefix}%',))
    cursor.execute("DELETE FROM plan.product_info WHERE serial_number LIKE %s", (f'{prefix}%',))
    db_conn.commit()
    cursor.close()


# ── 테스트 클래스 ──────────────────────────────────

class TestProductionPerformance:
    """GET /api/admin/production/performance"""

    def test_weekly_groups_by_order(self, client, db_conn, get_auth_token):
        """O/N 단위 그룹핑 — 같은 O/N의 S/N이 묶여서 반환"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup_test_data(db_conn)
        today = date.today()

        # O/N 6001에 S/N 2개
        _insert_product(db_conn, 'SN-PROD-33-001', 'DOC-PROD-33-001', 'GAIA-I', 'ON-SN-PROD-33-6001', today)
        _insert_product(db_conn, 'SN-PROD-33-002', 'DOC-PROD-33-002', 'GAIA-I', 'ON-SN-PROD-33-6001', today)
        # O/N 6002에 S/N 1개
        _insert_product(db_conn, 'SN-PROD-33-003', 'DOC-PROD-33-003', 'DRAGON', 'ON-SN-PROD-33-6002', today)

        iso_week = today.isocalendar()[1]
        token = get_auth_token(819, role='ADMIN')

        resp = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        assert data['total_orders'] >= 2
        orders = {o['sales_order']: o for o in data['orders']}

        if 'ON-SN-PROD-33-6001' in orders:
            assert orders['ON-SN-PROD-33-6001']['sn_count'] == 2
        if 'ON-SN-PROD-33-6002' in orders:
            assert orders['ON-SN-PROD-33-6002']['sn_count'] == 1

        _cleanup_test_data(db_conn)

    def test_confirmable_all_complete(self, client, db_conn, get_auth_token):
        """전체 S/N 공정 완료 → confirmable=True"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup_test_data(db_conn)
        today = date.today()

        _insert_product(db_conn, 'SN-PROD-33-010', 'DOC-PROD-33-010', 'GAIA-I', 'ON-SN-PROD-33-7001', today)
        # MECH 태스크 1개 — 완료
        _insert_task(db_conn, 'SN-PROD-33-010', 'DOC-PROD-33-010', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        iso_week = today.isocalendar()[1]
        token = get_auth_token(819, role='ADMIN')

        resp = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        order = next((o for o in data['orders'] if o['sales_order'] == 'ON-SN-PROD-33-7001'), None)
        assert order is not None
        assert order['processes'].get('MECH', {}).get('confirmable') is True

        _cleanup_test_data(db_conn)

    def test_confirmable_partial_incomplete(self, client, db_conn, get_auth_token):
        """일부 S/N 미완료 → confirmable=False"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup_test_data(db_conn)
        today = date.today()

        _insert_product(db_conn, 'SN-PROD-33-020', 'DOC-PROD-33-020', 'GAIA-I', 'ON-SN-PROD-33-7002', today)
        _insert_product(db_conn, 'SN-PROD-33-021', 'DOC-PROD-33-021', 'GAIA-I', 'ON-SN-PROD-33-7002', today)
        # 020: MECH 완료, 021: MECH 미완료
        _insert_task(db_conn, 'SN-PROD-33-020', 'DOC-PROD-33-020', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)
        _insert_task(db_conn, 'SN-PROD-33-021', 'DOC-PROD-33-021', 'MECH', 'SELF_INSPECTION', '자주검사', completed=False)

        iso_week = today.isocalendar()[1]
        token = get_auth_token(819, role='ADMIN')

        resp = client.get(
            f'/api/admin/production/performance?view=weekly&week=W{iso_week:02d}&year={today.year}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        order = next((o for o in data['orders'] if o['sales_order'] == 'ON-SN-PROD-33-7002'), None)
        assert order is not None
        assert order['processes'].get('MECH', {}).get('confirmable') is False

        _cleanup_test_data(db_conn)


class TestProductionConfirm:
    """POST /api/admin/production/confirm"""

    def test_confirm_success(self, client, db_conn, get_auth_token):
        """confirmable 조건 충족 → 실적확인 성공"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup_test_data(db_conn)
        today = date.today()
        iso_week = today.isocalendar()[1]

        _insert_product(db_conn, 'SN-PROD-33-030', 'DOC-PROD-33-030', 'GAIA-I', 'ON-SN-PROD-33-8001', today)
        _insert_task(db_conn, 'SN-PROD-33-030', 'DOC-PROD-33-030', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        token = get_auth_token(819, role='ADMIN')

        resp = client.post(
            '/api/admin/production/confirm',
            json={
                'sales_order': 'ON-SN-PROD-33-8001',
                'process_type': 'MECH',
                'confirmed_week': f'W{iso_week:02d}',
                'confirmed_month': f'{today.year}-{today.month:02d}',
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data.get('confirm_id') is not None

        _cleanup_test_data(db_conn)

    def test_confirm_not_confirmable(self, client, db_conn, get_auth_token):
        """미완료 → 실적확인 거부 400"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup_test_data(db_conn)
        today = date.today()
        iso_week = today.isocalendar()[1]

        _insert_product(db_conn, 'SN-PROD-33-040', 'DOC-PROD-33-040', 'GAIA-I', 'ON-SN-PROD-33-8002', today)
        _insert_task(db_conn, 'SN-PROD-33-040', 'DOC-PROD-33-040', 'MECH', 'SELF_INSPECTION', '자주검사', completed=False)

        token = get_auth_token(819, role='ADMIN')

        resp = client.post(
            '/api/admin/production/confirm',
            json={
                'sales_order': 'ON-SN-PROD-33-8002',
                'process_type': 'MECH',
                'confirmed_week': f'W{iso_week:02d}',
                'confirmed_month': f'{today.year}-{today.month:02d}',
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'NOT_CONFIRMABLE'

        _cleanup_test_data(db_conn)

    def test_confirm_duplicate_409(self, client, db_conn, get_auth_token):
        """중복 실적확인 → 409"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup_test_data(db_conn)
        today = date.today()
        iso_week = today.isocalendar()[1]

        _insert_product(db_conn, 'SN-PROD-33-050', 'DOC-PROD-33-050', 'GAIA-I', 'ON-SN-PROD-33-8003', today)
        _insert_task(db_conn, 'SN-PROD-33-050', 'DOC-PROD-33-050', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        token = get_auth_token(819, role='ADMIN')
        body = {
            'sales_order': 'ON-SN-PROD-33-8003',
            'process_type': 'MECH',
            'confirmed_week': f'W{iso_week:02d}',
            'confirmed_month': f'{today.year}-{today.month:02d}',
        }

        # 첫 번째 확인
        resp1 = client.post('/api/admin/production/confirm', json=body, headers={'Authorization': f'Bearer {token}'})
        assert resp1.status_code == 201

        # 중복 확인
        resp2 = client.post('/api/admin/production/confirm', json=body, headers={'Authorization': f'Bearer {token}'})
        assert resp2.status_code == 409

        _cleanup_test_data(db_conn)


class TestProductionCancel:
    """DELETE /api/admin/production/confirm/:id"""

    def test_cancel_soft_delete(self, client, db_conn, get_auth_token):
        """실적확인 취소 → soft delete"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup_test_data(db_conn)
        today = date.today()
        iso_week = today.isocalendar()[1]

        _insert_product(db_conn, 'SN-PROD-33-060', 'DOC-PROD-33-060', 'GAIA-I', 'ON-SN-PROD-33-9001', today)
        _insert_task(db_conn, 'SN-PROD-33-060', 'DOC-PROD-33-060', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        token = get_auth_token(819, role='ADMIN')

        # 확인
        resp = client.post('/api/admin/production/confirm', json={
            'sales_order': 'ON-SN-PROD-33-9001',
            'process_type': 'MECH',
            'confirmed_week': f'W{iso_week:02d}',
            'confirmed_month': f'{today.year}-{today.month:02d}',
        }, headers={'Authorization': f'Bearer {token}'})
        confirm_id = resp.get_json()['confirm_id']

        # 취소
        resp2 = client.delete(
            f'/api/admin/production/confirm/{confirm_id}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp2.status_code == 200

        # DB에서 soft delete 확인
        cursor = db_conn.cursor()
        cursor.execute("SELECT deleted_at FROM plan.production_confirm WHERE id = %s", (confirm_id,))
        row = cursor.fetchone()
        assert row[0] is not None  # deleted_at
        cursor.close()

        _cleanup_test_data(db_conn)

    def test_reconfirm_after_cancel(self, client, db_conn, get_auth_token):
        """취소 후 재확인 가능"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup_test_data(db_conn)
        today = date.today()
        iso_week = today.isocalendar()[1]

        _insert_product(db_conn, 'SN-PROD-33-070', 'DOC-PROD-33-070', 'GAIA-I', 'ON-SN-PROD-33-9002', today)
        _insert_task(db_conn, 'SN-PROD-33-070', 'DOC-PROD-33-070', 'MECH', 'SELF_INSPECTION', '자주검사', completed=True)

        token = get_auth_token(819, role='ADMIN')
        body = {
            'sales_order': 'ON-SN-PROD-33-9002',
            'process_type': 'MECH',
            'confirmed_week': f'W{iso_week:02d}',
            'confirmed_month': f'{today.year}-{today.month:02d}',
        }

        # 확인 → 취소 → 재확인
        resp1 = client.post('/api/admin/production/confirm', json=body, headers={'Authorization': f'Bearer {token}'})
        confirm_id = resp1.get_json()['confirm_id']

        client.delete(f'/api/admin/production/confirm/{confirm_id}', headers={'Authorization': f'Bearer {token}'})

        resp3 = client.post('/api/admin/production/confirm', json=body, headers={'Authorization': f'Bearer {token}'})
        assert resp3.status_code == 201

        _cleanup_test_data(db_conn)


class TestMonthlySummary:
    """GET /api/admin/production/monthly-summary"""

    def test_monthly_returns_orders(self, client, db_conn, get_auth_token):
        """월마감 집계 — O/N 목록 + 실적확인 이력"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup_test_data(db_conn)
        today = date.today()
        month_str = f'{today.year}-{today.month:02d}'

        _insert_product(db_conn, 'SN-PROD-33-080', 'DOC-PROD-33-080', 'GAIA-I', 'ON-SN-PROD-33-A001', today)

        token = get_auth_token(819, role='ADMIN')

        resp = client.get(
            f'/api/admin/production/monthly-summary?month={month_str}',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['month'] == month_str
        assert data['total_orders'] >= 1

        _cleanup_test_data(db_conn)
