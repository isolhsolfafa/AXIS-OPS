// ignore_for_file: avoid_web_libraries_in_flutter
import 'dart:async';
import 'dart:html' as html;
import 'dart:js_util' as js_util;
import 'package:flutter/foundation.dart';

dynamic _scanner;
html.DivElement? _scannerDiv;
html.StyleElement? _scannerStyle;

/// html5-qrcode 내부 video/canvas 요소를 컨테이너에 맞추는 CSS 주입
///
/// html5-qrcode 라이브러리 내부 DOM 구조:
///   #qr-scanner-dom-div
///     └── div (내부 컨테이너 — 라이브러리가 자체 width/height 계산)
///           ├── video (카메라 피드)
///           ├── canvas (스캔 분석용)
///           └── div (qr-shaded-region — 스캔 영역 표시)
///
/// 문제: 라이브러리가 aspectRatio/qrbox 기반으로 내부 크기를 계산하여
///       부모 컨테이너 밖으로 넘침 → CSS로 강제 제한
void _injectScannerCss() {
  if (_scannerStyle != null) return; // 이미 주입됨
  _scannerStyle = html.StyleElement()
    ..text = '''
      #qr-scanner-dom-div {
        overflow: hidden !important;
        box-sizing: border-box !important;
      }
      #qr-scanner-dom-div * {
        box-sizing: border-box !important;
      }
      #qr-scanner-dom-div > div {
        position: relative !important;
        width: 100% !important;
        height: 100% !important;
        overflow: hidden !important;
        max-width: 100% !important;
      }
      #qr-scanner-dom-div > div > div {
        position: relative !important;
        width: 100% !important;
        height: 100% !important;
        overflow: hidden !important;
        max-width: 100% !important;
      }
      #qr-scanner-dom-div video {
        object-fit: cover !important;
        width: 100% !important;
        height: 100% !important;
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        max-width: none !important;
        min-width: 100% !important;
        min-height: 100% !important;
      }
      #qr-scanner-dom-div img {
        display: none !important;
      }
      #qr-scanner-dom-div canvas {
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        width: 100% !important;
        height: 100% !important;
      }
    ''';
  html.document.head!.append(_scannerStyle!);
}

/// 주입된 CSS 제거
void _removeScannerCss() {
  _scannerStyle?.remove();
  _scannerStyle = null;
}

/// html5-qrcode가 시작 후 생성한 내부 요소의 inline style을 강제 수정
///
/// 라이브러리가 start() 완료 후 내부 div에 고정 width/height를 inline으로 넣기 때문에
/// CSS !important만으로는 부족 → JS로 직접 inline style 제거/수정
void _forceContainerFit(String divId) {
  // 약간의 딜레이 후 실행 (라이브러리가 내부 DOM 구성 완료할 시간)
  Future.delayed(const Duration(milliseconds: 200), () {
    final container = html.document.getElementById(divId);
    if (container == null) return;

    // 1차 자식 div (라이브러리가 생성한 내부 컨테이너)
    final children = container.querySelectorAll('div');
    for (var i = 0; i < children.length; i++) {
      final child = children[i] as html.Element;
      child.style
        ..width = '100%'
        ..height = '100%'
        ..maxWidth = '100%'
        ..overflow = 'hidden'
        ..position = 'relative';
    }

    // video 요소 강제 스타일
    final videos = container.querySelectorAll('video');
    for (var i = 0; i < videos.length; i++) {
      final video = videos[i] as html.Element;
      video.style
        ..width = '100%'
        ..height = '100%'
        ..objectFit = 'cover'
        ..position = 'absolute'
        ..top = '0'
        ..left = '0';
    }

    debugPrint('[QrScannerWeb] Forced container fit on $divId');
  });
}

/// DOM에 스캐너 div를 직접 생성 (Flutter Shadow DOM 우회)
///
/// [containerRect]: 카메라 뷰 영역의 위치/크기 (화면 좌표)
/// 반환: 생성된 div의 ID
String ensureScannerDiv({html.Rectangle? containerRect}) {
  const divId = 'qr-scanner-dom-div';

  // CSS 주입
  _injectScannerCss();

  // 이미 존재하면 위치만 업데이트
  _scannerDiv = html.document.getElementById(divId) as html.DivElement?;
  if (_scannerDiv == null) {
    _scannerDiv = html.DivElement()
      ..id = divId;
    html.document.body!.append(_scannerDiv!);
  }

  // 스타일 설정 — 카메라 뷰 영역에 오버레이
  _scannerDiv!.style
    ..position = 'fixed'
    ..zIndex = '9999'
    ..backgroundColor = '#000000'
    ..overflow = 'hidden';

  if (containerRect != null) {
    _scannerDiv!.style
      ..left = '${containerRect.left}px'
      ..top = '${containerRect.top}px'
      ..width = '${containerRect.width}px'
      ..height = '${containerRect.height}px'
      ..borderRadius = '12px';
  } else {
    // 기본값: 완전 정사각형 (QR코드용), 화면 중앙 정렬
    final screenWidth = html.window.innerWidth ?? 400;
    final boxSize = (screenWidth * 0.78).clamp(260, 360).toInt();
    _scannerDiv!.style
      ..left = '50%'
      ..top = '100px'
      ..width = '${boxSize}px'
      ..height = '${boxSize}px'
      ..transform = 'translateX(-50%)'  // 수평 중앙
      ..borderRadius = '12px';
  }

  return divId;
}

