"""
Migration 053 schema 정합 검증 — FEAT-MATERIAL-MASTER-AND-BOM-INTEGRATION-20260507 Step 1

검증 영역:
[1] checklist schema 의 3 신규 테이블 (material_master / product_bom / bom_checklist_log) 존재
[2] public 의 3 폐기 테이블 (product_bom / bom_checklist_log / bom_csv_import) 부재
[3] FK 정합 (product_bom.material_id RESTRICT, bom_checklist_log.bom_item_id RESTRICT)
[4] UNIQUE 제약 (material_master.item_code, product_bom (product_code, material_id))
[5] NOT NULL 제약 (D1-02 — boolean / timestamp 영역)
[6] checklist_record.selected_material_id 컬럼 존재 (NEW-M-01 정정)
[7] qr_doc_id 컬럼 존재 + google_doc_id 부재 (TC-NEW-09, D1-01 정정)
[8] updated_at 트리거 3건 존재
[9] 인덱스 정합 (partial WHERE is_active 등)

Codex 라운드 1~5 합의 영역 (RED → AMBER → GREEN trail):
- D1-01: google_doc_id → qr_doc_id 표준 준수
- D1-02: NOT NULL 제약 보강
- D1-03: DROP 순서 자식 → 부모
- NEW-M-01: selected_material_id INTEGER FK
"""

import sys
from pathlib import Path

_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest


# ═════════════════════════════════════════════════════════════════════════════
# [1] checklist schema 3 신규 테이블 존재 검증
# ═════════════════════════════════════════════════════════════════════════════

