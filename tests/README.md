# AXIS-OPS Test Suite

This directory contains the complete test suite for the AXIS-OPS system.

## Directory Structure

```
tests/
├── conftest.py                          # Shared pytest fixtures and configuration
├── backend/                             # Backend API tests
│   ├── test_auth.py                    # Authentication and authorization tests
│   ├── test_work_api.py                # Task management API tests
│   ├── test_process_validator.py       # Process sequence validation tests
│   ├── test_duration_validator.py      # Duration validation and anomaly detection
│   ├── test_alert_service.py           # Alert service tests
│   └── test_websocket.py               # WebSocket real-time communication tests
├── frontend/                            # Flutter frontend tests
│   ├── test_task_management.dart       # Task management UI tests
│   ├── test_auth_flow.dart             # Authentication flow tests
│   └── test_offline_sync.dart          # Offline mode and sync tests
├── integration/                         # Integration tests
│   ├── test_full_workflow.py           # Complete workflow tests (register → approve → login → work)
│   ├── test_process_check_flow.py      # Process sequence validation workflow tests
│   └── test_concurrent_work.py         # Concurrent worker and multi-user tests
└── fixtures/                            # Test data fixtures
    ├── sample_workers.json             # Sample worker data (MM, PI, Admin)
    ├── sample_products.json            # Sample product data with QR codes
    └── sample_tasks.json               # Sample task data
```

## Test Files Overview

### conftest.py
Shared pytest configuration and fixtures used across all tests:
- `app` - Flask test application fixture
- `client` - Test client for Flask app
- `db_session` - Test database session
- `get_auth_token()` - JWT token generation helper
- `test_worker` - Sample test worker fixture
- `unapproved_worker` - Unapproved worker fixture
- `cleanup` - Auto-cleanup after each test
- `sample_qr_code` - Sample QR code fixture
- `set_timezone` - KST timezone setup

### Backend Tests (tests/backend/)

#### test_auth.py
Tests for authentication and authorization:
- Worker registration (valid and duplicate email)
- Login success and failure scenarios
- Email verification
- Unapproved worker access restrictions
- Password reset functionality

#### test_work_api.py
Tests for task management and work operations:
- Task start/complete operations
- Duration calculation (completed_at - started_at)
- Task retrieval (my tasks, current task, history)
- QR code validation
- Multi-task prevention

#### test_process_validator.py
Tests for process sequence validation:
- PI requires MM and EE completion
- QI requires MM and EE completion
- SI requires all processes completed
- Missing process alerts
- Location QR verification

#### test_duration_validator.py
Tests for duration validation and anomaly detection:
- Normal duration acceptance
- Duration > 14 hours alerting
- Reverse duration detection (completed < started)
- Duplicate task detection
- Unusual duration patterns

#### test_alert_service.py
Tests for alert creation and management:
- Alert creation and retrieval
- Unread alert filtering
- Mark alerts as read
- Delete alerts
- Process violation alerts
- Duration anomaly alerts
- Unfinished task closing time alerts

#### test_websocket.py
Tests for WebSocket real-time communication:
- Connection establishment and authentication
- Task started/completed event broadcasting
- Alert event broadcasting
- Message handling
- Heartbeat mechanism
- Connection closure and error handling

### Frontend Tests (tests/frontend/)

#### test_task_management.dart
Flutter widget tests for task management UI:
- Task list display
- Start/complete task buttons
- Current task display
- QR code scanning
- Offline mode support

#### test_auth_flow.dart
Flutter tests for authentication flow:
- Login/registration screens
- Valid/invalid credentials handling
- Email verification flow
- Token refresh
- Logout and session management

#### test_offline_sync.dart
Flutter tests for offline mode and sync:
- Offline status display
- Task operations while offline
- Cached data display
- Auto-sync when returning online
- Conflict resolution
- Cache management

### Integration Tests (tests/integration/)

