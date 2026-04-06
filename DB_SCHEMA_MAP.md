# AXIS-OPS Database Schema Map

> 운영 DB (Railway PostgreSQL 15) 기준 — 최종 업데이트: 2026-04-07
> 8개 스키마, 43개 테이블, 3개 ENUM

---

## 스키마 개요

| 스키마 | 테이블 수 | 용도 |
|--------|----------|------|
| **public** | 18 | APP 운영 (workers, tasks, alerts, QR, 설정) |
| **plan** | 2 | 생산관리 (product_info, production_confirm) |
| **hr** | 3 | 인사/근태 (출퇴근, PIN 인증) |
| **checklist** | 2 | 체크리스트 (마스터 + 기록) |
| **auth** | 1 | 인증 (refresh_tokens) |
| **analytics** | 4 | 분석 (불량 통계, ML 예측) |
| **defect** | 2 | 불량 관리 (defect_record, inspection_record) |
| **etl** | 1 | ETL 변경이력 (change_log) |

---

## public 스키마 (18 테이블)

### workers (13컬럼) — 작업자/관리자 계정
```
id                  SERIAL PK
name                VARCHAR(255) NOT NULL
email               VARCHAR(255) NOT NULL UNIQUE
password_hash       VARCHAR(255) NOT NULL
role                role_enum NOT NULL
approval_status     approval_status_enum DEFAULT 'pending'
email_verified      BOOLEAN DEFAULT false
is_manager          BOOLEAN DEFAULT false
is_admin            BOOLEAN DEFAULT false
created_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
updated_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
company             VARCHAR(50)
active_role         VARCHAR(10)
```

### app_task_details (22컬럼) — 작업 상세
```
id                  SERIAL PK
worker_id           INTEGER FK→workers(id)
serial_number       VARCHAR(255) NOT NULL
qr_doc_id           VARCHAR(255) NOT NULL FK→qr_registry(qr_doc_id)
task_category       VARCHAR(50) NOT NULL
task_id             VARCHAR(100) NOT NULL
task_name           VARCHAR(255) NOT NULL
started_at          TIMESTAMPTZ
completed_at        TIMESTAMPTZ
duration_minutes    INTEGER
is_applicable       BOOLEAN DEFAULT true
location_qr_verified BOOLEAN DEFAULT false
created_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
updated_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
elapsed_minutes     INTEGER
worker_count        INTEGER DEFAULT 1
force_closed        BOOLEAN DEFAULT false
closed_by           INTEGER FK→workers(id)
close_reason        TEXT
is_paused           BOOLEAN DEFAULT false
total_pause_minutes INTEGER DEFAULT 0
task_type           VARCHAR(20) NOT NULL DEFAULT 'NORMAL'
```
UNIQUE: (serial_number, qr_doc_id, task_category, task_id)

### qr_registry (10컬럼) — QR ↔ 제품 매핑
```
id                  SERIAL PK
qr_doc_id           VARCHAR(255) NOT NULL UNIQUE
serial_number       VARCHAR(255) NOT NULL FK→plan.product_info(serial_number)
status              VARCHAR(50) DEFAULT 'active'
issued_at           TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
revoked_at          TIMESTAMPTZ
created_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
updated_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
parent_qr_doc_id    VARCHAR(100) FK→qr_registry(qr_doc_id)
qr_type             VARCHAR(20) NOT NULL DEFAULT 'PRODUCT'
```

### completion_status (11컬럼) — 공정 완료 상태
```
serial_number       VARCHAR(255) PK FK→plan.product_info(serial_number)
mech_completed      BOOLEAN DEFAULT false
elec_completed      BOOLEAN DEFAULT false
tm_completed        BOOLEAN DEFAULT false
pi_completed        BOOLEAN DEFAULT false
qi_completed        BOOLEAN DEFAULT false
si_completed        BOOLEAN DEFAULT false
all_completed       BOOLEAN DEFAULT false
all_completed_at    TIMESTAMPTZ
created_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
updated_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```

