# Sprint 80 — SI 출하예정 주차별 그룹핑 (FEAT-SI-FINISHING-SHIPMENT-WEEK-GROUP)

> 작성 2026-05-29. 사용자(Twin파파) catch + 결정 반영. BACKLOG `FEAT-SI-FINISHING-SHIPMENT-GROUP-BY-MODEL-20260529` 후속 — group 기준이 model 단독 → **ISO 주차(52주) 1차 + model 2차** 로 확정.

## 1. 배경 / 문제

OPS SI 마무리공정 화면 (`frontend/lib/screens/si/si_finishing_screen.dart`, 688 LOC, Sprint 79) 탭3 "출하 예정"이 두 가지 문제를 가짐:

### 문제 A — 200건 cap 누락 (운영 버그)
- BE `admin_shipment_flow.py` L56 `per_page = min(200, ...)`, FE는 `page=1 / per_page=200`만 요청
- 실측: 출하예정(`ship_plan_date > CURRENT_DATE` + 미출하 + TEST 제외) = **389건** → **189건 누락 중**
- 응답에 `total`(389)이 오지만 FE가 무시. 페이지네이션(`page`)은 BE 지원하나 FE 미사용
- 단, **검색(`&q=`)은 BE에서 DB 필터 후 cap이라 특정 S/N 조회는 정상** → 평소 검색 위주 사용이라 체감 안 됐음. 누락은 "검색 없이 전체 스크롤" 시에만 드러남

### 문제 B — 평면 200개 리스트 가독성
- 모델만으로 묶으면 GAIA-I DUAL 230건이 한 덩어리 → 의미 없음
- 출하날짜가 제각각 → **주차(week) 단위로 묶어야 관리 가능한 크기**

## 2. 데이터 분석 (2026-05-29 staging 실측)

### 모델별 분포 (top)
```
GAIA-I DUAL 230 · GAIA-I 59 · GAIA-P 38 · GAIA-P DUAL 19 · O3 Destructor 15 · SWS-I 10 · ...
```

### ISO 주차 분포 (총 17개 주차)
```
W23 (6/1~6/5) 22 · W24 (6/8~6/12) 51 · W25 (6/15~6/19) 57 · W26 39 · W27 66
· W28 8 · W29 4 · W30 5 · W31 8 · W32 4 · W33 1 · W34 2 · W35 3 · W37 1 · W41 1
· W53 (12/31) 115 ⚠️ · 2027-W01 2
```
- **W23~W27 (임박 5주)**: 22/51/57/39/66 — 관리 가능한 크기
- **W53 (12/31) 115건**: 출하일 미정 → 연말 placeholder 패턴 (실제 예정일 아님). 그대로 주차 카드로 표시 (별 버킷 분리 안 함 — 운영이 12/31 = 미정으로 인지)

## 3. 확정 사양 (사용자 결정)

| 항목 | 결정 |
|---|---|
| 적용 탭 | **출하예정(탭3)만**. 출하확정(탭2)은 ≤13건이라 평면 유지 |
| 1차 그룹 | **ISO 주차 (52주 체계, `IYYY-IW`)** — 현장이 "24주차"로 일정 관리 |
| 2차 | 주차 카드 펼치면 **모델별 카운트** |
| 정렬 | 주차 오름차순 (출고 임박 주가 위) |
| 펼침 | **펼쳐야 모델 보임** (ExpansionTile 접힘 기본). 임박 주만 펼쳐 봄 |
| 검색 | 검색어 있으면 **group 스킵 → 평면 결과** (특정 S/N 찾기용) |
| 출고 처리 | 검색으로 S/N 찾아 기존 `[출고 완료]` 버튼 (v2.20.15 SI 인원 허용) |

## 4. 권한 (기존 유지 — 변경 0)

- 페이지 조회 `/admin/shipment/by-status`: `@jwt_required + @gst_or_admin_required` (GST 전원 + admin)
- 출고완료 `/api/app/work/ship-complete`: `@si_manager_or_admin_required` (SI 인원 + manager + admin, v2.20.15)
- → SI 인원이 조회·출고완료 모두 가능, 흐름 일관. **Sprint 80은 권한 변경 없음**

## 5. 구현 설계

### BE — 주차+모델 집계 (방안 A 채택)
`shipment_flow_service.get_shipment_by_status` 의 `planned` 분기 응답에 **집계 블록 추가**. 평면 `items`(검색·페이지)는 현행 유지, 집계는 별도 GROUP BY 쿼리(전체 기준, 200 cap 무관).

```
응답 (planned, q 없을 때):
{
  "items": [...],           # 기존 평면 (per_page 적용)
  "total": 389,
  "by_week": [              # 신규 — 전체 389 기준 집계
    {
      "week": "2026-W23",
      "date_from": "2026-06-01", "date_to": "2026-06-07",
      "count": 22,
      "by_model": [{"model": "GAIA-I DUAL", "count": 10}, ...]   # count desc
    }, ...                  # week asc
  ]
}
```

