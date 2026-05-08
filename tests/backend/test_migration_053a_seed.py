"""
Migration 053a seed 정합 검증 — FEAT-MATERIAL-MASTER-AND-BOM-INTEGRATION-20260507 Step 2

검증 영역 (5-07 사용자 합의 + 5-08 ADR-023 cross-check 정정 후):
[1] material_master 185 unique 자재 INSERT 정합 (csv 173 + MFC 13 - placeholder 1)
[2] product_bom 1626 매핑 (csv 1640 - 13 dedup - 1 placeholder) 정합
[3] MFC category 분포 — 단일 'MFC' category + item_name 가스 분기 보존 (가스 분기 = Step 4 admin 매핑 영역)
[4] product_code='41200076' 의 BOM JOIN 정합 (sample)
[5] '-' placeholder 자재 reject 검증 (Codex M1 신규 영역)
[6] item_name 가스 분기 보존 (1110299900 = 'MFC LNG' — 사용자 결정, LNG 우선)

Codex 라운드 1 추가 TC:
[TC-NEW-07] generator dedup 영역 검증 (D2-02 정정 영역)
[TC-NEW-08] csv 따옴표 / 쌍따옴표 / blank 영역 처리 검증 (D2-03 정정 영역)
"""

import sys
from pathlib import Path

_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest


# ═════════════════════════════════════════════════════════════════════════════
# Step 2 seed 영역 검증 (4 TC)
# ═════════════════════════════════════════════════════════════════════════════

def test_material_master_seeded_185_unique(db_conn):
    """Migration 053a 후 material_master 185 unique 자재 INSERT 검증.

    Codex 라운드 1 M3 정정: 186 → 185 (csv row 720 의 '-' placeholder reject 영역, M1 정정).
    """
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    with db_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM checklist.material_master")
        count = cur.fetchone()[0]

    assert count == 185, (
        f"material_master 자재 수 정합 실패: 기대 185, 실제 {count} "
        f"(csv 173 + MFC 14 - 1110299900 LNG/O2 1 dedup - '-' placeholder 1 = 185)"
    )

    # placeholder 부재 검증
    with db_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM checklist.material_master WHERE item_code = '-'")
        placeholder_count = cur.fetchone()[0]
    assert placeholder_count == 0, f"'-' placeholder 자재 잔존: {placeholder_count} (M1 정정 영역 위반)"


