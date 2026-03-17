"""
DB Connection Pool 관리
Sprint 30: psycopg2 ConnectionPool 기반 연결 풀링.
Sprint 30-B: Railway TCP_INVALID_SYN 대응
  - TCP keepalive 활성화 (Railway proxy idle disconnect 방지)
  - 커넥션 health check (죽은 커넥션 자동 교체)
  - connect_timeout 설정 (무한 대기 방지)
  - put_conn에서 broken connection 감지 후 close
"""

import logging
import os
import psycopg2
from psycopg2 import pool, OperationalError, InterfaceError
from psycopg2.extras import RealDictCursor
from app.config import Config

logger = logging.getLogger(__name__)

# 풀 설정
_MIN_CONN = int(os.environ.get('DB_POOL_MIN', 2))
_MAX_CONN = int(os.environ.get('DB_POOL_MAX', 10))

# Railway TCP keepalive 설정
_KEEPALIVE_KWARGS = {
    'keepalives': 1,            # TCP keepalive ON
    'keepalives_idle': 30,      # 30초 유휴 후 keepalive 시작
    'keepalives_interval': 10,  # 10초 간격으로 probe
    'keepalives_count': 3,      # 3회 실패 시 연결 끊김 판정
    'connect_timeout': 5,       # 연결 시도 5초 제한
}

_pool = None


def _create_pool():
    """Connection Pool 생성 (keepalive 포함)."""
    return pool.ThreadedConnectionPool(
        minconn=_MIN_CONN,
        maxconn=_MAX_CONN,
        dsn=Config.DATABASE_URL,
        cursor_factory=RealDictCursor,
        options="-c timezone=Asia/Seoul",
        **_KEEPALIVE_KWARGS,
    )


def init_pool():
    """앱 시작 시 Connection Pool 초기화. create_app()에서 호출."""
    global _pool

    # 환경변수로 풀 비활성화 (롤백용)
    if os.environ.get('DB_POOL_DISABLED', '').lower() in ('true', '1'):
        logger.info("[db_pool] Pool disabled by DB_POOL_DISABLED env var")
        return

    try:
        _pool = _create_pool()
        logger.info(
            f"[db_pool] Connection pool initialized: "
            f"min={_MIN_CONN}, max={_MAX_CONN}, "
            f"keepalives_idle=30s, connect_timeout=5s"
        )
    except Exception as e:
        logger.error(f"[db_pool] Pool initialization failed: {e}")
        _pool = None


def _is_conn_alive(conn) -> bool:
    """커넥션이 살아있는지 빠르게 확인 (SELECT 1)."""
    try:
        if conn.closed:
            return False
        # 트랜잭션 상태 확인: 에러 상태이면 rollback 필요
        if conn.info.transaction_status == psycopg2.extensions.TRANSACTION_STATUS_INERROR:
            conn.rollback()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        return True
    except Exception:
        return False


def _create_direct_conn():
    """풀 없이 직접 연결 생성 (fallback용)."""
    logger.warning("[db_pool] Pool not available, using direct connection")
    return psycopg2.connect(
        Config.DATABASE_URL,
        cursor_factory=RealDictCursor,
        options="-c timezone=Asia/Seoul",
        **_KEEPALIVE_KWARGS,
    )


def get_conn():
    """
    풀에서 연결 가져오기 + health check.
    죽은 커넥션이면 풀에서 제거하고 새로 가져옴.
    풀 초기화 실패 시 fallback으로 직접 연결 생성.
    """
    global _pool
    if _pool is None:
        return _create_direct_conn()

    retries = 2
    for attempt in range(retries):
        try:
            conn = _pool.getconn()
        except pool.PoolError as e:
            # 풀 고갈 — 직접 연결로 fallback
            logger.warning(f"[db_pool] Pool exhausted (attempt {attempt+1}): {e}")
            return _create_direct_conn()
        except Exception as e:
            logger.error(f"[db_pool] getconn failed: {e}")
            raise

        # Health check: Railway TCP_INVALID_SYN으로 죽은 커넥션 감지
        if _is_conn_alive(conn):
            return conn

        # 죽은 커넥션 → 풀에서 제거 (close=True)
        logger.warning(
            f"[db_pool] Dead connection detected (attempt {attempt+1}), "
            f"discarding and retrying"
        )
        try:
            _pool.putconn(conn, close=True)
        except Exception:
            try:
                conn.close()
            except Exception:
                pass

    # 재시도 실패 → 직접 연결
    logger.error("[db_pool] All pool connections dead, creating direct connection")
    return _create_direct_conn()


def put_conn(conn):
    """
    연결을 풀에 반납.
    broken 커넥션이면 close하고 풀에서 제거.
    풀이 없으면 close.
    """
    global _pool
    if conn is None:
        return

    if _pool is None:
        try:
            conn.close()
        except Exception:
            pass
        return

    try:
        # broken connection 감지: closed이거나 에러 상태
        if conn.closed:
            logger.warning("[db_pool] Returning closed connection, discarding")
            try:
                _pool.putconn(conn, close=True)
            except Exception:
                pass
            return

        # 트랜잭션이 에러 상태이면 rollback 후 반납
        if conn.info.transaction_status == psycopg2.extensions.TRANSACTION_STATUS_INERROR:
            try:
                conn.rollback()
            except Exception:
                logger.warning("[db_pool] Rollback failed, discarding connection")
                try:
                    _pool.putconn(conn, close=True)
                except Exception:
                    try:
                        conn.close()
                    except Exception:
                        pass
                return

        _pool.putconn(conn)

    except Exception:
        try:
            conn.close()
        except Exception:
            pass


def close_pool():
    """앱 종료 시 풀 정리."""
    global _pool
    if _pool:
        _pool.closeall()
        logger.info("[db_pool] Connection pool closed")
        _pool = None
