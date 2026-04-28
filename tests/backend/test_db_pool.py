"""
db_pool direct conn fallback 동작 단위 테스트.
FIX-DB-POOL-DIRECT-FALLBACK-LOG-LEVEL-20260428.
"""
from unittest.mock import patch, MagicMock
import logging

import pytest

from app import db_pool


def test_fallback_increments_counter(caplog):
    """3 retry 모두 unusable 판정 시 counter 증가 + warning 로그."""
    before = db_pool.get_direct_fallback_count()

    fake_conn = MagicMock()
    with patch.object(db_pool, '_pool') as mock_pool, \
         patch.object(db_pool, '_is_conn_usable', return_value=False), \
         patch.object(db_pool, '_create_direct_conn', return_value='DIRECT'):
        mock_pool.getconn.return_value = fake_conn

        with caplog.at_level(logging.WARNING, logger='app.db_pool'):
            result = db_pool.get_conn()

    assert result == 'DIRECT'
    assert db_pool.get_direct_fallback_count() == before + 1
    # warning level 확인 (error 아님)
    fallback_logs = [r for r in caplog.records
                     if 'All pool connections unusable' in r.message]
    assert len(fallback_logs) >= 1
    assert fallback_logs[-1].levelno == logging.WARNING


def test_normal_path_no_counter_increment():
    """정상 conn 획득 시 counter 무변화."""
    before = db_pool.get_direct_fallback_count()

    fake_conn = MagicMock()
    with patch.object(db_pool, '_pool') as mock_pool, \
         patch.object(db_pool, '_is_conn_usable', return_value=True):
        mock_pool.getconn.return_value = fake_conn
        result = db_pool.get_conn()

    assert result is fake_conn
    assert db_pool.get_direct_fallback_count() == before  # 무변화


def test_pool_exhausted_does_not_increment_fallback_counter():
    """pool.PoolError (exhausted) 경로는 별도 — direct fallback counter 증가 X."""
    before = db_pool.get_direct_fallback_count()

    from psycopg2 import pool as pg_pool
    with patch.object(db_pool, '_pool') as mock_pool, \
         patch.object(db_pool, '_create_direct_conn', return_value='DIRECT'):
        mock_pool.getconn.side_effect = pg_pool.PoolError("exhausted")
        result = db_pool.get_conn()

    assert result == 'DIRECT'
    # exhausted fallback 은 별도 경로 (get_conn L150-151) — 본 counter 와 분리
    assert db_pool.get_direct_fallback_count() == before
