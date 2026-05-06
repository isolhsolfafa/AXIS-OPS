# AXIS-OPS 백로그

> 마지막 업데이트: 2026-04-27 (DB Pool 사이즈 보정 Sprint + 3개 OBSERV + PIN 보호 Sprint 4건 신규 등록 — Q-B 31 peak in-flight 결정적 데이터 + PIN 화면 손실 가설 입증 기반)
> 이 파일은 보류/재검토/계획/아이디어를 한 곳에서 관리합니다.
> 완료된 항목은 PROGRESS.md로 이동합니다.

---

## 🔧 리팩토링 Sprint 계획 (2026-04-21 등록)

> **근거**: CLAUDE.md § 📏 코드 크기 원칙 + 🛡️ 리팩토링 안전 규칙 7원칙
> **트리거**: 2026-03-22 AXIS SYSTEM 점검 보고서 지적 사항 미해결 + 감사 이후 파일 크기 오히려 증가
> **실측 기준일**: 2026-04-21

### 📊 현재 위반 현황 (1단계 기준: 🟡 500 / 🔴 800 / ⛔ 1200)

#### OPS BE

| 파일 | LOC | 감사 시점 | 증감 | 등급 |
|---|---|---|---|---|
| `routes/admin.py` | 2,546 | 2,070 | +476 | ⛔ God File |
| `services/task_service.py` | 1,478 | 1,018 | +460 | ⛔ God File |
| `routes/work.py` | 1,343 | 921 | +422 | ⛔ God File |
| `routes/checklist.py` | 1,192 | — | 신규 | 🔴 필수 분할 |
| `services/auth_service.py` | 1,108 | 1,097 | +11 | 🔴 필수 분할 |
| `services/checklist_service.py` | 1,085 | — | 신규 | 🔴 필수 분할 |
| `services/scheduler_service.py` | 1,074 | — | 신규 | 🔴 필수 분할 |
| `routes/production.py` | 875 | 496 | +379 | 🔴 필수 분할 |
| `routes/auth.py` | 860 | — | — | 🔴 필수 분할 |
| `services/task_seed.py` | 660 | — | — | 🟡 경고 |

#### OPS FE (Flutter)

| 파일 | LOC | 등급 |
|---|---|---|
| `screens/admin/admin_options_screen.dart` | 2,593 | ⛔ God File |
| `screens/task/task_detail_screen.dart` | 1,082 | 🔴 필수 분할 |
| `screens/checklist/elec_checklist_screen.dart` | 1,076 | 🔴 필수 분할 |
| `screens/qr/qr_scan_screen.dart` | 943 | 🔴 필수 분할 |
| `screens/task/task_management_screen.dart` | 905 | 🔴 필수 분할 |
| `screens/checklist/tm_checklist_screen.dart` | 808 | 🔴 필수 분할 |
| `screens/settings/profile_screen.dart` | 727 | 🟡 경고 |

---

### 📋 리팩토링 Sprint 전체 로드맵

> **총 12개 Sprint (BE 7 + FE 5), 각 1주 전후 예상 + 1~2일 배포 관찰**
> **원칙**: Sprint 간 독립 배포 가능. 중간에 기능 Sprint 끼워넣기 허용.

#### Phase 1 — 테스트 기반 확보 (선행 필수)

| Sprint ID | 대상 | 작업 | 우선순위 |
|---|---|---|---|
| **REF-00-TEST** | 전 대상 파일 | pytest 커버리지 측정 + 미비 영역 테스트 추가 (목표 80%+) | 🔴 HIGH |

**Why**: 리팩토링 7원칙 #1(테스트 커버리지 선행) 준수. 테스트 없이 분할 시 Regression 탐지 불가.

#### Phase 2 — BE God File 분할 (admin.py 우선)

##### REF-BE-01 ~ 06: admin.py 2,546줄 → 분할 (6 Sprint)

| Sprint ID | 작업 | 이동 LOC | 결과 admin.py |
|---|---|---|---|
| **REF-BE-01** | `routes/admin_settings.py` 분리 (settings + admin_settings CRUD) | ~400줄 | 2,546 → 2,146 |
| **REF-BE-02** | `routes/admin_attendance.py` 분리 (출퇴근 조회·수정) | ~500줄 | 2,146 → 1,646 |
| **REF-BE-03** | `routes/admin_worker.py` 분리 (worker 승인·관리자 지정·비활성화) | ~600줄 | 1,646 → 1,046 |
| **REF-BE-04** | `routes/admin_kpi.py` 분리 (KPI·대시보드 집계) | ~400줄 | 1,046 → 646 |
| **REF-BE-05** | `routes/admin_task.py` 분리 (강제종료·task 관리) | ~300줄 | 646 → ~346 |
| **REF-BE-06** | 잔여 정리 + 도메인 entity 도입 (`Worker`, `Task` dataclass 확장) | — | 🟢 OK 진입 |

**분할 전략**: `admin.py` 블루프린트 유지 + 모듈별 register 방식 (기존 URL 경로 100% 유지 — BE API 계약 변경 0)
**테스트**: 기존 admin API 테스트 전부 GREEN 유지. 분할 이후에도 URL·응답 스키마 동일 검증.

##### REF-BE-07 ~ 09: task_service.py 1,478줄 → 분할 (3 Sprint)

| Sprint ID | 작업 | 이동 LOC |
|---|---|---|
| **REF-BE-07** | `services/task_state_service.py` 분리 (시작/완료/일시정지) | ~500줄 |
| **REF-BE-08** | `services/task_validation_service.py` 분리 (공정 검증 + duration 검증) | ~400줄 |
| **REF-BE-09** | `services/task_alert_service.py` 분리 (완료 알림 + 트리거) | ~400줄 |

**분할 근거**: ADR-010(partner→company 매핑)·ADR-015(worker별 pause) 등 책임 3개 혼재
**최종**: task_service.py → ~200줄 (공통 helper만)

##### REF-BE-10 ~ 11: work.py 1,343줄 → 분할 (2 Sprint)

| Sprint ID | 작업 | 이동 LOC |
|---|---|---|
| **REF-BE-10** | `routes/work_lifecycle.py` 분리 (start/complete/resume) | ~700줄 |
| **REF-BE-11** | `routes/work_relay.py` 분리 (릴레이 + 재활성화) | ~400줄 |

##### REF-BE-12 ~ 14: 나머지 God/필수 분할

| Sprint ID | 대상 | 작업 |
|---|---|---|
| **REF-BE-12** | `checklist.py` + `checklist_service.py` | 카테고리별 분리 (TM / ELEC / MECH) |
| **REF-BE-13** | `auth_service.py` 1,108 | `auth_core.py`(로그인/회원가입) + `auth_email.py`(SMTP/인증) + `auth_token.py`(JWT/refresh) |
| **REF-BE-14** | `scheduler_service.py` 1,074 | 알림 유형별 분리 (`scheduler_task_alert`, `scheduler_escalation`, `scheduler_shift_end`) |

#### Phase 3 — BE 경고 파일 정리 (🟡 500~800줄)

| Sprint ID | 대상 | 우선순위 |
|---|---|---|
| **REF-BE-15** | `production.py` 875 → 분할 | 🟡 MEDIUM |
| **REF-BE-16** | `auth.py` 860 → 분할 | 🟡 MEDIUM |
| **REF-BE-17** | `task_seed.py` 660 → 분할 (MECH/ELEC/TMS seed 분리) | 🟢 LOW |

#### Phase 4 — FE 리팩토링 (OPS Flutter)

| Sprint ID | 대상 | 작업 |
|---|---|---|
| **REF-FE-01** | `admin_options_screen.dart` 2,593 | 섹션별 위젯 분리 (설정·출퇴근·미종료·매니저·체크리스트 → 5 파일) |
| **REF-FE-02** | `task_detail_screen.dart` 1,082 | `widgets/task_detail/*` (헤더·workers·actions·tooltip 분리) |
| **REF-FE-03** | `elec_checklist_screen.dart` 1,076 + `tm_checklist_screen.dart` 808 | 공통 `widgets/checklist/*` 추출 (CheckItemRow, PhaseSelector 등) — 재활용 원칙 Rule of Three |
| **REF-FE-04** | `qr_scan_screen.dart` 943 | 카메라 로직 → `services/qr_scanner_web.dart` 강화 + UI 분리 |
| **REF-FE-05** | `task_management_screen.dart` 905 | 필터·리스트·액션 시트 각각 위젯으로 추출 |

---

### 🛡️ 공통 안전장치 (모든 REFACTOR Sprint 적용)

1. Sprint 시작 전 `git tag pre-refactor-{sprint-id}` 생성
2. pytest 결과 스냅샷 저장 (`tests/snapshots/{sprint-id}_before.txt`)
3. `[REFACTOR]` 커밋 prefix
4. Railway staging 먼저 → 1~2일 현장 관찰 → prod
5. DB migration 포함 금지 (리팩토링 Sprint에는 ALTER/CREATE 0)
6. Codex 교차검증 M 전부 해결
7. 한 Sprint 이동 LOC 상한 500줄

### 📈 진행 추적

| 항목 | 시작 LOC | 목표 LOC | 현재 LOC | 상태 |
|---|---|---|---|---|
| admin.py | 2,546 | ≤ 500 | 2,546 | 🔴 미착수 |
| task_service.py | 1,478 | ≤ 500 | 1,478 | 🔴 미착수 |
| work.py | 1,343 | ≤ 500 | 1,343 | 🔴 미착수 |
| checklist.py | 1,192 | ≤ 500 | 1,192 | 🔴 미착수 |
| auth_service.py | 1,108 | ≤ 500 | 1,108 | 🔴 미착수 |
| checklist_service.py | 1,085 | ≤ 500 | 1,085 | 🔴 미착수 |
| scheduler_service.py | 1,074 | ≤ 500 | 1,074 | 🔴 미착수 |
| admin_options_screen.dart | 2,593 | ≤ 500 | 2,593 | 🔴 미착수 |
| task_detail_screen.dart | 1,082 | ≤ 500 | 1,082 | 🔴 미착수 |
| elec_checklist_screen.dart | 1,076 | ≤ 500 | 1,076 | 🔴 미착수 |

### 🚧 리팩토링 Sprint 우선순위 (권장 순서)

