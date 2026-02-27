import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/auth_provider.dart';
import '../utils/design_system.dart';

/// 휴게시간 시작 팝업 (BREAK_TIME_PAUSE WebSocket 이벤트)
///
/// - barrierDismissible: false (강제 확인)
/// - 저녁시간: "무시하고 계속 작업" 버튼 추가 → POST /app/work/resume
class BreakTimePopup extends ConsumerWidget {
  final String breakType; // 'morning', 'lunch', 'afternoon', 'dinner'
  final String breakTypeName; // '오전 휴게', '점심시간', '오후 휴게', '저녁시간'
  final String endTime; // 종료 시각 (HH:MM)

  const BreakTimePopup({
    super.key,
    required this.breakType,
    required this.breakTypeName,
    required this.endTime,
  });

  /// 팝업 표시 정적 메서드
  static Future<void> show(
    BuildContext context, {
    required String breakType,
    required String breakTypeName,
    required String endTime,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => BreakTimePopup(
        breakType: breakType,
        breakTypeName: breakTypeName,
        endTime: endTime,
      ),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isDinner = breakType == 'dinner';

    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.xl)),
      backgroundColor: Colors.transparent,
      child: Container(
        decoration: GxGlass.card(radius: GxRadius.xl),
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // 아이콘
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: GxColors.warningBg,
                borderRadius: BorderRadius.circular(GxRadius.lg),
              ),
              child: const Icon(Icons.coffee, size: 30, color: GxColors.warning),
            ),
            const SizedBox(height: 16),

            // 제목
            const Text(
              '휴게시간 안내',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: GxColors.charcoal),
            ),
            const SizedBox(height: 12),

            // 내용
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: GxColors.warningBg,
                borderRadius: BorderRadius.circular(GxRadius.md),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Text(
                    breakTypeName,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: GxColors.warning,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.access_time, size: 16, color: GxColors.slate),
                      const SizedBox(width: 6),
                      Text(
                        '종료: $endTime',
                        style: const TextStyle(fontSize: 14, color: GxColors.slate),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              '진행 중인 작업이 자동으로 일시정지되었습니다.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 12, color: GxColors.steel),
            ),
            const SizedBox(height: 20),

            // 버튼 영역
            if (isDinner) ...[
              // 저녁 전용: 무시하고 계속 작업 버튼
              SizedBox(
                width: double.infinity,
                height: 44,
                child: OutlinedButton(
                  onPressed: () async {
                    Navigator.of(context).pop();
                    await _handleResumeAll(context, ref);
                  },
                  style: OutlinedButton.styleFrom(
                    foregroundColor: GxColors.slate,
                    side: const BorderSide(color: GxColors.mist, width: 1.5),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(GxRadius.sm),
                    ),
                  ),
                  child: const Text(
                    '무시하고 계속 작업',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
                  ),
                ),
              ),
              const SizedBox(height: 8),
            ],

            // 확인 버튼
            SizedBox(
              width: double.infinity,
              height: 44,
              child: Container(
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFFF59E0B), Color(0xFFFBBF24)],
                  ),
                  borderRadius: BorderRadius.circular(GxRadius.sm),
                  boxShadow: [
                    BoxShadow(
                      color: GxColors.warning.withValues(alpha: 0.3),
                      blurRadius: 8,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: () => Navigator.of(context).pop(),
                    borderRadius: BorderRadius.circular(GxRadius.sm),
                    child: const Center(
                      child: Text(
                        '확인',
                        style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Colors.white),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 저녁 무시: 모든 일시정지 작업 재개 (POST /app/work/resume with all paused tasks)
  Future<void> _handleResumeAll(BuildContext context, WidgetRef ref) async {
    try {
      final apiService = ref.read(apiServiceProvider);
      await apiService.post('/app/work/resume', data: {'resume_all': true});
    } catch (e) {
      // 오류 시 무시 (사용자가 이미 확인했으므로)
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('재개 요청에 실패했습니다. 개별 작업에서 재개해주세요.'),
            backgroundColor: GxColors.danger,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
          ),
        );
      }
    }
  }
}
