# G-axis App — Agent Teams 프로젝트

## 프로젝트 개요
GST 제조 현장 작업 관리 시스템. 스프레드시트 수동 입력 → 모바일 App 실시간 Push 전환.
Clean Cut 전략: 기존 PDA는 그대로 유지, App MVP를 별도 개발 후 테스트 완료 시 일괄 전환.

## 팀 구성 & 모델 설정

### 리드 에이전트 (Lead — 설계 조율)
- **모델**: Opus (claude-opus-4-6)
- **역할**: 전체 아키텍처 설계, 에이전트 간 조율, 코드 리뷰, 의사결정
- **모드**: Delegate 모드 (Shift+Tab) — 리드는 직접 코드 작성하지 않고 조율만 수행
- **권한**: 모든 파일 읽기 가능, 직접 수정은 하지 않음

### 워커 에이전트 (Workers — 구현/테스트)
- **모델**: Sonnet (claude-sonnet-4-5)
- **역할**: FE, BE, TEST 각각 담당 영역의 코드 구현
- **모드**: 사용자 승인 후 코드 수정 가능 (위임 모드)

### 위임 모드 규칙
1. 리드가 작업을 분배하고 워커에게 위임
2. 워커는 코드 변경 전 **반드시 사용자 승인** 필요
3. 파일 소유권 위반 시 즉시 중단
4. 스프린트 단위로 작업 진행 (현재 Sprint 1부터 시작)

## 참조 문서 (반드시 읽을 것)
- `APP_PLAN_v4(26.02.16).md` — App 설계/로직/API/DB 스키마 전체 정의
- `PROJECT_COMPREHENSIVE_ANALYSIS_2026(02.16).md` — 프로젝트 종합 분석 (워크플로우, 테이블 정의, 시간 계산 로직 등)

## 기술 스택
- **Frontend**: Flutter 3.x (Web Build + PWA) + Riverpod + SQLite (오프라인) + dio (HTTP)
- **Backend**: Flask 3.x + PostgreSQL 15 + Flask-SocketIO (WebSocket) + psycopg2
- **Test**: pytest (BE) + flutter_test (FE) + integration tests

## 배포 전략: PWA 우선 (Web-First)
- **1단계 (현재)**: Flutter Web Build → PWA로 배포 (앱스토어 심사 없이 즉시 배포)
- **2단계 (안정화 후)**: 동일 코드로 iOS/Android 네이티브 빌드 → 앱스토어 정식 심사

### PWA 구현 필수사항
- `web/manifest.json` — 앱 이름, 아이콘, 테마 색상 설정
- `web/index.html` — Service Worker 등록 (오프라인 캐싱)
- 앱 아이콘: 192x192, 512x512 PNG 필요
- HTTPS 필수 (PWA 설치 조건)
- 카메라(QR 스캔): `html` 패키지의 `MediaDevices` API 사용 (웹 호환)

### FE 에이전트 주의사항
- `flutter build web` 기준으로 개발
- 네이티브 전용 플러그인 사용 금지 (웹 미지원 플러그인 X)
- QR 스캔: `mobile_scanner` 대신 웹 호환 패키지 사용 또는 조건부 import
- 로컬 저장소: SQLite 대신 `shared_preferences` 또는 `hive` (웹 호환)
- 반응형 UI: 모바일 브라우저 기준 설계 (375px ~ 428px 너비)

## 핵심 규칙 (모든 에이전트 공통)

### DB 규칙
- `qr_doc_id` 사용 (`google_doc_id` 사용 금지)
- `product_info` 테이블 사용 (`info` 테이블 사용 금지)
- `duration = completed_at - started_at` (calculate_working_hours 함수 사용 금지)
- Staging DB 기준 개발 (PDA Production DB 절대 건드리지 않음)

### API 규칙
- JWT 인증 필수
- 에러 응답: `{"error": "ERROR_CODE", "message": "설명"}`
- 응답시간 목표: < 500ms

### 코드 스타일
- Python: type hints 사용, docstring 필수
- Dart: Riverpod 패턴, null safety
- 한국어 주석 허용
- 커밋 메시지: 영어 (conventional commits)

---

## 에이전트 팀 구성

### Agent 1: FE (Frontend — Flutter App)
**담당**: Flutter 앱 전체 (UI, 상태관리, 로컬DB, API 통신)

**소유 파일**:
```
frontend/**
```

**주요 업무**:
- 회원가입/로그인 화면 (이메일 인증 포함)
- QR 스캔 → 제품 조회 화면
- Task 시작/완료 터치 UI
- 공정 누락 검증 팝업 (PI/QI/SI)
- 관리자 알림 수신 화면
- WebSocket 연결 (실시간 동기화)
- 오프라인 동기화 (SQLite + offline_sync_queue)

**절대 수정 금지**: `backend/**`, `tests/backend/**`

---

### Agent 2: BE (Backend — Flask API)
**담당**: Flask API 서버 전체 (인증, 작업관리, 알림, WebSocket)

**소유 파일**:
```
backend/**
```

