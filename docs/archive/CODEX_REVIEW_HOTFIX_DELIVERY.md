# Codex 교차검증 프롬프트 — HOTFIX-ALERT-SCHEDULER-DELIVERY-20260422

> **AI 검증 워크플로우 v2 ③ 단계** — Claude Cowork 에서 `/codex:review` 호출용
> **작성**: 2026-04-22 15:00 KST
> **자동 이관 사유**: CLAUDE.md L138 "3개 이상 파일 touch" (6 파일) + L140 "의심 시 포함"
> **라운드 상한**: 1회 (핑퐁 방지, 침묵 승인 시 자동 재질문)
> **라벨 요청**: M(Must fix) / A(Advisory) 구분 필수

---

## 📋 Codex 검증 요청 프롬프트 (아래 블록을 Claude Cowork 에 그대로 붙여넣기)

```
# Codex 독립 검증 요청 — HOTFIX-ALERT-SCHEDULER-DELIVERY-20260422

당신은 AXIS-OPS 프로젝트의 교차 검증자입니다. 아래 HOTFIX Sprint 설계를
독립적으로 검토하고 M(Must fix) / A(Advisory) 라벨로 지적해주세요.

## 배경 요약

AXIS-OPS 는 제조 현장 작업 관리 시스템 (Flask + PostgreSQL + Flutter PWA).
2026-04-17~22 5일간 `app_alert_logs` INSERT 0건 장애 발생 → 근본 원인 3개 발견 및
단계적 복구 중. 현재 Phase 5 (alert delivery 실패).

**이전 복구 완료**:
- HOTFIX-ALERT-SCHEMA-RESTORE (11:25 KST) — migration 049 수동 SQL 복구
- HOTFIX-SCHEDULER-DUP (commit f1af8a4) — fcntl file lock 기반 스케줄러 단일 실행
- 위 2건으로 INSERT 는 복구됨. BUT FE delivery 여전히 실패.

**새 발견 (본 Sprint 대상)**:
- `app_alert_logs.target_role='TMS'` 52건 전부 read=0% (완전 undelivered)
- 원인: `role_enum` 허용값은 MECH/ELEC/TM/PI/QI/SI/ADMIN/PM 이고 `TMS` 없음
- `scheduler_service.py` 3곳 (L884/L967/L1044) 이 `target_worker_id` 없이
  `target_role` 만 지정 → `emit_process_alert()` → `role_TMS` room broadcast →
  FE 는 해당 room 구독 안 함 → 완전 실패

**표준 패턴** (task_service.py L571-591):
  managers = get_managers_by_partner(serial_number, target_source)
  for manager_id in managers:
      create_alert(..., target_worker_id=manager_id, target_role=label)

## 설계 핵심 (검증 대상)

### 수정 대상
단일 파일 `backend/app/services/scheduler_service.py` 3곳:

1. **L884** `check_orphan_relay_tasks_job` (RELAY_ORPHAN)
   - 현재: target_role = orphan['task_category']  ('TMS' 포함)
   - 수정: managers 루프 + target_worker_id=manager_id

2. **L967** `_check_not_started_tasks` (TASK_NOT_STARTED, Sprint 61-BE 신규)
   - 동일 패턴

3. **L1044** `_check_checklist_done_task_open` (CHECKLIST_DONE_TASK_OPEN, Sprint 61-BE 신규)
   - target_role='ELEC' hardcoded, target_worker_id 미지정

### 신규 헬퍼 함수 (DRY 원칙)

  _CATEGORY_PARTNER_FIELD = {
      'TMS':  'module_outsourcing',
      'MECH': 'mech_partner',
      'ELEC': 'elec_partner',
  }

  def _resolve_managers_for_category(serial_number, category):
      from app.services.process_validator import get_managers_by_partner, get_managers_for_role
      if category in _CATEGORY_PARTNER_FIELD:
          return get_managers_by_partner(serial_number, _CATEGORY_PARTNER_FIELD[category])
      return get_managers_for_role(category)  # PI / QI / SI

### 변경 범위
- +18~25 LOC / -3 LOC (단일 파일)
- 함수 시그니처 무변경
- migration 없음
- task_service.py / alert_service.py / alert_log.py / __init__.py 무변경

### 배포
- v2.9.10 → v2.9.11 PATCH bump (2026-04-22 HOTFIX 4종 일괄 정리)
- Netlify skip (BE only)
- S2 HOTFIX — Opus 단독 리뷰 → 배포 → 7일 이내 사후 Codex 재검토

## 관련 원칙 원문 인용 (CLAUDE.md)

### § 🚨 긴급 HOTFIX 예외 조항 (L153-163)
> S2 🟠 | 부분 장애 | Opus 단독 리뷰 → 배포 | 7일 이내 또는 다음 Sprint 시작 전
> 중 이른 시점 Codex 검토 필수 + BACKLOG `POST-REVIEW-{HOTFIX-ID}` 등록

### § 📏 코드 크기 (L483-510)
> scheduler_service.py 현재 ~1050 LOC → 1단계 "필수 분할" 800줄 초과
> ⛔ God File 1200줄 임계 근접 → 본 Sprint 완료 후 REFACTOR-SCHEDULER-SPLIT BACKLOG 등록 필요 여부?

### § 🔄 DRY (L524-)
> Rule of Three — 3곳 공통 로직이면 헬퍼 추출 필수
> 본 Sprint 는 3곳 동일 패턴 → _resolve_managers_for_category 헬퍼로 추출 ✅

### § 🛡️ Scope 엄수 (L586 L2 "기능 변경 금지")
> 리팩토링 Sprint 7원칙은 본 Sprint 적용 안 함 (HOTFIX = 장애 복구, 기능 수정 포함 가능)
> 하지만 "작은 단위", "기존 동작 보존" 정신은 유지

## 검증 요청 항목 (M/A 라벨로 응답)

1. **[M1 후보] 과도 broadcast 리스크**
   - TMS task orphan → 현재 수정안은 TMS(M) company 관리자 전체에게 알람
   - 하지만 get_managers_by_partner 가 TMS(M) managers 3명 (이성균, 이선만, tms(m)test)
     리스트 반환 → 3명 모두 동일 알람 수신 → DB 에 3배 기록
   - 이전 버그 (undelivered) 대비 개선이지만, "의도된 1개 대상만 수신" 설계 관점에선 과도
   - **판단 요청**: 이게 Advisory (수용 가능) 인지, Must (get_managers_by_partner 대신
     타겟 1명만 고르는 로직 추가 필요) 인지?

2. **[M2 후보] 기존 52건 legacy 처리**
   - `target_role='TMS'` 로 INSERT 된 52건은 여전히 FE 에 도달 안 함
   - 수정 후에도 legacy 는 그대로 — 관리자들이 "과거 5일치 알람을 놓친 채" 상태
   - **판단 요청**: 본 Sprint 에서 legacy 복구 (target_worker_id 로 복제 INSERT) 를
     포함해야 하는지, 아니면 별도 BACKLOG (FIX-LEGACY-ALERT-TMS-DELIVERY) 로 분리?
   - 제안: 분리 (과거 알람이라 대부분 skip 가능 + 수정 범위 분할이 원칙상 바람직)

3. **[M3 후보] _check_not_started_tasks 의 category='PI' 경로 검증**
   - get_managers_for_role('PI') 는 role='PI' AND is_manager=TRUE workers 반환
   - 하지만 role_enum 에 PI 있음 + workers 테이블에 PI manager 5명 존재 → OK
   - QI/SI 동일
   - **판단 요청**: 검증 안전성 확인. 엣지케이스 있는가?

4. **[A 후보] scheduler_service.py 크기 (~1050 LOC)**
   - CLAUDE.md 코드 크기 1단계 "필수 분할 800줄" 초과 + "God File 1200줄" 근접
   - 본 Sprint +18 LOC 는 임계 영향 거의 없음
   - 별도 `REFACTOR-SCHEDULER-SPLIT` BACKLOG 등록 필요성?

5. **[A 후보] Sentry/로깅 정합성**
   - 수정 후에도 Phase 1.5 의 [alert_silent_fail] / [alert_create_none] /
     [alert_insert_fail] prefix 로깅은 그대로 작동
   - 수정 범위가 alert_service / alert_log 아니라 scheduler_service 만이므로 영향 없음
   - 확인 요청

6. **[A 후보] 테스트 커버리지**
   - test_alert_all20_verify.py TC-AL20-07~08 (RELAY_ORPHAN) 가 서비스 직접 호출
     방식이라 DB INSERT 만 검증하고 FE delivery 검증은 없음
   - 기존 테스트가 GREEN 이면서도 운영에서는 undelivered 였던 것이 이 때문
   - **판단 요청**: 본 Sprint 에 delivery 통합 테스트 (worker room 구독 → emit → 수신) 추가 필요?
   - 제안: 별도 BACKLOG (TEST-ALERT-DELIVERY-E2E) — 통합 테스트 infra 필요

7. **[A 후보] 버전 bump 소급 (v2.9.11)**
   - 2026-04-22 HOTFIX 4종 (PHASE1.5 / SCHEMA-RESTORE / DUP / DELIVERY) 일괄 정리
   - 4건 모두 PATCH 수준 (기능 추가 아닌 버그 수정 + 관찰 로깅)
   - CLAUDE.md L1369: PATCH = "HOTFIX, 버그 수정, 기능 변경 없음"
   - 본 HOTFIX 는 "delivery 복구" 라 기능 변경? 아니면 "의도된 동작 복구" 라 버그 수정?
   - **판단 요청**: v2.9.11 타당한지, 아니면 v2.10.0 MINOR 올려야 하는지?

## 응답 형식 요청

각 항목에 대해:
- 라벨: M(Must, 배포 블로커) / A(Advisory, BACKLOG 등록 후 진행 가능)
- 이유: 구체적 증거 기반 (코드 경로, DB schema, 사용자 영향 등)
- 수정 제안: 구체적 action (대안 코드 / BACKLOG 제목 / 추가 검증)

CLAUDE.md AI 검증 워크플로우 L98-103:
"침묵 승인 거부: Codex 가 구체성 없는 OK 응답 시 자동 재질문"
→ "LGTM" / "문제 없음" 류 답변 금지. 각 항목에 구체적 검토 내용 기입.
```

