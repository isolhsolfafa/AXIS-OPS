# Sprint: Worker별 Pause/Resume — 다중작업자 개인별 작업시간 추적

> 등록일: 2026-04-07
> 우선순위: 높음 (CT 분석 정확도 + 현장 운영 정합성)
> 선행: Sprint 9 (pause/resume), Sprint 15 (다중작업자 Join), BUG-6 (coworker resume)

---

## 1. 문제 정의

### 현재 구조 (task 단위 pause)

```
app_task_details.is_paused = TRUE/FALSE  ← task 전체 1개 플래그
work_pause_log.worker_id                 ← 누가 눌렀는지만 기록
```

A가 pause → **task 전체 멈춤** → B도 작업 불가 표시
B가 resume → **task 전체 재개** → A의 실제 쉬는 시간 추적 불가

### 발생하는 문제

| 문제 | 영향 |
|------|------|
| A pause 시 B도 멈춤 표시 | FE에서 B가 작업 중인데 paused 표시 |
| B가 A의 pause를 resume | A의 pause_duration이 B 기준으로 계산 |
| 개인별 순수작업시간 산출 불가 | CT 분석 부정확 (공수 오차 최대 N-1배) |
| 5명 task에서 1명 pause → 5명분 차감 | 공수 과다 산출 |

### 실제 데이터 (GBWS-6920)

```
task 81 (Waste Gas LINE 1): 3명 — 권민수, 윤춘국, 박동길
task 82 (Util LINE 1):      5명 — 황진충, 서정원, 유승민, 임지후, 손국권
task 85 (Waste Gas LINE 2): 4명 — 황진충, 유승민, 임지후, 서정원
```

서정원 1명 pause → task 82 전체 5명 paused 표시 → 실제로 4명은 작업 중

---

## 2. 목표 구조 (worker별 pause)

```
app_task_details.is_paused      → 전원 paused일 때만 true (또는 제거)
work_pause_log.worker_id        → 개인별 pause 상태
FE: worker별 pause/resume 버튼   → 본인만 pause/resume
```

### 동작 변경

| 시나리오 | 현재 | 변경 후 |
|---------|------|--------|
| A pause | task 전체 paused | A만 paused, B는 working |
| B resume | task 전체 재개 (A의 pause 종료) | B는 이미 working, A만 paused 유지 |
| A resume | A 본인 재개 | A 재개 |
| A+B 둘 다 pause | task paused | task.is_paused = true (전원 paused) |

### 결과값 차이

```
시나리오: A, B 동시 시작 09:00, A만 10:00~10:30 pause, 둘 다 12:00 완료

현재:  공수 = (180-30) × 2 = 300 man-min (부정확)
변경후: 공수 = 150(A) + 180(B) = 330 man-min (정확)
오차: 30분 / 330분 = 9%

5명 task 시: 오차 최대 (N-1)/N = 80%
```

---

## 3. 수정 범위

### BE (4파일)

```
1. backend/app/routes/work.py
   - pause: task.is_paused 대신 worker별 pause 상태 관리
   - resume: 본인 pause만 resume (coworker resume 제거)
   - 응답에 my_pause_status 추가

2. backend/app/services/task_service.py
   - complete_work: 개인별 pause 자동 resume 후 완료
   - _calculate_working_minutes: worker별 pause_duration 합산

3. backend/app/models/work_pause_log.py
   - get_active_pause(task_id) → get_active_pause(task_id, worker_id)
   - get_my_pause_status(task_id, worker_id) 신규

4. backend/app/models/task_detail.py
   - is_paused 판정: 전원 paused일 때만 true (또는 참여 중 worker 기준)
```

### FE (2파일)

```
1. frontend/lib/screens/task/task_detail_screen.dart
   - pause/resume 버튼: task.is_paused → my_pause_status 기준
   - 다중작업자 시 "A: 일시정지 / B: 작업중" 개별 표시

2. frontend/lib/models/task_item.dart
   - myPauseStatus 필드 추가
```

### DB 변경: 없음
- work_pause_log 스키마 변경 불필요 (이미 worker_id 컬럼 존재)
- app_task_details.is_paused는 유지 (전원 paused 여부로 의미 변경)

---

## 4. 하위호환

| 항목 | 영향 |
|------|------|
| 단독작업자 (1인) | 기존과 동일 (본인 pause = task pause) |
| FE 미업데이트 | task.is_paused 기준으로 동작 (전원 pause 시만 표시) |
| 기존 work_pause_log 데이터 | 그대로 유지 (worker_id 이미 존재) |
| scheduler 자동 pause (휴게시간) | 참여 중인 전원에게 각각 pause 기록 |

---

## 5. CT 분석 연동

worker별 pause가 구현되면 CT 분석에서:

```sql
-- 작업자별 순수작업시간
SELECT wsl.worker_id,
       EXTRACT(EPOCH FROM (wcl.completed_at - wsl.started_at)) / 60
       - COALESCE(SUM(wpl.pause_duration_minutes), 0) AS net_minutes
FROM work_start_log wsl
JOIN work_completion_log wcl ON wsl.task_id = wcl.task_id AND wsl.worker_id = wcl.worker_id
LEFT JOIN work_pause_log wpl ON wpl.task_detail_id = wsl.task_id AND wpl.worker_id = wsl.worker_id
WHERE wsl.task_id = %s
GROUP BY wsl.worker_id, wsl.started_at, wcl.completed_at
```

→ 개인별 정확한 공수 산출 가능

---

## 6. 테스트 케이스

```
[worker별 pause 기본]
TC-WP-01: A pause → A만 paused, B는 working 표시
TC-WP-02: A pause → A resume → A working
TC-WP-03: A pause → B는 resume 불가 (본인만 resume)
TC-WP-04: A pause + B pause → task.is_paused = true
TC-WP-05: A resume (B는 여전히 paused) → task.is_paused = true 유지

[작업시간 정확도]
TC-WP-06: A 30분 pause, B pause 없음 → A 순수시간 = 전체-30, B = 전체
TC-WP-07: 5명 중 1명 pause → 1명분만 차감 (4명 영향 없음)

[complete 연동]
TC-WP-08: A paused 상태에서 A complete → auto resume 후 complete
TC-WP-09: A paused, B complete → B만 완료, A는 여전히 paused

[scheduler 자동 pause]
TC-WP-10: 휴게시간 → 참여 중인 전원 각각 pause 기록
TC-WP-11: 휴게시간 종료 → 전원 각각 resume
```

---

## 7. 착수 조건

- [x] BUG-6 수정 완료 (coworker resume 허용 — 임시 조치)
- [x] 다중작업자 현장 데이터 확보 (task 81/82/85/89/91)
- [ ] FE pause/resume UI 변경 설계 확정
- [ ] scheduler 자동 pause 변경 범위 확정
- [ ] CT 분석 Sprint과 우선순위 조율
