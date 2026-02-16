/// AlertLog 모델 (알림 로그)
///
/// DB 테이블: app_alert_logs
/// 공정 경고, 비정상 duration, 작업자 승인/거부 등 시스템 알림 추적
///
/// 알림 타입 (alert_type_enum):
/// - PROCESS_READY: 다음 공정 준비 알림
/// - UNFINISHED_AT_CLOSING: 마감 시 미완료 작업 알림
/// - DURATION_EXCEEDED: 비정상 소요시간 알림 (>14시간)
/// - REVERSE_COMPLETION: 역순 완료 경고
/// - DUPLICATE_COMPLETION: 중복 완료 경고
/// - LOCATION_QR_FAILED: 장소 QR 검증 실패
/// - WORKER_APPROVED: 작업자 승인
/// - WORKER_REJECTED: 작업자 거부
class AlertLog {
  final int id;
  final String alertType;
  final String? serialNumber; // QR 문서에서 추출한 시리얼 번호
  final String? qrDocId;
  final int? workerId;
  final String message;
  final String? targetRole; // 알림 대상 역할 (ADMIN, PI, QI, SI 등)
  final bool isRead;
  final DateTime? readAt;
  final DateTime createdAt;
  final DateTime? updatedAt;

  AlertLog({
    required this.id,
    required this.alertType,
    this.serialNumber,
    this.qrDocId,
    this.workerId,
    required this.message,
    this.targetRole,
    this.isRead = false,
    this.readAt,
    required this.createdAt,
    this.updatedAt,
  });

  /// JSON에서 AlertLog 객체 생성
  ///
  /// BE API 응답 형식:
  /// ```json
  /// {
  ///   "id": 1,
  ///   "alert_type": "PROCESS_READY",
  ///   "serial_number": "GBWS-6408",
  ///   "qr_doc_id": "DOC_GBWS-6408",
  ///   "worker_id": 5,
  ///   "message": "PI 공정이 완료되었습니다. QI 작업을 시작하세요.",
  ///   "target_role": "QI",
  ///   "is_read": false,
  ///   "read_at": null,
  ///   "created_at": "2026-02-16T10:00:00Z",
  ///   "updated_at": null
  /// }
  /// ```
  factory AlertLog.fromJson(Map<String, dynamic> json) {
    return AlertLog(
      id: json['id'] as int,
      alertType: json['alert_type'] as String,
      serialNumber: json['serial_number'] as String?,
      qrDocId: json['qr_doc_id'] as String?,
      workerId: json['worker_id'] as int?,
      message: json['message'] as String,
      targetRole: json['target_role'] as String?,
      isRead: json['is_read'] as bool? ?? false,
      readAt: json['read_at'] != null
          ? DateTime.parse(json['read_at'] as String)
          : null,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'] as String)
          : null,
    );
  }

  /// AlertLog 객체를 JSON으로 변환
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'alert_type': alertType,
      'serial_number': serialNumber,
      'qr_doc_id': qrDocId,
      'worker_id': workerId,
      'message': message,
      'target_role': targetRole,
      'is_read': isRead,
      'read_at': readAt?.toIso8601String(),
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
    };
  }

  /// AlertLog 객체 복사 (불변성 유지)
  AlertLog copyWith({
    int? id,
    String? alertType,
    String? serialNumber,
    String? qrDocId,
    int? workerId,
    String? message,
    String? targetRole,
    bool? isRead,
    DateTime? readAt,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return AlertLog(
      id: id ?? this.id,
      alertType: alertType ?? this.alertType,
      serialNumber: serialNumber ?? this.serialNumber,
      qrDocId: qrDocId ?? this.qrDocId,
      workerId: workerId ?? this.workerId,
      message: message ?? this.message,
      targetRole: targetRole ?? this.targetRole,
      isRead: isRead ?? this.isRead,
      readAt: readAt ?? this.readAt,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  /// 알림 우선순위 (높을수록 긴급)
  int get priority {
    switch (alertType) {
      case 'DURATION_EXCEEDED':
      case 'REVERSE_COMPLETION':
        return 3; // 높음
      case 'PROCESS_READY':
      case 'UNFINISHED_AT_CLOSING':
        return 2; // 중간
      default:
        return 1; // 낮음
    }
  }

  /// 알림 아이콘 이름 (Flutter Icons 기준)
  String get iconName {
    switch (alertType) {
      case 'PROCESS_READY':
        return 'notifications_active';
      case 'UNFINISHED_AT_CLOSING':
        return 'warning';
      case 'DURATION_EXCEEDED':
        return 'timer_off';
      case 'REVERSE_COMPLETION':
      case 'DUPLICATE_COMPLETION':
        return 'error_outline';
      case 'LOCATION_QR_FAILED':
        return 'qr_code_scanner';
      case 'WORKER_APPROVED':
        return 'check_circle';
      case 'WORKER_REJECTED':
        return 'cancel';
      default:
        return 'info';
    }
  }

  @override
  String toString() {
    return 'AlertLog(id: $id, alertType: $alertType, message: $message, '
        'isRead: $isRead, createdAt: $createdAt)';
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;

    return other is AlertLog &&
        other.id == id &&
        other.alertType == alertType &&
        other.serialNumber == serialNumber &&
        other.qrDocId == qrDocId &&
        other.workerId == workerId &&
        other.message == message &&
        other.targetRole == targetRole &&
        other.isRead == isRead &&
        other.readAt == readAt &&
        other.createdAt == createdAt &&
        other.updatedAt == updatedAt;
  }

  @override
  int get hashCode {
    return Object.hash(
      id,
      alertType,
      serialNumber,
      qrDocId,
      workerId,
      message,
      targetRole,
      isRead,
      readAt,
      createdAt,
      updatedAt,
    );
  }
}
