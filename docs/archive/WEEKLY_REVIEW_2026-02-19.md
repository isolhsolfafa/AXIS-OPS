# AXIS-OPS 주간 리뷰 (2026-02-19)

> 범위: 2026-02-16 (일) ~ 02-19 (수)

---

## 1. 이번 주 주요 의사결정

### 1.1 Clean Cut 전략 확정 (02/16)
- 하이브리드(PDA+App 동시 운영) 폐기 → App MVP 별도 개발 후 일괄 전환
- 워킹타임 계산 200줄 로직 → `duration = completed_at - started_at` 10줄로 단순화
- QR 호환 불필요 (PDA google_doc_id ↔ App qr_doc_id 별개 운영)
- APP_PLAN v4.0 작성 완료 (전략/워크플로우/API/DB/변수관리)

### 1.2 3-Tier 스키마 아키텍처 재설계 (02/19)
- `product_info`를 `plan` 스키마로 이동 (생산관리 데이터 ≠ App 운영 데이터)
- `qr_registry` 테이블 신설 (QR ↔ 제품 매핑 브릿지, status: active/revoked/reissued)
- FK 체인 정립: `app_task_details → qr_registry → plan.product_info`
- DB 타임존 `Asia/Seoul` 설정
- 컬럼명을 ETL 실무 기준으로 간소화:
  - `production_date` → `prod_date`
  - `manufacturing_start/end` → `mech_start/mech_end`
  - `test_start/test_end` → 삭제 (역할 기반으로 재정의)
  - `semi_product_start` → `module_start`
  - 신규: `pi_start`, `qi_start`, `si_start`, `ship_plan_date`

### 1.3 PDA 테이블 정리 (02/19)
- PDA 전용 테이블 11개 삭제 실행 완료 (Staging DB)
  - worksheet, task_summary, progress_summary, progress_snapshots
  - stats, partner_stats, additional_info, ot_details
  - treemap_data, processing_log, processed_files
- Staging DB: 25개 → **14개 테이블** (plan 1 + public 13)

### 1.4 QR 스캔 인증 버그 수정 (02/19)
- TaskService/AlertService가 자체 ApiService 인스턴스 생성 → JWT 토큰 미포함
- Riverpod `apiServiceProvider` 싱글턴으로 통합하여 해결

---

## 2. 코드 변경 사항 (30+ files modified)

### Backend (8 files)
| 파일 | 변경 내용 |
|------|----------|
| `migrations/002_create_product_info.sql` | `plan` 스키마 + `plan.product_info` + `public.qr_registry` 분리, 트리거/인덱스 |
| `models/product_info.py` | `qr_registry JOIN plan.product_info` 쿼리 구조 전환, `_BASE_JOIN_QUERY` 상수 |
| `routes/product.py` | `prod_date` API 응답 변경, null safety 추가 |
| `routes/work.py` | 동일 변경 |
| `services/auth_service.py` | `VALID_ROLES`에 `ADMIN` 추가, login 응답에 `email_verified` 포함 |
| `run.py` | `allow_unsafe_werkzeug=True` (dev SocketIO 호환) |

### Frontend (20 files)
| 카테고리 | 변경 내용 |
|---------|----------|
| models | `product_info.dart`: `prodDate` 전환, `isTmsModule` getter |
| models | `worker.dart`: 수정 |
| services | `auth_service.dart`, `local_db_service.dart` 수정 |
| providers | `auth_provider.dart`: **apiServiceProvider 싱글턴 추가** (QR 인증 버그 해결) |
| providers | `task_provider.dart`, `alert_provider.dart`: 공유 apiServiceProvider 사용 |
| screens | 로그인/회원가입/인증/QR/Task/관리자 화면 전체 수정 |
| widgets | `task_card`, `completion_badge`, `process_alert_popup` 수정 |
| 신규 | `splash_screen.dart`, `design_system.dart` (GxColors) 추가 |
| config | `pubspec.yaml`에 `assets/images/` 경로 추가 |

### ETL (별도 경로)
| 파일 | 변경 내용 |
|------|----------|
| `step2_load.py` | `plan.product_info` + `public.qr_registry` 2-table insert 패턴으로 전환 |

### 문서 (4 files)
| 파일 | 변경 내용 |
|------|----------|
| `APP_PLAN_v4(26.02.16).md` | v4.3: 3-Tier 스키마 아키텍처, ETL 컬럼 매핑, qr_registry 반영 |
| `db_schema_cleanup.sql` | plan 스키마 반영, FK 체인 문서화, PDA 삭제 스크립트 갱신 |
| `CLAUDE.md` | Sprint 5~7 계획, Admin 정책, Task Seed 데이터 추가 |
| `AGENT_TEAM_LAUNCH.md` | Sprint 5/6/7 팀에이전트 프롬프트 작성 |

---

## 3. 스키마 점검 결과 요약

