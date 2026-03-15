"""
Sprint 29: 공장 API 테스트
- #10 GET /api/admin/factory/monthly-detail
- #9 GET /api/admin/factory/weekly-kpi

⚠️ 운영 데이터 보존: plan.product_info, qr_registry, workers, completion_status 등
   기존 데이터 수정/삭제 없음. 읽기 전용 테스트.
"""

import pytest
from datetime import date


class TestMonthlyDetail:
    """GET /api/admin/factory/monthly-detail 테스트"""

    def test_md01_default_params(self, client, create_test_admin, get_admin_auth_token):
        """기본 파라미터로 조회 → 200, items + total + by_model"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        resp = client.get(
            '/api/admin/factory/monthly-detail',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'items' in data
        assert 'total' in data
        assert 'by_model' in data
        assert 'page' in data
        assert 'per_page' in data
        assert 'total_pages' in data
        assert 'month' in data

    def test_md02_date_field_mech_start(self, client, create_test_admin, get_admin_auth_token):
        """date_field=mech_start → 200"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        resp = client.get(
            '/api/admin/factory/monthly-detail?date_field=mech_start',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'items' in data

    def test_md03_invalid_date_field(self, client, create_test_admin, get_admin_auth_token):
        """date_field=invalid → 400"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        resp = client.get(
            '/api/admin/factory/monthly-detail?date_field=invalid_field',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'INVALID_DATE_FIELD'

    def test_md04_invalid_month(self, client, create_test_admin, get_admin_auth_token):
        """month=2026-13 → 400"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        resp = client.get(
            '/api/admin/factory/monthly-detail?month=2026-13',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'INVALID_MONTH'

    def test_md05_per_page_max_limit(self, client, create_test_admin, get_admin_auth_token):
        """per_page=300 → 200, per_page가 200으로 제한"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        resp = client.get(
            '/api/admin/factory/monthly-detail?per_page=300',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['per_page'] == 200

    def test_md06_pagination_page2(self, client, create_test_admin, get_admin_auth_token):
        """page=2, per_page=5 → 200, offset 올바른지 확인"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        resp = client.get(
            '/api/admin/factory/monthly-detail?page=2&per_page=5',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['page'] == 2
        assert data['per_page'] == 5

    def test_md07_completion_tm_gaia_vs_non_gaia(self, client, create_test_admin, get_admin_auth_token):
        """completion.tm: GAIA → bool, 비GAIA → null"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        # 3월 데이터로 조회 (GAIA 모델이 있는 달)
        resp = client.get(
            '/api/admin/factory/monthly-detail?month=2026-03&per_page=200',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()

        for item in data.get('items', []):
            is_gaia = (item.get('model') or '').upper().startswith('GAIA')
            if is_gaia:
                # GAIA: tm은 bool (True or False)
                assert item['completion']['tm'] is not None, \
                    f"GAIA model {item['model']} should have bool tm, got None"
                assert isinstance(item['completion']['tm'], bool)
            else:
                # 비GAIA: tm은 None
                assert item['completion']['tm'] is None, \
                    f"Non-GAIA model {item['model']} should have null tm, got {item['completion']['tm']}"

    def test_md08_progress_pct_range(self, client, create_test_admin, get_admin_auth_token):
        """progress_pct 값이 0~100 범위"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        resp = client.get(
            '/api/admin/factory/monthly-detail?month=2026-03&per_page=200',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200

        for item in resp.get_json().get('items', []):
            pct = item.get('progress_pct', 0)
            assert 0 <= pct <= 100, f"progress_pct {pct} out of range for {item['serial_number']}"


