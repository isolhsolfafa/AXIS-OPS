"""v2.18.2 pytest 신규 TC — MECH 체크리스트 qr_doc_id SINGLE 통일 검증.

Sprint: FIX-MECH-CHECKLIST-QR-DOC-ID-SINGLE-UNIFY-20260519
도입: 2026-05-19

배경 (BACKLOG L354 BUG-MECH-CHECKLIST-DUAL-MODEL-QR-DOC-ID-MISMATCH, 🔴 P0):
- DRAGON DUAL 모델 MECH 체크리스트가 영원히 100% 안 됨 → finalize 차단.
- 원인: INLET 8항목은 'DOC_{S/N}-L'/'-R' 분리 저장 / 나머지는 'DOC_{S/N}' SINGLE 저장 →
  check_mech_completion DUAL 분기가 -L/-R loop 전수 매칭 요구 → SINGLE 항목 영원히 mismatch.
- 옵션 D 채택: qr_doc_id 를 모델 무관 'DOC_{S/N}' SINGLE 한 가지로 통일.
  INLET L/R 구분은 master(item_name 'Left/Right #N' + 별도 master_id)가 담당.

검증 영역 (Codex 라운드 1 M-Q1+M-Q5 — 호출자 전수 커버):
- TC-MECH-QR-01: check_mech_completion — SINGLE qr_doc_id(DOC_{S/N}) 한 번만 사용 + model SELECT 제거
- TC-MECH-QR-02: 일부 미입력 → False (회귀)
- TC-MECH-QR-03: check_mech_completion 소스 — DUAL 분기/_is_report_dual_model 제거 확인
- TC-MECH-QR-04: check_tm_completion 소스 — TM DUAL -L/-R 분기 보존 (TM 미변경 보장)
- TC-MECH-QR-05: check_mech_completion_all — Phase 1+2 합산 게이트 (close 게이트 경로)
- TC-MECH-QR-06: task_service.check_category_close_eligible MECH 분기 — check_mech_completion_all 호출

Codex 라운드 1 M=2 (Q1 호출자 전수 TC + Q5 게이트 경로 TC) 반영 후 작성.
"""

import sys
import inspect
from pathlib import Path
from unittest.mock import patch, MagicMock

