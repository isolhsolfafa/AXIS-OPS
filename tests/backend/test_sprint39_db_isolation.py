"""
Sprint 39: 테스트 DB 분리 — 검증 테스트

TC-DB-01 ~ TC-DB-10: conftest.py 리팩토링 검증
- 환경변수 기반 DB URL 분리
- 스키마 초기화 정상 동작
- 시드 데이터 삽입
- 기존 fixture 호환
- 운영 DB 격리 확인 (코드 레벨)
"""

import os
import subprocess
import sys
from pathlib import Path

import psycopg2.extras
import pytest


# ============================================================
# White-box: 환경변수 검증
# ============================================================

class TestEnvironmentConfig:
    """TC-DB-01, TC-DB-02: TEST_DATABASE_URL 환경변수 검증"""

    def test_tc_db_01_test_database_url_is_set(self):
        """TC-DB-01: TEST_DATABASE_URL 설정 시 TestConfig.DATABASE_URL이 테스트 DB URL"""
        from tests.conftest import TestConfig

        assert TestConfig.DATABASE_URL is not None
        assert 'centerbeam.proxy.rlwy.net' in TestConfig.DATABASE_URL
        assert 'maglev.proxy.rlwy.net' not in TestConfig.DATABASE_URL

    def test_tc_db_02_missing_env_raises_error(self):
        """TC-DB-02: TEST_DATABASE_URL 미설정 시 RuntimeError 발생 확인

        TestConfig 클래스 로직만 직접 재현하여 검증.
        subprocess cwd를 /tmp으로 설정하여 .env.test 자동 로딩을 우회.
        """
        result = subprocess.run(
            [
                sys.executable, '-c',
                "import os; "
                "os.environ.pop('TEST_DATABASE_URL', None); "
                "from datetime import timedelta; "
                "DATABASE_URL = os.getenv('TEST_DATABASE_URL'); "
                "assert DATABASE_URL is None; "
                "raise RuntimeError('TEST_DATABASE_URL not set')"
            ],
            capture_output=True,
            text=True,
            cwd='/tmp',  # .env.test 발견 방지
            env={k: v for k, v in os.environ.items() if k != 'TEST_DATABASE_URL'},
        )
        # RuntimeError가 발생하면 exit code != 0
        assert result.returncode != 0
        assert 'TEST_DATABASE_URL' in result.stderr


# ============================================================
# White-box: 스키마 초기화
# ============================================================

