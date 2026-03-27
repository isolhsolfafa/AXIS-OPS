"""
Sprint 40-A: 오늘 태깅 QR 드롭다운 BE API 테스트
엔드포인트: GET /api/app/work/today-tags

TC-40A-01: 인증된 작업자 → 200 + tags 배열
TC-40A-02: 오늘 태깅 이력 없는 작업자 → 빈 배열
TC-40A-03: 같은 QR 2번 태깅 → 중복 제거, 1건만
TC-40A-04: 응답 필드 검증 — qr_doc_id, serial_number, last_tagged_at
TC-40A-05: 토큰 없이 호출 → 401

KST(Asia/Seoul) 기준 오늘 태깅 이력만 반환하는지 검증.
"""

import sys
from pathlib import Path

_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest
from datetime import datetime, timedelta, timezone

_PREFIX = 'SP40A-'

# KST = UTC+9
_KST = timezone(timedelta(hours=9))


# ── 공통 헬퍼 ──────────────────────────────────────────────────

def _insert_product(db_conn, serial_number, model='GALLANT-50',
                    mech_partner='FNI', elec_partner='P&S'):
    """plan.product_info + qr_registry + completion_status 삽입"""
    qr_doc_id = f'DOC_{serial_number}'
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO plan.product_info (serial_number, model, mech_partner, elec_partner, ship_plan_date)
        VALUES (%s, %s, %s, %s, '2099-12-31')
        ON CONFLICT (serial_number) DO NOTHING
    """, (serial_number, model, mech_partner, elec_partner))
    cursor.execute("""
        INSERT INTO qr_registry (qr_doc_id, serial_number, status)
        VALUES (%s, %s, 'active')
        ON CONFLICT (qr_doc_id) DO NOTHING
    """, (qr_doc_id, serial_number))
    cursor.execute("""
        INSERT INTO completion_status (serial_number)
        VALUES (%s)
        ON CONFLICT (serial_number) DO NOTHING
    """, (serial_number,))
    db_conn.commit()
    cursor.close()
    return qr_doc_id


def _insert_task_detail(db_conn, serial_number, qr_doc_id, worker_id,
                        category='MECH', task_id_ref='SELF_INSPECTION',
                        task_name='자주검사'):
    """app_task_details 레코드 삽입 → 반환: task_detail_id"""
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO app_task_details
            (worker_id, serial_number, qr_doc_id, task_category, task_id, task_name, is_applicable)
        VALUES (%s, %s, %s, %s, %s, %s, true)
        ON CONFLICT (serial_number, qr_doc_id, task_category, task_id)
            DO UPDATE SET worker_id = EXCLUDED.worker_id
        RETURNING id
    """, (worker_id, serial_number, qr_doc_id, category, task_id_ref, task_name))
    task_detail_id = cursor.fetchone()[0]
    db_conn.commit()
    cursor.close()
    return task_detail_id


def _insert_start_log(db_conn, task_detail_id, worker_id, serial_number, qr_doc_id,
                      started_at=None, category='MECH', task_id_ref='SELF_INSPECTION',
                      task_name='자주검사'):
    """work_start_log 삽입 → 반환: log_id"""
    if started_at is None:
        started_at = datetime.now(_KST)
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO work_start_log
            (task_id, worker_id, serial_number, qr_doc_id, task_category,
             task_id_ref, task_name, started_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (task_detail_id, worker_id, serial_number, qr_doc_id,
          category, task_id_ref, task_name, started_at))
    log_id = cursor.fetchone()[0]
    db_conn.commit()
    cursor.close()
    return log_id


