# AXIS-OPS Test Suite - Quick Reference Guide

## File Structure

```
/sessions/sweet-affectionate-ptolemy/mnt/GST/AXIS-OPS/tests/
├── conftest.py                    # Shared fixtures (app, db, auth, cleanup)
├── README.md                      # Detailed documentation
│
├── backend/                       # Backend API unit tests (6 files)
│   ├── test_auth.py              # Authentication & authorization (7 test stubs)
│   ├── test_work_api.py          # Task operations (8 test stubs)
│   ├── test_process_validator.py # Process sequence validation (5 test stubs)
│   ├── test_duration_validator.py # Duration validation (6 test stubs)
│   ├── test_alert_service.py     # Alert management (9 test stubs)
│   └── test_websocket.py         # WebSocket communication (8 test stubs)
│
├── frontend/                      # Flutter widget tests (3 files)
│   ├── test_task_management.dart # Task UI (8 test stubs)
│   ├── test_auth_flow.dart       # Auth UI (9 test stubs)
│   └── test_offline_sync.dart    # Offline & sync (13 test stubs)
│
├── integration/                   # End-to-end integration tests (3 files)
│   ├── test_full_workflow.py     # Complete workflows (8 test stubs)
│   ├── test_process_check_flow.py # Process validation flow (7 test stubs)
│   └── test_concurrent_work.py   # Multi-user & load tests (11 test stubs)
│
└── fixtures/                      # Test data (3 JSON files)
    ├── sample_workers.json       # 3 sample workers
    ├── sample_products.json      # 2 sample products
    └── sample_tasks.json         # 3 sample tasks
```

## Key Test Stubs Summary

### Authentication (test_auth.py)
- `test_register_worker` - Valid registration → 201 Created
- `test_register_duplicate_email` - Duplicate → 409 Conflict
- `test_login_success` - Valid creds → JWT token
- `test_login_wrong_password` - Invalid → 401 Unauthorized
- `test_email_verification` - Verify token → is_verified=True
- `test_unapproved_worker_login` - Login allowed but API access denied (403)

### Work Management (test_work_api.py)
- `test_start_task` - Start task → status=RUNNING
- `test_complete_task` - Complete task → status=COMPLETED
- `test_duration_calculation` - Duration = completed_at - started_at
- `test_get_my_tasks` - Get worker's task list
- `test_get_current_task` - Get active task with elapsed time
- `test_task_history` - Get completed tasks sorted by date

### Process Validation (test_process_validator.py)
- `test_pi_check_mm_ee_completed` - PI needs MM + EE done first
- `test_qi_check_mm_ee_completed` - QI needs MM + EE done first
- `test_si_check_all_completed` - SI needs MM + EE + PI + QI done first
- `test_missing_process_alert_created` - Missing process → Alert created
- `test_location_qr_verification` - QR code validates location

### Duration Validation (test_duration_validator.py)
- `test_normal_duration` - 5min-4h range → no alert
- `test_duration_over_14h` - >14h → Alert created
- `test_reverse_duration` - completed < started → Error 400
- `test_duplicate_task_same_worker` - Same task twice → 409 Conflict

### Alerts (test_alert_service.py)
- `test_create_alert` - Create alert → 201 Created
- `test_get_unread_alerts` - Get unread only
- `test_mark_alert_read` - Mark read → is_read=True
- `test_unfinished_task_closing_time_alert` - Past due + still running → Alert

### WebSocket (test_websocket.py)
- `test_websocket_connection` - Connect with token
- `test_task_started_event` - Broadcast task_started event
- `test_alert_broadcast` - Broadcast alert to users
- `test_websocket_heartbeat` - Ping/pong keep-alive

### Frontend Tests (Dart)
- **test_task_management.dart** - Task list, start, complete, current task
- **test_auth_flow.dart** - Login, register, email verify, logout
- **test_offline_sync.dart** - Offline ops, sync, conflict resolution

### Integration Tests
- **test_full_workflow.py** - Register→Approve→Login→Scan→Start→Complete
- **test_process_check_flow.py** - MM→EE→PI→QI→SI sequence
- **test_concurrent_work.py** - 50+ concurrent workers, load testing

## Critical Process Sequence

```
Product Flow:
  MM (Material Measurement) ── Start: Ready
  EE (Equipment Examination) ├─ Start: After MM done
  PI (Process Inspection) ────┤─ Start: After MM + EE done
  QI (Quality Inspection) ────┤─ Start: After MM + EE done
  SI (Statistical Inspection) └─ Start: After all done
```

