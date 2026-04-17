# AXIS-OPS 백로그

> 마지막 업데이트: 2026-04-17 (Sprint 61-BE v2.9.4)
> 이 파일은 보류/재검토/계획/아이디어를 한 곳에서 관리합니다.
> 완료된 항목은 PROGRESS.md로 이동합니다.

---

## 🔴 지금 진행 중 / 미해결

| ID | 항목 | 상태 | 비고 |
|----|------|------|------|
| BUG-1 | QR 카메라 권한 팝업 가려짐 | 🔧 수정 중 | DOM 오버레이(z-index:9999)가 브라우저 권한 팝업을 가림. getUserMedia 선행 호출 방식으로 수정 진행 |
| BUG-2 | WebSocket 프로토콜 불일치 | ✅ Sprint 13 수정 완료 | Flask-SocketIO → flask-sock(raw WS) 교체. events.py 전체 리라이트(ConnectionRegistry + ws_handler). FE 변경 0건. 배포/검증 대기 |
| BUG-3 | 출퇴근 버튼 퇴근 후 비활성화 | 🔍 분석 완료 | BE는 당일 다중 in/out 쌍 지원(카운팅 로직), 그러나 FE에서 `checked_out` 상태가 종료 상태로 처리되어 재출근 버튼 비활성화됨. FE 상태 머신에 재출근 플로우 추가 필요. 일일 리셋은 KST 자정 기준 정상 동작 |
| BUG-4 | 알림/알람 실시간 전달 안됨 | ✅ Sprint 13 수정 완료 | scheduler_service.py 5곳 `create_alert()` → `create_and_broadcast_alert()` 변경. DB 저장 + WebSocket broadcast 동시 처리. BUG-2 해결로 실시간 경로 복원. 배포/검증 대기 |
| BUG-5 | QR 카메라 프레임 벗어남 + 스캔 영역 직사각형 | ✅ 수정 완료 + 배포 | **1차 원인(위치)**: `left+right` CSS → `left+width` 명시로 해결. **2차 원인(스캔 영역)**: Dart `jsify()` interop이 html5-qrcode qrbox 객체 전달 실패 (6~8차 시도 모두 실패) → **9차 수정**: 순수 JS `<script>` 태그로 config 생성, Dart interop 완전 제거. qrbox 콜백 함수가 205×205 정사각형 반환 확인. **11차 수정(Sprint 16)**: 3중 방어 — CSS !important(aspect-ratio:1/1), DOM 강제(height=width), MutationObserver 실시간 감시 |
| BUG-6 | 협력사 task 리스트에 작업자명 미표시 | ✅ 수정 완료 | BE `work.py`: task 목록 API에 `worker_name` 필드 추가 (workers 테이블 JOIN). FE `task_item.dart`: `workerName` 필드 추가. FE `task_management_screen.dart`: 카테고리 행에 작업자 아이콘+이름 표시. GST `gst_products_screen.dart`는 기존에 이미 worker_name 표시 구현됨 (시작된 작업만 표시 — 정상) |
| BUG-7 | 휴게시간 일시정지/알람 미작동 + 자동재개 미구현 | ✅ Sprint 14 핫픽스 수정 완료 | IntervalTrigger→CronTrigger(second=0), send_break_end_notifications에 auto-resume 추가, force_pause 멀티작업자 지원. 76 passed |
| BUG-8 | 작업시간(duration)에서 휴게시간 미제외 | ✅ Sprint 14 핫픽스 수정 완료 | `_calculate_working_minutes()` + `_calculate_break_overlap()` 신규. admin_settings 4개 break 자동 차감. 이중차감 방지 (manual pause만 finalize에서 차감) |
| BUG-9 | Force-close에서 total_pause_minutes 미차감 | ✅ Sprint 14 핫픽스 수정 완료 | admin.py force-close에 `_calculate_working_minutes` 적용 + manual pause 차감 |
| BUG-10 | QR 카메라 프레임 스크롤 분리 | ✅ Sprint 14 핫픽스 수정 완료 | ScrollController + onScroll → `updateScannerDivPosition()` 연결. video와 Flutter Container 동기화 |
| BUG-11 | Location QR 필수 설정(on/off) 미작동 | ✅ Sprint 15 수정 완료 | **근본 원인**: `task.location_qr_verified`는 DB에서 항상 FALSE (업데이트 안 됨). **수정**: BE에서 `product.location_qr_id` 직접 체크로 변경. FE에서 QR 스캔 후 location_qr_required 팝업 + 자동 location scan 모드 전환. 28 tests passed |
| BUG-12 | 다중 작업자 시작/종료 FE 차단 | ✅ Sprint 15 수정 완료 | **근본 원인**: FE가 `task.status`(전체 상태)로 버튼 표시 → worker2 시작 불가. **수정**: BE에 `my_status` 필드 추가(work_start_log/completion_log JOIN). FE에 `myWorkStatus` getter + "작업 참여" 버튼 + "내 작업 완료" 뱃지. 28 tests passed |
| BUG-13 | getAdminSettings() 에러 시 빈 {} 반환 | ✅ Sprint 16 수정 완료 | FE `task_service.dart` catch블록: `{}` → `{'location_qr_required': true}` 안전모드 기본값. 에러 시 블록 활성(안전한 쪽)으로 동작 |
| BUG-14 | 다중 작업자 표시 디버깅 부족 | ✅ Sprint 16 디버그 로깅 추가 | BE work.py/gst.py: 2명+ workers task에 `[BUG-14]` 로그. FE task_item.dart: `debugPrint` 추가. 재현 시 로그로 원인 추적 가능 |
| BUG-15 | QR 카메라 div가 dialog overlay 시 가려짐 | ✅ Sprint 15.5 수정 완료 | `hideScannerDiv()`/`showScannerDiv()` 추가. dialog 열릴 때 DOM div 숨김 처리 |
| BUG-16 | System Offline 표시 (서버 정상인데) | ✅ Sprint 16.1 수정 완료 | CORS가 `/api/*`에만 적용 → `/health`는 브라우저 preflight 거부. `__init__.py` CORS에 `/health` 경로 추가 |
| BUG-17 | Location QR 팝업 깜빡임 + 확인 버튼 미작동 | ✅ Sprint 16.1 수정 완료 | MutationObserver가 `display:none` 감지 → hide↔show 무한루프. `hideScannerDiv()`에서 Observer disconnect, `showScannerDiv()`에서 재활성화 |
| BUG-18 | GST Manager 출퇴근 데이터 미표시 | ✅ Sprint 24 핫픽스 수정 완료 | `_get_manager_company_filter()` GST manager → `'GST'` 반환 vs `WHERE w.company != 'GST'` 모순. GST이면 None 반환(전체 접근)으로 수정 |
| BUG-19 | 비밀번호 찾기 — 없는 이메일도 인증 화면 이동 | ✅ Sprint 24 핫픽스 수정 완료 | 보안 관행(항상 200) → 내부 시스템이므로 404 EMAIL_NOT_FOUND 반환으로 변경 |
| BUG-20 | 로그인 에러 메시지 불명확 (계정 미존재 vs 비밀번호 오류) | ✅ Sprint 24 핫픽스 수정 완료 | 동일 INVALID_CREDENTIALS → 404 ACCOUNT_NOT_FOUND + 401 INVALID_PASSWORD 분리 |
| BUG-21 | FE 404 에러 메시지 하드코딩 | ✅ Sprint 24 핫픽스 수정 완료 | "요청한 리소스가 없습니다" → 서버 메시지 그대로 표시 |
| BUG-22 | Logout Storm — 401 무한 루프 | ✅ Sprint 25 수정 완료 | FE: _authSkipPaths + _isForceLogout + _isLoggingOut + clearToken 선행 + 3s timeout. BE: jwt_optional 데코레이터 + logout @jwt_optional (토큰 없이 200 OK). VIEW도 동일 패턴 수정 완료 (v1.4.2) |
| BUG-23 | QR 카메라 Viewfinder 모서리 코너 간헐적 미표시 | ✅ 수정 + 배포 완료 | `_forceSquareAfterCameraStart()`에서 viewfinder 제외 (video 포함 div만 타겟) + CSS `overflow:visible !important` 보호. Netlify 배포 완료 — 실기기 테스트 필요 |
| BUG-24 | Task Seed 반복 실패 — 배포마다 task 0건 | ✅ Sprint 29-fix 수정 완료 | migration 022 소실 → task_type 컬럼 없어 INSERT silent fail. **근본 해결**: `schema_check.py` ensure_schema() 앱 시작 시 자동 검증/복구 + migration 023 정식 기록 + FK CASCADE→RESTRICT |
| FIX-21 | QR 목록 search에 Order No 검색 추가 | ✅ 수정 완료 (2026-03-18) | `qr.py` search WHERE절에 `p.sales_order ILIKE` 추가. FE placeholder 변경 대기 ("S/N, QR Doc ID, Order No 검색...") |
| FIX-22 | Admin 태스크 목록에 DUAL TMS L/R 미표시 | ✅ 수정 + push 완료 (2026-03-18) | `work.py` — `?all=true`(관리자) 시 serial_number 기준 전체 조회로 TANK QR 태스크 포함 |
| FIX-23 | SWS JP line 매칭 누락 (JP(F15) 등) | ✅ 수정 완료 (2026-03-18) | `task_seed.py` — `== 'JP'` → `startswith('JP')` JP 계열 전체 PI_LNG_UTIL 활성 |
| BUG-25 | 생산실적 O/N 펼침 시 S/N 상세 미반환 | ✅ 수정 완료 (2026-03-22) | `production.py` — `sns` 배열 구성 로직 누락. `sns_detail` + `sn_summary` 추가. 변수명 충돌(`sn_progress`→`sn_prog`) 수정 |
| BUG-26 | 생산실적 TMS→TM 키 불일치 — O/N process N/A + S/N TM N/A | ✅ 수정 완료 (2026-03-22) | `production.py` — `_CAT_TO_PROC={'TMS':'TM'}` 매핑. FE `process_status`→`processes` 키 변경만 필요 |
| BUG-26-B | processes ready 미반환 + confirmable 매핑 오류 | ✅ 수정 완료 (2026-03-22) | `ready` alias + `proc_key` 전달 + O/N 스코프 필터 + `_PROC_TO_CAT` 역매핑 (POST confirm 시 TM→TMS 변환) |
| BUG-29 | QR 카메라 프레임 과대 — 직접입력 안보임 | ✅ 수정 + 배포 완료 (2026-03-27) | cameraSize 300→240 + Center 래핑. stretch 방지. 실기기 검증 완료 |
| BUG-30 | 로그인 에러 시 시스템코드 노출 | ✅ 수정 + 배포 완료 (2026-03-28) | api_service.dart 401→서버 message 사용. login_screen.dart 표시 시 `[ERROR_CODE]` regex 제거. 에러코드는 내부 분기용 보존 |
| BUG-31 | PIN→이메일 로그인 전환 미동작 | ✅ 수정 + 배포 완료 (2026-03-28) | pin_login_screen.dart: logout 후 `pushNamedAndRemoveUntil('/')` → 루트 이동, AuthGate가 로그인 화면 표시 |
| BUG-32 | 분석 대시보드 엔드포인트 한글 미표시 | ✅ 수정 완료 (2026-03-30) | analytics.py _ENDPOINT_LABELS 40개 누락 전수 등록 (30→90개) |
| BUG-33 | 릴레이 재완료 시 KeyError: 0 서버 에러 | ✅ 수정 완료 (2026-03-30) | _worker_restarted_after_completion() RealDictCursor dict 접근 — row[0]→row.get('last_start') |
| #48 | 재활성화 권한 체크 `in` 비교 방향 버그 | ✅ 수정 완료 (2026-03-30) | company_base 추출 (접미사 제거) + 비교 방향 통일. TMS(M)/TMS(E) 재활성화 허용. 테스트 10/10 passed |
| #52 | ETL 변경이력 `_FIELD_LABELS` finishing_plan_end 누락 | ✅ 수정 완료 (2026-03-31) | admin.py _FIELD_LABELS에 `finishing_plan_end: 마무리계획일` 추가. VIEW 마무리계획일 조회 400 에러 해소 |
| #51 | progress API에 `sales_order` 필드 추가 | ✅ 완료 (2026-03-31) | progress_service.py CTE+SELECT+sn_map 3곳 추가. regression 23 passed |
| 52 | TM 체크리스트 Phase 1 — Partner 검수 시스템 | ✅ 완료 (2026-04-01) | migration 043 + checklist_service.py + TM API 3개 + Admin CRUD 4개 + task 알림 + FE 화면. 테스트 39/39 passed |
| 53 | 알림 소리 + 진동 — 포그라운드 알림 피드백 | ✅ 완료 (2026-04-02) | Web Audio API 비프음 5종 + navigator.vibrate + 프로필 설정 드롭다운. 패키지 추가 0 |
| 52-A | TM 체크리스트 보완 — COMMON seed + scope 수정 | ✅ 완료 (2026-04-02) | migration 043a + COMMON 15항목 + item_type 컬럼 + scope='all' 기본값 |
| 54 | 공정 흐름 알림 트리거 — partner 분기 + admin_settings | ✅ 완료 (2026-04-02) | process_validator + task_service + migration 044 + FE 설정 UI. 테스트 30/34 (4 FE skip) |
| 52-BF | TM 체크리스트 BUG-FIX #1~#6 | ✅ 수정 완료 (2026-04-02) | #1~#5 + #6 알림 메시지 [S/N\|O/N] 포맷 + 팝업 QR 행 제거 |
| 31C-A | PI 위임 모델별 옵션 — pi_delegate_models | ✅ 완료 (2026-04-03) | allowlist 방식. GAIA/DRAGON 위임, SWS GST PI 직접. 테스트 18/18 passed |
| 53 | monthly-summary API weeks + totals 집계 | ✅ 완료 (2026-04-03) | 금요일 기준 주차-월 매핑 + MECH/ELEC/TM completed/confirmed. 테스트 18/18 passed |
| 54 | 체크리스트 성적서 API — O/N 검색 + S/N 성적서 | ✅ 완료 (2026-04-03) | _get_checklist_by_category 공통 추출 + report/orders + report/{sn} 배치 쿼리. 테스트 19/19 passed |
| BUG-34 | 체크리스트 master_id 응답 누락 | ✅ 수정 (2026-04-03) | _get_checklist_by_category items에 master_id 추가 → FE 토글 정상 |
| BUG-35 | #53 monthly-summary mech_start→mech_end 필터 | ✅ 수정 (2026-04-03) | mech_end 기준 + NULL fallback. GBWS-6905 등 3월 시작→4월 종료 제품 포함 |
| 54-FE | TM 체크리스트 description 표시 | ✅ 완료 (2026-04-03) | 항목명 아래 검사방법/기준 fontSize 10 silver |
| BUG-6 | 다중작업자 동료 resume 403 FORBIDDEN | ✅ 수정 완료 (2026-04-07) | work.py — task coworker 허용 → Sprint 55에서 worker별 pause로 근본 해결 |
| 55 | Worker별 Pause/Resume + Auto-Finalize | ✅ 완료 (2026-04-07) | 개인별 pause, 전원 relay auto-finalize, FINAL task 릴레이 불가. 테스트 27/27 + regression 28/28 |
| INFRA-1 | Migration 자동 실행 시스템 | ✅ 완료 (2026-04-08) | migration_runner.py + migration_history 테이블. 앱 시작 시 미실행 migration 순차 적용. 041~045 운영 적용 완료 |
| TEST-AL20 | Alert 20종 전체 검증 테스트 | ✅ 완료 (2026-04-08) | test_alert_all20_verify.py 38TC (36 passed, 2 skipped). 검토 후 is_relay 버그 등 3건 수정. TC-PR-20 assert 수정 |
| 55-B | Task 목록 API my_pause_status 누락 | ✅ 완료 (2026-04-09) | work.py get_tasks_by_serial() work_pause_log JOIN 추가. 테스트 5/5 + regression 8/8 passed |
| 56 | QR 목록 API elec_start 필드 + 필터 | ✅ 완료 (2026-04-09) | qr.py 4곳 수정. QR regression 23/23 passed |
| #55 | 비활성 사용자 목록 노출 수정 | ✅ 완료 (2026-04-09) | admin.py workers/managers/출퇴근 API에 is_active=TRUE 필터. migration 040 운영 실행 |
| 57 | ELEC 공정 시퀀스 변경 + 체크리스트 | ✅ 완료 (2026-04-09) | INSPECTION freeroll, IF_2 FINAL, Dual-Trigger 닫기, 체크리스트 31항목, migration 046/046a. 테스트 13/13 + TM regression 3/3 |
| BUG-36 | Dual 제품 TANK_MODULE 일괄 처리 | ✅ Sprint 57-C 수정 (2026-04-10) | get_incomplete_tasks qr_doc_id 옵션 + TMS qr_doc_id 필터. DUAL L/R 독립 완료 판정 |
| 57-C | ELEC seed 교체 + SELECT/INPUT 스키마 | ✅ 완료 (2026-04-10) | migration 047. 실제 전장외주검사성적서 31항목 + select_options/selected_value/input_value + qr_doc_id UNIQUE. 34/34 passed |
| 57-FE | ELEC 체크리스트 FE 연동 | ✅ 완료 (2026-04-10) | startTask/completeTask Record 반환, _kFinalTaskIds 동기화, ElecChecklistScreen 신규, 체크리스트 버튼 ELEC 확장, 2차 배선 judgment_phase 수정 |
| BUG-37 | TM DUAL L/R 체크리스트 분리 | ✅ Sprint 57-D 수정 (2026-04-10) | upsert_tm_check qr_doc_id 파라미터 + FE 6곳 qrDocId 전달 |
| BUG-38 | ELEC SELECT TUBE 색상 드롭다운 | ✅ 코드 완료 → QA 검증 | DropdownButton 구현 완료. 실기기 QA 필요 |
| BUG-39 | QI 공정검사 ELEC 2차 체크 | ✅ Sprint 57-E 수정 (2026-04-10) | _isQiBlocked role 검증 + _hasChecklistAccess QI 포함 + initialPhase=2 |
| BUG-40 | 체크리스트 버튼 시작 시 미활성 | ✅ Sprint 57-E 수정 (2026-04-10) | _hasChecklistAccess TM/ELEC/QI in_progress 확장 |
| 30-BE | 성적서 API ELEC Phase + TM DUAL | ✅ 완료 (2026-04-10) | get_checklist_report ELEC Phase 1+2 자동분리 + TM DUAL L/R + 진행률 재활용. 33/33 passed |
| 58-BE | check_elec_completion + confirmable + ELEC status | ✅ 완료 (2026-04-13) | Phase 1+2 합산, confirm_checklist_required 토글, /elec/{sn}/status. 36/36 passed |
| 59-BE | TM qr_doc_id 정규화 | ✅ 완료 (2026-04-14) | _check_tm_completion SINGLE DOC_{S/N} + DUAL L/R, get_checklist_report 통합, 레거시 UPDATE. 37/37 passed |
| 60-BE | ELEC 마스터 정규화 | ✅ 완료 (2026-04-15) | phase1_applicable + qi_check_required + remarks 컬럼, 문자열 추론 제거, 마스터 API 확장. migration 048. 42/43 passed |
| 61-BE | 알람 강화 + 미종료 작업 API 확장 | ✅ 완료 (2026-04-17) | sn_label() O/N 통일, 에스컬레이션 3종, pending API 확장, SETTING_KEYS +5, migration 049. 29/29 passed |
| FEAT-1 | 사용자 행위 트래킹 + 분석 대시보드 | ✅ BE Sprint 32 완료 (2026-03-19) | `app_access_log` 테이블 + analytics API 4개 + 30일 정리 스케줄러. VIEW 분석 대시보드는 별도 Sprint |
| BUG-41 | PWA 업데이트 시 PIN 초기화 + 이메일 재입력 요구 | 🟡 BACKLOG (우선순위 보류) | Chrome PWA 환경에서 업데이트 후 PIN 로그인 화면 대신 초기 이메일 로그인 화면으로 진입, 이메일 전체 재입력 필요. 변경 범위/regression 리스크 대비 우선순위 낮음 — 아래 "BUG-41 상세" 섹션 참조 |
| BUG-42 | 명판 소형 QR 접사 인식 실패 | 🔴 OPEN | 기본 카메라로는 문자열 정상 읽힘 / OPS 앱 스캐너(html5-qrcode)는 미인식. 명판 QR 이미지 크기가 스티커 대비 작아 매크로 포커스 + 고해상도 + 줌 필요. 아래 "BUG-42 상세" 섹션 참조 |
| BUG-43 | 분석 대시보드 기능별 사용량 한글 라벨 누락 (24건) | ✅ 수정 완료 (2026-04-17) | Sprint 52+ 체크리스트/성적서/ELEC 엔드포인트 등 24개 `_ENDPOINT_LABELS` 미등록 → 전수 등록. 기존 111키 → 135키 (유니크 108 라우트 커버) |
| BUG-44 | OPS 미종료 작업 목록 0건 반환 (Admin/Manager 양쪽) | ✅ 수정 완료 (2026-04-17) | `get_pending_tasks()` INNER JOIN → LATERAL JOIN (work_start_log FK). Claude×Codex 교차 검증 합의. 29/29 passed |

