// ignore_for_file: avoid_web_libraries_in_flutter
import 'dart:async';
import 'dart:html' as html;
import 'dart:js_util' as js_util;
import 'package:flutter/foundation.dart';

dynamic _scanner;
html.DivElement? _scannerDiv;
html.StyleElement? _scannerStyle;
StreamSubscription? _resizeSubscription;
html.MutationObserver? _squareObserver;

/// 저장된 컨테이너 위치/크기 (반응형 리사이즈 시 재사용)
double _savedLeft = 20.0;
double _savedTopPx = 100.0;
double _savedWidth = 360.0;
double _savedHeight = 300.0;

/// CSS 주입 — 컨테이너 정사각형 강제 + 내부 video crop
/// ★ 11차 수정: html5-qrcode가 컨테이너 높이를 카메라 비율(세로)로 덮어쓰는 문제 대응
/// 모바일 카메라는 세로(portrait) 비율이라 컨테이너가 직사각형으로 늘어남
/// → width/height/max-height를 !important로 고정 + video를 object-fit:cover로 crop
void _injectScannerCss() {
  if (_scannerStyle != null) return;
  _scannerStyle = html.StyleElement()
    ..text = '''
      #qr-scanner-dom-div {
        overflow: hidden !important;
        aspect-ratio: 1 / 1 !important;
      }
      #qr-scanner-dom-div video {
        object-fit: cover !important;
        width: 100% !important;
        height: 100% !important;
      }
      #qr-scanner-dom-div img {
        object-fit: cover !important;
      }
      /* BUG-23: viewfinder 코너 마커가 잘리지 않도록 보호 */
      [id*="shaded"], [id*="region"] {
        overflow: visible !important;
      }
    ''';
  html.document.head!.append(_scannerStyle!);
}

/// 주입된 CSS 제거
void _removeScannerCss() {
  _scannerStyle?.remove();
  _scannerStyle = null;
}

/// DOM에 스캐너 div를 직접 생성 (Flutter Shadow DOM 우회)
///
/// ★ 정렬 전략:
/// - Flutter renderBox에서 얻은 실제 left, top, width, height를 그대로 사용
/// - CSS `left` + `width` 명시 방식 (right 방식 제거)
///   → 대칭 여백 가정 오류 수정 (right=left는 ScrollView가 완전 중앙일 때만 성립)
/// - position: fixed 기준이므로 Flutter logical pixel = CSS pixel (DPR 보정 불필요)
///
/// [containerLeft]: Flutter 컨테이너의 왼쪽 위치 (논리 px = CSS px)
/// [containerTop]: Flutter 컨테이너의 상단 위치 (논리 px = CSS px)
/// [containerWidth]: Flutter 컨테이너 너비 (논리 px = CSS px)
/// [containerHeight]: Flutter 컨테이너 높이 (논리 px = CSS px)
/// 반환: 생성된 div의 ID
String ensureScannerDiv({
  double? containerLeft,
  double? containerTop,
  double? containerWidth,
  double? containerHeight,
}) {
  const divId = 'qr-scanner-dom-div';

  _injectScannerCss();

  // 이미 존재하면 재사용
  _scannerDiv = html.document.getElementById(divId) as html.DivElement?;
  if (_scannerDiv == null) {
    _scannerDiv = html.DivElement()
      ..id = divId;
    html.document.body!.append(_scannerDiv!);
  }

  // 스타일 설정 — Flutter 카메라 컨테이너 위에 position:fixed 오버레이
  _scannerDiv!.style
    ..position = 'fixed'
    ..zIndex = '9999'
    ..backgroundColor = '#000000'
    ..overflow = 'hidden'
    ..borderRadius = '12px';

  if (containerLeft != null && containerTop != null &&
      containerWidth != null && containerHeight != null) {
    // ★ 핵심: left + width 방식 (정확한 위치 지정)
    // Flutter renderBox.localToGlobal() 논리 픽셀 = CSS position:fixed 픽셀
    // right 제거 → 대칭 여백 가정 오류 수정
    _savedLeft = containerLeft;
    _savedTopPx = containerTop;
    _savedWidth = containerWidth;
    _savedHeight = containerHeight;

    _scannerDiv!.style
      ..left = '${containerLeft}px'
      ..top = '${containerTop}px'
      ..width = '${containerWidth}px'
      ..height = '${containerHeight}px'
      ..right = '' // right 제거 — width로 명시
      ..transform = '';

    debugPrint('[QrScannerWeb] ensureScannerDiv (explicit): '
        'left=${containerLeft}px, top=${containerTop}px, '
        'width=${containerWidth}px, height=${containerHeight}px');
  } else {
    // fallback: 화면 중앙, padding 5% 양쪽
    final screenWidth = html.window.innerWidth ?? 400;
    final margin = (screenWidth * 0.05).clamp(16, 40).toInt();
    final fallbackWidth = screenWidth - margin * 2;

    _savedLeft = margin.toDouble();
    _savedTopPx = 100;
    _savedWidth = fallbackWidth.toDouble();
    _savedHeight = 300;

    _scannerDiv!.style
      ..left = '${margin}px'
      ..top = '100px'
      ..width = '${fallbackWidth}px'
      ..height = '300px'
      ..right = '' // right 제거
      ..transform = '';

    debugPrint('[QrScannerWeb] ensureScannerDiv (fallback): '
        'margin=${margin}px, viewport=${screenWidth}px, width=${fallbackWidth}px');
  }

  // 반응형: 창 크기 변경 시 자동 재조정 (회전, 리사이즈 대응)
  _startResizeListener();

  return divId;
}

