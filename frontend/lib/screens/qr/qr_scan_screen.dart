import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/task_provider.dart';
import '../../providers/auth_provider.dart';

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
                backgroundColor: Colors.green,
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
        title: const Text('오류'),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('확인'),
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
      appBar: AppBar(
        title: const Text('QR 스캔'),
        centerTitle: true,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // 현재 제품 정보 (Worksheet QR 스캔 후)
                if (currentProduct != null)
                  Card(
                    elevation: 2,
                    color: Colors.blue.shade50,
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        children: [
                          Row(
                            children: [
                              Icon(Icons.check_circle, color: Colors.blue.shade700),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  '제품 스캔 완료',
                                  style: TextStyle(
                                    color: Colors.blue.shade700,
                                    fontWeight: FontWeight.bold,
                                    fontSize: 16,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          _buildInfoRow('QR 문서 ID', currentProduct.qrDocId),
                          _buildInfoRow('시리얼 번호', currentProduct.serialNumber),
                          _buildInfoRow('모델', currentProduct.model),
                          if (currentProduct.locationQrId != null)
                            _buildInfoRow('위치', currentProduct.locationQrId!),
                        ],
                      ),
                    ),
                  ),
                const SizedBox(height: 24),

                // QR 타입 선택
                const Text(
                  'QR 타입',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 12),
                SegmentedButton<String>(
                  segments: const [
                    ButtonSegment(
                      value: 'worksheet',
                      label: Text('Worksheet QR'),
                      icon: Icon(Icons.description),
                    ),
                    ButtonSegment(
                      value: 'location',
                      label: Text('Location QR'),
                      icon: Icon(Icons.location_on),
                    ),
                  ],
                  selected: {_scanType},
                  onSelectionChanged: (Set<String> selection) {
                    setState(() {
                      _scanType = selection.first;
                    });
                  },
                ),
                const SizedBox(height: 24),

                // QR 코드 입력 안내
                Text(
                  _scanType == 'worksheet'
                      ? 'Worksheet QR 형식: DOC_GBWS-6408'
                      : 'Location QR 형식: LOC_ASSY_01',
                  style: TextStyle(
                    fontSize: 14,
                    color: Colors.grey[600],
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),

                // QR 코드 입력 필드
                TextFormField(
                  controller: _qrCodeController,
                  decoration: InputDecoration(
                    labelText: 'QR 코드',
                    hintText: _scanType == 'worksheet'
                        ? 'DOC_GBWS-6408'
                        : 'LOC_ASSY_01',
                    prefixIcon: const Icon(Icons.qr_code),
                    border: const OutlineInputBorder(),
                    filled: true,
                    fillColor: Colors.grey.shade50,
                  ),
                  textCapitalization: TextCapitalization.characters,
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'QR 코드를 입력해주세요.';
                    }
                    if (_scanType == 'worksheet' &&
                        !value.toUpperCase().startsWith('DOC_')) {
                      return 'Worksheet QR은 DOC_로 시작해야 합니다.';
                    }
                    if (_scanType == 'location' &&
                        !value.toUpperCase().startsWith('LOC_')) {
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
                const SizedBox(height: 24),

                // 스캔 버튼
                ElevatedButton(
                  onPressed: _isProcessing
                      ? null
                      : () {
                          if (_formKey.currentState!.validate()) {
                            _handleQrCode(_qrCodeController.text);
                          }
                        },
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    textStyle: const TextStyle(fontSize: 18),
                  ),
                  child: _isProcessing
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('스캔'),
                ),
                const SizedBox(height: 32),

                // 웹 카메라 지원 안내
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.amber.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.amber.shade200),
                  ),
                  child: Column(
                    children: [
                      Row(
                        children: [
                          Icon(Icons.info_outline, color: Colors.amber.shade700),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Sprint 2 MVP',
                              style: TextStyle(
                                color: Colors.amber.shade700,
                                fontWeight: FontWeight.bold,
                                fontSize: 16,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        '현재 텍스트 입력 방식으로 제공됩니다.\n'
                        '웹 카메라 QR 스캔 기능은\n'
                        '향후 업데이트에서 추가됩니다.',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: Colors.amber.shade700,
                          fontSize: 14,
                        ),
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
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        children: [
          Text(
            '$label: ',
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 14,
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontSize: 14),
            ),
          ),
        ],
      ),
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
