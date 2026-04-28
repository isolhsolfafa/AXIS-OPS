# G-axis App — Agent Teams 프로젝트

## 프로젝트 개요
GST 제조 현장 작업 관리 시스템. 스프레드시트 수동 입력 → 모바일 App 실시간 Push 전환.
Clean Cut 전략: 기존 PDA는 그대로 유지, App MVP를 별도 개발 후 테스트 완료 시 일괄 전환.

## 팀 구성 & 모델 설정

### 리드 에이전트 (Lead — 설계 조율)
- **모델**: Opus 최상위 — **2026-04-21 현재 `claude-opus-4-7`** ⚠️ 신 모델 출시 시 갱신
- **역할**: 전체 아키텍처 설계, 에이전트 간 조율, 코드 리뷰, 의사결정
- **모드**: Delegate 모드 (Shift+Tab) — 리드는 직접 코드 작성하지 않고 조율만 수행
- **권한**: 모든 파일 읽기 가능, 직접 수정은 하지 않음

### 워커 에이전트 (Workers — 구현/테스트)
- **모델**: Sonnet 최상위 — **2026-04-21 현재 `claude-sonnet-4-6`** ⚠️ 신 모델 출시 시 갱신
- **역할**: FE, BE, TEST 각각 담당 영역의 코드 구현
- **모드**: 사용자 승인 후 코드 수정 가능 (위임 모드)

### ⚠️ 모델 버전 관리 규칙 (2026-04-21 추가, 2026-04-24 Codex 섹션 보강)

#### Claude 모델 (Opus 리드 / Sonnet 워커)

- **원칙**: 항상 각 티어의 **최상위 모델** 사용 (Opus = 리드, Sonnet = 워커)
  - 리드는 설계·아키텍처 판단 역할 → 추론 성능 최우선 → Opus 최상위
  - 워커는 대량 구현·테스트 → 처리량·비용 균형 → Sonnet 최상위
  - 하위 모델 사용 금지 (설계 오류·컨텍스트 누락 리스크)
- **업데이트 트리거**: 새 Claude 모델(Opus/Sonnet) 릴리스 감지 시 이 섹션 즉시 갱신
- **세션 시작 체크**: Claude Code / Cowork 시작 시 현재 가용 모델 확인 → CLAUDE.md 기재 버전과 대조 → 신규 있으면 **먼저 갱신 후** 작업 시작
- **갱신 시 업데이트 대상**:
  - `AXIS-OPS/CLAUDE.md` (이 파일) L10, L16
  - `AXIS-VIEW/CLAUDE.md` L33, L39
  - `memory.md`에 ADR 추가 (모델 전환 이유·영향)

#### Codex (외부 교차 검증자) — 2026-04-24 보강

- **원칙**: Codex CLI 기본 모델(= 자동 최신) 유지 — `~/.codex/config.toml` 에 model **pinning 금지**
  - 이유: Codex CLI가 최신 GPT 모델을 자동 수신하도록 설계됨. pinning 시 구 모델 고착 위험
  - 현재 설치: `codex-cli 0.122.0` (2026-04-24 기준)
- **업데이트 트리거**:
  - 주 1회 이상 `brew outdated codex` 수동 확인 (권장: 매주 월요일 Sprint 시작 시)
  - Codex 메이저 업데이트(0.X → 0.Y) 발견 시 즉시 `brew upgrade codex` 후 CLAUDE.md 버전 갱신
  - GPT 신 모델(GPT-5.x 등) 출시 감지 시 Codex CLI가 자동 수신하는지 `codex doctor` 또는 공식 페이지로 확인
- **세션 시작 체크** (Claude 모델 체크와 병행):
  ```bash
  codex --version              # 현재 CLI 버전
  brew outdated codex          # 업데이트 가용 여부
  ```
- **검증 라운드 trail 기록**: `memory.md` ADR 또는 `CROSS_VERIFY_LOG.md` 에 사용 모델·CLI 버전 병기
  - 예: `"2026-04-24 / Codex CLI 0.122.0 / 검증 결과: M=2 A=1"`
- **갱신 시 업데이트 대상**:
  - `AXIS-OPS/CLAUDE.md` (이 파일) 이 섹션 "현재 설치" 라인
  - `AXIS-VIEW/CLAUDE.md` 동일 섹션
  - `memory.md` ADR (메이저 업데이트 시)
- **실패 시 fallback**: Codex CLI 업데이트 불가 상황(네트워크·권한)이면 당일 Sprint 교차검증을 Claude Code 자가 리뷰로 대체 + 다음 세션에 Codex 재실행 의무

### 위임 모드 규칙
1. 리드가 작업을 분배하고 워커에게 위임
2. 워커는 코드 변경 전 **반드시 사용자 승인** 필요
3. 파일 소유권 위반 시 즉시 중단
4. 스프린트 단위로 작업 진행 (현재 Sprint 1부터 시작)

## 세션 컨텍스트 문서
- `memory.md` — 누적 의사결정, 감사 결과, APS 분석 (세션 간 영구 기록)
- `handoff.md` — 세션 인계용. 현재 진행상황, 대기 Sprint, 다음 할 일

## 참조 문서
- `APP_PLAN_v4(26.02.16).md` — **주 참조 문서**. App 설계/로직/API/DB 스키마 전체 정의
- `PROJECT_COMPREHENSIVE_ANALYSIS_2026(02.16).md` — ⚠️ **부분 참조만 허용** (아래 규칙 준수)
  - ✅ 참조 가능: 섹션 1.1(비즈니스 목표), 섹션 6(기술 스택), 섹션 14(브랜드/로고)
  - ❌ 절대 참조 금지: 섹션 8.4(시간 계산 로직 — calculate_working_hours 사용 금지), 섹션 13(하이브리드 전환 분석 — Clean Cut으로 폐기), 섹션 2/4/5/9/11(구 전략/일정 — 전부 구버전)
  - ❌ 이 문서의 `info` 테이블, `google_doc_id`, `worksheet` 참조 금지 → 반드시 `product_info`, `qr_doc_id` 사용

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
- 카메라(QR 스캔): `html5-qrcode` JS interop 사용 (web/index.html에 스크립트 추가 + dart:js_interop 래핑)

### FE 에이전트 주의사항
- `flutter build web` 기준으로 개발
- 네이티브 전용 플러그인 사용 금지 (웹 미지원 플러그인 X)
- QR 스캔: `mobile_scanner` 사용 금지 → `html5-qrcode` JS interop만 사용 (iOS Safari PWA 호환성 보장)
- 로컬 저장소: SQLite 대신 `shared_preferences` 또는 `hive` (웹 호환)
- 반응형 UI: 모바일 브라우저 기준 설계 (375px ~ 428px 너비)

## AI 검증 워크플로우 (Claude-Codex 교차 검증, 2026-04-21 개정 v2)

### 3주체 용어 정의

- **Claude Cowork**: Claude 기반 설계 환경 (대화형 설계 초안 md 산출)
- **Claude Code**: Claude 기반 로컬 CLI (로컬 맥락 접근 + 코드 구현)
- **Codex**: 외부 독립 모델 (Claude 견해 편향 제거용 교차 검증자)

### 스프린트 파이프라인 (9단계 · ⑦.5 사용자 승인 게이트 포함)

```
① Claude Cowork → 설계 초안 md 작성 (AGENT_TEAM_LAUNCH.md)

② Claude Code (Opus Lead) → 1차 리뷰 + 쟁점 압축
   · 로컬 맥락(CLAUDE.md / memory / handoff) 대조
   · 사소한 이슈(오타·서식·설계서 문구만)는 설계서 내 직접 수정
   · ⚠️ 설계서의 **조건·API 응답 필드·데이터 플로우·숫자 임계값** 변경은 "사소함" 불인정 → 사용자 승인 필수
   · ⚠️ 코드 수정은 ⑥ 구현 단계 전까지 금지 (사용자 승인 필수)
   · 중대 쟁점만 Codex용 프롬프트 생성
   · Codex 프롬프트에 관련 ADR/원칙 원문 인용 첨부 (맥락 보완)

③ /codex:review → 압축 프롬프트 전달 → Codex 독립 검증 + M/A 라벨

④ Claude Code → Codex 지적 대조 (1라운드 상한)
   · 수용/반박 의견 설계서 기록
   · Codex 응답이 침묵 승인(예: "LGTM", "문제 없음" 류 한 줄 답변)이면
     → 자동 재질문 ("구체적으로 검토한 부분과 잠재 리스크 재답변")
   · ⚠️ 구체성 부족으로 인한 자동 재질문은 라운드 카운트 제외
     (실질적 쟁점 교환이 아닌 "응답 품질 보강"이므로 1라운드 상한 무관)
   · ⚠️ Claude가 Codex 지적을 **즉시 수용(1라운드 내)**하는 경우에도
     "Claude 원안의 약점" 을 설계서에 한 줄 기록 — 맹목 동조 방지, 사후 trail 확보

⑤ 합의 분기
   · 합의 M(Must) → 구현 전 필수 해결
   · 합의 A(Advisory) → BACKLOG 등록 (기본 🟡 LOW, Must 강등 시 🟠 MEDIUM 병기)
   · **M→A 재라벨 정상 경로**: Claude-Codex 2자 합의로만 가능. Claude 단독 강등 금지
   · 합의 실패 정의: Codex 반박 1회 + Claude 재반박 1회 후에도 불일치
     → 사용자 최종 판정 (M 유지 / A 강등 / 기각)

⑥ 확정 설계서 → 구현 (이 단계부터 코드 수정 허용)

⑦ 테스트 GREEN 확인
   · BE: `pytest -q` (회귀)
   · Migration: `flask db upgrade` / 관련 migration 테스트
   · FE 테스트 경로는 별도 문서(재공유 예정) — OPS CLAUDE.md 에서는 BE·Migration 만 강제
   · 실패 항목 → Codex 합의 후 수정 → 재실행 (전건 GREEN까지 반복)

   ⚠️ **실패 발견 시 강제 절차 (2026-04-22 추가 — HOTFIX-ALERT-SCHEDULER-DELIVERY 세션 위반 사례 반영)**:
   a. Claude 단독 "범위 외 판단" **절대 금지**
      — "본 Sprint 와 무관해 보여" / "결과적으로 맞을 것 같아" 휴리스틱 배제
   b. 실패 테스트 정보 정리 (필수):
      - 테스트 파일:라인 + 실패 메시지 전문
      - 본 Sprint 수정 파일 목록 + 실패 테스트가 참조하는 코드 경로
      - 파일 겹침 / import 체인 / 데이터 플로우 분석 1줄
   c. Codex 쿼리 구성 → `/codex:rescue` 또는 이관 프롬프트로 전달
   d. Codex M/A 라벨 수신 후에만 조치:
      - M(Must) → 본 Sprint 에 포함 or 선행 fix Sprint 분리
      - A(Advisory) → BACKLOG 이관 (이관 trail 을 설계서 § Codex 합의 기록 에 추가)
   e. 판정 trail 은 설계서 § Codex 합의 기록 에 1줄 기록 (위반 방지)

   > 이 강제 절차는 AI 검증 워크플로우 L98-103 (침묵 승인 거부) 와 L149 (Codex 독립) 의 실패 경로 특화 버전.
   > "결과적으로 맞을 것 같다" 는 판단이 실제로 맞더라도 절차 위반이며, 사후 Codex 재검토 대상.

⑦.5 사용자 배포 승인 (Twin파파)
   · 테스트 GREEN ≠ 자동 배포. Twin파파의 명시적 "배포 OK" 승인 필수
   · HOTFIX S1 제외 (🚨 긴급 HOTFIX 예외 조항 참조)

⑧ 머지/배포
```

### ② 단계 Codex 이관 자동 체크리스트

> Opus가 "사소함"으로 분류해서 Codex로 안 넘기는 누락 편향을 방지.
> 아래 6가지 중 **1개라도 해당**되면 **자동 Codex 이관** (Opus 재량 제외).

- [ ] DB 스키마 변경 (migration 동반)
- [ ] API 응답 계약 변경 (breaking change 가능성)
- [ ] FK/PK/인덱스 변경
- [ ] 인증·권한 로직 변경
- [ ] 클린 코어 데이터 원칙 영향 여부 (강제종료·duration·wsl/wcl 관련)
      → 원칙 전문: `BACKLOG.md` 📐 설계 원칙 § 클린 코어 데이터 원칙 (2026-04-20)