/// 창 크기 변경 리스너 (화면 회전, 브라우저 리사이즈 대응)
void _startResizeListener() {
  _resizeSubscription?.cancel();
  _resizeSubscription = html.window.onResize.listen((_) {
    if (_scannerDiv == null) return;
    // 저장된 left/top/width/height 재적용 (명시적 위치 유지)
    _scannerDiv!.style
      ..left = '${_savedLeft}px'
      ..top = '${_savedTopPx}px'
      ..width = '${_savedWidth}px'
      ..height = '${_savedHeight}px'
      ..right = '';

    final viewportWidth = html.window.innerWidth ?? 400;
    debugPrint('[QrScannerWeb] onResize: viewport=${viewportWidth}px, '
        'left=${_savedLeft}px, width=${_savedWidth}px');
  });
}

/// 리사이즈 리스너 해제
void _stopResizeListener() {
  _resizeSubscription?.cancel();
  _resizeSubscription = null;
}

/// DOM에서 스캐너 div + CSS + 리스너 + MutationObserver 제거
void removeScannerDiv() {
  _squareObserver?.disconnect();
  _squareObserver = null;
  _stopResizeListener();
  _scannerDiv?.remove();
  _scannerDiv = null;
  _removeScannerCss();
}

/// 스캐너 div를 일시적으로 숨김 (다이얼로그 표시 시 z-index 충돌 방지)
/// ★ MutationObserver를 일시 해제하여 hide→show 깜빡임 루프 방지
void hideScannerDiv() {
  if (_scannerDiv == null) return;
  _squareObserver?.disconnect();
  _scannerDiv!.style.display = 'none';
  debugPrint('[QrScannerWeb] Scanner div hidden + observer paused (dialog overlay)');
}

