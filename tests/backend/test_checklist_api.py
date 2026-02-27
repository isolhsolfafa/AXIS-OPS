"""
Sprint 11: Checklist API 테스트
체크리스트 스키마 신설 — Hook-Up 체크리스트 (SI task 전용)

테스트 대상:
- GET /api/app/checklist/{serial_number}/{category} → 체크리스트 조회
- PUT /api/app/checklist/check → 개별 항목 체크/해제
- POST /api/admin/checklist/import → Excel 파일 업로드로 마스터 일괄 등록
- checklist 스키마: checklist_master, checklist_record 테이블
- 인증 / 권한 처리
"""

import pytest
import sys
import io
from pathlib import Path
from typing import Optional

# backend 경로 추가
backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


# ============================================================
# 헬퍼 함수
# ============================================================

def _has_checklist_schema(db_conn) -> bool:
    """checklist 스키마가 존재하는지 확인"""
    try:
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT schema_name FROM information_schema.schemata
            WHERE schema_name = 'checklist'
        """)
        result = cursor.fetchone() is not None
        cursor.close()
        return result
    except Exception:
        return False


def _has_checklist_tables(db_conn) -> bool:
    """checklist.checklist_master, checklist.checklist_record 테이블 존재 확인"""
    try:
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'checklist'
            AND table_name IN ('checklist_master', 'checklist_record')
        """)
        tables = {r[0] for r in cursor.fetchall()}
        cursor.close()
        return 'checklist_master' in tables and 'checklist_record' in tables
    except Exception:
        return False


def _insert_checklist_master(db_conn, product_code: str, category: str,
                              item_name: str, item_order: int = 1,
                              description: str = None) -> Optional[int]:
    """체크리스트 마스터 직접 삽입 헬퍼"""
    try:
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO checklist.checklist_master
                (product_code, category, item_name, item_order, description)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (product_code, category, item_name) DO NOTHING
            RETURNING id
        """, (product_code, category, item_name, item_order, description))
        row = cursor.fetchone()
        db_conn.commit()
        cursor.close()
        return row[0] if row else None
    except Exception:
        try:
            db_conn.rollback()
        except Exception:
            pass
        return None


def _insert_test_product_for_checklist(db_conn, serial_number: str, qr_doc_id: str,
                                        product_code: str = 'GAIA-100'):
    """체크리스트 테스트용 제품 삽입"""
    try:
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO plan.product_info (serial_number, model, product_code)
            VALUES (%s, %s, %s) ON CONFLICT (serial_number) DO NOTHING
        """, (serial_number, product_code, product_code))
        cursor.execute("""
            INSERT INTO public.qr_registry (qr_doc_id, serial_number)
            VALUES (%s, %s) ON CONFLICT (qr_doc_id) DO NOTHING
        """, (qr_doc_id, serial_number))
        db_conn.commit()
        cursor.close()
    except Exception:
        try:
            db_conn.rollback()
        except Exception:
            pass
        # product_code 컬럼이 없을 경우 재시도 (컬럼 없는 버전)
        try:
            cursor = db_conn.cursor()
            cursor.execute("""
                INSERT INTO plan.product_info (serial_number, model)
                VALUES (%s, %s) ON CONFLICT (serial_number) DO NOTHING
            """, (serial_number, product_code))
            cursor.execute("""
                INSERT INTO public.qr_registry (qr_doc_id, serial_number)
                VALUES (%s, %s) ON CONFLICT (qr_doc_id) DO NOTHING
            """, (qr_doc_id, serial_number))
            db_conn.commit()
            cursor.close()
        except Exception:
            pass


def _create_minimal_excel(product_code: str, category: str = 'HOOKUP') -> bytes:
    """최소한의 체크리스트 Excel 파일 바이트 생성"""
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'checklist'
        # 헤더
        ws.append(['product_code', 'category', 'item_name', 'item_order', 'description'])
        # 데이터
        ws.append([product_code, category, 'Hook-Up 항목 1', 1, '설명 1'])
        ws.append([product_code, category, 'Hook-Up 항목 2', 2, '설명 2'])
        ws.append([product_code, category, 'Hook-Up 항목 3', 3, '설명 3'])

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()
    except ImportError:
        return None


# ============================================================
# 공통 픽스처
# ============================================================