**주요 업무**:
- JWT 인증 미들웨어
- 회원가입/로그인 API (workers + email_verification)
- 작업 시작/완료 API (app_task_details + completion_status)
- 공정 검증 로직 (MM/EE 완료 체크)
- 관리자 알림 API (app_alert_logs)
- WebSocket 이벤트 (Flask-SocketIO)
- DB 마이그레이션 스크립트

**절대 수정 금지**: `frontend/**`, `tests/frontend/**`

---

### Agent 3: TEST (테스트 담당)
**담당**: 전체 테스트 코드 작성 및 실행

**소유 파일**:
```
tests/**
```

**주요 업무**:
- Backend API 단위 테스트 (pytest)
- Frontend 위젯 테스트 (flutter_test)
- 통합 테스트 (API → DB 플로우)
- 공정 검증 로직 테스트 (누락 감지, 알림)
- 비정상 duration 검증 테스트
- 테스트 데이터 fixtures

**절대 수정 금지**: `backend/app/**` (소스코드), `frontend/lib/**` (소스코드)
**읽기 가능**: 모든 파일 (테스트 작성을 위해)

---

## 프로젝트 디렉토리 구조

```
AXIS-OPS/
├── CLAUDE.md                              # 이 파일
├── APP_PLAN_v4(26.02.16).md              # App 설계 문서
├── PROJECT_COMPREHENSIVE_ANALYSIS_2026(02.16).md  # 종합 분석 문서
│
├── frontend/                              # [FE 소유]
│   ├── lib/
│   │   ├── main.dart
│   │   ├── models/                        # 데이터 모델
│   │   │   ├── worker.dart
│   │   │   ├── task_item.dart
│   │   │   ├── product_info.dart
│   │   │   └── alert_log.dart
│   │   ├── services/                      # API/DB 서비스
│   │   │   ├── api_service.dart
│   │   │   ├── auth_service.dart
│   │   │   ├── websocket_service.dart
│   │   │   └── local_db_service.dart
│   │   ├── providers/                     # Riverpod 상태관리
│   │   │   ├── auth_provider.dart
│   │   │   ├── task_provider.dart
│   │   │   └── alert_provider.dart
│   │   ├── screens/                       # UI 화면
│   │   │   ├── auth/
│   │   │   │   ├── login_screen.dart
│   │   │   │   ├── register_screen.dart
│   │   │   │   └── verify_email_screen.dart
│   │   │   ├── home/
│   │   │   │   └── home_screen.dart
│   │   │   ├── task/
│   │   │   │   ├── task_management_screen.dart
│   │   │   │   └── task_detail_screen.dart
│   │   │   ├── qr/
│   │   │   │   └── qr_scan_screen.dart
│   │   │   └── admin/
│   │   │       ├── admin_dashboard.dart
│   │   │       └── worker_approval_screen.dart
│   │   ├── widgets/                       # 재사용 위젯
│   │   │   ├── process_alert_popup.dart
│   │   │   ├── task_card.dart
│   │   │   └── completion_badge.dart
│   │   └── utils/
│   │       ├── constants.dart
│   │       └── validators.dart
│   ├── pubspec.yaml
│   └── README.md
│
├── backend/                               # [BE 소유]
│   ├── app/
│   │   ├── __init__.py                    # Flask app factory
│   │   ├── config.py                      # 설정 (DB URL, JWT secret 등)
│   │   ├── models/                        # SQLAlchemy 모델 (or raw SQL)
│   │   │   ├── __init__.py
│   │   │   ├── worker.py
│   │   │   ├── product_info.py
│   │   │   ├── task_detail.py
│   │   │   ├── completion_status.py
│   │   │   ├── alert_log.py
│   │   │   └── location_history.py
│   │   ├── routes/                        # API 엔드포인트
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                    # /api/auth/*
│   │   │   ├── work.py                    # /api/app/work/*
│   │   │   ├── product.py                 # /api/app/product/*
│   │   │   ├── alert.py                   # /api/app/alerts/*
│   │   │   ├── admin.py                   # /api/admin/*
│   │   │   └── sync.py                    # /api/app/sync
│   │   ├── services/                      # 비즈니스 로직
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── task_service.py
│   │   │   ├── process_validator.py       # 공정 누락 검증
│   │   │   ├── alert_service.py
│   │   │   └── duration_validator.py      # 비정상 duration 검증
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── jwt_auth.py
│   │   │   └── audit_log.py
│   │   └── websocket/
│   │       ├── __init__.py
│   │       └── events.py                  # SocketIO 이벤트 핸들러
│   ├── migrations/                        # DB 마이그레이션
│   │   ├── 001_create_workers.sql
│   │   ├── 002_create_product_info.sql
│   │   ├── 003_create_task_tables.sql
│   │   ├── 004_create_alert_tables.sql
│   │   └── 005_create_sync_tables.sql
│   ├── requirements.txt
│   ├── run.py                             # 서버 실행 진입점
│   └── README.md
│
└── tests/                                 # [TEST 소유]
    ├── conftest.py                        # 공통 fixtures
    ├── backend/
    │   ├── test_auth.py                   # 인증 API 테스트
    │   ├── test_work_api.py               # 작업 API 테스트
    │   ├── test_process_validator.py      # 공정 검증 테스트
    │   ├── test_duration_validator.py     # duration 검증 테스트
    │   ├── test_alert_service.py          # 알림 서비스 테스트
    │   └── test_websocket.py              # WebSocket 테스트
    ├── frontend/
    │   ├── test_task_management.dart       # Task UI 테스트
    │   ├── test_auth_flow.dart            # 인증 플로우 테스트
    │   └── test_offline_sync.dart         # 오프라인 동기화 테스트
    ├── integration/
    │   ├── test_full_workflow.py           # 전체 워크플로우 (가입→작업→완료)
    │   ├── test_process_check_flow.py     # 공정 검증 플로우
    │   └── test_concurrent_work.py        # 동시 작업 테스트
    └── fixtures/
        ├── sample_workers.json
        ├── sample_products.json
        └── sample_tasks.json
```

