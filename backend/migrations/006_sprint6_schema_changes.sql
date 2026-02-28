-- Sprint 6: 네이밍 변경(MM→MECH, EE→ELEC) + DB 스키마 확장
-- 실행 순서: 순차 실행 (트랜잭션 내)

BEGIN;

-- ============================================================
-- 1. role_enum 변경: MECH, ELEC, ADMIN 추가
-- ============================================================

-- role_enum에 새 값 추가 (ALTER TYPE ... ADD VALUE는 트랜잭션 밖에서만 가능하므로
--  아래 방식: 새 타입 생성 → 컬럼 교체 → 기존 타입 삭제)

-- 1-1. 새 role_enum 타입 생성 (MECH, ELEC 포함)
CREATE TYPE role_enum_new AS ENUM ('MECH', 'ELEC', 'TM', 'PI', 'QI', 'SI', 'ADMIN');

-- 1-2. workers.role 컬럼을 새 타입으로 교체
--      기존 MM → MECH, EE → ELEC 데이터 마이그레이션
ALTER TABLE workers
    ALTER COLUMN role TYPE role_enum_new
    USING (
        CASE role::text
            WHEN 'MM' THEN 'MECH'::role_enum_new
            WHEN 'EE' THEN 'ELEC'::role_enum_new
            ELSE role::text::role_enum_new
        END
    );

-- 1-3. 기존 role_enum 타입 삭제 후 이름 변경
DROP TYPE role_enum;
ALTER TYPE role_enum_new RENAME TO role_enum;

-- ============================================================
-- 2. workers 테이블에 company 컬럼 추가
-- ============================================================
ALTER TABLE workers
    ADD COLUMN IF NOT EXISTS company VARCHAR(50);

-- company 인덱스
CREATE INDEX IF NOT EXISTS idx_workers_company ON workers(company);

-- ============================================================
-- 3. completion_status: mm_completed → mech_completed, ee_completed → elec_completed
-- ============================================================
ALTER TABLE completion_status
    RENAME COLUMN mm_completed TO mech_completed;

ALTER TABLE completion_status
    RENAME COLUMN ee_completed TO elec_completed;

