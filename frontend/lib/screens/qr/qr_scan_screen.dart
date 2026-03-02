import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/task_provider.dart';
import '../../providers/auth_provider.dart';
import '../../services/qr_scanner_service.dart';
import '../../utils/design_system.dart';

/// QR 스캔 화면 (웹 호환 - 카메라 우선, 텍스트 입력 보조)
///
/// html5-qrcode JS 라이브러리를 통한 카메라 QR 스캔
/// 카메라 실패 시 텍스트 입력으로 자동 전환
///
/// 두 가지 QR 타입 지원:
/// 1. Worksheet QR: DOC_{SN} 형식 (예: DOC_GBWS-6408) → 제품 조회
/// 2. Location QR: LOC_{LOCATION} 형식 (예: LOC_ASSY_01) → 위치 등록
class QrScanScreen extends ConsumerStatefulWidget {
  const QrScanScreen({Key? key}) : super(key: key);

  @override
  ConsumerState<QrScanScreen> createState() => _QrScanScreenState();
}

class _QrScanScreenState extends ConsumerState<QrScanScreen> {
  final _formKey = GlobalKey<FormState>();
  final _qrCodeController = TextEditingController();
  final _qrScannerService = QrScannerService();
  final ScrollController _scrollController = ScrollController();

  bool _isProcessing = false;
  String _scanType = 'worksheet'; // 'worksheet' or 'location'
  bool _showTextInput = false; // 카메라 실패 또는 사용자가 직접 펼침
  bool _cameraInitializing = true;
  bool _cameraFailed = false;

