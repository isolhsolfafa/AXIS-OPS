# AXIS-OPS 백로그

> 마지막 업데이트: 2026-04-22 (알람 장애 4 HOTFIX 완료 + Sprint 55 auto-finalize UX 조사 + 우선순위 로드맵 정리)
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
11. `OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION` — 🟡 P2, 2h (10번 선행)
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
| POST-REVIEW-MIGRATION-049-NOT-APPLIED | 왜 migration 049 가 Railway prod DB 에 적용되지 않았는가 조사 | 🔴 OPEN (S3 조사, HOTFIX-DUP 배포 후 착수) | §12.5 의 4가지 가능성 중 어느 것인지 확정. 교차검토 대상 3파일: (1) Railway Dockerfile / Procfile (2) `migration_runner.py` (Sprint 45 INFRA-1 산출물) (3) 배포 스크립트 + 환경변수. 가설: ① DATABASE_URL 분기 (test vs prod) ② migration_runner 의 idempotent 판정 버그 ③ 047/048 간 runtime 오류로 049 skip ④ Railway volume/layer 캐시. 예상 소요 1~2h. 산출: `AXIS-OPS/POST_MORTEM_MIGRATION_049.md` 또는 `ALERT_SCHEDULER_DIAGNOSIS.md` §13 신설 |
| OBSERV-ALERT-SILENT-FAIL | Phase 1.5 임시 ERROR 로깅 → 영구 반영 + Sentry 정식 연동 | 🔴 OPEN (P1, HOTFIX-DUP 배포 후 1주 내) | Phase 1.5 의 `try/except + log.error + sentry import guard` 패턴을 ① 영구 코드로 승격 ② `sentry-sdk` requirements 정식 추가 ③ release/environment tag + `contexts={"alert": ...}` 구조화 payload ④ sentry alert rule 설정 (1시간 내 5회 이상 발생 시 paging). 재발 방지 필수 방어선. 예상 소요 3~4h |
| OBSERV-MIGRATION-HISTORY-SCHEMA | migration_history 에 success/error_message/checksum 컬럼 추가 | 🟡 OPEN (P2, 중간) | 현재 스키마 3컬럼 (id/filename/executed_at) 으로 실패 관찰 불가. 추가: `success BOOLEAN NOT NULL DEFAULT TRUE` + `error_message TEXT NULL` + `checksum VARCHAR(64) NULL`. migration_runner.py 의 INSERT 절도 동반 수정. checksum 은 migration 파일 내용의 SHA-256 → 배포 간 불일치 감지 가능. 예상 소요 2~3h (migration + runner 수정 + 검증) |
| OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION | 앱 부팅 시 migration 상태 assertion + drift 알림 | 🟡 OPEN (P2, OBSERV-MIGRATION-HISTORY-SCHEMA 후속) | 앱 시작 시 `migrations/` 디렉토리 max filename 번호 vs `migration_history.MAX(id)` 비교. 불일치 시: (a) 환경변수 `STRICT_MIGRATION=1` → `SystemExit(1)` 로 배포 중단 (b) 기본 → Sentry WARNING 알림. test DB 와 prod DB 의 drift 를 부팅 단계에서 즉시 감지. 본건은 2026-04-17~22 장애의 근본 재발 방지책. 예상 소요 2h |
| INFRA-COLLATION-REFRESH | Postgres collation mismatch 경고 해소 | 🟡 MEDIUM (별건) | 별도 이슈로 존재. Sprint 62 이후 배포 창구에서 개별 처리 예정. 본 알람 장애와 무관 |
| UX-SPRINT55-FINALIZE-DIALOG-WARNING | "내 작업만 종료" 마지막 참여자 경고 다이얼로그 (2026-04-22 등록, **1차 보완**) | 🟡 OPEN (P2, 이번 주 내) | **FE only — `frontend/lib/screens/task/task_detail_screen.dart` `_showCompleteDialog()` 확장**. 현장 호소: "내 작업만 종료 눌렀는데 task 가 닫혀서 재참여 불가" (2026-04-22 O/N 6588 GBWS-6978/6979/6980 UTIL_LINE_2 — 이영식/서명환 사례). **원인 확정**: Sprint 55 (3-B) `auto_finalize` — `not finalize` 모드에서도 `_all_workers_completed(task.id)` True 시 task 자동 종료. 버그 아니고 설계대로 동작(progress 실시간 정확도 목적). 다만 "내 작업만 종료" 문구와 실제 동작 괴리 → UX 혼란. **해결**: 다이얼로그 진입 시 현재 참여자의 completion 상태 pre-check → 본인이 partial close 하면 auto-finalize 발동 예정인 경우 **2차 확인 문구** 추가: "⚠️ 현재 다른 참여자 전원이 종료 상태입니다. 당신이 마지막 참여자이므로 이 버튼을 누르면 task 가 자동 종료됩니다. (추후 재개 필요 시 관리자에게 재활성화 요청)". **BE 변경 필요**: `/api/app/tasks/<sn>` 또는 `/api/app/task/<id>` 응답에 `is_last_active_worker: bool` 플래그 추가 (work_start_log 찍힌 전원이 completion_log 있고 본인만 active 상태인지 판정). 작업 소요: FE 30분 + BE 30분 + 테스트 15분 ≈ 1.5h. **오늘 이슈의 80% 를 해소하는 최소 비용 조치**. 관련: `AXIS-OPS/BACKLOG.md` UX-SPRINT55-FINALIZE-DIALOG-WARNING + `backend/app/services/task_service.py` L292-304 auto_finalize 분기 |
| FEAT-SPRINT55-REACTIVATE-HYBRID-ROLE | manager+worker hybrid role 의 PWA 내 재활성화 버튼 (2026-04-22 등록) | 🟡 OPEN (P2, 다음 Sprint) | **FE + BE 연계 — 이영식(manager+worker hybrid) 사용 경험 최적화**. 현재: 이영식(manager) 이 완료된 task 를 다시 열려면 AXIS-VIEW 콘솔 로그인 → task 검색 → 작업재활성화 버튼 클릭 (5분 마찰). **제안**: PWA task 상세 화면 `_buildCompletedBadge()` 옆에 **role 조건부 [재활성화] 버튼** 노출. 조건: `worker.role IN ('MANAGER', 'MECH+MANAGER', 'ELEC+MANAGER', ...)` 인 경우만. 1-tap → 기존 VIEW 재활성화 API (`/admin/tasks/<id>/reactivate` 등) 호출 + audit log 기록 (→ `OBSERV-ADMIN-ACTION-AUDIT` 연계). 버튼 UX: 확인 모달 필수 ("이 작업을 재활성화하시겠습니까? 완료 상태가 해제됩니다."). **비용**: FE 버튼 1개 + 조건부 노출 로직 + BE 엔드포인트 재사용 (신규 0). 작업 소요 반나절. **이득**: 오늘처럼 manager 가 hybrid 로 있는 케이스에서 VIEW 왕복 제거. BE 재활성화 API 가 이미 있는지 먼저 확인 필요 (없으면 별도 Sprint). 관련: `AXIS-OPS/BACKLOG.md` FEAT-SPRINT55-REACTIVATE-HYBRID-ROLE |
| FEAT-SPRINT55-REACTIVATE-REQUEST-FLOW | worker → manager 재활성화 요청 flow (2026-04-22 등록, **2차 보완**) | 🟢 OPEN (P3, 중기) | **BE + FE + VIEW 3-way 구현 — 현장 worker-manager 협업 완전체**. 시나리오: 일반 worker(non-manager)가 완료된 task 에 재참여 필요 → 현재 플로우 "카톡으로 manager 에게 요청 → manager VIEW 로그인 → 수동 재활성화" (마찰 큼). **신규 flow**: (1) PWA 완료 task 카드 → [재개 요청] 버튼 → 사유 입력 모달 → POST `/api/app/task/<id>/reactivate-request` (2) VIEW 상단 알림 배지 + AXIS-VIEW 전용 요청 목록 페이지 (3) manager 1-tap 승인 → 기존 재활성화 API 내부 호출 + 요청자에게 push 알림 (4) 승인 거절 시 사유 회신. **새 테이블**: `task_reactivate_requests (id, task_detail_id, requester_id, reason, status, approver_id, approved_at, rejected_reason, created_at)`. **새 엔드포인트 3개**: POST 요청 생성 / GET 대기 목록 (manager only) / PATCH 승인·거절. **FE**: PWA 재개요청 버튼 + 모달 + 내 요청 상태 조회. VIEW: 요청 목록 페이지 + 알림 widget. **작업 소요**: 1~1.5일 full-stack. **전제**: `FEAT-SPRINT55-REACTIVATE-HYBRID-ROLE` 먼저 배포해서 manager-hybrid 케이스 해결 후 진행 (non-hybrid worker 남은 케이스 대응). `OBSERV-ADMIN-ACTION-AUDIT` 와 통합 (요청/승인 모두 audit log 기록). 관련: `AXIS-OPS/BACKLOG.md` FEAT-SPRINT55-REACTIVATE-REQUEST-FLOW |
| DOC-AXIS-VIEW-REACTIVATE-BUTTON | AXIS-VIEW "작업재활성화" 버튼 존재·영향 범위 문서화 (2026-04-22 등록) | 🟢 OPEN (P3, 30분) | **문서 정리 only**. 2026-04-22 UTIL_LINE_2 조사 중 Q1 의 `first_worker_id=NULL` + started_at 갱신 이력을 미스터리로 접근했다가 Twin파파가 "VIEW 에 재활성화 버튼 존재" 확인해 해소. 다음 번 비슷한 조사 시간 낭비 방지용 기록. **수정 대상**: `AXIS-OPS/memory.md` 상단 "📍 주요 관리 기능" 섹션 신설 or `AXIS-OPS/CLAUDE.md` 관리자 기능 블록. **내용**: (1) AXIS-VIEW 에 task 재활성화 버튼 존재 (위치·권한·호출 API 명시) (2) 재활성화 시 DB 상태 변화: `started_at=NULL, completed_at=NULL, worker_id=NULL, total_pause_minutes 잔존 가능` (3) 기존 start_log/completion_log 는 보존 — 재활성화 이후 새 시작 시 새 row 추가 (4) 재활성화 가 의도된 기능임 (우회가 아님) (5) 재활성화 이력은 현재 audit log 부재 → `OBSERV-ADMIN-ACTION-AUDIT` 연계. 예상 소요 30분. 관련: `AXIS-OPS/BACKLOG.md` DOC-AXIS-VIEW-REACTIVATE-BUTTON |
| OBSERV-ADMIN-ACTION-AUDIT | 관리자 액션 audit log 테이블 도입 (2026-04-22 등록) | 🟡 OPEN (P2, 독립 Sprint) | **BE 신규 인프라 — 관찰성 gap 해소**. 2026-04-22 UTIL_LINE_2 조사 중 Q7 `SELECT * FROM admin_audit_log` 실행 시 `relation "admin_audit_log" does not exist` (42P01) 에러로 확인: **AXIS-VIEW 재활성화 등 admin destructive/corrective 액션에 audit 기록 인프라 부재**. 누가 언제 어떤 task 를 재활성화했는지 DB 추적 불가. **스키마 초안**: `CREATE TABLE admin_audit_log (id BIGSERIAL PK, actor_user_id INT NOT NULL, actor_email TEXT, action TEXT NOT NULL, target_table TEXT NOT NULL, target_id BIGINT NOT NULL, before_state JSONB, after_state JSONB, reason TEXT, ip_address INET, user_agent TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())` + index `(target_table, target_id)` / `(actor_user_id, created_at DESC)`. **적용 범위**: (1) task 재활성화 (2) task 강제 종료 (HOTFIX-04 force-close) (3) worker 강제 로그아웃 (4) pause 강제 해제 (5) admin_settings 변경 (6) role 승격/강등 etc. **연동 방식**: Flask `before_request` + `after_request` middleware 에서 자동 snapshot 기록 (해당 blueprint 범위: `/admin/*` mutation 라우트). 수동 호출 불필요. **수반 이득**: (i) 향후 데이터 미스터리 조사 시간 5~10분 → 30초 (ii) 다중 관리자 환경 책임 추적 (compliance) (iii) Sprint 45 INFRA-1 migration runner 관찰성 부재와 동일 유형의 blind spot 해소. **작업 소요**: migration 1개 + middleware ~30~50줄 + 기존 admin 라우트 점진 적용 → 초기 구현 2h + 전 admin 라우트 적용 추가 2h. **관련 BACKLOG**: `FEAT-SPRINT55-REACTIVATE-HYBRID-ROLE` / `FEAT-SPRINT55-REACTIVATE-REQUEST-FLOW` 배포 전 선행 권고. 오늘 조사 근거: `AXIS-OPS/BACKLOG.md` OBSERV-ADMIN-ACTION-AUDIT |
| HOTFIX-ALERT-SCHEDULER-DELIVERY-20260422 | scheduler 3곳 target_worker_id 표준 패턴 적용 + 배치 dedupe (M2) | ✅ 🟢 COMPLETED (2026-04-22, v2.9.11) | **5일 알람 장애 최종 복구**. scheduler_service.py 3곳 (RELAY_ORPHAN L884 + TASK_NOT_STARTED L967 + CHECKLIST_DONE_TASK_OPEN L1044) 이 target_worker_id 미지정 → role_<VALUE> broadcast → role_TMS room 구독자 0 → 52건 완전 undelivered. 수정: `_resolve_managers_for_category` 헬퍼 도입 (task_service.py L571 표준 패턴) + 배치 dedupe (target_worker_id IS NOT NULL 필터로 legacy 69건 간섭 차단). +100/-52 LOC. Codex 교차검증 M1 수용 + A 6건 BACKLOG 이관. pytest 129 passed / 7 skipped / 회귀 0건. 관련: `AXIS-OPS/ALERT_SCHEDULER_DIAGNOSIS.md` §11.14.7 / `AXIS-OPS/AGENT_TEAM_LAUNCH.md` HOTFIX-ALERT-SCHEDULER-DELIVERY-20260422 섹션 |
| OBSERV-RAILWAY-LOG-LEVEL-MAPPING | gunicorn stderr → Railway 'error' 태깅 수정 (2026-04-22 등록) | 🔴 OPEN (P1, OBSERV-ALERT-SILENT-FAIL blocker) | Python `logger.info()` 호출한 모든 로그가 Railway UI 에 `level: error` 로 태깅됨. apscheduler 내장 logger (apscheduler.scheduler) 도 동일. 원인: Python `logging.basicConfig` 기본 stderr 출력 + Railway 수집 에이전트 `stderr → error` 매핑. **영향**: Sentry alert rule 에 `level=error` 필터 설정 시 정상 INFO 도 폭주 → 실제 에러 구분 불가. **해결안**: Procfile 에 `--access-logfile=- --error-logfile=- --log-level=info` 추가 + Python `logging.basicConfig(stream=sys.stdout)` 명시. 30~45분. **전제**: `OBSERV-ALERT-SILENT-FAIL` Sentry 연동 선행 필수 조건. 오늘 발견 근거: `Scheduler initialized with 11 jobs` / `file lock acquired/held` 등 INFO 메시지가 Railway 대시보드에서 Error 뱃지로 표시됨 |
| FIX-LEGACY-ALERT-TMS-DELIVERY | 4-17~22 기간 legacy 69건 복구 여부 결정 (2026-04-22 등록) | 🟡 OPEN (P3, 옵션) | HOTFIX-ALERT-SCHEDULER-DELIVERY 이후 새 알람은 정상 delivery. 다만 기존 `target_role='TMS'` 52건 + `target_role='elec_partner/mech_partner/module_outsourcing'` 17건 = **69건 legacy 는 여전히 target_worker_id=NULL 상태로 존재**. 복구 옵션: (a) 각 알람을 관리자별로 복제 INSERT → 과거 알람 소급 notification (사용자 혼란 가능) (b) skip — 대개 1주 이상 지난 알람이라 actionable 정보 아님. **권장: (b) skip**. 다만 legacy 가 존재하는 한 HOTFIX Sprint 설계서 § Codex M2 지적처럼 다음 migration 시에도 유사 dedupe 간섭 가능 → 24h/7d/3d window 지나면 자연 소거 |
| REFACTOR-SCHEDULER-SPLIT | scheduler_service.py 파일 분할 (2026-04-22 등록) | 🟡 OPEN (P2, 다음 Sprint) | 현재 scheduler_service.py ~1090 LOC (HOTFIX 후). CLAUDE.md L491 1단계 기준 "필수 분할 800줄" 초과 + "God File 1200줄" 근접. 분할 제안: (1) `scheduler_service.py` (init/start/stop + 스케줄러 라이프사이클) (2) `scheduler_alerts.py` (11 job 함수) (3) `scheduler_helpers.py` (`_resolve_managers_for_category` 등 헬퍼). 예상 LOC: 200 + 600 + 100. **전제**: 리팩토링 7원칙 (CLAUDE.md L586) 엄수 — 기능 변경 0, pytest Before/After GREEN 증명, git 태그 `pre-refactor-scheduler-split`. 작업 소요 4~6h. 관련: `AGENT_TEAM_LAUNCH.md` HOTFIX-ALERT-SCHEDULER-DELIVERY § Codex A4 |
| TEST-ALERT-DELIVERY-E2E | 알람 delivery WebSocket E2E 통합 테스트 (2026-04-22 등록) | 🟡 OPEN (P2, 다음 Sprint) | 본 장애가 pytest GREEN 에서도 운영에서 undelivered 였던 근본 원인: 기존 테스트는 DB INSERT 만 검증하고 **FE delivery 검증 부재** (test_alert_all20_verify TC-AL20-07/08). 신규 통합 테스트: (1) WebSocket mock 등록 (`role_<X>` 또는 `worker_<id>` room) (2) alert 생성 트리거 (3) emit_new_alert/emit_process_alert 호출 확인 (4) mock room 에 message 도달 여부 assertion. pytest fixture 로 WebSocket 레지스트리 주입. 3~5 TC 신규. 작업 소요 3~4h. 관련: Codex A6 |
| TEST-SCHEDULER-EMPTY-MANAGERS | scheduler PI/QI/SI 엣지 empty-manager 테스트 (2026-04-22 등록) | 🟢 OPEN (P3, 1h) | Codex A3 지적 — `_resolve_managers_for_category` 가 PI/QI/SI 로 `get_managers_for_role` 호출 시 빈 리스트 반환 가능성 (관리자 미등록 / 비활성). 현재 코드는 for 루프로 safe skip 하지만 명시적 테스트 필요. TC: (1) role='PI' managers=[] 상황에서 RELAY_ORPHAN 생성 → 0건 INSERT (2) role='QI' managers=[1] 정상 1건. `test_scheduler.py` 에 2~3 TC 추가. 작업 소요 1h |
| BUG-DURATION-VALIDATOR-API-FIELD | `/api/app/work/complete` 응답에 `duration_warnings` 필드 누락 (2026-04-22 등록) | 🟡 OPEN (P2, 독립 Sprint) | **⚠️ Codex 합의 미실행 항목**: pytest 실패 `test_duration_validator.py::TestReverseDuration::test_reverse_completion` 이 HOTFIX-ALERT-SCHEDULER-DELIVERY 세션 중 발견. Claude 단독 "본 HOTFIX 와 무관한 기존 failing" 으로 판단 후 제외 → CLAUDE.md AI 검증 워크플로우 ⑦단계 (실패 → Codex 합의 후 수정) 위반. **착수 전 필수**: Codex `/codex:rescue` 호출해서 (a) "기존 별건" 재확인 (b) M/A 라벨 확정 (c) 본 BUG 의 실제 원인 분석 (HOTFIX-04 옵션 C' 이후 `close_reason/closed_by/closed_by_name` 3필드 추가했지만 `duration_warnings` 누락 가정). 작업 소요: Codex 합의 30분 + 수정 30~60분. 관련: CLAUDE.md ⑦ 강제 절차 (2026-04-22 추가) |
| POST-REVIEW-HOTFIX-ALERT-SCHEDULER-DELIVERY-20260422 | HOTFIX-ALERT-SCHEDULER-DELIVERY 배포 사후 Codex 교차검토 (2026-04-22 등록) | 🔴 OPEN (S2, 7일 이내 필수) | CLAUDE.md § 🚨 긴급 HOTFIX 예외 조항 S2 적용 — Opus 단독 리뷰 후 배포 → 7일 이내 Codex 사후 검토 의무. 검토 범위: ① `_resolve_managers_for_category` 헬퍼의 정확성 ② 3곳 배치 dedupe 쿼리 index 활용 효율 (`idx_alert_logs_dedupe`) ③ for manager_id 루프의 N+1 query 여부 ④ Codex M1 (Item 2) 해결 완결성 ⑤ 배포 후 48h 관찰 데이터 (실제 delivery 재개 + legacy 69건 수렴 곡선). 예상 소요 30분 |
| BIZ-KPI-SHIPPING-01 | 경영 대시보드 출하 KPI 설계 (이행률·정합성, 2026-04-23 등록) | 🟢 DRAFT (P3, App 베타 100% 전환 후 착수 검토) | **추상 단계 / 확정 아님 / 정리만 보존**. 배경: OPS App 전환기 (기존 PDA/수기 → App 베타). 이행률·정합성 같은 경영 지표는 App 전환율이 충분히 올라간 뒤 의미 있는 해석 가능. **선행**: Sprint 62-BE v2.2 (데이터 공급 인프라 — `shipped_plan`/`shipped_actual`/`shipped_ops` 3필드 raw) 배포 완료. **검토 필요 항목** (Sprint 착수 시 확정): ① 이행률 정의 — `actual/plan` 단순 vs `actual/(plan 만기도래)` 정교 ② 정합성 지표 공개 범위 — 공장 카드 / Admin 전용 / 임계치 알림 ③ `plan_count` 정의 — si_completed 조건 유무 ④ 경영 대시보드 화면 위치 — 기존 공장 대시보드 확장 vs 별도 Exec 뷰 ⑤ 베타 전환 스케줄 반영 — 어느 모델/협력사부터 단계적 100%. **3계층 데이터 구조**: 계획층(`ship_plan_date` ETL) → 실적층(`actual_ship_date` Teams 수기 + cron) → 앱층(`SI_SHIPMENT.completed_at` OPS 앱 베타). **지표 2종** (추후 확정): `fulfillment_rate = shipped_actual / shipped_plan × 100` (이행률) / `app_coverage_rate = shipped_ops / shipped_actual × 100` (베타 전환 커버리지). **현재 실측 (2026-04-23 기준 이번 주)**: plan=0 / actual=23 / ops=0. **주의**: 자동 UNION 합산(`shipped_union`) 은 폐기 — 3개 소스는 독립 비교용. 관련: `AGENT_TEAM_LAUNCH.md` Sprint 62-BE v2.2 섹션 |
| POST-REVIEW-SPRINT-62-BE-V2.2-20260423 | Sprint 62-BE v2.2 배포 사후 Codex 교차검토 (2026-04-23 등록) | ✅ **PARTIAL COMPLETED** (Q1/Q3 해소, Q5 관찰형 유지) | **Q1 (migration 050 Railway 적용)**: ✅ 2026-04-23 13:38 KST 수동 적용 + `migration_history` 기록 + `pg_indexes` 3종 확인. **Q3 EXPLAIN ANALYZE 실측 (2026-04-23)**: ✅ ② `idx_product_info_actual_ship_date` 사용 (Bitmap Index Scan 0.071ms) / ④ `idx_product_info_finishing_plan_end` 사용 (Bitmap Index Scan 0.127ms, weekly-kpi 메인 쿼리) / ③ `idx_app_task_details_completed_at` 기존 인덱스 사용 (0.092ms). ① `idx_product_info_ship_plan_date` 는 현 쿼리 패턴에서 planner가 `completion_status` Seq Scan + serial_number Nested Loop 선택 → "never executed" (si_completed=TRUE 0건이라 다른 전략이 더 효율적). **sub-ms 대역** 전체 쿼리 매우 빠름. Q3 A **완전 해소**. **Q5 (네이밍 부채 모니터링)**: ⏸ 관찰형 — `pipeline.shipped` vs `shipped_plan` FE 혼동 사례 7일 관찰 중. BIZ-KPI-SHIPPING-01 착수 시 final 네이밍 결정. **Q3 Advisory**: `idx_product_info_ship_plan_date` 현재 미사용이나 향후 si_completed=TRUE 비율 증가 시 자동 활성화 가능, 삭제 불필요 (공간 무시). **v2.10.1 교정** 포함 (weekly-kpi WHERE ship_plan_date→finishing_plan_end). 관련: `AGENT_TEAM_LAUNCH.md` Sprint 62-BE v2.2 섹션 / handoff.md |

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
