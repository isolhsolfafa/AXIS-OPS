"""
Sprint 63-BE MECH 체크리스트 테스트 (21 TC)

분류:
[A] _normalize_qr_doc_id() pure function unit (6 TC)
[B] scope_rule + phase1 _resolve_active_master_ids (7 TC)
[C] trigger_task_id 매핑 master 데이터 검증 (3 TC)
[D] seed count by scope_rule (1 TC)
[E] rename gate _check_tm_completion = 0 (1 TC)
[F] phase=2 (c)안 1차 record 미강제 (2 TC)
[G] WebSocket emit + alert INSERT (1 TC)

운영 DB 동일 seed (migration 051 + 051a 자동 적용 = 73 항목 / 20 그룹).
"""

import sys
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest


_PREFIX = 'SN-SP63-'


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _insert_product(db_conn, sn, model='GAIA-I', mech_partner='FNI',
                    elec_partner='P&S', module_outsourcing='TMS'):
    cur = db_conn.cursor()
    cur.execute("""
        INSERT INTO plan.product_info
            (serial_number, model, mech_partner, elec_partner, module_outsourcing, prod_date)
        VALUES (%s, %s, %s, %s, %s, NOW()::date)
        ON CONFLICT (serial_number) DO NOTHING
    """, (sn, model, mech_partner, elec_partner, module_outsourcing))
    cur.execute("""
        INSERT INTO public.qr_registry (qr_doc_id, serial_number, status)
        VALUES (%s, %s, 'active') ON CONFLICT (qr_doc_id) DO NOTHING
    """, (f'DOC_{sn}', sn))
    db_conn.commit()
    cur.close()


def _cleanup(db_conn, sn):
    cur = db_conn.cursor()
    try:
        cur.execute("DELETE FROM app_alert_logs WHERE serial_number=%s", (sn,))
        cur.execute("DELETE FROM checklist.checklist_record WHERE serial_number=%s", (sn,))
        cur.execute("DELETE FROM completion_status WHERE serial_number=%s", (sn,))
        cur.execute("DELETE FROM qr_registry WHERE serial_number=%s", (sn,))
        cur.execute("DELETE FROM plan.product_info WHERE serial_number=%s", (sn,))
        db_conn.commit()
    except Exception:
        db_conn.rollback()
    finally:
        cur.close()


def _seed_record(db_conn, sn, master_id, judgment_phase, qr_doc_id,
                 check_result='PASS', worker_id=None):
    """checklist_record 직접 삽입 (UPSERT 우회 — phase=2 (c)안 검증용)"""
    cur = db_conn.cursor()
    cur.execute("""
        INSERT INTO checklist.checklist_record
            (serial_number, master_id, judgment_phase, check_result,
             checked_by, checked_at, qr_doc_id, updated_at)
        VALUES (%s, %s, %s, %s, %s, NOW(), %s, NOW())
        ON CONFLICT (serial_number, master_id, judgment_phase, qr_doc_id) DO UPDATE
        SET check_result = EXCLUDED.check_result,
            updated_at = NOW()
    """, (sn, master_id, judgment_phase, check_result, worker_id, qr_doc_id))
    db_conn.commit()
    cur.close()


# ═════════════════════════════════════════════════════════════════════════════
# [A] _normalize_qr_doc_id() pure function unit tests (6 TC)
# ═════════════════════════════════════════════════════════════════════════════

