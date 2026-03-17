"""
DB Connection Pool 관리
Sprint 30: psycopg2 ConnectionPool 기반 연결 풀링.
동시 접속 100명+ 환경에서 DB 연결 포화 방지.
"""

import logging
import os
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from app.config import Config

logger = logging.getLogger(__name__)

# 풀 설정
_MIN_CONN = int(os.environ.get('DB_POOL_MIN', 5))
_MAX_CONN = int(os.environ.get('DB_POOL_MAX', 20))

_pool = None


def init_pool():
    """앱 시작 시 Connection Pool 초기화. create_app()에서 호출."""
    global _pool

    # 환경변수로 풀 비활성화 (롤백용)
    if os.environ.get('DB_POOL_DISABLED', '').lower() in ('true', '1'):
        logger.info("[db_pool] Pool disabled by DB_POOL_DISABLED env var")
        return

    try:
        _pool = pool.ThreadedConnectionPool(
            minconn=_MIN_CONN,
            maxconn=_MAX_CONN,
            dsn=Config.DATABASE_URL,
            cursor_factory=RealDictCursor,
            options="-c timezone=Asia/Seoul"
        )
        logger.info(
            f"[db_pool] Connection pool initialized: "
            f"min={_MIN_CONN}, max={_MAX_CONN}"
        )
    except Exception as e:
        logger.error(f"[db_pool] Pool initialization failed: {e}")
        _pool = None


def get_conn():
    """
    풀에서 연결 가져오기.
    풀 초기화 실패 시 fallback으로 직접 연결 생성.
    """
    global _pool
    if _pool is None:
        import psycopg2
        logger.warning("[db_pool] Pool not available, using direct connection")
        return psycopg2.connect(
            Config.DATABASE_URL,
            cursor_factory=RealDictCursor,
            options="-c timezone=Asia/Seoul"
        )
    try:
        conn = _pool.getconn()
        return conn
    except Exception as e:
        logger.error(f"[db_pool] getconn failed: {e}")
        raise


def put_conn(conn):
    """연결을 풀에 반납. 풀이 없으면 close."""
    global _pool
    if _pool is None or conn is None:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        return
    try:
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
