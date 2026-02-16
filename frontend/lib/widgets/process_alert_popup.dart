import 'package:flutter/material.dart';

/// 공정 누락 경고 팝업 위젯
///
/// PI/QI/SI 작업자가 Worksheet QR 태깅 후, Task 목록 진입 전 표시
/// APP_PLAN_v4 § 2.3 공정 누락 검증 팝업
///
/// 경고 타입:
/// - location_qr_missing: Location QR 미등록 (차단)
/// - mm_missing: 기구 작업 누락 (경고)
/// - ee_missing: 전장 작업 누락 (경고)
/// - tm_missing: TMS 반제품 작업 누락 (경고)
class ProcessAlertPopup extends StatelessWidget {
  final String title;
  final String message;
  final String alertType; // location_qr_missing, mm_missing, ee_missing, tm_missing
  final List<String>? missingProcesses; // 누락된 공정 목록
  final VoidCallback? onDismiss; // 취소/나중에 버튼
  final VoidCallback? onConfirm; // 확인 버튼

  const ProcessAlertPopup({
    Key? key,
    required this.title,
    required this.message,
    required this.alertType,
    this.missingProcesses,
    this.onDismiss,
    this.onConfirm,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    // 경고 유형에 따른 색상 및 아이콘 설정
    final bool isBlocking = alertType == 'location_qr_missing';
    final Color alertColor = isBlocking ? Colors.red : Colors.orange;
    final IconData alertIcon = isBlocking ? Icons.block : Icons.warning;

    return AlertDialog(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      title: Row(
        children: [
          Icon(
            alertIcon,
            color: alertColor,
            size: 28,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              title,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: alertColor,
              ),
            ),
          ),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            message,
            style: const TextStyle(
              fontSize: 16,
              height: 1.5,
            ),
          ),
          // 누락된 공정 목록 표시
          if (missingProcesses != null && missingProcesses!.isNotEmpty) ...[
            const SizedBox(height: 16),
            const Text(
              '누락된 공정:',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 8),
            ...missingProcesses!.map((process) => Padding(
                  padding: const EdgeInsets.only(left: 8, bottom: 4),
                  child: Row(
                    children: [
                      Icon(
                        Icons.check_box_outline_blank,
                        size: 16,
                        color: alertColor,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        _getProcessDisplayName(process),
                        style: const TextStyle(fontSize: 14),
                      ),
                    ],
                  ),
                )),
          ],
          // Location QR 미등록인 경우 추가 안내
          if (isBlocking) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.red.shade50,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.red.shade200),
              ),
              child: const Row(
                children: [
                  Icon(Icons.info_outline, color: Colors.red, size: 20),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Location QR을 등록해야 작업을 시작할 수 있습니다.',
                      style: TextStyle(fontSize: 12, color: Colors.red),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
      actions: [
        // 취소/나중에 버튼 (Location QR 미등록인 경우에만)
        if (isBlocking && onDismiss != null)
          TextButton(
            onPressed: onDismiss,
            child: const Text(
              '나중에',
              style: TextStyle(color: Colors.grey),
            ),
          ),
        // 확인 버튼
        ElevatedButton(
          onPressed: onConfirm ?? () => Navigator.pop(context),
          style: ElevatedButton.styleFrom(
            backgroundColor: alertColor,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          ),
          child: Text(
            isBlocking ? 'Location QR 촬영하기' : '확인',
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
        ),
      ],
    );
  }

  /// 공정 코드를 한글 이름으로 변환
  String _getProcessDisplayName(String processCode) {
    switch (processCode) {
      case 'MM':
        return '기구 작업';
      case 'EE':
        return '전장 작업';
      case 'TM':
        return 'TMS 반제품 작업';
      case 'PI':
        return '가압 검사';
      case 'QI':
        return '공정 검사';
      case 'SI':
        return '출하 검사';
      default:
        return processCode;
    }
  }
}

/// 공정 누락 검증 결과에 따라 팝업 표시
///
/// [context]: BuildContext
/// [validationResult]: validation/check-process API 응답
///   - valid: bool
///   - missing_processes: List<String> (예: ['MM', 'EE'])
///   - location_qr_verified: bool
///   - message: String
/// [onLocationQrScan]: Location QR 촬영 콜백
///
/// Returns: 사용자가 확인 버튼을 누른 경우 true, 취소/나중에 버튼을 누른 경우 false
Future<bool> showProcessAlertDialog({
  required BuildContext context,
  required Map<String, dynamic> validationResult,
  VoidCallback? onLocationQrScan,
}) async {
  final bool isValid = validationResult['valid'] as bool? ?? true;
  final bool locationQrVerified =
      validationResult['location_qr_verified'] as bool? ?? false;
  final List<String> missingProcesses =
      (validationResult['missing_processes'] as List?)
              ?.map((e) => e.toString())
              .toList() ??
          [];
  final String message =
      validationResult['message'] as String? ?? '공정 검증 중 오류가 발생했습니다.';

  // 검증 통과 시 팝업 표시 안 함
  if (isValid && locationQrVerified) {
    return true;
  }

  // Location QR 미등록
  if (!locationQrVerified) {
    final result = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (context) => ProcessAlertPopup(
        title: '📍 검사 위치 등록 필요',
        message: 'Location QR을 먼저 촬영하세요.\n작업을 시작하려면 검사 위치를 등록해야 합니다.',
        alertType: 'location_qr_missing',
        onDismiss: () => Navigator.pop(context, false),
        onConfirm: () {
          Navigator.pop(context, true);
          onLocationQrScan?.call();
        },
      ),
    );
    return result ?? false;
  }

  // 공정 누락 경고 (진행 허용)
  if (!isValid && missingProcesses.isNotEmpty) {
    String alertType = 'warning';
    String title = '⚠️ 선행 공정 누락';

    if (missingProcesses.contains('MM')) {
      alertType = 'mm_missing';
      title = '⚠️ 기구 작업 누락 발생';
    } else if (missingProcesses.contains('EE')) {
      alertType = 'ee_missing';
      title = '⚠️ 전장 작업 누락 발생';
    } else if (missingProcesses.contains('TM')) {
      alertType = 'tm_missing';
      title = '⚠️ TMS 반제품 작업 누락 발생';
    }

    await showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => ProcessAlertPopup(
        title: title,
        message: '$message\n관리자에게 알림이 발송되었습니다.',
        alertType: alertType,
        missingProcesses: missingProcesses,
        onConfirm: () => Navigator.pop(context),
      ),
    );

    // 경고만 표시하고 진행 허용
    return true;
  }

  // 기타 검증 실패
  await showDialog(
    context: context,
    builder: (context) => ProcessAlertPopup(
      title: '⚠️ 검증 실패',
      message: message,
      alertType: 'warning',
      onConfirm: () => Navigator.pop(context),
    ),
  );

  return true;
}
