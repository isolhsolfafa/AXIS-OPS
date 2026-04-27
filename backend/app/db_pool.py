"""
DB Connection Pool 관리
Sprint 30: psycopg2 ConnectionPool 기반 연결 풀링.
Sprint 30-B: Railway TCP 대응
  - keepalive 제거 (Railway proxy TCP_OVERWINDOW 충돌 방지)
  - 커넥션 수명 관리 (max_age 기반 자동 재생성)
  - 커넥션 health check (죽은 커넥션 자동 교체)
  - connect_timeout 설정 (무한 대기 방지)
"""

import logging
import os
import time
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from app.config import Config

logger = logging.getLogger(__name__)

# 풀 설정
_MIN_CONN = int(os.environ.get('DB_POOL_MIN', 1))
_MAX_CONN = int(os.environ.get('DB_POOL_MAX', 10))

# 커넥션 최대 수명 (초) — Railway proxy idle disconnect 전에 자발적 교체
_MAX_CONN_AGE = int(os.environ.get('DB_CONN_MAX_AGE', 300))  # 5분

# Railway public proxy용: keepalive OFF (프록시와 충돌 방지)
# connect_timeout만 설정
_CONN_KWARGS = {
    'connect_timeout': 5,
}

_pool = None

# 커넥션별 생성 시각 추적
_conn_created_at: dict = {}


def _create_pool():
    """Connection Pool 생성."""
    return pool.ThreadedConnectionPool(
        minconn=_MIN_CONN,
        maxconn=_MAX_CONN,
        dsn=Config.DATABASE_URL,
        cursor_factory=RealDictCursor,
        options="-c timezone=Asia/Seoul",
        **_CONN_KWARGS,
    )


def init_pool():
    """앱 시작 시 Connection Pool 초기화. create_app()에서 호출."""
    global _pool

    if os.environ.get('DB_POOL_DISABLED', '').lower() in ('true', '1'):
        logger.info("[db_pool] Pool disabled by DB_POOL_DISABLED env var")
        return

    try:
        _pool = _create_pool()
        logger.info(
            f"[db_pool] Connection pool initialized: "
            f"min={_MIN_CONN}, max={_MAX_CONN}, "
            f"max_age={_MAX_CONN_AGE}s, connect_timeout=5s"
        )
    except Exception as e:
        logger.error(f"[db_pool] Pool initialization failed: {e}")
        _pool = None


def _is_conn_usable(conn) -> bool:
    """
    커넥션이 사용 가능한지 확인:
    1) closed 여부
    2) 수명 초과 여부 (Railway proxy idle disconnect 방지)
    3) SELECT 1 health check
    """
    try:
        if conn.closed:
            return False

        # 수명 초과 확인
        conn_id = id(conn)
        created = _conn_created_at.get(conn_id, 0)
        if time.time() - created > _MAX_CONN_AGE:
            logger.info(f"[db_pool] Connection expired (age>{_MAX_CONN_AGE}s), recycling")
            return False

        # 트랜잭션 에러 상태 정리
        if conn.info.transaction_status == psycopg2.extensions.TRANSACTION_STATUS_INERROR:
            conn.rollback()

        # health check
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        # HOTFIX-08 (v2.10.10): SELECT 1 후 transaction 정리.
        # psycopg2 default autocommit=False → SELECT 도 BEGIN 자동 시작 → INTRANS 상태로 풀 반납됨.
        # 이 conn 을 받아 m_conn.autocommit=True 시도 시 set_session error 발생 (migration_runner 사례).
        conn.rollback()
        return True
    except Exception:
        return False


def _create_direct_conn():
    """풀 없이 직접 연결 생성 (fallback용)."""
    logger.warning("[db_pool] Using direct connection")
    conn = psycopg2.connect(
        Config.DATABASE_URL,
        cursor_factory=RealDictCursor,
        options="-c timezone=Asia/Seoul",
        **_CONN_KWARGS,
    )
    _conn_created_at[id(conn)] = time.time()
    return conn


def _discard_conn(conn):
    """커넥션을 풀에서 제거하고 수명 추적도 정리."""
    conn_id = id(conn)
    _conn_created_at.pop(conn_id, None)
    try:
        if _pool:
            _pool.putconn(conn, close=True)
        else:
            conn.close()
    except Exception:
        try:
            conn.close()
        except Exception:
            pass


