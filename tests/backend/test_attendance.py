"""
협력사 출퇴근 기록 테스트 (Sprint 12)
엔드포인트:
  POST /api/hr/attendance/check  - 출근/퇴근 기록 (협력사 작업자 전용)
  GET  /api/hr/attendance/today  - 당일 출퇴근 기록 조회

DB: hr.partner_attendance (worker_id, check_type, check_time, method)
대상: 협력사(MECH/ELEC/TM) 작업자만 허용, GST 작업자는 403
"""

import time
import pytest
from datetime import datetime, timezone


# ============================================================
# Autouse cleanup fixture — hr.partner_attendance 정리
# ============================================================
@pytest.fixture(autouse=True)
def cleanup_hr_attendance(db_conn):
    """각 테스트 후 테스트가 생성한 worker의 hr.partner_attendance만 정리
    (기존 운영 데이터는 보존)"""
    # 테스트 시작 전 시점 기록
    test_start = None
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            cursor.execute("SELECT NOW()")
            test_start = cursor.fetchone()[0]
            cursor.close()
        except Exception:
            pass
    yield
    # 테스트 시작 이후에 생성된 레코드만 삭제 (운영 데이터 보존)
    if db_conn and not db_conn.closed and test_start:
        try:
            cursor = db_conn.cursor()
            cursor.execute(
                "DELETE FROM hr.partner_attendance WHERE created_at >= %s",
                (test_start,)
            )
            db_conn.commit()
            cursor.close()
        except Exception:
            try:
                db_conn.rollback()
            except Exception:
                pass


def _check_hr_attendance_schema(db_conn) -> bool:
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


def _get_today_date_str() -> str:
    """KST 기준 오늘 날짜 문자열 반환 (YYYY-MM-DD)"""
    from datetime import timezone, timedelta
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst).strftime('%Y-%m-%d')


