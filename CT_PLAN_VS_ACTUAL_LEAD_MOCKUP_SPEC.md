# 계획 vs 실적 Lead 분석 — VIEW Mockup Spec

> 작성 2026-06-08 (OPS 쿼리 검증 기반). VIEW 분석 페이지 mockup 설계용.
> **목적**: 최초계획(납기) ↔ 실제출하 ↔ 공정별 실행 lead 를 한 화면에서.
> ⚠️ 모든 수치는 **2026-05 이후 / TEST 제외 / 정상완료(duration_source IS NULL)** 기준 운영 실측값.

---

## 🚨 설계 핵심 규칙 (mockup 전에 반드시 반영)

### 규칙 1 — 계획일 데이터 소스는 `etl.change_log` (현재 ship_plan 금지)
- `plan.product_info.ship_plan_date` 는 **출하 시 actual_ship_date 로 덮어써짐** → 납기가 항상 +0일(self-fulfilling). **쓰면 안 됨.**
- **진짜 최초 계획** = `etl.change_log` `field_name='ship_plan_date'` 의 **가장 오래된 `old_value`** (덮어쓰기 전 frozen).
- 즉 "계획 대비 실적"의 계획축 = change_log baseline. (현재 ship_plan = 실제출하 미러일 뿐.)
- ✅ **baseline 무결성 검증됨 (Codex M5 반박 데이터)**: first old_value = actual_ship 인 케이스 **0/106건** → old_value 는 실제출하와 절대 일치 안 함 = self-fulfilling 오염 없는 깨끗한 계획값 (지연 73 / 조기 33 분포 정상).
- ⚠️ **좌측절단 주의 (Codex M1)**: change_log 기록 시작 = **2026-03-11**. 그 이전 생성 제품은 first old_value 가 "기록 시작 시점 값"이라 진짜 최초계획 아닐 수 있음 → **첫 기록일이 제품 생성 직후인 제품만 신뢰**, 또는 "baseline 추정" 플래그. 블록1 라벨 = "first observed plan" (최초 관측 계획).

### 규칙 2 — 판넬작업(PANEL_WORK)은 협력사 본사 off-site 태깅 (Codex M2 정정)
- PANEL_WORK 은 **GST 본사가 아니라 협력사 본사에서 작업·체크**하는 데이터.
- ⚠️ **정정**: 앱이 판넬을 "못 보는" 게 아니라 **협력사가 원격으로 태깅함** (실측: PANEL n=147, elapsed 중앙 32.5h = 실제 off-site 작업시간 잡힘).
- 단 **위치가 off-site**라 의미가 다름: 판넬 started_at 은 elec_start 보다 중앙 **+11일 늦음** → 계획 elec_start 는 판넬 실제 시작 anchor 아님.
- lead 분해 시 판넬 = **"태깅된 off-site 세그먼트"**로 표기 (앱 사각지대 아님, 위치만 협력사). in-house GST 작업과 색/패턴 구분.
- "in-house lead 20.6일" 명칭 금지 → **"앱 관측 lead(off-site 판넬 포함)"** 로 정확히 표기.

### 규칙 3 — 추적율(태깅 정착) 게이트
- 제품/공정마다 추적율 다름: ELEC 88~97%(신뢰), MECH 47~56%(provisional).
- 신뢰도 뱃지 필수: 추적율<50% 셀은 "참고용" 회색 처리.

