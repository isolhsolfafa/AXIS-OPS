"""
공지사항 API 테스트
Sprint 20-B: notices CRUD API
"""

import pytest


@pytest.fixture(autouse=True)
def cleanup_notices(db_conn):
    """테스트 전후 notices 데이터 정리"""
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            cursor.execute("DELETE FROM notices WHERE title LIKE 'NTC-TEST-%'")
            cursor.execute("DELETE FROM workers WHERE email LIKE 'ntc_test_%@test.com'")
            db_conn.commit()
            cursor.close()
        except Exception:
            db_conn.rollback()

    yield

    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            cursor.execute("DELETE FROM notices WHERE title LIKE 'NTC-TEST-%'")
            cursor.execute("DELETE FROM workers WHERE email LIKE 'ntc_test_%@test.com'")
            cursor.execute("DELETE FROM workers WHERE email = 'admin_sprint4@test.axisos.com'")
            db_conn.commit()
            cursor.close()
        except Exception:
            pass


@pytest.fixture
def admin_token(create_test_worker, get_admin_auth_token):
    """Admin 토큰"""
    admin_id = create_test_worker(
        email='ntc_test_admin@test.com', password='Test123!',
        name='NTC Admin', role='QI', is_admin=True, company='GST',
    )
    return get_admin_auth_token(admin_id)


@pytest.fixture
def worker_token(create_test_worker, get_auth_token):
    """일반 작업자 토큰"""
    worker_id = create_test_worker(
        email='ntc_test_worker@test.com', password='Test123!',
        name='NTC Worker', role='MECH', company='FNI',
    )
    return get_auth_token(worker_id)


class TestNoticeCreate:
    """POST /api/admin/notices"""

    def test_ntc01_admin_create_notice(self, client, admin_token):
        """NTC-01: Admin이 공지 작성 → 목록에 표시"""
        response = client.post('/api/admin/notices', json={
            'title': 'NTC-TEST-공지 제목',
            'content': '공지 내용입니다.',
            'version': '1.4.0',
        }, headers={'Authorization': f'Bearer {admin_token}'})

        assert response.status_code == 201
        data = response.get_json()
        assert data['notice']['title'] == 'NTC-TEST-공지 제목'
        assert data['notice']['version'] == '1.4.0'

        # 목록에서 확인
        list_resp = client.get(
            '/api/notices',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert list_resp.status_code == 200
        notices = list_resp.get_json()['notices']
        assert any(n['title'] == 'NTC-TEST-공지 제목' for n in notices)

    def test_ntc02_non_admin_create_forbidden(self, client, worker_token):
        """NTC-02: 일반 작업자 → 작성 API 403"""
        response = client.post('/api/admin/notices', json={
            'title': 'NTC-TEST-불가',
            'content': '내용',
        }, headers={'Authorization': f'Bearer {worker_token}'})

        assert response.status_code == 403


class TestNoticeList:
    """GET /api/notices"""

    def test_ntc03_pagination(self, client, admin_token):
        """NTC-03: 페이지네이션"""
        # 12개 공지 생성
        for i in range(12):
            client.post('/api/admin/notices', json={
                'title': f'NTC-TEST-공지{i:02d}',
                'content': f'내용{i}',
            }, headers={'Authorization': f'Bearer {admin_token}'})

        # 첫 페이지 (10개)
        resp1 = client.get(
            '/api/notices?page=1&limit=10',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert resp1.status_code == 200
        data1 = resp1.get_json()
        assert len(data1['notices']) == 10
        assert data1['total'] >= 12

        # 두 번째 페이지
        resp2 = client.get(
            '/api/notices?page=2&limit=10',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert resp2.status_code == 200
        data2 = resp2.get_json()
        assert len(data2['notices']) >= 2

    def test_ntc04_pinned_on_top(self, client, admin_token):
        """NTC-04: 고정 공지 상단 표시"""
        # 일반 공지
        client.post('/api/admin/notices', json={
            'title': 'NTC-TEST-일반공지',
            'content': '일반',
        }, headers={'Authorization': f'Bearer {admin_token}'})

        # 고정 공지
        client.post('/api/admin/notices', json={
            'title': 'NTC-TEST-고정공지',
            'content': '고정',
            'is_pinned': True,
        }, headers={'Authorization': f'Bearer {admin_token}'})

        resp = client.get(
            '/api/notices',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert resp.status_code == 200
        notices = resp.get_json()['notices']

        # NTC-TEST 공지만 필터
        test_notices = [n for n in notices if n['title'].startswith('NTC-TEST-')]
        pinned_idx = next((i for i, n in enumerate(test_notices) if n['title'] == 'NTC-TEST-고정공지'), None)
        normal_idx = next((i for i, n in enumerate(test_notices) if n['title'] == 'NTC-TEST-일반공지'), None)

        assert pinned_idx is not None
        assert normal_idx is not None
        assert pinned_idx < normal_idx


class TestNoticeUpdateDelete:
    """PUT/DELETE /api/admin/notices/<id>"""

    def test_ntc05_update_and_delete(self, client, admin_token):
        """NTC-05: 공지 수정/삭제"""
        # 작성
        create_resp = client.post('/api/admin/notices', json={
            'title': 'NTC-TEST-수정테스트',
            'content': '원본 내용',
        }, headers={'Authorization': f'Bearer {admin_token}'})
        notice_id = create_resp.get_json()['notice']['id']

        # 수정
        update_resp = client.put(f'/api/admin/notices/{notice_id}', json={
            'title': 'NTC-TEST-수정완료',
            'content': '수정된 내용',
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert update_resp.status_code == 200

        # 수정 확인
        detail_resp = client.get(
            f'/api/notices/{notice_id}',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert detail_resp.get_json()['title'] == 'NTC-TEST-수정완료'

        # 삭제
        delete_resp = client.delete(
            f'/api/admin/notices/{notice_id}',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert delete_resp.status_code == 200

        # 삭제 확인
        gone_resp = client.get(
            f'/api/notices/{notice_id}',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert gone_resp.status_code == 404


class TestNoticeVersionFilter:
    """GET /api/notices?version="""

    def test_ntc06_version_filter(self, client, admin_token):
        """NTC-06: 버전 필터"""
        client.post('/api/admin/notices', json={
            'title': 'NTC-TEST-v140',
            'content': 'v1.4.0 노트',
            'version': '1.4.0',
        }, headers={'Authorization': f'Bearer {admin_token}'})

        client.post('/api/admin/notices', json={
            'title': 'NTC-TEST-v150',
            'content': 'v1.5.0 노트',
            'version': '1.5.0',
        }, headers={'Authorization': f'Bearer {admin_token}'})

        resp = client.get(
            '/api/notices?version=1.4.0',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert resp.status_code == 200
        notices = resp.get_json()['notices']
        test_notices = [n for n in notices if n['title'].startswith('NTC-TEST-')]
        assert all(n['version'] == '1.4.0' for n in test_notices)
        assert any(n['title'] == 'NTC-TEST-v140' for n in test_notices)
