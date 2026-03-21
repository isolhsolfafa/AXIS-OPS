-- Sprint 35: 추이 집계용 복합 인덱스 (무중단)
-- DATE(check_time KST) + work_site + worker_id, check_type='in'만

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_partner_att_trend
    ON hr.partner_attendance (
        (DATE(check_time AT TIME ZONE 'Asia/Seoul')),
        work_site,
        worker_id
    )
    WHERE check_type = 'in';