def test_product_bom_seeded_1626_with_material_join(db_conn):
    """Migration 053a 후 product_bom 1626 매핑 + material_id JOIN 정합 검증.

    Codex 라운드 1 M3 정정: 1627 → 1626 ('-' placeholder reject 영역, M1 정정).
    """
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    with db_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM checklist.product_bom")
        bom_count = cur.fetchone()[0]
    assert bom_count == 1626, (
        f"product_bom 매핑 수 정합 실패: 기대 1626 (csv 1640 - 13 dedup - 1 placeholder), 실제 {bom_count}"
    )

    # JOIN 정합 — orphan material_id 0건
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM checklist.product_bom pb
             WHERE NOT EXISTS (
                 SELECT 1 FROM checklist.material_master mm WHERE mm.id = pb.material_id
             )
        """)
        orphans = cur.fetchone()[0]
    assert orphans == 0, f"product_bom orphan material_id 영역: {orphans} 건 (FK 위반)"


def test_mfc_category_distribution(db_conn):
    """MFC 자재 카테고리 분포 — 13 unique, 단일 'MFC' category (가스 분기 = description, Step 4 매핑).

    5-08 정정 (ADR-023): MFC 자재의 item_name + category 모두 단일 'MFC' 통일.
    가스 종류 (LNG/CDA/O2/N2) 는 description 컬럼에서 보존 (053b 추가).
    1110299900 = LNG/O2 dual-use → 단일 row + description='LNG,O2'.
    """
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM checklist.material_master
             WHERE category = 'MFC'
        """)
        mfc_count = cur.fetchone()[0]

    assert mfc_count == 13, (
        f"MFC 자재 수 정합 실패: 기대 13 (1110299900 LNG/O2 단일화), 실제 {mfc_count}"
    )

    # 1110299900 = 단일 'MFC' + description='LNG,O2' (dual-use 보존)
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT item_name, category, description FROM checklist.material_master
             WHERE item_code = '1110299900'
        """)
        row = cur.fetchone()
    assert row is not None, "1110299900 자재 미존재"
    item_name, category, description = row[0], row[1], row[2]
    assert item_name == 'MFC', f"1110299900 item_name 정합 실패: 기대 'MFC', 실제 '{item_name}'"
    assert category == 'MFC', f"1110299900 category 정합 실패: 기대 'MFC', 실제 '{category}'"
    assert description == 'LNG,O2', (
        f"1110299900 description 정합 실패: 기대 'LNG,O2' (dual-use), 실제 '{description}'"
    )


def test_mfc_description_backfill_13_rows(db_conn):
    """Migration 053b — 13 MFC 자재 description backfill 정합 + ILIKE 검색 정합.

    분포: LNG 5 + LNG,O2 1 + CDA 2 + O2 4 + N2 1 = 13
    ILIKE 검색 (admin AXIS-VIEW 시뮬레이션):
      - %LNG% → 6 hits (5 LNG + 1 dual)
      - %O2%  → 5 hits (4 O2 + 1 dual)
      - 1110299900 → LNG/O2 양쪽 매칭 (dual-use 보존)
    """
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    with db_conn.cursor() as cur:
        # 13 MFC row description 모두 NOT NULL
        cur.execute("""
            SELECT COUNT(*) FROM checklist.material_master
             WHERE category = 'MFC' AND description IS NOT NULL
        """)
        described = cur.fetchone()[0]
    assert described == 13, f"MFC description backfill 정합 실패: 기대 13, 실제 {described}"

    # 비 MFC 자재는 description NULL (의도된 상태)
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM checklist.material_master
             WHERE category != 'MFC' AND description IS NOT NULL
        """)
        non_mfc_described = cur.fetchone()[0]
    assert non_mfc_described == 0, (
        f"비 MFC 자재 description 비정상 채워짐: {non_mfc_described} 건 (5-08 합의 영역 위반)"
    )

    # ILIKE 검색 정합 — admin AXIS-VIEW 시뮬레이션
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT
              (SELECT COUNT(*) FROM checklist.material_master WHERE description ILIKE '%LNG%'),
              (SELECT COUNT(*) FROM checklist.material_master WHERE description ILIKE '%O2%'),
              (SELECT COUNT(*) FROM checklist.material_master WHERE description ILIKE '%CDA%'),
              (SELECT COUNT(*) FROM checklist.material_master WHERE description ILIKE '%N2%')
        """)
        lng, o2, cda, n2 = cur.fetchone()
    assert lng == 6, f"LNG 검색 정합 실패: 기대 6 (5 LNG + 1 dual), 실제 {lng}"
    assert o2 == 5, f"O2 검색 정합 실패: 기대 5 (4 O2 + 1 dual), 실제 {o2}"
    assert cda == 2, f"CDA 검색 정합 실패: 기대 2, 실제 {cda}"
    assert n2 == 1, f"N2 검색 정합 실패: 기대 1, 실제 {n2}"

    # 1110299900 dual-use 검증 — LNG/O2 양쪽 ILIKE 매칭
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT
              (description ILIKE '%LNG%') AS hits_lng,
              (description ILIKE '%O2%')  AS hits_o2
              FROM checklist.material_master
             WHERE item_code = '1110299900'
        """)
        hits_lng, hits_o2 = cur.fetchone()
    assert hits_lng is True, "1110299900 LNG 검색 미매칭 — dual-use 보존 실패"
    assert hits_o2 is True, "1110299900 O2 검색 미매칭 — dual-use 보존 실패"