### 규칙 4 — 가동률 분모는 `work_site='GST'`(공장 출근)만 (2026-06-08 사용자 catch)
- `hr.partner_attendance.work_site` = `GST`(공장 4404) / `HQ`(협력사 본사=판넬 1252) 구분 존재 (+ `product_line` 컬럼).
- **가동률(M/H ÷ 출근시간)의 분모 = `work_site='GST'`만**. HQ(판넬 off-site)는 제외 — 안 그러면 ELEC 가동률 과소(15~20%→실제 30~44%).
- 출근시간 = worker별 일별 (MAX out − MIN in), GREATEST(0) 가드.
- ⚠️ 출근시간은 3분해: ①태깅 생산(측정) ②미태깅 생산(adoption gap) ③비생산(자재/재작업/이동/딴일). ②③은 현재 분리 불가 → 활동코드 태깅(4종) 필요. **"낮은 가동률 = 낮은 생산성"으로 해석 금지**(분모 정의 차이).
- 실측 공장 가동률(5월+): P&S(ELEC) 30~44% / C&A 22~41% / FNI(MECH) 12~16%(태깅 절반이라 과소).

---

## 📐 섹션 구성 (4 블록)

### 블록 1 — 납기 준수 (Delivery Performance) ⭐ 핵심
> 데이터소스: etl.change_log 최초계획 vs actual_ship_date

**KPI 카드 3개**
- 최초계획 대비 실제출하 **중앙 +4.0일 (지연)**
- 지연 **73대** / 조기 **33대** / 정시 **0대** (총 106대, 5월+ 출하)
- 평균 지연폭(지연 건만) / 최대 지연 (+42일, 6900번대)

**위젯**
- 히스토그램: 납기 delta 분포 (x축 -10~+45일, 0 기준선)
- **모델 그룹별 층화 (Codex M4 — 중앙값 단일 호도 방지)**: WS(SWS) +16.5일 / GBWS +3.5일 / GPWS +2.0일 → 그룹별 p50/p75 병기 필수
- 제품 테이블: `S/N | model | 최초계획일 | 현재계획(=실제) | 실제출하 | 납기Δ | (지연사유 추후)`
  - 예: `GBWS-6919 | GAIA-I DUAL | 2026-04-21 | 2026-06-02 | 2026-06-02 | +42`
- 정렬/필터: 납기Δ desc, 모델별, 고객사별

### 블록 2 — 공정별 실행 Lead (계획 창 vs 실제 실행)
> 실제 = MAX(완료)−MIN(시작) 앱 태깅 / 계획 = {proc}_start ~ {proc}_end

| 공정 | 실제 span 중앙 | 계획 span 중앙 | 실제/계획 | 표본 | 신뢰도 |
|---|---|---|---|---|---|
| MECH | 7.9일 | 10.0일 | 79% | 12대 | provisional |
| ELEC | 10.3일 | 26.0일 | 40% | 53대 | 신뢰(판넬 off-site 포함 주석) |

**위젯**
- 공정별 가로 막대: 계획(연한) vs 실제(진한) 오버레이
- ELEC 막대에 "계획 26일 중 판넬 off-site ~20일 포함" 주석 칩
- 표본 수 + 신뢰도 뱃지

### 블록 3 — 제품 단위 Lead 분해 (전장외부~출하)
> 워터폴/간트 형태. 판넬 off-site 세그먼트 분리 표시

```
계획 lead (elec_start ~ ship)         = 35일
 ├─ 판넬 off-site (협력사 본사) ~20일   ← 앱 사각지대 (규칙 2)
 └─ in-house 실행 ~15일
앱태깅 lead (앱 첫시작 ~ 출하)         = 20.6일  ← in-house only
```

**위젯**
- 간트 1줄/제품: [판넬 off-site(회색 빗금)] → [MECH] → [ELEC in-house] → [PI/QI/SI] → 출하
- 계획 막대 vs 실제 막대 2단
- 판넬 구간 = "off-site, 앱 미추적" 빗금 패턴 + 툴팁

### 블록 3.5 — 설비 흐름 지연 지도 (Codex 최우선 추천 — M/H 불완전해도 robust)
> S/N 단위로 "어디서 시간이 새는가". timestamp 기반이라 태깅 갭에 강함.

