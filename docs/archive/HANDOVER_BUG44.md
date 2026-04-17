# BUG-44 인수인계: OPS 미종료 작업 목록 0건 반환

**작성일**: 2026-04-17
**최종 업데이트**: 2026-04-17 (코드 적용 완료)
**상태**: ✅ 코드 적용 완료 — `admin.py` L1705-1741 반영. Sprint 61-BE-B(#60/#61) / HOTFIX 후속 진행 상태는 `HANDOVER_FULL.md` 참조
**버전**: v2.9.5

---

## 1. 문제 요약

OPS(Flutter PWA)의 "미종료 작업" 화면이 Admin/Manager 양쪽 모두 0건을 반환한다.
VIEW(React)에서는 동일 S/N의 진행 중 작업이 정상 표시됨.

## 2. 근본 원인

**파일**: `backend/app/routes/admin.py` — `get_pending_tasks()` L1705-1731

```sql
-- 문제 쿼리 (L1721)
FROM app_task_details t
JOIN workers w ON t.worker_id = w.id   -- ← INNER JOIN
```

- `app_task_details.worker_id`는 정상적으로 **전부 NULL**
- `start_task()` (task_detail.py L384-419)는 `started_at`만 UPDATE, `worker_id`는 세팅 안 함
- 작업자 추적은 `work_start_log` 테이블에서 별도 관리
- `NULL = w.id`는 항상 FALSE → INNER JOIN 매칭 0건

**VIEW가 정상인 이유**: work.py L588-608에서 `work_start_log wsl JOIN workers w ON wsl.worker_id = w.id` 사용

## 3. 수정 대상

### 파일: `backend/app/routes/admin.py`

### 위치: `get_pending_tasks()` L1705-1731 (진행 중 쿼리)

**현재 코드** (L1705-1731):
```sql
SELECT
    t.id,
    t.worker_id,
    w.name AS worker_name,
    t.serial_number,
    t.qr_doc_id,
    t.task_category,
    t.task_id,
    t.task_name,
    t.started_at,
    EXTRACT(EPOCH FROM (NOW() - t.started_at)) / 60 AS elapsed_minutes,
    pi.sales_order,
    'in_progress' AS status
FROM app_task_details t
JOIN workers w ON t.worker_id = w.id
LEFT JOIN plan.product_info pi ON pi.serial_number = t.serial_number
WHERE t.started_at IS NOT NULL
  AND t.completed_at IS NULL
  AND t.is_applicable = TRUE
  AND t.force_closed = FALSE
  AND (w.company = %s OR %s IS NULL)
ORDER BY t.started_at ASC
```

**수정 후**:
```sql
SELECT
    t.id,
    wsl.worker_id,
    w.name AS worker_name,
    t.serial_number,
    t.qr_doc_id,
    t.task_category,
    t.task_id,
    t.task_name,
    t.started_at,
    EXTRACT(EPOCH FROM (NOW() - t.started_at)) / 60 AS elapsed_minutes,
    pi.sales_order,
    'in_progress' AS status
FROM app_task_details t
LEFT JOIN LATERAL (
    SELECT wsl2.worker_id
    FROM work_start_log wsl2
    WHERE wsl2.task_id = t.id          -- FK 매칭 (work_start_log.task_id → app_task_details.id)
    ORDER BY wsl2.started_at DESC
    LIMIT 1
) wsl ON TRUE
LEFT JOIN workers w ON wsl.worker_id = w.id
LEFT JOIN plan.product_info pi ON pi.serial_number = t.serial_number
WHERE t.started_at IS NOT NULL
  AND t.completed_at IS NULL
  AND t.is_applicable = TRUE
  AND t.force_closed = FALSE
  AND (w.company = %s OR %s IS NULL)   -- 유지: work_start_log 작업자의 company로 필터
ORDER BY t.started_at ASC
```

### 교차 검증 합의 포인트 (Claude × Codex)

- `wsl2.task_id = t.id` — FK 매칭 (DDL: `REFERENCES app_task_details(id)`). 3컬럼 매칭보다 정확
- `wsl2.task_id_ref = t.task_id` 단독 사용 금지 — VARCHAR로 S/N 간 중복 가능 (unsafe)
- `AND (w.company = %s OR %s IS NULL)` **유지** — 제거 시 FNI/BAT 모두 MECH라 타사 작업 노출 (Codex 발견)
- 파라미터 바인딩 `(company, company)` 그대로 유지
- Manager company 필터링은 이미 L1776-1777의 Python `COMPANY_CATEGORIES` 필터로 처리됨:
  ```python
  if allowed_categories:
      all_rows = [r for r in all_rows if r['task_category'] in allowed_categories]
  ```

### 미시작 쿼리 (L1737-1766): 변경 없음

이미 `workers` 테이블을 JOIN하지 않으므로 영향 없음.

## 4. 검증 방법

수정 후 확인사항:
1. Admin 계정으로 `/admin/tasks/pending` 호출 → tasks 배열에 진행 중 작업 반환 확인
2. Manager(C&A) 계정으로 `/admin/tasks/pending?company=C%26A` 호출 → C&A 카테고리 작업만 반환 확인
3. OPS 앱 "미종료 작업" 화면에서 목록 표시 확인
4. VIEW와 OPS 건수 일치 확인

## 5. 관련 파일 목록

| 파일 | 역할 |
|------|------|
| `backend/app/routes/admin.py` L1661-1815 | **수정 대상** — `get_pending_tasks()` |
| `backend/app/models/task_detail.py` L384-419 | 참고 — `start_task()`가 worker_id 미세팅 확인 |
| `backend/app/routes/work.py` L588-608 | 참고 — VIEW의 정상 쿼리 패턴 (work_start_log 사용) |
| `frontend/lib/screens/admin/admin_options_screen.dart` L557-570 | FE — Admin pending tasks 호출 |
| `frontend/lib/screens/manager/manager_pending_tasks_screen.dart` L35-37 | FE — Manager pending tasks 호출 |
| `AGENT_TEAM_LAUNCH.md` 마지막 섹션 "BUG-44" | 설계서 (이미 작성 완료) |
| `BACKLOG.md` BUG-44 행 + 상세 섹션 | 백로그 (이미 업데이트 완료) |

## 6. 이 세션에서 완료된 작업

- ✅ Sprint 61-BE 설계 보정 10건 (M1-M6, A1-A3, 추가 M1 1-2b)
- ✅ CLAUDE.md AI 검증 워크플로우 추가 (AXIS-OPS + AXIS-VIEW)
- ✅ BUG-43 수정 (analytics.py 24개 한글 라벨 추가)
- ✅ BUG-44 원인 규명 + 설계서 작성
- ✅ BUG-44 코드 적용 완료 (`admin.py` L1705-1741, FK LATERAL JOIN, company 필터 유지)
- ✅ Sprint 61-BE-B 완료 (v2.9.5) — #60 `company` / #61 `force_closed` 필드 추가 (admin.py + work.py)
- ✅ HOTFIX `force_close_task()` + `force_complete_task()` TypeError — **pytest 29/29 passed** (완료)
  - 실제 구현은 설계 범위 초과: `completed_at`(진짜 원인) + `started_at` 양쪽 naive→KST aware 정규화
  - `force_close_task()` L1170-1200 + `force_complete_task()` L897-960 2곳 모두 적용

## 7. 후속 진행 상황 (HANDOVER_FULL.md 우선)

- ⏳ RULE-01: `flutter build web --release` + Netlify 재배포 (v2.9.5 릴리즈)
- ⏳ VIEW Sprint 33 FE-15 (SNDetailPanel 강제종료 UI) — BE 선행 2건(#60/#61) 완료로 착수 가능
- 🔴 BUG-42: QR 스캐너 접사 인식 실패 (BACKLOG.md 등록, 미착수)

> 본 문서는 BUG-44 전용 기록이며, 이후 세션 이어받기는 **`HANDOVER_FULL.md` 우선**.
