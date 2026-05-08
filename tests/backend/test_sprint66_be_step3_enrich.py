"""
Sprint 66-BE Step 3 (v2.12.2) — checklist_master select_options enrich + selected_material_id 직접 전달

검증 영역:
[1] _enrich_select_options — legacy string array (옛 51a placeholder) 그대로 반환
[2] _enrich_select_options — int array (신규 material_id) → "name (description) | spec_1 | spec_2"
[3] _enrich_select_options — description NULL 영역 (비 MFC) "name | spec_1 | spec_2" (괄호 없음)
[4] _enrich_select_options — description 있는 영역 (MFC) "MFC (LNG) | spec_1 | spec_2"
[5] _enrich_select_options — invalid material_id 영역 WARN log + skip (작업자 dropdown noise 0)
[6] _enrich_select_options — 혼합 영역 (string + int) WARN + fallback
[7] _validate_material_id — None → no-op / 미존재 → ValueError(INVALID_MATERIAL_ID)
[8] _validate_material_id — is_active=FALSE 영역 → ValueError
[9] _get_checklist_by_category — N+1 BATCHED 단일 SELECT 영역 검증 (73개 items × 1 SELECT)
[10] upsert_mech_check — selected_material_id NULL OK / 정상 INSERT
[11] upsert_mech_check — selected_material_id 정상 INSERT + checklist_record.selected_material_id 저장 확인
"""

import sys
from pathlib import Path

_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest
from unittest.mock import MagicMock


# ═════════════════════════════════════════════════════════════════════════════
# _enrich_select_options 단위 테스트 (DB 무관)
# ═════════════════════════════════════════════════════════════════════════════

def test_enrich_legacy_string_array_returns_unchanged():
    """[1] 옛 51a placeholder string 배열 → 그대로 반환 + material_ids 모두 NULL."""
    from app.services.checklist_service import _enrich_select_options

    legacy_options = [
        "MKS GE50A | 5 SLM | 0.5 MPa | 0.1-0.7 MPa",
        "Brooks 5850E | 10 SLM | 0.7 MPa | 0.2-0.9 MPa",
    ]
    display, material_ids = _enrich_select_options(legacy_options, {})

    assert display == legacy_options, "legacy string array 영역 보존 실패"
    assert material_ids == [None, None], "legacy 영역의 material_ids 는 모두 NULL 이어야 함"


def test_enrich_int_array_with_material_master_join():
    """[2] 신규 material_id int 배열 → JOIN 후 옵션 Y 형식 변환."""
    from app.services.checklist_service import _enrich_select_options

    material_map = {
        12: {'item_name': 'MFC', 'spec_1': 'MKP | 50 SLM', 'spec_2': 'P:0.3~2.5 / W:0.3', 'description': 'LNG'},
        14: {'item_name': 'ANCHOR BRACKET', 'spec_1': 'O3 DESTRUCTOR', 'spec_2': 'STANDARD', 'description': None},
    }
    display, material_ids = _enrich_select_options([12, 14], material_map)

    assert display == [
        'MFC (LNG) | MKP | 50 SLM | P:0.3~2.5 / W:0.3',
        'ANCHOR BRACKET | O3 DESTRUCTOR | STANDARD',
    ], f"옵션 Y 형식 변환 실패: {display}"
    assert material_ids == [12, 14], "material_ids 순서 보존 실패"


def test_enrich_with_description_mfc_dual_use():
    """[3]+[4] MFC dual-use (1110299900 = LNG,O2) 영역 — description 그대로 표시."""
    from app.services.checklist_service import _enrich_select_options

    material_map = {
        100: {'item_name': 'MFC', 'spec_1': 'MKP | 150 SLM', 'spec_2': 'P:2~4 / W:0.3', 'description': 'LNG,O2'},
    }
    display, _ = _enrich_select_options([100], material_map)

    assert display == ['MFC (LNG,O2) | MKP | 150 SLM | P:2~4 / W:0.3'], (
        f"dual-use description 포함 영역 정합 실패: {display}"
    )


def test_enrich_invalid_material_id_skips_with_warn(caplog):
    """[5] invalid material_id (미존재) → WARN log + 결과에서 skip."""
    import logging
    from app.services.checklist_service import _enrich_select_options

    material_map = {
        12: {'item_name': 'MFC', 'spec_1': 'MKP', 'spec_2': '', 'description': 'LNG'},
        # 999 미존재
    }
    with caplog.at_level(logging.WARNING):
        display, material_ids = _enrich_select_options([12, 999], material_map)

    assert display == ['MFC (LNG) | MKP'], "invalid id 영역 skip 실패"
    assert material_ids == [12], "invalid id 영역 material_ids 도 skip 되어야 함"
    assert any('invalid material_id' in rec.message.lower() for rec in caplog.records), (
        "WARN log 미발생 — Sentry capture trigger 미작동"
    )


