# AXIS-OPS 작업 Flow 시나리오 검토

> 마지막 업데이트: 2026-03-01
> 다중 작업자 Task 완료 흐름 + 알람 시스템 빈틈 분석

---

## 현재 다중 작업자 Task 구조

### DB 테이블 관계

```
app_task_details (메인)
  ├─ worker_id        ← 첫 번째 작업자만 기록
  ├─ started_at       ← 첫 번째 작업자 시작 시각
  ├─ completed_at     ← 마지막 작업자 완료 시각
  ├─ duration_minutes ← 전체 합산 (공수)
  ├─ elapsed_minutes  ← 경과 시간 (벽시계)
  └─ worker_count     ← 참여 작업자 수

work_start_log (작업자별 시작)
  ├─ worker_id + started_at (작업자별 1건)

work_completion_log (작업자별 완료)
  ├─ worker_id + completed_at + duration_minutes (작업자별 1건)
```

### 완료 판정 조건

```python
# _all_workers_completed()
started_count = COUNT(work_start_log WHERE task_id)
completed_count = COUNT(work_completion_log WHERE task_id)
return completed_count >= started_count  # 전원 완료해야 TRUE
```

---

## 정상 시나리오: UTIL LINE1 (A, B, C 3명)

```
10:00  A 시작 → work_start_log (A, 10:00) + app_task_details.started_at = 10:00
10:05  B 시작 → work_start_log (B, 10:05)
10:10  C 시작 → work_start_log (C, 10:10)
10:30  A 종료 → work_completion_log (A, 30분) → all_done? 1/3 = NO
10:35  B 종료 → work_completion_log (B, 30분) → all_done? 2/3 = NO
10:40  C 종료 → work_completion_log (C, 30분) → all_done? 3/3 = YES ✅

→ _finalize_task_multi_worker() 실행:
  duration_minutes = 30 + 30 + 30 = 90분 (공수 합산)
  elapsed_minutes  = 10:40 - 10:00 = 40분 (경과 시간)
  worker_count     = 3

→ category 완료 체크 → completion_status 업데이트
→ _trigger_completion_alerts() → 후속 공정 알림
```

---

## 문제 시나리오

### 시나리오 1: 단일 작업자 종료 누락

```
UTIL LINE1 — A 혼자 작업

10:00  A 시작
...    A 실제 작업 완료, 종료 버튼 안 누름

현재 알람 시스템 반응:
  매시 정각  → TASK_REMINDER → A에게 "N시간 경과, 아직 완료 전"
  17:00     → SHIFT_END_REMINDER → A에게 "미완료 작업 있습니다"
  18:00     → UNFINISHED_AT_CLOSING → MECH 관리자에게 알림
  20:00     → SHIFT_END_REMINDER 2차 → A에게
  익일 09:00 → TASK_ESCALATION → A 소속 회사 관리자에게

결론: 알람은 정상 작동. A 또는 관리자가 인지 가능.
빈틈: 자동 종료 안 됨 → 관리자가 force-close 수동 조치 필요.
```

### 시나리오 2: 3명 중 1명 종료 누락 (핵심 문제)

```
UTIL LINE1 — A, B, C 3명 작업

10:00  A 시작
10:05  B 시작
10:10  C 시작
10:30  A 종료 ✅
10:35  B 종료 ✅
...    C 종료 안 누름 ❌

→ _all_workers_completed() = (2 >= 3) = FALSE
→ Task는 영원히 "진행 중" 상태로 고착

현재 알람 시스템 반응:
  매시 정각  → TASK_REMINDER → 누구에게? ⚠️
             app_task_details.worker_id = A (첫 번째)
             → A에게 리마인더가 감 (A는 이미 종료했는데!)
  17:00     → SHIFT_END_REMINDER → 동일 문제 (A에게 감)
  익일 09:00 → TASK_ESCALATION → "작업자: A" 로 표시

빈틈 ①: 실제 미종료자 C에게 알람이 안 감
빈틈 ②: 관리자는 A가 문제인 줄 알고 A에게 연락
빈틈 ③: C가 누군지 알려면 DB 직접 조회해야 함
```

### 시나리오 3: 종료 누락 → 공정 체인 차단

```
SN-001 제품 공정 흐름:

TMS 가압검사 완료 ─────→ [TMS_TANK_COMPLETE] → MECH 관리자 알림
                              │
MECH TANK_DOCKING ←── MECH 팀 시작
  ├─ A 시작, A 종료 ✅
  ├─ B 시작, B 종료 ✅
  └─ C 시작, C 미종료 ❌
                              │
      TANK_DOCKING.completed_at = NULL (미완료)
                              │
      ├─ [TANK_DOCKING_COMPLETE] 알림 발송 안 됨 → ELEC 모름
      ├─ phase_block 켜져있으면 → MECH 후속 task (WASTE_GAS_LINE_2 등) 차단
      └─ ELEC 시작 시도 → PROCESS_READY 알림만 발생 (MECH 미완료)

결론: 1명의 종료 누락 → 전체 생산 라인 정체
```

### 시나리오 4: Phase Block OFF 일 때

```
phase_block_enabled = FALSE (현재 설정)

MECH TANK_DOCKING 미완료 상태에서도:
  → MECH 후속 task (WASTE_GAS_LINE_2 등) 시작 가능
  → ELEC 작업도 시작 가능 (차단 없음)
  → 단, PI/QI/SI 시작 시 PROCESS_READY 알림은 발생

빈틈: 공정 순서 무시 가능 → 품질 이슈 발생 위험
장점: 1명 미종료로 전체 차단되는 것은 방지
```

