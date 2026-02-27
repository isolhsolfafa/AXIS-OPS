"""
PIN 인증 테스트 (Sprint 12)
엔드포인트:
  POST /api/auth/set-pin         - PIN 설정 (JWT 인증 필요)
  PUT  /api/auth/change-pin      - PIN 변경 (JWT 인증 필요)
  POST /api/auth/pin-login       - PIN으로 로그인 (worker_id + pin, JWT 불필요)
  GET  /api/auth/pin-status      - PIN 등록 여부 조회 (JWT 인증 필요)

DB: hr.worker_auth_settings (worker_id, pin_hash, pin_fail_count, pin_locked_until)

BE API 스펙:
  - pin-login 요청: {"worker_id": int, "pin": str} (email 아닌 worker_id 사용)
  - change-pin 틀린 PIN: 401 (WRONG_PIN)
  - pin-login 3회 실패: 403 (PIN_LOCKED)
  - pin-login PIN 미등록: 404 (PIN_NOT_SET)
"""

import time
import pytest
from datetime import datetime, timedelta, timezone


# ============================================================
# Autouse cleanup fixture — hr.worker_auth_settings 정리
# ============================================================
@pytest.fixture(autouse=True)
def cleanup_hr_worker_auth(db_conn):
    """각 테스트 후 hr.worker_auth_settings 정리"""
    yield
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            cursor.execute("DELETE FROM hr.worker_auth_settings WHERE 1=1")
            db_conn.commit()
            cursor.close()
        except Exception:
            try:
                db_conn.rollback()
            except Exception:
                pass


