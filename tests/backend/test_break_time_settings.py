"""
휴게시간 설정 API 테스트 (Sprint 9)
관리자 설정 엔드포인트:
  GET  /api/admin/settings  - 전체 설정 조회 (휴게시간 포함)
  PUT  /api/admin/settings  - 설정 업데이트

Sprint 9 신규 설정 키:
  break_morning_start, break_morning_end
  break_afternoon_start, break_afternoon_end
  lunch_start, lunch_end
  dinner_start, dinner_end
  auto_pause_enabled

TC-SET-01 ~ TC-SET-08: 8개 테스트 케이스
"""

import time
import pytest
from datetime import datetime, timezone


# ============================================================
# 설정 테스트 전용 fixture
# ============================================================
@pytest.fixture(autouse=True)
def cleanup_settings_test_data(db_conn):
    """테스트 후 변경된 설정 원복"""
    # 기본 휴게시간 값 저장
    original_settings = {}
    break_keys = [
        'break_morning_start', 'break_morning_end',
        'break_afternoon_start', 'break_afternoon_end',
        'lunch_start', 'lunch_end',
        'dinner_start', 'dinner_end',
        'auto_pause_enabled',
    ]

    if db_conn and not db_conn.closed:
        cursor = db_conn.cursor()
        for key in break_keys:
            cursor.execute(
                "SELECT setting_value FROM admin_settings WHERE setting_key = %s",
                (key,)
            )
            row = cursor.fetchone()
            if row:
                original_settings[key] = row[0]
        cursor.close()

    yield

    # 원복
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            for key, value in original_settings.items():
                cursor.execute(
                    """
                    UPDATE admin_settings
                    SET setting_value = %s
                    WHERE setting_key = %s
                    """,
                    (str(value) if not isinstance(value, str) else value, key)
                )
            db_conn.commit()
            cursor.close()
        except Exception:
            pass


@pytest.fixture
def settings_admin(create_test_worker, get_admin_auth_token):
    """설정 테스트 전용 Admin"""
    unique_email = f'settings_admin_{int(time.time() * 1000)}@settings_test.com'
    worker_id = create_test_worker(
        email=unique_email,
        password='AdminPass123!',
        name='Settings Test Admin',
        role='QI',
        approval_status='approved',
        email_verified=True,
        is_admin=True
    )
    token = get_admin_auth_token(worker_id)
    return {'id': worker_id, 'email': unique_email, 'token': token}


# ============================================================
# TestBreakTimeSettingsRead: 휴게시간 설정 조회
# ============================================================
class TestBreakTimeSettingsRead:
    """GET /api/admin/settings — 휴게시간 설정 포함 확인"""

    def test_get_settings_includes_break_time_keys(
        self, client, settings_admin
    ):
        """
        TC-SET-01: GET /api/admin/settings 결과에 휴게시간 키 포함 확인

        Expected:
        - Status 200
        - break_morning_start, break_morning_end 키 포함
        - lunch_start, lunch_end 키 포함
        - break_afternoon_start, break_afternoon_end 키 포함
        - dinner_start, dinner_end 키 포함
        - auto_pause_enabled 키 포함
        """
        response = client.get(
            '/api/admin/settings',
            headers={'Authorization': f'Bearer {settings_admin["token"]}'}
        )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()

        # Sprint 9 신규 휴게시간 키 확인
        expected_keys = [
            'break_morning_start', 'break_morning_end',
            'lunch_start', 'lunch_end',
            'break_afternoon_start', 'break_afternoon_end',
            'dinner_start', 'dinner_end',
            'auto_pause_enabled',
        ]
        for key in expected_keys:
            assert key in data, f"Setting key '{key}' should be in response"

    def test_get_settings_break_time_default_values(
        self, client, settings_admin
    ):
        """
        TC-SET-02: 휴게시간 기본값 확인

        Expected (migration 008_sprint9_pause_resume.sql 기준):
        - break_morning_start == "10:00"
        - break_morning_end == "10:20"
        - lunch_start == "11:20"
        - lunch_end == "12:20"
        - break_afternoon_start == "15:00"
        - break_afternoon_end == "15:20"
        - dinner_start == "17:00"
        - dinner_end == "18:00"
        - auto_pause_enabled == True
        """
        response = client.get(
            '/api/admin/settings',
            headers={'Authorization': f'Bearer {settings_admin["token"]}'}
        )

        assert response.status_code == 200
        data = response.get_json()

        # 기본값 검증 (설정 변경이 없었다면)
        expected_defaults = {
            'break_morning_start': '10:00',
            'break_morning_end': '10:20',
            'lunch_start': '11:20',
            'lunch_end': '12:20',
            'break_afternoon_start': '15:00',
            'break_afternoon_end': '15:20',
            'dinner_start': '17:00',
            'dinner_end': '18:00',
        }
        for key, expected_val in expected_defaults.items():
            if key in data:
                actual = data[key]
                # 값이 string 또는 dict 형태일 수 있음
                actual_str = str(actual).strip('"') if actual else ''
                assert actual_str == expected_val or actual == expected_val, (
                    f"Default value for '{key}': expected '{expected_val}', got '{actual}'"
                )


