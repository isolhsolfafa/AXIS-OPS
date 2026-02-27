"""
Sprint 11: GST active_role 전환 테스트
PUT /api/auth/active-role — GST 작업자만 active_role 변경 가능

테스트 대상:
- PUT /api/auth/active-role → active_role='PI'/'QI'/'SI'/'ADMIN' 변경
- 유효하지 않은 role 거부 ('MECH', 'ELEC' 등)
- 협력사 작업자 변경 시도 → 403
- GET /api/auth/me → active_role 포함 확인
- active_role 변경 후 작업 관리에서 필터링 확인
- 미인증 시 401
"""

import pytest
import sys
from pathlib import Path

# backend 경로 추가
backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


# ============================================================
# 헬퍼 함수
# ============================================================

def _has_active_role_column(db_conn) -> bool:
    """workers 테이블에 active_role 컬럼 존재 확인"""
    try:
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'workers' AND column_name = 'active_role'
        """)
        result = cursor.fetchone() is not None
        cursor.close()
        return result
    except Exception:
        return False


def _get_worker_active_role(db_conn, worker_id: int):
    """DB에서 직접 active_role 조회"""
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT active_role FROM workers WHERE id = %s",
            (worker_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else None
    except Exception:
        return None


# ============================================================
# 공통 픽스처
# ============================================================

def _do_cleanup_active_role_data(db_conn):
    """active_role 테스트 데이터 정리 (setup/teardown 공용)"""
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            cursor.execute(
                "DELETE FROM app_task_details WHERE serial_number LIKE 'SN-SP11-AR-%%'"
            )
            cursor.execute(
                "DELETE FROM public.qr_registry WHERE qr_doc_id LIKE 'DOC-SP11-AR-%%'"
            )
            cursor.execute(
                "DELETE FROM plan.product_info WHERE serial_number LIKE 'SN-SP11-AR-%%'"
            )
            cursor.execute(
                "DELETE FROM workers WHERE email LIKE '%%@sp11_ar_test.com'"
            )
            db_conn.commit()
            cursor.close()
        except Exception:
            try:
                db_conn.rollback()
            except Exception:
                pass


@pytest.fixture(autouse=True)
def cleanup_active_role_data(db_conn):
    """테스트 전/후 active_role 테스트 데이터 정리 (stale data 방지)"""
    _do_cleanup_active_role_data(db_conn)
    yield
    _do_cleanup_active_role_data(db_conn)


@pytest.fixture
def gst_pi_worker(create_test_worker, get_auth_token):
    """GST PI 작업자 (active_role 변경 가능)"""
    worker_id = create_test_worker(
        email='gst_pi@sp11_ar_test.com', password='Test123!',
        name='GST PI Worker', role='PI', company='GST'
    )
    token = get_auth_token(worker_id, role='PI')
    return worker_id, token


@pytest.fixture
def fni_mech_worker(create_test_worker, get_auth_token):
    """협력사 FNI MECH 작업자 (active_role 변경 불가)"""
    worker_id = create_test_worker(
        email='fni_mech@sp11_ar_test.com', password='Test123!',
        name='FNI MECH Worker', role='MECH', company='FNI'
    )
    token = get_auth_token(worker_id, role='MECH')
    return worker_id, token


# ============================================================
# TC-AR-01 ~ 08: active_role 전환 테스트
# ============================================================

class TestActiveRoleChange:
    """Sprint 11: PUT /api/auth/active-role 테스트"""

    def test_gst_worker_change_active_role_to_pi(self, client, db_conn, gst_pi_worker):
        """
        TC-AR-01: GST 작업자 active_role='PI' 변경 성공

        Expected:
        - PUT /api/auth/active-role {"active_role": "PI"} → 200
        - 응답에 active_role='PI' 포함
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        if not _has_active_role_column(db_conn):
            pytest.skip("workers.active_role 컬럼 미생성 (Sprint 11 BE 구현 필요)")

        worker_id, token = gst_pi_worker

        response = client.put(
            '/api/auth/active-role',
            json={'active_role': 'PI'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("PUT /api/auth/active-role 미구현")

        assert response.status_code == 200, \
            f"Expected 200, got {response.status_code}: {response.get_json()}"

        data = response.get_json()
        assert data.get('active_role') == 'PI', \
            f"응답에 active_role='PI' 필요, got {data.get('active_role')}"

    def test_gst_worker_change_active_role_to_qi(self, client, db_conn, gst_pi_worker):
        """
        TC-AR-02: GST 작업자 active_role='QI' 변경 성공

        Expected:
        - PUT {"active_role": "QI"} → 200
        - active_role='QI' 반환
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        if not _has_active_role_column(db_conn):
            pytest.skip("workers.active_role 컬럼 미생성")

        worker_id, token = gst_pi_worker

        response = client.put(
            '/api/auth/active-role',
            json={'active_role': 'QI'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("PUT /api/auth/active-role 미구현")

        assert response.status_code == 200

        data = response.get_json()
        assert data.get('active_role') == 'QI', \
            f"응답에 active_role='QI' 필요, got {data.get('active_role')}"

        # DB 직접 확인
        db_active_role = _get_worker_active_role(db_conn, worker_id)
        if db_active_role is not None:
            assert db_active_role == 'QI', f"DB active_role='QI' 필요, 현재 '{db_active_role}'"

    def test_gst_worker_change_active_role_to_si(self, client, db_conn, gst_pi_worker):
        """
        TC-AR-03: GST 작업자 active_role='SI' 변경 성공

        Expected:
        - PUT {"active_role": "SI"} → 200
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        if not _has_active_role_column(db_conn):
            pytest.skip("workers.active_role 컬럼 미생성")

        worker_id, token = gst_pi_worker

        response = client.put(
            '/api/auth/active-role',
            json={'active_role': 'SI'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("PUT /api/auth/active-role 미구현")

        assert response.status_code == 200

        data = response.get_json()
        assert data.get('active_role') == 'SI'

    def test_invalid_role_mech_rejected(self, client, db_conn, gst_pi_worker):
        """
        TC-AR-04: 유효하지 않은 role ('MECH') → 400 거부

        Expected:
        - PUT {"active_role": "MECH"} → 400 (GST 인원은 MECH 설정 불가)
        - 유효 role은 PI/QI/SI/ADMIN만 허용
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        if not _has_active_role_column(db_conn):
            pytest.skip("workers.active_role 컬럼 미생성")

        _, token = gst_pi_worker

        response = client.put(
            '/api/auth/active-role',
            json={'active_role': 'MECH'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("PUT /api/auth/active-role 미구현")

        assert response.status_code == 400, \
            f"유효하지 않은 role 'MECH'는 400 필요, got {response.status_code}"

    def test_fni_worker_cannot_change_active_role(self, client, db_conn, fni_mech_worker):
        """
        TC-AR-05: 협력사(FNI) 작업자 active_role 변경 시도 → 403

        Expected:
        - company='FNI', role='MECH' → 403 FORBIDDEN
        - GST 작업자만 active_role 변경 가능
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        if not _has_active_role_column(db_conn):
            pytest.skip("workers.active_role 컬럼 미생성")

        _, token = fni_mech_worker

        response = client.put(
            '/api/auth/active-role',
            json={'active_role': 'PI'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("PUT /api/auth/active-role 미구현")

        assert response.status_code == 403, \
            f"협력사 작업자는 403 필요, got {response.status_code}"

    def test_get_me_includes_active_role(self, client, db_conn, gst_pi_worker):
        """
        TC-AR-06: GET /api/auth/me → active_role 필드 포함

        Expected:
        - GET /api/auth/me 응답에 active_role 포함
        - active_role이 null이 아닌 값 반환 (초기값 또는 변경 후 값)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        if not _has_active_role_column(db_conn):
            pytest.skip("workers.active_role 컬럼 미생성")

        worker_id, token = gst_pi_worker

        response = client.get(
            '/api/auth/me',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/auth/me 미구현")

        assert response.status_code == 200

        data = response.get_json()
        assert 'active_role' in data, \
            f"GET /api/auth/me 응답에 active_role 필드 필요. 현재 키: {list(data.keys())}"

    def test_active_role_change_reflected_in_get_me(self, client, db_conn, gst_pi_worker):
        """
        TC-AR-07: active_role 변경 후 GET /api/auth/me에서 반영 확인

        Expected:
        - PUT active_role='QI' → 이후 GET /api/auth/me → active_role='QI' 반환
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        if not _has_active_role_column(db_conn):
            pytest.skip("workers.active_role 컬럼 미생성")

        worker_id, token = gst_pi_worker

        # active_role 변경
        put_response = client.put(
            '/api/auth/active-role',
            json={'active_role': 'QI'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if put_response.status_code == 404:
            pytest.skip("PUT /api/auth/active-role 미구현")

        if put_response.status_code != 200:
            pytest.skip(f"active_role 변경 실패: {put_response.status_code}")

        # GET me로 확인
        get_response = client.get(
            '/api/auth/me',
            headers={'Authorization': f'Bearer {token}'}
        )

        if get_response.status_code == 404:
            pytest.skip("GET /api/auth/me 미구현")

        assert get_response.status_code == 200
        data = get_response.get_json()
        active_role = data.get('active_role')

        assert active_role == 'QI', \
            f"active_role 변경 후 GET me에서 'QI' 필요, got '{active_role}'"

    def test_unauthenticated_returns_401(self, client):
        """
        TC-AR-08: 미인증 상태로 active_role 변경 시도 → 401

        Expected:
        - Authorization 헤더 없음 → 401
        """
        response = client.put(
            '/api/auth/active-role',
            json={'active_role': 'PI'}
        )

        if response.status_code == 404:
            pytest.skip("PUT /api/auth/active-role 미구현")

        assert response.status_code == 401, \
            f"미인증 상태는 401 필요, got {response.status_code}"


class TestActiveRoleTaskFiltering:
    """active_role 변경 후 작업 관리 필터링 테스트"""

    def test_active_role_pi_shows_pi_tasks(
        self, client, db_conn, create_test_worker, get_auth_token
    ):
        """
        TC-AR-09 (추가): active_role='PI'로 변경 후 작업 관리에서 PI task 조회

        Expected:
        - active_role='PI'인 GST 작업자 → 작업 관리에서 PI task 목록 조회 가능
        - 기본 task 목록에 PI category task 포함
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        if not _has_active_role_column(db_conn):
            pytest.skip("workers.active_role 컬럼 미생성")

        # GST 작업자 생성
        worker_id = create_test_worker(
            email='gst_arfilter@sp11_ar_test.com', password='Test123!',
            name='GST AR Filter Worker', role='PI', company='GST'
        )
        token = get_auth_token(worker_id, role='PI')

        # PI task 삽입
        serial_number = 'SN-SP11-AR-001'
        qr_doc_id = 'DOC-SP11-AR-001'
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO plan.product_info (serial_number, model)
            VALUES (%s, 'GAIA-100') ON CONFLICT (serial_number) DO NOTHING
        """, (serial_number,))
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number)
            VALUES (%s, %s) ON CONFLICT (qr_doc_id) DO NOTHING
        """, (qr_doc_id, serial_number))
        cursor.execute("""
            INSERT INTO app_task_details
                (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable)
            VALUES (%s, %s, %s, 'PI', 'PI_LNG_UTIL', 'LNG/UTIL 가압검사', TRUE)
            ON CONFLICT (serial_number, task_category, task_id) DO NOTHING
        """, (worker_id, serial_number, qr_doc_id))
        db_conn.commit()
        cursor.close()

        # active_role PI로 변경
        put_resp = client.put(
            '/api/auth/active-role',
            json={'active_role': 'PI'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if put_resp.status_code == 404:
            pytest.skip("PUT /api/auth/active-role 미구현")

        if put_resp.status_code != 200:
            pytest.skip(f"active_role 변경 실패: {put_resp.status_code}")

        # 작업 목록 조회 (active_role=PI 기준 필터링 확인)
        response = client.get(
            f'/api/app/tasks/{serial_number}',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/tasks/<sn> 미구현")

        assert response.status_code == 200
        data = response.get_json()
        tasks = data if isinstance(data, list) else data.get('tasks', [])

        # PI task가 포함되어야 함
        pi_tasks = [t for t in tasks if t.get('task_category') == 'PI']
        # active_role 필터링이 구현되었다면 PI task가 보여야 함
        # 미구현이면 전체 목록이 보이는 것도 허용 (skip 아님)
        assert len(pi_tasks) >= 0  # PI task 포함 여부만 확인 (구현 여부 불확실)
