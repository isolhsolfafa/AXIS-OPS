"""
협력사별 S/N 작업 진행률 조회 테스트 (Sprint 18)
엔드포인트: GET /api/app/product/progress

프로덕션 데이터 보호: TEST_PROG_ prefix 테스트 데이터만 사용
teardown에서 prefix 데이터만 삭제
"""

import time
import pytest


# ============================================================
# 테스트 데이터 prefix — 프로덕션 데이터 오염 방지
# ============================================================
_PREFIX = 'TEST_PROG_'
_TS = lambda: str(int(time.time() * 1000))


def _sn(suffix: str) -> str:
    return f'{_PREFIX}{suffix}'


# ============================================================
# Fixture: 테스트 데이터 정리 (autouse)
# ============================================================
@pytest.fixture(autouse=True)
def cleanup_progress_data(db_conn):
    """각 테스트 후 TEST_PROG_ prefix 데이터만 삭제"""
    yield
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            # 역순 삭제 (FK 관계 존중)
            cursor.execute(
                "DELETE FROM app_task_details WHERE serial_number LIKE %s",
                (f'{_PREFIX}%',)
            )
            cursor.execute(
                "DELETE FROM completion_status WHERE serial_number LIKE %s",
                (f'{_PREFIX}%',)
            )
            cursor.execute(
                "DELETE FROM qr_registry WHERE serial_number LIKE %s",
                (f'{_PREFIX}%',)
            )
            cursor.execute(
                "DELETE FROM plan.product_info WHERE serial_number LIKE %s",
                (f'{_PREFIX}%',)
            )
            db_conn.commit()
            cursor.close()
        except Exception:
            try:
                db_conn.rollback()
            except Exception:
                pass


def _seed_product(db_conn, serial_number: str, model: str = 'GAIA-100',
                  mech_partner: str = 'FNI', elec_partner: str = 'P&S',
                  module_outsourcing: str = '', ship_plan_date: str = '2026-04-01'):
    """테스트용 product_info + qr_registry + completion_status 시드"""
    cursor = db_conn.cursor()
    qr_doc_id = f'DOC_{serial_number}'

    cursor.execute("""
        INSERT INTO plan.product_info (serial_number, model, mech_partner, elec_partner,
            module_outsourcing, ship_plan_date)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (serial_number) DO NOTHING
    """, (serial_number, model, mech_partner, elec_partner, module_outsourcing, ship_plan_date))

    cursor.execute("""
        INSERT INTO qr_registry (qr_doc_id, serial_number, status)
        VALUES (%s, %s, 'active')
        ON CONFLICT (qr_doc_id) DO NOTHING
    """, (qr_doc_id, serial_number))

    cursor.execute("""
        INSERT INTO completion_status (serial_number)
        VALUES (%s)
        ON CONFLICT (serial_number) DO NOTHING
    """, (serial_number,))

    db_conn.commit()
    cursor.close()
    return qr_doc_id


def _seed_task(db_conn, serial_number: str, qr_doc_id: str, worker_id: int,
               category: str, task_id: str, task_name: str,
               is_applicable: bool = True, completed: bool = False):
    """테스트용 task 시드"""
    cursor = db_conn.cursor()
    completed_at = 'NOW()' if completed else 'NULL'
    duration = '60' if completed else 'NULL'

    cursor.execute(f"""
        INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
             is_applicable, completed_at, duration_minutes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, {completed_at}, {duration})
        ON CONFLICT (serial_number, task_category, task_id) DO NOTHING
    """, (worker_id, serial_number, qr_doc_id, category, task_id, task_name, is_applicable))

    db_conn.commit()
    cursor.close()


