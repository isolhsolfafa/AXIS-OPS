-- Sprint 12: hr 스키마 — 협력사 근태 관리 + PIN 인증 설정
-- 마이그레이션 번호: 010

-- ────────────────────────────────────────────────────────────────
-- 1. hr 스키마 생성
-- ────────────────────────────────────────────────────────────────

CREATE SCHEMA IF NOT EXISTS hr;

-- ────────────────────────────────────────────────────────────────
-- 2. hr.worker_auth_settings — 작업자 PIN/생체인증 설정 (1 row per worker)
-- ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS hr.worker_auth_settings (
    worker_id INTEGER PRIMARY KEY REFERENCES public.workers(id),
    pin_hash VARCHAR(255),                             -- bcrypt 해시된 4자리 PIN
    biometric_enabled BOOLEAN DEFAULT FALSE,           -- 생체인증 활성화 여부
    biometric_type VARCHAR(20),                        -- 'fingerprint' / 'face_id' / null
    pin_fail_count INTEGER DEFAULT 0,                  -- PIN 입력 실패 횟수
    pin_locked_until TIMESTAMPTZ,                      -- PIN 잠금 해제 시각 (3회 실패 → 5분 잠금)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ────────────────────────────────────────────────────────────────
-- 3. hr.partner_attendance — 협력사 출퇴근 기록
--    대상: workers.company != 'GST' (MECH/ELEC/TM 협력사)
-- ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS hr.partner_attendance (
    id SERIAL PRIMARY KEY,
    worker_id INTEGER NOT NULL REFERENCES public.workers(id),
    check_type VARCHAR(3) NOT NULL,     -- 'in' / 'out'
    check_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    method VARCHAR(10) DEFAULT 'button', -- 'button' / 'pin' / 'biometric'
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_partner_att_worker
    ON hr.partner_attendance(worker_id, check_time DESC);

CREATE INDEX IF NOT EXISTS idx_partner_att_date
    ON hr.partner_attendance(check_time);

-- ────────────────────────────────────────────────────────────────
-- 4. hr.gst_attendance — GST 사내 출퇴근 기록 (수동 입력용)
--    대상: workers.company = 'GST'
-- ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS hr.gst_attendance (
    id SERIAL PRIMARY KEY,
    worker_id INTEGER NOT NULL REFERENCES public.workers(id),
    check_type VARCHAR(3) NOT NULL,     -- 'in' / 'out'
    check_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source VARCHAR(20) DEFAULT 'manual', -- 'manual' / 'groupware'
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gst_att_worker
    ON hr.gst_attendance(worker_id, check_time DESC);

-- ────────────────────────────────────────────────────────────────
-- 5. admin_settings: location_qr_required 초기값 (BUG-11)
-- ────────────────────────────────────────────────────────────────
INSERT INTO admin_settings (setting_key, setting_value, description) VALUES
    ('location_qr_required', 'false', 'Location QR 인증 필수 여부 (작업 시작 전)')
ON CONFLICT (setting_key) DO NOTHING;