## Running Tests

```bash
# All tests
pytest /sessions/sweet-affectionate-ptolemy/mnt/GST/AXIS-OPS/tests/

# Backend only
pytest /sessions/sweet-affectionate-ptolemy/mnt/GST/AXIS-OPS/tests/backend/

# Integration only
pytest /sessions/sweet-affectionate-ptolemy/mnt/GST/AXIS-OPS/tests/integration/

# Specific file
pytest /sessions/sweet-affectionate-ptolemy/mnt/GST/AXIS-OPS/tests/backend/test_auth.py

# Specific test
pytest /sessions/sweet-affectionate-ptolemy/mnt/GST/AXIS-OPS/tests/backend/test_auth.py::TestWorkerLogin::test_login_success

# With coverage
pytest /sessions/sweet-affectionate-ptolemy/mnt/GST/AXIS-OPS/tests/ --cov --cov-report=html

# Flutter tests
flutter test /sessions/sweet-affectionate-ptolemy/mnt/GST/AXIS-OPS/tests/frontend/
```

## Fixtures Available

### In conftest.py
- `app` - Flask test application
- `client` - Test client for API calls
- `db_session` - Test database connection
- `get_auth_token()` - Generate JWT tokens
  - Usage: `token = get_auth_token('WORKER_ID', role='MM')`
- `test_worker` - Pre-made approved worker
- `unapproved_worker` - Pre-made unapproved worker
- `sample_qr_code` - Sample QR code data
- `cleanup` - Auto-cleanup after test

### JSON Fixtures
- `sample_workers.json` - MM_001, PI_001, ADMIN_001
- `sample_products.json` - PROD_001, PROD_002
- `sample_tasks.json` - MM_TASK_001, EE_TASK_001, PI_TASK_001

## Test Implementation Pattern

```python
def test_something(self, client, get_auth_token, db_session):
    # 1. Setup
    token = get_auth_token('WORKER_ID', role='MM')
    headers = {'Authorization': f'Bearer {token}'}
    
    # 2. Action
    response = client.post('/api/endpoint', json=payload, headers=headers)
    
    # 3. Assert
    assert response.status_code == 200
    assert response.json()['field'] == expected_value
```

## Key API Endpoints (from test comments)

### Authentication
- `POST /api/auth/register` - Register new worker
- `POST /api/auth/login` - Login
- `GET /api/auth/verify-email?token=xxx` - Verify email
- `POST /api/auth/password-reset-request` - Request reset
- `POST /api/auth/reset-password` - Reset with token

### Work Management
- `POST /api/work/tasks/start` - Start task
- `POST /api/work/tasks/complete` - Complete task
- `GET /api/work/my-tasks` - List my tasks
- `GET /api/work/current-task` - Get active task
- `GET /api/work/task-history` - Get history

### Alerts
- `POST /api/alerts` - Create alert
- `GET /api/alerts` - Get all alerts
- `GET /api/alerts/unread` - Get unread alerts
- `PUT /api/alerts/{id}/read` - Mark as read
- `DELETE /api/alerts/{id}` - Delete alert

### Admin
- `PUT /api/admin/workers/{id}/approve` - Approve worker

### WebSocket
- `WS /ws?token=xxx` - Connect with JWT

## Common HTTP Status Codes

- `200` - OK (success)
- `201` - Created (resource created)
- `400` - Bad Request (validation error)
- `401` - Unauthorized (auth failed)
- `403` - Forbidden (access denied)
- `409` - Conflict (duplicate, state error)
- `500` - Server Error

## Todo Implementation Checklist

For each test file:
- [ ] Replace `assert False, "Test implementation required"` with actual assertions
- [ ] Implement API calls according to endpoint comments
- [ ] Use fixtures (client, get_auth_token, db_session)
- [ ] Verify response status codes
- [ ] Verify response JSON content
- [ ] Verify database state changes
- [ ] Handle both success and failure paths

## Test Documentation

- **README.md** - Detailed suite documentation
- **TESTS_CREATED.md** - Creation summary
- **QUICK_TEST_REFERENCE.md** - This file

All test files include Korean TODO comments explaining:
- What to implement
- Expected outcomes
- API endpoints to call
- Error handling
- Validation rules