---

## ✅ Sprint 29 보완 완료 (v1.7.7, 2026-03-16)

- DB: `role_enum`에 PM 추가 (migration 021 적용)
- BE: 이름 기반 로그인 (`get_worker_by_name`, login 조회 체인 확장)
- BE: monthly-detail `ship_plan_date` 응답 추가
- BE: monthly-detail `per_page` 상한 200 → 500

## ✅ Sprint 29 완료 (v1.7.6, 2026-03-15) — 공장 API (BE only)

- `GET /api/admin/factory/monthly-detail` — 월간 생산 현황 상세 (view_access_required)
- `GET /api/admin/factory/weekly-kpi` — 주간 KPI 대시보드 (gst_or_admin_required)
- test_factory.py 18 passed
- factory.py 블루프린트 신규 (12번째)

---

## ✅ Sprint 27-fix 완료 (2026-03-15) — Task Seed Silent Fail + SINGLE_ACTION UI

### 근본 원인
`022_add_task_type.sql` migration 미적용 상태에서 task seed가 `task_type` 컬럼 참조 → silent fail (`logger.warning`으로 삼킴).

### 해결
- 에러 로깅 강화 (warning → error + traceback) — 향후 silent fail 방지
- migration 적용 후 GBWS-6869, GBWS-6867 각각 20개 task 생성 확인
- debug 엔드포인트 추가 → 원인 확인 → 제거 완료
- BE task 목록 API에 `task_type` 필드 추가 (누락 수정)
- FE task_management_screen: SINGLE_ACTION task에 녹색 "완료" 버튼 표시 (Netlify 배포 완료)

---

## ✅ Sprint 27 완료 (v1.7.4, 2026-03-14) — 단일 액션 Task (task_type)

### 개요
app_task_details 테이블에 `task_type VARCHAR(20) DEFAULT 'NORMAL'` 컬럼 추가. 기존 시작/종료 2-step → 완료 체크만(SINGLE_ACTION) 지원.

