-- 작업 관련 테이블 생성
-- Sprint 2: app_task_details + completion_status + work logs

-- 작업 상세 테이블
CREATE TABLE IF NOT EXISTS app_task_details (
    id SERIAL PRIMARY KEY,
    worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    serial_number VARCHAR(255) NOT NULL,
    qr_doc_id VARCHAR(255) NOT NULL REFERENCES qr_registry(qr_doc_id) ON DELETE CASCADE,
    task_category VARCHAR(50) NOT NULL,  -- MM, EE, TM, PI, QI, SI
    task_id VARCHAR(100) NOT NULL,  -- Task 식별자 (예: CABINET_ASSY)
    task_name VARCHAR(255) NOT NULL,  -- Task 이름 (예: 캐비넷 조립)
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_minutes INTEGER,  -- 소요시간 (분 단위, completed_at - started_at)
    is_applicable BOOLEAN DEFAULT TRUE,  -- Task 적용 여부 (관리자/사내직원이 비활성화 가능)
    location_qr_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (serial_number, task_category, task_id)  -- 중복 작업 방지
);

-- 완료 상태 테이블
CREATE TABLE IF NOT EXISTS completion_status (
    serial_number VARCHAR(255) PRIMARY KEY REFERENCES plan.product_info(serial_number) ON DELETE RESTRICT,
    mm_completed BOOLEAN DEFAULT FALSE,
    ee_completed BOOLEAN DEFAULT FALSE,
    tm_completed BOOLEAN DEFAULT FALSE,
    pi_completed BOOLEAN DEFAULT FALSE,
    qi_completed BOOLEAN DEFAULT FALSE,
    si_completed BOOLEAN DEFAULT FALSE,
    all_completed BOOLEAN DEFAULT FALSE,  -- 모든 공정 완료 여부
    all_completed_at TIMESTAMP WITH TIME ZONE,  -- 전체 완료 시각
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 작업 시작 로그 (감사용)
CREATE TABLE IF NOT EXISTS work_start_log (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES app_task_details(id) ON DELETE CASCADE,
    worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    serial_number VARCHAR(255) NOT NULL,
    qr_doc_id VARCHAR(255) NOT NULL,
    task_category VARCHAR(50) NOT NULL,
    task_id_ref VARCHAR(100) NOT NULL,  -- task_id와 구분하기 위해 _ref 접미사
    task_name VARCHAR(255) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 작업 완료 로그 (감사용 + 실시간 소요시간 추적)
CREATE TABLE IF NOT EXISTS work_completion_log (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES app_task_details(id) ON DELETE CASCADE,
    worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    serial_number VARCHAR(255) NOT NULL,
    qr_doc_id VARCHAR(255) NOT NULL,
    task_category VARCHAR(50) NOT NULL,
    task_id_ref VARCHAR(100) NOT NULL,  -- task_id와 구분하기 위해 _ref 접미사
    task_name VARCHAR(255) NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_minutes INTEGER,  -- 소요시간 (분 단위, completed_at - started_at 자동계산)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_app_task_details_worker_id ON app_task_details(worker_id);
CREATE INDEX IF NOT EXISTS idx_app_task_details_qr_doc_id ON app_task_details(qr_doc_id);
CREATE INDEX IF NOT EXISTS idx_app_task_details_serial_number ON app_task_details(serial_number);
CREATE INDEX IF NOT EXISTS idx_app_task_details_completed_at ON app_task_details(completed_at);
CREATE INDEX IF NOT EXISTS idx_app_task_details_task_category ON app_task_details(task_category);
CREATE INDEX IF NOT EXISTS idx_completion_status_serial_number ON completion_status(serial_number);
CREATE INDEX IF NOT EXISTS idx_work_start_log_serial_number ON work_start_log(serial_number);
CREATE INDEX IF NOT EXISTS idx_work_completion_log_serial_number ON work_completion_log(serial_number);