-- ============================================================
-- 4. model_config 테이블 생성
-- ============================================================
CREATE TABLE IF NOT EXISTS model_config (
    id SERIAL PRIMARY KEY,
    model_prefix VARCHAR(50) UNIQUE NOT NULL,     -- GAIA, DRAGON, GALLANT, MITHAS, SDS, SWS
    has_docking BOOLEAN NOT NULL DEFAULT FALSE,   -- 도킹 공정 존재 여부 (GAIA: true)
    is_tms BOOLEAN NOT NULL DEFAULT FALSE,        -- TMS 모듈 사용 여부 (GAIA: true)
    tank_in_mech BOOLEAN NOT NULL DEFAULT FALSE,  -- 탱크가 MECH 협력사 담당 여부 (DRAGON: true)
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- model_config 초기 데이터 (6개 모델)
INSERT INTO model_config (model_prefix, has_docking, is_tms, tank_in_mech, description)
VALUES
    ('GAIA',    TRUE,  TRUE,  FALSE, 'TMS(M) 탱크 별도 → MECH 도킹'),
    ('DRAGON',  FALSE, FALSE, TRUE,  '한 협력사가 탱크+MECH 일괄'),
    ('GALLANT', FALSE, FALSE, FALSE, '탱크/도킹 없음'),
    ('MITHAS',  FALSE, FALSE, FALSE, '탱크/도킹 없음'),
    ('SDS',     FALSE, FALSE, FALSE, '탱크/도킹 없음'),
    ('SWS',     FALSE, FALSE, FALSE, '탱크/도킹 없음')
ON CONFLICT (model_prefix) DO NOTHING;

-- model_config updated_at 트리거
CREATE TRIGGER update_model_config_updated_at
    BEFORE UPDATE ON model_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 5. admin_settings 테이블 생성
-- ============================================================
CREATE TABLE IF NOT EXISTS admin_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value JSONB NOT NULL DEFAULT 'false',
    description TEXT,
    updated_by INTEGER REFERENCES workers(id),
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- admin_settings 초기값
INSERT INTO admin_settings (setting_key, setting_value, description)
VALUES
    ('heating_jacket_enabled', 'false', 'Heating Jacket task 활성화 여부'),
    ('phase_block_enabled',    'false', 'Tank Docking 완료 전 POST_DOCKING task 차단 여부')
ON CONFLICT (setting_key) DO NOTHING;

-- ============================================================
-- 6. app_task_details 확장: 멀티 작업자 + 강제 종료 컬럼 추가
-- ============================================================
ALTER TABLE app_task_details
    ADD COLUMN IF NOT EXISTS elapsed_minutes INTEGER,         -- 실경과시간 (최초시작~마지막종료)
    ADD COLUMN IF NOT EXISTS worker_count INTEGER DEFAULT 1,  -- 투입 인원 수
    ADD COLUMN IF NOT EXISTS force_closed BOOLEAN DEFAULT FALSE,  -- 강제 종료 여부
    ADD COLUMN IF NOT EXISTS closed_by INTEGER REFERENCES workers(id),  -- 강제 종료한 관리자
    ADD COLUMN IF NOT EXISTS close_reason TEXT;               -- 강제 종료 사유

-- ============================================================
-- 7. alert_type_enum 확장: 신규 알림 타입 추가
-- ============================================================

-- alert_type_enum에 새 값 추가
--  ALTER TYPE ... ADD VALUE는 트랜잭션 밖에서 실행해야 하므로
--  새 타입 생성 → 컬럼 교체 → 기존 타입 삭제 방식 사용
CREATE TYPE alert_type_enum_new AS ENUM (
    'PROCESS_READY',
    'UNFINISHED_AT_CLOSING',
    'DURATION_EXCEEDED',
    'REVERSE_COMPLETION',
    'DUPLICATE_COMPLETION',
    'LOCATION_QR_FAILED',
    'WORKER_APPROVED',
    'WORKER_REJECTED',
    'TMS_TANK_COMPLETE',        -- TMS 가압검사 완료 → MECH 관리자 알림 (GAIA)
    'TANK_DOCKING_COMPLETE',    -- MECH Tank Docking 완료 → ELEC 관리자 알림 (GAIA)
    'TASK_REMINDER',            -- 작업자 리마인더 (매 1시간)
    'SHIFT_END_REMINDER',       -- 퇴근 시간 알림 (17:00, 20:00)
    'TASK_ESCALATION'           -- 관리자 에스컬레이션 (익일 09:00)
);

ALTER TABLE app_alert_logs
    ALTER COLUMN alert_type TYPE alert_type_enum_new
    USING (alert_type::text::alert_type_enum_new);

DROP TYPE alert_type_enum;
ALTER TYPE alert_type_enum_new RENAME TO alert_type_enum;

-- ============================================================
-- 8. app_alert_logs: read_at 컬럼 추가 (Sprint 5 누락)
-- ============================================================
ALTER TABLE app_alert_logs
    ADD COLUMN IF NOT EXISTS read_at TIMESTAMPTZ;

-- app_alert_logs updated_at 트리거 추가 (Sprint 5 누락)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'update_app_alert_logs_updated_at'
    ) THEN
        CREATE TRIGGER update_app_alert_logs_updated_at
            BEFORE UPDATE ON app_alert_logs
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- ============================================================
-- 9. app_task_details.worker_id → NULL 허용
--    Task Seed 시점에는 아직 담당 작업자가 배정되지 않음
-- ============================================================
ALTER TABLE app_task_details
    ALTER COLUMN worker_id DROP NOT NULL;

-- ============================================================
-- 10. Admin Seed 계정 (Sprint 간 초기화 방지)
-- ============================================================
INSERT INTO workers (name, email, password_hash, role, company,
                     approval_status, email_verified, is_manager, is_admin)
VALUES ('관리자', 'dkkim1@gst-in.com',
        '$2b$12$rA3QYwD/moabyRWHG4MrPuUQMEw3M4lBP79UCi/9uc/BiBeHMa2yO',
        'ADMIN', 'GST', 'approved', TRUE, TRUE, TRUE)
ON CONFLICT (email) DO NOTHING;

COMMIT;