| Task | 공정 | 현재 | 변경 | 주체 |
|------|------|------|------|------|
| Tank Docking | MECH | 시작/종료 (NORMAL) | 단일 액션 (SINGLE_ACTION) | MECH 담당 |
| 출하완료 (SI_SHIPMENT) | SI (신규) | 없음 | 단일 액션 (SINGLE_ACTION) | SI 담당 |

### 구현 완료 항목
- 022_add_task_type.sql migration (Railway DB 적용 완료 2026-03-14)
- TaskDetail model + complete_single_action()
- TaskSeed update (TANK_DOCKING→SINGLE_ACTION, SI_SHIPMENT 신규, total 20)
- POST /work/complete-single 엔드포인트
- TaskItem.dart taskType 필드 + isSingleAction getter
- task_detail_screen.dart 단일 액션 "완료" 버튼 UI
- FE service/provider completeSingleAction()
- ⚠️ migration 미적용으로 task seed silent fail 발생 → 2026-03-14 적용으로 해결

---

## ✅ ETL pi_start 변경이력 지원 (2026-03-14) — CORE-ETL Sprint 2-A 연동

### 개요
CORE-ETL에서 pi_start(가압시작) 변경이력 추적 추가에 따른 OPS BE 수정.

### 변경 내역
- `backend/app/routes/admin.py`: `_FIELD_LABELS`에 `'pi_start': '가압시작'` 추가 (5→6개)
- GET `/api/admin/etl/changes`에서 `field=pi_start` 필터 + 한글 라벨 표시 지원
- **연관 변경**: CORE-ETL step2_load.py `TRACKED_FIELDS`에 `'pressure_test': 'pi_start'` 추가 (별도 repo)
- **VIEW FE**: FIELD_CONFIG, DATE_FIELDS, KPI 그리드 6열, 주간 차트 — VIEW 별도 진행

---

## ✅ Sprint 28 완료 (v1.7.5, 2026-03-13)

### AXIS-VIEW 권한 데코레이터 재정비
- `get_current_worker()` 캐싱 헬퍼 추가 (request 당 1회 DB 조회)
- `admin_required`, `manager_or_admin_required` 내부 → 캐싱 리팩토링
- `@gst_or_admin_required` 신규 (GST 소속 + Admin만 허용, 공장 대시보드 전용)
- `@view_access_required` 신규 (GST + Admin + Manager, VIEW 전체 공개 API)
- QR 엔드포인트: 자사필터로 처리하여 데코레이터 변경 불필요 → 제거
- `admin.py` ETL 변경이력: `@manager_or_admin_required` → `@view_access_required`
- DB 스키마 변경 없음, FE 변경 없음
- pytest: 667 passed (regression 0건)

---

## ✅ Sprint 26 완료 (v1.7.3, 2026-03-12)

### PWA-1: ✅ SW 업데이트 토스트 — 완료
- index.html: controllerchange + updatefound 감지 → 하단 토스트 표시 → 탭하면 reload

### PWA-2: ✅ 업데이트 내용 팝업 — 완료
- UpdateService: SharedPreferences 버전 비교 → notices API 호출 (최초 1회)
- UpdateDialog: GxDesignSystem 팝업 (버전 뱃지 + 본문 스크롤 + 확인 버튼)

### DB-PROTECT: ✅ conftest.py 운영 데이터 보호 강화 — 완료
- workers, hr 스키마, auth 스키마, admin_settings, model_config DROP 제거

---

## ✅ Sprint 25 완료 (v1.7.2, 2026-03-12)

### BUG-22: ✅ Logout Storm 수정 — 완료
- FE: `_authSkipPaths` + `_isForceLogout` + `_isLoggingOut` 3중 방어
- BE: `jwt_optional` 데코레이터 + logout `@jwt_optional` 변경

### pytest 전체 실행 결과: 643 passed / 44 failed / 12 skipped
- 실패 원인: 코드 버그 0건 — 테스트 코드 데이터 불일치 + DB 상태 간섭
- Task Seed count 수정 (PI/QI/SI 추가: GAIA 15→19, 기타 13→17)
- `create_test_worker` 잔여 데이터 cleanup 추가
- `test_auth.py` Sprint 24 login 에러 분리 반영 (404 ACCOUNT_NOT_FOUND)

### TEST-FIX: ✅ 테스트 수정 3건 — 완료
- `test_model_task_seed_integration.py` — seed count assertions 업데이트
- `conftest.py` — create_test_worker에 pre-insert cleanup 추가
- `test_auth.py` — Sprint 24 login error 코드 변경 반영

---

## ✅ Sprint 24 완료 (v1.7.1, 2026-03-11)

### 핫픽스 (BUG-18~21):
- BUG-18: GST Manager 출퇴근 데이터 미표시 → GST manager는 전체 접근
- BUG-19: 비밀번호 찾기 없는 이메일 → 404 EMAIL_NOT_FOUND 반환
- BUG-20: 로그인 에러 분리 → 404 ACCOUNT_NOT_FOUND + 401 INVALID_PASSWORD
- BUG-21: FE 404 하드코딩 → 서버 메시지 그대로 표시

---

## ✅ Sprint 23 완료 (v1.7.0, 2026-03-11)

### OPS-1: ✅ is_manager 로그인 시 권한 부여 메뉴 표시 — 완료
### OPS-2: ✅ 관리자 옵션 메뉴 위치 이동 (공지사항 위) — 완료

### VIEW-1: ETL 변경이력 알림 뱃지 (Header + 사이드바) — 예정 (VIEW 프로젝트)
- `/api/admin/etl/changes?days=1` → total_changes - last_seen = unread count
- Header.tsx 알림 아이콘 + 사이드바 "변경이력" 뱃지

### VIEW-2: Admin 간편 로그인 (prefix 매칭) — 예정 (VIEW 프로젝트)
- BE `get_admin_by_email_prefix()` 이미 구현됨
- VIEW LoginPage.tsx에서 `@` 미포함 시 prefix 로그인 호출

---

## ✅ Sprint 22-A/B 완료 (2026-03-10)

### SEC-1: ✅ email_verified 완료 시 Admin 승인 알림 — 완료
### SEC-2: ✅ 이메일 재인증(재전송) 엔드포인트 — 완료 (BE만, FE 연동은 별도)
### SEC-3: ✅ GPS enableHighAccuracy: true — 완료
### SEC-4: ✅ DMS→Decimal 변환 헬퍼 — 완료

### DB-1: DB 보호 정책
- **배경**: HR 테이블(출퇴근, 근무자)은 운영 데이터 — 손실 불가
- **보호 대상**: `workers`, `partner_attendance`, `qr_registry`
- **현재 Railway 환경**: 테스트 DB = 운영 DB (동일 인스턴스)
  - Railway Pro 자동 일일 백업 + 7일 보관 ✅
  - BE 코드 push는 DB에 영향 없음 (코드와 DB 분리)
- **conftest.py 백업/복원 현황**:
  - ✅ `workers` — backup/restore 구현됨
  - ✅ `hr.worker_auth_settings` — backup/restore 구현됨
  - ✅ `hr.partner_attendance` — backup/restore 구현됨
  - ✅ `qr_registry` — backup/restore 구현됨 (Sprint 22-E)
  - ✅ `plan.product_info` — backup/restore 구현됨 (Sprint 22-E)
- **운영 규칙**: ALTER TABLE 실행 전 반드시 수동 pg_dump
- **최종 목표**: 사내 WAS DB로 마이그레이션 → production 분리 운영

### PM-1: ✅ PM Role push + Manager 권한 위임 구조 — 완료 (Sprint 22-C, v1.6.2)

**PM Role**: ✅ 완료 (코드 + Railway DB enum 추가)

**Manager 권한 위임**: ✅ 완료 (Sprint 22-C)
- `toggle_manager()`: `@admin_required` → `@manager_or_admin_required` 변경
- Manager: 같은 company 소속만 is_manager 부여/해제 가능
- Admin 보호: Manager → Admin 권한 변경 시 403
- 테스트 5/5 통과 (기존 5개 + 신규 5개 = 10개 전체 통과)

---

## 🟡 재검토 (Review Needed)

보류해둔 항목. 다음 Sprint 기획 시 우선 검토.

### RV-4: Flaky 테스트 안정화 (중간 리스크 3건)
- **배경**: Sprint 19 회귀 테스트에서 23건 실패 — 모두 기존 flaky 테스트 (신규 코드 결함 아님)
- **중간 리스크 그룹**:
  1. **test_pause_resume** — 타이밍 의존성 (`sleep` 기반 검증). 운영 기능은 정상이나 CI에서 간헐적 실패. 재현 불안정하여 디버깅 어려움
  2. **test_scheduler_integration** — APScheduler 초기화 타이밍 + DB 상태 간섭. 스케줄러 자체는 production에서 정상 동작하나, 테스트 격리 부족으로 실행 순서에 따라 실패
  3. **test_pin_auth** — 테스트 간 DB 상태 공유로 인한 실행 순서 의존성. PIN 인증 기능 자체는 정상
- **낮은 리스크 그룹** (기록만): test_product_api, test_task_seed, test_sprint10_fixes — DB fixture 간섭이 원인, 운영 리스크 없음
- **권장 조치**: 테스트 격리 개선 (각 테스트 전후 DB 롤백), 타이밍 기반 → 이벤트 기반 검증으로 리팩터링
- **우선순위**: 중 (CI/CD 구축 전에 해결 권장)
- **등록일**: 2026-03-06

### RV-1: checklist 스키마 vs 실제 Excel 양식 불일치
- **배경**: `출하 어플용의 사본.xlsx` (sheet=DB) 분석 결과, 현재 checklist_master 스키마(단순 item_name 기반)와 실제 데이터 구조가 다름
- **현재 스키마**: product_code + category + item_name
- **실제 Excel**: 자재코드(material_code) + 자재내역 + 규격1/규격2 + 수량 + 단위 + 상태(OK/NG)
- **차이점**: 현재는 체크리스트 "항목명"만 있지만, 실제는 BOM(자재 목록) 기반으로 각 자재별 OK/NG 판정
- **필요 작업**:
  - checklist_master에 material_code, spec1, spec2, qty, unit 컬럼 추가 검토
  - item_master 테이블 분리 여부 결정
  - status를 PENDING/OK/NG/NA로 확장
  - Excel ETL import 로직 수정
- **DB 현황**: checklist 스키마 생성됨, 테이블 비어있음 (테스트는 임시 데이터로 통과)
- **결정 시점**: Sprint 13 이전

### RV-2: FE 전역 시간 표시 검증
- **배경**: Sprint 11 핫픽스로 4개 화면 `.toLocal()` 추가했지만, 다른 화면에도 같은 문제 있을 수 있음
- **확인 대상**: 모든 DateTime 표시 화면에서 `.toLocal()` 호출 여부
- **우선순위**: 낮음 (현재 수정된 4개 화면이 주요 사용 화면)

### RV-3: 앱 아이콘 최적화
- **배경**: G 다이아몬드 심볼로 favicon + PWA 아이콘 생성 완료, 모바일 홈화면 아이콘 크기 미세 조정 필요
- **현재**: 72% fill ratio로 생성, 사용자 피드백 대기
- **우선순위**: 낮음

---

## 🟠 배포 준비

| ID | 항목 | 설명 | 상태 |
|----|------|------|------|
| DP-1 | Railway Flask API 설정 | `axis-ops-api.up.railway.app` | ✅ 완료 |
| DP-2 | GitHub commit/push | Sprint 5~12 + 배포설정 push 완료 | ✅ 완료 |
| DP-3 | FE apiBaseUrl 변경 | `constants.dart` → Railway 도메인으로 변경 | ✅ 완료 |
| DP-4 | PWA 배포 | `flutter build web` → Netlify `gaxis-ops.netlify.app` 배포 | ✅ 완료 |
| DP-5 | 베타 테스트 | 현장 작업자 실사용 테스트 | 대기 (BUG-1 해결 후) |
| DP-6 | CI/CD 구축 | GitHub Actions (CLAUDE.md에 추후로 기록됨) | 추후 |

