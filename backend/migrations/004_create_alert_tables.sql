-- 알림 관련 테이블 생성
-- TODO: 알림 타입 정의
-- TODO: 알림 우선순위

-- 알림 타입 ENUM
CREATE TYPE alert_type_enum AS ENUM (
    'PROCESS_READY',
    'UNFINISHED_AT_CLOSING',
    'DURATION_EXCEEDED',
    'REVERSE_COMPLETION',
    'DUPLICATE_COMPLETION',
    'LOCATION_QR_FAILED',
    'WORKER_APPROVED',
    'WORKER_REJECTED'
);

-- 알림 로그 테이블
CREATE TABLE IF NOT EXISTS app_alert_logs (
    id SERIAL PRIMARY KEY,
    alert_type alert_type_enum NOT NULL,
    serial_number VARCHAR(255),
    qr_doc_id VARCHAR(255),
    triggered_by_worker_id INTEGER REFERENCES workers(id) ON DELETE SET NULL,
    target_worker_id INTEGER REFERENCES workers(id) ON DELETE SET NULL,
    target_role VARCHAR(50),
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_app_alert_logs_target_worker_id ON app_alert_logs(target_worker_id);
CREATE INDEX IF NOT EXISTS idx_app_alert_logs_qr_doc_id ON app_alert_logs(qr_doc_id);
CREATE INDEX IF NOT EXISTS idx_app_alert_logs_is_read ON app_alert_logs(is_read);
CREATE INDEX IF NOT EXISTS idx_app_alert_logs_created_at ON app_alert_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_app_alert_logs_serial_number ON app_alert_logs(serial_number);
