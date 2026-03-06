"""
Admin 출퇴근 API 테스트
Sprint 19-E: VIEW용 Admin 출퇴근 API 3개
"""

import pytest
from datetime import datetime, timedelta, timezone


KST = timezone(timedelta(hours=9))


@pytest.fixture(autouse=True)
def cleanup_attendance_test_data(db_conn):
    """테스트 전후 출퇴근 테스트 데이터 정리"""
    # Pre-cleanup: 이전 테스트 잔여 데이터 제거
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            cursor.execute(
                "DELETE FROM hr.partner_attendance WHERE worker_id IN "
                "(SELECT id FROM workers WHERE email LIKE 'att_test_%@test.com')"
            )
            cursor.execute(
                "DELETE FROM workers WHERE email LIKE 'att_test_%@test.com'"
            )
            cursor.execute(
                "DELETE FROM workers WHERE email = 'admin_sprint4@test.axisos.com'"
            )
            db_conn.commit()
            cursor.close()
        except Exception:
            db_conn.rollback()

    yield

    # Post-cleanup
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            cursor.execute(
                "DELETE FROM hr.partner_attendance WHERE worker_id IN "
                "(SELECT id FROM workers WHERE email LIKE 'att_test_%@test.com')"
            )
            cursor.execute(
                "DELETE FROM workers WHERE email LIKE 'att_test_%@test.com'"
            )
            cursor.execute(
                "DELETE FROM workers WHERE email = 'admin_sprint4@test.axisos.com'"
            )
            db_conn.commit()
            cursor.close()
        except Exception:
            pass


@pytest.fixture
def att_workers(create_test_worker):
    """출퇴근 테스트용 작업자 3명 (C&A 2명, FNI 1명)"""
    w1 = create_test_worker(
        email='att_test_ca1@test.com', password='Test123!',
        name='CA Worker 1', role='ELEC', company='C&A',
    )
    w2 = create_test_worker(
        email='att_test_ca2@test.com', password='Test123!',
        name='CA Worker 2', role='ELEC', company='C&A',
    )
    w3 = create_test_worker(
        email='att_test_fni1@test.com', password='Test123!',
        name='FNI Worker 1', role='MECH', company='FNI',
    )
    return {'ca1': w1, 'ca2': w2, 'fni1': w3}