class TestNormalizeQrDocId:
    """Pure function — DB 없이 빠른 검증."""

    def test_qr_doc_id_normalization_single(self):
        """TC-A-01: SINGLE 모델 — hint 없으면 'DOC_{SN}' 반환."""
        from app.services.checklist_service import _normalize_qr_doc_id
        assert _normalize_qr_doc_id('GBWS-6905') == 'DOC_GBWS-6905'
        # idempotent — 같은 input 반복 호출해도 동일 결과
        assert _normalize_qr_doc_id('GBWS-6905') == _normalize_qr_doc_id('GBWS-6905')

    def test_qr_doc_id_normalization_dual(self):
        """TC-A-02: DUAL 모델 — hint='L'/'R' suffix → 'DOC_{SN}-L'/'-R'."""
        from app.services.checklist_service import _normalize_qr_doc_id
        assert _normalize_qr_doc_id('GBWS-7043', 'L') == 'DOC_GBWS-7043-L'
        assert _normalize_qr_doc_id('GBWS-7043', 'R') == 'DOC_GBWS-7043-R'
        # 소문자 hint 도 대문자로 정규화
        assert _normalize_qr_doc_id('GBWS-7043', 'l') == 'DOC_GBWS-7043-L'
        assert _normalize_qr_doc_id('GBWS-7043', 'r') == 'DOC_GBWS-7043-R'

    def test_normalize_qr_doc_id_hint_none(self):
        """TC-A-03: hint=None → 기본 SINGLE 'DOC_{SN}'."""
        from app.services.checklist_service import _normalize_qr_doc_id
        assert _normalize_qr_doc_id('GBWS-6905', None) == 'DOC_GBWS-6905'

    def test_normalize_qr_doc_id_blank_hint(self):
        """TC-A-04: hint='' 또는 공백 → 기본 SINGLE fallback."""
        from app.services.checklist_service import _normalize_qr_doc_id
        assert _normalize_qr_doc_id('GBWS-6905', '') == 'DOC_GBWS-6905'
        assert _normalize_qr_doc_id('GBWS-6905', '   ') == 'DOC_GBWS-6905'
        assert _normalize_qr_doc_id('GBWS-6905', '\t') == 'DOC_GBWS-6905'

    def test_normalize_qr_doc_id_mixed_case_full_id(self):
        """TC-A-05: hint=full id (이미 정규화 형태) → idempotent 보장."""
        from app.services.checklist_service import _normalize_qr_doc_id
        # 이미 'DOC_{SN}' 으로 시작하면 그대로 (대소문자 무관)
        assert _normalize_qr_doc_id('GBWS-7043', 'DOC_GBWS-7043-L') == 'DOC_GBWS-7043-L'
        assert _normalize_qr_doc_id('GBWS-7043', 'DOC_GBWS-7043-R') == 'DOC_GBWS-7043-R'
        assert _normalize_qr_doc_id('GBWS-6905', 'DOC_GBWS-6905') == 'DOC_GBWS-6905'

    def test_normalize_qr_doc_id_empty_serial(self):
        """TC-A-06: serial='' 또는 공백 → '' 반환 (호출자 책임 분리)."""
        from app.services.checklist_service import _normalize_qr_doc_id
        assert _normalize_qr_doc_id('') == ''
        assert _normalize_qr_doc_id('   ') == ''
        assert _normalize_qr_doc_id('', 'L') == ''


# ═════════════════════════════════════════════════════════════════════════════
# [B] scope_rule + phase1_applicable _resolve_active_master_ids (7 TC)
# ═════════════════════════════════════════════════════════════════════════════