def get_conn():
    """
    풀에서 연결 가져오기 + health check + 수명 확인.
    죽은/만료된 커넥션은 자동 교체.
    """
    global _pool
    if _pool is None:
        return _create_direct_conn()

    retries = 3
    for attempt in range(retries):
        try:
            conn = _pool.getconn()
        except pool.PoolError as e:
            logger.warning(f"[db_pool] Pool exhausted: {e}")
            return _create_direct_conn()
        except Exception as e:
            logger.error(f"[db_pool] getconn failed: {e}")
            raise

        # 신규 커넥션이면 생성 시각 기록
        conn_id = id(conn)
        if conn_id not in _conn_created_at:
            _conn_created_at[conn_id] = time.time()

        # 사용 가능한지 확인 (health check + 수명)
        if _is_conn_usable(conn):
            return conn

        # 사용 불가 → 폐기
        logger.warning(
            f"[db_pool] Unusable connection (attempt {attempt+1}/{retries}), discarding"
        )
        _discard_conn(conn)

    # 모든 재시도 실패
    logger.error("[db_pool] All pool connections unusable, creating direct connection")
    return _create_direct_conn()


def put_conn(conn):
    """
    연결을 풀에 반납.
    broken/만료 커넥션은 폐기.
    """
    global _pool
    if conn is None:
        return

    if _pool is None:
        _conn_created_at.pop(id(conn), None)
        try:
            conn.close()
        except Exception:
            pass
        return

    try:
        # broken connection
        if conn.closed:
            logger.warning("[db_pool] Returning closed connection, discarding")
            _discard_conn(conn)
            return

        # 수명 초과 — 반납 시 폐기 (다음 getconn에서 새로 생성됨)
        conn_id = id(conn)
        created = _conn_created_at.get(conn_id, 0)
        if time.time() - created > _MAX_CONN_AGE:
            logger.info("[db_pool] Connection expired on return, discarding")
            _discard_conn(conn)
            return

        # 트랜잭션 에러 상태이면 rollback
        if conn.info.transaction_status == psycopg2.extensions.TRANSACTION_STATUS_INERROR:
            try:
                conn.rollback()
            except Exception:
                _discard_conn(conn)
                return

        _pool.putconn(conn)

    except Exception:
        _conn_created_at.pop(id(conn), None)
        try:
            conn.close()
        except Exception:
            pass


def close_pool():
    """앱 종료 시 풀 정리."""
    global _pool
    if _pool:
        _pool.closeall()
        _conn_created_at.clear()
        logger.info("[db_pool] Connection pool closed")
        _pool = None


def warmup_pool() -> tuple:
    """
    OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP-20260427:
    Pool conn 자발적 폐기 방지 — _MIN_CONN 만큼 SELECT 1 실행으로 max_age 시계 리셋.

    배경: max_age=300s 만료 + lazy 재생성 race 로 MIN=5 사실상 무효.
          실측 (2026-04-27): 풀 초기화 후 10 → 9 → 7 conn (10분 만에 30% 감소).

    효과: scheduler_service 의 5분 간격 cron 에서 호출 → 모든 idle conn 활성화 →
          max_age 시계 리셋 → MIN=5 강제 유지.

    Returns:
        tuple (warmed: int, requested: int) — 성공한 conn 수 / 요청한 conn 수.
    """
    if _pool is None:
        logger.debug("[db_pool] warmup skipped — pool not initialized")
        return (0, 0)

    conns = []
    try:
        for _ in range(_MIN_CONN):
            try:
                conn = _pool.getconn()
                conns.append(conn)
            except Exception as e:
                logger.warning(f"[db_pool] warmup getconn failed (skip): {e}")
                break

        warmed = 0
        for conn in conns:
            try:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.close()
                # HOTFIX-08 (v2.10.10): SELECT 1 후 transaction 정리 (INTRANS 상태 회피).
                conn.rollback()
                # HOTFIX-06 (v2.10.7): max_age 시계 리셋 — warmup 의도대로 작동.
                # 누락 시 warmup 후에도 _is_conn_usable() 가 expired 판정 → discard → fallback.
                _conn_created_at[id(conn)] = time.time()
                warmed += 1
            except Exception as e:
                logger.warning(f"[db_pool] warmup SELECT 1 failed: {e}")

        return (warmed, len(conns))
    finally:
        for conn in conns:
            try:
                _pool.putconn(conn)
            except Exception:
                pass