**현재 배포 URL**:
- FE (PWA): `https://gaxis-ops.netlify.app`
- BE (API): `https://axis-ops-api.up.railway.app`

**로컬 테스트**: `constants.dart`에서 apiBaseUrl을 `http://localhost:5001/api`로 변경 후 `flutter run -d chrome`

---

## 📋 VIEW 생산관리 페이지 검토 (2026-03-13)

### 생산일정 (ProductionPlanPage)
- **GST 공정 일정만 표시** (PI/QI/SI + 출하). MECH/ELEC은 변수가 많고 OPS에서 트래킹
- GST 공정은 보통 하루 만에 끝남 → 현황 파악 용이
- 파이프라인 라벨: **가압(PI) → 공정(QI) → 포장(SI) → 출하**. 자주검사 삭제
- 출하 컬럼 = finishing_plan_end 값 확정
- API: #10 monthly-detail 그대로 사용, 권한 @view_access_required
- **BE 추가 코드 거의 없음** — 엔드포인트 구현 1개뿐

### 생산실적 (ProductionPerformancePage)
- **협력사 실적 처리용 페이지** (MECH/ELEC/TM). GST 공정은 QMS I/F로 자동 처리
- **확인 주체: PM**. OPS progress 100% → VIEW 반영(react) → PM 확인 → SAP key 값 저장
- 혼재 태그 (P&S/C&A): 업체별 개별 확인 필요 → 행/셀 단위 처리 + 추후 일괄 처리
- 월마감 탭: 주간 결과 합산 — 실제 완료 count vs 실적처리 count (미처리 건수 체크)
- 일괄확인: OPS progress 100% 건에 대한 실적 일괄 승인 처리
- SAP key 값 매핑 columns 확인 필요 (내용 정리 우선)

### 출하이력 (ShipmentHistoryPage)
- finishing_plan_end = 출하예정일, actual_ship_date = 실제출하일
- 데이터 소스 확정 대기, 출하 지연 상태 추가 검토 필요
- 기간/고객사 필터 추가 권장

### 출하 확인 프로세스 (전체 흐름)
1. **OPS App**: SI 담당자가 QR 스캔 → "출하완료" task 체크 (단일 액션)
2. **BE 자동 처리**: actual_ship_date = NOW() + qr_registry.status = 'shipped'
3. **VIEW 생산실적**: 공정별 "확인" 버튼 활성화 → 실적 확인
4. **VIEW 생산관리(PM)**: 최종 승인 → SAP key-in 값 저장
5. **CORE-ETL**: actual_ship_date 덮어쓰기 방지 (CASE 분기)
- SAP/QMS 매핑 data thread 값은 추후 정의 예정

---

## 🔵 추후 구현 (Phase 로드맵)

CLAUDE.md Phase 계획 기반. 시급도순.

### Phase A 잔여: 생체인증
- **내용**: 지문/FaceID — WebAuthn API (HTTPS + Flutter Web JS interop)
- **현재**: Sprint 12에서 메뉴 UI만 생성 + "추후 오픈 예정" 안내
- **의존성**: PWA 배포(HTTPS) 완료 ✅

### Phase B 잔여: Admin 출퇴근 대시보드
- **내용**: 협력사 출퇴근 현황 조회 (당일 + 월간 집계)
- **결정**: App에서 제외 → AXIS-VIEW (React 대시보드)에서 구현
- **BE API**: ✅ Sprint 19-E 완료 — `/api/admin/hr/attendance/today`, `/attendance?date=`, `/attendance/summary`
- **남은 작업**: 월간 집계 API (GET /api/admin/hr/attendance/monthly) 추후 필요 시 추가
- **의존성**: hr.partner_attendance 테이블 (Sprint 12에서 생성)

### Phase B 잔여: GST 근태 확장
- **내용**: hr.gst_attendance 테이블은 Sprint 12에서 생성, API/UI 미구현
- **용도**: 그룹웨어 RDB 연동 or 동기화
- **시기**: 미정 (그룹웨어 연동 계획 수립 후)

### Phase C: BOM 검증
- **내용**: product_bom 테이블 + bom_checklist_log
- **관련**: RV-1 (checklist 스키마 재검토)과 연결될 수 있음
- **시기**: checklist 스키마 확정 후

### ~~WebSocket 실시간 통신 정식 구현~~ → ✅ Sprint 13 완료
- Sprint 13에서 flask-sock(raw WS) 마이그레이션으로 해결
- FE `web_socket_channel`과 BE `/ws` 엔드포인트 정합성 확보

### ~~QR ETL 자동화 파이프라인~~ → axis-core-etl repo로 분리 완료 (2026-03-09)
- **상태**: 별도 repo(`axis-core-etl`)에서 관리 → `AXIS-CORE/CORE-ETL/BACKLOG.md` 참조
- **QR 라벨 관리 페이지**: 별도 검토 (라벨기 자동생성으로 우선순위 낮아짐)

### ~~Geolocation 기반 접속 보안 (2차 보안)~~ → ✅ Sprint 19-D 완료
- Sprint 19-D에서 구현 완료
- admin_settings 5개 키 (geo_check_enabled, geo_latitude, geo_longitude, geo_radius_meters, geo_strict_mode)
- FE: 출퇴근 시 GPS 좌표 전송, Admin UI 위치 보안 설정
- BE: Haversine 거리 검증, soft/strict 모드, HQ 면제
- 11 tests passed

### ~~신규 가입 시 Admin 이메일 알림~~ → ✅ Sprint 20-A 완료
- Sprint 20-A에서 구현 완료
- email_service.py 신규: get_admin_emails() + send_register_notification()
- auth.py register 성공 시 Admin 전원 이메일 발송 (best-effort)
- 5 tests passed

### ~~공지사항 탭 (앱 내 업데이트 노트)~~ → ✅ Sprint 20-B 완료
- Sprint 20-B에서 구현 완료
- BE: notices 테이블 + 5개 CRUD API
- FE: 공지 목록/상세/작성 화면, 홈 메뉴 카드 추가
- 6 tests passed

### defect 스키마
- **내용**: 불량 분석, 추적, 리포트 (QMS 연동)
- **시기**: 미정

---

## 🟡 체크리스트 확장 설계 (MECH/ELEC/TM 자주검사)

