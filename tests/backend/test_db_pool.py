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


def test_warmup_logs_error_when_pool_none(caplog):
    """FIX-DB-POOL-WARMUP-WATCHDOG-20260430:
    warmup cron 호출됐는데 _pool=None 이면 silent failure → logger.error 호출 검증.
    4-29 23:31 사고 (1.5시간+ silent) 재발 방지.
    LoggingIntegration(event_level=ERROR) 가 자동 Sentry capture → 알림 받음."""
    with patch.object(db_pool, '_pool', None):
        with caplog.at_level(logging.ERROR, logger='app.db_pool'):
            warmed, total = db_pool.warmup_pool()

    # 거동 검증
    assert warmed == 0
    assert total == 0
    # error level + pid context 검증
    pool_death_logs = [r for r in caplog.records if 'gunicorn worker pool died' in r.message]
    assert len(pool_death_logs) >= 1, "pool=None 시 logger.error 호출 누락"
    assert pool_death_logs[-1].levelno == logging.ERROR


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


# ─────────────────────────────────────────────────────────────────
# FIX-DB-POOL-SELF-RECOVERY-20260504 (v2.10.18)
# Railway proxy idle TCP disconnect + ThreadedConnectionPool 자가 회복 부재 해소.
# 4-29 23:31 + 5-04 11:38 KST 5일 주기 사고 차단.
# ─────────────────────────────────────────────────────────────────


def test_keepalive_args_passed_to_psycopg2():
    """psycopg2 connect 시 keepalive 4 args 전달 검증.
    Railway network proxy idle TCP disconnect 회피용 (기존 _CONN_KWARGS={'connect_timeout': 5} 만)."""
    with patch('app.db_pool.pool.ThreadedConnectionPool') as mock_pool:
        db_pool._create_pool()
        kwargs = mock_pool.call_args.kwargs
        assert kwargs.get('keepalives') == 1
        assert kwargs.get('keepalives_idle') == 60
        assert kwargs.get('keepalives_interval') == 10
        assert kwargs.get('keepalives_count') == 3
        # 기존 connect_timeout 유지 검증
        assert kwargs.get('connect_timeout') == 5


def test_consecutive_zero_warmup_triggers_init_pool():
    """0/0 conn warmed 3 cycles 연속 시 close_pool + init_pool 자동 호출.
    5-04 11:38~12:32 사고 패턴 (40분 0/0 지속) 자가 회복 검증.
    _used dict dead conn 정리 부재 → getconn fail 지속 → break → 0/0 → counter 증가."""
    db_pool._consecutive_zero_warmup = 0  # 격리 (이전 테스트 영향 차단)

    fake_pool = MagicMock()
    fake_pool.getconn.side_effect = Exception("PoolError exhausted")

    with patch.object(db_pool, '_pool', fake_pool), \
         patch.object(db_pool, 'close_pool') as mock_close, \
         patch.object(db_pool, 'init_pool') as mock_init:

        # 1차 cycle — 0/0
        warmed, total = db_pool.warmup_pool()
        assert warmed == 0 and total == 0
        assert db_pool.get_consecutive_zero_warmup() == 1
        mock_close.assert_not_called()
        mock_init.assert_not_called()

        # 2차 cycle — 0/0
        db_pool.warmup_pool()
        assert db_pool.get_consecutive_zero_warmup() == 2
        mock_close.assert_not_called()
        mock_init.assert_not_called()

        # 3차 cycle — 0/0 → 자가 회복 trigger
        db_pool.warmup_pool()
        mock_close.assert_called_once()
        mock_init.assert_called_once()
        # 회복 후 카운터 리셋 검증
        assert db_pool.get_consecutive_zero_warmup() == 0


def test_zero_warmup_logger_error_captured(caplog):
    """0/0 연속 3회 시 logger.error 호출 (LoggingIntegration 자동 Sentry capture 보장).
    WATCHDOG 확장 — 운영 시 5-09 ± 1d 재발 시점 Twin파파 알람 1분 안 도달."""
    db_pool._consecutive_zero_warmup = 2  # 마지막 cycle 직전 상태

    fake_pool = MagicMock()
    fake_pool.getconn.side_effect = Exception("PoolError")

    with patch.object(db_pool, '_pool', fake_pool), \
         patch.object(db_pool, 'close_pool'), \
         patch.object(db_pool, 'init_pool'):

        with caplog.at_level(logging.ERROR, logger='app.db_pool'):
            db_pool.warmup_pool()

    error_logs = [r for r in caplog.records
                  if 're-initializing pool' in r.message]
    assert len(error_logs) >= 1, "self-recovery trigger 시 logger.error 호출 누락"
    assert error_logs[-1].levelno == logging.ERROR


def test_normal_warmup_resets_consecutive_counter():
    """정상 warmup (warmed > 0) 시 _consecutive_zero_warmup 리셋 검증.
    중간에 일시적 0/0 발생 후 정상 회복 시 카운터 누적 방지."""
    db_pool._consecutive_zero_warmup = 2  # 임의 누적 상태

    fake_conn = MagicMock()
    fake_cur = MagicMock()
    fake_conn.cursor.return_value = fake_cur

    fake_pool = MagicMock()
    fake_pool.getconn.return_value = fake_conn

    with patch.object(db_pool, '_pool', fake_pool), \
         patch.object(db_pool, '_MIN_CONN', 1):
        warmed, total = db_pool.warmup_pool()

    assert warmed == 1 and total == 1
    # 정상 cycle 시 카운터 리셋
    assert db_pool.get_consecutive_zero_warmup() == 0
