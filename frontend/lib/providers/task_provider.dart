import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/product_info.dart';
import '../models/task_item.dart';
import '../services/task_service.dart';
import 'auth_provider.dart';

/// Task 상태 클래스
///
/// Task 목록, 제품 정보, 공정 완료 상태, 로딩 상태, 에러 메시지 등을 관리
class TaskState {
  final bool isLoading;
  final String? errorMessage;
  final ProductInfo? currentProduct; // 현재 선택된 제품
  final List<TaskItem> tasks; // 현재 제품의 Task 목록
  final Map<String, dynamic>? completionStatus; // 공정 완료 상태
  final TaskItem? selectedTask; // 선택된 Task (상세 화면용)

  const TaskState({
    this.isLoading = false,
    this.errorMessage,
    this.currentProduct,
    this.tasks = const [],
    this.completionStatus,
    this.selectedTask,
  });

  TaskState copyWith({
    bool? isLoading,
    String? errorMessage,
    ProductInfo? currentProduct,
    List<TaskItem>? tasks,
    Map<String, dynamic>? completionStatus,
    TaskItem? selectedTask,
    bool clearError = false,
    bool clearProduct = false,
    bool clearTasks = false,
    bool clearCompletionStatus = false,
    bool clearSelectedTask = false,
  }) {
    return TaskState(
      isLoading: isLoading ?? this.isLoading,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
      currentProduct:
          clearProduct ? null : (currentProduct ?? this.currentProduct),
      tasks: clearTasks ? const [] : (tasks ?? this.tasks),
      completionStatus: clearCompletionStatus
          ? null
          : (completionStatus ?? this.completionStatus),
      selectedTask:
          clearSelectedTask ? null : (selectedTask ?? this.selectedTask),
    );
  }

  /// 현재 제품의 시리얼 번호
  String? get currentSerialNumber => currentProduct?.serialNumber;

  /// 현재 제품의 QR 문서 ID
  String? get currentQrDocId => currentProduct?.qrDocId;

  /// Task 진행률 (0.0 ~ 1.0)
  double get taskProgress {
    if (tasks.isEmpty) return 0.0;
    final completedCount = tasks.where((task) => task.status == 'completed').length;
    return completedCount / tasks.length;
  }

  /// 완료된 Task 수
  int get completedTaskCount =>
      tasks.where((task) => task.status == 'completed').length;

  /// 진행 중인 Task 수
  int get inProgressTaskCount =>
      tasks.where((task) => task.status == 'in_progress').length;

  /// 대기 중인 Task 수
  int get pendingTaskCount =>
      tasks.where((task) => task.status == 'pending').length;

  @override
  String toString() {
    return 'TaskState(isLoading: $isLoading, product: ${currentProduct?.serialNumber}, '
        'tasks: ${tasks.length}, completed: $completedTaskCount, error: $errorMessage)';
  }
}

/// Task 상태 관리 Notifier
///
/// QR 스캔, Task 목록 조회, 작업 시작/완료, 공정 검증 등의 비즈니스 로직 처리
class TaskNotifier extends StateNotifier<TaskState> {
  final TaskService _taskService;

  TaskNotifier(this._taskService) : super(const TaskState());

  /// Exception에서 사용자 친화적 에러 메시지 추출
  /// ApiService가 이미 [ERROR_CODE] message 형식으로 변환하므로
  /// "Exception: " 접두사만 제거하여 반환
  String _extractErrorMessage(Object e) {
    final raw = e.toString();
    if (raw.startsWith('Exception: ')) {
      return raw.substring('Exception: '.length);
    }
    return raw;
  }

