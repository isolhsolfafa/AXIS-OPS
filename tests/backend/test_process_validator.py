"""
공정 검증 API 테스트
엔드포인트: POST /api/app/validation/check-process
Sprint 3: 공정 누락 검증 + 알림 생성
Sprint 6: mech_completed/elec_completed 컬럼 (Sprint 6 마이그레이션 필요)
"""

import pytest
from datetime import datetime, timezone


@pytest.fixture(autouse=True)
def skip_if_no_sprint6(has_sprint6_schema, request):
    """Sprint 6 스키마 없으면 해당 클래스 테스트 스킵"""
    # TestProcessValidationNoProduct, TestProcessValidationNonInspection은 스킵 안 함
    skip_classes = [
        'TestProcessValidationMMIncomplete',
        'TestProcessValidationEEIncomplete',
        'TestProcessValidationBothComplete',
        'TestLocationQRCheck'
    ]
    if request.cls and request.cls.__name__ in skip_classes and not has_sprint6_schema:
        pytest.skip("Sprint 6 DB 마이그레이션 필요 (mech_completed 컬럼 없음)")


@pytest.fixture(autouse=True)
def cleanup_process_alerts(db_conn):
    """테스트 후 공정 검증으로 생성된 알림 정리"""
    yield
    if db_conn and not db_conn.closed:
        try:
            cursor = db_conn.cursor()
            cursor.execute(
                "DELETE FROM app_alert_logs WHERE serial_number LIKE 'SN-PROC%%'"
            )
            db_conn.commit()
            cursor.close()
        except Exception:
            pass