- 집계 쿼리: `GROUP BY to_char(ship_plan_date,'IYYY-"W"IW'), model` → FE/BE 어느 쪽에서 nesting? → **BE에서 nested 구성** (FE 단순화)
- WHERE = planned 평면과 동일 (`ship_plan_date > CURRENT_DATE AND actual_date IS NULL AND customer<>'TEST CUSTOMER'`)
- `q` 있으면 `by_week` 생략(또는 빈 배열) — 검색 모드는 평면만
- **per_page cap**: 200 → 그대로 둘지 상향할지가 쟁점 (§7 Q1). 집계가 by_week로 해결되면 평면 200 유지 가능(검색 위주). 단 "검색 없이 특정 주차 펼침 → 그 주 S/N 목록"을 보려면 그 주차 S/N이 평면 200 안에 있어야 함 → drill-down 방식 결정 필요 (§7 Q2)

### FE — `si_finishing_screen.dart`
- `_buildShipmentTab(isConfirmed:false)` 분기:
  - `_searchQuery.isEmpty` → `by_week` 기반 **주차 ExpansionTile 리스트** (접힘 기본, 펼치면 모델 카운트 행)
  - `_searchQuery.isNotEmpty` → 기존 평면 `ListView.builder` + `_buildShipmentCard`
- 주차 카드 헤더: `📅 W24 (6/8~6/12) · 51건`
- 펼친 내용: 모델별 `GAIA-I DUAL · 10` 행 (카운트 desc)
- 출고확정(isConfirmed:true) 무변경

## 6. 변경 파일 / 범위

| 파일 | 변경 |
|---|---|
| `backend/app/services/shipment_flow_service.py` | planned 분기에 `by_week` 집계 쿼리 + nested 구성 (~40 LOC) |
| `backend/app/routes/admin_shipment_flow.py` | 응답에 `by_week` 패스스루 (이미 dict 반환이면 0~2 LOC) |
| `frontend/lib/screens/si/si_finishing_screen.dart` | `_buildShipmentTab` 주차 ExpansionTile 분기 (~60 LOC) |
| `tests/backend/test_*` | by_week 집계 TC (주차 그룹/모델 nested/정렬/q 시 생략) |
| 권한 | 변경 0 |
| migration | 불필요 (기존 테이블 조회만) |

## 7. Codex 검증 쟁점 (M/A 분류 요청)

- **Q1 per_page cap**: 집계(by_week) 도입 후 평면 `items` per_page 200을 유지할지 상향(2000)할지. 검색 위주면 200 유지 가능하나, 주차 펼침 drill-down을 평면 items에서 하려면 부족.
- **Q2 주차 펼침 drill-down 데이터원**: 주차 카드 펼쳐 모델 카운트만 볼지(by_week.by_model로 충분), 아니면 그 주차 S/N 목록까지 펼칠지. S/N 목록까지면 (a) 전체 items 로드(per_page 상향) (b) 주차 클릭 시 `q`/주차필터 추가 요청. 사용자 의도 = "카운트 현황 + 검색으로 출고" → **모델 카운트만으로 충분, S/N drill-down 불필요** 추정. 확인 필요.
- **Q3 W53 115건 placeholder**: 출하일 미정이 12/31로 몰림. 그대로 W53 카드 표시 vs "미정" 버킷. → 그대로 표시 (운영 인지) 결정. 동의?
- **Q4 집계 nesting 위치**: BE nested(week→by_model) vs FE 클라 집계. BE nested 채택 — FE 단순화 + 전체 기준 정확. 동의?
- **Q5 정렬 tie-break**: 같은 주차 내 모델은 count desc, 동수면 model asc. by_week 자체는 week asc. 적절?
- **Q6 성능**: 집계 쿼리 1건 추가(GROUP BY week,model). 389 규모 무시 가능. 미래 수천 건 시? 인덱스(ship_plan_date) 활용.
- **Q7 회귀**: 출하확정 탭 / pending 탭 / 검색 동작 불변? `by_week`는 additive 응답이라 기존 소비처 영향 0.
- **Q8 pytest**: by_week 그룹/nested/정렬/q-시-생략 TC 충분 범위.

## 7.5 Codex 라운드 1 합의 (2026-05-29) — M=4 / A=2 / N=3

방향 승인. M 4건 설계 반영:

### M-Q6 — base predicate 공유 (WHERE 복붙 정합 리스크)
`total`(L75) / `items`(L122) WHERE가 이미 복붙 중. `by_week` 집계가 또 별도 WHERE면 4중 복붙 → `TEST CUSTOMER` / `ship_plan_date IS NOT NULL` / `actual_date IS NULL` / `q` 조건 어긋날 위험.
→ **planned WHERE predicate를 헬퍼/CTE로 공유**. `by_week`는 q 없을 때만, q 있으면 응답에서 생략(키 부재) 일관 처리.