class TestScopeRule:

    @pytest.fixture(autouse=True)
    def setup(self, db_conn, seed_test_data):
        self.db_conn = db_conn
        self.created_sns = []
        yield
        for sn in self.created_sns:
            _cleanup(db_conn, sn)

    def _create(self, sn_suffix, model, mech='FNI'):
        sn = f'{_PREFIX}{sn_suffix}'
        _insert_product(self.db_conn, sn, model=model, mech_partner=mech)
        self.created_sns.append(sn)
        return sn

    def test_scope_rule_all_matches_any_model(self):
        """TC-B-01: scope='all' 항목은 모든 모델에서 활성. GAIA, DRAGON, GALLANT 모두 ≥ 56개."""
        from app.services.checklist_service import _resolve_active_master_ids

        # judgment_phase=2 (전체) — phase1_applicable 무관
        gaia_sn = self._create('SCOPE-ALL-GAIA', 'GAIA-I')
        dragon_sn = self._create('SCOPE-ALL-DRAGON', 'DRAGON-V')
        gallant_sn = self._create('SCOPE-ALL-GALLANT', 'GALLANT-50')

        gaia_ids = _resolve_active_master_ids(gaia_sn, judgment_phase=2)
        dragon_ids = _resolve_active_master_ids(dragon_sn, judgment_phase=2)
        gallant_ids = _resolve_active_master_ids(gallant_sn, judgment_phase=2)

        # 모두 56 (all) 이상은 있어야 (tank_in_mech 9 / DRAGON 8 추가는 모델별 다름)
        assert len(gaia_ids) >= 56, f"GAIA active count={len(gaia_ids)} (≥56 expected)"
        assert len(dragon_ids) >= 56
        assert len(gallant_ids) >= 56

    def test_scope_rule_tank_in_mech_matches_dragon(self):
        """TC-B-02: scope='tank_in_mech' 항목 9개 (Exhaust 4 + TANK 3 + Quenching 2) → DRAGON 활성."""
        from app.services.checklist_service import _resolve_active_master_ids

        dragon_sn = self._create('TANK-DRAGON', 'DRAGON-V')
        dragon_ids = _resolve_active_master_ids(dragon_sn, judgment_phase=2)

        # tank_in_mech 9개가 active list 안에 포함됐는지 확인
        cur = self.db_conn.cursor()
        cur.execute("""
            SELECT id FROM checklist.checklist_master
            WHERE category='MECH' AND scope_rule='tank_in_mech' AND is_active=TRUE
        """)
        tank_ids = [r[0] for r in cur.fetchall()]
        cur.close()
        assert len(tank_ids) == 9, f"tank_in_mech master count={len(tank_ids)} (9 expected)"

        for tid in tank_ids:
            assert tid in dragon_ids, f"DRAGON 에서 tank_in_mech master {tid} 비활성"

    def test_scope_rule_tank_in_mech_matches_gallant(self):
        """TC-B-03: scope='tank_in_mech' → GALLANT (tank_in_mech=TRUE) 도 활성."""
        from app.services.checklist_service import _resolve_active_master_ids

        gallant_sn = self._create('TANK-GALLANT', 'GALLANT-50')
        gallant_ids = _resolve_active_master_ids(gallant_sn, judgment_phase=2)

        cur = self.db_conn.cursor()
        cur.execute("""
            SELECT id FROM checklist.checklist_master
            WHERE category='MECH' AND scope_rule='tank_in_mech' AND is_active=TRUE
        """)
        tank_ids = [r[0] for r in cur.fetchall()]
        cur.close()

        for tid in tank_ids:
            assert tid in gallant_ids, f"GALLANT 에서 tank_in_mech master {tid} 비활성"

    def test_scope_rule_tank_in_mech_matches_sws(self):
        """TC-B-04: scope='tank_in_mech' → SWS (tank_in_mech=TRUE) 도 활성."""
        from app.services.checklist_service import _resolve_active_master_ids

        sws_sn = self._create('TANK-SWS', 'SWS-100')
        sws_ids = _resolve_active_master_ids(sws_sn, judgment_phase=2)

        cur = self.db_conn.cursor()
        cur.execute("""
            SELECT id FROM checklist.checklist_master
            WHERE category='MECH' AND scope_rule='tank_in_mech' AND is_active=TRUE
        """)
        tank_ids = [r[0] for r in cur.fetchall()]
        cur.close()

        for tid in tank_ids:
            assert tid in sws_ids, f"SWS 에서 tank_in_mech master {tid} 비활성"

    def test_scope_rule_tank_in_mech_excludes_gaia(self):
        """TC-B-05: scope='tank_in_mech' → GAIA (tank_in_mech=FALSE) 비활성."""
        from app.services.checklist_service import _resolve_active_master_ids

        gaia_sn = self._create('TANK-GAIA-EXCL', 'GAIA-I')
        gaia_ids = _resolve_active_master_ids(gaia_sn, judgment_phase=2)

        cur = self.db_conn.cursor()
        cur.execute("""
            SELECT id FROM checklist.checklist_master
            WHERE category='MECH' AND scope_rule='tank_in_mech' AND is_active=TRUE
        """)
        tank_ids = [r[0] for r in cur.fetchall()]
        cur.close()

        for tid in tank_ids:
            assert tid not in gaia_ids, f"GAIA 에 tank_in_mech master {tid} 활성 (오류)"

    def test_scope_rule_dragon_only_matches_dragon(self):
        """TC-B-06: scope='DRAGON' (INLET S/N L/R 8개) → DRAGON 만 활성, GALLANT/SWS 도 비활성."""
        from app.services.checklist_service import _resolve_active_master_ids

        dragon_sn = self._create('DRAGON-ONLY', 'DRAGON-V')
        gallant_sn = self._create('DRAGON-EXCL-GAL', 'GALLANT-50')
        sws_sn = self._create('DRAGON-EXCL-SWS', 'SWS-100')
        gaia_sn = self._create('DRAGON-EXCL-GAIA', 'GAIA-I')

        dragon_ids = _resolve_active_master_ids(dragon_sn, judgment_phase=2)
        gallant_ids = _resolve_active_master_ids(gallant_sn, judgment_phase=2)
        sws_ids = _resolve_active_master_ids(sws_sn, judgment_phase=2)
        gaia_ids = _resolve_active_master_ids(gaia_sn, judgment_phase=2)

        cur = self.db_conn.cursor()
        cur.execute("""
            SELECT id FROM checklist.checklist_master
            WHERE category='MECH' AND scope_rule='DRAGON' AND is_active=TRUE
        """)
        d_ids = [r[0] for r in cur.fetchall()]
        cur.close()
        assert len(d_ids) == 8, f"DRAGON-only master count={len(d_ids)} (8 expected — INLET S/N L/R)"

        for did in d_ids:
            assert did in dragon_ids, f"DRAGON 에 DRAGON-only master {did} 비활성"
            assert did not in gallant_ids, f"GALLANT 에 DRAGON-only master {did} 활성 (오류)"
            assert did not in sws_ids, f"SWS 에 DRAGON-only master {did} 활성 (오류)"
            assert did not in gaia_ids, f"GAIA 에 DRAGON-only master {did} 활성 (오류)"

    def test_phase1_applicable_19_items_only(self):
        """TC-B-07: judgment_phase=1 + DRAGON → phase1_applicable=TRUE 19개만 활성."""
        from app.services.checklist_service import _resolve_active_master_ids

        dragon_sn = self._create('PHASE1-19', 'DRAGON-V')

        ids_phase1 = _resolve_active_master_ids(dragon_sn, judgment_phase=1)
        ids_phase2 = _resolve_active_master_ids(dragon_sn, judgment_phase=2)

        # phase1: phase1_applicable=TRUE 만
        # DRAGON 의 phase1_applicable=TRUE 항목 = INLET S/N 8 (DRAGON scope) +
        # GN2/CDA Speed 4 + MFC/FS 7 = 19 (all + DRAGON 둘 다 가능)
        cur = self.db_conn.cursor()
        cur.execute("""
            SELECT COUNT(*) AS cnt FROM checklist.checklist_master
            WHERE category='MECH' AND is_active=TRUE
              AND phase1_applicable=TRUE
              AND (scope_rule='all' OR scope_rule='tank_in_mech' OR scope_rule='DRAGON')
        """)
        total_phase1_master = cur.fetchone()[0]
        cur.close()

        # phase=1 active 는 master 의 phase1=TRUE 갯수와 같거나 적어야 (DRAGON 모델만의 scope filter)
        assert len(ids_phase1) <= total_phase1_master
        # phase=2 는 모든 항목 (phase1 무관) → phase=1 보다 많거나 같아야
        assert len(ids_phase2) >= len(ids_phase1)
        # phase=1 19개 (DRAGON 의 모든 phase1=TRUE — INLET 8 + Speed 4 + MFC/FS 7)
        assert len(ids_phase1) == 19, f"DRAGON phase=1 active={len(ids_phase1)} (19 expected)"


