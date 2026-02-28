"""
Test configuration and fixtures for AXIS-OPS test suite.
테스트 설정 및 픽스처 - 모든 테스트에서 공유되는 구성 요소
"""

import pytest
import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import jwt
import bcrypt
from typing import Dict, Any, Generator, Optional


# ============================================================
# 전역 SMTP Mock (autouse=True) — 모든 테스트에서 실제 메일 발송 차단
# register API 호출 시 send_verification_email()이 실제 SMTP 서버에
# 연결하지 않도록 smtplib.SMTP / smtplib.SMTP_SSL을 전역 mock 처리
# ============================================================
@pytest.fixture(autouse=True)
def _block_smtp_globally():
    """모든 테스트에서 SMTP 실제 발송을 차단하는 전역 fixture"""
    mock_server = MagicMock()
    mock_server.__enter__ = MagicMock(return_value=mock_server)
    mock_server.__exit__ = MagicMock(return_value=False)

    with patch('smtplib.SMTP', return_value=mock_server), \
         patch('smtplib.SMTP_SSL', return_value=mock_server):
        yield mock_server


# 테스트 환경 변수 설정 (Config 임포트 전에 설정 → Config.JWT_SECRET_KEY에 반영됨)
os.environ['JWT_SECRET_KEY'] = 'test-secret-key-do-not-use-in-production'

# Staging DB URL
STAGING_DB_URL = (
    'postgresql://postgres:aemQKKvZhddWGlLUsAghiWAlzFkoWugL'
    '@maglev.proxy.rlwy.net:38813/railway'
)


class TestConfig:
    """테스트 전용 설정"""
    TESTING = True
    DEBUG = True
    JWT_SECRET_KEY = 'test-secret-key-do-not-use-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # DB 연결: TEST_DATABASE_URL → DATABASE_URL → Staging DB
    DATABASE_URL = os.getenv(
        'TEST_DATABASE_URL',
        os.getenv('DATABASE_URL', STAGING_DB_URL)
    )


def _parse_db_url(db_url: str) -> dict:
    """DB URL 파싱 헬퍼"""
    from urllib.parse import urlparse
    result = urlparse(db_url)
    return {
        'host': result.hostname,
        'port': result.port,
        'user': result.username,
        'password': result.password,
        'database': result.path[1:]
    }


def _split_sql_statements(sql: str) -> list:
    """
    SQL 파일을 개별 문장으로 분리 (PL/pgSQL $$ 블록 안의 ';'은 분리하지 않음).

    psycopg2의 cursor.execute는 한 번에 하나의 문장만 실행하므로,
    SQL 파일을 세미콜론으로 분리해야 하되, dollar-quote 블록($$...$$) 내부의
    세미콜론은 분리 기준에서 제외해야 함.
    """
    statements = []
    current = []
    in_dollar_quote = False
    dollar_tag = ''
    i = 0
    lines = sql.splitlines(keepends=True)
    text = sql

    # 단순 상태 머신으로 $$ 추적
    pos = 0
    length = len(text)
    stmt_start = 0

    while pos < length:
        # dollar-quote 시작/종료 감지
        if text[pos] == '$':
            # dollar tag 찾기: $tag$ 또는 $$
            end = text.find('$', pos + 1)
            if end != -1:
                tag = text[pos:end + 1]
                if not in_dollar_quote:
                    in_dollar_quote = True
                    dollar_tag = tag
                    pos = end + 1
                    continue
                elif tag == dollar_tag:
                    in_dollar_quote = False
                    dollar_tag = ''
                    pos = end + 1
                    continue

        # 문장 종료 감지 (dollar-quote 밖의 ';')
        if text[pos] == ';' and not in_dollar_quote:
            stmt = text[stmt_start:pos].strip()
            if stmt:
                statements.append(stmt)
            stmt_start = pos + 1

        pos += 1

    # 마지막 남은 문장
    remaining = text[stmt_start:].strip()
    if remaining:
        statements.append(remaining)

    return statements