def _cleanup(db_conn, serial_numbers: list, worker_ids: list):
    """테스트 데이터 클린업 (FK 의존 순서 준수)"""
    cursor = db_conn.cursor()
    try:
        for sn in serial_numbers:
            cursor.execute("DELETE FROM work_start_log WHERE serial_number = %s", (sn,))
            cursor.execute("DELETE FROM work_completion_log WHERE serial_number = %s", (sn,))
            cursor.execute("DELETE FROM work_pause_log WHERE task_id IN "
                           "(SELECT id FROM app_task_details WHERE serial_number = %s)", (sn,))
            cursor.execute("DELETE FROM app_task_details WHERE serial_number = %s", (sn,))
            cursor.execute("DELETE FROM completion_status WHERE serial_number = %s", (sn,))
            cursor.execute("DELETE FROM qr_registry WHERE serial_number = %s", (sn,))
            cursor.execute("DELETE FROM plan.product_info WHERE serial_number = %s", (sn,))
        for wid in worker_ids:
            cursor.execute("DELETE FROM work_start_log WHERE worker_id = %s", (wid,))
            cursor.execute("DELETE FROM work_completion_log WHERE worker_id = %s", (wid,))
            cursor.execute("DELETE FROM work_pause_log WHERE worker_id = %s", (wid,))
            cursor.execute("DELETE FROM app_alert_logs WHERE triggered_by_worker_id = %s "
                           "OR target_worker_id = %s", (wid, wid))
            cursor.execute("DELETE FROM email_verification WHERE worker_id = %s", (wid,))
            cursor.execute("DELETE FROM hr.worker_auth_settings WHERE worker_id = %s", (wid,))
            cursor.execute("DELETE FROM hr.partner_attendance WHERE worker_id = %s", (wid,))
            cursor.execute("DELETE FROM workers WHERE id = %s", (wid,))
        db_conn.commit()
    except Exception as e:
        db_conn.rollback()
        print(f"[cleanup] warning: {e}")
    finally:
        cursor.close()


# ── 테스트 케이스 ──────────────────────────────────────────────