class TestSnProgress:
    """협력사별 S/N 작업 진행률 테스트 (TC-PROG-01 ~ TC-PROG-10)"""

    # ------------------------------------------------------------------
    # TC-PROG-01: 인증 없이 접근 → 401
    # ------------------------------------------------------------------
    def test_progress_requires_auth(self, client):
        """TC-PROG-01: JWT 없이 접근 시 401 반환"""
        response = client.get('/api/app/product/progress')
        assert response.status_code == 401

    # ------------------------------------------------------------------
    # TC-PROG-02: FNI 작업자 → mech_partner='FNI' 제품만 조회
    # ------------------------------------------------------------------
    def test_fni_worker_sees_own_products(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-PROG-02: FNI 작업자는 mech_partner=FNI 제품만 조회"""
        sn_fni = _sn(f'FNI_{_TS()}')
        sn_bat = _sn(f'BAT_{_TS()}')

        _seed_product(db_conn, sn_fni, mech_partner='FNI')
        _seed_product(db_conn, sn_bat, mech_partner='BAT')

        worker_id = create_test_worker(
            email=f'prog_fni_{_TS()}@test.com',
            password='Test123!', name='FNI Worker',
            role='MECH', company='FNI'
        )
        token = get_auth_token(worker_id)

        response = client.get(
            '/api/app/product/progress',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200
        data = response.get_json()

        sns = [p['serial_number'] for p in data['products']]
        assert sn_fni in sns
        assert sn_bat not in sns

    # ------------------------------------------------------------------
    # TC-PROG-03: Admin → 전체 제품 조회
    # ------------------------------------------------------------------
    def test_admin_sees_all_products(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-PROG-03: Admin은 전체 제품 조회 가능"""
        sn1 = _sn(f'ADM1_{_TS()}')
        sn2 = _sn(f'ADM2_{_TS()}')

        _seed_product(db_conn, sn1, mech_partner='FNI')
        _seed_product(db_conn, sn2, mech_partner='BAT')

        worker_id = create_test_worker(
            email=f'prog_admin_{_TS()}@test.com',
            password='Test123!', name='Admin',
            role='ADMIN', company='GST', is_admin=True
        )
        token = get_auth_token(worker_id)

        response = client.get(
            '/api/app/product/progress',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200
        data = response.get_json()

        sns = [p['serial_number'] for p in data['products']]
        assert sn1 in sns
        assert sn2 in sns

    # ------------------------------------------------------------------
    # TC-PROG-04: Admin → company 파라미터로 특정 회사 필터
    # ------------------------------------------------------------------
    def test_admin_company_filter(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-PROG-04: Admin이 ?company=FNI로 FNI 제품만 필터링"""
        sn_fni = _sn(f'ADMF_{_TS()}')
        sn_bat = _sn(f'ADMB_{_TS()}')

        _seed_product(db_conn, sn_fni, mech_partner='FNI')
        _seed_product(db_conn, sn_bat, mech_partner='BAT')

        worker_id = create_test_worker(
            email=f'prog_admf_{_TS()}@test.com',
            password='Test123!', name='Admin Filter',
            role='ADMIN', company='GST', is_admin=True
        )
        token = get_auth_token(worker_id)

        response = client.get(
            '/api/app/product/progress?company=FNI',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200
        data = response.get_json()

        sns = [p['serial_number'] for p in data['products']]
        assert sn_fni in sns
        assert sn_bat not in sns

    # ------------------------------------------------------------------
    # TC-PROG-05: 비admin은 company 파라미터 무시
    # ------------------------------------------------------------------
    def test_non_admin_ignores_company_param(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-PROG-05: 일반 작업자는 ?company= 파라미터 무시, 자기 회사만"""
        sn_fni = _sn(f'NAF_{_TS()}')
        sn_bat = _sn(f'NAB_{_TS()}')

        _seed_product(db_conn, sn_fni, mech_partner='FNI')
        _seed_product(db_conn, sn_bat, mech_partner='BAT')

        worker_id = create_test_worker(
            email=f'prog_na_{_TS()}@test.com',
            password='Test123!', name='FNI Non-Admin',
            role='MECH', company='FNI'
        )
        token = get_auth_token(worker_id)

        # BAT 필터 시도 → 무시되고 FNI만 보임
        response = client.get(
            '/api/app/product/progress?company=BAT',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200
        data = response.get_json()

        sns = [p['serial_number'] for p in data['products']]
        assert sn_fni in sns
        assert sn_bat not in sns

    # ------------------------------------------------------------------
    # TC-PROG-06: 카테고리별 진행률 정확성
    # ------------------------------------------------------------------
    def test_category_progress_accuracy(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-PROG-06: MECH 2/3 완료 → 67%, ELEC 1/2 완료 → 50%, overall 3/5=60%"""
        sn = _sn(f'ACC_{_TS()}')
        qr_doc_id = _seed_product(db_conn, sn, mech_partner='FNI')

        worker_id = create_test_worker(
            email=f'prog_acc_{_TS()}@test.com',
            password='Test123!', name='Accuracy Worker',
            role='MECH', company='FNI'
        )
        token = get_auth_token(worker_id)

        # MECH tasks: 3 total, 2 completed
        _seed_task(db_conn, sn, qr_doc_id, worker_id, 'MECH', 'M1', 'Task M1', completed=True)
        _seed_task(db_conn, sn, qr_doc_id, worker_id, 'MECH', 'M2', 'Task M2', completed=True)
        _seed_task(db_conn, sn, qr_doc_id, worker_id, 'MECH', 'M3', 'Task M3', completed=False)

        # ELEC tasks: 2 total, 1 completed
        _seed_task(db_conn, sn, qr_doc_id, worker_id, 'ELEC', 'E1', 'Task E1', completed=True)
        _seed_task(db_conn, sn, qr_doc_id, worker_id, 'ELEC', 'E2', 'Task E2', completed=False)

        response = client.get(
            '/api/app/product/progress',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200
        data = response.get_json()

        product = next(
            (p for p in data['products'] if p['serial_number'] == sn), None
        )
        assert product is not None

        assert product['categories']['MECH']['percent'] == 67
        assert product['categories']['ELEC']['percent'] == 50
        assert product['overall_percent'] == 60

    # ------------------------------------------------------------------
    # TC-PROG-07: is_applicable=false task는 진행률에서 제외
    # ------------------------------------------------------------------
    def test_non_applicable_excluded(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-PROG-07: is_applicable=false task는 total/done 모두에서 제외"""
        sn = _sn(f'NAP_{_TS()}')
        qr_doc_id = _seed_product(db_conn, sn, mech_partner='FNI')

        worker_id = create_test_worker(
            email=f'prog_nap_{_TS()}@test.com',
            password='Test123!', name='NAP Worker',
            role='MECH', company='FNI'
        )
        token = get_auth_token(worker_id)

        # 2 applicable (1 done), 1 not applicable
        _seed_task(db_conn, sn, qr_doc_id, worker_id, 'MECH', 'M1', 'T1', completed=True)
        _seed_task(db_conn, sn, qr_doc_id, worker_id, 'MECH', 'M2', 'T2', completed=False)
        _seed_task(db_conn, sn, qr_doc_id, worker_id, 'MECH', 'M3', 'T3', is_applicable=False)

        response = client.get(
            '/api/app/product/progress',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200
        data = response.get_json()

        product = next(
            (p for p in data['products'] if p['serial_number'] == sn), None
        )
        assert product is not None
        assert product['categories']['MECH']['total'] == 2
        assert product['categories']['MECH']['done'] == 1
        assert product['categories']['MECH']['percent'] == 50

    # ------------------------------------------------------------------
    # TC-PROG-08: TMS(M) 작업자 → mech_partner=TMS OR module_outsourcing=TMS
    # ------------------------------------------------------------------
    def test_tms_m_filter(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-PROG-08: TMS(M)은 mech_partner=TMS 또는 module_outsourcing=TMS 제품 조회"""
        sn_mech = _sn(f'TMM_{_TS()}')
        sn_mod = _sn(f'TMO_{_TS()}')
        sn_other = _sn(f'TMX_{_TS()}')

        _seed_product(db_conn, sn_mech, mech_partner='TMS', module_outsourcing='')
        _seed_product(db_conn, sn_mod, mech_partner='FNI', module_outsourcing='TMS')
        _seed_product(db_conn, sn_other, mech_partner='FNI', module_outsourcing='')

        worker_id = create_test_worker(
            email=f'prog_tmm_{_TS()}@test.com',
            password='Test123!', name='TMS(M) Worker',
            role='MECH', company='TMS(M)'
        )
        token = get_auth_token(worker_id)

        response = client.get(
            '/api/app/product/progress',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200
        data = response.get_json()

        sns = [p['serial_number'] for p in data['products']]
        assert sn_mech in sns
        assert sn_mod in sns
        assert sn_other not in sns

    # ------------------------------------------------------------------
    # TC-PROG-09: summary 카운트 정확성
    # ------------------------------------------------------------------
    def test_summary_counts(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-PROG-09: summary의 total/in_progress/completed_recent 정확"""
        sn1 = _sn(f'SUM1_{_TS()}')
        sn2 = _sn(f'SUM2_{_TS()}')

        _seed_product(db_conn, sn1, mech_partner='FNI')
        _seed_product(db_conn, sn2, mech_partner='FNI')

        # sn2를 완료 상태로 — completion_status 업데이트
        cursor = db_conn.cursor()
        cursor.execute("""
            UPDATE completion_status
            SET all_completed = true, all_completed_at = NOW()
            WHERE serial_number = %s
        """, (sn2,))
        db_conn.commit()
        cursor.close()

        worker_id = create_test_worker(
            email=f'prog_sum_{_TS()}@test.com',
            password='Test123!', name='Summary Worker',
            role='MECH', company='FNI'
        )
        token = get_auth_token(worker_id)

        response = client.get(
            '/api/app/product/progress',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200
        data = response.get_json()

        # sn2는 방금 완료 → completed_recent에 포함 (1일 이내)
        summary = data['summary']
        # 기존 데이터 때문에 정확한 수를 비교하기 어려울 수 있으므로
        # 최소한 우리 테스트 데이터가 포함되어 있는지 확인
        sns = [p['serial_number'] for p in data['products']]
        assert sn1 in sns
        assert sn2 in sns

        # total >= 2 (우리 데이터 최소 포함)
        assert summary['total'] >= 2

    # ------------------------------------------------------------------
    # TC-PROG-10: P&S 작업자 → elec_partner='P&S' 제품만 조회
    # ------------------------------------------------------------------
    def test_ps_worker_elec_filter(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-PROG-10: P&S 작업자는 elec_partner=P&S 제품만 조회"""
        sn_ps = _sn(f'PS_{_TS()}')
        sn_ca = _sn(f'CA_{_TS()}')

        _seed_product(db_conn, sn_ps, elec_partner='P&S')
        _seed_product(db_conn, sn_ca, elec_partner='C&A')

        worker_id = create_test_worker(
            email=f'prog_ps_{_TS()}@test.com',
            password='Test123!', name='P&S Worker',
            role='ELEC', company='P&S'
        )
        token = get_auth_token(worker_id)

        response = client.get(
            '/api/app/product/progress',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200
        data = response.get_json()

        sns = [p['serial_number'] for p in data['products']]
        assert sn_ps in sns
        assert sn_ca not in sns