# ═════════════════════════════════════════════════════════════════════════════
# [C] trigger_task_id 매핑 (3 TC)
# ═════════════════════════════════════════════════════════════════════════════

class TestTriggerTaskId:

    @pytest.fixture(autouse=True)
    def setup(self, db_conn, seed_test_data):
        self.db_conn = db_conn

    def test_trigger_task_id_util_line_1_for_speed(self):
        """TC-C-01: UTIL_LINE_1 trigger → Speed Controller 4 항목 (GN2 2 + CDA 2)."""
        cur = self.db_conn.cursor()
        cur.execute("""
            SELECT COUNT(*) AS cnt FROM checklist.checklist_master
            WHERE category='MECH' AND trigger_task_id='UTIL_LINE_1' AND is_active=TRUE
        """)
        cnt = cur.fetchone()[0]
        cur.close()
        assert cnt == 4, f"UTIL_LINE_1 trigger master count={cnt} (4 expected — Speed Controller GN2 2 + CDA 2)"

    def test_trigger_task_id_util_line_2_for_mfc_fs(self):
        """TC-C-02: UTIL_LINE_2 trigger → MFC 4 + Flow Sensor 3 = 7 항목."""
        cur = self.db_conn.cursor()
        cur.execute("""
            SELECT COUNT(*) AS cnt FROM checklist.checklist_master
            WHERE category='MECH' AND trigger_task_id='UTIL_LINE_2' AND is_active=TRUE
        """)
        cnt = cur.fetchone()[0]
        cur.close()
        assert cnt == 7, f"UTIL_LINE_2 trigger master count={cnt} (7 expected — MFC 4 + FS 3)"

    def test_trigger_task_id_waste_gas_line_2_for_inlet_sn(self):
        """TC-C-03: WASTE_GAS_LINE_2 trigger → INLET S/N L/R 8 항목 (v2 분리)."""
        cur = self.db_conn.cursor()
        cur.execute("""
            SELECT COUNT(*) AS cnt FROM checklist.checklist_master
            WHERE category='MECH' AND trigger_task_id='WASTE_GAS_LINE_2' AND is_active=TRUE
        """)
        cnt = cur.fetchone()[0]
        cur.close()
        assert cnt == 8, f"WASTE_GAS_LINE_2 trigger master count={cnt} (8 expected — INLET S/N L/R 8 분리)"


