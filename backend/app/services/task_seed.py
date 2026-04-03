"""
Task Seed 서비스
Sprint 6 Phase B: Task 템플릿 15개(MECH 7 + ELEC 6 + TMS 2) 정의 + 제품별 초기화
Sprint 11: PI/QI/SI 템플릿 4개 추가 → 총 19개

CLAUDE.md Task Seed 데이터 기준:
  MECH 7개, ELEC 6개, TMS 2개 = 기존 15개
  PI 2개, QI 1개, SI 1개 = 추가 4개 → 합계 19개
  model_config 기반 분기: GAIA(has_docking), DRAGON(tank_in_mech), 기타
  admin_settings.heating_jacket_enabled 로 HEATING_JACKET 제어
  PI/QI/SI 는 모든 모델에 항상 생성 (is_applicable=True)

Sprint 31A: 다모델 지원
  DUAL 모델: TMS 태스크를 L/R qr_doc_id별 생성
  iVAS: always_dual=True → DUAL 키워드 없이도 L/R
  DRAGON: MECH에 TANK_MODULE + PRESSURE_TEST 추가 (PI 불필요)
  SWS/GALLANT: MECH에 TANK_MODULE만 추가 (가압검사는 GST PI 담당)
  SWS JP line: product_info.line='JP'이면 PI_LNG_UTIL 추가 활성
  PI 범위: model_config.pi_lng_util, pi_chamber 기반 분기
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any

import psycopg2
from psycopg2 import Error as PsycopgError

from app.models.worker import get_db_connection
from app.models.model_config import get_model_config_for_product
from app.models.admin_settings import get_setting
from app.models.completion_status import get_or_create_completion_status
from app.db_pool import put_conn


logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Task 템플릿 정의
# ──────────────────────────────────────────────

@dataclass
class TaskTemplate:
    """
    Task 템플릿 (app_task_details 행 생성용 설계도)

    Attributes:
        task_id: 고유 식별자 (예: WASTE_GAS_LINE_1)
        task_name: 표시 이름 (한글 가능)
        phase: 공정 단계 (PRE_DOCKING / DOCKING / POST_DOCKING / FINAL)
        is_docking_required: True면 has_docking/tank_in_mech 분기 대상
    """
    task_id: str
    task_name: str
    phase: str
    is_docking_required: bool = False  # docking 관련 task 여부
    task_type: str = 'NORMAL'  # Sprint 27: 'NORMAL' 또는 'SINGLE_ACTION'


# MECH Tasks (7개) — CLAUDE.md 기준
MECH_TASKS: List[TaskTemplate] = [
    TaskTemplate('WASTE_GAS_LINE_1', 'Waste Gas LINE 1',  'PRE_DOCKING',  True),
    TaskTemplate('UTIL_LINE_1',      'Util LINE 1',        'PRE_DOCKING',  True),
    TaskTemplate('TANK_DOCKING',     'Tank Docking',       'DOCKING',      True, 'SINGLE_ACTION'),
    TaskTemplate('WASTE_GAS_LINE_2', 'Waste Gas LINE 2',  'POST_DOCKING', True),
    TaskTemplate('UTIL_LINE_2',      'Util LINE 2',        'POST_DOCKING', True),
    TaskTemplate('HEATING_JACKET',   'Heating Jacket',     'PRE_DOCKING',  False),  # admin 옵션
    TaskTemplate('SELF_INSPECTION',  '자주검사',            'FINAL',        False),  # 항상 활성
]

# ELEC Tasks (6개) — 전 모델 공통
ELEC_TASKS: List[TaskTemplate] = [
    TaskTemplate('PANEL_WORK',   '판넬 작업',         'PRE_DOCKING',  False),
    TaskTemplate('CABINET_PREP', '케비넷 준비 작업',   'PRE_DOCKING',  False),
    TaskTemplate('WIRING',       '배선 포설',          'PRE_DOCKING',  False),
    TaskTemplate('IF_1',         'I.F 1',             'PRE_DOCKING',  False),
    TaskTemplate('IF_2',         'I.F 2',             'POST_DOCKING', False),
    TaskTemplate('INSPECTION',   '자주검사 (검수)',    'FINAL',        False),
]

# TMS Tasks (2개) — GAIA(is_tms=True)만 생성
TMS_TASKS: List[TaskTemplate] = [
    TaskTemplate('TANK_MODULE',   'Tank Module', 'PRE_DOCKING', False),
    TaskTemplate('PRESSURE_TEST', '가압검사',    'FINAL',       False),
]

# Sprint 31A: DRAGON MECH 추가 태스크 (TANK_MODULE + PRESSURE_TEST)
# DRAGON은 PI 불필요 → MECH에서 가압검사까지 전부 처리
MECH_TANK_FULL: List[TaskTemplate] = [
    TaskTemplate('TANK_MODULE',   'Tank Module', 'PRE_DOCKING', False),
    TaskTemplate('PRESSURE_TEST', '가압검사',    'FINAL',       False),
]

# Sprint 31A: SWS/GALLANT MECH 추가 태스크 (TANK_MODULE만)
# 가압검사는 GST PI가 별도 진행
MECH_TANK_MODULE_ONLY: List[TaskTemplate] = [
    TaskTemplate('TANK_MODULE',   'Tank Module', 'PRE_DOCKING', False),
]

# Sprint 11: PI Tasks (2개) — 모든 모델 공통 (GST PI 검사원 전용)
PI_TASKS: List[TaskTemplate] = [
    TaskTemplate('PI_LNG_UTIL', 'LNG/UTIL 가압검사', 'FINAL', False),
    TaskTemplate('PI_CHAMBER',  'CHAMBER 가압검사',   'FINAL', False),
]

# Sprint 11: QI Tasks (1개) — 모든 모델 공통 (GST QI 검사원 전용)
QI_TASKS: List[TaskTemplate] = [
    TaskTemplate('QI_INSPECTION', '공정검사', 'FINAL', False),
]

# Sprint 11: SI Tasks (2개) — 모든 모델 공통 (GST SI 작업자 전용)
SI_TASKS: List[TaskTemplate] = [
    TaskTemplate('SI_FINISHING', '마무리공정', 'FINAL', False),
    TaskTemplate('SI_SHIPMENT', '출하완료', 'FINAL', False, 'SINGLE_ACTION'),  # Sprint 27
]

# category → 템플릿 매핑
_TEMPLATES: Dict[str, List[TaskTemplate]] = {
    'MECH': MECH_TASKS,
    'ELEC': ELEC_TASKS,
    'TMS':  TMS_TASKS,
    'PI':   PI_TASKS,
    'QI':   QI_TASKS,
    'SI':   SI_TASKS,
}


def get_templates(category: str) -> List[TaskTemplate]:
    """카테고리별 Task 템플릿 목록 반환"""
    return _TEMPLATES.get(category, [])


def _is_dual_model(model_name: str, config) -> bool:
    """
    DUAL 여부 판단: model명에 'DUAL' 단어 포함 OR always_dual=True
    - GAIA-I DUAL, GAIA-P DUAL, DRAGON LE DUAL → 'DUAL' in split
    - iVAS → always_dual=True (model명에 DUAL 없어도 항상 2탱크)
    """
    if config and config.always_dual:
        return True
    return 'DUAL' in model_name.upper().split()


# ──────────────────────────────────────────────
# Task 초기화 핵심 함수
# ──────────────────────────────────────────────

def initialize_product_tasks(
    serial_number: str,
    qr_doc_id: str,
    model_name: str
) -> Dict[str, Any]:
    """
    제품 등록 시 Task 20개(MECH 7 + ELEC 6 + TMS 2 + PI 2 + QI 1 + SI 2) 자동 생성.
    Sprint 11: PI/QI/SI 4개 추가.
    CLAUDE.md "Task Seed 초기화 로직" 그대로 구현.

    분기 규칙:
      MECH:
        - HEATING_JACKET → admin_settings.heating_jacket_enabled (default False)
        - is_docking_required Task:
            GAIA (has_docking=True)      → 전부 활성
            DRAGON (tank_in_mech=True)   → TANK_DOCKING만 비활성, 나머지 활성
            기타                          → 비활성
        - SELF_INSPECTION → 항상 활성
      ELEC: 전 모델 6개 전부 활성
      TMS: is_tms=True 인 모델만 생성 (GAIA)
      PI: 모든 모델 2개 전부 활성 (GST PI 검사원 전용)
      QI: 모든 모델 1개 전부 활성 (GST QI 검사원 전용)
      SI: 모든 모델 2개 전부 활성 (GST SI 작업자 전용)

    Args:
        serial_number: 제품 시리얼 번호
        qr_doc_id: QR 문서 ID
        model_name: plan.product_info.model 값 (예: 'GAIA-1234')

    Returns:
        {
            "created": int,           # 생성된 Task 수
            "skipped": int,           # ON CONFLICT로 건너뛴 수
            "categories": {
                "MECH": int, "ELEC": int, "TMS": int, "PI": int, "QI": int, "SI": int
            },
            "error": str | None
        }
    """
    # model_config 조회 (prefix 매칭)
    config = get_model_config_for_product(model_name)
    if config:
        has_docking  = config.has_docking
        is_tms       = config.is_tms
        tank_in_mech = config.tank_in_mech
        logger.info(
            f"Model config found: model={model_name}, prefix={config.model_prefix}, "
            f"has_docking={has_docking}, is_tms={is_tms}, tank_in_mech={tank_in_mech}"
        )
    else:
        # config 없으면 기본값: 도킹/TMS 없음
        has_docking  = False
        is_tms       = False
        tank_in_mech = False
        logger.warning(
            f"Model config not found for model='{model_name}'. "
            f"Using defaults: has_docking=False, is_tms=False, tank_in_mech=False"
        )

    # Sprint 31A: 다모델 분기 변수
    is_dual = _is_dual_model(model_name, config)
    pi_lng_util = config.pi_lng_util if config else True
    pi_chamber = config.pi_chamber if config else True

    # admin_settings에서 heating_jacket 활성화 여부 조회
    heating_jacket_enabled = get_setting('heating_jacket_enabled', False)

    conn = None
    created = 0
    skipped = 0
    counts: Dict[str, int] = {'MECH': 0, 'ELEC': 0, 'TMS': 0, 'PI': 0, 'QI': 0, 'SI': 0}

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # ── MECH Tasks (7개) ──────────────────────────
        for t in MECH_TASKS:
            is_applicable = _resolve_mech_applicability(
                t, has_docking, tank_in_mech, heating_jacket_enabled
            )

            inserted = _upsert_task(
                cur, serial_number, qr_doc_id,
                'MECH', t.task_id, t.task_name, t.phase, is_applicable, t.task_type
            )
            if inserted:
                created += 1
                counts['MECH'] += 1
            else:
                skipped += 1

        # ── Sprint 31A: tank_in_mech MECH 추가 태스크 ──────
        if tank_in_mech:
            # DRAGON(PI 없음): TANK_MODULE + PRESSURE_TEST
            # SWS/GALLANT(PI 있음): TANK_MODULE만
            extra = MECH_TANK_FULL if (not pi_lng_util and not pi_chamber) else MECH_TANK_MODULE_ONLY
            for t in extra:
                inserted = _upsert_task(
                    cur, serial_number, qr_doc_id,
                    'MECH', t.task_id, t.task_name, t.phase, True, t.task_type
                )
                if inserted:
                    created += 1
                    counts['MECH'] += 1
                else:
                    skipped += 1

        # ── ELEC Tasks (6개) — 전 모델 공통 ──────────
        for t in ELEC_TASKS:
            inserted = _upsert_task(
                cur, serial_number, qr_doc_id,
                'ELEC', t.task_id, t.task_name, t.phase, True, t.task_type
            )
            if inserted:
                created += 1
                counts['ELEC'] += 1
            else:
                skipped += 1

        # ── TMS Tasks (2개) — is_tms 모델만 ─────────
        # Sprint 31A: DUAL이면 L/R qr_doc_id별 생성
        if is_tms:
            if is_dual:
                # DUAL: L/R 탱크별 TMS 태스크 생성
                for suffix in ['-L', '-R']:
                    tank_qr = f"{qr_doc_id}{suffix}"
                    for t in TMS_TASKS:
                        inserted = _upsert_task(
                            cur, serial_number, tank_qr,
                            'TMS', t.task_id, t.task_name, t.phase, True, t.task_type
                        )
                        if inserted:
                            created += 1
                            counts['TMS'] += 1
                        else:
                            skipped += 1
            else:
                # SINGLE: 기존 동일
                for t in TMS_TASKS:
                    inserted = _upsert_task(
                        cur, serial_number, qr_doc_id,
                        'TMS', t.task_id, t.task_name, t.phase, True, t.task_type
                    )
                    if inserted:
                        created += 1
                        counts['TMS'] += 1
                    else:
                        skipped += 1

        # ── PI Tasks — Sprint 31A: model_config 기반 분기 ─────
        # SWS JP line 예외: line='JP'이면 pi_lng_util 강제 활성
        _pi_lng = pi_lng_util
        _pi_chm = pi_chamber
        if tank_in_mech:
            cur.execute(
                "SELECT line FROM plan.product_info WHERE serial_number = %s",
                (serial_number,)
            )
            line_row = cur.fetchone()
            product_line = line_row['line'] if line_row and line_row.get('line') else ''
            if product_line.strip().upper().startswith('JP'):
                _pi_lng = True  # SWS + JP(F15) 등 JP 계열 → PI_LNG_UTIL 활성 오버라이드

        for t in PI_TASKS:
            if t.task_id == 'PI_LNG_UTIL':
                is_applicable = _pi_lng
            elif t.task_id == 'PI_CHAMBER':
                is_applicable = _pi_chm
            else:
                is_applicable = True
            inserted = _upsert_task(
                cur, serial_number, qr_doc_id,
                'PI', t.task_id, t.task_name, t.phase, is_applicable, t.task_type
            )
            if inserted:
                created += 1
                counts['PI'] += 1
            else:
                skipped += 1

        # ── Sprint 11: QI Tasks (1개) — 모든 모델 공통 ─────
        for t in QI_TASKS:
            inserted = _upsert_task(
                cur, serial_number, qr_doc_id,
                'QI', t.task_id, t.task_name, t.phase, True, t.task_type
            )
            if inserted:
                created += 1
                counts['QI'] += 1
            else:
                skipped += 1

        # ── Sprint 11: SI Tasks (1개) — 모든 모델 공통 ─────
        for t in SI_TASKS:
            inserted = _upsert_task(
                cur, serial_number, qr_doc_id,
                'SI', t.task_id, t.task_name, t.phase, True, t.task_type
            )
            if inserted:
                created += 1
                counts['SI'] += 1
            else:
                skipped += 1

        conn.commit()

        # completion_status 행 보장 (없으면 생성)
        get_or_create_completion_status(serial_number)

        # Sprint 31A: is_tms=False 모델 → tm_completed = TRUE (TMS 태스크 없음)
        if not is_tms:
            from app.models.completion_status import update_process_completion
            update_process_completion(serial_number, 'TM', True)

        logger.info(
            f"Task seed complete: serial_number={serial_number}, "
            f"created={created}, skipped={skipped}, counts={counts}"
        )

        return {
            "created": created,
            "skipped": skipped,
            "categories": counts,
            "error": None
        }

    except PsycopgError as e:
        import traceback
        if conn:
            conn.rollback()
        logger.error(
            f"Task seed DB ERROR: serial_number={serial_number}, "
            f"model_name={model_name}, error={e}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        return {
            "created": created,
            "skipped": skipped,
            "categories": counts,
            "error": str(e)
        }
    except Exception as e:
        import traceback
        if conn:
            conn.rollback()
        logger.error(
            f"Task seed UNEXPECTED ERROR: serial_number={serial_number}, "
            f"model_name={model_name}, error={e}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        return {
            "created": created,
            "skipped": skipped,
            "categories": counts,
            "error": str(e)
        }
    finally:
        if conn:
            put_conn(conn)


def _resolve_mech_applicability(
    t: TaskTemplate,
    has_docking: bool,
    tank_in_mech: bool,
    heating_jacket_enabled: bool
) -> bool:
    """
    MECH Task 하나의 is_applicable 결정 로직.

    Args:
        t: 템플릿
        has_docking: GAIA 계열
        tank_in_mech: DRAGON 계열
        heating_jacket_enabled: admin_settings 값

    Returns:
        is_applicable bool
    """
    # HEATING_JACKET: admin_settings 제어
    if t.task_id == 'HEATING_JACKET':
        return bool(heating_jacket_enabled)

    # SELF_INSPECTION: 항상 활성
    if t.task_id == 'SELF_INSPECTION':
        return True

    # 나머지 docking-related tasks
    if t.is_docking_required:
        if has_docking:
            # GAIA: 전부 활성
            return True
        elif tank_in_mech:
            # DRAGON: TANK_DOCKING만 비활성, 나머지 활성
            return t.task_id != 'TANK_DOCKING'
        else:
            # 기타: docking-related 전부 비활성
            return False

    # is_docking_required=False이고 특수 케이스가 아닌 경우 → 기본 활성
    return True


def _upsert_task(
    cur,
    serial_number: str,
    qr_doc_id: str,
    task_category: str,
    task_id: str,
    task_name: str,
    phase: str,
    is_applicable: bool,
    task_type: str = 'NORMAL'
) -> bool:
    """
    app_task_details에 Task 행 삽입 (이미 있으면 건너뜀).

    UNIQUE 제약: (serial_number, qr_doc_id, task_category, task_id)
    Sprint 31A: DUAL L/R에서 같은 S/N + task_id지만 qr_doc_id가 다른 행 허용

    Returns:
        True = 새로 삽입됨, False = 이미 존재(건너뜀)
    """
    cur.execute(
        """
        INSERT INTO app_task_details (
            serial_number, qr_doc_id, task_category,
            task_id, task_name, is_applicable, task_type
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (serial_number, qr_doc_id, task_category, task_id) DO NOTHING
        RETURNING id
        """,
        (serial_number, qr_doc_id, task_category,
         task_id, task_name, is_applicable, task_type)
    )
    row = cur.fetchone()
    return row is not None  # RETURNING이 있으면 삽입됨


# ──────────────────────────────────────────────
# Company 기반 Task 필터링
# ──────────────────────────────────────────────

def get_task_categories_for_worker(
    worker_company: Optional[str],
    worker_role: str,
    product_mech_partner: Optional[str],
    product_elec_partner: Optional[str],
    product_module_outsourcing: Optional[str],
    worker_active_role: Optional[str] = None,
    product_line: Optional[str] = None,
    product_model: Optional[str] = None
) -> Optional[List[str]]:
    """
    작업자의 company + role + 제품 협력사 정보를 기반으로
    해당 작업자가 볼 수 있는 task_category 목록을 반환.

    Sprint 11: active_role 파라미터 추가.
    Sprint 31C: product_line 추가 — PI 협력사 위임 분기.

    필터링 규칙:
      - TMS(M): TMS + MECH + PI(pi_capable이면, JP 제외)
      - FNI/BAT: MECH + PI(pi_capable이면, JP 제외)
      - TMS(E)/P&S/C&A: ELEC only
      - GST PI: PI (단, pi_capable 협력사 담당이면 제외, JP이면 유지)
      - GST QI/SI: 해당 검사 category
      - ADMIN: 전체 조회

    Args:
        worker_company: workers.company
        worker_role: workers.role
        product_mech_partner: plan.product_info.mech_partner
        product_elec_partner: plan.product_info.elec_partner
        product_module_outsourcing: plan.product_info.module_outsourcing
        worker_active_role: workers.active_role (Sprint 11)
        product_line: plan.product_info.line (Sprint 31C)
        product_model: plan.product_info.model (Sprint 31C-A — pi_delegate_models 체크)

    Returns:
        보여줄 task_category 리스트 (예: ['MECH'], ['ELEC'], ['TMS', 'MECH', 'PI'])
    """
    categories: List[str] = []

    def _is_delegate_model() -> bool:
        """현재 제품 모델이 pi_delegate_models에 속하는지 확인."""
        if not product_model:
            return False
        delegate_models = get_setting('pi_delegate_models', [])
        model_upper = product_model.strip().upper()
        return any(model_upper.startswith(m.upper()) for m in delegate_models)

    # GST 사내직원: active_role > role 기반 (PI, QI, SI, ADMIN)
    if worker_company == 'GST' or worker_role in ('PI', 'QI', 'SI', 'ADMIN'):
        effective_role = worker_active_role if worker_active_role else worker_role
        if effective_role == 'ADMIN':
            return None
        if effective_role == 'PI':
            # Sprint 31C: PI 협력사 위임 분기
            # pi_capable_mech_partners: mech_partner 컬럼 값 기준 (예: ["TMS"])
            pi_capable = get_setting('pi_capable_mech_partners', [])
            mech_upper = product_mech_partner.upper() if product_mech_partner else ''
            if (
                _is_delegate_model()
                and pi_capable
                and mech_upper
                and mech_upper in [p.upper() for p in pi_capable]
            ):
                # mech_partner가 PI 가능 협력사 + 위임 모델 → GST PI 제외 (단, override 라인이면 유지)
                override_lines = get_setting('pi_gst_override_lines', [])
                line_upper = product_line.strip().upper() if product_line else ''
                is_override = any(line_upper.startswith(p.upper()) for p in override_lines)
                if is_override:
                    categories.append('PI')
                # else: 협력사 담당 → GST PI에서 PI 제외
            else:
                categories.append('PI')
        elif effective_role in ('QI', 'SI'):
            categories.append(effective_role)
        return categories

    # TMS(M): TMS task + mech_partner 매칭 시 MECH + PI(위임 시)
    if worker_company == 'TMS(M)':
        if product_module_outsourcing and 'TMS' in product_module_outsourcing.upper():
            categories.append('TMS')
        if product_mech_partner and product_mech_partner.upper() == 'TMS':
            categories.append('MECH')
            # Sprint 31C-A: PI 위임 — 위임 모델 + pi_capable 회사인지 확인
            pi_capable = get_setting('pi_capable_mech_partners', [])
            if (
                _is_delegate_model()
                and product_mech_partner.upper() in [p.upper() for p in pi_capable]
            ):
                override_lines = get_setting('pi_gst_override_lines', [])
                line_upper = product_line.strip().upper() if product_line else ''
                is_override = any(line_upper.startswith(p.upper()) for p in override_lines)
                if not is_override:
                    categories.append('PI')
        return categories if categories else []

    # FNI / BAT: mech_partner 매칭 → MECH + PI(위임 시)
    if worker_company in ('FNI', 'BAT'):
        if product_mech_partner and product_mech_partner.upper() == worker_company.upper():
            categories.append('MECH')
            # Sprint 31C-A: PI 위임 — 위임 모델 + pi_capable 회사인지 확인
            pi_capable = get_setting('pi_capable_mech_partners', [])
            if (
                _is_delegate_model()
                and product_mech_partner.upper() in [p.upper() for p in pi_capable]
            ):
                override_lines = get_setting('pi_gst_override_lines', [])
                line_upper = product_line.strip().upper() if product_line else ''
                is_override = any(line_upper.startswith(p.upper()) for p in override_lines)
                if not is_override:
                    categories.append('PI')
        return categories

    # TMS(E) / P&S / C&A: elec_partner 매칭 → ELEC only
    if worker_company in ('TMS(E)', 'P&S', 'C&A'):
        # elec_partner 값이 'TMS', 'P&S', 'C&A'로 저장됨
        company_key = worker_company.replace('TMS(E)', 'TMS')
        if product_elec_partner and product_elec_partner.upper() == company_key.upper():
            categories.append('ELEC')
        return categories

    # company 미설정 또는 알 수 없는 경우 → role 기반 fallback
    if worker_role == 'MECH':
        categories.append('MECH')
    elif worker_role == 'ELEC':
        categories.append('ELEC')

    return categories


def filter_tasks_for_worker(
    tasks: list,
    worker_company: Optional[str],
    worker_role: str,
    product,
    worker_active_role: Optional[str] = None
) -> list:
    """
    Task 목록을 작업자 company/role 기준으로 필터링.
    Sprint 11: active_role 파라미터 추가.

    Args:
        tasks: TaskDetail 리스트
        worker_company: workers.company
        worker_role: workers.role
        product: ProductInfo 객체
        worker_active_role: workers.active_role (optional, Sprint 11)

    Returns:
        필터링된 TaskDetail 리스트
    """
    visible_categories = get_task_categories_for_worker(
        worker_company=worker_company,
        worker_role=worker_role,
        product_mech_partner=product.mech_partner if product else None,
        product_elec_partner=product.elec_partner if product else None,
        product_module_outsourcing=product.module_outsourcing if product else None,
        worker_active_role=worker_active_role,
        product_line=product.line if product else None,
        product_model=product.model if product else None,
    )

    # None = 필터 없음 (ADMIN), 빈 리스트면 매칭 없음 → 빈 결과
    if visible_categories is None:
        return tasks

    return [t for t in tasks if t.task_category in visible_categories]