/// ★ 11차 수정: html5-qrcode가 카메라 시작 후 컨테이너/내부 요소 크기를
/// 카메라 비율로 덮어쓰는 것을 강제 복원
/// 카메라 start() 성공 후 호출
void _forceSquareAfterCameraStart() {
  if (_scannerDiv == null) return;

  // 1. 컨테이너 div 자체를 정사각형으로 강제
  _scannerDiv!.style
    ..width = '${_savedWidth}px'
    ..height = '${_savedWidth}px'  // ★ height = width (정사각형)
    ..maxHeight = '${_savedWidth}px';

  // 2. html5-qrcode가 생성한 내부 요소들도 강제 조정
  // 내부 video 태그
  final videos = _scannerDiv!.querySelectorAll('video');
  for (final v in videos) {
    (v as html.Element).style
      ..objectFit = 'cover'
      ..width = '100%'
      ..height = '100%';
  }

  // html5-qrcode 내부 컨테이너 (video 포함 div만 타겟, viewfinder 제외)
  final children = _scannerDiv!.children;
  for (final child in children) {
    if (child is html.DivElement) {
      // viewfinder(#qr-shaded-region) 및 코너 마커 영역은 건드리지 않음 (BUG-23)
      final childId = child.id;
      if (childId.contains('shaded') || childId.contains('region')) continue;
      // video 태그를 포함한 div만 overflow:hidden 적용
      final hasVideo = child.querySelector('video') != null;
      if (!hasVideo) continue;

      child.style
        ..width = '100%'
        ..height = '${_savedWidth}px'
        ..maxHeight = '${_savedWidth}px'
        ..overflow = 'hidden';
    }
  }

  // 3. MutationObserver: html5-qrcode가 비동기로 크기를 다시 변경하면 즉시 재적용
  _squareObserver?.disconnect();
  _squareObserver = html.MutationObserver((mutations, observer) {
    if (_scannerDiv == null) return;
    final currentHeight = _scannerDiv!.style.height;
    final expectedHeight = '${_savedWidth}px';
    if (currentHeight != expectedHeight) {
      _scannerDiv!.style
        ..height = expectedHeight
        ..maxHeight = expectedHeight;
      // 내부 video도 재적용
      final vids = _scannerDiv!.querySelectorAll('video');
      for (final v in vids) {
        (v as html.Element).style
          ..objectFit = 'cover'
          ..width = '100%'
          ..height = '100%';
      }
      debugPrint('[QrScannerWeb] ★ MutationObserver re-applied square: $currentHeight → $expectedHeight');
    }
  });
  _squareObserver!.observe(_scannerDiv!, childList: true, subtree: true, attributes: true, attributeFilter: ['style']);

  debugPrint('[QrScannerWeb] ★ forceSquare applied + MutationObserver active: ${_savedWidth}x${_savedWidth}px');
}

/// 숨겨진 스캐너 div를 다시 표시
/// ★ MutationObserver 재활성화 + 정사각형 강제 재적용
void showScannerDiv() {
  if (_scannerDiv == null) return;
  _scannerDiv!.style.display = 'block';
  // 다시 표시 후 정사각형 강제 + Observer 재활성화
  _forceSquareAfterCameraStart();
  debugPrint('[QrScannerWeb] Scanner div shown + observer resumed (dialog closed)');
}

/// 카메라 권한을 먼저 요청 (브라우저 팝업이 보이는 상태에서)
/// 권한 획득 후 stream을 즉시 중지하고 true 반환
Future<bool> _requestCameraPermission() async {
  try {
    final mediaDevices = html.window.navigator.mediaDevices;
    if (mediaDevices == null) return false;

    final stream = await mediaDevices.getUserMedia({'video': true});
    stream.getTracks().forEach((track) => track.stop());

    debugPrint('[QrScannerWeb] Camera permission granted');
    return true;
  } catch (e) {
    debugPrint('[QrScannerWeb] Camera permission denied: $e');
    return false;
  }
}

/// 외부에서 스캐너 div 위치를 업데이트 (스크롤 시 호출)
void updateScannerDivPosition({
  required double left,
  required double top,
  required double width,
  required double height,
}) {
  if (_scannerDiv == null) return;

  _savedLeft = left;
  _savedTopPx = top;
  _savedWidth = width;
  _savedHeight = height;

  // 명시적 left + width 방식 (대칭 가정 오류 수정)
  _scannerDiv!.style
    ..left = '${left}px'
    ..top = '${top}px'
    ..width = '${width}px'
    ..height = '${height}px'
    ..right = '' // right 제거
    ..transform = '';
}

