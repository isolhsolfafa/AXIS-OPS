/// ProductInfo 모델 (제품 정보)
///
/// DB 테이블: product_info
/// QR 코드 기반 제품 조회 + Location 추적 + TMS 분기 지원
class ProductInfo {
  final int id;
  final String qrDocId;
  final String serialNumber;
  final String model;
  final DateTime prodDate;
  final String? locationQrId;
  final String? mechPartner;
  final String? elecPartner;
  final String? moduleOutsourcing;
  final DateTime createdAt;
  final DateTime? updatedAt;

  ProductInfo({
    required this.id,
    required this.qrDocId,
    required this.serialNumber,
    required this.model,
    required this.prodDate,
    this.locationQrId,
    this.mechPartner,
    this.elecPartner,
    this.moduleOutsourcing,
    required this.createdAt,
    this.updatedAt,
  });

  /// JSON에서 ProductInfo 객체 생성
  ///
  /// BE API 응답 형식:
  /// ```json
  /// {
  ///   "id": 1,
  ///   "qr_doc_id": "DOC_GBWS-6408",
  ///   "serial_number": "GBWS-6408",
  ///   "model": "GBWS",
  ///   "prod_date": "2026-02-16",
  ///   "location_qr_id": "LOC_ASSY_01",
  ///   "mech_partner": "협력사A",
  ///   "module_outsourcing": "TMS",
  ///   "created_at": "2026-02-16T10:00:00Z",
  ///   "updated_at": "2026-02-16T11:00:00Z"
  /// }
  /// ```
  factory ProductInfo.fromJson(Map<String, dynamic> json) {
    return ProductInfo(
      id: (json['id'] as num?)?.toInt() ?? 0,
      qrDocId: json['qr_doc_id'] as String,
      serialNumber: json['serial_number'] as String,
      model: json['model'] as String,
      prodDate: DateTime.parse(json['prod_date'] as String),
      locationQrId: json['location_qr_id'] as String?,
      mechPartner: json['mech_partner'] as String?,
      elecPartner: json['elec_partner'] as String?,
      moduleOutsourcing: json['module_outsourcing'] as String?,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'] as String)
          : DateTime.now(),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'] as String)
          : null,
    );
  }

  /// ProductInfo 객체를 JSON으로 변환
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'qr_doc_id': qrDocId,
      'serial_number': serialNumber,
      'model': model,
      'prod_date': prodDate.toIso8601String().split('T')[0], // YYYY-MM-DD
      'location_qr_id': locationQrId,
      'mech_partner': mechPartner,
      'elec_partner': elecPartner,
      'module_outsourcing': moduleOutsourcing,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
    };
  }

  /// ProductInfo 객체 복사 (불변성 유지)
  ProductInfo copyWith({
    int? id,
    String? qrDocId,
    String? serialNumber,
    String? model,
    DateTime? prodDate,
    String? locationQrId,
    String? mechPartner,
    String? elecPartner,
    String? moduleOutsourcing,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return ProductInfo(
      id: id ?? this.id,
      qrDocId: qrDocId ?? this.qrDocId,
      serialNumber: serialNumber ?? this.serialNumber,
      model: model ?? this.model,
      prodDate: prodDate ?? this.prodDate,
      locationQrId: locationQrId ?? this.locationQrId,
      mechPartner: mechPartner ?? this.mechPartner,
      elecPartner: elecPartner ?? this.elecPartner,
      moduleOutsourcing: moduleOutsourcing ?? this.moduleOutsourcing,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  /// TMS 분기 여부 확인
  ///
  /// TMS 모듈 Task 조건:
  /// - mech_partner == "TMS" AND module_outsourcing == "TMS"
  bool get isTmsModule {
    return mechPartner == 'TMS' && moduleOutsourcing == 'TMS';
  }

  /// Location QR 등록 여부 확인
  bool get hasLocationQr => locationQrId != null && locationQrId!.isNotEmpty;

  @override
  String toString() {
    return 'ProductInfo(id: $id, qrDocId: $qrDocId, serialNumber: $serialNumber, '
        'model: $model, isTmsModule: $isTmsModule)';
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;

    return other is ProductInfo &&
        other.id == id &&
        other.qrDocId == qrDocId &&
        other.serialNumber == serialNumber &&
        other.model == model &&
        other.prodDate == prodDate &&
        other.locationQrId == locationQrId &&
        other.mechPartner == mechPartner &&
        other.elecPartner == elecPartner &&
        other.moduleOutsourcing == moduleOutsourcing &&
        other.createdAt == createdAt &&
        other.updatedAt == updatedAt;
  }

  @override
  int get hashCode {
    return Object.hash(
      id,
      qrDocId,
      serialNumber,
      model,
      prodDate,
      locationQrId,
      mechPartner,
      elecPartner,
      moduleOutsourcing,
      createdAt,
      updatedAt,
    );
  }
}