1. **REF-00-TEST** (테스트 기반 확보 — 필수 선행)
2. **REF-BE-01 ~ 06** (admin.py — 감사서 #2 우선순위)
3. **REF-FE-01** (admin_options_screen.dart — 2,593줄, FE 최대 God File)
4. **REF-BE-07 ~ 09** (task_service.py — 알림 트리거 안정화 겸)
5. **REF-BE-10 ~ 11** (work.py — 릴레이/재활성화 로직 분리)
6. **REF-FE-02 ~ 05** (FE 병행 가능)
7. **REF-BE-12 ~ 14** (checklist/auth/scheduler)
8. **REF-BE-15 ~ 17** (경고 파일 정리)

---

## 📐 설계 원칙 (모든 Sprint·HOTFIX 결정 시 참조)

### 클린 코어 데이터 원칙 (2026-04-20 확정)

> **강제종료 task는 실행 측정값(`work_start_log` / `work_completion_log` / `duration_sec`)을 절대 생성하지 않는다. NULL이 정직한 답이다.**

- **Why**: G-AXIS 장기 목표는 **APS-Lite**(Advanced Planning & Scheduling). 강제종료는 실측이 없는 상태이므로 추측값을 채우면 cycle time·리드타임·OEE 분석이 영구 오염. 한 번 들어간 가짜 시간은 진짜 데이터와 구분 불가.
- **BE 적용**: force-close 엔드포인트에서 `wsl`/`wcl` row insert 절대 금지. `duration_sec`에 NOW() 기반 계산값·추정값·기본값 주입 금지. 감사 기록은 `app_task_details.completed_at` + `force_closed=TRUE` + `close_reason` + `closed_by` 4필드에만.
- **VIEW 적용**: 강제종료 task 시간 필드(`completed_at` / `force_closed_at`) 노출 시 단독 시각 표시 금지, 반드시 감사 액션 라벨 동반 (상태 컬럼 `🔒 강제종료 {시각}` / 툴팁 `종료 처리: {시각}`). 현행 v1.32.2는 상태 컬럼 측면 이미 충족 — FE-19.1은 툴팁 용어 정합에 한정.
- **회귀 가드**: `TEST-CLEAN-CORE-01` pytest (force_close 호출 후 wsl/wcl row 0건 확인) — 하단 표 참조.
- **스코프**: 강제종료 경로에만 적용. 정상 완료(`work_completion_log` 자발 생성) + Case 1 Orphan wsl(기존 측정값 보존)은 적용 대상 아님.
- **상세**: `AGENT_TEAM_LAUNCH.md` HOTFIX-04 섹션 상단 📐 설계 원칙 블록 참조.

---

## 🔴 지금 진행 중 / 미해결

### 🗺️ 우선순위 로드맵 (2026-04-22 확정 — 알람 장애 4 HOTFIX 완료 직후)

> **컨텍스트**: 2026-04-17~22 알람 장애 4 HOTFIX (PHASE1.5 / SCHEMA-RESTORE / DUP / DELIVERY) 모두 VIEW + OPS(BE) Sprint 완료. 이 로드맵은 그 직후 "급한 순서" 기준.

**Phase A — 24h 시계 (긴급 HOTFIX 사후 의무)**
1. `POST-REVIEW-HOTFIX-PHASE1.5-20260422` — 30분
2. `POST-REVIEW-HOTFIX-SCHEMA-RESTORE-20260422` — 30분
3. `POST-REVIEW-HOTFIX-DUP-20260422` — 30~40분
4. `POST-REVIEW-HOTFIX-DELIVERY-20260422` — 30분
   - 합계 **~2h**. CLAUDE.md 긴급 HOTFIX 예외조항 S2 준수. 배포 후 24h 이내 Codex 사후 검토 의무.

**Phase B — 네가 직접 언급한 미진 사항 (일정 결정 필요)**

5. **Railway DB rotation** — 배포 창구 세워야 함. Twin파파 결정 필요.
6. **작업 flow 디버깅** — 맥락 재확인 필요. (혹시 오늘 Sprint 55 UTIL_LINE_2 건과 연결? 별건인지?)

**Phase C — 이번 주 내**

7. `OBSERV-ALERT-SILENT-FAIL` — 🔴 P1, Phase 1.5 임시 로깅 → 영구 + Sentry 정식 연동. 3~4h. 재발 방지 필수 방어선.
8. `UX-SPRINT55-FINALIZE-DIALOG-WARNING` — 🟡 P2, 1.5h. 현장 혼란 즉시 제거 (오늘 신규 등록).

**Phase D — HOTFIX-DUP 배포 24h 안정화 이후 착수**

9. `POST-REVIEW-MIGRATION-049-NOT-APPLIED` — 🔴 S3, 1~2h. 재발 방지의 근본 조사. 산출: `POST_MORTEM_MIGRATION_049.md` 또는 `ALERT_SCHEDULER_DIAGNOSIS.md` §13.

**Phase E — 관찰성 + 인프라 정비 (중기)**

10. `OBSERV-MIGRATION-HISTORY-SCHEMA` — 🟡 P2, 2~3h
11. ~~`OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION`~~ — ✅ **COMPLETED** (v2.10.8, 2026-04-27 — `assert_migrations_in_sync()` 신규, disk vs DB sync 검증 + Sentry capture_message)
12. `OBSERV-ADMIN-ACTION-AUDIT` — 🟡 P2, 2+2h (FEAT-SPRINT55-REACTIVATE-* 배포 전 권고)

**Phase F — Sprint 55 UX 개선 (중기)**

13. `FEAT-SPRINT55-REACTIVATE-HYBRID-ROLE` — 🟡 P2, 반나절
14. `FEAT-SPRINT55-REACTIVATE-REQUEST-FLOW` — 🟢 P3, 1~1.5일 (13번 선행)
15. `DOC-AXIS-VIEW-REACTIVATE-BUTTON` — 🟢 P3, 30분

**Phase G — 기타 별건**

16. `INFRA-COLLATION-REFRESH` — 🟡 MEDIUM, Sprint 62 이후 배포 창구
17. `TEST-CLEAN-CORE-01` — 🔴 OPEN (P 중간-상), 강제종료 회귀 가드, 40분
18. `FE-ALERT-BADGE-SYNC` — 🟡 BACKLOG 재검토, 45분 (Scheduler 복구 완료로 전제조건 해소됨)

---

**내일 첫 항목**: Phase A #1 (POST-REVIEW-HOTFIX-PHASE1.5) 부터 순차. 4건 모두 Codex 로 돌리면 사실상 프로세스만 기다리면 되니까 오전 중 일괄 처리 가능.

---



| ID | 항목 | 상태 | 비고 |
|----|------|------|------|
| BUG-1 | QR 카메라 권한 팝업 가려짐 | 🔧 수정 중 | DOM 오버레이(z-index:9999)가 브라우저 권한 팝업을 가림. getUserMedia 선행 호출 방식으로 수정 진행 |
| BUG-2 | WebSocket 프로토콜 불일치 | ✅ Sprint 13 수정 완료 | Flask-SocketIO → flask-sock(raw WS) 교체. events.py 전체 리라이트(ConnectionRegistry + ws_handler). FE 변경 0건. 배포/검증 대기 |
| BUG-3 | 출퇴근 버튼 퇴근 후 비활성화 | 🔍 분석 완료 | BE는 당일 다중 in/out 쌍 지원(카운팅 로직), 그러나 FE에서 `checked_out` 상태가 종료 상태로 처리되어 재출근 버튼 비활성화됨. FE 상태 머신에 재출근 플로우 추가 필요. 일일 리셋은 KST 자정 기준 정상 동작 |
| BUG-4 | 알림/알람 실시간 전달 안됨 | ✅ Sprint 13 수정 완료 | scheduler_service.py 5곳 `create_alert()` → `create_and_broadcast_alert()` 변경. DB 저장 + WebSocket broadcast 동시 처리. BUG-2 해결로 실시간 경로 복원. 배포/검증 대기 |
| BUG-5 | QR 카메라 프레임 벗어남 + 스캔 영역 직사각형 | ✅ 수정 완료 + 배포 | **1차 원인(위치)**: `left+right` CSS → `left+width` 명시로 해결. **2차 원인(스캔 영역)**: Dart `jsify()` interop이 html5-qrcode qrbox 객체 전달 실패 (6~8차 시도 모두 실패) → **9차 수정**: 순수 JS `<script>` 태그로 config 생성, Dart interop 완전 제거. qrbox 콜백 함수가 205×205 정사각형 반환 확인. **11차 수정(Sprint 16)**: 3중 방어 — CSS !important(aspect-ratio:1/1), DOM 강제(height=width), MutationObserver 실시간 감시 |
| BUG-6 | 협력사 task 리스트에 작업자명 미표시 | ✅ 수정 완료 | BE `work.py`: task 목록 API에 `worker_name` 필드 추가 (workers 테이블 JOIN). FE `task_item.dart`: `workerName` 필드 추가. FE `task_management_screen.dart`: 카테고리 행에 작업자 아이콘+이름 표시. GST `gst_products_screen.dart`는 기존에 이미 worker_name 표시 구현됨 (시작된 작업만 표시 — 정상) |
| BUG-7 | 휴게시간 일시정지/알람 미작동 + 자동재개 미구현 | ✅ Sprint 14 핫픽스 수정 완료 | IntervalTrigger→CronTrigger(second=0), send_break_end_notifications에 auto-resume 추가, force_pause 멀티작업자 지원. 76 passed |
| BUG-8 | 작업시간(duration)에서 휴게시간 미제외 | ✅ Sprint 14 핫픽스 수정 완료 | `_calculate_working_minutes()` + `_calculate_break_overlap()` 신규. admin_settings 4개 break 자동 차감. 이중차감 방지 (manual pause만 finalize에서 차감) |
| BUG-9 | Force-close에서 total_pause_minutes 미차감 | ✅ Sprint 14 핫픽스 수정 완료 | admin.py force-close에 `_calculate_working_minutes` 적용 + manual pause 차감 |
| BUG-10 | QR 카메라 프레임 스크롤 분리 | ✅ Sprint 14 핫픽스 수정 완료 | ScrollController + onScroll → `updateScannerDivPosition()` 연결. video와 Flutter Container 동기화 |
| BUG-11 | Location QR 필수 설정(on/off) 미작동 | ✅ Sprint 15 수정 완료 | **근본 원인**: `task.location_qr_verified`는 DB에서 항상 FALSE (업데이트 안 됨). **수정**: BE에서 `product.location_qr_id` 직접 체크로 변경. FE에서 QR 스캔 후 location_qr_required 팝업 + 자동 location scan 모드 전환. 28 tests passed |
| BUG-12 | 다중 작업자 시작/종료 FE 차단 | ✅ Sprint 15 수정 완료 | **근본 원인**: FE가 `task.status`(전체 상태)로 버튼 표시 → worker2 시작 불가. **수정**: BE에 `my_status` 필드 추가(work_start_log/completion_log JOIN). FE에 `myWorkStatus` getter + "작업 참여" 버튼 + "내 작업 완료" 뱃지. 28 tests passed |
| BUG-13 | getAdminSettings() 에러 시 빈 {} 반환 | ✅ Sprint 16 수정 완료 | FE `task_service.dart` catch블록: `{}` → `{'location_qr_required': true}` 안전모드 기본값. 에러 시 블록 활성(안전한 쪽)으로 동작 |
| BUG-14 | 다중 작업자 표시 디버깅 부족 | ✅ Sprint 16 디버그 로깅 추가 | BE work.py/gst.py: 2명+ workers task에 `[BUG-14]` 로그. FE task_item.dart: `debugPrint` 추가. 재현 시 로그로 원인 추적 가능 |
| BUG-15 | QR 카메라 div가 dialog overlay 시 가려짐 | ✅ Sprint 15.5 수정 완료 | `hideScannerDiv()`/`showScannerDiv()` 추가. dialog 열릴 때 DOM div 숨김 처리 |
| BUG-16 | System Offline 표시 (서버 정상인데) | ✅ Sprint 16.1 수정 완료 | CORS가 `/api/*`에만 적용 → `/health`는 브라우저 preflight 거부. `__init__.py` CORS에 `/health` 경로 추가 |
| BUG-17 | Location QR 팝업 깜빡임 + 확인 버튼 미작동 | ✅ Sprint 16.1 수정 완료 | MutationObserver가 `display:none` 감지 → hide↔show 무한루프. `hideScannerDiv()`에서 Observer disconnect, `showScannerDiv()`에서 재활성화 |
| BUG-18 | GST Manager 출퇴근 데이터 미표시 | ✅ Sprint 24 핫픽스 수정 완료 | `_get_manager_company_filter()` GST manager → `'GST'` 반환 vs `WHERE w.company != 'GST'` 모순. GST이면 None 반환(전체 접근)으로 수정 |
| BUG-19 | 비밀번호 찾기 — 없는 이메일도 인증 화면 이동 | ✅ Sprint 24 핫픽스 수정 완료 | 보안 관행(항상 200) → 내부 시스템이므로 404 EMAIL_NOT_FOUND 반환으로 변경 |
| BUG-20 | 로그인 에러 메시지 불명확 (계정 미존재 vs 비밀번호 오류) | ✅ Sprint 24 핫픽스 수정 완료 | 동일 INVALID_CREDENTIALS → 404 ACCOUNT_NOT_FOUND + 401 INVALID_PASSWORD 분리 |
| BUG-21 | FE 404 에러 메시지 하드코딩 | ✅ Sprint 24 핫픽스 수정 완료 | "요청한 리소스가 없습니다" → 서버 메시지 그대로 표시 |
| BUG-22 | Logout Storm — 401 무한 루프 | ✅ Sprint 25 수정 완료 | FE: _authSkipPaths + _isForceLogout + _isLoggingOut + clearToken 선행 + 3s timeout. BE: jwt_optional 데코레이터 + logout @jwt_optional (토큰 없이 200 OK). VIEW도 동일 패턴 수정 완료 (v1.4.2) |
| BUG-23 | QR 카메라 Viewfinder 모서리 코너 간헐적 미표시 | ✅ 수정 + 배포 완료 | `_forceSquareAfterCameraStart()`에서 viewfinder 제외 (video 포함 div만 타겟) + CSS `overflow:visible !important` 보호. Netlify 배포 완료 — 실기기 테스트 필요 |
| BUG-24 | Task Seed 반복 실패 — 배포마다 task 0건 | ✅ Sprint 29-fix 수정 완료 | migration 022 소실 → task_type 컬럼 없어 INSERT silent fail. **근본 해결**: `schema_check.py` ensure_schema() 앱 시작 시 자동 검증/복구 + migration 023 정식 기록 + FK CASCADE→RESTRICT |
| FIX-21 | QR 목록 search에 Order No 검색 추가 | ✅ 수정 완료 (2026-03-18) | `qr.py` search WHERE절에 `p.sales_order ILIKE` 추가. FE placeholder 변경 대기 ("S/N, QR Doc ID, Order No 검색...") |
| FIX-22 | Admin 태스크 목록에 DUAL TMS L/R 미표시 | ✅ 수정 + push 완료 (2026-03-18) | `work.py` — `?all=true`(관리자) 시 serial_number 기준 전체 조회로 TANK QR 태스크 포함 |
| FIX-23 | SWS JP line 매칭 누락 (JP(F15) 등) | ✅ 수정 완료 (2026-03-18) | `task_seed.py` — `== 'JP'` → `startswith('JP')` JP 계열 전체 PI_LNG_UTIL 활성 |
| BUG-25 | 생산실적 O/N 펼침 시 S/N 상세 미반환 | ✅ 수정 완료 (2026-03-22) | `production.py` — `sns` 배열 구성 로직 누락. `sns_detail` + `sn_summary` 추가. 변수명 충돌(`sn_progress`→`sn_prog`) 수정 |
| BUG-26 | 생산실적 TMS→TM 키 불일치 — O/N process N/A + S/N TM N/A | ✅ 수정 완료 (2026-03-22) | `production.py` — `_CAT_TO_PROC={'TMS':'TM'}` 매핑. FE `process_status`→`processes` 키 변경만 필요 |
| BUG-26-B | processes ready 미반환 + confirmable 매핑 오류 | ✅ 수정 완료 (2026-03-22) | `ready` alias + `proc_key` 전달 + O/N 스코프 필터 + `_PROC_TO_CAT` 역매핑 (POST confirm 시 TM→TMS 변환) |
| BUG-29 | QR 카메라 프레임 과대 — 직접입력 안보임 | ✅ 수정 + 배포 완료 (2026-03-27) | cameraSize 300→240 + Center 래핑. stretch 방지. 실기기 검증 완료 |
| BUG-30 | 로그인 에러 시 시스템코드 노출 | ✅ 수정 + 배포 완료 (2026-03-28) | api_service.dart 401→서버 message 사용. login_screen.dart 표시 시 `[ERROR_CODE]` regex 제거. 에러코드는 내부 분기용 보존 |
| BUG-31 | PIN→이메일 로그인 전환 미동작 | ✅ 수정 + 배포 완료 (2026-03-28) | pin_login_screen.dart: logout 후 `pushNamedAndRemoveUntil('/')` → 루트 이동, AuthGate가 로그인 화면 표시 |
| BUG-32 | 분석 대시보드 엔드포인트 한글 미표시 | ✅ 수정 완료 (2026-03-30) | analytics.py _ENDPOINT_LABELS 40개 누락 전수 등록 (30→90개) |
| BUG-33 | 릴레이 재완료 시 KeyError: 0 서버 에러 | ✅ 수정 완료 (2026-03-30) | _worker_restarted_after_completion() RealDictCursor dict 접근 — row[0]→row.get('last_start') |
| #48 | 재활성화 권한 체크 `in` 비교 방향 버그 | ✅ 수정 완료 (2026-03-30) | company_base 추출 (접미사 제거) + 비교 방향 통일. TMS(M)/TMS(E) 재활성화 허용. 테스트 10/10 passed |
| #52 | ETL 변경이력 `_FIELD_LABELS` finishing_plan_end 누락 | ✅ 수정 완료 (2026-03-31) | admin.py _FIELD_LABELS에 `finishing_plan_end: 마무리계획일` 추가. VIEW 마무리계획일 조회 400 에러 해소 |
| #51 | progress API에 `sales_order` 필드 추가 | ✅ 완료 (2026-03-31) | progress_service.py CTE+SELECT+sn_map 3곳 추가. regression 23 passed |
| 52 | TM 체크리스트 Phase 1 — Partner 검수 시스템 | ✅ 완료 (2026-04-01) | migration 043 + checklist_service.py + TM API 3개 + Admin CRUD 4개 + task 알림 + FE 화면. 테스트 39/39 passed |
| 53 | 알림 소리 + 진동 — 포그라운드 알림 피드백 | ✅ 완료 (2026-04-02) | Web Audio API 비프음 5종 + navigator.vibrate + 프로필 설정 드롭다운. 패키지 추가 0 |
| 52-A | TM 체크리스트 보완 — COMMON seed + scope 수정 | ✅ 완료 (2026-04-02) | migration 043a + COMMON 15항목 + item_type 컬럼 + scope='all' 기본값 |
| 54 | 공정 흐름 알림 트리거 — partner 분기 + admin_settings | ✅ 완료 (2026-04-02) | process_validator + task_service + migration 044 + FE 설정 UI. 테스트 30/34 (4 FE skip) |
| 52-BF | TM 체크리스트 BUG-FIX #1~#6 | ✅ 수정 완료 (2026-04-02) | #1~#5 + #6 알림 메시지 [S/N\|O/N] 포맷 + 팝업 QR 행 제거 |
| 31C-A | PI 위임 모델별 옵션 — pi_delegate_models | ✅ 완료 (2026-04-03) | allowlist 방식. GAIA/DRAGON 위임, SWS GST PI 직접. 테스트 18/18 passed |
| 53 | monthly-summary API weeks + totals 집계 | ✅ 완료 (2026-04-03) | 금요일 기준 주차-월 매핑 + MECH/ELEC/TM completed/confirmed. 테스트 18/18 passed |
| 54 | 체크리스트 성적서 API — O/N 검색 + S/N 성적서 | ✅ 완료 (2026-04-03) | _get_checklist_by_category 공통 추출 + report/orders + report/{sn} 배치 쿼리. 테스트 19/19 passed |
| BUG-34 | 체크리스트 master_id 응답 누락 | ✅ 수정 (2026-04-03) | _get_checklist_by_category items에 master_id 추가 → FE 토글 정상 |
| BUG-35 | #53 monthly-summary mech_start→mech_end 필터 | ✅ 수정 (2026-04-03) | mech_end 기준 + NULL fallback. GBWS-6905 등 3월 시작→4월 종료 제품 포함 |
| 54-FE | TM 체크리스트 description 표시 | ✅ 완료 (2026-04-03) | 항목명 아래 검사방법/기준 fontSize 10 silver |
| BUG-6 | 다중작업자 동료 resume 403 FORBIDDEN | ✅ 수정 완료 (2026-04-07) | work.py — task coworker 허용 → Sprint 55에서 worker별 pause로 근본 해결 |
| 55 | Worker별 Pause/Resume + Auto-Finalize | ✅ 완료 (2026-04-07) | 개인별 pause, 전원 relay auto-finalize, FINAL task 릴레이 불가. 테스트 27/27 + regression 28/28 |
| INFRA-1 | Migration 자동 실행 시스템 | ✅ 완료 (2026-04-08) | migration_runner.py + migration_history 테이블. 앱 시작 시 미실행 migration 순차 적용. 041~045 운영 적용 완료 |
| TEST-AL20 | Alert 20종 전체 검증 테스트 | ✅ 완료 (2026-04-08) | test_alert_all20_verify.py 38TC (36 passed, 2 skipped). 검토 후 is_relay 버그 등 3건 수정. TC-PR-20 assert 수정 |
| 55-B | Task 목록 API my_pause_status 누락 | ✅ 완료 (2026-04-09) | work.py get_tasks_by_serial() work_pause_log JOIN 추가. 테스트 5/5 + regression 8/8 passed |
| 56 | QR 목록 API elec_start 필드 + 필터 | ✅ 완료 (2026-04-09) | qr.py 4곳 수정. QR regression 23/23 passed |
| #55 | 비활성 사용자 목록 노출 수정 | ✅ 완료 (2026-04-09) | admin.py workers/managers/출퇴근 API에 is_active=TRUE 필터. migration 040 운영 실행 |
| 57 | ELEC 공정 시퀀스 변경 + 체크리스트 | ✅ 완료 (2026-04-09) | INSPECTION freeroll, IF_2 FINAL, Dual-Trigger 닫기, 체크리스트 31항목, migration 046/046a. 테스트 13/13 + TM regression 3/3 |
| BUG-36 | Dual 제품 TANK_MODULE 일괄 처리 | ✅ Sprint 57-C 수정 (2026-04-10) | get_incomplete_tasks qr_doc_id 옵션 + TMS qr_doc_id 필터. DUAL L/R 독립 완료 판정 |
| 57-C | ELEC seed 교체 + SELECT/INPUT 스키마 | ✅ 완료 (2026-04-10) | migration 047. 실제 전장외주검사성적서 31항목 + select_options/selected_value/input_value + qr_doc_id UNIQUE. 34/34 passed |
| 57-FE | ELEC 체크리스트 FE 연동 | ✅ 완료 (2026-04-10) | startTask/completeTask Record 반환, _kFinalTaskIds 동기화, ElecChecklistScreen 신규, 체크리스트 버튼 ELEC 확장, 2차 배선 judgment_phase 수정 |
| BUG-37 | TM DUAL L/R 체크리스트 분리 | ✅ Sprint 57-D 수정 (2026-04-10) | upsert_tm_check qr_doc_id 파라미터 + FE 6곳 qrDocId 전달 |
| BUG-38 | ELEC SELECT TUBE 색상 드롭다운 | ✅ 코드 완료 → QA 검증 | DropdownButton 구현 완료. 실기기 QA 필요 |
| BUG-39 | QI 공정검사 ELEC 2차 체크 | ✅ Sprint 57-E 수정 (2026-04-10) | _isQiBlocked role 검증 + _hasChecklistAccess QI 포함 + initialPhase=2 |
| BUG-40 | 체크리스트 버튼 시작 시 미활성 | ✅ Sprint 57-E 수정 (2026-04-10) | _hasChecklistAccess TM/ELEC/QI in_progress 확장 |
| 30-BE | 성적서 API ELEC Phase + TM DUAL | ✅ 완료 (2026-04-10) | get_checklist_report ELEC Phase 1+2 자동분리 + TM DUAL L/R + 진행률 재활용. 33/33 passed |
| 58-BE | check_elec_completion + confirmable + ELEC status | ✅ 완료 (2026-04-13) | Phase 1+2 합산, confirm_checklist_required 토글, /elec/{sn}/status. 36/36 passed |
| 59-BE | TM qr_doc_id 정규화 | ✅ 완료 (2026-04-14) | _check_tm_completion SINGLE DOC_{S/N} + DUAL L/R, get_checklist_report 통합, 레거시 UPDATE. 37/37 passed |
| 60-BE | ELEC 마스터 정규화 | ✅ 완료 (2026-04-15) | phase1_applicable + qi_check_required + remarks 컬럼, 문자열 추론 제거, 마스터 API 확장. migration 048. 42/43 passed |
| 61-BE | 알람 강화 + 미종료 작업 API 확장 | ✅ 완료 (2026-04-17) | sn_label() O/N 통일, 에스컬레이션 3종, pending API 확장, SETTING_KEYS +5, migration 049. 29/29 passed |
| 61-BE-B | BUG-44 보완 + #60 company / #61 force_closed 필드 | ✅ 완료 (2026-04-17, v2.9.5) | admin.py + work.py 7개 포인트 반영. VIEW Sprint 33 FE-15 선행 조건 해소 |
| FEAT-1 | 사용자 행위 트래킹 + 분석 대시보드 | ✅ BE Sprint 32 완료 (2026-03-19) | `app_access_log` 테이블 + analytics API 4개 + 30일 정리 스케줄러. VIEW 분석 대시보드는 별도 Sprint |
| BUG-41 | PWA 업데이트 시 PIN 초기화 + 이메일 재입력 요구 | 🟡 BACKLOG (우선순위 보류) | Chrome PWA 환경에서 업데이트 후 PIN 로그인 화면 대신 초기 이메일 로그인 화면으로 진입, 이메일 전체 재입력 필요. 변경 범위/regression 리스크 대비 우선순위 낮음 — 아래 "BUG-41 상세" 섹션 참조 |
| SEC-01 | 인프라 시크릿/CORS 정리 (H-04 + H-05) | 🟡 BACKLOG (리팩토링 후 착수) | SECURITY_REVIEW.md H-04(CORS `origins="*"`) + H-05(JWT/DB/Refresh fallback 하드코딩). 코드 LOC 과대 → REF-BE-13(auth_service.py 분할) 이후 착수 권장. 아래 "SEC-01 상세" 섹션 참조 |
| BUG-42 | 명판 소형 QR 접사 인식 실패 | 🔴 OPEN | 기본 카메라로는 문자열 정상 읽힘 / OPS 앱 스캐너(html5-qrcode)는 미인식. 명판 QR 이미지 크기가 스티커 대비 작아 매크로 포커스 + 고해상도 + 줌 필요. 아래 "BUG-42 상세" 섹션 참조 |
| BUG-43 | 분석 대시보드 기능별 사용량 한글 라벨 누락 (24건) | ✅ 수정 완료 (2026-04-17) | Sprint 52+ 체크리스트/성적서/ELEC 엔드포인트 등 24개 `_ENDPOINT_LABELS` 미등록 → 전수 등록. 기존 111키 → 135키 (유니크 108 라우트 커버) |
| BUG-44 | OPS 미종료 작업 목록 0건 반환 (Admin/Manager 양쪽) | ✅ 수정 완료 (2026-04-17) | `get_pending_tasks()` INNER JOIN → LATERAL JOIN (work_start_log FK). Claude×Codex 교차 검증 합의. 29/29 passed |
| HOTFIX-01 | force_close/force_complete TypeError (naive vs aware datetime) | ✅ 수정 완료 (2026-04-17) | `completed_at` + `started_at` 양쪽 naive→KST aware 정규화. force_close + force_complete 2곳 적용. Claude×Codex 합의: completed_at이 진짜 원인. 29/29 passed |
| BUG-45 | VIEW 강제 종료 INVALID_REQUEST (close_reason 필드 미스매치) + 완료 시각 검증 부재 | ✅ 수정 완료 (2026-04-17, v2.9.6) | BE: `force_close_task()` 미래 시각(60s skew) + started_at 이전 가드 14줄 + docstring Returns 2건. FE-17: VIEW `useForceClose.ts` L24 `reason → close_reason`. pytest TC-FC-11~18 8/8 GREEN, 회귀 TC-FC-01~10 + admin 46건 모두 GREEN. force_complete는 Advisory(미호출 엔드포인트) |
| TEST-CONTRACT-01 | VIEW↔BE API 필드 계약 자동 검증 테스트 도입 | 🟡 BACKLOG (중간, 재발 방지 Advisory) | BUG-45 후속 — `close_reason`/`reason` 같은 필드명 미스매치를 CI 단계에서 자동 차단. 과거 유사 사례: `is_pinned`/`priority` (공지), `qr_doc_id`, `taskId` snake/camel. 본건은 Bug fix 아닌 **재발 방지 구조 개선** → 기존 BUG-45 배포에 영향 없음. 설계: `AGENT_TEAM_LAUNCH.md` TEST-CONTRACT-01 섹션 (pytest + JSON Schema 우선, OpenAPI/Pact는 후보안). 등록: 2026-04-17 |
| HOTFIX-02 | 체크리스트 마스터 API `checker_role` 키 노출 누락 (Sprint 60-BE 후속) | ✅ 수정 완료 (2026-04-17) | `backend/app/routes/checklist.py` `list_checklist_master()` SELECT 절에 `cm.checker_role` + 응답 dict에 `'checker_role': row.get('checker_role') or 'WORKER'` 2줄 추가 + docstring Response 스펙 동기화. 증상: VIEW 체크리스트 관리 JIG 14 row 전체 WORKER 뱃지 (원래 7 WORKER + 7 QI 분리 필요). OPS #59-B DONE / VIEW FE-18 ✅. 상세: `AGENT_TEAM_LAUNCH.md` Sprint 60-BE 후속 핫픽스 섹션 |
| HOTFIX-03 | 비활성 task(is_applicable=FALSE) 조회 필터 누락 — 미시작 카운트 오염 | ✅ 수정 완료 (2026-04-17) | `backend/app/models/task_detail.py` `get_tasks_by_serial_number()` + `get_tasks_by_qr_doc_id()` 두 함수의 4개 SELECT 쿼리 모두 `AND is_applicable = TRUE` 추가. 방안 A 채택 (제품 결정: 비활성 task는 일반 조회 응답에서 완전 제외). 증상: Heating Jacket task 비활성 설정에도 VIEW S/N 상세뷰에서 "미시작 1건"으로 카운트. OPS #60 BUG DONE. VIEW FE 수정 불필요. 관리자 전체 조회가 필요해지면 추후 `?include_inactive=true` 파라미터(방안 C)로 확장 |
| HOTFIX-04 | 강제종료 표시 누락 종합 (Case 1: Orphan work_start_log "진행중" 오표시 + Case 2: 미시작 강제종료 시 worker 라인·시각·사유 소실) | ✅ BE 수정 완료 (2026-04-17, v2.9.8 — pytest 9 신규 + 24 회귀 = 33/33 GREEN) | **범위 확장 (Twin파파 2026-04-17)**: 기존 Case 1(Orphan wsl) + Case 2(미시작 강제종료 — 가압검사 등 모든 task 유형 적용) 통합 수정. **방안 B + 확장 A 통합 + M2 옵션 C' 재확정**: ① Case 1 — BE `work.py` `get_tasks_by_serial()` workers SQL에 `app_task_details` JOIN + `COALESCE(wcl.completed_at, td.completed_at)` + `CASE ... WHEN td.completed_at IS NOT NULL THEN 'completed'` + `is_orphan`/`task_closed_at` 메타필드. ② Case 2 — **옵션 C' (장기 시스템 원칙 반영)**: `TaskDetail` 모델에 `closed_by_name` 런타임 필드 1개 신규 + `from_db_row()` 1줄 + `get_tasks_by_serial_number()`·`get_tasks_by_qr_doc_id()` SELECT 5곳에 `LEFT JOIN workers` 추가 → `_task_to_dict()`에서 `close_reason`/`closed_by`/`closed_by_name` 3키 자동 노출. **M1 정정 반영**: `force_closed`/`closed_by`/`close_reason` 3필드는 이미 TaskDetail dataclass L67~L69 + from_db_row L104~L106에 존재 → 중복 추가 없음, `closed_by_name` 1개만 신규. **M2 정정 반영**: Codex 1차 권고 옵션 A(후처리 루프)는 단기 해법이라 반려 → 옵션 C'(모델 필드 + SELECT JOIN) 채택. 이유: 새 응답 경로 확장 시 모델 불변·쿼리만 추가하면 자동 일관, APS-Lite 타겟 원칙 부합. **A1 반영**: TC-FORCECLOSE-NS-03(혼재) / NS-04(legacy backward-compat) / NS-05(Case 1+2 경계 중첩) 추가. **A2 불필요**: 이름이 모델 단계 바인딩이라 worker_ids 세트 확장 불요. **M1 COALESCE 미반영(옵션 α)**: worker row `duration_minutes` NULL 유지 — Orphan worker 개별 작업시간 관측 불가, `td.duration_minutes` fallback 시 복수 worker에서 N배 부풀림 → garbage 방지. **회귀 안전**: `SELECT *` → `SELECT td.*, w.name AS closed_by_name` — `td.*`로 기존 컬럼 보존·LEFT JOIN이라 row 유지. 타 조회 경로(scheduler/admin 통계/checklist/production/gst/factory) 쿼리 미변경 → `closed_by_name=None` 자동. **VIEW FE 소폭 변경 포함**: `ProcessStepCard.tsx` 2곳 수정(taskStatus 분기 + workers=[] placeholder 렌더) + `types/snStatus.ts` 2필드 추가. placeholder 문구 "강제 종료 · 작업 이력 없음 · 처리: 김*규(마스킹) · KST 시각 · 사유: 원문" (FE-19). OPS FE 변경 없음. 배포 즉시 박*현/김*욱(Case 1) + TM 모듈 가압검사(Case 2) 등 기존 데이터 자동 복구, DB backfill 불필요. 설계 상세: `AGENT_TEAM_LAUNCH.md` HOTFIX-04 섹션 / FE 상세: `AXIS-VIEW/VIEW_FE_Request.md` FE-19. 등록: 2026-04-17 / 설계 확정: 2026-04-17 (범위 확장) / Codex 재검증 M1·M2·A1·A2 반영: 2026-04-17 |
| HOTFIX-05 | Admin 옵션 미종료 작업 카드 시간 UTC 오표시 (`.toLocal()` 누락) | ✅ 수정 완료 (2026-04-17, v2.9.7) | `frontend/lib/screens/admin/admin_options_screen.dart` L2474 `DateTime.tryParse(...)?.toLocal()` 1줄 추가. 증상: BE가 `+09:00` offset 포함 ISO 응답을 반환하나 Dart `DateTime.tryParse()`가 내부 UTC로 저장 → 게터가 UTC 값 반환 → "2026-04-01 06:41" 표시 (KST 15:41이 정답). `manager_pending_tasks_screen.dart` L353은 이미 `.toLocal()` 적용되어 있어 화면 간 불일치. FE only, BE/DB 영향 없음 |
| DOC-SYNC-01 | OPS_API_REQUESTS.md / VIEW_FE_Request.md 잔여 PENDING 15건 실구현 상태 교차 검증 | ✅ 검증 완료 (2026-04-17) | **Explore 에이전트 15건 일괄 검증 + Twin파파 확정 반영**: 13/15 ✅ DONE 확정(#40/#41/#46 상세뷰 workers/#48-A/#48-B/#51/#52/#54/#55/#56-A ELEC API/#56-B confirm_checklist_required 연동/#57 성적서 Phase+DUAL 분기/FE-08) → 헤더 업데이트 완료. 1/15 🟡 BACKLOG(장기)(#22 SI_SHIPMENT 로직 미구현 — Twin파파 2026-04-17 확정: 테스트 완료 설비 1건으로 운영 영향 미미, 실출하 데이터 누적 시점에 Sprint 배정. BE factory.py + VIEW FE `si` 필드 분리 동시 필요). 1/15 🟡 보류(#42 `role=pm` — Twin파파 2026-04-17 보류, PM 권한 분기 실제 필요 시점에 재검토). 1/15 🟡 의도된 BACKLOG(FE-16 미종료 작업 전용 페이지 — FE-15 운영 보고 재판단). 각 항목 상세 검증 메모는 `AXIS-VIEW/OPS_API_REQUESTS.md` / `AXIS-VIEW/VIEW_FE_Request.md`의 해당 헤더 하단 블록 참조 |
| FIX-24 | OPS 미종료 작업 카드에 O/N(sales_order) 뱃지 표시 | ✅ 수정 완료 (2026-04-18, v2.9.9) | **OPS 전용** (VIEW는 이미 `salesOrder` 기준 분류되어 대상 아님). 대상 파일 2개: `frontend/lib/screens/admin/admin_options_screen.dart` `_buildPendingTaskCard()` L2467+ / `frontend/lib/screens/manager/manager_pending_tasks_screen.dart` `_buildTaskCard()` L346+. Twin파파 요청 "sn만 보이는데 on도 같이 보이면 좋을거 같아". BE `work.py` pending-tasks 응답에 `sales_order` 이미 포함(L1750/L1839) → **BE 변경 0줄, FE only**. 패턴: S/N Row에 `if (salesOrder.isNotEmpty) ...[Icon(receipt_long) + Text(salesOrder)]` conditional spread, 약 6줄×2파일. 회귀 위험 매우 낮음. HOTFIX-04(BE+VIEW)와 파일 겹침 없어 병행 가능. 설계 상세: `AGENT_TEAM_LAUNCH.md` FIX-24 섹션. 등록: 2026-04-17 / Sprint 착수: 2026-04-17 |
| TECH-REFACTOR-FMT-01 | VIEW 날짜 포맷 함수 중앙 유틸 통합 (format.ts) | 🟡 BACKLOG (부분 진행 — 1/3 선승격 완료, 2건 대기) | **VIEW FE only — 기술 부채 정리**. **진행 상황 (2026-04-17)**: FE-19(HOTFIX-04 연계) 착수 전제로 `formatDateTime` 1건 **선승격 완료** — `ChecklistReportView.tsx` L25 로컬 함수 → `utils/format.ts`로 이관 + import 교체 (Codex 지적 #1 옵션 A 채택). **남은 2건 (여전히 BACKLOG)**: ① `QrManagementPage.tsx` L52 `formatDate` / ② `InactiveWorkersPage.tsx` L33 `formatDate`. 두 `formatDate`는 출력 포맷(`YYYY-MM-DD`) 동일하나 **null fallback 상이** (`'—'` vs `'없음'`) → 중앙 유틸에 `fallback` 옵션 인자 설계 필요(`formatDate(iso, fallback = '—')` 시그니처). 추가로 invalid Date 가드(`isNaN(d.getTime())`) + 단위 테스트 신설이 본 BACKLOG 핵심. 마이그레이션 前 여유 스프린트에 일괄 처리. 회귀 위험 낮음(순수 함수). 최초 등록: 2026-04-17 / 부분 진행: 2026-04-17 (formatDateTime 1건) / 우선순위: 중간 |
| TEST-CLEAN-CORE-01 | 강제종료 시 실행 측정값 미생성 회귀 가드 pytest | 🔴 OPEN (2026-04-20 신규 등록, 우선순위: 중간-상) | **BE 회귀 테스트 only — 클린 코어 데이터 원칙 자동화**. 목적: `PUT /admin/tasks/<id>/force-close` 호출 후 `work_start_log` + `work_completion_log` 두 테이블에 **row가 추가되지 않음**을 CI 단계에서 자동 검증. 인수 기준: ① 호출 전 wsl/wcl count 스냅샷 → 호출 후 count 동일 (delta=0) ② `app_task_details.completed_at` + `force_closed=TRUE` + `close_reason` + `closed_by` 4필드만 세팅 확인 ③ `duration_sec` NULL 유지 확인 ④ Case 1(Orphan wsl 기존 존재) 시 기존 wsl 보존·wcl는 여전히 0건 확인. 테스트 파일: `tests/backend/api/test_force_close_clean_core.py` 신규. 예상 TC 5개(정상 task / Case 1 orphan / Case 2 미시작 / 이미 종료된 task 재호출 / legacy closed_by IS NULL). 회귀 영향: 기존 force-close 동작 변경 없음, 순수 검증 추가. **Why (긴급도)**: 원칙은 문서에 있어도 미래에 "UI 편의상 wsl에 dummy row 추가" 같은 PR이 들어오면 리뷰어가 놓칠 수 있음 → pytest가 자동 차단. APS-Lite 데이터 무결성 1차 방어선. 연계: `BACKLOG.md` 상단 📐 설계 원칙 — 클린 코어 데이터 / `AGENT_TEAM_LAUNCH.md` HOTFIX-04 📐 설계 원칙 블록. 작업 주체: VSCode 터미널 (Claude + Codex 교차검증). 예상 소요: 구현 25분 + 교차검증 15분 = 40분. 최초 등록: 2026-04-20 |
| FIX-25 | VIEW 상세뷰·O/N 리스트에 협력사명 + line 노출 (progress API 단일 확장, v4 Codex M1 반영) | ✅ BE 구현 완료 (2026-04-20, v2.9.10 — progress_service.py touch 6줄/net 0, pytest 42/42 GREEN), VIEW FE-20/FE-21 착수 대기 | **BE + VIEW FE 연계 건 — progress API 단일 확장 기반 v4 (Codex M1 breaking change 지적 반영)** (Twin파파 2026-04-20 "BE 코드 클린 코어" 원칙 적용 사례). **요구**: (1) 상세뷰 MECH/ELEC/TMS 카테고리 헤더에 담당 회사명 동반 표시 (PI/QI/SI는 GST 자체검사 고정, 라벨 없음). (2) 생산현황 O/N 카드·S/N 상세뷰 헤더에 `plan.product_info.line` 노출 (혼재 시 "F16 외 N" 표기 — **FE 계산**). **⚠️ v1~v3 폐기 이력**: v1(task_detail 2쿼리 + production 거미줄 LEFT JOIN, 모델 무시) → v2(CTE 집계, BE·FE 집계 중복) → v3(`work.py` tasks 응답을 List→Dict 래핑 + production LEFT JOIN) 단계적 개선. **v3 치명적 결함 (Codex M1)**: 설계서 예시 `response = {'tasks': [...], 'product_info': {...}}` 가 실제 `work.py:718` `return jsonify(task_list), 200` **리스트 응답과 불일치** → 구현 시 VIEW `snStatus.ts getSNTasks()` (`Array.isArray(data)` 체크) + OPS `task_service.dart:102~112` (List/Map 양면 파서) 모두 동시 breaking. **v4 전환 결정적 발견 (실측 재조사)**: `progress_service.py` L65~67에 이미 `pi.mech_partner` / `elec_partner` / `module_outsourcing` **3필드 SELECT 중** + L296~299 `sn_data.pop(...)` 으로 응답에서만 제거 중 (주석 원문 "응답에서 partner 필드 제거 (내부용)"). 권한 숨김 목적이 아닌 my_category 계산용으로만 쓰고 버리는 상태. **v4 채택안 (progress API 단일 확장)**: ① `progress_service.py` **1파일만 수정**. ② CTE + 메인 SELECT 에 `pi.line` 1줄씩 추가(2줄). ③ `_aggregate_products()` dict 조립에 `'line': row['line']` 1줄 추가. ④ L296~299 pop 3줄 **제거**. → touch 6줄 / **net 0줄(+3 -3)**. ⑤ tasks API(`work.py`) / production.py / `models/product_info.py` **전부 무변경** → v3 breaking 원천 차단. OPS FE 영향 0건(`sn_progress_screen.dart:44` progress API 사용 중이나 `Map<String, dynamic>.from(e)` 방식이라 신규 키 4개 추가 파싱 무영향). **FE (별도 세션 — 터미널 Codex 교차검증 후)**: `SNProduct` 인터페이스 4필드 확장 + `SNDetailPanel` 카테고리 헤더 JSX + `SNStatusPage` `groupedByON` useMemo 로 per-O/N `line` 최빈값 집계. `ProcessStepCard.tsx` switch key 는 `'TMS'` (DB 실측). **변경 요약**: v1 ~150줄 → v2 ~60줄 → v3 ~40줄 → **v4 6 touch줄 / net 0줄**. 거미줄 지수 🔴 → 🟡 → 🟢 → **🟢 (JOIN 증가 0)**. Breaking 위험 🔴 → 🟡 → 🔴(v3 M1) → **🟢 (tasks API 무변경)**. **하위 호환**: `/api/app/product/progress` products 요소에 4키 추가만, 기존 필드 변경 0건. 마이그레이션 0건. 모델 수정 0줄. **NULL 처리 (클린 코어 원칙)**: NULL·빈 문자열 → FE에서 생략 렌더, placeholder 주입 금지. **Twin파파 확정사항**: ① module_outsourcing 실질 고정값 "TMS" ② S/N 채번 시 협력사 배정 완료 → NULL 사실상 없으나 방어 코드 유지 ③ line 변경 이력 추적 불요. **테스트 (TC 6개, `test_progress_service.py`)**: TC-PROGRESS-PI-01(일반) / -02(4필드 NULL) / -03(GST 자체생산) / -04(Admin 전체) / -05(company_override 협력사 필터) / -06(O/N 혼재 per-S/N line — BE는 per-S/N만, 집계는 FE-21 스테이징). 회귀: SELECT 컬럼 추가 + pop 제거뿐이라 row 수·다른 필드 무변경. **검증 API 경로**: `curl /api/app/product/progress | jq '.products[0] | {mech_partner, elec_partner, module_outsourcing, line}'` + `curl /api/app/tasks/<sn>?all=true | jq 'type'` 로 여전히 `"array"` 확인 (v3 breaking 방지). 설계 상세: `AGENT_TEAM_LAUNCH.md` FIX-25 섹션 (v4 전환 근거 + 4-way 비교표 포함) / VIEW FE 상세: `AXIS-VIEW/VIEW_FE_Request.md` FE-20 + FE-21 (**v4 대응 수정은 터미널 Codex 교차검증 완료 후 별도 커밋**). 작업 주체: VSCode 터미널 (Claude + Codex 교차검증, breaking change 완전 철회 확인도 Codex 재검증). 예상 소요 (v4 기준): BE 구현 15min + 테스트 45min + 검증 30min + Codex 재검증 30min = **약 2시간** (v3와 큰 차이 없으나 breaking 위험 0 + OPS FE 파싱 회귀 부담 제거(사용 중이나 추가 전용 변경)로 실측 위험가중 소요 감소). 최초 등록: 2026-04-20 / v2 재설계: 2026-04-20 / v3 Codex 교차검증: 2026-04-20 / v4 Codex M1(tasks breaking) 반영: 2026-04-20 |
| FE-ALERT-BADGE-SYNC | 홈 화면 알림 배지 카운트 `/alerts` 복귀 시 즉시 동기화 (UX 개선) | 🟡 BACKLOG (재검토 후 진행, 2026-04-22 등록) | **OPS FE only — `frontend/lib/screens/home/home_screen.dart` 2곳 수정**. 현재 diff(미커밋 working copy): AppBar 알림 아이콘(L587~593) + 메뉴 리스트 '알림' 항목(L760~770) 의 `onPressed`/`onTap` 을 `async` 로 변경 + `await Navigator.pushNamed` 후 `ref.read(alertProvider.notifier).refreshUnreadCount()` 호출 추가. 목적: `/alerts` 화면에서 읽음 처리 후 홈 복귀 시 배지 카운트 즉시 갱신 (기존에는 stale). 초기 진입 시에는 이미 `initState → _initializeAlerts → refreshUnreadCount` 호출됨(L70)으로 이번 변경은 "다녀온 뒤 재갱신"만 보완. **⚠️ 현재 "메인에 배지 없음" 증상은 이 변경과 무관**: `app_alert_logs` 4-17 이후 0건 장애의 결과 (`unreadCount = 0` 이라 배지 정상적으로 미표시). Scheduler 알람 복구(`HOTFIX-SCHEDULER-DUP-20260422` 계열) 후 배지 자연 복귀 예정. **재검토 사항**: ① 변경 완결성 — `refreshUnreadCount()` 외 `fetchAlerts()` 도 필요한가? ② 회귀 — 빠른 연속 탭 시 race condition 가능성 ③ WebSocket push 와 중복 호출 가능성. **배포 조건**: (a) Scheduler 장애 복구 완료 후 배지 정상 복귀 확인 → (b) 실기기 QA (iOS/Android/데스크톱 PWA) → (c) flutter build web + Netlify 배포. 작업 소요: 재검토 15분 + 배포 30분 = 45분. 최초 발견: 2026-04-22 HOTFIX-SCHEDULER-PHASE1.5 세션 중 미커밋 working copy 로 확인 |
| HOTFIX-SCHEDULER-PHASE1.5-LOGGING | Alert 경로 silent fail ERROR 로깅 + Sentry 임시 연동 (2026-04-22 등록) | ✅ 🟢 COMPLETED (배포 + 결정적 포착 완료, 2026-04-22) | **결정적 성과**: 5일 알람 장애의 근본 원인을 배포 직후 단일 hourly tick (02:00 UTC) 에서 포착. `[alert_insert_fail]` / `[alert_create_none]` 로그 4건 + 공통 에러 `column "task_detail_id" of relation "app_alert_logs" does not exist` 로 G.3 + A 동시 확정. 이후 §11.14.7 / §12 recovery SQL 실행 근거가 됨. 관련: `AXIS-OPS/ALERT_SCHEDULER_DIAGNOSIS.md` §11.14.6 / `AXIS-OPS/AGENT_TEAM_LAUNCH.md` HOTFIX-SCHEDULER-PHASE1.5 섹션 |
| HOTFIX-ALERT-SCHEMA-RESTORE-20260422 | Railway 운영 DB 스키마 복구 (049 수동 적용) | ✅ 🟢 COMPLETED (2026-04-22 11:25 KST) | Phase 1.5 로 확정된 "migration 049 prod 미적용 + task_detail_id 컬럼 부재 + enum 3종 미등록" 문제 SQL 수동 복구. 5 블록 실행 (enum 3 + column + index + admin_settings + migration_history). 검증 A/B/C 3종 PASS. 12:00 KST tick 에서 신규 INSERT 16건 (id=658~673) 확인. 5일간 0건 장애 완전 해소. 관련: `AXIS-OPS/ALERT_SCHEDULER_DIAGNOSIS.md` §12.6 / `AXIS-OPS/AGENT_TEAM_LAUNCH.md` HOTFIX-ALERT-SCHEMA-RESTORE-20260422 섹션 |
| HOTFIX-SCHEDULER-DUP-20260422 | APScheduler 중복 실행 방지 — Option 2 fcntl file lock | ✅ 🟢 COMPLETED (2026-04-22, VIEW/OPS BE Sprint 완료) | **R1 쿼리로 확정 (2026-04-22 12:40 KST)**: RELAY_ORPHAN 16건 중 5 unique serial_number 가 중복 기록 (GBWS-6980/7017/7024/7038 각 2중복 + GPWS-0773 3중복). gap_ms 18~86ms 범위로 동시 실행 race condition 확정. Worker ≥3 추정 (GPWS-0773 triple). 중복율 37.5% (6/16). **해결책**: `app/__init__.py` (또는 `scheduler_service.py`) 에 `fcntl.flock LOCK_EX | LOCK_NB` 기반 `/tmp/axis_ops_scheduler.lock` 파일 락 도입. 기존 `_SCHEDULER_STARTED` env 가드는 보조 유지. GPWS-0773 3중복 근거로 Option 3 (Redis distributed lock) 병행 검토 권고. 관련: `AXIS-OPS/ALERT_SCHEDULER_DIAGNOSIS.md` §11.7.4 / §11.14.7 / `AXIS-OPS/AGENT_TEAM_LAUNCH.md` HOTFIX-SCHEDULER-DUP-20260422 섹션 |
| HOTFIX-ALERT-SCHEDULER-DELIVERY-20260422 | Scheduler 알람 delivery 복구 — 표준 패턴 + 배치 dedupe | ✅ 🟢 COMPLETED (2026-04-22, VIEW/OPS BE Sprint 완료) | 4 HOTFIX 중 마지막 건. delivery 파이프라인 표준 패턴 통일 + 배치 단위 dedupe 로직 반영. PHASE1.5 (관찰성) + SCHEMA-RESTORE (복구) + DUP (중복 방지) 와 함께 알람 장애 종결의 마지막 축. 관련: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` HOTFIX-ALERT-SCHEDULER-DELIVERY-20260422 섹션 (L30178) |
| POST-REVIEW-HOTFIX-PHASE1.5-20260422 | 긴급 HOTFIX Phase 1.5 배포 사후 Codex 교차검토 | ✅ **CLOSED** (2026-04-23 Phase A 일괄 검토 완료) | Codex 판정: Q1-1 A (direct caller 공통 wrapper 권고, `OBSERV-ALERT-SILENT-FAIL` 흡수) / Q1-2 N (Sentry import guard 안전) / Q1-3 A (영구 승격 시 구조화 payload, `OBSERV-ALERT-SILENT-FAIL` 흡수). blocking defect 없음. 관찰성 목적 달성. |
| POST-REVIEW-HOTFIX-DUP-20260422 | HOTFIX-SCHEDULER-DUP 배포 사후 Codex 교차검토 | ✅ **CLOSED** (2026-04-23 Phase A 일괄 검토 완료) | Codex 판정: Q3-1 N (현재 Railway 단일 hostname 환경에서 fcntl 가정 성립) / Q3-2 A (loser-path fd leak — 신규 `FIX-FCNTL-FD-CLOSE` 등록) / Q3-3 A (`_SCHEDULER_STARTED` dead state 정리 — 신규 `FIX-SCHEDULER-STARTED-DEAD-STATE` 등록) / Q3-4 A (Redis scale-out 트리거 조건부 — replica>1 전환 시 이관). 중복 방지 핵심 성립. |
| POST-REVIEW-HOTFIX-SCHEMA-RESTORE-20260422 | HOTFIX-ALERT-SCHEMA-RESTORE 사후 Codex 교차검토 (2026-04-22 등록) | ✅ **CLOSED** (2026-04-23 Phase A 일괄 검토 완료) | Codex 판정: Q2-1 A (runbook drift — migration_history `ON CONFLICT (filename) DO NOTHING` 추가 권고, admin_settings 키 불일치 sync 권고) / Q2-2 A (migration 049 prod 미적용 가설은 "prod artifact/deploy-path 문제" 가장 유력 — `POST-REVIEW-MIGRATION-049-NOT-APPLIED` 선행 재료) / Q2-3 A (`OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION` 우선순위 > `OBSERV-MIGRATION-HISTORY-SCHEMA`). 복구 유효. runbook re-sync는 advisory 수준. |
| POST-REVIEW-HOTFIX-DELIVERY-20260422 | HOTFIX-ALERT-SCHEDULER-DELIVERY 사후 Codex 교차검토 (2026-04-22 등록) | ✅ **CLOSED** (2026-04-23 v2.10.2 FIX-CHECKLIST-DONE-DEDUPE-KEY 로 M1 해소) | Codex 판정: **Q4-4 M** (CHECKLIST_DONE_TASK_OPEN dedupe key 오류 — 같은 S/N 복수 ELEC task open 시 alert suppress 버그) → **v2.10.2 PATCH 로 수정 완료**. Q4-1 A (role 경로 company 필터 — 신규 `SEC-ROLE-COMPANY-FILTER` 등록) / Q4-2 A (CHECKLIST_DONE index miss + RELAY_ORPHAN `message LIKE` — **v2.10.2 동시 수정 완료**) / Q4-3 A (N+1 — `REFACTOR-SCHEDULER-SPLIT` 흡수) / Q4-5 A (48h 관찰 SQL 권고, 실행 권장). |
| FIX-CHECKLIST-DONE-DEDUPE-KEY | v2.10.2 — CHECKLIST_DONE_TASK_OPEN + RELAY_ORPHAN dedupe 키 교정 (Codex 사후 Q4-4 M + Q4-2 A) | ✅ **COMPLETED** (2026-04-23, v2.10.2) | **BE 2곳 수정 + 신규 TC-61B-19B**. (1) `scheduler_service.py:1064~1070` CHECKLIST_DONE dedupe 에 `AND task_detail_id = %s` 추가 — 같은 S/N 내 복수 ELEC task(IF_1/IF_2) alert suppress 버그 해소. (2) `scheduler_service.py:883~913` RELAY_ORPHAN dedupe `message LIKE` → `task_detail_id` 기반 전환 + INSERT dict 에도 task_detail_id 저장. (3) `test_sprint61_alert_escalation.py::test_tc_61b_19b_dedup_per_task_detail` 신규 — 회귀 가드. (4) setup fixture partner 보강 (mech_partner='FNI', elec_partner='TMS'). pytest 4/4 GREEN. 관련: `CHANGELOG.md` v2.10.2 / Codex POST-REVIEW-HOTFIX-BATCH 2026-04-23 |
| FIX-FCNTL-FD-CLOSE | HOTFIX-DUP loser-path fd leak 수정 (Codex 사후 Q3-2 A) | 🟡 OPEN (P2, 30분) | `backend/app/__init__.py:78-79,90-92` lock 획득 실패 분기에서 `os.open()` 으로 연 fd 가 close 안 됨 → loser-path fd leak. 수정: `except BlockingIOError` 및 일반 예외 분기에서 `_lock_fd` 를 `os.close()` 처리. 장기 운영 시 fd 고갈 리스크 방어. |
| FIX-SCHEDULER-STARTED-DEAD-STATE | `_SCHEDULER_STARTED` dead env state 제거 (Codex 사후 Q3-3 A) | 🟢 OPEN (P3, 15분) | `__init__.py:85` 에서 `_SCHEDULER_STARTED` 를 env 로 설정만 하고 실제 분기에서 읽지 않음 (fcntl 전환 후 dead state). 운영자 혼란 방지를 위해 read-path 복원 또는 제거. |
| SEC-ROLE-COMPANY-FILTER | PI/QI/SI role 경로 company 필터 누락 — cross-company leakage 리스크 (Codex 사후 Q4-1 A) | 🟠 OPEN (P2, 1h) | `process_validator.py:241-247` `get_managers_for_role()` 호출 경로에 company 제약 없음 → 현재 "PI/QI/SI = GST 단일 회사" 불문율에 의존. 향후 비GST PI/QI/SI manager 등장 시 타회사 alert 누출 가능. 수정: `get_managers_for_role()` 시그니처에 `company` 파라미터 추가 또는 명시적 WHERE 절 + 테스트 불변식 고정. |
| DOC-SCHEMA-RESTORE-RUNBOOK | SCHEMA-RESTORE runbook drift 보정 (Codex 사후 Q2-1 A) | 🟢 OPEN (P3, 30분) | `AGENT_TEAM_LAUNCH.md:29811~29823` HOTFIX-ALERT-SCHEMA-RESTORE SQL Block 5 에 `ON CONFLICT (filename) DO NOTHING` 추가 + admin_settings Block 4 의 setting_key 를 실제 코드 (`admin.py:71-74`, `scheduler_service.py:942-945`) 와 동기화. 향후 runbook 재사용 시 실행 오류 방지. |
| FIX-ORPHAN-ON-FINAL-DELIVERY | v2.10.3 — ORPHAN_ON_FINAL alert target_worker_id 미지정 (HOTFIX-DELIVERY 숨은 4번째 경로) | ✅ **COMPLETED** (2026-04-24, v2.10.3) | **배경**: v2.10.2 배포 후 Codex Q4-5 48h 관찰 쿼리에서 ORPHAN_ON_FINAL 8건/4일 legacy NULL 포착 (2026-04-23~24 KST). 2026-04-22 HOTFIX-ALERT-SCHEDULER-DELIVERY 가 `scheduler_service.py` 3곳만 수정, `task_service.py:391~419` `complete_task` 내 `_create_alert_61(...)` 호출 경로를 놓침. 수정: `_resolve_managers_for_category` 재사용 + 관리자별 개별 INSERT. 관련: `CHANGELOG.md` v2.10.3 |
| CASCADE-ALERT-NEXT-PROCESS | ORPHAN_ON_FINAL 확장 — 현재 공정 관리자 + 다음 공정 담당자 동시 알림 (연쇄 차단 알림) | 🟢 **DRAFT** (P3, 사내 공정 활성화 후) | **설계 의도 (Twin파파 2026-04-24 확인)**: ORPHAN_ON_FINAL 은 단순 해당 카테고리 독려 알림이 아니라 **"다음 공정 진입 차단 통보"** 목적. 현재 v2.10.3 A안은 "해당 공정 관리자만" 이라 설계 의도 일부만 충족. **완전판 매핑** (유추 — Twin파파 추후 확정): MECH→PI / ELEC→PI / TMS→MECH(GAIA) / PI→QI / QI→SI / SI→종료. **보류 사유**: 사내 공정 (PI/QI/SI) 활성화 계획 **변동사항 많음** — 현장 운영 안정 시까지 대기. **착수 조건**: (1) PI/QI/SI 담당자 지정 방식 확정 (role 전체 vs is_manager 만) (2) TMS→MECH GAIA 특수 분기 최종 스펙 (3) 사내 공정 실제 가동 결정. **예상 작업**: `task_service.py` + `scheduler_service.py` 양쪽 ORPHAN_ON_FINAL INSERT 에 next_category 매핑 추가 + `NEXT_PROCESS_MAP` 상수 신설 + TC 추가. 예상 소요 2~3h. |
| POST-REVIEW-MIGRATION-049-NOT-APPLIED | 왜 migration 049 가 Railway prod DB 에 적용되지 않았는가 조사 | ✅ 🟢 COMPLETED (v2.10.8, 2026-04-27) | **산출**: `POST_MORTEM_MIGRATION_049.md` — 4가지 가설 전수 검증 → 가설 ① (DATABASE_URL) ❌ 기각, ② (코드 버그) ❌ 기각, ③ (raise) ❌ 모순 (049 미적용 + 050 적용은 raise 흐름과 충돌), **④ (Docker artifact/Railway build cache) 가장 유력** (Codex POST-REVIEW Q2-2 판정 일치). 결정적 증거 미확보 (4-17~22 Railway image build log 무료 tier 보존 X). **재발 방지 (v2.10.8 동시 적용)**: (1) `assert_migrations_in_sync()` 함수 신규 — disk vs DB sync 검증, gap 시 `sentry_sdk.capture_message` (2) migration_runner 실패 시 `sentry_sdk.capture_exception` (3) 신규 BACKLOG `INFRA-DEPLOY-HEALTH-CHECK` 권장 (선택). 본 보고서 산출로 종결 |
| OBSERV-ALERT-SILENT-FAIL | Phase 1.5 임시 ERROR 로깅 → 영구 반영 + Sentry 정식 연동 | ✅ 🟢 COMPLETED (v2.10.8, 2026-04-27) | **BE — sentry-sdk[flask]>=2.0 requirements 정식 추가 + `_init_sentry()` __init__.py L12+ 신규 (~50 LOC)**. DSN env 없으면 graceful skip (로컬/test 호환). FlaskIntegration + LoggingIntegration (INFO breadcrumb / ERROR event). release auto-binding (version.py). send_default_pii=False (PII 보호). 환경변수: SENTRY_DSN(필수), SENTRY_ENVIRONMENT(기본 production), SENTRY_TRACES_SAMPLE_RATE(기본 0.0). migration_runner.py 실패 시 capture_exception, assert_migrations_in_sync gap 시 capture_message. **Twin파파 측 후속 (배포 후)**: (1) sentry.io 가입 + Python/Flask project 생성 + DSN 발급 (2) Railway env SENTRY_DSN 추가 (3) Sentry alert rule 설정 (level=error + message contains "[migration-assert]" or "[scheduler]"). **검증**: Railway logs `[sentry] initialized (env=production, release=2.10.8)` 출력 + Sentry test event 자동 발송 |
| OBSERV-MIGRATION-HISTORY-SCHEMA | migration_history 에 success/error_message/checksum 컬럼 추가 | 🟡 OPEN (P2, 중간) | 현재 스키마 3컬럼 (id/filename/executed_at) 으로 실패 관찰 불가. 추가: `success BOOLEAN NOT NULL DEFAULT TRUE` + `error_message TEXT NULL` + `checksum VARCHAR(64) NULL`. migration_runner.py 의 INSERT 절도 동반 수정. checksum 은 migration 파일 내용의 SHA-256 → 배포 간 불일치 감지 가능. 예상 소요 2~3h (migration + runner 수정 + 검증) |
| ~~OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION~~ (DUP) | 앱 부팅 시 migration 상태 assertion + drift 알림 | ✅ **COMPLETED — L356 entry 참조** (DUP 정리 2026-04-27) | 본 row 는 중복 entry. v2.10.8 완료 trail 은 L356 의 COMPLETED entry 에 통합. 본 row 는 정합성 sync 위해 보존하되 L356 우선 |
| INFRA-COLLATION-REFRESH | Postgres collation mismatch 경고 해소 | ✅ 🟢 COMPLETED (2026-04-30 — `ALTER DATABASE railway REFRESH COLLATION VERSION;` 1줄 218ms 실행, collversion 2.36 → 2.41 갱신, WARNING 0건 입증) | Railway 호스트 OS glibc 업그레이드 (2.36 → 2.41) 로 발생한 mismatch. 영향: 운영 무관 (WARNING only, 텍스트 정렬 순서 잠재 차이만). Twin파파 측 SQL 1줄 실행으로 close. NOTICE: changing version from 2.36 to 2.41 / ALTER DATABASE / 218 msec |
| UX-SPRINT55-FINALIZE-DIALOG-WARNING | "내 작업만 종료" 마지막 참여자 경고 다이얼로그 (2026-04-22 등록, **1차 보완**) | 🟡 OPEN (P2, 이번 주 내) | **FE only — `frontend/lib/screens/task/task_detail_screen.dart` `_showCompleteDialog()` 확장**. 현장 호소: "내 작업만 종료 눌렀는데 task 가 닫혀서 재참여 불가" (2026-04-22 O/N 6588 GBWS-6978/6979/6980 UTIL_LINE_2 — 이영식/서명환 사례). **원인 확정**: Sprint 55 (3-B) `auto_finalize` — `not finalize` 모드에서도 `_all_workers_completed(task.id)` True 시 task 자동 종료. 버그 아니고 설계대로 동작(progress 실시간 정확도 목적). 다만 "내 작업만 종료" 문구와 실제 동작 괴리 → UX 혼란. **해결**: 다이얼로그 진입 시 현재 참여자의 completion 상태 pre-check → 본인이 partial close 하면 auto-finalize 발동 예정인 경우 **2차 확인 문구** 추가: "⚠️ 현재 다른 참여자 전원이 종료 상태입니다. 당신이 마지막 참여자이므로 이 버튼을 누르면 task 가 자동 종료됩니다. (추후 재개 필요 시 관리자에게 재활성화 요청)". **BE 변경 필요**: `/api/app/tasks/<sn>` 또는 `/api/app/task/<id>` 응답에 `is_last_active_worker: bool` 플래그 추가 (work_start_log 찍힌 전원이 completion_log 있고 본인만 active 상태인지 판정). 작업 소요: FE 30분 + BE 30분 + 테스트 15분 ≈ 1.5h. **오늘 이슈의 80% 를 해소하는 최소 비용 조치**. 관련: `AXIS-OPS/BACKLOG.md` UX-SPRINT55-FINALIZE-DIALOG-WARNING + `backend/app/services/task_service.py` L292-304 auto_finalize 분기 |
| FEAT-SPRINT55-REACTIVATE-HYBRID-ROLE | manager+worker hybrid role 의 PWA 내 재활성화 버튼 (2026-04-22 등록) | 🟡 OPEN (P2, 다음 Sprint) | **FE + BE 연계 — 이영식(manager+worker hybrid) 사용 경험 최적화**. 현재: 이영식(manager) 이 완료된 task 를 다시 열려면 AXIS-VIEW 콘솔 로그인 → task 검색 → 작업재활성화 버튼 클릭 (5분 마찰). **제안**: PWA task 상세 화면 `_buildCompletedBadge()` 옆에 **role 조건부 [재활성화] 버튼** 노출. 조건: `worker.role IN ('MANAGER', 'MECH+MANAGER', 'ELEC+MANAGER', ...)` 인 경우만. 1-tap → 기존 VIEW 재활성화 API (`/admin/tasks/<id>/reactivate` 등) 호출 + audit log 기록 (→ `OBSERV-ADMIN-ACTION-AUDIT` 연계). 버튼 UX: 확인 모달 필수 ("이 작업을 재활성화하시겠습니까? 완료 상태가 해제됩니다."). **비용**: FE 버튼 1개 + 조건부 노출 로직 + BE 엔드포인트 재사용 (신규 0). 작업 소요 반나절. **이득**: 오늘처럼 manager 가 hybrid 로 있는 케이스에서 VIEW 왕복 제거. BE 재활성화 API 가 이미 있는지 먼저 확인 필요 (없으면 별도 Sprint). 관련: `AXIS-OPS/BACKLOG.md` FEAT-SPRINT55-REACTIVATE-HYBRID-ROLE |
| FEAT-SPRINT55-REACTIVATE-REQUEST-FLOW | worker → manager 재활성화 요청 flow (2026-04-22 등록, **2차 보완**) | 🟢 OPEN (P3, 중기) | **BE + FE + VIEW 3-way 구현 — 현장 worker-manager 협업 완전체**. 시나리오: 일반 worker(non-manager)가 완료된 task 에 재참여 필요 → 현재 플로우 "카톡으로 manager 에게 요청 → manager VIEW 로그인 → 수동 재활성화" (마찰 큼). **신규 flow**: (1) PWA 완료 task 카드 → [재개 요청] 버튼 → 사유 입력 모달 → POST `/api/app/task/<id>/reactivate-request` (2) VIEW 상단 알림 배지 + AXIS-VIEW 전용 요청 목록 페이지 (3) manager 1-tap 승인 → 기존 재활성화 API 내부 호출 + 요청자에게 push 알림 (4) 승인 거절 시 사유 회신. **새 테이블**: `task_reactivate_requests (id, task_detail_id, requester_id, reason, status, approver_id, approved_at, rejected_reason, created_at)`. **새 엔드포인트 3개**: POST 요청 생성 / GET 대기 목록 (manager only) / PATCH 승인·거절. **FE**: PWA 재개요청 버튼 + 모달 + 내 요청 상태 조회. VIEW: 요청 목록 페이지 + 알림 widget. **작업 소요**: 1~1.5일 full-stack. **전제**: `FEAT-SPRINT55-REACTIVATE-HYBRID-ROLE` 먼저 배포해서 manager-hybrid 케이스 해결 후 진행 (non-hybrid worker 남은 케이스 대응). `OBSERV-ADMIN-ACTION-AUDIT` 와 통합 (요청/승인 모두 audit log 기록). 관련: `AXIS-OPS/BACKLOG.md` FEAT-SPRINT55-REACTIVATE-REQUEST-FLOW |
| DOC-AXIS-VIEW-REACTIVATE-BUTTON | AXIS-VIEW "작업재활성화" 버튼 존재·영향 범위 문서화 (2026-04-22 등록) | 🟢 OPEN (P3, 30분) | **문서 정리 only**. 2026-04-22 UTIL_LINE_2 조사 중 Q1 의 `first_worker_id=NULL` + started_at 갱신 이력을 미스터리로 접근했다가 Twin파파가 "VIEW 에 재활성화 버튼 존재" 확인해 해소. 다음 번 비슷한 조사 시간 낭비 방지용 기록. **수정 대상**: `AXIS-OPS/memory.md` 상단 "📍 주요 관리 기능" 섹션 신설 or `AXIS-OPS/CLAUDE.md` 관리자 기능 블록. **내용**: (1) AXIS-VIEW 에 task 재활성화 버튼 존재 (위치·권한·호출 API 명시) (2) 재활성화 시 DB 상태 변화: `started_at=NULL, completed_at=NULL, worker_id=NULL, total_pause_minutes 잔존 가능` (3) 기존 start_log/completion_log 는 보존 — 재활성화 이후 새 시작 시 새 row 추가 (4) 재활성화 가 의도된 기능임 (우회가 아님) (5) 재활성화 이력은 현재 audit log 부재 → `OBSERV-ADMIN-ACTION-AUDIT` 연계. 예상 소요 30분. 관련: `AXIS-OPS/BACKLOG.md` DOC-AXIS-VIEW-REACTIVATE-BUTTON |
| OBSERV-ADMIN-ACTION-AUDIT | 관리자 액션 audit log 테이블 도입 (2026-04-22 등록) | 🟡 OPEN (P2, 독립 Sprint) | **BE 신규 인프라 — 관찰성 gap 해소**. 2026-04-22 UTIL_LINE_2 조사 중 Q7 `SELECT * FROM admin_audit_log` 실행 시 `relation "admin_audit_log" does not exist` (42P01) 에러로 확인: **AXIS-VIEW 재활성화 등 admin destructive/corrective 액션에 audit 기록 인프라 부재**. 누가 언제 어떤 task 를 재활성화했는지 DB 추적 불가. **스키마 초안**: `CREATE TABLE admin_audit_log (id BIGSERIAL PK, actor_user_id INT NOT NULL, actor_email TEXT, action TEXT NOT NULL, target_table TEXT NOT NULL, target_id BIGINT NOT NULL, before_state JSONB, after_state JSONB, reason TEXT, ip_address INET, user_agent TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())` + index `(target_table, target_id)` / `(actor_user_id, created_at DESC)`. **적용 범위**: (1) task 재활성화 (2) task 강제 종료 (HOTFIX-04 force-close) (3) worker 강제 로그아웃 (4) pause 강제 해제 (5) admin_settings 변경 (6) role 승격/강등 etc. **연동 방식**: Flask `before_request` + `after_request` middleware 에서 자동 snapshot 기록 (해당 blueprint 범위: `/admin/*` mutation 라우트). 수동 호출 불필요. **수반 이득**: (i) 향후 데이터 미스터리 조사 시간 5~10분 → 30초 (ii) 다중 관리자 환경 책임 추적 (compliance) (iii) Sprint 45 INFRA-1 migration runner 관찰성 부재와 동일 유형의 blind spot 해소. **작업 소요**: migration 1개 + middleware ~30~50줄 + 기존 admin 라우트 점진 적용 → 초기 구현 2h + 전 admin 라우트 적용 추가 2h. **관련 BACKLOG**: `FEAT-SPRINT55-REACTIVATE-HYBRID-ROLE` / `FEAT-SPRINT55-REACTIVATE-REQUEST-FLOW` 배포 전 선행 권고. 오늘 조사 근거: `AXIS-OPS/BACKLOG.md` OBSERV-ADMIN-ACTION-AUDIT |
| FIX-DB-POOL-MAX-SIZE-20260427 | DB Connection Pool 사이즈 보정 (MAX=20→30, MIN=5 유지, env 변경 only, 2026-04-27 등록) | 🟡 PHASE A APPLIED → B 관찰 중 (P1, 2026-04-27 KST 배포) | **Railway env 1개 변경 + 코드 변경 0**. 트리거: 4-25 토 새벽 (UTC 22:29 / KST 07:29) Pool exhausted 다발 사례 + 사용자 ≥120명 / peak 07:30~09:00, 16:30~17:00 출근 burst 패턴 확정. **4 라운드 advisory review (Codex 1차 + Claude Code 2차 + Codex 3차 + Twin파파 fact-check 4차) 로 약점 12건 정정 후 최종 산정**. ⚠️ 라운드 4 결정적 정정: 기존 prod env 가 **이미 MIN=5/MAX=20 운영 중** (코드 default 1/10 가정 X). 이번 변경은 MAX 만 20→30. **per-worker 독립 pool 구조** (init_pool() in create_app() — gunicorn -w 2 fork 시 각 worker 독립) → Worker A (scheduler owner) 15 conn + Worker B (HTTP only) 10 conn 필요 → MAX=30 채택 (per-worker × 2 = 총 60, Postgres 100 중 62% 점유). **결정적 데이터 (Q-B)**: 2026-04-21 화 출근 burst 측정 — peak 31 동시 in-flight, 21 동시 17회 빈번. **MAX=20 환경 측정 결과** = peak 31 시 worker당 ~16 → fallback 1건/peak (라운드 4 정정, 라운드 3 의 ~100건/일 추정 무효), MAX=30 이면 fallback 0. **MIN=5 유지**: 이미 운영 중이었으므로 cold-start 효과는 기존부터 적용된 상태. max_age=300s 5분 후 lazy 재생성 race 로 일시적 MIN 미달 가능 — 별건 OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP (P3 격하) 에서 5분 간격 SELECT 1 cron 으로 보강. **미래 dimensioning**: MAX=30 = 미래 2x (62 in-flight) 까지 안전, 사용자 600명 (5x) 도달 시 MAX=70~80 + Postgres tier 상향 / PgBouncer 도입 검토 필수. **Phase A** (✅ 2026-04-27 KST 완료): Railway env `DB_POOL_MAX=20→30` 변경, MIN=5 유지 → 자동 재배포 ~1분 → logs 에서 `Connection pool initialized: min=5, max=30` 확인. **Phase B** (3일 관찰 중, 화/수/목): Pool exhausted grep + Q-B 재측정 (off-peak 12:00 권장, O(N²) 부담 회피) + pg_stat_activity 정밀 SQL (pid+client_addr 로 worker A/B 분리). **Phase C** (D+3 이후 조건부): 0 fallback 종료 / 1~5건 시 40 ↑ / 10+건 시 50 ↑ + leak audit. **사용자 영향**: 7일 Q5 결과 slow_req≥5s = 0건 (사용자 체감 0). **롤백**: env 1개 복원 (30→20) → 자동 재배포 ~1분, 코드 영향 0. 설계 상세: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` FIX-DB-POOL-MAX-SIZE-20260427 섹션 (약점 trail 12건 + 4라운드 검증 기록 포함) |
| OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP-20260427 | DB Pool warmup cron — MIN=5 강제 유지 (P3 → P2 격상, 2026-04-27 실측 입증) | ✅ 🟢 COMPLETED 확정 (v2.10.7 + D+1 PASS, 2026-04-28 — 옵션 X1 유지, HOTFIX-06b 불필요) **D+1 (4-28 화 출근 peak) 측정 결과**: Pool exhausted 0 / direct conn fallback 0 / OPS conn 6~7 안정 / Sentry 새 issue 0 → per-worker 함정 영향 무, Worker A warmup 만으로 사용자 영향 0 보장 입증. v2.10.11 HOTFIX-06b (per-worker warmup) **진행 불필요**, OBSERV-WARMUP 정식 완료. 이전 | **BE only — `backend/app/services/scheduler_service.py` 에 `_pool_warmup_job` 신규 추가**. **2026-04-27 KST 실측으로 P3 → P2 격상**: Phase A (DB_POOL_MAX=30 + MIN=5) 적용 후 OPS conn 추세 측정 — 10:14 (10 conn) → 10:19 (9 conn, -1) → 10:24 (7 conn, -3 누적). max_age=300s 만료 + lazy 재생성 race 로 MIN=5 사실상 무효 입증 (Codex 라운드 3 A4 advisory 가 10분만에 실측 확정). **해결**: APScheduler 의 5분 간격 cron job 으로 풀 안 모든 conn 에 SELECT 1 실행 → max_age 시계 리셋 → 자발적 폐기 방지 → MIN=5 강제 유지 → 영구 10 conn (5 × 2 worker) 보장. **구현 ~30 LOC**: `_pool_warmup_job()` 함수 + `scheduler.add_job(..., interval=5분)` 등록 1줄. **위험도 매우 낮음**: 기존 코드 변경 0 / fcntl lock 이미 1 worker 만 scheduler / DB 부하 SELECT 1 × 5 conn × 12회/시간 = 60 query/시간 (무시 가능) / 회귀 위험 ↓ / 롤백 git revert 1 commit. **신규 pytest TC**: warmup 호출 후 conn 수 유지 검증 + 회귀 11 job GREEN. **검증**: 배포 후 매 5분 pg_stat_activity 측정 → conn=10 영구 유지 확인 (현재 7로 감소 중). **부수 효과**: TTFB 15s 안정성 ↑ (별건 OBSERV-RAILWAY-HEALTH 일부 자연 해결 가능). 설계 상세: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP-20260427 섹션 |
| FIX-DB-POOL-WARMUP-WATCHDOG-20260430 | warmup_pool() 의 `_pool=None` 분기 logger.debug → logger.error 격상 + pid context, Sentry 자동 capture (4-29 23:31 silent failure 재발 방지) | ✅ 🟢 COMPLETED (v2.10.16, 2026-04-30 — db_pool.py L266 1줄 격상 + 신규 TC test_warmup_logs_error_when_pool_none, pytest 4/4 PASS) |
| HOTFIX-09-ACCESS-LOG-CLEANUP-NAMEERROR-20260501 | `_cleanup_access_logs()` 의 `get_db_connection` import 누락 — Sprint 32 도입 (3-19) 후 43일간 매일 03:00 NameError silent failure | ✅ 🟢 COMPLETED (v2.10.17, 2026-05-01 — `scheduler_service.py` L1122 1줄 추가 + Codex 라운드 1 합의 trail [Q1 S3 N / Q4 TC 4개 보강 / Q5 framing 정정 — Sprint 32 design/QA 부족 + Sentry 는 latent defect 탐지 layer], 신규 pytest TC 4개 PASS [import / SQL pattern / 정상 흐름 / 예외 rollback], 5-02 03:00 cron 부터 정상 작동) |
| OBSERV-SCHEDULER-IMPORT-AUDIT-20260501 | scheduler_service.py 의 모든 cron 함수 import 패턴 audit + 표준 통일 (lazy import 11개 vs module-top vs `_get_db_connection()` helper) | 🟢 OPEN (P3, 30분, MECH 체크리스트 후순위) | **Codex 라운드 1 Q2 M 권고 (HOTFIX-09 사후 검토)**. 트리거: HOTFIX-09 (Sprint 32 도입 후 43일 silent failure) 와 동일 패턴 재발 위험. **현황**: scheduler_service.py 의 12개 함수 중 11개가 함수 본체 lazy import 사용 (`from app.models.worker import get_db_connection`), 1개 (`_cleanup_access_logs`) 만 누락됐던 사고. 다른 service 파일 (duration_validator/alert_service 등) 은 대부분 module-top import. **권고**: (1) services/ 전체 grep audit (`grep -rn "from app.models.worker import get_db_connection" backend/app/services/`) — 1회 (2) 표준 통일 — module-top import 일괄 적용 또는 `_get_db_connection()` helper 1개로 감싸서 ad hoc import 회피. **선행 의존성 0**, MECH 체크리스트 후 진행. 예상 30분 |
| INFRA-LINT-PRECOMMIT-HOOK-20260501 | flake8/pyflakes/ruff pre-commit hook 도입 — F821 (undefined name) 등 NameError 사전 차단 | 🟢 OPEN (P3, 1h, MECH 체크리스트 후순위) | **Codex 라운드 1 Q3 M 권고 (HOTFIX-09 사후 검토)**. 트리거: HOTFIX-09 의 NameError 가 lint-time 에 catch 가능했음 (Python 의 `undefined name` 은 F821/E0602 로 표시됨). 현재 리포에는 lint 운용 흔적은 있으나 상시 hook 체계 부재. **권고**: (1) `.pre-commit-config.yaml` 신설 또는 기존 보강 (2) `ruff` (가장 빠름) 또는 `flake8 + pyflakes` 조합 (3) `pre-commit install` 가이드 README 명시. **선행 의존성 0**. 본 hook 도입 시 향후 동일 NameError silent failure 사전 차단 → 인프라 신뢰성 ↑. 예상 1h (config + 기존 코드 lint 결과 audit + fix) |
| OBSERV-DB-POOL-STATUS-ENDPOINT-20260429 | `/api/admin/db-pool-status` endpoint 신설 — pg_stat_activity conn 수 + cumulative_fallback + warmup_last_run 실시간 조회 | 🟢 OPEN (P3, **MECH 체크리스트 우선 → 후순위**, 30분 BE) | **BE only — `backend/app/routes/admin.py` 신규 endpoint**. 트리거: 2026-04-29 사용자 측 conn 추세 측정 시 자동 모니터링 인프라 부재 발견 (Sentry 는 error/event 만 추적, conn 수 같은 numerical metric 은 별도 도구 필요). **기능**: (1) pg_stat_activity SQL 로 OPS conn 수 + state + age + idle_for 측정 (2) `db_pool.get_direct_fallback_count()` (v2.10.13 도입) cumulative counter 응답 (3) warmup_pool 의 마지막 실행 시각 + warmed/requested ratio (4) pool config (MIN/MAX/workers). **응답 예시**: `{ "pool_config": {"min": 5, "max": 30}, "current_conn": 5, "cumulative_fallback": 12, "warmup_last_run": "2026-04-29T22:43:00+09:00" }`. **인증**: `@admin_required`. **연계**: 추후 Admin 화면에 카드 추가하면 실시간 시각화 가능 (FE 별건). **회귀 위험 0** (read-only endpoint). **소요**: BE 30분 + pytest 1 TC 10분. 관련: 4-29 22:40 사용자 측정 (conn=3 일시 변동 발견) → 자동 모니터링 부재 인지 → 인프라 등록 |
| OBSERV-DB-POOL-CONN-THRESHOLD-ALERT-20260429 | conn 임계 미만 시 Sentry capture_message 자동 alert (5분 cron) | 🟢 OPEN (P3, **MECH 체크리스트 우선 → 후순위**, 20분 BE) | **BE only — `scheduler_service.py` 에 5분 cron job 추가 (~20 LOC)**. 트리거: peak 시간대 (07:30~09:00) conn < 5 (MIN 미달) 또는 cumulative_fallback ↑↑ 시 운영자 즉시 인지 필요. **기능**: 5분마다 pg_stat_activity COUNT(*) 측정 + 임계 검사: (a) peak 시간 (KST 07~09 / 17~18) conn < 5 → `sentry_sdk.capture_message(level='warning')` (b) cumulative_fallback 5분 delta > 50 → 동일 alert. **Sentry 활용**: warning level 이라 alert rule "level >= warning AND message contains [db_pool]" 로 필터. **선행**: 본 entry 와 OBSERV-DB-POOL-STATUS-ENDPOINT 와 묶음 배포 가능 (둘 다 conn 측정 SQL 공통). **회귀 위험 0** (cron 신규 추가, 기존 코드 무수정). **소요**: 20분 + pytest 1 TC. 관련: 본 BACKLOG 와 사용자 측 Sentry alert rule 설정 후 자동 운영 |
| OBSERV-SENTRY-TRACES-APM-ENABLE-20260429 | Sentry Performance APM 활성화 (Railway env `SENTRY_TRACES_SAMPLE_RATE=0.1` 1줄) | 🟢 OPEN (P3, **MECH 체크리스트 우선 → 후순위**, 5분) | **인프라 only — Railway env 변경 1줄 (코드 0)**. 트리거: 2026-04-29 사용자 측 conn 추세 모니터링 옵션 검토 시 latency 시계열 부재 발견. **기능**: `SENTRY_TRACES_SAMPLE_RATE=0.1` (10% sampling) → Sentry dashboard 에 transaction 별 latency 시계열 자동 추적 → conn 부족 시 latency p95 ↑ 간접 신호. **장점**: 코드 변경 0, 5분 셋업. **단점**: Sentry events 사용량 ↑ (free tier 100k/월 한도 점검 필요), conn 직접 추적 ❌ (latency 간접 추적). **검증**: 활성화 후 Sentry dashboard → Performance 탭 → /api/* transaction p50/p95/p99 시계열 확인. **선행 의존성 0**. 관련: OBSERV-RAILWAY-HEALTH-TTFB-15S-INTERMITTENT (별건 L345) 의 (b) 옵션과 동일. 본건은 **즉시 enable** + L345 는 추가 분석 |
| OBSERV-RAILWAY-HEALTH-TTFB-15S-INTERMITTENT | /health TTFB 15s intermittent 추적 + 외부 모니터링 도입 (2026-04-27 등록) | 🟡 OPEN (P2, 별건) | **외부 모니터링 도입 — direct conn fallback 의 +0.3~0.5s 지연이 TTFB 15s 의 일부 기여 가능성**. v2.10.4 Flutter health timeout 5s→20s 우회 적용으로 사용자 체감 해소했으나 근본 원인 미해결. **2026-04-27 측정**: Railway 자체 `/health` access_log 에 미기록 (middleware 제외), Q5 결과 slow_req≥5s = 0건. **연관 가설**: 1) Railway proxy 첫 TLS handshake 1~3초 + 2) DB pool exhausted 시 direct conn fallback +0.3~0.5s + 3) 클라이언트 SW sticky cache. **해결 방향**: (a) UptimeRobot or BetterStack 무료 tier 5분 간격 ping → 응답시간 시계열 외부 보관 + 부수 효과로 pool warmup. (b) Sentry Performance APM 도입 → /health 자체 응답시간 측정. **선행 검증**: FIX-DB-POOL-MAX-SIZE-20260427 (Pool 30 + MIN 5) 배포 후 fallback 빈도 0 도달 시 → TTFB 15s 자연 해결 여부 확인. 자연 해결 안 되면 외부 모니터링 도입. 예상 소요: UptimeRobot 30분 / Sentry 2~3h. 관련: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` FIX-DB-POOL-MAX-SIZE-20260427 섹션 |
| OBSERV-SLOW-QUERY-ENDPOINT-PROFILING | Slow query endpoint level profiling (2026-04-27 등록 / **2026-05-04 heavy endpoint 확정**) | 🟡 OPEN (P2, 별건 — heavy endpoint 식별 완료, 코드 audit 단계만 잔여) | **Pool 사이즈 무관 — slow query 자체 분석**. 2026-04-21~27 Q-A 결과: 화/수 p99≥1초 burst 9건 발생, 특히 (1) **Tue 19:00 — 353 req max 2495ms** (출근 peak 수준 부하 + max 2.5초, 이례적), (2) **Wed 00:00 — 239 req max 1211ms** (자정에 비정상 부하, cron/batch 후보), (3) Tue 13/14/15/16/17/19시 + Wed 09/10/16/18시 p99 1~2초. **분석 범위**: 각 burst 시점 endpoint 별 분류 → heavy endpoint 식별 → 쿼리 최적화 또는 timeout 적용 결정. **수단**: app_access_log 의 request_path GROUP BY + duration_ms 분포 분석. **선행 의존성 없음**, FIX-DB-POOL-MAX-SIZE-20260427 와 병행 가능. **작업**: SQL 분석 30분 + 후속 endpoint 별 코드 audit 1~2h + 최적화 Sprint 별도 등록. **🎯 2026-05-04 측정 결과 — heavy endpoint 단독 확정**: Railway 차트 p99 3초 spike 추적 SQL 3종 결과 **`work.complete_work` POST 가 단독 hot spot**. Top 6 hourly p99 시점 중 5건이 work.complete_work, 가장 큰 4-30 15:00 KST: max **2,668ms** / avg **2,181ms** / n=4 (4건 평균이 2초 넘음 = 일시적이 아니라 그 시간대 일관 부하). 4-30 09:00 max 2,253ms n=11 = Restart 직후 cold start (4-30 09:30 Railway Restart 와 30분 윈도우 일치, 4-29 23:31 silent failure 복구). 4-30 14~16시 burst = 평일 오후 출하 마감 시간대 다중 작업자 동시 완료. 5-04 10:00 max 1,722ms = admin1234 batch fetch 시점 일치. **추정 원인 3종** (audit 대상): ① 알람 + scheduler trigger 다발 (RELAY_ORPHAN/CHECKLIST_DONE/UNFINISHED_AT_CLOSING + WebSocket broadcast 동시) ② work_completion_log + app_task_details + workers JOIN + duration_validator + process_validator 호출 chain ③ Restart 직후 connection pool warm-up 미완료 + direct conn fallback (+0.3~0.5s) 누적. 부수 hot endpoint: production.get_performance (4건, 528~847ms) / factory.get_monthly_kpi (1건, 2,110ms) / analytics.get_by_worker (1건, 647ms). **5xx 0건 7일 입증** — 진짜 ERROR 없음, slow latency 만 잔존. Railway 차트 4-30 1.3% error rate spike + 3초 p99 spike 동일 시점 = 동일 burst 의 두 측면 (5xx 아닌 slow 200 응답). 관련 데이터: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` FIX-DB-POOL-MAX-SIZE-20260427 의 Q-A 섹션 (Slow Top 5) + 5-04 측정 SQL 3종 (Hourly p99 spike 추적 + 4-29~5-01 윈도우 500ms 이상 + 7일 4xx/5xx 분석) |
| FIX-PIN-FLAG-MIGRATION-SHAREDPREFS-20260427 | PIN 등록 플래그 SecureStorage → SharedPreferences 이전 (자동 마이그레이션, 2026-04-27 등록) | 🔴 OPEN (S2, 30분, 즉시 착수) | **FE only — `frontend/lib/services/auth_service.dart` 단일 파일 수정**. 트리거: 2026-04-26 Twin파파 PC sticky cache 조사 중 PIN 화면 손실 가설 입증 — `pin_registered` 플래그가 `flutter_secure_storage` (encrypted IndexedDB) 에 저장 중. **PWA 환경에서 SW 업데이트 / 캐시 정책 변경 / iOS Safari 7일 idle 정책 등으로 IndexedDB 손실 시 → main.dart 라우팅 EmailLoginScreen 으로 빠짐 → 비번 모르는 사용자 막힘**. 동일 파일의 `device_id` 는 이미 `SharedPreferences` (localStorage) 사용 중인데 PIN 플래그만 비대칭. **수정 함수 2개**: (1) `hasPinRegistered()` — 양쪽 read + 자동 마이그레이션 (SharedPrefs 우선, fallback SecureStorage 발견 시 자동 이전 + 옛 entry 정리) (2) `savePinRegistered(bool)` — SharedPreferences 에 직접 쓰기 + SecureStorage 잔존 정리. **logout 흐름 (L243)** 도 양쪽 cleanup 추가. **마이그레이션 호환성**: 기존 사용자 영향 0 (옛 SecureStorage 'true' 자동 발견 → SharedPreferences 이전 후 PinLoginScreen 으로 정상 진입). **검증 시나리오 3개**: (1) 신규 사용자 PIN 등록 (2) 기존 사용자 자동 마이그레이션 (3) SW 업데이트 후 IndexedDB 손실 시뮬레이션. **Post-deploy 1주 관찰 지표**: EmailLoginScreen 진입 빈도 ↓ + PIN 재등록 빈도 ↓ → ~0~1건/일 기대. **Rollback**: git revert + flutter build web + Netlify (단방향 마이그레이션이라 rollback 시 SharedPrefs 잔존 entry 와 SecureStorage 의 desync 가능, 'true' 통일이면 무관). 설계 상세: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` FIX-PIN-FLAG-MIGRATION-SHAREDPREFS-20260427 섹션 |
| FEAT-PIN-STATUS-BACKEND-FALLBACK-20260427 | Backend PIN 상태 자동 복구 layer (양쪽 storage 다 잃어도 자동 복구, 2026-04-27 등록) | ✅ 🟢 COMPLETED (v2.10.6, 2026-04-27) | **FE 분기 추가 — `frontend/lib/main.dart` 라우팅 분기 (L260~269 근처)**. FIX-PIN-FLAG-MIGRATION (1차 보호) 후 잔존 극단 케이스 (양쪽 local storage 다 잃은 경우) 대응. **현재 흐름**: hasPinRegistered() false → EmailLoginScreen (비번 모름 → 막힘). **변경 흐름**: hasPinRegistered() false 인데 hasRefreshToken() true → refresh 시도 → 성공 시 backend `/auth/pin-status` 조회 → registered=true 응답 → 로컬 플래그 복구 + PinLoginScreen ✅. **BE 엔드포인트 `/auth/pin-status` 이미 존재** (PROGRESS.md L2284 확인). **선행**: `FIX-PIN-FLAG-MIGRATION-SHAREDPREFS-20260427` 완료. **변경 LOC**: ~20 (main.dart 분기) + ~10 (auth_service.dart `hasRefreshToken()` helper). **수동 검증**: 로컬 storage 비우고 refresh_token 만 살린 상태 시뮬레이션. 설계 상세: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` FEAT-PIN-STATUS-BACKEND-FALLBACK-20260427 섹션 |
| AUDIT-PWA-SW-INDEXEDDB-PRESERVE-20260427 | PWA Service Worker IndexedDB 손실 경로 audit (2026-04-27 등록) | 🟡 OPEN (P2, 30분, 선택적) | **`frontend/web/flutter_service_worker.js` audit only**. PIN 플래그 손실 가설 검증 — Flutter PWA SW 가 IndexedDB 를 건드리는 코드 경로 있는지 확인. 표준 Flutter SW 는 cache versioning 만 하고 IndexedDB 안 건드리지만, 커스텀 또는 가능 시나리오 검증 필요. **audit 명령**: `grep -i "indexedDB\|deleteObjectStore\|deleteDatabase\|deleteStore" flutter_service_worker.js` + cache 정책 grep. **결과 분류**: 🟢 IndexedDB 직접 호출 0건 → 안전 (문서화만) / 🟡 caches.delete 패턴 → 영향 분석 / 🔴 deleteDatabase 발견 → 즉시 수정. **산출물**: `AXIS-OPS/docs/SW_INDEXEDDB_AUDIT_20260427.md` 또는 본 Sprint 섹션 사후 기록. 코드 변경 0 (audit only), 결과에 따라 후속 Sprint 트리거. 설계 상세: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` AUDIT-PWA-SW-INDEXEDDB-PRESERVE-20260427 섹션 |
| UX-LOGIN-FALLBACK-PIN-RESET-LINK-20260427 | EmailLoginScreen 에 PIN 재등록 요청 + 비번 재설정 link 추가 (2026-04-27 등록) | 🟢 OPEN (P3, 1h, FIX-PIN-FLAG-MIGRATION + FEAT-BACKEND-FALLBACK 완료 후 잔존 케이스 대응) | **FE only — `frontend/lib/screens/auth/email_login_screen.dart` 확장**. FIX-PIN-FLAG-MIGRATION + FEAT-BACKEND-FALLBACK 두 Sprint 후 잔존 극단 케이스 (refresh_token 도 잃은 경우) 사용자 안내 부재 해결. **추가 UI 2개**: (1) 비번 입력란 옆 "비밀번호를 잊으셨나요?" 링크 → 비번 재설정 안내 모달 (2) 화면 하단 "이전에 PIN 으로 로그인하셨나요? 관리자에게 PIN 재등록 요청" 안내 + 관리자 연락처 모달. **효과**: 첫 회 진입 사용자 방해 없음 / PIN 사용자 잘못 빠진 케이스 명확 안내 / 비번 잊은 사용자 stuck 회피. **선행**: 1번 + 2번 Sprint 배포 후 잔존 케이스만 대응. 관리자 PIN 재등록 흐름이 backend 에 이미 있어야 (없으면 별도 Sprint). 설계 상세: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` UX-LOGIN-FALLBACK-PIN-RESET-LINK-20260427 섹션 |
| FEAT-AUTH-STORAGE-MIGRATION-FULL-20260427 | refresh_token + worker_id + worker_data SharedPrefs 양방향 sync 이전 (Codex 1차 advisory 신규 권장, 2026-04-27 등록) | 🟡 OPEN (P2, 보안 trade-off 검토 필수) | **FE — `auth_service.dart` 의 SecureStorage 쓰는 4개 키 중 pin_registered 외 3개 (`refresh_token`, `worker_id`, `worker_data`) 도 SharedPreferences 양방향 sync 이전**. 트리거: Codex 1차 advisory — IndexedDB 일괄 손실 시 4개 키가 함께 사라지므로 pin_registered 만 옮긴 본 Sprint (FIX-PIN-FLAG-MIGRATION) 효과 영역 좁음. **보안 trade-off**: refresh_token 을 plaintext localStorage 에 두면 XSS 공격 표면 ↑. JWT 만료 5분 + refresh 7일 정책으로 영향 제한적이나 보안 검토 필수. **대안**: backend `/auth/pin-status` + `/auth/refresh` 흐름 재설계로 storage 의존도 낮추는 방향 (FEAT-PIN-STATUS-BACKEND-FALLBACK 와 통합 가능). **선행**: FEAT-PIN-STATUS-BACKEND-FALLBACK 배포 후 잔존 영향 측정 → 그래도 EmailLoginScreen 빠지는 cohort 있으면 본 Sprint 진행. **소요**: 보안 검토 1h + 코드 ~2h + pytest = 3~4h. 설계 상세: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` FIX-PIN-FLAG-MIGRATION-SHAREDPREFS-20260427 의 Limitation 섹션 |
| FIX-PROCESS-VALIDATOR-TMS-MAPPING-20260428 | duration_validator + scheduler_service 의 TMS 매핑 누락 fix — `resolve_managers_for_category()` public 함수 도입 (옵션 D-2 채택, 2026-04-27 등록 / 4-28 옵션 확정) | ✅ 🟢 COMPLETED (v2.10.11, 2026-04-28 — Codex 라운드 1 M=2/A=2/N=2 + 라운드 2 Q1/Q2 A 합의 모두 해소, pytest 신규 TC 7/7 PASS + 회귀 0건) | **BE only — `process_validator.py` 에 `resolve_managers_for_category(sn, category)` public 함수 신설 + scheduler_service 의 `_resolve_managers_for_category` 흡수 + duration_validator 3곳 표준 함수 호출로 통일**. **트리거**: 2026-04-28 03:00 KST (UTC 18:00) 매시간 정각 cron job 실행 중 Sentry 가 `Failed to get managers for role=TMS: invalid input value for enum role_enum: "TMS"` 에러를 도입 8시간만에 31 events / escalating 으로 자동 감지. **원인**: 4-22 HOTFIX-ALERT-SCHEDULER-DELIVERY 의 `_resolve_managers_for_category` 표준 패턴이 scheduler_service 에만 적용되고 duration_validator 3곳 (L74/L100/L179) 에는 미적용 → `get_managers_for_role(task.task_category)` 호출 → SQL `WHERE role='TMS'` → enum cast 실패. **role_enum 실측** (`migrations/006_sprint6_schema_changes.sql` L14): `'MECH'/'ELEC'/'TM'/'PI'/'QI'/'SI'/'ADMIN'` — **'TMS' 값 자체가 enum 에 없음**. CLAUDE.md L1131 'TMS(M)'/'TMS(E)' 는 `workers.company` 값. **Twin파파 SQL 검증**: `SELECT id FROM workers WHERE role='TM' AND is_manager=TRUE;` → 0건 (옵션 A 'TMS'→'TM' 매핑 폐기 확정). **영향 알람 4종**: ① UNFINISHED_AT_CLOSING ② DURATION_EXCEEDED ③ REVERSE_COMPLETION (모두 duration_validator) ④ task_service L583 은 target_source='PI'/'QI' 등 role 기반이라 무관. **회귀 영향 없음 알람**: RELAY_ORPHAN / TASK_NOT_STARTED / CHECKLIST_DONE_TASK_OPEN (이미 `_resolve_managers_for_category` 사용 중). **사용자 영향**: try/except PsycopgError 로 silent skip → HTTP 영향 0, 다만 **TMS 매니저 (module_outsourcing='TMS' 협력사 매니저) 가 UNFINISHED_AT_CLOSING 등 4종 알람 미수신** (4-22 target_role='TMS' 와 동일 구조 silent failure 재발). **누적**: 매시간 정각 ~10건 ERROR → 일일 ~240건 / 1주 ~1680건. **옵션 D-2 채택**: A('TMS'→'TM' 1줄, TM 매니저 0명이라 무효) / B(호출자에서 분기, DRY 위반) / C(scheduler_service 표준 함수 그대로 import, private 우회) / **D-2 (process_validator 로 이전 + public 화, DRY 깔끔, 4-22 본의도 정합) ✅ 채택**. **수정 범위 4 파일**: (1) `process_validator.py` +30 LOC (resolve_managers_for_category 신규 + _CATEGORY_PARTNER_FIELD dict 이전) (2) `scheduler_service.py` -15/+5 LOC (private 함수 제거 + import 교체) (3) `duration_validator.py` ~6 LOC (3곳 호출 교체) (4) `tests/backend/test_process_validator.py` +60 LOC (**TC 6개**: TMS-GAIA partner / **DRAGON 회귀** (`module_outsourcing=None` 거동) / MECH / ELEC / PI role fallback / unknown empty — `tests/conftest.py` L1318-1323 의 6 모델 fixture + `_create_product` helper 재사용, 신규 fixture 작성 0). **총 변경**: ~100 LOC touch / net +25 LOC. **Codex 이관 권장**: ② 자동 체크리스트 인증·권한 로직 (알림 수신자 결정) + 4-22 동일 구조 silent failure 후속 + 4 파일 touch → 자동 이관. **선행**: 없음, FIX-DB-POOL Phase B 측정과 병행 가능. **메타 가치**: Sentry 도입 8시간만에 4-22 와 동일 구조 silent failure 자동 발견 — Sentry 가치 입증 #3 사례. **검증 후 1주 관찰**: Sentry PYTHON-FLASK-4 events 31 → 31 (증가 0) 확인 시 COMPLETED. 설계 상세: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` FIX-PROCESS-VALIDATOR-TMS-MAPPING-20260428 섹션 |
| FIX-DB-POOL-DIRECT-FALLBACK-LOG-LEVEL-20260428 | db_pool direct conn fallback 의 ERROR 로그 잡음 분리 + 신호 보존 (notices.get_notices PYTHON-FLASK-? 22 events/16h, 2026-04-28 등록) | ✅ 🟢 COMPLETED (v2.10.13, 2026-04-28 — db_pool.py L172 logger.error→warning + `_direct_fallback_count` counter + getter, test_db_pool.py 신규 TC 3/3 PASS) | **BE only — `backend/app/db_pool.py:172` `logger.error` → `logger.warning` 강등 + counter metric 신규 도입**. 트리거: 2026-04-28 KST Sentry 대시보드에서 `[db_pool] All pool connections unusable, creating direct connection` issue (transaction=`notices.get_notices` / handled=-- / 22 events/16h / 0 users / Release 2.10.10) 자동 감지. **원인**: `db_pool.py:172` 가 `logger.error` 로 출력 → `LoggingIntegration(event_level=ERROR)` 자동 capture. 그러나 본 fallback **자체는 의도된 안전장치** (3 retry 동안 pool 모든 conn 이 `_is_conn_usable()` False 판정 시 `_create_direct_conn()` 으로 우회 → HTTP 요청 정상 완료, +0.3~0.5s 지연만). **사용자 영향 0** (22 events / 0 users 가 증거). **근본 메커니즘 가설**: max_age=300s + warmup interval=5분 의 시점 race — warmup 직전 ~10초 window 에서 5 conn 이 동시 cohort stale → 3 retry 모두 같은 cohort 만남 → fallback. notices.get_notices 가 자주 뜨는 이유는 클라이언트 polling 빈도 (홈 화면 진입/새로고침 시 호출) + 짧은 endpoint 라 conn 빠른 cycling. **위험**: 4-22 alert silent failure 같은 진짜 ERROR 가 잡음에 묻힐 추적성 손실. 옵션 A (logger.error → warning 강등 + counter metric 분리, ~20 LOC, **채택**) / B (Sentry before_send 필터 — FIX-WEBSOCKET-STOPITERATION 패턴 동일, log level 보존하지만 모듈 결합도↑) / C (warmup interval 5→3분 단축 — 별건 OBSERV-WARMUP-INTERVAL-TUNE-20260428 P2 로 분리). **수정 범위 2 파일**: (1) `backend/app/db_pool.py` ~10 LOC (L172 `logger.error` → `logger.warning` 강등 + 카운터 변수 `_direct_fallback_count` 신규 + `get_direct_fallback_count()` getter) (2) `tests/backend/test_db_pool.py` 신규 또는 확장 +30 LOC (TC 3개: fallback 발생 시 카운터 증가 / fallback 시 logger.warning 호출 / 정상 시 카운터 0). **선행 의존성 0**, FIX-26-DURATION-WARNINGS-FORWARD + FIX-WEBSOCKET-STOPITERATION 와 v2.10.13 묶음 배포 가능. **Post-deploy 1h/24h**: Sentry 본 issue events 증가 0 + Railway logs 에 `[db_pool] All pool connections unusable...` warning level 출력 확인 + counter 가시성 (선택: `/health/diagnostics` 또는 `/admin/db-pool-status` 신규 endpoint 후속). **회귀 위험 0** (log level 변경만, fallback 로직 무수정). **Rollback** git revert 1 commit (atomic, 2 파일). **별건 후속 (선택)**: OBSERV-WARMUP-INTERVAL-TUNE-20260428 (warmup interval 5→3분 단축 / max_age 300→240s, fallback 빈도 자체 ↓, P2). 설계 상세: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` FIX-DB-POOL-DIRECT-FALLBACK-LOG-LEVEL-20260428 섹션 |
| FIX-WEBSOCKET-STOPITERATION-SENTRY-NOISE-20260428 | flask-sock wsgi generator drain 시 발생하는 StopIteration Sentry 잡음 필터 (PYTHON-FLASK-2, 2026-04-28 등록) | ✅ 🟢 COMPLETED (v2.10.13, 2026-04-28 — `__init__.py` 모듈 top-level `_sentry_before_send(event, hint)` 신설 + `sentry_sdk.init(before_send=...)` 등록, 매칭 3조건 모두 성립 시 drop, test_sentry_filter.py 신규 TC 4/4 PASS) | **BE only — `backend/app/__init__.py` `_init_sentry()` 내 `before_send` hook 추가**. 트리거: 2026-04-28 KST Sentry 대시보드에서 PYTHON-FLASK-2 issue (StopIteration / unhandled / mechanism=wsgi / transaction=websocket_route) **16h 내 302 events / Escalating** 자동 감지. q-c.csv 평일/주말 패턴(평일 2,000~4,000 / 주말 300~900) 으로 실 운영 트래픽 확인 (샘플 데이터 X). **원인**: `flask_sock` 의 `Sock.route` 가 wsgi response 를 generator stream 으로 반환 → `ws_handler` 함수 return 후 gunicorn wsgi 가 generator drain 시 `StopIteration` 발생 (Python 정상 종료 신호) → `mechanism=wsgi` 로 unhandled 마킹 → Sentry `FlaskIntegration` 자동 capture. `events.py:162` 의 `try/except Exception: break` 는 `ws.receive()` 내부 호출에만 적용되며 wsgi 외부 generator 단계는 catch 범위 밖. **사용자 영향 0** (302 events / 0 users — 정상 disconnect 흐름). **위험**: 4-22 alert silent failure 같은 진짜 ERROR 가 잡음 302건에 묻힐 추적성 손실. 옵션 A (Sentry `before_send` 필터, ~15 LOC, **채택**) / B (flask-sock middleware wrap, 위험도↑) / C (Sentry UI ignore, 환경 이전 시 재발). **수정 범위 2 파일**: (1) `backend/app/__init__.py` +15 LOC (`before_send` hook — `event.exception.values[0].mechanism.type == 'wsgi'` + `transaction == 'websocket_route'` + `type == 'StopIteration'` 매칭 시 None 반환) (2) `tests/backend/test_sentry_filter.py` 신규 +30 LOC (TC 3개: 매칭 무시 / 다른 transaction StopIteration 전달 / 다른 exception type 전달). **선행 의존성 0**, FIX-26-DURATION-WARNINGS-FORWARD-20260428 와 병행 가능. **Post-deploy 1h/24h**: PYTHON-FLASK-2 events 증가 0 → COMPLETED. **회귀 위험 0** (필터만 추가, 정상 ERROR 경로 무영향). **Rollback** git revert 1 commit (atomic, 1 파일). 설계 상세: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` FIX-WEBSOCKET-STOPITERATION-SENTRY-NOISE-20260428 섹션 |
| FIX-FACTORY-KPI-SHIPPED-V2.4-AMENDMENT-20260428 | Sprint 62-BE v2.4 AMENDMENT — `_count_shipped` plan AND→OR 교정 + `ops` 폐기 + `best` 신설 (FE Phase 2 v1.35.0 선행 BE, 2026-04-28 등록) | ✅ 🟢 COMPLETED (v2.10.14, 2026-04-28 — Pre-deploy Gate ③ R-02 반례 0건 검증 + factory.py `_count_shipped` 3분기 재작성 + 응답 4곳 ops→best, test_factory_kpi 17 passed / 3 skipped — v2.3 ops 의존 TC 운영 데이터 보존 한계로 무효, 신규 TestFactoryKpiV24Amendment 3 TC PASS) | **BE only — `backend/app/routes/factory.py` 의 `_count_shipped()` 함수 + weekly-kpi/monthly-kpi 응답 필드 교체**. 트리거: 2026-04-23~24 Twin파파↔Claude 논의 — W17 검증 쿼리 결과 `shipped_plan=0` 상수화 현상 확인 → `_count_shipped` plan basis 의 `cs.si_completed=TRUE` AND 조건이 실운영과 괴리 (app SI flow 도입률 ≈0%, 2026 상반기 100% 목표). 동시에 `ops` 토글이 실제의 10% 수준으로만 표시되어 사용자 혼란 + 100% 후 ops=best=actual 수렴해서 영구 무의미. **선행 의존**: AXIS-VIEW Phase 2 (v1.35.0 = TEMP-HARDCODE 제거 + 토글 모달 FactoryDashboardSettingsPanel 신규) — BE v2.4 배포 완료 후 FE 진행. **변경 5건**: (1) `_count_shipped()` basis='plan' SQL 의 `INNER JOIN completion_status + cs.si_completed=TRUE` 제거 → `LEFT JOIN app_task_details` (task_id='SI_SHIPMENT' ⭐ 대문자) + WHERE `(actual_ship_date IS NOT NULL OR t.completed_at IS NOT NULL)` OR 조건 (2) basis='ops' 분기 **함수 본체 제거** (L69-78) (3) basis='best' 분기 **신규** — `WHERE p.actual_ship_date IS NOT NULL` reality 경계 + `COALESCE(DATE(t.completed_at), p.actual_ship_date)` si 우선 귀속 (해석 A: si ⊆ actual) (4) weekly-kpi 응답 (L442-444, L458-460) `shipped_ops` → `shipped_best` 교체 (5) monthly-kpi 응답 (L539-541, L551-553) 동일 교체. **순 LOC**: ~+10 net (basis='plan' SQL 재작성 +5 / basis='ops' -10 / basis='best' +15 / 응답 4곳 0 net). **⚠️ Critical 함정 1건**: OPS_API_REQUESTS.md v2.4 문서 (L4810/4853) SQL 이 `'si_shipment'` **소문자** 로 작성되어 있는데 실 DB 값은 `'SI_SHIPMENT'` 대문자 (factory.py L73 / task_seed.py L115 일치). 그대로 구현 시 LEFT JOIN 매칭 0건 → shipped_plan/shipped_best 영구 0. 구현 시 4곳 모두 **대문자 정정 필수**. **사전 검증 SQL 5종**: ① finishing_plan_end NULL 비율 (v2.3 사후 확인) ② DATE(completed_at) timezone 검증 (db_pool options KST 자동 변환 확인) ③ R-02 해석 A 가정 (si 있는데 actual NULL 반례 0건 확인) ④ `app_task_details(task_id, serial_number, completed_at)` 부분 인덱스 존재 ⑤ W17 기준 v2.4 vs v2.3 shipped_plan 차이 미리보기. **pytest TC 14개**: TC-FK-01~14 (기존 v2.2 TC 재정렬 + shipped_plan OR 조건 2종 + shipped_best 귀속 3종 + force_closed 제외 + ops 필드 응답 미포함 검증). **FE backward compat (v1.35.1 degrade safe)**: `pickShipped(data, basis)` 가 basis='ops' 들어와도 plan/best 매칭 안 되고 `return data.shipped_actual` fallback → 자동으로 actual 표시. localStorage 잔존 'ops' 값 마이그레이션 1줄로 처리 가능. **선행 의존성 0**, BE 단독 배포 가능. **Post-deploy 72h 내**: R-02 해석 A 검증 쿼리 결과 0건 확인 → COMPLETED. **회귀 위험 낮음** (단일 함수 SQL 재작성 + 응답 필드 교체, 다른 라우트 무영향). **Rollback** git revert 1 commit (atomic, 1 파일). **연계 BACKLOG**: BIZ-KPI-SHIPPING-01 (3필드 차이 기반 이행률/정합성 분석, app 베타 100% 후 착수) / SI-BACKFILL-01 (생산관리 플랫폼 선행 블로커). 설계 상세: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` FIX-FACTORY-KPI-SHIPPED-V2.4-AMENDMENT-20260428 섹션 |
| FIX-ACCESS-LOG-RETENTION-90D-20260429 | app_access_log 보관 30일 → 90일 완화 (분기 추세 분석 + 사고 사후 검증 윈도우 확보) | ✅ 🟢 COMPLETED (v2.10.15, 2026-04-29 — scheduler_service.py L1128 `INTERVAL '30 days'` → `'90 days'` 1줄 + 주석/job name 동기 갱신, 90일 시뮬레이션 64 MB Railway 0.5 GB 한도 12.8% 디스크 부담 무시, BE only 회귀 0) |
| FIX-MECH-CHECKLIST-PHASE2-DATA-AND-DESCRIPTION-20260504 | MECH 체크리스트 2차 phase 1차 데이터 inherit (BE cr_p1 LEFT JOIN + COALESCE, 4개 조건 DUAL L/R 보장) + _buildCheckRadio description (FE CHECK 누락만) | ✅ COMPLETED (v2.11.5, 2026-05-06, BE 1 + FE 1 ~25 LoC, Codex 라운드 1 M=1 정합 / pytest 2 TC PASS, ADR-024 신설) | **BE+FE — `backend/app/services/checklist_service.py` _get_checklist_by_category() L92-96 + `frontend/lib/screens/checklist/mech_checklist_screen.dart` _buildCheckRadio / _buildSelectDropdown**. 트리거: 2026-05-04 v2.11.X prod 배포 후 사용자 운영 검증 (스크린샷 1차 vs 2차 비교) — (1) **2차 phase 진입 시 1차 input_value/selected_value 빈 표시** (KEYENCE Flow Sensor 1차 선택 + Speed Controller 수량 "1" 입력했으나 2차 화면에서 빈 placeholder + 빈 드롭다운) (2) **description 표시 INPUT 만 적용, CHECK/SELECT 누락** (사용자 catch). **Root cause 1**: `_get_checklist_by_category` L92-96 의 LEFT JOIN 이 `cr.judgment_phase = $2` 단일 조건 → phase=2 GET 시 phase=2 record 만 join → phase=1 record 의 input_value/selected_value 미반환. ELEC/TM 패턴 그대로 차용한 결과 (ELEC SELECT 적게 사용 + TM INPUT 미사용으로 미발견, MECH 가 SELECT 7+INPUT 6 다용 첫 카테고리라 본 영역 처음 노출). **Root cause 2**: cowork 가 작성한 mech_checklist_screen.dart 의 _buildInputField 만 description Text 추가, _buildCheckRadio + _buildSelectDropdown 에는 누락 (cowork 추측 작성 실수 #4 — Sprint 설계서 본문에 3 위젯 모두 표기했지만 실 코드 적용 누락). **변경 2건**: (1) BE SQL JOIN 추가 — `LEFT JOIN checklist.checklist_record cr_p1 ON ... AND cr_p1.judgment_phase = 1` + `COALESCE(cr.input_value, cr_p1.input_value) AS input_value` + `COALESCE(cr.selected_value, cr_p1.selected_value) AS selected_value` (~10 LoC, _get_checklist_by_category 단일 함수, ELEC/TM 도 자동 적용 — 회귀 위험 0 additive) (2) FE _buildCheckRadio + _buildSelectDropdown 에 description Text 추가 (~10 LoC, ELEC L898-909 패턴 차용 — _buildInputField 와 동일). **선행 의존**: 0 (FIX-MECH-CHECKLIST-PHASE2-READONLY-AND-VALIDATION-20260504 와 묶음 진행 권장 — 같은 화면 + 같은 P0 영역). **사용자 영향**: 2차 관리자 검수 흐름 차단 → fix 후 정상 활성화. **회귀 위험 0** (BE additive JOIN + FE Text 추가만, ELEC/TM 무영향). **추정 1h**: BE SQL 5분 + FE 위젯 5분 + flutter analyze + pytest TC 1건 (test_get_mech_checklist_phase2_inherits_phase1_data) + 묶음 atomic commit + push + 운영 검증. **Rollback** git revert 1 commit. **검증 시나리오**: phase=1 데이터 입력 (SELECT MFC + INPUT 수량 + PASS) → phase=2 진입 → 1차 값 read-only 표시 (회색 배경) + 모든 항목에 description 작은 글씨 표시. **Cowork 추측 작성 실수 trail #4** (재발 방지 ADR-023 권장): description 표시 영역에서 _buildInputField 만 적용하고 _buildCheckRadio + _buildSelectDropdown 누락 — Sprint 설계서 본문에 3 위젯 모두 명시했지만 실 코드 적용 시 1개만. 신규 Flutter 코드 작성 시 ELEC 패턴 1:1 검증 + 모든 동등 위젯 동일 적용 검증 표준화. 설계 상세: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` FIX-MECH-CHECKLIST-PHASE2-DATA-AND-DESCRIPTION-20260504 섹션 |
| FIX-MECH-CHECKLIST-PHASE2-READONLY-AND-VALIDATION-20260504 | MECH 체크리스트 2차 read-only UI + check_result null fix + 옵션 C UI 가이드 + description 렌더 (3 release 누적 ~43 LoC, ELEC 패턴 정합 + Codex M=0 합의) | ✅ COMPLETED (v2.11.3 + v2.11.4, 2026-05-04~06, FE only, ADR-023 신설) | **FE only — `frontend/lib/screens/checklist/mech_checklist_screen.dart`**. 트리거: 2026-05-04 v2.11.1 prod 배포 후 사용자 운영 검증 (TEST-333) — (1) BE 400 `INVALID_CHECK_RESULT: 'None'` 에러 발견 (cowork 작성 코드의 `cr.isEmpty ? null : cr` 처리 BE validator 거부) (2) 2차 검사인원 화면에서 1차 입력값 read-only 미구현 — Codex 라운드 1 A3-F2 advisory 영역 실 구현 누락. **logs 부분 검증** (13:55 timeline): INLET S/N 8 master (130~137) 저장 OK + qr_doc_id L/R suffix 정확 (R2-2 정합). 다만 `input_value` / `selected_value` 저장 여부 DB 진단 필요. **변경 3건 (~13 LoC)**: (1) `_upsertNow` check_result 빈 시 PUT skip + null 전송 차단 (~5 LoC, ELEC `_toggleResult` 패턴 정합) — 사용자 PASS/NA 클릭 시점에 input/select+check_result 번들 PUT (2) `_buildInputField` TextField `readOnly: _currentPhase == 2` + `onChanged: phase==2 ? null : ...` (~5 LoC, A3-F2) (3) `_buildSelectDropdown` DropdownButton `onChanged: phase==2 ? null : ...` (~3 LoC, A3-F2). **진단 SQL** (선행 권장): `SELECT master_id, check_result, input_value, selected_value, judgment_phase, qr_doc_id FROM checklist.checklist_record WHERE serial_number='TEST-333' ORDER BY master_id, judgment_phase` — input_value/selected_value 실 저장 확인. NULL 이면 별 BE fix 추가. **선행 의존 0**. **사용자 영향**: 1차 PASS/NA 미선택 시 자동 저장 안 됨 (의도된 ELEC 정합) + 2차 1차 데이터 read-only. **회귀 위험 0** (FE UI 변경만). **묶음 처리 권장**: FIX-SPRINT-63-MECH-CHECKLIST-ENTRY-POINT (P0, 30분) 과 같이 단일 atomic commit → 1h 안 Sprint 63 완전 활성화. **Cowork 추측 작성 실수 trail**: (a) GxColors background/surface/mistLight (commit 21c581e 사용자 fix) (b) check_result null 처리 (본 BUG, 사용자 운영 catch) — 재발 방지 표준 (ELEC 패턴 검증 후 작성, 추측 X). 설계 상세: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` FIX-MECH-CHECKLIST-PHASE2-READONLY-AND-VALIDATION-20260504 섹션 |
| FEAT-MECH-WORK-COMPLETE-CHECKLIST-NUDGE-20260504 | task 완료 후 MECH 체크리스트 미완료 시 진입 유도 (ELEC IF_2 패턴 차용, 본 hotfix 후 안정 운영 1주 후 진행 권장) | 🟢 OPEN (P3, 30분, FIX-SPRINT-63-MECH-CHECKLIST-ENTRY-POINT 후 진행) | **BE only — `backend/app/services/task_service.py` L488 work/complete 응답 영역**. 트리거: 2026-05-04 FIX-SPRINT-63-MECH-CHECKLIST-ENTRY-POINT-20260504 hotfix 작성 시 cowork 가 "선택 3" 으로 명시한 영역. Codex 라운드 1 AV2 — 본 hotfix 는 P0 (사용자 진입 경로 0 해소) 영역만, work/complete UX 개선 (task 완료 후 체크리스트 미완료 시 자동 진입 유도) 는 ELEC 패턴과 동작 차이 추적 필요해 별 sprint 분리. **변경 1건**: task_service.py L488 영역에 ELEC IF_2 패턴 차용 MECH 분기 추가 — `if task.task_category == 'MECH' and task.task_id in {'UTIL_LINE_1', 'UTIL_LINE_2', 'WASTE_GAS_LINE_2'}: check_mech_completion(judgment_phase=1) 미완료 시 response['checklist_ready']=True + 'checklist_category']='MECH' + UI 메시지 ('체크리스트 미완료 항목 N건')`. **선행 의존**: FIX-SPRINT-63-MECH-CHECKLIST-ENTRY-POINT 완료 + 안정 운영 1주 (사용자 진입 패턴 검증 후). **사용자 영향**: 0 (UX 개선만, 기존 동작 유지). **추정 30분**: BE 분기 ~10 LoC + UI 메시지 결정 + pytest TC 1개 (test_work_complete_mech_checklist_pending). **Rollback** git revert 1 commit. 설계 상세: 본 BACKLOG entry + FIX-SPRINT-63-MECH-CHECKLIST-ENTRY-POINT-20260504 의 "선택 3" trail 참조 |
| FIX-MIGRATION-RUNNER-PER-WORKER-RACE-20260504 | migration_runner per-worker race 영구 차단 (51a 에 ON CONFLICT DO NOTHING + PostgreSQL advisory_lock 도입) | 🟡 OPEN (P2, 1h, Sprint 63 후 권장) | **BE only — `backend/app/migration_runner.py` + `migrations/051a_mech_checklist_seed.sql`**. 트리거: 2026-05-04 v2.10.X (Sprint 63-BE) prod 배포 시 Railway logs `❌ 051a_mech_checklist_seed.sql 실행 실패: duplicate key` ERROR 1건 발생. **Root cause 분석**: gunicorn -w 2 가 Worker A + B 동시 startup 시 양쪽 모두 `_get_executed()` 호출 → 둘 다 051a 미실행 판단 → autocommit 모드 + advisory_lock 부재로 동시 INSERT 시도 → Worker A 가 17ms 먼저 73 INSERT + migration_history 기록 성공, Worker B 가 같은 INSERT 시도 시 duplicate key fail. **사용자 영향 0** (Worker A 가 73 row 정상 commit + migration_history 기록 → 다음 redeploy 시 skip → 재발 0). 다만 **Sentry ERROR 1건** 잡음 + 미래 migration 마다 같은 패턴 재발 위험. **변경 2건**: (1) `migrations/051a_mech_checklist_seed.sql` 의 INSERT 끝에 `ON CONFLICT (product_code, category, item_group, item_name) DO NOTHING` 추가 — 73 INSERT idempotent 보장 (2) `backend/app/migration_runner.py` L102-104 영역에 PostgreSQL advisory_lock 도입 — `m_cur.execute("SELECT pg_advisory_lock(hashtext('migration_runner'))")` + try/finally pg_advisory_unlock. 한 시점에 한 worker 만 migration 실행 → per-worker race 영구 차단. **선행 의존성 0** (Sprint 63 무관, 독립 진행 가능). **회귀 위험 0** (autocommit + advisory_lock 표준 패턴). **추정 1h** (코드 변경 ~15 LoC + pytest 신규 TC 2개 (advisory_lock 동시 호출 시뮬레이션 + ON CONFLICT idempotent 검증) + 검증). **모든 future migration 영향**: 본 변경 후 모든 신규 migration (052+, 060+ 등) 자동 protect — 별 작업 0. **Rollback** git revert 1 commit (atomic, 2 파일). **검증**: 시뮬레이션 — 동일 migration 의도적 실패 후 재시도 시 advisory_lock 으로 한 worker 만 실행 + 51a 같은 race 발생 시 ON CONFLICT 로 silent skip. 설계 상세: 2026-05-04 사후 분석 trail (Railway logs 12:04:35.385 / 12:04:35.387 / 12:04:35.402 timeline 정합). **연관**: Sprint 63-BE prod 배포 후 발견 (cowork + 사용자 협업 분석). 재발 방지 표준화. 별 BACKLOG 분리 처리 (Sprint 63 진행 무관) |
| FIX-SPRINT-63-MECH-CHECKLIST-ENTRY-POINT-20260504 | Sprint 63 후속 BUGFIX — MECH 체크리스트 진입점 누락 (BE work/start 응답 분기 + FE task 상세 5 위치 정정 + pytest 6 TC, 추가 검토 5번째 catch 반영) | ✅ COMPLETED (v2.11.2, 2026-05-04, pytest 30/30 PASS, BE 1 + FE 1 = 2 파일 +25 LoC) | **BE + FE 양쪽 — Sprint 63-BE 설계 시 진입점 (entry point) 검증 누락 catch**. 트리거: 2026-05-04 v2.11.1 (Sprint 63-FE) prod 배포 후 사용자 운영 검증 시 발견 — UTIL_LINE_1 / SELF_INSPECTION task 시작 시 ELEC 처럼 자동 전환 안 됨 + task 상세 화면에 MECH 체크리스트 진입 버튼 부재. **사용자 가시 기능 0**: Sprint 63 의 73 항목 + Flutter UI 가 prod 에 적용됐지만 사용자가 진입 못 함. **Cowork 인지 누락 영역**: Sprint 63-BE 설계 시 trigger_task_id 토스트 알림은 명시했지만 work/start 응답 분기 (`checklist_ready` + `checklist_category='MECH'`) 와 FE task 상세 진입 버튼은 ELEC 패턴 차용 시점에 검증 누락. **Root cause 2건**: (1) `backend/app/routes/work.py` L177-184 에 ELEC + QI 만 분기, MECH 분기 부재 → FE 가 응답에서 `checklist_category='MECH'` 못 받음 → `_navigateToChecklist` 호출 안 됨 → 자동 전환 0 (2) FE task 상세 화면 (또는 task_card / task_list) 에 ELEC/TM 체크리스트 진입 버튼 있지만 MECH 버튼 부재 → 작업자 진입 경로 0. **변경 범위 2 파일**: (1) `backend/app/routes/work.py` L177~ MECH 분기 +6 LoC — task_id ∈ {UTIL_LINE_1, UTIL_LINE_2, WASTE_GAS_LINE_2, SELF_INSPECTION} 시 `checklist_ready=True` + `checklist_category='MECH'` (2) FE task 상세 화면 (사용자 측 grep 으로 정확 위치 확정) MECH 분기 +5 LoC. **선택적 변경 1건**: (3) `backend/app/services/task_service.py` L488-497 의 work/complete 응답에도 MECH 분기 추가 (ELEC IF_2 패턴 차용, MECH 도 task 완료 시 체크리스트 진입 유도). **사용자 영향**: Sprint 63 자체는 prod 정상 적용됐지만 사용자 가시 기능 0 → fix 후 즉시 활성화. **회귀 위험 0** (response key 추가만, 기존 클라이언트 무영향). **선행 의존성**: 없음 (Sprint 63-BE + 63-FE prod 배포 완료 전제). **추정**: BE 5분 + FE 30분 (grep + 분기 추가) + 검증 15분 = 1h. **Rollback**: git revert 1 commit (atomic). **검증**: DRAGON S/N 의 UTIL_LINE_1 task 시작 → MechChecklistScreen 자동 진입 + task 상세 화면에서 MECH 체크리스트 버튼 클릭 시 진입. 설계 상세: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` FIX-SPRINT-63-MECH-CHECKLIST-ENTRY-POINT-20260504 섹션. **재발 방지**: 신규 카테고리 도입 시 진입점 (BE work/start 응답 분기 + FE task 상세 버튼) 명시 검증 절차 표준화 (memory.md ADR 추가 권장) |
| BUG-TM-CHECKLIST-AUTO-FINALIZE-STALE-TC-20260504 | TM 체크리스트 4 TC stale (Sprint 63-BE regression 후 발견, Sprint 55 auto-finalize 도입 영향) | 🟡 OPEN (P3, 1h, Sprint 63-BE 진행 무관) | **별 BUG — Sprint 63-BE 와 무관 확정 (회귀 영향 0)**. 트리거: 2026-05-04 Sprint 63-BE squash merge 후 regression 실행 시 4 TC AssertionError 발견. **4 TC**: TC-18 (TM TANK_MODULE 완료 alert) / TC-19 (relay_mode 시 알람 미발송) / TC-27 (admin master duplicate 409) / TC-38 (relay_and_tm_checklist_alert_only_on_finalize). **TC-38 traceback 분석 (확인된 1건)**: `client.post('/api/app/work/complete', json={'task_detail_id': task_id, 'finalize': False})` 호출 시 응답에 `relay_mode` 키 없음. logs `Auto-finalize triggered: all workers completed via relay, task_id=4, last_worker=4` → 단일 작업자 finalize=False 호출 시 auto-finalize 자동 발생 (relay_mode 미설정). **원인 추정**: Sprint 55 (Worker별 Pause/Resume + Auto-Finalize) 도입 후 `_all_workers_completed` 자동화 로직과 기존 TC 의 `finalize=False + relay_mode=True` 가정이 충돌. **Sprint 63-BE 무관 확정**: (1) 4 fail 모두 AssertionError (logic mismatch) — NOT ImportError → rename 9곳 영향 0 (2) Sprint 63-BE 변경 영역 (checklist_service MECH 분기 / routes/checklist MECH / production MECH 분기) 모두 TM checklist 무관 (3) task_service `_trigger_mech_checklist_alert` hook 은 MECH category 만 트리거, TM_TANK_MODULE 무관. **처리 방향**: TC fixture 에 multi-worker 시뮬레이션 추가 또는 expected response 갱신 (auto-finalize 시 `relay_mode` 키 부재 정합 보장). **선행 의존성 0**, Sprint 63-BE 진행과 병렬 가능. **추정**: 1h (TC fixture 4건 수정 + pytest 재검증). **Rollback**: TC 변경만이라 영향 0. 설계 상세: 본 BACKLOG entry + Sprint 55 (Worker별 Pause/Resume) 의 Auto-Finalize 로직 trail 참조 |
| FIX-DB-POOL-SELF-RECOVERY-20260504 | DB Pool 자가 회복 메커니즘 — psycopg2 keepalive 활성화 + 0/0 conn warmed 연속 감지 시 init_pool() 재호출 + WATCHDOG 확장 (4-29 23:31 + 5-04 11:38 KST 5일 주기 사고 차단) | 🔴 OPEN (P1, 1.5h, 5-09 ± 1d 재발 전 배포 필수) | **BE only — `backend/app/db_pool.py` 단일 파일 ~30 LOC**. 트리거: 2026-05-04 KST 11:38~12:32 사고 (4-29 23:31 KST 사고 5일 주기 재발). 사고 timeline: warmup 정상 (10:38~11:38 5/5 1h) → KST 11:43:35 5/5→2/2 첫 degrade → 11:48:35 0/0 시작 → 40분 0/0 지속 (자가 회복 X) → 12:32:50 Restart 후 5/5 회복. **2단계 root cause 분석 결과**: (1단계 트리거) Railway network proxy idle TCP disconnect — Postgres 측 idle 정책 모두 0 (안 끊음) + tcp_keepalives_idle=7200초 (2시간) + **client psycopg2 keepalive OFF** (Sprint 30-B Railway TCP_OVERWINDOW 충돌 회피 정책). Railway proxy 가 idle TCP 끊으면 client 모름 (silent disconnect). (2단계 확산) **ThreadedConnectionPool 자가 회복 부재** — `_used` dict 의 dead conn 5개 정리 메커니즘 없음 → `_pool.getconn()` 시 PoolError exhausted → warmup 의 break → 0/0 conn warmed 8회 연속 (40분) → 새 conn 생성 자체 fail → Restart 외 회복 불가. **WATCHDOG 영역 외**: 기존 WATCHDOG (db_pool.py:267-277) 는 `_pool=None` 만 감지 → 본 사고는 `_pool` object 살아있음 + internal state 만 깨짐 → WATCHDOG 미발화 → Sentry 0 event (사용자 실측). **변경 3건**: (1) `_CONN_KWARGS` 에 keepalive 활성화 — `keepalives=1, keepalives_idle=60, keepalives_interval=10, keepalives_count=3` (60초 idle 후 30초 안 dead 감지, Railway proxy idle 회피) (2) `warmup_pool()` 에 module-level counter `_consecutive_zero_warmup` 추가, 3 cycles (15분) 연속 0/0 시 `close_pool()` + `init_pool()` 재호출 (자가 회복 메커니즘) (3) 변경 2의 logger.error 격상 → LoggingIntegration(event_level=ERROR) 자동 Sentry capture (WATCHDOG 확장, 추가 작업 0). **위험**: Sprint 30-B 의 Railway proxy TCP_OVERWINDOW 충돌 패턴 재발 가능성 — 4-30+ Railway tier 변동으로 해결됐을 가능성 (staging 검증 필수). **Pre-deploy Gate**: (a) staging 환경 1h 운영 후 keepalive 패킷 / TCP_OVERWINDOW WARN 0건 확인 (b) 자가 회복 trigger 강제 시뮬레이션 — 수동 conn close 후 0/0 cycles 발화 → init_pool() 재초기화 검증 (c) WATCHDOG ERROR Sentry capture 검증. **pytest 신규 TC 3개**: test_keepalive_args_passed (psycopg2 connect kwargs 검증) / test_consecutive_zero_warmup_triggers_init_pool (자가 회복) / test_zero_warmup_logger_error_captured (WATCHDOG 확장). **선행 의존성**: 없음 (BE 단독, db_pool.py 단일 파일). **사용자 영향**: 0 (정상 운영 시 변경 무영향, 사고 시 자가 회복 효과). **회귀 위험**: 0 (keepalive 추가 시 Railway proxy 충돌 가능성만 staging 검증 후 해소). **Rollback**: git revert 1 commit. **효과 검증**: 5-09 ± 1d 재발 시점 자가 회복 작동 + 사고 차단 입증. **연관**: OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP-20260427 (warmup cron) ✅ + FIX-DB-POOL-DIRECT-FALLBACK-LOG-LEVEL-20260428 (logger.warning 강등) ✅ + 본 Sprint = 자가 회복 추가. 설계 상세: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` FIX-DB-POOL-SELF-RECOVERY-20260504 섹션 + 사고 logs 분석 trail (조사 5/6/7 결과) |
| FIX-ELEC-QR-DOC-ID-HARDCODE-20260502 | ELEC 완료 판정 SQL 의 `cr.qr_doc_id = ''` 하드코딩 → `_normalize_qr_doc_id()` 공유 helper 사용으로 마이그레이션 (Sprint 63-BE 후속 HOTFIX, 2026-04-30 등록) | 🟡 OPEN (P2, 1h, Sprint 63-BE 배포 후 즉시 후속) | **BE only — `backend/app/services/checklist_service.py` L923 + L945 의 `AND cr.qr_doc_id = ''` 하드코딩 SQL 2곳을 `_normalize_qr_doc_id(serial_number)` 공유 helper 호출로 변경**. 트리거: 2026-04-30 Codex 라운드 2 advisory Q6-3 — Sprint 63-BE 의 `_normalize_qr_doc_id()` 공유 helper 도입 후 ELEC 도 동일 표준 적용 필요. **선행 의존**: Sprint 63-BE 배포 완료 (`_normalize_qr_doc_id()` 함수 존재 보장). **변경 3건**: (1) checklist_service.py L424 주석 정정 ("MECH 등: 기존 그대로 qr_doc_id='' 사용" → 표준 normalizer 사용으로 갱신) (2) L923 SQL 의 `AND cr.qr_doc_id = ''` → `AND cr.qr_doc_id = _normalize_qr_doc_id(%(sn)s)` (Python 측에서 helper 호출 후 파라미터 주입) (3) L945 SQL 동일 패턴. **위험**: ELEC 운영 record 가 현재 `qr_doc_id=''` (31건) 상태 → 마이그레이션 후 매칭 깨짐 가능 → **마이그레이션 전 ELEC record `qr_doc_id` 일괄 UPDATE 필요** (DOC_{S/N} 패턴으로 backfill, 별 migration 052). **pytest TC**: test_check_elec_completion_normalize_qr_doc_id (정합성 회귀) + test_elec_record_backfill_migration (UPDATE 적용 후 매칭 OK). **순 LOC**: ~+5 / 회귀 위험: ELEC SINGLE/DUAL 호환성 정합성 (Sprint 63-BE 와 동일 검증 패턴). **Rollback** git revert 1 commit + ELEC record 원복 (qr_doc_id='' 재적용 — backfill 단방향 위험 별도 검토). 설계 상세: 본 BACKLOG entry + Sprint 63-BE `_normalize_qr_doc_id()` helper 호환 trail |
| DOC-MODELS-QR-REGISTRY-PATH-SYNC-20260502 | 설계서 ↔ 실파일 경로 sync (qr_registry helper 위치 명확화) | 🟢 OPEN (P3, 30분, 즉시 가능) | **doc drift fix only — 코드 변경 0**. 트리거: 2026-04-30 Codex 라운드 2 advisory Q6-A4 — Sprint 63-BE 설계서 일부 옛 표기에 `models/qr_registry.py` 언급 가능성 + 실파일 검색 결과 `/backend/app/models/qr_*.py` 경로 부재 확인. **현 상태**: Sprint 63-BE 4-A 섹션 (`_normalize_qr_doc_id()`) = `services/checklist_service.py` 정확 명시 — 그러나 다른 문서 잔존 표기 정합성 검증 필요. **작업**: (1) AGENT_TEAM_LAUNCH.md / memory.md / handoff.md / CLAUDE.md grep 으로 `models/qr_registry` 잔존 표기 확인 (2) 발견 시 `services/checklist_service.py` 또는 정확한 위치로 정정 (3) 신규 helper 도입 시 표준 위치 ADR 1줄 추가 (memory.md). **순 LOC**: ~10 (doc only) / 회귀 위험 0. 설계 상세: 본 BACKLOG entry only |
| SPRINT-63-FE-MECH-CHECKLIST-20260501 | Sprint 63-FE — MECH 체크리스트 Flutter UI + R2-1 BE patch + alert 핸들러 + pytest 3 TC (mech_checklist_screen.dart 844 LOC, 2026-05-01 등록 → 2026-05-04 v2.11.1 release, 라운드 1+2+N1+N2 모두 정정) | ✅ COMPLETED (v2.11.1, 2026-05-04, +1,038 LoC, BE+FE 통합) | **AXIS-OPS FE only — `frontend/lib/screens/checklist/mech_checklist_screen.dart` 신규**. 트리거: Sprint 63-BE BE 인프라 배포 완료. ELEC `elec_checklist_screen.dart` (1,076 LOC) 패턴 복제 + 입력 UI 3종 분기 추가. **변경 사항**: (1) `mech_checklist_screen.dart` 신규 (~1,000 LOC, ELEC 패턴 차용) (2) input_type 별 입력 위젯 분기 — CHECK 라디오 / SELECT 드롭다운 (`select_options` JSON 활용) / **INPUT 텍스트 필드 (INLET 8개 L/R 명확 구분 표시)** (3) 1차/2차 phase 토글 + 1차 입력값 read-only 표시 (관리자 화면) (4) scope_rule 매칭 안 되는 항목 = 회색 + "해당없음" 자동 NA UI (DRAGON/GALLANT/SWS 외 모델은 13/14/19 disabled) (5) WebSocket `CHECKLIST_MECH_READY` alert 수신 시 토스트 + 화면 진입 유도 (6) **INLET 8개 명확 구분** — 사용자 결정 옵션 A 변형 반영 (Left #1, Right #1, Left #2, ... 별도 입력 필드, schema 8 record per S/N 정합). **선행 의존**: Sprint 63-BE 배포 완료 (응답 schema scope_rule + trigger_task_id + select_options 활용). **Sprint 착수 시 결정 사항 1건 (Codex 라운드 3 A2-A 분리)**: DRAGON/GALLANT/SWS 외 모델의 13/14/19 그룹 disabled UI 메시지 텍스트 — "해당없음 (Tank Ass'y 미적용)" / "N/A" / "—" 중 ELEC 패턴 차용 + 화면 보면서 30초 결정. BE 응답 schema 영향 0 (FE 단독 결정). **수정 파일**: `mech_checklist_screen.dart` 신규 1 파일 + `app_navigation.dart` 라우팅 1줄 추가. **추정**: ELEC 패턴 차용으로 2d. **Rollback** git revert (Flutter 빌드 이전 상태) + Netlify 이전 빌드 활성화. 설계 상세: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` Sprint 63-BE 섹션 의 "AXIS-OPS FE 구현" 부분 cross-reference + ELEC `elec_checklist_screen.dart` 코드 참조 |
| SPRINT-63-BE-MECH-CHECKLIST-20260429 | Sprint 63-BE — MECH 체크리스트 BE 인프라 (양식 73항목 / 20그룹 / scope_rule + trigger_task_id 신규 / item_type INPUT 추가 / TM·ELEC·MECH completion 함수 public 통일, **2026-04-29 등록 → 2026-05-01 v2 INLET S/N L/R 8개 분리 → 2026-05-04 v2.11.0 squash merge 완료, pytest 21/21 PASS**) | ✅ COMPLETED (v2.11.0, 2026-05-04, +1,415 LoC, branch sprint-63-be-mech-checklist 11 commits squash merge) | **BE+FE 양쪽 — `backend/app/routes/checklist.py` MECH 분기 + `services/checklist_service.py` `check_mech_completion()` 신설 + `migrations/051_mech_checklist_extension.sql` + `051a_mech_checklist_seed.sql` (69 INSERT) + `frontend/lib/screens/checklist/mech_checklist_screen.dart` 신규 + AXIS-VIEW `ChecklistManagePage.tsx` BLUR 해제 + `ChecklistAddModal.tsx` MECH 토글 활성화**. 트리거: 2026-04-29 Twin파파 양식 공유 (Excel `현황판_260108_MFC Maker추가 260223.xlsm` 의 `공정진행현황-2행` 시트 기구 조립 검사 성적서 + `model_config.csv` tank_in_mech 컬럼 + `checklist_master.csv`/`checklist_record.csv` 기존 schema). **양식 분석 결과 (v2 2026-05-01)**: **73 항목** / 20 그룹 (3Way V/V / WASTE GAS / INLET / BURNER / REACTOR / GN₂ / LNG / O₂ / CDA / BCW / PCW-S / PCW-R / Exhaust / TANK / PU / 설비 상부 / 설비 전면부 / H/J / Quenching / 눈관리). **19개 1차+2차 (phase1_applicable=TRUE)**: **INLET S/N(INPUT) 8개 (Left #1~#4 + Right #1~#4 master 분리, 사용자 결정 옵션 A 변형)** + Speed Controller 방향(CHECK) 2개 + Speed Controller 수량(INPUT) 2개 + MFC Spec(SELECT) 4개 + Flow Sensor Spec(SELECT) 3개. **54개 2차만 (phase1_applicable=FALSE)**: 일반 CHECK 항목. **judgment_phase=2 동작**: (c)안 — 관리자 phase=2 record 충족만 판정, 1차 미입력 항목도 관리자가 검수 자리에서 직접 입력 가능. **schema 변경 3건**: (1) `scope_rule VARCHAR(30) DEFAULT 'all'` 신규 — 'all' (56) / 'tank_in_mech' (9, DRAGON/GALLANT/SWS, 13·14·19 그룹) / 'DRAGON' (8, INLET S/N L/R 분리) (2) `trigger_task_id VARCHAR(50)` 신규 — UTIL_LINE_1 (Speed 4) / WASTE_GAS_LINE_2 (INLET 8) / UTIL_LINE_2 (MFC+FS 7) / NULL (54개 일반 → SELF_INSPECTION 일괄 2차) (3) `item_type` enum 'INPUT' 추가 (기존 CHECK/SELECT). **분포 검증 (v2 51a 실파일)**: CHECK 56 / INPUT 10 / SELECT 7 / phase1 TRUE 19 / phase1 FALSE 54 — 모두 정합. **권한**: `resolve_managers_for_category(sn, 'MECH')` 호출로 mech_partner 매니저 자동 lookup (4-22 HOTFIX-ALERT-SCHEDULER-DELIVERY 표준 패턴 + v2.10.11 정리 후 그대로 활용, GST QI 무관). **alert_type 확장**: `CHECKLIST_MECH_READY` 신규. **TM/ELEC/MECH completion 함수 public 통일** (memory.md L364): `_check_tm_completion` → `check_tm_completion` rename / `check_elec_completion` 그대로 / `check_mech_completion` 신규. **product_code='COMMON' 단일** (Twin파파: 100+ product_code 분기는 미래 MTO 시점 대비 미리 구현, 현재 미사용). **MFC/Flow Sensor 옵션**: 임의값 임시 입력 (단순 문자열 배열, 단위 포함 복합 텍스트, 예: "MKS GE50A | 5 SLM | 0.5 MPa | 0.1-0.7 MPa"), VIEW 토글로 사후 수정. **INLET S/N**: 일단 텍스트 입력, OCR 후속 별건. **VIEW 측 이미 부분 준비**: `BLUR_CATEGORIES=['MECH']` (블러 처리 중) / `GROUP_POLICY.MECH={fixed:false}` (그룹 자유) / `TYPE_OPTIONS.MECH=['CHECK','INPUT']` (SELECT 추가 필요) / `effectiveProduct = selectedProduct` (모델별 의도, 미래 대비). **수정 파일 (Sprint 63-BE 범위)**: BE 5 파일 (~250 LOC). **AXIS-OPS FE 별 Sprint 63-FE** = mech_checklist_screen.dart 신규 (~1,000 LOC, 2d, BE 배포 완료 후 착수). **AXIS-VIEW FE 별 repo Sprint** = `AXIS-VIEW/DESIGN_FIX_SPRINT.md` Sprint 39 (~30 LOC, BE 배포 후 착수). **선행 의존성**: 없음, BE 단독 배포 가능. **선행 결정 trail (5단계)**: 1차 입력 타입 4종 → input_type 3종 통합 (CHECK/SELECT/INPUT) → 13/14/19 모델 = tank_in_mech=TRUE 3개 → product_code COMMON 단일 + scope_rule 신규 → 토스트 trigger_task_id 4종. **Codex 이관 권장**: ② 자동 체크리스트 인증·권한 로직 (4-22 동일 영역) + 5 파일 touch + ELEC 패턴 차용. **Post-deploy 1주 관찰**: 작업자 1차 입력률 + 2차 검수 완료율 + Sentry 새 ERROR 0건. **Rollback** git revert (1차 commit) — migration `051` 은 별도 down migration 필요 (column drop). 설계 상세: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` Sprint 63-BE 섹션 + `mech_checklist_seed_extracted.csv` (양식 분석 결과) |
| BUG-DRAGON-TMS-PARTNER-MAPPING-20260428 | DRAGON 모델의 TMS task 매니저 매핑 정합성 검토 (FIX-PROCESS-VALIDATOR-TMS-MAPPING 후속) | 🟢 OPEN (P3, 별건, 추정 1~2h) | **분석 only — 잠재 design 이슈**. 트리거: FIX-PROCESS-VALIDATOR-TMS-MAPPING-20260428 Sprint 설계 검토 advisory 2번. CLAUDE.md L1100 `DRAGON: tank_in_mech=TRUE — 한 협력사가 탱크+MECH 일괄 처리. 주로 TMS(M)이지만 반드시 product_info.mech_partner 확인`. 현재 `_CATEGORY_PARTNER_FIELD['TMS']='module_outsourcing'` 매핑은 GAIA 정합 (module_outsourcing='TMS'). 그러나 **DRAGON 의 경우 module_outsourcing=None** → partner 매핑 결과 = 빈 리스트 → DRAGON 의 TMS task 알람 잠재 미수신. **검증 필요**: (1) prod 에 DRAGON 모델 + task_category='TMS' 인 task 가 실제 존재하는지 (task_seed.py 가 DRAGON 에 TMS task 생성 안 할 수도) (2) 존재한다면 매니저는 mech_partner 기반이어야 정합 (3) `_CATEGORY_PARTNER_FIELD` 가 model_config 기반 분기로 확장 필요 가능성. **선행**: FIX-PROCESS-VALIDATOR-TMS-MAPPING-20260428 배포 후 1주 Sentry 관찰 → DRAGON 관련 silent failure 0건 입증 시 본 BUG close, 발생 시 fix Sprint. 4-22 동일 패턴 재발 방지용 proactive audit. 예상 1~2h |
| INFRA-RAILWAY-DB-ROTATION | Railway Postgres credentials rotation (보안 점검) | 🟡 OPEN (P2, 별도 배포 windows 필요) | **인프라 보안 작업 — Railway Postgres 자격증명 (DATABASE_URL 의 user/password) 정기 rotation**. 트리거: 4-22 알람 장애 세션 중 Twin파파 미진 사항 언급 ("railway rotation도 진행해야되는데"). 이전 노출 가능성 (실수로 git commit / log 노출) 정기 점검 차원. **작업**: (1) Railway Postgres → Settings → "Reset Database Password" 또는 새 credentials 발급 (2) 모든 dependent services (axis-ops-api, ETL, AXIS-VIEW backend 등) 의 `DATABASE_URL` env 동시 갱신 (3) old credentials revoke (4) 정상 동작 검증. **위험**: rotation 중 ~1~5분 connection 재수립 동안 일시적 Pool exhausted 발생 가능 → off-peak (저녁 22:00 이후 또는 주말) 권고. **선행 의존성 0**, 다른 작업과 무관. 우선 처리 차원에서는 **알람 사후 검증 (POST-REVIEW-049 + OBSERV-ALERT-SILENT-FAIL) 종결 후 진행 권고**. 예상 소요 1~2h (배포 windows 포함). 관련: 4-22 세션 핸드오프 |
| INFRA-GITHUB-REPO-PUBLIC-TO-PRIVATE | GitHub repo public → private 전환 (보안 점검) | 🟡 OPEN (P2, 단발성, 30분~1h) | **인프라 보안 작업 — GitHub `isolhsolfafa/AXIS-OPS` repo 를 public 에서 private 으로 전환**. 트리거: 사내 manufacturing operations 시스템 코드라 외부 공개 risk (스키마 / API 구조 / 보안 검토 미진 영역 노출). 이전 4-22 세션에서 `SECURITY_REVIEW.md` + `DB_ROTATION_PLAN.md` `.gitignore` 추가는 했으나, 전체 repo 자체의 visibility 는 그대로. **작업**: (1) GitHub repo Settings → General → "Change visibility" → Private (2) Deploy keys / webhook 영향 확인 (Railway / Netlify CI 재설정 필요 여부) (3) 협력사 (Codex, Claude Code) 접근 권한 재발급 — 이미 작업 중인 collaborator 가 있다면 access token / SSH key 재인증 (4) repo 검색 노출 차단 확인 (5) Public 시기 동안 cloning 했던 외부 사용자 추정 — 가능하면 git history rewrite 검토 (선택). **위험**: CI/CD 설정 누락 시 다음 push 배포 실패 가능 → 변경 직후 가벼운 commit + Railway/Netlify 자동 배포 검증 권고. **선행 의존성 0**. INFRA-RAILWAY-DB-ROTATION 와 묶어서 "보안 점검 day" 처리도 효율적. 예상 소요 30분~1h. 관련: 이전 세션 미진 사항 |
| HOTFIX-ALERT-SCHEDULER-DELIVERY-20260422 | scheduler 3곳 target_worker_id 표준 패턴 적용 + 배치 dedupe (M2) | ✅ 🟢 COMPLETED (2026-04-22, v2.9.11) | **5일 알람 장애 최종 복구**. scheduler_service.py 3곳 (RELAY_ORPHAN L884 + TASK_NOT_STARTED L967 + CHECKLIST_DONE_TASK_OPEN L1044) 이 target_worker_id 미지정 → role_<VALUE> broadcast → role_TMS room 구독자 0 → 52건 완전 undelivered. 수정: `_resolve_managers_for_category` 헬퍼 도입 (task_service.py L571 표준 패턴) + 배치 dedupe (target_worker_id IS NOT NULL 필터로 legacy 69건 간섭 차단). +100/-52 LOC. Codex 교차검증 M1 수용 + A 6건 BACKLOG 이관. pytest 129 passed / 7 skipped / 회귀 0건. 관련: `AXIS-OPS/ALERT_SCHEDULER_DIAGNOSIS.md` §11.14.7 / `AXIS-OPS/AGENT_TEAM_LAUNCH.md` HOTFIX-ALERT-SCHEDULER-DELIVERY-20260422 섹션 |
| OBSERV-RAILWAY-LOG-LEVEL-MAPPING | gunicorn stderr → Railway 'error' 태깅 수정 (2026-04-22 등록) | ✅ 🟢 COMPLETED (v2.10.8, 2026-04-27) | **BE — `__init__.py` L8+ `import sys` + `logging.basicConfig(... stream=sys.stdout, force=True)` 명시 / Procfile gunicorn `--access-logfile=- --log-level=info` 추가**. 기본 stderr → Railway 'error' 잘못 태깅 문제 해소. Sentry alert rule 의 level=error 필터 정확 작동 (선행 조건 충족). **검증**: Railway logs 에서 INFO 메시지가 `level: info` 로 정확 분류되는지 확인 권장 |
| OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION | 앱 부팅 시 migration 상태 assertion + drift 알림 (2026-04-22 등록) | ✅ 🟢 COMPLETED (v2.10.8, 2026-04-27 — `assert_migrations_in_sync()` 함수 신규, disk vs DB sync 검증 + Sentry capture_message) |
| FIX-LEGACY-ALERT-TMS-DELIVERY | 4-17~22 기간 legacy 69건 복구 여부 결정 (2026-04-22 등록) | 🟡 OPEN (P3, 옵션) | HOTFIX-ALERT-SCHEDULER-DELIVERY 이후 새 알람은 정상 delivery. 다만 기존 `target_role='TMS'` 52건 + `target_role='elec_partner/mech_partner/module_outsourcing'` 17건 = **69건 legacy 는 여전히 target_worker_id=NULL 상태로 존재**. 복구 옵션: (a) 각 알람을 관리자별로 복제 INSERT → 과거 알람 소급 notification (사용자 혼란 가능) (b) skip — 대개 1주 이상 지난 알람이라 actionable 정보 아님. **권장: (b) skip**. 다만 legacy 가 존재하는 한 HOTFIX Sprint 설계서 § Codex M2 지적처럼 다음 migration 시에도 유사 dedupe 간섭 가능 → 24h/7d/3d window 지나면 자연 소거 |
| REFACTOR-SCHEDULER-SPLIT | scheduler_service.py 파일 분할 (2026-04-22 등록) | 🟡 OPEN (P2, 다음 Sprint) | 현재 scheduler_service.py ~1090 LOC (HOTFIX 후). CLAUDE.md L491 1단계 기준 "필수 분할 800줄" 초과 + "God File 1200줄" 근접. 분할 제안: (1) `scheduler_service.py` (init/start/stop + 스케줄러 라이프사이클) (2) `scheduler_alerts.py` (11 job 함수) (3) `scheduler_helpers.py` (`_resolve_managers_for_category` 등 헬퍼). 예상 LOC: 200 + 600 + 100. **전제**: 리팩토링 7원칙 (CLAUDE.md L586) 엄수 — 기능 변경 0, pytest Before/After GREEN 증명, git 태그 `pre-refactor-scheduler-split`. 작업 소요 4~6h. 관련: `AGENT_TEAM_LAUNCH.md` HOTFIX-ALERT-SCHEDULER-DELIVERY § Codex A4 |
| TEST-ALERT-DELIVERY-E2E | 알람 delivery WebSocket E2E 통합 테스트 (2026-04-22 등록) | 🟡 OPEN (P2, 다음 Sprint) | 본 장애가 pytest GREEN 에서도 운영에서 undelivered 였던 근본 원인: 기존 테스트는 DB INSERT 만 검증하고 **FE delivery 검증 부재** (test_alert_all20_verify TC-AL20-07/08). 신규 통합 테스트: (1) WebSocket mock 등록 (`role_<X>` 또는 `worker_<id>` room) (2) alert 생성 트리거 (3) emit_new_alert/emit_process_alert 호출 확인 (4) mock room 에 message 도달 여부 assertion. pytest fixture 로 WebSocket 레지스트리 주입. 3~5 TC 신규. 작업 소요 3~4h. 관련: Codex A6 |
| TEST-SCHEDULER-EMPTY-MANAGERS | scheduler PI/QI/SI 엣지 empty-manager 테스트 (2026-04-22 등록) | 🟢 OPEN (P3, 1h) | Codex A3 지적 — `_resolve_managers_for_category` 가 PI/QI/SI 로 `get_managers_for_role` 호출 시 빈 리스트 반환 가능성 (관리자 미등록 / 비활성). 현재 코드는 for 루프로 safe skip 하지만 명시적 테스트 필요. TC: (1) role='PI' managers=[] 상황에서 RELAY_ORPHAN 생성 → 0건 INSERT (2) role='QI' managers=[1] 정상 1건. `test_scheduler.py` 에 2~3 TC 추가. 작업 소요 1h |
| BUG-DURATION-VALIDATOR-API-FIELD | `/api/app/work/complete` 응답에 `duration_warnings` 필드 누락 (2026-04-22 등록) | ✅ 🟢 COMPLETED (v2.10.12, 2026-04-28 — `FIX-26-DURATION-WARNINGS-FORWARD-20260428` 옵션 C) | **Codex 라운드 2 합의 (2026-04-28)**: Q1/Q2 모두 A — 응답 키 생성 경로 4-22 부터 누락된 별건. **fix 적용**: (1) `task_service.py` L497-499 unconditional 응답 키 (조건부 제거) (2) `work.py` L265-266 default 빈 리스트 forward (3) `test_duration_validator.py` L75-76 assertion 갱신 + 신규 TC `test_normal_completion_returns_empty_duration_warnings` + `test_reverse_completion` `@pytest.mark.skip` (시작/종료 timestamp 서버 `datetime.now(Config.KST)` 자동 기록 — `task_service.py:146/256` + `work.py:448`, prod 0건 실측, 인프라 사고 시나리오만). v2.10.12 BE 2 파일 + test 1 파일 atomic. 관련: AGENT_TEAM_LAUNCH.md § FIX-26-DURATION-WARNINGS-FORWARD-20260428 |
| POST-REVIEW-HOTFIX-ALERT-SCHEDULER-DELIVERY-20260422 | HOTFIX-ALERT-SCHEDULER-DELIVERY 배포 사후 Codex 교차검토 (2026-04-22 등록) | 🔴 OPEN (S2, 7일 이내 필수) | CLAUDE.md § 🚨 긴급 HOTFIX 예외 조항 S2 적용 — Opus 단독 리뷰 후 배포 → 7일 이내 Codex 사후 검토 의무. 검토 범위: ① `_resolve_managers_for_category` 헬퍼의 정확성 ② 3곳 배치 dedupe 쿼리 index 활용 효율 (`idx_alert_logs_dedupe`) ③ for manager_id 루프의 N+1 query 여부 ④ Codex M1 (Item 2) 해결 완결성 ⑤ 배포 후 48h 관찰 데이터 (실제 delivery 재개 + legacy 69건 수렴 곡선). 예상 소요 30분 |
| BIZ-KPI-SHIPPING-01 | 경영 대시보드 출하 KPI 설계 (이행률·정합성, 2026-04-23 등록) | 🟢 DRAFT (P3, App 베타 100% 전환 후 착수 검토) | **추상 단계 / 확정 아님 / 정리만 보존**. 배경: OPS App 전환기 (기존 PDA/수기 → App 베타). 이행률·정합성 같은 경영 지표는 App 전환율이 충분히 올라간 뒤 의미 있는 해석 가능. **선행**: Sprint 62-BE v2.2 (데이터 공급 인프라 — `shipped_plan`/`shipped_actual`/`shipped_ops` 3필드 raw) 배포 완료. **검토 필요 항목** (Sprint 착수 시 확정): ① 이행률 정의 — `actual/plan` 단순 vs `actual/(plan 만기도래)` 정교 ② 정합성 지표 공개 범위 — 공장 카드 / Admin 전용 / 임계치 알림 ③ `plan_count` 정의 — si_completed 조건 유무 ④ 경영 대시보드 화면 위치 — 기존 공장 대시보드 확장 vs 별도 Exec 뷰 ⑤ 베타 전환 스케줄 반영 — 어느 모델/협력사부터 단계적 100%. **3계층 데이터 구조**: 계획층(`ship_plan_date` ETL) → 실적층(`actual_ship_date` Teams 수기 + cron) → 앱층(`SI_SHIPMENT.completed_at` OPS 앱 베타). **지표 2종** (추후 확정): `fulfillment_rate = shipped_actual / shipped_plan × 100` (이행률) / `app_coverage_rate = shipped_ops / shipped_actual × 100` (베타 전환 커버리지). **현재 실측 (2026-04-23 기준 이번 주)**: plan=0 / actual=23 / ops=0. **주의**: 자동 UNION 합산(`shipped_union`) 은 폐기 — 3개 소스는 독립 비교용. 관련: `AGENT_TEAM_LAUNCH.md` Sprint 62-BE v2.2 섹션 |
| POST-REVIEW-SPRINT-62-BE-V2.2-20260423 | Sprint 62-BE v2.2 배포 사후 Codex 교차검토 (2026-04-23 등록) | ✅ **PARTIAL COMPLETED** (Q1/Q3 해소, Q5 관찰형 유지) | **Q1 (migration 050 Railway 적용)**: ✅ 2026-04-23 13:38 KST 수동 적용 + `migration_history` 기록 + `pg_indexes` 3종 확인. **Q3 EXPLAIN ANALYZE 실측 (2026-04-23)**: ✅ ② `idx_product_info_actual_ship_date` 사용 (Bitmap Index Scan 0.071ms) / ④ `idx_product_info_finishing_plan_end` 사용 (Bitmap Index Scan 0.127ms, weekly-kpi 메인 쿼리) / ③ `idx_app_task_details_completed_at` 기존 인덱스 사용 (0.092ms). ① `idx_product_info_ship_plan_date` 는 현 쿼리 패턴에서 planner가 `completion_status` Seq Scan + serial_number Nested Loop 선택 → "never executed" (si_completed=TRUE 0건이라 다른 전략이 더 효율적). **sub-ms 대역** 전체 쿼리 매우 빠름. Q3 A **완전 해소**. **Q5 (네이밍 부채 모니터링)**: ⏸ 관찰형 — `pipeline.shipped` vs `shipped_plan` FE 혼동 사례 7일 관찰 중. BIZ-KPI-SHIPPING-01 착수 시 final 네이밍 결정. **Q3 Advisory**: `idx_product_info_ship_plan_date` 현재 미사용이나 향후 si_completed=TRUE 비율 증가 시 자동 활성화 가능, 삭제 불필요 (공간 무시). **v2.10.1 교정** 포함 (weekly-kpi WHERE ship_plan_date→finishing_plan_end). 관련: `AGENT_TEAM_LAUNCH.md` Sprint 62-BE v2.2 섹션 / handoff.md |
| UX-ATTENDANCE-CHECK-401-TOAST-20260504 | hr.attendance_check 401 시 "세션 만료" 토스트 + 자동 재로그인 안내 (사용자 6연타 UX 해소, 2026-05-04 등록) | 🟢 OPEN (P3, 1h) | **FE only — `frontend/lib/services/api_service.dart` `_forceLogout()` 분기 + `frontend/lib/main.dart` ScaffoldMessenger 글로벌 hook**. 트리거: 2026-05-04 사용자 측 401 로그 분석 중 `POST /api/hr/attendance/check` **6연속 401 (3~6ms)** 패턴 발견. 원인 분석 (`app_access_log` 대조 + `api_service.dart:14-19` `_authSkipPaths` 검증): 사용자가 출근체크 버튼을 누른 시점에 토큰이 이미 만료된 상태 (idle 18분 후 admin1234 재현 케이스 동일 흐름) → BE 401 응답 → FE 가드(`/api/hr/attendance/check` 는 `_authSkipPaths` 외 경로라 refresh 시도) → refresh 도 401 → `_forceLogout()` 발동 (`api_service.dart:104-109`). **현재 동작**: clearToken + `onRefreshFailed?.call()` 만 실행, 사용자에게 명시적 안내 없음 → "왜 안 되지" 반복 클릭 → 6연타. BUG-22 가드 자체는 정상 동작 (refresh storm 0건, `_isForceLogout=true` 후 재호출 차단). **데이터 근거** (5-04 access_log 분석): `hr.attendance_check` 자체 BE 응답 양호 (avg 58ms / p95 106ms / max 181ms / n=58 in 24h) — **이슈는 100% UX 안내 부재**. **변경 사항**: (1) `api_service.dart` `_forceLogout()` 에 글로벌 ScaffoldMessenger hook 추가 — `onRefreshFailed?.call()` 콜백에 토스트 표시 책임 위임 (또는 `onSessionExpired` 콜백 분리 신설) (2) `main.dart` 또는 `app.dart` 의 `MaterialApp` 에 `scaffoldMessengerKey: GlobalKey<ScaffoldMessengerState>()` 등록 + AuthService 가 force-logout 시 `scaffoldMessengerKey.currentState?.showSnackBar(SnackBar(content: Text("세션이 만료되었습니다. 다시 로그인해 주세요"), duration: 3s))` 호출 (3) AuthGate 의 login 화면 redirect 가 toast 후 자연스럽게 이어지는지 검증. **선행 의존성 0** (BUG-22 가드 위에 토스트 layer 만 추가, 기존 logout flow 무수정). **회귀 위험 매우 낮음** (UI alert 추가만, 비즈니스 로직 무수정). **연계 BACKLOG**: `FE-ALERT-BADGE-SYNC` (홈 복귀 시 stale 배지) — 같은 "세션 만료 / refresh 직후 UX 명료화" 흐름. 함께 묶어 FE only mini-Sprint 가능. **검증 시나리오 3개**: (1) 출근체크 버튼 클릭 시점 토큰 만료 → 토스트 1회 + 로그인 화면 (2) 화면 idle 후 백그라운드 폴링 401 → 토스트 1회 + 로그인 화면 (race condition 시 중복 토스트 방지 — `_isForceLogout` flag 활용 가능) (3) 로그인 후 정상 작동. **소요**: FE 구현 30분 + 실기기 QA 30분 = 1h. 최초 등록: 2026-05-04 (사용자 측 401 로그 + access_log p95 분석 결과). 근거 데이터: `app_access_log` `endpoint='hr.attendance_check'` 24h 응답시간 분포 + `_authSkipPaths` (3개) 외 18개 endpoint 가 401 시 refresh 시도 경로임을 코드로 확인 |
| UX-ADMIN-MENU-403-FEEDBACK-20260504 | 권한 없는 사용자의 admin 메뉴 진입 시 403 안내 부재 (동일 사용자 5-02~5-04 across days 반복 시도, 2026-05-04 등록) | 🟢 OPEN (P3, 1h) | **FE only — admin 메뉴 항목 conditional rendering + 403 응답 처리 토스트**. 트리거: 2026-05-04 7일 4xx/5xx 분석 중 `admin.get_settings` + `checklist.list_checklist_master` 쌍 403 응답이 **5-02 / 5-03 / 5-04 across days 반복 발생** 패턴 확인. 같은 ms timestamp 에 batch 호출 → batch 차단 → 화면 안내 없음 → 다음 날 또 시도. **데이터 근거** (5-04 7일 분석 50건): 403 38건 / 400 10건 / 404 1건 / **5xx 0건**. 403 38건 모두 `admin.get_settings` + `checklist.list_checklist_master` 쌍 (`category=TM&product_code=COMMON` 동일 query string). 시간대 패턴: 5-02 08:14 (출근 시점) / 5-03 16:29~16:30 / 5-04 10:19 — 동일 worker 의 동일 행동 반복 추정. 4-30 09:22~09:23 / 14:23 도 동일 패턴 (n=4쌍 × 2일). **현재 동작**: BE 정상 차단 (`@admin_required` 데코레이터) → FE 가 403 받아도 토스트/안내 없이 빈 화면 또는 무반응 → 사용자가 "왜 안 보이지" → 다음 날 또 시도. **변경 사항**: (1) admin 메뉴 항목을 `worker.role`/`is_manager` 기반 conditional rendering — 메뉴에서 안 보이게 (이미 일부 적용일 수 있음, `home_screen.dart` 메뉴 빌더 audit 필요) (2) deep link / 캐시 / role 변경 race condition 으로 들어왔을 때 403 응답 시 ScaffoldMessenger 토스트 "관리자 권한이 필요합니다" + 이전 화면 자동 복귀 (3) 동일 timestamp batch 403 시 토스트 1회만 표시 (debounce, `UX-ATTENDANCE-CHECK-401-TOAST-20260504` 와 동일 패턴). **선행 의존성 0** (BUG-22 가드 위 토스트 layer). **회귀 위험 매우 낮음** (UI alert + conditional rendering, 비즈니스 로직 무수정). **연계 BACKLOG**: `UX-ATTENDANCE-CHECK-401-TOAST-20260504` (401 토스트) + `FE-ALERT-BADGE-SYNC` — 같은 "에러 응답 UX 명료화" 흐름. **함께 묶어 FE only mini-Sprint 권장** (3건 합쳐 2~3h, 권한·세션 UX 종합 정리). **검증 시나리오 3개**: (1) 일반 worker 로그인 → admin 메뉴 항목 미노출 (2) deep link `/admin/options` 강제 진입 → 403 토스트 1회 + 홈 복귀 (3) role 변경 직후 race condition → 토스트 1회 + 메뉴 갱신. **소요**: FE 30분 + 실기기 QA 30분 = 1h. 최초 등록: 2026-05-04 (7일 4xx 패턴 분석 b.csv). 근거 데이터: `app_access_log` 7일 status>=400 분석 결과 (`admin.get_settings` + `checklist.list_checklist_master` 쌍 38건 / 동일 사용자 across days 추정) |

---

## ✅ Sprint 29 보완 완료 (v1.7.7, 2026-03-16)

- DB: `role_enum`에 PM 추가 (migration 021 적용)
- BE: 이름 기반 로그인 (`get_worker_by_name`, login 조회 체인 확장)
- BE: monthly-detail `ship_plan_date` 응답 추가
- BE: monthly-detail `per_page` 상한 200 → 500

## ✅ Sprint 29 완료 (v1.7.6, 2026-03-15) — 공장 API (BE only)

- `GET /api/admin/factory/monthly-detail` — 월간 생산 현황 상세 (view_access_required)
- `GET /api/admin/factory/weekly-kpi` — 주간 KPI 대시보드 (gst_or_admin_required)
- test_factory.py 18 passed
- factory.py 블루프린트 신규 (12번째)

---

## ✅ Sprint 27-fix 완료 (2026-03-15) — Task Seed Silent Fail + SINGLE_ACTION UI

### 근본 원인
`022_add_task_type.sql` migration 미적용 상태에서 task seed가 `task_type` 컬럼 참조 → silent fail (`logger.warning`으로 삼킴).

### 해결
- 에러 로깅 강화 (warning → error + traceback) — 향후 silent fail 방지
- migration 적용 후 GBWS-6869, GBWS-6867 각각 20개 task 생성 확인
- debug 엔드포인트 추가 → 원인 확인 → 제거 완료
- BE task 목록 API에 `task_type` 필드 추가 (누락 수정)
- FE task_management_screen: SINGLE_ACTION task에 녹색 "완료" 버튼 표시 (Netlify 배포 완료)

---

## ✅ Sprint 27 완료 (v1.7.4, 2026-03-14) — 단일 액션 Task (task_type)

### 개요
app_task_details 테이블에 `task_type VARCHAR(20) DEFAULT 'NORMAL'` 컬럼 추가. 기존 시작/종료 2-step → 완료 체크만(SINGLE_ACTION) 지원.

| Task | 공정 | 현재 | 변경 | 주체 |
|------|------|------|------|------|
| Tank Docking | MECH | 시작/종료 (NORMAL) | 단일 액션 (SINGLE_ACTION) | MECH 담당 |
| 출하완료 (SI_SHIPMENT) | SI (신규) | 없음 | 단일 액션 (SINGLE_ACTION) | SI 담당 |

### 구현 완료 항목
- 022_add_task_type.sql migration (Railway DB 적용 완료 2026-03-14)
- TaskDetail model + complete_single_action()
- TaskSeed update (TANK_DOCKING→SINGLE_ACTION, SI_SHIPMENT 신규, total 20)
- POST /work/complete-single 엔드포인트
- TaskItem.dart taskType 필드 + isSingleAction getter
- task_detail_screen.dart 단일 액션 "완료" 버튼 UI
- FE service/provider completeSingleAction()
- ⚠️ migration 미적용으로 task seed silent fail 발생 → 2026-03-14 적용으로 해결

---

## ✅ ETL pi_start 변경이력 지원 (2026-03-14) — CORE-ETL Sprint 2-A 연동

### 개요
CORE-ETL에서 pi_start(가압시작) 변경이력 추적 추가에 따른 OPS BE 수정.

### 변경 내역
- `backend/app/routes/admin.py`: `_FIELD_LABELS`에 `'pi_start': '가압시작'` 추가 (5→6개)
- GET `/api/admin/etl/changes`에서 `field=pi_start` 필터 + 한글 라벨 표시 지원
- **연관 변경**: CORE-ETL step2_load.py `TRACKED_FIELDS`에 `'pressure_test': 'pi_start'` 추가 (별도 repo)
- **VIEW FE**: FIELD_CONFIG, DATE_FIELDS, KPI 그리드 6열, 주간 차트 — VIEW 별도 진행

---

## ✅ Sprint 28 완료 (v1.7.5, 2026-03-13)

### AXIS-VIEW 권한 데코레이터 재정비
- `get_current_worker()` 캐싱 헬퍼 추가 (request 당 1회 DB 조회)
- `admin_required`, `manager_or_admin_required` 내부 → 캐싱 리팩토링
- `@gst_or_admin_required` 신규 (GST 소속 + Admin만 허용, 공장 대시보드 전용)
- `@view_access_required` 신규 (GST + Admin + Manager, VIEW 전체 공개 API)
- QR 엔드포인트: 자사필터로 처리하여 데코레이터 변경 불필요 → 제거
- `admin.py` ETL 변경이력: `@manager_or_admin_required` → `@view_access_required`
- DB 스키마 변경 없음, FE 변경 없음
- pytest: 667 passed (regression 0건)

---

## ✅ Sprint 26 완료 (v1.7.3, 2026-03-12)

### PWA-1: ✅ SW 업데이트 토스트 — 완료
- index.html: controllerchange + updatefound 감지 → 하단 토스트 표시 → 탭하면 reload

### PWA-2: ✅ 업데이트 내용 팝업 — 완료
- UpdateService: SharedPreferences 버전 비교 → notices API 호출 (최초 1회)
- UpdateDialog: GxDesignSystem 팝업 (버전 뱃지 + 본문 스크롤 + 확인 버튼)

### DB-PROTECT: ✅ conftest.py 운영 데이터 보호 강화 — 완료
- workers, hr 스키마, auth 스키마, admin_settings, model_config DROP 제거

---

## ✅ Sprint 25 완료 (v1.7.2, 2026-03-12)

### BUG-22: ✅ Logout Storm 수정 — 완료
- FE: `_authSkipPaths` + `_isForceLogout` + `_isLoggingOut` 3중 방어
- BE: `jwt_optional` 데코레이터 + logout `@jwt_optional` 변경

### pytest 전체 실행 결과: 643 passed / 44 failed / 12 skipped
- 실패 원인: 코드 버그 0건 — 테스트 코드 데이터 불일치 + DB 상태 간섭
- Task Seed count 수정 (PI/QI/SI 추가: GAIA 15→19, 기타 13→17)
- `create_test_worker` 잔여 데이터 cleanup 추가
- `test_auth.py` Sprint 24 login 에러 분리 반영 (404 ACCOUNT_NOT_FOUND)

### TEST-FIX: ✅ 테스트 수정 3건 — 완료
- `test_model_task_seed_integration.py` — seed count assertions 업데이트
- `conftest.py` — create_test_worker에 pre-insert cleanup 추가
- `test_auth.py` — Sprint 24 login error 코드 변경 반영

---

## ✅ Sprint 24 완료 (v1.7.1, 2026-03-11)

### 핫픽스 (BUG-18~21):
- BUG-18: GST Manager 출퇴근 데이터 미표시 → GST manager는 전체 접근
- BUG-19: 비밀번호 찾기 없는 이메일 → 404 EMAIL_NOT_FOUND 반환
- BUG-20: 로그인 에러 분리 → 404 ACCOUNT_NOT_FOUND + 401 INVALID_PASSWORD
- BUG-21: FE 404 하드코딩 → 서버 메시지 그대로 표시

---

## ✅ Sprint 23 완료 (v1.7.0, 2026-03-11)

### OPS-1: ✅ is_manager 로그인 시 권한 부여 메뉴 표시 — 완료
### OPS-2: ✅ 관리자 옵션 메뉴 위치 이동 (공지사항 위) — 완료

### VIEW-1: ETL 변경이력 알림 뱃지 (Header + 사이드바) — 예정 (VIEW 프로젝트)
- `/api/admin/etl/changes?days=1` → total_changes - last_seen = unread count
- Header.tsx 알림 아이콘 + 사이드바 "변경이력" 뱃지

### VIEW-2: Admin 간편 로그인 (prefix 매칭) — 예정 (VIEW 프로젝트)
- BE `get_admin_by_email_prefix()` 이미 구현됨
- VIEW LoginPage.tsx에서 `@` 미포함 시 prefix 로그인 호출

---

## ✅ Sprint 22-A/B 완료 (2026-03-10)

### SEC-1: ✅ email_verified 완료 시 Admin 승인 알림 — 완료
### SEC-2: ✅ 이메일 재인증(재전송) 엔드포인트 — 완료 (BE만, FE 연동은 별도)
### SEC-3: ✅ GPS enableHighAccuracy: true — 완료
### SEC-4: ✅ DMS→Decimal 변환 헬퍼 — 완료

### DB-1: DB 보호 정책
- **배경**: HR 테이블(출퇴근, 근무자)은 운영 데이터 — 손실 불가
- **보호 대상**: `workers`, `partner_attendance`, `qr_registry`
- **현재 Railway 환경**: 테스트 DB = 운영 DB (동일 인스턴스)
  - Railway Pro 자동 일일 백업 + 7일 보관 ✅
  - BE 코드 push는 DB에 영향 없음 (코드와 DB 분리)
- **conftest.py 백업/복원 현황**:
  - ✅ `workers` — backup/restore 구현됨
  - ✅ `hr.worker_auth_settings` — backup/restore 구현됨
  - ✅ `hr.partner_attendance` — backup/restore 구현됨
  - ✅ `qr_registry` — backup/restore 구현됨 (Sprint 22-E)
  - ✅ `plan.product_info` — backup/restore 구현됨 (Sprint 22-E)
- **운영 규칙**: ALTER TABLE 실행 전 반드시 수동 pg_dump
- **최종 목표**: 사내 WAS DB로 마이그레이션 → production 분리 운영

### PM-1: ✅ PM Role push + Manager 권한 위임 구조 — 완료 (Sprint 22-C, v1.6.2)

**PM Role**: ✅ 완료 (코드 + Railway DB enum 추가)

**Manager 권한 위임**: ✅ 완료 (Sprint 22-C)
- `toggle_manager()`: `@admin_required` → `@manager_or_admin_required` 변경
- Manager: 같은 company 소속만 is_manager 부여/해제 가능
- Admin 보호: Manager → Admin 권한 변경 시 403
- 테스트 5/5 통과 (기존 5개 + 신규 5개 = 10개 전체 통과)

---

## 🟡 재검토 (Review Needed)

보류해둔 항목. 다음 Sprint 기획 시 우선 검토.

### RV-4: Flaky 테스트 안정화 (중간 리스크 3건)
- **배경**: Sprint 19 회귀 테스트에서 23건 실패 — 모두 기존 flaky 테스트 (신규 코드 결함 아님)
- **중간 리스크 그룹**:
  1. **test_pause_resume** — 타이밍 의존성 (`sleep` 기반 검증). 운영 기능은 정상이나 CI에서 간헐적 실패. 재현 불안정하여 디버깅 어려움
  2. **test_scheduler_integration** — APScheduler 초기화 타이밍 + DB 상태 간섭. 스케줄러 자체는 production에서 정상 동작하나, 테스트 격리 부족으로 실행 순서에 따라 실패
  3. **test_pin_auth** — 테스트 간 DB 상태 공유로 인한 실행 순서 의존성. PIN 인증 기능 자체는 정상
- **낮은 리스크 그룹** (기록만): test_product_api, test_task_seed, test_sprint10_fixes — DB fixture 간섭이 원인, 운영 리스크 없음
- **권장 조치**: 테스트 격리 개선 (각 테스트 전후 DB 롤백), 타이밍 기반 → 이벤트 기반 검증으로 리팩터링
- **우선순위**: 중 (CI/CD 구축 전에 해결 권장)
- **등록일**: 2026-03-06

### RV-1: checklist 스키마 vs 실제 Excel 양식 불일치
- **배경**: `출하 어플용의 사본.xlsx` (sheet=DB) 분석 결과, 현재 checklist_master 스키마(단순 item_name 기반)와 실제 데이터 구조가 다름
- **현재 스키마**: product_code + category + item_name
- **실제 Excel**: 자재코드(material_code) + 자재내역 + 규격1/규격2 + 수량 + 단위 + 상태(OK/NG)
- **차이점**: 현재는 체크리스트 "항목명"만 있지만, 실제는 BOM(자재 목록) 기반으로 각 자재별 OK/NG 판정
- **필요 작업**:
  - checklist_master에 material_code, spec1, spec2, qty, unit 컬럼 추가 검토
  - item_master 테이블 분리 여부 결정
  - status를 PENDING/OK/NG/NA로 확장
  - Excel ETL import 로직 수정
- **DB 현황**: checklist 스키마 생성됨, 테이블 비어있음 (테스트는 임시 데이터로 통과)
- **결정 시점**: Sprint 13 이전

### RV-2: FE 전역 시간 표시 검증
- **배경**: Sprint 11 핫픽스로 4개 화면 `.toLocal()` 추가했지만, 다른 화면에도 같은 문제 있을 수 있음
- **확인 대상**: 모든 DateTime 표시 화면에서 `.toLocal()` 호출 여부
- **우선순위**: 낮음 (현재 수정된 4개 화면이 주요 사용 화면)

### RV-3: 앱 아이콘 최적화
- **배경**: G 다이아몬드 심볼로 favicon + PWA 아이콘 생성 완료, 모바일 홈화면 아이콘 크기 미세 조정 필요
- **현재**: 72% fill ratio로 생성, 사용자 피드백 대기
- **우선순위**: 낮음

---

## 🟠 배포 준비

| ID | 항목 | 설명 | 상태 |
|----|------|------|------|
| DP-1 | Railway Flask API 설정 | `axis-ops-api.up.railway.app` | ✅ 완료 |
| DP-2 | GitHub commit/push | Sprint 5~12 + 배포설정 push 완료 | ✅ 완료 |
| DP-3 | FE apiBaseUrl 변경 | `constants.dart` → Railway 도메인으로 변경 | ✅ 완료 |
| DP-4 | PWA 배포 | `flutter build web` → Netlify `gaxis-ops.netlify.app` 배포 | ✅ 완료 |
| DP-5 | 베타 테스트 | 현장 작업자 실사용 테스트 | 대기 (BUG-1 해결 후) |
| DP-6 | CI/CD 구축 | GitHub Actions (CLAUDE.md에 추후로 기록됨) | 추후 |

**현재 배포 URL**:
- FE (PWA): `https://gaxis-ops.netlify.app`
- BE (API): `https://axis-ops-api.up.railway.app`

**로컬 테스트**: `constants.dart`에서 apiBaseUrl을 `http://localhost:5001/api`로 변경 후 `flutter run -d chrome`

---

## 📋 VIEW 생산관리 페이지 검토 (2026-03-13)

### 생산일정 (ProductionPlanPage)
- **GST 공정 일정만 표시** (PI/QI/SI + 출하). MECH/ELEC은 변수가 많고 OPS에서 트래킹
- GST 공정은 보통 하루 만에 끝남 → 현황 파악 용이
- 파이프라인 라벨: **가압(PI) → 공정(QI) → 포장(SI) → 출하**. 자주검사 삭제
- 출하 컬럼 = finishing_plan_end 값 확정
- API: #10 monthly-detail 그대로 사용, 권한 @view_access_required
- **BE 추가 코드 거의 없음** — 엔드포인트 구현 1개뿐

### 생산실적 (ProductionPerformancePage)
- **협력사 실적 처리용 페이지** (MECH/ELEC/TM). GST 공정은 QMS I/F로 자동 처리
- **확인 주체: PM**. OPS progress 100% → VIEW 반영(react) → PM 확인 → SAP key 값 저장
- 혼재 태그 (P&S/C&A): 업체별 개별 확인 필요 → 행/셀 단위 처리 + 추후 일괄 처리
- 월마감 탭: 주간 결과 합산 — 실제 완료 count vs 실적처리 count (미처리 건수 체크)
- 일괄확인: OPS progress 100% 건에 대한 실적 일괄 승인 처리
- SAP key 값 매핑 columns 확인 필요 (내용 정리 우선)

### 출하이력 (ShipmentHistoryPage)
- finishing_plan_end = 출하예정일, actual_ship_date = 실제출하일
- 데이터 소스 확정 대기, 출하 지연 상태 추가 검토 필요
- 기간/고객사 필터 추가 권장

### 출하 확인 프로세스 (전체 흐름)
1. **OPS App**: SI 담당자가 QR 스캔 → "출하완료" task 체크 (단일 액션)
2. **BE 자동 처리**: actual_ship_date = NOW() + qr_registry.status = 'shipped'
3. **VIEW 생산실적**: 공정별 "확인" 버튼 활성화 → 실적 확인
4. **VIEW 생산관리(PM)**: 최종 승인 → SAP key-in 값 저장
5. **CORE-ETL**: actual_ship_date 덮어쓰기 방지 (CASE 분기)
- SAP/QMS 매핑 data thread 값은 추후 정의 예정

---

## 🔵 추후 구현 (Phase 로드맵)

CLAUDE.md Phase 계획 기반. 시급도순.

### Phase A 잔여: 생체인증
- **내용**: 지문/FaceID — WebAuthn API (HTTPS + Flutter Web JS interop)
- **현재**: Sprint 12에서 메뉴 UI만 생성 + "추후 오픈 예정" 안내
- **의존성**: PWA 배포(HTTPS) 완료 ✅

### Phase B 잔여: Admin 출퇴근 대시보드
- **내용**: 협력사 출퇴근 현황 조회 (당일 + 월간 집계)
- **결정**: App에서 제외 → AXIS-VIEW (React 대시보드)에서 구현
- **BE API**: ✅ Sprint 19-E 완료 — `/api/admin/hr/attendance/today`, `/attendance?date=`, `/attendance/summary`
- **남은 작업**: 월간 집계 API (GET /api/admin/hr/attendance/monthly) 추후 필요 시 추가
- **의존성**: hr.partner_attendance 테이블 (Sprint 12에서 생성)

### Phase B 잔여: GST 근태 확장
- **내용**: hr.gst_attendance 테이블은 Sprint 12에서 생성, API/UI 미구현
- **용도**: 그룹웨어 RDB 연동 or 동기화
- **시기**: 미정 (그룹웨어 연동 계획 수립 후)

### Phase C: BOM 검증
- **내용**: product_bom 테이블 + bom_checklist_log
- **관련**: RV-1 (checklist 스키마 재검토)과 연결될 수 있음
- **시기**: checklist 스키마 확정 후

### ~~WebSocket 실시간 통신 정식 구현~~ → ✅ Sprint 13 완료
- Sprint 13에서 flask-sock(raw WS) 마이그레이션으로 해결
- FE `web_socket_channel`과 BE `/ws` 엔드포인트 정합성 확보

### ~~QR ETL 자동화 파이프라인~~ → axis-core-etl repo로 분리 완료 (2026-03-09)
- **상태**: 별도 repo(`axis-core-etl`)에서 관리 → `AXIS-CORE/CORE-ETL/BACKLOG.md` 참조
- **QR 라벨 관리 페이지**: 별도 검토 (라벨기 자동생성으로 우선순위 낮아짐)

### ~~Geolocation 기반 접속 보안 (2차 보안)~~ → ✅ Sprint 19-D 완료
- Sprint 19-D에서 구현 완료
- admin_settings 5개 키 (geo_check_enabled, geo_latitude, geo_longitude, geo_radius_meters, geo_strict_mode)
- FE: 출퇴근 시 GPS 좌표 전송, Admin UI 위치 보안 설정
- BE: Haversine 거리 검증, soft/strict 모드, HQ 면제
- 11 tests passed

### ~~신규 가입 시 Admin 이메일 알림~~ → ✅ Sprint 20-A 완료
- Sprint 20-A에서 구현 완료
- email_service.py 신규: get_admin_emails() + send_register_notification()
- auth.py register 성공 시 Admin 전원 이메일 발송 (best-effort)
- 5 tests passed

### ~~공지사항 탭 (앱 내 업데이트 노트)~~ → ✅ Sprint 20-B 완료
- Sprint 20-B에서 구현 완료
- BE: notices 테이블 + 5개 CRUD API
- FE: 공지 목록/상세/작성 화면, 홈 메뉴 카드 추가
- 6 tests passed

### defect 스키마
- **내용**: 불량 분석, 추적, 리포트 (QMS 연동)
- **시기**: 미정

---

## 🟡 체크리스트 확장 설계 (MECH/ELEC/TM 자주검사)

> 마지막 업데이트: 2026-04-09
> 상태: MECH 전체 확정 (#1~#20), TM 확인 완료, VIEW 연동 설계 완료, **ELEC 양식 수집 완료 → Sprint 57 할당**

### 배경
- 기존 Sprint 11 `checklist` 스키마 (checklist_master + checklist_record) 확장
- VIEW 대시보드에서 마스터 항목 CRUD + APP에서 자주검사 토스트 팝업
- 실적확인(confirm) 연동: progress 100% + 체크리스트 완료 = 승인 가능

### MECH 양식 분석 (기구 조립 검사 성적서)
- 소스: `현황판_260108_MFC Maker추가 260223.xlsm` → sheet `공정진행현황-2행`
- **20개 그룹, 약 60개 항목** (#1~#20 전체 확인 완료)

**#1~#6** (cols 1~130):

| # | inspection_group | CHECK 항목 | INPUT 항목 | 비고 |
|---|---|---|---|---|
| 1 | 3Way V/V | Spec 확인, 볼트 체결 (2) | 없음 | |
| 2 | WASTE GAS | 배관 도면 일치, 클램프 체결 (2) | 없음 | |
| 3 | INLET | 배관 도면 일치 (1) | 배관 S/N 확인 Left#1~#4/Right#1~#4 (1) | DRAGON 전용 — 비DRAGON은 NA. `product_info` 참조 |
| 4 | BURNER | SUS Fitting 조임, Gas Nozzle Cover 휨, 클램프 체결 (3) | 없음 | |
| 5 | REACTOR | Fitting 조임, Tube 조립, 클램프 체결, Cir Line Tubing (4) | 없음 | |
| 6 | GN2 | Sol V/V Spec/Flow, SUS Fitting 조임, Tube 조립, Speed Controller 방향 (4) | Speed Controller 수량 EA (1) + MFC Spec (1) | |

**#7~#20** (cols 131~260):

| # | inspection_group | CHECK 항목 | INPUT 항목 | 비고 |
|---|---|---|---|---|
| 7 | LNG | MFC Spec/Flow 방향, SUS Fitting 조임, Part 조립 (3) | MFC Maker/Spec 정보 (1) | |
| 8 | O2 | MFC Spec/Flow 방향, SUS Fitting 조임, Part 조립 (3) | MFC Maker/Spec 정보 (1) | |
| 9 | CDA | Sol V/V Spec/Flow, SUS Fitting 조임, Part 조립, Speed Controller 방향 (4) | MFC Maker/Spec 정보 (1) + Speed Controller 수량 EA (1) | |
| 10 | BCW | Flow Sensor Spec/방향, 공압 밸브 Flow, SUS Fitting 조임, Part 조립 (4) | Flow Sensor Spec 정보 (1) | |
| 11 | PCW-S | Flow Sensor Spec/방향, 공압 밸브 Flow, SUS Fitting 조임, Part 조립 (4) | Flow Sensor Spec 정보 (1) | |
| 12 | PCW-R | Flow Sensor Spec/방향, 공압 밸브 Flow, SUS Fitting 조임, Part 조립 (4) | Flow Sensor Spec 정보 (1) | |
| 13 | Exhaust | Packing 조립, Packing Guide 고정, SUS Fitting 조임, BCW Nozzle Spray (4) | 없음 | |
| 14 | TANK | Cir Pump Spec, Flow Sensor Swirl Orifice, Tank 내부 이물질 (3) | 없음 | |
| 15 | PU | 버너 및 이그저스트 위치 (1) | 없음 | |
| 16 | 설비 상부 | SUS Fitting 조임, Drain Nut 조립, 미사용 Hole 막음 (3) | 없음 | |
| 17 | 설비 전면부 | Interface 스티커 부착 (1) | 없음 | |
| 18 | H/J | 배관 H/J 완전체 조립, 벨크로 체결, 케이블 정리 (3) | 없음 | |
| 19 | Quenching | Flow Sensor Spec/방향, Flow Sensor 위치 (2) | 없음 | |
| 20 | 눈관리 | 눈관리 스티커 위치 (1) | 없음 | |

- **가압검사 섹션**: 체크리스트 범위에서 **제외**
- **ISSUE사항**: 체크리스트 외 별도 기록란 (범위 외)

### TM 양식 분석 (이미지 기준)
- 총 15개 항목: BURNER(3) + REACTOR(4) + Exhaust(4) + TANK(4)
- MECH와 컬럼 구조 동일 (검사 항목/검사 내용/기준·SPEC/검사 방법/1차판정/작업자/2차판정/비고)

### 스키마 확장 — checklist_master 컬럼 추가

| 컬럼명 | 타입 | 매핑 | 비고 |
|--------|------|------|------|
| `inspection_group` | VARCHAR(100) | 검사 항목 그룹 (BURNER/LNG/BCW 등) | 그룹핑 레이어 |
| `item_name` | VARCHAR(255) | 검사 내용 | 기존 컬럼 유지 |
| `item_type` | VARCHAR(10) DEFAULT 'CHECK' | **CHECK** = PASS/NA 판정 항목 / **INPUT** = 직접 입력 항목 | 신규 핵심 |
| `spec_criteria` | VARCHAR(255) | 기준/SPEC (GAP GAUGE 등) | 신규 |
| `inspection_method` | VARCHAR(100) | 검사 방법 (측수 검사/육안 검사) | 신규 |
| `second_judgment_required` | BOOLEAN DEFAULT FALSE | 2차판정 옵션키 | 카테고리 단위 ON/OFF |

### item_type 동작
- **CHECK** (`item_type = 'CHECK'`): APP UI에서 PASS/NA 버튼 표시 → `checklist_record.status`에 저장
- **INPUT** (`item_type = 'INPUT'`): APP UI에서 텍스트 입력 필드 표시 → `checklist_record.note`에 저장
  - MFC Maker/Spec 정보 (LNG, O2, CDA, GN2)
  - Flow Sensor Spec 정보 (BCW, PCW-S, PCW-R)
  - Speed Controller 수량 (CDA, GN2)
  - 배관 S/N (INLET — 해당 제품만 대시보드에서 항목 추가)
- **INPUT 항목은 선택 입력** — 비어있어도 실적 승인에 영향 없음 (실적 승인 조건은 CHECK 항목 전체 판정 완료만 확인)

### 설계 원칙: 대시보드 중심 관리
- product_info JOIN 등 코드 레벨 조건부 로직 **사용 안 함**
- 제품별 항목 차이(DRAGON 배관 S/N, 신규 추가 항목 등)는 **VIEW 대시보드에서 해당 product_code에 항목 추가/수정/비활성화로 관리**
- 모든 설정값·변경값은 대시보드에서 edit 가능한 구조로 통일
- BE는 master 테이블 데이터만 충실히 서빙하면 됨 (비즈니스 로직 최소화)

### 스키마 확장 — checklist_record 변경

| 변경 | 현재 | 제안 |
|------|------|------|
| `is_checked` BOOLEAN | TRUE/FALSE | → `status` VARCHAR(10): **PASS / NA** 2가지만 (CHECK 항목용) |
| 단일 판정 | 1회 | → `judgment_round` INTEGER DEFAULT 1 (1차=1, 2차=2) |
| UNIQUE 제약 | `(serial_number, master_id)` | → `(serial_number, master_id, judgment_round)` |

- 미검사 = record 행 없음 (LEFT JOIN 시 NULL). PENDING 상태 불필요
- 비고(`note`): APP에서 직접 입력 가능 (기존 컬럼 유지)
- INPUT 항목: `status` = NULL, `note`에 입력값 저장

### 옵션키 동작 (second_judgment_required)
- **OFF (기본)**: 전항목 1차판정 완료 (CHECK→PASS/NA, INPUT→note 입력) → 실적 승인 가능
- **ON**: 전항목 1차 + 2차판정 모두 완료 → 실적 승인 가능
- TM/MECH/ELEC 동일 조건으로 적용

### 누락 BE API — Admin CRUD (VIEW 대시보드용)

| 엔드포인트 | 메서드 | 용도 | 권한 |
|---|---|---|---|
| `/api/admin/checklist/master` | GET | 마스터 목록 (category, product_code 필터) | admin/manager/gst(pm) |
| `/api/admin/checklist/master` | POST | 개별 항목 생성 | admin/manager/gst(pm) |
| `/api/admin/checklist/master/{id}` | PUT | 항목 수정 | admin/manager/gst(pm) |
| `/api/admin/checklist/master/{id}` | DELETE | 비활성화 (soft delete → is_active=FALSE) | admin |

### VIEW FE 구성

#### 1. 생산관리 > 체크리스트 관리 (마스터 CRUD)
- 필터 바: product_code 드롭다운 + category 탭 (TM/MECH/ELEC)
- 마스터 항목 테이블: item_order 순, 인라인 수정/비활성화
- item_type 구분 표시 (CHECK 뱃지 / INPUT 뱃지)
- 항목 추가: 모달 또는 인라인 폼 (item_type 선택 포함)
- TanStack Query v5 (useQuery + useMutation + invalidateQueries)

#### 2. 생산현황 > S/N 디테일 패널에 체크리스트 연동
- **현재 구조**: SNStatusPage → S/N 카드 클릭 → SNDetailPanel(480px 슬라이드인) → ProcessStepCard(MECH/ELEC/TMS...) 확장 → 작업자 태깅 정보
- **추가**: ProcessStepCard 확장 시 작업자 정보 아래에 **체크리스트 현황 섹션** 표시
- **API 방식**: 옵션 B — 기존 `GET /api/app/checklist/{SN}/{category}` 별도 호출 (BE 변경 0, APP과 동일 API 공유)
- **FE 추가**: `useChecklist.ts` 훅 신규 → 카드 확장 시 task + checklist 병렬 fetch
- **표시 내용**:
  - 체크리스트 완료율 (예: ✅ 12/15 완료 + 프로그레스 바)
  - 미완료 항목 리스트 (inspection_group + item_name)

#### 3. S/N 카드 레벨 체크리스트 요약 (Phase 2)
- **목적**: 카드 목록만 봐도 체크리스트 상태 확인 (예: 진행률 바 옆에 ✅ 3/3 또는 ⚠️ 2/3 아이콘)
- **구현**: BE 집계 API 신규 — `GET /api/admin/checklist/summary`
  - 파라미터: `serial_numbers` (복수 S/N)
  - SQL 한 번으로 S/N×category별 total/checked 집계
  - FE에서 progress API 호출 후 반환된 S/N 목록으로 summary API **1회 추가 호출** (총 2회)
- **우선순위**: 후순위. 디테일 패널 연동 먼저 완성 후, 필요 시 추가

### APP 트리거
- MECH/ELEC/TM 자주검사 시작 → 토스트 팝업 체크리스트 표시
- CHECK 항목: PASS/NA 버튼
- INPUT 항목: 텍스트 입력 필드 (비고와 동일 UX)
- 기존 GET/PUT API 사용 (status 타입 + item_type 분기 추가)

### 연동 흐름
```
VIEW: 마스터 CRUD (CHECK/INPUT 항목 관리)
→ APP: 자주검사 시작 → 체크리스트 팝업
→ 작업자: CHECK→PASS/NA 판정 / INPUT→텍스트 입력 + 비고 입력
→ 전항목 완료 + progress 100% = 실적확인 승인 활성화
→ VIEW 생산현황: S/N 디테일에서 체크리스트 완료 현황 확인
```

### 구현 우선순위
1. **BE**: checklist_master/record 스키마 확장 (migration) + Admin CRUD API 4개
2. **VIEW**: 체크리스트 관리 페이지 (마스터 CRUD UI)
3. **VIEW**: 생산현황 ProcessStepCard 체크리스트 연동 (옵션 B)
4. **APP**: 자주검사 토스트 팝업 (기존 API 활용)
5. **BE+VIEW**: S/N 카드 레벨 summary 집계 API (Phase 2)

### 미결정 사항
- RV-1: 단순 item_name vs BOM 기반 확장 → ~~ELEC 양식 확인 후 최종 결정~~ **ELEC 양식 수집 완료 (2026-04-09)**
- `second_judgment_required` 저장 위치: master 행마다 vs 별도 설정 테이블 (admin_settings 등)
- ~~ELEC 양식 수집 대기 중~~ **✅ 완료 — 전장외주검사성적서 3그룹 24항목 + GST 검증 7항목**
- **Sprint 57 할당**: ELEC 공정 시퀀스 변경 + 체크리스트 구현 (AGENT_TEAM_LAUNCH.md 참조)

### ELEC 양식 분석 (전장외주검사성적서)
> 소스: `+_전장외주검사성적서.xlsx` → sheet `GIAA-I S SEC (2)`
> Sprint 57 할당 (2026-04-09)

| Group | 항목 수 | 검사주체 | 비고 |
|-------|--------|---------|------|
| PANEL 검사 | 11 | ELEC 외주 전담 (2~3명) | 1차/2차 동일 인원 |
| 조립 검사 | 6 | ELEC 외주 전담 (동일) | 버너 위 배선 1차 N.A |
| JIG 검사 및 특별관리 POINT | 7 + 7(GST) | ELEC 외주 + QI | GST 담당자 별도 phase |

**ELEC 공정 시퀀스 변경**:
- INSPECTION: FINAL → freeroll (시작 시 체크리스트 팝업)
- IF_2: → FINAL (ELEC 닫기 트리거)
- 닫기 조건: 체크리스트 완료(GST 제외) + IF_2 완료
- **TM과 공통 패턴**: `checklist_ready` + `checklist_category` 응답

---

## 🟡 SEC-01 상세: 인프라 시크릿/CORS 정리 (H-04 + H-05)

> **상태**: BACKLOG (리팩토링 후 착수, 2026-04-21 등록)
> **출처**: `SECURITY_REVIEW.md` H-04 / H-05 (Phase 2 점검)
> **착수 시점**: REF-BE-13 (auth_service.py 1,108 LOC 분할) 완료 직후 권장
> **이유**: JWT 시크릿 참조가 auth_service.py / jwt_auth.py / config.py 에 얽혀있음. God File 분할 전 수정 시 regression 리스크 가중

### 착수 이유 / 리팩토링 선행 근거

- H-05 JWT 시크릿 교체는 `auth_service.py:144/172/189` 와 `jwt_auth.py:71/126/141` 에 걸쳐 6곳 참조. `auth_service.py` 가 1,108 LOC God File 상태라 수정 시 로그인·refresh·소켓 인증 전반의 회귀 테스트 범위가 큼.
- REF-BE-13 이후 `auth_core.py` / `auth_token.py` / `auth_email.py` 로 분리되면 시크릿 참조가 `auth_token.py` 한 곳으로 응집 → H-05 수정 diff 가 작고 리뷰 용이.
- H-04 CORS 는 `__init__.py` 단독 수정이라 리팩토링과 독립 가능하나, env 주입/배포 타이밍을 맞추기 위해 H-05 와 같은 Sprint 로 묶는 것이 효율적.

### 수정 대상

| 항목 | 위치 | 규모 |
|---|---|---|
| H-04 CORS allowlist | `backend/app/__init__.py:40-45` | +10/-4 줄 |
| H-05a JWT secrets | `backend/app/config.py:27-35` | +6/-10 줄 |
| H-05b DATABASE_URL | `backend/app/config.py:21-24` | +2/-4 줄 |
| H-05 공통 helper | `backend/app/config.py` 상단 | +5줄 (`_require_env`) |
| Railway env 세팅 | Railway 대시보드 | 4개 변수 추가/갱신 |

### 병행 조치 (코드 외)

1. **Railway DB 비밀번호 rotation**: `config.py:23` 에 fallback 으로 박혀있는 자격증명 (`maglev.proxy.rlwy.net:38813` 접근 키) 은 git 에 노출된 상태 → 무효화 필요
2. **CORE-ETL / AXIS-VIEW-ETL env 동기화**: 같은 DB 를 쓰므로 password 교체 시 연쇄 업데이트
3. **git 히스토리 스캔**: `git log -S "aemQKKvZ..."` 로 커밋 이력 확인 → 필요 시 `git filter-repo` 로 삭제 (선택)

### 배포 타이밍 리스크

- JWT_SECRET_KEY 가 바뀌면 **기존 refresh_token(30일) 전부 무효** → 현장 작업자 전원 재로그인
- 점심시간·새벽 배포 권장 + 사내 공지 선행
- Railway env 선주입 → 코드 배포 → 자동 재시작 → 실패 시 이전 커밋 revert 가능 상태로 진행

### 사용자 확인 필요 (착수 전)

1. CORS allowlist 에 넣을 운영 도메인 목록 (VIEW Netlify URL, OPS Flutter PWA URL, 자사 도메인)
2. Railway env 에 JWT_SECRET_KEY / JWT_REFRESH_SECRET_KEY 가 현재 실제 세팅돼 있는지 (세팅돼 있으면 그 값 유지, 없으면 신규 생성)
3. DB password rotation 가능한 시간대
4. CORE-ETL / VIEW-ETL DATABASE_URL 저장 위치 (로컬 .env / GitHub Actions Secret / Railway)
5. 외부 모니터링이 `/health` 호출 중인지

### 참조

- `SECURITY_REVIEW.md` H-04 / H-05 상세 + 권장 수정 코드
- CLAUDE.md § 🛡️ 리팩토링 안전 규칙 7원칙
- REF-BE-13 (auth_service.py 분할) 완료 후 본 Sprint 착수

---

## 🟡 BUG-41 상세: PWA 업데이트 시 PIN 초기화 + 이메일 재입력 요구

> **상태**: BACKLOG (우선순위 보류, 2026-04-15 등록)
> **환경**: Chrome PWA 전용 (데스크톱/모바일 모두). iOS Safari 미사용
> **증상**:
> 1. 앱 업데이트 알림 후 reload → PIN 로그인 화면이 아닌 초기 이메일 로그인 화면으로 진입
> 2. 이메일을 전체 다시 입력해야 로그인 가능
> 3. 비밀번호 재입력 + PIN 재등록까지 매 업데이트마다 반복

### 영향 범위

- **사용자 불편**: 매 업데이트(주 1~2회)마다 전 사용자 재로그인 + PIN 재등록
- **업무 영향**: 현장 작업자가 업데이트 직후 수 분간 작업 불가
- **보안 이슈 아님**: 데이터 손실/무단 접근 없음, 단순 UX 열화

### 원인 분석 (요약)

**PWA + `flutter_secure_storage_web` 조합의 구조적 문제**
- `flutter_secure_storage_web` 9.x는 localStorage에 AES 키 + 암호화된 값을 함께 저장
- 웹에서는 "보안 저장소"라는 이름과 달리 실제 보안 이점 거의 없음 (AES 키 평문 노출)
- Flutter Web 빌드 해시 변경 시 부트스트랩 시점에 키 동기화 실패 케이스 발생
- PWA 서비스워커 업데이트 후 첫 로드 시 storage 초기화 타이밍 이슈 가능

**관련 파일 및 라인** (2026-04-15 기준)
- `frontend/lib/services/auth_service.dart:12` — `FlutterSecureStorage()` 기본 옵션
- `frontend/lib/services/auth_service.dart:20` — `_pinRegisteredKey` SecureStorage 저장
- `frontend/lib/services/auth_service.dart:349-360` — `hasPinRegistered()` / `savePinRegistered()`
- `frontend/lib/services/update_service.dart:14-39` — 버전 감지 (lastSeen 비교)
- `frontend/lib/main.dart:259-273` — AppStartup PIN 체크 분기
- `frontend/web/index.html:180-232` — SW 업데이트 토스트 (이미 구현됨)

### 제안 해결안 (Sprint 60-FE 후보)

**Task 1 — `navigator.storage.persist()` 호출**
- 효과: Chrome evict 방지
- 리스크: 없음 (순수 추가 API)
- 변경 범위: `index.html` 또는 `main.dart` 부트스트랩 1곳

**Task 2 — PIN 등록 플래그를 SecureStorage → SharedPreferences 이전**
- 효과: `flutter_secure_storage_web` 암호화 키 동기화 실패 회피
- 보안 영향: 없음 (flag는 민감정보 아님, 값 자체는 서버 검증)
- ⚠️ **리스크: 기존 사용자 1회 강제 PIN 재등록** — 마이그레이션 로직 필수 포함
  ```dart
  // auth_service.dart hasPinRegistered() 일회성 마이그레이션
  if (prefs.containsKey(_pinRegisteredKey)) {
    return prefs.getBool(_pinRegisteredKey) ?? false;
  }
  // 첫 실행 — SecureStorage에서 마이그레이션 시도
  final legacy = await _secureStorage.read(key: _pinRegisteredKey);
  final registered = legacy == 'true';
  await prefs.setBool(_pinRegisteredKey, registered);
  return registered;
  ```
- 변경 범위: `auth_service.dart` (3 메서드), `logout()` 불일치 방지 (SharedPreferences 삭제 추가)

**Task 3 — 이메일 SharedPreferences 저장 + 로그인 화면 자동 채움**
- 효과: PIN이 날아가도 이메일 자동 채움 → 재입력 부담 대폭 감소
- 보안 영향: 저위험 (이메일은 민감도 낮음)
- ⚠️ 리스크: 공용 기기에서 이전 사용자 이메일 노출 → "내 계정 기억 안 함" 토글 필요할 수 있음
- 변경 범위: `auth_service.dart` + 로그인 화면

**Task 4 — SecureStorage read 예외 graceful handling**
- 효과: 복호화 실패 시 앱 크래시/무한 로딩 방지
- ⚠️ 주의: `deleteAll()`은 금지. 단순히 `false` 반환으로 처리 (일시적 IO 에러가 영구 데이터 손실로 악화 방지)
- 변경 범위: `auth_service.dart` 각 read 메서드

### Sprint 60-FE 규모 예상

- 코드 변경: `auth_service.dart`(주요), `main.dart`(부트스트랩), `login_screen.dart`(자동 채움), `index.html`(persist 호출) — **4~5 파일**
- 신규 테스트: PWA 업데이트 수동 시나리오(staging v1→v2), 기존 사용자 마이그레이션 시나리오
- 예상 기간: 2~3일 (구현) + 3~5일 (staging 검증) = **약 1주**

### 왜 지금 보류하나

1. **변경 범위가 인증 플로우 전반** — 마이그레이션 로직 없으면 배포 당일 전사 PIN 초기화 사태 유발
2. **Regression 테스트 비용 높음** — PWA 업데이트 시나리오는 자동화 어려움, 수동 검증 필수
3. **완전 해결이 아님** — Task 1+2+3+4 모두 적용해도 refresh_token 손실 시나리오는 여전히 남음 (완화 80%, 근본 해결 아님)
4. **근본 해결 대안**: refresh_token을 httpOnly 쿠키로 이전 (Flask-JWT + CORS 설정 변경 필요, 별도 Sprint 규모)
5. **우선순위**: 체크리스트/성적서/실적 확인 기능이 더 중요 (Sprint 58/59 계열 진행 중)

### 재개 조건

다음 중 하나라도 충족 시 Sprint 60-FE로 승격:
- 사용자 민원이 다른 우선순위 항목보다 심각해짐
- 업데이트 주기가 짧아져 사용자 고통 누적
- 다른 Sprint와 함께 묶을 수 있는 기회 발생 (예: 로그인 플로우 대규모 개선 시)
- refresh_token httpOnly 쿠키 이전 계획 수립 시 통합 Sprint로 진행

### 관련 분석 기록

- 분석일: 2026-04-15 (Twin파파 + Claude Opus 4.6 세션)
- 초기 진단: 네이티브 Flutter 앱 가정 → SecureStorage Keychain 손실 → 오진
- 재진단: PWA 환경 확인 → `flutter_secure_storage_web` localStorage 구조 이슈로 확정
- 배포 환경: Chrome 전용(데스크톱/모바일), iOS Safari 미사용으로 확정

---

## 🔴 BUG-42 상세: 명판 소형 QR 접사 인식 실패

### 환경
- **대상**: OPS PWA (Chrome 전용, 모바일/태블릿)
- **QR 소스**: 제품 명판(metal nameplate)에 각인/인쇄된 소형 QR — 스티커 QR 대비 면적 작음
- **비교 조건**: 동일 명판을 iOS/Android 기본 카메라 앱으로 촬영하면 QR 문자열 정상 읽힘
- **증상**: OPS 앱 스캐너 화면에서 같은 QR을 접사/근접 촬영해도 인식 안 됨 → timeout 또는 미검출

### 원인 분석

현재 스캐너 구현(`frontend/lib/services/qr_scanner_web.dart`)은 `html5-qrcode@2.3.8` (CDN, `web/index.html` L164)를 사용하며 카메라 제약을 **최소값**만 지정:

| 항목 | 현재 값 | 필요 값 |
|---|---|---|
| 라이브러리 | `html5-qrcode@2.3.8` | `@2.3.10` 또는 네이티브 `BarcodeDetector` API 병용 |
| 디코더 | zxing WASM (기본) | BarcodeDetector (OS 네이티브 / 훨씬 정확) |
| 해상도 constraint | 미지정 → 기본 640×480~1280×720 | `width: {ideal: 1920}, height: {ideal: 1080}` |
| 포커스 constraint | 미지정 | `focusMode: 'continuous'` + advanced |
| 줌 노출 | 없음 | `getCapabilities().zoom` 기반 슬라이더 UI |
| 손전등(Torch) | 없음 | `applyConstraints({advanced:[{torch:true}]})` |
| qrbox | 200 (고정 integer) | 컨테이너의 70-80% 동적 계산 |
| experimentalFeatures | 미사용 | `useBarCodeDetectorIfSupported: true` |

기본 카메라 앱이 잘 읽는 이유:
- 센서 최대 해상도(4K/12MP) 프레임 공급
- OS 레벨 Auto Focus + Macro Focus (하드웨어)
- OS 네이티브 QR 디코더 (iOS Vision / Android ML Kit) — 저해상도·기울어진 코드에 강함
- 사용자가 핀치 줌으로 확대 가능

현재 OPS 스캐너는 이 네 가지가 모두 빠져 있어 **QR 픽셀 밀도가 낮으면 디코딩 실패**.

### 관련 파일
- `frontend/lib/services/qr_scanner_web.dart` L305-469 — `startQrScanner()`, 특히 L376-389 `configScript` 주입 블록
- `frontend/web/index.html` L164 — `html5-qrcode@2.3.8` CDN 링크
- `frontend/lib/screens/qr/qr_scan_screen.dart` — UI 레이어 (줌/Torch 버튼 추가 위치)

### ⚠️ 제약 조건 — 프레임/레이아웃 절대 불변

**카메라 스캐너 프레임(컨테이너 크기·위치·정사각형 강제·뷰파인더 크기·CSS·`qrbox` 값)은 과거 20회 이상 반복 수정되어 현재 최적값. 본 BUG-42 수정 범위에서 절대 건드리지 않음.**

금지 영역 (수정 시 regression 고위험):
- `qr_scanner_web.dart` L23-250 — CSS 주입, DOM 생성, `_forceSquareAfterCameraStart()`, MutationObserver
- `qrbox: 200` 고정값
- `qr_scan_screen.dart` 의 레이아웃/UI 위젯 배치
- `web/index.html` 의 스캐너 관련 스타일

### 제안 Sprint 61-FE 태스크 (프레임 무변 범위만)

**Task 1: BarcodeDetector API 활성화 🎯 최우선 (한 줄 추가, 프레임 영향 0)**
`qr_scanner_web.dart` L376-383 `__qrScanConfig` 에 `experimentalFeatures` 한 줄 추가:
```js
window.__qrScanConfig = {
  fps: 10,
  qrbox: 200,  // ← 그대로 유지 (프레임 불변)
  experimentalFeatures: { useBarCodeDetectorIfSupported: true }  // ← 추가
};
```
- Chrome/Edge: OS 네이티브 `BarcodeDetector` 디코더 사용 → 소형 QR 인식률 급상승
- 미지원 브라우저: 자동 zxing 폴백
- **프레임/뷰파인더 크기 불변** — 디코더만 교체됨

**Task 2: 카메라 해상도 + 연속 포커스 제약 (프레임 영향 0)**
L402 / L421 / L443 의 `facingMode` 제약을 객체로 확장:
```js
const envConstraints = {
  facingMode: 'environment',
  width:  { ideal: 1920 },
  height: { ideal: 1080 },
  advanced: [{ focusMode: 'continuous' }]
};
```
- 센서 해상도만 상승. video 요소는 이미 L31-35 / L200-206 에서 `object-fit: cover` + `width/height: 100%` 로 컨테이너에 **crop** 처리되므로 화면 프레임 크기 불변
- `_forceSquareAfterCameraStart()` + MutationObserver (L189-250) 가 혹시 모를 크기 변경을 즉시 되돌림
- `focusMode: continuous` 는 OS 카메라 레벨 설정 — UI 영향 없음

**Task 3: 자동 줌 적용 (UI 추가 없음, 프레임 영향 0)**
카메라 시작 성공 직후(`_forceSquareAfterCameraStart` 이후) 헬퍼 1개 호출:
```dart
Future<void> _applyZoomIfSupported() async {
  // MediaStreamTrack.getCapabilities().zoom 확인
  // 지원 시 advanced: [{ zoom: min + (max-min) * 0.3 }] 자동 적용
  // 미지원 시 silent skip
}
```
- 약 30% 기본 줌을 **자동 1회만** 적용 → 명판 작은 QR 디코더 인식률 상승
- 사용자 슬라이더/UI 추가 **없음** → qr_scan_screen.dart 레이아웃 무변
- 미지원 기기는 조용히 넘어감

### 제외 (프레임 영향으로 보류)

- ~~qrbox 동적 계산~~ — 뷰파인더 크기 변경. **제외**.
- ~~줌 슬라이더 UI 추가~~ — 레이아웃 변경. **제외**.
- ~~Torch 버튼 UI 추가~~ — 레이아웃 변경. **제외**.
- ~~html5-qrcode 라이브러리 업그레이드~~ — 2.3.8 → 2.3.10 미세 차이 있을 수 있음, 우선순위 낮음. Task 1+2+3 효과 부족 시에만 검토.

### 규모 추정
- Task 1: **1줄 추가**
- Task 2: 3곳 × 약 5줄 = 15줄
- Task 3: 신규 헬퍼 ~15줄 + 호출 3곳
- **전체: 약 35줄 수정**, UI/CSS/컨테이너/qrbox 전부 불변
- 작업 시간: 반나절 + 실물 명판 테스트

### 점진적 적용 권장
1. **Task 1만** 먼저 핫픽스 → 실물 명판 샘플 테스트
2. 여전히 부족하면 Task 2 추가
3. 그래도 부족하면 Task 3 추가
4. 각 단계마다 프레임/뷰파인더 시각적 regression 없는지 확인

### 검증 체크리스트
- [ ] 스캐너 뷰파인더 정사각형·크기·위치가 수정 전과 픽셀 단위로 동일
- [ ] 기존 스티커 QR 인식 속도 동등 이상
- [ ] 명판 소형 QR 인식 성공
- [ ] Chrome Desktop / Chrome Android 두 환경 확인
- [ ] `[QrScannerWeb] ★ forceSquare applied` 로그 정상 출력 (프레임 유지 확인)

### 검증
- 명판 실물 샘플 + 스티커 샘플 모두 인식 성공
- Chrome Desktop(웹캠), Chrome Android, Chrome iOS(가능 시) 세 환경에서 확인
- Regression: 기존 스티커 QR / 작업 태그 QR 인식률 동등 이상 유지

### 임시 우회책 (사용자 전달 가능)
- 명판 QR에 초점이 잡힐 때까지 카메라를 앞뒤로 움직여 포커스 유도
- 조명 밝은 곳에서 스캔
- 가능하면 명판 QR을 스티커 복사본으로도 병행 부착 (근본 대책 아님)

### 관련
- BUG-41 동일하게 PWA 카메라 스택 의존. 해결 우선순위는 **BUG-42 > BUG-41** (작업 차단 영향이 큼).

---

## 🟢 아이디어 / 메모

- **AXIS-VIEW**: React 기반 관리자 대시보드 (출퇴근, 생산 현황, KPI 등). App과 분리.
- **PWA → Native 전환**: 현재 Flutter Web(PWA) 코드는 Native 전환 시 비즈니스 로직 그대로 재사용 가능. 플랫폼 의존 코드(html5-qrcode → mobile_scanner, secure storage 등)만 조건부 import 처리.
- **공용 태블릿 시나리오**: 공장 현장 공용 기기 사용 시 로그아웃 시 localStorage 클리어 로직 필요 (현재는 미구현, 필요 시 추가)
- **model_config 조회/수정**: CLAUDE.md에 "추후"로 기록됨. Admin이 모델별 설정(has_docking, is_tms 등) 수정 가능한 UI.
- **Sprint 완료 시 공지사항 등록**: 현재 수동 (Admin 화면에서 version 필드 입력). 업데이트 팝업은 notices 테이블에 해당 버전 공지가 있을 때만 표시됨. 공지 없으면 팝업 안 뜸. 자동화 옵션: A) CLAUDE.md 버전 업데이트 절차에 공지 생성 단계 추가 / B) 배포 스크립트에 API 호출 / C) CI/CD hook (추후)
- **QR 목록 contract_type / sales_note 필드 추가 검토**:
  - `contract_type`: Excel N열 "신규여부" (양산/신규/계약변경). step1_extract.py에서 추출은 됨, DB 컬럼 미추가 + step2 UPSERT 미포함
  - `sales_note`: Excel CJ열 "특이사항(영업)". 마찬가지로 추출만, DB 미적재
  - 작업 필요: ① plan.product_info ALTER TABLE ② step2_load.py UPSERT 추가 ③ qr.py SELECT 추가
  - 활용성 검토 필요: VIEW QR관리 페이지에서 이 정보를 어떻게 활용할지 (필터? 표시만?) 확인 후 진행
  - OPS_API_REQUESTS.md #6에 등록됨
- ~~**PWA 버전 업데이트 알림 토스트**~~ → ✅ Sprint 26 전체 완료 (Task 1: SW 업데이트 토스트, Task 2~5: UpdateService + UpdateDialog + HomeScreen 연동 — 버전별 공지 팝업 정상 동작 확인)
- ~~**QR 스캔 UX 개선 3건**~~ → ✅ Sprint 40-A 전체 완료 (2026-03-27)
  - ① QR 프레임 축소: qrbox 200→160, cameraSize 350→240 + BUG-29 수정
  - ② DOC_/LOC_ 자동접두어: prefixText + validator + submit 결합
  - ③ 오늘 태깅 드롭다운: BE today-tags API + FE _loadTodayTags() + BUG-25 수정 (ApiService.get() 반환 타입 불일치)
- ~~**테스트 DB 분리**~~ → ✅ Sprint 39 완료 (2026-03-26). `TEST_DATABASE_URL` 환경변수 분리, `.env.test` 자동 로딩, 운영 DB 하드코딩 제거, Sprint 39-fix regression 118→0 해결
- ~~**비활성 사용자 자동 삭제 + 협력사 유저 삭제 기능**~~ → ✅ Sprint 40-C 전체 완료 (2026-03-27)
  - ✅ Migration 040/041: workers에 is_active, deactivated_at, last_login_at + alert_type_enum
  - ✅ BE: worker.py 5함수 + auth login is_active 체크 + last_login_at 갱신
  - ✅ BE: admin API 3개 + manager request-deactivation API 1개
  - ✅ BE: 비활성화 요청 시 admin 앱 알림 + 이메일 알림 동시 발송
  - ✅ FE: Admin 옵션 — 비활성 사용자 관리 섹션 (30일 미로그인 + 비활성화/재활성화)
  - ✅ FE: Admin 옵션 레이아웃 8섹션 재배치
  - 🔲 FE: Manager 위임 화면 — 자사 유저 "비활성화 요청" 버튼 (미구현)
  - 테스트 9/9 passed

---

## 📋 Sprint 이력 요약

| Sprint | 주요 내용 | 테스트 |
|--------|----------|--------|
| 1 | 인증 + DB 기반 | 8 PASSED |
| 2 | Task 핵심 플로우 | 21 PASSED |
| 3 | 공정 검증 + 알림 | 21 PASSED |
| 4 | 관리자 + 퇴근시간 자동감지 | 31 PASSED |
| 5 | 보안 + PWA + 이메일 + 잔여 모델 | 59 PASSED |
| 6 | Task 재설계 + 네이밍 + Admin 옵션 | 157 PASSED, 20 SKIP |
| 7 | 실데이터 + 통합 테스트 | 356 PASSED, 19 SKIP |
| 8 | Admin API 보완 + UX + 비밀번호 찾기 | 271 PASSED, 19 SKIP |
| 9 | Pause/Resume + 근무시간 관리 | 318 PASSED, 19 SKIP |
| 10 | 수동 검증 + 버그 수정 | 456+ PASSED, 19 SKIP |
| 11 | GST Task + 대시보드 + Checklist | 44 PASSED, 1 SKIP |
| 11 핫픽스 | 타입 불일치, 필터링, 협력사 정보, UTC→KST | 수동 수정 4건 |
| 12 | PIN + 출퇴근 + QR 카메라 | 22 PASSED |
| 12 핫픽스 | PIN 자동로그인 분기 로직 | 수동 수정 4건 |
| 12 배포 | Netlify PWA + Railway API 배포 | 전체 API 동작 확인 |
| 13 | WebSocket flask-sock 마이그레이션 + BUG-2/4 수정 | 18 PASSED, 배포 완료 |
| BUG-5 핫픽스 | QR 카메라 위치(left+width) + 스캔 영역(순수 JS config) + 스플래시 스크린 | 19 PASSED, 웹 검증 완료 |
| 14 | 작업자명 표시(Task Detail + GST 대시보드) + QR 스캔 영역 정사각형 | 28 PASSED, 배포 완료 |
| 14 핫픽스 | BUG-7/8/9/10/11: 휴게시간 자동재개 + 작업시간 계산 + force-close + QR 스크롤 + Location QR | 76 PASSED, 1 SKIP, 배포 완료 |
| 15 | BUG-12 다중작업자 Join + BUG-11 재수정 + MH/WH 로깅 | 28 PASSED, 배포 완료 |
| 16 | Admin prefix 로그인 + BUG-13/14/15 + QR 카메라 정사각형 | 9 PASSED, 배포 완료 |
| 16.1 | v1.1.0 버전 관리 + System Online 실연동 + BUG-16/17 수정 | 빌드 에러 0건, 배포 완료 |
| 16.2 | 담당공정 설정 이동 (홈→개인설정) + BUG-16/17 배포 | 빌드 에러 0건, 배포 완료 |
| 17 | 출퇴근 분류 체계 (work_site + product_line) v1.2.0 | 13 PASSED, 배포 완료 |
| 18 | 협력사별 S/N 진행률 뷰 v1.3.0 | 10 PASSED, 배포 완료 |
| 19-A | 보안: Refresh Token Rotation + Device ID | 6 PASSED + 28 회귀, 배포 완료 |
| 19-B | 보안: DB 기반 Refresh Token 관리 + 탈취 감지 | 10 PASSED, 배포 완료 |
| 19-D | 보안: Geolocation GPS 위치 검증 (출퇴근) | 11 PASSED, 배포 완료 |
| 19-E | VIEW용 Admin 출퇴근 API 3개 (BE) | 8 PASSED |
| 20-A | 신규 가입 시 Admin 이메일 알림 | 5 PASSED |
| 20-B | 공지사항 탭 (BE+FE) | 6 PASSED |
| 21 | QR Registry 목록 API (BE) + 날짜 필터 | ✅ |
| 21-ETL | ETL → axis-core-etl repo 분리 | ✅ 분리 완료 |
| 22-A | Email Verification 개선 (Admin 알림 시점 + 재전송 API) | ✅ |
| 22-A보완 | 인증 3분 만료, FE 연동, 승인필터, PM role | ✅ v1.6.1 |
| 22-B | GPS enableHighAccuracy + DMS 변환 헬퍼 | ✅ |
| 22-C | Manager 권한 위임 (같은 회사 is_manager 부여) | ✅ v1.6.2 |
| 22-D | 공지수정 UI + Admin 간편로그인 + ETL 변경이력 API | ✅ v1.6.3 |
| 23 | Manager 권한 위임 화면 + 홈 메뉴 재구성 | ✅ v1.7.0 |
| 24 | QR actual_ship_date + Manager 자사 필터 + workers 권한 완화 | ✅ v1.7.1 |
| 24 핫픽스 | BUG-18/19/20/21: GST 출퇴근 + 비밀번호 찾기 + 로그인 에러 분리 + 404 메시지 | ✅ |
| 22-E | conftest.py 운영 데이터 5테이블 백업/복원 완성 (product_info + qr_registry) | ✅ |
| 25 | BUG-22 Logout Storm 수정 (FE 3중 방어 + BE jwt_optional) | ✅ v1.7.2 |
| 26 | PWA 업데이트 알림 토스트 + 업데이트 팝업 + conftest 보호 강화 | ✅ v1.7.3 |
| 27 | 단일 액션 Task (task_type 컬럼 + Docking/출하완료) | ✅ v1.7.4 (migration 022 적용) |
| 28 | AXIS-VIEW 권한 데코레이터 재정비 (gst_or_admin + view_access) | ✅ v1.7.4~v1.7.5 |
| 27-fix | Task Seed Silent Fail 디버깅 — 로깅 강화 + SINGLE_ACTION UI | ✅ v1.7.5 |
| 29 | 공장 API — 생산일정 #10 + 주간 KPI #9 (BE only) | ✅ v1.7.6 |
| 29 보완 | PM role + 이름 로그인 + ship_plan_date + per_page 500 | ✅ v1.7.7 |
| 29-fix | BUG-24 재발 방지 — ensure_schema 자동 검증 + migration 023 | ✅ v1.7.8 |
| 30 | DB Connection Pool 도입 — 동시 접속 안정화 (33파일 175건 변환) | ✅ v1.8.0 |
| 30-B | DB Pool TCP keepalive + health check + Procfile 튜닝 | ✅ v1.8.0 |
| 31A | 다모델 지원 — DUAL L/R, DRAGON MECH, PI 분기, workers RESTRICT | ✅ v1.9.0 |
| 31B | QR 기반 태스크 필터링 — DUAL L/R 분리 표시 (BE+FE) | ✅ v1.9.0 |
| 32 | 사용자 행위 트래킹 — app_access_log + analytics API 4개 + 30일 정리 | ✅ v1.9.0 |
| 31C | PI 검사 협력사 위임 — 가시성 분기 + DRAGON PI 활성화 | ✅ v2.0.0 |
| 33 | 생산실적 API — O/N 단위 실적확인 + 월마감 (production.py 4개) | ✅ v2.0.0 |
| 34 | admin_settings 레지스트리 리팩터링 + workers 필터 + PI 설정 API | ✅ v2.0.0 |
| 34-A | Admin 옵션 PI 위임 설정 UI — Chip 추가/삭제 (FE) | ✅ v2.0.0 |
| 35 | 근태 기간별 출입 추이 API — 단일 SQL 집계 + trend 엔드포인트 | ✅ v2.0.0 |
| 36 | TM 실적확인 TANK_MODULE only + 공정 종료일 기준 + module_end ETL | ✅ v2.0.0 |
| 37 | 혼재 O/N 실적확인 partner별 분리 — mixed + partner_confirms | ✅ v2.1.0 |
| 37-A | TM 가압검사 옵션 — tm_pressure_test_required settings 기반 progress/알람 | ✅ v2.1.0 |
| 37-B | S/N별 실적확인 + TM 혼재 제거 + 탭별 End 필터 (#38) | ✅ v2.1.0 |
| BUG-27 | monthly-summary 500 에러 — SUM(sn_count) 참조 (DROP된 컬럼) | ✅ 수정 완료 (2026-03-24) |
| BUG-28 | tm_pressure_test_required PUT 400 — SETTING_KEYS 등록 누락 | ✅ 수정 완료 (2026-03-24) | `admin.py` SETTING_KEYS에 `tm_pressure_test_required` bool 추가. DB에는 존재했으나 레지스트리 미등록 |
| 38 | product/progress API last_worker + last_activity_at 필드 추가 | ✅ 완료 (2026-03-27) | progress_service.py 서브쿼리 추가 + 테스트 16/16 passed. VIEW Sprint 18 연동 |
| 38-B | product/progress API last_task_name + last_task_category 추가 | ✅ 완료 (2026-03-27) | progress_service.py 서브쿼리 확장 + 테스트 4/4 passed (기존 8건 regression 0) |
| 40-A | QR 스캔 UX 개선 — 프레임 축소 + DOC_ 자동접두어 + 오늘 태깅 드롭다운 | ✅ 완료 (2026-03-27) | BE: today-tags API 5/5 passed. FE: qrbox 160, prefixText, 드롭다운 UI |
| #46 | 상세뷰 workers 매핑 — task_id fallback + serial_number 기준 조회 | ✅ 완료 (2026-03-27) | work.py 2단계 매핑 (task_id 1차 + category+ref fallback). 테스트 5/5 passed |
| 40-C | 비활성 사용자 관리 — soft delete + admin 승인 + manager 요청 | ✅ 완료 (2026-03-27) | migration 040/041 + worker.py 5함수 + auth login is_active 체크 + API 4개 + 앱/이메일 알림. 테스트 9/9 passed |
| 40-C FE | Admin 옵션 레이아웃 재배치 + 비활성 사용자 관리 UI | ✅ 완료 (2026-03-27) | 8섹션 순서 변경 + 30일 미로그인 목록 + 비활성화/재활성화 버튼 + 빌드 성공 |
| 41 | 작업 릴레이 + Manager 재활성화 | ✅ 완료 (2026-03-30) | finalize 파라미터 + 릴레이 재시작 + reactivate-task API + FE 종료 팝업. 테스트 18/19 passed (1 xfail) + regression 71 passed |
| 41-A | 작업 완료 토스트 + 릴레이 다이얼로그 + 재시작 UI + 재완료 허용 | ✅ 완료 (2026-03-30) | Task 0~4: pop(result) + 릴레이 다이얼로그 + 재시작 UI + _worker_restarted_after_completion(). TC-41A-01~21 |
| 41-B | 릴레이 미완료 task 자동 마감 + Manager 알림 | ✅ 완료 (2026-03-30) | FINAL task 트리거 + orphan 4시간 스케줄러 + RELAY_ORPHAN alert. 테스트 14/14 passed |
| 39 | 테스트 DB 분리 — conftest.py 리팩토링 | ✅ 완료 (2026-03-26) | TEST_DATABASE_URL 환경변수 분리, .env.test 자동 로딩, 운영 DB 하드코딩 제거, seed_test_data fixture, test_sprint39_db_isolation.py 10/10 통과 |
| 39-fix | Regression 수정 — 118 failed → 0 failed | ✅ 완료 (2026-03-27) | BE: factory.py finishing_plan_end→ship_plan_date, production.py module_end→module_start. TEST: 18개 파일 수정 (MM→MECH, worker_id 819→seed admin, task seed 기대값, GAIA-I DUAL→SINGLE, confirmable→all_confirmable 등). 최종 714 passed / 14 skipped |

---

## 🔷 Sprint 40 계획 (병렬 3트랙)

> 등록일: 2026-03-26
> 상태: Track A/B/C 전체 완료 (2026-03-27)
> 선행: Sprint 38 ✅ 완료

### Track A: QR 스캔 UX 개선 3건 (APP FE + BE 1개)

| # | 개선 | 변경 범위 | 난이도 |
|---|------|----------|--------|
| A-1 | QR 프레임 크기 축소 | `qr_scanner_web.dart` qrbox값 1줄 + `qr_scan_screen.dart` cameraSize 1줄 | 매우 낮음 |
| A-2 | DOC_ 자동 접두어 | `qr_scan_screen.dart` — prefixText + validator/submit 로직 수정 | 낮음 |
| A-3 | 오늘 태깅 QR 드롭다운 | BE: `work.py` API 1개 + `work_start_log.py` 쿼리 1개 / FE: 드롭다운 UI | 중 |

⚠️ **카메라 관련 주의**: BUG-5~BUG-23까지 20회 이상 카메라 수정 이력 있음. 정사각형 강제 로직(MutationObserver, _forceSquareAfterCameraStart, CSS aspect-ratio 등) 절대 수정 금지. qrbox 정수값과 cameraSize clamp 범위만 변경.

### Track B: VIEW Sprint 18 — S/N 카드뷰

- Sprint 38의 last_worker/last_activity_at 필드를 FE에서 카드뷰에 연결
- VIEW FE만 변경 (BE 변경 0건)

### Track C: 비활성 사용자 관리 — 프롬프트 작성 완료 ✅

- BE: `workers.last_login_at` 기반 30일 미로그인 감지 API + 삭제 대기 목록 + admin 승인 API
- BE: 협력사 manager 자사 유저 삭제 요청 API
- VIEW: 권한관리 페이지에 삭제 대기 목록 + 승인/반려 UI (별도 Sprint)
- soft delete (is_active=FALSE)
- **최종 admin 승인 후 삭제** (즉시 삭제 아님)
- Migration 040: workers에 `is_active`, `deactivated_at`, `last_login_at` 컬럼 추가
- ⚠️ `app_access_log`는 30일 보관 한계 → `workers.last_login_at`으로 판단
- 📋 프롬프트: `AGENT_TEAM_LAUNCH.md` Sprint 40-C 섹션 참조

### Sprint 41: 작업 릴레이 + Manager 재활성화 — 프롬프트 작성 완료 (2026-03-30)

- **문제**: 판넬 작업 등 1개 task를 여러 작업자가 순차 교대 시, 유저1 종료 → task 닫힘 → 유저2 시작 불가
- **해결**: "내 작업 종료" (finalize=false, task 열린 상태) vs "task 완료" (finalize=true, task 닫힘) 분리
- FE: 종료 버튼 → "다음 작업자가 이어서 작업하나요?" 팝업 (예/아니오)
- BE: complete_work() finalize 파라미터 + start_work() 릴레이 재시작 허용
- Manager/Admin: reactivate-task API (실수 완료 복구)
- 하위 호환: finalize 기본값 true → 기존 FE 미업데이트 시에도 정상 동작
- 📋 프롬프트: `AGENT_TEAM_LAUNCH.md` Sprint 41 섹션 참조

### Sprint 40 이후 대기

| 작업 | 선행 조건 |
|------|----------|
| Sprint 41 (작업 릴레이 + 재활성화) | 프롬프트 작성 완료 ✅ |
| 체크리스트 BE (스키마 + CRUD) | ELEC 양식 수집 완료 |
| VIEW Sprint 20 (체크리스트 관리 UI) | 체크리스트 BE 완료 ✅ |
| QR contract_type / sales_note | 활용성 검토 확정 |

---

## 운영 / 릴리스 루틴

### RULE-01 — Sprint 완료 시 FE 재빌드·재배포 의무화

**배경**
- 2026-04-15: 사용자 화면에 `v2.8.1` 표시, 코드상 git 버전은 `v2.9.2` (Sprint 59-BE까지 반영됨).
- 원인: Sprint 58-BE / 59-BE가 **백엔드 전용** 변경이라 판단해 `flutter build web`을 돌리지 않음.
- 하지만 `frontend/lib/utils/app_version.dart`의 `AppVersion.version` 문자열은 **매 sprint에서 FE 파일로 수정**되므로, FE 재빌드 없이 배포하면 버전 문구가 화면에 반영되지 않음.
- PWA 특성상 서비스워커는 새 빌드 해시가 감지되어야 `controllerchange` → 업데이트 토스트 → `window.location.reload()` 흐름이 동작 → **빌드·배포 공백 = 업데이트 토스트 미발생**.

**규칙**
모든 sprint (BE / FE / VIEW 종류 불문) 머지/완료 시 다음 순서 강제:

1. `frontend/lib/utils/app_version.dart`의 `version` / `buildDate` 업데이트 (sprint 담당자 책임)
2. `cd frontend && flutter build web --release`
3. Netlify 배포 트리거 (CI auto 또는 수동 업로드)
4. 배포 후 Chrome PWA에서 업데이트 토스트 수신 → 새로고침 → 버전 문구 확인
5. 서비스워커 캐시 문제 의심 시: DevTools → Application → Storage → Clear site data

**체크포인트**
- Sprint 완료 PR 머지 전에 `app_version.dart` diff 반드시 포함
- CI에 `flutter build web --release` 에러 0건 게이트 유지
- BE-only sprint라도 위 루틴은 동일하게 적용 — **버전 문구 싱크가 우선**

**현재 필요 조치 (v2.9.2 기준)**
- [x] `flutter build web --release` 실행 (v2.9.3, 2026-04-16)
- [x] Netlify 재배포 (v2.9.3)
- [ ] 사용자 Chrome PWA에서 하드 리프레시 (Cmd/Ctrl + Shift + R) 또는 site data clear
- [ ] 화면 하단 버전 문구가 `G-AXIS OPS v2.9.3`으로 뜨는지 확인

**관련**
- BUG-41 (PWA PIN 로그인 유실) — 동일 PWA 업데이트 플로우 의존. 빌드·배포 루틴 정착이 재현 디버깅의 선행 조건.
- `frontend/web/index.html` L180-232 — `controllerchange` → `showUpdateToast()` → `window.location.reload()` 구현 (이미 존재, 새 빌드 해시 트리거가 없으면 무용지물).

---

## ✅ BUG-44 상세: OPS 미종료 작업 목록 0건 반환 (수정 완료 2026-04-17)

**현상**
- OPS Admin 계정: `/admin/tasks/pending` → `{"tasks":[], "total":0}`
- OPS Manager(C&A): `/admin/tasks/pending?company=C%26A` → 동일 0건
- VIEW(React)에서는 동일 S/N의 진행 중 작업 정상 표시

**원인 규명 (2026-04-17)**

`get_pending_tasks()` (admin.py L1721)의 INNER JOIN이 근본 원인:

```sql
FROM app_task_details t
JOIN workers w ON t.worker_id = w.id   -- ← worker_id가 전부 NULL → 0건
```

진단 과정:
1. ✅ DB 정상 — is_admin/is_manager 값 확인됨
2. ✅ v2.9.4 배포 확인
3. ✅ API 호출 정상 — DevTools에서 pending 엔드포인트 응답 확인 (빈 배열)
4. 🔑 `SELECT ... FROM app_task_details WHERE started_at IS NOT NULL AND completed_at IS NULL` → 20건+ 존재 (worker_id **전부 NULL**)
5. 🔑 `SELECT ... FROM app_task_details t JOIN workers w ON t.worker_id = w.id WHERE started_at IS NOT NULL AND completed_at IS NULL` → **0건**

**근본 원인**: `start_task()` (task_detail.py L384-419)는 `started_at`만 UPDATE하고 `worker_id`는 세팅하지 않음. 작업자 추적은 `work_start_log` 테이블에서 별도 관리. VIEW는 `work_start_log`에서 JOIN하므로 정상 작동.

**수정** (Claude × Codex 교차 검증 합의, 2026-04-17):
- FK 매칭 LATERAL JOIN — `wsl2.task_id = t.id` (DDL: `REFERENCES app_task_details(id)`)
- `task_id_ref` 단독 매칭 금지 — VARCHAR라 S/N 간 중복 가능 (unsafe)
- `AND (w.company = %s OR %s IS NULL)` **유지** — 제거 시 FNI/BAT MECH 권한 분리 깨짐
- 파라미터 바인딩 `(company, company)` 유지, API 응답 형식 무변경
- 상세 설계는 `AGENT_TEAM_LAUNCH.md` BUG-44 섹션 + `HANDOVER_BUG44.md` 참조