# ═════════════════════════════════════════════════════════════════════════════
# [D] seed count by scope_rule (1 TC)
# ═════════════════════════════════════════════════════════════════════════════

class TestSeedCount:

    def test_seed_count_by_scope_rule(self, db_conn, seed_test_data):
        """TC-D-01: 51a 실파일 seed 분포 자동 검증 — all=56 / tank_in_mech=9 / DRAGON=8 = 73."""
        cur = db_conn.cursor()
        cur.execute("""
            SELECT scope_rule, COUNT(*) AS cnt FROM checklist.checklist_master
            WHERE category='MECH' AND is_active=TRUE
            GROUP BY scope_rule
        """)
        rows = {r[0]: r[1] for r in cur.fetchall()}

        # 합계 확인
        cur.execute("""
            SELECT COUNT(*) AS cnt FROM checklist.checklist_master
            WHERE category='MECH' AND is_active=TRUE
        """)
        total = cur.fetchone()[0]
        cur.close()

        assert rows.get('all') == 56, f"scope='all' count={rows.get('all')} (56 expected)"
        assert rows.get('tank_in_mech') == 9, f"scope='tank_in_mech' count={rows.get('tank_in_mech')} (9 expected)"
        assert rows.get('DRAGON') == 8, f"scope='DRAGON' count={rows.get('DRAGON')} (8 expected — v2 INLET 8개 분리)"
        assert total == 73, f"total MECH master count={total} (73 expected)"


# ═════════════════════════════════════════════════════════════════════════════
# [D2] R2-1 patch — get_mech_checklist 응답 tank_in_mech 키 회귀 검증 (3 TC)
# ═════════════════════════════════════════════════════════════════════════════

class TestR21TankInMechResponse:
    """R2-1 patch (Codex 라운드 2): get_mech_checklist() 응답에 tank_in_mech bool 추가.
    M-R2-D 정정 — FE _isScopeMatched 활용 정합성 검증."""

    @pytest.fixture(autouse=True)
    def setup(self, db_conn, seed_test_data):
        self.db_conn = db_conn
        self.created_sns = []
        yield
        for sn in self.created_sns:
            _cleanup(db_conn, sn)

    def _create_and_get(self, sn_suffix, model):
        from app.services.checklist_service import get_mech_checklist
        sn = f'{_PREFIX}R21-{sn_suffix}'
        _insert_product(self.db_conn, sn, model=model)
        self.created_sns.append(sn)
        return get_mech_checklist(sn, judgment_phase=1)

    def test_get_mech_checklist_response_has_tank_in_mech_key(self):
        """TC-D2-01: 모든 모델 응답에 tank_in_mech 키 존재 (additive contract)."""
        for model in ['GAIA-I', 'DRAGON-V', 'GALLANT-50', 'SWS-100', 'MITHAS-X']:
            response = self._create_and_get(f'KEY-{model}', model)
            assert 'tank_in_mech' in response, \
                f"model={model} 응답에 'tank_in_mech' 키 부재 (R2-1 patch 미적용)"
            assert isinstance(response['tank_in_mech'], bool), \
                f"model={model} tank_in_mech 타입 != bool ({type(response['tank_in_mech'])})"

    def test_get_mech_checklist_tank_in_mech_true_for_dragon_gallant_sws(self):
        """TC-D2-02: tank_in_mech=TRUE 모델 — DRAGON / GALLANT / SWS."""
        for model in ['DRAGON-V', 'GALLANT-50', 'SWS-100']:
            response = self._create_and_get(f'TIM-T-{model}', model)
            assert response['tank_in_mech'] is True, \
                f"model={model} tank_in_mech={response['tank_in_mech']} (TRUE expected — model_config flip)"

    def test_get_mech_checklist_tank_in_mech_false_for_gaia_mithas_sds(self):
        """TC-D2-03: tank_in_mech=FALSE 모델 — GAIA / MITHAS / SDS."""
        for model in ['GAIA-I', 'MITHAS-X', 'SDS-Y']:
            response = self._create_and_get(f'TIM-F-{model}', model)
            assert response['tank_in_mech'] is False, \
                f"model={model} tank_in_mech={response['tank_in_mech']} (FALSE expected)"