- [ ] 3개 이상 파일 touch

> ⚠️ **판정 애매 시 = 자동 이관 (의심 시 포함)**: 위 6항목 중 "영향 여부 판정이 주관적으로 갈릴 여지"가 보이면 Opus는 이관 쪽으로 판단. 원래 막으려던 "사소함 편향" 재발 방지용.
> **"touch" 정의**: 신규 파일 · 테스트 파일 · 3줄 이상 code 변경 파일 모두 포함. comment-only / 서식만 변경은 제외.

### 핵심 규칙 7가지

1. **설계서 선행** — 코드 작성 전 반드시 md 설계서 완료
2. **설계 단계 교차 검증** — 구현 전 검증으로 재작업 방지
3. **합의 기반 보정** — 맹목 수용 금지, 근거 없는 반박도 금지
4. **Opus 1차 리뷰** — 쟁점 압축으로 Codex 응답 시간 단축
5. **M/A 라벨링 = Codex 독립** — Claude 편향 제거
6. **라운드 상한 1회** — 핑퐁 방지, 합의 실패는 즉시 사용자 에스컬레이션
7. **테스트 실패 → Codex 합의 후 수정** — 빌드·pytest·회귀 전부 동일

### 🚨 긴급 HOTFIX 예외 조항

> 프로덕션 장애 시 정식 파이프라인 skip 허용. 사후 검토 필수 (Google SRE Book / Microsoft SDL 관례 준수).

| Severity | 조건 | 프로세스 | 사후 조치 |
|---|---|---|---|
| **S1** 🚨 | 전체 서비스 장애 (로그인 불가·DB down·모든 API 500 등) | **Codex만 skip** (Opus 자가 리뷰 필수: 로컬 맥락 대조 + 회귀 영향 1분 스캔) → 즉시 패치 배포 | **24h 이내** 사후 Codex 검토 + BACKLOG `POST-REVIEW-{HOTFIX-ID}` 등록 |
| **S2** 🟠 | 부분 장애 (특정 기능 차단·오류율 10%+) | Opus 단독 리뷰 → 배포 | **7일 이내** 또는 다음 Sprint 시작 전 중 이른 시점 Codex 검토 필수 + BACKLOG `POST-REVIEW-{HOTFIX-ID}` 등록 |
| **S3~** | 일반 버그·UX 이슈 | 정상 파이프라인 | — |

**판정 기준**: S1/S2 여부는 Twin파파 단독 판정. 애매하면 S2로 처리 (보수적).

### 우선순위 라벨 (4단계)

- 🔴 **HIGH** — 배포 블로커 / 실데이터 장애 / 보안 이슈 (즉시 패치)
- 🟠 **MEDIUM** — 다음 Sprint 내 해결 (기능 제약 있으나 우회 가능)
- 🟡 **LOW** — BACKLOG, 여유 Sprint에 소화
- 🟢 **INFO** — 변경 요청 아님, 참고/기록용

### 교차 검증 원칙

- **전수 검증**: 설계서 전체를 코드/기존 시스템과 대조 — 특정 항목만 체크하지 않음
- **맹목 수용 금지**: 지적 사항은 Claude와 대조하여 합의된 항목만 반영
- **M/A 분류**: Codex 지적은 M(Must fix), A(Advisory) 로 구분하여 공유
- **침묵 승인 거부**: Codex가 구체성 없는 OK 응답 시 자동 재질문

### 재검토 조건 (이 플로우는 완벽하지 않음)

다음 조건 중 하나라도 충족 시 워크플로우 재개정:

1. Codex가 로컬 파일 직접 접근 가능해지면 → ② 쟁점 압축 단계 단순화
2. 제3의 독립 모델 도입 시 → 3자 검증 도입 검토
3. 실제 합의 실패율 20%+ 관찰 시 → 라운드 상한 2회로 완화 검토
   - **측정 정의**: 합의 실패율 = (사용자 판정 에스컬레이션 건수) / (Codex 검증 완료 설계서 수)
   - **trail 기록 위치**: `memory.md` 또는 별도 `CROSS_VERIFY_LOG.md` 에 Sprint별 누적 기록

---

## 핵심 규칙 (모든 에이전트 공통)

### DB 규칙
- `qr_doc_id` 사용 (`google_doc_id` 사용 금지)
- `plan.product_info` 테이블 사용 — plan 스키마 (`info` 테이블 사용 금지)
- `qr_registry` 테이블로 QR ↔ 제품 매핑 (qr_doc_id는 product_info가 아닌 qr_registry에 존재)
- 제품 조회 시: `qr_registry JOIN plan.product_info ON serial_number`
- `duration = completed_at - started_at` (calculate_working_hours 함수 사용 금지)
- Staging DB 기준 개발 (PDA Production DB 절대 건드리지 않음)
- DB 타임존: `Asia/Seoul` (KST)
- **운영 데이터 보존 규칙**: 테스트 실행 시 아래 테이블 데이터는 반드시 백업/복원 (DELETE/TRUNCATE 금지)
  - `workers` — 실서비스 계정 (conftest.py 백업/복원 ✅)
  - `hr.worker_auth_settings` — PIN 설정 (conftest.py 백업/복원 ✅)
  - `hr.partner_attendance` — 출퇴근 기록 (conftest.py 백업/복원 ✅)
  - `qr_registry` — QR↔제품 매핑 (conftest.py 백업/복원 ✅)
  - `plan.product_info` — 생산 메타데이터 (conftest.py 백업/복원 ✅)
  - 테스트 cleanup fixture는 `WHERE created_at >= test_start` 조건으로 테스트 생성 데이터만 삭제
  - **최종 목표**: 사내 WAS DB로 마이그레이션 → production/test DB 분리 운영

### DB 스키마 구조 (Staging DB — 3-Tier)
```
plan 스키마 (생산관리 — ETL 적재):
  product_info — 생산 메타데이터 (S/N, model, 일정, 협력사)

public 스키마 (App 운영 — 14개 테이블):
  qr_registry          — QR ↔ 제품 매핑 브릿지 (qr_doc_id, serial_number, status)
  workers              — 작업자/관리자 계정
  email_verification   — 이메일 인증 코드
  app_task_details     — 작업 상세 (FK→qr_registry.qr_doc_id)
  completion_status    — 공정 완료 상태 (FK→qr_registry.serial_number)
  app_alert_logs       — 알림 로그
  work_start_log       — 작업 시작 이력
  work_completion_log  — 작업 완료 이력
  location_history     — 위치 이력
  offline_sync_queue   — 오프라인 동기화 큐
  product_bom          — BOM 목록 (Phase 2)
  bom_checklist_log    — BOM 검증 (Phase 2)
  documents            — PDA 기준 참조용 유지

defect 스키마 (추후 — 불량 분석, 추적, 리포트)
```

**FK 체인:**
```
app_task_details.qr_doc_id      → qr_registry.qr_doc_id
completion_status.serial_number → qr_registry.serial_number
qr_registry.serial_number      → plan.product_info.serial_number
```

**조회 흐름:**
```
QR 스캔 → qr_registry(qr_doc_id) → serial_number 획득
  → plan.product_info JOIN (제품 상세)
  → app_task_details 조회 (Task 목록)
```

- PDA 전용 테이블 11개 삭제 완료 (worksheet, task_summary, stats 등)
- DB 타임존: `Asia/Seoul` (KST)

### ⚠️ DB 테이블 정확한 컬럼 명세 (Staging DB 기준 — 반드시 준수)
> **주의**: 아래 컬럼명은 Staging DB에 실제 존재하는 이름입니다.
> migration SQL, Python model, Flask route 모두 이 컬럼명을 정확히 사용해야 합니다.

#### 1. workers (11컬럼) ✅ 코드 일치
```sql
id SERIAL PK, name VARCHAR(255) NOT NULL, email VARCHAR(255) UNIQUE NOT NULL,
password_hash VARCHAR(255) NOT NULL, role role_enum NOT NULL (MM/EE/TM/PI/QI/SI),
approval_status approval_status_enum DEFAULT 'pending' (pending/approved/rejected),
email_verified BOOLEAN DEFAULT FALSE, is_manager BOOLEAN DEFAULT FALSE,
is_admin BOOLEAN DEFAULT FALSE,
created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```
- 트리거: update_workers_updated_at ✅
- Python model: Worker dataclass ✅

#### 2. email_verification (6컬럼) ⚠️ Python dataclass 없음
```sql
id SERIAL PK, worker_id INTEGER FK→workers(id) NOT NULL,
verification_code VARCHAR(6) UNIQUE NOT NULL, expires_at TIMESTAMPTZ NOT NULL,
verified_at TIMESTAMPTZ, created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```
- Python model: ❌ dataclass 없음 (Dict 반환) → Sprint 5에서 생성 필요

#### 3. plan.product_info (plan 스키마) ✅ 코드 일치
```sql
-- plan 스키마에 위치 (public 아님!)
id SERIAL PK,
serial_number VARCHAR(255) UNIQUE NOT NULL,
model VARCHAR(255) NOT NULL,
title_number VARCHAR(255),
product_code VARCHAR(255),
sales_order VARCHAR(255),
customer VARCHAR(255),
line VARCHAR(255),
quantity VARCHAR(255) DEFAULT '1',
mech_partner VARCHAR(255),
elec_partner VARCHAR(255),
module_outsourcing VARCHAR(255),
prod_date DATE,                  -- 생산일 (= mech_start)
mech_start DATE,                 -- 기구 시작일
mech_end DATE,                   -- 기구 종료일
elec_start DATE,                 -- 전장 시작일
elec_end DATE,                   -- 전장 종료일
module_start DATE,               -- 모듈(TM) 시작일
pi_start DATE,                   -- PI 가압검사 시작일
qi_start DATE,                   -- QI 공정검사 시작일
si_start DATE,                   -- SI 마무리검사 시작일
ship_plan_date DATE,             -- 출하계획일
location_qr_id VARCHAR(255),
created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```
- ⚠️ `qr_doc_id`는 이 테이블에 없음 → `qr_registry` 테이블에서 관리
- 트리거: update_product_info_updated_at ✅
- Python model: ProductInfo dataclass ✅ (qr_registry JOIN으로 조회)
- BE model: `_BASE_JOIN_QUERY`로 qr_registry + plan.product_info JOIN

#### 4. qr_registry (public 스키마) ✅ 코드 일치
```sql
id SERIAL PK,
qr_doc_id VARCHAR(255) UNIQUE NOT NULL,     -- DOC_{serial_number}
serial_number VARCHAR(255) UNIQUE NOT NULL,  -- FK→plan.product_info
status VARCHAR(20) DEFAULT 'active',         -- active / revoked / reissued
issued_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
revoked_at TIMESTAMPTZ,
created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```
- ETL에서 `plan.product_info` INSERT 후 `qr_registry` INSERT
- App 진입점: QR 스캔 → qr_doc_id로 조회

#### 5. app_task_details (14컬럼) ✅ 코드 일치
```sql
id SERIAL PK, worker_id INTEGER FK→workers(id) NOT NULL,
serial_number VARCHAR(255) NOT NULL,
qr_doc_id VARCHAR(255) FK→qr_registry(qr_doc_id) NOT NULL,
task_category VARCHAR(50) NOT NULL, task_id VARCHAR(100) NOT NULL,
task_name VARCHAR(255) NOT NULL, started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ,
duration_minutes INTEGER, is_applicable BOOLEAN DEFAULT TRUE,
location_qr_verified BOOLEAN DEFAULT FALSE,
created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
UNIQUE (serial_number, task_category, task_id)
```
- 트리거: update_app_task_details_updated_at ✅
- Python model: TaskDetail dataclass ✅

#### 6. completion_status (11컬럼) ✅ 코드 일치
```sql
serial_number VARCHAR(255) PK FK→qr_registry(serial_number),
mm_completed BOOLEAN DEFAULT FALSE, ee_completed BOOLEAN DEFAULT FALSE,
tm_completed BOOLEAN DEFAULT FALSE, pi_completed BOOLEAN DEFAULT FALSE,
qi_completed BOOLEAN DEFAULT FALSE, si_completed BOOLEAN DEFAULT FALSE,
all_completed BOOLEAN DEFAULT FALSE, all_completed_at TIMESTAMPTZ,
created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```
- Python model: CompletionStatus dataclass ✅