def test_migration_053_creates_checklist_tables(db_conn):
    """Migration 053 후 checklist schema 의 3 신규 테이블 존재 검증."""
    if db_conn is None:
        pytest.skip("DB 연결 없음 (sqlite 환경)")

    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT table_name FROM information_schema.tables
             WHERE table_schema = 'checklist'
               AND table_name IN ('material_master', 'product_bom', 'bom_checklist_log')
             ORDER BY table_name
        """)
        tables = {r[0] for r in cur.fetchall()}

    expected = {'material_master', 'product_bom', 'bom_checklist_log'}
    assert tables == expected, (
        f"checklist schema 의 3 신규 테이블 정합 실패: "
        f"기대 {expected}, 실제 {tables}"
    )


# ═════════════════════════════════════════════════════════════════════════════
# [2] public 3 폐기 테이블 부재 검증
# ═════════════════════════════════════════════════════════════════════════════

def test_migration_053_drops_public_legacy_tables(db_conn):
    """Migration 053 후 public 의 3 폐기 테이블 (product_bom / bom_checklist_log / bom_csv_import) 부재."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM information_schema.tables
             WHERE table_schema = 'public'
               AND table_name IN ('product_bom', 'bom_checklist_log', 'bom_csv_import')
        """)
        count = cur.fetchone()[0]

    assert count == 0, f"public 폐기 테이블 잔존: {count} 건 (기대 0)"


# ═════════════════════════════════════════════════════════════════════════════
# [3] FK 정합 (RESTRICT)
# ═════════════════════════════════════════════════════════════════════════════

def test_migration_053_fk_constraints_restrict(db_conn):
    """product_bom.material_id + bom_checklist_log.bom_item_id 의 FK + RESTRICT 영역 검증."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT
                tc.table_name,
                kcu.column_name,
                ccu.table_schema || '.' || ccu.table_name AS foreign_table,
                rc.delete_rule
              FROM information_schema.table_constraints tc
              JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
               AND tc.constraint_schema = kcu.constraint_schema
              JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
               AND ccu.constraint_schema = tc.constraint_schema
              JOIN information_schema.referential_constraints rc
                ON rc.constraint_name = tc.constraint_name
               AND rc.constraint_schema = tc.constraint_schema
             WHERE tc.constraint_type = 'FOREIGN KEY'
               AND tc.table_schema = 'checklist'
               AND tc.table_name IN ('product_bom', 'bom_checklist_log', 'checklist_record')
               AND kcu.column_name IN ('material_id', 'bom_item_id', 'selected_material_id')
             ORDER BY tc.table_name, kcu.column_name
        """)
        fks = cur.fetchall()

    fk_map = {(t, c): (ft, dr) for t, c, ft, dr in fks}

    assert ('product_bom', 'material_id') in fk_map, "product_bom.material_id FK 미존재"
    assert fk_map[('product_bom', 'material_id')] == ('checklist.material_master', 'RESTRICT'), \
        f"product_bom.material_id FK 정합 실패: {fk_map[('product_bom', 'material_id')]}"

    assert ('bom_checklist_log', 'bom_item_id') in fk_map, "bom_checklist_log.bom_item_id FK 미존재"
    assert fk_map[('bom_checklist_log', 'bom_item_id')] == ('checklist.product_bom', 'RESTRICT'), \
        f"bom_checklist_log.bom_item_id FK 정합 실패: {fk_map[('bom_checklist_log', 'bom_item_id')]}"

    # NEW-M-01 정정: checklist_record.selected_material_id FK
    assert ('checklist_record', 'selected_material_id') in fk_map, \
        "checklist_record.selected_material_id FK 미존재 (NEW-M-01)"
    assert fk_map[('checklist_record', 'selected_material_id')] == ('checklist.material_master', 'RESTRICT'), \
        f"checklist_record.selected_material_id FK 정합 실패: {fk_map[('checklist_record', 'selected_material_id')]}"


# ═════════════════════════════════════════════════════════════════════════════
# [4] UNIQUE 제약 영역
# ═════════════════════════════════════════════════════════════════════════════

def test_migration_053_unique_constraints(db_conn):
    """material_master.item_code UNIQUE + product_bom (product_code, material_id) UNIQUE 검증.

    Codex 라운드 1 A1 정정: 컬럼 명시 검증 (수만 검증 → 정확 컬럼 매칭).
    """
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    with db_conn.cursor() as cur:
        # 모든 UNIQUE 제약의 컬럼 영역 수집 (Python 측 group by — psycopg2 array 호환)
        cur.execute("""
            SELECT tc.table_name, tc.constraint_name, kcu.column_name
              FROM information_schema.table_constraints tc
              JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
               AND tc.constraint_schema = kcu.constraint_schema
             WHERE tc.constraint_schema = 'checklist'
               AND tc.table_name IN ('material_master', 'product_bom')
               AND tc.constraint_type = 'UNIQUE'
             ORDER BY tc.table_name, tc.constraint_name, kcu.ordinal_position
        """)
        rows = cur.fetchall()

    # group by (table_name, constraint_name) → ordered column list
    grouped: dict = {}
    for tn, cn, col in rows:
        grouped.setdefault((tn, cn), []).append(col)

    # material_master.item_code 단일 컬럼 UNIQUE
    mm_uniques = [cols for (tn, _), cols in grouped.items() if tn == 'material_master']
    assert ['item_code'] in mm_uniques, (
        f"material_master.item_code UNIQUE 컬럼 미존재 (Codex A1): {mm_uniques}"
    )

    # product_bom (product_code, material_id) 복합 UNIQUE
    pb_uniques = [cols for (tn, _), cols in grouped.items() if tn == 'product_bom']
    assert ['product_code', 'material_id'] in pb_uniques, (
        f"product_bom (product_code, material_id) UNIQUE 컬럼 미존재 (Codex A1): {pb_uniques}"
    )


# ═════════════════════════════════════════════════════════════════════════════
# [5] NOT NULL 제약 (D1-02 정정)
# ═════════════════════════════════════════════════════════════════════════════

def test_migration_053_not_null_constraints_d1_02(db_conn):
    """D1-02 정정 영역 — boolean / timestamp 컬럼의 NOT NULL 제약 검증."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT table_name, column_name, is_nullable
              FROM information_schema.columns
             WHERE table_schema = 'checklist'
               AND table_name IN ('material_master', 'product_bom', 'bom_checklist_log')
               AND column_name IN ('is_active', 'is_checked', 'mismatch_reported',
                                   'created_at', 'updated_at')
             ORDER BY table_name, column_name
        """)
        rows = cur.fetchall()

    # 모든 row 가 NO (NOT NULL)
    not_null_violations = [(t, c) for t, c, n in rows if n != 'NO']
    assert not not_null_violations, (
        f"D1-02 NOT NULL 위반 영역: {not_null_violations}"
    )


# ═════════════════════════════════════════════════════════════════════════════
# [6] checklist_record.selected_material_id 컬럼 존재 (NEW-M-01 정정)
# ═════════════════════════════════════════════════════════════════════════════

def test_migration_053_checklist_record_selected_material_id_added(db_conn):
    """NEW-M-01 정정 영역 — checklist_record.selected_material_id INTEGER 컬럼 추가 검증."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT data_type, is_nullable
              FROM information_schema.columns
             WHERE table_schema = 'checklist'
               AND table_name = 'checklist_record'
               AND column_name = 'selected_material_id'
        """)
        row = cur.fetchone()

    assert row is not None, "checklist_record.selected_material_id 컬럼 미존재 (NEW-M-01)"
    data_type, is_nullable = row
    assert data_type == 'integer', f"selected_material_id 타입 정합 실패: {data_type} (기대 integer)"
    assert is_nullable == 'YES', f"selected_material_id NULL 허용 영역 (legacy 호환): {is_nullable}"


# ═════════════════════════════════════════════════════════════════════════════
# [7] TC-NEW-09 — qr_doc_id 컬럼 존재 + google_doc_id 부재 (D1-01 정정)
# ═════════════════════════════════════════════════════════════════════════════

def test_migration_053_uses_qr_doc_id_not_google_doc_id(db_conn):
    """TC-NEW-09 / D1-01 정정 영역 — bom_checklist_log 의 qr_doc_id 컬럼 + google_doc_id 부재."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
              FROM information_schema.columns
             WHERE table_schema = 'checklist'
               AND table_name = 'bom_checklist_log'
               AND column_name IN ('qr_doc_id', 'google_doc_id')
        """)
        cols = {r[0] for r in cur.fetchall()}

    assert 'qr_doc_id' in cols, (
        "TC-NEW-09: bom_checklist_log.qr_doc_id 컬럼 미존재 (D1-01 표준 위반)"
    )
    assert 'google_doc_id' not in cols, (
        "TC-NEW-09: bom_checklist_log.google_doc_id 컬럼 잔존 (D1-01 표준 위반 — CLAUDE.md L72)"
    )


# ═════════════════════════════════════════════════════════════════════════════
# [8] updated_at 트리거 3건 존재
# ═════════════════════════════════════════════════════════════════════════════

def test_migration_053_updated_at_triggers_exist(db_conn):
    """3 신규 테이블의 updated_at 자동 갱신 트리거 검증."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT trigger_name, event_object_table
              FROM information_schema.triggers
             WHERE event_object_schema = 'checklist'
               AND event_object_table IN ('material_master', 'product_bom', 'bom_checklist_log')
               AND action_timing = 'BEFORE'
               AND event_manipulation = 'UPDATE'
             ORDER BY event_object_table
        """)
        triggers = {t for _, t in cur.fetchall()}

    expected = {'material_master', 'product_bom', 'bom_checklist_log'}
    assert triggers == expected, (
        f"updated_at 트리거 정합 실패: 기대 {expected}, 실제 {triggers}"
    )


# ═════════════════════════════════════════════════════════════════════════════
# [9] 인덱스 정합 (partial WHERE is_active)
# ═════════════════════════════════════════════════════════════════════════════

def test_migration_053_indexes_exist(db_conn):
    """주요 인덱스 (material_master.category partial, product_bom.product_code partial 등) 존재 검증.

    Codex 라운드 1 A2 정정: partial predicate 영역 검증 (pg_index.indpred 통해 WHERE 조건 정합).
    """
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    expected_indexes = {
        'idx_material_master_category',
        'idx_material_master_item_name',
        'idx_product_bom_product_code',
        'idx_product_bom_material_id',
        'idx_bom_checklist_log_serial',
        'idx_bom_checklist_log_bom_item',
        'idx_checklist_record_selected_material_id',
    }

    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT indexname FROM pg_indexes
             WHERE schemaname = 'checklist'
               AND indexname = ANY(%s)
        """, (list(expected_indexes),))
        existing = {r[0] for r in cur.fetchall()}

    missing = expected_indexes - existing
    assert not missing, f"인덱스 누락: {missing}"

    # Codex A2: partial predicate 영역 검증 (pg_index.indpred 통해)
    # partial 인덱스 3건:
    #   - idx_material_master_category WHERE is_active = TRUE
    #   - idx_product_bom_product_code WHERE is_active = TRUE
    #   - idx_checklist_record_selected_material_id WHERE selected_material_id IS NOT NULL
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT i.relname AS indexname,
                   pg_get_expr(idx.indpred, idx.indrelid) AS predicate
              FROM pg_index idx
              JOIN pg_class i ON i.oid = idx.indexrelid
              JOIN pg_class t ON t.oid = idx.indrelid
              JOIN pg_namespace n ON n.oid = t.relnamespace
             WHERE n.nspname = 'checklist'
               AND i.relname = ANY(%s)
        """, (['idx_material_master_category',
               'idx_product_bom_product_code',
               'idx_checklist_record_selected_material_id'],))
        partials = {r[0]: r[1] for r in cur.fetchall()}

    # PostgreSQL pg_get_expr() 는 partial WHERE 식을 괄호 wrapping 반환 ("(is_active = true)")
    # → strip('()') 후 비교
    def _normalize(expr):
        return (expr or '').strip('()').strip()

    assert _normalize(partials.get('idx_material_master_category')) == 'is_active = true', (
        f"idx_material_master_category partial WHERE 정합 실패: {partials.get('idx_material_master_category')}"
    )
    assert _normalize(partials.get('idx_product_bom_product_code')) == 'is_active = true', (
        f"idx_product_bom_product_code partial WHERE 정합 실패: {partials.get('idx_product_bom_product_code')}"
    )
    assert _normalize(partials.get('idx_checklist_record_selected_material_id')) == 'selected_material_id IS NOT NULL', (
        f"idx_checklist_record_selected_material_id partial WHERE 정합 실패: "
        f"{partials.get('idx_checklist_record_selected_material_id')}"
    )
