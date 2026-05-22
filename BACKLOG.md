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
| BUG-42 | 명판 소형 QR 접사 인식 실패 | ✅ 1차 검증 GREEN (2026-05-21, v2.18.16) — 명판 실측 대기 | 누적 trail (13번 시도): v2.18.5~v2.18.11 (11번 hotfix → 셀카 catch) → v2.18.12 (1차 ROLLBACK) → qr-test.html + Codex 라운드 1+2 (root cause 확정: html5-qrcode `videoConstraints` 키 자체가 `cameraIdOrConfig.facingMode` 무시) → v2.18.13/14 (4-tier/3-tier fallback chain → 인식 NG) → v2.18.15 (2차 ROLLBACK + qr-test.html Phase 1+2 옵션) → 사용자 검증 (videoConstraints 사용 = 디코더 방해 / applyConstraints zoom 만 사용 = OK) → **v2.18.16 최종 fix** (`_applyZoomIfSupported` 2.0x 자동 적용, videoConstraints 우회). 1차 검증 GREEN (웹 QR 인식 개선 확인). 실기기 명판 실측 (2026-05-22 사용자 회사 현장) 대기 후 close 결정 |
| BUG-42-TASK3-AUTO-ZOOM-DEFERRED | 명판 QR 자동 줌 (Task 2 부족 시 추가 검토) | ✅ v2.18.16 적용 완료 (zoom 2.0x 자동) | BUG-42 Codex 라운드 1 Q4 A — 자동 30% 줌 BACKLOG 이관. **v2.18.16 영역 zoom 2.0x 자동 적용 완료** (`_applyZoomIfSupported` helper, getCapabilities().zoom 확인 후 min/max clamp + silent skip 미지원). 본 sprint 영역 closed |
| BUG-42-CAMERA-SWITCH-BUTTON-DEFERRED | 카메라 전환 버튼 UI (전면 ↔ 후면) | 🟡 BACKLOG (LOW, qr_scan_screen.dart 절대 불변 영역 해소 필요) | v2.18.7 catch 후속 — 사용자 catch "카메라 방향이 셀카인데 전환 버튼 돌려달라". v2.18.7 에서 후면 강제(facingMode exact + label 매칭) 로 모바일 catch 해결. 단 명시적 전환 UI 는 별 sprint — `qr_scan_screen.dart` 레이아웃/UI 위젯 배치는 CLAUDE.md L1134-1142 절대 불변 영역(과거 20회+ 수정) 침범 위험. 설계 시 검토: ① 뷰파인더 외부 영역(상단 또는 하단)에 토글 버튼 ② 버튼 클릭 → 카메라 재시작 + facingMode 토글 ③ 토글 상태 shared_preferences 저장 ④ 프레임 / 뷰파인더 / forceSquare regression 검증. 추정 ~30 LOC + 실기기 QA 의무 |
| REFACTOR-QR-SCANNER-WEB-FUNCTION-SPLIT | qr_scanner_web.dart 함수 분할 (`startQrScanner` 175줄 → 60줄 이하) | 🟠 BACKLOG (MEDIUM, Codex 라운드 2 A-Q7 격상) | v2.18.13 적용 후 파일 LOC 569줄 (🟡 경고 영역) + `startQrScanner()` 175줄 (🔴 절대 한도 100줄 초과). v2.18.13 영역 4-tier 시도 영역 추가되어 함수 더 길어짐. Codex 라운드 2 권고: `_tryStartWithTier()` + `_tryUserCameraFallback()` + `_tryFirstCameraIdFallback()` 분리. 리팩토링 안전 7원칙(CLAUDE.md L575) 준수. **우선순위 LOW → MEDIUM 격상 (Codex A-Q7, 2026-05-21)** |
| QR-SCANNER-RETRY-CLEANUP | tier 실패 시 DOM/stream 잔여물 정리 | 🟡 BACKLOG (LOW, Codex A-Q2/Q3) | 등록 trail: Codex 라운드 2 A-Q2/Q3 권고 (2026-05-21). 4-tier chain 영역 tier 실패 시 html5-qrcode 가 video element / stream 영역 dispose 안 하는 경우 가능. 다음 tier 시도 시 영역 잔여물 충돌 가능성. 조치: ① 각 tier 실패 catch block 영역 best-effort `scanner.clear()` 호출 ② #qr-scanner-dom-div 내부 video element 잔존 확인 + 제거 ③ 운영 로그 영역 잔여물 발견 시 fix 진행. v2.18.13 영역 즉시 영영 영역 영영 — 운영 catch 후 진행 |
| QR-SCANNER-ERROR-CLASSIFICATION | 마지막 시도 실패 시 사용자 메시지 분류 | 🟡 BACKLOG (LOW, Codex A-Q8) | 등록 trail: Codex 라운드 2 A-Q8 권고 (2026-05-21). 현재: 4-tier + user + cameraId 모두 실패 → "사용 가능한 카메라를 찾을 수 없습니다" 단일 메시지. 권한 거부 (NotAllowedError) / 카메라 점유 (NotReadableError) / 카메라 없음 영역 영역 미구분. 조치: ① 마지막 catch 영역 error.name / error.message 보존 ② 분류: NotAllowedError → "카메라 권한 거부, 브라우저 설정에서 허용" / NotReadableError → "다른 앱이 카메라 사용 중" / OverconstrainedError → "지원되지 않는 카메라 설정" / 기타 → 현재 메시지. v2.18.13 영역 즉시 영영 영역 영영 — 운영 catch 후 진행 |
| TEST-QR-LIB-CONSTRAINT-PREFLIGHT | 외부 카메라/QR 라이브러리 사용 사전 검증 체크리스트 | 🟡 BACKLOG (LOW, 재발 방지) | 등록 trail: BUG-42 v2.18.5~v2.18.11 (11번 hotfix) 실패 시리즈 + Codex 라운드 1 A-Q5 + 라운드 2 A-Q6 권고 (2026-05-21). 원인: html5-qrcode `config.videoConstraints` 키 자체가 `cameraIdOrConfig.facingMode` hint 를 무시한다는 라이브러리 내부 동작 미확인. **체크리스트 도입**: ① 라이브러리 source 코드 영역 input parameter 우선순위 확인 의무 (특히 conflicting constraints) ② 최소 재현 HTML (qr-test.html 패턴) 영역 iOS/Android 실기기 사전 테스트 ③ Codex 라운드 1 위임 시 "라이브러리 source 확인" 항목 명시 ④ 단일 minimal change 마다 실기기 검증. **실기기 QA 8항목 (deploy 전 강제 evidence, Codex 라운드 2 A-Q6 추가)**: (1) iPhone Safari 후면 화면 육안 확인 (2) `getRunningTrackSettings()` 영역 facingMode/width/height/deviceId 로그 (3) 명판 QR 3거리 (10/15/20cm) 인식 테스트 (4) 스티커 QR 정상 인식 regression (5) Stop → 재Start 시 카메라 방향 유지 (6) 권한 최초 허용 / 이미 허용 / 거부 후 복구 (7) Android Chrome 후면 + 인식률 (8) Desktop Chrome OverconstrainedError 없이 fallback. CLAUDE.md L98-103 (침묵 승인 거부) + L149 (Codex 독립) 영역 보완 |
| FEAT-SHIPMENT-STATUS-PAGE | 출고 현황 페이지 | 🔴 HIGH (사용자 우선순위 1, 2026-05-22) | 등록 trail: 사용자 catch (2026-05-22). 목업 페이지 사용자 측 영역 작성 완료 — 상세 catch 추가 후 본문 보강 예정. 추정 영역: 출고 진행 상황 / 출하 완료 / 출하 대기 등 실시간 dashboard. 선행: AXIS-VIEW Sprint 47 (`FEAT-SHIPMENT-HISTORY-PAGE` 6월 초 예정) 와 관계 catch 필요 — 신규 추가 vs 기존 통합. 추정 시간 미정 (상세 catch 후) |
| FEAT-PENDING-TASK-MANAGEMENT-PAGE | 종료 누락 관리 페이지 | 🔴 HIGH (사용자 우선순위 2, 2026-05-22) | 등록 trail: 사용자 catch (2026-05-22). 목업 페이지 사용자 측 영역 작성 완료 — 상세 catch 추가 후 본문 보강 예정. 추정 영역: 미종료 작업 (started_at NOT NULL + completed_at IS NULL) 통합 관리 / 강제 종료 / Manager 알림 등. 현재 OPS admin_options_screen + manager_pending_tasks_screen 영역 일부 기능 존재 — 신규 페이지 vs 기존 통합/개선 catch 필요. 추정 시간 미정 (상세 catch 후) |
| FEAT-QR-SCANNER-ADMIN-SETTINGS | QR 스캐너 설정값 (zoom / qrbox / fps) admin 옵션 화면 노출 | 🟡 BACKLOG (LOW, 운영 안정화 후) | 등록 trail: v2.18.16 BUG-42 fix 후 사용자 제안 (2026-05-21). 운영 환경 변화 (다른 명판 인쇄 / iPhone 모델 / 작업장 조명) 시 코드 수정 없이 운영팀 직접 조정. 설계: ① admin_settings SETTING_KEYS 3개 등록 — `qr_scanner_zoom` (default 2.0, range 1.0~3.0) / `qr_scanner_qrbox` (default 200, range 100~300) / `qr_scanner_fps` (default 10, range 5~30). 추가 가능 `qr_scanner_facing_mode` (environment/user) / `qr_scanner_videoConstraints_enabled` (운영 catch 시 끄기). ② BE: 기존 `GET/PUT /api/admin/settings` 자동 활용 + 신규 `GET /api/app/qr-scanner-config` (jwt 만, admin 권한 미요구). ③ FE: QR 스캔 화면 진입 시 settings fetch → `_applyZoomIfSupported(config.zoom)` + `qrbox: config.qrbox` 동적 적용. ④ admin_options_screen 영역 Slider/TextField UI 추가. 추정 ~130 LOC + pytest. 선행: BUG-42 명판 실측 GREEN + 1주 운영 catch + zoom 2.0x 적정성 검증 |
| REFACTOR-ADMIN-SPLIT | admin.py God File 분할 (2,568 LOC ⛔) | 🔴 HIGH (CLAUDE.md L477 정책 위반, Codex M-Q4 권고 2026-05-22) | v2.18.20 시점 LOC 2,568 — ⛔ 1,200 임계 2배 초과 = "새 로직 추가 금지" 정책 영영 영영 영영 catch. v2.18.20 영역 +8 LOC 영역 일부 완화로 받아들였지만 향후 신규 admin endpoint 추가 시 사전 분할 필수. 분할 안: ① `routes/admin_workers.py` (worker 승인/거부/조회) ② `routes/admin_settings.py` (admin_settings CRUD) ③ `routes/admin_alerts.py` (알림 관리) ④ `routes/admin_tasks.py` (force-close 등). 리팩토링 안전 7원칙 (CLAUDE.md L575) 준수. 추정 4 Sprint 분할 (각 500 LOC 단위), git tag `pre-refactor-admin-split` |
| FEAT-LOGIN-AMBIGUOUS-PREFIX-NOTICE | prefix 모호 매칭 시 사용자 안내 메시지 | 🟡 BACKLOG (LOW, UX 개선) | 등록 trail: Codex 라운드 1 A-Q3 권고 (v2.18.20). 동일 prefix 2명+ 가입 시 (예: `kdkyu` → `kdkyu@gst-in.com` + `kdkyu@naver.com`) 현재 응답 `ACCOUNT_NOT_FOUND` — 실제로 계정 영영 영영 catch. 분기: prefix 모호 시 별도 에러 코드 `EMAIL_PREFIX_AMBIGUOUS` 신규 + FE 안내 "동일 prefix 다중 매칭, 전체 이메일 주소 입력 부탁". worker.py 이미 debug log 출력 (v2.18.20). auth_service.login 영역 모호 catch 분기 추가 ~10 LOC |
| REFACTOR-EMAIL-DOMAIN-CONSTANT | ALLOWED_EMAIL_DOMAINS 4중 중복 통합 | 🟡 BACKLOG (LOW, DRY 정합) | 등록 trail: Codex 라운드 1 A-Q2 권고 (v2.18.20). 동일 도메인 list 4곳 중복 — `worker.py` (get_worker_by_email_prefix) / `auth_service.py` (ALLOWED_EMAIL_DOMAINS) / `frontend/lib/utils/validators.dart` (allowedEmailDomains) / `CLAUDE.md L626` (문서). 향후 도메인 추가 시 누락 위험. 안: `backend/app/config.py` 영역 단일 상수 + FE 영역 `/api/app/allowed-email-domains` endpoint (또는 config 영역 보내기). 추정 ~20 LOC |
| FEAT-APPROVAL-EMAIL-OUTBOX | 승인 메일 outbox 패턴 (daemon thread 유실 catch) | 🟡 BACKLOG (LOW, 신뢰성) | 등록 trail: Codex 라운드 1 A-Q5 권고 (v2.18.20). 현재 `send_approval_notification_async` 영역 daemon=True 스레드 — gunicorn worker 종료/배포 시 강제 종료 → 메일 발송 누락 가능. 운영 best-effort 수용 중 (현재 gthread 영영 영영, eventlet 충돌 catch 없음). 신뢰성 강화 시: ① outbox 테이블 신규 (pending/sent/failed) ② scheduler 영역 5분 단위 pending → 발송 ③ 발송 실패 시 재시도 3회. 추정 ~80 LOC + migration |
| TOOL-ERUDA-DEV-CONSOLE | Eruda in-app 콘솔 도입 (모바일 실기기 catch) | 🟡 BACKLOG (LOW, 도구 영역) | 등록 trail: BUG-42 시리즈 + Codex 라운드 1 A-Q6 권고 (2026-05-21). 원인: 모바일 실기기 콘솔 catch 어려움 → 11번 hotfix 시리즈 발생. 도입 안: ① `web/index.html` 영역 `<script src="https://cdn.jsdelivr.net/npm/eruda"></script>` 조건부 로드 ② 활성화: `?debug=eruda` 쿼리 파라미터 또는 dev build flag (production 기본 OFF) ③ `track.getSettings()` + `getCapabilities()` + selected constraints 로그 자동 포함 옵션 ④ Mac 원격 디버깅 (Safari Web Inspector) 가능 시 1순위, Eruda 는 현장 단독 진단 2순위. 운영 영향 0 (조건부 로드, 기본 OFF). ~10 LOC + 검증 |
| BUG-43 | 분석 대시보드 기능별 사용량 한글 라벨 누락 (24건) | ✅ 수정 완료 (2026-04-17) | Sprint 52+ 체크리스트/성적서/ELEC 엔드포인트 등 24개 `_ENDPOINT_LABELS` 미등록 → 전수 등록. 기존 111키 → 135키 (유니크 108 라우트 커버) |
| BUG-44 | OPS 미종료 작업 목록 0건 반환 (Admin/Manager 양쪽) | ✅ 수정 완료 (2026-04-17) | `get_pending_tasks()` INNER JOIN → LATERAL JOIN (work_start_log FK). Claude×Codex 교차 검증 합의. 29/29 passed |
| HOTFIX-01 | force_close/force_complete TypeError (naive vs aware datetime) | ✅ 수정 완료 (2026-04-17) | `completed_at` + `started_at` 양쪽 naive→KST aware 정규화. force_close + force_complete 2곳 적용. Claude×Codex 합의: completed_at이 진짜 원인. 29/29 passed |
| BUG-45 | VIEW 강제 종료 INVALID_REQUEST (close_reason 필드 미스매치) + 완료 시각 검증 부재 | ✅ 수정 완료 (2026-04-17, v2.9.6) | BE: `force_close_task()` 미래 시각(60s skew) + started_at 이전 가드 14줄 + docstring Returns 2건. FE-17: VIEW `useForceClose.ts` L24 `reason → close_reason`. pytest TC-FC-11~18 8/8 GREEN, 회귀 TC-FC-01~10 + admin 46건 모두 GREEN. force_complete는 Advisory(미호출 엔드포인트) |
| TEST-CONTRACT-01 | VIEW↔BE API 필드 계약 자동 검증 테스트 도입 | 🟡 BACKLOG (중간, 재발 방지 Advisory) | BUG-45 후속 — `close_reason`/`reason` 같은 필드명 미스매치를 CI 단계에서 자동 차단. 과거 유사 사례: `is_pinned`/`priority` (공지), `qr_doc_id`, `taskId` snake/camel. 본건은 Bug fix 아닌 **재발 방지 구조 개선** → 기존 BUG-45 배포에 영향 없음. 설계: `AGENT_TEAM_LAUNCH.md` TEST-CONTRACT-01 섹션 (pytest + JSON Schema 우선, OpenAPI/Pact는 후보안). 등록: 2026-04-17 |
| REACTIVATE-AUDIT-TRAIL-20260518 | 작업 재활성화 append-only audit 로그 부재 | 🟡 BACKLOG (Advisory) | FIX-FORCE-CLOSED-REACTIVATION (v2.15.20) Codex 라운드 1 A-Q4. `reactivate_task()` 는 `logger.info()` 로 처리자만 남기고 DB audit row 미생성. 재활성화는 강제종료 메타데이터(force_closed/closed_by/close_reason)를 지우는 방향 → row 만 보면 "누가 언제 왜 강제종료했고 누가 다시 열었는지" 장기 추적 불가. 별 sprint 로 append-only 로그(`FORCE_CLOSE`/`REACTIVATE` actor·reason·timestamp) 추가 권고. 등록: 2026-05-18 |
| REF-REACTIVATE-DECORATOR-20260518 | reactivate route 권한 데코레이터 일관성 | 🟡 BACKLOG (Advisory) | FIX-FORCE-CLOSED-REACTIVATION (v2.15.20) Codex 라운드 1 A-Q5. `/api/app/work/reactivate-task` route 는 `@jwt_required` 만 있고 함수 내부에서 `is_manager`/`is_admin` 체크 + 403 반환 (권한 보장은 정상). 일관성 차원에서 `@manager_or_admin_required` 데코레이터를 붙이고 세부 회사 검증만 내부 유지 권고. 기능 영향 0 (현 동작 정상). 등록: 2026-05-18 |
| HOTFIX-02 | 체크리스트 마스터 API `checker_role` 키 노출 누락 (Sprint 60-BE 후속) | ✅ 수정 완료 (2026-04-17) | `backend/app/routes/checklist.py` `list_checklist_master()` SELECT 절에 `cm.checker_role` + 응답 dict에 `'checker_role': row.get('checker_role') or 'WORKER'` 2줄 추가 + docstring Response 스펙 동기화. 증상: VIEW 체크리스트 관리 JIG 14 row 전체 WORKER 뱃지 (원래 7 WORKER + 7 QI 분리 필요). OPS #59-B DONE / VIEW FE-18 ✅. 상세: `AGENT_TEAM_LAUNCH.md` Sprint 60-BE 후속 핫픽스 섹션 |
| HOTFIX-03 | 비활성 task(is_applicable=FALSE) 조회 필터 누락 — 미시작 카운트 오염 | ✅ 수정 완료 (2026-04-17) | `backend/app/models/task_detail.py` `get_tasks_by_serial_number()` + `get_tasks_by_qr_doc_id()` 두 함수의 4개 SELECT 쿼리 모두 `AND is_applicable = TRUE` 추가. 방안 A 채택 (제품 결정: 비활성 task는 일반 조회 응답에서 완전 제외). 증상: Heating Jacket task 비활성 설정에도 VIEW S/N 상세뷰에서 "미시작 1건"으로 카운트. OPS #60 BUG DONE. VIEW FE 수정 불필요. 관리자 전체 조회가 필요해지면 추후 `?include_inactive=true` 파라미터(방안 C)로 확장 |
| HOTFIX-04 | 강제종료 표시 누락 종합 (Case 1: Orphan work_start_log "진행중" 오표시 + Case 2: 미시작 강제종료 시 worker 라인·시각·사유 소실) | ✅ BE 수정 완료 (2026-04-17, v2.9.8 — pytest 9 신규 + 24 회귀 = 33/33 GREEN) | **범위 확장 (Twin파파 2026-04-17)**: 기존 Case 1(Orphan wsl) + Case 2(미시작 강제종료 — 가압검사 등 모든 task 유형 적용) 통합 수정. **방안 B + 확장 A 통합 + M2 옵션 C' 재확정**: ① Case 1 — BE `work.py` `get_tasks_by_serial()` workers SQL에 `app_task_details` JOIN + `COALESCE(wcl.completed_at, td.completed_at)` + `CASE ... WHEN td.completed_at IS NOT NULL THEN 'completed'` + `is_orphan`/`task_closed_at` 메타필드. ② Case 2 — **옵션 C' (장기 시스템 원칙 반영)**: `TaskDetail` 모델에 `closed_by_name` 런타임 필드 1개 신규 + `from_db_row()` 1줄 + `get_tasks_by_serial_number()`·`get_tasks_by_qr_doc_id()` SELECT 5곳에 `LEFT JOIN workers` 추가 → `_task_to_dict()`에서 `close_reason`/`closed_by`/`closed_by_name` 3키 자동 노출. **M1 정정 반영**: `force_closed`/`closed_by`/`close_reason` 3필드는 이미 TaskDetail dataclass L67~L69 + from_db_row L104~L106에 존재 → 중복 추가 없음, `closed_by_name` 1개만 신규. **M2 정정 반영**: Codex 1차 권고 옵션 A(후처리 루프)는 단기 해법이라 반려 → 옵션 C'(모델 필드 + SELECT JOIN) 채택. 이유: 새 응답 경로 확장 시 모델 불변·쿼리만 추가하면 자동 일관, APS-Lite 타겟 원칙 부합. **A1 반영**: TC-FORCECLOSE-NS-03(혼재) / NS-04(legacy backward-compat) / NS-05(Case 1+2 경계 중첩) 추가. **A2 불필요**: 이름이 모델 단계 바인딩이라 worker_ids 세트 확장 불요. **M1 COALESCE 미반영(옵션 α)**: worker row `duration_minutes` NULL 유지 — Orphan worker 개별 작업시간 관측 불가, `td.duration_minutes` fallback 시 복수 worker에서 N배 부풀림 → garbage 방지. **회귀 안전**: `SELECT *` → `SELECT td.*, w.name AS closed_by_name` — `td.*`로 기존 컬럼 보존·LEFT JOIN이라 row 유지. 타 조회 경로(scheduler/admin 통계/checklist/production/gst/factory) 쿼리 미변경 → `closed_by_name=None` 자동. **VIEW FE 소폭 변경 포함**: `ProcessStepCard.tsx` 2곳 수정(taskStatus 분기 + workers=[] placeholder 렌더) + `types/snStatus.ts` 2필드 추가. placeholder 문구 "강제 종료 · 작업 이력 없음 · 처리: 김*규(마스킹) · KST 시각 · 사유: 원문" (FE-19). OPS FE 변경 없음. 배포 즉시 박*현/김*욱(Case 1) + TM 모듈 가압검사(Case 2) 등 기존 데이터 자동 복구, DB backfill 불필요. 설계 상세: `AGENT_TEAM_LAUNCH.md` HOTFIX-04 섹션 / FE 상세: `AXIS-VIEW/VIEW_FE_Request.md` FE-19. 등록: 2026-04-17 / 설계 확정: 2026-04-17 (범위 확장) / Codex 재검증 M1·M2·A1·A2 반영: 2026-04-17 |
| HOTFIX-05 | Admin 옵션 미종료 작업 카드 시간 UTC 오표시 (`.toLocal()` 누락) | ✅ 수정 완료 (2026-04-17, v2.9.7) | `frontend/lib/screens/admin/admin_options_screen.dart` L2474 `DateTime.tryParse(...)?.toLocal()` 1줄 추가. 증상: BE가 `+09:00` offset 포함 ISO 응답을 반환하나 Dart `DateTime.tryParse()`가 내부 UTC로 저장 → 게터가 UTC 값 반환 → "2026-04-01 06:41" 표시 (KST 15:41이 정답). `manager_pending_tasks_screen.dart` L353은 이미 `.toLocal()` 적용되어 있어 화면 간 불일치. FE only, BE/DB 영향 없음 |
| DOC-SYNC-01 | OPS_API_REQUESTS.md / VIEW_FE_Request.md 잔여 PENDING 15건 실구현 상태 교차 검증 | ✅ 검증 완료 (2026-04-17) | **Explore 에이전트 15건 일괄 검증 + Twin파파 확정 반영**: 13/15 ✅ DONE 확정(#40/#41/#46 상세뷰 workers/#48-A/#48-B/#51/#52/#54/#55/#56-A ELEC API/#56-B confirm_checklist_required 연동/#57 성적서 Phase+DUAL 분기/FE-08) → 헤더 업데이트 완료. 1/15 🟡 BACKLOG(장기)(#22 SI_SHIPMENT 로직 미구현 — Twin파파 2026-04-17 확정: 테스트 완료 설비 1건으로 운영 영향 미미, 실출하 데이터 누적 시점에 Sprint 배정. BE factory.py + VIEW FE `si` 필드 분리 동시 필요). 1/15 🟡 보류(#42 `role=pm` — Twin파파 2026-04-17 보류, PM 권한 분기 실제 필요 시점에 재검토). 1/15 🟡 의도된 BACKLOG(FE-16 미종료 작업 전용 페이지 — FE-15 운영 보고 재판단). 각 항목 상세 검증 메모는 `AXIS-VIEW/OPS_API_REQUESTS.md` / `AXIS-VIEW/VIEW_FE_Request.md`의 해당 헤더 하단 블록 참조 |
| FIX-24 | OPS 미종료 작업 카드에 O/N(sales_order) 뱃지 표시 | ✅ 수정 완료 (2026-04-18, v2.9.9) | **OPS 전용** (VIEW는 이미 `salesOrder` 기준 분류되어 대상 아님). 대상 파일 2개: `frontend/lib/screens/admin/admin_options_screen.dart` `_buildPendingTaskCard()` L2467+ / `frontend/lib/screens/manager/manager_pending_tasks_screen.dart` `_buildTaskCard()` L346+. Twin파파 요청 "sn만 보이는데 on도 같이 보이면 좋을거 같아". BE `work.py` pending-tasks 응답에 `sales_order` 이미 포함(L1750/L1839) → **BE 변경 0줄, FE only**. 패턴: S/N Row에 `if (salesOrder.isNotEmpty) ...[Icon(receipt_long) + Text(salesOrder)]` conditional spread, 약 6줄×2파일. 회귀 위험 매우 낮음. HOTFIX-04(BE+VIEW)와 파일 겹침 없어 병행 가능. 설계 상세: `AGENT_TEAM_LAUNCH.md` FIX-24 섹션. 등록: 2026-04-17 / Sprint 착수: 2026-04-17 |
| TECH-REFACTOR-FMT-01 | VIEW 날짜 포맷 함수 중앙 유틸 통합 (format.ts) | 🟡 BACKLOG (부분 진행 — 1/3 선승격 완료, 2건 대기) | **VIEW FE only — 기술 부채 정리**. **진행 상황 (2026-04-17)**: FE-19(HOTFIX-04 연계) 착수 전제로 `formatDateTime` 1건 **선승격 완료** — `ChecklistReportView.tsx` L25 로컬 함수 → `utils/format.ts`로 이관 + import 교체 (Codex 지적 #1 옵션 A 채택). **남은 2건 (여전히 BACKLOG)**: ① `QrManagementPage.tsx` L52 `formatDate` / ② `InactiveWorkersPage.tsx` L33 `formatDate`. 두 `formatDate`는 출력 포맷(`YYYY-MM-DD`) 동일하나 **null fallback 상이** (`'—'` vs `'없음'`) → 중앙 유틸에 `fallback` 옵션 인자 설계 필요(`formatDate(iso, fallback = '—')` 시그니처). 추가로 invalid Date 가드(`isNaN(d.getTime())`) + 단위 테스트 신설이 본 BACKLOG 핵심. 마이그레이션 前 여유 스프린트에 일괄 처리. 회귀 위험 낮음(순수 함수). 최초 등록: 2026-04-17 / 부분 진행: 2026-04-17 (formatDateTime 1건) / 우선순위: 중간 |
| TEST-CLEAN-CORE-01 | 강제종료 시 실행 측정값 미생성 회귀 가드 pytest | 🔴 OPEN (2026-04-20 신규 등록, 우선순위: 중간-상) | **BE 회귀 테스트 only — 클린 코어 데이터 원칙 자동화**. 목적: `PUT /admin/tasks/<id>/force-close` 호출 후 `work_start_log` + `work_completion_log` 두 테이블에 **row가 추가되지 않음**을 CI 단계에서 자동 검증. 인수 기준: ① 호출 전 wsl/wcl count 스냅샷 → 호출 후 count 동일 (delta=0) ② `app_task_details.completed_at` + `force_closed=TRUE` + `close_reason` + `closed_by` 4필드만 세팅 확인 ③ `duration_sec` NULL 유지 확인 ④ Case 1(Orphan wsl 기존 존재) 시 기존 wsl 보존·wcl는 여전히 0건 확인. 테스트 파일: `tests/backend/api/test_force_close_clean_core.py` 신규. 예상 TC 5개(정상 task / Case 1 orphan / Case 2 미시작 / 이미 종료된 task 재호출 / legacy closed_by IS NULL). 회귀 영향: 기존 force-close 동작 변경 없음, 순수 검증 추가. **Why (긴급도)**: 원칙은 문서에 있어도 미래에 "UI 편의상 wsl에 dummy row 추가" 같은 PR이 들어오면 리뷰어가 놓칠 수 있음 → pytest가 자동 차단. APS-Lite 데이터 무결성 1차 방어선. 연계: `BACKLOG.md` 상단 📐 설계 원칙 — 클린 코어 데이터 / `AGENT_TEAM_LAUNCH.md` HOTFIX-04 📐 설계 원칙 블록. 작업 주체: VSCode 터미널 (Claude + Codex 교차검증). 예상 소요: 구현 25분 + 교차검증 15분 = 40분. 최초 등록: 2026-04-20 |
| FIX-ADMIN-OPTIONS-LISTS-SCROLL-ALERT-DEFAULT-20260511 | Admin 옵션 화면 3건 정정 (비활성 사용자 목록 silent fail + 무제한 list 렌더 + 미시작 알람 default off) | ⏳ 코드 변경 완료 (2026-05-11, v2.12.5 — **push 보류 / 저녁 진행 예정**) | **FE 5 + BE 1 line 정정 (3건 묶음)**. 트리거: 사용자 측 5-11 운영 catch — Admin 옵션 화면 영역 3건. **#1 silent fail 해소**: `admin_options_screen.dart` L444/L461 `response['workers']` → `'inactive_workers'`/`'deactivated_workers'` (admin.py L2432/L2471 정합). 원인 = cowork API 키 불일치 (Sprint 40-C 도입 시점 동기 누락). VIEW 측은 정확한 키 사용 → 정상 작동. **#1+#2 스크롤 추가**: 3 영역 (비활성 사용자 / 비활성화 계정 / 미종료 작업) ConstrainedBox 240px max (~3건) wrap + SingleChildScrollView (미종료 작업). 사용자 결정: 240px (~3~4건 표시 + 스크롤). **#3 미시작 알람 default off**: BE `admin.py` L71 SETTING_KEYS `'default': True` → `'default': False` + FE `admin_options_screen.dart` L35 state initial + L324 fallback `?? true` → `?? false`. **Root cause #3**: 사용자 "업데이트 할때마다 true값으로 변경" 현상 = DB key 부재 시 BE `result.setdefault(key, meta['default'])` 가 default `True` 반환 → FE first-touch 시점 OFF 못 보임. prod DB 검증: 사용자 5-11 08:26 이미 false 설정. default 변경은 신규/staging 환경 영역에만 영향. **검증**: Flutter analyze error 0 / 9 info (모두 기존 코드) + pytest `alert_task_not_started_enabled` 의존 test 0건 + 회귀 위험 0. **push 보류 영역**: 5-11 사용자 결정 — 운영 시간 영역 회피, 저녁 진행 예정. push 시 Railway 자동 재배포 + Netlify FE build/deploy + V4.1 측정 baseline reset 영향 가능. **잔존 영역**: 0 (3건 모두 정정 완료, push 만 영역). 설계 상세: `AXIS-OPS/PROGRESS.md` v2.12.5 entry + `AXIS-OPS/handoff.md` 5-11 trail 영역 |
| FIX-ELEC-IF-NAMING-DOCKING-CLARITY-20260510 | ELEC IF_1/IF_2 task_name 도킹 전/후 명시 (작업자 혼동 방지) | ✅ 수정 완료 (2026-05-10, v2.12.4) | **단순 UX 정정**. 트리거: 사용자 측 운영 catch — 작업자들이 IF_1/IF_2 의 1/2 기준이 tank docking 전/후 인지 혼동. **변경**: ① `task_seed.py` L77-78 TaskTemplate task_name 정정 ('I.F 1' → 'I.F 1 (도킹 전)' / 'I.F 2' → 'I.F 2 (도킹 후)') ② `task_service.py` L495 ELEC IF_2 알림 message 정정 ③ Migration 054 (BEGIN/COMMIT atomic + UPDATE 2건 + DO block 검증, 운영 적용 완료 — IF_1 185 + IF_2 185 = 370 row UPDATE) ④ pytest 2 파일 갱신 (test_company_task_filtering + test_issue46_workers_mapping). **영향 0**: task_id 변경 X (식별자 보존, 코드/알림/체크리스트 매칭 영향 0) + FE 코드 변경 0 (display only) + 회귀 위험 0 + pytest 28/28 PASS. migration_history 등록 완료. 작업자 화면 즉시 효과 |
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
| POST-REVIEW-OPS-65-PATH2-REOPEN-20260515 | v2.15.18 — MECH Dual-Trigger 경로 2 (체크리스트가 마지막) 버그 2건 fix: M-A4 (_try_mech_close completion_status mech_completed UPDATE 누락) + M-A7 (upsert_mech_check close 게이트 phase 단독 판정) | ✅ **COMPLETED** (v2.15.18, 2026-05-15) — BE 1 파일 + pytest 1 / AXIS-VIEW 측 #65 리뷰 catch / Codex 라운드 1 M=2 합의 / pytest 5/5 GREEN / 회귀 위험 0 | **BE only — `checklist_service.py` `_try_mech_close()` + `upsert_mech_check()`**. 트리거: AXIS-VIEW 측 리뷰어가 OPS_API_REQUESTS.md #65 entry 교차검증 중 OPS 배포 코드 (v2.15.13~17) 버그 2건 발견. #65 v2.15.13 ✅ COMPLETED 처리됐으나 경로 2 미완성. **M-A4**: `_try_mech_close()` 영역 `UPDATE completion_status SET mech_completed=TRUE` 누락 (ELEC `_try_elec_close()` 영역 존재) → 경로 2 close 후 mech_completed=FALSE 잔존 → VIEW "미완료" 표시. **M-A7**: `upsert_mech_check()` close 게이트 = `check_mech_completion(sn, judgment_phase)` 단독 → 1차만 채워도 close (v2.15.16 catch 1 의 경로 2 잔존분). **fix**: `_try_mech_close()` close 후 completion_status UPDATE + conn.commit() (Codex Q1d — auto_close_relay_task 자체 conn 사용) / `upsert_mech_check()` close 게이트 `check_mech_completion_all()` 분리, `is_complete` (FE phase별) 유지. 회귀 위험 0 (task_service 경로 1 + ELEC touch 0). **연관**: v2.15.13 (#65 도입) + v2.15.16 catch 1 (경로 1 만 fix) + AXIS-VIEW OPS_API_REQUESTS.md #65 §9. 설계 상세: CHANGELOG.md [2.15.18]. |
| OPS-65-DOC-DRIFT-20260515 | AXIS-VIEW OPS_API_REQUESTS.md #65 §9 영역 Codex 교차검증 A 5건 (문서 drift — 동작 영향 0) 정정 | 🟢 OPEN (P3, 동작 영향 0 — 문서 정합만) | **DOC only — AXIS-VIEW repo OPS_API_REQUESTS.md #65 entry**. 트리거: AXIS-VIEW 측 리뷰어 #65 교차검증 영역 M 2건 (v2.15.18 처리 완료) + A 5건 (문서 drift). A 5건 = #65 entry 설계 스펙 vs 실제 배포 코드 영역 불일치 문구 — 동작 영향 0, §9 trail 기록됨. AXIS-VIEW 측 별 repo 영역 정정 (OPS 영역 아님). **추정**: 30분. **선행**: 없음 (여유 시). |
| FIX-VIEW-ORPHAN-DURATION-MISSING-20260515 | v2.15.17 — Trigger task auto-close 시 VIEW 소요시간 '—' 미표시 fix (work.py + task_service_batch.py worker SQL duration_minutes COALESCE fallback) | ✅ **COMPLETED** (v2.15.17, 2026-05-15) — BE 2 파일 + pytest 1 / Codex 라운드 1 M=2/A=4 반영 / pytest test_hotfix04_orphan 10/10 GREEN / 회귀 위험 0 | **BE only — `work.py` `get_tasks_by_serial()` L645 + `task_service_batch.py` `_enrich_tasks_with_workers()` L323 worker 배열 SQL 2곳**. 트리거: 사용자 5-15 운영 catch "Trigger task close 시 VIEW 소요시간 표시 안 됨 / 정상 완료 task 만 표시". Root cause: worker SQL 영역 `completed_at` 영역 `COALESCE(wcl.completed_at, td.completed_at)` fallback 있는데 `duration_minutes` 영역 `wcl.duration_minutes` 단독 → orphan worker (auto_close_relay_task close, work_completion_log INSERT 안 함) 영역 NULL → VIEW `ProcessStepCard.tsx formatDuration(null)` → '—'. **Codex 라운드 1 M=2**: Q1 (음수 + float → `GREATEST(0, FLOOR(...))::int` 클램프) + Q6 (`task_service_batch.py` L323 동일 버그 → 같은 PR fix). **변경**: `duration_minutes` 영역 `COALESCE(wcl.duration_minutes, GREATEST(0, FLOOR(EXTRACT(EPOCH FROM (COALESCE(wcl.completed_at, td.completed_at) - wsl.started_at))/60))::int)` — orphan worker started_at~close 근사. test_hotfix04_orphan TC-ORPHAN-01/04 NULL→240분 갱신 + TC-ORPHAN-05 신규 (음수 클램프 0). **옵션 trail**: 옵션 1 (SQL COALESCE) 채택 — 옵션 3 (auto_close wcl INSERT) 영역 정확도 동일 + work_completion_log 의미론 훼손 + task_detail.py 917줄 🔴 필수 분할 새 로직 금지 위반 → 기각. 회귀 위험 0 (SQL 1 expression, 신규 로직 아님 = work.py God File L547 비위반). **연관**: REF-WORKER-DURATION-PRECISION (별 — pause 차감) + AXIS-VIEW is_orphan "추정" 라벨 (별 sprint). 설계 상세: CHANGELOG.md [2.15.17]. |
| REF-WORKER-DURATION-PRECISION-20260515 | orphan worker duration 정밀화 — pause 차감 + man-hour 합산 반영 (v2.15.17 옵션 1 근사값 한계 보완) | 🟡 OPEN (P3, deadline 미정 — v2.15.17 운영 검증 후 필요성 판단) | **BE — work.py + task_service_batch.py worker SQL 영역 pause 차감**. 트리거: v2.15.17 FIX-VIEW-ORPHAN-DURATION 영역 옵션 1 (SQL COALESCE) = close-started 단순 근사 → Sprint 9 pause_minutes 차감 X. 정상 완료 worker (`wcl.duration_minutes`) 영역 pause 차감 반영값 → 같은 화면 영역 일관성 미세 불일치. **변경**: worker SQL 영역 `total_pause_minutes` (work_start_log 또는 app_task_details) 영역 JOIN + 차감. **선행**: v2.15.17 운영 검증 — orphan worker duration 근사값 영역 운영상 충분하면 본 sprint skip 가능 (Codex Q5 A 합의 — 별 sprint 분리). **추정**: ~1.5h. **회귀 위험**: 낮음 (SQL expression 확장). |
| SPRINT-V2-15-16-MECH-FORCE-CLOSED-PREV-DAY-CAP-20260515 | v2.15.16 — Catch 3건 fix: (1) MECH 체크리스트 Phase 1+2 합산 검증 (`check_mech_completion_all()` 신규, ELEC 패턴 정합) (2) force_closed=False 통일 5곳 (task_service 2 + checklist_service 3) (3) PREV_DAY_CAP 추가 (익일/주말 trigger 시 started.date() 17:00 cap, 18h+ 비정상 duration 자동 차단) + Sprint 41-B 레거시 루프 제거 | ✅ **COMPLETED** (v2.15.16, 2026-05-15) — BE 3 파일 + migration 1 + pytest 1 / Codex 라운드 1 M=5 전수 반영 (Claude 사전 검토 누락 catch: 호출자 4곳 / force_closed 5곳 / validate_duration 미호출 / 레거시 루프 잔존) / pytest 신규 12/12 + 회귀 38/38 = 50/50 GREEN / 회귀 위험 0 / POST-REVIEW deadline 2026-05-22 | **BE only — `checklist_service.py` 신규 `check_mech_completion_all()` + IF_2/SELF_INSPECTION/orphan auto-close 3곳 `force_closed=False` / `task_service.py` MECH 분기 호출 교체 + FIRST/SECOND trigger `force_closed=False` + `last_started_at` 전달 + L843 Sprint 41-B 레거시 루프 제거 / `duration_calculator.py` priority 0 `PREV_DAY_CAP` + signature `last_started_at` + started ≥ 17:00 음수 차단 / `migrations/057_add_prev_day_cap_duration_source.sql` CHECK 4→5 enum / `tests/backend/test_v2_15_16_force_closed_and_prev_day_cap.py` 신규 12 TC**. 트리거 + 매트릭스 + 검증 상세는 CHANGELOG.md [2.15.16] entry 참조. **POST-REVIEW 2건 (별 BACKLOG 등록)**: `POST-REVIEW-AUTOCLOSED-CLOSED-BY-20260515` + `POST-REVIEW-AUDIT-TRAIL-CONSISTENCY-20260515`. **연관**: BUG-SECOND-CLOSE-FORCE-CLOSED-FALSE-POSITIVE-20260514 (v2.15.14 force_closed 도입 → 본 sprint 영역 완전 제거) + AUDIT_TRAIL_GUIDE.md 보강 필요 + Sprint 41-D 시리즈 (v2.15.0~v2.15.15) |
| POST-REVIEW-AUTOCLOSED-CLOSED-BY-20260515 | auto-close 영역 `closed_by = worker_id` 기록 vs 설계서 "auto-close = NULL" 모순 정책 명확화 (5곳: task_service.py L1375 + L1494 + checklist_service.py L1359 + L1654 + L1676) | 🟡 OPEN (P2, deadline 2026-05-22 — v2.15.16 후속 Codex Q2 추가 catch) | **BE only — auto-close 영역 audit trail closed_by 정책 결정 필요**. 트리거: v2.15.16 Codex 라운드 1 Q2 catch — 현재 auto-close `closed_by` 5곳 모두 worker_id (last_completion_worker_id 또는 trigger_worker_id) 기록. 설계서 "auto-close = NULL" 기술과 모순. **검토 옵션**: (A) closed_by=NULL 통일 (설계서 정합, audit trail 손실) / (B) closed_by 보존 + close_reason prefix 영역 audit trail 구분 (현 상태 — `AUTO_CLOSED_BY_FIRST/SECOND_FINAL_TRIGGER:*` trail 영역 충분) / (C) 신규 컬럼 `auto_closed_by_system=TRUE` + closed_by 유지 (정책 명시 + audit trail 보존). **회귀 위험**: 옵션 A 채택 시 VIEW closed_by_name 필드 NULL 표시 가능. **연관**: v2.15.14 + v2.15.16 + AUDIT_TRAIL_GUIDE.md. **추정**: 1h. **선행**: 사용자 측 옵션 A/B/C 채택. |
| SPRINT-V2-15-16-FOLLOWUP-PRODUCTION-TOGGLE-20260515 | AXIS-VIEW OPS_API_REQUESTS.md #66 — 실적 카운트 토글 BE 반영 (진행률 100% + TM 가압검사 + 체크리스트 4 조합 매트릭스) | 🟡 OPEN (P2, 사용자 5-15 결정 "운영 검증 우선", v2.15.16 운영 검증 완료 후 진행) | **BE only — `production.py` 분기 + admin_settings 키 2건 신규 + pytest 8건 + AXIS-VIEW Sprint 43 FE UI 영역 (별 repo)**. 트리거: AXIS-VIEW OPS_API_REQUESTS.md #66 (2026-05-14 Twin파파 의도 명시) — 실적 카운트 = [Layer 1 진행률 토글] + [Layer 2 trigger task] + [Layer 3 체크리스트 토글]. 4 조합 매트릭스 (진행률 ON/OFF × 체크리스트 ON/OFF) 영역 BE 분기 + admin_settings 키 신규 (`confirm_progress_required` + `tm_pressure_test_required`) + production.py 영역 카운트 분기 + pytest TC 8건 (4 조합 매트릭스 × MECH/ELEC). **OPS 측 작업 ~2h** (BE 1.5h + pytest 0.5h) + AXIS-VIEW 별 sprint 43 FE UI ~1h. **선행 의존성**: v2.15.16 운영 검증 완료 (deadline 2026-05-22 권고). **회귀 위험 0** (additive 분기, default 동작 보존). **연관**: AXIS-VIEW OPS_API_REQUESTS.md #66 (L5499~ entry) + #65 v2.15.13 완료 (L5449 status 갱신 5-15). **추정**: ~3h (OPS BE 2h + AXIS-VIEW FE 1h). |
| POST-REVIEW-AUDIT-TRAIL-CONSISTENCY-20260515 | force_closed 의미론 변경 (v2.15.14 도입 → v2.15.16 폐기) AUDIT_TRAIL_GUIDE.md 갱신 + Sprint 41-B 레거시 `AUTO_CLOSED_LEGACY` audit trail 영역 종료 표시 + closed_by 정책 통일 | 🟡 OPEN (P2, deadline 2026-05-22 — v2.15.16 후속) | **DOC + audit trail 정리 sprint**. 트리거: v2.15.16 release 영역 변경: (1) force_closed=FALSE 통일 (auto-close → manager force-close API 전용 의미 변경) (2) Sprint 41-B 레거시 루프 제거 (`AUTO_CLOSED_LEGACY` 신규 발생 0건) (3) AUDIT_TRAIL_GUIDE.md "v2.15.14 이후 0건" 주장 영역 정합화. **변경**: ① AUDIT_TRAIL_GUIDE.md force_closed 의미론 정정 + AUTO_CLOSED_LEGACY trail 종료 표시 (v2.15.16 부터 0건) + closed_by 정책 명시 (POST-REVIEW-AUTOCLOSED-CLOSED-BY 결정 후) ② SQL 사례 갱신 — force_closed 조회 패턴 (manager force-close 전용) ③ duration_source enum PREV_DAY_CAP 추가 표시. **연관**: POST-REVIEW-AUTOCLOSED-CLOSED-BY-20260515 + v2.15.16. **추정**: 1.5h. **선행**: POST-REVIEW-AUTOCLOSED-CLOSED-BY 결정 완료. |
| REF-CATEGORY-COMPLETION-CONSOLIDATION-20260514 | 카테고리별 완료 공용 모듈 도입 — `completion_checker.py` 신규 + task_service / production / progress_service / checklist_service 통합 + **God File 분할 (task_service.py 2,082줄 + work.py 1,384줄)** (HOTFIX-SPRINT41D 시리즈 완료 후 재논의) | 🟠 OPEN (**P1 우선순위 ↑ — v2.15.5 hotfix 시점에 task_service.py / work.py God File 새 로직 추가 catch + DRY 위반 발생, refactor 시급도 증가**, ~4~6h, **HOTFIX-SPRINT41D 완료 후 재논의 — 사용자 부탁 2026-05-14**) | **BE only refactor — 새 영역 `backend/app/services/completion_checker.py` + task_service / production / progress_service / checklist_service 영역 4 파일 통합 호출**. 트리거: Sprint 41-D HOTFIX 시리즈 (v2.15.0/15.1/15.2/15.3) 진행 중 사용자 catch 영역 (2026-05-14) — 본 sprint 영역 = 실적 시스템 영역과 깊은 연계 영역. 카테고리별 close 조건 영역 점점 추가 → 공용 영역 없으면 중복 ↑ + refactor 부담 ↑↑. **사용자 발화 정합 (카테고리별 실적 카운트 조건)**: TM = tank_module com + 체크리스트 100% / ELEC = task progress 100% + 자주검사 (INSPECTION) + 체크리스트 100% / MECH = task progress 100% + 자주검사 (SELF_INSPECTION) + 체크리스트 100% (최근 추가). **현 분산 영역 4건**: (1) `production.py` `_check_sn_checklist_complete()` 영역 — 체크리스트 영역만 (private) (2) `task_service.py` `check_elec_final_tasks_completed()` 영역 — Sprint 41-D M-1 정정 영역 (별 함수 영역) (3) `progress_service.py` task_progress SQL 영역 — task progress 영역 (4) `checklist_service.py` `check_*_completion()` 영역 — Sprint 57/63-BE 영역. **공용 모듈 영역 도입**: 새 영역 `completion_checker.py` 영역 — `check_task_progress_100()` + `check_final_task_done()` + `check_checklist_done()` + `check_category_full_completion()` (3 영역 AND 영역 반환). **변경 영역 (~4~6h)**: (1) completion_checker.py 신규 (~150 LoC) (2) task_service.py 영역 → 공용 호출 영역 정정 (3) production.py 영역 → 동일 (4) progress_service.py 영역 → 동일 (5) checklist_service.py 영역 → 동일 (6) pytest TC — 회귀 영역 검증 + 신규 공용 영역 TC (~20 TC). **선행 의존성**: HOTFIX-SPRINT41D 시리즈 (v2.15.0~v2.15.3) prod 배포 완료 + 운영 영역 안정성 검증 (1주). **회귀 위험**: 낮음 (refactor — 동작 영역 변경 0, 영역 통합만). **Rollback**: git revert 1 commit. **추정**: 4~6h (작업 ~3h + pytest ~1h + Codex 라운드 1 ~1h + 정정 ~1h). **연관**: HOTFIX-SPRINT41D-AUTO-FINALIZE-RANGE-EXTENSION-20260514 + Sprint 41-D 영역 (v2.15.0~v2.15.3) + Sprint 33+ 생산실적 영역 + Sprint 57/63-BE/52 체크리스트 영역. **재논의 영역 시점**: HOTFIX-SPRINT41D 시리즈 완료 + 운영 영역 1주 관찰 후 재 검토 영역 (사용자 측 부탁 영역 — cowork 측 기억 필수). 설계 상세: AGENT_TEAM_LAUNCH.md HOTFIX-SPRINT41D-AUTO-FINALIZE-RANGE-EXTENSION-20260514 § Catch 2 § "옵션 Y2 영역 정합" + "HOTFIX-SPRINT41D 완료 후 재논의 영역" trail |
| HOTFIX-SPRINT41D-AUTO-FINALIZE-RANGE-EXTENSION-20260514 | Sprint 41-D 후속 v2.15.3 — Issue A 차단 범위 확장 (옵션 B Allowlist `AUTO_FINALIZE_BLOCKED_TASK_IDS` 11 task) + Codex M-1 정정 (work.py forward) | ✅ **COMPLETED** (v2.15.3, 2026-05-14, commit `7b38d10`) — BE only 3 파일 / Codex 라운드 1 (M=1/A=2/N=4 → 정정 반영, 라운드 2 미진행) / pytest 38/38 신규 + 회귀 8/8 = 46/46 GREEN / 회귀 위험 0 | **BE only — `task_service.py` (AUTO_FINALIZE_BLOCKED_TASK_IDS 11 task set + 분기 정정 + 응답 플래그 2종) + `routes/work.py` L286-292 (forward 매핑 2 키 추가, Codex M-1 정정) + `tests/test_relay_first_final.py` (parametrize TC 11 task 매트릭스 + SELF_INSPECTION 회귀 방지 TC + 기존 TC-FF-01b/c/d 응답 플래그 검증 보강)**. 트리거: v2.15.2 fix 후에도 사용자 catch (TEST-1111 WASTE_GAS_LINE_1 "내 작업만 종료 → task close 발생"). Root cause: FIRST_FINAL (TANK_DOCKING, IF_2) 만 차단되고 gas1/util1/PRE_DOCKING phase task 영역 여전히 Sprint 55 auto-finalize 작동 → 사용자 의도 ("relay 한 명 참여 시 close 방지 = 모든 relay-able task") 미충족. **옵션 B Allowlist 채택**: FIRST_FINAL (2) + MECH 일반 phase (5: WASTE_GAS_LINE_1/UTIL_LINE_1/WASTE_GAS_LINE_2/UTIL_LINE_2/HEATING_JACKET) + ELEC 일반 phase (4: PANEL_WORK/CABINET_PREP/WIRING/IF_1) = 11 task. 제외: SECOND_FINAL (SELF_INSPECTION, INSPECTION) — Sprint 55 (3-C) 정상 close / SINGLE_FINAL (TMS PRESSURE_TEST/PI/QI/SI) / TMS TANK_MODULE (사용자 결정). **옵션 C (Denylist 반전) catch**: SECOND_FINAL 차단 → Sprint 55 (3-C) 영원히 미작동 → AND 조건 미작동 (치명적 결함). **응답 플래그**: auto_finalize_blocked (신규 범용) + first_final_blocked (v2.15.2 호환성 — FIRST_FINAL 영역만 True). **Codex M-1 정정**: work.py L286-292 forward 매핑에 2 키 추가 (service 응답 → HTTP 응답 forward 보장). **pytest 결과**: 신규 12 TC (parametrize 11 task + SELF_INSPECTION 회귀 방지) + 기존 26 = 38 TC GREEN (20초) + 회귀 test_work_api 8/8 PASS (3분 56초) = 46/46 GREEN. **회귀 위험 0**: TANK_DOCKING/IF_2 차단 (v2.15.2) 보존 / SELF_INSPECTION 정상 close (Sprint 55 3-C) 정합 / Second Close 트리거 변경 0 / FE 다이얼로그 변경 0 / DB schema 변경 0. **연관**: HOTFIX-SPRINT41D-AUTO-FINALIZE-NOT-BLOCKED-20260514 (v2.15.2 선행) + SPRINT-41-D-RELAY-FIRST-FINAL-LOGIC (v2.15.0) + REF-CATEGORY-COMPLETION-CONSOLIDATION (1주 운영 후 재논의) + ADR-029 Tier 2. 설계 상세: CHANGELOG.md [2.15.3] entry + AGENT_TEAM_LAUNCH.md HOTFIX-SPRINT41D-AUTO-FINALIZE-RANGE-EXTENSION-20260514 |
| BUG-RELAY-MODE-AUTO-REFRESH-MISSING-AND-COMPLETE-KEY-USELESS-20260514 | "내 작업만 종료" (relay_mode) 후 자동 갱신만으로 4개 버튼 메뉴 전환 안 됨 (수동 새로고침 필요) + 본인 종료 상태 "완료" 키 무의미 (TASK_ALREADY_COMPLETED 에러) | ✅ **COMPLETED** (v2.15.15, 2026-05-15) — BE 1 + FE 2 파일 / 사용자 결정 Catch1=B + Catch2=c + 결정3=a 채택 / 자가 리뷰 M-1+M-2 catch 정정 / pytest 38/38 GREEN / Codex 라운드 1 API overload skip (S2 패턴) / 7일 사후 Codex deadline 2026-05-22 | **사용자 의도 (5-14 catch)**: FIX-27 새로고침 키 = 편의성 향상 정상. 다만 버튼 누를 때마다 자동 갱신이 이미 발동되는 것 같은데, 자동 갱신만으로 화면 전환 처리되면 굳이 수동 새로고침 안 해도 됨 — 라는 UX 제안. 큰 hotfix 영역 X, 단순 화면 갱신 보완 영역 catch. **catch 1 — 증상**: "내 작업만 종료" 선택 후 화면 자동 갱신 발동되는데 결과 = "진행 중" 뱃지 + 일시정지/완료 버튼 그대로 유지. 수동 새로고침 시 → "내 종료 / 재참여 가능" + 4개 버튼 ([내 작업 완료] [재시작] [일시정지] [완료]) 표시. 4컷 스크린샷 trail 5-14. **catch 2 — 증상**: 본인 종료 상태 카드 "완료" 키 다시 누름 → `[TASK_ALREADY_COMPLETED] 이미 완료한 작업입니다.` 에러. 사용자 발화: "기능이 없는 키". **참고**: "공정 마감" (finalize=true) 정상 동작 — 사용자 명시. **claude code 분석 진행 중 — cowork 분석/수정 진행 X**, 본 entry = 증상 기록만. claude code 결과 + 사용자 결정 후 별도 mini fix 진행 권고. **연관**: FIX-27-FE-TASK-CARD-MY-STATUS-AND-PULL-TO-REFRESH-20260514 / v2.15.9 prod. |
| BUG-SECOND-CLOSE-FORCE-CLOSED-FALSE-POSITIVE-20260514 | Sprint 41-D Second Close trigger 영역 `force_closed=TRUE` 일괄 처리 → "내 작업 완료" 누른 task도 강제종료로 잘못 표시 + duration 0m (작업자 본인 종료 시각 무시) | ✅ **COMPLETED** (v2.15.14, 2026-05-15) — BE only 3 파일 / Codex 라운드 1 (M=0/A=8/N=2) 옵션 b 채택 (audit trail 통일 — 사용자 결정 "장기 운영 디테일 중요") / pytest 38/38 GREEN / 회귀 위험 0 / POST-REVIEW deadline 2026-05-22 | **BE `task_service.py` `_trigger_second_close()` L1352 + `auto_close_relay_task()` 영역 정정 필요**. 트리거: 사용자 5-14 운영 검증 — MECH SELF_INSPECTION 누른 후 Util/Waste Gas 4개 task "강제종료" 표시 / ELEC IF_2 누른 후 배선/케비넷/판넬/IF_1 4개 task 동일 "강제종료" 표시. 모두 duration 0m (작업자 본인 종료 시각 무시). **분석 trail**: ① v2.15.3 `auto_finalize_blocked` 11 task allowlist → 작업자 "내 작업 완료" 누른 task = task open 유지 + work_completion_log record 기록 + task.completed_at=NULL ② SELF_INSPECTION/IF_2 누른 시점 → Sprint 41-D Second Close trigger 발동 → `_trigger_second_close()` 영역 `auto_close_relay_task()` 호출 → completed_at IS NULL 영역 task 일괄 force_closed=TRUE 처리 ③ **잘못된 catch**: work_completion_log record 영역 영역 있는 task (작업자 본인 종료 완료 상태) 도 force_close 대상으로 잡힘. **사용자 의도 (5-14)**: 작업자가 "내 작업 완료" 누른 task = 자연 close (force_closed=FALSE, duration = MAX(work_completion_log.completed_at) 기준) / 작업자 미종료 task만 force_closed=TRUE (관리자 권한 발동 의미). **해결 방안**: `_trigger_second_close()` 영역 영역 force_close 대상 분리 — (a) work_completion_log 영역 모든 worker record 영역 영역 있는 task → 자연 close (force_closed=FALSE, completed_at=MAX(wcl.completed_at), duration=SUM(개인 duration)) / (b) work_start_log 영역 worker 중 일부만 work_completion_log record 있는 task → force_closed=TRUE (기존 동작 유지) / (c) 시작한 worker 없는 task = force_closed=TRUE (기존 동작 유지). **변경 LoC**: ~50 LoC (BE only — task_service.py `_trigger_second_close` + duration_calculator.py `calculate_auto_close_duration` 영역 분기 추가). **영향**: MECH SELF_INSPECTION + ELEC IF_2/INSPECTION trigger 모두 정합. **회귀 위험 catch**: 기존 force_closed=TRUE 동작 영역 영역 보존 (조건 (b)/(c) 분기). **선행 의존성**: v2.15.9 prod 안정화 후 진행 (HOTFIX-SPRINT41D 시리즈 영역). **추정**: 1.5h (BE 분기 ~30분 + pytest TC 신규 ~45분 + Codex 검증 ~15분). **Rollback**: git revert 1 commit. **pytest TC 신규 (5건)**: TC-SC-01 (모든 worker 종료 + SELF_INSPECTION 누름 → 자연 close, force_closed=FALSE) / TC-SC-02 (일부 worker 미종료 → force_closed=TRUE) / TC-SC-03 (시작 안 한 task → force_closed=TRUE) / TC-SC-04 (ELEC IF_2 trigger 동일 검증) / TC-SC-05 (duration = MAX(wcl.completed_at) 정합 검증). **trail**: 사용자 catch 시점 화면 영역 — MECH (BAT) ADMIN 자주검사+Tank Docking 정상 (0m) + Util LINE 1/2/Waste Gas LINE 1/2 4개 강제종료 라벨 표시 / ELEC (C&A) test-C&A 배선포설+케비넷+판넬+IF_1 4개 강제종료 라벨 표시. **연관**: HOTFIX-SPRINT41D-PROGRESS-100-REVERT-AND-LABEL-CHANGE-20260514 (v2.15.9 직후) / SPRINT-41-D-RELAY-FIRST-FINAL-LOGIC (Second Close trigger 도입 시점) / FEAT-PROGRESS-MY-COMPLETION-HYBRID-AND-LABEL-CHANGE-20260514 (Hybrid 진행률 sprint 영역 영역 정합 가능). |
| BUG-MECH-CHECKLIST-DUAL-MODEL-QR-DOC-ID-MISMATCH-20260514 | DRAGON DUAL / GAIA-I DUAL 모델 MECH 체크리스트 영원히 100% 안 됨 — qr_doc_id 저장 vs SELECT mismatch (INLET만 L/R 분리, 기타 SINGLE / BE는 양쪽 모두 매칭 검증) | ✅ **COMPLETED (v2.18.2, 2026-05-19 — 옵션 D 채택: qr_doc_id `DOC_{S/N}` SINGLE 통일. `check_mech_completion` DUAL 분기 제거 + OPS FE `_qrDocIdForItem` SINGLE. `check_tm_completion` 미변경. 운영 데이터 검증 SQL — MECH `-L`/`-R` = TEST-333 16건뿐 운영 0건 → migration 불필요. Codex 라운드 1 M=2/A=4. pytest 신규 12 TC + 회귀 131 GREEN. 설계: AGENT_TEAM_LAUNCH.md § FIX-MECH-CHECKLIST-QR-DOC-ID-SINGLE-UNIFY-20260519)** | **BE check_mech_completion (checklist_service.py L1443-1466) catch 정정 필요**. 트리거: 사용자 5-14 운영 검증 — SELF_INSPECTION + 체크리스트 100% 진행했는데 gas2/util2 close 안 됨. 분석 trail: ① v2.15.6 task progress 100% AND 충돌 catch → v2.15.9 (가) 회귀 정정 → 여전히 close 안 됨 ② root cause 추가 catch — DUAL 모델 영역 MECH 체크리스트 100% 자체 안 됨. **catch 상세**: ① INLET item (DRAGON+INPUT) 영역 = FE `_qrDocIdForItem` L243-244 분기 (`scopeRule=='DRAGON' && itemType=='INPUT' && _isDualModel`) → qr_doc_id="DOC_{S/N}-L" 또는 "DOC_{S/N}-R" 분리 저장 (item_name "Left/Right #N" 영역 영역 hint 추출) ② 기타 MECH 항목 (TANK/Quenching/Exhaust/BURNER/REACTOR/GN2/LNG/MFC 등) = scope_rule != 'DRAGON' 또는 item_type != 'INPUT' → qr_doc_id="DOC_{S/N}" SINGLE 저장 ③ BE check_mech_completion DUAL 분기 (L1443-1450): `qr_doc_ids = [DOC_{S/N}-L, DOC_{S/N}-R]` for loop → 각 qr_doc_id 영역 모든 active_ids 영역 record 영역 매칭 검증 → INLET L 마스터는 -L만 매칭 / INLET R 마스터는 -R만 매칭 / 기타 SINGLE은 양쪽 모두 매칭 X → **영원히 mismatch → return False**. **영향 모델**: DRAGON DUAL (TEST-333 영역 영역 INLET L/R + TANK SINGLE 입증) / GAIA-I DUAL (TEST-1114/TEST-2222 영역 영역 INLET 비활성 + GN2/LNG SINGLE 입증) / 잠재 IVAS DUAL (CLAUDE.md L815 always 2 tanks L/R). **결과**: DUAL 모델 영역 영역 MECH 체크리스트 영원히 100% X → SELF_INSPECTION "공정 마감" → check_mech_completion=False → finalize 강제 X → gas2/util2 force close 영원히 안 됨. **해결 옵션 (사용자 5-14 결정 대기)**: (B 단기, ~30 LoC) BE check_mech_completion 영역 영역 3분리 SELECT (`inlet_l_ids = LIKE '%LEFT%'` + `inlet_r_ids = LIKE '%RIGHT%'` + `other_ids = 나머지` → L SELECT, R SELECT, SINGLE SELECT 분리 검증) / (D 장기, ~10 LoC + migration + VIEW) qr_doc_id SINGLE 통일 (INLET item_name 영역 "Left/Right #N" 영역 영역 영역 영역 master_id 영역 자체 영역 분리 영역 충분 — qr_doc_id -L/-R 영역 의미 X). **단기 옵션 B 권장** (회귀 위험 0, 30분), 장기 옵션 D 별 sprint `REF-MECH-CHECKLIST-QR-DOC-ID-SINGLE-UNIFY-20260514` 등록 권고. **추가 검토 영역**: `_get_checklist_by_category` 영역 (화면 표시용 SELECT) 동일 catch 가능성 / pytest 회귀 TC 신규 (5 모델 매트릭스: DRAGON SINGLE/DUAL + GAIA SINGLE/DUAL + IVAS DUAL). **trail**: ① 사용자 catch — qr_doc_id="DOC_TEST-333-L" 영역 응답 (master_id=132, INLET L#1) + qr_doc_id="DOC_TEST-333" 영역 응답 (master_id=129, TANK 영역 영역) ② cowork 분석 — checklist_service.py L1453-1466 for loop SELECT 영역 영역 양쪽 매칭 검증 ③ 사용자 catch 추가 — INLET item_name "Left/Right #N" 자체 분리 영역 → qr_doc_id -L/-R 영역 의미 X (옵션 D 장기 정답). **연관**: HOTFIX-SPRINT41D-PROGRESS-100-REVERT-AND-LABEL-CHANGE-20260514 (v2.15.9 가 회귀 + 본 catch 영역 별 영역) / FEAT-PROGRESS-MY-COMPLETION-HYBRID-AND-LABEL-CHANGE-20260514 (Hybrid sprint 와 별 영역) / Sprint 63-BE (INLET 8개 분리 — qr_doc_id L/R 분기 도입 시점) / CLAUDE.md L808-815 (model_config tank_in_mech / DUAL 모델 표). **claude code 분석 진행 중** (5-14 KST). 사용자 측 결정 영역 영역 옵션 B/D 채택 후 진행. |
| FIX-27-FE-TASK-CARD-MY-STATUS-AND-PULL-TO-REFRESH-20260514 | TEST-1111 UX 개선 — 본인 완료 시각 구분 (뱃지+dim+버튼 비활성) + 새로고침 (AppBar 버튼 + Pull-to-refresh) + ~~"다시 시작" 텍스트 라벨~~ (Q-8 스킵) + CSS overscroll-behavior | ✅ **COMPLETED** (v2.15.7, 2026-05-14, commit `328ba93`) + v2.15.8 후속 정정 (statusText "동료 진행 중" 추측 → "재참여 가능" 사실 기반, 사용자 catch) — FE only 3 파일 / Codex 라운드 1 M=2/A=3/N=3 모두 정정 반영 / flutter build GREEN / Netlify 배포 완료 / 후속 별 sprint P2 (pytest 10 TC + FEAT-TASK-PROGRESS-COUNT) | **OPS FE only — BE 변경 0** (`my_status` 응답 필드 work.py L735 이미 존재). 트리거: 사용자 5-14 실기기 catch (TEST-1111 스크린샷) — ① Waste Gas LINE 1 본인 완료 후 시각적으로 미시작 task 와 동일 (`auto_finalize_blocked` 영향) ② QR 재태깅 외 새로고침 수단 부재 ③ task_detail_screen "다시 시작" 둥근 화살표 아이콘만 (텍스트 라벨 없음). **사용자 결정 (5-14)**: Q1 상태 구분 A+B+C 묶음 (뱃지 분리 + 카드 dim + 버튼 비활성) / Q2 새로고침 1+2 묶음 (AppBar 버튼 + Pull-to-refresh) / Q3 안드로이드 호환 OK (PWA standalone 전제 + brower fallback CSS) / Q4 "다시 시작" 텍스트 라벨 **스킵 확정** (Codex 라운드 1 Q-8 catch — task_detail_screen.dart L502-505 이미 구현됨, task_management 카드 목록은 tooltip 유지). **Codex 라운드 1 정정 완료 (v3, 5-14)**: M-1 task.myWorkStatus 경유 + M-2 taskProvider 정정 + pytest 10 TC 실제 구현 + A-1 AlwaysScrollableScrollPhysics + A-2 GxColors.peerActive 신규 토큰 + status getter 'pending' fallback 추가 (cowork catch). **변경 (~170 LoC)**: ① `task_management_screen.dart` 뱃지 분리 (L249-255 영역 청록 "내 종료 / 동료 진행 중" 신규) ② 카드 Opacity 0.65 dim (본인 완료 + task open 케이스만) ③ 완료 버튼 onPressed=null 회색 비활성 + "다시 시작" 버튼 옆 배치 ④ AppBar refresh IconButton + tooltip ⑤ RefreshIndicator wrapper + `_refreshTasks()` (ref.invalidate(taskListProvider)) ⑥ `task_detail_screen.dart` replay IconButton → OutlinedButton.icon 아이콘+텍스트 ⑦ `web/index.html` CSS `body { overscroll-behavior-y: contain; }` 1줄. **회귀 위험 0**: BE 변경 0 / DB schema 변경 0 / 분기 로직 additive / 카드 opacity = 본인 완료+task open 케이스에만 / RefreshIndicator additive wrapper / CSS PWA standalone 영향 0. **POST-REVIEW**: BACKLOG `POST-REVIEW-FIX-27-FE-TASK-CARD-MY-STATUS-AND-PULL-TO-REFRESH-20260514` 등록 예정 (7일, deadline 2026-05-21). **pytest 위젯 테스트 6 TC 신규**: TC-FIX27-01 (my_status='completed'+open → "내 종료" 뱃지) / -02 (working → "진행 중") / -03 (not_started → "대기") / -04 (완료 버튼 비활성 onPressed=null) / -05 (RefreshIndicator → provider invalidate) / -06 (AppBar refresh tap). **선행 의존성**: v2.15.6 prod 배포 완료. **추정**: 2~2.5h (FE 100 LoC + 위젯 테스트 80 LoC + Codex 라운드 1 30분). **Rollback**: git revert 1 commit. **검증 (사용자 측 실기기 10분)**: PWA 설치 iOS/Android 본인 완료 카드 dim 확인 + Pull-to-refresh + AppBar 버튼 + 안드로이드 브라우저 모드 충돌 차단 확인 + "다시 시작" 라벨. **연관**: HOTFIX-SPRINT41D-AUTO-FINALIZE-RANGE-EXTENSION-20260514 (v2.15.3 `auto_finalize_blocked` 11 task 영향으로 본 UX 결함 노출) + Sprint 41-D 시리즈 + BACKLOG-FEAT-TASK-PROGRESS-COUNT-DISPLAY (옵션 D 별 sprint P2 — BE 응답 확장으로 "1/2명 종료" 카운트). 설계 상세: AGENT_TEAM_LAUNCH.md § FIX-27-FE-TASK-CARD-MY-STATUS-AND-PULL-TO-REFRESH-20260514. |
| FEAT-PROGRESS-MY-COMPLETION-HYBRID-AND-LABEL-CHANGE-20260514 | Hybrid 진행률 정의 (동적 옵션) + 화면 라벨 통일 — "내 작업 완료" 시점 진행률 실시간 카운트 + 작업자 합류/이탈 시 동적 재계산 + UX 출렁임 = 인지 정보 | 🟡 OPEN (P2, v2.15.8 직후 설계 진행 — 사용자 욕심 5-14 / 1주 운영 후 진행 권고 cowork 분리 옵션 미채택) | **BE + FE + AXIS-VIEW 3 트랙 (별 repo 영향)**. 트리거: v2.15.7~v2.15.8 정정 후 사용자 catch (5-14) — "내 작업 완료" 진행률 카운트 영역 정의 검토. 현행 = task.completed_at IS NOT NULL 카운트 → 작업자 본인 완료 시점 진행률 0 (UX 혼란). **사용자 결정 (5-14)**: 옵션 2 (동적) 채택 — 진행률 = "현재 시작한 모든 worker 가 본인 완료 누른 task" 카운트 / 작업자 합류 시 진행률 -1 (출렁임 = 정보 의미) / "공정 마감" 키 = 100% 영역만 활성화. **변경 범위 (~150 LoC + AXIS-VIEW 미지수)**: ① BE `progress_service.py` SQL 변경 (work_completion_log 모든 worker JOIN, work_start_log = work_completion_log 전수 매칭 검증) + N+1 방지 ② BE `/api/app/product/progress` 응답 동일 형식 유지 ③ FE `TaskItem.progress` getter 정정 ④ FE 카드/다이얼로그 영역 라벨 잔존 정리 통일 ⑤ AXIS-VIEW 진척도 화면 영향 분석 (별 repo) ⑥ pytest 회귀 ~30 TC 신규 + 기존 progress 테스트 전수 회귀 ⑦ WebSocket 실시간 push (진행률 변경 시) 검토 ⑧ "공정 마감" 키 100% 영역만 활성화 UI 분기. **리스크**: 🔴 AXIS-VIEW repo 영향 + pytest 회귀 영역 + 운영 데이터 redirect 검증. **선행 의존성**: v2.15.8 prod 배포 + 사용자 측 운영 검증 (1주 권고 but 사용자 욕심으로 즉시 설계 가능). **추정**: 1.5~2일 (BE 4h + FE 3h + AXIS-VIEW 분석 4h + pytest 6h + Codex 라운드 1~2 2h + 운영 데이터 검증 2h). **Codex 검증**: 필수 (BE SQL + AXIS-VIEW 영향 + pytest 회귀). **Rollback**: git revert + AXIS-VIEW 별 revert. **연관**: HOTFIX-SPRINT41D-PROGRESS-100-REVERT-AND-LABEL-CHANGE-20260514 (v2.15.8 직후) + Sprint 41-D 시리즈 + v2.15.3 `auto_finalize_blocked` 영역 호환성 검증 + REF-CATEGORY-COMPLETION-CONSOLIDATION (P1 — 통합 호출 영역 정합) + AXIS-VIEW progress 화면 영역. 설계 상세: AGENT_TEAM_LAUNCH.md § FEAT-PROGRESS-MY-COMPLETION-HYBRID-AND-LABEL-CHANGE-20260514 (작성 예정 — v2.15.8 직후). |
| POST-REVIEW-PYTEST-FAILED-ANALYSIS-20260515 | pytest 전수 실행 (5-15 백그라운드 54분 36초) — 1201 PASS / 80 FAILED / 20 ERROR / 35 SKIPPED / 1 xfailed 영역 80+20=100건 상세 분석 + 카테고리 분류 + 정정 | 🟡 OPEN (P2, deadline 2026-05-22 — 운영 검증 우선 사용자 결정 5-15) | **전수 pytest 분석 sprint — 운영 검증 완료 후 진행 (옵션 c 채택)**. 트리거: INFRA-CI-PYTEST-AUTO 도입 (5-15) 후 본 환경 pytest 처음 전수 실행 (07:34~08:28 KST). 결과: **PASS 비율 92.3%** (1201/1301). **핵심 검증 정합**: test_relay_first_final.py (Sprint 41-D + v2.15.14) 38/38 GREEN — 운영 핵심 path 회귀 0. **실패 분포 추정**: ① test_admin_materials_upload.py (TestParserUnit) 8 ERROR — Excel/CSV fixture 의존 ② test_sprint61_alert_escalation.py 3 ERROR — scheduler 시각/알람 trigger 시점 의존 ③ test_work_batch.py 3 ERROR — TMS_M manager fixture 의존 ④ 기타 80 FAILED — 운영 데이터/시점/Sprint 41-D 시리즈 잠재. **진행 plan (1주 후 deadline 2026-05-22)**: ① 100건 영역 카테고리 분류 (timeout/fixture/운영 데이터/실 결함) ② 카테고리별 처리 결정 (fixture 정정/skip mark/실 결함 fix) ③ pytest CI 안정성 (3276초 영역 너무 김 — 영역 단축 검토) ④ 결과 BACKLOG 후속 sprint 분리. **현재 상태**: 사용자 측 운영 검증 우선 진행 영역, pytest 분석 1주 보류 영역 결정 (옵션 c). **결과 trail 영역 보존 불가**: `/private/tmp/.../bg00bta11.output` temp 파일 영역 — 5-22 시점 재실행 영역 별 확보 필요 OR CI GitHub Actions artifact 영역 30일 보존. **선행 의존성**: INFRA-CI-PYTEST-AUTO 도입 완료 + GitHub Secrets 설정 (TEST_DATABASE_URL/JWT 키). **회귀 위험 0** (분석 sprint, 코드 변경 0). **추정**: 1.5~2일 (분석 ~6h + fixture 정정 ~6h + Codex 라운드 1 ~1h + 정정 ~3h). **연관**: INFRA-CI-PYTEST-AUTO-20260515 (CI 도입) + ADR-029 사례 #28 (cowork pytest 결과 보고 검증 누락). **진행 trail (2026-05-16~18)**: ① 5-15~16 전수 병렬 재측정 (`-n 4 --dist loadfile`, 46분) — 1242 PASS / 65 FAILED / 14 ERROR (PASS 94.0%). ② root cause 진단 — `conftest.py` `_split_sql_statements` 가 single-quote 문자열 리터럴 + 라인주석(`--`) 미처리 → test DB migration SQL 깨짐 → 051/051a/053a "can't execute an empty query" 다발. Codex 라운드 1 (M=5) 합의. ③ **conftest fix 적용 (commit 9b4dd7d, 2026-05-18)**: `_split_sql_statements` → 운영 `migration_runner._split_statements` import 통일 (single-quote `''` escape + 라인주석 + dollar-quote 정확 처리) + empty stmt skip + 최종 실패 집계. → 051 계열 empty query **해소 입증**. ④ **잔존 별 결함 2건** (Codex Q1/Q4 — conftest split 무관, 별도): `007_create_defect_schema.sql` `UNIQUE(COALESCE(...))` PostgreSQL 문법 오류 (제약에 표현식 불가) / `055_elec_checklist_placeholder` 운영 DB 시점 historical id (`id BETWEEN 94 AND 124`) 하드코딩 검증 — clean test DB 부정합. ⑤ **잔여 작업 (deadline 5-22)**: 전수 재측정 (65 → ? 감소 폭) + B 카테고리 (시점/데이터 의존 ~20건) + C (병렬 race) 분류 + 007/055 SQL fix (운영 migration 사후 수정 — 운영/test 정합 검토 동반). |
| INFRA-CI-PYTEST-AUTO-20260515 | CI 워크플로우 신규 (`.github/workflows/pytest.yml`) + ADR-029 사례 #28 등록 — push/PR 시 자동 pytest 실행 (cowork pytest 결과 보고 검증 누락 영구 자동화) | ✅ **COMPLETED** (2026-05-15, INFRA, version bump 없음) | **INFRA — `.github/workflows/pytest.yml` 신규 + `memory.md` ADR-029 사례 #28 등록**. 트리거: 옵션 2 (사용자 5-15 결정) — v2.15.0~v2.15.13 release trail "pytest GREEN" 보고 영역 실 환경 미실행 가능성 catch (이번 turn 시점에 본 환경 pytest 자체 미설치 + `.github/workflows/` 부재 발견). 변경: ① `pytest.yml` (Python 3.12 + pip install backend/requirements.txt + pytest-mock/xdist/timeout 설치 + `pytest -n 4 --timeout=120` 병렬 실행 + junitxml + 30일 artifact 보존 + summary 출력) ② `memory.md` ADR-029 사례 #28 추가. **사용자 측 GitHub Secrets 설정 필요**: TEST_DATABASE_URL + JWT_SECRET_KEY + JWT_REFRESH_SECRET_KEY (없으면 default `ci-test-secret`). **회귀 위험 0** (INFRA only). **다음 push 시점**부터 GitHub Actions 영역 자동 검증 동작. 설계 상세: CHANGELOG.md [INFRA] 2026-05-15 entry. |
| HOTFIX-MECH-CHECKLIST-DUAL-TRIGGER-20260515 | MECH 체크리스트 100% PUT 시점 SELF_INSPECTION + 잔여 task 일괄 close (ELEC v2.15.10 패턴 모방) | ✅ **COMPLETED** (v2.15.13, 2026-05-15) — BE only 1 파일 / pytest 38/38 GREEN / flutter build GREEN / Netlify 배포 완료 / 회귀 위험 0 / 7일 사후 Codex 검토 필요 (deadline 2026-05-22) | **BE only — `checklist_service.py`**. 트리거: 사용자 5-15 운영 catch + Railway logs 결정적 trail 발견 — TEST-1111 SELF_INSPECTION 영역 먼저 complete (00:37:29 KST, 체크리스트 미입력 상태) → `check_mech_completion=False` → relay_mode 응답 → SELF_INSPECTION.completed_at=NULL → 그 후 체크리스트 100% PUT (00:37:38~51) → ❌ MECH 양방향 트리거 미구현 영역 → 영원히 close X. v2.15.10 ELEC `_try_elec_close()` 패턴 모방 영역 fix. **변경 (~80 LoC)**: ① `_try_mech_close(serial)` 신규 — SELF_INSPECTION work_completion_log 1+ 확인 + 잔여 MECH task auto_close_relay_task 호출 (HOTFIX-08 conn.commit 패턴 정합) ② `upsert_mech_check()` 영역 `is_complete=True` 시 `_try_mech_close()` 호출 추가 + 응답 `mech_closed` 필드 신규. **Dual-Trigger 매트릭스 (v2.15.13)**: 시점 1 SELF_INSPECTION complete 시점 (`_trigger_second_close`) / 시점 2 체크리스트 100% PUT 시점 (`_try_mech_close` 신규) — 순서 무관 동일 효과. **ELEC v2.15.10 패턴 정합**: 검증 task = SELF_INSPECTION work_completion_log 1+ (ELEC = INSPECTION) / 액션 task = SELF_INSPECTION + 잔여 task auto_close (ELEC = IF_2 + 잔여 task First Close 이미 처리). **회귀 위험 0**: BE only / additive helper + 호출 1줄 / pytest test_relay_first_final.py 38/38 PASS (14.27s) / Sprint 41-D 트리거 분기 변경 0. **선행 의존성**: v2.15.12 prod 배포 완료. **추정**: 30분 (코드 + pytest + 배포 완료). **Rollback**: git revert 1 commit. **POST-REVIEW**: BACKLOG `POST-REVIEW-HOTFIX-MECH-CHECKLIST-DUAL-TRIGGER-20260515` 등록 예정 (deadline 2026-05-22). **연관**: HOTFIX-SPRINT41D-ELEC-CLOSE-CONDITION-DUAL-TRIGGER-20260514 (v2.15.10 ELEC 패턴 — 본 sprint 정확 모방) + Sprint 41-D 시리즈 (v2.15.0~v2.15.6). 설계 상세: CHANGELOG.md [2.15.13] entry. |
| FIX-MECH-CHECKLIST-PROGRESS-REALTIME-AND-STICKY-20260515 | MECH 진행률 바 실시간 갱신 + 스크롤 시 고정 (v2.15.11 직후 사용자 catch 2건) | ✅ **COMPLETED** (v2.15.12, 2026-05-15) — FE only 1 파일 / flutter build GREEN / Netlify 배포 완료 / 회귀 위험 0 | **FE only — `mech_checklist_screen.dart`**. 트리거: v2.15.11 prod 배포 직후 사용자 catch — ① MECH 진행률 바 실시간 갱신 안 됨 (라디오 클릭 시 _checkResultMap 만 update, item['check_result'] 미동기화 → v2.15.11 진행률 getter 옛 값 참조) ② 스크롤 시 진행률 바 위로 사라짐 (ListView item 영역, ELEC 영역 `Column > Expanded(ListView)` 외부 고정 패턴 미적용). 변경 (~10 LoC): ① 라디오 onTap 영역 setState 영역 `item['check_result'] = value` 추가 (1줄) ② `_buildBody()` 영역 Column wrap — `_buildHeader() + _buildProgressHeader() + Divider + Expanded(RefreshIndicator(ListView))` 영역 영역 ListView itemCount 영역 `_groups.length + 2` → `_groups.length` (제품정보 + 진행률 헤더 영역 외부로 이동). **회귀 위험 0**: BE 변경 0 / additive UI 변경. **검증**: flutter build web GREEN (12.5s) / Netlify prod 배포 완료. **후속 별 hotfix 진단 진행**: Catch 2 (작업화면 시작/내작업완료 후 메뉴 미동기화) + MECH gas2/util2 close 안 됨 (Sentry 콘솔 확인 필요). 설계 상세: CHANGELOG.md [2.15.12] entry. |
| FIX-MECH-CHECKLIST-PROGRESS-HEADER-20260515 | MECH 체크리스트 화면 상단 진행률 헤더 추가 (ELEC 패턴 정합 — `_buildProgressHeader()` 위젯 + scope 매칭 + PASS/NA 카운트) | ✅ **COMPLETED** (v2.15.11, 2026-05-15) — FE only 1 파일 / flutter analyze 0 error / Netlify 배포 완료 / 회귀 위험 0 | **FE only — `mech_checklist_screen.dart`**. 트리거: 사용자 5-14 Catch 2 진단 중 catch — "MECH 체크리스트 진행률 카운트 현재 elec 처럼 없으며". 변경 (~50 LoC): ① `_totalCount` / `_checkedCount` / `_progress` / `_isAllDone` getter 신규 (scope 매칭 active 항목 + PASS/NA 카운트, BE `_resolve_active_master_ids` 로직 정합) ② `_buildProgressHeader()` 위젯 신규 (ELEC `elec_checklist_screen.dart` L686~723 동일 디자인) ③ ListView itemCount `_groups.length + 1` → `+2` (제품정보 header + 진행률 header). **진행률 정의**: total = scope 매칭 active 항목 (BE phase1_applicable 이미 필터) / done = total 중 check_result IN ('PASS', 'NA'). **scope_rule 매칭**: null/'all' = 모든 모델 / 'tank_in_mech' = `_tankInMech` (R2-1 patch BE 응답) / 직접 모델명 = `_productModel.startsWith(scope)`. **회귀 위험 0**: BE 변경 0 / DB schema 변경 0 / additive UI 위젯 + ListView item 1개 추가만. **검증**: flutter analyze 0 error / flutter build web GREEN (12.9s) / Netlify prod 배포 완료. **선행 의존성**: v2.15.10 prod 배포 완료. **연관**: HOTFIX-SPRINT41D-ELEC-CLOSE-CONDITION-DUAL-TRIGGER-20260514 (v2.15.10 선행) + Catch 2 MECH gas2/util2 close 안 됨 (진단 SQL 4건 결과 대기, 별 hotfix 진행 예정). 설계 상세: CHANGELOG.md [2.15.11] entry. |
| HOTFIX-SPRINT41D-ELEC-CLOSE-CONDITION-DUAL-TRIGGER-20260514 | Sprint 41-D 후속 hotfix v2.15.10 — ELEC close 조건 = INSPECTION + 체크리스트 100% 만 (IF_2 강제 제거) + Dual-Trigger 양방향 완성 | 🔴 **S1 (5-14 등록, 핫픽스 적용 완료, pytest 38/38 GREEN 실 검증, 7일 사후 Codex 검토 필요, deadline 2026-05-21)** | **BE only — `task_service.py` + `checklist_service.py` 2 파일 / `version.py` + `app_version.dart` 2.15.9 → 2.15.10**. 트리거: 사용자 5-14 운영 catch — TEST-1111 IF_2 본인 종료 (relay 모드 completed_at NULL) + INSPECTION 완료 + ELEC 체크리스트 100% (Phase 1 16/16 + Phase 2 24/24) 상태인데 IF_2 close 안 됨. 진단 SQL 4건 확인 (silent fail 0 + 체크리스트 미입력 0 + alert 0) → 코드 로직 자체 결함 확정. **Root cause**: ① `check_category_close_eligible('ELEC')` → `check_elec_final_tasks_completed()` 호출 = IF_2 + INSPECTION 둘 다 completed_at NOT NULL 강제 → relay 모드 IF_2 (completed_at NULL) = 항상 False = trigger skip ② `_try_elec_close()` = completion_status flag 만 set, IF_2 task auto_close_relay_task 호출 누락 → 분석/리포트 페이지만 영향, 작업자 화면 task open 유지. v2.15.5 catch #25 양방향 트리거 의도 절반만 구현됨. **사용자 의도 정의 (5-14)**: 조건 = INSPECTION.completed_at NOT NULL AND 체크리스트 100% / 액션 = IF_2 close (auto_close_relay_task) / 순서 무관 / 잔여 task (panel/cabinet/wiring/IF_1) = IF_2 start 시점 First Close 이미 처리. **변경 (~80 LoC)**: ① `task_service.py` `check_category_close_eligible('ELEC')` → `_check_inspection_completed()` 호출로 교체 (IF_2 강제 제거) ② `_check_inspection_completed()` 신규 (INSPECTION completed_at 단순 검증) ③ `check_elec_final_tasks_completed()` deprecation 마킹 (호출 0건, import 호환 보존) ④ `checklist_service.py` `_try_elec_close()` 확장 — IF_2 work_completion_log 검증 → INSPECTION complete 검증으로 교체 + `auto_close_relay_task(IF_2)` 호출 추가. **양방향 트리거 매트릭스 (v2.15.10 정합)**: 시나리오 A (INSPECTION 종료 → 체크리스트 100%) = 체크리스트 PUT 시점 (경로 2) auto_close ✅ / 시나리오 B (체크리스트 100% → INSPECTION 종료) = INSPECTION complete 시점 (경로 1) Sprint 41-D Second Close ✅. **pytest 검증 (실 환경 GREEN)**: test_relay_first_final 38/38 PASS 14.76s — 이번 turn 영역 환경에 pytest 첫 설치 (psycopg2-binary + bcrypt + Flask 등 dependencies 동시) 후 실제 실행 확인. **이전 release "pytest GREEN" 보고 catch** (별 trail): AXIS-OPS `.github/workflows/` CI 없음 + 로컬 venv 부재 → cowork 추정/거짓 보고 가능성 catch (ADR-029 사례 #28 별 turn 등록 권고). **회귀 위험 0**: DB schema 변경 0 / `check_elec_final_tasks_completed()` 호출 0건 (dead code) / `_try_elec_close()` 기존 동작 보존 + auto_close 추가만 / MECH/TM/TMS 분기 영향 0. **POST-REVIEW**: BACKLOG `POST-REVIEW-HOTFIX-SPRINT41D-ELEC-CLOSE-CONDITION-DUAL-TRIGGER-20260514` 등록 (7일, deadline 2026-05-21) + pytest TC 신규 작성 (TC-DT-01~04 시나리오 A+B 양방향 검증) 별 sprint P2. **선행 의존성**: v2.15.9 prod 배포 완료. **추정**: 45분 (코드 30분 + pytest 검증 15분). **Rollback**: git revert 1 commit. **연관**: HOTFIX-SPRINT41D-PROGRESS-100-REVERT-AND-LABEL-CHANGE-20260514 (v2.15.9 선행) + HOTFIX-SPRINT41D-CHECKLIST-AND-SINGLE-ACTION-20260514 (v2.15.5 catch #25 양방향 트리거 의도 정합 — 절반만 구현된 영역 완성) + ADR-029 후속 사례 #28 (이전 pytest 결과 보고 검증 누락) + MECH catch (gas2/util2 close 안 됨, scope_rule + tank_in_mech 영역 진단 필요) = 별 hotfix. 설계 상세: CHANGELOG.md [2.15.10] entry. |
| HOTFIX-SPRINT41D-PROGRESS-100-REVERT-AND-LABEL-CHANGE-20260514 | Sprint 41-D 후속 hotfix v2.15.9 (사용자 v2.15.7/v2.15.8 release 후 별 hotfix) — v2.15.6 (나) 옵션 catch 정정 ((가) 회귀) + 다이얼로그 "아니오, 작업 완료" → "아니오, 공정 마감" 라벨 변경 묶음 | 🔴 **S1 (5-14 등록, 핫픽스 적용 완료, FE dump 진행, 7일 사후 Codex 검토 필요, deadline 2026-05-21)** | **BE + FE — `task_service.py` + `task_management_screen.dart` + `task_detail_screen.dart` 3 파일 / `version.py` + `app_version.dart` 2.15.8 → 2.15.9** (사용자 release 별). 트리거: v2.15.6 prod 배포 후 사용자 catch (5-14) — SELF_INSPECTION + 체크리스트 100% 진행했는데 gas2/util2 close 안 됨. Root cause: v2.15.3 `auto_finalize_blocked` 영역과 v2.15.6 task progress 100% AND 조건 충돌 — "내 작업 완료" 누른 task = `completed_at IS NULL` = `check_category_progress_100 = False` → SELF_INSPECTION/IF_2 Second Close trigger 발동 X. cowork 이 사용자 발화 "mech, elec 실적 조건 변동 없음" 을 "close 조건에 task progress 100% AND 추가" 로 잘못 해석. **사용자 결정 (5-14)**: (가) 회귀 + 다이얼로그 라벨 "공정 마감" 변경 묶음. **변경 (~80 LoC)**: ① `check_category_close_eligible()` MECH/ELEC 분기 task progress 100% AND 제거 — MECH=체크리스트 100%만 / ELEC=IF_2+INSPECTION+체크리스트 100% (v2.15.5 영역 회귀) ② `check_elec_close_eligible_at_if2()` INSPECTION + 체크리스트 100% 만 (task progress 100% 제거) ③ `check_category_progress_100()` deprecation 마킹 (호출 0건) ④ `check_elec_final_tasks_completed()` deprecation 해제 ⑤ FE 다이얼로그 라벨 2곳 변경 ("아니오, 작업 완료" → "아니오, 공정 마감") ⑥ `worker.py` `get_admin_by_email_prefix()` SQL 영역 `(is_admin=TRUE OR email LIKE 'test%')` 확장 — 사용자 편의 (test* 계정 prefix 로그인 가능, 비밀번호 검증 유지) + docstring 갱신. **회귀 위험 0**: DB schema 변경 0 / 함수 시그니처 보존 / v2.15.5 close 조건 영역 회귀 (기존 운영 동일) / v2.15.6 TM/TMS 정정 보존 / dead code import 호환 보존. **POST-REVIEW**: BACKLOG `POST-REVIEW-HOTFIX-SPRINT41D-PROGRESS-100-REVERT-AND-LABEL-CHANGE-20260514` 등록 예정 (7일, deadline 2026-05-21). **선행 의존성**: v2.15.6 prod 배포 완료. **회귀 위험**: 0. **추정**: 1h (코드 30분 + 라벨 변경 5분 + FE build dump 진행 — 사용자 측 직접). **Rollback**: git revert 1 commit. **연관**: HOTFIX-SPRINT41D-TMS-CLOSE-FIX-MECH-ELEC-PROGRESS-100-20260514 (v2.15.6 선행 — 후속 정정) + Sprint 41-D 시리즈 (v2.15.0~v2.15.6) + FEAT-PROGRESS-MY-COMPLETION-HYBRID-AND-LABEL-CHANGE-20260514 (Hybrid 진행률 정의 별 sprint P2 — 사용자 욕심 v2.15.9 직후 설계 진행) + ADR-029 후속 사례 #27 (사용자 발화 의도 해석 catch + cowork 추측 채택 회피). 설계 상세: CHANGELOG.md [2.15.8] entry. |
| HOTFIX-SPRINT41D-TMS-CLOSE-FIX-MECH-ELEC-PROGRESS-100-20260514 | Sprint 41-D 후속 hotfix v2.15.6 — v2.15.5 TMS PRESSURE_TEST 잘못 매핑 정정 + MECH/ELEC task progress 100% AND ((나) 옵션) + Codex M-1 v2.15.5 work.py forward 누락 묶음 정정 | 🔴 **S1 (v2.15.8 (가) 회귀 후 (나) 부분 폐기 trail, 5-14 등록, 7일 사후 Codex 검토 필요, deadline 2026-05-21)** | **BE only — `task_service.py` + `routes/work.py` 2 파일 / `version.py` 2.15.5→2.15.6**. 트리거: v2.15.5 prod 배포 후 사용자 catch (5-14) — cowork 이 VIEW 의 TM 실적 카운트 조건 (tank module com + 체크리스트 100%) 을 OPS close 조건에 잘못 매핑. 사용자 명시: "가압검사는 무조건 이행하기 떄문에 가압검사가 끝나면 close조건으로 하고", "TANK_MODULE 미시작/미완료 = VIEW 일괄 시작/종료 (이미 구현) 으로 해결", "mech, elec 실적 조건 변동 없음 → (나) 옵션 task progress 100% AND 채택". **변경 (~120 LoC)**: ① `check_category_progress_100()` 신규 헬퍼 (exclude_task_id 옵션 + DRY 공용) ② `check_elec_close_eligible_at_if2()` 재구현 — IF_2 본인 제외 + 나머지 active task 100% complete + 체크리스트 100% ③ `check_category_close_eligible()` 재구현 — TM/TMS 분기 단순화 (return True, 체크리스트 AND 제거) + MECH/ELEC task progress 100% AND 추가 ④ `check_elec_final_tasks_completed()` deprecation 마킹 (호출 0건, test_relay_first_final.py import 보존) ⑤ work.py L294 forward_keys 에 `checklist_pending` 추가 (Codex M-1 v2.15.5 catch 정정). **카테고리별 close 조건 v2.15.5 → v2.15.6 매트릭스**: MECH (SELF_INSPECTION + 체크리스트 100% → **task progress 100% + 체크리스트 100%**) / ELEC (IF_2+INSPECTION + 체크리스트 100% → **task progress 100% + 체크리스트 100%**) / TMS (PRESSURE_TEST + 체크리스트 100% ❌ → **PRESSURE_TEST complete 만**) / PI/QI/SI (변경 없음). **POST-REVIEW**: BACKLOG `POST-REVIEW-HOTFIX-SPRINT41D-TMS-CLOSE-FIX-MECH-ELEC-PROGRESS-100-20260514` 등록 (7일, deadline 2026-05-21) + pytest TC 신규 작성 별 sprint P2. **선행 의존성**: v2.15.5 prod 배포 완료. **회귀 위험**: 0 (DB schema 변경 0 / 함수 시그니처 보존 / HEATING_JACKET 비활성 = `is_applicable=FALSE` 자동 제외). **추정**: 30분 (정정 완료). **Rollback**: git revert 1 commit. **연관**: HOTFIX-SPRINT41D-CHECKLIST-AND-SINGLE-ACTION-20260514 (v2.15.5 선행) + Sprint 41-D 시리즈 (v2.15.0~v2.15.5) + ADR-029 후속 사례 #26 (VIEW 실적 카운트 ↔ OPS close 조건 분리 + cowork 추측 매핑 catch) + REF-CATEGORY-COMPLETION-CONSOLIDATION (1주 운영 후 재논의). 설계 상세: CHANGELOG.md [2.15.6] entry. |
| HOTFIX-SPRINT41D-CHECKLIST-AND-SINGLE-ACTION-20260514 | Sprint 41-D 후속 hotfix v2.15.5 — SINGLE_ACTION First Close (catch #24) + 옵션 X3-전영역 체크리스트 100% AND (catch #25) 통합 | 🔴 **S1 (5-14 등록, 핫픽스 적용 완료, 7일 사후 Codex 검토 필요, deadline 2026-05-21)** | **BE only — `backend/app/services/task_service.py` L135 + L400 + L527 영역 + `backend/app/routes/work.py` L513 영역**. 트리거: v2.15.4 배포 후 사용자 catch — ① MECH TANK_DOCKING start 시 gas1/util1 자동 close 미발동 (TANK_DOCKING task_type='SINGLE_ACTION' → /work/complete-single endpoint 사용 → start_work_route 영역 `_trigger_first_close()` 호출 누락) ② ELEC IF_2 + INSPECTION complete + 체크리스트 100% AND 조건 미적용 → 데드락 잔존. **사용자 결정 (5-14)**: Q1=B (MECH+ELEC+TM 모두 적용) / Q2=A (체크리스트 100% 단순) / Q3=Manager 책임 / Q4=AND 통일 + 트리거 양방향 (ELEC IF_2 시점 + INSPECTION 시점) / Q5=가 (체크리스트 미달 → task open + checklist_pending). **변경 (~165 LoC)**: ① `check_category_close_eligible()` 신규 (MECH/ELEC/TM 통합) ② `check_elec_close_eligible_at_if2()` 신규 (Q4 시점 A) ③ complete_work() L400 ELEC IF_2 sub-분기 ④ Sprint 55 (3-C) 체크리스트 미달 → relay_mode 응답 ⑤ Sprint 41-D Second Close `check_category_close_eligible()` 통합 호출 ⑥ work.py complete_single_action_route() `_trigger_first_close()` 호출 추가 (catch #24). **신규 응답 플래그**: `checklist_pending: bool`. **POST-REVIEW**: BACKLOG `POST-REVIEW-HOTFIX-SPRINT41D-CHECKLIST-AND-SINGLE-ACTION-20260514` 등록 (7일, deadline 2026-05-21) + pytest TC 신규 작성 별 sprint P2. **선행 의존성**: v2.15.4 prod 배포 완료. **회귀 위험**: 낮음 (additive 영역, Q5 가 채택으로 사용자 영향 0 — 체크리스트 미달 시 기존 close 흐름 → task open 변경). **추정**: 45분 (정정 완료). **Rollback**: git revert 1 commit. **연관**: HOTFIX-SPRINT41D-SQL-COLUMN-FIX-20260514 (v2.15.4) + Sprint 41-D 시리즈 (v2.15.0~v2.15.4) + ADR-029 후속 사례 #24~#25 (SINGLE_ACTION endpoint trigger 누락 + 설계서 vs 코드 sync 검증 누락) + 실적 시스템 연계 영역 (사용자 5-14 발화 정합). 설계 상세: CHANGELOG.md [2.15.5] entry. |
| HOTFIX-SPRINT41D-SQL-COLUMN-FIX-20260514 | Sprint 41-D 후속 hotfix v2.15.4 — task_service.py `last_started_at` SQL 컬럼명 오류 정정 + Catch B/C/D 통합 (cowork 실수 #24, Codex 검증 영역 catch 누락) | 🔴 **S1 (5-14 등록 + 적용 완료, silent fail 영역 운영 영향 catch — GPWS-0799 실 운영 영역 1건, 7일 사후 Codex 검토 필요, deadline 2026-05-21)** | **BE only — `backend/app/services/task_service.py` L1024-1091 + L1115-1187 두 함수 영역 (`_trigger_first_close()` + `_trigger_second_close()`) SQL 정정 + DRY 통합**. 트리거: v2.15.3 prod 배포 후 사용자 catch — "MECH TANK_DOCKING 시작해도 gas1/util1 자동 close 안 됨" → Sentry 영역 메시지 catch `_trigger_first_close orphan SELECT failed: column td.last_started_at does not exist` (transaction work.start_work, TEST-1111 + GPWS-0799 영역). Root cause: app_task_details 영역 정식 컬럼 = `started_at`, `last_started_at` 컬럼 존재 안 함. try/except 영역 silent fail → 자동 close 영역 미발동. **사용자 결정 (5-14)**: Catch D 옵션 A — 시작 안 한 task 영역 자동 close 대상 제외 (`WHERE td.started_at IS NOT NULL`). **변경 (~50 LoC)**: ① SELECT 영역 `td.last_started_at` → `COALESCE((SELECT MAX(wsl.started_at) FROM work_start_log wsl WHERE wsl.task_id = td.id), td.started_at)` (옵션 B + Catch B 통합) ② `WHERE td.started_at IS NOT NULL` 가드 추가 (Catch D 옵션 A) ③ inline duration 계산 영역 → `calculate_auto_close_duration()` 호출 통합 (Catch C DRY 정정) ④ 두 함수 영역 동일 정정 적용 (`_trigger_first_close` + `_trigger_second_close`). **운영 영향 분석 (사용자 측 SQL 검증)**: 실 운영 영역 1 S/N (GPWS-0799 ELEC IF_2 영역 4 task orphan) — Manager force-close 직접 처리 필요. 테스트 영역 2 케이스 (TEST-1111 MECH + ELEC). Sprint 41-D 이전 영역 4 S/N (GBWS-6979/6980/7087/7088 — 본 결함 무관 기존 영역). **POST-REVIEW**: BACKLOG `POST-REVIEW-HOTFIX-SPRINT41D-SQL-COLUMN-FIX-20260514` 등록 (7일, deadline 2026-05-21) + pytest integration TC 영역 별 sprint P2 (TC-FF-01p/01q/01r). **선행 의존성**: v2.15.3 prod 배포 완료. **회귀 위험**: 0 (SELECT 영역 정정 + DRY 정정 — 다른 영역 변경 0). **추정**: 30분 (정정 완료) + pytest integration TC 영역 별 sprint P2 (45분). **Rollback**: git revert 1 commit. **연관**: HOTFIX-SPRINT41D-AUTO-FINALIZE-NOT-BLOCKED-20260514 (v2.15.2) + Sprint 41-D 시리즈 (v2.15.0~v2.15.3) + ADR-029 후속 사례 #21~#23 (pytest mock 한계 + Codex schema cross-check 누락 + 사용자 검증 답변 영역 운영 데이터 SQL 권고). **검증 방법** (사용자 측): (1) Railway 자동 재배포 후 Sentry 영역 `column td.last_started_at does not exist` 메시지 영역 0건 확인 (2) 미래 새 trigger 영역 정상 작동 검증 — 신규 S/N 영역 TANK_DOCKING / IF_2 start 후 자동 close 확인 (3) GPWS-0799 영역 Manager force-close 직접 처리 (기존 orphan 영역, v2.15.4 영역 외). 설계 상세: CHANGELOG.md [2.15.4] entry + AGENT_TEAM_LAUNCH.md HOTFIX-SPRINT41D-AUTO-FINALIZE-RANGE-EXTENSION-20260514 § Catch 영역 정합 |
| HOTFIX-SPRINT41D-AUTO-FINALIZE-NOT-BLOCKED-20260514 | Sprint 41-D BE 후속 hotfix — `task_service.py` L363-369 First Final 차단 분기 결함 fix (logger.info only → 즉시 return) (cowork 실수 #20, Sprint 41-D 구현 단계 catch 누락) | ✅ **COMPLETED** (v2.15.2, 2026-05-14) — pytest 26/26 GREEN / 후속 v2.15.3 (Issue A 차단 범위 확장) 진행 완료 | **BE only — `backend/app/services/task_service.py` complete_work() L353-378 정정 + `tests/backend/test_relay_first_final.py` 신규 3 TC (TC-FF-01b/01c/01d)**. 트리거: v2.15.0 + v2.15.1 배포 후에도 사용자 측 운영 영역 "내 작업만 종료 → task close 발생" 사고 재현. Root cause: 설계서 (AGENT_TEAM_LAUNCH.md Sprint 41-D L478-499) 즉시 return 명시했으나 구현 단계에서 logger.info 만으로 단순화 → `finalize` 변수 그대로 False 유지 → L408 auto_finalize 분기 진입 → `_all_workers_completed=True` (한 명 참여) 시 `auto_finalized=True` 트리거 → **task close 발생 (의도와 반대)**. pytest 23/23 GREEN 이었으나 TC-FF-01~05 명시 영역이 실제로는 constants/phase map 검증만 작성되어 본 결함 catch 누락. **변경 (~50 LoC)**: (1) L363-378 즉시 return 추가 + work_completion_log 기록 + pause 자동 resume 흡수 (2) `first_final_blocked=True` 응답 플래그 신규 (FE 인지용) (3) pytest 신규 3 TC — TC-FF-01b (ELEC IF_2 + 한 명 참여 + `_all_workers_completed=True` mock 시 즉시 return + `mock_all_done.assert_not_called()` 회귀 차단) + TC-FF-01c (MECH TANK_DOCKING 동일 검증) + TC-FF-01d (Single Final TMS PRESSURE_TEST 정상 종료 회귀 방지). **POST-REVIEW**: BACKLOG `POST-REVIEW-HOTFIX-SPRINT41D-AUTO-FINALIZE-NOT-BLOCKED-20260514` 등록 (7일, deadline 2026-05-21) + ADR 후보 "pytest TC 작성 시 constants 검증 vs 실제 동작 검증 분리 표준". **선행 의존성 0**. **회귀 위험**: 0 (FE 변경 0, Single Final 영역 보존, 멀티 worker 영역 정합 유지). **추정**: 30분 (정정 완료). **Rollback**: git revert 1 commit. **연관**: SPRINT-41-D-RELAY-FIRST-FINAL-LOGIC-20260513 / v2.15.0 / v2.15.1 / cowork 실수 #20 — Sprint 41-D 영역 구현 단계 catch 누락 영역 (ADR-029 Tier 2 영역 검증 누락 trail). **검증 방법**: pytest 신규 3 TC + 기존 23 TC = 26/26 PASS 예상 → Railway 자동 재배포 → 운영 영역 사용자 측 재현 (TEST-1111 사례 → ELEC IF_2 한 명 참여 "내 작업만 종료" → task open 유지 확인). 설계 상세: CHANGELOG.md [2.15.2] entry + AGENT_TEAM_LAUNCH.md Sprint 41-D L353-378 영역 정정 trail |
| SPRINT-41-D-RELAY-FIRST-FINAL-LOGIC-20260513 | Sprint 41-D — Relay First Final Logic + 자동 정리 트리거 (FIRST/SECOND/SINGLE Final 분리, ELEC IF_2+INSPECTION AND 조건, attendance check_out + 17:00 fallback) | ✅ **COMPLETED** (v2.15.0, 2026-05-14) — BE only 5 파일 +650 LOC / Codex 라운드 1+2 정정 12건 (M-1 함수분리 + M-2 wire-through + A-1/A-3/A-5/A-8 + N-2 + 일관성 표) / pytest 38/38 GREEN (신규 23 unit + 회귀 work_api 15) / migration 056 (duration_source NULLABLE + CHECK 4 enum) / 회귀 위험 0 (FE 변경 0 + Sprint 41-B 호환 + Sprint 57 보존 + M-3 진단 0건) | **BE only — `backend/app/services/task_service.py` + 신규 `duration_calculator.py` + `checklist_service.py` + `task_detail.py` + migration 1건 + pytest 신규 15 TC**. 트리거: Sprint 41 (2026-03-30) finalize 분리 + Sprint 55 (3-B, 2026-04-07) auto_finalize 도입 후 → "내 작업만 종료" 의도 무력화 → Manager Rollback 요청 폭증 (2026-04-22 O/N 6588 GBWS-6978/6979/6980 UTIL_LINE_2 — 이영식/서명환 사례). UX-SPRINT55-FINALIZE-DIALOG-WARNING (다이얼로그 1.5h 영역) = 3 선택지 모두 같은 영역 갇힘 → 폐기. **사용자 결정 (2026-05-13)**: Q1 (a) attendance check_out 우선 / Q2 trigger 발생일 17:00 fallback / Q3 14% 야근 손실 = IQR 통계 보강 / Q4 pause_minutes Sprint 9 로직 활용 / Q5 (c) MIN(check_out, trigger_time). **솔루션**: ① FIRST_FINAL_TASK_IDS (MECH TANK_DOCKING / ELEC IF_2) — start 시점 트리거로 전 phase 미완료 + pause 자동 close ② SECOND_FINAL_TASK_IDS (MECH SELF_INSPECTION / ELEC IF_2 + INSPECTION AND) — complete 시점 카테고리 미완료 자동 close ③ SINGLE_FINAL_TASK_IDS (TMS/PI/QI/SI 변경 없음) ④ First Final auto_finalize 차단 (한 명 참여여도 task open 유지) ⑤ `_calculate_close_at()` 신규 (attendance + 17:00 fallback + MIN) ⑥ `_calculate_auto_close_duration()` (pause_minutes 차감) ⑦ `auto_close_relay_task()` 확장 (closed_by + trigger_task_id + duration_source 인자) ⑧ `check_elec_completion()` AND 조건 변경 ⑨ migration: `duration_source` 컬럼 추가 (enum 4종: WORKER_COMPLETION / ATTENDANCE_OUT / FALLBACK_TRIGGER_DATE_17 / INVALID_WARNING) ⑩ close_reason prefix `AUTO_CLOSED_BY_{FIRST\|SECOND}_FINAL_TRIGGER:{trigger_task_id}` (Q2-c). **선행 의존성**: 없음 (Sprint 64-BE v2 / Sprint 66-BE-FOLLOWUP 와 병렬 가능). **회귀 위험 0**: 기존 Sprint 41 finalize 분리 + Sprint 41-B auto_close_relay_task 함수 + Sprint 55 auto-finalize 로직 + Sprint 57 INSPECTION freeroll 모두 그대로 유지. FE Flutter 변경 0 (다이얼로그 + 3 선택지 그대로). DRAGON/GALLANT/SWS (tank_in_mech=TRUE) 모델은 TANK_DOCKING is_applicable=FALSE 자동 흡수. **추정**: 12h (task_service 1.5h + start_work First Close 1.5h + complete_work 차단+Second Close 1h + duration_calculator 신규 2.5h + check_elec_completion 1h + auto_close 확장 30분 + migration 30분 + pytest 15 TC 2.5h + Codex 라운드 1 1h). **Pre-deploy Gate**: pytest 15 TC GREEN + baseline 측정 SQL 실행 + Sentry 새 ERROR 0건. **post-deploy 4주 후**: Manager Rollback 비율 50%+ 감소 검증. **Rollback**: git revert 1 commit (회귀 0 — duration_source 컬럼은 nullable additive). **연관**: Sprint 41/41-A/41-B (v2.3.0) trail / Sprint 55 (v2.7.0) / UX-SPRINT55-FINALIZE-DIALOG-WARNING (OBSOLETE 처리) / FEAT-SPRINT55-REACTIVATE-HYBRID-ROLE (별 Sprint, manager+worker hybrid) / FEAT-RELAY-FIRST-FINAL-ANALYTICS-DASHBOARD-20260513 (별 sprint, 4주 baseline 후) / ADR-029 Tier 2. 설계 상세: AGENT_TEAM_LAUNCH.md § Sprint 41-D (Sprint 41 trail cross-reference + 동작 매트릭스 + pytest 15 TC 매트릭스 + close_at 알고리즘 포함) |
| FEAT-RELAY-FIRST-FINAL-ANALYTICS-DASHBOARD-20260513 | 협력사 평가지수 KPI 분석 대시보드 — Sprint 41-D 데이터 source 활용 (자동 close 발생률 / task 종료 누락률 / 평균 duration IQR 통계 / duration_source 4종 분포) | 🟢 OPEN (P2, 별 sprint, Sprint 41-D 배포 후 4주 baseline 축적 후 진행) | **VIEW 트랙 — AXIS-VIEW 별 sprint 신설 권장 (FE 대시보드 화면 2종 + BE 통계 endpoint 1~2개)**. 트리거: Sprint 41-D 가 자동 close 트리거 + duration_source 컬럼 + close_reason prefix 데이터 source 자동 채워줌. 4주 누적 후 baseline 산출 → 협력사 평가지수 KPI 신설 가능. **화면 영역**: ① Manager 대시보드 (오늘 자동 마감 카드 + 자동/수동 close 비율 비교) ② 협력사별 자동 마감 발생률 (BAT vs FNI 등) ③ task 별 종료 누락률 (판넬/배선 등) ④ duration_validator warning 비율 + IQR 통계 (Q3 사용자 결정 정합). **인사이트**: Manager Rollback 비율 감소 효과 측정 + 작업자 종료 누락 패턴 식별 + 협력사 운영 영역 개선 + 향후 APS 도입 시 baseline 학습 데이터. **선행 의존성**: Sprint 41-D prod 배포 완료 + 4주 데이터 축적 (2026-06-08+ 시점 진행 가능). **연관**: Sprint 41-D / VIEW-S35-001 협력사 평가지수 대시보드 (G-AXIS_BACKLOG.md). 설계 상세: AGENT_TEAM_LAUNCH.md § Sprint 41-D § "다음 응용 포인트" 영역 + 사용자 측 5-11 catch 통계 분리 view 샘플 |
| UX-SPRINT55-FINALIZE-DIALOG-WARNING | "내 작업만 종료" 마지막 참여자 경고 다이얼로그 (2026-04-22 등록, **1차 보완**) | ❌ **OBSOLETE — 2026-05-11 Sprint 41-D 로 대체 폐기** | **폐기 사유 (2026-05-11)**: 본 entry 가 catch 한 root cause (Sprint 55 auto_finalize) 는 정확했으나, 1.5h 다이얼로그 솔루션 자체가 운영 영역에서 실효성 부족. 작업자가 다이얼로그 보고 선택할 수 있는 3 옵션 (내 작업 완료 / 일시정지 / 완전 종료) 모두 같은 영역 갇힘: (a) 내 작업 완료 = auto_finalize 트리거로 close, (b) 일시정지 = 영원히 멈춤 (자동 정리 없음), (c) 완전 종료 = close. 다이얼로그 정보 제공만으로는 작업자에게 안전한 선택지 자체가 없음. **대체**: Sprint 41-D `SPRINT-41-D-RELAY-FIRST-FINAL-LOGIC-20260513` — 시스템 강제 보호 (First Final auto_finalize 차단) + 자동 정리 (First Close 트리거). 본 entry 의 catch 사례 (O/N 6588 GBWS-6978/6979/6980 — 이영식/서명환) 는 Sprint 41-D 가 직접 해결. **이전 본문 (참조용)**: FE only — `frontend/lib/screens/task/task_detail_screen.dart` `_showCompleteDialog()` 확장. 현장 호소: "내 작업만 종료 눌렀는데 task 가 닫혀서 재참여 불가" (2026-04-22 O/N 6588 GBWS-6978/6979/6980 UTIL_LINE_2 — 이영식/서명환 사례). **원인 확정**: Sprint 55 (3-B) `auto_finalize` — `not finalize` 모드에서도 `_all_workers_completed(task.id)` True 시 task 자동 종료. 버그 아니고 설계대로 동작(progress 실시간 정확도 목적). 다만 "내 작업만 종료" 문구와 실제 동작 괴리 → UX 혼란. **해결**: 다이얼로그 진입 시 현재 참여자의 completion 상태 pre-check → 본인이 partial close 하면 auto-finalize 발동 예정인 경우 **2차 확인 문구** 추가: "⚠️ 현재 다른 참여자 전원이 종료 상태입니다. 당신이 마지막 참여자이므로 이 버튼을 누르면 task 가 자동 종료됩니다. (추후 재개 필요 시 관리자에게 재활성화 요청)". **BE 변경 필요**: `/api/app/tasks/<sn>` 또는 `/api/app/task/<id>` 응답에 `is_last_active_worker: bool` 플래그 추가 (work_start_log 찍힌 전원이 completion_log 있고 본인만 active 상태인지 판정). 작업 소요: FE 30분 + BE 30분 + 테스트 15분 ≈ 1.5h. **오늘 이슈의 80% 를 해소하는 최소 비용 조치**. 관련: `AXIS-OPS/BACKLOG.md` UX-SPRINT55-FINALIZE-DIALOG-WARNING + `backend/app/services/task_service.py` L292-304 auto_finalize 분기 |
| FEAT-SPRINT55-REACTIVATE-HYBRID-ROLE | manager+worker hybrid role 의 PWA 내 재활성화 버튼 (2026-04-22 등록) | 🟡 OPEN (P2, 다음 Sprint) | **FE + BE 연계 — 이영식(manager+worker hybrid) 사용 경험 최적화**. 현재: 이영식(manager) 이 완료된 task 를 다시 열려면 AXIS-VIEW 콘솔 로그인 → task 검색 → 작업재활성화 버튼 클릭 (5분 마찰). **제안**: PWA task 상세 화면 `_buildCompletedBadge()` 옆에 **role 조건부 [재활성화] 버튼** 노출. 조건: `worker.role IN ('MANAGER', 'MECH+MANAGER', 'ELEC+MANAGER', ...)` 인 경우만. 1-tap → 기존 VIEW 재활성화 API (`/admin/tasks/<id>/reactivate` 등) 호출 + audit log 기록 (→ `OBSERV-ADMIN-ACTION-AUDIT` 연계). 버튼 UX: 확인 모달 필수 ("이 작업을 재활성화하시겠습니까? 완료 상태가 해제됩니다."). **비용**: FE 버튼 1개 + 조건부 노출 로직 + BE 엔드포인트 재사용 (신규 0). 작업 소요 반나절. **이득**: 오늘처럼 manager 가 hybrid 로 있는 케이스에서 VIEW 왕복 제거. BE 재활성화 API 가 이미 있는지 먼저 확인 필요 (없으면 별도 Sprint). 관련: `AXIS-OPS/BACKLOG.md` FEAT-SPRINT55-REACTIVATE-HYBRID-ROLE |
| FEAT-SPRINT55-REACTIVATE-REQUEST-FLOW | worker → manager 재활성화 요청 flow (2026-04-22 등록, **2차 보완**) | 🟢 OPEN (P3, 중기) | **BE + FE + VIEW 3-way 구현 — 현장 worker-manager 협업 완전체**. 시나리오: 일반 worker(non-manager)가 완료된 task 에 재참여 필요 → 현재 플로우 "카톡으로 manager 에게 요청 → manager VIEW 로그인 → 수동 재활성화" (마찰 큼). **신규 flow**: (1) PWA 완료 task 카드 → [재개 요청] 버튼 → 사유 입력 모달 → POST `/api/app/task/<id>/reactivate-request` (2) VIEW 상단 알림 배지 + AXIS-VIEW 전용 요청 목록 페이지 (3) manager 1-tap 승인 → 기존 재활성화 API 내부 호출 + 요청자에게 push 알림 (4) 승인 거절 시 사유 회신. **새 테이블**: `task_reactivate_requests (id, task_detail_id, requester_id, reason, status, approver_id, approved_at, rejected_reason, created_at)`. **새 엔드포인트 3개**: POST 요청 생성 / GET 대기 목록 (manager only) / PATCH 승인·거절. **FE**: PWA 재개요청 버튼 + 모달 + 내 요청 상태 조회. VIEW: 요청 목록 페이지 + 알림 widget. **작업 소요**: 1~1.5일 full-stack. **전제**: `FEAT-SPRINT55-REACTIVATE-HYBRID-ROLE` 먼저 배포해서 manager-hybrid 케이스 해결 후 진행 (non-hybrid worker 남은 케이스 대응). `OBSERV-ADMIN-ACTION-AUDIT` 와 통합 (요청/승인 모두 audit log 기록). 관련: `AXIS-OPS/BACKLOG.md` FEAT-SPRINT55-REACTIVATE-REQUEST-FLOW |
| DOC-AXIS-VIEW-REACTIVATE-BUTTON | AXIS-VIEW "작업재활성화" 버튼 존재·영향 범위 문서화 (2026-04-22 등록) | 🟢 OPEN (P3, 30분) | **문서 정리 only**. 2026-04-22 UTIL_LINE_2 조사 중 Q1 의 `first_worker_id=NULL` + started_at 갱신 이력을 미스터리로 접근했다가 Twin파파가 "VIEW 에 재활성화 버튼 존재" 확인해 해소. 다음 번 비슷한 조사 시간 낭비 방지용 기록. **수정 대상**: `AXIS-OPS/memory.md` 상단 "📍 주요 관리 기능" 섹션 신설 or `AXIS-OPS/CLAUDE.md` 관리자 기능 블록. **내용**: (1) AXIS-VIEW 에 task 재활성화 버튼 존재 (위치·권한·호출 API 명시) (2) 재활성화 시 DB 상태 변화: `started_at=NULL, completed_at=NULL, worker_id=NULL, total_pause_minutes 잔존 가능` (3) 기존 start_log/completion_log 는 보존 — 재활성화 이후 새 시작 시 새 row 추가 (4) 재활성화 가 의도된 기능임 (우회가 아님) (5) 재활성화 이력은 현재 audit log 부재 → `OBSERV-ADMIN-ACTION-AUDIT` 연계. 예상 소요 30분. 관련: `AXIS-OPS/BACKLOG.md` DOC-AXIS-VIEW-REACTIVATE-BUTTON |
| OBSERV-ADMIN-ACTION-AUDIT | 관리자 액션 audit log 테이블 도입 (2026-04-22 등록) | 🟡 OPEN (P2, 독립 Sprint) | **BE 신규 인프라 — 관찰성 gap 해소**. 2026-04-22 UTIL_LINE_2 조사 중 Q7 `SELECT * FROM admin_audit_log` 실행 시 `relation "admin_audit_log" does not exist` (42P01) 에러로 확인: **AXIS-VIEW 재활성화 등 admin destructive/corrective 액션에 audit 기록 인프라 부재**. 누가 언제 어떤 task 를 재활성화했는지 DB 추적 불가. **스키마 초안**: `CREATE TABLE admin_audit_log (id BIGSERIAL PK, actor_user_id INT NOT NULL, actor_email TEXT, action TEXT NOT NULL, target_table TEXT NOT NULL, target_id BIGINT NOT NULL, before_state JSONB, after_state JSONB, reason TEXT, ip_address INET, user_agent TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())` + index `(target_table, target_id)` / `(actor_user_id, created_at DESC)`. **적용 범위**: (1) task 재활성화 (2) task 강제 종료 (HOTFIX-04 force-close) (3) worker 강제 로그아웃 (4) pause 강제 해제 (5) admin_settings 변경 (6) role 승격/강등 etc. **연동 방식**: Flask `before_request` + `after_request` middleware 에서 자동 snapshot 기록 (해당 blueprint 범위: `/admin/*` mutation 라우트). 수동 호출 불필요. **수반 이득**: (i) 향후 데이터 미스터리 조사 시간 5~10분 → 30초 (ii) 다중 관리자 환경 책임 추적 (compliance) (iii) Sprint 45 INFRA-1 migration runner 관찰성 부재와 동일 유형의 blind spot 해소. **작업 소요**: migration 1개 + middleware ~30~50줄 + 기존 admin 라우트 점진 적용 → 초기 구현 2h + 전 admin 라우트 적용 추가 2h. **관련 BACKLOG**: `FEAT-SPRINT55-REACTIVATE-HYBRID-ROLE` / `FEAT-SPRINT55-REACTIVATE-REQUEST-FLOW` 배포 전 선행 권고. 오늘 조사 근거: `AXIS-OPS/BACKLOG.md` OBSERV-ADMIN-ACTION-AUDIT |
| FEAT-MODEL-O3-DESTRUCTOR-TASK-SEED-20260515 | 신규 모델 `O3 Destructor` — task seed 자체가 표준(MECH 7 + ELEC 6 + TMS 2)과 다름. MECH 작업 없음 + ELEC 축소 (판넬/IF_2/자주검사 수준) + TMS 없음 | 🟡 OPEN (P2, **추후 진행 — 사용자 5-15 결정**) | **BE — `model_config` INSERT + `task_seed.py` O3 전용 분기 (단순 model_config 등록으로 불충분)**. 트리거: 2026-05-15 05:06 Railway logs — `Model config not found for model='O3 Destructor'`. **사용자 catch (5-15)**: O3 Destructor 는 task seed 자체가 표준 15개(MECH 7 + ELEC 6 + TMS 2)와 다른 모델 — **MECH 작업 없음 / ELEC 도 판넬(PANEL_WORK) + IF_2 + 자주검사(INSPECTION) 정도만 / TMS 없음**. **현 상태 영향**: `model_config` 미등록 → task_seed default fallback (has_docking/is_tms/tank_in_mech 전부 False) → 표준 ELEC 6 task 가 그대로 생성됨 (O3 실제는 3개 수준) → 작업자 화면 영역 불필요 task 표시 가능. MECH 는 default 영역 자주검사만 활성이라 부분 정합. **필요 작업 (단순 INSERT 아님)**: ① `model_config` 영역 O3 prefix 등록 ② `task_seed.py` 영역 O3 전용 task 템플릿 분기 — MECH skip + ELEC 축소 seed (판넬/IF_2/자주검사) ③ pytest TC (O3 모델 task seed 검증). **추정**: ~2~3h (task_seed 분기 + 검증). **회귀 위험**: 낮음 (O3 전용 분기 = 기존 모델 영향 0). **선행**: O3 Destructor 정확한 task 구성 확정 (Twin파파 양식 공유). **연관**: CLAUDE.md Task Seed 데이터 (MECH 7 + ELEC 6 + TMS 2 표준) + model_config 모델별 분기 표 + task_seed.py. **현재 운영 영향**: O3 제품 QR 스캔 시 표준 task 생성 (불필요 ELEC task 포함) — 사용자 측 추후 진행 결정, 시급도 낮음. |
| FIX-DB-POOL-MAX-SIZE-20260427 | DB Connection Pool 사이즈 보정 (MAX=20→30, MIN=5 유지, env 변경 only, 2026-04-27 등록) | ✅ **COMPLETED** (V4.1 영구 종결, 2026-05-15) — V4.1 T+8d 점검 통과: 5-11 마지막 자가 회복 사고 이후 5-15 까지 신규 사고 0건 (Pool exhausted 0 / 자가 회복 발화 0 / Sentry 0). 시나리오 A 이상적. Using direct connection 11건 = 의도된 안전망 (새벽 idle, v2.10.13 강등). Phase B task close. | **Railway env 1개 변경 + 코드 변경 0**. 트리거: 4-25 토 새벽 (UTC 22:29 / KST 07:29) Pool exhausted 다발 사례 + 사용자 ≥120명 / peak 07:30~09:00, 16:30~17:00 출근 burst 패턴 확정. **4 라운드 advisory review (Codex 1차 + Claude Code 2차 + Codex 3차 + Twin파파 fact-check 4차) 로 약점 12건 정정 후 최종 산정**. ⚠️ 라운드 4 결정적 정정: 기존 prod env 가 **이미 MIN=5/MAX=20 운영 중** (코드 default 1/10 가정 X). 이번 변경은 MAX 만 20→30. **per-worker 독립 pool 구조** (init_pool() in create_app() — gunicorn -w 2 fork 시 각 worker 독립) → Worker A (scheduler owner) 15 conn + Worker B (HTTP only) 10 conn 필요 → MAX=30 채택 (per-worker × 2 = 총 60, Postgres 100 중 62% 점유). **결정적 데이터 (Q-B)**: 2026-04-21 화 출근 burst 측정 — peak 31 동시 in-flight, 21 동시 17회 빈번. **MAX=20 환경 측정 결과** = peak 31 시 worker당 ~16 → fallback 1건/peak (라운드 4 정정, 라운드 3 의 ~100건/일 추정 무효), MAX=30 이면 fallback 0. **MIN=5 유지**: 이미 운영 중이었으므로 cold-start 효과는 기존부터 적용된 상태. max_age=300s 5분 후 lazy 재생성 race 로 일시적 MIN 미달 가능 — 별건 OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP (P3 격하) 에서 5분 간격 SELECT 1 cron 으로 보강. **미래 dimensioning**: MAX=30 = 미래 2x (62 in-flight) 까지 안전, 사용자 600명 (5x) 도달 시 MAX=70~80 + Postgres tier 상향 / PgBouncer 도입 검토 필수. **Phase A** (✅ 2026-04-27 KST 완료): Railway env `DB_POOL_MAX=20→30` 변경, MIN=5 유지 → 자동 재배포 ~1분 → logs 에서 `Connection pool initialized: min=5, max=30` 확인. **Phase B** (3일 관찰 중, 화/수/목): Pool exhausted grep + Q-B 재측정 (off-peak 12:00 권장, O(N²) 부담 회피) + pg_stat_activity 정밀 SQL (pid+client_addr 로 worker A/B 분리). **Phase C** (D+3 이후 조건부): 0 fallback 종료 / 1~5건 시 40 ↑ / 10+건 시 50 ↑ + leak audit. **사용자 영향**: 7일 Q5 결과 slow_req≥5s = 0건 (사용자 체감 0). **롤백**: env 1개 복원 (30→20) → 자동 재배포 ~1분, 코드 영향 0. 설계 상세: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` FIX-DB-POOL-MAX-SIZE-20260427 섹션 (약점 trail 12건 + 4라운드 검증 기록 포함) |
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
| OBSERV-PIN-FLAG-DEPLOY-CORRELATION-RE-CHECK-20260601 | PIN 재등록 burst ↔ Netlify FE deploy 상관관계 6월 재점검 (5-11 D+14 측정 결과 기반) | 🟡 OPEN (P2, 6월 본격 운영 상태 재점검 영역) | **6월 재점검 sprint — 5월 운영 안정화 시기 종료 후 본격 운영 상태에서 PIN flag 영역 재측정**. 트리거: 2026-05-11 D+14 측정 결과 = pin_status_calls 14일 안정 (backend fallback 활성 ✅) BUT **5-11 PIN 재등록 23건 polynomial spike** (4-30/5-05/5-07/5-08/5-10 1~2건 정상 대비). 23명 모두 5-11 06:54~09:02 KST 출근 burst (FNI/TMS/BAT/P&S/C&A/GST 광범위) + pin_fail_count=0 (storage 손실, lock 영역 X) + 5-11 인증 흔적 0건 (login/pin-login/pin-status 모두 0 → set-pin endpoint 도 access_log 미기록 = silent fail or 다른 영역). **상관관계 가설**: 5-10 evening v2.12.4 Netlify FE deploy → PWA SW 업데이트 → IndexedDB 일괄 손실 → 5-11 morning 출근 burst 시 EmailLoginScreen 빠짐 → 비번 로그인 → PIN 재설정 흐름. **비교 증거**: 5-08 v2.12.3 (BE only, FE 빌드 X) → 5-09 PIN 재등록 0건 ✅. **사용자 결정 (5-11)**: 5월 = 운영 안정화 + 디버깅 + 편의사항 개선 = 잦은 push 지속 영역, storage 손실 trade-off 영역. 6월 본격 운영 상태에서 재점검 진행. **재점검 영역 (6월 1일+)**: (1) 5월 PIN 재등록 일별 추세 측정 (deploy 시점 매핑) (2) deploy 후 D+1 PIN 재등록 burst 패턴 통계 (n=5 이상 sample) (3) backend fallback 우회 cohort 분석 (refresh_token 동시 손실 영역) (4) FE 측 storage 측정 — IndexedDB vs SharedPreferences (LocalStorage) 영역 손실 비교 (5) 사용자 측 인터뷰 (5-11 23명 sample). **결정 영역 (6월 재점검 결과 후)**: (a) FEAT-AUTH-STORAGE-MIGRATION-FULL-20260427 진행 — refresh_token + worker_id + worker_data SharedPrefs 양방향 sync. (b) UX-LOGIN-FALLBACK-PIN-RESET-LINK-20260427 진행 — EmailLogin 화면 PIN 재등록/비번 재설정 link. (c) 또는 backend `/auth/pin-status` 흐름 재설계 (storage 의존도 0). **선행**: 5월 end 도달 (잦은 push 시기 종료). **소요**: 측정 SQL 30분 + 분석 1h + 결정 sprint 분기 1h = 2~3h. **연관 측정 데이터**: handoff.md 2026-05-11 trail (`Q1~Q4 측정 결과` + Deploy ↔ PIN 재등록 상관관계 분석). 최초 등록: 2026-05-11 |
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
| SPRINT-65-BE-MECH-REPORT-BRANCH-20260505 | Sprint 65-BE — MECH 체크리스트 성적서 분기 hotfix (qr_doc_id 명시 + Phase 1/2 분리, ELEC 패턴 차용, ~25 LoC, Codex 1차 P1~P5 전건 반영) | ✅ COMPLETED (v2.11.7, 2026-05-06, BE only ~25 LoC + pytest 3 TC / 22/22 PASS, ADR-026 신설) | **BE only — `backend/app/services/checklist_service.py` 단일 파일 ~25 LoC**. 트리거: 2026-05-05 Twin파파 운영 검증 — VIEW `/partner/report` 페이지 "기구" 섹션 input_value '—' 표시 (모바일 앱 입력 정상 + DB record 정상 but VIEW 미표시). **Root cause**: BE `else` 분기에서 `qr_doc_id=''` (default) 로 SELECT → DB row (`DOC_TEST-1111`) 매칭 0건 → LEFT JOIN cr 컬럼 NULL → VIEW '—' 표시. 운영 DB 검증 결과 (master_id IN 149/158/163/176): record 정상 (input_value='1', '11' 등). **변경**: (1) `else` → `elif cat == 'MECH':` 명시 분기 + ELEC 패턴 (Phase 1/2 분리: '1차 입력' / '2차 검수') (2) `_normalize_qr_doc_id(serial_number)` 명시 호출 = `'DOC_<sn>'` (모바일 앱 정합) (3) `phase1_applicable=False` 항목 자동 제외 (Sprint 60-BE 컬럼 기반) (4) DUAL INLET L/R 분리 TODO 주석 명시 (운영 데이터 0건, 향후 hotfix 예약) (5) 기존 `else` 보존 → PI/QI/SI 잠재 신규 카테고리 fallback (ADR-026 표준 검토 후 명시 분기 권장). **VIEW FE 정합 (P1 prerequisite 통과)**: ChecklistReportView L177-178 categories.map entry 개수 무관 + L202-203 `cat.phase_label` 표시 로직 이미 구현 + types/checklist.ts L109-113 phase/phase_label optional 타입 + ELEC baseline 운영 검증 → VIEW FE 변경 0건, BE 단독 hotfix 안전 + atomic deploy 불필요. **pytest 신규 TC 3건**: TC-65-01 qr_doc_id 매칭 + input_value 반환 / TC-65-02 phase split + phase_label / TC-65-03 TM 회귀 0. **결과**: 22/22 PASS (sprint54 GREEN, 회귀 0). **memory.md ADR-026 신설** — 신규 체크리스트 카테고리 phase split 표준 (ELEC/MECH/TM/PI/QI/SI 결정 매트릭스). **선행 의존성**: 0 (BE 단독, Sprint 39 + Sprint 63-BE + Sprint 60-BE 배포 완료 전제). **사용자 영향**: VIEW 성적서 MECH 섹션 input_value 정상 표시 + Phase 1/2 분리 노출 (UX 개선). **회귀 위험**: 0 (BE additive 분기, ELEC/TM 무영향). **Rollback**: git revert 1 commit → v2.11.6 복귀. **후속 BACKLOG**: OPS-CHECKLIST-PHASE-SPLIT-REFACTOR-01 (P3 LOW, ELEC/MECH 헬퍼 함수 추출, ~1h) + FIX-MECH-DUAL-INLET-L-R-SEPARATION (LOW, INLET L/R record 발생 시). 설계 상세: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` Sprint 65-BE 섹션 (Codex 1차 P1~P5 전건 반영) + `memory.md` ADR-026 |
| OPS-CHECKLIST-PHASE-SPLIT-REFACTOR-01 | ELEC + MECH (+ 향후 PI/QI/SI) 의 phase 분리 로직 헬퍼 함수 추출 — 코드 중복 제거 (Sprint 65-BE 후속 P3) | 🟡 OPEN (P3 LOW, ~1h) | **BE only — `backend/app/services/checklist_service.py` `_get_phase_split_categories()` 헬퍼 함수 신설**. 트리거: Sprint 65-BE 적용 후 ELEC L438-461 + MECH L484~ 분기가 phase_label 텍스트 + qr_doc_id 명시 여부만 차이로 거의 1:1 중복. 향후 PI/QI/SI 신규 카테고리 도입 시 또 중복 추가 위험. **변경**: `_get_phase_split_categories(cur, sn, category, product_code, scope, phase_labels: List[Tuple[int, str]], qr_doc_id: Optional[str] = None) -> List[Dict]` 헬퍼 + 기존 ELEC/MECH 분기를 `categories.extend(_get_phase_split_categories(...))` 1줄로 통합. **회귀 위험**: 낮음 (refactor only, 동작 100% 동일). **pytest**: 기존 TC 22/22 GREEN 유지로 검증 충분. **선행 의존성**: Sprint 65-BE COMPLETED. **트리거 시점**: 신규 카테고리 (PI/QI/SI) 도입 또는 코드 정리 슬롯 확보 시. 추정 1h (헬퍼 + 기존 분기 통합 + pytest 회귀). 설계 상세: AGENT_TEAM_LAUNCH.md Sprint 65-BE 섹션 P3 |
| FIX-MECH-DUAL-INLET-L-R-SEPARATION-FUTURE | DUAL DRAGON 모델의 INLET S/N L/R 분리 record 발생 시 hotfix (Sprint 65-BE 후속 P5 TODO) | 🟡 OPEN (LOW, 트리거 시) | **BE only — `backend/app/services/checklist_service.py` MECH 분기에 DUAL qr_doc_ids 배열 확장**. 트리거: 운영에서 INLET S/N L/R 별도 입력 시 또는 DRAGON DUAL INLET 분리 record 발생 시. 현재 5-06 시점 운영 데이터 0건 (모든 record SINGLE-style 'DOC_<sn>'). **변경 (트리거 시)**: TM 패턴 (`L463-482`) 차용 — `qr_doc_ids = [(_normalize_qr_doc_id(sn, 'L'), 'L'), (_normalize_qr_doc_id(sn, 'R'), 'R'), ...]` + 각 qr_doc_id 별 Phase 1/2 분리 호출. **선행 의존성**: Sprint 65-BE COMPLETED + 운영 데이터에 INLET L/R record 발생. **추정**: ~30분 (TM 패턴 차용). 설계 상세: checklist_service.py MECH 분기 TODO 주석 + AGENT_TEAM_LAUNCH.md Sprint 65-BE 섹션 P5 |
| OBSERV-WORKER-CONN-LOSS-20260507 | gunicorn 2 worker 기준 OPS conn 5개만 보임 (예상 10) — 5-09 V4.4 worker 수 확정 후 시나리오 분기 | 🟡 OPEN (조건부, 5-09 후 결정) | **OPS T+24h 측정 (5-07) 발견 — Procfile `gunicorn -w 2 --worker-class gthread --threads 8` 정합 검증 필요**. 트리거: 2026-05-07 ~12:44 KST V2.2/V2.3 측정 결과 — OPS application_name='' conn 5개, oldest 4h 12m alive (keepalive 정상), Procfile 기준 2 worker × MIN=5 = 10 예상 대비 50% 누락. **3 가능 원인**: (1) Railway 가 1 worker 만 실행 (Hobby tier 메모리 제약 또는 auto-scaling) (2) 2 worker 였지만 1 worker conn 5개 dead → warmup 자가 회복 trigger 안 걸림 (3 cycles 0/0 조건 미달) (3) gunicorn `-w 2` Railway env override 또는 OOM 으로 worker 1개 죽음. **현재 영향 0** — 살아있는 5 conn 모두 4h+ alive, max_idle_sec 14s, idle in tx 0건, Sentry 0 events → 정상 운영 중. **5-09 V4.4 진단 SQL** (DB_POOL_VERIFICATION_QUERIES_20260427.md 참조): pid 분포 + Railway boot logs worker pid 수 확인. **시나리오 분기**: (A) **1 worker 확정**: MIN=5 보장 100% — 본 sprint 종결 (Procfile -w 2 vs 실제 1 worker 차이는 별 INFRA-RAILWAY-WORKER-COUNT-AUDIT 로 follow-up) (B) **2 worker 확정 + 5 conn loss**: warmup 자가 회복 메커니즘 보완 필요 — `_consecutive_zero_warmup` 임계값 (3 cycles=15분) 너무 길어서 부분 loss 무감지 → 임계값 낮추기 또는 부분 loss 검출 로직 추가. **선행 의존성**: 5-09 V4.4 측정 결과. **추정** (시나리오별): A = 30분 (문서 정리만) / B = 2-4h (코드 수정 + pytest + Codex review). **회귀 위험**: B 시나리오 시 임계값 변경으로 false positive 가능성 검토 필요. 설계 상세: `DB_POOL_VERIFICATION_QUERIES_20260427.md` V2.3 결과 + V4.4 신규 query |
| FIX-DB-POOL-SELF-RECOVERY-20260504 | DB Pool 자가 회복 메커니즘 — psycopg2 keepalive 활성화 + 0/0 conn warmed 연속 감지 시 init_pool() 재호출 + WATCHDOG 확장 (4-29 23:31 + 5-04 11:38 KST 5일 주기 사고 차단) | ✅ COMPLETED (v2.11.6, 2026-05-06, BE only ~30 LOC + pytest 4 TC / 8/8 PASS, ADR-025 신설 / staging 1h 검증 + T+1주 재발 시점 효과 정량 검증 plan) | **BE only — `backend/app/db_pool.py` 단일 파일 ~30 LOC**. 트리거: 2026-05-04 KST 11:38~12:32 사고 (4-29 23:31 KST 사고 5일 주기 재발). 사고 timeline: warmup 정상 (10:38~11:38 5/5 1h) → KST 11:43:35 5/5→2/2 첫 degrade → 11:48:35 0/0 시작 → 40분 0/0 지속 (자가 회복 X) → 12:32:50 Restart 후 5/5 회복. **2단계 root cause 분석 결과**: (1단계 트리거) Railway network proxy idle TCP disconnect — Postgres 측 idle 정책 모두 0 (안 끊음) + tcp_keepalives_idle=7200초 (2시간) + **client psycopg2 keepalive OFF** (Sprint 30-B Railway TCP_OVERWINDOW 충돌 회피 정책). Railway proxy 가 idle TCP 끊으면 client 모름 (silent disconnect). (2단계 확산) **ThreadedConnectionPool 자가 회복 부재** — `_used` dict 의 dead conn 5개 정리 메커니즘 없음 → `_pool.getconn()` 시 PoolError exhausted → warmup 의 break → 0/0 conn warmed 8회 연속 (40분) → 새 conn 생성 자체 fail → Restart 외 회복 불가. **WATCHDOG 영역 외**: 기존 WATCHDOG (db_pool.py:267-277) 는 `_pool=None` 만 감지 → 본 사고는 `_pool` object 살아있음 + internal state 만 깨짐 → WATCHDOG 미발화 → Sentry 0 event (사용자 실측). **변경 3건**: (1) `_CONN_KWARGS` 에 keepalive 활성화 — `keepalives=1, keepalives_idle=60, keepalives_interval=10, keepalives_count=3` (60초 idle 후 30초 안 dead 감지, Railway proxy idle 회피) (2) `warmup_pool()` 에 module-level counter `_consecutive_zero_warmup` 추가, 3 cycles (15분) 연속 0/0 시 `close_pool()` + `init_pool()` 재호출 (자가 회복 메커니즘) (3) 변경 2의 logger.error 격상 → LoggingIntegration(event_level=ERROR) 자동 Sentry capture (WATCHDOG 확장, 추가 작업 0). **위험**: Sprint 30-B 의 Railway proxy TCP_OVERWINDOW 충돌 패턴 재발 가능성 — 4-30+ Railway tier 변동으로 해결됐을 가능성 (staging 검증 필수). **Pre-deploy Gate**: (a) staging 환경 1h 운영 후 keepalive 패킷 / TCP_OVERWINDOW WARN 0건 확인 (b) 자가 회복 trigger 강제 시뮬레이션 — 수동 conn close 후 0/0 cycles 발화 → init_pool() 재초기화 검증 (c) WATCHDOG ERROR Sentry capture 검증. **pytest 신규 TC 3개**: test_keepalive_args_passed (psycopg2 connect kwargs 검증) / test_consecutive_zero_warmup_triggers_init_pool (자가 회복) / test_zero_warmup_logger_error_captured (WATCHDOG 확장). **선행 의존성**: 없음 (BE 단독, db_pool.py 단일 파일). **사용자 영향**: 0 (정상 운영 시 변경 무영향, 사고 시 자가 회복 효과). **회귀 위험**: 0 (keepalive 추가 시 Railway proxy 충돌 가능성만 staging 검증 후 해소). **Rollback**: git revert 1 commit. **효과 검증**: 5-09 ± 1d 재발 시점 자가 회복 작동 + 사고 차단 입증. **연관**: OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP-20260427 (warmup cron) ✅ + FIX-DB-POOL-DIRECT-FALLBACK-LOG-LEVEL-20260428 (logger.warning 강등) ✅ + 본 Sprint = 자가 회복 추가. 설계 상세: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` FIX-DB-POOL-SELF-RECOVERY-20260504 섹션 + 사고 logs 분석 trail (조사 5/6/7 결과) |
| FIX-ELEC-QR-DOC-ID-HARDCODE-20260502 | ELEC 완료 판정 SQL 의 `cr.qr_doc_id = ''` 하드코딩 → `_normalize_qr_doc_id()` 공유 helper 사용으로 마이그레이션 (Sprint 63-BE 후속 HOTFIX, 2026-04-30 등록) | 🟡 OPEN (P2, 1h, Sprint 63-BE 배포 후 즉시 후속) | **BE only — `backend/app/services/checklist_service.py` L923 + L945 의 `AND cr.qr_doc_id = ''` 하드코딩 SQL 2곳을 `_normalize_qr_doc_id(serial_number)` 공유 helper 호출로 변경**. 트리거: 2026-04-30 Codex 라운드 2 advisory Q6-3 — Sprint 63-BE 의 `_normalize_qr_doc_id()` 공유 helper 도입 후 ELEC 도 동일 표준 적용 필요. **선행 의존**: Sprint 63-BE 배포 완료 (`_normalize_qr_doc_id()` 함수 존재 보장). **변경 3건**: (1) checklist_service.py L424 주석 정정 ("MECH 등: 기존 그대로 qr_doc_id='' 사용" → 표준 normalizer 사용으로 갱신) (2) L923 SQL 의 `AND cr.qr_doc_id = ''` → `AND cr.qr_doc_id = _normalize_qr_doc_id(%(sn)s)` (Python 측에서 helper 호출 후 파라미터 주입) (3) L945 SQL 동일 패턴. **위험**: ELEC 운영 record 가 현재 `qr_doc_id=''` (31건) 상태 → 마이그레이션 후 매칭 깨짐 가능 → **마이그레이션 전 ELEC record `qr_doc_id` 일괄 UPDATE 필요** (DOC_{S/N} 패턴으로 backfill, 별 migration 052). **pytest TC**: test_check_elec_completion_normalize_qr_doc_id (정합성 회귀) + test_elec_record_backfill_migration (UPDATE 적용 후 매칭 OK). **순 LOC**: ~+5 / 회귀 위험: ELEC SINGLE/DUAL 호환성 정합성 (Sprint 63-BE 와 동일 검증 패턴). **Rollback** git revert 1 commit + ELEC record 원복 (qr_doc_id='' 재적용 — backfill 단방향 위험 별도 검토). 설계 상세: 본 BACKLOG entry + Sprint 63-BE `_normalize_qr_doc_id()` helper 호환 trail |
| DOC-MODELS-QR-REGISTRY-PATH-SYNC-20260502 | 설계서 ↔ 실파일 경로 sync (qr_registry helper 위치 명확화) | 🟢 OPEN (P3, 30분, 즉시 가능) | **doc drift fix only — 코드 변경 0**. 트리거: 2026-04-30 Codex 라운드 2 advisory Q6-A4 — Sprint 63-BE 설계서 일부 옛 표기에 `models/qr_registry.py` 언급 가능성 + 실파일 검색 결과 `/backend/app/models/qr_*.py` 경로 부재 확인. **현 상태**: Sprint 63-BE 4-A 섹션 (`_normalize_qr_doc_id()`) = `services/checklist_service.py` 정확 명시 — 그러나 다른 문서 잔존 표기 정합성 검증 필요. **작업**: (1) AGENT_TEAM_LAUNCH.md / memory.md / handoff.md / CLAUDE.md grep 으로 `models/qr_registry` 잔존 표기 확인 (2) 발견 시 `services/checklist_service.py` 또는 정확한 위치로 정정 (3) 신규 helper 도입 시 표준 위치 ADR 1줄 추가 (memory.md). **순 LOC**: ~10 (doc only) / 회귀 위험 0. 설계 상세: 본 BACKLOG entry only |
| SPRINT-63-FE-MECH-CHECKLIST-20260501 | Sprint 63-FE — MECH 체크리스트 Flutter UI + R2-1 BE patch + alert 핸들러 + pytest 3 TC (mech_checklist_screen.dart 844 LOC, 2026-05-01 등록 → 2026-05-04 v2.11.1 release, 라운드 1+2+N1+N2 모두 정정) | ✅ COMPLETED (v2.11.1, 2026-05-04, +1,038 LoC, BE+FE 통합) | **AXIS-OPS FE only — `frontend/lib/screens/checklist/mech_checklist_screen.dart` 신규**. 트리거: Sprint 63-BE BE 인프라 배포 완료. ELEC `elec_checklist_screen.dart` (1,076 LOC) 패턴 복제 + 입력 UI 3종 분기 추가. **변경 사항**: (1) `mech_checklist_screen.dart` 신규 (~1,000 LOC, ELEC 패턴 차용) (2) input_type 별 입력 위젯 분기 — CHECK 라디오 / SELECT 드롭다운 (`select_options` JSON 활용) / **INPUT 텍스트 필드 (INLET 8개 L/R 명확 구분 표시)** (3) 1차/2차 phase 토글 + 1차 입력값 read-only 표시 (관리자 화면) (4) scope_rule 매칭 안 되는 항목 = 회색 + "해당없음" 자동 NA UI (DRAGON/GALLANT/SWS 외 모델은 13/14/19 disabled) (5) WebSocket `CHECKLIST_MECH_READY` alert 수신 시 토스트 + 화면 진입 유도 (6) **INLET 8개 명확 구분** — 사용자 결정 옵션 A 변형 반영 (Left #1, Right #1, Left #2, ... 별도 입력 필드, schema 8 record per S/N 정합). **선행 의존**: Sprint 63-BE 배포 완료 (응답 schema scope_rule + trigger_task_id + select_options 활용). **Sprint 착수 시 결정 사항 1건 (Codex 라운드 3 A2-A 분리)**: DRAGON/GALLANT/SWS 외 모델의 13/14/19 그룹 disabled UI 메시지 텍스트 — "해당없음 (Tank Ass'y 미적용)" / "N/A" / "—" 중 ELEC 패턴 차용 + 화면 보면서 30초 결정. BE 응답 schema 영향 0 (FE 단독 결정). **수정 파일**: `mech_checklist_screen.dart` 신규 1 파일 + `app_navigation.dart` 라우팅 1줄 추가. **추정**: ELEC 패턴 차용으로 2d. **Rollback** git revert (Flutter 빌드 이전 상태) + Netlify 이전 빌드 활성화. 설계 상세: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` Sprint 63-BE 섹션 의 "AXIS-OPS FE 구현" 부분 cross-reference + ELEC `elec_checklist_screen.dart` 코드 참조 |
| ADR-029-COWORK-CLAUDE-CODE-WORK-SEPARATION-POLICY-20260511 | Cowork ↔ Claude Code 작업 분리 정책 정식 채택 (memory.md ADR-029 등록, 누적 catch 9건 임계 초과) | ✅ ADR 등록 완료 (2026-05-11) | **memory.md only — ADR 등록 정합 영역**. 트리거: 2026-05-07 memory.md ADR-023 2차 보강 영역 "ADR-024 분리 검토 영역 도달" (6건 누적) → 5-11 추가 3건 (5-08 #7 MFC + 5-09 #16 폐기 + 5-11 #18+#19 동일 그룹) = **9건 누적 도달**. 5-11 #18+#19 동일 endpoint 그룹 (체크리스트 master) GET+POST 동시 catch 실패 = cowork 검증 절차 부재 입증. **결정 — 3단계 분류**: **Tier 1** (직접 가능) = md 문서 / SQL read-only / 분석 / 인터뷰 / 설계 초안 (cowork 강점, 실수 0건). **Tier 2** (검증 필수) = HOTFIX 설계서 / API schema 변경 / 신규 코드 / Migration SQL / CONFLICT 응답 (검증 표준: cross-check + Codex 라운드 + pytest). **Tier 3** (금지) = prod DB 직접 변경 / 보안 / migration_history 직접 수정 / 데코레이터 신규 / deploy 결정. **검증 절차 표준 (Tier 2)**: ① cowork 작업 → ② Claude Code cross-check (grep + endpoint 그룹 일관성) → ③ Codex 라운드 1 → ④ pytest → ⑤ Pre-deploy Gate. **잠재 ADR-030 후보** (현재 trail, 미래 결정): cowork 사용 모델 명시 / 3자 역할 분리 표준 / Sprint 설계서 작성자 분리. **연관 ADR**: ADR-023 / ADR-024 / ADR-028. 설계 상세: `AXIS-OPS/memory.md` ADR-029 섹션 |
| FIX-DB-POOL-CONN-LEAK-WORK-PY-20260512 | work.py conn leak 5 위치 fix (L705 conn.close → put_conn + try/finally 4건) — 16:48 Railway pool exhausted 사고 root cause | ✅ **COMPLETED** (v2.14.1, 2026-05-12) — BE only ~40 LoC / Codex GREEN (M=0/A=1) / pytest 45/45 PASS / 회귀 위험 0 |
| HOTFIX-MATERIALS-CATEGORY-ILIKE-20260513 | `/api/admin/materials?category=` 가 `=` 정확 매칭이라 'm' / 'mfc' 입력 시 0건 — AXIS-VIEW OPS_API_REQUESTS.md #64 catch | ✅ **COMPLETED** (v2.14.2, 2026-05-13) — BE only 3 line + pytest TC 2건 / 15/15 PASS / 회귀 위험 0 | **BE only — `backend/app/routes/admin_materials.py` L82-84 `category = %s` → `category ILIKE %s` + `f'%{category}%'`**. 트리거: AXIS-VIEW v1.43.8 (FE client filter 정정 완료) 후속 BE. keyword/description 은 이미 ILIKE 적용되어 있어 일관성 보강. pytest TC 신규 2건 (case_insensitive + partial_match) + 기존 정확 매칭 MFC 13건 TC 회귀 0. **회귀 위험 0** (`=` 케이스는 `ILIKE` 부분 매칭에 흡수, NULL 매칭 동일). 연관: AXIS-VIEW BACKLOG OPS-MATERIALS-KEYWORD-ILIKE. |
| HOTFIX-ELEC-CHECKLIST-PLACEHOLDER-DEACTIVATE-20260513 | ELEC `checklist_master` placeholder 31건 (id 94-124, 'Jig 검사 항목 1~7' 포함) soft delete — 4-27 HOTFIX-08 부수 효과로 046a 자동 재적용된 사고 정정 | ✅ **COMPLETED** (v2.14.3, 2026-05-13) — BE only Migration 055 신규 + 046a 본문 교체 + pytest TC 5건 / Logic 변경 0 / 운영 검증 GREEN | **BE only — `backend/migrations/055_elec_checklist_placeholder_deactivate.sql` 신규 + `backend/migrations/046a_elec_checklist_seed.sql` 본문 교체 (placeholder → 047 정상 31항목 + ON CONFLICT DO NOTHING) + `tests/backend/test_migration_055_elec_placeholder.py` 신규 5 TC**. 트리거: 2026-05-13 사용자 catch — 운영 DB id 111-124 placeholder 'Jig 검사 항목 1~7' 표시. **Root cause**: HOTFIX-08 (v2.10.10, 2026-04-27 21:36:04) db_pool transaction 정리 부수 효과 → migration 046a (Sprint 57 초기 placeholder seed) 자동 재적용 → 047 의 `DELETE → 정상 INSERT` (4-10) 이후 placeholder 31건 신규 INSERT (id 94-124). UNIQUE 제약 (product_code, category, item_group, item_name) 충돌 회피 (item_name 다름) → ON CONFLICT DO NOTHING 우회 → 신규 row 추가. **사용자 결정 (5-13)**: Soft delete (`is_active=FALSE`) + record 50건 보존 (FK 보존, 작업자 입력 trail 감사용). **Logic 변경 0**: 모든 ELEC 체크리스트 logic 이 `cm.is_active=TRUE` 필터 사용 — check_elec_completion() Phase 1+2 + get_elec_checklist() + get_checklist_report(). 작업자/QI 화면 + 1차/2차 체크 + 성적서 모두 정상화. 운영 검증 GREEN (placeholder 0 active / 정식 31 active 유지 / 총 active 31). **회귀 위험 0**. 연관: HOTFIX-08 v2.10.10 (사고 trigger), Sprint 57-C v2.8.1 (047 정식 31항목 seed). |
| HOTFIX-ELEC-CHECKLIST-SELECT-IMMEDIATE-PUT-20260513 | ELEC checklist dropdown onChanged 시 즉시 PUT 누락 — "PASS 먼저 → 드랍다운" 순서 입력 시 selected_value 영원히 NULL (운영 record 11/18 NULL 사례) | ✅ **COMPLETED** (v2.14.4, 2026-05-13) — FE only 1 파일 변경 / flutter analyze clean / Netlify prod 배포 완료 / BE 무변경 / 회귀 위험 0 | **FE only — `frontend/lib/screens/checklist/elec_checklist_screen.dart` 변경 (dart:async import + `_selectDebounceTimers` Map + dispose cancel + `_saveSelectedValue()` helper 신규 + dropdown onChanged 영역 helper 호출 + PASS/NA 미선택 경고 위젯)**. 트리거: 2026-05-13 사용자 catch — ELEC master_id=67 (TUBE 종류/색상) 운영 record 18건 중 11건 selected_value=NULL. **Root cause**: dropdown onChanged 가 setState 만 호출하고 PUT API 호출 없음 → "PASS 먼저 → 드랍다운" 순서 입력 시 selected_value 영원히 NULL. MECH 는 v2.11.4 (4-22) Q6-C fix 적용된 패턴 (500ms debounce 즉시 PUT) 운영 안정 입증, ELEC 는 동일 fix 누락. **사용자 결정 (5-13)**: 옵션 A (MECH 패턴 그대로 — 즉시 PUT 500ms debounce + PASS/NA 미선택 경고). **동작 변경**: ① 드랍다운 → PASS (✅) ② **PASS → 드랍다운 (❌ NULL → ✅ 저장)** ③ **드랍다운만 (❌ → ✅ 저장 + 노란 경고)** ④ 옵션 여러번 변경 (✅ 마지막만 PUT). **BE 무변경** (`checklist_service.py:upsert_elec_check` 정상 처리 입증 — selected_value 단독 PUT 도 INSERT/UPDATE 모두 처리). **운영 영향**: 신규 입력 자동 정상 저장. 기존 NULL 11건 (4-24 ~ 5-13)은 자동 fix X — 운영자가 재진입 + 드랍다운 재선택 시 수동 보정. v2.14.3 placeholder fix 와 무관 (id 67 정식 영역). 연관: AXIS-VIEW v1.43.8 (FE client filter), MECH v2.11.4 Q6-C 패턴. |
| BUG-WORK-INSERT-ROLLBACK-EXPLICIT-20260512 | work.py L468-486 complete_single_action_route INSERT except 시 `conn.rollback()` 명시 추가 (보수적 보강) | 🟢 OPEN (P3 Advisory, Codex 라운드 1 A-1) — put_conn() 안에서 INERROR 상태 자동 정리되지만 명시적 rollback 호출이 보수적으로 더 안전. 추정 ~10분 + pytest |
| SPRINT-66-BE-FOLLOWUP-MATERIALS-UPLOAD-20260513 | Sprint 66-BE-FOLLOWUP v3 — 자재 마스터 Excel 일괄 업로드 endpoint (`POST /api/admin/materials/upload`) — Q1~Q3 (A) 확정 + Codex 5라운드 검증 GREEN | ✅ **COMPLETED** (v2.14.0, 2026-05-12) — BE only ~544 LoC + 24 TC / Codex 5라운드 (M=4→0 GREEN) / pytest 23/23 GREEN (Unit 12 + Integration 11 + 1 skip) / 회귀 위험 0 | **BE only — `backend/app/utils/material_parser.py` 신규 + `backend/app/routes/admin_materials.py` `/upload` route 추가 + `backend/tests/test_admin_materials_upload.py` 신규**. 트리거: AXIS-VIEW Sprint 42 v1.43.0 `MaterialUploadModal.tsx` 4단계 업로드 모달 prod 배포 완료, but BE `/upload` endpoint 미구현 → 사용자 측 자재 마스터 변경 시 SQL 직접 INSERT 필요 (운영 부담). **사용자 결정 (2026-05-13)**: Q1 MFC 동일 item_code 중복 row = (A) 자동 합침 (description 합쳐서 단일 row UPSERT) / Q2 BOM customer/model 변경 = (A) 컬럼 UPDATE (변경 추적) / Q3 row-level reject = (A) Best-effort (검증 트랜잭션 외부 + 정상 행만 트랜잭션 내부). **변경**: ① `material_parser.py` 신규 — 인코딩 감지 (chardet → UTF-8 → CP949 → EUC-KR fallback) + CSV/xlsx 파싱 + Q1 합침 + category 자동 추출 (MFC* → 'MFC' / 그 외 → 자재내역) + diff_with_db + commit_upload (~280 LoC) ② `/upload` route 추가 (preview / commit mode 분기, gst_or_admin_required, ~60 LoC) ③ pytest 15 TC 신규 (TC-MU-01~12 + TC-MU-13/14/15 Q1/Q2/Q3 trail, ~220 LoC) ④ requirements.txt 의존성 (chardet>=5.2.0, openpyxl>=3.1.0). **선행 의존성**: Sprint 66-BE Step 1~4 prod 배포 완료 ✅ (material_master + product_bom schema, admin_materials.py 5 endpoint 존재). **회귀 위험 0**: 기존 5 endpoint 영향 없음. DB schema 변경 0. migration 불필요. **추정**: 3-4일 (material_parser 0.5d + xlsx 신규 0.5d + diff 0.5d + commit 0.5d + route 0.3d + pytest 1d + Codex 정정 0.5d). **Rollback**: git revert 1 commit (회귀 0). **연관**: AXIS-VIEW OPS_API_REQUESTS.md #63 (원본 요청) + AXIS-VIEW Sprint 42 v1.43.0 (FE) + Sprint 64-BE v2 트랜잭션 분리 패턴 학습 + ADR-029 Tier 2 (admin_materials.py CRUD 6 endpoint 일관성). 설계 상세: AGENT_TEAM_LAUNCH.md § Sprint 66-BE-FOLLOWUP (Q1~Q3 결정 표 + 4 Phase 트랜잭션 패턴 + pytest 15 TC 매트릭스 포함) |
| SPRINT-64-BE-WORK-BATCH-V2-20260513 | Sprint 64-BE v3 — Work Start/Complete Batch (TM Tank Module 일괄 처리, helper 재사용 패턴, 분리 파일) | ✅ **COMPLETED** (v2.13.0, 2026-05-11) — BE only 신규 파일 2개 분리 (CLAUDE.md L545 정합) + pytest 30 TC GREEN (Unit 13 + Integration 17, staging DB 22분 10초 실측) + Codex 5 라운드 검증 (M=6→M=4→M=1→M=1→**M=0 GREEN**). | **BE only — `backend/app/routes/work_batch.py` (+117 LOC 신규) + `backend/app/services/task_service_batch.py` (+209 LOC 신규) + `backend/app/__init__.py` (+1 import) + `tests/conftest.py` (+150 LOC fixture 3종) + `tests/backend/test_work_batch.py` (+280 LOC 30 TC 신규)**. 트리거: 2026-04-28 등록 후 Codex 라운드 1 catch (M=6 Critical) → 2026-05-13 v2 재설계 → 라운드 2 catch (M=4, 분리 파일 + 30건 + pseudo code + 16+ TC) → v3 재정정 → 라운드 3 (M=1, 12 case + TC-AUDIT-02 + import 순서) → 라운드 4 (M=1, prefix 충돌) → 라운드 5 (M=0/A=1/N=3 GREEN) → 구현 진입. **결정 사항 (v3)**: ① 신규 파일 2개 분리 (기존 work.py 1,355 LOC 🔴 + task_service.py 1,551 LOC ⛔ touch 0) ② 30건 상한 (helper task당 7~9 query, pool MAX=30 안전) ③ best-effort sequential (audit log 자동 흡수) ④ `_match_manager_company()` work.py L340-356 reactivate 패턴 정합 (TMS = module_outsourcing OR mech_partner). **3 route 신규**: POST /work/start-batch + POST /work/complete-batch + GET /tasks/by-order/<sales_order>. **conftest fixture 3종**: seed_tank_module_tasks_batch / seed_manager_company_matrix / assert_audit_log_count. **pytest catch 2건** (Codex 5 라운드 못 catch, pytest 자체 catch): C1 case 인자 오기 (manager 'TMS' vs mod 'FNI') + complete TC reason 예상값 잘못 (NOT_STARTED → FORBIDDEN_WORKER, helper L217 guard 순서 영향). **회귀 위험 0**: 기존 endpoint touch 0, DB schema 변경 0, migration 불필요. **연관**: AXIS-VIEW Sprint 40 v1.40.0 (FE) + ADR-029 Tier 2 + ADR-023 + 후속 BACKLOG `BUG-MATCH-COMPANY-SUBSTRING-FALSE-POSITIVE-20260511` (A-1 substring boundary, 운영 미발생 P3). 설계 상세: AGENT_TEAM_LAUNCH.md § Sprint 64-BE v3 (L35506~L36044, Codex 5 라운드 catch trail + v1→v2→v3 차이 매트릭스 포함) |
| FEAT-BATCH-START-WITHOUT-QR-TAG-20260511 | VIEW 일괄 시작/종료 시 QR 태깅 없이도 작업 현황 표시 — task seed 자동 생성 fallback (Sprint 64-BE v3 후속) | 🟡 OPEN (P2 MEDIUM, 사용자 제안 2026-05-11, 검토 단계) | **BE — `task_service_batch.py` `start_work_batch()` 안에 task seed 자동 생성 helper 추가 또는 `/tasks/by-order/<sales_order>` fallback 처리**. 트리거: 2026-05-11 사용자 catch — 현재는 OPS app QR 태깅 시점에 `initialize_product_tasks()` 자동 호출로 task seed가 생성되므로 admin/manager가 VIEW에서 일괄 시작 액션을 해도 task가 없으면 시작 자체가 안 됨. **사용자 의도**: admin/manager가 사전 등록할 수 있도록 운영 (작업자 QR 태깅 전에도 작업 현황 표시 가능). **검토 옵션**: ① A — `start_work_batch()` 안에 `_ensure_tasks_exist()` helper 추가 (task seed 자동 호출) ② B — 새 endpoint `/work/start-batch-by-order`로 sales_order 받아서 task seed 자동 생성 + 시작 동시 처리 ③ C — `/tasks/by-order/<sales_order>` prefetch 시점에 task seed fallback ④ D — 미진행 (기존 흐름 유지, Location QR 검증 우회 위험으로 사용자가 SKIP 결정 가능성). **검토 필요 사항**: Location QR 검증 (`location_qr_required` admin setting=TRUE일 때) 우회 위험 + model_config 분기 (GAIA/DRAGON/iVAS 별 task 종류 차이). **추정**: A ~2h / B ~4h / C ~1h. **선행 의존성**: Sprint 64-BE v3 + v2.13.1 + v2.13.2 prod 정합 확인. **회귀 위험**: A/B 낮음 (additive) / C 중간 (prefetch 영향). 설계 상세: 사용자 제안 trail + 옵션 비교 표 |
| HOTFIX-TASKS-BY-ORDER-WORKERS-20260511 | `/api/app/tasks/by-order/<sales_order>` 응답에 `workers` 배열 추가 — Sprint 64-BE v3 / v2.13.1 후속 hotfix (S1 동반) | ✅ **COMPLETED** (v2.13.2, 2026-05-11) — BE only ~110 LoC / VIEW v1.43.6 S1 HOTFIX 동시 release / 회귀 위험 0 / POST-REVIEW deadline 2026-05-12 | **BE only — `backend/app/services/task_service_batch.py` 신규 helper `_enrich_tasks_with_workers()` (~100 LoC) + `get_tasks_by_order()` helper 호출 추가 (1 line)**. 트리거: v2.13.1 release 직후 VIEW v1.43.6 S1 HOTFIX catch — `/tasks/by-order/` 응답에 `workers` 배열 누락 → FE `task.workers.find()` TypeError → React crash → S/N 상세뷰 흰 화면. **Root cause**: `get_tasks_by_order()`에서 `_task_to_dict()` 호출 후 후처리가 없음. 기존 `get_tasks_by_serial` (work.py L562~728)의 약 170 line 후처리 (workers + worker_name + my_status 일괄 조회) 동일 패턴이 누락됨. Codex 5라운드 + v2.13.1 catch 모두 응답 spec 검증만 했고, 후처리 패턴 일관성 검증이 누락. **변경 (~110 LoC)**: ① 신규 private helper `_enrich_tasks_with_workers(task_list)` — worker_name 일괄 조회 + workers 배열 일괄 조회 (work_start_log JOIN workers JOIN work_completion_log) + legacy fallback ② `get_tasks_by_order()`에 helper 호출 추가 ③ work.py touch 0 (분리 정책 정합). **응답 schema 추가**: 각 task item에 `workers: [...]` + `worker_name: string | null`. **POST-REVIEW**: 24h 이내 Codex 사후 검토 (CLAUDE.md L237 S1 정합) + Codex 검증 라운드 표준화 권고 (응답 spec + 후처리 패턴 동시 검증). **연관**: AXIS-VIEW v1.43.6 S1 HOTFIX (FE 정규화 + 가드) + Sprint 64-BE v3 (v2.13.0) + v2.13.1 (응답 형식). 설계 trail: CHANGELOG.md v2.13.2 entry |
| HOTFIX-TASKS-BY-ORDER-SCHEMA-20260511 | `/api/app/tasks/by-order/<sales_order>` 응답 형식 정정 — Sprint 64-BE v3 후속 hotfix (객체 wrap → 배열 직접 반환) | ✅ **COMPLETED** (v2.13.1, 2026-05-11) — BE only ~5 line / VIEW v1.43.5 동시 release / 회귀 위험 0 | **BE only — `backend/app/services/task_service_batch.py` `get_tasks_by_order()` return 영역 정정 (`{tasks, total}` → `tasks` 배열 직접)**. 트리거: v2.13.0 Sprint 64-BE v3 release 직후 AXIS-VIEW 측 catch — VIEW `getTasksByOrder()` 영역 `Array.isArray(data) ? data : []` 영역 객체 응답 빈 배열 fallback → 일괄 시작 토스트 미표시. **Root cause**: Codex 5 라운드 검증 모두 통과 영역, 다른 list endpoint (`/api/app/tasks/{sn}?all=true` 영역 배열 직접) 응답 spec 대조 누락. POST-REVIEW catch. **옵션 B 선택**: VIEW v1.43.5 호환 코드 (양쪽 형식 처리) + OPS v2.13.1 정합 정정 동시 release → 양쪽 즉시 정합 + 회귀 0. **변경 (~5 line)**: ① return type annotation `Tuple[Dict, int]` → `Tuple[List[Dict], int]` ② return 영역 `({'tasks': tasks, 'total': N}, 200)` → `(tasks, 200)` ③ `jsonify(response)` 그대로 (Flask 3.x list 자동 처리). **POST-REVIEW 후속**: Codex 검증 라운드 영역 응답 spec 일관성 항목 추가 권고 (다른 endpoint 대조 표준화). **연관**: AXIS-VIEW v1.43.5 HOTFIX-TASKS-BY-ORDER-SCHEMA (FE 호환 코드) + Sprint 64-BE v3 (v2.13.0 선행). 설계 상세: CHANGELOG.md v2.13.1 entry + 5 endpoint 응답 spec 비교 표 |
| BUG-MATCH-COMPANY-SUBSTRING-FALSE-POSITIVE-20260511 | `_match_manager_company()` substring 매칭 false positive 가능성 — BAT vs COMBAT 같은 boundary issue (work.py L347 reactivate 패턴 정합 보존 영역) | 🟢 OPEN (P3 Advisory, 운영 미발생) | **BE — `backend/app/services/task_service_batch.py` `_match_manager_company()` + `backend/app/routes/work.py` L340-356 reactivate 패턴 동시 정정**. 트리거: Sprint 64-BE v3 Codex 라운드 2 A-1 advisory. **catch**: `base in mech` substring 매칭 → `('BAT', 'MECH', None, 'COMBAT') → True` boundary 위반. 현재 운영 데이터 기준 발생 케이스 0 (mech_partner/module_outsourcing 영역 FNI/BAT/TMS/P&S/C&A 영역 substring 충돌 없음). **변경 영역**: word boundary (regex `\b`) 또는 set 매칭 영역 + 정확 매칭 only (substring 제거). 다만 work.py reactivate 패턴 동시 정정 필요 (정합 보존). **추정**: 1~2h (양쪽 정정 + pytest TC 갱신 + 운영 데이터 검증). **선행 의존성**: 운영 데이터 영역 boundary 충돌 모니터링 (분기별 1회). **사용자 영향**: 0 (현재). **회귀 위험**: 매우 낮음 (substring 영역 → 정확 매칭 영역 강화). 설계 상세: AGENT_TEAM_LAUNCH.md § Sprint 64-BE v3 § A-1 BACKLOG 영역 |
| HOTFIX-SPRINT66BE-CREATE-MASTER-ITEM-TYPE-AND-CONFLICT-MSG-20260513 | `/api/admin/checklist/master` POST INSERT 에서 `item_type` + `select_options` 컬럼 누락 + CONFLICT 응답 메시지 비식별 (cowork 실수 #19, Sprint 52 시점 회귀) | 🟠 **S2 (5-11 등록, 핫픽스 적용 완료, 7일 사후 Codex 검토 필요, deadline 2026-05-20)** | **BE only — `backend/app/routes/checklist.py` `create_checklist_master()` (L375-461) INSERT 정정 + CONFLICT 응답 보강**. 트리거: 2026-05-11 사용자 catch — AXIS-VIEW 항목 추가 모달에서 신규 항목 생성 시 toast "추가에 실패했습니다" + Network 응답 `{"error": "CONFLICT", "message": "이미 존재하는 항목입니다."}` (409). **3 분리 원인**: ① UNIQUE 제약 `(product_code, category, item_group, item_name)` (migration 043a) 위반 — 사용자가 추가하려는 (그룹+항목명) 조합이 이미 DB 에 존재 (활성/비활성 무관). ② **POST INSERT 가 `item_type` / `select_options` 컬럼 누락** — FE 가 `item_type='SELECT'|'INPUT'` 전송해도 BE 가 무시하고 DB DEFAULT `'CHECK'` 저장 → 신규 SELECT/INPUT 항목 생성 불가 묵음 회귀 (Sprint 52 POST 작성 시점 ~ Sprint 63-BE 'INPUT' enum 확장 시점까지 누적). ③ GET 가 `is_active=TRUE` 만 반환 → 비활성 항목 충돌 시 사용자 디버깅 불가. **변경 (~50 LoC)**: (1) `item_type` 추출 + 검증 (CHECK/SELECT/INPUT) (2) `select_options` 추출 + 타입 검증 (list) (3) INSERT 컬럼 2개 추가 (4) `json.dumps()` 직렬화 (admin_checklists.py L224 컨벤션 정합) (5) CONFLICT 응답에 기존 충돌 항목 `id` + `is_active` 포함 + 비활성 시 토글 안내 메시지. **POST-REVIEW**: BACKLOG `POST-REVIEW-HOTFIX-SPRINT66BE-CREATE-MASTER-ITEM-TYPE-20260511` 등록 (7일, deadline 2026-05-20). **선행 의존성 0** (HOTFIX-SPRINT66BE-MASTER-LIST-ITEM-TYPE-20260513 동시 배포 권장 — 동일 endpoint 그룹). **회귀 위험**: 0 (FE 가 item_type 미전송 시 'CHECK' fallback — 기존 동작 보존). **추정**: 10분 (정정 완료) + pytest TC 3건 (P2: SELECT/INPUT 신규 생성 + 비활성 CONFLICT 메시지 + select_options JSON 직렬화). **Rollback**: git revert 1 commit. **연관**: HOTFIX-SPRINT66BE-MASTER-LIST-ITEM-TYPE-20260513 (GET) + Sprint 52 (POST 작성 시점) + Sprint 63-BE migration 051 (item_type 'INPUT' enum 확장). **검증 방법** (사용자 측): admin 로그인 → 체크리스트 관리 → MECH → "+ 항목 추가" → 그룹: GN2 / 항목명: "테스트 SELECT 1" / 타입: SELECT → "추가" → DB `SELECT id, item_name, item_type FROM checklist.checklist_master WHERE item_name='테스트 SELECT 1'` 결과 `item_type='SELECT'` 확인. 설계 상세: AGENT_TEAM_LAUNCH.md HOTFIX-SPRINT66BE-CREATE-MASTER-ITEM-TYPE-AND-CONFLICT-MSG-20260513 섹션 |
| HOTFIX-SPRINT66BE-MASTER-LIST-ITEM-TYPE-20260513 | `/api/admin/checklist/master` GET 응답에서 `item_type` + `select_options` 직렬화 누락 → AXIS-VIEW v1.43.1 SELECT 분기 UI 미동작 (cowork 실수 #18, Sprint 66-BE 직렬화 회귀) | 🟠 **S2 (5-11 등록, 핫픽스 적용 완료, 7일 사후 Codex 검토 필요, deadline 2026-05-20)** | **BE only — `backend/app/routes/checklist.py` `list_checklist_master()` (L256-368) SELECT 절 + 응답 dict 정정 (+2 LoC)**. 트리거: 2026-05-11 사용자 catch — AXIS-VIEW v1.43.1 prod 배포 정상 확인 + Netlify deploy 검증 완료, 그러나 `/api/admin/checklist/master?category=MECH&product_code=COMMON` 응답 JSON 에 `item_type` 필드 완전 누락 (id=150 MFC Maker SELECT 항목 응답 = `{id, category, item_group, item_name, item_order, description, is_active, phase1_applicable, qi_check_required, remarks, checker_role}` only). **Root cause**: Sprint 66-BE 또는 그 이전 시점부터 admin master list 엔드포인트 SELECT 쿼리 (L320-340) 가 `cm.item_type` / `cm.select_options` 컬럼을 SELECT 절에서 누락 + 응답 dict (L343-359) 에서도 누락. DB 스키마 (`checklist_master`) 에는 두 컬럼 모두 존재하며 `services/checklist_service.py` MECH 분기 (L196/L203) 등 다른 엔드포인트는 모두 정상 반환. admin master list 만 회귀. **사용자 영향**: ChecklistEditModal (v1.43.1) `item.item_type === 'SELECT'` 분기 = 항상 false (item_type undefined) → SELECT 매핑 UI 자체가 그려지지 않음 → 자재 매핑 기능 사용 불가. **변경 (+2 LoC)**: (1) SELECT 절에 `cm.item_type, cm.select_options` 추가 (2) 응답 dict 에 `'item_type': row.get('item_type') or 'CHECK', 'select_options': row.get('select_options')` 추가. **POST-REVIEW**: BACKLOG `POST-REVIEW-HOTFIX-SPRINT66BE-MASTER-LIST-ITEM-TYPE-20260513` 등록 (7일, deadline 2026-05-20). **선행 의존성 0**. **회귀 위험 0** (additive 응답 — 기존 FE/Flutter 클라이언트 무영향, 신규 필드만 추가). **추정**: 5분 (정정 완료) + pytest TC 1건 (응답 schema 정합성, P2). **Rollback**: git revert 1 commit (회귀 없음). **연관**: AXIS-VIEW HOTFIX-SPRINT42-CHECKLIST-EDIT-MATERIAL-MAPPING-20260509 (v1.43.1) + Sprint 66-BE Step 4. **검증 방법** (사용자 측): admin 로그인 → 체크리스트 관리 → MECH/COMMON 진입 → SELECT 항목 (예: id=150 MFC Maker) 수정 클릭 → "🔍 자재 검색 도움" 버튼 + 선택지 입력 영역 표시 확인. 설계 상세: AGENT_TEAM_LAUNCH.md HOTFIX-SPRINT66BE-MASTER-LIST-ITEM-TYPE-20260513 섹션 |
| HOTFIX-SPRINT66BE-ENRICH-SELECT-OPTIONS-ITEMCODE-20260509 | _enrich_select_options() 자재코드 string[] 영역 처리 추가 (Sprint 66-BE 후속 hotfix) | ❌ **OBSOLETE — 5-09 Codex 검토 라운드 catch (M1~M5 + A1~A2)** — 방향 A 채택 (AXIS-VIEW 정정, HOTFIX-SPRINT42 v1.43.1 영역 자재코드 → material_id 변환). 본 entry 폐기 영역. 근거: ① M3 endpoint 충돌 (Sprint 42 Step 4 = int 검증) ② M2 N+1 BATCHED 회귀 (73 query) ③ M5 ADR-027 옵션 X 위반 (selected_material_id NULL) ④ M4 description 영역 (5-08) 위반 ⑤ M1 시그니처 불일치. → AXIS-VIEW v1.43.1 영역 정정 시 BE 영역 변경 0 + 모든 Sprint 42 schema 영역 정합 보존 | **BE only — `backend/app/services/checklist_service.py` `_enrich_select_options()` 영역 정정**. 트리거: 2026-05-09 cowork 자체 검증 catch (사용자 측 OPS BE FE 영역 catch) — AXIS-VIEW HOTFIX-SPRINT42 v1.43.1 영역에서 admin 이 "선택지 (자재코드, 쉼표 구분)" 영역에 자재코드 직접 입력 시 (예: `["1110006700", "1120094300"]`) → DB select_options = 자재코드 string[] 저장. **Root cause**: 현재 `_enrich_select_options()` L78-79 영역 = `all(isinstance(x, str))` 조건 매칭 → legacy placeholder 영역으로 처리 (material_ids 모두 None) → material_master JOIN X → Flutter 측 dropdown 에 자재코드 raw 표시 (`"1110006700"`) → 작업자 측 정보 부족. **변경 (~15 LoC)**: string[] 영역에서 자재코드 패턴 검증 (10자리 숫자 string) → 매칭 시 material_master JOIN → 옵션 Y string 변환 (`"MFC | MRC | 25 SLM | P:0.2~1 / W:0.4"`) → 미매칭 시 legacy placeholder 영역 그대로. **Severity**: 🟠 S2 (부분 장애 — 작업자 dropdown 자재 raw 표시 영역). **사후 Codex 검토**: 7일 이내 (deadline 2026-05-16) — CLAUDE.md L237 정합. **POST-REVIEW**: BACKLOG `POST-REVIEW-HOTFIX-SPRINT66BE-ENRICH-SELECT-OPTIONS-ITEMCODE-20260509` 등록. **선행 의존성**: Sprint 66-BE Step 3 prod 배포 완료 (`_enrich_select_options()` 함수 존재) + AXIS-VIEW HOTFIX-SPRINT42 v1.43.1 동기 영역 (admin 자재코드 입력 영역). **사용자 영향**: 작업자 측 dropdown 영역 = 자재코드 raw 표시 → 옵션 Y full spec 표시 영역 정정. **회귀 위험**: 0 (자재코드 패턴 영역 매칭 시점만 신규 분기, legacy placeholder 영역 그대로). **추정**: ~1h (정정 ~15 LoC + pytest TC 2건). **Rollback**: git revert 1 commit. **연관**: AXIS-VIEW HOTFIX-SPRINT42-CHECKLIST-EDIT-MATERIAL-MAPPING-20260509 (v1.43.1) + Sprint 66-BE (FEAT-MATERIAL-MASTER-AND-BOM-INTEGRATION-20260507). 설계 상세: AGENT_TEAM_LAUNCH.md HOTFIX-SPRINT66BE-ENRICH-SELECT-OPTIONS-ITEMCODE-20260509 섹션 |
| FEAT-CHECKLIST-OPTIONS-CACHE-20260508 | checklist_master.select_options 의 material_master JOIN BATCHED SELECT 영역 in-memory cache (TTL 5분) — 작업자 진입 빈도 ↑ 영역 성능 보호 (P2 cowork 점검 라운드 1 권고) | 🟢 OPEN (P2, 1h, FEAT-MATERIAL-MASTER-AND-BOM-INTEGRATION 후속) | **BE only — `backend/app/services/checklist_service.py` `_enrich_select_options()` 영역에 in-memory cache layer 추가**. 트리거: 2026-05-07 cowork 자체 검증 라운드 1 P2 #10 — material_master JOIN 영역 N+1 → BATCHED 단일 SELECT 최적화 후에도 작업자 진입 빈도 (분당 N건) × 73 항목 × 평균 6 material_id = ~438 ID/호출 부담 영역. **Root cause**: material_master 변경 빈도 낮음 (admin 매핑 수정 시점만) but 작업자 측 GET /checklist/mech 매번 호출 시 DB 부담. **변경**: (1) functools.lru_cache 또는 cachetools TTL cache 도입 (TTL 5분, 또는 admin 매핑 PATCH 시점 invalidate) (2) cache key = checklist_master.id + select_options hash (3) prepared statement 영역 검토 (선택). **선행 의존성**: FEAT-MATERIAL-MASTER-AND-BOM-INTEGRATION-20260507 배포 완료 (`_enrich_select_options()` 함수 존재). **사용자 영향**: 작업자 측 응답 속도 ↑ (cache hit 시 DB 호출 0). **회귀 위험**: 낮음 (cache invalidation 영역 검증 필수, admin 매핑 변경 시 즉시 stale cache 제거). **추정**: 1h (cache 도입 + invalidation hook + pytest TC 2건). **Rollback**: git revert 1 commit (cache 비활성화). 설계 상세: AGENT_TEAM_LAUNCH.md FEAT-MATERIAL-MASTER-AND-BOM-INTEGRATION-20260507 섹션 + cowork 자체 검증 라운드 1 P2 #10 trail |
| FEAT-SI-HOOKUP-CHECKLIST-FLOW-20260508 | SI hook-up 검사 흐름 — 마무리공정 task_id 진입 시 토스트 + 작업자 SI 화면 + bom_checklist_log 적재 (협력사 check list 패턴 차용, FK key=product_code) | 🟡 OPEN (P2, Sprint 64 이후, 5-07 사용자 답변 4번) | **BE + FE 양쪽 — bom_checklist_log 활용 SI 공정 hook-up 검사 흐름 구현**. 트리거: 2026-05-07 사용자 답변 — "현재 hook-up list 토스트는 설계되지 않았지만, 협력사 check list flow 와 동일함, task_id: 마무리공정 시작으로 진입 시 체크리스트 토스트, FK key 는 product_code 가 맞음 (이건 후순위, sprint 64 이후에 적용)". **선행 의존성**: ① FEAT-MATERIAL-MASTER-AND-BOM-INTEGRATION-20260507 배포 완료 (Step 4 까지) — material_master + product_bom + bom_checklist_log schema + admin UI 자재 등록 ② Sprint 64 (regression 위험 영역 재설계) ✅. **변경 영역 추정**: ① BE: SI 마무리공정 task_id 분기 (work/start 응답 + alert_type CHECKLIST_SI_HOOKUP_READY 신규) ② BE: GET /checklist/si-hookup?serial_number=X → product_code 추출 → product_bom 조회 → 자재 N건 응답 ③ BE: POST /checklist/si-hookup/log → bom_checklist_log INSERT ④ FE: si_hookup_screen.dart 신규 (mech_checklist_screen.dart 패턴 차용 ~600 LOC) ⑤ FE: WebSocket alert 핸들러 + 토스트 ⑥ task_detail_screen 진입 버튼. **추정**: ~5h+ (FE 화면 신규 + BE API + alert 분기 + pytest). **위험**: 중간 정도 — 신규 화면 + alert 영역 + 협력사 check list 패턴 정확 차용 검증 필수. **연관**: 본 entry = 1순위 sprint 인프라 활용 후속, 3순위 영역 (사용자 5-07 우선순위 매트릭스 명시). 설계 상세: 사용자 답변 4번 + 협력사 check list flow 패턴 cross-reference + AGENT_TEAM_LAUNCH.md FEAT-MATERIAL-MASTER-AND-BOM-INTEGRATION-20260507 섹션 |
| FEAT-MATERIAL-AI-VISION-VERIFY-20260508 | bom_checklist_log 의 ai_* 컬럼 활용 — 작업자 사진 업로드 → AI 자재 명판 인식 → 1차 입력값 매칭 검증 (Phase 3) | 🟢 OPEN (P3, Sprint 64 이후, 5-07 사용자 답변 5번) | **BE + AI Vision API + FE — bom_checklist_log 의 미사용 ai_* 컬럼 인프라 활용**. 트리거: 2026-05-07 사용자 답변 5번 — "추후 논의 + backlog 기록 가능". **인프라**: bom_checklist_log 17 컬럼 중 5건 (ai_verified / ai_verified_at / ai_confidence / ai_image_url / ai_response) 이 Phase 3 영역으로 이미 schema 보존됨. **변경 영역 추정**: ① 작업자 SI 화면에서 자재 사진 업로드 버튼 ② BE: 사진 업로드 endpoint + 객체 스토리지 (Cloudinary 또는 Railway 볼륨) ③ BE: AI Vision API 호출 (OpenAI GPT-4 Vision 또는 Claude Sonnet Vision) — 자재 명판 OCR + 자재코드 인식 ④ BE: 1차 입력값 (selected_value=material_id) 과 AI 인식 자재코드 매칭 ⑤ 일치 → ai_verified=TRUE / 불일치 → mismatch_reported=TRUE + 관리자 알림 ⑥ FE: 결과 표시 (AI 일치 / 불일치 시 다시 촬영 가이드). **선행 의존성**: ① FEAT-SI-HOOKUP-CHECKLIST-FLOW-20260508 배포 완료 (검사 화면 인프라) ② AI API 비용 / 정확도 검증 ③ 객체 스토리지 도입 (사진 보관). **추정**: ~10h+ (AI API 통합 + 객체 스토리지 + UI + 비용 분석 + pytest). **위험**: 높음 — AI API 비용 / 정확도 / 응답 시간 영역 검증 필수. **POC 우선**: 본 sprint 진행 전 AI Vision API 정확도 / 비용 / 처리 시간 POC 1주 권장. **연관**: bom_checklist_log schema (Sprint FEAT-MATERIAL-MASTER-AND-BOM-INTEGRATION) ai_* 컬럼 보존 → 본 sprint 활용. 사용자 우선순위 = 3순위 (Sprint 64 이후). 설계 상세: 사용자 답변 5번 + bom_checklist_log Phase 3 영역 + AI Vision API POC trail (사전 검증) |
| Sprint 66-BE / FEAT-MATERIAL-MASTER-AND-BOM-INTEGRATION-20260507 | 자재 마스터 (material_master) 신설 + product_bom/bom_checklist_log public→checklist 이전 + checklist_master 동적 자재 조회 + AXIS-VIEW 자재 등록 페이지 (R3 단계별 release, 운영 flow P1, MECH 체크리스트 완성 prerequisite, Sprint 65-BE 후속, Sprint 64 후순위) | ✅ COMPLETED (P1 OPS 측, **Step 1 ✅ v2.12.0 (5-07) / Step 2 ✅ v2.12.1 (5-08) / Step 3 ✅ v2.12.2 (5-08) / Step 4 ✅ v2.12.3 (5-08, OPS BE)**, Step 4 AXIS-VIEW 측 = Sprint 42 별 repo. 총 pytest 47/47 GREEN, BE+FE 운영 적용 완료. Codex 라운드 1~5 + Step 4 라운드 1 모두 GREEN. **Sprint 66-BE OPS 측 100% 종결**) | **BE + AXIS-VIEW + DB schema 통합 — `checklist.material_master` 신규 + `public.product_bom` / `public.bom_checklist_log` → `checklist.*` 이전 + 51a placeholder 옛 옵션 BE 동적 override + 자재 등록/체크리스트 관리 페이지**. 트리거: 2026-05-07 Twin파파 운영 사용자 catch — 51a seed 의 select_options 가 placeholder JSON ("MKS GE50A | 5 SLM | 0.5 MPa | 0.1-0.7 MPa") 라 현장 작업자 무관 + DB 직접 수정 운영 불가능. **3 영역 영구 해결**: ① 51a placeholder 무의미 옵션 → 실 자재 데이터 ② DB 직접 수정 의존 → admin UI 등록 ③ MECH 체크 + SI hook-up BOM 검사 분리 인프라 → 단일 자재 마스터 공유. **검증 받은 데이터 (5-07 사용자 측 검증)**: csv 1,640 row (246 product_code × 173 unique 자재) + xlsx 14 MFC 자재 (4 가스: LNG/CDA/O2/N2) + plan.product_info 매칭 부분 (4100xxxx prefix 다수 missing → soft FK 채택). 통합 csv: `/Users/twinfafa/Desktop/GST/material_master_통합.csv` = 1,654 row, 186 unique 자재. **schema 결정 (사용자 합의)**: ① material_master 신설 (정규화) ② product_bom 마이그레이션 + 영문 컬럼 (product_code/customer/model/material_id/quantity) ③ bom_checklist_log 마이그레이션 (17 컬럼 그대로, AI 검증 영역 보존) ④ checklist_master.select_options 에 material_id 배열 저장 (admin 매핑) ⑤ checklist_record.selected_value 에 material_id 저장 ⑥ FK 정책 = soft FK (REFERENCES X, plan.product_info 미등록 product_code 도 INSERT 허용). **R3 4 단계 release**: Step 1 (~1h, BE) — Migration 053 schema 이전 + material_master CREATE → v2.12.0 (BE only) / Step 2 (~30분, SQL) — Migration 053a seed (186 자재 + 1,640 BOM) → v2.12.1 (SQL only, schema 변경 0) / Step 3 (~2h, BE+FE) — checklist_master 동적 조회 + 51a BE override + mech_checklist_screen.dart material spec 표시 → v2.12.2 (MECH 체크리스트 완성!) / Step 4 (~3h, AXIS-VIEW + BE) — /materials 페이지 + /checklists 관리 페이지 + admin/GST 권한 → v2.12.3 (admin UX 완성). **선행 의존성 0** (BE 단독 시작 가능, SI hook-up list 별도 구현은 Step 4 후 별 sprint). **회귀 위험 0** (material_master + product_bom 마이그레이션 = 신규 테이블 + soft FK, 기존 코드 영향 0. 51a placeholder 동적 override = BE additive 변경). **사용자 영향**: Step 1+2 = 0 (schema만, 기존 51a placeholder 유지) / Step 3 = MECH 체크리스트 SELECT 옵션 placeholder → 실 자재 데이터 (긍정 영향) / Step 4 = admin UX 개선 (DB 직접 수정 X). **Rollback**: 단계별 git revert + Migration 053 reverse migration (별도). **연관 sprint**: Sprint 63-BE/FE (MECH 체크리스트 도입) ✅ + Sprint 65-BE (성적서 분기) ✅ + 본 sprint = MECH 체크리스트 완성 영역. **ADR 후보**: ADR-027 (자재 마스터 인프라 도입). 설계 상세: `AXIS-OPS/AGENT_TEAM_LAUNCH.md` FEAT-MATERIAL-MASTER-AND-BOM-INTEGRATION-20260507 섹션 + 통합 csv 파일 + plan 매칭률 검증 SQL trail (5-07 사용자 측 검증 완료) |
| OBSERV-DUAL-WORKER-CONN-COEXIST-20260511 | 2 worker × MIN=5 = 10 기대치 미달 (실측 5 conn 일관) — 양쪽 worker 동시 active conn 보유하지 않는 패턴 추적 (2026-05-13 등록, OBSERV-PER-WORKER-POOL-RECOVERY-20260507 close 후속) | 🟢 OPEN (P3, 1~2h, 사용자 영향 0 영역) | **분석 only — 잠재 capacity gap**. 트리거: 2026-05-11 15:42 KST 측정 (자가 회복 직후 + warmup 직후 2회) — Sentry 가 pid=3 자가 회복 보고 + Boot logs `[2]` + `[3]` 동시 boot 확정에도 pg_stat_activity 항상 5 conn 만 visible (5-07 측정과 동일). **2 worker × MIN=5 = 10 기대** vs **실측 5 conn** = capacity 절반. **사용자 영향 0** (현재 트래픽 수준 peak 16 in-flight 까지 direct conn fallback 흡수, p95 < 200ms 정상) → **시급도 낮음**. **가능한 해석 3종 (검증 필요)**: (A) Railway proxy 가 한쪽 worker 의 conn 을 더 자주 disconnect — proxy 분배 불균등 (B) 양쪽 worker 가 시간차로 active — 한 쪽 dead/idle 시 다른 쪽 active (5일 주기 사고 패턴과 정합) (C) `pg_stat_activity` SELECT 시점에 한쪽 worker 의 conn 이 우연히 모두 transient (TLS handshake 중) — 측정 artifact 가능성. **검증 방법**: ① pg_stat_activity 의 `application_name` 외 다른 필드 (`pid` 의 OS-level 분포 / `client_addr` ephemeral port range) 로 worker 별 conn 분포 추적 ② Railway logs 에서 boot 직후 5분 간격 측정 → 양쪽 worker 모두 5 conn 보유 시점 확인 ③ pg_stat_activity 의 `state_change` 패턴 + warmup cron tick 시점 cross-reference. **권장 액션**: (1) burst 시점 capacity 부족 신호 발생 시 (HTTP 5xx 증가 또는 direct conn fallback 다발) **즉시 P2 격상** (2) 그 전까지는 분석 only 영역 — 자가 회복 메커니즘이 안전망 역할 정상. **검증 시나리오 4개**: (1) boot 직후 5분 시점 conn 측정 (양쪽 worker fresh 시 10 conn 도달 여부) (2) burst peak 직후 conn 분포 (16 in-flight 시점) (3) idle 시간 24h+ 후 conn 분포 (5 conn 정착 여부) (4) Railway worker restart 강제 후 conn 분포. **소요**: 분석 only — 측정 SQL 정교화 30분 + 24h 자연 추세 관찰 + 정리 30분 = 1~2h. **데이터 근거**: handoff.md 5-11 14:55 KST 자가 회복 2차 실전 작동 블록 + `DB_POOL_VERIFICATION_QUERIES_20260427.md` V4.1 5-11 trail (측정 1 3 conn + 측정 2 5 conn, warmup tick 3 conn 보충 입증). **선행 의존성 0** (분석 only). **회귀 위험 0** (분석 only, 코드 변경 없음). **최초 등록**: 2026-05-11 15:42 KST (OBSERV-PER-WORKER-POOL-RECOVERY-20260507 close 후속 발견 영역). **연계 sprint**: ADR-025 (DB Pool 자가 회복 메커니즘) 의 *"per-worker 카운터 의도가 양쪽 worker 정상 작동"* 입증 후속 + `OBSERV-RAILWAY-HEALTH-TTFB-15S-INTERMITTENT` (외부 모니터링) 도입 시 자연 추적 가능 |
| OBSERV-PER-WORKER-POOL-RECOVERY-20260507 | ~~gunicorn 다중 worker 환경에서 scheduler-owner 외 worker 의 풀 dead 자가 회복 메커니즘 부재~~ (2026-05-07 등록 가설 → **2026-05-11 측정으로 가설 폐기**) | ✅ **CLOSE 권장** (P2 → 폐기, 2026-05-11 가설 반박됨) | **🎯 2026-05-11 14:55 KST 측정으로 5-07 가설 전수 폐기됨**. ~~기존~~: Worker B 풀 dead 시 warmup cron 미실행 → 자가 회복 trigger 도달 불가능. **반박 데이터**: ① 5-11 14:55 Sentry alert `re-initializing pool (pid=3)` — **pid=3 (Worker B 추정) 자가 회복 정상 작동** ② DB pid 215907 backend_start = Sentry +108ms 일치 (5-07 패턴 재현) ③ 사용자 영향 0 (silent self-recovery 100%) ④ 5-07 측정 시 단일 cluster 5 conn 만 보인 것은 *"한쪽 worker conn 모두 idle disconnect 시점에 측정"* 으로 재해석 가능 (양쪽 worker 모두 자가 회복 능력 보유). **결론**: ADR-025 의 'per-worker 카운터 의도' 가 **실제로 양쪽 worker 모두 작동 중** 임이 입증됨. fcntl lock 가설 (warmup cron 가 단일 worker 만 실행) 도 반박됨 — 양쪽 worker 가 각자 warmup 실행. **사고 단계 감소 정량 입증**: 4-29 (1.5h+ 수동) → 5-04 (40분 수동) → 5-07 (15분 자동 pid=2) → **5-11 (15분 자동 pid=3) ✅ 양쪽 worker 자동화 달성**. **남은 영역 (별 BACKLOG 로 분리)**: 5 conn 만 visible 미스터리 → `OBSERV-DUAL-WORKER-CONN-COEXIST-20260511` (P3, 1~2h) 신규 등록. 본 BACKLOG 의 옵션 A/B/C 해결책은 **불필요** (가설 자체 폐기). **참조 trail**: handoff.md 5-11 14:55 KST 자가 회복 2차 실전 작동 블록 + `DB_POOL_VERIFICATION_QUERIES_20260427.md` V4.1 5-11 trail + ADR-025 보강 (양쪽 worker 자가 회복 입증 추가). **최초 등록**: 2026-05-07 21:46 KST / **가설 폐기 + close 권장**: 2026-05-11 15:42 KST (Twin파파 측 3분 안 2회 측정 + Sentry alert 양쪽 worker pid 분리 입증) |
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