#### 7. app_alert_logs (11컬럼) ⚠️ read_at 누락
```sql
id SERIAL PK, alert_type alert_type_enum NOT NULL,
serial_number VARCHAR(255), qr_doc_id VARCHAR(255),
triggered_by_worker_id INTEGER FK→workers(id), target_worker_id INTEGER FK→workers(id),
target_role VARCHAR(50), message TEXT NOT NULL, is_read BOOLEAN DEFAULT FALSE,
created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
-- ❌ read_at TIMESTAMPTZ 추가 필요 (APP_PLAN 스펙: is_read + read_at)
```
- 트리거: ❌ update_app_alert_logs_updated_at 없음 → 추가 필요
- Python model: AlertLog dataclass ⚠️ read_at 필드 추가 필요

#### 8. work_start_log (9컬럼) ⚠️ Python 모델 없음
```sql
id SERIAL PK, task_id INTEGER FK→app_task_details(id) NOT NULL,
worker_id INTEGER FK→workers(id) NOT NULL, serial_number VARCHAR(255) NOT NULL,
qr_doc_id VARCHAR(255) NOT NULL, task_category VARCHAR(50) NOT NULL,
task_id_ref VARCHAR(100) NOT NULL, task_name VARCHAR(255) NOT NULL,
started_at TIMESTAMPTZ NOT NULL, created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```
- Python model: ❌ 없음 → Sprint 5에서 생성 필요

#### 9. work_completion_log (10컬럼) ⚠️ Python 모델 없음
```sql
id SERIAL PK, task_id INTEGER FK→app_task_details(id) NOT NULL,
worker_id INTEGER FK→workers(id) NOT NULL, serial_number VARCHAR(255) NOT NULL,
qr_doc_id VARCHAR(255) NOT NULL, task_category VARCHAR(50) NOT NULL,
task_id_ref VARCHAR(100) NOT NULL, task_name VARCHAR(255) NOT NULL,
completed_at TIMESTAMPTZ NOT NULL, duration_minutes INTEGER,
created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```
- Python model: ❌ 없음 → Sprint 5에서 생성 필요

#### 10. location_history (6컬럼) 🔴 모델 빈 껍데기
```sql
id SERIAL PK, worker_id INTEGER FK→workers(id) NOT NULL,
latitude DECIMAL(10,8) NOT NULL, longitude DECIMAL(11,8) NOT NULL,
recorded_at TIMESTAMPTZ NOT NULL, created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```
- Python model: ❌ from_db_row()가 `pass` → Sprint 5에서 완성 필요

#### 11. offline_sync_queue (9컬럼) ⚠️ Python 모델 없음
```sql
id SERIAL PK, worker_id INTEGER FK→workers(id) NOT NULL,
operation VARCHAR(50) NOT NULL, table_name VARCHAR(100) NOT NULL,
record_id VARCHAR(255), data JSONB,
synced BOOLEAN DEFAULT FALSE, synced_at TIMESTAMPTZ,
created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
```
- Python model: ❌ 없음 → Sprint 5에서 생성 필요

#### 12-13. product_bom, bom_checklist_log — Phase 2 (미구현)

### Admin 계정 정책
관리자 계정은 **Migration Seed 방식**으로 사전 등록 (회원가입/이메일인증/승인 절차 우회):
```sql
-- 006_sprint6_schema_changes.sql 내 포함 (ON CONFLICT DO NOTHING → Sprint 간 초기화 방지)
INSERT INTO workers (name, email, password_hash, role, company,
                     approval_status, email_verified, is_manager, is_admin)
VALUES ('관리자', 'dkkim1@gst-in.com', '<pbkdf2_hash>',
        'ADMIN', 'GST', 'approved', TRUE, TRUE, TRUE)
ON CONFLICT (email) DO NOTHING;
```
- **⚠️ Admin Seed는 반드시 migration SQL 내에 존재해야 함** (Sprint 간 초기화 방지)
- Admin은 일반 회원가입 플로우 불필요 (DB 직접 등록)
- Admin 로그인 시 이메일 인증/승인 체크 건너뜀 (`is_admin = TRUE`면 freepass)
- 비밀번호: `Gst@dmin2026!` (werkzeug pbkdf2:sha256 해시)
- BE auth_service.py의 login 함수에서 admin 분기 처리:
  ```python
  if not worker.is_admin:
      # 일반 사용자만 이메일 인증/승인 체크
      if not worker.email_verified: return 403 (EMAIL_NOT_VERIFIED)
      if worker.approval_status == 'pending': return 403 (APPROVAL_PENDING)
      if worker.approval_status == 'rejected': return 403 (APPROVAL_REJECTED)
  ```

### 로그인 에러 코드 → 화면 분기 정책
| BE 에러 코드 | HTTP | FE 동작 |
|---|---|---|
| `INVALID_CREDENTIALS` | 401 | 로그인 화면에 에러 메시지 표시 |
| `EMAIL_NOT_VERIFIED` | 403 | 로그인 화면에 에러 메시지 표시 |
| `APPROVAL_PENDING` | 403 | **ApprovalPendingScreen으로 네비게이션** |
| `APPROVAL_REJECTED` | 403 | 로그인 화면에 에러 메시지 표시 |

- api_service.dart의 403 처리에서 서버 에러 코드를 `[ERROR_CODE] message` 형식으로 보존
- login_screen.dart에서 에러 메시지에 `APPROVAL_PENDING` 포함 시 ApprovalPendingScreen으로 이동

### 이메일 인증 설정
- 인증 메일 발송 대상 도메인: `@gst-in.com`, `@naver.com`, `@gmail.com`
- SMTP 설정 (.env 파일) — KT Biz Office SSL(465) 사용:
  ```
  SMTP_HOST=jmp.ktbizoffice.com
  SMTP_PORT=465
  SMTP_USER=dkkim1@gst-in.com
  SMTP_PASSWORD=<그룹웨어 비밀번호>
  SMTP_FROM_NAME=G-AXIS
  SMTP_FROM_EMAIL=dkkim1@gst-in.com
  ```
- SMTP 포트 분기: 465=SMTP_SSL 직접 연결, 587=STARTTLS (auth_service.py에서 자동 분기)
- 인증 코드: 6자리 숫자, 유효기간 10분
- 이메일 도메인 제한 없음 (사용자가 직접 입력)
- ⚠️ Rate Limiting: 동일 이메일 시간당 5회 발송 제한 (DoS 방지, `_check_email_rate_limit()`)
- ⚠️ Subject 인코딩: `email.header.Header`로 UTF-8 명시 (한글 깨짐 방지)

### 환경변수 운영 가이드
- **로컬 개발**: `backend/.env` 파일 사용 (`.gitignore`에 포함 — git에 올리지 않음)
- **배포 (Staging/Prod)**: Railway Variables에 동일 키-값 설정 → 배포 시 자동 주입
- **CI/CD (추후)**: GitHub Secrets → GitHub Actions에서 사용
- 테스트 시 Railway에 배포된 Flask API로 테스트 (Railway Variables 환경)
- 필수 환경변수 목록:
  ```
  DATABASE_URL          — PostgreSQL 연결 문자열
  JWT_SECRET_KEY        — Access Token 서명 키
  JWT_REFRESH_SECRET_KEY — Refresh Token 서명 키 (Access와 반드시 분리)
  SMTP_HOST             — smtp.gmail.com
  SMTP_PORT             — 587
  SMTP_USER             — 발송용 Gmail 계정
  SMTP_PASSWORD         — Gmail 앱 비밀번호
  SMTP_FROM_NAME        — G-AXIS
  SMTP_FROM_EMAIL       — noreply@gst-in.com
  ```

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

## 📏 코드 크기 원칙 (2026-04-21 확정)

> **배경**: 2026-03-22 AXIS SYSTEM 점검 보고서에서 admin.py 2,070줄(God Route), task_service.py 1,018줄 지적 후에도 파일이 계속 비대화됨 (현재 admin.py 2,546줄). 업계 표준(ESLint 300 / SonarQube 200~750 / Google Python 500)을 기준으로 GST 현실에 맞춰 단계적 도입.

### 파일당 최대 LOC (단계적 도입)

| 단계 | 적용 시점 | 🟡 경고 (리팩토링 계획 수립) | 🔴 필수 분할 | ⛔ God File |
|---|---|---|---|---|
| **1단계 (현재)** | 2026-04-21 ~ | **500줄** | **800줄** | **1200줄** |
| 2단계 | APS Lite 연동 전 (~2026 Q3) | 400줄 | 600줄 | 1000줄 |
| 3단계 (업계 표준) | APS Lite 연동 후 | 300줄 | 500줄 | 800줄 |

### 함수·클래스 (1단계부터 엄격 적용)

- 함수 1개: **60줄 이하** (권장 30줄, 절대 한도 100줄)
- 클래스 1개: **200줄 이하**
- 매개변수: **4개 이하** (5개 이상 → dict/dataclass로 묶기)
- 순환 복잡도 (Cyclomatic): **≤ 10**
- 중첩 깊이: **≤ 3단계**

### 적용 규칙

- 🟡 경고 임계 초과 시: Sprint 시작 전 BACKLOG에 `REFACTOR-{파일명}` 등록
- 🔴 필수 분할 파일: **새 로직 추가 금지** → 분할 Sprint 선행 필수
- ⛔ God File: 즉시 BACKLOG 최상단 + 분할 Sprint 우선순위 🔴 HIGH
- 예외: 자동 생성 파일(`version.py`, migration SQL), 테스트 파일(`tests/**`)

### 측정 명령어 (Sprint 시작 전 체크 필수)

```bash
# 대상 파일 Top 10
find backend/app -name "*.py" | xargs wc -l | sort -rn | head -10
find frontend/lib -name "*.dart" | xargs wc -l | sort -rn | head -10

# Python 복잡도 분석
pip install radon
radon cc backend/app -a -nc -s
```

---

## 🔄 재활용 원칙 — DRY (Don't Repeat Yourself)

> **배경**: `formatDateTime` 중복 2건 발견(REFACTOR-FMT-01) 등, 복사+수정 패턴이 파일 크기 비대화의 근본 원인. 재활용은 Line 수를 **줄이지 절대 늘리지 않음**.

### 코드 작성 전 필수 절차 (모든 Sprint 공통)

```
① 새 함수/클래스/유틸 작성 전 → 기존 구현 존재 여부 grep 검색 필수
   → 유사 로직 발견 시: 재활용 또는 공통 유틸로 승격

② Rule of Three (3의 법칙)
   - 같은 로직 2곳 반복: 의식적 선택 (용인 or 승격)
   - 같은 로직 3곳 이상: 무조건 공통화 (Sprint 선행)

③ 승격 위치 (BE)
   - 범용 유틸: backend/app/utils/
   - 비즈니스 로직: backend/app/services/{domain}_service.py
   - 데이터 접근: backend/app/models/
   - 검증 로직: backend/app/services/{domain}_validator.py
```

### 검색 명령어 (Sprint 시작 전)

```bash
# 유사 함수 검색 예시
grep -rn "def format_date\|def _format_date" backend/app/
grep -rn "def calculate_duration" backend/app/

# 공통 유틸 현황
ls backend/app/services/
ls backend/app/utils/ 2>/dev/null || echo "utils 없음 (필요 시 생성)"
```

### 중복 발견 시 BACKLOG 등록 규칙

- 2곳 중복: `REFACTOR-{함수명}` Advisory 등록 (낮은 우선순위)
- 3곳+ 중복: Sprint 선행 (신규 기능보다 우선)

### 🚫 금지 패턴

- ❌ 비슷한 로직을 복사+수정해서 새 함수 만들기 (예: `format_date` → `format_date_kr` → `format_date_short`)
- ❌ 파일 내부 private 유틸 방치 (다른 파일에서도 또 만들게 됨)
- ❌ "일단 구현하고 나중에 공통화" (나중은 안 옴)

### ✅ 권장 패턴

