"""
Test configuration and fixtures for AXIS-OPS test suite.
테스트 설정 및 픽스처 - 모든 테스트에서 공유되는 구성 요소
"""

import pytest
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import jwt
import bcrypt
from typing import Dict, Any, Generator, Optional


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


# Session-scoped: DB 스키마 초기화 (migrations 실행)
@pytest.fixture(scope='session')
def db_schema():
    """
    데이터베이스 스키마 초기화 (session-scoped)
    migrations/*.sql 파일을 순서대로 실행
    """
    db_url = TestConfig.DATABASE_URL

    if db_url.startswith('sqlite'):
        yield
        return

    try:
        params = _parse_db_url(db_url)
        conn = psycopg2.connect(**params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # 기존 스키마 정리 (재실행 대비) - Sprint 4 테이블 추가
        cursor.execute("DROP TABLE IF EXISTS location_history CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS offline_sync_queue CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS app_alert_logs CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS work_completion_log CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS work_start_log CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS completion_status CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS app_task_details CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS email_verification CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS product_info CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS workers CASCADE;")
        cursor.execute("DROP TYPE IF EXISTS alert_type_enum CASCADE;")
        cursor.execute("DROP TYPE IF EXISTS role_enum CASCADE;")
        cursor.execute("DROP TYPE IF EXISTS approval_status_enum CASCADE;")
        cursor.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;")

        # migrations 디렉토리
        migrations_dir = Path(__file__).parent.parent / 'backend' / 'migrations'

        migration_files = [
            '001_create_workers.sql',
            '002_create_product_info.sql',
            '003_create_task_tables.sql',
            '004_create_alert_tables.sql',
            '005_create_sync_tables.sql'
        ]

        for filename in migration_files:
            filepath = migrations_dir / filename
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    sql = f.read()
                    cursor.execute(sql)

        cursor.close()
        conn.close()

        yield

    except Exception as e:
        print(f"Warning: Schema initialization failed: {e}")
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
        role: str = 'MM',
        expires_in_hours: int = 1
    ) -> str:
        if not email:
            email = f'worker{worker_id}@test.axisos.com'

        payload = {
            'sub': str(worker_id),
            'email': email,
            'role': role,
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
        role: str = 'MM',
        approval_status: str = 'approved',
        email_verified: bool = True,
        is_manager: bool = False,
        is_admin: bool = False
    ) -> int:
        if db_conn is None:
            return 999

        password_hash = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

        cursor = db_conn.cursor()

        cursor.execute("""
            INSERT INTO workers (name, email, password_hash, role, approval_status,
                                 email_verified, is_manager, is_admin)
            VALUES (%s, %s, %s, %s::role_enum, %s::approval_status_enum, %s, %s, %s)
            RETURNING id
        """, (name, email, password_hash, role, approval_status,
              email_verified, is_manager, is_admin))

        worker_id = cursor.fetchone()[0]
        created_worker_ids.append(worker_id)
        db_conn.commit()
        cursor.close()

        return worker_id

    yield _create_worker

    # Cleanup: 테스트 워커 및 관련 데이터 삭제
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            for worker_id in created_worker_ids:
                cursor.execute(
                    "DELETE FROM email_verification WHERE worker_id = %s",
                    (worker_id,)
                )
                cursor.execute(
                    "DELETE FROM workers WHERE id = %s",
                    (worker_id,)
                )
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
        'role': 'MM',
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
        model: str = 'GBWS-50',
        production_date: str = '2025-02-15',
        location_qr_id: Optional[str] = None,
        mech_partner: Optional[str] = 'PARTNER_A',
        module_outsourcing: Optional[str] = 'PARTNER_B'
    ) -> int:
        if db_conn is None:
            return 999

        cursor = db_conn.cursor()

        cursor.execute("""
            INSERT INTO product_info (
                qr_doc_id, serial_number, model, production_date,
                location_qr_id, mech_partner, module_outsourcing
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (qr_doc_id, serial_number, model, production_date,
              location_qr_id, mech_partner, module_outsourcing))

        product_id = cursor.fetchone()[0]
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
                # CASCADE로 연관 데이터 자동 삭제
                cursor.execute(
                    "DELETE FROM product_info WHERE qr_doc_id = %s",
                    (qr_doc_id,)
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
        db_conn.commit()
        cursor.close()

        return task_detail_id

    yield _create_task

    # Cleanup: 테스트 작업 삭제
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            for task_id in created_task_ids:
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
        mm_completed: bool = False,
        ee_completed: bool = False,
        tm_completed: bool = False,
        pi_completed: bool = False,
        qi_completed: bool = False,
        si_completed: bool = False
    ) -> str:
        if db_conn is None:
            return serial_number

        cursor = db_conn.cursor()

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
        """, (serial_number, mm_completed, ee_completed, tm_completed,
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
        'email': 'mm_manager@test.axisos.com',
        'password': 'ManagerPass123!',
        'name': 'MM Manager',
        'role': 'MM',
        'approval_status': 'approved',
        'email_verified': True,
        'is_manager': True
    }

    worker_id = create_test_worker(**worker_data)
    worker_data['id'] = worker_id

    return worker_data


# EE 관리자 워커
@pytest.fixture
def ee_manager_worker(create_test_worker) -> Dict[str, Any]:
    """EE 관리자 워커 생성 (is_manager=True)"""
    worker_data = {
        'email': 'ee_manager@test.axisos.com',
        'password': 'ManagerPass123!',
        'name': 'EE Manager',
        'role': 'EE',
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
