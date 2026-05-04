-- Sprint 63-BE: MECH 체크리스트 도입 — schema 확장
-- 등록일: 2026-04-29
-- 트리거: Twin파파 양식 공유 (현황판_260108_MFC Maker추가 260223.xlsm)
-- 선행 Sprint: Sprint 52 (TM) ✅ / Sprint 60-BE (ELEC) ✅
-- 변경 내용: 신규 컬럼 2개 + enum 2개 (item_type 'INPUT' + alert_type 'CHECKLIST_MECH_READY')

-- ────────────────────────────────────────────────────────────────
-- (1) scope_rule — 모델 분기 매크로
--     'all'           = 모든 모델 적용 (기본, TM/ELEC 호환)
--     'tank_in_mech'  = model_config.tank_in_mech=TRUE 인 모델만 (DRAGON/GALLANT/SWS)
--     'DRAGON'        = DRAGON 모델만 (INLET S/N 4 sub-rows 용)
-- ────────────────────────────────────────────────────────────────
ALTER TABLE checklist.checklist_master
    ADD COLUMN IF NOT EXISTS scope_rule VARCHAR(30) DEFAULT 'all';

COMMENT ON COLUMN checklist.checklist_master.scope_rule IS
    '모델 분기 매크로 (Sprint 63-BE). all=모든 모델 / tank_in_mech=DRAGON·GALLANT·SWS / DRAGON=DRAGON 단독';


-- ────────────────────────────────────────────────────────────────
-- (2) trigger_task_id — 1차 입력 토스트 발화 시점
--     UTIL_LINE_1        = Speed Controller 4 항목 (PRE_DOCKING)
--     UTIL_LINE_2        = MFC 4 + Flow Sensor 3 = 7 항목 (POST_DOCKING)
--     WASTE_GAS_LINE_2   = INLET S/N 4 항목 (POST_DOCKING)
--     NULL               = 1차 트리거 없음 (54개 일반 CHECK 항목 → SELF_INSPECTION 일괄 2차)
-- ────────────────────────────────────────────────────────────────
ALTER TABLE checklist.checklist_master
    ADD COLUMN IF NOT EXISTS trigger_task_id VARCHAR(50);

COMMENT ON COLUMN checklist.checklist_master.trigger_task_id IS
    'MECH 체크리스트 1차 입력 토스트 발화 task_id (Sprint 63-BE). UTIL_LINE_1/UTIL_LINE_2/WASTE_GAS_LINE_2/NULL';


-- ────────────────────────────────────────────────────────────────
-- (3) item_type 'INPUT' enum 확장 (기존 CHECK / SELECT)
--     INPUT = 자유 텍스트 입력 (SN, 수량 등)
-- ────────────────────────────────────────────────────────────────
ALTER TABLE checklist.checklist_master
    DROP CONSTRAINT IF EXISTS checklist_master_item_type_check;

ALTER TABLE checklist.checklist_master
    ADD CONSTRAINT checklist_master_item_type_check
    CHECK (item_type IN ('CHECK', 'SELECT', 'INPUT'));


-- ────────────────────────────────────────────────────────────────
-- (4) alert_type_enum 'CHECKLIST_MECH_READY' 추가
--     UTIL_LINE_1 / UTIL_LINE_2 / WASTE_GAS_LINE_2 task 시작 시 작업자 토스트
-- ────────────────────────────────────────────────────────────────
ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'CHECKLIST_MECH_READY';


-- ────────────────────────────────────────────────────────────────
-- 검증 쿼리 (배포 후 실행)
-- ────────────────────────────────────────────────────────────────
-- SELECT column_name, data_type, column_default
-- FROM information_schema.columns
-- WHERE table_schema='checklist' AND table_name='checklist_master'
--   AND column_name IN ('scope_rule', 'trigger_task_id');
--
-- SELECT enumlabel FROM pg_enum
-- WHERE enumtypid = 'alert_type_enum'::regtype
--   AND enumlabel = 'CHECKLIST_MECH_READY';
