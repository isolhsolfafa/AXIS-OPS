# G-axis App Plan v4.0 — Clean Cut 전략

> 작성일: 2026-02-16
> 전략: PDA 유지 + App MVP 별도 개발 → Staging 테스트 → 서버 전환
> 목표: 스프레드시트 수동 입력 → 모바일 App 실시간 Push 전환

---

## 1. 전략 결정 사항 (대화 기반 확정)

### 1.1 Clean Cut 전략 (하이브리드 X)

```
현재 PDA ─── 그대로 운영 (건드리지 않음) ─── 전환 시점에 중단
                                                 ↓
App MVP ─── Mac에서 개발 ──► Staging DB 테스트 ──► 서버 배포
  │                              ↑
  └── Staging DB (관계형 정립) ─── quality/planning 스키마 추가
                                   ↓
신규 React ── App DB 기반 처음부터 구축 ──── 서버 배포
```

**하이브리드를 버린 이유:**
- PDA 27개 + App 12개 = 39개 테이블 동시 운영 → 정합성 관리 불가
- 두 시스템이 같은 테이블에 쓰면 충돌 발생
- 기존 PDA 안 깨뜨리면서 개발하는 제약 → 개발 속도 저하
- 1인 DX팀에게 병행 운영은 비현실적

### 1.2 워킹타임 계산 로직 — 생략 결정

**기존 (PDA):** `calculate_working_hours_with_holidays()` 200줄
- 스프레드시트 수동 입력 오류 보정 목적
- 휴일 체크, 근무시간 클리핑, 일일 최대시간, 휴게시간 제외

**신규 (App):** 검증 10줄 이내
```
duration = completed_at - started_at  (끝)
+ 비정상 duration 체크 (> 14시간)
+ 역전 방지 (completed_at < started_at)
+ 중복 방지 (같은 S/N + Task에 이미 완료)
```

**근거:** App push 방식은 버튼 터치 시점에 NOW() 타임스탬프가 찍히므로 입력 자체가 정확. 휴게시간/휴일/주말 보정이 불필요.

### 1.3 QR 코드 — 호환 불필요

- PDA: `google_doc_id` 기반
- App: `qr_doc_id` (DOC_{SN}) 기반
- 두 시스템 별도 운영이므로 호환 필요 없음
- PDA QR은 PDA가 살아있는 동안 유효
- App 전환 시 새 QR 발행

### 1.4 React 대시보드 — 신규 구축

- 기존 React 코드 패칭 X
- App → Staging DB → 신규 React SPA (처음부터)
- 기존 코드에서 참고할 것: UI 디자인 정도만

### 1.5 작업자 등록 방식

- 관리자 + 주요인원: SQL 벌크 등록 (approval_status = 'approved')
- 나머지 작업자: 자가 회원가입 → 관리자 승인

---

## 2. App 워크플로우 (확정 로직)

### 2.1 전체 흐름

```
[회원가입/로그인]
  ├── 이메일 + 비밀번호 입력
  ├── 이메일 인증 (6자리 코드, 10분 만료)
  └── 관리자 승인 대기 → approved 시 활성화

[QR 입력] (순서 무관)
  ├── Worksheet QR 스캔 → qr_doc_id → product_info 조회
  └── Location QR 스캔 → 위치 등록

[공정 검증] (PI/QI/SI 작업자에게만)
  ├── MM(기구) 미완료? → "기구 작업 누락" 경고 + MM 관리자 알림
  ├── EE(전장) 미완료? → "전장 작업 누락" 경고 + EE 관리자 알림
  ├── Location QR 미등록? → "위치 QR 먼저 촬영하세요" 팝업
  └── 전부 완료 → 검사 작업 진행 허용

[Task 시작/완료]
  ├── 시작 터치 → started_at = NOW()
  ├── 완료 터치 → completed_at = NOW()
  ├── duration = completed_at - started_at (자동)
  └── 카테고리 전체 완료 시 → completion_status 업데이트

[자동 감지]
  ├── 정규 퇴근시간 도래 → 미완료 Task 감지
  ├── 관리자 알림 발송
  └── app_alert_logs 기록
```

### 2.2 역할별 Task 목록

**6개 역할 (Production PDA 기준):**

| 역할 | 카테고리 | Task 수 | 완료 기준 Task | 소속 |
|------|---------|---------|--------------|------|
| MM | 기구 | 19개 (TMS 제외 15) | 자주검사 | 협력사 |
| TM | TMS반제품 | 4개 | - | 협력사 |
| EE | 전장 | 8개 | 검수 | 협력사 |
| PI | 가압검사 | 3개 | - | 사내 |
| QI | 공정검사 | 1개 | I/O체크+가동검사+전장마무리 | 사내 |
| SI | 출하검사 | 4개 | - | 사내 |

