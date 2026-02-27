// ignore_for_file: avoid_web_libraries_in_flutter
import 'dart:async';
import 'dart:js_util' as js_util;
import 'package:flutter/foundation.dart';

dynamic _scanner;

/// QR 스캐너 시작 (웹 구현 — dart:js_util 기반)
///
/// 카메라 우선순위:
/// 1. facingMode: environment (모바일 후면 카메라)
/// 2. facingMode: user (데스크톱/전면 카메라)
/// 3. 첫 번째 사용 가능한 카메라 ID
Future<bool> startQrScanner({
  required String elementId,
  required void Function(String qrCode) onResult,
  void Function(String error)? onError,
}) async {
  try {
    final html5QrcodeClass = js_util.getProperty(
      js_util.globalThis,
      'Html5Qrcode',
    );

    if (html5QrcodeClass == null) {
      onError?.call('html5-qrcode 라이브러리가 로드되지 않았습니다.');
      return false;
    }

    // DOM 요소 렌더링 대기 (HtmlElementView 타이밍 이슈 방지)
    await Future.delayed(const Duration(milliseconds: 800));

    _scanner = js_util.callConstructor(html5QrcodeClass, [elementId]);

    final config = js_util.jsify({
      'fps': 10,
      'qrbox': {'width': 250, 'height': 250},
      'aspectRatio': 1.0,
    });

    final successCallback = js_util.allowInterop((String decodedText, dynamic result) {
      onResult(decodedText);
    });

    final errorCallback = js_util.allowInterop((String errorMessage, dynamic error) {
      // QR 미인식은 정상 상태
    });

    // 1차 시도: 후면 카메라 (모바일)
    try {
      final envConstraints = js_util.jsify({'facingMode': 'environment'});
      final promise = js_util.callMethod(
        _scanner!,
        'start',
        [envConstraints, config, successCallback, errorCallback],
      );
      await js_util.promiseToFuture(promise);
      return true;
    } catch (e) {
      debugPrint('[QrScannerWeb] environment camera failed: $e');
    }

    // 2차 시도: 전면 카메라 (데스크톱/MacBook)
    try {
      _scanner = js_util.callConstructor(html5QrcodeClass, [elementId]);
      final userConstraints = js_util.jsify({'facingMode': 'user'});
      final promise = js_util.callMethod(
        _scanner!,
        'start',
        [userConstraints, config, successCallback, errorCallback],
      );
      await js_util.promiseToFuture(promise);
      return true;
    } catch (e) {
      debugPrint('[QrScannerWeb] user camera failed: $e');
    }

    // 3차 시도: 사용 가능한 첫 번째 카메라 ID로 직접 시도
    try {
      final camerasPromise = js_util.callMethod(html5QrcodeClass, 'getCameras', []);
      final cameras = await js_util.promiseToFuture(camerasPromise) as List<dynamic>;
      if (cameras.isNotEmpty) {
        final cameraId = js_util.getProperty(cameras[0] as Object, 'id') as String;
        _scanner = js_util.callConstructor(html5QrcodeClass, [elementId]);
        final promise = js_util.callMethod(
          _scanner!,
          'start',
          [cameraId, config, successCallback, errorCallback],
        );
        await js_util.promiseToFuture(promise);
        return true;
      }
    } catch (e) {
      debugPrint('[QrScannerWeb] camera ID fallback failed: $e');
    }

    onError?.call('사용 가능한 카메라를 찾을 수 없습니다.');
    _scanner = null;
    return false;
  } catch (e) {
    debugPrint('[QrScannerWeb] start failed: $e');
    _scanner = null;
    onError?.call('카메라 시작 실패: $e');
    return false;
  }
}

/// QR 스캐너 중지 (웹 구현)
Future<void> stopQrScanner() async {
  if (_scanner == null) return;
  try {
    final promise = js_util.callMethod(_scanner!, 'stop', []);
    await js_util.promiseToFuture(promise);
  } catch (_) {
    // 이미 중지됐거나 오류 — 무시
  } finally {
    _scanner = null;
  }
}

/// 사용 가능한 카메라 목록 (웹 구현)
Future<List<Map<String, String>>> getQrCameras() async {
  try {
    final html5QrcodeClass = js_util.getProperty(
      js_util.globalThis,
      'Html5Qrcode',
    );
    if (html5QrcodeClass == null) return [];

    final promise = js_util.callMethod(html5QrcodeClass, 'getCameras', []);
    final cameras = await js_util.promiseToFuture(promise) as List<dynamic>;

    return cameras.map((cam) {
      final id = js_util.getProperty(cam as Object, 'id') as String? ?? '';
      final label = js_util.getProperty(cam, 'label') as String? ?? '';
      return {'id': id, 'label': label};
    }).toList();
  } catch (e) {
    debugPrint('[QrScannerWeb] getCameras failed: $e');
    return [];
  }
}
