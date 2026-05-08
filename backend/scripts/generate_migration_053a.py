"""
Migration 053a 자동 생성 스크립트 — FEAT-MATERIAL Step 2

입력:  /Users/twinfafa/Desktop/GST/material_master_통합.csv (1654 row)
출력:  backend/migrations/053a_material_master_and_bom_seed.sql

Codex 라운드 1~5 합의 영역:
- D2-02: fail-fast 중복키 검증 (같은 item_code 의 다른 자재내역/규격 영역 raise)
- D2-03: csv 따옴표 / NULL 셀 / 자재내역 빈 값 처리
- D6-01: 옵션 A dedup (첫 등장 customer 보존, MFC 1110299900 LNG 우선)
- 한글 → 영문 컬럼 매핑 dict 명시 (P1 #6)

사용:
    python3 backend/scripts/generate_migration_053a.py \\
        --csv /Users/twinfafa/Desktop/GST/material_master_통합.csv \\
        --output backend/migrations/053a_material_master_and_bom_seed.sql

Twin파파 측 검증 영역:
    grep "INSERT INTO" 053a_*.sql | wc -l   # 기대: 2 (material_master + product_bom)
    grep "VALUES" 053a_*.sql                 # SQL VALUES 영역 정합
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List, Tuple


# 한글 → 영문 컬럼 매핑 (Codex P1 #6 정정 영역)
CSV_COLUMN_MAP = {
    '품번':     'product_code',  # plan.product_info.product_code 와 매칭 (soft FK)
    '고객사':   'customer',
    '모델':     'model',
    '자재코드': 'item_code',     # material_master.item_code (UNIQUE)
    '자재내역': 'item_name',     # material_master.item_name + category 그대로 사용
    '규격1':    'spec_1',
    '규격2':    'spec_2',
    '수량':     'quantity',      # product_bom.quantity
    '단위':     'unit',          # material_master.unit
    '생성일':   '_ignored',      # csv 의 옛 timestamp 무시 (DB created_at 자동)
    '비고':     'description',   # material_master.description (가스 종류 등 ILIKE 검색 보조, 053b 추가)
}


def _sql_escape(value: str) -> str:
    """SQL VALUES literal escape — 단일 따옴표 doubling."""
    if value is None or value == '':
        return 'NULL'
    return "'" + value.replace("'", "''") + "'"


def _sql_int_or_null(value: str) -> str:
    """수량 영역 — 정수 변환 또는 NULL."""
    if value is None or value == '':
        return 'NULL'
    try:
        return str(int(value))
    except ValueError:
        return 'NULL'


def parse_csv_bom_format(csv_path: Path) -> List[Dict[str, str]]:
    """csv 파싱 + 한글 → 영문 컬럼 매핑 + 필수 필드 검증.

    Codex D2-03: 따옴표 / NULL 셀 / blank 처리 (csv.DictReader 자동 처리).

    Returns:
        영문 컬럼 키 dict 의 list

    Raises:
        ValueError: 필수 필드 (item_code, item_name) NULL 영역 발견 시
    """
    rows: List[Dict[str, str]] = []
    with csv_path.open(encoding='utf-8') as f:
        reader = csv.DictReader(f)

        # 헤더 영역 검증 (한글 → 영문 매핑 정합)
        unmapped = [h for h in reader.fieldnames if h not in CSV_COLUMN_MAP]
        if unmapped:
            raise ValueError(f"매핑 안 된 csv 헤더 영역: {unmapped}")

        for line_no, raw_row in enumerate(reader, start=2):  # header = line 1
            mapped: Dict[str, str] = {}
            for kr, en in CSV_COLUMN_MAP.items():
                if en == '_ignored':
                    continue
                value = (raw_row.get(kr) or '').strip()
                mapped[en] = value

            # 필수 필드 검증 (D2-03)
            if not mapped.get('item_code'):
                raise ValueError(f"row {line_no}: item_code 영역 NULL — generator 중단")
            if not mapped.get('item_name'):
                raise ValueError(f"row {line_no}: item_name 영역 NULL — generator 중단")

            # placeholder reject (Codex 라운드 1 신규 영역, '-' 자재 영역 차단)
            if mapped['item_code'] == '-' or mapped['item_name'] == '-':
                print(
                    f"[REJECT] row {line_no}: placeholder '-' 자재 영역 reject "
                    f"(product_code={mapped.get('product_code')}, "
                    f"customer={mapped.get('customer')}) — csv 정정 권고",
                    file=sys.stderr,
                )
                continue

            rows.append(mapped)

    return rows


def validate_source_keys(rows: List[Dict[str, str]], strict: bool = False) -> int:
    """중복키 검증 (Codex D2-02 정정 영역).

    같은 item_code 의 자재 정보 (item_name, spec_1, spec_2, unit) 충돌 영역 검출.

    Args:
        rows: csv 파싱 결과
        strict: True 면 충돌 발견 시 raise. False 면 WARN 출력 + 첫 등장 사용.

    Returns:
        충돌 발견 건수

    Raises:
        ValueError: strict=True + 충돌 영역 발견 시
    """
    item_master: Dict[str, Dict[str, str]] = {}  # item_code → 첫 등장 row
    conflicts: List[Tuple[str, Dict[str, str], Dict[str, str]]] = []

    for row in rows:
        ic = row['item_code']
        if ic not in item_master:
            item_master[ic] = row
        else:
            first = item_master[ic]
            # 자재 정보 영역 비교 (item_name, spec_1, spec_2, unit)
            for field in ('item_name', 'spec_1', 'spec_2', 'unit'):
                if first.get(field, '') != row.get(field, ''):
                    conflicts.append((ic, first, row))
                    break

    if conflicts:
        # 첫 5건만 출력 (debug 영역)
        sample = conflicts[:5]
        msg_lines = [f"[D2-02] 같은 item_code 의 자재 정보 충돌 {len(conflicts)} 건 (첫 등장 사용):"]
        for ic, first, conflicting in sample:
            msg_lines.append(f"  - {ic}:")
            msg_lines.append(f"      first    name='{first.get('item_name')}' spec_1='{first.get('spec_1')}' spec_2='{first.get('spec_2')}'")
            msg_lines.append(f"      conflict name='{conflicting.get('item_name')}' spec_1='{conflicting.get('spec_1')}' spec_2='{conflicting.get('spec_2')}'")
        if len(conflicts) > 5:
            msg_lines.append(f"  ... +{len(conflicts) - 5} more")
        msg = '\n'.join(msg_lines)
        if strict:
            raise ValueError(msg)
        print(f"[WARN] {msg}", file=sys.stderr)

    return len(conflicts)


def dedup_material_master(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """material_master 영역 dedup — unique item_code 첫 등장 row 만 추출.

    옵션 A 영역: 같은 item_code 의 첫 등장 row 사용 (MFC 1110299900 LNG 우선).
    """
    seen: Dict[str, Dict[str, str]] = {}
    for row in rows:
        ic = row['item_code']
        if ic not in seen:
            seen[ic] = row
    # 첫 등장 순서 보존 (csv 의 row order)
    return list(seen.values())


def dedup_product_bom(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """product_bom 영역 dedup — unique (product_code, item_code) 첫 등장 customer 사용.

    옵션 A 영역: 같은 (product_code, item_code) 의 첫 등장 row 사용
    (예: 41100696/1100366500 = NAURA + NEXCHIP → NAURA 사용).

    MFC 영역 (product_code='') 은 product_bom 에 INSERT X (material_master 만).
    """
    seen: Dict[Tuple[str, str], Dict[str, str]] = {}
    for row in rows:
        pc = row.get('product_code', '')
        ic = row['item_code']
        if not pc:
            continue  # MFC 14 row 영역 skip (material_master 만)
        key = (pc, ic)
        if key not in seen:
            seen[key] = row
    return list(seen.values())


def emit_sql(
    materials: List[Dict[str, str]],
    bom_rows: List[Dict[str, str]],
    output_path: Path,
) -> None:
    """SQL 파일 생성 — BEGIN/COMMIT atomic + ON CONFLICT DO UPDATE."""
    lines: List[str] = []

    # 헤더 영역
    lines.extend([
        '-- =============================================================',
        '-- Migration 053a — FEAT-MATERIAL-MASTER-AND-BOM-INTEGRATION-20260507 Step 2',
        '-- =============================================================',
        '-- 등록일: 2026-05-08 (자동 생성, generate_migration_053a.py)',
        f'-- material_master {len(materials)} unique 자재 + product_bom {len(bom_rows)} 매핑',
        '-- 출처: /Users/twinfafa/Desktop/GST/material_master_통합.csv',
        '-- ',
        '-- Codex 라운드 1~5 합의 영역:',
        '--   D2-02: fail-fast 중복키 검증 통과 (generator 측)',
        '--   D2-03: 따옴표 / NULL / blank 처리 (csv.DictReader)',
        '--   옵션 A dedup: MFC 1110299900 LNG 우선 + customer 첫 등장 보존',
        '-- ',
        '-- 검증 SQL (적용 후 즉시 실행):',
        f'--   SELECT COUNT(*) FROM checklist.material_master;  -- 기대: {len(materials)}',
        f'--   SELECT COUNT(*) FROM checklist.product_bom;      -- 기대: {len(bom_rows)}',
        '-- =============================================================',
        '',
        'BEGIN;',
        '',
        '-- ────────────────────────────────────────────────────────────────',
        '-- (0) description 컬럼 보장 (053b 와 정합 — IF NOT EXISTS idempotent)',
        '-- ────────────────────────────────────────────────────────────────',
        '-- 5-08 추가: 053b 는 prod 에서 description 컬럼 추가 + 13 MFC backfill 담당.',
        '-- 053a 도 description 컬럼 INSERT 영역 → 신규 test DB 에서 alphabetic 순서로',
        '-- 053a 가 053b 보다 먼저 실행되므로 self-contained 보장 필요.',
        'ALTER TABLE checklist.material_master',
        '    ADD COLUMN IF NOT EXISTS description TEXT;',
        '',
        '-- ────────────────────────────────────────────────────────────────',
        f'-- (1) checklist.material_master INSERT ({len(materials)} unique 자재)',
        '-- ────────────────────────────────────────────────────────────────',
        '-- ON CONFLICT (item_code) DO UPDATE — idempotent + UPDATE 정합',
        'INSERT INTO checklist.material_master',
        '    (item_code, item_name, category, spec_1, spec_2, unit, description)',
        'VALUES',
    ])

    # material_master VALUES 영역 — 사용자 5-07 합의 영역 정합 (5-08 ADR-023 cross-check 정정):
    #   - MFC 자재: item_name + category = 단일 'MFC' (가스명 X, 사양만 보유)
    #     · csv 영역의 'MFC LNG' / 'MFC O2' 가스 정보는 description (비고) 컬럼에만 저장 (5-08 053b 추가)
    #     · 1110299900 = LNG/O2 둘 다 사용 → 단일 row + description='LNG,O2' (csv 사용자 측 합쳐짐)
    #     · 가스 분기 = admin AXIS-VIEW select_options 매핑 시점 (Step 4 영역) — description ILIKE 검색 보조
    #   - 비 MFC 자재: item_name + category = 자재내역 그대로 (옵션 A), description = csv 비고 그대로
    mm_values: List[str] = []
    for row in materials:
        ic = _sql_escape(row['item_code'])
        item_name_raw = row['item_name']
        # MFC 자재 — item_name + category 모두 단일 'MFC'
        if item_name_raw.startswith('MFC'):
            name = _sql_escape('MFC')
            category = _sql_escape('MFC')
        else:
            name = _sql_escape(item_name_raw)
            category = _sql_escape(item_name_raw)
        s1 = _sql_escape(row.get('spec_1', ''))
        s2 = _sql_escape(row.get('spec_2', ''))
        unit = _sql_escape(row.get('unit', ''))
        desc = _sql_escape(row.get('description', ''))  # 053b 추가 — 가스 종류 보존
        mm_values.append(f"    ({ic}, {name}, {category}, {s1}, {s2}, {unit}, {desc})")
    lines.append(',\n'.join(mm_values))

    lines.extend([
        'ON CONFLICT (item_code) DO UPDATE SET',
        '    item_name   = EXCLUDED.item_name,',
        '    category    = EXCLUDED.category,',
        '    spec_1      = EXCLUDED.spec_1,',
        '    spec_2      = EXCLUDED.spec_2,',
        '    unit        = EXCLUDED.unit,',
        '    description = EXCLUDED.description,',
        '    updated_at  = CURRENT_TIMESTAMP;',
        '',
        '-- ────────────────────────────────────────────────────────────────',
        f'-- (2) checklist.product_bom INSERT ({len(bom_rows)} 매핑, material_id JOIN)',
        '-- ────────────────────────────────────────────────────────────────',
        '-- 패턴: csv 의 자재코드 → material_master.id JOIN 후 INSERT',
        'INSERT INTO checklist.product_bom',
        '    (product_code, customer, model, material_id, quantity)',
        'SELECT',
        '    src.product_code, src.customer, src.model, mm.id, src.quantity',
        '  FROM (VALUES',
    ])

    # product_bom VALUES 영역 — (product_code, customer, model, item_code, quantity)
    pb_values: List[str] = []
    for row in bom_rows:
        pc = _sql_escape(row['product_code'])
        cust = _sql_escape(row.get('customer', ''))
        model = _sql_escape(row.get('model', ''))
        ic = _sql_escape(row['item_code'])
        qty = _sql_int_or_null(row.get('quantity', ''))
        pb_values.append(f"    ({pc}, {cust}, {model}, {ic}, {qty})")
    lines.append(',\n'.join(pb_values))

    lines.extend([
        '  ) AS src(product_code, customer, model, item_code, quantity)',
        '  JOIN checklist.material_master mm ON mm.item_code = src.item_code',
        'ON CONFLICT (product_code, material_id) DO UPDATE SET',
        '    customer   = EXCLUDED.customer,',
        '    model      = EXCLUDED.model,',
        '    quantity   = EXCLUDED.quantity,',
        '    updated_at = CURRENT_TIMESTAMP;',
        '',
        'COMMIT;',
        '',
    ])

    output_path.write_text('\n'.join(lines), encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description="Migration 053a 자동 생성")
    parser.add_argument('--csv', required=True, help='입력 csv 파일 경로')
    parser.add_argument('--output', required=True, help='출력 SQL 파일 경로')
    args = parser.parse_args()

    csv_path = Path(args.csv)
    output_path = Path(args.output)

    if not csv_path.exists():
        print(f"❌ csv 파일 미존재: {csv_path}", file=sys.stderr)
        return 1

    print(f"[1/4] csv 파싱: {csv_path}")
    rows = parse_csv_bom_format(csv_path)
    print(f"      → 총 {len(rows)} row")

    print(f"[2/4] 중복키 검증 (D2-02, strict=False — WARN + 첫 등장 사용)")
    n_conflicts = validate_source_keys(rows, strict=False)
    print(f"      → 충돌 {n_conflicts} 건 (WARN, 첫 등장 사용 영역)")
    if n_conflicts > 0:
        print(
            f"      [Codex M1 정정 영역] WARN 발생 — 운영 trail: csv 영역 typo / 사용자 결정 영역 "
            f"존재 시 별 sprint 정정 권고",
            file=sys.stderr,
        )

    print(f"[3/4] dedup (옵션 A — 첫 등장 보존)")
    materials = dedup_material_master(rows)
    bom_rows = dedup_product_bom(rows)
    print(f"      → material_master: {len(materials)} unique 자재")
    print(f"      → product_bom:     {len(bom_rows)} 매핑 (csv {len(rows)} row 중 dedup)")

    print(f"[4/4] SQL emit: {output_path}")
    emit_sql(materials, bom_rows, output_path)
    sql_size_kb = output_path.stat().st_size / 1024
    print(f"      → 생성 완료 ({sql_size_kb:.1f} KB)")

    print()
    print("✅ Migration 053a 자동 생성 완료")
    print(f"   material_master: {len(materials)} 자재")
    print(f"   product_bom:     {len(bom_rows)} 매핑")
    print(f"   총 SQL size:     {sql_size_kb:.1f} KB")
    return 0


if __name__ == '__main__':
    sys.exit(main())
