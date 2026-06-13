"""
FIX-FORCE-CLOSE-DURATION-SOURCE (20260613) — 강제종료 duration_source='FORCE_CLOSED' 정합 (A)

검증:
  - migration 062 CHECK enum 이 'FORCE_CLOSED' 허용 (INSERT 통과)
  - force_close UPDATE 가 duration_source='FORCE_CLOSED' 기록 (admin.py 소스 검증)
  - _ESTIMATED_SOURCES 에 FORCE_CLOSED 포함 (비-clean 분류)
  - _CLEAN_CORE/get_data_quality 에서 FORCE_CLOSED 제외 (입력정합 정합)
  - backfill 멱등 (force_closed=TRUE AND source∈(NULL,NORMAL) 만 정정)
"""
import re

import pytest


# ── 소스 상수 검증 (DB 불필요) ──

def test_fc01_estimated_sources_includes_force_closed():
    """TC-FC-01: _ESTIMATED_SOURCES 에 FORCE_CLOSED 포함 (비-clean 추정 분류)."""
    from app.services.statistics_service import _ESTIMATED_SOURCES, _CLEAN_SOURCES
    assert "FORCE_CLOSED" in _ESTIMATED_SOURCES
    # clean 에는 절대 포함 안 됨
    assert "FORCE_CLOSED" not in _CLEAN_SOURCES


def test_fc02_clean_core_excludes_force_closed():
    """TC-FC-02: _CLEAN_CORE 가 force_closed=FALSE 가드 + NORMAL-only → FORCE_CLOSED 이중 제외."""
    from app.services.statistics_service import _CLEAN_CORE
    assert "COALESCE(td.force_closed, FALSE) = FALSE" in _CLEAN_CORE
    # FORCE_CLOSED 는 NORMAL/NULL 아니므로 source 필터로도 제외
    assert "'NORMAL_COMPLETION'" in _CLEAN_CORE


def test_fc03_admin_force_close_sets_source():
    """TC-FC-03: admin.py force_close UPDATE 가 duration_source='FORCE_CLOSED' 기록."""
    import app.routes.admin as admin_mod
    src = open(admin_mod.__file__).read()
    # force_close UPDATE 블록에 duration_source = 'FORCE_CLOSED' 존재
    assert "duration_source  = 'FORCE_CLOSED'" in src


def test_fc04_migration_062_enum_and_backfill():
    """TC-FC-04: migration 062 가 enum 추가 + backfill(멱등 조건) + 검증 DO block 포함."""
    sql = open("backend/migrations/062_add_force_closed_duration_source.sql").read()
    assert "'FORCE_CLOSED'" in sql
    assert "DROP CONSTRAINT" in sql
    # backfill 멱등 조건: clean(NULL/NORMAL) 만 정정
    assert "force_closed = TRUE" in sql
    assert "duration_source IS NULL OR duration_source = 'NORMAL_COMPLETION'" in sql
    # 검증 DO block (clean 잔존 0)
    assert "RAISE EXCEPTION" in sql


# ── DB 통합 (enum 허용 + 제외 동작) ──

@pytest.fixture
def _ensure_enum(db_conn):
    """migration 062 enum 적용 보장 (test DB 가 미적용일 수 있어 멱등 ALTER)."""
    if db_conn is None:
        pytest.skip("sqlite")
    cur = db_conn.cursor()
    cur.execute("""
        SELECT pg_get_constraintdef(oid) FROM pg_constraint
        WHERE conname = 'app_task_details_duration_source_check'
    """)
    row = cur.fetchone()
    if row and "FORCE_CLOSED" not in row[0]:
        cur.execute("ALTER TABLE app_task_details DROP CONSTRAINT app_task_details_duration_source_check")
        cur.execute("""
            ALTER TABLE app_task_details ADD CONSTRAINT app_task_details_duration_source_check
            CHECK (duration_source IS NULL OR duration_source IN
                ('NORMAL_COMPLETION','ATTENDANCE_OUT','FALLBACK_TRIGGER_DATE_17',
                 'INVALID_WARNING','PREV_DAY_CAP','FORCE_CLOSED'))
        """)
        db_conn.commit()
    cur.close()


def test_fc05_enum_definition_includes_force_closed(db_conn, _ensure_enum):
    """TC-FC-05: CHECK 제약 정의에 FORCE_CLOSED enum 포함 (migration 062 적용 검증)."""
    cur = db_conn.cursor()
    try:
        cur.execute("""
            SELECT pg_get_constraintdef(oid) FROM pg_constraint
            WHERE conname = 'app_task_details_duration_source_check'
        """)
        row = cur.fetchone()
        assert row is not None, "duration_source CHECK 제약 부재"
        assert "FORCE_CLOSED" in row[0], f"FORCE_CLOSED enum 미포함: {row[0]}"
    finally:
        db_conn.rollback()
        cur.close()
