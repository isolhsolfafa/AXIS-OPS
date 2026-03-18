-- ============================================================
-- Migration 024: 다모델 지원 (Sprint 31A)
-- 목적: DUAL L/R QR + DRAGON MECH 탱크 + 모델별 PI + workers/hr 보호
-- 사전조건: Railway DB 백업 완료 (2026-03-17 13:19 UTC, 228MB)
-- ============================================================

BEGIN;

-- ──────────────────────────────────────────────────────────
-- ① model_config: PI/DUAL 관련 컬럼 추가
-- ──────────────────────────────────────────────────────────
ALTER TABLE model_config
    ADD COLUMN IF NOT EXISTS pi_lng_util BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS pi_chamber BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS always_dual BOOLEAN NOT NULL DEFAULT FALSE;

-- ② model_config 기존 데이터 업데이트
UPDATE model_config SET pi_lng_util = TRUE,  pi_chamber = TRUE,  always_dual = FALSE WHERE model_prefix = 'GAIA';
UPDATE model_config SET pi_lng_util = FALSE, pi_chamber = FALSE, always_dual = FALSE WHERE model_prefix = 'DRAGON';
UPDATE model_config SET pi_lng_util = FALSE, pi_chamber = TRUE,  always_dual = FALSE, tank_in_mech = TRUE WHERE model_prefix = 'SWS';
UPDATE model_config SET pi_lng_util = TRUE,  pi_chamber = FALSE, always_dual = FALSE, tank_in_mech = TRUE WHERE model_prefix = 'GALLANT';
UPDATE model_config SET pi_lng_util = TRUE,  pi_chamber = TRUE,  always_dual = FALSE WHERE model_prefix = 'MITHAS';
UPDATE model_config SET pi_lng_util = TRUE,  pi_chamber = TRUE,  always_dual = FALSE WHERE model_prefix = 'SDS';

-- ③ iVAS 모델 추가 (has_docking=True, is_tms=True, always_dual=True)
INSERT INTO model_config (model_prefix, has_docking, is_tms, tank_in_mech, pi_lng_util, pi_chamber, always_dual, description)
VALUES ('IVAS', TRUE, TRUE, FALSE, TRUE, TRUE, TRUE, 'iVAS: 항상 2탱크(L/R), TMS 별도, 도킹 있음')
ON CONFLICT (model_prefix) DO UPDATE SET
    has_docking = EXCLUDED.has_docking,
    is_tms = EXCLUDED.is_tms,
    tank_in_mech = EXCLUDED.tank_in_mech,
    pi_lng_util = EXCLUDED.pi_lng_util,
    pi_chamber = EXCLUDED.pi_chamber,
    always_dual = EXCLUDED.always_dual,
    description = EXCLUDED.description;

-- ──────────────────────────────────────────────────────────
-- ④ qr_registry: 탱크 QR 계층 구조 컬럼 추가
-- ──────────────────────────────────────────────────────────
ALTER TABLE public.qr_registry
    ADD COLUMN IF NOT EXISTS parent_qr_doc_id VARCHAR(100) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS qr_type VARCHAR(20) NOT NULL DEFAULT 'PRODUCT';

-- parent_qr_doc_id FK (자기 참조)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'qr_registry_parent_fk'
    ) THEN
        ALTER TABLE public.qr_registry
            ADD CONSTRAINT qr_registry_parent_fk
            FOREIGN KEY (parent_qr_doc_id) REFERENCES public.qr_registry(qr_doc_id)
            ON DELETE CASCADE;
    END IF;
END $$;

-- ──────────────────────────────────────────────────────────
-- ⑤ app_task_details: UNIQUE 제약 변경
--    기존: (serial_number, task_category, task_id)
--    변경: (serial_number, qr_doc_id, task_category, task_id)
--    이유: DUAL에서 같은 S/N + task_id지만 L/R qr_doc_id가 다른 행 허용
-- ──────────────────────────────────────────────────────────
DO $$
DECLARE
    _constraint_name TEXT;
BEGIN
    SELECT constraint_name INTO _constraint_name
    FROM information_schema.table_constraints
    WHERE table_name = 'app_task_details'
      AND constraint_type = 'UNIQUE'
    LIMIT 1;

    IF _constraint_name IS NOT NULL THEN
        EXECUTE 'ALTER TABLE app_task_details DROP CONSTRAINT ' || _constraint_name;
    END IF;
END $$;

ALTER TABLE app_task_details
    ADD CONSTRAINT app_task_details_sn_qr_cat_tid_unique
    UNIQUE (serial_number, qr_doc_id, task_category, task_id);

-- ──────────────────────────────────────────────────────────
-- ⑥ workers / hr 테이블 보호: CASCADE → RESTRICT
--    Railway 백업 완료 후 실행
-- ──────────────────────────────────────────────────────────

-- 작업 이력 보존 (CASCADE → RESTRICT)
ALTER TABLE work_start_log
    DROP CONSTRAINT IF EXISTS work_start_log_worker_id_fkey;
ALTER TABLE work_start_log
    ADD CONSTRAINT work_start_log_worker_id_fkey
    FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE RESTRICT;

ALTER TABLE work_completion_log
    DROP CONSTRAINT IF EXISTS work_completion_log_worker_id_fkey;
ALTER TABLE work_completion_log
    ADD CONSTRAINT work_completion_log_worker_id_fkey
    FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE RESTRICT;

-- PIN/생체인증 보존 (CASCADE → RESTRICT)
ALTER TABLE hr.worker_auth_settings
    DROP CONSTRAINT IF EXISTS worker_auth_settings_worker_id_fkey;
ALTER TABLE hr.worker_auth_settings
    ADD CONSTRAINT worker_auth_settings_worker_id_fkey
    FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE RESTRICT;

-- 출퇴근 기록 보호 (FK 규칙 없음 → RESTRICT)
ALTER TABLE hr.partner_attendance
    DROP CONSTRAINT IF EXISTS partner_attendance_worker_id_fkey;
ALTER TABLE hr.partner_attendance
    ADD CONSTRAINT partner_attendance_worker_id_fkey
    FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE RESTRICT;

ALTER TABLE hr.gst_attendance
    DROP CONSTRAINT IF EXISTS gst_attendance_worker_id_fkey;
ALTER TABLE hr.gst_attendance
    ADD CONSTRAINT gst_attendance_worker_id_fkey
    FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE RESTRICT;

-- app_task_details: 작업자 삭제 시 태스크 보존, 담당자만 NULL
ALTER TABLE app_task_details
    DROP CONSTRAINT IF EXISTS app_task_details_worker_id_fkey;
ALTER TABLE app_task_details
    ADD CONSTRAINT app_task_details_worker_id_fkey
    FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE SET NULL;

COMMIT;
