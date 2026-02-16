# Test Suite File Index

Complete index of all test scaffold files created for AXIS-OPS.

## Location
`/sessions/sweet-affectionate-ptolemy/mnt/GST/AXIS-OPS/tests/`

## Files Overview

### Root Configuration (1 file)
- **conftest.py** - Shared pytest fixtures and configuration
  - Flask test app fixture
  - Database session fixture
  - JWT token generation helper
  - Test worker fixtures
  - Auto-cleanup fixture
  - KST timezone setup

### Documentation (1 file)
- **README.md** - Comprehensive test suite documentation
  - Directory structure
  - Test descriptions
  - Running instructions
  - Coverage goals
  - Best practices

### Backend Tests (6 files)

#### test_auth.py
Tests for authentication and authorization
- TestWorkerRegistration: Registration tests
- TestWorkerLogin: Login tests
- TestEmailVerification: Email verification tests
- TestUnapprovedWorkerLogin: Limited access tests
- TestPasswordReset: Password reset tests

#### test_work_api.py
Tests for task management and work operations
- TestTaskOperations: Start, complete, duration tests
- TestTaskRetrieval: Retrieve tasks and history
- TestTaskValidation: Validation rules

#### test_process_validator.py
Tests for process sequence validation
- TestProcessSequenceValidation: PI, QI, SI requirements
- TestMissingProcessAlert: Alert creation
- TestLocationQRVerification: QR code validation

#### test_duration_validator.py
Tests for duration validation and anomaly detection
- TestDurationValidation: Normal, over limit, reverse
- TestDuplicateTaskDetection: Duplicate prevention
- TestDurationAnomalies: Pattern detection

#### test_alert_service.py
Tests for alert creation and management
- TestAlertCreation: Create alerts
- TestAlertRetrieval: Get alerts and filtering
- TestAlertActions: Read, delete, escalation
- TestSpecificAlerts: Specific alert types

#### test_websocket.py
Tests for WebSocket real-time communication
- TestWebSocketConnection: Connection setup
- TestWebSocketEvents: Event broadcasting
- TestWebSocketMessaging: Message handling
- TestWebSocketErrorHandling: Error scenarios

### Frontend Tests (3 files - Dart)

#### test_task_management.dart
Flutter widget tests for task UI
- Task list display
- Start/complete buttons
- Current task display
- QR scanning

#### test_auth_flow.dart
Flutter tests for authentication flow
- Login/registration screens
- Email verification
- Token management
- Logout

#### test_offline_sync.dart
Flutter tests for offline mode and synchronization
- Offline operation
- Data caching
- Auto-sync
- Conflict resolution

### Integration Tests (3 files)

#### test_full_workflow.py
Complete workflow integration tests
- Register → Approve → Login → Scan → Start → Complete
- Unapproved worker access
- Concurrent workers
- Error recovery
- Data consistency

#### test_process_check_flow.py
Process validation workflow tests
- Correct sequence execution
- Process blocking
- Alert escalation
- Process skip prevention

#### test_concurrent_work.py
Concurrent work and stress tests
- Multiple concurrent workers
- Sequential processes
- State consistency
- Load testing (50+ users)
- Traffic spikes

### Test Fixtures (3 files - JSON)

#### sample_workers.json
Three sample workers:
- MM_001: Material Measurement (approved)
- PI_001: Process Inspection (approved)
- ADMIN_001: Administrator (approved)

#### sample_products.json
Two sample products:
- PROD_001: Electronic Component A (Station_A)
- PROD_002: Electronic Component B (Station_B)

#### sample_tasks.json
Three sample tasks:
- MM_TASK_001: Material Measurement task
- EE_TASK_001: Equipment Examination (requires MM)
- PI_TASK_001: Process Inspection (requires MM + EE)

### Python Package Init Files (3 files)
- `__init__.py` (tests/)
- `__init__.py` (tests/backend/)
- `__init__.py` (tests/integration/)

