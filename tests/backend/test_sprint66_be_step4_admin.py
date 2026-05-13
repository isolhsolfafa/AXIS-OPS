"""
Sprint 66-BE Step 4 (v2.12.3) — admin/materials + admin/checklists CRUD endpoint pytest

검증 영역:
[1] GET /api/admin/materials — 검색 + 페이지네이션 + ILIKE filter
[2] POST /api/admin/materials — 신규 자재 INSERT (ON CONFLICT DO UPDATE idempotent)
[3] PATCH /api/admin/materials/<id> — 자재 spec 수정 + 갱신 가능 필드 화이트리스트
[4] PATCH /api/admin/materials/<id>/deactivate + reactivate — soft delete + 복구
[5] GET /api/admin/checklists/master/<id>/options — 매핑 조회 + dual-format 분기
[6] PATCH /api/admin/checklists/master/<id>/options — material_id 배열 매핑 + 검증
[7] 권한: @gst_or_admin_required — admin OR GST 만 접근

ADR-023 cross-check 사례 #6: 새 데코레이터 작성 X — 기존 표준 (jwt_auth.py L263) 활용.
"""
import sys
from pathlib import Path

_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest
import json


# ═════════════════════════════════════════════════════════════════════════════
# Fixture helpers — admin/GST/partner 헤더 생성
# ═════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def admin_headers(create_test_admin, get_admin_auth_token):
    """admin (is_admin=TRUE) JWT 헤더."""
    admin = create_test_admin
    token = get_admin_auth_token(
        worker_id=admin['id'],
        email=admin['email'],
        role=admin['role'],
        is_admin=True,
    )
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def gst_worker_headers(create_test_worker, get_auth_token):
    """GST 회사 직원 (non-admin) JWT 헤더 — gst_or_admin_required 의 GST 분기 검증용."""
    worker_id = create_test_worker(
        email='gst_step4@test.axisos.com',
        password='GstPass123!',
        name='GST Step4 Worker',
        role='QI',
        company='GST',
        is_admin=False,
    )
    token = get_auth_token(worker_id, role='QI')
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def partner_worker_headers(create_test_worker, get_auth_token):
    """협력사 직원 (non-admin, non-GST) JWT 헤더 — 권한 차단 검증용."""
    worker_id = create_test_worker(
        email='partner_step4@test.axisos.com',
        password='PartnerPass123!',
        name='Partner Step4 Worker',
        role='MECH',
        company='FNI',
        is_admin=False,
    )
    token = get_auth_token(worker_id, role='MECH')
    return {'Authorization': f'Bearer {token}'}


# ═════════════════════════════════════════════════════════════════════════════
# /api/admin/materials — CRUD pytest
# ═════════════════════════════════════════════════════════════════════════════

def test_list_materials_default(client, admin_headers, db_conn):
    """[1] GET /api/admin/materials — 기본 목록 + 페이지네이션 + is_active=TRUE 필터."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    response = client.get('/api/admin/materials', headers=admin_headers)
    assert response.status_code == 200, f"응답 코드 정합 실패: {response.status_code} - {response.data}"

    data = response.get_json()
    assert 'items' in data
    assert 'total' in data
    assert data['total'] >= 13, f"운영 자재 수 정합 실패: {data['total']}"

    if data['items']:
        first = data['items'][0]
        for k in ('id', 'item_code', 'item_name', 'description', 'is_active'):
            assert k in first, f"item dict 누락 필드: {k}"


def test_list_materials_filter_by_description(client, admin_headers, db_conn):
    """[1-A] description ILIKE 검색 — LNG 6 hits 정합."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    response = client.get('/api/admin/materials?description=LNG', headers=admin_headers)
    assert response.status_code == 200

    data = response.get_json()
    assert data['total'] >= 5, f"LNG ILIKE 결과 정합 실패: {data['total']}"

    for item in data['items']:
        desc = item.get('description') or ''
        assert 'LNG' in desc.upper(), f"LNG ILIKE 결과 오염: description={desc}"


