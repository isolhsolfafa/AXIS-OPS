-- Sprint 41-B: 릴레이 미완료 task Manager 알림용 alert_type 추가
ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'RELAY_ORPHAN';
