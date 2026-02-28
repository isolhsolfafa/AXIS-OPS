# AXIS-OPS 백로그

> 마지막 업데이트: 2026-02-28 (Sprint 12 완료, 배포 완료, BUG-2/3/4 분석 완료, BUG-6 수정 완료)
> 이 파일은 보류/재검토/계획/아이디어를 한 곳에서 관리합니다.
> 완료된 항목은 PROGRESS.md로 이동합니다.

---

## 🔴 지금 진행 중 / 미해결

| ID | 항목 | 상태 | 비고 |
|----|------|------|------|
| BUG-1 | QR 카메라 권한 팝업 가려짐 | 🔧 수정 중 | DOM 오버레이(z-index:9999)가 브라우저 권한 팝업을 가림. getUserMedia 선행 호출 방식으로 수정 진행 |
| BUG-2 | WebSocket 프로토콜 불일치 | 🔧 Sprint 13 (주말) | FE: raw WebSocket → BE: Flask-SocketIO 프로토콜 불일치. **수정 방안**: BE를 `flask-sock`(raw WS)으로 교체, FE 변경 없음. `socket_io_client` Flutter Web 이슈(#128) 회피. 상세: `SPRINT_13_PLAN.md` |
| BUG-3 | 출퇴근 버튼 퇴근 후 비활성화 | 🔍 분석 완료 | BE는 당일 다중 in/out 쌍 지원(카운팅 로직), 그러나 FE에서 `checked_out` 상태가 종료 상태로 처리되어 재출근 버튼 비활성화됨. FE 상태 머신에 재출근 플로우 추가 필요. 일일 리셋은 KST 자정 기준 정상 동작 |
| BUG-4 | 알림/알람 실시간 전달 안됨 | 🔍 분석 완료 (BUG-2 종속) | **근본 원인**: 1단계 리마인더가 `create_alert()`만 호출하여 DB 저장만 됨 → WebSocket broadcast 미호출. 추가로 BUG-2(프로토콜 불일치)로 실시간 전달 경로 자체가 끊김. **수정**: BUG-2 해결 + `scheduler_service.py`에서 `create_and_broadcast_alert()` 사용으로 변경. 3단계 에스컬레이션 익일 기준은 설계대로 정상 |
| BUG-5 | QR 카메라 프레임 벗어남 | ✅ 수정 완료 | **근본 원인**: `ensureScannerDiv()`가 `containerRect` 없이 호출되어 하드코딩 위치(top:100px, 화면 78%) 사용 → Flutter 카메라 Container와 불일치. **수정**: `qr_scan_screen.dart`에서 `_cameraContainerKey`로 컨테이너 좌표 계산 → 서비스 레이어 통해 `ensureScannerDiv(containerRect)` 전달. borderRadius 12px 일치. `updatePosition()` 함수 추가(스크롤 대응) |
| BUG-6 | 협력사 task 리스트에 작업자명 미표시 | ✅ 수정 완료 | BE `work.py`: task 목록 API에 `worker_name` 필드 추가 (workers 테이블 JOIN). FE `task_item.dart`: `workerName` 필드 추가. FE `task_management_screen.dart`: 카테고리 행에 작업자 아이콘+이름 표시. GST `gst_products_screen.dart`는 기존에 이미 worker_name 표시 구현됨 (시작된 작업만 표시 — 정상) |

---

## 🟡 재검토 (Review Needed)

보류해둔 항목. 다음 Sprint 기획 시 우선 검토.

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

## 🔵 추후 구현 (Phase 로드맵)

CLAUDE.md Phase 계획 기반. 시급도순.

### Phase A 잔여: 생체인증
- **내용**: 지문/FaceID — WebAuthn API (HTTPS + Flutter Web JS interop)
- **현재**: Sprint 12에서 메뉴 UI만 생성 + "추후 오픈 예정" 안내
- **의존성**: PWA 배포(HTTPS) 완료 ✅

### Phase B 잔여: Admin 출퇴근 대시보드
- **내용**: 협력사 출퇴근 현황 조회 (당일 + 월간 집계)
- **결정**: App에서 제외 → AXIS-VIEW (React 대시보드)에서 구현
- **필요 API**: GET /api/admin/hr/attendance/dashboard, /monthly
- **의존성**: hr.partner_attendance 테이블 (Sprint 12에서 생성)

### Phase B 잔여: GST 근태 확장
- **내용**: hr.gst_attendance 테이블은 Sprint 12에서 생성, API/UI 미구현
- **용도**: 그룹웨어 RDB 연동 or 동기화
- **시기**: 미정 (그룹웨어 연동 계획 수립 후)

### Phase C: BOM 검증
- **내용**: product_bom 테이블 + bom_checklist_log
- **관련**: RV-1 (checklist 스키마 재검토)과 연결될 수 있음
- **시기**: checklist 스키마 확정 후

### WebSocket 실시간 통신 정식 구현
- **내용**: 현재 FE raw WebSocket과 BE Flask-SocketIO 간 프로토콜 불일치 → 정식 연동
- **방안 A**: FE에 `socket_io_client` 패키지 도입 (Flutter Web 호환)
- **방안 B**: BE에 raw WebSocket 엔드포인트 추가 (`/ws` → pure WebSocket)
- **현재 임시 조치**: reconnect 최대 2회, 간격 10초로 축소 (에러 로그 최소화)
- **시기**: 실시간 알림/푸시 기능 필요 시

### QR ETL 자동화 파이프라인 + QR 라벨 관리 페이지
- **내용**: ETL 파이프라인을 Git 기반 Cron으로 자동 실행 → DB 적재 → QR 이미지 자동 생성 → QR 라벨 다운로드 페이지 상시 최신화
- **목적**: 생성된 QR 이미지를 설비에 스티커로 부착 (현장 운영용)
- **현재 상태**:
  - ETL 모듈: `/Users/kdkyu311/dev/my_app/test_server/etl_pipeline/` (수동 실행)
  - QR 라벨 관리 페이지: `/Users/kdkyu311/dev/my_app/test_server/static/qr_download.html` (로컬 Flask 서버)
  - API: `/api/qr/list`, `/api/qr/image/{filename}`, `/api/qr/download/{filename}`, `/api/qr/batch-download`
- **필요 작업**:
  1. GitHub Actions 또는 서버 Cron으로 ETL 자동 실행 스케줄 구성
  2. QR 라벨 다운로드 페이지를 Railway 또는 별도 서버에 배포 (상시 접근 가능)
  3. 신규 제품 등록 시 QR 이미지 자동 생성 + DB 반영
  4. QR 이미지 출력/인쇄 기능 (스티커 규격 맞춤)
- **참고**: ETL_MODULE_GUIDE.md 참조
- **시기**: 미정

### Geolocation 기반 접속 보안 (2차 보안)
- **내용**: 사용자 위치정보(GPS)를 확인하여 허용 범위 내에서만 앱 사용 가능
- **배경**: 1차 보안으로 IP 화이트리스트(내부망 제한) 예정, 2차 보안으로 위치정보 검증 추가
- **구현 방안**:
  1. FE: `navigator.geolocation.getCurrentPosition()` → 출근/QR스캔/Task 시작 시 위치 좌표 전송
  2. BE: 허용 좌표 기준점 + 반경(m) 비교 → 범위 밖이면 차단
  3. Admin 설정 화면: 허용 위치 기준점(위도/경도) + 허용 반경(m) 설정 가능
- **필요 작업**:
  - `admin.app_settings` 또는 별도 테이블에 `allowed_lat`, `allowed_lng`, `allowed_radius_m` 컬럼
  - Admin Settings UI에 지도 기반 위치 선택 or 좌표 직접 입력
  - FE 미들웨어: 위치 권한 요청 + 주기적 위치 확인
  - BE API: 위치 검증 엔드포인트 or 기존 API에 위치 파라미터 추가
- **참고**: 공장 GPS 좌표 사전 확인 필요, 실내 GPS 정확도 한계 고려 (Wi-Fi 기반 보완 가능)
- **시기**: IP 화이트리스트 구축 후

### defect 스키마
- **내용**: 불량 분석, 추적, 리포트 (QMS 연동)
- **시기**: 미정

---

## 🟢 아이디어 / 메모

- **AXIS-VIEW**: React 기반 관리자 대시보드 (출퇴근, 생산 현황, KPI 등). App과 분리.
- **PWA → Native 전환**: 현재 Flutter Web(PWA) 코드는 Native 전환 시 비즈니스 로직 그대로 재사용 가능. 플랫폼 의존 코드(html5-qrcode → mobile_scanner, secure storage 등)만 조건부 import 처리.
- **공용 태블릿 시나리오**: 공장 현장 공용 기기 사용 시 로그아웃 시 localStorage 클리어 로직 필요 (현재는 미구현, 필요 시 추가)
- **model_config 조회/수정**: CLAUDE.md에 "추후"로 기록됨. Admin이 모델별 설정(has_docking, is_tms 등) 수정 가능한 UI.

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
