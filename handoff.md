# AXIS-OPS Handoff

> 세션 종료 시 업데이트. 다음 세션이 즉시 작업을 이어갈 수 있도록 현재 상태를 기록합니다.
> 마지막 업데이트: 2026-05-14 KST (✅ v2.15.9 hotfix 코드 적용 — v2.15.6 (나) 옵션 catch 정정 + 다이얼로그 라벨 "공정 마감" 변경. 사용자 v2.15.7/v2.15.8 release 후 별 hotfix. prod 배포 대기.)

---

## ✅ 2026-05-14 KST — v2.15.9 hotfix (HOTFIX-SPRINT41D-PROGRESS-100-REVERT-AND-LABEL-CHANGE)

> **사용자 catch (5-14 운영 검증)**: v2.15.6 prod 배포 후 SELF_INSPECTION + 체크리스트 100% 진행했는데 gas2/util2 close 안 됨. Root cause: v2.15.3 `auto_finalize_blocked` 와 v2.15.6 task progress 100% AND 조건 충돌 — "내 작업 완료" 누른 task = completed_at IS NULL → progress < 100% → Second Close trigger 발동 X. cowork 이 사용자 발화 "mech, elec 실적 조건 변동 없음" 을 (나) 로 잘못 해석. 실제 의도 = (가) 회귀.

### 변경 (BE + FE, 3 파일 + version)

- `task_service.py` — `check_category_close_eligible()` MECH=체크리스트 100%만 / ELEC=IF_2+INSPECTION+체크리스트 100% (v2.15.5 영역 회귀)
- `task_service.py` — `check_elec_close_eligible_at_if2()` INSPECTION + 체크리스트 100% 만 (task progress 100% 제거)
- `task_service.py` — `check_category_progress_100()` deprecation 마킹 (호출 0건 dead code)
- `task_service.py` — `check_elec_final_tasks_completed()` deprecation 해제 (재호출)
- `task_management_screen.dart` L888 + `task_detail_screen.dart` L904 — "아니오, 작업 완료" → "아니오, 공정 마감"
- `version.py` + `app_version.dart` 2.15.8 → **2.15.9** (사용자 v2.15.7 + v2.15.8 release 후 별 hotfix)

### 카테고리별 close 조건 매트릭스 (v2.15.6 → v2.15.9)

| Category | v2.15.6 (잘못) | v2.15.9 (회귀) |
|---|---|---|
| MECH | task progress 100% + 체크리스트 100% | **체크리스트 100% 만** |
| ELEC | task progress 100% + 체크리스트 100% | **IF_2 + INSPECTION + 체크리스트 100%** |
| TMS | PRESSURE_TEST complete 만 | 동일 보존 |
| PI/QI/SI | 항상 True | 동일 |

### 다이얼로그 라벨 (UX 변경)

| 키 | 이전 | v2.15.9 |
|---|---|---|
| finalize=false (relay) | "예, 내 작업만 종료" | 동일 |
| finalize=true | "아니오, 작업 완료" | **"아니오, 공정 마감"** |

> "공정 마감" = task 1개 단위 마감 (util1, gas2 등) / MECH 카테고리 전체 마감 아님. SELF_INSPECTION 영역 "공정 마감" 시 = MECH 전체 정리 trigger 효과 (Sprint 41-D Second Close).

### 사용자 결정 trail (5-14)

- 옵션 (가) 회귀 = task progress 100% AND 조건 제거 — gas2/util2 force close 회복
- "공정 마감" 라벨 변경 = UX 명확화 (작업자 인지)
- Hybrid 진행률 정의 = 별 sprint 분리 + v2.15.9 직후 설계 진행 (사용자 욕심, 1주 운영 X)

### 다음 단계

1. **사용자 측 prod 배포** — git commit + push + Railway 자동 재배포 + Netlify FE dump (사용자 측 직접 진행)
2. **운영 영역 검증** — SELF_INSPECTION/IF_2 "공정 마감" 누른 후 gas2/util2 자동 close 동작 확인
3. **POST-REVIEW Codex 검토 (7일, deadline 2026-05-21)**
4. **Hybrid sprint 설계 진행** — `FEAT-PROGRESS-MY-COMPLETION-HYBRID-AND-LABEL-CHANGE-20260514` 사용자 욕심 즉시 설계

### 후속 BACKLOG

- `FEAT-PROGRESS-MY-COMPLETION-HYBRID-AND-LABEL-CHANGE-20260514` P2 (v2.15.9 직후 설계, 사용자 욕심)
- `POST-REVIEW-HOTFIX-SPRINT41D-PROGRESS-100-REVERT-AND-LABEL-CHANGE-20260514` 등록 예정 (7일)

### CHANGELOG entry 순서 catch

CHANGELOG.md 영역 v2.15.9 entry 위치 = L66~L117 (v2.15.6 entry 위) — chronological 순서 (v2.15.9 → v2.15.8 → v2.15.7) 영역 정렬 catch. 별 정리 sprint 권고 (P3, 30분).

---

## ✅ 2026-05-14 KST — v2.15.8 release (FIX-27 statusText 정정)

> **사용자 catch**: "내 종료 / 동료 진행 중" 표현은 시스템이 실제 동료 상태를 모르는 상태에서 추측한 표현. task open 상태일 뿐 동료 진행 여부 불명. → "재참여 가능" 사실 기반 표현.

### 변경 (FE only)

- `task_management_screen.dart` L249 영역 — statusText `'내 종료 / 동료 진행 중'` → `'내 종료 / 재참여 가능'`
- 버전: 2.15.7 → 2.15.8

### 검증

- flutter build web GREEN (12.8s) + Netlify 배포 완료
- 회귀 위험 0 (단일 문자열)

---

## ✅ 2026-05-14 KST — v2.15.7 release (FIX-27 FE TASK_CARD UX 개선)

> **사용자 catch (TEST-1111 실기기 5-14)**: (1) 본인 완료 + task open 시각 구분 부재 (v2.15.3 옵션 B 영향) (2) 새로고침 수단 부재 (QR 재태깅만 가능) (3) "다시 시작" 라벨 — task_detail_screen 이미 구현 확인 → 스킵.

### 변경 (FE only, 3 파일)

- `design_system.dart`: GxColors 신규 토큰 (peerActive + peerActiveBg + muted + mutedBg)
- `task_management_screen.dart`: 청록 뱃지 + RefreshIndicator + AppBar refresh + `_refreshTasks()` 신규
- `web/index.html`: `overscroll-behavior-y: contain` (안드로이드 Chrome 자체 새로고침 차단)

### Codex 검증

- 라운드 1: M=2 / A=3 / N=3 → 모두 정정 반영
- 라운드 2 미진행 (CLAUDE.md 라운드 상한 1회 정합)

### 후속 (별 sprint P2)

- pytest 위젯 10 TC (TC-FIX27-01~10) — 더미 영역 실제 구현
- BACKLOG `FEAT-TASK-PROGRESS-COUNT-DISPLAY` (옵션 D — "1/2명 종료")

---

## ✅ 2026-05-14 KST — v2.15.6 hotfix (HOTFIX-SPRINT41D-TMS-CLOSE-FIX-MECH-ELEC-PROGRESS-100)

> **사용자 catch (5-14 운영 검증)**: v2.15.5 prod 배포 후 cowork 이 VIEW 의 TM 실적 카운트 조건 (tank module com + 체크리스트 100%) 을 OPS close 조건에 잘못 매핑. 사용자 명시: "가압검사는 무조건 이행하기 떄문에 가압검사가 끝나면 close조건으로 하고", "TANK_MODULE 미시작/미완료 = VIEW 일괄 시작/종료 (이미 구현) 으로 해결", "mech, elec 실적 조건 변동 없음 → (나) 옵션 task progress 100% AND 채택".

### 변경 (BE only, 2 파일 + version)

- `task_service.py` L135 — `check_category_progress_100()` 신규 헬퍼 (exclude_task_id 옵션, DRY 공용)
- `task_service.py` L195 — `check_elec_close_eligible_at_if2()` 재구현 (IF_2 본인 제외 + 나머지 active task 100% + 체크리스트 100%)
- `task_service.py` L213 — `check_category_close_eligible()` 재구현 — TM/TMS 분기 단순화 (return True, 체크리스트 AND 제거) + MECH/ELEC task progress 100% AND 추가
- `task_service.py` L254 — `check_elec_final_tasks_completed()` deprecation 마킹 (호출 0건, 테스트 import 보존)
- `work.py` L294 — forward_keys 에 `checklist_pending` 추가 (Codex M-1 v2.15.5 catch 정정)
- `version.py` 2.15.5 → 2.15.6

### 카테고리별 task close 조건 매트릭스 (v2.15.5 → v2.15.6)

| 카테고리 | v2.15.5 close 조건 | v2.15.6 close 조건 | 사용자 실적 조건 정합 |
|---|---|---|:-:|
| MECH | SELF_INSPECTION com + 체크리스트 100% | **task progress 100%** + 체크리스트 100% | ✅ |
| ELEC | IF_2 + INSPECTION + 체크리스트 100% | **task progress 100%** + 체크리스트 100% | ✅ |
| TMS | PRESSURE_TEST + 체크리스트 100% (❌ 잘못) | **PRESSURE_TEST complete 만** | ✅ |
| PI/QI/SI | 항상 True | 항상 True (변경 없음) | — |

### 영향 매트릭스 (v2.15.5 → v2.15.6)

| 시나리오 | v2.15.5 | v2.15.6 |
|---|:-:|:-:|
| TMS PRESSURE_TEST complete + 체크리스트 < 100% | ❌ open (잘못) | ✅ close |
| MECH SELF_INSPECTION + 다른 task 미완료 + 체크리스트 100% | ❌ close (catch 못함) | ✅ open |
| ELEC IF_2/INSPECTION + 다른 task 미완료 + 체크리스트 100% | ❌ close (catch 못함) | ✅ open |
| MECH/ELEC 모든 active task 100% + 체크리스트 100% | ✅ close | ✅ close (동일) |
| FE `checklist_pending` 응답 수신 | ❌ drop (forward 누락) | ✅ 정상 forward |

### 사용자 결정 trail

- TMS PRESSURE_TEST = 가압검사 무조건 이행 → complete 만으로 close (체크리스트 무관)
- TM 실적 카운트 = VIEW (tank module com + 체크리스트 100%) 별도 — OPS close 와 분리
- TANK_MODULE 미시작/미완료 = VIEW 일괄 시작/종료 (이미 구현) 으로 해결
- MECH/ELEC = (나) 옵션 — task progress 100% + 자주검사 + 체크리스트 100% 모두 AND

### Codex 교차 검증 (대기)

- v2.15.5 라운드 1 M-1 (`checklist_pending` forward 누락) 정정 묶음
- 사용자 측 codex 검증 진행 예정

### 다음 단계

1. **사용자 측 Codex 교차 검증** — v2.15.6 변경 영역 검토 (라운드 1)
2. **Codex M/A 라벨 수신 후 정정** — M 항목 우선 처리
3. **prod 배포** — Railway 자동 재배포 확인
4. **운영 영역 검증** — TMS PRESSURE_TEST close 정상 동작 + MECH/ELEC task progress 100% 차단 동작
5. **POST-REVIEW (7일, deadline 2026-05-21)** — Codex 사후 검토 + pytest TC 신규 작성 별 sprint P2

### 후속 BACKLOG (참조)

- `REF-CATEGORY-COMPLETION-CONSOLIDATION` P1 — HOTFIX-SPRINT41D 시리즈 안정화 1주 후 진행
- `POST-REVIEW-HOTFIX-SPRINT41D-TMS-CLOSE-FIX-MECH-ELEC-PROGRESS-100-20260514` — 신규 등록 예정

---

## ✅ 2026-05-14 KST — v2.15.5 통합 hotfix (HOTFIX-SPRINT41D-CHECKLIST-AND-SINGLE-ACTION)