- 공통 유틸 먼저 검색 → 없으면 `services/` 또는 `utils/`에 **먼저 만들고** → 호출
- 옵션 파라미터로 변형 흡수 (`format_date(d, with_time=True, fallback='-')`)
- 서비스 재사용 (예: `get_managers_by_partner()` 한 번 만들고 전체 알림 트리거에서 재사용 — ADR-010 참조)

### GST 기존 참조 사례

- ✅ REFACTOR-FMT-01 (VIEW): `ChecklistReportView.tsx` 로컬 `formatDateTime` → `utils/format.ts` 승격 → 다른 페이지 import 재사용
- ✅ ADR-010: `_partner_to_company()` 역방향 매핑 함수 도입 → 알림 트리거 5군데 공통 사용
- ✅ ADR-018: `TaskDetail.closed_by_name` 모델 레벨 바인딩 → 어떤 응답 경로에서도 자동 일관 (후처리 루프 복제 회피)

---

## 🛡️ 리팩토링 안전 규칙 (Regression 방지 7원칙)

> **배경**: admin.py 2,546줄, task_service.py 1,478줄 등 God File 다수 존재. 대형 리팩토링은 Regression 리스크가 최대. 안전장치 7원칙 필수 준수.

### 7원칙 (리팩토링 Sprint는 일반 Sprint와 규칙이 다름)

```
1. 테스트 커버리지 확인 선행
   - 대상 파일/함수의 pytest 전부 GREEN 확인
   - 테스트 없으면 → 리팩토링 전에 테스트 Sprint 먼저 (별도 분리)
   - 최소 커버리지 기준: 핵심 비즈니스 로직 80%+

2. 기능 변경 절대 금지
   - 리팩토링 Sprint = "동작 100% 동일, 구조만 변경"
   - 버그 수정·기능 추가·최적화와 같은 커밋에 섞지 않기
   - 커밋 메시지 prefix: [REFACTOR] 필수

3. 작은 단위로 쪼개기
   - 2000줄+ 파일을 한 번에 5개로 쪼개지 않기
   - 한 Sprint당 이동 줄 수 상한: 500줄
   - 점진적 분할 (예: admin.py → 6 Sprint에 걸쳐)

4. Before/After 테스트 GREEN 증명
   - 리팩토링 전: pytest 전체 결과 기록 (PASS 개수·테스트명)
   - 리팩토링 후: 동일 테스트가 동일 결과
   - Sprint PR에 명시 필수: "Before: X PASS → After: X PASS, 회귀 0"

5. Claude×Codex 교차검증 필수 (1순위 대상)
   - 리팩토링은 교차검증 대상 1순위 (기능 변경보다 엄격)
   - Codex M(Must) 지적 전부 해결 후 머지
   - 설계서 = diff 계획서 (이동 줄 수, 새 파일 경로, import 변경 목록)

6. 단계적 배포 (Canary)
   - BE: Railway staging 먼저 → 1~2일 현장 관찰 → prod
   - 장애 없이 유지되면 다음 Sprint 시작

7. 롤백 플랜 사전 준비
   - git 태그 `pre-refactor-{sprint}` 먼저 생성
   - Sprint 단위 revert 가능한 상태 확보
   - DB 변경 금지 (리팩토링 Sprint에는 migration 포함 안 함)
```

### 리팩토링 Sprint 체크리스트 (PR 머지 전 필수)

- [ ] 대상 파일 pytest GREEN (Before)
- [ ] 리팩토링 완료 후 동일 pytest GREEN (After)
- [ ] PASS 개수·테스트명 100% 일치
- [ ] `[REFACTOR]` 커밋 prefix 적용
- [ ] DB migration 포함 안 됨 확인
- [ ] git 태그 `pre-refactor-{sprint}` 생성됨
- [ ] Codex 교차검증 M 해결됨
- [ ] BACKLOG 해당 REFACTOR 항목 체크

### 상세 리팩토링 계획

→ **`BACKLOG.md` 🔧 리팩토링 Sprint 계획 섹션 참조** (파일별·단계별 Sprint 일정)

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
- 공정 검증 로직 (MECH/ELEC 완료 체크)
- 관리자 알림 API (app_alert_logs)
- WebSocket 이벤트 (Flask-SocketIO)
- DB 마이그레이션 스크립트

**인증/권한 데코레이터** (`backend/app/middleware/jwt_auth.py`):
| 데코레이터 | 용도 | 선행 조건 | 추가 시점 |
|---|---|---|---|
| `@jwt_required` | JWT Bearer 토큰 검증 → g.worker_id, g.worker_email, g.worker_role 설정 | 없음 | Sprint 1 |
| `@admin_required` | is_admin=True 검증 (관리자 전용 API) | @jwt_required 선행 필수 | Sprint 1 |
| `@manager_or_admin_required` | is_admin=True OR is_manager=True 검증 (관리자/협력사 매니저 공용 API) | @jwt_required 선행 필수 | Sprint 6 |

사용 예시:
```python
@app.route('/api/admin/tasks/<int:task_id>/force-close', methods=['PUT'])
@jwt_required
@manager_or_admin_required
def force_close_task(task_id: int):
    ...
```

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

### Sprint 4: 관리자 + 오프라인 (2주) ✅ 완료

### Sprint 5: 보안 + PWA + 이메일 + 잔여 모델 (1주) ✅ 완료 (보완 필요)
> ✅ DB 스키마 사전 작업 완료: plan.product_info + qr_registry 분리, 컬럼명 간소화, ETL 동기화, PDA 테이블 삭제
1. **BE (migration SQL 동기화 + 누락 모델)**: ✅ 완료
   - `003_create_task_tables.sql` FK 수정: `qr_registry(qr_doc_id)`, `qr_registry(serial_number)` ✅
   - 누락 Python 모델 3개 생성 ✅ / location_history 완성 ✅ / alert_log read_at ✅ / worker EmailVerification ✅
2. **BE (보안 + 이메일)**: ✅ 완료
   - .env 분리 ✅ / SMTP 연동 ✅ / Refresh Token ✅
3. **FE**: PWA 빌드 성공 ✅
4. **TEST**: 54개 테스트 구현 (test_models 25 + test_email 12 + test_refresh_token 17)

#### ⚠️ Sprint 5 보완 필요 사항 (Sprint 6 전에 반드시 완료):
1. **product_info.py — ProductInfo dataclass 15개 컬럼 추가**: 현재 10개 필드만 있음. plan.product_info 25개 컬럼 중 title_number~ship_plan_date 15개 누락. `_BASE_JOIN_QUERY` SELECT절도 동기화 필요
2. **SMTP Subject UTF-8 인코딩**: `email.header.Header`로 한글 Subject 인코딩 명시 (일부 메일 클라이언트 깨짐 방지)
3. **이메일 Rate Limiting 추가**: 시간당 5회 제한 (DoS 방지). 메모리 기반 `_check_email_rate_limit()` 함수 추가
4. **test_refresh_token.py 5개 테스트 보충**: PROGRESS.md 22개 주장 vs 실제 17개. access↔refresh 혼용 방지 등 5개 추가 필요
5. **PROGRESS.md 테스트 카운트 정정**: test_email 8→12, test_refresh_token 22→17(보충 후 22), 합계 55→59

### Sprint 6: Task 재설계 + 네이밍 변경 + Admin 옵션 (1~2주)
> ⚠️ 네이밍 변경: MM→MECH, EE→ELEC (전체 코드베이스 22+ 파일 영향)
> ⚠️ Task 재설계: 기존 27개(MM19+EE8) → 15개(MECH7+ELEC6+TMS2)
1. **BE (Phase A — 네이밍 + DB 변경)**:
   - `role_enum` 변경: MM→MECH, EE→ELEC, ADMIN 추가 (migration SQL)
   - `workers` 테이블에 `company VARCHAR(50)` 컬럼 추가
   - `model_config` 테이블 신설 (model_prefix, has_docking, is_tms, tank_in_mech)
   - `admin_settings` 테이블 신설 (key-value 구조, heating_jacket_enabled, phase_block_enabled 등)
   - 기존 코드 MM→MECH, EE→ELEC 전수 교체 (auth_service, task_service, process_validator, completion_status, work.py)
2. **BE (Phase B — Task Seed 재설계)**:
   - Task 템플릿 15개 정의 (MECH 7 + ELEC 6 + TMS 2)
   - `initialize_product_tasks(serial_number, qr_doc_id, model_name)` 구현
   - model_config 기반 분기: GAIA(docking), DRAGON(tank_in_mech), 기타
   - company 기반 Task 필터링 API 구현
   - 알림 트리거 2개: TMS_TANK_COMPLETE → MECH 관리자, TANK_DOCKING_COMPLETE → ELEC 관리자
3. **FE**:
   - 회원가입 화면: company 드롭다운 추가 → role 자동 필터링
   - MM→MECH, EE→ELEC 네이밍 전수 교체 (worker.dart, home_screen.dart, register_screen.dart 등)
   - Admin 옵션 화면 신설 (heating_jacket, phase_block 토글)
4. **TEST**: 기존 테스트 MM→MECH, EE→ELEC 교체 → Task Seed 테스트 → model_config 분기 테스트

### Sprint 7: 전체 플로우 검증 + 통합 테스트 (⚠️ 신규 기능 없음)
1. **BE**: 테스트용 모델별 제품 데이터 Seed fixture 추가 (GAIA/DRAGON/GALLANT/MITHAS/SDS/SWS 6종) + GET /api/app/product 엔드포인트 테스트 보완 + 발견 버그 수정
2. **FE**: flutter build web 에러 0건 확인 + 화면 플로우 코드 점검
3. **TEST**:
   - 빈 껍데기 통합 테스트 3개 파일 전부 실제 구현 (`assert False` 0건)
   - test_product_api.py 신규 (제품 조회 + Task Seed 자동 생성 검증)
   - test_model_task_seed_integration.py 신규 (6개 모델 혼합 Task Seed 검증)
   - test_company_task_filtering.py 신규 (모든 company-worker 조합 필터링 검증)
   - test_scheduler_integration.py 신규 (미종료 알림 시간 경과 시뮬레이션)
   - 기존 단위 테스트 regression 0건

### Sprint 8: Admin API 보완 + UX 개선 + 버그 수정
1. **BE**: Admin 누락 API 5개 구현 + 비밀번호 찾기 API (forgot-password, reset-password) + 토큰 만료 변경 (access 2시간, refresh 30일) + worker_id NULL 대응
2. **FE**: admin_options_screen API 연동 + 로그인 유지 (401→자동 refresh→retry) + 마지막 화면 복원 (shared_preferences route 저장) + 비밀번호 찾기 화면 + worker_id/created_at null 방어
3. **TEST**: Admin API 테스트 12개+ + 비밀번호 찾기 테스트 8개+ + 토큰 만료 확인 + regression 0건

### Sprint 9: Pause/Resume + 근무시간 관리 (예정)
1. **BE**:
   - `POST /api/app/work/pause` + `POST /api/app/work/resume` API
   - `work_pause_log` 테이블 (task_detail_id, worker_id, paused_at, resumed_at)
   - duration 계산 시 중지 시간 자동 차감
   - 휴게/식사시간 강제 중지 스케줄러 (admin_settings에서 시간 관리)
   - 기본값: 오전휴게 10:00-10:20, 점심 11:20-12:20, 오후휴게 15:00-15:20, 저녁 17:00-18:00
2. **FE**:
   - Task 상세: 일시정지/재개 버튼 + 상태 표시 (진행중/일시정지)
   - 휴게시간 시작 시 알림 팝업 + 자동 강제 pause
   - 휴게시간 종료 시 알림 → 수동 재개
   - 저녁시간: "무시하고 계속" 옵션 (작업시간에 포함)
   - Admin 옵션: 휴게/식사시간 변경 설정 UI
3. **TEST**: pause/resume 플로우 + 휴게시간 자동 중지 + duration 차감 검증

### Sprint 10+: Railway 배포 + PWA (production 준비)
- Railway 배포 설정 (Procfile, railway.toml, eventlet, CORS, DATABASE_URL 호환, PORT 대응)
- PWA 설치 가능 상태 (manifest.json, Service Worker, 아이콘)
- API_BASE_URL 환경 분기 (constants.dart)

---

## 고도화 로드맵

