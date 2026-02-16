/// TaskItem 모델 (작업 Task)
///
/// DB 테이블: app_task_details
/// 작업자별 Task 추적: 시작/완료 타임스탬프, 소요시간, 적용 여부
///
/// 스키마 변경사항 (2026-02-16):
/// - duration_minutes: 분 단위로 변경 (seconds → minutes)
/// - process_type 필드 제거: task_category와 중복
class TaskItem {
  final int id;
  final int workerId;
  final String serialNumber;
  final String qrDocId;
  final String taskCategory; // 기구, 전장, TMS반제품, 가압검사, 공정검사, 출하검사 (MM, EE, TM, PI, QI, SI)
  final String taskId; // Task 식별자 (예: CABINET_ASSY)
  final String taskName; // Task 이름 (예: 캐비넷 조립)
  final DateTime? startedAt;
  final DateTime? completedAt;
  final int? durationMinutes; // 소요시간 (분 단위, completed_at - started_at)
  final bool isApplicable; // Task 적용 여부 (관리자/사내직원이 비활성화 가능)
  final bool locationQrVerified;
  final DateTime createdAt;
  final DateTime? updatedAt;

  TaskItem({
    required this.id,
    required this.workerId,
    required this.serialNumber,
    required this.qrDocId,
    required this.taskCategory,
    required this.taskId,
    required this.taskName,
    this.startedAt,
    this.completedAt,
    this.durationMinutes,
    this.isApplicable = true,
    this.locationQrVerified = false,
    required this.createdAt,
    this.updatedAt,
  });

  /// JSON에서 TaskItem 객체 생성
  ///
  /// BE API 응답 형식:
  /// ```json
  /// {
  ///   "id": 1,
  ///   "worker_id": 5,
  ///   "serial_number": "GBWS-6408",
  ///   "qr_doc_id": "DOC_GBWS-6408",
  ///   "task_category": "MM",
  ///   "task_id": "CABINET_ASSY",
  ///   "task_name": "캐비넷 조립",
  ///   "started_at": "2026-02-16T10:00:00Z",
  ///   "completed_at": "2026-02-16T11:30:00Z",
  ///   "duration_minutes": 90,
  ///   "is_applicable": true,
  ///   "location_qr_verified": true,
  ///   "created_at": "2026-02-16T09:00:00Z",
  ///   "updated_at": "2026-02-16T11:30:00Z"
  /// }
  /// ```
  factory TaskItem.fromJson(Map<String, dynamic> json) {
    return TaskItem(
      id: json['id'] as int,
      workerId: json['worker_id'] as int,
      serialNumber: json['serial_number'] as String,
      qrDocId: json['qr_doc_id'] as String,
      taskCategory: json['task_category'] as String,
      taskId: json['task_id'] as String,
      taskName: json['task_name'] as String,
      startedAt: json['started_at'] != null
          ? DateTime.parse(json['started_at'] as String)
          : null,
      completedAt: json['completed_at'] != null
          ? DateTime.parse(json['completed_at'] as String)
          : null,
      durationMinutes: json['duration_minutes'] as int?,
      isApplicable: json['is_applicable'] as bool? ?? true,
      locationQrVerified: json['location_qr_verified'] as bool? ?? false,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'] as String)
          : null,
    );
  }

  /// TaskItem 객체를 JSON으로 변환
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'worker_id': workerId,
      'serial_number': serialNumber,
      'qr_doc_id': qrDocId,
      'task_category': taskCategory,
      'task_id': taskId,
      'task_name': taskName,
      'started_at': startedAt?.toIso8601String(),
      'completed_at': completedAt?.toIso8601String(),
      'duration_minutes': durationMinutes,
      'is_applicable': isApplicable,
      'location_qr_verified': locationQrVerified,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
    };
  }

  /// TaskItem 객체 복사 (불변성 유지)
  TaskItem copyWith({
    int? id,
    int? workerId,
    String? serialNumber,
    String? qrDocId,
    String? taskCategory,
    String? taskId,
    String? taskName,
    DateTime? startedAt,
    DateTime? completedAt,
    int? durationMinutes,
    bool? isApplicable,
    bool? locationQrVerified,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return TaskItem(
      id: id ?? this.id,
      workerId: workerId ?? this.workerId,
      serialNumber: serialNumber ?? this.serialNumber,
      qrDocId: qrDocId ?? this.qrDocId,
      taskCategory: taskCategory ?? this.taskCategory,
      taskId: taskId ?? this.taskId,
      taskName: taskName ?? this.taskName,
      startedAt: startedAt ?? this.startedAt,
      completedAt: completedAt ?? this.completedAt,
      durationMinutes: durationMinutes ?? this.durationMinutes,
      isApplicable: isApplicable ?? this.isApplicable,
      locationQrVerified: locationQrVerified ?? this.locationQrVerified,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  /// Task 상태 확인
  String get status {
    if (completedAt != null) return 'completed';
    if (startedAt != null) return 'in_progress';
    return 'pending';
  }

  /// Task 진행률 (0.0 ~ 1.0)
  double get progress {
    if (completedAt != null) return 1.0;
    if (startedAt != null) return 0.5;
    return 0.0;
  }

  /// 소요시간 포맷 (HH:MM)
  String get durationFormatted {
    if (durationMinutes == null) return '--:--';
    final hours = durationMinutes! ~/ 60;
    final minutes = durationMinutes! % 60;
    return '${hours.toString().padLeft(2, '0')}:'
        '${minutes.toString().padLeft(2, '0')}';
  }

  /// 비정상 duration 체크 (> 14시간 = 840분)
  bool get hasAbnormalDuration {
    if (durationMinutes == null) return false;
    return durationMinutes! > 840; // 14시간 = 840분
  }

  @override
  String toString() {
    return 'TaskItem(id: $id, taskName: $taskName, status: $status, '
        'duration: $durationFormatted)';
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;

    return other is TaskItem &&
        other.id == id &&
        other.workerId == workerId &&
        other.serialNumber == serialNumber &&
        other.qrDocId == qrDocId &&
        other.taskCategory == taskCategory &&
        other.taskId == taskId &&
        other.taskName == taskName &&
        other.startedAt == startedAt &&
        other.completedAt == completedAt &&
        other.durationMinutes == durationMinutes &&
        other.isApplicable == isApplicable &&
        other.locationQrVerified == locationQrVerified &&
        other.createdAt == createdAt &&
        other.updatedAt == updatedAt;
  }

  @override
  int get hashCode {
    return Object.hash(
      id,
      workerId,
      serialNumber,
      qrDocId,
      taskCategory,
      taskId,
      taskName,
      startedAt,
      completedAt,
      durationMinutes,
      isApplicable,
      locationQrVerified,
      createdAt,
      updatedAt,
    );
  }
}
