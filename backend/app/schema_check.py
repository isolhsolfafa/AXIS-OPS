"""
DB 스키마 자동 검증 — 앱 시작 시 필수 컬럼/제약조건 확인 및 자동 적용.
BUG-24: 배포마다 migration 누락으로 task seed silent fail 방지.
"""

import logging
from app.models.worker import get_db_connection
from psycopg2 import Error as PsycopgError

logger = logging.getLogger(__name__)

# ── 필수 컬럼 정의 ──────────────────────────────────
# (테이블명, 컬럼명, 없으면 실행할 ALTER TABLE DDL)
REQUIRED_COLUMNS = [
    (
        'app_task_details',
        'task_type',
        "ALTER TABLE app_task_details ADD COLUMN IF NOT EXISTS task_type VARCHAR(20) DEFAULT 'NORMAL'"
    ),
]

# ── 필수 FK 제약조건 정의 ────────────────────────────
# (테이블명, constraint명, 컬럼명, 기대하는 delete_rule, 수정 DDL)
REQUIRED_CONSTRAINTS = [
    (
        'app_task_details',
        'app_task_details_qr_doc_id_fkey',
        'qr_doc_id',
        'RESTRICT',
        [
            "ALTER TABLE app_task_details DROP CONSTRAINT IF EXISTS app_task_details_qr_doc_id_fkey",
            "ALTER TABLE app_task_details ADD CONSTRAINT app_task_details_qr_doc_id_fkey "
            "FOREIGN KEY (qr_doc_id) REFERENCES qr_registry(qr_doc_id) ON DELETE RESTRICT",
        ]
    ),
    (
        'completion_status',
        'completion_status_serial_number_fkey',
        'serial_number',
        'RESTRICT',
        [
            "ALTER TABLE completion_status DROP CONSTRAINT IF EXISTS completion_status_serial_number_fkey",
            "ALTER TABLE completion_status ADD CONSTRAINT completion_status_serial_number_fkey "
            "FOREIGN KEY (serial_number) REFERENCES qr_registry(serial_number) ON DELETE RESTRICT",
        ]
    ),
]


def ensure_schema():
    """
    앱 시작 시 호출. 필수 컬럼과 FK 제약조건을 검증하고 누락 시 자동 적용.
    실패해도 앱 시작을 막지는 않지만, ERROR 로그를 남김.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # ── 1. 필수 컬럼 검증 ──────────────────────
        for table, column, ddl in REQUIRED_COLUMNS:
            cur.execute(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = %s AND column_name = %s",
                (table, column)
            )
            if not cur.fetchone():
                logger.warning(
                    f"[schema_check] 필수 컬럼 누락 감지: {table}.{column} — 자동 추가 실행"
                )
                cur.execute(ddl)
                conn.commit()
                logger.info(f"[schema_check] {table}.{column} 컬럼 추가 완료")
            else:
                logger.info(f"[schema_check] {table}.{column} ✓")

        # ── 2. FK 제약조건 검증 ────────────────────
        for table, constraint, column, expected_rule, fix_ddls in REQUIRED_CONSTRAINTS:
            cur.execute(
                """SELECT rc.delete_rule
                   FROM information_schema.table_constraints tc
                   JOIN information_schema.key_column_usage kcu
                       ON tc.constraint_name = kcu.constraint_name
                   JOIN information_schema.referential_constraints rc
                       ON tc.constraint_name = rc.constraint_name
                   WHERE tc.constraint_type = 'FOREIGN KEY'
                       AND tc.table_name = %s
                       AND kcu.column_name = %s""",
                (table, column)
            )
            row = cur.fetchone()
            if row and row['delete_rule'] == expected_rule:
                logger.info(f"[schema_check] {table}.{column} FK={expected_rule} ✓")
            else:
                current = row['delete_rule'] if row else 'MISSING'
                logger.warning(
                    f"[schema_check] FK 수정 필요: {table}.{column} "
                    f"현재={current}, 기대={expected_rule} — 자동 수정 실행"
                )
                for ddl in fix_ddls:
                    cur.execute(ddl)
                conn.commit()
                logger.info(f"[schema_check] {table}.{column} FK → {expected_rule} 변경 완료")

        logger.info("[schema_check] DB 스키마 검증 완료 — 모든 항목 정상")

    except PsycopgError as e:
        logger.error(f"[schema_check] DB 스키마 검증 실패: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        logger.error(f"[schema_check] 예상치 못한 오류: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