**위젯**
- S/N별 워터폴/간트: `최초계획 →[착수 지연]→ 실제 착수 →[실행 span: 작업+대기]→ 마지막 완료 →[출하 전 대기]→ 실제출하`
- 단계별 일수 분해 + % 노출 → 병목 단계 식별
- 협력사 × 모델 × dual 층화 (Simpson's paradox 방지)
- active vs CT 벌어짐 = 병렬효과(M/H↑ CT↓) vs 릴레이 지연(CT↑) 분리

### 블록 3.6 — 협력사 주간 가동률 / WIP (M/M 공수)
> work_start_log + attendance(work_site=GST). 규칙 4 적용.

**위젯**
- 협력사 × 주: 동시설비수 / 투입작업자 / M/H / 가동률 (두 분모 병기: 공장출근 vs 태깅인원)
- 태깅 참여율 곡선 (출근 대비 태깅 인원) — 교육 추적 KPI
- ⚠️ 베타 (태깅 참여율 70%+ 전까지 "참고")

### 블록 5 — 미출하 Backlog & 계획 변경 추적 ⭐ (2026-06-09 추가, change_log 기반 = 지금 신뢰)
> 핵심 발견: backlog는 단일 숫자가 아니라 **3층 구조**. 적체의 본질 = 생산 캐파가 아니라 **고객/수주 재계획**. timestamp 로그(etl.change_log)로 "누가·언제·왜 안 나갔나" 전부 재구성 가능.

**5-1. Backlog 분류 스택 (현재 스냅샷, 일관 모집단=2026 생산일정 미출하)**
```
미출하 561대 (2026 생산일정 1244대 중 45%)   ← 합산 검증 561=301+230+7+22+1 ✓
├─ 301대  정상 WIP (미래계획 + ship_plan 변경 이력 없음)      ← 초록
├─ 230대  계획 push-out (미래계획이나 최초보다 뒤로 밀림, 중앙 192일) ← 노랑 (142대가 2026-12-31)
├─  22대  계획 변경됐으나 안 밀림(당김/동일)                   ← 회색
├─   7대  hard overdue (현재도 계획 지남)                     ← 빨강 (3월계획 5대 92일 = 즉시 조치)
└─   1대  계획일 없음(미정)                                   ← 회색
```
- ⚠️ "완성 미출하 2대"(앱 si_completed 플래그)는 **출하 태깅 5월말 시작이라 오류**. backlog 분모 = `actual_ship_date`(ETL, 2025-11+ 신뢰).
- ⚠️ **좌측절단(Codex M1)**: change_log 기록 시작 3-11 → 3-11 이전 밀린 제품은 "변경없음=정상 301"에 오분류 가능. "정상 301"은 **상한**, 실제 정상은 더 적을 수 있음.

**5-2. 고객사별 Backlog 매트릭스**
| 고객사 | 전체 | 출하 | 미출하 | 12-31 push | 12-31 비율 |
|---|---|---|---|---|---|
| MICRON | 573 | 291 | 282 | **87 (절대 최대)** | 31% |
| SEC | 304 | 152 | 152 | 21 | 14% |
| SK-HYNIX | 117 | 79 | 38 | 33 | **87% (비율 최대)** |
| SAS | 87 | 50 | 37 | 0 | 0% |
- ⚠️ **절대수 vs 비율 분리(Codex A4)**: 운영 우선순위 = **절대 push 수** = MICRON 87 > SK-HYNIX 33. "SK-HYNIX 87%"는 분모(38) 작아 불안정 → 앵커링 주의. 비율은 보조 지표.
- 위젯: 고객사 × [출하/정상WIP/push/overdue] 스택 바 (절대수). 비율은 툴팁.
- 출하 비율 도넛: MICRON 43% / SEC 22% / SK-HYNIX 11% (상위 3사 76% 집중).

**5-3. ISO Week 시계열 — 출하 vs 계획변경 churn**
```
주    출하  계획밀림  당김
W11    71    122★    43   ← change_log 기록 시작(3-11), 초기 일괄 (할인 표기)
W20    49     78     11
W23    20     47     21
W24     0     42      6
```
- 위젯: 주별 stacked bar (출하) + line (push-out/pull-in).
- ⚠️ **좌측절단(Codex M5)**: W11 이전(3-11 전) push-out 전부 미관측 → 시계열 초반 과소. **"상시 ~40/주" 단정 금지** → "최근(W20~24) 40+건/주 높은 수준 유지"로 한정. W11 spike(122)=기록 시작 일괄, 회색 처리.

**5-4. 고객사 × ISO Week 히트맵 ⭐ — "언제 누가 보류했나"**
```
주        MICRON  SEC  SK-HYNIX  SAS
W13~17      ~8    ~5   10~17(★)   ─   ← SK-HYNIX 보류 wave (3월말~4월 집중)
W16          10    0     10      34   ← SAS 일회성 spike
W20~21     58/34   ─     ~5       ─   ← MICRON 반복 wave
W23~24     21/9  20/33   ─        ─   ← SEC 최근 증가 (watch!)
```
- 위젯: 고객사 × 주 히트맵(셀 = push-out 건수). **클러스터 = 고객 결정 이벤트**.
- 인사이트 칩: "SK-HYNIX 보류는 W13-17 집중 = 고객 일정 결정" / "SEC W23-24 신규 밀림 = 최근 발생, 대응 가능".

> **📌 블록 5 핵심 인사이트 (mockup 메인 메시지) — Codex M3/M7 정정**: backlog에 **대규모 재계획 성분(push-out 230, 중앙 192일)이 관측됨**. push-out이 고객사별·시기별로 클러스터링(SK-HYNIX W13-17, SAS W16, MICRON 반복).
> ⚠️ **단 "적체=캐파 아니라 고객 재계획" 단정 금지**: §17은 동시에 **캐파 과부하(P&S 154%, FNI 134% 등 정규 초과 25~35%)**를 문서화. 클러스터링만으로 "캐파 아님"은 **역인과(캐파 부족→납기 못 맞춤→고객이 일정 미룸) 미배제 = 상관≠인과 트랩**. 캐파 병목은 최대 고객(MICRON)에서 먼저 표면화되므로 클러스터링과 양립.
> → **방어 가능한 결론**: "재계획 성분 大 관측 + 캐파 과부하 동시 존재. 인과(고객 사유 vs 캐파 유발)는 push-out **원인 코드**로 별도 검증 후 레버 결정." **"증설" 및 "증설 불요" 둘 다 단정 금지.**

> **🎯 가장 가치 큰 미실행 분석 (Codex M6)**: **push-out 원인 분리** (고객 요청 / 캐파 미스 / 자재 / 설계·재작업). §17이 "원인 불확실 → 미추적"이라 했는데 메인 결론이 바로 그 원인 귀속에 의존 = 모순. 원인 코드 없이는 캐파투자/고객협상/생산회복 중 레버 결정 불가. → push-out 시 사유 입력(활동코드처럼) 또는 판생회의 회의록 매핑이 다음 1순위.

### 블록 4 — 데이터 신뢰도 / 커버리지 (생존편향 방어)
> 모든 lead 수치의 신뢰 한계 명시

**위젯**
- 공정별 추적율 막대: MECH 9~56% / ELEC 88~97% / PI 18% / QI 4% / SI 8%
- "잘 잡힌 제품(추적율≥80%)" 비율 게이지
- 경고 배너: "현재 태깅 추적율이 낮은 공정은 lead 가 과소 추정됩니다. 추적율 80%+ 도달 시 전수 신뢰."
- 미추적 = 0초 탭(시작=완료) 비율 표기

---

## 🔌 BE API 필요 (추후 OPS 구현 — read-only)

| endpoint | 내용 | 데이터소스 |
|---|---|---|
| `GET /api/ct/delivery-performance` | 납기 delta 분포 + late/early/ontime + 제품 테이블 | **etl.change_log** 최초 ship_plan vs actual_ship |
| `GET /api/ct/process-lead?category=` | 공정별 실제 span vs 계획 span + 표본/신뢰도 | app 태깅 vs plan {proc}_start/end |
| `GET /api/ct/product-lead-breakdown?sn=` | 제품 1대 공정별 계획/실제 간트 데이터 + 판넬 off-site 플래그 | plan + app + change_log |
| `GET /api/ct/backlog-summary` | 미출하 3층(정상WIP/숨은지연/overdue) + 고객사별 매트릭스 | plan(actual_ship/ship_plan) + change_log(first_plan) |
| `GET /api/ct/plan-change-timeline?by=customer` | ISO week 출하 vs push-out/pull-in (고객사 층화) | change_log(changed_at) + plan(actual_ship) |

- 권한: `@jwt_required + @gst_or_admin_required` (CT 페이지 기존 정합)
- 모든 응답 meta: `as_of`, `window{from,to}`, `tracking_coverage`, `confidence`, `panel_offsite_note`, `changelog_start='2026-03-11'`(좌측절단 표기)

---

## ⚠️ Mockup 단계 주의 (데이터 성숙 전)
- 블록 1(납기) + **블록 5(backlog/계획변경)** = change_log 기반이라 **지금도 신뢰 가능** → 우선 구현 가치 최상 (태깅 무관).
- 블록 2~3(공정 lead) = MECH 표본 12대 등 provisional → mockup 은 "참고/베타" 라벨.
- 블록 4 = 항상 노출 (신뢰 한계 투명성).
- 태깅 추적율 80%+ 도달 시 블록 2~3 자동 신뢰권 (인프라 재작업 0).
- ⚠️ 블록 5 좌측절단: change_log 기록 시작 2026-03-11 → 이전 push-out 미관측. 12-31 = 보류 placeholder(생산지연 아님, 판생회의 대조 필요).

---

## 검증 trail (이 spec 의 모든 수치 출처)
- 2026-06-08 OPS staging 쿼리 (5월+, TEST 제외, 정상완료):
  - 납기: 최초계획 vs actual = +4일 중앙 (지연 73/조기 33/정시 0, n=106)
  - MECH lead: 실제 7.9 vs 계획 10일 (n=12, trk≥4)
  - ELEC lead: 실제 10.3 vs 계획 26일 (n=53, trk≥4)
  - 제품 lead: 계획 35일 / 앱태깅 20.6일 (판넬 off-site 차이)
  - 추적율: ELEC 88~97% / MECH 9~56% (0초 탭 = 미추적)
- 2026-06-09 backlog/계획변경 (블록 5, Codex M=6/A=1 정정 후):
  - 미출하 561 = 정상WIP 301 + push-out 230(중앙 192일) + overdue 7 + 기타변경 22 + 미정 1 (합산 561 ✓)
  - 12-31 push = 142대(전체), MICRON 87 절대최대 / SK-HYNIX 33(미출하38의 87% 비율최대, 분모작아 불안정)
  - push-out 최근(W20~24) 40+/주 (좌측절단 3-11이라 "상시" 단정 금지). 클러스터: SK-HYNIX W13-17 / SAS W16 / MICRON 반복 / SEC W23-24 신규
  - **12-31 = 추정 보류/TBD**(연말 일괄납기 계약 가능성 배제 불가, 판생회의 대조 필수). **"적체=캐파 아니라 고객" 단정 철회** — §17 캐파 과부하(154%)와 양립, 역인과 미배제, 원인코드로 별도 검증
- 상세 전체 분석: `CT_LEAD_CAPACITY_ANALYSIS_2026-06-08.md` §17
- 관련: `CT_S1_BASIS_ACTIVE_DESIGN.md`, memory `ct-trust-cutoff`, `duration-data-reliability`
