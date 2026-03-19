-- Migration 026: 사용자 행위 트래킹 (Sprint 32)
BEGIN;

CREATE TABLE IF NOT EXISTS app_access_log (
    id BIGSERIAL PRIMARY KEY,
    worker_id INTEGER REFERENCES workers(id) ON DELETE SET NULL,
    worker_email VARCHAR(255),
    worker_role VARCHAR(50),
    endpoint VARCHAR(255),
    method VARCHAR(10),
    status_code INTEGER,
    duration_ms INTEGER,
    ip_address VARCHAR(45),
    user_agent TEXT,
    request_path VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_access_log_worker_created ON app_access_log(worker_id, created_at);
CREATE INDEX IF NOT EXISTS idx_access_log_created ON app_access_log(created_at);
CREATE INDEX IF NOT EXISTS idx_access_log_endpoint ON app_access_log(endpoint, created_at);

COMMIT;
