-- Migration 040: 비활성 사용자 관리 (Sprint 40-C)
-- workers 테이블에 is_active, deactivated_at, last_login_at 추가
BEGIN;

-- workers 테이블에 3개 컬럼 추가
ALTER TABLE workers ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE NOT NULL;
ALTER TABLE workers ADD COLUMN IF NOT EXISTS deactivated_at TIMESTAMPTZ;
ALTER TABLE workers ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_workers_is_active ON workers(is_active);
CREATE INDEX IF NOT EXISTS idx_workers_last_login ON workers(last_login_at);

-- 기존 사용자 last_login_at 초기값: app_access_log에서 가장 최근 접속 시각
UPDATE workers w
SET last_login_at = sub.last_access
FROM (
    SELECT worker_id, MAX(created_at) AS last_access
    FROM app_access_log
    GROUP BY worker_id
) sub
WHERE w.id = sub.worker_id
  AND w.last_login_at IS NULL;

COMMIT;