  /// QR 스캔 → 제품 조회
  ///
  /// [qrDocId]: QR 문서 ID (예: DOC_GBWS-6408)
  ///
  /// Returns: 조회 성공 여부
  Future<bool> scanQrCode(String qrDocId) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final product = await _taskService.getProductByQrDocId(qrDocId);
      state = state.copyWith(
        isLoading: false,
        currentProduct: product,
      );
      return true;
    } on ProductShippedException {
      state = state.copyWith(isLoading: false);
      rethrow;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.toString(),
      );
      return false;
    }
  }

  /// Location QR 등록
  ///
  /// [locationQrId]: Location QR ID (예: LOC_ASSY_01)
  ///
  /// Returns: 등록 성공 여부
  Future<bool> updateLocation(String locationQrId) async {
    if (state.currentQrDocId == null) {
      state = state.copyWith(
        errorMessage: 'Worksheet QR을 먼저 스캔해주세요.',
      );
      return false;
    }

    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final updatedProduct = await _taskService.updateLocation(
        qrDocId: state.currentQrDocId!,
        locationQrId: locationQrId,
      );
      state = state.copyWith(
        isLoading: false,
        currentProduct: updatedProduct,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.toString(),
      );
      return false;
    }
  }

  /// 역할별 Task 목록 조회
  ///
  /// [serialNumber]: 제품 시리얼 번호
  /// [workerId]: 작업자 ID
  ///
  /// Returns: 조회 성공 여부
  Future<bool> fetchTasks({
    required String serialNumber,
    required int workerId,
    String? qrDocId,
  }) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final tasks = await _taskService.getTasksBySerialNumber(
        serialNumber: serialNumber,
        workerId: workerId,
        qrDocId: qrDocId,
      );
      state = state.copyWith(
        isLoading: false,
        tasks: tasks,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.toString(),
      );
      return false;
    }
  }

  /// 작업 시작
  ///
  /// [taskId]: app_task_details의 ID
  /// [workerId]: 작업자 ID
  ///
  /// Returns: 시작 성공 여부
  Future<bool> startTask({
    required int taskId,
    required int workerId,
  }) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final updatedTask = await _taskService.startTask(
        taskId: taskId,
        workerId: workerId,
      );

      // Task 목록 업데이트
      final updatedTasks = state.tasks.map((task) {
        return task.id == taskId ? updatedTask : task;
      }).toList();

      state = state.copyWith(
        isLoading: false,
        tasks: updatedTasks,
        selectedTask: updatedTask,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: _extractErrorMessage(e),
      );
      return false;
    }
  }

  /// 작업 완료
  ///
  /// [taskId]: app_task_details의 ID
  /// [workerId]: 작업자 ID
  ///
  /// Returns: 완료 성공 여부
  /// Returns: ({bool success, bool checklistReady})
  /// Sprint 52 BUG-FIX: checklistReady — 매니저 직접 완료 시 체크리스트 화면 전환용
  Future<({bool success, bool checklistReady})> completeTask({
    required int taskId,
    required int workerId,
    bool finalize = true,
  }) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final result = await _taskService.completeTask(
        taskId: taskId,
        workerId: workerId,
        finalize: finalize,
      );

      // Task 목록 업데이트
      final updatedTasks = state.tasks.map((task) {
        return task.id == taskId ? result.task : task;
      }).toList();

      state = state.copyWith(
        isLoading: false,
        tasks: updatedTasks,
        selectedTask: result.task,
      );

      // 완료 후 공정 완료 상태 새로고침
      if (state.currentSerialNumber != null) {
        await refreshCompletionStatus(state.currentSerialNumber!);
      }

      return (success: true, checklistReady: result.checklistReady);
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: _extractErrorMessage(e),
      );
      return (success: false, checklistReady: false);
    }
  }

  /// 단일 액션 Task 완료 (Sprint 27)
  Future<bool> completeSingleAction({required int taskDetailId}) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final updatedTask = await _taskService.completeSingleAction(
        taskDetailId: taskDetailId,
      );

      final updatedTasks = state.tasks.map((task) {
        return task.id == taskDetailId ? updatedTask : task;
      }).toList();

      state = state.copyWith(
        isLoading: false,
        tasks: updatedTasks,
        selectedTask: updatedTask,
      );

      if (state.currentSerialNumber != null) {
        await refreshCompletionStatus(state.currentSerialNumber!);
      }

      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: _extractErrorMessage(e),
      );
      return false;
    }
  }

  /// 공정 완료 상태 조회
  ///
  /// [serialNumber]: 제품 시리얼 번호
  ///
  /// Returns: 조회 성공 여부
  Future<bool> refreshCompletionStatus(String serialNumber) async {
    try {
      final status = await _taskService.getCompletionStatus(serialNumber);
      state = state.copyWith(completionStatus: status);
      return true;
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
      return false;
    }
  }

  /// 공정 누락 검증 (PI/QI/SI용)
  ///
  /// [serialNumber]: 제품 시리얼 번호
  /// [processType]: 공정 타입 (PI, QI, SI)
  ///
  /// Returns: 검증 결과 (valid, missing_processes, location_qr_verified, message)
  Future<Map<String, dynamic>?> validateProcess({
    required String serialNumber,
    required String processType,
  }) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final validationResult = await _taskService.validateProcess(
        serialNumber: serialNumber,
        processType: processType,
      );
      state = state.copyWith(isLoading: false);
      return validationResult;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.toString(),
      );
      return null;
    }
  }

  /// Task 선택 (상세 화면용)
  void selectTask(TaskItem task) {
    state = state.copyWith(selectedTask: task);
  }

  /// Task 선택 해제
  void clearSelectedTask() {
    state = state.copyWith(clearSelectedTask: true);
  }

  /// 에러 메시지 클리어
  void clearError() {
    state = state.copyWith(clearError: true);
  }

  /// 현재 제품 클리어 (새 QR 스캔 준비)
  void clearCurrentProduct() {
    state = state.copyWith(
      clearProduct: true,
      clearTasks: true,
      clearCompletionStatus: true,
      clearSelectedTask: true,
    );
  }

  /// 작업 일시정지
  ///
  /// [taskDetailId]: app_task_details의 ID
  ///
  /// Returns: 성공 여부
  Future<bool> pauseTask({required int taskDetailId}) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final updatedTask = await _taskService.pauseTask(taskDetailId: taskDetailId);

      final updatedTasks = state.tasks.map((task) {
        return task.id == taskDetailId ? updatedTask : task;
      }).toList();

      state = state.copyWith(
        isLoading: false,
        tasks: updatedTasks,
        selectedTask: updatedTask,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.toString(),
      );
      return false;
    }
  }

  /// 작업 재개
  ///
  /// [taskDetailId]: app_task_details의 ID
  ///
  /// Returns: 성공 여부
  Future<bool> resumeTask({required int taskDetailId}) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final updatedTask = await _taskService.resumeTask(taskDetailId: taskDetailId);

      final updatedTasks = state.tasks.map((task) {
        return task.id == taskDetailId ? updatedTask : task;
      }).toList();

      state = state.copyWith(
        isLoading: false,
        tasks: updatedTasks,
        selectedTask: updatedTask,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.toString(),
      );
      return false;
    }
  }

  /// Task 비활성화 (관리자/사내직원 전용)
  Future<bool> toggleTaskApplicable({
    required int taskId,
    required bool isApplicable,
  }) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final updatedTask = await _taskService.toggleTaskApplicable(
        taskId: taskId,
        isApplicable: isApplicable,
      );

      // Task 목록 업데이트
      final updatedTasks = state.tasks.map((task) {
        return task.id == taskId ? updatedTask : task;
      }).toList();

      state = state.copyWith(
        isLoading: false,
        tasks: updatedTasks,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.toString(),
      );
      return false;
    }
  }
}

/// TaskService Provider — 공유 ApiService 사용 (JWT 토큰 공유)
final taskServiceProvider = Provider<TaskService>((ref) {
  final apiService = ref.watch(apiServiceProvider);
  return TaskService(apiService: apiService);
});

/// TaskNotifier Provider
final taskProvider = StateNotifierProvider<TaskNotifier, TaskState>((ref) {
  final taskService = ref.watch(taskServiceProvider);
  return TaskNotifier(taskService);
});
