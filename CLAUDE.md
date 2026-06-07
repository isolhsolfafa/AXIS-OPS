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
  - 현재 설치: `codex-cli 0.132.0` (2026-05-20 기준, **npm `@openai/codex` 채널**)
  - 실제 경로: `/opt/homebrew/bin/codex` → symlink → `lib/node_modules/@openai/codex/bin/codex.js` (npm 글로벌)
  - ⚠️ Homebrew formula 와는 **별도 채널** — brew formula 는 0.130.0 ("Not installed") 이고 우리는 npm 채널로 관리됨. `brew outdated codex` / `brew upgrade codex` 명령은 우리 환경에서 동작 안 함 (2026-05-20 VIEW 측 catch 후 정정)
- **업데이트 트리거**:
  - 주 1회 이상 `npm view @openai/codex version` 으로 npm registry 최신 확인 (권장: 매주 월요일 Sprint 시작 시)
  - Codex 마이너/메이저 업데이트 발견 시 즉시 `npm install -g @openai/codex@latest` 후 CLAUDE.md 버전 갱신
  - GPT 신 모델(GPT-5.x 등) 출시 감지 시 Codex CLI가 자동 수신하는지 `codex doctor` 또는 공식 페이지로 확인
- **세션 시작 체크** (Claude 모델 체크와 병행):
  ```bash
  codex --version                       # 현재 CLI 버전
  npm view @openai/codex version        # npm registry 최신 버전 (실제 설치 채널)
  # 참고: which codex → /opt/homebrew/bin/codex → npm 글로벌 symlink (brew 아님)
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
- 📊 **DB 추적 가이드**: `AUDIT_TRAIL_GUIDE.md` 영역 참조 — close_reason / closed_by / force_closed / duration_minutes 4W 추적 + SQL 활용 사례 (v2.15.14 audit trail 통일 후)
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

## 📐 책임 분리 원칙 — App / View / Admin (2026-05-25 명문화)

> **배경**: VIEW Sprint 71 (자동 마감 분석 페이지) mockup 의 [복원] 버튼 catch trigger. VIEW 측에 input 라우트 (force-close / reactivate / ship-complete / admin-complete / worker 비활성화) 가 편의 명분으로 점점 늘어남 → 책임 영역 흐려짐. 사용자 catch (5-22 ~ 5-25) 후 명문화.

### 3 카테고리 분리

```
App (OPS PWA)
   = 모든 input / mutation 단일점
   · 모바일 환경 적합
   · 작업자 작업 — QR 스캔 / 작업 시작·완료 / 일시정지 / 체크리스트
   · 매니저 mutation (편의 명분 시 제한적 허용) — 강제종료 / 재활성화 / 출하완료 / admin-complete
   · OPS BE service layer (task_service / shipment_service / checklist_service 등) = mutation 단일점

View (AXIS-VIEW)
   = 모든 output / read-only
   · PC 환경 적합
   · 매니저 / GST 조회 — Manager Dashboard / S/N 상세뷰 / 공장 대시보드 / 분석 페이지
   · 통계 / KPI / 차트 / drill-down / 보고서
   · 원칙: mutation 0 (read-only)

Admin (PC 환경 input)
   = 별 카테고리 (예외 인정)
   · PC 적합 mutation (모바일 부적합 = Excel 업로드 / 다중 행 편집 / 권한 관리 등)
   · 위치: VIEW repo 내 admin 페이지에 둠 (현재 운영 패턴 유지)
   · 권한: `@admin_required` 또는 `@manager_or_admin_required` 명시
   · 예시: 자재 마스터 Excel 업로드 / 공지 작성·관리 / 권한 토글 / 체크리스트 master CRUD
```

### BE 측 = 이미 정합 (변경 0)

OPS BE 가 mutation single source of truth. VIEW / OPS PWA 어느 곳에서 호출해도 동일 OPS BE route 처리:

```
[VIEW 매니저] 강제종료 클릭
   ↓
[OPS BE]   = mutation 처리 단일점 (audit log / WebSocket emit / DB write)
   ↓
[양쪽 broadcast]
```

→ 신규 input 추가 시 **신규 BE route 만들지 않음** → 기존 OPS BE route 호출. BE 측 네이밍·권한·audit·WebSocket 규칙 그대로 따름.

### 향후 신규 sprint catch 규칙

신규 mutation 추가 시 본 원칙 review 의무:

```
[신규 mutation 추가 영역?]
   ├─ 작업자용 (모바일) → OPS PWA   ✅ 명확
   ├─ 매니저 PC 빠른 처리 (편의) → 다음 catch 의무:
   │   · OPS PWA 측 동일 기능 가능?
   │   · "편의" 명분 명시?
   │   · 점진 회귀 계획?
   │   · 감사 trail 강화?
   └─ Admin PC 영역 (Excel / 다중 행 등) → Admin 카테고리   ✅ 명확
```

→ "그냥 편하니까 VIEW 에 또 넣자" 패턴 자동 차단.

### 기존 VIEW input 라우트 — 점진 OPS 회귀 후보

현재 VIEW 에 존재하는 매니저 mutation 5종 (편의 명분으로 점진 누적):

| 기능 | OPS 동일 기능 | 회귀 우선순위 |
|---|---|---|
| Force-close | OPS admin_options_screen ✅ | 🟠 MEDIUM |
| Reactivate | OPS + VIEW 양쪽 ✅ | 🟠 MEDIUM |
| Ship-complete | OPS v2.17.1 ✅ | 🟡 LOW |
| Admin-complete (PI/QI 종료) | OPS v2.18.0 ✅ | 🟡 LOW |
| Worker 비활성화/재활성화 | OPS admin_options_screen 일부 ✅ | 🟡 LOW |

→ Sprint 75 (가칭) — VIEW input 점진 OPS 회귀 BACKLOG 등록. ~6개월 점진. 즉시 제거 X (운영 매니저 익숙 + UX 영향).

### 실무 운영 가이드

- **신규 input 라우트 추가 시**:
  1. App / View / Admin 카테고리 판단
  2. App → OPS PWA UI 추가 + BE route 신설/재사용
  3. View → ⚠️ 본 원칙 review 의무. 편의 명분 명시 + 점진 회귀 계획
  4. Admin → VIEW admin 페이지 추가 OK (예외 인정)
- **WebSocket emit** = OPS BE 단일점 (REST API 와 별 layer, 양방향 broadcast 정합)
- **Audit trail** = OPS BE `audit_log.py` 미들웨어 일괄 처리 (호출 출처 OPS PWA / VIEW 무관)

### 업계 표준 정합

본 원칙은 다음 패턴들의 GST 적용:
- **CQRS** (Command Query Responsibility Segregation) — Command = App, Query = View
- **SSoT** (Single Source of Truth) — OPS BE = mutation 단일점
- **DDD** (Domain-Driven Design) — Read / Write Model 분리

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
| GALLANT     | FALSE      | FALSE  | TRUE        | 탱크 일체형 (MECH 패키지 포함, migration 024 flip) |
| MITHAS      | FALSE      | FALSE  | FALSE       | 탱크/도킹 없음 |
| SDS         | FALSE      | FALSE  | FALSE       | 탱크/도킹 없음 |
| SWS         | FALSE      | FALSE  | TRUE        | 탱크 일체형 (MECH 패키지 포함, migration 024 flip) |
| IVAS        | TRUE       | TRUE   | FALSE       | 항상 2탱크(L/R), TMS 별도, 도킹 있음 |
```
- DRAGON: tank~mech 일괄 처리. 주로 TMS(M)이지만 **반드시 product_info.mech_partner 확인**
- product_info 단위 override 가능하도록 설계
- **migration trail (Sprint 63-BE 정정 2026-04-30 — Codex 라운드 1 Q1 반영)**:
  - migration 006 (Sprint 6 schema): GALLANT/SWS `tank_in_mech=FALSE` 초기 seed
  - migration 024 (multi-model support, L20-21): GALLANT/SWS `tank_in_mech=TRUE` flip + UPSERT
  - **현재 운영 DB 정합 = `tank_in_mech=TRUE` 3개 모델: DRAGON / GALLANT / SWS**
