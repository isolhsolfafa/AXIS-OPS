# AXIS-OPS Handoff

> 세션 종료 시 업데이트. 다음 세션이 즉시 작업을 이어갈 수 있도록 현재 상태를 기록합니다.
> 마지막 업데이트: 2026-04-20

---

## 현재 버전

- **OPS BE**: v2.9.10
- **OPS FE (Flutter PWA)**: v2.9.10 (version 파일만 bump, OPS FE 코드 변경 0 — Netlify 배포 skip 가능)
- **최근 Sprint**: FIX-25 v4 (progress API에 partner/line 4필드 노출) — ✅ BE 구현 완료, VIEW FE-20/FE-21 착수 대기
- **최근 완료 Sprint**: FIX-25 v4, FIX-24, HOTFIX-04, HOTFIX-05, HOTFIX-03, HOTFIX-02, BUG-45, 61-BE-B, 61-BE, BUG-43/44, HOTFIX-01, 60-BE, 59-BE, 58-BE
- **최근 Migration**: 049 (alert_escalation_expansion)
- **체크리스트 현황**: TM 완료 (SINGLE/DUAL qr_doc_id 정규화) / ELEC 완료 (Phase 1+2, 마스터 정규화) / MECH 미구현
- **RULE-01**: Sprint 완료 시 FE flutter build web + Netlify 배포 필수

---

## 직전 세션 작업 내용 (2026-04-20)

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