def test_product_bom_sample_join_41200076(db_conn):
    """product_code='41200076' 의 BOM JOIN 정합 sample 검증."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT mm.item_code, mm.item_name, pb.quantity
              FROM checklist.product_bom pb
              JOIN checklist.material_master mm ON pb.material_id = mm.id
             WHERE pb.product_code = '41200076'
             ORDER BY mm.item_code
        """)
        bom_rows = cur.fetchall()

    assert len(bom_rows) > 0, "41200076 BOM 매핑 미존재"

    # 알려진 영역 — 1100359600 (CLAMP) 가 quantity=12 로 매핑
    item_codes = {r[0] for r in bom_rows}
    assert '1100359600' in item_codes, (
        f"41200076 의 1100359600 (CLAMP) 매핑 미존재: {sorted(item_codes)}"
    )


# ═════════════════════════════════════════════════════════════════════════════
# Codex 라운드 1 추가 TC — generator 영역 (TC-NEW-07/08)
# ═════════════════════════════════════════════════════════════════════════════

def test_tc_new_07_generator_dedup_first_occurrence():
    """TC-NEW-07 / D2-02: generator 가 같은 item_code 의 첫 등장 row 만 보존."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'backend' / 'scripts'))
    from generate_migration_053a import dedup_material_master, validate_source_keys

    rows = [
        {'product_code': '41200001', 'customer': 'A', 'model': 'X', 'item_code': '1234',
         'item_name': 'BOLT', 'spec_1': 'M10', 'spec_2': '', 'unit': 'EA', 'quantity': '4'},
        {'product_code': '41200002', 'customer': 'B', 'model': 'Y', 'item_code': '1234',
         'item_name': 'BOLT', 'spec_1': 'M10', 'spec_2': '', 'unit': 'EA', 'quantity': '2'},
        {'product_code': '41200003', 'customer': 'C', 'model': 'Z', 'item_code': '5678',
         'item_name': 'NUT', 'spec_1': 'M10', 'spec_2': '', 'unit': 'EA', 'quantity': '1'},
    ]

    materials = dedup_material_master(rows)
    assert len(materials) == 2, f"unique item_code 영역 정합 실패: {len(materials)}"

    # 1234 = 첫 등장 = customer 'A'
    item_1234 = next(m for m in materials if m['item_code'] == '1234')
    assert item_1234['customer'] == 'A', f"첫 등장 customer 정합 실패: {item_1234['customer']}"


def test_tc_new_08_generator_handles_quoted_commas_and_nulls():
    """TC-NEW-08 / D2-03: generator 가 따옴표 안 콤마 / NULL / blank 처리."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'backend' / 'scripts'))
    from generate_migration_053a import _sql_escape, _sql_int_or_null

    # 따옴표 안 콤마 영역 (csv 의 "NW100,PVC")
    assert _sql_escape('NW100,PVC') == "'NW100,PVC'"

    # 단일 따옴표 escape (csv 의 "VCR, 태광, 1/2'")
    assert _sql_escape("VCR, 1/2'") == "'VCR, 1/2'''"

    # blank → NULL
    assert _sql_escape('') == 'NULL'
    assert _sql_escape(None) == 'NULL'

    # 정상 정수
    assert _sql_int_or_null('4') == '4'
    assert _sql_int_or_null('0') == '0'

    # NULL / blank → NULL
    assert _sql_int_or_null('') == 'NULL'
    assert _sql_int_or_null(None) == 'NULL'

    # 비정수 → NULL (defensive)
    assert _sql_int_or_null('abc') == 'NULL'