> 마지막 업데이트: 2026-04-09
> 상태: MECH 전체 확정 (#1~#20), TM 확인 완료, VIEW 연동 설계 완료, **ELEC 양식 수집 완료 → Sprint 57 할당**

### 배경
- 기존 Sprint 11 `checklist` 스키마 (checklist_master + checklist_record) 확장
- VIEW 대시보드에서 마스터 항목 CRUD + APP에서 자주검사 토스트 팝업
- 실적확인(confirm) 연동: progress 100% + 체크리스트 완료 = 승인 가능

### MECH 양식 분석 (기구 조립 검사 성적서)
- 소스: `현황판_260108_MFC Maker추가 260223.xlsm` → sheet `공정진행현황-2행`
- **20개 그룹, 약 60개 항목** (#1~#20 전체 확인 완료)

**#1~#6** (cols 1~130):

| # | inspection_group | CHECK 항목 | INPUT 항목 | 비고 |
|---|---|---|---|---|
| 1 | 3Way V/V | Spec 확인, 볼트 체결 (2) | 없음 | |
| 2 | WASTE GAS | 배관 도면 일치, 클램프 체결 (2) | 없음 | |
| 3 | INLET | 배관 도면 일치 (1) | 배관 S/N 확인 Left#1~#4/Right#1~#4 (1) | DRAGON 전용 — 비DRAGON은 NA. `product_info` 참조 |
| 4 | BURNER | SUS Fitting 조임, Gas Nozzle Cover 휨, 클램프 체결 (3) | 없음 | |
| 5 | REACTOR | Fitting 조임, Tube 조립, 클램프 체결, Cir Line Tubing (4) | 없음 | |
| 6 | GN2 | Sol V/V Spec/Flow, SUS Fitting 조임, Tube 조립, Speed Controller 방향 (4) | Speed Controller 수량 EA (1) + MFC Spec (1) | |

**#7~#20** (cols 131~260):

| # | inspection_group | CHECK 항목 | INPUT 항목 | 비고 |
|---|---|---|---|---|
| 7 | LNG | MFC Spec/Flow 방향, SUS Fitting 조임, Part 조립 (3) | MFC Maker/Spec 정보 (1) | |
| 8 | O2 | MFC Spec/Flow 방향, SUS Fitting 조임, Part 조립 (3) | MFC Maker/Spec 정보 (1) | |
| 9 | CDA | Sol V/V Spec/Flow, SUS Fitting 조임, Part 조립, Speed Controller 방향 (4) | MFC Maker/Spec 정보 (1) + Speed Controller 수량 EA (1) | |
| 10 | BCW | Flow Sensor Spec/방향, 공압 밸브 Flow, SUS Fitting 조임, Part 조립 (4) | Flow Sensor Spec 정보 (1) | |
| 11 | PCW-S | Flow Sensor Spec/방향, 공압 밸브 Flow, SUS Fitting 조임, Part 조립 (4) | Flow Sensor Spec 정보 (1) | |
| 12 | PCW-R | Flow Sensor Spec/방향, 공압 밸브 Flow, SUS Fitting 조임, Part 조립 (4) | Flow Sensor Spec 정보 (1) | |
| 13 | Exhaust | Packing 조립, Packing Guide 고정, SUS Fitting 조임, BCW Nozzle Spray (4) | 없음 | |
| 14 | TANK | Cir Pump Spec, Flow Sensor Swirl Orifice, Tank 내부 이물질 (3) | 없음 | |
| 15 | PU | 버너 및 이그저스트 위치 (1) | 없음 | |
| 16 | 설비 상부 | SUS Fitting 조임, Drain Nut 조립, 미사용 Hole 막음 (3) | 없음 | |
| 17 | 설비 전면부 | Interface 스티커 부착 (1) | 없음 | |
| 18 | H/J | 배관 H/J 완전체 조립, 벨크로 체결, 케이블 정리 (3) | 없음 | |
| 19 | Quenching | Flow Sensor Spec/방향, Flow Sensor 위치 (2) | 없음 | |
| 20 | 눈관리 | 눈관리 스티커 위치 (1) | 없음 | |

- **가압검사 섹션**: 체크리스트 범위에서 **제외**
- **ISSUE사항**: 체크리스트 외 별도 기록란 (범위 외)

### TM 양식 분석 (이미지 기준)
- 총 15개 항목: BURNER(3) + REACTOR(4) + Exhaust(4) + TANK(4)
- MECH와 컬럼 구조 동일 (검사 항목/검사 내용/기준·SPEC/검사 방법/1차판정/작업자/2차판정/비고)

### 스키마 확장 — checklist_master 컬럼 추가

| 컬럼명 | 타입 | 매핑 | 비고 |
|--------|------|------|------|
| `inspection_group` | VARCHAR(100) | 검사 항목 그룹 (BURNER/LNG/BCW 등) | 그룹핑 레이어 |
| `item_name` | VARCHAR(255) | 검사 내용 | 기존 컬럼 유지 |
| `item_type` | VARCHAR(10) DEFAULT 'CHECK' | **CHECK** = PASS/NA 판정 항목 / **INPUT** = 직접 입력 항목 | 신규 핵심 |
| `spec_criteria` | VARCHAR(255) | 기준/SPEC (GAP GAUGE 등) | 신규 |
| `inspection_method` | VARCHAR(100) | 검사 방법 (측수 검사/육안 검사) | 신규 |
| `second_judgment_required` | BOOLEAN DEFAULT FALSE | 2차판정 옵션키 | 카테고리 단위 ON/OFF |

### item_type 동작
- **CHECK** (`item_type = 'CHECK'`): APP UI에서 PASS/NA 버튼 표시 → `checklist_record.status`에 저장
- **INPUT** (`item_type = 'INPUT'`): APP UI에서 텍스트 입력 필드 표시 → `checklist_record.note`에 저장
  - MFC Maker/Spec 정보 (LNG, O2, CDA, GN2)
  - Flow Sensor Spec 정보 (BCW, PCW-S, PCW-R)
  - Speed Controller 수량 (CDA, GN2)
  - 배관 S/N (INLET — 해당 제품만 대시보드에서 항목 추가)
- **INPUT 항목은 선택 입력** — 비어있어도 실적 승인에 영향 없음 (실적 승인 조건은 CHECK 항목 전체 판정 완료만 확인)

### 설계 원칙: 대시보드 중심 관리
- product_info JOIN 등 코드 레벨 조건부 로직 **사용 안 함**
- 제품별 항목 차이(DRAGON 배관 S/N, 신규 추가 항목 등)는 **VIEW 대시보드에서 해당 product_code에 항목 추가/수정/비활성화로 관리**
- 모든 설정값·변경값은 대시보드에서 edit 가능한 구조로 통일
- BE는 master 테이블 데이터만 충실히 서빙하면 됨 (비즈니스 로직 최소화)

### 스키마 확장 — checklist_record 변경

| 변경 | 현재 | 제안 |
|------|------|------|
| `is_checked` BOOLEAN | TRUE/FALSE | → `status` VARCHAR(10): **PASS / NA** 2가지만 (CHECK 항목용) |
| 단일 판정 | 1회 | → `judgment_round` INTEGER DEFAULT 1 (1차=1, 2차=2) |
| UNIQUE 제약 | `(serial_number, master_id)` | → `(serial_number, master_id, judgment_round)` |

- 미검사 = record 행 없음 (LEFT JOIN 시 NULL). PENDING 상태 불필요
- 비고(`note`): APP에서 직접 입력 가능 (기존 컬럼 유지)
- INPUT 항목: `status` = NULL, `note`에 입력값 저장

### 옵션키 동작 (second_judgment_required)
- **OFF (기본)**: 전항목 1차판정 완료 (CHECK→PASS/NA, INPUT→note 입력) → 실적 승인 가능
- **ON**: 전항목 1차 + 2차판정 모두 완료 → 실적 승인 가능
- TM/MECH/ELEC 동일 조건으로 적용

### 누락 BE API — Admin CRUD (VIEW 대시보드용)

| 엔드포인트 | 메서드 | 용도 | 권한 |
|---|---|---|---|
| `/api/admin/checklist/master` | GET | 마스터 목록 (category, product_code 필터) | admin/manager/gst(pm) |
| `/api/admin/checklist/master` | POST | 개별 항목 생성 | admin/manager/gst(pm) |
| `/api/admin/checklist/master/{id}` | PUT | 항목 수정 | admin/manager/gst(pm) |
| `/api/admin/checklist/master/{id}` | DELETE | 비활성화 (soft delete → is_active=FALSE) | admin |

### VIEW FE 구성

#### 1. 생산관리 > 체크리스트 관리 (마스터 CRUD)
- 필터 바: product_code 드롭다운 + category 탭 (TM/MECH/ELEC)
- 마스터 항목 테이블: item_order 순, 인라인 수정/비활성화
- item_type 구분 표시 (CHECK 뱃지 / INPUT 뱃지)
- 항목 추가: 모달 또는 인라인 폼 (item_type 선택 포함)
- TanStack Query v5 (useQuery + useMutation + invalidateQueries)

#### 2. 생산현황 > S/N 디테일 패널에 체크리스트 연동
- **현재 구조**: SNStatusPage → S/N 카드 클릭 → SNDetailPanel(480px 슬라이드인) → ProcessStepCard(MECH/ELEC/TMS...) 확장 → 작업자 태깅 정보
- **추가**: ProcessStepCard 확장 시 작업자 정보 아래에 **체크리스트 현황 섹션** 표시
- **API 방식**: 옵션 B — 기존 `GET /api/app/checklist/{SN}/{category}` 별도 호출 (BE 변경 0, APP과 동일 API 공유)
- **FE 추가**: `useChecklist.ts` 훅 신규 → 카드 확장 시 task + checklist 병렬 fetch
- **표시 내용**:
  - 체크리스트 완료율 (예: ✅ 12/15 완료 + 프로그레스 바)
  - 미완료 항목 리스트 (inspection_group + item_name)

#### 3. S/N 카드 레벨 체크리스트 요약 (Phase 2)
- **목적**: 카드 목록만 봐도 체크리스트 상태 확인 (예: 진행률 바 옆에 ✅ 3/3 또는 ⚠️ 2/3 아이콘)
- **구현**: BE 집계 API 신규 — `GET /api/admin/checklist/summary`
  - 파라미터: `serial_numbers` (복수 S/N)
  - SQL 한 번으로 S/N×category별 total/checked 집계
  - FE에서 progress API 호출 후 반환된 S/N 목록으로 summary API **1회 추가 호출** (총 2회)
- **우선순위**: 후순위. 디테일 패널 연동 먼저 완성 후, 필요 시 추가

### APP 트리거
- MECH/ELEC/TM 자주검사 시작 → 토스트 팝업 체크리스트 표시
- CHECK 항목: PASS/NA 버튼
- INPUT 항목: 텍스트 입력 필드 (비고와 동일 UX)
- 기존 GET/PUT API 사용 (status 타입 + item_type 분기 추가)

### 연동 흐름
```
VIEW: 마스터 CRUD (CHECK/INPUT 항목 관리)
→ APP: 자주검사 시작 → 체크리스트 팝업
→ 작업자: CHECK→PASS/NA 판정 / INPUT→텍스트 입력 + 비고 입력
→ 전항목 완료 + progress 100% = 실적확인 승인 활성화
→ VIEW 생산현황: S/N 디테일에서 체크리스트 완료 현황 확인
```

### 구현 우선순위
1. **BE**: checklist_master/record 스키마 확장 (migration) + Admin CRUD API 4개
2. **VIEW**: 체크리스트 관리 페이지 (마스터 CRUD UI)
3. **VIEW**: 생산현황 ProcessStepCard 체크리스트 연동 (옵션 B)
4. **APP**: 자주검사 토스트 팝업 (기존 API 활용)
5. **BE+VIEW**: S/N 카드 레벨 summary 집계 API (Phase 2)

### 미결정 사항
- RV-1: 단순 item_name vs BOM 기반 확장 → ~~ELEC 양식 확인 후 최종 결정~~ **ELEC 양식 수집 완료 (2026-04-09)**
- `second_judgment_required` 저장 위치: master 행마다 vs 별도 설정 테이블 (admin_settings 등)
- ~~ELEC 양식 수집 대기 중~~ **✅ 완료 — 전장외주검사성적서 3그룹 24항목 + GST 검증 7항목**
- **Sprint 57 할당**: ELEC 공정 시퀀스 변경 + 체크리스트 구현 (AGENT_TEAM_LAUNCH.md 참조)

### ELEC 양식 분석 (전장외주검사성적서)
> 소스: `+_전장외주검사성적서.xlsx` → sheet `GIAA-I S SEC (2)`
> Sprint 57 할당 (2026-04-09)

| Group | 항목 수 | 검사주체 | 비고 |
|-------|--------|---------|------|
| PANEL 검사 | 11 | ELEC 외주 전담 (2~3명) | 1차/2차 동일 인원 |
| 조립 검사 | 6 | ELEC 외주 전담 (동일) | 버너 위 배선 1차 N.A |
| JIG 검사 및 특별관리 POINT | 7 + 7(GST) | ELEC 외주 + QI | GST 담당자 별도 phase |

**ELEC 공정 시퀀스 변경**:
- INSPECTION: FINAL → freeroll (시작 시 체크리스트 팝업)
- IF_2: → FINAL (ELEC 닫기 트리거)
- 닫기 조건: 체크리스트 완료(GST 제외) + IF_2 완료
- **TM과 공통 패턴**: `checklist_ready` + `checklist_category` 응답

---

## 🟡 BUG-41 상세: PWA 업데이트 시 PIN 초기화 + 이메일 재입력 요구

> **상태**: BACKLOG (우선순위 보류, 2026-04-15 등록)
> **환경**: Chrome PWA 전용 (데스크톱/모바일 모두). iOS Safari 미사용
> **증상**:
> 1. 앱 업데이트 알림 후 reload → PIN 로그인 화면이 아닌 초기 이메일 로그인 화면으로 진입
> 2. 이메일을 전체 다시 입력해야 로그인 가능
> 3. 비밀번호 재입력 + PIN 재등록까지 매 업데이트마다 반복

### 영향 범위

- **사용자 불편**: 매 업데이트(주 1~2회)마다 전 사용자 재로그인 + PIN 재등록
- **업무 영향**: 현장 작업자가 업데이트 직후 수 분간 작업 불가
- **보안 이슈 아님**: 데이터 손실/무단 접근 없음, 단순 UX 열화

### 원인 분석 (요약)

**PWA + `flutter_secure_storage_web` 조합의 구조적 문제**
- `flutter_secure_storage_web` 9.x는 localStorage에 AES 키 + 암호화된 값을 함께 저장
- 웹에서는 "보안 저장소"라는 이름과 달리 실제 보안 이점 거의 없음 (AES 키 평문 노출)
- Flutter Web 빌드 해시 변경 시 부트스트랩 시점에 키 동기화 실패 케이스 발생
- PWA 서비스워커 업데이트 후 첫 로드 시 storage 초기화 타이밍 이슈 가능

**관련 파일 및 라인** (2026-04-15 기준)
- `frontend/lib/services/auth_service.dart:12` — `FlutterSecureStorage()` 기본 옵션
- `frontend/lib/services/auth_service.dart:20` — `_pinRegisteredKey` SecureStorage 저장
- `frontend/lib/services/auth_service.dart:349-360` — `hasPinRegistered()` / `savePinRegistered()`
- `frontend/lib/services/update_service.dart:14-39` — 버전 감지 (lastSeen 비교)
- `frontend/lib/main.dart:259-273` — AppStartup PIN 체크 분기
- `frontend/web/index.html:180-232` — SW 업데이트 토스트 (이미 구현됨)

### 제안 해결안 (Sprint 60-FE 후보)

**Task 1 — `navigator.storage.persist()` 호출**
- 효과: Chrome evict 방지
- 리스크: 없음 (순수 추가 API)
- 변경 범위: `index.html` 또는 `main.dart` 부트스트랩 1곳

**Task 2 — PIN 등록 플래그를 SecureStorage → SharedPreferences 이전**
- 효과: `flutter_secure_storage_web` 암호화 키 동기화 실패 회피
- 보안 영향: 없음 (flag는 민감정보 아님, 값 자체는 서버 검증)
- ⚠️ **리스크: 기존 사용자 1회 강제 PIN 재등록** — 마이그레이션 로직 필수 포함
  ```dart
  // auth_service.dart hasPinRegistered() 일회성 마이그레이션
  if (prefs.containsKey(_pinRegisteredKey)) {
    return prefs.getBool(_pinRegisteredKey) ?? false;
  }
  // 첫 실행 — SecureStorage에서 마이그레이션 시도
  final legacy = await _secureStorage.read(key: _pinRegisteredKey);
  final registered = legacy == 'true';
  await prefs.setBool(_pinRegisteredKey, registered);
  return registered;
  ```
- 변경 범위: `auth_service.dart` (3 메서드), `logout()` 불일치 방지 (SharedPreferences 삭제 추가)

**Task 3 — 이메일 SharedPreferences 저장 + 로그인 화면 자동 채움**
- 효과: PIN이 날아가도 이메일 자동 채움 → 재입력 부담 대폭 감소
- 보안 영향: 저위험 (이메일은 민감도 낮음)
- ⚠️ 리스크: 공용 기기에서 이전 사용자 이메일 노출 → "내 계정 기억 안 함" 토글 필요할 수 있음
- 변경 범위: `auth_service.dart` + 로그인 화면

**Task 4 — SecureStorage read 예외 graceful handling**
- 효과: 복호화 실패 시 앱 크래시/무한 로딩 방지
- ⚠️ 주의: `deleteAll()`은 금지. 단순히 `false` 반환으로 처리 (일시적 IO 에러가 영구 데이터 손실로 악화 방지)
- 변경 범위: `auth_service.dart` 각 read 메서드

### Sprint 60-FE 규모 예상

- 코드 변경: `auth_service.dart`(주요), `main.dart`(부트스트랩), `login_screen.dart`(자동 채움), `index.html`(persist 호출) — **4~5 파일**
- 신규 테스트: PWA 업데이트 수동 시나리오(staging v1→v2), 기존 사용자 마이그레이션 시나리오
- 예상 기간: 2~3일 (구현) + 3~5일 (staging 검증) = **약 1주**

### 왜 지금 보류하나

1. **변경 범위가 인증 플로우 전반** — 마이그레이션 로직 없으면 배포 당일 전사 PIN 초기화 사태 유발
2. **Regression 테스트 비용 높음** — PWA 업데이트 시나리오는 자동화 어려움, 수동 검증 필수
3. **완전 해결이 아님** — Task 1+2+3+4 모두 적용해도 refresh_token 손실 시나리오는 여전히 남음 (완화 80%, 근본 해결 아님)
4. **근본 해결 대안**: refresh_token을 httpOnly 쿠키로 이전 (Flask-JWT + CORS 설정 변경 필요, 별도 Sprint 규모)
5. **우선순위**: 체크리스트/성적서/실적 확인 기능이 더 중요 (Sprint 58/59 계열 진행 중)

### 재개 조건

다음 중 하나라도 충족 시 Sprint 60-FE로 승격:
- 사용자 민원이 다른 우선순위 항목보다 심각해짐
- 업데이트 주기가 짧아져 사용자 고통 누적
- 다른 Sprint와 함께 묶을 수 있는 기회 발생 (예: 로그인 플로우 대규모 개선 시)
- refresh_token httpOnly 쿠키 이전 계획 수립 시 통합 Sprint로 진행

### 관련 분석 기록

- 분석일: 2026-04-15 (Twin파파 + Claude Opus 4.6 세션)
- 초기 진단: 네이티브 Flutter 앱 가정 → SecureStorage Keychain 손실 → 오진
- 재진단: PWA 환경 확인 → `flutter_secure_storage_web` localStorage 구조 이슈로 확정
- 배포 환경: Chrome 전용(데스크톱/모바일), iOS Safari 미사용으로 확정

---

## 🔴 BUG-42 상세: 명판 소형 QR 접사 인식 실패

### 환경
- **대상**: OPS PWA (Chrome 전용, 모바일/태블릿)
- **QR 소스**: 제품 명판(metal nameplate)에 각인/인쇄된 소형 QR — 스티커 QR 대비 면적 작음
- **비교 조건**: 동일 명판을 iOS/Android 기본 카메라 앱으로 촬영하면 QR 문자열 정상 읽힘
- **증상**: OPS 앱 스캐너 화면에서 같은 QR을 접사/근접 촬영해도 인식 안 됨 → timeout 또는 미검출

### 원인 분석

현재 스캐너 구현(`frontend/lib/services/qr_scanner_web.dart`)은 `html5-qrcode@2.3.8` (CDN, `web/index.html` L164)를 사용하며 카메라 제약을 **최소값**만 지정:

| 항목 | 현재 값 | 필요 값 |
|---|---|---|
| 라이브러리 | `html5-qrcode@2.3.8` | `@2.3.10` 또는 네이티브 `BarcodeDetector` API 병용 |
| 디코더 | zxing WASM (기본) | BarcodeDetector (OS 네이티브 / 훨씬 정확) |
| 해상도 constraint | 미지정 → 기본 640×480~1280×720 | `width: {ideal: 1920}, height: {ideal: 1080}` |
| 포커스 constraint | 미지정 | `focusMode: 'continuous'` + advanced |
| 줌 노출 | 없음 | `getCapabilities().zoom` 기반 슬라이더 UI |
| 손전등(Torch) | 없음 | `applyConstraints({advanced:[{torch:true}]})` |
| qrbox | 200 (고정 integer) | 컨테이너의 70-80% 동적 계산 |
| experimentalFeatures | 미사용 | `useBarCodeDetectorIfSupported: true` |

기본 카메라 앱이 잘 읽는 이유:
- 센서 최대 해상도(4K/12MP) 프레임 공급
- OS 레벨 Auto Focus + Macro Focus (하드웨어)
- OS 네이티브 QR 디코더 (iOS Vision / Android ML Kit) — 저해상도·기울어진 코드에 강함
- 사용자가 핀치 줌으로 확대 가능

현재 OPS 스캐너는 이 네 가지가 모두 빠져 있어 **QR 픽셀 밀도가 낮으면 디코딩 실패**.

### 관련 파일
- `frontend/lib/services/qr_scanner_web.dart` L305-469 — `startQrScanner()`, 특히 L376-389 `configScript` 주입 블록
- `frontend/web/index.html` L164 — `html5-qrcode@2.3.8` CDN 링크
- `frontend/lib/screens/qr/qr_scan_screen.dart` — UI 레이어 (줌/Torch 버튼 추가 위치)

### ⚠️ 제약 조건 — 프레임/레이아웃 절대 불변

**카메라 스캐너 프레임(컨테이너 크기·위치·정사각형 강제·뷰파인더 크기·CSS·`qrbox` 값)은 과거 20회 이상 반복 수정되어 현재 최적값. 본 BUG-42 수정 범위에서 절대 건드리지 않음.**

금지 영역 (수정 시 regression 고위험):
- `qr_scanner_web.dart` L23-250 — CSS 주입, DOM 생성, `_forceSquareAfterCameraStart()`, MutationObserver
- `qrbox: 200` 고정값
- `qr_scan_screen.dart` 의 레이아웃/UI 위젯 배치
- `web/index.html` 의 스캐너 관련 스타일

### 제안 Sprint 61-FE 태스크 (프레임 무변 범위만)

**Task 1: BarcodeDetector API 활성화 🎯 최우선 (한 줄 추가, 프레임 영향 0)**
`qr_scanner_web.dart` L376-383 `__qrScanConfig` 에 `experimentalFeatures` 한 줄 추가:
```js
window.__qrScanConfig = {
  fps: 10,
  qrbox: 200,  // ← 그대로 유지 (프레임 불변)
  experimentalFeatures: { useBarCodeDetectorIfSupported: true }  // ← 추가
};
```
- Chrome/Edge: OS 네이티브 `BarcodeDetector` 디코더 사용 → 소형 QR 인식률 급상승
- 미지원 브라우저: 자동 zxing 폴백
- **프레임/뷰파인더 크기 불변** — 디코더만 교체됨

**Task 2: 카메라 해상도 + 연속 포커스 제약 (프레임 영향 0)**
L402 / L421 / L443 의 `facingMode` 제약을 객체로 확장:
```js
const envConstraints = {
  facingMode: 'environment',
  width:  { ideal: 1920 },
  height: { ideal: 1080 },
  advanced: [{ focusMode: 'continuous' }]
};
```
- 센서 해상도만 상승. video 요소는 이미 L31-35 / L200-206 에서 `object-fit: cover` + `width/height: 100%` 로 컨테이너에 **crop** 처리되므로 화면 프레임 크기 불변
- `_forceSquareAfterCameraStart()` + MutationObserver (L189-250) 가 혹시 모를 크기 변경을 즉시 되돌림
- `focusMode: continuous` 는 OS 카메라 레벨 설정 — UI 영향 없음

**Task 3: 자동 줌 적용 (UI 추가 없음, 프레임 영향 0)**
카메라 시작 성공 직후(`_forceSquareAfterCameraStart` 이후) 헬퍼 1개 호출:
```dart
Future<void> _applyZoomIfSupported() async {
  // MediaStreamTrack.getCapabilities().zoom 확인
  // 지원 시 advanced: [{ zoom: min + (max-min) * 0.3 }] 자동 적용
  // 미지원 시 silent skip
}
```
- 약 30% 기본 줌을 **자동 1회만** 적용 → 명판 작은 QR 디코더 인식률 상승
- 사용자 슬라이더/UI 추가 **없음** → qr_scan_screen.dart 레이아웃 무변
- 미지원 기기는 조용히 넘어감

### 제외 (프레임 영향으로 보류)

- ~~qrbox 동적 계산~~ — 뷰파인더 크기 변경. **제외**.
- ~~줌 슬라이더 UI 추가~~ — 레이아웃 변경. **제외**.
- ~~Torch 버튼 UI 추가~~ — 레이아웃 변경. **제외**.
- ~~html5-qrcode 라이브러리 업그레이드~~ — 2.3.8 → 2.3.10 미세 차이 있을 수 있음, 우선순위 낮음. Task 1+2+3 효과 부족 시에만 검토.

### 규모 추정
- Task 1: **1줄 추가**
- Task 2: 3곳 × 약 5줄 = 15줄
- Task 3: 신규 헬퍼 ~15줄 + 호출 3곳
- **전체: 약 35줄 수정**, UI/CSS/컨테이너/qrbox 전부 불변
- 작업 시간: 반나절 + 실물 명판 테스트

### 점진적 적용 권장
1. **Task 1만** 먼저 핫픽스 → 실물 명판 샘플 테스트
2. 여전히 부족하면 Task 2 추가
3. 그래도 부족하면 Task 3 추가
4. 각 단계마다 프레임/뷰파인더 시각적 regression 없는지 확인

### 검증 체크리스트
- [ ] 스캐너 뷰파인더 정사각형·크기·위치가 수정 전과 픽셀 단위로 동일
- [ ] 기존 스티커 QR 인식 속도 동등 이상
- [ ] 명판 소형 QR 인식 성공
- [ ] Chrome Desktop / Chrome Android 두 환경 확인
- [ ] `[QrScannerWeb] ★ forceSquare applied` 로그 정상 출력 (프레임 유지 확인)

### 검증
- 명판 실물 샘플 + 스티커 샘플 모두 인식 성공
- Chrome Desktop(웹캠), Chrome Android, Chrome iOS(가능 시) 세 환경에서 확인
- Regression: 기존 스티커 QR / 작업 태그 QR 인식률 동등 이상 유지

### 임시 우회책 (사용자 전달 가능)
- 명판 QR에 초점이 잡힐 때까지 카메라를 앞뒤로 움직여 포커스 유도
- 조명 밝은 곳에서 스캔
- 가능하면 명판 QR을 스티커 복사본으로도 병행 부착 (근본 대책 아님)

### 관련
- BUG-41 동일하게 PWA 카메라 스택 의존. 해결 우선순위는 **BUG-42 > BUG-41** (작업 차단 영향이 큼).

---

## 🟢 아이디어 / 메모

- **AXIS-VIEW**: React 기반 관리자 대시보드 (출퇴근, 생산 현황, KPI 등). App과 분리.
- **PWA → Native 전환**: 현재 Flutter Web(PWA) 코드는 Native 전환 시 비즈니스 로직 그대로 재사용 가능. 플랫폼 의존 코드(html5-qrcode → mobile_scanner, secure storage 등)만 조건부 import 처리.
- **공용 태블릿 시나리오**: 공장 현장 공용 기기 사용 시 로그아웃 시 localStorage 클리어 로직 필요 (현재는 미구현, 필요 시 추가)
- **model_config 조회/수정**: CLAUDE.md에 "추후"로 기록됨. Admin이 모델별 설정(has_docking, is_tms 등) 수정 가능한 UI.
- **Sprint 완료 시 공지사항 등록**: 현재 수동 (Admin 화면에서 version 필드 입력). 업데이트 팝업은 notices 테이블에 해당 버전 공지가 있을 때만 표시됨. 공지 없으면 팝업 안 뜸. 자동화 옵션: A) CLAUDE.md 버전 업데이트 절차에 공지 생성 단계 추가 / B) 배포 스크립트에 API 호출 / C) CI/CD hook (추후)
- **QR 목록 contract_type / sales_note 필드 추가 검토**:
  - `contract_type`: Excel N열 "신규여부" (양산/신규/계약변경). step1_extract.py에서 추출은 됨, DB 컬럼 미추가 + step2 UPSERT 미포함
  - `sales_note`: Excel CJ열 "특이사항(영업)". 마찬가지로 추출만, DB 미적재
  - 작업 필요: ① plan.product_info ALTER TABLE ② step2_load.py UPSERT 추가 ③ qr.py SELECT 추가
  - 활용성 검토 필요: VIEW QR관리 페이지에서 이 정보를 어떻게 활용할지 (필터? 표시만?) 확인 후 진행
  - OPS_API_REQUESTS.md #6에 등록됨