def test_list_materials_filter_by_category(client, admin_headers, db_conn):
    """[1-B] category 정확 일치 — MFC 13 자재 정합 (ILIKE 부분 매칭 후에도 유지)."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    response = client.get('/api/admin/materials?category=MFC', headers=admin_headers)
    assert response.status_code == 200

    data = response.get_json()
    assert data['total'] == 13, f"MFC 자재 수 정합 실패: {data['total']}"

    for item in data['items']:
        assert item['category'] == 'MFC'


def test_list_materials_filter_by_category_case_insensitive(client, admin_headers, db_conn):
    """[1-B-CI] HOTFIX-MATERIALS-CATEGORY-ILIKE-20260513 — 소문자 'mfc' → ILIKE 매칭."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    response = client.get('/api/admin/materials?category=mfc', headers=admin_headers)
    assert response.status_code == 200

    data = response.get_json()
    assert data['total'] == 13, f"case-insensitive 매칭 실패: {data['total']}"

    for item in data['items']:
        assert item['category'] == 'MFC'


def test_list_materials_filter_by_category_partial_match(client, admin_headers, db_conn):
    """[1-B-PM] HOTFIX-MATERIALS-CATEGORY-ILIKE-20260513 — 'm' 한 글자 → ILIKE 부분 매칭 (MFC 13건 포함)."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    response = client.get('/api/admin/materials?category=m', headers=admin_headers)
    assert response.status_code == 200

    data = response.get_json()
    assert data['total'] >= 13, f"부분 매칭 실패: {data['total']} (MFC 13건 이상이어야 함)"

    categories = {item['category'] for item in data['items']}
    assert any('m' in cat.lower() for cat in categories), f"매칭된 카테고리에 'm' 미포함: {categories}"


def test_create_material_idempotent(client, admin_headers, db_conn):
    """[2] POST — ON CONFLICT DO UPDATE idempotent."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    payload = {
        'item_code': 'TEST-S66S4-CRT-001',
        'item_name': 'Test Material',
        'category': 'TEST',
        'spec_1': 'spec1-test',
        'spec_2': 'spec2-test',
        'unit': 'EA',
        'description': 'pytest test',
    }

    try:
        # 1차 INSERT
        r1 = client.post('/api/admin/materials', headers=admin_headers, json=payload)
        assert r1.status_code == 201, f"1차 INSERT 실패: {r1.data}"
        d1 = r1.get_json()
        assert d1['created'] is True
        new_id = d1['id']

        # 2차 INSERT (idempotent — UPDATE)
        r2 = client.post('/api/admin/materials', headers=admin_headers, json=payload)
        assert r2.status_code == 201
        d2 = r2.get_json()
        assert d2['id'] == new_id, "ON CONFLICT 동일 id"
        assert d2['created'] is False
    finally:
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM checklist.material_master WHERE item_code = %s", ('TEST-S66S4-CRT-001',))
            db_conn.commit()


def test_create_material_validation(client, admin_headers, db_conn):
    """[2-A] item_code 또는 item_name 누락 시 400."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    r1 = client.post('/api/admin/materials', headers=admin_headers, json={'item_name': 'X'})
    assert r1.status_code == 400

    r2 = client.post('/api/admin/materials', headers=admin_headers, json={'item_code': 'X'})
    assert r2.status_code == 400


def test_update_material_whitelist(client, admin_headers, db_conn):
    """[3] PATCH 화이트리스트 — item_code 변경 차단 + 정상 갱신."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    create = client.post(
        '/api/admin/materials',
        headers=admin_headers,
        json={
            'item_code': 'TEST-S66S4-UPD-001',
            'item_name': 'Original',
            'category': 'TEST',
            'description': 'orig',
        },
    )
    new_id = create.get_json()['id']

    try:
        # 화이트리스트 외 (item_code) 무시 + name + description 갱신
        r = client.patch(
            f'/api/admin/materials/{new_id}',
            headers=admin_headers,
            json={
                'item_name': 'Updated',
                'description': 'new',
                'item_code': 'IGNORED',
            },
        )
        assert r.status_code == 200

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT item_code, item_name, description FROM checklist.material_master WHERE id = %s",
                (new_id,),
            )
            row = cur.fetchone()
        assert row[0] == 'TEST-S66S4-UPD-001', "item_code 화이트리스트 외 변경됨"
        assert row[1] == 'Updated'
        assert row[2] == 'new'

        # 빈 body
        r_empty = client.patch(f'/api/admin/materials/{new_id}', headers=admin_headers, json={})
        assert r_empty.status_code == 400

        # 미존재 id
        r_404 = client.patch('/api/admin/materials/99999999', headers=admin_headers, json={'item_name': 'X'})
        assert r_404.status_code == 404
    finally:
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM checklist.material_master WHERE id = %s", (new_id,))
            db_conn.commit()