def test_tc_new_07b_generator_validate_source_keys_warns_conflicts():
    """TC-NEW-07 보강: validate_source_keys 가 충돌 영역 검출 (strict=False, WARN)."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'backend' / 'scripts'))
    from generate_migration_053a import validate_source_keys

    rows = [
        {'product_code': '41200001', 'customer': 'A', 'model': 'X', 'item_code': '1234',
         'item_name': 'BOLT', 'spec_1': 'M10', 'spec_2': '', 'unit': 'EA', 'quantity': '4'},
        {'product_code': '41200002', 'customer': 'B', 'model': 'Y', 'item_code': '1234',
         'item_name': 'NUT',  # ← spec_1 동일하지만 item_name 충돌
         'spec_1': 'M10', 'spec_2': '', 'unit': 'EA', 'quantity': '2'},
    ]

    n_conflicts = validate_source_keys(rows, strict=False)
    assert n_conflicts == 1, f"충돌 검출 정합 실패: 기대 1, 실제 {n_conflicts}"


def test_tc_new_07c_generator_validate_source_keys_raises_on_strict():
    """TC-NEW-07 보강: validate_source_keys(strict=True) 가 충돌 영역 raise."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'backend' / 'scripts'))
    from generate_migration_053a import validate_source_keys

    rows = [
        {'product_code': '41200001', 'customer': 'A', 'model': 'X', 'item_code': '1234',
         'item_name': 'BOLT', 'spec_1': 'M10', 'spec_2': '', 'unit': 'EA', 'quantity': '4'},
        {'product_code': '41200002', 'customer': 'B', 'model': 'Y', 'item_code': '1234',
         'item_name': 'NUT', 'spec_1': 'M10', 'spec_2': '', 'unit': 'EA', 'quantity': '2'},
    ]

    with pytest.raises(ValueError, match='D2-02'):
        validate_source_keys(rows, strict=True)


def test_tc_m2_parse_csv_rejects_placeholder_dash_rows(tmp_path):
    """Codex 라운드 1 M2 정정 영역: parse_csv_bom_format 이 '-' placeholder row reject.

    M1 정정 영역 검증 — main() 의 strict=False 실행 경로에서 placeholder 영역 silent skip.
    """
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'backend' / 'scripts'))
    from generate_migration_053a import parse_csv_bom_format

    csv_path = tmp_path / 'test.csv'
    csv_path.write_text(
        '품번,고객사,모델,자재코드,자재내역,규격1,규격2,수량,단위,생성일\n'
        '41200001,SEC,GAIA,1234,BOLT,M10,STD,4,EA,\n'  # 정상 row
        '41200002,VEONIS,GAIA,-,-,-,-,-,EA,\n'  # placeholder row (reject)
        '41200003,SEC,GAIA,5678,NUT,M10,STD,2,EA,\n',  # 정상 row
        encoding='utf-8',
    )

    rows = parse_csv_bom_format(csv_path)
    assert len(rows) == 2, f"placeholder reject 영역 정합 실패: 기대 2 row, 실제 {len(rows)}"
    item_codes = {r['item_code'] for r in rows}
    assert item_codes == {'1234', '5678'}, f"placeholder skip 영역 위반: {item_codes}"
    assert '-' not in item_codes, "'-' placeholder 자재 잔존 — M1 정정 영역 위반"


def test_tc_m2_parse_csv_raises_on_missing_required_field(tmp_path):
    """Codex 라운드 1 M2 정정 영역: parse_csv_bom_format 이 필수 필드 NULL 영역 raise."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'backend' / 'scripts'))
    from generate_migration_053a import parse_csv_bom_format

    csv_path = tmp_path / 'test_null.csv'
    csv_path.write_text(
        '품번,고객사,모델,자재코드,자재내역,규격1,규격2,수량,단위,생성일\n'
        '41200001,SEC,GAIA,,BOLT,M10,STD,4,EA,\n',  # item_code NULL
        encoding='utf-8',
    )

    with pytest.raises(ValueError, match='item_code 영역 NULL'):
        parse_csv_bom_format(csv_path)