@pytest.fixture
def insert_attendance(db_conn):
    """출퇴근 기록 삽입 헬퍼"""
    def _insert(worker_id, check_type, check_time, work_site='GST', product_line='SCR'):
        if db_conn is None:
            return
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO hr.partner_attendance
                (worker_id, check_type, check_time, method, work_site, product_line)
            VALUES (%s, %s, %s, 'button', %s, %s)
        """, (worker_id, check_type, check_time, work_site, product_line))
        db_conn.commit()
        cursor.close()
    return _insert


class TestAttendanceToday:
    """GET /api/admin/hr/attendance/today"""

    def test_att01_empty_data(
        self, client, att_workers, create_test_admin, get_admin_auth_token
    ):
        """ATT-01: 출퇴근 기록 없음 → records에 작업자 있지만 전부 not_checked"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        response = client.get(
            '/api/admin/hr/attendance/today',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'date' in data
        assert 'records' in data
        assert 'summary' in data
        # 테스트 작업자들은 전부 not_checked
        test_records = [r for r in data['records'] if r['worker_id'] in att_workers.values()]
        for r in test_records:
            assert r['status'] == 'not_checked'
            assert r['check_in_time'] is None
            assert r['check_out_time'] is None

    def test_att02_checked_in_only(
        self, client, att_workers, insert_attendance,
        create_test_admin, get_admin_auth_token
    ):
        """ATT-02: 출근만 한 작업자 → status='working'"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        now_kst = datetime.now(KST)
        check_in_time = now_kst.replace(hour=8, minute=15, second=0, microsecond=0)
        insert_attendance(att_workers['ca1'], 'in', check_in_time, 'GST', 'SCR')

        response = client.get(
            '/api/admin/hr/attendance/today',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        ca1_record = next(
            (r for r in data['records'] if r['worker_id'] == att_workers['ca1']), None
        )
        assert ca1_record is not None
        assert ca1_record['status'] == 'working'
        assert ca1_record['check_in_time'] is not None
        assert ca1_record['check_out_time'] is None

    def test_att03_checked_in_and_out(
        self, client, att_workers, insert_attendance,
        create_test_admin, get_admin_auth_token
    ):
        """ATT-03: 출근+퇴근 완료 → status='left'"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        now_kst = datetime.now(KST)
        check_in = now_kst.replace(hour=8, minute=0, second=0, microsecond=0)
        check_out = now_kst.replace(hour=17, minute=30, second=0, microsecond=0)
        insert_attendance(att_workers['ca1'], 'in', check_in, 'GST', 'SCR')
        insert_attendance(att_workers['ca1'], 'out', check_out)

        response = client.get(
            '/api/admin/hr/attendance/today',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        ca1_record = next(
            (r for r in data['records'] if r['worker_id'] == att_workers['ca1']), None
        )
        assert ca1_record is not None
        assert ca1_record['status'] == 'left'
        assert ca1_record['check_in_time'] is not None
        assert ca1_record['check_out_time'] is not None

    def test_att04_not_checked(
        self, client, att_workers,
        create_test_admin, get_admin_auth_token
    ):
        """ATT-04: 미출근 작업자 → status='not_checked'"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        response = client.get(
            '/api/admin/hr/attendance/today',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        fni_record = next(
            (r for r in data['records'] if r['worker_id'] == att_workers['fni1']), None
        )
        assert fni_record is not None
        assert fni_record['status'] == 'not_checked'


class TestAttendanceByDate:
    """GET /api/admin/hr/attendance?date=YYYY-MM-DD"""

    def test_att05_date_param(
        self, client, att_workers, insert_attendance,
        create_test_admin, get_admin_auth_token
    ):
        """ATT-05: 날짜 파라미터 정상 동작"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        # 어제 날짜에 출근 기록 삽입
        yesterday_kst = datetime.now(KST) - timedelta(days=1)
        check_in = yesterday_kst.replace(hour=8, minute=0, second=0, microsecond=0)
        insert_attendance(att_workers['ca1'], 'in', check_in)

        yesterday_str = yesterday_kst.strftime('%Y-%m-%d')
        response = client.get(
            f'/api/admin/hr/attendance?date={yesterday_str}',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['date'] == yesterday_str
        ca1_record = next(
            (r for r in data['records'] if r['worker_id'] == att_workers['ca1']), None
        )
        assert ca1_record is not None
        assert ca1_record['status'] == 'working'

    def test_att06_invalid_date(
        self, client, create_test_admin, get_admin_auth_token
    ):
        """ATT-06: 잘못된 날짜 형식 → 400 에러"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        response = client.get(
            '/api/admin/hr/attendance?date=invalid',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'INVALID_DATE'


class TestAttendanceSummary:
    """GET /api/admin/hr/attendance/summary"""

    def test_att07_company_summary(
        self, client, att_workers, insert_attendance,
        create_test_admin, get_admin_auth_token
    ):
        """ATT-07: 회사별 집계 정확성"""
        admin = create_test_admin
        token = get_admin_auth_token(admin['id'])

        now_kst = datetime.now(KST)
        # C&A worker1: 출근+퇴근
        insert_attendance(att_workers['ca1'], 'in',
                          now_kst.replace(hour=8, minute=0, second=0, microsecond=0))
        insert_attendance(att_workers['ca1'], 'out',
                          now_kst.replace(hour=17, minute=0, second=0, microsecond=0))
        # C&A worker2: 출근만
        insert_attendance(att_workers['ca2'], 'in',
                          now_kst.replace(hour=9, minute=0, second=0, microsecond=0))
        # FNI worker: 미출근

        response = client.get(
            '/api/admin/hr/attendance/summary',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'by_company' in data

        ca_summary = next(
            (c for c in data['by_company'] if c['company'] == 'C&A'), None
        )
        assert ca_summary is not None
        # C&A: total >= 2 (기존 C&A 작업자가 있을 수도 있으므로 >=)
        assert ca_summary['total_workers'] >= 2
        assert ca_summary['checked_in'] >= 2
        assert ca_summary['checked_out'] >= 1
        assert ca_summary['currently_working'] >= 1

        fni_summary = next(
            (c for c in data['by_company'] if c['company'] == 'FNI'), None
        )
        assert fni_summary is not None
        assert fni_summary['total_workers'] >= 1
        assert fni_summary['not_checked'] >= 1


class TestAttendanceAuth:
    """권한 테스트"""

    def test_att08_non_admin_forbidden(
        self, client, create_test_worker, get_auth_token
    ):
        """ATT-08: 비관리자 접근 → 403"""
        worker_id = create_test_worker(
            email='att_test_normal@test.com', password='Test123!',
            name='Normal Worker', role='MECH', company='FNI',
        )
        token = get_auth_token(worker_id)

        for url in [
            '/api/admin/hr/attendance/today',
            '/api/admin/hr/attendance',
            '/api/admin/hr/attendance/summary',
        ]:
            response = client.get(
                url, headers={'Authorization': f'Bearer {token}'}
            )
            assert response.status_code == 403, f"Expected 403 for {url}"