class TestProcessValidationMMIncomplete:
    """MECH 미완료 시 PI 공정 검증"""

    def test_pi_mm_incomplete(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token
    ):
        """
        PI 작업자가 MECH 미완료 제품을 검증
        → can_proceed=false, MECH in missing_processes, 알림 생성

        Expected:
        - Status 200
        - valid == false
        - missing_processes에 'MECH' 포함
        - alerts_created >= 1 (MECH 관리자가 있을 때)
        """
        pi_worker_id = create_test_worker(
            email='pi_proc@test.com', password='Test123!',
            name='PI Proc Worker', role='PI'
        )
        # MECH 관리자 생성 (알림 대상)
        create_test_worker(
            email='mech_mgr_proc@test.com', password='Test123!',
            name='MECH Manager Proc', role='MECH', is_manager=True
        )

        create_test_product(
            qr_doc_id='DOC-PROC-001',
            serial_number='SN-PROC-001',
            model='GBWS-50',
            location_qr_id='LOC_A'
        )

        create_test_completion_status(
            serial_number='SN-PROC-001',
            mech_completed=False,
            elec_completed=True
        )

        token = get_auth_token(pi_worker_id, role='PI')
        response = client.post(
            '/api/app/validation/check-process',
            json={
                'serial_number': 'SN-PROC-001',
                'process_type': 'PI'
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is False
        assert 'MECH' in data['missing_processes']
        assert data['alerts_created'] >= 1


class TestProcessValidationEEIncomplete:
    """ELEC 미완료 시 QI 공정 검증"""

    def test_qi_ee_incomplete(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token
    ):
        """
        QI 작업자가 ELEC 미완료 제품을 검증
        → can_proceed=false, ELEC in missing_processes

        Expected:
        - Status 200
        - valid == false
        - missing_processes에 'ELEC' 포함
        """
        qi_worker_id = create_test_worker(
            email='qi_proc@test.com', password='Test123!',
            name='QI Proc Worker', role='QI'
        )
        create_test_worker(
            email='elec_mgr_proc@test.com', password='Test123!',
            name='ELEC Manager Proc', role='ELEC', is_manager=True
        )

        create_test_product(
            qr_doc_id='DOC-PROC-002',
            serial_number='SN-PROC-002',
            model='GBWS-50',
            location_qr_id='LOC_B'
        )

        create_test_completion_status(
            serial_number='SN-PROC-002',
            mech_completed=True,
            elec_completed=False
        )

        token = get_auth_token(qi_worker_id, role='QI')
        response = client.post(
            '/api/app/validation/check-process',
            json={
                'serial_number': 'SN-PROC-002',
                'process_type': 'QI'
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is False
        assert 'ELEC' in data['missing_processes']


class TestProcessValidationBothComplete:
    """MECH + ELEC 모두 완료 → 공정 진행 가능"""

    def test_pi_both_complete(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token
    ):
        """
        MECH + ELEC 완료 → can_proceed=true, 알림 없음

        Expected:
        - Status 200
        - valid == true
        - missing_processes 빈 배열
        - alerts_created == 0
        """
        pi_worker_id = create_test_worker(
            email='pi_pass@test.com', password='Test123!',
            name='PI Pass Worker', role='PI'
        )

        create_test_product(
            qr_doc_id='DOC-PROC-003',
            serial_number='SN-PROC-003',
            model='GBWS-50',
            location_qr_id='LOC_C'
        )

        create_test_completion_status(
            serial_number='SN-PROC-003',
            mech_completed=True,
            elec_completed=True
        )

        token = get_auth_token(pi_worker_id, role='PI')
        response = client.post(
            '/api/app/validation/check-process',
            json={
                'serial_number': 'SN-PROC-003',
                'process_type': 'PI'
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is True
        assert data['missing_processes'] == []
        assert data['alerts_created'] == 0


class TestProcessValidationNonInspection:
    """비검사 공정 (MECH, ELEC, TM) 검증 불필요"""

    def test_mm_skips_validation(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token
    ):
        """
        MECH 공정 타입 → 검증 건너뜀, valid=true

        Expected:
        - Status 200
        - valid == true (검사 공정이 아니므로)
        """
        mm_worker_id = create_test_worker(
            email='mech_skip@test.com', password='Test123!',
            name='MM Skip Worker', role='MECH'
        )

        create_test_product(
            qr_doc_id='DOC-PROC-004',
            serial_number='SN-PROC-004',
            model='GBWS-50'
        )

        create_test_completion_status(serial_number='SN-PROC-004')

        token = get_auth_token(mm_worker_id, role='MECH')
        response = client.post(
            '/api/app/validation/check-process',
            json={
                'serial_number': 'SN-PROC-004',
                'process_type': 'MECH'
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is True


class TestProcessValidationNoProduct:
    """존재하지 않는 제품"""

    def test_product_not_found(
        self, client, create_test_worker, get_auth_token
    ):
        """
        존재하지 않는 serial_number → 404

        Expected:
        - Status 404
        - error == PRODUCT_NOT_FOUND
        """
        worker_id = create_test_worker(
            email='proc_404@test.com', password='Test123!',
            name='NotFound Worker', role='PI'
        )

        token = get_auth_token(worker_id, role='PI')
        response = client.post(
            '/api/app/validation/check-process',
            json={
                'serial_number': 'SN-NONEXISTENT',
                'process_type': 'PI'
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data['error'] == 'PRODUCT_NOT_FOUND'


class TestLocationQRCheck:
    """Location QR 미등록 검증"""

    def test_no_location_qr(
        self, client, create_test_worker, create_test_product,
        create_test_completion_status, get_auth_token
    ):
        """
        Location QR 미등록 제품 → location_qr_verified=false

        Expected:
        - Status 200
        - location_qr_verified == false
        """
        worker_id = create_test_worker(
            email='loc_check@test.com', password='Test123!',
            name='Location Check Worker', role='PI'
        )

        create_test_product(
            qr_doc_id='DOC-PROC-005',
            serial_number='SN-PROC-005',
            model='GBWS-50',
            location_qr_id=None
        )

        create_test_completion_status(
            serial_number='SN-PROC-005',
            mech_completed=True,
            elec_completed=True
        )

        token = get_auth_token(worker_id, role='PI')
        response = client.post(
            '/api/app/validation/check-process',
            json={
                'serial_number': 'SN-PROC-005',
                'process_type': 'PI'
            },
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['location_qr_verified'] is False


# ==================== FIX-PROCESS-VALIDATOR-TMS-MAPPING-20260428 (TC 7개) ====================
# Codex 라운드 1 합의: M1 fixture 정합 (옵션 D 격리 fixture) + A2 e2e 회귀 TC.
# 표준 함수 resolve_managers_for_category 의 partner-based / role-based 분기 검증.

from app.services.process_validator import resolve_managers_for_category


class TestResolveManagersForCategory:
    """본 Sprint 핵심 — process_validator.resolve_managers_for_category() 분기 검증."""

    def test_tms_gaia_partner(
        self, seed_test_workers, seed_test_products, seed_test_managers_for_partner
    ):
        """GAIA TMS task → module_outsourcing='TMS' 매니저 반환 (정규 케이스)."""
        managers = resolve_managers_for_category('TEST-GAIA-001', 'TMS')
        assert isinstance(managers, list)
        assert len(managers) > 0, (
            "TEST-GAIA-001.module_outsourcing='TMS' 협력사의 TMS(M)/TMS(E) "
            "매니저 worker_id 가 1명 이상 반환되어야 함"
        )

    def test_tms_dragon_module_none(
        self, seed_test_workers, seed_test_products, seed_test_managers_for_partner
    ):
        """DRAGON 회귀 — module_outsourcing=None 인 DRAGON 의 TMS 매핑 거동 명시.
        CLAUDE.md L1100 'DRAGON: tank_in_mech, 한 협력사가 탱크+MECH 일괄'.
        현재 구현 (`module_outsourcing` 매핑) 은 None 이면 빈 리스트 반환.
        DRAGON 정합성 검토는 후속 BACKLOG `BUG-DRAGON-TMS-PARTNER-MAPPING-20260428`."""
        managers = resolve_managers_for_category('TEST-DRAGON-001', 'TMS')
        assert isinstance(managers, list)
        # module_outsourcing=None → get_managers_by_partner 가 빈 리스트 반환

    def test_mech_partner(
        self, seed_test_workers, seed_test_products, seed_test_managers_for_partner
    ):
        """MECH task → mech_partner 매니저 반환 (4-22 HOTFIX 표준 패턴 회귀)."""
        managers = resolve_managers_for_category('TEST-GALLANT-001', 'MECH')
        assert len(managers) > 0, "mech_partner='BAT' 매니저 1명 이상"

    def test_elec_partner(
        self, seed_test_workers, seed_test_products, seed_test_managers_for_partner
    ):
        """ELEC task → elec_partner 매니저 반환 (회귀)."""
        managers = resolve_managers_for_category('TEST-GALLANT-001', 'ELEC')
        assert len(managers) > 0, "elec_partner='C&A' 매니저 1명 이상"

    def test_pi_role_fallback(self, seed_test_workers):
        """PI task → role 기반 fallback. role='PI' 매니저는 TEST_WORKERS 에 없음.
        반환 type 만 검증 (role-based 분기 진입 + silent skip 거동 보존)."""
        managers = resolve_managers_for_category('any-sn', 'PI')
        assert isinstance(managers, list)

    def test_unknown_returns_empty(self):
        """알 수 없는 category → role 기반 fallback → enum 없으면 빈 리스트.
        silent skip 거동 유지 (try/except PsycopgError → [])."""
        managers = resolve_managers_for_category('any-sn', 'UNKNOWN')
        assert managers == []


def _setup_tms_task_with_long_duration(db_conn, sn: str, duration_hours: int = 15) -> int:
    """e2e TC helper — TMS task_detail INSERT + duration > 14h 셋업.
    Returns: 생성된 task_detail.id

    db_conn 의 default cursor 는 tuple 반환 → row[0] 으로 id 추출.
    """
    from datetime import datetime, timedelta, timezone
    cur = db_conn.cursor()
    started = datetime.now(timezone.utc) - timedelta(hours=duration_hours)
    completed = datetime.now(timezone.utc)
    cur.execute(
        """
        INSERT INTO app_task_details (
            worker_id, serial_number, qr_doc_id, task_category, task_id,
            task_name, started_at, completed_at, duration_minutes, is_applicable
        )
        SELECT w.id, %s, %s, 'TMS', 'PRESSURE_TEST', '가압검사',
               %s, %s, %s, TRUE
          FROM workers w
         WHERE w.email = 'tmsm1@test.com'
         LIMIT 1
        RETURNING id
        """,
        (sn, f'DOC_{sn}', started, completed, duration_hours * 60),
    )
    row = cur.fetchone()
    db_conn.commit()
    cur.close()
    return row[0]


def test_duration_validator_tms_alert_creation_e2e(
    db_conn, seed_test_workers, seed_test_products, seed_test_managers_for_partner
):
    """⭐ Codex A2 — 원본 장애 경로 직접 재현.

    Before fix: get_managers_for_role('TMS') → enum 'TMS' 부재 → silent skip → alert 0건
    After fix:  resolve_managers_for_category(sn, 'TMS') → module_outsourcing 매니저 → alert 1+건

    helper-only TC 가 잡지 못하는 회귀 경로 (validate_duration → alert_logs INSERT) 보강.
    """
    from app.services.duration_validator import validate_duration

    # TMS task 셋업 — duration 15h (14h 초과 → DURATION_EXCEEDED trigger)
    task_detail_id = _setup_tms_task_with_long_duration(db_conn, sn='TEST-GAIA-001', duration_hours=15)

    try:
        result = validate_duration(task_detail_id)

        # 알람 생성 검증 (silent skip 회귀 방지)
        assert result['alerts_created'] > 0, (
            "validate_duration() 가 TMS task 의 module_outsourcing 매니저에게 알람을 생성해야 함. "
            "0 = silent skip 회귀 (FIX-PROCESS-VALIDATOR-TMS-MAPPING fix 효과 무효)"
        )

        # alert_logs 테이블 직접 검증 (target_worker_id 가 매니저인지)
        # default cursor → tuple 반환 → row[0]=alert_type, row[1]=target_worker_id
        cur = db_conn.cursor()
        cur.execute(
            """
            SELECT alert_type, target_worker_id
              FROM app_alert_logs
             WHERE serial_number = 'TEST-GAIA-001'
               AND alert_type = 'DURATION_EXCEEDED'
            """
        )
        rows = cur.fetchall()
        cur.close()
        assert len(rows) > 0, "DURATION_EXCEEDED alert 가 1건 이상 생성되어야 함"
        assert all(r[1] is not None for r in rows), (
            "target_worker_id (row[1]) 가 None 이면 broadcast 모드 — 본 Sprint 후엔 개별 매니저 INSERT"
        )
    finally:
        # cleanup
        cur = db_conn.cursor()
        cur.execute("DELETE FROM app_alert_logs WHERE serial_number = 'TEST-GAIA-001'")
        cur.execute("DELETE FROM app_task_details WHERE id = %s", (task_detail_id,))
        db_conn.commit()
        cur.close()