**TMS 분기 로직:**
```
IF mech_partner == "TMS" AND module_outsourcing == "TMS":
  → TMS 모듈 Task (BURNER, WET TANK, COOLING, REACTOR + 가압검사)
ELSE:
  → 일반 기구 Task 19개
```

### 2.3 공정 누락 검증 상세 (핵심 차별점)

```yaml
트리거: PI/QI/SI 작업자가 Worksheet QR 태깅 시

검증_순서:
  1. Location QR 등록 여부 체크
     → 미등록: "📍 검사 위치 등록 필요 — Location QR을 먼저 촬영하세요"
     → [Location QR 촬영하기] / [나중에] 선택

  2. MM(기구) 공정 완료 체크 (completion_status.mm_completed)
     → 미완료: "⚠️ 기구 작업 누락 발생 — MM 관리자에게 알림이 발송되었습니다"
     → app_alert_logs INSERT (alert_type: 'missing_task')
     → MM 관리자에게 Push 알림

  3. EE(전장) 공정 완료 체크 (completion_status.ee_completed)
     → 미완료: "⚠️ 전장 작업 누락 발생 — EE 관리자에게 알림이 발송되었습니다"
     → app_alert_logs INSERT
     → EE 관리자에게 Push 알림

  4. 전부 완료:
     → 검사 작업 진행 허용
     → allowInspectionTasks()

결과:
  - 스프레드시트에서는 불가능했던 실시간 공정 검증
  - 누락 방지 + 관리자 즉각 대응
```

### 2.4 관리자 알림 시스템

```yaml
알림_트리거:
  1. 공정 누락 감지 (PI/QI/SI 태깅 시)
     → 해당 공정 관리자에게 즉시 알림
     → 예: "SN GBWS-6408 기구 작업 미완료 — PI 작업자 김OO이 검사 시도"

  2. 카테고리 전체 완료
     → 다음 공정 관리자에게 알림
     → 예: "SN GBWS-6408 기구 작업 전체 완료 — 전장 작업 시작 가능"

  3. 정규 퇴근시간 미완료 Task
     → 해당 작업자 + 관리자에게 알림
     → 예: "SN GBWS-6408 EE 작업 3/8 완료 — 미완료 5건"

  4. 비정상 duration 감지 (> 14시간)
     → 관리자에게 검토 요청 알림
     → 예: "SN GBWS-6408 CABINET ASSY 18시간 경과 — 완료 확인 필요"

구현_방식:
  - WebSocket (Flask-SocketIO): 실시간 Push
  - app_alert_logs 테이블: 이력 기록
  - is_read / read_at: 읽음 처리
```

### 2.5 미완료 Task 자동감지 정책

```yaml
퇴근시간_기준: 20:00 (평일), 17:00 (주말)

자동_감지_로직:
  1. 매일 퇴근시간에 batch 체크 (서버 cron)
  2. started_at IS NOT NULL AND completed_at IS NULL인 Task 조회
  3. duration = NOW() - started_at > 14시간이면 비정상

처리_옵션:
  - 관리자 수동 보정 UI (관리자 권한으로 completed_at 입력)
  - 자동 완료 처리 X (잘못된 데이터 방지)
  - 알림만 발송하고 현장에서 판단

비정상_duration_검증:
  - completed_at < started_at → 시스템 오류 (발생 불가하지만 방어코드)
  - duration > 14시간 → 경고 (완료 안 누름 가능성)
  - duration < 1분 → 경고 (실수 터치 가능성)
```

---

## 3. DB 스키마 (Staging → Production)

### 3.1 핵심 테이블 (App MVP)

```sql
-- 1. workers (작업자 관리)
-- 6역할: MM, EE, TM, PI, QI, SI
-- 이메일 인증 + 관리자 승인 2단계
-- is_manager: 협력사 관리자 (Task 삭제 권한)

-- 2. email_verification (이메일 인증)
-- 6자리 인증번호, 10분 만료

-- 3. product_info (제품 정보) — info 테이블 대체
-- qr_doc_id 기반 (DOC_{SN})
-- location_qr_id 포함

-- 4. app_task_details (Task 추적) — worksheet 대체
-- started_at/completed_at = NOW() (App push)
-- is_applicable: Task 비활성화 (관리자/사내직원 전용)
-- UNIQUE (serial_number, task_category, task_id)

-- 5. completion_status (공정별 완료 상태)
-- mm/tm/ee/pi/qi/si_completed (boolean)
-- all_completed + all_completed_at
```