## 작업 우선순위

### Sprint 1: 인증 + DB 기반 (2주)
1. **BE**: DB 마이그레이션 스크립트 (5개 테이블) → JWT 인증 → 회원가입/로그인 API
2. **FE**: 회원가입/로그인/이메일인증 화면 → API 연동
3. **TEST**: 인증 API 테스트 → 이메일 인증 플로우 테스트

### Sprint 2: Task 핵심 플로우 (2주)
1. **BE**: 제품조회 API → 작업 시작/완료 API → completion_status 업데이트
2. **FE**: QR 스캔 화면 → Task 목록 → 시작/완료 터치 UI
3. **TEST**: 작업 API 테스트 → Task 플로우 통합 테스트

### Sprint 3: 공정 검증 + 알림 (2주)
1. **BE**: 공정 누락 검증 로직 → 알림 API → WebSocket 이벤트
2. **FE**: 공정 누락 팝업 → 관리자 알림 화면 → WebSocket 연결
3. **TEST**: 공정 검증 테스트 → 알림 테스트 → WebSocket 테스트

### Sprint 4: 관리자 + 오프라인 (2주)
1. **BE**: 관리자 API (승인, Task 보정) → 퇴근시간 자동감지 cron
2. **FE**: 관리자 대시보드 → 오프라인 동기화 → 위치 추적
3. **TEST**: 관리자 플로우 테스트 → 오프라인 동기화 테스트 → 통합 테스트

---

## Sprint 1 상세 작업 지시

### BE 워커 — Sprint 1 작업 순서
```
1. backend/migrations/001_create_workers.sql 검토 및 보완
2. backend/migrations/002_create_product_info.sql 검토 및 보완
3. backend/app/models/worker.py — CRUD 함수 구현 (psycopg2)
4. backend/app/services/auth_service.py — register, login, verify_email 구현
5. backend/app/middleware/jwt_auth.py — jwt_required 데코레이터 구현
6. backend/app/routes/auth.py — 4개 엔드포인트 구현
7. backend/app/__init__.py — app factory에서 auth blueprint 등록 확인
8. backend/run.py — 서버 실행 테스트
```

### FE 워커 — Sprint 1 작업 순서
```
1. frontend/lib/services/api_service.dart — Dio + JWT interceptor 구현
2. frontend/lib/services/auth_service.dart — login, register, verifyEmail 구현
3. frontend/lib/models/worker.dart — fromJson/toJson 완성
4. frontend/lib/providers/auth_provider.dart — AuthNotifier 상태 관리 구현
5. frontend/lib/screens/auth/login_screen.dart — 로그인 UI 구현
6. frontend/lib/screens/auth/register_screen.dart — 회원가입 UI 구현 (역할 선택 포함)
7. frontend/lib/screens/auth/verify_email_screen.dart — 이메일 인증 화면
8. frontend/lib/main.dart — 라우팅 설정 (인증 상태에 따른 화면 분기)
```

### TEST 워커 — Sprint 1 작업 순서
```
1. tests/conftest.py — Flask test app fixture, test DB 연결 구현
2. tests/fixtures/sample_workers.json — 테스트 데이터 보완
3. tests/backend/test_auth.py — 6개 인증 테스트 케이스 구현
4. pytest 실행 확인 (backend 테스트만)
```

---

## 충돌 방지 규칙

| 에이전트 | 쓰기 가능 | 읽기 가능 | 절대 수정 금지 |
|---------|----------|----------|--------------|
| FE | `frontend/**` | 모든 파일 | `backend/**`, `tests/**` |
| BE | `backend/**` | 모든 파일 | `frontend/**`, `tests/**` |
| TEST | `tests/**` | 모든 파일 | `backend/app/**`, `frontend/lib/**` |

**공유 파일 (수정 전 리드 승인 필수)**:
- `CLAUDE.md` — 리드만 수정 가능
- API 인터페이스 변경 시 → 리드가 FE/BE 양쪽에 동기화 지시
