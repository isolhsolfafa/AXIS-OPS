"""
Geolocation 접속 보안 테스트 (Sprint 19-D)
엔드포인트: POST /api/hr/attendance/check (출근 시 GPS 위치 검증)
설정: GET/PUT /api/admin/settings (geo_check_enabled, geo_strict_mode, geo_latitude, geo_longitude, geo_radius_meters)

테스트 케이스:
  TC-GEO-01: geo_check_enabled=false → 위치 없어도 출근 성공
  TC-GEO-02: geo_check_enabled=true + soft 모드 + 위치 없음 → 출근 성공 (경고만)
  TC-GEO-03: geo_check_enabled=true + 범위 내 위치 → 출근 성공
  TC-GEO-04: geo_check_enabled=true + 범위 밖 위치 → 403 OUT_OF_RANGE
  TC-GEO-05: geo_check_enabled=true + 퇴근 → 위치 불필요 (퇴근은 검증 제외)
  TC-GEO-06: geo_check_enabled=true + 잘못된 좌표 타입 → 400 INVALID_LOCATION
  TC-GEO-07: GET /api/admin/settings → geo 설정 5개 키 포함 확인
  TC-GEO-08: PUT /api/admin/settings → geo_check_enabled 업데이트 성공
  TC-GEO-09: geo_check_enabled=true + strict 모드 + 위치 없음 → 400 LOCATION_REQUIRED
  TC-GEO-10: geo_check_enabled=true + work_site='HQ' → GPS 검증 면제 (위치 없어도 성공)
  TC-GEO-11: PUT /api/admin/settings → geo_strict_mode 업데이트 성공
"""

import time
import pytest
from unittest.mock import patch


# ============================================================
# Helpers
# ============================================================

def _check_hr_schema(db_conn) -> bool:
    """hr.partner_attendance 테이블 존재 여부 확인"""
    if db_conn is None:
        return False
    try:
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'hr' AND table_name = 'partner_attendance'
        """)
        exists = cursor.fetchone() is not None
        cursor.close()
        return exists
    except Exception:
        return False


def _check_admin_settings_table(db_conn) -> bool:
    """admin_settings 테이블 존재 여부 확인"""
    if db_conn is None:
        return False
    try:
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_name = 'admin_settings'
        """)
        exists = cursor.fetchone() is not None
        cursor.close()
        return exists
    except Exception:
        return False


def _set_geo_settings(db_conn, enabled: bool, lat: float, lon: float, radius: float,
                      strict: bool = False):
    """테스트용 geo 설정을 admin_settings에 직접 UPSERT"""
    import json
    cursor = db_conn.cursor()
    settings = [
        ('geo_check_enabled', enabled),
        ('geo_latitude', lat),
        ('geo_longitude', lon),
        ('geo_radius_meters', radius),
        ('geo_strict_mode', strict),
    ]
    for key, val in settings:
        cursor.execute("""
            INSERT INTO admin_settings (setting_key, setting_value)
            VALUES (%s, %s::jsonb)
            ON CONFLICT (setting_key) DO UPDATE
                SET setting_value = EXCLUDED.setting_value
        """, (key, json.dumps(val)))
    db_conn.commit()
    cursor.close()


def _reset_geo_settings(db_conn):
    """geo 설정을 기본값(비활성화)으로 복원"""
    import json
    cursor = db_conn.cursor()
    for key, val in [('geo_check_enabled', False), ('geo_strict_mode', False)]:
        cursor.execute("""
            INSERT INTO admin_settings (setting_key, setting_value)
            VALUES (%s, %s::jsonb)
            ON CONFLICT (setting_key) DO UPDATE SET setting_value = EXCLUDED.setting_value
        """, (key, json.dumps(val)))
    db_conn.commit()
    cursor.close()


# ============================================================
# Autouse cleanup fixtures
# ============================================================

@pytest.fixture(autouse=True)
def cleanup_hr_attendance(db_conn):
    """각 테스트 후 hr.partner_attendance 정리"""
    yield
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            cursor.execute("DELETE FROM hr.partner_attendance WHERE 1=1")
            db_conn.commit()
            cursor.close()
        except Exception:
            try:
                db_conn.rollback()
            except Exception:
                pass


@pytest.fixture(autouse=True)
def reset_geo_after_test(db_conn):
    """각 테스트 후 geo_check_enabled/geo_strict_mode를 false로 복원"""
    yield
    if db_conn and not db_conn.closed:
        try:
            _reset_geo_settings(db_conn)
        except Exception:
            try:
                db_conn.rollback()
            except Exception:
                pass