# ═════════════════════════════════════════════════════════════════════════════
# [E] rename gate _check_tm_completion = 0 (1 TC)
# ═════════════════════════════════════════════════════════════════════════════

class TestRenameGate:

    def test_tm_completion_rename_no_legacy_caller(self):
        """TC-E-01: grep "_check_tm_completion" *.py → 0 hits 보장 (자기 self-match 제외).

        rename 회귀 자동 차단 — 누군가 _check_tm_completion 다시 추가 시 즉시 실패.
        .pyc 와 본 테스트 파일 자체 (검증 목적 string 포함) 는 제외.
        """
        repo_root = Path(__file__).parent.parent.parent
        self_filename = Path(__file__).name  # 'test_mech_checklist.py'

        # grep --include='*.py' 로 .pyc 제외, *.py 만 검색
        result = subprocess.run(
            ['grep', '-rn', '--include=*.py', '_check_tm_completion',
             'backend/', 'tests/'],
            cwd=repo_root, capture_output=True, text=True, timeout=10
        )

        # 자기 self-match (test_mech_checklist.py 안의 검증 문자열) 제외
        matches = [
            line for line in result.stdout.splitlines()
            if line.strip() and self_filename not in line
        ]

        if matches:
            pytest.fail(
                f"_check_tm_completion legacy caller 발견 ({len(matches)} hits):\n"
                + "\n".join(matches[:10])
                + f"\n→ Sprint 63-BE Step 5 rename 회귀. check_tm_completion 으로 정정 필요."
            )


# ═════════════════════════════════════════════════════════════════════════════
# [F] phase=2 (c)안 검증 — 1차 record 강제 안 함 (2 TC)
# ═════════════════════════════════════════════════════════════════════════════

class TestPhase2CCase:

    @pytest.fixture(autouse=True)
    def setup(self, db_conn, seed_test_data, create_test_worker):
        self.db_conn = db_conn
        self.worker_id = create_test_worker(
            email='sp63_phase2@test.axisos.com', password='Test1234!',
            name='SP63 Phase2', role='MECH', company='FNI'
        )
        self.sn = f'{_PREFIX}PHASE2'
        # GAIA-I 사용 (tank_in_mech=FALSE, DRAGON-only 항목 비활성 → 단순 케이스)
        _insert_product(db_conn, self.sn, model='GAIA-I')
        yield
        _cleanup(db_conn, self.sn)

    def _get_active_ids(self, phase=2):
        from app.services.checklist_service import _resolve_active_master_ids
        return _resolve_active_master_ids(self.sn, judgment_phase=phase)

    def test_phase2_completion_when_phase1_missing(self):
        """TC-F-01: 1차 record 0건 + 2차 record 모두 채움 → check_mech_completion(phase=2)=True ((c)안 핵심).

        시나리오: 작업자가 phase=1 미입력. 관리자가 phase=2 record 만 입력.
        → 1차 record 강제 안 함, phase=2 만으로 cover 가능.
        """
        from app.services.checklist_service import check_mech_completion

        active_ids_2 = self._get_active_ids(phase=2)
        assert len(active_ids_2) > 0, "phase=2 active master 0건 (seed 누락)"

        qr = f'DOC_{self.sn}'

        # phase=1 record 0건 유지 (의도적 미입력)
        # phase=2 record 모두 채움 — (c)안 동작 검증
        for mid in active_ids_2:
            _seed_record(self.db_conn, self.sn, mid,
                         judgment_phase=2, qr_doc_id=qr,
                         check_result='PASS', worker_id=self.worker_id)

        # phase=1 미입력 → phase=1 완료 False
        assert check_mech_completion(self.sn, judgment_phase=1) is False, \
            "phase=1 record 0건인데 phase=1 완료 True (오류)"
        # phase=2 만 채워도 phase=2 완료 True ((c)안)
        assert check_mech_completion(self.sn, judgment_phase=2) is True, \
            "phase=2 record 채웠는데 완료 False ((c)안 위반)"

    def test_phase2_completion_when_both_filled(self):
        """TC-F-02: phase=1 + phase=2 둘 다 입력 시 양쪽 모두 완료."""
        from app.services.checklist_service import check_mech_completion

        active_ids_1 = self._get_active_ids(phase=1)
        active_ids_2 = self._get_active_ids(phase=2)
        qr = f'DOC_{self.sn}'

        # phase=1 채움
        for mid in active_ids_1:
            _seed_record(self.db_conn, self.sn, mid, 1, qr, 'PASS', self.worker_id)
        # phase=2 채움
        for mid in active_ids_2:
            _seed_record(self.db_conn, self.sn, mid, 2, qr, 'PASS', self.worker_id)

        assert check_mech_completion(self.sn, judgment_phase=1) is True, \
            "phase=1 모두 채웠는데 완료 False"
        assert check_mech_completion(self.sn, judgment_phase=2) is True, \
            "phase=2 모두 채웠는데 완료 False"