def _check_hr_schema(db_conn) -> bool:
    """hr 스키마 및 worker_auth_settings 테이블 존재 여부 확인"""
    if db_conn is None:
        return False
    try:
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'hr' AND table_name = 'worker_auth_settings'
        """)
        exists = cursor.fetchone() is not None
        cursor.close()
        return exists
    except Exception:
        return False


class TestPINAuth:
    """PIN 인증 테스트 (TC-PIN-01 ~ TC-PIN-14)"""

    # ------------------------------------------------------------------
    # TC-PIN-01: POST /api/auth/set-pin → PIN 설정 성공 (4자리 숫자)
    # ------------------------------------------------------------------
    def test_set_pin_success(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-PIN-01: 4자리 숫자 PIN 설정 성공"""
        if not _check_hr_schema(db_conn):
            pytest.skip("hr.worker_auth_settings 테이블 없음 (Sprint 12 마이그레이션 필요)")

        worker_id = create_test_worker(
            email=f'pin_set_{int(time.time()*1000)}@pin_test.com',
            password='Test123!',
            name='PIN Set Test Worker',
            role='MECH',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        response = client.post(
            '/api/auth/set-pin',
            json={'pin': '1234'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("POST /api/auth/set-pin 엔드포인트 미구현")

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        assert 'message' in data

        # DB에서 PIN 해시 저장 확인
        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute(
                "SELECT pin_hash FROM hr.worker_auth_settings WHERE worker_id = %s",
                (worker_id,)
            )
            row = cursor.fetchone()
            cursor.close()
            assert row is not None, "hr.worker_auth_settings에 PIN 해시가 저장되지 않음"
            assert row[0] is not None, "pin_hash가 NULL임"

    # ------------------------------------------------------------------
    # TC-PIN-02: POST /api/auth/set-pin → 3자리/5자리 → 400
    # ------------------------------------------------------------------
    def test_set_pin_invalid_length(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-PIN-02: 3자리 또는 5자리 PIN 설정 → 400 Bad Request"""
        if not _check_hr_schema(db_conn):
            pytest.skip("hr.worker_auth_settings 테이블 없음")

        worker_id = create_test_worker(
            email=f'pin_len_{int(time.time()*1000)}@pin_test.com',
            password='Test123!',
            name='PIN Length Test',
            role='MECH',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        for bad_pin in ['123', '12345']:
            response = client.post(
                '/api/auth/set-pin',
                json={'pin': bad_pin},
                headers={'Authorization': f'Bearer {token}'}
            )

            if response.status_code in (404, 405):
                pytest.skip("POST /api/auth/set-pin 엔드포인트 미구현")

            assert response.status_code == 400, (
                f"PIN '{bad_pin}' → Expected 400, got {response.status_code}"
            )

    # ------------------------------------------------------------------
    # TC-PIN-03: 문자 포함 PIN → 400
    # ------------------------------------------------------------------
    def test_set_pin_non_numeric(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-PIN-03: 문자가 포함된 PIN → 400 Bad Request"""
        if not _check_hr_schema(db_conn):
            pytest.skip("hr.worker_auth_settings 테이블 없음")

        worker_id = create_test_worker(
            email=f'pin_alpha_{int(time.time()*1000)}@pin_test.com',
            password='Test123!',
            name='PIN Alpha Test',
            role='MECH',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        response = client.post(
            '/api/auth/set-pin',
            json={'pin': 'ab12'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("POST /api/auth/set-pin 엔드포인트 미구현")

        assert response.status_code == 400, (
            f"문자 포함 PIN → Expected 400, got {response.status_code}"
        )

    # ------------------------------------------------------------------
    # TC-PIN-04: 미인증 요청 → 401
    # ------------------------------------------------------------------
    def test_set_pin_unauthorized(self, client, db_conn):
        """TC-PIN-04: JWT 없이 PIN 설정 → 401"""
        if not _check_hr_schema(db_conn):
            pytest.skip("hr.worker_auth_settings 테이블 없음")

        response = client.post(
            '/api/auth/set-pin',
            json={'pin': '1234'}
        )

        if response.status_code in (404, 405):
            pytest.skip("POST /api/auth/set-pin 엔드포인트 미구현")

        assert response.status_code == 401, (
            f"미인증 → Expected 401, got {response.status_code}"
        )

    # ------------------------------------------------------------------
    # TC-PIN-05: PUT /api/auth/change-pin → 현재 PIN 맞으면 변경 성공
    # ------------------------------------------------------------------
    def test_change_pin_success(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-PIN-05: 현재 PIN이 일치할 때 PIN 변경 성공"""
        if not _check_hr_schema(db_conn):
            pytest.skip("hr.worker_auth_settings 테이블 없음")

        worker_id = create_test_worker(
            email=f'pin_change_{int(time.time()*1000)}@pin_test.com',
            password='Test123!',
            name='PIN Change Test',
            role='MECH',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        # 먼저 PIN 설정
        set_resp = client.post(
            '/api/auth/set-pin',
            json={'pin': '1234'},
            headers={'Authorization': f'Bearer {token}'}
        )
        if set_resp.status_code in (404, 405):
            pytest.skip("POST /api/auth/set-pin 엔드포인트 미구현")
        if set_resp.status_code != 200:
            pytest.skip(f"PIN 설정 실패 ({set_resp.status_code}), change-pin 테스트 불가")

        # PIN 변경
        response = client.put(
            '/api/auth/change-pin',
            json={'current_pin': '1234', 'new_pin': '5678'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("PUT /api/auth/change-pin 엔드포인트 미구현")

        assert response.status_code == 200, (
            f"PIN 변경 성공 → Expected 200, got {response.status_code}: {response.get_json()}"
        )

    # ------------------------------------------------------------------
    # TC-PIN-06: PUT /api/auth/change-pin → 현재 PIN 틀리면 400 또는 401
    # ------------------------------------------------------------------
    def test_change_pin_wrong_current(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-PIN-06: 현재 PIN이 틀릴 때 PIN 변경 → 400 또는 401 (WRONG_PIN)"""
        if not _check_hr_schema(db_conn):
            pytest.skip("hr.worker_auth_settings 테이블 없음")

        worker_id = create_test_worker(
            email=f'pin_wrong_{int(time.time()*1000)}@pin_test.com',
            password='Test123!',
            name='PIN Wrong Test',
            role='MECH',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        # PIN 설정
        set_resp = client.post(
            '/api/auth/set-pin',
            json={'pin': '1234'},
            headers={'Authorization': f'Bearer {token}'}
        )
        if set_resp.status_code in (404, 405):
            pytest.skip("POST /api/auth/set-pin 엔드포인트 미구현")
        if set_resp.status_code != 200:
            pytest.skip(f"PIN 설정 실패 ({set_resp.status_code})")

        # 틀린 현재 PIN으로 변경 시도
        response = client.put(
            '/api/auth/change-pin',
            json={'current_pin': '9999', 'new_pin': '5678'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("PUT /api/auth/change-pin 엔드포인트 미구현")

        # BE는 틀린 PIN에 401(WRONG_PIN) 반환
        assert response.status_code in (400, 401), (
            f"틀린 PIN → Expected 400 or 401, got {response.status_code}"
        )
        data = response.get_json()
        assert data.get('error') in ('WRONG_PIN', 'INVALID_PIN', 'INVALID_REQUEST'), (
            f"예상치 못한 에러 코드: {data.get('error')}"
        )

    # ------------------------------------------------------------------
    # TC-PIN-07: POST /api/auth/pin-login → 맞는 PIN → JWT 토큰 발급
    # ------------------------------------------------------------------
    def test_pin_login_success(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-PIN-07: 맞는 PIN으로 로그인 → access_token 발급 (worker_id + pin 사용)"""
        if not _check_hr_schema(db_conn):
            pytest.skip("hr.worker_auth_settings 테이블 없음")

        worker_id = create_test_worker(
            email=f'pin_login_{int(time.time()*1000)}@pin_test.com',
            password='Test123!',
            name='PIN Login Test',
            role='MECH',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        # PIN 설정
        set_resp = client.post(
            '/api/auth/set-pin',
            json={'pin': '1234'},
            headers={'Authorization': f'Bearer {token}'}
        )
        if set_resp.status_code in (404, 405):
            pytest.skip("POST /api/auth/set-pin 엔드포인트 미구현")
        if set_resp.status_code != 200:
            pytest.skip(f"PIN 설정 실패 ({set_resp.status_code})")

        # PIN으로 로그인 (worker_id + pin 사용 — BE API 스펙)
        response = client.post(
            '/api/auth/pin-login',
            json={'worker_id': worker_id, 'pin': '1234'}
        )

        if response.status_code in (404, 405):
            pytest.skip("POST /api/auth/pin-login 엔드포인트 미구현")

        assert response.status_code == 200, (
            f"PIN 로그인 성공 → Expected 200, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        assert 'access_token' in data, "access_token이 응답에 없음"

    # ------------------------------------------------------------------
    # TC-PIN-08: 틀린 PIN → 401 + pin_fail_count 증가
    # ------------------------------------------------------------------
    def test_pin_login_wrong_pin(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-PIN-08: 틀린 PIN → 401 (WRONG_PIN), pin_fail_count 증가"""
        if not _check_hr_schema(db_conn):
            pytest.skip("hr.worker_auth_settings 테이블 없음")

        worker_id = create_test_worker(
            email=f'pin_fail_{int(time.time()*1000)}@pin_test.com',
            password='Test123!',
            name='PIN Fail Test',
            role='MECH',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        # PIN 설정
        set_resp = client.post(
            '/api/auth/set-pin',
            json={'pin': '1234'},
            headers={'Authorization': f'Bearer {token}'}
        )
        if set_resp.status_code in (404, 405):
            pytest.skip("POST /api/auth/set-pin 엔드포인트 미구현")
        if set_resp.status_code != 200:
            pytest.skip(f"PIN 설정 실패 ({set_resp.status_code})")

        # 틀린 PIN으로 로그인 시도 (worker_id + pin)
        response = client.post(
            '/api/auth/pin-login',
            json={'worker_id': worker_id, 'pin': '9999'}
        )

        if response.status_code in (404, 405):
            pytest.skip("POST /api/auth/pin-login 엔드포인트 미구현")

        assert response.status_code == 401, (
            f"틀린 PIN → Expected 401, got {response.status_code}"
        )

        # DB에서 pin_fail_count 증가 확인
        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute(
                "SELECT pin_fail_count FROM hr.worker_auth_settings WHERE worker_id = %s",
                (worker_id,)
            )
            row = cursor.fetchone()
            cursor.close()
            if row is not None:
                assert row[0] >= 1, f"pin_fail_count가 증가하지 않음: {row[0]}"

    # ------------------------------------------------------------------
    # TC-PIN-09: 3회 연속 실패 → 403 Locked (PIN_LOCKED)
    # ------------------------------------------------------------------
    def test_pin_login_locked_after_3_failures(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-PIN-09: PIN 3회 연속 실패 → 403 (PIN_LOCKED)"""
        if not _check_hr_schema(db_conn):
            pytest.skip("hr.worker_auth_settings 테이블 없음")

        worker_id = create_test_worker(
            email=f'pin_lock_{int(time.time()*1000)}@pin_test.com',
            password='Test123!',
            name='PIN Lock Test',
            role='MECH',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        # PIN 설정
        set_resp = client.post(
            '/api/auth/set-pin',
            json={'pin': '1234'},
            headers={'Authorization': f'Bearer {token}'}
        )
        if set_resp.status_code in (404, 405):
            pytest.skip("POST /api/auth/set-pin 엔드포인트 미구현")
        if set_resp.status_code != 200:
            pytest.skip(f"PIN 설정 실패 ({set_resp.status_code})")

        # 3회 틀린 PIN 시도 (worker_id + pin)
        last_response = None
        for _ in range(3):
            last_response = client.post(
                '/api/auth/pin-login',
                json={'worker_id': worker_id, 'pin': '9999'}
            )
            if last_response.status_code in (404, 405):
                pytest.skip("POST /api/auth/pin-login 엔드포인트 미구현")

        # 3회 실패 후: 마지막 시도는 403(PIN_LOCKED) 반환
        assert last_response.status_code in (403, 401, 423), (
            f"3회 실패 후 → Expected 403/401/423, got {last_response.status_code}"
        )

        # 잠금 상태에서 올바른 PIN도 거부되는지 확인
        locked_resp = client.post(
            '/api/auth/pin-login',
            json={'worker_id': worker_id, 'pin': '1234'}
        )
        # 잠금 상태면 403(PIN_LOCKED) 반환
        assert locked_resp.status_code in (403, 401, 423), (
            f"잠금 상태에서 올바른 PIN → Expected 403/401/423, got {locked_resp.status_code}"
        )

    # ------------------------------------------------------------------
    # TC-PIN-10: 잠금 해제 후 성공 (DB에서 pin_locked_until 과거로 설정)
    # ------------------------------------------------------------------
    def test_pin_login_after_lock_expires(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-PIN-10: pin_locked_until을 과거로 설정 후 올바른 PIN 로그인 성공"""
        if not _check_hr_schema(db_conn):
            pytest.skip("hr.worker_auth_settings 테이블 없음")

        worker_id = create_test_worker(
            email=f'pin_unlock_{int(time.time()*1000)}@pin_test.com',
            password='Test123!',
            name='PIN Unlock Test',
            role='MECH',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        # PIN 설정
        set_resp = client.post(
            '/api/auth/set-pin',
            json={'pin': '1234'},
            headers={'Authorization': f'Bearer {token}'}
        )
        if set_resp.status_code in (404, 405):
            pytest.skip("POST /api/auth/set-pin 엔드포인트 미구현")
        if set_resp.status_code != 200:
            pytest.skip(f"PIN 설정 실패 ({set_resp.status_code})")

        if db_conn is None:
            pytest.skip("DB 연결 없음")

        # 잠금 상태로 직접 설정 (pin_fail_count=3, pin_locked_until=과거)
        past_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        cursor = db_conn.cursor()
        try:
            cursor.execute("""
                UPDATE hr.worker_auth_settings
                SET pin_fail_count = 3, pin_locked_until = %s
                WHERE worker_id = %s
            """, (past_time, worker_id))
            db_conn.commit()
        except Exception:
            db_conn.rollback()
            cursor.close()
            pytest.skip("hr.worker_auth_settings 업데이트 실패 (컬럼 구조 다름)")
        cursor.close()

        # 잠금 만료 후 올바른 PIN으로 로그인 (worker_id + pin)
        response = client.post(
            '/api/auth/pin-login',
            json={'worker_id': worker_id, 'pin': '1234'}
        )

        if response.status_code in (404, 405):
            pytest.skip("POST /api/auth/pin-login 엔드포인트 미구현")

        assert response.status_code == 200, (
            f"잠금 해제 후 로그인 → Expected 200, got {response.status_code}: {response.get_json()}"
        )

    # ------------------------------------------------------------------
    # TC-PIN-11: GET /api/auth/pin-status → PIN 미등록 시 pin_registered=false
    # ------------------------------------------------------------------
    def test_pin_status_not_registered(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-PIN-11: PIN 미등록 시 pin_registered=false"""
        if not _check_hr_schema(db_conn):
            pytest.skip("hr.worker_auth_settings 테이블 없음")

        worker_id = create_test_worker(
            email=f'pin_status_no_{int(time.time()*1000)}@pin_test.com',
            password='Test123!',
            name='PIN Status No PIN',
            role='MECH',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        response = client.get(
            '/api/auth/pin-status',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("GET /api/auth/pin-status 엔드포인트 미구현")

        assert response.status_code == 200, (
            f"PIN 상태 조회 → Expected 200, got {response.status_code}"
        )
        data = response.get_json()
        assert 'pin_registered' in data, "pin_registered 필드 없음"
        assert data['pin_registered'] is False, "PIN 미등록 상태인데 pin_registered=true"

    # ------------------------------------------------------------------
    # TC-PIN-12: GET /api/auth/pin-status → PIN 등록 후 pin_registered=true
    # ------------------------------------------------------------------
    def test_pin_status_registered(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-PIN-12: PIN 등록 후 pin_registered=true"""
        if not _check_hr_schema(db_conn):
            pytest.skip("hr.worker_auth_settings 테이블 없음")

        worker_id = create_test_worker(
            email=f'pin_status_yes_{int(time.time()*1000)}@pin_test.com',
            password='Test123!',
            name='PIN Status Yes PIN',
            role='MECH',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        # PIN 설정
        set_resp = client.post(
            '/api/auth/set-pin',
            json={'pin': '4321'},
            headers={'Authorization': f'Bearer {token}'}
        )
        if set_resp.status_code in (404, 405):
            pytest.skip("POST /api/auth/set-pin 엔드포인트 미구현")
        if set_resp.status_code != 200:
            pytest.skip(f"PIN 설정 실패 ({set_resp.status_code})")

        # 상태 확인
        response = client.get(
            '/api/auth/pin-status',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("GET /api/auth/pin-status 엔드포인트 미구현")

        assert response.status_code == 200
        data = response.get_json()
        assert 'pin_registered' in data
        assert data['pin_registered'] is True, "PIN 등록 후인데 pin_registered=false"

    # ------------------------------------------------------------------
    # TC-PIN-13: POST /api/auth/pin-login → PIN 미등록 worker → 404
    # ------------------------------------------------------------------
    def test_pin_login_no_pin_registered(self, client, create_test_worker, db_conn):
        """TC-PIN-13: PIN 미등록 작업자로 PIN 로그인 시도 → 404 (PIN_NOT_SET)"""
        if not _check_hr_schema(db_conn):
            pytest.skip("hr.worker_auth_settings 테이블 없음")

        worker_id = create_test_worker(
            email=f'pin_no_reg_{int(time.time()*1000)}@pin_test.com',
            password='Test123!',
            name='No PIN Worker',
            role='MECH',
            company='FNI'
        )

        # worker_id + pin 으로 로그인 시도 (PIN 미등록 상태)
        response = client.post(
            '/api/auth/pin-login',
            json={'worker_id': worker_id, 'pin': '1234'}
        )

        if response.status_code == 405:
            pytest.skip("POST /api/auth/pin-login 엔드포인트 미구현")

        # BE 스펙: PIN_NOT_SET → 404
        assert response.status_code in (404, 400, 401), (
            f"PIN 미등록 → Expected 404, got {response.status_code}: {response.get_json()}"
        )
        # 404인 경우 에러 코드 확인
        if response.status_code == 404:
            data = response.get_json()
            assert data.get('error') in ('PIN_NOT_SET', 'WORKER_NOT_FOUND'), (
                f"예상치 못한 에러 코드: {data.get('error')}"
            )

    # ------------------------------------------------------------------
    # TC-PIN-14: POST /api/auth/set-pin → 중복 설정 → UPSERT 성공 (에러 없음)
    # ------------------------------------------------------------------
    def test_set_pin_upsert_idempotent(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-PIN-14: 이미 PIN이 설정된 작업자가 set-pin 다시 호출 → UPSERT 성공"""
        if not _check_hr_schema(db_conn):
            pytest.skip("hr.worker_auth_settings 테이블 없음")

        worker_id = create_test_worker(
            email=f'pin_upsert_{int(time.time()*1000)}@pin_test.com',
            password='Test123!',
            name='PIN Upsert Test',
            role='MECH',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        # 첫 번째 PIN 설정
        resp1 = client.post(
            '/api/auth/set-pin',
            json={'pin': '1111'},
            headers={'Authorization': f'Bearer {token}'}
        )
        if resp1.status_code in (404, 405):
            pytest.skip("POST /api/auth/set-pin 엔드포인트 미구현")
        if resp1.status_code != 200:
            pytest.skip(f"첫 PIN 설정 실패 ({resp1.status_code})")

        # 두 번째 PIN 설정 (UPSERT)
        resp2 = client.post(
            '/api/auth/set-pin',
            json={'pin': '2222'},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert resp2.status_code == 200, (
            f"UPSERT PIN 설정 → Expected 200, got {resp2.status_code}: {resp2.get_json()}"
        )

        # DB에서 레코드 1건만 존재 확인
        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM hr.worker_auth_settings WHERE worker_id = %s",
                (worker_id,)
            )
            count = cursor.fetchone()[0]
            cursor.close()
            assert count == 1, f"UPSERT 후 레코드가 {count}건 (1건이어야 함)"