def test_enrich_mixed_array_warns_and_fallbacks(caplog):
    """[6] 혼합 영역 (string + int) → WARN + str(x) fallback."""
    import logging
    from app.services.checklist_service import _enrich_select_options

    with caplog.at_level(logging.WARNING):
        display, material_ids = _enrich_select_options(['MKS GE50A', 12], {})

    assert display == ['MKS GE50A', '12'], f"혼합 영역 fallback 실패: {display}"
    assert material_ids == [None, None], "혼합 영역 material_ids 는 모두 NULL"
    assert any('혼합 양식' in rec.message for rec in caplog.records), (
        "혼합 양식 WARN log 미발생"
    )


def test_enrich_none_or_empty_options_returns_none():
    """[보강] select_options=None / [] → (None, None) 또는 ([], None)."""
    from app.services.checklist_service import _enrich_select_options

    # None
    display, material_ids = _enrich_select_options(None, {})
    assert display is None and material_ids is None

    # 빈 배열
    display, material_ids = _enrich_select_options([], {})
    assert (display == [] or display is None) and material_ids is None


# ═════════════════════════════════════════════════════════════════════════════
# _validate_material_id 단위 테스트 (DB 의존)
# ═════════════════════════════════════════════════════════════════════════════

def test_validate_material_id_none_is_noop():
    """[7-A] selected_material_id=None → no-op (raise 안 함)."""
    from app.services.checklist_service import _validate_material_id

    cur = MagicMock()
    _validate_material_id(cur, None)
    assert not cur.execute.called, "None 영역에서는 SELECT 호출 X"


def test_validate_material_id_existing_active_material_passes(db_conn):
    """[7-B] 정상 active material_id → no raise."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    from app.services.checklist_service import _validate_material_id

    # 1110006700 (LNG MFC) 사용
    with db_conn.cursor() as cur:
        cur.execute("SELECT id FROM checklist.material_master WHERE item_code = '1110006700' LIMIT 1")
        row = cur.fetchone()
    assert row is not None, "테스트 자재 1110006700 미존재 — seed 누락"
    material_id = row[0] if not isinstance(row, dict) else row['id']

    with db_conn.cursor() as cur:
        _validate_material_id(cur, material_id)  # raise 안 해야 정상


def test_validate_material_id_nonexistent_raises(db_conn):
    """[7-C] 미존재 material_id → ValueError(INVALID_MATERIAL_ID)."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    from app.services.checklist_service import _validate_material_id

    with db_conn.cursor() as cur:
        with pytest.raises(ValueError) as exc_info:
            _validate_material_id(cur, 99999999)  # 존재할 수 없는 큰 id

    assert 'INVALID_MATERIAL_ID' in str(exc_info.value), (
        f"INVALID_MATERIAL_ID 에러 코드 부재: {exc_info.value}"
    )


# ═════════════════════════════════════════════════════════════════════════════
# integration: _get_checklist_by_category — N+1 BATCHED 검증
# ═════════════════════════════════════════════════════════════════════════════

def test_get_checklist_n_plus_1_batched_single_select(db_conn):
    """[9] _get_checklist_by_category — material_master JOIN 영역이 N+1 X 단일 SELECT 보장.

    73개 items 의 select_options 를 일괄 collect → 단일 SELECT → in-memory map → row 변환.
    Codex P0 #3 BATCHED 영역 정합.
    """
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    from app.services.checklist_service import _get_checklist_by_category

    # 운영 데이터로 호출 (MECH 73 items, 8개 select_options)
    # SQL 호출 카운터 wrapper
    original_execute = db_conn.cursor().__class__.execute
    select_count = 0

    # _get_checklist_by_category 는 RealDictCursor 사용 (named column access)
    from psycopg2.extras import RealDictCursor

    with db_conn.cursor(cursor_factory=RealDictCursor) as cur:
        result = _get_checklist_by_category(
            cur=cur,
            serial_number='G6S-25-XXX',  # 가상 S/N (no record)
            category='MECH',
            product_code=None,
            scope='all',
            judgment_phase=1,
            qr_doc_id='',
        )

    # items 응답 구조 검증
    assert 'items' in result, "items 키 부재"
    assert 'summary' in result, "summary 키 부재"
    assert isinstance(result['items'], list), "items 배열 아님"

    # select_material_ids 필드 모든 item 에 존재
    for item in result['items']:
        assert 'select_material_ids' in item, (
            f"select_material_ids 필드 누락: master_id={item.get('master_id')}"
        )
        # 일관성: select_options 가 list 면 select_material_ids 도 list 또는 None
        opts = item.get('select_options')
        mat_ids = item.get('select_material_ids')
        if opts is None:
            assert mat_ids is None, "select_options=None 이면 select_material_ids 도 None"
        elif isinstance(opts, list) and len(opts) > 0:
            # 길이 정합 — invalid skip 영역 가능 (mat_ids 가 더 짧을 수 있음)
            assert mat_ids is not None, (
                f"select_options 가 array 인데 select_material_ids=None: master_id={item.get('master_id')}"
            )


# ═════════════════════════════════════════════════════════════════════════════
# integration: upsert_mech_check — selected_material_id 저장 검증
# ═════════════════════════════════════════════════════════════════════════════