- ~~**PWA 버전 업데이트 알림 토스트**~~ → ✅ Sprint 26 전체 완료 (Task 1: SW 업데이트 토스트, Task 2~5: UpdateService + UpdateDialog + HomeScreen 연동 — 버전별 공지 팝업 정상 동작 확인)
- ~~**QR 스캔 UX 개선 3건**~~ → ✅ Sprint 40-A 전체 완료 (2026-03-27)
  - ① QR 프레임 축소: qrbox 200→160, cameraSize 350→240 + BUG-29 수정
  - ② DOC_/LOC_ 자동접두어: prefixText + validator + submit 결합
  - ③ 오늘 태깅 드롭다운: BE today-tags API + FE _loadTodayTags() + BUG-25 수정 (ApiService.get() 반환 타입 불일치)
- ~~**테스트 DB 분리**~~ → ✅ Sprint 39 완료 (2026-03-26). `TEST_DATABASE_URL` 환경변수 분리, `.env.test` 자동 로딩, 운영 DB 하드코딩 제거, Sprint 39-fix regression 118→0 해결
- ~~**비활성 사용자 자동 삭제 + 협력사 유저 삭제 기능**~~ → ✅ Sprint 40-C 전체 완료 (2026-03-27)
  - ✅ Migration 040/041: workers에 is_active, deactivated_at, last_login_at + alert_type_enum
  - ✅ BE: worker.py 5함수 + auth login is_active 체크 + last_login_at 갱신
  - ✅ BE: admin API 3개 + manager request-deactivation API 1개
  - ✅ BE: 비활성화 요청 시 admin 앱 알림 + 이메일 알림 동시 발송
  - ✅ FE: Admin 옵션 — 비활성 사용자 관리 섹션 (30일 미로그인 + 비활성화/재활성화)
  - ✅ FE: Admin 옵션 레이아웃 8섹션 재배치
  - 🔲 FE: Manager 위임 화면 — 자사 유저 "비활성화 요청" 버튼 (미구현)
  - 테스트 9/9 passed