### 3.2 알림/동기화 테이블

```sql
-- 6. app_alert_logs (알림/경고)
-- alert_type: missing_task, approval_complete, system
-- target_worker_id + is_read + read_at

-- 7. location_history (QR 위치 추적)
-- qr_location_id + location_name
-- GPS 보조 (latitude/longitude)

-- 8. offline_sync_queue (오프라인 동기화)
-- sync_status: pending → synced / failed

-- 9. work_start_log (작업 시작 이벤트)
-- 10. work_completion_log (작업 완료 + 소요시간)
-- duration_minutes: completed_at - started_at (자동계산)
```

### 3.3 추후 테이블

```sql
-- 11. product_bom (BOM 목록, SI용) — Phase 2
-- 12. bom_checklist_log (BOM 검증 + AI) — Phase 2
```

### 3.4 PDA 테이블과의 대체 관계

```
PDA (Sheets 기반)              →  App (실시간 Push)
────────────────────────────────────────────────────
info                           →  product_info
  google_doc_id                →  qr_doc_id (DOC_{SN})
worksheet (시트 추출)           →  app_task_details (앱 직접 기록)
task_summary (배치 계산)        →  work_completion_log (실시간)
  working_hours (float, 200줄) →  duration_minutes (int, 자동)
progress_summary               →  completion_status (boolean)
stats / partner_stats          →  실시간 SQL 쿼리
treemap_data                   →  실시간 SQL 쿼리
processing_log                 →  없음 (배치 처리 자체가 없어짐)
processed_files                →  없음 (파일 기반 처리 없어짐)
```

---

## 4. API 설계 (Clean Cut 기준)

### 4.1 인증 API

```
POST /api/auth/register       — 회원가입 (workers INSERT)
POST /api/auth/verify-email   — 이메일 인증 확인
POST /api/auth/login          — 로그인 (JWT 토큰 발급)
POST /api/auth/approve        — 관리자 승인 (관리자 전용)
```

### 4.2 작업 API (핵심)

```
GET  /api/app/product/{qr_doc_id}     — QR 스캔 → 제품 조회
POST /api/app/location/update         — Location QR 등록
GET  /api/app/tasks/{serial_number}   — 역할별 Task 목록 조회
POST /api/app/work/start              — 작업 시작 (started_at = NOW())
POST /api/app/work/complete           — 작업 완료 (completed_at = NOW())
GET  /api/app/completion/{serial_number} — 공정 완료 상태 조회
```

### 4.3 알림/동기화 API

```
GET  /api/app/alerts/{worker_id}      — 내 알림 목록
PUT  /api/app/alerts/{id}/read        — 읽음 처리
POST /api/app/sync                    — 오프라인 데이터 동기화
```

### 4.4 관리자 API

```
GET  /api/admin/pending-workers       — 승인 대기 목록
POST /api/admin/approve/{worker_id}   — 승인/거절
PUT  /api/admin/task/close            — 미완료 Task 수동 보정
GET  /api/admin/dashboard             — 관리자 대시보드 데이터
```

### 4.5 WebSocket 이벤트

```
[서버 → 클라이언트]
  task_completed    — 누군가 Task 완료 시 관련자에게
  process_alert     — 공정 누락 감지 시
  approval_update   — 승인 상태 변경 시
  daily_summary     — 퇴근 시간 미완료 요약

[클라이언트 → 서버]
  location_update   — 위치 변경 시
  task_progress     — 진행 상태 변경 시
```

---

## 5. Flutter App 현황 & 변경 사항

### 5.1 이미 완성된 것 (80%)

```yaml
로컬_DB: SQLite (task_details, completion_status, alert_logs, offline_queue)
데이터_모델: TaskItem, CompletionStatus, AlertLog, WorksheetInfo
API_통신: ApiService (REST, Mock, 타임아웃, 에러핸들링)
UI_화면: TestInputScreen, WorksheetDetailScreen, TaskManagementScreen
역할_분기: MM 19개, EE 8개, II 4개, TMS 분기 로직
```

### 5.2 Clean Cut으로 변경해야 할 것

```yaml
변경_필요:
  1. google_doc_id → qr_doc_id 전환 (전체 코드)
  2. info 테이블 참조 → product_info 테이블
  3. worksheet/task_summary 참조 제거 → app_task_details만
  4. calculate_working_hours 호출 제거 → duration 자동계산
  5. API 엔드포인트 변경 (Push API 신규)

신규_구현:
  1. 회원가입/로그인 화면 (이메일 인증 포함)
  2. WebSocket 연결 (Flask-SocketIO)
  3. 공정 누락 검증 팝업 (PI/QI/SI)
  4. 관리자 알림 수신 화면
  5. 미완료 Task 알림 처리
  6. QR 스캔 (MLKit 복원 또는 대안)

미정_사항:
  - Apple Developer Program 승인 여부
  - QR 스캔 라이브러리 선택
  - 오프라인 충돌 해결 정책 (Server Wins)
```