### M-Q7 — Python 서비스 반환 계약 (HTTP additive ≠ 서비스 계약 additive)
`get_shipment_by_status` 는 `Tuple[List[Dict], int]` 반환(L37), route가 `items, total = ...`(L65) 언패킹, 기존 test도 튜플 계약 사용(`test_sprint79_shipment_flow.py:137`). 여기에 by_week를 끼우면 서비스 계약 깨짐.
→ **기존 튜플 서비스 유지 + 신규 `get_shipment_week_groups()` 별도 함수**를 route에서 planned·no-q일 때만 추가 호출 → JSON에 `by_week`만 append. 회귀 최소.

### M-Q8 — pytest TC 확대 (happy path만으론 부족)
추가 필수 TC:
- `total == sum(by_week[].count)` 정합
- actual_date 완료 건 제외
- TEST CUSTOMER 제외
- route 응답 JSON schema (by_week 구조)
- confirmed 탭엔 by_week 없음
- planned + q 있으면 by_week 없음
- `per_page=1` 이어도 by_week 는 전체(389) 기준

### M-추가 — SI 출고완료 권한 매트릭스 확정 + FE/BE 정합 (Sprint 80에 포함)

사용자 결정 (2026-05-29): **SI 공정 권한 = GST manager + SI 인원 + admin**. PI/QI 제외. 협력사 매니저 제외 (SI = GST 자사 공정).

| 주체 | 조회(by-status) | 출고완료(ship-complete) |
|---|---|---|
| SI 인원 (role=='SI') | ✅ | ✅ |
| GST manager (company=='GST' AND is_manager) | ✅ | ✅ |
| admin | ✅ | ✅ |
| GST PI/QI (비매니저) | ✅ | ❌ |
| 협력사 매니저 (company≠'GST') | ❌ (조회 GST-only) | ❌ |

**사용자 추가 결정 (2026-05-29)**: "협력사 매니저 Read 조건이 있으면 그대로 유지해도 상관없어" → **BE write 데코 변경 불필요**. 협력사 매니저는 조회(`gst_or_admin_required`, company=='GST' OR admin)가 이미 막혀 SI 화면 진입 자체가 안 됨 → write 데코(`si_manager_or_admin_required`, v2.20.15)를 GST 한정으로 좁히지 않아도 실무 무해. **read 데코도 현행 유지**.

→ Sprint 80 권한 작업은 **FE 버튼 정합 1건으로 축소**:

**변경 (FE only)**:
- **FE** `si_finishing_screen.dart` L294 `_isGstSelf`(company=='GST', GST 전원 PI/QI/SI) → 출고완료 버튼 조건을 BE `si_manager_or_admin_required` **정확 미러**(`role=='SI' || isManager || isAdmin`)로 변경. L643/L664/L666. → GST PI/QI(비매니저)는 버튼 미노출(403 방지), GST manager·SI·admin은 노출.
- `gst_products_screen.dart` canShip(isAdmin||isManager||isSi)는 이미 BE 정확 미러 — 변경 0 (확인만).

**변경 없음 (현행 유지)**:
- BE `si_manager_or_admin_required` (v2.20.15) — 유지 (협력사 매니저는 read 막혀 무해)
- BE `gst_or_admin_required` read 데코 — 유지
- `test_ship_complete.py` PERM-03(협력사 manager 200) — 유지 (BE 무변경 → 회귀 없음)
- admin-complete(PI/QI 종료) manager/admin — 무관

→ **BE 권한 변경 0**이므로 권한 사유 Codex 라운드 2 불필요. FE 버튼 정합만 (flutter build 검증). Sprint 80 본체(주차 그룹핑 BE 집계)는 M-Q6/Q7/Q8 반영분만 라운드 2 재검증.

### A 반영 (권고 수용)
- **A-Q1**: grouped(no-q) 모드 탭 배지 — `_plannedShipments.length`(L309, 평면 200 cap) → `total` 또는 `by_week.count 합` 표시. **평면 items를 grouped 모드 UI 진실원천으로 쓰지 않음** 명문화.
- **A-Q3**: W53 placeholder 카드에 `미정` 라벨 병기 (실제 일정과 시각 구분).
- **Q4 권고**: `by_week[].date_from/date_to` = `date_trunc('week', ship_plan_date)::date` 기반 BE 산출 → FE ISO week 재계산 불필요.

### N (이견 없음)
- Q2 drill-down 불필요(모델 카운트만), Q4 BE nested + ISO 키, Q5 정렬 — 설계대로 확정.

## 8. 정책 정합

- CLAUDE.md 책임 분리 — OPS PWA = mutation(출고완료), 본 건은 조회 개선 (read-only 집계). OPS 화면 전용
- ② 자동 Codex 이관 체크리스트: API 응답 계약 변경(additive `by_week`) → 이관 대상 → 본 설계서 검증
- 200 cap 누락(문제 A)은 by_week 집계로 "전체 현황"은 해소. 평면 items cap은 Q1에서 결정