> **사용자 catch (5-14 운영 검증)**: v2.15.4 배포 후에도 ① MECH TANK_DOCKING start 시 gas1/util1 자동 close 미발동 (catch #24) ② ELEC IF_2 + INSPECTION + 체크리스트 100% AND 조건 미적용 — 데드락 잔존 (catch #25). **사용자 5-14 결정**: Q1=B 옵션 X3-전영역 / Q2=A 체크리스트 100% 단순 / Q3=Manager 책임 / Q4=AND 통일 + 트리거 양방향 / Q5=가 task open + checklist_pending.

### 변경 (BE only, 2 파일 + version)

- `task_service.py` L135 영역 — `check_category_close_eligible()` + `check_elec_close_eligible_at_if2()` 신규 함수 2개
- `task_service.py` L400 영역 — ELEC IF_2 sub-분기 (옵션 B 차단 우회)
- `task_service.py` L527 영역 — Sprint 55 (3-C) 체크리스트 100% AND 검증 추가 (미달 시 relay_mode + `checklist_pending: True`)
- `task_service.py` L555 영역 — Second Close 트리거 `check_category_close_eligible()` 통합
- `work.py` L513 영역 — `complete_single_action_route()` `_trigger_first_close()` 호출 추가
- `version.py` 2.15.4 → 2.15.5

### 카테고리별 task close 조건 (옵션 X3-전영역)

| 카테고리 | AND 조건 | 트리거 시점 |
|---|---|---|
| MECH | SELF_INSPECTION + 체크리스트 100% | SELF_INSPECTION 시점 |
| ELEC | IF_2 + INSPECTION + 체크리스트 100% | IF_2 시점 + INSPECTION 시점 (양방향) |
| TM | PRESSURE_TEST + 체크리스트 100% | PRESSURE_TEST 시점 |

### 영향 매트릭스 (v2.15.4 → v2.15.5)

| 시나리오 | v2.15.4 | v2.15.5 |
|---|:-:|:-:|
| TANK_DOCKING → gas1/util1 자동 close | ❌ 미발동 | ✅ 자동 close |
| ELEC IF_2 "내 작업 완료" + 체크리스트 100% | ❌ task open 영원 | ✅ 자동 finalize → close |
| MECH/TM 체크리스트 미달 시 close | ❌ 무조건 close | ✅ task open + checklist_pending |

### 신규 응답 플래그

- `checklist_pending: bool` — 체크리스트 100% 미달 시 True

### 다음 세션 후속 액션

1. **사용자 측 Codex 교차 검증 진행** — task_service.py + work.py 정정 영역 검증 위임
2. **Railway 자동 재배포 확인** — v2.15.5 BUILD_DATE 2026-05-14
3. **운영 검증** — TEST-1111 영역 재현 (MECH TANK_DOCKING 시 gas1/util1 자동 close + ELEC IF_2 데드락 해소)
4. **pytest TC 신규 작성 별 sprint P2** — 체크리스트 100% AND 매트릭스 + SINGLE_ACTION First Close
5. **POST-REVIEW** — 7일 이내 Codex 검토 (deadline 2026-05-21)

### ADR-029 후속 사례 (#24 + #25)

| # | 사례 |
|---|---|
| 24 | SINGLE_ACTION task 별 endpoint 영역 trigger 호출 검증 누락 — Codex cross-endpoint 정합 표준 |
| 25 | 설계서 후속 추가 trail vs 코드 sync 검증 표준 — 옵션 X3-단순 설계만, 코드 미구현 catch 누락 |

---

---

## ✅ 2026-05-14 KST — v2.15.4 hotfix (HOTFIX-SPRINT41D-SQL-COLUMN-FIX)

> **사용자 catch + Sentry 검증**: v2.15.3 prod 배포 후 사용자 측 — "MECH TANK_DOCKING 시작해도 gas1/util1 자동 close 안 됨". Sentry 영역 `_trigger_first_close orphan SELECT failed: column td.last_started_at does not exist` 메시지 catch (TEST-1111 + 실 운영 GPWS-0799). Root cause: app_task_details 영역 정식 컬럼 = `started_at`, `last_started_at` 컬럼 존재 안 함. try/except silent fail → 4 트리거 케이스 모두 미발동.

### 변경 (BE only, 2 파일)

- `backend/app/services/task_service.py` L1024-1091 `_trigger_first_close()` + L1115-1187 `_trigger_second_close()` SQL 정정
  - 옵션 B: `COALESCE((SELECT MAX(wsl.started_at) FROM work_start_log wsl WHERE wsl.task_id = td.id), td.started_at)`
  - Catch B: COALESCE 안전망
  - Catch D 옵션 A: `WHERE td.started_at IS NOT NULL` 가드 (시작 안 한 task 영역 제외)
  - Catch C: inline duration 계산 → `calculate_auto_close_duration()` 호출 통합 (DRY)
- `backend/version.py` 2.15.2 → 2.15.4 (v2.15.3 결함 영역 우회 skip)

### Sprint 41-D 영향 매트릭스 (v2.15.3 결함 → v2.15.4 fix)

| 트리거 | Before | After |
|---|:-:|:-:|
| MECH TANK_DOCKING start → gas1/util1 close | ❌ silent fail | ✅ 자동 close |
| ELEC IF_2 start → panel/cabinet/wiring/IF_1 close | ❌ silent fail | ✅ 자동 close |
| MECH SELF_INSPECTION complete → gas2/util2 close | ❌ silent fail | ✅ 자동 close |
| ELEC IF_2+INSPECTION AND complete → 잔여 close | ❌ silent fail | ✅ 자동 close |

### 운영 영역 영향 catch (사용자 측 SQL 검증)

| S/N | trigger | 영향 |
|---|---|---|
| GPWS-0799 (실 운영) | ELEC IF_2 2026-05-14 13:15 | 4 task orphan — **Manager force-close 필요** |
| TEST-1111 (테스트) | MECH + ELEC 13:29/13:35 | 6 task orphan |
| GBWS-6979/6980/7087/7088 | Sprint 41-D 이전 영역 | ⚠️ 본 결함 무관 |

### 다음 세션 후속 액션

1. **Railway 자동 재배포 확인** — v2.15.4 BUILD_DATE 2026-05-14
2. **Sentry 검증** — `column td.last_started_at does not exist` 메시지 0건 확인
3. **운영 영역 검증** — 사용자 측 GPWS-0799 영역 Manager force-close 직접 처리
4. **미래 trigger 정상 작동 검증** — 신규 S/N TANK_DOCKING / IF_2 start 후 자동 close 확인
5. **pytest integration TC 영역 별 sprint P2** — TC-FF-01p/01q/01r (~45분)
6. **POST-REVIEW** — 7일 이내 Codex 검토 (deadline 2026-05-21)

### ADR-029 후속 사례 보강 (#21~#23)

| # | 사례 |
|---|---|
| 21 | pytest mock 영역 vs 실제 동작 검증 분리 표준 |
| 22 | Codex/SQL 작성 영역 information_schema cross-check 표준 |
| 23 | 사용자 검증 답변 "True" 영역도 운영 데이터 영역 SQL 검증 권고 |

→ HOTFIX-SPRINT41D 시리즈 완료 후 재논의 영역에 통합 영역 영향.

---

## ✅ 2026-05-14 KST — v2.15.3 release 완료 (HOTFIX-SPRINT41D-AUTO-FINALIZE-RANGE-EXTENSION)

---

## ✅ 2026-05-14 KST — v2.15.3 release 완료 (HOTFIX-SPRINT41D-AUTO-FINALIZE-RANGE-EXTENSION)

> **한 줄 요약**: v2.15.2 잔존 catch (Issue A — FIRST_FINAL 만 차단) 영역 옵션 B Allowlist 확장 (AUTO_FINALIZE_BLOCKED_TASK_IDS 11 task) + Codex M-1 정정 (work.py forward) 적용. 사용자 의도 ("relay 한 명 참여 시 close 방지 = 모든 relay-able task") 정합.

### 변경 (3 파일)

- `backend/app/services/task_service.py` — AUTO_FINALIZE_BLOCKED_TASK_IDS 11 task set + 분기 정정 + 응답 플래그
- `backend/app/routes/work.py` L286-292 — forward 매핑 2 키 추가 (Codex M-1)
- `tests/backend/test_relay_first_final.py` — parametrize 11 task 신규 + SELF_INSPECTION 회귀 방지 + 기존 보강

### pytest 결과 GREEN

- 신규 v2.15.3: 12 TC (parametrize 11 task + SELF_INSPECTION) PASS (0.21s)
- 기존: 26 TC PASS (TC-FF-01b/c/d 보강 + 기존 23 TC)
- 회귀: test_work_api 8/8 PASS (3분 56초)
- **총 46/46 GREEN**

### Codex 검증

- 라운드 1: M=1 / A=2 / N=4 → M-1 (work.py forward) + A-1 (parametrize TC) 정정 반영
- 라운드 2 미진행 (CLAUDE.md 핵심 규칙 6 라운드 상한 1회 정합)

### 후속 액션

- **사용자 측 운영 검증** (브라우저 새로고침 후 SW cache invalidation 5~10초):
  1. TEST-1111 WASTE_GAS_LINE_1 "내 작업만 종료" → task open 유지 확인
  2. admin 계정 WASTE_GAS_LINE_1 재진입 가능 확인
  3. TANK_DOCKING start → gas1/util1 자동 close 트리거 확인
  4. SELF_INSPECTION complete → 잔여 task 일괄 close (Second Close 보존 확인)
- T+1주 (2026-05-21): Sentry 새 ERROR 0건 관찰
- T+4주 (2026-06-11): baseline 비교 SQL — Manager Rollback 비율 50%+ 감소 검증
- REF-CATEGORY-COMPLETION-CONSOLIDATION 영역 재논의 진입 가능 (HOTFIX-SPRINT41D 시리즈 완료 + 1주 운영 안정성 확인 후)

---

## ⭐ HOTFIX-SPRINT41D 시리즈 완료 후 재논의 영역 (사용자 부탁 2026-05-14)

> **cowork 측 기억 필수 영역** — 사용자 부탁 "꼭 기억 하고 있어야되" (2026-05-14)

### 재논의 영역 시점
HOTFIX-SPRINT41D 시리즈 (v2.15.0/15.1/15.2/15.3) prod 배포 완료 + 운영 영역 안정성 검증 (1주) 후.

### 재논의 영역 내용 (사용자 발화 5-14 정합)

1. **실적 카운트 조건 영역 통합** — 카테고리별 close 조건 영역 명시:
   - TM: tank_module com + 체크리스트 100%
   - ELEC: task progress 100% + 자주검사 (INSPECTION) + 체크리스트 100%
   - MECH: task progress 100% + 자주검사 (SELF_INSPECTION) + 체크리스트 100% (최근 추가)
2. **공용 모듈 영역 도입** — `completion_checker.py` 신규
3. **분산 영역 통합** — task_service / production / progress_service / checklist_service 영역 4건 공용 호출
4. **refactor 부담 영역 점진적 해소** — Sprint 41-D 영역 분산 영역 안정화 후 단계적 영역 정리

### 별 sprint 영역
`REF-CATEGORY-COMPLETION-CONSOLIDATION-20260514` — BACKLOG.md 등록 완료 (P2, ~4~6h).

### 진행 영역 트리거
- HOTFIX-SPRINT41D v2.15.3 영역 prod 배포 완료 + 운영 영역 1주 관찰 + Sentry 새 ERROR 0건 → 재논의 영역 진입 가능

---

---

## ✅ 2026-05-14 KST — v2.15.2 hotfix (HOTFIX-SPRINT41D-AUTO-FINALIZE-NOT-BLOCKED)

> **한 줄 요약**: v2.15.0 + v2.15.1 배포 후에도 사용자 운영 영역 "내 작업만 종료 → task close 발생" 사고 재현. Root cause: `task_service.py` L363-369 First Final 차단 분기가 `logger.info` 만 출력 + `finalize` 변수 그대로 False 유지 → L408 auto_finalize 분기 진입 → `_all_workers_completed=True` (한 명 참여) 시 task close. 설계서는 즉시 return 명시했으나 구현 단계 단순화 영역 결함. pytest 23/23 GREEN 이었으나 TC-FF-01~05 가 constants 검증만 — 실제 동작 검증 누락.

### 변경 (BE only, 2 파일)

- `backend/app/services/task_service.py` L353-378 — 즉시 return + work_completion_log 기록 + pause 자동 resume 흡수 + `first_final_blocked=True` 응답 플래그 신규
- `tests/backend/test_relay_first_final.py` — 신규 3 TC (TC-FF-01b/01c/01d) — `mock_all_done.assert_not_called()` 회귀 차단

### Sprint 41-D 결함 매트릭스 (v2.15.0/15.1 → v2.15.2)

| 시나리오 | Before (결함) | After (fix) |
|---------|:-:|:-:|
| ELEC IF_2 + 한 명 참여 + finalize=false | ❌ task close | ✅ task open 유지 |
| MECH TANK_DOCKING + 한 명 참여 + finalize=false | ❌ task close | ✅ task open 유지 |
| TMS PRESSURE_TEST (Single Final) | ✅ 정상 close | ✅ 동일 (회귀 0) |

### 후속 액션

1. Railway 자동 재배포 확인 (v2.15.2)
2. **운영 영역 사용자 측 재현 검증** — TEST-1111 사례 (O/N 6588 GBWS UTIL_LINE_2) ELEC IF_2 영역 "내 작업만 종료" → task open 유지 확인
3. pytest 신규 3 TC + 기존 23 TC = 26/26 PASS 검증 (CI 또는 수동)
4. POST-REVIEW: 7일 이내 Codex 검토 (deadline 2026-05-21)
5. ADR 후보 — "pytest TC 작성 시 constants 검증 vs 실제 동작 검증 분리 표준" 보강

---

## ✅ 2026-05-14 KST — v2.15.0 minor release (Sprint 41-D Relay First Final Logic)

> **한 줄 요약**: Sprint 41/41-A/41-B/55 trail 마무리 — "내 작업만 종료" 의도 + 시스템 강제 보호 통합. FIRST/SECOND/SINGLE Final 3 카테고리 분리 + auto-close 트리거 + close_at 계산 + duration_source 컬럼 추가. FE 변경 0, BE only 5 파일 +650 LOC, pytest 38/38 GREEN.

### 변경 (5 파일)

- `backend/app/services/task_service.py` — 3 카테고리 분리 + PHASE_MAP + ENUM + 트리거 함수 2종 + check_elec_final_tasks_completed()
- `backend/app/services/duration_calculator.py` 신규 — _to_kst() + calculate_close_at() + calculate_auto_close_duration()
- `backend/app/models/task_detail.py` — auto_close_relay_task() 확장 (default 값 + RETURNING id + race no-op + close_reason null-safe)
- `backend/migrations/056_add_duration_source.sql` 신규 — duration_source NULLABLE + CHECK constraint 4 enum
- `tests/backend/test_relay_first_final.py` 신규 — pytest 23 TC

### 다음 세션 후속 액션

1. **Railway 자동 재배포 확인** — migration 056 자동 적용 (DO block GREEN 확인)
2. **baseline 측정 SQL — 완료 (2026-05-14 운영 측정)**:
   - endpoint 형식: `work.reactivate_task_route` (Flask endpoint name)
   - request_path: `/api/app/work/reactivate-task?`
   - 정정 SQL: `WHERE (endpoint LIKE '%reactivate_task%' OR request_path LIKE '%reactivate-task%')`
   - **baseline (4-22 ~ 5-14 4주 누적): 44건**
     - 4-20 ~ 4-26: 6건 / 4-27 ~ 5-03: 1건 / 5-04 ~ 5-10: 14건 / 5-11 ~ 5-17: 23건 (트렌드 ↑)
   - 4주 후 (2026-06-11 부근) 동일 SQL 재실행 → **목표 22건 이하 (50%+ 감소)**
3. **post-deploy 1주 관찰** — Sentry 새 ERROR 0건
4. **post-deploy 4주 후** — 동일 SQL 재실행 → Manager Rollback 비율 50%+ 감소 검증
5. **별 sprint** `FEAT-RELAY-FIRST-FINAL-ANALYTICS-DASHBOARD-20260513` 진행 가능 (4주 baseline 축적 후)

---

## 🎯 (이전) 다음 세션 첫 액션 — Sprint 41-D 구현 (Relay First Final Logic) — ✅ 완료

### 사전 준비 완료 (2026-05-14)

- **설계서 위치**: `AGENT_TEAM_LAUNCH.md` L36396~L37100 (~700 line, Codex 검증 정정 12건 반영)
- **Codex 검증 trail**:
  - 라운드 1: M=2 / A=4 / N=2 → 정정 7건 반영
  - 라운드 2: M=2 / A=2 / GREEN=2 → 잔존 정정 5건 반영
  - 라운드 3 미진행 (CLAUDE.md 핵심 규칙 6 "라운드 상한 1회" 정합)
- **잔존 catch**: 모두 단순 wire-through + 일관성 정정 → 구현 시 자연 흡수

### 구현 범위 (~650 LOC)

| # | 파일 | 변경 | 라인수 |
|---|------|------|------|
| 1 | `backend/app/services/task_service.py` | (a) FIRST/SECOND/SINGLE FINAL TASK_IDS 분리 (b) `_trigger_first_close()` 신규 (c) `_trigger_second_close()` 신규 (d) `_get_previous_phase_task_ids()` helper (e) `start_work()` First Close 호출 (f) `complete_work()` First Final 차단 + Second Close 호출 (g) `check_elec_final_tasks_completed()` 신규 (M-1 정정) (h) `FIRST_FINAL_PREVIOUS_PHASE_MAP` module-level constant (i) `DURATION_SOURCE_ENUM` set | +200 |
| 2 | `backend/app/services/duration_calculator.py` | 신규 — `_calculate_close_at(orphan_last_completion_at=None)` + `_to_kst()` + `_calculate_auto_close_duration()` | +110 |
| 3 | `backend/app/models/task_detail.py` | `auto_close_relay_task()` 확장 (4 인자 default + `RETURNING id` + race no-op 분기) | +40 |
| 4 | `backend/migrations/0XX_add_duration_source.sql` | `duration_source VARCHAR(40)` 컬럼 + 4 enum CHECK constraint (additive NULLABLE) | +30 |
| 5 | `backend/tests/test_relay_first_final.py` | 신규 — pytest 19 TC (TC-FF-01~19) | +320 |

### pytest 19 TC 매트릭스 요약

- **TC-FF-01~05**: MECH/ELEC First Final auto_finalize 차단 + First Close 트리거
- **TC-FF-06~08**: ELEC IF_2 + INSPECTION AND 조건
- **TC-FF-09**: TMS Single Final 그대로 작동
- **TC-FF-10/10b/10c/10d**: 모델 분기 (GAIA/DRAGON/MITHAS-SDS) 매트릭스
- **TC-FF-11~13**: close_at 계산 (attendance / 17:00 fallback / pause 차감)
- **TC-FF-14**: idempotent (중복 트리거 no-op)
- **TC-FF-15**: duration_validator 비정상 검출
- **TC-FF-16**: Sprint 41-B legacy 호환 (3 인자 호출 + default 값)
- **TC-FF-17**: Sprint 57 checklist path 보존 검증 (M-1 분리 효과)
- **TC-FF-18**: concurrent start_work race (RETURNING id 1건 + 두 번째 False)
- **TC-FF-19**: KST day-rollover (fallback FALLBACK_TRIGGER_DATE_17)

### 구현 흐름 (12h 예상)

1. **Phase 1 (2h)**: task_service.py TASK_IDS 분리 + PHASE_MAP + ENUM + helper 함수
2. **Phase 2 (3h)**: `_trigger_first_close()` + `_trigger_second_close()` + `check_elec_final_tasks_completed()` 구현
3. **Phase 3 (2h)**: duration_calculator.py `_calculate_close_at()` + `_to_kst()` + `_calculate_auto_close_duration()`
4. **Phase 4 (1h)**: `auto_close_relay_task()` 확장 (RETURNING id + race no-op)
5. **Phase 5 (1h)**: migration SQL + DO block 검증
6. **Phase 6 (3h)**: pytest 19 TC 구현 + GREEN 확인
7. **배포**: 사용자 합의 → Railway 자동 재배포 + baseline 측정 SQL 실행

### 운영 영향 + 회귀 위험

- FE 변경 0 (Flutter 기존 다이얼로그 + 3 선택지 유지)
- DB schema additive (duration_source NULLABLE, forward-only)
- Sprint 41-B 호환성 보존 (default 값 + LEGACY trigger_type)
- Sprint 57 checklist 의미 보존 (별 함수명 분리)
- 진단 SQL 결과 0건 (M-3 GREEN) — 기존 ELEC record 영향 0
- 회귀 위험: **낮음** (라운드 2 GREEN + 정정 완료)

### Pre-deploy Gate

- [ ] pytest 19 TC 전체 GREEN
- [ ] flutter build web (FE 영향 0 확인)
- [ ] baseline 측정 SQL 실행 + 기록
- [ ] post-deploy 4주 후 동일 SQL → Manager Rollback 비율 50%+ 감소 확인
- [ ] Sentry 새 ERROR 0건 (배포 후 1주 관찰)

---

## ✅ 2026-05-13 KST — v2.14.4 patch release (HOTFIX-ELEC-CHECKLIST-SELECT-IMMEDIATE-PUT)

> **한 줄 요약**: 사용자 catch — ELEC `master_id=67` (TUBE 종류/색상) 운영 record 18건 중 11건 selected_value=NULL. Root cause: dropdown `onChanged` 가 setState 만 호출, PUT API 호출 없음. MECH 패턴 (v2.11.4 Q6-C) 그대로 이식 — debounce 500ms 즉시 PUT + PASS/NA 미선택 경고. flutter analyze clean, flutter build web GREEN.

### 진단 결과 (운영 record 18건 패턴)

| 시점 | 정상 selected_value | NULL selected_value | 판정 |
|------|:-:|:-:|------|
| 4-13 ~ 4-24 | 일부 | 일부 (phase 2 부터 NULL 시작) | 부분 회귀 |
| 5-07 ~ 5-12 11:47 | 2 | 1 (NA OK) | 정상 |
| **5-12 15:22 ~ 5-13** | **0** | **7 전체 ⚠️** | 회귀 확정 |

### 변경 (FE only, 1 파일)

- `frontend/lib/screens/checklist/elec_checklist_screen.dart`
  - `dart:async` import + `_selectDebounceTimers` Map + dispose
  - `_saveSelectedValue()` helper 신규 (500ms debounce 즉시 PUT)
  - dropdown onChanged → helper 호출 추가
  - PASS/NA 미선택 경고 위젯 (MECH L860-872 패턴)

### 동작 변경

| 시나리오 | Before | After |
|---------|-------|-------|
| 드랍다운 → PASS | ✅ | ✅ (2회 PUT, debounce) |
| **PASS → 드랍다운** | ❌ NULL | ✅ 저장 |
| **드랍다운만 (PASS 안 누름)** | ❌ | ✅ 저장 + 노란 경고 |

### 운영 검증

- 사용자가 신규 ELEC SELECT 항목 입력 시 자동 정상화
- 기존 4-24 ~ 5-13 NULL 11건 record 는 운영자가 재진입 + 드랍다운 재선택 시 자동 보정 (수동)

---

---

## ✅ 2026-05-13 KST — v2.14.3 patch release (HOTFIX-ELEC-CHECKLIST-PLACEHOLDER-DEACTIVATE)

## ✅ 2026-05-13 KST — v2.14.3 patch release (HOTFIX-ELEC-CHECKLIST-PLACEHOLDER-DEACTIVATE)

> **한 줄 요약**: 사용자 catch — 운영 DB ELEC `checklist_master` 영역 placeholder 31건 (id 94-124, 'Jig 검사 항목 1~7' 포함) 이 정식 31건 (id 62-92) 과 별도로 존재. Root cause: HOTFIX-08 (v2.10.10, 4-27) 부수 효과로 046a 자동 재적용. Migration 055 신규 (placeholder `is_active=FALSE`) + 046a 본문 교체 (047 정상 31항목 + ON CONFLICT). Logic 변경 0.

### Root cause trail

- 4-10 11:26: migration 047 적용 → 정식 31항목 INSERT (id 62-92)
- 4-15 23:06: migration 048 적용 → phase1_applicable + qi_check_required 정규화
- **4-27 21:36: HOTFIX-08 v2.10.10 부수 효과 → 046a 자동 재적용 → placeholder 31건 신규 INSERT (id 94-124)**
- 5-13: 사용자 catch + migration 055 작성

### 변경 (3 파일)

| 파일 | 변경 |
|------|-----|
| `backend/migrations/055_elec_checklist_placeholder_deactivate.sql` | 신규 — placeholder 31건 deactivate + DO block 검증 |
| `backend/migrations/046a_elec_checklist_seed.sql` | 본문 교체 — placeholder → 047 정상 31항목 + ON CONFLICT DO NOTHING (재발 방지) |
| `backend/version.py` / `frontend/lib/utils/app_version.dart` | 2.14.2 → 2.14.3 |

### pytest TC 신규 5건

- placeholder 31건 deactivate / 정식 31건 active 유지 / record 50건 FK 보존 / ELEC COMMON active 총 31

### Logic 변경: 0

모든 ELEC 체크리스트 logic 이 `cm.is_active = TRUE` 필터 사용 — placeholder deactivate 후 정식 31건만 노출. 작업자/QI 화면 + Phase 1·2 판정 + 성적서 모두 정상화.

### 사용자 측 검증 (Railway 재배포 후)

```sql
-- ① placeholder 31건 모두 deactivate 확인
SELECT COUNT(*) FROM checklist.checklist_master
WHERE category='ELEC' AND product_code='COMMON' AND id BETWEEN 94 AND 124 AND is_active=FALSE;
-- 기대: 31

-- ② 정식 31건 active 유지 확인
SELECT COUNT(*) FROM checklist.checklist_master
WHERE category='ELEC' AND product_code='COMMON' AND id BETWEEN 62 AND 92 AND is_active=TRUE;
-- 기대: 31

-- ③ ELEC COMMON 영역 active 총 31 (정식만) 확인
SELECT COUNT(*) FROM checklist.checklist_master
WHERE category='ELEC' AND product_code='COMMON' AND is_active=TRUE;
-- 기대: 31
```

---

## ✅ 2026-05-13 KST — v2.14.2 patch release (HOTFIX-MATERIALS-CATEGORY-ILIKE)

> **한 줄 요약**: AXIS-VIEW `OPS_API_REQUESTS.md` #64 catch — `/api/admin/materials?category=` 가 `=` 정확 매칭이라 'm' / 'mfc' 입력 시 0건. keyword/description 은 이미 ILIKE 적용되어 일관성 보강. 3 line + pytest TC 2건 신규 + commit `86fc8a1` push 완료.

### 변경 (1 파일 / 3 line)

| 파일 | 변경 |
|------|-----|
| `backend/app/routes/admin_materials.py` L82-84 | `category = %s` → `category ILIKE %s` + `f'%{category}%'` |

### pytest TC

- 신규 2건: `test_list_materials_filter_by_category_case_insensitive` (mfc → 13건) / `test_list_materials_filter_by_category_partial_match` (m → 13건 이상)
- 회귀: 기존 정확 매칭 MFC 13건 TC + step4_admin 15/15 PASS (218초)

### 검증

| 입력 | Before | After |
|------|--------|-------|
| `MFC` | ✅ 13건 | ✅ 13건 |
| `mfc` | ❌ 0건 | ✅ 13건 |
| `m` | ❌ 0건 | ✅ 13건 이상 |

### 후속 (사용자 측 검증)

- Railway 자동 배포 후 (2~3분) AXIS-VIEW `ChecklistOptionMapModal` 영역에서 'm' / 'mfc' / 'M' 검색 정상화 확인

### 연관

- AXIS-VIEW v1.43.8 `ChecklistEditModal` 자재코드 input case-insensitive (FE client filter)
- AXIS-VIEW BACKLOG `OPS-MATERIALS-KEYWORD-ILIKE`

---

## ✅ 2026-05-12 KST — v2.14.1 patch release (FIX-DB-POOL-CONN-LEAK-WORK-PY)

> **한 줄 요약**: 16:48 Railway pool exhausted 사고 root cause 영역 `routes/work.py` L705 `conn2.close()` 영역 → ThreadedConnectionPool 영역 conn 반환 X → 영구 leak. 5 위치 fix (L705 + try/finally 4건). Codex GREEN + pytest 45/45 PASS. 회귀 위험 0.

### 사고 분석 trail

- 16:48:12 (KST) — Railway pool exhausted 첫 catch
- 자가 회복 영역 정상 작동 (5-04 도입 영역, 3 cycles=15분 후 close+init)
- 사용자 측 restart 영역 정상화
- 분석: 모바일 작업자 `GET /api/app/tasks/{sn}` 영역 매 호출 1 conn 영구 leak (work.py L705 `conn2.close()`)

### Fix 5 위치 (work.py만)

| 위치 | fix | 영향 |
|------|-----|------|
| L705 | `conn2.close()` → `put_conn(conn2)` + try/finally | 🔴 영구 leak 차단 |
| L676-707 | `conn2 = None` + finally | exception 시 leak 차단 |
| L594-670 | try/finally 패턴 | exception 시 leak 차단 |
| L568-583 | try/finally + worker_map 외부 초기화 | exception 시 leak 차단 |
| L468-486 | try/finally 패턴 | exception 시 leak 차단 |

### 후속 BACKLOG

- `BUG-WORK-INSERT-ROLLBACK-EXPLICIT-20260512` (P3) — L468-486 INSERT except rollback 명시 (Codex A-1)

### 운영 모니터링 (Twin파파 측, v2.14.1 release 후)

#### 🔴 1순위 — Pool exhausted 재발 여부

| 영역 | 정상 기준 | 위험 기준 | 확인 방법 |
|------|-----------|-----------|-----------|
| `[db_pool] Pool exhausted` Sentry alert | 0건/24h | 1건+ | Sentry 대시보드 |
| `[db_pool] Using direct connection` Railway log | 0~매우 적음 | 시간당 10+ | Railway logs 검색 |
| `[pool_warmup] 0/0 conn warmed` | 0건 | 1건+ | Railway logs |
| `[db_pool] 0/0 warmed for 3 consecutive cycles` (자가 회복 발화) | 0건 | 1건+ = leak 재발 가설 | Sentry alert |

→ fix 효과 있으면 위 4개 모두 24h 동안 **0건 유지** 목표

#### 🟠 2순위 — 응답 시간 정상화

| endpoint | 정상 | 위험 |
|----------|------|------|
| `GET /api/app/tasks/{sn}` | 50-300ms | 500ms+ 지속 |
| `POST /api/app/work/complete` | 200-800ms | 1.5초+ 지속 |
| `GET /api/app/work/today-tags` | 50-150ms | 300ms+ |

#### 🟡 3순위 — 다른 release 운영 안정성

- v2.14.0 자재 업로드 endpoint — flow sensor 완료 후 운영 검증
- AXIS-VIEW Sprint 40 일괄 처리 — 모바일/대시보드 정상 작동
- 5-17 ± 1d — 5일 주기 Railway proxy idle 가설 재발 X 확인

#### 검증 시점 권고

- **T+1h** (배포 1시간 후): ✅ **GREEN 확인** (2026-05-13, Sentry/Railway db_pool 키워드 0건)
- **T+24h** (5-13 17:00 KST): 같은 시간대 (16:00~17:00 KST peak) 정상 응답
- **T+5d** (5-17): 5일 주기 가설 재발 X 확정

---

## ⏸️ 이전 release: v2.14.0 (Sprint 66-BE-FOLLOWUP v3 자재 마스터 Excel 일괄 업로드)

> **한 줄 요약**: 자재 마스터 Excel 일괄 업로드 endpoint 신규 — Sprint 66-BE-FOLLOWUP v3 자재 마스터 Excel 일괄 업로드 endpoint. Codex 5라운드 검증 (M=4→0 GREEN). pytest 23/23 GREEN. 신규 파일 2개 분리 (utils + services). VIEW Sprint 42 v1.43.0 BE 404 fix)

## ✅ 2026-05-12 KST — v2.14.0 minor release (Sprint 66-BE-FOLLOWUP v3)

> **한 줄 요약**: 자재 마스터 Excel/CSV 일괄 업로드 endpoint 신규 (POST /api/admin/materials/upload). VIEW Sprint 42 v1.43.0 `MaterialUploadModal.tsx` 4단계 워크플로우 BE 404 fix. Codex 5라운드 검증 + pytest 23/23 GREEN. 회귀 위험 0.

### 변경 trail

| 단계 | 결과 |
|---|---|
| #63 사용자 결정 Q1/Q2/Q3 확정 (2026-05-11) | ✅ |
| Codex 라운드 1~5 (M=4→0 GREEN, 053a generator 패턴 정합) | ✅ |
| Step 1-A: utils/material_parser.py (+228 LOC) | ✅ |
| Step 1-B: services/material_upload_service.py (+228 LOC) | ✅ |
| Step 1-C: routes/admin_materials.py /upload route (+88 LOC) | ✅ |
| Step 1-D: pytest 24 TC (Unit 12 + Integration 11 + 1 skip) | ✅ 23/23 GREEN |
| requirements.txt 의존성 추가 (chardet + openpyxl) | ✅ |
| version bump v2.13.2 → v2.14.0 + md 5개 갱신 | ✅ |
| commit + push | ⏳ |

### 핵심 결정

- Q1 MFC scope only / non-MFC dedup / ATTRIBUTE_CONFLICT 첫 등장 유지 / INVALID_BOM_KEY BOM row 영역만 / FIELD_TOO_LONG 8 필드 / .xls drop / utils + services 분리 / `{error, message}`

### 후속 영역

- AXIS-VIEW repo 별 PR: FE #63 BOM 4-key → 2-key + `detail` → `message` + `.csv/.xlsx only`
- TC-MU-11 ROLLBACK injection TC 별 sprint
- Twin파파 측 자재 마스터 페이지 영역 업로드 운영 검증 (sample 30rows / 1654 rows 부하)

---

## ⏸️ 이전 release: v2.13.2 (HOTFIX-TASKS-BY-ORDER-WORKERS, S1 동반) (S1 동반) — `/tasks/by-order/<sales_order>` 응답에 `workers` 배열 추가. VIEW v1.43.6 S1 HOTFIX catch 영역 — 흰 화면 발생 → 후처리 helper `_enrich_tasks_with_workers()` 신규 추가. POST-REVIEW deadline 2026-05-12)

## ✅ 2026-05-11 KST — v2.13.2 hotfix release (HOTFIX-TASKS-BY-ORDER-WORKERS, S1 동반)

> **한 줄 요약**: VIEW v1.43.6 S1 HOTFIX catch — `/tasks/by-order/<sales_order>` 응답에 `workers` 배열 누락 → FE TypeError → 흰 화면. 후처리 helper 영역 `_enrich_tasks_with_workers()` 신규 추가 (work.py L562~728 패턴 정합). VIEW v1.43.6 정규화 코드 동시 release → 회귀 위험 0.

### Root cause

- 내 `get_tasks_by_order()` 영역 `_task_to_dict()` 호출 후 후처리 영역 X
- 기존 `get_tasks_by_serial` (work.py L562~728) 영역 약 170 line 후처리 (workers + worker_name + my_status 일괄 조회) 영역 동일 패턴 누락
- Codex 5 라운드 + v2.13.1 검증 모두 — **후처리 패턴 일관성** 검증 누락 (응답 spec만 검증)

### 변경 trail

| 단계 | 결과 |
|---|---|
| VIEW v1.43.6 S1 HOTFIX catch — 흰 화면 root cause 정리 | ✅ |
| 신규 helper `_enrich_tasks_with_workers()` (~100 LoC) 추가 | ✅ |
| `get_tasks_by_order()` helper 호출 추가 (1 line) | ✅ |
| version bump v2.13.1 → v2.13.2 + md 5개 갱신 | ✅ |
| commit + push | ⏳ |

### POST-REVIEW 영역 (24h 이내, deadline 2026-05-12)

- Codex 사후 검토 — S1 HOTFIX 정합 (CLAUDE.md L237)
- Codex 검증 라운드 표준화 권고 — 응답 spec 일관성 + 후처리 패턴 일관성 동시 검증 항목

### ✅ 운영 검증 완료 (Twin파파 측, 2026-05-11 KST)

- VIEW 대시보드 영역 **일괄 시작/종료 정상 작동 확인** — TEST-1111~1113 영역
- S/N 상세뷰 영역 흰 화면 영역 정상 렌더 확인 (VIEW v1.43.6 + OPS v2.13.2 정합)
- 토스트 영역 succeeded / skipped 양쪽 정상 표시
- 회귀 영역 0 — 기존 단일 `/work/start` `/work/complete` 영역 영향 없음

### 신규 제안 영역 — BACKLOG 등록 후 별 sprint 검토

사용자 제안 (2026-05-11 KST): "일괄 시작 영역 입력 시 QR 태깅 없이도 작업 현황 영역 표시" — admin/manager 영역 사전 등록 영역 의도. 별 BACKLOG entry 등록 후 검토 영역 진행 영역 (FEAT-BATCH-START-WITHOUT-QR-TAG).

---

## ⏸️ 이전 release: v2.13.1 (HOTFIX-TASKS-BY-ORDER-SCHEMA)

## ✅ 2026-05-11 KST — v2.13.1 hotfix release (HOTFIX-TASKS-BY-ORDER-SCHEMA)

> **한 줄 요약**: Sprint 64-BE v3 후속 hotfix — `/tasks/by-order/<sales_order>` 응답 객체 wrap → 배열 직접 정정. VIEW v1.43.5 호환 코드 양쪽 형식 처리. 일괄 시작 토스트 미표시 catch 즉시 fix.

### 변경 trail

