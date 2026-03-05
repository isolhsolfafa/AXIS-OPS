-- Sprint 19-B: Refresh Token DB 관리 + 탈취 감지
-- auth 스키마에 refresh_tokens 테이블 생성

CREATE SCHEMA IF NOT EXISTS auth;

CREATE TABLE IF NOT EXISTS auth.refresh_tokens (
    id SERIAL PRIMARY KEY,
    worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    device_id VARCHAR(100) NOT NULL DEFAULT 'unknown',
    token_hash VARCHAR(64) NOT NULL,          -- SHA256 해시 (원본 저장 안 함)
    expires_at TIMESTAMPTZ NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    revoked_reason VARCHAR(50),               -- 'rotation' | 'logout' | 'theft_detected' | 'admin'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_worker ON auth.refresh_tokens(worker_id, revoked);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON auth.refresh_tokens(token_hash);
