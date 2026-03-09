/// Worker 모델 (작업자)
///
/// DB 테이블: workers
/// 역할: MECH(기구), ELEC(전장), TM(TMS반제품), PI(가압검사), QI(공정검사), SI(출하검사)
/// 승인 상태: pending(대기), approved(승인), rejected(거절)
/// 협력사: FNI, BAT, TMS(M), TMS(E), P&S, C&A, GST
class Worker {
  final int id;
  final String name;
  final String email;
  final String role; // MECH, ELEC, TM, PI, QI, SI, ADMIN
  final String? company; // FNI, BAT, TMS(M), TMS(E), P&S, C&A, GST
  final String approvalStatus; // pending, approved, rejected
  final bool emailVerified;
  final bool isManager;
  final bool isAdmin;
  final DateTime createdAt;
  final DateTime? updatedAt;
  final String? activeRole; // GST 작업자의 현재 활성 역할 (PI, QI, SI)

  Worker({
    required this.id,
    required this.name,
    required this.email,
    required this.role,
    this.company,
    required this.approvalStatus,
    required this.emailVerified,
    required this.isManager,
    required this.isAdmin,
    required this.createdAt,
    this.updatedAt,
    this.activeRole,
  });

  /// JSON에서 Worker 객체 생성
  ///
  /// BE API 응답 형식:
  /// ```json
  /// {
  ///   "id": 1,
  ///   "name": "홍길동",
  ///   "email": "hong@example.com",
  ///   "role": "MECH",
  ///   "company": "FNI",
  ///   "approval_status": "approved",
  ///   "email_verified": true,
  ///   "is_manager": false,
  ///   "is_admin": false,
  ///   "created_at": "2026-02-16T10:00:00Z",
  ///   "updated_at": "2026-02-16T11:00:00Z",
  ///   "active_role": "PI"
  /// }
  /// ```
  factory Worker.fromJson(Map<String, dynamic> json) {
    return Worker(
      id: json['id'] as int? ?? json['worker_id'] as int? ?? 0,
      name: json['name'] as String? ?? '',
      email: json['email'] as String? ?? '',
      role: json['role'] as String? ?? '',
      company: json['company'] as String?,
      approvalStatus: json['approval_status'] as String? ?? 'pending',
      emailVerified: json['email_verified'] as bool? ?? false,
      isManager: json['is_manager'] as bool? ?? false,
      isAdmin: json['is_admin'] as bool? ?? false,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'] as String)
          : DateTime.now(),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'] as String)
          : null,
      activeRole: json['active_role'] as String?,
    );
  }

  /// Worker 객체를 JSON으로 변환
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'email': email,
      'role': role,
      'company': company,
      'approval_status': approvalStatus,
      'email_verified': emailVerified,
      'is_manager': isManager,
      'is_admin': isAdmin,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
      'active_role': activeRole,
    };
  }

  /// Worker 객체 복사 (불변성 유지)
  Worker copyWith({
    int? id,
    String? name,
    String? email,
    String? role,
    String? company,
    String? approvalStatus,
    bool? emailVerified,
    bool? isManager,
    bool? isAdmin,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? activeRole,
    bool clearActiveRole = false,
  }) {
    return Worker(
      id: id ?? this.id,
      name: name ?? this.name,
      email: email ?? this.email,
      role: role ?? this.role,
      company: company ?? this.company,
      approvalStatus: approvalStatus ?? this.approvalStatus,
      emailVerified: emailVerified ?? this.emailVerified,
      isManager: isManager ?? this.isManager,
      isAdmin: isAdmin ?? this.isAdmin,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      activeRole: clearActiveRole ? null : (activeRole ?? this.activeRole),
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
      case 'MECH':
        return '기구';
      case 'ELEC':
        return '전장';
      case 'TM':
        return 'TMS반제품';
      case 'PI':
        return '가압검사';
      case 'QI':
        return '공정검사';
      case 'SI':
        return '출하검사';
      case 'PM':
        return '생산관리';
      case 'ADMIN':
        return '마스터 관리자';
      default:
        return role;
    }
  }

  @override
  String toString() {
    return 'Worker(id: $id, name: $name, email: $email, role: $role, '
        'company: $company, approvalStatus: $approvalStatus, emailVerified: $emailVerified)';
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;

    return other is Worker &&
        other.id == id &&
        other.name == name &&
        other.email == email &&
        other.role == role &&
        other.company == company &&
        other.approvalStatus == approvalStatus &&
        other.emailVerified == emailVerified &&
        other.isManager == isManager &&
        other.isAdmin == isAdmin &&
        other.createdAt == createdAt &&
        other.updatedAt == updatedAt &&
        other.activeRole == activeRole;
  }

  @override
  int get hashCode {
    return Object.hash(
      id,
      name,
      email,
      role,
      company,
      approvalStatus,
      emailVerified,
      isManager,
      isAdmin,
      createdAt,
      updatedAt,
      activeRole,
    );
  }
}
