// QR 스캐너 Stub (비웹 환경용)
// Flutter Web이 아닌 환경에서는 이 stub이 사용됩니다.
// 실제 QR 스캔은 지원되지 않으며, 항상 실패를 반환합니다.

void updateScannerDivPosition({
  required double left,
  required double top,
  required double width,
  required double height,
}) {}

Future<bool> startQrScanner({
  required String elementId,
  required void Function(String qrCode) onResult,
  void Function(String error)? onError,
  double? containerLeft,
  double? containerTop,
  double? containerWidth,
  double? containerHeight,
}) async {
  onError?.call('QR 스캔은 웹 환경에서만 지원됩니다.');
  return false;
}

Future<void> stopQrScanner() async {}

Future<List<Map<String, String>>> getQrCameras() async {
  return [];
}
