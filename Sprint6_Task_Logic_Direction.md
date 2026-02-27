# Sprint 6 — Task Seed 로직 방향 정리

**작성일**: 2026-02-20
**상태**: 설계 확정 (구현 전)

---

## 1. 네이밍 규칙

| 기존 | 변경 | 사유 |
|------|------|------|
| MM | **MECH** | 기구 — 가독성 |
| EE | **ELEC** | 전장 — 가독성 |
| TMS | **TMS** | 유지 |

> role enum, task_category, 코드 전반에 mech/elec 적용

---

## 2. workers 테이블 확장

### 변경 사항
```sql
-- role enum 변경
CREATE TYPE role_enum AS ENUM ('MECH', 'ELEC', 'TM', 'PI', 'QI', 'SI', 'ADMIN');

-- company 컬럼 추가
ALTER TABLE workers ADD COLUMN company VARCHAR(50);
```

### company 목록 (7개)

| company | 공정 | role 조합 | DB 저장값 (확정) |
|---------|------|----------|-----------------|
| FNI | 기구 | MECH | mech_partner = 'FNI' |
| BAT | 기구 | MECH | mech_partner = 'BAT' |
| TMS | 기구+전장 | MECH 또는 ELEC | elec_partner = 'TMS' / module_outsourcing = 'TMS' |
| P&S | 전장 | ELEC | elec_partner = 'P&S' |
| C&A | 전장 | ELEC | elec_partner = 'C&A' |
| GST | 검사/관리 | PI, QI, SI, ADMIN | (사내 — partner 컬럼 해당 없음) |

> ✅ DB 실제 저장값 확인 완료 (2026-02-20 Staging DB 기준)
> mech_partner: FNI, BAT / elec_partner: TMS, C&A, P&S / module_outsourcing: TMS

### company ↔ role 유효 조합

```
FNI  → MECH만
BAT  → MECH만
TMS  → MECH 또는 ELEC (소속 같고 작업자 다름)
PNS  → ELEC만
CNA  → ELEC만
GST  → PI, QI, SI, ADMIN
```

### FE 회원가입 화면 변경
- company 선택 (드롭다운) → role 선택지 자동 필터링
- GST 선택 → PI/QI/SI 표시
- FNI/BAT 선택 → MECH만 표시
- TMS 선택 → MECH/ELEC 표시
- PNS/CNA 선택 → ELEC만 표시

---

## 3. 모델 분류 (model_config)

| model_prefix | has_docking | is_tms | tank_in_mech | 설명 |
|-------------|------------|--------|-------------|------|
| GAIA | TRUE | TRUE | FALSE | TMS(M) 탱크 별도 → MECH 도킹 |
| DRAGON | FALSE | FALSE | TRUE | 한 협력사가 탱크+MECH 일괄 |
| GALLANT | FALSE | FALSE | FALSE | 탱크/도킹 없음 |
| MITHAS | FALSE | FALSE | FALSE | 탱크/도킹 없음 |
| SDS | FALSE | FALSE | FALSE | 탱크/도킹 없음 |
| SWS | FALSE | FALSE | FALSE | 탱크/도킹 없음 |

### 예외 처리
- DRAGON 외에도 TMS(M)이 탱크+MECH 일괄하는 경우 있음
- model_config는 prefix 기반 **기본값**
- product_info 단위 override 가능하도록 설계

---

## 4. Task 정의 (간소화 — 총 14개)

### MECH (기구) — 7개

| # | task_id | task_name | phase | docking 모델 | non-docking | 비고 |
|---|---------|-----------|-------|-------------|-------------|------|
| 1 | WASTE_GAS_LINE_1 | Waste Gas LINE 1 | PRE_DOCKING | ✅ | ❌ | |
| 2 | UTIL_LINE_1 | Util LINE 1 | PRE_DOCKING | ✅ | ❌ | |
| 3 | TANK_DOCKING | Tank Docking | DOCKING | ✅ | ❌ | |
| 4 | WASTE_GAS_LINE_2 | Waste Gas LINE 2 | POST_DOCKING | ✅ | ❌ | |
| 5 | UTIL_LINE_2 | Util LINE 2 | POST_DOCKING | ✅ | ❌ | |
| 6 | HEATING_JACKET | Heating Jacket | PRE_DOCKING | ⚙️ | ⚙️ | admin 옵션 (default false) |
| 7 | SELF_INSPECTION | 자주검사 ⭐ | FINAL | ✅ | ✅ | |

**모델별 분기:**
- **GAIA** (has_docking): 1~5, 7 활성 + phase 구분 적용
- **DRAGON** (tank_in_mech): 1~5 활성 + TANK_DOCKING만 비활성 (순차 진행)
- **기타**: 자주검사만 활성, 1~5 비활성
- **HEATING_JACKET**: 모든 모델에서 `admin_settings.heating_jacket_enabled`로 제어 (현재 false, 기준 확정 후 model_config에 `has_heating_jacket` 추가하여 모델별 분기)

### ELEC (전장) — 6개

| # | task_id | task_name | phase |
|---|---------|-----------|-------|
| 1 | PANEL_WORK | 판넬 작업 | PRE_DOCKING |
| 2 | CABINET_PREP | 케비넷 준비 작업 | PRE_DOCKING |
| 3 | WIRING | 배선 포설 | PRE_DOCKING |
| 4 | IF_1 | I.F 1 | PRE_DOCKING |
| 5 | IF_2 | I.F 2 | POST_DOCKING |
| 6 | INSPECTION | 자주검사 (검수) ⭐ | FINAL |