### work_start_log (10컬럼) — 작업 시작 이력
```
id                  SERIAL PK
task_id             INTEGER NOT NULL FK→app_task_details(id)
worker_id           INTEGER NOT NULL FK→workers(id)
serial_number       VARCHAR(255) NOT NULL
qr_doc_id           VARCHAR(255) NOT NULL
task_category       VARCHAR(50) NOT NULL
task_id_ref         VARCHAR(100) NOT NULL
task_name           VARCHAR(255) NOT NULL
started_at          TIMESTAMPTZ NOT NULL
created_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```

### work_completion_log (11컬럼) — 작업 완료 이력
```
id                  SERIAL PK
task_id             INTEGER NOT NULL FK→app_task_details(id)
worker_id           INTEGER NOT NULL FK→workers(id)
serial_number       VARCHAR(255) NOT NULL
qr_doc_id           VARCHAR(255) NOT NULL
task_category       VARCHAR(50) NOT NULL
task_id_ref         VARCHAR(100) NOT NULL
task_name           VARCHAR(255) NOT NULL
completed_at        TIMESTAMPTZ NOT NULL
duration_minutes    INTEGER
created_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```

### work_pause_log (8컬럼) — 일시정지 이력
```
id                  SERIAL PK
task_detail_id      INTEGER NOT NULL FK→app_task_details(id)
worker_id           INTEGER NOT NULL FK→workers(id)
paused_at           TIMESTAMPTZ NOT NULL DEFAULT now()
resumed_at          TIMESTAMPTZ
pause_type          VARCHAR(20) NOT NULL DEFAULT 'manual'
pause_duration_minutes INTEGER
created_at          TIMESTAMPTZ DEFAULT now()
```

### app_alert_logs (12컬럼) — 알림 로그
```
id                  SERIAL PK
alert_type          alert_type_enum NOT NULL
serial_number       VARCHAR(255)
qr_doc_id           VARCHAR(255)
triggered_by_worker_id INTEGER FK→workers(id)
target_worker_id    INTEGER FK→workers(id)
target_role         VARCHAR(50)
message             TEXT NOT NULL
is_read             BOOLEAN DEFAULT false
read_at             TIMESTAMPTZ
created_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
updated_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```

### admin_settings (6컬럼) — 관리자 설정
```
id                  SERIAL PK
setting_key         VARCHAR(100) NOT NULL UNIQUE
setting_value       JSONB NOT NULL DEFAULT 'false'
description         TEXT
updated_by          INTEGER FK→workers(id)
updated_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```

### model_config (11컬럼) — 모델별 설정
```
id                  SERIAL PK
model_prefix        VARCHAR(50) NOT NULL
has_docking         BOOLEAN NOT NULL DEFAULT false
is_tms              BOOLEAN NOT NULL DEFAULT false
tank_in_mech        BOOLEAN NOT NULL DEFAULT false
description         TEXT
created_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
updated_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
pi_lng_util         BOOLEAN NOT NULL DEFAULT true
pi_chamber          BOOLEAN NOT NULL DEFAULT true
always_dual         BOOLEAN NOT NULL DEFAULT false
```

### notices (8컬럼) — 공지사항
```
id                  SERIAL PK
title               VARCHAR(200) NOT NULL
content             TEXT NOT NULL
version             VARCHAR(20)
is_pinned           BOOLEAN DEFAULT false
created_by          INTEGER FK→workers(id)
created_at          TIMESTAMPTZ DEFAULT now()
updated_at          TIMESTAMPTZ DEFAULT now()
```

### email_verification (6컬럼) — 이메일 인증
```
id                  SERIAL PK
worker_id           INTEGER NOT NULL FK→workers(id)
verification_code   VARCHAR(6) NOT NULL UNIQUE
expires_at          TIMESTAMPTZ NOT NULL
verified_at         TIMESTAMPTZ
created_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```