### Phase A: 로그인 ID + 생체인증
| 항목 | 설명 |
|------|------|
| **login_id 컬럼 추가** | `workers` 테이블에 `login_id VARCHAR UNIQUE` 추가. 회원가입 시 이메일(인증용) + 로그인 ID(간편 접속용) 입력. 로그인은 ID + 비밀번호만으로 처리 |
| **BE 로그인 분기** | `auth_service.login()` — email 또는 login_id로 조회: `get_worker_by_email(identifier) OR get_worker_by_login_id(identifier)` |
| **FE 로그인 화면** | 이미 `EMAIL / ID` 입력 가능 (validateLoginId 적용 완료). login_id 지원 시 BE만 수정하면 연동 가능 |
| **생체인증 (지문/FaceID)** | 네이티브 빌드 전환 후 `local_auth` 패키지 적용. 최초 1회 ID/PW 로그인 → 생체 등록 → 이후 생체만으로 JWT 발급. PWA에서는 WebAuthn API로 대체 가능 |

### Phase B: 협력사 근태 관리 (MECH, ELEC, TM 전용)

> **핵심**: 생산 추적(qr_doc_id, location_qr_id)과 **완전 분리**.
> **대상**: 협력사(MECH/ELEC/TM)만 해당. 사내직원(PI/QI/SI)은 회사 그룹웨어로 근태 관리 → App 근태 불필요.
> **스키마**: `hr` 스키마 신설 — `public`은 제조 운영 전용으로 유지.

#### 5-Tier 스키마 아키텍처 (고도화 후)
```
plan       → 생산 메타데이터 (ETL 적재: product_info)
app        → 제조 운영 (workers, tasks, alerts, qr_registry, work_logs...)
checklist  → 공정별 체크리스트 (Hook-Up, BOM 검수 등)
hr         → 인사/인증/근태 (PIN 인증: 전체, 출퇴근: 협력사, GST 확장 예약)
defect     → 불량 분석 (QMS 연동)
```

| 항목 | 설명 |
|------|------|
| **PIN 간편 로그인** | 전체 사용자(GST + 협력사) 대상. 앱 재진입 시 4자리 PIN으로 빠른 로그인 |
| **근태 입력 화면** | 협력사 계정 로그인 시 홈 화면에 출근/퇴근 버튼 표시. PIN 로그인 ≠ 출근 |
| **생체 인증 (추후)** | 지문 / FaceID — 메뉴만 표시, 추후 WebAuthn API로 구현 |
| **PIN/생체 등록 시점** | **최초 로그인 후 개인 설정 화면**에서 등록 (회원가입 시 X) |
| **Admin 대시보드** | 협력사 출퇴근 현황 실시간 조회, 지각/결근 집계, 월간 리포트 |

#### DB 설계 (`hr` 스키마)
```sql
CREATE SCHEMA IF NOT EXISTS hr;

-- ① 간편 인증 설정 (전체 사용자 — GST + 협력사)
CREATE TABLE hr.worker_auth_settings (
    worker_id INTEGER PRIMARY KEY REFERENCES public.workers(id),
    pin_hash VARCHAR(255),               -- 4자리 PIN bcrypt 해시
    biometric_enabled BOOLEAN DEFAULT FALSE,
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

-- ③ GST 사내직원 근태 (추후 확장 예약 — 그룹웨어 연동 or RDB 동기화)
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

> **역할 분류**: MECH/ELEC/TM = 협력사 (작업) | PI/QI/SI = 사내직원 (인스펙션, 그룹웨어 근태)

### Phase C: BOM 검증 (기존 Phase 2)
| 항목 | 설명 |
|------|------|
| **product_bom** | 제품별 BOM(자재 목록) 관리 |
| **bom_checklist_log** | 자재 검수 체크리스트 기록 |

---

## Task Seed 데이터 (MECH 7 + ELEC 6 + TMS 2 = 15개)

> ⚠️ 기존 27개(MM19+EE8)에서 15개로 간소화 (2026-02-20 확정)

### model_config (모델별 분기 설정)
```
| model_prefix | has_docking | is_tms | tank_in_mech | 설명 |
|-------------|------------|--------|-------------|------|
| GAIA        | TRUE       | TRUE   | FALSE       | TMS(M) 탱크 별도 → MECH 도킹 |
| DRAGON      | FALSE      | FALSE  | TRUE        | 한 협력사가 탱크+MECH 일괄 |
| GALLANT     | FALSE      | FALSE  | FALSE       | 탱크/도킹 없음 |
| MITHAS      | FALSE      | FALSE  | FALSE       | 탱크/도킹 없음 |
| SDS         | FALSE      | FALSE  | FALSE       | 탱크/도킹 없음 |
| SWS         | FALSE      | FALSE  | FALSE       | 탱크/도킹 없음 |
```
- DRAGON: tank~mech 일괄 처리. 주로 TMS(M)이지만 **반드시 product_info.mech_partner 확인**
- product_info 단위 override 가능하도록 설계

### workers.company (7개 — product_info 실제 값과 동일)
```
| company  | role       | 매칭 컬럼              | 매칭 값 |
|----------|-----------|----------------------|--------|
| FNI      | MECH      | mech_partner         | FNI    |
| BAT      | MECH      | mech_partner         | BAT    |
| TMS(M)   | MECH      | module_outsourcing   | TMS    |
| TMS(E)   | ELEC      | elec_partner         | TMS    |
| P&S      | ELEC      | elec_partner         | P&S    |
| C&A      | ELEC      | elec_partner         | C&A    |
| GST      | PI,QI,SI,ADMIN | —              | —      |
```
- TMS(M): TMS task(Tank Module, 가압검사) + mech_partner 매칭 시 MECH task도 표시
- TMS(E): elec_partner = 'TMS'인 제품의 ELEC task만 표시

### MECH (기구) — 7개
```
| # | task_id          | task_name          | phase         | docking 모델 | non-docking | 비고 |
|---|------------------|--------------------|---------------|-------------|-------------|------|
| 1 | WASTE_GAS_LINE_1 | Waste Gas LINE 1   | PRE_DOCKING   | ✅          | ❌          |      |
| 2 | UTIL_LINE_1      | Util LINE 1        | PRE_DOCKING   | ✅          | ❌          |      |
| 3 | TANK_DOCKING     | Tank Docking       | DOCKING       | ✅          | ❌          |      |
| 4 | WASTE_GAS_LINE_2 | Waste Gas LINE 2   | POST_DOCKING  | ✅          | ❌          |      |
| 5 | UTIL_LINE_2      | Util LINE 2        | POST_DOCKING  | ✅          | ❌          |      |
| 6 | HEATING_JACKET   | Heating Jacket     | PRE_DOCKING   | ⚙️          | ⚙️          | admin 옵션 (default false) |
| 7 | SELF_INSPECTION  | 자주검사 ⭐         | FINAL         | ✅          | ✅          |      |
```
모델별 분기:
- **GAIA** (has_docking): 1~5, 7 활성 + phase 구분 적용
- **DRAGON** (tank_in_mech): 1~5 활성 + TANK_DOCKING만 비활성
- **기타**: 자주검사만 활성, 1~5 비활성
- **HEATING_JACKET**: `admin_settings.heating_jacket_enabled`로 제어 (default false)

### ELEC (전장) — 6개
```
| # | task_id       | task_name        | phase         |
|---|--------------|------------------|---------------|
| 1 | PANEL_WORK   | 판넬 작업         | PRE_DOCKING   |
| 2 | CABINET_PREP | 케비넷 준비 작업   | PRE_DOCKING   |
| 3 | WIRING       | 배선 포설         | PRE_DOCKING   |
| 4 | IF_1         | I.F 1            | PRE_DOCKING   |
| 5 | IF_2         | I.F 2            | POST_DOCKING  |
| 6 | INSPECTION   | 자주검사 (검수) ⭐ | FINAL         |
```
전 모델 공통: 6개 전부 활성
- GAIA: I.F 1 후 도킹 완료 대기 → I.F 2 (phase_block 옵션으로 제어, default false)
- 기타: I.F 1 → I.F 2 순차 (phase 무의미)

### TMS (모듈) — 2개 (GAIA 전용)
```
| # | task_id        | task_name    |
|---|---------------|-------------|
| 1 | TANK_MODULE    | Tank Module  |
| 2 | PRESSURE_TEST  | 가압검사 ⭐   |
```
GAIA만 생성 (is_tms = TRUE)

### admin_settings 테이블
```sql
CREATE TABLE admin_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value JSONB NOT NULL DEFAULT 'false',
    description TEXT,
    updated_by INTEGER REFERENCES workers(id),
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
-- 초기값
INSERT INTO admin_settings (setting_key, setting_value, description) VALUES
('heating_jacket_enabled', 'false', 'Heating Jacket task 활성화 여부'),
('phase_block_enabled', 'false', 'Tank Docking 완료 전 POST_DOCKING task 차단 여부');
```

### 알림 트리거 (MVP)
```
TMS 가압검사 완료 → alert_type: TMS_TANK_COMPLETE → 수신: 해당 제품 MECH 관리자 (GAIA만)
MECH Tank Docking 완료 → alert_type: TANK_DOCKING_COMPLETE → 수신: 해당 제품 ELEC 관리자 (GAIA만)
```

### Task Seed 자동 초기화 트리거
- **QR 스캔 시 자동 실행**: `GET /api/app/product/{qr_doc_id}` → 제품 조회 후 `initialize_product_tasks()` 자동 호출
- `ON CONFLICT DO NOTHING` — 이미 Task가 존재하면 무시 (멱등성 보장)
- 실패 시 non-blocking (제품 조회는 정상 반환, 로그만 기록)
- Admin 수동 초기화도 유지: `POST /api/admin/products/initialize-tasks`

### Task Seed 초기화 로직
```python
def initialize_product_tasks(serial_number: str, qr_doc_id: str, model_name: str):
    config = get_model_config(model_name)  # prefix 매칭

    # MECH Tasks (7개)
    for t in get_templates('MECH'):
        is_applicable = True
        if t.task_id == 'HEATING_JACKET':
            is_applicable = get_admin_setting('heating_jacket_enabled', False)
        elif t.is_docking_required:
            if config['has_docking']:
                is_applicable = True           # GAIA: 전부 활성
            elif config['tank_in_mech']:
                is_applicable = (t.task_id != 'TANK_DOCKING')  # DRAGON: DOCKING만 비활성
            else:
                is_applicable = False          # 기타: 비활성
        create_task(serial_number, qr_doc_id, 'MECH', t, is_applicable)

    # ELEC Tasks (6개) — 전 모델 공통
    for t in get_templates('ELEC'):
        create_task(serial_number, qr_doc_id, 'ELEC', t, True)

    # TMS Tasks (2개) — GAIA만
    if config['is_tms']:
        for t in get_templates('TMS'):
            create_task(serial_number, qr_doc_id, 'TMS', t, True)
```

### Task 필터링 로직 (작업자 화면)
```python
# TMS(M) 작업자가 보는 Task:
#   1. module_outsourcing = 'TMS' → TMS task (Tank Module, 가압검사)
#   2. mech_partner 매칭 → 해당 제품의 MECH task (DRAGON 등 일괄 처리 케이스)
#
# FNI/BAT 작업자: mech_partner = 'FNI'/'BAT' → MECH task만
# TMS(E)/P&S/C&A 작업자: elec_partner 매칭 → ELEC task만
# GST 작업자: PI/QI/SI role 기반 → 검사 task
```

### 멀티 작업자 동시 작업 로직
> 같은 Task에 여러 작업자(A, B, C)가 서로 다른 시간에 시작/종료 가능

`app_task_details` 확장 컬럼:
```sql
duration_minutes INTEGER,          -- man-hour (A+B+C 개별 duration 합산)
elapsed_minutes INTEGER,           -- 실경과시간 (최초 시작 ~ 마지막 종료)
worker_count INTEGER DEFAULT 1,    -- 투입 인원
force_closed BOOLEAN DEFAULT FALSE,-- 강제 종료 여부
closed_by INTEGER REFERENCES workers(id),  -- 강제 종료한 관리자
close_reason TEXT                  -- 강제 종료 사유
```

계산 로직:
```
app_task_details.started_at     = MIN(work_start_log.started_at)       ← 최초 시작
app_task_details.completed_at   = MAX(work_completion_log.completed_at) ← 마지막 종료
app_task_details.duration_minutes = SUM(각 worker 개별 duration)        ← man-hour 합산
app_task_details.elapsed_minutes  = completed_at - started_at           ← 실경과시간
app_task_details.worker_count     = COUNT(DISTINCT worker_id)           ← 투입 인원
```

### 작업 미종료 알림 체계 (3단계)
> scheduler_service.py (APScheduler) + alert_log + WebSocket 활용

```
[1단계] 작업자 리마인더 — 매 1시간
  - 트리거: 작업 시작 후 1시간 단위 경과, completed_at IS NULL
  - 수신: 해당 작업자
  - alert_type: TASK_REMINDER
  - 메시지: "{task_name} 작업이 {N}시간째 진행 중입니다. 완료 시 종료 버튼을 눌러주세요."