---

## 📋 Sprint 이력 요약

| Sprint | 주요 내용 | 테스트 |
|--------|----------|--------|
| 1 | 인증 + DB 기반 | 8 PASSED |
| 2 | Task 핵심 플로우 | 21 PASSED |
| 3 | 공정 검증 + 알림 | 21 PASSED |
| 4 | 관리자 + 퇴근시간 자동감지 | 31 PASSED |
| 5 | 보안 + PWA + 이메일 + 잔여 모델 | 59 PASSED |
| 6 | Task 재설계 + 네이밍 + Admin 옵션 | 157 PASSED, 20 SKIP |
| 7 | 실데이터 + 통합 테스트 | 356 PASSED, 19 SKIP |
| 8 | Admin API 보완 + UX + 비밀번호 찾기 | 271 PASSED, 19 SKIP |
| 9 | Pause/Resume + 근무시간 관리 | 318 PASSED, 19 SKIP |
| 10 | 수동 검증 + 버그 수정 | 456+ PASSED, 19 SKIP |
| 11 | GST Task + 대시보드 + Checklist | 44 PASSED, 1 SKIP |
| 11 핫픽스 | 타입 불일치, 필터링, 협력사 정보, UTC→KST | 수동 수정 4건 |
| 12 | PIN + 출퇴근 + QR 카메라 | 22 PASSED |
| 12 핫픽스 | PIN 자동로그인 분기 로직 | 수동 수정 4건 |
| 12 배포 | Netlify PWA + Railway API 배포 | 전체 API 동작 확인 |
| 13 | WebSocket flask-sock 마이그레이션 + BUG-2/4 수정 | 18 PASSED, 배포 완료 |
| BUG-5 핫픽스 | QR 카메라 위치(left+width) + 스캔 영역(순수 JS config) + 스플래시 스크린 | 19 PASSED, 웹 검증 완료 |
| 14 | 작업자명 표시(Task Detail + GST 대시보드) + QR 스캔 영역 정사각형 | 28 PASSED, 배포 완료 |
| 14 핫픽스 | BUG-7/8/9/10/11: 휴게시간 자동재개 + 작업시간 계산 + force-close + QR 스크롤 + Location QR | 76 PASSED, 1 SKIP, 배포 완료 |
| 15 | BUG-12 다중작업자 Join + BUG-11 재수정 + MH/WH 로깅 | 28 PASSED, 배포 완료 |
| 16 | Admin prefix 로그인 + BUG-13/14/15 + QR 카메라 정사각형 | 9 PASSED, 배포 완료 |
| 16.1 | v1.1.0 버전 관리 + System Online 실연동 + BUG-16/17 수정 | 빌드 에러 0건, 배포 완료 |
| 16.2 | 담당공정 설정 이동 (홈→개인설정) + BUG-16/17 배포 | 빌드 에러 0건, 배포 완료 |
| 17 | 출퇴근 분류 체계 (work_site + product_line) v1.2.0 | 13 PASSED, 배포 완료 |
| 18 | 협력사별 S/N 진행률 뷰 v1.3.0 | 10 PASSED, 배포 완료 |
| 19-A | 보안: Refresh Token Rotation + Device ID | 6 PASSED + 28 회귀, 배포 완료 |
| 19-B | 보안: DB 기반 Refresh Token 관리 + 탈취 감지 | 10 PASSED, 배포 완료 |
| 19-D | 보안: Geolocation GPS 위치 검증 (출퇴근) | 11 PASSED, 배포 완료 |
| 19-E | VIEW용 Admin 출퇴근 API 3개 (BE) | 8 PASSED |
| 20-A | 신규 가입 시 Admin 이메일 알림 | 5 PASSED |
| 20-B | 공지사항 탭 (BE+FE) | 6 PASSED |
| 21 | QR Registry 목록 API (BE) + 날짜 필터 | ✅ |
| 21-ETL | ETL → axis-core-etl repo 분리 | ✅ 분리 완료 |
| 22-A | Email Verification 개선 (Admin 알림 시점 + 재전송 API) | ✅ |
| 22-A보완 | 인증 3분 만료, FE 연동, 승인필터, PM role | ✅ v1.6.1 |
| 22-B | GPS enableHighAccuracy + DMS 변환 헬퍼 | ✅ |
| 22-C | Manager 권한 위임 (같은 회사 is_manager 부여) | ✅ v1.6.2 |
| 22-D | 공지수정 UI + Admin 간편로그인 + ETL 변경이력 API | ✅ v1.6.3 |
| 23 | Manager 권한 위임 화면 + 홈 메뉴 재구성 | ✅ v1.7.0 |
| 24 | QR actual_ship_date + Manager 자사 필터 + workers 권한 완화 | ✅ v1.7.1 |
| 24 핫픽스 | BUG-18/19/20/21: GST 출퇴근 + 비밀번호 찾기 + 로그인 에러 분리 + 404 메시지 | ✅ |
| 22-E | conftest.py 운영 데이터 5테이블 백업/복원 완성 (product_info + qr_registry) | ✅ |
| 25 | BUG-22 Logout Storm 수정 (FE 3중 방어 + BE jwt_optional) | ✅ v1.7.2 |
| 26 | PWA 업데이트 알림 토스트 + 업데이트 팝업 + conftest 보호 강화 | ✅ v1.7.3 |
| 27 | 단일 액션 Task (task_type 컬럼 + Docking/출하완료) | ✅ v1.7.4 (migration 022 적용) |
| 28 | AXIS-VIEW 권한 데코레이터 재정비 (gst_or_admin + view_access) | ✅ v1.7.4~v1.7.5 |
| 27-fix | Task Seed Silent Fail 디버깅 — 로깅 강화 + SINGLE_ACTION UI | ✅ v1.7.5 |
| 29 | 공장 API — 생산일정 #10 + 주간 KPI #9 (BE only) | ✅ v1.7.6 |
| 29 보완 | PM role + 이름 로그인 + ship_plan_date + per_page 500 | ✅ v1.7.7 |
| 29-fix | BUG-24 재발 방지 — ensure_schema 자동 검증 + migration 023 | ✅ v1.7.8 |
| 30 | DB Connection Pool 도입 — 동시 접속 안정화 (33파일 175건 변환) | ✅ v1.8.0 |
| 30-B | DB Pool TCP keepalive + health check + Procfile 튜닝 | ✅ v1.8.0 |
| 31A | 다모델 지원 — DUAL L/R, DRAGON MECH, PI 분기, workers RESTRICT | ✅ v1.9.0 |
| 31B | QR 기반 태스크 필터링 — DUAL L/R 분리 표시 (BE+FE) | ✅ v1.9.0 |
| 32 | 사용자 행위 트래킹 — app_access_log + analytics API 4개 + 30일 정리 | ✅ v1.9.0 |
| 31C | PI 검사 협력사 위임 — 가시성 분기 + DRAGON PI 활성화 | ✅ v2.0.0 |
| 33 | 생산실적 API — O/N 단위 실적확인 + 월마감 (production.py 4개) | ✅ v2.0.0 |
| 34 | admin_settings 레지스트리 리팩터링 + workers 필터 + PI 설정 API | ✅ v2.0.0 |
| 34-A | Admin 옵션 PI 위임 설정 UI — Chip 추가/삭제 (FE) | ✅ v2.0.0 |
| 35 | 근태 기간별 출입 추이 API — 단일 SQL 집계 + trend 엔드포인트 | ✅ v2.0.0 |
| 36 | TM 실적확인 TANK_MODULE only + 공정 종료일 기준 + module_end ETL | ✅ v2.0.0 |
| 37 | 혼재 O/N 실적확인 partner별 분리 — mixed + partner_confirms | ✅ v2.1.0 |
| 37-A | TM 가압검사 옵션 — tm_pressure_test_required settings 기반 progress/알람 | ✅ v2.1.0 |
| 37-B | S/N별 실적확인 + TM 혼재 제거 + 탭별 End 필터 (#38) | ✅ v2.1.0 |
| BUG-27 | monthly-summary 500 에러 — SUM(sn_count) 참조 (DROP된 컬럼) | ✅ 수정 완료 (2026-03-24) |
| BUG-28 | tm_pressure_test_required PUT 400 — SETTING_KEYS 등록 누락 | ✅ 수정 완료 (2026-03-24) | `admin.py` SETTING_KEYS에 `tm_pressure_test_required` bool 추가. DB에는 존재했으나 레지스트리 미등록 |
| 38 | product/progress API last_worker + last_activity_at 필드 추가 | ✅ 완료 (2026-03-27) | progress_service.py 서브쿼리 추가 + 테스트 16/16 passed. VIEW Sprint 18 연동 |
| 38-B | product/progress API last_task_name + last_task_category 추가 | ✅ 완료 (2026-03-27) | progress_service.py 서브쿼리 확장 + 테스트 4/4 passed (기존 8건 regression 0) |
| 40-A | QR 스캔 UX 개선 — 프레임 축소 + DOC_ 자동접두어 + 오늘 태깅 드롭다운 | ✅ 완료 (2026-03-27) | BE: today-tags API 5/5 passed. FE: qrbox 160, prefixText, 드롭다운 UI |
| #46 | 상세뷰 workers 매핑 — task_id fallback + serial_number 기준 조회 | ✅ 완료 (2026-03-27) | work.py 2단계 매핑 (task_id 1차 + category+ref fallback). 테스트 5/5 passed |
| 40-C | 비활성 사용자 관리 — soft delete + admin 승인 + manager 요청 | ✅ 완료 (2026-03-27) | migration 040/041 + worker.py 5함수 + auth login is_active 체크 + API 4개 + 앱/이메일 알림. 테스트 9/9 passed |
| 40-C FE | Admin 옵션 레이아웃 재배치 + 비활성 사용자 관리 UI | ✅ 완료 (2026-03-27) | 8섹션 순서 변경 + 30일 미로그인 목록 + 비활성화/재활성화 버튼 + 빌드 성공 |
| 41 | 작업 릴레이 + Manager 재활성화 | ✅ 완료 (2026-03-30) | finalize 파라미터 + 릴레이 재시작 + reactivate-task API + FE 종료 팝업. 테스트 18/19 passed (1 xfail) + regression 71 passed |
| 41-A | 작업 완료 토스트 + 릴레이 다이얼로그 + 재시작 UI + 재완료 허용 | ✅ 완료 (2026-03-30) | Task 0~4: pop(result) + 릴레이 다이얼로그 + 재시작 UI + _worker_restarted_after_completion(). TC-41A-01~21 |
| 41-B | 릴레이 미완료 task 자동 마감 + Manager 알림 | ✅ 완료 (2026-03-30) | FINAL task 트리거 + orphan 4시간 스케줄러 + RELAY_ORPHAN alert. 테스트 14/14 passed |
| 39 | 테스트 DB 분리 — conftest.py 리팩토링 | ✅ 완료 (2026-03-26) | TEST_DATABASE_URL 환경변수 분리, .env.test 자동 로딩, 운영 DB 하드코딩 제거, seed_test_data fixture, test_sprint39_db_isolation.py 10/10 통과 |
| 39-fix | Regression 수정 — 118 failed → 0 failed | ✅ 완료 (2026-03-27) | BE: factory.py finishing_plan_end→ship_plan_date, production.py module_end→module_start. TEST: 18개 파일 수정 (MM→MECH, worker_id 819→seed admin, task seed 기대값, GAIA-I DUAL→SINGLE, confirmable→all_confirmable 등). 최종 714 passed / 14 skipped |

---

## 🔷 Sprint 40 계획 (병렬 3트랙)

> 등록일: 2026-03-26
> 상태: Track A/B/C 전체 완료 (2026-03-27)
> 선행: Sprint 38 ✅ 완료

### Track A: QR 스캔 UX 개선 3건 (APP FE + BE 1개)

| # | 개선 | 변경 범위 | 난이도 |
|---|------|----------|--------|
| A-1 | QR 프레임 크기 축소 | `qr_scanner_web.dart` qrbox값 1줄 + `qr_scan_screen.dart` cameraSize 1줄 | 매우 낮음 |
| A-2 | DOC_ 자동 접두어 | `qr_scan_screen.dart` — prefixText + validator/submit 로직 수정 | 낮음 |
| A-3 | 오늘 태깅 QR 드롭다운 | BE: `work.py` API 1개 + `work_start_log.py` 쿼리 1개 / FE: 드롭다운 UI | 중 |

⚠️ **카메라 관련 주의**: BUG-5~BUG-23까지 20회 이상 카메라 수정 이력 있음. 정사각형 강제 로직(MutationObserver, _forceSquareAfterCameraStart, CSS aspect-ratio 등) 절대 수정 금지. qrbox 정수값과 cameraSize clamp 범위만 변경.

### Track B: VIEW Sprint 18 — S/N 카드뷰

- Sprint 38의 last_worker/last_activity_at 필드를 FE에서 카드뷰에 연결
- VIEW FE만 변경 (BE 변경 0건)

### Track C: 비활성 사용자 관리 — 프롬프트 작성 완료 ✅

- BE: `workers.last_login_at` 기반 30일 미로그인 감지 API + 삭제 대기 목록 + admin 승인 API
- BE: 협력사 manager 자사 유저 삭제 요청 API
- VIEW: 권한관리 페이지에 삭제 대기 목록 + 승인/반려 UI (별도 Sprint)
- soft delete (is_active=FALSE)
- **최종 admin 승인 후 삭제** (즉시 삭제 아님)
- Migration 040: workers에 `is_active`, `deactivated_at`, `last_login_at` 컬럼 추가
- ⚠️ `app_access_log`는 30일 보관 한계 → `workers.last_login_at`으로 판단
- 📋 프롬프트: `AGENT_TEAM_LAUNCH.md` Sprint 40-C 섹션 참조

### Sprint 41: 작업 릴레이 + Manager 재활성화 — 프롬프트 작성 완료 (2026-03-30)

- **문제**: 판넬 작업 등 1개 task를 여러 작업자가 순차 교대 시, 유저1 종료 → task 닫힘 → 유저2 시작 불가
- **해결**: "내 작업 종료" (finalize=false, task 열린 상태) vs "task 완료" (finalize=true, task 닫힘) 분리
- FE: 종료 버튼 → "다음 작업자가 이어서 작업하나요?" 팝업 (예/아니오)
- BE: complete_work() finalize 파라미터 + start_work() 릴레이 재시작 허용
- Manager/Admin: reactivate-task API (실수 완료 복구)
- 하위 호환: finalize 기본값 true → 기존 FE 미업데이트 시에도 정상 동작
- 📋 프롬프트: `AGENT_TEAM_LAUNCH.md` Sprint 41 섹션 참조

### Sprint 40 이후 대기

| 작업 | 선행 조건 |
|------|----------|
| Sprint 41 (작업 릴레이 + 재활성화) | 프롬프트 작성 완료 ✅ |
| 체크리스트 BE (스키마 + CRUD) | ELEC 양식 수집 완료 |
| VIEW Sprint 20 (체크리스트 관리 UI) | 체크리스트 BE 완료 ✅ |
| QR contract_type / sales_note | 활용성 검토 확정 |

---

## 운영 / 릴리스 루틴

### RULE-01 — Sprint 완료 시 FE 재빌드·재배포 의무화

**배경**
- 2026-04-15: 사용자 화면에 `v2.8.1` 표시, 코드상 git 버전은 `v2.9.2` (Sprint 59-BE까지 반영됨).
- 원인: Sprint 58-BE / 59-BE가 **백엔드 전용** 변경이라 판단해 `flutter build web`을 돌리지 않음.
- 하지만 `frontend/lib/utils/app_version.dart`의 `AppVersion.version` 문자열은 **매 sprint에서 FE 파일로 수정**되므로, FE 재빌드 없이 배포하면 버전 문구가 화면에 반영되지 않음.
- PWA 특성상 서비스워커는 새 빌드 해시가 감지되어야 `controllerchange` → 업데이트 토스트 → `window.location.reload()` 흐름이 동작 → **빌드·배포 공백 = 업데이트 토스트 미발생**.

**규칙**
모든 sprint (BE / FE / VIEW 종류 불문) 머지/완료 시 다음 순서 강제:

1. `frontend/lib/utils/app_version.dart`의 `version` / `buildDate` 업데이트 (sprint 담당자 책임)
2. `cd frontend && flutter build web --release`
3. Netlify 배포 트리거 (CI auto 또는 수동 업로드)
4. 배포 후 Chrome PWA에서 업데이트 토스트 수신 → 새로고침 → 버전 문구 확인
5. 서비스워커 캐시 문제 의심 시: DevTools → Application → Storage → Clear site data

**체크포인트**
- Sprint 완료 PR 머지 전에 `app_version.dart` diff 반드시 포함
- CI에 `flutter build web --release` 에러 0건 게이트 유지
- BE-only sprint라도 위 루틴은 동일하게 적용 — **버전 문구 싱크가 우선**

**현재 필요 조치 (v2.9.2 기준)**
- [x] `flutter build web --release` 실행 (v2.9.3, 2026-04-16)
- [x] Netlify 재배포 (v2.9.3)
- [ ] 사용자 Chrome PWA에서 하드 리프레시 (Cmd/Ctrl + Shift + R) 또는 site data clear
- [ ] 화면 하단 버전 문구가 `G-AXIS OPS v2.9.3`으로 뜨는지 확인

**관련**
- BUG-41 (PWA PIN 로그인 유실) — 동일 PWA 업데이트 플로우 의존. 빌드·배포 루틴 정착이 재현 디버깅의 선행 조건.
- `frontend/web/index.html` L180-232 — `controllerchange` → `showUpdateToast()` → `window.location.reload()` 구현 (이미 존재, 새 빌드 해시 트리거가 없으면 무용지물).

---

## 🔴 BUG-44 상세: OPS 미종료 작업 목록 0건 반환

**현상**
- OPS Admin 계정: `/admin/tasks/pending` → `{"tasks":[], "total":0}`
- OPS Manager(C&A): `/admin/tasks/pending?company=C%26A` → 동일 0건
- VIEW(React)에서는 동일 S/N의 진행 중 작업 정상 표시

**원인 규명 (2026-04-17)**

`get_pending_tasks()` (admin.py L1721)의 INNER JOIN이 근본 원인:

```sql
FROM app_task_details t
JOIN workers w ON t.worker_id = w.id   -- ← worker_id가 전부 NULL → 0건
```

진단 과정:
1. ✅ DB 정상 — is_admin/is_manager 값 확인됨
2. ✅ v2.9.4 배포 확인
3. ✅ API 호출 정상 — DevTools에서 pending 엔드포인트 응답 확인 (빈 배열)
4. 🔑 `SELECT ... FROM app_task_details WHERE started_at IS NOT NULL AND completed_at IS NULL` → 20건+ 존재 (worker_id **전부 NULL**)
5. 🔑 `SELECT ... FROM app_task_details t JOIN workers w ON t.worker_id = w.id WHERE started_at IS NOT NULL AND completed_at IS NULL` → **0건**

**근본 원인**: `start_task()` (task_detail.py L384-419)는 `started_at`만 UPDATE하고 `worker_id`는 세팅하지 않음. 작업자 추적은 `work_start_log` 테이블에서 별도 관리. VIEW는 `work_start_log`에서 JOIN하므로 정상 작동.

**수정** (Claude × Codex 교차 검증 합의, 2026-04-17):
- FK 매칭 LATERAL JOIN — `wsl2.task_id = t.id` (DDL: `REFERENCES app_task_details(id)`)
- `task_id_ref` 단독 매칭 금지 — VARCHAR라 S/N 간 중복 가능 (unsafe)
- `AND (w.company = %s OR %s IS NULL)` **유지** — 제거 시 FNI/BAT MECH 권한 분리 깨짐
- 파라미터 바인딩 `(company, company)` 유지, API 응답 형식 무변경
- 상세 설계는 `AGENT_TEAM_LAUNCH.md` BUG-44 섹션 + `HANDOVER_BUG44.md` 참조