### app_access_log (12컬럼) — API 접근 로그
```
id                  BIGSERIAL PK
worker_id           INTEGER FK→workers(id)
worker_email        VARCHAR(255)
worker_role         VARCHAR(50)
endpoint            VARCHAR(255)
method              VARCHAR(10)
status_code         INTEGER
duration_ms         INTEGER
ip_address          VARCHAR(45)
user_agent          TEXT
request_path        VARCHAR(500)
created_at          TIMESTAMPTZ DEFAULT now()
```

### location_history (6컬럼) — 위치 이력
```
id                  SERIAL PK
worker_id           INTEGER NOT NULL FK→workers(id)
latitude            NUMERIC NOT NULL
longitude           NUMERIC NOT NULL
recorded_at         TIMESTAMPTZ NOT NULL
created_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```

### offline_sync_queue (9컬럼) — 오프라인 동기화 큐
```
id                  SERIAL PK
worker_id           INTEGER NOT NULL FK→workers(id)
operation           VARCHAR(50) NOT NULL
table_name          VARCHAR(100) NOT NULL
record_id           VARCHAR(255)
data                JSONB
synced              BOOLEAN DEFAULT false
synced_at           TIMESTAMPTZ
created_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```

### product_bom (11컬럼) — BOM 목록
```
id                  SERIAL PK
product_code        VARCHAR(50) NOT NULL
item_seq            INTEGER NOT NULL
item_name           VARCHAR(200) NOT NULL
item_code           VARCHAR(50)
quantity            INTEGER DEFAULT 1
unit                VARCHAR(20)
category            VARCHAR(50)
is_active           BOOLEAN DEFAULT true
created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

### bom_checklist_log (17컬럼) — BOM 검증 로그
```
id                  SERIAL PK
serial_number       VARCHAR(128) NOT NULL
google_doc_id       VARCHAR(100)
product_code        VARCHAR(50) NOT NULL
bom_item_id         INTEGER NOT NULL FK→product_bom(id)
is_checked          BOOLEAN DEFAULT false
checked_at          TIMESTAMP
checked_by          VARCHAR(50)
ai_verified         BOOLEAN
ai_verified_at      TIMESTAMP
ai_confidence       NUMERIC
ai_image_url        TEXT
ai_response         JSONB
mismatch_reported   BOOLEAN DEFAULT false
mismatch_notes      TEXT
created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

### documents (4컬럼) — PDA 기준 참조용
```
document_id         SERIAL PK
execution_date      DATE
timestamp           TIMESTAMP
serial_number       VARCHAR(128)
```

---

## plan 스키마 (2 테이블)

### plan.product_info (28컬럼) — 생산 메타데이터
```
id                  SERIAL PK
serial_number       VARCHAR(255) NOT NULL UNIQUE
model               VARCHAR(255) NOT NULL
title_number        VARCHAR(255)
product_code        VARCHAR(255)
sales_order         VARCHAR(255)
customer            VARCHAR(255)
line                VARCHAR(255)
quantity            VARCHAR(50) DEFAULT '1'
mech_partner        VARCHAR(255)
elec_partner        VARCHAR(255)
module_outsourcing  VARCHAR(255)
prod_date           DATE
mech_start          DATE
mech_end            DATE
elec_start          DATE
elec_end            DATE
module_start        DATE
location_qr_id      VARCHAR(255)
created_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
updated_at          TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
pi_start            DATE
qi_start            DATE
si_start            DATE
ship_plan_date      DATE
finishing_plan_end  DATE
actual_ship_date    DATE
module_end          DATE
```

