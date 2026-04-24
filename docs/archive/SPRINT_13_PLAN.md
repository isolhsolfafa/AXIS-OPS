# Sprint 13: WebSocket 정합성 수정 + 알림 실시간 전달 복원

> 기간: 2026-03-01 ~ 03-02 (주말)
> 목표: BUG-2 (WebSocket 프로토콜 불일치) + BUG-4 (알림 실시간 전달 안됨) 해결

---

## 1. 배경

### 현재 문제
- **FE**: `web_socket_channel` (raw WebSocket) → `wss://domain/ws?token=xxx`
- **BE**: Flask-SocketIO → `/socket.io/` 프로토콜
- **결과**: 프로토콜 불일치로 연결 자체가 불가. 모든 실시간 기능 작동 안함

### 해결 방안: BE를 `flask-sock`으로 교체
- `socket_io_client`의 Flutter Web 이슈 (#128) 회피
- FE 코드 변경 0건 (이미 PWA에서 검증된 raw WebSocket 유지)
- BE에 FE가 기대하는 `/ws` 엔드포인트를 만들어줌

---

## 2. 변경 파일 목록

### BE 변경 (6개 파일)

| # | 파일 | 변경 내용 |
|---|------|---------|
| 1 | `requirements.txt` | `Flask-SocketIO>=5.3`, `eventlet>=0.33` 제거 → `flask-sock` 추가 |
| 2 | `Procfile` | `--worker-class eventlet` → `--worker-class gthread --threads 4` |
| 3 | `app/__init__.py` | SocketIO 초기화 제거 → Sock 초기화 + `/ws` 라우트 등록 |
| 4 | `run.py` | `socketio.run()` → `app.run()` |
| 5 | `app/websocket/events.py` | **전체 리라이트** (핵심) |
| 6 | `app/services/scheduler_service.py` | `create_alert()` → `create_and_broadcast_alert()` (3곳) |

### 추가 수정

| # | 파일 | 변경 내용 |
|---|------|---------|
| 7 | `app/websocket/__init__.py` | `register_events(socketio)` → 새 초기화 함수 |
| 8 | `tests/backend/test_websocket.py` | Flask-SocketIO test_client → 새 테스트 방식 |

### FE 변경: 0개
- `websocket_service.dart` — 그대로 (raw WebSocket)
- `constants.dart` — 그대로 (`wss://domain/ws`)
- `home_screen.dart`, `alert_provider.dart` — 그대로

---

## 3. events.py 리라이트 상세

### 현재 구조 (Flask-SocketIO)
```
socketio_instance → 글로벌 SocketIO 객체
register_events(socketio) → @socketio.on("connect/disconnect/join/leave") 데코레이터
emit_task_completed() → socketio_instance.emit("task_completed", broadcast=True)
emit_process_alert() → socketio_instance.emit("process_alert", room=room)
emit_new_alert() → socketio_instance.emit("new_alert", room=room)
```

### 새 구조 (flask-sock raw WebSocket)
```
ConnectionRegistry → thread-safe dict
  - connections: { ws_id: { ws, worker_id, role } }
  - rooms: { "worker_1": [ws_id_a], "role_MECH": [ws_id_b, ws_id_c] }

ws_handler(ws) → /ws 라우트 핸들러
  - query param에서 JWT 토큰 추출
  - worker_id, role 파싱 → room 자동 등록
  - 메시지 수신 루프 (ping/pong 처리)
  - disconnect 시 registry 정리

emit_task_completed() → registry에서 broadcast (시그니처 동일)
emit_process_alert() → registry에서 room별 전송 (시그니처 동일)
emit_new_alert() → registry에서 worker room 전송 (시그니처 동일)
```

### 메시지 포맷 (FE 기존 방식 유지)
```json
{ "event": "new_alert", "data": { "alert_id": 1, "message": "..." } }
```

### Thread-Safety
- `threading.Lock()` 으로 connections/rooms dict 보호
- gunicorn `gthread` 워커에서 여러 스레드가 동시 접근 가능

---

## 4. scheduler_service.py 변경

### 변경 전 (3곳)

```python
# task_reminder_job (line 180)
create_alert(alert_type='TASK_REMINDER', ...)

# shift_end_reminder_job (line 217)
create_alert(alert_type='SHIFT_END_REMINDER', ...)

# task_escalation_job (line 259)
create_alert(alert_type='TASK_ESCALATION', ...)
```

### 변경 후

```python
from app.services.alert_service import create_and_broadcast_alert

# task_reminder_job
create_and_broadcast_alert({
    'alert_type': 'TASK_REMINDER',
    'message': ...,
    'serial_number': ...,
    'qr_doc_id': ...,
    'target_worker_id': ...,
})
```

→ `create_and_broadcast_alert()`는 DB 저장 + WebSocket broadcast를 한번에 처리

---

## 5. 의존성 맵 (영향도 분석)

```
events.py (변경)
├── alert_service.py (L53: from app.websocket.events import emit_new_alert, emit_process_alert)
│   ├── admin.py (L18,89: create_and_broadcast_alert → alert_service → events.py)
│   └── scheduler_service.py (변경: create_alert → create_and_broadcast_alert)
├── websocket/__init__.py (L9: from events import register_events)
└── app/__init__.py (L47: from events import register_events)

FE consumers (변경 없음, 검증 필요):
├── websocket_service.dart → wss://domain/ws 연결, JSON 메시지 파싱
├── home_screen.dart → WebSocket 초기화, 휴게시간 이벤트 구독
├── alert_provider.dart → new_alert, process_alert, duration_alert 구독
├── break_time_popup.dart → BREAK_TIME_PAUSE 이벤트
└── break_time_end_popup.dart → BREAK_TIME_END 이벤트
```

---

## 6. 테스트 체크리스트

### Phase 1: 단위 테스트 (코딩 직후)

| # | 테스트 | 검증 내용 | 우선순위 |
|---|--------|---------|----------|
| T-01 | ConnectionRegistry 생성/삭제 | 연결 등록, 해제, room 자동 정리 | 🔴 |
| T-02 | Room 관리 | worker_{id}, role_{role} join/leave 동작 | 🔴 |
| T-03 | JWT 토큰 파싱 | query param에서 토큰 추출 → worker_id, role 디코딩 | 🔴 |
| T-04 | 메시지 포맷 직렬화 | `{"event": "xxx", "data": {...}}` JSON 포맷 검증 | 🔴 |
| T-05 | emit_new_alert 함수 | worker room에만 전송되는지 확인 | 🔴 |
| T-06 | emit_process_alert 함수 | role room에만 전송되는지 확인 | 🔴 |
| T-07 | emit_task_completed 함수 | broadcast (전체 연결)에 전송되는지 | 🟡 |
| T-08 | ping/pong heartbeat | FE ping 수신 → pong 응답 | 🟡 |
| T-09 | 동시 다중 연결 | 여러 worker 동시 연결 시 registry 무결성 | 🟡 |
| T-10 | 비정상 연결 해제 | 갑작스런 disconnect 시 registry cleanup | 🟡 |

### Phase 2: 기존 테스트 수정 및 회귀 테스트

| # | 테스트 파일 | 변경 필요 | 이유 |
|---|-----------|----------|------|
| T-11 | `test_websocket.py` | 🔴 전면 수정 | Flask-SocketIO test_client → flask-sock 방식 |
| T-12 | `test_alert_service.py` | ✅ 그대로 | alert REST API는 변경 없음 |
| T-13 | `test_scheduler.py` | 🟡 확인 필요 | scheduler → create_and_broadcast_alert 변경 영향 |
| T-14 | `test_admin_api.py` | ✅ 그대로 | admin API는 변경 없음 |
| T-15 | `test_work_api.py` | ✅ 그대로 | work API는 변경 없음 |
| T-16 | `test_duration_validator.py` | ✅ 그대로 | duration 로직 변경 없음 |

### Phase 3: 통합 테스트 (로컬)

| # | 시나리오 | 검증 내용 |
|---|---------|---------|
| T-17 | FE 연결 → BE /ws 핸드셰이크 | WebSocket 업그레이드 성공, connected 이벤트 수신 |
| T-18 | 1단계: 작업 시작 → 1시간 대기 → TASK_REMINDER 수신 | scheduler → broadcast → FE 알림 팝업 |
| T-19 | Admin 알림 생성 → 작업자 실시간 수신 | admin API → create_and_broadcast → worker room → FE |
| T-20 | 다중 사용자 동시 접속 | Worker A, B 각각 연결 → 각자 room의 알림만 수신 |
| T-21 | 연결 끊김 → 재연결 | FE reconnect 로직 (최대 2회, 10초 간격) 정상 동작 |
| T-22 | 휴게시간 알림 | BREAK_TIME_PAUSE/END 이벤트 FE 전달 |

### Phase 4: 배포 테스트 (Railway + Netlify)

| # | 체크 항목 | 검증 방법 |
|---|---------|---------|
| T-23 | Railway 배포 성공 | `git push` → build 성공, health check 통과 |
| T-24 | Procfile gthread 워커 동작 | Railway 로그에서 워커 시작 확인 |
| T-25 | WSS 연결 (HTTPS) | PWA에서 `wss://axis-ops-api.up.railway.app/ws` 연결 |
| T-26 | 알림 E2E | PWA 접속 → 작업 시작 → Admin에서 알림 생성 → PWA 실시간 수신 |
| T-27 | 기존 REST API 정상 | `/health`, 로그인, QR스캔, 작업시작/완료 전부 동작 확인 |
| T-28 | 기존 스케줄러 정상 | Railway 로그에서 스케줄러 6개 job 등록 확인 |

---

## 7. 작업 순서

### Day 1 (토요일) — 코딩 + 로컬 테스트

| 순서 | 작업 | 시간 |
|------|------|------|
| 1 | `requirements.txt` 수정, `flask-sock` 설치 확인 | 10분 |
| 2 | `events.py` 리라이트 (ConnectionRegistry + ws_handler + emit 함수) | 2~3시간 |
| 3 | `websocket/__init__.py` 수정 | 10분 |
| 4 | `app/__init__.py` 수정 (Sock 초기화 + /ws 라우트) | 30분 |
| 5 | `run.py` 수정 | 10분 |
| 6 | `scheduler_service.py` — create_alert → create_and_broadcast_alert (3곳) | 1시간 |
| 7 | T-01 ~ T-10 단위 테스트 | 1~2시간 |
| 8 | T-11, T-13 기존 테스트 수정 | 1시간 |
| 9 | 로컬 `flask run` + `flutter run -d chrome` E2E | 1시간 |

### Day 2 (일요일) — 배포 + 검증

| 순서 | 작업 | 시간 |
|------|------|------|
| 10 | `Procfile` 수정 | 10분 |
| 11 | `git push` → Railway 배포 | 30분 |
| 12 | `flutter build web` → Netlify 배포 | 30분 |
| 13 | T-23 ~ T-28 배포 테스트 | 1~2시간 |
| 14 | 버그 수정 (있으면) | 1~2시간 |
| 15 | PROGRESS.md, BACKLOG.md 업데이트 | 30분 |

---

## 8. 리스크 & 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| `flask-sock`이 Railway gunicorn에서 WSS 지원 안됨 | 배포 실패 | `gunicorn --worker-class gthread` + Railway HTTPS 프록시가 WSS 자동 지원하는지 사전 확인 |
| ConnectionRegistry thread-safety 문제 | 동시 접속 시 크래시 | `threading.Lock()` + 스트레스 테스트 |
| FE reconnect 무한 루프 | 서버 부하 | 현재 max 2회 제한 되어있음 (확인 완료) |
| 기존 Flask-SocketIO 의존 테스트 깨짐 | CI 실패 | test_websocket.py 전면 수정 (Phase 2) |
| eventlet 제거로 인한 사이드 이펙트 | 스케줄러 등 | APScheduler는 eventlet 불필요 (BackgroundScheduler 사용) |

---

## 9. 완료 기준

- [ ] FE PWA에서 `wss://` 연결 성공
- [ ] 1단계 TASK_REMINDER → 실시간 수신 확인
- [ ] 2단계 SHIFT_END_REMINDER → 실시간 수신 확인
- [ ] 3단계 TASK_ESCALATION → 관리자 실시간 수신 확인
- [ ] Admin 수동 알림 → 작업자 실시간 수신 확인
- [ ] 기존 REST API 전부 정상 동작
- [ ] 기존 테스트 PASS (깨진 테스트 수정 완료)
- [ ] Railway + Netlify 배포 완료
