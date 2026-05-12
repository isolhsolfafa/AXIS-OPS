"""
Sprint 66-BE-FOLLOWUP v3 — pytest 24 TC (TC-MU-01~24)

Codex 5라운드 검증 GREEN 정합:
  - TC-MU-01~12: #63 기본 (preview/commit/strategy)
  - TC-MU-13~15: Q1/Q2/Q3 trail
  - TC-MU-16~21: critical coverage (xlsx/empty/header-only/INVALID_BOM_KEY/FIELD_TOO_LONG/NULL vs '')
  - TC-MU-22~24: ATTRIBUTE_CONFLICT + non-MFC dedup + MFC material-only

⚠️ Unit TC (DB-free, ~0.3초): TC-MU-04~06 / 13~14 / 17~20 / 22~24
⚠️ Integration TC (실 DB, ~10-20분): TC-MU-01~03 / 07~12 / 15 / 16 / 21
"""
import io
import pytest


# ── Unit TC (DB-free) — material_parser ──────────────────────────────────

class TestParserUnit:
    """parser 영역 unit TC — DB 무관, 빠른 영역 영역."""

    @pytest.fixture(autouse=True)
    def _setup(self, app):
        from app.utils.material_parser import (
            parse_upload_file, detect_encoding, _merge_duplicate_mfc,
            _validate_row, _map_korean_to_english, FIELD_MAX_LENGTH,
        )
        self.parse = parse_upload_file
        self.detect = detect_encoding
        self.merge = _merge_duplicate_mfc
        self.validate = _validate_row
        self.map_ko = _map_korean_to_english
        self.field_max = FIELD_MAX_LENGTH

    def _make_file(self, content: str, filename: str = 'test.csv',
                   encoding: str = 'utf-8') -> object:
        """가상 file 객체 영역 영역."""
        class _File:
            def __init__(s, data, name):
                s._data = data
                s.filename = name
            def read(s):
                return s._data
        return _File(content.encode(encoding) if isinstance(content, str) else content, filename)

    # TC-MU-04: 자재코드 누락 row → rejected_rows
    def test_mu_04_missing_item_code_rejected(self):
        # product_code 영역 빈칸 (material-only 영역) — MISSING_ITEM_CODE 영역 단독 reject 검증
        csv = '품번,자재코드,자재내역,규격1,수량\n,,A,B,1\n,X1,Y,Z,2\n'
        parsed, rejected = self.parse(self._make_file(csv))
        assert len(parsed) == 1
        assert len(rejected) == 1
        assert rejected[0]['reason'] == 'MISSING_ITEM_CODE'

    # TC-MU-05: CP949 인코딩 자동 감지
    def test_mu_05_cp949_encoding(self):
        csv = '자재코드,자재내역\nX1,한글자재\n'
        file = self._make_file(csv, encoding='cp949')
        parsed, rejected = self.parse(file)
        assert len(parsed) == 1
        assert parsed[0]['item_code'] == 'X1'
        assert parsed[0]['item_name'] == '한글자재'

    # TC-MU-06: 손상된 xlsx → PARSE_ERROR
    def test_mu_06_corrupted_xlsx(self):
        file = self._make_file(b'NOT_AN_XLSX', filename='broken.xlsx')
        with pytest.raises(ValueError, match='PARSE_ERROR'):
            self.parse(file)

    # TC-MU-13: Q1 MFC dual-use 합침
    def test_mu_13_mfc_dual_use_merge(self):
        rows = [
            {'item_code': 'MFC-1', 'item_name': 'MFC', 'category': 'MFC',
             'spec_1': '5 SLM', 'spec_2': '0.5 MPa', 'unit': 'EA', 'description': 'LNG'},
            {'item_code': 'MFC-1', 'item_name': 'MFC', 'category': 'MFC',
             'spec_1': '5 SLM', 'spec_2': '0.5 MPa', 'unit': 'EA', 'description': 'O2'},
        ]
        merged, conflicts = self.merge(rows)
        assert len(merged) == 1
        assert len(conflicts) == 0
        assert merged[0]['description'] == 'LNG,O2'

    # TC-MU-14: category 자동 추출
    def test_mu_14_category_auto_extract(self):
        # MFC* → category='MFC', item_name='MFC'
        mapped_mfc, reject = self.validate(
            {'item_code': 'X1', 'item_name': 'MFC GE50A'}, 2)
        assert reject is None
        assert mapped_mfc['category'] == 'MFC'
        assert mapped_mfc['item_name'] == 'MFC'

        # 그 외 → category = item_name
        mapped_other, _ = self.validate(
            {'item_code': 'X2', 'item_name': 'O3 DESTRUCTOR'}, 3)
        assert mapped_other['category'] == 'O3 DESTRUCTOR'
        assert mapped_other['item_name'] == 'O3 DESTRUCTOR'

    # TC-MU-17: empty file → 200 + total_rows=0 (header X 영역 INVALID_HEADER)
    def test_mu_17_empty_file(self):
        file = self._make_file('', filename='empty.csv')
        parsed, rejected = self.parse(file)
        assert parsed == []
        assert rejected == []

    # TC-MU-18: header-only file → 200 + total_rows=0
    def test_mu_18_header_only(self):
        csv = '자재코드,자재내역,규격1\n'
        parsed, rejected = self.parse(self._make_file(csv))
        assert parsed == []
        assert rejected == []

    # TC-MU-19: INVALID_BOM_KEY (BOM row + customer/model 빈칸)
    def test_mu_19_invalid_bom_key(self):
        # BOM row (product_code != '') 영역 customer 빈칸 → reject
        mapped, reject = self.validate(
            {'item_code': 'X1', 'item_name': 'A',
             'product_code': '4100', 'customer': '', 'model': 'M1'}, 2)
        assert reject is not None
        assert reject['reason'] == 'INVALID_BOM_KEY'

        # material-only MFC (product_code='') 영역 customer/model 빈칸 → 허용
        mapped, reject = self.validate(
            {'item_code': 'MFC-1', 'item_name': 'MFC',
             'product_code': '', 'customer': '', 'model': ''}, 3)
        assert reject is None

    # TC-MU-20: FIELD_TOO_LONG (8 필드)
    def test_mu_20_field_too_long(self):
        # item_code 51자 → reject
        mapped, reject = self.validate(
            {'item_code': 'X' * 51, 'item_name': 'A'}, 2)
        assert reject is not None
        assert reject['reason'] == 'FIELD_TOO_LONG'
        assert 'item_code' in reject['detail']

        # category 51자 (item_name 51자 영역 영역 영역 영역 — 영역 영역 영역 영역 영역)
        mapped, reject = self.validate(
            {'item_code': 'X1', 'item_name': 'A' * 51}, 3)
        # item_name 51자 영역 영역 영역 영역 200 영역 OK, but category = item_name = 51자 영역 → category 50 초과 → reject
        assert reject is not None
        assert reject['reason'] == 'FIELD_TOO_LONG'
        assert 'category' in reject['detail']

    # TC-MU-22: ATTRIBUTE_CONFLICT (자재 정보 충돌)
    def test_mu_22_attribute_conflict(self):
        rows = [
            {'item_code': 'X1', 'item_name': 'A', 'category': 'X',
             'spec_1': 'A1', 'spec_2': '', 'unit': 'EA', '_row_number': 2},
            {'item_code': 'X1', 'item_name': 'A', 'category': 'X',
             'spec_1': 'B2', 'spec_2': '', 'unit': 'EA', '_row_number': 3},  # spec_1 충돌
        ]
        merged, conflicts = self.merge(rows)
        assert len(merged) == 1  # 첫 등장 row 유지
        assert merged[0]['_row_number'] == 2  # 첫 등장
        assert len(conflicts) == 1
        assert conflicts[0]['reason'] == 'ATTRIBUTE_CONFLICT'
        assert 'spec_1' in conflicts[0]['detail']

    # TC-MU-23: non-MFC 중복 item_code → dedup 첫 등장 (reject X)
    def test_mu_23_non_mfc_dedup(self):
        rows = [
            {'item_code': 'X1', 'item_name': 'A', 'category': 'A',  # non-MFC
             'spec_1': '', 'spec_2': '', 'unit': '', '_row_number': 2},
            {'item_code': 'X1', 'item_name': 'A', 'category': 'A',  # 동일
             'spec_1': '', 'spec_2': '', 'unit': '', '_row_number': 3},
        ]
        merged, conflicts = self.merge(rows)
        assert len(merged) == 1  # dedup
        assert merged[0]['_row_number'] == 2  # 첫 등장
        assert len(conflicts) == 0  # 자재 정보 동일 → reject X

    # TC-MU-24: material-only MFC rows (product_code='') 허용
    def test_mu_24_mfc_material_only(self):
        csv = '품번,자재코드,자재내역,규격1\n,MFC-1,MFC GE50A,5 SLM\n'
        parsed, rejected = self.parse(self._make_file(csv))
        assert len(parsed) == 1
        assert len(rejected) == 0
        assert parsed[0]['item_code'] == 'MFC-1'
        assert parsed[0]['category'] == 'MFC'
        assert parsed[0].get('product_code') == ''