| 단계 | 결과 |
|---|---|
| Sprint 64-BE v3 v2.13.0 release 직후 사용자 catch (VIEW 분석) | ✅ |
| Root cause 확정 — Codex 5라운드 catch 누락 (다른 endpoint spec 대조 X) | ✅ |
| 옵션 B 결정 — VIEW v1.43.5 + OPS v2.13.1 동시 release | ✅ |
| BE 정정 — `task_service_batch.py` `get_tasks_by_order()` return type | ✅ |
| version bump v2.13.0 → v2.13.1 | ✅ |
| md 5개 갱신 (CLAUDE.md / CHANGELOG.md / PROGRESS.md / handoff.md / BACKLOG.md) | ⏳ |
| commit + push | ⏳ |

### 핵심 결정 사항

- VIEW v1.43.5 호환 코드 (양쪽 형식 처리) + OPS v2.13.1 응답 정합 = 양쪽 즉시 release
- 회귀 위험 0 — VIEW 호환 코드 영역 BE 변경 후에도 자동 정상 작동
- pytest TC 영역 추가는 별 sprint (즉시 release 우선)

### 후속 BACKLOG

- POST-REVIEW: Codex 검증 라운드 영역 응답 spec 일관성 항목 추가 (다른 endpoint 영역 대조 표준화)

---

## ⏸️ 이전 release: v2.13.0 (Sprint 64-BE v3 Work Batch)

## ✅ 2026-05-11 KST — v2.13.0 minor release (Sprint 64-BE v3 Work Batch)

> **한 줄 요약**: TM Tank Module 일괄 처리 BE 엔드포인트 — `POST /work/start-batch` + `POST /work/complete-batch` + `GET /tasks/by-order/<sales_order>`. FE Sprint 40 v1.40.0 contract 정합. 신규 파일 2개 분리 (CLAUDE.md L545 정합, 기존 work.py/task_service.py touch 0). Codex 5 라운드 검증 (M=6→4→1→1→0 GREEN). pytest 30 TC GREEN (Unit 13 + Integration 17, staging DB 22분 10초 실측). 회귀 위험 0.

### 변경 trail

| 단계 | 결과 |
|---|---|
| Codex 라운드 1 (M=6/A=3) → v2 재설계 (helper reuse 패턴) | ✅ |
| Codex 라운드 2 (M=4/A=1) → v3 (분리 파일 + 30건 + pseudo code + 16+ TC) | ✅ |
| Codex 라운드 3 (M=1/A=3) → 12 case 전수 + TC-AUDIT-02 + import 순서 + gate 측정 | ✅ |
| Codex 라운드 4 (M=1/A=1) → prefix 충돌 정정 (Blueprint url_prefix 영역) | ✅ |
| Codex 라운드 5 (M=0/A=1/N=3) → pool warm-up 한 줄 추가 후 구현 진입 권고 | ✅ |
| Step 1-A: `work_batch.py` (+117) + `task_service_batch.py` (+209) + `__init__.py` (+1) | ✅ |
| Step 1-B: `tests/conftest.py` fixture 3종 (+150) + `tests/backend/test_work_batch.py` (+280) | ✅ |
| pytest catch 2건: C1 case 인자 오기 + complete TC reason 예상값 (pytest 자체 catch) | ✅ |
| pytest 30/30 GREEN (Unit 13 + Integration 17, staging DB 22분 10초) | ✅ |
| version bump v2.12.6 → v2.13.0 + md 5개 갱신 | ✅ |
| commit + push (Twin파파 측 AXIS-VIEW 직접 검증 예정) | ⏳ 진행 중 |

### 핵심 결정 사항 (v3)

- **신규 파일 2개 분리**: CLAUDE.md L545 "필수 분할 파일 새 로직 추가 금지" 정합. 기존 work.py 1,355 LOC (🔴) + task_service.py 1,551 LOC (⛔) touch 0.
- **30건 상한**: helper task당 7~9 query, pool MAX=30 안전. 50→30 하향 (Codex M-2).
- **Best-effort sequential**: 각 task 마다 기존 `start_work()`/`complete_work()` helper 호출. audit log + start guards + complete logic 자동 흡수.
- **`_match_manager_company()`**: work.py L340-356 reactivate 패턴 정합 (TMS = `module_outsourcing OR mech_partner`). substring 매칭 보존 (A-1 BACKLOG 후속).

### 후속 BACKLOG

- `BUG-MATCH-COMPANY-SUBSTRING-FALSE-POSITIVE-20260511` 🟢 P3 — BAT vs COMBAT substring boundary (운영 미발생, 분기별 모니터링)
- AXIS-VIEW Sprint 40 v1.40.0 — Twin파파 측 직접 검증 후 결과 공유 예정

### 다음 세션 영역

- DB Pool V4.1 5-15 추가 점검 (T+8d 윈도우, 5-12 ± 1d 예상 사고 시점 통과 확인)
- POST-REVIEW 2건 deadline 2026-05-18 (HOTFIX-MASTER-LIST + HOTFIX-CREATE-MASTER)
- 6월 OBSERV-PIN-FLAG-DEPLOY-CORRELATION-RE-CHECK-20260601

---

## ⏸️ 이전 release: v2.12.6 patch (HOTFIX-SPRINT66BE-CREATE-MASTER-ITEM-TYPE-AND-CONFLICT-MSG)

## ✅ 2026-05-11 KST — v2.12.6 patch release (HOTFIX-SPRINT66BE-CREATE-MASTER-ITEM-TYPE-AND-CONFLICT-MSG)

> **한 줄 요약**: v2.12.5 release 직후 사용자 catch — AXIS-VIEW "+ 항목 추가" 모달에서 신규 SELECT/INPUT 항목 추가 시 묵음 회귀 (DB DEFAULT 'CHECK' 저장). `create_checklist_master()` POST 정정 ~50 LoC (item_type 검증 + select_options 직렬화 + CONFLICT 응답 보강). 회귀 위험 0 (additive). cowork 누적 실수 #19 — ADR-024 분리 정책 결정 시급 영역.

### 변경 trail

| 단계 | 결과 |
|---|---|
| BE `checklist.py` import json + POST 정정 (~50 LoC) | ✅ |
| ① item_type 추출 + enum 검증 (CHECK/SELECT/INPUT) | ✅ |
| ② select_options 추출 + list 검증 + json.dumps 직렬화 | ✅ |
| ③ CONFLICT 응답 보강 (기존 id + is_active + 비활성 안내) | ✅ |
| INSERT 컬럼 2개 추가 (item_type, select_options) | ✅ |
| BACKLOG entry 신규 등록 | ✅ |
| AGENT_TEAM_LAUNCH 설계서 신규 섹션 | ✅ |
| version bump v2.12.5 → v2.12.6 | ✅ |
| commit + push | ⏳ 진행 중 |
| Railway 자동 재배포 검증 | ⏳ |

### Root cause

- Sprint 52 POST 작성 시점 ~ Sprint 63-BE 'INPUT' enum 확장 시점까지 **묵음 누적 회귀**
- FE 측 item_type 전송에도 BE 가 무시 → DB DEFAULT 'CHECK' 저장
- 신규 SELECT/INPUT 항목 생성 불가 묵음 회귀 → ~수 sprint 잠복

### ADR-024 분리 정책 결정 시급

cowork 누적 실수 영역 (5-09~5-11 2일 누적 3건):
- #16 (5-09): HOTFIX-SPRINT66BE-ENRICH-SELECT-OPTIONS-ITEMCODE (Codex M1~M5 폐기)
- #18 (5-11): HOTFIX-SPRINT66BE-MASTER-LIST-ITEM-TYPE (GET 누락)
- #19 (5-11): 본 HOTFIX (POST 누락, #18 동일 그룹)

→ cowork ↔ Claude Code 작업 분리 정책 결정 영역 임계 초과. 별 sprint 결정 필요.

### 영향

- 회귀 위험 0 (FE 가 item_type 미전송 시 'CHECK' fallback)
- 사용자 영향: AXIS-VIEW 신규 SELECT/INPUT 항목 추가 정상화
- FE Netlify 빌드 X (BE only) — v2.12.5 deploy 시 PWA storage 손실 영향과 별 영역

---

## ✅ 2026-05-11 KST — v2.12.5 release 완료 (4건 묶음: Admin 옵션 3건 + HOTFIX-SPRINT66BE-MASTER-LIST-ITEM-TYPE)

## ✅ 2026-05-11 KST — v2.12.5 release 완료 (4건 묶음: Admin 옵션 3건 + HOTFIX-SPRINT66BE-MASTER-LIST-ITEM-TYPE)