# Session-scoped: DB 스키마 초기화 (migrations 실행)
@pytest.fixture(scope='session')
def db_schema():
    """
    데이터베이스 스키마 초기화 (session-scoped)
    migrations/*.sql 파일을 순서대로 실행
    deadlock 발생 시 최대 3회 재시도
    """
    import time as _time

    db_url = TestConfig.DATABASE_URL

    if db_url.startswith('sqlite'):
        yield
        return

    def _execute_migrations():
        """스키마 DROP 후 migrations 재실행 (기존 worker 데이터 보존)"""
        params = _parse_db_url(db_url)
        conn = psycopg2.connect(**params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        try:
            # ── 기존 worker 데이터 백업 (실서비스 계정 보존) ──
            backed_up_workers = []
            backed_up_auth_settings = []
            try:
                cursor.execute(
                    "SELECT id, name, email, password_hash, role::text, "
                    "approval_status::text, email_verified, is_manager, is_admin, "
                    "company, active_role "
                    "FROM workers"
                )
                backed_up_workers = cursor.fetchall()
                print(f"[db_schema] Backed up {len(backed_up_workers)} workers")

                # hr.worker_auth_settings 백업 (PIN 설정)
                cursor.execute(
                    "SELECT worker_id, pin_hash, biometric_enabled, biometric_type, "
                    "pin_fail_count, pin_locked_until "
                    "FROM hr.worker_auth_settings"
                )
                backed_up_auth_settings = cursor.fetchall()
                print(f"[db_schema] Backed up {len(backed_up_auth_settings)} auth settings")
            except Exception as backup_err:
                print(f"[db_schema] Worker backup skipped (table may not exist): {backup_err}")

            # 기존 스키마 정리 (재실행 대비) - Sprint 6 + Sprint 11 + Sprint 12 테이블 포함
            drop_stmts = [
                "DROP SCHEMA IF EXISTS checklist CASCADE",
                "DROP SCHEMA IF EXISTS hr CASCADE",
                "DROP TABLE IF EXISTS location_history CASCADE",
                "DROP TABLE IF EXISTS offline_sync_queue CASCADE",
                "DROP TABLE IF EXISTS app_alert_logs CASCADE",
                "DROP TABLE IF EXISTS work_pause_log CASCADE",
                "DROP TABLE IF EXISTS work_completion_log CASCADE",
                "DROP TABLE IF EXISTS work_start_log CASCADE",
                "DROP TABLE IF EXISTS completion_status CASCADE",
                "DROP TABLE IF EXISTS app_task_details CASCADE",
                "DROP TABLE IF EXISTS email_verification CASCADE",
                "DROP TABLE IF EXISTS product_info CASCADE",
                "DROP TABLE IF EXISTS admin_settings CASCADE",
                "DROP TABLE IF EXISTS model_config CASCADE",
                "DROP TABLE IF EXISTS workers CASCADE",
                "DROP TYPE IF EXISTS alert_type_enum CASCADE",
                "DROP TYPE IF EXISTS alert_type_enum_new CASCADE",
                "DROP TYPE IF EXISTS role_enum CASCADE",
                "DROP TYPE IF EXISTS role_enum_new CASCADE",
                "DROP TYPE IF EXISTS approval_status_enum CASCADE",
                "DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE",
            ]
            for stmt in drop_stmts:
                cursor.execute(stmt)

            # migrations 디렉토리
            migrations_dir = Path(__file__).parent.parent / 'backend' / 'migrations'

            migration_files = [
                '001_create_workers.sql',
                '002_create_product_info.sql',
                '003_create_task_tables.sql',
                '004_create_alert_tables.sql',
                '005_create_sync_tables.sql',
                '006_sprint6_schema_changes.sql',
                '008_sprint9_pause_resume.sql',
                '009_sprint11_gst_tasks.sql',
                '010_sprint12_hr_schema.sql',
            ]

            for filename in migration_files:
                filepath = migrations_dir / filename
                if filepath.exists():
                    with open(filepath, 'r', encoding='utf-8') as f:
                        sql = f.read()
                    # psycopg2는 cursor.execute에 여러 문장을 한번에 넘기면
                    # 첫 번째 문장만 실행하므로 파일을 세미콜론으로 분리해서 실행.
                    # 단, $$...$$로 감싸진 PL/pgSQL 블록 내부 ';'은 분리하지 않도록
                    # dollar-quote 상태를 추적하여 분리
                    statements = _split_sql_statements(sql)
                    for stmt in statements:
                        # BEGIN/COMMIT/ROLLBACK은 autocommit 모드에서 불필요하므로 건너뜀
                        # 주석 제거 후 실제 SQL 키워드 확인
                        non_comment_lines = [
                            line for line in stmt.splitlines()
                            if line.strip() and not line.strip().startswith('--')
                        ]
                        effective_stmt = ' '.join(non_comment_lines).strip().upper()
                        if effective_stmt in ('BEGIN', 'COMMIT', 'ROLLBACK'):
                            continue
                        try:
                            cursor.execute(stmt)
                        except Exception as stmt_err:
                            # 개별 문장 실패 시 경고만 출력하고 계속 진행
                            print(f"Warning: Migration stmt failed in {filename}: {stmt_err}")
            # ── 백업된 worker 데이터 복원 ──
            if backed_up_workers:
                restored = 0
                for row in backed_up_workers:
                    try:
                        cursor.execute(
                            """
                            INSERT INTO workers (id, name, email, password_hash, role,
                                approval_status, email_verified, is_manager, is_admin,
                                company, active_role)
                            VALUES (%s, %s, %s, %s, %s::role_enum,
                                %s::approval_status_enum, %s, %s, %s,
                                %s, %s)
                            ON CONFLICT (id) DO NOTHING
                            """,
                            row
                        )
                        restored += 1
                    except Exception as restore_err:
                        print(f"[db_schema] Worker restore failed for id={row[0]}: {restore_err}")

                # id 시퀀스를 최대값으로 조정
                cursor.execute(
                    "SELECT setval('workers_id_seq', COALESCE((SELECT MAX(id) FROM workers), 1))"
                )
                print(f"[db_schema] Restored {restored}/{len(backed_up_workers)} workers")

            # hr.worker_auth_settings 복원
            if backed_up_auth_settings:
                restored_auth = 0
                for row in backed_up_auth_settings:
                    try:
                        cursor.execute(
                            """
                            INSERT INTO hr.worker_auth_settings
                                (worker_id, pin_hash, biometric_enabled, biometric_type,
                                 pin_fail_count, pin_locked_until)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (worker_id) DO NOTHING
                            """,
                            row
                        )
                        restored_auth += 1
                    except Exception as auth_err:
                        print(f"[db_schema] Auth settings restore failed: {auth_err}")
                print(f"[db_schema] Restored {restored_auth}/{len(backed_up_auth_settings)} auth settings")

        finally:
            cursor.close()
            conn.close()

    # deadlock 시 최대 3회 재시도
    max_retries = 3
    for attempt in range(max_retries):
        try:
            _execute_migrations()
            break  # 성공
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Warning: Schema init attempt {attempt+1} failed (retry): {e}")
                _time.sleep(3)
            else:
                print(f"Warning: Schema initialization failed after {max_retries} attempts: {e}")

    yield


# Function-scoped: DB 연결 및 트랜잭션 관리
@pytest.fixture
def db_conn(db_schema):
    """
    테스트용 DB 연결
    각 테스트마다 독립 연결 제공 (fixture 데이터는 commit, teardown에서 정리)

    Yields:
        psycopg2 connection
    """
    db_url = TestConfig.DATABASE_URL

    if db_url.startswith('sqlite'):
        yield None
        return

    params = _parse_db_url(db_url)
    conn = psycopg2.connect(**params)
    conn.autocommit = False

    yield conn

    if not conn.closed:
        conn.close()


# Flask 테스트 앱
@pytest.fixture
def app():
    """
    Flask 테스트 애플리케이션 생성
    backend/app/__init__.py의 create_app() 사용
    """
    import sys
    backend_path = str(Path(__file__).parent.parent / 'backend')
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    from app import create_app

    test_app = create_app(TestConfig)

    yield test_app


# Flask 테스트 클라이언트
@pytest.fixture
def client(app):
    """Flask 테스트 클라이언트"""
    return app.test_client()


# Sprint 6 전/후 role 이름 매핑 헬퍼
SPRINT6_ROLE_MAP = {
    'MECH': 'MM',   # Sprint 6 → Sprint 5 이전
    'ELEC': 'EE',
    'TMS': 'TM',
    'ADMIN': 'PI',  # ADMIN 역할 없을 때 PI fallback
}
SPRINT6_ROLE_MAP_REVERSE = {v: k for k, v in SPRINT6_ROLE_MAP.items()}


@pytest.fixture(scope='session')
def db_existing_roles():
    """현재 DB의 role_enum 값 목록 반환 (Sprint 6 마이그레이션 여부 확인용)"""
    try:
        conn = psycopg2.connect(STAGING_DB_URL)
        cur = conn.cursor()
        cur.execute("SELECT unnest(enum_range(NULL::role_enum))")
        roles = {r[0] for r in cur.fetchall()}
        cur.close()
        conn.close()
        return roles
    except Exception:
        return {'MM', 'EE', 'TM', 'PI', 'QI', 'SI'}  # 기본값


@pytest.fixture(scope='session')
def has_sprint6_schema():
    """
    Sprint 6 DB 마이그레이션 완료 여부 확인
    - completion_status에 mech_completed 컬럼 존재
    - workers에 company 컬럼 존재
    - role_enum에 MECH 값 존재
    """
    try:
        conn = psycopg2.connect(STAGING_DB_URL)
        cur = conn.cursor()
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='completion_status' AND column_name='mech_completed'")
        has_mech_col = cur.fetchone() is not None
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='workers' AND column_name='company'")
        has_company = cur.fetchone() is not None
        cur.execute("SELECT 1 FROM pg_enum JOIN pg_type ON pg_enum.enumtypid=pg_type.oid WHERE pg_type.typname='role_enum' AND pg_enum.enumlabel='MECH'")
        has_mech_role = cur.fetchone() is not None
        cur.close()
        conn.close()
        return has_mech_col and has_company and has_mech_role
    except Exception:
        return False


# JWT 토큰 생성 헬퍼
@pytest.fixture
def get_auth_token():
    """
    JWT 토큰 생성 헬퍼 함수 (auth_service.create_access_token과 동일 형식)

    Returns:
        Function(worker_id, email, role, expires_in_hours) -> JWT token string
    """
    def _generate_token(
        worker_id: int,
        email: str = '',
        role: str = 'MECH',
        is_admin: bool = False,
        expires_in_hours: int = 1
    ) -> str:
        if not email:
            email = f'worker{worker_id}@test.axisos.com'

        payload = {
            'sub': str(worker_id),
            'email': email,
            'role': role,
            'is_admin': is_admin,
            'exp': datetime.utcnow() + timedelta(hours=expires_in_hours),
            'iat': datetime.utcnow()
        }

        return jwt.encode(
            payload,
            TestConfig.JWT_SECRET_KEY,
            algorithm='HS256'
        )

    return _generate_token


# 샘플 워커 데이터 로딩
@pytest.fixture
def sample_workers() -> list[Dict[str, Any]]:
    """tests/fixtures/sample_workers.json 로딩"""
    fixtures_path = Path(__file__).parent / 'fixtures' / 'sample_workers.json'

    with open(fixtures_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# 테스트 워커 생성 헬퍼
@pytest.fixture
def create_test_worker(db_conn):
    """
    테스트 워커 생성 헬퍼 함수 (commit + teardown 정리)

    Returns:
        Function(email, password, name, role, approval_status, email_verified, is_manager, is_admin) -> worker_id
    """
    created_worker_ids = []

    def _create_worker(
        email: str,
        password: str,
        name: str,
        role: str = 'MECH',
        approval_status: str = 'approved',
        email_verified: bool = True,
        is_manager: bool = False,
        is_admin: bool = False,
        company: Optional[str] = None
    ) -> int:
        if db_conn is None:
            return 999

        password_hash = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

        cursor = db_conn.cursor()

        # role_enum 실제 값 확인 (Sprint 6 전/후 호환)
        # InternalError_ (cache lookup failed) 발생 시 별도 연결로 재시도
        try:
            cursor.execute("SELECT unnest(enum_range(NULL::role_enum))")
            existing_roles = {r[0] for r in cursor.fetchall()}
        except Exception:
            # 타입 캐시 오염 시 별도 연결로 조회
            try:
                db_conn.rollback()
                cursor.close()
                cursor = db_conn.cursor()
                cursor.execute("SELECT unnest(enum_range(NULL::role_enum))")
                existing_roles = {r[0] for r in cursor.fetchall()}
            except Exception:
                # 최후 폴백: Sprint 11 기준 role_enum 값
                existing_roles = {'MECH', 'ELEC', 'TM', 'PI', 'QI', 'SI', 'ADMIN'}

        # Sprint 6 전/후 role 이름 호환 매핑
        # Sprint 6 이전 DB: MECH→MM, ELEC→EE, ADMIN→PI (downgrade)
        # Sprint 6 이후 DB: MM→MECH, EE→ELEC, TM→TM (upgrade)
        role_fallback_map = {'MECH': 'MM', 'ELEC': 'EE', 'ADMIN': 'PI', 'TMS': 'TM'}
        role_upgrade_map = {'MM': 'MECH', 'EE': 'ELEC'}  # 구버전 코드가 새 DB에 접근할 때
        db_role = role
        if role not in existing_roles:
            if role in role_fallback_map:
                db_role = role_fallback_map[role]
            elif role in role_upgrade_map:
                db_role = role_upgrade_map[role]

        # company 컬럼 존재 여부 확인 (Sprint 6 마이그레이션 유무)
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='workers' AND column_name='company'
        """)
        has_company_col = cursor.fetchone() is not None

        if has_company_col:
            cursor.execute("""
                INSERT INTO workers (name, email, password_hash, role, company, approval_status,
                                     email_verified, is_manager, is_admin)
                VALUES (%s, %s, %s, %s::role_enum, %s, %s::approval_status_enum, %s, %s, %s)
                RETURNING id
            """, (name, email, password_hash, db_role, company, approval_status,
                  email_verified, is_manager, is_admin))
        else:
            cursor.execute("""
                INSERT INTO workers (name, email, password_hash, role, approval_status,
                                     email_verified, is_manager, is_admin)
                VALUES (%s, %s, %s, %s::role_enum, %s::approval_status_enum, %s, %s, %s)
                RETURNING id
            """, (name, email, password_hash, db_role, approval_status,
                  email_verified, is_manager, is_admin))

        worker_id = cursor.fetchone()[0]
        created_worker_ids.append(worker_id)
        db_conn.commit()
        cursor.close()

        return worker_id

    yield _create_worker

    # Cleanup: 테스트 워커 및 관련 데이터 삭제 (FK 의존 순서 준수)
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            for worker_id in created_worker_ids:
                # 0. hr 스키마 (Sprint 12) — workers 삭제 전에 먼저 정리
                try:
                    cursor.execute("DELETE FROM hr.worker_auth_settings WHERE worker_id = %s", (worker_id,))
                except Exception:
                    db_conn.rollback()
                try:
                    cursor.execute("DELETE FROM hr.partner_attendance WHERE worker_id = %s", (worker_id,))
                except Exception:
                    db_conn.rollback()
                # 1. checklist_record (checked_by FK)
                try:
                    cursor.execute("DELETE FROM checklist.checklist_record WHERE checked_by = %s", (worker_id,))
                except Exception:
                    db_conn.rollback()
                # 2. work_pause_log → work_start_log → work_completion_log (task FK 먼저)
                try:
                    cursor.execute("DELETE FROM work_pause_log WHERE worker_id = %s", (worker_id,))
                    cursor.execute("DELETE FROM work_start_log WHERE worker_id = %s", (worker_id,))
                    cursor.execute("DELETE FROM work_completion_log WHERE worker_id = %s", (worker_id,))
                except Exception:
                    db_conn.rollback()
                # 3. app_alert_logs (triggered_by / target FK)
                try:
                    cursor.execute("DELETE FROM app_alert_logs WHERE triggered_by_worker_id = %s OR target_worker_id = %s", (worker_id, worker_id))
                except Exception:
                    db_conn.rollback()
                # 4. app_task_details (worker_id FK)
                try:
                    cursor.execute("DELETE FROM app_task_details WHERE worker_id = %s", (worker_id,))
                except Exception:
                    db_conn.rollback()
                # 5. email_verification + workers
                try:
                    cursor.execute("DELETE FROM email_verification WHERE worker_id = %s", (worker_id,))
                    cursor.execute("DELETE FROM workers WHERE id = %s", (worker_id,))
                except Exception:
                    db_conn.rollback()
            db_conn.commit()
            cursor.close()
        except Exception as e:
            print(f"Warning: Worker cleanup failed: {e}")


# 승인된 테스트 워커 (기본)
@pytest.fixture
def approved_worker(create_test_worker) -> Dict[str, Any]:
    """승인된 테스트 워커 생성"""
    worker_data = {
        'email': 'approved_worker@test.axisos.com',
        'password': 'TestPassword123!',
        'name': 'Approved Test Worker',
        'role': 'MECH',
        'approval_status': 'approved',
        'email_verified': True
    }

    worker_id = create_test_worker(**worker_data)
    worker_data['id'] = worker_id

    return worker_data


# 미승인 워커
@pytest.fixture
def unapproved_worker(create_test_worker) -> Dict[str, Any]:
    """미승인 테스트 워커 생성 (승인 대기)"""
    worker_data = {
        'email': 'unapproved_worker@test.axisos.com',
        'password': 'TestPassword123!',
        'name': 'Unapproved Test Worker',
        'role': 'PI',
        'approval_status': 'pending',
        'email_verified': True
    }

    worker_id = create_test_worker(**worker_data)
    worker_data['id'] = worker_id

    return worker_data


# 관리자 워커
@pytest.fixture
def admin_worker(create_test_worker) -> Dict[str, Any]:
    """시스템 관리자 워커 생성"""
    worker_data = {
        'email': 'admin@test.axisos.com',
        'password': 'AdminPassword123!',
        'name': 'Test Admin',
        'role': 'QI',
        'approval_status': 'approved',
        'email_verified': True,
        'is_admin': True
    }

    worker_id = create_test_worker(**worker_data)
    worker_data['id'] = worker_id

    return worker_data


# 샘플 QR 코드
@pytest.fixture
def sample_qr_code() -> Dict[str, str]:
    """테스트용 샘플 QR 코드 데이터"""
    return {
        'qr_doc_id': 'DOC_GBWS-TEST-001',
        'serial_number': 'GBWS-TEST-001',
        'location_qr_id': 'LOC_STATION_A'
    }


# 타임존 설정 (KST)
@pytest.fixture(scope='session', autouse=True)
def set_timezone():
    """테스트 타임존을 KST로 설정"""
    original_tz = os.environ.get('TZ')
    os.environ['TZ'] = 'Asia/Seoul'

    try:
        import time
        time.tzset()
    except AttributeError:
        pass

    yield

    if original_tz:
        os.environ['TZ'] = original_tz
    else:
        os.environ.pop('TZ', None)


# ==================== Sprint 2 픽스처 ====================


# 샘플 제품 데이터 로딩
@pytest.fixture
def sample_products() -> list[Dict[str, Any]]:
    """tests/fixtures/sample_products.json 로딩"""
    fixtures_path = Path(__file__).parent / 'fixtures' / 'sample_products.json'

    with open(fixtures_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# 샘플 작업 데이터 로딩
@pytest.fixture
def sample_tasks() -> list[Dict[str, Any]]:
    """tests/fixtures/sample_tasks.json 로딩"""
    fixtures_path = Path(__file__).parent / 'fixtures' / 'sample_tasks.json'

    with open(fixtures_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# 샘플 완료 상태 데이터 로딩
@pytest.fixture
def sample_completion_status() -> list[Dict[str, Any]]:
    """tests/fixtures/sample_completion_status.json 로딩"""
    fixtures_path = Path(__file__).parent / 'fixtures' / 'sample_completion_status.json'

    with open(fixtures_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# 테스트 제품 생성 헬퍼
@pytest.fixture
def create_test_product(db_conn):
    """
    테스트 제품 생성 헬퍼 함수 (commit + teardown 정리)

    Returns:
        Function(qr_doc_id, serial_number, model, production_date, location_qr_id,
                 mech_partner, module_outsourcing) -> product_id
    """
    created_qr_doc_ids = []

    def _create_product(
        qr_doc_id: str,
        serial_number: str,
        model: str = 'GALLANT-50',
        production_date: str = '2025-02-15',
        location_qr_id: Optional[str] = None,
        mech_partner: Optional[str] = 'FNI',
        elec_partner: Optional[str] = 'P&S',
        module_outsourcing: Optional[str] = None
    ) -> int:
        if db_conn is None:
            return 999

        cursor = db_conn.cursor()

        # plan.product_info에 제품 메타데이터 삽입
        cursor.execute("""
            INSERT INTO plan.product_info (
                serial_number, model, mech_partner, elec_partner,
                module_outsourcing, location_qr_id, prod_date
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (serial_number) DO NOTHING
            RETURNING id
        """, (serial_number, model, mech_partner, elec_partner,
              module_outsourcing, location_qr_id, production_date))

        row = cursor.fetchone()
        product_id = row[0] if row else -1

        # qr_registry에 QR 매핑 삽입
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number)
            VALUES (%s, %s)
            ON CONFLICT (qr_doc_id) DO NOTHING
        """, (qr_doc_id, serial_number))

        created_qr_doc_ids.append(qr_doc_id)
        db_conn.commit()
        cursor.close()

        return product_id

    yield _create_product

    # Cleanup: 테스트 제품 및 관련 데이터 삭제
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            for qr_doc_id in created_qr_doc_ids:
                # qr_registry에서 serial_number 조회 후 cascade 삭제
                cursor.execute(
                    "SELECT serial_number FROM public.qr_registry WHERE qr_doc_id = %s",
                    (qr_doc_id,)
                )
                row = cursor.fetchone()
                if row:
                    sn = row[0]
                    cursor.execute(
                        "DELETE FROM public.qr_registry WHERE qr_doc_id = %s",
                        (qr_doc_id,)
                    )
                    cursor.execute(
                        "DELETE FROM plan.product_info WHERE serial_number = %s",
                        (sn,)
                    )
            db_conn.commit()
            cursor.close()
        except Exception as e:
            print(f"Warning: Product cleanup failed: {e}")


# 테스트 작업 생성 헬퍼
@pytest.fixture
def create_test_task(db_conn):
    """
    테스트 작업 생성 헬퍼 함수 (commit + teardown 정리)

    Returns:
        Function(worker_id, serial_number, qr_doc_id, task_category, task_id, task_name,
                 started_at, completed_at, duration_minutes, is_applicable) -> task_detail_id
    """
    created_task_ids = []

    def _create_task(
        worker_id: int,
        serial_number: str,
        qr_doc_id: str,
        task_category: str,
        task_id: str,
        task_name: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        duration_minutes: Optional[int] = None,
        is_applicable: bool = True
    ) -> int:
        if db_conn is None:
            return 999

        cursor = db_conn.cursor()

        cursor.execute("""
            INSERT INTO app_task_details (
                worker_id, serial_number, qr_doc_id, task_category,
                task_id, task_name, started_at, completed_at,
                duration_minutes, is_applicable
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (worker_id, serial_number, qr_doc_id, task_category,
              task_id, task_name, started_at, completed_at,
              duration_minutes, is_applicable))

        task_detail_id = cursor.fetchone()[0]
        created_task_ids.append(task_detail_id)

        # Sprint 6 Phase C: work_start_log에도 시작 기록 삽입 (멀티 작업자 지원)
        # BE complete_work는 work_start_log를 기반으로 작업자 권한을 확인함
        if started_at is not None:
            cursor.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_name = 'work_start_log'
            """)
            has_start_log = cursor.fetchone() is not None
            if has_start_log:
                cursor.execute("""
                    INSERT INTO work_start_log
                        (task_id, worker_id, serial_number, qr_doc_id,
                         task_category, task_id_ref, task_name, started_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (task_detail_id, worker_id, serial_number, qr_doc_id,
                      task_category, task_id, task_name, started_at))

        db_conn.commit()
        cursor.close()

        return task_detail_id

    yield _create_task

    # Cleanup: 테스트 작업 삭제
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            for task_id in created_task_ids:
                # work_pause_log, work_start_log, work_completion_log 먼저 삭제 (FK 의존성)
                cursor.execute(
                    "DELETE FROM work_pause_log WHERE task_detail_id = %s",
                    (task_id,)
                )
                cursor.execute(
                    "DELETE FROM work_start_log WHERE task_id = %s",
                    (task_id,)
                )
                cursor.execute(
                    "DELETE FROM work_completion_log WHERE task_id = %s",
                    (task_id,)
                )
                cursor.execute(
                    "DELETE FROM app_task_details WHERE id = %s",
                    (task_id,)
                )
            db_conn.commit()
            cursor.close()
        except Exception as e:
            print(f"Warning: Task cleanup failed: {e}")


# 테스트 완료 상태 생성 헬퍼
@pytest.fixture
def create_test_completion_status(db_conn):
    """
    테스트 완료 상태 생성 헬퍼 함수 (commit + teardown 정리)

    Returns:
        Function(serial_number, mm_completed, ee_completed, tm_completed,
                 pi_completed, qi_completed, si_completed) -> serial_number
    """
    created_serial_numbers = []

    def _create_completion_status(
        serial_number: str,
        mech_completed: bool = False,
        elec_completed: bool = False,
        tm_completed: bool = False,
        pi_completed: bool = False,
        qi_completed: bool = False,
        si_completed: bool = False
    ) -> str:
        if db_conn is None:
            return serial_number

        cursor = db_conn.cursor()

        # mech_completed vs mm_completed 컬럼 호환성 확인 (Sprint 6 전/후)
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='completion_status' AND column_name='mech_completed'
        """)
        has_mech_col = cursor.fetchone() is not None

        if has_mech_col:
            cursor.execute("""
                INSERT INTO completion_status (
                    serial_number, mech_completed, elec_completed, tm_completed,
                    pi_completed, qi_completed, si_completed
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (serial_number) DO UPDATE
                SET mech_completed = EXCLUDED.mech_completed,
                    elec_completed = EXCLUDED.elec_completed,
                    tm_completed = EXCLUDED.tm_completed,
                    pi_completed = EXCLUDED.pi_completed,
                    qi_completed = EXCLUDED.qi_completed,
                    si_completed = EXCLUDED.si_completed
            """, (serial_number, mech_completed, elec_completed, tm_completed,
                  pi_completed, qi_completed, si_completed))
        else:
            # Sprint 6 이전: mm_completed, ee_completed 컬럼 사용
            cursor.execute("""
                INSERT INTO completion_status (
                    serial_number, mm_completed, ee_completed, tm_completed,
                    pi_completed, qi_completed, si_completed
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (serial_number) DO UPDATE
                SET mm_completed = EXCLUDED.mm_completed,
                    ee_completed = EXCLUDED.ee_completed,
                    tm_completed = EXCLUDED.tm_completed,
                    pi_completed = EXCLUDED.pi_completed,
                    qi_completed = EXCLUDED.qi_completed,
                    si_completed = EXCLUDED.si_completed
            """, (serial_number, mech_completed, elec_completed, tm_completed,
                  pi_completed, qi_completed, si_completed))

        created_serial_numbers.append(serial_number)
        db_conn.commit()
        cursor.close()

        return serial_number

    yield _create_completion_status

    # Cleanup: 테스트 완료 상태 삭제
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            for sn in created_serial_numbers:
                cursor.execute(
                    "DELETE FROM completion_status WHERE serial_number = %s",
                    (sn,)
                )
            db_conn.commit()
            cursor.close()
        except Exception as e:
            print(f"Warning: Completion status cleanup failed: {e}")


# ==================== Sprint 3 픽스처 ====================


# 샘플 알림 데이터 로딩
@pytest.fixture
def sample_alerts() -> list[Dict[str, Any]]:
    """tests/fixtures/sample_alerts.json 로딩"""
    fixtures_path = Path(__file__).parent / 'fixtures' / 'sample_alerts.json'

    with open(fixtures_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# 관리자 워커 (is_manager=True)
@pytest.fixture
def manager_worker(create_test_worker) -> Dict[str, Any]:
    """MM 관리자 워커 생성 (is_manager=True)"""
    worker_data = {
        'email': 'mech_manager@test.axisos.com',
        'password': 'ManagerPass123!',
        'name': 'MECH Manager',
        'role': 'MECH',
        'company': 'FNI',
        'approval_status': 'approved',
        'email_verified': True,
        'is_manager': True
    }

    worker_id = create_test_worker(**worker_data)
    worker_data['id'] = worker_id

    return worker_data


# ELEC 관리자 워커
@pytest.fixture
def elec_manager_worker(create_test_worker) -> Dict[str, Any]:
    """ELEC 관리자 워커 생성 (is_manager=True)"""
    worker_data = {
        'email': 'elec_manager@test.axisos.com',
        'password': 'ManagerPass123!',
        'name': 'ELEC Manager',
        'role': 'ELEC',
        'company': 'P&S',
        'approval_status': 'approved',
        'email_verified': True,
        'is_manager': True
    }

    worker_id = create_test_worker(**worker_data)
    worker_data['id'] = worker_id

    return worker_data


# PI 작업자
@pytest.fixture
def pi_worker(create_test_worker) -> Dict[str, Any]:
    """PI 작업자 생성"""
    worker_data = {
        'email': 'pi_worker@test.axisos.com',
        'password': 'PIWorker123!',
        'name': 'PI Worker',
        'role': 'PI',
        'approval_status': 'approved',
        'email_verified': True
    }

    worker_id = create_test_worker(**worker_data)
    worker_data['id'] = worker_id

    return worker_data


# QI 작업자
@pytest.fixture
def qi_worker(create_test_worker) -> Dict[str, Any]:
    """QI 작업자 생성"""
    worker_data = {
        'email': 'qi_worker@test.axisos.com',
        'password': 'QIWorker123!',
        'name': 'QI Worker',
        'role': 'QI',
        'approval_status': 'approved',
        'email_verified': True
    }

    worker_id = create_test_worker(**worker_data)
    worker_data['id'] = worker_id

    return worker_data


# SI 작업자
@pytest.fixture
def si_worker(create_test_worker) -> Dict[str, Any]:
    """SI 작업자 생성"""
    worker_data = {
        'email': 'si_worker@test.axisos.com',
        'password': 'SIWorker123!',
        'name': 'SI Worker',
        'role': 'SI',
        'approval_status': 'approved',
        'email_verified': True
    }

    worker_id = create_test_worker(**worker_data)
    worker_data['id'] = worker_id

    return worker_data


# 테스트 알림 생성 헬퍼
@pytest.fixture
def create_test_alert(db_conn):
    """
    테스트 알림 생성 헬퍼 함수 (commit + teardown 정리)

    Returns:
        Function(alert_type, message, serial_number, qr_doc_id,
                 triggered_by_worker_id, target_worker_id, target_role) -> alert_id
    """
    created_alert_ids = []

    def _create_alert(
        alert_type: str,
        message: str,
        serial_number: Optional[str] = None,
        qr_doc_id: Optional[str] = None,
        triggered_by_worker_id: Optional[int] = None,
        target_worker_id: Optional[int] = None,
        target_role: Optional[str] = None
    ) -> int:
        if db_conn is None:
            return 999

        cursor = db_conn.cursor()

        cursor.execute("""
            INSERT INTO app_alert_logs (
                alert_type, message, serial_number, qr_doc_id,
                triggered_by_worker_id, target_worker_id, target_role
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (alert_type, message, serial_number, qr_doc_id,
              triggered_by_worker_id, target_worker_id, target_role))

        alert_id = cursor.fetchone()[0]
        created_alert_ids.append(alert_id)
        db_conn.commit()
        cursor.close()

        return alert_id

    yield _create_alert

    # Cleanup: 테스트 알림 삭제
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            for alert_id in created_alert_ids:
                cursor.execute(
                    "DELETE FROM app_alert_logs WHERE id = %s",
                    (alert_id,)
                )
            db_conn.commit()
            cursor.close()
        except Exception as e:
            print(f"Warning: Alert cleanup failed: {e}")


# ==================== Sprint 4 픽스처 ====================


# 관리자 워커 생성 헬퍼 (is_admin=True)
@pytest.fixture
def create_test_admin(create_test_worker) -> Dict[str, Any]:
    """
    시스템 관리자 워커 생성 (is_admin=True)
    Sprint 4 admin API 테스트용
    """
    admin_data = {
        'email': 'admin_sprint4@test.axisos.com',
        'password': 'AdminPass123!',
        'name': 'Sprint4 Admin',
        'role': 'QI',
        'approval_status': 'approved',
        'email_verified': True,
        'is_admin': True
    }

    worker_id = create_test_worker(**admin_data)
    admin_data['id'] = worker_id

    return admin_data


# 승인 대기 워커 생성 헬퍼
@pytest.fixture
def create_pending_worker(create_test_worker) -> Dict[str, Any]:
    """
    승인 대기 워커 생성 (approval_status='pending')
    관리자 승인 API 테스트용
    """
    pending_data = {
        'email': 'pending_worker@test.axisos.com',
        'password': 'PendingPass123!',
        'name': 'Pending Worker',
        'role': 'MM',
        'approval_status': 'pending',
        'email_verified': True
    }

    worker_id = create_test_worker(**pending_data)
    pending_data['id'] = worker_id

    return pending_data


# 관리자 JWT 토큰 생성 헬퍼
@pytest.fixture
def get_admin_auth_token(get_auth_token):
    """
    관리자 JWT 토큰 생성 헬퍼 (is_admin 플래그 포함)

    Returns:
        Function(worker_id, email, role, is_admin, expires_in_hours) -> JWT token string
    """
    def _generate_admin_token(
        worker_id: int,
        email: str = '',
        role: str = 'QI',
        is_admin: bool = True,
        expires_in_hours: int = 1
    ) -> str:
        if not email:
            email = f'admin{worker_id}@test.axisos.com'

        payload = {
            'sub': str(worker_id),
            'email': email,
            'role': role,
            'is_admin': is_admin,
            'exp': datetime.utcnow() + timedelta(hours=expires_in_hours),
            'iat': datetime.utcnow()
        }

        return jwt.encode(
            payload,
            TestConfig.JWT_SECRET_KEY,
            algorithm='HS256'
        )

    return _generate_admin_token


# 테스트 동기화 레코드 생성 헬퍼
@pytest.fixture
def create_test_sync_record(db_conn):
    """
    테스트 동기화 레코드 생성 헬퍼 함수 (commit + teardown 정리)

    Returns:
        Function(worker_id, operation, table_name, record_id, data, synced) -> sync_id
    """
    created_sync_ids = []

    def _create_sync_record(
        worker_id: int,
        operation: str,
        table_name: str,
        record_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        synced: bool = False
    ) -> int:
        if db_conn is None:
            return 999

        cursor = db_conn.cursor()

        import json
        data_json = json.dumps(data) if data else None

        cursor.execute("""
            INSERT INTO offline_sync_queue (
                worker_id, operation, table_name, record_id, data, synced
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (worker_id, operation, table_name, record_id, data_json, synced))

        sync_id = cursor.fetchone()[0]
        created_sync_ids.append(sync_id)
        db_conn.commit()
        cursor.close()

        return sync_id

    yield _create_sync_record

    # Cleanup: 테스트 동기화 레코드 삭제
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            for sync_id in created_sync_ids:
                cursor.execute(
                    "DELETE FROM offline_sync_queue WHERE id = %s",
                    (sync_id,)
                )
            db_conn.commit()
            cursor.close()
        except Exception as e:
            print(f"Warning: Sync record cleanup failed: {e}")


# 테스트 위치 기록 생성 헬퍼
@pytest.fixture
def create_test_location_history(db_conn):
    """
    테스트 위치 기록 생성 헬퍼 함수 (commit + teardown 정리)

    Returns:
        Function(worker_id, latitude, longitude, recorded_at) -> location_id
    """
    created_location_ids = []

    def _create_location_history(
        worker_id: int,
        latitude: float,
        longitude: float,
        recorded_at: Optional[datetime] = None
    ) -> int:
        if db_conn is None:
            return 999

        if recorded_at is None:
            recorded_at = datetime.now(timezone.utc)

        cursor = db_conn.cursor()

        cursor.execute("""
            INSERT INTO location_history (
                worker_id, latitude, longitude, recorded_at
            )
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (worker_id, latitude, longitude, recorded_at))

        location_id = cursor.fetchone()[0]
        created_location_ids.append(location_id)
        db_conn.commit()
        cursor.close()

        return location_id

    yield _create_location_history

    # Cleanup: 테스트 위치 기록 삭제
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            for location_id in created_location_ids:
                cursor.execute(
                    "DELETE FROM location_history WHERE id = %s",
                    (location_id,)
                )
            db_conn.commit()
            cursor.close()
        except Exception as e:
            print(f"Warning: Location history cleanup failed: {e}")


# ==================== Sprint 7 픽스처 ====================

# Sprint 7 테스트 제품 데이터 (6개 모델)
TEST_PRODUCTS = [
    {"serial_number": "TEST-GAIA-001",    "qr_doc_id": "DOC_TEST-GAIA-001",    "model": "GAIA-I DUAL",    "mech_partner": "FNI",  "elec_partner": "TMS",  "module_outsourcing": "TMS"},
    {"serial_number": "TEST-DRAGON-001",  "qr_doc_id": "DOC_TEST-DRAGON-001",  "model": "DRAGON-V",       "mech_partner": "TMS",  "elec_partner": "P&S",  "module_outsourcing": None},
    {"serial_number": "TEST-GALLANT-001", "qr_doc_id": "DOC_TEST-GALLANT-001", "model": "GALLANT-III",    "mech_partner": "BAT",  "elec_partner": "C&A",  "module_outsourcing": None},
    {"serial_number": "TEST-MITHAS-001",  "qr_doc_id": "DOC_TEST-MITHAS-001",  "model": "MITHAS-II",      "mech_partner": "FNI",  "elec_partner": "P&S",  "module_outsourcing": None},
    {"serial_number": "TEST-SDS-001",     "qr_doc_id": "DOC_TEST-SDS-001",     "model": "SDS-100",        "mech_partner": "BAT",  "elec_partner": "TMS",  "module_outsourcing": None},
    {"serial_number": "TEST-SWS-001",     "qr_doc_id": "DOC_TEST-SWS-001",     "model": "SWS-200",        "mech_partner": "FNI",  "elec_partner": "C&A",  "module_outsourcing": None},
]

# Sprint 7 테스트 작업자 데이터 (9명)
TEST_WORKERS = [
    {"name": "FNI기구1",    "email": "fni1@test.com",    "role": "MECH", "company": "FNI",    "approval_status": "approved", "email_verified": True},
    {"name": "BAT기구1",    "email": "bat1@test.com",    "role": "MECH", "company": "BAT",    "approval_status": "approved", "email_verified": True},
    {"name": "TMS기구1",    "email": "tmsm1@test.com",   "role": "MECH", "company": "TMS(M)", "approval_status": "approved", "email_verified": True},
    {"name": "TMS전기1",    "email": "tmse1@test.com",   "role": "ELEC", "company": "TMS(E)", "approval_status": "approved", "email_verified": True},
    {"name": "PS전기1",     "email": "ps1@test.com",     "role": "ELEC", "company": "P&S",    "approval_status": "approved", "email_verified": True},
    {"name": "CA전기1",     "email": "ca1@test.com",     "role": "ELEC", "company": "C&A",    "approval_status": "approved", "email_verified": True},
    {"name": "GST관리자",   "email": "admin@test.com",   "role": "ADMIN","company": "GST",    "approval_status": "approved", "email_verified": True, "is_admin": True, "is_manager": True},
    {"name": "미승인작업자", "email": "pending@test.com", "role": "MECH", "company": "FNI",    "approval_status": "pending",  "email_verified": True},
    {"name": "미인증작업자", "email": "noverify@test.com","role": "ELEC", "company": "P&S",    "approval_status": "pending",  "email_verified": False},
]


@pytest.fixture
def seed_test_products(db_conn):
    """
    Sprint 7 테스트 제품 6개를 DB에 삽입하는 fixture.
    plan.product_info + public.qr_registry에 INSERT (ON CONFLICT DO NOTHING — 멱등성).

    Yields:
        삽입된 TEST_PRODUCTS 리스트
    """
    if db_conn is None:
        yield TEST_PRODUCTS
        return

    inserted_qr_doc_ids = []
    cursor = db_conn.cursor()

    try:
        for p in TEST_PRODUCTS:
            cursor.execute("""
                INSERT INTO plan.product_info (
                    serial_number, model, mech_partner, elec_partner,
                    module_outsourcing, prod_date
                )
                VALUES (%s, %s, %s, %s, %s, NOW()::date)
                ON CONFLICT (serial_number) DO NOTHING
            """, (p["serial_number"], p["model"], p["mech_partner"],
                  p["elec_partner"], p["module_outsourcing"]))

            cursor.execute("""
                INSERT INTO public.qr_registry (qr_doc_id, serial_number)
                VALUES (%s, %s)
                ON CONFLICT (qr_doc_id) DO NOTHING
            """, (p["qr_doc_id"], p["serial_number"]))

            inserted_qr_doc_ids.append(p["qr_doc_id"])

        db_conn.commit()
    except Exception as e:
        db_conn.rollback()
        print(f"Warning: seed_test_products insert failed: {e}")
    finally:
        cursor.close()

    yield TEST_PRODUCTS

    # Cleanup
    if not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            for qr_doc_id in inserted_qr_doc_ids:
                cursor.execute(
                    "DELETE FROM public.qr_registry WHERE qr_doc_id = %s",
                    (qr_doc_id,)
                )
            for p in TEST_PRODUCTS:
                cursor.execute(
                    "DELETE FROM plan.product_info WHERE serial_number = %s",
                    (p["serial_number"],)
                )
            db_conn.commit()
            cursor.close()
        except Exception as e:
            print(f"Warning: seed_test_products cleanup failed: {e}")


@pytest.fixture
def seed_test_workers(db_conn):
    """
    Sprint 7 테스트 작업자 9명을 DB에 삽입하는 fixture.
    password_hash = werkzeug generate_password_hash('test1234').
    ON CONFLICT (email) DO NOTHING — 멱등성.

    Yields:
        삽입된 TEST_WORKERS 리스트 (각 항목에 'id' 키 추가)
    """
    from werkzeug.security import generate_password_hash

    if db_conn is None:
        yield TEST_WORKERS
        return

    inserted_emails = []
    workers_with_ids = []
    cursor = db_conn.cursor()

    try:
        # role_enum 및 company 컬럼 존재 여부 확인 (Sprint 6 호환)
        cursor.execute("SELECT unnest(enum_range(NULL::role_enum))")
        existing_roles = {r[0] for r in cursor.fetchall()}

        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='workers' AND column_name='company'
        """)
        has_company_col = cursor.fetchone() is not None

        role_fallback_map = {'MECH': 'MM', 'ELEC': 'EE', 'ADMIN': 'PI'}

        for w in TEST_WORKERS:
            password_hash = generate_password_hash('test1234')
            db_role = w["role"]
            if db_role not in existing_roles:
                db_role = role_fallback_map.get(db_role, db_role)

            is_admin = w.get("is_admin", False)
            is_manager = w.get("is_manager", False)

            if has_company_col:
                cursor.execute("""
                    INSERT INTO workers (
                        name, email, password_hash, role, company,
                        approval_status, email_verified, is_admin, is_manager
                    )
                    VALUES (%s, %s, %s, %s::role_enum, %s,
                            %s::approval_status_enum, %s, %s, %s)
                    ON CONFLICT (email) DO NOTHING
                    RETURNING id
                """, (w["name"], w["email"], password_hash, db_role, w.get("company"),
                      w["approval_status"], w["email_verified"], is_admin, is_manager))
            else:
                cursor.execute("""
                    INSERT INTO workers (
                        name, email, password_hash, role,
                        approval_status, email_verified, is_admin, is_manager
                    )
                    VALUES (%s, %s, %s, %s::role_enum,
                            %s::approval_status_enum, %s, %s, %s)
                    ON CONFLICT (email) DO NOTHING
                    RETURNING id
                """, (w["name"], w["email"], password_hash, db_role,
                      w["approval_status"], w["email_verified"], is_admin, is_manager))

            row = cursor.fetchone()
            worker_id = row[0] if row else None
            inserted_emails.append(w["email"])
            workers_with_ids.append({**w, "id": worker_id})

        db_conn.commit()
    except Exception as e:
        db_conn.rollback()
        print(f"Warning: seed_test_workers insert failed: {e}")
    finally:
        cursor.close()

    yield workers_with_ids

    # Cleanup
    if not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            for email in inserted_emails:
                cursor.execute("DELETE FROM workers WHERE email = %s", (email,))
            db_conn.commit()
            cursor.close()
        except Exception as e:
            print(f"Warning: seed_test_workers cleanup failed: {e}")


# ==================== Sprint 9 픽스처 ====================


@pytest.fixture
def has_sprint9_schema():
    """
    Sprint 9 DB 마이그레이션 완료 여부 확인
    - app_task_details에 is_paused, total_pause_minutes 컬럼 존재
    - work_pause_log 테이블 존재
    - alert_type_enum에 BREAK_TIME_PAUSE, BREAK_TIME_END 값 존재
    """
    try:
        conn = psycopg2.connect(STAGING_DB_URL)
        cur = conn.cursor()
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='app_task_details' AND column_name='is_paused'
        """)
        has_is_paused = cur.fetchone() is not None
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_name='work_pause_log'
        """)
        has_pause_log = cur.fetchone() is not None
        cur.execute("""
            SELECT 1 FROM pg_enum
            JOIN pg_type ON pg_enum.enumtypid=pg_type.oid
            WHERE pg_type.typname='alert_type_enum'
              AND pg_enum.enumlabel='BREAK_TIME_PAUSE'
        """)
        has_break_alert = cur.fetchone() is not None
        cur.close()
        conn.close()
        return has_is_paused and has_pause_log and has_break_alert
    except Exception:
        return False


@pytest.fixture
def create_test_pause_log(db_conn):
    """
    테스트 일시정지 로그 생성 헬퍼 함수 (commit + teardown 정리)
    Sprint 9: work_pause_log 테이블 직접 삽입용

    Returns:
        Function(task_detail_id, worker_id, paused_at, resumed_at, pause_type,
                 pause_duration_minutes) -> pause_log_id
    """
    created_pause_ids = []

    def _create_pause_log(
        task_detail_id: int,
        worker_id: int,
        paused_at: Optional[datetime] = None,
        resumed_at: Optional[datetime] = None,
        pause_type: str = 'manual',
        pause_duration_minutes: Optional[int] = None
    ) -> int:
        if db_conn is None:
            return 999

        if paused_at is None:
            paused_at = datetime.now(timezone.utc)

        cursor = db_conn.cursor()

        # work_pause_log 테이블 존재 확인 (Sprint 9 마이그레이션 전/후 호환)
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_name = 'work_pause_log'
        """)
        has_pause_log = cursor.fetchone() is not None

        if not has_pause_log:
            cursor.close()
            return 999

        cursor.execute("""
            INSERT INTO work_pause_log
                (task_detail_id, worker_id, paused_at, resumed_at,
                 pause_type, pause_duration_minutes)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (task_detail_id, worker_id, paused_at, resumed_at,
              pause_type, pause_duration_minutes))

        pause_id = cursor.fetchone()[0]
        created_pause_ids.append(pause_id)
        db_conn.commit()
        cursor.close()

        return pause_id

    yield _create_pause_log

    # Cleanup: 테스트 pause 로그 삭제
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            for pause_id in created_pause_ids:
                cursor.execute(
                    "DELETE FROM work_pause_log WHERE id = %s",
                    (pause_id,)
                )
            db_conn.commit()
            cursor.close()
        except Exception as e:
            print(f"Warning: Pause log cleanup failed: {e}")