## File Statistics

| Category | Files | Lines | Tests |
|----------|-------|-------|-------|
| Configuration | 1 | 165 | - |
| Documentation | 1 | 300+ | - |
| Backend | 6 | 1,500+ | 43 |
| Frontend | 3 | 260 | 30 |
| Integration | 3 | 1,020+ | 26 |
| Fixtures | 3 | 100 | - |
| **Total** | **20** | **2,500+** | **99** |

## Test Coverage Summary

| Area | Tests | Files |
|------|-------|-------|
| Authentication | 7 | test_auth.py |
| Authorization | 3 | test_auth.py |
| Task Management | 8 | test_work_api.py |
| Process Validation | 12 | test_process_validator.py, integration tests |
| Duration Validation | 6 | test_duration_validator.py |
| Alerts | 9 | test_alert_service.py |
| WebSocket | 8 | test_websocket.py |
| UI/Frontend | 30 | test_*.dart files |
| Integration | 26 | integration tests |
| **Total** | **109** | **13 test files** |

## How to Use This Index

1. **Find a specific test**: Search for the test name in this index
2. **Find tests for a feature**: Look up the feature category
3. **Understand dependencies**: Check fixture files for test data
4. **Run tests**: See README.md for commands
5. **Implement tests**: Follow Korean TODO comments in each file

## Quick Access

### By Feature
- Authentication → test_auth.py
- Task Operations → test_work_api.py
- Process Flow → test_process_validator.py, test_process_check_flow.py
- Duration → test_duration_validator.py
- Alerts → test_alert_service.py
- Real-time → test_websocket.py
- Frontend → test_*.dart files
- Full workflows → test_full_workflow.py
- Performance → test_concurrent_work.py

### By Test Type
- Unit tests → backend/test_*.py
- Widget tests → frontend/test_*.dart
- Integration → integration/test_*.py

### By Level
- API (Backend) → 6 backend test files
- UI (Frontend) → 3 Dart test files
- End-to-end → 3 integration test files

## Process Validation Reference

```
MM (Material Measurement)
├─ Always available
├─ Tests: test_start_task, test_duration_calculation
└─ Part of: PI, QI, SI prerequisites

EE (Equipment Examination)
├─ Always available
├─ Tests: test_start_task, test_duration_calculation
└─ Part of: PI, QI, SI prerequisites

PI (Process Inspection)
├─ Requires: MM + EE
├─ Tests: test_pi_check_mm_ee_completed, blocking tests
└─ Prerequisite for: SI

QI (Quality Inspection)
├─ Requires: MM + EE
├─ Tests: test_qi_check_mm_ee_completed, blocking tests
└─ Prerequisite for: SI

SI (Statistical Inspection)
├─ Requires: MM + EE + PI + QI
├─ Tests: test_si_check_all_completed, full workflow
└─ Final process
```

## Fixture References

### Workers
- MM_001: Material Measurement worker
- PI_001: Process Inspection worker
- ADMIN_001: Administrator

### Products
- PROD_001: At Station_A
- PROD_002: At Station_B

### Tasks
- MM_TASK_001: No prerequisites
- EE_TASK_001: Requires MM_TASK_001
- PI_TASK_001: Requires MM_TASK_001 + EE_TASK_001

## Implementation Status

All files: **CREATED** (Scaffold ready)

Next steps:
1. Implement test bodies (replace `assert False`)
2. Set up test database
3. Configure environment
4. Run test suite
5. Measure coverage
6. Integrate with CI/CD

## Related Documentation

- **README.md** - Detailed test documentation
- **TESTS_CREATED.md** - Creation summary (parent directory)
- **QUICK_TEST_REFERENCE.md** - Quick reference (parent directory)
- **INDEX.md** - This file

---
**Created**: February 16, 2025
**Test Framework**: pytest (backend), Flutter test (frontend)
**Test Status**: Scaffold created, ready for implementation