---

## 빈틈 요약

| # | 빈틈 | 영향 | 심각도 |
|---|------|------|--------|
| 1 | 미완료 작업자 특정 불가 | 에스컬레이션이 첫 번째 작업자만 표시, 실제 미종료자 C를 모름 | 🔴 높음 |
| 2 | 개별 작업자 리마인더 없음 | 시작했지만 종료 안 한 작업자 개인에게 알람 안 감 | 🔴 높음 |
| 3 | 1명 미종료 → 공정 체인 차단 | phase_block ON이면 전체 생산 라인 정체 | 🔴 높음 |
| 4 | 자동 종료 메커니즘 없음 | N일 경과해도 자동 force-close 안 됨 | 🟡 중간 |
| 5 | Task Detail 화면에 작업자별 상태 없음 | 누가 참여했고 누가 미종료인지 FE에서 확인 불가 | 🟡 중간 |
| 6 | 관리자 대시보드 부재 | 미종료 작업자 현황을 한눈에 볼 수 없음 | 🟡 중간 |

---

## 개선 제안

### 제안 1: 미완료 작업자 개별 알람 (빈틈 #1, #2 해결)

**로직**:
```sql
-- 시작했지만 완료 안 한 작업자 조회
SELECT wsl.worker_id, wsl.started_at, w.name
FROM work_start_log wsl
JOIN workers w ON wsl.worker_id = w.id
LEFT JOIN work_completion_log wcl
  ON wsl.task_id = wcl.task_id AND wsl.worker_id = wcl.worker_id
WHERE wsl.task_id = %s AND wcl.id IS NULL
```

**적용 위치**: `scheduler_service.py` — TASK_REMINDER, SHIFT_END_REMINDER, TASK_ESCALATION 모두

**변경 내용**:
- 리마인더: 미완료 작업자 각각에게 개별 알림
- 에스컬레이션 메시지: `"작업자: A(✅), B(✅), C(❌미완료)"` 형태

### 제안 2: 에스컬레이션 메시지 개선 (빈틈 #1 해결)

**현재**: `"작업자: A (FNI)"` ← 첫 번째 작업자만
**개선**: `"[에스컬레이션] UTIL LINE1 — 참여 3명: A(✅완료), B(✅완료), C(❌미완료). C에게 종료 확인 필요"`

### 제안 3: 자동 Force Close (빈틈 #3, #4 해결)

**방식**: `admin_settings`에 `auto_force_close_hours` 추가 (기본값: 24시간)

**로직**:
```
스케줄러 매시 체크:
  started_at + auto_force_close_hours < NOW()
  AND completed_at IS NULL
  → 자동 force_close + 관리자 알림
  → close_reason = "자동 종료 (24시간 초과)"
```

**효과**: 1명 미종료로 인한 공정 체인 차단 방지

### 제안 4: Task Detail API + FE 작업자별 표시 (빈틈 #5 해결)

**BE**: task detail API에 작업자 리스트 추가
```json
{
  "workers": [
    {"name": "A", "started_at": "10:00", "completed_at": "10:30", "duration": 30, "status": "completed"},
    {"name": "B", "started_at": "10:05", "completed_at": "10:35", "duration": 30, "status": "completed"},
    {"name": "C", "started_at": "10:10", "completed_at": null, "duration": null, "status": "in_progress"}
  ]
}
```

**FE**: 작업 시간 섹션 위에 작업자별 상태 카드 표시

### 제안 5: Phase Block + 예외 처리 (빈틈 #3 보완)

**Phase Block ON + 미종료 작업자 존재 시**:
- 자동 force-close 또는 관리자 수동 종료로 차단 해제
- 관리자에게 "TANK_DOCKING 차단 중 — C 미종료" 전용 알림 추가

---

## 구현 우선순위 (제안)

| 순위 | 제안 | 이유 |
|------|------|------|
| 1 | 제안 1: 미완료 작업자 개별 알람 | 가장 시급 — 현재 알람이 엉뚱한 사람에게 감 |
| 2 | 제안 2: 에스컬레이션 메시지 개선 | 제안 1과 함께 수정 가능 (같은 로직) |
| 3 | 제안 4: Task Detail 작업자별 표시 | 관리자가 현황 파악 가능 (FE+BE) |
| 4 | 제안 3: 자동 Force Close | 공정 차단 방지 (정책 결정 필요) |
| 5 | 제안 5: Phase Block 예외 처리 | Phase Block 활성화 후 필요 |

---

## 관련 소스 파일

| 파일 | 역할 |
|------|------|
| `backend/app/services/task_service.py` | complete_work, _all_workers_completed, _finalize_task_multi_worker, _trigger_completion_alerts |
| `backend/app/services/scheduler_service.py` | TASK_REMINDER, SHIFT_END, ESCALATION 스케줄러 |
| `backend/app/services/process_validator.py` | PROCESS_READY 선행 공정 검증 |
| `backend/app/routes/admin.py` | force-close 엔드포인트 |
| `backend/app/routes/work.py` | task detail API (_task_to_dict) |
| `frontend/lib/screens/task/task_detail_screen.dart` | Task 상세 화면 |
| `frontend/lib/models/task_item.dart` | TaskItem 모델 (workerName 필드 있음) |