class TestTodayTagsAPI:
    """
    GET /api/app/work/today-tags 테스트 (5건)
    """

    def test_tc_40a_01_authenticated_worker_returns_200_with_tags(
        self, client, seed_test_data, create_test_worker, get_auth_token, db_conn
    ):
        """TC-40A-01: 인증된 작업자 → 200 + tags 배열"""
        test_id = f'{_PREFIX}01'
        serial = f'SP40A-01-SN-001'
        worker_ids = []

        try:
            # 작업자 생성
            worker_id = create_test_worker(
                email='sp40a_01_worker@test.axisos.com',
                password='Pass123!',
                name=f'{test_id} Worker',
                role='MECH',
                company='FNI',
            )
            worker_ids.append(worker_id)

            # 제품 + QR 등록
            qr_doc_id = _insert_product(db_conn, serial)

            # task_detail 생성 (work_start_log FK 필요)
            task_detail_id = _insert_task_detail(
                db_conn, serial, qr_doc_id, worker_id
            )

            # 오늘 태깅 이력 삽입
            _insert_start_log(
                db_conn, task_detail_id, worker_id, serial, qr_doc_id
            )

            # API 호출
            token = get_auth_token(worker_id, role='MECH')
            resp = client.get(
                '/api/app/work/today-tags',
                headers={'Authorization': f'Bearer {token}'}
            )

            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.get_data(as_text=True)}"
            data = resp.get_json()
            assert 'tags' in data, "응답에 'tags' 키가 없습니다."
            assert isinstance(data['tags'], list), "'tags'가 리스트가 아닙니다."
            assert len(data['tags']) >= 1, "태그 목록이 비어 있습니다."

        finally:
            _cleanup(db_conn, [serial], worker_ids)

    def test_tc_40a_02_no_tags_today_returns_empty_list(
        self, client, seed_test_data, create_test_worker, get_auth_token, db_conn
    ):
        """TC-40A-02: 오늘 태깅 이력 없는 작업자 → 빈 배열"""
        test_id = f'{_PREFIX}02'
        worker_ids = []

        try:
            # 작업자 생성 (태깅 없음)
            worker_id = create_test_worker(
                email='sp40a_02_worker@test.axisos.com',
                password='Pass123!',
                name=f'{test_id} Worker',
                role='MECH',
                company='FNI',
            )
            worker_ids.append(worker_id)

            # API 호출
            token = get_auth_token(worker_id, role='MECH')
            resp = client.get(
                '/api/app/work/today-tags',
                headers={'Authorization': f'Bearer {token}'}
            )

            assert resp.status_code == 200
            data = resp.get_json()
            assert 'tags' in data
            assert data['tags'] == [], f"빈 배열이어야 하는데 {data['tags']} 반환됨"

        finally:
            _cleanup(db_conn, [], worker_ids)

    def test_tc_40a_03_same_qr_tagged_twice_returns_one_entry(
        self, client, seed_test_data, create_test_worker, get_auth_token, db_conn
    ):
        """TC-40A-03: 같은 QR 2번 태깅 → 중복 제거, 1건만"""
        test_id = f'{_PREFIX}03'
        serial = 'SP40A-03-SN-001'
        worker_ids = []

        try:
            # 작업자 생성
            worker_id = create_test_worker(
                email='sp40a_03_worker@test.axisos.com',
                password='Pass123!',
                name=f'{test_id} Worker',
                role='MECH',
                company='FNI',
            )
            worker_ids.append(worker_id)

            # 제품 + QR 등록
            qr_doc_id = _insert_product(db_conn, serial)

            # task_detail 생성
            task_detail_id = _insert_task_detail(
                db_conn, serial, qr_doc_id, worker_id
            )

            # 동일 QR 2번 태깅 (시간 차이를 두어 중복 확인)
            now_kst = datetime.now(_KST)
            _insert_start_log(
                db_conn, task_detail_id, worker_id, serial, qr_doc_id,
                started_at=now_kst - timedelta(hours=2)
            )
            _insert_start_log(
                db_conn, task_detail_id, worker_id, serial, qr_doc_id,
                started_at=now_kst - timedelta(hours=1)
            )

            # API 호출
            token = get_auth_token(worker_id, role='MECH')
            resp = client.get(
                '/api/app/work/today-tags',
                headers={'Authorization': f'Bearer {token}'}
            )

            assert resp.status_code == 200
            data = resp.get_json()
            assert 'tags' in data

            # 해당 QR에 대한 항목이 1건만 존재해야 함 (DISTINCT)
            matching = [t for t in data['tags'] if t['qr_doc_id'] == qr_doc_id]
            assert len(matching) == 1, (
                f"DISTINCT 적용 후 1건이어야 하는데 {len(matching)}건 반환됨"
            )

        finally:
            _cleanup(db_conn, [serial], worker_ids)

    def test_tc_40a_04_response_fields_validation(
        self, client, seed_test_data, create_test_worker, get_auth_token, db_conn
    ):
        """TC-40A-04: 응답 필드 검증 — qr_doc_id, serial_number, last_tagged_at"""
        test_id = f'{_PREFIX}04'
        serial = 'SP40A-04-SN-001'
        worker_ids = []

        try:
            # 작업자 생성
            worker_id = create_test_worker(
                email='sp40a_04_worker@test.axisos.com',
                password='Pass123!',
                name=f'{test_id} Worker',
                role='MECH',
                company='FNI',
            )
            worker_ids.append(worker_id)

            # 제품 + QR 등록
            qr_doc_id = _insert_product(db_conn, serial)

            # task_detail 생성
            task_detail_id = _insert_task_detail(
                db_conn, serial, qr_doc_id, worker_id
            )

            # 오늘 태깅 이력 삽입
            tag_time = datetime.now(_KST) - timedelta(minutes=30)
            _insert_start_log(
                db_conn, task_detail_id, worker_id, serial, qr_doc_id,
                started_at=tag_time
            )

            # API 호출
            token = get_auth_token(worker_id, role='MECH')
            resp = client.get(
                '/api/app/work/today-tags',
                headers={'Authorization': f'Bearer {token}'}
            )

            assert resp.status_code == 200
            data = resp.get_json()
            assert 'tags' in data
            assert len(data['tags']) >= 1

            # 필드 존재 확인
            tag = next((t for t in data['tags'] if t['qr_doc_id'] == qr_doc_id), None)
            assert tag is not None, f"qr_doc_id={qr_doc_id} 항목이 없습니다."
            assert 'qr_doc_id' in tag, "'qr_doc_id' 필드 누락"
            assert 'serial_number' in tag, "'serial_number' 필드 누락"
            assert 'last_tagged_at' in tag, "'last_tagged_at' 필드 누락"

            # 값 검증
            assert tag['qr_doc_id'] == qr_doc_id
            assert tag['serial_number'] == serial
            assert tag['last_tagged_at'] is not None, "'last_tagged_at'가 None입니다."
            # ISO 8601 형식인지 확인 (파싱 가능 여부)
            datetime.fromisoformat(tag['last_tagged_at'].replace('Z', '+00:00'))

        finally:
            _cleanup(db_conn, [serial], worker_ids)

    def test_tc_40a_05_no_token_returns_401(
        self, client, seed_test_data
    ):
        """TC-40A-05: 토큰 없이 호출 → 401"""
        resp = client.get('/api/app/work/today-tags')
        assert resp.status_code == 401, (
            f"인증 없이 호출 시 401이어야 하는데 {resp.status_code} 반환됨"
        )
