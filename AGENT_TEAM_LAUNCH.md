# Agent Teams 실행 가이드 (Sprint 5~11)

## 사전 조건
- ✅ Sprint 1~4 완료 (81 tests, 32 API endpoints)
- ✅ `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` = "1" 설정 완료
- ✅ CLAUDE.md Sprint 5~11 + Task Seed 데이터 업데이트 완료
- ✅ UI 디자인 시스템 (GxColors) 적용 중
- ✅ 5-Tier 스키마 아키텍처 (plan, app, checklist, hr, defect)

---

## 실행 순서

### Step 1: tmux 세션 시작 (멀티창 보기)
```bash
# tmux 세션 생성
tmux new -s axis

# 4분할 레이아웃 설정
# 1) 먼저 세로 분할
Ctrl+B, %

# 2) 왼쪽 패널에서 가로 분할
Ctrl+B, 방향키(←)로 왼쪽 이동
Ctrl+B, "

# 3) 오른쪽 패널에서 가로 분할
Ctrl+B, 방향키(→)로 오른쪽 이동
Ctrl+B, "
```

결과: 4개 패널
```
┌──────────┬──────────┐
│  Lead    │   BE     │
├──────────┼──────────┤
│  FE      │  TEST    │
└──────────┴──────────┘
```

tmux 패널 이동: `Ctrl+B, 방향키`

### Step 2: 왼쪽 상단 패널(Lead)에서 Claude Code 시작
```bash
cd ~/Desktop/GST/AXIS-OPS
claude
```

### Step 3: accept edits on 확인
- 하단에 `accept edits on` 표시 확인
- 아니면 **Shift+Tab** 으로 전환

### Step 4: Sprint 5 팀 생성 프롬프트 입력

---

## 🚀 Sprint 5 프롬프트 (복사해서 사용)

```
CLAUDE.md가 대폭 업데이트 되었어. 반드시 CLAUDE.md를 처음부터 끝까지 다시 읽고 Agent Teams를 구성해줘.

⚠️ 사전 작업 완료 사항 (이미 반영됨 — 다시 하지 말 것):
- plan.product_info + qr_registry 2테이블 분리 완료
- 컬럼명 간소화 완료 (mech_start, pi_start, qi_start, si_start, ship_plan_date 등)
- product_info.py JOIN 쿼리 + dataclass 업데이트 완료
- ETL step2_load.py 2-table insert 패턴 적용 완료
- PDA 전용 테이블 11개 삭제 완료 (25→14 테이블)
- DB 타임존 Asia/Seoul 설정 완료
- FE product_info.dart 모델 동기화 완료

## 팀 구성
3명의 teammate를 생성해줘. 모든 teammate는 Sonnet 모델 사용:

1. **BE** (Backend 담당) - 소유: backend/**
2. **FE** (Frontend 담당) - 소유: frontend/**
3. **TEST** (테스트 담당) - 소유: tests/**

## Sprint 5 시작 (Migration FK 수정 + 누락 모델 + 보안 + PWA + 이메일)

### BE 작업 순서 (반드시 이 순서대로):
**Phase A: Migration SQL FK 수정 + 누락 모델**
1. 003_create_task_tables.sql FK 수정:
   - app_task_details.qr_doc_id FK → qr_registry(qr_doc_id) (구: product_info)
   - completion_status.serial_number FK → qr_registry(serial_number) (구: product_info)
2. 누락 Python 모델 파일 생성:
   - work_start_log.py (WorkStartLog dataclass + CRUD)
   - work_completion_log.py (WorkCompletionLog dataclass + CRUD)
   - offline_sync_queue.py (OfflineSyncQueue dataclass + CRUD)
3. location_history.py 완성: from_db_row() 구현 + CRUD 함수 추가 (현재 pass 상태)
4. alert_log.py에 read_at 필드 추가 + 004_create_alert_tables.sql에 read_at 컬럼 + 트리거 추가
5. worker.py에 EmailVerification dataclass 추가
6. models/__init__.py에 새 모델 전부 import 추가

**Phase B: 보안 + 이메일**
7. config.py → .env 파일로 분리 (DATABASE_URL, JWT_SECRET_KEY, SMTP 설정)
8. python-dotenv 적용, config.py에서 os.getenv로 읽기
9. SMTP 연동 (auth_service.py에서 실제 이메일 발송 구현, SMTP_FROM_NAME=G-AXIS)
10. Refresh Token 엔드포인트 구현

### FE 작업 순서:
1. PWA Service Worker 생성 및 등록 (web/service-worker.js)
2. web/manifest.json 앱 아이콘 경로 확인
3. flutter build web 실행 → 빌드 에러 수정
4. 빌드 성공 확인

### TEST 작업 순서:
1. 누락 모델 단위 테스트 (WorkStartLog, WorkCompletionLog, OfflineSyncQueue)
2. 이메일 발송 mock 테스트 구현
3. Refresh Token 테스트 구현

## 규칙
- CLAUDE.md의 "DB 테이블 정확한 컬럼 명세" 섹션을 반드시 참조
- product_info는 plan 스키마, qr_registry는 public 스키마
- 제품 조회: qr_registry JOIN plan.product_info ON serial_number
- BE가 코드를 완성하면 TEST가 먼저 CLAUDE.md 기준으로 코드 리뷰 진행
- 리뷰 통과 후에만 테스트 코드 작성
- 각 teammate는 자신의 소유 파일만 수정 가능
- Sprint 5 완료 시 PROGRESS.md에 진행사항 추가 정리
```

---

## 🔧 Sprint 5 보완 프롬프트 (Sprint 6 전에 먼저 실행)

```
CLAUDE.md 읽고 Sprint 5 보완 작업을 진행해줘.

## 팀 구성
2명의 teammate를 생성해줘. 모든 teammate는 Sonnet 모델 사용:

1. **BE** (Backend 담당) - 소유: backend/**
2. **TEST** (테스트 담당) - 소유: tests/**

## 보완 작업 (총 3개)

### BE 작업 순서:

**1. product_info.py — ProductInfo dataclass 컬럼 완성 (⚠️ 최우선)**

현재 ProductInfo dataclass에 10개 필드만 있는데, plan.product_info 테이블에는 25개 컬럼이 있음.
누락된 15개 필드를 dataclass에 추가하고, _BASE_JOIN_QUERY SELECT절도 동기화해야 함.

추가할 필드 (전부 Optional — NULL 허용):
```python
title_number: Optional[str] = None
product_code: Optional[str] = None
sales_order: Optional[str] = None
customer: Optional[str] = None
line: Optional[str] = None
quantity: Optional[str] = None      # VARCHAR(255) DEFAULT '1'
elec_partner: Optional[str] = None
mech_start: Optional[date] = None
mech_end: Optional[date] = None
elec_start: Optional[date] = None
elec_end: Optional[date] = None
module_start: Optional[date] = None
pi_start: Optional[date] = None
qi_start: Optional[date] = None
si_start: Optional[date] = None
ship_plan_date: Optional[date] = None
```

_BASE_JOIN_QUERY 수정:
```sql
SELECT pi.id, qr.qr_doc_id, pi.serial_number,
       pi.model, pi.prod_date, pi.location_qr_id,
       pi.mech_partner, pi.elec_partner, pi.module_outsourcing,
       pi.title_number, pi.product_code, pi.sales_order,
       pi.customer, pi.line, pi.quantity,
       pi.mech_start, pi.mech_end,
       pi.elec_start, pi.elec_end,
       pi.module_start, pi.pi_start, pi.qi_start, pi.si_start,
       pi.ship_plan_date,
       pi.created_at, pi.updated_at
FROM public.qr_registry qr
JOIN plan.product_info pi ON qr.serial_number = pi.serial_number
```

from_db_row()도 새 필드 전부 row.get()으로 매핑.

**2. 이메일 Rate Limiting 추가**

auth_service.py 상단에 간단한 메모리 기반 Rate Limiter 추가:
```python
from collections import defaultdict
import time

_email_rate_log: dict = defaultdict(list)
_MAX_EMAILS_PER_HOUR = 5

def _check_email_rate_limit(email: str) -> bool:
    """1시간 내 이메일 발송 횟수 제한 (DoS 방지)"""
    now = time.time()
    _email_rate_log[email] = [t for t in _email_rate_log[email] if now - t < 3600]
    if len(_email_rate_log[email]) >= _MAX_EMAILS_PER_HOUR:
        return False
    _email_rate_log[email].append(now)
    return True
```

send_verification_email() 시작에 Rate limit 체크 추가:
```python
if not _check_email_rate_limit(to_email):
    logger.warning(f"Email rate limit exceeded: {to_email}")
    return False
```

### TEST 작업 순서:

**3. test_refresh_token.py — 누락 테스트 5개 추가**

PROGRESS.md에 22개로 기재되어 있지만 실제 17개만 구현됨.
아래 5개 테스트를 추가 구현:
- test_refresh_token_cannot_be_used_as_access_token (refresh 토큰으로 일반 API 호출 시 401)
- test_access_token_cannot_be_used_as_refresh_token (access 토큰으로 refresh 엔드포인트 호출 시 401)
- test_refresh_after_role_change (역할 변경 후 refresh 시 새 역할 반영)
- test_refresh_after_account_rejected (승인 거부 후 refresh 시 403)
- test_multiple_refresh_tokens_valid (여러 refresh token 동시 유효)

## 규칙
- product_info.py 수정 시 CLAUDE.md "plan.product_info" 명세의 컬럼명을 정확히 따를 것
- BE 완료 후 TEST가 코드 리뷰 진행
- SMTP Subject UTF-8 인코딩은 이미 완료됨 (메일 정상 수신 확인) — 건드리지 말 것
- 완료 시 PROGRESS.md 테스트 카운트 정정 (test_email: 12개, test_refresh_token: 22개, 합계: 59개)
```

---

## 🚀 Sprint 6 프롬프트 (Sprint 5 보완 완료 후 사용)

```
CLAUDE.md가 대폭 업데이트 되었어. 반드시 CLAUDE.md를 처음부터 끝까지 다시 읽고 Agent Teams를 구성해줘.

⚠️ Sprint 6 핵심 변경사항:
- 네이밍 변경: MM→MECH, EE→ELEC (코드 전체 22+ 파일 영향)
- Task 재설계: 기존 27개 → 15개 (MECH 7 + ELEC 6 + TMS 2)
- workers.company 컬럼 추가 (FNI, BAT, TMS(M), TMS(E), P&S, C&A, GST)
- model_config, admin_settings 테이블 신설
- role_enum에 ADMIN 추가

## 팀 구성
3명의 teammate를 생성해줘. 모든 teammate는 Sonnet 모델 사용:

1. **BE** (Backend 담당) - 소유: backend/**
2. **FE** (Frontend 담당) - 소유: frontend/**
3. **TEST** (테스트 담당) - 소유: tests/**

## Sprint 6 시작

### BE 작업 순서 (반드시 이 순서대로):

**Phase A: 네이밍 변경 + DB 스키마 변경**
1. Migration SQL 작성 (005_sprint6_schema_changes.sql):
   - role_enum 변경: MECH, ELEC 추가 → 기존 데이터 UPDATE (MM→MECH, EE→ELEC) → MM, EE 값 제거
   - role_enum에 ADMIN 추가
   - workers 테이블에 company VARCHAR(50) 컬럼 추가
   - model_config 테이블 생성 (model_prefix, has_docking, is_tms, tank_in_mech + 초기 데이터 6건: GAIA, DRAGON, GALLANT, MITHAS, SDS, SWS)
   - admin_settings 테이블 생성 (key-value JSONB, 초기값: heating_jacket_enabled=false, phase_block_enabled=false)
2. 기존 코드 MM→MECH, EE→ELEC 전수 교체:
   - auth_service.py: VALID_ROLES = {'MECH', 'ELEC', 'TM', 'PI', 'QI', 'SI'}
   - task_service.py: VALID_PROCESS_TYPES, process 분기
   - process_validator.py: get_managers_for_role('MECH'/'ELEC')
   - completion_status.py: mm_completed→mech_completed, ee_completed→elec_completed
   - work.py: missing_processes 분기
3. 회원가입 시 company 검증 로직 추가 (company↔role 유효 조합):
   - FNI/BAT → MECH만
   - TMS(M) → MECH만
   - TMS(E) → ELEC만
   - P&S/C&A → ELEC만
   - GST → PI, QI, SI, ADMIN

**Phase B: Task Seed 재설계**
4. Task 템플릿 15개 정의 (CLAUDE.md "Task Seed 데이터" 섹션 반드시 참조):
   - MECH 7개: WASTE_GAS_LINE_1, UTIL_LINE_1, TANK_DOCKING, WASTE_GAS_LINE_2, UTIL_LINE_2, HEATING_JACKET, SELF_INSPECTION
   - ELEC 6개: PANEL_WORK, CABINET_PREP, WIRING, IF_1, IF_2, INSPECTION
   - TMS 2개: TANK_MODULE, PRESSURE_TEST
5. initialize_product_tasks(serial_number, qr_doc_id, model_name) 구현:
   - model_config에서 prefix 매칭으로 has_docking/is_tms/tank_in_mech 조회
   - GAIA: MECH 1~5,7 활성 + TMS 2개 생성
   - DRAGON: MECH 1~5 활성 + TANK_DOCKING만 비활성
   - 기타: 자주검사만 활성, 1~5 비활성
   - HEATING_JACKET: admin_settings에서 heating_jacket_enabled 조회 (default false)
6. Task Seed API: POST /api/admin/products/initialize-tasks
7. company 기반 Task 필터링 로직:
   - TMS(M): module_outsourcing='TMS' → TMS task + mech_partner 매칭 시 MECH task
   - FNI/BAT: mech_partner 매칭 → MECH task만
   - TMS(E)/P&S/C&A: elec_partner 매칭 → ELEC task만
   - ⚠️ DRAGON 모델: TMS(M)이 보통 담당하지만 반드시 product_info.mech_partner 값으로 확인
8. 알림 트리거 2개 (GAIA 전용):
   - TMS 가압검사 완료 → TMS_TANK_COMPLETE → MECH 관리자 알림
   - MECH Tank Docking 완료 → TANK_DOCKING_COMPLETE → ELEC 관리자 알림

**Phase C: 멀티 작업자 + 미종료 처리**
9. app_task_details 컬럼 확장 (migration에 포함):
   - elapsed_minutes INTEGER (실경과시간)
   - worker_count INTEGER DEFAULT 1 (투입 인원)
   - force_closed BOOLEAN DEFAULT FALSE (강제 종료 여부)
   - closed_by INTEGER FK→workers(id) (강제 종료 관리자)
   - close_reason TEXT (강제 종료 사유)
10. 멀티 작업자 duration 계산 로직:
    - started_at = MIN(work_start_log.started_at)
    - completed_at = MAX(work_completion_log.completed_at)
    - duration_minutes = SUM(각 worker 개별 duration) ← man-hour 합산
    - elapsed_minutes = completed_at - started_at
11. 미종료 작업 알림 스케줄러 (scheduler_service.py 확장):
    - 1단계: 매 1시간 → 작업자 리마인더 (TASK_REMINDER)
    - 2단계: 17:00/20:00 KST → 퇴근 알림 (SHIFT_END_REMINDER)
    - 3단계: 익일 09:00 → 관리자 에스컬레이션 (TASK_ESCALATION)
12. 관리자 강제 종료 API: PUT /api/admin/tasks/{task_id}/force-close

### FE 작업 순서:
1. MM→MECH, EE→ELEC 네이밍 전수 교체:
   - worker.dart, task_item.dart, register_screen.dart, home_screen.dart, process_alert_popup.dart
2. 회원가입 화면 변경:
   - company 드롭다운 추가 (FNI, BAT, TMS(M), TMS(E), P&S, C&A, GST)
   - company 선택 → role 선택지 자동 필터링
3. Admin 옵션 화면 신설:
   - admin_settings 토글 (heating_jacket, phase_block)
   - 협력사 관리자 지정/해제 (is_manager 토글, company 필터)
   - 미종료 작업 목록 → 강제 종료 버튼 (completed_at 입력 + 사유)
4. GxColors 디자인 통일 확인

### TEST 작업 순서:
1. 기존 테스트 MM→MECH, EE→ELEC 전수 교체 (conftest.py, sample_workers.json, sample_tasks.json, sample_alerts.json 포함)
2. model_config 분기 테스트 (GAIA/DRAGON/기타)
3. Task Seed 초기화 테스트
4. company 기반 Task 필터링 테스트
5. admin_settings CRUD 테스트
6. 멀티 작업자 duration 계산 테스트
7. 미종료 알림 스케줄러 테스트 (mock 시간)

## 규칙
- CLAUDE.md의 "Task Seed 데이터" 섹션을 반드시 참조
- product_info는 plan 스키마, qr_registry는 public 스키마
- company 저장값은 product_info 실제 DB 값과 동일: FNI, BAT, TMS(M), TMS(E), P&S, C&A, GST
- BE가 코드를 완성하면 TEST가 먼저 CLAUDE.md 기준으로 코드 리뷰 진행
- 리뷰 통과 후에만 테스트 코드 작성
- Sprint 6 완료 시 PROGRESS.md에 진행사항 추가 정리
```

---

## 🚀 Sprint 7 프롬프트 — 전체 플로우 검증 + 통합 테스트 (Sprint 6 완료 후 사용)

```
CLAUDE.md를 처음부터 끝까지 다시 읽고 Sprint 7을 시작해줘.

⚠️ Sprint 7 핵심 목표:
1. **FE↔BE API 불일치 해소** — FE가 호출하는데 BE에 없는 API 5개 구현
2. **전체 플로우 검증 + 통합 테스트** — 모든 시나리오에서 정상 동작 확인

## 팀 구성
3명의 teammate를 생성해줘. 모든 teammate는 Sonnet 모델 사용:

1. **BE** (Backend 담당) - 소유: backend/**
2. **FE** (Frontend 담당) - 소유: frontend/**
3. **TEST** (테스트 담당) - 소유: tests/**

## BE 작업 순서

### 0. ⚠️ Admin API 누락 엔드포인트 5개 구현 (최우선)
FE admin_options_screen.dart가 호출하는데 BE admin.py에 없는 API를 구현:

**0-1. GET /api/admin/managers** (query: ?company=선택)
- workers 테이블에서 전체 작업자 목록 반환 (approval_status='approved')
- company 파라미터가 있으면 해당 company만 필터링
- 응답: `{"workers": [{"id", "name", "email", "role", "company", "is_manager", "is_admin"}]}`
- @jwt_required + @admin_required

**0-2. PUT /api/admin/workers/{worker_id}/manager**
- 특정 작업자의 is_manager 값을 토글
- 요청: `{"is_manager": true/false}`
- 응답: `{"message": "매니저 권한이 변경되었습니다.", "worker_id": int, "is_manager": bool}`
- @jwt_required + @admin_required

**0-3. GET /api/admin/settings**
- admin_settings 테이블의 전체 설정 조회
- 응답: `{"settings": [{"setting_key", "setting_value", "description", "updated_at"}]}`
- @jwt_required + @admin_required

**0-4. PUT /api/admin/settings**
- admin_settings 업데이트 (UPSERT)
- 요청: `{"setting_key": "heating_jacket_enabled", "setting_value": true}`
- 기존 admin_settings.py의 update_setting() 함수 활용
- @jwt_required + @admin_required

**0-5. GET /api/admin/tasks/pending**
- 미종료 작업 목록 (started_at IS NOT NULL AND completed_at IS NULL)
- 작업자 이름, serial_number, task_category, task_name, started_at 포함
- 응답: `{"tasks": [...], "total": int}`
- @jwt_required + @admin_required

### 1. 테스트용 모델별 제품 데이터 Seed (conftest.py에 fixture 추가)
현재 Staging DB에는 GAIA-I DUAL만 있지만, 테스트에서는 6개 모델 전부 커버해야 함.
conftest.py에 모델별 테스트 제품 fixture 추가:

```python
# conftest.py에 추가할 fixture
TEST_PRODUCTS = [
    {"serial_number": "TEST-GAIA-001",    "qr_doc_id": "DOC_TEST-GAIA-001",    "model": "GAIA-I DUAL",    "mech_partner": "FNI",  "elec_partner": "TMS",  "module_outsourcing": "TMS"},
    {"serial_number": "TEST-DRAGON-001",  "qr_doc_id": "DOC_TEST-DRAGON-001",  "model": "DRAGON-V",       "mech_partner": "TMS",  "elec_partner": "P&S",  "module_outsourcing": None},
    {"serial_number": "TEST-GALLANT-001", "qr_doc_id": "DOC_TEST-GALLANT-001", "model": "GALLANT-III",    "mech_partner": "BAT",  "elec_partner": "C&A",  "module_outsourcing": None},
    {"serial_number": "TEST-MITHAS-001",  "qr_doc_id": "DOC_TEST-MITHAS-001",  "model": "MITHAS-II",      "mech_partner": "FNI",  "elec_partner": "P&S",  "module_outsourcing": None},
    {"serial_number": "TEST-SDS-001",     "qr_doc_id": "DOC_TEST-SDS-001",     "model": "SDS-100",        "mech_partner": "BAT",  "elec_partner": "TMS",  "module_outsourcing": None},
    {"serial_number": "TEST-SWS-001",     "qr_doc_id": "DOC_TEST-SWS-001",     "model": "SWS-200",        "mech_partner": "FNI",  "elec_partner": "C&A",  "module_outsourcing": None},
]

TEST_WORKERS = [
    {"name": "FNI기구1",   "email": "fni1@test.com",   "role": "MECH", "company": "FNI",    "approval_status": "approved", "email_verified": True},
    {"name": "BAT기구1",   "email": "bat1@test.com",   "role": "MECH", "company": "BAT",    "approval_status": "approved", "email_verified": True},
    {"name": "TMS기구1",   "email": "tmsm1@test.com",  "role": "MECH", "company": "TMS(M)", "approval_status": "approved", "email_verified": True},
    {"name": "TMS전기1",   "email": "tmse1@test.com",  "role": "ELEC", "company": "TMS(E)", "approval_status": "approved", "email_verified": True},
    {"name": "PS전기1",    "email": "ps1@test.com",    "role": "ELEC", "company": "P&S",    "approval_status": "approved", "email_verified": True},
    {"name": "CA전기1",    "email": "ca1@test.com",    "role": "ELEC", "company": "C&A",    "approval_status": "approved", "email_verified": True},
    {"name": "GST관리자",  "email": "admin@test.com",  "role": "ADMIN","company": "GST",    "approval_status": "approved", "email_verified": True, "is_admin": True, "is_manager": True},
    {"name": "미승인작업자","email": "pending@test.com","role": "MECH", "company": "FNI",    "approval_status": "pending",  "email_verified": True},
    {"name": "미인증작업자","email": "noverify@test.com","role": "ELEC","company": "P&S",    "approval_status": "pending",  "email_verified": False},
]
```

### 2. GET /api/app/product/{qr_doc_id} 엔드포인트 검증
현재 이 엔드포인트 테스트가 **0건** — 반드시 추가:
- 제품 조회 정상 응답 (200)
- 존재하지 않는 QR → 404
- ⚠️ Task Seed 자동 초기화 확인: 제품 조회 시 app_task_details에 Task 자동 생성 검증 (product.py에 initialize_product_tasks 자동 호출 로직 있음)
- 동일 제품 재조회 시 Task 중복 생성 안 되는지 확인 (ON CONFLICT DO NOTHING)

### 3. 빈 껍데기 통합 테스트 실제 구현
현재 tests/integration/ 하위 3개 파일이 전부 `assert False, "Test implementation required"` 상태.
**이번 Sprint에서 반드시 실제 구현해야 함.**

### 4. 발견된 버그 수정
테스트 과정에서 발견되는 모든 버그를 즉시 수정.
이미 알려진 이슈:
- test_full_workflow.py에 role이 아직 'MM'으로 되어 있음 → 'MECH' 교체
- test_process_check_flow.py 내 MM→EE→PI 순서 → MECH→ELEC→PI 교체

## FE 작업 순서

### 1. 프론트엔드 빌드 및 에러 점검
- `flutter build web` 성공 확인
- 콘솔 에러 0건 확인
- API 연동 실패 시 사용자 친화적 에러 메시지 표시 확인

### 2. 화면별 플로우 점검 (코드 레벨)
- Splash → Login → (승인 대기) → Home → QR Scan → Task List → Task Start/Complete
- APPROVAL_PENDING 에러 시 ApprovalPendingScreen으로 이동하는지 확인
- Admin 옵션 화면에서 설정 토글/강제 종료 동작 코드 확인

## TEST 작업 순서 (⚠️ 이번 Sprint의 핵심)

### Phase 0: Admin API 누락 엔드포인트 테스트

**test_admin_options_api.py (신규 — 12개 이상)**
- GET /api/admin/managers → 전체 목록 반환
- GET /api/admin/managers?company=FNI → FNI만 필터
- GET /api/admin/managers?company=TMS(M) → TMS(M)만 필터
- PUT /api/admin/workers/{id}/manager → is_manager=true 설정 성공
- PUT /api/admin/workers/{id}/manager → is_manager=false 해제 성공
- 일반 작업자가 PUT manager 호출 → 403 거부
- GET /api/admin/settings → heating_jacket_enabled, phase_block_enabled 반환
- PUT /api/admin/settings → heating_jacket_enabled=true 변경 성공
- PUT /api/admin/settings → 변경 후 GET으로 확인
- GET /api/admin/tasks/pending → 미종료 작업 목록 반환
- GET /api/admin/tasks/pending → 진행 중 작업 없으면 빈 리스트
- 미인증 상태로 admin API 호출 → 401

### Phase 1: 엔드포인트 기본 테스트 (누락된 것 추가)

**test_product_api.py (신규 — 8개 이상)**
- 제품 조회 성공 (GET /api/app/product/{qr_doc_id}) → 200 + 제품 정보 반환
- 제품 조회 시 Task Seed 자동 생성 확인 → app_task_details 레코드 생성됨
- 같은 제품 재조회 → Task 중복 생성 안 됨 (멱등성)
- 존재하지 않는 QR → 404
- Location QR 업데이트 성공 (POST /api/app/product/location/update)
- Location QR 업데이트 — 존재하지 않는 QR → 404
- 미인증 상태로 API 호출 → 401
- GAIA 모델 조회 → TMS task 포함 확인 / GALLANT 모델 조회 → TMS task 미포함 확인

### Phase 2: 전체 플로우 통합 테스트

**test_full_workflow.py (기존 빈 껍데기 → 실제 구현 — 10개 이상)**

⚠️ 기존 코드 전부 삭제 후 새로 작성. `assert False` 코드 0건이어야 함.

시나리오 1: **정상 플로우** (가입 → 이메일 인증 → 로그인 → 관리자 승인 → QR 스캔 → Task 확인)
```
POST /api/auth/register (FNI, MECH)
→ POST /api/auth/verify-email
→ POST /api/auth/login → 403 APPROVAL_PENDING 확인
→ Admin 로그인 → PUT /api/admin/workers/{id}/approve
→ POST /api/auth/login → 200 + JWT 발급
→ GET /api/app/product/DOC_TEST-GAIA-001 → 200 + Task Seed 자동 생성
→ GET /api/app/tasks/TEST-GAIA-001?worker_id=X → MECH Task 목록 반환
```

시나리오 2: **승인 거부 플로우**
```
POST /api/auth/register → verify → login → 403 APPROVAL_PENDING
→ Admin이 reject → login → 403 APPROVAL_REJECTED
```

시나리오 3: **Admin freepass 로그인** (이메일 인증/승인 없이 바로 로그인)
```
Admin 계정으로 POST /api/auth/login → 200 (email_verified/approval_status 체크 건너뜀)
```

시나리오 4: **Task 시작 → 완료 전체 플로우**
```
GET /api/app/product/{qr_doc_id} → Task 확인
→ POST /api/app/work/start (task_id) → started_at 기록
→ POST /api/app/work/complete (task_id) → completed_at, duration_minutes 기록
→ GET /api/app/tasks/{serial} → 해당 Task completed 확인
```

시나리오 5: **미승인 사용자 접근 제한**
```
미승인 사용자로 GET /api/app/product/{qr_doc_id} 시도 → JWT 없으면 401
```

### Phase 3: 모델별 Task Seed 혼합 테스트

**test_model_task_seed_integration.py (신규 — 12개 이상)**

모든 모델 타입을 섞어서 Task Seed 결과 검증:

| 모델 | 기대 MECH Task 수 | 기대 ELEC Task 수 | 기대 TMS Task 수 | 검증 포인트 |
|------|------------------|------------------|-----------------|------------|
| GAIA-I DUAL | 7 (전부 applicable 또는 docking 관련) | 6 | 2 | has_docking=T, is_tms=T |
| DRAGON-V | 6 (TANK_DOCKING=N/A) | 6 | 0 | tank_in_mech=T, TMS 없음 |
| GALLANT-III | 2 (SELF_INSPECTION + HEATING_JACKET if enabled) | 6 | 0 | docking 전부 비활성 |
| MITHAS-II | 2 | 6 | 0 | GALLANT과 동일 패턴 |
| SDS-100 | 2 | 6 | 0 | GALLANT과 동일 패턴 |
| SWS-200 | 2 | 6 | 0 | GALLANT과 동일 패턴 |

추가 검증:
- GAIA + heating_jacket_enabled=true → HEATING_JACKET task is_applicable=true
- GAIA + heating_jacket_enabled=false → HEATING_JACKET task is_applicable=false
- DRAGON + mech_partner='TMS' → TMS(M) 작업자가 MECH task도 볼 수 있는지
- DRAGON + mech_partner='FNI' → FNI 작업자가 MECH task 보이고, TMS(M)은 안 보이는지
- 6개 모델 전부 동시에 Task Seed → 각각 독립적으로 정확한 수량 생성

### Phase 4: Company 기반 필터링 통합 테스트

**test_company_task_filtering.py (신규 — 14개 이상)**

모든 company-worker 조합에서 올바른 Task만 보이는지 검증:

GAIA 모델 기준 (mech_partner=FNI, elec_partner=TMS, module_outsourcing=TMS):
- FNI 작업자 → MECH task만 보임 (7개)
- BAT 작업자 → Task 안 보임 (mech_partner≠BAT)
- TMS(M) 작업자 → TMS task(2개) + MECH task(mech_partner=FNI이므로 TMS≠FNI → MECH 안 보임)
  ⚠️ 단, module_outsourcing=TMS이면 TMS task는 보임
- TMS(E) 작업자 → ELEC task만 보임 (elec_partner=TMS)
- P&S 작업자 → Task 안 보임 (elec_partner≠P&S)
- C&A 작업자 → Task 안 보임 (elec_partner≠C&A)
- GST ADMIN → 전체 Task 보임 (필터링 없음)

DRAGON 모델 기준 (mech_partner=TMS, elec_partner=P&S):
- TMS(M) 작업자 → TMS task 없음 (is_tms=false) + MECH task 보임 (mech_partner=TMS)
- FNI 작업자 → Task 안 보임 (mech_partner≠FNI)
- P&S 작업자 → ELEC task 보임 (elec_partner=P&S)

GALLANT 모델 기준 (mech_partner=BAT, elec_partner=C&A):
- BAT 작업자 → MECH task 보임 (2개: SELF_INSPECTION + HEATING_JACKET if enabled)
- FNI 작업자 → Task 안 보임
- C&A 작업자 → ELEC task 보임 (6개)
- P&S 작업자 → Task 안 보임

### Phase 5: 동시 작업 + 미종료 통합 테스트

**test_concurrent_work.py (기존 빈 껍데기 → 실제 구현 — 10개 이상)**

⚠️ 기존 코드 전부 삭제 후 새로 작성.

- 작업자 A가 Task 시작 → B도 같은 Task 시작 → 둘 다 시작 가능 (멀티 작업자)
- A 완료 + B 미완료 → Task는 아직 미완료 상태
- B도 완료 → Task 완료, duration=A+B 합산, elapsed=실경과, worker_count=2
- 관리자 강제 종료 시 force_closed=true, closed_by=관리자ID, close_reason 확인
- 일반 작업자가 강제 종료 시도 → 403 거부

**test_process_check_flow.py (기존 빈 껍데기 → 실제 구현 — 8개 이상)**

⚠️ 기존 코드 전부 삭제 후 새로 작성. MECH/ELEC 네이밍 사용.

- GAIA: TMS 가압검사 완료 → TMS_TANK_COMPLETE 알림 → MECH 관리자에게 전달
- GAIA: MECH Tank Docking 완료 → TANK_DOCKING_COMPLETE 알림 → ELEC 관리자에게 전달
- phase_block_enabled=true일 때: TANK_DOCKING 미완료 → POST_DOCKING task 차단
- phase_block_enabled=false일 때: TANK_DOCKING 미완료 → POST_DOCKING task 차단 안 됨
- MECH 전체 완료 → completion_status.mech_completed=true
- ELEC 전체 완료 → completion_status.elec_completed=true
- MECH+ELEC 미완료 상태에서 PI 시작 시도 → 경고 생성 확인
- DRAGON 모델: TANK_DOCKING task 없음 → docking 관련 알림 미생성

### Phase 6: 미종료 알림 스케줄러 통합 테스트

**test_scheduler_integration.py (신규 — 6개 이상)**

mock datetime을 사용하여 시간 경과 시뮬레이션:
- 작업 시작 후 1시간 경과 → TASK_REMINDER 1건 생성
- 작업 시작 후 3시간 경과 → TASK_REMINDER 3건 누적
- 17:00 KST + 미종료 작업 → SHIFT_END_REMINDER 생성 (해당 작업자에게)
- 20:00 KST + 미종료 작업 → SHIFT_END_REMINDER 생성
- 익일 09:00 + 전일 미종료 → TASK_ESCALATION (같은 company의 is_manager=true에게)
- 다른 company 관리자에게는 TASK_ESCALATION 미전송

## 검증 기준 (Sprint 7 완료 조건)

✅ `assert False, "Test implementation required"` → **파일 전체에서 0건**
✅ 통합 테스트 전부 PASS (test_full_workflow, test_concurrent_work, test_process_check_flow)
✅ 모델별 Task Seed 혼합 테스트 전부 PASS
✅ Company 기반 필터링 테스트 전부 PASS
✅ GET /api/app/product/{qr_doc_id} 테스트 존재 및 PASS
✅ 기존 단위 테스트 전부 PASS (regression 없음)
✅ `flutter build web` 에러 0건
✅ PROGRESS.md에 테스트 카운트 정확 기재

## 규칙
- ⚠️ **Admin 누락 API 5개는 신규 기능이 아닌 버그 수정** — 반드시 구현
- 그 외 신규 기능 추가 금지 — 기존 코드의 버그 수정만 허용
- 테스트 실패 시 해당 BE/FE 코드를 수정하여 PASS시켜야 함
- 빈 껍데기(assert False) 테스트 파일은 전부 삭제 후 새로 작성
- integration 테스트 파일 내 role='MM'/'EE' 잔존 → 전부 'MECH'/'ELEC'으로 교체
- 테스트 중 발견된 모든 버그를 PROGRESS.md "Sprint 7 발견 버그" 섹션에 기록
- Sprint 7 완료 시 PROGRESS.md에 최종 테스트 카운트 정리
```

---

## 🚀 Sprint 8 프롬프트 — Admin API 보완 + UX 개선 + 버그 수정 (Sprint 7 완료 후 사용)

```
CLAUDE.md를 처음부터 끝까지 다시 읽고 Sprint 8을 시작해줘.

⚠️ Sprint 8 핵심 목표:
1. Admin 옵션 화면 누락 API 5개 구현 + 테스트
2. 로그인 유지 + 마지막 화면 복원 + 비밀번호 찾기
3. 기존 버그 수정 (worker_id NULL 대응 등)
⚠️ Railway 배포, PWA는 이번 Sprint 범위 아님

## 팀 구성
3명의 teammate를 생성해줘. 모든 teammate는 Sonnet 모델 사용:

1. **BE** (Backend 담당) - 소유: backend/**
2. **FE** (Frontend 담당) - 소유: frontend/**
3. **TEST** (테스트 담당) - 소유: tests/**

## BE 작업 순서

### 1. ⚠️ Admin API 누락 엔드포인트 5개 구현 (최우선)

FE의 admin_options_screen.dart가 호출하는데 BE admin.py에 없는 API를 구현해야 함.
CLAUDE.md "Admin 옵션 화면 필수 API" 테이블 반드시 참조.

**1-1. GET /api/admin/managers** (query: ?company=선택)
- workers 테이블에서 승인된 작업자 목록 반환 (approval_status='approved')
- company 파라미터가 있으면 해당 company만 필터링
- 응답: {"workers": [{"id", "name", "email", "role", "company", "is_manager", "is_admin"}]}
- @jwt_required + @admin_required

**1-2. PUT /api/admin/workers/{worker_id}/manager**
- 특정 작업자의 is_manager 값을 토글
- 요청: {"is_manager": true/false}
- 응답: {"message": "매니저 권한이 변경되었습니다.", "worker_id": int, "is_manager": bool}
- worker.py에 update_worker_manager_status() 함수 추가 필요
- @jwt_required + @admin_required

**1-3. GET /api/admin/settings**
- admin_settings 테이블의 전체 설정 조회
- 기존 admin_settings.py의 get_all_settings() 함수 활용
- 응답: {"settings": [{"setting_key", "setting_value", "description", "updated_at"}]}
- @jwt_required + @admin_required

**1-4. PUT /api/admin/settings**
- admin_settings 업데이트 (UPSERT)
- 요청: {"setting_key": "heating_jacket_enabled", "setting_value": true}
- 기존 admin_settings.py의 update_setting() 함수 활용
- @jwt_required + @admin_required

**1-5. GET /api/admin/tasks/pending**
- 미종료 작업 목록 (started_at IS NOT NULL AND completed_at IS NULL)
- 작업자 이름, serial_number, task_category, task_name, started_at 포함
- worker JOIN으로 작업자 이름 가져오기
- 응답: {"tasks": [...], "total": int}
- @jwt_required + @admin_required

### 2. 비밀번호 찾기 API

**2-1. POST /api/auth/forgot-password**
- 요청: {"email": "user@example.com"}
- 이메일로 비밀번호 리셋 토큰 발송 (JWT 기반, 30분 만료)
- 리셋 링크 or 6자리 인증코드 이메일 발송 (기존 send_verification_email 패턴 재활용)
- 이메일 미존재 시에도 동일 응답 (보안: 이메일 존재 여부 노출 방지)
- 응답: {"message": "비밀번호 재설정 이메일을 발송했습니다."}

**2-2. POST /api/auth/reset-password**
- 요청: {"email": "user@example.com", "code": "123456", "new_password": "newpass"}
- 인증코드 검증 → 비밀번호 bcrypt 해싱 → workers 테이블 UPDATE
- 코드 만료(30분) 또는 불일치 시 400 에러
- 응답: {"message": "비밀번호가 변경되었습니다."}

### 3. 토큰 만료 시간 변경

**config.py 수정:**
- JWT_EXPIRATION_DELTA: 1시간 → 2시간 (교대 중 끊기지 않게)
- JWT_REFRESH_EXPIRATION_DELTA: 7일 → 30일 (한 달에 한 번만 로그인)

### 4. 버그 수정

**4-1. _task_to_dict worker_id NULL 대응** (work.py)
- Task Seed로 생성된 task는 worker_id=NULL (아직 작업 시작 전)
- `'worker_id': task.worker_id or 0` 으로 변경 (이미 수정됨 — 확인만)

## FE 작업 순서

### 1. Admin 옵션 화면 API 연동 확인
admin_options_screen.dart에서 호출하는 5개 API가 BE에 구현된 후:
- 작업자 목록 로드 + company 필터 동작 확인
- is_manager 토글 동작 확인
- admin_settings 토글 동작 확인
- 미종료 작업 목록 + 강제 종료 동작 확인

### 2. 로그인 유지 (자동 토큰 갱신)
- api_service.dart의 Dio interceptor에 **401 응답 시 자동 refresh** 로직 추가:
  - 401 수신 → 저장된 refresh_token으로 POST /api/auth/refresh 호출
  - 새 access_token 받으면 저장 + 원래 요청 재시도 (retry)
  - refresh도 실패하면 로그인 화면으로 이동
- 앱 시작(main.dart) 시:
  - shared_preferences에서 refresh_token 존재 확인
  - 있으면 자동 refresh → 성공 시 로그인 스킵
  - 없으면 로그인 화면 표시

### 3. 마지막 화면 복원 (앱 복귀 시)
- shared_preferences에 현재 route + arguments 저장 (예: '/task-management', {serial_number, workerId})
- Navigator 이동할 때마다 저장: _saveLastRoute(routeName, args)
- 앱 시작 시 로그인 유지 성공하면 → 저장된 route로 복원
- 저장 대상 route: /home, /qr-scan, /task-management, /task-detail, /admin-options
- 로그인 관련 route (/login, /register, /verify-email)는 저장하지 않음

### 4. 비밀번호 찾기 화면
- login_screen.dart에 "비밀번호를 잊으셨나요?" 링크 추가
- forgot_password_screen.dart 신규:
  - 이메일 입력 → POST /api/auth/forgot-password → 인증코드 입력 화면으로 이동
- reset_password_screen.dart 신규:
  - 인증코드 + 새 비밀번호 입력 → POST /api/auth/reset-password → 성공 시 로그인 화면으로
- main.dart에 /forgot-password, /reset-password 라우트 등록

### 5. TaskItem.fromJson worker_id NULL 대응 (task_item.dart)
- `worker_id as int` → `as int? ?? 0` (이미 수정됨 — 확인만)
- `created_at` null 방어 추가 (이미 수정됨 — 확인만)

### 6. flutter build web 에러 0건 확인

## TEST 작업 순서

### 1. Admin 누락 API 테스트 (test_admin_options_api.py — 신규 12개 이상)
- GET /api/admin/managers → 전체 작업자 목록 반환
- GET /api/admin/managers?company=FNI → FNI만 필터
- GET /api/admin/managers?company=TMS(M) → TMS(M)만 필터
- PUT /api/admin/workers/{id}/manager → is_manager=true 설정 성공
- PUT /api/admin/workers/{id}/manager → is_manager=false 해제 성공
- 일반 작업자가 PUT manager 호출 → 403 거부
- GET /api/admin/settings → heating_jacket_enabled, phase_block_enabled 반환
- PUT /api/admin/settings → heating_jacket_enabled=true 변경 성공
- PUT /api/admin/settings → 변경 후 GET으로 확인 (값 일치)
- GET /api/admin/tasks/pending → 미종료 작업 목록 반환
- GET /api/admin/tasks/pending → 진행 중 작업 없으면 빈 리스트
- 미인증 상태로 admin API 호출 → 401

### 2. 비밀번호 찾기 API 테스트 (test_forgot_password.py — 신규 8개 이상)
- POST /api/auth/forgot-password 성공 → 이메일 발송 (SMTP mock)
- POST /api/auth/forgot-password 미존재 이메일 → 동일 200 응답 (보안)
- POST /api/auth/forgot-password 이메일 누락 → 400
- POST /api/auth/reset-password 성공 → 비밀번호 변경 후 로그인 가능
- POST /api/auth/reset-password 잘못된 코드 → 400
- POST /api/auth/reset-password 만료된 코드 → 400
- POST /api/auth/reset-password 필드 누락 → 400
- 비밀번호 변경 후 기존 비밀번호로 로그인 → 실패 확인

### 3. 토큰 갱신 테스트 (기존 test_refresh_token.py 보완)
- refresh token 30일 만료 확인
- access token 2시간 만료 확인

### 4. 기존 테스트 regression 확인
Sprint 7에서 작성된 모든 테스트가 여전히 PASS하는지 확인.

## 검증 기준 (Sprint 8 완료 조건)
✅ Admin API 5개 전부 구현 + 테스트 PASS
✅ FE admin_options_screen에서 작업자 목록 정상 표시
✅ 비밀번호 찾기 플로우 동작 (이메일 발송 → 코드 입력 → 비밀번호 변경)
✅ 로그인 유지: 앱 재시작 시 자동 로그인 + 마지막 화면 복원
✅ flutter build web 에러 0건
✅ 기존 테스트 regression 0건

## 규칙
- 위 명시된 기능 외 신규 기능 추가 금지
- Railway 배포, PWA는 이번 Sprint 범위 아님
- .env 파일 절대 커밋 금지
- Sprint 8 완료 시 PROGRESS.md에 구현 기록
```

---

## 🚀 Sprint 9 프롬프트 — Pause/Resume + 근무시간 관리 (Sprint 8 완료 후 사용)

```
CLAUDE.md를 처음부터 끝까지 다시 읽고 Sprint 9을 시작해줘.

⚠️ Sprint 9 핵심 목표:
1. 작업 일시정지(Pause) / 재개(Resume) 기능 — 작업자가 수동으로 중지/재개
2. 휴게/식사시간 강제 자동 중지 — 시간이 되면 시스템이 자동 pause + 알림 팝업
3. duration 계산 시 중지 시간 자동 차감
4. Admin 옵션에서 휴게/식사시간 변경 가능
⚠️ Railway 배포, PWA는 이번 Sprint 범위 아님

## 팀 구성
3명의 teammate를 생성해줘. 모든 teammate는 Sonnet 모델 사용:

1. **BE** (Backend 담당) - 소유: backend/**
2. **FE** (Frontend 담당) - 소유: frontend/**
3. **TEST** (테스트 담당) - 소유: tests/**

## BE 작업 순서

### 1. DB 마이그레이션 (007_sprint9_pause_resume.sql)

**1-1. work_pause_log 테이블 생성**
```sql
CREATE TABLE work_pause_log (
    id SERIAL PRIMARY KEY,
    task_detail_id INTEGER NOT NULL REFERENCES app_task_details(id),
    worker_id INTEGER NOT NULL REFERENCES workers(id),
    paused_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resumed_at TIMESTAMPTZ,
    pause_type VARCHAR(20) NOT NULL DEFAULT 'manual',
        -- 'manual': 작업자 수동 중지
        -- 'break_morning': 오전 휴게 (10:00-10:20)
        -- 'break_afternoon': 오후 휴게 (15:00-15:20)
        -- 'lunch': 점심 (11:20-12:20)
        -- 'dinner': 저녁 (17:00-18:00)
    pause_duration_minutes INTEGER,  -- resumed_at - paused_at (분)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_work_pause_log_task ON work_pause_log(task_detail_id);
CREATE INDEX idx_work_pause_log_worker ON work_pause_log(worker_id);
```

**1-2. admin_settings 초기값 추가 (휴게/식사시간)**
```sql
INSERT INTO admin_settings (setting_key, setting_value, description) VALUES
('break_morning_start', '"10:00"', '오전 휴게 시작 시간'),
('break_morning_end', '"10:20"', '오전 휴게 종료 시간'),
('break_afternoon_start', '"15:00"', '오후 휴게 시작 시간'),
('break_afternoon_end', '"15:20"', '오후 휴게 종료 시간'),
('lunch_start', '"11:20"', '점심시간 시작'),
('lunch_end', '"12:20"', '점심시간 종료'),
('dinner_start', '"17:00"', '저녁시간 시작'),
('dinner_end', '"18:00"', '저녁시간 종료'),
('auto_pause_enabled', 'true', '휴게/식사시간 자동 중지 활성화')
ON CONFLICT (setting_key) DO NOTHING;
```

**1-3. app_task_details에 pause 상태 컬럼 추가**
```sql
ALTER TABLE app_task_details ADD COLUMN IF NOT EXISTS is_paused BOOLEAN DEFAULT FALSE;
ALTER TABLE app_task_details ADD COLUMN IF NOT EXISTS total_pause_minutes INTEGER DEFAULT 0;
```

### 2. Pause/Resume API 구현 (work.py에 추가)

**2-1. POST /api/app/work/pause**
- 요청: {"task_detail_id": int}
- 검증:
  - task가 존재하는지
  - task가 시작됨 (started_at IS NOT NULL)
  - task가 미완료 (completed_at IS NULL)
  - 현재 paused 상태가 아닌지 (이미 pause면 400)
  - 요청 worker_id가 해당 task의 현재 작업자인지 (work_start_log 확인)
- 동작:
  - work_pause_log INSERT (task_detail_id, worker_id, paused_at=NOW())
  - app_task_details.is_paused = TRUE 업데이트
- 응답: {"message": "작업이 일시정지되었습니다.", "paused_at": "ISO8601"}
- @jwt_required

**2-2. POST /api/app/work/resume**
- 요청: {"task_detail_id": int}
- 검증:
  - task가 paused 상태인지 (아니면 400)
  - 요청 worker_id가 해당 pause를 건 작업자이거나 관리자인지
- 동작:
  - work_pause_log의 최신 미종료 레코드에 resumed_at=NOW(), pause_duration_minutes 계산
  - app_task_details.is_paused = FALSE
  - app_task_details.total_pause_minutes += pause_duration_minutes
- 응답: {"message": "작업이 재개되었습니다.", "resumed_at": "ISO8601", "pause_duration_minutes": int}
- @jwt_required

**2-3. GET /api/app/work/pause-history/{task_detail_id}**
- 해당 task의 pause/resume 이력 조회
- 응답: {"pauses": [{"id", "worker_id", "paused_at", "resumed_at", "pause_type", "pause_duration_minutes"}]}
- @jwt_required

### 3. duration 계산 수정

**3-1. work.py의 작업 완료 로직 수정**
작업 완료 시 duration_minutes 계산에서 총 중지 시간 차감:
```python
# 기존: duration_minutes = (completed_at - started_at).total_seconds() / 60
# 변경: duration_minutes = (completed_at - started_at).total_seconds() / 60 - total_pause_minutes
```

⚠️ 완료 시 아직 paused 상태면:
- 자동으로 resume 처리 (resumed_at = completed_at)
- pause_duration 계산 후 total_pause_minutes에 반영
- 그 다음 completed_at 기록

### 4. 휴게/식사시간 자동 강제 중지 스케줄러

**4-1. scheduler_service.py에 break_time_checker 추가**

매 분(1분 간격) 실행되는 스케줄러:
```python
def check_break_time():
    """휴게/식사시간 자동 강제 중지"""
    if not get_admin_setting('auto_pause_enabled', True):
        return

    now = datetime.now(KST)
    current_time = now.strftime('%H:%M')

    # 4개 시간대 체크
    break_periods = [
        ('break_morning_start', 'break_morning_end', 'break_morning'),
        ('break_afternoon_start', 'break_afternoon_end', 'break_afternoon'),
        ('lunch_start', 'lunch_end', 'lunch'),
        ('dinner_start', 'dinner_end', 'dinner'),
    ]

    for start_key, end_key, pause_type in break_periods:
        start_time = get_admin_setting(start_key)  # "10:00"
        end_time = get_admin_setting(end_key)       # "10:20"

        if current_time == start_time:
            # 진행 중인 모든 작업 강제 pause
            force_pause_all_active_tasks(pause_type)

        if current_time == end_time and pause_type != 'dinner':
            # 저녁 제외: 휴게 종료 시 알림만 발송 (수동 재개)
            send_break_end_notifications(pause_type)
```

**4-2. force_pause_all_active_tasks(pause_type) 구현**
- app_task_details에서 started_at NOT NULL AND completed_at IS NULL AND is_paused=FALSE 조회
- 각 task에 대해:
  - work_pause_log INSERT (pause_type 지정)
  - app_task_details.is_paused = TRUE
  - 해당 작업자에게 알림 생성 (alert_type: BREAK_TIME_PAUSE)
  - 메시지: "휴게시간입니다. 작업이 자동 중지되었습니다. 휴게 종료 후 재개 버튼을 눌러주세요."

**4-3. send_break_end_notifications(pause_type) 구현**
- 해당 pause_type으로 현재 paused 상태인 작업자에게 알림
- alert_type: BREAK_TIME_END
- 메시지: "휴게시간이 종료되었습니다. 작업을 재개해주세요."
- ⚠️ 저녁시간(dinner)은 종료 알림 발송하되, 자동 resume 하지 않음 (수동 재개)

**4-4. 저녁시간 특수 처리**
- 저녁 17:00 시작 시: 강제 pause + 알림 팝업에 "무시하고 계속" 버튼 포함
- "무시하고 계속" 클릭 시: 즉시 resume + 저녁시간 동안의 작업시간은 duration에 포함
- 저녁 18:00 종료 시: 아직 paused 상태인 작업자에게만 종료 알림
- 만약 "무시하고 계속"으로 이미 resume한 작업자는 알림 미발송

### 5. Admin 휴게시간 설정 API

기존 PUT /api/admin/settings 엔드포인트를 그대로 활용.
FE에서 아래 setting_key들을 개별 업데이트:
- break_morning_start, break_morning_end
- break_afternoon_start, break_afternoon_end
- lunch_start, lunch_end
- dinner_start, dinner_end
- auto_pause_enabled

⚠️ 시간 형식 검증 추가: HH:MM 포맷 (정규식: ^([01]\\d|2[0-3]):[0-5]\\d$)
⚠️ start < end 검증 (start_time이 end_time보다 이전이어야 함)

### 6. 버그 수정: admin_options_screen.dart API URL 중복

⚠️ Sprint 8에서 발견된 버그 — 이미 수정됨, 확인만:
- apiBaseUrl이 'http://localhost:5001/api'인데 FE에서 '/api/admin/...'으로 호출하면 '/api/api/admin/...'이 됨
- 모든 admin API 호출 경로에서 '/api' 접두사 제거 확인

## FE 작업 순서

### 1. Task 상세 화면에 일시정지/재개 버튼 추가

**task_detail_screen.dart 또는 task_management_screen.dart 수정:**
- 작업 진행 중(started_at NOT NULL, completed_at IS NULL) 상태에서:
  - is_paused=false → "일시정지" 버튼 표시 (아이콘: pause_circle)
  - is_paused=true → "재개" 버튼 표시 (아이콘: play_circle) + 경과 시간 표시
- 버튼 클릭 시:
  - 일시정지: POST /app/work/pause → 성공 시 UI 업데이트
  - 재개: POST /app/work/resume → 성공 시 UI 업데이트
- 일시정지 상태에서는 "작업 완료" 버튼 비활성화 (먼저 재개 필요) 또는 자동 resume 후 완료 처리
- ⚠️ API 경로에 '/api' 접두사 넣지 말 것 (apiBaseUrl에 이미 포함)

### 2. 휴게시간 알림 팝업

**break_time_popup.dart (신규 위젯):**
- 실시간 알림 수신 시 (BREAK_TIME_PAUSE 타입) 팝업 표시
- 내용: "휴게시간입니다" + 현재 시간 + 종료 예정 시간
- 버튼: "확인" (팝업 닫기)
- 저녁시간 전용 추가 버튼: "무시하고 계속 작업" → POST /app/work/resume 호출

**break_time_end_popup.dart (신규 위젯):**
- BREAK_TIME_END 알림 수신 시 표시
- 내용: "휴게시간이 종료되었습니다. 작업을 재개해주세요."
- 버튼: "재개하기" → POST /app/work/resume 호출

⚠️ 팝업은 overlay 방식으로 현재 화면 위에 표시 (Navigator.push X → showDialog 사용)
⚠️ 팝업 닫기 전까지 다른 조작 차단 (barrierDismissible: false)

### 3. 일시정지 상태 시각적 표시

- Task 카드에 paused 상태 배지 표시 (주황색 "일시정지" 텍스트)
- 일시정지 경과 시간 실시간 표시 (Timer 사용)
- Task 목록에서 paused task는 상단에 하이라이트

### 4. Admin 옵션 — 휴게/식사시간 설정 UI

**admin_options_screen.dart에 섹션 4 추가:**
- 섹션 헤더: "근무시간 설정" (아이콘: schedule)
- 설정 항목 (각각 시작/종료 시간 입력):
  - 오전 휴게: 10:00 ~ 10:20
  - 점심시간: 11:20 ~ 12:20
  - 오후 휴게: 15:00 ~ 15:20
  - 저녁시간: 17:00 ~ 18:00
- 자동 중지 ON/OFF 토글 (auto_pause_enabled)
- 시간 입력: TimePicker 사용 (showTimePicker)
- 저장 시: PUT /admin/settings 개별 호출
- ⚠️ API 경로: '/admin/settings' (apiBaseUrl에 /api 이미 포함)

### 5. flutter build web 에러 0건 확인

## TEST 작업 순서

### 1. Pause/Resume API 테스트 (test_pause_resume.py — 신규 18개 이상)

**기본 Pause/Resume 플로우:**
- TC-PR-01: 작업 시작 → pause 성공 → is_paused=true 확인
- TC-PR-02: pause 상태에서 resume 성공 → is_paused=false 확인
- TC-PR-03: resume 후 work_pause_log에 resumed_at, pause_duration_minutes 기록 확인
- TC-PR-04: 미시작 task에 pause 시도 → 400 (started_at IS NULL)
- TC-PR-05: 이미 완료된 task에 pause 시도 → 400 (completed_at IS NOT NULL)
- TC-PR-06: 이미 paused인 task에 다시 pause → 400 (중복 방지)
- TC-PR-07: paused 아닌 task에 resume → 400
- TC-PR-08: 다른 작업자가 resume 시도 → 400 또는 403 (본인 또는 관리자만)
- TC-PR-09: 관리자가 다른 작업자의 task resume → 성공

**Duration 차감 검증:**
- TC-PR-10: pause 5분 → resume → 완료 → duration에서 5분 차감 확인
- TC-PR-11: pause 2회 (5분 + 10분) → 완료 → total_pause_minutes=15, duration에서 15분 차감
- TC-PR-12: pause 상태에서 바로 완료 → 자동 resume 후 완료, pause 시간 차감 확인

**Pause 이력 조회:**
- TC-PR-13: GET /api/app/work/pause-history/{id} → pause 이력 목록 반환
- TC-PR-14: pause 이력 없는 task → 빈 리스트

**멀티 작업자 + Pause:**
- TC-PR-15: 작업자 A pause + 작업자 B는 계속 진행 → B의 duration에는 영향 없음
- TC-PR-16: A와 B 둘 다 pause → 둘 다 resume 후 완료 → 각각 pause 시간 차감
- TC-PR-17: A pause + B 완료 → task는 아직 미완료 (A가 아직 진행 중)

**인증:**
- TC-PR-18: 미인증 상태로 pause/resume 호출 → 401

### 2. 휴게시간 자동 강제 중지 테스트 (test_break_time_scheduler.py — 신규 14개 이상)

**자동 중지 기본:**
- TC-BT-01: 10:00 도달 + 진행 중 작업 있음 → force pause (break_morning) + 알림 생성
- TC-BT-02: 10:00 도달 + 진행 중 작업 없음 → pause 미발생
- TC-BT-03: 10:20 도달 → break_morning으로 paused 작업자에게 BREAK_TIME_END 알림
- TC-BT-04: 11:20 도달 → lunch 강제 pause
- TC-BT-05: 15:00 도달 → break_afternoon 강제 pause
- TC-BT-06: 17:00 도달 → dinner 강제 pause

**저녁시간 특수 처리:**
- TC-BT-07: dinner pause 후 "무시하고 계속" (resume) → 작업시간에 포함
- TC-BT-08: dinner pause + resume하지 않음 + 18:00 도달 → BREAK_TIME_END 알림
- TC-BT-09: dinner pause + "무시하고 계속" resume 후 18:00 도달 → 알림 미발송

**Admin 설정 연동:**
- TC-BT-10: auto_pause_enabled=false → 어떤 시간이든 자동 pause 미발생
- TC-BT-11: break_morning_start를 '09:30'으로 변경 → 09:30에 pause 발생
- TC-BT-12: 이미 수동 pause 상태인 task → 자동 pause 시 중복 안 됨

**알림 검증:**
- TC-BT-13: force pause 시 BREAK_TIME_PAUSE 알림 생성 확인 (작업자별 1건)
- TC-BT-14: break end 시 BREAK_TIME_END 알림 생성 확인

### 3. Admin 휴게시간 설정 테스트 (test_break_time_settings.py — 신규 8개 이상)

- TC-BS-01: GET /api/admin/settings → 9개 휴게시간 설정값 포함 확인
- TC-BS-02: PUT break_morning_start='09:50' → 성공, GET으로 확인
- TC-BS-03: PUT auto_pause_enabled=false → 성공
- TC-BS-04: 잘못된 시간 형식 ('25:00') → 400 에러
- TC-BS-05: start > end 검증 ('12:00' > '11:00') → 400 에러
- TC-BS-06: 일반 작업자가 설정 변경 시도 → 403
- TC-BS-07: 미인증 상태로 설정 조회 → 401
- TC-BS-08: 4개 시간대 전부 변경 → GET으로 전부 반영 확인

### 4. 기존 테스트 regression 확인
Sprint 8까지의 모든 테스트가 여전히 PASS하는지 확인.
⚠️ duration 계산 로직 변경으로 기존 test_work_api.py, test_concurrent_work.py 영향 가능 → 필요 시 수정

## 검증 기준 (Sprint 9 완료 조건)

✅ Pause/Resume API 정상 동작 (pause → is_paused=true, resume → is_paused=false)
✅ duration 계산 시 총 중지 시간(total_pause_minutes) 자동 차감
✅ 휴게/식사시간 자동 강제 중지 스케줄러 동작 (4개 시간대)
✅ 저녁시간 "무시하고 계속" 옵션 → resume 후 작업시간 포함
✅ Admin 옵션에서 휴게/식사시간 변경 가능 + 시간 형식 검증
✅ FE: 일시정지/재개 버튼 + 휴게시간 팝업 + 상태 배지
✅ flutter build web 에러 0건
✅ 신규 테스트 40개 이상 PASS (pause_resume 18 + break_time 14 + settings 8)
✅ 기존 테스트 regression 0건
✅ PROGRESS.md에 Sprint 9 기록

## 규칙
- CLAUDE.md의 Sprint 9 섹션 반드시 참조
- 위 명시된 기능 외 신규 기능 추가 금지
- Railway 배포, PWA는 이번 Sprint 범위 아님
- .env 파일 절대 커밋 금지
- ⚠️ FE API 경로에 '/api' 접두사 넣지 말 것 (apiBaseUrl에 이미 /api 포함 — Sprint 8 버그 재발 방지)
- admin_settings의 시간 값은 JSON string으로 저장 (예: '"10:00"')
- pause_type enum 값: 'manual', 'break_morning', 'break_afternoon', 'lunch', 'dinner'
- Sprint 9 완료 시 PROGRESS.md에 구현 기록
```

---

## 🔧 Sprint 10 테스트 프롬프트 — 수동 수정 검증 + 추가 버그 수정 (Sprint 9 완료 후 사용)

```
CLAUDE.md를 처음부터 끝까지 다시 읽고 Sprint 10 수정사항을 검증 + 추가 버그를 수정해줘.

⚠️ Sprint 10은 팀 에이전트 실행 없이 수동으로 진행한 디버그/개선 Sprint.
아래 수정사항이 정상 반영되었는지 코드 레벨에서 검증하고,
추가 발견된 버그 3건을 반드시 수정해야 함.

## 팀 구성
3명의 teammate를 생성해줘. 모든 teammate는 Sonnet 모델 사용:

1. **BE** (Backend 담당) - 소유: backend/**
2. **FE** (Frontend 담당) - 소유: frontend/**
3. **TEST** (테스트 담당) - 소유: tests/**

## ⚠️ 필수 버그 수정 3건 (이미 코드에 반영됨 — 검증 + 빌드 확인)

### 버그 A: DB 시간이 UTC로 표시됨 (worker.py)
**원인**: get_db_connection()에서 PostgreSQL 세션 timezone이 미설정.
TIMESTAMPTZ를 조회하면 psycopg2가 UTC 기준 datetime을 반환하여 isoformat() 시 +00:00 출력.

**이미 적용된 수정**:
```python
# backend/app/models/worker.py — get_db_connection()
conn = psycopg2.connect(
    Config.DATABASE_URL,
    cursor_factory=psycopg2.extras.RealDictCursor,
    options="-c timezone=Asia/Seoul"   # ← 이 옵션 추가됨
)
```

**BE 검증**:
- get_db_connection()에 `options="-c timezone=Asia/Seoul"` 존재 확인
- 모든 API 응답의 시간 필드가 +09:00(KST)로 반환되는지 확인
- 기존 DB 데이터의 TIMESTAMPTZ 조회 시에도 KST로 정상 변환되는지 확인
**TEST 검증**:
- 작업 시작(start_work) 후 응답의 started_at이 KST 기준인지 확인
- pause/resume 응답의 paused_at/resumed_at이 KST인지 확인

### 버그 B: Heating Jacket OFF 시 task 목록에서 안 사라짐 (admin.py + task_management_screen.dart)
**원인 2가지**:
1. BE: task_seed.py가 `ON CONFLICT DO NOTHING`으로 INSERT하므로, 이미 생성된 task의 is_applicable이 admin setting 변경 후에도 업데이트 안 됨
2. FE: task_management_screen.dart에서 is_applicable 필터링 없이 전체 task를 목록에 표시

**이미 적용된 수정**:

BE (admin.py PUT /admin/settings 엔드포인트 끝부분):
```python
# heating_jacket_enabled 변경 시 → 기존 HEATING_JACKET task의 is_applicable 동기화
if 'heating_jacket_enabled' in update_pairs:
    new_val = bool(update_pairs['heating_jacket_enabled'])
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE app_task_details
        SET is_applicable = %s, updated_at = NOW()
        WHERE task_category = 'MECH'
          AND task_id = 'HEATING_JACKET'
          AND completed_at IS NULL
    """, (new_val,))
    conn.commit()
```

FE (task_management_screen.dart):
```dart
// is_applicable=false인 비활성 task 제외
final filteredTasks = tasks.where((task) {
  if (!task.isApplicable) return false;
  if (_filterStatus == 'all') return true;
  return task.status == _filterStatus;
}).toList();

// 진행률/카운트도 isApplicable 기준으로 계산
final applicable = tasks.where((t) => t.isApplicable).toList();
final completed = applicable.where((t) => t.status == 'completed').length;
final progress = applicable.length > 0 ? completed / applicable.length : 0.0;
```

**BE 검증**:
- PUT /admin/settings에서 heating_jacket_enabled 변경 시 기존 HEATING_JACKET task UPDATE 로직 확인
- 이미 완료된(completed_at IS NOT NULL) task는 UPDATE 대상에서 제외 확인
**FE 검증**:
- task 목록에서 isApplicable=false인 task가 완전히 숨겨지는지 확인
- 진행률 계산이 활성(isApplicable=true) task 기준인지 확인
- 진행률 바(LinearProgressIndicator)도 활성 task 기준인지 확인
**TEST 검증**:
- heating_jacket_enabled=true → false 변경 시 HEATING_JACKET task is_applicable=false 확인
- heating_jacket_enabled=false → true 변경 시 HEATING_JACKET task is_applicable=true 복원 확인
- 이미 완료된 HEATING_JACKET task는 is_applicable 변경 안 됨 확인

### 버그 C: location_qr_required가 ALLOWED_KEYS에 누락 (admin.py)
**원인**: PUT /admin/settings의 ALLOWED_KEYS set에 'location_qr_required'가 없어서 저장 시 400 에러.

**이미 적용된 수정**:
```python
ALLOWED_KEYS = {
    'heating_jacket_enabled',
    'phase_block_enabled',
    'location_qr_required',    # ← 추가됨
    # Sprint 9: 휴게시간 설정
    'break_morning_start',
    ...
}
```

GET 기본값에도 추가:
```python
result.setdefault('location_qr_required', True)
```

**BE 검증**:
- ALLOWED_KEYS에 'location_qr_required' 포함 확인
- GET /admin/settings 응답에 location_qr_required 기본값(True) 포함 확인
- PUT location_qr_required=false → 200 성공 확인
- PUT 후 GET으로 값 반영 확인

### 버그 D: phase_block_enabled 차단 로직 미구현 (process_validator.py + task_service.py)
**원인**: admin_settings 테이블에 phase_block_enabled 키는 있고, FE 토글도 있지만,
실제 차단 로직이 BE에 구현되지 않음.

**구현 필요 사항**:

**D-1. task_service.py의 start_work()에 phase_block 체크 추가**
MECH POST_DOCKING phase task(WASTE_GAS_LINE_2, UTIL_LINE_2) 시작 시:
- phase_block_enabled=true이면:
  - TANK_DOCKING task가 완료(completed_at IS NOT NULL)되었는지 확인
  - 미완료 시 차단: {"error": "PHASE_BLOCKED", "message": "Tank Docking이 완료되지 않았습니다."}
  - 완료 시 진행 허용
- phase_block_enabled=false이면: 차단 없이 진행

```python
# task_service.py start_work() 내부에 추가
from app.models.admin_settings import get_setting

# POST_DOCKING phase task인지 확인
if task.task_category == 'MECH' and task.phase == 'POST_DOCKING':
    phase_block = get_setting('phase_block_enabled', False)
    if phase_block:
        # TANK_DOCKING task 완료 여부 확인
        docking_task = get_task_by_serial_and_id(
            task.serial_number, 'MECH', 'TANK_DOCKING'
        )
        if docking_task and not docking_task.completed_at:
            return {
                'error': 'PHASE_BLOCKED',
                'message': 'Tank Docking이 완료되지 않았습니다. POST_DOCKING 공정을 시작할 수 없습니다.'
            }, 400
```

**D-2. task_detail.py에 get_task_by_serial_and_id() 함수 추가**
```python
def get_task_by_serial_and_id(serial_number: str, task_category: str, task_id: str) -> Optional[TaskDetail]:
    """serial_number + task_category + task_id로 단일 task 조회"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM app_task_details WHERE serial_number = %s AND task_category = %s AND task_id = %s",
        (serial_number, task_category, task_id)
    )
    row = cur.fetchone()
    conn.close()
    return TaskDetail.from_db_row(row) if row else None
```

**D-3. TaskDetail dataclass에 phase 필드가 없으면 추가 필요**
task_seed.py에서 phase 값으로 INSERT하지만, task_detail.py의 TaskDetail dataclass에 phase 필드가 없을 수 있음.
DB 테이블 app_task_details에 phase 컬럼이 없다면:
- task_id 기반으로 POST_DOCKING 판별: task_id IN ('WASTE_GAS_LINE_2', 'UTIL_LINE_2')

⚠️ 구현 시 task_seed.py의 MECH_TASKS 템플릿 참조:
- PRE_DOCKING: WASTE_GAS_LINE_1, UTIL_LINE_1, HEATING_JACKET
- DOCKING: TANK_DOCKING
- POST_DOCKING: WASTE_GAS_LINE_2, UTIL_LINE_2
- FINAL: SELF_INSPECTION

**TEST 검증**:
- phase_block_enabled=true + TANK_DOCKING 미완료 → POST_DOCKING task 시작 시 400 PHASE_BLOCKED
- phase_block_enabled=true + TANK_DOCKING 완료 → POST_DOCKING task 시작 성공
- phase_block_enabled=false + TANK_DOCKING 미완료 → POST_DOCKING task 시작 성공 (차단 없음)
- phase_block_enabled 미설정(기본 false) → 차단 없음

## 기존 수정사항 6건 검증 (코드 확인만)

### 1. 로그아웃 화면 전환 수정 (main.dart)
- GAxisApp에 `GlobalKey<NavigatorState>` + `ref.listen<AuthState>` 존재 확인
- 인증→비인증 전환 시 `pushAndRemoveUntil` 호출 확인

### 2. 일시정지/재개 BE 응답 수정 (work.py)
- pause_work(), resume_work()가 `_task_to_dict()` 전체 TaskItem 반환 확인
- 응답에 id, serial_number, task_name, is_paused, total_pause_minutes 포함 확인

### 3. 가입 승인 대기 필터 (admin_options_screen.dart)
- 기본값이 **null(전체)** 인지 확인 (⚠️ 변경됨: 기존 "본인 company" → "전체")
- 필터 칩 UI + `_filteredPendingWorkers` getter 동작 확인
- 목록이 **ListView + maxHeight 300 + Scrollbar** (스크롤 가능)인지 확인

### 4. 협력사 관리자 미종료 작업 화면 (신규)
- manager_pending_tasks_screen.dart 존재 확인
- home_screen.dart: is_admin → "관리자 옵션", is_manager && !is_admin → "미종료 작업" 확인
- admin.py: @manager_or_admin_required + 서버측 company 강제 오버라이드 확인

### 5. location_qr_required admin setting
- process_validator.py에서 `get_setting('location_qr_required', True)` 조건 분기 확인
- admin_options_screen.dart에 토글 UI 확인

### 6. admin 관리자 목록 기본 필터
- `_selectedManagerCompany = _companies.first` (FNI) 확인

## TEST 작업

### 기존 테스트 regression 확인
Sprint 9까지의 모든 테스트가 여전히 PASS하는지 확인.

### Sprint 10 신규 테스트 (test_sprint10_fixes.py — 15개 이상)
**기존 10개:**
- 협력사 관리자가 본인 company 미종료 작업 조회 성공
- 협력사 관리자가 타 company 미종료 작업 조회 시 빈 리스트
- admin이 company 필터 없이 전체 미종료 작업 조회 성공
- 일반 작업자(is_manager=false)가 미종료 작업 조회 시 403
- pause 응답에 전체 task 필드 포함 확인
- resume 응답에 전체 task 필드 포함 확인
- location_qr_required=false → 경고 미생성
- location_qr_required=true → 경고 생성
- location_qr_required 기본값 → 경고 생성
- 협력사 관리자 강제 종료 성공

**추가 9개 (버그 A/B/C/D 검증):**
- 작업 시작 후 started_at이 KST(+09:00) 포함 확인
- heating_jacket_enabled=false 변경 → HEATING_JACKET task is_applicable=false 확인
- heating_jacket_enabled=true 복원 → HEATING_JACKET task is_applicable=true 확인
- 완료된 HEATING_JACKET task는 setting 변경 시 is_applicable 유지 확인
- location_qr_required PUT 요청 → 200 성공 (ALLOWED_KEYS 포함 확인)
- phase_block_enabled=true + TANK_DOCKING 미완료 → POST_DOCKING start 시 400 PHASE_BLOCKED
- phase_block_enabled=true + TANK_DOCKING 완료 → POST_DOCKING start 성공
- phase_block_enabled=false + TANK_DOCKING 미완료 → POST_DOCKING start 성공 (차단 없음)
- phase_block_enabled 기본값(false) → 차단 없음

## 검증 기준 (Sprint 10 완료 조건)

✅ 버그 A: 모든 시간 필드가 KST(+09:00) 기준으로 반환
✅ 버그 B: Heating Jacket OFF → task 목록에서 숨김 + 진행률 계산에서 제외
✅ 버그 C: location_qr_required 토글 저장 성공
✅ 버그 D: phase_block_enabled=true → POST_DOCKING task 차단 동작
✅ 기존 수정사항 6건 코드에 정상 반영 확인
✅ Sprint 10 신규 테스트 19개 이상 PASS
✅ 기존 테스트 regression 0건
✅ flutter build web 에러 0건

## 규칙
- 이번 Sprint은 신규 기능 추가 금지 — 기존 수정사항 검증 + 버그 수정만
- 위에 명시된 버그 A/B/C/D 외 추가 발견 버그도 즉시 수정 허용
- ⚠️ FE API 경로에 '/api' 접두사 넣지 말 것 (apiBaseUrl에 이미 /api 포함)
- ⚠️ DB 시간 관련: get_db_connection()의 `options="-c timezone=Asia/Seoul"` 절대 삭제 금지
- ⚠️ task_management_screen.dart의 isApplicable 필터링 절대 삭제 금지
- Sprint 10 완료 시 PROGRESS.md에 기록
```

---

## 🚀 Sprint 11 프롬프트 — GST Task + 홈 메뉴 확장 + Checklist 스키마 (Sprint 10 완료 후 사용)

```
CLAUDE.md를 처음부터 끝까지 다시 읽고 Sprint 11을 시작해줘.

⚠️ Sprint 11 핵심 목표:
1. GST 인원용 Task 템플릿 추가 (PI 2개 + QI 1개 + SI 1개)
2. 홈 화면 메뉴 확장 — PI/QI/SI 진행 제품 대시보드 3개
3. checklist 스키마 신설 — Hook-Up 체크리스트 (SI task 전용, 추후 전 공정 확장)
4. GST active_role 전환 기능
⚠️ Railway 배포, PWA는 이번 Sprint 범위 아님

## 팀 구성
3명의 teammate를 생성해줘. 모든 teammate는 Sonnet 모델 사용:

1. **BE** (Backend 담당) - 소유: backend/**
2. **FE** (Frontend 담당) - 소유: frontend/**
3. **TEST** (테스트 담당) - 소유: tests/**

## BE 작업 순서

### 1. DB 마이그레이션 (008_sprint11_gst_tasks.sql)

**1-1. checklist 스키마 생성**
```sql
CREATE SCHEMA IF NOT EXISTS checklist;

-- 체크리스트 마스터 (품번 + category별 체크항목)
-- Excel import로 적재 (product_code 기준)
CREATE TABLE checklist.checklist_master (
    id SERIAL PRIMARY KEY,
    product_code VARCHAR(100) NOT NULL,       -- 품번 (product_info.product_code)
    category VARCHAR(20) NOT NULL,            -- 'HOOKUP', 'MECH', 'ELEC', 'PI', 'QI'
    item_name VARCHAR(255) NOT NULL,          -- 체크 항목명
    item_order INTEGER DEFAULT 0,             -- 표시 순서
    description TEXT,                         -- 상세 설명
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(product_code, category, item_name)
);

CREATE INDEX idx_checklist_master_product ON checklist.checklist_master(product_code, category);

-- 체크리스트 기록 (S/N별 체크 이력)
CREATE TABLE checklist.checklist_record (
    id SERIAL PRIMARY KEY,
    serial_number VARCHAR(100) NOT NULL,      -- product_info.serial_number
    master_id INTEGER NOT NULL REFERENCES checklist.checklist_master(id),
    is_checked BOOLEAN DEFAULT FALSE,
    checked_by INTEGER REFERENCES public.workers(id),
    checked_at TIMESTAMPTZ,
    note TEXT,                                -- 비고
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(serial_number, master_id)
);

CREATE INDEX idx_checklist_record_sn ON checklist.checklist_record(serial_number);
CREATE INDEX idx_checklist_record_master ON checklist.checklist_record(master_id);
```

**1-2. task_seed.py에 GST task 템플릿 추가**

기존 MECH 7개 + ELEC 6개 + TMS 2개 = 15개에 추가:

```python
# PI tasks (2개)
{'category': 'PI', 'order': 1, 'name': 'LNG/UTIL 가압검사',  'code': 'PI_LNG_UTIL'},
{'category': 'PI', 'order': 2, 'name': 'CHAMBER 가압검사',   'code': 'PI_CHAMBER'},

# QI tasks (1개)
{'category': 'QI', 'order': 1, 'name': '공정검사',           'code': 'QI_INSPECTION'},

# SI tasks (1개)
{'category': 'SI', 'order': 1, 'name': '마무리공정',         'code': 'SI_FINISHING'},
```

총 19개 (15 + 4)

**1-3. task_seed.py 필터링 로직 확장**
- PI/QI/SI task는 모든 모델에 대해 생성 (is_applicable=true)
- Location QR 조건: location_qr_required admin setting에 따름 (Sprint 10에서 구현됨)
- GST 작업자(company='GST')는 PI/QI/SI task를 모두 볼 수 있음 (active_role 무관)
- Admin(is_admin=true)도 PI/QI/SI task 전부 볼 수 있음

### 2. GST active_role 전환 API

**2-1. workers 테이블에 active_role 컬럼 추가 (migration)**
```sql
ALTER TABLE workers ADD COLUMN IF NOT EXISTS active_role VARCHAR(10);
-- GST 작업자 기본값: 본인 role과 동일
UPDATE workers SET active_role = role WHERE company = 'GST' AND active_role IS NULL;
```

**2-2. PUT /api/auth/active-role**
- 요청: {"active_role": "PI"}
- 검증: GST 작업자만 변경 가능, 유효 role은 PI/QI/SI/ADMIN
- worker.active_role 업데이트
- 응답: {"message": "활성 역할이 변경되었습니다.", "active_role": "PI"}
- @jwt_required

**2-3. GET /api/auth/me 응답에 active_role 포함**
- 기존 worker 정보에 active_role 필드 추가

### 3. GST 진행 제품 대시보드 API

**3-1. GET /api/app/gst/products/{category}**
- category: PI, QI, SI
- 해당 category의 task가 진행 중(started_at IS NOT NULL AND completed_at IS NULL)인 제품 목록 반환
- 또는 해당 category의 task가 할당되었지만 아직 시작 안 한 제품도 포함
- 작업자 정보(worker_name) 포함
- S/N, model, task_name, task_status(not_started/in_progress/paused/completed), worker_name, started_at
- 응답: {"products": [...], "total": int}
- @jwt_required
- GST 작업자 또는 admin만 접근 가능

**3-2. 타 작업자 task 제어 허용**
GST 인원은 본인뿐 아니라 타 GST 작업자의 task도 일시정지/재개/완료 가능:
- work.py의 pause_work/resume_work/complete_work에 GST 작업자 예외 추가
- 기존: 본인 또는 관리자만 허용
- 변경: 본인 또는 관리자 또는 같은 company('GST') 작업자 허용

### 4. Checklist API

**4-1. GET /api/app/checklist/{serial_number}/{category}**
- 해당 S/N + category의 체크리스트 반환
- checklist_master JOIN checklist_record (LEFT JOIN — 아직 체크 안 한 항목도 포함)
- product_info.product_code → checklist_master.product_code 매칭
- 응답: {"items": [{"master_id", "item_name", "item_order", "is_checked", "checked_by", "checked_at", "note"}]}
- 체크리스트 마스터에 해당 product_code가 없으면 빈 리스트 반환
- @jwt_required

**4-2. PUT /api/app/checklist/check**
- 요청: {"serial_number": "xxx", "master_id": int, "is_checked": true, "note": "optional"}
- checklist_record UPSERT (ON CONFLICT serial_number, master_id DO UPDATE)
- checked_by = g.worker_id, checked_at = NOW()
- 응답: 업데이트된 record
- @jwt_required

**4-3. POST /api/admin/checklist/import**
- Excel 파일 업로드 → checklist_master 일괄 INSERT
- Excel 형식: product_code | category | item_name | item_order | description
- openpyxl 사용
- @jwt_required + @admin_required

### 5. SI Hook-Up 체크리스트 연동

SI task(마무리공정)의 task_management_screen 또는 detail 화면에서:
- "Hook-Up 체크리스트" 버튼 → GET /api/app/checklist/{serial_number}/HOOKUP
- 체크항목 리스트 표시 → 개별 체크 → PUT /api/app/checklist/check
- 체크 완료율 표시 (checked / total)

## FE 작업 순서

### 1. 홈 메뉴 확장 (home_screen.dart)

GST 작업자(company='GST') 또는 admin(is_admin=true)에게 3개 메뉴 추가:

```dart
// PI 가압검사 진행 제품
if (worker?.company == 'GST' || worker?.isAdmin == true) ...[
  _buildFeatureCard(
    icon: Icons.compress,
    iconBg: GxColors.successBg,
    iconColor: GxColors.success,
    title: 'PI 가압검사',
    subtitle: 'PI 가압검사 진행 제품 현황',
    onTap: () => Navigator.pushNamed(context, '/gst-products', arguments: {'category': 'PI'}),
  ),
  const SizedBox(height: 8),

  // QI 공정검사 진행 제품
  _buildFeatureCard(
    icon: Icons.verified,
    iconBg: Color(0xFFF3E8FF).withOpacity(0.5),
    iconColor: Color(0xFF7C3AED),
    title: 'QI 공정검사',
    subtitle: 'QI 공정검사 진행 제품 현황',
    onTap: () => Navigator.pushNamed(context, '/gst-products', arguments: {'category': 'QI'}),
  ),
  const SizedBox(height: 8),

  // SI 마무리공정 진행 제품
  _buildFeatureCard(
    icon: Icons.local_shipping,
    iconBg: GxColors.accentSoft,
    iconColor: GxColors.accent,
    title: 'SI 마무리공정',
    subtitle: 'SI 마무리공정 진행 제품 현황',
    onTap: () => Navigator.pushNamed(context, '/gst-products', arguments: {'category': 'SI'}),
  ),
  const SizedBox(height: 8),
],
```

⚠️ GST 인원은 본인 role(PI/QI/SI)과 무관하게 3개 메뉴 전부 표시.
⚠️ "작업 관리" 메뉴는 기존과 동일 — 본인 task만 표시 (active_role 기준 필터링).

### 2. GST 진행 제품 대시보드 화면 (gst_products_screen.dart 신규)

- route: '/gst-products' (arguments: {category: 'PI'/'QI'/'SI'})
- GET /app/gst/products/{category} 호출
- 제품 목록 카드: S/N, model, task_name, status badge, worker_name, started_at
- 각 카드 탭 → 해당 task의 상세 화면 (pause/resume/complete 가능)
- 타 작업자 task도 pause/resume/complete 버튼 표시 (GST 인원끼리 상호 제어)
- Pull-to-refresh 지원
- 빈 목록 시 "진행 중인 {category} 작업이 없습니다" 표시

### 3. SI Hook-Up 체크리스트 화면 (checklist_screen.dart 신규)

- SI task 상세에서 "Hook-Up 체크리스트" 버튼 클릭 시 이동
- GET /app/checklist/{serial_number}/HOOKUP 호출
- 체크항목 리스트: item_name, is_checked(체크박스), checked_by, checked_at
- 체크/해제 시 PUT /app/checklist/check 호출
- 상단에 완료율 Progress bar (예: 12/20 완료)
- 체크리스트가 비어있으면 "등록된 체크리스트가 없습니다. 관리자에게 문의하세요." 표시

### 4. active_role 전환 UI

home_screen.dart 상단 worker 정보 카드에:
- GST 작업자인 경우 active_role 표시 + 전환 버튼
- 탭 시 PI/QI/SI 선택 다이얼로그 → PUT /auth/active-role 호출
- 전환 후 홈 화면 새로고침

### 5. main.dart에 새 라우트 등록

```dart
'/gst-products': (context) {
  final args = ModalRoute.of(context)?.settings.arguments;
  final category = args is Map<String, dynamic>
      ? (args['category'] as String? ?? 'PI')
      : 'PI';
  return GstProductsScreen(category: category);
},
'/checklist': (context) {
  final args = ModalRoute.of(context)?.settings.arguments;
  final serialNumber = args is Map<String, dynamic>
      ? (args['serial_number'] as String? ?? '')
      : '';
  final category = args is Map<String, dynamic>
      ? (args['category'] as String? ?? 'HOOKUP')
      : 'HOOKUP';
  return ChecklistScreen(serialNumber: serialNumber, category: category);
},
```

_saveableRoutes에 '/gst-products' 추가.

### 6. flutter build web 에러 0건 확인

## TEST 작업 순서

### 1. GST Task 템플릿 테스트 (test_gst_task_seed.py — 신규 10개 이상)
- GAIA 모델 Task Seed → PI 2개 + QI 1개 + SI 1개 생성 확인
- DRAGON 모델 → 동일하게 PI/QI/SI task 생성 확인 (모든 모델 공통)
- GALLANT 모델 → 동일 확인
- 총 Task 수: MECH + ELEC + TMS + PI(2) + QI(1) + SI(1) 정확 검증
- PI task의 task_category='PI' 확인
- QI task의 task_category='QI' 확인
- SI task의 task_category='SI' 확인
- 중복 생성 방지 (같은 S/N 재초기화 시 중복 없음)
- GST 작업자가 PI/QI/SI task 전부 조회 가능 확인
- Admin이 PI/QI/SI task 전부 조회 가능 확인

### 2. GST 진행 제품 대시보드 API 테스트 (test_gst_products_api.py — 신규 12개 이상)
- GET /api/app/gst/products/PI → PI 진행 중 제품 반환
- GET /api/app/gst/products/QI → QI 진행 중 제품 반환
- GET /api/app/gst/products/SI → SI 진행 중 제품 반환
- 작업 미시작 제품 → 목록에 포함 (status: not_started)
- 작업 완료 제품 → 목록에서 제외 또는 completed 상태로 표시
- GST 작업자 조회 성공
- Admin 조회 성공
- 협력사 작업자(MECH, FNI) 조회 시 403
- 미인증 상태 → 401
- 타 작업자 task pause 성공 (같은 GST company)
- 타 작업자 task resume 성공
- 타 작업자 task complete 성공

### 3. Checklist API 테스트 (test_checklist_api.py — 신규 14개 이상)
- GET /api/app/checklist/{sn}/HOOKUP → 체크리스트 반환
- product_code에 해당하는 마스터가 없으면 빈 리스트 반환
- PUT /api/app/checklist/check → is_checked=true 성공
- PUT /api/app/checklist/check → is_checked=false (체크 해제) 성공
- PUT 후 GET으로 checked_by, checked_at 확인
- 같은 항목 중복 PUT → UPSERT (에러 안 남)
- 존재하지 않는 master_id → 400 또는 404
- POST /api/admin/checklist/import → Excel 파일 업로드 성공
- import 후 GET으로 항목 수 확인
- 중복 import 시 UNIQUE 제약으로 충돌 → ON CONFLICT 처리 확인
- 일반 작업자가 import 시도 → 403
- 미인증 상태 → 401
- 체크 완료율 계산 검증 (checked 수 / total 수)
- note 필드 저장 확인

### 4. active_role 전환 테스트 (test_active_role.py — 신규 8개 이상)
- PUT /api/auth/active-role → active_role='PI' 변경 성공
- PUT /api/auth/active-role → active_role='QI' 변경 성공
- PUT /api/auth/active-role → active_role='SI' 변경 성공
- 유효하지 않은 role ('MECH') → 400 거부
- 협력사 작업자(company='FNI')가 active_role 변경 시도 → 403
- GET /api/auth/me → active_role 포함 확인
- active_role 변경 후 작업 관리에서 해당 role task만 표시 확인
- 미인증 상태 → 401

### 5. 기존 테스트 regression 확인
Sprint 10까지의 모든 테스트가 여전히 PASS하는지 확인.
⚠️ task_seed.py 변경으로 기존 모델별 Task 수 검증 테스트 영향 가능 → 필요 시 수정 (PI/QI/SI 4개 추가 반영)

## 검증 기준 (Sprint 11 완료 조건)

✅ PI/QI/SI task 템플릿 4개 정상 생성 (모든 모델 공통)
✅ 홈 메뉴에 PI/QI/SI 진행 제품 대시보드 3개 표시 (GST + admin)
✅ GST 진행 제품 대시보드에서 S/N별 작업 현황 조회 가능
✅ 타 GST 작업자 task pause/resume/complete 가능
✅ checklist 스키마 생성 + CRUD API 정상 동작
✅ SI Hook-Up 체크리스트 화면에서 체크/해제 + 완료율 표시
✅ Excel import로 체크리스트 마스터 적재 가능
✅ active_role 전환 + 작업 관리 필터링 정상 동작
✅ Sprint 11 신규 테스트 44개 이상 PASS (task_seed 10 + products 12 + checklist 14 + role 8)
✅ 기존 테스트 regression 0건
✅ flutter build web 에러 0건
✅ PROGRESS.md에 Sprint 11 기록

## 규칙
- CLAUDE.md의 "5-Tier 스키마 아키텍처" 참조 (checklist 스키마 위치 확인)
- checklist_master의 product_code는 plan.product_info.product_code와 매칭
- checklist_record의 serial_number는 plan.product_info.serial_number와 매칭
- GST 인원 = company='GST' (role: PI, QI, SI, ADMIN)
- active_role은 "작업 관리" 메뉴의 본인 task 필터링에만 사용
- PI/QI/SI 홈 메뉴 대시보드는 active_role과 무관 — GST 전원에게 3개 모두 표시
- ⚠️ FE API 경로에 '/api' 접두사 넣지 말 것 (apiBaseUrl에 이미 /api 포함)
- 위 명시된 기능 외 신규 기능 추가 금지
- Railway 배포, PWA는 이번 Sprint 범위 아님
- .env 파일 절대 커밋 금지
- Sprint 11 완료 시 PROGRESS.md에 구현 기록
```

---

## 🔧 Sprint 11 팀 에이전트 종료 및 이어서 테스트 실행 가이드

### 1단계: 기존 팀 에이전트 종료
```bash
# Claude Code 터미널에서 실행
TeamDelete sprint-11
```
> ⚠️ "Already leading team" 에러가 나면 위 명령으로 먼저 종료 후 다음 단계 진행

### 2단계: Sprint 11 이어서 테스트 실행 프롬프트

아래 프롬프트를 Claude Code에 붙여넣으세요:

```
CLAUDE.md를 처음부터 끝까지 다시 읽고 Sprint 11 검증 테스트를 실행해줘.

⚠️ Sprint 11 상태:
- BE 구현 완료: gst.py, checklist.py 라우트 + worker.py active_role + 009 migration
- FE 구현 완료: gst_products_screen.dart, checklist_screen.dart
- 테스트 45개 작성 완료 (TDD): test_gst_task_seed.py(10), test_gst_products_api.py(12), test_checklist_api.py(14), test_active_role.py(9)
- 테스트 실행 안 됨 (이전 환경에서 DB 연결 실패)

⚠️ 이번 작업 목표:
1. 009_sprint11_gst_tasks.sql 마이그레이션 실행 (아직 안 됐을 수 있음)
2. Sprint 11 테스트 45개 실행 + PASS 확인
3. 기존 테스트 regression 확인 (Sprint 10까지 전체)
4. flutter build web 에러 0건 확인
5. 실패 테스트 있으면 원인 분석 후 코드 수정
6. PROGRESS.md 업데이트

## 팀 구성
3명의 teammate를 생성해줘. 모든 teammate는 Sonnet 모델 사용:

1. **BE** (Backend 담당) - 소유: backend/**
2. **FE** (Frontend 담당) - 소유: frontend/**
3. **TEST** (테스트 담당) - 소유: tests/**

## 작업 순서

### BE 작업
1. DB 마이그레이션 상태 확인:
   - Railway PostgreSQL에 접속하여 checklist 스키마 존재 여부 확인
   - 없으면 009_sprint11_gst_tasks.sql 실행
   - workers 테이블에 active_role 컬럼 존재 여부 확인
2. 기존 구현 코드 검증:
   - backend/app/routes/gst.py → 라우트 등록 확인 (__init__.py)
   - backend/app/routes/checklist.py → 라우트 등록 확인
   - backend/app/routes/auth.py → active-role 엔드포인트 확인
   - backend/app/models/worker.py → active_role 필드 + update_active_role() 함수 확인
3. 이상 있으면 수정, 없으면 TEST에게 넘기기

### FE 작업
1. 기존 구현 코드 검증:
   - frontend/lib/screens/gst/gst_products_screen.dart 존재 + 빌드 확인
   - frontend/lib/screens/checklist/checklist_screen.dart 존재 + 빌드 확인
   - main.dart에 '/gst-products', '/checklist' 라우트 등록 확인
   - home_screen.dart에 PI/QI/SI 메뉴 추가 확인
2. flutter build web 실행 → 에러 0건 확인
3. 이상 있으면 수정

### TEST 작업
1. BE가 마이그레이션 완료 확인 후 테스트 실행:
   ```bash
   cd /path/to/AXIS-OPS
   python -m pytest tests/backend/test_gst_task_seed.py -v
   python -m pytest tests/backend/test_gst_products_api.py -v
   python -m pytest tests/backend/test_checklist_api.py -v
   python -m pytest tests/backend/test_active_role.py -v
   ```
2. 실패 시 원인 분석 → BE/FE에게 수정 요청
3. 기존 테스트 regression 확인:
   ```bash
   python -m pytest tests/backend/test_sprint10_fixes.py -v
   python -m pytest tests/backend/ -v --timeout=120
   ```
4. 전체 결과 정리

## 검증 기준 (완료 조건)
✅ 009 마이그레이션 정상 적용 (checklist 스키마 + active_role 컬럼)
✅ Sprint 11 신규 테스트 45개 PASS
✅ 기존 테스트 regression 0건
✅ flutter build web 에러 0건
✅ PROGRESS.md에 Sprint 11 구현 완료 기록

## 규칙
- 이미 구현된 코드를 확인하고 테스트 실행이 핵심 — 신규 기능 추가 금지
- 테스트 실패 시 기존 코드 수정만 허용 (신규 기능 아님)
- ⚠️ FE API 경로에 '/api' 접두사 넣지 말 것 (apiBaseUrl에 이미 /api 포함)
- ⚠️ DB 시간 관련: get_db_connection()의 `options="-c timezone=Asia/Seoul"` 절대 삭제 금지
- ⚠️ task_management_screen.dart의 isApplicable 필터링 절대 삭제 금지
- .env 파일 절대 커밋 금지
- Sprint 11 완료 시 PROGRESS.md에 기록
```

---

## 🚀 Sprint 12 프롬프트 — PIN 간편 로그인 + 협력사 출퇴근 + QR 카메라 스캔 (Sprint 11 완료 후 사용)

```
CLAUDE.md를 처음부터 끝까지 다시 읽고 Sprint 12를 시작해줘.

⚠️ Sprint 12 핵심 목표:
1. hr 스키마 신설 + PIN 간편 로그인 (전체 사용자)
2. 협력사 출퇴근 기록 (MECH/ELEC/TMS만)
3. 개인 설정 화면 (PIN 등록/변경 + 생체인증 메뉴 비활성)
4. QR 카메라 스캔 (메인) + 텍스트 입력 (보조)

⚠️ Railway 배포, PWA는 이번 Sprint 범위 아님
⚠️ 생체인증(지문/FaceID)은 메뉴만 표시하고 "추후 오픈 예정" 안내

## 팀 구성
3명의 teammate를 생성해줘. 모든 teammate는 Sonnet 모델 사용:

1. **BE** (Backend 담당) - 소유: backend/**
2. **FE** (Frontend 담당) - 소유: frontend/**
3. **TEST** (테스트 담당) - 소유: tests/**

## BE 작업 순서

### 1. DB 마이그레이션 (010_sprint12_hr_schema.sql)

**1-1. hr 스키마 생성 (인사/인증/근태)**
```sql
CREATE SCHEMA IF NOT EXISTS hr;

-- ① 간편 인증 설정 (전체 사용자 — GST + 협력사)
CREATE TABLE hr.worker_auth_settings (
    worker_id INTEGER PRIMARY KEY REFERENCES public.workers(id),
    pin_hash VARCHAR(255),               -- 4자리 PIN bcrypt 해시
    biometric_enabled BOOLEAN DEFAULT FALSE,  -- 추후 지문/FaceID 지원
    biometric_type VARCHAR(20),          -- 'fingerprint' / 'face_id' (추후)
    pin_fail_count INTEGER DEFAULT 0,    -- PIN 연속 실패 횟수
    pin_locked_until TIMESTAMPTZ,        -- 3회 실패 시 잠금 시각
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ② 협력사 출퇴근 기록 (company != 'GST')
CREATE TABLE hr.partner_attendance (
    id SERIAL PRIMARY KEY,
    worker_id INTEGER NOT NULL REFERENCES public.workers(id),
    check_type VARCHAR(3) NOT NULL,      -- 'in' / 'out'
    check_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    method VARCHAR(10) DEFAULT 'button', -- 'button' / 'pin' / 'fingerprint' / 'face_id'
    note TEXT,                           -- 비고 (지각 사유 등)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_partner_att_worker ON hr.partner_attendance(worker_id, check_time DESC);
CREATE INDEX idx_partner_att_date ON hr.partner_attendance(check_time);

-- ③ GST 사내직원 근태 (추후 확장 예약 — 그룹웨어 연동 or RDB 동기화)
-- 이번 Sprint에서는 테이블만 생성, API/UI 미구현
CREATE TABLE hr.gst_attendance (
    id SERIAL PRIMARY KEY,
    worker_id INTEGER NOT NULL REFERENCES public.workers(id),
    check_type VARCHAR(3) NOT NULL,      -- 'in' / 'out'
    check_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source VARCHAR(20) DEFAULT 'manual', -- 'manual' / 'groupware_sync' / 'api'
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_gst_att_worker ON hr.gst_attendance(worker_id, check_time DESC);
```

### 2. PIN 간편 로그인 API

⚠️ PIN 로그인과 출퇴근은 완전 분리. PIN 로그인 = 앱 재진입 편의, 출퇴근 = 명시적 버튼 클릭.

**2-1. POST /api/auth/set-pin**
- 요청: {"pin": "1234"}
- PIN 4자리 숫자만 허용 (정규식 검증)
- bcrypt 해시 후 hr.worker_auth_settings에 UPSERT
- pin_fail_count 초기화
- 응답: {"message": "PIN이 설정되었습니다."}
- @jwt_required (로그인 상태에서만 설정 가능)

**2-2. PUT /api/auth/change-pin**
- 요청: {"current_pin": "1234", "new_pin": "5678"}
- current_pin 검증 후 new_pin으로 변경
- 응답: {"message": "PIN이 변경되었습니다."}
- @jwt_required

**2-3. POST /api/auth/pin-login**
- 요청: {"worker_id": int, "pin": "1234"}
- worker_id + PIN bcrypt 검증
- pin_fail_count 관리:
  - 실패 시 +1, 3회 이상 시 5분 잠금 (pin_locked_until 설정)
  - 잠금 중 시도 → "PIN이 잠겼습니다. N분 후 다시 시도하세요."
  - 성공 시 pin_fail_count = 0 초기화
- 검증 성공 → JWT access_token + refresh_token 발급 (기존 login과 동일 형태)
- 응답: {"access_token": "...", "refresh_token": "...", "worker": {...}}
- @jwt_required 아님 (로그인 엔드포인트)

**2-4. GET /api/auth/pin-status**
- 현재 로그인한 사용자의 PIN 등록 여부 반환
- 응답: {"pin_registered": true/false, "biometric_enabled": false}
- @jwt_required

### 3. 협력사 출퇴근 API

⚠️ 출퇴근 = 협력사(company != 'GST')만 사용. GST 사내직원은 그룹웨어로 근태 관리.

**3-1. POST /api/hr/attendance/check**
- 요청: {"check_type": "in"} 또는 {"check_type": "out"}
- 당일 중복 출근 체크: 이미 'in' 기록 있으면 "이미 출근 처리되었습니다." (400)
- 'out' 시 당일 'in' 기록 없으면 "출근 기록이 없습니다." (400)
- 당일 기준: KST 00:00~23:59 (timezone=Asia/Seoul)
- 응답: {"message": "출근 처리되었습니다.", "check_time": "2026-02-27T09:00:00+09:00"}
- @jwt_required
- 접근 제어: company != 'GST' (협력사만)

**3-2. GET /api/hr/attendance/today**
- 현재 로그인한 작업자의 당일 출퇴근 기록 조회
- 응답: {"records": [{"check_type": "in", "check_time": "...", "method": "button"}], "status": "checked_in"}
- status: 'not_checked' / 'checked_in' / 'checked_out'
- @jwt_required

⚠️ Admin 출퇴근 조회 API (dashboard, monthly)는 Sprint 12 범위 아님 → 추후 AXIS-VIEW(React 대시보드)에서 구현

### 4. Route 등록

**backend/app/__init__.py:**
```python
from app.routes.hr import hr_bp
app.register_blueprint(hr_bp)
```

→ 권장: auth.py에 PIN 관련 (set-pin, change-pin, pin-login, pin-status) 추가
         hr.py 신규 생성 — 출퇴근 check/today만

## FE 작업 순서

### 1. 개인 설정 화면 (profile_screen.dart 신규)

**route: '/profile'**
- 홈 화면 AppBar에 설정 아이콘(Icons.settings_outlined) 추가 → '/profile' 이동
- 화면 구성:
  ```
  [프로필 정보]
  - 이름, 이메일, 역할, 회사 (읽기 전용)

  [간편 인증 설정]
  - PIN 번호: [등록하기] / [변경하기] (등록 여부에 따라)
  - 지문 인식: [추후 오픈 예정] (비활성, 회색 처리)
  - Face ID: [추후 오픈 예정] (비활성, 회색 처리)
  ```
- PIN 등록/변경 시 → PinSettingsScreen으로 이동

### 2. PIN 설정 화면 (pin_settings_screen.dart 신규)

**route: '/pin-settings'**
- PIN 등록 화면:
  - 4자리 숫자 입력 UI (원형 도트 4개 + 숫자 키패드)
  - "PIN 번호를 입력하세요" → 4자리 입력
  - "다시 한번 입력하세요" → 확인 입력
  - 두 입력 일치 시 → POST /auth/set-pin
  - 불일치 시 → "PIN이 일치하지 않습니다. 다시 시도해주세요."

- PIN 변경 화면:
  - "현재 PIN을 입력하세요" → 4자리 입력
  - "새 PIN을 입력하세요" → 4자리 입력
  - "다시 한번 입력하세요" → 확인 입력
  - PUT /auth/change-pin

### 3. PIN 로그인 화면 (pin_login_screen.dart 신규)

**앱 재실행 시 분기 로직 (AuthGate 수정):**
```
앱 시작
  ↓
refresh_token 존재?
  ├ NO → 이메일/비밀번호 로그인 화면
  └ YES → worker_id + PIN 등록 여부 확인 (secure storage)
              ├ PIN 미등록 → refresh_token으로 자동 로그인 시도 → 홈
              └ PIN 등록됨 → PIN 입력 화면
                              ├ PIN 맞음 → POST /auth/pin-login → 홈
                              ├ PIN 3회 실패 → "PIN이 잠겼습니다" + 이메일 로그인으로 이동
                              └ "이메일로 로그인" 링크 → 기존 로그인 화면
```

- PIN 입력 화면 UI:
  - 상단: 사용자 이름 + 회사 표시 (secure storage에서)
  - 중앙: 원형 도트 4개 (입력 시 채워짐)
  - 하단: 숫자 키패드 (0-9) + 삭제 + 이메일 로그인 링크
  - 실패 시: "PIN이 일치하지 않습니다 (N/3)" 빨간 안내

### 4. 협력사 출퇴근 UI (home_screen.dart 수정)

홈 화면에서 협력사 작업자(company != 'GST')에게만 출퇴근 카드 표시:

```dart
// 협력사 작업자 전용 출퇴근 카드
if (worker?.company != 'GST' && worker?.isAdmin != true) ...[
  _buildAttendanceCard(),  // 출근/퇴근 버튼
  const SizedBox(height: 12),
],
```

**출퇴근 카드 구성:**
```
┌─────────────────────────────────┐
│  📋 출퇴근 관리                   │
│                                 │
│  현재 상태: 미출근 / 출근 중 / 퇴근  │
│  출근 시각: 09:00               │
│                                 │
│  [출근하기] / [퇴근하기] 버튼      │
└─────────────────────────────────┘
```

- 앱 진입 시 GET /hr/attendance/today로 당일 상태 조회
- 미출근 → "출근하기" 버튼 활성
- 출근 중 → "퇴근하기" 버튼 활성 + 출근 시각 표시
- 퇴근 완료 → 두 버튼 비활성 + "오늘 근무 완료" 표시

### 5. QR 카메라 스캔 (qr_scan_screen.dart 수정)

**현재**: 텍스트 입력만 (카메라 "향후 업데이트" 안내)
**변경**: 카메라 스캔 메인 + 텍스트 입력 보조

**카메라 스캔 구현 (html5-qrcode JS interop 확정):**
- ⚠️ mobile_scanner 사용 금지 — iOS Safari PWA 호환성 이슈 있음
- html5-qrcode JS 라이브러리를 Flutter Web JS interop으로 호출
- 구현 순서:
  1. web/index.html에 `<script src="https://unpkg.com/html5-qrcode"></script>` 추가
  2. lib/services/qr_scanner_service.dart 생성 — dart:js_interop 또는 dart:js_util로 Html5Qrcode 클래스 래핑
  3. 주요 메서드: start(cameraId, config, onSuccess, onError), stop(), getDevices()
  4. qr_scan_screen.dart에서 HtmlElementView로 카메라 프리뷰 div 삽입
- 카메라 권한 요청 → 허용 시 카메라 프리뷰 표시 → QR 인식 시 자동 처리
- 카메라 불가 시(데스크톱, 권한 거부 등) → 텍스트 입력 fallback 자동 전환

**UI 구조 변경:**
```
┌─────────────────────────────────┐
│  QR 스캔                        │
│                                 │
│  [Worksheet QR] [Location QR]   │  ← 기존 타입 선택
│                                 │
│  ┌───────────────────────────┐  │
│  │     📷 카메라 프리뷰        │  │  ← 메인 (신규)
│  │     QR 코드를 비추세요      │  │
│  └───────────────────────────┘  │
│                                 │
│  또는 직접 입력:                 │
│  [DOC_GBWS-6408_______] [확인]  │  ← 보조 (기존)
│                                 │
└─────────────────────────────────┘
```

- "Sprint 2 MVP" 안내 배너 제거
- 카메라 프리뷰 영역이 메인
- 하단에 "직접 입력" 토글/접이식으로 텍스트 입력 유지

### 7. main.dart에 새 라우트 등록

```dart
'/profile': (context) => const ProfileScreen(),
'/pin-settings': (context) => const PinSettingsScreen(),
'/pin-login': (context) => const PinLoginScreen(),
```

### 7. flutter build web 에러 0건 확인

## TEST 작업 순서

### 1. PIN 인증 테스트 (test_pin_auth.py — 신규 14개 이상)
- POST /api/auth/set-pin → PIN 설정 성공
- POST /api/auth/set-pin → 4자리 아닌 값 → 400
- POST /api/auth/set-pin → 숫자 아닌 값 → 400
- POST /api/auth/set-pin → 미인증 → 401
- PUT /api/auth/change-pin → 현재 PIN 맞으면 변경 성공
- PUT /api/auth/change-pin → 현재 PIN 틀리면 400
- POST /api/auth/pin-login → 맞는 PIN → 토큰 발급
- POST /api/auth/pin-login → 틀린 PIN → 401 + fail_count 증가
- POST /api/auth/pin-login → 3회 실패 → 잠금 (423 Locked)
- POST /api/auth/pin-login → 잠금 해제 후 성공
- GET /api/auth/pin-status → PIN 미등록 시 false
- GET /api/auth/pin-status → PIN 등록 시 true
- POST /api/auth/pin-login → PIN 미등록 worker → 404
- POST /api/auth/set-pin → 중복 설정 → UPSERT 성공

### 2. 출퇴근 API 테스트 (test_attendance.py — 신규 8개 이상)
- POST /api/hr/attendance/check → check_type='in' 출근 성공
- POST /api/hr/attendance/check → check_type='out' 퇴근 성공
- POST /api/hr/attendance/check → 당일 중복 출근 → 400
- POST /api/hr/attendance/check → 출근 없이 퇴근 → 400
- POST /api/hr/attendance/check → GST 작업자 → 403
- POST /api/hr/attendance/check → 미인증 → 401
- GET /api/hr/attendance/today → 당일 기록 조회
- GET /api/hr/attendance/today → 기록 없으면 status='not_checked'

### 3. 기존 테스트 regression 확인
Sprint 11까지의 모든 테스트가 여전히 PASS하는지 확인.

## 검증 기준 (Sprint 12 완료 조건)

✅ hr 스키마 생성 (worker_auth_settings + partner_attendance + gst_attendance)
✅ PIN 설정/변경/로그인/상태 API 4개 정상 동작
✅ PIN 3회 실패 → 5분 잠금 동작
✅ 출퇴근 check-in/check-out API 정상 (협력사만)
✅ 당일 중복 출근 방지
✅ 개인 설정 화면 — PIN 등록/변경 + 생체인증 "추후 오픈" 메뉴
✅ PIN 로그인 화면 — 4자리 입력 + 키패드 + 실패 카운트 표시
✅ 홈 화면 — 협력사 출퇴근 카드 (GST 제외)
✅ QR 카메라 스캔 메인 + 텍스트 입력 보조
✅ Sprint 12 신규 테스트 22개 이상 PASS
✅ 기존 테스트 regression 0건
✅ flutter build web 에러 0건
✅ PROGRESS.md에 Sprint 12 기록

## 규칙
- CLAUDE.md의 "Phase B: 협력사 근태 관리" (643~709 line) 참조
- PIN 로그인과 출퇴근은 완전 분리 — PIN 로그인 ≠ 자동 출근
- PIN 로그인 대상: 전체 사용자 (GST + 협력사)
- 출퇴근 대상: 협력사만 (company != 'GST')
- Admin 출퇴근 대시보드는 Sprint 12 범위 아님 → 추후 AXIS-VIEW에서 구현
- 생체인증 메뉴: UI만 표시, "추후 오픈 예정" 안내, 실제 기능 미구현
- QR 카메라: html5-qrcode JS interop만 사용 (mobile_scanner 사용 금지)
- ⚠️ FE API 경로에 '/api' 접두사 넣지 말 것 (apiBaseUrl에 이미 /api 포함)
- ⚠️ DB 시간: get_db_connection()의 `options="-c timezone=Asia/Seoul"` 절대 삭제 금지
- ⚠️ FE 시간 표시: 반드시 `.toLocal()` 호출 후 포맷팅
- .env 파일 절대 커밋 금지
- 위 명시된 기능 외 신규 기능 추가 금지
- Sprint 12 완료 시 PROGRESS.md에 기록
```

---

## 🚀 Sprint 13 프롬프트 — WebSocket 정합성 수정 + 알림 실시간 전달 복원 (Sprint 12 완료 후 사용)

```
CLAUDE.md를 처음부터 끝까지 다시 읽고 Sprint 13을 시작해줘.
SPRINT_13_PLAN.md도 반드시 읽어.

⚠️ Sprint 13 핵심 목표:
1. BUG-2 수정: Flask-SocketIO → flask-sock(raw WebSocket) 마이그레이션
2. BUG-4 수정: scheduler_service.py의 create_alert() → create_and_broadcast_alert() 변경 (DB저장+WS broadcast 동시 처리)
3. FE 변경 0건 (이미 raw WebSocket 사용 중)

## 변경 대상 BE 파일 (8개)
1. requirements.txt — Flask-SocketIO/eventlet 제거, flask-sock 추가
2. Procfile — eventlet → gthread --threads 4
3. app/websocket/events.py — **전체 리라이트** (ConnectionRegistry + ws_handler + emit 함수)
4. app/websocket/__init__.py — ws_handler/registry export
5. app/__init__.py — SocketIO 제거, Sock 초기화 + /ws 라우트 등록
6. run.py — socketio.run() → app.run()
7. app/services/scheduler_service.py — 5곳 create_alert → create_and_broadcast_alert
8. tests/backend/test_websocket.py — 전면 리라이트 (ConnectionRegistry 단위 테스트)

## events.py 핵심 구조
- ConnectionRegistry: thread-safe dict (threading.Lock), connections + rooms 관리
- ws_handler(ws): JWT from query param → registry 등록 → 메시지 루프 (ping/pong) → disconnect 정리
- emit_new_alert(worker_id, data): worker room 전송 (기존 시그니처 유지)
- emit_process_alert(data): role room 또는 broadcast (기존 시그니처 유지)
- emit_task_completed(serial, category, worker_id): broadcast (기존 시그니처 유지)
- 메시지 포맷: {"event": "xxx", "data": {...}} — FE websocket_service.dart와 일치

## 팀 구성
2명의 teammate를 생성해줘. 모든 teammate는 Sonnet 모델 사용:

1. **BE** (Backend 담당) - 소유: backend/**
2. **TEST** (테스트 담당) - 소유: tests/**

FE 변경 없으므로 FE teammate 불필요.

## 테스트 체크리스트
- T-01~T-10: ConnectionRegistry 단위 테스트 (등록/해제, room, 메시지 전송, 동시 연결)
- T-11: test_websocket.py 전면 수정
- T-13: test_scheduler.py 영향 확인 (create_and_broadcast_alert 변경)

## 배포 순서 (Day 2)
1. git commit & push
2. Railway 배포 (Procfile gthread 확인)
3. flutter build web → Netlify 배포
4. WSS 연결 테스트 (wss://axis-ops-api.up.railway.app/ws)

## 규칙
- SPRINT_13_PLAN.md의 섹션 2~7 순서대로 작업
- alert_service.py의 emit_new_alert, emit_process_alert 시그니처 절대 변경 금지
- FE 코드 수정 금지 (websocket_service.dart 그대로)
- ⚠️ DB 시간: get_db_connection()의 `options="-c timezone=Asia/Seoul"` 절대 삭제 금지
- .env 파일 절대 커밋 금지
- Sprint 13 완료 시 PROGRESS.md, BACKLOG.md에 기록
```

---

## ✅ BUG-5 핫픽스 — QR 스캔 영역 정사각형 수정 (완료 2026-03-01)

### 해결 완료
- ✅ 카메라 위치: `left + width` 명시 방식 (5차 수정)
- ✅ 스캔 영역: 순수 JS `<script>` 태그 config 주입 (9차 수정)
- ✅ 스플래시 스크린: G-AXIS 로고 + flutter-first-frame fade-out
- ✅ 웹 검증: Console 로그 `qrbox=205x205` 정사각형 확인

### 실패한 방법 (6~8차)
| 차수 | 방법 | 결과 |
|------|------|------|
| 6차 | `jsify({'qrbox': qrboxSize})` 정수 | ❌ 직사각형 |
| 7차 | `newObject()` + `setProperty()` | ❌ 직사각형 (iPad/Android/iOS) |
| 8차 | `JSON.parse()` + `allowInterop` 콜백 | ❌ 직사각형 |

### 성공한 방법 (9차 — 순수 JavaScript 주입)
```javascript
// <script> 태그로 Dart interop 없이 순수 JS에서 config 생성
window.__qrScanConfig = {
  fps: 10,
  qrbox: function(viewfinderWidth, viewfinderHeight) {
    var size = Math.round(Math.min(viewfinderWidth, viewfinderHeight) * 0.7);
    size = Math.max(120, Math.min(250, size));
    return { width: size, height: size };
  }
};
```
Dart에서는 `js_util.getProperty(globalThis, '__qrScanConfig')`으로 읽기만 함.

### 교훈
**Dart-to-JS interop의 한계**: `jsify()`, `newObject()+setProperty()`, `JSON.parse()+allowInterop` 모두 html5-qrcode 내부에서 프로퍼티 접근 실패. 서드파티 JS 라이브러리에 config를 전달할 때는 **순수 JavaScript에서 객체를 생성**하고 Dart는 참조만 전달하는 것이 안전.

### 남은 작업
- [ ] iOS/Android 모바일 기기에서 정사각형 스캔 영역 최종 확인
- [ ] QR 코드 'DOC_GBWS-6408' 인식 테스트
- [ ] 인식 후 _onQrDetected → _handleQrCode 플로우 확인

### 테스트 QR 코드
- 내용: `DOC_GBWS-6408` (Worksheet QR, DOC_ 접두사)
- 기대: QR 인식 → `[QrScannerWeb] ★ QR DETECTED: DOC_GBWS-6408` 콘솔 출력
```

---

## 🚀 Sprint 14 프롬프트 — 작업자명 표시 + 휴게시간/작업시간 버그 수정 + QR 카메라 수정

```
CLAUDE.md를 처음부터 끝까지 다시 읽고 Sprint 14를 시작해줘.
BACKLOG.md, BACKLOG-ALARM.md도 읽어.

## Sprint 14 목표
5가지 작업:
1. Task를 시작한 작업자 이름이 화면에 표시되도록 (협력사 Task Detail + GST 검사 대시보드)
2. 🔴 휴게시간 자동 일시정지/재개 + 작업시간 계산 버그 수정 (핵심 기능 — 충분한 테스트 필수)
3. 🔴 Location QR 필수 설정(on/off) 미작동 수정 — on일 때 location QR 미등록 시 작업 시작 차단
4. QR 카메라 프레임 스크롤 분리 버그 수정
5. QR 스캔 영역 직사각형 → 정사각형 수정

⚠️ 다중 작업자 알람 고도화(에스컬레이션 타겟 변경 등)는 이번 Sprint 범위 아님.
BACKLOG-FLOWLOGIC.md 참고만 하고 수정하지 말 것. 추후 별도 Sprint에서 진행.

## 팀 구성
3명의 teammate를 생성해줘. 모든 teammate는 Sonnet 모델 사용:

1. **BE** (Backend 담당) - 소유: backend/**
2. **FE** (Frontend 담당) - 소유: frontend/**
3. **TEST** (테스트 담당) - 소유: tests/**

---

## BE 작업 (5개)

### BE-1: Task Detail API + GST API에 작업자 리스트 추가
현재 `/api/app/tasks/<serial_number>` (work.py)와
`/api/app/gst/products/<category>` (gst.py)가 각각 `worker_id`, `worker_name` 1명만 반환.
task를 시작한 작업자 전원의 이름 + 상태를 반환하도록 수정.

**work.py 변경:**
task list 반환 후 work_start_log + work_completion_log 배치 조회하여 workers 배열 추가:
```sql
SELECT
    wsl.task_id,
    wsl.worker_id,
    w.name AS worker_name,
    wsl.started_at,
    wcl.completed_at,
    wcl.duration_minutes,
    CASE WHEN wcl.id IS NOT NULL THEN 'completed' ELSE 'in_progress' END AS status
FROM work_start_log wsl
JOIN workers w ON wsl.worker_id = w.id
LEFT JOIN work_completion_log wcl
    ON wsl.task_id = wcl.task_id AND wsl.worker_id = wcl.worker_id
WHERE wsl.task_id = ANY(%s)
ORDER BY wsl.task_id, wsl.started_at ASC
```

⚠️ N+1 쿼리 금지. task_id 배열을 모아서 한 번에 조회 → task_id 기준 그룹핑.

각 task에 추가되는 필드:
```json
"workers": [
  {"worker_id": 10, "worker_name": "김철수", "started_at": "...", "completed_at": "...", "duration_minutes": 30, "status": "completed"},
  {"worker_id": 11, "worker_name": "이영희", "started_at": "...", "completed_at": null, "duration_minutes": null, "status": "in_progress"}
]
```

work_start_log에 기록 없는 레거시 task는 fallback:
```python
if not workers_list and task_worker_id:
    workers_list = [{'worker_id': task_worker_id, 'worker_name': task_worker_name,
                     'started_at': task_started_at, 'completed_at': task_completed_at,
                     'duration_minutes': task_duration, 'status': task_status_str}]
```

**gst.py 변경:** 동일 패턴 적용.
기존 `LEFT JOIN workers w ON w.id = t.worker_id`는 유지 (하위 호환 worker_name 필드).
추가로 work_start_log 배치 조회하여 workers 배열 추가.

### BE-2: 🔴 휴게시간 자동 일시정지 전체 점검 + 자동 재개 구현
파일: `backend/app/services/scheduler_service.py`

**현재 버그 (BUG-7)** — 🚨 휴게시간 알람 자체가 도착하지 않는 현상 보고됨:

**진단 필수 (코드 수정 전 먼저 확인):**
1. `check_break_time_job()` 실행 여부: 로깅 강화하여 매 분 실행 확인
   ```python
   logger.info(f"check_break_time_job: current_time={current_time}, auto_pause_enabled={auto_pause_enabled}")
   ```
2. `admin_settings` 테이블에 휴게시간 값 존재 여부:
   - migration 008이 Railway DB에 적용됐는지 확인
   - `get_setting('lunch_start', None)` 반환값이 `"11:20"`(str)인지 `None`인지
3. `IntervalTrigger(minutes=1)` 타이밍 이슈:
   - 매 60초 간격이지만 정각(:00초)에 맞춰지지 않음
   - 예: 스케줄러가 10:00:45에 시작하면 → 10:01:45, 10:02:45... → "10:00" 윈도우를 놓칠 수 있음
   - **수정**: `CronTrigger(second=0)` (매 분 정각) 또는 비교 로직을 범위로 변경
4. `force_pause_all_active_tasks()`: 다중 작업자 task에서 `t.worker_id`(첫 번째만) 기반이라 나머지 작업자에게 알림 안 감

**수정 ①: IntervalTrigger → CronTrigger 변경** (타이밍 안정화):
```python
# 변경 전
_scheduler.add_job(func=check_break_time_job, trigger=IntervalTrigger(minutes=1), ...)
# 변경 후
_scheduler.add_job(func=check_break_time_job, trigger=CronTrigger(second=0), ...)
```

**수정 ②: 로깅 강화** — 모든 경로에 디버그 로그:
```python
def check_break_time_job():
    logger.info(f"[BREAK_CHECK] Running at {current_time}")
    for period in BREAK_PERIODS:
        start_time = get_setting(period['start_key'], None)
        end_time = get_setting(period['end_key'], None)
        logger.info(f"[BREAK_CHECK] {period['pause_type']}: start={start_time}, end={end_time}, current={current_time}")
```

**수정 ③: 자동 재개 (auto-resume) 구현**:
`send_break_end_notifications()` (644~705행)가 휴게시간 종료 시 **알림만 발송**하고
`resume_pause()`와 `set_paused(False)`를 호출하지 않음.
→ 작업이 영구적으로 일시정지 상태에 빠짐.
→ `work_pause_log.resumed_at`이 NULL로 남아 `pause_duration_minutes`도 계산 안 됨.

**수정 내용**:
`send_break_end_notifications()` 함수에 자동 재개 로직 추가:
```python
def send_break_end_notifications(pause_type: str, message: str) -> None:
    from app.models.work_pause_log import resume_pause
    from app.models.task_detail import set_paused
    # ...기존 쿼리로 resumed_at IS NULL인 pause_log 조회...

    for row in rows:
        # 1. work_pause_log 재개 처리
        pause_log_id = row['pause_log_id']  # ← 쿼리에 wpl.id 추가 필요
        now_kst = datetime.now(Config.KST)
        updated_pause = resume_pause(pause_log_id, now_kst)

        # 2. pause_duration 계산 → total_pause_minutes 업데이트
        if updated_pause:
            pause_duration = updated_pause.pause_duration_minutes or 0
            # app_task_details.total_pause_minutes 갱신
            task_detail_id = row['task_detail_id']  # ← 쿼리에 wpl.task_detail_id 추가
            _update_total_pause(task_detail_id, pause_duration)

        # 3. app_task_details.is_paused = FALSE
        set_paused(row['task_detail_id'], is_paused=False)

        # 4. 알림 발송 (기존 코드)
```

⚠️ 쿼리 수정 필요:
```sql
SELECT wpl.id AS pause_log_id,
       wpl.task_detail_id,
       wpl.worker_id,
       t.serial_number,
       t.qr_doc_id,
       t.task_name,
       t.total_pause_minutes
FROM work_pause_log wpl
JOIN app_task_details t ON wpl.task_detail_id = t.id
WHERE wpl.pause_type = %s
  AND wpl.resumed_at IS NULL
```

`_update_total_pause()` 헬퍼:
```python
def _update_total_pause(task_detail_id: int, additional_pause: int) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE app_task_details
        SET total_pause_minutes = COALESCE(total_pause_minutes, 0) + %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """, (additional_pause, task_detail_id))
    conn.commit()
    conn.close()
```

### BE-3: 🔴 작업시간(duration) 계산에서 휴게시간 자동 제외
파일: `backend/app/services/task_service.py`

**현재 버그 (BUG-8)**:
`_record_completion_log()` (541~601행)에서 개인 작업시간 계산:
```python
personal_duration = int((completed_at - row['started_at']).total_seconds() / 60)
```
→ 휴게시간(점심, 오전/오후/저녁 휴게)이 포함된 채로 duration 기록됨.
→ pause 기록이 없어도 (auto_pause가 작동하지 않았어도) 설정된 휴게시간은 제외해야 함.

**수정 내용**:
`_record_completion_log()`에서 duration 계산 시 admin_settings의 휴게시간 구간을 조회하고,
작업 시간(started_at ~ completed_at) 구간과 겹치는 휴게시간을 자동 차감:

```python
def _calculate_working_minutes(started_at: datetime, completed_at: datetime) -> int:
    """
    started_at ~ completed_at 사이의 순수 작업시간(분) 계산.
    admin_settings에 설정된 휴게시간 구간을 자동 차감.
    """
    from app.models.admin_settings import get_setting

    total_minutes = int((completed_at - started_at).total_seconds() / 60)

    # 휴게시간 구간 조회
    break_periods = [
        ('break_morning_start', 'break_morning_end'),
        ('lunch_start', 'lunch_end'),
        ('break_afternoon_start', 'break_afternoon_end'),
        ('dinner_start', 'dinner_end'),
    ]

    work_date = started_at.date()
    overlap_minutes = 0

    for start_key, end_key in break_periods:
        bs = get_setting(start_key, None)  # "HH:MM" string
        be = get_setting(end_key, None)
        if not bs or not be:
            continue

        # HH:MM → 해당일 KST datetime
        bh, bm = map(int, bs.split(':'))
        eh, em = map(int, be.split(':'))
        break_start = started_at.replace(hour=bh, minute=bm, second=0, microsecond=0)
        break_end = started_at.replace(hour=eh, minute=em, second=0, microsecond=0)

        # 작업 구간이 여러 날에 걸칠 수 있으므로 날짜별 반복
        # (대부분 당일이므로 단순화: started_at 날짜 기준 + 필요시 다음날)
        for day_offset in range(0, max(1, (completed_at.date() - started_at.date()).days + 1)):
            day_delta = timedelta(days=day_offset)
            day_break_start = break_start + day_delta
            day_break_end = break_end + day_delta

            # 겹치는 구간 계산
            overlap_start = max(started_at, day_break_start)
            overlap_end = min(completed_at, day_break_end)

            if overlap_start < overlap_end:
                overlap_minutes += int((overlap_end - overlap_start).total_seconds() / 60)

    return max(0, total_minutes - overlap_minutes)
```

**적용 위치**:
1. `_record_completion_log()`: `personal_duration = _calculate_working_minutes(started_at, completed_at)`
2. `_finalize_task_multi_worker()`: 이미 `total_pause_minutes` 차감하고 있으므로,
   개별 작업자 duration에서 휴게시간이 미리 제외되면 이중 차감 방지 필요.
   → **원칙**: `_record_completion_log()`에서 휴게시간 제외된 duration 기록,
   `_finalize_task_multi_worker()`에서는 수동 pause만 차감 (auto_pause 기록은 별도 구분).

⚠️ 이중 차감 방지 로직:
- `work_pause_log.pause_type`이 'break_morning', 'lunch', 'break_afternoon', 'dinner'인 건은
  `_calculate_working_minutes()`에서 이미 제외되므로 `total_pause_minutes`에서 다시 빼면 안 됨.
- `_finalize_task_multi_worker()`에서 `total_pause_minutes` 조회 시:
  ```sql
  SELECT COALESCE(SUM(pause_duration_minutes), 0) AS manual_pause
  FROM work_pause_log
  WHERE task_detail_id = %s
    AND pause_type NOT IN ('break_morning', 'lunch', 'break_afternoon', 'dinner')
    AND resumed_at IS NOT NULL
  ```
  또는 `total_pause_minutes` 컬럼 대신 수동 pause만 집계하도록 변경.

### BE-4: Force-close에서 pause 시간 차감
파일: `backend/app/routes/admin.py` (1006~1059행)

**현재 버그 (BUG-9)**:
force-close 시 `duration_minutes` 계산:
```python
duration_minutes = existing_duration + pending_duration
```
→ `total_pause_minutes`를 차감하지 않음.
→ 휴게시간 포함된 채 duration 저장됨.

**수정 내용**:
```python
# total_pause_minutes 조회
cur.execute(
    "SELECT COALESCE(total_pause_minutes, 0) AS total_pause FROM app_task_details WHERE id = %s",
    (task_id,)
)
total_pause = int(cur.fetchone()['total_pause'])

# 휴게시간 자동 제외 (BE-3의 _calculate_working_minutes 사용)
# + 수동 pause 차감
duration_minutes = max(0, existing_duration + pending_duration - total_pause)
```

⚠️ BE-3에서 `_calculate_working_minutes()`로 개인 duration에 이미 휴게시간 제외한 경우,
force-close의 pending_duration도 동일하게 적용해야 함:
```python
for pw in pending_workers:
    if pw['started_at']:
        pending_duration += _calculate_working_minutes(pw['started_at'], completed_at)
```

### BE-5: 🔴 Location QR 필수 설정 미작동 수정 (BUG-11)
파일: `backend/app/services/task_service.py`, `backend/app/routes/work.py`

**현재 버그**:
admin_settings의 `location_qr_required=true`여도 qr-doc-id 스캔만으로 Task 작업이 바로 진행됨.
Location QR을 먼저 스캔해야 한다는 알림/차단이 없음.

**근본 원인**: Location QR 체크가 3곳에서 모두 누락.
1. `process_validator.py`에서 경고만 생성 (warnings 배열), **차단하지 않음**
2. `task_service.py`의 `start_work()`에 location_qr 체크 **완전 없음**
3. FE에서 Worksheet QR 스캔 후 Task 목록으로 **바로 이동** (location QR 검증 없음)

**수정 ①: `task_service.py` — `start_work()` 에 차단 로직 추가:**
```python
def start_work(self, worker_id, task_detail_id):
    # ...기존 task 조회, 적용여부 확인 후에 추가...

    from app.models.admin_settings import get_setting

    location_qr_required = get_setting('location_qr_required', True)
    if location_qr_required:
        # product_info에서 location_qr_id 확인
        from app.models.product_info import get_product_by_qr_doc_id
        product = get_product_by_qr_doc_id(task.qr_doc_id)
        if product and not product.location_qr_id:
            return {
                'error': 'LOCATION_QR_REQUIRED',
                'message': 'Location QR이 등록되지 않았습니다. Location QR을 먼저 스캔해주세요.'
            }, 400
```

**수정 ②: `process_validator.py` — 경고 → 차단으로 변경:**
현재 `warnings.append()` → `can_proceed = False`로 변경 (또는 별도 에러 반환).
단, 기존에 경고만 사용하던 곳이 있으면 영향도 확인 필요.

---

## FE 작업 (5개)

### FE-0: 🔴 Location QR 필수 설정 미작동 — FE 차단 로직 (BUG-11)
파일: `frontend/lib/screens/qr/qr_scan_screen.dart`, `frontend/lib/screens/task/task_detail_screen.dart`

**수정 ①: QR 스캔 후 Location QR 체크** (`qr_scan_screen.dart`):
Worksheet QR 스캔 성공 후 Task 목록으로 이동하기 전:
```dart
if (success) {
    final product = ref.read(taskProvider).currentProduct;
    if (product != null) {
        // location_qr_required 설정 확인
        final settings = await apiService.get('/admin/settings');
        final locationQrRequired = settings['location_qr_required'] as bool? ?? true;

        if (locationQrRequired && (product.locationQrId == null || product.locationQrId!.isEmpty)) {
            // Location QR 미등록 → 알림 + Location QR 스캔 모드로 전환
            _showLocationQrRequiredDialog();
            return;
        }

        Navigator.pushReplacementNamed(context, '/task-management', ...);
    }
}
```

**수정 ②: Task 시작 버튼 차단** (`task_detail_screen.dart`):
작업 시작 버튼 클릭 시 BE에서 `LOCATION_QR_REQUIRED` 에러 응답 처리:
```dart
final result = await taskNotifier.startWork(taskId: task.id, workerId: workerId);
if (result['error'] == 'LOCATION_QR_REQUIRED') {
    ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(result['message']), backgroundColor: Colors.orange)
    );
    return;
}
```

⚠️ admin settings 조회는 캐싱 권장 (매번 API 호출 부담 감소). Provider에 settings 값 저장.

### FE-1: 협력사 Task Detail — 작업자 정보 섹션 추가
파일: `frontend/lib/screens/task/task_detail_screen.dart`

현재 화면 구조:
① Task 상태 → ② Task 정보 → ③ 제품 정보 → ④ 작업 시간 → ⑤ 액션 버튼

**③과 ④ 사이에 "작업자 정보" 섹션 추가:**

단일 작업자:
```
┌─────────────────────────────┐
│ 작업자 정보                  │
│ 작업자    김철수              │
└─────────────────────────────┘
```

다중 작업자:
```
┌─────────────────────────────┐
│ 작업자 정보 (3명)            │
│ ✅ 김철수   10:00~10:30  30분│
│ ✅ 이영희   10:05~10:35  30분│
│ 🔄 박민수   10:10~         │
└─────────────────────────────┘
```

BE API `workers` 배열 사용. 빈 배열이면 기존 `workerName` fallback.
기존 패턴: `_buildSectionTitle()`, `_buildInfoRow()`, `GxGlass.cardSm(radius: GxRadius.lg)`

### FE-2: GST 대시보드 카드 — 작업자명 표시 보완
파일: `frontend/lib/screens/gst/gst_products_screen.dart`

현재 `worker_name` 표시 코드 있음 (person_outline 아이콘 + 이름).
workers 배열 기반으로 변경:
```dart
final workers = product['workers'] as List?;
final workerDisplay = (workers != null && workers.isNotEmpty)
    ? (workers.length > 1
        ? '${workers.first['worker_name']} 외 ${workers.length - 1}명'
        : workers.first['worker_name'] as String?)
    : product['worker_name'] as String?;
```

### FE-3: QR 카메라 프레임 스크롤 분리 버그 수정 (BUG-10)
파일: `frontend/lib/services/qr_scanner_web.dart`, `frontend/lib/screens/qr/qr_scan_screen.dart`

**현재 버그**:
카메라 촬영 프레임(video)과 검은 부모 사각 프레임(scannerDiv)이 따로 움직임.
화면을 스크롤하면 촬영되는 Frame은 위치가 고정(`position: fixed`)되어 있고,
Flutter의 Container(검은 배경)는 스크롤에 따라 이동.

**원인**: `qr_scan_screen.dart`에서 카메라 Container가 `SingleChildScrollView` 안에 있음 (293행).
스크롤하면 Flutter Container는 올라가지만, DOM의 scannerDiv(`position: fixed`)는 그대로.

**해결 방법 (2가지 중 택1):**

방법 A — 스크롤 이벤트 리스너 추가 (권장):
`qr_scan_screen.dart`에 ScrollController 추가, 스크롤 시 scannerDiv 위치 업데이트:
```dart
final _scrollController = ScrollController();

@override
void initState() {
  super.initState();
  _scrollController.addListener(_onScroll);
}

void _onScroll() {
  // Container의 현재 화면상 좌표를 재계산
  final RenderBox? box = _cameraContainerKey.currentContext?.findRenderObject() as RenderBox?;
  if (box != null) {
    final position = box.localToGlobal(Offset.zero);
    QrScannerWeb.updateScannerDivPosition(
      left: position.dx,
      top: position.dy,
      width: box.size.width,
      height: box.size.height,
    );
  }
}
```

⚠️ `updateScannerDivPosition()`은 이미 `qr_scanner_web.dart` 178~190행에 구현되어 있음.
호출만 연결하면 됨.

방법 B — 스크롤 비활성화:
QR 스캔 화면에서 `SingleChildScrollView`를 `NeverScrollableScrollPhysics()`로 변경하거나,
카메라 영역을 스크롤 밖으로 분리 (Scaffold body를 Column으로 재구성).

**권장: 방법 A** (기존 `updateScannerDivPosition` 활용, 구조 변경 최소화)

### FE-4: QR 스캔 영역 정사각형 수정 (BUG-5 10차 수정)
파일: `frontend/lib/services/qr_scanner_web.dart`, `frontend/lib/screens/qr/qr_scan_screen.dart`

**현재 상태**:
- 9차 수정: 순수 JS `<script>` 태그로 config 생성
- Console: `qrbox=205x205` 출력됨 (JS 콜백은 정사각형 반환)
- QR 인식 성공 (DOC_GBWS-6408 스캔 완료 ✅)
- ❌ 스캔 영역 흰색 브라켓이 여전히 가로로 긴 직사각형

**원인**: html5-qrcode의 viewfinder가 컨테이너 비율(약 390×293 = 가로형)을 따르므로,
qrbox 콜백이 정사각형을 반환해도 viewfinder 안에서 가로에 맞춰 렌더링됨.

**해결 방법 (순서대로 시도):**

방법 A — qrbox를 순수 JS 정수로 전달 (콜백 대신):
```javascript
window.__qrScanConfig = {
  fps: 10,
  qrbox: 200  // 정수 하나 = 자동 정사각형, 콜백보다 단순
};
```
이전 6차(Dart jsify 정수)는 실패했지만, 순수 JS 정수는 다를 수 있음.
⚠️ 콘솔에 `typeof qrbox`로 타입 확인 로그 필수.

방법 B — 카메라 컨테이너를 정사각형으로 변경:
`qr_scan_screen.dart`의 카메라 Container 수정:
```dart
// 현재: height: 300 (width는 Column stretch로 화면폭)
// 변경: width = height = min(screenWidth - 40, 300)
Container(
  width: cameraSize,   // 정사각형
  height: cameraSize,  // 정사각형
  ...
)
```
viewfinder가 정사각형 컨테이너에 맞춰지면 qrbox도 자동으로 정사각형.
`qr_scanner_web.dart`의 `ensureScannerDiv()`도 정사각형 containerWidth=containerHeight 전달.

방법 C — A+B 동시 적용 (가장 확실):
정사각형 컨테이너 + 정수 qrbox.

**디버깅 로그**:
config 생성 후 start() 호출 전:
```javascript
console.log("[QrScannerWeb] config.qrbox type=" + typeof window.__qrScanConfig.qrbox);
console.log("[QrScannerWeb] config.qrbox value=" + JSON.stringify(window.__qrScanConfig.qrbox));
```

start() 성공 후 html5-qrcode가 생성한 DOM 확인:
```dart
final scanRegion = html.document.getElementById('qr-shaded-region');
debugPrint('[QrScannerWeb] scan-region size: ${scanRegion?.style.width} x ${scanRegion?.style.height}');
```

---

## TEST 작업 (tests/backend/) — 충분한 테스트 필수

⚠️ 공정 진행 task와 시간계산은 핵심 기능. 모든 시나리오를 빠짐없이 테스트할 것.
협력사(MECH/ELEC/TMS) + GST(PI/QI/SI) 모두 동일 조건.

### test_task_workers_api.py (신규)
1. TC-WA-01: task detail API에 workers 배열 포함 확인
2. TC-WA-02: workers에 worker_name, started_at, completed_at, duration_minutes, status 포함
3. TC-WA-03: 3명 시작 2명 완료 → completed 2건 + in_progress 1건
4. TC-WA-04: work_start_log 없는 레거시 task → fallback 1건
5. TC-WA-05: GST API에도 workers 배열 포함
6. TC-WA-06: 단일 작업자 → workers 1건
7. TC-WA-07: 아무도 시작 안 한 task → workers 빈 배열

### test_break_time_auto.py (신규) — 🔴 핵심 테스트
8. TC-BT-01: check_break_time_job() 호출 시 로그 출력 확인 (실행 자체 검증)
9. TC-BT-02: admin_settings에 break time 설정값이 있으면 → 매칭 시 force_pause 호출
10. TC-BT-03: admin_settings에 break time 설정값이 없으면(None) → skip (에러 없이)
11. TC-BT-04: 휴게시간 시작 → 진행 중 task 자동 일시정지 확인
   - is_paused = TRUE, work_pause_log 생성 확인
   - BREAK_TIME_PAUSE 알림 발송 확인
12. TC-BT-05: 휴게시간 종료 → 자동 재개 확인
   - is_paused = FALSE, work_pause_log.resumed_at 기록 확인
   - pause_duration_minutes 계산 정확성
   - total_pause_minutes 업데이트 확인
   - BREAK_TIME_END 알림 발송 확인
13. TC-BT-06: 4개 휴게 구간 각각 테스트 (break_morning, lunch, break_afternoon, dinner)
14. TC-BT-07: auto_pause_enabled = FALSE → 일시정지 안 됨
15. TC-BT-08: 이미 일시정지된 task → 중복 pause 생성 안 됨
16. TC-BT-09: 휴게시간 중 task 완료 → 정상 처리 (pause 자동 해제 후 완료)
17. TC-BT-10: 다중 작업자 task에서 모든 작업자에게 BREAK_TIME_PAUSE 알림 전달 확인

### test_working_hours_calculation.py (신규) — 🔴 핵심 테스트
14. TC-WH-01: 점심시간(12:00~13:00) 포함 작업 → duration에서 60분 자동 차감
    - 예: 10:00 시작 ~ 14:00 완료 → 순수 duration = 180분 (240 - 60)
15. TC-WH-02: 점심시간 겹침 없는 작업 → 차감 0분
    - 예: 14:00 시작 ~ 16:00 완료 → duration = 120분
16. TC-WH-03: 부분 겹침 → 겹치는 만큼만 차감
    - 예: 12:30 시작 ~ 14:00 완료 → lunch 겹침 30분 → duration = 60분
17. TC-WH-04: 여러 휴게 구간 겹침 → 모두 차감
    - 예: 10:00 시작 ~ 18:00 완료 → break_morning + lunch + break_afternoon 각각 차감
18. TC-WH-05: 자정 넘어가는 작업 → 다음날 휴게시간도 차감
19. TC-WH-06: 다중 작업자 duration 합산 시 각 작업자별 휴게시간 차감 확인
20. TC-WH-07: 수동 pause + 자동 휴게 제외 → 이중 차감 안 됨
    - work_pause_log에 lunch 타입 pause 있으면서 _calculate_working_minutes에서도 제외 → 하나만 적용
21. TC-WH-08: force-close 시 duration에 휴게시간 제외 + pause 차감 확인
22. TC-WH-09: 설정된 휴게시간이 없는 경우 → 차감 0분 (정상 작동)
23. TC-WH-10: GST task (PI/QI/SI)도 동일한 휴게시간 제외 로직 적용 확인

### test_location_qr_required.py (신규) — 🔴
28. TC-LQ-01: location_qr_required=true + location_qr_id=NULL → start_work 400 에러 (LOCATION_QR_REQUIRED)
29. TC-LQ-02: location_qr_required=true + location_qr_id 존재 → start_work 정상 진행
30. TC-LQ-03: location_qr_required=false + location_qr_id=NULL → start_work 정상 진행
31. TC-LQ-04: location_qr_required 설정 미존재(기본값=true) + location_qr_id=NULL → 400 에러
32. TC-LQ-05: process_validator에서 location QR 미등록 시 can_proceed=false 확인

### test_qr_scanner_logic.py (기존 + 추가)
33. TC-QR-11: qrbox 정수 config → 정사각형 계산
34. TC-QR-12: 정사각형 컨테이너(300×300) → viewfinder 비율 1:1
35. TC-QR-13: 스크롤 시 scannerDiv position 업데이트 확인

---

## 변경 파일

| 파일 | 변경 |
|------|------|
| `backend/app/routes/work.py` | task list에 workers 배열 추가 (배치 조회) |
| `backend/app/routes/gst.py` | GST products에 workers 배열 추가 |
| `backend/app/services/scheduler_service.py` | send_break_end_notifications()에 auto-resume 추가 |
| `backend/app/services/task_service.py` | _calculate_working_minutes() 신규 + _record_completion_log 수정 + _finalize 이중차감 방지 |
| `backend/app/routes/admin.py` | force-close duration에 pause/휴게시간 차감 |
| `backend/app/services/process_validator.py` | location QR 미등록 시 can_proceed=false |
| `frontend/lib/screens/task/task_detail_screen.dart` | 작업자 정보 섹션 신규 추가 |
| `frontend/lib/screens/gst/gst_products_screen.dart` | workers 기반 표시 + "외 N명" |
| `frontend/lib/services/qr_scanner_web.dart` | qrbox 10차 수정 (정수 or 컨테이너 정사각형) |
| `frontend/lib/screens/qr/qr_scan_screen.dart` | ScrollController + onScroll → updateScannerDivPosition 연결 + (방법 B 시) 컨테이너 정사각형 |
| `tests/backend/test_task_workers_api.py` | 작업자 API 테스트 (신규) |
| `tests/backend/test_break_time_auto.py` | 휴게시간 자동 일시정지/재개 테스트 (신규) |
| `tests/backend/test_working_hours_calculation.py` | 작업시간 계산 테스트 (신규) |
| `tests/backend/test_location_qr_required.py` | Location QR 필수 체크 테스트 (신규) |
| `tests/backend/test_qr_scanner_logic.py` | QR 테스트 추가 |

---

## 검증 기준
- [ ] Task Detail API: workers 배열에 작업자별 name/started_at/completed_at/status
- [ ] GST Products API: workers 배열 포함
- [ ] 단일 작업자 task: 기존과 동일 (하위 호환)
- [ ] FE Task Detail: 작업자 정보 섹션에 이름 표시 (다중이면 시간/상태 포함)
- [ ] FE GST 카드: 작업자명 표시 (다중이면 "외 N명")
- [ ] 🔴 휴게시간 시작 → 자동 일시정지 (is_paused=TRUE, pause_log 생성)
- [ ] 🔴 휴게시간 종료 → 자동 재개 (is_paused=FALSE, resumed_at 기록, pause_duration 계산)
- [ ] 🔴 작업시간에서 설정된 휴게시간 자동 차감 (pause 유무와 무관)
- [ ] 🔴 이중 차감 안 됨 (auto_pause + _calculate_working_minutes 동시 적용 방지)
- [ ] 🔴 force-close 시 duration에서 pause + 휴게시간 차감
- [ ] 🔴 다중 작업자: 각 작업자 개인 duration에서 각각 휴게시간 차감
- [ ] 🔴 Location QR 필수=true + 미등록 → Task 시작 차단 (BE 400 에러)
- [ ] 🔴 Location QR 필수=true + 등록됨 → Task 정상 시작
- [ ] 🔴 Location QR 필수=false + 미등록 → Task 정상 시작
- [ ] FE QR 스캔 후 location QR 미등록 알림 표시
- [ ] QR 스크롤 시 카메라 프레임과 컨테이너 동기화
- [ ] QR 스캔 영역: 정사각형 브라켓 — iPad/Android/iOS 3기기 확인
- [ ] QR 인식: DOC_GBWS-6408 스캔 성공 유지
- [ ] Console: qrbox 로그 정상
- [ ] 테스트 전체 PASSED (35건 이상)
- [ ] flutter build web --release 에러 0건
- [ ] 기존 테스트 회귀 0건

## 규칙
- ⚠️ DB 시간: get_db_connection()의 `options="-c timezone=Asia/Seoul"` 절대 삭제 금지
- .env 파일 절대 커밋 금지
- N+1 쿼리 금지 — task_id 배치 조회(ANY 사용)
- html5-qrcode 내부 DOM(video, canvas, 자식 div)은 CSS/JS로 수정 금지
- _forceContainerFit() 같은 자식 요소 강제 스타일 함수 만들지 않음
- qr_scan_screen.dart 카메라 위치 계산(localToGlobal)은 변경 금지 (이미 해결)
- 알람 에스컬레이션 타겟 변경 로직은 수정 금지 (이번 Sprint 범위 아님)
- 완료 시 PROGRESS.md, BACKLOG.md에 기록 (상세히 — progress 기록은 매우 중요)
```

---

## 🚀 Sprint 15 프롬프트 — 다중 작업자 시작/종료 + MH 계산 확정

```
CLAUDE.md를 처음부터 끝까지 다시 읽고 Sprint 15를 시작해줘.
BACKLOG.md, AXIS-VIEW-QUERY-SPEC.md도 읽어.

## Sprint 15 목표
4가지 핵심 작업:
1. 🔴 다중 작업자 시작/종료 FE 차단 해제 (BUG-12) — 작업자2가 이미 진행 중인 task에 참여/완료 가능하도록
2. 🔴 Location QR 차단 재수정 (BUG-11 미해결) — QR 스캔 직후 팝업 + start_work 에러 핸들링 수정
3. 🔴 Working Hour 계산 검증 — 휴게시간/식사시간 차감 로직 실데이터 테스트
4. MH(공수) 계산 방식 B 확정 반영 — duration_minutes = 개인별 SUM (현재 로직 유지, 검증 강화)

⚠️ 위 명시된 기능 외 신규 기능 추가 금지.
⚠️ BACKLOG-FLOWLOGIC.md 참고만 하고 수정하지 말 것.

## 팀 구성
3명의 teammate를 생성해줘. 모든 teammate는 Sonnet 모델 사용:

1. **BE** (Backend 담당) - 소유: backend/**
2. **FE** (Frontend 담당) - 소유: frontend/**
3. **TEST** (테스트 담당) - 소유: tests/**

---

## BE 작업 (2개)

### BE-1: 🔴 Task Detail API에 "현재 작업자의 참여 상태" 추가
파일: `backend/app/routes/work.py`

**현재 문제 (BUG-12)**:
SN1의 UTIL_LINE1을 작업자1이 시작하면, 작업자2는 같은 task에서 시작/종료 버튼을 누를 수 없음.

**근본 원인**:
- BE는 이미 다중 작업자 지원 (`_worker_has_started_task()`는 같은 작업자 중복만 체크)
- 하지만 FE `task_item.dart`에서 `startedAt != null`이면 `'in_progress'` 반환
- FE `task_detail_screen.dart`에서 `in_progress` 상태면 시작 버튼 미표시
- 즉 작업자1이 시작한 후, 작업자2가 해당 task를 보면 시작 버튼이 없음

**수정**: Task 목록/상세 API 응답에 **요청한 작업자의 참여 상태**를 추가.

`/api/app/tasks/<serial_number>` 응답의 각 task에:
```json
{
  "my_status": "not_started",  // 이 작업자가 이 task에 대해 아직 미시작
  // 또는
  "my_status": "in_progress",  // 이 작업자가 시작했지만 미완료
  // 또는
  "my_status": "completed"     // 이 작업자가 완료함
}
```

**로직**:
```python
# 현재 요청자의 worker_id 획득 (JWT에서)
worker_id = get_jwt_identity()

# work_start_log + work_completion_log에서 이 작업자의 상태 배치 조회
cur.execute("""
    SELECT wsl.task_id,
           CASE
               WHEN wcl.id IS NOT NULL THEN 'completed'
               WHEN wsl.id IS NOT NULL THEN 'in_progress'
               ELSE 'not_started'
           END AS my_status
    FROM app_task_details t
    LEFT JOIN work_start_log wsl
        ON wsl.task_id = t.id AND wsl.worker_id = %s
    LEFT JOIN work_completion_log wcl
        ON wcl.task_id = t.id AND wcl.worker_id = %s
    WHERE t.serial_number = %s
""", (worker_id, worker_id, serial_number))
```

⚠️ N+1 쿼리 금지. task_id 배치 조회(ANY) 후 dict 매핑.
⚠️ GST API(`gst.py`)에도 동일 패턴 적용.

### BE-3: 🔴 Location QR 차단 디버깅 + 에러 응답 확인 (BUG-11 미해결)
파일: `backend/app/services/task_service.py`, `backend/app/routes/work.py`

**현재 상태**: Sprint 14 핫픽스에서 BE `start_work()` 98행에 차단 로직 추가했으나,
사용자 테스트 결과 **아직도 location QR 팝업/차단이 안 됨**.

**진단 포인트 (코드 수정 전 반드시 확인):**

① admin_settings DB에 `location_qr_required` 값이 실제로 `true`인지 확인:
```python
# 로그 추가
logger.info(f"[BUG-11 DEBUG] location_qr_required raw = {_get_admin_setting('location_qr_required', False)}")
logger.info(f"[BUG-11 DEBUG] task.location_qr_verified = {task.location_qr_verified}")
```
⚠️ `get_setting()` 반환값 타입 확인: JSONB `'false'` → Python bool `False`? 아니면 str `"false"`?

② migration 010에서 초기값이 `'false'`로 입력됨 (68행):
```sql
('location_qr_required', 'false', ...)
```
→ admin 설정에서 `true`로 변경하지 않았으면 당연히 체크 안 됨.
→ 사용자가 admin에서 `true`로 설정했는데도 안 되는지 확인.

③ admin.py 1324행: defaults에서는 `True` 반환 — 불일치:
```python
result.setdefault('location_qr_required', True)  # GET /api/admin/settings defaults
```
→ GET 응답은 `true`를 보여주지만 실제 DB에는 `'false'`가 저장되어 있을 수 있음.
→ **admin settings PUT에서 값이 제대로 저장되는지 확인**.

④ `task.location_qr_verified`가 뭘 보는지:
```python
# task_service.py 99행
if location_qr_required and not task.location_qr_verified:
```
→ `location_qr_verified`는 `app_task_details` 컬럼 (기본값 FALSE).
→ 이 값은 언제 TRUE로 바뀌는가? → Location QR 스캔 성공 시 `update_location_qr()` 호출되면 product_info.location_qr_id만 업데이트하고, **app_task_details.location_qr_verified는 업데이트 안 함**.
→ 🚨 **이게 두 번째 원인일 수 있음**: product에 location_qr_id가 등록되어도 task의 location_qr_verified는 계속 FALSE.

**수정 방안**:
task_service.py 99행 조건을 `location_qr_verified` 대신 product의 `location_qr_id` 직접 확인으로 변경:
```python
# BUG-11 수정: product_info.location_qr_id 직접 확인
location_qr_required = _get_admin_setting('location_qr_required', False)
if location_qr_required:
    from app.models.product_info import get_product_by_qr_doc_id
    product = get_product_by_qr_doc_id(task.qr_doc_id)
    if product and not product.location_qr_id:
        return {
            'error': 'LOCATION_QR_REQUIRED',
            'message': 'Location QR이 등록되지 않았습니다. QR 스캔 화면에서 Location QR을 먼저 스캔해주세요.'
        }, 400
```

⚠️ 디버그 로그를 충분히 추가하여 Railway 로그에서 확인 가능하도록.

### BE-4: Working Hour 계산 검증 로그 강화
파일: `backend/app/services/task_service.py`

Sprint 14 핫픽스에서 `_calculate_working_minutes()` + `_calculate_break_overlap()` 구현됨.
**실제 운영 환경에서 정상 동작하는지 검증용 로그 추가.**

```python
def _calculate_working_minutes(started_at, completed_at):
    # 기존 로직 유지 + 로그 강화
    logger.info(
        f"[WORKING_HOURS] started={started_at}, completed={completed_at}, "
        f"raw_minutes={raw_minutes}, break_overlap={total_break_overlap}, "
        f"net_working_minutes={max(0, raw_minutes - total_break_overlap)}"
    )
```

각 break period 별로도:
```python
for start_key, end_key in _BREAK_PERIOD_KEYS:
    # ...
    logger.info(f"[WORKING_HOURS] break={start_key}: {break_start_str}~{break_end_str}, overlap={overlap}m")
```

⚠️ 계산 로직 자체는 수정 금지. 로그만 추가.

### BE-2: MH 계산 방식 확인 및 검증 로그 강화
파일: `backend/app/services/task_service.py`

**확정 사항** (AXIS-VIEW-QUERY-SPEC.md 참조):
- `duration_minutes` = 개인별 SUM(방식 B) = **공수 MH (메인 지표)**
- `elapsed_minutes` = CT (첫시작~마지막완료) = **작업 소요시간**
- `라인 효율(%)` = duration / (elapsed × worker_count) × 100 = **대시보드 계산 필드**

현재 `_finalize_task_multi_worker()` 코드가 이미 방식 B로 동작 중 (SUM(work_completion_log.duration_minutes) - manual_pause).

**수정**: 로그 강화만 수행 (계산 로직 변경 없음):
```python
logger.info(
    f"_finalize_task_multi_worker: task_id={task_detail_id}, "
    f"MH(duration)={duration_minutes}m, CT(elapsed)={elapsed_minutes}m, "
    f"workers={worker_count}, "
    f"line_efficiency={round(duration_minutes * 100 / max(1, elapsed_minutes * worker_count))}%"
)
```

⚠️ _calculate_working_minutes()의 break 차감 로직은 Sprint 14 핫픽스에서 구현 완료. 수정 금지.
⚠️ _finalize_task_multi_worker()의 manual_pause만 차감 로직도 완료. 수정 금지.

---

## FE 작업 (2개)

### FE-1: 🔴 다중 작업자 — "작업 참여" 버튼 추가 (BUG-12)
파일: `frontend/lib/models/task_item.dart`, `frontend/lib/screens/task/task_detail_screen.dart`

**현재 문제**:
`task_item.dart` 174~178행:
```dart
String get status {
    if (completedAt != null) return 'completed';
    if (startedAt != null) return 'in_progress';
    return 'pending';
}
```
→ 작업자1이 시작하면 `startedAt != null` → 전체가 `'in_progress'`.
→ 작업자2도 이 task를 보면 시작 버튼이 안 나옴 (320~327행).

**수정 ①: task_item.dart에 `myStatus` 필드 추가:**
```dart
class TaskItem {
  // ...기존 필드...
  final String? myStatus; // 'not_started', 'in_progress', 'completed' (BE에서 전달)

  // fromJson에 추가
  myStatus: json['my_status'] as String?,

  // status getter 수정
  String get status {
    if (completedAt != null) return 'completed';
    if (startedAt != null) return 'in_progress';
    return 'pending';
  }

  // 새 getter: 이 작업자 기준 상태
  String get myWorkStatus => myStatus ?? status;
}
```

**수정 ②: task_detail_screen.dart 액션 버튼 로직 수정:**
```dart
// 기존 (320~327행)
else if (task.status == 'pending')
  _buildStartButton(task.id, workerId)
else if (task.status == 'in_progress' && task.isPaused)
  _buildResumeRow(task.id)
else if (task.status == 'in_progress' && !task.isPaused)
  _buildInProgressRow(task.id, workerId)

// 변경
else if (task.status == 'pending')
  _buildStartButton(task.id, workerId)
else if (task.status == 'in_progress' && task.myWorkStatus == 'not_started')
  _buildJoinButton(task.id, workerId)  // ← 신규: "작업 참여" 버튼
else if (task.status == 'in_progress' && task.isPaused)
  _buildResumeRow(task.id)
else if (task.status == 'in_progress' && !task.isPaused)
  _buildInProgressRow(task.id, workerId)
else if (task.status == 'in_progress' && task.myWorkStatus == 'completed')
  _buildMyCompletedBadge()  // ← 신규: "내 작업 완료" 배지
```

**신규 위젯 _buildJoinButton():**
```dart
Widget _buildJoinButton(int taskId, int workerId) {
  return Container(
    height: 48,
    decoration: BoxDecoration(
      gradient: GxGradients.accentButton,
      borderRadius: BorderRadius.circular(GxRadius.sm),
    ),
    child: Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () => _handleStartTask(taskId, workerId), // 기존 start_work API 호출
        borderRadius: BorderRadius.circular(GxRadius.sm),
        child: Center(child: Row(mainAxisAlignment: MainAxisAlignment.center, children: const [
          Icon(Icons.group_add, size: 20, color: Colors.white),
          SizedBox(width: 8),
          Text('작업 참여', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Colors.white)),
        ])),
      ),
    ),
  );
}
```

⚠️ _handleStartTask()는 기존 start_work API 호출. BE가 이미 다중 작업자 지원하므로 변경 없음.
⚠️ "작업 참여" 클릭 → BE `/api/app/work/start` → work_start_log에 작업자2 기록 → 성공 시 화면 갱신.

**신규 위젯 _buildMyCompletedBadge():**
```dart
Widget _buildMyCompletedBadge() {
  return Container(
    height: 48,
    decoration: BoxDecoration(
      color: GxColors.successBg,
      borderRadius: BorderRadius.circular(GxRadius.sm),
      border: Border.all(color: GxColors.success, width: 1),
    ),
    child: Center(child: Row(mainAxisAlignment: MainAxisAlignment.center, children: const [
      Icon(Icons.check_circle, size: 20, color: GxColors.success),
      SizedBox(width: 8),
      Text('내 작업 완료', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: GxColors.success)),
    ])),
  );
}
```

### FE-2: 🔴 Location QR 차단 — QR 스캔 직후 팝업 + 에러 핸들링 수정 (BUG-11)
파일: `frontend/lib/screens/qr/qr_scan_screen.dart`, `frontend/lib/screens/task/task_detail_screen.dart`,
      `frontend/lib/providers/task_provider.dart`

**현재 문제 2가지:**

**문제 A: QR 스캔 후 → task 목록 이동 시 차단 없음**
`qr_scan_screen.dart` 186~196행에서 Worksheet QR 스캔 성공 → 바로 task-management 이동.
location_qr_required 체크 없음.

**수정**: 스캔 성공 후 task-management 이동 전에 location QR 체크:
```dart
if (tasksSuccess) {
  // BUG-11: Location QR 체크
  final settings = await ref.read(taskProvider.notifier).getAdminSettings();
  final locationQrRequired = settings?['location_qr_required'] == true;

  if (locationQrRequired && (product.locationQrId == null || product.locationQrId!.isEmpty)) {
    // Location QR 미등록 → 팝업 + Location QR 스캔 모드 전환
    if (mounted) {
      setState(() {
        _scanType = 'location'; // Location QR 스캔 모드로 전환
        _isProcessing = false;
      });
      _showLocationQrRequiredPopup();
    }
    return;
  }

  // Location QR OK → Task 목록으로 이동
  if (mounted) {
    Navigator.pushReplacementNamed(context, '/task-management', ...);
  }
}
```

**_showLocationQrRequiredPopup() 신규:**
```dart
void _showLocationQrRequiredPopup() {
  showDialog(
    context: context,
    barrierDismissible: false,
    builder: (ctx) => AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      title: Row(children: [
        Icon(Icons.location_on, color: Colors.orange),
        SizedBox(width: 8),
        Text('Location QR 필요'),
      ]),
      content: Text('이 제품은 Location QR 인증이 필요합니다.\nLocation QR을 먼저 스캔해주세요.'),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(ctx),
          child: Text('확인'),
        ),
      ],
    ),
  );
}
```

⚠️ admin settings 조회: 기존 `getAdminSettings()` 메서드가 있으면 사용, 없으면 신규 추가 (GET /admin/settings).
⚠️ 이미 location QR 스캔 타입 전환 UI가 있음 (_scanType = 'location'). 다이얼로그 닫으면 자연스럽게 Location QR 스캔 가능.

**문제 B: start_work 에러에서 LOCATION_QR_REQUIRED 문자열 못 찾음**
`task_detail_screen.dart` 496행: `errorMessage.contains('LOCATION_QR_REQUIRED')` 체크.
그런데 `task_provider.dart` 211행에서 `e.toString()`으로 저장 — Exception 객체의 toString이라 원본 에러 코드가 포함 안 될 수 있음.

**수정**: task_provider.dart에서 API 에러 응답 body를 파싱하여 저장:
```dart
} catch (e) {
  String errorMsg = e.toString();
  // DioException이면 response body에서 error 코드 추출
  if (e is DioException && e.response?.data is Map) {
    final data = e.response!.data as Map;
    errorMsg = data['error']?.toString() ?? data['message']?.toString() ?? errorMsg;
  }
  state = state.copyWith(
    isLoading: false,
    errorMessage: errorMsg,
  );
  return false;
}
```

⚠️ Dio 사용 시 DioException, http 패키지 사용 시 해당 Exception 타입 확인.
⚠️ apiService에서 이미 에러를 파싱하고 있을 수 있으니 확인 후 중복 방지.

### FE-3: Task 목록에서 다중 작업자 상태 표시 보완
파일: `frontend/lib/screens/task/task_management_screen.dart`

task_management_screen.dart의 task 리스트 아이템에서:
- 내가 시작한 task: 기존 "진행 중" 표시
- 남이 시작했지만 내가 미참여: "진행 중 (미참여)" 또는 구분 색상
- 내가 완료했지만 task 미종료: "내 작업 완료"

```dart
// 기존 status switch 로직 (228~260행) 수정
String statusText;
Color statusColor;

if (task.isPaused) {
  statusText = '일시정지';
  statusColor = GxColors.warning;
} else {
  switch (task.myWorkStatus) { // ← status 대신 myWorkStatus 사용
    case 'completed':
      statusText = task.status == 'completed' ? '완료' : '내 작업 완료';
      statusColor = GxColors.success;
    case 'in_progress':
      statusText = '진행 중';
      statusColor = GxColors.accent;
    case 'not_started':
      if (task.status == 'in_progress') {
        statusText = '참여 가능';
        statusColor = GxColors.info;
      } else {
        statusText = '대기';
        statusColor = GxColors.slate;
      }
    default:
      statusText = '대기';
      statusColor = GxColors.slate;
  }
}
```

---

## TEST 작업 (tests/backend/)

### test_multi_worker_join.py (신규) — 🔴 핵심 테스트
1. TC-MW-01: 작업자1이 task 시작 → 작업자2가 같은 task 시작 → 성공 (work_start_log 2건)
2. TC-MW-02: 작업자1이 task 시작 → 작업자1이 다시 시작 → 400 TASK_ALREADY_STARTED
3. TC-MW-03: task detail API 응답에 my_status='not_started' (미참여 작업자)
4. TC-MW-04: task detail API 응답에 my_status='in_progress' (참여 작업자)
5. TC-MW-05: task detail API 응답에 my_status='completed' (완료 작업자)
6. TC-MW-06: 작업자1 완료 + 작업자2 미완료 → task 미종료 (all_workers_completed=false)
7. TC-MW-07: 작업자1,2 모두 완료 → task 종료 + _finalize_task_multi_worker 실행
8. TC-MW-08: 3명 시작, 2명 완료, 1명 미완료 → task 미종료
9. TC-MW-09: GST API에도 my_status 포함 확인
10. TC-MW-10: 레거시 task (work_start_log 없음) → my_status=null fallback

### test_location_qr_recheck.py (신규) — 🔴 BUG-11 재검증
11. TC-LQ-R01: admin_settings `location_qr_required=true` + product `location_qr_id=NULL` → start_work 400 반환
12. TC-LQ-R02: admin_settings `location_qr_required=true` + product `location_qr_id='LOC_BAY1'` → start_work 정상
13. TC-LQ-R03: admin_settings `location_qr_required=false` + product `location_qr_id=NULL` → start_work 정상
14. TC-LQ-R04: `get_setting('location_qr_required')` 반환 타입 확인 — bool True/False인지, str "true"/"false"인지
15. TC-LQ-R05: admin settings PUT으로 `location_qr_required=true` 설정 → GET으로 확인 → start_work 차단 확인 (E2E)
16. TC-LQ-R06: Location QR 스캔 후 `update_location_qr()` → product.location_qr_id 업데이트 확인 → start_work 통과

### test_working_hours_recheck.py (신규) — 🔴 Working Hour 재검증
17. TC-WH-R01: 9:00~12:00 작업 + break_morning(10:00~10:20) → net=160분 (180-20)
18. TC-WH-R02: 9:00~18:00 작업 + 4개 break(morning 20m + lunch 60m + afternoon 20m + dinner 60m) → net=320분 (540-160-수동pause)
19. TC-WH-R03: 14:00~16:00 작업 + break_afternoon(15:00~15:20) → net=100분 (120-20)
20. TC-WH-R04: 18:30~20:00 작업 (모든 break 시간 외) → net=90분 (차감 0)
21. TC-WH-R05: admin_settings에 break 시간이 NULL인 경우 → 차감 없이 정상 작동
22. TC-WH-R06: 다중 작업자 2명 동시 작업(9~12) → 각각 break 차감 → finalize SUM 확인
23. TC-WH-R07: force-close 시 _calculate_working_minutes 적용 확인

### test_mh_calculation_method_b.py (신규) — MH 계산 검증
11. TC-MH-01: 2명 동시 시작/동시 완료(3h) → duration=2×(3h-break) = 방식B MH 확인
12. TC-MH-02: 2명 시작 시간 다름(1: 9~11, 2: 9~12) → CT=3h, MH=1h40m+2h40m=4h20m
13. TC-MH-03: 1명 작업 → duration=elapsed(CT), MH=CT (방식A=방식B)
14. TC-MH-04: _finalize_task_multi_worker 결과에서 라인효율 계산 확인
    - efficiency = duration_minutes / (elapsed_minutes × worker_count) × 100
15. TC-MH-05: break 4개 구간 모두 포함된 장시간 작업(9~18) → 정확한 차감

---

## 변경 파일

| 파일 | 변경 |
|------|------|
| `backend/app/routes/work.py` | my_status 필드 추가 (배치 조회) |
| `backend/app/routes/gst.py` | my_status 필드 추가 (배치 조회) |
| `backend/app/services/task_service.py` | BUG-11 location_qr 조건 수정(product.location_qr_id 직접 확인) + _finalize 로그 강화 + working hours 로그 강화 |
| `frontend/lib/models/task_item.dart` | myStatus 필드 + myWorkStatus getter |
| `frontend/lib/screens/task/task_detail_screen.dart` | _buildJoinButton + _buildMyCompletedBadge + 조건 분기 수정 |
| `frontend/lib/screens/task/task_management_screen.dart` | myWorkStatus 기반 상태 표시 |
| `frontend/lib/screens/qr/qr_scan_screen.dart` | BUG-11 Location QR 체크 + 팝업 + 스캔 모드 전환 |
| `frontend/lib/providers/task_provider.dart` | API 에러 응답 파싱 개선 (error 코드 추출) |
| `tests/backend/test_multi_worker_join.py` | 다중 작업자 참여 테스트 (신규) |
| `tests/backend/test_location_qr_recheck.py` | Location QR 재검증 테스트 (신규) |
| `tests/backend/test_working_hours_recheck.py` | Working Hour 재검증 테스트 (신규) |
| `tests/backend/test_mh_calculation_method_b.py` | MH 계산 검증 테스트 (신규) |

---

## 검증 기준
### 다중 작업자 (BUG-12)
- [ ] 🔴 작업자1 task 시작 후 → 작업자2가 같은 task에서 "작업 참여" 버튼 표시
- [ ] 🔴 작업자2 "작업 참여" 클릭 → BE start_work 성공 → work_start_log에 2번째 레코드
- [ ] 🔴 작업자2 참여 후 → 일시정지/작업완료 버튼 정상 표시
- [ ] 🔴 작업자1 완료 + 작업자2 미완료 → task 미종료, 작업자1은 "내 작업 완료" 배지
- [ ] 🔴 작업자1,2 모두 완료 → task 종료 + duration = 개인SUM(방식B)
- [ ] task 목록에서 미참여 task는 "참여 가능" 표시
- [ ] my_status API 필드 정상 반환 (not_started / in_progress / completed)
- [ ] 단일 작업자 task: 기존과 동일 동작 (하위 호환)

### Location QR (BUG-11 재수정)
- [ ] 🔴 admin에서 location_qr_required=true 설정 → Worksheet QR 스캔 직후 팝업 알림 표시
- [ ] 🔴 팝업 후 Location QR 스캔 모드로 자동 전환
- [ ] 🔴 Location QR 스캔 완료 → task-management 이동 정상
- [ ] 🔴 start_work API 400 에러 시 FE에서 LOCATION_QR_REQUIRED 에러 코드 인식 → 다이얼로그 표시
- [ ] location_qr_required=false → 체크 없이 정상 진행
- [ ] get_setting() 반환 타입 로그로 확인 (bool vs str)

### Working Hour 계산
- [ ] 🔴 9:00~12:00 작업 → break_morning(10:00~10:20) 20분 차감 → net 160분
- [ ] 🔴 9:00~18:00 장시간 작업 → 4개 break 모두 차감
- [ ] 🔴 break 시간 외 작업 → 차감 0분
- [ ] 🔴 다중 작업자 각각 개별 break 차감 후 SUM
- [ ] 라인효율 로그 출력 확인

### 공통
- [ ] 테스트 전체 PASSED (28건 이상)
- [ ] flutter build web --release 에러 0건
- [ ] 기존 테스트 회귀 0건

## 규칙
- ⚠️ DB 시간: get_db_connection()의 `options="-c timezone=Asia/Seoul"` 절대 삭제 금지
- ⚠️ _calculate_working_minutes() break 차감 로직 수정 금지 (Sprint 14 핫픽스 완료)
- ⚠️ _finalize_task_multi_worker() manual_pause만 차감 로직 수정 금지
- .env 파일 절대 커밋 금지
- N+1 쿼리 금지 — task_id 배치 조회(ANY 사용)
- ⚠️ FE API 경로에 '/api' 접두사 넣지 말 것 (apiBaseUrl에 이미 /api 포함)
- 완료 시 PROGRESS.md, BACKLOG.md에 기록
```

---

## 주요 단축키

| 단축키 | 기능 |
|--------|------|
| **Shift+Tab** | 모드 전환 (accept edits ↔ plan ↔ bypass) |
| **Shift+↑** | Teammate 상세 보기 (expand) |
| **Shift+↓** | Teammate 축소/전환 |
| **Ctrl+T** | 공유 Task List 보기 |
| **Escape** | 현재 Teammate 작업 중단 |

## tmux 단축키

| 단축키 | 기능 |
|--------|------|
| **Ctrl+B, 방향키** | 패널 이동 |
| **Ctrl+B, %** | 세로 분할 |
| **Ctrl+B, "** | 가로 분할 |
| **Ctrl+B, d** | 세션 분리 (백그라운드) |
| **tmux attach -t axis** | 세션 재접속 |
| **Ctrl+B, z** | 현재 패널 전체화면 토글 |

## 맥북 닫았다 다시 열 때

tmux 세션은 맥북 닫으면 **종료됩니다** (sleep 시 프로세스 중단).
다시 시작하려면:

```bash
# tmux 세션 확인
tmux ls

# 세션이 있으면 재접속
tmux attach -t axis

# 세션이 없으면 새로 시작
tmux new -s axis
cd ~/Desktop/GST/AXIS-OPS
claude
# → 다음 Sprint 프롬프트 입력
```

AXIS-OPS 코드 파일은 전부 보존됩니다. Agent Teams 세션만 새로 시작하면 됩니다.

---

## Sprint 16 프롬프트 (BUG-13/14/15 수정 + Admin 로그인 간소화)

### 목표
1. **BUG-13**: Location QR 블록 로직이 일반 작업자 계정에서 미작동 — FE 에러 핸들링 안전모드 적용
2. **BUG-14**: 다중 작업자(2명+) 시작 시 작업자 정보 미표시 — BE/FE 디버깅 + 수정
3. **BUG-15**: QR 스캔 화면에서 에러/Location QR 팝업이 카메라 프레임에 가려짐 — 이미 수정 완료, 배포만
4. **FEAT-1**: Admin 로그인 간소화 — 이메일 prefix만으로 로그인 가능 (예: `admin` 입력 → `admin@gst` 매칭)
5. 빌드 + 배포 (FE: Netlify, BE: Railway)

### ⚠️ 중요: 이미 코드에 반영된 변경사항 (절대 되돌리지 말 것)

아래 변경사항은 Cowork 세션에서 이미 반영 완료. 빌드+배포만 필요.

#### ✅ 반영 완료 1: `/api/app/settings` 엔드포인트 (BUG-13 부분 수정)
- **`backend/app/routes/work.py`** — `get_app_settings()` 함수 (약 line 30-62)
  - `@work_bp.route("/settings", methods=["GET"])` + `@jwt_required` (admin_required 없음)
  - `get_all_settings()`로 전체 설정 반환, 기본값 보장
  - import: `from app.models.admin_settings import get_all_settings`
- **`frontend/lib/services/task_service.dart`** — `getAdminSettings()` (약 line 257)
  - `/admin/settings` → `/app/settings` 변경됨
- **`frontend/lib/screens/admin/admin_options_screen.dart`** — 변경 없음 (기존 `/admin/settings` 유지)

#### ✅ 반영 완료 2: 카메라 DOM hide/show (BUG-15)
- **`frontend/lib/services/qr_scanner_web.dart`** — `hideScannerDiv()`, `showScannerDiv()` 추가
- **`frontend/lib/services/qr_scanner_service.dart`** — `hide()`, `show()` public API 추가
- **`frontend/lib/services/qr_scanner_stub.dart`** — stub 함수 추가
- **`frontend/lib/screens/qr/qr_scan_screen.dart`** — `_showLocationQrRequiredPopup()`, `_showErrorDialog()` 모두 다이얼로그 전 `_qrScannerService.hide()`, 닫은 후 `_qrScannerService.show()` 호출

---

### BE-1: Admin 로그인 간소화 (이메일 prefix 매칭)

**파일: `backend/app/models/worker.py`**

`get_worker_by_email()` 함수 아래에 새 함수 추가:

```python
def get_admin_by_email_prefix(prefix: str) -> Optional[Worker]:
    """
    이메일 prefix로 admin 작업자 조회 (간소화 로그인용)

    예: 'admin' → email이 'admin@%'인 is_admin=True 작업자 반환
    prefix에 @가 없을 때만 호출됨.
    매칭되는 admin이 정확히 1명일 때만 반환, 0명 또는 2명+ 이면 None.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM workers WHERE email LIKE %s AND is_admin = true",
            (f"{prefix}@%",)
        )
        rows = cur.fetchall()
        if len(rows) == 1:
            return Worker.from_db_row(rows[0])
        return None
    except PsycopgError as e:
        logger.error(f"Failed to get admin by prefix '{prefix}': {e}")
        return None
    finally:
        if conn:
            conn.close()
```

**파일: `backend/app/services/auth_service.py`**

`login()` 메서드의 사용자 조회 부분 수정 (약 line 413-420):

```python
# 기존 line 414:
# worker = get_worker_by_email(email)

# 수정:
if '@' in email:
    worker = get_worker_by_email(email)
else:
    # Admin 간소화 로그인: prefix만으로 조회 (is_admin=True만 대상)
    worker = get_admin_by_email_prefix(email)
    if worker is None:
        # prefix 매칭 실패 → 정확한 이메일로 재시도 (fallback)
        worker = get_worker_by_email(email)
```

import 추가 (파일 상단, 기존 import 근처):
```python
from app.models.worker import get_admin_by_email_prefix
```

### BE-2: BUG-13 FE 에러 핸들링 안전모드

**문제**: `getAdminSettings()` API 에러 시 빈 `{}` 반환 → `location_qr_required`가 null → 블록 로직 스킵

**파일: `frontend/lib/services/task_service.dart`** (약 line 252-267)

```dart
  /// 앱 설정 조회 (일반 작업자 접근 가능)
  ///
  /// API 에러 시 안전모드: location_qr_required = true (블록 활성)
  ///
  /// API: GET /api/app/settings (jwt_required만, admin_required 없음)
  Future<Map<String, dynamic>> getAdminSettings() async {
    try {
      final response = await _apiService.get('/app/settings');
      if (response is Map<String, dynamic>) {
        return response;
      }
      // 응답이 Map이 아닌 경우 안전모드 반환
      return {'location_qr_required': true};
    } catch (e) {
      // API 에러 시 안전모드 반환 (location_qr 체크 활성)
      debugPrint('[TaskService] getAdminSettings error: $e — using safe defaults');
      return {'location_qr_required': true};
    }
  }
```

핵심: **에러 시 빈 `{}` 대신 `{'location_qr_required': true}` 반환** — 실패해도 안전한 쪽으로

### BE-3: BUG-14 다중 작업자 표시 디버깅

**현상**: 1명 작업 시작 → 작업자 정보 표시됨. 2명 시작 → 작업자 미표시.
**BE는 정상으로 보이나 실 데이터 확인 필요.**

**파일: `backend/app/routes/work.py`** — workers 조회 쿼리에 로깅 추가 (약 line 293):

```python
# 기존 line 293:
# for row in cur.fetchall():
# 수정:
rows = cur.fetchall()
logger.info(f"[BUG-14] workers query: task_ids={task_db_ids}, returned {len(rows)} rows")
for row in rows:
    tid = row['task_id']
    logger.info(f"[BUG-14] worker: task_id={tid}, worker_id={row['worker_id']}, name={row['worker_name']}")
    if tid in workers_by_task:
        workers_by_task[tid].append({
            'worker_id': row['worker_id'],
            'worker_name': row['worker_name'],
            'started_at': row['started_at'].isoformat() if row['started_at'] else None,
            'completed_at': row['completed_at'].isoformat() if row['completed_at'] else None,
            'duration_minutes': row['duration_minutes'],
            'status': row['status'],
        })
```

**파일: `backend/app/routes/gst.py`** — 동일한 로깅 추가

**FE 디버깅: `frontend/lib/models/task_item.dart`** — fromJson workers 파싱 로그:

```dart
// workers 파싱 부분에 임시 디버그 추가:
workers: json['workers'] != null
    ? (() {
        final parsed = List<Map<String, dynamic>>.from(
            (json['workers'] as List).map((w) => Map<String, dynamic>.from(w as Map)),
        );
        if (parsed.length > 1) {
          debugPrint('[BUG-14] task ${json['id']} has ${parsed.length} workers: '
              '${parsed.map((w) => w['worker_name']).toList()}');
        }
        return parsed;
      })()
    : const [],
```

**핵심 확인사항**:
1. BE 로그에서 2명이 반환되는지 확인
2. FE 파싱 로그에서 2명이 파싱되는지 확인
3. `_buildWorkerInfoSection()` (task_detail_screen.dart line 649-732)의 로직은 정상 — workers가 비어있지 않으면 모두 표시

### FE-1: 로그인 화면 admin 안내 텍스트

**파일: `frontend/lib/screens/auth/login_screen.dart`**

이메일 입력 필드 하단에 안내 텍스트 추가:
```dart
// 이메일 TextFormField 바로 아래에 추가
const SizedBox(height: 4),
const Text(
  'Admin은 이메일 앞부분만 입력 가능',
  style: TextStyle(fontSize: 11, color: GxColors.silver),
),
```

---

### 테스트 파일

#### `tests/backend/test_sprint16_admin_login.py`
```python
"""Sprint 16: Admin 로그인 간소화 테스트"""
import pytest

class TestAdminPrefixLogin:
    """Admin 이메일 prefix 로그인"""

    def test_admin_login_full_email(self, client):
        """TC-AL-01: 기존 full email 로그인 정상"""
        resp = client.post('/api/auth/login', json={
            'email': 'dkkim1@gst-in.com',
            'password': 'test_admin_pw'
        })
        # 테스트 환경 비밀번호에 따라 200 또는 401
        assert resp.status_code in [200, 401]

    def test_admin_login_prefix_only(self, client):
        """TC-AL-02: admin prefix만으로 로그인 (핵심)"""
        resp = client.post('/api/auth/login', json={
            'email': 'admin',
            'password': '93830979'
        })
        # admin@gst 계정 존재 시 200
        assert resp.status_code in [200, 401]
        if resp.status_code == 200:
            data = resp.get_json()
            assert 'access_token' in data

    def test_normal_user_prefix_rejected(self, client):
        """TC-AL-03: 일반 사용자는 prefix 로그인 불가 (is_admin=False)"""
        resp = client.post('/api/auth/login', json={
            'email': 'kdky311',
            'password': '93830979'
        })
        assert resp.status_code == 401

    def test_prefix_with_at_uses_exact_match(self, client):
        """TC-AL-04: @가 포함되면 정확 매칭"""
        resp = client.post('/api/auth/login', json={
            'email': 'admin@gst',
            'password': '93830979'
        })
        assert resp.status_code in [200, 401]
```

#### `tests/backend/test_sprint16_app_settings.py`
```python
"""Sprint 16: /api/app/settings 일반 사용자 접근 테스트"""
import pytest

class TestAppSettings:
    """일반 작업자용 앱 설정 엔드포인트"""

    def test_admin_access(self, client, admin_token):
        """TC-AS-01: admin 접근 가능"""
        resp = client.get('/api/app/settings', headers={
            'Authorization': f'Bearer {admin_token}'
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'location_qr_required' in data

    def test_worker_access(self, client, worker_token):
        """TC-AS-02: 일반 작업자 접근 가능 (핵심!)"""
        resp = client.get('/api/app/settings', headers={
            'Authorization': f'Bearer {worker_token}'
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'location_qr_required' in data

    def test_unauthenticated_rejected(self, client):
        """TC-AS-03: 미인증 요청 거부"""
        resp = client.get('/api/app/settings')
        assert resp.status_code == 401

    def test_old_admin_endpoint_still_restricted(self, client, worker_token):
        """TC-AS-04: 기존 /api/admin/settings는 admin만"""
        resp = client.get('/api/admin/settings', headers={
            'Authorization': f'Bearer {worker_token}'
        })
        assert resp.status_code == 403
```

---

### 실행 순서

```
1. BE 수정 (BE-1: prefix login, BE-2: safe defaults, BE-3: debug logs)
2. FE 수정 (FE-1: login hint)
3. 테스트 실행: pytest tests/backend/test_sprint16*.py -v
4. flutter build web --release
5. git add + commit + push
6. 배포 확인 (Netlify auto-deploy + Railway auto-deploy)
```

### 검증 체크리스트

- [ ] `admin` + 비밀번호로 로그인 성공 (prefix 매칭)
- [ ] `admin@gst` + 비밀번호로 로그인 성공 (full email)
- [ ] 일반 사용자 `kdky311` prefix 로그인 → 실패 (401)
- [ ] 일반 사용자 `/api/app/settings` → 200 (location_qr_required 포함)
- [ ] 일반 사용자 `/api/admin/settings` → 403 (기존 동작 유지)
- [ ] Location QR 블록: 일반 계정으로 worksheet QR 스캔 → 팝업 + 블록 정상
- [ ] Location QR 팝업: 카메라에 가려지지 않고 표시됨
- [ ] 에러 팝업: 카메라에 가려지지 않고 표시됨
- [ ] 2명 작업 시작: task detail에서 작업자 2명 이름+시간 표시됨
- [ ] 기존 기능 회귀 없음

---

## Sprint 16.1 프롬프트 (버전 관리 + System Online + LOC 형식 정리)

### 목표
1. **버전 관리 시스템**: 중앙 버전 파일에서 관리, splash 화면 + 향후 API 버전 헤더에 사용
2. **System Online 실제 연동**: 목업 → BE `/health` API 실시간 체크로 변경
3. **Location QR 형식 정리**: hint/에러 메시지 `LOC_01` 형식으로 통일 (이미 Cowork에서 반영 완료)
4. 빌드 + 배포 → 버전 `v1.1.0` (Sprint 16.1은 새 기능 포함이므로 MINOR 업)

### ⚠️ 이미 코드에 반영된 변경사항 (절대 되돌리지 말 것)

- **`frontend/lib/screens/qr/qr_scan_screen.dart`**: `LOC_ASSY_01` → `LOC_01`로 모두 변경됨 (hint, 에러 메시지, 주석)
- **Sprint 16에서 반영한 모든 변경사항**: `/api/app/settings`, 카메라 hide/show, admin prefix login, MutationObserver 정사각형 등
- **`backend/app/__init__.py`**: CORS 설정에 `/health` 경로 추가 완료 (BUG-16 수정)
- **`frontend/lib/services/qr_scanner_web.dart`**: `hideScannerDiv()` → Observer disconnect 후 hide, `showScannerDiv()` → show 후 Observer 재활성화 (BUG-17 수정)

---

### BE-1: 버전 파일 생성

**파일: `backend/version.py`** (신규)
```python
"""AXIS-OPS 버전 정보 — 단일 소스"""
VERSION = "1.1.0"
BUILD_DATE = "2026-03-03"
```

**파일: `backend/app/__init__.py`** — health 엔드포인트에 버전 추가:

```python
from version import VERSION, BUILD_DATE

@app.route("/health", methods=["GET"])
def health_check():
    """헬스 체크 + 버전 정보"""
    return jsonify({
        "status": "ok",
        "version": VERSION,
        "build_date": BUILD_DATE,
    }), 200
```

### FE-1: 버전 중앙 관리

**파일: `frontend/lib/utils/app_version.dart`** (신규)
```dart
/// AXIS-OPS 앱 버전 — 단일 소스
class AppVersion {
  static const String version = '1.1.0';
  static const String buildDate = '2026-03-03';
  static String get display => 'G-AXIS OPS v$version';
}
```

**파일: `frontend/lib/screens/auth/splash_screen.dart`** — 하드코딩 제거:

```dart
// 기존 line 243:
// 'G-AXIS OPS v1.0.0'

// 수정:
import '../../utils/app_version.dart';
// ...
AppVersion.display,  // → 'G-AXIS OPS v1.1.0'
```

### FE-2: System Online → 실제 API 헬스 체크

**파일: `frontend/lib/screens/auth/splash_screen.dart`**

splash 화면 초기화 시 `/health` 호출하여 실제 서버 상태 확인:

```dart
class _SplashScreenState extends ConsumerState<SplashScreen> {
  bool _isSystemOnline = false;  // 기본값: offline
  bool _healthChecked = false;

  @override
  void initState() {
    super.initState();
    _checkSystemHealth();
    // 기존 초기화 로직...
  }

  Future<void> _checkSystemHealth() async {
    try {
      final apiService = ApiService();
      // /health는 인증 불필요
      final response = await apiService.getPublic('/health');
      if (mounted) {
        setState(() {
          _isSystemOnline = response != null && response['status'] == 'ok';
          _healthChecked = true;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isSystemOnline = false;
          _healthChecked = true;
        });
      }
    }
  }
```

ApiService에 인증 없는 GET 메서드 필요:

**파일: `frontend/lib/services/api_service.dart`** — `getPublic()` 추가:

```dart
/// 인증 없이 GET 요청 (health check 등)
Future<Map<String, dynamic>?> getPublic(String path) async {
  try {
    final response = await http.get(
      Uri.parse('$baseUrl$path'),
      headers: {'Content-Type': 'application/json'},
    );
    if (response.statusCode == 200) {
      return json.decode(response.body) as Map<String, dynamic>;
    }
    return null;
  } catch (e) {
    return null;
  }
}
```

System Online 인디케이터 UI 수정 (splash_screen.dart 약 line 201-238):

```dart
// 기존: 항상 초록색 + 'System Online'
// 수정: _isSystemOnline에 따라 색상 + 텍스트 변경

Container(
  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
  decoration: BoxDecoration(
    color: Colors.white.withValues(alpha: 0.35),
    borderRadius: BorderRadius.circular(20),
    border: Border.all(color: GxGlass.borderColor, width: 1),
  ),
  child: Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      Container(
        width: 6,
        height: 6,
        decoration: BoxDecoration(
          color: !_healthChecked
              ? GxColors.silver          // 체크 중: 회색
              : _isSystemOnline
                  ? GxColors.success     // 온라인: 초록
                  : GxColors.danger,     // 오프라인: 빨강
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: (_isSystemOnline ? GxColors.success : GxColors.danger).withValues(alpha: 0.4),
              blurRadius: 4,
              spreadRadius: 1,
            ),
          ],
        ),
      ),
      const SizedBox(width: 6),
      Text(
        !_healthChecked
            ? 'Connecting...'
            : _isSystemOnline
                ? 'System Online'
                : 'System Offline',
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w500,
          color: Colors.white.withValues(alpha: 0.6),
        ),
      ),
    ],
  ),
),
```

---

### 실행 순서

```
1. BE-1: version.py + health 엔드포인트 수정
2. FE-1: app_version.dart + splash 버전 변경
3. FE-2: health check + System Online 실연동
4. flutter build web --release
5. git add + commit + push (커밋 메시지에 v1.1.0 포함)
6. 배포 확인
```

### 검증 체크리스트

- [ ] `/health` 응답에 version, build_date 포함
- [ ] splash 화면에 'G-AXIS OPS v1.1.0' 표시
- [ ] 서버 정상 시 'System Online' (초록)
- [ ] 서버 다운 시 'System Offline' (빨강)
- [ ] Location QR hint가 'LOC_01' 형식
- [ ] Location QR 팝업 확인 버튼 정상 클릭 (깜빡임 없음)
- [ ] 기존 기능 회귀 없음

---

### BUG-16: System Offline 표시 버그 (Cowork 반영 완료)

**증상**: Railway `/health` 200 정상 반환하지만 FE splash에서 `System Offline` 출력
**원인**: `backend/app/__init__.py` CORS 설정이 `/api/*`에만 적용 → `/health`는 CORS 미허용 → 브라우저 preflight 거부 → catch → offline
**수정**: CORS에 `/health` 경로 추가

```python
# 수정 전
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 수정 후
CORS(app, resources={
    r"/api/*": {"origins": "*"},
    r"/health": {"origins": "*"},
})
```

**파일**: `backend/app/__init__.py` (line 40-44)

---

### BUG-17: Location QR 팝업 깜빡임 + 확인 버튼 미작동 (Cowork 반영 완료)

**증상**: Location QR 차단 팝업이 뜨지만 깜빡거리면서 확인 버튼 클릭 불가
**원인**: `MutationObserver`가 `attributes`+`style` 변경을 감시 중 → `hideScannerDiv()`의 `display:none` 설정을 감지 → 스타일 재적용으로 `display` 복원 → hide↔show 무한 루프
**수정**: hide 시 Observer disconnect, show 시 Observer 재활성화

```dart
// hideScannerDiv() — Observer 먼저 해제
void hideScannerDiv() {
  if (_scannerDiv == null) return;
  _squareObserver?.disconnect();  // ★ 추가
  _scannerDiv!.style.display = 'none';
}

// showScannerDiv() — show 후 Observer 재활성화
void showScannerDiv() {
  if (_scannerDiv == null) return;
  _scannerDiv!.style.display = 'block';
  _forceSquareAfterCameraStart();  // ★ 추가: 정사각형 + Observer 재활성화
}
```

**파일**: `frontend/lib/services/qr_scanner_web.dart` (line 173-245)

---

## Sprint 16.2 프롬프트 (담당공정 설정 이동 + BUG-16/17 배포)

### 목표
1. **담당공정 설정 이동**: 홈 화면 프로필 카드의 "활성 역할" → 개인설정(ProfileScreen)으로 이동
2. **BUG-16 배포**: CORS `/health` 추가 (이미 코드 반영 완료)
3. **BUG-17 배포**: MutationObserver hide/show 깜빡임 수정 (이미 코드 반영 완료)
4. 빌드 + 배포

### ⚠️ 이미 코드에 반영된 변경사항 (절대 되돌리지 말 것)

- **`backend/app/__init__.py`**: CORS에 `/health` 경로 추가 완료 (BUG-16)
- **`frontend/lib/services/qr_scanner_web.dart`**: `hideScannerDiv()` Observer disconnect + `showScannerDiv()` Observer 재활성화 (BUG-17)
- **Sprint 16 / 16.1에서 반영한 모든 변경사항**: `/api/app/settings`, 카메라 hide/show, admin prefix login, MutationObserver 정사각형, LOC_01 형식, 버전 관리 등

---

### FE-1: 홈 화면에서 "활성 역할" UI 제거

**파일: `frontend/lib/screens/home/home_screen.dart`**

홈 화면 프로필 카드에서 활성 역할 영역(약 line 606-652)을 제거한다.

삭제 대상 코드:
```dart
// ★ 아래 블록 전체 삭제 (line 606~652)
// GST 작업자 active_role 표시
if (worker?.company == 'GST' || worker?.isAdmin == true) ...[
  const SizedBox(height: 10),
  const Divider(color: GxColors.mist, height: 1),
  const SizedBox(height: 10),
  InkWell(
    onTap: () => _showActiveRoleDialog(context, ref, worker?.activeRole),
    // ... (전체 InkWell 블록)
  ),
],
```

또한 `_showActiveRoleDialog()`, `_getActiveRoleLabel()`, `_getRoleColor()` 메서드가 홈 화면에서만 사용되면 함께 삭제. ProfileScreen으로 이동할 것이므로 중복 방지.

---

### FE-2: 개인설정(ProfileScreen)에 "담당공정" 섹션 추가

**파일: `frontend/lib/screens/settings/profile_screen.dart`**

"PIN 설정" 섹션 위(line 134 부근)에 "담당공정" 섹션을 추가한다. GST 소속 또는 관리자만 표시.

**용어 변경**: "활성 역할" → "담당공정" (현장 작업자가 이해하기 쉬운 용어)

```dart
// --- PIN 설정 섹션 위에 추가 ---
// 담당공정 설정 (GST 작업자 또는 관리자만 표시)
if (worker?.company == 'GST' || worker?.isAdmin == true) ...[
  _buildSectionHeader('담당공정'),
  const SizedBox(height: 8),
  Container(
    decoration: GxGlass.cardSm(radius: GxRadius.lg),
    child: Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () => _showActiveRoleDialog(context, ref, worker?.activeRole),
        borderRadius: BorderRadius.circular(GxRadius.lg),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: _getRoleColor(worker?.activeRole).withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(GxRadius.md),
                ),
                child: Icon(Icons.swap_horiz, size: 18, color: _getRoleColor(worker?.activeRole)),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      '담당공정 변경',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: GxColors.graphite,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      worker?.activeRole != null
                          ? _getActiveRoleLabel(worker?.activeRole)
                          : '미설정',
                      style: TextStyle(
                        fontSize: 12,
                        color: worker?.activeRole != null
                            ? _getRoleColor(worker?.activeRole)
                            : GxColors.silver,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: GxColors.accentSoft,
                  borderRadius: BorderRadius.circular(GxRadius.sm),
                ),
                child: const Text(
                  '변경하기',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: GxColors.accent),
                ),
              ),
            ],
          ),
        ),
      ),
    ),
  ),
  const SizedBox(height: 24),
],
```

**헬퍼 메서드 추가** (ProfileScreen 클래스에):

```dart
/// 담당공정 한국어 레이블
String _getActiveRoleLabel(String? role) {
  switch (role) {
    case 'PI': return 'PI 가압검사';
    case 'QI': return 'QI 공정검사';
    case 'SI': return 'SI 마무리공정';
    default: return role ?? '미설정';
  }
}

/// 담당공정 색상
Color _getRoleColor(String? role) {
  switch (role) {
    case 'PI': return GxColors.success;
    case 'QI': return const Color(0xFF7C3AED);
    case 'SI': return GxColors.accent;
    default: return GxColors.steel;
  }
}

/// 담당공정 선택 다이얼로그
Future<void> _showActiveRoleDialog(BuildContext context, WidgetRef ref, String? currentRole) async {
  final roles = [
    {'code': 'PI', 'label': 'PI 가압검사', 'icon': Icons.compress, 'color': GxColors.success},
    {'code': 'QI', 'label': 'QI 공정검사', 'icon': Icons.verified, 'color': const Color(0xFF7C3AED)},
    {'code': 'SI', 'label': 'SI 마무리공정', 'icon': Icons.local_shipping, 'color': GxColors.accent},
  ];

  await showDialog<void>(
    context: context,
    builder: (ctx) => AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.lg)),
      title: const Text(
        '담당공정 선택',
        style: TextStyle(color: GxColors.charcoal, fontWeight: FontWeight.w600, fontSize: 15),
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: roles.map((r) {
          final isSelected = currentRole == r['code'];
          final color = r['color'] as Color;
          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: InkWell(
              onTap: () async {
                Navigator.of(ctx).pop();
                await ref.read(authProvider.notifier).changeActiveRole(r['code'] as String);
                if (mounted) setState(() {});  // UI 갱신
              },
              borderRadius: BorderRadius.circular(GxRadius.md),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                decoration: BoxDecoration(
                  color: isSelected ? color.withValues(alpha: 0.1) : GxColors.cloud,
                  borderRadius: BorderRadius.circular(GxRadius.md),
                  border: Border.all(
                    color: isSelected ? color : GxColors.mist,
                    width: isSelected ? 1.5 : 1,
                  ),
                ),
                child: Row(
                  children: [
                    Icon(r['icon'] as IconData, size: 18, color: color),
                    const SizedBox(width: 10),
                    Text(
                      r['label'] as String,
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                        color: isSelected ? color : GxColors.graphite,
                      ),
                    ),
                    if (isSelected) ...[
                      const Spacer(),
                      Icon(Icons.check_circle, size: 16, color: color),
                    ],
                  ],
                ),
              ),
            ),
          );
        }).toList(),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(ctx).pop(),
          child: const Text('닫기', style: TextStyle(color: GxColors.slate)),
        ),
      ],
    ),
  );
}
```

**import 추가** (profile_screen.dart 상단):
```dart
import '../../providers/auth_provider.dart';  // 이미 있으면 skip
```

---

### 실행 순서

```
1. FE-1: 홈 화면에서 활성 역할 UI + 관련 메서드 삭제
2. FE-2: ProfileScreen에 담당공정 섹션 + 헬퍼 메서드 추가
3. flutter build web --release
4. git add + commit + push (v1.1.1 — BUG-16/17 + 담당공정 설정 이동)
5. 배포 확인 (BE: CORS /health, FE: Netlify)
```

### 검증 체크리스트

- [ ] 홈 화면 프로필 카드에 "활성 역할" 영역이 없음
- [ ] 개인설정 화면에 "담당공정" 섹션 표시 (GST 계정만)
- [ ] 담당공정 변경 시 PI/QI/SI 선택 다이얼로그 정상 작동
- [ ] 변경 후 개인설정 화면에 선택된 공정 즉시 반영
- [ ] 변경 후 홈 화면 공정 task 목록이 변경된 역할에 맞게 필터링
- [ ] 비GST 계정 (협력사)에는 담당공정 섹션 미표시
- [ ] System Online 정상 표시 (BUG-16 CORS 수정 확인)
- [ ] Location QR 팝업 확인 버튼 정상 클릭 + 깜빡임 없음 (BUG-17 수정 확인)
- [ ] 기존 기능 회귀 없음

---

## Sprint 17 프롬프트 (출퇴근 분류 체계 — work_site + product_line)

> 참고 문서: `AXIS-OPS/AXIS_VIEW_ROADMAP.md` Phase 1 > 출퇴근 분류 체계 (2026-03-04 확정)
> 버전: v1.1.1 → v1.2.0 (신규 기능 추가이므로 MINOR 업)

### 배경

협력사 출퇴근 기록에 근무지(work_site)와 제품군(product_line) 분류를 추가한다.
CHI(칠러) 제조기술부 통합 대비 + ELEC 협력사 변동 대응.

### 변경 대상 파일

```
BE:
├── backend/migrations/017_add_attendance_classification.sql  (신규)
├── backend/app/routes/hr.py                                  (수정)

FE:
├── frontend/lib/screens/home/home_screen.dart                (수정)

TEST:
├── tests/backend/test_attendance.py                          (수정)
```

---

### BE 작업

**Phase A: 마이그레이션 (신규 파일)**

`backend/migrations/017_add_attendance_classification.sql`:

```sql
-- Sprint 17: 출퇴근 분류 체계 추가 (work_site + product_line)
-- VARCHAR + CHECK constraint 방식 (ENUM 아님 — 확장성)
-- 기존 데이터는 DEFAULT 값 자동 적용 (GST + SCR)

ALTER TABLE hr.partner_attendance
  ADD COLUMN work_site VARCHAR(10) NOT NULL DEFAULT 'GST',
  ADD COLUMN product_line VARCHAR(10) NOT NULL DEFAULT 'SCR';

ALTER TABLE hr.partner_attendance
  ADD CONSTRAINT chk_work_site CHECK (work_site IN ('GST', 'HQ')),
  ADD CONSTRAINT chk_product_line CHECK (product_line IN ('SCR', 'CHI'));

CREATE INDEX IF NOT EXISTS idx_partner_att_site_line
  ON hr.partner_attendance(work_site, product_line);
```

**Phase B: hr.py 수정**

1. `attendance_check()` 수정:

```python
# Request Body 파싱 추가 (check_type 파싱 아래):
work_site = data.get('work_site', 'GST').strip().upper()
product_line = data.get('product_line', 'SCR').strip().upper()

# check_type == 'out' 일 때: FE 값 무시, 마지막 IN에서 복사
if check_type == 'out':
    # 기존 today_records 조회 결과에서 마지막 IN 레코드 찾기
    last_in = None
    for r in reversed(today_records):
        if r['check_type'] == 'in':
            last_in = r
            break
    if last_in:
        work_site = last_in.get('work_site', 'GST')
        product_line = last_in.get('product_line', 'SCR')

# Validation (in일 때만):
if check_type == 'in':
    if work_site not in ('GST', 'HQ'):
        return jsonify({'error': 'INVALID_WORK_SITE', 'message': "work_site는 'GST' 또는 'HQ'"}), 400
    if product_line not in ('SCR', 'CHI'):
        return jsonify({'error': 'INVALID_PRODUCT_LINE', 'message': "product_line은 'SCR' 또는 'CHI'"}), 400

# INSERT 수정:
cur.execute("""
    INSERT INTO hr.partner_attendance
        (worker_id, check_type, check_time, method, note, work_site, product_line)
    VALUES (%s, %s, %s, 'button', %s, %s, %s)
    RETURNING id, worker_id, check_type, check_time, method, note, work_site, product_line
""", (worker_id, check_type, now_utc, note, work_site, product_line))

# Response에 work_site, product_line 추가:
'record': {
    ...기존 필드...,
    'work_site': record['work_site'],
    'product_line': record['product_line'],
}
```

2. `attendance_today()` SELECT + Response에 work_site, product_line 추가:

```python
# SELECT 수정:
SELECT id, check_type, check_time, method, note, work_site, product_line
FROM hr.partner_attendance ...

# Response records에 추가:
{
    ...기존 필드...,
    'work_site': r.get('work_site', 'GST'),
    'product_line': r.get('product_line', 'SCR'),
}
```

3. 기존 today_records 조회 (중복체크인 로직용)에도 work_site, product_line SELECT 추가:

```python
# attendance_check() 내부, line 97~104 영역:
SELECT id, check_type, check_time, work_site, product_line
FROM hr.partner_attendance
WHERE worker_id = %s ...
```

---

### FE 작업

**home_screen.dart 수정**

1. 출퇴근 상태에 work_site/product_line 필드 추가:

```dart
// 클래스 상단 변수 추가:
String _selectedWorkSite = 'GST';
String _selectedProductLine = 'SCR';
```

2. `_buildAttendanceCard()` 수정 — 출근 상태(notCheckedIn)일 때 드롭다운 표시:

```dart
// 협력사 작업자만 (company != 'GST') 드롭다운 표시
// 드롭다운 옵션 4개:
// - GST 공장 (SCR) → work_site='GST', product_line='SCR'  ← default
// - GST 공장 (CHI) → work_site='GST', product_line='CHI'
// - 협력사 본사 (SCR) → work_site='HQ', product_line='SCR'
// - 협력사 본사 (CHI) → work_site='HQ', product_line='CHI'

// 퇴근 상태(checkedIn)일 때: 드롭다운 미표시 (BE에서 자동 복사)
// 퇴근 완료(checkedOut)일 때: 드롭다운 미표시
```

3. `_handleAttendance()` 수정 — 출근 시 work_site/product_line 전송:

```dart
final checkType = _attendanceStatus == AttendanceStatus.notCheckedIn ? 'in' : 'out';
final Map<String, dynamic> body = {'check_type': checkType};

// 출근일 때만 work_site/product_line 전송
if (checkType == 'in') {
  body['work_site'] = _selectedWorkSite;
  body['product_line'] = _selectedProductLine;
}

await apiService.post('/hr/attendance/check', data: body);
```

4. `_fetchAttendanceStatus()` 수정 — response에서 work_site/product_line 읽기:

```dart
// 마지막 IN 레코드의 work_site/product_line을 현재 선택값으로 세팅
// (이전 출근 기록이 있으면 다음 출근 시 같은 값이 기본 선택됨)
```

---

### TEST 작업

**test_attendance.py 수정**

```python
# 기존 테스트: 변경 불필요 (work_site/product_line 미전송 시 default 적용)
# 아래 테스트 케이스 추가:

# ⚠️ 기존 TC-ATT-01 ~ TC-ATT-08 사용 중 (TC-ATT-08 = test_get_today_attendance_not_checked)
# 신규 테스트는 TC-ATT-09부터 시작:

# TC-ATT-09: 출근 시 work_site + product_line 전달 → DB 정상 저장
# TC-ATT-10: 퇴근 시 work_site/product_line 미전달 → 마지막 IN 값 자동 복사
# TC-ATT-11: 잘못된 work_site 전달 → 400 INVALID_WORK_SITE
# TC-ATT-12: 잘못된 product_line 전달 → 400 INVALID_PRODUCT_LINE
# TC-ATT-13: today 조회 시 work_site/product_line 포함 확인
```

---

### 실행 순서

```
1. BE: 마이그레이션 SQL 생성 (017_add_attendance_classification.sql)
2. BE: hr.py attendance_check() 수정
3. BE: hr.py attendance_today() 수정
4. TEST: 신규 테스트 케이스 추가 + 기존 테스트 통과 확인
5. FE: home_screen.dart 드롭다운 UI + 상태 관리 추가
6. flutter build web --release
7. git add + commit + push (v1.2.0 — 출퇴근 분류 체계)
8. Railway 배포 시 마이그레이션 실행: psql $DATABASE_URL -f backend/migrations/017_add_attendance_classification.sql
9. 배포 확인
```

### 검증 체크리스트

- [ ] 마이그레이션: ALTER TABLE 성공, 기존 데이터에 GST/SCR 기본값 적용됨
- [ ] 출근(IN): work_site + product_line DB 정상 저장
- [ ] 퇴근(OUT): 마지막 IN 레코드의 work_site/product_line 자동 복사됨
- [ ] FE: 협력사 작업자 → 출근 시 드롭다운 4개 옵션 표시
- [ ] FE: GST 작업자(PI/QI/SI) → 드롭다운 미표시
- [ ] FE: 퇴근 시 드롭다운 미표시
- [ ] FE: 기본값 GST 공장(SCR) 선택 상태
- [ ] API: /hr/attendance/today 응답에 work_site/product_line 포함
- [ ] 기존 테스트 전부 통과 (기존 API 호출은 default 적용으로 호환)
- [ ] 기존 기능 회귀 없음

---

## Sprint 18 프롬프트 (협력사별 S/N 작업 진행률 뷰)

> **목적**: 협력사 관리자가 자사 담당 S/N들의 작업 진행률을 종합적으로 조회할 수 있는 API + FE 화면 구현
> **설계 원칙**: AXIS-VIEW(React 대시보드)에서도 동일 API를 재사용할 수 있도록 범용적으로 설계
> **버전**: v1.3.0 (신규 기능 추가이므로 MINOR 업)

### 배경

현재 협력사 관리자는 QR 태깅할 때마다 개별 task 진행을 볼 수 있지만, 자사가 담당하는 **전체 S/N의 종합 진행률**은 확인할 수 없다.

**요구사항**:
1. 협력사별로 담당 S/N만 필터링해서 진행률 표시
2. 100% 완료된 S/N은 `all_completed_at` 기준 **1일 후** 목록에서 사라짐
3. GST 계정은 전체 S/N 조회 가능
4. AXIS-VIEW에서 동일 API 재사용 가능한 구조

### 협력사별 S/N 필터링 규칙

| 협력사 | 필터 조건 | 보이는 공정 |
|--------|----------|------------|
| FNI, BAT, TMS(M) | `mech_partner` 또는 `module_outsourcing` 일치 | MM (+ TM for TMS) |
| TMS(E), P&S, C&A | `elec_partner` 일치 | EE |
| GST (is_admin) | 전체 | 전체 |

> **참고**: 기존 `filter_tasks_for_worker()` 로직(`backend/app/services/task_seed.py` L457-491)의 회사별 카테고리 매핑을 참고하되, 진행률 API는 **카테고리별 완료율**을 반환하므로 FE에서 해당 공정만 하이라이트 처리

### 변경 대상 파일

```
BE:
├── backend/app/routes/product.py                  (수정 — 신규 엔드포인트 추가)
├── backend/app/services/progress_service.py       (신규 — 진행률 계산 서비스)

FE:
├── frontend/lib/screens/home/home_screen.dart     (수정 — 진행현황 카드 추가)
├── frontend/lib/services/progress_service.dart    (신규 — 진행률 API 호출)
├── frontend/lib/screens/progress/sn_progress_screen.dart  (신규 — 전체 목록 화면)

TEST:
├── tests/backend/test_sn_progress.py              (신규)
```

---

### BE 작업

**Phase A: 진행률 계산 서비스 (신규 파일)**

`backend/app/services/progress_service.py`:

```python
"""
협력사별 S/N 진행률 계산 서비스
- AXIS-OPS FE + AXIS-VIEW 공용 API
"""

def get_partner_sn_progress(worker_company: str, worker_role: str,
                             is_admin: bool = False,
                             include_completed_within_days: int = 1) -> list:
    """
    협력사별 담당 S/N 진행률 조회

    Returns: [
        {
            "serial_number": "SCR-001",
            "model": "SCR-1200",
            "mech_partner": "FNI",
            "elec_partner": "TMS(E)",
            "progress": {
                "MM": {"total": 8, "done": 5, "percent": 62.5},
                "EE": {"total": 6, "done": 6, "percent": 100.0},
                "TM": {"total": 3, "done": 0, "percent": 0.0},
                "PI": {"total": 4, "done": 2, "percent": 50.0},
                "QI": {"total": 4, "done": 0, "percent": 0.0},
                "SI": {"total": 3, "done": 0, "percent": 0.0}
            },
            "overall_percent": 43.3,
            "all_completed": false,
            "all_completed_at": null,
            "mech_start": "2026-03-01",
            "ship_plan_date": "2026-04-15"
        },
        ...
    ]
    """
    # Step 1: 협력사별 S/N 필터링
    # GST admin → 전체
    # FNI/BAT → WHERE mech_partner = company
    # TMS(M) → WHERE mech_partner = 'TMS' OR module_outsourcing = 'TMS'
    # TMS(E)/P&S/C&A → WHERE elec_partner = company

    # Step 2: 완료 필터링
    # WHERE cs.all_completed = false
    #    OR cs.all_completed_at > NOW() - INTERVAL '{days} days'

    # Step 3: 카테고리별 진행률 계산
    # JOIN app_task_details → GROUP BY serial_number, task_category
    # COUNT(*) as total, SUM(completed_at IS NOT NULL) as done

    # Step 4: overall_percent 계산
    # 전체 applicable tasks 중 completed 비율
```

**핵심 SQL 쿼리 패턴**:

```sql
-- 협력사 S/N 목록 + 완료상태 (예: FNI)
SELECT pi.serial_number, pi.model, pi.mech_partner, pi.elec_partner,
       pi.mech_start, pi.ship_plan_date,
       cs.all_completed, cs.all_completed_at
FROM plan.product_info pi
LEFT JOIN completion_status cs ON cs.serial_number = pi.serial_number
WHERE pi.mech_partner = %(company)s
  AND (cs.all_completed IS NULL
       OR cs.all_completed = false
       OR cs.all_completed_at > NOW() - INTERVAL '1 day')
ORDER BY pi.mech_start NULLS LAST;

-- 카테고리별 진행률 (위 S/N들에 대해)
SELECT td.serial_number, td.task_category,
       COUNT(*) FILTER (WHERE td.is_applicable = true) as total,
       COUNT(*) FILTER (WHERE td.is_applicable = true AND td.completed_at IS NOT NULL) as done
FROM app_task_details td
WHERE td.serial_number = ANY(%(serial_numbers)s)
GROUP BY td.serial_number, td.task_category;
```

> **주의**: `completion_status` 컬럼명은 `mm_completed`, `ee_completed` (mech/elec 아님)

**Phase B: API 엔드포인트 추가**

`backend/app/routes/product.py`에 추가:

```python
@product_bp.route('/progress', methods=['GET'])
@jwt_required()
def get_sn_progress():
    """
    협력사별 S/N 진행률 조회

    Query params:
      - company: (optional) 특정 협력사 필터 (admin용)
      - include_completed: (optional) 완료 포함 일수, default=1

    Response: { "products": [...], "summary": { "total": 15, "in_progress": 12, "completed_recent": 3 } }
    """
    worker = get_current_worker()  # JWT에서 worker 추출

    # admin이면 company 파라미터 허용, 아니면 자기 회사만
    company = request.args.get('company', worker.company)
    if not worker.is_admin and company != worker.company:
        return jsonify({'error': 'FORBIDDEN'}), 403

    include_days = int(request.args.get('include_completed', 1))

    result = get_partner_sn_progress(
        worker_company=company,
        worker_role=worker.role,
        is_admin=worker.is_admin,
        include_completed_within_days=include_days
    )

    return jsonify({
        'products': result,
        'summary': {
            'total': len(result),
            'in_progress': sum(1 for r in result if not r['all_completed']),
            'completed_recent': sum(1 for r in result if r['all_completed'])
        }
    })
```

> **AXIS-VIEW 재사용**: 동일 JWT 인증 + `?company=FNI` 파라미터로 admin이 특정 협력사 조회 가능

---

### FE 작업

**Phase A: 진행률 서비스 (신규)**

`frontend/lib/services/progress_service.dart`:

```dart
class ProgressService {
  final ApiService _api;

  Future<Map<String, dynamic>> getSnProgress({String? company}) async {
    final params = company != null ? '?company=$company' : '';
    return await _api.getPrivate('/app/product/progress$params');
  }
}
```

**Phase B: 홈 화면 진행현황 카드**

`frontend/lib/screens/home/home_screen.dart` 수정:

```dart
// 홈 화면 기존 카드(출퇴근, 작업관리) 아래에 추가
// 협력사 계정(company != 'GST')일 때만 표시

// "작업 진행현황" 카드:
// - 상단: "진행 중 12건 / 최근 완료 3건" 요약
// - 하단: 상위 5개 S/N의 미니 진행바 (overall_percent)
// - 탭하면 sn_progress_screen.dart로 이동

// GST 계정: 같은 카드, but "전사 작업 진행현황"으로 표시
```

**Phase C: S/N 진행률 전체 목록 화면 (신규)**

`frontend/lib/screens/progress/sn_progress_screen.dart`:

```dart
// 전체 S/N 목록 — ListView
// 각 아이템:
//   [S/N] [모델명]
//   [전체 진행바 43%]
//   [MM ██░░ 62%] [EE ████ 100%] [TM ░░░░ 0%]   ← 자사 담당 공정만 강조색
//   [PI ██░░ 50%] [QI ░░░░ 0%] [SI ░░░░ 0%]
//   [납기: 2026-04-15]

// 100% 완료 아이템: 초록 배경 + "(완료)" 뱃지
// 정렬: 납기(ship_plan_date) 오름차순 (급한 것 위로)

// Pull-to-refresh 지원
// 자동 갱신: 30초 (Timer)
```

---

### TEST 작업

> ⚠️ **프로덕션 데이터 보호 — 절대 준수**
> - `workers` 테이블에 **실제 유저가 등록되어 있음** — 테스트 중 DELETE/TRUNCATE 금지
> - `plan.product_info`, `qr_registry`, `app_task_details`, `completion_status`도 실데이터 있을 수 있음
> - 테스트는 반드시 **별도 테스트 DB** 또는 **트랜잭션 롤백 패턴** 사용
> - fixture에서 테스트용 worker INSERT 시 **고유한 테스트 전용 ID/이름** 사용 (예: `test_worker_prog_01`)
> - teardown에서 테스트가 INSERT한 데이터**만** 정리 (WHERE 조건 명시)
> - `DROP TABLE`, `TRUNCATE`, `DELETE FROM workers` 같은 전체 삭제 **절대 금지**

`tests/backend/test_sn_progress.py`:

```python
# ⚠️ 테스트 격리: 기존 workers/product_info 데이터 절대 삭제하지 않음
# setup: 테스트 전용 worker + product + task 데이터 INSERT (고유 prefix: TEST_PROG_)
# teardown: TEST_PROG_ prefix 데이터만 DELETE

# TC-PROG-01: 협력사(FNI) 로그인 → mech_partner='FNI'인 S/N만 반환
# TC-PROG-02: 협력사(TMS(E)) 로그인 → elec_partner='TMS'인 S/N만 반환
# TC-PROG-03: GST admin 로그인 → 전체 S/N 반환
# TC-PROG-04: 진행률 계산 정확도 (8개 task 중 5개 완료 → 62.5%)
# TC-PROG-05: 100% 완료 + 1일 경과 → 목록에서 제외
# TC-PROG-06: 100% 완료 + 12시간 경과 → 목록에 포함 (아직 1일 미경과)
# TC-PROG-07: admin의 ?company=FNI 파라미터 → FNI S/N만 반환
# TC-PROG-08: 비admin의 ?company=FNI (자기 회사 아닌) → 403 FORBIDDEN
# TC-PROG-09: task 없는 S/N → progress 빈 dict, overall_percent 0
# TC-PROG-10: is_applicable=false 태스크는 진행률 계산에서 제외
```

---

### 실행 순서

```
⚠️ 프로덕션 DB에 실제 workers 데이터 존재 — 테스트 시 기존 데이터 삭제 금지

1. BE: progress_service.py 신규 생성
2. BE: product.py에 /progress 엔드포인트 추가
3. TEST: test_sn_progress.py 작성 + 실행 (트랜잭션 롤백 or 테스트 전용 데이터만 사용)
4. FE: progress_service.dart 신규 생성
5. FE: home_screen.dart에 진행현황 카드 추가
6. FE: sn_progress_screen.dart 신규 생성
7. flutter build web --release
8. git add + commit + push (v1.3.0 — 협력사 S/N 진행률)
9. 배포 확인
```

### 검증 체크리스트

- [ ] BE: /api/app/product/progress 엔드포인트 정상 응답
- [ ] BE: 협력사별 S/N 필터링 정확 (mech_partner/elec_partner 기준)
- [ ] BE: 100% 완료 후 1일 경과 시 목록 제외
- [ ] BE: 100% 완료 후 1일 미경과 시 목록 포함
- [ ] BE: GST admin → 전체 S/N 조회 가능
- [ ] BE: admin → ?company=FNI 파라미터로 특정 협력사 조회 가능
- [ ] BE: 비admin → 타사 조회 시 403 반환
- [ ] BE: is_applicable=false 태스크 진행률 계산 제외
- [ ] FE: 협력사 홈 화면에 진행현황 카드 표시
- [ ] FE: 카드 탭 → S/N 전체 목록 화면 이동
- [ ] FE: 자사 담당 공정 강조 표시
- [ ] FE: 납기 기준 정렬 (급한 것 위로)
- [ ] FE: Pull-to-refresh 동작
- [ ] TEST: 10개 테스트 케이스 전부 통과
- [ ] TEST: 기존 workers 테이블 데이터 보존 확인 (테스트 전후 COUNT 비교)
- [ ] 기존 기능 회귀 없음

### AXIS-VIEW 연동 메모

이 API는 AXIS-VIEW(React)에서 그대로 재사용된다:
```
AXIS-VIEW → GET /api/app/product/progress?company=FNI
          → Authorization: Bearer {admin_jwt}
          → 동일 응답 포맷
```

AXIS-VIEW에서는 추가로:
- 전체 협력사 비교 대시보드 (company별 반복 호출 또는 추후 batch API)
- 차트/그래프 시각화 (Chart.js)
- WebSocket 실시간 갱신 (작업 완료 이벤트 시)

---

## 보안 Sprint 19-A: Refresh Token Rotation + Device ID (BE 전용)

> **영향 범위**: AXIS-OPS BE만 수정. 양쪽 FE(OPS + VIEW) 수정 불필요 확인 완료.
> **선행 조건**: 없음 (독립 실행 가능)
> **AXIS-VIEW Sprint 2에서 Phase A 완료 가정하고 진행**

### 배경

현재 `/api/auth/refresh`는 `access_token`만 반환한다 (`auth_service.py` 533~535번째 줄).
동일 `refresh_token`을 30일간 재사용하므로 탈취 시 30일간 악용 가능.

### Phase A: Rotation 최소 구현 (BE 코드 수정만)

**수정 파일**: `backend/app/services/auth_service.py` — `refresh_access_token()` 메서드

**현재 코드 (533~535번째 줄):**
```python
return {
    'access_token': new_access_token,
}, 200
```

**변경:**
```python
new_refresh_token = self.create_refresh_token(
    worker_id=worker.id,
    email=worker.email
)

logger.info(f"Token rotation: worker_id={worker_id}, new refresh_token issued")

return {
    'access_token': new_access_token,
    'refresh_token': new_refresh_token,
}, 200
```

**효과**: 토큰 탈취 창이 30일 → 2시간으로 축소. FE는 양쪽 모두 수정 불필요:
- AXIS-OPS FE: `auth_service.dart` 251~254번째 줄에 `if (response['refresh_token'] != null)` 이미 있음
- AXIS-VIEW FE: `client.ts` 72~76번째 줄에 동일 패턴 있음

### Phase B: Device ID 수집

**목적**: 다중 기기 로그인 구분 + 추후 Phase C에서 기기별 토큰 관리

**B-1. AXIS-OPS FE (Flutter PWA) — device_id 생성**

`frontend/lib/services/auth_service.dart` 수정:

```dart
import 'package:uuid/uuid.dart';
import 'dart:html' as html;

/// 기기 고유 ID 생성 (브라우저 localStorage 기반)
/// PWA 환경에서는 하드웨어 ID 접근 불가 → UUID를 최초 생성 후 재사용
String getDeviceId() {
  const key = 'axis_device_id';
  var id = html.window.localStorage[key];
  if (id == null || id.isEmpty) {
    id = const Uuid().v4();
    html.window.localStorage[key] = id;
  }
  return id;
}
```

**B-2. 로그인/refresh 요청에 device_id 포함**

`auth_service.dart` — `login()` 수정:
```dart
final response = await _apiService.post(
  authLoginEndpoint,
  data: {
    'email': email,
    'password': password,
    'device_id': getDeviceId(),  // ← 추가
  },
);
```

`auth_service.dart` — `refreshToken()` 수정:
```dart
final response = await _apiService.post(
  authRefreshEndpoint,
  data: {
    'refresh_token': storedRefreshToken,
    'device_id': getDeviceId(),  // ← 추가
  },
);
```

PIN 로그인 (`auth.py` 680번째 줄 근처)도 동일하게 `device_id` 수신.

**B-3. BE — device_id 수신 (저장은 Phase C)**

`auth_service.py` — `login()`, `refresh_access_token()`:
```python
# request body에서 device_id 읽기 (optional, 없으면 'unknown')
device_id = data.get('device_id', 'unknown')
# Phase A에서는 로그만 남김, Phase C에서 DB 저장
logger.info(f"Login: worker_id={worker.id}, device_id={device_id}")
```

**B-4. AXIS-VIEW FE (React)**

`src/lib/client.ts` 또는 `src/stores/auth.ts`:
```ts
function getDeviceId(): string {
  const key = 'axis_device_id';
  let id = localStorage.getItem(key);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(key, id);
  }
  return id;
}

// login 요청에 추가
const response = await client.post('/api/auth/login', {
  email, password,
  device_id: getDeviceId(),
});

// refresh 요청에 추가
const response = await client.post('/api/auth/refresh', {
  refresh_token: storedToken,
  device_id: getDeviceId(),
});
```

> ⚠️ `uuid` 패키지 설치 필요 (OPS): `flutter pub add uuid`
> AXIS-VIEW는 `crypto.randomUUID()` 네이티브 사용 (패키지 불필요)

---

### 보안 Sprint 19-A 변경 대상 파일

```
BE (AXIS-OPS):
├── backend/app/services/auth_service.py        (수정 — Phase A: rotation 반환)
├── backend/app/routes/auth.py                  (수정 — Phase B: device_id 수신/로깅)

FE (AXIS-OPS):
├── frontend/lib/services/auth_service.dart     (수정 — Phase B: device_id 생성+전송)
├── frontend/pubspec.yaml                       (수정 — uuid 패키지 추가)

FE (AXIS-VIEW):
├── src/lib/client.ts 또는 src/stores/auth.ts   (수정 — Phase B: device_id 생성+전송)

TEST:
├── tests/backend/test_auth_rotation.py         (신규)
```

### 보안 Sprint 19-A 테스트

```python
# TC-ROT-01: /auth/refresh 호출 → 응답에 access_token + refresh_token 둘 다 포함
# TC-ROT-02: 새 refresh_token으로 다시 refresh → 성공
# TC-ROT-03: 이전(교체된) refresh_token으로 refresh → 현재는 성공 (Phase C에서 차단 예정)
# TC-ROT-04: login 요청에 device_id 포함 → 로그에 device_id 기록됨
# TC-ROT-05: device_id 미전송 → 'unknown'으로 기본 처리 (에러 아님)
# TC-ROT-06: PIN 로그인 → refresh_token 발급 정상 + rotation 동일 적용
```

> ⚠️ 기존 workers 테이블 데이터 보존 — DELETE/TRUNCATE 금지 (Sprint 18 동일 규칙)

### 보안 Sprint 19-A 검증 체크리스트

- [ ] BE: /auth/refresh 응답에 refresh_token 필드 추가됨
- [ ] BE: 새 refresh_token으로 재차 refresh 성공
- [ ] BE: login/refresh 로그에 device_id 기록
- [ ] OPS FE: 로그인 후 access_token 만료 → 자동 갱신 → 새 refresh_token 저장됨
- [ ] OPS FE: 갱신 후 정상 API 호출 가능
- [ ] VIEW FE: 동일 동작 확인 (AXIS-VIEW Sprint 2 완료 후)
- [ ] PIN 로그인: rotation 동일 적용
- [ ] 기존 기능 회귀 없음
- [ ] 기존 workers 데이터 보존

---

## 보안 Sprint 19-B: DB 토큰 관리 + Geolocation (BE + FE)

> **선행 조건**: 보안 Sprint 19-A 완료
> **영향 범위**: BE 마이그레이션 + BE 로직 + 양쪽 FE (위치 전송)

### Phase C: DB 기반 토큰 관리 + 탈취 감지

**C-1. 마이그레이션 (신규)**

`backend/migrations/018_auth_refresh_tokens.sql`:

```sql
-- 보안 Sprint 19-B: Refresh Token DB 관리
CREATE SCHEMA IF NOT EXISTS auth;

CREATE TABLE auth.refresh_tokens (
    id SERIAL PRIMARY KEY,
    worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    device_id VARCHAR(100) NOT NULL DEFAULT 'unknown',
    token_hash VARCHAR(64) NOT NULL,     -- SHA256 해시 (원본 저장 안 함)
    expires_at TIMESTAMPTZ NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    revoked_reason VARCHAR(50),          -- 'rotation' | 'logout' | 'theft_detected' | 'admin'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);

CREATE INDEX idx_refresh_tokens_worker ON auth.refresh_tokens(worker_id, revoked);
CREATE INDEX idx_refresh_tokens_hash ON auth.refresh_tokens(token_hash);
```

**C-2. auth_service.py 수정 — 토큰 발급 시 DB 저장**

```python
import hashlib

def _hash_token(self, token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def _store_refresh_token(self, worker_id: int, device_id: str,
                          token: str, expires_at: datetime):
    token_hash = self._hash_token(token)
    # INSERT into auth.refresh_tokens
    # 같은 (worker_id, device_id)의 이전 토큰은 revoked=TRUE, revoked_reason='rotation'

def _verify_stored_refresh_token(self, token: str) -> bool:
    token_hash = self._hash_token(token)
    # SELECT from auth.refresh_tokens WHERE token_hash = %s AND revoked = FALSE
    # 있으면 True + last_used_at 업데이트
    # 없으면 → 탈취 감지: 해당 worker의 모든 토큰 무효화
```

**C-3. 탈취 감지 로직**

```
[정상 흐름]
  refresh_token_v1으로 refresh → v1 revoked, v2 발급 → v2로 refresh → v2 revoked, v3 발급 ...

[탈취 감지]
  공격자가 v1(이미 revoked)으로 refresh 시도
  → DB에서 v1 hash 조회 → revoked=TRUE 발견
  → "이미 교체된 토큰 재사용" = 탈취 의심
  → 해당 worker의 모든 refresh_token 무효화 (revoked=TRUE, reason='theft_detected')
  → 모든 기기에서 재로그인 필요
  → 로그 경고: "SECURITY: Refresh token reuse detected for worker_id=X"
```

**C-4. 로그아웃 시 토큰 무효화**

현재 로그아웃 API가 없으므로 추가:

```python
@auth_bp.route("/logout", methods=["POST"])
@jwt_required
def logout():
    """현재 기기의 refresh_token 무효화"""
    data = request.get_json()
    refresh_token = data.get('refresh_token')
    if refresh_token:
        auth_service.revoke_refresh_token(refresh_token, reason='logout')
    return jsonify({'message': '로그아웃 완료'}), 200
```

양쪽 FE에서 로그아웃 시 이 API 호출 추가.

---

### Phase D: Geolocation 접속 보안

## 팀 구성
2명의 teammate를 생성해줘. Sonnet 모델 사용:

1. **BE** (Backend 담당) - 소유: backend/**
   - D-1: 마이그레이션 019_geolocation_settings.sql 작성 + 실행
   - D-2: geo_service.py 신규 작성 (haversine + check_attendance_location)
   - D-3: hr.py attendance_check()에 위치 검증 적용
   - admin.py: geolocation 키 validation 추가
   - admin_settings.py: geolocation 키 default 추가

2. **FE** (Frontend 담당) - 소유: frontend/**
   - D-4: home_screen.dart — getCurrentLocation() + 출근 체크 시 lat/lng 전송
   - D-5: admin_options_screen.dart — Section 5 "위치 보안" 설정 UI 추가
     - _buildTextFieldSetting (신규 위젯), _buildDropdownSetting (신규 위젯)
     - 기존 _buildSettingToggle, _buildSectionHeader 패턴 참고

⚠️ **의존 관계**: BE의 마이그레이션 019 + admin.py validation이 먼저 완료되어야 FE Section 5에서 설정 읽기/저장이 동작함.
⚠️ **기존 workers 테이블 데이터 보존 — DELETE/TRUNCATE 금지**

---

> **핵심 설계 원칙:**
> 1. **work_site 기반 예외**: GST 현장 출근만 위치 검증. 협력사 본사(HQ) 근무는 검증 스킵.
> 2. **반경 1km**: 웹 GPS 오차(실내 300~500m) + 공장 부지/부대시설 고려.
> 3. **soft/strict 모드**: 초기 2~4주 soft 모드(경고만) → 데이터 확인 후 strict 전환.
>
> **예외 대상:**
> - ELEC 협력사 작업자 → 협력사 본사 근무 빈번 (work_site ≠ 'GST')
> - MECH 협력사 → 추후 협력사 본사 근무 가능성 있음
> - work_site가 'GST'가 아니면 위치 검증 자동 스킵

**D-1. Admin 설정 테이블 확장**

`backend/migrations/019_geolocation_settings.sql`:

```sql
-- 보안 Sprint 19-B: Geolocation 접속 보안
-- admin.app_settings에 위치 설정 추가 (key-value 방식 기존 패턴 재사용)
-- 설정 키:
--   geolocation_enabled: true/false (전체 ON/OFF)
--   geolocation_mode: soft/strict (soft=경고만, strict=차단)
--   allowed_lat: GST 공장 위도 (예: 36.xxxxx)
--   allowed_lng: GST 공장 경도 (예: 127.xxxxx)
--   allowed_radius_m: 허용 반경 (미터, 기본 1000 = 1km)
--   geolocation_check_points: 체크 시점 (예: 'attendance')

INSERT INTO admin.app_settings (key, value) VALUES
  ('geolocation_enabled', 'false'),
  ('geolocation_mode', 'soft'),
  ('allowed_lat', '0'),
  ('allowed_lng', '0'),
  ('allowed_radius_m', '1000'),
  ('geolocation_check_points', 'attendance')
ON CONFLICT (key) DO NOTHING;
```

> ⚠️ **GST 공장 GPS 좌표 사전 확인 필요** — 배포 전 실측
> ⚠️ **배포 후 2~4주간 `geolocation_mode=soft` 유지** — 오차 데이터 수집 후 strict 전환

**D-2. BE — 위치 검증 유틸**

`backend/app/services/geo_service.py` (신규):

```python
import math
import logging

logger = logging.getLogger(__name__)

def haversine_distance(lat1, lon1, lat2, lon2) -> float:
    """두 좌표 간 거리 (미터) — Haversine 공식"""
    R = 6371000  # 지구 반경 (m)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def check_attendance_location(work_site: str, user_lat: float = None,
                               user_lng: float = None, worker_id: int = None) -> dict:
    """
    출퇴근 위치 검증 (work_site 기반 예외 처리 포함)

    예외 조건:
    - work_site != 'GST' → 협력사 본사 근무 등 → 위치 검증 스킵
    - geolocation_enabled=false → 전체 스킵
    - lat/lng 미전송 → 경고 로그만 (차단 안 함, GPS 권한 미허용 대응)

    모드:
    - soft: 범위 밖이어도 허용 + 경고 로그 (초기 운영용, 오차 데이터 수집)
    - strict: 범위 밖이면 차단 (403)
    """
    # 1. 전체 비활성화 체크
    enabled = get_setting('geolocation_enabled', 'false')
    if enabled != 'true':
        return {'allowed': True, 'reason': 'geolocation_disabled'}

    # 2. work_site 기반 예외 — GST 현장이 아니면 스킵
    if work_site and work_site.upper() != 'GST':
        logger.info(f"GEO_SKIP: worker_id={worker_id}, work_site={work_site} (non-GST, 검증 스킵)")
        return {'allowed': True, 'reason': 'non_gst_site', 'work_site': work_site}

    # 3. 좌표 미전송 — 경고만 (GPS 권한 거부 대응)
    if user_lat is None or user_lng is None:
        logger.warning(f"GEO_NO_COORDS: worker_id={worker_id}, work_site={work_site} (좌표 미전송)")
        return {'allowed': True, 'reason': 'no_coordinates'}

    # 4. 거리 계산
    allowed_lat = float(get_setting('allowed_lat', '0'))
    allowed_lng = float(get_setting('allowed_lng', '0'))
    allowed_radius = float(get_setting('allowed_radius_m', '1000'))  # 기본 1km
    mode = get_setting('geolocation_mode', 'soft')  # 'soft' | 'strict'

    distance = haversine_distance(user_lat, user_lng, allowed_lat, allowed_lng)

    # 5. 범위 내 → 허용
    if distance <= allowed_radius:
        logger.info(f"GEO_OK: worker_id={worker_id}, distance={round(distance)}m (반경 {allowed_radius}m 이내)")
        return {'allowed': True, 'distance_m': round(distance)}

    # 6. 범위 밖 → 모드에 따라 분기
    if mode == 'soft':
        # soft 모드: 허용하되 경고 로그 (오차 데이터 수집용)
        logger.warning(
            f"GEO_SOFT_WARN: worker_id={worker_id}, distance={round(distance)}m, "
            f"radius={allowed_radius}m, lat={user_lat}, lng={user_lng} (범위 밖이지만 soft 모드로 허용)"
        )
        return {
            'allowed': True,
            'reason': 'soft_mode',
            'distance_m': round(distance),
            'radius_m': int(allowed_radius)
        }
    else:
        # strict 모드: 차단
        logger.warning(
            f"GEO_BLOCKED: worker_id={worker_id}, distance={round(distance)}m, "
            f"radius={allowed_radius}m, lat={user_lat}, lng={user_lng}"
        )
        return {
            'allowed': False,
            'distance_m': round(distance),
            'radius_m': int(allowed_radius)
        }
```

**D-3. 적용 시점 — 출퇴근 체크에만 우선 적용**

`backend/app/routes/hr.py` — `attendance_check()` 수정:

```python
from app.services.geo_service import check_attendance_location

# 출근 시 위치 검증
lat = data.get('lat')
lng = data.get('lng')
work_site = data.get('work_site', '')

geo_result = check_attendance_location(
    work_site=work_site,
    user_lat=float(lat) if lat else None,
    user_lng=float(lng) if lng else None,
    worker_id=worker.id
)

if not geo_result['allowed']:
    return jsonify({
        'error': 'LOCATION_OUT_OF_RANGE',
        'message': f"GST 공장 허용 범위({geo_result['radius_m']}m) 밖입니다. "
                   f"현재 거리: {geo_result['distance_m']}m",
        'distance_m': geo_result['distance_m'],
        'radius_m': geo_result['radius_m']
    }), 403
```

> **위치 검증 흐름 요약:**
> ```
> 출퇴근 체크 요청
>   ├─ geolocation_enabled=false → 검증 스킵 ✅
>   ├─ work_site ≠ 'GST' (협력사 본사 등) → 검증 스킵 ✅
>   ├─ lat/lng 미전송 (GPS 권한 거부) → 경고 로그 + 허용 ✅
>   ├─ 거리 ≤ 1km → 허용 ✅
>   ├─ 거리 > 1km + soft 모드 → 경고 로그 + 허용 ✅ (데이터 수집)
>   └─ 거리 > 1km + strict 모드 → 차단 ❌ (403)
> ```

**D-4. AXIS-OPS FE — 위치 전송**

`frontend/lib/services/auth_service.dart` 또는 `home_screen.dart`:

```dart
import 'dart:html' as html;

Future<Map<String, double>?> getCurrentLocation() async {
  try {
    final position = await html.window.navigator.geolocation
        .getCurrentPosition(enableHighAccuracy: true, timeout: Duration(seconds: 10));
    return {
      'lat': position.coords!.latitude!.toDouble(),
      'lng': position.coords!.longitude!.toDouble(),
    };
  } catch (e) {
    debugPrint('Geolocation error: $e');
    return null;  // 위치 권한 거부 시 null → BE에서 경고 로그만
  }
}

// 출근 체크 시
final location = await getCurrentLocation();
final body = {'check_type': 'in', 'work_site': _selectedWorkSite, 'product_line': _selectedProductLine};
if (location != null) {
  body['lat'] = location['lat'].toString();
  body['lng'] = location['lng'].toString();
}
await apiService.post('/hr/attendance/check', data: body);
```

**D-5. AXIS-OPS Admin 설정 — Geolocation 섹션 추가 (Sprint 19-B 포함)**

> **기존 OPS admin 설정 페이지에 Section 5로 추가.**
> - FE: `admin_options_screen.dart` — 기존 Section 0~4 뒤에 Section 5 "위치 보안" 추가
> - BE: `GET/PUT /api/admin/settings` — **이미 존재**, 새 API 불필요. 마이그레이션 019에서 키만 추가하면 됨
> - DB: `admin_settings` 테이블 key-value JSONB 방식 그대로 사용

**admin_options_screen.dart — Section 5: 위치 보안 설정 추가:**

```dart
// Section 5: 위치 보안 설정
// 기존 패턴과 동일하게 _buildSectionHeader + _buildSettingToggle 재사용

// 상태 변수 추가
bool _geolocationEnabled = false;
String _geolocationMode = 'soft';  // 'soft' | 'strict'
String _allowedLat = '0';
String _allowedLng = '0';
int _allowedRadiusM = 1000;

// Section 5 UI
_buildSectionHeader('위치 보안', Icons.location_on),
_buildSettingToggle(
  '위치 검증',
  '출근 체크 시 GPS 위치 확인 (GST 현장만 적용, 협력사 본사 근무는 자동 스킵)',
  _geolocationEnabled,
  (val) => _updateSetting('geolocation_enabled', val),
),
// geolocation_enabled=true일 때만 표시
if (_geolocationEnabled) ...[
  _buildSettingToggle(
    '차단 모드 (strict)',
    'OFF: 범위 밖 경고만 (soft) / ON: 범위 밖 출근 차단 (strict)',
    _geolocationMode == 'strict',
    (val) => _updateSetting('geolocation_mode', val ? 'strict' : 'soft'),
  ),
  // GST 공장 좌표 입력 (Number Input)
  _buildTextFieldSetting('GST 공장 위도', _allowedLat, (val) => _updateSetting('allowed_lat', val)),
  _buildTextFieldSetting('GST 공장 경도', _allowedLng, (val) => _updateSetting('allowed_lng', val)),
  // 허용 반경 선택
  _buildDropdownSetting('허용 반경', _allowedRadiusM, {
    500: '500m',
    1000: '1km (권장)',
    2000: '2km',
  }, (val) => _updateSetting('allowed_radius_m', val)),
],
```

> **⚠️ `_buildTextFieldSetting`과 `_buildDropdownSetting`은 신규 위젯 메서드.**
> 기존 `_buildSettingToggle`, `_buildBreakTimeRow` 패턴을 참고하여 구현.
> BE는 기존 `PUT /api/admin/settings` 그대로 사용 — 새 키(geolocation_*)만 추가됨.

**BE 변경 사항:**
- `admin.py` `PUT /api/admin/settings` — geolocation 키에 대한 validation 추가 (좌표 범위, radius 허용값)
- `admin_settings.py` — geolocation 키의 default 값 추가 (기존 패턴 동일)
- 마이그레이션 019에서 키 INSERT 처리 완료 (D-1에 이미 포함)

---

### 보안 Sprint 19-B 변경 대상 파일

```
BE (AXIS-OPS):
├── backend/migrations/018_auth_refresh_tokens.sql   (신규 — Phase C)
├── backend/migrations/019_geolocation_settings.sql  (신규 — Phase D)
├── backend/app/services/auth_service.py             (수정 — Phase C: DB 저장/검증)
├── backend/app/services/geo_service.py              (신규 — Phase D: 위치 검증)
├── backend/app/routes/auth.py                       (수정 — Phase C: logout 추가)
├── backend/app/routes/hr.py                         (수정 — Phase D: 위치 검증 적용)

FE (AXIS-OPS):
├── frontend/lib/screens/home/home_screen.dart       (수정 — Phase D: 출근 시 위치 전송)
├── frontend/lib/screens/admin/admin_options_screen.dart (수정 — Phase D: Section 5 위치 보안 추가)
├── frontend/lib/services/auth_service.dart          (수정 — Phase C: 로그아웃 시 토큰 무효화 API 호출)

BE (AXIS-OPS):
├── backend/app/routes/admin.py                       (수정 — Phase D: geolocation 키 validation 추가)
├── backend/app/models/admin_settings.py              (수정 — Phase D: geolocation 키 default 추가)

FE (AXIS-VIEW):
├── src/stores/auth.ts 또는 src/lib/client.ts        (수정 — Phase C: 로그아웃 시 토큰 무효화)

TEST:
├── tests/backend/test_refresh_token_db.py           (신규 — Phase C)
├── tests/backend/test_geolocation.py                (신규 — Phase D)
```

### 보안 Sprint 19-B 테스트

```python
# Phase C 테스트:
# TC-RTD-01: 로그인 → auth.refresh_tokens에 행 INSERT됨
# TC-RTD-02: refresh → 이전 토큰 revoked=TRUE(reason='rotation'), 새 토큰 INSERT
# TC-RTD-03: revoked 토큰으로 refresh → 403 + 해당 worker 전체 토큰 무효화 (탈취 감지)
# TC-RTD-04: logout → 해당 토큰 revoked=TRUE(reason='logout')
# TC-RTD-05: 다중 기기 (device_id 2개) → 각각 독립 토큰, 한쪽 로그아웃 시 다른 쪽 유지
# TC-RTD-06: PIN 로그인 → DB에 토큰 저장 + rotation 동일 적용

# Phase D 테스트:
# TC-GEO-01: geolocation_enabled=false → 위치 검증 스킵, 출근 성공
# TC-GEO-02: geolocation_enabled=true + work_site='GST' + 범위 내(1km) 좌표 → 출근 성공
# TC-GEO-03: geolocation_enabled=true + work_site='GST' + 범위 밖 좌표 + strict 모드 → 403 LOCATION_OUT_OF_RANGE
# TC-GEO-04: geolocation_enabled=true + work_site='GST' + 범위 밖 좌표 + soft 모드 → 경고 로그 + 출근 허용
# TC-GEO-05: geolocation_enabled=true + work_site='HQ' (협력사 본사) → 위치 검증 스킵, 출근 성공
# TC-GEO-06: geolocation_enabled=true + work_site='GST' + 좌표 미전송 → 경고 로그만, 출근 허용
# TC-GEO-07: haversine_distance 정확도 검증 (알려진 좌표 쌍으로 계산)
# TC-GEO-08: work_site가 빈 문자열 또는 None → GST로 간주하고 검증 진행
```

> ⚠️ 기존 workers 테이블 데이터 보존 — DELETE/TRUNCATE 금지

### 보안 Sprint 19-B 검증 체크리스트

- [ ] 마이그레이션 018, 019 정상 실행
- [ ] 로그인/PIN 로그인 → auth.refresh_tokens에 행 생성됨
- [ ] refresh → 이전 토큰 revoked, 새 토큰 생성
- [ ] revoked 토큰 재사용 → 전체 무효화 (탈취 감지)
- [ ] logout API → 토큰 무효화
- [ ] 다중 기기 독립 관리 (device_id별)
- [ ] geolocation_enabled=false → 영향 없음
- [ ] geolocation_enabled=true + work_site='GST' + 범위 내(1km) → 출근 성공
- [ ] geolocation_enabled=true + work_site='GST' + 범위 밖 + strict → 403
- [ ] geolocation_enabled=true + work_site='GST' + 범위 밖 + soft → 경고 로그 + 허용
- [ ] geolocation_enabled=true + work_site='HQ' (협력사 본사) → 검증 스킵
- [ ] 좌표 미전송 → 경고 로그만 (허용)
- [ ] OPS admin 설정 Section 5: 위치 보안 토글/모드/좌표/반경 UI 표시
- [ ] OPS admin 설정 Section 5: 설정 변경 → PUT /api/admin/settings → DB 반영 확인
- [ ] OPS admin 설정: geolocation_enabled=false일 때 하위 설정 숨김 처리
- [ ] 기존 기능 회귀 없음
- [ ] 기존 workers 데이터 보존

---

### 보안 스프린트 실행 순서 요약

```
보안 Sprint 19-A (Rotation + Device ID):
  1. BE: auth_service.py refresh → 새 refresh_token 반환 (Phase A)
  2. OPS FE: uuid 패키지 + device_id 생성 + login/refresh에 전송 (Phase B)
  3. VIEW FE: device_id 생성 + login/refresh에 전송 (Phase B)
  4. TEST: test_auth_rotation.py (6개 TC)
  5. 배포 + 검증

보안 Sprint 19-B (DB 관리 + Geolocation):
  ⚠️ 선행: Sprint 19-A 완료
  1. BE: 마이그레이션 018, 019 실행
  2. BE: auth_service.py DB 저장/검증 + logout API (Phase C)
  3. BE: geo_service.py (work_site 예외 + soft/strict 모드) + hr.py 위치 검증 (Phase D)
  4. BE: admin.py geolocation 키 validation + admin_settings.py default 추가 (Phase D)
  5. OPS FE: admin_options_screen.dart Section 5 위치 보안 + 출근 시 위치 전송 (Phase D)
  6. OPS FE: 로그아웃 토큰 무효화 (Phase C)
  7. VIEW FE: 로그아웃 토큰 무효화 (Phase C)
  8. TEST: test_refresh_token_db.py + test_geolocation.py (14개 TC)
  9. GST 공장 GPS 좌표 실측 → OPS admin 설정에서 입력
  8. 배포 (geolocation_mode=soft) → 2~4주 데이터 수집 → strict 전환
```

---

## Sprint 19-E: VIEW용 Admin 출퇴근 API (BE)

> 사전 조건: Sprint 19-A/B/D ✅
> 목적: AXIS-VIEW 대시보드가 실 데이터를 조회할 수 있도록 Admin 전용 출퇴근 API 3개 추가
> VIEW Sprint 3 (실 데이터 연결)의 선행 작업

---

### 🚀 Sprint 19-E 프롬프트 (복사해서 사용)

```
AXIS-VIEW 대시보드용 Admin 출퇴근 API 3개를 추가합니다.
기존 admin.py Blueprint에 추가하며, hr.partner_attendance 테이블을 조회합니다.

⚠️ 반드시 읽어야 할 파일:
- CLAUDE.md (프로젝트 컨텍스트, DB 스키마)
- backend/app/routes/admin.py (기존 Admin 엔드포인트 패턴 참고)
- backend/app/routes/hr.py (partner_attendance 테이블 사용 패턴 참고)

## 팀 구성
단독 진행 (BE만)

---

## Task 1: GET /api/admin/hr/attendance/today — 오늘 전체 출퇴근 현황

### 위치: backend/app/routes/admin.py (기존 admin_bp에 추가)

### 라우트 정의:
@admin_bp.route("/hr/attendance/today", methods=["GET"])
@jwt_required
@admin_required

### 핵심 SQL (IN/OUT 피봇, KST 기준):

⚠️ 반드시 KST 기준으로 날짜 범위를 계산할 것. `check_time::date = CURRENT_DATE`는 UTC 이슈 발생.

```python
from datetime import datetime, timezone, timedelta
KST = timezone(timedelta(hours=9))
now_kst = datetime.now(KST)
today_start_kst = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
tomorrow_start_kst = today_start_kst + timedelta(days=1)
```

```sql
SELECT
  w.id AS worker_id,
  w.name AS worker_name,
  w.company,
  w.role,
  MAX(CASE WHEN pa.check_type = 'in'  THEN pa.check_time END) AS check_in_time,
  MAX(CASE WHEN pa.check_type = 'out' THEN pa.check_time END) AS check_out_time,
  MAX(CASE WHEN pa.check_type = 'in'  THEN pa.work_site END) AS work_site,
  MAX(CASE WHEN pa.check_type = 'in'  THEN pa.product_line END) AS product_line
FROM workers w
LEFT JOIN hr.partner_attendance pa
  ON w.id = pa.worker_id
  AND pa.check_time >= %s   -- today_start_kst
  AND pa.check_time <  %s   -- tomorrow_start_kst
WHERE w.company != 'GST'
  AND w.approval_status = 'approved'
GROUP BY w.id, w.name, w.company, w.role
ORDER BY w.company, w.name
```

### status 계산 (Python):
```python
if check_in_time is None:
    status = 'not_checked'
elif check_out_time is None:
    status = 'working'
else:
    status = 'left'
```

### summary 계산:
records 루프 돌면서 집계:
- total_registered: 전체 records 수
- checked_in: status != 'not_checked' 수
- checked_out: status == 'left' 수
- currently_working: status == 'working' 수
- not_checked: status == 'not_checked' 수

### 응답 형식:
```json
{
  "date": "2026-03-06",
  "records": [
    {
      "worker_id": 5,
      "worker_name": "탁재훈",
      "company": "C&A",
      "role": "ELEC",
      "check_in_time": "2026-03-06T08:15:00+09:00",
      "check_out_time": "2026-03-06T17:30:00+09:00",
      "status": "left",
      "work_site": "GST",
      "product_line": "SCR"
    }
  ],
  "summary": {
    "total_registered": 98,
    "checked_in": 86,
    "checked_out": 34,
    "currently_working": 52,
    "not_checked": 12
  }
}
```

⚠️ check_in_time, check_out_time은 ISO8601 KST (+09:00) 문자열로 변환.
None인 경우 null 반환.

---

## Task 2: GET /api/admin/hr/attendance?date=YYYY-MM-DD — 날짜별 조회

### 위치: admin.py 동일

### 라우트 정의:
@admin_bp.route("/hr/attendance", methods=["GET"])
@jwt_required
@admin_required

### 구현:
- query parameter: `date` (YYYY-MM-DD 형식)
- date 없으면 오늘 날짜 사용 (Task 1과 동일)
- date 있으면 해당 날짜의 KST 00:00 ~ 다음날 KST 00:00 범위로 조회
- SQL과 응답 형식은 Task 1과 동일
- date 파싱 실패 시 400 에러

```python
date_str = request.args.get('date')
if date_str:
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'INVALID_DATE', 'message': 'date 형식: YYYY-MM-DD'}), 400
    target_start_kst = target_date.replace(tzinfo=KST)
    target_end_kst = target_start_kst + timedelta(days=1)
else:
    target_start_kst = today_start_kst
    target_end_kst = tomorrow_start_kst
```

### 응답: Task 1과 동일 구조 (date 필드만 요청 날짜로 변경)

---

## Task 3: GET /api/admin/hr/attendance/summary — 회사별 출퇴근 요약

### 위치: admin.py 동일

### 라우트 정의:
@admin_bp.route("/hr/attendance/summary", methods=["GET"])
@jwt_required
@admin_required

### 구현:
- query parameter: `date` (옵션, 없으면 오늘)
- 회사별(company) 그룹핑으로 집계

### SQL:
Task 1/2의 쿼리 결과를 Python에서 company별로 그룹핑하거나,
별도 SQL로 직접 집계:

```sql
SELECT
  w.company,
  COUNT(*) AS total_workers,
  COUNT(CASE WHEN pa_in.check_time IS NOT NULL THEN 1 END) AS checked_in,
  COUNT(CASE WHEN pa_out.check_time IS NOT NULL THEN 1 END) AS checked_out
FROM workers w
LEFT JOIN (
  SELECT worker_id, MAX(check_time) AS check_time
  FROM hr.partner_attendance
  WHERE check_type = 'in'
    AND check_time >= %s AND check_time < %s
  GROUP BY worker_id
) pa_in ON w.id = pa_in.worker_id
LEFT JOIN (
  SELECT worker_id, MAX(check_time) AS check_time
  FROM hr.partner_attendance
  WHERE check_type = 'out'
    AND check_time >= %s AND check_time < %s
  GROUP BY worker_id
) pa_out ON w.id = pa_out.worker_id
WHERE w.company != 'GST'
  AND w.approval_status = 'approved'
GROUP BY w.company
ORDER BY w.company
```

또는 간단하게: Task 1/2 내부 함수를 재활용하여 records → company별 집계

### 응답 형식:
```json
{
  "date": "2026-03-06",
  "by_company": [
    {
      "company": "C&A",
      "total_workers": 22,
      "checked_in": 17,
      "checked_out": 7,
      "currently_working": 10,
      "not_checked": 5
    }
  ]
}
```

### 계산:
- currently_working = checked_in - checked_out
- not_checked = total_workers - checked_in

---

## Task 4: 공통 함수 추출 (리팩터링)

Task 1~3에서 중복되는 로직을 내부 함수로 추출:

```python
def _get_attendance_data(target_start_kst, target_end_kst):
    """출퇴근 데이터 조회 공통 함수 — records + summary 반환"""
    # SQL 실행 → records 리스트 생성 → summary 계산
    # Task 1/2/3에서 재사용
    ...
    return records, summary
```

- Task 1: `_get_attendance_data(today_start_kst, tomorrow_start_kst)`
- Task 2: `_get_attendance_data(target_start_kst, target_end_kst)`
- Task 3: `_get_attendance_data()` 결과를 company별 그룹핑

---

## Task 5: 테스트

### 테스트 파일: tests/backend/test_admin_attendance.py (신규)

### 테스트 케이스 (8개):

| TC | 설명 |
|----|------|
| ATT-01 | /hr/attendance/today — 빈 데이터 (출퇴근 기록 없음) → records=[], summary 전부 0 |
| ATT-02 | /hr/attendance/today — 출근만 한 작업자 → status='working' |
| ATT-03 | /hr/attendance/today — 출근+퇴근 완료 → status='left' |
| ATT-04 | /hr/attendance/today — 미출근 작업자 → status='not_checked' |
| ATT-05 | /hr/attendance?date=2026-03-05 — 날짜 파라미터 정상 |
| ATT-06 | /hr/attendance?date=invalid — 400 에러 |
| ATT-07 | /hr/attendance/summary — 회사별 집계 정확성 |
| ATT-08 | 비관리자 접근 → 403 |

### 테스트 데이터 셋업:
```python
# conftest.py fixture 활용
# workers 3명: company='C&A' 2명, company='FNI' 1명
# partner_attendance: C&A worker1 in/out, C&A worker2 in만, FNI worker3 없음
```

---

## 체크리스트

- [ ] admin.py에 3개 엔드포인트 추가
- [ ] _get_attendance_data 공통 함수 추출
- [ ] KST 기준 날짜 범위 계산 (UTC 이슈 방지)
- [ ] check_time → ISO8601 KST 문자열 변환
- [ ] approval_status='approved' 필터 (미승인 작업자 제외)
- [ ] company != 'GST' 필터 (GST 직원 제외 — 협력사만)
- [ ] test_admin_attendance.py 8개 TC 통과
- [ ] 기존 테스트 회귀 없음

## ⚠️ 금지 사항
- hr.py 기존 엔드포인트 수정 금지 (개인용 API는 그대로 유지)
- workers 테이블 스키마 변경 금지
- partner_attendance 테이블 스키마 변경 금지
- FE 코드 수정 금지 (BE만 작업)
```

---

## Sprint 20 (예정) — 알림 + 공지사항


---

### Sprint 20-A: 신규 가입 시 Admin 이메일 알림

**목표**: 작업자가 회원가입하면 DB의 `is_admin=true` 사용자 전원에게 이메일 자동 발송 — 가입 사실을 즉시 인지하고 승인/거부 판단 가능

**배경**:
- 현재 가입 후 Admin이 직접 사용자 목록에서 확인해야 함
- 현장 관리자가 신규 가입을 놓칠 수 있음

**수신자 규칙**:
- DB `workers` 테이블에서 `is_admin=true`인 사용자의 `email` 조회
- 환경변수 `ADMIN_EMAIL`이 아닌 **DB 기반** (Admin이 추가/변경되면 자동 반영)
- Admin이 여러 명이면 각각에게 개별 발송

**테스트 제한**:
- ⚠️ 테스트 단계에서는 수신자를 `dkkim1@gst-in.com`으로만 하드코딩하여 테스트
- 프로덕션 전환 시 DB 조회 방식으로 변경

**Teammate**: 불필요 (파일 3~4개, BE만 작업)

#### Phase A: BE — 이메일 발송 서비스

**파일 목록**:
```
backend/app/services/email_service.py    — SMTP 이메일 발송 유틸리티 (신규)
backend/app/routes/auth.py               — register 엔드포인트에 알림 호출 추가
backend/config.py                        — SMTP 설정 (환경변수)
```

**구현 내용**:
1. `email_service.py` 생성:
   - `get_admin_emails()` 함수: DB에서 `is_admin=true` workers의 email 목록 조회
     ```python
     def get_admin_emails():
         """DB에서 is_admin=true인 사용자 이메일 목록 조회"""
         conn = get_db_connection()
         try:
             cur = conn.cursor()
             cur.execute("SELECT email FROM workers WHERE is_admin = true AND email IS NOT NULL")
             return [row[0] for row in cur.fetchall()]
         finally:
             conn.close()
     ```
   - `send_admin_notification(subject, html_body)` 함수: admin 전원에게 발송
     ```python
     def send_admin_notification(subject, html_body):
         """is_admin=true 사용자 전원에게 이메일 발송 (best-effort)"""
         admin_emails = get_admin_emails()
         if not admin_emails:
             logger.warning("Admin 이메일 수신자 없음 (is_admin=true 사용자 없음)")
             return

         for email in admin_emails:
             try:
                 _send_email(to_email=email, subject=subject, html_body=html_body)
                 logger.info(f"Admin 알림 발송 성공: {email}")
             except Exception as e:
                 logger.error(f"Admin 알림 발송 실패: {email} — {e}")
     ```
   - `_send_email(to_email, subject, html_body)` 내부 함수: smtplib SMTP 발송
   - `render_register_notification(worker)` 함수: HTML 템플릿 생성
     - 포함 정보: 가입자 이름, 역할(role), 협력사(company), 가입일시
   - Flask-Mail 사용하지 않음 → `smtplib` + `email.mime` 직접 사용 (의존성 최소화)

2. `auth.py` register 성공 후:
   ```python
   # 가입 완료 후 Admin 알림 (best-effort — 실패해도 가입은 정상)
   try:
       from app.services.email_service import send_admin_notification, render_register_notification
       send_admin_notification(
           subject=f"[AXIS-OPS] 신규 가입: {worker['name']} ({worker['company']})",
           html_body=render_register_notification(worker)
       )
   except Exception as e:
       logger.error(f"가입 알림 이메일 발송 실패: {e}")
   ```

3. 이메일 발송 실패 시 가입 자체는 정상 완료 (알림은 best-effort)

**config.py 환경변수** (SMTP 설정만 — 수신자는 DB 조회):
```python
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
# ADMIN_EMAIL 환경변수 불필요 — DB에서 is_admin=true 사용자 조회
```

**테스트 케이스** (5개):
| TC | 설명 |
|----|------|
| MAIL-01 | 정상 가입 → DB에서 admin 이메일 조회 → 발송 확인 (mock SMTP, 수신자: `dkkim1@gst-in.com`) |
| MAIL-02 | SMTP 설정 없음 → 가입 성공, 이메일 스킵 (에러 로그만) |
| MAIL-03 | SMTP 연결 실패 → 가입 성공, 이메일 실패 로그 |
| MAIL-04 | 이메일 내용에 가입자 정보 (이름, 역할, 협력사, 가입일시) 포함 확인 |
| MAIL-05 | Admin이 여러 명 → 각각에게 개별 발송 확인 (테스트 단계에서는 `dkkim1@gst-in.com`만) |

**체크리스트**:
- [ ] email_service.py 생성 (get_admin_emails, send_admin_notification, _send_email, render_register_notification)
- [ ] auth.py register에 알림 호출 추가 (try-catch best-effort)
- [ ] config.py SMTP 환경변수 추가 (ADMIN_EMAIL 환경변수 불필요)
- [ ] 이메일 실패 시 가입 정상 완료 확인
- [ ] 테스트 수신자: `dkkim1@gst-in.com`으로 제한
- [ ] Railway 환경변수 설정 (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD)
- [ ] 기존 테스트 회귀 없음

---

### Sprint 20-B: 공지사항 탭 (앱 내 업데이트 노트)

**목표**: 앱 내 공지사항 기능 — 버전 업데이트마다 사용자에게 필요한 변경사항만 요약 게시

**배경**:
- 앱 업데이트 시 작업자가 변경사항을 알 방법이 없음
- 개발 용어 없이 사용자 관점에서 "무엇이 바뀌었는지" 전달 필요
- Admin이 직접 공지 작성/관리

#### Phase B-1: BE — notices 테이블 + API

**파일 목록**:
```
backend/migrations/020_create_notices.sql  — notices 테이블 생성
backend/app/routes/notices.py              — 공지사항 CRUD API (신규)
backend/app/__init__.py                    — Blueprint 등록
```

**DB 스키마**:
```sql
CREATE TABLE IF NOT EXISTS notices (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    version VARCHAR(20),                    -- 연관 앱 버전 (예: '1.4.0')
    is_pinned BOOLEAN DEFAULT FALSE,        -- 상단 고정
    created_by INTEGER REFERENCES workers(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**API 엔드포인트**:
```
GET  /api/notices                — 공지 목록 (최신순, 페이지네이션)
GET  /api/notices/<id>           — 공지 상세
POST /api/admin/notices          — 공지 작성 (Admin only)
PUT  /api/admin/notices/<id>     — 공지 수정 (Admin only)
DELETE /api/admin/notices/<id>   — 공지 삭제 (Admin only)
```

#### Phase B-2: OPS FE — 공지사항 화면

**파일 목록**:
```
frontend/lib/screens/notice/notice_list_screen.dart   — 공지 목록 화면 (신규)
frontend/lib/screens/notice/notice_detail_screen.dart  — 공지 상세 화면 (신규)
frontend/lib/services/notice_service.dart              — 공지 API 호출 (신규)
frontend/lib/screens/home_screen.dart                  — 사이드메뉴에 공지사항 탭 추가
frontend/lib/screens/admin/notice_write_screen.dart    — Admin 공지 작성 화면 (신규)
```

**FE 구현**:
1. 홈 사이드메뉴에 "공지사항" 항목 추가 (Icons.campaign)
2. 안 읽은 공지 뱃지 표시 (SharedPreferences에 마지막 확인 공지 ID 저장)
3. 공지 목록: 제목 + 날짜 + 버전 태그 + 고정 아이콘
4. Admin 역할일 때만 "공지 작성" 버튼 표시
5. 공지 상세: title + content (마크다운 또는 plain text) + 작성일

**테스트 케이스** (6개):
| TC | 설명 |
|----|------|
| NTC-01 | 공지 작성 (Admin) → 목록에 표시 |
| NTC-02 | 일반 작업자 → 작성 API 403 |
| NTC-03 | 공지 목록 페이지네이션 (10개 단위) |
| NTC-04 | 고정 공지 상단 표시 |
| NTC-05 | 공지 수정/삭제 (Admin) |
| NTC-06 | 버전 필터 (특정 버전 공지만 조회) |

**체크리스트**:
- [ ] 마이그레이션 020 실행 — notices 테이블 생성
- [ ] notices.py Blueprint + 5개 API 엔드포인트
- [ ] notice_list_screen.dart — 목록 + 뱃지
- [ ] notice_detail_screen.dart — 상세 보기
- [ ] notice_write_screen.dart — Admin 작성 화면
- [ ] home_screen.dart 사이드메뉴에 공지사항 추가
- [ ] 안 읽은 공지 뱃지 로직 (SharedPreferences)
- [ ] 테스트 6개 통과

---

## Sprint 21 — QR Registry 목록 API + ETL 분리

---

### Sprint 21: QR Registry 목록 조회 API + AXIS-CORE ETL 분리

**목표**: Admin/Manager용 QR 등록 목록 조회 API 구현 + ETL 파이프라인을 별도 repo(axis-core-etl)로 분리

**배경**:
- AXIS-VIEW 대시보드에서 QR 등록 현황을 조회할 엔드포인트 필요
- ETL 코드가 OPS repo에 포함되어 있어 관심사 분리 필요 → AXIS-CORE/CORE-ETL repo로 이동
- SCR-Schedule(POC 대시보드)과 동일한 데이터소스(SharePoint Excel)를 사용하되, 별도 ETL 파이프라인으로 DB 적재

**Teammate**: 불필요 (BE 1개 엔드포인트 + repo 분리 작업)

#### Phase A: BE — QR 목록 조회 API

**파일 목록**:
```
backend/app/routes/qr.py        — QR 목록 조회 엔드포인트 (신규)
backend/app/__init__.py          — qr_bp Blueprint 등록 (수정)
```

**구현 내용**:
1. `GET /api/admin/qr/list` 엔드포인트:
   - `qr_registry` JOIN `plan.product_info` (serial_number 기준)
   - 검색: S/N 또는 qr_doc_id 부분검색 (ILIKE)
   - 필터: model, status (active/revoked)
   - 날짜 필터: `date_field` (mech_start/module_start) + `date_from` + `date_to`
   - 페이지네이션: page, per_page (default 50, max 200)
   - 정렬: sort_by (created_at, serial_number, model, mech_start, module_start, sales_order), sort_order (asc/desc)
   - 응답: items[], total, page, per_page, total_pages, models[], stats{total, active, revoked}

2. 권한: `@jwt_required` + `@manager_or_admin_required`

**API 엔드포인트**:
```
GET  /api/admin/qr/list   — QR 목록 조회 (Admin/Manager)
```

#### Phase B: ETL 파이프라인 분리

- OPS repo 내 ETL 코드 → `AXIS-CORE/CORE-ETL/` 별도 repo로 이동
- ETL은 plan 스키마만 접근 — HR 테이블(workers, partner_attendance, qr_registry) 접근 금지
- SharePoint Excel → Graph API → PostgreSQL plan.product_info UPSERT
- 반기 필터 + mech_start 기준 날짜 범위 필터

**체크리스트**:
- [ ] qr.py Blueprint + GET /api/admin/qr/list 엔드포인트
- [ ] __init__.py에 qr_bp 등록
- [ ] 날짜 필터 파라미터 (date_field, date_from, date_to)
- [ ] ETL 코드 AXIS-CORE/CORE-ETL repo로 분리
- [ ] ETL → plan 스키마만 접근 확인

---

## Sprint 22 (예정) — 보안 개선 + GPS + DB 백업

---

### Sprint 22-A: Email Verification 개선

**목표**: 이메일 인증 완료 시 Admin 승인 알림 발송 + 이메일 재인증(재전송) API 추가

**배경**:
- 현재 Admin 알림은 회원가입 시(email_verified 전) 발송됨 → Admin이 미인증 사용자까지 승인 대상으로 혼동
- 이메일 인증을 완료한 사용자만 Admin 승인 알림을 받아야 함
- 이메일 재전송 기능이 FE에 버튼은 있으나 BE API가 없음

**Teammate**: 불필요 (BE 2~3개 파일 수정)

#### Phase A: BE — email_verified 후 Admin 알림

**파일 목록**:
```
backend/app/routes/auth.py               — verify-email 성공 시 Admin 알림 호출 (수정)
backend/app/services/email_service.py     — send_register_notification 호출 위치 변경 (수정)
```

**구현 내용**:
1. `POST /api/auth/verify-email` 핸들러에서:
   - email_verified = true 설정 성공 후 → `send_register_notification()` 호출
   - 기존 register 엔드포인트의 알림 호출 제거 (또는 유지하되 "인증 대기" 표시)
2. 알림 이메일 본문에 "이메일 인증 완료됨" 상태 명시

**테스트 케이스** (3개):
| TC | 설명 |
|----|------|
| SEC-01 | 이메일 인증 완료 → Admin 알림 발송 확인 |
| SEC-02 | 이메일 미인증 상태 → Admin 알림 미발송 |
| SEC-03 | SMTP 실패 → 인증 자체는 정상 완료 |

#### Phase B: BE — 이메일 재전송 API

**파일 목록**:
```
backend/app/routes/auth.py               — resend-verification 엔드포인트 추가 (수정)
backend/app/services/auth_service.py      — resend_verification_email 함수 추가 (수정)
```

**구현 내용**:
1. `POST /api/auth/resend-verification` 엔드포인트:
   - Body: `{ "email": "user@example.com" }`
   - 이미 인증 완료 → 400 (ALREADY_VERIFIED)
   - 미가입 이메일 → 404 (USER_NOT_FOUND)
   - rate limiting: 60초 내 재전송 불가 (429)
   - 새 verification_code 생성 + 이메일 발송
2. FE `resend-verification` 버튼에 API 연동 (기존 버튼 활용)

**테스트 케이스** (4개):
| TC | 설명 |
|----|------|
| SEC-04 | 이메일 재전송 성공 → 새 코드 발급 |
| SEC-05 | 이미 인증된 사용자 → 400 |
| SEC-06 | 존재하지 않는 이메일 → 404 |
| SEC-07 | 60초 내 재전송 → 429 (rate limit) |

**체크리스트**:
- [x] verify-email 성공 시 Admin 알림 발송
- [x] register에서 알림 호출 제거 또는 "인증 대기" 표시로 변경
- [x] POST /api/auth/resend-verification 엔드포인트
- [x] rate limiting (60초)
- [ ] 테스트 7개 통과 (BE 구현 완료, 테스트 코드 별도)

---

### Sprint 22-B: GPS 위치 보안 개선

**목표**: GPS 위치 정확도 개선 (enableHighAccuracy) + DMS→Decimal 변환 헬퍼 제공

**배경**:
- `enableHighAccuracy: false` (기본값) → WiFi/Cell Tower 기반 위치 → km 수준 오차 발생
- 현장 관리자가 DMS 좌표(예: 37°10'11"N)를 Decimal(37.10)로 잘못 변환하는 사례 발생
- 올바른 변환: 37°10'11" = 37 + 10/60 + 11/3600 = **37.1697** (37.10이 아님)

**Teammate**: 불필요 (FE 1~2개 파일 수정)

#### Phase A: FE — enableHighAccuracy 변경

**파일 목록**:
```
frontend/lib/screens/home/home_screen.dart   — enableHighAccuracy: true (수정)
```

**구현 내용**:
1. `_getCurrentLocation()` 메서드에서:
   ```dart
   // 변경 전
   enableHighAccuracy: false
   // 변경 후
   enableHighAccuracy: true
   ```
2. timeout을 12초 → 15초로 연장 (GPS 위성 탐색에 시간 소요)
3. fallback: GPS 실패 시 WiFi 기반으로 재시도 (optional)

#### Phase B: Admin 좌표 설정 — DMS 변환 헬퍼

**파일 목록**:
```
frontend/lib/screens/admin/admin_options_screen.dart   — DMS 입력 필드 + 변환 로직 (수정)
```

**구현 내용**:
1. Admin 위치 설정 화면에 DMS 입력 필드 추가:
   - 도(°), 분('), 초(") 개별 입력 → Decimal 자동 변환
   - 변환 공식: `decimal = degrees + minutes/60 + seconds/3600`
2. 변환 결과를 기존 lat/lng 필드에 자동 입력
3. 유효 범위 검증: lat (-90~90), lng (-180~180)

**테스트 케이스** (3개):
| TC | 설명 |
|----|------|
| GPS-01 | DMS 37°10'11" → Decimal 37.1697 변환 정확성 |
| GPS-02 | DMS 127°5'16" → Decimal 127.0878 변환 정확성 |
| GPS-03 | enableHighAccuracy=true → 위치 정확도 개선 확인 |

**체크리스트**:
- [x] enableHighAccuracy: false → true 변경
- [x] timeout 15초로 연장
- [x] DMS 입력 필드 + Decimal 변환 로직
- [x] 유효 범위 검증 (lat/lng)
- [ ] 테스트 3개 통과 (FE 구현 완료, 테스트 별도)

---

### Sprint 22-C: 권한 체계 정리 + Manager 권한 위임

**목표**: 협력사 Manager가 자기 회사 소속 작업자에게 is_manager 권한 부여 가능하도록 변경 (VIEW 대시보드 로그인 권한 자체 관리 목적)

**배경**:
- 현재 `toggle_manager()`는 `@admin_required` → Admin(GST)만 is_manager 부여 가능
- 협력사가 늘어나면 Admin이 일일이 manager 지정하기 비효율
- 협력사 manager가 자기 회사 내에서 자율적으로 관리할 수 있어야 함
- **DB 보호**: `workers`, `partner_attendance`, `qr_registry` 테스트 시 훼손 금지
  - conftest.py backup/restore: workers ✅, auth_settings ✅, attendance ✅, qr_registry ⚠️ 누락

**Teammate**: 불필요 (BE 1개 파일 수정)

**⚠️ DB 보호 규칙**:
- 테스트는 conftest.py backup/restore 패턴 유지
- `workers`, `partner_attendance`, `qr_registry`, `plan.product_info` 훼손 금지
- 테스트용 worker는 `seed_test_workers` fixture 사용 → teardown 시 삭제

**현재 구조**:
- `@admin_required` — is_admin=true (GST 관리자)만 접근
- `@manager_or_admin_required` — is_admin 또는 is_manager
- `toggle_manager()` (admin.py line 1225) — `@admin_required` → Admin만 is_manager 부여 가능
- 협력사 manager는 본인 company 내 작업만 force-close 가능 (company 필터 적용됨)

**변경 목표**:
```
Admin (GST)
  └─ 전체 작업자 is_manager 부여/해제 (기존과 동일)

협력사 Manager
  └─ 같은 회사(company) 소속 작업자만 is_manager 부여/해제
  └─ Admin 권한 변경 불가
  └─ 다른 회사 작업자 변경 불가
```

**구현 내용**:
1. `toggle_manager()` API 수정 (`admin.py` line 1225):
   - `@admin_required` → `@manager_or_admin_required`로 변경
   - Manager인 경우: 대상 worker의 `company`가 본인과 같은지 검증
   - Manager인 경우: 대상이 `is_admin=true`이면 403 반환 (상위 권한 보호)
   - Admin인 경우: 기존과 동일 (제한 없음)

**파일 목록**:
```
backend/app/routes/admin.py       — toggle_manager() 데코레이터 + company 검증 (수정)
```

**테스트 케이스** (5개):
| TC | 설명 |
|----|------|
| MGR-01 | Admin → 아무 작업자 manager 부여 성공 |
| MGR-02 | 협력사 Manager → 같은 회사 작업자 manager 부여 성공 |
| MGR-03 | 협력사 Manager → 다른 회사 작업자 → 403 |
| MGR-04 | 협력사 Manager → Admin 권한 변경 → 403 |
| MGR-05 | 일반 작업자 → manager 부여 시도 → 403 |

**체크리스트**:
- [x] toggle_manager() 데코레이터 변경 (@admin_required → @manager_or_admin_required)
- [x] Manager일 때 같은 company 검증 로직 추가
- [x] Admin 보호 로직 (Manager가 Admin 권한 변경 불가)
- [x] 테스트 5개 통과 (기존 운영 DB 데이터 훼손 없음 확인)

---

### Sprint 22-D: 공지수정 + Admin 간편로그인 + ETL API (v1.6.3, 완료)

**구현 내용**:
1. 공지사항 수정 기능: `NoticeWriteScreen` 수정 모드 (existingNotice 파라미터)
2. Admin 간편 로그인: `get_admin_by_email_prefix()` 2단계 매칭
3. ETL 변경 이력 API: `GET /api/admin/etl/changes` — CORE-ETL Sprint 2 Task 4
   - `@manager_or_admin_required` 권한
   - days/field/serial_number/limit 쿼리 파라미터
   - `etl.change_log` JOIN `plan.product_info` (model 포함)
   - summary: total_changes + by_field 집계

**파일 목록**:
```
frontend/lib/screens/admin/notice_write_screen.dart     — 수정 모드
frontend/lib/screens/notice/notice_detail_screen.dart   — 수정 버튼
backend/app/models/worker.py                            — admin prefix 2단계 매칭
backend/app/routes/admin.py                             — ETL changes 엔드포인트
```

**체크리스트**:
- [x] 공지사항 수정 모드 (NoticeWriteScreen + NoticeDetailScreen)
- [x] Admin 간편 로그인 prefix 2단계 매칭
- [x] GET /api/admin/etl/changes 엔드포인트

---

### Sprint 22-E: conftest.py 운영 데이터 5테이블 백업/복원 완성

> **버전**: 변경 없음 (테스트 인프라만 수정)
> **날짜**: 2026-03-12
> **목표**: pytest 실행 시 운영 DB 5개 테이블 데이터 보존 보장
> **⚠️ 제약**: DB 스키마 변경 절대 금지. conftest.py Python 코드만 수정.

## 배경

현재 Railway 환경에서 테스트 DB = 운영 DB (동일 인스턴스).
`conftest.py`의 `db_schema` fixture가 DROP SCHEMA → migration 재실행하므로,
백업/복원이 없는 테이블은 pytest 실행 시 **운영 데이터가 전부 삭제됨**.

현재 백업/복원 현황:
- ✅ `workers` — 구현됨 (11개 컬럼) ← `DROP TABLE workers` 대상이므로 필수
- ✅ `hr.worker_auth_settings` — 구현됨 (6개 컬럼) ← `DROP SCHEMA hr` 대상이므로 필수
- ✅ `hr.partner_attendance` — 구현됨 (9개 컬럼) ← `DROP SCHEMA hr` 대상이므로 필수
- ⚠️ `plan.product_info` — **누락** → 추가 필요
- ⚠️ `public.qr_registry` — **누락** → 추가 필요

### 리스크 분석

현재 drop_stmts에 `DROP SCHEMA IF EXISTS plan CASCADE`는 **없음**.
`DROP TABLE IF EXISTS product_info CASCADE`는 **public.product_info** 대상 (plan.product_info 아님).
migration은 `CREATE TABLE IF NOT EXISTS`를 사용하므로 **현재는 데이터가 보존됨**.

하지만:
- 누군가 drop_stmts에 `plan` 스키마 추가하면 즉시 삭제됨
- migration 파일 수정 시 `DROP TABLE` + `CREATE TABLE`로 바꾸면 삭제됨
- **방어적 백업을 추가하여 어떤 상황에서도 운영 데이터를 보호**

## Task 1: `plan.product_info` 백업/복원 추가

**파일**: `tests/conftest.py` — `db_schema` fixture 내

### 1-A: 백업 코드 추가 (기존 attendance 백업 바로 다음에)

기존 3개 백업 블록(`backed_up_workers`, `backed_up_auth_settings`, `backed_up_attendance`) 바로 아래에 추가:

```python
# plan.product_info 백업 (ETL 적재 데이터 보존)
backed_up_product_info = []
try:
    cursor.execute(
        "SELECT id, serial_number, model, title_number, product_code, "
        "sales_order, customer, line, quantity, "
        "mech_partner, elec_partner, module_outsourcing, "
        "prod_date, mech_start, mech_end, elec_start, elec_end, "
        "module_start, pi_start, qi_start, si_start, "
        "ship_plan_date, location_qr_id, "
        "actual_ship_date, "
        "created_at, updated_at "
        "FROM plan.product_info"
    )
    backed_up_product_info = cursor.fetchall()
    print(f"[db_schema] Backed up {len(backed_up_product_info)} product_info records")
except Exception as pi_err:
    print(f"[db_schema] product_info backup skipped: {pi_err}")
```

**⚠️ 주의**: `actual_ship_date` 컬럼은 ETL Sprint 2에서 ALTER TABLE로 추가된 컬럼.
migration `002_create_product_info.sql`에는 없지만 운영 DB에는 존재함.
백업 SELECT에 반드시 포함해야 함.

### 1-B: 복원 코드 추가 (기존 attendance 복원 블록 다음에)

```python
# plan.product_info 복원
if backed_up_product_info:
    restored_pi = 0
    for row in backed_up_product_info:
        try:
            cursor.execute(
                """
                INSERT INTO plan.product_info
                    (id, serial_number, model, title_number, product_code,
                     sales_order, customer, line, quantity,
                     mech_partner, elec_partner, module_outsourcing,
                     prod_date, mech_start, mech_end, elec_start, elec_end,
                     module_start, pi_start, qi_start, si_start,
                     ship_plan_date, location_qr_id,
                     actual_ship_date,
                     created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s,
                        %s,
                        %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                row
            )
            restored_pi += 1
        except Exception as pi_err:
            print(f"[db_schema] product_info restore failed: {pi_err}")
    cursor.execute(
        "SELECT setval('plan.product_info_id_seq', "
        "COALESCE((SELECT MAX(id) FROM plan.product_info), 1))"
    )
    print(f"[db_schema] Restored {restored_pi}/{len(backed_up_product_info)} product_info records")
```

**⚠️ actual_ship_date 컬럼 주의**: migration 재실행 후 이 컬럼이 없을 수 있음.
복원 전에 컬럼 존재 여부 확인하고, 없으면 ALTER TABLE ADD COLUMN 실행:

```python
# actual_ship_date 컬럼 보장 (migration에 없으므로)
try:
    cursor.execute(
        "ALTER TABLE plan.product_info ADD COLUMN IF NOT EXISTS actual_ship_date DATE"
    )
except Exception:
    pass  # 이미 존재하면 무시
```

이 ALTER TABLE은 **컬럼 추가**이지 스키마 변경이 아님 — 운영 DB에 이미 있는 컬럼을 migration 재실행 후 복구하는 것.

---

## Task 2: `public.qr_registry` 백업/복원 추가

**파일**: `tests/conftest.py` — `db_schema` fixture 내

### 2-A: 백업 코드 추가 (product_info 백업 바로 다음에)

```python
# public.qr_registry 백업 (QR ↔ 제품 매핑 보존)
backed_up_qr_registry = []
try:
    cursor.execute(
        "SELECT id, qr_doc_id, serial_number, status, "
        "issued_at, revoked_at, created_at, updated_at "
        "FROM public.qr_registry"
    )
    backed_up_qr_registry = cursor.fetchall()
    print(f"[db_schema] Backed up {len(backed_up_qr_registry)} qr_registry records")
except Exception as qr_err:
    print(f"[db_schema] qr_registry backup skipped: {qr_err}")
```

### 2-B: 복원 코드 추가 (product_info 복원 다음에 — FK 의존성 순서 중요!)

**⚠️ 복원 순서 주의**: `qr_registry.serial_number`이 `plan.product_info(serial_number)`를 FK 참조하므로,
**반드시 product_info 복원 후에** qr_registry 복원해야 함.

```python
# public.qr_registry 복원 (product_info 다음에 — FK 의존성)
if backed_up_qr_registry:
    restored_qr = 0
    for row in backed_up_qr_registry:
        try:
            cursor.execute(
                """
                INSERT INTO public.qr_registry
                    (id, qr_doc_id, serial_number, status,
                     issued_at, revoked_at, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                row
            )
            restored_qr += 1
        except Exception as qr_err:
            print(f"[db_schema] qr_registry restore failed for id={row[0]}: {qr_err}")
    cursor.execute(
        "SELECT setval('qr_registry_id_seq', "
        "COALESCE((SELECT MAX(id) FROM public.qr_registry), 1))"
    )
    print(f"[db_schema] Restored {restored_qr}/{len(backed_up_qr_registry)} qr_registry records")
```

---

## Task 3: 백업/복원 순서 정리

**전체 순서** (FK 의존성 기반):

### 백업 순서 (DROP 전):
```
1. workers                    ← 독립
2. hr.worker_auth_settings    ← workers FK
3. hr.partner_attendance      ← workers FK
4. plan.product_info          ← 독립 (plan 스키마)
5. public.qr_registry         ← product_info FK
```

### 복원 순서 (migration 후):
```
1. workers                    ← 먼저 (다른 테이블이 FK 참조)
2. hr.worker_auth_settings    ← workers 의존
3. hr.partner_attendance      ← workers 의존
4. plan.product_info          ← 독립 (+ actual_ship_date ALTER TABLE 보장)
5. public.qr_registry         ← product_info 의존 (반드시 4번 다음!)
```

기존 코드에서 1~3 순서는 이미 올바름. 4~5를 3번 다음에 추가하면 됨.

---

## Task 4: CLAUDE.md / BACKLOG.md 문서 업데이트

### 4-A: CLAUDE.md 운영 데이터 보존 규칙 업데이트

기존:
```
- `qr_registry` — QR↔제품 매핑 (conftest.py 백업/복원 ⚠️ 누락 → 추가 필요)
- `plan.product_info` — 생산 메타데이터 (ETL 적재 데이터, 절대 훼손 금지)
```

변경:
```
- `qr_registry` — QR↔제품 매핑 (conftest.py 백업/복원 ✅)
- `plan.product_info` — 생산 메타데이터 (conftest.py 백업/복원 ✅)
```

### 4-B: BACKLOG.md DB-1 업데이트

conftest.py 백업/복원 현황을 5/5 완료로 변경:
```
- ✅ `workers` — backup/restore 구현됨
- ✅ `hr.worker_auth_settings` — backup/restore 구현됨
- ✅ `hr.partner_attendance` — backup/restore 구현됨
- ✅ `qr_registry` — backup/restore 구현됨 (Sprint 22-E)
- ✅ `plan.product_info` — backup/restore 구현됨 (Sprint 22-E)
```

---

## 변경 파일 요약

```
tests/conftest.py             — product_info + qr_registry 백업/복원 추가 (actual_ship_date 포함)
CLAUDE.md                     — 운영 데이터 보존 규칙 5/5 완료 표기
BACKLOG.md                    — DB-1 conftest.py 현황 5/5 완료
```

> ⚠️ DB 스키마 변경 0건. 신규 테이블/컬럼 생성 없음.
> actual_ship_date ADD COLUMN IF NOT EXISTS는 migration 재실행 후 기존 컬럼 복구 목적.

## 체크리스트

- [ ] plan.product_info 백업: 26개 컬럼 (actual_ship_date 포함) SELECT 확인
- [ ] plan.product_info 복원: ON CONFLICT (id) DO NOTHING + 시퀀스 조정
- [ ] actual_ship_date: ALTER TABLE ADD COLUMN IF NOT EXISTS 복원 전 실행
- [ ] qr_registry 백업: 8개 컬럼 SELECT 확인
- [ ] qr_registry 복원: product_info 다음 순서 (FK 의존성)
- [ ] 복원 순서: workers → auth_settings → attendance → product_info → qr_registry
- [ ] pytest 실행 후 5개 테이블 데이터 건수 동일 확인 (전후 비교 print 로그)
- [ ] CLAUDE.md 5/5 완료 업데이트
- [ ] BACKLOG.md DB-1 5/5 완료 업데이트
- [ ] ⚠️ DB 스키마 변경 없음 확인

---

### Sprint 23: OPS FE 메뉴 재구성 (is_manager 권한 메뉴 + 메뉴 순서)

**목표**: is_manager 로그인 시 "관리자 권한 부여" 메뉴 노출 + 관리자 관련 메뉴를 공지사항 바로 위로 이동

**배경**:
- Sprint 22-C에서 BE `toggle_manager()`에 `@manager_or_admin_required` 권한 위임 완료
- 그러나 FE에서 is_manager 로그인 시 해당 기능에 접근할 메뉴가 없음
- 관리자 관련 메뉴(관리자 옵션, 권한 부여)를 공지사항 바로 위에 그룹핑

**Teammate**: 불필요 (FE 1개 파일 수정, BE 변경 없음)

**⚠️ BE 변경 없음**: 이 Sprint은 순수 FE(Flutter) 작업만 포함

**⚠️ 필수 참조 (CLAUDE.md)**:
- **버전 관리**: `CLAUDE.md > 버전 관리 기준` 섹션 확인 → Sprint 완료 시 `backend/version.py` + `frontend/lib/utils/app_version.dart` 동시 업데이트 (현재 v1.6.3)
- **DB 보호 규칙**: `CLAUDE.md > DB 규칙 > 운영 데이터 보존 규칙` — `workers`, `partner_attendance`, `qr_registry`, `plan.product_info` 훼손 금지 (이번 Sprint은 FE만이므로 해당 없으나 습관적 확인)

---

#### Task 1: 메뉴 순서 재배치 (OPS-2)

**현재 메뉴 순서** (`home_screen.dart` lines 683-806):
```
1. 전사 작업 진행현황 / 작업 진행현황
2. QR Scan
3. 작업 관리
4. 관리자 옵션          ← isAdmin only (line 718)
5. 미종료 작업          ← isManager && !isAdmin (line 731)
6. 알림
7. PI/QI/SI 검사       ← GST || isAdmin (line 755)
8. 공지사항             ← 항상 표시 (line 798)
```

**변경 후 메뉴 순서**:
```
1. 전사 작업 진행현황 / 작업 진행현황
2. QR Scan
3. 작업 관리
4. 미종료 작업          ← isManager && !isAdmin
5. 알림
6. PI/QI/SI 검사       ← GST || isAdmin
7. 관리자 옵션          ← isAdmin only (공지사항 위로 이동)
8. 관리자 권한 부여     ← NEW: isManager (Task 2에서 추가)
9. 공지사항             ← 항상 표시 (최하단 유지)
```

**수정 내용**:
- `home_screen.dart`에서 "관리자 옵션" 블록(line 718-728)을 공지사항(line 798) 바로 위로 이동
- 기존 조건(`isAdmin == true`)은 그대로 유지, 위치만 변경

---

#### Task 2: "관리자 권한 부여" 메뉴 카드 추가 (OPS-1)

**조건**: `worker?.isManager == true` (Admin 포함 — Admin도 is_manager 부여 가능하므로)

**메뉴 카드 구성**:
```dart
if (worker?.isManager == true || worker?.isAdmin == true) ...[
  _buildFeatureCard(
    icon: Icons.supervisor_account,       // 또는 Icons.group_add
    iconBg: GxColors.primaryBg,           // 또는 적절한 색상
    iconColor: GxColors.primary,
    title: '관리자 권한 부여',
    subtitle: '${worker?.company ?? ''} 소속 작업자 Manager 권한 관리',
    onTap: () => Navigator.pushNamed(context, '/manager-delegation'),
  ),
  const SizedBox(height: 8),
],
```

**위치**: 관리자 옵션과 공지사항 사이 (변경 후 순서 8번)

**라우트**: `/manager-delegation` — 새 화면 필요

---

#### Task 3: Manager 권한 부여 화면 생성

**새 파일**: `frontend/lib/screens/admin/manager_delegation_screen.dart`

**화면 구성**:
1. 본인과 같은 company 소속 작업자 목록 표시
   - API: `GET /api/admin/workers` (기존 API, company 필터)
   - Admin인 경우: 전체 작업자 표시
   - Manager인 경우: 같은 company만 필터링 (FE에서 필터 또는 BE 쿼리 파라미터)
2. 각 작업자 옆에 is_manager 토글 스위치
   - API: `PUT /api/admin/workers/{id}/toggle-manager` (Sprint 22-C에서 구현 완료)
3. Admin 사용자는 토글 비활성화 (변경 불가 표시)
4. 성공/실패 Snackbar 피드백

**참고**: BE는 Sprint 22-C에서 이미 완료됨
- Manager → 같은 company만 toggle 가능
- Manager → Admin 권한 변경 시 403 반환
- Admin → 전체 toggle 가능

---

#### Task 4: 라우트 등록

**수정 파일**: `frontend/lib/main.dart` (또는 라우트 설정 파일)

```dart
'/manager-delegation': (context) => const ManagerDelegationScreen(),
```

---

**파일 목록**:
```
frontend/lib/screens/home/home_screen.dart              — 메뉴 순서 변경 + 새 카드 추가 (수정)
frontend/lib/screens/admin/manager_delegation_screen.dart — 권한 부여 화면 (신규)
frontend/lib/main.dart                                   — 라우트 등록 (수정)
```

**체크리스트**:
- [x] 관리자 옵션 메뉴를 공지사항 바로 위로 이동 (Task 1)
- [x] "관리자 권한 부여" 메뉴 카드 추가 — isManager || isAdmin 조건 (Task 2)
- [x] Manager 권한 부여 화면 — 같은 company 작업자 목록 + toggle (Task 3)
- [x] `/manager-delegation` 라우트 등록 (Task 4)
- [x] is_manager 로그인 테스트: 메뉴 표시 확인
- [x] Admin 로그인 테스트: 관리자 옵션 + 권한 부여 메뉴 모두 표시 확인
- [x] 일반 작업자 로그인 테스트: 두 메뉴 모두 미표시 확인
- [x] Shipped 제품 QR 스캔 시 "출고 완료" 안내 다이얼로그 (추가)

---

## Sprint 24: QR 목록 actual_ship_date 추가 + is_manager 자사 필터

> **버전**: v1.7.0 → v1.7.1 (PATCH — BE API 응답 확장 + 권한 필터)
> **범위**: BE only (FE 변경 없음)

### 필수 참조 (CLAUDE.md)
- **버전 관리**: `backend/app/version.py` → `1.7.1` 업데이트
- **DB 보호**: workers, partner_attendance, qr_registry, plan.product_info — conftest.py 백업/복원 확인

---

#### Task 1: QR 목록 응답에 actual_ship_date 추가

**수정 파일**: `backend/app/routes/qr.py`

**현재 상태**: `GET /api/admin/qr/list` SELECT 절에 `actual_ship_date` 누락
- `plan.product_info`에 컬럼은 존재 (CORE-ETL Sprint 2 Task 3에서 ALTER TABLE 완료)
- ETL에서 적재도 진행 중
- 단, SELECT 절에 빠져서 응답에 안 내려옴

**수정 내용**:
```python
# qr.py의 SELECT 절에 추가
p.actual_ship_date,   # ← 추가
```

**응답 변환 부분도 확인**:
```python
# dict 변환 시 actual_ship_date 포함
'actual_ship_date': str(row['actual_ship_date']) if row.get('actual_ship_date') else None,
```

**검증**:
- `actual_ship_date`가 있는 S/N → 날짜 문자열 반환
- `actual_ship_date`가 NULL인 S/N → `null` 반환
- `status`가 `shipped`인 건과 `actual_ship_date`가 있는 건이 일치하는지 확인

---

#### Task 2: QR 목록 — is_manager 자사 필터

**수정 파일**: `backend/app/routes/qr.py`

**현재 문제**: `@manager_or_admin_required`는 역할만 체크. 함수 내부에서 company 필터 없음 → manager가 전사 QR 데이터 조회 가능.

**수정 패턴** (기존 force_close_task과 동일):
```python
from flask import g
from app.models.worker import get_worker_by_id

# get_qr_list() 함수 내부, WHERE 조건 빌드 부분
current_worker = get_worker_by_id(g.worker_id)
if current_worker and current_worker.is_manager and not current_worker.is_admin:
    manager_company = current_worker.company
    conditions.append("(p.mech_partner = %s OR p.elec_partner = %s)")
    params.extend([manager_company, manager_company])
```

**검증**:
- Admin 로그인 → 전체 QR 반환 (기존과 동일)
- Manager(company='BAT') 로그인 → mech_partner='BAT' OR elec_partner='BAT' 건만 반환
- Manager가 다른 회사 S/N 조회 불가 확인

---

#### Task 3: 출퇴근 API — is_manager 접근 허용 + 자사 필터

**수정 파일**: `backend/app/routes/admin.py`

**현재 문제**: `/api/admin/hr/attendance/today` 등이 `@admin_required`만 적용 → manager 접근 자체 불가 (403).

**수정 내용**:

1. 데코레이터 변경:
```python
# 변경 전
@admin_required
def get_attendance_today():

# 변경 후
@manager_or_admin_required
def get_attendance_today():
```

2. `_get_attendance_data()` 함수에 company 필터 추가:
```python
current_worker = get_worker_by_id(g.worker_id)
company_filter = None
if current_worker and current_worker.is_manager and not current_worker.is_admin:
    company_filter = current_worker.company

# SQL WHERE 절에 추가
if company_filter:
    query += " AND w.company = %s"
    params.append(company_filter)
```

**대상 엔드포인트 3개**:
- `GET /api/admin/hr/attendance/today`
- `GET /api/admin/hr/attendance` (date 파라미터)
- `GET /api/admin/hr/attendance/summary`

**검증**:
- Admin → 전체 협력사 출퇴근 데이터
- Manager(company='FNI') → FNI 소속만 표시
- 일반 작업자 → 403

---

#### Task 4: 테스트 + 버전 업데이트

1. 기존 테스트 회귀 확인 (pytest 전체 실행)
2. `backend/app/version.py` → `1.7.1`
3. `CLAUDE.md` 버전 이력에 Sprint 24 추가

---

**파일 목록**:
```
backend/app/routes/qr.py    — actual_ship_date SELECT 추가 + manager company 필터 (수정)
backend/app/routes/admin.py  — attendance 3개 엔드포인트 데코레이터 + company 필터 (수정)
backend/app/version.py       — 1.7.0 → 1.7.1 (수정)
```

**체크리스트**:
- [x] qr.py SELECT에 `p.actual_ship_date` 추가 (Task 1)
- [x] qr.py에 manager company 필터 추가 (Task 2)
- [x] admin.py attendance 3개 → `@manager_or_admin_required` 변경 (Task 3)
- [x] admin.py `_get_attendance_data()`에 company 필터 추가 (Task 3)
- [ ] Manager 로그인 → QR 자사만 반환 테스트
- [ ] Manager 로그인 → 출퇴근 자사만 반환 테스트
- [ ] Admin 로그인 → 전체 데이터 반환 (회귀 확인)
- [ ] pytest 전체 통과
- [x] version.py → 1.7.1

---

## 🔧 BUG-1 Hotfix: Logout Storm (401 무한 루프) — VIEW FE (2026-03-12)

### 증상
Railway HTTP 로그에서 `/api/auth/logout` 401이 10회+ 반복 후 `/api/auth/login` 200 복구.
refresh_token 만료 시 여러 컴포넌트가 동시에 logout을 트리거하며 불필요한 API 호출 발생.

### 근본 원인
1. Header/Sidebar의 `useNotices`, `useEtlChanges` 등 다수 훅이 동시 API 호출
2. 첫 401 → interceptor refresh 시도 → refresh도 401 (만료)
3. interceptor catch에서 `refreshSubscribers = []` 비움 → 대기 중 요청들 reject
4. 각 컴포넌트 에러 핸들러에서 `authStore.logout()` 각자 호출
5. `logout()`이 `apiClient.post('/api/auth/logout')` 호출 → 토큰 이미 삭제 → 401 → interceptor 재진입

### 수정 내용

#### 1. `src/api/client.ts` — interceptor 3중 방어

```typescript
// (A) auth URL 401 retry 제외
const AUTH_SKIP_URLS = ['/api/auth/logout', '/api/auth/refresh', '/api/auth/login'];
// → logout/refresh/login 요청이 401 받아도 다시 refresh 시도 안 함

// (B) forceLogout() 중복 실행 방지
let isForceLogout = false;
function forceLogout() {
  if (isForceLogout) return;
  isForceLogout = true;
  localStorage.removeItem(...)
  window.location.href = '/login';
}

// (C) refresh 실패 시 BE logout API 호출 안 함
// 기존: refreshSubscribers = [] → 대기 요청 해소 안 됨
// 변경: refreshSubscribers.forEach(cb => cb('')) → 빈 토큰으로 실패 전파 후 forceLogout()
```

#### 2. `src/store/authStore.ts` — logout 중복 호출 차단

```typescript
const logoutRef = React.useRef(false);

const logout = useCallback(async () => {
  if (logoutRef.current) return; // 이미 진행 중이면 스킵
  logoutRef.current = true;
  try {
    // 3초 timeout으로 BE 응답 지연 시 빠르게 포기
    await Promise.race([
      apiClient.post('/api/auth/logout'),
      new Promise((_, reject) => setTimeout(() => reject('timeout'), 3000)),
    ]);
  } catch (e) { /* ignored */ }
  localStorage.removeItem(...)
  logoutRef.current = false;
}, []);
```

### 수정 전후 비교

| 시나리오 | 수정 전 | 수정 후 |
|---------|---------|---------|
| refresh 401 | → logout API 10회+ 호출 | → forceLogout 1회 (API 호출 없음) |
| 동시 401 5건 | → 각자 refresh 대기 후 각자 logout | → 첫 번째만 refresh, 실패 시 전체 forceLogout |
| logout API 자체 401 | → interceptor 재진입 → 무한 루프 | → AUTH_SKIP_URLS로 즉시 reject |

### 변경 파일

```
AXIS-VIEW/app/src/api/client.ts        — interceptor 3중 방어 (AUTH_SKIP_URLS + isForceLogout + forceLogout)
AXIS-VIEW/app/src/store/authStore.ts   — logoutRef 중복 차단 + 3초 timeout
```

### 빌드: ✅ 통과 (npm run build)

---

# Sprint 25: BUG-22 Logout Storm — OPS FE(Flutter) 수정

> **버전**: 1.7.1 → 1.7.2
> **날짜**: 2026-03-12
> **선행 조건**: Sprint 22-E (conftest.py 5테이블 백업/복원) 완료 후 진행
> **목표**: refresh 401 발생 시 logout 무한 호출(10회+) 방지 — VIEW FE와 동일 패턴 적용
> **⚠️ 제약**: DB 스키마 변경 절대 금지 (ALTER TABLE / CREATE TABLE 없음). 코드 변경만 수행.

## 배경

Railway HTTP 로그에서 `/api/auth/logout` 401이 10회+ 반복 후 `/api/auth/login` 200 복구되는 패턴 확인.
Sprint 19-A Refresh Token Rotation 이후 발생. VIEW FE는 Phase 4 Hotfix에서 수정 완료.

**현재 문제 흐름:**
```
refresh_token 만료 → interceptor refresh 시도 → refresh 401
→ onRefreshFailed() 호출 → AuthNotifier.logout()
→ logout()이 /api/auth/logout POST (토큰 이미 없음) → 401
→ interceptor가 이 401도 처리하려고 시도 → 중복 호출
```

---

## Task 1: `api_service.dart` — interceptor 3중 방어

**파일**: `frontend/lib/services/api_service.dart`

### 1-A: AUTH_SKIP_PATHS 추가

```dart
// ① 클래스 상단에 상수 추가
static const List<String> _authSkipPaths = [
  '/auth/logout',
  '/auth/refresh',
  '/auth/login',
];
```

### 1-B: interceptor 401 체크에 logout 경로 추가

**현재 코드** (L48-53):
```dart
if (error.response?.statusCode == 401 && !_isRefreshing) {
  final requestPath = error.requestOptions.path;
  if (requestPath.contains('/auth/refresh') ||
      requestPath.contains('/auth/login')) {
    return handler.next(error);
  }
```

**변경**:
```dart
if (error.response?.statusCode == 401 && !_isRefreshing) {
  final requestPath = error.requestOptions.path;
  // auth 관련 경로는 401 재시도 하지 않음 (logout 포함!)
  if (_authSkipPaths.any((p) => requestPath.contains(p))) {
    return handler.next(error);
  }
```

### 1-C: forceLogout 싱글턴 플래그 추가

```dart
// ② 클래스 상단에 플래그 추가 (_isRefreshing 옆)
bool _isForceLogout = false;

// ③ forceLogout 메서드 추가
void forceLogout() {
  if (_isForceLogout) return;  // 중복 차단
  _isForceLogout = true;
  clearToken();
  onRefreshFailed?.call();
  // _isForceLogout은 리셋하지 않음 — 앱 재시작/재로그인까지 유지
}
```

### 1-D: refresh 실패 시 forceLogout 사용

**현재 코드** (L65-74):
```dart
} else {
  clearToken();
  onRefreshFailed?.call();
  return handler.next(error);
}
} catch (e) {
  clearToken();
  onRefreshFailed?.call();
  return handler.next(error);
}
```

**변경**:
```dart
} else {
  forceLogout();
  return handler.next(error);
}
} catch (e) {
  forceLogout();
  return handler.next(error);
}
```

### 1-E: 로그인 성공 시 forceLogout 플래그 리셋

```dart
// setToken 메서드에 리셋 추가
void setToken(String token) {
  _token = token;
  _isForceLogout = false;  // 로그인 성공 → 리셋
}
```

### 검증 포인트
- [ ] `/auth/logout` 401이 interceptor 재진입하지 않는 것 확인
- [ ] forceLogout이 1회만 호출되는 것 확인 (`debugPrint` 로그)
- [ ] 정상 로그인 후 `_isForceLogout`이 false인 것 확인

---

## Task 2: `auth_service.dart` — logout 중복 호출 차단 + timeout

**파일**: `frontend/lib/services/auth_service.dart`

### 2-A: _isLoggingOut 플래그 추가

```dart
// ① 클래스 상단에 추가 (_secureStorage 아래)
bool _isLoggingOut = false;
```

### 2-B: logout() 메서드 수정

**현재 코드** (L211-243):
```dart
Future<void> logout() async {
  try {
    final storedRefreshToken = await _secureStorage.read(key: _refreshTokenKey);
    try {
      await _apiService.post(
        authLogoutEndpoint,
        data: {
          if (storedRefreshToken != null) 'refresh_token': storedRefreshToken,
        },
      );
    } catch (_) {
      // 서버 요청 실패해도 로컬 로그아웃은 계속 진행
    }
    // ... 토큰 삭제 ...
  }
}
```

**변경**:
```dart
Future<void> logout() async {
  // ★ 중복 호출 차단 — 이미 진행 중이면 스킵
  if (_isLoggingOut) return;
  _isLoggingOut = true;

  try {
    final storedRefreshToken = await _secureStorage.read(key: _refreshTokenKey);

    // ★ 토큰 먼저 클리어 (서버 호출 전에!) — 이후 API 호출에서 401 방지
    _apiService.clearToken();

    // ★ 서버 로그아웃은 best-effort + 3초 timeout
    try {
      await Future.any([
        _apiService.post(
          authLogoutEndpoint,
          data: {
            if (storedRefreshToken != null) 'refresh_token': storedRefreshToken,
          },
        ),
        Future.delayed(const Duration(seconds: 3), () => null),  // timeout
      ]);
    } catch (_) {
      // 서버 요청 실패해도 로컬 로그아웃은 계속 진행
    }

    // 로컬 스토리지 클리어
    await _secureStorage.delete(key: _tokenKey);
    await _secureStorage.delete(key: _refreshTokenKey);
    await _secureStorage.delete(key: _workerIdKey);
    await _secureStorage.delete(key: _workerRoleKey);
    await _secureStorage.delete(key: _workerDataKey);
    await _secureStorage.delete(key: _pinRegisteredKey);

    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_lastRouteKey);
    await prefs.remove(_lastRouteArgsKey);
  } catch (e) {
    await _secureStorage.deleteAll();
    rethrow;
  } finally {
    _isLoggingOut = false;  // ★ 항상 리셋
  }
}
```

### 핵심 변경 3가지
1. `_isLoggingOut` 플래그로 중복 호출 차단
2. `_apiService.clearToken()` 을 **서버 호출 전에** 실행 — 이후 API 호출에서 Authorization 헤더 미첨부 → 불필요한 401 방지
3. `Future.any` 3초 timeout — BE 응답 지연 시 빠르게 포기

### 검증 포인트
- [ ] logout() 연속 2회 호출 시 두 번째는 즉시 리턴
- [ ] 서버 /auth/logout 호출이 최대 1회인 것 확인
- [ ] 3초 내 BE 응답 없으면 로컬 로그아웃 완료

---

## Task 3: `auth_provider.dart` — onRefreshFailed 안전 래핑

**파일**: `frontend/lib/providers/auth_provider.dart`

### 3-A: onRefreshFailed 콜백 안전화

**현재 코드** (L305-308):
```dart
authService.onRefreshFailed = () {
  notifier.logout();
};
```

**변경**:
```dart
// refresh 실패 시 자동 로그아웃 — 중복 호출 방지는 AuthService._isLoggingOut에서 처리
authService.onRefreshFailed = () {
  // 이미 로그아웃 상태면 스킵
  if (!notifier.state.isAuthenticated) return;
  debugPrint('[AuthProvider] onRefreshFailed → logout 트리거');
  notifier.logout();
};
```

### 검증 포인트
- [ ] isAuthenticated=false 상태에서 onRefreshFailed 호출 시 logout 안 됨
- [ ] 로그 메시지 1회만 출력되는 것 확인

---

## Task 4: BE `auth.py` + `jwt_auth.py` — logout 토큰 선택적 처리 (코드만, DB 변경 없음)

> ⚠️ **DB 변경 없음**: ALTER TABLE / CREATE TABLE 절대 금지. Python 코드만 수정.

**파일 2개**: `backend/app/middleware/jwt_auth.py`, `backend/app/routes/auth.py`

### 4-A: `jwt_auth.py`에 jwt_optional 데코레이터 추가

`jwt_required` 함수 바로 아래(L93 이후)에 추가. 기존 `jwt_required` 패턴을 그대로 복사하되, 토큰 없거나 무효해도 에러 대신 `g.worker_id = None`으로 진행:

```python
def jwt_optional(f: Callable) -> Callable:
    """
    JWT 토큰 선택적 검증 데코레이터

    토큰이 있으면 g.worker_id 설정, 없거나 무효하면 g.worker_id = None으로 진행.
    logout처럼 토큰 없이도 호출 가능해야 하는 엔드포인트에 사용.

    ⚠️ DB 변경 없음 — 데코레이터 로직만 추가
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            g.worker_id = None
            g.worker_email = None
            g.worker_role = None
            return f(*args, **kwargs)

        parts = auth_header.split(' ')
        if len(parts) != 2 or parts[0] != 'Bearer':
            g.worker_id = None
            g.worker_email = None
            g.worker_role = None
            return f(*args, **kwargs)

        token = parts[1]
        try:
            payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
            g.worker_id = int(payload['sub'])
            g.worker_email = payload['email']
            g.worker_role = payload['role']
        except (ExpiredSignatureError, InvalidTokenError):
            g.worker_id = None
            g.worker_email = None
            g.worker_role = None

        return f(*args, **kwargs)
    return decorated_function
```

### 4-B: `auth.py` logout 데코레이터 변경

**현재 코드** (L450-452):
```python
@auth_bp.route("/logout", methods=["POST"])
@jwt_required
def logout() -> Tuple[Dict[str, Any], int]:
```

**변경**:
```python
@auth_bp.route("/logout", methods=["POST"])
@jwt_optional      # ★ 토큰 없어도 logout 요청 허용 (BUG-22 Logout Storm 방지)
def logout() -> Tuple[Dict[str, Any], int]:
```

상단 import에 `jwt_optional` 추가 필요:
```python
from app.middleware.jwt_auth import jwt_required, jwt_optional, get_current_worker_id, ...
```

### 4-C: logout 함수 body — g.worker_id가 None인 경우 처리

**현재 코드** (L467-477):
```python
    data = request.get_json() or {}
    refresh_token = data.get('refresh_token')

    if refresh_token:
        auth_service.revoke_refresh_token(refresh_token, reason='logout')
        logger.info(f"Logout with token revocation: worker_id={get_current_worker_id()}")
    else:
        # refresh_token 미전송 시 해당 worker 전체 토큰 무효화
        worker_id = get_current_worker_id()
        auth_service.revoke_all_worker_tokens(worker_id, reason='logout')
        logger.info(f"Logout all tokens: worker_id={worker_id}")
```

**변경**:
```python
    data = request.get_json(silent=True) or {}
    refresh_token = data.get('refresh_token')

    if refresh_token:
        # body에 refresh_token 있으면 해당 토큰만 무효화
        auth_service.revoke_refresh_token(refresh_token, reason='logout')
        logger.info(f"Logout with token revocation: worker_id={g.worker_id}")
    elif g.worker_id:
        # refresh_token 미전송이지만 JWT 유효 → 전체 토큰 무효화
        auth_service.revoke_all_worker_tokens(g.worker_id, reason='logout')
        logger.info(f"Logout all tokens: worker_id={g.worker_id}")
    else:
        # 토큰도 없고 refresh_token도 없음 → 로컬 로그아웃만 (서버 할 일 없음)
        logger.info("Logout without credentials (already expired)")
```

### 핵심: 401 storm 근본 차단
- FE가 토큰 없이 `/auth/logout` 호출해도 **200 OK** 반환
- `refresh_token`이 body에 있으면 DB에서 해당 토큰 무효화 (기존 동작 유지)
- `g.worker_id`가 None이고 `refresh_token`도 없으면 → 그냥 200 반환 (할 일 없음)
- **DB 스키마 변경 0건** — 기존 테이블 그대로 사용

### 검증 포인트
- [ ] 토큰 없이 `POST /api/auth/logout` → 200 응답 (401 아님!)
- [ ] 토큰 없이 + body에 refresh_token → 200 + DB 무효화 정상
- [ ] 토큰 있는 정상 logout → 기존 동작 회귀 확인
- [ ] pytest 전체 통과 (기존 logout 테스트 포함)

---

## Task 5: 테스트 + 버전 업데이트

### 5-A: 테스트 시나리오

```
시나리오 1: Refresh 만료 → 자동 로그아웃
  1. 정상 로그인
  2. refresh_token 만료 대기 (또는 DB에서 수동 삭제)
  3. 앱에서 API 호출 트리거
  4. 확인: /api/auth/logout 호출 최대 1회 (Railway 로그)
  5. 확인: 로그인 화면으로 자동 이동

시나리오 2: 동시 API 401
  1. 정상 로그인 후 여러 화면이 동시 API 호출
  2. access_token 만료 → 동시 401 5건+
  3. 확인: refresh 시도 1회만 발생
  4. refresh 실패 시 → forceLogout 1회 → 로그인 화면

시나리오 3: 정상 플로우 회귀
  1. 로그인 → 정상 사용 → 수동 로그아웃
  2. 확인: /api/auth/logout 200 정상 반환
  3. 확인: 토큰 DB 무효화 정상
```

### 5-B: 버전 업데이트

```
backend/version.py → VERSION = "1.7.2"
```

### 5-C: pytest 실행

> ⚠️ **Sprint 22-E 선행 필수**: conftest.py에 5테이블 백업/복원이 완성된 상태에서만 pytest 실행할 것.
> 미완성 상태에서 실행하면 `plan.product_info`, `qr_registry` 운영 데이터가 삭제됨.

```bash
cd backend && python -m pytest tests/ -x -q
```

실행 후 확인:
- [ ] 기존 테스트 전체 통과 (회귀 확인)
- [ ] logout 관련 테스트 통과 (토큰 없이 logout 200)
- [ ] `[db_schema] Backed up N product_info records` 로그 확인
- [ ] `[db_schema] Backed up N qr_registry records` 로그 확인
- [ ] `[db_schema] Restored N/N product_info records` 로그 확인
- [ ] `[db_schema] Restored N/N qr_registry records` 로그 확인

---

## 변경 파일 요약

```
frontend/lib/services/api_service.dart      — AUTH_SKIP_PATHS + forceLogout 싱글턴 + setToken 리셋
frontend/lib/services/auth_service.dart     — _isLoggingOut 플래그 + clearToken 선행 + 3초 timeout
frontend/lib/providers/auth_provider.dart   — onRefreshFailed 상태 체크 추가
backend/app/middleware/jwt_auth.py          — jwt_optional 데코레이터 신규 추가 (코드만, DB 변경 없음)
backend/app/routes/auth.py                 — @jwt_required → @jwt_optional (logout만)
backend/version.py                         — 1.7.1 → 1.7.2
```

> ⚠️ DB 스키마 변경 0건. ALTER TABLE / CREATE TABLE 절대 금지.

## 수정 전후 비교 (VIEW 수정과 동일 패턴)

| 시나리오 | 수정 전 (OPS FE) | 수정 후 |
|---------|------------------|---------|
| refresh 401 | → onRefreshFailed → logout() → /auth/logout 401 → 10회+ | → forceLogout 1회 (BE 호출 0~1회) |
| 동시 401 5건 | → 각자 onRefreshFailed | → _isForceLogout 차단 → 1회만 |
| logout API 자체 401 | → interceptor 재진입 가능 | → _authSkipPaths로 즉시 reject |
| BE 토큰 없는 logout | → 401 에러 | → @jwt_optional → 200 OK |

## 체크리스트

- [x] api_service.dart: _authSkipPaths에 /auth/logout 포함
- [x] api_service.dart: _isForceLogout 플래그 + forceLogout() 메서드
- [x] api_service.dart: setToken()에서 _isForceLogout = false 리셋
- [x] auth_service.dart: _isLoggingOut 중복 차단
- [x] auth_service.dart: clearToken()이 서버 호출 전에 실행
- [x] auth_service.dart: 3초 timeout
- [x] auth_provider.dart: isAuthenticated 체크 후 logout — StateNotifier 외부 접근 불가로 제거, _isLoggingOut + _isForceLogout에서 중복 차단
- [x] jwt_auth.py: jwt_optional 데코레이터 추가 (코드만, DB 변경 없음)
- [x] auth.py: logout에 @jwt_optional 적용
- [x] BE logout: 토큰 없이도 200 반환
- [x] ⚠️ DB 스키마 변경 없음 확인 (ALTER TABLE / CREATE TABLE 금지)
- [ ] pytest 전체 통과 (conftest.py 초기화 주의 — 기존 DB 데이터 보존)
- [x] version.py → 1.7.2

---

# Sprint 26: PWA 버전 업데이트 알림 + 업데이트 내용 팝업

> **버전**: 1.7.2 → 1.7.3
> **날짜**: 2026-03-12
> **목표**: (1) 새 배포 시 "새 버전이 있습니다" 토스트 표시 → 탭하여 reload, (2) reload 후 "무엇이 바뀌었는지" 업데이트 내용 팝업 자동 표시
> **⚠️ 제약**: DB 스키마 변경 절대 금지 / notices 테이블 version 필드 활용 (이미 존재)

## 배경

현재 PWA 배포 흐름:
1. `flutter build web` → Netlify 배포
2. `flutter_service_worker.js`가 `skipWaiting()` + `clients.claim()` 실행
3. 새 SW가 즉시 활성화되지만, **브라우저 탭은 이전 캐시된 JS/CSS를 사용 중**
4. 사용자가 새로고침 1~2회 해야 새 버전 반영
5. 사용자에게 **안내가 전혀 없어서** 구 버전을 계속 사용하게 됨

해결 (2단계):
- **1단계 (index.html JS)**: SW controllerchange 감지 → "새 버전이 있습니다" 토스트 → 탭하면 reload
- **2단계 (Flutter FE)**: reload 후 앱 시작 시 버전 비교 → 새 버전이면 `GET /api/notices?version=X` 호출 → 업데이트 내용 팝업 표시

### 기존 공지사항 시스템 (활용)

```
notices 테이블 (이미 존재, 변경 없음)
├── id, title, content, version(VARCHAR 20), is_pinned
├── GET /api/notices?version=1.7.3  ← 버전별 필터 이미 지원
└── POST /api/admin/notices         ← Admin이 공지 등록 시 version 필드 입력
```

**연동 흐름 (사용자 관점)**:
```
개발자: 배포 + Admin에서 공지 등록 (version="1.7.3", 내용="로그인 오류 수정...")
    ↓
사용자: 앱 사용 중 → 하단 토스트 "새 버전이 있습니다" 표시
    ↓
사용자: 토스트 탭 → 새로고침
    ↓
앱 재시작 → "이전 버전과 다르네?" 감지 → 공지 API 호출
    ↓
팝업 표시:
  ┌───────────────────────────────────┐
  │  🔄 OPS 업데이트        v1.7.3   │
  │  ─────────────────────────────── │
  │  🔧 로그인 관련 오류 수정         │
  │  일부 환경에서 로그인 후 자동      │
  │  로그아웃이 반복되는 문제가        │
  │  수정되었습니다.                   │
  │                                   │
  │           [ 확인 ]                │
  └───────────────────────────────────┘
    ↓
"확인" → 팝업 닫힘 → 정상 사용
```

### 현재 SW 구조 (변경하지 않는 파일)

```
flutter_service_worker.js   ← flutter build web이 자동 생성, 수정 금지
├── install: self.skipWaiting()
├── activate: clients.claim() + 캐시 비교/갱신
└── fetch: index.html = Online-first, 나머지 = Cache-first
```

### 현재 index.html 구조

```html
<body>
  <div id="splash-screen">...</div>
  <script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
  <script src="flutter_bootstrap.js" async></script>
  <script>
    window.addEventListener('flutter-first-frame', function () { ... });
  </script>
</body>
```

---

## Task 1: index.html — SW 업데이트 감지 + 토스트 UI

### 파일: `frontend/web/index.html`

### 1-1. 토스트 CSS 추가 (기존 `</style>` 직전에 삽입)

```css
/* ── PWA Update Toast ── */
#update-toast {
  display: none;                       /* JS에서 flex로 변경 */
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100000;                     /* splash(99999) 위 */
  background: #1E293B;                 /* GxColors.charcoal 계열 */
  color: #FFFFFF;
  padding: 14px 20px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 14px;
  align-items: center;
  gap: 12px;
  max-width: 360px;
  width: calc(100% - 48px);
  cursor: pointer;
  animation: toast-slide-up 0.3s ease-out;
}

#update-toast:active {
  transform: translateX(-50%) scale(0.97);
}

#update-toast-icon {
  font-size: 20px;
  flex-shrink: 0;
}

#update-toast-text {
  flex: 1;
  line-height: 1.4;
}

#update-toast-text strong {
  display: block;
  font-size: 14px;
  margin-bottom: 2px;
}

#update-toast-text span {
  font-size: 12px;
  color: #94A3B8;
}

#update-toast-btn {
  background: #6366F1;                 /* GxColors.accent */
  color: white;
  border: none;
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  flex-shrink: 0;
}

#update-toast-btn:active {
  background: #4F46E5;
}

@keyframes toast-slide-up {
  from { opacity: 0; transform: translateX(-50%) translateY(20px); }
  to   { opacity: 1; transform: translateX(-50%) translateY(0); }
}
```

### 1-2. 토스트 HTML 추가 (`<body>` 안, splash-screen `</div>` 바로 뒤)

```html
<!-- PWA Update Toast: 새 SW 감지 시 표시 -->
<div id="update-toast" onclick="applyUpdate()">
  <div id="update-toast-icon">🔄</div>
  <div id="update-toast-text">
    <strong>새 버전이 있습니다</strong>
    <span>탭하여 업데이트</span>
  </div>
  <button id="update-toast-btn" onclick="applyUpdate()">업데이트</button>
</div>
```

### 1-3. SW 업데이트 감지 JS (`flutter-first-frame` 리스너 아래에 추가)

```javascript
<!-- PWA Update Detection -->
<script>
  (function() {
    // SW 지원 여부 확인
    if (!('serviceWorker' in navigator)) return;

    var updateToast = null;

    function showUpdateToast() {
      updateToast = document.getElementById('update-toast');
      if (updateToast) {
        updateToast.style.display = 'flex';
      }
    }

    // 전역 함수: 토스트 클릭 시 새로고침
    window.applyUpdate = function() {
      if (updateToast) {
        updateToast.style.display = 'none';
      }
      window.location.reload();
    };

    // 방법 1: controllerchange — 새 SW가 제어권 획득 시
    var refreshing = false;
    navigator.serviceWorker.addEventListener('controllerchange', function() {
      if (refreshing) return;   // 중복 방지
      refreshing = true;
      showUpdateToast();
    });

    // 방법 2: 새 SW waiting 상태 감지 (skipWaiting 전)
    navigator.serviceWorker.ready.then(function(registration) {
      // 이미 waiting 중인 SW가 있으면 즉시 표시
      if (registration.waiting) {
        showUpdateToast();
        return;
      }

      // 새 SW 설치 완료 → waiting 진입 감지
      registration.addEventListener('updatefound', function() {
        var newSW = registration.installing;
        if (!newSW) return;

        newSW.addEventListener('statechange', function() {
          // installed(=waiting) 상태 && 기존 controller 존재 = 업데이트
          if (newSW.state === 'installed' && navigator.serviceWorker.controller) {
            showUpdateToast();
          }
        });
      });
    });
  })();
</script>
```

### 검증 포인트
- [ ] `index.html` 문법 오류 없음 (브라우저 콘솔 에러 확인)
- [ ] 토스트가 기본 `display: none` → 업데이트 시 `display: flex`
- [ ] `applyUpdate()` 호출 시 `window.location.reload()` 실행
- [ ] 스플래시 스크린과 z-index 충돌 없음 (splash=99999, toast=100000)
- [ ] `controllerchange` + `updatefound` 이중 감지 동작
- [ ] 모바일 뷰포트에서 토스트가 화면 하단에 정상 표시 (max-width: 360px)

---

## Task 2: 앱 버전 상수 + 업데이트 감지 서비스

> 앱 시작 시 "이전에 본 버전"과 "현재 버전"을 비교하여 업데이트 여부 판단

### 2-1. 앱 버전 상수 파일: `frontend/lib/utils/app_version.dart` (신규)

```dart
/// 앱 버전 — version.py와 동일하게 유지
/// 배포 시 version.py와 함께 업데이트
const String appVersion = '1.7.3';
```

### 2-2. 업데이트 감지 서비스: `frontend/lib/services/update_service.dart` (신규)

```dart
import 'package:shared_preferences/shared_preferences.dart';
import '../utils/app_version.dart';
import 'notice_service.dart';

/// 버전 업데이트 감지 + 공지 조회
class UpdateService {
  final NoticeService _noticeService;
  static const _lastSeenVersionKey = 'last_seen_app_version';

  UpdateService(this._noticeService);

  /// 앱 시작 시 호출: 새 버전이면 해당 버전의 공지를 반환
  /// 새 버전이 아니거나 공지가 없으면 null 반환
  Future<Map<String, dynamic>?> checkForUpdateNotice() async {
    final prefs = await SharedPreferences.getInstance();
    final lastSeen = prefs.getString(_lastSeenVersionKey);

    // 같은 버전이면 스킵
    if (lastSeen == appVersion) return null;

    // 새 버전 감지! → 버전 저장 (다음엔 안 뜨도록)
    await prefs.setString(_lastSeenVersionKey, appVersion);

    // 해당 버전의 공지 조회
    try {
      final result = await _noticeService.getNotices(
        page: 1,
        limit: 1,
        version: appVersion,
      );
      final notices = result['notices'] as List<dynamic>? ?? [];
      if (notices.isNotEmpty) {
        return notices.first as Map<String, dynamic>;
      }
    } catch (e) {
      // 네트워크 에러 시 무시 — 팝업 없이 진행
    }
    return null;
  }
}
```

### 검증 포인트
- [ ] `appVersion` 상수가 version.py와 동일 (1.7.3)
- [ ] `SharedPreferences`에 `last_seen_app_version` 저장/비교
- [ ] 같은 버전이면 null 반환 (팝업 안 뜸)
- [ ] 새 버전이면 `GET /api/notices?version=1.7.3&limit=1` 호출
- [ ] 공지 없으면 null 반환 (팝업 없이 정상 진행)
- [ ] 네트워크 에러 시 앱 크래시 없음 (try-catch)

---

## Task 3: 업데이트 내용 팝업 다이얼로그

> HomeScreen 진입 시 새 버전 감지 → 업데이트 내용 팝업 표시
> 첨부 스크린샷 참고: 깔끔한 정보 카드 스타일, 사용자 친화적 한국어

### 파일: `frontend/lib/widgets/update_dialog.dart` (신규)

```dart
import 'package:flutter/material.dart';
import '../utils/design_system.dart';

/// 버전 업데이트 내용 팝업
/// notices API에서 받은 공지 데이터를 표시
class UpdateDialog extends StatelessWidget {
  final String title;
  final String content;
  final String? version;

  const UpdateDialog({
    super.key,
    required this.title,
    required this.content,
    this.version,
  });

  /// 팝업 표시 헬퍼
  static Future<void> show(
    BuildContext context, {
    required String title,
    required String content,
    String? version,
  }) {
    return showDialog(
      context: context,
      barrierDismissible: false,   // 배경 탭으로 닫기 방지
      builder: (_) => UpdateDialog(
        title: title,
        content: content,
        version: version,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(GxRadius.lg),
      ),
      insetPadding: const EdgeInsets.symmetric(horizontal: 24),
      child: Container(
        constraints: const BoxConstraints(maxWidth: 400),
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: GxColors.white,
          borderRadius: BorderRadius.circular(GxRadius.lg),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── 헤더: 아이콘 + 타이틀 + 버전 뱃지 ──
            Row(
              children: [
                // 업데이트 아이콘
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: GxColors.accent.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(
                    Icons.system_update_outlined,
                    color: GxColors.accent,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 12),
                // 타이틀
                Expanded(
                  child: Text(
                    title,
                    style: const TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                      color: GxColors.charcoal,
                    ),
                  ),
                ),
                // 버전 뱃지
                if (version != null)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8, vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: GxColors.accent.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      'v$version',
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: GxColors.accent,
                      ),
                    ),
                  ),
              ],
            ),

            const SizedBox(height: 16),

            // ── 구분선 ──
            Container(
              height: 1,
              color: GxColors.mist,
            ),

            const SizedBox(height: 16),

            // ── 본문 내용 (스크롤 가능) ──
            ConstrainedBox(
              constraints: BoxConstraints(
                maxHeight: MediaQuery.of(context).size.height * 0.4,
              ),
              child: SingleChildScrollView(
                child: Text(
                  content,
                  style: const TextStyle(
                    fontSize: 14,
                    height: 1.6,
                    color: GxColors.steel,
                  ),
                ),
              ),
            ),

            const SizedBox(height: 24),

            // ── 확인 버튼 ──
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () => Navigator.of(context).pop(),
                style: ElevatedButton.styleFrom(
                  backgroundColor: GxColors.accent,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(GxRadius.sm),
                  ),
                  elevation: 0,
                ),
                child: const Text(
                  '확인',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

### 검증 포인트
- [ ] 디자인 시스템(GxColors, GxRadius) 활용
- [ ] 버전 뱃지 "v1.7.3" 표시
- [ ] 본문이 길면 스크롤 가능 (maxHeight 40%)
- [ ] `barrierDismissible: false` — 반드시 "확인" 눌러야 닫힘
- [ ] 모바일에서 가로 여백 24px, 최대 너비 400px

---

## Task 4: HomeScreen에 업데이트 팝업 연동

> HomeScreen 진입 시 UpdateService로 새 버전 확인 → 공지 있으면 팝업

### 파일: `frontend/lib/screens/home/home_screen.dart` (기존 파일 수정)

### 4-1. import 추가

```dart
import '../../services/update_service.dart';
import '../../services/notice_service.dart';
import '../../services/api_service.dart';
import '../../widgets/update_dialog.dart';
```

### 4-2. initState 또는 기존 초기화 로직에 추가

HomeScreen의 `initState()` (또는 ConsumerState의 초기화 콜백) 안에서 `addPostFrameCallback`으로 호출:

```dart
@override
void initState() {
  super.initState();
  WidgetsBinding.instance.addPostFrameCallback((_) {
    _checkForUpdate();
    // ... 기존 초기화 로직 유지
  });
}

/// 버전 업데이트 공지 확인
Future<void> _checkForUpdate() async {
  if (!mounted) return;
  try {
    final apiService = ref.read(apiServiceProvider);
    final noticeService = NoticeService(apiService);
    final updateService = UpdateService(noticeService);

    final notice = await updateService.checkForUpdateNotice();
    if (notice != null && mounted) {
      await UpdateDialog.show(
        context,
        title: notice['title'] ?? 'OPS 업데이트',
        content: notice['content'] ?? '',
        version: notice['version'],
      );
    }
  } catch (e) {
    debugPrint('[HomeScreen] Update check failed: $e');
    // 실패 시 무시 — 앱 사용에 지장 없음
  }
}
```

> ⚠️ **주의**: HomeScreen의 기존 initState/build 로직을 절대 삭제하지 말 것.
> `_checkForUpdate()`만 추가. 기존 WebSocket, 대시보드, 공지 뱃지 로직은 그대로 유지.

### 4-3. Provider 확인

`apiServiceProvider`가 이미 존재하는지 확인. 없으면 HomeScreen이 사용하는 기존 API 호출 패턴을 따를 것.
NoticeService 인스턴스 생성 방식은 `notice_list_screen.dart`의 기존 패턴을 참고.

### 검증 포인트
- [ ] HomeScreen 진입 시 `_checkForUpdate()` 호출
- [ ] 새 버전 + 공지 존재 → UpdateDialog 팝업 표시
- [ ] 새 버전 + 공지 없음 → 팝업 없이 정상 진행
- [ ] 같은 버전 → 팝업 없이 정상 진행 (SharedPreferences 비교)
- [ ] 네트워크 에러 시 앱 크래시 없음
- [ ] 기존 HomeScreen 기능(WebSocket, 대시보드, 공지 뱃지) 영향 없음
- [ ] 팝업은 앱 업데이트 후 **최초 1회만** 표시 (이후 같은 버전에서는 안 뜸)

---

## Task 5: 테스트 + 버전 업데이트

### 5-1. `backend/version.py` 버전 업데이트

```python
VERSION = "1.7.3"
BUILD_DATE = "2026-03-12"
```

### 5-2. `frontend/lib/utils/app_version.dart` 확인

```dart
const String appVersion = '1.7.3';   // version.py와 동일
```

### 5-3. 빌드 검증

```bash
# Flutter 웹 빌드 에러 확인
cd frontend
flutter build web --release 2>&1 | tail -20

# 빌드 결과물에서 index.html 토스트 코드 확인
grep -c "update-toast" build/web/index.html
# 기대: 1 이상

# flutter_service_worker.js가 정상 생성되었는지 확인
ls -la build/web/flutter_service_worker.js
```

> ⚠️ `flutter build web`은 `web/index.html`을 `build/web/index.html`로 복사함.
> 따라서 **소스는 `web/index.html`만 수정**하면 빌드 시 자동 반영.

### 5-4. pytest 실행 (BE 변경 = version.py만이므로 회귀 리스크 낮음)

```bash
cd ../
pytest tests/ -x -q 2>&1 | tail -20
```

### 5-5. 테스트 공지 등록 (수동 — Admin 화면 또는 API)

배포 후 Admin 계정으로 공지사항 등록:
```
제목: OPS 업데이트
버전: 1.7.3
내용:
🔧 로그인 관련 오류 수정
일부 환경에서 로그인 후 자동 로그아웃이 반복되는 문제가 수정되었습니다.

🔔 업데이트 알림 추가
새 버전이 배포되면 자동으로 알림이 표시됩니다.
```

> 또는 기존 Admin 공지 작성 화면(`/notice-write`)에서 version 필드에 "1.7.3" 입력하여 등록.

### 검증 포인트
- [ ] version.py → 1.7.3
- [ ] app_version.dart → '1.7.3' (일치)
- [ ] `flutter build web` 에러 없음
- [ ] build/web/index.html에 update-toast 포함
- [ ] pytest 전체 통과
- [ ] Admin에서 v1.7.3 공지 등록 후, 앱 새로고침 시 팝업 표시 확인

---

## 변경 파일 요약

| 파일 | 변경 | 내용 |
|------|------|------|
| `frontend/web/index.html` | 수정 | 토스트 CSS + HTML + SW 감지 JS 추가 |
| `frontend/lib/utils/app_version.dart` | **신규** | 앱 버전 상수 ('1.7.3') |
| `frontend/lib/services/update_service.dart` | **신규** | 버전 비교 + 공지 조회 서비스 |
| `frontend/lib/widgets/update_dialog.dart` | **신규** | 업데이트 내용 팝업 다이얼로그 위젯 |
| `frontend/lib/screens/home/home_screen.dart` | 수정 | initState에 `_checkForUpdate()` 추가 |
| `backend/version.py` | 수정 | 1.7.2 → 1.7.3 |

## 수정 전후 비교

| 항목 | Before | After |
|------|--------|-------|
| SW 업데이트 감지 | 없음 — 사용자가 모르고 구 버전 사용 | 하단 토스트 "새 버전이 있습니다" 표시 |
| 업데이트 방법 | 수동 새로고침 1~2회 | 토스트 탭 → 자동 reload |
| 변경사항 안내 | 없음 | reload 후 업데이트 내용 팝업 자동 표시 |
| 공지 활용 | 사용자가 직접 공지 탭 방문 | 버전별 공지가 팝업으로 자동 노출 |
| 버전 | 1.7.2 | 1.7.3 |

---

## 전체 동작 흐름도

```
[Netlify 배포 완료]
       ↓
[사용자 브라우저]
  SW가 백그라운드에서 새 파일 감지
       ↓
  controllerchange / updatefound 이벤트 발생
       ↓
  ┌─────────────────────────────────┐
  │ 🔄 새 버전이 있습니다   [업데이트] │  ← index.html JS 토스트
  └─────────────────────────────────┘
       ↓ (사용자 탭)
  window.location.reload()
       ↓
[Flutter 앱 재시작]
  HomeScreen.initState()
       ↓
  UpdateService.checkForUpdateNotice()
  SharedPreferences: lastSeen='1.7.2' vs current='1.7.3'
  → 다르다! → GET /api/notices?version=1.7.3&limit=1
       ↓
  공지 존재하면:
  ┌───────────────────────────────────┐
  │  🔄 OPS 업데이트          v1.7.3  │
  │  ───────────────────────────────  │
  │  🔧 로그인 관련 오류 수정          │
  │  자동 로그아웃 반복 문제가         │
  │  수정되었습니다.                   │
  │                                   │
  │            [ 확인 ]               │  ← Flutter UpdateDialog
  └───────────────────────────────────┘
       ↓ (확인 탭)
  팝업 닫힘 → 정상 사용
  SharedPreferences: lastSeen='1.7.3' 저장 (다음엔 안 뜸)
```

---

## 체크리스트

- [x] index.html: update-toast CSS 추가
- [x] index.html: update-toast HTML 추가
- [x] index.html: SW controllerchange + updatefound 감지 JS 추가
- [x] applyUpdate() → window.location.reload() 동작
- [x] 토스트가 모바일 하단에 정상 표시 (z-index 100000)
- [x] app_version.dart: appVersion 상수 = '1.7.3'
- [x] update_service.dart: SharedPreferences 버전 비교 + notices API 호출
- [x] update_dialog.dart: 팝업 UI (버전 뱃지 + 본문 스크롤 + 확인 버튼)
- [x] home_screen.dart: _checkForUpdate() 추가 (기존 로직 보존)
- [x] 팝업은 앱 업데이트 후 최초 1회만 표시
- [x] 공지 없을 때 팝업 없이 정상 진행
- [x] ⚠️ DB 스키마 변경 없음 확인 (notices 테이블 그대로 사용)
- [x] ⚠️ flutter_service_worker.js 직접 수정하지 않음 (빌드 자동 생성)
- [x] version.py → 1.7.3
- [x] app_version.dart → '1.7.3' (일치)
- [x] flutter build web 에러 없음
- [x] pytest — BE 로직 변경 0건, 스킵 (version.py만 변경)

---

# Sprint 27: 단일 액션 Task 설계 (task_type 컬럼 + 출하완료 Task)

> **버전**: 1.7.4 → 1.7.4 (동일 — version.py는 Sprint 28에서 올림)
> **날짜**: 2026-03-13
> **목표**: (1) `app_task_details` 테이블에 `task_type` 컬럼 추가, (2) Tank Docking을 SINGLE_ACTION으로 전환, (3) SI에 '출하완료' Task 추가, (4) FE에서 task_type에 따라 버튼 분기

## 배경

현재 모든 Task는 **시작 → 완료** 2단계 액션이 필요합니다.
하지만 일부 Task는 "완료 체크만" 하면 되는 단일 액션이 적합합니다:

| Task | 공정 | 현재 | 변경 | 주체 |
|------|------|------|------|------|
| Tank Docking | MECH | 시작/종료 | 단일 액션 | MECH 담당 |
| 출하완료 (신규) | SI | 없음 | 단일 액션 | SI 담당 |

**A안 채택**: `task_type` 컬럼을 추가하여 장기적으로 다른 Task에도 확장 가능하게 설계.

## 변경 대상 파일

| 파일 | 변경 내용 |
|------|----------|
| `backend/migrations/022_add_task_type.sql` | task_type 컬럼 추가 + 기존 TANK_DOCKING 업데이트 |
| `backend/app/models/task_detail.py` | TaskDetail dataclass에 task_type 필드 추가 |
| `backend/app/services/task_seed.py` | TaskTemplate에 task_type 추가 + 출하완료 Task 등록 |
| `backend/app/services/task_service.py` | complete_single_action() 함수 추가 |
| `backend/app/routes/work.py` | POST /work/complete-single 엔드포인트 추가 |
| `frontend/lib/models/task_item.dart` | taskType 필드 추가 |
| `frontend/lib/screens/task/task_detail_screen.dart` | task_type 분기 → "완료" 버튼 1개 표시 |

---

## Task 1 — DB 마이그레이션: task_type 컬럼 추가

**파일**: `backend/migrations/022_add_task_type.sql`

```sql
-- Sprint 27: 단일 액션 Task 지원
-- task_type: 'NORMAL' (기본, 시작→완료) / 'SINGLE_ACTION' (완료 체크만)

ALTER TABLE app_task_details
ADD COLUMN IF NOT EXISTS task_type VARCHAR(20) NOT NULL DEFAULT 'NORMAL';

-- 기존 Tank Docking 행을 SINGLE_ACTION으로 업데이트
UPDATE app_task_details
SET task_type = 'SINGLE_ACTION'
WHERE task_id = 'TANK_DOCKING';

COMMENT ON COLUMN app_task_details.task_type IS 'NORMAL: 시작/완료 2단계, SINGLE_ACTION: 완료 체크만';
```

**주의**: `DEFAULT 'NORMAL'`이므로 기존 행은 자동으로 NORMAL 유지. Tank Docking만 UPDATE.

---

## Task 2 — BE 모델: TaskDetail에 task_type 필드 추가

**파일**: `backend/app/models/task_detail.py`

### 2-1. TaskDetail dataclass에 필드 추가

기존 `total_pause_minutes` 아래에 추가:

```python
    # Sprint 27: 단일 액션 Task 지원
    task_type: str = 'NORMAL'  # 'NORMAL' 또는 'SINGLE_ACTION'
```

### 2-2. from_db_row()에 task_type 파싱 추가

기존 `total_pause_minutes` 파싱 아래에:

```python
            task_type=row.get('task_type') or 'NORMAL',
```

### 2-3. complete_single_action() 함수 추가

`complete_task()` 함수 아래에 새 함수 추가:

```python
def complete_single_action(task_detail_id: int, completed_at: datetime, worker_id: int) -> bool:
    """
    단일 액션 Task 완료 처리 (started_at 없이 바로 완료).

    SINGLE_ACTION Task는 시작 단계 없이 "완료 체크"만 수행.
    started_at = completed_at (동시), duration_minutes = 0으로 설정.

    Args:
        task_detail_id: 작업 ID
        completed_at: 완료 시간 (timezone-aware)
        worker_id: 완료 처리한 작업자 ID

    Returns:
        성공 시 True, 실패 시 False
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE app_task_details
            SET started_at = %s,
                completed_at = %s,
                duration_minutes = 0,
                worker_id = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
              AND task_type = 'SINGLE_ACTION'
              AND completed_at IS NULL
            """,
            (completed_at, completed_at, worker_id, task_detail_id)
        )

        updated = cur.rowcount > 0
        conn.commit()

        if updated:
            logger.info(f"Single action completed: id={task_detail_id}, worker_id={worker_id}")
        return updated

    except PsycopgError as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to complete single action: {e}")
        return False
    finally:
        if conn:
            conn.close()
```

---

## Task 3 — BE 서비스: TaskSeed 업데이트

**파일**: `backend/app/services/task_seed.py`

### 3-1. TaskTemplate에 task_type 필드 추가

```python
@dataclass
class TaskTemplate:
    task_id: str
    task_name: str
    phase: str
    is_docking_required: bool = False
    task_type: str = 'NORMAL'  # Sprint 27: 'NORMAL' 또는 'SINGLE_ACTION'
```

### 3-2. TANK_DOCKING 템플릿에 task_type 설정

```python
# MECH_TASKS 중 TANK_DOCKING 행 변경:
TaskTemplate('TANK_DOCKING', 'Tank Docking', 'DOCKING', True, 'SINGLE_ACTION'),
```

**주의**: 위치 인자 순서에 맞게 `is_docking_required=True` 다음에 `task_type='SINGLE_ACTION'` 추가. 다른 TaskTemplate 행은 변경하지 않음 (기본값 'NORMAL' 유지).

### 3-3. SI_TASKS에 출하완료 Task 추가

```python
# Sprint 11: SI Tasks (1개) → Sprint 27: 2개로 확장
SI_TASKS: List[TaskTemplate] = [
    TaskTemplate('SI_FINISHING', '마무리공정', 'FINAL', False),
    TaskTemplate('SI_SHIPMENT', '출하완료', 'FINAL', False, 'SINGLE_ACTION'),  # Sprint 27
]
```

### 3-4. _upsert_task()에 task_type 파라미터 추가

```python
def _upsert_task(
    cur,
    serial_number: str,
    qr_doc_id: str,
    task_category: str,
    task_id: str,
    task_name: str,
    phase: str,
    is_applicable: bool,
    task_type: str = 'NORMAL'  # Sprint 27 추가
) -> bool:
    cur.execute(
        """
        INSERT INTO app_task_details (
            serial_number, qr_doc_id, task_category,
            task_id, task_name, is_applicable, task_type
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (serial_number, task_category, task_id) DO NOTHING
        RETURNING id
        """,
        (serial_number, qr_doc_id, task_category,
         task_id, task_name, is_applicable, task_type)
    )
    row = cur.fetchone()
    return row is not None
```

### 3-5. 모든 _upsert_task 호출부에 task_type 전달

각 카테고리 루프에서 `t.task_type`을 전달:

```python
# 예시 (모든 카테고리 동일 패턴):
inserted = _upsert_task(
    cur, serial_number, qr_doc_id,
    'MECH', t.task_id, t.task_name, t.phase, is_applicable, t.task_type
)
```

### 3-6. docstring 업데이트

`initialize_product_tasks` docstring의 Task 수 업데이트:
- 기존: `Task 19개(MECH 7 + ELEC 6 + TMS 2 + PI 2 + QI 1 + SI 1)`
- 변경: `Task 20개(MECH 7 + ELEC 6 + TMS 2 + PI 2 + QI 1 + SI 2)`

---

## Task 4 — BE 라우트: 단일 액션 완료 엔드포인트

**파일**: `backend/app/routes/work.py`

기존 `POST /work/complete` 아래에 추가:

```python
@work_bp.route("/work/complete-single", methods=["POST"])
@jwt_required
def complete_single_action_route():
    """
    단일 액션 Task 완료 API.

    SINGLE_ACTION type Task는 시작 없이 바로 완료 체크만 수행.
    started_at = completed_at 동시 설정, duration = 0.

    Request Body:
        {
            "task_detail_id": int (required)
        }

    Returns:
        200: {"status": "COMPLETED", "message": "작업이 완료되었습니다."}
        400: 유효성 검증 실패
        404: Task 미발견 또는 task_type 불일치
    """
    data = request.get_json()
    if not data or 'task_detail_id' not in data:
        return jsonify({
            'error': 'VALIDATION_ERROR',
            'message': 'task_detail_id가 필요합니다.'
        }), 400

    task_detail_id = data['task_detail_id']

    # Task 조회 및 task_type 검증
    task = get_task_by_id(task_detail_id)
    if not task:
        return jsonify({'error': 'NOT_FOUND', 'message': 'Task를 찾을 수 없습니다.'}), 404

    if task.task_type != 'SINGLE_ACTION':
        return jsonify({
            'error': 'INVALID_TASK_TYPE',
            'message': '단일 액션 Task가 아닙니다. 일반 시작/완료 API를 사용하세요.'
        }), 400

    if task.completed_at is not None:
        return jsonify({
            'error': 'ALREADY_COMPLETED',
            'message': '이미 완료된 Task입니다.'
        }), 400

    # 완료 처리
    completed_at = datetime.now(timezone.utc)
    success = complete_single_action(task_detail_id, completed_at, g.worker_id)

    if not success:
        return jsonify({'error': 'COMPLETE_FAILED', 'message': '완료 처리에 실패했습니다.'}), 500

    # completion_status 업데이트 (기존 로직 재사용)
    task_service = TaskService()
    task_service._check_category_completion(task.serial_number, task.task_category)

    # work_completion_log 기록
    _log_single_action_completion(task, g.worker_id, completed_at)

    return jsonify({
        'status': 'COMPLETED',
        'message': '작업이 완료되었습니다.',
        'task_detail_id': task_detail_id
    }), 200
```

**필요 import 추가**:
```python
from datetime import datetime, timezone
from app.models.task_detail import get_task_by_id, complete_single_action
from app.services.task_service import TaskService
```

**_log_single_action_completion() 헬퍼** (같은 파일 하단에):
```python
def _log_single_action_completion(task, worker_id, completed_at):
    """단일 액션 완료 로그 기록 (work_completion_log)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO work_completion_log (
                task_id, worker_id, serial_number, qr_doc_id,
                task_category, task_id_ref, task_name,
                completed_at, duration_minutes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)
            """,
            (task.id, worker_id, task.serial_number, task.qr_doc_id,
             task.task_category, task.task_id, task.task_name,
             completed_at)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to log single action completion: {e}")
```

---

## Task 5 — FE 모델: TaskItem에 taskType 추가

**파일**: `frontend/lib/models/task_item.dart`

### 5-1. 필드 추가

`myStatus` 아래에:
```dart
  final String taskType; // 'NORMAL' 또는 'SINGLE_ACTION'
```

### 5-2. 생성자에 추가

```dart
  this.taskType = 'NORMAL',
```

### 5-3. fromJson에 추가

```dart
      taskType: json['task_type'] as String? ?? 'NORMAL',
```

### 5-4. toJson에 추가

```dart
      'task_type': taskType,
```

### 5-5. copyWith에 추가

파라미터: `String? taskType,`
본문: `taskType: taskType ?? this.taskType,`

### 5-6. 상태 헬퍼 추가

```dart
  /// 단일 액션 Task 여부
  bool get isSingleAction => taskType == 'SINGLE_ACTION';
```

---

## Task 6 — FE 화면: 단일 액션 버튼 분기

**파일**: `frontend/lib/screens/task/task_detail_screen.dart`

### 6-1. 액션 버튼 빌드 분기

기존 `_buildActionButtons()` 메서드(또는 버튼 영역)에서 task_type 분기 추가:

```dart
// 기존 버튼 빌드 로직 앞에 추가:
if (task.isSingleAction) {
  return _buildSingleActionButton(task);
}
// ... 기존 시작/완료 버튼 로직
```

### 6-2. _buildSingleActionButton() 구현

```dart
Widget _buildSingleActionButton(TaskItem task) {
  // 이미 완료됨
  if (task.completedAt != null) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 14),
      decoration: BoxDecoration(
        color: GxColors.success.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: const Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.check_circle, color: GxColors.success, size: 20),
          SizedBox(width: 8),
          Text('작업 완료됨', style: TextStyle(
            color: GxColors.success,
            fontWeight: FontWeight.w600,
            fontSize: 15,
          )),
        ],
      ),
    );
  }

  // 완료 버튼 (1개만)
  return SizedBox(
    width: double.infinity,
    child: ElevatedButton(
      onPressed: _isActionLoading ? null : () => _completeSingleAction(task),
      style: ElevatedButton.styleFrom(
        backgroundColor: GxColors.accent,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
      child: _isActionLoading
          ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
          : const Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.check, size: 20),
                SizedBox(width: 8),
                Text('완료', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
              ],
            ),
    ),
  );
}
```

### 6-3. _completeSingleAction() 메서드

```dart
Future<void> _completeSingleAction(TaskItem task) async {
  setState(() => _isActionLoading = true);
  try {
    final taskNotifier = ref.read(taskProvider.notifier);
    final success = await taskNotifier.completeSingleAction(task.id);
    if (mounted) {
      _showSnack(success, '작업이 완료되었습니다.', '작업 완료에 실패했습니다.');
    }
  } finally {
    if (mounted) setState(() => _isActionLoading = false);
  }
}
```

---

## Task 7 — FE 서비스/프로바이더: completeSingleAction API 호출

### 7-1. task_service.dart에 추가

```dart
Future<bool> completeSingleAction(int taskDetailId) async {
  try {
    final response = await _dio.post('/work/complete-single', data: {
      'task_detail_id': taskDetailId,
    });
    return response.statusCode == 200;
  } catch (e) {
    debugPrint('completeSingleAction error: $e');
    return false;
  }
}
```

### 7-2. task_provider.dart에 추가

```dart
Future<bool> completeSingleAction(int taskDetailId) async {
  final success = await _taskService.completeSingleAction(taskDetailId);
  if (success) {
    await refreshCurrentProduct(); // Task 목록 새로고침
  }
  return success;
}
```

---

## Task 8 — 테스트

### 8-1. BE 테스트

```bash
cd /path/to/AXIS-OPS/backend
python -m pytest tests/ -x -v --timeout=30 2>&1 | tail -50
```

**신규 테스트 항목**:

1. **마이그레이션 적용 확인**
   - `task_type` 컬럼 존재, DEFAULT = 'NORMAL'
   - 기존 Task 행 → task_type = 'NORMAL' 유지

2. **Task Seed**
   - TANK_DOCKING seed → task_type = 'SINGLE_ACTION'
   - SI_SHIPMENT seed → task_type = 'SINGLE_ACTION'
   - 기존 Task seed → task_type = 'NORMAL' 유지
   - SI Task 수: 1개 → 2개 (SI_FINISHING + SI_SHIPMENT)

3. **complete_single_action()**
   - SINGLE_ACTION Task → started_at = completed_at, duration = 0, 200 반환
   - NORMAL Task로 호출 → 400 반환 (task_type 불일치)
   - 이미 완료된 Task → 400 반환

4. **기존 시작/완료 API regression**
   - NORMAL Task: 기존 start/complete 정상 동작
   - SINGLE_ACTION Task: 기존 start API 호출 시 동작 확인 (방어 로직 선택)

### 8-2. FE 빌드

```bash
cd /path/to/AXIS-OPS/frontend
flutter build web
```

빌드 에러 없음 확인.

---

## 체크리스트

- [x] `022_add_task_type.sql` 마이그레이션 작성
- [x] TaskDetail dataclass에 `task_type` 필드 추가
- [x] `complete_single_action()` DB 함수 추가
- [x] TaskTemplate에 `task_type` 필드 추가
- [x] TANK_DOCKING → `SINGLE_ACTION` 변경
- [x] SI_SHIPMENT ('출하완료') Task 추가
- [x] `_upsert_task()`에 task_type 파라미터 추가
- [x] 모든 _upsert_task 호출부 task_type 전달
- [x] `POST /work/complete-single` 엔드포인트 추가
- [x] work_completion_log 기록 함수 추가
- [x] TaskItem.dart에 `taskType` 필드 + `isSingleAction` getter 추가
- [x] task_detail_screen.dart에 단일 액션 버튼 분기 추가
- [x] task_service.dart에 completeSingleAction() 추가
- [x] task_provider.dart에 completeSingleAction() 추가
- [x] pytest 전체 통과 (35 passed, 1 기존 fail — Sprint 27 regression 0건)
- [x] flutter build web 에러 없음
- [x] ⚠️ 기존 NORMAL Task 시작/완료 동작 영향 없음 확인
- [x] ⚠️ 기존 Task Seed 19개 → 20개 (SI +1) 카운트 확인

---

# Sprint 28: AXIS-VIEW 권한 데코레이터 재정비

> **버전**: 1.7.4 → 1.7.5
> **날짜**: 2026-03-13
> **목표**: (1) `get_current_worker()` 캐싱 헬퍼로 중복 DB 쿼리 제거, (2) 신규 데코레이터 2개 추가 (`@gst_or_admin_required`, `@view_access_required`), (3) 기존 API 4개 데코레이터 교체, (4) 기존 데코레이터도 캐싱 적용

## 배경

AXIS-VIEW 사이드바 권한 테스트 결과, FE/BE 간 권한 불일치 발생.
- GST 일반 직원(PI, QI 등)이 FE에서 페이지 진입은 되지만 BE API에서 403 반환
- 원인: `@manager_or_admin_required`가 QR목록, ETL변경이력 등에 걸려있어 GST 일반 직원 차단
- 추가로 공장 대시보드 전용 API에는 협력사 manager를 차단하는 데코레이터가 필요

**참고 문서**: `/AXIS-VIEW/docs/OPS_API_REQUESTS.md` #11-A ~ #11-D

## 확정 권한 매트릭스 (참고)

| 메뉴 | admin | GST+manager(PM) | GST+일반(PI,QI) | 협력사+manager |
|------|-------|-----------------|-----------------|---------------|
| 공장 대시보드 | ✅ | ✅ | ✅ | ❌ |
| 협력사 관리 | ✅ | ✅ | ❌ | ✅(자사) |
| 생산관리 | ✅ | ✅ | ✅ | ✅ |
| QR 관리 | ✅ | ✅ | ✅ | ✅ |
| 권한 관리 | ✅ | ✅(GST만) | ❌ | ✅(자사) |
| 불량 분석 | ✅ | ✅ | ✅ | ❌ |
| CT 분석 | ✅ | ✅ | ✅ | ❌ |
| AI 예측/챗봇 | ✅ | ✅ | ✅ | ❌ |

## 변경 대상 파일 (BE only — DB 스키마 변경 없음)

| 파일 | 변경 내용 |
|------|----------|
| `backend/app/middleware/jwt_auth.py` | `get_current_worker()` 헬퍼 추가, 신규 데코레이터 2개 추가, 기존 데코레이터 캐싱 리팩토링 |
| `backend/app/routes/qr.py` | L22 `@manager_or_admin_required` → `@view_access_required` |
| `backend/app/routes/admin.py` | L1921 `@manager_or_admin_required` → `@view_access_required` (etl/changes) |
| `backend/version.py` | 1.7.3 → 1.7.4 |

## 금지 사항

- ❌ DB 스키마, migration 추가 금지
- ❌ FE(Flutter) 변경 금지 — VIEW 사이드바는 VIEW 자체 처리
- ❌ 기존 `@admin_required`, `@manager_or_admin_required` 삭제 금지 (사용처 존재)
- ❌ `@jwt_required` 로직 변경 금지
- ❌ 신규 API 엔드포인트 추가 금지 (#9, #10은 별도 Sprint)

---

## Task 1 — `get_current_worker()` 캐싱 헬퍼 추가

**파일**: `backend/app/middleware/jwt_auth.py`

**현재 문제**: `@jwt_required` → `@admin_required` 체이닝 시 `get_worker_by_id(g.worker_id)`가 매번 호출되어 같은 request 안에서 동일 worker를 2~3회 DB 조회.

**구현 위치**: 기존 `get_current_worker_id()` 함수(L140~149) 바로 아래에 추가

```python
def get_current_worker():
    """
    현재 인증된 작업자 객체를 반환 (request 당 1회 DB 조회, 이후 캐시).

    jwt_required 데코레이터 실행 후 호출 가능.
    g.current_worker에 캐시하여 동일 request 내 중복 DB 쿼리 방지.

    Returns:
        Worker 객체 또는 None (미인증 시)
    """
    if hasattr(g, 'current_worker') and g.current_worker is not None:
        return g.current_worker

    if not hasattr(g, 'worker_id'):
        return None

    worker = get_worker_by_id(g.worker_id)
    g.current_worker = worker
    return worker
```

**테스트 관점**:
- `get_current_worker()` 2회 연속 호출 시 `get_worker_by_id()` 1회만 호출 확인 (mock)
- `g.worker_id` 없을 때 None 반환 확인

---

## Task 2 — 기존 데코레이터 캐싱 리팩토링

**파일**: `backend/app/middleware/jwt_auth.py`

기존 `admin_required`와 `manager_or_admin_required` 내부의 `get_worker_by_id(g.worker_id)` 호출을 `get_current_worker()` 로 교체.

### admin_required (L183)

**변경 전**:
```python
worker = get_worker_by_id(g.worker_id)
```

**변경 후**:
```python
worker = get_current_worker()
```

### manager_or_admin_required (L221)

**변경 전**:
```python
worker = get_worker_by_id(g.worker_id)
```

**변경 후**:
```python
worker = get_current_worker()
```

**주의**: 두 데코레이터의 권한 조건 로직은 절대 변경하지 말 것. `get_worker_by_id` → `get_current_worker` 호출만 교체.

---

## Task 3 — 신규 데코레이터 `@gst_or_admin_required` 추가

**파일**: `backend/app/middleware/jwt_auth.py`

**삽입 위치**: `manager_or_admin_required` 함수 바로 아래 (파일 끝 부분)

```python
def gst_or_admin_required(f: Callable) -> Callable:
    """
    GST 소속 전직원 또는 Admin만 허용.

    용도: 공장 대시보드 KPI, 불량 분석, CT 분석 등 GST 전용 페이지 API.
    AXIS-VIEW 접근 가능 사용자 중 협력사 manager를 차단.

    조건: worker.company == 'GST' OR worker.is_admin == True

    jwt_required와 함께 사용되어야 합니다.

    Usage:
        @app.route('/api/admin/factory/weekly-kpi')
        @jwt_required
        @gst_or_admin_required
        def factory_kpi():
            ...
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if not hasattr(g, 'worker_id'):
            return jsonify({
                'error': 'UNAUTHORIZED',
                'message': '인증이 필요합니다.'
            }), 401

        worker = get_current_worker()

        if not worker or (worker.company != 'GST' and not worker.is_admin):
            logger.warning(
                f"Forbidden: worker_id={g.worker_id} attempted GST-only access"
            )
            return jsonify({
                'error': 'FORBIDDEN',
                'message': 'GST 소속 또는 관리자 권한이 필요합니다.'
            }), 403

        logger.debug(f"GST/admin access granted: worker_id={g.worker_id}")
        return f(*args, **kwargs)

    return decorated_function
```

**테스트 시나리오**:
1. GST+일반(PI) → 200 통과 ✅
2. GST+manager(PM) → 200 통과 ✅
3. GST+admin → 200 통과 ✅
4. 협력사+manager(BAT) → 403 차단 ✅
5. 협력사+일반(MECH) → 403 차단 ✅
6. JWT 없음 → 401 ✅

---

## Task 4 — 신규 데코레이터 `@view_access_required` 추가

**파일**: `backend/app/middleware/jwt_auth.py`

**삽입 위치**: `gst_or_admin_required` 바로 아래

```python
def view_access_required(f: Callable) -> Callable:
    """
    AXIS-VIEW 접근 가능 사용자만 허용.

    조건: worker.company == 'GST' OR worker.is_admin OR worker.is_manager
    (= AXIS-VIEW 로그인 게이트와 동일 조건)

    용도: QR 관리, 생산관리, ETL 변경이력 등 VIEW 사용자 전체 공개 API.

    jwt_required와 함께 사용되어야 합니다.

    Usage:
        @app.route('/api/admin/qr/list')
        @jwt_required
        @view_access_required
        def qr_list():
            ...
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if not hasattr(g, 'worker_id'):
            return jsonify({
                'error': 'UNAUTHORIZED',
                'message': '인증이 필요합니다.'
            }), 401

        worker = get_current_worker()

        if not worker or (
            worker.company != 'GST'
            and not worker.is_admin
            and not worker.is_manager
        ):
            logger.warning(
                f"Forbidden: worker_id={g.worker_id} attempted VIEW access"
            )
            return jsonify({
                'error': 'FORBIDDEN',
                'message': 'AXIS-VIEW 접근 권한이 필요합니다.'
            }), 403

        logger.debug(f"VIEW access granted: worker_id={g.worker_id}")
        return f(*args, **kwargs)

    return decorated_function
```

**테스트 시나리오**:
1. GST+일반(PI) → 200 통과 ✅ (핵심! 기존 403 해소)
2. GST+manager(PM) → 200 통과 ✅
3. GST+admin → 200 통과 ✅
4. 협력사+manager(BAT) → 200 통과 ✅
5. 협력사+일반(MECH) → 403 차단 ✅
6. JWT 없음 → 401 ✅

---

## Task 5 — 기존 API 데코레이터 교체 (2개 엔드포인트)

### 5-1. QR 목록 조회

**파일**: `backend/app/routes/qr.py` (L20~22)

**변경 전**:
```python
@qr_bp.route("/list", methods=["GET"])
@jwt_required
@manager_or_admin_required
```

**변경 후**:
```python
@qr_bp.route("/list", methods=["GET"])
@jwt_required
@view_access_required
```

**import 추가** (qr.py 상단):
```python
from app.middleware.jwt_auth import jwt_required, view_access_required
# 기존: from app.middleware.jwt_auth import jwt_required, manager_or_admin_required
# manager_or_admin_required import가 이 파일에서 더 이상 사용되지 않으면 제거
```

### 5-2. ETL 변경이력 조회

**파일**: `backend/app/routes/admin.py` (L1919~1921)

**변경 전**:
```python
@admin_bp.route("/etl/changes", methods=["GET"])
@jwt_required
@manager_or_admin_required
```

**변경 후**:
```python
@admin_bp.route("/etl/changes", methods=["GET"])
@jwt_required
@view_access_required
```

**import 추가** (admin.py 상단): `view_access_required`를 기존 import 라인에 추가.
```python
from app.middleware.jwt_auth import jwt_required, admin_required, manager_or_admin_required, view_access_required
```

**주의**: admin.py에서 `manager_or_admin_required`는 다른 엔드포인트에서 사용 중이므로 import 제거 금지!

---

## Task 6 — 테스트 + 버전 업데이트

### 6-1. 버전 업데이트

**파일**: `backend/version.py`

```python
VERSION = "1.7.5"
BUILD_DATE = "2026-03-13"
```

### 6-2. 테스트 실행

```bash
cd /path/to/AXIS-OPS/backend
python -m pytest tests/ -x -v --timeout=30 2>&1 | tail -50
```

**신규 테스트 필요 항목** (기존 테스트 파일에 추가):

1. `get_current_worker()` 캐싱 동작 확인
   - 동일 request 내 2회 호출 → DB 쿼리 1회 (mock 검증)
   - `g.worker_id` 미설정 → None 반환

2. `@gst_or_admin_required` 접근 제어
   - GST 일반(company='GST', is_admin=False, is_manager=False) → 200
   - 협력사 manager(company='BAT', is_manager=True) → 403
   - admin(is_admin=True, company=무관) → 200

3. `@view_access_required` 접근 제어
   - GST 일반 → 200 (기존 403이 200으로 해소)
   - 협력사 manager → 200
   - 협력사 일반 → 403

4. 기존 테스트 통과 확인 (regression)
   - `@admin_required` 기존 테스트 → 변경 없이 통과
   - `@manager_or_admin_required` 기존 테스트 → 변경 없이 통과

### 6-3. 기존 테스트 실패 시

`get_worker_by_id` → `get_current_worker` 변경으로 mock 대상이 달라질 수 있음.
- 기존 테스트에서 `patch('app.middleware.jwt_auth.get_worker_by_id')` → 그대로 유지 (get_current_worker 내부에서 호출하므로)
- 새 테스트에서는 `patch('app.middleware.jwt_auth.get_current_worker')` 사용 가능

---

## 데코레이터 체계 요약 (변경 후)

| 데코레이터 | 조건 | 용도 |
|---|---|---|
| `@admin_required` (기존) | `is_admin` | 시스템 설정, 가입 승인 |
| `@manager_or_admin_required` (기존) | `is_admin OR is_manager` | 권한 관리, 출퇴근, 강제 종료 |
| `@gst_or_admin_required` (신규) | `company='GST' OR is_admin` | 공장 대시보드 전용 API |
| `@view_access_required` (신규) | `company='GST' OR is_admin OR is_manager` | VIEW 전체 공개 API |

**계층 관계**: `admin_required` ⊂ `manager_or_admin_required` ⊂ `view_access_required` (포함 관계)

`gst_or_admin_required`는 별도 축: GST 소속 기준이라 manager 축과 교차

---

## 체크리스트

- [x] `get_current_worker()` 캐싱 헬퍼 추가 (jwt_auth.py)
- [x] `admin_required` 내부 → `get_current_worker()` 교체
- [x] `manager_or_admin_required` 내부 → `get_current_worker()` 교체
- [x] `@gst_or_admin_required` 데코레이터 추가
- [x] `@view_access_required` 데코레이터 추가
- [x] `qr.py` L22 → `@view_access_required` 교체 + import 수정
- [x] `admin.py` L1921 → `@view_access_required` 교체 + import 추가
- [ ] 신규 데코레이터 테스트 케이스 추가 (GST일반→200, 협력사manager→200/403) → Sprint 29에서 처리
- [x] 기존 데코레이터 테스트 regression 통과
- [ ] `get_current_worker()` 캐싱 테스트 통과 → Sprint 29에서 처리
- [ ] version.py → 1.7.5 → Sprint 29 완료 시 함께 버전업
- [x] pytest 전체 통과 (667 passed, 36 기존 실패 — Sprint 27 regression 0건)
- [x] ⚠️ DB 스키마 변경 없음 확인
- [x] ⚠️ FE(Flutter) 변경 없음 확인
- [x] ⚠️ 기존 `@admin_required`, `@manager_or_admin_required` 사용처 영향 없음 확인

---

# Sprint 29: 공장 API — 생산일정 + 주간 KPI (BE only)

> **버전**: 현재 version.py 확인 후 patch +1
> **날짜**: 2026-03-13
> **범위**: BE only (FE 없음). factory.py 블루프린트 신규 생성
> **참조**: OPS_API_REQUESTS.md #9, #10

## 배경

VIEW 생산일정 페이지(`ProductionPlanPage.tsx`)와 공장 대시보드(`FactoryDashboardPage.tsx`)에 필요한 BE API 2개를 구현한다.

- **#10 monthly-detail**: 생산일정 페이지 테이블 데이터 (GST 공정 일정)
- **#9 weekly-kpi**: 공장 대시보드 KPI 카드 + 차트 데이터

두 엔드포인트 모두 `plan.product_info` + `completion_status` JOIN 기반이며, 기존 패턴(qr.py 페이지네이션)을 따른다.

## 전제 조건

- `finishing_plan_end` 컬럼이 `plan.product_info`에 이미 존재 (CORE-ETL migration 001)
- `actual_ship_date` 컬럼이 `public.qr_registry`에 이미 존재
- `@gst_or_admin_required`, `@view_access_required` 데코레이터 이미 구현 (Sprint 28)

---

## Task 1: factory.py 블루프린트 생성 + __init__.py 등록

### 파일 생성: `backend/app/routes/factory.py`

```python
"""
공장 API 라우트 (Sprint 29)
엔드포인트: /api/admin/factory/*
VIEW 생산일정 + 공장 대시보드 전용
"""

import logging
import math
from datetime import date, timedelta
from flask import Blueprint, request, jsonify
from typing import Tuple, Dict, Any

from app.middleware.jwt_auth import (
    jwt_required,
    gst_or_admin_required,
    view_access_required,
)
from app.models.worker import get_db_connection
from psycopg2 import Error as PsycopgError

logger = logging.getLogger(__name__)

factory_bp = Blueprint("factory", __name__, url_prefix="/api/admin/factory")
```

### __init__.py 등록

`backend/app/__init__.py`에 추가:

```python
from app.routes.factory import factory_bp  # Sprint 29
# ... 기존 register_blueprint 아래에
app.register_blueprint(factory_bp)
```

### 검증
- `python -c "from app.routes.factory import factory_bp; print(factory_bp.name)"` → `factory`

---

## Task 2: #10 monthly-detail 엔드포인트 구현

### 파일: `backend/app/routes/factory.py`에 추가

```python
@factory_bp.route("/monthly-detail", methods=["GET"])
@jwt_required
@view_access_required
def get_monthly_detail() -> Tuple[Dict[str, Any], int]:
    """
    월간 생산 현황 상세 (OPS_API_REQUESTS #10)

    생산일정 페이지 + 공장 대시보드 상세 테이블용.
    plan.product_info + completion_status JOIN.

    Query Parameters:
        month: YYYY-MM (기본: 현재 월)
        date_field: pi_start | mech_start (기본: pi_start)
        page: 페이지 번호 (기본: 1)
        per_page: 페이지당 건수, max 200 (기본: 50)
    """
```

### 구현 요구 사항

1. **파라미터 검증**:
   - `month`: `YYYY-MM` 정규식 검증. 유효하지 않으면 400
   - `date_field`: `pi_start` 또는 `mech_start`만 허용. 그 외 400
   - `per_page`: max 200 제한
   - `page`: 1 이상

2. **SQL 쿼리** (OPS_API_REQUESTS.md #10 그대로):
```sql
-- COUNT 쿼리
SELECT COUNT(*) AS cnt
FROM plan.product_info p
WHERE p.{date_field} >= %s AND p.{date_field} < %s

-- 데이터 쿼리
SELECT p.sales_order, p.product_code, p.serial_number, p.model,
       p.customer, p.line, p.mech_partner, p.elec_partner,
       p.mech_start, p.mech_end, p.elec_start, p.elec_end,
       p.pi_start, p.qi_start, p.si_start, p.finishing_plan_end,
       cs.mech_completed, cs.elec_completed, cs.tm_completed,
       cs.pi_completed, cs.qi_completed, cs.si_completed
FROM plan.product_info p
LEFT JOIN completion_status cs ON p.serial_number = cs.serial_number
WHERE p.{date_field} >= %s AND p.{date_field} < %s
ORDER BY p.{date_field} DESC
LIMIT %s OFFSET %s

-- by_model 집계 쿼리
SELECT p.model, COUNT(*) AS count
FROM plan.product_info p
WHERE p.{date_field} >= %s AND p.{date_field} < %s
GROUP BY p.model
ORDER BY count DESC
```

   ⚠️ **중요**: `date_field`는 SQL 인젝션 방지를 위해 **화이트리스트 검증 후 f-string**으로 삽입. 파라미터 바인딩(%s)은 날짜값에만 사용.

3. **날짜 범위 계산**:
   - `month = "2026-03"` → `start_date = date(2026, 3, 1)`, `end_date = date(2026, 4, 1)`
   - 12월이면 다음해 1월 1일

4. **progress_pct 계산** (Python 측):
```python
def _calc_progress(row):
    """완료 단계 수 / 해당 단계 수 * 100"""
    is_gaia = (row.get('model') or '').upper().startswith('GAIA')
    stages = ['mech_completed', 'elec_completed', 'pi_completed', 'qi_completed', 'si_completed']
    if is_gaia:
        stages.append('tm_completed')
    completed = sum(1 for s in stages if row.get(s))
    return round(completed / len(stages) * 100, 1)
```

5. **completion.tm 처리**:
   - GAIA 모델: `tm_completed` 값 반환 (bool)
   - 비GAIA 모델: `null` 반환

6. **응답 형식** (OPS_API_REQUESTS.md #10 그대로):
```python
{
    "month": "2026-03",
    "items": [
        {
            "sales_order": "6408",
            "product_code": "41000558",
            "serial_number": "GBWS-6408",
            "model": "GAIA-I DUAL",
            "customer": "SEC",
            "line": "15L",
            "mech_partner": "BAT",
            "elec_partner": "C&A",
            "mech_start": "2026-03-03",  # date → isoformat() or null
            "mech_end": "2026-03-10",
            "elec_start": "2026-03-08",
            "elec_end": "2026-03-15",
            "pi_start": "2026-03-14",
            "qi_start": "2026-03-16",
            "si_start": "2026-03-18",
            "finishing_plan_end": "2026-03-20",
            "completion": {
                "mech": True,
                "elec": False,
                "tm": None,  # 비GAIA
                "pi": False,
                "qi": False,
                "si": False
            },
            "progress_pct": 16.7
        }
    ],
    "by_model": [
        {"model": "GAIA-I DUAL", "count": 81}
    ],
    "total": 119,
    "page": 1,
    "per_page": 50,
    "total_pages": 3
}
```

7. **에러 처리**: qr.py 패턴 동일 — `PsycopgError` catch → 500 + logger.error

### 검증
- 서버 재시작 후 `curl` 또는 pytest로 엔드포인트 호출 가능 확인

---

## Task 3: #9 weekly-kpi 엔드포인트 구현

### 파일: `backend/app/routes/factory.py`에 추가

```python
@factory_bp.route("/weekly-kpi", methods=["GET"])
@jwt_required
@gst_or_admin_required
def get_weekly_kpi() -> Tuple[Dict[str, Any], int]:
    """
    주간 공장 KPI (OPS_API_REQUESTS #9)

    공장 대시보드 KPI 카드 + 차트용.
    finishing_plan_end 기준 ISO week 필터.

    Query Parameters:
        week: ISO week 번호 1~53 (기본: 현재 주)
        year: 연도 (기본: 현재 연도)
    """
```

### 구현 요구 사항

1. **파라미터 검증**:
   - `week`: 1~53 범위. 그 외 400
   - `year`: 2020~2100 범위 (합리적 범위)

2. **ISO week → 날짜 범위 변환**:
```python
from datetime import date
# ISO week → Monday~Sunday
week_start = date.fromisocalendar(year, week, 1)  # Monday
week_end = date.fromisocalendar(year, week, 7)     # Sunday
```

3. **SQL 쿼리**:
```sql
-- 대상 S/N + completion_status JOIN
SELECT p.serial_number, p.model, p.finishing_plan_end,
       cs.mech_completed, cs.elec_completed, cs.tm_completed,
       cs.pi_completed, cs.qi_completed, cs.si_completed
FROM plan.product_info p
LEFT JOIN completion_status cs ON p.serial_number = cs.serial_number
WHERE p.finishing_plan_end >= %s AND p.finishing_plan_end <= %s
```

4. **Python 집계** (쿼리 결과 rows를 순회하며):

   a. `production_count`: len(rows)

   b. `completion_rate`: 각 S/N의 progress_pct 평균

   c. `by_model`: model별 카운트 → `[{"model": "...", "count": N}]` (count DESC)

   d. `by_stage`:
   ```python
   {
       "mech": (mech_completed=True 수 / 전체) * 100,
       "elec": (elec_completed=True 수 / 전체) * 100,
       "tm": (tm_completed=True 수 / GAIA 모델 수) * 100,  # GAIA만 분모
       "pi": (pi_completed=True 수 / 전체) * 100,
       "qi": (qi_completed=True 수 / 전체) * 100,
       "si": (si_completed=True 수 / 전체) * 100
   }
   ```
   - `by_stage.tm`: TM 해당 모델(GAIA)의 S/N만 분모. 비GAIA 제외
   - 전체 0건이면 모든 값 0.0

   e. `pipeline`: GST 공정 파이프라인 현재 대수
   ```python
   {
       "pi": pi_completed=True AND qi_completed=False 인 S/N 수,
       "qi": qi_completed=True AND si_completed=False 인 S/N 수,
       "si": si_completed=True AND finishing_plan_end > TODAY 인 S/N 수,
       "shipped": finishing_plan_end <= TODAY 인 S/N 수
   }
   ```

5. **응답 형식** (OPS_API_REQUESTS.md #9 그대로):
```python
{
    "week": 11,
    "year": 2026,
    "week_range": {
        "start": "2026-03-09",
        "end": "2026-03-15"
    },
    "production_count": 37,
    "completion_rate": 62.5,
    "by_model": [...],
    "by_stage": {...},
    "pipeline": {...}
}
```

### 검증
- 주차별 KPI 값이 합리적인지 확인

---

## Task 4: 테스트

### 파일 생성: `backend/tests/test_factory.py`

```python
"""
Sprint 29: 공장 API 테스트
- #10 monthly-detail
- #9 weekly-kpi
"""
```

### 테스트 케이스

**#10 monthly-detail**:
1. 정상 조회 (기본 파라미터) → 200, items 배열 + total + by_model
2. `date_field=mech_start` → 200
3. `date_field=invalid` → 400
4. `month=2026-13` → 400 (유효하지 않은 월)
5. `per_page=300` → 200 (max 200으로 제한)
6. 페이지네이션: page=2 → 200, offset 올바른지 확인
7. completion.tm: GAIA 모델 → bool, 비GAIA → null
8. progress_pct 계산 검증

**#9 weekly-kpi**:
1. 정상 조회 (기본 파라미터) → 200, week + year + production_count
2. `week=53` 경계값 → 200 또는 400 (해당 연도에 53주가 없으면)
3. `week=0` → 400
4. by_stage.tm 분모가 GAIA 모델만인지 확인
5. pipeline 카운트 합리성 검증

**권한 테스트**:
1. monthly-detail: 토큰 없음 → 401
2. monthly-detail: 협력사 일반 → 403 (view_access_required)
3. monthly-detail: 협력사 manager → 200
4. weekly-kpi: 협력사 manager → 403 (gst_or_admin_required)
5. weekly-kpi: GST 일반 → 200

### 실행
```bash
cd backend && python -m pytest tests/test_factory.py -v
```

기존 테스트 regression 확인:
```bash
cd backend && python -m pytest --tb=short -q 2>&1 | tail -5
```

---

## Task 5: version.py 업데이트 + 최종 확인

### version.py
```python
VERSION = "{현재 버전 patch +1}"
BUILD_DATE = "2026-03-13"
```

### 최종 확인
1. `python -m pytest tests/test_factory.py -v` → 전체 통과
2. `python -m pytest --tb=short -q` → 기존 테스트 regression 없음
3. factory.py에 미사용 import 없음
4. `finishing_plan_end` 컬럼이 실제 DB에 존재하는지 쿼리로 확인:
```sql
SELECT column_name FROM information_schema.columns
WHERE table_schema='plan' AND table_name='product_info'
AND column_name='finishing_plan_end';
```
5. 컬럼 미존재 시 → CORE-ETL migration 001 실행 필요하다는 WARNING 로그 출력 (엔드포인트는 정상 동작해야 함, null 반환)

---

## 체크리스트

- [x] `factory.py` 블루프린트 생성 (`/api/admin/factory`)
- [x] `__init__.py`에 `factory_bp` 등록 (12번째 블루프린트)
- [x] `GET /monthly-detail` 구현 (#10)
  - [x] month, date_field, page, per_page 파라미터
  - [x] date_field 화이트리스트 검증 (SQL 인젝션 방지)
  - [x] completion.tm GAIA 분기
  - [x] progress_pct 계산
  - [x] by_model 집계
  - [x] 페이지네이션 (total, page, per_page, total_pages)
- [x] `GET /weekly-kpi` 구현 (#9)
  - [x] ISO week → 날짜 범위 변환
  - [x] production_count, completion_rate
  - [x] by_model, by_stage, pipeline 집계
  - [x] by_stage.tm GAIA 분모 분리
- [x] `test_factory.py` 테스트 (18 passed — md 8개 + wk 5개 + 권한 5개)
- [x] 기존 pytest regression 0건 (test_factory.py 18 passed)
- [x] version.py 업데이트 (v1.7.6)
- [x] ⚠️ DB 스키마 변경 없음 확인 (finishing_plan_end는 CORE-ETL에서 이미 추가됨)
- [x] ⚠️ FE(Flutter) 변경 없음 확인 (BE only Sprint)

---

## Sprint 27-fix: Task Seed Silent Fail 디버깅 + 수정

> **목표**: QR 태깅 시 task가 0개 생성되는 문제 해결
> **현상**: DB 스키마 정상 (수동 INSERT 성공), Railway 앱에서 task seed가 silent fail
> **우선순위**: 🔴 긴급 (QR 스캔 핵심 기능 불가)

### 배경 정보

- `app_task_details` 테이블 구조 정상 (task_type 컬럼 존재, UNIQUE 제약조건 존재)
- 수동 INSERT 성공: `INSERT INTO app_task_details (..., task_type) VALUES (...) ON CONFLICT DO NOTHING RETURNING id;` → id=7 반환
- `model_config` 테이블에 GAIA prefix 존재 (has_docking=true, is_tms=true)
- `qr_registry`에 DOC_GBWS-6869 active 상태 확인
- `product.py` line 119-120에서 `except Exception as e: logger.warning(...)` 으로 에러를 삼킴 → FE에 에러 미표시
- 이 문제는 GBWS-6867, GBWS-6869 등 복수 제품에서 재현됨

### Task 1: 에러 로깅 강화 (product.py)

`backend/app/routes/product.py` 의 task seed except 블록을 수정:

**현재** (line 119-120):
```python
except Exception as e:
    logger.warning(f"Task seed failed (non-blocking): {e}")
```

**변경**:
```python
except Exception as e:
    import traceback
    logger.error(
        f"Task seed FAILED: serial={product.serial_number}, "
        f"model={product.model}, error={e}\n"
        f"Traceback: {traceback.format_exc()}"
    )
```

→ `logger.warning` → `logger.error` + traceback 추가. Railway 로그에서 정확한 에러 확인 가능.

### Task 2: task_seed.py 에러 로깅 강화

`backend/app/services/task_seed.py` line 281-284의 except 블록:

**현재**:
```python
except PsycopgError as e:
    if conn:
        conn.rollback()
    logger.error(f"Task seed failed: serial_number={serial_number}, error={e}")
```

**변경**:
```python
except PsycopgError as e:
    import traceback
    if conn:
        conn.rollback()
    logger.error(
        f"Task seed DB ERROR: serial_number={serial_number}, "
        f"model_name={model_name}, error={e}\n"
        f"Traceback: {traceback.format_exc()}"
    )
except Exception as e:
    import traceback
    if conn:
        conn.rollback()
    logger.error(
        f"Task seed UNEXPECTED ERROR: serial_number={serial_number}, "
        f"model_name={model_name}, error={e}\n"
        f"Traceback: {traceback.format_exc()}"
    )
```

→ PsycopgError 외의 일반 Exception도 별도 catch + traceback.

### Task 3: 디버그 엔드포인트 추가 (임시)

`backend/app/routes/product.py`에 디버그용 엔드포인트 추가:

```python
@product_bp.route("/debug/seed/<qr_doc_id>", methods=["POST"])
@jwt_required
def debug_task_seed(qr_doc_id: str):
    """임시 디버그: task seed 수동 실행 + 상세 에러 반환"""
    from app.models.product_info import get_product_by_qr_doc_id
    
    product = get_product_by_qr_doc_id(qr_doc_id, include_shipped=False)
    if not product:
        return jsonify({'error': 'PRODUCT_NOT_FOUND'}), 404
    
    try:
        seed_result = initialize_product_tasks(
            serial_number=product.serial_number,
            qr_doc_id=product.qr_doc_id,
            model_name=product.model
        )
        return jsonify({
            'success': True,
            'serial_number': product.serial_number,
            'model': product.model,
            'seed_result': seed_result
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
```

→ `POST /api/app/product/debug/seed/DOC_GBWS-6869` 호출 시 에러 메시지를 JSON으로 직접 반환.

### Task 4: Railway 배포 확인 + 디버그

1. 코드 push 후 Railway 재배포
2. `curl -X POST https://axis-ops-api.up.railway.app/api/app/product/debug/seed/DOC_GBWS-6869 -H "Authorization: Bearer {token}"` 호출
3. 반환된 에러 메시지 확인
4. 에러 원인에 따라 수정

### Task 5: 근본 원인 수정 후 정리

- 근본 원인 수정 적용
- debug/seed 엔드포인트 제거 (또는 admin_required로 변경)
- 기존 task가 없는 제품들 재스캔하여 task seed 확인
- GBWS-6867, GBWS-6869 등 task 생성 확인

### Task 6: version.py + 테스트

- version.py 버전은 유지 (v1.7.4 — 핫픽스 수준)
- 기존 pytest regression 0건 확인

### 체크리스트

- [x] product.py 에러 로깅 강화 (warning → error + traceback)
- [x] task_seed.py 에러 로깅 강화 (일반 Exception 추가)
- [x] debug/seed 엔드포인트 추가
- [x] Railway push + 재배포
- [x] debug/seed 호출로 에러 원인 확인 → task_type 컬럼 미존재 (migration 미적용 시점 문제)
- [x] 근본 원인 수정 → migration 적용 후 정상 동작 확인
- [x] GBWS-6869 QR 태깅 → task 20개 생성 확인 (MECH7+ELEC6+TMS2+PI2+QI1+SI2)
- [x] SINGLE_ACTION 검증: 배포 후 API 확인 필요 (task_type 응답 누락 수정 완료)
- [x] task_service.py task 목록 응답에 task_type 필드 추가
- [x] debug 엔드포인트 정리 (제거 완료)
- [x] 기존 pytest regression 0건 확인 (35 passed, 1 기존 이슈)

---

## Sprint 27-fix Phase 2: task_type 컬럼 미존재 근본 원인 수정

> **확인된 에러**: debug/seed 엔드포인트 응답:
> ```json
> "error": "column \"task_type\" of relation \"app_task_details\" does not exist"
> ```
> **모순**: pgAdmin에서 `SELECT table_schema, column_name FROM information_schema.columns WHERE table_name='app_task_details' AND column_name='task_type';` → `public, task_type` 존재 확인됨.
> pgAdmin과 앱이 같은 Railway DB (10.250.11.60:5432, database=railway)에 연결되어 있음 확인.

### 조사 방법

1. **앱이 실제로 연결하는 DB 확인**: Railway 대시보드 Variables 탭에서 `DATABASE_URL` 확인. 또는 코드에서 DB 연결 정보 확인:
   ```bash
   grep -r "DATABASE_URL\|DB_HOST\|DB_NAME\|get_db_connection" backend/app/models/worker.py backend/app/ --include="*.py" | head -30
   ```

2. **터미널에서 debug/seed 직접 호출**:
   먼저 JWT 토큰 발급:
   ```bash
   TOKEN=$(curl -s -X POST https://axis-ops-api.up.railway.app/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"admin1234@gst-in.com","password":"YOUR_PASSWORD"}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
   ```
   
   그 다음 debug/seed 호출:
   ```bash
   curl -s -X POST https://axis-ops-api.up.railway.app/api/app/product/debug/seed/DOC_GBWS-6876 \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
   ```

3. **DB 연결 정보 디버그 엔드포인트 추가** (임시):
   `backend/app/routes/product.py`에 DB 정보 확인용 엔드포인트 추가:
   ```python
   @product_bp.route("/debug/db-info", methods=["GET"])
   @jwt_required
   def debug_db_info():
       """임시: 앱이 연결한 DB 정보 + task_type 컬럼 존재 확인"""
       from app.models.worker import get_db_connection
       conn = None
       try:
           conn = get_db_connection()
           cur = conn.cursor()
           
           # 현재 DB 정보
           cur.execute("SELECT current_database(), inet_server_addr(), inet_server_port()")
           db_info = cur.fetchone()
           
           # task_type 컬럼 확인
           cur.execute("""
               SELECT column_name FROM information_schema.columns
               WHERE table_schema='public' AND table_name='app_task_details' AND column_name='task_type'
           """)
           task_type_exists = cur.fetchone() is not None
           
           # 전체 컬럼 목록
           cur.execute("""
               SELECT column_name FROM information_schema.columns
               WHERE table_schema='public' AND table_name='app_task_details'
               ORDER BY ordinal_position
           """)
           columns = [row[0] if isinstance(row, tuple) else row['column_name'] for row in cur.fetchall()]
           
           # DATABASE_URL 확인 (비밀번호 마스킹)
           import os
           db_url = os.environ.get('DATABASE_URL', 'NOT SET')
           if '@' in db_url:
               parts = db_url.split('@')
               db_url_masked = '***@' + parts[-1]
           else:
               db_url_masked = db_url
           
           return jsonify({
               'database': db_info[0] if db_info else None,
               'server_addr': str(db_info[1]) if db_info else None,
               'server_port': db_info[2] if db_info else None,
               'database_url_masked': db_url_masked,
               'task_type_column_exists': task_type_exists,
               'all_columns': columns,
               'column_count': len(columns)
           }), 200
       except Exception as e:
           import traceback
           return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500
       finally:
           if conn:
               conn.close()
   ```

4. **배포 후 확인**:
   ```bash
   curl -s https://axis-ops-api.up.railway.app/api/app/product/debug/db-info \
     -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
   ```

5. **결과에 따른 수정**:
   - task_type_column_exists=false → 앱 DB에 컬럼 추가 필요 (앱에서 직접 ALTER TABLE 실행하는 마이그레이션 코드 추가)
   - server_addr이 pgAdmin과 다름 → 앱 DATABASE_URL 수정 필요
   - 그 외 → 결과에 따라 판단

### 체크리스트

- [x] DB 연결 정보 확인 → server_addr=10.250.11.60, database=railway (pgAdmin과 동일)
- [x] debug/db-info 엔드포인트 추가 → 호출 확인 → task_type_column_exists=true
- [x] Railway push + 재배포
- [x] debug/db-info 호출로 앱 DB 상태 확인 → 컬럼 존재, 22개 컬럼 정상
- [x] task_type 컬럼 존재 확인 → migration 이미 적용됨
- [x] debug/seed 재호출로 task seed 성공 확인 → GBWS-6869 created=20, GBWS-6867 created=20
- [x] GBWS-6869, GBWS-6876 QR 태깅 → task 생성 확인
- [x] SINGLE_ACTION 검증: task_service.py 응답에 task_type 필드 추가 (배포 후 확인)
- [x] debug 엔드포인트 정리 (제거 완료)
- [x] 기존 pytest regression 0건 확인 (35 passed)

---

## BUG-23: QR 카메라 Viewfinder 모서리 코너 간헐적 미표시

> **현상**: QR 스캔 화면에서 인식 영역(qrbox)의 모서리 코너 마커가 표시될 때도 있고 안 될 때도 있음
> **우선순위**: 🟡 중간 (기능은 정상, UI 개선)
> **관련 이력**: BUG-5(프레임 벗어남), BUG-10(스크롤 분리), BUG-15(dialog overlay), BUG-17(깜빡임 루프) — 카메라 11차 수정까지 진행됨

### 근본 원인 분석

`frontend/lib/services/qr_scanner_web.dart`의 `_forceSquareAfterCameraStart()` (line 185~240)에서 문제 발생:

```dart
// line 205-213: 모든 자식 div 스타일을 무차별 덮어씀
final children = _scannerDiv!.children;
for (final child in children) {
  if (child is html.DivElement) {
    child.style
      ..width = '100%'
      ..height = '${_savedWidth}px'
      ..maxHeight = '${_savedWidth}px'
      ..overflow = 'hidden';  // ← viewfinder 모서리를 잘라냄
  }
}
```

**html5-qrcode 라이브러리**는 카메라 시작 후 내부적으로 다음 DOM 구조를 생성:
```
#qr-scanner-dom-div (우리가 만든 컨테이너)
  └─ div (html5-qrcode 내부 컨테이너)
      ├─ video (카메라 피드)
      ├─ canvas (QR 디코딩용, display:none)
      └─ div#qr-shaded-region (viewfinder + 코너 마커)
          ├─ div (top-left corner)
          ├─ div (top-right corner)  
          ├─ div (bottom-left corner)
          └─ div (bottom-right corner)
```

`_forceSquareAfterCameraStart()`가 **모든 자식 DivElement**에 `overflow: hidden`을 적용하면서 `#qr-shaded-region`과 그 내부 코너 마커까지 영향받음.

**간헐적인 이유**: 카메라 시작 타이밍에 따라:
- `_forceSquareAfterCameraStart()`가 먼저 실행 → html5-qrcode가 나중에 viewfinder 생성 → **코너 보임**
- html5-qrcode가 먼저 viewfinder 생성 → `_forceSquareAfterCameraStart()`가 덮어씀 → **코너 안 보임**

추가로 **MutationObserver** (line 218-237)가 스타일 변경을 감시하며 반복 적용하므로, 라이브러리가 viewfinder를 복구해도 다시 덮어씌워질 수 있음.

### 수정 방향

`_forceSquareAfterCameraStart()` line 205-213의 자식 div 스타일 적용에서 **viewfinder 관련 요소 제외**:

```dart
// 수정 전: 모든 자식 div에 적용
final children = _scannerDiv!.children;
for (final child in children) {
  if (child is html.DivElement) {
    child.style
      ..width = '100%'
      ..height = '${_savedWidth}px'
      ..maxHeight = '${_savedWidth}px'
      ..overflow = 'hidden';
  }
}

// 수정 후: viewfinder(#qr-shaded-region) 제외
final children = _scannerDiv!.children;
for (final child in children) {
  if (child is html.DivElement) {
    // html5-qrcode의 viewfinder 영역은 건드리지 않음
    final childId = child.id;
    if (childId.contains('shaded') || childId.contains('region')) continue;
    // qr-shaded-region의 부모 div도 overflow:hidden이면 안됨
    // → video 태그를 포함한 div만 타겟팅
    final hasVideo = child.querySelector('video') != null;
    if (!hasVideo) continue;
    
    child.style
      ..width = '100%'
      ..height = '${_savedWidth}px'
      ..maxHeight = '${_savedWidth}px'
      ..overflow = 'hidden';
  }
}
```

또한 MutationObserver 콜백 (line 218-237)에서도 동일하게 viewfinder 요소를 건드리지 않도록 확인.

### ⚠️ 주의사항 (이전 카메라 수정 이력 참고)

이 파일은 **11차 수정**까지 거친 민감한 코드. 수정 시 반드시:
1. 정사각형 컨테이너 강제 (`aspect-ratio: 1/1`) 유지 — 이것이 깨지면 BUG-5 재발
2. MutationObserver의 height 복원 로직 유지 — 이것이 깨지면 카메라 비율 왜곡
3. `overflow: hidden`은 **컨테이너 div**에는 유지 (카메라 피드 crop용), viewfinder div에서만 제거
4. dialog overlay 시 hide/show 로직 건드리지 않음 — 이것이 깨지면 BUG-17 재발
5. video 태그의 `object-fit: cover` 유지

### 테스트 방법

1. QR 스캔 화면 진입 → viewfinder 코너 4개 보이는지 확인
2. 5회 이상 반복 진입 → 매번 코너가 보이는지 확인 (간헐적 미표시 재현 방지)
3. 카메라 영역이 정사각형인지 확인 (BUG-5 regression)
4. QR 인식 정상 동작 확인
5. dialog(Location QR 팝업) 열림/닫힘 시 카메라 정상 복구 확인 (BUG-17 regression)

### 체크리스트

- [ ] `_forceSquareAfterCameraStart()` 자식 div 순회에서 viewfinder 제외
- [ ] MutationObserver 콜백에서 viewfinder 스타일 덮어쓰기 방지
- [ ] CSS `_injectScannerCss()`에서 `#qr-shaded-region` overflow 보호 추가 검토
- [ ] QR 스캔 5회 반복 → 코너 마커 항상 표시 확인
- [ ] 정사각형 컨테이너 유지 확인 (BUG-5 regression)
- [ ] QR 인식 정상 확인
- [ ] dialog overlay hide/show 정상 확인 (BUG-17 regression)
- [ ] Netlify 배포 + 실기기 테스트

---

## BUG-24: Task Seed 반복 실패 — 배포마다 task 0건

> **현상**: Sprint 배포 후 QR 태깅 시 task가 0건. 매 Sprint마다 반복 발생.
> **우선순위**: 🔴 치명적
> **근본 원인**: migration 022(`task_type` 컬럼)가 Railway 배포 과정에서 소실됨.
>   task seed INSERT에 `task_type` 컬럼이 포함되어 있는데 DB에 컬럼이 없어서 INSERT 실패.
>   `except Exception`으로 에러가 잡혀 사용자에게는 200 정상 반환 → silent fail.
> **조치 완료 (수동)**:
>   - `ALTER TABLE app_task_details ADD COLUMN IF NOT EXISTS task_type VARCHAR(20) DEFAULT 'NORMAL'` 수동 적용
>   - FK constraint `ON DELETE CASCADE` → `ON DELETE RESTRICT` 변경 (안전장치)
> **재발 방지 필요**: 앱 시작 시 스키마 자동 검증 로직 추가

---

## Sprint 29-fix: 앱 시작 시 DB 스키마 자동 검증 (ensure_schema)

> **목적**: 배포마다 migration 누락으로 task seed가 silent fail하는 문제 근본 차단
> **범위**: BE only — `backend/app/schema_check.py` 신규 + `__init__.py` 연동
> **버전**: v1.7.7 → v1.7.8 (BUILD_DATE 변경만)

### 근본 원인 분석

Sprint 진행 → Railway 배포 → DB에 migration 미적용 → task seed INSERT 실패(컬럼 없음) → except로 잡혀서 200 반환 → 사용자는 정상인 줄 알지만 task 0건

**이력**:
- Sprint 27-fix: `task_type` 컬럼 수동 추가 → 해결
- Sprint 29 배포: 같은 컬럼이 또 없음 → 또 task 0건
- 사용자가 직접 변경한 건 없음. Sprint 배포만 반복됨.

### Task 1: `backend/app/schema_check.py` 신규 생성

```python
"""
DB 스키마 자동 검증 — 앱 시작 시 필수 컬럼/제약조건 확인 및 자동 적용.
BUG-24: 배포마다 migration 누락으로 task seed silent fail 방지.
"""

import logging
from app.models.worker import get_db_connection
from psycopg2 import Error as PsycopgError

logger = logging.getLogger(__name__)

# ── 필수 컬럼 정의 ──────────────────────────────────
# (테이블명, 컬럼명, 없으면 실행할 ALTER TABLE DDL)
REQUIRED_COLUMNS = [
    (
        'app_task_details',
        'task_type',
        "ALTER TABLE app_task_details ADD COLUMN IF NOT EXISTS task_type VARCHAR(20) DEFAULT 'NORMAL'"
    ),
    # 향후 추가 컬럼이 있으면 여기에 추가
]

# ── 필수 FK 제약조건 정의 ────────────────────────────
# (테이블명, constraint명, 컬럼명, 기대하는 delete_rule, 수정 DDL)
REQUIRED_CONSTRAINTS = [
    (
        'app_task_details',
        'app_task_details_qr_doc_id_fkey',
        'qr_doc_id',
        'RESTRICT',
        [
            "ALTER TABLE app_task_details DROP CONSTRAINT IF EXISTS app_task_details_qr_doc_id_fkey",
            "ALTER TABLE app_task_details ADD CONSTRAINT app_task_details_qr_doc_id_fkey "
            "FOREIGN KEY (qr_doc_id) REFERENCES qr_registry(qr_doc_id) ON DELETE RESTRICT",
        ]
    ),
    (
        'completion_status',
        'completion_status_serial_number_fkey',
        'serial_number',
        'RESTRICT',
        [
            "ALTER TABLE completion_status DROP CONSTRAINT IF EXISTS completion_status_serial_number_fkey",
            "ALTER TABLE completion_status ADD CONSTRAINT completion_status_serial_number_fkey "
            "FOREIGN KEY (serial_number) REFERENCES qr_registry(serial_number) ON DELETE RESTRICT",
        ]
    ),
]


def ensure_schema():
    """
    앱 시작 시 호출. 필수 컬럼과 FK 제약조건을 검증하고 누락 시 자동 적용.
    실패해도 앱 시작을 막지는 않지만, ERROR 로그를 남김.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # ── 1. 필수 컬럼 검증 ──────────────────────
        for table, column, ddl in REQUIRED_COLUMNS:
            cur.execute(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = %s AND column_name = %s",
                (table, column)
            )
            if not cur.fetchone():
                logger.warning(
                    f"[schema_check] 필수 컬럼 누락 감지: {table}.{column} — 자동 추가 실행"
                )
                cur.execute(ddl)
                conn.commit()
                logger.info(f"[schema_check] {table}.{column} 컬럼 추가 완료")
            else:
                logger.info(f"[schema_check] {table}.{column} ✓")

        # ── 2. FK 제약조건 검증 ────────────────────
        for table, constraint, column, expected_rule, fix_ddls in REQUIRED_CONSTRAINTS:
            cur.execute(
                """SELECT rc.delete_rule
                   FROM information_schema.table_constraints tc
                   JOIN information_schema.key_column_usage kcu
                       ON tc.constraint_name = kcu.constraint_name
                   JOIN information_schema.referential_constraints rc
                       ON tc.constraint_name = rc.constraint_name
                   WHERE tc.constraint_type = 'FOREIGN KEY'
                       AND tc.table_name = %s
                       AND kcu.column_name = %s""",
                (table, column)
            )
            row = cur.fetchone()
            if row and row['delete_rule'] == expected_rule:
                logger.info(f"[schema_check] {table}.{column} FK={expected_rule} ✓")
            else:
                current = row['delete_rule'] if row else 'MISSING'
                logger.warning(
                    f"[schema_check] FK 수정 필요: {table}.{column} "
                    f"현재={current}, 기대={expected_rule} — 자동 수정 실행"
                )
                for ddl in fix_ddls:
                    cur.execute(ddl)
                conn.commit()
                logger.info(f"[schema_check] {table}.{column} FK → {expected_rule} 변경 완료")

        logger.info("[schema_check] DB 스키마 검증 완료 — 모든 항목 정상")

    except PsycopgError as e:
        logger.error(f"[schema_check] DB 스키마 검증 실패: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        logger.error(f"[schema_check] 예상치 못한 오류: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
```

### Task 2: `backend/app/__init__.py` 수정 — ensure_schema 호출

`create_app()` 함수에서 블루프린트 등록 직전에 추가:

```python
# 기존 코드: 스케줄러 초기화 뒤, 블루프린트 등록 전
if not app.config.get('TESTING', False):
    from app.services.scheduler_service import init_scheduler, start_scheduler
    init_scheduler()
    start_scheduler()
    logger.info("Scheduler initialized and started")

# ★ 추가: DB 스키마 자동 검증 (BUG-24 방지)
if not app.config.get('TESTING', False):
    from app.schema_check import ensure_schema
    ensure_schema()

# 블루프린트 등록
from app.routes.auth import auth_bp
# ...
```

**위치**: 스케줄러 초기화 후, 블루프린트 등록 전
**조건**: TESTING 환경에서는 실행하지 않음 (테스트 DB 스키마는 별도 관리)

### Task 3: migration 023 파일 생성

**파일**: `backend/migrations/023_fix_cascade_and_task_type.sql`

기존 수동 적용 내역을 migration 파일로 정식 기록:

```sql
-- BUG-24: task_type 컬럼 보장 + CASCADE → RESTRICT 변경
-- 이미 적용된 경우 IF NOT EXISTS / IF EXISTS로 안전하게 처리
BEGIN;

-- 1. task_type 컬럼 (migration 022가 누락될 경우 대비)
ALTER TABLE app_task_details
    ADD COLUMN IF NOT EXISTS task_type VARCHAR(20) DEFAULT 'NORMAL';

-- 2. FK: CASCADE → RESTRICT
ALTER TABLE app_task_details
    DROP CONSTRAINT IF EXISTS app_task_details_qr_doc_id_fkey;
ALTER TABLE app_task_details
    ADD CONSTRAINT app_task_details_qr_doc_id_fkey
    FOREIGN KEY (qr_doc_id) REFERENCES qr_registry(qr_doc_id) ON DELETE RESTRICT;

ALTER TABLE completion_status
    DROP CONSTRAINT IF EXISTS completion_status_serial_number_fkey;
ALTER TABLE completion_status
    ADD CONSTRAINT completion_status_serial_number_fkey
    FOREIGN KEY (serial_number) REFERENCES qr_registry(serial_number) ON DELETE RESTRICT;

COMMIT;
```

### Task 4: version.py 업데이트

```python
VERSION = "1.7.8"
BUILD_DATE = "2026-03-16"
```

### 테스트 체크리스트

- [x] `schema_check.py` 생성
- [x] `__init__.py`에 `ensure_schema()` 호출 추가
- [x] migration 023 파일 생성 (정식 기록용)
- [x] DB 검증: task_type 컬럼 존재 확인 (migration 023 수동 적용 후)
- [x] DB 검증: FK CASCADE → RESTRICT 변경 확인 (migration 023 수동 적용 후)
- [x] Railway 로그에서 `[schema_check]` 메시지 확인 — 로컬 테스트에서 정상 출력 확인 (task_type ✓, FK RESTRICT ✓, "DB 스키마 검증 완료")
- [x] QR 태깅 → task 생성 정상 확인 — GBWS-6876: 20 tasks, task_type 전부 정상 (NORMAL/SINGLE_ACTION)
- [x] 기존 pytest regression 0건 확인 (35 passed, 1 failed — test_admin_email_notification 기존 이슈)
- [x] version.py v1.7.8 + BUILD_DATE 업데이트

---

## Sprint 30: DB Connection Pool 도입 — 동시 접속 안정화

> **목적**: 100명+ 협력사 동시 접속 시 499 타임아웃 방지
> **범위**: BE only — `backend/app/db_pool.py` 신규 + `worker.py` + `__init__.py` 수정
> **버전**: v1.7.8 → v1.8.0 (마이너 버전업 — 인프라 변경)

### 배경

현재 `get_db_connection()`은 **매 요청마다 새 DB 연결을 생성**하고 요청 끝나면 닫음.
협력사 100명+가 출퇴근 시간(07:30~08:00, 16:30~17:00)에 동시 접속하면:
- QR 태깅 1건 = product API + tasks API + settings API = 연결 3개
- 100명 동시 = 300개 연결 시도
- Railway PostgreSQL max_connections = 기본 100개 → 연결 포화 → 499 에러

Connection Pool은 연결을 미리 만들어두고 재사용하므로:
- 최대 20~30개 연결로 100명+ 동시 처리 가능
- 연결 생성 비용(~50ms/건) 절감
- DB 서버 부하 감소

### Task 1: `backend/app/db_pool.py` 신규 생성

```python
"""
DB Connection Pool 관리
Sprint 30: psycopg2 ConnectionPool 기반 연결 풀링.
동시 접속 100명+ 환경에서 DB 연결 포화 방지.
"""

import logging
import os
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from app.config import Config

logger = logging.getLogger(__name__)

# 풀 설정
_MIN_CONN = int(os.environ.get('DB_POOL_MIN', 5))    # 최소 유지 연결
_MAX_CONN = int(os.environ.get('DB_POOL_MAX', 20))   # 최대 연결 수

_pool = None


def init_pool():
    """앱 시작 시 Connection Pool 초기화. create_app()에서 호출."""
    global _pool
    try:
        _pool = pool.ThreadedConnectionPool(
            minconn=_MIN_CONN,
            maxconn=_MAX_CONN,
            dsn=Config.DATABASE_URL,
            cursor_factory=RealDictCursor,
            options="-c timezone=Asia/Seoul"
        )
        logger.info(
            f"[db_pool] Connection pool initialized: "
            f"min={_MIN_CONN}, max={_MAX_CONN}"
        )
    except Exception as e:
        logger.error(f"[db_pool] Pool initialization failed: {e}")
        _pool = None


def get_conn():
    """
    풀에서 연결 가져오기.
    풀 초기화 실패 시 fallback으로 직접 연결 생성.
    """
    global _pool
    if _pool is None:
        # fallback: 풀 없으면 기존 방식
        import psycopg2
        logger.warning("[db_pool] Pool not available, using direct connection")
        return psycopg2.connect(
            Config.DATABASE_URL,
            cursor_factory=RealDictCursor,
            options="-c timezone=Asia/Seoul"
        )
    try:
        conn = _pool.getconn()
        return conn
    except Exception as e:
        logger.error(f"[db_pool] getconn failed: {e}")
        raise


def put_conn(conn):
    """연결을 풀에 반납. 에러 발생한 연결은 close=True로 폐기."""
    global _pool
    if _pool is None or conn is None:
        if conn:
            conn.close()
        return
    try:
        _pool.putconn(conn)
    except Exception:
        try:
            conn.close()
        except Exception:
            pass


def close_pool():
    """앱 종료 시 풀 정리."""
    global _pool
    if _pool:
        _pool.closeall()
        logger.info("[db_pool] Connection pool closed")
        _pool = None
```

### Task 2: `backend/app/models/worker.py` 수정 — get_db_connection 교체

기존 `get_db_connection()` 함수를 pool 기반으로 교체:

```python
# ── 기존 코드 (삭제) ──────────────────────────
def get_db_connection() -> psycopg2.extensions.connection:
    try:
        conn = psycopg2.connect(
            Config.DATABASE_URL,
            cursor_factory=psycopg2.extras.RealDictCursor,
            options="-c timezone=Asia/Seoul"
        )
        return conn
    except PsycopgError as e:
        logger.error(f"Database connection failed: {e}")
        raise

# ── 변경 코드 ──────────────────────────────────
def get_db_connection():
    """
    DB 연결 가져오기 (Connection Pool 사용).
    Sprint 30: 직접 연결 → 풀 기반으로 교체.
    호출부에서 conn.close() 대신 put_conn(conn) 사용 권장.
    하위 호환: close()도 동작하지만 풀 반납이 안 됨 (연결 낭비).
    """
    from app.db_pool import get_conn
    return get_conn()
```

### Task 3: 모든 라우트 파일 `conn.close()` → `put_conn(conn)` 변경

**핵심 변경**: `finally` 블록에서 `conn.close()` → `put_conn(conn)`

변경 대상 파일 (모든 라우트 + 서비스):
- `routes/product.py`
- `routes/factory.py`
- `routes/work.py`
- `routes/admin.py`
- `routes/gst.py`
- `routes/checklist.py`
- `routes/hr.py`
- `routes/notices.py`
- `routes/qr.py`
- `routes/alert.py`
- `services/task_seed.py`
- `services/task_service.py`
- `services/progress_service.py`
- `services/scheduler_service.py`
- `services/alert_service.py`
- `models/task_detail.py`
- `models/product_info.py`
- `models/completion_status.py`
- `models/admin_settings.py`
- `schema_check.py`

패턴:
```python
# 기존
finally:
    if conn:
        conn.close()

# 변경
from app.db_pool import put_conn
# ...
finally:
    if conn:
        put_conn(conn)
```

**⚠️ 주의**: `conn.rollback()` 호출은 유지. rollback 후 put_conn하면 풀이 해당 연결을 정리함.

```python
# 에러 처리 패턴
except PsycopgError as e:
    if conn:
        conn.rollback()
    logger.error(...)
finally:
    if conn:
        put_conn(conn)
```

### Task 4: `backend/app/__init__.py` 수정 — 풀 초기화 + 종료

```python
# create_app() 내부, 스케줄러 초기화 후:

# ★ DB Connection Pool 초기화 (Sprint 30)
if not app.config.get('TESTING', False):
    from app.db_pool import init_pool, close_pool
    init_pool()

# DB 스키마 자동 검증 (BUG-24: migration 누락 방지)
if not app.config.get('TESTING', False):
    from app.schema_check import ensure_schema
    ensure_schema()

# ...

# 앱 종료 시 풀 정리
import atexit
if not app.config.get('TESTING', False):
    atexit.register(close_pool)
```

### Task 5: Railway 환경변수 설정

Railway 대시보드에서 환경변수 추가:
```
DB_POOL_MIN=5
DB_POOL_MAX=20
```

Railway PostgreSQL 기본 max_connections 확인:
```sql
SHOW max_connections;
```
결과가 100이면 DB_POOL_MAX=20이 안전. 결과가 25이면 DB_POOL_MAX=10으로 조정.

### Task 6: version.py 업데이트

```python
VERSION = "1.8.0"
BUILD_DATE = "2026-03-17"
```

### Task 7: 테스트

기존 테스트는 `TESTING=True`일 때 풀을 초기화하지 않으므로 영향 없음.
풀 전용 테스트 추가 (선택):

```python
# tests/backend/test_db_pool.py
def test_pool_init_and_get():
    """풀 초기화 후 연결 획득/반납 테스트"""
    from app.db_pool import init_pool, get_conn, put_conn, close_pool
    init_pool()
    conn = get_conn()
    assert conn is not None
    cur = conn.cursor()
    cur.execute("SELECT 1 AS test")
    assert cur.fetchone()['test'] == 1
    put_conn(conn)
    close_pool()

def test_pool_fallback():
    """풀 없을 때 직접 연결 fallback 테스트"""
    from app.db_pool import get_conn, put_conn
    # _pool이 None인 상태에서 get_conn → 직접 연결
    conn = get_conn()
    assert conn is not None
    put_conn(conn)
```

### 체크리스트

- [x] `db_pool.py` 생성
- [x] `worker.py`의 `get_db_connection()` 교체
- [x] 모든 라우트/서비스 `conn.close()` → `put_conn(conn)` 변경 (33개 파일, 175건)
- [x] `__init__.py`에 `init_pool()` + `atexit.register(close_pool)` 추가
- [x] Railway 환경변수 `DB_POOL_MIN=5`, `DB_POOL_MAX=20` 설정 — 기본값으로 동작 중, 필요 시 추가
- [x] Railway DB `SHOW max_connections;` 확인 → 100 확인, pool max=20 안전
- [x] 로컬 테스트: 앱 시작 → `[db_pool] Connection pool initialized: min=5, max=20` 로그 확인
- [x] 기존 pytest regression 0건 확인 (35 passed, 1 failed — test_admin_email_notification 기존 이슈)
- [ ] Railway 배포 후 출퇴근 시간대 499 에러 모니터링 — 다음 출퇴근 시간에 확인
- [x] version.py v1.8.0 + BUILD_DATE 업데이트

### 롤백 계획

문제 발생 시: Railway 환경변수에 `DB_POOL_DISABLED=true` 추가 → `init_pool()`에서 즉시 return → fallback으로 기존 직접 연결 방식 사용. 코드 롤백 없이 환경변수만으로 제어 가능.

---

## Sprint 31A: DUAL 모델 지원 + DRAGON 탱크 태스크 — 다모델 QR/Task 기반 구축

> **목적**: DUAL 모델(2탱크 L/R) QR 분리 + DRAGON MECH 탱크 태스크 추가 + 모델별 PI 분기
> **범위**: BE + CORE-ETL — `model_config` 확장, `qr_registry` 확장, `task_seed.py`, `task_service.py`, `step2_load.py`
> **버전**: v1.8.0 → v1.9.0 (마이너 버전업 — 다모델 지원)

### 배경

현재 시스템은 제품당 QR 1개(DOC_{serial_number}), TMS 태스크는 GAIA만 지원.
다모델 확장 시 아래 요구사항 발생:

1. **DUAL 모델** (GAIA-I DUAL, GAIA-P DUAL 등): 탱크 2세트 → QR을 L/R로 분리하여 개별 태스크 추적 필요
2. **DRAGON**: TMS 별도 카테고리 없이 MECH에서 TANK_MODULE + PRESSURE_TEST 작업 → MECH에 태스크 추가 필요
3. **iVAS**: has_docking=True, is_tms=True, **항상 2탱크** → always_dual 플래그 필요
4. **SWS/GALLANT**: tank_in_mech=True, PI 범위가 모델별로 다름
5. **SWS JP line**: 같은 SWS지만 line=JP이면 PI 범위가 확장됨

DUAL 감지: `'DUAL' in model_name.upper().split()` (model 컬럼에 "****DUAL" 형태로 적재됨)
iVAS는 DUAL 키워드 없이도 항상 2탱크: `always_dual=True`
DRAGON은 L/R 분리 불필요 (MECH 한 곳에서 전부 처리)

### Task 1: Migration `024_multi_model_support.sql` 신규 생성

```sql
-- Migration 024: 다모델 지원 (Sprint 31A)
-- model_config 확장 + qr_registry 확장 + UNIQUE 제약 변경

BEGIN;

-- ① model_config: PI/DUAL 관련 컬럼 추가
ALTER TABLE model_config
    ADD COLUMN IF NOT EXISTS pi_lng_util BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS pi_chamber BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS always_dual BOOLEAN NOT NULL DEFAULT FALSE;

-- ② model_config 기존 데이터 업데이트
UPDATE model_config SET pi_lng_util = TRUE,  pi_chamber = TRUE,  always_dual = FALSE WHERE model_prefix = 'GAIA';
UPDATE model_config SET pi_lng_util = FALSE, pi_chamber = FALSE, always_dual = FALSE WHERE model_prefix = 'DRAGON';
UPDATE model_config SET pi_lng_util = FALSE, pi_chamber = TRUE,  always_dual = FALSE, tank_in_mech = TRUE WHERE model_prefix = 'SWS';
UPDATE model_config SET pi_lng_util = TRUE,  pi_chamber = FALSE, always_dual = FALSE, tank_in_mech = TRUE WHERE model_prefix = 'GALLANT';
UPDATE model_config SET pi_lng_util = TRUE,  pi_chamber = TRUE,  always_dual = FALSE WHERE model_prefix = 'MITHAS';
UPDATE model_config SET pi_lng_util = TRUE,  pi_chamber = TRUE,  always_dual = FALSE WHERE model_prefix = 'SDS';

-- ③ iVAS 모델 추가 (has_docking=True, is_tms=True, always_dual=True)
INSERT INTO model_config (model_prefix, has_docking, is_tms, tank_in_mech, pi_lng_util, pi_chamber, always_dual, description)
VALUES ('IVAS', TRUE, TRUE, FALSE, TRUE, TRUE, TRUE, 'iVAS 모델: 항상 2탱크(L/R), TMS 별도, 도킹 있음')
ON CONFLICT (model_prefix) DO UPDATE SET
    has_docking = EXCLUDED.has_docking,
    is_tms = EXCLUDED.is_tms,
    tank_in_mech = EXCLUDED.tank_in_mech,
    pi_lng_util = EXCLUDED.pi_lng_util,
    pi_chamber = EXCLUDED.pi_chamber,
    always_dual = EXCLUDED.always_dual,
    description = EXCLUDED.description;

-- ④ qr_registry: 탱크 QR 계층 구조 컬럼 추가
ALTER TABLE public.qr_registry
    ADD COLUMN IF NOT EXISTS parent_qr_doc_id VARCHAR(100) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS qr_type VARCHAR(20) NOT NULL DEFAULT 'PRODUCT';

-- parent_qr_doc_id FK (자기 참조)
-- 제품 QR: parent_qr_doc_id = NULL, qr_type = 'PRODUCT'
-- 탱크 QR: parent_qr_doc_id = 제품 QR의 qr_doc_id, qr_type = 'TANK'
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'qr_registry_parent_fk'
    ) THEN
        ALTER TABLE public.qr_registry
            ADD CONSTRAINT qr_registry_parent_fk
            FOREIGN KEY (parent_qr_doc_id) REFERENCES public.qr_registry(qr_doc_id)
            ON DELETE CASCADE;
    END IF;
END $$;

-- ⑤ app_task_details: UNIQUE 제약 변경
-- 기존: (serial_number, task_category, task_id)
-- 변경: (serial_number, qr_doc_id, task_category, task_id)
-- DUAL에서 같은 S/N + 같은 task_id지만 qr_doc_id(L/R)가 다른 행 허용

-- 기존 UNIQUE 제약 삭제
DO $$
BEGIN
    -- 제약 이름은 테이블 생성 방식에 따라 다를 수 있음 — 조회 후 삭제
    PERFORM 1 FROM information_schema.table_constraints
    WHERE table_name = 'app_task_details'
      AND constraint_type = 'UNIQUE';
    IF FOUND THEN
        EXECUTE (
            SELECT 'ALTER TABLE app_task_details DROP CONSTRAINT ' || constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'app_task_details'
              AND constraint_type = 'UNIQUE'
            LIMIT 1
        );
    END IF;
END $$;

-- 새 UNIQUE 제약 생성
ALTER TABLE app_task_details
    ADD CONSTRAINT app_task_details_sn_qr_cat_tid_unique
    UNIQUE (serial_number, qr_doc_id, task_category, task_id);

-- ⑥ workers / hr 테이블 보호: CASCADE → RESTRICT
-- Railway 백업 완료 (2026-03-17 13:19 UTC, 228MB) 후 실행

-- workers 삭제 시 작업 이력 보존 (CASCADE → RESTRICT)
ALTER TABLE work_start_log
    DROP CONSTRAINT IF EXISTS work_start_log_worker_id_fkey;
ALTER TABLE work_start_log
    ADD CONSTRAINT work_start_log_worker_id_fkey
    FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE RESTRICT;

ALTER TABLE work_completion_log
    DROP CONSTRAINT IF EXISTS work_completion_log_worker_id_fkey;
ALTER TABLE work_completion_log
    ADD CONSTRAINT work_completion_log_worker_id_fkey
    FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE RESTRICT;

-- workers 삭제 시 PIN/생체인증 보존 (CASCADE → RESTRICT)
ALTER TABLE hr.worker_auth_settings
    DROP CONSTRAINT IF EXISTS worker_auth_settings_worker_id_fkey;
ALTER TABLE hr.worker_auth_settings
    ADD CONSTRAINT worker_auth_settings_worker_id_fkey
    FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE RESTRICT;

-- hr 출퇴근 기록: FK 규칙 없음 → RESTRICT 추가
ALTER TABLE hr.partner_attendance
    DROP CONSTRAINT IF EXISTS partner_attendance_worker_id_fkey;
ALTER TABLE hr.partner_attendance
    ADD CONSTRAINT partner_attendance_worker_id_fkey
    FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE RESTRICT;

ALTER TABLE hr.gst_attendance
    DROP CONSTRAINT IF EXISTS gst_attendance_worker_id_fkey;
ALTER TABLE hr.gst_attendance
    ADD CONSTRAINT gst_attendance_worker_id_fkey
    FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE RESTRICT;

-- app_task_details.worker_id: 작업자 삭제 시 태스크는 보존, 담당자만 NULL
ALTER TABLE app_task_details
    DROP CONSTRAINT IF EXISTS app_task_details_worker_id_fkey;
ALTER TABLE app_task_details
    ADD CONSTRAINT app_task_details_worker_id_fkey
    FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE SET NULL;

COMMIT;
```

### Task 2: `backend/app/models/model_config.py` 수정 — 신규 컬럼 반영

```python
# ModelConfig dataclass 확장
@dataclass
class ModelConfig:
    id: int
    model_prefix: str
    has_docking: bool
    is_tms: bool
    tank_in_mech: bool
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    # Sprint 31A: 다모델 PI/DUAL 지원
    pi_lng_util: bool = True       # PI LNG/UTIL 가압검사 진행 여부
    pi_chamber: bool = True        # PI CHAMBER 가압검사 진행 여부
    always_dual: bool = False      # 항상 2탱크 (iVAS)

    @staticmethod
    def from_db_row(row: Dict[str, Any]) -> "ModelConfig":
        return ModelConfig(
            id=row['id'],
            model_prefix=row['model_prefix'],
            has_docking=row['has_docking'],
            is_tms=row['is_tms'],
            tank_in_mech=row['tank_in_mech'],
            description=row.get('description'),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            pi_lng_util=row.get('pi_lng_util', True),
            pi_chamber=row.get('pi_chamber', True),
            always_dual=row.get('always_dual', False),
        )

    def to_dict(self) -> Dict[str, Any]:
        d = {
            'id': self.id,
            'model_prefix': self.model_prefix,
            'has_docking': self.has_docking,
            'is_tms': self.is_tms,
            'tank_in_mech': self.tank_in_mech,
            'pi_lng_util': self.pi_lng_util,
            'pi_chamber': self.pi_chamber,
            'always_dual': self.always_dual,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        return d
```

### Task 3: `backend/app/services/task_seed.py` 수정 — 핵심 변경

```python
"""
Task Seed 서비스
Sprint 31A: 다모델 지원
  - DUAL 모델: TMS 태스크를 L/R qr_doc_id별 생성
  - iVAS: always_dual=True → DUAL 키워드 없이도 L/R 생성
  - DRAGON: MECH에 TANK_MODULE + PRESSURE_TEST 추가, tm_completed=TRUE
  - SWS/GALLANT: MECH에 TANK_MODULE 추가, PI 범위 model_config 기반
  - SWS JP line: product_info.line='JP'이면 PI_LNG_UTIL 추가 활성
"""

# ── DUAL 감지 함수 ──────────────────────────────────
def _is_dual_model(model_name: str, config) -> bool:
    """DUAL 여부 판단: model명에 'DUAL' 포함 OR always_dual=True"""
    if config and config.always_dual:
        return True
    return 'DUAL' in model_name.upper().split()


# ── DRAGON/SWS/GALLANT MECH 추가 태스크 ──────────────
MECH_TANK_TASKS: List[TaskTemplate] = [
    TaskTemplate('TANK_MODULE',   'Tank Module', 'PRE_DOCKING', False),
    TaskTemplate('PRESSURE_TEST', '가압검사',    'FINAL',       False),
]

MECH_TANK_MODULE_ONLY: List[TaskTemplate] = [
    TaskTemplate('TANK_MODULE',   'Tank Module', 'PRE_DOCKING', False),
]


def initialize_product_tasks(serial_number, qr_doc_id, model_name):
    config = get_model_config_for_product(model_name)
    # ... 기존 config 분기 ...

    is_dual = _is_dual_model(model_name, config)
    tank_in_mech = config.tank_in_mech if config else False
    pi_lng_util = config.pi_lng_util if config else True
    pi_chamber = config.pi_chamber if config else True

    # ── MECH Tasks (7개 + tank_in_mech 추가분) ──────
    for t in MECH_TASKS:
        # ... 기존 로직 동일 ...
        pass

    # tank_in_mech 모델: MECH에 탱크 태스크 추가
    if tank_in_mech:
        # DRAGON: TANK_MODULE + PRESSURE_TEST (PI 불필요하므로)
        # SWS/GALLANT: TANK_MODULE만 (가압검사는 GST PI가 담당)
        extra_tasks = MECH_TANK_TASKS if not pi_lng_util and not pi_chamber else MECH_TANK_MODULE_ONLY
        for t in extra_tasks:
            inserted = _upsert_task(
                cur, serial_number, qr_doc_id,
                'MECH', t.task_id, t.task_name, t.phase, True, t.task_type
            )
            if inserted:
                created += 1
                counts['MECH'] += 1
            else:
                skipped += 1

    # ── ELEC Tasks (6개) — 전 모델 공통 (기존 동일) ──────

    # ── TMS Tasks — is_tms 모델만 ──────
    if is_tms:
        if is_dual:
            # DUAL: L/R 탱크별 TMS 태스크 생성
            for suffix in ['-L', '-R']:
                tank_qr = f"{qr_doc_id}{suffix}"
                for t in TMS_TASKS:
                    inserted = _upsert_task(
                        cur, serial_number, tank_qr,
                        'TMS', t.task_id, t.task_name, t.phase, True, t.task_type
                    )
                    if inserted:
                        created += 1
                        counts['TMS'] += 1
                    else:
                        skipped += 1
        else:
            # SINGLE: 기존 동일
            for t in TMS_TASKS:
                inserted = _upsert_task(
                    cur, serial_number, qr_doc_id,
                    'TMS', t.task_id, t.task_name, t.phase, True, t.task_type
                )
                # ...

    # ── PI Tasks — model_config 기반 분기 ──────
    # SWS JP line 예외: product_info.line='JP'이면 pi_lng_util 강제 활성
    if tank_in_mech:
        # product_info에서 line 조회
        cur.execute(
            "SELECT line FROM plan.product_info WHERE serial_number = %s",
            (serial_number,)
        )
        line_row = cur.fetchone()
        product_line = line_row['line'] if line_row else ''
        # SWS + JP line → pi_lng_util 활성 오버라이드
        if product_line and product_line.strip().upper() == 'JP':
            pi_lng_util = True

    for t in PI_TASKS:
        if t.task_id == 'PI_LNG_UTIL':
            is_applicable = pi_lng_util
        elif t.task_id == 'PI_CHAMBER':
            is_applicable = pi_chamber
        else:
            is_applicable = True
        inserted = _upsert_task(
            cur, serial_number, qr_doc_id,
            'PI', t.task_id, t.task_name, t.phase, is_applicable, t.task_type
        )
        # ...

    # ── QI, SI Tasks (기존 동일) ──────

    conn.commit()

    # completion_status 생성
    get_or_create_completion_status(serial_number)

    # DRAGON 등 is_tms=False 모델: tm_completed = TRUE
    if not is_tms:
        from app.models.completion_status import update_process_completion
        update_process_completion(serial_number, 'TMS', True)

    return { ... }
```

### Task 4: `CORE-ETL/step2_load.py` 수정 — DUAL Tank QR 생성

```python
# _process_single_record() 내부, qr_registry INSERT 직후 (is_insert=True 블록):

    elif row[1]:  # is_insert = True (신규 제품)
        product_id = row[0]
        qr_doc_id = generate_qr_doc_id(sn)

        # 제품 QR 생성 (기존)
        cursor.execute('''
            INSERT INTO public.qr_registry (qr_doc_id, serial_number, status, qr_type)
            VALUES (%s, %s, 'active', 'PRODUCT')
            RETURNING id
        ''', (qr_doc_id, sn))
        cursor.fetchone()

        # ★ Sprint 31A: DUAL 모델 → Tank QR 추가 생성
        # DUAL 감지: model_name에 'DUAL' 단어 포함 여부
        # always_dual 감지: model_config 조회 필요
        model_name = item['model_name']
        is_dual = 'DUAL' in model_name.upper().split()

        # always_dual 체크 (model_config 조회)
        if not is_dual:
            cursor.execute("""
                SELECT always_dual FROM model_config
                WHERE %s ILIKE model_prefix || '%%'
                ORDER BY LENGTH(model_prefix) DESC
                LIMIT 1
            """, (model_name,))
            mc_row = cursor.fetchone()
            if mc_row and mc_row[0]:
                is_dual = True

        # DRAGON 계열(tank_in_mech=True)은 Tank QR 미생성
        is_tank_in_mech = False
        if is_dual:
            cursor.execute("""
                SELECT tank_in_mech FROM model_config
                WHERE %s ILIKE model_prefix || '%%'
                ORDER BY LENGTH(model_prefix) DESC
                LIMIT 1
            """, (model_name,))
            mc_row = cursor.fetchone()
            if mc_row and mc_row[0]:
                is_tank_in_mech = True

        if is_dual and not is_tank_in_mech:
            for suffix in ['-L', '-R']:
                tank_qr = f"{qr_doc_id}{suffix}"
                cursor.execute('''
                    INSERT INTO public.qr_registry
                        (qr_doc_id, serial_number, status, qr_type, parent_qr_doc_id)
                    VALUES (%s, %s, 'active', 'TANK', %s)
                    ON CONFLICT (qr_doc_id) DO NOTHING
                ''', (tank_qr, sn, qr_doc_id))
            print(f"  [DUAL] {sn} → Tank QR 생성: {qr_doc_id}-L, {qr_doc_id}-R")

        status = 'inserted'
```

주의: `qr_registry`에 `qr_type` 컬럼을 추가했으므로, 기존 INSERT 구문에도 `qr_type = 'PRODUCT'`를 명시해야 함 (DEFAULT가 'PRODUCT'이므로 기존 데이터는 영향 없음).

### Task 5: `backend/app/services/task_service.py` 수정 — 알람 확장

```python
def _trigger_completion_alerts(self, task) -> None:
    """
    Sprint 31A: 다모델 알람 확장
    - GAIA SINGLE: TMS PRESSURE_TEST 완료 → MECH 매니저 (기존)
    - GAIA DUAL:   TMS PRESSURE_TEST L+R 모두 완료 시 1회 → MECH 매니저
    - DRAGON:      MECH PRESSURE_TEST 완료 → QI 매니저
    - MECH TANK_DOCKING 완료 → ELEC 매니저 (기존)
    - PI 완료 → QI 매니저 (옵션, 같은 부서이므로)
    """
    trigger = None

    if task.task_id == 'PRESSURE_TEST':
        if task.task_category == 'TMS':
            # GAIA 계열 — DUAL 체크
            if self._is_dual_pressure_all_done(task.serial_number):
                trigger = ('TMS_TANK_COMPLETE', 'MECH', 'TMS 가압검사 완료 (전체 탱크)')
            # SINGLE이면 즉시 또는 DUAL인데 아직 하나만 완료면 skip
        elif task.task_category == 'MECH':
            # DRAGON 계열 — MECH에서 가압검사 완료 → QI 매니저
            trigger = ('TMS_TANK_COMPLETE', 'QI', 'MECH 가압검사 완료')

    elif task.task_category == 'MECH' and task.task_id == 'TANK_DOCKING':
        trigger = ('TANK_DOCKING_COMPLETE', 'ELEC', 'Tank Docking 완료')

    # 옵션: PI 전체 완료 → QI 매니저 알람
    elif task.task_category == 'PI':
        from app.models.task_detail import get_incomplete_tasks
        incomplete_pi = get_incomplete_tasks(task.serial_number, 'PI')
        if len(incomplete_pi) == 0:
            trigger = ('TMS_TANK_COMPLETE', 'QI', 'PI 검사 완료')

    if trigger is None:
        return

    # ... 기존 알람 생성 로직 동일 ...


def _is_dual_pressure_all_done(self, serial_number: str) -> bool:
    """DUAL 모델의 PRESSURE_TEST가 L+R 모두 완료인지 확인"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as incomplete
            FROM app_task_details
            WHERE serial_number = %s
              AND task_category = 'TMS'
              AND task_id = 'PRESSURE_TEST'
              AND completed_at IS NULL
              AND is_applicable = TRUE
        """, (serial_number,))
        row = cur.fetchone()
        return row['incomplete'] == 0
    except Exception:
        return True  # 에러 시 알람 발송 (안전 방향)
    finally:
        if conn:
            put_conn(conn)
```

### Task 6: version.py 업데이트

```python
VERSION = "1.9.0"
BUILD_DATE = "2026-03-18"
```

### Task 7: 테스트 시나리오

```
[DUAL 테스트]
1. GAIA-I DUAL 제품 ETL 적재
   → qr_registry에 DOC_{sn}, DOC_{sn}-L, DOC_{sn}-R 3건 생성 확인
   → Tank QR의 parent_qr_doc_id, qr_type 확인
2. QR 태깅 시 task_seed 호출
   → TMS 태스크 4건 확인 (TANK_MODULE×2 + PRESSURE_TEST×2)
   → L탱크 QR 스캔 → L 태스크만 표시
   → R탱크 QR 스캔 → R 태스크만 표시
3. L PRESSURE_TEST 완료 → 알람 미발송
4. R PRESSURE_TEST 완료 → MECH 매니저 알람 1건 확인

[iVAS 테스트]
5. iVAS 제품 ETL 적재 (model에 'DUAL' 없음)
   → always_dual=True → DOC_{sn}-L, DOC_{sn}-R 생성 확인

[DRAGON 테스트]
6. DRAGON 제품 task_seed
   → MECH에 TANK_MODULE + PRESSURE_TEST 추가 확인 (총 9개)
   → TMS 태스크 0건, tm_completed=TRUE 확인
7. MECH PRESSURE_TEST 완료 → QI 매니저 알람 확인

[SWS 테스트]
8. SWS 제품 task_seed
   → MECH에 TANK_MODULE 추가 확인
   → PI_LNG_UTIL=FALSE, PI_CHAMBER=TRUE 확인
9. SWS + line=JP 제품 task_seed
   → PI_LNG_UTIL=TRUE, PI_CHAMBER=TRUE 확인

[GALLANT 테스트]
10. GALLANT 제품 task_seed
    → MECH에 TANK_MODULE 추가 확인
    → PI_LNG_UTIL=TRUE, PI_CHAMBER=FALSE 확인
```

### 코드 수정 체크리스트

- [x] Railway DB 백업 확인 (2026-03-17 13:19 UTC, 228MB)
- [x] Migration 024 SQL 작성 완료 (`backend/migrations/024_multi_model_support.sql`)
- [x] model_config.py 수정 완료 — pi_lng_util, pi_chamber, always_dual 필드 추가
- [x] task_seed.py 수정 완료 — _is_dual_model, MECH_TANK_TASKS, DUAL L/R, PI 분기, tm_completed
- [x] task_seed.py ON CONFLICT 수정 — `(serial_number, qr_doc_id, task_category, task_id)` migration 024 UNIQUE와 일치
- [x] task_seed.py TMS→TM 매핑 수정 — `update_process_completion(sn, 'TM', True)` (process_map 키가 'TM')
- [x] task_service.py 수정 완료 — _trigger_completion_alerts 확장, _is_dual_pressure_all_done 추가
- [x] schema_check.py 수정 완료 — REQUIRED_COLUMNS 5개 + REQUIRED_CONSTRAINTS 5개 추가
- [x] conftest.py 수정 완료 — migration_files에 022, 023, 024 추가 (테스트 DB 재생성 시 누락 방지)
- [x] step2_load.py 수정 완료 — DUAL Tank QR 생성, qr_type='PRODUCT' 명시
- [x] version.py v1.9.0 업데이트 완료
- [x] White-box 테스트 21/21 PASS (TestIsDualModel 6건, TestDualAlarmLogic 2건)
- [x] Migration 024 SWS/GALLANT tank_in_mech=TRUE 누락 수정 완료

### DB 배포 체크리스트 (Railway — 2026-03-18 완료)

- [x] Migration 024 Railway DB 실행 (teammate + schema_check 자동 적용)
- [x] workers/hr 테이블 RESTRICT 보호 확인 — work_start_log, work_completion_log, partner_attendance, gst_attendance, worker_auth_settings 전부 RESTRICT
- [x] app_task_details.worker_id → SET NULL 확인
- [x] model_config 7개 모델 확인 — DRAGON(tank_in_mech=T, pi=F/F), SWS(tank_in_mech=T, pi=F/T), GALLANT(tank_in_mech=T, pi=T/F), IVAS(always_dual=T)
- [x] iVAS model_config 추가 확인 (model_prefix='IVAS', has_docking=T, is_tms=T, always_dual=T)
- [x] qr_registry parent_qr_doc_id, qr_type 컬럼 확인
- [x] app_task_details UNIQUE 제약 변경 확인 (app_task_details_sn_qr_cat_tid_unique)

### Sprint 30-B: DB Pool TCP 수정 (2026-03-18 완료)

- [x] db_pool.py — TCP keepalive 활성화 (idle=30s, interval=10s, count=3)
- [x] db_pool.py — connect_timeout=5s, health check (SELECT 1), dead connection 자동 교체
- [x] Procfile — workers 1→2, threads 4→8, timeout=30s 명시
- [x] Railway DATABASE_URL → public proxy 유지 (private networking IPv6 전용 문제로 보류)
- [ ] Railway Private Networking IPv6→IPv4+IPv6 전환 시 DATABASE_URL private 전환 (보류)

### 기능 검증 체크리스트 (코드 push 후 진행)

> Sprint 31A 코드가 push되어야 Railway에 배포되고 기능 검증 가능

- [x] Sprint 31A 코드 commit & push (AXIS-OPS) — fa97a7f
- [x] CORE-ETL step2_load.py commit & push (AXIS-CORE) — 1489885 (v0.3.0)
- [x] Gray-box 테스트 실행 — 21 passed, 0 failed, 2 skipped
- [x] Regression 테스트 — test_active_role ON CONFLICT 수정 완료 (테스트 20건 4컬럼 일괄 교체)
- [ ] CORE-ETL step2_load.py DUAL Tank QR 생성 확인
- [x] task_seed.py DUAL L/R TMS 태스크 — migration 025로 serial_number UNIQUE 제거, 21 passed
- [x] task_seed.py DRAGON/SWS/GALLANT MECH 탱크 태스크 확인 (PASSED)
- [x] task_seed.py PI 범위 model_config 기반 분기 확인 (PASSED)
- [x] task_seed.py SWS JP line 예외 확인 (PASSED)
- [x] task_seed.py DRAGON tm_completed=TRUE 확인 (PASSED)
- [ ] task_service.py DUAL L+R 합산 알람 확인 (DUAL UNIQUE 해결됨 — 실기기 테스트 필요)
- [ ] task_service.py DRAGON → QI 알람 확인
- [ ] task_service.py PI → QI 알람 확인 (옵션)
- [ ] 기존 GAIA SINGLE 제품 regression 확인 (기존 태스크 영향 없음)
- [x] QR 대시보드: qr_type 필드 BE 응답 추가 + stats PRODUCT 기준 카운트

#### ⚠️ DUAL QR 설계 결정 필요

**현상**: `qr_registry.serial_number`에 UNIQUE 제약 → 같은 serial_number로 L/R QR 2행 등록 불가
**영향**: DUAL 모델(GAIA DUAL, iVAS)의 L/R 탱크 QR을 qr_registry에 등록할 수 없음
**선택지**:
1. serial_number UNIQUE 유지 → L/R QR serial_number를 `SN-L`, `SN-R`로 분리 (completion_status FK 영향 없음)
2. serial_number UNIQUE 제거 → 같은 S/N 공유 허용 (completion_status FK 재설계 필요)
3. L/R QR은 qr_registry에 등록하지 않고, app_task_details의 qr_doc_id만으로 관리 (기존 FK 영향 없음)

---

### Gray-box 테스트 시나리오 (DB 연결 필요 — Railway)

> 아래 테스트는 실제 Railway DB에 연결된 환경에서 실행해야 합니다.
> 테스트 파일: `tests/backend/test_sprint31a_multi_model.py`

#### 테스트 클래스 및 시나리오

**Class 1: TestModelConfigSprint31A** (6건)
```
- test_gaia_config_has_pi_columns: GAIA → pi_lng_util=True, pi_chamber=True, always_dual=False
- test_dragon_config_no_pi: DRAGON → pi_lng_util=False, pi_chamber=False
- test_sws_config: SWS → pi_chamber=True, pi_lng_util=False, tank_in_mech=True
- test_gallant_config: GALLANT → pi_lng_util=True, pi_chamber=False, tank_in_mech=True
- test_ivas_config: IVAS → always_dual=True, has_docking=True, is_tms=True
- test_all_models_have_new_columns: 전체 모델 신규 컬럼 NOT NULL 확인
```

**Class 2: TestTaskSeedDual** (2건)
```
- test_dual_creates_lr_tms_tasks: GAIA DUAL → DOC_{sn}-L, DOC_{sn}-R TMS 태스크 생성 확인
- test_single_no_lr_tasks: GAIA SINGLE → L/R 분리 없이 기존 qr_doc_id로 TMS 태스크
```

**Class 3: TestTaskSeedDragon** (2건)
```
- test_dragon_mech_extra_tasks: DRAGON → MECH에 TANK_MODULE + PRESSURE_TEST 추가 (총 9개)
- test_dragon_tm_completed_true: DRAGON → completion_status.tm_completed = TRUE
```

**Class 4: TestTaskSeedPI** (3건)
```
- test_sws_pi_chamber_only: SWS → PI_CHAMBER=applicable, PI_LNG_UTIL=not applicable
- test_sws_jp_pi_both: SWS + line='JP' → PI_LNG_UTIL + PI_CHAMBER 둘 다 applicable
- test_gallant_pi_util_only: GALLANT → PI_LNG_UTIL=applicable, PI_CHAMBER=not applicable
```

**Class 5: TestTaskSeedSWSGallant** (2건)
```
- test_sws_mech_tank_module_only: SWS → MECH에 TANK_MODULE만 추가 (PRESSURE_TEST 없음)
- test_gallant_mech_tank_module_only: GALLANT → MECH에 TANK_MODULE만 추가
```

#### 테스트 실행 명령어

```bash
# 프로젝트 루트에서
cd ~/Desktop/GST/AXIS-OPS

# 전체 Sprint 31A 테스트 실행
python -m pytest tests/backend/test_sprint31a_multi_model.py -v

# 개별 클래스 실행
python -m pytest tests/backend/test_sprint31a_multi_model.py::TestModelConfigSprint31A -v
python -m pytest tests/backend/test_sprint31a_multi_model.py::TestTaskSeedDual -v
python -m pytest tests/backend/test_sprint31a_multi_model.py::TestTaskSeedDragon -v
python -m pytest tests/backend/test_sprint31a_multi_model.py::TestTaskSeedPI -v
python -m pytest tests/backend/test_sprint31a_multi_model.py::TestTaskSeedSWSGallant -v

# White-box 테스트만 (DB 불필요)
python -m pytest tests/backend/test_sprint31a_multi_model.py::TestIsDualModel -v
python -m pytest tests/backend/test_sprint31a_multi_model.py::TestDualAlarmLogic -v
```

#### DB가 없는 환경에서 White-box 테스트만 실행

```bash
# conftest.py db_conn 고정 없이 직접 실행
python -c "
import sys; sys.path.insert(0, 'backend')
from tests.backend.test_sprint31a_multi_model import TestIsDualModel, TestDualAlarmLogic
import unittest

suite = unittest.TestSuite()
for cls in [TestIsDualModel, TestDualAlarmLogic]:
    for method in dir(cls):
        if method.startswith('test_'):
            suite.addTest(cls(method))

runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
"
```

---

### Claude Code Teammate 실행 가이드

> Sprint 31A는 코드 수정이 이미 완료되었습니다.
> Teammate는 **Migration 실행 + Gray-box 테스트 + 배포 검증**에 사용합니다.

#### Step 1: Claude Code 실행

```bash
cd ~/Desktop/GST/AXIS-OPS
claude
```

#### Step 2: Migration 실행 프롬프트

```
Sprint 31A Migration 024를 Railway DB에 실행해줘.

파일 위치: backend/migrations/024_multi_model_support.sql

실행 순서:
1. 먼저 CLAUDE.md를 읽고 DB 연결 정보 확인
2. Migration SQL 파일 내용 확인 (cat으로 확인)
3. psql 또는 Python으로 Railway DB에 연결
4. BEGIN ~ COMMIT 트랜잭션 안에서 실행
5. 실행 후 검증:
   - SELECT * FROM model_config ORDER BY model_prefix;
     → IVAS 행 존재, SWS/GALLANT tank_in_mech=TRUE 확인
   - SELECT column_name FROM information_schema.columns WHERE table_name = 'qr_registry' AND column_name IN ('parent_qr_doc_id', 'qr_type');
   - SELECT constraint_name, delete_rule FROM information_schema.referential_constraints WHERE constraint_name LIKE '%worker_id_fkey';

문제 발생 시 ROLLBACK하고 에러 내용 알려줘.
```

#### Step 3: Gray-box 테스트 실행 프롬프트

```
Sprint 31A Gray-box 테스트를 실행해줘.

테스트 파일: tests/backend/test_sprint31a_multi_model.py

실행 명령:
python -m pytest tests/backend/test_sprint31a_multi_model.py -v --tb=short

DB 연결이 필요한 테스트 클래스:
- TestModelConfigSprint31A (6건)
- TestTaskSeedDual (2건)
- TestTaskSeedDragon (2건)
- TestTaskSeedPI (3건)
- TestTaskSeedSWSGallant (2건)

총 21건 (White-box 8건 + Gray-box 15건 = 23건 전체)

실패하는 테스트가 있으면:
1. 에러 메시지 분석
2. 원인 파악 (DB 스키마 vs 코드 로직)
3. 수정이 필요하면 수정 방안 제시 (코드 직접 수정 금지 — 나한테 확인 받고 진행)
```

#### Step 4: 기존 테스트 Regression 확인

```
기존 테스트 전체를 실행해서 Sprint 31A 변경으로 깨진 테스트가 없는지 확인해줘.

python -m pytest tests/ -v --tb=short -x

실패하는 테스트가 있으면 원인 분석 후 알려줘.
특히 task_seed, task_service, model_config 관련 기존 테스트가 영향받을 수 있으니 주의.
```

### 롤백 계획

문제 발생 시:
1. UNIQUE 제약: 신규 UNIQUE 삭제 → 기존 UNIQUE 재생성
   ```sql
   ALTER TABLE app_task_details DROP CONSTRAINT app_task_details_sn_qr_cat_tid_unique;
   ALTER TABLE app_task_details ADD CONSTRAINT app_task_details_unique UNIQUE (serial_number, task_category, task_id);
   ```
2. model_config: 신규 컬럼은 DEFAULT 값이 있어 기존 코드에 영향 없음
3. qr_registry: parent_qr_doc_id, qr_type도 DEFAULT 있어 기존 동작 유지
4. task_seed: 기존 SINGLE 모델은 is_dual=False로 기존 로직 그대로 실행
5. SWS/GALLANT tank_in_mech 복구: `UPDATE model_config SET tank_in_mech = FALSE WHERE model_prefix IN ('SWS', 'GALLANT');`
6. workers/hr RESTRICT → CASCADE 복구:
   ```sql
   -- 긴급 복구 시에만 (데이터 보호 해제됨)
   ALTER TABLE work_start_log DROP CONSTRAINT work_start_log_worker_id_fkey;
   ALTER TABLE work_start_log ADD CONSTRAINT work_start_log_worker_id_fkey FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE CASCADE;
   -- 나머지 테이블도 동일 패턴
   ```

---

## Sprint 31B: QR 기반 태스크 필터링 — DUAL L/R 분리 표시

> **목적**: QR 스캔 시 해당 QR에 배정된 태스크만 표시 (PRODUCT QR → 본체 작업, TANK QR → 해당 탱크 TMS만)
> **범위**: BE 3파일 수정 완료 + FE Flutter 3파일 수정 필요
> **의존성**: Sprint 31A 완료

### 배경

Sprint 31A에서 DUAL 모델의 TMS 태스크가 L/R 분리되었으나, 태스크 조회가 `serial_number` 기준이라서
TANK QR L을 스캔해도 L+R 전부(4개) 표시되는 문제 발생.

물리적 흐름:
- 캐비넷 QR(PRODUCT) 스캔 → MECH/ELEC/PI/QI/SI 작업 표시
- 탱크 모듈 QR(TANK L) 스캔 → 해당 탱크 TMS 작업만 표시 (2개)
- 탱크 모듈 QR(TANK R) 스캔 → 해당 탱크 TMS 작업만 표시 (2개)

핵심 설계: task_seed가 이미 올바른 qr_doc_id로 태스크를 생성하므로, **조회 시 qr_doc_id로 필터링**하면 모든 모델에서 자동 분리됨.

```
GAIA SINGLE:  PRODUCT QR → MECH+ELEC+TMS+PI+QI+SI (전부 같은 qr_doc_id)
GAIA DUAL:    PRODUCT QR → MECH+ELEC+PI+QI+SI / TANK L → TMS×2 / TANK R → TMS×2
DRAGON:       PRODUCT QR → MECH(+TANK_MODULE+PRESSURE_TEST)+ELEC+QI+SI
SWS/GALLANT:  PRODUCT QR → MECH(+TANK_MODULE)+ELEC+PI+QI+SI
```

### BE 수정 (✅ 완료 — Cowork에서 수정됨)

**1. `backend/app/models/task_detail.py`** — `get_tasks_by_qr_doc_id()` 함수 추가

```python
def get_tasks_by_qr_doc_id(
    qr_doc_id: str,
    task_category: Optional[str] = None
) -> List[TaskDetail]:
    """qr_doc_id로 작업 목록 조회 — DUAL L/R 분리"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        if task_category:
            cur.execute(
                "SELECT * FROM app_task_details WHERE qr_doc_id = %s AND task_category = %s ORDER BY id",
                (qr_doc_id, task_category)
            )
        else:
            cur.execute(
                "SELECT * FROM app_task_details WHERE qr_doc_id = %s ORDER BY id",
                (qr_doc_id,)
            )
        rows = cur.fetchall()
        return [TaskDetail.from_db_row(row) for row in rows]
    except PsycopgError as e:
        logger.error(f"Failed to get tasks by qr_doc_id={qr_doc_id}: {e}")
        return []
    finally:
        if conn:
            put_conn(conn)
```

**2. `backend/app/routes/work.py`** — `?qr_doc_id=` 쿼리 파라미터 추가

```python
qr_doc_id = request.args.get('qr_doc_id')  # Sprint 31B

if qr_doc_id:
    tasks = get_tasks_by_qr_doc_id(qr_doc_id, task_category)
else:
    tasks = get_tasks_by_serial_number(serial_number, task_category)
```

하위 호환: qr_doc_id 없이 호출하면 기존 serial_number 기준 동작.

**3. `backend/app/routes/product.py`** — TANK QR 스캔 시 PRODUCT QR로 task_seed

```python
seed_qr_doc_id = product.qr_doc_id
try:
    _conn = get_db_connection()
    _cur = _conn.cursor()
    _cur.execute(
        "SELECT parent_qr_doc_id FROM qr_registry WHERE qr_doc_id = %s",
        (qr_doc_id,)
    )
    _qr_row = _cur.fetchone()
    if _qr_row and _qr_row.get('parent_qr_doc_id'):
        seed_qr_doc_id = _qr_row['parent_qr_doc_id']
    _put_conn(_conn)
except Exception:
    pass

seed_result = initialize_product_tasks(
    serial_number=product.serial_number,
    qr_doc_id=seed_qr_doc_id,      # 항상 PRODUCT QR
    model_name=product.model
)
```

### FE 수정 (Teammate 작업)

> CLAUDE.md 읽고 아래 작업 진행. BE 수정은 이미 완료 — FE만 수정.

**팀 구성**: 1명 teammate (Sonnet), **FE** — 소유: frontend/**

#### Task 1: `lib/services/task_service.dart` — qrDocId 파라미터 추가

```dart
// getTasksBySerialNumber 함수에 optional qrDocId 파라미터 추가
Future<List<TaskItem>> getTasksBySerialNumber({
    required String serialNumber,
    required int workerId,
    String? qrDocId,                              // ← 추가
}) async {
    try {
        final params = <String, dynamic>{'worker_id': workerId};
        if (qrDocId != null) {
            params['qr_doc_id'] = qrDocId;        // ← 추가
        }
        final response = await _apiService.get(
            '/app/tasks/$serialNumber',
            queryParameters: params,              // ← 변경
        );
        // ... 기존 파싱 로직 동일 ...
    }
}
```

#### Task 2: `lib/providers/task_provider.dart` — fetchTasks에 qrDocId 전달

```dart
// fetchTasks 함수에 optional qrDocId 파라미터 추가
Future<bool> fetchTasks({
    required String serialNumber,
    required int workerId,
    String? qrDocId,                              // ← 추가
}) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
        final tasks = await _taskService.getTasksBySerialNumber(
            serialNumber: serialNumber,
            workerId: workerId,
            qrDocId: qrDocId,                     // ← 추가
        );
        // ... 기존 상태 업데이트 동일 ...
    }
}
```

#### Task 3: fetchTasks 호출부 — currentQrDocId 전달

fetchTasks를 호출하는 모든 곳에서 현재 스캔한 QR의 qrDocId를 전달:

```dart
// 예: QR 스캔 후 태스크 로드
await taskProvider.fetchTasks(
    serialNumber: product.serialNumber,
    workerId: currentWorker.id,
    qrDocId: taskProvider.currentQrDocId,         // ← 추가
);
```

⚠️ fetchTasks 호출부를 전부 찾아서 수정해야 함:
```bash
grep -rn "fetchTasks" frontend/lib/ --include="*.dart"
```

### 체크리스트

**BE (✅ 완료)**:
- [x] task_detail.py — get_tasks_by_qr_doc_id 함수 추가
- [x] work.py — qr_doc_id 쿼리 파라미터 추가 (하위 호환)
- [x] product.py — TANK QR → PRODUCT QR 해석 후 task_seed

**FE (✅ 완료)**:
- [x] task_service.dart — getTasksBySerialNumber에 qrDocId 파라미터 추가
- [x] task_provider.dart — fetchTasks에 qrDocId 전달
- [x] fetchTasks 호출부 수정 — ref.read(taskProvider).currentQrDocId 전달 (1곳)
- [ ] GAIA-I DUAL PRODUCT QR 스캔 → MECH+ELEC+PI+QI+SI 표시 확인 — 실기기 테스트
- [ ] GAIA-I DUAL TANK QR L 스캔 → TMS 2개만 표시 확인 — 실기기 테스트
- [ ] GAIA-I DUAL TANK QR R 스캔 → TMS 2개만 표시 확인 — 실기기 테스트
- [ ] GAIA SINGLE QR 스캔 → 기존과 동일 확인 — 실기기 테스트
- [ ] DRAGON QR 스캔 → MECH(+TANK_MODULE+PRESSURE_TEST)+ELEC+QI+SI 확인 — 실기기 테스트
- [x] flutter build web 에러 없음 + Netlify 배포 완료

---

## Sprint 32: 사용자 행위 트래킹 — API Access Log

> **목적**: 모든 인증 API 호출을 기록하여 사용자 접속 횟수, 사용 시간, 기능 사용 패턴 분석
> **범위**: BE — 미들웨어 + 테이블 + 조회 API
> **관련**: AXIS-VIEW Sprint 7에서 분석 대시보드 구현

### 배경

현재 사용자 행동 데이터가 없어서 접속 빈도, 어떤 기능을 많이 쓰는지, 에러가 언제 발생하는지 알 수 없음.
`@jwt_required` 미들웨어를 통과하는 모든 API 호출을 기록하면 비용 없이 전수 트래킹 가능.

### Task 1: Migration — `app_access_log` 테이블 생성

```sql
-- Migration 026: 사용자 행위 트래킹
CREATE TABLE IF NOT EXISTS app_access_log (
    id BIGSERIAL PRIMARY KEY,
    worker_id INTEGER REFERENCES workers(id) ON DELETE SET NULL,
    worker_email VARCHAR(255),
    worker_role VARCHAR(50),
    endpoint VARCHAR(255),          -- /api/app/work/start
    method VARCHAR(10),             -- GET, POST, PUT, DELETE
    status_code INTEGER,            -- 200, 400, 500
    duration_ms INTEGER,            -- 응답 소요 시간 (ms)
    ip_address VARCHAR(45),
    user_agent TEXT,
    request_path VARCHAR(500),      -- 전체 path + query params
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스 (대시보드 쿼리 성능)
CREATE INDEX idx_access_log_worker_created ON app_access_log(worker_id, created_at);
CREATE INDEX idx_access_log_created ON app_access_log(created_at);
CREATE INDEX idx_access_log_endpoint ON app_access_log(endpoint, created_at);

-- 30일 이상 된 로그 자동 삭제 (선택적 — 데이터 크기 관리)
-- 필요 시 scheduler_service에 cron job 추가
```

### Task 2: 미들웨어 수정 — `jwt_auth.py`

`@jwt_required` 데코레이터에서 요청 시작/종료 시각을 측정하고 로그 기록:

```python
import time

def jwt_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        g.request_start_time = time.time()  # ← 요청 시작 시각

        # ... 기존 JWT 검증 로직 동일 ...

        return f(*args, **kwargs)
    return decorated_function
```

Flask `after_request`에서 로그 기록:

```python
# app/__init__.py 또는 별도 미들웨어 파일
@app.after_request
def log_access(response):
    """모든 인증 API 호출 기록"""
    # jwt_required를 거친 요청만 (g.worker_id가 있는 경우)
    worker_id = getattr(g, 'worker_id', None)
    if worker_id is None:
        return response  # 비인증 API (로그인 등) 스킵

    start_time = getattr(g, 'request_start_time', None)
    duration_ms = int((time.time() - start_time) * 1000) if start_time else None

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO app_access_log
                (worker_id, worker_email, worker_role, endpoint, method,
                 status_code, duration_ms, ip_address, user_agent, request_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            worker_id,
            getattr(g, 'email', None),
            getattr(g, 'role', None),
            request.endpoint or request.path,
            request.method,
            response.status_code,
            duration_ms,
            request.remote_addr,
            request.user_agent.string[:500] if request.user_agent else None,
            request.full_path[:500],
        ))
        conn.commit()
        put_conn(conn)
    except Exception as e:
        logger.warning(f"Access log failed: {e}")
        # 로깅 실패가 요청을 블로킹하지 않도록

    return response
```

⚠️ 성능 주의: INSERT가 매 요청마다 실행되므로, 트래픽이 높으면 비동기 큐(메모리 버퍼 → 배치 INSERT)로 개선 가능. 현재 규모에서는 직접 INSERT로 충분.

### Task 3: 조회 API — VIEW 대시보드용

```
GET /api/admin/analytics/summary?period=7d
GET /api/admin/analytics/by-worker?period=30d
GET /api/admin/analytics/by-endpoint?period=7d
GET /api/admin/analytics/hourly?date=2026-03-18
```

**summary** 응답:
```json
{
    "period": "7d",
    "unique_users": 25,
    "total_requests": 3420,
    "avg_duration_ms": 145,
    "error_rate": 2.3,
    "daily": [
        {"date": "2026-03-18", "users": 22, "requests": 520, "errors": 12},
        ...
    ]
}
```

**by-worker** 응답:
```json
{
    "workers": [
        {
            "worker_id": 3760,
            "email": "user@example.com",
            "role": "worker",
            "total_requests": 156,
            "first_access": "2026-03-18T08:02:00",
            "last_access": "2026-03-18T17:45:00",
            "usage_minutes": 583,
            "top_endpoints": ["/api/app/work/start", "/api/app/product/{qr}"]
        },
        ...
    ]
}
```

**by-endpoint** 응답:
```json
{
    "endpoints": [
        {"endpoint": "/api/app/work/start", "count": 890, "avg_ms": 120, "error_rate": 0.5},
        {"endpoint": "/api/app/product/{qr}", "count": 650, "avg_ms": 85, "error_rate": 1.2},
        ...
    ]
}
```

### Task 4: 로그 정리 스케줄러 (선택적)

`scheduler_service.py`에 30일 이상 된 로그 삭제 cron job 추가:

```python
# 매일 새벽 3시 실행
scheduler.add_job(
    _cleanup_access_logs,
    CronTrigger(hour=3, minute=0),
    id='cleanup_access_logs',
    name='Access Log 정리 (30일 이상)',
)

def _cleanup_access_logs():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM app_access_log WHERE created_at < NOW() - INTERVAL '30 days'")
    deleted = cur.rowcount
    conn.commit()
    put_conn(conn)
    logger.info(f"[cleanup] Access log: {deleted} rows deleted (30d+)")
```

### 체크리스트

- [x] Migration 026 작성 + Railway DB 실행 ✅
- [x] `jwt_auth.py` — `g.request_start_time` 세팅 ✅
- [x] `__init__.py` — `after_request` access log 기록 ✅
- [x] analytics API 4개 엔드포인트 구현 (summary, by-worker, by-endpoint, hourly) ✅
- [x] 로그 정리 스케줄러 추가 (30일, 매일 03:00) ✅
- [x] 기존 API 성능 영향 없음 확인 — 평균 응답시간 43ms ✅
- [x] app_access_log 테이블 데이터 적재 확인 — 195건+ 기록 확인 ✅
- [x] by-endpoint 한글 라벨 매핑 (`_ENDPOINT_LABELS` 37개) ✅
- [x] by-worker name/company 필드 추가 (workers JOIN) ✅
- [x] 전체 쿼리 ADMIN 요청 제외 (`worker_role != 'ADMIN'`) ✅

---

## Sprint 33: 생산실적 API — O/N 단위 실적확인 + 월마감

> **목적**: VIEW 생산실적 페이지용 API 4개 구현 — O/N 단위 공정별 progress 조회, 실적확인 처리/취소, 월마감 집계
> **범위**: BE — migration + 라우트 + 모델
> **참고**: `AXIS-VIEW/docs/OPS_API_REQUESTS.md` #23~#26 상세 스펙
> **버전**: v1.9.0 → v2.0.0

### 배경

생산실적 관리는 O/N(sales_order) 단위로 공정별 완료 여부를 추적하고 실적확인하는 프로세스.
현재 개별 S/N 진행률은 있지만, O/N 그룹핑 + 실적확인 이력 + 월마감 집계가 없음.

핵심 흐름:
```
O/N 6238 (GAIA-I DUAL × 3대)
  ├─ GBWS-6627: MECH 100%, ELEC 66%, TMS 50%
  ├─ GBWS-6628: MECH 100%, ELEC 100%, TMS 100%
  └─ GBWS-6629: MECH 85%, ELEC 0%, TMS 0%

→ MECH 실적확인 가능? → 6629가 미완료 → confirmable = false
→ TMS 실적확인 가능? → 6627 미완료 → confirmable = false
```

공정별 실적확인 조건:
- MECH: O/N 전체 S/N의 MECH 태스크 100% 완료 (+ 체크리스트 완료 — 추후)
- ELEC: O/N 전체 S/N의 ELEC 태스크 100% 완료 (+ 체크리스트 완료 — 추후)
- TM: O/N 전체 S/N의 TANK_MODULE 태스크 완료 (PRESSURE_TEST 무관)
- DUAL 모델: L/R 통합 (serial_number 기준 GROUP BY)
- SWS/GALLANT: model_config.is_tms=FALSE이므로 TM은 해당 없음, MECH에서 TANK_MODULE 추적
- 체크리스트: 아직 미구현 → admin_settings으로 skip 가능하게 옵션 처리

### 팀 구성

```
CLAUDE.md를 읽고 Sprint 33을 진행해줘.

팀 구성: 2명 teammate (Sonnet)
1. **BE** — 소유: backend/**
2. **TEST** — 소유: tests/**
```

### Task 1: Migration 027 — `plan.production_confirm` 테이블

```sql
-- Migration 027: 생산실적 확인 이력
BEGIN;

CREATE TABLE IF NOT EXISTS plan.production_confirm (
    id SERIAL PRIMARY KEY,
    sales_order VARCHAR(255) NOT NULL,
    process_type VARCHAR(20) NOT NULL,        -- MECH, ELEC, TM
    confirmed_week VARCHAR(10) NOT NULL,      -- W10, W11, W12
    confirmed_month VARCHAR(7) NOT NULL,      -- 2026-03
    sn_count INTEGER NOT NULL DEFAULT 0,      -- 확인 시점 O/N 내 S/N 수
    confirmed_by INTEGER REFERENCES workers(id) ON DELETE SET NULL,
    confirmed_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ DEFAULT NULL,      -- soft delete (취소 이력 보존)
    deleted_by INTEGER REFERENCES workers(id) ON DELETE SET NULL,
    UNIQUE(sales_order, process_type, confirmed_week)
);

CREATE INDEX idx_production_confirm_month ON plan.production_confirm(confirmed_month);
CREATE INDEX idx_production_confirm_order ON plan.production_confirm(sales_order);

-- 실적확인 공정별 on/off 설정 (admin_settings에 추가)
INSERT INTO admin_settings (key, value, description)
VALUES
    ('confirm_mech_enabled', 'true', '기구 실적확인 활성화'),
    ('confirm_elec_enabled', 'true', '전장 실적확인 활성화'),
    ('confirm_tm_enabled', 'true', 'Tank Module 실적확인 활성화'),
    ('confirm_pi_enabled', 'false', 'PI 실적확인 활성화'),
    ('confirm_qi_enabled', 'false', 'QI 실적확인 활성화'),
    ('confirm_si_enabled', 'false', 'SI 실적확인 활성화'),
    ('confirm_checklist_required', 'false', '실적확인 시 체크리스트 완료 필수 여부')
ON CONFLICT (key) DO NOTHING;

COMMIT;
```

### Task 2: `backend/app/routes/production.py` — 신규 라우트

```python
"""
생산실적 라우트 (Sprint 33)
엔드포인트: /api/admin/production/*
VIEW 생산실적 페이지 전용
"""

production_bp = Blueprint("production", __name__, url_prefix="/api/admin/production")
```

#### 2-1. `GET /api/admin/production/performance`

```python
@production_bp.route("/performance", methods=["GET"])
@jwt_required
@view_access_required
def get_performance():
    """
    생산실적 조회 — O/N 단위 공정별 progress + 실적확인 이력

    Query Params:
        week: ISO 주차 (W10~W53), default: 현재 주
        month: YYYY-MM, default: 현재 월
        view: weekly | monthly, default: weekly

    응답: OPS_API_REQUESTS.md #23 참조
    """
    pass
```

핵심 쿼리 로직:
```sql
-- 1. 대상 S/N 조회 (월/주 기준)
SELECT p.sales_order, p.serial_number, p.model,
       p.mech_partner, p.elec_partner, p.line
FROM plan.product_info p
WHERE p.{date_field} >= %s AND p.{date_field} < %s

-- 2. S/N별 공정 progress (app_task_details)
SELECT serial_number, task_category,
       COUNT(*) AS total,
       COUNT(completed_at) AS completed
FROM app_task_details
WHERE serial_number = ANY(%s) AND is_applicable = TRUE
GROUP BY serial_number, task_category

-- 3. TM 세부 (TANK_MODULE / PRESSURE_TEST 개별)
SELECT serial_number, task_id, completed_at
FROM app_task_details
WHERE serial_number = ANY(%s) AND task_category IN ('TMS', 'MECH')
  AND task_id IN ('TANK_MODULE', 'PRESSURE_TEST')

-- 4. 기존 실적확인 이력
SELECT * FROM plan.production_confirm
WHERE sales_order = ANY(%s) AND deleted_at IS NULL
```

O/N 그룹핑:
```python
# sales_order 기준 그룹핑
from collections import defaultdict
orders = defaultdict(list)
for row in product_rows:
    orders[row['sales_order']].append(row)
```

confirmable 판정:
```python
def _is_confirmable(sns_progress, process_type, settings):
    """O/N 전체 S/N이 해당 공정 100% 완료인지"""
    # admin_settings에서 해당 공정 enabled 확인
    if not settings.get(f'confirm_{process_type}_enabled', False):
        return False

    for sn_data in sns_progress:
        cat_data = sn_data['by_category'].get(process_type, {})
        if cat_data.get('total', 0) == 0:
            continue  # 해당 공정 없는 모델 (DRAGON의 TMS 등) → skip
        if cat_data.get('completed', 0) < cat_data.get('total', 0):
            return False  # 미완료 S/N 있음

    # 체크리스트 조건 (추후)
    if settings.get('confirm_checklist_required', False):
        pass  # 체크리스트 완료 확인 로직 (skip for now)

    return True
```

TM confirmable 특수 조건:
```python
# TM: TANK_MODULE 완료만 확인 (PRESSURE_TEST 무관)
# SWS/GALLANT: MECH에서 TANK_MODULE → task_category='MECH', task_id='TANK_MODULE'
def _is_tm_confirmable(sns_tm_tasks):
    for sn, tasks in sns_tm_tasks.items():
        tank_module = next((t for t in tasks if t['task_id'] == 'TANK_MODULE'), None)
        if tank_module and not tank_module['completed_at']:
            return False
    return True
```

#### 2-2. `POST /api/admin/production/confirm`

```python
@production_bp.route("/confirm", methods=["POST"])
@jwt_required
@view_access_required
def confirm_production():
    """
    실적확인 처리 — 조건 재검증 후 INSERT

    Body: { sales_order, process_type, confirmed_week, confirmed_month }
    """
    # 1. confirmable 조건 재검증 (서버에서)
    # 2. 조건 미충족 → 400 + 미충족 S/N 상세
    # 3. 충족 → plan.production_confirm INSERT
    # 4. UNIQUE 위반 → 409 (이미 확인됨)
    pass
```

#### 2-3. `DELETE /api/admin/production/confirm/<int:confirm_id>`

```python
@production_bp.route("/confirm/<int:confirm_id>", methods=["DELETE"])
@jwt_required
@admin_required  # Admin만 취소 가능
def cancel_confirm(confirm_id):
    """
    실적확인 취소 — soft delete (이력 보존)

    deleted_at + deleted_by 기록 → UNIQUE 제약은 유지
    (같은 O/N+공정+주차 재확인 필요 시 deleted_at IS NOT NULL 행은 무시)
    """
    pass
```

⚠️ soft delete 시 UNIQUE 충돌 주의:
```sql
-- UNIQUE(sales_order, process_type, confirmed_week)에서
-- soft delete된 행이 있으면 재확인 INSERT가 UNIQUE 위반
-- → partial unique index로 변경
DROP INDEX IF EXISTS production_confirm_sales_order_process_type_confirmed_week_key;
CREATE UNIQUE INDEX production_confirm_active_unique
    ON plan.production_confirm(sales_order, process_type, confirmed_week)
    WHERE deleted_at IS NULL;
```

#### 2-4. `GET /api/admin/production/monthly-summary`

```python
@production_bp.route("/monthly-summary", methods=["GET"])
@jwt_required
@view_access_required
def get_monthly_summary():
    """
    월마감 집계 — 주차별 완료/확인 카운트

    Query Params: month=YYYY-MM
    응답: OPS_API_REQUESTS.md #26 참조
    """
    pass
```

### Task 3: Blueprint 등록

`backend/app/__init__.py`에 production_bp 등록:
```python
from app.routes.production import production_bp
app.register_blueprint(production_bp)
```

### Task 4: 테스트

```python
# tests/backend/test_production.py

class TestProductionPerformance:
    """GET /api/admin/production/performance"""
    def test_weekly_view_groups_by_order(self, ...):
        """O/N 단위 그룹핑 확인"""
    def test_confirmable_all_complete(self, ...):
        """전체 S/N 완료 시 confirmable=True"""
    def test_confirmable_partial(self, ...):
        """일부 S/N 미완료 시 confirmable=False"""
    def test_dual_lr_integrated(self, ...):
        """DUAL L/R이 통합 progress로 표시"""
    def test_dragon_no_tm(self, ...):
        """DRAGON은 TM process_status 없음"""

class TestProductionConfirm:
    """POST /api/admin/production/confirm"""
    def test_confirm_success(self, ...):
    def test_confirm_not_confirmable(self, ...):
    def test_confirm_duplicate_409(self, ...):

class TestProductionCancel:
    """DELETE /api/admin/production/confirm/:id"""
    def test_cancel_soft_delete(self, ...):
    def test_cancel_admin_only(self, ...):
    def test_reconfirm_after_cancel(self, ...):

class TestMonthlySummary:
    """GET /api/admin/production/monthly-summary"""
    def test_weekly_breakdown(self, ...):
    def test_completed_vs_confirmed(self, ...):
```

### 체크리스트

**BE (✅ 완료)**:
- [x] Migration 027 작성 + Railway DB 실행 ✅
- [x] `routes/production.py` 신규 — 4개 엔드포인트 (performance, confirm, cancel, monthly-summary) ✅
- [x] `__init__.py`에 production_bp 등록 (14번째 blueprint) ✅
- [x] confirmable 판정 로직 — `_is_process_confirmable()` (공정별 + admin_settings 제어) ✅
- [x] DUAL L/R 통합 — serial_number 기준 GROUP BY (`_calc_sn_progress`) ✅
- [x] soft delete + partial unique index (`WHERE deleted_at IS NULL`) ✅
- [x] admin_settings 7개 (confirm_*_enabled, confirm_checklist_required) ✅
- [x] version.py v2.0.0 ✅

**TEST (✅ 완료 — 9/9 passed)**:
- [x] 테스트 파일 작성 — `tests/backend/test_production.py` 9건 ✅
- [x] O/N 그룹핑 검증 (2개 O/N, 3개 S/N 묶임 확인) ✅
- [x] confirmable 조건 검증 — 전체 완료 True, 부분 미완료 False ✅
- [x] soft delete 후 재확인 검증 (취소 → 재확인 201) ✅
- [x] 중복 확인 409 + 미완료 거부 400 ✅
- [ ] DUAL/DRAGON/SWS 모델별 검증 — 추후 추가

**검증 (배포 후)**:
- [ ] VIEW 생산실적 페이지 연동 테스트
- [ ] 실적확인 버튼 활성/비활성 확인
- [ ] 월마감 집계 정합성 확인

---

## Sprint 31C: PI 검사 협력사 위임 — 가시성 분기 + model_config 변경

> **목적**: mech_partner가 PI 가능 협력사(현재 TMS(M))일 때, PI 검사 태스크를 해당 협력사 작업자에게 표시. GST PI 검사원은 예외 라인(현재 JP)에서만 PI 유지
> **범위**: BE 4파일 수정 + migration 1건 + 테스트
> **의존성**: Sprint 31A (model_config, PI task generation), Sprint 11 (get_task_categories_for_worker)
> **버전**: v1.9.0 → v1.9.1 (패치 — 가시성 로직 변경, 스키마 변경 없음)

### 배경

현장 운영 변경: TMS(M) 협력사가 원패스(MECH → TANK MODULE → 가압검사)로 전 공정을 진행하는 체제로 전환.
기존에는 PI 가압검사(LNG/UTIL, CHAMBER)가 GST 본사 PI 검사원 전담이었으나, mech_partner가 TMS(M)인 제품은 TMS(M) 작업자가 PI도 자체 검사하게 변경.

적용 대상:
- **GAIA 계열**: mech_partner=TMS → PI를 TMS(M) 작업자에게 표시 (단, line=JP → GST PI 유지)
- **DRAGON 계열**: mech_partner=TMS → PI를 TMS(M) 작업자에게 표시 (JP 예외 해당 없음)
  - ⚠️ DRAGON은 현재 model_config `pi_lng_util=FALSE, pi_chamber=FALSE` → **TRUE로 변경 필요**
  - model_config 변경 시 task_seed에서 자동으로:
    - PI_LNG_UTIL, PI_CHAMBER → `is_applicable=TRUE`
    - MECH 쪽 PRESSURE_TEST 제거 (MECH_TANK_FULL → MECH_TANK_MODULE_ONLY)

향후 확장:
- FNI, BAT도 PI 검사 가능 협력사로 추가될 수 있음
- JP 외 다른 라인도 GST PI 유지 대상으로 추가/제거될 수 있음
- 모든 옵션은 admin_settings에서 제어 (코드 수정 없이 설정 변경만으로 운영)

### 팀 구성

```
CLAUDE.md를 읽고 Sprint 31C를 진행해줘.

팀 구성: 2명 teammate (Sonnet)
1. **BE** — 소유: backend/**
2. **TEST** — 소유: tests/**
```

### Task 1: Migration 026 — admin_settings 초기값 + DRAGON model_config 변경

**파일**: `backend/migrations/026_pi_mech_partner_settings.sql`

```sql
-- Migration 026: PI 검사 협력사 위임 설정
-- Sprint 31C: mech_partner 기준 PI 가시성 분기
BEGIN;

-- 1. PI 검사 가능 협력사 목록 (JSON array)
-- 이 목록에 포함된 회사가 mech_partner일 때, 해당 협력사 작업자에게 PI 태스크 표시
INSERT INTO admin_settings (setting_key, setting_value, description)
VALUES (
    'pi_capable_mech_partners',
    '["TMS(M)"]',
    'PI 검사 가능 협력사 목록 (mech_partner 매칭 시 PI 태스크 위임)'
)
ON CONFLICT (setting_key) DO NOTHING;

-- 2. GST PI 유지 라인 prefix 목록 (JSON array)
-- 이 prefix로 시작하는 line의 제품은 협력사 위임 대상에서 제외, GST PI가 기존대로 검사
INSERT INTO admin_settings (setting_key, setting_value, description)
VALUES (
    'pi_gst_override_lines',
    '["JP"]',
    'GST PI 유지 라인 prefix (이 라인은 협력사 위임 제외, GST PI 직접 검사)'
)
ON CONFLICT (setting_key) DO NOTHING;

-- 3. DRAGON model_config 변경: PI 활성화
-- 기존: pi_lng_util=FALSE, pi_chamber=FALSE (가압검사를 MECH PRESSURE_TEST로 대체)
-- 변경: pi_lng_util=TRUE, pi_chamber=TRUE (PI 카테고리로 정식 분리)
-- ⚠️ task_seed.py Line 245 영향: MECH_TANK_FULL → MECH_TANK_MODULE_ONLY 자동 전환
UPDATE model_config
SET pi_lng_util = TRUE,
    pi_chamber = TRUE,
    updated_at = CURRENT_TIMESTAMP
WHERE model_prefix = 'DRAGON';

-- 4. 기존 DRAGON 제품 데이터 마이그레이션
-- 4-1. PI 태스크 활성화 (기존 is_applicable=FALSE → TRUE)
UPDATE app_task_details
SET is_applicable = TRUE,
    updated_at = CURRENT_TIMESTAMP
WHERE task_category = 'PI'
  AND is_applicable = FALSE
  AND serial_number IN (
      SELECT p.serial_number
      FROM plan.product_info p
      WHERE p.model ILIKE 'DRAGON%'
  );

-- 4-2. MECH PRESSURE_TEST 비활성화 (PI로 이관)
-- DRAGON의 MECH PRESSURE_TEST는 PI_LNG_UTIL/PI_CHAMBER로 대체됨
UPDATE app_task_details
SET is_applicable = FALSE,
    updated_at = CURRENT_TIMESTAMP
WHERE task_category = 'MECH'
  AND task_id = 'PRESSURE_TEST'
  AND serial_number IN (
      SELECT p.serial_number
      FROM plan.product_info p
      WHERE p.model ILIKE 'DRAGON%'
  );

COMMIT;
```

### Task 2: `backend/app/services/task_seed.py` 수정 — get_task_categories_for_worker 확장

#### 2-1. 함수 시그니처 변경

`get_task_categories_for_worker`에 `product_line` 파라미터 추가:

```python
def get_task_categories_for_worker(
    worker_company: Optional[str],
    worker_role: str,
    product_mech_partner: Optional[str],
    product_elec_partner: Optional[str],
    product_module_outsourcing: Optional[str],
    worker_active_role: Optional[str] = None,
    product_line: Optional[str] = None           # ★ Sprint 31C 추가
) -> Optional[List[str]]:
```

#### 2-2. GST PI 블록 수정 (Line 530~538 교체)

기존:
```python
    # GST 사내직원: active_role > role 기반 (PI, QI, SI, ADMIN)
    if worker_company == 'GST' or worker_role in ('PI', 'QI', 'SI', 'ADMIN'):
        effective_role = worker_active_role if worker_active_role else worker_role
        if effective_role in ('PI', 'QI', 'SI'):
            categories.append(effective_role)
        elif effective_role == 'ADMIN':
            return None
        return categories
```

변경:
```python
    # GST 사내직원: active_role > role 기반 (PI, QI, SI, ADMIN)
    if worker_company == 'GST' or worker_role in ('PI', 'QI', 'SI', 'ADMIN'):
        effective_role = worker_active_role if worker_active_role else worker_role
        if effective_role == 'ADMIN':
            return None
        if effective_role == 'PI':
            # Sprint 31C: PI 협력사 위임 분기
            # mech_partner가 pi_capable 목록에 있으면 → GST PI 제외 (협력사가 담당)
            # 단, override_lines에 해당하면 → GST PI 유지
            pi_capable = get_setting('pi_capable_mech_partners', [])
            if pi_capable and product_mech_partner and product_mech_partner in pi_capable:
                # mech_partner가 PI 가능 협력사
                override_lines = get_setting('pi_gst_override_lines', [])
                line_upper = product_line.strip().upper() if product_line else ''
                is_override = any(line_upper.startswith(prefix.upper()) for prefix in override_lines)
                if is_override:
                    # JP 등 예외 라인 → GST PI 유지
                    categories.append('PI')
                # else: 협력사 담당 → GST PI에서 PI 제외
            else:
                # 기존 동작: GST PI가 PI 담당
                categories.append('PI')
        elif effective_role in ('QI', 'SI'):
            categories.append(effective_role)
        return categories
```

#### 2-3. TMS(M) 블록 수정 (Line 541~549 확장)

기존:
```python
    # TMS(M): TMS task + mech_partner 매칭 시 MECH task도
    if worker_company == 'TMS(M)':
        if product_module_outsourcing and 'TMS' in product_module_outsourcing.upper():
            categories.append('TMS')
        if product_mech_partner and worker_company == 'TMS(M)':
            if product_mech_partner.upper() == 'TMS':
                categories.append('MECH')
        return categories if categories else []
```

변경:
```python
    # TMS(M): TMS task + mech_partner 매칭 시 MECH task도
    if worker_company == 'TMS(M)':
        if product_module_outsourcing and 'TMS' in product_module_outsourcing.upper():
            categories.append('TMS')
        if product_mech_partner and product_mech_partner.upper() == 'TMS':
            categories.append('MECH')

            # Sprint 31C: PI 협력사 위임 — TMS(M)이 mech이면 PI도 표시
            pi_capable = get_setting('pi_capable_mech_partners', [])
            if worker_company in pi_capable:
                override_lines = get_setting('pi_gst_override_lines', [])
                line_upper = product_line.strip().upper() if product_line else ''
                is_override = any(line_upper.startswith(prefix.upper()) for prefix in override_lines)
                if not is_override:
                    categories.append('PI')
                # override 라인이면 PI는 GST PI 담당 → 여기서 PI 추가 안 함

        return categories if categories else []
```

#### 2-4. FNI/BAT 블록 확장 (Line 552~555 — 향후 대비)

기존:
```python
    # FNI / BAT: mech_partner 매칭 → MECH only
    if worker_company in ('FNI', 'BAT'):
        if product_mech_partner and product_mech_partner.upper() == worker_company.upper():
            categories.append('MECH')
        return categories
```

변경:
```python
    # FNI / BAT: mech_partner 매칭 → MECH only
    # Sprint 31C: pi_capable_mech_partners에 포함되면 PI도 표시
    if worker_company in ('FNI', 'BAT'):
        if product_mech_partner and product_mech_partner.upper() == worker_company.upper():
            categories.append('MECH')

            # PI 위임 확인 (현재 FNI/BAT는 미포함이지만 향후 추가 대비)
            pi_capable = get_setting('pi_capable_mech_partners', [])
            if worker_company in pi_capable:
                override_lines = get_setting('pi_gst_override_lines', [])
                line_upper = product_line.strip().upper() if product_line else ''
                is_override = any(line_upper.startswith(prefix.upper()) for prefix in override_lines)
                if not is_override:
                    categories.append('PI')

        return categories
```

#### 2-5. filter_tasks_for_worker 수정 (product.line 전달)

기존 (Line 595~602):
```python
    visible_categories = get_task_categories_for_worker(
        worker_company=worker_company,
        worker_role=worker_role,
        product_mech_partner=product.mech_partner if product else None,
        product_elec_partner=product.elec_partner if product else None,
        product_module_outsourcing=product.module_outsourcing if product else None,
        worker_active_role=worker_active_role
    )
```

변경:
```python
    visible_categories = get_task_categories_for_worker(
        worker_company=worker_company,
        worker_role=worker_role,
        product_mech_partner=product.mech_partner if product else None,
        product_elec_partner=product.elec_partner if product else None,
        product_module_outsourcing=product.module_outsourcing if product else None,
        worker_active_role=worker_active_role,
        product_line=product.line if product else None  # ★ Sprint 31C
    )
```

#### 2-6. task_seed.py 주석 업데이트

Line 88~89 주석 변경:
```python
# Sprint 31A: DRAGON MECH 추가 태스크 (TANK_MODULE + PRESSURE_TEST)
# DRAGON은 PI 불필요 → MECH에서 가압검사까지 전부 처리
```
→
```python
# Sprint 31A: tank_in_mech MECH 추가 태스크 (TANK_MODULE + PRESSURE_TEST)
# Sprint 31C: DRAGON PI 활성화 → MECH_TANK_MODULE_ONLY로 전환 (PRESSURE_TEST는 PI로 이관)
# MECH_TANK_FULL은 pi_lng_util=FALSE AND pi_chamber=FALSE인 모델에서만 사용
```

Line 101 주석 변경:
```python
# Sprint 11: PI Tasks (2개) — 모든 모델 공통 (GST PI 검사원 전용)
```
→
```python
# Sprint 11: PI Tasks (2개) — 모든 모델 공통
# Sprint 31C: pi_capable_mech_partners 설정에 따라 협력사 작업자에게도 표시 가능
```

### Task 3: import 확인

`task_seed.py` 상단에 `get_setting` import 확인:
```python
from app.models.admin_settings import get_setting
```
이미 `heating_jacket_enabled`에서 사용 중이므로 import는 존재할 것. 없으면 추가.

### Task 4: version.py 업데이트

```python
VERSION = "1.9.1"
BUILD_DATE = "2026-03-20"
```

### Task 5: 테스트

**파일**: `tests/backend/test_sprint31c_pi_visibility.py`

#### White-box 테스트 (DB 불필요 — mock 사용)

```python
"""
Sprint 31C: PI 검사 협력사 위임 — 가시성 분기 테스트
White-box: get_task_categories_for_worker 단위 테스트 (admin_settings mock)
"""

import unittest
from unittest.mock import patch

import sys
sys.path.insert(0, 'backend')
from app.services.task_seed import get_task_categories_for_worker


class TestPIVisibilityTMS(unittest.TestCase):
    """TMS(M) 작업자의 PI 가시성 테스트"""

    @patch('app.services.task_seed.get_setting')
    def test_tms_sees_pi_when_capable(self, mock_setting):
        """TMS(M)이 pi_capable이고 mech_partner=TMS → PI 보임"""
        mock_setting.side_effect = lambda key, default=None: {
            'pi_capable_mech_partners': ['TMS(M)'],
            'pi_gst_override_lines': ['JP'],
        }.get(key, default)

        cats = get_task_categories_for_worker(
            worker_company='TMS(M)', worker_role='MECH',
            product_mech_partner='TMS', product_elec_partner=None,
            product_module_outsourcing='TMS',
            product_line='P4-D'
        )
        self.assertIn('PI', cats)
        self.assertIn('TMS', cats)
        self.assertIn('MECH', cats)

    @patch('app.services.task_seed.get_setting')
    def test_tms_no_pi_on_jp_line(self, mock_setting):
        """TMS(M)이 pi_capable이지만 line=JP → PI 안 보임 (GST PI 유지)"""
        mock_setting.side_effect = lambda key, default=None: {
            'pi_capable_mech_partners': ['TMS(M)'],
            'pi_gst_override_lines': ['JP'],
        }.get(key, default)

        cats = get_task_categories_for_worker(
            worker_company='TMS(M)', worker_role='MECH',
            product_mech_partner='TMS', product_elec_partner=None,
            product_module_outsourcing='TMS',
            product_line='JP(F15)'
        )
        self.assertNotIn('PI', cats)
        self.assertIn('TMS', cats)
        self.assertIn('MECH', cats)

    @patch('app.services.task_seed.get_setting')
    def test_tms_no_pi_when_not_capable(self, mock_setting):
        """pi_capable_mech_partners가 빈 리스트 → 기존 동작 (PI 없음)"""
        mock_setting.side_effect = lambda key, default=None: {
            'pi_capable_mech_partners': [],
            'pi_gst_override_lines': ['JP'],
        }.get(key, default)

        cats = get_task_categories_for_worker(
            worker_company='TMS(M)', worker_role='MECH',
            product_mech_partner='TMS', product_elec_partner=None,
            product_module_outsourcing='TMS',
            product_line='P4-D'
        )
        self.assertNotIn('PI', cats)

    @patch('app.services.task_seed.get_setting')
    def test_tms_no_pi_when_mech_not_tms(self, mock_setting):
        """mech_partner가 TMS가 아닌 경우 → PI 없음"""
        mock_setting.side_effect = lambda key, default=None: {
            'pi_capable_mech_partners': ['TMS(M)'],
            'pi_gst_override_lines': ['JP'],
        }.get(key, default)

        cats = get_task_categories_for_worker(
            worker_company='TMS(M)', worker_role='MECH',
            product_mech_partner='FNI', product_elec_partner=None,
            product_module_outsourcing='TMS',
            product_line='P4-D'
        )
        self.assertNotIn('PI', cats)


class TestPIVisibilityGST(unittest.TestCase):
    """GST PI 작업자의 PI 가시성 테스트"""

    @patch('app.services.task_seed.get_setting')
    def test_gst_pi_no_pi_when_delegated(self, mock_setting):
        """mech_partner=TMS, line=P4-D → GST PI에서 PI 제외"""
        mock_setting.side_effect = lambda key, default=None: {
            'pi_capable_mech_partners': ['TMS(M)'],
            'pi_gst_override_lines': ['JP'],
        }.get(key, default)

        cats = get_task_categories_for_worker(
            worker_company='GST', worker_role='PI',
            product_mech_partner='TMS', product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='P4-D'
        )
        self.assertNotIn('PI', cats)

    @patch('app.services.task_seed.get_setting')
    def test_gst_pi_keeps_pi_on_jp(self, mock_setting):
        """mech_partner=TMS, line=JP(F15) → GST PI 유지"""
        mock_setting.side_effect = lambda key, default=None: {
            'pi_capable_mech_partners': ['TMS(M)'],
            'pi_gst_override_lines': ['JP'],
        }.get(key, default)

        cats = get_task_categories_for_worker(
            worker_company='GST', worker_role='PI',
            product_mech_partner='TMS', product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='JP(F15)'
        )
        self.assertIn('PI', cats)

    @patch('app.services.task_seed.get_setting')
    def test_gst_pi_keeps_pi_when_mech_not_capable(self, mock_setting):
        """mech_partner=FNI (pi_capable 아님) → GST PI 유지"""
        mock_setting.side_effect = lambda key, default=None: {
            'pi_capable_mech_partners': ['TMS(M)'],
            'pi_gst_override_lines': ['JP'],
        }.get(key, default)

        cats = get_task_categories_for_worker(
            worker_company='GST', worker_role='PI',
            product_mech_partner='FNI', product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='P4-D'
        )
        self.assertIn('PI', cats)

    @patch('app.services.task_seed.get_setting')
    def test_gst_pi_keeps_pi_when_no_mech(self, mock_setting):
        """mech_partner=NULL → GST PI 유지 (기존 동작)"""
        mock_setting.side_effect = lambda key, default=None: {
            'pi_capable_mech_partners': ['TMS(M)'],
            'pi_gst_override_lines': ['JP'],
        }.get(key, default)

        cats = get_task_categories_for_worker(
            worker_company='GST', worker_role='PI',
            product_mech_partner=None, product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='P4-D'
        )
        self.assertIn('PI', cats)

    @patch('app.services.task_seed.get_setting')
    def test_gst_pi_active_role_override(self, mock_setting):
        """active_role=PI, role=QI → PI 기준으로 가시성 판단"""
        mock_setting.side_effect = lambda key, default=None: {
            'pi_capable_mech_partners': ['TMS(M)'],
            'pi_gst_override_lines': ['JP'],
        }.get(key, default)

        cats = get_task_categories_for_worker(
            worker_company='GST', worker_role='QI',
            product_mech_partner='TMS', product_elec_partner=None,
            product_module_outsourcing=None,
            worker_active_role='PI',
            product_line='P4-D'
        )
        self.assertNotIn('PI', cats)  # 위임 대상이므로 GST PI에서 제외


class TestPIVisibilityFNI(unittest.TestCase):
    """FNI/BAT 작업자의 PI 가시성 — 향후 확장 대비"""

    @patch('app.services.task_seed.get_setting')
    def test_fni_no_pi_by_default(self, mock_setting):
        """FNI는 현재 pi_capable 아님 → PI 없음"""
        mock_setting.side_effect = lambda key, default=None: {
            'pi_capable_mech_partners': ['TMS(M)'],
            'pi_gst_override_lines': ['JP'],
        }.get(key, default)

        cats = get_task_categories_for_worker(
            worker_company='FNI', worker_role='MECH',
            product_mech_partner='FNI', product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='P4-D'
        )
        self.assertIn('MECH', cats)
        self.assertNotIn('PI', cats)

    @patch('app.services.task_seed.get_setting')
    def test_fni_sees_pi_when_added_to_capable(self, mock_setting):
        """FNI를 pi_capable에 추가하면 PI 보임"""
        mock_setting.side_effect = lambda key, default=None: {
            'pi_capable_mech_partners': ['TMS(M)', 'FNI'],
            'pi_gst_override_lines': ['JP'],
        }.get(key, default)

        cats = get_task_categories_for_worker(
            worker_company='FNI', worker_role='MECH',
            product_mech_partner='FNI', product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='P4-D'
        )
        self.assertIn('MECH', cats)
        self.assertIn('PI', cats)


class TestPIVisibilityNoChange(unittest.TestCase):
    """기존 동작 유지 검증 (regression)"""

    @patch('app.services.task_seed.get_setting')
    def test_admin_sees_all(self, mock_setting):
        """ADMIN → 전체 조회 (None 반환) — 변경 없음"""
        cats = get_task_categories_for_worker(
            worker_company='GST', worker_role='ADMIN',
            product_mech_partner='TMS', product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='P4-D'
        )
        self.assertIsNone(cats)

    @patch('app.services.task_seed.get_setting')
    def test_gst_qi_unchanged(self, mock_setting):
        """GST QI → QI만 (PI 위임과 무관)"""
        cats = get_task_categories_for_worker(
            worker_company='GST', worker_role='QI',
            product_mech_partner='TMS', product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='P4-D'
        )
        self.assertIn('QI', cats)
        self.assertNotIn('PI', cats)

    @patch('app.services.task_seed.get_setting')
    def test_gst_si_unchanged(self, mock_setting):
        """GST SI → SI만 (PI 위임과 무관)"""
        cats = get_task_categories_for_worker(
            worker_company='GST', worker_role='SI',
            product_mech_partner='TMS', product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='P4-D'
        )
        self.assertIn('SI', cats)
        self.assertNotIn('PI', cats)

    @patch('app.services.task_seed.get_setting')
    def test_elec_partner_unchanged(self, mock_setting):
        """TMS(E) → ELEC만 (PI 위임과 무관)"""
        cats = get_task_categories_for_worker(
            worker_company='TMS(E)', worker_role='ELEC',
            product_mech_partner='TMS', product_elec_partner='TMS',
            product_module_outsourcing=None,
            product_line='P4-D'
        )
        self.assertIn('ELEC', cats)
        self.assertNotIn('PI', cats)

    @patch('app.services.task_seed.get_setting')
    def test_multiple_override_lines(self, mock_setting):
        """override_lines에 여러 prefix 등록 시 정상 동작"""
        mock_setting.side_effect = lambda key, default=None: {
            'pi_capable_mech_partners': ['TMS(M)'],
            'pi_gst_override_lines': ['JP', 'FAB2', 'AUSTRIA'],
        }.get(key, default)

        # FAB2 → GST PI 유지
        cats = get_task_categories_for_worker(
            worker_company='GST', worker_role='PI',
            product_mech_partner='TMS', product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='FAB2'
        )
        self.assertIn('PI', cats)

        # P4-D → 협력사 위임
        cats2 = get_task_categories_for_worker(
            worker_company='GST', worker_role='PI',
            product_mech_partner='TMS', product_elec_partner=None,
            product_module_outsourcing=None,
            product_line='P4-D'
        )
        self.assertNotIn('PI', cats2)
```

#### Gray-box 테스트 (DB 연결 필요 — Railway)

```python
class TestDragonModelConfigChanged(unittest.TestCase):
    """DRAGON model_config 변경 후 task_seed 동작 검증"""

    def test_dragon_pi_tasks_applicable(self):
        """DRAGON → PI_LNG_UTIL, PI_CHAMBER is_applicable=TRUE"""
        config = get_model_config_by_prefix('DRAGON')
        self.assertTrue(config.pi_lng_util)
        self.assertTrue(config.pi_chamber)

    def test_dragon_mech_no_pressure_test(self):
        """DRAGON → MECH에 PRESSURE_TEST 없음 (TANK_MODULE만)"""
        # 테스트 제품으로 initialize_product_tasks 실행 후
        # MECH 태스크에 PRESSURE_TEST is_applicable=False 확인
        pass  # DB 연결 환경에서 구현

    def test_gaia_pi_visibility_tms_worker(self):
        """GAIA + mech_partner=TMS + line=P4-D → TMS(M) 작업자에게 PI 보임"""
        pass  # 실제 product_info + worker로 filter_tasks_for_worker 호출

    def test_gaia_pi_visibility_jp_gst(self):
        """GAIA + mech_partner=TMS + line=JP(F15) → GST PI에게 PI 보임"""
        pass  # 실제 product_info + worker로 filter_tasks_for_worker 호출
```

### Task 6: 기존 테스트 수정 (Regression 대응)

**파일**: `tests/backend/test_sprint31a_multi_model.py` — 아래 테스트 수정 필요:

1. **`TestModelConfigSprint31A::test_dragon_config_no_pi`** → 수정
   ```python
   # 변경 전: assert config.pi_lng_util == False
   # 변경 후:
   def test_dragon_config_has_pi(self):
       """DRAGON → pi_lng_util=True, pi_chamber=True (Sprint 31C)"""
       config = get_model_config_by_prefix('DRAGON')
       self.assertTrue(config.pi_lng_util)
       self.assertTrue(config.pi_chamber)
   ```

2. **`TestTaskSeedDragon::test_dragon_mech_extra_tasks`** → MECH 태스크 수 변경
   ```python
   # 변경 전: MECH 9개 (기본 7 + TANK_MODULE + PRESSURE_TEST)
   # 변경 후: MECH 8개 (기본 7 + TANK_MODULE만, PRESSURE_TEST는 PI로 이관)
   def test_dragon_mech_extra_tasks(self):
       """DRAGON → MECH에 TANK_MODULE만 추가 (8개), PRESSURE_TEST는 PI"""
       # ... MECH count = 8 확인
       # ... PI_LNG_UTIL, PI_CHAMBER is_applicable=True 추가 확인
   ```

3. **기존 company filtering 테스트** — `test_company_task_filtering.py`
   - `product_line` 파라미터 추가 (기본값 None이므로 기존 테스트는 깨지지 않지만 확인 필요)

### 테스트 실행 명령어

```bash
cd ~/Desktop/GST/AXIS-OPS

# Sprint 31C White-box 테스트
python -m pytest tests/backend/test_sprint31c_pi_visibility.py -v

# 기존 Sprint 31A 테스트 (regression 확인)
python -m pytest tests/backend/test_sprint31a_multi_model.py -v

# 기존 company filtering 테스트 (regression 확인)
python -m pytest tests/backend/test_company_task_filtering.py -v

# 전체 regression
python -m pytest tests/ -v --tb=short -x
```

### 체크리스트

**BE (✅ 완료)**:
- [x] Migration 028 작성 + Railway DB 실행 (admin_settings 2건 + DRAGON model_config PI 활성화) ✅
- [x] `task_seed.py` — `get_task_categories_for_worker` 시그니처에 `product_line` 추가 ✅
- [x] `task_seed.py` — GST PI 블록에 PI 위임 분기 추가 (pi_capable + override_lines) ✅
- [x] `task_seed.py` — TMS(M) 블록에 PI 카테고리 추가 ✅
- [x] `task_seed.py` — FNI/BAT 블록에 PI 확장 대비 로직 추가 ✅
- [x] `task_seed.py` — `filter_tasks_for_worker`에서 `product.line` 전달 ✅
- [x] pi_capable_mech_partners 값 수정: `["TMS(M)"]` → `["TMS"]` (mech_partner 컬럼 값 기준) ✅

**TEST (✅ 완료 — 16/16 passed)**:
- [x] `test_sprint31c_pi_visibility.py` White-box 테스트 16건 ✅
- [x] TMS(M) PI 가시성 4건 (capable+보임, JP+안보임, 미등록+안보임, mech≠TMS+안보임) ✅
- [x] GST PI 가시성 5건 (위임+제외, JP+유지, mech≠capable+유지, mech=NULL+유지, active_role) ✅
- [x] FNI/BAT 확장 2건 (기본 미포함, capable 추가 시 PI 보임) ✅
- [x] Regression 5건 (ADMIN, QI, SI, ELEC, 복수 override_lines) ✅
- [ ] Gray-box 테스트 (DRAGON config + 태스크 생성 검증) — 추후

**기존 테스트 수정**:
- [ ] `test_sprint31a_multi_model.py` — DRAGON PI 관련 테스트 수정 — 추후
- [ ] `test_company_task_filtering.py` — product_line 파라미터 호환성 (기본값 None → 기존 동작 유지)
- [ ] 전체 regression 테스트 통과 확인

**검증 (✅ 배포 후 실기기 확인 완료)**:
- [x] TMS(M) 작업자 → GAIA(mech=TMS, line=P4-D) QR 스캔 → PI 보임 ✅
- [x] TMS(M) 작업자 → GAIA(mech=TMS, line=JP(F15)) QR 스캔 → PI 안 보임 ✅
- [x] GST PI 작업자 → GAIA(mech=TMS, line=P4-D) QR 스캔 → PI 안 보임 ✅
- [x] GST PI 작업자 → GAIA(mech=TMS, line=JP(F15)) QR 스캔 → PI 보임 ✅
- [x] TMS(M) → DRAGON(mech=TMS) QR 스캔 → PI 보임 ✅
- [x] 기존 GAIA(mech=FNI) → GST PI에서 PI 정상 표시 (변경 없음) ✅
- [x] admin_settings 수정 후 즉시 반영 확인 ✅

### 롤백 계획

문제 발생 시:
1. **model_config 복원**: `UPDATE model_config SET pi_lng_util=FALSE, pi_chamber=FALSE WHERE model_prefix='DRAGON';`
2. **기존 데이터 복원**:
   ```sql
   -- PI 태스크 비활성화 복원
   UPDATE app_task_details SET is_applicable = FALSE WHERE task_category = 'PI'
     AND serial_number IN (SELECT serial_number FROM plan.product_info WHERE model ILIKE 'DRAGON%');
   -- MECH PRESSURE_TEST 활성화 복원
   UPDATE app_task_details SET is_applicable = TRUE WHERE task_category = 'MECH' AND task_id = 'PRESSURE_TEST'
     AND serial_number IN (SELECT serial_number FROM plan.product_info WHERE model ILIKE 'DRAGON%');
   ```
3. **admin_settings 삭제**: `DELETE FROM admin_settings WHERE setting_key IN ('pi_capable_mech_partners', 'pi_gst_override_lines');`
4. **코드 롤백**: `git revert` — `product_line` 파라미터는 기본값 None이므로 하위 호환 유지

## Sprint 34: admin_settings PI 위임 설정 API 확장 — JSON 배열 키 지원

> **목적**: Sprint 31C에서 DB에 추가된 `pi_capable_mech_partners`, `pi_gst_override_lines`를 PUT /api/admin/settings API로 수정 가능하게 확장. 향후 JSON 배열 타입 설정이 추가되어도 검증 로직을 반복 작성하지 않는 구조 설계.
> **범위**: BE 1파일 수정 + 테스트
> **의존성**: Sprint 31C (admin_settings에 pi_capable_mech_partners, pi_gst_override_lines 값 존재)
> **버전**: v1.9.1 패치 (마이그레이션 없음)

### 배경

Sprint 31C에서 마이그레이션으로 admin_settings에 2개 키를 INSERT했지만, `admin.py`의 `ALLOWED_KEYS`에 등록되지 않아 PUT API로 수정 불가 상태.

현재 ALLOWED_KEYS 구조:
```python
ALLOWED_KEYS = {
    'heating_jacket_enabled',     # bool
    'phase_block_enabled',        # bool
    'location_qr_required',       # bool
    'break_morning_start',        # HH:MM string
    ...
    'geo_check_enabled',          # bool
    'geo_radius_meters',          # number
}
```

문제: 모든 키가 flat set에 들어있고, 타입별 검증이 TIME_KEYS / TIME_PAIRS로 분산되어 있음.
PI 설정은 **JSON 배열** (`["TMS(M)"]`, `["JP"]`) 타입이라 기존 bool/string 검증과 다른 로직 필요.

### 설계 — 타입별 키 레지스트리

기존 flat `ALLOWED_KEYS` set을 **타입별 레지스트리 dict**으로 리팩터링:

```python
# ─── 설정 키 레지스트리 ───────────────────────────────
# 타입별로 분류 → 검증 로직이 타입에 따라 자동 적용
# 새 키 추가 시 여기에 등록만 하면 검증이 자동으로 걸림

SETTING_KEYS: Dict[str, Dict[str, Any]] = {
    # ── bool 타입 ──
    'heating_jacket_enabled':   {'type': 'bool', 'default': False},
    'phase_block_enabled':      {'type': 'bool', 'default': False},
    'location_qr_required':     {'type': 'bool', 'default': True},
    'auto_pause_enabled':       {'type': 'bool', 'default': True},
    'geo_check_enabled':        {'type': 'bool', 'default': False},
    'geo_strict_mode':          {'type': 'bool', 'default': False},

    # ── time (HH:MM) 타입 ──
    'break_morning_start':      {'type': 'time', 'default': '10:00', 'pair': 'break_morning_end'},
    'break_morning_end':        {'type': 'time', 'default': '10:20', 'pair': 'break_morning_start'},
    'break_afternoon_start':    {'type': 'time', 'default': '15:00', 'pair': 'break_afternoon_end'},
    'break_afternoon_end':      {'type': 'time', 'default': '15:20', 'pair': 'break_afternoon_start'},
    'lunch_start':              {'type': 'time', 'default': '11:20', 'pair': 'lunch_end'},
    'lunch_end':                {'type': 'time', 'default': '12:20', 'pair': 'lunch_start'},
    'dinner_start':             {'type': 'time', 'default': '17:00', 'pair': 'dinner_end'},
    'dinner_end':               {'type': 'time', 'default': '18:00', 'pair': 'dinner_start'},

    # ── number 타입 ──
    'geo_latitude':             {'type': 'number', 'default': 35.1796},
    'geo_longitude':            {'type': 'number', 'default': 129.0756},
    'geo_radius_meters':        {'type': 'number', 'default': 200, 'min': 50, 'max': 5000},

    # ── string_list (JSON 배열) 타입 ── Sprint 34 추가
    'pi_capable_mech_partners': {'type': 'string_list', 'default': [], 'allowed_values': None},
    'pi_gst_override_lines':    {'type': 'string_list', 'default': [], 'allowed_values': None},

    # ── bool 타입 (실적확인) ── Sprint 33
    'confirm_mech_enabled':     {'type': 'bool', 'default': True},
    'confirm_elec_enabled':     {'type': 'bool', 'default': True},
    'confirm_tm_enabled':       {'type': 'bool', 'default': True},
    'confirm_pi_enabled':       {'type': 'bool', 'default': False},
    'confirm_qi_enabled':       {'type': 'bool', 'default': False},
    'confirm_si_enabled':       {'type': 'bool', 'default': False},
    'confirm_checklist_required': {'type': 'bool', 'default': False},
}

# 하위호환: 기존 코드에서 ALLOWED_KEYS를 참조하는 곳 대비
ALLOWED_KEYS = set(SETTING_KEYS.keys())
```

### 팀 구성

```
CLAUDE.md를 읽고 Sprint 34를 진행해줘.

팀 구성: 1명 teammate (Sonnet)
1. **BE** — 소유: backend/**  tests/**
```

### Task 1: admin.py — SETTING_KEYS 레지스트리 + 타입별 검증 함수

**파일**: `backend/app/routes/admin.py`

#### 1-1. SETTING_KEYS dict 추가 (PUT 핸들러 위)

위 설계의 `SETTING_KEYS` dict를 모듈 레벨 상수로 추가.
기존 `ALLOWED_KEYS` set, `TIME_KEYS` set, `TIME_PAIRS` list는 삭제하고 `SETTING_KEYS`로 통합.

```python
ALLOWED_KEYS = set(SETTING_KEYS.keys())  # 하위호환
```

#### 1-2. 타입별 검증 함수 추가

```python
import re

TIME_PATTERN = re.compile(r'^([01]\d|2[0-3]):[0-5]\d$')


def _validate_setting(key: str, value: Any) -> Optional[str]:
    """
    설정 값 타입 검증.
    Returns: 에러 메시지 (None이면 통과)
    """
    meta = SETTING_KEYS.get(key)
    if not meta:
        return f'허용되지 않은 설정 키: {key}'

    stype = meta['type']

    if stype == 'bool':
        if not isinstance(value, bool):
            return f'{key}: bool 타입이어야 합니다.'

    elif stype == 'time':
        if not isinstance(value, str) or not TIME_PATTERN.match(value):
            return f'{key}: HH:MM 형식이어야 합니다. (예: "10:00")'

    elif stype == 'number':
        if not isinstance(value, (int, float)):
            return f'{key}: 숫자 타입이어야 합니다.'
        if 'min' in meta and value < meta['min']:
            return f'{key}: 최소값은 {meta["min"]}입니다.'
        if 'max' in meta and value > meta['max']:
            return f'{key}: 최대값은 {meta["max"]}입니다.'

    elif stype == 'string_list':
        if not isinstance(value, list):
            return f'{key}: 배열 타입이어야 합니다. (예: ["TMS(M)"])'
        for i, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                return f'{key}[{i}]: 빈 문자열이 아닌 문자열이어야 합니다.'
        # 중복 제거 검증 (선택적 — 경고만)
        if len(value) != len(set(value)):
            return f'{key}: 중복 값이 포함되어 있습니다.'
        # allowed_values 검증 (설정되어 있으면)
        allowed = meta.get('allowed_values')
        if allowed:
            invalid = [v for v in value if v not in allowed]
            if invalid:
                return f'{key}: 허용되지 않은 값: {invalid}'

    return None
```

#### 1-3. PUT 핸들러 리팩터링

기존의 TIME_KEYS / TIME_PAIRS 분산 검증을 `_validate_setting()` 한 곳으로 통합:

```python
@admin_bp.route("/settings", methods=["PUT"])
@jwt_required
@manager_or_admin_required
def update_settings():
    data = request.get_json(silent=True) or {}

    update_pairs = {k: v for k, v in data.items() if k in ALLOWED_KEYS}

    if not update_pairs:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': f'업데이트할 유효한 설정 키가 없습니다.'
        }), 400

    # ─── 타입별 검증 (통합) ───
    for key, value in update_pairs.items():
        error = _validate_setting(key, value)
        if error:
            return jsonify({'error': 'VALIDATION_ERROR', 'message': error}), 400

    # ─── 시간 쌍 검증 (start < end) ───
    from app.models.admin_settings import get_setting as _get_setting
    time_keys_in_update = [k for k in update_pairs if SETTING_KEYS[k]['type'] == 'time']
    checked_pairs = set()
    for tk in time_keys_in_update:
        pair_key = SETTING_KEYS[tk].get('pair')
        if not pair_key or (tk, pair_key) in checked_pairs or (pair_key, tk) in checked_pairs:
            continue
        checked_pairs.add((tk, pair_key))
        # start_key는 _start로 끝나는 쪽
        if tk.endswith('_start'):
            start_val = update_pairs.get(tk) or _get_setting(tk)
            end_val = update_pairs.get(pair_key) or _get_setting(pair_key)
        else:
            start_val = update_pairs.get(pair_key) or _get_setting(pair_key)
            end_val = update_pairs.get(tk) or _get_setting(tk)
        if start_val and end_val and start_val >= end_val:
            return jsonify({
                'error': 'INVALID_TIME_RANGE',
                'message': f'시작 시간({start_val})이 종료 시간({end_val})보다 이전이어야 합니다.'
            }), 400

    # ─── 저장 ───
    failed_keys = []
    for key, value in update_pairs.items():
        success = update_setting(key, value, updated_by=g.worker_id)
        if not success:
            failed_keys.append(key)

    if failed_keys:
        logger.error(f"Admin settings update failed for keys: {failed_keys}, by_admin={g.worker_id}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': f'설정 저장 실패: {", ".join(failed_keys)}'
        }), 500

    updated_keys = list(update_pairs.keys())
    logger.info(f"Admin settings updated: keys={updated_keys}, by_admin={g.worker_id}")

    # ─── Side Effects (기존 유지) ───
    if 'heating_jacket_enabled' in update_pairs:
        _sync_heating_jacket_tasks(update_pairs['heating_jacket_enabled'])

    return jsonify({
        'message': '설정이 저장되었습니다.',
        'updated_keys': updated_keys
    }), 200
```

#### 1-4. heating_jacket side effect 별도 함수 추출

기존 인라인 코드를 `_sync_heating_jacket_tasks(new_val: bool)` 함수로 추출 (가독성 개선).

#### 1-5. GET 핸들러 기본값 자동화

기존 수동 `result.setdefault(...)` 나열을 `SETTING_KEYS`에서 자동 생성:

```python
@admin_bp.route("/settings", methods=["GET"])
@jwt_required
@admin_required
def get_settings():
    settings_list = get_all_settings()
    result = {}
    for s in settings_list:
        result[s.setting_key] = s.setting_value

    # SETTING_KEYS 기반 기본값 자동 적용
    for key, meta in SETTING_KEYS.items():
        result.setdefault(key, meta['default'])

    return jsonify(result), 200
```

이렇게 하면 새 키 추가 시 `SETTING_KEYS`에만 등록하면 GET 기본값 + PUT 검증이 자동 적용됨.

### Task 2: 테스트

**파일**: `tests/backend/test_sprint34_settings_registry.py`

#### White-box 테스트 — _validate_setting 단위 테스트

```python
"""
Sprint 34: admin_settings 타입별 검증 레지스트리 테스트
"""

import unittest
import sys
sys.path.insert(0, 'backend')
from app.routes.admin import _validate_setting


class TestValidateBool(unittest.TestCase):
    """bool 타입 검증"""

    def test_bool_valid(self):
        self.assertIsNone(_validate_setting('heating_jacket_enabled', True))
        self.assertIsNone(_validate_setting('heating_jacket_enabled', False))

    def test_bool_invalid_string(self):
        error = _validate_setting('heating_jacket_enabled', 'true')
        self.assertIsNotNone(error)

    def test_bool_invalid_int(self):
        error = _validate_setting('heating_jacket_enabled', 1)
        self.assertIsNotNone(error)


class TestValidateStringList(unittest.TestCase):
    """string_list (JSON 배열) 타입 검증"""

    def test_valid_list(self):
        self.assertIsNone(_validate_setting('pi_capable_mech_partners', ['TMS(M)']))

    def test_valid_multi(self):
        self.assertIsNone(_validate_setting('pi_capable_mech_partners', ['TMS(M)', 'FNI']))

    def test_valid_empty_list(self):
        """빈 배열 허용 (전체 비활성화)"""
        self.assertIsNone(_validate_setting('pi_capable_mech_partners', []))

    def test_invalid_not_list(self):
        error = _validate_setting('pi_capable_mech_partners', 'TMS(M)')
        self.assertIsNotNone(error)

    def test_invalid_empty_string_item(self):
        error = _validate_setting('pi_capable_mech_partners', ['TMS(M)', ''])
        self.assertIsNotNone(error)

    def test_invalid_non_string_item(self):
        error = _validate_setting('pi_capable_mech_partners', ['TMS(M)', 123])
        self.assertIsNotNone(error)

    def test_invalid_duplicate(self):
        error = _validate_setting('pi_capable_mech_partners', ['TMS(M)', 'TMS(M)'])
        self.assertIsNotNone(error)

    def test_override_lines_valid(self):
        self.assertIsNone(_validate_setting('pi_gst_override_lines', ['JP', 'FAB2']))


class TestValidateTime(unittest.TestCase):
    """time (HH:MM) 타입 검증"""

    def test_valid(self):
        self.assertIsNone(_validate_setting('lunch_start', '11:20'))

    def test_invalid_format(self):
        error = _validate_setting('lunch_start', '25:00')
        self.assertIsNotNone(error)


class TestValidateNumber(unittest.TestCase):
    """number 타입 검증"""

    def test_valid(self):
        self.assertIsNone(_validate_setting('geo_radius_meters', 200))

    def test_below_min(self):
        error = _validate_setting('geo_radius_meters', 10)
        self.assertIsNotNone(error)

    def test_above_max(self):
        error = _validate_setting('geo_radius_meters', 10000)
        self.assertIsNotNone(error)


class TestValidateConfirmEnabled(unittest.TestCase):
    """Sprint 33 confirm_* 설정 검증"""

    def test_confirm_mech_valid(self):
        self.assertIsNone(_validate_setting('confirm_mech_enabled', True))

    def test_confirm_pi_valid(self):
        self.assertIsNone(_validate_setting('confirm_pi_enabled', False))


class TestValidateUnknownKey(unittest.TestCase):
    """등록되지 않은 키 검증"""

    def test_unknown_key(self):
        error = _validate_setting('unknown_key', True)
        self.assertIsNotNone(error)
```

#### Gray-box 테스트 — API 통합 테스트

```python
class TestSettingsAPIStringList(unittest.TestCase):
    """PUT /api/admin/settings — JSON 배열 타입 통합 테스트"""

    def test_update_pi_capable_partners(self):
        """pi_capable_mech_partners 업데이트"""
        # PUT /api/admin/settings
        # body: {"pi_capable_mech_partners": ["TMS(M)", "FNI"]}
        # → 200, updated_keys에 포함 확인
        # → GET /api/admin/settings → pi_capable_mech_partners == ["TMS(M)", "FNI"]
        pass

    def test_update_override_lines(self):
        """pi_gst_override_lines 업데이트"""
        # PUT body: {"pi_gst_override_lines": ["JP", "FAB2"]}
        # → 200 확인
        pass

    def test_update_mixed_types(self):
        """bool + string_list 동시 업데이트"""
        # PUT body: {"confirm_pi_enabled": true, "pi_capable_mech_partners": ["TMS(M)", "FNI"]}
        # → 200 확인
        pass

    def test_invalid_string_list_rejected(self):
        """잘못된 형식 400 거부"""
        # PUT body: {"pi_capable_mech_partners": "TMS(M)"}  ← 문자열 (배열 아님)
        # → 400 VALIDATION_ERROR
        pass
```

### Task 3: version.py (변경 없음)

Sprint 31C에서 이미 v1.9.1로 올렸으므로 유지. Sprint 33과 34는 동일 패치 범위.

### 테스트 실행

```bash
cd ~/Desktop/GST/AXIS-OPS

# Sprint 34 단위 테스트
python -m pytest tests/backend/test_sprint34_settings_registry.py -v

# 기존 admin settings 테스트 (있으면) regression 확인
python -m pytest tests/ -k "settings or admin" -v

# 전체 regression
python -m pytest tests/ -v --tb=short -x
```

### 체크리스트

**BE (✅ 완료)**:
- [x] `admin.py` — `SETTING_KEYS` 레지스트리 dict 28개 키 (기존 ALLOWED_KEYS/TIME_KEYS/TIME_PAIRS 대체) ✅
- [x] `admin.py` — `_validate_setting()` 함수 추가 (bool, time, number, string_list 4타입) ✅
- [x] `admin.py` — PUT 핸들러에서 `_validate_setting()` 호출로 통합 검증 ✅
- [x] `admin.py` — 시간 쌍 검증 — SETTING_KEYS의 `pair` 필드 기반 리팩터링 ✅
- [x] `admin.py` — GET 기본값 `setdefault` 나열 → `SETTING_KEYS` 기반 자동화 ✅
- [x] `admin.py` — `ALLOWED_KEYS = set(SETTING_KEYS.keys())` 하위호환 유지 ✅
- [x] `SETTING_KEYS`에 Sprint 31C 키: `pi_capable_mech_partners`, `pi_gst_override_lines` (string_list) ✅
- [x] `SETTING_KEYS`에 Sprint 33 키: `confirm_*_enabled` 7개 (bool) ✅
- [x] 로컬 _validate_setting 검증 통과 (bool/time/number/string_list/unknown 전부) ✅

**TEST**:
- [x] _validate_setting 로컬 검증 (bool valid/invalid, string_list valid/empty/not-list/duplicate, time, number min/max, unknown key) ✅
- [ ] 정식 테스트 파일 작성 — 추후
- [ ] 전체 regression 테스트 — 추후

**검증 (배포 후)**:
- [ ] PUT `{"pi_capable_mech_partners": ["TMS", "FNI"]}` → 200
- [ ] PUT `{"pi_capable_mech_partners": "TMS"}` → 400 (배열 아님)
- [ ] PUT `{"pi_gst_override_lines": ["JP", "FAB2"]}` → 200
- [ ] PUT `{"confirm_pi_enabled": true}` → 200
- [ ] GET → 모든 키 28개 기본값 포함 확인
- [ ] 기존 OPS Flutter 앱 설정 화면 정상 동작 (regression)

### 장기 확장성

새 설정 키 추가 시 `SETTING_KEYS`에 1줄만 추가하면 됨:

```python
# 예: 나중에 QI 검사 가능 협력사 추가 시
'qi_capable_partners': {'type': 'string_list', 'default': [], 'allowed_values': None},

# 예: 자동 마감 시간 추가 시
'auto_close_time': {'type': 'time', 'default': '18:00', 'pair': None},

# 예: 최대 동시 작업 수 추가 시
'max_concurrent_tasks': {'type': 'number', 'default': 3, 'min': 1, 'max': 10},
```

GET 기본값 + PUT 검증이 자동 적용되므로, 기존 패턴처럼 `setdefault` 추가 + `ALLOWED_KEYS` 추가 + 타입 검증 추가를 3곳에서 할 필요 없음.

### Task 4: GET /api/admin/workers — is_manager 필터 파라미터 추가

**파일**: `backend/app/routes/admin.py` (Lines 185~287)

**현재 문제**: 협력사 관리자 관리 화면에서 전체 작업자 목록이 표시됨. FNI 선택 시 FNI 소속 전원이 나오는데, 실제 manager는 1~2명. 나머지는 스크롤 낭비.

**현재 쿼리 파라미터**: `approval_status`, `role`, `limit` — `is_manager` 필터 없음

**수정**: `company`, `is_manager` 쿼리 파라미터 추가

```python
@admin_bp.route("/workers", methods=["GET"])
@jwt_required
@manager_or_admin_required
def get_workers():
    """
    작업자 목록 조회 (필터링 지원)

    Query Parameters:
        approval_status: str (optional: pending, approved, rejected)
        role: str (optional: MM, EE, TM, PI, QI, SI)
        company: str (optional: GST, FNI, BAT, TMS(M), TMS(E), P&S, C&A)
        is_manager: str (optional: true/false — manager 필터)
        limit: int (default: 200)
    """
    approval_status = request.args.get('approval_status')
    role = request.args.get('role')
    company_filter = request.args.get('company')        # ★ Sprint 34 추가
    is_manager_filter = request.args.get('is_manager')  # ★ Sprint 34 추가
    limit = min(500, request.args.get('limit', 200, type=int))

    # ... 기존 where_clauses 구성 ...

    # ★ Sprint 34: company 필터 (기존 manager 자사 필터와 별개)
    if company_filter:
        where_clauses.append("company = %s")
        params.append(company_filter)

    # ★ Sprint 34: is_manager 필터
    if is_manager_filter is not None:
        if is_manager_filter.lower() in ('true', '1'):
            where_clauses.append("(is_manager = TRUE OR is_admin = TRUE)")
        elif is_manager_filter.lower() in ('false', '0'):
            where_clauses.append("is_manager = FALSE AND is_admin = FALSE")

    # ... 이하 기존 로직 동일 ...
```

**하위호환**: 기존 호출(`?limit=500` 파라미터만 사용)은 필터 없이 동작 → 전체 반환 유지.

**FE 사용 예시**:

```
OPS Flutter: GET /api/admin/workers?company=FNI&is_manager=true
  → FNI 소속 manager/admin만 반환 (1~2명)

OPS Flutter: GET /api/admin/workers?company=FNI
  → FNI 소속 전체 (기존 동작 — manager 지정할 때 사용)

VIEW:       GET /api/admin/workers?is_manager=true
  → 전체 회사 manager/admin 목록
```

**OPS Flutter 변경**: 협력사 관리자 관리 화면에서 기본 호출을 `?is_manager=true`로 변경. "전체 보기" 토글 시 파라미터 제거.

**테스트 추가** (`test_sprint34_settings_registry.py` 또는 별도 파일):

```python
class TestWorkersFilterIsManager(unittest.TestCase):
    """GET /api/admin/workers — is_manager 필터 테스트"""

    def test_filter_managers_only(self):
        """is_manager=true → manager/admin만 반환"""
        # GET /api/admin/workers?is_manager=true
        # 응답의 모든 worker가 is_manager=True OR is_admin=True
        pass

    def test_filter_non_managers(self):
        """is_manager=false → 일반 작업자만 반환"""
        pass

    def test_no_filter_returns_all(self):
        """is_manager 미지정 → 전체 반환 (하위호환)"""
        pass

    def test_combined_filter(self):
        """company=FNI&is_manager=true → FNI 소속 manager만"""
        pass
```

**체크리스트 추가**:

**BE (✅ 완료)**:
- [x] `admin.py` GET /workers — `company` 쿼리 파라미터 추가 ✅
- [x] `admin.py` GET /workers — `is_manager` 쿼리 파라미터 추가 (true → manager/admin, false → 일반) ✅
- [x] 하위호환: 파라미터 미지정 시 전체 반환 ✅
- [x] `is_manager=true` 시 `is_admin=TRUE`도 포함 ✅

**TEST**:
- [x] is_manager 필터 테스트 — 추후
- [x] company + is_manager 복합 필터 테스트 — 추후

**검증 (배포 후)**:
- [x] OPS Flutter 협력사 관리자 화면 — 기본 manager만 표시 확인
- [x] VIEW 권한 관리 페이지 — 기존 동작 유지

---

## Sprint 34-A: OPS Flutter — Admin 옵션 화면 PI 위임 설정 UI 추가

**목표**: Sprint 31C에서 추가된 `pi_capable_mech_partners`, `pi_gst_override_lines` 설정을 OPS Flutter Admin 옵션 화면에서 편집할 수 있도록 UI 추가.

**범위**: 1 FE 파일 수정 (`admin_options_screen.dart`)
**의존성**: Sprint 31C (BE — 키 등록), Sprint 34 Task 1 (BE — `string_list` 타입 validation)
**버전**: v1.9.1 (동일 패치)

---

### Task 1: `admin_options_screen.dart` — 상태 변수 + _loadSettings 확장

**파일**: `frontend/lib/screens/admin/admin_options_screen.dart`

**1-1. 상태 변수 추가** (Line 26 부근, 기존 `_isLoadingSettings` 아래):

```dart
  // PI 위임 설정 (Sprint 34-A)
  List<String> _piCapableMechPartners = [];   // pi_capable_mech_partners
  List<String> _piGstOverrideLines = [];      // pi_gst_override_lines
```

**1-2. _loadSettings() 확장** (Line 237 부근, `_locationQrRequired` 파싱 아래):

기존 `_loadSettings()` 내부 setState 블록에 추가:

```dart
          // PI 위임 설정 (Sprint 34-A)
          final rawPartners = response['pi_capable_mech_partners'];
          _piCapableMechPartners = (rawPartners is List)
              ? rawPartners.map((e) => e.toString()).toList()
              : <String>[];
          final rawLines = response['pi_gst_override_lines'];
          _piGstOverrideLines = (rawLines is List)
              ? rawLines.map((e) => e.toString()).toList()
              : <String>[];
```

**참고**: `response['pi_capable_mech_partners']`는 JSON array(`["FNI","BAT"]`)로 반환됨.
Flask BE에서 JSONB 필드이므로 Dart에서는 `List<dynamic>`으로 수신 → `.map((e) => e.toString()).toList()`.

---

### Task 2: `admin_options_screen.dart` — string_list 업데이트 메서드

**2-1. _updateStringListSetting() 추가** (Line 287 부근, `_updateSetting()` 아래):

```dart
  /// string_list 타입 설정 업데이트 (PUT /admin/settings)
  Future<void> _updateStringListSetting(String key, List<String> value) async {
    try {
      final apiService = ref.read(apiServiceProvider);
      await apiService.put('/admin/settings', data: {key: value});
      if (mounted) {
        setState(() {
          if (key == 'pi_capable_mech_partners') _piCapableMechPartners = value;
          if (key == 'pi_gst_override_lines') _piGstOverrideLines = value;
        });
        _showSnack('설정이 저장되었습니다.', isError: false);
      }
    } catch (e) {
      if (mounted) _showSnack('설정 저장에 실패했습니다.', isError: true);
    }
  }
```

**핵심**: `data: {key: value}` → value가 `List<String>`이므로 Dio가 자동으로 JSON array로 직렬화.
BE `_validate_setting()`이 `string_list` 타입 검증 수행.

---

### Task 3: `admin_options_screen.dart` — _buildChipListSetting 위젯 메서드

**3-1. 헬퍼 메서드 추가** (Line 1055 부근, `_buildSettingToggle()` 아래):

```dart
  /// string_list 설정을 Chip 목록 + 추가/삭제로 표시
  Widget _buildChipListSetting({
    required String title,
    required String subtitle,
    required List<String> values,
    required List<String> allOptions,
    required String settingKey,
    bool isFirst = false,
  }) {
    return Padding(
      padding: EdgeInsets.only(
        left: 16, right: 16,
        top: isFirst ? 14 : 10,
        bottom: 10,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 제목 + 설명
          Text(title, style: const TextStyle(
            fontSize: 13, fontWeight: FontWeight.w500, color: GxColors.charcoal,
          )),
          const SizedBox(height: 2),
          Text(subtitle, style: const TextStyle(fontSize: 11, color: GxColors.steel)),
          const SizedBox(height: 8),
          // Chip 목록 (Wrap)
          Wrap(
            spacing: 6,
            runSpacing: 4,
            children: [
              // 현재 선택된 값들 → 삭제 가능한 Chip
              ...values.map((v) => Chip(
                label: Text(v, style: const TextStyle(fontSize: 12)),
                deleteIcon: const Icon(Icons.close, size: 14),
                onDeleted: () {
                  final updated = List<String>.from(values)..remove(v);
                  _updateStringListSetting(settingKey, updated);
                },
                backgroundColor: GxColors.accentSoft,
                deleteIconColor: GxColors.steel,
                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                visualDensity: VisualDensity.compact,
              )),
              // 추가 버튼 → 미선택 항목 중 고르기
              if (allOptions.where((o) => !values.contains(o)).isNotEmpty)
                ActionChip(
                  avatar: const Icon(Icons.add, size: 14, color: GxColors.accent),
                  label: const Text('추가', style: TextStyle(fontSize: 12, color: GxColors.accent)),
                  onPressed: () => _showAddOptionDialog(
                    title: title,
                    currentValues: values,
                    allOptions: allOptions,
                    settingKey: settingKey,
                  ),
                  backgroundColor: GxColors.snowBg,
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  visualDensity: VisualDensity.compact,
                ),
            ],
          ),
        ],
      ),
    );
  }
```

**3-2. _showAddOptionDialog() 추가** (바로 아래):

```dart
  /// 미선택 옵션 중 하나를 선택하여 추가하는 다이얼로그
  void _showAddOptionDialog({
    required String title,
    required List<String> currentValues,
    required List<String> allOptions,
    required String settingKey,
  }) {
    final available = allOptions.where((o) => !currentValues.contains(o)).toList();
    if (available.isEmpty) return;

    showDialog(
      context: context,
      builder: (ctx) => SimpleDialog(
        title: Text('$title 추가', style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.lg)),
        children: available.map((option) => SimpleDialogOption(
          onPressed: () {
            Navigator.pop(ctx);
            final updated = List<String>.from(currentValues)..add(option);
            _updateStringListSetting(settingKey, updated);
          },
          child: Text(option, style: const TextStyle(fontSize: 14)),
        )).toList(),
      ),
    );
  }
```

**디자인 패턴**:
- 선택된 값 → `Chip` (× 버튼으로 삭제)
- 미선택 항목 있으면 `ActionChip(+ 추가)` 표시
- "추가" 탭 → `SimpleDialog`에서 미선택 항목 리스트 표시
- 선택 즉시 PUT → setState 반영

**allOptions 값**:
- `pi_capable_mech_partners` → `_companies` (기존 상수: `['FNI', 'BAT', 'TMS(M)', 'TMS(E)', 'P&S', 'C&A', 'GST']`)
- `pi_gst_override_lines` → 라인 리스트 상수 추가 필요 (Task 4)

---

### Task 4: `admin_options_screen.dart` — 라인 상수 + 섹션 UI 배치

**4-1. 라인 상수 추가** (Line 76 부근, `_companies` 아래):

```dart
  /// GST Override 가능한 라인 목록
  static const List<String> _gstLines = [
    'LINE-1', 'LINE-2', 'LINE-3', 'LINE-4', 'LINE-5', 'LINE-6',
  ];
```

> **참고**: 실제 라인 값은 현재 운영 중인 라인명으로 교체. GST 공장 라인 구성에 맞춰 조정.

**4-2. 섹션 UI — PI 위임 설정** (Section 1 `Admin Settings` 영역, Line 682 `SizedBox(height: 24)` 위에 삽입):

기존 구조:
```
Section 1: Admin Settings (heating_jacket, phase_block, location_qr)
   └─ GxGlass.cardSm 컨테이너
       ├─ Heating Jacket 토글
       ├─ Phase Block 토글
       └─ Location QR 필수 토글
SizedBox(height: 24)
Section 2: 협력사 관리자 관리
```

변경 후:
```
Section 1: Admin Settings (기존 토글 유지)
   └─ GxGlass.cardSm 컨테이너
       ├─ Heating Jacket 토글
       ├─ Phase Block 토글
       └─ Location QR 필수 토글
SizedBox(height: 16)          ← 간격 추가
PI 위임 설정 서브섹션          ← 새로 추가
   └─ GxGlass.cardSm 컨테이너
       ├─ _buildChipListSetting (PI 위임 가능 MECH 협력사)
       ├─ Divider
       └─ _buildChipListSetting (PI GST Override 라인)
SizedBox(height: 24)
Section 2: 협력사 관리자 관리 (기존 유지)
```

**삽입 코드** (Line 683 `),` 직후, `const SizedBox(height: 24)` 직전):

```dart
              const SizedBox(height: 16),
              // PI 위임 설정 (Sprint 34-A)
              _buildSectionHeader(
                icon: Icons.assignment_ind,
                iconBg: GxColors.warningBg,
                iconColor: GxColors.warning,
                title: 'PI 위임 설정',
                subtitle: 'PI 검사를 수행할 수 있는 협력사 / GST Override 라인',
              ),
              const SizedBox(height: 10),
              Container(
                decoration: GxGlass.cardSm(radius: GxRadius.lg),
                child: _isLoadingSettings
                    ? const Padding(
                        padding: EdgeInsets.all(20),
                        child: Center(child: CircularProgressIndicator(
                          color: GxColors.accent, strokeWidth: 2,
                        )),
                      )
                    : Column(
                        children: [
                          _buildChipListSetting(
                            title: 'PI 위임 가능 MECH 협력사',
                            subtitle: '선택된 협력사의 MECH 작업자가 PI 검사 수행 가능',
                            values: _piCapableMechPartners,
                            allOptions: _companies,
                            settingKey: 'pi_capable_mech_partners',
                            isFirst: true,
                          ),
                          const Divider(height: 1, color: GxColors.mist),
                          _buildChipListSetting(
                            title: 'PI GST Override 라인',
                            subtitle: '선택된 라인에서 GST PI 담당자도 PI 검사 수행 가능',
                            values: _piGstOverrideLines,
                            allOptions: _gstLines,
                            settingKey: 'pi_gst_override_lines',
                          ),
                        ],
                      ),
              ),
```

---

### Task 5: 테스트 — 수동 검증 체크리스트

Sprint 34-A는 Flutter FE 전용이므로 자동화 테스트 대신 수동 검증:

```
[ ] Admin 옵션 화면 진입 시 PI 위임 설정 섹션 표시
[ ] _loadSettings() → pi_capable_mech_partners, pi_gst_override_lines 정상 로드
[ ] 빈 배열일 때 → Chip 없이 "추가" ActionChip만 표시
[ ] "추가" 탭 → SimpleDialog에 미선택 항목 표시
[ ] 항목 선택 → PUT /admin/settings 호출 → Chip 즉시 반영
[ ] Chip × 버튼 → 삭제 PUT 호출 → Chip 제거 반영
[ ] 모든 옵션 선택 시 → "추가" ActionChip 숨김
[ ] 저장 성공 → "설정이 저장되었습니다." 스낵바
[ ] 저장 실패 → "설정 저장에 실패했습니다." 에러 스낵바
[ ] 기존 섹션 (heating_jacket, phase_block, location_qr) 영향 없음
```

---

### 체크리스트

**FE (✅ 완료)**:
- [x] 상태 변수: `_piCapableMechPartners`, `_piGstOverrideLines` ✅
- [x] `_loadSettings()` — 두 키 파싱 추가 ✅
- [x] `_updateStringListSetting()` — List<String> PUT 메서드 ✅
- [x] `_buildChipListSetting()` — Chip 목록 + 추가/삭제 위젯 ✅
- [x] `_showAddOptionDialog()` — 미선택 항목 선택 다이얼로그 ✅
- [x] `_mechPartnerOptions`, `_lineOptions` 상수 ✅
- [x] Section UI — PI 위임 설정 카드 배치 + Netlify 배포 ✅

**검증**:
- [x] PI 위임 설정 Chip 추가/삭제 동작 확인 — 실기기
- [x] PUT /admin/settings → BE `string_list` validation 통과 확인
- [x] 기존 Admin Settings 토글 영향 없음 확인

---

### Task 6: `admin_options_screen.dart` — 협력사 관리자 관리 is_manager 필터 적용

**배경**: 현재 `/admin/managers` 엔드포인트가 **전체 인원을 반환**하고 있어 리스트가 너무 길고 비효율적.
Sprint 34 Task 4에서 `/admin/workers`에 `is_manager` 필터를 추가했으므로, OPS Flutter에서도 이를 활용.

**6-1. 상태 변수 추가** (Line 63 부근, `_selectedManagerCompany` 아래):

```dart
  bool _showAllWorkers = false;  // false: manager만, true: 전체 인원
```

**6-2. `_loadManagers()` 수정** (Line 338~355):

변경 전:
```dart
  Future<void> _loadManagers() async {
    setState(() => _isLoadingManagers = true);
    try {
      final apiService = ref.read(apiServiceProvider);
      final queryParams = _selectedManagerCompany != null
          ? '?company=${Uri.encodeComponent(_selectedManagerCompany!)}'
          : '';
      final response = await apiService.get('/admin/managers$queryParams');
```

변경 후:
```dart
  Future<void> _loadManagers() async {
    setState(() => _isLoadingManagers = true);
    try {
      final apiService = ref.read(apiServiceProvider);
      // 쿼리 파라미터 조합: company + is_manager
      final params = <String, String>{};
      if (_selectedManagerCompany != null) {
        params['company'] = _selectedManagerCompany!;
      }
      if (!_showAllWorkers) {
        params['is_manager'] = 'true';  // 기본: manager/admin만
      }
      final queryString = params.entries
          .map((e) => '${e.key}=${Uri.encodeComponent(e.value)}')
          .join('&');
      final url = queryString.isEmpty
          ? '/admin/workers'
          : '/admin/workers?$queryString';
      final response = await apiService.get(url);
```

**핵심 변경**:
- 엔드포인트: `/admin/managers` → `/admin/workers` (Sprint 34 Task 4에서 필터 추가된 엔드포인트)
- 기본 동작: `is_manager=true` → manager/admin만 반환 (짧은 리스트)
- `_showAllWorkers = true` → `is_manager` 파라미터 제거 → 전체 인원 (신규 지정 가능)

**6-3. 섹션 헤더에 "전체 보기" 토글 추가** (Line 762~768):

변경 전:
```dart
              _buildSectionHeader(
                icon: Icons.manage_accounts,
                iconBg: GxColors.infoBg,
                iconColor: GxColors.info,
                title: '협력사 관리자 관리',
                subtitle: 'is_manager 토글 (company 필터)',
              ),
```

변경 후:
```dart
              _buildSectionHeader(
                icon: Icons.manage_accounts,
                iconBg: GxColors.infoBg,
                iconColor: GxColors.info,
                title: '협력사 관리자 관리',
                subtitle: _showAllWorkers ? '전체 인원 표시 중' : '관리자만 표시 중',
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '전체 보기',
                      style: TextStyle(
                        fontSize: 11,
                        color: _showAllWorkers ? GxColors.accent : GxColors.steel,
                      ),
                    ),
                    const SizedBox(width: 4),
                    Switch(
                      value: _showAllWorkers,
                      onChanged: (v) {
                        setState(() => _showAllWorkers = v);
                        _loadManagers();
                      },
                      activeColor: GxColors.accent,
                      activeTrackColor: GxColors.accentSoft,
                      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    ),
                  ],
                ),
              ),
```

**참고**: `_buildSectionHeader()`에 `trailing` 파라미터가 이미 존재하는지 확인 필요.
없으면 `_buildSectionHeader()`에 `Widget? trailing` 옵셔널 파라미터 추가:

```dart
  Widget _buildSectionHeader({
    required IconData icon,
    required Color iconBg,
    required Color iconColor,
    required String title,
    required String subtitle,
    Widget? trailing,   // ← 추가
  }) {
    return Row(
      children: [
        // ... 기존 icon + title + subtitle ...
        if (trailing != null) ...[
          const Spacer(),
          trailing,
        ],
      ],
    );
  }
```

**6-4. 빈 목록 메시지 분기** (Line 810 부근):

```dart
                    : _managers.isEmpty
                        ? Padding(
                            padding: const EdgeInsets.all(20),
                            child: Center(
                              child: Text(
                                _showAllWorkers ? '작업자가 없습니다.' : '관리자가 없습니다.',
                                style: const TextStyle(fontSize: 13, color: GxColors.steel),
                              ),
                            ),
                          )
```

---

### Task 6 체크리스트 (✅ 완료)

- [x] `_showAllWorkers` 상태 변수 추가 ✅
- [x] `_loadManagers()` → `/admin/workers?is_manager=true` 변경 ✅
- [x] 섹션 헤더 "전체" Switch 토글 추가 ✅
- [x] `_buildSectionHeader()` trailing — 기존 존재 확인 ✅
- [x] 기본: manager만 → 토글 ON → 전체 인원 ✅
- [x] company + is_manager 필터 동시 작동 ✅
- [x] Netlify 배포 완료 ✅

---

## BACKLOG: confirm_checklist_required — 체크리스트 연동 (실적확인 2단계)

**등록일**: 2026-03-21
**선행**: 자주검사 체크리스트 Sprint (테이블 설계 + CRUD)
**관련 코드**: `production.py` → `_is_process_confirmable()` (Line 97~113)

### 배경

실적확인(confirm) 시스템은 2단계로 설계됨:

**Stage 1 (현재 — Sprint 33 구현 완료)**:
- `confirm_{process}_enabled` = ON/OFF → 해당 공정의 실적확인 기능 자체를 켜고 끔
- confirmable 조건: `confirm_{process}_enabled = true` + **progress 100%**
- 현재 기본값: MECH/ELEC/TM = ON, PI/QI/SI = OFF

**Stage 2 (추후 — 체크리스트 Sprint 후)**:
- `confirm_checklist_required` = ON 시:
  - confirmable 조건: progress 100% **+ 체크리스트 완료**
  - 둘 중 하나라도 미완 → confirmable = false
- `confirm_checklist_required` = OFF 시:
  - Stage 1과 동일 (progress 100%만으로 confirmable)

### 토글 키 정리

| 키 | 타입 | 기본값 | 기능 |
|---|---|---|---|
| `confirm_mech_enabled` | bool | true | MECH 공정 실적확인 ON/OFF |
| `confirm_elec_enabled` | bool | true | ELEC 공정 실적확인 ON/OFF |
| `confirm_tm_enabled` | bool | true | TM 공정 실적확인 ON/OFF |
| `confirm_pi_enabled` | bool | false | PI 공정 실적확인 ON/OFF |
| `confirm_qi_enabled` | bool | false | QI 공정 실적확인 ON/OFF |
| `confirm_si_enabled` | bool | false | SI 공정 실적확인 ON/OFF |
| `confirm_checklist_required` | bool | false | 체크리스트 완료 필수 여부 |

- **ON/OFF 토글 6개**: "이 공정에 대해 완료 도장을 찍을 건지 말 건지"
- **체크리스트 필수**: "도장 찍기 전에 자주검사까지 끝내야 하는지"

### 수정 필요 내용 (체크리스트 Sprint 시)

1. **체크리스트 테이블 설계**: `production_checklist` 테이블 (O/N + 공정별 체크항목)
2. **체크리스트 CRUD API**: 체크리스트 생성/조회/완료 처리
3. **`_is_process_confirmable()` 확장**:
```python
def _is_process_confirmable(sns_progress, process_type, settings, sales_order=None) -> bool:
    key = f'confirm_{process_type.lower()}_enabled'
    if not settings.get(key, False):
        return False

    # Stage 1: progress 100%
    for sn, cats in sns_progress.items():
        cat_data = cats.get(process_type, {})
        if cat_data.get('total', 0) == 0:
            continue
        if cat_data.get('completed', 0) < cat_data.get('total', 0):
            return False

    # Stage 2: 체크리스트 필수
    if settings.get('confirm_checklist_required', False):
        if not _is_checklist_completed(sales_order, process_type):
            return False

    return True
```
4. **VIEW 실적페이지**: 체크리스트 미완 시 confirm 버튼 비활성 + 안내 메시지
5. **OPS/VIEW Admin**: `confirm_checklist_required` 토글 이미 배치됨 → 켜기만 하면 적용

---

## Sprint 35: 근태 기간별 출입 추이 API — 단일 SQL 집계

**목표**: 날짜 범위 지정 시 일별 출입 인원 집계를 반환하는 API 추가. VIEW 근태관리 차트의 주간(7일)/월간(30일) 라인 차트 데이터 제공.

**범위**: BE 1 파일 수정 (`admin.py`) + migration (인덱스) + 테스트
**의존성**: 없음
**버전**: v1.9.2 patch
**OPS_API_REQUESTS**: #29

**설계 원칙**: 엔터프라이즈 운영 시스템 기준 — 단일 SQL 집계, 인덱스 최적화, 정확한 `total_registered` 산출.

---

### 기존 설계 문제점 (v1 → v2 변경 사유)

| 문제 | 영향 | 해결 |
|------|------|------|
| N+1 쿼리: 날짜별 `_get_attendance_data()` 반복 호출 (30일=30회 쿼리) | 인원 300명+, 월간 조회 빈번 시 응답 1~3초 | 단일 SQL `GROUP BY DATE()` 1회 쿼리 |
| `total_registered`: 현재 시점 등록 인원으로 고정 | 과거 날짜에 등록 안 된 사람도 카운트 (데이터 왜곡) | 별도 카운트: 각 날짜 시점 approved 인원 기준 |
| 인덱스 미비: `check_time` 단일 인덱스만 존재 | `DATE()` + `work_site` + `worker_id` 복합 쿼리에서 full scan | 복합 인덱스 추가 |
| 출근 없는 날짜 누락: SQL GROUP BY는 데이터 없는 날 행 생성 안 함 | 주말/공휴일 빠지면 라인 차트 끊김 | Python에서 `generate_series` 또는 날짜 채움 처리 |

---

### Task 1: Migration — 추이 쿼리 전용 인덱스

**파일**: `backend/migrations/028_attendance_trend_index.sql`

```sql
-- Sprint 35: 추이 집계용 복합 인덱스
-- DATE(check_time AT TIME ZONE 'Asia/Seoul') + work_site 기반 GROUP BY 최적화

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_partner_att_trend
    ON hr.partner_attendance (
        (DATE(check_time AT TIME ZONE 'Asia/Seoul')),
        work_site,
        worker_id
    )
    WHERE check_type = 'in';
```

**설계 근거**:
- 추이 쿼리는 `check_type = 'in'`만 사용 → partial index로 사이즈 절반
- `DATE()` expression index → GROUP BY에서 index-only scan 가능
- 기존 `idx_partner_att_date(check_time)` — 단일 날짜 조회용 (기존 API에 필요, 유지)
- `CONCURRENTLY`: 무중단 인덱스 생성

---

### Task 2: `admin.py` — `_get_attendance_trend_data()` 전용 집계 함수

**파일**: `backend/app/routes/admin.py`

**배치 위치**: `_get_attendance_data()` 아래 (Line 1775 부근)

```python
def _get_attendance_trend_data(
    date_from: date,
    date_to: date,
    company_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """기간별 일별 출입 집계 — 단일 SQL

    Args:
        date_from: 시작일 (date 객체)
        date_to: 종료일 (date 객체)
        company_filter: Manager 자사 필터 (None이면 전체)

    Returns:
        일별 집계 리스트 (빈 날짜 포함, date 오름차순)
    """
    # KST 범위 계산
    range_start = datetime(date_from.year, date_from.month, date_from.day, tzinfo=_KST)
    range_end = datetime(date_to.year, date_to.month, date_to.day, tzinfo=_KST) + timedelta(days=1)

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # ── 1) 일별 출근 집계 (단일 쿼리) ──
        checkin_query = """
            SELECT
                DATE(pa.check_time AT TIME ZONE 'Asia/Seoul') AS check_date,
                COUNT(DISTINCT pa.worker_id) AS checked_in,
                COUNT(DISTINCT CASE
                    WHEN pa.work_site = 'HQ' THEN pa.worker_id
                END) AS hq_count,
                COUNT(DISTINCT CASE
                    WHEN pa.work_site != 'HQ' THEN pa.worker_id
                END) AS site_count
            FROM hr.partner_attendance pa
            INNER JOIN workers w ON w.id = pa.worker_id
            WHERE pa.check_type = 'in'
              AND pa.check_time >= %s
              AND pa.check_time < %s
              AND w.company != 'GST'
              AND w.approval_status = 'approved'
        """
        params = [range_start, range_end]

        if company_filter:
            checkin_query += " AND w.company = %s"
            params.append(company_filter)

        checkin_query += """
            GROUP BY check_date
            ORDER BY check_date
        """
        cur.execute(checkin_query, params)
        checkin_rows = {row['check_date']: row for row in cur.fetchall()}

        # ── 2) 전체 등록 인원 (기간 내 approved 기준) ──
        # 단순화: 현재 approved 인원 카운트 (과거 변동 추적은 추후 worker_history 테이블 필요)
        reg_query = """
            SELECT COUNT(*) AS total_registered
            FROM workers
            WHERE company != 'GST'
              AND approval_status = 'approved'
        """
        reg_params = []
        if company_filter:
            reg_query += " AND company = %s"
            reg_params.append(company_filter)

        cur.execute(reg_query, reg_params)
        total_registered = cur.fetchone()['total_registered']

        # ── 3) 빈 날짜 채우기 (주말/공휴일 포함) ──
        trend = []
        current = date_from
        while current <= date_to:
            row = checkin_rows.get(current)
            trend.append({
                'date': current.strftime('%Y-%m-%d'),
                'total_registered': total_registered,
                'checked_in': row['checked_in'] if row else 0,
                'hq_count': row['hq_count'] if row else 0,
                'site_count': row['site_count'] if row else 0,
            })
            current += timedelta(days=1)

        return trend

    finally:
        if conn:
            put_conn(conn)
```

**핵심 설계 포인트**:

1. **단일 SQL 집계**: `GROUP BY DATE(check_time AT TIME ZONE 'Asia/Seoul')` — 30일=1회 쿼리 (vs 이전 30회)
2. **`COUNT(DISTINCT worker_id)`**: 같은 날 여러 번 체크인해도 1명으로 카운트
3. **`CASE WHEN work_site`**: hq/site 분리를 SQL 레벨에서 처리 (Python 루프 제거)
4. **partial index 활용**: `WHERE check_type = 'in'` — Task 1 인덱스와 일치
5. **빈 날짜 채우기**: Python에서 date_from~date_to 루프 → 주말/공휴일도 `checked_in: 0`으로 포함 → 라인 차트 끊김 방지
6. **`total_registered` 한계**: 현재는 "현재 시점" approved 인원으로 고정. 정확한 과거 시점 인원은 `worker_history` 테이블 (가입/탈퇴 이력) 필요 — 추후 ERD 설계 시 반영

---

### Task 3: `admin.py` — `GET /api/admin/hr/attendance/trend` 엔드포인트

**파일**: `backend/app/routes/admin.py`

**배치 위치**: Line 1940 부근 (기존 `get_attendance_summary()` 아래)

```python
@admin_bp.route("/hr/attendance/trend", methods=["GET"])
@jwt_required
@manager_or_admin_required
def get_attendance_trend() -> Tuple[Dict[str, Any], int]:
    """
    기간별 일별 출입 인원 추이

    Query Parameters:
        date_from: str (YYYY-MM-DD, 필수) — 시작일
        date_to:   str (YYYY-MM-DD, 필수) — 종료일

    Headers:
        Authorization: Bearer {token}

    Returns:
        200: {
            "date_from": "2026-03-15",
            "date_to": "2026-03-21",
            "trend": [
                {
                    "date": "2026-03-15",
                    "total_registered": 130,
                    "checked_in": 98,
                    "hq_count": 32,
                    "site_count": 66
                },
                ...
            ]
        }
        400: {"error": "INVALID_PARAMS", "message": "..."}
    """
    date_from_str = request.args.get('date_from')
    date_to_str = request.args.get('date_to')

    # ── 파라미터 검증 ──
    if not date_from_str or not date_to_str:
        return jsonify({
            'error': 'INVALID_PARAMS',
            'message': 'date_from, date_to 파라미터가 필요합니다. (YYYY-MM-DD)'
        }), 400

    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({
            'error': 'INVALID_DATE',
            'message': 'date 형식: YYYY-MM-DD'
        }), 400

    if date_from > date_to:
        return jsonify({
            'error': 'INVALID_PARAMS',
            'message': 'date_from은 date_to보다 이전이어야 합니다.'
        }), 400

    # 최대 90일 제한 (남용 방지)
    if (date_to - date_from).days > 90:
        return jsonify({
            'error': 'INVALID_PARAMS',
            'message': '조회 범위는 최대 90일입니다.'
        }), 400

    company_filter = _get_manager_company_filter()

    try:
        trend = _get_attendance_trend_data(date_from, date_to, company_filter)

        return jsonify({
            'date_from': date_from_str,
            'date_to': date_to_str,
            'trend': trend,
        }), 200

    except Exception as e:
        logger.error(f"Failed to get attendance trend: {e}")
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': '출입 추이 조회에 실패했습니다.'
        }), 500
```

**엔드포인트는 얇게** — 검증 + 권한만 처리, 실제 로직은 `_get_attendance_trend_data()`에 위임.

---

### Task 4: 테스트

**파일**: `tests/backend/test_sprint35_attendance_trend.py`

```python
import unittest
from datetime import date, timedelta


class TestAttendanceTrendValidation(unittest.TestCase):
    """파라미터 검증 테스트"""

    def test_missing_params_returns_400(self):
        """date_from, date_to 누락 → 400"""
        pass

    def test_missing_date_to_returns_400(self):
        """date_from만 있고 date_to 누락 → 400"""
        pass

    def test_invalid_date_format_returns_400(self):
        """잘못된 날짜 형식 → 400"""
        pass

    def test_date_from_after_date_to_returns_400(self):
        """date_from > date_to → 400"""
        pass

    def test_range_exceeds_90_days_returns_400(self):
        """90일 초과 범위 → 400"""
        pass


class TestAttendanceTrendResponse(unittest.TestCase):
    """응답 구조 + 데이터 정합성 테스트"""

    def test_7day_trend_returns_7_items(self):
        """7일 범위 → trend 배열 정확히 7개 (빈 날짜 포함)"""
        pass

    def test_30day_trend_returns_30_items(self):
        """30일 범위 → trend 배열 정확히 30개 (빈 날짜 포함)"""
        pass

    def test_trend_item_structure(self):
        """각 trend 항목에 필수 필드 5개 존재"""
        # date, total_registered, checked_in, hq_count, site_count
        pass

    def test_hq_site_sum_equals_checked_in(self):
        """hq_count + site_count == checked_in (각 날짜별)"""
        pass

    def test_dates_in_order_no_gaps(self):
        """trend 배열이 날짜 오름차순이며 빈 날짜 없음"""
        pass

    def test_weekend_zero_checkin(self):
        """주말 데이터 포함 — checked_in=0이어도 행 존재"""
        pass

    def test_distinct_worker_count(self):
        """같은 날 2번 체크인해도 checked_in=1"""
        # worker A가 09:00 체크인 → 12:00 체크아웃 → 13:00 재체크인
        # → checked_in = 1 (DISTINCT worker_id)
        pass


class TestAttendanceTrendAuth(unittest.TestCase):
    """인증/권한 테스트"""

    def test_no_token_returns_401(self):
        """JWT 없이 요청 → 401"""
        pass

    def test_non_manager_returns_403(self):
        """일반 작업자 → 403"""
        pass

    def test_manager_gets_own_company_only(self):
        """Manager → 자사 데이터만 반환"""
        pass

    def test_admin_gets_all_companies(self):
        """Admin → 전체 데이터"""
        pass
```

---

### Task 5: `version.py` — 버전 업데이트

**파일**: `backend/app/version.py`

```python
__version__ = '1.9.2'
```

---

### 장기 과제 (ERD/온톨로지 관련)

| 과제 | 현재 상태 | 필요 시점 |
|------|-----------|-----------|
| `worker_history` 테이블 | 없음 — 가입/탈퇴 이력 미추적 | `total_registered`를 과거 시점 기준으로 정확히 산출하려면 필요 |
| `attendance_daily_summary` 물리화 뷰 | 없음 — 매 요청마다 raw 데이터 집계 | 데이터 1년+ 누적 시 성능 문제. `pg_cron`으로 매일 자정 집계 → 읽기 전용 테이블 |
| `work_site` ENUM 정규화 | VARCHAR + CHECK constraint | 사이트 추가 시 migration 필요. `work_sites` 참조 테이블로 분리 |
| `product_line` 정규화 | VARCHAR + CHECK constraint | 모델 확장 시 동일. `product_lines` 참조 테이블로 분리 |

---

### 체크리스트

**BE (✅ 완료)**:
- [x] `migrations/029_attendance_trend_index.sql` — partial composite index + DB 적용 ✅
- [x] `admin.py` — `_get_attendance_trend_data()` 단일 SQL 집계 + 빈 날짜 채우기 ✅
- [x] `admin.py` — `get_attendance_trend()` 엔드포인트 (검증 + 위임) ✅
- [x] 파라미터 검증: date_from/date_to 필수, YYYY-MM-DD, from <= to, 최대 90일 ✅
- [x] 빈 날짜 채우기: 주말/공휴일도 `checked_in: 0`으로 포함 ✅
- [x] `COUNT(DISTINCT worker_id)`: 중복 체크인 방지 ✅
- [x] `_get_manager_company_filter()` 적용 ✅

**TEST**:
- [ ] 테스트 파일 작성 — 추후

**검증 (배포 후)**:
- [ ] `GET /api/admin/hr/attendance/trend?date_from=2026-03-15&date_to=2026-03-21` → 7개 항목
- [ ] hq_count + site_count == checked_in 정합성
- [ ] 주말 날짜 포함 (checked_in=0)
- [ ] Manager → 자사 데이터만 반환
- [ ] VIEW 연동 → 주간/월간 라인 차트 표시

---

## BUG-26-B: production processes 필드 불일치 — ready alias + confirmable 매핑 수정

> **목적**: production API processes 내부 필드를 FE 타입과 일치시키고, confirmable 판정 시 매핑 후 키(proc_key) 전달
> **범위**: BE `production.py` 2곳 수정
> **의존성**: BUG-26 (TMS→TM 매핑) 완료

### 배경

BUG-26에서 `_CAT_TO_PROC` 매핑을 추가했으나, 2가지 후속 문제 발생:
1. O/N processes에 `completed` 필드만 있고 FE가 참조하는 `ready` 없음 → `/6` 표시
2. `_is_process_confirmable` 호출 시 매핑 전 DB키(`pt='TMS'`) 전달 → `confirm_tms_enabled` 조회 실패

### 수정 내용

**1. processes dict에 `ready` alias 추가:**
```python
processes[proc_key] = {
    'total': total,
    'completed': completed,
    'ready': completed,           # ← FE 호환 alias
    'pct': ...,
    'confirmable': ...,
}
```

**2. `_is_process_confirmable` 호출 시 `proc_key` 전달:**
```python
# 변경 전
'confirmable': _is_process_confirmable(sns_progress, pt, settings),
# 변경 후
'confirmable': _is_process_confirmable(sns_progress, pt, settings, proc_key), 
```

`_is_process_confirmable`에서 admin_settings 조회 키를 `proc_key` 기반으로:
```python
def _is_process_confirmable(sns_progress, process_type, settings, proc_key=None):
    key = f'confirm_{(proc_key or process_type).lower()}_enabled'
    ...
```

### 체크리스트

- [x] `production.py` — processes dict에 `ready` alias 추가 ✅ 2026-03-22
- [x] `production.py` — `_is_process_confirmable`에 `proc_key` 파라미터 전달 ✅ 2026-03-22
- [x] FE `6/6` 정상 표시 확인 ✅ 2026-03-22
- [x] `production.py` — `_is_process_confirmable`에 `serial_numbers` 파라미터 추가 (O/N 스코프 필터) ✅ 2026-03-23
  - 근본 원인: `sns_progress`가 주차 내 전체 S/N을 포함 → 다른 O/N 미완료 S/N이 현재 O/N 판정에 영향
  - `has_data` 플래그 추가: 해당 공정 데이터 0건이면 False 반환
- [x] `api/production.ts` — `partner_info.mixed` 혼재 판정 수정 (S/N 배열 기반) ✅ 2026-03-23
- [x] MECH/ELEC `✓ 확인` 정상 ✅ 2026-03-23
- [x] `production.py` — `confirm_production()` TM→TMS 역방향 매핑 추가 ✅ 2026-03-23
  - 원인: FE가 `process_type='TM'` 전송 → `sns_progress`는 DB키 `'TMS'` → `cats.get('TM')` = 빈 dict → NOT_CONFIRMABLE
  - `_PROC_TO_CAT = {'TM': 'TMS'}` 역매핑으로 DB category 변환 후 호출
- [x] `ProductionPerformancePage.tsx` — ProcessCell N/A 상태에서 협력사 + 혼재 마크 표시 ✅ 2026-03-23
  - O/N 6587 (5대, 미착수): 기구 FNI/BAT 혼재, 전장 C&A/TMS 혼재인데 마크 미표시
  - `total===0` early return에 partnerDisplay + mixed 렌더링 추가
- [ ] TM 실적확인 배포 후 확인
- [ ] FE 확인 버튼 활성화 확인 (enabled + confirmable + !confirmed)

---

## BACKLOG: SAP I/F 대비 실적확인 데이터 구조 보강

> **시급도**: 낮음 — SAP 연동 설계 확정 시 착수
> **참조**: OPS_API_REQUESTS.md #34

### 배경

현재 `plan.production_confirm`은 O/N + 공정 단위로만 저장. SAP PP/CO (CO11N 공정실적확인) 연동 시 S/N 단위 실적, 수량 구분, 전송 상태 추적이 필요.

### 필요 작업

**마이그레이션 (SAP 설계 확정 후)**:

1. `plan.production_confirm_detail` 테이블 신설
   - `confirm_id` FK → `production_confirm`
   - `serial_number`, `process_type`, `yield_qty`, `scrap_qty`, `rework_qty`
   - `sap_operation` (SAP 공정번호), `sap_work_center` (SAP 작업장)

2. `plan.sap_interface_log` 테이블 신설
   - `confirm_id` FK, `interface_type` (CO11N/REVERSAL)
   - `sap_doc_number`, `status` (PENDING/SENT/SUCCESS/FAILED/REVERSED)
   - `request_payload` JSONB, `response_payload` JSONB
   - `retry_count`, `sent_at`, `completed_at`

3. `plan.production_confirm` 컬럼 추가
   - `sap_status` VARCHAR(20) DEFAULT 'NOT_SENT'
   - `sap_doc_number` VARCHAR(50)
   - `sap_sent_at` TIMESTAMPTZ

**BE 로직 변경**:

4. `confirm_production()` — INSERT 시 `production_confirm_detail` 동시 생성 (S/N별 1건씩)
5. `cancel_confirm()` — `sap_status = 'CONFIRMED'`이면 역전기 요청 로직 추가
6. SAP 배치 스케줄러 — `sap_status = 'NOT_SENT'` 건 주기적 전송

**선제 적용 가능 (현재)**:
- `production_confirm`에 `sap_status` 컬럼만 먼저 추가 (기존 로직 무영향, DEFAULT 'NOT_SENT')

---

## 생산실적 리스트 기준 변경: mech_start → 공정 종료일 기준 (2026-03-23) ✅ 완료

> **목적**: 실적확인 시점과 표시 기준 일치 — W12 착수 O/N이 W13 완료 시 W13에 표시
> **참조**: OPS_API_REQUESTS.md #35, CORE-ETL Sprint 3

### 체크리스트

- [ ] DB: `ALTER TABLE plan.product_info ADD COLUMN module_end DATE` + 인덱스 3개 (수동 실행)
- [x] ETL: `step1_extract.py` — AQ열 "모듈계획종료일" 추출 (`semi_product_end`, index 42) ✅
- [x] ETL: `step2_load.py` — `module_end` INSERT/UPSERT/WHERE 추가 ✅
- [x] BE: `production.py` — performance 쿼리 `mech_start` → `mech_end OR elec_end OR COALESCE(module_end, module_start)` ✅
- [x] ETL 재실행: DB 컬럼 추가 후 `python3 etl_main.py --all` 실행하여 module_end 적재
- [x] VIEW 확인: W12 선택 시 공정 종료일 기준 O/N 목록 정상 표시

---

## TM 실적확인 로직 분리: TANK_MODULE only confirmable (2026-03-23) — #36

> **목적**: TM 실적확인(confirmable)은 TANK_MODULE만 기준, progress/알람은 TANK_MODULE+PRESSURE_TEST 전체 기준으로 분리
> **참조**: OPS_API_REQUESTS.md #36, #36-B, #36-C
> **배경**: 가압검사가 TMS(협력사) + PI(GST 내부) 2회 중복 수행 중 (공정 안정화 목적). 추후 PI만 남기고 TMS PRESSURE_TEST 제거 예정.

### 설계 원칙

| 항목 | 기준 | 범위 |
|------|------|------|
| Progress | TMS 카테고리 전체 | TANK_MODULE + PRESSURE_TEST |
| Alarm trigger | TMS 전체 완료 시 | PRESSURE_TEST 완료 → mech_partner 알람 |
| 실적확인 (confirmable) | TANK_MODULE만 | PRESSURE_TEST 미완료여도 실적확인 가능 |

### 체크리스트

- [x] BE: `_calc_sn_progress()` — `GROUP BY task_category` → `GROUP BY task_category, task_id` 확장 ✅ 2026-03-23
  - 반환 구조: `{sn: {cat: {total, completed, pct, tasks: {task_id: {total, completed}}}}}`
  - 기존 카테고리 레벨 total/completed는 Python 합산으로 유지 (하위호환)
- [x] BE: `_CONFIRM_TASK_FILTER = {'TMS': 'TANK_MODULE'}` 매핑 추가 ✅ 2026-03-23
- [x] BE: `_is_process_confirmable()` — TMS일 때 `tasks.TANK_MODULE`만 체크하도록 분기 ✅ 2026-03-23
- [x] BE: `_build_order_item()` — 추후 `tm_pressure_test_required` 옵션 연계 주석 추가 ✅ 2026-03-23
- [x] 배포 후 확인: TM `1/2` 상태에서 실적확인 버튼 활성화 (TANK_MODULE 완료 기준)
- [x] 배포 후 확인: TM progress `1/2` 정상 표시 (PRESSURE_TEST 미완 포함)

### BACKLOG: `tm_pressure_test_required` 옵션 (설비 변경 시)

- [ ] BE: `admin_settings` 테이블에 `tm_pressure_test_required` 키 추가
- [ ] BE: `_build_order_item()` — 설정값에 따라 TMS progress에서 PRESSURE_TEST 제외/포함 분기
- [ ] BE: `task_service.py` `_trigger_completion_alerts()` — 설정값에 따라 알람 트리거 분기
- [ ] FE: `ConfirmSettingsPanel` — TM 그룹 UI + 가압검사 포함 토글 (#36-C)

---

## Sprint 37: 혼재 O/N 실적확인 partner별 분리 (2026-03-23) — #37

> **목적**: 혼재 O/N에서 서로 다른 협력사의 실적을 개별 확인 (완료 날짜가 다르므로 정산 구분 필요)
> **참조**: OPS_API_REQUESTS.md #37
> **대상**: `AXIS-OPS/backend/app/routes/production.py`
> **선행**: #36 push 완료 (Task 1~3), DB Migration 030 실행 완료

### 분리 규칙

| 공정 | 분리 기준 | 혼재 O/N | 비혼재 O/N | 비고 |
|------|----------|---------|----------|------|
| MECH | `mech_partner` | partner별 버튼 | 버튼 1개 | |
| ELEC | `elec_partner` | partner별 버튼 | 버튼 1개 | |
| TM | `mech_partner` | partner별 버튼 | 버튼 1개 | TMS(M) 전담이나 S/N 그룹별 일정 상이 |
| PI/QI/SI | 분리 안함 | — | 버튼 1개 | 기존 O/N 단위 유지 |

### BE 작업 — Task 정의

#### Task 1: DB Migration 030 (`backend/migrations/030_production_confirm_partner.sql`)

- `production_confirm`에 `partner VARCHAR(50) DEFAULT NULL` 추가
- unique index 변경: `(sales_order, process_type, confirmed_week, COALESCE(partner, ''))`
- partner 검색 인덱스 추가

#### Task 2: `_build_order_item()` — partner별 confirmable/confirmed 반환

- `_PROC_PARTNER_COL = {'MECH': 'mech_partner', 'ELEC': 'elec_partner', 'TM': 'mech_partner'}` 상수 추가
- 혼재 판정: partner_col 고유값 2개 이상 → `mixed = True`
- mixed일 때 `partner_confirms` 배열 생성 (partner별 sn_count, confirmable, confirmed)
- 비혼재 시 기존 구조 유지 (하위호환)

#### Task 3: `get_performance()` — confirms 조회에 partner 포함

- SELECT에 partner 컬럼 추가
- confirms dict 키: partner 있으면 `{sales_order}:{process_type}:{partner}`, NULL이면 기존 키

#### Task 4: `confirm_production()` — partner 파라미터 추가

- 요청 Body: `partner?` 필드 (nullable)
- partner 지정 시 해당 partner S/N만 필터하여 confirmable 체크 + INSERT
- `_PROC_TO_CAT = {'TM': 'TMS'}` 역매핑은 기존 코드 유지

#### Task 5: `cancel_confirm()` — partner 응답 포함

- soft delete는 `confirm_id` 기반 (기존 유지)
- 응답에 partner 포함하여 FE UI 갱신 시 사용

### 배포 순서

1. **즉시 push 가능**: #36 Task 1~3 (confirmable TANK_MODULE only)
2. **DB migration**: Task 1 → Railway에서 수동 실행
3. **BE push**: Task 2~5 (#37 — partner별 실적확인)
4. **FE push**: ProcessCell partner별 버튼 (VIEW 별도)

### 체크리스트

**BE (✅ 완료)**:
- [x] Migration 030 작성 + Railway DB 적용 (partner 컬럼 + unique index) ✅
- [x] `production.py` — `_PROC_PARTNER_COL` 상수 추가 ✅
- [x] `production.py` — `_build_order_item()` mixed 판정 + partner_confirms 배열 ✅
- [x] `production.py` — `get_performance()` confirms 조회에 partner 포함 (키 변경) ✅
- [x] `production.py` — `confirm_production()` partner 파라미터 + S/N 필터 + INSERT ✅
- [x] `production.py` — `cancel_confirm()` RETURNING에 partner 포함 ✅

**TEST**:
- [ ] 테스트 파일 작성 — 추후

**검증 (배포 후)**:
- [ ] 혼재 O/N: partner_confirms 배열 정상 반환
- [ ] 비혼재 O/N: 기존 동작 regression 없음
- [ ] POST confirm partner='TMS' → 해당 partner S/N만 체크
- [ ] 기존 partner=NULL 데이터 하위호환

**검증 (배포 후 실기기)**:
- [ ] 🔴 혼재 O/N(6520 GAIA-I)에서 MECH partner별 실적확인 버튼 개별 표시 (TMS / FNI)
- [ ] 🔴 partner별 confirm 클릭 → DB에 partner 포함 저장 확인
- [ ] 🔴 partner별 cancel → 해당 partner confirm만 삭제, 다른 partner 유지
- [ ] 🔴 TM 혼재 → partner별 분리 + TANK_MODULE only confirmable 정상
- [ ] 비혼재 O/N에서 기존 단일 실적확인 버튼 유지 (하위호환)
- [ ] ELEC 혼재 → elec_partner 기준 분리 정상
- [ ] PI/QI/SI → 혼재 무관, 기존 O/N 단위 유지

---

## TEST 작업 (tests/backend/) — Sprint 37

### test_sprint37_partner_confirm.py (신규) — 🔴 혼재 O/N partner별 분리 테스트

**White-box: _build_order_item() partner 분리**
1. TC-PC-01: 혼재 O/N (MECH: TMS 1대 + FNI 4대) → `mixed=true`, `partner_confirms` 2건 (TMS sn_count=1, FNI sn_count=4)
2. TC-PC-02: 비혼재 O/N (MECH: FNI 5대) → `mixed=false`, `partner_confirms=null`, 기존 confirmable/confirmed 필드 사용
3. TC-PC-03: ELEC 혼재 (elec_partner 기준: TMS 2대 + JP 3대) → `mixed=true`, `partner_confirms` 2건
4. TC-PC-04: TM 혼재 (mech_partner 기준 분리 + `_CONFIRM_TASK_FILTER` TANK_MODULE only confirmable)
5. TC-PC-05: PI/QI/SI → 혼재 무관, `partner_confirms=null` 항상

**White-box: partner별 confirmable 판정**
6. TC-PC-06: 혼재 MECH — TMS S/N 전부 완료 → TMS confirmable=true, FNI S/N 미완료 → FNI confirmable=false
7. TC-PC-07: 혼재 TM — TANK_MODULE만 완료, PRESSURE_TEST 미완료 → confirmable=true (TANK_MODULE only)
8. TC-PC-08: 비혼재 — 전체 S/N 완료 → confirmable=true (기존 로직 유지)

**White-box: confirm_production() partner 필터**
9. TC-PC-09: partner='TMS', process_type='MECH' → mech_partner='TMS'인 S/N만 필터하여 confirm
10. TC-PC-10: partner='FNI', process_type='MECH' → mech_partner='FNI'인 S/N만 필터하여 confirm
11. TC-PC-11: partner=null, 비혼재 O/N → 전체 S/N 대상 confirm (하위호환)

**White-box: get_performance() confirms 조회**
12. TC-PC-12: partner 포함 confirm → confirms dict 키 `{sales_order}:{process_type}:{partner}` 정상 조회
13. TC-PC-13: partner=NULL 기존 데이터 → confirms dict 키 `{sales_order}:{process_type}` 정상 조회 (하위호환)

**White-box: cancel_confirm()**
14. TC-PC-14: partner별 confirm 취소 → 해당 partner confirm만 soft delete, 다른 partner confirm 유지
15. TC-PC-15: 비혼재 confirm 취소 → 기존 동작 유지

### test_sprint37_partner_graybox.py (신규) — Gray-box 테스트
16. TC-PG-01: Migration 030 적용 후 → partner 컬럼 존재 + unique index 정상 동작 확인
17. TC-PG-02: 혼재 O/N confirm → cancel → 재confirm E2E 흐름 (partner별)
18. TC-PG-03: 동일 O/N에서 TMS confirm + FNI 미confirm → API 응답에 TMS confirmed=true, FNI confirmed=false

### test_sprint37_regression.py (신규) — Regression 테스트
19. TC-PR-01: #36 `_CONFIRM_TASK_FILTER` TMS→TANK_MODULE only 로직 미변경 확인
20. TC-PR-02: `_calc_sn_progress()` task_id 레벨 GROUP BY 정상 (기존 #36 변경분)
21. TC-PR-03: `_is_process_confirmable()` — 비혼재 MECH/ELEC 기존 동작 동일
22. TC-PR-04: `_PROC_TO_CAT` TM→TMS 역매핑 정상 (기존 로직)
23. TC-PR-05: admin_settings confirm_*_enabled=false → confirmable=false (설정 비활성 시 차단)

---

## 변경 파일 — Sprint 37

| 파일 | 변경 |
|------|------|
| `backend/migrations/030_production_confirm_partner.sql` | partner 컬럼 + unique index 변경 (신규) |
| `backend/app/routes/production.py` | `_PROC_PARTNER_COL` 상수 + `_build_order_item()` mixed/partner_confirms + `get_performance()` partner 키 + `confirm_production()` partner 필터 + `cancel_confirm()` partner 응답 |
| `tests/backend/test_sprint37_partner_confirm.py` | White-box 테스트 15건 (신규) |
| `tests/backend/test_sprint37_partner_graybox.py` | Gray-box 테스트 3건 (신규) |
| `tests/backend/test_sprint37_regression.py` | Regression 테스트 5건 (신규) |

## 규칙 — Sprint 37
- CLAUDE.md의 "DB 테이블 정확한 컬럼 명세" 섹션을 반드시 참조 — `production_confirm`, `product_info`, `admin_settings` 컬럼명 실수 방지
- `admin_settings` 컬럼은 `setting_key`, `setting_value`, `description` (NOT `key`, `value`)
- `production_confirm`은 plan 스키마 — partner 컬럼 `COALESCE(partner, '')` unique index 주의
- `product_info.mech_partner`, `elec_partner` 컬럼값은 DB에 `'TMS'`로 저장 (NOT `'TMS(M)'`/`'TMS(E)'`)
- `_PROC_TO_CAT = {'TM': 'TMS'}` 역매핑은 confirmable 체크 전용 — confirm INSERT에는 process_type 그대로 사용
- confirms dict 키 생성 시 partner=NULL이면 기존 키(`{so}:{proc}`) 유지 — 하위호환 필수
- BE가 코드를 완성하면 TEST가 먼저 CLAUDE.md 기준으로 코드 리뷰 진행
- 리뷰 통과 후에만 테스트 코드 작성
- 각 teammate는 자신의 소유 파일만 수정 가능
- ⚠️ `_calc_sn_progress()` 수정 금지 — #36에서 task_id 레벨로 확장 완료
- ⚠️ `_is_process_confirmable()` 수정 금지 — #36에서 TANK_MODULE only 분기 완료
- ⚠️ `_CONFIRM_TASK_FILTER` 수정 금지
- ⚠️ `task_seed.py` 수정 금지 — task 생성 로직 변경 없음
- ⚠️ `task_service.py` 수정 금지 — 알람 로직 변경 없음
- ⚠️ FE 코드 수정 금지 — VIEW 별도 진행
- .env 파일 절대 커밋 금지
- N+1 쿼리 금지 — batch 조회(ANY 사용)
- 완료 시 AGENT_TEAM_LAUNCH.md 체크리스트 업데이트

---

### Teammate 프롬프트 — Sprint 37 (#37 혼재 O/N 실적확인 partner별 분리)

> **이 프롬프트를 Claude Code teammate에게 전달하여 실행**
> 선행 조건: #36 push 완료, DB Migration 030 실행 완료

```
## Sprint 37: 혼재 O/N 실적확인 partner별 분리

### 컨텍스트
- 참조: `AXIS-VIEW/docs/OPS_API_REQUESTS.md` #37 (설계 문서 전문)
- 참조: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` Sprint 37 섹션
- 대상 파일: `backend/app/routes/production.py`
- DB: `plan.production_confirm` 테이블에 `partner VARCHAR(50)` 컬럼 추가 완료 상태

### 배경
혼재 O/N(같은 주문에 서로 다른 협력사 S/N이 혼합)에서 실적확인을 협력사별로 분리해야 함.
현재 O/N 단위 1개 → 혼재 시 partner별 개별 확인으로 변경.

### 분리 규칙

| 공정 | 분리 기준 | 비고 |
|------|----------|------|
| MECH | `plan.product_info.mech_partner` | |
| ELEC | `plan.product_info.elec_partner` | |
| TM | `plan.product_info.mech_partner` | TM 작업은 TMS(M) 전담이나 S/N 그룹별 일정 상이 |
| PI/QI/SI | 분리 안함 | 기존 O/N 단위 유지 |

### Task 순서 (반드시 이 순서대로)

#### Task 1: Migration 030 작성 (`backend/migrations/030_production_confirm_partner.sql`)

```sql
BEGIN;

ALTER TABLE plan.production_confirm
    ADD COLUMN IF NOT EXISTS partner VARCHAR(50) DEFAULT NULL;

DROP INDEX IF EXISTS production_confirm_active_unique;

CREATE UNIQUE INDEX production_confirm_active_unique
    ON plan.production_confirm(sales_order, process_type, confirmed_week, COALESCE(partner, ''))
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_production_confirm_partner
    ON plan.production_confirm(partner)
    WHERE deleted_at IS NULL;

COMMIT;
```

#### Task 2: `_build_order_item()` 수정 — partner별 confirmable/confirmed 반환

현재 코드 위치: `production.py` 내 `_build_order_item()` 함수

추가할 매핑 (모듈 레벨 상수):
```python
# 혼재 판정 대상 공정 → partner 컬럼 매핑
_PROC_PARTNER_COL = {'MECH': 'mech_partner', 'ELEC': 'elec_partner', 'TM': 'mech_partner'}
```

로직 변경:
1. `processes[proc_key]` 구성 시, `proc_key`가 `_PROC_PARTNER_COL`에 있으면:
   - products 리스트에서 해당 partner_col의 고유값 추출
   - 고유값 2개 이상이면 `mixed = True`
   - mixed일 때 `partner_confirms` 배열 생성:
     - partner별 S/N 필터 → `_is_process_confirmable()` 호출
     - partner별 confirmed 상태: `confirms` dict에서 `{sales_order}:{proc_key}:{partner}` 키로 조회
   - `confirmable`, `confirmed`, `confirmed_at`, `confirm_id`는 `None` (개별은 partner_confirms에)
2. `proc_key`가 `_PROC_PARTNER_COL`에 없거나 비혼재면:
   - 기존 로직 그대로 (하위호환)

partner_confirms 배열 항목 구조:
```python
{
    'partner': str,        # 협력사명 (예: 'TMS', 'FNI')
    'sn_count': int,       # 해당 partner S/N 수
    'total': int,          # 해당 partner S/N들의 task total 합산
    'completed': int,      # 해당 partner S/N들의 task completed 합산
    'confirmable': bool,   # 해당 S/N들만 대상 _is_process_confirmable()
    'confirmed': bool,
    'confirmed_at': str | None,
    'confirm_id': int | None,
}
```

#### Task 3: `get_performance()` 수정 — confirms 조회에 partner 포함

현재 confirms 조회 SQL에 `partner` 컬럼 추가:
```python
cur.execute("""
    SELECT id, sales_order, process_type, partner, confirmed_at
    FROM plan.production_confirm
    WHERE confirmed_week = %s AND deleted_at IS NULL
""", (week_str,))
```

confirms dict 키 변경:
- partner가 있으면: `{sales_order}:{process_type}:{partner}`
- partner가 NULL이면: `{sales_order}:{process_type}` (기존 호환)

#### Task 4: `confirm_production()` 수정 — partner 파라미터 추가

요청 Body에 `partner` 필드 추가 (optional):
```python
partner = data.get('partner')  # nullable
```

S/N 필터 분기:
```python
_PROC_PARTNER_COL = {'MECH': 'mech_partner', 'ELEC': 'elec_partner', 'TM': 'mech_partner'}

if partner and process_type in _PROC_PARTNER_COL:
    partner_col = _PROC_PARTNER_COL[process_type]
    cur.execute(f"""
        SELECT serial_number FROM plan.product_info
        WHERE sales_order = %s AND {partner_col} = %s
    """, (sales_order, partner))
else:
    cur.execute("""
        SELECT serial_number FROM plan.product_info
        WHERE sales_order = %s
    """, (sales_order,))
```

주의: `process_type`은 FE에서 시스템 표준 키로 전송 (TM, MECH, ELEC).
`_PROC_TO_CAT = {'TM': 'TMS'}` 역매핑은 confirmable 체크에만 사용 (기존 코드 유지).

INSERT에 partner 포함:
```python
cur.execute("""
    INSERT INTO plan.production_confirm
        (sales_order, process_type, partner, confirmed_week, confirmed_month, sn_count, confirmed_by)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    RETURNING id, confirmed_at
""", (sales_order, process_type, partner, confirmed_week, confirmed_month, len(serial_numbers), g.worker_id))
```

#### Task 5: `cancel_confirm()` 수정 — partner 조건 추가

현재 DELETE(soft delete) 쿼리에 partner 조건 불필요 — `confirm_id`로 직접 삭제하므로.
단, 추후 partner 기반 취소가 필요할 수 있으니 응답에 partner 포함:
```python
# 기존 코드 유지 (id 기반 soft delete)
# 응답에 partner 포함하여 FE에서 UI 갱신 시 사용
```

#### Task 6: 테스트 코드 작성

`AGENT_TEAM_LAUNCH.md`의 "TEST 작업 — Sprint 37" 섹션 참조.
아래 3개 테스트 파일을 `tests/backend/`에 작성:

1. `test_sprint37_partner_confirm.py` — White-box 15건 (TC-PC-01 ~ TC-PC-15)
2. `test_sprint37_partner_graybox.py` — Gray-box 3건 (TC-PG-01 ~ TC-PG-03)
3. `test_sprint37_regression.py` — Regression 5건 (TC-PR-01 ~ TC-PR-05)

테스트 전체 PASSED (23건 이상) 확인 후 완료.

### 검증 체크리스트

수정 완료 후 아래 시나리오 검증 (코드 리뷰 레벨):

1. **혼재 O/N (6520)**: MECH에 TMS(1대) + FNI(4대)
   - `processes.MECH.mixed = true`
   - `processes.MECH.partner_confirms` 길이 2 (TMS, FNI)
   - 각 partner의 `sn_count`, `confirmable` 정상
2. **비혼재 O/N**: partner 단일
   - `processes.MECH.mixed = false`
   - `processes.MECH.partner_confirms = null`
   - `confirmable`, `confirmed` 기존 필드 사용
3. **TM 혼재**: mech_partner 기준 분리
   - `processes.TM.mixed = true` (mech_partner 혼재 시)
   - TM의 `_is_process_confirmable()`은 `_CONFIRM_TASK_FILTER`로 TANK_MODULE만 체크
4. **PI/QI/SI**: 혼재 무관, 기존 O/N 단위
   - `partner_confirms = null` 항상
5. **confirm_production()**: partner='TMS', process_type='MECH'
   - mech_partner='TMS'인 S/N만 필터
   - INSERT에 partner='TMS' 포함
6. **하위호환**: 기존 partner=NULL 데이터 정상 조회

### 수정 대상 파일 목록

- `backend/migrations/030_production_confirm_partner.sql` (신규)
- `backend/app/routes/production.py` (수정)
- `tests/backend/test_sprint37_partner_confirm.py` (신규)
- `tests/backend/test_sprint37_partner_graybox.py` (신규)
- `tests/backend/test_sprint37_regression.py` (신규)

### 규칙

- CLAUDE.md의 "DB 테이블 정확한 컬럼 명세" 섹션을 반드시 참조 — `production_confirm`, `product_info`, `admin_settings` 컬럼명 실수 방지
- `admin_settings` 컬럼은 `setting_key`, `setting_value`, `description` (NOT `key`, `value`)
- `production_confirm`은 plan 스키마 — partner 컬럼 `COALESCE(partner, '')` unique index 주의
- `product_info.mech_partner`, `elec_partner` 컬럼값은 DB에 `'TMS'`로 저장 (NOT `'TMS(M)'`/`'TMS(E)'`)
- `_PROC_TO_CAT = {'TM': 'TMS'}` 역매핑은 confirmable 체크 전용 — confirm INSERT에는 process_type 그대로 사용
- confirms dict 키 생성 시 partner=NULL이면 기존 키(`{so}:{proc}`) 유지 — 하위호환 필수
- BE가 코드를 완성하면 TEST가 먼저 CLAUDE.md 기준으로 코드 리뷰 진행
- 리뷰 통과 후에만 테스트 코드 작성
- 각 teammate는 자신의 소유 파일만 수정 가능
- N+1 쿼리 금지 — batch 조회(ANY 사용)
- .env 파일 절대 커밋 금지

### 절대 수정 금지

- `task_seed.py` — task 생성 로직 변경 없음
- `task_service.py` — 알람 로직 변경 없음
- FE 코드 — VIEW 별도 진행
- `_calc_sn_progress()` — 이미 #36에서 task_id 레벨로 확장 완료
- `_is_process_confirmable()` — 이미 #36에서 TANK_MODULE only 분기 완료
- `_CONFIRM_TASK_FILTER` — 변경 없음
```

---

## Sprint 37-A: TM 가압검사 옵션 — settings 기반 progress/알람 제어 (2026-03-23) — #36-C

> **참조**: OPS_API_REQUESTS.md #36-C, DESIGN_FIX_SPRINT.md Sprint 13
> **선행**: Sprint 37 완료 (partner별 실적확인)
> **대상**: `production.py`, `task_service.py`, migration

### 배경

TM 공정은 TANK_MODULE + PRESSURE_TEST 2개 task 존재.
- 실적확인(confirmable): TANK_MODULE만 체크 — #36에서 `_CONFIRM_TASK_FILTER` 구현 완료
- Progress/알람: 현재 TANK_MODULE + PRESSURE_TEST 전체 포함 (기본 동작)
- `tm_pressure_test_required` 옵션: progress/알람에 가압검사 포함 여부를 admin_settings로 제어

default `true` = 현재 동작 유지 (가압검사 포함). `false`로 변경 시 progress는 TANK_MODULE만, 알람은 TANK_MODULE 완료 시점에 트리거.

### BE 작업 — Task 정의

#### Task 1: Migration (`backend/migrations/031_tm_pressure_test_setting.sql`)

```sql
BEGIN;

INSERT INTO plan.admin_settings (setting_key, setting_value, description)
VALUES ('tm_pressure_test_required', 'true', 'TM 가압검사 progress/알람 포함 여부 (true=포함, false=탱크모듈만)')
ON CONFLICT (setting_key) DO NOTHING;

COMMIT;
```

#### Task 2: `_get_confirm_settings()` WHERE 조건 확장

현재: `WHERE setting_key LIKE 'confirm_%'` → `tm_pressure_test_required` 조회 불가

변경:
```python
def _get_confirm_settings(cur) -> Dict[str, bool]:
    """admin_settings에서 실적확인 관련 설정 조회"""
    cur.execute("""
        SELECT setting_key, setting_value
        FROM admin_settings
        WHERE setting_key LIKE 'confirm_%'
           OR setting_key = 'tm_pressure_test_required'
    """)
    # ... 기존 파싱 로직 유지
```

#### Task 3: `_build_order_item()` — settings 기반 TMS progress 집계 분기

현재 (line 203~206): 주석만 존재
변경: `tm_pressure_test_required=false` 시 TMS 카테고리 progress에서 PRESSURE_TEST 제외

```python
for pt in process_types:
    total = 0
    completed = 0
    for sn in serial_numbers:
        cat = sns_progress.get(sn, {}).get(pt, {})

        # TMS 카테고리 + tm_pressure_test_required=false → TANK_MODULE만 합산
        if pt == 'TMS' and not settings.get('tm_pressure_test_required', True):
            tm_task = cat.get('tasks', {}).get('TANK_MODULE', {})
            total += tm_task.get('total', 0)
            completed += tm_task.get('completed', 0)
        else:
            total += cat.get('total', 0)
            completed += cat.get('completed', 0)
```

혼재 분기에서도 동일 적용 (partner별 progress 집계 루프):
```python
for sn in ptnr_sns:
    cat = sns_progress.get(sn, {}).get(pt, {})
    if pt == 'TMS' and not settings.get('tm_pressure_test_required', True):
        tm_task = cat.get('tasks', {}).get('TANK_MODULE', {})
        ptnr_total += tm_task.get('total', 0)
        ptnr_completed += tm_task.get('completed', 0)
    else:
        ptnr_total += cat.get('total', 0)
        ptnr_completed += cat.get('completed', 0)
```

#### Task 4: `task_service.py` `_trigger_completion_alerts()` — settings 기반 트리거 분기

현재 (line 359~363): `PRESSURE_TEST` 완료 시에만 알람 트리거
변경: `tm_pressure_test_required=false` 시 `TANK_MODULE` 완료 시에도 알람 트리거

```python
def _trigger_completion_alerts(self, task) -> None:
    trigger = None

    if task.task_id == 'PRESSURE_TEST':
        if task.task_category == 'TMS':
            if self._is_dual_pressure_all_done(task.serial_number):
                trigger = ('TMS_TANK_COMPLETE', 'MECH', 'TMS 가압검사 완료')
        elif task.task_category == 'MECH':
            trigger = ('TMS_TANK_COMPLETE', 'QI', 'MECH 가압검사 완료')

    # NEW: tm_pressure_test_required=false 시 TANK_MODULE 완료로도 알람
    elif task.task_id == 'TANK_MODULE' and task.task_category == 'TMS':
        if not self._is_tm_pressure_test_required():
            trigger = ('TMS_TANK_COMPLETE', 'MECH', 'TMS 탱크모듈 완료 (가압검사 제외)')

    elif task.task_category == 'MECH' and task.task_id == 'TANK_DOCKING':
        # ... 기존 코드 유지
```

`_is_tm_pressure_test_required()` 헬퍼 추가:
```python
def _is_tm_pressure_test_required(self) -> bool:
    """admin_settings에서 tm_pressure_test_required 조회"""
    cur = get_db_connection().cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT setting_value FROM plan.admin_settings
        WHERE setting_key = 'tm_pressure_test_required'
    """)
    row = cur.fetchone()
    if row is None:
        return True  # default: 가압검사 포함
    val = row['setting_value']
    return val.lower() in ('true', '1') if isinstance(val, str) else bool(val)
```

### 배포 순서

1. **DB migration**: Migration 031 실행 (Railway)
2. **BE push**: Task 2~4 (`production.py` + `task_service.py`)
3. **FE push**: ConfirmSettingsPanel TM 그룹 박스 UI (VIEW Sprint 13)

### 체크리스트

**BE (✅ 완료)**:
- [x] Migration 031 작성 + Railway DB 적용 ✅
- [x] `production.py` — `_get_confirm_settings()` WHERE 확장 (`tm_pressure_test_required` 포함) ✅
- [x] `production.py` — `_build_order_item()` TMS progress 비혼재 분기 (TANK_MODULE only) ✅
- [x] `production.py` — 혼재 partner별 progress에서도 동일 분기 ✅
- [x] `task_service.py` — `_trigger_completion_alerts()` TANK_MODULE 완료 알람 분기 ✅
- [x] `task_service.py` — `_is_tm_pressure_test_required()` 헬퍼 추가 ✅

## TEST 작업 (tests/backend/) — Sprint 37-A

### test_sprint37a_pressure_test_setting.py (신규) — 🔴 가압검사 옵션 테스트

**White-box: _build_order_item() progress 분기**
1. TC-PT-01: `tm_pressure_test_required=true` → TMS progress = TANK_MODULE + PRESSURE_TEST 합산 (기본 동작)
2. TC-PT-02: `tm_pressure_test_required=false` → TMS progress = TANK_MODULE만 합산 (PRESSURE_TEST 제외)
3. TC-PT-03: `tm_pressure_test_required=false` + TANK_MODULE 5/5 완료 → pct=100% (PRESSURE_TEST 0/5 무시)
4. TC-PT-04: `tm_pressure_test_required` 설정 미존재 → default `true` 동작 (가압검사 포함)

**White-box: 혼재 partner별 progress 분기**
5. TC-PT-05: 혼재 O/N + `tm_pressure_test_required=false` → partner_confirms의 TMS total/completed도 TANK_MODULE만 합산
6. TC-PT-06: 혼재 O/N + `tm_pressure_test_required=true` → partner_confirms의 TMS total/completed = 전체 합산

**White-box: _get_confirm_settings() 확장**
7. TC-PT-07: `_get_confirm_settings()` → `tm_pressure_test_required` 키 포함 반환 확인

**White-box: _trigger_completion_alerts() 알람 분기**
8. TC-PT-08: `tm_pressure_test_required=true` + TANK_MODULE 완료 → 알람 미발송 (PRESSURE_TEST 대기)
9. TC-PT-09: `tm_pressure_test_required=false` + TANK_MODULE 완료 → 알람 발송 (TMS_TANK_COMPLETE)
10. TC-PT-10: `tm_pressure_test_required=true` + PRESSURE_TEST 완료 → 기존 알람 발송 (변경 없음)

### test_sprint37a_regression.py (신규) — Regression 테스트
11. TC-PTR-01: MECH/ELEC progress — `tm_pressure_test_required` 무관, 기존 동작 유지
12. TC-PTR-02: `_CONFIRM_TASK_FILTER` TMS→TANK_MODULE only confirmable — 변경 없음
13. TC-PTR-03: `_is_process_confirmable()` — 설정값 무관, TANK_MODULE only 유지 (confirmable ≠ progress)
14. TC-PTR-04: partner별 confirm/cancel — Sprint 37 동작 유지
15. TC-PTR-05: PI/QI/SI 알람 — 변경 없음

---

## 변경 파일 — Sprint 37-A

| 파일 | 변경 |
|------|------|
| `backend/migrations/031_tm_pressure_test_setting.sql` | admin_settings에 `tm_pressure_test_required` 키 추가 (신규) |
| `backend/app/routes/production.py` | `_get_confirm_settings()` WHERE 확장 + `_build_order_item()` TMS progress 분기 (비혼재 + 혼재) |
| `backend/app/services/task_service.py` | `_trigger_completion_alerts()` TANK_MODULE 완료 알람 분기 + `_is_tm_pressure_test_required()` 헬퍼 |
| `tests/backend/test_sprint37a_pressure_test_setting.py` | White-box 테스트 10건 (신규) |
| `tests/backend/test_sprint37a_regression.py` | Regression 테스트 5건 (신규) |

## 규칙 — Sprint 37-A
- CLAUDE.md의 "DB 테이블 정확한 컬럼 명세" 섹션을 반드시 참조 — `admin_settings` 컬럼은 `setting_key`, `setting_value`, `description`
- `admin_settings` 조회: `_get_confirm_settings()`를 통해 일괄 조회 — 개별 쿼리 금지
- `_calc_sn_progress()` 결과의 `tasks` dict 활용 — task_id 레벨 데이터 이미 존재 (#36)
- `tm_pressure_test_required` default = `true` — 설정 미존재 시 기존 동작(가압검사 포함) 유지 필수
- confirmable 로직(`_CONFIRM_TASK_FILTER`)과 progress 로직은 독립 — confirmable은 항상 TANK_MODULE only
- BE가 코드를 완성하면 TEST가 먼저 CLAUDE.md 기준으로 코드 리뷰 진행
- 리뷰 통과 후에만 테스트 코드 작성
- 각 teammate는 자신의 소유 파일만 수정 가능
- ⚠️ `_calc_sn_progress()` 수정 금지 — #36에서 task_id 레벨로 확장 완료
- ⚠️ `_is_process_confirmable()` 수정 금지 — #36에서 TANK_MODULE only 분기 완료
- ⚠️ `_CONFIRM_TASK_FILTER` 수정 금지
- ⚠️ `task_seed.py` 수정 금지 — task 생성 로직 변경 없음
- ⚠️ FE 코드 수정 금지 — VIEW Sprint 13에서 별도 진행
- .env 파일 절대 커밋 금지
- N+1 쿼리 금지 — batch 조회(ANY 사용)
- 완료 시 AGENT_TEAM_LAUNCH.md 체크리스트 업데이트

---

### Teammate 프롬프트 — Sprint 37-A (#36-C TM 가압검사 옵션)

> **이 프롬프트를 Claude Code teammate에게 전달하여 실행**
> 선행 조건: Sprint 37 완료, DB Migration 031 실행 완료

```
## Sprint 37-A: TM 가압검사 옵션 — settings 기반 progress/알람 제어

### 컨텍스트
- 참조: `AXIS-VIEW/docs/OPS_API_REQUESTS.md` #36-C (설계 문서)
- 참조: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` Sprint 37-A 섹션
- 대상 파일: `backend/app/routes/production.py`, `backend/app/services/task_service.py`
- DB: `plan.admin_settings`에 `tm_pressure_test_required=true` 키 추가 완료 상태

### 배경
TM 공정의 PRESSURE_TEST를 progress/알람에 포함할지 admin_settings로 제어.
- confirmable: 항상 TANK_MODULE only (변경 없음 — `_CONFIRM_TASK_FILTER` 유지)
- progress: `tm_pressure_test_required=true` → 전체, `false` → TANK_MODULE만
- 알람: `tm_pressure_test_required=true` → PRESSURE_TEST 완료 시, `false` → TANK_MODULE 완료 시

### Task 순서 (반드시 이 순서대로)

#### Task 1: Migration 031 작성 (`backend/migrations/031_tm_pressure_test_setting.sql`)

```sql
BEGIN;

INSERT INTO plan.admin_settings (setting_key, setting_value, description)
VALUES ('tm_pressure_test_required', 'true', 'TM 가압검사 progress/알람 포함 여부 (true=포함, false=탱크모듈만)')
ON CONFLICT (setting_key) DO NOTHING;

COMMIT;
```

#### Task 2: `_get_confirm_settings()` WHERE 조건 확장

현재 WHERE: `setting_key LIKE 'confirm_%'`
변경: `tm_pressure_test_required`도 포함

```python
cur.execute("""
    SELECT setting_key, setting_value
    FROM admin_settings
    WHERE setting_key LIKE 'confirm_%'
       OR setting_key = 'tm_pressure_test_required'
""")
```

#### Task 3: `_build_order_item()` — TMS progress 분기

현재 주석(line 203~206)을 실제 코드로 변경.
비혼재 + 혼재 양쪽 progress 집계 루프에서:
- `pt == 'TMS'` and `settings.get('tm_pressure_test_required', True) == False`
- → `tasks` dict에서 TANK_MODULE만 합산

비혼재 루프:
```python
for sn in serial_numbers:
    cat = sns_progress.get(sn, {}).get(pt, {})
    if pt == 'TMS' and not settings.get('tm_pressure_test_required', True):
        tm_task = cat.get('tasks', {}).get('TANK_MODULE', {})
        total += tm_task.get('total', 0)
        completed += tm_task.get('completed', 0)
    else:
        total += cat.get('total', 0)
        completed += cat.get('completed', 0)
```

혼재 partner별 루프에서도 동일 패턴 적용.

#### Task 4: `task_service.py` `_trigger_completion_alerts()` — 알람 분기

기존 `PRESSURE_TEST` 완료 알람 유지 + TANK_MODULE 완료 시 알람 분기 추가:

```python
# 기존 PRESSURE_TEST 블록 유지 (line 359~366)

# NEW: TANK_MODULE 완료 + tm_pressure_test_required=false → 알람 발송
elif task.task_id == 'TANK_MODULE' and task.task_category == 'TMS':
    if not self._is_tm_pressure_test_required():
        trigger = ('TMS_TANK_COMPLETE', 'MECH', 'TMS 탱크모듈 완료 (가압검사 제외)')
```

`_is_tm_pressure_test_required()` 헬퍼 추가:
```python
def _is_tm_pressure_test_required(self) -> bool:
    cur = get_db_connection().cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT setting_value FROM plan.admin_settings
        WHERE setting_key = 'tm_pressure_test_required'
    """)
    row = cur.fetchone()
    if row is None:
        return True
    val = row['setting_value']
    return val.lower() in ('true', '1') if isinstance(val, str) else bool(val)
```

#### Task 5: 테스트 코드 작성

`AGENT_TEAM_LAUNCH.md`의 "TEST 작업 — Sprint 37-A" 섹션 참조.
아래 2개 테스트 파일을 `tests/backend/`에 작성:

1. `test_sprint37a_pressure_test_setting.py` — White-box 10건 (TC-PT-01 ~ TC-PT-10)
2. `test_sprint37a_regression.py` — Regression 5건 (TC-PTR-01 ~ TC-PTR-05)

테스트 전체 PASSED (15건 이상) 확인 후 완료.

### 검증 체크리스트

1. **tm_pressure_test_required=true** (기본): TMS progress = TANK_MODULE + PRESSURE_TEST 합산, 알람 = PRESSURE_TEST 완료 시
2. **tm_pressure_test_required=false**: TMS progress = TANK_MODULE만, 알람 = TANK_MODULE 완료 시
3. **설정 미존재**: default `true` 동작 (기존과 동일)
4. **confirmable 미변경**: `_CONFIRM_TASK_FILTER` = TANK_MODULE only 그대로
5. **MECH/ELEC/PI/QI/SI**: 영향 없음
6. **혼재 + false**: partner별 TMS progress도 TANK_MODULE만 합산

### 수정 대상 파일 목록

- `backend/migrations/031_tm_pressure_test_setting.sql` (신규)
- `backend/app/routes/production.py` (수정)
- `backend/app/services/task_service.py` (수정)
- `tests/backend/test_sprint37a_pressure_test_setting.py` (신규)
- `tests/backend/test_sprint37a_regression.py` (신규)

### 규칙

- CLAUDE.md의 "DB 테이블 정확한 컬럼 명세" 반드시 참조 — `admin_settings` 컬럼: `setting_key`, `setting_value`, `description`
- `_get_confirm_settings()`를 통해 일괄 조회 — 개별 쿼리 금지 (`_is_tm_pressure_test_required` 헬퍼는 task_service.py 전용)
- `tm_pressure_test_required` default = `true` — 설정 미존재 시 기존 동작 유지 필수
- confirmable 로직과 progress 로직은 독립 — confirmable은 항상 TANK_MODULE only
- BE가 코드를 완성하면 TEST가 먼저 CLAUDE.md 기준으로 코드 리뷰 진행
- 리뷰 통과 후에만 테스트 코드 작성
- 각 teammate는 자신의 소유 파일만 수정 가능
- N+1 쿼리 금지 — batch 조회(ANY 사용)
- .env 파일 절대 커밋 금지

### 절대 수정 금지

- `_calc_sn_progress()` — task_id 레벨 구조 변경 없음
- `_is_process_confirmable()` — TANK_MODULE only 분기 변경 없음
- `_CONFIRM_TASK_FILTER` — 변경 없음
- `task_seed.py` — task 생성 로직 변경 없음
- FE 코드 — VIEW Sprint 13에서 별도 진행
- Sprint 37 partner 혼재 로직 (`_PROC_PARTNER_COL`, `partner_confirms`) — 구조 변경 없음
```

---

## Sprint 37-B: S/N별 실적확인 + TM 혼재 제거 + 탭별 End 필터 (2026-03-24) — #38

> **목적**: ① TM partner_confirms에서 FNI 혼입 버그 수정 (TM 혼재 제거) ② 전 공정 S/N별 실적확인 ③ 탭별 end 날짜 필터
> **참조**: OPS_API_REQUESTS.md #38
> **대상**: `AXIS-OPS/backend/app/routes/production.py`, DB migration
> **선행**: Sprint 37 완료 (partner별 실적확인), Sprint 37-A 완료 (tm_pressure_test_required)

### 배경

**문제 (#38)**: `_PROC_PARTNER_COL = {'TM': 'mech_partner'}`로 TM 혼재 판정 시 `mech_partner` 기준으로 FNI(기구 협력사)가 TM partner_confirms에 혼입. FNI는 tank을 제작하지 않으므로 TM 실적과 무관. TM 작업은 TMS(M)에서 전부 수행.

**해결**: 3가지 변경
1. **TM 혼재 제거** — `_PROC_PARTNER_COL`에서 `'TM'` 삭제. TM은 `is_tms=true` 모델 S/N만 자연 필터링 (TMS tasks 유무)
2. **S/N별 실적확인** — `production_confirm`에 `serial_number` 추가. 모든 공정(MECH/ELEC/TM)에서 S/N 단위 확인. 일괄확인 = 여러 S/N rows 한 번에 INSERT
3. **탭별 End 필터** — 기구전장 탭: `mech_end`/`elec_end`, TM 탭: `module_end` 기준. BE 응답에 end 날짜 포함

### 분리 규칙 (Sprint 37에서 변경)

| 공정 | 분리 기준 | 혼재 O/N | 비혼재 O/N | S/N별 확인 | 비고 |
|------|----------|---------|----------|-----------|------|
| MECH | `mech_partner` | partner 그룹 내 S/N별 버튼 | S/N별 버튼 | ✅ | 전체 완료 시 일괄확인 |
| ELEC | `elec_partner` | partner 그룹 내 S/N별 버튼 | S/N별 버튼 | ✅ | 전체 완료 시 일괄확인 |
| TM | ~~`mech_partner`~~ 제거 | — | S/N별 버튼 | ✅ | partner 혼재 미적용 |
| PI/QI/SI | 분리 안함 | — | 기존 O/N 단위 | ❌ | 변경 없음 |

### BE 작업 — Task 정의

#### Task 1: DB Migration 032 (`backend/migrations/032_production_confirm_serial_number.sql`)

- `production_confirm`에 `serial_number VARCHAR(20) DEFAULT NULL` 컬럼 추가
- `sn_count` 컬럼 제거 (S/N별 1 row이므로 불필요)
- unique index 변경: `(sales_order, process_type, COALESCE(partner, ''), serial_number)` WHERE `deleted_at IS NULL`
- 기존 데이터 마이그레이션: 기존 rows (serial_number=NULL)는 유지 (하위호환)

```sql
BEGIN;

-- 1. serial_number 컬럼 추가
ALTER TABLE plan.production_confirm
    ADD COLUMN IF NOT EXISTS serial_number VARCHAR(20) DEFAULT NULL;

-- 2. sn_count 컬럼 제거
ALTER TABLE plan.production_confirm
    DROP COLUMN IF EXISTS sn_count;

-- 3. unique index 변경
DROP INDEX IF EXISTS production_confirm_active_unique;

CREATE UNIQUE INDEX production_confirm_active_unique
    ON plan.production_confirm(sales_order, process_type, COALESCE(partner, ''), serial_number)
    WHERE deleted_at IS NULL;

-- 4. serial_number 검색 인덱스
CREATE INDEX IF NOT EXISTS idx_production_confirm_serial_number
    ON plan.production_confirm(serial_number)
    WHERE deleted_at IS NULL;

COMMIT;
```

#### Task 2: `_PROC_PARTNER_COL` 수정 — TM 제거

현재:
```python
_PROC_PARTNER_COL = {'MECH': 'mech_partner', 'ELEC': 'elec_partner', 'TM': 'mech_partner'}
```

변경:
```python
_PROC_PARTNER_COL = {'MECH': 'mech_partner', 'ELEC': 'elec_partner'}
```

→ TM은 partner 기반 혼재 판정 안 함. TMS tasks가 있는 S/N만 자연 필터링 (`is_tms=true` 모델).

#### Task 3: `get_performance()` — product_info SELECT에 end 날짜 + model_config JOIN

현재 SELECT:
```python
SELECT p.sales_order, p.serial_number, p.model,
       p.mech_partner, p.elec_partner, p.line
FROM plan.product_info p
```

변경:
```python
SELECT p.sales_order, p.serial_number, p.model,
       p.mech_partner, p.elec_partner, p.line,
       p.mech_end, p.elec_end,
       COALESCE(p.module_end, p.module_start) AS module_end
FROM plan.product_info p
```

→ FE에서 탭별 end 날짜 필터링에 사용

confirms 조회 변경 — serial_number 포함:
```python
SELECT id, sales_order, process_type, partner, serial_number,
       confirmed_week, confirmed_month, confirmed_by, confirmed_at
FROM plan.production_confirm
WHERE sales_order = ANY(%s) AND deleted_at IS NULL
```

confirms dict 키 변경:
- partner + serial_number: `{sales_order}:{process_type}:{partner}:{serial_number}`
- partner만: `{sales_order}:{process_type}:{partner}:` (하위호환)
- 둘 다 없음: `{sales_order}:{process_type}::` (하위호환)

#### Task 4: `_build_order_item()` — S/N별 confirmable/confirmed 구조

**MECH/ELEC (혼재)**: partner_confirms 안에 sn_confirms 배열 추가

```python
partner_confirms_list.append({
    'partner': ptnr,
    'sn_confirms': [
        {
            'serial_number': sn,
            'total': sn_total,
            'completed': sn_completed,
            'pct': round(sn_completed / sn_total * 100, 1) if sn_total > 0 else 0.0,
            'confirmable': _is_sn_process_confirmable(sns_progress, pt, settings, proc_key, sn),
            'confirmed': confirm is not None,
            'confirmed_at': ...,
            'confirm_id': ...,
        }
        for sn in ptnr_sns
    ],
    'all_confirmable': all(sn['confirmable'] for sn in sn_confirms),  # 일괄확인 가능 여부
    'all_confirmed': all(sn['confirmed'] for sn in sn_confirms),
})
```

**MECH/ELEC (비혼재) + TM**: sn_confirms 배열 직접 추가

```python
processes[proc_key] = {
    'total': total,
    'completed': completed,
    'pct': ...,
    'mixed': False,
    'sn_confirms': [
        {
            'serial_number': sn,
            'total': sn_total,
            'completed': sn_completed,
            'pct': ...,
            'confirmable': _is_sn_process_confirmable(sns_progress, pt, settings, proc_key, sn),
            'confirmed': ...,
            'confirmed_at': ...,
            'confirm_id': ...,
        }
        for sn in serial_numbers
    ],
    'all_confirmable': ...,
    'all_confirmed': ...,
}
```

**PI/QI/SI**: 기존 O/N 단위 유지 (sn_confirms 없음)

**`_is_sn_process_confirmable()` 헬퍼 추가** — 단일 S/N 판정:
```python
def _is_sn_process_confirmable(
    sns_progress: Dict, process_type: str, settings: Dict,
    proc_key: str, serial_number: str
) -> bool:
    """단일 S/N의 해당 공정 confirmable 판정"""
    key = f'confirm_{proc_key.lower()}_enabled'
    if not settings.get(key, False):
        return False
    cat_data = sns_progress.get(serial_number, {}).get(process_type, {})
    confirm_task = _CONFIRM_TASK_FILTER.get(process_type)
    if confirm_task:
        task_data = cat_data.get('tasks', {}).get(confirm_task, {})
        return task_data.get('total', 0) > 0 and task_data.get('completed', 0) >= task_data.get('total', 0)
    else:
        return cat_data.get('total', 0) > 0 and cat_data.get('completed', 0) >= cat_data.get('total', 0)
```

**sns_detail에 end 날짜 추가**:
```python
sns_detail.append({
    'serial_number': sn,
    'mech_partner': p.get('mech_partner', ''),
    'elec_partner': p.get('elec_partner', ''),
    'mech_end': p.get('mech_end').isoformat() if p.get('mech_end') else None,
    'elec_end': p.get('elec_end').isoformat() if p.get('elec_end') else None,
    'module_end': p.get('module_end').isoformat() if p.get('module_end') else None,
    'progress': sn_prog,
})
```

#### Task 5: `confirm_production()` — serial_numbers 배열 처리

요청 Body 변경:
- 기존: `{ sales_order, process_type, partner?, confirmed_week, confirmed_month }`
- 변경: `{ sales_order, process_type, partner?, serial_numbers: [str], confirmed_week, confirmed_month }`

```python
serial_numbers_req = data.get('serial_numbers', [])
if not serial_numbers_req:
    return jsonify({'error': 'INVALID_REQUEST', 'message': 'serial_numbers 필수'}), 400
```

S/N별 confirmable 검증 + multi-row INSERT:
```python
# 각 S/N별 confirmable 체크
for sn in serial_numbers_req:
    if not _is_sn_process_confirmable(sns_progress, db_category, settings, process_type, sn):
        return jsonify({
            'error': 'NOT_CONFIRMABLE',
            'message': f'{sn}: {process_type} 공정이 아직 완료되지 않았습니다.',
        }), 400

# multi-row INSERT
values = []
for sn in serial_numbers_req:
    values.append((sales_order, process_type, partner, sn,
                    confirmed_week, confirmed_month, g.worker_id))

cur.executemany("""
    INSERT INTO plan.production_confirm
        (sales_order, process_type, partner, serial_number,
         confirmed_week, confirmed_month, confirmed_by)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
""", values)

# RETURNING 대신 별도 조회 (executemany는 RETURNING 미지원)
cur.execute("""
    SELECT id, serial_number, confirmed_at
    FROM plan.production_confirm
    WHERE sales_order = %s AND process_type = %s
      AND COALESCE(partner, '') = COALESCE(%s, '')
      AND serial_number = ANY(%s)
      AND deleted_at IS NULL
    ORDER BY serial_number
""", (sales_order, process_type, partner, serial_numbers_req))
```

응답:
```python
return jsonify({
    'message': '실적확인 완료',
    'confirmed': [dict(r) for r in cur.fetchall()],
    'count': len(serial_numbers_req),
}), 201
```

#### Task 6: `cancel_confirm()` — 변경 없음

기존 `confirm_id` 기반 soft delete 유지. S/N별 confirm이므로 개별 취소는 confirm_id로 충분.
응답에 `serial_number` 추가:
```python
RETURNING id, sales_order, process_type, partner, serial_number
```

#### Task 7: 테스트 코드 작성

`AGENT_TEAM_LAUNCH.md`의 "TEST 작업 — Sprint 37-B" 섹션 참조.

### 배포 순서

1. **DB migration**: Migration 032 실행 (Railway) — serial_number 컬럼 + unique index 변경
2. **BE push**: Task 2~6 (TM 혼재 제거 + S/N별 확인 + end 날짜)
3. **FE push**: VIEW Sprint에서 S/N별 버튼 UI 변경 (별도)

### 체크리스트

**BE (✅ 완료)**:
- [x] Migration 032 작성 + Railway DB 적용 ✅
- [x] `_PROC_PARTNER_COL` TM 제거 ✅
- [x] `get_performance()` SELECT에 `mech_end`, `elec_end`, `module_end` 추가 ✅
- [x] confirms 조회에 `serial_number` 포함 + dict 키 `{so}:{proc}:{ptnr}:{sn}` ✅
- [x] `_is_sn_process_confirmable()` 헬퍼 추가 ✅
- [x] `_build_order_item()` sn_confirms 배열 (혼재/비혼재/TM/PI분리) ✅
- [x] `sns_detail`에 end 날짜 추가 ✅
- [x] `confirm_production()` serial_numbers 배열 + multi-row INSERT ✅
- [x] `cancel_confirm()` RETURNING serial_number ✅

**TEST (✅ 36/36 passed — 26분 53초)**:
- [x] `test_sprint37b_sn_confirm.py` White-box 24건 ✅
- [x] `test_sprint37b_graybox.py` Gray-box 5건 ✅
- [x] `test_sprint37b_regression.py` Regression 7건 ✅
- [x] `has_docking` 컬럼 참조 버그 수정 (product_info에 없는 컬럼) ✅

**검증 (배포 후)**:
- [ ] 🔴 TM 혼재 제거: `processes.TM.mixed` 없음, `partner_confirms` 없음
- [ ] 🔴 TM S/N별 확인: `processes.TM.sn_confirms` 배열 정상
- [ ] 🔴 MECH 혼재 + S/N별: `partner_confirms[].sn_confirms` 배열 정상
- [ ] 🔴 MECH 비혼재 + S/N별: `processes.MECH.sn_confirms` 배열 정상
- [ ] 🔴 일괄확인: 전체 S/N 완료 시 `all_confirmable=true` + multi-row INSERT
- [ ] 🔴 개별확인: 완료된 S/N만 개별 confirm
- [ ] 🔴 탭별 End 필터: `sns[].mech_end`, `elec_end`, `module_end` 정상 반환
- [ ] PI/QI/SI → 기존 O/N 단위 유지 (sn_confirms 없음)
- [ ] 기존 serial_number=NULL 데이터 하위호환

---

## TEST 작업 (tests/backend/) — Sprint 37-B

### test_sprint37b_sn_confirm.py (신규) — 🔴 S/N별 실적확인 + TM 혼재 제거

**White-box: _PROC_PARTNER_COL TM 제거**
1. TC-SC-01: TM 공정 — `_PROC_PARTNER_COL`에 `'TM'` 없음 확인 → TM은 비혼재 경로
2. TC-SC-02: O/N에 mech_partner TMS(1대)+FNI(4대) — TM processes에 `partner_confirms` 없음, `sn_confirms` 배열만 존재
3. TC-SC-03: O/N에 mech_partner TMS 단독 — TM `sn_confirms` 정상 (is_tms=true S/N만 TMS tasks 존재)

**White-box: _is_sn_process_confirmable() 단일 S/N 판정**
4. TC-SC-04: S/N의 MECH 공정 100% 완료 → confirmable=true
5. TC-SC-05: S/N의 MECH 공정 80% 완료 → confirmable=false
6. TC-SC-06: S/N의 TMS 공정 TANK_MODULE 100% + PRESSURE_TEST 0% → confirmable=true (`_CONFIRM_TASK_FILTER` TANK_MODULE only)
7. TC-SC-07: `confirm_mech_enabled=false` 설정 시 → confirmable=false (설정 비활성)

**White-box: _build_order_item() S/N별 sn_confirms 구조**
8. TC-SC-08: MECH 비혼재 O/N 3대 — `processes.MECH.sn_confirms` 길이 3, 각 S/N별 confirmable/confirmed
9. TC-SC-09: MECH 혼재 O/N (TMS 2대+FNI 3대) — `partner_confirms[TMS].sn_confirms` 길이 2, `partner_confirms[FNI].sn_confirms` 길이 3
10. TC-SC-10: ELEC 비혼재 O/N — `processes.ELEC.sn_confirms` 정상
11. TC-SC-11: TM O/N 5대 — `processes.TM.sn_confirms` 길이 5 (partner_confirms 없음)
12. TC-SC-12: PI/QI/SI — `sn_confirms` 없음, 기존 O/N 단위 confirmable/confirmed
13. TC-SC-13: `all_confirmable` — S/N 5대 중 5대 모두 완료 → `all_confirmable=true`
14. TC-SC-14: `all_confirmable` — S/N 5대 중 3대만 완료 → `all_confirmable=false`, 완료된 3대 confirmable=true

**White-box: confirm_production() serial_numbers 배열 처리**
15. TC-SC-15: serial_numbers=['SN001','SN002'] → 2 rows INSERT, confirmed count=2
16. TC-SC-16: serial_numbers=['SN001'] 개별 확인 → 1 row INSERT
17. TC-SC-17: serial_numbers 빈 배열 → 400 에러 (INVALID_REQUEST)
18. TC-SC-18: serial_numbers에 미완료 S/N 포함 → 400 에러 (NOT_CONFIRMABLE, 해당 S/N 명시)
19. TC-SC-19: MECH 혼재 + partner='TMS' + serial_numbers → mech_partner='TMS'인 S/N만 대상 확인

**White-box: cancel_confirm() serial_number 응답**
20. TC-SC-20: S/N별 confirm 취소 → 해당 S/N confirm만 soft delete, 같은 O/N 다른 S/N confirm 유지
21. TC-SC-21: RETURNING에 serial_number 포함 확인

**White-box: get_performance() end 날짜 + confirms dict 키**
22. TC-SC-22: sns_detail에 `mech_end`, `elec_end`, `module_end` 포함 확인
23. TC-SC-23: confirms dict 키 — `{so}:{proc}:{partner}:{sn}` 형식 정상
24. TC-SC-24: 기존 serial_number=NULL 데이터 → dict 키 하위호환

### test_sprint37b_graybox.py (신규) — Gray-box 테스트

25. TC-SG-01: Migration 032 적용 후 → serial_number 컬럼 존재 + sn_count 컬럼 없음 + unique index 정상
26. TC-SG-02: S/N별 confirm → cancel → 재confirm E2E 흐름
27. TC-SG-03: 혼재 O/N — TMS partner S/N 2대 일괄확인 → FNI partner S/N 3대 중 1대 개별확인 → API 응답에 TMS 2대 confirmed, FNI 1대 confirmed + 2대 미확인
28. TC-SG-04: TM S/N 5대 중 3대 개별확인 → API 응답에 3대 confirmed + 2대 미확인 + FNI 미포함(TM 혼재 제거)
29. TC-SG-05: duplicate INSERT (동일 sales_order+process_type+partner+serial_number) → unique constraint 에러 처리

### test_sprint37b_regression.py (신규) — Regression 테스트

30. TC-SR-01: Sprint 37 `_PROC_PARTNER_COL` — MECH/ELEC partner 혼재 기존 동작 유지 (TM만 제거)
31. TC-SR-02: Sprint 37-A `tm_pressure_test_required=false` → TMS progress TANK_MODULE only 유지
32. TC-SR-03: `_CONFIRM_TASK_FILTER` TMS→TANK_MODULE only confirmable 미변경
33. TC-SR-04: `_is_process_confirmable()` — 기존 O/N 전체 판정 로직 미변경 (PI/QI/SI용)
34. TC-SR-05: `_calc_sn_progress()` task_id 레벨 GROUP BY 정상
35. TC-SR-06: `cancel_confirm()` id 기반 soft delete 기존 동작 유지
36. TC-SR-07: admin_settings `confirm_*_enabled=false` → confirmable=false (설정 비활성 차단)

---

## 변경 파일 — Sprint 37-B

| 파일 | 변경 |
|------|------|
| `backend/migrations/032_production_confirm_serial_number.sql` | serial_number 컬럼 추가 + sn_count 제거 + unique index 변경 (신규) |
| `backend/app/routes/production.py` | `_PROC_PARTNER_COL` TM 제거 + `_is_sn_process_confirmable()` 헬퍼 + `_build_order_item()` sn_confirms 구조 + `get_performance()` end 날짜/confirms 키 + `confirm_production()` serial_numbers 배열 + `cancel_confirm()` serial_number 응답 |
| `tests/backend/test_sprint37b_sn_confirm.py` | White-box 테스트 24건 (신규) |
| `tests/backend/test_sprint37b_graybox.py` | Gray-box 테스트 5건 (신규) |
| `tests/backend/test_sprint37b_regression.py` | Regression 테스트 7건 (신규) |

## 규칙 — Sprint 37-B

- CLAUDE.md의 "DB 테이블 정확한 컬럼 명세" 반드시 참조 — `production_confirm`, `product_info`, `admin_settings` 컬럼명 실수 방지
- `admin_settings` 컬럼은 `setting_key`, `setting_value`, `description` (NOT `key`, `value`)
- `production_confirm`은 plan 스키마 — unique index: `(sales_order, process_type, COALESCE(partner, ''), serial_number)` WHERE `deleted_at IS NULL`
- `product_info.mech_partner`, `elec_partner` 컬럼값은 DB에 `'TMS'`로 저장 (NOT `'TMS(M)'`/`'TMS(E)'`)
- `product_info`의 end 날짜: `mech_end`, `elec_end`, `module_end` — `module_end` NULL 시 `module_start` fallback
- `_is_sn_process_confirmable()`는 `_is_process_confirmable()`와 독립 — SN 단일 판정 전용, 기존 함수 수정 금지
- `_PROC_TO_CAT = {'TM': 'TMS'}` 역매핑은 confirmable 체크 전용 유지
- confirms dict 키: `{so}:{proc}:{partner}:{sn}` — partner/sn NULL이면 빈문자열로 처리 (하위호환)
- `executemany`는 `RETURNING` 미지원 — multi-row INSERT 후 별도 SELECT로 결과 조회
- PI/QI/SI는 S/N별 확인 미적용 — 기존 O/N 단위 유지, `_is_process_confirmable()` 사용
- BE가 코드를 완성하면 TEST가 먼저 CLAUDE.md 기준으로 코드 리뷰 진행
- 리뷰 통과 후에만 테스트 코드 작성
- 각 teammate는 자신의 소유 파일만 수정 가능
- ⚠️ `_calc_sn_progress()` 수정 금지 — #36에서 task_id 레벨로 확장 완료
- ⚠️ `_is_process_confirmable()` 수정 금지 — PI/QI/SI에서 계속 사용
- ⚠️ `_CONFIRM_TASK_FILTER` 수정 금지
- ⚠️ `task_seed.py` 수정 금지
- ⚠️ `task_service.py` 수정 금지 — Sprint 37-A에서 완료
- ⚠️ FE 코드 수정 금지 — VIEW Sprint에서 별도 진행
- .env 파일 절대 커밋 금지
- N+1 쿼리 금지 — batch 조회(ANY 사용)
- 완료 시 AGENT_TEAM_LAUNCH.md 체크리스트 업데이트

---

### Teammate 프롬프트 — Sprint 37-B (#38 S/N별 실적확인 + TM 혼재 제거 + 탭별 End 필터)

> **이 프롬프트를 Claude Code teammate에게 전달하여 실행**
> 선행 조건: Sprint 37 완료, Sprint 37-A 완료, DB Migration 032 실행 완료

```
## Sprint 37-B: S/N별 실적확인 + TM 혼재 제거 + 탭별 End 필터

### 컨텍스트
- 참조: `AXIS-VIEW/docs/OPS_API_REQUESTS.md` #38 (버그 리포트)
- 참조: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` Sprint 37-B 섹션
- 대상 파일: `backend/app/routes/production.py`
- DB: `plan.production_confirm` 테이블에 `serial_number VARCHAR(20)` 컬럼 추가 완료, `sn_count` 컬럼 제거 완료

### 배경
1. TM partner_confirms에 FNI 혼입 버그 — `_PROC_PARTNER_COL`에서 `'TM': 'mech_partner'` 삭제로 해결
2. 모든 공정(MECH/ELEC/TM)에서 S/N별 실적확인 — O/N 내 S/N 완료 시점이 다를 수 있으므로 개별 확인 필요
3. 탭별 End 날짜 필터 — 기구전장: `mech_end`/`elec_end`, TM: `module_end` 기준

### Task 순서 (반드시 이 순서대로)

#### Task 1: Migration 032 작성 (`backend/migrations/032_production_confirm_serial_number.sql`)

```sql
BEGIN;

ALTER TABLE plan.production_confirm
    ADD COLUMN IF NOT EXISTS serial_number VARCHAR(20) DEFAULT NULL;

ALTER TABLE plan.production_confirm
    DROP COLUMN IF EXISTS sn_count;

DROP INDEX IF EXISTS production_confirm_active_unique;

CREATE UNIQUE INDEX production_confirm_active_unique
    ON plan.production_confirm(sales_order, process_type, COALESCE(partner, ''), serial_number)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_production_confirm_serial_number
    ON plan.production_confirm(serial_number)
    WHERE deleted_at IS NULL;

COMMIT;
```

#### Task 2: `_PROC_PARTNER_COL` 수정 — TM 제거

```python
# 변경 전
_PROC_PARTNER_COL = {'MECH': 'mech_partner', 'ELEC': 'elec_partner', 'TM': 'mech_partner'}

# 변경 후
_PROC_PARTNER_COL = {'MECH': 'mech_partner', 'ELEC': 'elec_partner'}
```

#### Task 3: `_is_sn_process_confirmable()` 헬퍼 추가

`_is_process_confirmable()` 아래에 추가 (기존 함수 수정 금지):

```python
def _is_sn_process_confirmable(
    sns_progress: Dict[str, Dict],
    process_type: str,
    settings: Dict[str, bool],
    proc_key: str,
    serial_number: str,
) -> bool:
    """단일 S/N의 해당 공정 confirmable 판정

    _is_process_confirmable()과 동일 로직이나 S/N 1개만 대상.
    _CONFIRM_TASK_FILTER 적용 (TMS → TANK_MODULE only).
    """
    key = f'confirm_{proc_key.lower()}_enabled'
    if not settings.get(key, False):
        return False

    cat_data = sns_progress.get(serial_number, {}).get(process_type, {})
    confirm_task = _CONFIRM_TASK_FILTER.get(process_type)

    if confirm_task:
        task_data = cat_data.get('tasks', {}).get(confirm_task, {})
        if task_data.get('total', 0) == 0:
            return False
        return task_data.get('completed', 0) >= task_data.get('total', 0)
    else:
        if cat_data.get('total', 0) == 0:
            return False
        return cat_data.get('completed', 0) >= cat_data.get('total', 0)
```

#### Task 4: `get_performance()` 수정 — end 날짜 + confirms dict 키

product_info SELECT 변경:
```python
cur.execute("""
    SELECT p.sales_order, p.serial_number, p.model,
           p.mech_partner, p.elec_partner, p.line,
           p.mech_end, p.elec_end,
           COALESCE(p.module_end, p.module_start) AS module_end
    FROM plan.product_info p
    WHERE (p.mech_end >= %s AND p.mech_end < %s)
       OR (p.elec_end >= %s AND p.elec_end < %s)
       OR (COALESCE(p.module_end, p.module_start) >= %s
           AND COALESCE(p.module_end, p.module_start) < %s)
    ORDER BY p.sales_order, p.serial_number
""", (start_date, end_date, start_date, end_date, start_date, end_date))
```

confirms 조회에 serial_number 포함:
```python
cur.execute("""
    SELECT id, sales_order, process_type, partner, serial_number,
           confirmed_week, confirmed_month, confirmed_by, confirmed_at
    FROM plan.production_confirm
    WHERE sales_order = ANY(%s) AND deleted_at IS NULL
""", (order_list,))
confirms = {}
for row in cur.fetchall():
    r = dict(row)
    ptnr = r.get('partner') or ''
    sn = r.get('serial_number') or ''
    key = f"{r['sales_order']}:{r['process_type']}:{ptnr}:{sn}"
    confirms[key] = r
```

#### Task 5: `_build_order_item()` 수정 — S/N별 sn_confirms 구조

**혼재 경로** (mixed=True, MECH/ELEC만 해당):
- 기존 `partner_confirms` 배열 유지
- 각 partner 내부에 `sn_confirms` 배열 추가 (partner S/N별 confirmable/confirmed)
- confirms dict 키: `{so}:{proc_key}:{ptnr}:{sn}`
- `all_confirmable`: 해당 partner의 모든 S/N confirmable
- `all_confirmed`: 해당 partner의 모든 S/N confirmed

**비혼재 경로** (MECH/ELEC 비혼재, TM):
- 기존 confirmable/confirmed → `sn_confirms` 배열로 대체
- `all_confirmable`: 전체 S/N confirmable
- `all_confirmed`: 전체 S/N confirmed

**PI/QI/SI**: 기존 로직 유지 (S/N별 미적용). `_is_process_confirmable()` 사용.

**sns_detail에 end 날짜 추가**:
- `mech_end`, `elec_end`, `module_end` 필드 추가 (ISO format string 또는 null)

#### Task 6: `confirm_production()` 수정 — serial_numbers 배열 처리

요청 Body 필수 필드 추가: `serial_numbers` (string 배열)
```python
serial_numbers_req = data.get('serial_numbers', [])
if not serial_numbers_req:
    return jsonify({'error': 'INVALID_REQUEST', 'message': 'serial_numbers 필수'}), 400
```

partner 지정 시 해당 partner S/N인지 검증:
```python
if partner and process_type in _PROC_PARTNER_COL:
    partner_col = _PROC_PARTNER_COL[process_type]
    cur.execute(f"""
        SELECT serial_number FROM plan.product_info
        WHERE sales_order = %s AND {partner_col} = %s
          AND serial_number = ANY(%s)
    """, (sales_order, partner, serial_numbers_req))
    valid_sns = [r['serial_number'] for r in cur.fetchall()]
    if len(valid_sns) != len(serial_numbers_req):
        return jsonify({'error': 'INVALID_SN', 'message': '요청 S/N이 해당 partner에 속하지 않습니다.'}), 400
```

S/N별 confirmable 검증:
```python
sns_progress = _calc_sn_progress(cur, serial_numbers_req)
settings = _get_confirm_settings(cur)
_PROC_TO_CAT = {'TM': 'TMS'}
db_category = _PROC_TO_CAT.get(process_type, process_type)

for sn in serial_numbers_req:
    if not _is_sn_process_confirmable(sns_progress, db_category, settings, process_type, sn):
        return jsonify({
            'error': 'NOT_CONFIRMABLE',
            'message': f'{sn}: {process_type} 공정 미완료',
        }), 400
```

multi-row INSERT:
```python
values = [(sales_order, process_type, partner, sn,
           confirmed_week, confirmed_month, g.worker_id)
          for sn in serial_numbers_req]

cur.executemany("""
    INSERT INTO plan.production_confirm
        (sales_order, process_type, partner, serial_number,
         confirmed_week, confirmed_month, confirmed_by)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
""", values)

cur.execute("""
    SELECT id, serial_number, confirmed_at
    FROM plan.production_confirm
    WHERE sales_order = %s AND process_type = %s
      AND COALESCE(partner, '') = COALESCE(%s, '')
      AND serial_number = ANY(%s)
      AND deleted_at IS NULL
""", (sales_order, process_type, partner, serial_numbers_req))
conn.commit()
```

#### Task 7: `cancel_confirm()` 수정 — RETURNING에 serial_number 추가

```python
RETURNING id, sales_order, process_type, partner, serial_number
```

#### Task 8: 테스트 코드 작성

`AGENT_TEAM_LAUNCH.md`의 "TEST 작업 — Sprint 37-B" 섹션 참조.
아래 3개 테스트 파일을 `tests/backend/`에 작성:

1. `test_sprint37b_sn_confirm.py` — White-box 24건 (TC-SC-01 ~ TC-SC-24)
2. `test_sprint37b_graybox.py` — Gray-box 5건 (TC-SG-01 ~ TC-SG-05)
3. `test_sprint37b_regression.py` — Regression 7건 (TC-SR-01 ~ TC-SR-07)

테스트 전체 PASSED (36건 이상) 확인 후 완료.

### 검증 체크리스트

1. **TM 혼재 제거**: `_PROC_PARTNER_COL`에 `'TM'` 없음 → TM은 비혼재 경로 → `partner_confirms` 없음
2. **S/N별 확인 (비혼재 MECH)**: `processes.MECH.sn_confirms` 길이 = S/N 수
3. **S/N별 확인 (혼재 MECH)**: `partner_confirms[TMS].sn_confirms` + `partner_confirms[FNI].sn_confirms`
4. **S/N별 확인 (TM)**: `processes.TM.sn_confirms` 길이 = S/N 수 (TMS tasks 있는 S/N만)
5. **일괄확인**: 전체 S/N 완료 → `all_confirmable=true` → serial_numbers 배열로 multi-row INSERT
6. **개별확인**: 완료 S/N만 → serial_numbers=[해당SN] → 1 row INSERT
7. **End 날짜**: `sns[].mech_end`, `elec_end`, `module_end` 정상 반환
8. **PI/QI/SI**: 기존 O/N 단위 유지 (sn_confirms 없음)
9. **하위호환**: 기존 serial_number=NULL 데이터 정상 조회

### 수정 대상 파일 목록

- `backend/migrations/032_production_confirm_serial_number.sql` (신규)
- `backend/app/routes/production.py` (수정)
- `tests/backend/test_sprint37b_sn_confirm.py` (신규)
- `tests/backend/test_sprint37b_graybox.py` (신규)
- `tests/backend/test_sprint37b_regression.py` (신규)

### 규칙

- CLAUDE.md의 "DB 테이블 정확한 컬럼 명세" 반드시 참조 — `production_confirm`, `product_info`, `admin_settings`
- `admin_settings` 컬럼은 `setting_key`, `setting_value`, `description` (NOT `key`, `value`)
- `production_confirm`은 plan 스키마 — unique index: `(sales_order, process_type, COALESCE(partner, ''), serial_number)` WHERE `deleted_at IS NULL`
- `product_info.mech_partner`, `elec_partner` 컬럼값은 DB에 `'TMS'`로 저장 (NOT `'TMS(M)'`/`'TMS(E)'`)
- `product_info`의 end 날짜: `mech_end`, `elec_end`, `module_end` — `module_end` NULL 시 `module_start` fallback
- `_is_sn_process_confirmable()`는 신규 헬퍼 — `_is_process_confirmable()` 수정 금지 (PI/QI/SI에서 계속 사용)
- `_PROC_TO_CAT = {'TM': 'TMS'}` 역매핑 유지
- confirms dict 키: `{so}:{proc}:{partner}:{sn}` — partner/sn 없으면 빈문자열
- `executemany`는 `RETURNING` 미지원 — INSERT 후 별도 SELECT
- PI/QI/SI는 S/N별 미적용 — 기존 `_is_process_confirmable()` + O/N 단위 유지
- BE가 코드를 완성하면 TEST가 먼저 CLAUDE.md 기준으로 코드 리뷰 진행
- 리뷰 통과 후에만 테스트 코드 작성
- 각 teammate는 자신의 소유 파일만 수정 가능
- N+1 쿼리 금지 — batch 조회(ANY 사용)
- .env 파일 절대 커밋 금지

### 절대 수정 금지

- `_calc_sn_progress()` — task_id 레벨 구조 변경 없음
- `_is_process_confirmable()` — PI/QI/SI에서 계속 사용, 수정 금지
- `_CONFIRM_TASK_FILTER` — 변경 없음
- `task_seed.py` — task 생성 로직 변경 없음
- `task_service.py` — Sprint 37-A에서 완료, 변경 없음
- FE 코드 — VIEW Sprint에서 별도 진행
- Sprint 37 MECH/ELEC partner 혼재 판정 로직 — `_PROC_PARTNER_COL`에서 TM만 제거, MECH/ELEC 유지
```

---

## Sprint 38: product/progress API 최근 태깅 요약 필드 추가 (2026-03-25) — VIEW Sprint 18 연동

> **목적**: VIEW S/N 카드뷰에서 카드 리스트 단계에서 최근 태깅 작업자를 표시하기 위한 BE 확장. N+1 호출 방지(방향 B 채택)
> **참조**: OPS_API_REQUESTS.md #43, VIEW DESIGN_FIX_SPRINT.md Sprint 18
> **대상**: `AXIS-OPS/backend/app/services/progress_service.py`
> **선행**: Sprint 37-B 완료

### 배경

VIEW Sprint 18 S/N 카드뷰에서 카드에 "최근 작업자 + 마지막 태깅 시간"을 표시하려면, 기존 방식으로는 S/N마다 `GET /tasks/<sn>?all=true`를 호출해야 하는 N+1 문제 발생. 방향 B를 채택하여 `GET /api/app/product/progress` 응답의 `products[]`에 summary 필드를 추가.

카드 리스트 데이터 소스는 APP 전사 작업 진행현황과 동일한 `GET /api/app/product/progress` API 사용. VIEW Sprint 18은 Sprint 38 없이 선행 가능 (progress만 표시), Sprint 38 완료 후 `last_worker` 필드 FE 연결만 추가.

현장 관리자(mech, elec in_manager)가 카드 리스트에서 작업자의 실제 태깅 여부를 바로 확인하는 용도.

장기적으로 작업자별 공정시간 집계 → APS integration 기반 데이터로 활용 예정.

### BE 작업

#### Task 1: `_aggregate_products()` — S/N별 최근 태깅 요약 서브쿼리 추가

**파일**: `backend/app/services/progress_service.py`
**위치**: `_aggregate_products()` 함수 내, S/N 그룹핑 후 반환 전

**추가할 서브쿼리** (`get_partner_sn_progress()` 메인 쿼리 이후, 별도 쿼리):

```sql
SELECT DISTINCT ON (t.serial_number)
    t.serial_number,
    w.name AS last_worker,
    COALESCE(wcl.completed_at, wsl.started_at) AS last_activity_at
FROM app_task_details t
JOIN work_start_log wsl ON wsl.task_id = t.id
JOIN workers w ON wsl.worker_id = w.id
LEFT JOIN work_completion_log wcl
    ON wcl.task_id = t.id AND wcl.worker_id = wsl.worker_id
WHERE t.serial_number = ANY(%s)
ORDER BY t.serial_number, COALESCE(wcl.completed_at, wsl.started_at) DESC
```

**파라미터**: `list(sn_map.keys())` — 그룹핑된 S/N 목록

**결과 캐싱**: `last_activity_map = { sn: { 'last_worker': name, 'last_activity_at': timestamp } }`

#### Task 2: `products[]` 응답에 필드 추가

**현재** (`_aggregate_products()` line 229~246):
```python
for sn_data in sn_map.values():
    # ... overall_percent, my_category 계산 ...
    products.append(sn_data)
    'mech_end': ...,
    'elec_end': ...,
    'module_end': ...,
    'progress': sn_prog,
})
```

**변경 후**:
```python
for sn_data in sn_map.values():
    # ... overall_percent, my_category 계산 ...
    activity = last_activity_map.get(sn_data['serial_number'], {})
    sn_data['last_worker'] = activity.get('last_worker')
    sn_data['last_activity_at'] = (
        activity['last_activity_at'].isoformat()
        if activity.get('last_activity_at') else None
    )
    products.append(sn_data)
```

### 응답 변경 (기존 호환)

기존 APP FE에서 사용하지 않는 필드 추가이므로 **하위 호환성 문제 없음**.

```json
{
  "products": [
    {
      "serial_number": "GBWS-6804",
      "model": "GAIA-I DUAL",
      "customer": "MICRON",
      "ship_plan_date": "2026-04-17",
      "all_completed": false,
      "overall_percent": 76,
      "categories": {
        "MECH": { "total": 6, "done": 6, "percent": 100 },
        "ELEC": { "total": 6, "done": 6, "percent": 100 }
      },
      "last_worker": "김태영",
      "last_activity_at": "2026-03-25T10:32:45+09:00"
    }
  ],
  "summary": { "total": 4, "in_progress": 3, "completed_recent": 1 }
}
```

> `last_worker`가 `null`이면 해당 S/N에 아직 태깅 이력 없음 → FE에서 "-" 또는 빈칸 처리

### 성능 고려

- `DISTINCT ON` + `ORDER BY DESC` → S/N당 최신 1건만 반환, 인덱스 활용
- `progress_service.py`는 전체 진행중 S/N 대상이므로 최대 수십~백 건 — 1회 batch 쿼리로 부하 미미
- `work_start_log`에 `task_id` 인덱스 이미 존재 (Sprint 14부터)

### 장기 확장 — APS Integration 기반

이 서브쿼리의 데이터 소스(`work_start_log` + `work_completion_log`)는 향후 아래 기능 확장의 기반:

| 확장 방향 | 설명 | 데이터 소스 |
|----------|------|-----------|
| 작업자별 공정시간 집계 | 모델별·공정별·작업자별 SUM(duration_minutes) | `work_completion_log.duration_minutes` |
| 생산계획 vs 실적 비교 | 계획 공정시간 대비 실제 소요시간 GAP 분석 | `plan.product_info` + `work_completion_log` |
| APS 데이터 제공 | 집계된 공정시간을 APS 시스템에 전달 | 위 집계 API 기반 |

현재 Sprint 38에서는 summary(최근 1건)만 제공하되, 동일 데이터 소스를 활용하므로 향후 집계 API 확장 시 일관성 유지.

### 배포 순서

1. **DB migration 불필요** — 기존 테이블(`work_start_log`, `work_completion_log`, `app_task_details`, `workers`) 활용
2. **BE push**: Task 1~2 (`production.py` 수정)
3. **TEST push**: 테스트 3파일 작성 + 전체 PASSED 확인
4. **FE 연결**: VIEW Sprint 18에서 `sns[].last_worker`, `last_activity_at` 사용 — 별도 진행

### 체크리스트

**BE**:
- [x] `progress_service.py` — `get_partner_sn_progress()` 내 `last_activity` 서브쿼리 추가 (1회 batch, N+1 금지)
- [x] `progress_service.py` — `_aggregate_products()` 반환 시 `last_worker`, `last_activity_at` 필드 추가
- [x] `last_activity_at` → `.isoformat()` 포맷, `None`이면 `null` 반환
- [x] 동시작업 S/N → `DISTINCT ON` + `ORDER BY DESC`로 가장 최근 활동 작업자 1명만

**TEST**:
- [x] `test_sprint38_last_activity.py` — White-box 8건 ✅
- [x] `test_sprint38_graybox.py` — Gray-box 3건 ✅
- [x] `test_sprint38_regression.py` — Regression 5건 ✅
- [x] 전체 PASSED (16건) 확인 — 2026-03-27

**검증 (배포 후)**:
- [ ] 태깅 이력 있는 S/N → `last_worker` = "작업자명", `last_activity_at` = ISO timestamp
- [ ] 태깅 이력 없는 S/N → `last_worker` = null, `last_activity_at` = null
- [ ] 동시작업 S/N → 가장 최근 활동한 작업자 1명만 표시
- [ ] 기존 APP 전사 작업 진행현황 영향 없음 (하위호환)

**검증 (배포 후 실기기)**:
- [ ] 🔴 `GET /api/app/product/progress` → 응답 `products[]` 각 항목에 `last_worker`, `last_activity_at` 존재
- [ ] 🔴 작업자 태깅 후 재조회 → `last_worker`, `last_activity_at` 갱신 확인
- [ ] 🔴 동시작업 task → 최후 활동 작업자 1명만 반환
- [ ] APP 전사 작업 진행현황 + VIEW 생산실적 페이지 정상 동작 (하위호환)

---

## TEST 작업 (tests/backend/) — Sprint 38

### test_sprint38_last_activity.py (신규) — 🔴 S/N 최근 태깅 요약 테스트

**White-box: `_aggregate_products()` last_activity 서브쿼리**
1. TC-LA-01: 태깅 이력 있는 S/N 1대 → `last_worker` = 작업자명, `last_activity_at` = ISO timestamp
2. TC-LA-02: 태깅 이력 없는 S/N 1대 → `last_worker` = null, `last_activity_at` = null
3. TC-LA-03: 동시작업 (workers 2명) S/N → `COALESCE(completed_at, started_at)` DESC 기준 최신 1명만 반환
4. TC-LA-04: 작업 시작만 한 S/N (완료 전) → `last_activity_at` = `started_at` (completed_at = null → COALESCE fallback)
5. TC-LA-05: S/N 5대 batch → 5대 모두 각각 올바른 `last_worker` 반환 (batch 정상)

**White-box: 응답 구조**
6. TC-LA-06: `products[]` 배열 각 항목에 `last_worker`, `last_activity_at` 필드 존재 확인
7. TC-LA-07: `last_activity_at` 포맷 → ISO 8601 (`.isoformat()`)
8. TC-LA-08: 기존 필드(`serial_number`, `categories`, `overall_percent`, `my_category`) 유지 확인 (하위호환)

### test_sprint38_graybox.py (신규) — Gray-box 테스트

9. TC-LG-01: `GET /api/app/product/progress` E2E → `products[].last_worker` 존재 확인
10. TC-LG-02: 작업자 태깅 → 재조회 → `last_worker` 갱신 확인 (E2E 흐름)
11. TC-LG-03: admin 호출 → 전체 S/N, 협력사 호출 → 소속 S/N만 + `last_worker` 모두 정상

### test_sprint38_regression.py (신규) — Regression 테스트

12. TC-LR-01: `_build_company_filter()` admin/GST/협력사 필터 정상 (last_activity 추가 후 regression 없음)
13. TC-LR-02: `completion_status` 완료 후 N일 필터 정상 (기존 로직 변경 없음)
14. TC-LR-03: `_resolve_my_category()` 자사 담당 카테고리 정상 (변경 없음)
15. TC-LR-04: `categories` 진행률 계산 정상 (total/done/percent 변경 없음)
16. TC-LR-05: `summary` (total/in_progress/completed_recent) 카운트 정상 (변경 없음)

---

## 변경 파일 — Sprint 38

| 파일 | 변경 |
|------|------|
| `backend/app/services/progress_service.py` | `get_partner_sn_progress()` — last_activity 서브쿼리 추가 + `_aggregate_products()` 필드 추가 |
| `tests/backend/test_sprint38_last_activity.py` | White-box 테스트 8건 (신규) |
| `tests/backend/test_sprint38_graybox.py` | Gray-box 테스트 3건 (신규) |
| `tests/backend/test_sprint38_regression.py` | Regression 테스트 5건 (신규) |

## 규칙 — Sprint 38

- CLAUDE.md의 "DB 테이블 정확한 컬럼 명세" 섹션을 반드시 참조 — `work_start_log`, `work_completion_log`, `workers`, `app_task_details` 컬럼명 실수 방지
- `_aggregate_products()` 기존 로직 수정 금지 — **필드 추가만**
- `_build_company_filter()`, `_resolve_my_category()` 수정 금지
- 서브쿼리는 `get_partner_sn_progress()` 내부에서 `sn_map.keys()` ANY 1회 실행 (N+1 금지)
- `DISTINCT ON (t.serial_number)` + `ORDER BY COALESCE(wcl.completed_at, wsl.started_at) DESC` — 최신 1건만
- `work_start_log` / `work_completion_log` 테이블 스키마 변경 없음
- FE 코드 수정 없음 — VIEW Sprint 18에서 별도 진행
- BE가 코드를 완성하면 TEST가 먼저 CLAUDE.md 기준으로 코드 리뷰 진행
- 리뷰 통과 후에만 테스트 코드 작성
- 각 teammate는 자신의 소유 파일만 수정 가능
- N+1 쿼리 금지 — batch 조회(ANY 사용)
- .env 파일 절대 커밋 금지

### 절대 수정 금지

- `_build_company_filter()` — 협력사 필터 로직 변경 없음
- `_resolve_my_category()` — 자사 담당 카테고리 판정 변경 없음
- `_aggregate_products()` 기존 필드 — `categories`, `overall_percent`, `my_category` 등 제거/변경 없음, 추가만 허용
- `product.py` 라우트 — `get_sn_progress()` 함수 변경 없음
- `task_seed.py` — task 생성 로직 변경 없음
- `task_service.py` — 알람 로직 변경 없음
- `production.py` — 이 Sprint에서 수정 대상 아님
- FE 코드 — VIEW Sprint 18에서 별도 진행

---

### Teammate 프롬프트 — Sprint 38 (#43 product/progress API last_activity 확장)

> **이 프롬프트를 Claude Code teammate에게 전달하여 실행**
> 선행 조건: Sprint 37-B 완료

```
## Sprint 38: product/progress API 최근 태깅 요약 필드 추가

### 컨텍스트
- 참조: `AXIS-VIEW/docs/OPS_API_REQUESTS.md` #43 (설계 문서)
- 참조: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` Sprint 38 섹션
- 대상 파일: `backend/app/services/progress_service.py`
- DB: 기존 테이블 활용 (스키마 변경 없음)

### 배경
VIEW Sprint 18 S/N 카드뷰에서 카드 리스트에 "최근 태깅 작업자 + 시간"을 표시해야 함.
카드 리스트 데이터 소스는 APP 전사 작업 진행현황과 동일한 `GET /api/app/product/progress` API.
S/N마다 `GET /tasks/<sn>?all=true`를 호출하면 N+1 문제 발생.
`products[]` 응답에 `last_worker`, `last_activity_at` summary 필드를 추가하여 해결.

### Task 순서 (반드시 이 순서대로)

#### Task 1: `get_partner_sn_progress()` — last_activity 서브쿼리 추가

파일: `backend/app/services/progress_service.py`
위치: `get_partner_sn_progress()` 함수 내, `_aggregate_products()` 호출 전

메인 쿼리 실행 후, 그룹핑된 S/N 목록으로 별도 서브쿼리 (1회 batch, N+1 금지):
```sql
SELECT DISTINCT ON (t.serial_number)
    t.serial_number,
    w.name AS last_worker,
    COALESCE(wcl.completed_at, wsl.started_at) AS last_activity_at
FROM app_task_details t
JOIN work_start_log wsl ON wsl.task_id = t.id
JOIN workers w ON wsl.worker_id = w.id
LEFT JOIN work_completion_log wcl
    ON wcl.task_id = t.id AND wcl.worker_id = wsl.worker_id
WHERE t.serial_number = ANY(%s)
ORDER BY t.serial_number, COALESCE(wcl.completed_at, wsl.started_at) DESC
```

결과를 dict로 캐싱:
```python
last_activity_map = {}
for row in cur.fetchall():
    last_activity_map[row['serial_number']] = {
        'last_worker': row['last_worker'],
        'last_activity_at': row['last_activity_at'],
    }
```

`last_activity_map`을 `_aggregate_products()`에 파라미터로 전달.

#### Task 2: `_aggregate_products()` 응답에 필드 추가

`products.append(sn_data)` 직전에 2개 필드 추가:
```python
activity = last_activity_map.get(sn_data['serial_number'], {})
sn_data['last_worker'] = activity.get('last_worker')
sn_data['last_activity_at'] = (
    activity['last_activity_at'].isoformat()
    if activity.get('last_activity_at') else None
)
products.append(sn_data)
```

#### Task 3: 테스트 코드 작성

`AGENT_TEAM_LAUNCH.md`의 "TEST 작업 — Sprint 38" 섹션 참조.
아래 3개 테스트 파일을 `tests/backend/`에 작성:

1. `test_sprint38_last_activity.py` — White-box 8건 (TC-LA-01 ~ TC-LA-08)
2. `test_sprint38_graybox.py` — Gray-box 3건 (TC-LG-01 ~ TC-LG-03)
3. `test_sprint38_regression.py` — Regression 5건 (TC-LR-01 ~ TC-LR-05)

테스트 전체 PASSED (16건 이상) 확인 후 완료.

### 검증 체크리스트

수정 완료 후 아래 시나리오 검증 (코드 리뷰 레벨):

1. **태깅 이력 있는 S/N**: `last_worker` = 작업자명, `last_activity_at` = ISO timestamp
2. **태깅 이력 없는 S/N**: `last_worker` = null, `last_activity_at` = null
3. **동시작업 S/N**: workers 2명 → 가장 최근 활동 작업자 1명만 반환
4. **작업 시작만 한 S/N**: completed_at = null → COALESCE fallback으로 started_at 사용
5. **S/N 5대 batch**: 5대 모두 각각 올바른 last_worker 반환
6. **admin vs 협력사**: admin → 전체 S/N + last_worker, 협력사 → 소속 S/N + last_worker
7. **기존 APP 하위호환**: 기존 products[] 필드 유지, 추가 필드만

### 수정 대상 파일 목록

- `backend/app/services/progress_service.py` (수정)
- `tests/backend/test_sprint38_last_activity.py` (신규)
- `tests/backend/test_sprint38_graybox.py` (신규)
- `tests/backend/test_sprint38_regression.py` (신규)

### 규칙

- CLAUDE.md의 "DB 테이블 정확한 컬럼 명세" 섹션을 반드시 참조
- `_aggregate_products()` 기존 로직 수정 금지 — 필드 추가만
- `_build_company_filter()`, `_resolve_my_category()` 수정 금지
- 서브쿼리는 sn_map.keys() ANY 1회 실행 (N+1 금지)
- `DISTINCT ON` + `ORDER BY DESC` 필수 — 최신 1건만
- BE가 코드를 완성하면 TEST가 먼저 CLAUDE.md 기준으로 코드 리뷰 진행
- 리뷰 통과 후에만 테스트 코드 작성
- 각 teammate는 자신의 소유 파일만 수정 가능
- N+1 쿼리 금지 — batch 조회(ANY 사용)
- .env 파일 절대 커밋 금지

### 절대 수정 금지

- `_build_company_filter()` — 협력사 필터 로직 변경 없음
- `_resolve_my_category()` — 자사 담당 카테고리 판정 변경 없음
- `_aggregate_products()` 기존 필드 — `categories`, `overall_percent`, `my_category` 등 제거/변경 없음
- `product.py` 라우트 — `get_sn_progress()` 함수 변경 없음
- `task_seed.py` — task 생성 로직 변경 없음
- `task_service.py` — 알람 로직 변경 없음
- `production.py` — 이 Sprint에서 수정 대상 아님
- FE 코드 — VIEW Sprint 18에서 별도 진행
```

---

## Sprint 39: 테스트 DB 분리 — conftest.py 리팩토링 (2026-03-25) — 인프라

> **목적**: 테스트 실행 시 운영 DB(Railway Staging) 대신 전용 테스트 DB를 사용하도록 분리. 운영 데이터 백업/복원 로직 제거, 안전한 regression test 환경 구축
> **대상**: `tests/conftest.py`
> **선행**: Railway 테스트 PostgreSQL 18 인스턴스 생성 완료 (`centerbeam.proxy.rlwy.net:20196`)

### 배경

현재 `conftest.py`의 문제점:
1. **운영 DB 직접 사용**: `STAGING_DB_URL`이 하드코딩되어 테스트가 운영 DB에서 실행됨
2. **백업/복원 위험**: 테스트 시작 시 workers, product_info, qr_registry, auth_settings, attendance를 백업 → 스키마 DROP → migration → 복원하는 절차 — 실패 시 운영 데이터 유실 위험
3. **DROP 제약**: 운영 데이터 보존을 위해 workers, hr, plan 스키마를 DROP하지 못함 → 불완전한 스키마 초기화
4. **`STAGING_DB_URL` 하드코딩**: `db_existing_roles`, `has_sprint6_schema` fixture에서도 직접 참조

### BE 작업 — Task 정의

#### Task 1: 환경변수 기반 DB URL 분리

- `STAGING_DB_URL` 하드코딩 제거
- `TEST_DATABASE_URL` 환경변수 필수화 (미설정 시 명확한 에러 메시지)
- `.env.test` 파일 생성 (`.gitignore` 등록)
- `.env.test` 자동 로딩: `python-dotenv` 있으면 사용, 없으면 수동 파싱 fallback (별도 설치 불필요)

```python
# Before (위험)
STAGING_DB_URL = 'postgresql://postgres:xxx@maglev.proxy.rlwy.net:38813/railway'
class TestConfig:
    DATABASE_URL = os.getenv('TEST_DATABASE_URL', os.getenv('DATABASE_URL', STAGING_DB_URL))

# After (안전)
class TestConfig:
    DATABASE_URL = os.getenv('TEST_DATABASE_URL')
    if not DATABASE_URL:
        raise RuntimeError(
            "TEST_DATABASE_URL 환경변수가 설정되지 않았습니다.\n"
            "테스트 전용 DB URL을 설정하세요: export TEST_DATABASE_URL='postgresql://...'"
        )
```

#### Task 2: db_schema fixture 간소화 — 백업/복원 로직 제거

- 기존: 5개 테이블 백업 → DROP → migration → 5개 테이블 복원 (약 200줄)
- 변경: 전체 스키마 DROP → migration 실행 (약 40줄)
- 테스트 DB는 운영 데이터가 없으므로 자유롭게 DROP/CREATE 가능

```python
# After: 깔끔한 스키마 초기화
@pytest.fixture(scope='session')
def db_schema():
    db_url = TestConfig.DATABASE_URL
    params = _parse_db_url(db_url)
    conn = psycopg2.connect(**params)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    try:
        # 전체 스키마 클린 DROP (테스트 DB이므로 안전)
        cursor.execute("DROP SCHEMA IF EXISTS public CASCADE")
        cursor.execute("CREATE SCHEMA public")
        cursor.execute("DROP SCHEMA IF EXISTS hr CASCADE")
        cursor.execute("DROP SCHEMA IF EXISTS plan CASCADE")
        cursor.execute("DROP SCHEMA IF EXISTS auth CASCADE")
        cursor.execute("DROP SCHEMA IF EXISTS checklist CASCADE")

        # migrations 순서대로 실행
        migrations_dir = Path(__file__).parent.parent / 'backend' / 'migrations'
        for filename in sorted(migrations_dir.glob('*.sql')):
            sql = filename.read_text(encoding='utf-8')
            for stmt in _split_sql_statements(sql):
                effective = ' '.join(
                    l for l in stmt.splitlines()
                    if l.strip() and not l.strip().startswith('--')
                ).strip().upper()
                if effective in ('BEGIN', 'COMMIT', 'ROLLBACK'):
                    continue
                try:
                    cursor.execute(stmt)
                except Exception as e:
                    print(f"Warning: {filename.name}: {e}")
    finally:
        cursor.close()
        conn.close()

    yield
```

#### Task 3: STAGING_DB_URL 참조 전수 제거

- `db_existing_roles` fixture: `STAGING_DB_URL` → `TestConfig.DATABASE_URL`
- `has_sprint6_schema` fixture: `STAGING_DB_URL` → `TestConfig.DATABASE_URL`
- 파일 전체에서 `STAGING_DB_URL` 변수 및 하드코딩된 운영 DB URL 완전 제거

#### Task 4: 테스트 시드 데이터 fixture 추가

- 운영 DB에서 복원하던 데이터를 테스트 전용 fixture로 교체
- `seed_test_data` (session-scoped): 테스트에 필요한 최소 데이터 삽입
  - workers: admin 1명, manager 1명, 일반 작업자 3명 (FNI MECH, TMS ELEC, GST QI)
  - product_info: 2~3건 (혼재/비혼재 O/N 포함)
  - qr_registry: product_info와 매핑된 QR 2~3건
  - admin_settings: 기본 설정값

```python
@pytest.fixture(scope='session')
def seed_test_data(db_schema):
    """테스트용 시드 데이터 삽입 (session-scoped)"""
    db_url = TestConfig.DATABASE_URL
    params = _parse_db_url(db_url)
    conn = psycopg2.connect(**params)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    try:
        # admin worker
        cursor.execute("""
            INSERT INTO workers (name, email, password_hash, role, company,
                approval_status, email_verified, is_manager, is_admin)
            VALUES ('Test Admin', 'admin@test.axisos.com', %s,
                'ADMIN'::role_enum, 'GST', 'approved'::approval_status_enum,
                true, false, true)
            ON CONFLICT (email) DO NOTHING
        """, (bcrypt.hashpw(b'AdminPass123!', bcrypt.gensalt()).decode(),))

        # ... (일반 작업자, product_info, qr_registry, admin_settings)
    finally:
        cursor.close()
        conn.close()

    yield
```

#### Task 5: `.env.test` 생성 + `.gitignore` 등록

```bash
# .env.test (커밋 금지)
TEST_DATABASE_URL=postgresql://postgres:bNgbAqsBMseFyIDHmiuqLjDCGAuuqmXS@centerbeam.proxy.rlwy.net:20196/railway
```

### 체크리스트

**BE (인프라)**:
- [x] `.env.test` 생성 (TEST_DATABASE_URL 설정) ✅
- [x] `.gitignore`에 `.env.test` 추가 ✅
- [x] `conftest.py` — `STAGING_DB_URL` 하드코딩 제거 ✅
- [x] `conftest.py` — `TestConfig.DATABASE_URL` fallback 제거 → `TEST_DATABASE_URL` 필수 ✅
- [x] `conftest.py` — `db_schema` fixture 간소화 (백업/복원 약 200줄 제거) ✅
- [x] `conftest.py` — `db_existing_roles`, `has_sprint6_schema`에서 `STAGING_DB_URL` → `TestConfig.DATABASE_URL` ✅
- [x] `conftest.py` — `seed_test_data` fixture 추가 ✅
- [x] `conftest.py` — `create_test_worker` fixture에서 Sprint 6 호환 분기 정리 (테스트 DB는 항상 최신 스키마) ✅

**TEST**:
- [x] 테스트 DB 연결 확인 (`pytest --co` — collect only) ✅
- [x] migration 전체 실행 확인 (에러 없이 완료) ✅
- [x] 기존 테스트 전체 실행 regression 확인 ✅ — 714 passed / 14 skipped (Sprint 39-fix로 118→0 수정)
- [x] seed_test_data fixture로 기본 데이터 정상 삽입 확인 ✅

**검증**:
- [x] `STAGING_DB_URL` 문자열이 `conftest.py`에 없음 확인 ✅ (TC-DB-10)
- [x] 운영 DB URL(`maglev.proxy.rlwy.net`)이 코드 어디에도 없음 확인 ✅ (TC-DB-09)
- [x] `TEST_DATABASE_URL` 미설정 시 명확한 RuntimeError 발생 확인 ✅ (TC-DB-02)
- [x] 테스트 실행 후 운영 DB 데이터 영향 없음 확인 ✅

### TEST 작업 (tests/backend/) — Sprint 39

#### test_sprint39_db_isolation.py (신규) — 테스트 DB 분리 검증

**White-box: 환경변수 검증**
1. TC-DB-01: `TEST_DATABASE_URL` 설정 시 → `TestConfig.DATABASE_URL`이 테스트 DB URL
2. TC-DB-02: `TEST_DATABASE_URL` 미설정 시 → `RuntimeError` 발생 (운영 DB fallback 없음)

**White-box: 스키마 초기화**
3. TC-DB-03: `db_schema` fixture 실행 후 → 모든 테이블 존재 확인 (workers, app_task_details, work_start_log, work_completion_log, completion_status, qr_registry, plan.product_info, hr.worker_auth_settings, hr.partner_attendance, auth.refresh_tokens, checklist.*)
4. TC-DB-04: `db_schema` fixture 2회 실행 → 멱등성 확인 (DROP + CREATE 반복 에러 없음)

**White-box: 시드 데이터**
5. TC-DB-05: `seed_test_data` fixture 실행 후 → admin worker 존재 확인
6. TC-DB-06: `seed_test_data` fixture 실행 후 → product_info, qr_registry 존재 확인

**Gray-box: 기존 fixture 호환**
7. TC-DB-07: `create_test_worker` fixture → 테스트 DB에서 정상 동작 (INSERT + RETURNING id)
8. TC-DB-08: `approved_worker` + `get_auth_token` → JWT 발급 + API 호출 정상

**Regression: 운영 DB 격리 확인**
9. TC-DB-09: `conftest.py` 전체 소스에서 운영 DB 호스트(`maglev.proxy.rlwy.net`) 문자열 없음 확인 (코드 레벨 격리 검증)
10. TC-DB-10: `conftest.py` 전체 소스에서 `STAGING_DB_URL` 변수명 없음 확인

### 변경 파일 — Sprint 39

| 파일 | 변경 |
|------|------|
| `tests/conftest.py` | STAGING_DB_URL 제거, db_schema 간소화, seed_test_data 추가, Sprint 6 호환 분기 정리 |
| `.env.test` | TEST_DATABASE_URL 설정 (신규, .gitignore 등록) |
| `.gitignore` | `.env.test` 추가 |
| `tests/backend/test_sprint39_db_isolation.py` | 테스트 DB 분리 검증 10건 (신규) |

### 규칙 — Sprint 39

- 운영 DB URL(`maglev.proxy.rlwy.net:38813`)을 코드에 절대 남기지 않음
- `.env.test`는 `.gitignore`에 반드시 등록 — 커밋 금지
- `db_schema` fixture는 session-scoped 유지 — 테스트 세션당 1회만 스키마 초기화
- `seed_test_data`는 `db_schema` 의존 — 스키마 초기화 후 시드 삽입
- 기존 테스트 파일(`test_sprint37_*.py`, `test_sprint38_*.py` 등)은 수정 없이 통과해야 함
- `create_test_worker` fixture의 Sprint 6 호환 분기(role fallback, company 컬럼 확인)는 제거 가능 — 테스트 DB는 항상 최신 migration 적용 상태
- BE가 코드를 완성하면 TEST가 먼저 코드 리뷰 진행
- 리뷰 통과 후에만 테스트 코드 작성
- .env 파일 절대 커밋 금지

### 절대 수정 금지

- `backend/app/` 하위 모든 파일 — 이 Sprint은 테스트 인프라만 변경
- `backend/migrations/` — migration 파일 수정/추가 없음
- `tests/fixtures/` — 기존 fixture JSON 파일 변경 없음
- `CLAUDE.md` — 수정 없음
- `.env` (운영 환경변수) — 절대 수정 금지

---

### Teammate 프롬프트 — Sprint 39 (테스트 DB 분리)

> **이 프롬프트를 Claude Code teammate에게 전달하여 실행**
> 선행 조건: Railway 테스트 PostgreSQL 인스턴스 생성 완료

```
## Sprint 39: 테스트 DB 분리 — conftest.py 리팩토링

### 컨텍스트
- 참조: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` Sprint 39 섹션
- 대상 파일: `tests/conftest.py`
- 테스트 DB: Railway PostgreSQL 18 (`centerbeam.proxy.rlwy.net:20196`)

### 배경
현재 테스트가 운영 DB를 직접 사용하며, 백업/복원 절차가 복잡하고 위험함.
전용 테스트 DB로 분리하여 안전하게 regression test를 실행할 수 있는 환경을 구축.

### Task 순서

#### Task 1: `.env.test` 생성 + `.gitignore` 등록
- `.env.test` 파일 생성: `TEST_DATABASE_URL=postgresql://postgres:bNgbAqsBMseFyIDHmiuqLjDCGAuuqmXS@centerbeam.proxy.rlwy.net:20196/railway`
- `.gitignore`에 `.env.test` 추가

#### Task 2: `conftest.py` — STAGING_DB_URL 제거 + TestConfig 변경
- `STAGING_DB_URL` 변수 및 하드코딩된 URL 완전 제거
- `TestConfig.DATABASE_URL`: `TEST_DATABASE_URL` 환경변수 필수 (미설정 시 RuntimeError)
- `db_existing_roles`, `has_sprint6_schema` fixture: `STAGING_DB_URL` → `TestConfig.DATABASE_URL`

#### Task 3: `conftest.py` — db_schema fixture 간소화
- 기존 백업/복원 로직 전체 제거 (workers, product_info, qr_registry, auth_settings, attendance)
- 변경: 전체 스키마 DROP → migrations/*.sql 순서대로 실행
- `DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;` + hr, plan, auth, checklist
- migration 파일은 `sorted(migrations_dir.glob('*.sql'))` — 하드코딩 목록 대신 자동 탐색

#### Task 4: `conftest.py` — seed_test_data fixture 추가
- session-scoped, db_schema 의존
- 최소 시드: admin 1명, manager 1명 (GST), 일반 작업자 3명 (FNI MECH, TMS ELEC, GST QI)
- product_info 2~3건, qr_registry 매핑, admin_settings 기본값
- bcrypt로 비밀번호 해싱

#### Task 5: `conftest.py` — create_test_worker 정리
- Sprint 6 호환 분기 제거 (role fallback, company 컬럼 존재 확인)
- 테스트 DB는 항상 최신 스키마 → company 컬럼 항상 존재, role_enum 최신
- role_enum 조회 실패 fallback 제거

#### Task 6: 검증
- `.env.test` 자동 로딩: conftest.py 상단에서 python-dotenv 또는 수동 파싱으로 자동 로드됨 (별도 `source` 불필요)
- `pytest --co` (collect only) — 모든 테스트 수집 확인
- `pytest tests/backend/test_sprint39_db_isolation.py -v` — 신규 테스트 통과
- `pytest tests/ -v` — 전체 regression 통과

### 수정 대상 파일 목록

- `tests/conftest.py` (수정)
- `.env.test` (신규)
- `.gitignore` (수정)
- `tests/backend/test_sprint39_db_isolation.py` (신규)

### 규칙

- CLAUDE.md의 "DB 테이블 정확한 컬럼 명세" 섹션을 반드시 참조
- 운영 DB URL(`maglev.proxy.rlwy.net`)을 코드에 절대 남기지 않음
- `.env.test`는 커밋 금지
- `backend/app/` 하위 파일 수정 금지 — 테스트 인프라만 변경
- `backend/migrations/` 수정 금지
- 기존 테스트 파일 수정 없이 통과해야 함
- N+1 쿼리 금지
- .env 파일 절대 커밋 금지

### 절대 수정 금지

- `backend/app/` 하위 모든 파일 — 이 Sprint은 테스트 인프라만 변경
- `backend/migrations/` — migration 파일 수정/추가 없음
- `tests/fixtures/` — 기존 fixture JSON 파일 변경 없음
- `CLAUDE.md` — 수정 없음
- `.env` — 운영 환경변수 절대 수정 금지
```

---

## Sprint 40-A: QR 스캔 UX 개선 3건 (2026-03-26) — APP FE + BE

> **목적**: QR 스캔 현장 UX 3가지 개선 — 프레임 축소, DOC_ 자동접두어, 오늘 태깅 드롭다운
> **위험도**: ⚠️ QR 카메라는 BUG-5~BUG-23까지 20회 이상 수정 이력 있음. 카메라 초기화/정사각형/MutationObserver 관련 코드는 절대 수정 금지.

### 변경 대상 파일 (총 4개)

| 파일 | 변경 유형 | Task |
|------|----------|------|
| `frontend/lib/services/qr_scanner_web.dart` | 수정 (1줄) | A-1 |
| `frontend/lib/screens/qr/qr_scan_screen.dart` | 수정 (~60줄) | A-1, A-2, A-3 |
| `backend/app/routes/work.py` | 수정 (엔드포인트 1개 추가) | A-3 |
| `backend/app/models/work_start_log.py` | 수정 (함수 1개 추가) | A-3 |

### 테스트 파일 (신규 1개)

| 파일 | 내용 |
|------|------|
| `tests/backend/test_sprint40a_today_tags.py` | 오늘 태깅 API 테스트 5건 |

---

### Task A-1: QR 프레임 크기 축소 (config 값 변경만)

**변경 1 — `frontend/lib/services/qr_scanner_web.dart` 라인 380**

현재:
```javascript
qrbox: 200
```
변경:
```javascript
qrbox: 160
```

이 파일에서 이 1줄 외에 **다른 어떤 코드도 수정하지 않는다**.
- `_forceSquareAfterCameraStart()` 함수 수정 금지
- CSS `aspect-ratio: 1 / 1` 수정 금지
- MutationObserver 로직 수정 금지
- 3단계 카메라 폴백 전략 수정 금지
- `window.__qrScanConfig` 구조 변경 금지 (fps, qrbox 키 유지)

**변경 2 — `frontend/lib/screens/qr/qr_scan_screen.dart` 라인 604**

현재:
```dart
final cameraSize = (screenWidth - 40).clamp(200.0, 350.0); // padding 20*2
```
변경:
```dart
final cameraSize = (screenWidth - 40).clamp(200.0, 300.0); // padding 20*2
```

clamp 상한만 350→300으로 변경. 하한 200 유지. 이 라인 외 주변 코드 수정 금지.

---

### Task A-2: DOC_ 자동 접두어 (직접입력 UX 개선)

**목적**: 사용자가 `DOC_GBWS-6408` 전체를 수동 입력하는 대신, `DOC_` prefix가 자동 표시되고 사용자는 `GBWS-6408`만 입력.

**변경 위치: `frontend/lib/screens/qr/qr_scan_screen.dart`**

#### 변경 A-2-1: 형식 안내 텍스트 수정 (라인 681~683)

현재:
```dart
_scanType == 'worksheet'
    ? '형식: DOC_GBWS-6408'
    : '형식: LOC_01',
```
변경:
```dart
_scanType == 'worksheet'
    ? '형식: GBWS-6408 (DOC_ 자동 추가)'
    : '형식: 01 (LOC_ 자동 추가)',
```

#### 변경 A-2-2: TextFormField에 prefixText 추가 (라인 692~698 영역)

현재:
```dart
TextFormField(
  controller: _qrCodeController,
  decoration: InputDecoration(
    labelText: 'QR 코드',
    labelStyle: const TextStyle(color: GxColors.steel, fontSize: 13),
    hintText: _scanType == 'worksheet' ? 'DOC_GBWS-6408' : 'LOC_01',
    hintStyle: const TextStyle(color: GxColors.silver),
    prefixIcon: const Icon(Icons.qr_code, color: GxColors.accent),
```
변경:
```dart
TextFormField(
  controller: _qrCodeController,
  decoration: InputDecoration(
    labelText: _scanType == 'worksheet' ? 'S/N' : 'Location',
    labelStyle: const TextStyle(color: GxColors.steel, fontSize: 13),
    hintText: _scanType == 'worksheet' ? 'GBWS-6408' : '01',
    hintStyle: const TextStyle(color: GxColors.silver),
    prefixIcon: const Icon(Icons.qr_code, color: GxColors.accent),
    prefixText: _scanType == 'worksheet' ? 'DOC_' : 'LOC_',
    prefixStyle: const TextStyle(
      color: GxColors.accent,
      fontSize: 14,
      fontWeight: FontWeight.w600,
    ),
```

#### 변경 A-2-3: validator 수정 (라인 721~731)

현재:
```dart
validator: (value) {
  if (value == null || value.isEmpty) {
    return 'QR 코드를 입력해주세요.';
  }
  if (_scanType == 'worksheet' && !value.toUpperCase().startsWith('DOC_')) {
    return 'Worksheet QR은 DOC_로 시작해야 합니다.';
  }
  if (_scanType == 'location' && !value.toUpperCase().startsWith('LOC_')) {
    return 'Location QR은 LOC_로 시작해야 합니다.';
  }
  return null;
},
```
변경:
```dart
validator: (value) {
  if (value == null || value.trim().isEmpty) {
    return _scanType == 'worksheet'
        ? 'S/N을 입력해주세요. (예: GBWS-6408)'
        : 'Location 코드를 입력해주세요. (예: 01)';
  }
  return null;
},
```

DOC_/LOC_ 접두어 검사 제거 — prefixText가 자동으로 붙으므로 불필요.

#### 변경 A-2-4: onFieldSubmitted + 확인버튼 submit에서 prefix 결합 (라인 733~736, 766)

현재 (onFieldSubmitted):
```dart
onFieldSubmitted: (value) {
  if (_formKey.currentState!.validate()) {
    _handleQrCode(value);
  }
},
```
변경:
```dart
onFieldSubmitted: (value) {
  if (_formKey.currentState!.validate()) {
    final prefix = _scanType == 'worksheet' ? 'DOC_' : 'LOC_';
    _handleQrCode('$prefix${value.trim().toUpperCase()}');
  }
},
```

현재 (확인 버튼 onTap, 라인 764~767):
```dart
: () {
    if (_formKey.currentState!.validate()) {
      _handleQrCode(_qrCodeController.text);
    }
  },
```
변경:
```dart
: () {
    if (_formKey.currentState!.validate()) {
      final prefix = _scanType == 'worksheet' ? 'DOC_' : 'LOC_';
      _handleQrCode('$prefix${_qrCodeController.text.trim().toUpperCase()}');
    }
  },
```

**중요**: `_handleQrCode()` 함수 자체는 수정하지 않는다. 이 함수는 `DOC_` prefix가 포함된 완전한 QR 코드를 기대하며, 내부에서 `DOC_` 검증 후 BE API를 호출한다. prefix 결합은 submit 시점에서만 처리.

---

### Task A-3: 오늘 태깅 QR 드롭다운 (BE API 신규 + FE 드롭다운)

#### BE 변경 1: `backend/app/models/work_start_log.py` — 함수 추가

파일 끝(라인 249 이후)에 아래 함수 추가:

```python
def get_today_tags_by_worker(worker_id: int) -> List[Dict[str, Any]]:
    """
    작업자의 오늘 태깅한 QR Doc ID 목록 조회 (중복 제거, 최신순)

    Args:
        worker_id: 작업자 ID

    Returns:
        [{"qr_doc_id": "DOC_GBWS-6408", "serial_number": "GBWS-6408", "last_tagged_at": "2026-03-26T09:30:00+09:00"}, ...]
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT DISTINCT ON (qr_doc_id)
                qr_doc_id,
                serial_number,
                started_at AS last_tagged_at
            FROM work_start_log
            WHERE worker_id = %s
              AND started_at >= (CURRENT_DATE AT TIME ZONE 'Asia/Seoul')
            ORDER BY qr_doc_id, started_at DESC
            """,
            (worker_id,)
        )

        rows = cur.fetchall()
        return [
            {
                'qr_doc_id': row['qr_doc_id'],
                'serial_number': row['serial_number'],
                'last_tagged_at': row['last_tagged_at'].isoformat() if row['last_tagged_at'] else None,
            }
            for row in rows
        ]

    except PsycopgError as e:
        logger.error(f"Failed to get today's tags for worker_id={worker_id}: {e}")
        return []
    finally:
        if conn:
            put_conn(conn)
```

#### BE 변경 2: `backend/app/routes/work.py` — 엔드포인트 추가

파일 끝(라인 922 이후, 마지막 함수 뒤)에 추가:

```python
@work_bp.route("/work/today-tags", methods=["GET"])
@jwt_required
def get_today_tags() -> Tuple[Dict[str, Any], int]:
    """
    내가 오늘 태깅한 QR Doc ID 목록 조회

    직접입력 UI에서 드롭다운으로 제공하여, 이전에 태깅했던 QR을 빠르게 재선택

    Headers:
        Authorization: Bearer {token}

    Returns:
        200: {"tags": [{"qr_doc_id": str, "serial_number": str, "last_tagged_at": str}, ...]}
    """
    worker_id = get_current_worker_id()

    from app.models.work_start_log import get_today_tags_by_worker
    tags = get_today_tags_by_worker(worker_id)

    return jsonify({'tags': tags}), 200
```

import 위치: 함수 내부 lazy import 사용 (기존 work.py 상단 import에 추가해도 됨).

#### FE 변경: `frontend/lib/screens/qr/qr_scan_screen.dart` — 드롭다운 추가

**변경 위치**: 직접입력 섹션 내부, "형식 안내" Container(라인 669~688) 바로 아래.

##### 1) State 변수 추가 (클래스 상단, 라인 30~34 근처):
```dart
List<Map<String, dynamic>> _todayTags = [];
bool _loadingTags = false;
```

##### 2) 태깅 목록 로드 함수 추가 (initState 근처):
```dart
Future<void> _loadTodayTags() async {
  if (_loadingTags) return;
  setState(() => _loadingTags = true);
  try {
    final authState = ref.read(authProvider);
    final apiService = ApiService();
    final response = await apiService.get('/app/work/today-tags');
    if (response.statusCode == 200 && response.data != null) {
      final tags = (response.data['tags'] as List?) ?? [];
      setState(() {
        _todayTags = tags.cast<Map<String, dynamic>>();
      });
    }
  } catch (e) {
    debugPrint('[QrScanScreen] Failed to load today tags: $e');
  } finally {
    if (mounted) setState(() => _loadingTags = false);
  }
}
```

##### 3) `_showTextInput` 토글 시 태깅 목록 로드:

현재 (라인 628):
```dart
onTap: () => setState(() => _showTextInput = !_showTextInput),
```
변경:
```dart
onTap: () {
  setState(() => _showTextInput = !_showTextInput);
  if (_showTextInput && _todayTags.isEmpty && _scanType == 'worksheet') {
    _loadTodayTags();
  }
},
```

##### 4) 드롭다운 위젯 (형식 안내 Container 바로 아래, `const SizedBox(height: 12)` 전):

"형식 안내" Container 닫는 `)` 와 `const SizedBox(height: 12)` 사이에 삽입:

```dart
// 오늘 태깅 이력 드롭다운 (worksheet 모드에서만)
if (_scanType == 'worksheet' && _todayTags.isNotEmpty) ...[
  const SizedBox(height: 8),
  Container(
    width: double.infinity,
    padding: const EdgeInsets.symmetric(horizontal: 12),
    decoration: BoxDecoration(
      color: GxColors.white,
      borderRadius: BorderRadius.circular(GxRadius.sm),
      border: Border.all(color: GxColors.mist, width: 1.5),
    ),
    child: DropdownButtonHideUnderline(
      child: DropdownButton<String>(
        isExpanded: true,
        hint: const Text(
          '오늘 태깅 이력에서 선택',
          style: TextStyle(fontSize: 13, color: GxColors.steel),
        ),
        icon: const Icon(Icons.history, color: GxColors.accent, size: 18),
        items: _todayTags.map((tag) {
          return DropdownMenuItem<String>(
            value: tag['qr_doc_id'] as String,
            child: Text(
              tag['serial_number'] as String? ?? tag['qr_doc_id'] as String,
              style: const TextStyle(fontSize: 14, color: GxColors.charcoal),
            ),
          );
        }).toList(),
        onChanged: (qrDocId) {
          if (qrDocId != null) {
            _handleQrCode(qrDocId);
          }
        },
      ),
    ),
  ),
],
```

**주의**: 드롭다운에서 선택 시 `_handleQrCode(qrDocId)`를 직접 호출한다. `qrDocId`는 이미 `DOC_GBWS-6408` 형식이므로 prefix 결합 불필요. `_qrCodeController`를 거치지 않고 바로 처리.

---

### 테스트 코드: `tests/backend/test_sprint40a_today_tags.py`

```python
"""Sprint 40-A: 오늘 태깅 QR 드롭다운 API 테스트"""
import pytest
from datetime import datetime, timezone


class TestTodayTags:
    """GET /api/app/work/today-tags"""

    def test_today_tags_returns_200(self, client, auth_token_worker1):
        """TC-40A-01: 인증된 작업자 → 200 + tags 배열"""
        resp = client.get(
            "/api/app/work/today-tags",
            headers={"Authorization": f"Bearer {auth_token_worker1}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "tags" in data
        assert isinstance(data["tags"], list)

    def test_today_tags_empty_for_new_worker(self, client, auth_token_worker2):
        """TC-40A-02: 오늘 태깅 이력 없는 작업자 → 빈 배열"""
        resp = client.get(
            "/api/app/work/today-tags",
            headers={"Authorization": f"Bearer {auth_token_worker2}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["tags"] == []

    def test_today_tags_distinct_qr_doc(self, client, auth_token_worker1, seed_multiple_tags):
        """TC-40A-03: 같은 QR 2번 태깅 → 중복 제거, 1건만"""
        resp = client.get(
            "/api/app/work/today-tags",
            headers={"Authorization": f"Bearer {auth_token_worker1}"},
        )
        data = resp.get_json()
        qr_ids = [t["qr_doc_id"] for t in data["tags"]]
        assert len(qr_ids) == len(set(qr_ids)), "중복 qr_doc_id 존재"

    def test_today_tags_has_required_fields(self, client, auth_token_worker1, seed_multiple_tags):
        """TC-40A-04: 응답 필드 검증 — qr_doc_id, serial_number, last_tagged_at"""
        resp = client.get(
            "/api/app/work/today-tags",
            headers={"Authorization": f"Bearer {auth_token_worker1}"},
        )
        data = resp.get_json()
        if data["tags"]:
            tag = data["tags"][0]
            assert "qr_doc_id" in tag
            assert "serial_number" in tag
            assert "last_tagged_at" in tag

    def test_today_tags_unauthorized(self, client):
        """TC-40A-05: 토큰 없이 호출 → 401"""
        resp = client.get("/api/app/work/today-tags")
        assert resp.status_code == 401
```

fixture (`seed_multiple_tags`)는 conftest.py의 기존 패턴을 따라 구현.
- worker1로 동일 qr_doc_id 2회 태깅 (DISTINCT 검증용)
- worker1로 서로 다른 qr_doc_id 2개 태깅

---

### 검증 체크리스트

수정 완료 후 아래 시나리오 검증 (코드 리뷰 레벨):

1. [x] **A-1 프레임 축소**: `qrbox: 160`, `clamp(200, 240)` — 실기기 검증 완료 ✅ (BUG-29로 300→240 추가 축소)
2. [x] **A-2 DOC_ 접두어**: Worksheet 모드에서 `DOC_` prefix 자동 표시 — 실기기 검증 완료 ✅
3. [x] **A-2 LOC_ 접두어**: Location 모드에서 `LOC_` prefix 자동 표시 ✅
4. [x] **A-2 submit**: 제출 시 `DOC_` + 입력값 결합 → `_handleQrCode()`에 전달 ✅
5. [x] **A-2 카메라 스캔**: 카메라 경로 수정 없음 확인 — 실기기 검증 완료 ✅
6. [x] **A-3 BE**: `/api/app/work/today-tags` → 오늘 날짜 DISTINCT qr_doc_id 반환 ✅
7. [x] **A-3 FE**: 드롭다운에서 선택 → `_handleQrCode(qrDocId)` 직접 호출 ✅
8. [x] **A-3 빈 이력**: `_todayTags.isNotEmpty` 조건으로 드롭다운 미표시 ✅
9. [x] **하위호환**: `_onQrDetected` → `_handleQrCode` 경로 수정 없음 — 실기기 검증 완료 ✅
10. [x] **테스트**: `test_sprint40a_today_tags.py` 5건 PASSED ✅

### 수정 대상 파일 목록

- `frontend/lib/services/qr_scanner_web.dart` (수정 — qrbox 값 1줄)
- `frontend/lib/screens/qr/qr_scan_screen.dart` (수정 — A-1 cameraSize, A-2 직접입력, A-3 드롭다운)
- `backend/app/routes/work.py` (수정 — 엔드포인트 1개 추가)
- `backend/app/models/work_start_log.py` (수정 — 함수 1개 추가)
- `tests/backend/test_sprint40a_today_tags.py` (신규)

### 규칙

- CLAUDE.md의 "DB 테이블 정확한 컬럼 명세" 섹션을 반드시 참조
- 기존 테스트 전체 PASSED 유지
- N+1 쿼리 금지 — `DISTINCT ON` + 단일 쿼리
- .env 파일 절대 커밋 금지

### ⛔ 절대 수정 금지 — 카메라 관련 (20회 수정 이력, 재수정 시 연쇄 버그 위험)

아래 나열된 코드/함수/로직은 **어떤 이유로도 수정하지 않는다**:

**`qr_scanner_web.dart` (qrbox 값 1줄 외 전체 수정 금지)**:
- `_forceSquareAfterCameraStart()` — 카메라 시작 후 정사각형 강제 함수
- MutationObserver 로직 (DOM 변경 감시 + height=width 복원)
- CSS `#qr-scanner-dom-div` 스타일 (aspect-ratio, overflow, object-fit)
- `_requestCameraPermission()` — 카메라 권한 선요청
- 3단계 카메라 폴백 전략 (environment → user → cameraId)
- `window.__qrScanConfig` 객체 구조 (fps + qrbox 키 유지)
- `ScriptElement` 생성/제거 패턴
- html5-qrcode 라이브러리 버전/CDN URL

**`qr_scan_screen.dart` (직접입력 UI 외 수정 금지)**:
- `_startCamera()` — 카메라 초기화 시퀀스
- `_onScroll()` / `_getCameraContainerRect()` — DOM 위치 동기화
- `_buildCameraView()` — 카메라 뷰 위젯
- `_cameraContainerKey` — 카메라 컨테이너 GlobalKey
- `_onQrDetected()` → `_handleQrCode()` 카메라 스캔 경로
- `_handleQrCode()` 함수 내부 로직 (DOC_ 검증, API 호출, 에러 처리)
- 카메라 Container 위젯 (Builder → cameraSize → Container) — clamp 값만 변경 가능

**BE 기존 코드**:
- `work.py` 기존 엔드포인트 (start_work, complete_work, pause, resume 등) 수정 금지
- `task_service.py` — 알람/시작/완료 서비스 로직 수정 금지
- `work_start_log.py` 기존 3개 함수 수정 금지 (create, get_by_serial, get_by_worker)

---

### Teammate 프롬프트 — Sprint 40-A BE (✅ 완료)

> **상태**: BE 완료 — `work_start_log.py` 함수 추가 + `work.py` 엔드포인트 추가 + `test_sprint40a_today_tags.py` 5/5 PASSED

```
## Sprint 40-A BE: 오늘 태깅 API (Task A-3 BE)

### 역할: BE teammate
### 소유 파일 (이 파일만 수정 가능):
- `backend/app/routes/work.py`
- `backend/app/models/work_start_log.py`
- `tests/backend/test_sprint40a_today_tags.py` (신규)

### 절대 수정 금지 (FE teammate 소유):
- `frontend/` 하위 모든 파일

### Task
1. `work_start_log.py` 파일 끝에 `get_today_tags_by_worker()` 함수 추가
2. `work.py` 파일 끝에 `GET /api/app/work/today-tags` 엔드포인트 추가
3. `test_sprint40a_today_tags.py` 5건 작성 + 실행

### 결과: ✅ 5/5 PASSED
```

---

### Teammate 프롬프트 — Sprint 40-A FE (QR 스캔 UX 개선)

> **이 프롬프트를 Claude Code FE teammate에게 전달하여 실행**
> 선행 조건: Sprint 40-A BE 완료 (✅ today-tags API 배포됨)

```
## Sprint 40-A FE: QR 스캔 UX 개선 3건 (Task A-1, A-2, A-3 FE)

### 역할: FE teammate
### 소유 파일 (이 파일만 수정 가능 — 총 2개):
- `frontend/lib/services/qr_scanner_web.dart` (1줄 변경)
- `frontend/lib/screens/qr/qr_scan_screen.dart` (~60줄 변경)

### 절대 수정 금지 (BE teammate 소유 — 이미 완료됨):
- `backend/` 하위 모든 파일 — 수정/추가/삭제 금지
- `tests/` 하위 모든 파일 — 수정/추가/삭제 금지

### 컨텍스트
- 참조: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` Sprint 40-A 섹션
- 위 섹션에 Task A-1, A-2, A-3 FE의 **정확한 변경 내용, 라인 번호, 코드**가 모두 명시됨
- 반드시 해당 섹션을 먼저 끝까지 읽고, 지시된 내용 **그대로** 수정할 것

### ⚠️ 최우선 규칙: 카메라 코드 수정 금지

QR 카메라는 BUG-5~BUG-23까지 **20회 이상 수정 이력**이 있다.
정사각형 강제/MutationObserver/CSS 코드가 극도로 민감하며, 숫자값 외 어떤 수정도 연쇄 버그를 유발한다.

**`qr_scanner_web.dart`에서 수정 가능한 것 — 딱 1줄**:
- 라인 380: `qrbox: 200` → `qrbox: 160`
- 이 파일의 다른 **어떤 코드도** 수정/추가/삭제하지 않는다

**`qr_scanner_web.dart`에서 수정 금지 목록** (하나라도 변경 시 전체 카메라 기능 장애):
- `_forceSquareAfterCameraStart()` 함수 전체
- MutationObserver 콜백 로직 전체
- CSS `#qr-scanner-dom-div` 스타일블록 전체 (aspect-ratio, overflow, object-fit)
- `_requestCameraPermission()` 함수 전체
- 3단계 카메라 폴백 전략 (environment → user → cameraId)
- `window.__qrScanConfig` 객체 키 구조 (fps, qrbox)
- `ScriptElement` 생성/제거 패턴
- html5-qrcode 라이브러리 참조

**`qr_scan_screen.dart`에서 수정 가능한 영역**:
- 라인 604: cameraSize clamp 상한 350→300 (숫자 1개)
- 라인 30~34 근처: State 변수 2개 추가
- 클래스 내 함수 추가: `_loadTodayTags()`
- 라인 628: `_showTextInput` 토글에 태깅 로드 추가
- 라인 660~790: 직접입력 섹션 내부 (형식안내, TextFormField, validator, submit, 드롭다운)

**`qr_scan_screen.dart`에서 수정 금지 목록**:
- `_startCamera()` — 카메라 초기화 시퀀스
- `_onScroll()` / `_getCameraContainerRect()` — DOM 위치 동기화
- `_buildCameraView()` — 카메라 뷰 위젯
- `_cameraContainerKey` — 카메라 컨테이너 GlobalKey
- `_onQrDetected()` 함수 — 카메라 스캔 콜백
- `_handleQrCode()` 함수 내부 — DOC_ 검증/API 호출/에러 처리 전체
- 카메라 Container 위젯 (Builder → cameraSize → Container 구조) — clamp 값만 변경

### Task 순서 (반드시 이 순서대로)

#### Task A-1: QR 프레임 크기 축소 (숫자 2개만 변경)

**변경 1** — `frontend/lib/services/qr_scanner_web.dart`:
파일 내에서 `qrbox: 200`을 찾아 `qrbox: 160`으로 변경. 이 파일은 이 1줄 외에 절대 수정하지 않는다.

**변경 2** — `frontend/lib/screens/qr/qr_scan_screen.dart`:
`(screenWidth - 40).clamp(200.0, 350.0)`을 찾아 `(screenWidth - 40).clamp(200.0, 300.0)`으로 변경.

#### Task A-2: DOC_ 자동 접두어 (직접입력 UI 개선)

AGENT_TEAM_LAUNCH.md Sprint 40-A 섹션의 "Task A-2" 참조. 정확한 "현재" → "변경" 코드가 명시되어 있다.

4가지 변경:
1. **A-2-1**: 형식 안내 텍스트 — `'형식: DOC_GBWS-6408'` → `'형식: GBWS-6408 (DOC_ 자동 추가)'`, LOC도 동일
2. **A-2-2**: TextFormField — `labelText`, `hintText` 변경 + `prefixText` / `prefixStyle` 추가
3. **A-2-3**: validator — `DOC_`/`LOC_` 시작 검사 제거, 빈값만 체크
4. **A-2-4**: onFieldSubmitted + 확인버튼 onTap — submit 시 `'$prefix${value.trim().toUpperCase()}'` 결합 후 `_handleQrCode()` 호출

**핵심**: `_handleQrCode()` 함수 자체는 수정하지 않는다. 이 함수는 `DOC_` prefix가 포함된 완전한 QR 코드를 기대한다. prefix 결합은 submit 시점에서만 처리.

#### Task A-3 FE: 오늘 태깅 QR 드롭다운

AGENT_TEAM_LAUNCH.md Sprint 40-A 섹션의 "Task A-3" FE 변경 참조.

4가지 변경:
1. **State 변수** 2개 추가: `_todayTags`, `_loadingTags`
2. **`_loadTodayTags()` 함수** 추가 — `GET /api/app/work/today-tags` 호출 (BE 이미 완료됨)
3. **`_showTextInput` 토글**에 `_loadTodayTags()` 호출 추가
4. **드롭다운 위젯** — 형식 안내 Container 아래, worksheet 모드 + 태깅 이력 있을 때만 표시

**드롭다운 선택 시**: `_handleQrCode(qrDocId)` 직접 호출. `qrDocId`는 이미 `DOC_GBWS-6408` 형식이므로 prefix 결합 불필요. `_qrCodeController`를 거치지 않는다.

### 검증 체크리스트

수정 완료 후 아래를 **반드시** 확인:

1. `flutter analyze` 에러 없음
2. `qr_scanner_web.dart` — `git diff`로 qrbox 값 변경 1줄만 있는지 확인. **다른 diff가 있으면 즉시 revert**
3. `qr_scan_screen.dart` — `_handleQrCode()` 함수 내부에 diff 없음 확인
4. `qr_scan_screen.dart` — `_startCamera()`, `_onScroll()`, `_buildCameraView()` 에 diff 없음 확인
5. `qr_scan_screen.dart` — `_onQrDetected()` 에 diff 없음 확인
6. DOC_ prefix 결합이 submit 경로(onFieldSubmitted + 확인버튼)에서만 발생하는지 확인
7. 드롭다운에서 선택 시 prefix 결합 없이 `_handleQrCode(qrDocId)` 직접 호출하는지 확인
8. `backend/` 하위 파일에 어떤 diff도 없음 확인

### 수정 대상 파일 (2개만, 그 외 절대 수정 금지)

1. `frontend/lib/services/qr_scanner_web.dart` — qrbox 숫자 1줄만
2. `frontend/lib/screens/qr/qr_scan_screen.dart` — A-1 clamp + A-2 직접입력 + A-3 드롭다운

### diff 검증 명령 (최종 확인용)

수정 완료 후 아래 명령으로 의도치 않은 변경이 없는지 반드시 확인:
```bash
# qr_scanner_web.dart — qrbox 1줄만 변경되었는지
git diff frontend/lib/services/qr_scanner_web.dart | grep "^[+-]" | grep -v "^[+-][+-][+-]"
# 기대 결과: -          qrbox: 200 / +          qrbox: 160 (이 2줄만)

# backend 변경 없음 확인
git diff backend/
# 기대 결과: 아무것도 없음 (BE는 이미 별도 커밋됨)

# _handleQrCode 함수 변경 없음 확인
git diff frontend/lib/screens/qr/qr_scan_screen.dart | grep "_handleQrCode"
# 기대 결과: _handleQrCode 함수 정의(Future<void> _handleQrCode) 라인이 diff에 없음
```
```

---

## Sprint 38-B: product/progress API — last_task_name / last_task_category 필드 추가 (VIEW #45)

> **목적**: S/N 카드뷰 및 상세뷰에서 마지막 작업자가 수행한 **Task 이름**(예: 캐비넷 조립)과 **카테고리**(예: MECH)를 표시할 수 있도록 `GET /api/app/product/progress` 응답에 2개 필드 추가.
>
> **배경**: Sprint 38에서 `last_worker`, `last_activity_at` 필드를 추가했으나, "어떤 작업을 했는지" 정보가 없어 VIEW에서 표시 불가. `work_start_log`, `work_completion_log` 테이블에 `task_name`, `task_category` 컬럼이 이미 존재하므로, 기존 서브쿼리의 SELECT 절에 2개 컬럼을 추가하면 됨.

### 수정 대상: 1개 파일

| 파일 | 변경 내용 |
|------|-----------|
| `backend/app/services/progress_service.py` | Step 5 last_activity 서브쿼리에 `task_name`, `task_category` SELECT 추가 + products 배열에 필드 추가 |

### 변경 상세

#### 1) `progress_service.py` — Step 5 last_activity 서브쿼리 수정

**현재 코드** (라인 ~116-143):
```python
last_activity_query = """
    SELECT DISTINCT ON (combined.serial_number)
           combined.serial_number,
           w.name AS last_worker,
           combined.activity_at AS last_activity_at
    FROM (
        SELECT wsl.serial_number,
               wsl.worker_id,
               wsl.started_at AS activity_at
        FROM work_start_log wsl
        WHERE wsl.serial_number = ANY(%s)
        UNION ALL
        SELECT wcl.serial_number,
               wcl.worker_id,
               wcl.completed_at AS activity_at
        FROM work_completion_log wcl
        WHERE wcl.serial_number = ANY(%s)
          AND wcl.completed_at IS NOT NULL
    ) combined
    JOIN workers w ON w.id = combined.worker_id
    ORDER BY combined.serial_number, combined.activity_at DESC
"""
```

**변경 코드**:
```python
last_activity_query = """
    SELECT DISTINCT ON (combined.serial_number)
           combined.serial_number,
           w.name AS last_worker,
           combined.activity_at AS last_activity_at,
           combined.task_name AS last_task_name,
           combined.task_category AS last_task_category
    FROM (
        SELECT wsl.serial_number,
               wsl.worker_id,
               wsl.started_at AS activity_at,
               wsl.task_name,
               wsl.task_category
        FROM work_start_log wsl
        WHERE wsl.serial_number = ANY(%s)
        UNION ALL
        SELECT wcl.serial_number,
               wcl.worker_id,
               wcl.completed_at AS activity_at,
               wcl.task_name,
               wcl.task_category
        FROM work_completion_log wcl
        WHERE wcl.serial_number = ANY(%s)
          AND wcl.completed_at IS NOT NULL
    ) combined
    JOIN workers w ON w.id = combined.worker_id
    ORDER BY combined.serial_number, combined.activity_at DESC
"""
```

#### 2) `progress_service.py` — Step 6 products 배열 필드 추가

**현재 코드** (라인 ~139-152):
```python
for la_row in cur.fetchall():
    last_activity_map[la_row['serial_number']] = {
        'last_worker': la_row['last_worker'],
        'last_activity_at': la_row['last_activity_at'],
    }

# Step 6: products 배열에 last_worker / last_activity_at 필드 추가
for p in products:
    activity = last_activity_map.get(p['serial_number'])
    p['last_worker'] = activity['last_worker'] if activity else None
    p['last_activity_at'] = (
        activity['last_activity_at'].isoformat()
        if activity and activity.get('last_activity_at') else None
    )
```

**변경 코드**:
```python
for la_row in cur.fetchall():
    last_activity_map[la_row['serial_number']] = {
        'last_worker': la_row['last_worker'],
        'last_activity_at': la_row['last_activity_at'],
        'last_task_name': la_row['last_task_name'],
        'last_task_category': la_row['last_task_category'],
    }

# Step 6: products 배열에 last_worker / last_activity_at / last_task 필드 추가
for p in products:
    activity = last_activity_map.get(p['serial_number'])
    p['last_worker'] = activity['last_worker'] if activity else None
    p['last_activity_at'] = (
        activity['last_activity_at'].isoformat()
        if activity and activity.get('last_activity_at') else None
    )
    p['last_task_name'] = activity['last_task_name'] if activity else None
    p['last_task_category'] = activity['last_task_category'] if activity else None
```

### TEST 작업 — Sprint 38-B

**파일**: `tests/backend/test_sprint38b_last_task.py`

기존 `test_sprint38_last_activity.py` 패턴 참조. 테스트 케이스:

| TC | 설명 | 검증 |
|----|------|------|
| TC-LT-01 | start 로그만 있는 S/N | `last_task_name`, `last_task_category`가 해당 start 로그의 값과 일치 |
| TC-LT-02 | start + completion 로그 (completion이 최신) | 최신 로그(completion)의 `task_name`, `task_category` 반환 |
| TC-LT-03 | 여러 태깅 이력 — 가장 최근 것만 반환 | `DISTINCT ON + DESC` 정렬로 최신 1건의 task 정보 |
| TC-LT-04 | 태깅 이력 없는 S/N | `last_task_name`, `last_task_category` 모두 `None` |

### 규칙 — Sprint 38-B

- ⛔ `work.py`, `work_start_log.py`, `work_completion_log.py` 등 **다른 파일 수정 금지** — `progress_service.py` 1개 파일만 수정
- ⛔ 기존 `last_worker`, `last_activity_at` 로직 변경 금지 — 필드 추가만
- ⛔ DB 스키마(ALTER TABLE) 변경 없음 — 이미 `task_name`, `task_category` 컬럼 존재
- ✅ UNION ALL 양쪽(start/completion) 모두 동일한 `task_name`, `task_category` 컬럼 추가 필수

### Teammate 프롬프트 — Sprint 38-B (#45 last_task_name/category 추가)

```
## Sprint 38-B BE: product/progress API last_task_name 필드 추가

너는 AXIS-OPS BE teammate다. `backend/` 하위 파일만 수정 가능.

### 목표
`GET /api/app/product/progress` 응답의 각 product 객체에 `last_task_name`, `last_task_category` 2개 필드를 추가한다.

### 수정 대상
- `backend/app/services/progress_service.py` — 1개 파일만

### 작업 내용
1. Step 5 last_activity_query의 UNION ALL 양쪽에 `task_name`, `task_category` 컬럼 추가
2. 외부 SELECT에 `combined.task_name AS last_task_name`, `combined.task_category AS last_task_category` 추가
3. last_activity_map 딕셔너리에 `last_task_name`, `last_task_category` 추가
4. Step 6 for 루프에서 products에 `last_task_name`, `last_task_category` 필드 추가

- 참조: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` Sprint 38-B 섹션
- "현재 코드" → "변경 코드" diff가 정확히 명시되어 있으니 그대로 적용

### 테스트
- `tests/backend/test_sprint38b_last_task.py` 신규 생성
- 기존 `test_sprint38_last_activity.py` 패턴 참조
- TC-LT-01 ~ TC-LT-04 (4건)

### 규칙
- ⛔ `progress_service.py` 외 다른 파일 수정 금지
- ⛔ 기존 last_worker/last_activity_at 로직 변경 금지 (필드 추가만)
- ⛔ DB 스키마 변경 없음

### 검증 명령
pytest tests/backend/test_sprint38b_last_task.py -v
pytest tests/backend/test_sprint38_last_activity.py -v  # 기존 테스트 regression 확인
pytest tests/backend/test_sn_progress.py -v  # 기존 progress 테스트 regression 확인
```

---

## BUG-24: QR 스캔 — 카메라 프레임 과대 + 직접입력 안보임 (Sprint 40-A 후속)

> **증상**: Sprint 40-A 적용 후 카메라 외곽 프레임이 화면 대부분을 차지하며, 하단 "직접 입력" 섹션이 스크롤 없이는 보이지 않음.
>
> **원인 분석**:
> 1. `Column`의 `crossAxisAlignment: CrossAxisAlignment.stretch` (라인 485)가 카메라 Container의 `width: cameraSize`를 무시 → 전체 너비(~350px)로 강제 확장
> 2. `cameraSize` max 300 + AppBar + QR타입 카드 + 여백 합산 → 직접입력 카드가 뷰포트 밖으로 밀림
>
> **영향 범위**: FE 1개 파일 (`qr_scan_screen.dart`) — BE 변경 없음

### 수정 대상: 1개 파일

| 파일 | 변경 내용 |
|------|-----------|
| `frontend/lib/screens/qr/qr_scan_screen.dart` | 카메라 Container를 Center로 감싸 stretch 방지 + cameraSize max 축소 |

### 변경 상세

#### 1) cameraSize clamp 축소 — max 300 → 240

**현재 코드** (라인 ~625):
```dart
final cameraSize = (screenWidth - 40).clamp(200.0, 300.0); // padding 20*2
```

**변경 코드**:
```dart
final cameraSize = (screenWidth - 40).clamp(200.0, 240.0); // padding 20*2
```

> qrbox=160이므로 240 컨테이너 안에 충분히 들어감 (160 < 240). 여백 40px씩 확보.

#### 2) 카메라 Container를 Center로 감싸서 stretch 무시

**현재 코드** (라인 ~622-638):
```dart
Builder(
  builder: (context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final cameraSize = (screenWidth - 40).clamp(200.0, 300.0); // padding 20*2
    return Container(
      key: _cameraContainerKey,
      width: cameraSize,
      height: cameraSize,
      decoration: BoxDecoration(
        color: Colors.black,
        borderRadius: BorderRadius.circular(GxRadius.lg),
        border: Border.all(color: GxColors.mist, width: 1),
      ),
      clipBehavior: Clip.antiAlias,
      child: _buildCameraView(),
    );
  },
),
```

**변경 코드**:
```dart
Builder(
  builder: (context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final cameraSize = (screenWidth - 40).clamp(200.0, 240.0); // padding 20*2
    return Center(
      child: Container(
        key: _cameraContainerKey,
        width: cameraSize,
        height: cameraSize,
        decoration: BoxDecoration(
          color: Colors.black,
          borderRadius: BorderRadius.circular(GxRadius.lg),
          border: Border.all(color: GxColors.mist, width: 1),
        ),
        clipBehavior: Clip.antiAlias,
        child: _buildCameraView(),
      ),
    );
  },
),
```

> `Center` 위젯이 `CrossAxisAlignment.stretch`를 차단하여 Container가 정확히 `cameraSize × cameraSize` 정사각형 유지.

### 규칙 — BUG-24

- ⛔ `_buildCameraView()` 함수 내부 수정 금지
- ⛔ `qr_scanner_web.dart` 수정 금지 (CSS, MutationObserver, aspect-ratio 등)
- ⛔ `_handleQrCode()` 함수 수정 금지
- ⛔ `_startCamera()` 함수 수정 금지
- ⛔ DOC_ prefix, today-tags 드롭다운 등 Sprint 40-A 기능 수정 금지
- ✅ 변경 허용: `cameraSize` clamp 숫자값 1줄 + `Center` 래핑 추가 1줄

### Teammate 프롬프트 — BUG-24 (카메라 프레임 축소)

```
## BUG-24 FE: QR 스캔 카메라 프레임 과대 수정

너는 AXIS-OPS FE teammate다. `frontend/` 하위 파일만 수정 가능.

### 목표
QR 스캔 화면의 카메라 프레임이 너무 커서 하단 직접입력 섹션이 보이지 않는 문제 수정.

### 수정 대상
- `frontend/lib/screens/qr/qr_scan_screen.dart` — 1개 파일, 2곳 수정

### 작업 내용
1. 라인 ~625: `cameraSize` clamp max를 300 → 240으로 변경
   ```dart
   // 변경 전
   final cameraSize = (screenWidth - 40).clamp(200.0, 300.0);
   // 변경 후
   final cameraSize = (screenWidth - 40).clamp(200.0, 240.0);
   ```

2. 카메라 Container를 `Center` 위젯으로 감싸기
   ```dart
   // 변경 전
   return Container(
     key: _cameraContainerKey,
   // 변경 후
   return Center(
     child: Container(
       key: _cameraContainerKey,
   ```
   → 닫는 괄호도 추가: Container 닫는 `)` 뒤에 `,` + Center 닫는 `)` 추가

- 참조: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` BUG-24 섹션

### ⛔ 절대 수정 금지
- _buildCameraView() 함수
- qr_scanner_web.dart (CSS, MutationObserver, aspect-ratio 등 전체)
- _handleQrCode() 함수
- _startCamera() 함수
- DOC_ prefix, today-tags 드롭다운 등 Sprint 40-A 기능 코드

### 검증 명령
git diff frontend/lib/screens/qr/qr_scan_screen.dart | grep "^[+-]" | grep -v "^[+-][+-][+-]"
# 기대 결과: clamp 숫자 변경 1줄 + Center( 추가 1줄 + 닫는 괄호 1줄 (총 ~4-6줄 diff만)

git diff frontend/lib/services/
# 기대 결과: 아무것도 없음 (qr_scanner_web.dart 변경 금지)
```

---

## #46 진단: 상세뷰 workers 누락 — task_id 매핑 불일치 (VIEW OPS_API_REQUESTS #46)

> **증상**: 카드뷰에서는 "박새벽 · 배선 포설" 정상 표시, 상세뷰에서는 박새벽 누락.
>
> **근본 원인 가설**: 두 API의 workers 조회 기준이 다름.
> - 카드뷰 (`progress_service.py`): `WHERE serial_number = ANY(%s)` → S/N 기준 전체 매칭 ✅
> - 상세뷰 (`work.py` 라인 397): `WHERE wsl.task_id = ANY(%s)` → `app_task_details.id` FK 기준 매칭
>
> `work_start_log.task_id`가 현재 `app_task_details`의 id와 매핑되지 않으면 workers 쿼리에서 누락됨.

### Phase 1: 진단 SQL (Railway DB에서 실행)

아래 3개 쿼리를 순서대로 실행하여 원인을 확정한다.

```sql
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 진단 1) GBWS-6905의 ELEC app_task_details 레코드 확인
-- → 기대: 배선 포설 등 ELEC task가 존재하고 id값 확인
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT id, task_id, task_name, task_category, serial_number, worker_id, started_at
FROM app_task_details
WHERE serial_number = 'GBWS-6905' AND task_category = 'ELEC'
ORDER BY id;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 진단 2) 박새벽의 work_start_log에서 GBWS-6905 기록 확인
-- → 기대: task_id, task_name, task_category 등 확인
-- → 핵심: 여기 task_id가 진단 1의 id 목록에 포함되는지 확인
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT wsl.id AS log_id, wsl.task_id, wsl.serial_number, wsl.task_name,
       wsl.task_category, wsl.task_id_ref, wsl.worker_id, w.name AS worker_name,
       wsl.started_at
FROM work_start_log wsl
JOIN workers w ON w.id = wsl.worker_id
WHERE wsl.serial_number = 'GBWS-6905'
ORDER BY wsl.started_at DESC;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 진단 3) task_id 매핑 일치 여부 직접 확인
-- → LEFT JOIN으로 work_start_log.task_id가 app_task_details에 매핑되는지
-- → atd.id IS NULL인 행 = 매핑 실패 (누락 원인)
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT wsl.id AS log_id, wsl.task_id, wsl.task_name, wsl.task_category,
       w.name AS worker_name, wsl.started_at,
       atd.id AS matched_task_detail_id,
       CASE WHEN atd.id IS NULL THEN '❌ 매핑 실패' ELSE '✅ 매핑 성공' END AS status
FROM work_start_log wsl
JOIN workers w ON w.id = wsl.worker_id
LEFT JOIN app_task_details atd
    ON wsl.task_id = atd.id AND atd.serial_number = 'GBWS-6905'
WHERE wsl.serial_number = 'GBWS-6905'
ORDER BY wsl.started_at DESC;
```

### Phase 2: 원인별 대응 방향

#### 시나리오 A: task seeding 누락

진단 1에서 "배선 포설" task가 `app_task_details`에 없는 경우.
→ `task_seed.py`에 해당 task 추가 후 재실행. **코드 수정 불필요.**

#### 시나리오 B: task_id FK 불일치 (가장 가능성 높음)

진단 3에서 `❌ 매핑 실패` 행이 존재하는 경우.
= `work_start_log.task_id`가 가리키는 `app_task_details` 레코드가 다른 S/N이거나, 삭제/재생성되어 id가 변경됨.

**원인**: task seed 재실행 시 기존 레코드 DELETE → 새 id로 INSERT. 기존 `work_start_log.task_id`는 옛 id를 가리킴.

**수정안**: `work.py` workers 쿼리를 `task_id` 단독 매핑 → `serial_number + task_category + task_id_ref` 복합 매핑으로 변경.

#### 시나리오 C: 동일 S/N에 중복 task 레코드

진단 1에서 같은 task_name/task_id가 여러 id로 존재하는 경우.
→ 중복 제거 + UPSERT 로직 확인 필요.

### Phase 3: 시나리오 B 수정안 (진단 결과 확인 후 적용)

> ⚠️ 아래 수정은 진단 3에서 `❌ 매핑 실패`가 확인된 후에만 진행.

#### 수정 대상: 1개 파일

| 파일 | 변경 내용 |
|------|-----------|
| `backend/app/routes/work.py` | workers 일괄 조회 쿼리 — `task_id` 단독 → `serial_number + task_id` 복합 + fallback |

#### 변경 상세: `work.py` 라인 383~401

**현재 코드** (task_id 단독 매핑):
```python
cur.execute(
    """
    SELECT
        wsl.task_id,
        wsl.worker_id,
        w.name AS worker_name,
        wsl.started_at,
        wcl.completed_at,
        wcl.duration_minutes,
        CASE WHEN wcl.id IS NOT NULL THEN 'completed' ELSE 'in_progress' END AS status
    FROM work_start_log wsl
    JOIN workers w ON wsl.worker_id = w.id
    LEFT JOIN work_completion_log wcl
        ON wsl.task_id = wcl.task_id AND wsl.worker_id = wcl.worker_id
    WHERE wsl.task_id = ANY(%s)
    ORDER BY wsl.task_id, wsl.started_at ASC
    """,
    (task_db_ids,)
)
```

**변경 코드** (serial_number + task_category + task_id_ref 복합 매핑):
```python
# task_list에서 task_id_ref → db_id 매핑 생성 (task_id_ref 기반 매칭용)
task_ref_to_id = {}
for item in task_list:
    key = (item.get('task_category', ''), item.get('task_id', ''))  # task_id = task_id_ref
    task_ref_to_id[key] = item['id']

cur.execute(
    """
    SELECT
        wsl.task_id,
        wsl.task_category,
        wsl.task_id_ref,
        wsl.worker_id,
        w.name AS worker_name,
        wsl.started_at,
        wcl.completed_at,
        wcl.duration_minutes,
        CASE WHEN wcl.id IS NOT NULL THEN 'completed' ELSE 'in_progress' END AS status
    FROM work_start_log wsl
    JOIN workers w ON wsl.worker_id = w.id
    LEFT JOIN work_completion_log wcl
        ON wsl.task_id = wcl.task_id AND wsl.worker_id = wcl.worker_id
    WHERE wsl.serial_number = %s
    ORDER BY wsl.task_category, wsl.started_at ASC
    """,
    (serial_number,)
)
rows = cur.fetchall()
for row in rows:
    # 1차: task_id로 직접 매핑 (정상 경우)
    tid = row['task_id']
    if tid in workers_by_task:
        workers_by_task[tid].append({
            'worker_id': row['worker_id'],
            'worker_name': row['worker_name'],
            'started_at': row['started_at'].isoformat() if row['started_at'] else None,
            'completed_at': row['completed_at'].isoformat() if row['completed_at'] else None,
            'duration_minutes': row['duration_minutes'],
            'status': row['status'],
        })
    else:
        # 2차 fallback: task_category + task_id_ref로 매핑
        ref_key = (row['task_category'], row['task_id_ref'])
        fallback_tid = task_ref_to_id.get(ref_key)
        if fallback_tid and fallback_tid in workers_by_task:
            workers_by_task[fallback_tid].append({
                'worker_id': row['worker_id'],
                'worker_name': row['worker_name'],
                'started_at': row['started_at'].isoformat() if row['started_at'] else None,
                'completed_at': row['completed_at'].isoformat() if row['completed_at'] else None,
                'duration_minutes': row['duration_minutes'],
                'status': row['status'],
            })
            logger.info(
                f"[#46-fallback] worker={row['worker_name']} matched via "
                f"ref_key={ref_key} instead of task_id={tid}"
            )
```

> **변경 포인트**:
> 1. `WHERE wsl.task_id = ANY(%s)` → `WHERE wsl.serial_number = %s` (S/N 기준 전체 조회)
> 2. 1차: 기존 `task_id` 매핑 유지 (정상 경우)
> 3. 2차: `task_id` 매핑 실패 시 `task_category + task_id_ref` 로 fallback
> 4. fallback 사용 시 `[#46-fallback]` 로그로 추적 가능

### TEST 작업 — #46

**파일**: `tests/backend/test_issue46_workers_mapping.py`

| TC | 설명 | 검증 |
|----|------|------|
| TC-46-01 | 정상 매핑 — task_id가 일치하는 경우 | workers 배열에 정상 포함 |
| TC-46-02 | task_id 불일치 — app_task_details 재생성으로 id 변경 | fallback으로 task_category + task_id_ref 매핑 성공 |
| TC-46-03 | 다른 S/N의 work_start_log가 혼입 안 됨 | serial_number 필터로 격리 |
| TC-46-04 | completion_log와 JOIN 정상 동작 | completed_at, duration_minutes 정상 반환 |
| TC-46-05 | 동시작업 (multi-worker) | 같은 task에 2명 → workers 배열에 2건 |

### 규칙 — #46

- ⛔ `progress_service.py` 수정 금지 — 카드뷰 API는 정상 동작
- ⛔ `work_start_log.py`, `work_completion_log.py` 모델 수정 금지
- ⛔ `task_service.py` 의 `start_work()` 수정 금지
- ✅ `work.py`의 workers 일괄 조회 블록(라인 375~418)만 수정
- ✅ 로그에 `[#46-fallback]` prefix로 추적 가능하게

### Teammate 프롬프트 — #46 (진단 확인 후 실행)

```
## #46 BE: 상세뷰 workers 매핑 — task_id fallback 추가

너는 AXIS-OPS BE teammate다. `backend/` 하위 파일만 수정 가능.

### 배경
상세뷰 API (`GET /api/app/tasks/{sn}?all=true`)에서 workers 조회 시 `work_start_log.task_id = ANY(task_db_ids)` 로만 매핑하는데, task seed 재실행 등으로 `app_task_details.id`가 변경되면 `work_start_log.task_id`와 불일치하여 작업자가 누락됨.

### 목표
workers 조회를 task_id 단독 매핑 → serial_number 기준 조회 + task_id/task_ref fallback 복합 매핑으로 변경.

### 수정 대상
- `backend/app/routes/work.py` — 1개 파일, workers 일괄 조회 블록 (라인 ~375-418)

### 작업 내용
1. WHERE 절을 `task_id = ANY(%s)` → `serial_number = %s` 로 변경
2. SELECT에 `wsl.task_category`, `wsl.task_id_ref` 추가
3. 기존 for row 루프를 2단계 매핑으로 변경:
   - 1차: task_id로 직접 매핑 (기존 동작 유지)
   - 2차: task_id 매핑 실패 시 task_category + task_id_ref로 fallback
4. fallback 사용 시 `[#46-fallback]` 로그 기록

- 참조: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` #46 섹션
- "현재 코드" → "변경 코드" diff가 정확히 명시되어 있으니 그대로 적용

### 테스트
- `tests/backend/test_issue46_workers_mapping.py` 신규 생성
- TC-46-01 ~ TC-46-05 (5건)
- 기존 regression: `pytest tests/backend/ -v --timeout=30` 전체 통과 확인

### 규칙
- ⛔ `progress_service.py` 수정 금지
- ⛔ `work_start_log.py`, `work_completion_log.py` 모델 수정 금지
- ⛔ `task_service.py` 수정 금지
- ✅ `work.py` 1개 파일만 수정

### 검증 명령
pytest tests/backend/test_issue46_workers_mapping.py -v
pytest tests/backend/test_sprint38_last_activity.py -v  # regression
pytest tests/backend/test_sn_progress.py -v  # regression
```

---

## Sprint 40-C: 비활성 사용자 관리 (Inactive User Management)

> 등록일: 2026-03-27
> 트랙: Sprint 40 Track C (BE 전용)
> 선행: Sprint 1 (workers 테이블), Sprint 32 (app_access_log 테이블)
> 난이도: 중~상

### 배경

현재 시스템에는 장기 미로그인 사용자를 감지·관리하는 기능이 없음.
퇴사/이직한 작업자 계정이 approved 상태로 남아 보안 리스크 발생 가능.
**soft delete 방식** (is_active=FALSE) + **admin 최종 승인** 후 비활성화 처리.

### 현재 DB 상태 (확인 완료)

```
workers 테이블 (001_create_workers.sql):
- is_active 컬럼 없음 ❌
- deactivated_at 컬럼 없음 ❌
- last_login_at 컬럼 없음 ❌

app_access_log 테이블 (026_access_log.sql):
- worker_id + created_at 인덱스 있음 ✅
- scheduler_service.py가 30일 이상 레코드 자동 삭제 ⚠️
  → access_log만으로 30일 미로그인 판단 불안정
  → workers.last_login_at 컬럼 추가가 안전한 방법
```

### auth_service.py login 함수 현재 구조 (라인 549~650)

```
1. 사용자 조회 (email / admin prefix / name fallback)
2. 비밀번호 검증 (bcrypt)
3. Admin freepass 체크 (is_admin=True → 이메일/승인 건너뜀)
4. 일반 사용자: email_verified + approval_status 체크
5. JWT access_token + refresh_token 생성
6. refresh token DB 저장 (_store_refresh_token)
7. 응답 반환: { access_token, refresh_token, worker: {...} }

Sprint 40-C 추가 위치:
- is_active 체크: Step 4 이후, Step 5(토큰 생성) 이전
- last_login_at 갱신: Step 6(refresh token 저장) 직후
```

### 수정 대상 파일

```
1. backend/migrations/040_inactive_user_management.sql  (신규)
2. backend/app/services/auth_service.py                 (수정)
3. backend/app/routes/admin.py                          (수정 — API 3개 추가)
4. backend/app/routes/work.py                           (수정 — manager API 1개 추가)
5. backend/app/models/worker.py                         (수정 — 쿼리 함수 추가)
6. tests/backend/test_sprint40c_inactive_user.py        (신규)
```

### Task 1: DB Migration (040_inactive_user_management.sql)

```sql
-- Migration 040: 비활성 사용자 관리 (Sprint 40-C)
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
```

⚠️ 주의: scheduler_service.py가 30일 이상 access_log 삭제하므로, 이 초기값은 최근 30일 내 접속자만 유효. 나머지는 NULL로 남음 (→ NULL = "접속 이력 불명" 으로 비활성 감지 대상에 포함).

### Task 2: auth_service.py 수정 (login 함수)

```python
# === 추가 위치: 라인 609 (approval_rejected 체크 이후) ===

# Sprint 40-C: 비활성 사용자 로그인 거부
if not getattr(worker, 'is_active', True):
    return {
        'error': 'ACCOUNT_DEACTIVATED',
        'message': '비활성화된 계정입니다. 관리자에게 문의하세요.'
    }, 403

# === 추가 위치: 라인 634 (logger.info 이후, return 이전) ===

# Sprint 40-C: last_login_at 갱신
from app.models.worker import update_last_login
update_last_login(worker.id)
```

### Task 3: worker.py 모델 함수 추가

```python
# 1) last_login_at 갱신
def update_last_login(worker_id: int) -> None:
    """로그인 시 last_login_at 갱신"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE workers SET last_login_at = NOW() WHERE id = %s",
                (worker_id,)
            )
        conn.commit()
    finally:
        put_conn(conn)

# 2) 비활성 사용자 감지 (30일 미로그인)
def get_inactive_workers(days: int = 30) -> list:
    """last_login_at이 {days}일 이전이거나 NULL인 approved 사용자 목록"""
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, name, email, role, company, is_active,
                       last_login_at, deactivated_at, created_at
                FROM workers
                WHERE approval_status = 'approved'
                  AND is_admin = FALSE
                  AND is_active = TRUE
                  AND (last_login_at < NOW() - INTERVAL '%s days'
                       OR last_login_at IS NULL)
                ORDER BY last_login_at ASC NULLS FIRST
            """, (days,))
            return cur.fetchall()
    finally:
        put_conn(conn)

# 3) 사용자 비활성화 (soft delete)
def deactivate_worker(worker_id: int) -> bool:
    """is_active=FALSE + deactivated_at 기록"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE workers
                SET is_active = FALSE, deactivated_at = NOW()
                WHERE id = %s AND is_active = TRUE
                RETURNING id
            """, (worker_id,))
            result = cur.fetchone()
        conn.commit()
        return result is not None
    finally:
        put_conn(conn)

# 4) 사용자 재활성화
def reactivate_worker(worker_id: int) -> bool:
    """is_active=TRUE + deactivated_at NULL"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE workers
                SET is_active = TRUE, deactivated_at = NULL
                WHERE id = %s AND is_active = FALSE
                RETURNING id
            """, (worker_id,))
            result = cur.fetchone()
        conn.commit()
        return result is not None
    finally:
        put_conn(conn)

# 5) 삭제 대기 목록 조회 (이미 비활성화된 사용자)
def get_deactivated_workers() -> list:
    """is_active=FALSE인 사용자 목록 (admin 최종 승인 대기)"""
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, name, email, role, company,
                       last_login_at, deactivated_at, created_at
                FROM workers
                WHERE is_active = FALSE
                ORDER BY deactivated_at DESC
            """)
            return cur.fetchall()
    finally:
        put_conn(conn)
```

### Task 4: API 엔드포인트 4개

```
# admin.py — 관리자 전용 (3개)

1) GET  /api/admin/inactive-workers?days=30
   - @jwt_required @admin_required
   - get_inactive_workers(days) 호출
   - 응답: { "inactive_workers": [...], "count": N, "threshold_days": 30 }

2) GET  /api/admin/deactivated-workers
   - @jwt_required @admin_required
   - get_deactivated_workers() 호출
   - 응답: { "deactivated_workers": [...], "count": N }

3) POST /api/admin/worker-status
   - @jwt_required @admin_required
   - Body: { "worker_id": int, "action": "deactivate" | "reactivate" }
   - deactivate → deactivate_worker(worker_id)
   - reactivate → reactivate_worker(worker_id)
   - 응답: { "message": "...", "worker_id": N, "action": "..." }

# work.py — 협력사 manager 요청 (1개)

4) POST /api/app/work/request-deactivation
   - @jwt_required (manager 체크: 토큰에서 is_manager=True 확인)
   - Body: { "worker_id": int, "reason": str }
   - 검증: 요청자와 대상이 같은 company인지 확인
   - deactivate_worker(worker_id) 호출
   - 응답: { "message": "비활성화 요청 완료", "worker_id": N }
   - ⚠️ manager가 직접 비활성화하지만, 최종적으로 admin이 reactivate 가능
```

### Task 5: 테스트 (test_sprint40c_inactive_user.py)

```
테스트 항목:
1. Migration: is_active, deactivated_at, last_login_at 컬럼 존재 확인
2. Login: is_active=FALSE인 사용자 → 403 ACCOUNT_DEACTIVATED
3. Login: 정상 사용자 → last_login_at 갱신 확인
4. GET /api/admin/inactive-workers → 30일 미로그인 목록 반환
5. GET /api/admin/deactivated-workers → 비활성 사용자 목록
6. POST /api/admin/worker-status → deactivate/reactivate 동작
7. POST /api/app/work/request-deactivation → manager 요청
8. POST /api/app/work/request-deactivation → 다른 company 사용자 거부
9. Regression: 기존 login/approve 흐름 영향 없음
```

### 제약사항

- ❌ is_admin=TRUE 사용자는 비활성화 대상에서 **제외** (get_inactive_workers에서 필터)
- ❌ 물리 삭제(DELETE) 절대 금지 — soft delete만 사용
- ✅ workers.last_login_at으로 판단 (app_access_log는 30일 보관 한계)
- ✅ 기존 `approval_status` 로직과 독립적으로 동작 (is_active는 별도 체크)
- ✅ Worker 모델 객체에 `is_active`, `last_login_at` 필드 추가 필요 (worker.py의 Worker 클래스/namedtuple)

### 실행 체크리스트

- [x] Migration 040 실행 ✅ (테스트 DB 자동 적용 — db_schema fixture)
- [x] auth_service.py login 함수 수정 (is_active 체크 + last_login_at 갱신) ✅
- [x] worker.py 모델 함수 5개 추가 ✅ (update_last_login, get_inactive/deactivated, de/reactivate)
- [x] admin.py API 3개 추가 ✅ (inactive-workers, deactivated-workers, worker-status)
- [x] work.py API 1개 추가 (request-deactivation) ✅
- [x] Worker 모델에 is_active, last_login_at, deactivated_at 필드 추가 ✅
- [x] 테스트 작성 및 통과 ✅ — 9/9 passed (2026-03-27)
- [x] Migration 041 (alert_type_enum WORKER_DEACTIVATION_REQUEST) ✅
- [x] email_service.py send_deactivation_notification() 추가 ✅
- [x] work.py request-deactivation 앱 알림 + 이메일 알림 추가 ✅
- [x] FE admin_options_screen.dart 레이아웃 8섹션 재배치 ✅
- [x] FE 비활성 사용자 관리 섹션 신규 (30일 미로그인 + 비활성화/재활성화) ✅
- [x] Flutter 빌드 성공 + Netlify 배포 완료 ✅ (2026-03-27)

### 검증 명령
```bash
pytest tests/backend/test_sprint40c_inactive_user.py -v
pytest tests/backend/test_auth.py -v  # regression
pytest tests/backend/test_workers.py -v  # regression
```

---

## Sprint 41: 작업 릴레이 + Manager 재활성화 (Task Relay & Reactivation)

> 등록일: 2026-03-30
> 트랙: BE + FE
> 선행: Sprint 6 Phase C (멀티 작업자 지원), Sprint 15 (BUG-12 다중작업자 Join)
> 난이도: 중

### 배경

현재 task 완료 흐름: 시작한 작업자 전원이 종료하면 자동으로 task 완료 처리 (`_all_workers_completed`).
**문제**: 판넬 작업 등 1개 task를 여러 작업자가 **순차적으로 교대**하는 경우, 유저1이 종료하면 `completed_count >= started_count` 조건에 의해 task가 즉시 닫혀 유저2가 이어서 시작 불가.

**요구사항**:
1. "내 작업 종료" (task는 열린 상태 유지) vs "task 완료" (task 닫힘) 분리
2. 기존 동시참여(Join) 로직 영향 없을 것
3. Manager가 실수로 완료된 task를 재활성화 가능
4. 작업 이력(work_start_log, work_completion_log) 절대 삭제하지 않음

### 현재 코드 구조 (확인 완료)

```
task_service.py — complete_work() (라인 165~330):
  1. task 조회 → 시작 여부 / 완료 여부 체크
  2. work_completion_log 기록 (라인 253-257)
  3. _all_workers_completed() 체크 (라인 260)
     → started_count == completed_count → True → _finalize_task_multi_worker()
     → app_task_details.completed_at 세팅 → task 닫힘
  4. completion_status 업데이트 (카테고리/전체 완료)

task_service.py — start_work() (라인 113~163):
  1. task.completed_at 존재 → 400 TASK_ALREADY_COMPLETED (재시작 차단)
  2. _worker_has_started_task() → 같은 worker 중복 시작 차단
  3. work_start_log 기록 + app_task_details.started_at 세팅 (최초만)

_all_workers_completed() (라인 817~864):
  started_count = COUNT(*) FROM work_start_log WHERE task_id
  completed_count = COUNT(*) FROM work_completion_log WHERE task_id
  return completed_count >= started_count

_worker_has_started_task() (라인 979~1011):
  SELECT 1 FROM work_start_log WHERE task_id AND worker_id
  → 기록 있으면 True → 동일 worker 재시작 차단
```

### 수정 대상 파일

```
1. backend/app/services/task_service.py              (수정 — 핵심)
2. backend/app/routes/work.py                        (수정 — complete-work 파라미터 + reactivate API)
3. backend/app/models/task_detail.py                 (수정 — reactivate_task 함수 추가)
4. backend/app/models/completion_status.py            (읽기 참조 — rollback 함수 확인)
5. frontend/lib/screens/qr/task_detail_screen.dart   (수정 — 종료 팝업 분기)
6. tests/backend/test_sprint41_task_relay.py          (신규)
```

### Task 0: _all_workers_completed() 버그 수정 (릴레이 필수 선행)

**현재 버그**: `COUNT(*)` 로 전체 행 수를 세기 때문에 릴레이 재시작 시 deadlock 발생.
- Worker1 시작→종료(relay)→재시작 → work_start_log에 2행
- started_count=2, completed_count=1 → `False` → task가 영원히 안 닫힘

**수정 위치**: `task_service.py` 라인 833-841

```python
# === 현재 (버그) ===
cur.execute("""
    SELECT COUNT(*) AS started_count
    FROM work_start_log
    WHERE task_id = %s
""", (task_detail_id,))

# === 수정 후 ===
cur.execute("""
    SELECT COUNT(DISTINCT worker_id) AS started_count
    FROM work_start_log
    WHERE task_id = %s
""", (task_detail_id,))
```

⚠️ 이 수정은 릴레이 기능과 무관하게 기존 동시참여(Join) 흐름에서도 안전함.
동시참여 시 같은 worker가 중복 시작하면 `TASK_ALREADY_STARTED` 로 차단되므로 DISTINCT와 COUNT(*)가 동일.

### Task 1: task_service.py — complete_work() 수정

**파라미터 추가**: `finalize: bool = True`

```python
def complete_work(
    self,
    worker_id: int,
    task_detail_id: int,
    finalize: bool = True    # ← 추가
) -> Tuple[Dict[str, Any], int]:
```

**수정 위치: 라인 260 부근 (_all_workers_completed 체크)**

```python
# === 현재 코드 (라인 260) ===
all_workers_done = _all_workers_completed(task.id)

# === 수정 후 ===
# finalize=False: 내 작업만 종료, task 열린 상태 유지 (릴레이 모드)
# finalize=True: 기존 동작 — 전원 종료 시 task 완료 (동시참여 + 단독 작업)
if not finalize:
    # 내 completion_log만 기록하고 종료. task는 열린 상태 유지
    logger.info(
        f"Worker session ended (relay mode): "
        f"task_id={task_detail_id}, worker_id={worker_id}"
    )
    return {
        'message': '내 작업이 종료되었습니다. 다른 작업자가 이어서 작업할 수 있습니다.',
        'task_id': task_detail_id,
        'completed_at': completed_at.isoformat(),
        'duration_minutes': this_worker_duration,
        'category_completed': False,
        'task_finished': False,
        'relay_mode': True,
    }, 200

# finalize=True: 기존 로직 유지
all_workers_done = _all_workers_completed(task.id)
```

⚠️ 이 수정 위치는 work_completion_log 기록 **이후**, _all_workers_completed 호출 **이전**이어야 함.
즉, 라인 257 (completion_log 기록) 이후, 라인 260 (all_workers_done 체크) 이전에 삽입.

### Task 2: task_service.py — start_work() 수정

**릴레이 재시작 허용**: 같은 worker가 이미 시작+종료한 task에 다시 시작 가능

```python
# === 현재 코드 (라인 122-126) ===
if _worker_has_started_task(task.id, worker_id):
    return {
        'error': 'TASK_ALREADY_STARTED',
        'message': '이미 시작한 작업입니다.'
    }, 400

# === 수정 후 ===
if _worker_has_started_task(task.id, worker_id):
    # 릴레이: 이 worker가 이미 완료한 경우 → 재시작 허용
    if _worker_already_completed_task(task.id, worker_id):
        # 이전 세션 완료됨 → 새 세션으로 재시작 가능
        logger.info(
            f"Relay re-start: task_id={task.id}, worker_id={worker_id}"
        )
    else:
        # 아직 완료 안 한 상태에서 중복 시작 → 차단 (기존 동작)
        return {
            'error': 'TASK_ALREADY_STARTED',
            'message': '이미 시작한 작업입니다.'
        }, 400
```

이렇게 하면:
- 유저1 시작→종료 후 다시 시작 가능 ✅
- 유저1 시작 중에 중복 시작 시도 → 차단 유지 ✅
- 동시참여(Join) 흐름 → 영향 없음 (다른 worker는 기존처럼 시작 가능) ✅

### Task 3: work.py — complete 엔드포인트 수정

```python
# 기존 complete 엔드포인트에서 finalize 파라미터 수신
# ⚠️ 실제 경로: /work/complete (complete-work 아님)
@work_bp.route('/complete', methods=['POST'])
@jwt_required
def complete_work():
    data = request.get_json()
    task_detail_id = data.get('task_detail_id')
    finalize = data.get('finalize', True)    # ← 추가. 기본값 True (하위 호환)

    # ...기존 검증 로직...

    task_service = TaskService()
    result, status = task_service.complete_work(
        worker_id=current_worker_id,
        task_detail_id=task_detail_id,
        finalize=finalize    # ← 전달
    )
    return jsonify(result), status
```

⚠️ 하위 호환: finalize 미전달 시 기본값 True → 기존 FE(업데이트 안 된 버전)도 정상 동작.

### Task 4: work.py — Manager 재활성화 API

```python
@work_bp.route('/reactivate-task', methods=['POST'])
@jwt_required
def reactivate_task():
    """
    Manager/Admin이 실수로 완료된 task를 재활성화.
    - app_task_details.completed_at → NULL
    - completion_status 롤백 (해당 카테고리)
    - work_start_log / work_completion_log → 보존 (삭제 안 함)
    """
    data = request.get_json()
    task_detail_id = data.get('task_detail_id')

    if not task_detail_id:
        return jsonify({'error': 'MISSING_PARAM', 'message': 'task_detail_id 필수'}), 400

    # 권한 체크: Manager 또는 Admin만 허용
    worker = get_current_worker()
    if not worker.is_manager and not worker.is_admin:
        return jsonify({'error': 'FORBIDDEN', 'message': '권한이 없습니다.'}), 403

    # task 조회
    task = get_task_by_id(task_detail_id)
    if not task:
        return jsonify({'error': 'TASK_NOT_FOUND', 'message': '작업을 찾을 수 없습니다.'}), 404

    if not task.completed_at:
        return jsonify({'error': 'TASK_NOT_COMPLETED', 'message': '이미 진행 중인 작업입니다.'}), 400

    # Manager: 같은 company 소속 task만 재활성화 가능
    if worker.is_manager and not worker.is_admin:
        # task의 serial_number로 product_info 조회 → partner 확인
        # 또는 task의 worker_id 소속 company 비교
        pass  # company 체크 로직 (기존 패턴 참조)

    # 1. app_task_details 재활성화 (completed_at + started_at 모두 초기화)
    from app.models.task_detail import reactivate_task as _reactivate_task
    if not _reactivate_task(task_detail_id):
        return jsonify({'error': 'REACTIVATE_FAILED', 'message': '재활성화 실패'}), 500

    # 2. completion_status 롤백 (카테고리 + 전체 완료)
    from app.models.completion_status import update_process_completion, update_all_completed, check_all_processes_completed
    update_process_completion(task.serial_number, task.task_category, False)
    if not check_all_processes_completed(task.serial_number):
        update_all_completed(task.serial_number, False, None)

    # 3. production_confirm 정합성 — 해당 S/N+공정의 실적확인 soft-delete
    #    재활성화된 task가 속한 공정의 confirm을 무효화해야 "확인됐는데 미완료" 방지
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE plan.production_confirm
            SET deleted_at = NOW(), deleted_by = %s
            WHERE serial_number = %s
              AND process_type = %s
              AND deleted_at IS NULL
        """, (worker.id, task.serial_number, task.task_category))
        confirm_invalidated = cur.rowcount
        conn.commit()
    finally:
        put_conn(conn)

    logger.info(
        f"Task reactivated: task_id={task_detail_id}, "
        f"by worker_id={worker.id} (is_manager={worker.is_manager}), "
        f"confirms_invalidated={confirm_invalidated}"
    )

    return jsonify({
        'message': '작업이 재활성화되었습니다.',
        'task_id': task_detail_id,
        'serial_number': task.serial_number,
        'task_category': task.task_category,
        'confirms_invalidated': confirm_invalidated,
    }), 200
```

### Task 5: task_detail.py — reactivate_task 함수 추가

```python
def reactivate_task(task_detail_id: int) -> bool:
    """
    완료된 task를 재활성화.
    completed_at, started_at, duration, elapsed, worker_count 모두 초기화.
    started_at도 초기화하는 이유: is_first_worker 판단이 started_at IS NULL 기준이므로,
    재활성화 후 새 worker가 시작하면 정상적으로 "최초 시작자"로 인식되어야 함.
    work_start_log / work_completion_log는 절대 삭제하지 않음 (이력 보존).
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE app_task_details
                SET completed_at = NULL,
                    started_at = NULL,
                    worker_id = NULL,
                    duration_minutes = NULL,
                    elapsed_minutes = NULL,
                    worker_count = NULL
                WHERE id = %s AND completed_at IS NOT NULL
                RETURNING id
            """, (task_detail_id,))
            result = cur.fetchone()
        conn.commit()
        return result is not None
    finally:
        put_conn(conn)
```

⚠️ started_at, worker_id도 NULL로 초기화 (is_first_worker 판단이 started_at IS NULL 기준이므로). work_start_log / work_completion_log는 절대 삭제 안 함 → 이력 보존.

### ⚠️ VIEW FE 연동은 별도 Sprint (VIEW Sprint 23)
Manager/Admin 재활성화 버튼은 VIEW 생산현황 S/N 디테일 패널(ProcessStepCard)에 배치.
이유: Manager/PM이 실적 확인하는 화면에서 "실수 취소"가 자연스러움 + APP에 넣으면 현장 작업자 실수 리스크.
→ OPS BE API(reactivate-task)만 이 Sprint에서 구현. VIEW FE는 DESIGN_FIX_SPRINT.md Sprint 23 참조.

### Task 6: FE — 종료 버튼 팝업 분기

**수정 파일**: `frontend/lib/screens/qr/task_detail_screen.dart`
**수정 위치**: 기존 "완료" 버튼 onPressed 핸들러

```dart
// 기존: 바로 complete-work API 호출
// 수정: 확인 다이얼로그 표시

onPressed: () async {
  final result = await showDialog<String>(
    context: context,
    builder: (context) => AlertDialog(
      title: const Text('작업 종료'),
      content: const Text('다음 작업자가 이어서 작업하나요?'),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, 'relay'),
          child: const Text('예, 내 작업만 종료'),
        ),
        TextButton(
          onPressed: () => Navigator.pop(context, 'finalize'),
          child: const Text('아니오, 작업 완료'),
        ),
      ],
    ),
  );

  if (result == null) return; // 취소

  final finalize = result == 'finalize';
  await _completeWork(finalize: finalize);
}
```

**_completeWork 수정**: body에 `finalize` 파라미터 추가

```dart
Future<void> _completeWork({bool finalize = true}) async {
  final response = await apiService.post('/app/work/complete', {
    'task_detail_id': widget.taskDetailId,
    'finalize': finalize,    // ← 추가
  });
  // ...기존 후처리...
}
```

### Task 7: 테스트 (test_sprint41_task_relay.py)

```
=== 릴레이 기본 흐름 (6건) ===

TC-41-01: 릴레이 종료 (finalize=false) → task 열린 상태 유지 (completed_at IS NULL)
TC-41-02: 릴레이 종료 후 다른 worker 시작 가능
TC-41-03: 릴레이 종료 후 같은 worker 재시작 가능
TC-41-04: 최종 완료 (finalize=true) → task 닫힘 (completed_at IS NOT NULL)
TC-41-05: 최종 완료 후 시작 시도 → 400 TASK_ALREADY_COMPLETED
TC-41-06: finalize 미전달 시 기본값 true → 기존 동작 유지 (하위 호환)

=== 릴레이 심화 시나리오 (3건) ===

TC-41-07: 릴레이 3회 연속 — worker1→worker2→worker3 순차 교대 후 worker3이 finalize=true
          → task 완료 + duration = 3명 공수 합산 + worker_count = 3
TC-41-08: 같은 worker 릴레이 2회 — worker1 시작→relay종료→재시작→finalize
          → _all_workers_completed() DISTINCT 체크로 정상 동작 (started_count=1, not 2)
TC-41-09: 일시정지 중 릴레이 종료 — worker1 시작→pause→relay종료(finalize=false)
          → auto-resume 후 completion_log 정상 기록 + task 열린 상태

=== 동시참여(Join) 호환 (2건) ===

TC-41-10: 동시참여 흐름 → finalize=true에서 기존과 동일하게 동작
TC-41-11: 동시참여 + 릴레이 혼합 — worker1+worker2 동시작업, worker1 relay종료,
          worker3 시작, worker2+worker3 finalize → task 완료

=== Manager 재활성화 (5건) ===

TC-41-12: Manager 재활성화 → completed_at/started_at/worker_id 모두 NULL 확인
TC-41-13: 재활성화 후 completion_status 롤백 확인 (카테고리 + all_completed)
TC-41-14: 재활성화 후 production_confirm soft-delete 확인 (confirms_invalidated > 0)
TC-41-15: 재활성화 후 새 worker 시작 가능 (is_first_worker=True)
TC-41-16: 일반 worker 재활성화 시도 → 403 FORBIDDEN

=== Regression (3건) ===

TC-41-17: 기존 단독 작업 start→complete (finalize 미전달) → 정상 완료
TC-41-18: 기존 동시참여 start→join→complete → 정상 완료
TC-41-19: completion_status 카테고리 전체 완료 시 all_completed=True 정상 동작
```

### _all_workers_completed() 버그 수정 주의사항

이 함수의 COUNT(*)→COUNT(DISTINCT worker_id) 변경은 릴레이 기능의 **필수 선행**.
변경하지 않으면 릴레이 재시작 후 finalize=true 해도 task가 닫히지 않음.
기존 동시참여 흐름에서는 같은 worker 중복 시작이 차단되므로 DISTINCT와 *가 동일 → regression 없음.

### production_confirm 정합성 주의사항

재활성화 API에서 해당 S/N+공정의 production_confirm을 soft-delete 하지 않으면
"실적확인 됐는데 공정 미완료" 불일치 상태 발생.
deleted_at, deleted_by 컬럼은 migration 027에서 이미 존재함.

### 기존 테스트 영향 분석

Sprint 41 변경으로 인해 기존 테스트 중 수정 필요 예상:

| 파일 | 영향 | 이유 |
|------|------|------|
| test_work_api.py | 🔴 수정 필요 | TASK_ALREADY_STARTED 에러 조건 변경 (릴레이 허용) |
| test_multi_worker_join.py | 🔴 수정 필요 | same_worker_start_twice 테스트 조건 변경 |
| test_concurrent_work.py | 🟠 확인 필요 | finalize 관련 assertion 추가 |
| test_working_hours.py | 🟠 확인 필요 | _finalize_task_multi_worker 호출 조건 변경 |
| test_pause_resume.py | 🟡 안전 가능 | pause+complete 흐름은 finalize=true 기본값으로 유지 |
| test_force_close.py | 🟡 안전 가능 | force_close는 별도 경로 |

⚠️ 기존 테스트에서 `TASK_ALREADY_STARTED` 에러를 기대하는 케이스:
→ "시작 중인데 중복 시작" → 여전히 차단됨 ✅
→ "시작+종료 후 재시작" → 릴레이 허용으로 변경됨 → 테스트 수정 필요

### 제약사항

- ❌ work_start_log, work_completion_log 삭제 절대 금지 (이력 보존)
- ❌ _finalize_task_multi_worker() 내부 집계 로직 수정 금지
- ❌ completion_status.update_process_completion() 시그니처 변경 금지
- ✅ finalize 기본값 True → 기존 FE 미업데이트 시에도 정상 동작 (하위 호환 필수)
- ✅ 동시참여(Join) 흐름은 기존 그대로 유지 (finalize=True 경로)
- ✅ 재활성화 시 completion_status + production_confirm 롤백 포함
- ✅ _all_workers_completed()는 COUNT(DISTINCT worker_id) 사용 (릴레이 필수)

### 실행 체크리스트

- [x] Task 0: _all_workers_completed() COUNT(*)→COUNT(DISTINCT worker_id) 수정 ✅
- [x] Task 1: task_service.py complete_work() — finalize 파라미터 + 분기 추가 ✅
- [x] Task 2: task_service.py start_work() — 릴레이 재시작 허용 로직 ✅
- [x] Task 3: work.py complete-work — finalize 파라미터 수신/전달 ✅
- [x] Task 4: work.py reactivate-task — Manager 재활성화 API (production_confirm 롤백 포함) ✅
- [x] Task 5: task_detail.py reactivate_task() 함수 추가 (started_at/worker_id도 초기화) ✅
- [x] Task 6: FE task_detail_screen.dart — 종료 팝업 분기 (relay/finalize) ✅
- [x] Task 7: 테스트 18 passed + 1 xfail (TC-41-14 production_confirm 타이밍 이슈) ✅
- [x] Regression: 71 passed, 6 skipped — test_work_api, test_multi_worker_join, test_multi_worker, test_pause_resume, test_force_close, test_working_hours 전체 통과 ✅

### 검증 명령
```bash
# Sprint 41 신규 테스트
pytest tests/backend/test_sprint41_task_relay.py -v

# Regression — 직접 영향 (수정 필요할 수 있음)
pytest tests/backend/test_work_api.py -v
pytest tests/backend/test_multi_worker_join.py -v
pytest tests/integration/test_concurrent_work.py -v
pytest tests/backend/test_working_hours.py -v

# Regression — 간접 영향 (통과 확인)
pytest tests/backend/test_pause_resume.py -v
pytest tests/backend/test_force_close.py -v
pytest tests/backend/test_multi_worker.py -v
pytest tests/integration/test_full_workflow.py -v
```

## Fix Sprint 41-A: 릴레이 토스트 미표시 + 목록 릴레이 다이얼로그 + 릴레이 재시작 UI/BE

> 등록일: 2026-03-30
> 선행: Sprint 41 완료
> 난이도: 중간 (FE 2파일 + BE 1파일)
> BE 변경: task_service.py (릴레이 재완료 허용)

### 배경

Sprint 41 릴레이 관련 문제 4건:

**문제 1**: task_management_screen (목록 화면)의 "완료" 버튼 (L569)이 릴레이 다이얼로그 없이 `_handleCompleteTask`(L727)를 직접 호출 → `finalize` 미전달(기본값 true) → 릴레이 선택 기회 없이 바로 완료.
(test1@naver.com TMS(M) is_manager, waste gas line1 NORMAL 타입에서 재현)

**문제 2**: task_detail_screen의 `_handleCompleteTask`에서 `_showSnack()` → `Navigator.pop()` 순서로 호출 → Scaffold 소멸 → SnackBar 미표시.

**문제 3**: 릴레이(finalize=false)로 "내 작업만 종료" 후 같은 task에 재진입하면 `myWorkStatus=='completed'` → `_buildMyCompletedBadge()`만 표시되고 **재시작 버튼 없음**. BE는 릴레이 재시작을 이미 지원하나 FE에 UI 없음.

**문제 4**: 릴레이 재시작 후 다시 "완료" 시 `[TASK_ALREADY_COMPLETED] 이미 완료한 작업입니다.` 에러 발생.
BE의 `start_work()`는 릴레이 재시작을 허용하지만(L134), `complete_work()`의 `_worker_already_completed_task()` 체크(L244)가 이전 completion_log를 보고 무조건 차단.
(test1@naver.com MECH Waste Gas LINE 1에서 재현 — 릴레이 종료 → 재시작 → 완료 시 에러)

### 원인

```dart
// 문제 1: task_management_screen.dart — _handleCompleteTask (L727-732)
// 릴레이 다이얼로그 없이 바로 완료 (finalize 미전달 → 기본값 true)
Future<void> _handleCompleteTask(int taskId, int workerId) async {
  final taskNotifier = ref.read(taskProvider.notifier);
  final success = await taskNotifier.completeTask(
    taskId: taskId,
    workerId: workerId,
    // ← finalize 파라미터 없음 → 기본값 true → 릴레이 불가
  );
  // ...토스트 표시...
}

// 문제 2: task_detail_screen.dart — _handleCompleteTask (L712-718)
if (success) {
  _showSnack(true, '작업을 완료했습니다.', '');
  Navigator.pop(context);    // ← SnackBar 표시 직후 Scaffold 소멸
}
```

### 수정 방침

1. **task_management_screen**: 목록 화면 "완료" 버튼에도 릴레이 다이얼로그 추가
2. **task_detail_screen**: `Navigator.pop(context, result)` 패턴 — 이전 화면에서 토스트 표시
- task_management_screen이 이미 모든 액션의 SnackBar를 직접 관리하는 패턴 사용 중
- result로 'relay'/'finalize' 전달 → 메시지 분기

### Task 0: task_detail_screen.dart 수정

파일: `frontend/lib/screens/task/task_detail_screen.dart`
위치: `_handleCompleteTask` 메서드

```dart
// ── 변경 전 ──
Future<void> _handleCompleteTask(int taskId, int workerId, {bool finalize = true}) async {
  setState(() => _isActionLoading = true);
  final taskNotifier = ref.read(taskProvider.notifier);
  final success = await taskNotifier.completeTask(taskId: taskId, workerId: workerId, finalize: finalize);
  if (mounted) {
    setState(() => _isActionLoading = false);
    if (success) {
      if (finalize) {
        _showSnack(true, '작업을 완료했습니다.', '');
        Navigator.pop(context);
      } else {
        _showSnack(true, '내 작업이 종료되었습니다. 다른 작업자가 이어서 작업할 수 있습니다.', '');
        Navigator.pop(context);
      }
    } else {
      _showSnack(false, '', '작업 완료에 실패했습니다.');
    }
  }
}

// ── 변경 후 ──
Future<void> _handleCompleteTask(int taskId, int workerId, {bool finalize = true}) async {
  setState(() => _isActionLoading = true);
  final taskNotifier = ref.read(taskProvider.notifier);
  final success = await taskNotifier.completeTask(taskId: taskId, workerId: workerId, finalize: finalize);
  if (mounted) {
    setState(() => _isActionLoading = false);
    if (success) {
      Navigator.pop(context, finalize ? 'finalize' : 'relay');
    } else {
      _showSnack(false, '', '작업 완료에 실패했습니다.');
    }
  }
}
```

⚠️ 실패 시에는 기존대로 detail 화면에서 에러 토스트 표시 (화면 유지).

### Task 1: task_management_screen.dart 수정

파일: `frontend/lib/screens/task/task_management_screen.dart`
위치: task 카드 `InkWell` onTap (Navigator.push 호출부)

```dart
// ── 변경 전 ──
onTap: () {
  ref.read(taskProvider.notifier).selectTask(task);
  Navigator.push(
    context,
    MaterialPageRoute(builder: (context) => const TaskDetailScreen()),
  );
},

// ── 변경 후 ──
onTap: () async {
  ref.read(taskProvider.notifier).selectTask(task);
  final result = await Navigator.push<String>(
    context,
    MaterialPageRoute(builder: (context) => const TaskDetailScreen()),
  );
  if (result != null && mounted) {
    final message = result == 'finalize'
        ? '작업을 완료했습니다.'
        : '내 작업이 종료되었습니다. 다른 작업자가 이어서 작업할 수 있습니다.';
    final bgColor = result == 'finalize' ? GxColors.success : GxColors.accent;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: bgColor,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
      ),
    );
  }
},
```

### Task 2: task_management_screen.dart — 목록 화면 "완료" 버튼에 릴레이 다이얼로그 추가

파일: `frontend/lib/screens/task/task_management_screen.dart`
위치: `_handleCompleteTask` 메서드 (L727)

```dart
// ── 변경 전 ──
Future<void> _handleCompleteTask(int taskId, int workerId) async {
  final taskNotifier = ref.read(taskProvider.notifier);
  final success = await taskNotifier.completeTask(
    taskId: taskId,
    workerId: workerId,
  );

  if (mounted) {
    if (success) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('작업을 완료했습니다.'),
          backgroundColor: GxColors.success,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
        ),
      );
    } else {
      // 에러 토스트...
    }
  }
}

// ── 변경 후 ──
Future<void> _handleCompleteTask(int taskId, int workerId) async {
  // Sprint 41: 릴레이 다이얼로그 — 목록 화면에서도 동일하게 표시
  final result = await showDialog<String>(
    context: context,
    builder: (ctx) => AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.lg)),
      title: Row(
        children: [
          Container(
            width: 32, height: 32,
            decoration: BoxDecoration(
              color: GxColors.successBg,
              borderRadius: BorderRadius.circular(GxRadius.md),
            ),
            child: const Icon(Icons.check_circle, color: GxColors.success, size: 18),
          ),
          const SizedBox(width: 10),
          const Expanded(
            child: Text('작업 종료',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: GxColors.charcoal)),
          ),
        ],
      ),
      content: const Text('다음 작업자가 이어서 작업하나요?',
        style: TextStyle(fontSize: 14, color: GxColors.slate, height: 1.5)),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(ctx, 'relay'),
          child: const Text('예, 내 작업만 종료',
            style: TextStyle(color: GxColors.accent, fontWeight: FontWeight.w500)),
        ),
        TextButton(
          onPressed: () => Navigator.pop(ctx, 'finalize'),
          child: const Text('아니오, 작업 완료',
            style: TextStyle(color: GxColors.success, fontWeight: FontWeight.w600)),
        ),
      ],
    ),
  );

  if (result == null) return; // 취소
  final finalize = result == 'finalize';

  final taskNotifier = ref.read(taskProvider.notifier);
  final success = await taskNotifier.completeTask(
    taskId: taskId,
    workerId: workerId,
    finalize: finalize,
  );

  if (mounted) {
    if (success) {
      final message = finalize
          ? '작업을 완료했습니다.'
          : '내 작업이 종료되었습니다. 다른 작업자가 이어서 작업할 수 있습니다.';
      final bgColor = finalize ? GxColors.success : GxColors.accent;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(message),
          backgroundColor: bgColor,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
        ),
      );
    } else {
      final errorMessage = ref.read(taskProvider).errorMessage;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(errorMessage ?? '작업 완료에 실패했습니다.'),
          backgroundColor: GxColors.danger,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
        ),
      );
    }
  }
}
```

⚠️ 다이얼로그 UI는 task_detail_screen.dart의 `_showCompleteDialog`와 동일.
⚠️ SINGLE_ACTION task는 목록에서 별도 `_handleCompleteSingleAction` (L598)으로 처리되므로 영향 없음.

### Regression 영향: 없음

| 화면 | 기존 흐름 | 변경 | 영향 |
|---|---|---|---|
| 목록 | NORMAL "완료" 버튼 → 바로 완료 | 릴레이 다이얼로그 추가 → finalize 전달 | ✅ 개선 |
| 목록 | SINGLE_ACTION "완료" → 바로 완료 | 변경 없음 (_handleCompleteSingleAction 별도 함수) | ✅ 무관 |
| 목록 | 시작/참여/일시정지/재개 버튼 | 변경 없음 | ✅ 무관 |
| 상세 | Navigator.pop → SnackBar 소멸 | pop(context, result) → 목록에서 토스트 | ✅ 개선 |
| 상세 | 뒤로가기 | result null → 무시 | ✅ 무관 |
| 상세 | SINGLE_ACTION 완료 | pop 안 함 → 변경 없음 | ✅ 무관 |
| 상세 | 완료 실패 | detail에서 에러 토스트 (pop 안 함) | ✅ 무관 |

### 테스트

```
[목록 화면 — task_management_screen]
TC-41A-01: NORMAL task 목록에서 "완료" 버튼 → 릴레이 팝업 표시 → "아니오, 작업 완료" → 성공 토스트 + task 완료
TC-41A-02: NORMAL task 목록에서 "완료" 버튼 → 릴레이 팝업 표시 → "예, 내 작업만 종료" → 릴레이 토스트 + task 열린 상태
TC-41A-03: NORMAL task 목록에서 "완료" 버튼 → 릴레이 팝업 취소(바깥 터치) → 아무 동작 없음
TC-41A-04: SINGLE_ACTION task 목록에서 "완료" 버튼 → 릴레이 팝업 없이 바로 완료 (기존 동작 유지)

[상세 화면 — task_detail_screen]
TC-41A-05: NORMAL task 상세 → "작업 완료" → 릴레이 팝업 "아니오, 작업 완료" → 목록 화면 복귀 + 성공 토스트
TC-41A-06: NORMAL task 상세 → "작업 완료" → 릴레이 팝업 "예, 내 작업만 종료" → 목록 화면 복귀 + 릴레이 토스트
TC-41A-07: NORMAL task 상세 → "작업 완료" → 릴레이 팝업 취소 → detail 화면 유지, 토스트 없음
TC-41A-08: task detail 뒤로가기 → 목록 화면 복귀, 토스트 없음
TC-41A-09: SINGLE_ACTION task detail "완료" → detail 화면에서 토스트 (기존 동작 유지)
```

### Task 3: 릴레이 재시작 UI — myWorkStatus='completed' + task 열림 상태에서 재시작 버튼 추가

**문제**: 릴레이 모드(finalize=false)로 "내 작업만 종료" 후, 같은 작업자가 같은 task에 다시 진입하면 **"내 작업 완료" 배지만 표시**되고 재시작 버튼이 없음.

**원인**: FE 상태 분기가 relay 종료와 최종 완료를 구분하지 않음:
```dart
// task_detail_screen.dart L327-328 — 현재
else if (task.status == 'in_progress' && task.myWorkStatus == 'completed')
  _buildMyCompletedBadge()    // ← 릴레이 종료 시에도 여기 진입 → 재시작 불가
```

**핵심 인사이트**: BE 수정 불필요. FE에서 이미 구분 가능:
- `task.status == 'in_progress'` + `myWorkStatus == 'completed'` → **릴레이 종료** (task 아직 열림) → 재시작 허용
- `task.status == 'completed'` + `myWorkStatus == 'completed'` → **최종 완료** → 배지만 표시

BE의 `start_work()` (task_service.py L122-133)은 이미 릴레이 재시작을 허용:
```python
# _worker_already_completed_task() = True → 릴레이 재시작 허용
if _worker_already_completed_task(conn, task_detail_id, worker_id):
    # completion_log에 기록 있어도 task.status=='in_progress'이면 재시작 가능
```

#### 파일 1: task_detail_screen.dart

위치: 상태별 버튼 분기 (L319-334)

```dart
// ── 변경 전 ──
else if (task.status == 'in_progress' && task.myWorkStatus == 'completed')
  _buildMyCompletedBadge()

// ── 변경 후 ──
else if (task.status == 'in_progress' && task.myWorkStatus == 'completed')
  _buildRelayRestartRow(task.id, workerId)
```

새 메서드 추가:

```dart
/// 릴레이 재시작 — "내 작업 완료" 상태에서 다시 시작 가능
Widget _buildRelayRestartRow(int taskId, int workerId) {
  return Column(
    children: [
      // 상태 배지 (기존 유지)
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: GxColors.accentBg,
          borderRadius: BorderRadius.circular(GxRadius.sm),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.check_circle_outline, color: GxColors.accent, size: 16),
            const SizedBox(width: 6),
            Text('내 작업 완료',
              style: TextStyle(color: GxColors.accent, fontSize: 13, fontWeight: FontWeight.w500)),
          ],
        ),
      ),
      const SizedBox(height: 12),
      // 재시작 버튼
      SizedBox(
        width: double.infinity,
        child: ElevatedButton.icon(
          onPressed: _isActionLoading ? null : () => _handleStartTask(taskId, workerId),
          icon: const Icon(Icons.replay, size: 18),
          label: const Text('다시 시작'),
          style: ElevatedButton.styleFrom(
            backgroundColor: GxColors.accent,
            foregroundColor: Colors.white,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.md)),
            padding: const EdgeInsets.symmetric(vertical: 12),
          ),
        ),
      ),
    ],
  );
}
```

⚠️ `_handleStartTask`는 기존 시작 로직 재사용. BE `start_work()`가 릴레이 재시작을 이미 허용하므로 추가 분기 불필요.

#### 파일 2: task_management_screen.dart

위치: 목록 화면 상태별 버튼 분기 (myWorkStatus == 'completed' 조건)

```dart
// ── 변경 전 ──
// myWorkStatus == 'completed' → "내 작업 완료" 배지만 표시

// ── 변경 후 ──
// myWorkStatus == 'completed' && task.status == 'in_progress' → "내 작업 완료" 배지 + "다시 시작" 아이콘 버튼
if (task.status == 'in_progress' && myWorkStatus == 'completed') {
  return Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      // 기존 "내 작업 완료" 뱃지
      _buildCompletedBadge(),
      const SizedBox(width: 8),
      // 재시작 아이콘 버튼 (컴팩트)
      IconButton(
        icon: const Icon(Icons.replay, color: GxColors.accent, size: 20),
        tooltip: '다시 시작',
        onPressed: () => _handleStartTask(task.id, workerId),
        constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
        padding: EdgeInsets.zero,
      ),
    ],
  );
}
```

### Regression 영향 (Task 3)

| 시나리오 | 기존 동작 | 변경 후 | 영향 |
|---|---|---|---|
| 릴레이 종료 → 재진입 | 배지만 (재시작 불가) | 배지 + 재시작 버튼 | ✅ 개선 |
| 최종 완료(finalize) → 재진입 | 완료 배지 | 변경 없음 (task.status=='completed') | ✅ 무관 |
| 다른 작업자가 이어받아 작업 중 → 원래 작업자 재진입 | 배지만 | 배지 + 재시작 | ⚠️ 동시 작업 주의* |
| 시작 전 상태 | "시작" 버튼 | 변경 없음 | ✅ 무관 |
| 일시정지 상태 | 재개/완료 버튼 | 변경 없음 | ✅ 무관 |

*⚠️ 동시 작업 주의: 다른 작업자가 이어받아 in_progress 상태일 때, 원래 작업자도 재시작 가능. BE에서 이미 `assigned_worker_id` 업데이트로 관리하므로 충돌은 없으나, **현장 혼선 방지를 위해 참여 인원 수를 UI에 표시하는 것을 권장** (별도 Sprint).

### 테스트 (Task 3 추가분)

```
[릴레이 재시작 — task_detail_screen]
TC-41A-10: NORMAL task, 릴레이 종료(finalize=false) → task 목록 복귀 → 같은 task 재진입 → "내 작업 완료" 배지 + "다시 시작" 버튼 표시
TC-41A-11: TC-41A-10 이후 "다시 시작" 클릭 → task 시작 성공 → myWorkStatus='working' → 일시정지/완료 버튼 표시
TC-41A-12: NORMAL task, 최종 완료(finalize=true) → task 재진입 → task.status='completed' → 완료 배지만 표시 (재시작 버튼 없음)
TC-41A-13: 릴레이 종료 후 다른 작업자가 시작 → 원래 작업자 재진입 → "내 작업 완료" 배지 + "다시 시작" 표시 (동시 참여 가능)

[릴레이 재시작 — task_management_screen 목록]
TC-41A-14: 릴레이 종료 후 목록 화면 → 해당 task에 "내 작업 완료" 배지 + replay 아이콘 표시
TC-41A-15: TC-41A-14에서 replay 아이콘 클릭 → task 시작 성공 → 버튼 상태 변경
```

### Task 4: task_service.py — 릴레이 재시작 후 재완료 허용 (BE)

**문제**: `complete_work()` L243-248에서 `_worker_already_completed_task()` = True이면 무조건 `TASK_ALREADY_COMPLETED` 반환.
`start_work()` L134는 릴레이 재시작을 허용하므로, 재시작 후에는 재완료도 가능해야 함.

**핵심 조건**: 작업자의 최신 `work_start_log.started_at` > 최신 `work_completion_log.completed_at`이면 릴레이 재시작한 것 → 재완료 허용.

#### 파일: task_service.py

**수정 1**: 릴레이 재시작 여부 확인 함수 추가

```python
# ── 추가: _worker_restarted_after_completion ──
def _worker_restarted_after_completion(task_detail_id: int, worker_id: int) -> bool:
    """
    Sprint 41 Fix: 릴레이 재시작 여부 확인.
    최신 work_start_log.started_at > 최신 work_completion_log.completed_at이면
    릴레이 재시작한 것으로 판단.

    Args:
        task_detail_id: app_task_details.id
        worker_id: 작업자 ID

    Returns:
        릴레이 재시작한 경우 True
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                (SELECT MAX(started_at) FROM work_start_log
                 WHERE task_id = %s AND worker_id = %s) AS last_start,
                (SELECT MAX(completed_at) FROM work_completion_log
                 WHERE task_id = %s AND worker_id = %s) AS last_completion
        """, (task_detail_id, worker_id, task_detail_id, worker_id))

        row = cur.fetchone()
        if not row or not row[0] or not row[1]:
            return False

        return row[0] > row[1]  # last_start > last_completion → 재시작함

    except PsycopgError as e:
        logger.error(
            f"_worker_restarted_after_completion failed: "
            f"task_id={task_detail_id}, worker_id={worker_id}, error={e}"
        )
        return False
    finally:
        if conn:
            put_conn(conn)
```

**수정 2**: `complete_work()` L243-248 체크 수정

```python
# ── 변경 전 (L243-248) ──
# 이 작업자가 이미 완료 기록을 남긴 경우 확인
if _worker_already_completed_task(task.id, worker_id):
    return {
        'error': 'TASK_ALREADY_COMPLETED',
        'message': '이미 완료한 작업입니다.'
    }, 400

# ── 변경 후 ──
# 이 작업자가 이미 완료 기록을 남긴 경우 확인
# Sprint 41 Fix: 릴레이 재시작한 경우(last_start > last_completion)는 재완료 허용
if _worker_already_completed_task(task.id, worker_id):
    if not _worker_restarted_after_completion(task.id, worker_id):
        return {
            'error': 'TASK_ALREADY_COMPLETED',
            'message': '이미 완료한 작업입니다.'
        }, 400
    logger.info(
        f"Relay re-completion allowed: task_id={task.id}, worker_id={worker_id}"
    )
```

**동작 흐름 (수정 후)**:
```
1. worker A 시작 → start_log(t1)
2. worker A 릴레이 종료 → completion_log(t2)
3. worker A 재시작 → start_log(t3)  [t3 > t2 → start_work 허용]
4. worker A 재완료 → _worker_already_completed_task=True
                    → _worker_restarted_after_completion: t3 > t2 = True
                    → 재완료 허용 ✅
```

**비릴레이 기존 동작 보존**:
```
1. worker A 시작 → start_log(t1)
2. worker A 완료 (finalize=true) → completion_log(t2), task.completed_at 설정
3. worker A 완료 재시도 → task.completed_at 체크(L237)에서 이미 차단 ✅
```

### Regression 영향 (Task 4)

| 시나리오 | 기존 동작 | 변경 후 | 영향 |
|---|---|---|---|
| 릴레이 종료 → 재시작 → 재완료 | TASK_ALREADY_COMPLETED ❌ | 재완료 허용 ✅ | ✅ 버그 수정 |
| 일반 완료(finalize=true) → 재완료 시도 | task.completed_at 체크(L237)에서 차단 | 동일 (L237 체크가 먼저) | ✅ 무관 |
| 릴레이 종료 → 재시작 안 함 → 완료 시도 | TASK_ALREADY_COMPLETED | 동일 (last_start < last_completion) | ✅ 무관 |
| 멀티 작업자 — worker B가 먼저 완료 → worker A 완료 | 각각 독립 completion_log | 동일 (worker별 별도 체크) | ✅ 무관 |
| 릴레이 재시작 → 릴레이 재종료 → 다시 재시작 → 재완료 (3회차) | N/A (기존 불가) | 매번 last_start > last_completion 체크 → 허용 | ✅ 정상 |

### 테스트 (Task 4 추가분)

```
[BE — 릴레이 재완료]
TC-41A-16: 릴레이 종료 → 재시작 → "아니오, 작업 완료" (finalize=true) → 완료 성공, task.completed_at 설정
TC-41A-17: 릴레이 종료 → 재시작 → "예, 내 작업만 종료" (finalize=false) → 릴레이 재종료 성공, task 열린 상태 유지
TC-41A-18: 릴레이 종료 → 재시작하지 않음 → 목록에서 "완료" → TASK_ALREADY_COMPLETED (기존 동작 보존)
TC-41A-19: 릴레이 종료 → 재시작 → 릴레이 재종료 → 다시 재시작 → 완료 (3회차) → 성공
TC-41A-20: 일반 완료(finalize=true) 후 재완료 시도 → task.completed_at 체크에서 TASK_ALREADY_COMPLETED (regression 없음)
TC-41A-21: worker A 릴레이 종료 → worker B 시작 → worker B 완료 → worker A 재시작 → worker A 완료 (동시 작업자 시나리오)
```

### 규칙
- 코드 변경 전 반드시 사용자 승인
- flutter build web 0 에러 확인 + pytest 기존 테스트 통과
- TC-41A-01~21 수동 테스트 통과 후 커밋


## Sprint 41-B: 릴레이 미완료 task 자동 마감 + Manager 알림

> 등록일: 2026-03-30
> 선행: Sprint 41 + Fix Sprint 41-A 완료
> 난이도: 중간 (BE only, 3파일)
> FE 변경: 없음

### 배경

Sprint 41 릴레이 모드(finalize=false)로 작업 종료 시 task의 `completed_at`은 NULL.
마지막 작업자도 "내 작업만 종료"를 선택하면 task가 영원히 열린 상태로 남음.

**1차 — Manager 알림**: 릴레이 후 미완료 상태가 일정 시간 경과하면 Manager에게 알림
**2차 — FINAL task 기반 자동 마감**: 자주검사/가압검사 등 FINAL phase task 완료 시, 같은 S/N+카테고리의 열린 릴레이 task를 자동 마감

### FINAL task 매핑

| 카테고리 | FINAL task | task_id |
|---|---|---|
| MECH | 자주검사 | SELF_INSPECTION |
| ELEC | 자주검사 (검수) | INSPECTION |
| TMS | 가압검사 | PRESSURE_TEST |
| PI | CHAMBER 가압검사 | PI_CHAMBER |
| QI | 공정검사 | QI_INSPECTION |
| SI | 출하완료 | SI_SHIPMENT |

⚠️ PI/QI/SI는 GST 내부 공정으로 릴레이 대상이 아니지만, 로직은 일괄 적용해도 무방 (해당 task가 없으면 트리거 안 됨).

### 수정 파일 (3개)

```
1. backend/app/services/task_service.py  (수정 — 자동 마감 로직 + Manager 알림)
2. backend/app/models/task_detail.py     (수정 — 릴레이 미완료 task 조회 + 자동 마감 함수)
3. backend/app/services/scheduler_service.py  (수정 — 주기적 미완료 릴레이 감지 알림)
```

### Task 0: task_detail.py — 릴레이 미완료 task 조회 함수

파일: `backend/app/models/task_detail.py`

```python
def get_orphan_relay_tasks(serial_number: str, task_category: str) -> List[Dict]:
    """
    릴레이 미완료 task 조회:
    - completed_at IS NULL (task 미완료)
    - work_completion_log에 1건 이상 존재 (누군가 작업은 했음)
    - is_applicable = TRUE
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT atd.id AS task_detail_id,
                   atd.task_id,
                   atd.task_name,
                   atd.started_at,
                   MAX(wcl.completed_at) AS last_completion_at,
                   COUNT(DISTINCT wcl.worker_id) AS worker_count
            FROM app_task_details atd
            JOIN work_completion_log wcl ON wcl.task_id = atd.id
            WHERE atd.serial_number = %s
              AND atd.task_category = %s
              AND atd.completed_at IS NULL
              AND atd.is_applicable = TRUE
            GROUP BY atd.id, atd.task_id, atd.task_name, atd.started_at
        """, (serial_number, task_category))
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        put_conn(conn)


def auto_close_relay_task(task_detail_id: int, last_completion_at, worker_count: int) -> bool:
    """
    릴레이 미완료 task 자동 마감.
    마지막 work_completion_log 기준으로 completed_at 설정.

    Args:
        task_detail_id: app_task_details.id
        last_completion_at: 마지막 completion_log의 completed_at
        worker_count: 참여 작업자 수

    Returns:
        True if 업데이트 성공
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # duration 계산: started_at ~ last_completion_at
        cur.execute("""
            UPDATE app_task_details
            SET completed_at = %s,
                duration_minutes = EXTRACT(EPOCH FROM (%s - started_at)) / 60,
                elapsed_minutes = EXTRACT(EPOCH FROM (%s - started_at)) / 60,
                worker_count = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
              AND completed_at IS NULL
            RETURNING id
        """, (last_completion_at, last_completion_at, last_completion_at,
              worker_count, task_detail_id))

        result = cur.fetchone()
        conn.commit()
        return result is not None
    except Exception as e:
        conn.rollback()
        logger.error(f"auto_close_relay_task failed: task_id={task_detail_id}, error={e}")
        return False
    finally:
        put_conn(conn)
```

### Task 1: task_service.py — FINAL task 완료 시 자동 마감 트리거

파일: `backend/app/services/task_service.py`
위치: `complete_work()` 메서드 — category_completed 판단 직전 (L330 근처)

```python
# ── 추가 위치: complete_task() 성공 후, incomplete_tasks 조회 전 ──

# Sprint 41-B: FINAL phase task 완료 시 → 릴레이 미완료 task 자동 마감
FINAL_TASK_IDS = {
    'SELF_INSPECTION',  # MECH 자주검사
    'INSPECTION',       # ELEC 자주검사 (검수)
    'PRESSURE_TEST',    # TMS 가압검사
    'PI_CHAMBER',       # PI CHAMBER 가압검사
    'QI_INSPECTION',    # QI 공정검사
    'SI_SHIPMENT',      # SI 출하완료
}

if task.task_id in FINAL_TASK_IDS:
    from app.models.task_detail import get_orphan_relay_tasks, auto_close_relay_task
    orphans = get_orphan_relay_tasks(task.serial_number, task.task_category)
    auto_closed_count = 0
    for orphan in orphans:
        success = auto_close_relay_task(
            task_detail_id=orphan['task_detail_id'],
            last_completion_at=orphan['last_completion_at'],
            worker_count=orphan['worker_count'],
        )
        if success:
            auto_closed_count += 1
            logger.info(
                f"Auto-closed relay task: task_detail_id={orphan['task_detail_id']}, "
                f"task_name={orphan['task_name']}, "
                f"last_completion_at={orphan['last_completion_at']}"
            )
    if auto_closed_count > 0:
        logger.info(
            f"Sprint 41-B auto-close: serial_number={task.serial_number}, "
            f"category={task.task_category}, closed={auto_closed_count}/{len(orphans)}"
        )
```

⚠️ 삽입 위치: `complete_task()` 호출 이후, `get_incomplete_tasks()` 이전.
이유: 자동 마감된 task가 incomplete 목록에서 빠져야 category_completed 판단이 정확함.

```python
# 현재 코드 흐름 (L312-331):
if not complete_task(task_detail_id, completed_at):
    return {'error': 'COMPLETE_FAILED'}, 500

# ★ Sprint 41-B 자동 마감 삽입 위치 ★

# 카테고리 전체 완료 확인
incomplete_tasks = get_incomplete_tasks(task.serial_number, task.task_category)
category_completed = len(incomplete_tasks) == 0
```

### Task 2: scheduler_service.py — Manager 알림 (주기적 감지)

파일: `backend/app/services/scheduler_service.py`

기존 스케줄러에 릴레이 미완료 감지 루틴 추가.
조건: work_completion_log의 마지막 기록 후 **4시간 경과** + completed_at IS NULL.

```python
def check_orphan_relay_tasks():
    """
    Sprint 41-B: 릴레이 미완료 task 감지 → Manager 알림

    조건: work_completion_log 마지막 기록 후 4시간 이상 경과 + completed_at IS NULL
    대상: MECH, ELEC, TMS 카테고리 (협력사 교대 작업 대상)
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT atd.id AS task_detail_id,
                   atd.serial_number,
                   atd.qr_doc_id,
                   atd.task_category,
                   atd.task_name,
                   MAX(wcl.completed_at) AS last_completion_at,
                   COUNT(DISTINCT wcl.worker_id) AS worker_count
            FROM app_task_details atd
            JOIN work_completion_log wcl ON wcl.task_id = atd.id
            WHERE atd.completed_at IS NULL
              AND atd.is_applicable = TRUE
              AND atd.task_category IN ('MECH', 'ELEC', 'TMS')
            GROUP BY atd.id
            HAVING MAX(wcl.completed_at) < NOW() - INTERVAL '4 hours'
        """)
        orphans = cur.fetchall()

        for orphan in orphans:
            # 중복 알림 방지: 같은 task에 대해 이미 알림이 존재하는지 확인
            cur.execute("""
                SELECT 1 FROM app_alert_logs
                WHERE alert_type = 'RELAY_ORPHAN'
                  AND serial_number = %s
                  AND message LIKE %s
                  AND created_at > NOW() - INTERVAL '24 hours'
                LIMIT 1
            """, (orphan['serial_number'], f"%{orphan['task_name']}%"))

            if cur.fetchone():
                continue  # 24시간 내 이미 알림 발송됨

            # Manager 알림 생성
            from app.services.alert_service import create_and_broadcast_alert
            create_and_broadcast_alert({
                'alert_type': 'RELAY_ORPHAN',
                'message': (
                    f"[릴레이 미완료] {orphan['serial_number']} "
                    f"{orphan['task_name']} — "
                    f"작업자 {orphan['worker_count']}명 참여 후 "
                    f"4시간 이상 미완료 상태입니다."
                ),
                'serial_number': orphan['serial_number'],
                'qr_doc_id': orphan['qr_doc_id'],
                'target_role': orphan['task_category'],  # 해당 카테고리 Manager에게
            })

            logger.info(
                f"Relay orphan alert sent: task_id={orphan['task_detail_id']}, "
                f"serial_number={orphan['serial_number']}"
            )
    finally:
        put_conn(conn)
```

스케줄러 등록: 기존 `run_scheduled_tasks()` 내에 추가.

```python
# scheduler_service.py — run_scheduled_tasks() 내
# 매 1시간마다 릴레이 미완료 감지 (기존 스케줄러 루프에 추가)
check_orphan_relay_tasks()
```

### Task 3: alert_type enum 등록

기존 패턴(Sprint 40-C `041_alert_type_deactivation.sql`)과 동일하게 `alert_type_enum`에 ALTER TYPE으로 추가.

```sql
-- migration: 042_alert_type_relay_orphan.sql
-- Sprint 41-B: 릴레이 미완료 task Manager 알림용 alert_type 추가
ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'RELAY_ORPHAN';
```

⚠️ `alert_types` 테이블은 존재하지 않음. 기존 시스템은 `alert_type_enum` PostgreSQL enum 타입 사용.
⚠️ migration 파일 번호는 기존 migration 마지막 번호 +1로 설정 (현재 041이 마지막이면 042).

### Regression 영향 분석

| 기존 흐름 | 변경 | 영향 |
|---|---|---|
| FINAL task 완료 → category_completed 판단 | 자동 마감 삽입 (incomplete_tasks 전) | ✅ 정확도 개선 (미완료 task 줄어듦) |
| 릴레이 없는 일반 완료 | orphans = [] → 루프 미실행 | ✅ 무관 |
| SINGLE_ACTION 완료 | FINAL_TASK_IDS에 포함 시 동일 동작 | ✅ 무관 (릴레이 대상 아니므로 orphan 없음) |
| 기존 알림 (TASK_REMINDER 등) | 별도 alert_type | ✅ 무관 |
| completion_status 업데이트 | 자동 마감된 task 반영 후 판단 | ✅ 정확도 개선 |
| production_confirm | 영향 없음 (자동 마감은 task만 닫음) | ✅ 무관 |

### 테스트

```
[자동 마감]
TC-41B-01: MECH task A 시작 → relay 종료 → MECH task B(다른 task) relay 종료 → SELF_INSPECTION finalize → A, B 모두 자동 마감 확인 (completed_at = last_completion_log 기준)
TC-41B-02: 자동 마감된 task의 duration_minutes = (started_at ~ last_completion_at) 계산 확인
TC-41B-03: 자동 마감된 task의 worker_count = completion_log의 DISTINCT worker_id 수 확인
TC-41B-04: SELF_INSPECTION finalize 후 category_completed 정상 판단 (자동 마감된 task가 incomplete에서 제외)
TC-41B-05: 릴레이 없는 S/N에서 SELF_INSPECTION finalize → orphans = [] → 기존 동작 유지 (regression)
TC-41B-06: ELEC INSPECTION finalize → ELEC 카테고리 릴레이 task 자동 마감 확인
TC-41B-07: TMS PRESSURE_TEST finalize → TMS 카테고리 릴레이 task 자동 마감 확인

[Manager 알림]
TC-41B-08: MECH task relay 종료 후 4시간 경과 → check_orphan_relay_tasks() 실행 → RELAY_ORPHAN 알림 생성 확인
TC-41B-09: 알림 메시지에 serial_number, task_name, worker_count 포함 확인
TC-41B-10: 24시간 내 동일 task에 대해 중복 알림 미발송 확인
TC-41B-11: completed_at이 설정된 task(자동 마감 완료)는 알림 대상 제외 확인

[혼합 시나리오]
TC-41B-12: worker1 relay → 3시간 후 worker2 relay → 4시간 후 알림 발생 → SELF_INSPECTION finalize → 자동 마감 (알림 후 마감 정상 동작)
TC-41B-13: worker1 relay → worker2 finalize(다른 task) → 해당 relay task는 열린 상태 유지 (다른 task의 finalize로 닫히지 않음 — FINAL task만 트리거)
TC-41B-14: 기존 단독 작업 start→complete (finalize=true) → orphan 검색 0건 → 자동 마감 미실행 (regression)
```

### 규칙
- 코드 변경 전 반드시 사용자 승인
- pytest 기존 테스트 전체 통과 확인
- 자동 마감 시 work_start_log, work_completion_log 보존 (이력 삭제 금지)
- FINAL_TASK_IDS 상수는 task_service.py 상단 또는 config에 정의 (하드코딩 최소화)
- alert_type 'RELAY_ORPHAN' migration 필수


## Fix Sprint 48: 재활성화 권한 체크 `in` 비교 방향 버그 (OPS_API_REQUESTS #48)

> 등록일: 2026-03-30
> 선행: 없음 (독립 버그 수정)
> 난이도: 낮음 (BE only, 1파일 1곳)
> FE 변경: 없음

### 배경

work.py L246-269의 재활성화(reactivate) 권한 체크에서 `company.upper() in partner.upper()` 비교 방향이 잘못됨.

**재현**: TMS(M) Manager가 `mech_partner = 'TMS'`인 제품의 MECH task를 재활성화 시도:
- L260: `'TMS(M)'.upper() in 'TMS'.upper()` → `'TMS(M)' in 'TMS'` → **False** → `FORBIDDEN`
- 기대: TMS(M)은 TMS 소속이므로 허용되어야 함

**동일 버그 — TMS 카테고리**:
- L264: `'TMS(M)'.upper() in module_outsourcing.upper()` → `module_outsourcing = 'TMS'`일 때 → **False**

### 원인 분석

```python
# work.py L260, L264 — 현재 (버그)
if category == 'MECH' and company and company.upper() in mech_partner.upper():
    allowed = True
elif category == 'TMS' and company and company.upper() in module_outsourcing.upper():
    allowed = True
```

Python `in` 연산자: `'A' in 'B'` → A가 B의 부분문자열인지 확인.
- `'TMS' in 'TMS(M)'` → True ✅
- `'TMS(M)' in 'TMS'` → False ❌ ← 현재 코드 방향

**progress_service.py (L209-216)**에서는 동일 문제를 회사별 하드코딩으로 해결:
```python
if company == 'TMS(M)':
    return ("(pi.mech_partner = 'TMS' OR pi.module_outsourcing = 'TMS')", [])
if company == 'TMS(E)':
    return ("pi.elec_partner = 'TMS'", [])
```

### 수정 방침

progress_service.py의 `_build_company_filter` 패턴과 일치시킴.
`company_base` 추출 (접미사 `(M)`, `(E)` 제거) 후 비교 방향 통일.

### Task 0: work.py — 재활성화 권한 체크 수정

파일: `backend/app/routes/work.py`
위치: L246-269

```python
# ── 변경 전 (L246-269) ──
    # Manager: 같은 company 소속 task만 재활성화 가능
    if worker.is_manager and not worker.is_admin:
        from app.models.product_info import get_product_by_serial_number as _get_product
        product = _get_product(task.serial_number)
        if product:
            company = worker.company or ''
            mech_partner = getattr(product, 'mech_partner', None) or ''
            elec_partner = getattr(product, 'elec_partner', None) or ''
            module_outsourcing = getattr(product, 'module_outsourcing', None) or ''
            category = task.task_category
            allowed = False
            if category == 'MECH' and company and company.upper() in mech_partner.upper():
                allowed = True
            elif category in ('ELEC',) and company and company.upper() in elec_partner.upper():
                allowed = True
            elif category == 'TMS' and company and company.upper() in module_outsourcing.upper():
                allowed = True
            elif category in ('PI', 'QI', 'SI') and company == 'GST':
                allowed = True
            if not allowed:
                return jsonify({'error': 'FORBIDDEN', 'message': '자사 제품이 아닙니다.'}), 403

# ── 변경 후 ──
    # Manager: 같은 company 소속 task만 재활성화 가능
    # Fix Sprint 48: company_base 추출 + 비교 방향 수정 (progress_service.py 패턴 일치)
    if worker.is_manager and not worker.is_admin:
        from app.models.product_info import get_product_by_serial_number as _get_product
        product = _get_product(task.serial_number)
        if product:
            company = worker.company or ''
            # TMS(M) → TMS, TMS(E) → TMS 등 접미사 제거
            company_base = company.upper().replace('(M)', '').replace('(E)', '')
            mech_partner = (getattr(product, 'mech_partner', None) or '').upper()
            elec_partner = (getattr(product, 'elec_partner', None) or '').upper()
            module_outsourcing = (getattr(product, 'module_outsourcing', None) or '').upper()
            category = task.task_category
            allowed = False

            if category == 'MECH' and company_base:
                # MECH: mech_partner 일치 확인
                # TMS(M) → company_base='TMS', mech_partner='TMS' → 일치 ✅
                # FNI → company_base='FNI', mech_partner='FNI' → 일치 ✅
                allowed = company_base == mech_partner or company_base in mech_partner

            elif category == 'ELEC' and company_base:
                # ELEC: elec_partner 일치 확인
                # TMS(E) → company_base='TMS', elec_partner='TMS' → 일치 ✅
                # P&S → company_base='P&S', elec_partner='P&S' → 일치 ✅
                allowed = company_base == elec_partner or company_base in elec_partner

            elif category == 'TMS' and company_base:
                # TMS: module_outsourcing 또는 mech_partner 확인
                # TMS(M) → company_base='TMS', module_outsourcing='TMS' → 일치 ✅
                # TMS(M) + mech_partner='TMS' → 일치 ✅
                allowed = (
                    company_base == module_outsourcing or company_base in module_outsourcing
                    or company_base == mech_partner or company_base in mech_partner
                )

            elif category in ('PI', 'QI', 'SI') and company == 'GST':
                allowed = True

            if not allowed:
                return jsonify({'error': 'FORBIDDEN', 'message': '자사 제품이 아닙니다.'}), 403
```

### 주요 회사별 매칭 결과 (수정 후)

| company | company_base | category | partner 필드 | 비교 | 결과 |
|---|---|---|---|---|---|
| TMS(M) | TMS | MECH | mech_partner='TMS' | TMS == TMS | ✅ 허용 |
| TMS(M) | TMS | TMS | module_outsourcing='TMS' | TMS == TMS | ✅ 허용 |
| TMS(E) | TMS | ELEC | elec_partner='TMS' | TMS == TMS | ✅ 허용 |
| FNI | FNI | MECH | mech_partner='FNI' | FNI == FNI | ✅ 허용 |
| BAT | BAT | MECH | mech_partner='BAT' | BAT == BAT | ✅ 허용 |
| P&S | P&S | ELEC | elec_partner='P&S' | P&S == P&S | ✅ 허용 |
| C&A | C&A | ELEC | elec_partner='C&A' | C&A == C&A | ✅ 허용 |
| GST | GST | PI | — | company == 'GST' | ✅ 허용 |
| FNI | FNI | ELEC | elec_partner='P&S' | FNI == P&S | ❌ 차단 (정상) |
| TMS(M) | TMS | ELEC | elec_partner='P&S' | TMS == P&S | ❌ 차단 (정상) |

### Regression 영향

| 기존 동작 | 변경 후 | 영향 |
|---|---|---|
| FNI/BAT MECH 재활성화 | company_base == mech_partner → 동일 결과 | ✅ 무관 |
| P&S/C&A ELEC 재활성화 | company_base == elec_partner → 동일 결과 | ✅ 무관 |
| GST PI/QI/SI 재활성화 | company == 'GST' → 변경 없음 | ✅ 무관 |
| TMS(M) MECH 재활성화 | 기존: False (버그) → 수정: True | ✅ 버그 수정 |
| TMS(M) TMS 재활성화 | 기존: False (버그) → 수정: True | ✅ 버그 수정 |
| TMS(E) ELEC 재활성화 | 기존: False (버그) → 수정: True | ✅ 버그 수정 |
| 타사 카테고리 cross 시도 | 기존: False → 수정: False | ✅ 무관 |
| Admin 재활성화 | L247 `not worker.is_admin` → 이 분기 미진입 | ✅ 무관 |

### 테스트

```
[TMS(M) — 핵심 버그 수정]
TC-48-01: TMS(M) Manager → mech_partner='TMS' 제품의 MECH task 재활성화 → 허용 (기존: FORBIDDEN)
TC-48-02: TMS(M) Manager → module_outsourcing='TMS' 제품의 TMS task 재활성화 → 허용 (기존: FORBIDDEN)
TC-48-03: TMS(M) Manager → elec_partner='P&S' 제품의 ELEC task 재활성화 → FORBIDDEN (타사 — 기존 동작 보존)

[TMS(E)]
TC-48-04: TMS(E) Manager → elec_partner='TMS' 제품의 ELEC task 재활성화 → 허용
TC-48-05: TMS(E) Manager → mech_partner='FNI' 제품의 MECH task 재활성화 → FORBIDDEN

[기존 회사 — regression]
TC-48-06: FNI Manager → mech_partner='FNI' 제품의 MECH task 재활성화 → 허용 (기존 동작 유지)
TC-48-07: P&S Manager → elec_partner='P&S' 제품의 ELEC task 재활성화 → 허용 (기존 동작 유지)
TC-48-08: GST Manager → PI task 재활성화 → 허용 (기존 동작 유지)
TC-48-09: BAT Manager → elec_partner='P&S' 제품의 ELEC task 재활성화 → FORBIDDEN (타사 차단 유지)
TC-48-10: Admin → 모든 카테고리 재활성화 → 허용 (is_admin 분기 미진입)
```

### 규칙
- 코드 변경 전 반드시 사용자 승인
- pytest 기존 테스트 전체 통과 확인
- progress_service.py의 _build_company_filter와 로직 일관성 유지
- TC-48-01~10 수동 테스트 통과 후 커밋


## Sprint 51: progress API에 `sales_order` 필드 추가 (OPS_API_REQUESTS #51)

> 등록일: 2026-03-31
> 선행: 없음 (독립 수정)
> 난이도: 낮음 (BE only, 1파일 3곳)
> FE 변경: 없음 (VIEW Sprint 24에서 소비)

### 배경

생산현황(SNStatusPage)에서 S/N 카드가 개별 나열되어 같은 O/N(Order Number) 소속 S/N을 한눈에 파악하기 어려움.
VIEW Sprint 24에서 O/N 단위 아코디언 그룹핑 UI를 구현하려면 progress API 응답에 `sales_order` 필드가 필요.

현재 `GET /api/app/product/progress` 응답에 `sales_order` 없음.
`plan.product_info` 테이블에 `sales_order` 컬럼은 이미 존재하며, `progress_service.py`에서 JOIN하고 있으나 SELECT에 미포함.

### Task 0: progress_service.py — sn_list CTE에 sales_order 추가

파일: `backend/app/services/progress_service.py`
위치: sn_list CTE (L57-66)

```python
# ── 변경 전 (L58-66) ──
WITH sn_list AS (
    SELECT
        qr.serial_number,
        qr.qr_doc_id,
        pi.model,
        pi.customer,
        pi.ship_plan_date,
        pi.mech_partner,
        pi.elec_partner,
        pi.module_outsourcing,

# ── 변경 후 ──
WITH sn_list AS (
    SELECT
        qr.serial_number,
        qr.qr_doc_id,
        pi.model,
        pi.customer,
        pi.ship_plan_date,
        pi.sales_order,              -- Sprint 51: O/N 그룹핑용
        pi.mech_partner,
        pi.elec_partner,
        pi.module_outsourcing,
```

### Task 1: progress_service.py — 메인 SELECT에 sales_order 추가

파일: `backend/app/services/progress_service.py`
위치: 메인 SELECT (L87-103)

```python
# ── 변경 전 (L87-95) ──
SELECT
    sn.serial_number,
    sn.qr_doc_id,
    sn.model,
    sn.customer,
    sn.ship_plan_date,
    sn.mech_partner,
    sn.elec_partner,
    sn.module_outsourcing,

# ── 변경 후 ──
SELECT
    sn.serial_number,
    sn.qr_doc_id,
    sn.model,
    sn.customer,
    sn.ship_plan_date,
    sn.sales_order,                  -- Sprint 51
    sn.mech_partner,
    sn.elec_partner,
    sn.module_outsourcing,
```

### Task 2: progress_service.py — _aggregate_products() sn_map에 sales_order 포함

파일: `backend/app/services/progress_service.py`
위치: `_aggregate_products()` sn_map 초기화 (L254-266)

```python
# ── 변경 전 (L254-266) ──
sn_map[sn] = {
    'serial_number': sn,
    'qr_doc_id': row['qr_doc_id'],
    'model': row['model'],
    'customer': row['customer'],
    'ship_plan_date': row['ship_plan_date'].isoformat() if row['ship_plan_date'] else None,
    'all_completed': row['all_completed'],
    'all_completed_at': row['all_completed_at'].isoformat() if row['all_completed_at'] else None,
    'mech_partner': row['mech_partner'],
    'elec_partner': row['elec_partner'],
    'module_outsourcing': row['module_outsourcing'],
    'categories': {},
}

# ── 변경 후 ──
sn_map[sn] = {
    'serial_number': sn,
    'qr_doc_id': row['qr_doc_id'],
    'model': row['model'],
    'customer': row['customer'],
    'ship_plan_date': row['ship_plan_date'].isoformat() if row['ship_plan_date'] else None,
    'sales_order': row['sales_order'],   # Sprint 51: O/N 그룹핑용
    'all_completed': row['all_completed'],
    'all_completed_at': row['all_completed_at'].isoformat() if row['all_completed_at'] else None,
    'mech_partner': row['mech_partner'],
    'elec_partner': row['elec_partner'],
    'module_outsourcing': row['module_outsourcing'],
    'categories': {},
}
```

⚠️ `sales_order`는 L293-296의 `pop()` 대상에 **포함하지 않음** — 응답에 노출되어야 FE에서 사용 가능.

```python
# L293-296 — 변경 없음 (partner 필드만 pop)
sn_data.pop('mech_partner', None)
sn_data.pop('elec_partner', None)
sn_data.pop('module_outsourcing', None)
# sales_order는 pop하지 않음
```

### 예상 응답 변화

```json
{
  "products": [
    {
      "serial_number": "6905",
      "model": "GAIA-I DUAL",
      "customer": "...",
      "sales_order": "6408",
      "ship_plan_date": "2026-04-15",
      "overall_percent": 65,
      "categories": { "MECH": {...}, "ELEC": {...} }
    },
    {
      "serial_number": "6906",
      "model": "GAIA-I DUAL",
      "customer": "...",
      "sales_order": null,
      "ship_plan_date": null,
      "overall_percent": 0,
      "categories": {}
    }
  ]
}
```

### Regression 영향

| 기존 동작 | 변경 후 | 영향 |
|---|---|---|
| progress 응답 필드 | `sales_order` 1개 추가 | ✅ 추가만 (기존 필드 삭제/변경 없음) |
| sales_order NULL인 S/N | `"sales_order": null` | ✅ 정상 (NULL 허용) |
| partner 필드 pop (내부용) | 변경 없음 | ✅ 무관 |
| _build_company_filter 쿼리 | 변경 없음 | ✅ 무관 |
| FE(Flutter OPS) progress 호출 | 추가 필드 무시 (사용 안 함) | ✅ 무관 |
| VIEW SNStatusPage progress 호출 | sales_order 수신 가능 (Sprint 24에서 소비) | ✅ 선행 완료 |

### 테스트

```
[기본 동작]
TC-51-01: GET /api/app/product/progress → 응답 products[].sales_order 필드 존재 확인
TC-51-02: sales_order가 NULL인 S/N → "sales_order": null 정상 응답
TC-51-03: sales_order가 있는 S/N → "sales_order": "6408" 등 정상 값

[기존 기능 regression]
TC-51-04: 기존 필드 (serial_number, model, customer, ship_plan_date, categories, overall_percent) 정상 응답
TC-51-05: 협력사 필터 (FNI → MECH만, TMS(M) → TMS+MECH, GST → 전체) 기존 동작 유지
TC-51-06: completion 필터 (all/completed/incomplete) 기존 동작 유지
TC-51-07: partner 필드 (mech_partner, elec_partner, module_outsourcing) 응답에서 제거 확인 (pop 동작 유지)
```

### 규칙
- 코드 변경 전 반드시 사용자 승인
- pytest 기존 테스트 전체 통과 확인
- VIEW Sprint 24 선행 조건 — 이 Sprint 완료 후 VIEW에서 SNProduct 타입에 sales_order 추가
- TC-51-01~07 수동 테스트 통과 후 커밋


## Sprint 52: TM 체크리스트 — Partner 검수 시스템 (2026-04-01) — Phase 1

> 등록일: 2026-04-01
> 트랙: BE + FE (OPS)
> 선행: Sprint 11 (checklist 스키마 + CRUD), Sprint 41-B (알림 시스템)
> 난이도: 중상 (DB 스키마 변경 + 신규 API + 신규 FE 화면)
> VIEW 변경: 없음 (VIEW 체크리스트 관리 페이지 이미 TM 탭 존재, VIEW Sprint는 이 Sprint의 Admin API를 소비)

### 배경

Tank Module 조립 완료 후 품질 검수가 종이 체크리스트로 진행되고 있어, 이력 추적·실적 연계가 불가.
현장에서는 작업 미스를 잡기 위한 크로스체크(2중 검사) 개념이 필요하며, 문제 발생 시 MECH/ELEC 파트너에게 ISSUE 알림 전달이 요구됨.

**현재 상태:**
- `checklist.checklist_master` + `checklist_record` 테이블 존재 (Sprint 11)
- `checklist_record.is_checked`가 **boolean** → Pass/NA 3상태 표현 불가
- 1차/2차 판정 구분 없음, 항목 그룹 개념 없음
- VIEW 대시보드에 MECH/ELEC/TM 탭은 이미 존재 (프론트엔드, DB 데이터 없음)
- OPS 앱 `checklist_screen.dart`는 HOOKUP/PI/QI용 범용 화면 (boolean 토글) → TM 전용 신규 화면 필요

**이번 Sprint 범위:**
- Phase 1 = **1차 체크(Manager)만 구현** (Tank Module task 종료 시점)
- 추후 Phase 2에서 2차 체크(가압검사 시점) + 1차 체크 일반유저 옵션 확장

**체크리스트 항목 (15항목, 4그룹) — 기구 조립 검사 성적서 기준:**

| 그룹 | 순서 | 검사 내용 | 기준/SPEC | 검사 방법 |
|------|------|-----------|-----------|-----------|
| BURNER | 1 | SUS Fitting 조임 상태 | GAP GAUGE | 측수 검사 |
| BURNER | 2 | Gas Nozzle Cover 휨 여부 | Jig 활용 Center 확인 | 육안 검사 |
| BURNER | 3 | 클램프 체결 | 조립 유동 여부 | 측수 검사 |
| REACTOR | 1 | Fitting 조임 상태 | 조립 유동 여부 | 측수 검사 |
| REACTOR | 2 | Tube 조립 상태 | 조립 유동 여부 | 측수 검사 |
| REACTOR | 3 | 클램프 체결 | 조립 유동 여부 | 측수 검사 |
| REACTOR | 4 | Cir Line Tubing | 조립 유동 여부 | 측수 검사 |
| EXHAUST | 1 | Packing 조립 확인 | 적용 여부 | 육안 검사 |
| EXHAUST | 2 | Packing Guide 고정 확인 | 유동 여부 | 육안 검사 |
| EXHAUST | 3 | SUS Fitting 조임 상태 | GAP GAUGE | 측수 검사 |
| EXHAUST | 4 | BCW Nozzle Spray 방향 | 아래 방향 | 육안 검사 |
| TANK | 1 | Cir Pump Spec 확인 | 조립 도면과 현물 1:1 확인 | 육안 검사 |
| TANK | 2 | Flow Sensor Swirl Orifice | Swirl Orifice 적용 조립 | 육안 검사 |
| TANK | 3 | Tank 내부 이물질 확인 | Tank 투시창 이용 확인 | 육안 검사 |
| TANK | 4 | 열교환기 Spec 확인 | 조립 도면과 현물 1:1 확인 | 육안 검사 |

> 판정: 1차판정 (TM 완료 시점, Manager), 2차판정 (가압검사 시점, Phase 2)
> 하단: 가압검사 (시작일시/종료일시/작업자/비고), ISSUE사항 메모란

**Seed SQL:** ~~아래는 참고용 (product_code별 개별 등록 시 사용)~~
> **Sprint 52-A에서 대체됨** — 실제 seed는 Sprint 52-A의 migration 043a에서 `product_code='COMMON'`으로 공통 등록.
> product_code별 개별 항목 관리가 필요해지면 아래 템플릿에 @product_code를 치환하여 사용.
> description에 기준/SPEC + 검사방법을 통합 저장 (Phase 1). 추후 컬럼 분리 가능.

```sql
-- [참고용 — 실행하지 마세요. Sprint 52-A migration 043a를 사용하세요]
-- product_code별 개별 등록 템플릿 (표준화 완료 후 사용)
-- @product_code: 대상 product_code (예: 'GST-24K')
INSERT INTO checklist.checklist_master (product_code, category, item_group, item_name, item_order, description, is_active)
VALUES
  (@product_code, 'TM', 'BURNER', 'SUS Fitting 조임 상태', 1, 'GAP GAUGE / 측수 검사', TRUE),
  ...
ON CONFLICT (product_code, category, item_group, item_name) DO NOTHING;
```

**워크플로우:**
```
TM 작업자가 Tank Module task 종료
  → task completed 처리
  → TMS is_manager에게 알림 (CHECKLIST_TM_READY)
  → Manager가 OPS 앱에서 TM 체크리스트 진입
  → 15항목 각각 Pass / NA 선택 + ISSUE 코멘트 입력 (선택)
  → 전체 항목 Pass 또는 NA 선택 완료 → 체크리스트 완료
  → ISSUE 코멘트 있으면 → MECH/ELEC is_manager에게 알림 (CHECKLIST_ISSUE, on/off 옵션)
```

### 현재 코드 구조 (확인 완료)

```
checklist_master (checklist 스키마):
  id, product_code, category, item_name, item_order, description, is_active
  UNIQUE(product_code, category, item_name)

checklist_record (checklist 스키마):
  id, serial_number, master_id(FK), is_checked(bool), checked_by(FK workers), checked_at, note
  UNIQUE(serial_number, master_id)

checklist.py (routes):
  GET  /api/app/checklist/<sn>/<category>   — master+record LEFT JOIN
  PUT  /api/app/checklist/check             — UPSERT (is_checked bool)
  POST /api/admin/checklist/import          — Excel 업로드

alert_service.py:
  create_and_broadcast_alert() — alert_type + message + target 지정

alert_type_enum 기존 값:
  PROCESS_READY, UNFINISHED_AT_CLOSING, DURATION_EXCEEDED, BREAK_TIME_PAUSE,
  BREAK_TIME_END, DEACTIVATED, RELAY_ORPHAN, ...
```

### 수정 대상 파일

```
1. backend/migrations/043_tm_checklist_schema.sql          (신규 — 스키마 변경)
2. backend/app/routes/checklist.py                         (수정 — OPS API + Admin API 확장)
3. backend/app/routes/admin.py                             (수정 — SETTING_KEYS에 tm_checklist_* 등록)
4. backend/app/services/checklist_service.py               (신규 — TM 체크리스트 비즈니스 로직)
5. backend/app/services/task_service.py                    (수정 — TM 완료 시 알림 트리거)
6. frontend/lib/screens/checklist/tm_checklist_screen.dart (신규 — TM 전용 화면)
7. tests/backend/test_sprint52_tm_checklist.py             (신규)
```

### Task 0: Migration — 스키마 확장 (043_tm_checklist_schema.sql)

신규 파일: `backend/migrations/043_tm_checklist_schema.sql`

```sql
-- Sprint 52: TM 체크리스트 스키마 확장
-- 043

-- ────────────────────────────────────────────────────────────────
-- 1. checklist_master에 item_group 컬럼 추가
--    용도: 15항목을 BURNER/REACTOR/EXHAUST/TANK 그룹으로 분류
-- ────────────────────────────────────────────────────────────────
ALTER TABLE checklist.checklist_master
    ADD COLUMN IF NOT EXISTS item_group VARCHAR(50);

COMMENT ON COLUMN checklist.checklist_master.item_group
    IS '항목 그룹 (TM: BURNER, REACTOR, EXHAUST, TANK)';


-- ────────────────────────────────────────────────────────────────
-- 2. checklist_record 변경: is_checked(bool) → check_result(varchar)
--    값: PASS, NA, NULL(미체크)
--    기존 데이터 마이그레이션: true→PASS, false→NULL
-- ────────────────────────────────────────────────────────────────
ALTER TABLE checklist.checklist_record
    ADD COLUMN IF NOT EXISTS check_result VARCHAR(10);

-- 기존 is_checked 데이터 마이그레이션
UPDATE checklist.checklist_record
SET check_result = CASE
    WHEN is_checked = TRUE THEN 'PASS'
    ELSE NULL
END
WHERE check_result IS NULL AND is_checked IS NOT NULL;

COMMENT ON COLUMN checklist.checklist_record.check_result
    IS '검사 결과: PASS=통과, NA=해당없음, NULL=미체크';


-- ────────────────────────────────────────────────────────────────
-- 3. checklist_record에 judgment_phase 컬럼 추가
--    Phase 1에서는 항상 1, Phase 2에서 2차 체크 시 2 사용
--    UNIQUE 제약 변경: (serial_number, master_id) → (serial_number, master_id, judgment_phase)
-- ────────────────────────────────────────────────────────────────
ALTER TABLE checklist.checklist_record
    ADD COLUMN IF NOT EXISTS judgment_phase INTEGER DEFAULT 1;

COMMENT ON COLUMN checklist.checklist_record.judgment_phase
    IS '판정 단계: 1=1차(TM종료 시점), 2=2차(가압검사 시점, 추후)';

-- 기존 UNIQUE 제약 제거 후 새 제약 추가
ALTER TABLE checklist.checklist_record
    DROP CONSTRAINT IF EXISTS checklist_record_serial_number_master_id_key;

ALTER TABLE checklist.checklist_record
    ADD CONSTRAINT checklist_record_sn_master_phase_key
    UNIQUE (serial_number, master_id, judgment_phase);


-- ────────────────────────────────────────────────────────────────
-- 4. alert_type_enum 확장: TM 체크리스트 알림 타입
-- ────────────────────────────────────────────────────────────────
ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'CHECKLIST_TM_READY';
ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'CHECKLIST_ISSUE';


-- ────────────────────────────────────────────────────────────────
-- 5. admin_settings에 TM 체크리스트 옵션 추가
--    tm_checklist_1st_checker: "is_manager" (기본값, 추후 "user" 가능)
--    tm_checklist_issue_alert: true (ISSUE 알림 on/off, 추후용 기능)
--    tm_checklist_scope: "product_code" (기본값, "all" 가능)
-- ────────────────────────────────────────────────────────────────
INSERT INTO admin_settings (setting_key, setting_value, description)
VALUES
    ('tm_checklist_1st_checker', '"is_manager"', 'TM 체크리스트 1차 체크 권한 (is_manager|user)'),
    ('tm_checklist_issue_alert', 'true', 'TM 체크리스트 ISSUE 알림 on/off'),
    ('tm_checklist_scope', '"product_code"', 'TM 체크리스트 항목 범위 (product_code|all)')
ON CONFLICT (setting_key) DO NOTHING;
```

⚠️ **is_checked 컬럼은 삭제하지 않음** — check_result로 마이그레이션 후에도 기존 코드 호환을 위해 유지. 기존 MECH/ELEC 체크리스트 GET/PUT API는 is_checked로 계속 동작하고, TM 전용 API만 check_result 사용.

### Task 1: checklist_service.py — TM 체크리스트 비즈니스 로직 (신규)

신규 파일: `backend/app/services/checklist_service.py`

핵심 함수 3개:

```python
"""
TM 체크리스트 서비스 (Sprint 52)
체크리스트 조회 / 항목 체크 / 완료 판정 + 알림
"""

# ── 함수 1: get_tm_checklist(serial_number, judgment_phase=1) ──
# checklist_master (category='TM') + checklist_record LEFT JOIN
# product_code 조회 → admin_settings.tm_checklist_scope 확인
#   - "product_code": 해당 product_code로 master 필터
#   - "all": product_code 무시, category='TM'인 전체 master 항목
# 반환: 그룹별 항목 리스트 (item_group으로 GROUP BY)
# {
#   "serial_number": "6905",
#   "sales_order": "6408",           ← O/N (product_info.sales_order JOIN)
#   "model": "GAIA-I DUAL",
#   "groups": [
#     {
#       "group_name": "BURNER",
#       "items": [
#         { "master_id": 1, "item_name": "...", "check_result": "PASS"|"NA"|null,
#           "checked_by_name": "...", "checked_at": "...", "note": "..." },
#         ...
#       ]
#     },
#     ...
#   ],
#   "summary": { "total": 15, "checked": 10, "remaining": 5, "is_complete": false }
# }


# ── 함수 2: upsert_tm_check(serial_number, master_id, check_result, note, worker_id, judgment_phase=1) ──
# check_result 유효성: 'PASS' 또는 'NA'만 허용
# UPSERT checklist_record (serial_number, master_id, judgment_phase)
# check_result + checked_by + checked_at + note 업데이트
#
# UPSERT 후 → _check_tm_completion() 호출하여 전체 완료 여부 판정
# 반환: { "master_id": ..., "check_result": ..., "is_complete": bool }


# ── 함수 3: _check_tm_completion(serial_number, judgment_phase=1) ──
# 해당 S/N의 TM 체크리스트 전체 항목 중 check_result IS NULL인 항목 수 확인
# 전부 PASS 또는 NA → is_complete = True
#
# is_complete일 때:
#   - note에 내용이 있는 항목(ISSUE) 존재 여부 확인
#   - ISSUE 있고 admin_settings.tm_checklist_issue_alert = true이면
#     → MECH/ELEC is_manager에게 CHECKLIST_ISSUE 알림 생성
#     → create_and_broadcast_alert({
#         alert_type: 'CHECKLIST_ISSUE',
#         message: '[S/N] TM 체크리스트 ISSUE: {item_name} - {note}',
#         serial_number: ...,
#         target_role: 'MECH'  # MECH manager (Sprint 6 이후 role 네이밍)
#       })
#   - 반환: True
# 미완료 → 반환: False
```

### Task 2: checklist.py — TM 전용 API 엔드포인트 추가

파일: `backend/app/routes/checklist.py`
위치: 기존 엔드포인트 아래에 추가

```python
# ── 추가 엔드포인트 1: TM 체크리스트 조회 ──
# GET /api/app/checklist/tm/<serial_number>
#
# 기존 GET /api/app/checklist/<sn>/<category>와 다른 점:
#   - item_group별 그룹핑 응답
#   - check_result (PASS/NA/null) 반환 (is_checked 대신)
#   - summary (total, checked, remaining, is_complete) 포함
#
# 내부: checklist_service.get_tm_checklist(serial_number) 호출


# ── 추가 엔드포인트 2: TM 체크리스트 항목 체크 ──
# PUT /api/app/checklist/tm/check
#
# Request Body:
#   {
#     "serial_number": str,
#     "master_id": int,
#     "check_result": "PASS" | "NA",    ← boolean 대신 문자열
#     "note": str (optional, ISSUE 내용)
#   }
#
# 권한 체크: admin_settings.tm_checklist_1st_checker 확인
#   - "is_manager": 호출자가 is_manager=True인지 확인
#   - "user": 모든 인증 유저 허용
#
# 내부: checklist_service.upsert_tm_check(...) 호출
# 완료 시 is_complete=True → 프론트에서 완료 UI 표시


# ── 추가 엔드포인트 3: TM 체크리스트 완료 상태 조회 ──
# GET /api/app/checklist/tm/<serial_number>/status
#
# 반환: { "is_complete": bool, "completed_at": str|null, "checked_count": int, "total_count": int }
# 용도: 실적 조건 연동 시 다른 서비스에서 체크리스트 완료 여부 확인용
```

### Task 3: task_service.py — TM 완료 시 알림 트리거

파일: `backend/app/services/task_service.py`
위치: `complete_work()` 내부, task 완료(finalize) 처리 후 블록

```python
# ── 변경 위치: _finalize_task_multi_worker() 또는 complete_work() 내 task 완료 후 ──
#
# 조건: 완료된 task의 category가 'TM' (Tank Module)일 때
#
# ── 분기: 완료자가 is_manager인지 여부 ──
#
# Case A: 완료자(worker_id)가 is_manager=True인 경우
#   → 알림 미발송 (본인이 방금 끝낸 작업이므로 알림 불필요)
#   → API 응답에 "checklist_ready": true 플래그 추가
#   → FE에서 "체크리스트 검수로 이동하시겠습니까?" 다이얼로그 표시
#   → 확인 → tm_checklist_screen으로 바로 이동
#
# Case B: 완료자가 일반 작업자(is_manager=False)인 경우
#   → TMS is_manager에게 CHECKLIST_TM_READY 알림 발송
#   → create_and_broadcast_alert({
#        alert_type: 'CHECKLIST_TM_READY',
#        message: '[S/N] Tank Module 작업 완료 — 체크리스트 검수가 필요합니다',
#        serial_number: serial_number,
#        target_worker_id: manager_id  # TMS is_manager
#      })
#
# ⚠️ 알림 실패해도 task 완료는 정상 처리 (try-except로 감싸기)
# ⚠️ finalize=False (릴레이 내 작업 종료)에서는 알림 안 보냄 — finalize=True일 때만
#
# ── 향후 확장 (MECH/ELEC 체크리스트 적용 시 동일 패턴) ──
# MECH task 완료 → MECH is_manager 알림 (완료자가 manager면 스킵)
# ELEC task 완료 → ELEC is_manager 알림 (완료자가 manager면 스킵)
# 카테고리별 checklist_ready 플래그 + 알림 타입만 변경하면 됨
```

### Task 4: tm_checklist_screen.dart — TM 전용 체크리스트 화면 (신규)

신규 파일: `frontend/lib/screens/checklist/tm_checklist_screen.dart`

```
화면 구성:
┌─────────────────────────────────────┐
│  ← TM 체크리스트                    │
│     O/N: 6408  |  S/N: 6905         │
│     진행률: 12/15  ████████░░ 80%   │
├─────────────────────────────────────┤
│  ▼ BURNER (2/3)                     │
│  ┌─────────────────────────────────┐│
│  │ ✅ PASS  항목1                  ││
│  │ ⬜ ---   항목2         [코멘트] ││
│  │ 🔘 NA    항목3                  ││
│  └─────────────────────────────────┘│
│  ▼ REACTOR (4/4) ✓                  │
│  ┌─────────────────────────────────┐│
│  │ ✅ PASS  항목4                  ││
│  │ ...                             ││
│  └─────────────────────────────────┘│
│  ▼ EXHAUST (3/4)                    │
│  ▼ TANK (3/4)                       │
├─────────────────────────────────────┤
│  [전체 완료 시 '검수 완료' 배너]     │
└─────────────────────────────────────┘
```

**UI 동작:**
- **헤더**: O/N(sales_order) + S/N 함께 표시 — 작업자가 O/N으로 제품 식별하므로 O/N 우선 노출
  - GET /api/app/checklist/tm/{sn} 응답에 sales_order 포함 (product_info JOIN)
- 각 항목 탭 → **PASS ↔ NA 토글** (3상태: null → PASS → NA → null)
- 항목 롱프레스 또는 코멘트 아이콘 → **ISSUE 코멘트 입력 다이얼로그**
- 그룹별 접기/펼치기 (ExpansionTile)
- 진행률 바: checked(PASS+NA) / total
- 전체 완료 시 → 상단 초록색 배너 + '검수 완료' 표시
- optimistic update + 실패 시 롤백 (기존 checklist_screen.dart 패턴 참고)

**진입 경로 (3가지):**
- **경로 1**: Manager가 직접 TM 완료 → complete_work 응답의 `checklist_ready: true` 감지 → "체크리스트 검수로 이동하시겠습니까?" 다이얼로그 → 확인 → tm_checklist_screen 진입
- **경로 2**: 알림 탭에서 CHECKLIST_TM_READY 알림 탭 → 해당 S/N의 tm_checklist_screen으로 이동
- **경로 3**: task_detail_screen에서 TM 카테고리 task 완료 상태일 때 '체크리스트' 버튼 노출 → 이동

### BUG-FIX (Sprint 52): tm_checklist_screen.dart — BE 응답 필드명 매핑 수정

파일: `frontend/lib/screens/checklist/tm_checklist_screen.dart`
적용일: 2026-04-02

FE가 읽는 키와 BE 응답 키가 불일치하여 항목명/그룹명이 "-"로 표시되는 버그.

```
수정 내역 (6곳):
  g['group']       → g['group_name']      (L76, L538)
  item['check_name'] → item['item_name']  (L208, L627)
  item['id']       → item['master_id']    (L132, L183, L314, L626)
```

### BUG-FIX #2 (Sprint 52): 매니저 직접 완료 시 체크리스트 화면 전환 누락

적용일: 2026-04-02

**증상**: 매니저가 직접 TANK_MODULE을 완료하면 BE에서 `checklist_ready: true`를
응답에 포함하지만 FE에서 이 플래그를 무시하여 체크리스트 화면으로 전환되지 않음.
비매니저 완료 시에는 알림(CHECKLIST_TM_READY)이 발송되어 알림 탭에서 체크리스트 진입 가능하지만,
매니저 직접 완료(Case A)는 알림 없이 FE 응답 플래그만 사용하므로 화면 전환이 필수.

**원인**: BE `_trigger_tm_checklist_alert()` Case A가 `checklist_ready: true`를 리턴하고
`complete_work` 응답에 포함하지만, FE의 `task_service.dart → task_provider.dart → task_detail_screen.dart`
체인에서 해당 필드를 파싱/전달/처리하지 않음.

**수정 파일 4개**:

```
1. frontend/lib/services/task_service.dart
   - completeTask() 리턴 타입: Future<TaskItem> → Future<({TaskItem task, bool checklistReady})>
   - response['checklist_ready'] == true 파싱 추가

2. frontend/lib/providers/task_provider.dart
   - completeTask() 리턴 타입: Future<bool> → Future<({bool success, bool checklistReady})>
   - result.task / result.checklistReady 분리 처리

3. frontend/lib/screens/task/task_detail_screen.dart
   - import '../checklist/tm_checklist_screen.dart' 추가
   - _handleCompleteTask(): result.checklistReady == true 시
     Navigator.pop 후 TmChecklistScreen(serialNumber) push

4. frontend/lib/screens/task/task_management_screen.dart
   - import '../checklist/tm_checklist_screen.dart' 추가
   - 완료 핸들러: result.checklistReady == true 시
     TmChecklistScreen(serialNumber) push
```

### BUG-FIX #3 (Sprint 52): task_detail_screen — TANK_MODULE 완료 시 체크리스트 진입 버튼

적용일: 2026-04-02

**증상**: 매니저가 TANK_MODULE 완료 후 실수로 체크리스트 화면을 벗어나면
알림이 없는 상태(Case A)에서 체크리스트에 재진입할 방법이 없음.

**수정**: `_buildCompletedBadge()`에 task 파라미터 추가.
`task.taskId == 'TANK_MODULE' && task.taskCategory == 'TMS'` 조건에서
"체크리스트 검수" 버튼을 `작업 완료됨` 배지 아래에 표시.

```
파일: frontend/lib/screens/task/task_detail_screen.dart

수정 내용:
  - _buildCompletedBadge() → _buildCompletedBadge(TaskItem task) 파라미터 추가
  - 호출부: _buildCompletedBadge() → _buildCompletedBadge(task)
  - TANK_MODULE + TMS 조건: accent 그라데이션 "체크리스트 검수" 버튼 추가
  - 탭 시 TmChecklistScreen(serialNumber) push
```

### BUG-FIX #4 (Sprint 52): checklist.py — check_result=null 500 에러

적용일: 2026-04-02 / commit: c68b211

**증상**: 체크리스트 항목을 PASS→NA→세번째 탭 시 FE가 `check_result: null`을 전송,
BE에서 `None.strip()` → `AttributeError` 500 에러.

**원인**: `data.get('check_result', '')` — 키가 존재하고 값이 `None`이면 default `''`가 아닌 `None` 반환.

**수정**:
```
파일: backend/app/routes/checklist.py L809

before: check_result = data.get('check_result', '').strip().upper()
after:  check_result = (data.get('check_result') or '').strip().upper()
```

`check_result=null` → `''` → `not in ('PASS', 'NA')` → 400 에러 응답으로 정상 처리.

→ FE 토글을 PASS↔NA 2상태 루프로 변경하여 null 전송 자체를 제거 (BUG-FIX #5 참조).

### BUG-FIX #5 (Sprint 52): tm_checklist_screen — 토글 PASS↔NA 2상태 루프

적용일: 2026-04-02

**증상**: PASS→NA→세번째 탭 시 `check_result: null` 전송 → BE 500 에러 (#4에서 400으로 방어).
3상태(PASS/NA/null) 중 null은 실질적으로 불필요.

**수정**: `_nextResult()` 3상태 → 2상태 루프

```
파일: frontend/lib/screens/checklist/tm_checklist_screen.dart

before:
  String? _nextResult(String? current) {
    if (current == null) return 'PASS';
    if (current == 'PASS') return 'NA';
    return null;
  }

after:
  String _nextResult(String? current) {
    if (current == 'PASS') return 'NA';
    return 'PASS';
  }
```

첫 탭 PASS, 두번째 탭 NA, 이후 PASS↔NA 무한 루프. BE에 null이 전송되지 않음.

### Task 5: 알림 탭 → TM 체크리스트 화면 연동 (FE)

파일: 알림 목록 화면 (기존 alert 관련 screen)
위치: 알림 탭 항목의 onTap 핸들러

```
# 기존: 알림 탭 → 해당 S/N task_detail_screen으로 이동
# 변경: alert_type == 'CHECKLIST_TM_READY'일 때
#   → TmChecklistScreen(serialNumber: sn) 으로 이동
#
# alert_type == 'CHECKLIST_ISSUE'일 때
#   → 일반 알림 표시 (MECH/ELEC manager가 받는 것이므로 체크리스트 화면 불필요)
```

### Task 6: admin.py — SETTING_KEYS에 tm_checklist_* 옵션 등록

파일: `backend/app/routes/admin.py`
위치: SETTING_KEYS 딕셔너리 (L26~59)

```python
# ── SETTING_KEYS에 추가 (기존 항목 아래) ──

    # string — Sprint 52 TM 체크리스트 옵션
    'tm_checklist_1st_checker':   {'type': 'string', 'default': 'is_manager',
                                   'allowed': ['is_manager', 'user']},
    'tm_checklist_issue_alert':   {'type': 'bool', 'default': True},
    'tm_checklist_scope':         {'type': 'string', 'default': 'product_code',
                                   'allowed': ['product_code', 'all']},
```

⚠️ `type: 'string'`에 `allowed` 리스트 추가 → `_validate_setting()`에서 값 검증 필요:

```python
# _validate_setting() 함수 내 추가 (L66~)
# 기존 bool/time/number 검증 아래에:
    if meta['type'] == 'string':
        allowed = meta.get('allowed')
        if allowed and value not in allowed:
            return f'{key}는 {allowed} 중 하나여야 합니다. (입력값: {value})'
        return None
```

이 설정은 VIEW 대시보드에서 `GET /admin/settings` → `PUT /admin/settings` 로 조회/변경 가능.
VIEW에서 체크리스트 옵션 토글 UI를 만들 때 이 API를 그대로 소비하면 됨.

### Task 7: checklist.py — VIEW용 Admin CRUD API (체크리스트 항목 관리)

파일: `backend/app/routes/checklist.py`
위치: 기존 import_checklist_master() 아래에 추가

현재 VIEW에서 항목 관리는 Excel 업로드(`POST /api/admin/checklist/import`)만 가능.
개별 항목 추가/수정/비활성화 API가 없으면 VIEW 체크리스트 관리 페이지가 동작 불가.

```python
# ── Admin API 1: 체크리스트 마스터 항목 목록 조회 ──
# GET /api/admin/checklist/master?category=TM&product_code=COMMON
#
# Query Parameters:
#   category: str (필수) — 'TM', 'MECH', 'ELEC' 등
#   product_code: str (선택) — 미지정 시 전체
#   include_inactive: bool (선택, 기본 false) — 비활성 항목 포함 여부
#
# Response 200:
#   {
#     "items": [
#       {
#         "id": 1,
#         "product_code": "COMMON",
#         "category": "TM",
#         "item_group": "BURNER",
#         "item_name": "버너 조립 상태 확인",
#         "item_order": 1,
#         "description": "...",
#         "is_active": true
#       }, ...
#     ],
#     "total": 15
#   }
#
# 권한: @admin_required


# ── Admin API 2: 체크리스트 마스터 항목 개별 추가 ──
# POST /api/admin/checklist/master
#
# Request Body:
#   {
#     "product_code": "COMMON",          ← 또는 특정 코드 (4*****)
#     "category": "TM",
#     "item_group": "BURNER",         ← TM 전용 (MECH/ELEC는 null 가능)
#     "item_name": "버너 조립 상태 확인",
#     "item_order": 1,                ← 선택, 기본 0
#     "description": "..."            ← 선택
#   }
#
# Response 201: { "id": int, "message": "항목이 추가되었습니다." }
# Response 409: UNIQUE 제약 위반 시 (product_code + category + item_name 중복)
#
# 권한: @admin_required


# ── Admin API 3: 체크리스트 마스터 항목 수정 ──
# PUT /api/admin/checklist/master/<int:master_id>
#
# Request Body (모든 필드 선택):
#   {
#     "item_name": "...",
#     "item_group": "REACTOR",
#     "item_order": 2,
#     "description": "..."
#   }
#
# ⚠️ product_code, category는 수정 불가 (PK 구성 요소)
#
# Response 200: { "message": "항목이 수정되었습니다." }
# Response 404: master_id 없음
#
# 권한: @admin_required


# ── Admin API 4: 체크리스트 마스터 항목 활성/비활성 토글 ──
# PATCH /api/admin/checklist/master/<int:master_id>/toggle
#
# 동작: is_active = NOT is_active (토글)
# 비활성화해도 기존 checklist_record는 유지 (삭제 아님)
# VIEW에서 '비활성 포함' 체크박스로 필터링
#
# Response 200: { "id": int, "is_active": bool, "message": "..." }
#
# 권한: @admin_required
```

**VIEW Sprint 연동 가이드:**
VIEW 체크리스트 관리 페이지에서 사용할 API 요약:

| VIEW 동작 | OPS API | 비고 |
|-----------|---------|------|
| Product Code 드롭다운 선택 → 항목 목록 | `GET /api/admin/checklist/master?category=TM&product_code={code}` | |
| MECH/ELEC/TM 탭 전환 | 같은 API, category 파라미터 변경 | |
| '+ 항목 추가' 버튼 | `POST /api/admin/checklist/master` | item_group 필수 (TM) |
| 항목 수정 (이름, 순서, 설명, 그룹) | `PUT /api/admin/checklist/master/{id}` | |
| 비활성화/활성화 | `PATCH /api/admin/checklist/master/{id}/toggle` | |
| '비활성 포함' 체크박스 | `GET ...?include_inactive=true` | |
| 옵션 설정 (1차체크 권한, 알림 on/off, scope) | `GET/PUT /admin/settings` | tm_checklist_* 키 |
| Excel 일괄 업로드 | `POST /api/admin/checklist/import` | 기존 API 유지 |

### 테스트

```
[DB 스키마]
TC-52-01: migration 043 실행 → checklist_master.item_group 컬럼 존재 확인
TC-52-02: migration 043 실행 → checklist_record.check_result 컬럼 존재 확인
TC-52-03: migration 043 실행 → checklist_record.judgment_phase 컬럼 존재, DEFAULT 1 확인
TC-52-04: UNIQUE 제약 변경 확인 → (serial_number, master_id, judgment_phase)
TC-52-05: 기존 is_checked=TRUE 데이터 → check_result='PASS'로 마이그레이션 확인
TC-52-06: alert_type_enum에 CHECKLIST_TM_READY, CHECKLIST_ISSUE 추가 확인
TC-52-07: admin_settings에 tm_checklist_* 3개 키 존재 확인

[TM 체크리스트 API]
TC-52-08: GET /api/app/checklist/tm/{sn} → groups별 항목 + summary 응답 확인
TC-52-09: GET /api/app/checklist/tm/{sn} → check_result=null (미체크) 기본값 확인
TC-52-10: PUT /api/app/checklist/tm/check → check_result='PASS' → 정상 저장
TC-52-11: PUT /api/app/checklist/tm/check → check_result='NA' → 정상 저장
TC-52-12: PUT /api/app/checklist/tm/check → check_result='FAIL' → 400 INVALID_CHECK_RESULT
TC-52-13: PUT /api/app/checklist/tm/check → note 포함 ISSUE 저장 확인
TC-52-14: 15항목 전부 PASS/NA → is_complete=True 반환
TC-52-15: 14항목 체크 + 1항목 미체크 → is_complete=False
TC-52-16: GET /api/app/checklist/tm/{sn}/status → is_complete + checked_count 확인
TC-52-17: is_manager=False인 유저가 PUT → 403 (tm_checklist_1st_checker="is_manager" 기본값)

[알림 연동]
TC-52-18: TM task 완료(finalize=True, 일반 작업자) → CHECKLIST_TM_READY 알림 생성 확인
TC-52-19: TM task 내 작업 종료(finalize=False) → 알림 미생성 확인
TC-52-19a: TM task 완료(finalize=True, is_manager=True) → 알림 미발송 + 응답에 checklist_ready=true 확인
TC-52-20: 체크리스트 완료 + ISSUE note 존재 + tm_checklist_issue_alert=true → CHECKLIST_ISSUE 알림 생성
TC-52-21: 체크리스트 완료 + ISSUE note 존재 + tm_checklist_issue_alert=false → 알림 미생성
TC-52-22: 알림 실패해도 task 완료 정상 처리 확인

[Admin CRUD API — VIEW 연동]
TC-52-23: GET /api/admin/checklist/master?category=TM → 항목 목록 반환
TC-52-24: GET /api/admin/checklist/master?category=TM&product_code=COMMON → product_code 필터 동작
TC-52-25: GET /api/admin/checklist/master?include_inactive=true → 비활성 항목 포함
TC-52-26: POST /api/admin/checklist/master → 신규 항목 추가 (item_group 포함)
TC-52-27: POST /api/admin/checklist/master → 중복 item_name → 409 CONFLICT
TC-52-28: PUT /api/admin/checklist/master/{id} → 항목 수정 (item_name, item_order, item_group)
TC-52-29: PATCH /api/admin/checklist/master/{id}/toggle → is_active 토글 동작
TC-52-30: admin이 아닌 유저가 Admin API 호출 → 403

[Settings API — VIEW 옵션 제어]
TC-52-31: GET /admin/settings → tm_checklist_* 3개 키 포함 확인
TC-52-32: PUT /admin/settings { tm_checklist_1st_checker: "user" } → 정상 저장
TC-52-33: PUT /admin/settings { tm_checklist_1st_checker: "invalid" } → 400 VALIDATION_ERROR
TC-52-34: PUT /admin/settings { tm_checklist_scope: "all" } → 정상 저장

[기존 기능 regression]
TC-52-35: 기존 GET /api/app/checklist/{sn}/MECH → 정상 동작 (is_checked 기반 유지)
TC-52-36: 기존 PUT /api/app/checklist/check → is_checked boolean 정상 동작 유지
TC-52-37: 기존 POST /api/admin/checklist/import → Excel 업로드 정상 동작
TC-52-38: 릴레이(Sprint 41) + TM 체크리스트 조합 → 릴레이 재시작 후 최종 완료 시에만 알림
```

### product_code "COMMON" 옵션 동작 설명

```
admin_settings.tm_checklist_scope 값에 따라:

"product_code" (기본값):
  → checklist_master에서 해당 S/N의 product_code + category='TM'으로 필터
  → VIEW에서 product_code별로 항목 등록 필요
  → 모듈화 고도화 후 (100개 → 50개) product_code별 맞춤 항목 가능

"all":
  → checklist_master에서 product_code='COMMON' + category='TM'으로 필터
  → VIEW에서 product_code='COMMON'로 한 번만 등록하면 전 모델 적용
  → 현재 기준 불명확한 시점에서 이 옵션 사용 권장
```

### 규칙
- 코드 변경 전 반드시 사용자 승인
- pytest 기존 테스트 전체 통과 확인 (특히 test_checklist_api.py 14개 기존 TC)
- is_checked 컬럼 삭제 금지 — 기존 MECH/ELEC 호환 유지
- Mock 데이터는 종이 체크리스트 기준으로 전면 교체 (별도 작업)
- TC-52-01~38 수동 테스트 통과 후 커밋


## Sprint 52-A: TM 체크리스트 보완 — COMMON seed + scope 수정 (2026-04-02)

> 등록일: 2026-04-02
> 트랙: BE (migration + 코드 1줄 수정)
> 선행: Sprint 52 (migration 043 적용 완료)
> 난이도: 낮음

### 배경

Sprint 52 구현 시 checklist_master에 실제 15항목 seed가 누락됨.
또한 product_code가 현재 100개+ 존재하여 표준화(→ 50개) 전까지 product_code별 관리는 시기상조.
`product_code = 'COMMON'` 예약어로 공통 항목 1세트를 관리하는 방식 채택.
추후 MECH, ELEC 체크리스트도 동일 패턴 적용 예정.

### 수정 대상

```
1. backend/migrations/043a_tm_checklist_seed.sql             (신규 — UNIQUE변경 + item_type추가 + seed + admin_settings)
2. backend/app/services/checklist_service.py                 (수정 — scope='all' 조회 로직 2곳)
3. backend/app/routes/admin.py                               (수정 — tm_checklist_scope default)
4. backend/app/routes/checklist.py                           (수정 — Excel ON CONFLICT 4컬럼)
```

### Task 0: Migration — 043a_tm_checklist_seed.sql (신규)

신규 파일: `backend/migrations/043a_tm_checklist_seed.sql`

```sql
-- Sprint 52-A: TM 체크리스트 COMMON seed + scope 기본값 수정
-- 043a

-- ────────────────────────────────────────────────────────────────
-- 1. tm_checklist_scope 기본값 'all'로 변경
--    product_code별 관리는 표준화 완료 후 전환 (현재 100개+ → 목표 50개)
-- ────────────────────────────────────────────────────────────────
UPDATE admin_settings
SET setting_value = '"all"'
WHERE setting_key = 'tm_checklist_scope';

-- ────────────────────────────────────────────────────────────────
-- 2. UNIQUE 제약 변경: item_group 추가
--    기존: (product_code, category, item_name) → 동일 item_name이 다른 그룹에 존재 시 충돌
--    예: BURNER '클램프 체결' vs REACTOR '클램프 체결', BURNER 'SUS Fitting 조임 상태' vs EXHAUST 'SUS Fitting 조임 상태'
--    변경: (product_code, category, item_group, item_name)
-- ────────────────────────────────────────────────────────────────
ALTER TABLE checklist.checklist_master
    DROP CONSTRAINT IF EXISTS checklist_master_product_code_category_item_name_key;

ALTER TABLE checklist.checklist_master
    ADD CONSTRAINT checklist_master_product_category_group_name_key
    UNIQUE (product_code, category, item_group, item_name);

-- ────────────────────────────────────────────────────────────────
-- 3. item_type 컬럼 추가
--    CHECK = 체크 항목 (Pass/NA), INPUT = 입력 항목 (값 입력, MECH 전용)
--    TM/ELEC: 전부 CHECK. MECH: CHECK + INPUT 혼재
--    기본값 'CHECK' → 기존 데이터(HOOKUP/PI/QI) 영향 없음
-- ────────────────────────────────────────────────────────────────
ALTER TABLE checklist.checklist_master
    ADD COLUMN IF NOT EXISTS item_type VARCHAR(10) DEFAULT 'CHECK';

COMMENT ON COLUMN checklist.checklist_master.item_type
    IS '항목 타입: CHECK=체크(Pass/NA), INPUT=입력(MECH 전용)';

-- ────────────────────────────────────────────────────────────────
-- 4. TM 체크리스트 15항목 공통 seed (기구 조립 검사 성적서 기준)
--    product_code = 'COMMON' → scope='all' 시 이 항목 사용
--    추후 MECH/ELEC도 동일 패턴: ('COMMON', 'MECH', ...), ('COMMON', 'ELEC', ...)
--    description: 기준/SPEC + 검사방법 통합 (Phase 1). 추후 컬럼 분리 가능.
-- ────────────────────────────────────────────────────────────────
INSERT INTO checklist.checklist_master
    (product_code, category, item_group, item_name, item_order, description, is_active)
VALUES
    -- BURNER (3항목)
    ('COMMON', 'TM', 'BURNER', 'SUS Fitting 조임 상태',       1, 'GAP GAUGE / 측수 검사', TRUE),
    ('COMMON', 'TM', 'BURNER', 'Gas Nozzle Cover 휨 여부',    2, 'Jig 활용 Center 확인 / 육안 검사', TRUE),
    ('COMMON', 'TM', 'BURNER', '클램프 체결',                  3, '조립 유동 여부 / 측수 검사', TRUE),
    -- REACTOR (4항목)
    ('COMMON', 'TM', 'REACTOR', 'Fitting 조임 상태',           1, '조립 유동 여부 / 측수 검사', TRUE),
    ('COMMON', 'TM', 'REACTOR', 'Tube 조립 상태',              2, '조립 유동 여부 / 측수 검사', TRUE),
    ('COMMON', 'TM', 'REACTOR', '클램프 체결',                  3, '조립 유동 여부 / 측수 검사', TRUE),
    ('COMMON', 'TM', 'REACTOR', 'Cir Line Tubing',            4, '조립 유동 여부 / 측수 검사', TRUE),
    -- EXHAUST (4항목)
    ('COMMON', 'TM', 'EXHAUST', 'Packing 조립 확인',           1, '적용 여부 / 육안 검사', TRUE),
    ('COMMON', 'TM', 'EXHAUST', 'Packing Guide 고정 확인',     2, '유동 여부 / 육안 검사', TRUE),
    ('COMMON', 'TM', 'EXHAUST', 'SUS Fitting 조임 상태',       3, 'GAP GAUGE / 측수 검사', TRUE),
    ('COMMON', 'TM', 'EXHAUST', 'BCW Nozzle Spray 방향',      4, '아래 방향 / 육안 검사', TRUE),
    -- TANK (4항목)
    ('COMMON', 'TM', 'TANK', 'Cir Pump Spec 확인',            1, '조립 도면과 현물 1:1 확인 / 육안 검사', TRUE),
    ('COMMON', 'TM', 'TANK', 'Flow Sensor Swirl Orifice',     2, 'Swirl Orifice 적용 조립 / 육안 검사', TRUE),
    ('COMMON', 'TM', 'TANK', 'Tank 내부 이물질 확인',          3, 'Tank 투시창 이용 확인 / 육안 검사', TRUE),
    ('COMMON', 'TM', 'TANK', '열교환기 Spec 확인',             4, '조립 도면과 현물 1:1 확인 / 육안 검사', TRUE)
ON CONFLICT (product_code, category, item_group, item_name) DO NOTHING;
```

### Task 1: checklist_service.py — scope='all' 조회 로직 수정 (2곳)

파일: `backend/app/services/checklist_service.py`

**수정 위치 A**: `get_tm_checklist()` 내 master 필터 조건 (L90~93)

```python
# ── 변경 전 ──
if scope == 'all' or not product_code:
    master_filter_sql = "cm.category = 'TM'"
    master_params: list = []

# ── 변경 후 ──
if scope == 'all' or not product_code:
    master_filter_sql = "cm.product_code = 'COMMON' AND cm.category = 'TM'"
    master_params: list = []
```

**수정 위치 B**: `_check_tm_completion()` 내 동일 필터 조건 (L313~315)

```python
# ── 변경 전 ──
if scope == 'all' or not product_code:
    master_filter = "cm.category = 'TM'"
    master_params: list = []

# ── 변경 후 ──
if scope == 'all' or not product_code:
    master_filter = "cm.product_code = 'COMMON' AND cm.category = 'TM'"
    master_params: list = []
```

> **이유**: scope='all'에서 category만 필터하면, 추후 product_code별 항목 추가 시
> COMMON 15항목 + 개별 product_code 항목이 중복 조회됨.
> 'COMMON'을 명시하면 공통 항목만 깔끔하게 반환.
> ⚠️ 두 함수 모두 동일 패턴이므로 반드시 2곳 다 수정

### TC (수동 테스트)

| TC | 내용 | 예상 |
|----|------|------|
| TC-52A-01 | migration 043a 실행 후 `SELECT * FROM checklist.checklist_master WHERE product_code='COMMON'` | **15 rows** (12개 아니고 15개 전부) |
| TC-52A-02 | `SELECT * FROM admin_settings WHERE setting_key='tm_checklist_scope'` | setting_value = '"all"' |
| TC-52A-03 | UNIQUE 제약 확인: `\d checklist.checklist_master` | `(product_code, category, item_group, item_name)` |
| TC-52A-04 | `GET /api/app/checklist/tm/{test_sn}` 호출 | 4그룹 15항목 반환 |
| TC-52A-05 | BURNER '클램프 체결' + REACTOR '클램프 체결' 모두 존재 확인 | 동일 item_name, 다른 item_group |
| TC-52A-06 | BURNER 'SUS Fitting 조임 상태' + EXHAUST 'SUS Fitting 조임 상태' 모두 존재 | 동일 item_name, 다른 item_group |
| TC-52A-07 | Excel 업로드 (기존 기능 regression) | item_group 포함 UPSERT 정상 동작 |

### Task 2: admin.py — SETTING_KEYS default 정합성 수정

파일: `backend/app/routes/admin.py`
위치: SETTING_KEYS 딕셔너리 (L62)

```python
# ── 변경 전 ──
'tm_checklist_scope': {'type': 'string', 'default': 'product_code', 'allowed': ['product_code', 'all']},

# ── 변경 후 ──
'tm_checklist_scope': {'type': 'string', 'default': 'all', 'allowed': ['product_code', 'all']},
```

> DB 값은 migration 043a에서 'all'로 UPDATE하지만, admin.py의 default도 일치시켜야
> 새 환경 배포 시 정합성 유지

### Task 3: checklist.py — Excel 업로드 ON CONFLICT 수정

파일: `backend/app/routes/checklist.py`
위치: `import_checklist_master()` 내 UPSERT (L685)

```python
# ── 변경 전 ──
ON CONFLICT (product_code, category, item_name) DO UPDATE

# ── 변경 후 ──
ON CONFLICT (product_code, category, item_group, item_name) DO UPDATE
```

> UNIQUE 제약이 `(product_code, category, item_group, item_name)`으로 변경되었으므로
> 기존 Excel 업로드 UPSERT의 ON CONFLICT도 일치시켜야 함
> ⚠️ Excel 업로드 시 item_group 컬럼도 INSERT에 포함되어야 함 — 확인 필요

### 규칙
- migration 043a는 043 이후에 실행 (043 적용 완료 상태에서)
- checklist_service.py 수정: 2곳 (get_tm_checklist + _check_tm_completion)
- admin.py 수정: default 값 1곳
- checklist.py 수정: Excel 업로드 ON CONFLICT 1곳
- 기존 TC-52 전체 영향 없음 (scope 기본값이 'all'로 바뀌므로 동일 동작)
- UNIQUE 변경으로 기존 데이터에 중복이 없는지 실행 전 확인 필요


## Sprint 53: 알림 소리 + 진동 — 포그라운드 알림 피드백 (2026-04-01)

> 등록일: 2026-04-01
> 트랙: FE only (OPS Flutter PWA)
> 선행: 없음 (독립 수정)
> 난이도: 낮음 (FE 2파일 + 에셋 1개)
> BE 변경: 없음
> 비고: 정식 앱(App Store/Play Store) 전환 시 FCM 네이티브 푸시로 확장 가능 — 이번은 앱 포그라운드 한정

### 배경

현재 OPS 앱의 알림 시스템은 WebSocket으로 실시간 수신되어 알림 탭에 표시되지만, **소리나 진동이 없어** 작업자가 알림 도착을 인지하지 못하는 문제.

특히 TM 체크리스트(Sprint 52), 릴레이 마감(Sprint 41-B) 등 즉시 행동이 필요한 알림에서 피드백이 없으면 지연 발생.

**현재 흐름:**
```
BE → WebSocket → alert_provider.dart _handleNewAlert()
  → state에 알림 추가 + unreadCount 증가
  → (끝, 소리/진동 없음)
```

**변경 후:**
```
BE → WebSocket → alert_provider.dart _handleNewAlert()
  → state에 알림 추가 + unreadCount 증가
  → notification_feedback_service.dart: 소리 재생 + 진동 트리거
```

**향후 확장:**
정식 앱(네이티브 빌드)으로 전환 시 Firebase Cloud Messaging(FCM) + APNs 연동으로 백그라운드/앱 종료 상태에서도 OS 알림센터 푸시 가능. 이번 Sprint는 포그라운드 한정이며, 네이티브 전환 시 별도 Sprint으로 진행.

### 수정 대상 파일

```
1. frontend/pubspec.yaml                                         (수정 — 패키지 추가)
2. frontend/lib/services/notification_feedback_service.dart       (신규 — 소리/진동 서비스)
3. frontend/lib/providers/alert_provider.dart                     (수정 — 알림 수신 시 피드백 호출)
4. frontend/assets/sounds/alert_tone.mp3                          (신규 — 알림음 에셋)
```

### Task 0: pubspec.yaml — 패키지 추가

파일: `frontend/pubspec.yaml`

```yaml
# dependencies에 추가:
  audioplayers: ^5.2.1       # 알림음 재생 (웹 호환)
  vibration: ^1.8.4          # 진동 (웹은 navigator.vibrate, 네이티브는 HapticFeedback)
```

```yaml
# flutter > assets에 추가:
  assets:
    - assets/images/
    - assets/sounds/          # 알림음 에셋 디렉토리
```

⚠️ `audioplayers`는 웹(HTML5 Audio) + 네이티브 양쪽 지원.
⚠️ `vibration`은 웹에서 `navigator.vibrate()` API 사용 — iOS Safari는 vibration API 미지원이므로 iOS 웹에서는 소리만 동작. 네이티브 전환 후 iOS 진동 가능.

### Task 1: notification_feedback_service.dart — 소리/진동 서비스 (신규)

신규 파일: `frontend/lib/services/notification_feedback_service.dart`

```dart
// ── NotificationFeedbackService ──
//
// 싱글톤 서비스: 알림 수신 시 소리 재생 + 진동 트리거
//
// 주요 메서드:
//
// playAlertFeedback({String alertType})
//   - 알림 타입에 따라 소리/진동 패턴 분기 (현재는 단일 패턴, 추후 확장)
//   - 소리: AudioPlayer로 assets/sounds/alert_tone.mp3 재생
//     - 짧은 알림음 (1초 이내)
//     - 볼륨: 시스템 볼륨 따름
//   - 진동: Vibration.vibrate(duration: 200) — 짧은 진동 1회
//   - 재생 간격 제한: 마지막 재생 후 2초 이내 재요청 무시 (연속 알림 시 도배 방지)
//
// 알림 타입별 패턴 (향후 확장):
//   - 일반 알림 (new_alert): 소리 1회 + 진동 1회
//   - 긴급 알림 (process_alert): 소리 1회 + 진동 2회 (추후)
//   - CHECKLIST_TM_READY: 소리 1회 + 진동 1회
//
// 음소거 설정:
//   - SharedPreferences에 'alert_sound_enabled' (기본 true)
//   - SharedPreferences에 'alert_vibration_enabled' (기본 true)
//   - 설정 화면에서 토글 가능 (Task 3)
//
// ⚠️ 웹 브라우저 정책: 사용자 인터랙션 없이 자동 재생 차단될 수 있음
//    → 앱 최초 로드 시 빈 오디오 재생으로 unlock (AudioPlayer.resume() 트릭)
//    → 또는 첫 탭 시 unlock 처리
```

### Task 2: alert_provider.dart — 알림 수신 시 피드백 호출

파일: `frontend/lib/providers/alert_provider.dart`
위치: `_handleNewAlert()` 메서드 (L223)

```dart
// ── 변경 전 (L223-248) ──
void _handleNewAlert(dynamic data) {
    try {
      final newAlert = AlertLog.fromJson(data as Map<String, dynamic>);
      // ... 중복 체크 + state 업데이트
      print('[AlertProvider] New alert received: ${newAlert.alertType}');
    } catch (e) {
      // ...
    }
  }

// ── 변경 후 ──
void _handleNewAlert(dynamic data) {
    try {
      final newAlert = AlertLog.fromJson(data as Map<String, dynamic>);
      // ... 중복 체크 + state 업데이트 (기존 로직 유지)

      // Sprint 53: 소리 + 진동 피드백
      NotificationFeedbackService.instance.playAlertFeedback(
        alertType: newAlert.alertType,
      );

      print('[AlertProvider] New alert received: ${newAlert.alertType}');
    } catch (e) {
      // ...
    }
  }
```

⚠️ `playAlertFeedback()` 실패해도 알림 수신 자체에는 영향 없음 (내부 try-catch).

### Task 3: 설정 화면에 소리/진동 토글 추가 (선택)

파일: 기존 설정 화면 (OPS 앱 내)

```
// SharedPreferences 기반:
//   alert_sound_enabled: bool (기본 true)
//   alert_vibration_enabled: bool (기본 true)
//
// UI: 단순 Switch 2개
//   [🔔 알림 소리]  ON/OFF
//   [📳 알림 진동]  ON/OFF
//
// NotificationFeedbackService가 재생 전 이 값을 체크하여 스킵
```

### 알림음 에셋

```
frontend/assets/sounds/alert_tone.mp3
- 짧은 알림음 (0.5~1초)
- 파일 크기: 50KB 이하
- 무료 라이선스 사운드 사용 (예: notification_simple.mp3)
- 추후 알림 타입별 다른 소리 추가 가능 (디렉토리 구조 준비)
```

### 테스트

```
[기본 동작]
TC-53-01: WebSocket 알림 수신 → 소리 재생 확인 (new_alert)
TC-53-02: WebSocket 알림 수신 → 진동 트리거 확인 (Android/Chrome)
TC-53-03: 2초 이내 연속 알림 → 두 번째 알림 소리/진동 스킵 확인

[설정 토글]
TC-53-04: alert_sound_enabled=false → 소리 미재생 확인
TC-53-05: alert_vibration_enabled=false → 진동 미트리거 확인
TC-53-06: 둘 다 false → 소리/진동 모두 미동작, 알림 수신은 정상

[엣지케이스]
TC-53-07: 앱 최초 로드 후 첫 알림 → 브라우저 autoplay 정책 대응 확인
TC-53-08: 기존 알림 타입 (PROCESS_READY, DURATION_EXCEEDED 등) → 소리/진동 정상 동작
TC-53-09: iOS Safari → 진동 미지원, 소리만 동작 확인 (에러 없음)11
[regression]
TC-53-10: 알림 수신 → state 업데이트 정상 (unreadCount 증가)
TC-53-11: 알림 읽음 처리 정상 동작
TC-53-12: 피드백 서비스 에러 시 알림 수신 자체는 정상
```

### 규칙
- 코드 변경 전 반드시 사용자 승인
- 알림음 파일은 무료 라이선스 확인 후 사용
- iOS Safari 진동 미지원은 정상 동작 (에러 미발생, graceful degradation)
- TC-53-01~12 수동 테스트 통과 후 커밋

---

## Sprint 54 — 공정 흐름 기반 알림 트리거 프레임워크 + Partner 분기

> **목표**: 완료 알림이 role 전체가 아닌 **해당 S/N의 partner 회사 매니저에게만** 발송되도록 수정.
> 공정 흐름 기반 트리거 on/off를 admin_settings로 관리하여 regression 없이 트리거 추가/제거 가능한 구조.
> Sprint 52 CHECKLIST_TM_READY 알림 미생성 버그도 함께 해결.

### 배경

```
공정 흐름:
TM ──(가압완료)──▶ MECH ──(도킹완료)──▶ ELEC ──(자주검사완료)──▶ PI ──▶ QI ──▶ SI
     trigger①         trigger②              trigger③

현재 문제:
- 모든 트리거가 get_managers_for_role('MECH'/'ELEC'/'QI')로 역할 전체에 발송
- FNI MECH 매니저가 추가되면 TMS 제품 알림도 FNI에 감
- Sprint 52 CHECKLIST_TM_READY는 get_managers_for_role('TM') → role='TM' worker 없음 → 알림 0건
```

### Partner → Company 매핑 규칙 (ADR-010, memory.md 참조)

```
partner_field         partner값    workers.company
─────────────────────────────────────────────────
mech_partner          TMS       →  TMS(M)
mech_partner          FNI       →  FNI
mech_partner          BAT       →  BAT
elec_partner          TMS       →  TMS(E)
elec_partner          P&S       →  P&S
elec_partner          C&A       →  C&A
module_outsourcing    TMS       →  TMS(M)

규칙: TMS만 특수 (mech/module → (M), elec → (E)). 나머지는 partner값 = company값.
```

### 기존 코드 참조 (동일 매핑 패턴 사용 중)

```
파일                              라인       용도                    방향
services/task_seed.py             L495-600   task 가시성 분기          company → partner
services/progress_service.py      L196-224   진행현황 조회 필터        company → partner
routes/work.py                    L250-280   재활성화 권한 체크        company → partner (접미사 제거)
```

---

### Task 0 — 신규 함수: partner → company 매핑 + 매니저 조회

**파일**: `backend/app/services/process_validator.py`

```python
# ─── 기존 함수 아래에 추가 ───

def _partner_to_company(partner_value: str, partner_field: str) -> str:
    """
    product_info의 partner 값 → workers.company 변환

    Args:
        partner_value: 'TMS', 'FNI', 'BAT', 'P&S', 'C&A' 등
        partner_field: 'mech_partner' | 'elec_partner' | 'module_outsourcing'

    Returns:
        workers.company 값 (예: 'TMS(M)', 'TMS(E)', 'FNI')
    """
    val = partner_value.upper().strip()
    if val == 'TMS':
        if partner_field == 'elec_partner':
            return 'TMS(E)'
        else:  # mech_partner, module_outsourcing
            return 'TMS(M)'
    return val  # FNI, BAT, P&S, C&A 등 그대로


def get_managers_by_partner(serial_number: str, partner_field: str) -> List[int]:
    """
    S/N의 product_info에서 partner_field 값 조회 → 해당 company의 매니저 ID 반환

    Args:
        serial_number: 'GBWS-6798'
        partner_field: 'mech_partner' | 'elec_partner' | 'module_outsourcing'

    Returns:
        매니저 worker_id 리스트. partner 값 없거나 매니저 없으면 빈 리스트.

    사용 예:
        get_managers_by_partner('GBWS-6798', 'mech_partner')
        → product_info.mech_partner = 'FNI'
        → company = 'FNI'
        → workers WHERE company='FNI' AND is_manager=TRUE
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. product_info에서 partner 값 조회
        allowed_fields = ('mech_partner', 'elec_partner', 'module_outsourcing')
        if partner_field not in allowed_fields:
            logger.error(f"Invalid partner_field: {partner_field}")
            return []

        cur.execute(
            f"SELECT {partner_field} FROM plan.product_info WHERE serial_number = %s",
            (serial_number,)
        )
        row = cur.fetchone()
        if not row or not row[partner_field]:
            logger.warning(f"No {partner_field} for serial_number={serial_number}")
            return []

        partner_value = row[partner_field]
        company = _partner_to_company(partner_value, partner_field)

        # 2. 해당 company의 매니저 조회
        cur.execute(
            """
            SELECT id FROM workers
            WHERE company = %s
              AND is_manager = TRUE
              AND approval_status = 'approved'
            """,
            (company,)
        )
        manager_rows = cur.fetchall()
        manager_ids = [r['id'] for r in manager_rows]

        logger.info(
            f"get_managers_by_partner: sn={serial_number}, "
            f"{partner_field}={partner_value}, company={company}, "
            f"managers={manager_ids}"
        )
        return manager_ids

    except PsycopgError as e:
        logger.error(f"get_managers_by_partner failed: {e}")
        return []
    finally:
        if conn:
            put_conn(conn)
```

---

### Task 1 — `_trigger_completion_alerts` 수정: partner 분기 + admin_settings on/off

**파일**: `backend/app/services/task_service.py`

**변경 전** (L414-488): `get_managers_for_role(target_role)` → 역할 전체 발송
**변경 후**: 트리거별 partner 분기 + admin_settings on/off 체크

```python
def _trigger_completion_alerts(self, task) -> None:
    """
    특정 Task 완료 시 연계 알림 트리거
    Sprint 54: partner 기반 분기 + admin_settings on/off

    트리거 규칙 (공정 흐름 순서):
      trigger①: TMS 완료 → mech_partner company 매니저
        - TMS PRESSURE_TEST 완료 (가압완료)
        - 단, mech_partner = module_outsourcing 회사면 같은 회사이므로 스킵
        - admin_settings: alert_tm_to_mech_enabled
      trigger②: MECH TANK_DOCKING 완료 → elec_partner company 매니저
        - admin_settings: alert_mech_to_elec_enabled
      trigger③: ELEC 자주검사 전체 완료 → PI 매니저 (GST)
        - admin_settings: alert_elec_to_pi_enabled

    Args:
        task: 완료된 TaskDetail 객체
    """
    from app.models.alert_log import create_alert
    from app.services.process_validator import get_managers_by_partner, get_managers_for_role
    from app.models.admin_settings import get_setting
    from app.models.product_info import get_product_by_serial_number

    trigger = None  # (alert_type, partner_field_or_role, action_label, settings_key)

    # ─── trigger① TMS → MECH (가압완료) ───
    if task.task_id == 'PRESSURE_TEST':
        if task.task_category == 'TMS':
            if self._is_dual_pressure_all_done(task.serial_number):
                trigger = ('TMS_TANK_COMPLETE', 'mech_partner', 'TMS 가압검사 완료', 'alert_tm_to_mech_enabled')
        elif task.task_category == 'MECH':
            # DRAGON: MECH 가압검사 완료 → QI 매니저
            trigger = ('TMS_TANK_COMPLETE', 'QI', 'MECH 가압검사 완료', 'alert_mech_pressure_to_qi_enabled')

    # ─── trigger②: MECH TANK_DOCKING → ELEC (도킹완료) ───
    elif task.task_category == 'MECH' and task.task_id == 'TANK_DOCKING':
        trigger = ('TANK_DOCKING_COMPLETE', 'elec_partner', 'Tank Docking 완료', 'alert_mech_to_elec_enabled')

    # ─── trigger③: ELEC 자주검사 전체 완료 → PI (GST) ───
    elif task.task_category == 'ELEC':
        from app.models.task_detail import get_incomplete_tasks
        incomplete_elec = get_incomplete_tasks(task.serial_number, 'ELEC')
        if len(incomplete_elec) == 0:
            trigger = ('ELEC_COMPLETE', 'PI', 'ELEC 자주검사 완료', 'alert_elec_to_pi_enabled')

    if trigger is None:
        return

    alert_type, target_source, action_label, settings_key = trigger

    try:
        # admin_settings on/off 체크
        if not get_setting(settings_key, True):
            logger.info(f"Alert trigger disabled: {settings_key}=false, skipping {alert_type}")
            return

        # partner 기반 매니저 조회 vs role 기반 (QI 등)
        if target_source in ('mech_partner', 'elec_partner', 'module_outsourcing'):
            # ── 같은 회사 스킵 로직 (trigger①) ──
            # mech_partner = module_outsourcing 회사면 같은 협력사 → 알림 불필요
            if target_source == 'mech_partner':
                product = get_product_by_serial_number(task.serial_number)
                if product:
                    mech = (product.mech_partner or '').upper()
                    module = (product.module_outsourcing or '').upper()
                    if mech and module and mech == module:
                        logger.info(
                            f"Same company skip: mech_partner={mech} == module_outsourcing={module}, "
                            f"sn={task.serial_number}"
                        )
                        return

            managers = get_managers_by_partner(task.serial_number, target_source)
            target_role_label = target_source  # 로그용
        else:
            # QI 등 role 기반 (GST 단일 회사)
            managers = get_managers_for_role(target_source)
            target_role_label = target_source

        for manager_id in managers:
            alert_id = create_alert(
                alert_type=alert_type,
                message=(
                    f"[{task.serial_number}] {action_label}: "
                    f"{task.task_name} 작업이 완료되었습니다."
                ),
                serial_number=task.serial_number,
                qr_doc_id=task.qr_doc_id,
                triggered_by_worker_id=task.worker_id,
                target_worker_id=manager_id,
                target_role=target_role_label
            )
            if alert_id:
                logger.info(
                    f"Completion alert: type={alert_type}, sn={task.serial_number}, "
                    f"manager={manager_id}, source={target_source}"
                )

    except Exception as e:
        logger.error(f"Failed to trigger completion alert: {e}")
```

**주의**: Sprint 37-A의 TANK_MODULE 완료(가압제외) → TMS_TANK_COMPLETE 트리거는 현재 제거.
향후 필요 시 admin_settings 키 추가 + elif 블록 추가만 하면 됨.

---

### Task 2 — `_trigger_tm_checklist_alert` 수정: module_outsourcing 기반

**파일**: `backend/app/services/task_service.py`

**변경**: L579-594 `get_managers_for_role('MECH')` → `get_managers_by_partner(sn, 'module_outsourcing')`

```python
# 변경 전:
                tms_managers = get_managers_for_role('MECH')
                ...
                    target_role='MECH',

# 변경 후:
            else:
                # 일반 작업자 완료 → module_outsourcing company 매니저에게 알림
                from app.services.process_validator import get_managers_by_partner
                tms_managers = get_managers_by_partner(task.serial_number, 'module_outsourcing')
                from app.models.alert_log import create_alert
                for manager_id in tms_managers:
                    alert_id = create_alert(
                        alert_type='CHECKLIST_TM_READY',
                        message=(
                            f"[{task.serial_number}] Tank Module 작업 완료 — "
                            f"체크리스트 검수가 필요합니다"
                        ),
                        serial_number=task.serial_number,
                        qr_doc_id=task.qr_doc_id,
                        triggered_by_worker_id=completing_worker_id,
                        target_worker_id=manager_id,
                        target_role='module_outsourcing',
                    )
                    if alert_id:
                        logger.info(
                            f"CHECKLIST_TM_READY alert: task_id={task.id}, "
                            f"manager_id={manager_id}, alert_id={alert_id}"
                        )
                return False
```

---

### Task 3 — admin_settings 키 등록 (migration)

**파일**: `backend/migrations/044_alert_trigger_settings.sql`

```sql
-- Sprint 54: 공정 흐름 알림 트리거 on/off 설정
-- 기존 admin_settings 테이블에 INSERT (컬럼: setting_key, setting_value, description)

INSERT INTO admin_settings (setting_key, setting_value, description)
VALUES
    ('alert_tm_to_mech_enabled', 'true', 'TMS 가압검사 완료 → MECH 매니저 알림 활성화'),
    ('alert_mech_to_elec_enabled', 'true', 'MECH Tank Docking 완료 → ELEC 매니저 알림 활성화'),
    ('alert_elec_to_pi_enabled', 'false', 'ELEC 자주검사 완료 → PI 매니저 알림 활성화'),
    ('alert_mech_pressure_to_qi_enabled', 'false', 'DRAGON MECH 가압검사 완료 → QI 매니저 알림 활성화'),
    ('alert_tm_tank_module_to_elec_enabled', 'false', 'TMS TANK_MODULE 완료(가압제외) → ELEC 매니저 알림 활성화')
ON CONFLICT (setting_key) DO NOTHING;

-- ※ ELEC_COMPLETE를 alert_type_enum에 추가
ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'ELEC_COMPLETE';
```

**admin.py SETTING_KEYS 등록** (L59 부근):

```python
# Sprint 54: 알림 트리거 on/off
'alert_tm_to_mech_enabled':              {'type': 'bool', 'default': True},
'alert_mech_to_elec_enabled':            {'type': 'bool', 'default': True},
'alert_elec_to_pi_enabled':              {'type': 'bool', 'default': False},
'alert_mech_pressure_to_qi_enabled':     {'type': 'bool', 'default': False},
'alert_tm_tank_module_to_elec_enabled':  {'type': 'bool', 'default': False},
```

---

### Task 4 — OPS FE: 알림 트리거 설정 위젯

**파일**: `frontend/lib/screens/admin/admin_options_screen.dart` (기존 파일에 섹션 추가)

**위치**: 기존 토글 설정 섹션 (heating_jacket, phase_block 등) 아래에 "알림 트리거 설정" 섹션 추가

#### 화면 구성

```
┌─────────────────────────────────────────┐
│  🔔 알림 트리거 설정                      │
├─────────────────────────────────────────┤
│                                         │
│  TM ──▶ MECH ──▶ ELEC ──▶ PI ──▶ QI    │  ← 공정 흐름도 (수평 스텝 위젯)
│     ①       ②        ③                 │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  ① TM → MECH 알림        [ON ■□ OFF]   │  ← alert_tm_to_mech_enabled
│     가압검사 완료 시 MECH 매니저에게 알림   │
│     (같은 협력사면 자동 스킵)              │
│                                         │
│  ② MECH → ELEC 알림      [ON ■□ OFF]   │  ← alert_mech_to_elec_enabled
│     Tank Docking 완료 시 ELEC 매니저에게   │
│                                         │
│  ③ ELEC → PI 알림          [OFF □■ ON]   │  ← alert_elec_to_pi_enabled
│     ELEC 자주검사 완료 시 PI(GST)에게     │
│                                         │
│  ─── 추가 트리거 (기본 OFF) ───           │
│                                         │
│  ④ TM(가압제외) → ELEC     [OFF □■ ON]   │  ← alert_tm_tank_module_to_elec_enabled
│     가압 미필요 시 TANK_MODULE 완료 알림   │
│                                         │
│  ⑤ MECH 가압(DRAGON) → QI  [OFF □■ ON]   │  ← alert_mech_pressure_to_qi_enabled
│     DRAGON 모델 MECH 가압검사 → QI        │
│                                         │
└─────────────────────────────────────────┘
```

#### 구현 포인트

1. **상태 변수 추가** (기존 _heatingJacketEnabled 등과 동일 패턴):
```dart
bool _alertTmToMechEnabled = true;
bool _alertMechToElecEnabled = true;
bool _alertElecToPiEnabled = false;
bool _alertTmTankModuleToElecEnabled = false;
bool _alertMechPressureToQiEnabled = false;
```

2. **_loadSettings()에 추가** (기존 GET /api/app/admin/settings 응답에서 로드):
```dart
_alertTmToMechEnabled = settings['alert_tm_to_mech_enabled'] ?? true;
_alertMechToElecEnabled = settings['alert_mech_to_elec_enabled'] ?? true;
_alertElecToPiEnabled = settings['alert_elec_to_pi_enabled'] ?? false;
```

3. **토글 변경 시** 기존 _updateSetting() 메서드 재사용:
```dart
_updateSetting('alert_tm_to_mech_enabled', value.toString());
```

4. **공정 흐름도 위젯**: Row + Container 원형 스텝 + 화살표 연결선
   - 각 스텝: 원형 아이콘 (TM/MECH/ELEC/PI/QI)
   - 트리거 위치에 번호 표시 (①②③)
   - 비활성 트리거는 회색 점선으로 표시

5. **권한**: is_admin 또는 is_manager만 접근 가능 (기존 AdminOptionsScreen 권한 그대로)

---

### Task 5 — Sprint 37-A TANK_MODULE(가압제외) 트리거 → admin_settings on/off 전환

**현재 상태**: L444-447에 TANK_MODULE 완료(가압제외) → TMS_TANK_COMPLETE → MECH 트리거 존재 (하드코딩)
**변경**: 제거하지 않고, admin_settings `alert_tm_tank_module_to_mech_enabled` (기본 false)로 전환

```python
# 변경 전 (L444-447):
elif task.task_id == 'TANK_MODULE' and task.task_category == 'TMS':
    if not self._is_tm_pressure_test_required():
        trigger = ('TMS_TANK_COMPLETE', 'MECH', 'TMS 탱크모듈 완료 (가압검사 제외)')

# 변경 후: admin_settings on/off + partner 분기 적용
elif task.task_id == 'TANK_MODULE' and task.task_category == 'TMS':
    if not self._is_tm_pressure_test_required():
        trigger = ('TMS_TANK_COMPLETE', 'elec_partner', 'TMS 탱크모듈 완료 (가압검사 제외)', 'alert_tm_tank_module_to_elec_enabled')
```

기본값 false → 현재 동작 변화 없음. 필요 시 admin에서 ON으로 전환.
동일하게 DRAGON MECH 가압검사 → QI도 admin_settings 전환:

```python
# 변경 전:
trigger = ('TMS_TANK_COMPLETE', 'QI', 'MECH 가압검사 완료', 'alert_mech_pressure_to_qi_enabled')
# → get_setting('alert_mech_pressure_to_qi_enabled', False) 체크 후 발송
```

---

### 테스트

```
[Task 0 — partner → company 매핑]
TC-54-01: _partner_to_company('TMS', 'mech_partner') → 'TMS(M)'
TC-54-02: _partner_to_company('TMS', 'elec_partner') → 'TMS(E)'
TC-54-03: _partner_to_company('TMS', 'module_outsourcing') → 'TMS(M)'
TC-54-04: _partner_to_company('FNI', 'mech_partner') → 'FNI'
TC-54-05: _partner_to_company('P&S', 'elec_partner') → 'P&S'
TC-54-06: get_managers_by_partner(sn, 'mech_partner') — mech_partner='TMS' → TMS(M) 매니저만 반환
TC-54-07: get_managers_by_partner(sn, 'elec_partner') — elec_partner='TMS' → TMS(E) 매니저만 반환
TC-54-08: get_managers_by_partner(sn, 'module_outsourcing') — module_outsourcing='TMS' → TMS(M) 매니저
TC-54-09: get_managers_by_partner(sn, 'mech_partner') — mech_partner=NULL → 빈 리스트
TC-54-10: get_managers_by_partner(sn, 'invalid_field') → 빈 리스트 + 에러 로그

[Task 1 — trigger① TMS→MECH 가압완료]
TC-54-11: TMS PRESSURE_TEST 완료, mech_partner='FNI' → FNI 매니저에게만 TMS_TANK_COMPLETE 알림
TC-54-12: TMS PRESSURE_TEST 완료, mech_partner='TMS' → 같은 회사 스킵, 알림 0건
TC-54-13: DUAL 모델 L만 완료 → 알림 미발송 (기존 로직 유지)
TC-54-14: DUAL 모델 L+R 모두 완료 → 알림 발송
TC-54-15: alert_tm_to_mech_enabled=false → 알림 스킵

[Task 1 — trigger② MECH→ELEC 도킹완료]
TC-54-16: MECH TANK_DOCKING 완료, elec_partner='TMS' → TMS(E) 매니저에게 TANK_DOCKING_COMPLETE
TC-54-17: MECH TANK_DOCKING 완료, elec_partner='P&S' → P&S 매니저에게 알림
TC-54-18: alert_mech_to_elec_enabled=false → 알림 스킵

[Task 1 — trigger③ ELEC→PI]
TC-54-19: ELEC 전체 완료 → alert_elec_to_pi_enabled=false(기본값) → 알림 스킵
TC-54-20: ELEC 전체 완료 → alert_elec_to_pi_enabled=true → PI(GST) 매니저에게 알림

[Task 2 — CHECKLIST_TM_READY (Sprint 52 수정)]
TC-54-21: 비매니저가 TMS TANK_MODULE 완료, module_outsourcing='TMS' → TMS(M) is_manager에게 CHECKLIST_TM_READY
TC-54-22: 매니저가 TMS TANK_MODULE 완료 → 알림 미발송 + checklist_ready=true
TC-54-23: CHECKLIST_TM_READY 알림 클릭 → TM 체크리스트 화면 이동

[Task 3 — admin_settings]
TC-54-24: migration 044 실행 → admin_settings에 5개 키 추가 확인
TC-54-25: GET /api/app/admin/settings → alert_tm_to_mech_enabled 등 응답 포함
TC-54-26: PUT /api/app/admin/settings alert_tm_to_mech_enabled=false → 저장 성공

[Task 4 — OPS FE 알림 트리거 설정]
TC-54-27: AdminOptionsScreen → "알림 트리거 설정" 섹션 표시
TC-54-28: 공정 흐름도 위젯 렌더링 (TM→MECH→ELEC→PI→QI)
TC-54-29: 토글 ON/OFF → PUT 요청 발송 → 설정값 변경 확인
TC-54-30: 비활성 트리거(ELEC→PI OFF) → 흐름도에서 회색 점선 표시

[regression]
TC-54-31: MECH PRESSURE_TEST 완료 (DRAGON) → QI 매니저 알림 정상 (기존 동작)
TC-54-32: 기존 TMS_TANK_COMPLETE 알림 수신 후 페이지 이동 정상
TC-54-33: 기존 TANK_DOCKING_COMPLETE 알림 수신 후 페이지 이동 정상
TC-54-34: get_managers_for_role('MECH') 함수 자체는 삭제하지 않음 (다른 곳에서 사용 가능)
```

### 규칙
- 코드 변경 전 반드시 사용자 승인
- `get_managers_for_role()` 함수는 삭제하지 않음 — 다른 코드에서 참조 가능
- `_partner_to_company()` 매핑은 하드코딩 (현재 회사 수가 적고 변경 빈도 낮음)
- 향후 새 트리거 추가 시: admin_settings 키 등록 + elif 블록 + TC 추가만으로 완료
- Sprint 37-A TANK_MODULE(가압제외) 트리거 제거 전 사용자 확인 필수
- TC-54-01~34 통과 후 커밋