/// QR 스캐너 시작 (웹 구현 — DOM 직접 생성 방식)
///
/// 전략:
/// - left + right CSS로 반응형 가로 크기 결정 (width 직접 설정 안함)
/// - html5-qrcode에 컨테이너 크기를 자동 계산하도록 유도
/// - 내부 요소 CSS 오버라이드 하지 않음 (QR 인식 보존)
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

    // ★ 진단 로그: Flutter에서 전달받은 좌표 vs viewport
    final viewportWidth = html.window.innerWidth ?? 400;
    final viewportHeight = html.window.innerHeight ?? 800;
    final dpr = html.window.devicePixelRatio;
    debugPrint('[QrScannerWeb] ═══════════════════════════════════════');
    debugPrint('[QrScannerWeb] Flutter coords: left=$containerLeft, top=$containerTop, '
        'width=$containerWidth, height=$containerHeight');
    debugPrint('[QrScannerWeb] Viewport: ${viewportWidth}x$viewportHeight, DPR: $dpr');
    final bodyRect = html.document.body?.getBoundingClientRect();
    debugPrint('[QrScannerWeb] Body rect: left=${bodyRect?.left}, top=${bodyRect?.top}, width=${bodyRect?.width}');
    debugPrint('[QrScannerWeb] ═══════════════════════════════════════');

    // ★ 핵심: div 생성 전에 카메라 권한을 먼저 요청
    final hasPermission = await _requestCameraPermission();
    if (!hasPermission) {
      onError?.call('카메라 권한이 거부되었습니다. 브라우저 설정에서 카메라를 허용해주세요.');
      return false;
    }

    // 권한 획득 후 DOM div 생성 (Flutter 실제 좌표 그대로 전달)
    final divId = ensureScannerDiv(
      containerLeft: containerLeft,
      containerTop: containerTop,
      containerWidth: containerWidth,
      containerHeight: containerHeight,
    );

    // DOM에 div가 실제로 존재하는지 확인 + 레이아웃 안정화
    await Future.delayed(const Duration(milliseconds: 500));

    // ★ 실제 div 크기를 DOM에서 읽어서 qrbox 계산
    final divRect = _scannerDiv?.getBoundingClientRect();
    final actualDivHeight = divRect?.height ?? (containerHeight ?? 300);
    debugPrint('[QrScannerWeb] Actual div rect: '
        'left=${divRect?.left}, top=${divRect?.top}, '
        'width=${divRect?.width}, height=${divRect?.height}');
    debugPrint('[QrScannerWeb] Div actual style: left=${_scannerDiv?.style.left}, '
        'top=${_scannerDiv?.style.top}, right=${_scannerDiv?.style.right}, '
        'width=${_scannerDiv?.style.width}');

    _scanner = js_util.callConstructor(html5QrcodeClass, [divId]);

    // ★ 10차 수정: qrbox를 integer로 변경 — 컨테이너가 정사각형이므로 숫자값이 자동으로 정사각형 스캔 영역 생성
    // 9차 실패 이력: qrbox callback이 정사각형 크기를 반환해도 컨테이너가 landscape이면 뷰파인더가 가로로 늘어남
    // 해결책: 컨테이너를 정사각형으로 만들고 qrbox도 integer로 지정
    final configScript = html.ScriptElement()
      ..text = '''
        window.__qrScanConfig = {
          fps: 10,
          qrbox: 200
        };
        console.log("[QrScannerWeb] config.qrbox type=" + typeof window.__qrScanConfig.qrbox + " value=" + window.__qrScanConfig.qrbox);
      ''';
    html.document.head!.append(configScript);
    configScript.remove(); // 스크립트 실행 완료 후 DOM에서 제거

    // window.__qrScanConfig를 가져옴 — 순수 JS 네이티브 객체
    final config = js_util.getProperty(js_util.globalThis, '__qrScanConfig');
    debugPrint('[QrScannerWeb] config from window.__qrScanConfig, fps=${js_util.getProperty(config, 'fps')}');

    final successCallback = js_util.allowInterop((String decodedText, dynamic result) {
      debugPrint('[QrScannerWeb] ★ QR DETECTED: $decodedText');
      onResult(decodedText);
    });

    final errorCallback = js_util.allowInterop((String errorMessage, dynamic error) {
      // QR 미인식은 정상 상태 — 무시
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
      debugPrint('[QrScannerWeb] Started with environment camera');
      // ★ 11차: 카메라 시작 후 약간의 딜레이 뒤 강제 정사각형 적용
      await Future.delayed(const Duration(milliseconds: 300));
      _forceSquareAfterCameraStart();
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
      debugPrint('[QrScannerWeb] Started with user camera');
      await Future.delayed(const Duration(milliseconds: 300));
      _forceSquareAfterCameraStart();
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
        debugPrint('[QrScannerWeb] Started with camera ID: $cameraId');
        await Future.delayed(const Duration(milliseconds: 300));
        _forceSquareAfterCameraStart();
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