### 현재 확정된 스키마 구조 (Staging DB — 14 테이블)
```
plan 스키마 (생산관리 — ETL 적재)
  └── product_info: serial_number, model, prod_date, 일정 9개, 협력사 3개, location_qr_id...

public 스키마 (App 운영)
  ├── qr_registry: qr_doc_id(UNIQUE) ↔ serial_number(UNIQUE) 매핑, status
  ├── workers (11컬럼)
  ├── email_verification (6컬럼)
  ├── app_task_details (14컬럼) — FK→qr_registry.qr_doc_id
  ├── completion_status (11컬럼) — FK→qr_registry.serial_number
  ├── app_alert_logs (11컬럼)
  ├── work_start_log (9컬럼)
  ├── work_completion_log (10컬럼)
  ├── location_history (6컬럼)
  ├── offline_sync_queue (9컬럼)
  ├── product_bom (Phase 2)
  ├── bom_checklist_log (Phase 2)
  └── documents (PDA 참조용 유지)

defect 스키마 (추후 — 불량 분석)
```

### FK 체인
```
app_task_details.qr_doc_id      → qr_registry.qr_doc_id
completion_status.serial_number → qr_registry.serial_number
qr_registry.serial_number      → plan.product_info.serial_number
```

### Sprint 5 진입 전 잔여 이슈

| # | 이슈 | 심각도 | 상태 |
|---|------|--------|------|
| 1 | `003_create_task_tables.sql` FK가 구 `product_info(qr_doc_id)` 참조 → `qr_registry` 변경 필요 | 🔴 | 미수정 (migration SQL만, 실제 DB FK는 정상) |
| 2 | `app_alert_logs`에 `read_at` 컬럼 + `updated_at` 트리거 누락 | 🟡 | 미수정 |
| 3 | CLAUDE.md "DB 스키마 구조" 섹션이 구버전 (plan 스키마/qr_registry 미반영) | 🟡 | **수정 필요** |
| 4 | AGENT_TEAM_LAUNCH.md Sprint 5 프롬프트가 구 컬럼명 기준 | 🟡 | **수정 필요** |
| 5 | Task seed 미구현 (MM 19 + EE 8 = 27개 Task 정의가 코드에 없음) | 🟡 | Sprint 6 예정 |

---

## 4. Sprint 현황

```
Sprint 1 (인증 + DB):      ✅ 완료  8/8 tests
Sprint 2 (Task 핵심):      ✅ 완료  21/21 tests
Sprint 3 (공정검증 + 알림): ✅ 완료  21/21 tests
Sprint 4 (관리자 + 동기화): ✅ 완료  31/31 tests
────────────────────────────────────────────
Sprint 1~4 Total:          81/81 PASSED

Sprint 5 (스키마 동기화 + 보안 + PWA):  🔄 사전 작업 진행 중
  ✅ plan.product_info + qr_registry 분리 (DB migration 완료)
  ✅ 컬럼명 ETL 기준 간소화 (mech_start, pi_start 등)
  ✅ product_info.py JOIN 쿼리 + dataclass 업데이트
  ✅ product_info.dart FE 모델 동기화
  ✅ ETL step2_load.py 2-table insert 패턴 적용
  ✅ QR 스캔 인증 버그 수정 (apiServiceProvider 싱글턴)
  ✅ PDA 전용 테이블 11개 삭제 (25→14 테이블)
  ✅ DB 타임존 Asia/Seoul 설정
  ✅ Admin 계정 등록 + 로그인 검증
  ✅ APP_PLAN v4.3 + db_schema_cleanup.sql 갱신
  ❌ migration SQL FK 참조 수정 (003, 004, 005)
  ❌ 누락 Python 모델 생성 (work_start_log, work_completion_log, offline_sync_queue)
  ❌ alert_logs read_at 컬럼 + 트리거
  ❌ config.py → .env 분리 (보안)
  ❌ SMTP 연동 (이메일 실제 발송)
  ❌ Refresh Token 구현
  ❌ PWA Service Worker
  ❌ CLAUDE.md / AGENT_TEAM_LAUNCH.md 최신화
```

---

## 5. 다음 액션 (Sprint 5 팀에이전트 실행 전)

1. **CLAUDE.md 업데이트** — 3-tier 스키마 구조, qr_registry, 컬럼 명세 현행화 (팀에이전트 기준 문서)
2. **AGENT_TEAM_LAUNCH.md 업데이트** — Sprint 5 프롬프트를 현재 DB 상태 기준으로 재작성
3. **팀에이전트 실행** — Sprint 5 잔여 작업 진행

### Sprint 5 잔여 작업 (팀에이전트 할당)
```
BE:  migration FK 수정 → 누락 모델 생성 → alert read_at → .env 분리 → SMTP → Refresh Token
FE:  PWA Service Worker → flutter build web 테스트
TEST: 신규 모델 테스트 → 이메일 mock 테스트 → Refresh Token 테스트
```

### Sprint 6 ��획 (Task seed 포함)
```
BE:  Task seed 상수 정의 (MM 19 + EE 8) → initialize_product_tasks() → audit_log.py
FE:  admin_dashboard 실제 구현 → worker_approval_screen → QR 웹 카메라
TEST: test_work_api 11개 → test_websocket → Task seed 테스트
```