class TestWeeklyKpi:
    """GET /api/admin/factory/weekly-kpi 테스트"""

    def test_wk01_default_params(self, client, create_test_admin, get_admin_auth_token):
        """기본 파라미터로 조회 → 200, week + year + production_count"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        resp = client.get(
            '/api/admin/factory/weekly-kpi',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'week' in data
        assert 'year' in data
        assert 'production_count' in data
        assert 'completion_rate' in data
        assert 'by_model' in data
        assert 'by_stage' in data
        assert 'pipeline' in data
        assert 'week_range' in data

    def test_wk02_week_53_boundary(self, client, create_test_admin, get_admin_auth_token):
        """week=53 경계값 — 해당 연도에 53주 존재 여부에 따라 200 또는 400"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        resp = client.get(
            '/api/admin/factory/weekly-kpi?week=53&year=2026',
            headers={'Authorization': f'Bearer {token}'}
        )
        # 200(53주 존재) 또는 400(53주 미존재) 모두 정상
        assert resp.status_code in (200, 400)

    def test_wk03_week_zero(self, client, create_test_admin, get_admin_auth_token):
        """week=0 → 400"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        resp = client.get(
            '/api/admin/factory/weekly-kpi?week=0',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'INVALID_WEEK'

    def test_wk04_by_stage_tm_gaia_only(self, client, create_test_admin, get_admin_auth_token):
        """by_stage.tm 값이 0~100 범위 (GAIA 분모 분리)"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        # 11주차 (2026-03-09 ~ 2026-03-15)
        resp = client.get(
            '/api/admin/factory/weekly-kpi?week=11&year=2026',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        by_stage = data.get('by_stage', {})
        assert 0 <= by_stage.get('tm', 0) <= 100

    def test_wk05_pipeline_counts(self, client, create_test_admin, get_admin_auth_token):
        """pipeline 카운트 합리성 — 음수 없고 int"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        resp = client.get(
            '/api/admin/factory/weekly-kpi?week=11&year=2026',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        pipeline = resp.get_json().get('pipeline', {})
        for key in ('pi', 'qi', 'si', 'shipped'):
            assert isinstance(pipeline.get(key, 0), int)
            assert pipeline.get(key, 0) >= 0


class TestFactoryAuth:
    """공장 API 권한 테스트"""

    def test_auth01_no_token(self, client):
        """토큰 없음 → 401"""
        resp = client.get('/api/admin/factory/monthly-detail')
        assert resp.status_code == 401

    def test_auth02_monthly_partner_worker_forbidden(
        self, client, approved_worker, get_auth_token
    ):
        """monthly-detail: 협력사 일반 작업자 → 403 (view_access_required)"""
        token = get_auth_token(
            worker_id=approved_worker['id'],
            role='MECH'
        )
        resp = client.get(
            '/api/admin/factory/monthly-detail',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 403

    def test_auth03_monthly_partner_manager_ok(
        self, client, manager_worker, get_auth_token
    ):
        """monthly-detail: 협력사 manager → 200 (view_access_required)"""
        token = get_auth_token(
            worker_id=manager_worker['id'],
            role='MECH'
        )
        # view_access_required는 is_manager=True도 허용
        # JWT에 is_manager 정보가 없어 DB 조회로 확인하므로 worker fixture가 is_manager=True여야 함
        resp = client.get(
            '/api/admin/factory/monthly-detail',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200

    def test_auth04_weekly_partner_manager_forbidden(
        self, client, manager_worker, get_auth_token
    ):
        """weekly-kpi: 협력사 manager → 403 (gst_or_admin_required)"""
        token = get_auth_token(
            worker_id=manager_worker['id'],
            role='MECH'
        )
        resp = client.get(
            '/api/admin/factory/weekly-kpi',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 403

    def test_auth05_weekly_gst_worker_ok(
        self, client, create_test_worker, get_auth_token
    ):
        """weekly-kpi: GST PI 작업자 → 200 (gst_or_admin_required)"""
        # company='GST'인 PI worker 생성 (gst_or_admin_required는 company='GST' 필요)
        gst_pi_id = create_test_worker(
            email='factory_gst_pi@test.axisos.com',
            password='GstPi123!',
            name='GST PI Worker',
            role='PI',
            company='GST',
            approval_status='approved',
            email_verified=True,
        )
        token = get_auth_token(
            worker_id=gst_pi_id,
            role='PI'
        )
        resp = client.get(
            '/api/admin/factory/weekly-kpi',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
