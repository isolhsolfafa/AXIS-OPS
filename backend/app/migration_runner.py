"""
Migration 자동 실행기 — 앱 시작 시 미실행 migration 자동 적용.
migration_history 테이블로 실행 이력 추적. 이미 실행된 migration은 건너뜀.
"""

import os
import re
import logging
from app.db_pool import get_conn, put_conn
from psycopg2 import Error as PsycopgError

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'migrations')

# migration 파일명 정렬용: "042_xxx.sql" → (42, 0, "042_xxx.sql")
# "043a_xxx.sql" → (43, 1, "043a_xxx.sql")  (숫자 뒤 소문자 = 서브 순서)
_FILE_PATTERN = re.compile(r'^(\d+)([a-z]?)_.*\.sql$')

def _sort_key(filename: str):
    """migration 파일 정렬 키: 숫자 → 접미사(a=1, b=2, ...)"""
    m = _FILE_PATTERN.match(filename)
    if not m:
        return (9999, 0, filename)
    num = int(m.group(1))
    suffix = ord(m.group(2)) - ord('a') + 1 if m.group(2) else 0
    return (num, suffix, filename)


def _ensure_migration_table(cur) -> None:
    """migration_history 테이블이 없으면 생성"""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS migration_history (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(255) UNIQUE NOT NULL,
            executed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _get_executed(cur) -> set:
    """이미 실행된 migration 파일명 set 반환.

    HOTFIX-07 (v2.10.9): db_pool 이 RealDictCursor 사용 → row 가 dict-like.
    이전 `row[0]` 은 KeyError 유발했지만 run_migrations 의 outer try/except 가
    silent 흡수했음. v2.10.8 에서 assert_migrations_in_sync() 가 추가되며
    try/except 없이 호출 → KeyError 가 그대로 propagate → gunicorn worker
    boot 실패 → 503. row['filename'] 로 정정.
    """
    cur.execute("SELECT filename FROM migration_history")
    return {row['filename'] for row in cur.fetchall()}


def run_migrations() -> None:
    """
    미실행 migration을 순서대로 실행.
    각 migration은 개별 트랜잭션으로 실행 (ENUM ADD VALUE는 트랜잭션 내 실행 불가 →
    autocommit 모드 사용).
    """
    if not os.path.isdir(MIGRATIONS_DIR):
        logger.warning(f"[migration] migrations 디렉토리 없음: {MIGRATIONS_DIR}")
        return

    conn = None
    try:
        conn = get_conn()

        # autocommit OFF 상태에서 migration_history 테이블 생성
        cur = conn.cursor()
        _ensure_migration_table(cur)
        conn.commit()

        executed = _get_executed(cur)

        # migration 파일 목록 (정렬)
        files = sorted(
            [f for f in os.listdir(MIGRATIONS_DIR) if _FILE_PATTERN.match(f)],
            key=_sort_key
        )

        pending = [f for f in files if f not in executed]
        if not pending:
            logger.info("[migration] 모든 migration 실행 완료 상태")
            return

        logger.info(f"[migration] 미실행 migration {len(pending)}건 감지: {pending}")
        put_conn(conn)
        conn = None

        # 각 migration 개별 실행 (ENUM ADD VALUE 호환을 위해 autocommit)
        for filename in pending:
            filepath = os.path.join(MIGRATIONS_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                sql = f.read().strip()

            if not sql:
                logger.warning(f"[migration] {filename} — 빈 파일, 건너뜀")
                continue

            m_conn = None
            try:
                m_conn = get_conn()
                # ENUM ADD VALUE는 autocommit 필수
                m_conn.autocommit = True
                m_cur = m_conn.cursor()

                # SQL 파일 내 여러 statement를 순차 실행
                # psycopg2 execute()는 멀티 statement 지원하지만,
                # ENUM ADD VALUE 이후 다른 구문이 올 수 있으므로 개별 실행
                statements = _split_statements(sql)
                for stmt in statements:
                    if stmt.strip():
                        m_cur.execute(stmt)

                # 실행 이력 기록 (autocommit이므로 즉시 반영)
                m_cur.execute(
                    "INSERT INTO migration_history (filename) VALUES (%s) ON CONFLICT DO NOTHING",
                    (filename,)
                )
                logger.info(f"[migration] ✅ {filename} 실행 완료")

            except Exception as e:
                logger.error(f"[migration] ❌ {filename} 실행 실패: {e}")
                # OBSERV-ALERT-SILENT-FAIL-20260427: Sentry capture (silent failure 방지)
                # 4-22 049 미적용 사례 같은 silent gap 외부 자동 감지.
                try:
                    import sentry_sdk
                    sentry_sdk.capture_exception(e)
                except ImportError:
                    pass  # Sentry 미설치 환경 (로컬/test)
                # 실패한 migration에서 멈추고 이후 migration은 건너뜀
                raise
            finally:
                if m_conn:
                    m_conn.autocommit = False
                    put_conn(m_conn)

    except PsycopgError as e:
        logger.error(f"[migration] DB 오류: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        logger.error(f"[migration] 예상치 못한 오류: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            put_conn(conn)


def assert_migrations_in_sync() -> None:
    """
    OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION-20260427:
    앱 시작 시 코드(disk)와 DB(migration_history) 의 migration 동기화 검증.
    4-22 049 미적용 사례 (POST_MORTEM_MIGRATION_049.md 권장 ①) 재발 방지.

    - missing_from_disk: DB 적용됐는데 disk 에 없음 (rollback 의심)
    - not_yet_applied: disk 에 있는데 DB 미적용 (049 같은 silent gap)

    not_yet_applied 발견 시 logger.error + Sentry capture_message.

    HOTFIX-07 (v2.10.9): outer try/except 추가 — assertion 자체 실패가
    gunicorn worker boot 막지 않도록 안전망. 실패 시에도 app 은 정상 boot.
    """
    try:
        if not os.path.isdir(MIGRATIONS_DIR):
            return

        files_in_disk = {f for f in os.listdir(MIGRATIONS_DIR) if _FILE_PATTERN.match(f)}

        conn = None
        try:
            conn = get_conn()
            cur = conn.cursor()
            executed = _get_executed(cur)
        finally:
            if conn:
                put_conn(conn)

        missing_from_disk = executed - files_in_disk
        not_yet_applied = files_in_disk - executed

        if missing_from_disk:
            logger.error(
                f"[migration-assert] DB 적용됐지만 disk 에 없음: {sorted(missing_from_disk)}"
            )

        if not_yet_applied:
            msg = f"[migration-assert] ⚠️ disk 에 있지만 DB 미적용: {sorted(not_yet_applied)}"
            logger.error(msg)
            # Sentry capture — 049 같은 silent gap 즉시 외부 알림
            try:
                import sentry_sdk
                sentry_sdk.capture_message(msg, level='error')
            except ImportError:
                pass
        else:
            logger.info(
                f"[migration-assert] ✅ sync OK ({len(executed)} migrations applied)"
            )
    except Exception as e:
        # HOTFIX-07: assertion 실패가 worker boot 막지 않도록 안전망
        logger.error(f"[migration-assert] assertion failed (non-fatal): {e}", exc_info=True)
        try:
            import sentry_sdk
            sentry_sdk.capture_exception(e)
        except ImportError:
            pass


def _split_statements(sql: str) -> list:
    """
    SQL 문자열을 개별 statement로 분리.
    세미콜론(;) 기준이지만 문자열 리터럴 내부의 세미콜론은 무시.
    단순 구현: 주석 제거 후 세미콜론 분리.
    """
    statements = []
    current = []
    in_single_quote = False
    in_dollar_quote = False
    dollar_tag = ''
    i = 0
    chars = sql

    while i < len(chars):
        c = chars[i]

        # 달러 인용 처리 ($$...$$)
        if c == '$' and not in_single_quote:
            # 달러 태그 시작/종료 감지
            j = i + 1
            while j < len(chars) and (chars[j].isalnum() or chars[j] == '_'):
                j += 1
            if j < len(chars) and chars[j] == '$':
                tag = chars[i:j+1]
                if in_dollar_quote and tag == dollar_tag:
                    in_dollar_quote = False
                    current.append(chars[i:j+1])
                    i = j + 1
                    continue
                elif not in_dollar_quote:
                    in_dollar_quote = True
                    dollar_tag = tag
                    current.append(chars[i:j+1])
                    i = j + 1
                    continue

        # 단일 인용 처리
        if c == "'" and not in_dollar_quote:
            if in_single_quote:
                # 이스케이프 체크 ('')
                if i + 1 < len(chars) and chars[i+1] == "'":
                    current.append("''")
                    i += 2
                    continue
                in_single_quote = False
            else:
                in_single_quote = True

        # 라인 주석 (--)
        if c == '-' and i + 1 < len(chars) and chars[i+1] == '-' and not in_single_quote and not in_dollar_quote:
            while i < len(chars) and chars[i] != '\n':
                i += 1
            current.append('\n')
            continue

        # statement 분리
        if c == ';' and not in_single_quote and not in_dollar_quote:
            stmt = ''.join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
            i += 1
            continue

        current.append(c)
        i += 1

    # 마지막 statement (세미콜론 없는 경우)
    stmt = ''.join(current).strip()
    if stmt:
        statements.append(stmt)

    return statements