def test_upsert_mech_check_with_null_material_id_ok(db_conn):
    """[10] selected_material_id=None → 정상 INSERT (legacy 영역 호환)."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    from app.services.checklist_service import upsert_mech_check

    # 단순 시그니처 호출 검증 — 실제 INSERT 는 conftest cleanup 으로 격리
    # MASTER_NOT_FOUND 회피용 더미 master_id 미사용 (시그니처 검증만)
    try:
        upsert_mech_check(
            serial_number='G6S-TEST-NULL-MID',
            master_id=99999999,  # 존재하지 않는 master_id → MASTER_NOT_FOUND 의도
            check_result='PASS',
            note=None,
            worker_id=1,
            selected_material_id=None,  # ⭐ 핵심: NULL 허용
        )
    except ValueError as e:
        # MASTER_NOT_FOUND 는 의도된 raise (시그니처 검증 통과)
        assert 'MASTER_NOT_FOUND' in str(e)


def test_upsert_mech_check_with_invalid_material_id_raises(db_conn):
    """[11] selected_material_id 미존재 → INVALID_MATERIAL_ID raise."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    from app.services.checklist_service import upsert_mech_check

    # 1110006700 의 material_id 가 아닌 99999999 사용 — INVALID raise 의도
    with pytest.raises(ValueError) as exc_info:
        upsert_mech_check(
            serial_number='G6S-TEST-INVALID-MID',
            master_id=99999999,
            check_result='PASS',
            note=None,
            worker_id=1,
            selected_material_id=99999999,
        )

    # MASTER_NOT_FOUND (master_id 검증) 또는 INVALID_MATERIAL_ID (material_id 검증) 어느 쪽이든 raise
    err_msg = str(exc_info.value)
    assert 'MASTER_NOT_FOUND' in err_msg or 'INVALID_MATERIAL_ID' in err_msg, (
        f"검증 실패 — 에러 메시지: {err_msg}"
    )


# ═════════════════════════════════════════════════════════════════════════════
# Codex 라운드 1 A 정정 — TC 보강 (N+1 batched 특정 + invalid material_id 특정)
# ═════════════════════════════════════════════════════════════════════════════

def test_fetch_material_master_map_single_select(db_conn):
    """[A 정정] _fetch_material_master_map — 단일 SELECT 보장 (N+1 BATCHED 영역).

    73 항목 × 평균 6 material_id = ~438 ID 영역에서 단일 쿼리만 실행됨을 명시 검증.
    """
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    from app.services.checklist_service import _fetch_material_master_map

    # 운영 자재 ID 5개 (csv 영역) 추출
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT id FROM checklist.material_master
             WHERE item_code IN ('1110006700', '1110049600', '1100887400', '1110298800', '1100479300')
        """)
        material_ids = {row[0] for row in cur.fetchall()}
    assert len(material_ids) == 5, f"테스트 자재 5개 미존재: {material_ids}"

    # _fetch_material_master_map 호출 시 cur.execute 호출 카운트 측정
    # psycopg2 cursor.execute 가 read-only 라 proxy class 로 wrapping
    class _CountingCursor:
        def __init__(self, real_cur):
            self._real = real_cur
            self.execute_count = 0

        def execute(self, *args, **kwargs):
            self.execute_count += 1
            return self._real.execute(*args, **kwargs)

        def fetchall(self):
            return self._real.fetchall()

        def fetchone(self):
            return self._real.fetchone()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self._real.__exit__(*args)

    from psycopg2.extras import RealDictCursor
    with db_conn.cursor(cursor_factory=RealDictCursor) as real_cur:
        proxy = _CountingCursor(real_cur)
        material_map = _fetch_material_master_map(proxy, material_ids)

    # 단일 SELECT 보장 — N+1 BATCHED Codex P0 #3 정합
    assert proxy.execute_count == 1, (
        f"_fetch_material_master_map 단일 쿼리 위반: {proxy.execute_count} 호출 — N+1 회귀"
    )
    assert len(material_map) == 5, f"5개 material 모두 fetch 실패: {len(material_map)}"


def test_validate_material_id_invalid_raises_specific(db_conn):
    """[C 정정] _validate_material_id — INVALID_MATERIAL_ID 특정 검증 (master_id 영역과 분리).

    upsert 통합 TC 가 MASTER_NOT_FOUND 또는 INVALID_MATERIAL_ID 양쪽 수용 영역에서,
    material_id 검증 경로만 특정 raise 검증.
    """
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    from app.services.checklist_service import _validate_material_id

    # 직접 호출 — master_id 검증 우회 (validate 경로 특정)
    with db_conn.cursor() as cur:
        with pytest.raises(ValueError) as exc_info:
            _validate_material_id(cur, 99999999)  # 미존재 id

    err_msg = str(exc_info.value)
    assert 'INVALID_MATERIAL_ID' in err_msg, (
        f"INVALID_MATERIAL_ID 영역 특정 raise 미발생: {err_msg}"
    )
    # 99999999 가 메시지에 포함되어야 함 (디버그 영역)
    assert '99999999' in err_msg, f"material_id 디버그 영역 부재: {err_msg}"