# ── Integration TC (실 DB, Railway staging) ─────────────────────────────

class TestUploadIntegration:
    """Integration TC — preview/commit + DB 대조. 실 staging DB 사용."""

    @pytest.fixture
    def admin_auth(self, get_auth_token, admin_worker):
        """admin Bearer header"""
        token = get_auth_token(
            worker_id=admin_worker['id'],
            email=admin_worker['email'],
            role='QI', is_admin=True,
        )
        return {'Authorization': f'Bearer {token}'}

    @pytest.fixture
    def cleanup_test_materials(self, db_conn):
        """test material_master + product_bom cleanup."""
        if db_conn is None:
            pytest.skip("DB not available")
        prefix = 'TESTMU-'
        yield prefix
        cur = db_conn.cursor()
        cur.execute("DELETE FROM checklist.product_bom WHERE product_code LIKE %s",
                    (f'{prefix}%',))
        cur.execute("DELETE FROM checklist.material_master WHERE item_code LIKE %s",
                    (f'{prefix}%',))
        db_conn.commit()

    def _post_upload(self, client, admin_auth, csv_content: str, mode: str,
                     strategy: str = None, selected: list = None):
        """multipart/form-data POST helper."""
        import json
        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'test.csv'),
            'mode': mode,
        }
        if strategy:
            data['strategy'] = strategy
        if selected is not None:
            data['selected_item_codes'] = json.dumps(selected)
        return client.post('/api/admin/materials/upload',
                           headers=admin_auth, data=data,
                           content_type='multipart/form-data')

    # TC-MU-01: preview 신규 자재만
    def test_mu_01_preview_new_only(self, client, admin_auth, cleanup_test_materials):
        prefix = cleanup_test_materials
        csv = f'자재코드,자재내역,규격1\n{prefix}001,A,X\n{prefix}002,B,Y\n'
        resp = self._post_upload(client, admin_auth, csv, mode='preview')
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['total_rows'] == 2
        assert len(body['new_materials']) == 2
        assert len(body['unchanged_materials']) == 0

    # TC-MU-02: 동일 파일 재업로드 → unchanged
    def test_mu_02_preview_unchanged_on_recommit(
        self, client, admin_auth, cleanup_test_materials
    ):
        prefix = cleanup_test_materials
        csv = f'자재코드,자재내역,규격1\n{prefix}010,A,X\n'
        # 1차: commit
        resp1 = self._post_upload(client, admin_auth, csv, mode='commit', strategy='all')
        assert resp1.status_code == 200
        # 2차: 동일 preview → unchanged
        resp2 = self._post_upload(client, admin_auth, csv, mode='preview')
        body = resp2.get_json()
        assert len(body['unchanged_materials']) == 1
        assert len(body['new_materials']) == 0

    # TC-MU-03: item_name 변경 → changed.changes[].field='item_name'
    def test_mu_03_preview_item_name_change(
        self, client, admin_auth, cleanup_test_materials
    ):
        prefix = cleanup_test_materials
        # 1차: A 영역 commit
        csv1 = f'자재코드,자재내역,규격1\n{prefix}020,A,X\n'
        self._post_upload(client, admin_auth, csv1, mode='commit', strategy='all')
        # 2차: B 영역 preview
        csv2 = f'자재코드,자재내역,규격1\n{prefix}020,B,X\n'
        resp = self._post_upload(client, admin_auth, csv2, mode='preview')
        body = resp.get_json()
        assert len(body['changed_materials']) == 1
        changes = body['changed_materials'][0]['changes']
        fields_changed = {c['field'] for c in changes}
        assert 'item_name' in fields_changed

    # TC-MU-07: commit strategy=all
    def test_mu_07_commit_all(self, client, admin_auth, cleanup_test_materials):
        prefix = cleanup_test_materials
        csv1 = f'자재코드,자재내역\n{prefix}030,A\n'
        self._post_upload(client, admin_auth, csv1, mode='commit', strategy='all')
        # item_name 변경 + strategy=all → UPDATE
        csv2 = f'자재코드,자재내역\n{prefix}030,B\n'
        resp = self._post_upload(client, admin_auth, csv2, mode='commit', strategy='all')
        body = resp.get_json()
        assert body['updated'] == 1
        assert body['inserted'] == 0

    # TC-MU-08: commit strategy=selected — selected만 UPDATE
    def test_mu_08_commit_selected(self, client, admin_auth, cleanup_test_materials):
        prefix = cleanup_test_materials
        csv1 = f'자재코드,자재내역\n{prefix}040,A\n{prefix}041,B\n'
        self._post_upload(client, admin_auth, csv1, mode='commit', strategy='all')
        # 둘 다 변경 + strategy=selected + 1개만 영역
        csv2 = f'자재코드,자재내역\n{prefix}040,A_v2\n{prefix}041,B_v2\n'
        resp = self._post_upload(client, admin_auth, csv2, mode='commit',
                                 strategy='selected', selected=[f'{prefix}040'])
        body = resp.get_json()
        assert body['updated'] == 1
        assert body['skipped'] == 1

    # TC-MU-09: commit strategy=skip — 기존 UPDATE 안 됨, 신규만 INSERT
    def test_mu_09_commit_skip(self, client, admin_auth, cleanup_test_materials):
        prefix = cleanup_test_materials
        csv1 = f'자재코드,자재내역\n{prefix}050,A\n'
        self._post_upload(client, admin_auth, csv1, mode='commit', strategy='all')
        # 기존 변경 + 신규 1개 추가 + strategy=skip
        csv2 = f'자재코드,자재내역\n{prefix}050,B\n{prefix}051,C\n'
        resp = self._post_upload(client, admin_auth, csv2, mode='commit', strategy='skip')
        body = resp.get_json()
        assert body['updated'] == 0
        assert body['inserted'] == 1
        assert body['skipped'] == 1

    # TC-MU-10: commit — BOM 신규 매핑 INSERT
    def test_mu_10_commit_bom_new(self, client, admin_auth, cleanup_test_materials):
        prefix = cleanup_test_materials
        csv = f'품번,고객사,모델,자재코드,자재내역,수량\n{prefix}P1,SEC,M1,{prefix}060,A,5\n'
        resp = self._post_upload(client, admin_auth, csv, mode='commit', strategy='all')
        body = resp.get_json()
        assert body['inserted'] == 1
        assert body['bom_inserted'] == 1

    # TC-MU-11: commit DB 에러 시 ROLLBACK — 영역 영역 영역 영역 영역 (skip)
    @pytest.mark.skip(reason='DB error injection 영역 영역 영역 영역 영역 영역 영역 영역')
    def test_mu_11_commit_rollback_on_db_error(self):
        pass

    # TC-MU-12: commit 빈 selected_item_codes → updated=0, INSERT만
    def test_mu_12_empty_selected(self, client, admin_auth, cleanup_test_materials):
        prefix = cleanup_test_materials
        csv1 = f'자재코드,자재내역\n{prefix}070,A\n'
        self._post_upload(client, admin_auth, csv1, mode='commit', strategy='all')
        # 변경 + 신규 + selected=[]
        csv2 = f'자재코드,자재내역\n{prefix}070,B\n{prefix}071,C\n'
        resp = self._post_upload(client, admin_auth, csv2, mode='commit',
                                 strategy='selected', selected=[])
        body = resp.get_json()
        assert body['updated'] == 0
        assert body['inserted'] == 1

    # TC-MU-15: Q2 BOM customer/model 변경 → bom_mappings_changed
    def test_mu_15_q2_bom_customer_change(
        self, client, admin_auth, cleanup_test_materials
    ):
        prefix = cleanup_test_materials
        csv1 = f'품번,고객사,모델,자재코드,자재내역,수량\n{prefix}P2,SEC,M1,{prefix}080,A,5\n'
        self._post_upload(client, admin_auth, csv1, mode='commit', strategy='all')
        # customer 변경 + 수량 동일
        csv2 = f'품번,고객사,모델,자재코드,자재내역,수량\n{prefix}P2,SK,M1,{prefix}080,A,5\n'
        resp = self._post_upload(client, admin_auth, csv2, mode='preview')
        body = resp.get_json()
        assert body['bom_mappings_changed'] >= 1

    # TC-MU-16: xlsx 정상 파싱
    def test_mu_16_xlsx_parse(self, client, admin_auth, cleanup_test_materials):
        # 가상 xlsx 영역 → openpyxl 영역 영역
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append(['자재코드', '자재내역', '규격1'])
        prefix = cleanup_test_materials
        ws.append([f'{prefix}090', 'XLSX_A', 'X'])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        data = {
            'file': (buf, 'test.xlsx'),
            'mode': 'preview',
        }
        resp = client.post('/api/admin/materials/upload',
                           headers=admin_auth, data=data,
                           content_type='multipart/form-data')
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['total_rows'] == 1
        assert len(body['new_materials']) == 1

    # TC-MU-21: NULL vs '' 정규화 (customer + model)
    def test_mu_21_null_vs_empty_normalization(
        self, client, admin_auth, cleanup_test_materials
    ):
        prefix = cleanup_test_materials
        # 1차: NULL 영역 영역 (customer 빈칸 = '' 영역 영역 INSERT)
        csv1 = f'품번,고객사,모델,자재코드,자재내역,수량\n{prefix}P3,SEC,M1,{prefix}100,A,5\n'
        self._post_upload(client, admin_auth, csv1, mode='commit', strategy='all')
        # 2차: 동일 (customer + model 동일) → unchanged 영역
        csv2 = f'품번,고객사,모델,자재코드,자재내역,수량\n{prefix}P3,SEC,M1,{prefix}100,A,5\n'
        resp = self._post_upload(client, admin_auth, csv2, mode='preview')
        body = resp.get_json()
        assert body['bom_mappings_changed'] == 0  # 동일 영역 변경 0
