/// Worker 모델 (작업자)
///
/// DB 테이블: workers
/// 역할: MM(기구), EE(전장), TM(TMS반제품), PI(가압검사), QI(공정검사), SI(출하검사)
/// 승인 상태: pending(대기), approved(승인), rejected(거절)
class Worker {
  final int id;
  final String name;
  final String email;
  final String role; // MM, EE, TM, PI, QI, SI
  final String approvalStatus; // pending, approved, rejected
  final bool emailVerified;
  final bool isManager;
  final bool isAdmin;
  final DateTime createdAt;
  final DateTime? updatedAt;

  Worker({
    required this.id,
    required this.name,
    required this.email,
    required this.role,
    required this.approvalStatus,
    required this.emailVerified,
    required this.isManager,
    required this.isAdmin,
    required this.createdAt,
    this.updatedAt,
  });

  /// JSON에서 Worker 객체 생성
  ///
  /// BE API 응답 형식:
  /// ```json
  /// {
  ///   "id": 1,
  ///   "name": "홍길동",
  ///   "email": "hong@example.com",
  ///   "role": "MM",
  ///   "approval_status": "approved",
  ///   "email_verified": true,
  ///   "is_manager": false,
  ///   "is_admin": false,
  ///   "created_at": "2026-02-16T10:00:00Z",
  ///   "updated_at": "2026-02-16T11:00:00Z"
  /// }
  /// ```
  factory Worker.fromJson(Map<String, dynamic> json) {
    return Worker(
      id: json['id'] as int? ?? json['worker_id'] as int,
      name: json['name'] as String,
      email: json['email'] as String,
      role: json['role'] as String,
      approvalStatus: json['approval_status'] as String? ?? 'pending',
      emailVerified: json['email_verified'] as bool? ?? false,
      isManager: json['is_manager'] as bool? ?? false,
      isAdmin: json['is_admin'] as bool? ?? false,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'] as String)
          : null,
    );
  }

  /// Worker 객체를 JSON으로 변환
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'email': email,
      'role': role,
      'approval_status': approvalStatus,
      'email_verified': emailVerified,
      'is_manager': isManager,
      'is_admin': isAdmin,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
    };
  }

  /// Worker 객체 복사 (불변성 유지)
  Worker copyWith({
    int? id,
    String? name,
    String? email,
    String? role,
    String? approvalStatus,
    bool? emailVerified,
    bool? isManager,
    bool? isAdmin,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return Worker(
      id: id ?? this.id,
      name: name ?? this.name,
      email: email ?? this.email,
      role: role ?? this.role,
      approvalStatus: approvalStatus ?? this.approvalStatus,
      emailVerified: emailVerified ?? this.emailVerified,
      isManager: isManager ?? this.isManager,
      isAdmin: isAdmin ?? this.isAdmin,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  /// 승인 상태 확인
  bool get isApproved => approvalStatus == 'approved';

  /// 승인 대기 상태 확인
  bool get isPending => approvalStatus == 'pending';

  /// 승인 거절 상태 확인
  bool get isRejected => approvalStatus == 'rejected';

  /// 역할 이름 반환 (한글)
  String get roleDisplayName {
    switch (role) {
      case 'MM':
        return '기구';
      case 'EE':
        return '전장';
      case 'TM':
        return 'TMS반제품';
      case 'PI':
        return '가압검사';
      case 'QI':
        return '공정검사';
      case 'SI':
        return '출하검사';
      default:
        return role;
    }
  }

  @override
  String toString() {
    return 'Worker(id: $id, name: $name, email: $email, role: $role, '
        'approvalStatus: $approvalStatus, emailVerified: $emailVerified)';
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;

    return other is Worker &&
        other.id == id &&
        other.name == name &&
        other.email == email &&
        other.role == role &&
        other.approvalStatus == approvalStatus &&
        other.emailVerified == emailVerified &&
        other.isManager == isManager &&
        other.isAdmin == isAdmin &&
        other.createdAt == createdAt &&
        other.updatedAt == updatedAt;
  }

  @override
  int get hashCode {
    return Object.hash(
      id,
      name,
      email,
      role,
      approvalStatus,
      emailVerified,
      isManager,
      isAdmin,
      createdAt,
      updatedAt,
    );
  }
}
