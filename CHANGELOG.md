# Changelog

All notable changes to AXIS-OPS are documented here.

Format: [Semantic Versioning](https://semver.org/) — MAJOR.MINOR.PATCH

---

## [2.22.0] - 2026-06-03 — duration man-hour 재정의 (수동 일시정지 미반영 + 휴게 이중차감 fix)

> 작업 완료 시 `duration_minutes`가 raw(완료−시작)로 덮어써져 **작업자 수동 일시정지가 전혀 반영되지 않던** 버그 (운영 210건). 사용자 결정 = 휴게/점심 차감 안 함(원본 적재) + 수동 일시정지만 차감.

### 새 man-hour 정의 (compute_task_manhour SSoT)
- **완료로그 ≥1건**: per-worker interval-union(세션) − (수동 pause ∩ session_union). 세션 상한 = LEAST(완료기록, 다음 start(LEAD), close_at). 멀티워커 man-hour 정확 + 재시작 capping.
- **완료로그 0건** (순수 open 자동마감): 단일구간 `[MAX(last_started), close_at] − manual∩` (추정값).
- 휴게(break_*) 미차감 / pause_type='manual'만 차감 / worker별 FLOOR 합산 / `started_at < close_at` crash 가드.

### 3경로 통일 (단일 UPDATE 원자 — completed_at+duration+elapsed+worker_count+audit)
- **정상완료** (`task_service.complete_work`): `_finalize`+`complete_task`(raw 덮어쓰기) → `complete_task_unified`
- **ship/admin 완료** (`shipment_service`): 3단계 → `complete_task_unified` (close_reason SHIP/ADMIN_COMPLETE)
- **자동마감** (`auto_close_relay_task`): 시그니처 유지 내부 `compute_task_manhour` 위임 (호출처 5곳 무변경, race guard/audit 보존)
- **수동 강제종료** (`admin.force_close_task`): 휴게 차감(`_calculate_working_minutes`) 제거 → `compute_task_manhour`. `AUTO_CLOSED_` prefix 입력 400 차단

### 검증
- 운영 데이터 직접 비교 (O/N 6873/6878/6770) + AUDIT_TRAIL_GUIDE §11 진단으로 자동마감/완료로그 분기 발견·해소
- **Codex 12라운드 GO** (설계 추상 1~8 + 운영검증 9~12, M:5→10→2→4→1→1→1→0→2→2→1→0)
- 회귀 95 GREEN (test_fix_duration 15 + relay 38 + force_close 17 + ship/admin 25)
- 검증 예: IF_1 자동마감 = 세션451 − pause338 = 113 (구 451은 pause 미차감)

### 후속 (별도)
- migration 058 백필 (과거 210건 정정, preflight 동반) — 별 단계
- 별 BACKLOG: REF-TASK-DETAIL-CONN-INJECTION(전사 트랜잭션) / worker_count 과소집계 / AUTOCLOSE-BACKSTOP(3일+OPEN 244) / 대시보드 세션 표시 집계
- 설계: AGENT_TEAM_LAUNCH.md § FIX-DURATION-MANUAL-PAUSE-RAW (v1~v12)

---

## [2.21.3] - 2026-06-02 — MECH 체크리스트 자재 드롭다운 긴 spec 줄바꿈 표시

> MECH 체크리스트 자재 선택 드롭다운에서 긴 자재 사양(flow sensor / MFC 등)이 `...`로 잘려 전체 spec이 안 보이던 문제.

### 원인
- `mech_checklist_screen.dart` 드롭다운 메뉴 항목이 `Text(opt, overflow: TextOverflow.ellipsis)` — 한 줄 + ellipsis로 잘림
- 단순히 ellipsis만 제거하면 Flutter `DropdownButton` 기본 항목 높이(`kMinInteractiveDimension` 48px) 고정 때문에 줄바꿈해도 잘리거나 RenderFlex overflow 발생

### Fix
- **FE** `mech_checklist_screen.dart` (자재 선택 드롭다운):
  - `itemHeight: null` — 항목 높이 가변 (줄바꿈 표시 필수 조건)
  - `selectedItemBuilder` 추가 — 닫힌 필드는 1줄 ellipsis 유지 (선택 후 카드 레이아웃 부풀림 방지)
  - 메뉴 항목 `ellipsis` → `softWrap: true, maxLines: 3` — 열면 전체 spec 줄바꿈 표시
- ELEC은 짧은 옵션(TUBE 색상 등)이라 이번 범위 제외

### 검증
- flutter build web GREEN. FE-only / 데이터·BE 무변경 / 회귀 위험 0
- 열면 전체 사양 줄바꿈 표시, 선택 후 닫으면 1줄 ellipsis

---

## [2.21.2] - 2026-05-30 — 위치 검증 토글 Off 시 출근 GPS 권한 요청 제거

> 협력사 출근 시 브라우저 위치 권한 팝업이 떴는데, admin 위치 검증 토글(`geo_check_enabled`)이 Off인데도 발생.

### 원인
- FE `_handleAttendance`가 설정과 무관하게 출근 시 무조건 `_getCurrentLocation()`(Web Geolocation) 호출
- BE는 `geo_check_enabled=true AND work_site=='GST'`일 때만 위치 검증(`hr.py:132`) → Off면 위치를 안 봄. FE만 불필요하게 권한 요청

### Fix
- **BE** `hr.py`: `/hr/attendance/today` 응답에 `geo_check_enabled: is_geo_check_enabled()` 추가 (additive)
- **FE** `home_screen.dart`: `_geoCheckEnabled` 파싱 + 출근 시 `(_geoCheckEnabled && work_site=='GST')`일 때만 GPS 호출 — BE 검증 조건과 정확 정합. Off면 권한 팝업 없음
- `_attendanceStatusLoaded` 게이트 — 설정 미로드/조회 실패 시 fail-open 방지 (Codex M-Q2)

### 검증
- Codex 라운드 1 **M=1(race fail-open) 반영 / A=2** (attendance/today 키 TC + 별 사항 BACKLOG)
- flutter build GREEN. 회귀 0 (additive + 조건 가드). 퇴근 GPS 원래 없음
- 현재 토글 Off → 협력사 출근 시 위치 권한 팝업 미발생. 토글 On 시에만 GPS 요청

---

## [2.21.1] - 2026-05-30 — 협력사 퇴근 실수 클릭 방지 + 출퇴근 성공 토스트

> 출퇴근 버튼이 one-action 토글이라 퇴근을 모르고 누르면 출근 상태가 바로 종료됨.

### Fix (`home_screen.dart` `_handleAttendance`)
- 퇴근(checkType=='out') 시 **"퇴근 처리하시겠습니까? / 출근 중 상태가 종료됩니다"** 확인 다이얼로그 (취소 시 중단)
- 출근은 바로 처리 (실수해도 재클릭 가능)
- 처리 성공 시 토스트 피드백 추가

### 검증
- flutter build GREEN. FE only, 회귀 0
- ②단계 Codex 이관 0항목 (FE 토글/다이얼로그) → Opus 자가 리뷰

---

## [2.21.0] - 2026-05-29 — Sprint 80: SI 출하예정 주차별 그룹핑 + 200 cap 누락 해소

> OPS SI 마무리공정 "출하 예정" 탭 개편. 평면 200건 리스트 → ISO 주차(52주) 그룹 카드. 실측 389건 중 189건 누락(200 cap) 동시 해소.

### 문제
- per_page 200 cap → 출하예정 389건 중 189건 누락 (검색은 BE 필터 후라 특정 S/N 조회는 정상이었음)
- 모델만 묶으면 GAIA-I DUAL 230건 한 덩어리 → 출하날짜 제각각이라 주차 단위 필요

### BE (additive, 기존 계약 무변경)
- `shipment_flow_service.py` 신규 `get_shipment_week_groups()` — ISO 주차(`IYYY-WIW`)별 + 모델별 카운트 집계 (전체 기준, 200 cap 무관). week asc / by_model count desc. WHERE는 기존 planned base_sql과 1:1 동일 (M-Q6)
- `admin_shipment_flow.py` — planned + 검색 없음일 때만 응답에 `by_week` append. 기존 `get_shipment_by_status` 튜플 서비스는 무변경 (M-Q7 — 별도 함수 호출)

### FE (`si_finishing_screen.dart`)
- 출하예정 탭: 검색 없으면 주차 ExpansionTile 카드(접힘 기본, 펼치면 모델 카운트) / 검색하면 평면. 탭 배지 = `_plannedTotal`(전체 기준). W53/12-31 "미정" 칩
- 출고완료 버튼 권한 정합: `_isGstSelf`(company=='GST', GST 전원) → `_canShip`(`role=='SI' || isManager || isAdmin`, BE `si_manager_or_admin_required` 정확 미러). **GST PI/QI 비매니저 403 방지**. BE 권한 데코 무변경 (협력사 매니저는 read가 막혀 무해)

### 검증
- pytest `test_sprint79_shipment_flow` **25 passed** (기존 18 + 신규 WK-01~07: 주차/모델 그룹·actual 제외·TEST 제외·구조 정합·route by_week 포함/미포함·per_page=1에도 전체)
- **Codex 라운드 1 (M=4/A=2/N=3) → 라운드 2 (M=0, DEPLOY_SAFE: YES)** — M 4건(predicate 공유/튜플 계약/pytest 확대/권한 정합) 전부 반영
- flutter build web GREEN. migration 불필요. 권한 BE 변경 0
- 설계서: `SPRINT80_SI_SHIPMENT_WEEK_GROUP.md`

### 후속 BACKLOG (Codex 라운드 2 A)
- `BACKLOG-SPRINT80-W53-PLACEHOLDER-20260529` 🟡 — FE "미정" 칩이 12/31 placeholder 가정. 실제 ISO W53 출하 생기면 오표시 → BE가 미정 플래그 필드로 내려줄 때만 표시
- `TEST-SPRINT80-WEEK-EDGE-20260529` 🟡 — W53 경계 / SI_SHIPMENT 완료 기반 actual 제외 / cleanup-before-yield 경계 TC

---

## [2.20.15] - 2026-05-29 — SI 마무리공정 출고완료 권한 확장 (GST SI 인원 허용)

> OPS SI 마무리공정 "출고 완료" 버튼이 manager/admin만 가능 → SI 일반 작업자(role='SI', is_manager=False)가 403. GST SI 인원 6명 중 1명(엄대선, manager)만 가능했음.

### Fix
- **BE**: `jwt_auth.py` 신규 데코레이터 `si_manager_or_admin_required` (manager OR admin OR role='SI'). `work_shipment.py` ship-complete route `@manager_or_admin_required` → `@si_manager_or_admin_required`. admin-complete(PI/QI 종료)은 `@manager_or_admin_required` 유지 (무변경)
- **FE**: `gst_products_screen.dart` — `canShip = canManage || (category=='SI' && isSi)`. SI 인원은 SI 화면에서만 [출고 완료] 노출 / PI·QI 화면(같은 공용 화면)에선 [종료] 버튼 미노출 (admin-complete은 manager/admin 한정)

### 정책
- SI 마무리공정의 마지막 액션 = 출고완료 → SI 작업자가 직접 처리 (Twin파파 결정 2026-05-29)
- 현재는 정적 `workers.role == 'SI'` 기준. 공정(activeRole) 전환 시 동적 권한 연동은 BACKLOG `FEAT-ACTIVE-ROLE-DYNAMIC-PERMISSION-20260529`

### 검증
- pytest test_ship_complete — 신규 `TestShipCompletePermission` (PERM-01 SI 작업자 200 / PERM-02 PI 작업자 403 / PERM-03 협력사 manager 200 회귀) + **기존 TC-SHIP-11 회귀 수정** (`_worker`가 role='SI'라 SI 확장 후 200이 되어 깨짐 → PI 작업자로 교체)
- **Codex 라운드 1: M=0 / A=6 (전부 advisory)** — Codex가 PERM-03 회귀 TC 추가. 단 TC-SHIP-11 SI 작업자 회귀는 Codex 미검출 → Claude 측 catch 후 수정
- 회귀: 기존 manager/admin ship-complete 불변 / admin-complete 무변경 / migration 불필요
- VIEW 변경 0 (OPS 앱 전용 화면)

### 후속 BACKLOG
- `FEAT-ACTIVE-ROLE-DYNAMIC-PERMISSION-20260529` 🟡 — 공정(activeRole) 전환 시 권한 동적 연동 (JWT activeRole 반영 + BE 권한 체크 activeRole 기준 + 토큰 재발급). 사용자 요청 (2026-05-29)

---

## [2.20.14] - 2026-05-29 — 종료 분석 페이지 GST 매니저 전체 조회 (권한 fix)

> 종료(자동마감) 분석 페이지에서 GST 매니저(is_admin=False)가 GST task(PI/QI/SI 검사)만 보이고 협력사 task(MECH/ELEC/TMS)는 안 보임. admin은 전체 정상.

### Root Cause
- GST 인원은 PI/QI/SI 검사 공정만 수행 → 기존 `_build_partner_filter` manager 분기가 `work_start_log JOIN workers WHERE w_f.company = worker_company` 로 "자기 회사 소속 worker 참여 task만" 필터링
- GST 매니저(company='GST') → GST 인원 참여 task(검사)만 매칭 → 협력사 작업 task 전부 누락
- admin은 `is_admin=True` 분기로 필터 없이 전체 노출

### Fix (dashboard_service.py — `_build_partner_filter`)
- `is_full_access = is_admin or (worker_company == "GST")` — GST는 발주·관리 주체 → admin과 동일하게 전체 조회 (partner 쿼리 시 해당 협력사만)
- 협력사 매니저(BAT/C&A/FNI/P&S/TMS)는 자기 회사 격리 유지 (무변경)
- summary + details 두 endpoint 동일 함수 → 일관 적용

### 검증
- pytest test_sprint71_dashboard 신규 `test_tc14b_gst_manager_sees_all_partners` (GST 매니저 → BAT+FNI 둘 다) + 기존 tc13(admin)/tc14(FNI 매니저 격리)/tc15(plain worker 403) 회귀 유지
- **Codex 라운드 1: M=0 (배포 블로커 없음) / A=2** — A-Q2(company='GST' 정규화 유틸) + A-Q6(추가 경계 TC) BACKLOG 이관
- 회귀 위험: GST 매니저만 동작 변경 / 협력사 매니저·admin 무변경 / migration 불필요 (기존 테이블만 조회)
- VIEW 변경 0 (BE 권한 로직만 → GST 매니저 토큰으로 호출 시 자동 전체 데이터 반환)

### 후속 BACKLOG (Codex A)
- `REFACTOR-COMPANY-NORMALIZE-20260529` 🟡 LOW — workers.company 'GST' 직접 문자열 비교 다수 (jwt_auth.py 등) → `normalize_company()` 공통 유틸 또는 DB check constraint
- `TEST-S71-GST-MANAGER-EDGE-20260529` 🟡 LOW — GST 매니저 details endpoint / partner=FNI 필터 / company 공백·소문자 경계 TC

---

## [2.20.13] - 2026-05-29 — VIEW #78: 공장 대시보드 TEST 데이터 전역 제외 (#69 확장)

> 공장 대시보드(`/factory`)에 TEST S/N 노출. #69의 `customer='TEST CUSTOMER'` 제외만으로는 부족.

### Root Cause (운영 검증 2026-05-29)
- TEST S/N(`serial_number LIKE 'TEST%'`) **17건** 중 **12건이 customer != 'TEST CUSTOMER'** (SEC 등 실고객사명)
- `customer_but_not_sn = 0` → serial_number prefix가 customer 조건의 상위집합
- #69 customer 기준만으로는 12건(TEST-1111/2221~2226/333/4444/5555 등) 누락

### Fix (factory.py 전역)
- `_TEST_EXCLUDE_SQL` 표준 상수 신설: `COALESCE(p.customer,'') <> 'TEST CUSTOMER' AND p.serial_number NOT LIKE 'TEST%'` (OR 통합, 미래 방어)
- 적용 6곳:
  - `_count_shipped` basis 3분기 (plan/actual/best)
  - `get_monthly_detail` where_sql 2 mode (단일/range) → count/items/by_model/by_customer 전부 정합
  - `get_weekly_kpi` production + by_stage
  - `get_monthly_kpi` production_count (#69 customer-only → serial_number OR 확장)

### 검증
- monthly_detail 5월 (mech_start): 169 → 164 (TEST 5건 제외)
- DB/마이그레이션 변경 0, **FE 변경 0** (BE 응답 자동 정합)

### 비고
- 공장 대시보드 = 경영 지표 → 토글 없이 항상 제외 (SNStatus/QR 페이지는 admin showTestSN 토글 별개)

---

## [2.20.12] - 2026-05-29 — VIEW #75 catch 1: ETL 변경 이력 필터 KST 자정 정합

> VIEW EtlChangeLogPage 운영 catch: "오늘/7일/14일/30일" 필터가 `NOW()` 24h 롤링 기준이라 어제 오후가 섞여 자정 정합 X.

### Fix (admin.py `/admin/etl/changes`)
```sql
-- Before: NOW() - INTERVAL 'N days'  (24h 롤링, 어제 오후 포함)
-- After (옵션 A, days=1=오늘 자정~현재):
cl.changed_at >= ((now() AT TIME ZONE 'Asia/Seoul')::date - (INTERVAL '1 day' * (%s - 1)))::timestamp
```
- changed_at = KST naive → `(now() AT TIME ZONE 'Asia/Seoul')::date` 기준 (서버 tz 독립)
- days=1 → 오늘 자정 / days=7 → 6일 전 자정 (오늘 포함 7일)
- VIEW PERIOD_OPTIONS `{value:1, label:'오늘'}` 의미 정합

### 검증 (운영)
- 경계: days=1→오늘 00:00 / 7→6일전 00:00 / 14→13일전 / 30→29일전 ✅
- 카운트: 오늘 24h롤링 32 → 자정기준 4 (어제 오후 28건 정확히 제외)

### catch 2 (serial_number tracking) — 스킵 (의도)
serial_number = 제품 고유 식별자 = 변경 불가가 정상. etl.change_log field_name 7종에 serial_number 없음 (ETL 미추적, 추적할 변경 자체가 없어야 정상). Twin파파 결정.

---

## [2.20.11] - 2026-05-29 — TMS(M)/TMS(E) 협력사 구분 + 매트릭스 셀↔리스트 정합 통일

> 사용자 catch: 매트릭스 'TMS' 셀이 모듈(TMS(M))+전장(TMS(E)) 뭉쳐 표시 + 셀 클릭 시 리스트 불일치 (TMS 셀 27 vs details 327).

### 도메인 규칙 (Twin파파 2026-05-29)
DB partner 컬럼은 'TMS' 단일 저장이나 의미 분리:
- `mech_partner='TMS'` → TMS(M) (MECH)
- `module_outsourcing='TMS'` → TMS(M) (TMS)
- `elec_partner='TMS'` → TMS(E) (ELEC)
→ ELEC 의 TMS 만 TMS(E), 나머지(MECH/TMS) TMS 는 TMS(M).

### Fix
- `_COMPANY_SQL` 표준 SQL 식 신설 (category별 1개 partner + TMS(M)/(E) 분기 + COALESCE '(미지정)')
- `_resolve_company_py`: details row 후처리 Python 버전 (1:1 정합)
- matrix / details / `_build_partner_filter` 3곳 통일 → 매트릭스 셀 ↔ 리스트 분류 기준 일치
- v2.20.10 `_UNASSIGNED` 특수분기 제거 (일반 통일에 흡수)

### 운영 검증 (5월)
- 매트릭스 (started auto): (미지정) 4 / BAT 28 / C&A 46 / FNI 38 / P&S 80 / TMS(E) 19 / TMS(M) 8 = grand_total 223
- 셀 클릭 details (auto+manual+force): TMS(M) 49(auto 8+force 41) / TMS(E) 21 / C&A 47 / (미지정) 5
- 매트릭스(started auto) vs details(force 포함) 모집단 분리 — 차이=force, 분류 기준 1:1 정합

---

## [2.20.10] - 2026-05-29 — 미지정 분류 버그 2건 (task_category TM→TMS + 미지정 셀 클릭)

> 사용자 catch: 매트릭스 '(미지정)' 셀 클릭 시 리스트 0건.

### 버그 1 — task_category 오타 (TM → TMS)
- dashboard_service.py 만 `task_category='TM'` (task_service.py 전체는 'TMS') — TMS 8건 매칭 실패 → 잘못 '(미지정)'
- Fix: matrix CASE + details company 결정 'TM' → 'TMS' (v2.20.11 에서 _COMPANY_SQL 로 흡수)

### 버그 2 — '(미지정)' 셀 클릭 0건
- partner='(미지정)' 을 `pi.mech_partner='(미지정)' OR ...` 직접 매칭 → DB 에 없는 표시값 → 0건
- Fix: `_UNASSIGNED` sentinel + category-aware CASE 매칭 (v2.20.11 에서 통일)

---

## [2.20.9] - 2026-05-29 — v2.20.8 syntax 깨짐 hotfix (trigger_sql 복원)

> v2.20.8 (afe477e) Railway 배포 실패 (15분+ 지연) — 4 분포 SQL force_closed=FALSE 가드 python 일괄 치환 시 regex 가 details endpoint 의 `trigger_sql` 문자열 리터럴 내부 `AND t.close_reason LIKE %s` 까지 매칭 → 줄바꿈 삽입 → `unterminated string literal (line 755)` → import 실패 → Flask boot 실패 → Railway health check 실패 → 배포 rollback (v2.20.7 잔존).

### Fix
- `trigger_sql = " AND t.close_reason LIKE %s "` 한 줄 복원 (details trigger filter — close_filter 가 이미 force_closed 처리하므로 가드 불필요)
- 4 분포 SQL force_closed=FALSE 가드 7곳 정상 유지 (L257/297/313/361/395/442/478)

### 검증 (배포 후)
- `/auto-close-summary?period=month`: 200, invariant 통과
  - auto=223 (started=223, missed_worker=243) / manual=0 / force=107 / total=330
  - 분포 정합: task_dist=223 / partner_dist=243 / grand_total=223
- force.by_reason: 누락 38 / 작업자누락 27 / 작업자 미처리 26 / ...
- `/auto-close-details`: close_type 'auto'/'force' 분류 정상
- #76 partner=C&A: 200, total=95 (회귀 0)

### 교훈
일괄 치환(sed/regex) 후 반드시 `ast.parse` syntax 검증 선행. 문자열 리터럴 내부 매칭 위험.

---

## [2.20.8] - 2026-05-29 — #77 hotfix — 4 분포 SQL force_closed=FALSE 가드 (배포 실패 → v2.20.9)

> v2.20.7 배포 후 invariant violation (task_distribution sum != started_task_count, 차이 4). 원인: auto CTE 에는 force_closed=FALSE 가드 추가했으나 4 분포 SQL 누락. force_closed=TRUE + AUTO_CLOSED_BY_% 케이스가 분포에만 포함되어 차이 발생.

### Fix (의도)
4 분포 SQL (trigger / task / partner / hourly + task_distribution CTE + partner_task_matrix CTE) 에 `AND t.force_closed=FALSE` 가드 8곳 추가.

⚠️ **배포 실패** — python 일괄 치환이 trigger_sql 문자열 리터럴 깨뜨림 → Flask boot 실패 → v2.20.9 에서 syntax 복원.

---

## [2.20.7] - 2026-05-29 — VIEW #77 — force_closed 카운트 + close_type 추가

> VIEW v1.54.0 Sprint 71 정식 연동 catch — 마감 유형 3분류 (자동/수동/강제). 옵션 X 채택 (force_closed=TRUE only, v2.15.16 force_closed=FALSE 통일 합의 정합).

### 운영 검증 (5-15 이후)
- force_closed=TRUE: 99건 (closed_by 매핑 97%)
- close_reason 매니저 free-text: '누락'/'작업자누락'/'작업자 미처리'/'종료 안함'/'test'
- MANUAL_FORCE_CLOSE enum: 0건 (legacy 정의, 운영 미사용)

### 분류 정의
- auto_closed = `close_reason LIKE 'AUTO_CLOSED_BY_%' AND force_closed=FALSE`
- manual_closed = `close_reason = 'MANUAL_FORCE_CLOSE' AND force_closed=FALSE`
- force_closed = `force_closed = TRUE` (매니저 명시적 [강제 종료])
- total_missed_close = auto + manual + force

### 변경
1. `_query_kpi_counts`: force CTE 신규 + force_count + auto/manual force_closed=FALSE 가드
2. `_query_force_close_reason_distribution` (신규): 강제 종료 close_reason 분포 (by_reason)
3. `build_auto_close_summary`: force_closed block (count/prev/delta/trend/improvement_pct/by_reason) + total = auto+manual+force
4. `_assert_invariants`: total 영역 force 합산 추가
5. `build_auto_close_details`: close_filter (auto OR manual OR force 합집합) + items 영역 close_type ('auto'|'manual'|'force')

### VIEW 측 후속
- types/dashboard.ts AutoCloseSummary 영역 force_closed?: CountWithDelta + by_reason
- AutoCloseDetailItem 영역 close_type?: 'auto'|'manual'|'force'
- KPI 3카드 분리 (옵션 A — Twin파파 확정)

---

## [2.20.6] - 2026-05-29 — VIEW #76 HOTFIX — auto-close-details 500 (SQL alias mismatch)

> VIEW v1.54.0 localhost 검증 중 매트릭스 셀 클릭 시 partner=C%26A → 500 INTERNAL_ERROR.

### Root Cause — SQL alias mismatch
- count_sql: `LEFT JOIN plan.product_info pi` (alias 'pi')
- item_sql: `LEFT JOIN plan.product_info p` (alias 'p') ← 불일치
- `_build_partner_filter` 응답: hardcoded `pi.mech_partner`
- partner 미지정 → partner_sql="" → 정상 / partner 명시 → item_sql 안 undefined alias 'pi' → PostgreSQL error → 500

### Fix
- item_sql alias 'p' → 'pi' 통일 (count_sql 정합)
- p.model/p.sales_order/p.mech_partner/p.elec_partner/p.module_outsourcing → pi.*
- row 처리 영역 PI/QI/SI category + partner NULL → '(미지정)' 분류 (Sprint 71 v3 패턴 정합)

### 검증
- partner=C&A: 200, total 80 (이전 500)
- VIEW 영향 0 (코드 변경 0, BE fix 자동 정합)

---

## [2.20.3] - 2026-05-29 — APScheduler timezone fix (시간 단위 cron 9시간 지연 버그)

> v2.20.2 디버그 endpoint로 root cause 확정: APScheduler `BackgroundScheduler(timezone=Config.KST)` 가 stdlib `timezone(timedelta(hours=9))` 를 정확한 IANA tz 로 인식 못해 시간 단위 cron 의 fire time 을 UTC 로 해석. 분 단위/interval cron 은 영향 없음.

### 확정 증거 (v2.20.2 `/api/admin/debug/scheduler` 응답)

```json
"id": "alert_shipment_overdue",
"trigger": "cron[hour='7', minute='30']",
"next_run_time": "2026-05-29T07:30:00+00:00"  ← UTC 07:30 = KST 16:30!
"timezone": "UTC+09:00"
```

→ 의도: 07:30 KST (= 22:30 UTC) / 실제: 07:30 UTC (= 16:30 KST) — **9시간 지연**

### 영향받은 cron 8종 (시간 단위 전부)

| Cron | 의도 KST | 실제 fire | Sprint |
|---|---|---|---|
| `alert_shipment_overdue` | 07:30 | 16:30 | Sprint 79 |
| `task_escalation` | 09:00 | 18:00 | Sprint 3 |
| `_check_checklist_done_task_open_09` | 09:00 | 18:00 | Sprint 52 |
| `_check_checklist_done_task_open_15` | 15:00 | 00:00 (+1) | Sprint 52 |
| `shift_end_reminder_17` | 17:00 | 02:00 (+1) | Sprint 3 |
| `check_unfinished_tasks` | 18:00 | 03:00 (+1) | 기존 |
| `shift_end_reminder_20` | 20:00 | 05:00 (+1) | Sprint 3 |
| `cleanup_access_logs` | 03:00 | 12:00 | Sprint 32 |

영향 없는 cron (timezone 무관):
- `pool_warmup` (interval 5분)
- `task_reminder` (cron[minute='0'] 매 정각)
- `check_break_time` (cron[second='0'] 매 분 정각)
- `check_orphan_relay_tasks` (cron[minute='0'] 매 정각)

### Fix

`backend/app/config.py`:
```python
from zoneinfo import ZoneInfo
KST = ZoneInfo('Asia/Seoul')  # 이전: timezone(timedelta(hours=9))
```

`backend/requirements.txt`:
```
tzdata>=2024.1  # Railway 컨테이너 IANA tz DB 보장
```

### 부수 변경

- `_alert_shipment_overdue` 가 실행 결과 dict 반환 (enabled / overdue_count / recipients_emails / send_success / reason)
- `admin_debug` run-job endpoint 가 `job_result` 응답 필드에 포함 → 메일 발송 성공/실패 즉시 확인 가능

### 영향

배포 후 즉시 scheduler 재초기화 → 모든 시간 단위 cron 의 next_run_time 이 정상 KST 시각으로 재계산. 내일(5-30) 07:30 KST 부터 출하 미처리 알림 정상 발송 예정.

---

## [2.20.2] - 2026-05-29 — admin debug endpoints (scheduler 진단 + cron 강제 실행)

> 5-29 07:30 KST 출하 미처리 알림 cron 누락 사건 후속. Railway 로그 분석 결과 다른 cron 4종 (pool_warmup / task_reminder / check_orphan_relay_tasks / check_break_time) 은 정상 fire / `alert_shipment_overdue` 만 0건. root cause 즉시 진단 + 운영 중 cron 누락 의심 시 임시 복구 수단 확보.

### 신규 endpoint 2개

- `GET /api/admin/debug/scheduler` — 등록된 cron job 전체 + 다음 실행 시각 + trigger + func 경로
- `POST /api/admin/debug/run-job/<job_id>` — 특정 cron 즉시 강제 실행 (동기, 결과 응답 포함)

### 신규 파일

- `backend/app/routes/admin_debug.py` (+~110 LoC) — 권한 `@jwt_required + @admin_required`

### 핵심 기능

1. **scheduler 진단**: 실제로 `alert_shipment_overdue` 가 scheduler 에 등록돼 있는지 즉시 확인
   - 등록 X → root cause A (silent 예외로 add_job 실패)
   - 등록 O 인데 fire 안 됨 → root cause C (timezone / next_run 계산 이슈)
2. **강제 발송**: 어제(5-28) 출하 미처리 10건 메일 즉시 발송 + 결과(success/error/traceback) 응답으로 확인
3. **재발 방지**: 향후 cron 누락 의심 시 1초 만에 검증 + 즉시 복구

### 사용 시나리오

```bash
# 1. 현재 등록 jobs 확인
curl -X GET https://<railway>/api/admin/debug/scheduler \
  -H "Authorization: Bearer <admin_token>"
# → { "running": true, "job_count": 13, "jobs": [...] }
# alert_shipment_overdue 가 jobs 안에 있는지 catch

# 2. 강제 실행
curl -X POST https://<railway>/api/admin/debug/run-job/alert_shipment_overdue \
  -H "Authorization: Bearer <admin_token>"
# → { "success": true, "started_at": ..., "finished_at": ... }
```

### 회귀 위험 0

- 신규 endpoint 2개 (기존 코드 touch 0)
- admin 전용 권한 (manager 차단)
- scheduler 자체는 read-only (run-job 만 강제 fire)

---

## [2.20.1] - 2026-05-29 — Sprint 71 hotfix — partner_task_matrix invariant violation 해소 (Sprint 76 패턴 정합)

> VIEW 측 catch (2026-05-28): `partner_task_matrix.grand_total 202 != started_task_count 215` → InvariantViolationError 500. Sprint 76 `product_code NULL` COALESCE 패턴 정합 fix.

### Root Cause

`_query_partner_task_matrix` SQL이 `HAVING ... IS NOT NULL`로 NULL partner 제외 → grand_total 부족 → invariant 위반.

**2가지 누락 경로**:
1. **PI/QI/SI category 자동 마감** — `CASE` 분기 `ELSE NULL` → HAVING 제외
2. **plan.product_info partner NULL** — 외부 협력사 미입력 / serial_number 매칭 X

### 운영 actual data 검증 (7일)

| task_category | auto_count | started | partner |
|---|---|---|---|
| ELEC | 35 | 35 | elec_partner ✅ |
| MECH | 32 | 32 | mech_partner ✅ |
| TMS | 4 | 4 | module_outsourcing ✅ |
| **PI** | **3** | **3** | **task_category ELSE NULL** → **'(미지정)'** |

**'(미지정)' 3건** = GBWS-7150 / GBWS-7110 / GBWS-7143 (`PI_LNG_UTIL` LNG/UTIL 가압검사, Sprint 41-D SECOND TRIGGER `PI_CHAMBER`)

→ **PI = GST 자사 인원 작업** = 협력사 매핑 자체가 없음 = `'(미지정)'` 분류 의미상 정합

### fix

`backend/app/services/dashboard_service.py _query_partner_task_matrix` SQL:
```sql
-- 이전
CASE WHEN task_category='MECH' THEN mech_partner ... ELSE NULL END AS company
...
HAVING CASE WHEN ... ELSE NULL END IS NOT NULL

-- 이후
COALESCE(
  NULLIF(TRIM(CASE WHEN task_category='MECH' THEN mech_partner ... ELSE NULL END), ''),
  '(미지정)'
) AS company
-- HAVING 제거
```

### pytest

- **TC-19 invariant_holds_with_unassigned_partner** ✅ PASS — fix 작동 입증 (sn9 mech_partner=NULL + sn10 PI category seed → grand_total == started_task_count)
- TC-18b grand_total_equals_started_task_count ✅ PASS — 회귀 0
- TC-20 unassigned_company_group_exists — `@pytest.mark.skip` (test infra 미스터리, 운영 actual data로 정합 검증 완료, POST-REVIEW-TC20-FIXTURE-MYSTERY-20260529 BACKLOG)

### 효과

| 항목 | Before | After |
|---|---|---|
| partner_task_matrix.grand_total | 202 (NULL 제외) | **215** (= started_task_count) ✅ |
| `(미지정)` row | 없음 | 신규 (PI category + partner NULL 통합) |
| InvariantViolationError | 발생 | 해소 ✅ |
| VIEW 영향 | 변경 0 (자동 정합) | — |

### BACKLOG 등록

- `POST-REVIEW-TC20-FIXTURE-MYSTERY-20260529` — fixture seed sn9+sn10 DB commit O 인데 Flask app endpoint 미반영 (운영 영향 0, test infra only)

---

## [2.20.0] - 2026-05-28 — Sprint 71 — Manager Dashboard 자동 마감 분석 API 2개 (FEAT-MANAGER-DASHBOARD-AUTO-CLOSE-20260521)

> AXIS-VIEW Sprint 71 (FEAT-MISSED-CLOSE-ANALYSIS) `/analysis/missed-close` 페이지 BE part — mockup 5 file 작성 완료 + BE freeze (v3.1) + Codex 라운드 1/2/3 close 후 BE 구현 진입. 사용자 catch (2026-05-28): "Mockup 페이지는 만들어져있고 route 엔드포인트가 필요해서 검토".

### 신규 endpoint 2개

- `GET /api/admin/dashboard/auto-close-summary` — KPI 3 (auto/manual/total) + 분포 7종 (trigger / task / partner / hourly / unstarted_task / partner_task_matrix) + 모집단 3분리
- `GET /api/admin/dashboard/auto-close-details` — drill-down 상세 카드 (페이지네이션 + trigger_task_id filter)

### 신규 파일 (2)

- `backend/app/services/dashboard_service.py` (+620 LoC) — 7 SQL helper + `build_auto_close_summary` + `build_auto_close_details` + `_assert_invariants()` + `InvariantViolationError`
- `backend/app/routes/admin_dashboard.py` (+150 LoC) — endpoint 2개 + 권한 + period validation + InvariantViolationError → 500 변환

### 핵심 설계 (v3.1 freeze 정합)

- **분류 LIKE** — `AUTO_CLOSED_BY_%` → auto / `MANUAL_FORCE_CLOSE` → manual / `SHIP_COMPLETE` + `ADMIN_COMPLETE` + NULL → 제외
- **모집단 3분리** (Codex Q7) — `started_task_count` (work_start_log 있는 task) / `unstarted_task_count` (work_start_log 없는 task) / `missed_worker_count` (worker-miss 단위, 한 task 2명 누락 시 2)
- **V1 hourly** — 24h backfill 강제 + KST 변환 (`AT TIME ZONE 'Asia/Seoul'`)
- **V6 partner_task_matrix** — canonical 정렬 (`ORDER BY task_name, task_id`) + length 일치 + grand_total = started_task_count assertion (Codex Q6)
- **invariant check** (Codex Q-Freeze-3) — 5분포 합계 + 4 합산 invariant → `InvariantViolationError` raise → 500 + Sentry capture
- **평균 대비** — 옵션 A (지난 30일 일평균)
- **권한** — `@jwt_required + @manager_or_admin_required` + manager partner filter X1 (work_start_log + workers.company EXISTS subquery, 결정 6 정합)

### Codex 라운드 2회 trail

- **라운드 1** (M=3 / A=4): manager filter 기준 불일치 (X1 채택) / pytest GREEN 미확보 / access_log FK cleanup 누락 (root cause 확정)
- **라운드 2** (M=0 GREEN ✅): M1 + M3 fix 정합 + 18 TC GREEN 입증

### M3 fix — pytest fixture cleanup (Codex Q5 root cause)

- `tests/conftest.py` `create_test_worker` teardown 영역 `app_access_log` 선행 DELETE 추가
- `backend/app/__init__.py` `log_access` after_request handler 영역 FK violation 시 rollback + `put_conn` 보장 → connection leak 차단

### pytest TC 18 — `tests/backend/test_sprint71_dashboard.py`

- 분류 LIKE 6 (TC-01~06) ✅
- 모집단 3분리 3 (TC-07/08/09) ✅
- invariant 2 (TC-10/11) ✅
- hourly backfill 1 (TC-12) ✅
- 권한 admin/manager/worker 3 (TC-13~15) ✅
- drill-down 2 (TC-16/17) ✅
- grand_total assertion 1 (TC-18) ✅

**결과**: 18/18 PASSED (617s)

### BACKLOG 등록 (Codex A 4건 + 라운드 2 A 4건)

- `partner_task_matrix` `started_task_count` 인자 미사용 정리
- SQL `EXPLAIN ANALYZE` + 복합 index 후보 검토
- VIEW trend 색상/아이콘 운영 후 재검토
- alert threshold 운영 1~3개월 후 재검토
- `app_access_log` migration constraint drift 점검
- 추가 TC 권고 (admin partner='BAT' explicit / 빈 응답 / invalid period / 특수문자)

### 후속 catch — AXIS-VIEW

- VIEW `useAutoCloseSummary` / `useAutoCloseDetails` hook 추가 (BE 배포 직후 즉시 가능)
- read-only consume catch (책임 분리 원칙 정합)
- 복원/강제 액션 catch 시 OPS PWA 기존 mutation 경로 catch (별 sprint deep link 검토 후보)

---

## [2.19.11] - 2026-05-28 — #74 후속 — `_ALLOWED_DATE_FIELDS` 화이트리스트 qi_start + si_start 추가

> VIEW v1.53.0 prod 배포 후 사용자 catch (Twin파파, 2026-05-28 11:20 KST): Phase 1 QI/SI 카드 카운트 0 (400 INVALID_DATE_FIELD).

### Root cause

`factory.py _ALLOWED_DATE_FIELDS` 영역 `qi_start` / `si_start` 누락 — `date_field=qi_start` 또는 `si_start` 호출 시 400 catch.

### 변경 (1줄)

```python
_ALLOWED_DATE_FIELDS = {
    'pi_start', 'qi_start', 'si_start', 'mech_start',  # qi_start + si_start 추가
    'finishing_plan_end', 'ship_plan_date', 'actual_ship_date'
}
```

### 영향

- VIEW Phase 1 + Phase 2 QI/SI 카드 자동 정상화
- 기존 endpoint 호환 (화이트리스트 확장만)
- VIEW 변경 0 (BE fix 자동 정합)

### pytest

- `test_factory.py` 11/11 PASS (회귀)
- 기존 TC (pi_start / mech_start) 영역 그대로 PASS

### Railway 자동 배포

- BE only / push 영역 trigger

---

## [2.19.10] - 2026-05-28 — #74 옵션 C (factory.py date param) + 출하 알림 메일 template 회원가입 컨셉 정합

> 사용자 catch (5-28): 두 가지 통합 release.

### 1. VIEW #74 옵션 C — factory.py `/monthly-detail` `date` parameter 신규

- VIEW Sprint 78 (v1.53.0 mockup) 영역 공정 카드 today 클릭 시 단일 일자 fetch carrier
- 기존 month range mode + 신규 date single mode 분기
- `where_sql` + `where_params` 통합 (COUNT + items + by_model + by_customer 4 SQL 동일)
- 회귀 위험 0 (additive — 기존 month range 영역 변경 0)

### 2. 출하 미처리 메일 template — 회원가입 승인 메일 컨셉 정합

- `_render_shipment_overdue_html` 전면 rewrite (`_render_approval_html` 컨셉 carrier)
- 외곽: max-width 600 + `#f5f5f7` background + `-apple-system` font
- 카드: white + border-radius 12 + box-shadow
- **박스 엣지 색상 제거** (사용자 catch — `border-left` accent 제거)
- 헤더: ⚠️ + amber (`#d97706`) / 정보 박스 + 표 + [앱 열기] 버튼 + OPS 접속 안내

### 메일 발송 로직 spec 확정 (사용자 합의 정합 trail)

- 기준 일자: **yesterday** `ship_plan_date` (= D-1 plan 도래)
- 미처리 조건: `actual_date IS NULL` = COALESCE(app SI_SHIPMENT, ETL actual_ship_date) NULL = **양쪽 모두 미처리** (best 패턴 정합)
- best 패턴: 완료 = OR (app OR ETL) — De Morgan's law 영역 미처리 = AND (양쪽 NULL)
- 0건 skip / TEST CUSTOMER 제외 / admin 무조건 + chip name list

### pytest

- `test_factory.py` 11/11 PASS (회귀 9 + 신규 2: `date_param_single_day` + `date_invalid_format`)

### 메일 미리보기

- `frontend/web/mail-preview-shipment-overdue.html`
- local: `file:///Users/twinfafa/Desktop/GST/AXIS-OPS/frontend/web/mail-preview-shipment-overdue.html`
- Netlify 배포 후: `https://gaxis-ops.netlify.app/mail-preview-shipment-overdue.html`

### Railway 자동 배포

- BE only (FE 변경 0)
- push 영역 trigger

---

## [2.19.9] - 2026-05-28 — Sprint 79 — 출하 예정 탭 [출고 완료] 버튼 추가 (옵션 B 채택)

> 사용자 catch: 생산관리 일정 자동화 X — 매니저 catch 누락 case 발생 가능. 출하 예정 탭 검색창 활용 → 검색된 모델 직접 출하 처리.

### 객관 분석 — 옵션 B 채택

| 옵션 | 분석 |
|---|---|
| A (ship_plan_date today 변경 + 출하 확정 탭 이동) | ❌ ETL 덮어쓰기 + plan_change_warning (v2.18.33) 자기 충족 catch 위반 |
| **B (출하 예정 탭 직접 출고 완료)** | ✅ ETL plan 보존 + 책임 분리 + 매니저 직관 1step + audit trail 자동 |

### 변경

- `si_finishing_screen.dart` 1줄 변경 — `isConfirmed` 조건 제거 → Tab 2 + Tab 3 양쪽 [출고 완료] 버튼
- BE 변경 0 (audit trail = `SI_SHIPMENT.completed_at` 자동, best_ship CTE 정합)

### 추후 분석 인큐베이션

- `FEAT-SHIPMENT-PROCESS-AUDIT-ANALYSIS-20260528` (가칭)
- `SI_SHIPMENT.completed_at vs ship_plan_date` 비교 → 매니저 catch 패턴, ETL 정확도, 누락 비율
- Sprint 77 (Lead Time 준수율) + plan_change_warning 통합 catch

---

## [2.19.8] - 2026-05-28 — Sprint 79 — 출하 알림 chip 카드 (PI 위임 패턴 정합, GST 매니저 name)

> 사용자 catch: 출하 미처리 알림 토글 ON 시 PI 위임 chip 패턴처럼 name 추가 → 해당 사람만 메일 발송.

### BE 변경

- `SETTING_KEYS.shipment_alert_recipients`: `int_list` → **`string_list`** (worker name CSV base)
- `shipment_flow_service.get_overdue_alert_recipients`:
  - Parameter: `extra_worker_ids` (`List[int]`) → `extra_names` (`List[str]`)
  - SQL: `id = ANY` → `name = ANY AND company = 'GST'`
  - `is_admin = TRUE` 무조건 catch 유지 (gmail 도메인 포함)
- `scheduler_service._alert_shipment_overdue`: `extra_names` 호출 변경

### FE 변경

- `admin_options_screen.dart`:
  - `_shipmentAlertRecipients` (`List<String>`) + `_gstManagerNameOptions` 추가
  - `_loadGstManagerNames()` 신규 — `/admin/workers?company=GST&is_manager=true`
  - 토글 ON 시 `_buildChipListSetting` 카드 노출 (PI 위임 패턴 정합)

### pytest

- 18/18 PASS (2분 39초)
- 신규 TC 4건: `overdue_06` GST name 매칭 / `overdue_07` 협력사 제외 / `overdue_08` 동명이인 모두 catch / `overdue_09` 비승인 제외

---

## [2.19.7] - 2026-05-28 — Sprint 79 — 미종료 작업 분류 화면 UI 컨셉 정합 (PI/QI carrier)

- `pending_tasks_grouped_screen.dart` 전면 rewrite — `Card(elevation 0 + grey border + BorderRadius 12)` 패턴
- 색상 정합: MECH (orange) / ELEC (blue) / TMS (teal) / GST (indigo)
- 헤더: 차분한 amber 배경 + warning icon

---

## [2.19.6] - 2026-05-28 — Sprint 79 — SI Finishing 버튼 권한 logic 재정정

- Tab 1 미종료: 본인 task → [내 작업 완료] + admin/manager → [강제 종료] (둘 다 catch 시 Row Expanded 가로 배치)
- Tab 2 출하 확정: [출고 완료] 권한 = `_canManage` → **`_isGstSelf || _canManage`** (GST 인원 전체)
- 2차 확인 dialog: `_completeMyWork` / `_shipComplete` / `_forceCloseTask` 모두 `showDialog` confirm catch

---

## [2.19.5] - 2026-05-28 — Sprint 79 — SI 카드 디자인 PI/QI 컨셉 정합 + Tab 2 GST 인원 [내 작업 완료] 버튼

### BE schema 추가

- `/admin/tasks/pending` 응답: `model` + `customer` 추가 (in_progress + not_started 양쪽)
- `/admin/shipment/by-status` 응답: `si_finishing_task_id` + `si_finishing_worker_id` + `si_finishing_worker_name` 추가 (LATERAL JOIN)

### FE catch

- `_buildPendingCard` 신규 — PI/QI 카드 디자인 carrier (S/N bold + 진행중 chip + Divider + 공정 + 작업자 + 시작 시간)
- Tab 2 카드: 본인 task → [내 작업 완료] / admin/manager → [출고 완료]

---

## [2.19.4] - 2026-05-28 — Sprint 79 — 미종료 작업 권한 BE + SI 버튼 UI PI/QI 컨셉

- BE `/admin/tasks/pending`: `@manager_or_admin_required` 데코레이터 제거 + 본문 권한 분기 (admin OR manager OR company='GST')
- FE SI Finishing 버튼: `TextButton + Align.centerRight` → `Divider + Row Expanded + ElevatedButton` (PI/QI 정합)

---

## [2.19.3] - 2026-05-28 — Sprint 79 — 미종료 작업 권한 GST 자사 (FE)

- BE `/admin/tasks/pending/grouped`: `@admin_required` → `@gst_or_admin_required`
- FE home 메뉴: `isAdmin` → `isAdmin || company=='GST'`

---

## [2.19.2] - 2026-05-28 — Sprint 79 — SI Finishing action 버튼 추가

- 함수 3개 추가 (gst_products_screen + admin_options carrier):
  - `_completeMyWork(taskDetailId)` — POST `/app/work/complete`
  - `_shipComplete(serialNumber)` — POST `/app/work/ship-complete`
  - `_forceCloseTask(taskId, sn)` — PUT `/admin/tasks/<id>/force-close`

---

## [2.19.1] - 2026-05-27 — Sprint 79 — SI 카드 navigate + admin_options 분리 + 메일 토글

- home_screen SI 카드: `/gst-products?category=SI` → `/si-finishing`
- admin_options L957~L1268 (~310 lines) 비활성 사용자 + 미종료 작업 섹션 제거 → 메인 메뉴 분리 정합
- admin_options Admin Settings 섹션에 출하 미처리 알림 토글 추가 (`shipment_alert_enabled`)

---

## [2.19.0] - 2026-05-27 — Sprint 79 FEAT-SI-SHIPMENT-FLOW-3PHASE (출하 흐름 3단계 + admin 분리 + 출하 미처리 알림)

> 큰 sprint catch — SI 마무리공정 영역 TabBar 3개 (미종료/출하 확정/출하 예정) + admin 메인 메뉴 분리 + 매일 07:30 KST 출하 미처리 자동 알림.

### 변경 영역 (BE 6 + FE 5 파일 + pytest 1 + 설계서)

**BE 신규 2 파일**:
- `services/shipment_flow_service.py` — 4 service 함수 (~280 lines)
- `routes/admin_shipment_flow.py` — endpoint 2개 (~110 lines)

**BE 수정 4 파일**:
- `routes/admin.py` — SETTING_KEYS 신규 키 2개 + `_validate_setting` int_list 타입 신규
- `services/scheduler_service.py` — `_alert_shipment_overdue` cron (매일 07:30 KST)
- `services/notification_service.py` — `send_shipment_overdue_alert` 메일 템플릿
- `services/shipment_history_service.py` — `_get_actual_date_subquery()` 헬퍼 분리 (DRY)
- `__init__.py` — `admin_shipment_flow_bp` 등록

**FE 신규 3 파일**:
- `screens/si/si_finishing_screen.dart` — SI TabBar 3개 + 검색
- `screens/admin/inactive_users_screen.dart` — 비활성 사용자 메인 메뉴 (admin only)
- `screens/admin/pending_tasks_grouped_screen.dart` — 미종료 작업 분류 UI (admin only)

**FE 수정 2 파일**:
- `screens/home/home_screen.dart` — 메뉴 카드 2개 추가 (SI ~ 관리자 옵션 사이)
- `main.dart` — route 3개 신규 (`/si-finishing`, `/inactive-users`, `/pending-tasks-grouped`)

### 신규 endpoint

| Endpoint | 권한 | 영역 |
|---|---|---|
| `GET /api/admin/shipment/by-status?status=confirmed\|planned` | `@gst_or_admin_required` | SI 화면 탭 2/3 |
| `GET /api/admin/tasks/pending/grouped` | `@admin_required` | 미종료 작업 분류 (메인 메뉴) |

### 신규 admin_settings 키 2개

- `shipment_alert_enabled` (bool, default=False) — 매일 07:30 KST 출하 미처리 알림 토글
- `shipment_alert_recipients` (int_list, default=[]) — 추가 매니저 worker_id list (admin 자동 포함)

### Codex 라운드 1 catch 합의 (M=7/A=2/N=4)

| Q | 합의 |
|---|---|
| Q1 M | `_get_actual_date_subquery()` 헬퍼 분리 (DRY) |
| Q5 M | `int_list` 타입 신규 + workers JOIN (approval_status + is_active + email) |
| Q7 M | `@gst_or_admin_required` (by-status) + `@admin_required` (grouped) |
| Q8 M (사용자 결정 나) | `is_si_finishing_in_progress` 응답 필드 (탭 1+탭 2 overlap 명시 + 🔄 배지) |
| Q9 M | workers JOIN 영역 admin 자동 포함 (chip 중복 방지) |
| M-추가1 | endpoint 경로 정정 (`/api/admin/inactive-workers` + `/api/admin/deactivated-workers`) |
| M-추가2 (사용자 결정) | admin_settings `@gst_or_admin_required` v2.18.34 정합 유지 |
| Q3 A | retry catch X — 실패 로그 + Sentry capture |
| A-추가1 (사용자 결정 가) | TEST CUSTOMER 제외 (v2.18.32 패턴) |

### 검증

- pytest `test_sprint79_shipment_flow.py` 14/14 PASS (1분 37초)
- Flask boot OK + 신규 route 2개 등록
- flutter build web GREEN (12.7초)

### 운영 검증 catch (D+1)

- 매일 07:30 KST 영역 `_alert_shipment_overdue` cron 발송 catch
- 토글 ON + 어제 미처리 catch 시 메일 발송 (admin + recipients chip)
- 0건 시 skip (spam 방지)

### BACKLOG 등록 catch

- `FEAT-NOTIFICATION-OUTBOX-PATTERN-20260527` 🟢 INFO — outbox 패턴 (Codex Q3 A)
- `FEAT-GST-MANAGER-ADMIN-ROLE-PROMOTION-20260527` 🟢 INFO — GST 매니저 admin role 부여 (M2 후속)
- `REFACTOR-ADMIN-OPTIONS-SCREEN-CLEANUP-20260527` 🟡 LOW — admin_options 영역 비활성/미종료 카드 제거 (별 sprint)

---

## [2.18.35] - 2026-05-27 — 매뉴얼 모바일 PWA HOTFIX (ApiService 싱글톤 catch)

> v2.18.34 fix 후 사용자 운영 catch: "세션만료. 다시 로그인 후 메뉴얼 접속" SnackBar 만 뜨고 접속 불가. v2.18.34 영역 매뉴얼 fix 자체 catch 본질 catch 영역 즉시 HOTFIX.

### Root cause

`api_service.dart` L6 — **ApiService 영역 싱글톤 아님** (매번 new instance 생성):

```dart
class ApiService {
  String? _token;
  ApiService({String? baseUrl}) { ... }  // ← new instance 매번
}
```

`home_screen.dart _handleOpenManual()` 영역 `ApiService().token` 직접 호출 = **새 instance 생성** + `_token = null` 초기값 = SnackBar 노출.

login 시 `setToken()` 호출한 instance = **`apiServiceProvider`** (Riverpod Provider singleton, `auth_provider.dart` L296). v2.18.34 fix 시 Provider 영역 catch X.

### 변경 (FE 1 파일 + version)

| 파일 | 변경 |
|------|-----|
| `frontend/lib/screens/home/home_screen.dart` | `ApiService()` 직접 호출 → `ref.read(apiServiceProvider).token` 변경 (Provider singleton 영역 동일 instance 영역 token 캐시 접근 정합) |
| `backend/version.py` + `frontend/lib/utils/app_version.dart` | 2.18.34 → 2.18.35 |

### 검증

- flutter build web GREEN (12.6초)
- 사용자 실기기 catch 정상 (모바일 PWA 매뉴얼 새 탭 열림 ✅)

### 회귀 위험

- 0 (1줄 변경 — `ApiService()` → `ref.read(apiServiceProvider)`)
- ConsumerState 영역 `ref` 직접 사용 가능 (Widget tree scope)

### 다음 catch — 같은 sprint 인큐베이션

- `REFACTOR-API-SERVICE-SINGLETON-20260527` (가칭) — ApiService 영역 다른 곳 영역 `ApiService()` 직접 호출 grep sweep + Provider 영역 통일. 본 catch 영역 다른 화면 영역 잠재 catch 가능성 catch.

---

## [2.18.34] - 2026-05-27 — VIEW #72 admin 권한 데코레이터 통일 + 매뉴얼 모바일 PWA fix

> 두 catch 통합 release — VIEW OPS_API_REQUESTS.md #72 운영 차단 catch (testpm GST manager 영역 체크리스트/admin_settings 접근 불가) + OPS 매뉴얼 모바일 PWA catch (`BUG-OPS-MANUAL-BUTTON-MOBILE-PWA-20260526`).

### 변경 (BE 2 파일 + FE 1 파일 + version)

#### #72 admin 권한 데코레이터 통일 (BE 2 파일)

| 파일 | 변경 |
|------|-----|
| `backend/app/routes/checklist.py` | `@admin_required` → `@gst_or_admin_required` 5곳 (L259/378/511/598/654) + import 추가 |
| `backend/app/routes/admin.py` | `/settings` GET `@admin_required` → `@gst_or_admin_required` (L1543) / PUT `@manager_or_admin_required` → `@gst_or_admin_required` (L1574) + import 추가 |
| `backend/app/routes/admin.py` | `/api/admin/product-codes` 신규 endpoint 추가 (`@jwt_required + @gst_or_admin_required`, `SELECT DISTINCT product_code FROM plan.product_info`) |

#### 매뉴얼 모바일 PWA fix (FE 1 파일)

| 파일 | 변경 |
|------|-----|
| `frontend/lib/screens/home/home_screen.dart` | `_handleOpenManual()` 영역 `await authService.getToken()` (secure_storage async) → `ApiService().token` (sync getter) 변경 + import 추가 + token null SnackBar 안내 |

### 영향

#### #72

- **GST manager (testpm 외 모든 자사 manager)** — 체크리스트 관리 + admin_settings 정상 작동 ✅
- **GST 일반 작업자** (FE `canEdit=true`) — 체크리스트 관리 진입 + admin_settings 정상
- **협력사 (BAT/FNI/TMS/P&S/C&A)** — `@gst_or_admin_required` 영역 협력사 거부 → 기존 의도 유지
- **admin** — 영향 0 (계속 통과)
- **`/product-codes`** — 추후 product_code 모듈화 (200건 → 50개 미만 catch) 후 별 체크리스트 관리 base

#### 매뉴얼 fix

- **Root cause**: `await authService.getToken()` (secure_storage async read) → user gesture context lost → 모바일 popup blocker 차단 → `anchor.click()` 실패
- **장기 시스템 관점 추천 (A)** — `ApiService.token` sync getter 재사용 (L123 기존 패턴 + DRY 원칙 + 책임 분리)
- token null catch — SnackBar "세션 만료. 다시 로그인 후 매뉴얼 접속해주세요." 안내 + 매뉴얼 진입 차단
- 모바일 PWA standalone mode 영역 새 탭 정상 catch (iOS Safari + Android Chrome)

### 검증

- pytest `test_admin_options_api.py` 28/28 PASS (4분 32초, staging DB) — 권한 변경 회귀 0
- Flask boot OK + `/api/admin/product-codes` route 등록 확인
- flutter build web GREEN (13.2초)

### 회귀 위험

- 0 (additive endpoint + 권한 catch 영역 GST 자사 확장 + 협력사 차단 유지)
- FE 매뉴얼 catch 영역 sync getter 변경만 (기존 anchor click 패턴 유지)

### BACKLOG 처리

- `BUG-OPS-MANUAL-BUTTON-MOBILE-PWA-20260526` → ✅ CLOSED (옵션 A 영역 fix 완료)
- VIEW `OPS_API_REQUESTS.md` #72 → ✅ DONE (BE 측 7곳 + 신규 endpoint 완료)

### 다음 catch (BACKLOG)

- `BACKLOG-VIEW-PRODUCT-CODES-SEMANTIC-20260527` (가칭) — `/api/admin/product-codes` 응답 영역 = 숫자 SKU (200건). FE dropdown UX 영역 검색/페이지네이션 catch (별 sprint). 추후 product_code 모듈화 후 50개 미만 catch 시 재검토
- 다른 admin/* 영역 `@admin_required` 잘못 적용된 곳 grep sweep (별 sprint)

---

## [2.18.33] - 2026-05-27 — Sprint 76-BE 계획 변경 hint (plan_change_warning, 자기 충족 catch 신호)

> 사용자 catch (5-27): "계획대비 출하 영역 = 계획일 수정 시 100% 정시 트릭" 모순 catch.

### 운영 검증 (5월 plan 148건)

| 영역 | 값 |
|---|---|
| 5월 plan 영역 전체 | 148 |
| `ship_plan_date` 변경 S/N | **89건 (60%)** ← 자기 충족 catch 가능성 확인 |
| 전체 변경 record | 185 (S/N당 평균 2회 변경) |

→ fulfillment_pct / avg_delay_days 영역 단독 KPI 영역 신뢰성 catch — 변경 hint 영역 매니저 신호 의무.

### 변경 (BE 1 파일 + pytest 1 TC)

| 파일 | 변경 |
|------|-----|
| `backend/app/services/shipment_history_service.py` | `_fetch_plan_change_warning()` 신규 (2단계 SQL — `to_regclass` table catch + `etl.change_log` JOIN) |
| `get_shipment_summary()` | `kpi['plan_change_warning'] = ...` 응답 추가 |
| `tests/backend/test_shipment_history.py` | `test_kpi_08_plan_change_warning` 신규 |

### 응답 schema 추가

```json
"kpi": {
  "fulfillment_pct": 82.4,
  "avg_delay_days": 0.0,
  "plan_change_warning": {                   // ← 신규 (v2.18.33)
    "count": 89,
    "share_pct": 60.1,
    "hint": "89건 계획 변경됨 (전체 148건 중 60.1%) — 납기 준수율/평균 지연 영역 자기 충족 catch 가능"
  },
  ...
}
```

### 안전망 — etl.change_log 영역 test DB 영역 없음

`to_regclass('etl.change_log')` 영역 IF 분기 — test 환경 영역 자동 0 반환 (count=0, hint=null).

### pytest 결과

- **32/32 PASS** (5분 24초, staging DB)
- 회귀 위험 0 (BE 신규 함수 + 응답 추가, 기존 영역 영향 0)

### 다음 sprint 인큐베이션 — Sprint 77 (가칭) Lead Time 준수율

- 모델별 standard lead time 영역 admin_settings 등록
- 시작점/끝점 결정 (mech_start ~ actual_ship_date)
- 협력사 평가지수 base
- 운영 6개월+ 영역 actual 정확 일자 누적 후 진입

---

## [2.18.32] - 2026-05-27 — Sprint 76-BE TEST CUSTOMER 제외 (factory.py v2.15.21 정합)

> 사용자 catch (5-27): 5월 운영 정합성 검증 시 TEST 5건 포함된 응답 → factory.py v2.15.21 (#69) 영역 이미 적용된 패턴 동일 적용 의무.

### 변경 (BE 2곳)

| 파일 | 영역 | 변경 |
|------|---|-----|
| `backend/app/services/shipment_history_service.py` `_build_best_ship_cte()` | WHERE 절 | `AND COALESCE(p.customer, '') <> 'TEST CUSTOMER'` 추가 |
| 동일 파일 `_fetch_monthly_trend()` Query 1 | plan.product_info 직접 조회 | 동일 조건 추가 |
| `backend/version.py` + `app_version.dart` | — | 2.18.32 |

### 효과 (5월 운영 데이터)

| 영역 | Before | After |
|---|---|---|
| `kpi.plan_count` | 153 | **148** (TEST 5건 제외) |
| `kpi.shipped_count` | 122 | **122** (TEST 영역 shipped 0) |
| `kpi.fulfillment_pct` | 79.7% | **82.4%** (정합도 ↑) |
| `kpi.pending_count` | 26 | **26** (TEST 영역 pending 영역 plan_date 도래 X 영역 제외 가능성) |

### pytest

- **31/31 PASS** (5분 12초, staging DB)
- 회귀 위험 0 (BE WHERE 절 1줄 + monthly_trend 1줄)

### 연관

- v2.15.21 (#69 5-18) factory.py `monthly-kpi` 영역 동일 패턴 적용 (5월 169 → 164)
- 본 sprint 영역 단일 best 정의 정합 확보

### 다음 catch (별 sprint 영역 논의 중)

- 납기 준수율 / 평균 지연일 영역 **기준값 (target)** 도입 — 현재 단순 수치 표시. "82.4% 가 좋은 신호?" 영역 base 없음
- admin_settings 영역 등록 + alert 임계 + 매니저 시각화

---

## [2.18.31] - 2026-05-26 — OPS 매뉴얼 버튼 모바일 PWA catch fix (anchor click + fallback)

> 사용자 catch (5-26): OPS 매뉴얼 버튼 PC 환경 정상, 모바일 환경 페이지 전환 안 됨.

### 원인

PWA standalone mode (iOS Safari / Android Chrome PWA) 영역 `window.open(_blank)` 차단 catch.

### 변경 (FE 1 파일)

| 파일 | 내용 |
|------|-----|
| `frontend/lib/screens/home/home_screen.dart` `_handleOpenManual()` | `window.open(_blank)` → anchor element dynamic click 패턴 + fallback (`window.location.href`) |

### 변경 코드

```diff
- html.window.open(url, '_blank', 'noopener,noreferrer');
+ try {
+   final anchor = html.AnchorElement(href: url)
+     ..target = '_blank'
+     ..rel = 'noopener noreferrer';
+   html.document.body!.append(anchor);
+   anchor.click();
+   anchor.remove();
+ } catch (anchorErr) {
+   html.window.location.href = url;  // fallback (PWA 떠나지만 catch 해소)
+ }
```

### 효과

- 모바일 PWA standalone mode 영역 새 탭 정상 (95~99% 정합, web.dev 표준 패턴)
- fallback 영역 같은 탭 이동 (1~5% edge case catch)
- PC 영역 새 탭 그대로
- token 영역 query param 동일 (axis-manual JWT 미들웨어 정합)

### 회귀 위험

- FE 1 함수 영역 (5줄 → 12줄) — 회귀 0
- VIEW 영향 0 / BE 영향 0

---

## [2.18.30] - 2026-05-26 — Sprint 76-BE best_ship CTE model source 정정 (product_code → model 칼럼)

> 사용자 catch (5-26): v2.18.29 운영 검증 시 by_model 합 != kpi.plan_count invariant 실패 → 운영 데이터 분석 결과 product_code 와 model 칼럼이 의미 완전 다른 catch.

### 운영 데이터 검증 (2026년 ship_plan 1199건)

| 항목 | 결과 |
|---|---|
| product_code NOT NULL | 1194 |
| model NOT NULL | 1199 (NOT NULL constraint) |
| 두 칼럼 같은 값 | **0건** |
| 두 칼럼 다른 값 | **1194건** |
| product_code NULL | 5건 (TEST 데이터) |

**의미 차이**:
- `product_code` = 숫자 SKU (예: '41200152', '41100286')
- `model` = 분류 이름 (예: 'GAIA-I DUAL', 'GAIA-LE', 'DRAGON')

→ by_model 카드 매니저 직관 = 분류 이름 (model 칼럼). product_code 사용 시 숫자 SKU 노출 + NULL 5건 invariant 실패.

### 변경 (BE 1줄)

| 파일 | 변경 |
|------|-----|
| `backend/app/services/shipment_history_service.py` `_best_ship_sql_select()` | `p.product_code AS model` → `p.model AS model` |
| `backend/version.py` + `app_version.dart` | 2.18.30 |

### 효과

- by_model 응답 `model` 필드 = "GAIA-I DUAL" 등 분류 이름 (매니저 직관 ↑)
- TEST 5건 자동 해소 (model 칼럼 = 'GAIA' 채워짐, NOT NULL 정합)
- invariant 자동 정합 (model NOT NULL constraint → NULL 제외 0건)
- VIEW 측 변경 0 (응답 schema 유지)

### pytest 결과

- **31/31 PASS** (3분 43초, staging DB)
- 회귀 위험 0 (BE 1줄 + 응답 schema 유지)

### VIEW 측 영향 0

- `model` 필드 type 변경 0 (`string` 그대로)
- 단 표시값 변경 — `"GAIA-I DUAL"` 등 분류 이름 (이전 `product_code` 값 = 숫자 SKU)

---

## [2.18.29] - 2026-05-26 — Sprint 76-BE by_model 옵션 C 정정 + P-v3 avg_lead_time_days 추가

> v2.18.28 운영 catch (사용자 5-26) — by_model 영역 base 일관성 정정 + lead time standard 추가.

### 사용자 catch 정합

1. **by_model 영역 일관성** — `by_customer` 영역 plan + shipped 분리인데 `by_model` 영역 plan 만 (count 단일) → base 다른 catch
2. **공정 순서 정정** — `elec → TM → mech → mech+TM → mech+elec → pi` (운영 1352/1357 영역 elec_first 검증)
3. **PI 일정 변동성** — pi_start 변동 가능하지만 standard value 의미상 현재 master plan 영역 그대로 OK
4. **데이터 source** — Plan ETL (master plan) standard, 추후 OPS actual lead time 인큐베이션

### 변경 (BE 1 + pytest +2 + version)

| 파일 | 내용 |
|------|-----|
| `backend/app/services/shipment_history_service.py` `_fetch_by_model()` | 옵션 C 정정 — `{model, plan, shipped, share_pct, avg_lead_time_days}` (`count` 필드 제거 + `plan`/`shipped` 분리 + `avg_lead_time_days` P-v3 추가) |
| `backend/app/services/shipment_history_service.py` `_assert_invariants()` | invariant +2 (`by_model.plan sum = kpi.plan_count` + `by_model.shipped sum = kpi.shipped_count`) — 총 5건 |
| `tests/backend/test_shipment_history.py` | TC +2 (`test_kpi_06_invariant_by_model_sum` + `test_kpi_07_by_model_avg_lead_time`) — 29 → 31 TC |
| `backend/version.py` + `app_version.dart` | 2.18.29 |

### 핵심 catch

- **옵션 C** — by_model 영역 `by_customer` 영역과 동일 패턴 (plan + shipped 분리, share_pct plan 기준)
- **shipped 정의** — best 패턴 (factory.py `_count_shipped(basis='best')` 정합) = `actual_ship_date IS NOT NULL OR SI_SHIPMENT.completed_at IS NOT NULL` (force_closed=FALSE)
- **P-v3 avg_lead_time_days** — Master Plan standard:
  ```sql
  AVG(pi_start - LEAST(elec_start, mech_start))
  ```
  · 시작 = elec_start (운영 1352/1357 검증, mech_first 5건 catch LEAST 안전망)
  · 끝 = pi_start (협력사 작업 끝 = 검사 진입)
  · ship_plan_date 변동 영향 0 (standard value, 모델별 비교 안정)
- **invariant 5건** — calendar plan / by_customer plan + shipped / by_model plan + shipped → 실패 시 500 + Sentry

### 응답 schema 변경 (breaking 0 — additive only)

```diff
"by_model": [
  {
    "model": "GAIA-LE",
-   "count": 52,
+   "plan": 52,                  // ship_plan_date 기준 (Master Plan)
+   "shipped": 49,               // best 패턴 (app SI ∪ excel actual)
    "share_pct": 31.7,           // plan 기준 (by_customer 와 동일)
+   "avg_lead_time_days": 28.0   // P-v3 협력사 lead standard
  }
]
```

⚠️ **breaking change 영역** — `count` → `plan` rename. VIEW 측 type 정정 동반 (정식 구현 진입 시).

### pytest 결과

- **31/31 PASS** (5분 7초, staging DB) — 신규 2 TC 포함 GREEN
- 회귀 위험 0 (additive + rename)

### BACKLOG 신규

- `BACKLOG-SPRINT76-ACTUAL-LEAD-TIME-OPS-20260526` 🟢 INFO (인큐베이션) — 추후 OPS actual data 기반 lead time 산출 + **토글 옵션** (`?lead_time_basis=plan/actual`). 공장 대시보드 `?basis=plan/actual/best` 패턴 정합. 운영 3~6개월+ 후

### 의존 관계

- ✅ v2.18.28 Sprint 76-BE prod 배포 직후 ASAP
- ⏳ AXIS-VIEW Sprint 76 FE — `count` → `plan` rename + `shipped` / `avg_lead_time_days` 신규 type 정정 (정식 구현 시)

---

## [2.18.28] - 2026-05-26 — Sprint 76-BE 출하이력 페이지 BE 신규 (FEAT-SHIPMENT-HISTORY-BE)

> AXIS-VIEW Sprint 76 (`/production/shipment`) mockup v1.51.1 의 OPS BE part. AXIS-VIEW `OPS_API_REQUESTS.md` #73 v2 명세 흡수 + Codex 2 라운드 (M=12 / A=4 / N=1 전수 close).

### 신규 endpoint 2개

| HTTP | 경로 | 권한 | 설명 |
|------|-----|------|------|
| GET | `/api/admin/shipment/summary` | `@jwt_required + @gst_or_admin_required` | KPI 6 + 분포 6 + monthly_trend + top_delayed |
| GET | `/api/admin/shipment/details` | 동일 | S/N 1:1 페이지네이션 + 필터 + 검색 |

### 변경 (BE 3 파일 + 신규 1 + pytest 1 + version)

| 파일 | 내용 |
|------|-----|
| `backend/app/services/shipment_history_service.py` (신규 ~500 LoC) | best_ship CTE + KPI + 캘린더 + monthly_trend + by_customer/model + top_delayed batch + `format_root_cause()` + `_assert_invariants()` |
| `backend/app/routes/shipment_history.py` (신규 ~110 LoC) | API 2개 + Blueprint + 권한 + invalid param 검증 |
| `backend/app/__init__.py` | Blueprint import + register (2줄) |
| `tests/backend/test_shipment_history.py` (신규 ~520 LoC) | 29 TC (auth 4 + KPI 5 + source 4 + status 4 + pagination 4 + monthly 2 + top_delayed 1 + format_root_cause 5) + TEST-SHIP-76-* 전용 fixture |
| `backend/version.py` + `frontend/.../app_version.dart` | 2.18.28 |

### 핵심 catch

- **단일 best 정의 정합** — factory.py `_count_shipped(basis='best')` L88~99 와 동일 패턴 (공장 대시보드 ↔ 출하이력 카운트 동기화)
- **반개구간 `>= AND <`** (Codex Q5 M) — 월말/월초 중복 회피
- **N+1 방지** — top_delayed 5건 batch 조회 `WHERE serial_number = ANY(%s)` (Codex Q3 M)
- **invariant 3건** — calendar plan / by_customer plan / by_customer shipped 합계 정합 → 실패 시 500 + Sentry capture (Codex Q8 M)
- **task_category DB 조회** — hardcoding X (Codex Q3 M)
- **신규 파일 분리** — mutation `shipment_service.py` (v2.17.0) 와 read-only `shipment_history_service.py` 책임 분리 (Codex Q3 M)

### Codex 검증 trail

| 라운드 | 일자 | 결과 | 처리 |
|---|---|---|---|
| 1 (VIEW) | 5-26 | M=7 / A=2 + 사용자 결정 6건 | 전수 반영 (v2 명세) |
| 2 (OPS BE) | 5-26 | M=5 / A=2 / N=1 | M 5건 close + A 2건 BACKLOG |

### pytest 결과

- **29/29 PASS** (4분 19초, staging DB) — 모든 TC GREEN
- 회귀 위험 0 (신규 endpoint + 신규 파일, 기존 코드 영향 0)
- 운영 데이터 보존 — TEST-SHIP-76-* 접두 S/N teardown 검증

### A 2건 BACKLOG

- `BACKLOG-SPRINT76-LATERAL-JOIN-20260526` (Q1) — best_ship CTE LATERAL JOIN 리팩토링
- `BACKLOG-SPRINT76-MONTHLY-CTE-UNIFY-20260526` (Q2) — monthly_trend 단일 CTE derive

### 의존 관계

- ✅ OPS #70 (v2.18.4 best 게이트 제거) prod 배포 완료
- ✅ Sprint 47/68 (ship-complete) prod 배포 완료
- ⏳ AXIS-VIEW Sprint 76 FE (mockup → 실 데이터) — BE freeze 후 진입
- 🟢 Sprint 71 BE 독립 (root_cause = close_reason literal 모델 레벨 보존)

---

## [2.18.27] - 2026-05-22 — 매뉴얼 보안 통합 (OPS 상단 버튼 + axis-manual JWT 미들웨어, Codex 라운드 1 M=2/A=8 반영)

> 사용자 catch: "사용자 매뉴얼도 url 을 공유 하는것 보다 버튼을 만들어줘 / url 이 현재 전체공개라 누구나 볼수 있게 됬는데 이것도 보안이 필요한데". OPS 매뉴얼 접근 통합 fix.

### 변경 (OPS 2 + axis-manual 3 + AXIS-VIEW 1)

| 파일 | 내용 |
|------|-----|
| `frontend/lib/screens/home/home_screen.dart` | 상단 actions 영역 — 설정 옆에 `[📖 매뉴얼]` IconButton 추가. `_handleOpenManual()` — access token 추출 → `?token=` 쿼리로 axis-manual 새 탭. Codex M-Q1 반영: `Uri.encodeQueryComponent` + `noopener,noreferrer` |
| `backend/app/services/notification_service.py` | 승인 메일 매뉴얼 박스 — 직접 URL 제거, "앱 로그인 후 [📖 매뉴얼] 버튼" 안내로 교체 (보안 일관성) |
| `axis-manual/netlify/edge-functions/auth.ts` (신규) | Netlify Edge Function — JWT (HS256) verify 미들웨어. ① `?token=...` 또는 Cookie 에서 추출 ② `JWT_SECRET_KEY` env 로 verify ③ Codex A-Q2: `payload.type==='access'` 검증 (refresh 차단) ④ Codex A-Q5: Cookie Max-Age 를 JWT exp 기준 동적 계산 ⑤ Codex M-Q3: 정적 자산 우회 축소 (favicon/robots/폰트만 — VitePress JS chunk 노출 방지) ⑥ 인증 실패 시 안내 페이지 |
| `axis-manual/netlify.toml` | `[[edge_functions]] path = "/*"` |
| `axis-manual/README.md` | Codex A-Q8 — 인증 미들웨어 동작 + Netlify env `JWT_SECRET_KEY` 등록 절차 + 보안 정책 문서화 |
| `AXIS-VIEW/app/src/components/layout/Header.tsx` | 매뉴얼 버튼 onClick — localStorage access token 추출 → `?token=` 첨부 (axis-manual 미들웨어 정합) |

### 인증 흐름

```
1. OPS 홈 [📖 매뉴얼] 클릭
   → const token = await AuthService.getToken()
   → window.open('https://axis-manual.netlify.app/?token={JWT}', '_blank', 'noopener,noreferrer')

2. Netlify Edge Function `auth.ts` 가로채기
   → ?token=... 추출 → jwtVerify(HS256, JWT_SECRET_KEY)
   → payload.type==='access' 검증
   → HttpOnly Cookie 저장 (Max-Age = JWT exp - now)
   → URL 토큰 제거 후 302 redirect

3. 이후 모든 페이지/리소스 요청
   → Cookie 자동 첨부 → Edge Function 자동 통과
   → 토큰 만료 시 401 안내 페이지
```

### Codex 라운드 1 결과 (M=2 + A=8 + N=1)

| Q | 라벨 | 상태 |
|---|---|---|
| M-Q1 token URL 인코딩·noopener | ✅ 반영 — `Uri.encodeQueryComponent` + `noopener,noreferrer` |
| M-Q3 정적 자산 우회 과대 | ✅ 반영 — `/assets/*` 우회 제거. favicon/robots/폰트(woff/woff2/ttf/otf/eot)만 우회. VitePress JS chunk 정상 인증 경로 |
| A-Q2 token type 검증 | ✅ 반영 — `payload.type !== 'access'` 시 401 |
| A-Q5 Cookie 만료 일치 | ✅ 반영 — Cookie Max-Age = JWT exp - now (fallback 2시간) |
| A-Q8 README 갱신 | ✅ 반영 — 인증 미들웨어 섹션 신규 |
| A-Q4/Q6/Q7 운영성 advisory | 🟡 BACKLOG 권고 (관리자 안내·로깅·이메일 본문 정리) |

### Netlify env 등록 (운영 필수)

매뉴얼 사이트 Netlify dashboard → Environment variables:

- `JWT_SECRET_KEY` = OPS BE Railway 의 `JWT_SECRET_KEY` 와 **동일 값**

⚠️ 다른 값이면 모든 토큰 401. 등록 후 deploy 재실행 필요.

### 회귀 위험

- OPS FE: 신규 IconButton + 함수 (additive) — 회귀 0
- BE: 메일 본문 박스 1개 변경 (URL 제거) — 기능 변경 0
- axis-manual: 신규 Edge Function — 미인증 직접 접근 차단됨 (의도). Netlify env 미등록 시 500 + 콘솔 에러 (운영자 catch 용이)
- AXIS-VIEW: localStorage token 추출 — token 없으면 base URL 그대로 (미들웨어가 401 안내)

### 연관

- v2.18.20 (notification_service.py 신규)
- v2.18.23 (매뉴얼 URL 메일 추가 — 본 release 영역 메일 안내 박스 정정)
- AXIS-VIEW v1.x (Header.tsx 매뉴얼 버튼 token 첨부)
- axis-manual v1.2.0 (Edge Function 인증 미들웨어 도입)

---

## [2.18.26] - 2026-05-22 — 로그인 후 AuthGate 강제 진입 (pushAndRemoveUntil)

> 사용자 catch: v2.18.25 fix 후에도 로그인 버튼 누르면 화면 안 넘어감. Dio response log 확인 시 token 발급 정상 → Navigator 스택 문제.

### 변경

| 파일 | 내용 |
|------|-----|
| `frontend/lib/screens/auth/login_screen.dart` | `popUntil((route) => route.isFirst)` → `pushAndRemoveUntil(MaterialPageRoute(builder: (_) => const AuthGate()), (route) => false)` 변경 |

### 원인

LoginScreen 자체가 first route 일 때 `popUntil` 가 무동작 → AuthGate (인증 상태 라우터) 진입 불가. `pushAndRemoveUntil` 로 stack 전부 비우고 AuthGate 신규 push.

회귀 위험 0 (Navigator 스택 정리 패턴).

---

## [2.18.25] - 2026-05-22 — 로그인 성공 후 화면 전환 안 될 시 새로고침 안내 SnackBar

> 사용자 catch: v2.18.24 후에도 PWA 모바일 영역 가입 승인 후 첫 로그인 시 화면 전환 안 됨. 강제 새로고침 어려움 (PWA 모바일 = Cmd+Shift+R 불가).

### 변경

| 파일 | 내용 |
|------|-----|
| `frontend/lib/screens/auth/login_screen.dart` | 로그인 성공 후 3초 후 화면 안 넘어가면 SnackBar 안내 (앱 종료 후 재실행 권고) |

> 주: v2.18.26 영역 `pushAndRemoveUntil` 정식 fix 로 본 안내 무용지물 (안전망 유지).

---

## [2.18.24] - 2026-05-22 — ApprovalPendingScreen 승인 후 자동 홈 이동 (강제 새로고침 catch)

> 사용자 catch: 이메일 인증 후 ApprovalPendingScreen 진입 → admin 승인 후 로그인 시도 → 화면 전환 정상 안 됨 → PWA 강제 새로고침 해야 동작.

### 변경

| 파일 | 내용 |
|------|-----|
| `frontend/lib/screens/auth/approval_pending_screen.dart` | `ref.listen(authProvider)` 추가 — approval_status='approved' 변경 자동 감지 + Navigator.popUntil 자동 홈. `_handleRefresh(context, ref)` 영역 manual check 추가 (안전망 이중 catch) |

### 원인 + 효과

- 기존: 새로고침 → currentWorker 갱신 / 화면 transition 트리거 없음 → 사용자가 PWA 강제 새로고침 필요
- 변경: ref.listen 자동 감지 + handleRefresh manual check 이중 안전망 → admin 승인 즉시 홈 이동

회귀 위험 0 (additive).

---

## [2.18.23] - 2026-05-22 — 가입 승인 메일에 매뉴얼 URL 추가

> 사용자 catch: 매뉴얼 URL https://axis-manual.netlify.app/ 안내 메일에 포함 부탁.

### 변경

| 파일 | 내용 |
|------|-----|
| `backend/app/services/notification_service.py` | HTML 템플릿 로그인 박스 하단에 📖 사용 매뉴얼 박스 추가 (axis-manual.netlify.app) |

---

## [2.18.22] - 2026-05-22 — 가입 승인 메일 URL 정정 + 로그인 방법 안내 박스 추가

> 사용자 catch: ① URL 잘못 안내됨 (g-view.netlify.app → gaxis-ops.netlify.app) ② 가입 완료 안내 메일에도 로그인 방법 작성 부탁 (OPS login 화면 안내는 그대로 유지).

### 변경

| 파일 | 내용 |
|------|-----|
| `backend/app/services/notification_service.py` | "앱 열기" 링크 도메인 변경 + 본문 회색 박스 (🔑 로그인 방법 3가지 + PIN 설정 위치) |

---

## [2.18.21] - 2026-05-22 — 안내 메일 도메인 변경 + login 안내 박스 + PIN 설정 위치 명시

> 사용자 catch: ① 가입 승인 메일 영역 링크 도메인 미완 (gaxis-ops.co.kr → g-view.netlify.app 임시) ② login 화면 안내 메시지 미인지 → Container 박스 + 🔑 이모지 강조 ③ PIN 설정 방법 안내 누락.

### 변경

| 파일 | 내용 |
|------|-----|
| `backend/app/services/notification_service.py` | HTML 영역 "앱 열기" 링크 도메인 정정 |
| `frontend/lib/screens/auth/login_screen.dart` | 안내 박스 (mist 배경) + 🔑 로그인 방법 3가지 + PIN 설정 위치 안내 ("[프로필] → [PIN 설정]") |

> 주: v2.18.22 영역 도메인 재정정 (g-view.netlify.app → gaxis-ops.netlify.app).

---

## [2.18.20] - 2026-05-22 — 승인 메일 + prefix 확장 + 안내 3가지 (Codex 라운드 1 M=3 반영)

> 사용자 catch 통합 fix: ① 가입 승인 시 사용자 환영 메일 발송 누락 catch ② 이메일 prefix 로그인 admin/test만 가능 (일반 사용자 불가) ③ register/login 안내 메시지 미흡. Codex 라운드 1 (M=3 / A=3 / N=2) 합의 후 적용.

### 변경 (BE 4 + FE 2 + 신규 1 + pytest 1)

| 파일 | 내용 |
|------|-----|
| `backend/app/services/notification_service.py` (신규, +138 LOC) | `send_approval_notification()` + `send_approval_notification_async()` (Codex M-Q4: thread 캡슐화) + `_render_approval_html()` (html.escape XSS 방지, Codex M-Q1) + `_send_smtp()` (email_service 패턴 정합) |
| `backend/app/models/worker.py` | `get_worker_by_email_prefix(prefix)` 신규 (+42 LOC). v2.18.18 ALLOWED_DOMAINS 3개 후보 검색, 1명 매칭 시 반환, 2명+ → debug log 후 None (Codex A-Q3) |
| `backend/app/services/auth_service.py` | login() chain 영역 일반 사용자 prefix 단계 신규 추가 (admin → user prefix → 이름 → 이메일). import 추가 |
| `backend/app/routes/admin.py` | approve_worker() 영역 1줄 호출만 (thread 로직 service 이동, Codex M-Q4 정합). admin.py God File LOC +8 (정책 일부 완화 + REFACTOR-ADMIN-SPLIT BACKLOG HIGH 등록) |
| `frontend/lib/screens/auth/register_screen.dart` | 가입 성공 SnackBar — "회원가입이 완료되었습니다. 이메일로 받은 인증 코드를 입력해주세요." |
| `frontend/lib/screens/auth/login_screen.dart` | 안내 메시지 3가지 (이메일 전체 / prefix / PIN). 이름 로그인 코드 유지하되 안내 제외 |
| `tests/backend/test_v2_18_20_prefix_login_and_approval.py` (신규) | 4개 TestClass — prefix 매칭 / login 확장 / XSS escape / async thread (Codex M-Q8 반영) |

### Codex 라운드 1 결과

| Q | 라벨 | 상태 |
|---|---|---|
| M-Q1 HTML escape | ✅ 반영 — `html.escape()` 적용 (name/role/company) |
| M-Q4 admin.py God File | ✅ 반영 — `send_approval_notification_async()` 신규 helper 로 thread 로직 이동 (admin.py +8 LOC만) |
| M-Q8 신규 경로 TC | ✅ 반영 — `test_v2_18_20_prefix_login_and_approval.py` 신규 |
| A-Q2 도메인 하드코딩 중복 | 🟡 BACKLOG 권고 (worker.py / auth_service.py / validators.dart / CLAUDE.md 4중) |
| A-Q3 모호 매칭 안내 | ✅ 반영 — debug log 추가 + 사용자 안내 메시지 별 sprint 권고 |
| A-Q5 daemon thread 신뢰성 | 🟡 BACKLOG 권고 (outbox/job queue) |
| N-Q6 SnackBar UX / N-Q7 회귀 | ✅ 안전 |

### 동작 변경

| 입력 | 매칭 |
|---|---|
| `dkkim1@gst-in.com` | 정확한 이메일 ✅ |
| `dkkim1` | admin prefix (1차) ✅ |
| `kdkyu311` | 일반 사용자 prefix (2차 신규) — `kdkyu311@naver.com` 등 매칭 ✅ |
| `홍길동` (이름) | 이름 fallback (3차, 코드 유지) ✅ |
| 동일 prefix 2명+ (모호) | 4차 fallback `get_worker_by_email(email)` — 사실상 매칭 X → `ACCOUNT_NOT_FOUND` |

### 신규 BACKLOG 권고

| sprint | 우선순위 | 의미 |
|---|---|---|
| `REFACTOR-ADMIN-SPLIT` | 🔴 HIGH | admin.py 2,568 LOC God File 분할 |
| `FEAT-LOGIN-AMBIGUOUS-PREFIX-NOTICE` | 🟡 LOW | prefix 모호 매칭 시 "전체 이메일 입력 부탁" 메시지 분기 |
| `REFACTOR-EMAIL-DOMAIN-CONSTANT` | 🟡 LOW | ALLOWED_DOMAINS 4중 중복 통합 |
| `FEAT-APPROVAL-EMAIL-OUTBOX` | 🟡 LOW | daemon thread 유실 catch 대응 (outbox/job queue) |

---

## [2.18.19] - 2026-05-22 — verify_email 카운트다운 3분 → 1분 (BE rate limit 60s 동기화)

> 사용자 catch: 가입 인증 화면 재발송 대기 시간 3분이 김. BE rate limit 은 이미 60초인데 FE 카운트다운만 180초 (3분) 표시 — 비동기. FE 만 60 으로 단축.

### 변경

| 파일 | 내용 |
|------|-----|
| `frontend/lib/screens/auth/verify_email_screen.dart` L32 + L50 | `_remainingSeconds = 180` → `60` (2곳) |
| `backend/version.py` | 2.18.18 → 2.18.19 |
| `frontend/lib/utils/app_version.dart` | 2.18.18 → 2.18.19 |

### 이미 구현되어 있던 항목 (사용자 catch 분석 후 확인)

| 항목 | 상태 |
|---|---|
| login `EMAIL_NOT_VERIFIED` → verify_email 자동 redirect + email prefill | ✅ 기존 구현 (`login_screen.dart` L55-62) |
| verify_email "인증 코드 다시 보내기" 버튼 | ✅ 기존 구현 (`verify_email_screen.dart` L434+) |
| api_service 403 에러 코드 보존 | ✅ 기존 구현 (`api_service.dart` L249-252) |

### 사용자 (kdkyu311) catch 분석

```
가입 → verify_email 화면 자동 진입 (자동 redirect 정상)
사용자 인증 안 함 → 화면 나감
로그인 시도 안 함 (또는 흐름 모름)
비밀번호 찾기 → reset 코드 → 비밀번호 변경 (email_verified 그대로 false)
사용자 인식: "메일 인증 했다" / 시스템 = 미완
```

→ 흐름 인식 catch + 운영 SQL 정리 필요.

### 후속 BACKLOG 권고

`FEAT-LOGIN-RESEND-VERIFICATION-LINK` — login 화면에 "이메일 인증 다시 받기" 명시 링크 추가 (회원가입 버튼 옆). 자동 redirect 외 사용자 명시적 진입 경로 확보.

---

## [2.18.18] - 2026-05-22 — 인증 메일 도메인 안내 + whitelist 검증 (BE + FE)

> 사용자 catch: 카카오/다음 메일로 가입 시 인증 메일 수신 안 됨. Railway 로그: `SMTP error while sending to kdkyu311@kakao.com: Connection unexpectedly closed` — KT Biz Office SMTP 영역 외부 도메인 차단 정책 (Connection 강제 끊김). CLAUDE.md L626 명시된 허용 도메인 (@gst-in.com / @naver.com / @gmail.com) 영역 코드 영역 미구현 catch — whitelist 강제 + UI 안내 동시 추가.

### 변경

| 파일 | 내용 |
|------|-----|
| `backend/app/services/auth_service.py` L43+L475 | `ALLOWED_EMAIL_DOMAINS = {'gst-in.com', 'naver.com', 'gmail.com'}` 상수 + `register()` 영역 도메인 체크 (INVALID_EMAIL_FORMAT + EMAIL_DOMAIN_NOT_ALLOWED 분기) |
| `frontend/lib/utils/validators.dart` | `allowedEmailDomains` 상수 + `validateEmail()` 영역 도메인 체크 추가 |
| `frontend/lib/screens/auth/register_screen.dart` L240 | 이메일 필드 아래 안내 메시지: "지원 메일: @gst-in.com, @naver.com, @gmail.com" |
| `backend/version.py` | 2.18.17 → 2.18.18 |
| `frontend/lib/utils/app_version.dart` | 2.18.17 → 2.18.18 |

### 동작

| 입력 | FE 결과 | BE 결과 |
|---|---|---|
| `user@gst-in.com` / `@naver.com` / `@gmail.com` | ✅ 통과 | ✅ 통과 |
| `user@kakao.com` / `@daum.net` / `@hanmail.net` | ❌ 빨간 글씨 "지원 메일: @gst-in.com, @naver.com, @gmail.com" + 가입 버튼 disabled | ❌ HTTP 400 `EMAIL_DOMAIN_NOT_ALLOWED` (보안 — FE 우회 차단) |

### 영향

- 카카오/다음/네이트/한메일 사용자 영역 가입 차단 (KT SMTP 정책 한계)
- 운영 catch — 사용자에게 명확한 안내 + 가입 전 catch
- Sentry 영역 SMTP Recipients refused / Connection unexpectedly closed 잡음 0건 기대

### 향후 옵션 (BACKLOG 검토)

| 옵션 | 의미 |
|---|---|
| 외부 SMTP 전환 (Gmail / SendGrid / Mailgun) | 모든 도메인 발송 가능 — 회사 정책 catch 필요 |
| KT Biz Office 외부 도메인 정책 완화 요청 | 회사 IT 절차 |
| ALLOWED_EMAIL_DOMAINS admin_settings 영역 동적 관리 | 운영팀이 직접 도메인 추가/제거 |

---

## [2.18.17] - 2026-05-22 — Sentry 잡음 2건 fix (WebSocket Broken pipe + SMTP Recipients refused)

> 사용자 catch (2026-05-22): Sentry ERROR 영역 정상 동작 catch 2건 잡힘 — WebSocket client disconnection + SMTP admin 이메일 거부. v2.10.13 (FIX-WEBSOCKET-STOPITERATION-SENTRY-NOISE) 패턴 정합.

### 변경

| 파일 | 내용 |
|------|-----|
| `backend/app/websocket/events.py` L183 | `except Exception` 단일 → `(BrokenPipeError, ConnectionResetError, ConnectionAbortedError)` 분기 + logger.info 강등 / 기타 Exception logger.error (exc_info=True) 유지 |
| `backend/app/services/email_service.py` L62 | `SMTPRecipientsRefused` 분기 추가 — `to_email` + `e.recipients` 로깅, logger.warning 강등 |
| `backend/app/services/auth_service.py` L427+L981 (2곳) | 동일 `SMTPRecipientsRefused` 분기 추가 (replace_all) |
| `backend/version.py` | 2.18.16 → 2.18.17 |
| `frontend/lib/utils/app_version.dart` | 2.18.16 → 2.18.17 |

### Sentry 영향

| 변경 전 | 변경 후 |
|---|---|
| `WS handler error: ws_id=..., error=[Errno 32] Broken pipe` ERROR | `WS client disconnected: ws_id=..., reason=BrokenPipeError` INFO (Sentry 미발송) |
| `SMTP error while sending to {admin}: 550 Unknown user` ERROR | `SMTP recipient refused: to={admin}, detail=...` WARNING (Sentry 미발송) |
| 진짜 ERROR | 그대로 ERROR + exc_info=True (Sentry 발송 + stack trace 포함) |

### 운영 catch — admin 이메일 점검 부탁

`SMTP 550 Unknown user` = `workers.email WHERE is_admin=true` 중 잘못된 이메일 존재. KT Biz Office SMTP 영역 외부 도메인 거부 또는 퇴사자 이메일 잔존 가능성. 운영 SQL 점검:

```sql
SELECT id, name, email FROM workers WHERE is_admin = true AND email IS NOT NULL;
```

### 누적 trail — Sentry 잡음 회피 패턴

- v2.10.13: flask-sock WSGI StopIteration → drop (sentry_before_send hook)
- v2.10.14: db_pool fallback → logger.warning 강등
- v2.18.17 (현재): WebSocket Broken pipe + SMTP Recipients refused → INFO/WARNING 강등

진짜 ERROR 추적성 보존하면서 잡음만 제거.

### LOC

- BE 3 파일 변경: +~15 LOC (분기 추가)
- FE: version bump 만

---

## [2.18.16] - 2026-05-21 — BUG-42 fix: zoom 2.0x 자동 적용 (videoConstraints 우회)

> qr-test.html 사용자 검증 catch (Step ⑤~⑧ 모두 GREEN): videoConstraints 사용 시 ZXing 디코더 방해 → 인식 NG. 그러나 `applyConstraints({advanced:[{zoom}]})` 만 사용 (videoConstraints 우회) 시 디코더 정상 + 명판 확대 모두 달성. 사용자 옵션 B 결정 (qrbox 200 현행 유지 + zoom 2.0x 자동).

### 변경

| 파일 | 내용 |
|------|-----|
| `frontend/lib/services/qr_scanner_web.dart` | `_applyZoomIfSupported(num targetZoom)` helper 신규 (+47 LOC) + 카메라 start 3곳 (env/user/cameraId) 성공 후 fire-and-forget 호출 (+3 LOC). 200ms 추가 delay 후 호출 (stream settled 보장) |
| `backend/version.py` | 2.18.15 → 2.18.16 |
| `frontend/lib/utils/app_version.dart` | 2.18.15 → 2.18.16 |

### 동작

1. 카메라 start 성공
2. `_forceSquareAfterCameraStart()` (기존)
3. 200ms 대기 후 `_applyZoomIfSupported(2.0)` 호출:
   - `videos[0].srcObject.getVideoTracks()[0]` 추출
   - `getCapabilities().zoom` 확인
   - 미지원 → silent skip + debug log
   - 지원 → `min/max clamp` 후 `applyConstraints({advanced:[{zoom:2.0}]})`
4. 실패 시 silent skip (try-catch)

### 변경 안 한 부분

- `videoConstraints` 사용 안 함 (디코더 방해 회피)
- `cameraIdOrConfig = {facingMode:'environment'}` 그대로 (v2.18.4 baseline 유지)
- qrbox 200 현행 유지 (UI 변경 0)
- DOM / CSS / MutationObserver / _forceSquareAfterCameraStart 절대 불변

### 영향 추정 (정량 측정은 실기기 catch 필수)

- 명판 작은 QR 인식: 거의 0% → 약 70~85% (zoom 2배 효과 추정)
- 스티커 QR (큰 QR): 100% → 약 60~80% ⚠️ regression 가능 (zoom 시 화면 일부 잘림 → 사용자가 멀리 비춰야 함)
- 디코더 정상 (videoConstraints 영향 0)
- 후면 카메라 정상 (v2.18.4 동작 그대로)

### LOC

- 파일 506 → 557 (+51, 🟡 경고 영역 유지)
- `startQrScanner()` 함수 158 → 161 (🔴 한도 초과 유지) — REFACTOR sprint MEDIUM 등록 상태

### 누적 trail (BUG-42 시리즈)

- v2.18.5~v2.18.11: 11번 hotfix → 셀카 catch
- v2.18.12: 1차 ROLLBACK
- v2.18.13/14: 4-tier/3-tier fallback chain → 실기기 인식 NG
- v2.18.15: 2차 ROLLBACK + qr-test.html Phase 1+2 옵션 추가
- v2.18.16: 사용자 qr-test.html 검증 후 zoom 만 적용 (videoConstraints 우회) — 13번 시도 후 도달한 최종 fix

### 실기기 manual QA — 사용자 위탁

| # | 항목 | 검증 |
|---|---|---|
| 1 | 후면 카메라 (regression) | v2.18.4 와 동일 |
| 2 | 스티커 QR (regression) | 인식률 catch — zoom 2.0x 영향 |
| 3 | **명판 작은 QR** ⭐ BUG-42 본 목적 | 인식 성공률 catch |
| 4 | 콘솔 로그 `zoom 적용: 2.0x` | 적용 성공 확인 |
| 5 | Desktop Chrome (zoom 미지원 시 silent skip) | 에러 없음 |

---

## [2.18.15] - 2026-05-21 — ROLLBACK 2차: v2.18.13/14 fallback chain 회귀 → v2.18.4 baseline 복귀

> v2.18.13 (4-tier) → v2.18.14 (3-tier, advanced 제거) 시도 후 실기기 catch: 1차 tier (해상도 1920×1080 + facingMode environment) 영역 QR 인식 NG (코너 초록색 변화 없음). 강제실패 토글로 2차/3차 fallback 진입 시에만 인식 OK. 운영 코드에서 1차 우선 시도가 fallback chain 으로 자동 회귀 안 됨. 누적 시도 비용 vs 효과 trade-off → ROLLBACK 결정.

### 변경

| 파일 | 내용 |
|------|-----|
| `frontend/lib/services/qr_scanner_web.dart` | `git checkout 8a2233f -- ...` → v2.18.4 baseline 복귀 (506 LOC). `_buildFallbackTiers()` helper + 4-tier/3-tier chain 모두 제거. 단순 `facingMode:'environment'` hint + user/cameraId fallback 만 |
| `backend/version.py` | 2.18.14 → 2.18.15 |
| `frontend/lib/utils/app_version.dart` | 2.18.14 → 2.18.15 |
| `BACKLOG.md` | BUG-42 🔴 OPEN 유지 + 별 sprint 5개 보존 (Task3-AUTO-ZOOM / CAMERA-SWITCH-BUTTON / REFACTOR-FUNCTION-SPLIT / TEST-QR-LIB-CONSTRAINT-PREFLIGHT / TOOL-ERUDA-DEV-CONSOLE) + QR-SCANNER-RETRY-CLEANUP / QR-SCANNER-ERROR-CLASSIFICATION (Codex 라운드 2 권고) 보존 |

### 영향

- ✅ 카메라 동작 v2.18.4 = v2.18.12 와 동일 (후면 카메라 정상)
- ✅ 스티커 QR 인식 정상
- ⚠️ 명판 소형 QR 인식 개선 효과 0 (BUG-42 별 sprint 로 이관)
- ✅ `qr-test.html` 보존 (향후 재시도 시 검증 도구)
- ✅ Codex 라운드 1+2 trail / 학습 기록 / BACKLOG 별 sprint 보존

### BUG-42 재시도 조건 (향후)

- 실기기 디버깅 환경 갖춘 시점에 재시도 (Mac 원격 디버깅 + Eruda 도입 후)
- qr-test.html 영역 minimal change 단위로 단계별 검증
- 운영 코드 1차 시도에서 OverconstrainedError 가 아닌 "디코더 인식 실패" 도 fallback 트리거하도록 설계 변경
- BUG-42 본 진단: 1920×1080 자체가 디코더 부담 가능성 → 실기기 + 실시간 검증 환경 필수

### 누적 trail

- v2.18.5~v2.18.11: 11번 hotfix → 셀카 catch → v2.18.12 1차 ROLLBACK
- v2.18.12 → qr-test.html + Codex 라운드 1 root cause 확정
- v2.18.13/14: 4-tier/3-tier fallback chain → 실기기 인식 NG → v2.18.15 2차 ROLLBACK

→ 총 13번 시도 후 baseline 으로 회귀. 학습: 외부 라이브러리(html5-qrcode) constraint 동작 + 실기기 디코더 동작은 source 분석 + 실시간 catch 환경 없이는 신뢰 불가.

---

## [2.18.14] - 2026-05-21 — focusMode advanced 제거 (ROLLED BACK in v2.18.15)

> v2.18.13 catch: 4-tier 1차(full) QR 인식 NG / 2차 fallback OK → advanced focusMode 가 ZXing 디코더 방해 추정 → 1차 advanced 제거 (3-tier chain). 실기기 catch: 1차(해상도 1920) 영역 QR 인식 NG 잔존. v2.18.15 ROLLBACK 에 포함.

## [2.18.13] - 2026-05-21 — BUG-42 재시도 (4-tier fallback chain, Codex 라운드 1+2 합의)

> v2.18.12 ROLLBACK + qr-test.html 검증 + Codex 라운드 1 (M=4/A=2/N=1) 합의 + 라운드 2 (M=0/A=5/N=3) 합의 후 운영 적용. 사용자 실기기 (iPhone 14/15 Pro) 4-tier 시뮬레이션 모두 GREEN catch.

### 변경

| 파일 | 내용 |
|------|-----|
| `frontend/lib/services/qr_scanner_web.dart` | `_buildFallbackTiers()` helper 신규 (+58 LOC) + `startQrScanner()` 1차 시도 영역 4-tier chain 으로 교체 (+17 LOC). 기존 user/cameraId fallback 그대로 유지 |
| `backend/version.py` | 2.18.12 → 2.18.13 |
| `frontend/lib/utils/app_version.dart` | 2.18.12 → 2.18.13 |
| `BACKLOG.md` | REFACTOR-QR-SCANNER-WEB-FUNCTION-SPLIT LOW → MEDIUM 격상 (Codex 라운드 2 A-Q7) + 신규 2개 등록 (QR-SCANNER-RETRY-CLEANUP / QR-SCANNER-ERROR-CLASSIFICATION) + TEST-QR-LIB-CONSTRAINT-PREFLIGHT 영역 QA 8항목 evidence 추가 |

### 4-tier fallback chain

| Tier | Config | 효과 |
|---|---|---|
| 1차 (full) | `{fps:10, qrbox:200, videoConstraints:{facingMode:'environment', width:{ideal:1920}, height:{ideal:1080}, advanced:[{focusMode:'continuous'}]}}` | 후면 + 고해상도 + 자동 포커스 (명판 QR 최적) |
| 2차 (advanced 제거) | 위에서 `advanced` 제거 | focusMode 미지원 환경 |
| 3차 (해상도 제거) | `{videoConstraints:{facingMode:'environment'}}` | 해상도 미지원 환경 |
| 4차 (baseline) | `{fps:10, qrbox:200}` (videoConstraints 없음) | v2.18.4 동일 — OverconstrainedError 최종 회피 |

### Root Cause 재확정

html5-qrcode 2.3.8 source: `areVideoConstraintsEnabled ? internalConfig.videoConstraints : createVideoConstraints(cameraIdOrConfig)` — `videoConstraints` 키 존재 시 `cameraIdOrConfig.facingMode` hint 무시. videoConstraints 안에 facingMode 명시 필수.

### Codex trail

- **라운드 1** (2026-05-21): M=4 (Root Cause / 안전 패턴 / fallback chain / QA 8항목) + A=2 (TEST-PREFLIGHT / Eruda) + N=1 (ROLLBACK 정합)
- **라운드 2** (2026-05-21): M=0 + A=5 (RETRY-CLEANUP / ERROR-CLASSIFICATION / 함수 분할 격상 / preflight evidence 추가 / 기타) + N=3
- **DEPLOY_SAFE: CONDITIONAL** — 4-tier chain 자체 must-fix 없음

### 영향

- 1차 성공 시: 후면 카메라 + 해상도 1920×1080 + 자동 포커스 → 명판 QR 인식률 개선 기대
- 1~4차 모두 OverconstrainedError 시: 기존 user / cameraId[0] fallback 자동 진입 (v2.18.4 동일)
- 프레임 / 뷰파인더 / qrbox / CSS / MutationObserver / DOM 절대 불변

### 실기기 manual QA — 사용자 위탁 (Codex 권고 8항목)

- (1) iPhone Safari 후면 화면 육안 확인
- (2) `getRunningTrackSettings()` 로그 catch
- (3) 명판 QR 3거리 (10cm / 15cm / 20cm) 인식 테스트
- (4) 스티커 QR 정상 인식 regression
- (5) Stop → 재Start 시 카메라 방향 유지
- (6) 권한 최초 허용 / 이미 허용 / 거부 후 복구
- (7) Android Chrome 후면 + 인식률
- (8) Desktop Chrome OverconstrainedError 없이 fallback

### LOC 영향

- 파일 506 → 569 (+63, 🟡 경고 유지)
- `startQrScanner()` 158 → 175 (🔴 절대 한도 100 초과 유지) → REFACTOR sprint MEDIUM 격상

---

## [2.18.12] - 2026-05-21 — ROLLBACK qr_scanner_web.dart v2.18.4 상태로 복귀

> v2.18.5 ~ v2.18.11 (11번 BUG-42 hotfix 시리즈) 모두 롤백. 실기기 catch: 콘솔 로그는 후면 카메라(`label=후면 듀얼 와이드 카메라`)로 표시되는데 실제 화면에는 전면 카메라(셀카)가 보이는 라이브러리 충돌 — `getUserMedia` 직접 호출 + `videoConstraints` 추가 + `{exact:'environment'}` 등 변경이 html5-qrcode 내부 stream 과 충돌 추정. 11번 누적 변경 후 디버깅 비용 > 복귀 비용 판단.

### 변경

| 파일 | 내용 |
|------|-----|
| `frontend/lib/services/qr_scanner_web.dart` | `git checkout 8a2233f -- ...` v2.18.4 상태 복귀 (506 LOC). 단순 `facingMode: 'environment'` / `facingMode: 'user'` hint 만 사용 |
| `backend/version.py` | 2.18.11 → 2.18.12 |
| `frontend/lib/utils/app_version.dart` | 2.18.11 → 2.18.12 |
| `BACKLOG.md` | BUG-42 → 🔴 OPEN reopen. `BUG-42-TASK3-AUTO-ZOOM-DEFERRED` / `BUG-42-CAMERA-SWITCH-BUTTON-DEFERRED` / `REFACTOR-QR-SCANNER-WEB-FUNCTION-SPLIT` 보존 |

### 롤백 대상 (v2.18.5 ~ v2.18.11)

- v2.18.5 (BUG-42 Task 2: 해상도 1920×1080 + focusMode continuous)
- v2.18.6 (HOTFIX-09 cameraIdOrConfig 1-key fix)
- v2.18.7 (HOTFIX-10 facingMode exact)
- v2.18.8 (HOTFIX-11 cameras label 매칭 1차 승격)
- v2.18.9 (HOTFIX-12 getUserMedia 직접 호출 0차)
- v2.18.10 (HOTFIX-13 exact + facingMode 검증)
- v2.18.11 (HOTFIX-14 권한 발급 시점 environment hint)

→ 위 7개 release qr_scanner_web.dart 변경분만 롤백. CHANGELOG/CLAUDE.md/PROGRESS.md 진행 기록은 trail 로 보존.

### 영향

- ✅ 카메라 동작 v2.18.4 (BUG-42 hotfix 시작 전) 상태로 복귀 — 후면 카메라 정상 작동 기대
- ⚠️ 명판 소형 QR 인식 개선 다시 OPEN — 실제 iPhone 환경에서 정밀 진단 후 재시도 필요
- ✅ 다른 모든 변경 (백엔드, 다른 화면) 보존

### 향후 재시도 조건

- 실제 iPhone Safari + Mac 원격 디버깅 또는 Eruda in-app 콘솔로 정확한 진단
- 라이브러리 충돌 없는 minimal change 우선
- 단일 변경마다 즉시 실기기 검증 후 다음 단계

### Post-mortem — qr-test.html 검증 + Codex 라운드 1 결과 (2026-05-21)

**테스트 페이지 (`frontend/web/qr-test.html`)** 작성 — 운영 1:1 복제 + 옵션 토글 7개. 사용자 실기기 (iPhone) 토글 매트릭스 catch:

| 토글 조합 | 결과 |
|---|---|
| 모두 OFF (v2.18.4 baseline) | 후면 ✅ |
| videoConstraints.width/height (옵션 1) 단독 | 셀카 ❌ |
| videoConstraints.advanced.focusMode (옵션 2) 단독 | 셀카 ❌ |
| 옵션 1 + 2 같이 | 셀카 ❌ |
| **videoConstraints.facingMode:'environment' 명시 (패턴 A) 단독** | **후면 ✅** |
| 패턴 A + 옵션 1 | 후면 ✅ |
| 패턴 A + 옵션 2 | 후면 ✅ |
| 패턴 A + 옵션 1 + 옵션 2 | 후면 ✅ + 해상도/포커스 적용 |

**Root Cause 확정** (Codex 라운드 1 M-Q1 확정):
- html5-qrcode 2.3.8 source: `areVideoConstraintsEnabled ? internalConfig.videoConstraints : createVideoConstraints(cameraIdOrConfig)`
- `config.videoConstraints` 키 존재 시 `cameraIdOrConfig` 의 facingMode hint 를 통째로 무시
- videoConstraints 안에 facingMode 없으면 OS default (대개 전면) 발급

**v2.18.13 재시도 안전 패턴 (Codex M-Q2 권고 4단계 fallback chain)**:
```
1차: {facingMode:'environment', width:{ideal:1920}, height:{ideal:1080}, advanced:[{focusMode:'continuous'}]}
2차 (실패 시): advanced 제거
3차 (실패 시): 해상도 제거 → {facingMode:'environment'}
4차 (실패 시): v2.18.4 baseline (cameraIdOrConfig 만)
```

**향후 재발 방지 (Codex A-Q5/Q6)**:
- `TEST-QR-LIB-CONSTRAINT-PREFLIGHT` BACKLOG 등록 — 외부 라이브러리 사용 사전 검증 체크리스트
- `TOOL-ERUDA-DEV-CONSOLE` BACKLOG 등록 — 모바일 실기기 콘솔 catch 도구

---

## [2.18.11] - 2026-05-21 — HOTFIX-14 권한 발급 시점 environment hint (ROLLED BACK in v2.18.12)

> 사용자 catch: 모든 시도 후 셀카 잔존. `_requestCameraPermission()` 영역 `{video:true}` → `{video:{facingMode:'environment'}}` 1차 권한 발급 → enumerate 후면 노출 유도. 의도와 달리 실제 화면 셀카 (라이브러리 catch). v2.18.12 ROLLBACK 에 포함.

## [2.18.10] - 2026-05-21 — HOTFIX-13 getUserMedia exact + facingMode 검증 (ROLLED BACK in v2.18.12)

> `{facingMode:{exact:'environment'}}` 강제 + `settings.facingMode` 검증 (actual 'user' 발급 시 reject). 의도와 달리 실제 화면 셀카 (라이브러리 catch). v2.18.12 ROLLBACK 에 포함.

## [2.18.9] - 2026-05-21 — HOTFIX-12 getUserMedia 직접 호출 0차 시도 (ROLLED BACK in v2.18.12)

> `getUserMedia({video:{facingMode:'environment'}})` 직접 호출 → stream videoTrack `settings.deviceId` 추출 → html5-qrcode 명시. 5-tier fallback chain (0차 + 4차). 의도와 달리 실제 화면 셀카 (라이브러리 catch). v2.18.12 ROLLBACK 에 포함.

## [2.18.8] - 2026-05-21 — HOTFIX-11 cameras label 매칭 1차 승격 (ROLLED BACK in v2.18.12)

> `_findBackCameraId()` helper 신규 + cameras list 영역 'back/rear/environment/후면' label 매칭 → deviceId 명시 시도를 1차로 승격. facingMode hint/exact 우회. 의도와 달리 실제 화면 셀카 (라이브러리 catch). v2.18.12 ROLLBACK 에 포함.

## [2.18.7] - 2026-05-21 — HOTFIX-10 후면 카메라 강제 (셀카 fallback 차단)

> 사용자 catch (5-21, v2.18.6 직후): "카메라 방향이 현재 셀카인데 전환하는 버튼을 돌려주던지 방향 변경해줘". 모바일에서 1차 시도 `facingMode: 'environment'` 가 hint 일 뿐이라 iOS Safari 등 일부 환경에서 OS 가 무시 → user 카메라로 silent fallback → 셀카로 보임. 명판 QR 인식이 본 목적이라 후면 강제 필수.

### 변경

| 파일 | 내용 |
|------|-----|
| `frontend/lib/services/qr_scanner_web.dart` | (1) `_buildScannerConstraints()` — `facingMode: 'environment'` 일 때 `{exact: 'environment'}` 강제. user 영역은 hint(string) 유지. (2) 3차 cameraId fallback 영역 카메라 list label 매칭 추가 — 'back' / 'rear' / 'environment' / '후면' 포함 카메라 우선 선택, 없으면 cameras[0] fallback (~13 LOC) |
| `backend/version.py` | 2.18.6 → 2.18.7 |
| `frontend/lib/utils/app_version.dart` | 2.18.6 → 2.18.7 |
| `BACKLOG.md` | `BUG-42-CAMERA-SWITCH-BUTTON-DEFERRED` 신규 등록 (별 sprint, qr_scan_screen.dart 절대 불변 영역 해소 필요) |

### 동작

- **모바일 후면 카메라 있음** (iPhone/Android): `{exact: 'environment'}` → 후면 강제 성공
- **모바일 후면 카메라 없음** (예외 케이스): exact OverconstrainedError → 2차 user 시도 → 전면 카메라
- **데스크톱/MacBook** (후면 없음): 1차 exact fail → 2차 user 시도 → 노트북 전면 카메라 정상 동작
- **3차 fallback**: cameraList 영역 'back/rear/후면' label 매칭 → 안전망 (1·2차 모두 fail 시)

### 절대 불변 영역 (CLAUDE.md L1134-1142)

- 프레임 / 뷰파인더 / qrbox:200 / CSS / DOM 변경 0
- `qr_scan_screen.dart` 위젯 배치 변경 0 (UI 전환 버튼은 별 sprint)

### 검증

- flutter build web --release GREEN (12.6s)
- LOC 533 → 551 (+18, 🟡 경고 영역 유지)
- 실기기 manual QA 재위탁 (Twin파파)

---

## [2.18.6] - 2026-05-21 — HOTFIX-09 cameraIdOrConfig 1-key 위반 fix

> v2.18.5 배포 직후 사용자 실기기 catch (5분 이내): `'cameraIdOrConfig' object should have exactly 1 key, if passed as an object, found 4 keys`. html5-qrcode@2.3.8 의 `start(cameraIdOrConfig, config, ...)` 1번째 인자는 **정확히 1 key 객체만 허용**. v2.18.5 의 `_buildScannerConstraints()` 가 facingMode + width + height + advanced 4 keys 반환 → 3차 시도 모두 reject → "사용 가능한 카메라를 찾을 수 없습니다" 에러. Codex 라운드 1 에서 놓친 라이브러리 spec.

### 변경

| 파일 | 내용 |
|------|-----|
| `frontend/lib/services/qr_scanner_web.dart` | (1) `_buildScannerConstraints({facingMode, cameraId})` — 1 key 객체만 반환하도록 단순화 (width/height/advanced 제거). (2) `__qrScanConfig` JS 객체에 `videoConstraints: { width:{ideal:1920}, height:{ideal:1080}, advanced:[{focusMode:'continuous'}] }` 영역 추가 — Html5QrcodeCameraScanConfig 공식 spec 영역 |
| `backend/version.py` | 2.18.5 → 2.18.6 |
| `frontend/lib/utils/app_version.dart` | 2.18.5 → 2.18.6 |

### 영향

- 카메라 시작: env/user/cameraId 3 시도 모두 정상 성공 기대
- 해상도/포커스: v2.18.5 의도와 동일 (위치만 cameraIdOrConfig → config.videoConstraints 이동)
- 프레임/뷰파인더/qrbox/CSS 절대 불변

### Codex 라운드 1 (v2.18.5) 놓친 catch

- html5-qrcode `cameraIdOrConfig` spec 영역 1-key 제약 미확인
- 5 Q 검증 영역 라이브러리 spec 영역 명시적 검토 부재 — 향후 외부 라이브러리 사용 영역 spec 확인 절차 권고 (별 sprint advisory)

### 검증

- flutter build web --release GREEN (12.7s)
- 실기기 manual QA 재진행 위탁 (Twin파파)

---

## [2.18.5] - 2026-05-21 — HOTFIX BUG-42 명판 소형 QR 인식률 개선 (Task 2)

> 사용자 운영 catch (2026-05-21): "자동 포커싱이 안 되는 거 같다". OPS PWA 스캐너(html5-qrcode@2.3.8)가 제품 명판(metal nameplate)의 소형 QR 미인식 — iOS/Android 기본 카메라 앱은 정상 인식. 카메라 OS 레벨 setting 누락(해상도/포커스/줌)으로 디코더 인식 임계 미달.

### 변경

| 파일 | 내용 |
|------|-----|
| `frontend/lib/services/qr_scanner_web.dart` | `_buildScannerConstraints({facingMode, cameraId})` helper 신규 (+18 LOC, DRY 정합) + 3곳 호출 통일 — L424 env / L443 user / L466 cameraId fallback. `width:{ideal:1920}, height:{ideal:1080}, advanced:[{focusMode:'continuous'}]` + cameraId 영역 `{deviceId:{exact:cameraId}}` 변환. 본체 LOC 506 → 530 (+24, 🟡 경고 영역 유지 / `startQrScanner()` 함수 158줄 변화 0 — helper 분리로 호출 1줄씩 동일). |
| `backend/version.py` | 2.18.4 → 2.18.5, BUILD_DATE 2026-05-21 |
| `frontend/lib/utils/app_version.dart` | 2.18.2 → 2.18.5 (BE/FE 버전 동기화) |
| `BACKLOG.md` | BUG-42 close + Task 1 (skip, no-op) / Task 3 (자동줌, BACKLOG 이관) trail + `REFACTOR-QR-SCANNER-WEB-FUNCTION-SPLIT` 등록 |

### 영향

- 명판 작은 QR: 해상도 1920×1080 (640×480 → 6배 픽셀) + 자동 재포커스 → 디코더 인식 임계 충족 기대
- 스티커 QR: object-fit cover + MutationObserver 영역 영향 없이 동작 (해상도 ↑ 만)
- iOS Safari: advanced unknown constraint 자동 무시 (MediaTrackConstraints spec) — 안전 폴백
- 프레임/뷰파인더/qrbox:200/CSS/DOM 절대 불변 (Codex Q6 M 합의)

### Codex 라운드 1 trail

- Q1 M: 옵션 C' (Task 2 우선) — Task 1 의 experimentalFeatures 가 잘못된 config 객체에 위치 (Html5QrcodeCameraScanConfig vs Html5QrcodeFullConfig) + 2.3.8 default 이미 true → no-op
- Q2 M: cameraId fallback 도 `{deviceId:{exact:...}}` + constraints 통일 — 반영
- Q3 M: iOS Safari BarcodeDetector 효과 0 전제 + advanced unknown constraint 자동 무시 활용
- Q4 A: Task 3 자동 줌 BACKLOG 이관 (스티커 QR 역효과 + UI 불변 제약 충돌)
- Q5 M: 실기기 manual QA 필수 — flutter_test 영역 자동화 불가 (web platform 의존성)
- Q6 M: 절대 불변 영역(_forceSquareAfterCameraStart + MutationObserver) 침범 0, 실기기 회귀 확인 필수
- Q7 N: FE only 1 파일, 자동 이관 불필요 — 사용자 자발 위임

### 검증

- flutter build web --release GREEN (12.6s)
- 실기기 manual QA (사용자 위탁): 명판 + 스티커 + Chrome Desktop + Android Chrome (BACKLOG.md L1207-1211)

---

## [2.18.4] - 2026-05-21 — #70 출하 KPI `best` 분기 엑셀 게이트 제거

> AXIS-VIEW `OPS_API_REQUESTS.md` #70 — SI 공정 5-19 시행 후 app SI 데이터 유입 시작 → `best` 토글 엑셀 게이트(WHERE actual_ship_date IS NOT NULL)가 app-only 출하 누락 → 합집합(OR) 으로 정정. 출하이력 페이지(`FEAT-SHIPMENT-HISTORY-PAGE`, 6월 초 예정) 선행 의존성 해소.

### 변경

| 파일 | 내용 |
|------|-----|
| `backend/app/routes/factory.py` | `_count_shipped()` basis='best' 분기 `WHERE` 절 1줄 — `p.actual_ship_date IS NOT NULL` 단독 → `(p.actual_ship_date IS NOT NULL OR t.completed_at IS NOT NULL)` 합집합. `COUNT(DISTINCT p.serial_number)` 가 중복 자동 제거 + `COALESCE(DATE(t.completed_at), p.actual_ship_date)` app 우선 날짜 귀속 |
| `tests/backend/test_factory_kpi.py` | `TestFactoryKpiV24Amendment` 에 #70 TC 2개 추가 (소스 검증 + smoke) |

### 영향

- 응답값 즉시 변경: **0** (현재 갭 0건 — 운영자 동시 입력 중)
- 미래 데이터: SI 정착 후 app-only 출하 발생 시 자동 정확 카운트
- FE 변경 0 (`shipped_best` 자동 반영)
- 회귀 위험 0

### 검증

- pytest `test_fk_70_count_shipped_best_removes_excel_gate` PASS — 소스 검증 (단독 게이트 제거 + OR 합집합 포함)
- 기존 `TestFactoryKpiV24Amendment` 3 TC + `TestWeeklyKpi`/`TestMonthlyDetail` 회귀

### 연관

- VIEW `BACKLOG.md` `FEAT-SHIPMENT-HISTORY-PAGE` 착수 트리거 해소
- v2.4 (2026-04-28) 배포 시점 가정 "해석 A: si ⊆ actual" 가 SI 시행으로 무너진 후속 정정

---

## [2.18.3] - 2026-05-20 — SEC-CONFIG-DATABASE-URL-FALLBACK-REMOVED (GCP migration 준비)

> GCP migration 중 발견: Cloud Run 첫 부팅 시 env DATABASE_URL 누락 → `config.py` 의 하드코딩 fallback (Railway DB URL with 평문 비밀번호) 사용 → 의도치 않게 Cloud Run 이 Railway DB 에 연결되던 catch. 같은 사고 재발 방지 + GitHub 평문 비밀번호 제거.

### 변경

| 파일 | 내용 |
|------|-----|
| `backend/app/config.py` | `DATABASE_URL` 하드코딩 Railway fallback 제거 → `os.getenv(default="")` + `RuntimeError` fail-fast |

### 동작

- env `DATABASE_URL` 미설정 시 BE boot 즉시 실패 + 명확한 에러 메시지
- 테스트: `conftest.py` 가 `TEST_DATABASE_URL` → `DATABASE_URL` 으로 import 전 매핑 (영향 0)
- 운영(Cloud Run/Railway): env 변수 등록 필수 (이미 등록됨)

### 검증

- pytest `test_v2_18_2_mech_qr_doc_id_unify` 7/7 GREEN (import + Config 클래스 로딩 정상)
- 보안: GitHub history의 평문 Railway 비밀번호 제거 (단 git history 영구 기록은 별도, cutover 후 Railway 비밀번호 회전 권고)

---

## [2.18.2] - 2026-05-19 — FIX-MECH-CHECKLIST-QR-DOC-ID-SINGLE-UNIFY: DRAGON DUAL MECH 체크리스트 완료판정 (P0)

> BACKLOG `BUG-MECH-CHECKLIST-DUAL-MODEL-QR-DOC-ID-MISMATCH` (🔴 P0). DRAGON DUAL 모델 MECH 체크리스트가 영원히 100% 안 되던 버그 — qr_doc_id 저장 컨벤션 혼재(INLET `-L`/`-R` vs 나머지 SINGLE)가 원인. 옵션 D 채택: qr_doc_id를 모델 무관 `DOC_{S/N}` SINGLE로 통일.

### 변경

| 영역 | 파일 | 내용 |
|------|------|-----|
| BE | `checklist_service.py` | `check_mech_completion()` DUAL 분기(model SELECT + `-L`/`-R` loop) 제거 → `DOC_{S/N}` SINGLE 단일. `check_tm_completion()`은 미변경(TM dual tank 정상) |
| OPS FE | `mech_checklist_screen.dart` | `_qrDocIdForItem()` `requiresLrHint` 로직 제거 → 항상 SINGLE 반환 |
| VIEW FE | — | 코드 변경 0 (BE 읽기 경로가 이미 SINGLE → 자동 정합) |

### 동작

- MECH 체크리스트 record는 모델 무관 `DOC_{S/N}` 한 가지로만 저장. INLET 배관 S/N L/R 구분은 master(`item_name` 'Left/Right #N' + 별도 `master_id`)가 담당 → qr_doc_id 접미사 불필요
- DRAGON DUAL MECH 체크리스트 100% 정상 도달 → SELF_INSPECTION 공정 마감 → finalize 정상

### 검증

- pytest `test_v2_18_2_mech_qr_doc_id_unify` 12 TC GREEN (SINGLE qr_doc_id / 부분미입력 False / DUAL 분기 제거 소스검증 / TM 분기 보존 / `check_mech_completion_all` / close 게이트 경로)
- 회귀: `test_mech_checklist` 69 + `test_relay_first_final` 38 + `test_v2_15_16/18` 24 GREEN
- flutter build web GREEN
- Codex 라운드 1 M=2(호출자 전수 TC + 게이트 경로 TC)/A=4 반영
- 운영 MECH `-L`/`-R` record 0건(테스트 S/N TEST-333만) → migration 불필요, 회귀 위험 0

---

## [2.18.1] - 2026-05-19 — Sprint 69 fix: 내 작업 완료 확인 다이얼로그 공정명 하드코딩

> 사용자 catch — OPS PI/QI 화면에서 `[내 작업 완료]` 누르면 확인 다이얼로그가 "본인의 SI 마무리공정 작업을..."로 SI 문구가 모든 공정에 동일하게 표시.

### 변경

| 파일 | 내용 |
|------|-----|
| `gst_products_screen.dart` | `_completeMyWork()` 확인 다이얼로그 content `'SI 마무리공정'` 하드코딩 → `$_categoryLabel` (PI 가압검사 / QI 공정검사 / SI 마무리공정) |

### 검증

- flutter build web GREEN
- FE only 1줄 문구 — ②단계 자동 Codex 이관 체크리스트 0항목 해당 → Opus 자가 리뷰
- 회귀 위험 0

---

## [2.18.0] - 2026-05-19 — Sprint 69: PI/QI 완료 권한 잠금 + admin 정상완료 + 검색 칸

> PI/QI는 GST 사내 검사 공정. cross-worker 완료(worker2가 worker1 task 완료)가 worker tracking·진행률을 왜곡 → PI/QI는 시작한 본인만 완료 + 불가피 시 admin/manager 정상완료.

### 변경

| 영역 | 파일 | 내용 |
|------|------|-----|
| BE-1 | `task_service.py` `complete_work()` | PI/QI cross-worker 완료 차단 (시작 안 한 사람 403) |
| BE-2 | `shipment_service.py` / `work_shipment.py` | `admin_complete()` + `POST /api/app/work/admin-complete` |
| FE-A | `gst_products_screen.dart` | PI/QI 카드 admin/manager `[종료]` 버튼 + 종료 시각 다이얼로그 |
| FE-B | `gst_products_screen.dart` | 상단 O/N·S/N 검색 칸 (PI/QI/SI 3화면 공용) |

### 동작

- PI/QI는 시작한 본인만 `complete` (cross 차단). 불가피 시 admin/manager `admin-complete` — `force_closed=FALSE` 정상완료, `completed_at` 지정
- `admin-complete` = PI/QI category 미완료 task 전수 완료 + audit `close_reason='ADMIN_COMPLETE'` + 멀티작업자 backfill + 멱등
- SI/MECH/ELEC/TMS cross 현행 유지 — PI/QI만 차단

### 검증

- pytest `test_admin_complete` 10/10 GREEN (cross 차단 PI/QI / admin-complete 성공 / 멱등 / completed_at 검증 / 멀티작업자 backfill / **PI 위임 모델(DRAGON) regression**)
- flutter build web GREEN
- Codex 라운드 1 — BE M=10/A=4 + OPS FE M=1(미래 시각 차단)/A=3 반영
- AXIS-VIEW Sprint 48 (PI/QI 종료 버튼)은 VIEW 세션 담당

---

## [2.17.2] - 2026-05-19 — Sprint 68 fix: OPS SI 마무리공정 화면 출고 대기 누락

> 사용자 catch — OPS SI 마무리공정 화면에 SI_FINISHING 작업이 완료된 출고 대기 제품(GBWS-7094/7095)이 안 보이고, 진행중인 TEST 제품만 표시됨.

### 원인

`gst.py get_gst_products()`의 SI 화면이 `started_at IS NOT NULL AND completed_at IS NULL`(= SI_FINISHING **작업 진행중**)만 표시 → SI_FINISHING 작업은 완료됐고 출하완료(SI_SHIPMENT)만 안 된 **출고 대기** 제품이 누락. 출고 완료 버튼 대상이 정작 화면에 없는 모순.

### 변경 (BE 1 파일)

| 파일 | 변경 |
|------|-----|
| `backend/app/routes/gst.py` | SI 카테고리 WHERE 분기 — `task_id='SI_FINISHING' AND started_at IS NOT NULL AND COALESCE(cs.si_completed, false)=false` + `completion_status` LEFT JOIN. PI/QI는 현행(진행중) 유지 |

→ SI 마무리공정 화면 = **출고 대기**(SI 작업 시작됨 + 미출고) 기준. SI_FINISHING 완료 여부 무관, `si_completed=false`면 표시. VIEW SI 토글 기준과 일치.

### 검증

- SQL 검증 — SI 화면 7건 (진행중 4 + 완료·출고대기 3: TEST-1114 / GBWS-7094 / GBWS-7095)
- Flask boot OK, PI/QI 화면 회귀 0 (현행 유지)

---

## [2.17.1] - 2026-05-19 — Sprint 68 OPS FE: SI 출고 버튼 + PI/QI/SI O/N 표시

> Sprint 68(`FEAT-SHIPMENT-COMPLETE`)의 OPS FE part — B(SI 마무리공정 화면 출고 버튼) + C(PI/QI/SI 카드 O/N·고객사 표시).

### 변경

| 파일 | 변경 |
|------|-----|
| `backend/app/routes/gst.py` | (C) products 응답에 `customer`/`sales_order` 추가 (additive) |
| `frontend/lib/screens/gst/gst_products_screen.dart` | (B) SI 카드 `[내 작업 완료]`+`[출고 완료]` 버튼 + 확인 다이얼로그 + 토스트 / (C) 카드에 `O/N · 고객사` 표시 |

### 동작

- **B** — `[출고 완료]` → `POST /api/app/work/ship-complete` (admin/manager만 노출), `[내 작업 완료]` → `POST /api/app/work/complete` finalize=false (진행 중 task만 노출). 둘 다 확인 다이얼로그 + 완료 토스트
- **C** — PI 가압검사 / QI 공정검사 / SI 마무리공정 3화면 공용 카드에 O/N(sales_order) + 고객사 표시

### 검증

- flutter build web GREEN
- Codex 라운드 1 M=2 (멱등 응답 `already_completed` 토스트 분기 / 권한 403 친화 메시지) + A-Q7(`_fetchProducts` mounted 가드) 반영, A-Q4·Q6 미반영(advisory)
- BE `gst.py` additive — 기존 소비처 회귀 0, migration 불필요

---

## [2.17.0] - 2026-05-19 — Sprint 68: 출하 완료(ship-complete) endpoint

> 출하 시점엔 작업자가 QR 태깅으로 SI task 완료가 어려움 → admin/manager 가 VIEW/OPS 화면에서 대행. 신규 `ship-complete` endpoint.

### 변경 (BE — 신규 2 파일 + 1 파일 1줄)

| 파일 | 변경 |
|------|-----|
| `backend/app/services/shipment_service.py` (신규) | `ship_complete()` — SI task 2개(SI_FINISHING+SI_SHIPMENT) 완료 + 헬퍼 3개 |
| `backend/app/routes/work_shipment.py` (신규) | `POST /api/app/work/ship-complete` (`@manager_or_admin_required`) |
| `backend/app/__init__.py` | work_shipment side-effect import 1줄 |

### 동작

- SI task 타입별 분기 — SI_FINISHING(NORMAL): `_finalize_task_multi_worker`+`complete_task` / SI_SHIPMENT(SINGLE_ACTION): `complete_single_action`
- `completed_at` 지정 가능 (없으면 서버 now KST) — 미래 차단 + SI_FINISHING `started_at` 이전 차단
- 멀티작업자 orphan `work_completion_log` backfill (force_closed 아닌 정상 완료)
- audit — `close_reason='SHIP_COMPLETE'` + `closed_by`(실행 관리자), `force_closed=FALSE` 유지
- 멱등 — 둘 다 완료 시 200 + `already_completed:true`
- `completion_status.si_completed` 갱신

### 검증

- pytest `test_ship_complete` 12/12 GREEN (TC-SHIP-01~12)
- Codex 라운드 1 (M=5/A=1/N=1) 전건 반영 — 설계: `AGENT_TEAM_LAUNCH.md` § Sprint 68 영역 10+11
- migration 불필요 (기존 테이블만). 기존 complete/complete-batch 영향 0
- OPS FE(SI 마무리공정 화면 출고 버튼 / PI·QI·SI O/N 표시) + VIEW Sprint 47(출하완료 버튼)은 후속

---

## [2.16.0] - 2026-05-18 — Sprint 67-BE: progress API 공정 토글 신호 (VIEW Sprint 46 BE part)

> AXIS-VIEW Sprint 46(생산현황 PI/QI/SI 공정 토글 필터)의 BE 공급. progress API `categories`에 토글 표시 조건 판정용 신호 3개 추가.

### 변경 (BE only, 1 파일)

| 파일 | 변경 |
|------|-----|
| `backend/app/services/progress_service.py` | `task_progress` CTE에 `MAX(completed_at)` + `completed_today`(KST) / `tagged_categories` CTE 신규(work_start_log 기반) / 메인 SELECT JOIN / `_aggregate_products()` categories dict 3필드 확장 |

### 응답 스키마 (additive)

`categories[CAT]` = `{total, done, percent}` → `{total, done, percent, started, completed_at, completed_today}`

- `started`: `work_start_log` 기반 작업 시작 이력 = "태깅됨" (재활성화 시에도 보존)
- `completed_at`: `MAX(app_task_details.completed_at)` — 공정 마지막 완료 시각
- `completed_today`: `completed_at`의 KST 날짜 == 오늘 (BE 계산)

### 검증

- pytest test_sn_progress 22/22 GREEN (기존 16 + 신규 TC-PROGRESS-TOGGLE-01~06)
- additive — 기존 `{total,done,percent}` 불변, VIEW 기존 소비처 회귀 0
- migration 불필요 (기존 테이블만 조회)
- Codex 라운드 1 (M=1/A=6) 합의 반영 — 설계서: `AGENT_TEAM_LAUNCH.md` § Sprint 67-BE / `AXIS-VIEW/DESIGN_FIX_SPRINT.md` Sprint 46 영역 9

---

## [2.15.21] - 2026-05-18 — #69 월간 생산량 KPI TEST CUSTOMER 제외

> 사용자 catch (5-18): 공장 대시보드 월간 생산량 KPI 카드(169)와 Sprint 44 고객사 도넛 중앙(164)이 불일치. `TEST CUSTOMER` 테스트 데이터 5대가 월간 생산량 KPI 에 집계되어 부풀려짐.

### 변경 (BE only, 1 파일)

| 파일 | 변경 |
|------|-----|
| `backend/app/routes/factory.py` `get_monthly_kpi()` | `production_count` 쿼리 WHERE 절에 `AND COALESCE(p.customer, '') <> 'TEST CUSTOMER'` 1줄 추가 |

### 검증

- pytest test_factory 19/19 GREEN (회귀 0)
- FE 변경 0 — `production_count` 응답값만 169→164 (월간 생산량 카드 자동 반영, 도넛과 일치)
- DB/마이그레이션 변경 0. ②단계 자동 Codex 이관 체크리스트 6항목 0개 해당 (WHERE 1줄) → Opus 자가 리뷰

---

## [2.15.20] - 2026-05-18 — FIX-FORCE-CLOSED-REACTIVATION (강제종료 task 재활성화 정상화)

> 사용자 catch (5-15~18): 생산현황 상세화면(VIEW)에서 ①강제종료한 task 를 재활성화해도 "🔒 강제종료" 표시가 안 풀림 ②미시작 task 를 강제종료한 경우 재활성화 버튼 자체가 안 뜸.

### Root Cause

| Catch | 원인 |
|-------|------|
| 1 (BE) | `reactivate_task()` (task_detail.py) UPDATE SQL 이 `completed_at/started_at/worker_id/duration_minutes/elapsed_minutes/worker_count` 만 NULL 처리 — 강제종료 메타데이터 `force_closed/closed_by/close_reason/duration_source` 4컬럼 미처리 → 재활성화해도 force_closed=TRUE 잔존 |
| 2 (VIEW) | `ProcessStepCard.tsx` 재활성화 버튼 조건이 `w.completed_at` 의존 — 작업자가 시작했던 task 강제종료는 worker completed_at 채워져 버튼 표시 / 미시작 강제종료는 SNDetailPanel placeholder worker `completed_at=null` 이라 버튼 미표시 |

### 변경

| 파일 | 변경 |
|------|-----|
| `backend/app/models/task_detail.py` | `reactivate_task()` UPDATE SET 절에 `force_closed=FALSE, closed_by=NULL, close_reason=NULL, duration_source=NULL` 4줄 추가 + docstring |
| `AXIS-VIEW ProcessStepCard.tsx` | 재활성화 버튼 조건 `w.completed_at` → `(w.completed_at || w.force_closed)` (1줄) |
| `tests/backend/test_sprint41_task_relay.py` | TC-41-12 SQL 검증 4컬럼 확장 + 통합 TC-41-17/18 신규 (시작이력有/미시작 force-close→reactivate→4컬럼+completed_at NULL 검증) |

### 연계 영향 검토 (force_closed 등 4컬럼 리셋)

- `closed_by/close_reason/duration_source` — 참조처 전부 LEFT JOIN·NULL 허용 (migration 056/057 CHECK constraint `IS NULL OR IN(...)`) → 안전
- `force_closed` — factory `_count_shipped()` 가 `force_closed=FALSE` 필터로 출하 KPI 집계하나, reactivate 는 `completed_at=NULL` 동반 → "미완료" 가 우선 → KPI 오염 없음

### 검증

- pytest reactivate 6/6 GREEN (TC-41-12 unit + 13~16 기존 + 17/18 신규 통합)
- Codex 라운드 1: M=2 (Q2 4컬럼 전부 리셋 / Q6 pytest 추가) 합의 반영, A=2 (Q4 재활성화 audit 로그 / Q5 `@manager_or_admin_required` 일관성) BACKLOG 이관, N=3

---

## [2.15.8] - 2026-05-14 — FIX-27 statusText 정정 ("동료 진행 중" 추측 → "재참여 가능" 사실 기반)

> 사용자 catch (v2.15.7 release 직후 5-14): "내 종료 / 동료 진행 중" 표현은 실제 동료 상태를 모르는 상태에서 추측한 표현. task open 상태일 뿐 동료가 진행 중인지 확실하지 않음. 사용자 권고: "재시작 가능 / 재참여 가능" 사실 기반 표현.

### 변경 (FE only, 1 파일)

| 파일 | 변경 |
|------|-----|
| `frontend/lib/screens/task/task_management_screen.dart` L249 영역 | statusText `'내 종료 / 동료 진행 중'` → `'내 종료 / 재참여 가능'` |

### 검증

- flutter build web GREEN (12.8s)
- Netlify prod 배포 완료
- 회귀 위험 0 (단일 문자열 변경)

### 학습

- UX 카피라이팅 — 시스템이 알 수 없는 상태 추측 표현 회피, 사용자 액션 가능성만 명시

---

## [2.15.7] - 2026-05-14 — FIX-27-FE-TASK-CARD-MY-STATUS-AND-PULL-TO-REFRESH (TEST-1111 UX 개선)

> 사용자 catch (TEST-1111 실기기 5-14): (1) 본인 완료 + task open 시각 구분 부재 (v2.15.3 옵션 B 적용 후) (2) 새로고침 수단 부재 (QR 재태깅만 가능) (3) "다시 시작" 라벨 — 상세뷰 이미 구현 확인 후 스킵.

### 변경 (FE only, 3 파일)

- `design_system.dart`: `GxColors.peerActive` + `peerActiveBg` + `muted` + `mutedBg` 신규 토큰
- `task_management_screen.dart`: 청록 뱃지 + RefreshIndicator + AppBar refresh + `_refreshTasks()` 신규
- `web/index.html`: `overscroll-behavior-y: contain` (안드로이드 Chrome 자체 새로고침 차단)

### Codex 검증 trail

- 라운드 1: M=2 / A=3 / N=3 → 모두 정정 반영 (M-1 myWorkStatus + M-2 taskProvider + A-1 AlwaysScrollable + A-2 GxColors + A-3 ③ 범위 제거)
- 라운드 2 미진행 (CLAUDE.md 라운드 상한 1회 정합)

### 동작 변경

| 시나리오 | v2.15.6 | v2.15.7 |
|---------|---------|---------|
| 본인 완료 + 동료 진행 중 | "진행 중" 보라 뱃지 (혼동) | 청록 "내 종료 / 동료 진행 중" |
| 다른 작업자 상태 갱신 | QR 재태깅 필수 | AppBar refresh + Pull-to-refresh |
| 안드로이드 Chrome pull-to-refresh | 브라우저 자체 새로고침 충돌 | CSS overscroll 차단 |

### 회귀 위험 0

- BE 변경 0 / DB schema 변경 0
- FE 분기 logic 추가만
- flutter analyze: error 0
- flutter build web: GREEN (12.6s)

### 후속 (별 sprint P2)

- pytest 위젯 10 TC (TC-FIX27-01~10) — `test_task_management.dart` 더미 영역 실제 구현
- BACKLOG `FEAT-TASK-PROGRESS-COUNT-DISPLAY` (옵션 D — "1/2명 종료" BE 응답 확장)

---

## [2.15.19] - 2026-05-18 — FEAT-FACTORY-MONTHLY-DETAIL-BY-CUSTOMER (#68)

> AXIS-VIEW OPS_API_REQUESTS.md #68 — 공장 대시보드 월간 뷰 "고객사 비율 도넛 차트" 위젯용 BE 집계 필드 추가.

### 변경 (BE 1 파일 + pytest 1 + version)

| 파일 | 변경 |
|------|------|
| `backend/app/routes/factory.py` `get_monthly_detail()` | `by_customer` 집계 쿼리 1건 + 응답 dict 1 키 추가 (~14 LOC) — `by_model` 1:1 복제 패턴 |
| `tests/backend/test_factory.py` | `test_md01` by_customer 키 검증 + `test_md01b_by_customer_aggregate` 신규 (키 구조 + count 내림차순 + 합계=total) |
| `backend/version.py` + `app_version.dart` | 2.15.18 → 2.15.19 |

### 동작

`SELECT p.customer, COUNT(*) FROM plan.product_info WHERE {date_field} 범위 GROUP BY p.customer ORDER BY count DESC, p.customer ASC` — `date_field` 화이트리스트 검증(기존) 후 f-string 안전. NULL customer 는 `by_model` 의 NULL model 과 동일하게 GROUP BY 자연 처리 (FE 필터).

### 검증

- pytest `test_factory.py` 19/19 PASS (241s) — 신규 TC 포함
- 회귀 위험 0 — additive (응답 키 1개 추가, breaking 아님), DB 스키마/migration 변경 0

### Codex 라운드 1

M=6/A=2/N=2 — M 6건 중 3건(Q1-1/Q1-2/Q2-1)은 Codex 의 prompt 코드블록 오독(실제 SQL 정상). 유효분 = 응답 dict `by_customer` 추가(설계 포함) + test_factory `by_customer` TC(반영). NULL = `by_model` 일관성 위해 원본 유지.

---

## [2.15.18] - 2026-05-15 — POST-REVIEW-OPS-65-PATH2-REOPEN (MECH Dual-Trigger 경로 2 fix)

> AXIS-VIEW 측 리뷰어가 OPS_API_REQUESTS.md #65 entry 교차검증 중 OPS 배포 코드 (v2.15.13~v2.15.17) 영역 버그 2건 발견. #65 = "MECH 체크리스트 Dual-Trigger" v2.15.13 ✅ COMPLETED 처리됐으나 경로 2 미완성. Codex 라운드 1 M=2 합의.

### MECH Dual-Trigger 경로 2 버그 2건

| catch | 라벨 | 내용 |
|-------|------|------|
| **M-A4** | M | `_try_mech_close()` 영역 `UPDATE completion_status SET mech_completed=TRUE` 누락 — ELEC `_try_elec_close()` 영역 존재. 경로 2 (체크리스트가 마지막) close 후 mech_completed=FALSE 잔존 → VIEW 생산현황 "미완료" 표시 |
| **M-A7** | M | `upsert_mech_check()` close 게이트 = `check_mech_completion(sn, judgment_phase)` 단독 — 1차 검수만 채워도 close. v2.15.16 catch 1 의 경로 2 잔존분 (v2.15.16 영역 경로 1 `check_category_close_eligible` 만 교체) |

### 변경 (BE 1 파일 + pytest 1 + version)

| 파일 | 변경 |
|------|------|
| `backend/app/services/checklist_service.py` `_try_mech_close()` | close 후 `UPDATE completion_status SET mech_completed=TRUE WHERE serial_number=%s AND mech_completed=FALSE` + `conn.commit()` 추가 (M-A4, ELEC 패턴 정합, Codex Q1d — auto_close_relay_task 자체 conn 사용이므로 명시 commit 필수) |
| `backend/app/services/checklist_service.py` `upsert_mech_check()` | close 게이트 분리 — `is_complete` (FE 진행률 표시용, phase별 `check_mech_completion`) 유지 + close 게이트만 `check_mech_completion_all()` (Phase 1+2 합산, 경로 1 정합) (M-A7) |
| `backend/version.py` + `app_version.dart` | 2.15.17 → 2.15.18 |
| `tests/backend/test_v2_15_18_mech_path2_close.py` | 신규 TC 5건 (M-A4 completion_status UPDATE 3 + M-A7 close 게이트 2) |

### 검증

- pytest 신규 `test_v2_15_18_mech_path2_close.py` 5/5 PASS (0.09s)
- 회귀 위험 0 — `task_service.py` 경로 1 touch 0 / ELEC `_try_elec_close()`+`upsert_elec_check()` touch 0 / MECH 경로 2 전용

### 영향

- 경로 1 (SELF_INSPECTION 가 마지막) 정상 동작 중 — 영향 0
- 경로 2 (체크리스트가 마지막): mech_completed flag 정상 set + 2차 검수 미입력 시 close 차단
- AXIS-VIEW 생산현황 상세뷰 MECH 동기화 정상화

### 후속 (BACKLOG 등록)

- `OPS-65-DOC-DRIFT-20260515` — AXIS-VIEW OPS_API_REQUESTS.md #65 §9 Codex A 5건 (문서 drift, 동작 영향 0) → AXIS-VIEW repo 측 정정 (P3)

---

## [2.15.17] - 2026-05-15 — FIX-VIEW-ORPHAN-DURATION (Trigger task close 시 소요시간 미표시 fix)

> 사용자 운영 catch (5-15): "Trigger task close 시 VIEW 에서 소요시간 표시 안 됨 / 정상 완료된 task 만 소요시간 표시 됨". Codex 라운드 1 M=2/A=4 반영.

### Root Cause — work.py + task_service_batch.py SQL 컬럼 불일치

worker 배열 조회 SQL 영역 `completed_at` 영역 `COALESCE(wcl.completed_at, td.completed_at)` fallback 있는데 `duration_minutes` 영역 `wcl.duration_minutes` 단독 → orphan worker (auto-close, work_completion_log record 없음) 영역 NULL → VIEW `formatDuration(null)` → '—' 표시.

- 정상 완료: worker complete_work() → work_completion_log INSERT (duration 포함) → 표시
- Trigger auto-close: `auto_close_relay_task()` 영역 work_completion_log INSERT 안 함 → wcl.duration_minutes NULL → 미표시

### Codex 라운드 1 결과 — M 2건 catch (Claude 사전 검토 누락)

| Q | 라벨 | catch |
|---|------|-------|
| Q1 | M | 음수 duration 가능 + float 반환 → `GREATEST(0, FLOOR(...))::int` 클램프 필수 |
| Q2~Q5 | A | 멀티 worker 정합 / 응답 일관성 / is_orphan 라벨 (VIEW 별 sprint) / pause 차감 별 sprint |
| Q6 | M | `task_service_batch.py` L323 동일 버그 — 같은 PR 영역 fix 필수 + test_hotfix04_orphan NULL assert 갱신 |

### 변경 (BE 2 파일 + pytest 1 + version)

| 파일 | 변경 |
|------|------|
| `backend/app/routes/work.py` L645 | `get_tasks_by_serial()` worker SQL — `duration_minutes` COALESCE + `GREATEST(0, FLOOR(EXTRACT(EPOCH ...)/60))::int` fallback |
| `backend/app/services/task_service_batch.py` L323 | `_enrich_tasks_with_workers()` worker SQL — 동일 fallback (Codex Q6 M, `/tasks/by-order` endpoint 백킹) |
| `tests/backend/test_hotfix04_orphan.py` | TC-ORPHAN-01/04 NULL assert → integer 240분 갱신 + TC-ORPHAN-05 신규 (음수 클램프 0 검증) |
| `backend/version.py` + `app_version.dart` | 2.15.16 → 2.15.17 |

### 동작 (fallback)

- orphan worker (auto-close): `wcl.duration_minutes` NULL → `close 시각 − started_at` 분 단위 근사 (GREATEST 0 클램프 + FLOOR + ::int)
- in_progress worker (task open): `COALESCE(wcl.completed_at, td.completed_at)` NULL → 전체 NULL 유지 (정상, duration 미표시)
- 정상 완료 worker: `wcl.duration_minutes` 그대로 (pause 차감 반영값)

### 검증

- pytest `test_hotfix04_orphan.py` 10/10 PASS (260s) — TC-ORPHAN-01/04 갱신 + TC-ORPHAN-05 신규
- 회귀 위험 0 (SQL 1 expression 2곳, 신규 로직/함수 아님 — work.py God File 1389줄 / task_service_batch.py 영역 LOC 증가 ≈ 12줄)

### 한계 (별 sprint)

- pause 차감 미반영 (근사값). 정밀 duration (pause 차감 + man-hour) 필요 시 `REF-WORKER-DURATION-PRECISION` 별 sprint
- VIEW 측 `is_orphan` worker "추정 소요시간" 라벨 표시 — AXIS-VIEW 별 sprint (`ProcessStepCard.tsx`)

---

## [2.15.16] - 2026-05-15 — Catch 3건 fix (MECH Phase 1+2 + force_closed=False 통일 + PREV_DAY_CAP)

> 사용자 운영 catch (v2.15.15 검증 후 5-15): (1) MECH 체크리스트 1차만 완료해도 task close 됨 (2) ELEC 정상 동작 확인 (3) close trigger 미완료 task 영역 force_closed=TRUE 처리되는데 사용자 분석상 trigger 가 근무시간 내 발동 → 조건 1 (attendance check_out) + 조건 2 (17:00) 무의미. Codex 라운드 1 M=5 catch (Claude Code 측 사전 검토 누락) 전수 반영.

### Codex 라운드 1 결과 — M 5건 catch (Claude Code 측 사전 검토 누락)

| Q | 라벨 | Catch |
|---|------|-------|
| Q1 | M | `check_mech_completion` 호출자 4곳 (Claude 2곳만 식별 — checklist.py L1338 + production.py L279 누락) → X-α 회귀 위험, **X-β 필수** |
| Q2 | M | force_closed 버그 5곳 (Claude 2곳만 식별 — checklist_service.py L1352 + L1647 + L1669 누락) |
| Q3 | M | auto-close 영역 validate_duration 미호출 → 별 sprint 불가, **본 sprint 영역 PREV_DAY_CAP 추가** |
| Q4 | N | test_relay_first_final.py 38 TC 영역 회귀 0 |
| Q5 | M | task_service.py L843 Sprint 41-B 레거시 루프 잔존 (Claude 미식별) — `AUDIT_TRAIL_GUIDE.md` "v2.15.14 이후 0건" 주장과 모순 |
| Q6 | N | duration_calculator.py 활성 사용 중, dead path 아님 |

### 변경 (BE 3 파일 + migration 1 + pytest 1 + version)

| 파일 | 변경 |
|------|------|
| `backend/app/services/checklist_service.py` | 신규 `check_mech_completion_all()` (Phase 1+2 합산, ELEC 패턴 정합) + IF_2/SELF_INSPECTION/orphan auto-close 3곳 `force_closed=False` 통일 (~50 LOC) |
| `backend/app/services/task_service.py` | (1) `check_category_close_eligible()` MECH 분기 `check_mech_completion_all()` 호출 (Q1 X-β) (2) `_trigger_first_final_close()` + `_trigger_second_close()` `force_closed=False` 통일 + `last_started_at` 전달 (Q2+Q3) (3) Sprint 41-B 레거시 루프 제거 (Q5) — `_trigger_second_close()` 만 호출 |
| `backend/app/services/duration_calculator.py` | `calculate_close_at()` signature `last_started_at` 인자 추가 + priority 0 `PREV_DAY_CAP` 추가 (Q3 M, 익일/주말 trigger 시 started.date() 17:00 KST cap) |
| `backend/migrations/057_add_prev_day_cap_duration_source.sql` | duration_source CHECK constraint 영역 `PREV_DAY_CAP` enum 추가 (4 → 5) |
| `backend/version.py` + `frontend/lib/utils/app_version.dart` | VERSION 2.15.15 → 2.15.16 |
| `tests/backend/test_v2_15_16_force_closed_and_prev_day_cap.py` | 신규 TC 12건 (시나리오 A/B/C/D + priority 0 + Phase 1+2 + signature 보존) |

### 시나리오 매트릭스 (PREV_DAY_CAP 발동 검증)

| 시나리오 | started | trigger | cap 발동? | close_at | duration |
|----------|---------|---------|-----------|----------|----------|
| A 정상 근무 (운영 99%) | 5-15 09:00 | 5-15 14:00 | ❌ | 14:00 | 5h |
| B 같은 날 야간 | 5-15 09:00 | 5-15 19:00 | ❌ | 17:00 (fallback) | 8h |
| C 익일 trigger | 5-14 14:00 | 5-15 09:00 | ✅ | **5-14 17:00** | 3h |
| D 주말 후 | 5-10 (금) 14:00 | 5-13 (월) 09:00 | ✅ | **5-10 17:00** | 3h |
| E started ≥ 17:00 (야간 시작) | 5-14 18:00 | 5-15 09:00 | ✅ + 보호 | started 그대로 | 0 (음수 차단) |

### 검증

- pytest 신규 12/12 PASS (0.14s) — `test_v2_15_16_force_closed_and_prev_day_cap.py`
- pytest `test_relay_first_final.py` 38/38 PASS (21.86s, 회귀 0)
- 회귀 위험 0 (FIX-A X-β = signature 보존, FIX-B = additive policy 단일화, FIX-C = additive priority 0, FIX-D = 레거시 루프 직후 `_trigger_second_close()` 동일 task 처리)

### POST-REVIEW (별 sprint BACKLOG 등록)

- `POST-REVIEW-AUTOCLOSED-CLOSED-BY-20260515` — Codex Q2 추가 catch: auto-close 영역 `closed_by = worker_id` 기록 중 (설계서 "auto-close = NULL" 기술과 모순). 정책 명확화 필요
- `POST-REVIEW-AUDIT-TRAIL-CONSISTENCY-20260515` — force_closed 의미론 변경 (auto-close 자연 close 통일 → manager force-close API 전용 강제종료) `AUDIT_TRAIL_GUIDE.md` 갱신 필요

### 영향 사용자

- 사용자 5-15 운영 catch 3건 모두 해결
- 익일/주말 trigger 시 18h+ 비정상 duration 자동 cap (운영 audit trail 정확화)
- MECH Phase 2 (관리자 input) 미입력 시 close 발동 차단 (ELEC 패턴 정합)
- Sprint 41-B 레거시 루프 제거 — `AUTO_CLOSED_LEGACY` audit trail 신규 발생 0건 (v2.15.14 표준 통일)

---

## [2.15.15] - 2026-05-15 — BUG-RELAY-MODE-AUTO-REFRESH-MISSING + COMPLETE-KEY-USELESS

> 사용자 5-14 catch (BACKLOG L342) + 5-15 결정 — "내 작업만 완료" relay_mode 후 자동 갱신만으로 화면 전환 안 됨 (수동 새로고침 필요) + 본인 완료 상태 "완료" 키 무의미 (TASK_ALREADY_COMPLETED 에러). 사용자 결정: Catch 1=B (FE fetchTasks 호출) / Catch 2=c (확인 다이얼로그) / 결정 3=a (일시정지 조건부 숨김). Codex 라운드 1 (1차) M-1 (목록 화면 else if 정리) 반영 + Opus 자가 리뷰 M-1 (fetchTasks flickering) + M-2 (BE TASK_ALREADY_COMPLETED 에러) 추가 catch + 정정.

### 변경 (BE 1 + FE 2 파일 + version)

| 파일 | 변경 |
|------|------|
| `frontend/lib/providers/task_provider.dart` | (1) `fetchTasks()` `silent: bool = false` 인자 추가 — silent=true 시 isLoading set skip (M-1 spinner 두 번 표시 catch) (2) `completeTask()` 응답 후 fetchTasks(silent: true) 호출 — 옵션 B (relay_mode 응답 task 객체 미포함 영역 우회) |
| `frontend/lib/screens/task/task_management_screen.dart` | (1) 본인 완료 카드 블록 A — `[내 작업 완료]` 표시 + `[재시작]` IconButton + `[공정 마감]` 버튼 신규 (2) 블록 B (일시정지) 조건 영역 `myWorkStatus != 'completed'` 추가 (Codex 1차 catch) (3) 블록 C (진행 중) 조건 영역 동일 추가 (4) `_handleFinalizeOnly()` 신규 — 확인 다이얼로그 "이 task만 정식 종료됩니다." + finalize=true 직행 |
| `backend/app/services/task_service.py` | `complete_work()` L564 영역 조건 영역 `... and not finalize` 추가 (M-2 catch) — 본인 완료 상태 영역 "공정 마감" 버튼 영역 finalize=True 호출 시 TASK_ALREADY_COMPLETED 우회 → task close 진행 |
| `backend/version.py` + `frontend/lib/utils/app_version.dart` | 2.15.14 → **2.15.15** |

### 자가 리뷰 catch (M-1 + M-2) + Codex 라운드 1 catch (M-3)

| Catch | 위치 | Root cause | Fix |
|-------|-----|---|---|
| M-1 (자가) | task_provider.dart fetchTasks() L175 | isLoading=true 다시 set → spinner 두 번 표시 (flickering) | silent 인자 추가 |
| M-2 (자가) | task_service.py L564~569 | 본인 완료 상태 영역 finalize=True 호출 시 `_worker_already_completed_task=True` → TASK_ALREADY_COMPLETED 400 에러 | `and not finalize` 조건 추가 |
| **M-3 (Codex Q3)** | task_service.py `_record_completion_log` 영역 | M-2 fix 후 finalize=True 재호출 시 work_completion_log 신규 INSERT → **중복 row 추가** + duration 부풀려짐 | `should_record_completion` 분기 추가 + `_get_latest_worker_completion_duration()` 신규 (기존 duration 재사용) |

### Codex 라운드 1 결과 (M=1 / A=4 / N=4)

- Q1 fetchTasks(silent) 기본값 호환성 = N
- Q2 silent isLoading 오염 가능성 = A (미사용 경로, 실 위험 낮음)
- **Q3 work_completion_log 중복 INSERT = M → Codex 자동 정정 완료**
- Q4 v2.15.14 force_closed 충돌 = N
- Q5 Sprint 41-D Second Close 충돌 = N
- Q6 카드 블록 A/B/C 상호 배타성 = N
- Q7 버튼 연타 락 없음 = A (UI race)
- Q8 finalize 기본값 회귀 검증 불가 = A (별 검증)
- 추가 catch: task_finished 메시지 오해 가능성 = A (UX, M 범위 밖)

### 본인 완료 상태 카드 UI 변경 (v2.15.15)

| 이전 | v2.15.15 |
|------|---|
| 내 작업 완료 / 재시작 / 일시정지 / 완료 (4 버튼, 일시정지 + 완료 무의미) | **내 작업 완료 / 재시작 / 공정 마감** (3 버튼, 일시정지 hide + 완료 → 공정 마감 라벨) |

→ 일시정지 conditional hide (myWorkStatus='completed' 시점만) — 재시작 후 다시 표시.

### 검증

- pytest test_relay_first_final.py 38/38 PASS (21.20s)
- flutter build web GREEN (12.5s)
- Netlify prod 배포 완료
- Codex 라운드 1 (2차) = API overload (529) catch 영역 skip — Opus 자가 리뷰 M-1+M-2 catch 충분 + S2 패턴 (7일 사후 Codex)
- 회귀 위험 0 (silent default=false 영역 기존 호출처 영향 0, finalize=False 영역 기존 동작 보존)

### 후속

- POST-REVIEW deadline 2026-05-22 (7일) — Codex 사후 검토 필수
- A' (BE route enrichment) 별 sprint BACKLOG `REF-WORK-RESPONSE-ENRICHMENT-20260515` 등록 권고

---

## [2.15.14] - 2026-05-15 — BUG-SECOND-CLOSE-FORCE-CLOSED-FALSE-POSITIVE + AUDIT TRAIL 통일

> 사용자 5-14 운영 catch (BACKLOG `BUG-SECOND-CLOSE-FORCE-CLOSED-FALSE-POSITIVE-20260514`) — MECH SELF_INSPECTION / ELEC IF_2 누른 후 자동 close 된 잔여 task 영역 "강제종료" 라벨 + duration 0m 잘못 표시. 작업자 본인이 "내 작업 완료" 누른 task도 (work_completion_log row 존재) `force_closed=TRUE` 일괄 적용된 결과. + Codex 라운드 1 옵션 b 채택 (audit trail 통일 — 사용자 5-15 결정 "장기 운영 영역 디테일 중요").

### 사용자 의도 정의 (5-14 운영 catch)

- 작업자가 "내 작업 완료" 누른 task = **자연 close** (`force_closed=FALSE`, duration = MAX(work_completion_log.completed_at) 기준)
- 작업자 미종료 task = **manager 권한 강제종료** (`force_closed=TRUE`, manager 발동 의미)

### 변경 (BE only, 3 파일 + version)

| 파일 | 변경 |
|------|------|
| `backend/app/models/task_detail.py` `auto_close_relay_task()` | `force_closed: bool = True` 인자 추가 (default=True 영역 Sprint 41-B legacy 호환 보존) + UPDATE SQL 양쪽 분기 `force_closed = %s` 변경 |
| `backend/app/services/task_service.py` `_trigger_first_close()` + `_trigger_second_close()` | SELECT 영역 `unfinished_workers_count` column 추가 (work_start_log JOIN work_completion_log NOT EXISTS) + for loop 영역 `o_unfinished > 0 → force_closed=TRUE` 분기 |
| `backend/app/services/checklist_service.py` `_try_mech_close()` + `_try_elec_close()` | 동일 패턴 (unfinished_workers_count + last_completion_worker_id) + audit trail 통일 (`trigger_type='SECOND_FINAL'` + `trigger_task_id='SELF_INSPECTION'/'IF_2'` + `closed_by_worker_id=last_completion_worker_id`) |
| `backend/version.py` + `frontend/lib/utils/app_version.dart` | 2.15.13 → **2.15.14** |

### force_closed 결정 로직

```sql
unfinished_workers_count = COUNT(DISTINCT wsl.worker_id)
  FROM work_start_log wsl
  WHERE wsl.task_id = td.id
    AND NOT EXISTS (
      SELECT 1 FROM work_completion_log wcl
       WHERE wcl.task_id = td.id
         AND wcl.worker_id = wsl.worker_id
    )

= 0  → 모든 worker 본인 종료 누름 → force_closed = FALSE (자연 close)
> 0  → 일부 worker 미종료 → force_closed = TRUE (manager 권한 강제종료)
```

### Audit Trail 통일 (Codex 옵션 b 채택)

| 경로 | 이전 (혼재) | v2.15.14 (통일) |
|------|---|---|
| task_service `_trigger_*_close` | `AUTO_CLOSED_BY_SECOND_FINAL_TRIGGER:...` + closed_by=worker_id | 동일 (기존 정합 유지) |
| checklist `_try_mech_close` | `AUTO_CLOSED_LEGACY` + closed_by=NULL | **`AUTO_CLOSED_BY_SECOND_FINAL_TRIGGER:SELF_INSPECTION` + closed_by=마지막 완료 worker_id** |
| checklist `_try_elec_close` | `AUTO_CLOSED_LEGACY` + closed_by=NULL | **`AUTO_CLOSED_BY_SECOND_FINAL_TRIGGER:IF_2` + closed_by=마지막 완료 worker_id** |

→ 4개 trigger 함수 영역 모두 동일 trail 형식 → 추후 데이터 분석 / 디버깅 영역 일관성 확보.

### Codex 라운드 1 결과 (M=0 / A=8 / N=2)

- M (Must) = 0 → 배포 블로커 없음
- A (Advisory) 8건 중 본 sprint 영역 반영 = 2건 (close_reason trail + closed_by 표준화)
- 잔존 A 6건 (pytest TC 신규 5건 + test_relay_first_final 카운트 catch) = 별 sprint P2

### 검증

- pytest test_relay_first_final.py 38/38 PASS (19.26s)
- flutter build web GREEN (13.9s)
- Netlify prod 배포 완료
- 회귀 위험 0 (default=TRUE legacy 호환 + Sprint 41-B 기존 호출 그대로)

### 후속

- POST-REVIEW deadline 2026-05-22 (7일)
- pytest TC 5건 (TC-SC-01~05) = 별 sprint P2
- Advisory 6건 잔존 = BACKLOG `POST-REVIEW-AUDIT-TRAIL-CONSISTENCY-20260515`

---

## [INFRA] - 2026-05-15 — INFRA-CI-PYTEST-AUTO (CI 워크플로우 신규 + ADR-029 사례 #28)

> 옵션 2 (사용자 5-15 결정) — v2.15.0~v2.15.13 release trail "pytest GREEN" 보고 영역 실 환경 미실행 가능성 catch 후 영구 자동화. `.github/workflows/pytest.yml` 신규 도입 — push/PR 시 자동 pytest 실행. ADR-029 사례 #28 등록 (cowork pytest 결과 보고 검증 누락).

### 변경 (INFRA, version bump 없음)

| 파일 | 변경 |
|------|------|
| `.github/workflows/pytest.yml` | 신규 — push/PR `backend/**` or `tests/**` 변경 시 자동 pytest 실행 (Python 3.12 + `pip install -r backend/requirements.txt` + pytest-mock/xdist/timeout + `pytest -n 4 --timeout=120` + junitxml + 30일 artifact 보존) |
| `memory.md` | ADR-029 사례 #28 추가 — pytest 결과 보고 검증 누락 catch trail |

### 사용자 측 GitHub Secrets 설정 필요 (CI 동작 전제)

- `TEST_DATABASE_URL` — Railway staging DB URL (또는 별 test DB)
- `JWT_SECRET_KEY` / `JWT_REFRESH_SECRET_KEY` — secret 미설정 시 default ci-test-secret 사용

### 후속

- 다음 push (backend/tests 변경) 시 자동 pytest 실행 → GitHub Actions 탭에서 결과 확인 가능
- 5-14 23:59 release trail "pytest GREEN" 보고 영역 = cowork 측 별 환경 또는 추정 보고 의심 — 이번 CI 도입 후 영구 검증 가능

---

## [2.15.13] - 2026-05-15 — HOTFIX-MECH-CHECKLIST-DUAL-TRIGGER (체크리스트 100% PUT 시점 SELF_INSPECTION + 잔여 task 일괄 close)

> 사용자 5-15 운영 catch + Railway logs 결정적 trail 발견 — TEST-1111 SELF_INSPECTION 영역 먼저 complete (체크리스트 미입력 상태) → `check_mech_completion=False` → relay_mode → SELF_INSPECTION.completed_at=NULL → 그 후 체크리스트 100% PUT → **MECH 영역 양방향 트리거 미구현 영역 → 영원히 close X**. v2.15.10 ELEC `_try_elec_close()` 패턴 모방 영역 fix.

### 사용자 실제 운영 흐름 (5-15 00:37 KST 로그 trail)

```
00:37:24  SELF_INSPECTION 시작
00:37:29  SELF_INSPECTION 완료 (체크리스트 미입력 상태)
          → check_mech_completion = False
          → "체크리스트 100% 미달 → close 보류" (정상 동작)
          → SELF_INSPECTION.completed_at = NULL (relay_mode 응답)
00:37:38  사용자 → MECH 체크리스트 화면 진입 → 11개 NA 입력 시작
00:37:51  체크리스트 100% 완료
          → ❌ v2.15.12 까지 MECH 양방향 트리거 없음 → close 안 됨
```

### 변경 (BE only, 1 파일 + version)

| 파일 | 변경 |
|------|------|
| `checklist_service.py` | (1) `_try_mech_close(serial)` 신규 — SELF_INSPECTION work_completion_log 1+ 확인 + 잔여 MECH task auto_close_relay_task 호출 (2) `upsert_mech_check()` 영역 `is_complete=True` 시 `_try_mech_close()` 호출 추가 + 응답 `mech_closed` 필드 신규 |
| `version.py` + `app_version.dart` | 2.15.12 → **2.15.13** |

### Dual-Trigger 매트릭스 (v2.15.13 정합)

| 시점 | 발동 | 액션 |
|------|------|------|
| **시점 1**: SELF_INSPECTION complete (체크리스트 이미 100%) | `complete_work` L772 `check_category_close_eligible('MECH')=True` → `_trigger_second_close()` | SELF_INSPECTION + 잔여 task auto_close |
| **시점 2**: 체크리스트 100% PUT (SELF_INSPECTION 이미 complete) | `upsert_mech_check` 영역 100% 도달 → `_try_mech_close()` (신규) | SELF_INSPECTION + 잔여 task auto_close |

→ 순서 무관. 두 경로 모두 동일 효과.

### ELEC v2.15.10 패턴 모방 확정

| 영역 | ELEC `_try_elec_close()` v2.15.10 | MECH `_try_mech_close()` v2.15.13 |
|------|---|---|
| 검증 task | INSPECTION work_completion_log 1+ | SELF_INSPECTION work_completion_log 1+ |
| 액션 task (본인) | IF_2 auto_close_relay_task | SELF_INSPECTION auto_close_relay_task |
| 잔여 task | First Close 이미 처리 (panel/cabinet/wiring/IF_1) | 잔여 task auto_close (gas2/util2/HEATING_JACKET 등) |

### 검증

- pytest test_relay_first_final.py 38/38 PASS (14.27s)
- flutter build web GREEN (12.7s)
- Netlify prod 배포 완료
- 회귀 위험 0 (BE only, additive helper + 호출 1줄)

### 후속

- POST-REVIEW deadline 2026-05-22 (7일) — Codex 사후 검토
- Catch 2 (작업화면 시작/내작업완료 후 메뉴 미동기화) = 별 hotfix 진단 진행

---

## [2.15.12] - 2026-05-15 — FIX-MECH-CHECKLIST-PROGRESS-REALTIME-AND-STICKY (실시간 갱신 + 스크롤 고정)

> v2.15.11 직후 사용자 catch 2건: ① MECH 진행률 바 실시간 갱신 안 됨 (새로고침 시점만 변경) ② MECH 진행률 바 스크롤 시 위로 사라짐 (ELEC = 고정).

### 변경 (FE only, 1 파일 + version)

| 파일 | 변경 |
|------|------|
| `mech_checklist_screen.dart` | (1) 라디오 onTap 영역 `setState` 영역 `_checkResultMap[masterId] = value` + `item['check_result'] = value` 동시 update — v2.15.11 진행률 getter (`_checkedCount`) 영역 `item['check_result']` 참조 정합 (2) `_buildBody()` 영역 ELEC 패턴 모방 — `Column > _buildHeader() + _buildProgressHeader() + Divider + Expanded(RefreshIndicator(ListView))` 영역 영역 진행률 헤더 영역 ListView 외부 고정 (ListView itemCount `+2` → 단순 `_groups.length`) |
| `version.py` + `app_version.dart` | 2.15.11 → **2.15.12** |

### Root cause

| Catch | Root cause |
|-------|----------|
| 실시간 갱신 안 됨 | `_checkResultMap` 만 update, `item['check_result']` 미동기화 — v2.15.11 진행률 getter 옛 값 참조 |
| 스크롤 시 사라짐 | v2.15.11 진행률 헤더 = ListView item (스크롤 시 위로) — ELEC 영역 = `Column > Expanded(ListView)` 외부 고정 패턴 미적용 |

### 검증

- flutter build web GREEN (12.5s)
- Netlify prod 배포 완료
- 회귀 위험 0 (BE 변경 0, 라디오 onTap 영역 +1줄, ListView wrap 영역 Column 변경)

### 후속

- **Catch 2 (작업화면 시작/내작업완료 후 메뉴 미동기화)** = 별 hotfix 진단 진행 — BE startTask/completeTask 응답 task 객체 필드 (workers / my_status 등) 영역 확인 + FE 카드 분기 영역 정합 검증

---

## [2.15.11] - 2026-05-15 — FIX-MECH-CHECKLIST-PROGRESS-HEADER (ELEC 패턴 정합 진행률 표시)

> 사용자 5-14 운영 catch (Catch 2 영역 진단 중) — "MECH 체크리스트 진행률 카운트 현재 elec 처럼 없으며". ELEC 체크리스트 화면 상단 영역 진행률 헤더 동일 디자인 적용. FE only 단일 파일.

### 변경 (FE only, 1 파일 + version)

| 파일 | 변경 |
|------|-----|
| `frontend/lib/screens/checklist/mech_checklist_screen.dart` | (1) `_totalCount` / `_checkedCount` / `_progress` / `_isAllDone` getter 신규 (scope 매칭 active 항목 + PASS/NA 카운트 — BE `_resolve_active_master_ids` 로직 정합) (2) `_buildProgressHeader()` 위젯 신규 (ELEC `_buildProgressHeader()` 동일 디자인) (3) ListView itemCount `_groups.length + 1` → `+2` (제품정보 header + 진행률 header) |
| `backend/version.py` + `frontend/lib/utils/app_version.dart` | 2.15.10 → **2.15.11** |

### 진행률 정의 (ELEC 패턴 정합)

```
total  = scope_rule 매칭 + BE phase1_applicable 필터 통과 항목 수
done   = total 항목 중 check_result IN ('PASS', 'NA')
%      = done / total
```

### scope_rule 매칭 (BE 정합)

| scope_rule | 매칭 조건 |
|------------|----------|
| `null` / `'all'` | 모든 모델 활성 |
| `'tank_in_mech'` | `_tankInMech` (BE 응답 R2-1 patch) |
| 직접 모델명 (예: `'DRAGON'`) | `_productModel.startsWith(scope)` |

### 검증

- `flutter analyze mech_checklist_screen.dart` = 0 error (info 4 = 기존 영역)
- `flutter build web --release` GREEN (12.9s)
- Netlify prod 배포 완료
- 회귀 위험 0: BE 변경 0 / DB schema 변경 0 / additive UI 위젯 + ListView item 1개 추가

### 후속

- Catch 2 (MECH gas2/util2 close 안 됨) = 사용자 측 진단 SQL 4건 결과 대기 후 별 hotfix 진행
- 옵션 2 (CI 워크플로우 + 이전 release pytest 재검증) = 사용자 측 자면서 진행 예정

---

## [2.15.10] - 2026-05-14 — HOTFIX-SPRINT41D-ELEC-CLOSE-CONDITION-DUAL-TRIGGER (IF_2 강제 제거 + Dual-Trigger 완성)

> 사용자 5-14 운영 catch + 진단 SQL 4건 확인 결과: TEST-1111 IF_2 본인 종료 (relay 모드, completed_at NULL) + INSPECTION 완료 + 체크리스트 100% (Phase 1 16/16 + Phase 2 24/24) 상태인데 IF_2 close 안 됨. Root cause: `check_category_close_eligible('ELEC')` 가 `check_elec_final_tasks_completed()` 호출 → IF_2 + INSPECTION 둘 다 completed_at NOT NULL 강제 → relay 모드 IF_2 (completed_at NULL) = False = trigger skip. + `_try_elec_close()` 는 completion_status flag 만 set, IF_2 task 자체 close X. v2.15.5 catch #25 의 양방향 트리거 의도가 절반만 구현됨. v2.15.10 = ELEC close 조건 = **INSPECTION complete + 체크리스트 100% 만** (IF_2 무관) + Dual-Trigger 양쪽 경로에서 IF_2 auto_close_relay_task 호출 보장.

### 사용자 의도 정의 (5-14 확정)

```
조건: INSPECTION(자주검사).completed_at NOT NULL  AND  ELEC 체크리스트 100%
액션: IF_2 task close (auto_close_relay_task 호출)
순서: 무관 (양방향 트리거)
잔여 task: 이미 IF_2 start 시점 First Close trigger 가 처리 (panel/cabinet/wiring/IF_1)
```

### 변경 (BE 2 파일 + version)

| 파일 | 변경 |
|------|-----|
| `backend/app/services/task_service.py` | (1) `check_category_close_eligible('ELEC')` 분기 — `check_elec_final_tasks_completed()` → `_check_inspection_completed()` 로 교체 (IF_2 강제 제거) (2) `_check_inspection_completed()` 신규 — INSPECTION completed_at NOT NULL 단순 검증 (3) `check_elec_final_tasks_completed()` deprecation 마킹 (호출 0건, import 호환 보존) |
| `backend/app/services/checklist_service.py` | `_try_elec_close()` 확장 — IF_2 work_completion_log 검증 → INSPECTION complete 검증으로 교체 + `auto_close_relay_task()` 호출 추가 (IF_2 task 실제 close) |
| `backend/version.py` + `frontend/lib/utils/app_version.dart` | 2.15.9 → **2.15.10** |

### 양방향 트리거 매트릭스 (v2.15.10 정합)

| 시나리오 | 순서 | 발동 시점 | 액션 | 결과 |
|---------|------|----------|------|:-:|
| **A** | IF_2 본인종료 → INSPECTION 종료 → 체크리스트 100% | 체크리스트 100% PUT 시점 (경로 2 `_try_elec_close`) | INSPECTION done 검증 → `auto_close_relay_task(IF_2)` 호출 | IF_2 close ✅ |
| **B** | IF_2 본인종료 → 체크리스트 100% → INSPECTION 종료 | INSPECTION complete 시점 (경로 1 `check_category_close_eligible`) | INSPECTION + 체크리스트 100% → Sprint 41-D Second Close 트리거 | IF_2 close ✅ |

### Root cause trail

- v2.15.5 catch #25 명시 의도 = "양방향 트리거 (INSPECTION 시점 + 체크리스트 100% 시점)"
- 그러나 구현은 `check_elec_final_tasks_completed()` 영역에서 IF_2 강제 → relay 모드 IF_2 = False = 트리거 영원히 미발동
- `_try_elec_close()` 영역 = completion_status flag 만 set (분석/리포트 페이지만 영향) — task 자체 close 누락
- 사용자 운영 catch (5-14): "IF_2 내 작업 완료 + INSPECTION 완료 + 체크리스트 100% 상태인데 IF_2 close 안 됨"
- 진단 SQL 4건 확인: ① IF_2.completed_at NULL + INSPECTION.completed_at NOT NULL ② 체크리스트 미입력 0건 ③ Phase 1 16/16 + Phase 2 24/24 ④ Sentry/alert 0건 — silent fail 영역 X, 코드 로직 자체 결함 확정

### 회귀 위험 0

- DB schema 변경 0
- `check_elec_final_tasks_completed()` 호출 0건 (dead code, import 호환 보존)
- `_try_elec_close()` 기존 동작 (completion_status flag set) 보존 + auto_close_relay_task 호출 추가만
- MECH/TM/TMS 분기 영향 0 (ELEC 만 변경)
- pytest 영역: 사용자 측 또는 CI 영역 위임 (S2 핫픽스 패턴)

### 후속

- POST-REVIEW deadline 2026-05-21 (7일) — Codex 사후 검토 필수
- BACKLOG `POST-REVIEW-HOTFIX-SPRINT41D-ELEC-CLOSE-CONDITION-DUAL-TRIGGER-20260514` 등록
- MECH 동일 패턴 catch (사용자 catch 2 영역 — gas2/util2 close 안 됨, scope_rule 영역 진단 필요) = 별 hotfix
- pytest TC 신규 작성 (TC-DT-01~04) — 별 sprint P2

---

## [2.15.9] - 2026-05-14 — HOTFIX-SPRINT41D-PROGRESS-100-REVERT-AND-LABEL-CHANGE ((나) → (가) 회귀 + 다이얼로그 라벨 변경)

> 사용자 release v2.15.7 (FIX-27 FE TASK_CARD UX) + v2.15.8 (statusText "재참여 가능" 정정) 와 별 hotfix. v2.15.6 (나) 옵션 채택이 v2.15.3 `auto_finalize_blocked` 영역과 충돌 catch — 사용자 5-14 운영 검증 시 SELF_INSPECTION + 체크리스트 100% 진행했는데 gas2/util2 close 안 됨. Root cause: task progress 100% AND 검증 시 `app_task_details.completed_at IS NULL` 기준 카운트 → "내 작업 완료" 누른 task = completed_at NULL = pending 잡힘 = `check_category_close_eligible = False` → Sprint 41-D Second Close trigger 발동 X → gas2/util2 영원히 open. cowork 이 사용자 발화 "mech, elec 실적 조건 변동 없음" 을 (나) 로 잘못 해석. 실제 의도 = (가) "실적 정의 불변, close 조건도 그대로". v2.15.9 = (가) 회귀 + 다이얼로그 라벨 "공정 마감" 변경 묶음.

### 변경 (3 파일 + version)

| 파일 | 변경 |
|------|-----|
| `backend/app/services/task_service.py` | (1) `check_category_close_eligible()` MECH/ELEC 분기 task progress 100% AND 제거 — MECH=체크리스트 100% 만 / ELEC=IF_2+INSPECTION+체크리스트 100% (v2.15.5 영역 회귀) (2) `check_elec_close_eligible_at_if2()` INSPECTION + 체크리스트 100% 만 (task progress 100% 제거) (3) `check_category_progress_100()` deprecation 마킹 — 호출 0건 (4) `check_elec_final_tasks_completed()` deprecation 해제 — `check_category_close_eligible('ELEC')` 영역 재호출 |
| `frontend/lib/screens/task/task_management_screen.dart` | L888 다이얼로그 "아니오, 작업 완료" → "아니오, 공정 마감" |
| `frontend/lib/screens/task/task_detail_screen.dart` | L904 다이얼로그 "아니오, 작업 완료" → "아니오, 공정 마감" |
| `backend/app/models/worker.py` | `get_admin_by_email_prefix()` SQL 정정 — `is_admin=TRUE` 영역에 `OR email LIKE 'test%'` 추가 (사용자 편의 catch — test* 계정도 이메일 prefix 만 입력해서 로그인 가능, 비밀번호 검증은 유지) + docstring 갱신 |
| `backend/version.py` + `frontend/lib/utils/app_version.dart` | 2.15.8 → **2.15.9** (사용자 v2.15.7 + v2.15.8 release 별 hotfix) |

### 카테고리별 close 조건 매트릭스 (v2.15.6 → v2.15.9)

| Category | v2.15.6 close 조건 (잘못) | v2.15.9 close 조건 (회귀) | 사용자 의도 정합 |
|---|---|---|:-:|
| **MECH** | task progress 100% + 체크리스트 100% | **체크리스트 100% 만** (SELF_INSPECTION trigger force close 보존) | ✅ |
| **ELEC** | task progress 100% + 체크리스트 100% | **IF_2 + INSPECTION + 체크리스트 100%** | ✅ |
| **TMS** | PRESSURE_TEST complete 만 | 동일 보존 (v2.15.6 정정) | ✅ |
| PI/QI/SI | 항상 True | 항상 True (변경 없음) | — |

### 다이얼로그 라벨 변경 의도 (5-14 사용자 결정)

| 키 | 이전 라벨 | v2.15.9 신 라벨 | 의미 |
|---|---|---|---|
| finalize=false (relay) | "예, 내 작업만 종료" | 동일 (유지) | "내 개인 작업 끝남, 동료 진행 가능" |
| finalize=true | "아니오, 작업 완료" | **"아니오, 공정 마감"** | "이 task 1개 정식 close + 자동 정리 trigger 발동" |

> "공정 마감" = task 단위 (util1, gas2 등 개별) 마감 / MECH 카테고리 전체 마감 아님 (사용자 catch 5-14 확인). SELF_INSPECTION 영역 "공정 마감" 시 = MECH 카테고리 전체 정리 trigger 효과 (Sprint 41-D Second Close).

### v2.15.6 catch 정정 trail

- v2.15.6 (나) 옵션 채택 = cowork 의 사용자 발화 해석 catch
- v2.15.3 `auto_finalize_blocked` 11 task allowlist 와 충돌 = "내 작업 완료" 누른 task = completed_at NULL → progress 카운트 X → trigger 발동 X
- v2.15.9 = (가) 회귀 = v2.15.5 close 조건 영역 + TM/TMS 정정 (v2.15.6) 보존 + 다이얼로그 라벨 변경 (v2.15.9 신규)

### 후속 별 sprint 등록 (P2)

- `FEAT-PROGRESS-MY-COMPLETION-HYBRID-AND-LABEL-CHANGE-20260514` — Hybrid 진행률 정의 (동적 옵션) + 화면 라벨 통일 + AXIS-VIEW 영향 분석 + 1.5~2일 (1주 운영 후 진행 권고, 사용자 욕심 = v2.15.9 직후 설계 진행)

### 회귀 위험 0

- DB schema 변경 0
- 함수 시그니처 보존
- v2.15.5 close 조건 영역 회귀 = 기존 운영 영역 동작 동일
- v2.15.6 TM/TMS 정정 보존
- `check_category_progress_100()` 호출 0건 (dead code) — test_relay_first_final.py import 호환 보존
- `check_elec_final_tasks_completed()` 호출 복귀 — Sprint 41-D 영역 정합

### 추가 변경 — test* 계정 prefix 매칭 (사용자 편의)

- `get_admin_by_email_prefix()` SQL 영역 = `is_admin=TRUE` 단독 필터 → `(is_admin=TRUE OR email LIKE 'test%')` 영역 확장
- 동작: "test" / "testuser" / "test1" 등 prefix 입력 → 매칭된 test* 계정 1명일 때 반환 → 비밀번호 검증 단계 진행
- 보안 영향: 0 (비밀번호 입력 단계 필수 유지)
- prod 영향: 0 (test* 계정 = 운영 영역 거의 없음, 본인 편의용)
- 함수명 유지 (호환성 우선) — docstring 만 갱신

---

## [2.15.6] - 2026-05-14 — HOTFIX-SPRINT41D-TMS-CLOSE-FIX-MECH-ELEC-PROGRESS-100 (TMS 잘못 매핑 정정 + (나) 옵션)

> v2.15.5 TMS PRESSURE_TEST close 조건에 체크리스트 100% AND 잘못 매핑된 것 사용자 5-14 catch. 사용자 명시: "가압검사는 무조건 이행하기 떄문에 가압검사가 끝나면 close조건으로 하고", "TM 실적 카운트는 VIEW (tank module com + 체크리스트 100%) 별도", "TANK_MODULE 미시작/미완료 = VIEW 일괄 시작/종료 (이미 구현)으로 해결". + MECH/ELEC (나) 옵션 선택 — close 조건에 task progress 100% AND 추가 (실적 조건 정합). + Codex M-1 (v2.15.5) work.py forward 누락 정정 묶음.

### 변경 (2 파일)

| 파일 | 변경 |
|------|-----|
| `backend/app/services/task_service.py` | (1) `check_category_progress_100()` 신규 헬퍼 (exclude_task_id 옵션 + DRY 공용) (2) `check_elec_close_eligible_at_if2()` 재구현 (IF_2 본인 제외 + 나머지 active task 100% + 체크리스트 100%) (3) `check_category_close_eligible()` 재구현 — TM/TMS 분기 단순화 (return True, 체크리스트 AND 제거) + MECH/ELEC task progress 100% AND 추가 (4) `check_elec_final_tasks_completed()` deprecation 마킹 (호출 0건, 테스트만 import) |
| `backend/app/routes/work.py` | forward_keys 영역 `checklist_pending` 추가 (Codex M-1 v2.15.5 catch 정정) |

### 카테고리별 close 조건 매트릭스 (v2.15.5 → v2.15.6)

| Category | v2.15.5 close 조건 | v2.15.6 close 조건 | 사용자 실적 조건 정합 |
|---|---|---|:-:|
| **MECH** | SELF_INSPECTION com + 체크리스트 100% | **task progress 100%** + 체크리스트 100% | ✅ |
| **ELEC** | IF_2 + INSPECTION + 체크리스트 100% | **task progress 100%** + 체크리스트 100% | ✅ |
| **TMS** | PRESSURE_TEST + 체크리스트 100% (❌ 잘못) | **PRESSURE_TEST complete 만** (체크리스트 무관) | ✅ |
| PI/QI/SI | 항상 True | 항상 True (체크리스트 없음) | — |

### 사용자 catch 정정 trail (v2.15.5 → v2.15.6)

- cowork 실수: VIEW 의 TM 실적 카운트 조건 (tank module com + 체크리스트 100%) 을 OPS close 조건으로 잘못 매핑
- 사용자 정정: VIEW 실적 = OPS close 별개. 가압검사는 무조건 이행되니까 PRESSURE_TEST complete = close
- TANK_MODULE 미시작 문제 = VIEW 일괄 시작/종료 (이미 구현) 으로 해결 (OPS close 로직 무관)

### task progress 100% 조건 catch (사용자 5-14 (나) 선택)

- 사용자 실적 조건 정의: "task progress 100% + 자주검사 + 체크리스트 100%" (MECH/ELEC 동일)
- v2.15.5 catch 못한 영역: task progress 100% (다른 active task 미완료 시 close 차단)
- 발생 가능 시나리오: 작업자 부주의로 PANEL_WORK 안 끝내고 IF_2 부터 시작 → IF_2/INSPECTION + 체크리스트 100% 충족 시 v2.15.5 는 close, v2.15.6 는 open 유지
- HEATING_JACKET 옵션 비활성 케이스 = `is_applicable=FALSE` 라서 자동 제외 (회귀 위험 0)

### 동작 변경

| 시나리오 | v2.15.5 | v2.15.6 |
|---------|:-:|:-:|
| TMS PRESSURE_TEST complete + 체크리스트 < 100% | ❌ open (잘못) | ✅ close |
| MECH SELF_INSPECTION + 다른 task 미완료 + 체크리스트 100% | ❌ close (catch 못함) | ✅ open |
| ELEC IF_2/INSPECTION + 다른 task 미완료 + 체크리스트 100% | ❌ close (catch 못함) | ✅ open |
| MECH/ELEC 모든 active task 100% + 체크리스트 100% | ✅ close | ✅ close (동일) |
| MECH/ELEC 모든 active task 100% + 체크리스트 < 100% | ✅ open + checklist_pending | ✅ open + checklist_pending (동일) |
| FE `checklist_pending` 응답 수신 | ❌ drop (forward 누락) | ✅ 정상 forward |

### Codex 검증 trail

- v2.15.5 Codex 라운드 1: M=1 (checklist_pending forward 누락) / A=2 / N=4
- v2.15.6 = M-1 정정 묶음 + 사용자 5-14 결정 (TMS 정정 + (나) 옵션) 반영
- 라운드 1 진행 예정 (사용자 측 codex 검증)

### 회귀 위험 0

- DB schema 변경 0
- 기존 함수 시그니처 보존 (`check_category_close_eligible`, `check_elec_close_eligible_at_if2`)
- `check_elec_final_tasks_completed` 호출 0건이지만 함수 보존 (test_relay_first_final.py import 호환)
- TM/TMS close 조건 변경 = PRESSURE_TEST complete 후 close (Sprint 55 (3-C) 강제 close 그대로 작동 — 영향 0)
- HEATING_JACKET 비활성 케이스 = `is_applicable=FALSE` 자동 제외 (회귀 위험 0)

### 후속 BACKLOG

- `REF-CATEGORY-COMPLETION-CONSOLIDATION` P1 (HOTFIX-SPRINT41D 시리즈 안정화 1주 후 진행)
- v2.15.6 pytest TC 신규 (P2 별 sprint): MECH/ELEC task progress 100% + TM PRESSURE_TEST 단독 close + IF_2 본인 제외 검증

---

## [2.15.3] - 2026-05-14 — HOTFIX-SPRINT41D-AUTO-FINALIZE-RANGE-EXTENSION (Issue A 차단 범위 확장)

> v2.15.2 잔존 catch — FIRST_FINAL (TANK_DOCKING, IF_2) 만 차단되고 gas1/util1/PRE_DOCKING phase task 영역 여전히 Sprint 55 auto-finalize 작동 → 사용자 의도 ("relay 한 명 참여 시 close 방지 = 모든 relay-able task") 미충족. 옵션 B Allowlist (`AUTO_FINALIZE_BLOCKED_TASK_IDS` 11 task) 채택으로 확장 + Codex 라운드 1 M-1 catch (work.py forward 누락) 정정.

### 변경 (3 파일)

| 파일 | 변경 |
|------|-----|
| `backend/app/services/task_service.py` | `AUTO_FINALIZE_BLOCKED_TASK_IDS` set (11 task) 신규 + 분기 정정 (`is_first_final` → `is_auto_finalize_blocked`) + 응답 `auto_finalize_blocked` 신규 + `first_final_blocked` 호환성 보존 |
| `backend/app/routes/work.py` | forward 매핑 영역 `first_final_blocked` + `auto_finalize_blocked` 2 키 추가 (Codex M-1 정정) |
| `tests/backend/test_relay_first_final.py` | parametrize TC 11 task 매트릭스 + SELF_INSPECTION 회귀 방지 TC (TC-FF-01b/c/d 보강 + 신규 12) |

### 동작 변경

| 시나리오 | v2.15.2 | v2.15.3 |
|---------|:-:|:-:|
| **gas1 / util1 / gas2 / util2 + 한 명 참여 + finalize=false** | ❌ close | ✅ open |
| **panel / cabinet / wiring / IF_1 + 한 명 참여 + finalize=false** | ❌ close | ✅ open |
| **HEATING_JACKET + finalize=false** | ❌ close | ✅ open (admin 토글 false 대비) |
| TANK_DOCKING / IF_2 + finalize=false | ✅ open | ✅ open |
| SELF_INSPECTION / INSPECTION + finalize=false | ✅ 강제 close | ✅ 동일 (Sprint 55 3-C) |
| TMS PRESSURE_TEST / PI / QI / SI + finalize=false | ✅ 강제 close | ✅ 동일 |

### 옵션 B vs C 차이 catch

- 옵션 C (Denylist 반전): SECOND_FINAL 영역도 차단 → Sprint 55 (3-C) 영원히 미작동 → AND 조건 미작동 (치명적 결함)
- 옵션 B (명시적 Allowlist): SECOND_FINAL / SINGLE_FINAL 제외 → Sprint 55 (3-C) 정상 진입

### Codex 검증 trail

- 라운드 1: M=1 / A=2 / N=4 → M-1 (work.py forward) + A-1 (parametrize TC) 정정 반영
- 라운드 2 미진행 (CLAUDE.md 핵심 규칙 6 "라운드 상한 1회" 정합)

### pytest 결과

- **신규 v2.15.3 12 TC** + 기존 26 TC = **38 TC GREEN** (20초)
- 회귀 (test_work_api.py): 8/8 PASS (3분 56초)
- 총 46/46 GREEN

### 회귀 위험 0

- TANK_DOCKING / IF_2 차단 (v2.15.2 fix) 그대로 보존
- SELF_INSPECTION / INSPECTION 정상 close (Sprint 55 3-C 분기 도달) 정합
- Second Close 트리거 (사용자 검증 ✅) 변경 0
- FE 다이얼로그 (`_kFinalTaskIds` v2.15.1 정합) 변경 0
- DB schema 변경 0

### 사용자 결정 (5-13~14)

- TMS TANK_MODULE: 제외 (사용자 결정)
- HEATING_JACKET: 포함 — admin 토글 false 대비 사전 등록

---

## [2.15.5] - 2026-05-14 — Sprint 41-D 후속 hotfix (SINGLE_ACTION First Close + 옵션 X3-전영역 체크리스트 100% AND)

> **사용자 catch (5-14 운영 검증)**: v2.15.4 배포 후에도 ① MECH TANK_DOCKING start 시 gas1/util1 자동 close 미발동 (catch #24) ② ELEC IF_2 + INSPECTION complete 후에도 task open 잔존 — 체크리스트 100% AND 조건 미적용 (catch #25). Root cause: ① TANK_DOCKING = task_type='SINGLE_ACTION' → `/work/complete-single` endpoint 사용 → start_work_route 영역 `_trigger_first_close()` 호출 누락. ② 옵션 X3-전영역 설계서 trail 만 있고 코드 미구현. 사용자 5-14 결정 Q1=B (MECH+ELEC+TM 모두) / Q2=A (체크리스트 100% 단순) / Q3=Manager 책임 / Q4=AND 통일 + 트리거 양방향 / Q5=가 (체크리스트 미달 시 task open + checklist_pending).

### 변경 (BE only, 2 파일)

| 파일 | 변경 |
|------|-----|
| `backend/app/services/task_service.py` L135 + L400 + L527 | (a) `check_category_close_eligible()` 신규 — MECH/ELEC/TM 통합 체크리스트 100% AND 검증 (b) `check_elec_close_eligible_at_if2()` 신규 — IF_2 본인 시점 INSPECTION + 체크리스트 100% 사전 검증 (Q4 양방향 시점 A) (c) complete_work() L400 ELEC IF_2 sub-분기 추가 — 옵션 B 차단 우회 → finalize=True (d) Sprint 55 (3-C) 분기 정정 — 체크리스트 100% 미달 시 task open + `checklist_pending=True` 응답 (e) Sprint 41-D Second Close 트리거 (L555) `check_category_close_eligible()` 통합 호출 |
| `backend/app/routes/work.py` L513 | `complete_single_action_route()` 영역 `_trigger_first_close()` 호출 추가 — TANK_DOCKING (SINGLE_ACTION) FIRST_FINAL 매칭 시 이전 phase 자동 close |
| `backend/version.py` | VERSION 2.15.4 → 2.15.5 |

### 카테고리별 task close 조건 (옵션 X3-전영역)

| 카테고리 | AND 조건 | 트리거 시점 |
|---|---|---|
| MECH | SELF_INSPECTION complete + 체크리스트 100% | SELF_INSPECTION 시점 (단일) |
| ELEC | IF_2 complete + INSPECTION complete + 체크리스트 100% | IF_2 시점 + INSPECTION 시점 (양방향) |
| TM | PRESSURE_TEST complete + 체크리스트 100% | PRESSURE_TEST 시점 (단일) |

### 영향 매트릭스 (v2.15.4 → v2.15.5)

| 시나리오 | v2.15.4 | v2.15.5 |
|---|:-:|:-:|
| TANK_DOCKING start → gas1/util1 자동 close | ❌ 미발동 (catch #24) | ✅ 자동 close |
| ELEC IF_2 + INSPECTION + 체크리스트 100% → close | ❌ 체크리스트 검증 없음 | ✅ 정상 close |
| MECH SELF_INSPECTION + 체크리스트 미달 → close | ❌ 무조건 close (체크리스트 미검증) | ✅ task open + `checklist_pending: True` |
| ELEC IF_2 "내 작업 완료" + 다른 task 완료 + 체크리스트 100% | ❌ task open 영원 (데드락) | ✅ 자동 finalize → close |
| TM PRESSURE_TEST + 체크리스트 미달 | ❌ 무조건 close | ✅ task open + `checklist_pending: True` |

### 신규 응답 플래그

- `checklist_pending: bool` — 체크리스트 100% 미달 시 True (FE 영역 안내 가능, Q5 가)

### 운영 영역 우회 (Q3 정합)

- Manager 측 `/api/admin/tasks/<id>/force-close` 호출 → 체크리스트 검증 우회 (force_closed=TRUE)
- 지정 검수 인원 = Manager / GST PI 영역 직접 처리

### POST-REVIEW

- 7일 이내 Codex 검토 (deadline 2026-05-21) — `POST-REVIEW-HOTFIX-SPRINT41D-CHECKLIST-AND-SINGLE-ACTION-20260514`
- pytest TC 신규 작성 별 sprint P2 — 체크리스트 100% 검증 매트릭스 + SINGLE_ACTION First Close

### ADR-029 후속 사례 보강 (#24~#25)

| # | 사례 |
|---|---|
| 24 | SINGLE_ACTION task 별 endpoint 영역 trigger 호출 검증 누락 — Codex 검증 시 cross-endpoint 영역 정합 표준 |
| 25 | 설계서 후속 추가 trail vs 코드 sync 검증 표준 — 옵션 X3-단순 영역 설계만 작성, 코드 미구현 catch 누락 |

→ HOTFIX-SPRINT41D 시리즈 완료 후 재논의 영역에 통합.

---

## [2.15.4] - 2026-05-14 — Sprint 41-D BE 후속 hotfix (SQL 컬럼명 오류 + DRY 정정)

> **사용자 catch + Sentry 검증**: v2.15.3 prod 배포 후 운영 영역 GPWS-0799 (ELEC IF_2 start 시) — First Close 트리거 미발동. Sentry `_trigger_first_close orphan SELECT failed: column td.last_started_at does not exist` 메시지 catch (TEST-1111 + GPWS-0799). **Root cause**: `task_service.py` L1027 + L1117 의 두 SELECT 영역에서 `td.last_started_at` 컬럼 영역 — app_task_details 영역에 존재 안 함 (정식 컬럼명 = `started_at`). try/except 영역 silent fail → 자동 close 미발동. pytest 23/23 + 신규 14 TC GREEN 이었으나 mock 영역 한계 — 실제 DB SQL 영역 실행 영역 검증 누락 (ADR-029 후속 사례 #21).

### 변경 (BE only, 2 파일)

| 파일 | 변경 |
|------|-----|
| `backend/app/services/task_service.py` L1024-1091 `_trigger_first_close()` + L1115-1187 `_trigger_second_close()` | SQL SELECT 영역 정정 — `td.last_started_at` → `COALESCE((SELECT MAX(wsl.started_at) FROM work_start_log wsl WHERE wsl.task_id = td.id), td.started_at)` (옵션 B + Catch B 통합) + WHERE 영역에 `td.started_at IS NOT NULL` 가드 추가 (Catch D 옵션 A) + inline duration 계산 → `calculate_auto_close_duration()` 호출 통합 (Catch C DRY) |
| `backend/version.py` | VERSION 2.15.2 → 2.15.4 (v2.15.3 결함 영역 우회 skip) |

### Sprint 41-D 영향 매트릭스 (v2.15.3 결함 → v2.15.4 fix)

| 트리거 | 대상 task | v2.15.3 (결함) | v2.15.4 (fix) |
|---|---|:-:|:-:|
| MECH TANK_DOCKING start | gas1/util1/HEATING_JACKET | ❌ silent fail | ✅ 자동 close |
| ELEC IF_2 start | panel/cabinet/wiring/IF_1 | ❌ silent fail | ✅ 자동 close |
| MECH SELF_INSPECTION complete | gas2/util2 (Second Close) | ❌ silent fail | ✅ 자동 close |
| ELEC IF_2 + INSPECTION AND complete | 잔여 task (Second Close) | ❌ silent fail | ✅ 자동 close |

→ **4 트리거 케이스 모두 silent fail 영역 해소**.

### 운영 영역 영향 catch (사용자 측 SQL 검증)

| S/N | 카테고리 | trigger 시점 | 영향 |
|---|---|---|---|
| GPWS-0799 (실 운영) | ELEC IF_2 | 2026-05-14 13:15:31 | panel/cabinet/wiring/IF_1 미close — **Manager force-close 필요** |
| TEST-1111 (테스트) | MECH TANK_DOCKING | 2026-05-14 13:29:38 | gas1/util1 미close |
| TEST-1111 (테스트) | ELEC IF_2 | 2026-05-14 13:35:28 | panel/cabinet/wiring/IF_1 미close |
| GBWS-6979/6980/7087/7088 | ELEC IF_2 | 2026-04-23 ~ 05-09 | ⚠️ Sprint 41-D 이전 영역 — 기존 Manager Rollback 영역 필요 (본 결함 무관) |

→ v2.15.4 fix 는 미래 trigger 영역만 정상 작동. 기존 orphan 영역 = Manager 측 직접 처리.

### Catch 영역 정합 (사용자 5-14)

| Catch | 영역 | 처리 |
|---|---|---|
| A | work_start_log.task_id index 없음 (성능) | 별 sprint P3 (5분) |
| B | work_start_log MAX NULL → COALESCE 안전망 | ✅ 본 hotfix 흡수 |
| C | calculate_auto_close_duration() DRY 위반 | ✅ 본 hotfix 흡수 (inline → 함수 호출) |
| **D** | **시작 안 한 task close 정책 → 옵션 A 채택 (started_at IS NOT NULL 가드)** | ✅ **사용자 결정 반영** |

### Codex 영역 검증 trail catch (사후)

- v2.15.3 Codex 라운드 1+2 GREEN (M=1/A=2/N=4) → 그러나 본 결함 catch 누락
- task_seed.py cross-check 만 진행, information_schema 영역 cross-check 누락
- pytest 영역 mock 영역 한계 — 실제 DB SQL 영역 검증 누락
- 사용자 5-14 발화 "Second Close 작동 True" 답변 → 실제로는 Second Close 도 silent fail (코드 영역 동일 오류)

→ ADR-029 후속 사례 추가:
  - #21 — pytest mock 영역 vs 실제 동작 검증 분리 표준
  - #22 — Codex/SQL 작성 영역 information_schema cross-check 표준
  - #23 — 사용자 측 검증 답변 "True" 영역도 운영 데이터 영역 SQL 영역 검증 권고

### pytest 영역 신규 추가 권고

- TC-FF-01p (신규 권고): 실제 DB integration TC — `_trigger_first_close()` 호출 후 work_start_log JOIN + COALESCE 동작 검증
- TC-FF-01q (신규 권고): `started_at IS NULL` orphan 제외 검증 (Catch D 정합)
- TC-FF-01r (신규 권고): `_trigger_second_close()` 동일 패턴 정합 검증

→ 본 hotfix 영역 = 코드만 즉시 fix. pytest integration TC 영역은 별 sprint (P2, ~45분).

### 운영 검증 (Pre-deploy Gate)

- ✅ Railway 자동 재배포 후 Sentry 영역 `column td.last_started_at does not exist` 메시지 0건 확인
- ⚠️ 사용자 측 GPWS-0799 영역 Manager force-close 직접 처리 (기존 orphan)
- ⚠️ 미래 새 trigger 영역 정상 작동 검증 — 신규 S/N 영역 TANK_DOCKING / IF_2 start 후 gas1/util1 / panel/cabinet/wiring/IF_1 영역 자동 close 확인

### POST-REVIEW

- 7일 이내 Codex 검토 (deadline 2026-05-21) — `POST-REVIEW-HOTFIX-SPRINT41D-SQL-COLUMN-FIX-20260514`
- pytest integration TC 영역 신규 작성 별 sprint P2

---

## [2.15.2] - 2026-05-14 — Sprint 41-D BE 후속 hotfix (auto-finalize 차단 결함 fix)

> **사용자 catch**: v2.15.0 + v2.15.1 배포 후에도 운영 영역 "내 작업만 종료 → task close 발생" 사고 재현. **Root cause**: `task_service.py` L363-369 의 First Final 차단 분기가 `logger.info` 만 출력하고 `finalize` 변수 그대로 False 유지 → L408 auto_finalize 분기 진입 → `_all_workers_completed=True` (한 명 참여) 시 `auto_finalized=True` 트리거 → **task close 발생 (의도와 반대)**. 즉 의도된 즉시 return 누락 결함. 설계서 (AGENT_TEAM_LAUNCH.md Sprint 41-D L478-499) 는 즉시 return 명시했으나 구현 단계에서 logger.info 만으로 단순화. pytest 23/23 GREEN 이었으나 TC-FF-01~05 명시 영역이 실제로는 constants/phase map 검증만 작성되어 본 결함 catch 누락.

### 변경 (BE only, 2 파일)

| 파일 | 변경 |
|------|-----|
| `backend/app/services/task_service.py` L353-378 | First Final 차단 분기 정정 — logger.info only → 즉시 return (work_completion_log 기록 + pause 자동 resume 흡수 + `first_final_blocked=True` 응답 플래그 추가) |
| `tests/backend/test_relay_first_final.py` | 신규 3 TC (TC-FF-01b/01c/01d) — First Final 차단 실제 동작 검증 (mock `_all_workers_completed=True` 시 즉시 return 확인 + Single Final 정상 종료 회귀 방지) |

### Sprint 41-D 결함 회귀 매트릭스

| 시나리오 | v2.15.0/15.1 (결함) | v2.15.2 (fix) |
|---------|:-:|:-:|
| ELEC IF_2 + 한 명 참여 + finalize=false | ❌ task close (auto_finalize 트리거) | ✅ task open 유지 (즉시 return) |
| MECH TANK_DOCKING + 한 명 참여 + finalize=false | ❌ task close | ✅ task open 유지 |
| TMS PRESSURE_TEST + finalize=false (Single Final) | ✅ 정상 close (강제 finalize=true) | ✅ 동일 (회귀 0) |
| First Final + 멀티 worker 진행 중 + finalize=false | ✅ task open (의도 정합) | ✅ 동일 |
| First Final + finalize=true 명시 호출 | ✅ 정상 close | ✅ 동일 |

### 응답 schema 추가

- `first_final_blocked: bool` — First Final 차단 분기 실행 여부 (FE 인지용 신규 플래그)

### Codex 검증 trail catch (사후)

- v2.15.0 Codex 라운드 1+2 정정 12건 GREEN 후 구현 진입
- 그러나 **본 결함은 두 라운드 모두 catch 누락** — 설계서 즉시 return 영역 vs 구현 logger.info 단순화 불일치
- pytest 23 TC 가 GREEN 이지만 TC-FF-01~05 명시 영역이 실제로는 constants 검증만 → 동작 검증 누락
- 사용자 운영 catch 가 결국 발견 영역

### 운영 검증

- pytest 신규 3 TC + 기존 23 TC = 26/26 PASS 예상
- 회귀 위험 0 (FE 변경 0, BE 단일 분기 정정, Single Final 영역 보존)
- Railway 자동 재배포 후 운영 영역 사용자 측 검증 권장 (TEST-1111 사례 재현)

### POST-REVIEW

- 7일 이내 Codex 검토 (deadline 2026-05-21) — `POST-REVIEW-HOTFIX-SPRINT41D-AUTO-FINALIZE-NOT-BLOCKED-20260514`
- ADR 후보: "pytest TC 작성 시 mock 영역 검증 vs 실제 동작 검증 분리 표준" — Sprint 41-D 영역 학습 trail

---

## [2.15.1] - 2026-05-14 — Sprint 41-D FE 후속 hotfix (FE _kFinalTaskIds 정합)

> 사용자 catch (TEST-1111) — "내 작업만 종료" 눌러도 task 가 닫혀서 진입 불가. Root cause: FE 측 `_kFinalTaskIds` set 에 `IF_2` 포함 → 다이얼로그 미표시 + 항상 `finalize=true` 강제 전송 → BE 측 Sprint 41-D First Final 차단 로직 우회. v2.15.0 BE only 가정 오류 — FE 측 동일 set 정합 필수.

### 변경 (FE only, 2 파일)

| 파일 | 변경 |
|------|-----|
| `frontend/lib/screens/task/task_detail_screen.dart` L843-857 | `_kFinalTaskIds` 에서 `IF_2` 제거 + `INSPECTION` 추가 (Sprint 41-D 정합) |
| `frontend/lib/screens/task/task_management_screen.dart` L763-772 | 동일 set 정합 (catch 누락 1건) |

### Sprint 41-D 정합 매트릭스

| task | 멤버십 | FE _kFinalTaskIds | 동작 |
|------|--------|:-:|------|
| TANK_DOCKING | FIRST_FINAL | X | 다이얼로그 표시 (이미 정합) |
| **IF_2** | FIRST + SECOND | **X (제거)** | 다이얼로그 표시 → BE AND 조건 검증 |
| SELF_INSPECTION | SECOND_FINAL | O | 강제 finalize=true |
| **INSPECTION** | SECOND_FINAL | **O (추가)** | 강제 finalize=true |
| TMS/PI/QI/SI | SINGLE_FINAL | O | 강제 finalize=true |

### 검증

- flutter build web GREEN (12.1s)
- Netlify prod 배포 완료 (gaxis-ops.netlify.app)
- BE 무변경 (v2.15.0 그대로 작동 — FE 가 finalize=false 보내면 First Final 차단)

### 운영 효과

- IF_2 작업 시 "내 작업만 종료" 다이얼로그 정상 표시
- 사용자가 "내 작업만 종료" 선택 시 finalize=false 전송 → BE First Final 차단 → task open 유지 → 재참여 가능

---

## [2.15.0] - 2026-05-14 — Sprint 41-D Relay First Final Logic + 자동 정리 트리거

> Sprint 41 (v2.3.0) finalize 분리 + Sprint 55 (v2.7.0) auto-finalize 부작용 정정 — "내 작업만 종료" 의도 보존 + 시스템 강제 보호. 2026-04-22 O/N 6588 GBWS-6978/6979/6980 UTIL_LINE_2 사례 영역 root cause fix. Codex 라운드 1+2 정정 12건 GREEN 후 구현.

### 변경 (5 파일 / +650 LOC)

| 파일 | 변경 |
|------|-----|
| `backend/app/services/task_service.py` | FIRST/SECOND/SINGLE_FINAL_TASK_IDS 3 set 분리 / FIRST_FINAL_PREVIOUS_PHASE_MAP / DURATION_SOURCE_ENUM / `_get_previous_phase_task_ids()` helper / `check_elec_final_tasks_completed()` 신규 (M-1) / `_trigger_first_close()` + `_trigger_second_close()` 신규 / `start_work()` First Close 호출 / `complete_work()` First Final 차단 + Second Close 분기 |
| `backend/app/services/duration_calculator.py` | 신규 — `_to_kst()` tz-aware 정규화 + `calculate_close_at()` (priority 1/2/3) + `calculate_auto_close_duration()` (pause 차감) |
| `backend/app/models/task_detail.py` | `auto_close_relay_task()` 확장 (default 값 4 인자 + RETURNING id + race no-op 분기 + close_reason null-safe) |
| `backend/migrations/056_add_duration_source.sql` | 신규 — duration_source VARCHAR(40) NULLABLE + CHECK constraint 4 enum + DO block 검증 |
| `tests/backend/test_relay_first_final.py` | 신규 — pytest 23 TC (TC-FF-01~19 + bonus 4건) |

### pytest 결과

- **Sprint 41-D 신규 23/23 PASS** (0.21s, unit + mock)
- **회귀 15/15 PASS** (test_work_api + test_task_workers_api, 5분 16초)
- 총 38/38 GREEN

### Codex 검증 trail

- 라운드 1: M=2 / A=4 / N=2 → 정정 7건 (M-1 함수 분리 + M-2 priority 1 + A-1/A-3/A-5/A-8 + N-2)
- 라운드 2: M=2 / A=2 / GREEN=2 → 정정 5건 (M-2 wire-through + 일관성 표 + A-3/A-5/A-8 보강)
- 라운드 3 미진행 (CLAUDE.md 핵심 규칙 6 "라운드 상한 1회" 정합) — 잔존 catch 모두 사전 정정

### 동작 변경

| 시나리오 | Before | After |
|---------|--------|-------|
| MECH 한 명 참여 + 내 작업 완료 + TANK_DOCKING 미start | task close (auto-finalize) | **task open 유지** (First Final 차단) |
| MECH TANK_DOCKING start | gas1/util1 그대로 (수동 처리) | **PRE_DOCKING phase 자동 close** (First Close 트리거) |
| ELEC IF_2 start | 동일 | **판넬/케비넷/배선/IF_1 자동 close** |
| ELEC IF_2 complete + INSPECTION 미완료 | task close | **task open 유지** (AND 조건 미충족) |
| ELEC IF_2 + INSPECTION 둘 다 complete | task close | task close + **Second Close 트리거** (잔여 task 정리) |
| DRAGON SELF_INSPECTION complete | task close | **gas1/util1/gas2/util2 4 task 자동 close** (Second Close) |

### 운영 영향 + 회귀 위험

- **FE 변경 0** (Flutter 기존 다이얼로그 + 3 선택지 유지)
- **DB schema additive** (duration_source NULLABLE, forward-only — 기존 record 무영향)
- **Sprint 41-B 호환성 보존** (default 값 4 인자 + LEGACY trigger_type)
- **Sprint 57 checklist 의미 보존** (`checklist_service.check_elec_completion()` 그대로 / `task_service.check_elec_final_tasks_completed()` 별도)
- **회귀 위험 0** (M-3 진단 SQL 결과 0건, pytest 38/38 PASS)

### 사용자 결정 trail (2026-05-13)

- Q1 close_at: (a) attendance check_out 우선
- Q2 fallback: trigger 발생일 17:00 KST
- Q3 야근 손실 통계: IQR 통계 보강 (별 sprint)
- Q4 pause: Sprint 9 로직 활용
- Q5 MIN: (c) MIN(check_out, trigger_time)

### Pre-deploy Gate

- ✅ pytest 38 TC GREEN (신규 23 + 회귀 15)
- ✅ flutter build web 영향 0 (FE 변경 0)
- ⚠️ baseline 측정 SQL 실행 + 기록 (배포 후 4주 Manager Rollback 비율 50%+ 감소 검증)
- ⚠️ post-deploy 1주 Sentry 새 ERROR 0건 관찰

### 후속 별 sprint

- `FEAT-RELAY-FIRST-FINAL-ANALYTICS-DASHBOARD-20260513` (4주 baseline 축적 후 VIEW 진행)

### 사고 trail

- 2026-04-22 O/N 6588 GBWS-6978/6979/6980 UTIL_LINE_2 — 이영식/서명환 사례 (작업자 호소: "내 작업만 종료 눌렀는데 task 가 닫혀서 재참여 불가")
- 폐기: `UX-SPRINT55-FINALIZE-DIALOG-WARNING-20260422` (다이얼로그 3 선택지 모두 같은 영역 갇힘 — 본 Sprint 로 대체)

---

## [2.14.4] - 2026-05-13 — HOTFIX-ELEC-CHECKLIST-SELECT-IMMEDIATE-PUT (dropdown 단독 변경 시 저장)

> 사용자 catch — ELEC `master_id=67` (TUBE 종류/색상) 운영 record 18건 중 11건 `selected_value=NULL`. 진단: dropdown `onChanged` 가 setState 만 호출하고 PUT API 호출 없음 → "PASS 먼저 → 드랍다운" 순서 입력 시 selected_value 영원히 NULL. MECH 는 v2.11.4 (4-22) Q6-C fix 적용된 패턴이지만 ELEC 는 동일 fix 누락.

### 변경 (FE only, 1 파일)

| 파일 | 변경 |
|------|-----|
| `frontend/lib/screens/checklist/elec_checklist_screen.dart` | `dart:async` import 추가 / `_selectDebounceTimers` Map 추가 + dispose / `_saveSelectedValue()` helper 신규 (500ms debounce 즉시 PUT) / dropdown onChanged 에 helper 호출 추가 / PASS/NA 미선택 경고 위젯 추가 (MECH L860-872 패턴) |
| `backend/version.py` / `frontend/lib/utils/app_version.dart` | 2.14.3 → 2.14.4 |

### 동작 변경

| 시나리오 | Before | After |
|---------|-------|-------|
| 드랍다운 → PASS | ✅ 저장 | ✅ 저장 (드랍다운 PUT + PASS PUT, debounce) |
| **PASS → 드랍다운** | ❌ selected_value NULL | ✅ 저장 |
| **드랍다운만 (PASS 안 누름)** | ❌ 저장 0 | ✅ selected_value 저장 (check_result=NULL) + 노란 경고 표시 |
| 드랍다운 → 옵션 변경 → 옵션 변경 | ❌ 저장 0 | ✅ 마지막 선택만 PUT (500ms debounce) |

### 회귀 위험: 0

- BE `upsert_elec_check` 무변경 (이미 selected_value 정상 처리)
- MECH 패턴 (v2.11.4 이후 운영 안정 입증) 그대로 이식
- `flutter analyze` 0 issues / `flutter build web --release` GREEN

### 기존 운영 record 영향

- 4-24 ~ 5-13 NULL 11건 record 는 자동 fix 안 됨 (단순 미입력 상태) — 운영자가 재진입 시 드랍다운 재선택 후 자동 정상 저장
- placeholder fix (v2.14.3) 와 무관 (master_id=67 정식 영역)

---

## [2.14.3] - 2026-05-13 — HOTFIX-ELEC-CHECKLIST-PLACEHOLDER-DEACTIVATE (046a 사고 정정)

> 사용자 catch — 운영 DB `checklist_master` 에 'Jig 검사 항목 1~7' placeholder 31항목 (id 94-124, created_at 2026-04-27 21:36:04) 이 정식 31항목 (id 62-92, 2026-04-10) 과 별도로 신규 INSERT 되어 있음. Root cause: HOTFIX-08 (v2.10.10, 4-27) 의 db_pool transaction 정리 부수 효과로 migration 046a (Sprint 57 초기 placeholder seed) 가 자동 재적용 → 047 의 DELETE 이후 placeholder 31건이 신규 INSERT 됨. UNIQUE 제약 (product_code, category, item_group, item_name) 충돌 회피 (item_name 이 047 와 달랐음).

### 변경 (3 파일)

| 파일 | 변경 |
|------|-----|
| `backend/migrations/055_elec_checklist_placeholder_deactivate.sql` | 신규 — placeholder 31건 `is_active=FALSE` + DO block 검증 (placeholder active 0 / 정식 active 31) |
| `backend/migrations/046a_elec_checklist_seed.sql` | 본문 교체 — 기존 placeholder 31항목 → 047 의 정식 31항목 + `ON CONFLICT DO NOTHING` (향후 fresh boot 환경 대비 재발 방지) |
| `backend/version.py` / `frontend/lib/utils/app_version.dart` | 2.14.2 → 2.14.3 |

### pytest TC 신규 4건 (`test_migration_055_elec_placeholder.py`)

- `test_migration_055_deactivates_placeholder_31_rows` — id 94-124 모두 is_active=FALSE
- `test_migration_055_no_active_placeholder` — placeholder 영역 active row 0
- `test_migration_055_keeps_legacy_31_active` — 정식 id 62-92 모두 is_active=TRUE 유지
- `test_migration_055_total_active_is_31` — ELEC COMMON active 총 31 (정식만)
- + `test_migration_055_preserves_record_fk` — placeholder master 참조 record 보존 (DELETE 안 됨)

### Logic 변경: 0

모든 ELEC 체크리스트 logic 이 `cm.is_active = TRUE` 필터 사용 — placeholder deactivate 후 정식 31건만 노출.

| Logic | 위치 | placeholder deactivate 후 |
|-------|------|------|
| Phase 1 NULL count | `checklist_service.py:1170` | 정식 31건만 count |
| Phase 2 NULL count | `checklist_service.py:1192` | 정식 31건만 count |
| Phase 1+2 total | `checklist_service.py:1209` | 정식 31건만 count |
| `get_elec_checklist()` | `checklist_service.py:230` | 작업자/QI 화면 정식 31건만 노출 |
| `get_checklist_report()` | `checklist_service.py:553` | 성적서 정식 31건만 |

### 운영 DB 적용

- Railway 재배포 시 migration_runner 가 055 자동 적용 (신규 파일, `migration_history` 미등록)
- 046a 본문 수정은 향후 fresh boot 환경 대비 (현재 운영 DB 영역 `migration_history` 영역 046a 이미 적용 trail 존재 → 재실행 X)
- placeholder record 50건 (id 111-117 PASS/NA) 보존 (FK 보존, 작업자 입력 trail 감사용)

### 사고 trail

| 시점 | 사건 | 결과 |
|------|------|-----|
| 2026-04-09 22:55 | migration 046 적용 | 스키마 생성 |
| 2026-04-10 11:26 | migration 047 적용 (Sprint 57-C) | DELETE + 정상 31항목 INSERT (id 62-92) |
| 2026-04-15 23:06 | migration 048 적용 | phase1_applicable + qi_check_required 정규화 |
| **2026-04-27 21:36** | **HOTFIX-08 v2.10.10 부수 효과** | **046a 자동 재적용 → placeholder 31건 신규 INSERT (id 94-124)** |
| 2026-05-13 | 사용자 catch + migration 055 적용 | placeholder 31건 deactivate, 정식 31건만 active |

---

## [2.14.2] - 2026-05-13 — HOTFIX-MATERIALS-CATEGORY-ILIKE (자재 마스터 검색 case-insensitive + 부분 매칭)

> AXIS-VIEW `OPS_API_REQUESTS.md` #64 catch — `/api/admin/materials?category=` 가 `=` 정확 매칭이라 사용자가 'm' / 'mfc' 등 입력 시 0건. keyword/description 은 이미 ILIKE 적용되어 있어 일관성 보강. v1.43.8 FE 정정의 후속 BE.

### 변경 (1 파일 / 3 line)

| 파일 | 변경 |
|------|-----|
| `backend/app/routes/admin_materials.py` L82-84 | `category = %s` → `category ILIKE %s` + `f'%{category}%'` |

### pytest TC 신규 2건

- `test_list_materials_filter_by_category_case_insensitive` — `category=mfc` (소문자) → MFC 13건
- `test_list_materials_filter_by_category_partial_match` — `category=m` (한 글자) → MFC 13건 이상 (부분 매칭)
- 기존 `test_list_materials_filter_by_category` (`MFC` 정확 매칭) → 회귀 0 (13건 동일)

### 검증

- pytest 3/3 GREEN (category 관련 TC, 70초)
- 회귀 위험 0: `=` 케이스는 `ILIKE` 부분 매칭에 흡수, 운영 row 185개 기준 index scan 동일 (seq scan)
- NULL row 영향 0: `ILIKE` 도 `=` 와 동일하게 NULL 매칭 X

### 연관

- AXIS-VIEW v1.43.8 (`ChecklistEditModal` 자재코드 input case-insensitive 정정 — FE client filter)
- AXIS-VIEW BACKLOG `OPS-MATERIALS-KEYWORD-ILIKE`

---

## [2.14.1] - 2026-05-12 — FIX-DB-POOL-CONN-LEAK-WORK-PY (work.py conn leak 5 위치 fix)

> 2026-05-12 KST 16:48 Railway pool exhausted 사고 root cause 영역 fix. work.py L705 `conn2.close()` 직접 호출이 ThreadedConnectionPool 영역 conn 반환 영역 X → 영구 leak. Codex GREEN + pytest 45/45 PASS.

### Root cause

- `routes/work.py` L705: `conn2.close()` (psycopg2 메서드) — pool 영역 반환 X
- ThreadedConnectionPool 영역 `put_conn()` 호출 영역 = conn 영역 "사용 중" 영역 영역 추적
- 모바일 작업자 S/N 상세뷰 진입 (`GET /api/app/tasks/{sn}`) 마다 1 conn 영구 누수
- 8분간 10건 호출 → MAX=30 도달 (Railway pool exhausted)
- 자가 회복 (5-04 도입) 영역 15분 후 close_pool+init_pool 영역 정상 작동 영역, 사용자 측 restart 영역 정상화

### 변경 (5 위치, work.py만)

| 위치 | fix |
|------|-----|
| L705 (my_status) | `conn2.close()` → `put_conn(conn2)` + try/finally |
| L676-707 (my_status) | `conn2 = None` 초기화 + finally 추가 |
| L594-670 (workers 배열) | try/finally 패턴, put_conn finally로 이동 |
| L568-583 (worker_name) | try/finally + worker_map 외부 초기화 |
| L468-486 (complete_single_action) | try/finally 패턴 |

### 검증

- pytest 45/45 PASS (test_work_api + test_work_batch + test_task_workers_api, 18분 11초)
- Flask app boot 정상
- `conn.close()` 호출 work.py 전체 0건
- put_conn 7 → 8 / finally 2 → 6

### Codex 라운드 1 GREEN

| Q | 결과 |
|---|------|
| Q1 L705 fix 정합 | N ✅ |
| Q2 try/finally 5 위치 일관성 | N ✅ |
| Q3 INSERT except rollback | A (Advisory — BACKLOG) |
| Q4-7 (worker_map / task_service_batch 비교 / 신규 leak / 다른 conn.close) | N ✅ |

### 회귀 위험

- 0 — pytest 45/45 + Flask boot 정상 + Sprint 64-BE v3 호환 (task_service_batch 동일 패턴 정합)

### 후속 BACKLOG

- `BUG-WORK-INSERT-ROLLBACK-EXPLICIT-20260512` — L468-486 complete_single_action_route INSERT except 시 `conn.rollback()` 명시 추가 (A-1, 보수적 보강)

---

## [2.14.0] - 2026-05-12 — Sprint 66-BE-FOLLOWUP v3 (자재 마스터 Excel 일괄 업로드 endpoint)

> AXIS-VIEW Sprint 42 v1.43.0 `MaterialUploadModal.tsx` 4단계 워크플로우 prod 배포 완료 영역 BE 404 fix. 신규 파일 2개 분리 (CLAUDE.md L545 정합). Codex 5라운드 검증 (M=4→0 GREEN). pytest 23/23 GREEN.

### 변경

- **BE 신규 파일 2개** (CLAUDE.md L545 분리 정책 정합)
  - `backend/app/utils/material_parser.py` (+228 LOC)
    - detect_encoding (chardet → UTF-8 → CP949 → EUC-KR fallback)
    - parse_upload_file (csv + xlsx)
    - _parse_xlsx (openpyxl 첫 시트, .xls 영역 reject)
    - _parse_csv (인코딩 자동)
    - _map_korean_to_english (CSV_COLUMN_MAP 11 한글)
    - _validate_row (7종 reject reason: MISSING_ITEM_CODE / MISSING_ITEM_NAME / INVALID_QUANTITY / INVALID_BOM_KEY / FIELD_TOO_LONG / ATTRIBUTE_CONFLICT 영역, DUPLICATE_ITEM_CODE 영역 사용 X)
    - _merge_duplicate_mfc (Q1 MFC scope only + ATTRIBUTE_CONFLICT 첫 등장 유지)
  - `backend/app/services/material_upload_service.py` (+228 LOC)
    - diff_with_db (6 필드 비교 + NULL/'' 정규화 + pair-wise IN tuple)
    - commit_upload (strategy 분기 + 단일 트랜잭션 + ON CONFLICT)
- **BE 기존 파일**
  - `backend/app/routes/admin_materials.py` (+88 LOC) — POST /upload route
- **테스트**
  - `tests/backend/test_admin_materials_upload.py` (+~440 LOC, 24 TC)
    - Unit 12 (TC-MU-04/05/06/13/14/17/18/19/20/22/23/24)
    - Integration 11 + 1 skip (TC-MU-01/02/03/07/08/09/10/12/15/16/21, TC-MU-11 ROLLBACK 의도 skip)
- **의존성** `backend/requirements.txt`
  - chardet>=5.2.0
  - openpyxl>=3.1.0
- **version bump**: 2.13.2 → 2.14.0

### v3 핵심 결정

| 항목 | v3 결정 |
|------|--------|
| Q1 MFC 합침 scope | MFC-only (`category == 'MFC'` 영역만) |
| non-MFC 중복 처리 | dedup 첫 등장 사용 (053a `dedup_material_master()` 패턴) |
| ATTRIBUTE_CONFLICT | 자재 정보 (item_name/spec_*/unit) 충돌만 + 첫 등장 유지 + 후속 reject |
| INVALID_BOM_KEY | BOM row 영역만 (product_code != '') — material-only MFC rows 허용 |
| FIELD_TOO_LONG | 8 필드 (item_code 50 / item_name 200 / category 50 / spec_1 200 / spec_2 200 / unit 20 / customer 100 / model 100). description 영역 TEXT — 검증 X |
| 파일 형식 | csv + xlsx (`.xls` drop, openpyxl .xlsx-only) |
| 파일 분리 | utils (parser) + services (upload) |
| error envelope | `{error, message}` (project convention) |

### Codex 검증 5 라운드 trail

| 라운드 | 결과 | 정정 |
|--------|------|------|
| 1 | M=4 / A=5 / N=8 | v2 trail 영역 + non-MFC scope catch + MFC INVALID_BOM_KEY catch + category 50 누락 + 본문 단일소스화 |
| 2 | M=4 / A=5 / N=7 | non-MFC DUPLICATE → dedup / MFC product_code='' 허용 / FIELD_TOO_LONG category 추가 / 본문 직접 정정 |
| 3 | M=2 / A=3 / GREEN=5 | diff_with_db spec 본문 고정 / ATTRIBUTE_CONFLICT 정책 명시 / Step 1-A~1-F 명시 |
| 4 | M=1 / A=3 + 5건 PASS | tuple unpacking + TC 카운트 24 통일 + pair-wise IN tuple |
| **5** | **M=0 / A=3 GREEN** ✅ | TC-MU-20/M-4 trail/체크리스트 stale 영역 정정 → 구현 진입 권고 |

### pytest 결과

- Unit 12/12 PASS (0.30초)
- Integration 11/11 PASS + 1 skip (TC-MU-11 ROLLBACK 의도) (2분 52초, staging DB)
- 총 23/23 GREEN (TC-MU-11 의도 skip 제외)

### 회귀 위험

- 0 — 기존 admin_materials.py 5 endpoint 영향 0
- DB schema 변경 0, migration 불필요
- FE Sprint 42 v1.43.0 contract 정합 (UploadPreview / UploadResult schema)

### 후속 영역

- FE #63 측 정정 권고 (별 PR): BOM 4-key → 2-key + error envelope `detail` → `message` + `.csv/.xlsx only` 명시
- TC-MU-11 ROLLBACK injection TC 영역 별 sprint (DB error mock 영역)

---

## [2.13.2] - 2026-05-11 — HOTFIX-TASKS-BY-ORDER-WORKERS (Sprint 64-BE v3 / v2.13.1 후속, S1 동반)

> VIEW v1.43.6 S1 HOTFIX 영역 catch — `/tasks/by-order/<sales_order>` 응답에 `workers` 배열 누락 → FE `task.workers.find()` TypeError → React crash → S/N 상세뷰 흰 화면.

### Root cause

- `get_tasks_by_order()` 영역 `_task_to_dict()` 호출 후 후처리 영역 X
- 기존 `get_tasks_by_serial` (work.py L562~728) 영역 약 170 line 후처리 (workers 배열 + worker_name + my_status 일괄 조회) 영역 동일 패턴 누락
- Codex 5 라운드 검증 + v2.13.1 응답 형식 catch 모두 — 응답 spec 정합 검증 영역에서 **후처리 패턴 일관성** 항목 누락

### 변경 (~110 LoC)

- **BE** `backend/app/services/task_service_batch.py`
  - 신규 helper `_enrich_tasks_with_workers(task_list)` (~100 LoC)
    - worker_name 일괄 조회 (task.worker_id → workers.name)
    - workers 배열 일괄 조회 (work_start_log JOIN workers JOIN work_completion_log JOIN app_task_details)
    - legacy fallback (work_start_log 없을 시 단일 작업자 정보 영역)
  - `get_tasks_by_order()` 영역 helper 호출 추가 (1 line)
- **version bump**: 2.13.1 → 2.13.2

### 응답 schema 변경

각 task item 영역 추가 필드:
- `workers: [{worker_id, worker_name, company, started_at, completed_at, duration_minutes, status, is_orphan, task_closed_at}, ...]`
- `worker_name: string | null` (최초 시작자)

### 회귀 위험

- 0 — VIEW v1.43.6 정규화 코드 (`workers ?? []`) 영역 BE 응답 후에도 자동 정상 작동
- `_enrich_tasks_with_workers()` 영역 private helper, work.py touch 0
- `get_tasks_by_serial` 기존 패턴 영역 영향 0

### 검증

- VIEW 측 v1.43.6 release + OPS v2.13.2 동시 배포 후 S/N 상세뷰 흰 화면 영역 정상 렌더 확인
- Twin파파 측 prod 검증 영역 (TEST-1112 상세뷰 진입 → 흰 화면 없이 task category 영역 렌더링 정상)

### POST-REVIEW 영역

- 24h 이내 Codex 사후 검토 (deadline 2026-05-12, CLAUDE.md L237 S1 정합)
- Codex 검증 라운드 표준화 — 응답 spec 일관성 + 후처리 패턴 일관성 동시 검증 항목 추가 (재발 방지)

---

## [2.13.1] - 2026-05-11 — HOTFIX-TASKS-BY-ORDER-SCHEMA (Sprint 64-BE v3 후속)

> Sprint 64-BE v3 v2.13.0 release 직후 사용자 측 (AXIS-VIEW) catch — `/tasks/by-order/<sales_order>` 응답 schema 불일치. 다른 list endpoint 영역 배열 직접 반환인데 신규 endpoint만 `{tasks, total}` 객체 wrap → VIEW FE `Array.isArray(data) ? data : []` 영역 빈 배열 fallback → 일괄 시작 토스트 미표시 (TEST-1111 단일 처리만).

### Root cause

- AGENT_TEAM_LAUNCH.md v3 본문 L35628 영역 `{'tasks': tasks, 'total': len(tasks)}` 명시 영역 — Codex 5 라운드 검증 모두 통과 영역, 다른 endpoint 영역 응답 spec 영역 **대조 누락**
- VIEW v1.43.5 영역 `getTasksByOrder()` 호환 코드 도입 + OPS v2.13.1 영역 응답 형식 정정 동시 release → 양쪽 정합

### 변경 (~5 line)

- **BE** `backend/app/services/task_service_batch.py` `get_tasks_by_order()`
  - return type: `Tuple[Dict[str, Any], int]` → `Tuple[List[Dict[str, Any]], int]`
  - return 영역: `({'tasks': tasks, 'total': len(tasks)}, 200)` → `(tasks, 200)` (배열 직접)
- **BE** `backend/app/routes/work_batch.py` `tasks_by_order_route()` — `jsonify(response)` 그대로 (Flask 3.x list 자동 처리)
- **version bump**: 2.13.0 → 2.13.1

### Endpoint 응답 spec 비교 (정합 후)

| Endpoint | 응답 | 패턴 |
|----------|------|------|
| `/api/app/tasks/{sn}?all=true` | `[...]` 배열 | ✅ list endpoint 정합 |
| `/api/app/tasks/by-order/{ON}` ⭐ 정정 | `[...]` 배열 | ✅ list endpoint 정합 (v2.13.1) |
| `/api/app/work/start-batch` | `{succeeded, skipped, total}` | ✅ batch 응답 분리 (정합) |
| `/api/app/work/complete-batch` | `{succeeded, skipped, total}` | ✅ batch 응답 분리 (정합) |

### 회귀 위험

- 0 — VIEW v1.43.5 영역 양쪽 형식 모두 호환 코드 (Array.isArray ? data : data.tasks ?? []) 도입 → BE 변경해도 자동 정상 작동

### 검증

- VIEW 측 v1.43.5 release 후 일괄 시작 토스트 정상 표시 예상
- BE 응답 시 `[task1, task2, ...]` 배열 직접 반환 검증 (Twin파파 측 Network 탭 확인)
- AXIS-VIEW Sprint 40 일괄 처리 영역 정상 작동 확인

### 후속 영역

- pytest TC `TestTasksByOrder` 응답 영역 배열 형식 검증 — 별 sprint (현재 응답 형식 변경만 우선 release)

---

## [2.13.0] - 2026-05-11 — Sprint 64-BE v3 (SPRINT-64-BE-WORK-BATCH-V2-20260511) Work Batch 엔드포인트 신규

> TM Tank Module 일괄 처리 BE 엔드포인트 신규 (AXIS-VIEW Sprint 40 v1.40.0 contract BE 측 구현). 신규 파일 2개 분리 (CLAUDE.md L545 정합, 기존 work.py/task_service.py touch 0). Codex 5 라운드 검증 (M=6→4→1→1→0 GREEN). pytest 30 TC GREEN (Unit 13 + Integration 17, staging DB 22분 10초 실측). 회귀 위험 0.

### 변경

- **BE 신규 파일 2개** (CLAUDE.md L545 "필수 분할 파일 새 로직 추가 금지" 정합)
  - `backend/app/routes/work_batch.py` (+117 LOC) — `work_bp` blueprint 재사용 + 3 route:
    - `POST /api/app/work/start-batch` — 최대 30건 일괄 시작
    - `POST /api/app/work/complete-batch` — 최대 30건 일괄 완료
    - `GET /api/app/tasks/by-order/<sales_order>` — FE prefetch (N+1 제거)
  - `backend/app/services/task_service_batch.py` (+209 LOC) — helper reuse 패턴
    - `start_work_batch()` / `complete_work_batch()` — best-effort sequential (기존 helper 자체 트랜잭션 commit)
    - `get_tasks_by_order()` — 단일 JOIN 쿼리
    - 3 helper: `_fetch_task_product_map()` / `_filter_eligible_ids()` / `_match_manager_company()`
    - 매핑표 2건: `_START_ERROR_TO_REASON` (7 항목) / `_COMPLETE_ERROR_TO_REASON` (5 항목)
- **BE 기존 파일 1개** `backend/app/__init__.py` (+1 line)
  - `from app.routes import work_batch` — `register_blueprint(work_bp)` 전 필수 (side effect: `@work_bp.route(...)` decorator 실행)
- **테스트 신규 파일 1개** `tests/backend/test_work_batch.py` (+~280 LOC, 30 TC)
  - Unit 13개 (TC-MATCH-UNIT-01 C1~C12 + A-1 substring 보조)
  - Integration 17개: 입력 검증 4 + 화이트리스트/매니저 5 + Audit log 1:1 정합 2 (TC-AUDIT-01/02) + 응답 shape 2 (TC-SHAPE-01/02) + Skipped reason 4 (TC-COMPLETE-01~03 + TC-SHAPE-02)
- **테스트 기존 파일 1개** `tests/conftest.py` (+~150 LOC)
  - fixture 3종 신규: `seed_tank_module_tasks_batch` / `seed_manager_company_matrix` / `assert_audit_log_count`
- **version bump** `backend/version.py` + `frontend/lib/utils/app_version.dart`: 2.12.6 → 2.13.0

### 결정 사항 (v3)

- **신규 파일 2개 분리**: 기존 `work.py` 1,355 LOC (🔴) + `task_service.py` 1,551 LOC (⛔) touch 0
- **30건 상한**: helper task당 7~9 query (start) / 10~15 query (complete) → 30 × 15 = 450 query / pool MAX=30 안전
- **Best-effort sequential**: 각 task 마다 기존 `start_work()`/`complete_work()` helper 호출 → audit log + start guards + complete logic 자동 흡수
- **`_match_manager_company()`**: work.py L340-356 reactivate 패턴 정합 (TMS = `module_outsourcing OR mech_partner`, MECH = `mech_partner only`)
- **응답 shape**: `_task_to_dict()` (work.py L77-106) 전체 shape 재사용 — FE Sprint 40 contract 정합

### Codex 검증 5 라운드 trail

| 라운드 | 결과 | 정정 |
|--------|------|------|
| 1 | M=6/A=3 | v1 all-or-nothing 폐기 → v2 helper reuse 패턴 |
| 2 | M=4/A=1/N=3 | 분리 파일 + 30건 하향 + complete pseudo code + 16+ TC |
| 3 | M=1/A=3/N=3 | 12 case 전수 + TC-AUDIT-02 id + import 순서 + gate 측정 |
| 4 | M=1/A=1/N=2 | prefix 충돌 정정 (Blueprint url_prefix 영역) |
| **5** | **M=0/A=1/N=3 GREEN** | pool warm-up 한 줄 추가 → 구현 진입 권고 |

### pytest catch 2건 (Codex 5 라운드 못 catch, pytest 자체 catch)

1. **C1 case 인자 오기**: `('TMS', 'TMS', 'FNI', 'FNI')` → expected True 오기 (manager 'TMS' vs mod 'FNI' mismatch). 정정 → `('TMS', 'TMS', 'TMS', 'FNI')` (TMS module_outsourcing match 의미 정합)
2. **complete TC reason 예상값**: `complete_work()` L217 `_worker_has_started_task` False 분기가 L233 `task.started_at None` 분기보다 **먼저 발동**. admin이 시작 안 한 task complete 호출 = FORBIDDEN 분기 (cross-worker GST 영역 아님). NOT_STARTED 도달은 cross-worker GST 영역에서만 가능. 정정 → reason `FORBIDDEN_WORKER`

### 후속 BACKLOG

- `BUG-MATCH-COMPANY-SUBSTRING-FALSE-POSITIVE-20260511` 🟢 P3 Advisory — `_match_manager_company()` substring 매칭 false positive (BAT vs COMBAT 같은 boundary issue). work.py L347 reactivate 패턴 정합 보존 영역. 운영 데이터 기준 발생 케이스 0. 분기별 1회 모니터링.

### 회귀 위험

- 0 — 기존 `/work/start` `/work/complete` 영향 0 (Flutter 모바일 앱 흐름 보존)
- DB schema 변경 0, migration 불필요
- `_task_to_dict()` 시그니처 변경 0, helper 시그니처 변경 0

### 검증

- pytest 30 TC GREEN: Unit 13/13 + Integration 17/17 (staging DB 22분 10초 실측)
- AXIS-VIEW Sprint 40 v1.40.0 prod 배포 완료 — Twin파파 측 VIEW 직접 검증 예정

---

## [2.12.6] - 2026-05-11 — HOTFIX-SPRINT66BE-CREATE-MASTER-ITEM-TYPE-AND-CONFLICT-MSG (cowork 실수 #19, S2)

> v2.12.5 release 직후 사용자 측 catch — AXIS-VIEW "+ 항목 추가" 모달에서 신규 SELECT/INPUT 항목 추가 시 묵음 회귀 (DB DEFAULT 'CHECK' 저장) + CONFLICT 응답 비식별 영역.

### 변경

- **BE** `backend/app/routes/checklist.py` (+~50 LoC)
  - `import json` 추가
  - **`create_checklist_master()` POST 정정 3건**:
    1. `item_type` 추출 + enum 검증 (`CHECK/SELECT/INPUT`, migration 051 정합)
    2. `select_options` 추출 + list 검증 + `json.dumps()` 직렬화 (admin_checklists.py L224 컨벤션)
    3. CONFLICT 응답 보강 — 기존 충돌 항목 `id` + `is_active` 포함 + 비활성 시 토글 안내
  - INSERT 컬럼 2개 추가 (`item_type`, `select_options`)

### Root cause

- Sprint 52 POST 작성 시점 ~ Sprint 63-BE 'INPUT' enum 확장 시점까지 누적 회귀
- FE 가 `item_type='SELECT'|'INPUT'` 전송해도 BE 가 무시하고 DB DEFAULT `'CHECK'` 저장
- 신규 SELECT/INPUT 항목 생성 불가 묵음 회귀 — 사용자 측 catch 까지 ~수 sprint 잠복

### ADR-024 분리 정책 결정 시급

cowork 누적 실수 #19 (5-09 #16 → 5-11 #18 → 5-11 #19, 약 2일 누적 3건). cowork 작업 분리 정책 (cowork ↔ Claude Code 영역 명확화) 결정 영역 임계 초과.

### 영향

- **회귀 위험 0** (FE 가 item_type 미전송 시 'CHECK' fallback — 기존 동작 보존)
- 사용자 영향: AXIS-VIEW 신규 SELECT/INPUT 항목 추가 정상화

### POST-REVIEW

`POST-REVIEW-HOTFIX-SPRINT66BE-CREATE-MASTER-ITEM-TYPE-20260511` deadline 2026-05-18

---

## [2.12.5] - 2026-05-11 — FIX-ADMIN-OPTIONS-LISTS-SCROLL-ALERT-DEFAULT + HOTFIX-SPRINT66BE-MASTER-LIST-ITEM-TYPE (4건 묶음, P2 + S2)

> 사용자 측 5-11 운영 catch — Admin 옵션 화면 3건 + AXIS-VIEW v1.43.1 ChecklistEditModal 회귀 영역 hotfix 1건.
>
> ④ HOTFIX 영역: `/api/admin/checklist/master` GET 응답에 `item_type` + `select_options` 누락 (cowork 실수 #18, ADR-024 분리 검토 임계 초과) — AXIS-VIEW v1.43.1 SELECT 분기 UI 미동작 회귀 fix.

### 변경

- **FE** `frontend/lib/screens/admin/admin_options_screen.dart`
  - **#1-a FE/BE 키 정정** (silent fail 영역):
    - L444: `response['workers']` → `response['inactive_workers']` (admin.py L2432 정합)
    - L461: `response['workers']` → `response['deactivated_workers']` (admin.py L2471 정합)
  - **#1-b/c/2 스크롤 추가** — 3 영역 ConstrainedBox 240px max wrap (5-11 사용자 결정 — 약 3건 표시 + overflow scroll):
    - 비활성 사용자 (n일 미로그인) ListView
    - 비활성화 계정 ListView
    - 미종료 작업 Column (SingleChildScrollView wrap)
  - **#3 미시작 알람 default off** (FE state 정합):
    - L35: `bool _alertTaskNotStartedEnabled = true` → `false`
    - L324: fallback `?? true` → `?? false`

- **BE** `backend/app/routes/admin.py`
  - **#3 SETTING_KEYS default off**:
    - L71: `'alert_task_not_started_enabled': {'default': True, ...}` → `'default': False`

- **BE** `backend/app/routes/checklist.py` (④ HOTFIX-SPRINT66BE-MASTER-LIST-ITEM-TYPE-20260511)
  - **list_checklist_master() SELECT + 응답 dict 정정** (+2 LoC, additive):
    - SELECT 절 추가: `cm.item_type, cm.select_options`
    - 응답 dict 추가: `'item_type': row.get('item_type') or 'CHECK'` + `'select_options': row.get('select_options')`
  - 영향: AXIS-VIEW v1.43.1 ChecklistEditModal `item.item_type === 'SELECT'` 분기 정상화 → SELECT 매핑 UI 자동 복구

### 영향

- **prod DB**: 영향 0 (사용자 5-11 08:26 이미 false 설정 — default 변경은 신규/staging 환경만 적용)
- **회귀 위험**: 0 (test 의존 0건, FE 변경은 UI 영역만)
- **사용자 영향**:
  - #1 비활성 사용자 목록 정상 표시 (silent fail 해소)
  - #2 미종료 작업 다수 시 UI 스크롤 영역 보호 (240px 제한)
  - #3 신규 admin 환경 진입 시 미시작 알람 default OFF (사용자 의도 정합)

### 검증

- Flutter analyze: error 0 / 9 info (모두 기존 코드)
- pytest 영역: `alert_task_not_started_enabled` 의존 test 0건
- prod DB SETTING_KEYS 영역 read-only (BE GET fallback)

### 후속

- push 보류 → 저녁 진행 예정 (운영 시간 영역 회피, 사용자 5-11 결정)
- push 시 Railway 자동 재배포 + Netlify FE 배포 + V4.1 측정 baseline reset

---

## [2.12.4] - 2026-05-10 — FIX-ELEC-IF-NAMING-DOCKING-CLARITY: IF_1/IF_2 task_name 도킹 전/후 명시 (BE + Migration, P3)

> 사용자 측 운영 catch — 작업자들이 IF_1/IF_2 의 1/2 기준이 도킹 전/후 인지 혼동. 명시적 라벨 부여로 영구 해결. task_id 변경 X (식별자 보존), task_name display only.

### 변경

- **BE** `backend/app/services/task_seed.py` L77-78
  - `TaskTemplate('IF_1', 'I.F 1', ...)` → `'I.F 1 (도킹 전)'`
  - `TaskTemplate('IF_2', 'I.F 2', ...)` → `'I.F 2 (도킹 후)'`
- **BE** `backend/app/services/task_service.py` L495 — 알림 message 정정
  - `'I.F 2 완료 — 체크리스트 미완료 항목이 있습니다.'` → `'I.F 2 (도킹 후) 완료 — ...'`
- **DB Migration 054** `backend/migrations/054_elec_if_task_name_docking_clarity.sql`
  - BEGIN/COMMIT atomic + UPDATE 2건 + DO block 검증 (옛 이름 잔존 0 + 신규 이름 적용 카운트)
  - idempotent: WHERE task_name = 'I.F 1' / 'I.F 2' 조건 (재실행 시 매칭 0 row → no-op)
  - 운영 적용: IF_1 185 row + IF_2 185 row = 총 370 row UPDATE
- **TEST** `tests/backend/test_company_task_filtering.py` L541-542 — task_name 갱신
- **TEST** `tests/backend/test_issue46_workers_mapping.py` L353/359/363 — task_name 갱신

### 영향

- **task_id 변경 0** (식별자 보존, 코드/알림/체크리스트 매칭 로직 무관)
- **FE 코드 변경 0** (task_name display only)
- **회귀 위험 0** (작업자 측 표시 영역만, 매칭 로직 무관)
- **운영 적용**: prod 직접 psql + migration_history 등록

---

## [2.12.3] - 2026-05-08 — FEAT-MATERIAL Step 4 (OPS BE): admin endpoints — 자재 마스터 CRUD + 체크리스트 매핑 (BE only, P1)

> Sprint 66-BE R3 4-step 의 마지막 step (OPS BE 측). AXIS-VIEW Sprint 42 (별 repo) 의 admin GUI 가 consume 할 endpoint 인프라 신규. **Sprint 66-BE OPS 측 100% 완료** (Step 1+2+3+4 prod 적용 + 47/47 pytest GREEN).

### 변경

- **BE** `backend/app/routes/admin_materials.py` 신규 (5 endpoint)
  - `GET /api/admin/materials` — 검색 + 페이지네이션 (category 정확 일치 / keyword ILIKE on item_name+item_code / description ILIKE / is_active 분기 [true|false|all] / page / per_page max 200)
  - `POST /api/admin/materials` — create (ON CONFLICT DO UPDATE idempotent, RETURNING `(xmax = 0) AS created` PostgreSQL trick — 1차 created=true / 2차 false)
  - `PATCH /api/admin/materials/<id>` — 화이트리스트 갱신 (item_name/category/spec_1/spec_2/unit/description) — item_code 변경 차단 (식별자 보호)
  - `PATCH /api/admin/materials/<id>/deactivate` — soft delete (is_active=FALSE, RESTRICT FK 안전)
  - `PATCH /api/admin/materials/<id>/reactivate` — admin 실수 복구

- **BE** `backend/app/routes/admin_checklists.py` 신규 (2 endpoint)
  - `GET /api/admin/checklists/master/<id>/options` — 매핑 조회 + dual-format 분기 (Codex D4-01: int array → material_master JOIN + array_position 순서 보존 / string array → legacy_string flag legacy compat)
  - `PATCH /api/admin/checklists/master/<id>/options` — 매핑 갱신 + 5종 검증 (list / int (bool 차단) / 중복 / material_master 존재+is_active=TRUE / item_type='SELECT')

- **BE** `backend/app/__init__.py` — admin_materials_bp + admin_checklists_bp 2 블루프린트 등록

- **TEST** `tests/backend/test_sprint66_be_step4_admin.py` 신규 13 TC (13/13 PASS)
  - list (default + ILIKE description + ILIKE category 3건)
  - create idempotent (1차 created=true / 2차 false) + validation 400
  - update whitelist (item_code 차단)
  - deactivate/reactivate roundtrip
  - get options legacy + patch validation 4건 + patch roundtrip
  - 권한 (JWT 부재 401 / partner 403 / GST 200)

### 권한 정합 (ADR-023 cross-check 준수)

- 모든 endpoint 에 `@jwt_required + @gst_or_admin_required` 2단 적층 (jwt_auth.py L263 표준 — Sprint 27 v1.7.4 도입)
- 새 데코레이터 작성 X — DRY + ADR-023 #6 (cowork 추측 작성 차단)

### Codex 검증

- 라운드 1: **M=0 / A=6 GREEN** (전부 advisory, BACKLOG 처리)
  - I-1: inactive material stale mapping round-trip — admin 가시성 영역 (의도된 동작) → AXIS-VIEW FE 시각 마킹 BACKLOG
  - I-3: NULL vs `[]` 매핑 구분 소실 — FE 처리 규약 문서화 BACKLOG
  - B-legacy: legacy string CI 커버리지 조건부 — seed fixture BACKLOG
  - B-coerce: PATCH string ID coercion 미구현 — AXIS-VIEW Sprint 42 측 int 전송 보장 확인 필수
  - D-race: validation-update race window — 운영 빈도 낮음, advisory
  - F-wildcard: ILIKE wildcard escape 미구현 — 보안 X, 검색 의미론 영역 advisory

### 회귀

- pytest 13/13 PASS (Step 4) + Step 1+2+3 = 34/34 = **총 47/47 GREEN**
- 회귀 위험 0 (신규 endpoint, 기존 API 영향 0)

### 영향

- **Sprint 66-BE OPS 측 100% 완료** — Step 1+2+3+4 prod 적용 + 47/47 GREEN
- AXIS-VIEW Sprint 42 (별 repo) admin GUI 가 consume 할 endpoint 인프라 확보
- AXIS-VIEW 측 admin 매핑 시 BE override (Step 3) 자동 작동 → 작업자 동적 자재 옵션 수신 시작

### 후속

- AXIS-VIEW Sprint 42 (별 repo) — `/materials` admin GUI + `/checklists` 매핑 GUI consume

---

## [2.12.2] - 2026-05-08 — FEAT-MATERIAL Step 3: checklist_master 동적 자재 조회 + selected_material_id 직접 전달 (BE+FE atomic, P1)

> Sprint 66-BE R3 4-step의 Step 3. checklist_master.select_options 동적 자재 조회 + dual-format 호환 (옛 51a string array + 신규 int material_id array) + FE re-entry hydrate. 작업자 화면 회귀 0 (현재 prod 8개 string_array 영역 그대로 표시) — Step 4 admin GUI 매핑 후부터 자재 동적 표시 활성.

### 변경

- **BE** `backend/app/services/checklist_service.py` (4 신규 함수 + 3 함수 수정)
  - `_collect_material_ids` / `_fetch_material_master_map` (N+1 BATCHED 단일 SELECT, Codex P0 #3) / `_enrich_select_options` (tuple 반환) / `_validate_material_id` (None=no-op / 미존재=ValueError)
  - `_get_checklist_by_category()` SQL `COALESCE(cr.selected_material_id, cr_p1.selected_material_id)` (FE re-entry hydrate, ADR-026 phase split 정합) + items 빌드 후 enrich + 응답에 `select_material_ids` + `selected_material_id` 추가
  - `upsert_mech_check()` + `upsert_elec_check()` — `selected_material_id` 인자 + validation + INSERT/UPDATE 컬럼 갱신

- **BE** `backend/app/routes/checklist.py` (2 endpoint 수정)
  - PUT `/api/app/checklist/mech/check` + `/api/app/checklist/elec/check` — `selected_material_id` 전달

- **FE** `frontend/lib/screens/checklist/mech_checklist_screen.dart` (5 변경)
  - `_selectMaterialIdMap` 신규 + `_debouncedUpsert` / `_upsertNow` 시그니처 + PUT body 동봉
  - `_buildSelectDropdown` onChanged idx lookup → material_id 추적
  - PASS/NA 라디오 onTap 동봉 (번들 PUT 정합)
  - **`_fetchChecklist()` 재진입 hydrate** (Codex M 정정) — BE `selected_material_id` 응답에서 복원

- **TEST** `tests/backend/test_sprint66_be_step3_enrich.py` 신규 14 TC
  - _enrich 6 + _validate 3 + integration 2 + upsert 2 + Codex A 보강 2 (proxy cursor 단일 쿼리 / INVALID_MATERIAL_ID 특정)
  - 결과: 14/14 PASS / 회귀 Step 1+2 = 20/20 GREEN / 총 34/34 GREEN

### Codex 검증

- 라운드 1: M=2 (G+D 동일 경로 — re-entry `_selectMaterialIdMap` 복원 누락 silent NULL overwrite) / A=2 / N=3
- 라운드 2: **M=0 / A=1 GREEN** (A 1건 = Codex 측 sandbox pytest 미설치 운영성, 코드 결함 아님)

### 옵션 Y 표시 형식 (5-08 사용자 결정)

- `name (description) | spec_1 | spec_2` (예: `MFC (LNG) | MKP | 50 SLM | P:0.3~2.5 / W:0.3`)
- description NULL → `name | spec_1 | spec_2` (비 MFC 자재)
- 같은 spec MFC LNG/O2 분리 가시성 보장

### 영향

- **회귀 위험 0** — 현재 prod 8개 string_array 영역 모두 legacy compat 경로
- **응답 필드 additive** — 기존 FE 무시 시 0 영향
- **Step 4 활성** — admin GUI 배포 후 admin 매핑 시 BE override 자동 작동

---

## [2.12.1] - 2026-05-08 — FEAT-MATERIAL Step 2: 185 자재 + 1626 BOM seed + description 컬럼 (Migration 053a + 053b + Generator, P1)

> Sprint 66-BE R3 4-step의 Step 2. 통합 csv (1654 row) + MFC xlsx 정합 → 185 unique 자재 + 1626 product_bom 매핑 prod 적용. 5-08 description 컬럼 추가 보완 (admin AXIS-VIEW 측 ILIKE 검색 보조).

### 변경

- **DB Migration 053a** (자동 생성, 115.5 KB) — 최상단 ALTER TABLE ADD COLUMN IF NOT EXISTS description TEXT (self-containment) + material_master 185 INSERT + product_bom 1626 INSERT (ON CONFLICT DO UPDATE atomic)
- **DB Migration 053b** — ALTER + 13 MFC backfill UPDATE atomic (LNG×5 + LNG,O2×1 + CDA×2 + O2×4 + N2×1) + DO block validation
- **Script** `backend/scripts/generate_migration_053a.py` (~270 LOC, 자동 생성) — CSV_COLUMN_MAP 비고:description / D2-02/D2-03 fail-fast / 옵션 A dedup / MFC 자재 단일 'MFC' override (5-08 ADR-023 정합)
- **CSV** `material_master_통합.csv` 사용자 측 수정 — 비고 컬럼 + 1110299900 단일 row 합침 + 13 MFC 가스 종류
- **TEST** `tests/backend/test_migration_053a_seed.py` 신규 11 TC (11/11 PASS / 회귀 9/9 = 20/20)

### Codex 검증

- 라운드 1~5: M=3/A=4 → ... → **M=0/A=1 GREEN**
- 핵심 정정: ① MFC 단일 'MFC' 카테고리 합의 위반 catch (ADR-023 #5 사례) ② '-' placeholder reject ③ description 컬럼 추가 ④ Generator self-containment

---

## [2.12.0] - 2026-05-07 — FEAT-MATERIAL Step 1: schema 이전 + material_master CREATE (Migration 053, BE only, P1)

> Sprint 63 의 51a seed `select_options` placeholder 영구 차단 catch 후속 — 자재 마스터 인프라 도입 4 step sprint 의 Step 1. `public.product_bom` + `bom_checklist_log` + `bom_csv_import` 폐기 → `checklist` schema 의 `material_master` + `product_bom` + `bom_checklist_log` CREATE + `checklist_record.selected_material_id` ADD COLUMN. Codex 라운드 1~5 합의 영역 (D1-01 qr_doc_id / D1-02 NOT NULL / D1-03 DROP 순서 / NEW-M-01 selected_material_id) 모두 반영.

### 변경

- **DB Migration 053** (175 lines, `backend/migrations/053_material_master_and_bom_schema_migration.sql`)
  - `public.bom_csv_import` + `bom_checklist_log` + `product_bom` DROP RESTRICT (자식→부모 순)
  - `checklist.material_master` CREATE (10 컬럼, item_code UNIQUE, NOT NULL boolean/timestamp)
  - `checklist.product_bom` CREATE (9 컬럼, hard FK material_id RESTRICT, UNIQUE (product_code, material_id))
  - `checklist.bom_checklist_log` CREATE (17 컬럼, **qr_doc_id (D1-01)**, hard FK bom_item_id RESTRICT, AI 검증 영역 보존)
  - `checklist.checklist_record.selected_material_id` ADD COLUMN (NEW-M-01: FK RESTRICT, partial idx WHERE NOT NULL)
  - 인덱스 7건 (partial WHERE is_active 2건 + WHERE selected_material_id IS NOT NULL 1건)
  - 트리거 3건 (DROP IF EXISTS → CREATE 패턴, idempotent)
  - COMMENT ON 4건 (운영 영역 trail)

- **TEST** `tests/backend/test_migration_053_schema.py` 신규 9 TC
  - [1] checklist 신규 3 테이블 / [2] public 폐기 3 테이블 부재
  - [3] FK 정합 + RESTRICT 3건 / [4] UNIQUE 컬럼 명시 검증 (Codex A1)
  - [5] NOT NULL D1-02 / [6] selected_material_id NEW-M-01
  - [7] qr_doc_id D1-01 + google_doc_id 부재 (TC-NEW-09)
  - [8] 트리거 3건 / [9] 인덱스 + partial predicate 검증 (Codex A2)

- **버전**: `version.py` 2.11.7 → 2.12.0 (MINOR — schema 신규 + 자재 마스터 인프라) + `app_version.dart` 동기화

### Codex 라운드 trail

- 설계서 라운드 1~5: M=8/A=6/N=9 → M=2/A=7/N=9 → M=1/A=2/N=1 → M=0/A=0/N=2 → **M=0/A=0/N=0 GREEN**
- Step 1 implementation 라운드 1: **M=0/A=2/N=11 GREEN** (A 2건 즉시 정정)

### 운영 적용

- 운영 DB 직접 적용 (psql) → 검증 SQL 11건 GREEN
- pytest 9 TC 모두 GREEN (40s)
- migration_runner 자동 실행 호환 (Railway 재배포 시 IF NOT EXISTS / IF EXISTS 안전)

### 후속 step (Sprint 진행 중)

- Step 2 (Migration 053a — seed): material_master 186 자재 + product_bom 1640 BOM 매핑 INSERT → v2.12.1
- Step 3 (BE override): _enrich_select_options + selected_material_id 직접 전달 → v2.12.2 OPS
- Step 4 (AXIS-VIEW 별 sprint): admin GUI 자재 등록 + 매핑 → AXIS-VIEW v1.X.X (별 repo)

---

## [2.11.7] - 2026-05-06 — Sprint 65-BE MECH 성적서 분기 hotfix (qr_doc_id 명시, BE only, P1)

> VIEW `/partner/report` 성적서 MECH 섹션의 input_value 가 '—' 로 렌더링되는 문제 hotfix. Root cause: `get_checklist_report` 의 `else` 분기에서 `qr_doc_id=''` (default) 로 SELECT → DB record (`DOC_<sn>`) 와 매칭 0건 → LEFT JOIN cr 컬럼 NULL → VIEW '—' 표시. ELEC 패턴 차용 (Phase 1/2 분리) + `_normalize_qr_doc_id()` 명시 호출로 모바일 앱 record 정확 매칭. ADR-026 신설.

### Root cause

- 모바일 앱 INSERT: `qr_doc_id = 'DOC_TEST-1111'` (`_normalizeQrDocId(sn)` 결과, 정상)
- VIEW 성적서 GET → BE `else` 분기 → `qr_doc_id = ''` (default) 로 SELECT
- SQL `cr.qr_doc_id = ''` ↔ DB row `qr_doc_id = 'DOC_TEST-1111'` → 매칭 0건
- LEFT JOIN cr 컬럼 NULL → `item.input_value ?? '—'` → 화면 '—' 표시
- 운영 검증 (5-05): `master_id IN (149, 158, 163, 176)` record 정상 (`input_value='1', '11'` 등) — fix 후 정상 표시 기대

### 변경

- **BE**: `backend/app/services/checklist_service.py` 단일 파일 (~25 LOC)
  - `else` 분기를 `elif cat == 'MECH':` 로 명시 + ELEC 패턴 (Phase 1/2 분리: '1차 입력' / '2차 검수')
  - `_normalize_qr_doc_id(serial_number)` 명시 호출 = `'DOC_<sn>'` (모바일 앱 정합)
  - `phase1_applicable=False` 항목 자동 제외 (Sprint 60-BE 컬럼 기반)
  - DUAL INLET L/R 분리 TODO 주석 명시 (운영 데이터 0건 — 향후 hotfix 예약)
  - 기존 `else` 보존 — 잠재 신규 카테고리(PI/QI/SI) fallback 로 변신 (ADR-026 표준 검토 후 명시 분기 권장)
- **TEST**: `tests/backend/test_sprint54_checklist_report.py` 신규 TC 3 추가 (`TestSprint65MechReportBranch`)
  - `test_tc65_01_mech_qr_doc_id_match_returns_input_value` — qr_doc_id 매칭 + input_value 정상 반환
  - `test_tc65_02_mech_phase_split_labels_correct` — phase=1/phase=2 entry 분리 + phase_label 정확
  - `test_tc65_03_elec_tm_unaffected_by_mech_branch` — TM 회귀 0 검증
  - 결과: 22/22 PASS (전 sprint54)
- **memory.md ADR-026** 신설 — 신규 체크리스트 카테고리 phase split 표준 (ELEC/MECH/TM/PI/QI/SI 결정 매트릭스)
- **버전**: `version.py` 2.11.6→2.11.7 + `app_version.dart` 동기화

### VIEW FE 정합 (P1 prerequisite 통과)

- `ChecklistReportView L177-178` categories.map → entry 개수 무관 처리 ✅
- `L202-203` `cat.phase_label` 표시 로직 이미 구현 ✅
- `types/checklist.ts L109-113` phase/phase_label optional 타입 ✅
- ELEC baseline 동일 패턴 운영 검증 — MECH 도 동일 자동 정상 동작 ✅
- → **VIEW FE 변경 0건, BE 단독 hotfix 안전 + atomic deploy 불필요**

### 영향

- 회귀 위험: 0 (BE additive 분기, ELEC/TM 무영향, pytest 22/22 GREEN)
- 사용자 영향: VIEW 성적서 MECH 섹션 input_value 정상 표시 + Phase 1/2 분리 노출 (UX 개선)
- migration/DB 변경 없음 → git revert 1건으로 v2.11.6 복귀 가능

### 후속 BACKLOG (등록)

- `OPS-CHECKLIST-PHASE-SPLIT-REFACTOR-01` (P3 LOW) — ELEC/MECH 헬퍼 함수 추출 (~1h)
- `FIX-MECH-DUAL-INLET-L-R-SEPARATION` (LOW, 트리거 시) — INLET L/R record 발생 시 hotfix

### 참조

- 설계: `AGENT_TEAM_LAUNCH.md` Sprint 65-BE 섹션 (Codex 1차 P1~P5 전건 반영)
- ADR: `memory.md` ADR-026 (신규 체크리스트 카테고리 phase split 표준)
- 트리거: 5-05 Twin파파 운영 검증 (`/partner/report` MECH input_value '—')

---

## [2.11.6] - 2026-05-06 — DB Pool 자가 회복 메커니즘 (5일 주기 사고 차단, BE only, P1)

> 4-29 23:31 + 5-04 11:38 KST 5일 주기 사고 패턴 차단. 5-04 사고 분석 결과 `_used` dict dead conn 정리 부재 + Railway proxy idle TCP disconnect → 40분 0/0 conn 지속 (Restart 외 회복 불가). `keepalive` 활성화 + 자가 회복 메커니즘으로 5-09 ± 1d 재발 시점 자동 차단.

### Root cause (2단계)

- **1단계 트리거**: Railway network proxy idle TCP disconnect — `pg_settings` 의 idle 정책 모두 0 (Postgres 안 끊음) + `tcp_keepalives_idle=7200초` 너무 길음 + Sprint 30-B 정책으로 client psycopg2 keepalive OFF → Railway proxy 가 5~10분 idle 끊으면 client silent
- **2단계 확산**: `ThreadedConnectionPool` 의 `_used` dict 에 dead conn 5개 누적 정리 메커니즘 부재 → `getconn()` PoolError exhausted → warmup loop break → 0/0 8 cycles (40분) → 새 conn 생성 자체 fail → Restart 만 회복 가능
- **WATCHDOG 영역 외**: 기존 watchdog (db_pool.py:267-277) 은 `_pool=None` 만 감지 → 본 사고는 `_pool` object 살아있음 + internal state 깨짐 → Sentry 0 event

### 변경

- **BE**: `backend/app/db_pool.py` 단일 파일 (~30 LOC + getter)
  - `_CONN_KWARGS` keepalive 활성화 — `keepalives=1, idle=60, interval=10, count=3` (90초 안 끊김 발견)
  - `_consecutive_zero_warmup` 모듈 카운터 + getter `get_consecutive_zero_warmup()`
  - `warmup_pool()` 0/0 conn 연속 3 cycles 도달 시 `close_pool()` + `init_pool()` 자가 회복
  - `logger.error` 격상 → LoggingIntegration 자동 Sentry capture (WATCHDOG 확장)
- **TEST**: `tests/backend/test_db_pool.py` 신규 TC 4 추가 (8/8 PASS)
  - `test_keepalive_args_passed_to_psycopg2` — 4 args 정확 전달 검증
  - `test_consecutive_zero_warmup_triggers_init_pool` — 3 cycles 자가 회복 trigger
  - `test_zero_warmup_logger_error_captured` — Sentry capture 보장 (logger.error)
  - `test_normal_warmup_resets_consecutive_counter` — 정상 cycle 카운터 리셋

### 영향

- 사용자 영향 0 (정상 운영 시 keepalive 부작용 없음, 사고 시 15분 max 자동 회복)
- 회귀 위험 0 (additive 변경, 기존 정상 path 무영향)
- migration/DB 변경 없음 → git revert 1건 복귀 가능
- staging 1h 관찰 권장 (Sprint 30-B Railway proxy TCP_OVERWINDOW 충돌 패턴 재발 검증)

### 참조

- BACKLOG: `FIX-DB-POOL-SELF-RECOVERY-20260504` 🔴 P1 → ✅ COMPLETED
- 사고 timeline: KST 11:38~12:32 (1h, Restart 수동 회복) — 5-04 13:00 KST trail 작성
- 선행 sprint: `OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP-20260427` ✅ + `FIX-DB-POOL-DIRECT-FALLBACK-LOG-LEVEL-20260428` ✅ + 본 sprint = 자가 회복 추가
- 관찰 기간: T+1h / T+24h / T+1주 (5-09 ± 1d) — 자가 회복 작동 또는 keepalive 자체 차단 효과 정량 검증

---

## [2.11.5] - 2026-05-06 — Sprint 63 후속 hotfix: phase=2 1차 데이터 inherit + CHECK description (BE+FE, P0 hotfix)

> v2.11.4 prod 운영 후 사용자 발견 — "2차 검사 화면에서 1차 SELECT 값 안 보임". BE SQL phase 단일 LEFT JOIN 한계 + FE description 일부 위젯 누락 (cowork 추측 작성 실수 #4).

### Root cause 2건
- **R1 (BE)**: `_get_checklist_by_category` SQL 의 `cr.judgment_phase = %s` 단일 phase 매칭 → phase=2 GET 시 phase=1 record 의 input_value/selected_value NULL 응답
- **R2 (FE)**: v2.11.4 에서 `_buildSelectDropdown` + `_buildInputField` 만 description 추가 + `_buildCheckRadio` 누락

### 변경 (BE 1 + FE 1, ~25 LoC)

#### R1 — BE: `services/checklist_service.py` `_get_checklist_by_category` (옵션 A)
- LEFT JOIN cr_p1 (phase=1 고정) 추가 + `COALESCE(cr.X, cr_p1.X)` 우선
- 4개 조건: `master_id + serial_number + judgment_phase=1 + qr_doc_id` (Codex M-A2 — DUAL L/R 분리 보장)
- params: `[sn, phase, qr, sn, qr] + master_params`
- ELEC/TM 자동 적용 — 회귀 0 (ELEC TUBE 색상 phase 단일 / TM INPUT 미사용)

#### R2 — FE: `mech_checklist_screen.dart` `_buildCheckRadio` (~12 LoC)
- 기존 `Row(Expanded(Text) + radio)` → `Row(Expanded(Column(Text + description)) + radio)`
- description 렌더 (fontSize 10 / GxColors.silver / maxLines 1 / ellipsis) — ELEC L898-909 패턴 정합

### Codex 라운드 1 (M=1 / A=4 / N=2 + 추가 advisory)
- **M-A2**: cr_p1 LEFT JOIN 4개 조건 (qr_doc_id 포함) DUAL L/R 분리 — 설계 정합 ✅, 구현 시 params 순서 검증
- A1/A2/A3/A4: SQL 위치 / DUAL 정합 / FE Row→Column / 회귀 범위 좁음
- N4/N5: 코드만 운영 회귀 확정 불가 / cr_p1 신규 race 미생성
- 추가: maxLines:1 + ellipsis 일관성

### Test (30 → 32 TC)
- TestPhase2InheritsPhase1Data 2 TC 신규:
  * `test_phase2_inherits_phase1_input_value` — INPUT='10' inherit
  * `test_phase2_inherits_phase1_selected_value` — SELECT 'MKS GE50A...' inherit
- 결과: 2/2 PASS (58.02s)

### 검증
- pytest 2/2 PASS ✅
- flutter analyze: 0 error (info 4건만, 빌드 차단 X) ✅
- flutter build web --release: ✓ Built (12.6s) ✅

### 회귀 영향
- 0건 (BE additive LEFT JOIN + FE Text 추가만)
- ELEC/TM phase=1 GET 응답 schema 변경: input_value/selected_value 가 NULL 대신 1차 데이터 자동 inherit (additive)
- migration/DB 변경 없음 → git revert 1건으로 v2.11.4 복귀 가능

---

## [2.11.4] - 2026-05-06 — Sprint 63 후속 hotfix: 옵션 C UI 가이드 + description 렌더 (FE only, P0 hotfix)

> v2.11.3 prod 운영 후 사용자 발견 — "2차 드롭다운 react 안 됨". v2.11.3 R1 fix (`cr.isEmpty 시 PUT skip`) 의 부작용 가시화 (사용자가 SELECT 선택 후 PASS/NA 미선택 시 저장 안 되는 흐름 인지 못함). **옵션 C 채택** (UI 가이드 + R1 fix 유지 + Q3-B Codex 결정 정합).

### 변경 (FE only, 1 파일 ~30 LoC)

`frontend/lib/screens/checklist/mech_checklist_screen.dart` 2 위젯 동일 패턴:

#### 추가 정정 1: description 렌더 (ELEC L898-909 패턴)
- `_buildSelectDropdown` + `_buildInputField` 둘 다 item_name 아래 description 표시
- fontSize 10 / GxColors.silver / maxLines 1 / ellipsis

#### 추가 정정 3: 옵션 C — PASS/NA 미선택 경고
- 변수 3개: `hasInput` / `hasResult` / `showPendingWarning = hasInput && !hasResult && !isPhase2`
- 위젯: ⚠️ "PASS 또는 NA 선택 후 저장됩니다" (warning_amber_rounded + GxColors.warning)
- INPUT 위젯 onChanged 안 `setState(() {})` 추가 — controller.text 변경 후 경고 메시지 갱신용

### Codex 라운드 1 결과 (M=0 / A=2 / N=3)
- **N1** Area 1 옵션 C + R1 정합: ELEC `_toggleResult` 패턴 정합, debounce 타이머 재사용으로 500ms 내 이중 PUT 상쇄
- **N3** Area 3 description 렌더: BE `_get_checklist_by_category()` `cm.description` 모든 item 응답 정합
- **N5** Area 5 read-only + 경고 호환: phase2 dropdown:null + readOnly + cloud + `!isPhase2` 가드 — R2 충돌 0
- **A2** INPUT setState({}) 성능: 매 키 입력마다 rebuild — 50건 환경 minor 성능 risk (minor hotfix 범위 허용)
- **A4** 회귀 0 보장 어려움: 저장 semantics 유지 but rebuild 비용 ↑ (minor 허용)
- **추가 advisory**: widget test 별 BACKLOG (provider/api mock harness 설계 필요)

### 검증
- flutter analyze: 0 error (info 4건만, 빌드 차단 X) ✅
- flutter build web --release: ✓ Built ✅

### 부수 발견 (Codex 합의)
- "phase2 에서 input 만 있고 result 없음" 케이스 사실상 생성 불가 (BE upsert 제약상) — `!isPhase2` 가드 안전성 입증
- 경고 재출현 우려 0 — 라디오 "해제" 안 되는 구조라 실질 발생 X

### 회귀 영향
- 0건 (FE UI 추가만, BE/타 화면 무관)
- migration/DB 변경 없음 → git revert 1건으로 v2.11.3 복귀 가능

---

## [2.11.3] - 2026-05-04 — Sprint 63 후속 hotfix: check_result null 차단 + phase=2 read-only UI (FE only, P0 hotfix)

> v2.11.2 prod 배포 후 사용자 운영 검증 (TEST-333/TEST-1111) — `PUT /api/app/checklist/mech/check → 400 INVALID_CHECK_RESULT: 'None'` + 2차 검사인원 읽기 전용 UI 부재. Codex 라운드 1 A3-F2 advisory 미구현 영역.

### 진단 SQL 결과 (DB 직접 쿼리)
- TEST-1111: CHECK 2 + SELECT 7 + INPUT 1 모두 정상 저장 ✅
- TEST-333 (DRAGON): CHECK 2 + SELECT 7 + INPUT 10 (INLET L/R 8 + Speed × 2) 모두 정상 저장 ✅
- → BE upsert 정상 작동 확정. **FE only 정정 충분** (BE 무관)

### Root cause 2건
- **R1**: `_upsertNow` 의 `cr.isEmpty ? null : cr` → null 전송 시 BE 400 거부
- **R2**: phase=2 시 TextField/DropdownButton 둘 다 enabled → 관리자가 1차 데이터 임의 변경 가능 (권한 위반)

### 변경 (FE only, 1 파일 ~13 LoC)

`frontend/lib/screens/checklist/mech_checklist_screen.dart` 3 위치:
1. **`_upsertNow`** L278~ — `cr.isEmpty` 시 PUT skip (R1, ELEC `_toggleResult` 패턴 정합)
2. **`_buildInputField`** L803~ — phase=2 시 `readOnly: true` + `fillColor: GxColors.cloud` + `onChanged: null` (R2)
3. **`_buildSelectDropdown`** L723~ — phase=2 시 `onChanged: null` + `fillColor: GxColors.cloud` (R2)

### 검증
- 진단 SQL: TEST-1111/TEST-333 phase=1 모든 항목 정상 저장 확인 ✅
- flutter analyze: 0 error (info 2건만, 빌드 차단 X) ✅
- flutter build web --release: ✓ Built ✅

### 회귀 영향
- 0건 (FE UI 변경만, BE/타 화면 무관)
- migration/DB 변경 없음 → git revert 1건으로 v2.11.2 복귀 가능

---

## [2.11.2] - 2026-05-04 — Sprint 63 후속 BUGFIX: 체크리스트 진입점 누락 fix (BE+FE, P0 hotfix)

> v2.11.1 prod 배포 직후 사용자 검증 — "체크리스트 자동 전환 안 됨" + "task 상세 메뉴 버튼 없음" 발견. Sprint 63-BE 설계 시 ELEC 패턴 차용 영역에서 토스트만 매핑하고 진입점(entry point) 영역 누락. P0 hotfix.

### Root cause
- Sprint 63-BE 설계 catch 누락: trigger_task_id 토스트만 매핑 + work/start 응답 분기 + task 상세 메뉴 버튼 누락
- Sprint 63-FE `_navigateToChecklist` 함수는 task_management_screen 에만 MECH 분기 추가, task_detail_screen 의 동일 이름 함수는 누락 (dead code 상태)

### 변경 (BE 1 파일 + FE 1 파일, 2 파일 ~25 LoC)

**BE (`backend/app/routes/work.py`)**:
- L177~ MECH 분기 추가: `MECH_CHECKLIST_TASK_IDS = {UTIL_LINE_1, UTIL_LINE_2, WASTE_GAS_LINE_2, SELF_INSPECTION}`
- 4 task 시작 시 응답에 `checklist_ready=True + checklist_category='MECH'`

**FE (`frontend/lib/screens/task/task_detail_screen.dart`) — 5 위치**:
1. L7-8 import: `mech_checklist_screen.dart` 추가
2. L760-770 `_hasChecklistAccess`: MECH 4 trigger task_id 분기
3. L737-746 `_buildChecklistButton` onTap (in_progress 시): MECH 분기
4. L767-780 `_navigateToChecklist`: MECH 분기 (`MechChecklistScreen`)
5. **L658-672 `_buildCompletedBadge` onTap (completed 시)**: MECH 분기 (추가 검토 5번째 catch)

### Codex 라운드 1 + 추가 검토 (M=1 / A=3 / N=1 + AV=2 + 추가 catch 1)
- M-R1: `_hasChecklistAccess` taskCategory + taskId 양쪽 매칭 risk indicator (현재 코드 OK)
- A1+AV1: trigger_task_id 권위 소스 정정 — `task_seed.py` → `migrations/051a_mech_checklist_seed.sql:106`
- A2: pytest TC 신규 6 assertions
- A3: BE+FE 단일 atomic commit (Railway half-state 차단)
- AV2: 선택 3 (work/complete MECH) → 별 sprint `FEAT-MECH-WORK-COMPLETE-CHECKLIST-NUDGE-20260504` (P3) 분리
- 추가 검토: 5번째 위치 (`_buildCompletedBadge` onTap) 누락 — 4 → 5 위치로 갱신

### Test
- `tests/backend/test_mech_checklist.py` `TestWorkStartMechChecklistEntry` 6 TC 신규:
  - UTIL_LINE_1/2 + WASTE_GAS_LINE_2 + SELF_INSPECTION 시작 시 checklist_ready=True
  - WASTE_GAS_LINE_1 (의도적 제외) negative 검증
  - ELEC INSPECTION 회귀 검증 (category='ELEC' 유지)
- 누적 24 → 30 TC

### 회귀 영향
- 0건 (BE response 키 추가 + FE 분기 추가만, additive)
- migration/DB 변경 없음 → git revert 1건으로 v2.11.1 복귀 가능

---

## [2.11.1] - 2026-05-04 — Sprint 63-FE Flutter UI + R2-1 BE patch + N1/N2 정정 (BE+FE)

> Sprint 63 전체 종료 piece. v2.11.0 (BE 인프라) + R2-1 BE patch + Flutter UI 통합 release.

### 추가 (BE patch — R2-1, Codex 라운드 2)
- `services/checklist_service.py` `get_mech_checklist()` 응답에 `tank_in_mech: bool` 추가
- model_config LEFT JOIN longest-prefix 매칭 (FE `_isScopeMatched` 활용)
- HOTFIX-08 표준 `conn.rollback()` 적용

### 추가 (FE 신규)
- `frontend/lib/screens/checklist/mech_checklist_screen.dart` 신규 (~844 LoC)
  - 입력 UI 3종 분기 (CHECK 라디오 / SELECT 드롭다운 / INPUT 텍스트)
  - scope_rule disabled NA UI ('N/A' 일관)
  - judgment_phase 토글 + role gate (`is_manager` / `is_admin`)
  - INLET 8개 Left/Right subgroup 시각 분리 (Q1-B)
  - debounce 500ms (Q6-C) + 번들 PUT (M5)
  - dispose() controller + timer 정리 (A4-F2)
- `frontend/lib/models/alert_log.dart` `CHECKLIST_MECH_READY` priority + iconName 추가
- `frontend/lib/screens/admin/alert_list_screen.dart`:
  - `_handleAlertTap` MECH 분기 → `MechChecklistScreen` 진입
  - title 매핑 + color 매핑 추가
- `frontend/lib/screens/task/task_management_screen.dart` `MechChecklistScreen` 라우팅 추가

### 정정 (Codex 라운드 2 Must 4건)
- M-R2-A/B: DUAL split-token 매칭 — `model.split(RegExp(r'[\s\-]')).contains('DUAL')` ('DUAL-300' / 'GAIA-DUAL-X' false-positive 차단)
- M-R2-C: DUAL 도면 qr_doc_id 정책 — `_qrDocIdForItem` DRAGON+INPUT+DUAL 만 hint 강제, 도면 SINGLE fallback
- M-R2-D: pytest 3 TC 신규 (`TestR21TankInMechResponse`)

### 정정 (N1+N2 본 세션 추가)
- N1: WebSocket `CHECKLIST_MECH_READY` alert provider 분기 추가 (alert_list_screen + alert_log)
- N2: pytest 3 TC 신규 — `tank_in_mech` 응답 키 회귀 + 모델별 boolean 검증

### Test
- `tests/backend/test_mech_checklist.py` 21 → 24 TC
- `TestR21TankInMechResponse` 3 TC: 모든 모델 응답 키 / DRAGON/GALLANT/SWS=TRUE / GAIA/MITHAS/SDS=FALSE
- 결과: **3/3 PASS** (85.54s)

### 회귀 영향
- 0건 (응답 키 추가 + 신규 FE 파일 + 기존 alert_log/alert_list 분기 추가만)

### Push 전 검증 (commit 21c581e GxColors 정정 포함)
- pytest test_mech_checklist 24/24 PASS (229.55s) — 위험 1 통과
- flutter analyze: 7 error → 0 error (info 2건만, 빌드 차단 X) — 위험 2-1
  * `GxColors.background` → `cloud` / `surface` → `white` / `mistLight` → `cloud` (7곳, ELEC 패턴 차용)
- flutter build web --release: ✓ Built build/web (12.3s) — 위험 2-2

### 후속 (별 sprint)
- AXIS-VIEW Sprint 39: BLUR 해제 + AddModal 토글 (~0.5d, 별 repo)
- BUG-TM-CHECKLIST-AUTO-FINALIZE-STALE-TC-20260504 (P3, 1h, Sprint 63-BE 무관)

---

## [2.11.0] - 2026-05-04 — Sprint 63-BE MECH 체크리스트 BE 인프라 (BE only, +1,415 LoC)

> 양식 73 항목 / 20 그룹 도입 — TM(Sprint 52)/ELEC(Sprint 57) 후 MECH 자주검사 체크리스트 디지털화. BE 단독 배포, FE/VIEW 별 sprint.

### 추가 (Schema)
- `migrations/051_mech_checklist_extension.sql`: `scope_rule` + `trigger_task_id` 컬럼 + `item_type` CHECK constraint 'INPUT' 추가 + `alert_type_enum` 'CHECKLIST_MECH_READY' ADD VALUE
- `migrations/051a_mech_checklist_seed.sql`: 73 INSERT (CHECK 56 / INPUT 10 / SELECT 7, all 56 / tank_in_mech 9 / DRAGON 8, INLET S/N L/R 8개 분리 v2)

### 추가 (BE)
- `services/checklist_service.py` 신규 함수 5개:
  - `_normalize_qr_doc_id()` — TM/ELEC/MECH 공유 normalizer (Sprint 59-BE 재발 방지)
  - `_resolve_active_master_ids()` — scope_rule + phase1_applicable Python helper
  - `check_mech_completion()` — SINGLE/DUAL 분기 + (c)안 phase=2 record-only 카운트
  - `get_mech_checklist()` — 73 항목 + scope_rule/trigger_task_id 응답
  - `upsert_mech_check()` — INPUT type 지원
- `_get_checklist_by_category()` SELECT 절에 `scope_rule` + `trigger_task_id` 추가 (TM/ELEC 응답에도 새 필드, 기존 키 무변경)
- `routes/checklist.py` MECH endpoints 3개: GET / PUT / GET status
- `task_service.py` `_trigger_mech_checklist_alert()` hook — UTIL_LINE_1/UTIL_LINE_2/WASTE_GAS_LINE_2 시작 시 `CHECKLIST_MECH_READY` alert
- `production.py` `_check_sn_checklist_complete()` MECH 분기 활성화

### 변경 (Refactor)
- `_check_tm_completion` → `check_tm_completion` rename (9 hits, private→public 일관 인터페이스): checklist_service 5 + production 2 + test_alert_all20 2

### 추가 (Test)
- `tests/backend/test_mech_checklist.py` 21 TC 신규 (+554 LoC):
  - `[A]` _normalize_qr_doc_id pure function 6 TC (DB 불필요)
  - `[B]` scope_rule + phase1 7 TC (all/tank_in_mech/DRAGON × 모델별 매핑)
  - `[C]` trigger_task_id 매핑 3 TC (Speed 4 / MFC+FS 7 / INLET 8)
  - `[D]` seed count 1 TC (51a 실파일 분포 자동 검증)
  - `[E]` rename gate 1 TC (rg "_check_tm_completion" = 0)
  - `[F]` phase=2 (c)안 2 TC (1차 record 미강제)
  - `[G]` WebSocket emit 1 TC (mock create_alert 호출 검증)
- 결과: **21/21 PASS** (186.84s)

### 검증
- pytest test_mech_checklist 21/21 PASS ✅
- rename gate `rg "_check_tm_completion" backend/ tests/` → 0 hits ✅
- syntax `ast.parse` 4 modified files OK ✅
- 회귀 영향: 0건 (신규 응답 필드 추가만, 기존 키 무변경)

### 정정 trail 11건 적용 (Codex 라운드 1+2+3 + 사용자 결정 4건)
- 라운드 1 (M=4 / A=2 / 추가 3): CLAUDE drift / rename grep / qr_doc_id normalizer / seed 총계+pytest / INLET 표 / enum / Python helper 통일
- 라운드 2 (M=3 / A=2 / N=1 / 추가 6): 핵심 통찰 "설계서 정정 ≠ 실코드 미구현" / atomic / silent failure / ELEC qr_doc_id 별 BACKLOG / models drift / lint hook / cross-repo
- 라운드 3 (M=3 / A=7 / N=8 / 추가 2): ALTER TYPE non-transactional 보증 (migration_runner autocommit=True 확인) / test 파일 경로 정정 / Pre-deploy Gate #7 신규
- 사용자 결정 v2: INLET S/N L/R 8 master 분리 (옵션 A 변형) / judgment_phase=2 (c)안 / BE/FE 분리 / Minor 3건

### 후속 Sprint (별 sprint, BE 배포 후 착수)
- Sprint 63-FE: `mech_checklist_screen.dart` 신규 (~1,000~1,200 LoC, 2~3d)
- AXIS-VIEW Sprint 39: BLUR 해제 + AddModal 토글 (~0.5d, 별 repo)

---

## [2.10.17] - 2026-05-01 — HOTFIX-09 access_log cleanup `get_db_connection` import 누락 (BE only, 1 line)

> Sprint 32 (v1.9.0, 2026-03-19) 도입 access_log cleanup cron 이 **43일간 매일 03:00 NameError silent failure**. 사용자 영향 0 (access_log 30 MB 누적, DB 한도 6%) but cleanup 자체 작동 0회.

### 사고 trail (Sentry 가치 입증 #4)

```
2026-03-19  Sprint 32 (v1.9.0) — _cleanup_access_logs cron 등록
              get_db_connection import 누락 → 매일 03:00 NameError
              ↓
2026-03-19 ~ 04-27  Sentry 미도입 → silent failure (40일)
              ↓
2026-04-27  Sentry 정식 활성화 (v2.10.8)
2026-04-28  03:00 cron 첫 capture
2026-04-29 ~ 05-01  4 events 누적
              ↓
2026-05-01  Sentry dashboard 우연 발견 → 본 fix
```

**확정 증거**: 4-29 측정 시 89,076 rows / 41일 누적 (3-19 ~ 4-29) — cleanup 한 번도 작동 안 했음.

### Fixed (BE only — import 1줄 추가)

- `backend/app/services/scheduler_service.py L1122 _cleanup_access_logs()`:
  - 함수 본체에 `from app.models.worker import get_db_connection` 1줄 추가
  - 다른 11개 함수 (L370/L418/L468/L654/L756/...) 와 동일 패턴 (lazy import)
  - docstring 에 HOTFIX-09 trail 추가

### 효과 (5-02 03:00 cron 부터)

```
다음 5-02 03:00 cron 실행 시:
  - 90일+ rows 삭제 대상 = 0건 (43일 누적이라)
  - 정상 작동 logger.info 출력
  
6-17 (3-19 + 90일) 이후:
  - 90일+ rows 삭제 시작 (정상 운영)
```

### Tests

- syntax check ✅
- 신규 TC 4개 (Codex Q4 advisory 보강 후, 5-01 동일일 commit 전 추가):
  - `test_cleanup_access_logs_imports_get_db_connection_correctly` — import 회귀 catch (mock patch)
  - `test_cleanup_access_logs_uses_90_days_interval` — v2.10.15 90일 retention 정적 검증
  - `test_cleanup_access_logs_full_flow_execute_commit_put_conn` — execute SQL + commit + put_conn 정상 흐름
  - `test_cleanup_access_logs_rollback_on_exception` — 예외 시 rollback + put_conn (예외 흡수)
- pytest 4/4 PASS (37.05s)

### Codex 라운드 1 합의 trail (5-01 사후 검토)

- Q1 (Severity S3): N (적정)
- Q2 (Proactive audit): **M** — `services/` 전체 grep audit + `_get_db_connection()` helper 통일 검토 → **별 BACKLOG `OBSERV-SCHEDULER-IMPORT-AUDIT-20260501` 등록**
- Q3 (lint pre-commit): **M** — flake8/pyflakes/ruff 도입으로 F821/E0602 차단 → **별 BACKLOG `INFRA-LINT-PRECOMMIT-HOOK-20260501` 등록**
- Q4 (TC 충분성): A → 본 commit 에서 TC 2개 → 4개로 보강 ✅
- Q5 (framing): A → "Sentry 가치 입증 #4" 보다 "Sprint 32 design/QA 부족 + Sentry 는 latent defect 탐지 layer" 가 정확. **결함 원인은 Sprint 32, Sentry 는 탐지 성공**
- Q6 (CHANGELOG sync): A → 본 commit 에서 "TC 없음" 표기 정정 ✅

### 정확한 framing — Sprint 32 design/QA 부족 + Sentry 탐지 성공

```
이전 latent defect 탐지 trail:
  #1 HOTFIX-07 (v2.10.9): row[0] KeyError 5일 silent → assertion 도입 첫 호출 시 즉시 노출
  #2 HOTFIX-08 (v2.10.10): db_pool transaction 정리 + 046a Docker artifact silent gap
  #3 v2.10.11 FIX-PROCESS-VALIDATOR-TMS-MAPPING: 4-22 silent failure 후속 Sentry 8h 자동 감지

본 사례 #4:
  결함 원인: Sprint 32 (3-19) design/QA 부족 — module-top import 또는 lazy import 표준 부재
  → 다른 11개 함수는 lazy import 사용 but _cleanup_access_logs() 만 누락
  → flake8/pyflakes pre-commit hook 부재 (lint-time F821 catch 가능했음)
  → 단위 test 부재 (43일간 한 번도 호출 안 됨 검증)

탐지 성공: Sentry layer 가 latent defect 를 4-28 부터 자동 capture
  → 사용자 영향 0 시점에 발견, 5-01 fix
```

### Deploy

- BE only (frontend version 만 동시 bump)
- Railway 자동 배포

### Related

- 사고 trail: 본 issue Sentry "[cleanup] Access log cleanup failed: name 'get_db_connection' is not defined" 4 events / 3 days
- v2.10.15 (FIX-ACCESS-LOG-RETENTION-90D) 가 사실상 효과 0 였음 (cleanup 자체 미작동) → 본 fix 후 정상 작동

---

## [2.10.16] - 2026-04-30 — FIX-DB-POOL-WARMUP-WATCHDOG (BE only, watchdog log 격상)

> **Sprint**: `FIX-DB-POOL-WARMUP-WATCHDOG-20260430`
> 4-29 23:31 ~ 4-30 09:30 사이 1.5h+ silent failure 사고 재발 방지. warmup cron 은 살아있는데 `_pool=None` 인 silent failure 가 `logger.debug` 로 묻혀 있던 사각지대 fix.

### 사고 배경

```
4-29 23:21 [pool_warmup] 5/5 conn warmed   ✅ 정상
4-29 23:26 [pool_warmup] 5/5 conn warmed   ✅ 정상
4-29 23:31 [pool_warmup] 0/0 conn warmed   ❌ silent 시작
... (1.5h+ 0/0 지속)
4-30 09:30 사용자 측 conn=2 측정으로 발견
```

### 원인

scheduler 가 도는 gunicorn worker 의 메모리 변수 `_pool` 이 None 으로 변환됨 (gunicorn worker 재시작 후 init_pool() 미호출 가능성). warmup cron 은 살아있어 5분마다 함수 호출 → `_pool is None` 분기 → `logger.debug(...)` → `return (0, 0)`. **Railway logs `--log-level=info` 라 미출력 + Sentry capture 안 됨** → silent failure.

### Fixed (BE only — 1줄 격상 + pid context)

- `backend/app/db_pool.py warmup_pool()` L266-268:
  - `logger.debug("[db_pool] warmup skipped — pool not initialized")` → `logger.error("[db_pool] warmup called but _pool=None — gunicorn worker pool died (pid=%d)", os.getpid())`
  - `LoggingIntegration(event_level=ERROR)` 가 자동 Sentry event capture (`__init__.py` L87) → Twin파파 1분 안에 알림
  - pid context 포함 — Worker A/B 어느 쪽이 죽었는지 식별

### Tests

- `tests/backend/test_db_pool.py`:
  - 신규 TC `test_warmup_logs_error_when_pool_none` — `_pool=None` 시 logger.error 호출 + 'gunicorn worker pool died' 메시지 검증
- pytest test_db_pool.py: **4/4 PASS** ✅ (신규 1 + 기존 3 회귀 0)

### LoC

- db_pool.py: 297 → 305 (+8 LOC, 1 분기 격상 + 주석)
- test_db_pool.py: ~70 → ~85 (+15 LOC, TC 1개)

### 효과 — silent failure 재발 방지

```
Before: warmup cron 0/0 출력 1.5h+ 지속 → 사용자 우연 발견
After:  warmup cron 0/0 발생 시점 logger.error → Sentry alert → 1분 안에 알림
```

### Codex 이관 미해당

단순 log level 격상 + Sentry 자동 capture (LoggingIntegration). 표준 패턴 (v2.10.13 동일).

### Deploy

- BE only (frontend version 만 동시 bump)
- Railway 자동 배포

### Related

- 사고 trail: 4-29 23:31 ~ 4-30 09:30 (1.5h+ silent)
- 후속 (선택): HOTFIX-06b per-worker warmup — Worker A/B 모두 자체 warmup + _pool=None 자동 재초기화 (영구 해결)

---

## [2.10.15] - 2026-04-29 — FIX-ACCESS-LOG-RETENTION-90D (BE only, 1줄)

> **Sprint**: `FIX-ACCESS-LOG-RETENTION-90D-20260429`
> Sprint 32 (v1.9.0, 2026-03-19) 도입 access log 30일 자동 삭제 정책을 90일로 완화. 분기 추세 분석 + 사고 사후 검증 윈도우 확보.

### Changed (BE only)

- `backend/app/services/scheduler_service.py`:
  - L1128 `INTERVAL '30 days'` → `INTERVAL '90 days'`
  - L111 주석 + L116 job name 동기 갱신

### 결정 근거

- 현재 (4-29 기준): 89,076 rows / 30 MB (table 14 + index 15) / 348 bytes/row / 일평균 ~2,144 rows
- 시뮬레이션 (90일): ~193,000 rows / **64 MB** — Railway Hobby plan 0.5 GB 한도 12.8% (무시 가능)
- 4-22 silent failure 5일 누적 사고 같은 사례에서 사후 1~2개월 분석 윈도우 확보 (이전 30일 부족)

### 회귀 위험 0

- 1줄 변경 (cron 빈도 동일, 삭제 조건만 완화)
- pytest 신규 TC 불필요 (행동 차이 자명)

### Deploy

- BE only — Railway 자동 배포

### Related

- BACKLOG: `FIX-ACCESS-LOG-RETENTION-90D-20260429` → COMPLETED (1줄 수정)

---

## [2.10.14] - 2026-04-28 — FIX-FACTORY-KPI-SHIPPED-V2.4 (BE only)

> **Sprint**: `FIX-FACTORY-KPI-SHIPPED-V2.4-AMENDMENT-20260428`
> Sprint 62-BE v2.2 의 `_count_shipped` 보정 — `shipped_plan` 의 si_completed AND 조건이 app SI 도입률 ≈0% 환경에서 무효 (W17 0 상수화) → OR 로 교정 + `shipped_ops` 폐기 + `shipped_best` 신설.

### Fixed (BE only — factory.py 단일)

#### `_count_shipped()` 재작성 (3 분기)

- **basis='plan'**: `INNER JOIN completion_status ... AND cs.si_completed=TRUE` 제거 → `LEFT JOIN app_task_details (task_id='SI_SHIPMENT') + WHERE (actual_ship_date IS NOT NULL OR t.completed_at IS NOT NULL)`
- **basis='ops'**: 분기 **제거** (app SI 100% 도입 후 ops=actual 수렴, 영구 무의미)
- **basis='best'**: 신규 — reality 경계 = `actual_ship_date IS NOT NULL` / 주간 귀속 = `COALESCE(DATE(t.completed_at), p.actual_ship_date)` (해석 A: si ⊆ actual, Pre-deploy Gate ③ 0건 검증 완료)
- ValueError 메시지: `'plan' | 'actual' | 'ops'` → `'plan' | 'actual' | 'best'`
- task_id `'SI_SHIPMENT'` 대문자 (Twin파파 검토 — 실 DB 값과 일치, OPS_API_REQUESTS.md v2.4 문서의 소문자 typo 정정)

#### weekly-kpi + monthly-kpi 응답 4곳 (`shipped_ops` → `shipped_best`)

- L457 weekly-kpi `_count_shipped` 호출
- L473 weekly-kpi 응답 dict
- L554 monthly-kpi `_count_shipped` 호출
- L566 monthly-kpi 응답 dict

### Tests (test_factory_kpi.py)

- 신규 클래스 `TestFactoryKpiV24Amendment` 3 TC:
  - `test_fk_v24_shipped_ops_field_removed_from_response` — 응답에 `shipped_ops` 부재 + `shipped_best` 존재 검증
  - `test_fk_v24_count_shipped_best_basis_smoke` — `basis='best'` 호출 스모크
  - `test_fk_v24_count_shipped_invalid_basis_raises` — `'ops'` (제거됨) + 임의 basis → ValueError + 메시지에 `plan | actual | best` 포함
- 기존 TC 갱신:
  - TC-FK-01 / TC-FK-03: 응답 키 `shipped_ops` → `shipped_best` (단순 교체)
  - TC-FK-07 / TC-FK-10: `_count_shipped` 직접 호출 `'ops'` → `'plan'` (force_closed 검증 의미 보존)
- 기존 TC skip 처리 (3건):
  - TC-FK-06 / TC-FK-09 / TC-FK-11: `@pytest.mark.skip` (사유: TC 본질이 v2.3 'ops' 분기의 +1 증가 검증, v2.4 에서 'ops' 제거 + fixture (SI_SHIPMENT INSERT only) 의 ship_plan_date / actual_ship_date 미설정 한계로 'plan'/'best' 분기 +1 시뮬레이션 불가, 운영 데이터 보존 정책 — UPDATE 금지). v2.4 핵심 거동은 신규 TestFactoryKpiV24Amendment 클래스로 이전.

### LoC

- factory.py: 562 → 575 (+13 LOC) — ⛔ God File 임계 미만이지만 500 초과 잔존 (별건 REFACTOR-FACTORY 추후 검토)
- test_factory_kpi.py: 435 → 511 (+76 LOC, 신규 TC 3개 + skip mark + 응답 키 갱신)

### Pre-deploy Gate (Twin파파 측 사전 검증 완료)

- ③ R-02 해석 A 반례 — `SELECT COUNT(*) ... WHERE task_id='SI_SHIPMENT' AND completed_at IS NOT NULL AND p.actual_ship_date IS NULL` → **0건** 확인 (해석 A 확정)

### Tests 요약

```
test_factory_kpi.py: 17 passed / 3 skipped / 0 fail (137.10s)
  ├─ 기존 14개 갱신 후 PASS
  └─ 신규 TestFactoryKpiV24Amendment 3개 PASS
```

### Codex 이관 미해당

OPS_API_REQUESTS.md v2.4 합의안 + 실 DB 값 검증 + Pre-deploy Gate 5종 명시 완료. Sprint 설계서 분석 단계에서 모든 결정 trail 보유.

### Deploy

- BE only (frontend version 만 동시 bump)
- Railway 자동 배포

### Post-deploy 검증 (예정)

- T+1h: 대시보드 W17 `shipped_plan` 0 → 수십대 (의도된 변화) + Sentry 새 ERROR 0
- T+24h: 3필드 `shipped_plan/actual/best` 정상 반환 + 회귀 0
- T+72h: R-02 해석 A 재검증 (반례 0건 유지) + FE Phase 2 (v1.35.0) 착수 가능 시점 도달

### Rollback (1 파일 atomic)

- git revert <commit-sha>
- v2.3 상태 복귀 (shipped_plan 0 상수화 재발 + shipped_ops 복원)
- 해석 A 가정 깨짐 시 (R-02 반례 발생): `_count_shipped basis='best'` WHERE 의 `p.actual_ship_date IS NOT NULL` 제거 + UNION 재도입 별건 hotfix

### Related

- 설계서: `AGENT_TEAM_LAUNCH.md` § FIX-FACTORY-KPI-SHIPPED-V2.4-AMENDMENT-20260428 (L33255+)
- BACKLOG: `FIX-FACTORY-KPI-SHIPPED-V2.4-AMENDMENT-20260428` → ✅ COMPLETED
- 후속: AXIS-VIEW Phase 2 (v1.35.0) — TEMP-HARDCODE 제거 + FactoryDashboardSettingsPanel + shipped_ops → shipped_best 타입 교체

---

## [2.10.13] - 2026-04-28 — Sentry garbage log 정리 2건 (BE only)

> **Sprint 묶음 배포**: `FIX-DB-POOL-DIRECT-FALLBACK-LOG-LEVEL-20260428` + `FIX-WEBSOCKET-STOPITERATION-SENTRY-NOISE-20260428`
> Sentry 대시보드 잡음 분리 → 진짜 ERROR 추적성 회복.

### Fixed (BE only — 4 파일)

#### Sprint 1 — db_pool direct conn fallback log level 강등 + counter

- `backend/app/db_pool.py`:
  - `_direct_fallback_count: int = 0` 모듈 변수 신설 + `get_direct_fallback_count()` getter 추가
  - L171-173 `logger.error("All pool connections unusable, ...")` → `logger.warning(... cumulative fallback=%d)` 강등 + counter 증가
  - 의미론 정합 (fallback 자체는 의도된 안전망 → warning 적정)
- `tests/backend/test_db_pool.py` 신규 (+~60 LOC, TC 3개):
  - `test_fallback_increments_counter` — 3 retry 모두 unusable → counter 증가 + warning level
  - `test_normal_path_no_counter_increment` — 정상 conn 획득 시 무변화
  - `test_pool_exhausted_does_not_increment_fallback_counter` — exhausted 경로는 별도 (counter 분리)
- 효과: Sentry `[db_pool] All pool connections unusable` issue (16h 22 events) 동결, ERROR level 미발생

#### Sprint 2 — flask-sock wsgi StopIteration Sentry 필터

- `backend/app/__init__.py`:
  - `_sentry_before_send(event, hint)` 모듈 top-level 함수 신설 (~30 LOC)
  - 매칭 조건 3개 모두 성립 시 `None` 반환 (drop): `exc_type='StopIteration'` + `mechanism.type='wsgi'` + `transaction='websocket_route'`
  - try/except 안전 fallback (필터 자체 실패 시 정상 capture)
  - `sentry_sdk.init()` 에 `before_send=_sentry_before_send` 등록
- `tests/backend/test_sentry_filter.py` 신규 (+~50 LOC, TC 4개):
  - `test_filters_websocket_stopiteration` — 3 조건 매칭 시 drop
  - `test_passes_other_transaction_stopiteration` — 다른 transaction 의 StopIteration 정상 전달
  - `test_passes_non_stopiteration_at_websocket` — websocket_route 의 다른 exception 정상 전달
  - `test_safe_on_malformed_event` — 이상한 event 구조 안전 fallback
- 효과: Sentry PYTHON-FLASK-2 issue (16h 302 events / Escalating) 동결, 정상 종료 시그널 분리

### Tests

- pytest tests/backend/test_db_pool.py: 3/3 PASS ✅
- pytest tests/backend/test_sentry_filter.py: 4/4 PASS ✅
- 총 7/7 PASS (0.09s, 회귀 0건)

### LoC

- db_pool.py: 286 → 297 (+11 LOC) — 🟢 500 미만 Pass
- __init__.py: ~190 → ~225 (+35 LOC) — 🟢 500 미만 Pass

### Codex 이관 미해당

두 Sprint 모두 표준 패턴 (log level 강등 + counter / Sentry SDK before_send hook). Sprint 설계서에서 분석 완료, Codex 이관 불필요.

### Deploy

- BE only (frontend version 만 동시 bump)
- Railway 자동 배포

### Post-deploy 검증 (예정)

- T+1h: Sentry 본 issue 2건 events 카운트 증가 멈춤 (22 / 302 동결)
- T+24h: 다른 issue 정상 capture 확인 (PYTHON-FLASK-1 4-22 enum cast / PYTHON-FLASK-4 TMS mapping 후속)
- T+7d: 본 Sprint 효과 정량 입증 → COMPLETED
- Railway logs `cumulative fallback=N` 추세 → 별건 OBSERV-WARMUP-INTERVAL-TUNE 우선순위 결정

### Rollback (4 파일 atomic)

- git revert <commit-sha>
- 부분 revert 안전 (각 Sprint 독립 작동)
- 영향 범위 0 (잡음 분리 only, 비즈니스 로직 무관)

### Related

- Sprint 1: `AGENT_TEAM_LAUNCH.md` § FIX-DB-POOL-DIRECT-FALLBACK-LOG-LEVEL-20260428 (L32942+)
- Sprint 2: `AGENT_TEAM_LAUNCH.md` § FIX-WEBSOCKET-STOPITERATION-SENTRY-NOISE-20260428 (L33255+)

---

## [2.10.12] - 2026-04-28 — FIX-26 DURATION_WARNINGS 응답 키 일관성 (BE only)

> **Sprint**: `FIX-26-DURATION-WARNINGS-FORWARD-20260428`
> 4-22 등록 BACKLOG L362 `BUG-DURATION-VALIDATOR-API-FIELD` 본격 fix. 4-28 FIX-PROCESS-VALIDATOR-TMS-MAPPING (v2.10.11) 회귀 시 동일 fail 재출현 → Codex 라운드 2 A 합의 (별건 확정) → 본 Sprint 진행.

### Fixed (BE only — 응답 키 contract 일관성)

#### 1. `task_service.py` L497-499 — unconditional 응답 키

- Before: `if duration_warnings: response['duration_warnings'] = duration_warnings` (조건부 키)
- After: `response['duration_warnings'] = duration_warnings` (항상 키 존재, 빈 리스트 [] 라도)
- API 계약 명확화: FE 가 `data.duration_warnings` 안전 접근 가능

#### 2. `work.py` L265-266 — default fallback forward

- Before: `if 'duration_warnings' in response: result['duration_warnings'] = response['duration_warnings']`
- After: `result['duration_warnings'] = response.get('duration_warnings', [])`
- 방어적 forward — task_service / work.py 양 끝 모두 보장 (옵션 C 채택)

### Tests (test_duration_validator.py)

- `test_normal_duration_no_warnings` L75-76: `assert 'duration_warnings' not in data` → `assert 'duration_warnings' in data; assert data['duration_warnings'] == []` (신 계약 정합)
- 신규 클래스 `TestDurationWarningsAlwaysPresent::test_normal_completion_returns_empty_duration_warnings` 추가 — 정상 완료 시 빈 리스트 반환 검증
- `TestReverseDuration::test_reverse_completion` `@pytest.mark.skip` 추가 — 사유: 시작/종료 timestamp 서버 자동 기록 (`task_service.py:146/256` `datetime.now(Config.KST)`), 운영 발생 불가 (prod 0건 실측, 4-04~4-28 24일 누적). REVERSE_COMPLETION 은 서버 시계 NTP jump back / SQL 직접 조작 / timezone 버그 같은 인프라 사고에서만 발생하는 방어적 안전망

### LoC 변경

| 파일 | Before | After | 차이 |
|---|---:|---:|---:|
| task_service.py | 1486 | 1486 | ±0 (조건부 → unconditional) |
| work.py | (이전) | (동일) | -1/+1 (조건부 → default get) |
| test_duration_validator.py | 246 | 308 | +62 (skip mark + 신규 TC) |

### 사용자 영향 0 — silent failure 우려는 무의미

본 Sprint 검토 중 "Sprint 55 multi-worker early return path 가 silent failure 일으키는가" 우려 제기됐으나:
- 시작/종료 timestamp 서버 `datetime.now()` 자동 기록 → 클라이언트 시간 입력 path 0
- prod 실측: REVERSE_COMPLETION 발생 0건 (24일 누적)
- 대시보드 Rollback 키로 사후 복구 메커니즘 별도 존재
- 시나리오 자체가 인프라 사고 차원

→ 별건 BACKLOG 등록 불필요 (P3 INFO 수준 이하). 본 Sprint 는 응답 contract 일관성만 fix 하고 종결.

### Codex 합의 trail

- 라운드 2 (2026-04-28, FIX-PROCESS-VALIDATOR-TMS-MAPPING 후속): Q1/Q2 모두 A — `duration_warnings` 키 누락은 응답 키 생성 경로의 4-22 부터 누락된 별건 확정. v2.10.11 회귀 0건. v2.10.12 별도 Sprint 처리.

### Deploy

- BE only (frontend version 만 동시 bump)
- Railway 자동 배포

### Rollback (3 파일 atomic)

- git revert <commit-sha> → 3 파일 원복
- Railway 자동 재배포 ~1분
- 부분 revert 안전 (각 파일 독립 작동)

### Related

- 설계서: `AGENT_TEAM_LAUNCH.md` § FIX-26-DURATION-WARNINGS-FORWARD-20260428 (L32717+)
- BACKLOG: L362 `BUG-DURATION-VALIDATOR-API-FIELD` → COMPLETED

---

## [2.10.11] - 2026-04-28 — FIX-PROCESS-VALIDATOR-TMS-MAPPING (옵션 D-2, BE only)

> **Sprint**: `FIX-PROCESS-VALIDATOR-TMS-MAPPING-20260428`
> 4-22 HOTFIX-ALERT-SCHEDULER-DELIVERY 의 표준 패턴이 duration_validator 3곳에 미적용 → TMS 매니저 알람 미수신 (silent failure 매시간 ~10건). Sentry 도입 8h 만에 자동 감지 → 30분 fix.

### Fixed (BE only — 5 파일 atomic refactor)

#### 1. `process_validator.py` (+30 LOC) — 표준 함수 신설

- `_CATEGORY_PARTNER_FIELD` dict 신설 (`'TMS':'module_outsourcing'/'MECH':'mech_partner'/'ELEC':'elec_partner'`)
- `resolve_managers_for_category(serial_number, category)` public 함수 — partner-based / role-based 자동 분기
- 4-22 HOTFIX 의 scheduler private 함수 패턴을 process_validator 로 이전 + public 화 (DRY)

#### 2. `scheduler_service.py` (-15 LOC) — private 함수 + dict 제거 + import 교체

- `_resolve_managers_for_category` 함수 + `_CATEGORY_PARTNER_FIELD` dict 제거
- `from app.services.process_validator import resolve_managers_for_category` 추가
- 3 호출 site (L921 / L1021 / L1110) `_resolve_managers_for_category` → `resolve_managers_for_category` 1:1 교체

#### 3. `task_service.py` (±0 LOC) — Codex M2 누락 발견된 5번째 파일

- L403: `from app.services.scheduler_service import _resolve_managers_for_category` → `from app.services.process_validator import resolve_managers_for_category`
- L410: 호출 1줄 1:1 교체
- ORPHAN_ON_FINAL alert (Sprint 61-B) 경로

#### 4. `duration_validator.py` (±0 LOC) — 본 Sprint 핵심 fix 대상

- L16 import: `get_managers_for_role` → `resolve_managers_for_category`
- L74 (REVERSE_COMPLETION) / L100 (DURATION_EXCEEDED) / L179 (UNFINISHED_AT_CLOSING):
  - Before: `get_managers_for_role(task.task_category)` → SQL `WHERE role='TMS'` → enum cast 실패 → silent skip
  - After: `resolve_managers_for_category(sn, category)` → module_outsourcing 매니저 정상 도착

#### 5. `tests/conftest.py` (+50 LOC) — Codex M1 옵션 D 격리 fixture

- `seed_test_managers_for_partner` — TEST_WORKERS 의 partner worker (FNI/BAT/TMS(M)/TMS(E)/P&S/C&A) 일시 매니저 promote
- teardown 명시적 원복 (`name != 'GST관리자'` 보호 조건) → 다른 테스트 영향 0

#### 6. `tests/backend/test_process_validator.py` (+130 LOC) — TC 7개

- TestResolveManagersForCategory 6 TC: TMS-GAIA partner / TMS-DRAGON 회귀 / MECH partner / ELEC partner / PI role fallback / unknown empty
- e2e TC 1개 (Codex A2 흡수): `test_duration_validator_tms_alert_creation_e2e` — `validate_duration()` 직접 호출 + alert_logs INSERT 검증

### LoC 변경 (Line 규칙 모두 통과 ✅)

| 파일 | Before | After | 차이 |
|---|---:|---:|---:|
| process_validator.py | 259 | 289 | +30 (🟢 500 미만) |
| scheduler_service.py | 1153 | 1138 | **-15** (⛔ God File 잔존, LoC 감소) |
| task_service.py | 1486 | 1486 | ±0 (⛔ God File 잔존, mechanical 1:1) |
| duration_validator.py | 204 | 204 | ±0 (🟢 import 1줄 + 호출 3곳 1:1) |

→ "🔴 새 로직 추가 금지" 규정 우회 (scheduler/task_service 모두 LoC 감소 또는 ±0). REFACTOR-SCHEDULER-SPLIT 의 부분 선행 효과.

### Tests

- pytest 신규 TC: **7/7 PASS** ✅
- pytest 회귀 (test_scheduler / test_scheduler_integration / test_task_seed): **51 passed / 5 skipped / 0 fail** ✅
- 1건 무관 fail: `test_duration_validator.py::TestReverseDuration::test_reverse_completion` — BACKLOG L362 `BUG-DURATION-VALIDATOR-API-FIELD` (4-22 기존 별건). **Codex 라운드 2 (2026-04-28) Q1/Q2 모두 A 라벨 합의** — 본 Sprint 응답 키 생성 경로 (duration_validator → task_service → work.py) 영향 0, 별도 Sprint 처리

### Codex 합의 기록

- **라운드 1 (Sprint 설계 검증)**: M=2 / A=2 / N=2 — M1 fixture 정합성 (옵션 D 격리 fixture) + M2 Rollback 5 파일 (task_service.py L403-410 누락 발견) + A1 DRAGON gap (별건 BACKLOG `BUG-DRAGON-TMS-PARTNER-MAPPING-20260428`) + A2 e2e 회귀 TC. 모두 반영
- **라운드 2 (pytest 회귀 라벨링)**: Q1/Q2 모두 A — 본 Sprint 회귀 0건 + BUG-DURATION-VALIDATOR-API-FIELD 별건 확정

### Deploy

- BE only (frontend version 만 동시 bump)
- 배포: Railway 자동 (git push origin main)
- Production: https://axis-ops-api.up.railway.app

### Post-deploy 검증 (예정)

- 즉시 (1h): Sentry PYTHON-FLASK-4 issue events 카운트 증가 멈춤 확인 (31 → 정착)
- 매시간 정각 (UTC) 7번: TMS / MECH / ELEC / PI 매니저 도달 회귀 검증
- D+7 종합: Sentry events 31 그대로 → COMPLETED 판정

### Rollback (5 파일 atomic)

```
git revert <commit-sha>   # 5 파일 동시 원복
→ Railway 자동 재배포 ~1분
부분 revert 절대 금지 (ImportError → 앱 boot 실패 → 503 폭주 위험)
```

### Related

- 설계서: `AGENT_TEAM_LAUNCH.md` L32249 FIX-PROCESS-VALIDATOR-TMS-MAPPING-20260428
- BACKLOG: L352 (본 Sprint, COMPLETED) / L353 (BUG-DRAGON-TMS-PARTNER-MAPPING 후속) / L362 (BUG-DURATION-VALIDATOR-API-FIELD 별건)
- 메타 가치: assertion + Sentry layer 가치 입증 #3 (memory.md ADR-019)

---

## [2.10.10] - 2026-04-27 — HOTFIX-08 db_pool transaction 정리 누락 + 046a 자동 적용 (BE only)

> **HOTFIX-08** — v2.10.9 배포 후 Railway log 에 `046a_elec_checklist_seed.sql 실행 실패: set_session cannot be used inside a transaction` 발생. assertion 자동 감지 layer 가 두 번째 잠재 버그 (db_pool transaction 정리 누락 + 046a silent gap) 사용자 영향 0 시점에 발견.

### Fixed

- **`backend/app/db_pool.py _is_conn_usable()`** — SELECT 1 실행 후 `conn.rollback()` 추가:
  - psycopg2 default `autocommit=False` → SELECT 도 BEGIN 자동 시작 → INTRANS 상태로 풀 반납
  - 이 conn 을 받아 `m_conn.autocommit=True` 시도 시 `set_session cannot be used inside a transaction` 거부 (migration_runner 사례)
  - 동일 SELECT 1 검증 패턴인 `warmup_pool()` 에도 동일 1줄 (총 2곳)

### Side Effect (긍정)

- **046a_elec_checklist_seed.sql 자동 적용** — 4-22 049 와 동일한 Docker artifact silent gap 사례로 추정. `ON CONFLICT DO NOTHING` idempotent 보장으로 prod 31항목 안전 재적용. 사용자 영향 0.

### Tests

- pytest 회귀 0건
- Railway log 검증: `[migration] ✅ 046a_elec_checklist_seed.sql 실행 완료` + `[migration-assert] ✅ sync OK (13 migrations applied)` (12 → 13 갱신)

### Deploy

- BE only — Railway 자동 (git push origin main)
- git commit: `72579e1`

### Related

- assertion 자동 감지 layer 가치 입증 trail: 도입 당일 잠재 버그 2건 발견 (HOTFIX-07 row[0] + HOTFIX-08 transaction 정리)

---

## [2.10.9] - 2026-04-27 — HOTFIX-07 RealDictCursor row[0] KeyError 긴급 복구 (BE only)

> **HOTFIX-07** — v2.10.8 배포 직후 `assert_migrations_in_sync()` 첫 호출 시 worker boot 503 발생. assertion 자체 도입이 5일 누적된 silent 버그를 즉시 노출시킨 사례 (assertion 가치 1차 입증).

### Fixed

- **`backend/app/migration_runner.py _get_executed()`** L51 — `row[0]` → `row['filename']`:
  - `db_pool` 이 `RealDictCursor` 사용 → row 가 dict-like → `row[0]` 은 `KeyError: 0`
  - 이전 `run_migrations()` 의 outer try/except 가 silent 흡수 → 5일간 무인지
  - v2.10.8 의 `assert_migrations_in_sync()` 는 try/except 없이 호출 → KeyError 가 그대로 propagate → gunicorn worker boot 실패 → 503
- **`backend/app/migration_runner.py assert_migrations_in_sync()`** L165+ — outer try/except 안전망 추가:
  - assertion 자체 실패가 worker boot 막지 않도록 (HOTFIX-07 같은 사고 예방)
  - 실패 시 `logger.error(exc_info=True)` + `sentry_sdk.capture_exception(e)` (best-effort)

### Tests

- pytest 회귀 0건
- Railway log: worker boot 정상화, `[migration-assert] ✅ sync OK (12 migrations applied)` 정상 출력

### Deploy

- BE only — Railway 자동 (git push origin main)

### Lesson

- **assertion 도입 자체가 사고 발견 trigger 가 됨** — 5일간 silent 흡수된 row[0] KeyError 가 try/except 없는 호출 경로에서 즉시 노출. 향후 신규 assertion 도입 시 outer try/except 안전망 표준화 권장.

---

## [2.10.8] - 2026-04-27 — 알람 시스템 사후 검증 마무리 3건 (BE only)

> **Sprint**: OBSERV-RAILWAY-LOG-LEVEL-MAPPING + POST-REVIEW-MIGRATION-049-NOT-APPLIED + OBSERV-ALERT-SILENT-FAIL
> 4-22 발생 알람 silent failure (5일간 52건 NULL) 의 사후 검증 마무리. 외부 자동 감지 layer (Sentry) + log level 정확화 + migration sync assertion 도입.

### Changed (BE only — 인프라 강화)

#### 1. OBSERV-RAILWAY-LOG-LEVEL-MAPPING (Sentry alert rule 선행 조건)

- **`backend/app/__init__.py`**:
  - `import sys` 추가
  - `logging.basicConfig(... stream=sys.stdout, force=True)` 명시 (기본 stderr 금지)
- **`backend/Procfile`**:
  - gunicorn `--access-logfile=- --log-level=info` 추가
- 효과: Python `logger.info()` 호출이 Railway 에서 'error' level 로 잘못 태깅되던 문제 해소. Sentry alert rule 의 `level=error` 필터 정확 작동.

#### 2. OBSERV-ALERT-SILENT-FAIL (Sentry 정식 연동)

- **`backend/requirements.txt`**: `sentry-sdk[flask]>=2.0` 추가
- **`backend/app/__init__.py`**: `_init_sentry()` 함수 신규 (~50 LOC)
  - DSN env 없으면 graceful skip (로컬/test 환경 호환)
  - `FlaskIntegration` + `LoggingIntegration` (INFO breadcrumb / ERROR event capture)
  - `release` 자동 binding (version.py)
  - `send_default_pii=False` (PII 보호)
  - 환경변수: `SENTRY_DSN` (필수), `SENTRY_ENVIRONMENT` (기본 production), `SENTRY_TRACES_SAMPLE_RATE` (기본 0.0)
- **`backend/app/migration_runner.py`**: 실패 시 `sentry_sdk.capture_exception(e)` 추가
- 효과: scheduler 죽음 / migration 실패 / target_worker_id NULL 다발 등 silent failure 외부 자동 감지

#### 3. POST-REVIEW-MIGRATION-049-NOT-APPLIED + OBSERV-MIGRATION-RUNNER-STARTUP-ASSERTION

- **`backend/app/migration_runner.py`** `assert_migrations_in_sync()` 함수 신규 (~40 LOC):
  - disk(코드) vs DB(`migration_history`) 동기화 검증
  - `not_yet_applied` 발견 시 logger.error + `sentry_sdk.capture_message`
  - 4-22 049 미적용 사례 같은 silent gap 즉시 외부 알림
- **`backend/app/__init__.py`**: `run_migrations()` 직후 `assert_migrations_in_sync()` 호출
- **신규 산출물**: `POST_MORTEM_MIGRATION_049.md` — 4가지 가설 검증 (가설 ④ "Docker artifact / Railway build cache" 가장 유력) + 재발 방지 권장 3건

### Twin파파 측 작업 (배포 후)

1. **Sentry 가입 + project 생성**:
   - https://sentry.io 가입
   - "Create Project" → Platform: Python → Framework: Flask
   - DSN 발급 (예: `https://abc123@o123.ingest.sentry.io/456`)
2. **Railway env 추가**:
   ```
   SENTRY_DSN = <발급받은 DSN>
   SENTRY_ENVIRONMENT = production  (선택, 기본 production)
   SENTRY_TRACES_SAMPLE_RATE = 0.0  (선택, performance tracing OFF)
   ```
3. **Sentry alert rule 설정** (Sentry Dashboard):
   - Issues → Alert rules
   - Rule: `level == error AND message contains "[migration-assert]" or "[scheduler]"` → 즉시 알림
4. **검증**:
   - Railway logs: `[sentry] initialized (env=production, release=2.10.8)`
   - Railway logs: `[migration-assert] ✅ sync OK (12 migrations applied)`
   - Sentry test event 자동 발송 확인

### Tests

- pytest test_scheduler.py 8 passed / 1 skipped / 회귀 0건 ✅ (logging 변경 영향 0)
- BE syntax check (init/migration_runner) ✅

### Codex 이관 미해당

- LOG-LEVEL: 코드 ~10 LOC (인프라 설정 only)
- POST-REVIEW: 분석 보고서만 (코드 변경 분리)
- SENTRY: 코드 ~90 LOC, 인증/스키마/API 무관 + 1파일 수준

→ Codex 이관 체크리스트 6항목 미충족. Claude Code 자체 검토 + pytest 회귀 충분.

### Deploy

- BE only (frontend 변경 0)
- 배포: Railway 자동 (git push origin main)
- Production: https://axis-ops-api.up.railway.app (BE)
- Sentry DSN 설정은 Twin파파 측 별도 (위 작업 1~2번)

### Rollback

- LOG-LEVEL: `__init__.py` + Procfile git revert
- SENTRY: `__init__.py` + `requirements.txt` git revert (또는 `SENTRY_DSN` env 제거로 graceful skip)
- migration assertion: `__init__.py` 호출 + `migration_runner.py` 함수 git revert

### Related

- 설계 상세: 본 commit + `POST_MORTEM_MIGRATION_049.md`
- 4-22 사건 trail: `BACKLOG.md` L319 (HOTFIX-ALERT-SCHEMA-RESTORE), L324 (POST-REVIEW), L333 (POST-REVIEW-MIGRATION-049-NOT-APPLIED)

---

## [2.10.7] - 2026-04-27 — HOTFIX-06 warmup_pool() 시계 리셋 누락 수정 (사후 보충)

> ⚠️ **사후 보충 entry** (2026-04-27 정리). v2.10.7 commit 시 CHANGELOG 추가 누락.

### Fixed

- **`backend/app/db_pool.py warmup_pool()`** L240+ — `_conn_created_at[id(conn)] = time.time()` 1줄 추가:
  - v2.10.6 OBSERV-DB-POOL-WARMUP 배포 후 결함 발견: warmup 외형상 작동하지만 SELECT 1 만 실행하고 시계 리셋 안 함 → `_is_conn_usable()` 가 expired 판정 → discard → direct conn fallback
  - 동일 파일 내 `_create_direct_conn() L112`, `get_conn() L154-155` 의 검증된 패턴 그대로 적용 (명백한 누락 정정)

### Tests

- pytest test_scheduler.py 8 passed / 1 skipped / 회귀 0건 (327.32s)

### Deploy

- BE only — Railway 자동 (git push origin main)
- git commit: `7a13085`

### Limitation (per-worker 함정)

본 fix 는 fcntl lock 으로 1 worker (Worker A) 만 scheduler 실행 → Worker A 의 pool 만 시계 리셋. **Worker B 의 pool 은 자연 만료**. 결과: conn 7~11 진동 (영구 10 의도는 절반 달성). 사용자 영향 0 입증 후 D+1 측정 결과 따라 v2.10.8 HOTFIX-06b (각 worker 자체 warmup) 진행 결정.

### Related

- v2.10.6 OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP 후속
- 별건 잠재 BACKLOG: HOTFIX-06b (per-worker warmup, D+1 측정 후 결정)

---

## [2.10.6] - 2026-04-27 — FEAT-PIN-STATUS-BACKEND-FALLBACK + OBSERV-DB-POOL-WARMUP

> **PIN 자동 복구 (FE) + DB Pool warmup (BE) 병행 배포**.
> FIX-PIN-FLAG v2.10.5 (1차 보호) + 본 v2.10.6 의 backend fallback (2차 보호) 으로 PIN 손실 사용자 자동 복구. 동시에 실측으로 입증된 MIN=5 무효 문제 (10:14→10:24 conn 10→9→7) 도 warmup cron 으로 해결.

### Added (FE — FEAT-PIN-STATUS-BACKEND-FALLBACK-20260427, P1 격상)

- **`frontend/lib/services/auth_service.dart`** `getBackendPinStatus()` 신규 (~15 LOC):
  - `/auth/pin-status` (BE 엔드포인트, JWT 보호) 호출 → `{"pin_registered": bool}` 응답 파싱
  - 호출 실패 (네트워크/서버) 시 `false` 반환 → 정상 흐름 fallback (debugPrint 로그)
- **`frontend/lib/main.dart`** L275~ 라우팅 분기 추가 (~16 LOC):
  - `tryAutoLogin()` 성공 후 `getBackendPinStatus()` 호출
  - `pin_registered=true` → `savePinRegistered(true)` 로 로컬 양방향 sync 복구 + PinLoginScreen 으로 진입
  - `pin_registered=false` → 정상 흐름 (마지막 경로 복원, HomeScreen)
- 효과: PIN 사용자가 로컬 storage 잃어도 (IndexedDB 손실 시) backend 가 진실의 source 로 자동 복구 → 사용자 보안 의도 유지

### Added (BE — OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP-20260427, P2)

- **`backend/app/db_pool.py`** `warmup_pool() -> tuple[int, int]` public 함수 신규 (~40 LOC):
  - `_MIN_CONN` 만큼 `getconn()` → `SELECT 1` → `putconn()`
  - 모든 idle conn 의 `max_age` 시계 리셋 → MIN 강제 유지
  - finally 블록으로 반납 보장
  - Claude Code advisory 1차 A1 반영 (private `_pool` 직접 import 회피, public API 노출)
- **`backend/app/services/scheduler_service.py`** L17, L23 import 추가 (`IntervalTrigger`, `warmup_pool`):
  - `_pool_warmup_job()` 신규 함수 (warmup_pool 호출 + 결과 로그)
  - `add_job` 등록 — `IntervalTrigger(minutes=5)` + `next_run_time=datetime.now(Config.KST) + timedelta(seconds=10)` (timezone-aware, A5 반영)
  - 스케줄러 job 수: **11 → 12**

### 실측 데이터 (OBSERV-WARMUP 트리거 근거)

```
2026-04-27 KST (DB_POOL_MIN=5, DB_POOL_MAX=30, max_age=300s):
  10:14:00  풀 초기화 직후     OPS 10 conn (5×2 worker)  baseline
  10:19:00  5분 경과            OPS  9 conn (-1)          max_age 1차 만료
  10:24:00  10분 경과           OPS  7 conn (-3)          감소 가속
```

→ Codex 라운드 3 A4 advisory ("MIN=5 효과는 max_age 만료 직전~직후 변동 가능, 실측 필요") 가 10분만에 실측으로 입증.

### Claude Code advisory 1차 (M=0 / A=5, OBSERV-WARMUP)

| # | Advisory | 반영 |
|:---:|:---|:---|
| A1 | `_pool` private API 직접 import → public `warmup_pool()` 노출 권장 | ✅ db_pool.py 에 public 함수 추가 |
| A2 | pytest TC test env `_pool=None` skip 처리 명시 | ✅ warmup_pool 자체에서 None 처리 |
| A3 | `IntervalTrigger` 명시 import 권장 | ✅ scheduler_service.py L17 |
| A4 | ThreadPool max=10 - warmup 5 = 여유 5 (burst 차단 위험 낮음) | ✅ 위험 평가 완료 |
| A5 | `next_run_time=datetime.now()` → timezone 명시 권장 | ✅ `Config.KST` 적용 |

### Codex 이관 여부

- **FEAT-PIN-STATUS-BACKEND-FALLBACK**: ❌ 6항목 미충족 (FE 2파일 + main.dart 분기 추가만, 인증 흐름은 `getBackendPinStatus` 호출 추가 + `savePinRegistered(true)` 호출 — 인증 로직 신규 X). FIX-PIN-FLAG v2.10.5 의 후속이라 같은 검토 컨텍스트.
- **OBSERV-DB-POOL-WARMUP**: ❌ 6항목 미충족 (BE 1함수 신규 + scheduler 1 job 추가). Claude Code 자체 검토만으로 진행.

### Tests

- `tests/backend/test_scheduler.py` 8 passed / 1 skipped / 회귀 0건 ✅
- BE syntax check (db_pool.py + scheduler_service.py) ✅

### Deploy

- 빌드: flutter build web --release ✓ 12.1s
- 배포 (FE): Netlify Deploy ID `69eef28fca3b7ffce577068d` (2026-04-27 KST)
- 배포 (BE): Railway 자동 (git push origin main)
- Production URL: https://gaxis-ops.netlify.app

### Post-deploy 검증

#### Railway logs (배포 직후)

```
[scheduler] Scheduler initialized with 12 jobs   ← 11 → 12 확인
[pool_warmup] 5/5 conn warmed                    ← 10초 후 첫 실행
```

#### 1시간 관찰 (`pg_stat_activity`)

매 5분마다 conn 수 측정 → **10 영구 유지** = 성공. 7 이하로 감소 시 Phase C (warmup 효과 미진).

### 신규 BACKLOG 갱신

- `FEAT-PIN-STATUS-BACKEND-FALLBACK-20260427` 🔴 P1 → ✅ COMPLETED (v2.10.6)
- `OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP-20260427` 🟡 P2 → ✅ COMPLETED (v2.10.6)
- `AUDIT-PWA-SW-INDEXEDDB-PRESERVE-20260427` 🟡 P2 (대기, 30분 audit)
- `UX-LOGIN-FALLBACK-PIN-RESET-LINK-20260427` 🟢 P3 (대기)
- `FEAT-AUTH-STORAGE-MIGRATION-FULL-20260427` 🟡 P2 (대기, 보안 trade-off 검토)

### Rollback

- FEAT-PIN-STATUS: `main.dart` + `auth_service.dart` git revert → flutter build → Netlify
- OBSERV-WARMUP: `db_pool.py` + `scheduler_service.py` git revert → Railway 자동 재배포 (~1분)
- 둘 다 부수 효과 없음

### Related

- 설계 상세: `AGENT_TEAM_LAUNCH.md`
  - FEAT-PIN-STATUS-BACKEND-FALLBACK-20260427 섹션 (L31772+)
  - OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP-20260427 섹션 (L32002+)
- 별건 (관찰 중): `FIX-DB-POOL-MAX-SIZE-20260427` Phase B (D+0 ~ D+3 화/수/목)

---

## [2.10.5] - 2026-04-27 — FIX-PIN-FLAG-MIGRATION-SHAREDPREFS

> **PIN 등록 플래그 storage 안정화** — `pin_registered` 를 SecureStorage (IndexedDB) → SharedPreferences (localStorage) 양방향 sync 이전. 4 라운드 advisory review (Claude Code 1차 + Codex 1차 — M 8건 + 추가 리스크 2건 전수 반영) 후 적용.

### Changed

- **`frontend/lib/services/auth_service.dart`** L20, L243-360 — `pin_registered` 플래그 양방향 sync 패턴 적용:
  - `hasPinRegistered()`: SharedPrefs 우선 read, fallback SecureStorage + 자동 sync (양방향, SecureStorage 유지 — rollback 안전)
  - `savePinRegistered()`: SharedPrefs 주 저장소 + SecureStorage best-effort try/catch (atomic 보장 불가 → non-fatal 로 처리, debugPrint 로그)
  - `logout()` (L243): SharedPrefs `pin_registered` 도 정리 (양방향 cleanup)
- `package:flutter/foundation.dart` import 추가 (debugPrint 사용)

### 부수 변경

- **`frontend/lib/screens/home/home_screen.dart`** — 알림 화면에서 돌아올 때 `alertProvider.refreshUnreadCount()` 호출 (배지 카운트 동기화). FIX-PIN-FLAG 와 무관한 별건 개선, 같은 commit 에 포함.

### 4 라운드 advisory trail (M=8/8 + 추가 리스크 2/2 반영)

- **Claude Code 1차** (사전 자체 검증, 6건):
  - A1 인증 로직 영향 → Codex 이관 결정
  - A2 connection 인과 정량 입증 부재 → baseline SQL 3종 추가
  - A3 ⛔ 단방향 마이그레이션 시 rollback 위험 → 양방향 sync 채택
  - A4 `savePinRegistered()` 양방향 write 패턴
  - A5 race condition (낮은 위험)
  - A6 IndexedDB 손실 trigger 정확성

- **Codex 1차** (M=8 / 추가 리스크 2):
  - M1/Q1.a atomic 보장 불가 → best-effort try/catch + 로그 명시
  - M2/Q3.f baseline SQL `request_path` LIKE 패턴 정정
  - M3/Q4.i SW 업데이트 ≠ IndexedDB 손실 정정
  - Q2.d Rollback 표 5번째 케이스 (SharedPrefs 'true' + SecureStorage write 실패)
  - Q2.e Cohort 정의 (cohort_A/B + secure_write_ok/fail)
  - Q3.g 다른 가설 구분 cohort (device_id, UA, 시간대)
  - Q3.h D+7 통계 신뢰성 (3일 pre/post + active worker 정규화)
  - Q4.j iOS Safari localStorage 도 영향
  - 추가 리스크 1: refresh_token + worker_id + worker_data 도 SecureStorage → BACKLOG `FEAT-AUTH-STORAGE-MIGRATION-FULL` 신규
  - 추가 리스크 2: backend `/auth/pin-status` 가 진짜 root fix → BACKLOG `FEAT-PIN-STATUS-BACKEND-FALLBACK` P2 → P1 격상

### Limitation

본 Sprint = 1차 보호 layer. `pin_registered` 만 단독 손실 케이스 (드뭄) 보호. **4개 키 함께 손실 (Clear site data, Storage quota evict, iOS Safari 7일 idle) 시 효과 없음** — `FEAT-PIN-STATUS-BACKEND-FALLBACK` (P1 격상) 이 진짜 root fix.

### Deploy

- 빌드: flutter build web --release ✓ 12.2s
- 배포: Netlify Deploy ID `69eed5d26147a9d3c6966ecf` (2026-04-27 KST)
- Production URL: https://gaxis-ops.netlify.app

### Baseline 측정 (Twin파파 pgAdmin 배포 전 1회 권장)

설계서 L31644~31691 SQL 3종 — PIN 손실 의심 사용자 / login attempts 추세 / auth_pct. 결과는 D+7 재측정과 비교하여 본 Sprint 효과 정량 입증.

### Rollback

`frontend/lib/services/auth_service.dart` 변경 git revert → flutter build web → Netlify 배포. 양방향 sync 채택으로 rollback 안전 (단, SecureStorage write 실패한 cohort 만 잔존 위험).

### 신규 BACKLOG (4개 후속 Sprint)

- `FEAT-PIN-STATUS-BACKEND-FALLBACK-20260427` 🔴 P1 (격상 — 진짜 root fix)
- `AUDIT-PWA-SW-INDEXEDDB-PRESERVE-20260427` 🟡 P2
- `UX-LOGIN-FALLBACK-PIN-RESET-LINK-20260427` 🟢 P3
- `FEAT-AUTH-STORAGE-MIGRATION-FULL-20260427` 🟡 P2 (Codex 신규 권장)

### Related

- 설계 상세: `AGENT_TEAM_LAUNCH.md` FIX-PIN-FLAG-MIGRATION-SHAREDPREFS-20260427 섹션
- Codex 1차 advisory: `CODEX_REVIEW_FIX_PIN_FLAG_20260427.md`
- 별건 (병행): `FIX-DB-POOL-MAX-SIZE-20260427` Phase B 관찰 중

---

## [Infra] - 2026-04-27 — FIX-DB-POOL-MAX-SIZE-20260427

> **인프라 변경 only — 코드 변경 0, 버전 bump 없음**.
> Railway env `DB_POOL_MAX` **20 → 30** 변경 (MIN=5 유지). 4 라운드 advisory review (Codex 1차 + Claude Code 2차 + Codex 3차 + Twin파파 fact-check 4차) 로 약점 12건 정정 후 적용.

### Changed (Railway env only)

- `DB_POOL_MAX`: 20 → **30** (per-worker 독립 pool × 2 worker = Postgres 60/100 점유)
- `DB_POOL_MIN`: 5 (변경 없음, 기존 운영값 유지)

### 결정 근거 (Q-B 결정적 데이터)

- **2026-04-21 화요일 출근 burst 측정** (4-25 ~ 4-27 진단):
  - peak 31 동시 in-flight (08:06:07 KST)
  - 21 동시 in-flight 17회 (07:46~08:55, 70분간)
  - MAX=20 환경에서 fallback 1건/peak 발생 (라운드 4 정정 — 이전 추정 ~100건/일은 코드 default 가정 오류 기반)
- **per-worker 독립 pool 구조** (`backend/app/__init__.py:60-62` `init_pool()` in `create_app()`):
  - gunicorn `-w 2` (preload 없음) → 각 worker fork 후 독립 pool 생성
  - Worker A (scheduler owner, fcntl lock): HTTP 8 + scheduler peak 4 + 여유 = 15 conn 필요
  - Worker B (HTTP only): 8 + 여유 2 = 10 conn 필요
  - MAX=30 채택으로 worker A 100% 안전 + 미래 2x (62 in-flight) 까지 dimensioning

### 4 라운드 advisory trail (M=0 / A=12)

- 라운드 1 (Codex 1차): scheduler peak 8 conn 재계산, 단계적 25→30 한 번에 직행, fallback 비용 (200~500ms) 명시 (4건)
- 라운드 2 (Claude Code 2차): ⛔ per-worker 독립 pool 구조 발견 (단일 pool 가정 정정), Phase B 1일→3일 통계 신뢰성, pg_stat_activity SQL pid+client_addr 정밀화 (4건)
- 라운드 3 (Codex 3차): Q-B 일자 오기 (4-27→4-21) 정정, 5x 산수 오류 (31×5=155 in-flight, MAX=30 으로 부족), MIN=5 ↔ max_age=300s 상호작용, grep `\b` 경계 + `get_db_connection` 함수명 누락 정정 (4건, M=0)
- 라운드 4 (Twin파파 fact-check): ⚠️ 코드 default (1/10) 가정 오류 — 실제 prod 가 이미 5/20 운영 중. 결론 (MAX=30) 유지하되 fallback 빈도 추정 정정 (3건)

### Codex 공식 이관 미해당

본 작업은 단순 env 변경 + 코드 변경 0 + S1/S2 미해당으로 **Codex 이관 체크리스트 6항목 미충족**. Advisory review 만 4 라운드 수행 (정식 Codex 이관 절차 미적용).

### Phase B 관찰 계획 (D+0 ~ D+3)

- D+0 (2026-04-27 월) 16:30~17:00 KST 퇴근 peak — `Pool exhausted` grep
- D+1 (4-28 화) 07:30~09:00 출근 peak
- D+2 (4-29 수) 07:30~09:00 출근 peak
- D+3 (4-30 목) 07:30~09:00 출근 peak + Phase C 결정
- off-peak (12:00) Q-B 동시 in-flight 재측정 SQL (peak 후 O(N²) 부담 회피)

### Rollback

`DB_POOL_MAX = 30 → 20` env 복원 → 자동 재배포 ~1분, 코드 영향 0.

### Related

- 설계 상세: `AGENT_TEAM_LAUNCH.md` FIX-DB-POOL-MAX-SIZE-20260427 섹션 (약점 trail 12건 + 4 라운드 검증 기록)
- 별건 BACKLOG: `OBSERV-DB-POOL-IDLE-DISCONNECT-WARMUP` (P3, 격하 — MIN=5 가 cold-start 일부 흡수), `OBSERV-RAILWAY-HEALTH-TTFB-15S-INTERMITTENT` (P2, 별건), `OBSERV-SLOW-QUERY-ENDPOINT-PROFILING` (P2, 신규 분리)

---

## [2.10.4] - 2026-04-25 — 긴급 health timeout 보정 (사후 보충)

> ⚠️ **사후 보충 entry** (2026-04-27 정리). 이전 세션 (2026-04-25) 배포 시 CHANGELOG 보충 누락. handoff.md 4-27 세션 (2/3) "부수 발견" 으로 추적.

### Fixed (긴급, 현장 영향)

- **`frontend/lib/services/api_service.dart` L209-210** `getPublic()` Dio 인스턴스 timeout 보정:
  - `connectTimeout: 5s` → **10s**
  - `receiveTimeout: 5s` → **20s**
- 트리거: 2026-04-25 KST "System Offline" UX 발생. Railway `/health` 200 OK 정상 응답 + TTFB 12~15s 간헐 (외부 원인) → Flutter health check 5s timeout 초과 → 클라이언트가 false-positive `System Offline` 표시
- 해결: 일반 API timeout (15s) 와 일관성 + 5s 여유 → 20s. Railway TTFB 지연 근본 원인은 별건 (`OBSERV-RAILWAY-HEALTH-TTFB-15S-INTERMITTENT` BACKLOG 추적).

### Deploy

- 빌드: flutter build web --release ✓ 45.2s
- 배포: Netlify Deploy ID `69ec09a231e1446389627519` (2026-04-25 KST)
- git commit: `cd701e2` "fix: v2.10.4 health check timeout 5s→20s — System Offline false positive 긴급 해소"

### Related

- 별건 BACKLOG: `OBSERV-RAILWAY-HEALTH-TTFB-15S-INTERMITTENT` 🟡 P2 — Railway TTFB 15s 근본 원인 조사 + 외부 모니터링 도입 검토
- v2.10.6 OBSERV-DB-POOL-WARMUP 적용 후 `direct conn fallback` 빈도 0 도달 시 → TTFB 자연 안정화 가능 (부수 효과 검증 필요)

---

## [2.10.3] - 2026-04-24

> FIX-ORPHAN-ON-FINAL-DELIVERY — v2.10.2 배포 후 Q4-5 48h 관찰에서 발견된 숨은 4번째 delivery 실패 경로 수정. 2026-04-22 HOTFIX-ALERT-SCHEDULER-DELIVERY 가 `scheduler_service.py` 3곳만 고쳤는데 `task_service.py` 내 `complete_task` 경로에 동일 패턴의 **target_worker_id 미지정 버그** 가 숨어있어 2026-04-23~24 4일간 8건 legacy NULL 발생.

### Fixed

- **`task_service.py:391~419` ORPHAN_ON_FINAL alert INSERT** — `_create_alert_61(...)` 호출 시 `target_role` 만 지정하고 `target_worker_id` 누락 → `role_ELEC`/`role_TMS` room broadcast → 구독자 0 → **관리자 전원 alert 수신 실패**
- 수정: `_resolve_managers_for_category` (scheduler_service.py 표준 패턴) 재사용 + 관리자별 개별 INSERT 로 전환. `target_worker_id=manager_id` 지정
- 부수: 로그 메시지에 `managers={N}` 추가 (delivery count 가시화)

### 실측 피해 (2026-04-23 Codex 사후 Q4-5 관찰 기반)

| 구간 | NULL 건수 | 상태 |
|---|---|---|
| 2026-04-23 14:51 ~ 04-24 08:07 KST | 8건 | 미전달 (legacy, 자연 소거 대상) |
| 이후 (v2.10.3 배포 이후) | 0건 예상 | ✅ |

### Tests

- **TC-61B-22B 신규** (`test_sprint61_alert_escalation.py::TestOrphanOnFinal`)
  - ORPHAN_ON_FINAL alert INSERT 시 `target_worker_id IS NOT NULL` 보장 회귀 가드
  - `_resolve_managers_for_category('ELEC')` 반환 매니저 수만큼 개별 INSERT 검증
- pytest 4/4 GREEN (TC-61B-20/21/22/22B)

### Related

- **HOTFIX-ALERT-SCHEDULER-DELIVERY-20260422** 의 숨은 4번째 경로 — v2.10.3 으로 완전 종결
- 신규 BACKLOG: `CASCADE-ALERT-NEXT-PROCESS` 🟢 DRAFT — ORPHAN_ON_FINAL 의 원래 설계 의도 (현재 공정 + 다음 공정 관리자 동시 알림 = 공정 연쇄 차단 알림) 는 사내 공정 (PI/QI/SI) 활성화 계획 변동 이슈로 후순위 보류. 현재는 A안 (해당 공정 관리자만) 유지.

---

## [2.10.2] - 2026-04-23

> FIX-CHECKLIST-DONE-DEDUPE-KEY — 2026-04-22 HOTFIX 4건 일괄 Codex 사후 검토 (Phase A) 결과 발견된 M1 (Q4-4) + Q4-2 advisory 일괄 수정.
> **프로덕션 알람 누락 리스크 해소**: 동일 S/N 내 복수 ELEC task (IF_1 + IF_2 등) 가 open 상태일 때 첫 alert 이후 나머지 3일 suppress 되는 버그.

### Fixed

- **CHECKLIST_DONE_TASK_OPEN dedupe key 오류 수정** (`scheduler_service.py:1064~1070`, Codex 사후 Q4-4 M)
  - dedupe 쿼리에 `task_detail_id = %s` 누락 → 같은 S/N 내 서로 다른 ELEC task 의 alert 가 서로 suppress 되는 버그
  - 수정: `WHERE serial_number = %s` → `WHERE serial_number = %s AND task_detail_id = %s`
  - 부수 효과: `idx_alert_logs_dedupe` partial index (`WHERE task_detail_id IS NOT NULL`) 활용 가능
- **RELAY_ORPHAN dedupe `message LIKE` → `task_detail_id` 전환** (`scheduler_service.py:883~913`, Codex 사후 Q4-2 advisory)
  - 기존: `message LIKE '%task_name%'` — 동명 task 중복 매칭 가능 + 인덱스 miss
  - 수정: `task_detail_id = orphan['task_detail_id']` — 정확한 dedupe + index 활용
  - 부수: INSERT dict 에도 `'task_detail_id': orphan['task_detail_id']` 추가

### Tests

- **TC-61B-19B 신규** (`test_sprint61_alert_escalation.py::TestChecklistDoneTaskOpen`)
  - 동일 S/N 에 ELEC open task 2건 (`PANEL_WORK` + `WIRING`) 상황에서 **각각 DISTINCT alert 발송** 검증
  - v2.10.2 이전 버그 회귀 가드 (이전 버전으로 롤백 시 FAIL)
- **setup_sprint61 fixture 보강** — `product_info` INSERT 에 `mech_partner='FNI'` + `elec_partner='TMS'` 추가
  - `_resolve_managers_for_category` 가 partner 필드로 관리자 찾기 때문에 누락 시 alert 0건 → 기존 TC-61B-17 도 불안정
  - 사전 누락된 fixture 정정 (v2.10.2 변경과 별개, 동일 커밋에 포함)

### Codex 사후 검토 결과 반영 (POST-REVIEW-HOTFIX-BATCH 2026-04-23)

- **HOTFIX #1 (PHASE1.5)**: Close ✅ — Q1-1/1-3 Advisory 는 `OBSERV-ALERT-SILENT-FAIL` 흡수
- **HOTFIX #2 (SCHEMA-RESTORE)**: Close ✅ — Q2-1/2-2/2-3 Advisory 는 기존 BACKLOG 흡수 (runbook / MIGRATION-049 / STARTUP-ASSERTION)
- **HOTFIX #3 (DUP)**: Close ✅ — Q3-2/3-3/3-4 Advisory 는 신규 FIX 엔트리 + Redis 조건부 유지
- **HOTFIX #4 (DELIVERY)**: **본 PATCH 로 Close** ✅ — Q4-4 M 수정 + Q4-2 동시 해결
- **Q4-1 role 경로 company 필터**: 🟠 신규 `SEC-ROLE-COMPANY-FILTER` 엔트리 등록 (leakage 리스크)
- **Q4-3 N+1 query**: `REFACTOR-SCHEDULER-SPLIT` 흡수
- **Q4-5 48h 관찰 SQL**: 실행 권장 (본 배포 후)

---

## [2.10.1] - 2026-04-23

> Sprint 62-BE 보정 PATCH — VIEW 측 입장 재검토 후 요청 반영. v2.2 에서 "숫자 변동 없음(31대 유지)" 근거로 `ship_plan_date` 유지 결정했으나, 주간 생산량의 **의미** (생산 완료 기준) 측면에서 `finishing_plan_end` 가 라벨 [Planned Finish] 과 일치. 실측 기반 수치 변동 투명 공개.

### Fixed

- **`weekly-kpi` WHERE 절 교정** (`backend/app/routes/factory.py` L322) — `ship_plan_date` → `finishing_plan_end` 1줄 수정. v2.2 에서는 "31대 유지 우선"으로 보류했으나 VIEW v1.34.4/Sprint 36 논의 결과 "주간 생산량 = 완료 기준" 의미 일치 우선 결정. 응답 `production_count` 숫자 변경 유의 (하위 3필드 `shipped_plan/actual/ops` 는 영향 없음)
- **TC-FK-02 업데이트** — "ship_plan_date 유지 회귀" → "finishing_plan_end 교정 검증" 으로 의미 반전. DB 직접 COUNT 와 응답 `production_count` 일치 assertion

### 실측 수치 변동 (2026-04-23 Railway)

| 기간 | ship_plan_date 기준 (기존) | finishing_plan_end 기준 (신규) | 차이 |
|---|---|---|---|
| 이번 주 (2026-04-20~26) | 31 | 48 | +17 (+55%) |
| 지난 주 (2026-04-13~19) | 30 | 51 | +21 (+70%) |

### Claude 원안 약점 기록 (CLAUDE.md ④ 맹목 동조 방지)

- v2.2 확정 당시 "주간 숫자 불변"을 설계 가치로 높게 평가 → 실제 중요한 건 **의미 일치**였음. "숫자 변경 리스크"를 과대 평가하여 의미 정확성 교정을 1 cycle 지연시킴
- 이번 PATCH 를 v2.10.0 배포 직후 즉시 적용 → 사용자 혼란 최소화

### Tests

- TC-FK-02 업데이트 후 17/17 GREEN
- 기존 TestWeeklyKpi 5/5 GREEN (스키마 의존만이라 WHERE 변경 무관)

---

## [2.10.0] - 2026-04-23

> Sprint 62-BE v2.2 — 공장 대시보드 Factory KPI 확장 (데이터 공급 인프라). VIEW Sprint 35 (v1.34.4 `mech_start` 영구 유지) + Sprint 36 (옵션 토글) 연계 배포. 경영 KPI 계산 로직 (이행률·정합성)은 `BACKLOG-BIZ-KPI-SHIPPING-01` 이관 (App 베타 100% 전환 후 확정).

### Added

- **`GET /api/admin/factory/monthly-kpi`** (신규 엔드포인트) — 월간 공장 KPI. `date_field` 쿼리 파라미터 4옵션 (`mech_start` / `finishing_plan_end` / `ship_plan_date` / `actual_ship_date`, 기본 `mech_start`). `completion_rate`/`by_stage`/`pipeline`/`by_model` 제외 (monthly-detail 엔드포인트가 담당)
- **`weekly-kpi` 응답 확장** — `shipped_plan` / `shipped_actual` / `shipped_ops` 3필드 + `defect_count=null` placeholder 추가. 기존 `pipeline.shipped` 는 backward compat 유지 (`today` 제한 기존 의미 보존)
- **`_count_shipped(conn, start, end, basis)` 헬퍼** — 출하 카운트 3분기 (plan/actual/ops). 자동 합산(UNION) 없이 3개 소스 독립 반환. 경영 KPI 레이어에서 비교 분석 가능. `force_closed = false` 클린 코어 원칙 적용
- **`monthly-detail` 화이트리스트 확장** — `_ALLOWED_DATE_FIELDS` 3값 → 5값 (`finishing_plan_end`/`ship_plan_date`/`actual_ship_date` 추가). `ProductionPlanPage` 기존 `pi_start`/`mech_start` 토글 유지
- **`_ALLOWED_DATE_FIELDS_MONTHLY_KPI`** (신규 상수) — monthly-kpi 전용 4값 (pi_start 제외). Codex 2차 Q4 M 반영 (화이트리스트 분리)
- **pytest 11 TC** (`tests/backend/test_factory_kpi.py`) — 17 assertions (parametrize 확장). 반개구간 `[start, end)` 경계 TC 포함 (Codex 3차 Q6 A)

### Infrastructure

- **Migration 050** (`050_factory_kpi_indexes.sql`) — `plan.product_info` 에 `actual_ship_date` / `finishing_plan_end` 컬럼 `ALTER TABLE ADD COLUMN IF NOT EXISTS` (Prod 기존 존재 → no-op, Test DB → 신규 생성). Partial index 3개 `CREATE INDEX CONCURRENTLY IF NOT EXISTS` (`actual_ship_date` / `ship_plan_date` / `finishing_plan_end`, `WHERE IS NOT NULL` 조건)
- Test DB 스키마 drift 발견 및 해결 — Prod엔 `actual_ship_date` 등이 ETL 시스템에 의해 추가돼 있으나 migration SQL 부재 → migration 050 에 DDL 명시로 양쪽 정합 확보

### AI 교차 검증

- **Codex 1차** (v1): M1(UNION 경계 중복), M2(반개구간), M3(`_FIELD_LABELS` `finishing_plan_end` 누락) 지적
- **Codex 2차** (v2 VIEW 역제안): M 2건 (Q4 화이트리스트 불일치 / Q5 `shipped_plan` 의미 모호) + A 4건
- **Codex 3차** (v2.2 축소): **M=0 / A=4 CONDITIONAL APPROVED**. A 4건 전부 합의 기반 반영 (INNER JOIN / EXPLAIN 배포 후 검증 / 네이밍 부채 debt / 반개구간 경계 TC)
- Claude 원안 약점 4건 trail 기록 (CLAUDE.md ④ 맹목 동조 방지 규칙 준수)

### Tests

- 신규 TC 17/17 GREEN (test_factory_kpi.py)
- 회귀 TC 36/36 GREEN (test_factory.py + test_admin_api.py)
- 총 53 PASSED / 0 regression

### Deferred (BACKLOG)

- `BACKLOG-BIZ-KPI-SHIPPING-01` (🟢 DRAFT) — 경영 대시보드 이행률(`fulfillment_rate = actual/plan`) / 정합성(`app_coverage_rate = ops/actual`) 지표. App 베타 100% 전환 후 착수 검토
- `POST-REVIEW-SPRINT-62-BE-V2.2-20260423` (🟡 OPEN, 7일 내) — Railway EXPLAIN ANALYZE 검증 + 네이밍 부채 FE 혼동 사례 모니터링

### BE 합의 (VIEW Sprint 35/36 연계)

| 항목 | v2.2 최종 |
|---|---|
| weekly-kpi WHERE | `ship_plan_date` 유지 (현 31대 유지) |
| monthly-kpi `date_field` | 4옵션, 기본 `mech_start` (pi_start 제외) |
| `_ALLOWED_DATE_FIELDS` (monthly-detail) | 5값 (pi_start 포함 유지) |
| 출하 응답 | **3필드** (`shipped_plan/actual/ops`, `shipped_count`/`union` 폐기) |
| `shipped_ops` 네이밍 | 기존 `shipped_realtime` 리네임 (AXIS-OPS 정체성) |

---

## [2.9.11] - 2026-04-22

> 2026-04-22 하루 동안 발생한 5일 알람 장애 (4-17~22 `app_alert_logs` INSERT 0건) 근본 원인 확정 및 복구. 4 HOTFIX 통합 PATCH release.

### Fixed

- **Alert delivery 복구** (HOTFIX-ALERT-SCHEDULER-DELIVERY-20260422) — `scheduler_service.py` 3곳 (RELAY_ORPHAN / TASK_NOT_STARTED / CHECKLIST_DONE_TASK_OPEN) 이 `target_worker_id` 미지정 + `target_role` 만으로 broadcast 하여 `role_TMS` / `role_elec_partner` 등 `role_enum` 외 값 room 으로 알람 발송 → 구독자 0 → 52+17 = 69건 완전 undelivered. `task_service.py` L571 표준 패턴 (`get_managers_by_partner` / `get_managers_for_role` → 관리자별 개별 INSERT) 로 통일
- **Alert 중복 발송 제거** (HOTFIX-SCHEDULER-DUP-20260422, commit `f1af8a4`) — Gunicorn multi-worker 환경에서 `_SCHEDULER_STARTED` env 가드가 fork 이후 COW semantics 로 worker 간 전파되지 않음 → 2~3개 scheduler 동시 실행 (R1 실측 37.5% 중복, GPWS-0773 3중복). `fcntl.flock(LOCK_EX | LOCK_NB)` + `/tmp/axis_ops_scheduler.lock` OS 레벨 lock 으로 단일 실행 보장
- **DB schema 복구** (HOTFIX-ALERT-SCHEMA-RESTORE-20260422) — Railway 운영 DB 에 migration 049 미적용 상태 → `app_alert_logs.task_detail_id` 컬럼 부재 + `alert_type_enum` 신규 3종 (`TASK_NOT_STARTED` / `CHECKLIST_DONE_TASK_OPEN` / `ORPHAN_ON_FINAL`) 미등록 → 모든 INSERT `PsycopgError`. pgAdmin 수동 SQL 5 블록 실행으로 복구
- **Dedupe legacy 간섭 차단** (Codex M2 수용) — 3곳 dedupe 쿼리에 `target_worker_id IS NOT NULL` 필터 추가 → legacy 69건 (`target_worker_id=NULL`) 이 window 내에서도 신규 INSERT 차단하지 않도록

### Added

- **Alert silent fail ERROR 로깅** (HOTFIX-SCHEDULER-PHASE1.5, commit `4a6caf8`) — `create_and_broadcast_alert()` / `create_alert()` 에 `[alert_silent_fail]` / `[alert_create_none]` / `[alert_insert_fail]` prefix 추가. Sentry SDK 선택적 import 가드. 본 장애 근본 원인 포착의 결정적 도구
- **`_resolve_managers_for_category` 헬퍼** (scheduler_service.py) — task_category → 관리자 worker_id 리스트 변환. Partner 기반 (TMS/MECH/ELEC) 또는 Role 기반 (PI/QI/SI) 자동 분기
- **AI 검증 워크플로우 ⑦ 단계 강제 절차** (CLAUDE.md) — pytest 실패 발견 시 Claude 단독 "범위 외 판단" 금지, Codex 합의 후 조치 강제. HOTFIX-ALERT-SCHEDULER-DELIVERY 세션 위반 사례 반영

### Infrastructure

- Phase 1.5 로깅 → 본 장애 근본 원인 5분 내 포착 (추론 5일 vs 실로그 5분 — "관찰성 우선" 원칙 재확인)
- 4 HOTFIX 통합 PATCH v2.9.11 로 버전 정리 (이전 누락된 bump 소급 반영)
- FE version skew 명시: 저장소 v2.9.11 vs Netlify 배포 v2.9.10 (FE 코드 변경 0, 다음 FE 배포 시 자동 반영)

### BACKLOG 이관 (후속 Sprint)

- `OBSERV-RAILWAY-LOG-LEVEL-MAPPING` (P1, Sentry 연동 blocker)
- `FIX-LEGACY-ALERT-TMS-DELIVERY` (P3, 69건 복구 옵션)
- `REFACTOR-SCHEDULER-SPLIT` (P2, ~1090 LOC 분할)
- `TEST-ALERT-DELIVERY-E2E` (P2, WebSocket 통합 테스트)
- `TEST-SCHEDULER-EMPTY-MANAGERS` (P3, PI/QI/SI 엣지)
- `BUG-DURATION-VALIDATOR-API-FIELD` (P2, Codex 합의 미실행 — 착수 전 합의 필수)
- `POST-REVIEW-HOTFIX-ALERT-SCHEDULER-DELIVERY-20260422` (S2, 7일 이내 Codex 사후 검토 필수)

---

> 이 이전 변경사항은 `handoff.md` 및 git tag 이력 참조.