# ============================================================
# Test class
# ============================================================

class TestGeolocation:
    """GPS 위치 검증 테스트 (TC-GEO-01 ~ TC-GEO-11)"""

    # ------------------------------------------------------------------
    # TC-GEO-01: geo_check_enabled=false → 위치 없어도 출근 성공
    # ------------------------------------------------------------------
    def test_geo_disabled_no_location_required(
        self, client, create_test_worker, get_auth_token, db_conn
    ):
        """TC-GEO-01: geo_check_enabled=false 상태에서 lat/lng 없이 출근 성공"""
        if not _check_hr_schema(db_conn):
            pytest.skip("hr.partner_attendance 테이블 없음")
        if not _check_admin_settings_table(db_conn):
            pytest.skip("admin_settings 테이블 없음")

        # geo_check_enabled=false (기본값 보장)
        _set_geo_settings(db_conn, False, 35.1796, 129.0756, 200)

        worker_id = create_test_worker(
            email=f'geo01_{int(time.time()*1000)}@geo_test.com',
            password='Test123!',
            name='GEO Test 01',
            role='MECH',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        response = client.post(
            '/api/hr/attendance/check',
            json={'check_type': 'in'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("POST /api/hr/attendance/check 엔드포인트 미구현")

        assert response.status_code in (200, 201), (
            f"geo 비활성화 + 위치 없음 → 출근 성공 Expected 201, got {response.status_code}: {response.get_json()}"
        )

    # ------------------------------------------------------------------
    # TC-GEO-02: geo_check_enabled=true + soft 모드 + 위치 없음 → 출근 허용
    # ------------------------------------------------------------------
    def test_geo_enabled_soft_mode_no_location_allows(
        self, client, create_test_worker, get_auth_token, db_conn
    ):
        """TC-GEO-02: geo_check_enabled=true + soft 모드 시 lat/lng 미전달 → 출근 허용 (경고만)"""
        if not _check_hr_schema(db_conn):
            pytest.skip("hr.partner_attendance 테이블 없음")
        if not _check_admin_settings_table(db_conn):
            pytest.skip("admin_settings 테이블 없음")

        # geo_check_enabled=true, strict=false (soft 모드)
        _set_geo_settings(db_conn, True, 35.1796, 129.0756, 200, strict=False)

        worker_id = create_test_worker(
            email=f'geo02_{int(time.time()*1000)}@geo_test.com',
            password='Test123!',
            name='GEO Test 02',
            role='MECH',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        response = client.post(
            '/api/hr/attendance/check',
            json={'check_type': 'in'},  # lat/lng 없음
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("POST /api/hr/attendance/check 엔드포인트 미구현")

        # soft 모드: 위치 미전송 → 출근 허용
        assert response.status_code in (200, 201), (
            f"geo 활성화 + soft 모드 + 위치 없음 → 출근 허용 Expected 201, got {response.status_code}: {response.get_json()}"
        )

    # ------------------------------------------------------------------
    # TC-GEO-03: geo_check_enabled=true + 범위 내 위치 → 출근 성공
    # ------------------------------------------------------------------
    def test_geo_enabled_in_range_success(
        self, client, create_test_worker, get_auth_token, db_conn
    ):
        """TC-GEO-03: geo_check_enabled=true + 허용 반경 내 GPS 좌표 → 출근 성공"""
        if not _check_hr_schema(db_conn):
            pytest.skip("hr.partner_attendance 테이블 없음")
        if not _check_admin_settings_table(db_conn):
            pytest.skip("admin_settings 테이블 없음")

        # 기준점: (35.1796, 129.0756), 반경 500m
        # 클라이언트 좌표: 기준점과 동일 → 거리 0m
        _set_geo_settings(db_conn, True, 35.1796, 129.0756, 500)

        worker_id = create_test_worker(
            email=f'geo03_{int(time.time()*1000)}@geo_test.com',
            password='Test123!',
            name='GEO Test 03',
            role='MECH',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        response = client.post(
            '/api/hr/attendance/check',
            json={
                'check_type': 'in',
                'latitude': 35.1796,
                'longitude': 129.0756
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("POST /api/hr/attendance/check 엔드포인트 미구현")

        assert response.status_code in (200, 201), (
            f"geo 활성화 + 범위 내 → 출근 성공 Expected 201, got {response.status_code}: {response.get_json()}"
        )

    # ------------------------------------------------------------------
    # TC-GEO-04: geo_check_enabled=true + 범위 밖 위치 → 403 OUT_OF_RANGE
    # ------------------------------------------------------------------
    def test_geo_enabled_out_of_range_403(
        self, client, create_test_worker, get_auth_token, db_conn
    ):
        """TC-GEO-04: geo_check_enabled=true + 허용 반경 밖 GPS 좌표 → 403 OUT_OF_RANGE"""
        if not _check_hr_schema(db_conn):
            pytest.skip("hr.partner_attendance 테이블 없음")
        if not _check_admin_settings_table(db_conn):
            pytest.skip("admin_settings 테이블 없음")

        # 기준점: (35.1796, 129.0756), 반경 50m (매우 좁음)
        # 클라이언트: 서울(37.5665, 126.9780) → 300km 이상 이격
        _set_geo_settings(db_conn, True, 35.1796, 129.0756, 50)

        worker_id = create_test_worker(
            email=f'geo04_{int(time.time()*1000)}@geo_test.com',
            password='Test123!',
            name='GEO Test 04',
            role='MECH',
            company='BAT'
        )
        token = get_auth_token(worker_id)

        response = client.post(
            '/api/hr/attendance/check',
            json={
                'check_type': 'in',
                'latitude': 37.5665,   # 서울
                'longitude': 126.9780
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("POST /api/hr/attendance/check 엔드포인트 미구현")

        assert response.status_code == 403, (
            f"geo 활성화 + 범위 밖 → Expected 403, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        assert data.get('error') == 'OUT_OF_RANGE', (
            f"에러 코드 불일치: expected OUT_OF_RANGE, got {data.get('error')}"
        )

    # ------------------------------------------------------------------
    # TC-GEO-05: geo_check_enabled=true + 퇴근 → 위치 불필요
    # ------------------------------------------------------------------
    def test_geo_enabled_checkout_no_location_needed(
        self, client, create_test_worker, get_auth_token, db_conn
    ):
        """TC-GEO-05: geo_check_enabled=true 시 퇴근(check_type=out)은 GPS 검증 제외"""
        if not _check_hr_schema(db_conn):
            pytest.skip("hr.partner_attendance 테이블 없음")
        if not _check_admin_settings_table(db_conn):
            pytest.skip("admin_settings 테이블 없음")

        # 기준점: (35.1796, 129.0756), 반경 50m (매우 좁음)
        _set_geo_settings(db_conn, True, 35.1796, 129.0756, 50)

        worker_id = create_test_worker(
            email=f'geo05_{int(time.time()*1000)}@geo_test.com',
            password='Test123!',
            name='GEO Test 05',
            role='ELEC',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        # geo 비활성화 후 출근 (DB 우회 — 출근 기록 직접 삽입)
        _set_geo_settings(db_conn, False, 35.1796, 129.0756, 50)
        in_resp = client.post(
            '/api/hr/attendance/check',
            json={'check_type': 'in'},
            headers={'Authorization': f'Bearer {token}'}
        )
        if in_resp.status_code in (404, 405):
            pytest.skip("POST /api/hr/attendance/check 엔드포인트 미구현")
        if in_resp.status_code not in (200, 201):
            pytest.skip(f"출근 기록 실패 ({in_resp.status_code}), 퇴근 테스트 불가")

        # geo 다시 활성화
        _set_geo_settings(db_conn, True, 35.1796, 129.0756, 50)

        # 퇴근 시 GPS 없이 요청 — 퇴근은 검증 면제
        out_resp = client.post(
            '/api/hr/attendance/check',
            json={'check_type': 'out'},  # lat/lng 없음
            headers={'Authorization': f'Bearer {token}'}
        )

        assert out_resp.status_code in (200, 201), (
            f"geo 활성화 + 퇴근 위치 없음 → Expected 201, got {out_resp.status_code}: {out_resp.get_json()}"
        )

    # ------------------------------------------------------------------
    # TC-GEO-06: geo_check_enabled=true + 잘못된 좌표 타입 → 400 INVALID_LOCATION
    # ------------------------------------------------------------------
    def test_geo_invalid_coordinate_type_400(
        self, client, create_test_worker, get_auth_token, db_conn
    ):
        """TC-GEO-06: latitude/longitude에 숫자가 아닌 값 전달 → 400 INVALID_LOCATION"""
        if not _check_hr_schema(db_conn):
            pytest.skip("hr.partner_attendance 테이블 없음")
        if not _check_admin_settings_table(db_conn):
            pytest.skip("admin_settings 테이블 없음")

        _set_geo_settings(db_conn, True, 35.1796, 129.0756, 200)

        worker_id = create_test_worker(
            email=f'geo06_{int(time.time()*1000)}@geo_test.com',
            password='Test123!',
            name='GEO Test 06',
            role='MECH',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        response = client.post(
            '/api/hr/attendance/check',
            json={
                'check_type': 'in',
                'latitude': 'not_a_number',  # 잘못된 타입
                'longitude': 129.0756
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("POST /api/hr/attendance/check 엔드포인트 미구현")

        assert response.status_code == 400, (
            f"잘못된 좌표 타입 → Expected 400, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        assert data.get('error') == 'INVALID_LOCATION', (
            f"에러 코드 불일치: expected INVALID_LOCATION, got {data.get('error')}"
        )

    # ------------------------------------------------------------------
    # TC-GEO-07: GET /api/admin/settings → geo 설정 5개 키 포함 확인
    # ------------------------------------------------------------------
    def test_admin_settings_includes_geo_keys(
        self, client, create_test_worker, get_auth_token, db_conn
    ):
        """TC-GEO-07: GET /api/admin/settings 응답에 geo 관련 5개 키 포함"""
        if not _check_admin_settings_table(db_conn):
            pytest.skip("admin_settings 테이블 없음")

        # 관리자 토큰 생성
        admin_id = create_test_worker(
            email=f'geo07_admin_{int(time.time()*1000)}@geo_test.com',
            password='Test123!',
            name='GEO Admin 07',
            role='ADMIN',
            is_admin=True,
            company='GST'
        )
        admin_token = get_auth_token(admin_id, role='ADMIN', is_admin=True)

        response = client.get(
            '/api/admin/settings',
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("GET /api/admin/settings 엔드포인트 미구현")

        assert response.status_code == 200, (
            f"관리자 설정 조회 → Expected 200, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()

        # geo 관련 5개 키 확인 (geo_strict_mode 포함)
        required_geo_keys = [
            'geo_check_enabled', 'geo_strict_mode',
            'geo_latitude', 'geo_longitude', 'geo_radius_meters',
        ]
        for key in required_geo_keys:
            assert key in data, f"응답에 '{key}' 키가 없음. 존재하는 키: {list(data.keys())}"

        # 기본값 타입 확인
        assert isinstance(data['geo_check_enabled'], bool), (
            f"geo_check_enabled는 bool이어야 함, got {type(data['geo_check_enabled'])}"
        )
        assert isinstance(data['geo_strict_mode'], bool), (
            f"geo_strict_mode는 bool이어야 함, got {type(data['geo_strict_mode'])}"
        )

    # ------------------------------------------------------------------
    # TC-GEO-08: PUT /api/admin/settings → geo_check_enabled 업데이트 성공
    # ------------------------------------------------------------------
    def test_admin_settings_update_geo_check_enabled(
        self, client, create_test_worker, get_auth_token, db_conn
    ):
        """TC-GEO-08: PUT /api/admin/settings으로 geo_check_enabled 업데이트 성공"""
        if not _check_admin_settings_table(db_conn):
            pytest.skip("admin_settings 테이블 없음")

        # 초기값: false
        _set_geo_settings(db_conn, False, 35.1796, 129.0756, 200)

        admin_id = create_test_worker(
            email=f'geo08_admin_{int(time.time()*1000)}@geo_test.com',
            password='Test123!',
            name='GEO Admin 08',
            role='ADMIN',
            is_admin=True,
            company='GST'
        )
        admin_token = get_auth_token(admin_id, role='ADMIN', is_admin=True)

        # geo_check_enabled=true로 업데이트
        response = client.put(
            '/api/admin/settings',
            json={'geo_check_enabled': True},
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("PUT /api/admin/settings 엔드포인트 미구현")

        assert response.status_code == 200, (
            f"geo_check_enabled 업데이트 → Expected 200, got {response.status_code}: {response.get_json()}"
        )

        # DB에서 실제로 변경됐는지 확인
        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute(
                "SELECT setting_value FROM admin_settings WHERE setting_key = 'geo_check_enabled'"
            )
            row = cursor.fetchone()
            cursor.close()
            assert row is not None, "admin_settings에 geo_check_enabled 레코드 없음"
            # JSONB true → Python True
            assert row[0] is True or row[0] == 'true' or row[0] is True, (
                f"DB의 geo_check_enabled 값이 true가 아님: {row[0]!r}"
            )

    # ------------------------------------------------------------------
    # TC-GEO-09: geo_check_enabled=true + strict 모드 + 위치 없음 → 400
    # ------------------------------------------------------------------
    def test_geo_enabled_strict_mode_no_location_returns_400(
        self, client, create_test_worker, get_auth_token, db_conn
    ):
        """TC-GEO-09: geo_check_enabled=true + strict 모드 시 lat/lng 미전달 → 400 LOCATION_REQUIRED"""
        if not _check_hr_schema(db_conn):
            pytest.skip("hr.partner_attendance 테이블 없음")
        if not _check_admin_settings_table(db_conn):
            pytest.skip("admin_settings 테이블 없음")

        # geo_check_enabled=true, strict=true
        _set_geo_settings(db_conn, True, 35.1796, 129.0756, 200, strict=True)

        worker_id = create_test_worker(
            email=f'geo09_{int(time.time()*1000)}@geo_test.com',
            password='Test123!',
            name='GEO Test 09',
            role='MECH',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        response = client.post(
            '/api/hr/attendance/check',
            json={'check_type': 'in'},  # lat/lng 없음
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("POST /api/hr/attendance/check 엔드포인트 미구현")

        assert response.status_code == 400, (
            f"geo 활성화 + strict 모드 + 위치 없음 → Expected 400, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        assert data.get('error') == 'LOCATION_REQUIRED', (
            f"에러 코드 불일치: expected LOCATION_REQUIRED, got {data.get('error')}"
        )

    # ------------------------------------------------------------------
    # TC-GEO-10: geo_check_enabled=true + work_site='HQ' → GPS 검증 면제
    # ------------------------------------------------------------------
    def test_geo_enabled_hq_work_site_bypasses_geo(
        self, client, create_test_worker, get_auth_token, db_conn
    ):
        """TC-GEO-10: geo_check_enabled=true + strict 모드이지만 work_site='HQ' → GPS 면제, 출근 성공"""
        if not _check_hr_schema(db_conn):
            pytest.skip("hr.partner_attendance 테이블 없음")
        if not _check_admin_settings_table(db_conn):
            pytest.skip("admin_settings 테이블 없음")

        # geo_check_enabled=true, strict=true (가장 엄격한 설정)
        _set_geo_settings(db_conn, True, 35.1796, 129.0756, 50, strict=True)

        worker_id = create_test_worker(
            email=f'geo10_{int(time.time()*1000)}@geo_test.com',
            password='Test123!',
            name='GEO Test 10',
            role='MECH',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        # work_site='HQ' → GPS 검증 면제 (위치 없이 출근)
        response = client.post(
            '/api/hr/attendance/check',
            json={'check_type': 'in', 'work_site': 'HQ'},  # lat/lng 없음
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("POST /api/hr/attendance/check 엔드포인트 미구현")

        assert response.status_code in (200, 201), (
            f"geo 활성화 + strict + HQ → GPS 면제 Expected 201, got {response.status_code}: {response.get_json()}"
        )

    # ------------------------------------------------------------------
    # TC-GEO-11: PUT /api/admin/settings → geo_strict_mode 업데이트 성공
    # ------------------------------------------------------------------
    def test_admin_settings_update_geo_strict_mode(
        self, client, create_test_worker, get_auth_token, db_conn
    ):
        """TC-GEO-11: PUT /api/admin/settings으로 geo_strict_mode 업데이트 성공"""
        if not _check_admin_settings_table(db_conn):
            pytest.skip("admin_settings 테이블 없음")

        # 초기값: false
        _set_geo_settings(db_conn, False, 35.1796, 129.0756, 200, strict=False)

        admin_id = create_test_worker(
            email=f'geo11_admin_{int(time.time()*1000)}@geo_test.com',
            password='Test123!',
            name='GEO Admin 11',
            role='ADMIN',
            is_admin=True,
            company='GST'
        )
        admin_token = get_auth_token(admin_id, role='ADMIN', is_admin=True)

        # geo_strict_mode=true로 업데이트
        response = client.put(
            '/api/admin/settings',
            json={'geo_strict_mode': True},
            headers={'Authorization': f'Bearer {admin_token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("PUT /api/admin/settings 엔드포인트 미구현")

        assert response.status_code == 200, (
            f"geo_strict_mode 업데이트 → Expected 200, got {response.status_code}: {response.get_json()}"
        )

        # DB에서 실제로 변경됐는지 확인
        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute(
                "SELECT setting_value FROM admin_settings WHERE setting_key = 'geo_strict_mode'"
            )
            row = cursor.fetchone()
            cursor.close()
            assert row is not None, "admin_settings에 geo_strict_mode 레코드 없음"
            assert row[0] is True or row[0] == 'true', (
                f"DB의 geo_strict_mode 값이 true가 아님: {row[0]!r}"
            )