/// DOM에서 스캐너 div + CSS 제거
void removeScannerDiv() {
  _scannerDiv?.remove();
  _scannerDiv = null;
  _removeScannerCss();
}

/// 카메라 권한을 먼저 요청 (브라우저 팝업이 보이는 상태에서)
/// 권한 획득 후 stream을 즉시 중지하고 true 반환
Future<bool> _requestCameraPermission() async {
  try {
    final mediaDevices = html.window.navigator.mediaDevices;
    if (mediaDevices == null) return false;

    // getUserMedia 호출 → 브라우저 권한 팝업 표시
    final stream = await mediaDevices.getUserMedia({'video': true});

    // 권한 획득 성공 → stream 즉시 중지 (html5-qrcode가 자체적으로 다시 열음)
    stream.getTracks().forEach((track) => track.stop());

    debugPrint('[QrScannerWeb] Camera permission granted');
    return true;
  } catch (e) {
    debugPrint('[QrScannerWeb] Camera permission denied: $e');
    return false;
  }
}

/// QR 스캐너 시작 (웹 구현 — DOM 직접 생성 방식)
///
/// 플로우:
/// 1. getUserMedia()로 카메라 권한 먼저 요청 (팝업 표시)
/// 2. 권한 획득 후 DOM div 생성
/// 3. html5-qrcode 스캐너 시작
///
/// 카메라 우선순위:
/// 1. facingMode: environment (모바일 후면 카메라)
/// 2. facingMode: user (데스크톱/전면 카메라)
/// 3. 첫 번째 사용 가능한 카메라 ID
/// 외부에서 스캐너 div 위치를 업데이트 (스크롤 시 호출)
void updateScannerDivPosition({
  required double left,
  required double top,
  required double width,
  required double height,
}) {
  if (_scannerDiv == null) return;
  _scannerDiv!.style
    ..left = '${left}px'
    ..top = '${top}px'
    ..width = '${width}px'
    ..height = '${height}px'
    ..transform = '';  // translateX 제거
}

Future<bool> startQrScanner({
  required String elementId,
  required void Function(String qrCode) onResult,
  void Function(String error)? onError,
  double? containerLeft,
  double? containerTop,
  double? containerWidth,
  double? containerHeight,
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

    // ★ 핵심: div 생성 전에 카메라 권한을 먼저 요청
    // 이 시점에는 오버레이 div가 없으므로 브라우저 팝업이 정상 표시됨
    final hasPermission = await _requestCameraPermission();
    if (!hasPermission) {
      onError?.call('카메라 권한이 거부되었습니다. 브라우저 설정에서 카메라를 허용해주세요.');
      return false;
    }

    // 권한 획득 후 DOM div 생성 (컨테이너 위치 전달)
    html.Rectangle? rect;
    if (containerLeft != null && containerTop != null &&
        containerWidth != null && containerHeight != null) {
      rect = html.Rectangle(containerLeft, containerTop, containerWidth, containerHeight);
    }
    final divId = ensureScannerDiv(containerRect: rect);

    // DOM에 div가 실제로 존재하는지 확인
    await Future.delayed(const Duration(milliseconds: 300));

    _scanner = js_util.callConstructor(html5QrcodeClass, [divId]);

    // qrbox를 컨테이너 크기에 맞게 동적 계산
    // aspectRatio 제거 — 라이브러리가 자체 크기 계산을 하지 않도록
    final qrboxSize = (containerWidth != null)
        ? (containerWidth * 0.6).clamp(150, 250).toInt()
        : 200;
    final config = js_util.jsify({
      'fps': 10,
      'qrbox': qrboxSize,  // 정수 전달 → 정사각형 스캔 영역
      'disableFlip': false,
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
      _forceContainerFit(divId);
      return true;
    } catch (e) {
      debugPrint('[QrScannerWeb] environment camera failed: $e');
    }

    // 2차 시도: 전면 카메라 (데스크톱/MacBook)
    try {
      _scanner = js_util.callConstructor(html5QrcodeClass, [divId]);
      final userConstraints = js_util.jsify({'facingMode': 'user'});
      final promise = js_util.callMethod(
        _scanner!,
        'start',
        [userConstraints, config, successCallback, errorCallback],
      );
      await js_util.promiseToFuture(promise);
      _forceContainerFit(divId);
      return true;
    } catch (e) {
      debugPrint('[QrScannerWeb] user camera failed: $e');
    }

    // 3차 시도: 사용 가능한 첫 번째 카메라 ID
    try {
      final camerasPromise = js_util.callMethod(html5QrcodeClass, 'getCameras', []);
      final cameras = await js_util.promiseToFuture(camerasPromise) as List<dynamic>;
      if (cameras.isNotEmpty) {
        final cameraId = js_util.getProperty(cameras[0] as Object, 'id') as String;
        _scanner = js_util.callConstructor(html5QrcodeClass, [divId]);
        final promise = js_util.callMethod(
          _scanner!,
          'start',
          [cameraId, config, successCallback, errorCallback],
        );
        await js_util.promiseToFuture(promise);
        _forceContainerFit(divId);
        return true;
      }
    } catch (e) {
      debugPrint('[QrScannerWeb] camera ID fallback failed: $e');
    }

    onError?.call('사용 가능한 카메라를 찾을 수 없습니다.');
    removeScannerDiv();
    _scanner = null;
    return false;
  } catch (e) {
    debugPrint('[QrScannerWeb] start failed: $e');
    removeScannerDiv();
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
    removeScannerDiv();
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
