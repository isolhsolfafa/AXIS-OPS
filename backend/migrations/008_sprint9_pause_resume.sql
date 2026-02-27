-- Sprint 9: 일시정지/재개 + 휴게시간 자동 중지
-- 실행 순서: 순차 실행 (ALTER TABLE은 트랜잭션 밖 또는 ADD COLUMN은 트랜잭션 내 가능)

BEGIN;

-- ============================================================
-- 1. work_pause_log 테이블 생성
-- ============================================================
CREATE TABLE IF NOT EXISTS work_pause_log (
    id SERIAL PRIMARY KEY,
    task_detail_id INTEGER NOT NULL REFERENCES app_task_details(id),
    worker_id INTEGER NOT NULL REFERENCES workers(id),
    paused_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resumed_at TIMESTAMPTZ,
    pause_type VARCHAR(20) NOT NULL DEFAULT 'manual',
    -- pause_type 값: 'manual' | 'break_morning' | 'lunch' | 'break_afternoon' | 'dinner'
    pause_duration_minutes INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_work_pause_log_task
    ON work_pause_log(task_detail_id);

CREATE INDEX IF NOT EXISTS idx_work_pause_log_worker
    ON work_pause_log(worker_id);

-- ============================================================
-- 2. app_task_details 컬럼 추가 (일시정지 상태 관리)
-- ============================================================
ALTER TABLE app_task_details
    ADD COLUMN IF NOT EXISTS is_paused BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS total_pause_minutes INTEGER DEFAULT 0;

-- ============================================================
-- 3. alert_type_enum 확장: 휴게시간 알림 타입 추가
-- ============================================================
-- ALTER TYPE ... ADD VALUE는 트랜잭션 밖에서 실행해야 하므로
-- 새 타입 생성 → 컬럼 교체 → 기존 타입 삭제 방식 사용

COMMIT;

-- 트랜잭션 밖에서 enum 확장
DO $$
BEGIN
    -- BREAK_TIME_PAUSE 추가 (없을 경우만)
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'BREAK_TIME_PAUSE'
          AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'alert_type_enum')
    ) THEN
        ALTER TYPE alert_type_enum ADD VALUE 'BREAK_TIME_PAUSE';
    END IF;
END $$;

DO $$
BEGIN
    -- BREAK_TIME_END 추가 (없을 경우만)
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'BREAK_TIME_END'
          AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'alert_type_enum')
    ) THEN
        ALTER TYPE alert_type_enum ADD VALUE 'BREAK_TIME_END';
    END IF;
END $$;

BEGIN;

-- ============================================================
-- 4. admin_settings: 휴게시간 설정 추가
-- ============================================================
INSERT INTO admin_settings (setting_key, setting_value, description) VALUES
    ('break_morning_start',  '"10:00"', '오전 휴게 시작'),
    ('break_morning_end',    '"10:20"', '오전 휴게 종료'),
    ('break_afternoon_start','"15:00"', '오후 휴게 시작'),
    ('break_afternoon_end',  '"15:20"', '오후 휴게 종료'),
    ('lunch_start',          '"11:20"', '점심시간 시작'),
    ('lunch_end',            '"12:20"', '점심시간 종료'),
    ('dinner_start',         '"17:00"', '저녁시간 시작'),
    ('dinner_end',           '"18:00"', '저녁시간 종료'),
    ('auto_pause_enabled',   'true',    '휴게시간 자동 일시정지 활성화')
ON CONFLICT (setting_key) DO NOTHING;

COMMIT;