def test_deactivate_reactivate_material(client, admin_headers, db_conn):
    """[4] deactivate + reactivate — soft delete + 복구 + default 검색 분기."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    create = client.post(
        '/api/admin/materials',
        headers=admin_headers,
        json={'item_code': 'TEST-S66S4-DCT-001', 'item_name': 'Deact Test'},
    )
    new_id = create.get_json()['id']

    try:
        # deactivate
        r = client.patch(f'/api/admin/materials/{new_id}/deactivate', headers=admin_headers)
        assert r.status_code == 200
        assert r.get_json()['deactivated'] is True

        with db_conn.cursor() as cur:
            cur.execute("SELECT is_active FROM checklist.material_master WHERE id = %s", (new_id,))
            assert cur.fetchone()[0] is False

        # default 검색 (is_active=true) 에서 제외
        list1 = client.get('/api/admin/materials?keyword=TEST-S66S4-DCT-001', headers=admin_headers)
        ids = {item['id'] for item in list1.get_json()['items']}
        assert new_id not in ids, "비활성 자재가 default 목록 포함"

        # is_active=all 에서 노출
        list2 = client.get('/api/admin/materials?keyword=TEST-S66S4-DCT-001&is_active=all', headers=admin_headers)
        all_ids = {item['id'] for item in list2.get_json()['items']}
        assert new_id in all_ids, "is_active=all 영역 미노출"

        # reactivate
        r2 = client.patch(f'/api/admin/materials/{new_id}/reactivate', headers=admin_headers)
        assert r2.status_code == 200
        with db_conn.cursor() as cur:
            cur.execute("SELECT is_active FROM checklist.material_master WHERE id = %s", (new_id,))
            assert cur.fetchone()[0] is True
    finally:
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM checklist.material_master WHERE id = %s", (new_id,))
            db_conn.commit()


# ═════════════════════════════════════════════════════════════════════════════
# /api/admin/checklists/master/<id>/options — 매핑 pytest
# ═════════════════════════════════════════════════════════════════════════════

def test_get_select_options_legacy_string_array(client, admin_headers, db_conn):
    """[5] GET dual-format — legacy string array 영역 legacy_string flag."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, select_options FROM checklist.checklist_master
             WHERE category = 'MECH' AND item_type = 'SELECT'
               AND select_options IS NOT NULL
             LIMIT 1
            """
        )
        row = cur.fetchone()
    if not row:
        pytest.skip("MECH SELECT master 미존재")
    master_id, raw = row[0], row[1]

    response = client.get(f'/api/admin/checklists/master/{master_id}/options', headers=admin_headers)
    assert response.status_code == 200

    data = response.get_json()
    assert data['master_id'] == master_id
    assert data['item_type'] == 'SELECT'
    assert 'select_options_raw' in data
    assert 'materials' in data

    if raw and all(isinstance(x, str) for x in raw):
        assert all('legacy_string' in m for m in data['materials']), (
            "legacy string 영역에서 legacy_string flag 부재"
        )


def test_update_select_options_validation(client, admin_headers, db_conn):
    """[6-A] PATCH 검증 — list/int/중복/미존재."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM checklist.checklist_master WHERE category='MECH' AND item_type='SELECT' LIMIT 1"
        )
        row = cur.fetchone()
    if not row:
        pytest.skip("MECH SELECT master 미존재")
    master_id = row[0]

    # 1. list 아님
    r1 = client.patch(
        f'/api/admin/checklists/master/{master_id}/options',
        headers=admin_headers,
        json={'material_ids': 'not_a_list'},
    )
    assert r1.status_code == 400

    # 2. int 아님
    r2 = client.patch(
        f'/api/admin/checklists/master/{master_id}/options',
        headers=admin_headers,
        json={'material_ids': [1, 'two', 3]},
    )
    assert r2.status_code == 400

    # 3. 중복
    r3 = client.patch(
        f'/api/admin/checklists/master/{master_id}/options',
        headers=admin_headers,
        json={'material_ids': [1, 2, 1]},
    )
    assert r3.status_code == 400

    # 4. 미존재 material_id
    r4 = client.patch(
        f'/api/admin/checklists/master/{master_id}/options',
        headers=admin_headers,
        json={'material_ids': [99999999]},
    )
    assert r4.status_code == 400
    assert 'INVALID_MATERIAL_IDS' in r4.get_json().get('error', '')