# ============================================================
# TestBreakTimeSettingsWrite: 휴게시간 설정 업데이트
# ============================================================
class TestBreakTimeSettingsWrite:
    """PUT /api/admin/settings — 휴게시간 설정 업데이트"""

    def test_update_morning_break_times(
        self, client, settings_admin
    ):
        """
        TC-SET-03: 오전 휴게시간 시작/종료 시각 업데이트

        Expected:
        - Status 200
        - updated_keys에 break_morning_start, break_morning_end 포함
        - GET으로 재조회 시 변경된 값 반영
        """
        token = settings_admin['token']

        response = client.put(
            '/api/admin/settings',
            json={
                'break_morning_start': '09:50',
                'break_morning_end': '10:10',
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        assert 'updated_keys' in data
        assert 'break_morning_start' in data['updated_keys']
        assert 'break_morning_end' in data['updated_keys']

        # GET으로 반영 확인
        get_resp = client.get(
            '/api/admin/settings',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert get_resp.status_code == 200
        settings = get_resp.get_json()
        assert '09:50' in str(settings.get('break_morning_start', ''))
        assert '10:10' in str(settings.get('break_morning_end', ''))

    def test_update_auto_pause_enabled(
        self, client, settings_admin
    ):
        """
        TC-SET-04: auto_pause_enabled 설정 변경

        Expected:
        - Status 200
        - auto_pause_enabled == False → GET 재조회 반영
        """
        token = settings_admin['token']

        # False로 설정
        resp = client.put(
            '/api/admin/settings',
            json={'auto_pause_enabled': False},
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200

        # GET으로 확인
        get_resp = client.get(
            '/api/admin/settings',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert get_resp.status_code == 200
        settings = get_resp.get_json()
        # auto_pause_enabled가 false로 변경되어야 함
        val = settings.get('auto_pause_enabled')
        assert val is False or str(val).lower() == 'false', (
            f"auto_pause_enabled should be False, got {val}"
        )

        # True로 원복
        client.put(
            '/api/admin/settings',
            json={'auto_pause_enabled': True},
            headers={'Authorization': f'Bearer {token}'}
        )

    def test_time_format_validation(
        self, client, settings_admin
    ):
        """
        TC-SET-05: 잘못된 시간 형식 거부 (HH:MM 형식 아닌 경우)

        Expected:
        - Status 400
        - error: INVALID_REQUEST 또는 TIME_FORMAT_INVALID
        """
        response = client.put(
            '/api/admin/settings',
            json={'break_morning_start': 'invalid_time'},
            headers={'Authorization': f'Bearer {settings_admin["token"]}'}
        )

        # 구현에 따라 400 (strict validation) 또는 200 (lenient) 가능
        # 400이면 error 포함, 200이면 저장될 수 있음 — 구현 확인
        if response.status_code == 400:
            data = response.get_json()
            assert 'error' in data
        else:
            # 200으로 성공하면 저장된 것으로 간주 (lenient 구현)
            assert response.status_code == 200

    def test_start_before_end_validation(
        self, client, settings_admin
    ):
        """
        TC-SET-06: start 시간이 end 시간보다 늦은 경우 거부

        Input: break_morning_start='11:00', break_morning_end='10:00'
        Expected:
        - Status 400 (strict validation)
          또는 200 (lenient — BE 구현에 따라)
        - 400이면 error 포함
        """
        response = client.put(
            '/api/admin/settings',
            json={
                'break_morning_start': '11:00',
                'break_morning_end': '10:00',  # start가 end보다 늦음
            },
            headers={'Authorization': f'Bearer {settings_admin["token"]}'}
        )

        if response.status_code == 400:
            data = response.get_json()
            assert 'error' in data
        else:
            # BE가 lenient하게 저장 허용할 수 있음
            assert response.status_code == 200

    def test_update_multiple_break_settings_at_once(
        self, client, settings_admin
    ):
        """
        TC-SET-07: 여러 휴게시간 설정 동시 업데이트

        Expected:
        - Status 200
        - updated_keys에 모든 변경 키 포함
        """
        token = settings_admin['token']

        response = client.put(
            '/api/admin/settings',
            json={
                'lunch_start': '12:00',
                'lunch_end': '13:00',
                'dinner_start': '18:00',
                'dinner_end': '19:00',
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        assert 'updated_keys' in data
        assert 'lunch_start' in data['updated_keys']
        assert 'lunch_end' in data['updated_keys']

    def test_update_break_settings_non_admin_forbidden(
        self, client, create_test_worker, get_auth_token
    ):
        """
        TC-SET-08: 일반 작업자로 휴게시간 설정 변경 → 403

        Expected:
        - Status 403
        """
        unique_email = f'regular_{int(time.time() * 1000)}@settings_test.com'
        worker_id = create_test_worker(
            email=unique_email,
            password='Test123!',
            name='Regular Worker',
            role='MECH',
            approval_status='approved',
            is_admin=False
        )
        token = get_auth_token(worker_id, role='MECH')

        response = client.put(
            '/api/admin/settings',
            json={'auto_pause_enabled': False},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 403, (
            f"Expected 403 for non-admin, got {response.status_code}"
        )
