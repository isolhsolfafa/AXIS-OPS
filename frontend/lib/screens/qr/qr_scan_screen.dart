import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/task_provider.dart';
import '../../providers/auth_provider.dart';
import '../../utils/design_system.dart';

/// QR 스캔 화면 (웹 호환 - 텍스트 입력 방식)
///
/// Sprint 2 MVP: 텍스트 입력으로 QR 코드 ID 직접 입력
/// 향후: dart:html의 MediaDevices API로 웹 카메라 지원 추가 예정
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
  bool _isProcessing = false;
  String _scanType = 'worksheet'; // 'worksheet' or 'location'

  @override
  void dispose() {
    _qrCodeController.dispose();
    super.dispose();
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
          padding: const EdgeInsets.all(20.0),
          child: Form(
            key: _formKey,
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
                      const SizedBox(height: 16),

                      // QR 코드 입력 안내
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
                      const SizedBox(height: 16),

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
                    ],
                  ),
                ),
                const SizedBox(height: 16),

                // 스캔 버튼
                SizedBox(
                  height: 44,
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
                                : const Text('스캔', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Colors.white)),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 24),

                // 웹 카메라 지원 안내
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: GxColors.warningBg,
                    borderRadius: BorderRadius.circular(GxRadius.md),
                  ),
                  child: Column(
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.info_outline, color: GxColors.warning, size: 18),
                          SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Sprint 2 MVP',
                              style: TextStyle(color: GxColors.warning, fontWeight: FontWeight.w600, fontSize: 13),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        '현재 텍스트 입력 방식으로 제공됩니다.\n'
                        '웹 카메라 QR 스캔 기능은\n'
                        '향후 업데이트에서 추가됩니다.',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: GxColors.slate, fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
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

// TODO: 향후 웹 카메라 지원 구현 예정
// import 'dart:html' as html;
//
// Future<void> _scanWithCamera() async {
//   final mediaDevices = html.window.navigator.mediaDevices;
//   final stream = await mediaDevices?.getUserMedia({'video': true});
//   // QR 스캔 로직 구현
// }