**전 모델 공통**: 6개 전부 활성
- GAIA: I.F 1 후 도킹 완료 대기 → I.F 2
- 기타: I.F 1 → I.F 2 순차 (phase 무의미)

### TMS (모듈) — 2개 (GAIA 전용)

| # | task_id | task_name | task_group |
|---|---------|-----------|-----------|
| 1 | TANK_MODULE | Tank Module | Tank Module |
| 2 | PRESSURE_TEST | 가압검사 ⭐ | Tank Module |

**GAIA만 생성** (is_tms = TRUE)

### Task 수량 요약

| 공정 | Task 수 | 비고 |
|------|--------|------|
| MECH | 7 | Docking 분기 + Heating Jacket(admin 옵션) |
| ELEC | 6 | 전 모델 공통 |
| TMS | 2 | GAIA만 |
| **합계** | **15** | 기존 PDA 20개+ → 15개로 간소화 |

---

## 5. 알림 트리거

### MVP (Sprint 6)

```
TMS 가압검사 완료
  → alert_type: TMS_TANK_COMPLETE
  → 수신: 해당 제품의 MECH 관리자 (is_manager + role=MECH)
  → 대상: GAIA 모델만

MECH Tank Docking 완료
  → alert_type: TANK_DOCKING_COMPLETE
  → 수신: 해당 제품의 ELEC 관리자 (is_manager + role=ELEC)
  → 대상: GAIA 모델만
```

### 추후 (Admin 옵션 — default false)

```
PHASE_BLOCK
  → POST_DOCKING task 시작 시도 + 도킹 미완료 시 차단
  → admin_settings.phase_block_enabled = false

HEATING_JACKET
  → 모델 옵션별 Heating Jacket task 활성화/비활성화
  → admin_settings.heating_jacket_enabled = false
  → 기준 확정 후 model_config.has_heating_jacket으로 모델별 분기 전환
```

---

## 6. 데이터 흐름 (GAIA 기준)

```
[product_info]
  model = "GAIA-P DUAL"
  mech_partner = "FNI"        ← MECH 작업 협력사
  elec_partner = "PNS"        ← ELEC 작업 협력사
  module_outsourcing = "TMS"  ← TMS 모듈 협력사

[model_config 조회]
  prefix "GAIA" → has_docking=T, is_tms=T, tank_in_mech=F

[Task Seed 생성]
  MECH task 6개 (전부 활성)
  ELEC task 6개 (전부 활성)
  TMS task 2개 (GAIA이므로 생성)

[작업자 화면 — Task 필터링]
  worker.company = "FNI" + worker.role = "MECH"
    → product_info.mech_partner = "FNI"인 제품의 MECH task만 표시

  worker.company = "PNS" + worker.role = "ELEC"
    → product_info.elec_partner = "P&S"인 제품의 ELEC task만 표시

  worker.company = "TMS" + worker.role = "MECH"
    → product_info.module_outsourcing = "TMS"인 제품의 TMS task만 표시

[알림 흐름]
  TMS 가압검사 완료 → FNI 소속 MECH 관리자에게 알림
  FNI MECH Tank Docking 완료 → P&S 소속 ELEC 관리자에게 알림
```

---

## 7. Task Seed 초기화 로직

```python
def initialize_product_tasks(serial_number: str, qr_doc_id: str, model_name: str):
    config = get_model_config(model_name)

    # MECH Tasks (7개)
    for t in get_templates('MECH'):
        is_applicable = True
        if t.task_id == 'HEATING_JACKET':
            # admin 옵션으로 제어 (기준 미확정 → default false)
            is_applicable = get_admin_setting('heating_jacket_enabled', False)
        elif t.is_docking_required:
            if config['has_docking']:
                is_applicable = True           # GAIA: 전부 활성
            elif config['tank_in_mech']:
                # DRAGON: LINE 1/2 활성, DOCKING만 비활성
                is_applicable = (t.task_id != 'TANK_DOCKING')
            else:
                is_applicable = False          # 기타: 비활성
        create_task(serial_number, qr_doc_id, 'MECH', t, is_applicable)

    # ELEC Tasks (6개) — 전 모델 공통
    for t in get_templates('ELEC'):
        create_task(serial_number, qr_doc_id, 'ELEC', t, True)

    # TMS Tasks (2개) — GAIA만
    if config['is_tms']:
        for t in get_templates('TMS'):
            create_task(serial_number, qr_doc_id, 'TMS', t, True)
```

---

## 8. 확인 필요 사항 (구현 전 체크리스트)

| # | 항목 | 상태 |
|---|------|------|
| 1 | product_info의 mech_partner 실제 저장값 확인 | ✅ FNI, BAT |
| 2 | product_info의 elec_partner 실제 저장값 확인 | ✅ TMS, C&A, P&S |
| 3 | product_info의 module_outsourcing 실제 저장값 확인 | ✅ TMS |
| 4 | workers role enum 변경 (MM→MECH, EE→ELEC) migration 영향 범위 | ⏳ |
| 5 | 기존 Sprint 1~5 코드에서 MM/EE 하드코딩된 곳 전수 조사 | ⏳ |
| 6 | product_info에 docking_override 컬럼 MVP에 넣을지 추후로 미룰지 | ⏳ |