### plan.production_confirm (11컬럼) — 생산실적 확인
```
id                  SERIAL PK
sales_order         VARCHAR(255) NOT NULL
process_type        VARCHAR(20) NOT NULL
confirmed_week      VARCHAR(10) NOT NULL
confirmed_month     VARCHAR(7) NOT NULL
confirmed_by        INTEGER FK→workers(id)
confirmed_at        TIMESTAMPTZ DEFAULT now()
deleted_at          TIMESTAMPTZ
deleted_by          INTEGER FK→workers(id)
partner             VARCHAR(50)
serial_number       VARCHAR(20)
```

---

## hr 스키마 (3 테이블)

### hr.partner_attendance (9컬럼) — 협력사 출퇴근
```
id                  SERIAL PK
worker_id           INTEGER NOT NULL FK→workers(id)
check_type          VARCHAR(3) NOT NULL        -- 'in' / 'out'
check_time          TIMESTAMPTZ NOT NULL DEFAULT now()
method              VARCHAR(10) DEFAULT 'button'
note                TEXT
created_at          TIMESTAMPTZ DEFAULT now()
work_site           VARCHAR(10) NOT NULL DEFAULT 'GST'
product_line        VARCHAR(10) NOT NULL DEFAULT 'SCR'
```

### hr.gst_attendance (7컬럼) — GST 사내직원 근태
```
id                  SERIAL PK
worker_id           INTEGER NOT NULL FK→workers(id)
check_type          VARCHAR(3) NOT NULL
check_time          TIMESTAMPTZ NOT NULL DEFAULT now()
source              VARCHAR(20) DEFAULT 'manual'
note                TEXT
created_at          TIMESTAMPTZ DEFAULT now()
```

### hr.worker_auth_settings (8컬럼) — PIN/생체 인증
```
worker_id           INTEGER PK FK→workers(id)
pin_hash            VARCHAR(255)
biometric_enabled   BOOLEAN DEFAULT false
biometric_type      VARCHAR(20)
pin_fail_count      INTEGER DEFAULT 0
pin_locked_until    TIMESTAMPTZ
created_at          TIMESTAMPTZ DEFAULT now()
updated_at          TIMESTAMPTZ DEFAULT now()
```

---

## checklist 스키마 (2 테이블)

### checklist.checklist_master (11컬럼) — 체크리스트 마스터
```
id                  SERIAL PK
product_code        VARCHAR(100) NOT NULL
category            VARCHAR(20) NOT NULL
item_name           VARCHAR(255) NOT NULL
item_order          INTEGER DEFAULT 0
description         TEXT
is_active           BOOLEAN DEFAULT true
created_at          TIMESTAMPTZ DEFAULT now()
updated_at          TIMESTAMPTZ DEFAULT now()
item_group          VARCHAR(50)              -- BURNER/REACTOR/EXHAUST/TANK
item_type           VARCHAR(10) DEFAULT 'CHECK' -- CHECK/INPUT
```
UNIQUE: (product_code, category, item_group, item_name)

### checklist.checklist_record (11컬럼) — 체크리스트 기록
```
id                  SERIAL PK
serial_number       VARCHAR(100) NOT NULL
master_id           INTEGER NOT NULL FK→checklist_master(id)
is_checked          BOOLEAN DEFAULT false    -- 기존 호환 유지
checked_by          INTEGER FK→workers(id)
checked_at          TIMESTAMPTZ
note                TEXT
created_at          TIMESTAMPTZ DEFAULT now()
updated_at          TIMESTAMPTZ DEFAULT now()
check_result        VARCHAR(10)              -- PASS/NA/NULL
judgment_phase      INTEGER DEFAULT 1        -- 1차/2차 판정
```
UNIQUE: (serial_number, master_id, judgment_phase)

---

## auth 스키마 (1 테이블)

### auth.refresh_tokens (9컬럼)
```
id                  SERIAL PK
worker_id           INTEGER NOT NULL FK→workers(id)
device_id           VARCHAR(100) NOT NULL DEFAULT 'unknown'
token_hash          VARCHAR(64) NOT NULL
expires_at          TIMESTAMPTZ NOT NULL
revoked             BOOLEAN DEFAULT false
revoked_reason      VARCHAR(50)
created_at          TIMESTAMPTZ DEFAULT now()
last_used_at        TIMESTAMPTZ
```