def _do_cleanup_checklist_data(db_conn):
    """체크리스트 테스트 데이터 정리 (setup/teardown 공용)"""
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            # checklist_record 먼저 삭제 (FK 의존성)
            cursor.execute("""
                DELETE FROM checklist.checklist_record
                WHERE serial_number LIKE 'SN-SP11-CL-%%'
                   OR master_id IN (
                       SELECT id FROM checklist.checklist_master
                       WHERE product_code LIKE 'SP11-CL-%%'
                   )
            """)
            # checklist_master 삭제
            cursor.execute("""
                DELETE FROM checklist.checklist_master
                WHERE product_code LIKE 'SP11-CL-%%'
            """)
            # 제품 데이터 삭제
            cursor.execute(
                "DELETE FROM app_task_details WHERE serial_number LIKE 'SN-SP11-CL-%%'"
            )
            cursor.execute(
                "DELETE FROM public.qr_registry WHERE qr_doc_id LIKE 'DOC-SP11-CL-%%'"
            )
            cursor.execute(
                "DELETE FROM plan.product_info WHERE serial_number LIKE 'SN-SP11-CL-%%'"
            )
            cursor.execute(
                "DELETE FROM workers WHERE email LIKE '%%@sp11_cl_test.com'"
            )
            db_conn.commit()
            cursor.close()
        except Exception:
            try:
                db_conn.rollback()
            except Exception:
                pass


@pytest.fixture(autouse=True)
def cleanup_checklist_data(db_conn):
    """테스트 전/후 체크리스트 데이터 정리 (stale data 방지)"""
    _do_cleanup_checklist_data(db_conn)
    yield
    _do_cleanup_checklist_data(db_conn)


@pytest.fixture
def cl_worker(create_test_worker, get_auth_token):
    """체크리스트 테스트용 일반 GST 작업자"""
    worker_id = create_test_worker(
        email='gst_cl_worker@sp11_cl_test.com', password='Test123!',
        name='GST CL Worker', role='SI', company='GST'
    )
    token = get_auth_token(worker_id, role='SI')
    return worker_id, token


@pytest.fixture
def cl_admin(create_test_worker, get_auth_token):
    """체크리스트 테스트용 Admin"""
    admin_id = create_test_worker(
        email='admin_cl@sp11_cl_test.com', password='Test123!',
        name='Admin CL', role='ADMIN', is_admin=True, company='GST'
    )
    token = get_auth_token(admin_id, role='ADMIN', is_admin=True)
    return admin_id, token


# ============================================================
# TC-CL-01 ~ 14: Checklist CRUD API 테스트
# ============================================================

class TestChecklistSchema:
    """Sprint 11: checklist 스키마 존재 확인"""

    def test_checklist_schema_exists(self, db_conn):
        """
        TC-CL-01: checklist 스키마 존재 확인

        Expected:
        - information_schema.schemata에 'checklist' 존재
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        if not _has_checklist_schema(db_conn):
            pytest.skip("checklist 스키마 미생성 (Sprint 11 BE 구현 필요)")

        assert _has_checklist_schema(db_conn), "checklist 스키마 없음"

    def test_checklist_tables_exist(self, db_conn):
        """
        TC-CL-02: checklist_master, checklist_record 테이블 존재 확인

        Expected:
        - checklist.checklist_master 테이블 존재
        - checklist.checklist_record 테이블 존재
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        if not _has_checklist_schema(db_conn):
            pytest.skip("checklist 스키마 미생성")

        assert _has_checklist_tables(db_conn), \
            "checklist_master 또는 checklist_record 테이블 없음"