---

## 6. 점검 체크리스트

### 6.1 Staging DB 설계 시

- [ ] 핵심 5개 테이블 DDL 작성 완료
- [ ] 알림/동기화 테이블 DDL 작성 완료
- [ ] serial_number FK 정합성 확인
- [ ] UNIQUE 제약조건 확인 (serial_number + task_category + task_id)
- [ ] 인덱스 설계 (검색 빈도 높은 컬럼)
- [ ] audit 컬럼 (created_at, updated_at) 전 테이블 확인

### 6.2 API 구현 시

- [ ] JWT 인증 미들웨어
- [ ] 이메일 발송 서비스 (SMTP / SendGrid)
- [ ] WebSocket 연결 관리 (Flask-SocketIO)
- [ ] 에러 핸들링 표준화 (HTTP 상태코드 + 에러 코드)
- [ ] API 응답시간 < 500ms 검증
- [ ] CORS 설정 (Flutter 웹 모드)

### 6.3 App 개발 시

- [ ] qr_doc_id 기반으로 전체 코드 전환
- [ ] 오프라인 → 온라인 복귀 시 동기화 테스트
- [ ] 공정 누락 검증 팝업 동작 확인
- [ ] WebSocket 재연결 로직 (네트워크 불안정)
- [ ] 관리자 알림 수신 확인
- [ ] TMS 분기 로직 테스트

### 6.4 테스트 시

- [ ] 관리자 계정으로 승인 플로우 테스트
- [ ] MM → EE → PI/QI/SI 순차 작업 플로우
- [ ] 동시 작업 (같은 S/N에 MM + EE 동시)
- [ ] 미완료 Task 퇴근시간 감지
- [ ] 비정상 duration 감지 (14시간+ / 1분-)
- [ ] 테스트 데이터 vs 실데이터 구분 (Staging DB = 테스트, Production = clean)

### 6.5 전환 시

- [ ] PDA → App 스키마 매핑 스크립트 작성
- [ ] Historical 데이터 마이그레이션 검증
- [ ] 전환일 공지 (협력사 포함)
- [ ] 새 QR 스티커 발행 (qr_doc_id 기반)
- [ ] SCR-Schedule 데이터 소스 변경 (planning 스키마)

---

## 7. 변수 & 리스크 관리

| # | 변수 | 결정 시점 | 현재 상태 | 대응 |
|---|------|----------|----------|------|
| 1 | QR 스캔 라이브러리 | P1 개발 시 | MLKit 제거됨 | qr_code_scanner 또는 대안 |
| 2 | Apple Developer Program | P1 개발 시 | 승인 대기 | 웹 모드 우선 |
| 3 | 보안팀 서버 승인 | P2 시작 전 | 요청서 v3.0 준비 | 팀장 보고 후 제출 |
| 4 | "완료 안 누름" 빈도 | P3 테스트 시 | 미확인 | 퇴근시간 감지 + 관리자 알림 |
| 5 | 오프라인 빈도 | P3 테스트 시 | 사내 WiFi | offline_sync_queue로 대응 |
| 6 | 협력사 저항 | P3 전환 시 | 미확인 | 관리자 선등록 + 교육 |
| 7 | SCR-Schedule 연동 | P4 React 시 | config.py 수정불가 | planning 스키마 별도 ETL |
| 8 | QMS 연동 방식 | P5 통합 시 | 미확인 | 직접DB/API/Export 조사 |

---

## 8. VS Code Claude 개발 시 참고

### 8.1 .claude/CLAUDE.md 설정 권장

```markdown
# GST Factory PDA → App 전환 프로젝트

## 프로젝트 컨텍스트
- 제조 현장 작업 관리 시스템 (MES-lite)
- Flutter App + Flask API + PostgreSQL
- Clean Cut 전략: PDA 유지 + App MVP 별도 개발

## DB 규칙
- Staging DB: App 테이블만 (PDA 테이블 X)
- qr_doc_id 기반 (google_doc_id X)
- product_info 테이블 (info X)
- duration = completed_at - started_at (calculate_working_hours X)

## API 규칙
- JWT 인증 필수
- 에러: {"error": "code", "message": "설명"}
- 응답시간 < 500ms 목표

## 코드 스타일
- Python: Flask, psycopg2, Flask-SocketIO
- Dart: Riverpod, SQLite, dio
- 한국어 주석 OK
```