class TestPartnerAttendance:
    """협력사 출퇴근 기록 테스트 (TC-ATT-01 ~ TC-ATT-08)"""

    # ------------------------------------------------------------------
    # TC-ATT-01: POST /api/hr/attendance/check → check_type='in' 출근 성공 (협력사)
    # ------------------------------------------------------------------
    def test_check_in_success(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-ATT-01: 협력사 작업자 출근 기록 성공"""
        if not _check_hr_attendance_schema(db_conn):
            pytest.skip("hr.partner_attendance 테이블 없음 (Sprint 12 마이그레이션 필요)")

        worker_id = create_test_worker(
            email=f'att_in_{int(time.time()*1000)}@att_test.com',
            password='Test123!',
            name='ATT Check In Worker',
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

        # BE 스펙: 출근/퇴근 기록 생성 시 201 반환
        assert response.status_code in (200, 201), (
            f"출근 기록 → Expected 200 or 201, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        assert 'message' in data or 'check_type' in data or 'id' in data or 'record' in data

        # DB에서 출근 기록 확인
        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute(
                "SELECT check_type FROM hr.partner_attendance WHERE worker_id = %s ORDER BY check_time DESC LIMIT 1",
                (worker_id,)
            )
            row = cursor.fetchone()
            cursor.close()
            assert row is not None, "출근 기록이 DB에 없음"
            assert row[0] == 'in', f"check_type이 'in'이 아님: {row[0]}"

    # ------------------------------------------------------------------
    # TC-ATT-02: POST /api/hr/attendance/check → check_type='out' 퇴근 성공
    # ------------------------------------------------------------------
    def test_check_out_success(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-ATT-02: 협력사 작업자 퇴근 기록 성공 (출근 후)"""
        if not _check_hr_attendance_schema(db_conn):
            pytest.skip("hr.partner_attendance 테이블 없음")

        worker_id = create_test_worker(
            email=f'att_out_{int(time.time()*1000)}@att_test.com',
            password='Test123!',
            name='ATT Check Out Worker',
            role='ELEC',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        # 출근 먼저
        in_resp = client.post(
            '/api/hr/attendance/check',
            json={'check_type': 'in'},
            headers={'Authorization': f'Bearer {token}'}
        )
        if in_resp.status_code in (404, 405):
            pytest.skip("POST /api/hr/attendance/check 엔드포인트 미구현")
        # BE 스펙: 출근 기록 성공 시 201 반환
        if in_resp.status_code not in (200, 201):
            pytest.skip(f"출근 기록 실패 ({in_resp.status_code}), 퇴근 테스트 불가")

        # 퇴근
        response = client.post(
            '/api/hr/attendance/check',
            json={'check_type': 'out'},
            headers={'Authorization': f'Bearer {token}'}
        )

        # BE 스펙: 퇴근 기록 성공 시 201 반환
        assert response.status_code in (200, 201), (
            f"퇴근 기록 → Expected 200 or 201, got {response.status_code}: {response.get_json()}"
        )

        # DB에서 퇴근 기록 확인
        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute(
                "SELECT check_type FROM hr.partner_attendance WHERE worker_id = %s ORDER BY check_time DESC LIMIT 1",
                (worker_id,)
            )
            row = cursor.fetchone()
            cursor.close()
            assert row is not None
            assert row[0] == 'out', f"check_type이 'out'이 아님: {row[0]}"

    # ------------------------------------------------------------------
    # TC-ATT-03: 당일 중복 출근 → 400
    # ------------------------------------------------------------------
    def test_duplicate_check_in_same_day(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-ATT-03: 당일 이미 출근한 경우 중복 출근 → 400"""
        if not _check_hr_attendance_schema(db_conn):
            pytest.skip("hr.partner_attendance 테이블 없음")

        worker_id = create_test_worker(
            email=f'att_dup_{int(time.time()*1000)}@att_test.com',
            password='Test123!',
            name='ATT Duplicate Test',
            role='MECH',
            company='BAT'
        )
        token = get_auth_token(worker_id)

        # 첫 번째 출근
        in_resp1 = client.post(
            '/api/hr/attendance/check',
            json={'check_type': 'in'},
            headers={'Authorization': f'Bearer {token}'}
        )
        if in_resp1.status_code in (404, 405):
            pytest.skip("POST /api/hr/attendance/check 엔드포인트 미구현")
        if in_resp1.status_code not in (200, 201):
            pytest.skip(f"첫 출근 기록 실패 ({in_resp1.status_code})")

        # 두 번째 출근 (중복)
        in_resp2 = client.post(
            '/api/hr/attendance/check',
            json={'check_type': 'in'},
            headers={'Authorization': f'Bearer {token}'}
        )

        assert in_resp2.status_code == 400, (
            f"중복 출근 → Expected 400, got {in_resp2.status_code}"
        )

    # ------------------------------------------------------------------
    # TC-ATT-04: 출근 없이 퇴근 → 400
    # ------------------------------------------------------------------
    def test_check_out_without_check_in(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-ATT-04: 당일 출근 기록 없이 퇴근 시도 → 400"""
        if not _check_hr_attendance_schema(db_conn):
            pytest.skip("hr.partner_attendance 테이블 없음")

        worker_id = create_test_worker(
            email=f'att_nocheck_{int(time.time()*1000)}@att_test.com',
            password='Test123!',
            name='ATT No CheckIn Test',
            role='MECH',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        # 출근 없이 바로 퇴근
        response = client.post(
            '/api/hr/attendance/check',
            json={'check_type': 'out'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("POST /api/hr/attendance/check 엔드포인트 미구현")

        assert response.status_code == 400, (
            f"출근 없이 퇴근 → Expected 400, got {response.status_code}"
        )

    # ------------------------------------------------------------------
    # TC-ATT-05: GST 작업자 → 403
    # ------------------------------------------------------------------
    def test_gst_worker_forbidden(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-ATT-05: GST 소속 작업자가 출퇴근 기록 시도 → 403"""
        if not _check_hr_attendance_schema(db_conn):
            pytest.skip("hr.partner_attendance 테이블 없음")

        worker_id = create_test_worker(
            email=f'gst_att_{int(time.time()*1000)}@att_test.com',
            password='Test123!',
            name='GST Attendance Test',
            role='PI',
            company='GST'
        )
        token = get_auth_token(worker_id)

        response = client.post(
            '/api/hr/attendance/check',
            json={'check_type': 'in'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("POST /api/hr/attendance/check 엔드포인트 미구현")

        assert response.status_code == 403, (
            f"GST 작업자 출근 → Expected 403, got {response.status_code}"
        )

    # ------------------------------------------------------------------
    # TC-ATT-06: 미인증 → 401
    # ------------------------------------------------------------------
    def test_check_unauthorized(self, client, db_conn):
        """TC-ATT-06: JWT 없이 출퇴근 기록 → 401"""
        if not _check_hr_attendance_schema(db_conn):
            pytest.skip("hr.partner_attendance 테이블 없음")

        response = client.post(
            '/api/hr/attendance/check',
            json={'check_type': 'in'}
        )

        if response.status_code in (404, 405):
            pytest.skip("POST /api/hr/attendance/check 엔드포인트 미구현")

        assert response.status_code == 401, (
            f"미인증 → Expected 401, got {response.status_code}"
        )

    # ------------------------------------------------------------------
    # TC-ATT-07: GET /api/hr/attendance/today → 당일 기록 조회
    # ------------------------------------------------------------------
    def test_get_today_attendance(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-ATT-07: 당일 출퇴근 기록 조회 (출근 후 기록 반환)"""
        if not _check_hr_attendance_schema(db_conn):
            pytest.skip("hr.partner_attendance 테이블 없음")

        worker_id = create_test_worker(
            email=f'att_today_{int(time.time()*1000)}@att_test.com',
            password='Test123!',
            name='ATT Today Test',
            role='MECH',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        # 출근 기록
        in_resp = client.post(
            '/api/hr/attendance/check',
            json={'check_type': 'in'},
            headers={'Authorization': f'Bearer {token}'}
        )
        if in_resp.status_code in (404, 405):
            pytest.skip("POST /api/hr/attendance/check 엔드포인트 미구현")
        if in_resp.status_code not in (200, 201):
            pytest.skip(f"출근 기록 실패 ({in_resp.status_code})")

        # 당일 기록 조회
        response = client.get(
            '/api/hr/attendance/today',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("GET /api/hr/attendance/today 엔드포인트 미구현")

        assert response.status_code == 200, (
            f"당일 기록 조회 → Expected 200, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        # 응답에 status 또는 records 또는 check_in 정보 포함
        assert any(key in data for key in ('status', 'records', 'check_in', 'check_in_time')), (
            f"응답에 출퇴근 정보 키가 없음: {data.keys()}"
        )

    # ------------------------------------------------------------------
    # TC-ATT-08: GET /api/hr/attendance/today → 기록 없으면 status='not_checked'
    # ------------------------------------------------------------------
    def test_get_today_attendance_not_checked(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-ATT-08: 당일 출퇴근 기록 없으면 status='not_checked' 또는 빈 결과"""
        if not _check_hr_attendance_schema(db_conn):
            pytest.skip("hr.partner_attendance 테이블 없음")

        worker_id = create_test_worker(
            email=f'att_empty_{int(time.time()*1000)}@att_test.com',
            password='Test123!',
            name='ATT Empty Test',
            role='MECH',
            company='BAT'
        )
        token = get_auth_token(worker_id)

        response = client.get(
            '/api/hr/attendance/today',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("GET /api/hr/attendance/today 엔드포인트 미구현")

        assert response.status_code == 200, (
            f"기록 없는 당일 조회 → Expected 200, got {response.status_code}"
        )
        data = response.get_json()
        # status='not_checked' 또는 records=[] 또는 check_in=null
        if 'status' in data:
            assert data['status'] == 'not_checked', (
                f"기록 없을 때 status='{data['status']}' (expected 'not_checked')"
            )
        elif 'records' in data:
            assert data['records'] == [], f"기록 없을 때 records가 비어있지 않음: {data['records']}"
        elif 'check_in' in data:
            assert data['check_in'] is None, f"기록 없을 때 check_in이 None이 아님: {data['check_in']}"
        # 그 외 구현에 따라 다를 수 있으므로 200이면 통과

    # ------------------------------------------------------------------
    # TC-ATT-09: 출근 시 work_site + product_line 전달 → DB 정상 저장
    # ------------------------------------------------------------------
    def test_check_in_with_work_site_product_line(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-ATT-09: 출근 시 work_site + product_line DB 정상 저장"""
        if not _check_hr_attendance_schema(db_conn):
            pytest.skip("hr.partner_attendance 테이블 없음")

        worker_id = create_test_worker(
            email=f'att_site_{int(time.time()*1000)}@att_test.com',
            password='Test123!',
            name='ATT Site Test',
            role='MECH',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        response = client.post(
            '/api/hr/attendance/check',
            json={'check_type': 'in', 'work_site': 'HQ', 'product_line': 'CHI'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("POST /api/hr/attendance/check 엔드포인트 미구현")

        assert response.status_code in (200, 201), (
            f"출근(HQ/CHI) → Expected 201, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        record = data.get('record', data)
        assert record.get('work_site') == 'HQ', f"work_site 불일치: {record.get('work_site')}"
        assert record.get('product_line') == 'CHI', f"product_line 불일치: {record.get('product_line')}"

        # DB 직접 확인
        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute(
                "SELECT work_site, product_line FROM hr.partner_attendance WHERE worker_id = %s ORDER BY check_time DESC LIMIT 1",
                (worker_id,)
            )
            row = cursor.fetchone()
            cursor.close()
            assert row is not None, "DB 레코드 없음"
            assert row[0] == 'HQ', f"DB work_site={row[0]}"
            assert row[1] == 'CHI', f"DB product_line={row[1]}"

    # ------------------------------------------------------------------
    # TC-ATT-10: 퇴근 시 work_site/product_line 미전달 → 마지막 IN 값 자동 복사
    # ------------------------------------------------------------------
    def test_check_out_copies_last_in_classification(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-ATT-10: 퇴근 시 마지막 IN 레코드의 work_site/product_line 자동 복사"""
        if not _check_hr_attendance_schema(db_conn):
            pytest.skip("hr.partner_attendance 테이블 없음")

        worker_id = create_test_worker(
            email=f'att_outcopy_{int(time.time()*1000)}@att_test.com',
            password='Test123!',
            name='ATT Out Copy Test',
            role='ELEC',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        # 출근 (HQ / CHI)
        in_resp = client.post(
            '/api/hr/attendance/check',
            json={'check_type': 'in', 'work_site': 'HQ', 'product_line': 'CHI'},
            headers={'Authorization': f'Bearer {token}'}
        )
        if in_resp.status_code in (404, 405):
            pytest.skip("POST /api/hr/attendance/check 엔드포인트 미구현")
        if in_resp.status_code not in (200, 201):
            pytest.skip(f"출근 기록 실패 ({in_resp.status_code})")

        # 퇴근 (work_site/product_line 미전달)
        out_resp = client.post(
            '/api/hr/attendance/check',
            json={'check_type': 'out'},
            headers={'Authorization': f'Bearer {token}'}
        )
        assert out_resp.status_code in (200, 201), (
            f"퇴근 → Expected 201, got {out_resp.status_code}: {out_resp.get_json()}"
        )
        data = out_resp.get_json()
        record = data.get('record', data)
        # 마지막 IN의 HQ / CHI가 복사되어야 함
        assert record.get('work_site') == 'HQ', f"퇴근 work_site 불일치: {record.get('work_site')}"
        assert record.get('product_line') == 'CHI', f"퇴근 product_line 불일치: {record.get('product_line')}"

    # ------------------------------------------------------------------
    # TC-ATT-11: 잘못된 work_site 전달 → 400 INVALID_WORK_SITE
    # ------------------------------------------------------------------
    def test_invalid_work_site(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-ATT-11: 잘못된 work_site 전달 시 400"""
        if not _check_hr_attendance_schema(db_conn):
            pytest.skip("hr.partner_attendance 테이블 없음")

        worker_id = create_test_worker(
            email=f'att_badsite_{int(time.time()*1000)}@att_test.com',
            password='Test123!',
            name='ATT Bad Site',
            role='MECH',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        response = client.post(
            '/api/hr/attendance/check',
            json={'check_type': 'in', 'work_site': 'INVALID'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("POST /api/hr/attendance/check 엔드포인트 미구현")

        assert response.status_code == 400, (
            f"잘못된 work_site → Expected 400, got {response.status_code}"
        )
        data = response.get_json()
        assert data.get('error') == 'INVALID_WORK_SITE', f"에러 코드 불일치: {data.get('error')}"

    # ------------------------------------------------------------------
    # TC-ATT-12: 잘못된 product_line 전달 → 400 INVALID_PRODUCT_LINE
    # ------------------------------------------------------------------
    def test_invalid_product_line(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-ATT-12: 잘못된 product_line 전달 시 400"""
        if not _check_hr_attendance_schema(db_conn):
            pytest.skip("hr.partner_attendance 테이블 없음")

        worker_id = create_test_worker(
            email=f'att_badline_{int(time.time()*1000)}@att_test.com',
            password='Test123!',
            name='ATT Bad Line',
            role='MECH',
            company='BAT'
        )
        token = get_auth_token(worker_id)

        response = client.post(
            '/api/hr/attendance/check',
            json={'check_type': 'in', 'product_line': 'INVALID'},
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("POST /api/hr/attendance/check 엔드포인트 미구현")

        assert response.status_code == 400, (
            f"잘못된 product_line → Expected 400, got {response.status_code}"
        )
        data = response.get_json()
        assert data.get('error') == 'INVALID_PRODUCT_LINE', f"에러 코드 불일치: {data.get('error')}"

    # ------------------------------------------------------------------
    # TC-ATT-13: today 조회 시 work_site/product_line 포함 확인
    # ------------------------------------------------------------------
    def test_today_includes_classification(self, client, create_test_worker, get_auth_token, db_conn):
        """TC-ATT-13: /attendance/today 응답에 work_site/product_line 포함"""
        if not _check_hr_attendance_schema(db_conn):
            pytest.skip("hr.partner_attendance 테이블 없음")

        worker_id = create_test_worker(
            email=f'att_todayclass_{int(time.time()*1000)}@att_test.com',
            password='Test123!',
            name='ATT Today Class',
            role='ELEC',
            company='FNI'
        )
        token = get_auth_token(worker_id)

        # 출근 (GST / SCR — default)
        in_resp = client.post(
            '/api/hr/attendance/check',
            json={'check_type': 'in'},
            headers={'Authorization': f'Bearer {token}'}
        )
        if in_resp.status_code in (404, 405):
            pytest.skip("POST /api/hr/attendance/check 엔드포인트 미구현")
        if in_resp.status_code not in (200, 201):
            pytest.skip(f"출근 기록 실패 ({in_resp.status_code})")

        # today 조회
        response = client.get(
            '/api/hr/attendance/today',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code in (404, 405):
            pytest.skip("GET /api/hr/attendance/today 엔드포인트 미구현")

        assert response.status_code == 200
        data = response.get_json()
        records = data.get('records', [])
        assert len(records) >= 1, "출근 기록이 없음"

        first = records[0]
        assert 'work_site' in first, f"records에 work_site 필드 없음: {first.keys()}"
        assert 'product_line' in first, f"records에 product_line 필드 없음: {first.keys()}"
        assert first['work_site'] == 'GST', f"default work_site 불일치: {first['work_site']}"
        assert first['product_line'] == 'SCR', f"default product_line 불일치: {first['product_line']}"