- **Sprint 63-BE MECH 체크리스트 scope_rule='tank_in_mech'** 매칭 = 위 3개 모델 (Exhaust/TANK/Quenching 그룹 9 항목)

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
| v2.10.13 | 2026-04-28 | FIX-DB-POOL-DIRECT-FALLBACK-LOG-LEVEL + FIX-WEBSOCKET-STOPITERATION-SENTRY-NOISE | Sentry 잡음 정리 2 Sprint 묶음 — (1) db_pool.py L172 `logger.error` → `logger.warning` 강등 + `_direct_fallback_count` counter + getter (의미론 정합, fallback = 의도된 안전망). Sentry `[db_pool] All pool connections unusable` 22 events 동결. (2) `__init__.py` 모듈 top-level `_sentry_before_send` hook 신설 + `sentry_sdk.init(before_send=...)` 등록. flask-sock wsgi StopIteration 매칭 3조건 (exc_type+mechanism+transaction) 모두 성립 시 drop. Sentry PYTHON-FLASK-2 302 events 동결. pytest 7/7 PASS (db_pool 3 + sentry_filter 4). 진짜 ERROR 추적성 회복 |
| v2.10.14 | 2026-04-28 | FIX-FACTORY-KPI-SHIPPED-V2.4-AMENDMENT | Sprint 62-BE v2.2 의 `_count_shipped` 3 분기 보정 — (1) basis='plan' INNER JOIN cs.si_completed=TRUE → LEFT JOIN app_task_details + OR (`actual_ship_date IS NOT NULL OR t.completed_at IS NOT NULL`), W17 0 상수화 해소 (2) basis='ops' 폐기 (app SI 100% 후 ops=actual 수렴 영구 무의미) (3) basis='best' 신설 (reality=actual_ship_date IS NOT NULL + 주간 귀속=COALESCE(DATE(si), actual)). task_id 'SI_SHIPMENT' 대문자 정정 (실 DB 값). weekly/monthly-kpi 응답 4곳 shipped_ops→shipped_best. Pre-deploy Gate ③ R-02 해석 A (si⊆actual) 반례 0건 검증 완료. test_factory_kpi 17 passed / 3 skipped (v2.3 ops 의존 TC 갱신 한계 — 운영 데이터 보존 정책상 fixture 확장 불가) + 신규 TestFactoryKpiV24Amendment 3 TC PASS. 후속 AXIS-VIEW Phase 2 (v1.35.0) 착수 가능 |
| v2.10.15 | 2026-04-29 | FIX-ACCESS-LOG-RETENTION-90D | scheduler_service `_cleanup_access_logs` cron 의 보관 기간 30일 → 90일 완화 (1줄). Sprint 32 도입 정책 보강. 현재 30 MB / 일평균 2,144 rows / 90일 시뮬레이션 64 MB (Railway Hobby plan 0.5 GB 한도 12.8%, 무시 가능). 4-22 silent failure 같은 사고 사후 검증 윈도우 확보 + 분기 추세 분석 가능. BE only / 회귀 0 |
| v2.10.16 | 2026-04-30 | FIX-DB-POOL-WARMUP-WATCHDOG | 4-29 23:31 ~ 4-30 09:30 (1.5h+) silent failure 재발 방지 — warmup cron 은 살아있는데 `_pool=None` 이라 `logger.debug` 로 0/0 출력만 한 채 Sentry 미포착 사고. `db_pool.warmup_pool()` L266 `logger.debug` → `logger.error` 격상 + pid context (Worker 식별). LoggingIntegration(event_level=ERROR) 자동 Sentry capture 활성화 → 다음 발생 시 1분 안에 알림. test_db_pool 신규 TC `test_warmup_logs_error_when_pool_none` 추가 (4/4 PASS). 후속 (선택): HOTFIX-06b per-worker warmup 별건 |
| v2.10.17 | 2026-05-01 | HOTFIX-09 | Sprint 32 (v1.9.0, 3-19) 도입 access_log cleanup cron 의 `get_db_connection` import 누락 — 43일간 매일 03:00 NameError silent failure. 4-29 측정 89,076 rows / 41일 누적 = cleanup 0회 입증. Sentry 도입 (v2.10.8) 후 4-28 부터 capture 시작 → 5-01 발견. `scheduler_service.py L1122 _cleanup_access_logs()` 함수 본체에 `from app.models.worker import get_db_connection` 1줄 추가 (다른 11개 함수와 동일 패턴). 5-02 03:00 cron 부터 정상 작동. Sentry 가치 입증 #4 사례 |
| v2.12.0 | 2026-05-07 | FEAT-MATERIAL Step 1 | Migration 053 — `public.{product_bom, bom_checklist_log, bom_csv_import}` DROP RESTRICT → `checklist` 스키마로 이전 + `material_master` 신설 (10 cols, item_code UNIQUE). FK material_id RESTRICT, FK bom_item_id RESTRICT. `checklist_record.selected_material_id` FK 컬럼 추가. 7 indexes (3 partial WHERE) + 3 BEFORE UPDATE triggers. pytest 9/9 GREEN. Codex 라운드 1 (M=0/A=2) 합의. AXIS-VIEW Step 4 admin GUI 매핑 영역 BE 인프라 사전 준비 |
| v2.12.1 | 2026-05-08 | FEAT-MATERIAL Step 2 | Migration 053a (185 자재 + 1626 BOM 매핑 seed) + 053b (description TEXT 컬럼 + 13 MFC backfill atomic). CSV 변환: `material_master_통합.csv` 비고 컬럼 추가, 1110299900 LNG/O2 dual-use 단일 row 합침 (RFC 4180 quote `"LNG,O2"`). Generator 자체 보강: ALTER TABLE ADD COLUMN IF NOT EXISTS prefix → test DB fresh boot self-contained. ILIKE 검색 1110299900 LNG/O2 양쪽 매칭 검증. pytest 11/11 + 회귀 9/9 = 20/20 GREEN. Codex 라운드 5 (M=0/A=1) 합의 — A 1건 = AXIS-VIEW Step 4 dropdown 회귀 검증은 별 repo 영역 |
| v2.12.2 | 2026-05-08 | FEAT-MATERIAL Step 3 | checklist_service.py 4 신규 함수 (`_collect_material_ids` / `_fetch_material_master_map` / `_enrich_select_options` / `_validate_material_id`) + N+1 BATCHED 단일 SELECT (Codex P0 #3 정합) + dual-format 호환 (옛 string array + 신규 int material_id array). selected_material_id 직접 전달 (NEW-M-01) — upsert_mech_check + upsert_elec_check 인자 추가 + 검증 + INSERT/UPDATE 컬럼 갱신. 옵션 Y 표시 형식 — `name (description) | spec_1 | spec_2` (5-08 사용자 결정 — 같은 spec MFC LNG/O2 분리 가시성). FE mech_checklist_screen.dart `_selectMaterialIdMap` 신규 + onChanged idx lookup + PASS/NA 라디오 번들 PUT 동봉 + **재진입 hydrate (BE COALESCE 응답 → FE setState 복원)** — Codex 라운드 1 M=2 (G+D silent NULL overwrite) 정정. pytest 14/14 + 회귀 20/20 = 총 34/34 GREEN. Codex 라운드 2 GREEN (M=0/A=1 운영성). 작업자 화면 회귀 0 (current prod 8개 string_array 영역 그대로 표시) — Step 4 admin GUI 매핑 후부터 자재 동적 표시 활성 |
| v2.12.3 | 2026-05-08 | FEAT-MATERIAL Step 4 (OPS BE) | admin endpoints 신규 — `backend/app/routes/admin_materials.py` (5 endpoint: GET list / POST create idempotent / PATCH update / PATCH deactivate / PATCH reactivate) + `backend/app/routes/admin_checklists.py` (2 endpoint: GET options / PATCH options) + Blueprint 등록. 권한 `@jwt_required + @gst_or_admin_required` 2단 적층 (Sprint 27 v1.7.4 표준, ADR-023 #6 — 기존 데코레이터 활용). dual-format 호환 (legacy string + 신규 int array) + array_position 순서 보존 + xmax trick idempotent (1차 created=true / 2차 false). 5종 검증 (list/int/중복/material_master 존재+is_active/item_type=SELECT). pytest 13/13 + 회귀 34/34 = 총 47/47 GREEN. Codex 라운드 1 GREEN (M=0/A=6 advisory, BACKLOG 처리). **Sprint 66-BE OPS 측 100% 완료** — AXIS-VIEW Sprint 42 (별 repo) admin GUI consume endpoint 인프라 확보 |
| v2.12.4 | 2026-05-10 | FIX-ELEC-IF-NAMING-DOCKING-CLARITY | ELEC IF_1/IF_2 task_name 도킹 전/후 명시 (작업자 혼동 방지). `task_seed.py` TaskTemplate 2 line + `task_service.py` 알림 message 1 line + Migration 054 (UPDATE 370 row atomic + DO block 검증) + pytest TC 2 파일 갱신. task_id 변경 0 (식별자 보존, 코드/알림/체크리스트 매칭 영향 0). prod 적용 완료 — IF_1: 'I.F 1' → 'I.F 1 (도킹 전)', IF_2: 'I.F 2' → 'I.F 2 (도킹 후)' 각 185 row. FE 코드 변경 0 (task_name display only). 회귀 위험 0 |
| v2.12.5 | 2026-05-11 | FIX-ADMIN-OPTIONS-LISTS-SCROLL-ALERT-DEFAULT + HOTFIX-SPRINT66BE-MASTER-LIST-ITEM-TYPE | **4건 묶음 release (BE+FE)**. ①~③ Admin 옵션 3건 정정 (사용자 5-11 catch). ① FE/BE API 키 불일치 silent fail (`admin_options_screen.dart` `response['workers']` → `'inactive_workers'`/`'deactivated_workers'`, admin.py L2432/L2471 정합). ② 3 list 영역 ConstrainedBox 240px max + 스크롤 wrap (비활성 사용자 / 비활성화 계정 / 미종료 작업). ③ `alert_task_not_started_enabled` SETTING_KEYS default `True` → `False` (BE admin.py L71 + FE state L35 + fallback L324). ④ **HOTFIX-SPRINT66BE-MASTER-LIST-ITEM-TYPE-20260511** (cowork 실수 #18, S2) — `checklist.py` `list_checklist_master()` SELECT 절 + 응답 dict 에 `cm.item_type` + `cm.select_options` 누락 정정 (+2 LoC). AXIS-VIEW v1.43.1 ChecklistEditModal `item.item_type === 'SELECT'` 분기 항상 false 회귀 영역 fix. 회귀 위험 0 (additive). POST-REVIEW deadline 2026-05-18 |
| v2.12.6 | 2026-05-11 | HOTFIX-SPRINT66BE-CREATE-MASTER-ITEM-TYPE-AND-CONFLICT-MSG | **BE only patch release**. cowork 실수 #19 (ADR-024 분리 정책 결정 시급 영역) — `checklist.py` `create_checklist_master()` POST INSERT 정정 (~50 LoC). **3 분리 fix**: (1) `item_type` 추출 + enum 검증 (CHECK/SELECT/INPUT) — FE 가 전송한 type 무시되어 DB DEFAULT 'CHECK' 저장되던 회귀 (Sprint 52 시점 ~ Sprint 63-BE 'INPUT' enum 확장 시점 누적). (2) `select_options` 추출 + list 검증 + json.dumps() 직렬화 (admin_checklists.py L224 컨벤션 정합). (3) CONFLICT 응답 보강 — 기존 충돌 항목 id + is_active 포함 + 비활성 시 토글 안내 메시지. AXIS-VIEW 신규 SELECT/INPUT 항목 추가 정상화. 회귀 위험 0 (FE 가 item_type 미전송 시 'CHECK' fallback). POST-REVIEW deadline 2026-05-18 |
| v2.14.1 | 2026-05-12 | FIX-DB-POOL-CONN-LEAK-WORK-PY-20260512 | **BE only patch release — work.py conn leak 5 위치 fix**. 2026-05-12 KST 16:48 사고 trigger: Railway pool exhausted (MAX=30 도달) 직접 catch 후 root cause 분석. **Root cause**: `routes/work.py` L705 `conn2.close()` 직접 호출 — psycopg2 close 메서드 (ThreadedConnectionPool 영역 `put_conn()` 호출 영역) → pool 영역 conn 영역 "사용 중" 영역 영역 추적 → **영구 leak**. 모바일 작업자 `GET /api/app/tasks/{sn}` 영역 호출 마다 1 conn 영구 누수 + 8분간 10건 누적 → MAX=30 도달. **자가 회복 영역 정상 작동** (FIX-DB-POOL-SELF-RECOVERY v2.11.6 영역, 3 cycles=15분 후 close_pool+init_pool 자동 회복) 영역 사용자 측 restart 영역 정상화. **Fix 5 위치 (모두 work.py)**: ① L705 `conn2.close()` → `put_conn(conn2)` + try/finally (영구 leak 차단) ② L676-707 `conn2=None` 초기화 + finally (my_status) ③ L594-670 try/finally 패턴 (workers 배열) ④ L568-583 try/finally + worker_map 외부 초기화 (worker_name) ⑤ L468-486 try/finally (complete_single_action_route). **검증**: pytest 45/45 PASS (test_work_api + test_work_batch Sprint 64-BE v3 30 TC + test_task_workers_api 7 TC) / Flask app boot OK / `conn.close()` 0건 (이전 1건) / put_conn 7→8 / finally 2→6. **Codex 라운드 1 GREEN** (M=0/A=1) — A-1 = INSERT except rollback 명시 권고 (별 sprint BACKLOG). **회귀 위험 0**. **연관**: FIX-DB-POOL-SELF-RECOVERY (5-04, 자가 회복) + FIX-DB-POOL-MAX (4-27, MAX=30) — 모두 누수 후 영역 fallback/회복 영역, 본 fix가 누수 자체 차단 |
| v2.14.0 | 2026-05-12 | Sprint 66-BE-FOLLOWUP v3 (SPRINT-66-BE-FOLLOWUP-MATERIALS-UPLOAD-20260511) | **BE only minor release — 자재 마스터 Excel 일괄 업로드 endpoint 신규**. AXIS-VIEW Sprint 42 v1.43.0 `MaterialUploadModal.tsx` 4단계 워크플로우 prod 배포 완료 영역 BE 404 영역 fix. 신규 파일 2개 (CLAUDE.md L545 분리 정책 정합) — `backend/app/utils/material_parser.py` (+228 LOC, parsing + 7종 검증 + Q1 MFC scope) + `backend/app/services/material_upload_service.py` (+228 LOC, diff_with_db 6 필드 + commit_upload strategy 분기). `routes/admin_materials.py` /upload route 추가 (+88 LOC). 의존성 추가 (chardet>=5.2.0 + openpyxl>=3.1.0). **Codex 검증 5 라운드 trail** (M=4→4→2→1→0 GREEN): 라운드 1 M=4/A=5 → v2 trail 영역 / 라운드 2 M=4 (non-MFC scope catch + MFC INVALID_BOM_KEY catch + category 50 누락 + 본문 단일소스화) → v3 본문 직접 정정 / 라운드 3 M=2 (diff_with_db spec + ATTRIBUTE_CONFLICT 정책 + Step 순서) / 라운드 4 M=1 (tuple unpacking + TC 24 통일 + pair-wise IN) / 라운드 5 M=0 GREEN. **v3 핵심 결정**: ① Q1 MFC scope only (category=='MFC' 영역만 합침) ② non-MFC 중복 = dedup 첫 등장 사용 (053a 패턴 정합) ③ ATTRIBUTE_CONFLICT = 자재 정보 충돌만 (첫 등장 유지 + 후속 reject) ④ INVALID_BOM_KEY = BOM row 영역만 (product_code != '') / material-only MFC rows 허용 ⑤ FIELD_TOO_LONG 8 필드 (item_code 50 / item_name 200 / category 50 / spec_1 200 / spec_2 200 / unit 20 / customer 100 / model 100, description 영역 TEXT — 검증 X) ⑥ 파일 형식 csv + xlsx (`.xls` drop) ⑦ 파일 분리 utils (parser) + services (upload) ⑧ error envelope `{error, message}`. pytest 23/23 GREEN (Unit 12 + Integration 11, TC-MU-11 ROLLBACK 의도 skip, staging DB 2분 52초). **회귀 위험 0**: 기존 admin_materials.py 5 endpoint 영향 0 / DB schema 변경 0 / migration 불필요. **연관**: AXIS-VIEW Sprint 42 v1.43.0 (FE prod 배포 완료) + Sprint 64-BE v3 학습 (분리 정책 + 트랜잭션 패턴) + ADR-029 Tier 2 (CRUD endpoint 일관성). 설계 상세: AGENT_TEAM_LAUNCH.md § Sprint 66-BE-FOLLOWUP v3 (L36396~L36900, Codex 5라운드 catch trail + v1→v2→v3 차이 매트릭스) |
| v2.13.2 | 2026-05-11 | HOTFIX-TASKS-BY-ORDER-WORKERS | **BE only patch release** — Sprint 64-BE v3 / v2.13.1 후속 hotfix (S1 동반). VIEW v1.43.6 S1 HOTFIX catch — `/tasks/by-order/<sales_order>` 응답에 `workers` 배열 누락 → FE `task.workers.find()` TypeError → React crash → S/N 상세뷰 흰 화면 발생. **Root cause**: 내 `get_tasks_by_order()` 영역 `_task_to_dict()` 호출 후 후처리 영역 X. `get_tasks_by_serial` (work.py L562~728) 영역 약 170 line 후처리 (workers 배열 + worker_name + my_status 일괄 조회) 영역 누락. Codex 5 라운드 + v2.13.1 catch 모두 영역 endpoint 응답 spec 정합 영역 동일 후처리 영역 검증 누락. **변경 (~110 LoC)**: `task_service_batch.py` 영역 신규 helper `_enrich_tasks_with_workers(task_list)` 영역 추가 — work_start_log JOIN workers JOIN work_completion_log 일괄 조회 + worker_name 영역 + legacy fallback. `get_tasks_by_order()` 영역 helper 호출 추가 (1 line). **응답 schema 추가**: 각 task item 영역 `workers: [{worker_id, worker_name, company, started_at, completed_at, duration_minutes, status, is_orphan, task_closed_at}, ...]` + `worker_name`. **회귀 위험 0**: VIEW v1.43.6 정규화 코드 (`workers ?? []`) 영역 BE 응답 후에도 자동 정상 작동. `_enrich_tasks_with_workers()` 영역 private helper (work.py touch 0). **POST-REVIEW 후속**: Codex 검증 라운드 영역 spec 일관성 + 후처리 패턴 일관성 항목 동시 검증 표준화 권고 (재발 방지). **연관**: AXIS-VIEW v1.43.6 S1 HOTFIX (FE 정규화 + 가드) + Sprint 64-BE v3 (v2.13.0) + v2.13.1 (응답 형식). 설계 trail: CHANGELOG.md v2.13.2 entry + workers 배열 schema |
| v2.13.1 | 2026-05-11 | HOTFIX-TASKS-BY-ORDER-SCHEMA | **BE only patch release** — Sprint 64-BE v3 후속 hotfix. `/api/app/tasks/by-order/<sales_order>` 응답 형식 정정 — Before: `{tasks: [...], total: N}` 객체 wrap (Sprint 64-BE 영역 일관성 위반) / After: `[...]` 배열 직접 반환 (다른 list endpoint `/api/app/tasks/{sn}?all=true` 정합). 트리거: AXIS-VIEW v1.43.5 catch — `getTasksByOrder()` 영역 `Array.isArray(data) ? data : []` 영역 객체 응답 → 빈 배열 fallback → 일괄 시작 토스트 X (TEST-1111 단일 처리만). **Root cause (Codex 5라운드 catch 누락 영역)**: AGENT_TEAM_LAUNCH.md v3 본문 영역 `{tasks, total}` 명시 영역 있었지만, 기존 endpoint 영역 spec 영역 대조 안 함. POST-REVIEW catch. **변경 (~5 line)**: `task_service_batch.py` `get_tasks_by_order()` return type `Tuple[Dict, int]` → `Tuple[List[Dict], int]`, return 영역 `({'tasks': tasks, 'total': N}, 200)` → `(tasks, 200)`. `work_batch.py` `jsonify()` 그대로 (Flask 3.x list 자동 처리). **회귀 위험 0**: VIEW v1.43.5 `getTasksByOrder()` 영역 두 형식 모두 호환 코드 도입 → BE 응답 변경해도 자동 정상 작동. **연관**: AXIS-VIEW v1.43.5 HOTFIX-TASKS-BY-ORDER-SCHEMA (FE 호환 코드) + Sprint 64-BE v3 (선행 v2.13.0). 설계 trail: 사용자 측 VIEW 분석 + 5 endpoint 응답 spec 비교 표 |
| v2.13.0 | 2026-05-11 | Sprint 64-BE v3 (SPRINT-64-BE-WORK-BATCH-V2-20260511) | **BE only minor release — Work Batch 엔드포인트 신규** (TM Tank Module 일괄 처리, AXIS-VIEW Sprint 40 v1.40.0 contract BE 측 구현). 신규 파일 2개 분리 (CLAUDE.md L545 정합) — `backend/app/routes/work_batch.py` (+117 LOC, 3 route: start-batch / complete-batch / by-order) + `backend/app/services/task_service_batch.py` (+209 LOC, helper reuse 패턴 — 기존 `start_work()`/`complete_work()` audit log + start guards + complete logic 자동 흡수). 기존 `work.py` (1,355 LOC 🔴) + `task_service.py` (1,551 LOC ⛔) touch 0. `__init__.py` +1줄 (work_batch import, register_blueprint 전 필수). **결정 사항**: 30건 상한 (helper task당 7~9 query / pool MAX=30 안전), best-effort sequential (audit log 자동 흡수), `_match_manager_company()` work.py L340-356 reactivate 패턴 정합 (TMS = module_outsourcing OR mech_partner). pytest 30 TC GREEN (Unit 13 + Integration 17 — 22분 10초 staging DB 실측). **Codex 검증 5 라운드 trail**: 라운드 1 M=6/A=3 → v2 재설계, 라운드 2 M=4/A=1 → 분리 파일 + 30건 + 16+ TC, 라운드 3 M=1/A=3 → 12 case 전수 + TC-AUDIT-02 + import 순서 + gate 측정, 라운드 4 M=1/A=1 → prefix 충돌 정정, **라운드 5 M=0/A=1/N=3 GREEN** → pool warm-up 한 줄 추가 후 구현 진입 권고. C1 case 인자 오기 + complete TC reason 예상값 catch 영역 pytest 자체 catch (Codex 5라운드 못 catch). A-1 BACKLOG 등록 (`BUG-MATCH-COMPANY-SUBSTRING-FALSE-POSITIVE-20260511` — BAT vs COMBAT, 운영 미발생). 회귀 위험 0 (기존 endpoint touch 0, DB schema 변경 0, migration 불필요). 설계 상세: `AGENT_TEAM_LAUNCH.md` § Sprint 64-BE v3 |
| v2.15.16 | 2026-05-15 | SPRINT-V2-15-16-MECH-FORCE-CLOSED-PREV-DAY-CAP-20260515 | **BE patch release — Catch 3건 통합 fix (Codex 라운드 1 M=5/N=2)**. 사용자 운영 catch (v2.15.15 검증 후 5-15): ① MECH 체크리스트 Phase 1만 채워도 task close → check_mech_completion default judgment_phase=1 만 검증되던 버그 (사용자 직접 catch). ② ELEC 정상 (확인). ③ close trigger 미완료 task force_closed=TRUE 처리 → 사용자 분석상 trigger 자체가 정상 close 시점 (근무시간 내) 이므로 조건 1 (attendance check_out) + 조건 2 (17:00 fallback) 무의미. **Codex 라운드 1 추가 catch (Claude Code 사전 검토 누락 5건)**: (Q1 M) `check_mech_completion` 호출자 4곳 식별 — checklist.py L1338 + production.py L279 추가 → X-α 회귀 위험 → **X-β 채택 (신규 `check_mech_completion_all()` 함수, 기존 signature 보존)** / (Q2 M) force_closed 버그 5곳 — task_service.py L1357 + L1476 + checklist_service.py L1352 + L1647 + L1669 → 전수 `force_closed=False` 통일 / (Q3 M) auto-close 영역 validate_duration 미호출 → 익일/주말 trigger 18h+ duration silent 저장 → **PREV_DAY_CAP** priority 0 추가 (`calculate_close_at()` signature 영역 `last_started_at` 인자 추가, trigger.date() > started.date() → started.date() 17:00 KST cap, 음수 duration 보호 분기 포함) / (Q5 M) task_service.py L843 Sprint 41-B 레거시 auto-close 루프 (3-arg → default force_closed=True + closed_by=NULL + AUTO_CLOSED_LEGACY) 잔존 → AUDIT_TRAIL_GUIDE.md "v2.15.14 이후 0건" 주장 위반 → **루프 제거, `_trigger_second_close()` 단일 경로 통일**. **변경 (BE 3 파일 + migration 1 + pytest 1 + version)**: (1) `checklist_service.py` 신규 `check_mech_completion_all()` (Phase 1 short-circuit + Phase 2 ELEC 패턴 정합) + IF_2/SELF_INSPECTION/orphan auto-close 3곳 `force_closed=False` 통일. (2) `task_service.py` MECH 분기 `check_mech_completion_all()` 호출 + FIRST/SECOND trigger `force_closed=False` + `last_started_at` 전달 + L843 레거시 루프 삭제 + `_trigger_second_close()` 만 호출. (3) `duration_calculator.py` priority 0 `PREV_DAY_CAP` 추가 (started ≥ 17:00 시 started 그대로 사용 = 음수 duration 차단). (4) `migrations/057_add_prev_day_cap_duration_source.sql` CHECK constraint 4→5 enum. (5) `tests/backend/test_v2_15_16_force_closed_and_prev_day_cap.py` 신규 TC 12건 (시나리오 A/B/C/D + priority 0 + Phase 1+2 + signature). **시나리오 매트릭스**: A 정상 (같은 날) → fallback / B 야간 (같은 날) → fallback / **C 익일** → cap 발동 / **D 주말 후** → cap 발동 / E started ≥ 17:00 → started 그대로 (음수 차단). **검증**: 신규 12/12 PASS (0.14s) + test_relay_first_final.py 38/38 PASS (21.86s) = 50/50 GREEN. **회귀 위험 0** (X-β signature 보존 + additive policy + additive priority 0 + 레거시 루프 직후 `_trigger_second_close()` 동일 task 재처리). **POST-REVIEW (BACKLOG 등록)**: `POST-REVIEW-AUTOCLOSED-CLOSED-BY-20260515` (auto-close `closed_by=worker_id` 기록 vs 설계서 "NULL" 모순 정책 명확화) + `POST-REVIEW-AUDIT-TRAIL-CONSISTENCY-20260515` (force_closed 의미론 변경 영역 AUDIT_TRAIL_GUIDE.md 갱신). **연관**: 사용자 5-15 catch 3건 모두 해결, v2.15.14 audit trail 표준 영역 레거시 잔존분 완전 정리, AXIS-VIEW 영향 0 (BE only) |
| v2.15.17 | 2026-05-15 | FIX-VIEW-ORPHAN-DURATION-MISSING-20260515 | **BE patch release — Trigger task auto-close 시 VIEW 소요시간 미표시 fix (Codex 라운드 1 M=2/A=4)**. 사용자 운영 catch (5-15): "Trigger task close 시 VIEW 에서 소요시간 표시 안 됨 / 정상 완료된 task 만 소요시간 표시 됨". **Root Cause**: `work.py` `get_tasks_by_serial()` + `task_service_batch.py` `_enrich_tasks_with_workers()` worker 배열 조회 SQL 영역 `completed_at` 영역 `COALESCE(wcl.completed_at, td.completed_at)` fallback 있는데 `duration_minutes` 영역 `wcl.duration_minutes` 단독 → orphan worker (auto_close_relay_task() 영역 close, work_completion_log INSERT 안 함) 영역 NULL → VIEW `ProcessStepCard.tsx` `formatDuration(null)` → '—' 표시. 정상 완료 task (worker complete_work() → wcl INSERT) 영역만 표시되던 catch. **Codex 라운드 1 M=2 추가 catch**: (Q1 M) 제안 SQL 영역 음수 duration 가능 (close < started) + float 반환 → integer 계약 위반 → `GREATEST(0, FLOOR(EXTRACT(EPOCH ...)/60))::int` 클램프 + cast 필수 / (Q6 M) `task_service_batch.py` L323 동일 `wcl.duration_minutes` fallback 없음 — `/api/app/tasks/by-order` endpoint 백킹 → 같은 PR 영역 2곳 동시 fix 필수 + `test_hotfix04_orphan.py` 기존 NULL assert 갱신. **변경 (BE 2 파일 + pytest 1 + version)**: (1) `work.py` L645 + `task_service_batch.py` L323 — `duration_minutes` 영역 `COALESCE(wcl.duration_minutes, GREATEST(0, FLOOR(EXTRACT(EPOCH FROM (COALESCE(wcl.completed_at, td.completed_at) - wsl.started_at))/60))::int)` fallback. orphan worker 영역 본인 started_at ~ task close 시각 근사 계산. (2) `test_hotfix04_orphan.py` TC-ORPHAN-01/04 NULL assert → integer 240분 갱신 + TC-ORPHAN-05 신규 (close < started → 0 클램프 검증). **동작**: orphan worker → close-started 근사 / in_progress worker (task open) → COALESCE(wcl/td completed_at) NULL → 전체 NULL 유지 (정상) / 정상 완료 → wcl.duration_minutes (pause 차감 반영). **검증**: pytest test_hotfix04_orphan.py 10/10 PASS (260s). **회귀 위험 0** (SQL 1 expression 2곳, 신규 로직/함수 아님 — work.py God File 1389줄 LOC 증가 ≈ 12줄 = 버그 fix, CLAUDE.md L547 "새 로직 추가 금지" 비위반). **옵션 선택 trail**: 옵션 1 (SQL COALESCE) 채택 — 옵션 3 (auto_close 영역 wcl INSERT) 영역 정확도 동일 (둘 다 close-started 근사) + work_completion_log 의미론 훼손 + task_detail.py 917줄 🔴 필수 분할 파일 새 로직 금지 위반 → 기각. **한계 (별 sprint)**: pause 차감 미반영 근사값 → `REF-WORKER-DURATION-PRECISION` / VIEW `is_orphan` "추정 소요시간" 라벨 → AXIS-VIEW 별 sprint. **연관**: HOTFIX-04 (v2.9.8 orphan 메타필드 도입) + Sprint 41-D auto_close_relay_task 영역 + AXIS-VIEW OPS_API_REQUESTS.md #61 (force_closed 필드) |
| v2.15.18 | 2026-05-15 | POST-REVIEW-OPS-65-PATH2-REOPEN-20260515 | **BE patch release — MECH Dual-Trigger 경로 2 버그 2건 fix (Codex 라운드 1 M=2)**. 트리거: AXIS-VIEW 측 리뷰어가 OPS_API_REQUESTS.md #65 entry 교차검증 중 OPS 배포 코드 (v2.15.13~v2.15.17) 영역 버그 2건 발견. #65 = "MECH 체크리스트 Dual-Trigger" v2.15.13 ✅ COMPLETED 처리됐으나 경로 2 (체크리스트가 마지막) 미완성. **버그 2건**: (M-A4) `_try_mech_close()` 영역 `UPDATE completion_status SET mech_completed=TRUE` 누락 — ELEC `_try_elec_close()` (L1372~1383) 영역 존재. 경로 2 close 후 task 는 닫히는데 `completion_status.mech_completed` FALSE 잔존 → AXIS-VIEW 생산현황 상세뷰 MECH "미완료" 표시 (#65 가 고치려던 증상 그대로). 경로 1 (SELF_INSPECTION 가 마지막) 영역 `task_service.py` complete_work 공용 경로 → `update_process_completion()` → mech_completed set 정상. (M-A7) `upsert_mech_check()` close 게이트 = `check_mech_completion(sn, judgment_phase)` 단독 — FE 가 1차 검수 PUT 시 `judgment_phase=1` → Phase 1 (19개) 단독 판정 → 1차만 채워도 `_try_mech_close()` 발동 → 2차 검수 (관리자 보강) 미입력 상태로 close. v2.15.16 catch 1 (사용자 "MECH 1차만 완료해도 close") 영역 경로 2 잔존분 — v2.15.16 영역 `check_mech_completion_all()` (Phase 1+2 합산) 신규 + `check_category_close_eligible()` (경로 1) 만 교체, 경로 2 게이트 누락. **변경 (BE 1 파일 + pytest 1 + version)**: (1) `checklist_service.py` `_try_mech_close()` — SELF_INSPECTION + 잔여 task close 후 `UPDATE completion_status SET mech_completed=TRUE WHERE serial_number=%s AND mech_completed=FALSE` + `conn.commit()` 추가 (M-A4, ELEC 패턴 정합, Codex Q1d — `auto_close_relay_task()` 자체 별도 conn 사용이므로 `_try_mech_close()` cur 영역 명시 commit 필수). (2) `checklist_service.py` `upsert_mech_check()` — close 게이트 분리: `is_complete` (FE 진행률 표시용, phase별 `check_mech_completion`) 유지 + close 게이트만 `check_mech_completion_all()` (Phase 1+2 합산, 경로 1 정합) (M-A7). (3) `tests/backend/test_v2_15_18_mech_path2_close.py` 신규 TC 5건 (M-A4 completion_status UPDATE 3 + M-A7 close 게이트 2). **검증**: pytest 신규 5/5 PASS (0.09s). **회귀 위험 0** — `task_service.py` 경로 1 touch 0 / ELEC `_try_elec_close()`+`upsert_elec_check()` touch 0 / MECH 경로 2 전용. **영향**: 경로 1 정상 동작 중 — 영향 0 / 경로 2 (체크리스트가 마지막) — mech_completed flag 정상 set + 2차 검수 미입력 시 close 차단 / AXIS-VIEW 생산현황 상세뷰 MECH 동기화 정상화. **연관**: v2.15.13 (#65 MECH Dual-Trigger 도입 — 경로 2 미완성) + v2.15.16 catch 1 (경로 1 만 fix) + AXIS-VIEW OPS_API_REQUESTS.md #65 (§9 Codex 교차검증 기록 — VIEW 측 리뷰 trail) |
| v2.15.19 | 2026-05-18 | FEAT-FACTORY-MONTHLY-DETAIL-BY-CUSTOMER (AXIS-VIEW OPS_API_REQUESTS.md #68) | **BE only minor — 공장 대시보드 월간 고객사 도넛용 집계 필드 추가**. AXIS-VIEW #68 요청 — `monthly-detail` API 응답에 월 전체 고객사별 집계 `by_customer` 추가 (FactoryDashboardPage 월간 뷰 "고객사 비율 도넛" 위젯용). **변경 (BE 1 파일 + pytest 1 + version)**: `factory.py` `get_monthly_detail()` 영역 `by_customer` 집계 쿼리 1건 (`SELECT p.customer, COUNT(*) ... GROUP BY p.customer ORDER BY count DESC, p.customer ASC`) + 응답 dict 키 1개 추가 (~14 LOC, 기존 `by_model` 1:1 복제 패턴). `date_field` 화이트리스트 검증 (`_ALLOWED_DATE_FIELDS` 기존) 후 f-string → SQL 인젝션 안전. NULL customer 는 `by_model` 의 NULL model 과 동일하게 GROUP BY 자연 처리 (FE 필터). `test_factory.py` — `test_md01` by_customer 키 검증 추가 + `test_md01b_by_customer_aggregate` 신규 (키 구조 {customer, count} + count 내림차순 정렬 + by_customer 합계 = total). **검증**: pytest test_factory.py 19/19 PASS (241s, 신규 TC 포함, conftest split fix 적용 상태). **회귀 위험 0** — additive (응답 키 1개 추가, 기존 month/items/by_model/total/page/per_page/total_pages 영향 0, breaking 아님) / DB 스키마·migration 변경 0 / FE 안전 degrade (BE 미배포 시 undefined). **Codex 라운드 1**: M=6/A=2/N=2 — M 6건 중 3건 (Q1-1 fSELECT / Q1-2 ORDER BY 구문 / Q2-1 dict comprehension) 은 Codex 의 prompt 코드블록 오독 (실제 제안 SQL 정상). 유효분 = 응답 dict `by_customer` 추가 (설계 포함) + `test_factory.py` by_customer TC (반영). A-Q1 NULL customer = `by_model` 일관성 위해 원본 유지 (FE 필터). **연관**: AXIS-VIEW OPS_API_REQUESTS.md #68 + FactoryDashboardPage 월간 도넛 (FE 별 작업) + 인프라 conftest migration SQL 분리 통일 (commit 9b4dd7d, POST-REVIEW-PYTEST-FAILED-ANALYSIS) |
| v2.15.20 | 2026-05-18 | FIX-FORCE-CLOSED-REACTIVATION | **BE 1 + VIEW 1 + pytest patch release — 강제종료 task 재활성화 정상화 (Codex 라운드 1 M=2/A=2/N=3)**. 사용자 catch (5-15~18): 생산현황 상세화면(VIEW)에서 ①강제종료한 task 를 재활성화해도 "🔒 강제종료" 표시 잔존 ②미시작 task 를 강제종료한 경우 재활성화 버튼 자체가 미표시. **Root Cause**: (Catch 1 BE) `task_detail.py reactivate_task()` UPDATE SQL 이 `completed_at/started_at/worker_id/duration_minutes/elapsed_minutes/worker_count` 만 NULL 처리 — 강제종료 메타데이터 `force_closed/closed_by/close_reason/duration_source` 4컬럼 미처리 → 재활성화해도 force_closed=TRUE 잔존. (Catch 2 VIEW) `ProcessStepCard.tsx` 재활성화 버튼 조건 `w.completed_at` 의존 — 시작 이력 있는 강제종료는 worker completed_at 채워져 버튼 표시 / 미시작 강제종료는 SNDetailPanel placeholder worker `completed_at=null` 이라 미표시. **변경**: (1) `task_detail.py reactivate_task()` UPDATE SET 절에 `force_closed=FALSE, closed_by=NULL, close_reason=NULL, duration_source=NULL` 4줄 + docstring (Codex M-Q2 — 4컬럼 전부 리셋, 일부 보존 시 "활성 task인데 강제종료 사유 잔존" 모순). (2) `AXIS-VIEW ProcessStepCard.tsx` 버튼 조건 `w.completed_at` → `(w.completed_at || w.force_closed)` (v1.44.2). (3) `test_sprint41_task_relay.py` TC-41-12 SQL 4컬럼 검증 확장 + 통합 TC-41-17/18 신규 (Codex M-Q6). **연계 영향 검토**: closed_by/close_reason/duration_source 참조처 전부 LEFT JOIN·NULL 허용 (migration 056/057 CHECK constraint `IS NULL OR IN(...)`) → 안전 / force_closed=FALSE 는 reactivate 가 completed_at=NULL 동반 → factory `_count_shipped()` KPI 오염 0. **검증**: pytest reactivate 6/6 GREEN, VIEW tsc/vite build GREEN. **Codex 라운드 1**: M=2 (Q2 4컬럼 / Q6 pytest) 반영, A=2 BACKLOG 이관 (`REACTIVATE-AUDIT-TRAIL-20260518` 재활성화 append-only audit 로그 / `REF-REACTIVATE-DECORATOR-20260518` `@manager_or_admin_required` 데코레이터 일관성), N=3. **회귀 위험 0** (additive). **연관**: Sprint 41 reactivate + HOTFIX-04 (v2.9.8 orphan 메타필드) + AXIS-VIEW v1.44.2 |
| v2.15.21 | 2026-05-18 | #69 월간 생산량 KPI TEST CUSTOMER 제외 | **BE only 1 파일 patch release**. 사용자 catch (5-18): 공장 대시보드 월간 생산량 KPI 카드(169)와 Sprint 44 고객사 도넛 중앙(164) 불일치 — `TEST CUSTOMER` 테스트 데이터 5대가 월간 생산량 KPI 에 집계되어 부풀려짐. **변경**: `factory.py get_monthly_kpi()` `production_count` 쿼리 WHERE 절에 `AND COALESCE(p.customer, '') <> 'TEST CUSTOMER'` 1줄 추가. **검증**: pytest test_factory 19/19 GREEN (회귀 0), FE 변경 0 (`production_count` 응답값 169→164 자동 반영, 고객사 도넛과 일치). DB/migration 변경 0. ②단계 자동 Codex 이관 체크리스트 6항목 0개 해당 (WHERE 1줄) → Opus 자가 리뷰. **연관**: AXIS-VIEW OPS_API_REQUESTS.md #69 + v2.15.19 (#68 by_customer 도넛) |
| v2.16.0 | 2026-05-18 | Sprint 67-BE — progress API 공정 토글 신호 (FEAT-SNSTATUS-PROGRESS-TOGGLE-SIGNALS-20260518) | **BE only 1 파일 minor release — AXIS-VIEW Sprint 46(생산현황 PI/QI/SI 공정 토글 필터)의 BE part**. VIEW 토글 표시 조건이 공정별 "태깅 여부/완료 시각/오늘 완료 여부"를 요구하나 progress API `categories` 가 `{total,done,percent}` 3필드만 → BE 보강. **변경**: `progress_service.py get_partner_sn_progress()` — `task_progress` CTE 에 `MAX(completed_at)` + `completed_today`(KST `DATE()=CURRENT_DATE`) / `tagged_categories` CTE 신규(`work_start_log` DISTINCT) / 메인 SELECT LEFT JOIN + `started` 산출 / `_aggregate_products()` categories dict 3필드 확장. **응답 스키마 (additive)**: `categories[CAT]` = `{total,done,percent}` → `+ {started, completed_at, completed_today}`. **핵심 결정**: "태깅됨" = `work_start_log` 기반 (Codex M-Q2) — `app_task_details.started_at` 기반이면 `reactivate_task()`(v2.15.20) 재활성화 시 NULL 리셋으로 이력 소실, `work_start_log` 는 보존되므로 재활성화된 task 의 토글 자동 재등장 보장. **검증**: pytest test_sn_progress 22/22 GREEN (기존 16 + 신규 TC-PROGRESS-TOGGLE-01~06 — completed_at/started true·false/재활성화 후 started 유지/completed_today/regression). additive → 기존 3필드 불변 VIEW 소비처 회귀 0. migration 불필요 (기존 테이블만 조회). **Codex 라운드 1**: M=1(Q2 work_start_log 기반) + A=6 전건 반영 — VIEW `DESIGN_FIX_SPRINT.md` Sprint 46 영역 9 통합 검증. **연관**: AXIS-VIEW Sprint 46 (`FEAT-SNSTATUS-PROCESS-TOGGLE-FILTER`) FE part — BE v2.16.0 배포 후 FE 구현 (Sprint 45 v1.45.0 롤백 + PI/QI/SI 토글 UI). 설계: `AGENT_TEAM_LAUNCH.md` § Sprint 67-BE |
| v2.17.0 | 2026-05-19 | Sprint 68 — 출하 완료 ship-complete endpoint (FEAT-SHIPMENT-COMPLETE-20260518) | **BE 신규 2 파일 minor release — 출하 완료 endpoint**. 출하 시점엔 작업자가 QR 태깅으로 SI task 완료가 어려움 → admin/manager 가 VIEW/OPS 화면에서 대행. **변경**: `shipment_service.py`(신규 — `ship_complete()` + 헬퍼 3개) + `routes/work_shipment.py`(신규 — `POST /api/app/work/ship-complete`, `@manager_or_admin_required`) + `__init__.py` side-effect import 1줄. **동작**: 한 S/N 의 SI task 2개(`SI_FINISHING` NORMAL + `SI_SHIPMENT` SINGLE_ACTION) 완료 — task 타입별 분기(`_finalize_task_multi_worker`+`complete_task` / `complete_single_action`), `completed_at` 지정 가능(미래 차단 + SI_FINISHING started_at 이전 차단), 멀티작업자 orphan `work_completion_log` backfill(force_closed 아닌 정상 완료), audit(`close_reason='SHIP_COMPLETE'`+`closed_by`, `force_closed=FALSE` 유지 — DB 추적), 멱등(둘 다 완료 시 200 `already_completed:true`), `completion_status.si_completed` 갱신. **검증**: pytest `test_ship_complete` 12/12 GREEN (TC-SHIP-01~12). **Codex 라운드 1**: M=5(SI 타입 분기 / force_closed=FALSE / 멀티작업자 backfill / completed_at 검증 / pytest TC) + A=1(멱등) + N=1 전건 반영 — 설계 `AGENT_TEAM_LAUNCH.md` § Sprint 68 영역 10+11. migration 불필요 (기존 테이블만 조회·UPDATE). 기존 complete/complete-batch 영향 0. **연관**: AXIS-VIEW Sprint 47 (`FEAT-SHIPMENT-COMPLETE-BUTTON` — VIEW 출하완료 버튼, VIEW 세션 담당) + OPS FE 후속 (SI 마무리공정 화면 출고 버튼 B / PI·QI·SI 카드 O/N 표시 C). 출하완료 기준 = Sprint 46 SI 토글 "출하 완료 시 제거" 정합 |
| v2.17.1 | 2026-05-19 | Sprint 68 OPS FE — SI 출고 버튼 + PI/QI/SI O/N 표시 | **BE 1 + FE 1 파일 patch release — Sprint 68 의 OPS FE part**. v2.17.0 ship-complete endpoint 의 OPS 앱 화면 연동. **변경**: (B) `frontend/lib/screens/gst/gst_products_screen.dart` — SI 마무리공정 화면 카드("진행중" 뱃지 아래)에 `[내 작업 완료]`(`POST /work/complete` finalize=false, 진행 중 task 만 노출) + `[출고 완료]`(`POST /work/ship-complete`, admin/manager 만) 버튼 + 확인 다이얼로그 + 완료 토스트. (C) `backend/app/routes/gst.py` `get_gst_products()` — products 응답에 `customer`/`sales_order` 추가(additive) + 카드에 `O/N · 고객사` 표시 (PI 가압검사/QI 공정검사/SI 마무리공정 3화면 공용 `gst_products_screen`). **검증**: flutter build web GREEN. **Codex 라운드 1**: M=2(멱등 응답 `already_completed` 토스트 분기 / 권한 403 친화 메시지) + A-Q7(`_fetchProducts` mounted 가드) 반영, A-Q4(`ref.read` stale)·A-Q6(UX scope) 미반영(advisory — 권한 세션 불변 / SI 화면 의도). `gst.py` additive — 기존 소비처 회귀 0, migration 불필요. **연관**: v2.17.0 (Sprint 68 BE ship-complete) + AXIS-VIEW Sprint 47 (출하완료 버튼 — VIEW 세션 담당) |
| v2.17.2 | 2026-05-19 | Sprint 68 fix — OPS SI 마무리공정 화면 출고 대기 누락 | **BE only 1 파일 patch release**. 사용자 catch — OPS SI 마무리공정 화면에 SI_FINISHING 작업이 완료된 출고 대기 제품(GBWS-7094/7095)이 안 보이고 진행중 TEST 제품만 표시. **원인**: `gst.py get_gst_products()` SI 화면이 `started_at IS NOT NULL AND completed_at IS NULL`(= SI_FINISHING 작업 진행중)만 표시 → SI_FINISHING 작업은 완료됐고 출하완료(SI_SHIPMENT)만 안 된 출고 대기 제품 누락 (출고 완료 버튼 대상이 정작 화면에 없는 모순). **변경**: `gst.py` SI 카테고리 WHERE 분기 — `task_id='SI_FINISHING' AND started_at IS NOT NULL AND COALESCE(cs.si_completed, false)=false` + `completion_status` LEFT JOIN. SI 화면 = "출고 대기"(SI 작업 시작됨 + 미출고) 기준 — SI_FINISHING completed 여부 무관, `si_completed=false`면 표시. VIEW SI 토글 기준과 일치. PI/QI 화면은 현행(진행중) 유지 — SI 만 출하 워크플로우 특수. **검증**: SQL 검증 SI 화면 7건(진행중 4 + 완료·출고대기 3: TEST-1114/GBWS-7094/GBWS-7095), Flask boot OK, PI/QI 회귀 0. **연관**: v2.17.1 (Sprint 68 OPS FE SI 출고 버튼) — 출고 완료 버튼 대상 제품 표시 정합 |
| v2.18.0 | 2026-05-19 | Sprint 69 — PI/QI 완료 권한 잠금 + admin 정상완료 (FEAT-PIQI-COMPLETE-OWNER-LOCK-20260519) | **BE 2 + FE 1 파일 minor release**. PI/QI = GST 사내 검사 공정 — cross-worker 완료(worker2가 worker1 task 완료)가 worker tracking·진행률을 왜곡 → ① PI/QI는 시작한 본인만 완료 ② 불가피 시 admin/manager 정상완료 endpoint ③ SI 화면 O/N·S/N 검색 칸. **변경**: (BE-1) `task_service.py complete_work()` — `task_category in ('PI','QI')` 이고 시작 worker ≠ 호출 worker 면 403 `FORBIDDEN`. SI/MECH/ELEC/TMS cross 현행 유지. (BE-2) `shipment_service.py admin_complete()` 신규 함수 + `routes/work_shipment.py` `POST /api/app/work/admin-complete` (`@manager_or_admin_required`) — PI/QI category 미완료 applicable task 전수 완료, task별 `completed_at` 검증(미래 차단 + started 이전 차단), 멀티작업자 orphan `work_completion_log` backfill, audit `close_reason='ADMIN_COMPLETE'`+`closed_by`+`force_closed=FALSE`(정상완료), 멱등(`already_completed`), `update_process_completion`. `_set_ship_audit`→`_set_close_audit(reason 파라미터화)` 리네임. (FE-A) `gst_products_screen.dart` — PI/QI 카드 admin/manager `[종료]` 버튼 + 종료 시각 다이얼로그(`showDatePicker`+`showTimePicker`, 미래 시각 차단) → admin-complete API. (FE-B) 상단 O/N·S/N 검색 칸 (`_searchQuery`+`_filteredProducts`, sales_order/serial_number 부분매칭, PI/QI/SI 3화면 공용). **검증**: pytest `test_admin_complete` 10/10 GREEN (TC-AC-01~10: cross 차단 PI/QI / admin-complete 성공 / partial·all-done 멱등 / completed_at 미래·started이전 차단 / 멀티작업자 backfill / **PI 위임 모델 DRAGON regression**). flutter build web GREEN. **Codex 라운드 1**: BE M=10/A=4 + OPS FE M=1(`_adminComplete` 미래 시각 차단)/A=3 반영 — A 3건(naive ISO8601 KST 환경 무관 / admin 버튼 status 무관 노출 의도 / `_fetchProducts` 초기 setState) 미반영 advisory. migration 불필요 (기존 테이블만 조회·UPDATE). 기존 complete/ship-complete 영향 0 (PI/QI 분기만 추가). **연관**: AXIS-VIEW Sprint 48 (PI/QI 종료 버튼 — VIEW 세션 담당) + v2.17.0 (Sprint 68 ship-complete — `admin_complete`는 동일 audit 패턴 재사용). 설계: `AGENT_TEAM_LAUNCH.md` § Sprint 69 |
| v2.18.1 | 2026-05-19 | Sprint 69 fix — 내 작업 완료 다이얼로그 공정명 하드코딩 | **FE only 1줄 patch release**. 사용자 catch — OPS PI/QI 화면 `[내 작업 완료]` 확인 다이얼로그가 `'본인의 SI 마무리공정 작업을 완료 처리하시겠습니까?'` 로 SI 문구 하드코딩 → PI/QI 에서도 동일 표시. **변경**: `gst_products_screen.dart` `_completeMyWork()` content `const Text('본인의 SI 마무리공정 작업을...')` → `Text('본인의 $_categoryLabel 작업을...')` (`_categoryLabel` = PI 가압검사 / QI 공정검사 / SI 마무리공정). **검증**: flutter build web GREEN. ②단계 자동 Codex 이관 체크리스트 0항목 → Opus 자가 리뷰. 회귀 위험 0. **연관**: v2.18.0 (Sprint 69) |
| v2.18.2 | 2026-05-19 | FIX-MECH-CHECKLIST-QR-DOC-ID-SINGLE-UNIFY-20260519 | **BE 1 + OPS FE 1 파일 patch release — DRAGON DUAL MECH 체크리스트 완료판정 P0 fix**. BACKLOG `BUG-MECH-CHECKLIST-DUAL-MODEL-QR-DOC-ID-MISMATCH-20260514` (🔴 P0) 해소. **버그**: DRAGON DUAL 모델 MECH 체크리스트가 영원히 100% 안 됨 → SELF_INSPECTION 공정 마감 finalize 차단 → gas2/util2 force close 불가. **Root Cause**: `checklist_record.qr_doc_id` 저장 컨벤션 혼재 — INLET 배관 S/N 8항목(scope_rule='DRAGON', INPUT)은 OPS FE 가 `DOC_{S/N}-L`/`-R` 분리 저장 / 나머지 MECH 항목은 `DOC_{S/N}` SINGLE 저장 → BE `check_mech_completion` DUAL 분기가 `[-L, -R]` loop 전수 매칭 요구 → SINGLE 저장 항목 영원히 mismatch → False. **사용자 결정**: 옵션 D 채택 (qr_doc_id `DOC_{S/N}` SINGLE 통일) — INLET L/R 구분은 master(item_name 'Left/Right #N' + 별도 master_id)가 담당하므로 접미사 불필요. 옵션 B(BE 3분리 SELECT)는 혼재 컨벤션 유지 반창고라 기각. **운영 데이터 검증 (2026-05-19 SQL)**: MECH `-L`/`-R` record = TEST-333(테스트 S/N) 16건뿐, 운영 0건 → migration 불필요. TM 카테고리 L 450/R 540 = dual tank 정상 → D 범위 제외. **변경**: (BE) `checklist_service.py check_mech_completion()` — DUAL 분기(model SELECT + is_dual + `-L`/`-R` loop) 제거 → `qr_doc_ids = [_normalize_qr_doc_id(serial_number)]` 단일. `check_tm_completion()` 미변경(TM dual tank). 읽기 경로 `get_mech_checklist`(L633) 이미 SINGLE → 변경 0. (OPS FE) `mech_checklist_screen.dart _qrDocIdForItem()` — `requiresLrHint` 로직 제거 → 항상 `_normalizeQrDocId(serialNumber)` SINGLE. (VIEW FE) 코드 변경 0 — VIEW 는 qr_doc_id 직접 미사용, BE 읽기 SINGLE 정합으로 자동 정상화. TEST-333 사용자 직접 초기화. **검증**: pytest 신규 `test_v2_18_2_mech_qr_doc_id_unify` 12 TC GREEN (SINGLE qr_doc_id / 부분미입력 False / DUAL 분기 제거 소스검증 / TM 분기 보존 / `check_mech_completion_all` Phase합산 / `check_category_close_eligible` close 게이트 — Codex M-Q1·M-Q5 호출자 전수 커버) + 회귀 `test_mech_checklist` 69 + `test_relay_first_final` 38 + `test_v2_15_16/18` 24 GREEN + flutter build web GREEN. **Codex 라운드 1**: M=2(Q1 호출자 5곳 전수 회귀 TC / Q5 게이트 경로 TC) + A=4(Q2 active_ids dry-run / Q3 FE hydrate / Q4 TM 분리 / Q6 `_is_report_dual_model` TM 전용 명칭 정비 — 별 sprint advisory) — M 2건 TC 보강으로 해소, Codex "코드 변경 방향 자체는 문제 없음" 확인. **회귀 위험 0** (운영 MECH `-L`/`-R` 0건 + TM 미변경 + ELEC 무관 + SINGLE 모델 동작 불변). **연관**: BACKLOG L354 P0 / Sprint 63-BE (INLET 8개 분리 도입 시점) / migration 불필요 |
| v2.18.3 | 2026-05-20 | SEC-CONFIG-DATABASE-URL-FALLBACK-REMOVED (GCP migration 준비) | **BE 1 파일 patch release**. GCP migration 중 catch — Cloud Run 첫 부팅 시 env `DATABASE_URL` 누락 → `config.py` 하드코딩 fallback (Railway DB URL with 평문 비밀번호) 사용 → 의도치 않게 Cloud Run 이 Railway DB 에 연결되던 사고 + GitHub 평문 비밀번호 노출. **변경**: `backend/app/config.py` `DATABASE_URL = os.getenv("DATABASE_URL", "")` + `RuntimeError` fail-fast. env 미설정 시 boot 즉시 실패. 테스트는 `conftest.py` 가 `TEST_DATABASE_URL → DATABASE_URL` 매핑. **검증**: pytest 7/7 GREEN, Cloud Run revision 00006-5sc 자동 배포 후 admin login → INVALID_PASSWORD 정상 (DB 정상 연결). Railway 영향 0 (Auto Deploys ON 복원 후에도 Railway env 에 DATABASE_URL 자동 설정돼 있음). **연관**: GCP migration 준비 + `GCP_MIGRATION_STANDBY.md` 신규 문서 |
| v2.18.24 | 2026-05-22 | ApprovalPendingScreen 승인 후 자동 홈 이동 (강제 새로고침 catch) | **FE 1 파일 patch release**. 사용자 catch: admin 승인 후 ApprovalPendingScreen 영역 화면 전환 안 됨 → PWA 강제 새로고침 필요. **변경**: `approval_pending_screen.dart` ref.listen(authProvider) 추가 — approval_status='approved' 변경 자동 감지 + Navigator.popUntil 자동 홈 / _handleRefresh(context, ref) manual check 안전망 이중 catch. 회귀 위험 0 |
| v2.18.23 | 2026-05-22 | 가입 승인 메일에 매뉴얼 URL 추가 | **BE 1 파일 patch release**. notification_service.py HTML 템플릿 영역 📖 사용 매뉴얼 박스 추가 (axis-manual.netlify.app). 회귀 위험 0 |
| v2.18.22 | 2026-05-22 | 가입 승인 메일 URL 정정 + 로그인 방법 안내 박스 추가 | **BE 1 파일 patch release**. 사용자 catch: ① URL 잘못 안내됨 (g-view.netlify.app → gaxis-ops.netlify.app) ② 가입 완료 안내 메일에도 로그인 방법 작성. **변경**: notification_service.py "앱 열기" 링크 도메인 변경 + 본문 회색 박스 (🔑 로그인 방법 3가지 + PIN 설정 위치) |
| v2.18.21 | 2026-05-22 | 안내 메일 도메인 변경 + login 안내 박스 + PIN 설정 위치 명시 | **BE 1 + FE 1 파일 patch release**. 사용자 catch 3가지: 가입 승인 메일 도메인 미완 / login 안내 미인지 / PIN 설정 안내 누락. **변경**: notification_service.py "앱 열기" 링크 변경 (gaxis-ops.co.kr → g-view.netlify.app, v2.18.22 영역 재정정) + login_screen.dart 안내 박스 (mist 배경 + 🔑 + PIN 위치 안내) |
| v2.18.20 | 2026-05-22 | 승인 메일 + prefix 확장 + 안내 3가지 (Codex 라운드 1 M=3 반영) | **BE 4 + FE 2 + 신규 1 + pytest 1**. 사용자 catch 통합: ① 가입 승인 시 환영 메일 발송 ② prefix 로그인 일반 사용자 확장 (admin/test → 모든 사용자, ALLOWED_DOMAINS 3개 후보) ③ register SnackBar + login 안내 3가지 (이메일/prefix/PIN, 이름 코드 유지/안내 제외). **변경**: notification_service.py 신규(`send_approval_notification` + `send_approval_notification_async` thread 캡슐화) / worker.py `get_worker_by_email_prefix` 신규 / auth_service.py login chain 4-tier (admin→user prefix→이름→이메일) / admin.py 1줄 호출만 (Codex M-Q4 admin.py God File 정책 정합). **Codex 라운드 1**: M=3 반영 (HTML escape XSS / admin.py thread 캡슐화 / pytest 신규 4 TestClass) + A=3 BACKLOG 권고 (ALLOWED_DOMAINS 4중 중복 / 모호 매칭 안내 / daemon thread outbox) + N=2 안전. **신규 BACKLOG**: REFACTOR-ADMIN-SPLIT 🔴 HIGH + FEAT-LOGIN-AMBIGUOUS-PREFIX-NOTICE / REFACTOR-EMAIL-DOMAIN-CONSTANT / FEAT-APPROVAL-EMAIL-OUTBOX 🟡 LOW |
| v2.18.19 | 2026-05-22 | verify_email 카운트다운 3분 → 1분 (BE rate limit 60s 동기화) | **FE 1 파일 patch release**. 사용자 catch: 가입 인증 화면 재발송 대기 시간 3분 김. BE rate limit 이미 60초 / FE 카운트다운만 180초 비동기. **변경**: `verify_email_screen.dart` L32 + L50 `_remainingSeconds = 180` → `60` (2곳). **이미 구현 항목 catch**: login `EMAIL_NOT_VERIFIED` → verify_email 자동 redirect + prefill (L55-62) + resend 버튼 (L434+) + api_service 403 에러 코드 보존 (L249-252). **사용자 (kdkyu311) catch 분석**: 가입 → 인증 안 함 → 비밀번호 찾기 우회 (비밀번호만 변경, email_verified 그대로 false) → 사용자 인식 catch + 운영 SQL 정리 필요 (`UPDATE workers SET email_verified=true, approval_status='approved' WHERE email='kdkyu311@naver.com'`). **후속 BACKLOG 권고**: `FEAT-LOGIN-RESEND-VERIFICATION-LINK` — login 화면에 "이메일 인증 다시 받기" 명시 링크 추가 |
| v2.18.18 | 2026-05-22 | 인증 메일 도메인 안내 + whitelist 검증 (BE + FE) | **BE 1 + FE 2 파일 patch release**. 사용자 catch: 카카오/다음 가입 시 인증 메일 미수신 / Railway 로그 `Connection unexpectedly closed` = KT Biz Office SMTP 외부 도메인 차단. CLAUDE.md L626 명시된 허용 도메인 영역 코드 미구현 catch — whitelist 강제 + UI 안내 동시 추가. **변경**: (BE) `auth_service.py` `ALLOWED_EMAIL_DOMAINS = {'gst-in.com', 'naver.com', 'gmail.com'}` + `register()` 도메인 체크 (INVALID_EMAIL_FORMAT / EMAIL_DOMAIN_NOT_ALLOWED) (FE) `validators.dart` `allowedEmailDomains` + `validateEmail()` 도메인 체크 + `register_screen.dart` 이메일 필드 아래 안내 메시지. **동작**: gst-in/naver/gmail 통과 / kakao/daum/hanmail/nate 등 차단 (FE + BE 양쪽). **Sentry**: SMTP Recipients refused / Connection unexpectedly closed 잡음 0건 기대. **BACKLOG 후속**: 외부 SMTP 전환 (Gmail/SendGrid) + admin_settings 영역 동적 도메인 관리 검토 |
| v2.18.17 | 2026-05-22 | Sentry 잡음 2건 fix (WebSocket Broken pipe + SMTP Recipients refused) | **BE 3 파일 + FE version bump patch release**. 사용자 catch: Sentry ERROR 정상 동작 2건 잡힘. v2.10.13 패턴 정합 (FIX-WEBSOCKET-STOPITERATION-SENTRY-NOISE). **변경**: (1) `events.py` L183 `except Exception` → `(BrokenPipeError, ConnectionResetError, ConnectionAbortedError)` 분기 + logger.info 강등 / 기타 Exception logger.error + exc_info=True (2) `email_service.py` + `auth_service.py` (2곳) `SMTPRecipientsRefused` 분기 → logger.warning 강등 (잘못된 admin 이메일 거부 = 550 Unknown user). **Sentry**: Broken pipe / Recipients refused → 미발송 / 진짜 ERROR → 그대로 발송 + stack trace. **운영 catch**: `workers.email WHERE is_admin=true` 잘못된 이메일 점검 부탁 (KT Biz Office SMTP 외부 도메인 거부 또는 퇴사자 잔존 가능성). +~15 LOC |
| v2.18.16 | 2026-05-21 | BUG-42 fix: zoom 2.0x 자동 적용 (videoConstraints 우회) | **FE 1 파일 patch release**. qr-test.html 사용자 검증 catch: videoConstraints 사용 시 ZXing 디코더 방해 → 인식 NG. `applyConstraints({advanced:[{zoom}]})` 만 사용 (videoConstraints 우회) 시 디코더 정상 + 명판 확대 동시 달성. 사용자 옵션 B 결정 (qrbox 200 현행 유지 + zoom 2.0x). **변경**: `qr_scanner_web.dart` `_applyZoomIfSupported(num targetZoom)` helper 신규 (+47 LOC) + 3곳 (env/user/cameraId) start 성공 후 fire-and-forget 호출 (200ms delay 후, +3 LOC). `getCapabilities().zoom` 확인 + min/max clamp + silent skip. **변경 안 한 부분**: videoConstraints (디코더 방해 회피), cameraIdOrConfig (v2.18.4 baseline), qrbox 200, DOM/CSS/MutationObserver 절대 불변. **누적 trail**: 13번 시도 후 도달 (v2.18.5~v2.18.11 셀카 → v2.18.12 1차 ROLLBACK → v2.18.13/14 인식 NG → v2.18.15 2차 ROLLBACK + qr-test.html → v2.18.16 최종 fix). **LOC**: 506 → 557 (🟡 경고 유지). 실기기 QA 사용자 위탁 |
| v2.18.15 | 2026-05-21 | ROLLBACK 2차 — v2.18.13/14 fallback chain 회귀, v2.18.4 baseline 복귀 | **FE 1 파일 patch release**. v2.18.13 (4-tier) + v2.18.14 (3-tier) 시도 후 실기기 catch: 1차 tier (해상도 1920×1080 + facingMode environment) QR 인식 NG (코너 초록색 변화 없음). 운영 코드 1차 시도 영역 fallback chain 자동 회귀 안 됨 — 디코더 인식 실패는 OverconstrainedError 아니어서 fallback trigger 안 됨. **변경**: `git checkout 8a2233f -- qr_scanner_web.dart` v2.18.4 baseline 복귀 (506 LOC, 단순 facingMode hint). **누적 trail**: v2.18.5~v2.18.11 (11번 hotfix → 셀카 catch) → v2.18.12 1차 ROLLBACK → qr-test.html + Codex 라운드 1+2 (root cause 확정 + 4-tier 권고) → v2.18.13/14 (fallback chain) → 실기기 인식 NG → v2.18.15 2차 ROLLBACK. **BACKLOG**: BUG-42 🔴 OPEN + 7개 별 sprint 보존 (TASK3-AUTO-ZOOM / CAMERA-SWITCH-BUTTON / REFACTOR-FUNCTION-SPLIT / TEST-QR-LIB-CONSTRAINT-PREFLIGHT / TOOL-ERUDA-DEV-CONSOLE / QR-SCANNER-RETRY-CLEANUP / QR-SCANNER-ERROR-CLASSIFICATION). **재시도 조건**: 실기기 디버깅 환경 (Mac 원격 + Eruda) 갖춘 후 minimal change 단위 단계별 검증 + 1차 시도 영역 인식 실패도 fallback trigger 하도록 설계 변경 |
| v2.18.14 | 2026-05-21 | focusMode advanced 제거 (ROLLED BACK in v2.18.15) | 3-tier chain 영역 1차에서 advanced focusMode 제거. 해상도 1920 유지. 실기기 catch: 1차 인식 NG 잔존. v2.18.15 ROLLBACK |
| v2.18.13 | 2026-05-21 | BUG-42 재시도 (4-tier fallback chain, Codex 라운드 1+2 합의, ROLLED BACK in v2.18.15) | **FE 1 파일 patch release**. v2.18.12 ROLLBACK + qr-test.html 검증 + Codex 라운드 1 (M=4/A=2/N=1) + 라운드 2 (M=0/A=5/N=3, DEPLOY_SAFE:CONDITIONAL) 합의 후 운영 적용. **변경**: `qr_scanner_web.dart` `_buildFallbackTiers()` helper 신규 (+58 LOC) + `startQrScanner()` 1차 시도 영역 4-tier chain (+17 LOC). 기존 user/cameraId fallback 그대로 유지. **4-tier**: 1차 full (facingMode+width+height+advanced focusMode) → 2차 advanced 제거 → 3차 해상도 제거 → 4차 baseline. **Root Cause**: html5-qrcode 2.3.8 source `areVideoConstraintsEnabled ? internalConfig.videoConstraints : createVideoConstraints(cameraIdOrConfig)` 영역 videoConstraints 키 존재 시 cameraIdOrConfig.facingMode 무시 → videoConstraints 안에 facingMode 명시 필수. **사용자 실기기 검증 (iPhone 14/15 Pro)**: qr-test.html 4-tier 시뮬레이션 4 시나리오 모두 GREEN. **신규 BACKLOG 2**: QR-SCANNER-RETRY-CLEANUP (Codex A-Q2/Q3) + QR-SCANNER-ERROR-CLASSIFICATION (A-Q8). **격상**: REFACTOR-QR-SCANNER-WEB-FUNCTION-SPLIT LOW → MEDIUM (A-Q7). **TEST-QR-LIB-CONSTRAINT-PREFLIGHT** 영역 QA 8항목 evidence 추가. **LOC**: 506 → 569 (🟡 경고 유지) / startQrScanner 158 → 175 (🔴 한도 초과 유지). **실기기 QA 8항목 사용자 위탁** |
| v2.18.12 | 2026-05-21 | ROLLBACK qr_scanner_web.dart v2.18.4 상태로 복귀 + Codex 라운드 1 root cause 확정 | **FE 1 파일 patch release + 테스트 페이지 + Codex 검증**. v2.18.5~v2.18.11 (11번 BUG-42 hotfix 시리즈) 모두 롤백. 실기기 catch: 콘솔 로그 후면 표시 + 실제 화면 셀카 = 라이브러리 충돌. **ROLLBACK**: `git checkout 8a2233f -- qr_scanner_web.dart` 506 LOC 단순 hint. **테스트 페이지**: `frontend/web/qr-test.html` 신규 — 운영 1:1 복제 + 옵션 토글 7개. **사용자 실기기 검증 매트릭스** (iPhone 14/15 Pro): ① 옵션 1(width/height) 또는 옵션 2(focusMode) 단독 ON → 셀카 ② **패턴 A (videoConstraints 안에 facingMode:'environment' 명시)** 단독 또는 조합 → 후면. **Root Cause 확정** (Codex 라운드 1 M-Q1): html5-qrcode 2.3.8 source — `areVideoConstraintsEnabled ? internalConfig.videoConstraints : createVideoConstraints(cameraIdOrConfig)` 영역 `videoConstraints` 키 존재 시 cameraIdOrConfig.facingMode 무시. **Codex 라운드 1 권고** (M=4/A=2/N=1): Q2 4단계 fallback chain 필수 / Q4 실기기 QA 8항목 / Q5 `TEST-QR-LIB-CONSTRAINT-PREFLIGHT` BACKLOG 등록 / Q6 `TOOL-ERUDA-DEV-CONSOLE` BACKLOG 등록. **BACKLOG**: BUG-42 🔴 OPEN reopen + 5개 별 sprint (TASK3-AUTO-ZOOM / CAMERA-SWITCH-BUTTON / REFACTOR-FUNCTION-SPLIT / TEST-QR-LIB-CONSTRAINT-PREFLIGHT / TOOL-ERUDA-DEV-CONSOLE). **v2.18.13 재시도 준비 완료** — 4단계 fallback chain + 실기기 QA 체크리스트 |
| v2.18.11 | 2026-05-21 | HOTFIX-14 권한 발급 시점에 후면 카메라 명시 (롤백됨) | **FE 1 파일 patch release**. iPhone Safari `cameras=1` catch — `_requestCameraPermission()` 영역 `{video:{facingMode:'environment'}}` 1차 권한 발급 → enumerate 후면 노출 유도. v2.18.12 에서 롤백 |
| v2.18.10 | 2026-05-21 | HOTFIX-13 getUserMedia exact + facingMode 검증 (롤백됨) | **FE 1 파일 patch release**. `{facingMode:{exact:'environment'}}` 강제 + `settings.facingMode` 검증. v2.18.12 에서 롤백 |
| v2.18.9 | 2026-05-21 | HOTFIX-12 getUserMedia 직접 호출 0차 시도 (롤백됨) | **FE 1 파일 patch release**. `getUserMedia({video:{facingMode:'environment'}})` 직접 → settings.deviceId 추출. v2.18.12 에서 롤백 |
| v2.18.8 | 2026-05-21 | HOTFIX-11 cameras label 매칭 1차 승격 (롤백됨) | **FE 1 파일 patch release**. `_findBackCameraId()` helper + 1차 시도 영역 승격. v2.18.12 에서 롤백 |
| v2.18.7 | 2026-05-21 | HOTFIX-10 후면 카메라 강제 (셀카 fallback 차단, 롤백됨) | **FE 1 파일 patch release**. 사용자 catch (v2.18.6 직후): "카메라 방향이 셀카인데 전환 버튼 돌려달라" — 모바일에서 1차 `facingMode:'environment'` 가 hint 일 뿐이라 iOS Safari 등 OS 가 무시 → user 카메라 silent fallback → 셀카. **변경**: `qr_scanner_web.dart` — (1) `_buildScannerConstraints()` `environment` → `{exact:'environment'}` 강제 / `user` 영역은 hint 유지 (2) 3차 fallback 영역 카메라 list 'back'/'rear'/'environment'/'후면' label 매칭 안전망 추가 (~13 LOC). **동작**: 모바일 후면 강제 / 데스크톱 1차 exact fail → user 자동 fallback / 3차 label 매칭 안전망. **절대 불변 영역 침범 0** (프레임/뷰파인더/qrbox/CSS/DOM, qr_scan_screen.dart UI 무변경). **검증**: flutter build web GREEN (12.6s) + 실기기 manual QA 재위탁. **LOC**: 533 → 551 (+18, 🟡 경고 유지). **별 sprint**: `BUG-42-CAMERA-SWITCH-BUTTON-DEFERRED` BACKLOG 등록 — 명시적 전환 버튼 UI 는 qr_scan_screen.dart 절대 불변 영역 해소 필요 |
| v2.18.6 | 2026-05-21 | HOTFIX-09 cameraIdOrConfig 1-key 위반 fix | **FE 1 파일 patch release**. v2.18.5 배포 직후 사용자 실기기 catch (5분 이내): `'cameraIdOrConfig' object should have exactly 1 key, found 4 keys`. html5-qrcode@2.3.8 `start(cameraIdOrConfig, config, ...)` 1번째 인자는 1 key 객체만 허용. v2.18.5 helper 가 4 keys 반환 → 3 시도 모두 reject → "사용 가능한 카메라를 찾을 수 없습니다". **변경**: `qr_scanner_web.dart` — `_buildScannerConstraints()` 1 key 객체만 반환하도록 단순화(width/height/advanced 제거) + `__qrScanConfig` JS 객체에 `videoConstraints:{width:{ideal:1920},height:{ideal:1080},advanced:[{focusMode:'continuous'}]}` 영역 신규(Html5QrcodeCameraScanConfig 공식 spec 위치). **Codex 라운드 1 (v2.18.5) 놓친 catch**: html5-qrcode spec 영역 1-key 제약 미확인 — 향후 외부 라이브러리 spec 명시 검토 절차 권고. **검증**: flutter build web GREEN (12.7s) + 실기기 manual QA 재위탁. **LOC**: 530 → 533 (+3, 🟡 경고 유지). 해상도/포커스 의도 동일 (위치만 이동) + 프레임 절대 불변 |
| v2.18.5 | 2026-05-21 | HOTFIX BUG-42 명판 소형 QR 인식률 개선 (Task 2) | **FE 1 파일 patch release**. 사용자 운영 catch (5-21): "자동 포커싱이 안 되는 거 같다" — OPS PWA 스캐너 html5-qrcode@2.3.8 가 제품 명판 소형 QR 미인식 (iOS/Android 기본 카메라 앱은 정상). **변경**: `frontend/lib/services/qr_scanner_web.dart` — `_buildScannerConstraints({facingMode, cameraId})` helper 신규 (+18 LOC, DRY 정합) + L424(env) / L443(user) / L466(cameraId fallback) 3곳 호출 통일. `width:{ideal:1920}, height:{ideal:1080}, advanced:[{focusMode:'continuous'}]` + cameraId 영역 `{deviceId:{exact:cameraId}}` 변환. **Codex 라운드 1 trail (M=4)**: Q1 옵션 C' (Task 2 우선) — Task 1 의 `experimentalFeatures` 가 잘못된 config 객체에 위치(`Html5QrcodeCameraScanConfig` vs `Html5QrcodeFullConfig`) + 2.3.8 default 이미 true = no-op skip / Q2 cameraId fallback `{deviceId:{exact:...}}` 통일 / Q3 iOS Safari advanced unknown constraint 자동 무시 → 안전 폴백 / Q4 Task 3 자동 줌 BACKLOG 이관 (스티커 QR 역효과 + UI 불변 충돌) / Q5 실기기 manual QA 필수 (flutter_test 자동화 불가) / Q6 절대 불변 영역 침범 0 / Q7 FE only 1파일 자동 이관 불필요. **LOC**: 506 → 530 (🟡 경고 영역 유지, +24 helper 분리) / `startQrScanner()` 158줄 변화 0 (호출 1줄 동일) → `REFACTOR-QR-SCANNER-WEB-FUNCTION-SPLIT` BACKLOG 등록. **검증**: flutter build web --release GREEN (12.6s) + 실기기 manual QA 위탁. **회귀 위험 0** (프레임/뷰파인더/qrbox:200/CSS/DOM/MutationObserver 절대 불변, 디코더 옵션 + 카메라 OS 레벨 setting 만 변경). **연관**: BACKLOG BUG-42 L302 close (Task 2) + `BUG-42-TASK3-AUTO-ZOOM-DEFERRED` 신규 + `REFACTOR-QR-SCANNER-WEB-FUNCTION-SPLIT` 신규 |
| v2.18.4 | 2026-05-21 | #70 출하 KPI `best` 분기 엑셀 게이트 제거 (app-only 출하 합집합) | **BE 1 파일 patch release**. AXIS-VIEW OPS_API_REQUESTS.md #70 — SI 공정 5-19 시행 후 app SI 데이터 유입 시작 → `best` 토글 엑셀 게이트(`WHERE actual_ship_date IS NOT NULL`) 가 app-only 출하 누락 → 합집합(OR) 으로 정정. **변경**: `factory.py _count_shipped()` basis='best' 분기 WHERE 절 1줄 — `p.actual_ship_date IS NOT NULL` 단독 → `(p.actual_ship_date IS NOT NULL OR t.completed_at IS NOT NULL)`. `COUNT(DISTINCT p.serial_number)` 자동 중복 제거 + `COALESCE(DATE(t.completed_at), p.actual_ship_date)` app 우선 날짜 귀속. **검증**: pytest `TestFactoryKpiV24Amendment` #70 TC 2개 신규 GREEN. 응답값 즉시 변경 0 (현재 갭 0건), 미래 SI 정착 후 app-only 자동 정확 카운트. **연관**: 출하이력 페이지(FEAT-SHIPMENT-HISTORY-PAGE) 6월 초 예정 선행 의존성 해소 |
| v2.28.2 | 2026-06-07 | active-time 식사시간만 제외 정정 (오전/오후 휴게 = 작업시간) | **BE only patch — task_detail.py 1 + migration 060 재백필, man-hour 불변**. 사용자 catch: Sprint 86(v2.28.0)이 4개 휴게(오전 10:00-10:20/점심 11:20-12:20/오후 15:00-15:20/저녁 17:00-18:00) 전부 제외했으나 **오전·오후 20분 휴게는 작업시간 인정** = **식사(점심·저녁)만 제외**. `compute_task_work` breaks_day = `[11:20-12:20, 17:00-18:00]` 만 + `migrations/060` active_time 전체 재백필(OVERWRITE, IS NULL 가드 없음, duration 불간섭). 일 제외 160→120분, active 상승(PANEL 6.1→6.7h, man 8.9h, active≤man 유지). pytest active 12 GREEN(AT-03 320→360/AT-04 220→240/AT-15 280→300). 배포 시 migration 060 자동 재백필. 설계: AGENT_TEAM_LAUNCH § Sprint 86. |
| v2.28.1 | 2026-06-07 | CT task-stats dual 파라미터 (DUAL/단일 분리, VIEW #81) | **BE only patch — statistics_service+ct_analysis 2파일, DB/migration 0**. CT ②(IQR)가 DUAL/단일 합산 → 작업시간 2배 차(PANEL 단일 5.6h vs DUAL 11.8h) 표준 왜곡. `GET /api/ct/task-stats?dual=dual\|single`(미지정=합산 하위호환) 추가. `_dual_clause()` = `p.model ILIKE '%DUAL%'`(dual)/`NOT ILIKE '%DUAL%'`(single) — **접미사 대신 포함**(iVAS GAIA-I DUAL PUMP RACK 3CH 8행 등 중간 DUAL 명 정확, 요청안 %DUAL 보강). meta dual_scope 추가, 스키마 불변(VIEW v1.59.x 선반영). 운영 PANEL 단일 man 5.6h/active 4.0h vs DUAL 11.8h/7.4h. pytest CT-16(dual)+CT-14 GREEN. 연계 active-time(VIEW #81 2번째)=v2.28.0 완료. 설계: OPS_API_REQUESTS #81. |
| v2.28.0 | 2026-06-07 | Sprint 86 순수 작업시간 active-time + CT 표준 격상 (FEAT-ACTIVE-TIME-PURE-WORK) | **BE only minor — additive 컬럼 + 산출 함수, man-hour 불변**. man-hour(현 CT 표준)는 세션−수동pause라 휴게(160분/일)·영업시간 밖 idle 미차감 → 주말/도킹 task 부풀음. **active-time = Σ_w FLOOR(GREATEST(0, len(session∩영업창) − len((수동pause ∪ 휴게)∩session∩영업창)))** = 순수 작업시간. **영업창** = attendance[MIN(in),MAX(out)] 우선(운영 86%) / fallback 평일[08,20]·주말[08,17] KST(GST 검사 자동 흡수). **휴게** = admin 표준 시간표 [10:00-10:20,11:20-12:20,15:00-15:20,17:00-18:00]. 저장 `LEAST(active, duration_minutes)` → active ≤ man-hour. **신규**: `task_detail.py compute_task_work()`(man-hour+active 단일 CTE, PG16 multirange) + 기존 `compute_task_manhour` .manhour 위임 / `migrations/059_add_active_time.sql`(컬럼+백필, 058=v2.22.0 예약 회피) / 완료 4경로 active 동봉(complete_task_unified·auto_close_relay_task·force_close_task·force_complete_task=Codex R6 raw-elapsed→man-hour 정합) / `statistics_service.py` active_*_hours 별 필드 + meta standard_basis/active_available/active_basis_note. **포렌식**: total_pause_minutes 컬럼만 깨짐(작업자별 += SUM 이중합산 id=87480=3790+3785) — duration·CT 영향 0. man-hour(duration_minutes) 불변(additive). **Codex 6라운드**: 설계 R1~R4 NO-GO → R5 GO / 구현 R6 NO-GO(M-1 force_complete 우회 / M-2 active_available Tukey비율) → 해소. **검증**: 운영 SQL man-hour=배포 일치(238673 둘다 1071)+active≤man-hour 위반0, 백필 set-based=per-task 일치(87480→265), active 중앙 PANEL 8.9→6.1h. pytest active 12(AT-01~16)+회귀 relay 38·CT 15·duration/v2.15.16/hotfix04 GREEN(man-hour 위임 mock 4건 갱신). 회귀 0. 후속 BACKLOG REBACKFILL-ACTIVE-TIME-ON-SETTINGS-CHANGE. VIEW FE 후속(별 세션): active 우선 표시. 설계: AGENT_TEAM_LAUNCH.md § Sprint 86. |
| v2.27.0 | 2026-06-05 | Sprint 85 CT 분석 허브 BE 연동 MVP (FEAT-CT-ANALYSIS-HUB-BE-MVP) | **BE only minor — 신규 2파일 + blueprint 1줄, DB·migration 0 read-time**. VIEW CT 분석 페이지(13 컴포넌트 4섹션) mock → 실데이터 연동 MVP = **①데이터신뢰도 + ②CT표준(IQR, man-hour)** 만 (③ M/H·병렬·협력사 = 관리자 preview skeleton / ④ M/M·APS = 미구현). 결정 동결 CT_ANALYSIS_ROADMAP §15. **신규**: `statistics_service.py`(`get_task_ct_stats` ② + `get_data_quality` ①) + `routes/ct_analysis.py`(`GET /api/ct/task-stats?period=last_90d&model=&category=` + `GET /api/ct/data-quality`, `@jwt_required+@gst_or_admin_required` = admin OR GST manager). **핵심 정합**: box plot = `percentile_cont(duration_minutes/60)` = v2.22.0 interval-union man-hour SSoT (목업 `mean×인원` 이중계산 폐기). clean = `duration_source IS NULL OR 'NORMAL_COMPLETION'` only + TMS(M)(TANK_MODULE/PRESSURE_TEST)·TEST 제외 + Tukey 1-pass(raw fence→fence 내 재집계, min/max 실측). 카테고리 Σmedian 폐기(DUAL 중복/모델변동) → pooled_median + median_basis meta. confidence high(n≥100)/medium(≥30)/low. KST: 자동마감추이/교육 cut `AT TIME ZONE 'Asia/Seoul'`(training cut '2026-06-02' literal), post n<30 → insufficient_sample. meta: as_of/lookback/model_distribution/excluded_by_source/excluded_pct/confidence_scope/low_sample_warning. TTL 캐시 1h. **Codex 3라운드**: 설계 R1 NO-GO(M=5: ATTENDANCE_OUT/카테고리Σ/KST/period) → R2 GO(M=0/A=2) → 구현 R3 **DEPLOY_SAFE/GO(M=0/A=4)**. A 처리: 추이 6mo 고정 주석 + AUTO_CLOSED LIKE drift BACKLOG. **검증**: pytest 15/15 GREEN(CT-01~15 seed 기반) + 회귀 test_factory 21. 운영 스모크 ② 17 task(§14.2 일치, TMS 제외) / ① 판넬 교육 전 18.9h→후 7.0h / excluded_pct 17.7%. 기존 service/DB/migration touch 0 회귀 0. **VIEW FE 후속**(별 세션): mock→API + MVP 제외 컬럼(man_hours/기준대비) 숨김 + ③ skeleton + ④ 보류. 설계: AGENT_TEAM_LAUNCH.md § Sprint 85. |
| v2.26.0 | 2026-06-05 | Sprint 84 생산현황 상세 1차/2차 마일스톤 (FEAT-FACTORY-PHASE-1-2-PROGRESS) | **BE only minor (factory.py 단일 파일, read-time, DB/migration 0)**. 생산현황 상세 진행률을 손님용 rollup + **1차(가압 PI까지)/2차(마무리 SI) 마일스톤** 그룹핑. monthly-detail 응답에 `phase` 필드 additive. Sprint 83 `_compute_stage_completion` 재사용. **1차** = 전장외부→반제품(TM)→기구(MECH)→전장(ELEC)→가압(PI), 1차완료=`pi` / **2차** = 공정(QI)→마무리(SI), 2차완료=`si`(SI_FINISHING 기준). ⚠️ QI app 미입력(검사자동화시스템 별 시스템, 추후 API) → 2차 진행률 **SI binary**, QI 연동 시 키 1개 추가로 자동 확장. **신규 helper** `_phase_pct(stages,keys)`(None 제외 비율) + `_build_phase(sc)`(p1_done/p2_done/p1_pct/p2_pct/status). `_compute_stage_completion` 0-applicable stage → `None` 일반화(기존 is_gaia tm 특수분기 제거) — non-standard 모델 분모 정확. 응답: `"phase":{p1_done,p2_done,p1_pct,p2_pct,status}`. **Codex 라운드 1 NO-GO(M=2) → 라운드 2 GO(M=0/A=1)**: M-2(p2_pct SI_SHIPMENT-only 50% 오염)→`_PHASE2_KEYS=['si']` binary / M-3(non-standard absent stage False 분모 왜곡)→present_map None / A-1(QI 연동 시 SI reached를 SI_FINISHING 기준 제한 별 sprint)→BACKLOG. pytest 39 GREEN (sprint83 11 + sprint84 8 PH-01~06+PH-04b+PH-05 + test_factory 19 회귀 0). 운영 W23 by_stage 불변(mech 88.2/elec 82.4/tm 100/pi 79.4/qi 64.7/si 64.7), phase 분포 34건(2차완료 22/2차진행중 5/1차진행중 7). additive 2필드+helper 2개, 기존 필드/엔드포인트 무변경 회귀 0. VIEW: progress_pct(rollup) 큰 바 + phase 마커/뱃지 렌더(별 세션). 설계: AGENT_TEAM_LAUNCH.md § Sprint 84. |
| v2.25.1 | 2026-06-05 | Sprint 83 공정 순서 정정 (반제품 선행) | **BE only patch (factory.py 1줄)**. v2.25.0 cascade tier 순서 정정. 사용자 catch "반제품은 다 끝났어야 정상" — 반제품(TM)을 기구/전장과 병렬(tier 0)로 뒀으나 실제 순서는 **전장외부→반제품(TM)→기구(MECH)→전장(ELEC)→가압(PI)→공정(QI)→마무리(SI)** 로 반제품이 기구/전장보다 선행. `_STAGE_TIER` = `{tm:0,mech:1,elec:2,pi:3,qi:4,si:5}` (기존 `{mech:0,elec:0,tm:0,pi:1,qi:2,si:3}` 병렬→순차). 효과: 후속 공정 도달 시 반제품 강제 100% (운영 W23 tm 83.9→100.0, mech 82.4→88.2). pytest test_sprint83 11 GREEN (CR-11 신규: 기구 도달→반제품 강제 100%) + 회귀 test_factory 21. 응답 스키마 불변/read-time/회귀 0. |
| v2.25.0 | 2026-06-05 | Sprint 83 공장 대시보드 공정별 완료율 정합 (FEAT-FACTORY-COMPLETION-ROLLUP) | **BE only minor (factory.py 단일 파일, read-time, DB/migration 0)**. 공정별 완료율이 `completion_status` 옛 플래그(lag)를 봐 저평가 — TM 19 vs 플래그 3 / 출하완료 12건 상위 플래그 통째 누락 / SI=SI_FINISHING+SI_SHIPMENT 둘 다 요구로 마무리완료분 누락. **해법(옵션 B 체크리스트 무관 cascade)**: 신규 `_compute_stage_completion` — 실제 task 완료 + 도달한 가장 뒤 tier보다 앞 공정 강제 100% + SI=SI_FINISHING 기준 + TM=GAIA만 + DUAL L+R 둘 다. `_progress_from_stages`(=구 `_calc_progress`). 적용=get_weekly_kpi by_stage/completion_rate + get_monthly_detail per-item. `_get_task_progress_by_serial`(생산현황 백킹) 무수정 별도 helper(A-5). 토글 미채택(글로벌=per-user 불가). **대시보드=보여주기만, 생산현황/실적/상세 무변경**. 운영 W23: mech 0→82.4 / tm 10→83.9 / GBWS-7163 100%. Codex R1 GO(M=0/A=3 반영). pytest test_sprint83 10 GREEN(CR-01~10) + 회귀 test_factory 21. 응답 스키마 불변(값 상승)/회귀 0. 후속 BACKLOG FEAT-FACTORY-ACTUAL-COMPLETION-VIEW(실제값 표시 위치). 설계: AGENT_TEAM_LAUNCH.md § Sprint 83. |
| v2.24.1 | 2026-06-04 | auto-close-details quarter period 지원 (#80 후속) | **BE only 1줄 patch**. VIEW catch: 강제 종료 분포도 분기 매트릭스(force 130/55건) ↔ 상세 패널 불일치. 원인: details period 화이트리스트가 summary 와 비대칭 — `_VALID_PERIODS_SUMMARY={today,week,month,quarter}` vs `_VALID_PERIODS_DETAILS={today,week,month}` → `period=quarter` 상세 조회 400 INVALID_PERIOD → VIEW 가 month 다운그레이드 → 6월 BAT 거의 0. 서비스 `_resolve_period_range` 는 quarter 이미 완전 지원 → **라우트 화이트리스트 1곳만 막던 것**(데이터/로직 문제 0). **Fix**: `admin_dashboard.py _VALID_PERIODS_DETAILS` 에 `"quarter"` 추가(summary 통일). pytest CT-11 신규(quarter+force+per_page=500 → 200) + 기존 12 GREEN. 응답 스키마·DB·migration 0, 회귀 0(화이트리스트 확장만). **VIEW 후속**(별 repo): `detailsPeriod` 다운그레이드 제거. ②단계 자동 Codex 이관 0항목 → Opus 자가 리뷰. |
| v2.24.0 | 2026-06-04 | Sprint 82 (#80) auto-close-details close_type/task_id 필터 | **BE only minor (dashboard_service.py + admin_dashboard.py, 응답 스키마 0 변경)**. VIEW 강제 종료 상세 패널이 union-50 client-filter 대신 "특정 협력사 force 전수" 서버 조회. **신규 요청 파라미터(additive)**: `close_type`(auto/manual/force, 미지정=현행 union 하위호환) + `task_id`(마감 `t.task_id`, 기존 trigger_task_id 와 별 컬럼). **BE**: `build_auto_close_details` close_filter close_type 분기 + task_sql + **per_page cap 100→500**(운영 Q2 force 125건 이미 초과 → 전수 보장) / 라우트 close_type 화이트리스트 400 + empty→None + 대소문자 정규화. **Catch**: per_page=200 이 cap 100 silent clamp 였음 → cap 상향 필수 / task_id ≠ trigger_task_id(트리거 task vs 마감 공정). **Codex R1 DEPLOY_SAFE (M=0/A=4 전건 반영)** — A5 manager 미시작 force 제외 = Sprint 81 격리 정책 정합(협력사 매니저 = 자기 회사 worker 시작 force 만, admin/GST = 전수). pytest test_sprint82 12 GREEN(CT-01~10) + 회귀 test_sprint71 영향 0. 응답 스키마 불변(VIEW 타입 0) / DB·migration 0 / summary·매트릭스·invariant 무변경 → 회귀 0. **VIEW 후속**(별 repo): force 셀 선택 시 close_type='force' 별 호출 → 전수 보장. 설계: AGENT_TEAM_LAUNCH.md § Sprint 82 (#80). |
| v2.23.0 | 2026-06-04 | Sprint 81 (#79) 강제 종료 협력사 2축 매트릭스 | **BE only minor (dashboard_service.py 단일 파일, OPS 앱 변경 0)**. 자동 마감 매트릭스(v2.20.x)에 있는 협력사 분포를 강제 종료(force_closed=TRUE)에도 동일 제공 — `/auto-close-summary` 응답 `force_closed` block 에 additive 2키. **신규**: `force_closed.partner_task_matrix`(협력사×공정) + `force_closed.partner_elapsed_matrix`(협력사×처리기간 5버킷: 미시작/1일내/1~3일/3~7일/7일+). **BE**: `_assemble_company_matrix` 공용 빌더(동적/고정컬럼) + `_query_force_partner_task_matrix`(auto 복제 + 모집단 force_closed=TRUE + EXISTS(work_start_log) 제거 → 미시작 force 포함 → grand_total==force_count) + `_query_force_partner_elapsed_matrix`(`started_at IS NULL` 최우선 분리 후 COALESCE(elapsed,0) 버킷) + `_assert_invariants` 2줄. 협력사=`_COMPANY_SQL` 재사용(신규 폴백 0). **운영 검증**(force 129건): 미시작 10건 중 8건 elapsed=0 → 원안 `elapsed IS NULL` 기준이면 '1일내' 오분류 → `started_at IS NULL` 기준 정정(핵심 가치). 협력사 task 126건 100% 분류, '(미지정)' 3건=GST QI/SI. **Codex 3라운드 GO**: R1(설계 M=6 전부 미구현 지적=결함0) → R2(실코드 **M-1 multi-SELECT snapshot invariant 거짓 위반**) → M-1 fix(`build_auto_close_summary` REPEATABLE READ 단일 snapshot 고정 = force_count==매트릭스 grand_total 수학 보장 + 기존 auto invariant 노출 동시 경화, isolation finally 복원 + 복원실패 conn 폐기 A-1) → R3 **DEPLOY_SAFE/GO(M=0)**. pytest `test_sprint81_force_matrix.py` 23 GREEN(FM-01~10 + 3자정합 3 + 헬퍼방어 2, FM-04 미시작+elapsed=0 / FM-05 경계 6값 / FM-09 manager격리 포함) + 회귀 test_sprint71 21 passed 1 skipped. DB/migration 변경 0. **VIEW 후속**(별 repo): force_closed 타입 optional 2키 + mock 조건부 fallback + PartnerTaskMatrix 제목 props(force/auto 구분). 설계: AGENT_TEAM_LAUNCH.md § Sprint 81 (#79). |
| v2.22.0 | 2026-06-03 | duration man-hour 재정의 | **BE minor — 수동 일시정지 미반영 + 휴게 이중차감 fix (운영 210건)**. `duration_minutes`가 raw로 덮어써져 수동 pause 무시. 사용자 결정 = 휴게 미차감(원본 적재) + manual pause만 차감. **compute_task_manhour SSoT**: 완료로그≥1 → per-worker interval-union(세션상한 LEAST(완료기록,LEAD다음start,close_at)) − (manual pause ∩ session_union) / 완료로그0 → 단일구간 [MAX(last_started),close_at]−manual∩ 추정값. FLOOR + started_at<close_at 가드. **3경로 통일 단일 UPDATE**(completed_at+duration+elapsed+worker_count+audit 원자): 정상완료(complete_work→complete_task_unified) / ship-admin(shipment_service) / 자동마감(auto_close_relay_task 시그니처 유지 내부 위임, 호출처 5곳 무변경) / 수동강제(admin.force_close_task 휴게차감 제거 + AUTO_CLOSED_ prefix 400 차단). **운영 데이터 검증**(O/N 6873/6878/6770 + AUDIT_TRAIL_GUIDE §11) 후 **Codex 12라운드 GO**(추상1~8 + 운영검증9~12, M:5→10→2→4→1→1→1→0→2→2→1→0). 회귀 95 GREEN. **후속**: migration 058 백필(과거 210건 preflight 동반) + REF-TASK-DETAIL-CONN-INJECTION / worker_count / AUTOCLOSE-BACKSTOP / 대시보드 세션집계 별 BACKLOG. 설계: AGENT_TEAM_LAUNCH.md § FIX-DURATION v1~v12. |
| v2.21.3 | 2026-06-02 | MECH 자재 드롭다운 줄바꿈 | **FE only 1 파일 patch release**. MECH 체크리스트 자재 선택 드롭다운에서 긴 자재 spec(flow sensor/MFC)이 ellipsis 로 잘려 전체 사양 안 보이던 문제. `mech_checklist_screen.dart` — `itemHeight: null`(항목 높이 가변, 줄바꿈 필수 조건) + `selectedItemBuilder`(닫힌 필드 1줄 ellipsis 유지, 카드 레이아웃 부풀림 방지) + 메뉴 항목 `ellipsis` → `softWrap: true, maxLines: 3`. 단순 ellipsis 제거 시 Flutter DropdownButton 기본 항목 높이(48px) 고정 때문에 잘림/overflow → `itemHeight: null` 이 핵심. ELEC(짧은 옵션) 범위 제외. flutter build web GREEN. 데이터·BE 무변경, 회귀 0. ②단계 자동 Codex 이관 0항목 → Opus 자가 리뷰. |
| v2.21.2 | 2026-05-30 | 위치권한 fix | **위치 검증 토글 Off 시 출근 GPS 권한 요청 제거** — admin `geo_check_enabled` Off 인데도 협력사 출근 시 위치 권한 팝업. 원인: FE `_handleAttendance` 가 설정 무관 무조건 `_getCurrentLocation()` 호출 (BE 는 Off 면 위치 안 봄, hr.py:132 `geo_check_enabled && work_site=='GST'`). Fix: BE `/hr/attendance/today` 응답에 `geo_check_enabled` additive + FE 출근 시 `(_geoCheckEnabled && work_site=='GST')` 일 때만 GPS 호출 (BE 조건 정확 정합). `_attendanceStatusLoaded` 게이트로 설정 미로드 fail-open 방지 (Codex M-Q2). Codex 라운드 1 M=1 반영. 회귀 0. |
| v2.21.1 | 2026-05-30 | 퇴근 실수방지 | **협력사 퇴근 확인 다이얼로그 + 출퇴근 성공 토스트** — 출퇴근 one-action 토글이라 퇴근 모르고 누르면 출근 상태 즉시 종료. `home_screen _handleAttendance` checkType=='out' 시 "퇴근 처리하시겠습니까?" 확인 (취소 시 중단), 출근은 바로. 처리 성공 토스트 추가. FE only, 회귀 0. |
| v2.21.0 | 2026-05-29 | Sprint 80 | **SI 출하예정 주차별 그룹핑 + 200 cap 누락 해소** — 출하예정 389건 중 200 cap 으로 189건 누락 + 평면 가독성. BE `get_shipment_week_groups()` 신규 (ISO 주차 `IYYY-WIW` 별 + 모델별 카운트, 전체 GROUP BY → 200 무관) + planned·no-q 시 응답 `by_week` additive (기존 `get_shipment_by_status` 튜플 서비스 무변경, M-Q7). FE 검색 없으면 주차 ExpansionTile(접힘, 펼치면 모델 카운트)/검색 시 평면 + W53/12-31 "미정" 칩 + 탭 배지 전체 total. 출고완료 버튼 `_isGstSelf` → `_canShip`(role=='SI'\|\|isManager\|\|isAdmin, BE `si_manager_or_admin_required` 미러) → GST PI/QI 403 방지. pytest test_sprint79 25 passed (신규 WK-01~07). Codex 라운드 1 (M=4/A=2) → 라운드 2 (M=0, DEPLOY_SAFE). 설계서 `SPRINT80_SI_SHIPMENT_WEEK_GROUP.md`. |
| v2.20.15 | 2026-05-29 | SI 출고완료 권한 | **SI 마무리공정 출고완료 권한 확장 (GST SI 인원 허용)** — SI 일반 작업자(role='SI' 비매니저)가 출고완료 403 (GST SI 6명 중 매니저 1명만 가능). `jwt_auth.py si_manager_or_admin_required` 데코 신규 (`is_admin \|\| is_manager \|\| role=='SI'`) + `work_shipment.py` ship-complete route 교체 (admin-complete 은 manager/admin 유지). FE `gst_products_screen canShip` 정합. pytest test_ship_complete 15 passed (PERM-01 SI 200 / PERM-02 PI 403 / PERM-03 협력사 manager 200 + 기존 TC-SHIP-11 회귀수정 `_worker` role='SI' → PI). Codex M=0/A=6. + 가입화면 한글화(c168832) + 입력라벨 괄호 통일(NAME (이름)). |
| v2.20.14 | 2026-05-29 | 종료분석 GST매니저 | **종료(자동마감) 분석 페이지 GST 매니저 전체 조회** — GST 매니저(is_admin=False)가 GST task(PI/QI/SI 검사)만 보이고 협력사 task 누락 (GST 인원은 검사만 → company='GST' 필터에 협력사 미포함). `dashboard_service._build_partner_filter` `is_full_access = is_admin or (worker_company=='GST')` → admin 동일 전체 조회. 협력사 매니저 자기 회사 격리 유지. pytest test_sprint71_dashboard 21 passed (신규 tc14b GST 매니저 → BAT+FNI 둘 다). Codex M=0/A=2 (company 정규화 + 경계 TC BACKLOG). VIEW 변경 0. |
| v2.20.13 | 2026-05-29 | VIEW #78 | **공장 대시보드 TEST 데이터 전역 제외 (#69 확장)** — TEST S/N 17건 중 12건이 customer != 'TEST CUSTOMER' (SEC 등) → #69 customer-only 제외로는 누락. `_TEST_EXCLUDE_SQL` 표준 상수 (`COALESCE(customer,'')<>'TEST CUSTOMER' AND serial_number NOT LIKE 'TEST%'`) 신설 + factory.py 6곳 적용 (_count_shipped 3분기 / monthly_detail 2 mode / weekly_kpi / monthly_kpi). 검증: monthly_detail 5월 169→164. FE 변경 0 (BE 자동 정합). 경영 지표라 토글 없이 항상 제외. |
| v2.20.12 | 2026-05-29 | VIEW #75 catch 1 | **ETL 변경 이력 필터 KST 자정 정합** — VIEW EtlChangeLogPage "오늘/7일/14일/30일" 필터가 `NOW()` 24h 롤링 → 어제 오후 섞임. `admin.py /admin/etl/changes` `NOW() - INTERVAL 'N days'` → `((now() AT TIME ZONE 'Asia/Seoul')::date - (INTERVAL '1 day' * (days-1)))::timestamp` (옵션 A, days=1=오늘 자정~현재). changed_at=KST naive → 서버 tz 독립. 검증: 오늘 24h롤링 32→자정기준 4. VIEW 영향 0. **catch 2 (serial_number tracking) 스킵** — S/N=제품 고유 식별자=불변이 정상, etl.change_log 미추적 정상 (Twin파파 결정). |
| v2.20.11 | 2026-05-29 | TMS(M)/(E) 구분 | **매트릭스 셀↔리스트 정합 통일** — DB partner 'TMS' 단일저장이나 mech/module→TMS(M), elec→TMS(E). `_COMPANY_SQL` 표준식 신설 → matrix/details/partner_filter 3곳 통일. 운영 grand_total 223 (TMS(M) 8 + TMS(E) 19 분리). 미시작 자동마감 0건 검증 (릴레이 자동마감=started만 대상, 정상). |
| v2.20.10 | 2026-05-29 | 미지정 분류 버그 | task_category 'TM'→'TMS' 오타 (dashboard_service.py만) + '(미지정)' 셀 클릭 0건 (표시값 직접매칭 → category-aware CASE). v2.20.11에 흡수. |
| v2.20.6~7 | 2026-05-29 | VIEW #76/#77 | #76 auto-close-details 500 (SQL alias p↔pi) / #77 force_closed 3분류 (옵션 X + by_reason + close_type). 운영 auto 223 + manual 0 + force 107 = total 330. |
| v2.20.9 | 2026-05-29 | syntax hotfix | **v2.20.8 배포 실패 복구** — 4 분포 SQL force_closed=FALSE 가드 python 일괄 치환 시 regex 가 details `trigger_sql` 문자열 리터럴 내부 `AND t.close_reason LIKE %s` 까지 매칭 → 줄바꿈 삽입 → unterminated string literal (L755) → Flask boot 실패 → Railway 배포 rollback (v2.20.7 잔존, 15분+ 지연). Fix: `trigger_sql` 한 줄 복원 (close_filter 가 force_closed 처리하므로 가드 불필요) + 4 분포 SQL 가드 7곳 정상 유지. 검증: `/auto-close-summary` 200 (auto 223 + force 107 = total 330, invariant 통과) + details close_type + #76 partner=C&A 200. **교훈**: 일괄 치환 후 `ast.parse` syntax 검증 선행 의무 (문자열 리터럴 내부 매칭 위험). |
| v2.20.7~8 | 2026-05-29 | VIEW #77 force_closed | **마감 유형 3분류 (자동/수동/강제)** — 옵션 X (force_closed=TRUE only, v2.15.16 합의 정합). `_query_kpi_counts` force CTE + force_count + auto/manual force_closed=FALSE 가드 / `_query_force_close_reason_distribution` 신규 (by_reason) / summary force_closed block + total=auto+manual+force / `_assert_invariants` force 합산 / details close_filter 합집합 + close_type ('auto'/'manual'/'force'). 운영 5-15후 force=99 (closed_by 97%), close_reason 매니저 free-text. v2.20.8 배포 실패(syntax) → v2.20.9 복구. VIEW 후속: types force_closed?:CountWithDelta + by_reason + close_type, KPI 3카드 분리(옵션 A). |
| v2.20.6 | 2026-05-29 | VIEW #76 HOTFIX | **auto-close-details 500 (SQL alias mismatch)** — count_sql(`pi`) vs item_sql(`p`) alias 불일치 + `_build_partner_filter` hardcoded `pi.*` → partner 명시 시 undefined alias → 500. Fix: item_sql alias `p`→`pi` 통일 + row 처리 PI/QI/SI+partner NULL → '(미지정)' (Sprint 71 v3 패턴 정합). 검증 partner=C&A 200. VIEW 영향 0. |
| v2.20.3 | 2026-05-29 | APScheduler timezone fix | **시간 단위 cron 9시간 지연 메가버그 fix** — v2.20.2 디버그 endpoint 로 root cause 확정. `BackgroundScheduler(timezone=Config.KST)` 에 stdlib `timezone(timedelta(hours=9))` 사용 → APScheduler 가 IANA tz 로 인식 못해 cron[hour] 영역 fire time 을 UTC 로 해석 → 시간 단위 cron 8종 전부 9시간 지연 fire. **증거**: `/api/admin/debug/scheduler` 응답에서 `alert_shipment_overdue` next_run_time = `2026-05-29T07:30:00+00:00` (= KST 16:30, 의도는 KST 07:30). **영향 cron 8종**: `alert_shipment_overdue` 07:30 / `task_escalation` 09:00 / `_check_checklist_done_task_open_09` 09:00 / `_check_checklist_done_task_open_15` 15:00 / `shift_end_reminder_17` 17:00 / `check_unfinished_tasks` 18:00 / `shift_end_reminder_20` 20:00 / `cleanup_access_logs` 03:00 — 모두 9h 지연 fire. 분 단위/interval cron (`pool_warmup` / `task_reminder` / `check_break_time` / `check_orphan_relay_tasks`) 은 영향 없음. **Fix**: `config.py` `KST = ZoneInfo('Asia/Seoul')` (이전: `timezone(timedelta(hours=9))`) + `requirements.txt tzdata>=2024.1` (컨테이너 IANA tz DB). **부수**: `_alert_shipment_overdue` 가 실행 결과 dict 반환 + admin_debug `/run-job` 응답에 `job_result` 포함 → 메일 발송 결과 즉시 확인 가능. **배포 즉시**: scheduler 재초기화 → 모든 시간 단위 cron next_run_time 정상 KST 시각 재계산. 5-30 07:30 KST 부터 출하 미처리 알림 정상 발송. |
| v2.20.2 | 2026-05-29 | admin debug | **scheduler 진단 + cron 강제 실행 endpoint 2개** — 5-29 07:30 KST `alert_shipment_overdue` cron 미실행 사건 후속 (Railway 로그 분석: 다른 cron 4종 정상 fire / 출하 알림만 0건, 어제 미처리 10건 메일 미발송). 신규 `backend/app/routes/admin_debug.py` (+~110 LoC) — `GET /api/admin/debug/scheduler` (등록 jobs + next_run + trigger + func 경로) + `POST /api/admin/debug/run-job/<job_id>` (동기 강제 실행 + traceback 응답). 권한 `@jwt_required + @admin_required`. 어제 출하 미처리 10건 (DBW-3750 / GBWS-6728/7037/7100/7118/7128/7129/7130 / IVAS-276/277) 강제 발송 수단 확보. 재발 방지 — 향후 cron 누락 의심 시 1초 진단 + 즉시 복구. 회귀 위험 0 (신규 endpoint, 기존 touch 0). |
| v2.20.1 | 2026-05-29 | Sprint 71 hotfix | **partner_task_matrix invariant violation 해소** (Sprint 76 COALESCE 패턴 정합). VIEW 측 catch (5-28): `grand_total != started_task_count` → InvariantViolationError 500. **Root**: `_query_partner_task_matrix` `HAVING ... IS NOT NULL` 이 (1) PI/QI/SI category 자동 마감 (ELSE NULL) (2) plan.product_info partner NULL 영역 제외 → grand_total 부족. **Fix**: SELECT 절 `COALESCE(NULLIF(TRIM(partner), ''), '(미지정)')` + HAVING 제거 → 통합 group. **운영 검증 (7일 actual)**: PI 3건 (GBWS-7150/7110/7143, PI_LNG_UTIL LNG/UTIL 가압검사, AUTO_CLOSED_BY_SECOND_FINAL_TRIGGER:PI_CHAMBER) = '(미지정)' 분류 — **PI는 GST 자사 인원 작업이라 협력사 매핑 자체 없음** = 의미상 정합. plan.product_info partner NULL 0건 (ETL 정합). **pytest**: TC-19 invariant 정합 PASS (fix 작동 입증) + TC-18b 회귀 PASS / TC-20 @skip (test infra 미스터리, BACKLOG POST-REVIEW-TC20-FIXTURE-MYSTERY-20260529). VIEW 영향 0 (자동 정합). |
| v2.20.0 | 2026-05-28 | Sprint 71 | **Manager Dashboard 자동 마감 분석 API 2개** — `dashboard_service.py` 신규 (~620 LoC) + `admin_dashboard.py` 신규 (~150 LoC) — endpoint 2개 (`/auto-close-summary` + `/auto-close-details`). 분류 LIKE (`AUTO_CLOSED_BY_%` / `MANUAL_FORCE_CLOSE` / 제외) + 모집단 3분리 (`started`/`unstarted`/`missed_worker`) + V1 24h backfill (KST) + V6 partner_task_matrix (canonical + grand_total assertion) + `_assert_invariants()` 5분포+4 합산 → 500 + Sentry. 권한 `@manager_or_admin_required` + manager partner filter X1 (`work_start_log + workers.company` EXISTS, v3.1 결정 6 정합). M3 fix (Codex Q5 root cause) — conftest teardown `app_access_log` 선행 + `__init__.py` after_request rollback+`put_conn` (connection leak 차단). pytest 18/18 GREEN (617s). Codex 라운드 1 (M=3/A=4) → 라운드 2 (M=0 GREEN ✅) 후 배포. AXIS-VIEW Sprint 71 mockup 5 file 작성 완료 + BE freeze (v3.1) 후 BE 구현 진입. VIEW hook 추가 catch 즉시 가능. 설계서: AGENT_TEAM_LAUNCH.md § Sprint 71 v3.1 |
| INFRA | 2026-05-20 | **GCP MIGRATION 준비 완료 → 비용 협의로 HOLD** | **인프라 작업, 코드 영향 0**. **배경**: Railway 부분 장애로 GCP Cloud Run + Cloud SQL migration 결정 → 1주 일정 진행 → 모든 자원 + 데이터 이전 + 검증 100% 완료 → 비용 분석 결과 Railway 대비 ~10배 증가 → 사용자 결정 hold + 비용 협의. **결과 자원**: Cloud SQL `g-axis-core` (PG 18, Enterprise Plus, db-perf-optimized-N-2 다운사이즈됨, 백업+PITR 활성화) + Cloud Run `axis-core-api` (1 vCPU/2 GiB, min=0 stop) + Artifact Registry 이미지 + Cloud Build trigger + 환경변수 12개 + 운영 데이터 dump 적용. **현재 standby**: Cloud SQL activation=NEVER, Cloud Run min=0 → 월 ~$20 (storage만). free trial $300 으로 500일+ 안전. **재오픈**: 30분 안에 cutover 가능 — `AXIS-OPS/GCP_MIGRATION_STANDBY.md` 참조. **코드 변경 (cutover 전 적용)**: backend/Dockerfile (`affea54`) + .dockerignore + config.py v2.18.3 fallback 제거 (`3fb98cd`) + CLAUDE.md Codex 채널 정정 (`9b43e66`, brew → npm). **Railway 상태**: Auto Deploys ON 복원 (2026-05-20 stop 후 재활성화), prod 운영 정상 (사용자 150명). **트리거 (재오픈 조건)**: Railway 장애 재발 / 비용 협의 완료 / free trial 만료 (~2026-06-19) 전 결정. **연관 catch**: Cloud Run env `DATABASE_URL` 에 공백 typo (`asia-northe   ast3`) → Unix socket 못 찾던 사고 → 즉시 수정. Cloud SQL 처음 N-8 (8 vCPU/64 GB) 선택했다가 free trial burn rate $38/일 발견 → N-2 다운사이즈. APScheduler `/tmp/lock` multi-instance 한계는 max_instances=10 + scale-out 시 cron 중복 fire 잠재 (별 sprint advisory). **메모리**: `~/.claude/projects/.../memory/project_gcp_migration_standby.md` |