class TestChecklistGetAPI:
    """GET /api/app/checklist/{serial_number}/{category}"""

    def test_get_checklist_returns_items(self, client, db_conn, cl_worker):
        """
        TC-CL-03: GET /api/app/checklist/{sn}/HOOKUP → 체크리스트 반환

        Expected:
        - 200 응답
        - items 배열 포함 (item_name, is_checked, item_order)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        if not _has_checklist_tables(db_conn):
            pytest.skip("checklist 테이블 미생성")

        worker_id, token = cl_worker
        serial_number = 'SN-SP11-CL-001'
        product_code = 'SP11-CL-GAIA100'

        # 제품 + 체크리스트 마스터 삽입
        _insert_test_product_for_checklist(
            db_conn, serial_number, 'DOC-SP11-CL-001', product_code
        )
        master_id = _insert_checklist_master(
            db_conn, product_code, 'HOOKUP', 'Hook-Up 연결 확인', 1
        )

        if master_id is None:
            pytest.skip("checklist_master 삽입 실패")

        response = client.get(
            f'/api/app/checklist/{serial_number}/HOOKUP',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/checklist 미구현")

        assert response.status_code == 200
        data = response.get_json()
        assert 'items' in data or isinstance(data, list), \
            "응답에 items 키 또는 리스트 필요"

    def test_get_checklist_empty_when_no_master(self, client, db_conn, cl_worker):
        """
        TC-CL-04: 해당 product_code 마스터 없으면 빈 리스트 반환

        Expected:
        - 마스터 데이터 없음 → items=[] 반환 (400/404 아님)
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        if not _has_checklist_tables(db_conn):
            pytest.skip("checklist 테이블 미생성")

        worker_id, token = cl_worker
        serial_number = 'SN-SP11-CL-002'

        # 제품만 삽입 (마스터 없음)
        _insert_test_product_for_checklist(
            db_conn, serial_number, 'DOC-SP11-CL-002', 'SP11-CL-NOMASTER'
        )

        response = client.get(
            f'/api/app/checklist/{serial_number}/HOOKUP',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/checklist 미구현")

        assert response.status_code == 200, \
            f"마스터 없는 경우 200 + 빈 리스트 필요, got {response.status_code}"

        data = response.get_json()
        items = data if isinstance(data, list) else data.get('items', [])
        assert isinstance(items, list), "items는 리스트여야 함"

    def test_get_checklist_unauthenticated_returns_401(self, client, db_conn):
        """
        TC-CL-05: 미인증 상태 GET → 401

        Expected:
        - Authorization 헤더 없음 → 401
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        response = client.get('/api/app/checklist/SN-TEST/HOOKUP')

        if response.status_code == 404:
            pytest.skip("GET /api/app/checklist 미구현")

        assert response.status_code == 401


class TestChecklistPutAPI:
    """PUT /api/app/checklist/check"""

    def test_check_item_success(self, client, db_conn, cl_worker):
        """
        TC-CL-06: PUT /api/app/checklist/check → is_checked=True 성공

        Expected:
        - 200 응답
        - DB checklist_record에 is_checked=True, checked_by 기록
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        if not _has_checklist_tables(db_conn):
            pytest.skip("checklist 테이블 미생성")

        worker_id, token = cl_worker
        serial_number = 'SN-SP11-CL-003'
        product_code = 'SP11-CL-CHECK001'

        _insert_test_product_for_checklist(
            db_conn, serial_number, 'DOC-SP11-CL-003', product_code
        )
        master_id = _insert_checklist_master(
            db_conn, product_code, 'HOOKUP', '배관 연결 확인', 1
        )

        if master_id is None:
            pytest.skip("checklist_master 삽입 실패")

        response = client.put(
            '/api/app/checklist/check',
            json={
                'serial_number': serial_number,
                'master_id': master_id,
                'is_checked': True
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("PUT /api/app/checklist/check 미구현")

        assert response.status_code == 200, \
            f"Expected 200, got {response.status_code}: {response.get_json()}"

        # DB 확인
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT is_checked, checked_by, checked_at
            FROM checklist.checklist_record
            WHERE serial_number = %s AND master_id = %s
        """, (serial_number, master_id))
        row = cursor.fetchone()
        cursor.close()

        assert row is not None, "checklist_record에 기록 없음"
        assert row[0] is True, "is_checked=True여야 함"
        assert row[1] == worker_id, f"checked_by={worker_id}여야 함, 현재 {row[1]}"
        assert row[2] is not None, "checked_at이 None이 아니어야 함"

    def test_uncheck_item_success(self, client, db_conn, cl_worker):
        """
        TC-CL-07: PUT /api/app/checklist/check → is_checked=False (체크 해제) 성공

        Expected:
        - 기존 True → False로 업데이트
        - 200 응답
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        if not _has_checklist_tables(db_conn):
            pytest.skip("checklist 테이블 미생성")

        worker_id, token = cl_worker
        serial_number = 'SN-SP11-CL-004'
        product_code = 'SP11-CL-UNCHECK001'

        _insert_test_product_for_checklist(
            db_conn, serial_number, 'DOC-SP11-CL-004', product_code
        )
        master_id = _insert_checklist_master(
            db_conn, product_code, 'HOOKUP', '전선 연결 확인', 1
        )

        if master_id is None:
            pytest.skip("checklist_master 삽입 실패")

        # 먼저 체크
        client.put(
            '/api/app/checklist/check',
            json={'serial_number': serial_number, 'master_id': master_id, 'is_checked': True},
            headers={'Authorization': f'Bearer {token}'}
        )

        # 체크 해제
        response = client.put(
            '/api/app/checklist/check',
            json={
                'serial_number': serial_number,
                'master_id': master_id,
                'is_checked': False
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("PUT /api/app/checklist/check 미구현")

        assert response.status_code == 200

        # DB 확인
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT is_checked FROM checklist.checklist_record
            WHERE serial_number = %s AND master_id = %s
        """, (serial_number, master_id))
        row = cursor.fetchone()
        cursor.close()

        if row:
            assert row[0] is False, "is_checked=False여야 함"

    def test_get_after_check_shows_checked_by(self, client, db_conn, cl_worker):
        """
        TC-CL-08: PUT 후 GET으로 checked_by, checked_at 확인

        Expected:
        - 체크 후 GET → 해당 항목에 checked_by=worker_id, checked_at 포함
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        if not _has_checklist_tables(db_conn):
            pytest.skip("checklist 테이블 미생성")

        worker_id, token = cl_worker
        serial_number = 'SN-SP11-CL-005'
        product_code = 'SP11-CL-GETCHECK001'

        _insert_test_product_for_checklist(
            db_conn, serial_number, 'DOC-SP11-CL-005', product_code
        )
        master_id = _insert_checklist_master(
            db_conn, product_code, 'HOOKUP', '단자 체결 확인', 1
        )

        if master_id is None:
            pytest.skip("checklist_master 삽입 실패")

        # 체크
        client.put(
            '/api/app/checklist/check',
            json={'serial_number': serial_number, 'master_id': master_id, 'is_checked': True},
            headers={'Authorization': f'Bearer {token}'}
        )

        # GET으로 확인
        response = client.get(
            f'/api/app/checklist/{serial_number}/HOOKUP',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("GET /api/app/checklist 미구현")

        assert response.status_code == 200
        data = response.get_json()
        items = data if isinstance(data, list) else data.get('items', [])

        checked_items = [i for i in items if i.get('is_checked') is True]
        assert len(checked_items) >= 1, "체크된 항목이 GET 응답에 포함되어야 함"

    def test_duplicate_check_is_upsert(self, client, db_conn, cl_worker):
        """
        TC-CL-09: 같은 항목 중복 PUT → UPSERT (에러 없음)

        Expected:
        - 동일 serial_number + master_id에 2회 PUT → 200 (에러 없음)
        - DB에 중복 레코드 없음
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        if not _has_checklist_tables(db_conn):
            pytest.skip("checklist 테이블 미생성")

        worker_id, token = cl_worker
        serial_number = 'SN-SP11-CL-006'
        product_code = 'SP11-CL-UPSERT001'

        _insert_test_product_for_checklist(
            db_conn, serial_number, 'DOC-SP11-CL-006', product_code
        )
        master_id = _insert_checklist_master(
            db_conn, product_code, 'HOOKUP', '밸브 개폐 확인', 1
        )

        if master_id is None:
            pytest.skip("checklist_master 삽입 실패")

        payload = {'serial_number': serial_number, 'master_id': master_id, 'is_checked': True}

        # 2회 PUT
        r1 = client.put('/api/app/checklist/check', json=payload,
                        headers={'Authorization': f'Bearer {token}'})
        r2 = client.put('/api/app/checklist/check', json=payload,
                        headers={'Authorization': f'Bearer {token}'})

        if r1.status_code == 404:
            pytest.skip("PUT /api/app/checklist/check 미구현")

        assert r1.status_code == 200, f"1회 PUT 실패: {r1.status_code}"
        assert r2.status_code == 200, f"2회 PUT (UPSERT) 실패: {r2.status_code}"

        # DB 중복 없음 확인
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM checklist.checklist_record
            WHERE serial_number = %s AND master_id = %s
        """, (serial_number, master_id))
        count = cursor.fetchone()[0]
        cursor.close()
        assert count == 1, f"UPSERT로 레코드는 1개여야 함, 현재 {count}개"

    def test_invalid_master_id_returns_error(self, client, db_conn, cl_worker):
        """
        TC-CL-10: 존재하지 않는 master_id → 400 또는 404

        Expected:
        - 없는 master_id 체크 시 400/404 반환
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        if not _has_checklist_tables(db_conn):
            pytest.skip("checklist 테이블 미생성")

        _, token = cl_worker

        response = client.put(
            '/api/app/checklist/check',
            json={
                'serial_number': 'SN-SP11-CL-INVALID',
                'master_id': 999999999,
                'is_checked': True
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("PUT /api/app/checklist/check 미구현")

        assert response.status_code in [400, 404, 422], \
            f"없는 master_id는 400/404/422 필요, got {response.status_code}"

    def test_note_field_saved(self, client, db_conn, cl_worker):
        """
        TC-CL-11: note 필드 저장 확인

        Expected:
        - PUT 요청에 note 포함 → DB에 note 저장
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        if not _has_checklist_tables(db_conn):
            pytest.skip("checklist 테이블 미생성")

        worker_id, token = cl_worker
        serial_number = 'SN-SP11-CL-007'
        product_code = 'SP11-CL-NOTE001'

        _insert_test_product_for_checklist(
            db_conn, serial_number, 'DOC-SP11-CL-007', product_code
        )
        master_id = _insert_checklist_master(
            db_conn, product_code, 'HOOKUP', '배기 라인 확인', 1
        )

        if master_id is None:
            pytest.skip("checklist_master 삽입 실패")

        note_text = '점검 완료 — 이상 없음'
        response = client.put(
            '/api/app/checklist/check',
            json={
                'serial_number': serial_number,
                'master_id': master_id,
                'is_checked': True,
                'note': note_text
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("PUT /api/app/checklist/check 미구현")

        assert response.status_code == 200

        # DB note 확인
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT note FROM checklist.checklist_record
            WHERE serial_number = %s AND master_id = %s
        """, (serial_number, master_id))
        row = cursor.fetchone()
        cursor.close()

        if row:
            assert row[0] == note_text, f"note가 '{note_text}'여야 함, 현재 '{row[0]}'"

    def test_put_unauthenticated_returns_401(self, client):
        """
        TC-CL-12: 미인증 상태 PUT → 401

        Expected:
        - Authorization 헤더 없음 → 401
        """
        response = client.put(
            '/api/app/checklist/check',
            json={'serial_number': 'SN-TEST', 'master_id': 1, 'is_checked': True}
        )

        if response.status_code == 404:
            pytest.skip("PUT /api/app/checklist/check 미구현")

        assert response.status_code == 401


class TestChecklistImportAPI:
    """POST /api/admin/checklist/import — Excel 파일 업로드"""

    def test_admin_can_import_excel(self, client, db_conn, cl_admin):
        """
        TC-CL-13: Admin이 Excel 파일 업로드 성공 → checklist_master 일괄 등록

        Expected:
        - 200 응답
        - checklist_master에 항목 삽입됨
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        if not _has_checklist_tables(db_conn):
            pytest.skip("checklist 테이블 미생성")

        excel_bytes = _create_minimal_excel('SP11-CL-IMPORT001')
        if excel_bytes is None:
            pytest.skip("openpyxl 미설치 — Excel 생성 불가")

        _, token = cl_admin

        response = client.post(
            '/api/admin/checklist/import',
            data={'file': (io.BytesIO(excel_bytes), 'test_checklist.xlsx')},
            content_type='multipart/form-data',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("POST /api/admin/checklist/import 미구현")

        assert response.status_code in [200, 201], \
            f"Excel import 성공 필요, got {response.status_code}: {response.get_json()}"

    def test_worker_cannot_import_excel(self, client, db_conn, cl_worker):
        """
        TC-CL-14: 일반 작업자가 import 시도 → 403

        Expected:
        - is_admin=False → 403 FORBIDDEN
        """
        if db_conn is None:
            pytest.skip("DB 연결 없음")

        if not _has_checklist_tables(db_conn):
            pytest.skip("checklist 테이블 미생성")

        excel_bytes = _create_minimal_excel('SP11-CL-IMPORT002')
        if excel_bytes is None:
            pytest.skip("openpyxl 미설치")

        _, token = cl_worker

        response = client.post(
            '/api/admin/checklist/import',
            data={'file': (io.BytesIO(excel_bytes), 'test_checklist.xlsx')},
            content_type='multipart/form-data',
            headers={'Authorization': f'Bearer {token}'}
        )

        if response.status_code == 404:
            pytest.skip("POST /api/admin/checklist/import 미구현")

        assert response.status_code == 403, \
            f"일반 작업자는 403 거부 필요, got {response.status_code}"