#### test_full_workflow.py
Complete workflow integration tests:
- Register → Approve → Login → Scan → Start → Complete
- Unapproved worker limited access
- Multiple workers concurrent tasks
- Error recovery (network, server)
- Data integrity verification

#### test_process_check_flow.py
Process validation workflow tests:
- Correct process sequence completion
- PI/QI blocking without MM/EE
- SI blocking without all prior processes
- Process alert generation and escalation
- Process skip attempt prevention

#### test_concurrent_work.py
Concurrent work and stress tests:
- Multiple workers starting tasks concurrently
- Multiple workers completing tasks concurrently
- Sequential processes on same product
- Same task access by multiple workers
- Event ordering guarantee
- High concurrent user load
- Sudden traffic spike handling

## Fixture Files (tests/fixtures/)

### sample_workers.json
Three sample workers for testing:
- MM_001: Material Measurement worker (approved)
- PI_001: Process Inspection worker (approved)
- ADMIN_001: Administrator (approved)

### sample_products.json
Two sample products with QR codes:
- PROD_001: Electronic Component A (Station_A)
- PROD_002: Electronic Component B (Station_B)

### sample_tasks.json
Three sample tasks for different processes:
- MM_TASK_001: Material Measurement task
- EE_TASK_001: Equipment Examination task (requires MM)
- PI_TASK_001: Process Inspection task (requires MM + EE)

## Running Tests

### Run all tests
```bash
pytest tests/
```

### Run specific test file
```bash
pytest tests/backend/test_auth.py
```

### Run specific test class
```bash
pytest tests/backend/test_auth.py::TestWorkerRegistration
```

### Run specific test
```bash
pytest tests/backend/test_auth.py::TestWorkerRegistration::test_register_worker
```

### Run with verbose output
```bash
pytest tests/ -v
```

### Run with coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

### Run only backend tests
```bash
pytest tests/backend/
```

### Run only integration tests
```bash
pytest tests/integration/
```

### Run Flutter tests
```bash
flutter test tests/frontend/
```

## Test Coverage Goals

- Backend: > 90% code coverage
- Frontend: > 80% code coverage
- Integration: Critical paths fully covered

## Test Implementation Notes

### Korean TODO Comments
All test files include Korean TODO comments (TODO: 한글 설명) to indicate:
- What needs to be implemented
- Expected outcomes
- Important validation points

### Test Structure
Each test follows this pattern:
1. Setup: Create test data
2. Action: Call the API/function
3. Assert: Verify the expected behavior

### Dependencies
- pytest: Test framework
- pytest-cov: Coverage reporting
- flask: Web framework for backend
- sqlalchemy: ORM
- flutter_test: Flutter testing framework

## Key Testing Areas

1. **Authentication**: Login, registration, email verification, token management
2. **Work Management**: Task start/complete, duration calculation, task retrieval
3. **Process Validation**: Sequence checking, prerequisites, blocking logic
4. **Duration Validation**: Normal ranges, anomaly detection, alerts
5. **Alerts**: Creation, retrieval, escalation, real-time broadcasting
6. **WebSocket**: Connection, events, heartbeat, error handling
7. **Offline Mode**: Operation without connectivity, data sync, conflict resolution
8. **Concurrency**: Multiple workers, data consistency, race condition prevention
9. **Integration**: Complete workflows from start to finish
10. **Load Testing**: High concurrent users, traffic spikes

## Common Test Assertions

```python
# HTTP Status Codes
assert response.status_code == 200  # Success
assert response.status_code == 201  # Created
assert response.status_code == 400  # Bad Request
assert response.status_code == 401  # Unauthorized
assert response.status_code == 403  # Forbidden
assert response.status_code == 409  # Conflict

# Database
assert db_session.query(Task).filter_by(id='TASK_001').first() is not None

# Response Content
assert 'token' in response.json()
assert response.json()['status'] == 'success'
```

## Future Enhancements

- Add performance benchmarking tests
- Add security testing (OWASP)
- Add accessibility testing
- Add load testing with k6 or locust
- Add mutation testing
- Add contract testing for API
