# 세션 종합 인수인계서

**작성일**: 2026-04-17
**최종 업데이트**: 2026-04-17 (BUG-45 완료, pytest TC-FC-11~18 8/8 + 회귀 46/46 GREEN)
**프로젝트**: GST AXIS-OPS (Flutter PWA) + AXIS-VIEW (React Dashboard)
**현재 버전**: v2.9.6

---

## 1. 프로젝트 구조

- **AXIS-OPS**: Flutter PWA — 현장 작업자용 모바일 앱 (작업 시작/완료/체크리스트/QR 스캔)
- **AXIS-VIEW**: React 대시보드 — 관리자용 웹 (S/N 진행현황, 분석, 성적서)
- **공용 백엔드**: Flask + PostgreSQL (Railway 배포)
- **핵심 문서**: `CLAUDE.md` (AI 에이전트 규칙), `AGENT_TEAM_LAUNCH.md` (스프린트 설계서), `BACKLOG.md` (버그/이슈 추적)

---

## 2. AI 검증 워크플로우 (CLAUDE.md에 등록됨)

이번 세션에서 Claude-Codex 교차 검증 파이프라인을 양쪽 CLAUDE.md에 추가:

```
①설계서 작성 → ②Codex 교차 검증 → ③설계 보정 → ④코드 구현 → ⑤pytest → ⑥머지
```

**교차 검증 3원칙**:
1. 전수 검증 — 설계서 전체를 대상으로 검증 (부분 체크 금지)
2. 맹목 수용 금지 — 검증 결과를 무조건 반영하지 않고, 타당성 판단 후 적용
3. M/A 분류 — Must fix(반드시 수정) / Advisory(권고) 구분하여 관리

---

## 3. 이번 세션 완료 작업

### 3-1. Sprint 61-BE 설계 보정 (10건)

Codex 교차 검증으로 발견된 9+1건 보정 완료 (AGENT_TEAM_LAUNCH.md):

| ID | 유형 | 내용 |
|----|------|------|
| M1 | Must | `_trigger_tm_checklist_alert()` — sn_label() 치환 방식 통일 |
| M2 | Must | Task 1-2 ORPHAN 알림 sn_label 적용 |
| M3 | Must | SETTING_KEYS 5개 등록 (alert_task_not_started_enabled 등) |
| M4 | Must | Task 3 SQL — `product_info pi` → `plan.product_info pi` (양쪽 UNION) |
| M5 | Must | Task 3-4 — COUNT FILTER 쿼리 분리 (total = len(tasks) 대체) |
| M6 | Must | Task 3-5 — Python COMPANY_CATEGORIES dict + get_categories_for_company() |
| A1 | Advisory | Migration 049 — alert_logs에 task_detail_id 컬럼 + dedupe index |
| A2 | Advisory | WebSocket room mapping — WS_ROOM_MAP dict |
| A3 | Advisory | Task 3-6 — force_close_task() NOT_STARTED 권한 수정 |
| M1-2b | Must | `_trigger_tm_checklist_alert()` L671-674 인라인 라벨 → sn_label() |

### 3-2. BUG-43 수정 완료 ✅

**파일**: `backend/app/routes/analytics.py`
**문제**: Sprint 52 이후 추가 엔드포인트 24개의 한글 라벨 미등록 → VIEW 분석 대시보드에 영문 노출
**수정**: `_ENDPOINT_LABELS`에 24개 추가 (111키 → 135키, 유니크 108 라우트 전수 커버)

추가 항목:
- checklist: TM 3, ELEC 3, 마스터 5, 성적서 2 = 13개
- admin: 5개 (force_complete_task, get_active_tasks 등)
- product: 2개, work: 3개, auth: 1개

### 3-3. BUG-44 수정 완료 ✅

**문제**: OPS "미종료 작업" Admin/Manager 양쪽 0건 반환
**파일**: `backend/app/routes/admin.py` — `get_pending_tasks()` L1705-1741
**상태**: ✅ 코드 적용 완료 (2026-04-17, v2.9.5)

**원인**: `INNER JOIN workers w ON t.worker_id = w.id` — `app_task_details.worker_id`가 전부 NULL (정상 설계).
- `start_task()`는 `started_at`만 UPDATE, worker_id 미세팅
- 작업자 추적은 `work_start_log` 테이블에서 별도 관리
- VIEW는 `work_start_log`로 JOIN하므로 정상

**수정 (Claude × Codex 합의 적용)**:

```sql
FROM app_task_details t
LEFT JOIN LATERAL (
    SELECT wsl2.worker_id
    FROM work_start_log wsl2
    WHERE wsl2.task_id = t.id          -- FK 매칭 (REFERENCES app_task_details(id))
    ORDER BY wsl2.started_at DESC
    LIMIT 1
) wsl ON TRUE
LEFT JOIN workers w ON wsl.worker_id = w.id
...
  AND (w.company = %s OR %s IS NULL)   -- 유지: work_start_log 작업자 company 기반
```

교차 검증 핵심: FK `wsl2.task_id = t.id` 사용(task_id_ref 단독 금지), company SQL 필터 유지(FNI/BAT MECH 중복 방지).

### 3-4. Sprint 61-BE-B 완료 ✅ (v2.9.5)

**목적**: BUG-44 보완 + VIEW Sprint 33 FE-15 선행 조건 해소 — OPS_API_REQUESTS.md #60/#61

**적용 위치**:

| Task | 파일·라인 | 내용 |
|------|-----------|------|
| 1-1 | `admin.py` L1713 | 진행 쿼리 SELECT에 `w.company AS worker_company` 추가 |
| 1-2 | `admin.py` L1802 | 응답 dict에 `'company': row.get('worker_company')` |
| 1-3 | `admin.py` L1753 | 미시작 쿼리 SELECT에 `NULL AS worker_company` (B1 보완) |
| 2-1 | `work.py` L597 | `/api/app/tasks/{sn}` SELECT에 `w.company AS worker_company` |
| 2-2 | `work.py` L617 | worker_entry dict에 `'company': row['worker_company']` |
| 2-3 | `work.py` L693 | legacy fallback에 `'company': None` (B2 보완) |
| 3-1 | `work.py` L93 | task dict에 `'force_closed': getattr(task, 'force_closed', False)` (#61) |

**결과**: `/api/admin/tasks/pending` + `/api/app/tasks/{sn}` 양쪽 응답에 `company` 필드 노출, S/N task에 `force_closed` 필드 포함. FE 하위호환 유지 (필드 추가만).

### 3-5. HOTFIX `force_close_task()` / `force_complete_task()` TypeError ✅ (v2.9.5)

**파일**: `backend/app/routes/admin.py` — `force_close_task()` L1170-1200, `force_complete_task()` L897-960
**증상**: VIEW에서 `PUT /api/admin/tasks/{id}/force-close` → 500. Railway 로그에 `TypeError: can't subtract offset-naive and offset-aware datetimes`.

**Claude × Codex 교차 검증 결과 (설계 대비 확장)**:
- 원래 설계: `started_at`의 naive→aware 정규화만 (2줄 추가)
- 실제 구현: **`completed_at`이 진짜 원인** — `datetime.fromisoformat(completed_at_param)`이 offset 없는 ISO 문자열을 받으면 naive 반환 → DB `started_at`(aware 여부는 psycopg2/DB 설정 의존)과 충돌 가능.
- 양쪽 모두 naive→KST aware 정규화 적용 (safety net).
- `force_close_task()` + `force_complete_task()` **2곳 모두** 동일 패턴 적용.

**수정 패턴**:
```python
# HOTFIX: naive datetime → KST aware 정규화 (fromisoformat offset 누락 대응)
if completed_at.tzinfo is None:
    completed_at = completed_at.replace(tzinfo=Config.KST)

started_at = row['started_at']
if started_at and started_at.tzinfo is None:
    started_at = started_at.replace(tzinfo=Config.KST)
```

**현재 상태**: ✅ **pytest 29/29 passed** — v2.9.5 확정. Netlify 재배포 단계로 진입.

---

### 3-6. BUG-45 완료 ✅ (v2.9.6)

**목적**: VIEW 강제 종료 INVALID_REQUEST(필드명 미스매치) + completed_at 범위 검증 부재 해소

**구현 위치**:

| Task | 파일·라인 | 내용 |
|------|-----------|------|
| 1-a | `admin.py` L1185-1191 | 미래 시각 차단 (60s skew 허용) — `INVALID_COMPLETED_AT_FUTURE` |
| 1-b | `admin.py` L1198-1203 | started_at 이전 시각 차단 — `INVALID_COMPLETED_AT_BEFORE_START` |
| docstring | `admin.py` L1098-1099 | Returns 섹션에 400 에러 코드 2개 추가 |
| FE-17 | `AXIS-VIEW/app/src/hooks/useForceClose.ts` L24 | `reason → close_reason` |
| Test | `tests/backend/test_force_close.py` | TC-FC-11~18 8건 추가 |

**Codex 합의 핵심**:
- force_complete_task() 검증은 Advisory 하향 (미호출 엔드포인트)
- 60s clock skew는 NTP/브라우저 오차 커버로 적절
- == boundary 허용(0분 task), helper 추출은 인라인 1회 권고
- 테스트 경로 `tests/backend/`, TC 번호 `TC-FC-11~18` 사용

**검증 결과**:
- TC-FC-11~18 (BUG-45 신규) 8/8 PASSED
- TC-FC-01~10 (회귀) 모두 PASSED, 1 skipped (pre-existing)
- test_admin_api + test_admin_options_api 46/46 PASSED
- **합계 63 passed, 1 skipped, 0 failed**

---

## 4. 진행 중 / 미완료 작업

| 항목 | 상태 | 상세 |
|------|------|------|
| **VIEW Sprint 33 FE-15** | ⏳ 착수 가능 | BE 선행(#60/#61) 완료 → SNDetailPanel 강제종료 UI. `AXIS-VIEW/VIEW_FE_Request.md` |
| **BUG-42** | 🔴 미착수 | QR 스캐너 소형 명판 접사 인식 실패. BACKLOG.md 등록됨 |

> 코드 관련 작업은 **모두 완료** (v2.9.6) — BUG-45 pytest 63/63 passed. 남은 항목은 VIEW FE 후속.

---

## 5. 핵심 파일 위치

### 설계/관리 문서
| 파일 | 용도 |
|------|------|
| `AXIS-OPS/CLAUDE.md` | AI 에이전트 규칙 + 버전 히스토리 (~1210줄) |
| `AXIS-VIEW/CLAUDE.md` | VIEW측 AI 규칙 (~440줄) |
| `AXIS-OPS/AGENT_TEAM_LAUNCH.md` | 스프린트 설계서 (~27800줄) — Sprint 61-BE + BUG-43/44 포함 |
| `AXIS-OPS/BACKLOG.md` | 버그/이슈 추적 — BUG-1~44 |
| `AXIS-OPS/HANDOVER_BUG44.md` | BUG-44 전용 인수인계 (수정 전/후 코드 포함) |

### BUG-44 관련 코드
| 파일 | 라인 | 역할 |
|------|------|------|
| `backend/app/routes/admin.py` | L1661-1815 | **수정 대상** — `get_pending_tasks()` |
| `backend/app/models/task_detail.py` | L384-419 | 참고 — `start_task()`가 worker_id 미세팅 |
| `backend/app/routes/work.py` | L588-608 | 참고 — VIEW의 정상 쿼리 (work_start_log 사용) |
| `frontend/lib/screens/admin/admin_options_screen.dart` | L557-570 | FE Admin pending tasks 호출 |
| `frontend/lib/screens/manager/manager_pending_tasks_screen.dart` | L35-37 | FE Manager pending tasks 호출 |

### BUG-43 관련 코드
| 파일 | 역할 |
|------|------|
| `backend/app/routes/analytics.py` | `_ENDPOINT_LABELS` dict — 수정 완료 |

---

## 6. DB 구조 참고

### 작업 추적 테이블 관계
```
app_task_details (작업 정의)
  ├── worker_id: 대부분 NULL (정상) — SINGLE_ACTION 완료 시에만 세팅
  ├── started_at: 첫 작업자 시작 시 UPDATE
  └── completed_at: 모든 작업자 완료 시 UPDATE

work_start_log (작업 시작 로그) ← 실제 작업자 추적
  ├── worker_id: 시작한 작업자 ID (NOT NULL)
  ├── serial_number, task_id, task_category: 작업 식별
  └── started_at: 개별 작업자의 시작 시각

work_completion_log (작업 완료 로그)
  ├── worker_id: 완료한 작업자 ID
  └── completed_at, duration_minutes
```

### 회사-카테고리 매핑 (Python)
```python
COMPANY_CATEGORIES = {
    'C&A': ['ELEC'],
    'P&S': ['ELEC'],
    # ... Manager company → 허용 task_category 매핑
}
```

---

## 7. 새 세션에서 이어가기

BUG-44 수정만 남은 경우:
> "HANDOVER_BUG44.md 읽고 BUG-44 코드 수정 진행해줘"

전체 컨텍스트 필요한 경우:
> "HANDOVER_FULL.md 읽고 이어서 진행해줘"
