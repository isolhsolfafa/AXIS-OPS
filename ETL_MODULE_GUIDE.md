# ETL Module Guide

## 개요
Teams Excel (SCR 생산현황) → Staging DB (PostgreSQL) 적재 + QR 이미지 생성 파이프라인

**모듈 경로**: `/Users/kdkyu311/dev/my_app/test_server/etl_pipeline/`

---

## 파이프라인 구조

```
[Step 1] Extract              [Step 2] Load                   [Step 3] QR Generate
Teams Excel (Graph API)  →  PostgreSQL Staging DB 적재    →  QR 이미지 (.png) 생성
SCR 일정관리_W*.xlsx         plan.product_info                {SN}_{DOC_SN}.png
                             public.qr_registry
```

| 파일 | 역할 |
|------|------|
| `etl_main.py` | 오케스트레이터 — CLI 인자로 실행 |
| `step1_extract.py` | Teams Excel에서 추출 (SCR-Schedule ExcelDataLoader 재사용) |
| `step2_load.py` | PostgreSQL 적재 (`plan.product_info` + `public.qr_registry`) |
| `step3_qr_generate.py` | QR 이미지 생성 (qrcode + PIL) |

---

## 실행 방법

```bash
cd /Users/kdkyu311/dev/my_app/test_server/etl_pipeline

# 특정 날짜
python3 etl_main.py --date 2026-01-05

# 날짜 범위
python3 etl_main.py --start 2026-01-01 --end 2026-01-10

# 전체 (필터 없음)
python3 etl_main.py --all

# 필터 기준 필드 변경 (기본값: mech_start)
python3 etl_main.py --start 2026-01-01 --end 2026-01-31 --field elec_start
```

---

## DB 스키마 (Staging DB)

**접속 정보**: Railway PostgreSQL (`maglev.proxy.rlwy.net:38813/railway`)

### plan.product_info (25 컬럼)

| 컬럼 | 타입 | Nullable | ETL INSERT | 비고 |
|------|------|----------|------------|------|
| id | integer | NO | - | auto-increment |
| serial_number | varchar | NO | O | S/N (UNIQUE) |
| model | varchar | NO | O | 모델명 |
| title_number | varchar | YES | O | YYMMDD/오더/SN |
| product_code | varchar | YES | O | 제품번호 |
| sales_order | varchar | YES | O | 판매오더 |
| customer | varchar | YES | O | 고객사 |
| line | varchar | YES | O | 라인 |
| quantity | varchar | YES | O | 수량 (default '1') |
| mech_partner | varchar | YES | O | 기구업체 |
| elec_partner | varchar | YES | O | 전장업체 |
| module_outsourcing | varchar | YES | O | 모듈외주 |
| prod_date | date | YES | O | 생산일 (= mech_start) |
| mech_start | date | YES | O | 기구시작 |
| mech_end | date | YES | O | 기구종료 |
| elec_start | date | YES | O | 전장시작 |
| elec_end | date | YES | O | 전장종료 |
| module_start | date | YES | O | 모듈시작 (TM) |
| location_qr_id | varchar | YES | - | 위치 QR (별도 관리) |
| created_at | timestamptz | YES | - | default CURRENT_TIMESTAMP |
| updated_at | timestamptz | YES | - | default CURRENT_TIMESTAMP |
| pi_start | date | YES | O | 가압검사 (PI) |
| qi_start | date | YES | O | 공정검사 (QI) |
| si_start | date | YES | O | 마무리검사 (SI) |
| ship_plan_date | date | YES | O | 출하계획일 |

### public.qr_registry (8 컬럼)

| 컬럼 | 타입 | Nullable | ETL INSERT | 비고 |
|------|------|----------|------------|------|
| id | integer | NO | - | auto-increment |
| qr_doc_id | varchar | NO | O | DOC_{S/N} |
| serial_number | varchar | NO | O | S/N |
| status | varchar | YES | O | 'active' (default) |
| issued_at | timestamptz | YES | - | default CURRENT_TIMESTAMP |
| revoked_at | timestamptz | YES | - | NULL |
| created_at | timestamptz | YES | - | default CURRENT_TIMESTAMP |
| updated_at | timestamptz | YES | - | default CURRENT_TIMESTAMP |

---

## 컬럼 매핑 (Excel → ETL → DB)

### 기본 매핑 (ExcelDataLoader 17개 컬럼)

