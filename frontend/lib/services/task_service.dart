import 'api_service.dart';
import '../models/product_info.dart';
import '../models/task_item.dart';

/// 출고 완료 제품 예외
class ProductShippedException implements Exception {
  final String message;
  final String? serialNumber;
  final String? model;
  ProductShippedException(this.message, {this.serialNumber, this.model});

  @override
  String toString() => message;
}

/// Task 서비스
///
/// QR 기반 제품 조회, Task 목록 조회, 작업 시작/완료 등을 담당
class TaskService {
  final ApiService _apiService;

  TaskService({ApiService? apiService})
      : _apiService = apiService ?? ApiService();

  /// QR 스캔 → 제품 조회
  ///
  /// [qrDocId]: QR 문서 ID (예: DOC_GBWS-6408)
  ///
  /// Returns: ProductInfo 객체
  ///
  /// API: GET /api/app/product/{qr_doc_id}
  /// Response: {"id": int, "qr_doc_id": str, "serial_number": str, ...}
  Future<ProductInfo> getProductByQrDocId(String qrDocId) async {
    try {
      final response = await _apiService.get('/app/product/$qrDocId');
      // shipped 제품 응답 처리
      if (response is Map && response['error'] == 'PRODUCT_SHIPPED') {
        throw ProductShippedException(
          response['message'] ?? '출고 완료된 제품입니다.',
          serialNumber: response['serial_number'],
          model: response['model'],
        );
      }
      return ProductInfo.fromJson(response);
    } catch (e) {
      rethrow;
    }
  }

  /// Location QR 등록
  ///
  /// [qrDocId]: QR 문서 ID
  /// [locationQrId]: Location QR ID (예: LOC_ASSY_01)
  ///
  /// Returns: 업데이트된 ProductInfo 객체
  ///
  /// API: POST /api/app/location/update
  /// Request: {"qr_doc_id": str, "location_qr_id": str}
  /// Response: {"id": int, "qr_doc_id": str, "location_qr_id": str, ...}
  Future<ProductInfo> updateLocation({
    required String qrDocId,
    required String locationQrId,
  }) async {
    try {
      final response = await _apiService.post(
        '/app/location/update',
        data: {
          'qr_doc_id': qrDocId,
          'location_qr_id': locationQrId,
        },
      );
      return ProductInfo.fromJson(response);
    } catch (e) {
      rethrow;
    }
  }

  /// 역할별 Task 목록 조회
  ///
  /// [serialNumber]: 제품 시리얼 번호 (예: GBWS-6408)
  /// [workerId]: 작업자 ID
  ///
  /// Returns: TaskItem 리스트
  ///
  /// API: GET /api/app/tasks/{serial_number}?worker_id={worker_id}
  /// Response: [{"id": int, "task_id": str, "task_name": str, ...}, ...]
  Future<List<TaskItem>> getTasksBySerialNumber({
    required String serialNumber,
    required int workerId,
    String? qrDocId,
  }) async {
    try {
      final params = <String, dynamic>{'worker_id': workerId};
      if (qrDocId != null) {
        params['qr_doc_id'] = qrDocId;
      }
      final response = await _apiService.get(
        '/app/tasks/$serialNumber',
        queryParameters: params,
      );

      // response가 리스트 형태인지 확인
      if (response is List) {
        return response.map((item) => TaskItem.fromJson(item)).toList();
      } else if (response is Map && response.containsKey('tasks')) {
        // {"tasks": [...]} 형태일 경우
        return (response['tasks'] as List)
            .map((item) => TaskItem.fromJson(item))
            .toList();
      } else {
        throw Exception('잘못된 응답 형식: Task 목록을 불러올 수 없습니다.');
      }
    } catch (e) {
      rethrow;
    }
  }

  /// 작업 시작
  ///
  /// [taskId]: app_task_details의 ID
  /// [workerId]: 작업자 ID
  ///
  /// Returns: 업데이트된 TaskItem 객체
  ///
  /// API: POST /api/app/work/start
  /// Request: {"task_id": int, "worker_id": int}
  /// Response: {"id": int, "started_at": str, ...}
  Future<TaskItem> startTask({
    required int taskId,
    required int workerId,
  }) async {
    try {
      final response = await _apiService.post(
        '/app/work/start',
        data: {
          'task_id': taskId,
          'worker_id': workerId,
        },
      );
      return TaskItem.fromJson(response);
    } catch (e) {
      rethrow;
    }
  }

  /// 작업 완료
  ///
  /// [taskId]: app_task_details의 ID
  /// [workerId]: 작업자 ID
  ///
  /// Returns: ({TaskItem task, bool checklistReady})
  ///
  /// API: POST /api/app/work/complete
  /// Request: {"task_id": int, "worker_id": int, "finalize": bool}
  /// Response: {"id": int, "completed_at": str, "duration": int, ...}
  /// Sprint 41: finalize=false → 릴레이 종료 (task 열린 상태 유지)
  /// Sprint 52 BUG-FIX: checklist_ready 플래그 전달 (매니저 직접 완료 시)
  Future<({TaskItem task, bool checklistReady})> completeTask({
    required int taskId,
    required int workerId,
    bool finalize = true,
  }) async {
    try {
      final response = await _apiService.post(
        '/app/work/complete',
        data: {
          'task_id': taskId,
          'worker_id': workerId,
          'finalize': finalize,
        },
      );
      final task = TaskItem.fromJson(response);
      final checklistReady = response['checklist_ready'] == true;
      return (task: task, checklistReady: checklistReady);
    } catch (e) {
      rethrow;
    }
  }