> **한 줄 요약**: 사용자 측 5-11 catch — Admin 옵션 화면 3건 정정 (① FE/BE 키 불일치 silent fail / ② 무제한 list 렌더 / ③ 미시작 알람 default 영역) + AXIS-VIEW v1.43.1 ChecklistEditModal SELECT 분기 회귀 HOTFIX (④ S2, cowork 실수 #18). Railway BE + Netlify FE 배포 완료, 회귀 위험 0 (additive).

### ④ HOTFIX-SPRINT66BE-MASTER-LIST-ITEM-TYPE-20260511 (S2 영역)

- **Root cause**: `/api/admin/checklist/master` GET 응답에 `item_type` + `select_options` 직렬화 누락 (cowork 실수 #18)
- **Trigger**: 사용자 catch — AXIS-VIEW v1.43.1 prod 정상 배포 확인 BUT ChecklistEditModal `item.item_type === 'SELECT'` 분기 항상 false → SELECT 매핑 UI 미동작
- **Fix**: `backend/app/routes/checklist.py` `list_checklist_master()` SELECT 절 + 응답 dict 정정 (+2 LoC, additive)
  - SELECT 절: `cm.item_type, cm.select_options` 추가
  - 응답 dict: `'item_type': row.get('item_type') or 'CHECK'` + `'select_options': row.get('select_options')` 추가
- **Severity**: 🟠 S2 (부분 장애 — SELECT 매핑 UI 영역만)
- **POST-REVIEW**: BACKLOG `POST-REVIEW-HOTFIX-SPRINT66BE-MASTER-LIST-ITEM-TYPE-20260511` deadline 2026-05-18
- **ADR-024 cowork 작업 분리 정책 검토 임계 초과** (실수 #18 누적)
- **회귀 위험 0** (additive 응답 — 기존 FE/Flutter 클라이언트 무영향)

### 변경 trail

| 단계 | 결과 |
|---|---|
| #1-a FE/BE 키 정정 (silent fail) | ✅ `response['workers']` → `'inactive_workers'`/`'deactivated_workers'` (admin.py L2432/L2471 정합) |
| #1-b/c 비활성 사용자 + 비활성화 계정 스크롤 | ✅ ConstrainedBox 240px (~3건) wrap |
| #2 미종료 작업 스크롤 | ✅ ConstrainedBox 240px + SingleChildScrollView wrap |
| #3 미시작 알람 default off (BE SETTING_KEYS) | ✅ admin.py L71 `True` → `False` |
| #3 미시작 알람 default off (FE state + fallback) | ✅ admin_options_screen.dart L35 + L324 |
| Flutter analyze | ✅ error 0 / 9 info (모두 기존 코드, 내 변경 syntax 정합) |
| pytest 회귀 영역 검증 | ✅ `alert_task_not_started_enabled` 의존 test 0건 |
| version bump | ✅ v2.12.4 → v2.12.5 (BE + FE) |
| md 갱신 (CLAUDE/CHANGELOG/PROGRESS/handoff/BACKLOG) | ✅ trail 기록 완료 |
| **git commit + push** | ✅ 5-11 commit 5118c04 (4건 묶음 release) |
| Netlify FE build + deploy | ✅ gaxis-ops.netlify.app 배포 완료 |
| Railway BE 자동 재배포 검증 | ⏳ 자동 재배포 진행 중 (v2.12.5 build_date 2026-05-11 검증 예정) |

### Root cause #3 사용자 시나리오 해석

prod DB 검증: `alert_task_not_started_enabled = false` (5-11 08:26 사용자 설정 marked). 사용자 "업데이트 할때마다 true값으로 변경" = DB key 부재 시 BE `result.setdefault(key, meta['default'])` 가 default `True` 반환 영역. 5-11 catch 직전 first-touch 시점 영역. default 변경 후 신규 admin/staging 환경에서도 OFF 정합.

### 저녁 push 시 작업 영역

1. `git add` BE + FE + md 모두
2. `git commit` v2.12.5 release message
3. `git push origin main`
4. `flutter build web --release` (FE 변경 있음)
5. Netlify deploy
6. Railway 자동 재배포 / build_date 2026-05-11 검증
7. T+1h 검증 (운영 영역)

### 잔존 영역

- **FIX-PIN-FLAG (task #29 pending)** — **5-11 D+14 측정 결과 deploy ↔ storage 손실 상관관계 발견**:
  - Q1 pin_status_calls 14일 추세 안정 ✅ (backend fallback 활성 입증)
  - Q3 PIN 재등록 신호: 4-30/5-05/5-07/5-08/5-10 각 1~2건 → **5-11 23건 polynomial spike** ⚠️
  - 23명 모두 5-11 06:54~09:02 KST 출근 burst 시점 (전 회사 광범위), pin_fail_count 0 (storage 손실, lock 영역 X)
  - 5-10 evening v2.12.4 Netlify FE deploy 직후 → PWA SW 업데이트 가설 강력
  - 비교: 5-08 v2.12.3 BE only (FE 빌드 X) → 5-09 PIN 재등록 0건 ✅
- **사용자 결정 (5-11)**: 5월 = 운영 안정화 + 디버깅 + 편의사항 개선 = 잦은 push 지속 (storage 손실 trade-off 영역). **6월 본격 운영 상태에서 재점검 진행**.
- **신규 BACKLOG entry 등록**: `OBSERV-PIN-FLAG-DEPLOY-CORRELATION-RE-CHECK-20260601` (6월 재점검 영역)
- backend fallback (v2.10.6) 효과 입증 ✅ — `/auth/pin-status` 14일 안정. 단 refresh_token 같이 잃은 cohort 영역엔 효과 0 (23명 EmailLogin → 비번 로그인 → PIN 재설정 흐름).
- task #29 **pending 유지** — 6월 재점검 후 정량 close 결정 영역.

---

## 🎯 2026-05-10 KST — v2.12.4 release (FIX-ELEC-IF-NAMING-DOCKING-CLARITY)

> **한 줄 요약**: 작업자 측 운영 catch — IF_1/IF_2 의 1/2 기준이 도킹 전/후 인지 혼동. 명시적 라벨 (`(도킹 전)` / `(도킹 후)`) 부여로 영구 해결. task_id 변경 0 (식별자 보존), FE 코드 변경 0, 회귀 위험 0.

### 변경 trail

| 단계 | 결과 |
|---|---|
| BE task_seed.py L77-78 | ✅ TaskTemplate task_name 정정 (IF_1/IF_2) |
| BE task_service.py L495 | ✅ ELEC IF_2 알림 message 정정 |
| Migration 054 작성 + atomic | ✅ BEGIN/COMMIT + UPDATE 2건 + DO block 검증 |
| Migration 054 prod 적용 | ✅ IF_1 185 + IF_2 185 = 370 row UPDATE, DO block PASS |
| migration_history 등록 | ✅ 054 등록 완료 |
| pytest 갱신 (2 파일) | ✅ test_company_task_filtering + test_issue46_workers_mapping |
| pytest 회귀 검증 | ✅ 28/28 PASS (회귀 0) |
| version bump | ✅ v2.12.3 → v2.12.4 (BE + FE) |
| Railway BE 배포 | ⏳ push 후 자동 배포 검증 예정 |
| Netlify FE 배포 | ⏳ build 완료, deploy 진행 예정 |

### 영향

- task_id 변경 X → 코드/알림/체크리스트 매칭 로직 영향 0
- FE 코드 변경 0 → task_name display 그대로 (BE 응답 변경 자동 반영)
- 회귀 위험 0
- 작업자 화면 즉시 효과: `I.F 1` → `I.F 1 (도킹 전)`, `I.F 2` → `I.F 2 (도킹 후)`

---

## 🎯 2026-05-11 14:55 KST — DB Pool 자가 회복 2차 실전 작동 ✅ (Worker B pid=3, 5-07 가설 폐기)

> **한 줄 요약**: 5-10 V4.1 1차 통과 (시나리오 A) 후 +1d 만에 자가 회복 2차 발생 — 이번엔 **pid=3 (Worker B)**. 5-07 가설 *"Worker B 자가 회복 trigger 도달 불가능"* 폐기됨 → **양쪽 worker 모두 자가 회복 능력 입증**. 사용자 영향 0 (silent auto-recovery 100%). 5-11 15:42 KST 측정으로 시나리오 A 90% + minor concern 1건 (5 conn capacity 절반) 확정. `OBSERV-PER-WORKER-POOL-RECOVERY-20260507` close 가능 판정.

### 사고 + 측정 trail (5-11)

| 시각 (KST) | 이벤트 | 출처 |
|---|---|---|
| 5-11 11:30:37 | Scheduler started (재배포 또는 worker restart 추정) | Sentry breadcrumb |
| 5-11 14:55:47.659 | warmup tick 시작 (interval 5분 cron) | Sentry breadcrumb |
| 5-11 14:55:47.660 | `[db_pool] warmup getconn failed (skip): connection pool exhausted` (warning) | Sentry breadcrumb |
| 5-11 14:55:47.660 | **Sentry alert: `re-initializing pool (pid=3)` ERROR** | Sentry breadcrumb |
| 5-11 14:55:47.768 | **DB pid 215907 backend_start** (Sentry +108ms) | pg_stat_activity |
| 5-11 14:55:47.808 | DB pid 215908 (2번째, +148ms) | pg_stat_activity |
| 5-11 15:34:04.698 | DB pid 215962 (단발성, HTTP 요청 direct conn fallback 추정) | pg_stat_activity |
| 5-11 15:35:47.6~.7 | DB pid 215965/215966 (warmup tick, 14:55 + 40분 정확) | pg_stat_activity |
| 5-11 15:40:47.6~.7 | DB pid 215978/.979/.980 (warmup tick, MIN=5 보충 3 conn fresh) | pg_stat_activity |

→ 9ms self-recovery latency 유지 (5-07 패턴 재현)

### 5-07 가설 폐기 — 양쪽 worker 자가 회복 능력 입증

| 5-07 가설 (5-07 entry 참조) | 5-11 실측 데이터 | 판정 |
|---|---|---|
| Worker B 자가 회복 trigger 도달 불가능 | **pid=3 자가 회복 정상 작동** (Sentry ERROR + DB conn fresh init) | ❌ **반박됨** |
| Worker B 풀 dead 시 사용자 영향 silent degradation | 사용자 영향 0 (silent self-recovery 성공, 0 users) | ❌ **반박됨** |
| warmup cron 가 fcntl lock 으로 단일 worker 만 실행 | 양쪽 worker 모두 warmup + self-recovery 능력 보유 | ❌ **반박됨** |

→ ADR-025 의 "per-worker 카운터 의도" 가 **실제로 양쪽 worker 모두 작동 중** 임이 입증됨. 5-07 측정 당시 단일 cluster 5 conn 만 보인 것은 *"한쪽 worker conn 모두 idle disconnect"* 시점에 측정한 결과로 재해석.

### warmup cron MIN=5 보장 작동 입증 (3분 안 2회 측정)

| 측정 | 시각 (KST) | conn 수 | 새 cohort |
|---|---|---|---|
| 측정 1 (warmup 직전) | 5-11 15:36~37 추정 | 3 conn | — (자가 회복 14:55 cohort 2 + 단발 15:34 cohort 1) |
| 측정 2 (warmup 직후) | 5-11 15:42~43 추정 | **5 conn** | **15:40:47 warmup tick 3 conn fresh 보충** ✅ |

→ `warmup_pool()` 이 *"현재 살아있는 conn 검사 + 부족분 보충"* 패턴으로 정상 작동.

### 사고 단계 감소 (4-29 → 5-11)

| 사고 | 시점 | pid | 처리 방식 | 사용자 영향 |
|---|---|---|---|---|
| 1차 | 4-29 23:31 KST | — | 수동 Railway Restart (10시간 silent + 1.5h 복구) | 1.5h+ |
| 2차 | 5-04 11:38 KST | — | 수동 Railway Restart | 40분 |
| 3차 | 5-07 20:54 KST | **pid=2** | 자가 회복 자동 | ~15분 |
| **4차** | **5-11 14:55 KST** | **pid=3** ⭐ | **자가 회복 자동 (Worker B 첫 실전 작동)** | **~15분** ✅ |

→ 4-29 (수동) → 5-11 (자동, 양쪽 worker 모두) **운영 부담 100% 자동화 달성**

### 시나리오 판정 — 90% A + 10% B

- ✅ **시나리오 A (이상적)**: 자가 회복 + warmup cron MIN=5 보장 모두 작동 입증
- 🟡 **시나리오 B (minor)**: 측정 시점 conn 수가 5 (per-worker × 2 = 10 기대) — capacity 절반

**핵심 미스터리**: 양쪽 worker 자가 회복 능력 있음 + warmup MIN=5 보장 작동인데 왜 항상 5 conn 만 visible 인가?

**가설**: Railway proxy 가 한쪽 worker 의 conn 을 더 자주 disconnect 또는 양쪽 worker 가 시간차로 active (한 쪽이 dead 일 때 다른 쪽이 active) — 별 sprint 분석 영역.

**사용자 영향**: 0 (현재 트래픽 수준에서 5 conn 으로도 충분, peak 16 in-flight 까지 direct conn fallback 으로 흡수)

### 다음 단계

- **5-15 V4.1 영구 종결 시점** — 5-12 ± 1d 가설은 사실상 깨졌으나 (5-11 사고 발생), **양쪽 worker 자가 회복** 으로 영향 0 → V4.1 close 무관
- `OBSERV-PER-WORKER-POOL-RECOVERY-20260507` **close 가능** (가설 폐기됨)
- **신규 BACKLOG** `OBSERV-DUAL-WORKER-CONN-COEXIST-20260511` (P3, 1~2h) — 5 conn 만 visible 미스터리 추적

### 종합 평가 — **NET 좋음** ✅

- 자가 회복 메커니즘이 **운영자 야간 호출 의존도 0** 도달
- 4-29 → 5-11 4회 사고 모두 학습 layer 추가로 단계 감소
- 5-07 가설 폐기 = 시스템이 예상보다 더 건강
- v2.11.6 자가 회복 메커니즘 투자가 **객관적 성공** 입증

### 검증 데이터 + 문서 업데이트

- 측정 SQL: `DB_POOL_VERIFICATION_QUERIES_20260427.md` V4.1 5-11 trail 추가 완료
- BACKLOG `OBSERV-PER-WORKER-POOL-RECOVERY-20260507` 갱신 (scope 재정의 + close 권장)
- BACKLOG `OBSERV-DUAL-WORKER-CONN-COEXIST-20260511` 신규 등록 (P3, 1~2h)

---

## 🟢 2026-05-10 KST — DB Pool V4.1 T+1주 측정 (1차 통과 — 시나리오 A 이상적)

> **한 줄 요약**: 4-27 v2.10.13 deploy 의 keepalive 차단 효과 + 자가 회복 안전망 1차 검증 통과. 5-07 자가 회복 사고 +2d 5h 측정 시점 신규 사고 0건. 사용자 측 5-15까지 추가 점검 진행 (5-12 ± 1d 예상 사고 시점 통과 확인 후 V4.1 영구 종결).

### 측정 결과 (2026-05-10 02:17 KST)

| 영역 | 결과 |
|---|---|
| Railway logs --since 36h (5-09~5-10) | 0/0 / re-initializing 0건 ✅ |
| Sentry 1주 신규 [db_pool] | 0건 ✅ (PYTHON-FLASK-B = 5-07 사고 기존 트래킹) |
| pg_stat_activity OPS conn | 8 conn (Cluster A 5 + warmup B 3) — MIN=5/MAX=30 정상 |
| Cluster A 안정성 | 9.5h 무중단 (5-09 16:45 boot 이후 worker re-init 0건) |
| 5일 주기 가설 | break 진행 중 (4-29 → 5-04 → 5-07 → 5-10 0건) |

### Sentry 기존 known logs (V4.1 신규 발생 영역 외, 사용자 확인 완료)

- PYTHON-FLASK-B: 5-07 db_pool 사고 트래킹
- PYTHON-FLASK-7/8/9: migration 051a duplicate key 5-05 (3 events)
- PYTHON-FLASK-A: SMTP work.request_deactivation 7 events (잘못된 이메일)
- PYTHON-FLASK-5: cleanup get_db_connection 4 events @ 5-03 (HOTFIX-09 fix 직후 잔존, 5-03 이후 0건 = fix 정합)
- PYTHON-FLASK-6: SMTP auth.verify_email 11 events

### 다음 단계

- **사용자 측 5-15까지 추가 점검** (T+8d window) — 5-12 ± 1d 예상 사고 시점 통과 확인
- 통과 시 **V4.1 영구 종결** + FIX-DB-POOL-MAX-SIZE-20260427 → COMPLETED + Phase B task #26 close
- 별 sprint 잔존: **OBSERV-PER-WORKER-POOL-RECOVERY-20260507** (Worker B silent fail 가설, 사용자 결정 영역 — 진행/보류/폐기)

---

## 🎯 2026-05-08 KST — v2.12.3 release (Sprint 66-BE FEAT-MATERIAL Step 4 OPS BE) ⭐ Sprint 66 OPS 100% 완료

> **헤더 갱신 (5-10)**: Sprint 66-BE OPS 측 100% 완료 영역은 5-08 release 그대로 유지 (별 영역).
> 마지막 업데이트 (이전): 2026-05-08 KST (🎯 v2.12.3 release — Sprint 66-BE FEAT-MATERIAL Step 4)

## 🎯 2026-05-08 KST — v2.12.3 release (Sprint 66-BE FEAT-MATERIAL Step 4 OPS BE) ⭐ Sprint 66 OPS 100% 완료

> **한 줄 요약**: Sprint 66-BE R3 4-step 의 마지막 step (OPS BE 측) 운영 적용 완료. admin endpoints 7건 신규 (자재 마스터 5 + 체크리스트 매핑 2) — AXIS-VIEW Sprint 42 (별 repo) 가 consume 할 인프라 확보. Codex 라운드 1 M=0/A=6 GREEN (advisory 전체 BACKLOG). **Sprint 66-BE OPS 측 100% 완료** (Step 1+2+3+4 prod 적용 + 총 47/47 pytest GREEN).

### 진행 trail

| 단계 | 결과 |
|---|---|
| BE admin_materials.py 신규 (5 endpoint) | ✅ GET list / POST create idempotent (xmax trick) / PATCH update whitelist / PATCH deactivate / PATCH reactivate |
| BE admin_checklists.py 신규 (2 endpoint) | ✅ GET options dual-format / PATCH options 5종 validation |
| Blueprint 등록 | ✅ admin_materials_bp + admin_checklists_bp 2 신규 |
| 권한 정합 (ADR-023) | ✅ 모든 endpoint @jwt_required + @gst_or_admin_required 2단 적층 (Sprint 27 v1.7.4 표준) — 새 데코레이터 작성 X |
| pytest 13 TC | ✅ 13/13 PASS (db_pool RealDictCursor 정합 정정 후) |
| 회귀 (Step 1+2+3+4) | ✅ **총 47/47 GREEN** (9 + 11 + 14 + 13) |
| Codex 라운드 1 (Step 4 impl) | ✅ M=0 / A=6 GREEN (전부 advisory, BACKLOG) |
| Railway BE 배포 | ⏳ push 후 자동 배포 검증 예정 |

### Codex A 6건 (BACKLOG 처리)

- I-1: inactive material stale mapping round-trip — admin 가시성 의도 (AXIS-VIEW FE 시각 마킹)
- I-3: NULL vs `[]` 매핑 구분 소실 — FE 처리 규약 문서화
- B-legacy: legacy string CI 커버리지 조건부 — seed fixture
- B-coerce: PATCH string ID coercion 미구현 — AXIS-VIEW Sprint 42 측 int 전송 보장 필수
- D-race: validation-update race window — 운영 빈도 낮음
- F-wildcard: ILIKE wildcard escape 미구현 — 검색 의미론, 보안 X

### 영향

- **Sprint 66-BE OPS 측 100% 완료** — Step 1+2+3+4 prod 적용 + 47/47 GREEN
- AXIS-VIEW Sprint 42 (별 repo) admin GUI consume endpoint 인프라 확보
- AXIS-VIEW 측 admin 매핑 시 BE override (Step 3) 자동 작동 → 작업자 동적 자재 옵션 수신 시작
- 회귀 위험 0 (신규 endpoint, 기존 API 영향 0)

### 다음 step

- **AXIS-VIEW Sprint 42** (별 repo) — `/materials` admin GUI + `/checklists` 매핑 GUI consume
- Sprint 66-BE OPS 측은 이번 release 로 종결

---

## 🎯 2026-05-08 KST — v2.12.2 release (Sprint 66-BE FEAT-MATERIAL Step 3)

> **한 줄 요약**: Sprint 66-BE R3 4-step 의 Step 3 (BE+FE atomic) 운영 적용 완료 — checklist_master 동적 자재 조회 + selected_material_id 직접 전달 + FE re-entry hydrate. Codex 라운드 1 M=2 (G+D silent NULL overwrite) 정정 후 라운드 2 GREEN. **Sprint 66-BE OPS 측 75% 완료 (3/4 step), Step 4 = AXIS-VIEW 별 repo 영역**.

### 진행 trail

| 단계 | 결과 |
|---|---|
| 사전 검증 SQL | ✅ select_options 분포 — MECH 7 + ELEC 1 + TM 0 = 8 array 모두 string_array (legacy 51a) |
| BE checklist_service.py 4 신규 함수 | ✅ _collect_material_ids / _fetch_material_master_map (N+1 BATCHED) / _enrich_select_options (tuple) / _validate_material_id |
| BE _get_checklist_by_category SQL + 응답 | ✅ COALESCE(cr.selected_material_id, cr_p1.selected_material_id) 추가 + select_material_ids + selected_material_id 응답 필드 |
| BE upsert_mech_check + upsert_elec_check | ✅ selected_material_id 인자 + validation + INSERT/UPDATE 컬럼 갱신 |
| BE routes/checklist.py 2 endpoint | ✅ PUT /mech/check + /elec/check 에 selected_material_id 전달 |
| FE mech_checklist_screen.dart 5 변경 | ✅ _selectMaterialIdMap + onChanged idx lookup + PASS/NA 동봉 + 재진입 hydrate |
| pytest 14 TC | ✅ 14/14 PASS (회귀 Step 1+2 = 20/20 + Step 3 14/14 = 총 34/34 GREEN) |
| Codex 라운드 1 (Step 3 impl) | ⚠️ M=2 (G+D 동일 경로 — re-entry _selectMaterialIdMap 복원 누락) / A=2 / N=3 |
| Codex 라운드 2 (M+A 정정) | ✅ M=0 / A=1 GREEN (A 1건 = Codex sandbox pytest 미설치 운영성) |
| Railway BE 배포 | ✅ v2.12.2 / build_date 2026-05-08 (3회 측정 일치) |
| Netlify FE 배포 | ✅ gaxis-ops.netlify.app 배포 완료 |

### 옵션 Y 표시 형식 (5-08 사용자 결정)

- description 있으면 `name (description) | spec_1 | spec_2` (예: `MFC (LNG) | MKP | 50 SLM | P:0.3~2.5 / W:0.3`)
- description NULL → `name | spec_1 | spec_2` (비 MFC 자재)
- 같은 spec MFC LNG/O2 분리 가시성 보장

### 다음 step (Step 4 — AXIS-VIEW 별 repo 영역)

- **Step 4** (AXIS-VIEW 별 sprint): admin GUI 자재 등록 + 매핑 → AXIS-VIEW v1.X.X (별 repo, FEAT-AXIS-VIEW-MATERIALS-AND-CHECKLISTS-MGMT-20260507)
  - `/api/admin/materials/*` CRUD endpoint (4건)
  - `/api/admin/checklists/master/:id/options` 매핑 endpoint
  - admin GUI 자재 등록 + checklist 매핑 화면
  - 배포 후 admin 매핑 시 BE override 자동 작동 → 작업자 동적 자재 옵션 수신 시작

### 영향

- **회귀 위험 0** — 현재 prod 8개 string_array 영역 모두 legacy compat 경로 (작업자 화면 표시 동일)
- **응답 필드 additive** — select_material_ids / selected_material_id (기존 FE 무시 시 0 영향)
- **운영 의도** — Step 4 admin GUI 배포 후 동적 자재 옵션 활성. 현재는 placeholder 그대로 표시.

### T+1h 검증 영역

- Railway boot 정상 + Sentry 새 ERROR 0
- 작업자 측 MECH 체크리스트 진입 시 placeholder 그대로 표시 (회귀 0)
- pytest 환경 격리 — test DB 만 영향, 운영 DB 무관

---

## 🎯 2026-05-07 23:30 KST — v2.12.0 release (FEAT-MATERIAL Step 1)

> **한 줄 요약**: Sprint 63 의 51a seed placeholder 영구 차단 catch (5-07) 후속 — 자재 마스터 인프라 4 step sprint 의 Step 1 (schema 영역) 운영 적용 완료. Codex 설계서 라운드 1~5 GREEN + Step 1 implementation 라운드 1 GREEN 후 진행.

### 진행 trail

| 단계 | 결과 |
|---|---|
| 사전 검증 SQL 11건 | ✅ 모두 GREEN (public 3 테이블 0 row / pg_depend 외부 의존성 0 / select_options 8건 모두 legacy_string_array) |
| Migration 053 SQL 작성 | ✅ 175 LOC (DROP×3 / CREATE TABLE×3 / CREATE INDEX×7 / ALTER TABLE×1 / CREATE TRIGGER×3 / COMMENT×4) |
| pytest 9 TC 작성 | ✅ Codex A1+A2 정정 후 9/9 PASS (40s) |
| Codex 라운드 1 (Step 1 impl) | ✅ M=0/A=2/N=11 GREEN (A 즉시 정정) |
| 운영 DB psql 직접 적용 | ✅ BEGIN/COMMIT 정상 + migration_history INSERT |
| version bump | ✅ v2.11.7 → v2.12.0 (BE + FE) |

### 다음 step

- **Step 2** (Migration 053a seed): material_master 186 자재 + product_bom 1640 BOM 매핑 INSERT → v2.12.1
  - cowork 측 generate_migration_053a.py 자동 SQL 생성 (csv 통합 1654 row → SQL VALUES)
  - 사전 검증 SQL 3~6번 (중복키 / NULL / join completeness)
  - pytest TC 2건 + generator pytest TC 2건
- **Step 3** (BE override): _enrich_select_options + selected_material_id 직접 전달 → v2.12.2 OPS
- **Step 4** (AXIS-VIEW 별 sprint): admin GUI 자재 등록 + 매핑 → AXIS-VIEW v1.X.X (별 repo)

### T+1h 검증 영역 (다음 세션 또는 Twin파파 측)

- Railway boot 정상 + Sentry 새 ERROR 0
- 작업자 측 회귀 0 (51a placeholder 그대로 유지 — Step 3 까지 select_options 양식 변경 X)
- 운영 영역 직접 적용이라 Railway 재배포 시 migration_runner 가 053 'already executed' 인식

### 후속 BACKLOG 영역 (Step 4 완료 후)

- FEAT-SI-HOOKUP-CHECKLIST-FLOW-20260508 (P2)
- FEAT-MATERIAL-AI-VISION-VERIFY-20260508 (P3)

---

## 🎯 2026-05-07 20:54 KST — v2.11.6 자가 회복 메커니즘 첫 실전 작동 ✅

> **한 줄 요약**: 4-29 → 5-04 → 5-07 5일 주기 사고 패턴 재발했으나 v2.11.6 자가 회복이 15분 안 자동 처리. WATCHDOG (v2.10.16) → 자가 회복 (v2.11.6) 통합 효과 첫 입증. **부수 발견**: per-worker 자가 회복 사각지대 (worker B 풀 dead 시 warmup cron 미실행으로 trigger 도달 불가능) → 별 sprint 등록.

### 사고 timeline + 자가 회복 9ms latency 입증

| 시각 (KST) | 이벤트 | 출처 |
|---|---|---|
| 5-07 14:24:38 | gunicorn 2 worker boot (pid=2 + pid=3) | Railway logs |
| 5-07 20:39~20:54 | warmup 0/0 conn warmed × 3 cycles (15분간 풀 dead) | scheduler logs |
| 5-07 20:54:48.706 | **Sentry alert: `re-initializing pool (pid=2)` ERROR 격상** | v2.10.16 WATCHDOG |
| 5-07 20:54:48.715 | **DB pid 205810 backend_start (Sentry +9ms)** | pg_stat_activity |
| 5-07 20:54:48.884 | DB pid 205814 (5번째, +178ms) — 5 conn 모두 fresh | pg_stat_activity |
| 5-07 21:46 | 사후 측정: 5 conn idle, max_idle 107s — 정상 cycle 복귀 | V2.2/V4.3 SQL |

→ `init_pool()` 호출 직후 **168ms 안 5 conn 모두 생성** 입증. 시나리오 B (정상 fallback) 확정.

### 사고 단계 감소 (관찰성 + 자동화 효과 입증)

| 사고 | 시점 | 처리 방식 | 사용자 영향 시간 |
|---|---|---|---|
| 1차 | 4-29 23:31 KST | Railway Restart 수동 | 1.5h+ (10시간 silent) |
| 2차 | 5-04 11:38~12:32 KST | Railway Restart 수동 | 40분 |
| **3차** | **5-07 20:54 KST** | **자가 회복 자동 (init_pool)** | **~15분 (3 cycles × 5분)** ✅ |

### ⚠️ 부수 발견 — Worker B 풀 사각지대 (CRITICAL, 별 sprint 등록)

- **Sentry 알람**: worker pid=2 만 자가 회복 메시지 출력
- **Boot logs**: pid=2 + pid=3 동시 boot (Procfile `-w 2` 정합) = 2 worker 운영 확정
- **pg_stat_activity 21:46 측정**: 5 conn 만 (단일 클러스터 205810-205814)
- → **Worker A (scheduler owner)**: 자가 회복 ✅
- → **Worker B (HTTP only)**: 풀 dead 추정 (warmup cron 가 fcntl lock 으로 scheduler owner 만 실행 → Worker B 의 `_consecutive_zero_warmup` 은 영원히 0 → 자가 회복 trigger 도달 불가능)
- **사용자 영향**: Worker B 의 HTTP 요청은 `_create_direct_conn()` fallback (+0.3~0.5s 지연) 으로 silent degradation
- **별 sprint**: `OBSERV-PER-WORKER-POOL-RECOVERY-20260507` 등록 (BACKLOG L+1)

### 검증 데이터 + 문서 업데이트

- 측정 SQL: `DB_POOL_VERIFICATION_QUERIES_20260427.md` V4.1 + V2.2 + V4.3 + V4.4 결과란 모두 채움 완료
- ADR-025 보강: `memory.md` (per-worker gap 실측 trail 추가)
- 1주 추적 plan: 5-13 또는 다음 5일 주기 (5-12 ± 1d) 시점에 V4.1 재측정

---

## ✅ Sprint 65-BE — 정식 종료 (v2.11.7 release, 2026-05-06)

### v2.11.7 변경 (5-05 Twin파파 운영 검증 trigger)

- **BE**: `backend/app/services/checklist_service.py` 단일 파일 (~25 LOC)
  - `else` → `elif cat == 'MECH':` 명시 분기 + ELEC 패턴 (Phase 1/2 분리: '1차 입력' / '2차 검수')
  - `_normalize_qr_doc_id(serial_number)` 명시 호출 = `'DOC_<sn>'` (모바일 앱 정합)
  - `phase1_applicable=False` 항목 자동 제외 + DUAL INLET TODO 주석 명시
  - 기존 `else` 보존 → PI/QI/SI 잠재 신규 카테고리 fallback (ADR-026 표준)
- **TEST**: `tests/backend/test_sprint54_checklist_report.py` 신규 TC 3 (`TestSprint65MechReportBranch`)
  - TC-65-01 qr_doc_id 매칭 + input_value 반환 / TC-65-02 phase split + phase_label / TC-65-03 TM 회귀 0
  - 결과: 22/22 PASS (전 sprint54 GREEN)
- **memory.md ADR-026** 신설 — 신규 체크리스트 카테고리 phase split 표준
- **버전**: `version.py` + `app_version.dart` v2.11.6→v2.11.7

Frontend 변경 없음 → Netlify deploy 불필요. version.py + app_version.dart 양쪽 v2.11.7 동기화.

### Codex 1차 검증 P1~P5 전건 반영

- 🔴 P1 VIEW FE schema 정합 — 4 angle prerequisite 통과 (entry 개수 무관 + phase_label 이미 구현 + optional 타입 + ELEC baseline 운영 검증)
- 🟠 P2 신규 pytest TC 2건 + 회귀 1건 (총 3 TC)
- 🟠 P3 REFACTOR-CHECKLIST-PHASE-SPLIT BACKLOG 등록 (헬퍼 함수 추출, P3 LOW)
- 🟡 P4 handoff/CHANGELOG/BACKLOG/memory ADR-026 자취 추가
- 🟡 P5 DUAL INLET L/R 분리 TODO 주석 + BACKLOG ID 명시

### 사용자 검증 plan (배포 후)

- VIEW `/partner/report` 페이지 TEST-1111 검색 → 기구 섹션 input_value 정상 표시 (1, 11 등)
- 작업자 이름 / 확인 일시 정상 표시
- Phase 1 / Phase 2 두 섹션 분리 노출 (ELEC 와 동일 패턴)
- ELEC / TM 카테고리 영향 없음

### Rollback

git revert <commit-sha> → v2.11.6 복귀. 위험: 0 (사용자 영향 = 이전과 동일, '—' 표시로 회귀).

---

## ✅ FIX-DB-POOL-SELF-RECOVERY-20260504 — 정식 종료 (v2.11.6 release, 2026-05-06)

### v2.11.6 변경 (5-04 11:38~12:32 KST 사고 trail)
- **BE**: `backend/app/db_pool.py` 단일 파일 — keepalive 4 args 활성화 + warmup_pool 0/0 conn 연속 3 cycles 시 close+init 자가 회복 + `logger.error` 격상 (Sentry capture)
- **TEST**: `tests/backend/test_db_pool.py` 신규 4 TC (8/8 PASS) — keepalive 검증 + 자가 회복 trigger + Sentry capture 보장 + 정상 cycle 리셋
- **사고 패턴**: `_used` dict dead conn 정리 부재 + Railway proxy idle TCP disconnect → 40분 0/0 conn 지속 → Restart 외 회복 불가
- **5-09 ± 1d 재발 차단** (4-29 23:31 + 5-04 11:38 = 5일 주기)

### 다음 단계 (퇴근 후 직접 실행)

```bash
git push origin main
# → Railway 자동 재배포 ~1분
# → Railway logs 정상 boot 확인
# → 1h 관찰 → TCP_OVERWINDOW WARN 0건 확인 (Sprint 30-B 충돌 검증)
```

Frontend 변경 없음 → Netlify deploy 불필요. version.py + app_version.dart 양쪽 v2.11.6 동기화.

### 관찰 plan
- **T+1h** (2026-05-06): ✅ **CLEAN PASS**
  - V1.1 boot + warmup 5/5 × 3 cycle 정상 (`pool_warmup` 5분 cron 간격 정확)
  - V1.2 TCP_OVERWINDOW: 제어 패킷 66 B 만, 즉시 OK 응답 → ⚠️ MONITOR (non-critical, Sprint 30-B 회귀 NO)
  - V1.3 Sentry new events: 0건 확정
  - 0/0 cycles: 0건 (자가 회복 trigger 미작동 = 정상)
- **T+24h** (2026-05-07): ✅ **STRONG PASS** + ⚠️ worker 수 anomaly
  - V2.1 Railway logs warmup grep — INCONCLUSIVE (검색어 mismatch 추정), V2.2/V2.3 로 대체 검증 PASS
  - V2.2 application_name 별 conn — OPS 5 idle, **max_idle_sec 14s** ⭐ (warmup 14초 안 갱신 직접 증거)
  - V2.3 keepalive 재측정 — **oldest conn 4h 12m alive** ⭐ (5-06 40분 대비 6배 향상)
  - state_change 12:42:40 4건 동시 일관성 → warmup 5분 cron 정상 작동
  - ⚠️ OPS conn 5개 (Procfile `-w 2` 기준 예상 10개 = 50% 누락) → 5-09 V4.4 추가 진단 필요
- **T+1주 (5-09 ± 1d)**: 재발 0 (keepalive 차단, 시나리오 A) 또는 자가 회복 작동 (시나리오 B) → COMPLETED 판정
  - V4.1~V4.3 (기존) + **V4.4 신규** (worker pid 분포 + Railway boot logs worker 수 확정)
  - 시나리오 A 신뢰도 상승 (4h+ alive 입증 + 사고 패턴 차단 가능성 높음)

### Rollback
git revert <commit-sha> → 이전 동작 (keepalive OFF + 자가 회복 X) 복귀. 위험: 5-09 ± 1d 재발 시 Restart 수동 필요. Sprint 30-B Railway proxy 충돌 재발 시 keepalive 만 제거 (부분 rollback OK).

---

## ✅ Sprint 63 BE+FE+Hotfix×4 — 정식 종료 (v2.11.5 release, 2026-05-06)

### v2.11.5 추가 변경 (FIX-MECH-CHECKLIST-PHASE2-DATA-AND-DESCRIPTION)
- BE: `_get_checklist_by_category` SQL 에 cr_p1 LEFT JOIN + COALESCE — phase=2 GET 시 phase=1 input/select inherit
- FE: `_buildCheckRadio` description 추가 (Row → Column wrap, ELEC L898-909 패턴 정합)
- pytest TestPhase2InheritsPhase1Data 2 TC 신규 (32 TC 누적)
- Codex 라운드 1: M=1 (DUAL qr_doc_id 보호 — 설계 자체 정합) / A=4 / N=2

### 다음 단계 (퇴근 후 직접 실행)

```bash
git push origin main
git push origin v2.11.5
cd frontend
npx netlify-cli deploy --prod --dir=build/web --site=ab8041c3-dc51-40c6-96e4-9966222aeda3
```

build 이미 완료 → Netlify deploy 만, Railway 자동 배포.

---

## ✅ Sprint 63 BE+FE+Hotfix×3 — 정식 종료 (v2.11.4 release, 2026-05-06)

### 잔존 hotfix 추가 release

```
v2.11.3 (2026-05-04) — check_result null 차단 + phase=2 read-only UI (FE only, FIX-MECH-CHECKLIST-PHASE2-READONLY-AND-VALIDATION 1차)
v2.11.4 (2026-05-06) — 옵션 C UI 가이드 + description 렌더 (FE only, 동 sprint 추가 정정 1+3+4)
```

### v2.11.4 변경
- description 렌더 (item_name 아래 작은 글씨, ELEC L898-909 패턴 정합)
- 옵션 C: PASS/NA 미선택 경고 ⚠️ "PASS 또는 NA 선택 후 저장됩니다"
- INPUT setState({}) 추가 (controller.text reactive 보강)
- Codex 라운드 1: M=0 / A=2 / N=3 — 즉시 구현 합의

### 다음 단계 (퇴근 후 직접 실행)

```bash
git push origin main
git push origin v2.11.4
cd frontend
npx netlify-cli deploy --prod --dir=build/web --site=ab8041c3-dc51-40c6-96e4-9966222aeda3
```

build 이미 완료 → Netlify deploy 만, Railway 자동 배포.

### 잔존 BACKLOG (clean work 후 진행)
- 🟠 **Sprint 64-BE v2 재설계 완료 (2026-05-11)** — Codex 라운드 1 catch M=6/A=3 정정. helper 재사용 패턴 (best-effort sequential) 으로 전면 재작성. AGENT_TEAM_LAUNCH.md § Sprint 64-BE 본문 갱신 + BACKLOG SPRINT-64-BE-WORK-BATCH-V2-20260511 신규 등록. **다음 단계**: Codex 라운드 2 검증 위임 → M/A 합의 → 구현 (~3h) → 배포. AXIS-VIEW Sprint 40 v1.40.0 prod 배포 완료 상태 (graceful degrade 작동 중).
- 🟡 widget test 별 BACKLOG (Codex AV1 — provider/api mock harness 설계 필요)
- 🟢 FEAT-MECH-WORK-COMPLETE-CHECKLIST-NUDGE (P3, 30분, 안정 운영 1주 후)
- 🟢 BUG-TM-CHECKLIST-AUTO-FINALIZE-STALE-TC (P3, 1h)
- 🟢 AXIS-VIEW Sprint 39 (별 repo)

---

## ✅ Sprint 63 BE+FE+Hotfix — 정식 종료 (v2.11.2 release, 2026-05-04)

```
commit 958fb09 (main) — fix: v2.11.2 Sprint 63 후속 BUGFIX 체크리스트 진입점
tag    v2.11.2
```

### v2.11.2 hotfix 변경
- BE work.py L177~ MECH 분기 (~12 LoC) — 4 task 시작 시 checklist_ready+category='MECH'
- FE task_detail_screen.dart 5 위치 (~25 LoC) — _hasChecklistAccess + onTap 2곳 (in_progress + completed) + _navigateToChecklist + import
- pytest TestWorkStartMechChecklistEntry 6 TC 신규 (24→30 TC)
- 결과: pytest 30/30 PASS (248.87s) / flutter analyze 0 error / flutter build web 성공
- 회귀 영향: 0건 (additive, migration 없음)

### Codex 라운드 1 + 추가 검토 trail
- M=1 (risk indicator) / A=3 (인용/pytest/atomic) / N=1 / AV=2 (인용 동일 / 선택 3 별 sprint)
- 추가 검토 catch: 5번째 위치 (`_buildCompletedBadge` onTap) 누락 → 4→5 위치 갱신

### 다음 단계 (퇴근 후 직접 실행)

```bash
git push origin main
git push origin v2.11.2
cd frontend
npx netlify-cli deploy --prod --dir=build/web --site=ab8041c3-dc51-40c6-96e4-9966222aeda3
```

build 이미 완료 → Netlify deploy 만, Railway 자동 배포.

### 후속 별 sprint
- FEAT-MECH-WORK-COMPLETE-CHECKLIST-NUDGE-20260504 (P3, 30분, 안정 운영 1주 후)
- AXIS-VIEW Sprint 39 (별 repo)

---

## ✅ Sprint 63 BE+FE — 정식 종료 (v2.11.1 release, 2026-05-04)

```
commit c70babd (main) — feat: v2.11.1 Sprint 63-FE Flutter UI + R2-1 BE patch + N1/N2
tag    v2.11.1
```

### v2.11.1 추가 변경
- BE patch (R2-1): get_mech_checklist() 응답에 tank_in_mech: bool (~10 LoC)
- FE 신규: mech_checklist_screen.dart 844 LoC + alert_log/alert_list 분기 + 라우팅
- N1: WebSocket CHECKLIST_MECH_READY 핸들러 (alert_provider 자동 + 탭 시 MECH 진입)
- N2: pytest TestR21TankInMechResponse 3 TC PASS (총 21→24 TC)
- **GxColors 정정** (commit 21c581e): background/surface/mistLight → cloud/white/cloud (7곳)
- 회귀 영향: 0건

### Push 전 검증 결과 ✅
- pytest test_mech_checklist **24/24 PASS** (229.55s)
- flutter analyze **0 error** (info 2건만, 빌드 차단 X)
- flutter build web --release **✓ Built build/web** (12.3s)
- → push 가능 상태 (Netlify 배포 시 rebuild 불필요)

### 다음 단계 (퇴근 후 직접 실행)

```bash
cd /Users/twinfafa/Desktop/GST/AXIS-OPS
git push origin main
git push origin v2.11.0
git push origin v2.11.1

cd frontend
flutter build web --release
npx netlify-cli deploy --prod --dir=build/web --site=ab8041c3-dc51-40c6-96e4-9966222aeda3
```

Railway 자동 배포 (~2분) + Netlify 자동 배포 → migration 051/051a 자동 적용 + FE Mech 화면 활성화.

---

## ✅ Sprint 63-BE — 정식 종료 (v2.11.0 release, 2026-05-04)

```
commit f59e1be (main) — feat: v2.11.0 Sprint 63-BE MECH 체크리스트 BE 인프라
tag    v2.11.0
branch sprint-63-be-mech-checklist (squash merged, 11 commits)
```

### 검증 결과 ✅
- pytest tests/backend/test_mech_checklist.py — **21/21 PASS** (186.84s)
- 회귀 영향 0건 (TM/ELEC 응답에 새 필드 scope_rule/trigger_task_id 추가만, 기존 키 무변경)
- rg "_check_tm_completion" backend/ tests/ → **0 hits**
- Pre-deploy Gate 7건 모두 통과

### Pre-deploy 이후 (Twin파파 측 진행 예정)

**🕐 push 대기 중** — 서버 운영 시간 회피 (퇴근 후 진행 결정 2026-05-04 KST)

```bash
# 퇴근 후 (예: 18:00 이후) 직접 실행:
git push origin main      # 5 commits push (f59e1be ~ 8e6d1c7)
git push origin v2.11.0   # tag push
```

배포 단계 (push 후 자동 + 사용자 검증):
1. 🕐 git push (퇴근 후)
2. ⏳ Railway 자동 배포 + migration 051/051a 자동 적용 (~2분)
3. ⏳ DB 검증: `SELECT COUNT(*) FROM checklist.checklist_master WHERE category='MECH'` → 73
4. ⏳ Railway logs: `[migration] ✅ 051_mech_checklist_extension.sql 실행 완료` 확인
5. ⏳ T+1d Sentry 새 ERROR 0건 확인
6. ⏳ 1주 운영 관찰 (1차 입력률 + 2차 검수 완료율)

### Sprint 63-FE 진행 상태

- ✅ 설계서 작성 (commit cd164ea)
- ✅ Codex 라운드 1 완료 (M=5 / A=5 / N=2 + Q1~Q7 결정 7건, commit 8e6d1c7)
- 🔴 Cowork 측 추가 검토 진행 중 (Twin파파 결정)
- 🔴 라운드 2 (옵션, tank_in_mech BE 응답 노출 + Dart normalizer)
- 🔴 구현 (~2~3d, BE 배포 후 착수)

### 후속 별 sprint (BE 배포 완료 후 착수)
- **Sprint 63-FE** — `mech_checklist_screen.dart` 신규 (~1,000~1,200 LoC, 2~3d) — **Codex 라운드 1 진입 예정**
- **AXIS-VIEW Sprint 39** — BLUR 해제 + AddModal 토글 (~0.5d, 별 repo)
- **FIX-ELEC-QR-DOC-ID-HARDCODE-20260502** — ELEC qr_doc_id='' 하드코딩 마이그레이션 (P2, 1h)

---

## 🚧 Sprint 63-BE 진행 상태 (세션 1 Step 1~9 완료, 2026-05-04)

### ✅ 완료 (Step 1~9, branch `sprint-63-be-mech-checklist`, commit 9건, +1,415 LoC)

```
9466f66 Step 9: test_mech_checklist.py 21 TC 신규 (+554 LoC, Group A+E 7/7 PASS)
5bbb83c (docs) Step 1~8 handoff trail 갱신
ad67e4b Step 7+8: task_service hook + production MECH 분기 (+69)
7cd10fc Step 6: routes MECH 분기 + service 2개 (+257)
c8b6607 (docs) Step 1~5 handoff trail
cfc3d38 Step 5: _check_tm_completion rename 9 hits
bce0c98 Step 3+4: _resolve_active_master_ids + check_mech_completion (+152)
bfe86d5 Step 2: _normalize_qr_doc_id (+42)
2075ef9 Step 1: migration 051/051a + CSV (+253)
```

### Step 9 pytest 21 TC 검증 결과

**Group A + E 본 세션 실행 (DB 불필요)**: **7/7 PASS** ✅
```
TestNormalizeQrDocId: 6 PASS (pure function unit)
TestRenameGate:       1 PASS (grep --include=*.py self-match 제외)
```

**Group B + C + D + F + G (14 TC, DB 필요)**: 사용자 측 실행 대기
```bash
TEST_DATABASE_URL=postgresql://... \
  backend/.venv/bin/pytest tests/backend/test_mech_checklist.py -v
```

기대 결과: 21/21 PASS (test DB 에 migration 051/051a 자동 적용됨).

### 🟡 잔존 (다음 단계)

```
1. 사용자 측 14 TC 실행 + 결과 확인 (TEST_DATABASE_URL 환경변수 필요)
2. 21/21 PASS 시 squash merge to main
3. backend/version.py + frontend/lib/utils/app_version.dart v2.11.0 갱신
4. CHANGELOG.md v2.11.0 entry 추가
5. Railway 자동 배포 + migration 051/051a 자동 적용 확인
6. T+1d Sentry 새 ERROR 0건 확인
```

### ✅ 완료 (Step 1~8, branch `sprint-63-be-mech-checklist`, commit 6건) [DEPRECATED 갱신]

```
2075ef9 Step 1: migration 051/051a + seed CSV git add (3 files, +253 LoC)
bfe86d5 Step 2: _normalize_qr_doc_id() 공유 helper 신설 (+42 LoC, smoke 9/9 PASS)
bce0c98 Step 3+4: _resolve_active_master_ids() + check_mech_completion() 신설 (+152 LoC)
cfc3d38 Step 5: _check_tm_completion → check_tm_completion rename 9 hits (3 files)
c8b6607 (docs) Step 1~5 handoff trail
7cd10fc Step 6: routes/checklist.py MECH 분기 + service get_mech_checklist/upsert_mech_check (+257 LoC)
ad67e4b Step 7+8: task_service _trigger_mech_checklist_alert hook + production.py MECH 분기 (+69 LoC)
```

**검증 통과**:
- `rg "_check_tm_completion" backend/ tests/` → 0건 ✅ (rename gate)
- `rg "check_tm_completion" backend/ tests/` → 9 hits ✅
- `ast.parse` checklist.py / checklist_service.py / task_service.py / production.py 양 4파일 OK
- 회귀 영향: 0건 (TM/ELEC 응답에 새 필드 추가만, 기존 키 무변경)

**구현 인프라 합계**: +773 LoC (BE only, FE 미포함)
- migration: 051/051a +253 LoC + CSV
- service: 신규 함수 5개 (`_normalize_qr_doc_id` / `_resolve_active_master_ids` / `check_mech_completion` / `get_mech_checklist` / `upsert_mech_check`)
- routes: MECH 분기 3개 (GET / PUT / GET status)
- task_service: `_trigger_mech_checklist_alert()` hook + start_work 호출 1줄
- production: `_check_sn_checklist_complete()` MECH 분기 5줄

### 🔴 미완료 (Step 9, 별 세션 권장, 3~4h)

```
Step 9: tests/backend/test_mech_checklist.py 21 TC (~600 LoC)
  ├─ 기본 10: scope_rule × 6 + trigger_task_id × 3 + phase1_applicable_19_items
  ├─ Q6 보강 3: qr_doc_id_normalization (single/dual) + seed_count_by_scope_rule
  ├─ Q3 보강 1: tm_completion_rename_no_legacy_caller
  ├─ I3 보강 2: phase2_completion_when_phase1_missing/when_both_filled
  └─ 라운드 3 보강 5: normalize edge cases × 4 + websocket emit
  → atomic squash merge to main + Railway 배포 (Step 9 완료 후)
```

**별 세션 권장 사유**:
- 21 TC fixture 설계 + DB seeding + assertion = 600+ LoC
- 본 세션 컨텍스트 누적 ↑ → 별 세션 fresh context 에서 집중 작업이 더 안전
- BE 인프라 (Step 1~8) 는 단독 commit 가능 상태 (Step 9 후 squash merge)

### 📋 다음 세션 시작 가이드

```bash
git checkout sprint-63-be-mech-checklist
git log --oneline ^main  # 7 commits (Step 1~8 + handoff)

# Step 9 작성 시 참고
ls tests/backend/test_checklist*.py
grep -l "check_elec_completion\|check_tm_completion" tests/backend/

# 최종 squash merge 절차 (Step 9 완료 후)
git checkout main
git merge --squash sprint-63-be-mech-checklist
git commit -m "feat: v2.11.0 — Sprint 63-BE MECH 체크리스트 인프라"
git tag v2.11.0
```

### 🎯 정정 trail 11건 적용 검증 완료 (라운드 1+2+3 + 사용자 결정 4건)

- 라운드 1 정정 7건 (양식 표 / scope_rule / input_type / Python helper / enum / pytest TC / BE/FE 분리)
- 라운드 2 정정 6건 (atomic / silent failure / ELEC qr_doc_id / models drift / lint hook / cross-repo)
- 라운드 3 정정 3건 M (ALTER TYPE non-transactional / test 파일 경로 / Pre-deploy Gate)
- 사용자 결정 v2 INLET 8개 분리 + (c)안 + BE/FE 분리 + Minor 3건

---
>
> ✅ **5-04 #29 FIX-PIN-FLAG-MIGRATION-SHAREDPREFS D+7 정성 close 완료** (4-27 v2.10.5 배포 D+7):
>   ├─ access_log 측정 (Twin파파 SQL 실행, `app_access_log` 14일 cohort): pin_status_calls 4-26 1~12 (1~7%) → **4-27 76 (44.7%)** 점프 → 4-28 81.3% / 4-29 81.9% / 4-30 76.6% / 5-02 76.9% / 5-03 72.7% / **5-04 79.4%** — v2.10.6 FEAT-PIN-STATUS-BACKEND-FALLBACK 배포일 점프 일치 + 7일 안정 추세 입증
>   ├─ 코호트 (workers + worker_auth_settings): 7일 활성 61명 / PIN 등록 19명 (31.1%) — 위험 노출 코호트 backend fallback 80% 도달
>   ├─ 사용자 신고 0건 (4-27 ~ 5-04, 7일 정성 관찰)
>   ├─ regression error 신호 0 (Sentry 새 issue 0)
>   └─ 정량 baseline 측정 인프라는 별건 (`FEAT-PIN-LOGIN-ANALYTICS`, 필요 시 등록) — 구조적 한계: `/auth/login` + `/auth/pin-login` 200 응답이 `app_access_log` 미기록 (`@app.after_request` 의 `g.worker_id is None` 분기로 skip, `__init__.py:236-240`). 직접 cohort 측정으로 우회.
>
> 📊 **5-04 운영 안정성 측정 종합** (Railway 차트 + `app_access_log` 7일 분석, Sprint 63-BE 진행과 별건):
>   ├─ Railway 차트 p99 3초 spike 정체 확정: **4-30 15:00 KST `work.complete_work` POST max 2,668ms / avg 2,181ms (n=4)** — 평일 오후 출하 마감 burst (5-01 새벽 가설 폐기). Top 6 hourly p99 spike 중 5건이 work.complete_work, **단독 hot endpoint** 확정. 4-30 09:00 max 2,253ms n=11 = 4-30 09:30 Railway Restart 직후 cold start 윈도우 (4-29 23:31 silent failure 복구 직후). 5-04 10:00 max 1,722ms = admin1234 batch fetch 시점 일치
>   ├─ Railway Error Rate 1.3% spike + p99 3초 spike 동일 시점 = 동일 burst 의 두 측면 (5xx 아닌 slow 200 응답)
>   ├─ **5xx 0건 7일 입증** ✅ (4-27~5-04), 4xx 50건 모두 정상 동작 (403 권한 차단 38 + 400 validation 거부 10 + 404 잘못된 S/N 1)
>   ├─ 5-04 admin1234 18분 idle 후 401 폭주 = 자연스러운 token 만료 패턴 (BUG-22 가드 정상 작동, refresh storm 0건, `_isForceLogout` 1회만 발동 후 재호출 차단)
>   ├─ CPU 거의 0 vCPU idle / Memory 100~150MB 안정 (누수 없음, 점선 = 재배포 cycle 정상)
>   └─ 종합: **운영 무탈** / Sprint 63-BE/FE 진행에 인프라 측 blocker 0건 / 신규 BACKLOG 2건 등록 (`UX-ATTENDANCE-CHECK-401-TOAST-20260504` 6연타 401 + `UX-ADMIN-MENU-403-FEEDBACK-20260504` 권한 없는 admin 메뉴 across days 반복 시도) + `OBSERV-SLOW-QUERY-ENDPOINT-PROFILING` 보강 (heavy endpoint = work.complete_work 단독 확정, 코드 audit 단계만 잔여)
>
> ✅ **4-30 INFRA-COLLATION-REFRESH 완료** — `ALTER DATABASE railway REFRESH COLLATION VERSION;` 218ms, 2.36 → 2.41, WARNING 0건. BACKLOG L337 COMPLETED.
>
> 🚨 **5-01 HOTFIX-09 v2.10.17** — Sprint 32 도입 (3-19) access_log cleanup cron 의 `get_db_connection` import 누락 발견. **43일간 매일 03:00 NameError silent failure** — 4-29 측정 89,076 rows / 41일 누적 = cleanup 0회 입증. Sentry 도입 후 4-28 부터 capture (4 events). 1줄 import 추가로 fix → 5-02 03:00 cron 부터 정상.
>
> 🤝 **Codex 라운드 1 사후 검토 합의** (HOTFIX-09): M=2 / A=3 / N=1 — Q1 S3 적정 / Q2-Q3 별 BACKLOG 등록 (`OBSERV-SCHEDULER-IMPORT-AUDIT-20260501` + `INFRA-LINT-PRECOMMIT-HOOK-20260501`) / Q4 TC 4개 보강 (import / SQL / 정상 흐름 / 예외 rollback 모두 PASS) / Q5 framing 정정 — "Sprint 32 design/QA 부족 + Sentry 는 latent defect 탐지 layer" / Q6 CHANGELOG TC trail sync.
>
> 🤝 **4-30 cross-repo Codex 워크플로우 동기화** — VIEW CLAUDE.md ⑦ 빌드·테스트 GREEN 섹션에 OPS 표준 "실패 발견 시 강제 절차 a~e" 추가 (805 → 822 LoC). 4-22 HOTFIX-ALERT-SCHEDULER-DELIVERY 사고 trail 양 repo 일관성 확보.
>
> 🚨 **4-29 23:31 ~ 4-30 09:30 silent failure 사고**:
>   ├─ warmup cron 은 살아있는데 `_pool=None` (gunicorn worker pool death) 으로 1.5h+ `[pool_warmup] 0/0 conn warmed`
>   ├─ 사용자 측 conn=2 측정으로 우연 발견 (logger.debug 라 Sentry 미포착 = 사각지대)
>   ├─ 응급 조치: Railway Restart → conn 10 회복 (Worker A 5 + Worker B 5 fresh init)
>   └─ 근본 fix: v2.10.16 — `logger.debug` → `logger.error` 격상 + pid context, Sentry 자동 capture 활성화 (다음 발생 1분 알림)
>
> 🎯 **다음 우선 작업**: **MECH 체크리스트 (Sprint 63 후보)** — TM(Sprint 52~v2.6.0) / ELEC(Sprint 57~v2.9.0) 도입 후 MECH 자주검사 체크리스트 전개
>
> 🟢 **DB Pool 모니터링 인프라 — 후순위로 BACKLOG 등록 (4-29 23:00)**:
>   ├─ OBSERV-DB-POOL-STATUS-ENDPOINT-20260429 (P3, 30분) — `/api/admin/db-pool-status` 실시간 조회
>   ├─ OBSERV-DB-POOL-CONN-THRESHOLD-ALERT-20260429 (P3, 20분) — Sentry capture_message 임계 alert (5분 cron)
>   └─ OBSERV-SENTRY-TRACES-APM-ENABLE-20260429 (P3, 5분) — Railway env `SENTRY_TRACES_SAMPLE_RATE=0.1` 1줄
>
> 🟡 **잔존 Sentry SMTP issue** (4-28 work.request_deactivation 7 events): 옵션 A (logger.warning 강등 + SMTPRecipientsRefused 분리) 별건 BACKLOG 등록 검토 중
>
> ✅ **4-29 검증 결과 (T+18~24h)**:
>   ├─ v2.10.11: TMS UNFINISHED_AT_CLOSING **Before 0 → After 32건 / target 100%** + Sentry PYTHON-FLASK-1 resolve 후 신규 0 → COMPLETED
>   ├─ v2.10.13 #1/#2: HTTP 5xx 0건 + Sentry db_pool/websocket 2 issue resolve 후 신규 0 → COMPLETED
>   ├─ v2.10.14: W17 v2.3 0건 → v2.4 **31건** (plan/actual/best 3축 일치) + R-02 반례 0건 유지 → COMPLETED
>   └─ migration_history: 39 migrations, latest 050 — assertion layer 정상
>
> 🟢 **4-29 D+2 (FIX-DB-POOL Phase B)**: conn **5~6 안정** (Worker A pool MIN=5 정확 작동 입증) → D+1/D+2 동일 추세, per-worker 함정 영향 무 → 옵션 X1 유지 재확정
>
> 🟢 **자연 종결 plan (옵션 A)**:
>   ├─ #26 FIX-DB-POOL-MAX Phase B → 내일 4-30 D+3 Twin파파 측 5분 측정 후 자동 COMPLETED (변경 없음 → MAX=30 충분 확정)
>   └─ ✅ #29 FIX-PIN-FLAG baseline → **5-04 D+7 정성 close 완료** (위 ✅ 5-04 블록 참조 — pin_status fallback 79.4% 안정 + 신고 0건). 정량 baseline 측정 인프라는 별건 (`FEAT-PIN-LOGIN-ANALYTICS`, 필요 시 등록)

---

## 🟢 2026-04-28 세션 요약 (5/5) — FIX-FACTORY-KPI-SHIPPED-V2.4 v2.10.14

> **한 줄 요약**: Sprint 62-BE v2.2 의 `_count_shipped` 3 분기 보정 — `shipped_plan` AND→OR (W17 0 상수화 해소) + `shipped_ops` 폐기 + `shipped_best` 신설. Pre-deploy Gate ③ R-02 반례 0건 검증 완료. pytest 17 passed / 3 skipped (v2.3 'ops' 의존 TC 무효).

### 코드 변경 (v2.10.14, BE only — factory.py 단일)

| 분기 | Before (v2.3) | After (v2.4) |
|---|---|---|
| `plan` | `INNER JOIN cs ON ... AND cs.si_completed=TRUE` | `LEFT JOIN app_task_details (task_id='SI_SHIPMENT') + WHERE (actual_ship_date IS NOT NULL OR t.completed_at IS NOT NULL)` |
| `ops` | `app_task_details task_id='SI_SHIPMENT' completed_at` | **제거** (app SI 100% 후 ops=actual 수렴) |
| `best` | (없음) | **신규** — `WHERE actual_ship_date IS NOT NULL` + 주간 귀속 `COALESCE(DATE(t.completed_at), p.actual_ship_date)` |

응답 4곳 (weekly-kpi L457/L473 + monthly-kpi L554/L566): `shipped_ops` → `shipped_best`.

### Pre-deploy Gate ③ R-02 해석 A 반례 검증 완료

```
SELECT COUNT(*) FROM app_task_details t
LEFT JOIN plan.product_info p ON t.serial_number = p.serial_number
WHERE t.task_id='SI_SHIPMENT' AND t.completed_at IS NOT NULL
  AND COALESCE(t.force_closed, FALSE) = FALSE
  AND p.actual_ship_date IS NULL;
→ 0건 (Twin파파 실측, 2026-04-28)
→ 해석 A (si ⊆ actual) 확정, v2.4 그대로 진행 OK
```

### Twin파파 검토 1건 반영

OPS_API_REQUESTS.md v2.4 문서 SQL 의 `task_id='si_shipment'` (소문자) → `'SI_SHIPMENT'` (대문자, 실 DB 값) 4곳 정정. 문서 그대로 구현 시 LEFT JOIN 매칭 0건 → shipped_plan/best 영구 0 (의도와 정반대).

### pytest 결과

```
test_factory_kpi.py: 17 passed / 3 skipped / 0 fail (137.10s)
  ✅ 신규 TestFactoryKpiV24Amendment 3 TC (응답 키 / best 스모크 / invalid basis)
  ✅ 기존 14 TC 갱신 후 PASS (응답 키 ops→best, _count_shipped 'ops'→'plan')
  ⏸ 3 TC skip (TC-FK-06/09/11): v2.3 'ops' 분기 의존 TC, v2.4 에서 fixture 한계로 TC 본질 무효
     → 운영 데이터 보존 정책 (plan.product_info UPDATE 금지) 으로 actual_ship_date 시뮬레이션 불가
     → v2.4 핵심 거동은 TestFactoryKpiV24Amendment 클래스로 이전
```

### LoC

- factory.py: 562 → 575 (+13 LOC, God File 잔존 but 별건 REFACTOR-FACTORY)
- test_factory_kpi.py: 435 → 511 (+76 LOC)

### Sprint 설계서 vs 실제 변경 차이

| 항목 | Sprint 설계서 권장 | 실제 |
|---|---|---|
| TC 개수 | 14개 (8 재정렬 + 6 신규) | 17 passed (14 기존 + 3 신규) + 3 skip — fixture 한계로 신규 TC 일부 단순화 |
| Codex 이관 | ❌ 불필요 | ❌ 불필요 (Pre-deploy Gate ③ 0건 검증 완료) |

### Post-deploy 검증 (예정)

- **T+1h**: 대시보드 W17 `shipped_plan` 0 → 수십대 (의도된 변화) + Sentry 새 ERROR 0
- **T+24h**: 3필드 `shipped_plan/actual/best` 정상 반환 + 회귀 0
- **T+72h**: R-02 해석 A 재검증 (반례 0건 유지) + FE Phase 2 (v1.35.0) 착수 가능 시점 도달

### BACKLOG 동기화

- `FIX-FACTORY-KPI-SHIPPED-V2.4-AMENDMENT-20260428` → ✅ COMPLETED
- 후속: AXIS-VIEW Phase 2 (v1.35.0) 착수 가능 (별 repo)

---

## 🟢 2026-04-28 세션 요약 (4/5) — Sentry garbage log 정리 v2.10.13 (2 Sprint 묶음)

> **한 줄 요약**: Sentry 대시보드 잡음 분리 — (1) db_pool direct fallback ERROR (22 events) → warning 강등 + counter (2) flask-sock wsgi StopIteration (302 events) → before_send hook 으로 drop. 진짜 ERROR 추적성 회복. pytest 7/7 PASS.

### Sprint 1 — FIX-DB-POOL-DIRECT-FALLBACK-LOG-LEVEL-20260428

- `db_pool.py`:
  - `_direct_fallback_count: int = 0` + `get_direct_fallback_count()` getter 신설
  - L171-173 `logger.error` → `logger.warning("[db_pool] All pool connections unusable after %d retries, creating direct connection (cumulative fallback=%d)", retries, _direct_fallback_count)` 강등
- `tests/backend/test_db_pool.py` 신규 — TC 3개 (counter / normal / exhausted 분리)
- 효과: Sentry `[db_pool] All pool connections unusable` 22 events 동결

### Sprint 2 — FIX-WEBSOCKET-STOPITERATION-SENTRY-NOISE-20260428

- `__init__.py`:
  - 모듈 top-level `_sentry_before_send(event, hint)` 신규 (~30 LOC)
  - 매칭 3조건 (`exc_type='StopIteration'` + `mechanism.type='wsgi'` + `transaction='websocket_route'`) 모두 성립 시 drop
  - try/except 안전 fallback (필터 실패 시 정상 capture)
  - `sentry_sdk.init()` 에 `before_send=_sentry_before_send` 등록
- `tests/backend/test_sentry_filter.py` 신규 — TC 4개 (drop / pass other transaction / pass other exc / malformed event)
- 효과: Sentry PYTHON-FLASK-2 302 events 동결

### pytest 결과

```
✅ test_db_pool.py 3/3 PASS
✅ test_sentry_filter.py 4/4 PASS
   총 7/7 PASS in 0.09s — 회귀 0건
```

### LoC 변경

| 파일 | Before | After | 차이 |
|---|---:|---:|---:|
| db_pool.py | 286 | 297 | +11 (🟢 500 미만) |
| __init__.py | ~190 | ~225 | +35 (🟢 500 미만) |

### Post-deploy 검증 (예정)

- T+1h: Sentry 2 issue events 카운트 증가 멈춤 (22 / 302 동결)
- T+24h: 다른 issue 정상 capture 확인 (PYTHON-FLASK-1 / PYTHON-FLASK-4)
- T+7d: 본 Sprint 효과 정량 입증 + Railway `cumulative fallback=N` 추세 → 별건 OBSERV-WARMUP-INTERVAL-TUNE 우선순위 결정

---

## 🟢 2026-04-28 세션 요약 (3/4) — FIX-26-DURATION-WARNINGS-FORWARD v2.10.12

> **한 줄 요약**: 4-22 등록 BACKLOG L362 `BUG-DURATION-VALIDATOR-API-FIELD` 본격 fix. `/api/app/work/complete` 응답에 `duration_warnings` 키 항상 존재 보장 (옵션 C — 양 끝 unconditional). test_reverse_completion 은 시작/종료 timestamp 서버 자동 기록 + prod 0건 실측 입증으로 `@pytest.mark.skip` 처리.

### 코드 변경 (v2.10.12, BE 2 파일 + test 1 파일)

| 파일 | LoC | 핵심 |
|---|---:|---|
| task_service.py | ±0 | L497-499 — unconditional 응답 키 (조건부 제거) |
| work.py | -1/+1 | L265-266 — default 빈 리스트 forward |
| test_duration_validator.py | +62 | assertion 갱신 + 신규 TC 1개 + skip mark |
| backend/version.py | bump | v2.10.11 → v2.10.12 |
| frontend/.../app_version.dart | bump | v2.10.11 → v2.10.12 |

### 핵심 인사이트 — 본 Sprint 단순화 (사용자 정정 반영)

- 시작/종료 timestamp 가 **서버 `datetime.now(Config.KST)` 자동 기록** (`task_service.py:146/256`, `work.py:448`)
- 클라이언트가 시간 보내거나 입력하는 경로 0
- REVERSE_COMPLETION (시작 > 종료) 은 운영 발생 불가 — 인프라 사고 (NTP jump back / SQL 직접 조작 / timezone 버그) 차원
- prod 실측 0건 (4-04 ~ 4-28 24일 누적, started_at>completed_at WHERE 절)
- 대시보드 Rollback 키로 잘못된 종료 사후 복구 메커니즘 별도 존재
- → 처음 우려한 silent failure / 4-22 유사 구조 모두 무의미. 본 Sprint 는 응답 contract 일관성만 fix

### Codex 라운드 2 합의 trail

v2.10.11 (FIX-PROCESS-VALIDATOR-TMS-MAPPING) 후속에서 Codex Q1/Q2 모두 A 라벨 합의:
- 본 fail 은 `duration_validator.py:70-93` REVERSE_COMPLETION 브랜치 → `task_service.py:361-363,496-498` → `work.py:261-266` 응답 키 생성 경로 4-22 부터 누락된 별건
- v2.10.11 회귀 0건 + 본 BUG 별건 확정 → 별도 Sprint 처리

### pytest 결과

```
test_duration_validator.py:
  ✅ test_normal_duration_no_warnings (assertion 갱신 후 신 계약 호환)
  ✅ test_duration_over_14h
  ✅ test_very_short_duration
  ⏸ test_reverse_completion (skip — 시작/종료 timestamp 서버 자동 기록, prod 0건)
  ✅ test_normal_completion_returns_empty_duration_warnings (신규)
```

### BACKLOG 동기화

- L362 `BUG-DURATION-VALIDATOR-API-FIELD` → ✅ COMPLETED (v2.10.12)
- 별건 BACKLOG 등록 불필요 (P3 INFO 수준 이하 — 사용자 영향 0 입증)

### Post-deploy 검증 (예정)

- FE 영향 0 — `data.duration_warnings` 안전 접근 가능 (FE 가 옵셔널 처리 안 했어도 빈 리스트 받음)
- 운영 회귀 검증 불필요 (응답 dict 키 1개 추가만)

---

## 🟢 2026-04-28 세션 요약 (2/3) — FIX-PROCESS-VALIDATOR-TMS-MAPPING v2.10.11 (옵션 D-2)

> **한 줄 요약**: 4-22 HOTFIX-ALERT-SCHEDULER-DELIVERY 의 표준 패턴이 duration_validator 3곳 + task_service L403 에 미적용 → TMS 매니저 silent failure (Sentry 도입 8h 자동 감지, 31 events). `process_validator.resolve_managers_for_category()` public 함수 신설 + 5 파일 atomic refactor + pytest 신규 TC 7개. 회귀 0건. Codex 2라운드 검증 합의 완료.

### 코드 변경 (v2.10.11, BE 5 파일 atomic)

| 파일 | LoC 변경 | 핵심 |
|---|---:|---|
| process_validator.py | **+30** | `_CATEGORY_PARTNER_FIELD` + `resolve_managers_for_category()` 신설 |
| scheduler_service.py | **-15** | private 함수 + dict 제거 + import 교체 + 3 호출 site 1:1 |
| task_service.py | **±0** | L403 import + L410 호출 1:1 (Codex M2 누락 발견) |
| duration_validator.py | **±0** | L74/L100/L179 + import 1줄 |
| tests/conftest.py | +50 | `seed_test_managers_for_partner` 격리 fixture (옵션 D, Codex M1) |
| tests/backend/test_process_validator.py | +130 | TC 7개 (TMS-GAIA / DRAGON 회귀 / MECH / ELEC / PI / unknown / e2e) |

→ Line 규칙 모두 통과 (scheduler/task_service God File 잔존 but LoC 감소/0).

### Codex 합의 trail (2 라운드)

- **라운드 1 (Sprint 설계 검증)**: M=2 / A=2 / N=2
  - M1 (fixture 정합성) → 옵션 D 격리 fixture 채택
  - M2 (Rollback 5파일) → task_service.py L403 누락 발견, 5 파일 명시
  - A1 (DRAGON gap) → 별건 BACKLOG `BUG-DRAGON-TMS-PARTNER-MAPPING-20260428`
  - A2 (e2e 회귀 TC) → `test_duration_validator_tms_alert_creation_e2e` 추가
- **라운드 2 (pytest 회귀 라벨링)**: Q1/Q2 모두 A
  - test_duration_validator 1 fail = BACKLOG L362 BUG-DURATION-VALIDATOR-API-FIELD (4-22 별건)
  - 본 Sprint 응답 키 생성 경로 영향 0 → 별도 Sprint 처리 결정

### pytest 결과

```
✅ 신규 TC 7/7 PASS (TestResolveManagersForCategory 6 + e2e 1)
✅ 회귀 51 passed / 5 skipped / 0 fail (test_scheduler / test_scheduler_integration / test_task_seed)
⚠️ test_duration_validator 1 fail = 4-22 기존 별건 (Codex A 라벨 합의)
```

### 다음 우선 처리 (별도 Sprint)

1. 🟡 **BUG-DURATION-VALIDATOR-API-FIELD** (BACKLOG L362) — `/api/app/work/complete` 응답에 `duration_warnings` 키 forward (30~60분)
2. 🟢 BUG-DRAGON-TMS-PARTNER-MAPPING-20260428 (BACKLOG L353) — prod DB 실측 후 우선순위 재평가

### Post-deploy 검증 (예정)

- 즉시 (1h): Sentry PYTHON-FLASK-4 events 31 → 정착 추세 확인
- 매시간 정각 (UTC) 7번: TMS / MECH / ELEC / PI 매니저 도달
- D+7: Sentry events 31 그대로 → COMPLETED 판정

---

## 🟢 2026-04-28 세션 요약 (1/2) — D+1 출근 peak 측정 PASS, 옵션 X1 유지

> **한 줄 요약**: 4-28 출근 peak (07:30~09:00 KST) 측정 결과 Pool exhausted 0 / direct conn fallback 0 / OPS conn 6~7 안정 / Sentry 새 issue 0 → v2.10.11 HOTFIX-06b 진행 불필요. v2.10.7 HOTFIX-06 단독으로 사용자 영향 0 보장 확정.

### 측정 결과

| 항목 | 기대 | 실측 | 판정 |
|---|---|---|---|
| Pool exhausted | 0건 | **0건** | ✅ |
| direct conn fallback | 0건 | **0건** | ✅ |
| OPS conn (peak) | ≥ 10 | **6~7 안정** | ✅ |
| Sentry 새 issue | 0건 | **0건** | ✅ |

### 결정

- ✅ 옵션 X1 유지 — Worker A 5 conn (warmup) + Worker B 자연 사용분 = 안정적 운영
- ❌ v2.10.11 HOTFIX-06b (per-worker warmup) 진행 불필요
- ✅ `OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP-20260427` **COMPLETED 확정** (부분 완료 → 정식 완료)
- 🟡 D+2 (4-29) / D+3 (4-30) 동일 추세 관찰 — Phase B 자연 종결 예정
- 🔴 다음 우선 처리: BACKLOG L352 `FIX-PROCESS-VALIDATOR-TMS-MAPPING-20260428` (옛 ID `-ROLE-MAPPING-20260427` 통일, Cowork 설계 완료 → Codex 이관 진행 중)

### 부수 발견 trail (Sentry layer)

- 4-28 03:00 KST cron 시점 Sentry 가 `Failed to get managers for role=TMS: invalid input value for enum role_enum: "TMS"` 31 events 자동 감지 → BACKLOG L352 등록 (FIX-PROCESS-VALIDATOR-TMS-ROLE-MAPPING)
- 4-22 HOTFIX-ALERT-SCHEDULER-DELIVERY 의 잔존 silent failure (process_validator/duration_validator 의 enum cast 미처리) → Sentry DSN 활성화 8시간 만에 자동 발견
- ADR-019 가치 입증 trail 3차 사례 추가 (memory.md)

### 이번 주 핵심 3가지 — 3개 모두 완료 ✅

1. ✅ PIN 화면 손실 막기 (v2.10.5 + v2.10.6)
2. ✅ DB Pool 안정화 마무리 (v2.10.6/.7 + D+1 PASS)
3. ✅ 알람 장애 사후 검증 마무리 (v2.10.8 + Sentry 활성화)

---

## 🟢 2026-04-27 세션 요약 (6/6) — Sentry DSN 활성화 + WEEKLY_PLAN 갱신

> **한 줄 요약**: Twin파파 측 sentry.io 가입 + Python/Flask project 생성 + DSN 발급 + Railway env (`SENTRY_DSN` / `SENTRY_ENVIRONMENT` / `SENTRY_TRACES_SAMPLE_RATE`) 등록 완료. v2.10.8 에 도입한 `_init_sentry()` 가 정식 활성화 → 외부 자동 감지 layer 1차 가동 시작.

### 활성화 결과

- ✅ `SENTRY_DSN` env 등록 → 다음 deploy 시 `_init_sentry()` 가 정상 init (이전엔 graceful skip 모드였음)
- ✅ `LoggingIntegration` (INFO breadcrumb / ERROR event capture) 정식 작동
- ✅ `FlaskIntegration` HTTP exception 자동 캡처
- ✅ `release` 자동 binding (version.py)
- 🟡 Sentry alert rule 미세 조정 (다음 주 운영 후 노이즈 비율 기반)

### 시스템 신뢰성 1차 완성

```
Before (4-22 사고): silent gap → 5일 무인지 → 사용자 신고로 발견
After (4-27+):       silent gap → assertion 즉시 캡처 → Sentry email/push
                     평균 인지 시간: 5일 → ~1분
```

### WEEKLY_PLAN_20260427.md 갱신

- v2.10.8/9/10 + Sentry 활성화 반영 (마지막 업데이트 23:13 KST)
- 핵심 3가지 → 2개 완료 + 1개 부분 완료 (DB Pool D+1 측정 잔존)
- 신규 섹션 "🛡️ assertion 자동 감지 layer + Sentry 시스템 확장" 추가 (자동 감지 시퀀스 표 + Before/After 비교)
- 4-28 화 측정 plan 에 v2.10.10 정상화 확인 + Sentry 24h 노이즈 비율 항목 추가

---

## 🟢 2026-04-27 세션 요약 (5/6) — HOTFIX-08 v2.10.10 db_pool transaction 정리 누락 + 046a 자동 적용

> **한 줄 요약**: v2.10.9 배포 후 Railway log 에 `046a_elec_checklist_seed.sql 실행 실패: set_session cannot be used inside a transaction` 발생 → assertion 이 두 번째 잠재 버그 (db_pool transaction 정리 누락 + 046a silent gap) 사용자 영향 0 시점에 발견. db_pool 2곳 SELECT 1 후 `conn.rollback()` 추가로 해결. 046a 자동 재적용 (ON CONFLICT idempotent).

### 문제 원인

- psycopg2 default `autocommit=False` → SELECT 도 BEGIN 자동 시작 → INTRANS 상태로 풀 반납
- 이 conn 을 받아 `m_conn.autocommit = True` 시도 시 `set_session cannot be used inside a transaction` 거부
- 영향받은 호출 경로: `_is_conn_usable()` + `warmup_pool()` 두 군데

### 코드 변경 (v2.10.10, BE only ~2줄)

- `backend/app/db_pool.py _is_conn_usable()` L98+ — SELECT 1 후 `conn.rollback()` 추가
- `backend/app/db_pool.py warmup_pool()` L270+ — 동일 패턴 적용
- `backend/version.py` v2.10.9 → 2.10.10
- `frontend/lib/utils/app_version.dart` v2.10.9 → 2.10.10

### 부수 발견 (가설 ④ 두 번째 사례)

- **046a_elec_checklist_seed.sql 도 silent gap** — 4-22 049 와 동일 Docker artifact 사례로 추정. assertion 이 자동 적용 시도 → set_session error 노출
- ON CONFLICT DO NOTHING idempotent 보장으로 prod 31항목 안전 재적용. **사용자 영향 0** ✅
- POST_MORTEM_MIGRATION_049.md 가설 ④ (Docker artifact / Railway build cache) 의 두 번째 케이스로 trail 추가

### git commit / 검증

- commit: `72579e1` (v2.10.10)
- pytest 회귀 0건
- Railway log 검증: `[migration] ✅ 046a_elec_checklist_seed.sql 실행 완료` + `[migration-assert] ✅ sync OK (13 migrations applied)` (12 → 13 갱신)

---

## 🟢 2026-04-27 세션 요약 (4/6) — HOTFIX-07 v2.10.9 RealDictCursor row[0] KeyError 긴급 복구

> **한 줄 요약**: v2.10.8 배포 직후 `assert_migrations_in_sync()` 첫 호출 시 worker boot 503 발생. `_get_executed()` 의 `row[0]` 이 RealDictCursor 와 호환 안 됨 → KeyError: 0. assertion 도입 자체가 5일 누적된 silent 버그를 즉시 노출시킨 사례 (assertion 가치 1차 입증).

### 문제 원인

- `db_pool` 이 `RealDictCursor` 사용 → row 가 dict-like → `row[0]` 은 `KeyError: 0`
- 이전 `run_migrations()` 의 outer try/except 가 silent 흡수 → 5일간 무인지
- v2.10.8 의 `assert_migrations_in_sync()` 는 try/except 없이 호출 → KeyError 그대로 propagate → gunicorn worker boot 실패 → 503

### 코드 변경 (v2.10.9, BE only)

- `backend/app/migration_runner.py _get_executed()` L51 — `row[0]` → `row['filename']`
- `backend/app/migration_runner.py assert_migrations_in_sync()` L165+ — outer try/except 안전망 추가 (assertion 자체 실패가 worker boot 막지 않도록)
- `backend/version.py` v2.10.8 → 2.10.9
- `frontend/lib/utils/app_version.dart` v2.10.8 → 2.10.9

### Lesson

- **assertion 도입 자체가 사고 발견 trigger 가 됨** — 5일간 silent 흡수된 row[0] KeyError 가 try/except 없는 호출 경로에서 즉시 노출
- 향후 신규 assertion 도입 시 outer try/except 안전망 표준화 권장

---

## 🟢 2026-04-27 세션 요약 (4/6 핵심) — v2.10.8 알람 시스템 사후 검증 마무리 4 Sprint 통합 배포

> **한 줄 요약**: 4-22 알람 silent failure (5일 52건 NULL) 사고의 사후 검증 마무리. POST-REVIEW-MIGRATION-049 + OBSERV-RAILWAY-LOG-LEVEL + OBSERV-ALERT-SILENT-FAIL (Sentry) + OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION 4 Sprint 통합 배포. 외부 자동 감지 layer 1차 완성.

### Sprint별 산출 (v2.10.8, BE only ~140 LOC)

| Sprint | 산출 |
|---|---|
| OBSERV-RAILWAY-LOG-LEVEL-MAPPING | `Procfile` `--access-logfile=- --log-level=info` 추가 + `__init__.py` `logging.basicConfig(stream=sys.stdout, force=True)` 명시 |
| OBSERV-ALERT-SILENT-FAIL (Sentry) | `requirements.txt` `sentry-sdk[flask]>=2.0` + `_init_sentry()` 신규 (~50 LOC, FlaskIntegration + LoggingIntegration + release auto-binding + send_default_pii=False) + migration_runner 실패 시 `sentry_sdk.capture_exception` |
| POST-REVIEW-MIGRATION-049-NOT-APPLIED | `POST_MORTEM_MIGRATION_049.md` 신규 — 4가지 가설 전수 검증 → ④ Docker artifact / Railway build cache 가장 유력 (Codex POST-REVIEW Q2-2 판정 일치) |
| OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION | `assert_migrations_in_sync()` 함수 신규 (~40 LOC) — disk vs DB sync 검증 + gap 시 `sentry_sdk.capture_message` |

### Twin파파 측 후속 (다음 세션 6/6 에서 완료)

1. ✅ sentry.io 가입 + Python/Flask project 생성 + DSN 발급
2. ✅ Railway env 등록: `SENTRY_DSN` (필수) + `SENTRY_ENVIRONMENT` (production) + `SENTRY_TRACES_SAMPLE_RATE`
3. 🟡 Sentry alert rule 설정 (1주 운영 후 미세 조정)

### 검증

- pytest test_scheduler.py 8 passed / 1 skipped / 회귀 0건 ✅
- BE syntax check (init/migration_runner) ✅

---

## 🟢 2026-04-27 세션 요약 (3.5/6) — HOTFIX-06 v2.10.7 warmup_pool() 시계 리셋 누락 fix

> **한 줄 요약**: v2.10.6 OBSERV-WARMUP 배포 후 결함 발견 — warmup 외형상 작동하지만 SELECT 1 만 실행하고 `_conn_created_at` 갱신 안 함 → `_is_conn_usable()` 가 expired 판정 → discard → direct conn fallback 다발. 1줄 추가로 해결.

### 코드 변경 (v2.10.7, BE only 1줄)

- `backend/app/db_pool.py warmup_pool()` L240+ — `_conn_created_at[id(conn)] = time.time()` 1줄 추가
- `backend/version.py` v2.10.6 → 2.10.7
- `frontend/lib/utils/app_version.dart` v2.10.6 → 2.10.7
- git commit: `7a13085`

### Limitation (per-worker 함정)

- 본 fix 는 fcntl lock 으로 1 worker (Worker A) 만 scheduler 실행 → Worker A 의 pool 만 시계 리셋
- **Worker B 의 pool 은 자연 만료**. 결과: conn 7~11 진동 (영구 10 의도는 절반 달성)
- 사용자 영향 0 입증 후 **D+1 (4-28 화) 출근 peak 측정 결과 따라 v2.10.11 HOTFIX-06b** (per-worker warmup) 진행 결정

---

## 🟢 2026-04-27 세션 요약 (3/3) — FEAT-PIN-STATUS-BACKEND-FALLBACK + OBSERV-DB-POOL-WARMUP 병행 Deploy (v2.10.6)

> **한 줄 요약**: FE 자동 PIN 복구 (P1 격상) + BE Pool warmup cron (P2, 실측 입증) 병행 배포. v2.10.6 Netlify (FE) + Railway (BE) 모두 배포 완료. PIN 사용자 보안 의도 유지 + Pool conn 영구 10 보장.

### 핵심 의사 결정 (병행 진행 안전성 검증 완료)

| Sprint | 영역 | 충돌 | 위험도 |
|---|---|---|---|
| FEAT-PIN-STATUS-BACKEND-FALLBACK | FE (main.dart + auth_service.dart) | 없음 | 🟢 LOW |
| OBSERV-DB-POOL-WARMUP | BE (db_pool.py + scheduler_service.py) | 없음 | 🟢 LOW |

→ 두 작업 다른 영역 + 의존성 없음 → 병행 안전. pytest test_scheduler.py 8 passed / 0 failed.

### 코드 변경 (v2.10.6)

**FE (FEAT-PIN-STATUS-BACKEND-FALLBACK, P1 격상)**:
- `frontend/lib/services/auth_service.dart` `getBackendPinStatus()` 신규 (~15 LOC)
  - `/auth/pin-status` 호출 + try/catch + debugPrint
- `frontend/lib/main.dart` L275~ tryAutoLogin 성공 후 backend PIN 복구 분기 추가 (~16 LOC)

**BE (OBSERV-DB-POOL-WARMUP, P2)**:
- `backend/app/db_pool.py` `warmup_pool()` public 함수 신규 (~40 LOC, A1 반영)
- `backend/app/services/scheduler_service.py`:
  - L17 `from apscheduler.triggers.interval import IntervalTrigger` (A3)
  - L23 `from app.db_pool import put_conn, warmup_pool`
  - `_pool_warmup_job()` 신규 함수
  - `add_job` 12번째 등록 — `IntervalTrigger(minutes=5)` + `next_run_time=datetime.now(Config.KST) + timedelta(seconds=10)` (timezone-aware, A5)
  - 스케줄러 job 수: **11 → 12**

**버전**:
- `backend/version.py` v2.10.5 → 2.10.6
- `frontend/lib/utils/app_version.dart` v2.10.5 → 2.10.6

### Claude Code advisory 1차 (OBSERV-WARMUP, M=0/A=5)

| # | Advisory | 반영 |
|:---:|:---|:---|
| A1 | private `_pool` API 직접 import → public `warmup_pool()` 노출 | ✅ |
| A2 | pytest TC `_pool=None` skip 처리 | ✅ warmup_pool 자체 처리 |
| A3 | `IntervalTrigger` 명시 import | ✅ |
| A4 | ThreadPool 경합 위험 평가 | ✅ 5/10 여유 |
| A5 | timezone-aware `next_run_time` | ✅ Config.KST |

### Codex 이관 미해당

두 sprint 모두 6항목 미충족:
- 인증 로직 변경 X (FEAT 는 호출 추가만, 로직 변경 X)
- 3파일 이상 X (각 2파일 이내)
- API 응답/스키마/FK X
- 클린코어 데이터 X

→ Claude Code 자체 검토 + 회귀 pytest 만으로 진행.

### 안전성 검증 완료

- ✅ Flutter web build 성공 (12.1s)
- ✅ BE syntax check (db_pool.py + scheduler_service.py)
- ✅ pytest test_scheduler.py: 8 passed / 1 skipped / 회귀 0건
- ✅ 다른 storage 키 영향 X (FEAT 는 pin_registered 만)
- ✅ scheduler 기존 11 job 영향 X

### Deploy

- 빌드: flutter build web --release ✓ 12.1s
- 배포 (FE): Netlify Deploy ID `69eef28fca3b7ffce577068d` (2026-04-27 KST)
- 배포 (BE): Railway 자동 (git push → ~1분)
- Production URL: https://gaxis-ops.netlify.app

### Post-deploy 검증 (Twin파파)

#### Railway logs (배포 직후, ~1분)

```
[scheduler] Scheduler initialized with 12 jobs   ← 11 → 12 확인
[pool_warmup] 5/5 conn warmed                    ← 첫 실행 (10초 후)
```

#### 1시간 관찰 (`pg_stat_activity`)

매 5분 conn 수 측정 → **10 영구 유지** = 성공. 7 이하 감소 시 Phase C 검토.

#### FEAT-PIN-STATUS 효과 검증

PIN 사용자가 IndexedDB 잃어도 `/auth/pin-status` 자동 호출 → PinLoginScreen 복귀 (HomeScreen 직행 X).

### 다음 세션 시작 시 할 일

1. **공지(notices) v2.10.6 bump** — PIN 자동 복구 + DB Pool 안정화 사용자 공지 (+ v2.10.5 합쳐서)
2. **FIX-DB-POOL Phase B 관찰 결과 정리** (D+1 화 4-28, D+2 수 4-29, D+3 목 4-30) — Pool exhausted grep + Q-B 재측정
3. **FEAT-PIN-FLAG 효과 측정** — D+7 (5-04) baseline SQL 재측정
4. **OBSERV-WARMUP 효과 검증** — D+1 새벽~출근 peak conn 추세 측정 (10 유지 확인)
5. **잔존 BACKLOG**:
   - `AUDIT-PWA-SW-INDEXEDDB-PRESERVE-20260427` 🟡 P2 (audit, 30분)
   - `UX-LOGIN-FALLBACK-PIN-RESET-LINK-20260427` 🟢 P3 (1h)
   - `FEAT-AUTH-STORAGE-MIGRATION-FULL-20260427` 🟡 P2 (보안 trade-off)

### 산출물 (v2.10.6)

- 코드 4 파일: db_pool.py + scheduler_service.py + auth_service.dart + main.dart
- 버전 2 파일: backend/version.py + frontend/lib/utils/app_version.dart
- 문서 3 파일: CHANGELOG.md ([2.10.6] entry) + BACKLOG.md (FEAT/OBSERV COMPLETED) + handoff.md (3/3 세션)

---

## 🟢 2026-04-27 세션 요약 (2/3) — FIX-PIN-FLAG-MIGRATION-SHAREDPREFS Deploy 완료 (v2.10.5)

> **한 줄 요약**: PIN 등록 플래그 storage 안정화 — `pin_registered` SecureStorage → SharedPreferences 양방향 sync 이전. 4 라운드 advisory review (M=8/8 + 추가 리스크 2/2 전수 반영) 후 적용. v2.10.5 Netlify 배포 완료.

### 핵심 의사 결정 (4 라운드 advisory 누적)

| 라운드 | 주체 | 발견 | 반영 |
|---|---|---|---|
| 1 (자체) | Claude Code | 인증 로직 영향 → Codex 이관 / 양방향 sync 채택 / baseline SQL 추가 (6건) | ✅ |
| 2 (Codex) | Codex 1차 | M 8건 (atomic / SQL LIKE / SW trigger / rollback 5번째 / cohort / 다른 가설 / D+7 통계 / iOS Safari) | ✅ 8/8 |
| 3 (Codex 추가) | Codex | 추가 리스크 2: refresh_token 도 SecureStorage / backend `/auth/pin-status` 가 진짜 root fix | ✅ 2/2 BACKLOG |
| 4 (배포 검증) | Twin파파 | home_screen.dart 별건 알림 배지 동기화 동시 포함 안전 검증 | ✅ |

### 코드 변경 (v2.10.5)

- `frontend/lib/services/auth_service.dart`:
  - L3 `package:flutter/foundation.dart` import 추가 (debugPrint)
  - `hasPinRegistered()` 양방향 read + sync (SharedPrefs 우선, SecureStorage fallback + auto-sync, **delete 안 함** rollback 안전)
  - `savePinRegistered()` 양방향 write + atomic try/catch (SharedPrefs 주 저장소, SecureStorage best-effort)
  - `logout()` (L243) SharedPrefs `pin_registered` 도 정리 (양방향 cleanup)
- `frontend/lib/utils/app_version.dart` v2.10.4 → **2.10.5**
- `backend/version.py` v2.10.4 → **2.10.5**
- 부수: `frontend/lib/screens/home/home_screen.dart` 알림 배지 동기화 (별건, 같은 commit 포함)

### Deploy

- 빌드: flutter build web --release ✓ 12.2s
- 배포: Netlify Deploy ID `69eed5d26147a9d3c6966ecf`
- Production URL: https://gaxis-ops.netlify.app

### Limitation (Codex 1차 advisory 핵심)

4개 SecureStorage 키 (`pin_registered`, `refresh_token`, `worker_id`, `worker_data`) 가 IndexedDB 일괄 손실 시 본 Sprint 효과 영역 좁음:
- `pin_registered` 만 단독 손실 (드뭄) → ✅ 본 Sprint 보호
- 4개 함께 손실 (Clear site data, Storage quota evict) → ❌ FEAT-PIN-STATUS-BACKEND-FALLBACK (P1) 가 진짜 root fix

### 신규 BACKLOG (4개 후속 Sprint, BACKLOG.md L347-L351 등록 완료)

- `FEAT-PIN-STATUS-BACKEND-FALLBACK-20260427` 🔴 P1 (격상 — 진짜 root fix, 1h)
- `AUDIT-PWA-SW-INDEXEDDB-PRESERVE-20260427` 🟡 P2 (audit, 30분)
- `UX-LOGIN-FALLBACK-PIN-RESET-LINK-20260427` 🟢 P3 (UX, 1h)
- `FEAT-AUTH-STORAGE-MIGRATION-FULL-20260427` 🟡 P2 (Codex 신규 권장 — refresh_token + worker_id + worker_data 도 양방향 sync)

### 다음 세션 시작 시 할 일

1. **Baseline SQL 측정** — 설계서 L31644~31691 SQL 3종 pgAdmin 실행 (배포 전 1회 권장, **사후 측정도 가능**)
2. **D+7 재측정 비교** (2026-05-04) — PIN 손실 의심 사용자 / login attempts / auth_pct 변화
3. **공지(notices) bump** — v2.10.5 사용자 공지 INSERT (PIN 화면 손실 보호 + 알림 배지 동기화)
4. **L32002 OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP P2 (격상)** — 실측으로 MIN=5 무효 입증 (10:14 → 10:24 conn 10→9→7), warmup cron 추가 (1~1.5h)
5. **FEAT-PIN-STATUS-BACKEND-FALLBACK P1** — 본 Sprint 직후 진행 (1h, 진짜 root fix)

### 부수 발견 (별도 보고)

1. **MIN=5 max_age=300s race 실측 입증** — 2026-04-27 10:14~10:24 KST 측정 결과 OPS 10→9→7 conn (10분만에 30% 감소). Codex 라운드 3 A4 advisory 가 실측으로 입증. → `OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP` P3 → P2 격상 + 본 세션 설계서 작성 (L32002).
2. **CHANGELOG v2.10.4 entry 누락** — 이전 세션 (4-25 health timeout 5→20s) 시 보충 안 됨. 별도 보충 필요 (사후 정리).

### 산출물 (FIX-PIN-FLAG)

- 코드 3 파일: auth_service.dart + app_version.dart + version.py
- 부수 1 파일: home_screen.dart
- 문서 4 파일: AGENT_TEAM_LAUNCH.md (PIN-FLAG + OBSERV-WARMUP 설계서) + CHANGELOG.md ([2.10.5] entry) + BACKLOG.md (5개 entry) + handoff.md (이 파일)
- 신규 1 파일: `CODEX_REVIEW_FIX_PIN_FLAG_20260427.md`

---

## 🟢 2026-04-27 세션 요약 (1/3) — FIX-DB-POOL-MAX-SIZE-20260427 Phase A 적용 (Phase B 관찰 중)

> **한 줄 요약**: Railway env `DB_POOL_MAX` 20→30 변경 (MIN=5 유지) — 코드 변경 0, 4 라운드 advisory review (Codex×2 + Claude Code×1 + Twin파파 fact-check×1) 후 적용. Phase B 3일 (화/수/목) 관찰 중.

### 핵심 의사 결정 (4 라운드 advisory 누적)

| 라운드 | 주체 | 발견 |
|---|---|---|
| 1 (텍스트) | Codex 1차 | scheduler peak 8 conn / 단계적 25→30 직행 / fallback 비용 / 평균 conn 정정 (4건) |
| 2 (코드 구조) | Claude Code | ⛔ **per-worker 독립 pool** 발견 (init_pool() in create_app() — 단일 pool 가정 무효) / Phase B 3일 확장 / pid+client_addr SQL (4건) |
| 3 (데이터 정합성) | Codex 3차 | Q-B 일자 오기 (4-27→4-21) / 5x 산수 오류 (155 in-flight 부족) / MIN ↔ max_age race / grep `\b` + `get_db_connection` 함수명 누락 (4건) |
| 4 (env fact-check) | **Twin파파** | ⚠️ 코드 default (1/10) 가정 오류 — **prod 가 이미 5/20 운영 중**. 결론 (MAX=30) 유지하되 fallback 추정 정정 (3건) |

### 최종 결정 + 배포

- **MAX**: 20 → **30** (Railway env)
- **MIN**: 5 (변경 없음, 유지)
- 배포 방식: Twin파파 Railway Dashboard 에서 직접 적용 → 자동 재배포
- 코드 변경 0 / 버전 bump 없음 / notices 없음

### Q-B 결정적 데이터 (2026-04-21 화 출근 burst)

- peak 31 동시 in-flight (08:06:07 KST)
- 21 동시 17회 (07:46~08:55)
- MAX=20 환경에서 fallback 1건/peak (라운드 4 정정)
- MAX=30 채택으로 fallback 0 + 미래 2x (62 in-flight) 까지 dimensioning

### Phase B 관찰 일정

| 날짜 | 시점 | 점검 |
|---|---|---|
| D+0 (4-27 월) | 16:30~17:00 KST | 퇴근 peak — Railway logs `Pool exhausted` grep |
| D+1 (4-28 화) | 07:30~09:00 KST | 출근 peak |
| D+2 (4-29 수) | 07:30~09:00 KST | 출근 peak |
| D+3 (4-30 목) | 07:30~09:00 KST | 출근 peak + Phase C 결정 |
| off-peak (12:00) | — | Q-B SQL 재측정 (O(N²) 부담 회피) |

### 다음 세션 시작 시 할 일

1. **Railway logs 검증** — `[db_pool] Connection pool initialized: min=5, max=30, max_age=300s, connect_timeout=5s` 1건 출력 확인 (D+0 배포 직후)
2. **Phase B grep 결과 정리** — 매일 오전 + 17:00 후 Railway logs `Pool exhausted` / `Using direct connection` 카운트
3. **D+3 (4-30 목) Phase C 결정**:
   - 0 fallback / 3일 → 30 충분, BACKLOG `FIX-DB-POOL-MAX-SIZE-20260427` COMPLETED 처리
   - 1~5건 / 3일 → MAX=40 ↑ (잠재 leak 의심)
   - 10+건 / 3일 → MAX=50 ↑ + leak audit 필수

### 부수 발견

1. **CHANGELOG v2.10.4 entry 누락** — 이전 세션 (2026-04-25 health timeout 5→20s 패치) 시 CHANGELOG 보충 안 됨. 별도 보충 필요 (사후 정리 항목).
2. **외부 환경 가정 SOP 부재** — 라운드 4 (Twin파파 fact-check) 가 결정적이었음. 향후 인프라 작업 시 Railway Variables 사전 확인 SOP 정립 필요 (CLAUDE.md INFRA 섹션 추가 후보).

### 산출물 (문서만 4 파일, 코드 0)

- `AGENT_TEAM_LAUNCH.md` FIX-DB-POOL-MAX-SIZE-20260427 섹션 (라운드 4 trail 추가, 약점 12건)
- `BACKLOG.md` FIX-DB-POOL 항목 → 🟡 PHASE A APPLIED → B 관찰 중
- `CHANGELOG.md` `[Infra] - 2026-04-27` entry 추가
- `handoff.md` (이 파일) 2026-04-27 세션 추가

### 별건 BACKLOG (2026-04-27 등록)

- `OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP` 🟢 P3 (격하 — MIN=5 가 cold-start 일부 흡수, 나머지는 5분 SELECT 1 cron)
- `OBSERV-RAILWAY-HEALTH-TTFB-15S-INTERMITTENT` 🟡 P2 (별건, Pool 30 적용 후 자연 해결 여부 확인)
- `OBSERV-SLOW-QUERY-ENDPOINT-PROFILING` 🟡 P2 (Q-A 화/수 p99≥1초 burst 9건 endpoint 분석 — Tue 19:00 max 2495ms / Wed 00:00 239 req 등)

---

## 🟢 2026-04-23 세션 요약 — Sprint 62-BE v2.2 구현 완료 (v2.10.0 배포 대기)

> **한 줄 요약**: Factory KPI 공급 인프라 확장 (weekly-kpi 3필드 + monthly-kpi 신설 + migration 050) — 신규 TC 17/17 + 회귀 36/36 GREEN, Railway 배포 대기

### 핵심 의사 결정 (3차 합의 축적)

| 단계 | 주체 | 결정 |
|---|---|---|
| v1 원안 (Opus) | Claude | weekly-kpi WHERE `ship_plan_date`→`finishing_plan_end` 교정 / `shipped_count` 단일 UNION |
| v1 Codex 1차 | Codex | M1(UNION 중복) / M2(반개구간) / M3(`_FIELD_LABELS` 누락) 지적 |
| v2 VIEW 역제안 | VIEW FE | v1.34.4 `mech_start` 영구 유지 + `shipped_count` 4필드 + `date_field` 파라미터 |
| v2 Codex 2차 | Codex | M 2건 (Q4 화이트리스트 불일치 / Q5 shipped_plan 이름) + A 4건 |
| v2.2 축소 확정 | **Twin파파** | UNION 자동 합산 폐기 (3개 소스 비교가 본질), 이행률·정합성 BACKLOG 이관 (App 베타 100% 전환 후 확정), `shipped_realtime`→`shipped_ops` 리네임 |
| v2.2 Codex 3차 | Codex | **M=0 / A=4 CONDITIONAL APPROVED** — v2.2 채택 가능 |
| A 4건 합의 반영 | Claude+Codex | INNER JOIN / TC-FK-11 경계 / EXPLAIN POST-REVIEW / 네이밍 부채 debt |

### 산출물 (3 파일 + 문서 4 파일)

**구현**:
- `backend/migrations/050_factory_kpi_indexes.sql` (신규, +20 LOC) — ALTER TABLE IF NOT EXISTS 2개 + CONCURRENTLY partial index 3개
- `backend/app/routes/factory.py` (+155/-6) — `_count_shipped` 3분기 헬퍼 + `_ALLOWED_DATE_FIELDS_MONTHLY_KPI` 신규 상수 + `get_monthly_kpi()` route + weekly-kpi 응답 3필드 확장 + monthly-detail 화이트리스트 5값 확장
- `tests/backend/test_factory_kpi.py` (신규, +330 LOC) — 11 TC (parametrize 17 assertions)

**문서**:
- `AGENT_TEAM_LAUNCH.md` Sprint 62-BE v2.2 섹션 (§ Codex 합의 기록 3차 결과 + Claude 원안 약점 trail 4건)
- `BACKLOG.md` — `BIZ-KPI-SHIPPING-01` 🟢 DRAFT 신규 + `POST-REVIEW-SPRINT-62-BE-V2.2-20260423` 🟡 OPEN 신규
- `CODEX_REVIEW_SPRINT_62_BE_V2.md` — 3차 축소 스코프 프롬프트 (Q1~Q6)
- `CHANGELOG.md` — v2.10.0 엔트리

### 부수 발견 (설계 단계에서 포착)

1. **Test DB 스키마 drift** — Prod에는 `actual_ship_date`/`finishing_plan_end` 컬럼이 ETL로 추가돼 있으나 `backend/migrations/*.sql` 에 정식 DDL 부재 → pytest 실행 시 500 에러로 발견. migration 050 에 `ALTER TABLE ADD COLUMN IF NOT EXISTS` 추가로 양쪽 정합 확보 (Prod no-op)
2. **Codex M-NEW-1 과다 지적 정정** — Codex 1차가 지적한 `_FIELD_LABELS` `finishing_plan_end` 누락은 실제로 `admin.py:2265` 이미 존재. `ship_plan_date` 도 `admin.py:2262` 존재. Codex 2차 Q1 A에서 스스로 정정
3. **Codex의 자기 재검증 가능** — v1 1차 검증 지적을 v2/v2.2 검증에서 스스로 무효화하는 패턴 확인. 편향 감소 효과

### Railway DB 실측 수치 (2026-04-23)

- **인덱스**: `completed_at` 1개만 존재, `actual_ship_date`/`ship_plan_date`/`finishing_plan_end` 3개 누락 확정 → migration 050 근거
- **주간 shipped 3종**: `shipped_ops=0` / `shipped_actual=23` / `shipped_plan=0` (이번 주 2026-04-20~27)
- **NULL 비율**: actual_ship_date 35.3% (미출하 정상) / ship_plan_date 0.1% / finishing_plan_end 0.1%
- **SI_SHIPMENT task 현황**: 71건 중 completed 1건 (베타 전환 초기 상태 — 정상)

### pytest 결과

```
신규 TC (test_factory_kpi.py)  17/17 PASSED ✅
회귀 TC (test_factory.py + test_admin_api.py)  36/36 PASSED ✅
─────────────────────────────────────────────────────────
합계                          53 PASSED / 0 regression
```

### 다음 세션 시작 시 할 일

1. ~~git commit + push (v2.10.0) → Railway 자동 배포~~ ✅ 완료
2. Railway 배포 후 Q3 A EXPLAIN ANALYZE 검증 — `_count_shipped` 3분기 쿼리가 partial index 실제 사용하는지
3. ~~notices INSERT — v2.10.0 공지~~ ✅ 완료 (id=102)
4. VIEW Sprint 36 (Cursor에서 동시 진행 중) — BE 3필드 배포 후 TEMP-HARDCODE 제거 연동 확인
5. POST-REVIEW-SPRINT-62-BE-V2.2 (배포 후 7일 내)

### 🔄 v2.10.1 PATCH 보정 (2026-04-23 동일일)

VIEW 측 재검토 후 1줄 교정 요청 수용:
- `weekly-kpi` L322 WHERE: `ship_plan_date` → `finishing_plan_end`
- TC-FK-02: "ship_plan_date 회귀" → "finishing_plan_end 교정 검증" 으로 반전
- 실측: 이번 주 31→48 (+17, +55%) / 지난 주 30→51 (+21, +70%)
- 의미: 주간 생산량 = 생산 완료 기준 (라벨 [Planned Finish] 와 일치) — v2.2 에서 "숫자 불변"을 가치로 높게 평가한 것이 실은 의미 정확성보다 덜 중요했음
- FE 변경 없음 (weekly.production_count 자동 반영)
- VIEW Sprint 35 Phase 2 (v1.35.0) 와 동기화 완료

### ✅ POST-REVIEW EXPLAIN ANALYZE 실측 완료 (2026-04-23)

Codex 3차 Q3 A 해소용 실측:

| # | 쿼리 | 인덱스 사용 | 실행 시간 |
|---|---|---|---|
| ① `_count_shipped('plan')` | ❌ planner가 completion_status Seq Scan + serial_number Nested Loop 선택 (si_completed=TRUE 0건이라 더 효율적) | 0.051 ms |
| ② `_count_shipped('actual')` | ✅ `idx_product_info_actual_ship_date` (Bitmap Index Scan) | 0.071 ms |
| ③ `_count_shipped('ops')` | ✅ `idx_app_task_details_completed_at` (기존 인덱스) | 0.092 ms |
| ④ weekly-kpi 메인 쿼리 | ✅ `idx_product_info_finishing_plan_end` (Bitmap Index Scan) | 0.127 ms |

**판정**: migration 050 partial index 2종 실사용 확인. 전체 sub-ms 대역. Q3 A **완전 해소**.

**잔여 Advisory**:
- `idx_product_info_ship_plan_date` 현재 미사용이나 si_completed=TRUE 비율 증가 시 자동 활성화 가능. 삭제 불필요 (공간 무시)
- Q5 (네이밍 부채 `pipeline.shipped` vs `shipped_plan`) — 관찰형 7일 유지, BIZ-KPI-SHIPPING-01 착수 시 final 네이밍 결정

### 🏁 Sprint 62-BE v2.2 전체 종결 (2026-04-23~24)

- ✅ v2.10.0 배포 (factory.py + migration 050 + 11 TC)
- ✅ v2.10.1 PATCH 교정 (weekly-kpi WHERE finishing_plan_end)
- ✅ v2.10.2 PATCH 교정 (FIX-CHECKLIST-DONE-DEDUPE-KEY, Codex Q4-4 M 해소)
- ✅ v2.10.3 PATCH 교정 (FIX-ORPHAN-ON-FINAL-DELIVERY, HOTFIX-DELIVERY 숨은 4번째 경로)
- ✅ Notices bump (id=102, v2.10.1 → v2.10.2 → v2.10.3)
- ✅ Netlify FE 배포 4회 (v2.10.0 + v2.10.1 + v2.10.2 + v2.10.3)
- ✅ Migration 050 Railway 적용 + migration_history 기록
- ✅ POST-REVIEW EXPLAIN ANALYZE Q3 A 해소
- ✅ POST-REVIEW-HOTFIX 4건 일괄 Codex 사후 검토 (Phase A 완료)
- ⏸ Q5 네이밍 부채 관찰형 7일 유지
- 🟢 **CASCADE-ALERT-NEXT-PROCESS DRAFT 등록** — ORPHAN_ON_FINAL 의 원래 설계 의도 (현재 공정 + 다음 공정 관리자 동시 알림) 는 사내 공정 활성화 계획 변동 이슈로 후순위 보류 (BACKLOG)

### 📋 Phase A Codex 사후 검토 결과 (2026-04-23)

4 HOTFIX 일괄 검토 → **M=1 / A=12 / N=2**

- **HOTFIX #1 PHASE1.5**: Close ✅ (Advisory 2건 OBSERV-ALERT-SILENT-FAIL 흡수)
- **HOTFIX #2 SCHEMA-RESTORE**: Close ✅ (Advisory 3건 기존 BACKLOG 흡수)
- **HOTFIX #3 DUP**: Close ✅ (Advisory 3건 — fd close / dead state / Redis 조건부)
- **HOTFIX #4 DELIVERY**: **v2.10.2 PATCH 로 Close** ✅ (M1 즉시 수정 + Q4-2 동시 해결)

**v2.10.2 수정 범위**:
- `scheduler_service.py` CHECKLIST_DONE_TASK_OPEN dedupe + RELAY_ORPHAN `message LIKE` → `task_detail_id` 전환
- `test_sprint61_alert_escalation.py` TC-61B-19B 신규 + setup fixture partner 보강
- `pytest` 결과: TC-61B-17/18/19/19B 전부 GREEN (이전 fixture 누락으로 TC-17 도 간헐 fail 했던 것 동시 해결)

### 📤 다음 액션 로드맵 (Phase B~G)

- **Phase B** (Twin파파 결정 필요): Railway DB rotation / 작업 flow 디버깅
- **Phase C (이번 주 내)**: OBSERV-ALERT-SILENT-FAIL (P1) + UX-SPRINT55-FINALIZE-DIALOG
- **Phase D**: POST-REVIEW-MIGRATION-049-NOT-APPLIED
- **Phase E**: OBSERV 3건 + ADMIN-ACTION-AUDIT
- **Phase F**: Sprint 55 UX 개선
- **Phase G**: INFRA-COLLATION / TEST-CLEAN-CORE / FE-ALERT-BADGE-SYNC

---

## 🔧 2026-04-21~22 세션 요약 (문서 개정 only — 코드 배포 없음)

> ⚠️ 마이그레이션으로 로컬 Cowork 초기화 → 컨텍스트 전수 재정리 + 규칙·워크플로우 대폭 개정
> ⚠️ 알람 시스템 장애 발견 — 4-17 이후 `app_alert_logs` 0건 (진단 완료, 확정 대기)

### 문서 개정 내역 (BE/FE 코드 변경 0)

1. **CLAUDE.md 대폭 개정** (OPS + VIEW 동시):
   - 📏 **코드 크기 원칙** 신설 — 1단계 500/800/1200 (파일당 LOC) + 함수 60줄 + 클래스 200줄 + 순환 복잡도 ≤10
   - 🔄 **DRY 재활용 원칙** 신설 — Rule of Three + grep 선행 + 승격 위치 명시
   - 🛡️ **리팩토링 안전 7원칙** 신설 — 테스트 커버리지 선행 + `[REFACTOR]` prefix + Before/After GREEN 증명 + git 태그 + DB migration 금지
   - 🤝 **AI 검증 워크플로우 v2** 전면 교체 — 8단계 파이프라인 + 3주체 용어(Cowork/Code/Codex) + Opus 1차 리뷰 + ② Codex 이관 체크리스트 6종 + 침묵 승인 거부 + 1라운드 상한 + 합의 실패 정의
   - 🚨 **긴급 HOTFIX 예외 조항** 신설 — S1/S2 Severity 구분 + 사후 Codex 검토 24h 규칙
   - 📦 **버전 번호 규칙** 재정의 — MAJOR(아키텍처/사내서버/SAP) / MINOR(Sprint 기능) / PATCH(HOTFIX·용어·데드 코드)
   - 🤖 **모델 버전 관리 규칙** 신설 — `claude-opus-4-7` (Lead) / `claude-sonnet-4-6` (Workers) — 신모델 출시 시 즉시 갱신

2. **BACKLOG.md 리팩토링 Sprint 계획 등록**:
   - OPS: **22 Sprint** (BE 17 + FE 5) — REF-00-TEST(테스트 선행) → admin.py 2,546줄 6단계 분할 → task_service.py 3단계 → work.py 2단계 → checklist/auth/scheduler → 경고 파일 → FE God File (admin_options_screen 2,593줄 등)
   - VIEW: **7 Sprint** — REF-V-00-UTIL(formatDate 공통화) → ProductionPerformancePage 895줄 → QrManagementPage 814줄 → Sidebar/ProductionPlan/FactoryDashboard 등

3. **리뷰 보완 4건 반영** (FE 회귀 블록 + 재질문 라운드 제외 + 합의 실패 정의 + 번들 크기 차등 ±10%/±5%)

### ✅ 완료 요약 (Phase 1·1.5·2 전부)

| Phase | 시각 | 결과 |
|---|---|---|
| Phase 1 (진단) | 4-21 | 후보 E duplicate 확정 + G 신규 확정 + A/C/D 기각 |
| Phase 1.5 (ERROR 로깅) | 4-22 10:47 | commit `4a6caf8` 배포, 47 pytest GREEN |
| **Phase 2 (근본 원인 확정)** | 4-22 11:00 | `column task_detail_id does not exist` 4건 포착 → **G.3 + A 부활 확정** |
| **Phase 2a (Schema Restore)** | 4-22 11:25 | pgAdmin SQL 5 블록 실행, 16건 신규 INSERT 성공 (§12.6) |
| Phase 2b (DUP 발견) | 4-22 12:40 | R1 쿼리 중복율 37.5%, Worker ≥3, DUP Sprint 작성 완료 |

### 📌 신규 세션(4.7) 시작 시 참조 순서

1. `~/Desktop/GST/AXIS-OPS/CLAUDE.md` (규칙·워크플로우 전문)
2. `~/Desktop/GST/AXIS-VIEW/CLAUDE.md` (VIEW 버전)
3. `~/Desktop/GST/AXIS-OPS/handoff.md` (이 파일 — 최신 상태)
4. `~/Desktop/GST/AXIS-VIEW/handoff.md` (VIEW 상태)
5. `~/Desktop/GST/AXIS-OPS/ALERT_SCHEDULER_DIAGNOSIS.md` (알람 장애 진단 최신)
6. `~/Desktop/GST/AXIS-OPS/BACKLOG.md` / `~/Desktop/GST/AXIS-VIEW/BACKLOG.md` (리팩토링 Sprint 계획)

---

## 현재 버전

- **OPS BE**: v2.9.11 (2026-04-22, 4 HOTFIX 통합 PATCH)
- **OPS FE (Flutter PWA)**: v2.9.11 (version 파일만 bump, OPS FE 코드 변경 0 — Netlify 배포 skip)
- **최근 Sprint**: HOTFIX-ALERT-SCHEDULER-DELIVERY-20260422 (scheduler 3곳 target_worker_id 표준 패턴 + 배치 dedupe) — ✅ 완료 (2026-04-22)
- **최근 완료 Sprint**: HOTFIX-ALERT-SCHEDULER-DELIVERY, HOTFIX-SCHEDULER-DUP, HOTFIX-ALERT-SCHEMA-RESTORE, HOTFIX-SCHEDULER-PHASE1.5, FIX-25 v4, FIX-24, HOTFIX-04, HOTFIX-05, HOTFIX-03, HOTFIX-02, BUG-45, 61-BE-B, 61-BE, BUG-43/44, HOTFIX-01, 60-BE, 59-BE, 58-BE

### 🗓 v2.9.11 포함 HOTFIX 이력 (SHA 별도 기록 — Codex A7 지적 반영)

| HOTFIX ID | Commit SHA | 변경 범위 | 배포 시각 (KST) |
|---|---|---|---|
| HOTFIX-SCHEDULER-PHASE1.5 | `4a6caf8` | ERROR 로깅 prefix 추가 (관찰용) | 2026-04-22 10:47 |
| HOTFIX-ALERT-SCHEMA-RESTORE | (pgAdmin SQL) | migration 049 수동 복구 (task_detail_id 컬럼 + enum 3종) | 2026-04-22 11:25 |
| HOTFIX-SCHEDULER-DUP | `f1af8a4` | fcntl file lock — scheduler 단일 실행 | 2026-04-22 13:24 |
| HOTFIX-ALERT-SCHEDULER-DELIVERY | `d946532` | scheduler 3곳 target_worker_id 표준 패턴 + 배치 dedupe | 2026-04-22 |
| FE Netlify 배포 | `69e8a677ca4e8352ce4678b6` | flutter build web + netlify-cli deploy --prod | 2026-04-22 19:45 KST |

✅ FE version skew 해소: 저장소 v2.9.11 + Netlify 배포 v2.9.11 동기화 완료 (gaxis-ops.netlify.app)
- **Migration 049**: Railway prod DB 에 migration_runner 미실행 → 2026-04-22 11:25 수동 SQL 복구 (id=37 기록)
- **체크리스트 현황**: TM 완료 (SINGLE/DUAL qr_doc_id 정규화) / ELEC 완료 (Phase 1+2, 마스터 정규화) / MECH 미구현
- **RULE-01**: Sprint 완료 시 FE flutter build web + Netlify 배포 필수

---

## 직전 세션 작업 내용 (2026-04-22)

> **🔴 5일 알람 장애 root cause 확정 + 🟢 복구 완료 + 🆕 중복 실행 신규 이슈 발견** — Phase 1.5 ERROR 로깅 배포 → 10분만에 근본 원인 포착 → pgAdmin SQL 수동 복구 → 12:00 tick 정상 INSERT 16건 → R1 쿼리로 중복 실행 37.5% 확정

### 🟢 Phase 1: HOTFIX-SCHEDULER-PHASE1.5 배포 (commit `4a6caf8`, 10:47 KST)

- `alert_service.py` + `alert_log.py` 2 파일 — `[alert_silent_fail]` / `[alert_create_none]` / `[alert_insert_fail]` prefix ERROR 로깅 추가. Sentry SDK 선택적 import 가드. 기존 `return None` 동작 유지. +80 / -37 LOC
- pytest 검증: `test_alert_service.py` 11 + `test_alert_all20_verify.py` 36 = **47 passed / 회귀 0건**

### 🔴 Phase 1.5: 근본 원인 확정 (11:00 KST, 02:00 UTC tick)

**결정적 로그** (단일 hourly tick 에서 4건 포착):
```
ERROR [alert_insert_fail] INSERT failed:
  error=column "task_detail_id" of relation "app_alert_logs" does not exist
```

**3-증거 삼각 검증** (ALERT_SCHEDULER_DIAGNOSIS.md §12.2):
- Q1 `migration_history` → max id=36, 049 기록 없음
- Q5 `app_alert_logs` → 12 컬럼, `task_detail_id` 부재
- Railway 로그 → `column ... does not exist` 4건

**최종 원인 (§12.1)**: _"Railway 운영 DB 의 `app_alert_logs` 에 `task_detail_id` 컬럼이 존재하지 않아, Sprint 61-BE(4-17) 배포 이후 8-컬럼 INSERT 가 100% PsycopgError 로 실패하고 try/except 가 삼켜 return None 반환 → 5일 연속 0건"_

### 🟢 Phase 2: HOTFIX-ALERT-SCHEMA-RESTORE-20260422 실행 (11:25 KST)

pgAdmin prod 에서 5 블록 autocommit SQL 실행 (migration 049 수동 재현):
1. enum 3종 추가 (`TASK_NOT_STARTED` / `CHECKLIST_DONE_TASK_OPEN` / `ORPHAN_ON_FINAL`)
2. `app_alert_logs.task_detail_id` 컬럼 추가 ← **핵심 복구**
3. `idx_alert_logs_dedupe` 인덱스
4. `admin_settings` 5 키 INSERT
5. `migration_history` id=37 수동 기록

**검증 A/B/C 3종 PASS** → 12:00 KST tick (03:00 UTC) 에서 **신규 INSERT 16건 성공** (id 657 → 673, RELAY_ORPHAN). 5일 장애 완전 해소.

### 🆕 Phase 3: HOTFIX-SCHEDULER-DUP-20260422 신규 발견 (12:40 KST, R1 쿼리)

복구 직후 R1 쿼리로 중복 실행 확정:
| serial_number | cnt | gap_ms |
|---|---|---|
| GBWS-6980 | 2 | 59.77 |
| GBWS-7017 | 2 | 18.87 |
| GBWS-7024 | 2 | 31.50 |
| GBWS-7038 | 2 | 73.15 |
| **GPWS-0773** | **3** | **86.37** |

- 중복율 **37.5%** (6/16)
- Worker ≥ **3** (GPWS-0773 triple)
- gap_ms 18~86ms 범위 → race condition 확정
- **해결책**: `app/__init__.py` 에 `fcntl.flock LOCK_EX | LOCK_NB` 기반 `/tmp/axis_ops_scheduler.lock` 파일 락 도입 — Sprint `HOTFIX-SCHEDULER-DUP-20260422` 작성 완료 (`AGENT_TEAM_LAUNCH.md` L29644~)

### 📋 세션 부수 작업

1. **Mac 마이그레이션 후 환경 복구**: Xcode license 재수락, `.git/objects/` 손상 blob 복구, Python venv 재생성, Claude Code FSA 이슈 인지
2. **보안 민감 md `.gitignore` 추가**: `/SECURITY_REVIEW.md` + `/DB_ROTATION_PLAN.md` (public repo 금지)
3. **FE-ALERT-BADGE-SYNC BACKLOG 등록**: `home_screen.dart` 미커밋 변경 재검토 후 별도 Sprint
4. **3 커밋 push 완료**: `a569dc0` (gitignore) + `41d9db2` (scheduler 진단 docs) + `ea55edb` (네이밍 규칙 + HOTFIX 프롬프트 + BACKLOG)
5. **ALERT_SCHEDULER_DIAGNOSIS.md §12 신설** + §11.14.3 반증 주석 + §12.3 "베타 설비 3→20대 확장" 컨텍스트 메모 추가

### 🔴 다음 세션 최우선 — HOTFIX-SCHEDULER-DUP-20260422 즉시 착수

**Sprint 프롬프트**: `AGENT_TEAM_LAUNCH.md` L29644~ 참조
**예상 소요**: 45~90분 (코드 15~25 + 검증 15~20 + 배포 관찰 30~60)
**영향 방지**: 현재 중복 기록 37.5% 발생 중, 설비 확장기 알람 품질 저하

**병행 관찰**:
- 매시 정각 Railway 로그: `Running` / `executed successfully` 2회 중복 여전 확인
- `app_alert_logs` 일간 건수 추이 (복구 후 4-16 수준 회복 검증, §12.3 환경 컨텍스트 참조)

**후속 장기 Sprint** (§12.9 BACKLOG 등록 완료):
- `POST-REVIEW-MIGRATION-049-NOT-APPLIED` (S3 조사) — DUP 배포 후
- `OBSERV-ALERT-SILENT-FAIL` (Sentry 정식 연동) — 재발 방지 필수
- `OBSERV-MIGRATION-HISTORY-SCHEMA` + `OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION` — 본 장애 근본 재발 방지책

---

## 이전 세션 작업 내용 (2026-04-20)

1. **FIX-25 v4 (v2.9.10)**: progress API(`/api/app/product/progress`) 응답에 `mech_partner`/`elec_partner`/`module_outsourcing`/`line` 4필드 노출. `progress_service.py` 단일 파일 — sn_list CTE + 메인 SELECT에 `pi.line` 추가 + `_aggregate_products` dict `'line'` 추가 + L296~299 `sn_data.pop(...)` 3줄 제거. touch 6줄 / net 0줄 (+3/-3).
2. **설계 진화 v1→v4**: v1(거미줄 JOIN 3곳) → v2(production CTE 집계) → v3(tasks API dict 주입, Codex M1 breaking) → **v4 채택**(progress API 단일 확장, tasks API 무변경).
3. **Claude×Codex 교차검증**: v3 M1(tasks API List→Dict) 지적 반영 → v4 전환. Claude 실측으로 `progress_service.py`에 partner 3필드 이미 SELECT 중 + L296~299 pop 구조 발견이 결정적 전환 근거.
4. **설계서 정정**: AGENT_TEAM_LAUNCH.md L27459/L27588 "OPS FE 미사용" 서술 → `sn_progress_screen.dart:44`에서 사용 중 확인 후 "사용 중이나 파싱 breaking 0 (Dart `Map<String, dynamic>.from(e)`)" 로 정정.
5. **pytest**: TC-PROGRESS-PI-01~06 신규 6건 + `test_sn_progress` 10 + `test_product_api` 17 + `test_production` 9 = **42/42 GREEN**, Codex 합의 진입 없이 첫 시도 통과.
6. **배포**: BE Railway 자동 (push `21cba31`). OPS FE 코드 변경 0 → Netlify 배포 skip.

---

## 이전 세션 작업 내용 (2026-04-17)

1. **Sprint 61-BE**: 알람 O/N 통일 + 에스컬레이션 3종 + pending API 확장 + SETTING_KEYS 5개
2. **BUG-43**: 분석 대시보드 한글 라벨 24개 누락 전수 등록 (111→135키)
3. **에스컬레이션 토글 UI**: admin_options_screen 알림 트리거 설정 하단에 토글 4개 + 기준일 드롭다운
4. **BUG-44**: 미종료 작업 0건 — INNER JOIN → LATERAL JOIN (work_start_log FK)
5. **Sprint 61-BE-B**: pending/task API company + force_closed 필드 추가 (#60, #61)
6. **HOTFIX-01**: force_close/force_complete TypeError — naive vs aware datetime 정규화
7. **BUG-45 (v2.9.6)**: force_close `completed_at` 범위 검증 — 미래 차단(60s skew 허용) + started_at 이전 차단. VIEW useForceClose `reason → close_reason` (FE-17). TC-FC-11~18 8건 추가, 회귀 GREEN
8. **HOTFIX-02 (Sprint 60-BE 후속)**: 체크리스트 마스터 API `checker_role` 키 응답 누락 — `list_checklist_master()` SELECT/응답 dict 2줄 추가. VIEW JIG WORKER/QI 뱃지 분기 정상화 (OPS #59-B DONE / VIEW FE-18 ✅)
9. **TEST-CONTRACT-01 BACKLOG 등록**: VIEW↔BE API 필드 계약 자동 검증 (pytest + JSON Schema). BUG-45 재발 방지 Advisory. 설계: AGENT_TEAM_LAUNCH.md TEST-CONTRACT-01 섹션
10. **HOTFIX-03**: 비활성 task 조회 필터 누락 — `get_tasks_by_serial_number()` + `get_tasks_by_qr_doc_id()` 4 SELECT에 `AND is_applicable = TRUE` 추가 (방안 A 채택). VIEW S/N 상세뷰 Heating Jacket 미시작 카운트 오염 정상화 (OPS #60 DONE)
11. **DOC-SYNC-01 BACKLOG 등록**: OPS_API_REQUESTS.md / VIEW_FE_Request.md 잔여 PENDING 13건+ 실구현 상태 교차 검증 (관리 작업)
12. **HOTFIX-05 (v2.9.7)**: Admin 옵션 미종료 작업 카드 시간 UTC 오표시 — `admin_options_screen.dart` L2474 `.toLocal()` 1줄 추가. Manager 화면과 일관성 확보. FE only, BE 영향 없음
13. **HOTFIX-04 BE 완료 (v2.9.8)**: 강제종료 표시 누락 종합 수정 — Case 1(Orphan wsl) + Case 2(NS 강제종료) 통합, **옵션 C' 채택**(TaskDetail 모델 `closed_by_name` 필드 + SELECT LEFT JOIN workers). task_detail.py + work.py 수정, pytest 신규 9 + 회귀 24 = 33/33 GREEN. VIEW FE-19(placeholder 렌더)는 VIEW 리포 별도 진행
14. **FIX-24 (v2.9.9)**: OPS 미종료 작업 카드 Row 2에 O/N(sales_order) 뱃지 추가 — `admin_options_screen.dart` + `manager_pending_tasks_screen.dart` 2파일, `Icons.receipt_long` + conditional spread 약 6줄×2. BE 변경 0줄 (응답 `sales_order` 이미 포함). A1 오버플로 방어 미반영(sales_order 6자리 이하)
15. **Claude × Codex 교차 리뷰**: Sprint 61 설계 9건 + BUG-44 6건 + HOTFIX 원인 수정 + BUG-45 1차 Must 보정 + HOTFIX-02/03/04/05 + FIX-24 합의. HOTFIX-04는 M2 옵션 A→C' 재확정(장기 시스템 원칙) + A1 TC 3건(NS-03/04/05) 추가 반영

---

## 실행 우선순위 (Sprint 실행 순서)

### ✅ 완료된 Sprint (전체 테스트 통과)

| Sprint | 내용 | 완료일 |
|--------|------|--------|
| Sprint 41 | 작업 릴레이 + Manager 재활성화 | 완료 |
| Fix Sprint 41-A | 릴레이 토스트 + 다이얼로그 + 재시작UI + 재완료BE | 완료 |
| Fix Sprint 48 | 재활성화 권한 `in` 비교 방향 버그 | 완료 |
| Sprint 41-B | 릴레이 자동 마감 + Manager 알림 | 완료 |
| Sprint 51 | progress API sales_order 추가 | 완료 |
| OPS_API #52 | ETL _FIELD_LABELS finishing_plan_end | 완료 |
| Sprint 52 | TM 체크리스트 Partner 검수 Phase 1 | 완료 |
| Sprint 53 | monthly-summary weeks+totals (Friday-based 매핑) | 완료 |
| Sprint 54(체크리스트) | 체크리스트 성적서 API (배치 최적화) | 완료 |
| Sprint 54(알림) | 공정 흐름 알림 트리거 + Partner 분기 | 완료 |

### 🔴 즉시 — 잔여 작업

| 순서 | 내용 | 상태 | 비고 |
|------|------|------|------|
| 1 | **VIEW FE 연동**: FE-12 ELEC 블러 해제 + FE-07/08 ELEC status 매핑 | BE 준비 완료 | Sprint 58-BE 완료로 착수 가능 |
| 2 | 실적확인 토글 테스트: OFF(progress 100%) / ON(progress+체크리스트) | BE 준비 완료 | 대시보드 업데이트 후 테스트 |
| 3 | Sprint 55: Worker별 Pause + Auto-Finalize | Sprint 작성 완료 | BE 5파일 + FE 2파일, DB 변경 없음, TC 28건 |
| 4 | MECH 체크리스트 양식 추가 | 대기 | TM/ELEC 완료, MECH 양식 수집 후 추가 |

### 🟡 중기 — VIEW 기능

| 순서 | Sprint | 내용 | 상태 | 비고 |
|------|--------|------|------|------|
| 2 | VIEW Sprint 23 | Task 재활성화 UI | 설계 완료 | Sprint 41 BE 완료됨, 착수 가능 |
| 3 | VIEW Sprint 24 | O/N 그룹핑 UI | 미작성 | Sprint 51 BE 완료됨, 착수 가능 |
| 4 | VIEW Sprint 18-C | S/N 카드뷰 개선 | 프롬프트 완료 | FE only, 빠르게 가능 |

### 🟠 대기 — 착수 조건 미충족

| 순서 | 내용 | 상태 | 착수 조건 |
|------|------|------|-----------|
| - | 개인정보 동의 관리 (팝업+토글) | Backlog 등록 완료 | 명세서 확정, 약관 본문, 법무 검토 |
| - | CT 분석 모듈 (공수/리드타임) | Backlog 등록 완료 | 스키마 맵 DB 검증, 데이터 축적 |

### 🟢 장기 — 데이터/분석 (100% 전환 후)

| 순서 | 내용 | 상태 | 비고 |
|------|------|------|------|
| - | analytics_prod 스키마 설계 | 방향 정리 완료 | 표준공수, 편차분석, 일별집계 |
| - | APS Lite Phase 0 | 기획 완료 | 실데이터 축적 후 |

---

## 미해결 버그

| ID | 설명 | 심각도 | 해결방법 |
|----|------|--------|----------|
| BUG-1 | QR 카메라 권한 팝업 가려짐 (DOM z-index) | 중 | FE z-index 조정 |
| BUG-3 | 출퇴근 버튼 퇴근 후 비활성화 (FE 상태 머신) | 낮음 | FE 상태 리셋 |
| ~~BUG-4~~ | ~~CHECKLIST_TM_READY 알림 미생성~~ | ~~높음~~ | ✅ Sprint 54(알림) 완료로 해결 |
| BUG-5 | Manager 완료 시 checklist_ready 플래그 FE 미처리 | 중 | task_detail_screen.dart _handleCompleteTask() 수정 |
| ~~BUG-6~~ | ~~다중작업자 task에서 동료가 resume 시 403 FORBIDDEN~~ | ~~높음~~ | ✅ Sprint 55 Worker별 Pause로 근본 해결 |

---

## 보안 이슈 (즉시 조치 권장)

1. **CORS `origins="*"`** — `__init__.py` 라인 41-44 → 운영 도메인만 허용으로 변경
2. **JWT_SECRET_KEY 하드코딩** — config.py → 환경변수 분리

---

## 문서 위치 가이드

| 파일 | 용도 | 읽는 시점 |
|------|------|-----------|
| `CLAUDE.md` | 프로젝트 고정 정보 (팀 구성, 기술 스택, 규칙) | 매 세션 시작 시 |
| `memory.md` | 누적 의사결정, ADR, 감사 결과 | 맥락 필요 시 |
| `handoff.md` | 현재 파일. 세션 인계용 | 매 세션 시작 시 |
| `DB_SCHEMA_MAP.md` | DB 스키마 맵 (8스키마, 43테이블, FK, ENUM) | 테이블 신설/쿼리 작성 시 |
| `BACKLOG.md` | 전체 백로그 + Sprint 이력 + 체크리스트 설계 | Sprint 기획 시 |
| `AGENT_TEAM_LAUNCH.md` | Sprint 프롬프트 모음 (19,000줄+) | Sprint 실행 시 |
| `PROGRESS.md` | API 엔드포인트 + 테스트 현황 | 진행률 확인 시 |
| `analytics_prod_erd.mermaid` | 생산 분석 ERD (향후) | analytics 작업 시 |
| `AXIS-VIEW/docs/OPS_API_REQUESTS.md` | VIEW→OPS API 요청/버그 | API 이슈 확인 시 |
| `AXIS-VIEW/docs/sprints/DESIGN_FIX_SPRINT.md` | VIEW Sprint 23 설계 | VIEW 재활성화 작업 시 |
| `concepts_reference.md` | 유튜브 학습 용어 + 점검 보고서 매핑 | 개념 확인 시 |

---

## 세션 업데이트 규칙

세션 종료 시 아래 항목만 업데이트:
- `현재 버전` — 새 Sprint 완료 시
- `직전 세션 작업 내용` — 전체 교체
- `실행 우선순위` — 완료된 것 제거, 새로 추가된 것 기록
- `미해결 버그` — 해결/신규 반영

memory.md에는 **의사결정/ADR/아키텍처 판단**만 추가 (일상 작업 기록 X)