| Excel 한글 | ETL 필드 | DB 컬럼 |
|-----------|---------|---------|
| S/N | serial_number | serial_number |
| 모델 | model_name | model |
| 오더번호 | order_no | sales_order |
| 고객사 | customer | customer |
| 제품번호 | product_code | product_code |
| 라인 | line | line |
| 기구업체 | mech_partner | mech_partner |
| 전장업체 | elec_partner | elec_partner |
| 기구시작 | mech_start | mech_start, prod_date |
| 기구종료 | mech_end | mech_end |
| 전장시작 | elec_start | elec_start |
| 전장종료 | elec_end | elec_end |
| 가압시작 | pressure_test | pi_start |
| 자주검사 | self_inspect | (미사용) |
| 공정시작 | process_inspect | qi_start |
| 마무리시작 | finishing_start | si_start |
| 출하 | planned_finish | ship_plan_date |

### 추가 매핑 (raw DataFrame iloc 직접 접근)

| Excel 위치 | ETL 필드 | DB 컬럼 | 비고 |
|-----------|---------|---------|------|
| AO열 (index 41) | module_outsourcing | module_outsourcing | 모듈외주 |
| AP열 (index 42) | semi_product_start | module_start | 모듈계획시작일 (TM) |

### 자동 생성 필드

| ETL 필드 | 생성 로직 | DB 컬럼 |
|---------|---------|---------|
| title_number | `YYMMDD/판매오더/SN번호` | title_number |
| quantity | 고정값 `'1'` | quantity |
| qr_doc_id | `DOC_{serial_number}` | qr_doc_id (qr_registry) |

---

## 의존성

| 모듈 | 역할 | 경로 |
|------|------|------|
| SCR-Schedule ExcelDataLoader | Teams Excel 로드 (Graph API) | `/Users/kdkyu311/Desktop/GST/SCR-Schedule` |
| SCR-Schedule sn_parser | S/N 범위 파싱 (예: 6528~6530 → 3건) | SCR-Schedule/src/utils/sn_parser.py |
| SCR-Schedule load_env_teams | Teams Graph API 환경변수 로드 | SCR-Schedule/main.py |
| psycopg2 | PostgreSQL 접속 | pip install |
| qrcode + PIL | QR 이미지 생성 | pip install qrcode[pil] |

---

## ETL 실행 이력

### 2026-02-21: mech_start 2026-01-01 ~ 2026-01-10

**실행 커맨드**:
```bash
python3 etl_main.py --start 2026-01-01 --end 2026-01-10 --field mech_start
```

**소스 파일**: `SCR 일정관리_W8(0219).xlsx` (W8 주차)

**결과**:
| 항목 | 수량 |
|------|------|
| 전체 추출 | 590건 |
| 필터 적용 | 45건 |
| 신규 적재 | 45건 |
| 중복 스킵 | 0건 |
| QR 생성 | 45건 |

**적재 상세** (plan.product_info ID 871~915, qr_registry ID 871~915):

| S/N | qr_doc_id | 모델 |
|-----|-----------|------|
| GBWS-6528 | DOC_GBWS-6528 | GAIA-I DUAL |
| GBWS-6529 | DOC_GBWS-6529 | GAIA-I DUAL |
| GBWS-6483 | DOC_GBWS-6483 | GAIA-I DUAL |
| DBW-3715 ~ 3722 | DOC_DBW-3715 ~ 3722 | DRAGON LE (8건) |
| GBWS-6530 | DOC_GBWS-6530 | GAIA-I DUAL |
| GBWS-6551 ~ 6553 | DOC_GBWS-6551 ~ 6553 | GAIA-I DUAL (3건) |
| GBWS-6536 ~ 6537 | DOC_GBWS-6536 ~ 6537 | GAIA-I DUAL (2건) |
| GBWS-6532 | DOC_GBWS-6532 | GAIA-I DUAL |
| GBWS-6527 | DOC_GBWS-6527 | GAIA-I DUAL |
| GBWS-6533 ~ 6535 | DOC_GBWS-6533 ~ 6535 | GAIA-I DUAL (3건) |
| GPWS-0664 | DOC_GPWS-0664 | GAIA-P DUAL |
| GBWS-6531 | DOC_GBWS-6531 | GAIA-I DUAL |
| GBWS-6538 ~ 6539 | DOC_GBWS-6538 ~ 6539 | GAIA-I DUAL (2건) |
| GPWS-0658 ~ 0663 | DOC_GPWS-0658 ~ 0663 | GAIA-P (6건) |
| WS-0139 ~ 0140 | DOC_WS-0139 ~ 0140 | SWS-I (2건) |
| DBW-3725 ~ 3726 | DOC_DBW-3725 ~ 3726 | DRAGON LE DUAL (2건) |
| GBWS-6554 ~ 6559 | DOC_GBWS-6554 ~ 6559 | GAIA-I DUAL (6건) |
| GBWS-6547 ~ 6549 | DOC_GBWS-6547 ~ 6549 | GAIA-I DUAL (3건) |