### 8.2 개발 단위 (자율 코딩 가능 범위)

```yaml
자율_코딩_적합:
  - DDL 스크립트 생성 (테이블 정의 명확)
  - API 엔드포인트 구현 (스펙 명확)
  - 데이터 모델 클래스 (스키마 기반)
  - 마이그레이션 스크립트 (매핑 명확)
  - 단위 테스트 (입출력 명확)

판단_필요 (사람 확인):
  - UI/UX 레이아웃 결정
  - 비즈니스 로직 예외 케이스
  - 성능 최적화 전략
  - 외부 서비스 연동 (이메일, QR)
  - 배포 환경 설정
```

---

## 9. 개발/테스트 환경 설정

### 9.1 DB 접속 정보

| 구분 | Host | Port | DB | 용도 |
|------|------|------|----|------|
| **Staging DB** | `maglev.proxy.rlwy.net` | `38813` | `railway` | App 개발/테스트 전용 |
| **Production DB** | `shinkansen.proxy.rlwy.net` | `49936` | `railway_pda` | PDA 운영 (참조만, 수정 금지) |

```
# Staging DB (App 개발용)
postgresql://postgres:aemQKKvZhddWGlLUsAghiWAlzFkoWugL@maglev.proxy.rlwy.net:38813/railway

# Production DB (PDA 운영 — 읽기 참조만)
postgresql://postgres:qBOUbdBJtpgoIGQuhmLhgUWyuddQjciX@shinkansen.proxy.rlwy.net:49936/railway_pda
```

> **주의**: Production DB는 PDA가 운영 중이므로 절대 스키마 변경/데이터 수정 금지. 참조(SELECT)만 허용.

### 9.2 로컬 테스트 서버

```bash
# 실행 방법
cd /Users/kdkyu311/dev/my_app/test_server
python app.py

# 접속
http://localhost:5001
```

| 항목 | 내용 |
|------|------|
| **프레임워크** | Flask (Python) |
| **포트** | 5001 |
| **UI** | G-AXIS 디자인 시스템 적용, 폰 시뮬레이터 형태 |
| **테스트 플로우** | 6스텝: Main → Login → QR Scan → Location QR → MM/EE Check → Task |
| **DB 연결** | Staging DB (위 접속 정보 사용) |
| **HTML 경로** | `test_server/static/index.html` |

### 9.3 참고 문서

| 문서 | 경로 | 내용 |
|------|------|------|
| **종합 분석 (스키마 참조)** | `PROJECT_COMPREHENSIVE_ANALYSIS_2026.md` | Production DB 스키마 (PDA 27개 테이블), App DB 스키마 (12개 테이블), 테이블 전환 매핑 |
| **App 스키마 설계** | `test_server/APP_SCHEMA_DESIGN_20260206.md` | App 테이블 DDL, QR 플로우, Task 카테고리 상세 |
| **전체 시퀀스 & Phase** | `APP_FULL_SEQUENCE_AND_PHASES.md` | 로그인→공정종료 전체 시퀀스, PDA 계산 로직 참조, 4단계 Phase 계획 |
| **브랜드 & 로고** | `PROJECT_COMPREHENSIVE_ANALYSIS_2026.md` Section 14 | 공식 로고 (G-AXIS-2.png), CSS 적용 규칙, 브랜드 체계 |
| **G-AXIS 디자인 시스템** | `~/Desktop/Brand indentity/G-AXIS_DESIGN_SYSTEM.md` | 컬러 토큰, 타이포그래피, 컴포넌트 스펙 |

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2026-01-12 | 1.0 | PROJECT_COMPREHENSIVE_ANALYSIS 초안 (하이브리드 방식) |
| 2026-02-06 | 1.1 | 6역할 체계, 순서무관 입력 반영 |
| 2026-02-11 | 2.0 | ETL 파이프라인, QR 배포, DB 전환 분석 추가 |
| 2026-02-15 | 3.0 | 서버 보안 요청서 v3.0, 데이터 전수 조사 |
| 2026-02-16 | 4.0 | **Clean Cut 전략 확정** — 하이브리드 폐기, 워킹타임 계산 생략, 신규 React, QR 호환 불필요, 미완료 자동감지 정책, 관리자 알림 시스템 |
| 2026-02-16 | 4.1 | Section 9 추가: Staging/Production DB 접속 정보, localhost:5001 테스트 서버, 참고 문서 목록 |
