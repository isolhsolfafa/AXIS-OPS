// ignore_for_file: avoid_web_libraries_in_flutter
import 'dart:async';
import 'package:flutter/foundation.dart';

// 웹 전용 조건부 import
import 'qr_scanner_web.dart' if (dart.library.io) 'qr_scanner_stub.dart'
    as qr_impl;

/// QR 스캐너 서비스 (html5-qrcode JS 라이브러리 래퍼)
///
/// 웹 전용: html5-qrcode 라이브러리를 Dart에서 JS interop으로 호출
/// 비웹 환경에서는 stub 구현체 사용
class QrScannerService {
  static final QrScannerService _instance = QrScannerService._internal();
  factory QrScannerService() => _instance;
  QrScannerService._internal();

  bool _isRunning = false;

  bool get isRunning => _isRunning;

  /// QR 스캐너 시작
  ///
  /// [elementId]: 카메라 미리보기를 렌더링할 HTML 요소 ID
  /// [onResult]: QR 코드 인식 성공 콜백
  /// [onError]: 에러 콜백 (선택적)
  /// [containerLeft/Top/Width/Height]: Flutter 카메라 컨테이너의 화면 좌표
  Future<bool> start({
    required String elementId,
    required void Function(String qrCode) onResult,
    void Function(String error)? onError,
    double? containerLeft,
    double? containerTop,
    double? containerWidth,
    double? containerHeight,
  }) async {
    if (_isRunning) {
      await stop();
    }
    try {
      final success = await qr_impl.startQrScanner(
        elementId: elementId,
        onResult: onResult,
        onError: onError,
        containerLeft: containerLeft,
        containerTop: containerTop,
        containerWidth: containerWidth,
        containerHeight: containerHeight,
      );
      _isRunning = success;
      return success;
    } catch (e) {
      debugPrint('[QrScannerService] start failed: $e');
      _isRunning = false;
      return false;
    }
  }

  /// DOM 스캐너 div 위치 업데이트 (스크롤 대응)
  void updatePosition({
    required double left,
    required double top,
    required double width,
    required double height,
  }) {
    qr_impl.updateScannerDivPosition(
      left: left,
      top: top,
      width: width,
      height: height,
    );
  }

  /// QR 스캐너 중지
  Future<void> stop() async {
    if (!_isRunning) return;
    try {
      await qr_impl.stopQrScanner();
    } catch (e) {
      debugPrint('[QrScannerService] stop failed: $e');
    } finally {
      _isRunning = false;
    }
  }

  /// 사용 가능한 카메라 목록 조회
  Future<List<Map<String, String>>> getCameras() async {
    try {
      return await qr_impl.getQrCameras();
    } catch (e) {
      debugPrint('[QrScannerService] getCameras failed: $e');
      return [];
    }
  }
}