**모델별 분포**:
| 모델 | 건수 |
|------|------|
| GAIA-I DUAL | 27 |
| DRAGON LE | 8 |
| GAIA-P | 6 |
| GAIA-P DUAL | 1 |
| SWS-I | 2 |
| DRAGON LE DUAL | 1 |

**QR 이미지 경로**: `/Users/kdkyu311/dev/my_app/test_server/output/qr_labels/`

---

## 스키마 검증 결과 (2026-02-21 확인)

### 1. Load 경로 검증

| 대상 | ETL 코드 경로 | 실제 DB 스키마 | 결과 |
|------|-------------|-------------|------|
| 제품 메타데이터 | `INSERT INTO plan.product_info` | `plan` 스키마 존재 | 일치 |
| QR 매핑 | `INSERT INTO public.qr_registry` | `public` 스키마 존재 | 일치 |
| 중복 체크 | `SELECT FROM public.qr_registry` | `public` 스키마 존재 | 일치 |

### 2. 컬럼 일치 검증

**plan.product_info**: ETL INSERT 21개 컬럼 vs DB 25개 컬럼
- 21개 INSERT 컬럼: 전부 일치
- 4개 미INSERT 컬럼: `id` (auto), `location_qr_id` (nullable), `created_at` (default), `updated_at` (default)
- 결과: **완전 일치**

**public.qr_registry**: ETL INSERT 3개 컬럼 vs DB 8개 컬럼
- 3개 INSERT 컬럼 (`qr_doc_id`, `serial_number`, `status`): 전부 일치
- 5개 미INSERT 컬럼: 모두 auto/default/nullable
- 결과: **완전 일치**

### 3. 주의사항

- **collation version mismatch** 경고 발생 (2.36 vs 2.41) — 기능상 문제 없으나 향후 `ALTER DATABASE railway REFRESH COLLATION VERSION` 권장
- **openpyxl Data Validation 경고** — Excel Data Validation extension 미지원 경고, 데이터 추출에 영향 없음
- **SCR-Schedule config.py 수정 금지** — Production 대시보드에서 사용 중이므로, 추가 컬럼은 raw DataFrame iloc으로 접근

---

## 출력 파일

| 파일 | 경로 | 설명 |
|------|------|------|
| ETL 결과 JSON | `/Users/kdkyu311/dev/my_app/test_server/output/etl_result.json` | 적재 결과 요약 |
| QR 이미지 | `/Users/kdkyu311/dev/my_app/test_server/output/qr_labels/*.png` | QR 코드 이미지 (로컬 전용, 라벨프린터 출력) |

---

## GitHub Actions 자동화 (2026-03-07)

### 변경 사항
- **QR 이미지**: 라벨프린터로 현장에서 직접 출력 → R2 클라우드 저장 불필요
- **CI 실행 범위**: Step 1 (Extract) + Step 2 (Load)만 실행, Step 3 (QR Generate) 제외
- **의존성 정리**: SCR-Schedule 모듈을 `lib/`로 복사하여 독립 실행 가능하게 변경

### CI/CD 리포 구조

```
etl-pipeline/ (독립 리포)
├── .github/workflows/etl-production.yml
├── etl_main.py
├── step1_extract.py
├── step2_load.py
├── step3_qr_generate.py  ← CI에서 미실행 (로컬 전용)
├── lib/
│   ├── teams_auth.py      ← SCR-Schedule/src/shared/teams_auth.py 복사
│   ├── excel_loader.py    ← SCR-Schedule/src/data_loader/excel_loader.py 경량화
│   └── sn_parser.py       ← SCR-Schedule/src/utils/sn_parser.py 복사
├── requirements.txt
└── README.md
```

### Cron 스케줄
- **매일 08:00 KST (월~금)**: `cron: '0 23 * * 0-4'` (UTC)
- **수동 실행**: `workflow_dispatch` (date-range 모드 지원)

### Secrets 목록
| Secret | 출처 |
|--------|------|
| `DATABASE_URL` | Railway 대시보드 |
| `TEAMS_CLIENT_ID` / `TEAMS_CLIENT_SECRET` / `TEAMS_TENANT_ID` | Azure AD 앱 등록 |
| `TEAMS_SITE_ID` / `TEAMS_DRIVE_ID` | SCR-Schedule `.env` 파일 |
| `SLACK_WEBHOOK_URL` | Slack App 설정 |