_backend_path = str(Path(__file__).parent.parent.parent / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

import pytest


# ═════════════════════════════════════════════════════════════════════════════
# TC-MECH-QR-01/02 — check_mech_completion SINGLE qr_doc_id
# ═════════════════════════════════════════════════════════════════════════════


def _make_completion_mocks(checked_count):
    """check_mech_completion 영역 cursor mock — count 쿼리 응답."""
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = {'checked': checked_count}
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    return mock_conn, mock_cur


def test_mech_qr_01_check_mech_completion_uses_single_qr_doc_id():
    """TC-MECH-QR-01: check_mech_completion — DOC_{S/N} SINGLE 한 번만 사용 + model SELECT 제거."""
    from app.services import checklist_service

    mock_conn, mock_cur = _make_completion_mocks(3)

    with patch.object(checklist_service, '_resolve_active_master_ids', return_value=[101, 102, 103]), \
         patch.object(checklist_service, 'get_db_connection', return_value=mock_conn), \
         patch.object(checklist_service, 'put_conn'):
        result = checklist_service.check_mech_completion('TEST-333', judgment_phase=1)

    assert result is True

    calls = mock_cur.execute.call_args_list
    # v2.18.2 — DUAL 판별용 model SELECT 제거 확인
    model_q = [c for c in calls if 'plan.product_info' in str(c.args[0])]
    assert len(model_q) == 0, "v2.18.2 — check_mech_completion 영역 model SELECT 제거 (DUAL 분기 폐기)"
    # count 쿼리 1회만 (-L/-R loop 없음)
    count_q = [c for c in calls if 'checklist.checklist_record' in str(c.args[0])]
    assert len(count_q) == 1, "MECH SINGLE qr_doc_id — count 쿼리 1회만 (loop 없음)"
    # qr_doc_id param = DOC_{S/N} (접미사 없음)
    params = count_q[0].args[1]
    assert params['qr_doc_id'] == 'DOC_TEST-333', \
        f"qr_doc_id 는 DOC_{{S/N}} SINGLE 이어야 함 (-L/-R 없음), got {params['qr_doc_id']}"
    assert not params['qr_doc_id'].endswith('-L'), "-L 접미사 없어야 함"
    assert not params['qr_doc_id'].endswith('-R'), "-R 접미사 없어야 함"


def test_mech_qr_02_partial_records_returns_false():
    """TC-MECH-QR-02: active_ids 일부만 입력 → check_mech_completion False (회귀)."""
    from app.services import checklist_service

    mock_conn, mock_cur = _make_completion_mocks(2)  # 3개 중 2개만 입력

    with patch.object(checklist_service, '_resolve_active_master_ids', return_value=[101, 102, 103]), \
         patch.object(checklist_service, 'get_db_connection', return_value=mock_conn), \
         patch.object(checklist_service, 'put_conn'):
        result = checklist_service.check_mech_completion('TEST-333', judgment_phase=1)

    assert result is False, "active_ids 3개 중 2개만 입력 → False"


def test_mech_qr_02b_no_active_ids_returns_false():
    """TC-MECH-QR-02b: active_ids 없음 (제품 미존재 등) → False (early return)."""
    from app.services import checklist_service

    with patch.object(checklist_service, '_resolve_active_master_ids', return_value=[]):
        result = checklist_service.check_mech_completion('NO-SUCH-SN', judgment_phase=1)

    assert result is False, "active_ids 없으면 False"


# ═════════════════════════════════════════════════════════════════════════════
# TC-MECH-QR-03/04 — 소스 검증 (MECH DUAL 제거 / TM DUAL 보존)
# ═════════════════════════════════════════════════════════════════════════════


def test_mech_qr_03_check_mech_completion_no_dual_branch():
    """TC-MECH-QR-03: check_mech_completion 소스 — DUAL 분기 + _is_report_dual_model 제거 확인."""
    from app.services import checklist_service

    src = inspect.getsource(checklist_service.check_mech_completion)
    assert '_is_report_dual_model' not in src, \
        "v2.18.2 — check_mech_completion 영역 _is_report_dual_model 호출 제거 (MECH DUAL 분기 폐기)"
    # 실제 코드 라인만 검사 (docstring 제외) — -L/-R hint 호출 제거 확인
    code_lines = [ln for ln in src.splitlines()
                  if not ln.strip().startswith('#') and not ln.strip().startswith('"')]
    code_only = '\n'.join(code_lines)
    assert "_normalize_qr_doc_id(serial_number, 'L')" not in code_only, \
        "v2.18.2 — check_mech_completion 영역 -L hint 호출 제거"
    assert "_normalize_qr_doc_id(serial_number, 'R')" not in code_only, \
        "v2.18.2 — check_mech_completion 영역 -R hint 호출 제거"
    assert 'plan.product_info' not in code_only, \
        "v2.18.2 — check_mech_completion 영역 model SELECT 제거"


def test_mech_qr_04_tm_completion_keeps_dual_branch():
    """TC-MECH-QR-04: check_tm_completion 소스 — TM DUAL -L/-R 분기 보존 (TM 미변경 보장)."""
    from app.services import checklist_service

    src = inspect.getsource(checklist_service.check_tm_completion)
    assert '_is_report_dual_model' in src, \
        "check_tm_completion 영역 _is_report_dual_model 보존 — TM dual tank 정상 사용 (D 범위 제외)"
    assert "-L'" in src and "-R'" in src, \
        "check_tm_completion 영역 -L/-R qr_doc_id 보존 — TM 미변경"


# ═════════════════════════════════════════════════════════════════════════════
# TC-MECH-QR-05/06 — close 게이트 경로 (Codex M-Q5)
# ═════════════════════════════════════════════════════════════════════════════


def test_mech_qr_05_check_mech_completion_all_phase_sum():
    """TC-MECH-QR-05: check_mech_completion_all — Phase 1+2 둘 다 True 일 때만 True."""
    from app.services import checklist_service

    # Phase 1+2 둘 다 통과
    with patch.object(checklist_service, 'check_mech_completion') as mock_check:
        mock_check.side_effect = [True, True]
        assert checklist_service.check_mech_completion_all('TEST-333') is True

    # Phase 1 통과 + Phase 2 미완료 → False
    with patch.object(checklist_service, 'check_mech_completion') as mock_check:
        mock_check.side_effect = [True, False]
        assert checklist_service.check_mech_completion_all('TEST-333') is False

    # Phase 1 미완료 → 즉시 False (short-circuit)
    with patch.object(checklist_service, 'check_mech_completion') as mock_check:
        mock_check.side_effect = [False]
        assert checklist_service.check_mech_completion_all('TEST-333') is False


def test_mech_qr_06_close_gate_uses_check_mech_completion_all():
    """TC-MECH-QR-06: task_service.check_category_close_eligible MECH 분기 — check_mech_completion_all 호출."""
    from app.services import task_service

    src = inspect.getsource(task_service.check_category_close_eligible)
    assert 'check_mech_completion_all' in src, \
        "MECH close 게이트 = check_mech_completion_all (Phase 1+2 합산) — qr_doc_id 통일 후에도 정합"