---

## analytics 스키마 (4 테이블)

### analytics.defect_statistics (12컬럼) — 불량 통계
### analytics.defect_keyword (6컬럼) — 불량 키워드
### analytics.component_priority (11컬럼) — 부품 우선순위
### analytics.ml_prediction (13컬럼) — ML 예측

---

## defect 스키마 (2 테이블)

### defect.defect_record (24컬럼) — 불량 기록
### defect.inspection_record (12컬럼) — 검사 기록

---

## etl 스키마 (1 테이블)

### etl.change_log (6컬럼) — ETL 변경이력
```
id                  SERIAL PK
serial_number       VARCHAR(50) NOT NULL
field_name          VARCHAR(50) NOT NULL
old_value           TEXT
new_value           TEXT
changed_at          TIMESTAMP DEFAULT now()
```

---

## FK 관계도

```
workers ←── auth.refresh_tokens (worker_id)
        ←── hr.worker_auth_settings (worker_id)
        ←── hr.partner_attendance (worker_id)
        ←── hr.gst_attendance (worker_id)
        ←── email_verification (worker_id)
        ←── app_task_details (worker_id, closed_by)
        ←── work_start_log (worker_id)
        ←── work_completion_log (worker_id)
        ←── work_pause_log (worker_id)
        ←── app_alert_logs (triggered_by, target)
        ←── app_access_log (worker_id)
        ←── location_history (worker_id)
        ←── offline_sync_queue (worker_id)
        ←── admin_settings (updated_by)
        ←── notices (created_by)
        ←── plan.production_confirm (confirmed_by, deleted_by)
        ←── checklist.checklist_record (checked_by)

plan.product_info ←── qr_registry (serial_number)
                  ←── completion_status (serial_number)

qr_registry ←── app_task_details (qr_doc_id)
            ←── qr_registry (parent_qr_doc_id) [self-ref]

app_task_details ←── work_start_log (task_id)
                 ←── work_completion_log (task_id)
                 ←── work_pause_log (task_detail_id)

checklist.checklist_master ←── checklist.checklist_record (master_id)

defect.defect_record ←── analytics.defect_keyword (defect_record_id)

product_bom ←── bom_checklist_log (bom_item_id)
```

---

## ENUM 타입

### role_enum
`MECH, ELEC, TM, PI, QI, SI, ADMIN, PM`

### approval_status_enum
`pending, approved, rejected`

### alert_type_enum (18값)
```
PROCESS_READY, UNFINISHED_AT_CLOSING, DURATION_EXCEEDED,
REVERSE_COMPLETION, DUPLICATE_COMPLETION, LOCATION_QR_FAILED,
WORKER_APPROVED, WORKER_REJECTED,
TMS_TANK_COMPLETE, TANK_DOCKING_COMPLETE,
TASK_REMINDER, SHIFT_END_REMINDER, TASK_ESCALATION,
BREAK_TIME_PAUSE, BREAK_TIME_END,
CHECKLIST_TM_READY, CHECKLIST_ISSUE, ELEC_COMPLETE
```

---

## 주요 JOIN 패턴

```sql
-- S/N → 제품 상세
qr_registry JOIN plan.product_info ON serial_number

-- Task 목록 + 작업자
app_task_details LEFT JOIN work_start_log ON task_id
                 LEFT JOIN work_completion_log ON task_id
                 LEFT JOIN workers ON worker_id

-- 체크리스트
checklist.checklist_master LEFT JOIN checklist.checklist_record
    ON master_id AND serial_number AND judgment_phase

-- 출퇴근
hr.partner_attendance JOIN workers ON worker_id

-- 알림
app_alert_logs JOIN workers ON target_worker_id
```