  /// 단일 액션 Task 완료 (Sprint 27)
  ///
  /// SINGLE_ACTION Task는 시작 없이 바로 완료 체크만 수행.
  ///
  /// API: POST /api/app/work/complete-single
  Future<TaskItem> completeSingleAction({required int taskDetailId}) async {
    try {
      final response = await _apiService.post(
        '/app/work/complete-single',
        data: {'task_detail_id': taskDetailId},
      );
      return TaskItem.fromJson(response);
    } catch (e) {
      rethrow;
    }
  }

  /// 공정 완료 상태 조회
  ///
  /// [serialNumber]: 제품 시리얼 번호
  ///
  /// Returns: CompletionStatus 맵
  ///
  /// API: GET /api/app/completion/{serial_number}
  /// Response: {
  ///   "qr_doc_id": str,
  ///   "mm_completed": bool,
  ///   "ee_completed": bool,
  ///   "tm_completed": bool,
  ///   "pi_completed": bool,
  ///   "qi_completed": bool,
  ///   "si_completed": bool,
  ///   "all_completed": bool,
  ///   "all_completed_at": str?
  /// }
  Future<Map<String, dynamic>> getCompletionStatus(String serialNumber) async {
    try {
      final response = await _apiService.get('/app/completion/$serialNumber');
      return response as Map<String, dynamic>;
    } catch (e) {
      rethrow;
    }
  }

  /// 공정 누락 검증 (PI/QI/SI용)
  ///
  /// [serialNumber]: 제품 시리얼 번호
  /// [processType]: 공정 타입 (PI, QI, SI)
  ///
  /// Returns: 검증 결과
  ///
  /// API: POST /api/app/validation/check-process
  /// Request: {"serial_number": str, "process_type": str}
  /// Response: {
  ///   "valid": bool,
  ///   "missing_processes": [str],
  ///   "location_qr_verified": bool,
  ///   "message": str?
  /// }
  Future<Map<String, dynamic>> validateProcess({
    required String serialNumber,
    required String processType,
  }) async {
    try {
      final response = await _apiService.post(
        '/app/validation/check-process',
        data: {
          'serial_number': serialNumber,
          'process_type': processType,
        },
      );
      return response as Map<String, dynamic>;
    } catch (e) {
      rethrow;
    }
  }

  /// 작업 일시정지
  ///
  /// [taskDetailId]: app_task_details의 ID
  ///
  /// Returns: 업데이트된 TaskItem 객체
  ///
  /// API: POST /api/app/work/pause
  /// Request: {"task_detail_id": int}
  /// Response: {"id": int, "is_paused": true, ...}
  Future<TaskItem> pauseTask({required int taskDetailId}) async {
    try {
      final response = await _apiService.post(
        '/app/work/pause',
        data: {'task_detail_id': taskDetailId},
      );
      return TaskItem.fromJson(response);
    } catch (e) {
      rethrow;
    }
  }

  /// 작업 재개
  ///
  /// [taskDetailId]: app_task_details의 ID
  ///
  /// Returns: 업데이트된 TaskItem 객체
  ///
  /// API: POST /api/app/work/resume
  /// Request: {"task_detail_id": int}
  /// Response: {"id": int, "is_paused": false, ...}
  Future<TaskItem> resumeTask({required int taskDetailId}) async {
    try {
      final response = await _apiService.post(
        '/app/work/resume',
        data: {'task_detail_id': taskDetailId},
      );
      return TaskItem.fromJson(response);
    } catch (e) {
      rethrow;
    }
  }

  /// 앱 설정 조회 (일반 작업자 접근 가능)
  ///
  /// Returns: admin_settings 맵 (key → value)
  ///
  /// API: GET /api/app/settings (jwt_required만, admin_required 없음)
  Future<Map<String, dynamic>> getAdminSettings() async {
    try {
      final response = await _apiService.get('/app/settings');
      if (response is Map<String, dynamic>) {
        return response;
      }
      return {};
    } catch (e) {
      // BUG-13: 에러 시 안전한 쪽(블록 활성)으로 기본값 반환
      return {'location_qr_required': true};
    }
  }

  /// Task 비활성화 (관리자/사내직원 전용)
  ///
  /// [taskId]: app_task_details의 ID
  /// [isApplicable]: 적용 여부
  ///
  /// Returns: 업데이트된 TaskItem 객체
  ///
  /// API: PUT /api/app/task/toggle-applicable
  /// Request: {"task_id": int, "is_applicable": bool}
  /// Response: {"id": int, "is_applicable": bool, ...}
  Future<TaskItem> toggleTaskApplicable({
    required int taskId,
    required bool isApplicable,
  }) async {
    try {
      final response = await _apiService.put(
        '/app/task/toggle-applicable',
        data: {
          'task_id': taskId,
          'is_applicable': isApplicable,
        },
      );
      return TaskItem.fromJson(response);
    } catch (e) {
      rethrow;
    }
  }
}