# ═════════════════════════════════════════════════════════════════════════════
# [G] WebSocket emit + alert INSERT (1 TC)
# ═════════════════════════════════════════════════════════════════════════════

class TestAlertEmit:

    @pytest.fixture(autouse=True)
    def setup(self, db_conn, seed_test_data, create_test_worker):
        self.db_conn = db_conn
        self.worker_id = create_test_worker(
            email='sp63_alert@test.axisos.com', password='Test1234!',
            name='SP63 Alert', role='MECH', company='FNI'
        )
        self.sn = f'{_PREFIX}ALERT'
        _insert_product(db_conn, self.sn, model='GAIA-I')
        yield
        _cleanup(db_conn, self.sn)

    def test_trigger_mech_checklist_alert_websocket_emit(self):
        """TC-G-01: 3개 trigger task (UTIL_LINE_1/UTIL_LINE_2/WASTE_GAS_LINE_2) 시작 시
        alert_type='CHECKLIST_MECH_READY' INSERT + create_alert 호출 검증."""
        from app.services.task_service import TaskService

        # task 객체 mock
        class _MockTask:
            def __init__(self, task_id, sn, qr, name):
                self.id = 9999
                self.task_id = task_id
                self.task_category = 'MECH'
                self.serial_number = sn
                self.qr_doc_id = qr
                self.task_name = name

        ts = TaskService()
        qr = f'DOC_{self.sn}'

        # create_alert 호출 카운트 확인
        with patch('app.models.alert_log.create_alert') as mock_create:
            mock_create.return_value = 12345  # alert_id

            # 3개 trigger task 모두 호출
            for tid, tname in [
                ('UTIL_LINE_1', 'Util LINE 1'),
                ('UTIL_LINE_2', 'Util LINE 2'),
                ('WASTE_GAS_LINE_2', 'Waste Gas LINE 2'),
            ]:
                task = _MockTask(tid, self.sn, qr, tname)
                ts._trigger_mech_checklist_alert(task, self.worker_id)

            # 3 task 모두 매칭 master 1+ 존재 → create_alert 3회 호출
            assert mock_create.call_count == 3, \
                f"create_alert 호출 횟수={mock_create.call_count} (3 expected)"

            # 호출 인자 검증 — alert_type='CHECKLIST_MECH_READY'
            for call in mock_create.call_args_list:
                kwargs = call.kwargs
                assert kwargs.get('alert_type') == 'CHECKLIST_MECH_READY'
                assert kwargs.get('serial_number') == self.sn
                assert kwargs.get('target_worker_id') == self.worker_id
                assert kwargs.get('triggered_by_worker_id') == self.worker_id

        # 비-trigger task (예: TANK_DOCKING) 은 발화 안 함
        with patch('app.models.alert_log.create_alert') as mock_create:
            task = _MockTask('TANK_DOCKING', self.sn, qr, 'Tank Docking')
            ts._trigger_mech_checklist_alert(task, self.worker_id)
            assert mock_create.call_count == 0, \
                "TANK_DOCKING 은 trigger 미매칭인데 create_alert 호출됨 (오류)"