  static const String _scannerDivId = 'qr-scanner-div';
  final GlobalKey _cameraContainerKey = GlobalKey();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _startCamera();
    });
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    _qrCodeController.dispose();
    _qrScannerService.stop();
    super.dispose();
  }

  /// Scroll listener: sync DOM scanner div position with Flutter camera container
  void _onScroll() {
    final rect = _getCameraContainerRect();
    if (rect != null) {
      _qrScannerService.updatePosition(
        left: rect['left']!,
        top: rect['top']!,
        width: rect['width']!,
        height: rect['height']!,
      );
    }
  }

  /// 카메라 컨테이너의 화면 좌표를 계산
  Map<String, double>? _getCameraContainerRect() {
    final context = _cameraContainerKey.currentContext;
    if (context == null) return null;
    final renderBox = context.findRenderObject() as RenderBox?;
    if (renderBox == null || !renderBox.hasSize) return null;
    final offset = renderBox.localToGlobal(Offset.zero);
    return {
      'left': offset.dx,
      'top': offset.dy,
      'width': renderBox.size.width,
      'height': renderBox.size.height,
    };
  }

  Future<void> _startCamera() async {
    setState(() {
      _cameraInitializing = true;
      _cameraFailed = false;
    });

    // 레이아웃 완료 대기 (모바일에서 AppBar/SafeArea 안정화 필요)
    await Future.delayed(const Duration(milliseconds: 300));
    final rect = _getCameraContainerRect();

    // 진단 로그
    if (rect != null) {
      final mq = MediaQuery.of(context);
      debugPrint('[QrScanScreen] ═══════════════════════════════════════');
      debugPrint('[QrScanScreen] Container rect: $rect');
      debugPrint('[QrScanScreen] Screen: ${mq.size.width}x${mq.size.height}');
      debugPrint('[QrScanScreen] Padding: ${mq.padding}');
      debugPrint('[QrScanScreen] ViewPadding: ${mq.viewPadding}');
      debugPrint('[QrScanScreen] DevicePixelRatio: ${mq.devicePixelRatio}');
      debugPrint('[QrScanScreen] ═══════════════════════════════════════');
    }

    final success = await _qrScannerService.start(
      elementId: _scannerDivId,
      onResult: _onQrDetected,
      onError: (error) {
        debugPrint('[QrScanScreen] Camera error: $error');
        if (mounted) {
          setState(() {
            _cameraFailed = true;
            _cameraInitializing = false;
            _showTextInput = true; // 자동 폴백
          });
        }
      },
      containerLeft: rect?['left'],
      containerTop: rect?['top'],
      containerWidth: rect?['width'],
      containerHeight: rect?['height'],
    );

    if (mounted) {
      setState(() {
        _cameraFailed = !success;
        _cameraInitializing = false;
        if (!success) {
          _showTextInput = true; // 자동 폴백
        }
      });
    }
  }

  void _onQrDetected(String qrCode) {
    if (_isProcessing) return;
    _handleQrCode(qrCode);
  }

  /// QR 코드 처리
  Future<void> _handleQrCode(String qrCode) async {
    if (_isProcessing) return;

    setState(() {
      _isProcessing = true;
    });

    final taskNotifier = ref.read(taskProvider.notifier);
    final authState = ref.read(authProvider);
    final workerId = authState.currentWorkerId;

    if (workerId == null) {
      _showErrorDialog('로그인 정보를 확인할 수 없습니다. 다시 로그인해주세요.');
      setState(() {
        _isProcessing = false;
      });
      return;
    }

    try {
      if (_scanType == 'worksheet') {
        // Worksheet QR: DOC_{SN} 형식
        if (!qrCode.toUpperCase().startsWith('DOC_')) {
          _showErrorDialog('잘못된 Worksheet QR 형식입니다.\n예: DOC_GBWS-6408');
          setState(() {
            _isProcessing = false;
          });
          return;
        }

        // 제품 조회
        final success = await taskNotifier.scanQrCode(qrCode.toUpperCase());
        if (!success) {
          final errorMessage = ref.read(taskProvider).errorMessage;
          _showErrorDialog(errorMessage ?? '제품 조회에 실패했습니다.');
        } else {
          // 성공: Task 목록 조회
          final product = ref.read(taskProvider).currentProduct;
          if (product != null) {
            final tasksSuccess = await taskNotifier.fetchTasks(
              serialNumber: product.serialNumber,
              workerId: workerId,
            );

            if (tasksSuccess) {
              // Task 목록 화면으로 이동
              if (mounted) {
                Navigator.pushReplacementNamed(
                  context,
                  '/task-management',
                  arguments: {
                    'product': product,
                    'workerId': workerId,
                  },
                );
              }
            } else {
              _showErrorDialog('Task 목록 조회에 실패했습니다.');
            }
          }
        }
      } else {
        // Location QR: LOC_{LOCATION} 형식
        if (!qrCode.toUpperCase().startsWith('LOC_')) {
          _showErrorDialog('잘못된 Location QR 형식입니다.\n예: LOC_ASSY_01');
          setState(() {
            _isProcessing = false;
          });
          return;
        }

        // Worksheet QR이 먼저 스캔되어 있어야 함
        final currentProduct = ref.read(taskProvider).currentProduct;
        if (currentProduct == null) {
          _showErrorDialog('Worksheet QR을 먼저 스캔해주세요.');
          setState(() {
            _isProcessing = false;
          });
          return;
        }

        // Location 등록
        final success = await taskNotifier.updateLocation(qrCode.toUpperCase());
        if (!success) {
          final errorMessage = ref.read(taskProvider).errorMessage;
          _showErrorDialog(errorMessage ?? 'Location 등록에 실패했습니다.');
        } else {
          // 성공 메시지
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('Location QR 등록 완료: ${qrCode.toUpperCase()}'),
                backgroundColor: GxColors.success,
                behavior: SnackBarBehavior.floating,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
              ),
            );
            _qrCodeController.clear();
          }
        }
      }
    } finally {
      setState(() {
        _isProcessing = false;
      });
    }
  }

  void _showErrorDialog(String message) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.lg)),
        title: const Row(
          children: [
            Icon(Icons.error_outline, color: GxColors.danger, size: 22),
            SizedBox(width: 8),
            Text('오류', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: GxColors.charcoal)),
          ],
        ),
        content: Text(message, style: const TextStyle(fontSize: 14, color: GxColors.slate)),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('확인', style: TextStyle(color: GxColors.accent, fontWeight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final taskState = ref.watch(taskProvider);
    final currentProduct = taskState.currentProduct;

    return Scaffold(
      backgroundColor: GxColors.cloud,
      appBar: AppBar(
        backgroundColor: GxColors.white,
        elevation: 0,
        foregroundColor: GxColors.charcoal,
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 4,
              height: 20,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [GxColors.accent, GxColors.accentHover],
                ),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(width: 12),
            const Text('QR 스캔', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: GxColors.charcoal)),
          ],
        ),
        centerTitle: false,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: GxColors.mist),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          controller: _scrollController,
          padding: const EdgeInsets.all(20.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // 현재 제품 정보 (Worksheet QR 스캔 후)
              if (currentProduct != null) ...[
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: GxGlass.cardSm(radius: GxRadius.lg),
                  child: Column(
                    children: [
                      Row(
                        children: [
                          Container(
                            width: 32,
                            height: 32,
                            decoration: BoxDecoration(
                              color: GxColors.successBg,
                              borderRadius: BorderRadius.circular(GxRadius.md),
                            ),
                            child: const Icon(Icons.check_circle, color: GxColors.success, size: 18),
                          ),
                          const SizedBox(width: 10),
                          const Expanded(
                            child: Text(
                              '제품 스캔 완료',
                              style: TextStyle(color: GxColors.success, fontWeight: FontWeight.w600, fontSize: 14),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      const Divider(height: 1, color: GxColors.mist),
                      const SizedBox(height: 12),
                      _buildInfoRow('QR 문서 ID', currentProduct.qrDocId),
                      const SizedBox(height: 6),
                      _buildInfoRow('시리얼 번호', currentProduct.serialNumber),
                      const SizedBox(height: 6),
                      _buildInfoRow('모델', currentProduct.model),
                      if (currentProduct.mechPartner != null) ...[
                        const SizedBox(height: 6),
                        _buildInfoRow('기구 협력사', currentProduct.mechPartner!),
                      ],
                      if (currentProduct.elecPartner != null) ...[
                        const SizedBox(height: 6),
                        _buildInfoRow('전장 협력사', currentProduct.elecPartner!),
                      ],
                      if (currentProduct.locationQrId != null) ...[
                        const SizedBox(height: 6),
                        _buildInfoRow('위치', currentProduct.locationQrId!),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 16),
              ],

              // QR 타입 선택
              Container(
                padding: const EdgeInsets.all(16),
                decoration: GxGlass.cardSm(radius: GxRadius.lg),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('QR 타입', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: GxColors.charcoal)),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: GestureDetector(
                            onTap: () => setState(() => _scanType = 'worksheet'),
                            child: Container(
                              padding: const EdgeInsets.symmetric(vertical: 10),
                              decoration: BoxDecoration(
                                color: _scanType == 'worksheet' ? GxColors.accentSoft : GxColors.cloud,
                                borderRadius: BorderRadius.circular(GxRadius.sm),
                                border: Border.all(
                                  color: _scanType == 'worksheet' ? GxColors.accent : GxColors.mist,
                                  width: 1.5,
                                ),
                              ),
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Icon(Icons.description, size: 16, color: _scanType == 'worksheet' ? GxColors.accent : GxColors.steel),
                                  const SizedBox(width: 6),
                                  Text(
                                    'Worksheet',
                                    style: TextStyle(
                                      fontSize: 13,
                                      fontWeight: FontWeight.w600,
                                      color: _scanType == 'worksheet' ? GxColors.accent : GxColors.steel,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: GestureDetector(
                            onTap: () => setState(() => _scanType = 'location'),
                            child: Container(
                              padding: const EdgeInsets.symmetric(vertical: 10),
                              decoration: BoxDecoration(
                                color: _scanType == 'location' ? GxColors.accentSoft : GxColors.cloud,
                                borderRadius: BorderRadius.circular(GxRadius.sm),
                                border: Border.all(
                                  color: _scanType == 'location' ? GxColors.accent : GxColors.mist,
                                  width: 1.5,
                                ),
                              ),
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Icon(Icons.location_on, size: 16, color: _scanType == 'location' ? GxColors.accent : GxColors.steel),
                                  const SizedBox(width: 6),
                                  Text(
                                    'Location',
                                    style: TextStyle(
                                      fontSize: 13,
                                      fontWeight: FontWeight.w600,
                                      color: _scanType == 'location' ? GxColors.accent : GxColors.steel,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // 카메라 뷰 (메인) — 정사각형 컨테이너 (qrbox integer와 함께 정사각형 스캔 영역 보장)
              Builder(
                builder: (context) {
                  final screenWidth = MediaQuery.of(context).size.width;
                  final cameraSize = (screenWidth - 40).clamp(200.0, 350.0); // padding 20*2
                  return Container(
                    key: _cameraContainerKey,
                    width: cameraSize,
                    height: cameraSize,
                    decoration: BoxDecoration(
                      color: Colors.black,
                      borderRadius: BorderRadius.circular(GxRadius.lg),
                      border: Border.all(color: GxColors.mist, width: 1),
                    ),
                    clipBehavior: Clip.antiAlias,
                    child: _buildCameraView(),
                  );
                },
              ),
              const SizedBox(height: 16),

              // 직접 입력 섹션 (접이식)
              Container(
                decoration: GxGlass.cardSm(radius: GxRadius.lg),
                child: Column(
                  children: [
                    // 헤더 (토글 버튼)
                    InkWell(
                      onTap: () => setState(() => _showTextInput = !_showTextInput),
                      borderRadius: BorderRadius.circular(GxRadius.lg),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        child: Row(
                          children: [
                            Icon(
                              Icons.keyboard,
                              size: 18,
                              color: _showTextInput ? GxColors.accent : GxColors.steel,
                            ),
                            const SizedBox(width: 8),
                            Text(
                              '직접 입력',
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w500,
                                color: _showTextInput ? GxColors.accent : GxColors.steel,
                              ),
                            ),
                            const Spacer(),
                            Icon(
                              _showTextInput ? Icons.expand_less : Icons.expand_more,
                              color: GxColors.silver,
                              size: 20,
                            ),
                          ],
                        ),
                      ),
                    ),

                    // 텍스트 입력 폼 (펼쳐졌을 때)
                    if (_showTextInput) ...[
                      const Divider(height: 1, color: GxColors.mist),
                      Padding(
                        padding: const EdgeInsets.all(16),
                        child: Form(
                          key: _formKey,
                          child: Column(
                            children: [
                              // 형식 안내
                              Container(
                                padding: const EdgeInsets.all(10),
                                decoration: BoxDecoration(
                                  color: GxColors.accentSoft,
                                  borderRadius: BorderRadius.circular(GxRadius.sm),
                                ),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    const Icon(Icons.info_outline, size: 16, color: GxColors.accent),
                                    const SizedBox(width: 6),
                                    Text(
                                      _scanType == 'worksheet'
                                          ? '형식: DOC_GBWS-6408'
                                          : '형식: LOC_ASSY_01',
                                      style: const TextStyle(fontSize: 12, color: GxColors.accent, fontWeight: FontWeight.w500),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(height: 12),

                              // QR 코드 입력 필드
                              TextFormField(
                                controller: _qrCodeController,
                                decoration: InputDecoration(
                                  labelText: 'QR 코드',
                                  labelStyle: const TextStyle(color: GxColors.steel, fontSize: 13),
                                  hintText: _scanType == 'worksheet' ? 'DOC_GBWS-6408' : 'LOC_ASSY_01',
                                  hintStyle: const TextStyle(color: GxColors.silver),
                                  prefixIcon: const Icon(Icons.qr_code, color: GxColors.accent),
                                  border: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(GxRadius.sm),
                                    borderSide: const BorderSide(color: GxColors.mist),
                                  ),
                                  enabledBorder: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(GxRadius.sm),
                                    borderSide: const BorderSide(color: GxColors.mist, width: 1.5),
                                  ),
                                  focusedBorder: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(GxRadius.sm),
                                    borderSide: const BorderSide(color: GxColors.accent, width: 1.5),
                                  ),
                                  errorBorder: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(GxRadius.sm),
                                    borderSide: const BorderSide(color: GxColors.danger, width: 1.5),
                                  ),
                                  filled: true,
                                  fillColor: GxColors.white,
                                ),
                                style: const TextStyle(fontSize: 14, color: GxColors.charcoal, fontWeight: FontWeight.w500),
                                textCapitalization: TextCapitalization.characters,
                                validator: (value) {
                                  if (value == null || value.isEmpty) {
                                    return 'QR 코드를 입력해주세요.';
                                  }
                                  if (_scanType == 'worksheet' && !value.toUpperCase().startsWith('DOC_')) {
                                    return 'Worksheet QR은 DOC_로 시작해야 합니다.';
                                  }
                                  if (_scanType == 'location' && !value.toUpperCase().startsWith('LOC_')) {
                                    return 'Location QR은 LOC_로 시작해야 합니다.';
                                  }
                                  return null;
                                },
                                onFieldSubmitted: (value) {
                                  if (_formKey.currentState!.validate()) {
                                    _handleQrCode(value);
                                  }
                                },
                              ),
                              const SizedBox(height: 12),

                              // 확인 버튼
                              SizedBox(
                                height: 44,
                                width: double.infinity,
                                child: Opacity(
                                  opacity: _isProcessing ? 0.6 : 1.0,
                                  child: Container(
                                    decoration: BoxDecoration(
                                      gradient: GxGradients.accentButton,
                                      borderRadius: BorderRadius.circular(GxRadius.sm),
                                      boxShadow: [
                                        BoxShadow(
                                          color: GxColors.accent.withValues(alpha: 0.35),
                                          blurRadius: 16,
                                          offset: const Offset(0, 4),
                                        ),
                                      ],
                                    ),
                                    child: Material(
                                      color: Colors.transparent,
                                      child: InkWell(
                                        onTap: _isProcessing
                                            ? null
                                            : () {
                                                if (_formKey.currentState!.validate()) {
                                                  _handleQrCode(_qrCodeController.text);
                                                }
                                              },
                                        borderRadius: BorderRadius.circular(GxRadius.sm),
                                        child: Center(
                                          child: _isProcessing
                                              ? const SizedBox(
                                                  height: 20,
                                                  width: 20,
                                                  child: CircularProgressIndicator(strokeWidth: 2, valueColor: AlwaysStoppedAnimation<Color>(Colors.white)),
                                                )
                                              : const Text('확인', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Colors.white)),
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCameraView() {
    if (_cameraInitializing) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(color: GxColors.white),
            SizedBox(height: 12),
            Text('카메라 초기화 중...', style: TextStyle(color: GxColors.silver, fontSize: 13)),
          ],
        ),
      );
    }

    if (_cameraFailed) {
      return Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.camera_alt_outlined, color: GxColors.silver, size: 40),
          const SizedBox(height: 12),
          const Text(
            '카메라를 사용할 수 없습니다',
            style: TextStyle(color: GxColors.silver, fontSize: 14),
          ),
          const SizedBox(height: 4),
          const Text(
            '아래 직접 입력을 사용하세요',
            style: TextStyle(color: GxColors.slate, fontSize: 12),
          ),
        ],
      );
    }

    // 카메라 활성 시 DOM div가 이 영역 위에 오버레이됨
    // html5-qrcode가 자체 스캔 영역 UI를 렌더링하므로 Flutter 오버레이 불필요
    return Stack(
      children: [
        Container(color: Colors.black),
        // 처리 중 오버레이
        if (_isProcessing)
          Container(
            color: Colors.black54,
            child: const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(color: GxColors.white),
                  SizedBox(height: 12),
                  Text('처리 중...', style: TextStyle(color: GxColors.white, fontSize: 13)),
                ],
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Row(
      children: [
        Text('$label: ', style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 13, color: GxColors.slate)),
        Expanded(child: Text(value, style: const TextStyle(fontSize: 13, color: GxColors.charcoal))),
      ],
    );
  }
}