[2단계] 퇴근 시간 알림 — 17:00, 20:00 (KST)
  - 트리거: 17:00 정상퇴근, 20:00 잔업종료 시점에 미종료 작업 존재
  - 수신: 해당 작업자
  - alert_type: SHIFT_END_REMINDER
  - 메시지: "퇴근 전 미완료 작업 {N}건이 있습니다."

[3단계] 관리자 에스컬레이션 — 익일 09:00
  - 트리거: 전일 미종료 작업 (started_at < 오늘 00:00, completed_at IS NULL)
  - 수신: 해당 협력사 관리자 (is_manager=true + 같은 company)
  - alert_type: TASK_ESCALATION
  - 메시지: "작업자 {name}의 {task_name} 작업이 전일 미종료 상태입니다."
  - 관리자 액션: 강제 종료 (force_closed=true, closed_by, close_reason 입력)
```

관리자 강제 종료 API: `PUT /api/admin/tasks/{task_id}/force-close`
- body: `{ "completed_at": "2026-02-20T17:00:00+09:00", "close_reason": "작업자 미처리" }`
- force_closed=true, closed_by=관리자 worker_id 자동 설정

### Admin 옵션 화면 기능 목록 + 필수 API
```
1. admin_settings 관리 (heating_jacket, phase_block 등 토글)
2. 협력사 관리자 지정/해제 (workers.is_manager 토글, company 기준 필터)
3. 미종료 작업 목록 → 강제 종료 버튼
4. model_config 조회/수정 (추후)
```

**⚠️ Admin 옵션 화면 필수 API (FE가 호출 — BE 구현 필수)**:
| HTTP | 엔드포인트 | 설명 | 권한 |
|------|-----------|------|------|
| GET | `/api/admin/managers?company=` | 작업자 목록 (approved, company 필터) | admin_required |
| PUT | `/api/admin/workers/{id}/manager` | is_manager 토글 `{"is_manager": bool}` | admin_required |
| GET | `/api/admin/settings` | admin_settings 전체 조회 | admin_required |
| PUT | `/api/admin/settings` | admin_settings 업데이트 `{"setting_key", "setting_value"}` | admin_required |
| GET | `/api/admin/tasks/pending` | 미종료 작업 목록 (started_at NOT NULL, completed_at IS NULL) | admin_required |
| PUT | `/api/admin/tasks/{id}/force-close` | 강제 종료 (이미 구현됨) | manager_or_admin_required |

### 멀티 작업자 + 미종료 처리 테스트 케이스 (TEST 반드시 전수 구현)

**멀티 작업자 duration 계산:**
```
TC-MW-01: 1명 단독 작업 → duration = 개인 작업시간, worker_count = 1
TC-MW-02: 2명 동시 시작, 다른 시간에 종료 → started_at = 동일, completed_at = 마지막 종료, duration = 합산
TC-MW-03: 3명 모두 다른 시작/종료 → started_at = MIN, completed_at = MAX, duration = SUM, elapsed = MAX-MIN
TC-MW-04: 작업자 A 종료 + B 아직 진행 중 → Task.completed_at IS NULL (미완료 상태 유지)
TC-MW-05: 마지막 작업자 종료 → Task 자동 완료, duration/elapsed/worker_count 모두 정확한지 검증
TC-MW-06: duration_minutes(man-hour) ≠ elapsed_minutes(실경과) 값이 서로 다른지 확인 (3명 동시 작업 시)
TC-MW-07: worker_count = 실제 참여 작업자 수 (중복 제거 DISTINCT)
```

**미종료 알림 스케줄러:**
```
TC-UF-01: 작업 시작 1시간 경과 → TASK_REMINDER 알림 생성 확인
TC-UF-02: 작업 시작 3시간 경과 → TASK_REMINDER 3회 누적 확인
TC-UF-03: 작업 완료된 건 → 알림 미생성 확인 (false positive 방지)
TC-UF-04: 17:00 KST 도달 + 미종료 작업 → SHIFT_END_REMINDER 생성
TC-UF-05: 17:00 KST 도달 + 미종료 작업 없음 → 알림 미생성
TC-UF-06: 20:00 KST 도달 + 미종료 작업 → SHIFT_END_REMINDER 생성
TC-UF-07: 익일 09:00 + 전일 미종료 → TASK_ESCALATION 관리자 알림 (is_manager=true + 같은 company)
TC-UF-08: 다른 company 관리자에게는 알림 미전송 확인
```

**관리자 강제 종료:**
```
TC-FC-01: 관리자(is_manager=true) → force-close 성공, force_closed=true 확인
TC-FC-02: 일반 작업자 → force-close 시도 → 403 거부
TC-FC-03: 강제 종료 시 completed_at = 관리자 지정 시간, closed_by = 관리자 ID 확인
TC-FC-04: 강제 종료 후 duration_minutes, elapsed_minutes 정확 계산 확인
TC-FC-05: close_reason 필수 입력 검증 (빈값 → 400)
TC-FC-06: 이미 완료된 Task에 force-close → 400 거부
TC-FC-07: 강제 종료된 Task는 리포트에서 force_closed=true로 필터 가능 확인
```

---

## Sprint 1 상세 작업 지시

### BE 워커 — Sprint 1 작업 순서
```
1. backend/migrations/001_create_workers.sql 검토 및 보완
2. backend/migrations/002_create_product_info.sql 검토 및 보완
3. backend/app/models/worker.py — CRUD 함수 구현 (psycopg2)
4. backend/app/services/auth_service.py — register, login, verify_email 구현
5. backend/app/middleware/jwt_auth.py — 인증/권한 데코레이터 구현
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

---

## Sprint/ID 네이밍 규칙 (작업 단위 식별자)

> 번호 체계 정합성 확보. 모든 작업 단위는 아래 중 하나의 접두사를 사용.
> **중복 번호 금지** — 새 작업 생성 전 BACKLOG.md/PROGRESS.md에서 번호 충돌 확인 필수.

### 접두사 분류

| 접두사 | 용도 | 번호 시퀀스 | 예시 |
|--------|------|-----------|------|
| **Sprint-N** | 신규 기능 (여러 파일·BE/FE 걸침, 설계서 선행) | 순차 증가, 공백 허용 안 함 | Sprint 55, Sprint 56 |
| **FIX-N** | 단일 이슈·소규모 수정 (설계서 없이 착수 가능) | Sprint와 독립 시퀀스 | FIX-24, FIX-25 |
| **HOTFIX-N** | 프로덕션 장애 긴급 대응 (1시간 이내 배포 목표) | 독립 시퀀스 | HOTFIX-04, HOTFIX-05 |
| **BUG-N** | 재현 가능한 결함 (백로그 등록 후 스케줄) | 독립 시퀀스 | BUG-44, BUG-45 |
| **INFRA-N** | 인프라/배포/CI (기능 아님) | 독립 시퀀스 | INFRA-1 |
| **TEST-<slug>** | 테스트 전용 작업 | 슬러그 기반 | TEST-AL20, TEST-CLEAN-CORE-01 |
| **TECH-<slug>** | 리팩토링/기술 부채 | 슬러그 기반 | TECH-REFACTOR-FMT-01 |
| **DOC-<slug>** | 문서 정리/검증 | 슬러그 기반 | DOC-SYNC-01 |
| **SEC-N** | 보안 패치 (Security Review 연계) | 독립 시퀀스 | SEC-01 |
| **REF-<area>-N** | 특정 파일/영역 리팩토링 | 영역 슬러그 + 순차 | REF-BE-13 (auth_service 분할) |

### 하위 번호 규칙 (A/B/C/fix)

- **허용 사례**: 같은 Sprint 범위를 다단계로 쪼갠 경우
  - `Sprint 57-C`, `Sprint 57-D`, `Sprint 57-E` = Sprint 57(ELEC 체크리스트)의 후속 단계
  - `Sprint 29-fix` = Sprint 29의 회귀 수정
  - `Sprint 61-BE-B` = Sprint 61 BE 작업의 연장
- **금지 사례**: 서로 무관한 작업에 같은 번호 재사용 (과거 Sprint 53/54 중복 사례 재발 방지)

### 번호 할당 절차

1. 착수 전 BACKLOG.md + PROGRESS.md에서 **같은 접두사의 max 번호** 확인
2. `max + 1` 할당 (공백 금지)
3. BACKLOG.md 표에 선등록 후 착수
4. 완료 시 PROGRESS.md로 이동, 버전 이력 반영

### 레거시 공백 (2026-04-21 기준 기록)

- Sprint 2~12, 17, 18, 20, 28, 42~50: 초기 설계 단계에서 건너뛴 번호로 **재사용하지 않음**
- 과거 중복(Sprint 53·54가 2~3건씩 존재)은 **현 상태 동결**, 신규 번호 할당 시만 규칙 적용

---

## 버전 관리 기준 (Semantic Versioning, 2026-04-21 개정)

### 버전 형식: `MAJOR.MINOR.PATCH`

| 구분 | 올리는 시점 | AXIS 실정 예시 |
|------|-----------|---------------|
| **MAJOR** (X.0.0) | 아키텍처 전환 (사내서버 마이그레이션·SAP 연동·DB 전면 재설계·인증 체계 교체 등) | v2→v3: Railway→사내서버 전환, SAP RFC 연동 |
| **MINOR** (0.X.0) | Sprint 단위 기능 추가 (신규 API·화면·기능, 하위 호환 유지) | v2.9→v2.10: Sprint 62 체크리스트 MECH 확장 |
| **PATCH** (0.0.X) | HOTFIX·용어 정합·데드 코드 정리·버그 수정 (기능 변경 없음) | v2.9.10→v2.9.11: 강제종료 툴팁 문구 정정 |

**릴리스 시 동시 업데이트 필수 (3곳)**:
1. `backend/version.py` + `frontend/lib/utils/app_version.dart` (VERSION 일치)
2. `CHANGELOG.md` (변경 요약)
3. `git tag v{X.Y.Z}` (배포 시점 고정)

### 버전 업데이트 파일 목록

스프린트 완료 후 반드시 아래 2개 파일을 **동시에** 업데이트:

1. `backend/version.py` — BE 버전 (VERSION, BUILD_DATE)
2. `frontend/lib/utils/app_version.dart` — FE 버전 (version, buildDate)

> health endpoint (`/api/health`)에서 VERSION 자동 반영됨, 앱 스플래시에서 `AppVersion.display` 자동 반영됨

### 버전 업데이트 절차

```
1. 스프린트 전체 완료 + 테스트 통과 확인
2. backend/version.py → VERSION, BUILD_DATE 업데이트
3. frontend/lib/utils/app_version.dart → version, buildDate 업데이트
4. 두 파일의 VERSION 값이 반드시 동일해야 함
5. CLAUDE.md 버전 이력에 기록
6. PROGRESS.md에 스프린트 완료 내역 추가 (BE/FE/TEST 완료 항목, 테스트 결과, 생성/수정 파일)
7. BACKLOG.md 업데이트 (완료 항목 체크, 다음 스프린트 계획 반영)
```

### FE 빌드 + 배포 절차 (Netlify)

```
1. cd frontend
2. flutter build web --release          # build/web 생성
3. npx netlify-cli deploy --prod --dir=build/web --site=ab8041c3-dc51-40c6-96e4-9966222aeda3
   # 사이트: https://gaxis-ops.netlify.app
4. git add → commit → push (빌드 결과물은 커밋하지 않음, 소스 변경만 커밋)
```

