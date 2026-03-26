"""
Sprint 38: last_worker / last_activity_at 필드 추가
Gray-box 테스트 3건 (TC-LG-01 ~ TC-LG-03)

GET /api/app/product/progress 엔드포인트를 통해
products[] 배열에 last_worker / last_activity_at 필드가
올바르게 포함되는지 HTTP 레벨에서 검증한다.
"""

import sys
from pathlib import Path

_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest
from datetime import datetime, timedelta, timezone

_PREFIX = 'SP38-GB-'


# ── Admin 토큰 픽스처 ────────────────────────────────────────────

@pytest.fixture
def admin_token(db_conn, seed_test_data, get_auth_token):
    """Seed admin의 실제 worker_id로 JWT 토큰 생성"""
    cursor = db_conn.cursor()
    cursor.execute("SELECT id FROM workers WHERE email = 'seed_admin@test.axisos.com'")
    row = cursor.fetchone()
    cursor.close()
    return get_auth_token(row[0], role='ADMIN', is_admin=True)


# ── 공통 헬퍼 ────────────────────────────────────────────────────

def _insert_product(db_conn, serial_number, mech_partner='FNI'):
    """plan.product_info + qr_registry + completion_status 삽입"""
    qr_doc_id = f'DOC_{serial_number}'
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO plan.product_info (serial_number, model, mech_partner, elec_partner, ship_plan_date)
        VALUES (%s, 'GALLANT-50', %s, 'P&S', '2099-12-31')
        ON CONFLICT (serial_number) DO NOTHING
    """, (serial_number, mech_partner))
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


def _insert_task_detail(db_conn, serial_number, qr_doc_id, worker_id):
    """app_task_details 삽입 → task_detail_id 반환"""
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable)
        VALUES (%s, %s, %s, 'MECH', 'SELF_INSPECTION', '자주검사', true)
        ON CONFLICT (serial_number, qr_doc_id, task_category, task_id)
            DO UPDATE SET worker_id = EXCLUDED.worker_id
        RETURNING id
    """, (worker_id, serial_number, qr_doc_id))
    task_detail_id = cursor.fetchone()[0]
    db_conn.commit()
    cursor.close()
    return task_detail_id


def _insert_completion_log(db_conn, task_detail_id, worker_id, serial_number, qr_doc_id):
    """work_completion_log 삽입"""
    completed_at = datetime.now(timezone.utc) - timedelta(minutes=30)
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO work_completion_log
            (task_id, worker_id, serial_number, qr_doc_id, task_category,
             task_id_ref, task_name, completed_at, duration_minutes)
        VALUES (%s, %s, %s, %s, 'MECH', 'SELF_INSPECTION', '자주검사', %s, 60)
    """, (task_detail_id, worker_id, serial_number, qr_doc_id, completed_at))
    db_conn.commit()
    cursor.close()


def _cleanup(db_conn, prefix=_PREFIX):
    """테스트 데이터 정리"""
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM work_start_log WHERE serial_number LIKE %s", (f'{prefix}%',))
    cursor.execute("DELETE FROM work_completion_log WHERE serial_number LIKE %s", (f'{prefix}%',))
    cursor.execute("DELETE FROM app_task_details WHERE serial_number LIKE %s", (f'{prefix}%',))
    cursor.execute("DELETE FROM completion_status WHERE serial_number LIKE %s", (f'{prefix}%',))
    cursor.execute("DELETE FROM qr_registry WHERE serial_number LIKE %s", (f'{prefix}%',))
    cursor.execute("DELETE FROM plan.product_info WHERE serial_number LIKE %s", (f'{prefix}%',))
    db_conn.commit()
    cursor.close()


def _find_product(data, serial_number):
    """응답 JSON의 products 배열에서 S/N으로 검색"""
    for p in data.get('products', []):
        if p['serial_number'] == serial_number:
            return p
    return None


# ── 테스트 클래스 ──────────────────────────────────────────────

class TestLastActivityGraybox:
    """TC-LG-01 ~ TC-LG-03: GET /api/app/product/progress 응답 필드 검증"""

    def test_tc_lg_01_response_has_last_worker_field(
        self, client, db_conn, admin_token
    ):
        """TC-LG-01: GET /api/app/product/progress → products[].last_worker 필드 존재 확인"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        sn = f'{_PREFIX}LG01-001'
        _insert_product(db_conn, sn)

        resp = client.get(
            '/api/app/product/progress',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert resp.status_code == 200
        data = resp.get_json()

        assert 'products' in data, "응답에 products 키가 없음"
        product = _find_product(data, sn)
        assert product is not None, f"S/N {sn}이 응답에 없음"

        # last_worker, last_activity_at 필드 존재 확인 (값은 null이어도 키는 있어야 함)
        assert 'last_worker' in product, "last_worker 필드가 응답에 없음"
        assert 'last_activity_at' in product, "last_activity_at 필드가 응답에 없음"

        _cleanup(db_conn)

    def test_tc_lg_02_tagged_sn_has_non_null_last_worker(
        self, client, db_conn, admin_token, create_test_worker
    ):
        """TC-LG-02: GET /api/app/product/progress → 태깅된 S/N의 last_worker가 null이 아님"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        sn = f'{_PREFIX}LG02-001'
        qr = _insert_product(db_conn, sn)

        worker_id = create_test_worker(
            email='sp38_lg02@test.axisos.com',
            password='Test123!', name='LG02 Tagged Worker',
            role='MECH', company='FNI'
        )
        task_id = _insert_task_detail(db_conn, sn, qr, worker_id)
        _insert_completion_log(db_conn, task_id, worker_id, sn, qr)

        resp = client.get(
            '/api/app/product/progress',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert resp.status_code == 200
        data = resp.get_json()
        product = _find_product(data, sn)

        assert product is not None, f"S/N {sn}이 응답에 없음"
        assert product['last_worker'] is not None, "태깅된 S/N의 last_worker가 null임"
        assert product['last_worker'] == 'LG02 Tagged Worker'
        assert product['last_activity_at'] is not None

        _cleanup(db_conn)

    def test_tc_lg_03_untagged_sn_has_null_last_worker(
        self, client, db_conn, admin_token
    ):
        """TC-LG-03: GET /api/app/product/progress → 태깅 안 된 S/N의 last_worker가 null"""
        if not db_conn:
            pytest.skip("DB 연결 없음")

        _cleanup(db_conn)
        sn = f'{_PREFIX}LG03-001'
        _insert_product(db_conn, sn)
        # 작업 로그 없음

        resp = client.get(
            '/api/app/product/progress',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        assert resp.status_code == 200
        data = resp.get_json()
        product = _find_product(data, sn)

        assert product is not None, f"S/N {sn}이 응답에 없음"
        assert product['last_worker'] is None, "태깅 없는 S/N의 last_worker가 null이 아님"
        assert product['last_activity_at'] is None

        _cleanup(db_conn)