def test_update_select_options_roundtrip(client, admin_headers, db_conn):
    """[6] PATCH → GET roundtrip — int array 양식 + array_position 순서 보존."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, select_options FROM checklist.checklist_master
             WHERE category='MECH' AND item_type='SELECT' LIMIT 1
            """
        )
        row = cur.fetchone()
    if not row:
        pytest.skip("MECH SELECT master 미존재")
    master_id = row[0]
    original = row[1]

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM checklist.material_master WHERE category='MFC' AND is_active=TRUE ORDER BY id LIMIT 5"
        )
        mat_ids = [r[0] for r in cur.fetchall()]
    if len(mat_ids) < 5:
        pytest.skip("MFC 자재 5개 미존재")

    try:
        # PATCH
        r = client.patch(
            f'/api/admin/checklists/master/{master_id}/options',
            headers=admin_headers,
            json={'material_ids': mat_ids},
        )
        assert r.status_code == 200, f"PATCH 실패: {r.data}"
        d = r.get_json()
        assert d['updated'] is True
        assert d['material_ids'] == mat_ids

        # GET roundtrip
        get_r = client.get(f'/api/admin/checklists/master/{master_id}/options', headers=admin_headers)
        assert get_r.status_code == 200
        gd = get_r.get_json()
        assert gd['select_options_raw'] == mat_ids, "raw roundtrip 불일치"
        assert len(gd['materials']) == 5, "materials 5개 정합 실패"

        # array_position 순서 보존
        returned_ids = [m['id'] for m in gd['materials']]
        assert returned_ids == mat_ids, f"순서 보존 실패: {returned_ids} vs {mat_ids}"

        # 신규 양식 — legacy_string flag 부재
        for m in gd['materials']:
            assert 'legacy_string' not in m
            assert 'description' in m
    finally:
        # 원복
        with db_conn.cursor() as cur:
            cur.execute(
                "UPDATE checklist.checklist_master SET select_options = %s::jsonb WHERE id = %s",
                (json.dumps(original) if original else None, master_id),
            )
            db_conn.commit()


# ═════════════════════════════════════════════════════════════════════════════
# 권한 검증 — @gst_or_admin_required (admin / GST OK, partner 차단)
# ═════════════════════════════════════════════════════════════════════════════

def test_admin_materials_require_jwt(client):
    """[7] JWT 부재 시 401."""
    response = client.get('/api/admin/materials')
    assert response.status_code == 401


def test_admin_materials_partner_forbidden(client, partner_worker_headers, db_conn):
    """[7-A] 협력사 (non-admin, non-GST) → 403."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    response = client.get('/api/admin/materials', headers=partner_worker_headers)
    assert response.status_code == 403


def test_admin_materials_gst_allowed(client, gst_worker_headers, db_conn):
    """[7-B] GST 직원 (non-admin, GST) → 200 (gst_or_admin_required 통과)."""
    if db_conn is None:
        pytest.skip("DB 연결 없음")

    response = client.get('/api/admin/materials', headers=gst_worker_headers)
    assert response.status_code == 200, (
        f"GST 직원 영역 접근 차단됨: {response.status_code} - {response.data}"
    )