> **참고**: `state.json` 없이 `--site=<site_id>` 플래그로 직접 지정.
> Netlify CLI가 없으면 `npx netlify-cli`로 자동 설치 후 실행됨.

### 사용자 공지 (notices) 작성 규칙

공지 INSERT 시 **플레인 텍스트 + 이모지** 형식 사용. 마크다운(`##`, `**`, ``` 등) 절대 미사용.
FE에 마크다운 렌더링 라이브러리가 없으므로 `##`이 문자 그대로 표시됨.

```
제목 (고정 형식): 📱 OPS v{버전} 업데이트 안내

본문 형식:
📱 OPS v{버전} 업데이트 안내

🔐 카테고리명
 - 항목 설명
 - 항목 설명

📊 카테고리명
 - 항목 설명

이모지 예시: 🔐(보안/로그인) 🔧(수정) 📊(QR/스캔) 📈(분석) ⚙️(설정) 👥(사용자)
```

공지 INSERT SQL:
```sql
INSERT INTO notices (title, content, version, is_pinned, created_by)
VALUES ('📱 OPS v2.2.1 업데이트 안내', '본문...', '2.2.1', TRUE, {admin_id})
-- ⚠️ 신규 공지는 is_pinned=TRUE, 기존 pinned는 FALSE로 해제
```

### ⚠️ OPS / VIEW 공지 구분 규칙 (2026-04-22 추가 — 실수 사례 반영)

> `notices` 테이블은 OPS / VIEW 공지를 **단일 테이블에 섞어 저장**. 해제(UPDATE)할 때 반드시 version prefix 로 시스템 구분 필요.

**version prefix 관례** (FE 구분 기준):
- `2.x.x` → **OPS** 공지 (`📱 OPS v{X.Y.Z} 업데이트 안내`)
- `1.x.x` → **VIEW** 공지 (`🖥️ VIEW v{X.Y.Z} 업데이트 안내`)

**공지 bump 시 권장 절차**:
```sql
-- ❌ WRONG — OPS/VIEW 모두 해제됨 (타 시스템 공지 실수로 숨김 사고 발생 이력 있음)
UPDATE notices SET is_pinned = FALSE WHERE is_pinned = TRUE;

-- ✅ OPS 공지 bump 시 — OPS 공지 (v2.x.x) 만 해제
UPDATE notices SET is_pinned = FALSE
WHERE is_pinned = TRUE AND version LIKE '2.%';

-- ✅ VIEW 공지 bump 시 — VIEW 공지 (v1.x.x) 만 해제
UPDATE notices SET is_pinned = FALSE
WHERE is_pinned = TRUE AND version LIKE '1.%';

-- 이후 신규 공지 INSERT (is_pinned=TRUE) — 다른 시스템 공지는 그대로 유지
```

**사고 이력**: 2026-04-22 OPS v2.9.11 공지 INSERT 시 `WHERE is_pinned = TRUE` 만으로 해제 → VIEW v1.32.3 공지도 함께 해제됨. 즉시 `UPDATE notices SET is_pinned = TRUE WHERE id = 100` 으로 복원. 본 규칙은 동일 사고 재발 방지용.

### 버전 이력

| 버전 | 날짜 | 스프린트 | 주요 변경 |
|------|------|---------|----------|
| v1.0.0 | 2026-02-16 | Sprint 1-10 | 초기 릴리스 (인증, 출퇴근, 작업관리, 관리자) |
| v1.1.0 | 2026-02-25 | Sprint 13 | QR 스캔 + 생산실적 입력 |
| v1.2.0 | 2026-02-28 | Sprint 14-15 | 일시정지/재개, 알림, 스케줄러 |
| v1.3.0 | 2026-03-04 | Sprint 16-17 | 버전 시스템 도입, 파트너 S/N 진행률 |
| v1.4.0 | 2026-03-06 | Sprint 19-A/B/D | 보안 강화 (Refresh Token Rotation, Device ID, DB 토큰 관리, Geolocation) |
| v1.5.0 | 2026-03-06 | Sprint 19-E/20-A/B | VIEW용 출퇴근 API, 가입 Admin 알림, 공지사항 탭 |
| v1.6.0 | 2026-03-10 | Sprint 21/22-A/B | QR 목록 API, 이메일 인증 개선, GPS 정확도 + DMS 변환 |
| v1.6.1 | 2026-03-10 | Sprint 22-A 보완 | 인증 3분 만료, 재전송 API 연동, 승인목록 인증필터, PM role |
| v1.6.2 | 2026-03-10 | Sprint 22-C | Manager 권한 위임 (같은 회사 is_manager 부여, Admin 보호) |
| v1.6.3 | 2026-03-11 | Sprint 22-D | 공지수정 UI, Admin 간편로그인, ETL 변경이력 API |
| v1.7.0 | 2026-03-11 | Sprint 23 | Manager 권한 위임 화면, 홈 메뉴 재구성, managers API 권한 완화 |
| v1.7.1 | 2026-03-11 | Sprint 24 | QR 목록 actual_ship_date 추가, Manager 자사 필터 (QR/출퇴근) |
| v1.7.2 | 2026-03-12 | Sprint 25 | BUG-22 Logout Storm 수정 (401 무한 루프 방지, jwt_optional) |
| v1.7.3 | 2026-03-12 | Sprint 26 | PWA 버전 업데이트 토스트 + 업데이트 내용 팝업, conftest 운영 데이터 보호 |
| v1.7.4 | 2026-03-13 | Sprint 27 | AXIS-VIEW 권한 데코레이터 재정비 (get_current_worker 캐싱, gst_or_admin_required, view_access_required) |
| v1.7.5 | 2026-03-15 | Sprint 27-fix | Task Seed silent fail 수정, SINGLE_ACTION UI 반영, BUG-23 QR viewfinder 코너 수정 |
| v1.7.6 | 2026-03-15 | Sprint 29 | 공장 API (monthly-detail, weekly-kpi) — BE only, factory.py 신규 |
| v1.7.7 | 2026-03-16 | Sprint 29 보완 | PM role 추가, 이름 로그인, ship_plan_date, per_page 500 |
| v1.7.8 | 2026-03-16 | Sprint 29-fix | BUG-24 재발 방지 — ensure_schema 앱 시작 시 DB 스키마 자동 검증 |
| v1.8.0 | 2026-03-17 | Sprint 30 | DB Connection Pool 도입 — 33파일 175건 conn.close→put_conn 변환 |
| v1.9.0 | 2026-03-18 | Sprint 31A | 다모델 지원 — DUAL L/R, DRAGON MECH 탱크, PI 분기, iVAS, workers RESTRICT |
| v1.9.0 | 2026-03-18 | Sprint 31B | QR 기반 태스크 필터링 — DUAL L/R 분리 표시, task_progress, FIX-21~23 |
| v1.9.0 | 2026-03-19 | Sprint 32 | 사용자 행위 트래킹 — app_access_log, analytics API 4개, 30일 정리 |
| v2.0.0 | 2026-03-20 | Sprint 31C | PI 검사 협력사 위임 — pi_capable_mech_partners, GST PI override_lines |
| v2.0.0 | 2026-03-20 | Sprint 33 | 생산실적 API — O/N 단위 실적확인/취소/월마감, production_confirm 테이블 |
| v2.0.0 | 2026-03-21 | Sprint 34 | admin_settings SETTING_KEYS 레지스트리 28개 + workers 필터 |
| v2.0.0 | 2026-03-21 | Sprint 34-A | Admin 옵션 PI 위임 설정 UI — Chip 추가/삭제 |
| v2.1.0 | 2026-03-23 | Sprint 35-37 | 생산실적 API 고도화 — 근태 추이, TM TANK_MODULE only, 혼재 O/N partner별 분리 |
| v2.1.0 | 2026-03-26 | Sprint 39 | 테스트 DB 분리 — conftest.py 리팩토링, TEST_DATABASE_URL 환경변수, .env.test |
| v2.1.0 | 2026-03-27 | Sprint 39-fix | Regression 수정 118→0 failed — BE 2파일 + TEST 18파일 |
| v2.2.0 | 2026-03-27 | Sprint 38 | product/progress API — last_worker, last_activity_at 필드 추가 (N+1 방지) |
| v2.2.0 | 2026-03-27 | Sprint 38-B | product/progress API — last_task_name, last_task_category 필드 추가 |
| v2.2.0 | 2026-03-27 | Sprint 40-A | QR 스캔 UX — 프레임 축소, DOC_/LOC_ 자동접두어, 오늘 태깅 드롭다운, BUG-29 프레임 과대 수정 |
| v2.2.0 | 2026-03-27 | #46 | 상세뷰 workers 매핑 — task_id fallback + serial_number 기준 조회 |
| v2.2.0 | 2026-03-27 | Sprint 40-C | 비활성 사용자 관리 — soft delete, is_active, last_login_at, admin/manager API |
| v2.2.0 | 2026-03-27 | Sprint 40-C FE | Admin 옵션 레이아웃 재배치 + 비활성 사용자 관리 UI + 비활성화 알림 (앱+이메일) |
| v2.2.0 | 2026-03-28 | BUG-30/31 | 로그인 에러 시스템코드 미표시 + PIN→이메일 로그인 전환 수정 + Manager 비활성화 요청 UI |
| v2.2.1 | 2026-03-30 | 버그수정 | 분석 대시보드 엔드포인트 한글 라벨 40개 누락 전수 등록 (30→90개) |
| v2.3.0 | 2026-03-30 | Sprint 41 | 작업 릴레이 + Manager 재활성화 — finalize 파라미터, 릴레이 재시작, reactivate-task API |
| v2.3.0 | 2026-03-30 | Sprint 41-A | 작업 완료 토스트 미표시 수정 + 목록 릴레이 다이얼로그 + 릴레이 재시작 UI — 실기기 테스트 완료 |
| v2.3.0 | 2026-03-30 | Sprint 41-B | 릴레이 미완료 task 자동 마감 (FINAL task 트리거) + Manager 알림 (4시간 경과) |
| v2.3.0 | 2026-03-30 | #48 | 재활성화 권한 체크 비교 방향 버그 — company_base 추출 + TMS(M)/TMS(E) 허용 |
| v2.3.0 | 2026-03-31 | #52 | ETL 변경이력 _FIELD_LABELS finishing_plan_end 누락 — 마무리계획일 조회 허용 |
| v2.3.0 | 2026-03-31 | #51 | progress API에 sales_order 필드 추가 — O/N 그룹핑용 (VIEW Sprint 24 선행) |
| v2.4.0 | 2026-04-01 | Sprint 52 | TM 체크리스트 Phase 1 — checklist_service, TM API 3개, Admin CRUD 4개, 알림 트리거, FE 화면 |
| v2.4.0 | 2026-04-02 | Sprint 53 | 알림 소리 + 진동 — Web Audio API 비프음 5종, 프로필 설정 드롭다운 + 미리듣기 |
| v2.5.0 | 2026-04-02 | Sprint 52-A | TM 체크리스트 보완 — COMMON seed 15항목, scope='all' 수정, item_type 컬럼 |
| v2.5.0 | 2026-04-02 | Sprint 54 | 공정 흐름 알림 트리거 — partner 분기 + admin_settings on/off 5개 + FE 설정 UI |
| v2.5.1 | 2026-04-02 | Sprint 52-BF | TM 체크리스트 BUG-FIX #1~#6 — FE 키 매핑, checklistReady, 체크리스트 버튼, null 방어, 2상태 토글, 알림 [S/N\|O/N] 포맷 |
| v2.6.0 | 2026-04-03 | Sprint 31C-A | PI 위임 모델별 옵션 — pi_delegate_models allowlist, SWS GST PI 직접 |
| v2.6.0 | 2026-04-03 | Sprint 53 | monthly-summary API weeks + totals — 금요일 기준 주차-월 매핑 |
| v2.6.0 | 2026-04-03 | Sprint 54 | 체크리스트 성적서 API — O/N 검색 + S/N 성적서 (배치 쿼리) |
| v2.6.0 | 2026-04-03 | BUG-FIX | master_id 응답 누락 수정, #53 mech_start→mech_end 필터, description 표시 |
| v2.6.0 | 2026-04-07 | BUG-6 | 다중작업자 동료 resume 403 — task coworker 허용 조건 추가 |
| v2.7.0 | 2026-04-07 | Sprint 55 | Worker별 Pause/Resume + Auto-Finalize + FINAL task 릴레이 불가 |
| v2.7.0 | 2026-04-08 | INFRA-1 | Migration 자동 실행 시스템 — migration_runner.py + migration_history 테이블, 041~045 운영 적용 |
| v2.7.0 | 2026-04-08 | TEST-AL20 | Alert 20종 전체 검증 테스트 38TC — is_relay 버그 수정, TC-PR-20 assert 수정 |
| v2.7.1 | 2026-04-09 | Sprint 55-B | Task 목록 API my_pause_status 누락 — 화면 재진입 시 pause 상태 소실 수정 |
| v2.7.1 | 2026-04-09 | Sprint 56 | QR 목록 API elec_start 필드 + 필터 + 정렬 추가 |
| v2.7.1 | 2026-04-09 | #55 | 비활성 사용자 목록 노출 — workers/managers/출퇴근 API is_active 필터, migration 040 운영 실행 |
| v2.8.0 | 2026-04-09 | Sprint 57 | ELEC 공정 시퀀스 변경 + 체크리스트 — INSPECTION freeroll, IF_2 FINAL, Dual-Trigger 닫기, 31항목 seed, migration 046/046a |
| v2.8.1 | 2026-04-10 | Sprint 57-C | ELEC seed 교체(실제 양식) + BUG-36 DUAL qr_doc_id + SELECT/INPUT 스키마, migration 047 |
| v2.9.0 | 2026-04-10 | Sprint 57-D/E/FE + 30-BE | ELEC 체크리스트 FE 연동 + TM DUAL L/R + QI 체크리스트 진입 + 성적서 API Phase/DUAL 분기 |
| v2.9.1 | 2026-04-13 | Sprint 58-BE | check_elec_completion Phase 1+2 합산 + confirmable 체크리스트 + ELEC status 엔드포인트 |
| v2.9.2 | 2026-04-14 | Sprint 59-BE | TM qr_doc_id 정규화 — SINGLE DOC_{S/N} + DUAL L/R, 성적서 SINGLE 분기 통합, 레거시 데이터 수정 |
| v2.9.3 | 2026-04-16 | Sprint 60-BE | ELEC 마스터 정규화 — phase1_applicable + qi_check_required + remarks, 문자열 추론 제거, migration 048 |
| v2.9.4 | 2026-04-17 | Sprint 61-BE | 알람 O/N 통일 + 에스컬레이션 3종 + pending API 확장 + SETTING_KEYS 5개 |
| v2.9.4 | 2026-04-17 | BUG-43 | 분석 대시보드 한글 라벨 누락 24건 전수 등록 (111→135키, 108 라우트 커버) |
| v2.9.4 | 2026-04-17 | BUG-44 | 미종료 작업 0건 — INNER JOIN → LATERAL JOIN (work_start_log FK). Claude×Codex 교차 검증 합의 |
| v2.9.5 | 2026-04-17 | Sprint 61-BE-B | BUG-44 보완 + API 응답 확장 — pending/task 응답에 company 필드(#60) + force_closed 필드(#61) 추가 |
| v2.9.5 | 2026-04-17 | HOTFIX | force_close/force_complete TypeError — naive vs aware datetime 정규화 (completed_at + started_at 양쪽) |
| v2.9.6 | 2026-04-17 | BUG-45 | force_close completed_at 범위 검증 — 미래 차단(60s skew 허용) + started_at 이전 차단. VIEW useForceClose 필드명 정정(FE-17). pytest 17/17(BUG-45 8 TC), 회귀 46/46 GREEN |
| v2.9.6 | 2026-04-17 | HOTFIX-02 | 체크리스트 마스터 API `checker_role` 키 노출 누락 — Sprint 60-BE 후속. `list_checklist_master()` SELECT + 응답 dict 2줄 추가. VIEW JIG WORKER/QI 뱃지 분기 정상화 (OPS #59-B DONE / VIEW FE-18 ✅) |
| v2.9.6 | 2026-04-17 | HOTFIX-03 | 비활성 task(`is_applicable=FALSE`) 조회 필터 누락 — `get_tasks_by_serial_number()` + `get_tasks_by_qr_doc_id()` 4 SELECT에 `AND is_applicable = TRUE` 추가. 방안 A 채택 (모델 레벨 필터). VIEW S/N 상세뷰 Heating Jacket 미시작 카운트 오염 정상화 (OPS #60 DONE) |
| v2.9.7 | 2026-04-17 | HOTFIX-05 | Admin 옵션 미종료 작업 카드 시간 UTC 그대로 표시 — `admin_options_screen.dart` L2474 `DateTime.tryParse(...)?.toLocal()` 누락 보정. BE 응답 `+09:00` offset → Dart DateTime 내부 UTC 저장 → 게터가 UTC값 반환했던 문제. manager_pending_tasks_screen과 일관성 확보 |
| v2.9.8 | 2026-04-17 | HOTFIX-04 | 강제종료 표시 누락 종합 수정 (Case 1 Orphan wsl + Case 2 미시작 강제종료, 방안 B + 확장 A 통합). `work.py` `get_tasks_by_serial()` SQL `COALESCE(wcl.completed_at, td.completed_at)` + orphan 판정 + `is_orphan`/`task_closed_at` 메타필드, `_task_to_dict()` 응답에 `close_reason`/`closed_by_name` 노출 (worker_map 캐시 재활용). pytest 6/6 신규 + 회귀 24/24 GREEN. VIEW FE-19(placeholder 렌더)는 VIEW 리포 별도 |
| v2.9.9 | 2026-04-18 | FIX-24 | OPS 미종료 작업 카드에 O/N(sales_order) 뱃지 추가 — `admin_options_screen.dart` + `manager_pending_tasks_screen.dart` 2파일 Row 2에 `Icons.receipt_long` + sales_order Text conditional spread 추가. BE 응답에 `sales_order` 이미 포함, FE only 약 6줄×2. `salesOrder.isNotEmpty` 조건부로 기존 화면 회귀 0 |
| v2.9.10 | 2026-04-20 | FIX-25 | progress API(`/api/app/product/progress`) 응답에 `mech_partner`/`elec_partner`/`module_outsourcing`/`line` 4필드 노출 — `progress_service.py` 단일 파일 수정 (CTE·메인 SELECT에 `pi.line` 추가 + `_aggregate_products` dict `'line'` 추가 + L296~299 pop() 3줄 제거, touch 6줄/net 0). tasks API·production.py·models 전부 무변경(v3 List→Dict breaking 회피). VIEW FE FE-20(상세뷰 협력사명)/FE-21(O/N line) 데이터 공급. TC-PROGRESS-PI-01~06 6건 + 기존 regression 42/42 GREEN, Codex 합의 없이 첫 시도 통과 |
| v2.10.0 | 2026-04-23 | Sprint 62-BE | 체크리스트 MECH 확장 — JIG WORKER/QI 분리, master 31항목 seed, migration 050 |
| v2.10.1 | 2026-04-23 | PATCH | weekly-kpi WHERE finishing_plan_end 교정 |
| v2.10.2 | 2026-04-23 | FIX-CHECKLIST-DONE-DEDUPE-KEY | 체크리스트 done 중복키 정정 (Codex Q4-4 M 해소) |
| v2.10.3 | 2026-04-24 | FIX-ORPHAN-ON-FINAL-DELIVERY | HOTFIX-DELIVERY 숨은 4번째 경로 처리 |
| v2.10.4 | 2026-04-25 | HOTFIX | health timeout 5s→20s — Railway TTFB intermittent 우회 (FE app_init.dart) |
| v2.10.5 | 2026-04-27 | FIX-PIN-FLAG-MIGRATION-SHAREDPREFS | PIN 등록 플래그 storage 안정화 — `pin_registered` SecureStorage→SharedPreferences 양방향 sync (FE auth_service.dart). 4 라운드 advisory review (Codex 1차 M=8/8 + 추가 리스크 2/2 전수 반영) 후 적용 |
| v2.10.6 | 2026-04-27 | FEAT-PIN-STATUS-BACKEND-FALLBACK + OBSERV-DB-POOL-WARMUP | (1) FE — `getBackendPinStatus()` + main.dart 라우팅 분기 (`/auth/pin-status` 호출 → IndexedDB 잃어도 backend 자동 복구) / (2) BE — `_pool_warmup_job` 5분 IntervalTrigger + `warmup_pool()` 신규 (Railway proxy idle disconnect 방지, MIN=5 강제 유지) |
| v2.10.7 | 2026-04-27 | HOTFIX-06 | warmup_pool() 시계 리셋 누락 — `_conn_created_at[id(conn)] = time.time()` 1줄 추가. v2.10.6 OBSERV-WARMUP 결함 fix. 결과: conn 7~11 진동 안정 |
| v2.10.8 | 2026-04-27 | OBSERV-RAILWAY-LOG-LEVEL + OBSERV-ALERT-SILENT-FAIL + POST-REVIEW-MIGRATION-049 + OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION | 알람 사후 검증 마무리 4 Sprint 통합 — (1) Procfile `--access-logfile=- --log-level=info` + `logging.basicConfig(stream=sys.stdout, force=True)` (2) `sentry-sdk[flask]>=2.0` + `_init_sentry()` 신규 (~50 LOC, FlaskIntegration + LoggingIntegration) (3) POST_MORTEM_MIGRATION_049.md 산출 (가설 ④ Docker artifact 가장 유력) (4) `assert_migrations_in_sync()` 신규 — disk vs DB sync 검증 + Sentry capture_message. **Sentry DSN 활성화 4-27 완료** (Twin파파 측 sentry.io 가입 + Railway env 등록) |
| v2.10.9 | 2026-04-27 | HOTFIX-07 | RealDictCursor row[0] KeyError 긴급 복구 — `_get_executed()` row[0]→row['filename'] + `assert_migrations_in_sync()` outer try/except 안전망. v2.10.8 assertion 도입이 5일 누적 silent 버그 즉시 노출 → assertion 가치 1차 입증 |
| v2.10.10 | 2026-04-27 | HOTFIX-08 | db_pool transaction 정리 누락 — `_is_conn_usable()` + `warmup_pool()` SELECT 1 후 `conn.rollback()` 2곳. psycopg2 INTRANS → migration_runner autocommit=True 거부 문제 해소. 부수 효과: 046a_elec_checklist_seed.sql 자동 적용 (4-22 049 와 동일 Docker artifact 두 번째 사례, ON CONFLICT 로 사용자 영향 0). assertion 자동 감지 layer 가치 2차 입증 |
| v2.10.11 | 2026-04-28 | FIX-PROCESS-VALIDATOR-TMS-MAPPING | 4-22 HOTFIX 표준 패턴이 duration_validator 3곳 (L74/L100/L179) + task_service L403 미적용 → TMS 매니저 silent failure (Sentry 도입 8h 자동 감지, 31 events). 옵션 D-2: `process_validator.resolve_managers_for_category()` public 함수 신설 + `_CATEGORY_PARTNER_FIELD` 이전 + scheduler/duration/task_service import 교체 (5 파일 atomic). pytest 신규 TC 7개 + 옵션 D 격리 fixture `seed_test_managers_for_partner` (Codex M1 합의). 회귀 0건 (test_duration_validator 1 fail = BACKLOG L362 BUG-DURATION-VALIDATOR-API-FIELD 4-22 별건, Codex 라운드 2 A 합의). Sentry 가치 입증 #3 |
| v2.10.12 | 2026-04-28 | FIX-26-DURATION-WARNINGS-FORWARD | `/api/app/work/complete` 응답에 `duration_warnings` 키 항상 존재 보장 — task_service.py L497 unconditional + work.py L266 default get (옵션 C). 4-22 등록 BACKLOG L362 본격 fix. test_normal_duration_no_warnings assertion 갱신 + 신규 TC `test_normal_completion_returns_empty_duration_warnings` + test_reverse_completion `@pytest.mark.skip` (시작/종료 timestamp 서버 datetime.now() 자동 기록 — 운영 발생 불가, prod 0건 실측, 인프라 사고 시나리오만). BACKLOG L362 COMPLETED |
