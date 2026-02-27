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
