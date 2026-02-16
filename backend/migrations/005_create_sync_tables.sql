-- 동기화 관련 테이블 생성
-- TODO: 오프라인 데이터 동기화
-- TODO: 배치 처리

-- 오프라인 동기화 큐
CREATE TABLE IF NOT EXISTS offline_sync_queue (
    id SERIAL PRIMARY KEY,
    worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    operation VARCHAR(50) NOT NULL,  -- 'INSERT', 'UPDATE', 'DELETE'
    table_name VARCHAR(100) NOT NULL,
    record_id VARCHAR(255),
    data JSONB,
    synced BOOLEAN DEFAULT FALSE,
    synced_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 위치 기록 테이블 (별도의 다른 마이그레이션에서도 정의되어야 함)
CREATE TABLE IF NOT EXISTS location_history (
    id SERIAL PRIMARY KEY,
    worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_offline_sync_queue_worker_id ON offline_sync_queue(worker_id);
CREATE INDEX IF NOT EXISTS idx_offline_sync_queue_synced ON offline_sync_queue(synced);
CREATE INDEX IF NOT EXISTS idx_location_history_worker_id ON location_history(worker_id);
CREATE INDEX IF NOT EXISTS idx_location_history_recorded_at ON location_history(recorded_at);