---

## 🔗 첨부 자료 (Codex 에 함께 제공)

### 실측 데이터

```
Q7 — target_role 분포 (역사 전체):
  MECH   118건 read 75.4%  🟢 정상
  ELEC   117건 read 38.5%  🟡 일부 지연
  TMS     52건 read  0.0%  🔴 완전 undelivered (role_enum 없음)
  QI      16건 read  0.0%  🟠 관리자 미접속 (별건)
  elec_partner   8건 read 50%    🟡 column name 오용
  mech_partner   6건 read  0%
  module_outsourcing 3건 read 66.7%

Q5 — role_enum 허용값:
  ['MECH', 'ELEC', 'TM', 'PI', 'QI', 'SI', 'ADMIN', 'PM']
  'TMS' 포함 여부: False
```

### FE WebSocket 구독 로그
```
WS registered: ws_id=ef4369fb, worker_id=4477, role=MECH,
  rooms={'worker_4477', 'role_MECH'}
```

### 표준 패턴 reference (task_service.py L571-591)
```python
managers = get_managers_by_partner(task.serial_number, target_source)
for manager_id in managers:
    alert_id = create_alert(
        alert_type=alert_type,
        message=...,
        serial_number=task.serial_number,
        qr_doc_id=task.qr_doc_id,
        triggered_by_worker_id=task.worker_id,
        target_worker_id=manager_id,    # 🎯 개별 지정
        target_role=target_role_label   # 라벨용
    )
```

---

## 📝 사용자 액션

1. `AXIS-OPS/CODEX_REVIEW_HOTFIX_DELIVERY.md` 파일 참조
2. Claude Cowork (또는 `/codex:review`) 에 위 "📋 Codex 검증 요청 프롬프트" 블록 복사
3. Codex 응답을 이 세션에 공유
4. M 지적은 구현 전 해결, A 지적은 BACKLOG 등록
5. M 전부 해결 후 "진행해" 라고 말씀해주시면 구현 착수
