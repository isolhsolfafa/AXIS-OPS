"""
Material Upload Service — DB 대조 + 트랜잭션 commit (Sprint 66-BE-FOLLOWUP v3)

Codex 5라운드 검증 GREEN 정합:
  - material_master 6 필드 비교 (item_name/category/spec_1/spec_2/unit/description) + NULL/'' 정규화
  - product_bom Q2 정합 (quantity/customer/model 3 필드)
  - N+1 차단: pair-wise IN tuple (psycopg2 tuple adapter)
  - 트랜잭션: 검증 외부 + 정상 행만 트랜잭션 내부 (Sprint 64-BE v2 학습)
  - strategy: all / selected / skip
"""
import json
import logging
from typing import Dict, List, Any, Optional

from app.db_pool import put_conn
from app.models.worker import get_db_connection

logger = logging.getLogger(__name__)


# diff_with_db 영역 6 필드 비교 enum
DIFF_FIELDS = ('item_name', 'category', 'spec_1', 'spec_2', 'unit', 'description')


def _normalize(v: Optional[str]) -> str:
    """NULL/'' 정규화 — 둘 다 빈 문자열 영역 처리."""
    return (v or '').strip()


def diff_with_db(parsed_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """DB 와 대조 → new / changed / unchanged + bom_new / bom_changed 분류.

    v3 spec (Codex 라운드 5 GREEN):
      - material_master 6 필드 비교 (NULL/'' 정규화)
      - product_bom 3 필드 (quantity/customer/model)
      - N+1 차단: 단일 IN 쿼리

    Returns: UploadPreview schema dict
    """
    if not parsed_rows:
        return {
            'new_materials': [],
            'changed_materials': [],
            'unchanged_materials': [],
            'bom_mappings_new': 0,
            'bom_mappings_changed': 0,
            'total_rows': 0,
        }

    # 1) material_master 단일 IN 쿼리
    item_codes = list({r['item_code'] for r in parsed_rows if r.get('item_code')})
    existing_materials: Dict[str, Dict[str, Any]] = {}

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if item_codes:
            cur.execute(
                """
                SELECT id, item_code, item_name, category, spec_1, spec_2, unit, description
                FROM checklist.material_master
                WHERE item_code = ANY(%s)
                """,
                (item_codes,),
            )
            for row in cur.fetchall():
                existing_materials[row['item_code']] = dict(row)
    finally:
        put_conn(conn)

    new_materials: List[Dict[str, Any]] = []
    changed_materials: List[Dict[str, Any]] = []
    unchanged_materials: List[Dict[str, Any]] = []

    # MFC 합침된 영역 영역 unique item_code 영역 영역 영역 — material_master diff
    seen_item_codes: set = set()
    for row in parsed_rows:
        item_code = row['item_code']
        if item_code in seen_item_codes:
            continue
        seen_item_codes.add(item_code)

        existing = existing_materials.get(item_code)
        if not existing:
            new_materials.append({
                'item_code': item_code,
                'item_name': row.get('item_name', ''),
                'category': row.get('category'),
                'spec_1': row.get('spec_1') or None,
                'spec_2': row.get('spec_2') or None,
                'unit': row.get('unit') or None,
                'description': row.get('description') or None,
            })
            continue

        # 6 필드 비교 (NULL/'' 정규화)
        changes: List[Dict[str, Any]] = []
        for field in DIFF_FIELDS:
            before = _normalize(existing.get(field))
            after = _normalize(row.get(field))
            if before != after:
                changes.append({
                    'field': field,
                    'before': existing.get(field),
                    'after': row.get(field) or None,
                })

        if changes:
            changed_materials.append({'item_code': item_code, 'changes': changes})
        else:
            unchanged_materials.append({'item_code': item_code})

    # 2) product_bom 단일 pair-wise IN tuple 쿼리
    # BOM row 영역만 (product_code != '' 영역 영역)
    bom_rows = [r for r in parsed_rows if (r.get('product_code') or '').strip()]
    bom_mappings_new = 0
    bom_mappings_changed = 0

    if bom_rows:
        # (product_code, item_code) 영역 영역 영역 — material_id 매핑 영역 영역 영역
        # → material_master id 영역 영역 매핑 (existing or new — new 영역 영역 아직 INSERT 영역 X)
        # diff 영역 영역 — 기존 BOM 영역 (product_code, material_id) 영역 영역 영역
        material_ids_for_existing: Dict[str, int] = {
            ic: mat['id'] for ic, mat in existing_materials.items()
        }

        # 기존 BOM 조회 — pair-wise IN tuple
        bom_pairs = []
        for row in bom_rows:
            ic = row['item_code']
            if ic not in material_ids_for_existing:
                continue
            bom_pairs.append((row['product_code'], material_ids_for_existing[ic]))

        existing_boms: Dict[tuple, Dict[str, Any]] = {}
        if bom_pairs:
            conn = get_db_connection()
            try:
                cur = conn.cursor()
                # psycopg2 tuple adapter — pair-wise IN tuple
                # mogrify 영역 영역 영역 영역 안전 영역 IN 영역 생성
                placeholders = ','.join(['(%s,%s)'] * len(bom_pairs))
                flat_params = [v for pair in bom_pairs for v in pair]
                cur.execute(
                    f"""
                    SELECT product_code, material_id, customer, model, quantity
                    FROM checklist.product_bom
                    WHERE (product_code, material_id) IN ({placeholders})
                    """,
                    flat_params,
                )
                for r in cur.fetchall():
                    existing_boms[(r['product_code'], r['material_id'])] = dict(r)
            finally:
                put_conn(conn)

        # BOM diff 분류
        for row in bom_rows:
            ic = row['item_code']
            mat_id = material_ids_for_existing.get(ic)
            if mat_id is None:
                # 신규 material — BOM 도 신규
                bom_mappings_new += 1
                continue

            key = (row['product_code'], mat_id)
            existing_bom = existing_boms.get(key)
            if not existing_bom:
                bom_mappings_new += 1
                continue

            # Q2: quantity OR customer OR model 변경
            qty_new = (row.get('quantity') or '').strip() or None
            qty_existing = existing_bom.get('quantity')
            qty_new_int = int(qty_new) if qty_new and qty_new.lstrip('-').isdigit() else None

            if (qty_new_int != qty_existing
                or _normalize(row.get('customer')) != _normalize(existing_bom.get('customer'))
                or _normalize(row.get('model')) != _normalize(existing_bom.get('model'))):
                bom_mappings_changed += 1

    return {
        'new_materials': new_materials,
        'changed_materials': changed_materials,
        'unchanged_materials': unchanged_materials,
        'bom_mappings_new': bom_mappings_new,
        'bom_mappings_changed': bom_mappings_changed,
        'total_rows': len(parsed_rows),
    }


def commit_upload(
    parsed_rows: List[Dict[str, Any]],
    strategy: str,
    selected_item_codes: Optional[List[str]] = None,
) -> Dict[str, int]:
    """Phase 3 — 단일 트랜잭션 INSERT/UPDATE.

    strategy:
      - 'all'      : 변경 자재 모두 UPDATE + 신규 INSERT
      - 'selected' : selected_item_codes 영역 영역 영역 UPDATE + 신규 모두 INSERT
      - 'skip'     : 기존 자재 UPDATE X, 신규만 INSERT
    """
    if strategy not in ('all', 'selected', 'skip'):
        raise ValueError(f'INVALID_STRATEGY: {strategy}')

    selected_set = set(selected_item_codes or [])
    result = {'inserted': 0, 'updated': 0, 'skipped': 0, 'rejected': 0,
              'bom_inserted': 0, 'bom_updated': 0}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # 1) 기존 material_master 영역 한 번에 조회
        item_codes = list({r['item_code'] for r in parsed_rows if r.get('item_code')})
        existing: Dict[str, Dict[str, Any]] = {}
        if item_codes:
            cur.execute(
                """
                SELECT id, item_code, item_name, category, spec_1, spec_2, unit, description
                FROM checklist.material_master
                WHERE item_code = ANY(%s)
                """,
                (item_codes,),
            )
            for r in cur.fetchall():
                existing[r['item_code']] = dict(r)

        # 2) material_master UPSERT (unique item_code 영역 영역)
        material_id_map: Dict[str, int] = {ic: row['id'] for ic, row in existing.items()}
        seen: set = set()

        for row in parsed_rows:
            ic = row['item_code']
            if ic in seen:
                continue
            seen.add(ic)

            existing_row = existing.get(ic)
            if not existing_row:
                # 신규 INSERT
                cur.execute(
                    """
                    INSERT INTO checklist.material_master
                        (item_code, item_name, category, spec_1, spec_2, unit, description)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (ic, row.get('item_name', ''), row.get('category'),
                     row.get('spec_1') or None, row.get('spec_2') or None,
                     row.get('unit') or None, row.get('description') or None),
                )
                new_id = cur.fetchone()['id']
                material_id_map[ic] = new_id
                result['inserted'] += 1
                continue

            # 기존 row — strategy 분기
            should_update = (
                strategy == 'all'
                or (strategy == 'selected' and ic in selected_set)
            )
            if not should_update:
                result['skipped'] += 1
                continue

            # 변경 영역 영역 검증
            has_change = any(
                _normalize(existing_row.get(f)) != _normalize(row.get(f))
                for f in DIFF_FIELDS
            )
            if not has_change:
                result['skipped'] += 1
                continue

            cur.execute(
                """
                UPDATE checklist.material_master
                SET item_name = %s, category = %s, spec_1 = %s, spec_2 = %s,
                    unit = %s, description = %s, updated_at = CURRENT_TIMESTAMP
                WHERE item_code = %s
                """,
                (row.get('item_name', ''), row.get('category'),
                 row.get('spec_1') or None, row.get('spec_2') or None,
                 row.get('unit') or None, row.get('description') or None, ic),
            )
            result['updated'] += 1

        # 3) product_bom UPSERT (BOM row 영역만 — product_code != '')
        bom_rows = [r for r in parsed_rows if (r.get('product_code') or '').strip()]
        for row in bom_rows:
            ic = row['item_code']
            mat_id = material_id_map.get(ic)
            if mat_id is None:
                # 영역 영역 영역 영역 — silent skip (rejected 영역 영역 영역 X)
                continue

            pc = row['product_code']
            qty_str = (row.get('quantity') or '').strip()
            qty = int(qty_str) if qty_str and qty_str.lstrip('-').isdigit() else None
            customer = row.get('customer') or None
            model = row.get('model') or None

            cur.execute(
                """
                INSERT INTO checklist.product_bom
                    (product_code, customer, model, material_id, quantity)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (product_code, material_id) DO UPDATE
                SET customer = EXCLUDED.customer,
                    model = EXCLUDED.model,
                    quantity = EXCLUDED.quantity,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING (xmax = 0) AS is_inserted
                """,
                (pc, customer, model, mat_id, qty),
            )
            res = cur.fetchone()
            if res and res.get('is_inserted'):
                result['bom_inserted'] += 1
            else:
                result['bom_updated'] += 1

        conn.commit()
        return result

    except Exception as e:
        conn.rollback()
        logger.error(f'commit_upload failed: {e}')
        raise
    finally:
        put_conn(conn)