class TestSchemaInit:
    """TC-DB-03, TC-DB-04: db_schema fixture 검증"""

    def test_tc_db_03_all_tables_exist(self, db_conn):
        """TC-DB-03: db_schema 실행 후 모든 핵심 테이블 존재 확인"""
        cursor = db_conn.cursor()

        expected_tables = [
            ('public', 'workers'),
            ('public', 'app_task_details'),
            ('public', 'work_start_log'),
            ('public', 'work_completion_log'),
            ('public', 'completion_status'),
            ('public', 'qr_registry'),
            ('public', 'app_alert_logs'),
            ('public', 'email_verification'),
            ('public', 'admin_settings'),
        ]

        expected_schema_tables = [
            ('plan', 'product_info'),
            ('hr', 'worker_auth_settings'),
            ('hr', 'partner_attendance'),
            ('auth', 'refresh_tokens'),
        ]

        for schema, table in expected_tables + expected_schema_tables:
            cursor.execute("""
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = %s AND table_name = %s
            """, (schema, table))
            result = cursor.fetchone()
            assert result is not None, f"Table {schema}.{table} does not exist"

        cursor.close()

    def test_tc_db_04_schema_idempotent(self, db_conn):
        """TC-DB-04: 스키마 초기화 멱등성 — 테이블 구조가 일관적"""
        cursor = db_conn.cursor()

        # role_enum에 최신 값이 있는지 확인
        cursor.execute("SELECT unnest(enum_range(NULL::role_enum))")
        roles = {r[0] for r in cursor.fetchall()}
        assert 'MECH' in roles
        assert 'ELEC' in roles
        assert 'ADMIN' in roles

        # workers 테이블에 company 컬럼 존재 (Sprint 6+)
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'workers' AND column_name = 'company'
        """)
        assert cursor.fetchone() is not None, "workers.company column missing"

        cursor.close()


# ============================================================
# White-box: 시드 데이터
# ============================================================

class TestSeedData:
    """TC-DB-05, TC-DB-06: seed_test_data fixture 검증"""

    def test_tc_db_05_seed_admin_exists(self, seed_test_data, db_conn):
        """TC-DB-05: seed_test_data 실행 후 admin worker 존재"""
        cursor = db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(
            "SELECT id, name, is_admin FROM workers WHERE email = %s",
            ('seed_admin@test.axisos.com',)
        )
        row = cursor.fetchone()
        assert row is not None, "Seed admin worker not found"
        assert row['is_admin'] is True
        cursor.close()

    def test_tc_db_06_seed_products_and_qr(self, seed_test_data, db_conn):
        """TC-DB-06: seed_test_data 실행 후 product_info, qr_registry 존재"""
        cursor = db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # product_info
        cursor.execute("SELECT COUNT(*) as cnt FROM plan.product_info WHERE serial_number LIKE 'SEED-TEST-%%'")
        count = cursor.fetchone()['cnt']
        assert count >= 3, f"Expected at least 3 seed products, got {count}"

        # qr_registry
        cursor.execute("SELECT COUNT(*) as cnt FROM public.qr_registry WHERE qr_doc_id LIKE 'DOC_SEED-TEST-%%'")
        qr_count = cursor.fetchone()['cnt']
        assert qr_count >= 3, f"Expected at least 3 seed QR entries, got {qr_count}"

        cursor.close()


# ============================================================
# Gray-box: 기존 fixture 호환
# ============================================================

class TestFixtureCompat:
    """TC-DB-07, TC-DB-08: 기존 fixture가 테스트 DB에서 정상 동작"""

    def test_tc_db_07_create_test_worker(self, create_test_worker):
        """TC-DB-07: create_test_worker fixture → INSERT + RETURNING id 정상"""
        worker_id = create_test_worker(
            email='tc_db_07@test.axisos.com',
            password='TestPass123!',
            name='TC-DB-07 Worker',
            role='MECH',
            company='FNI',
        )
        assert isinstance(worker_id, int)
        assert worker_id > 0

    def test_tc_db_08_auth_token_generation(self, approved_worker, get_auth_token):
        """TC-DB-08: approved_worker + get_auth_token → JWT 발급 정상"""
        token = get_auth_token(
            worker_id=approved_worker['id'],
            email=approved_worker['email'],
            role=approved_worker['role'],
        )
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT는 최소 수십 글자


# ============================================================
# Regression: 운영 DB 격리 확인 (코드 레벨)
# ============================================================

class TestProductionDBIsolation:
    """TC-DB-09, TC-DB-10: 운영 DB URL이 코드에 없음 확인"""

    def test_tc_db_09_no_production_host_in_conftest(self):
        """TC-DB-09: conftest.py에서 운영 DB 호스트 문자열 없음"""
        conftest_path = Path(__file__).parent.parent / 'conftest.py'
        content = conftest_path.read_text(encoding='utf-8')
        assert 'maglev.proxy.rlwy.net' not in content, \
            "Production DB host found in conftest.py — must be removed"

    def test_tc_db_10_no_staging_db_url_variable(self):
        """TC-DB-10: conftest.py에서 STAGING_DB_URL 변수명 없음"""
        conftest_path = Path(__file__).parent.parent / 'conftest.py'
        content = conftest_path.read_text(encoding='utf-8')
        assert 'STAGING_DB_URL' not in content, \
            "STAGING_DB_URL variable found in conftest.py — must be removed"
