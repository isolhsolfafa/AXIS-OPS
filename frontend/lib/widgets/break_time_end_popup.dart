import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/auth_provider.dart';
import '../utils/design_system.dart';

/// 휴게시간 종료 팝업 (BREAK_TIME_END WebSocket 이벤트)
///
/// - 제목: 휴게시간 종료
/// - "재개하기" 버튼 → POST /app/work/resume (all paused tasks)
class BreakTimeEndPopup extends ConsumerWidget {
  final String breakTypeName; // '오전 휴게', '점심시간', '오후 휴게', '저녁시간'

  const BreakTimeEndPopup({
    super.key,
    required this.breakTypeName,
  });

  /// 팝업 표시 정적 메서드
  static Future<void> show(
    BuildContext context, {
    required String breakTypeName,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => BreakTimeEndPopup(breakTypeName: breakTypeName),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
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
                color: GxColors.successBg,
                borderRadius: BorderRadius.circular(GxRadius.lg),
              ),
              child: const Icon(Icons.alarm_on, size: 30, color: GxColors.success),
            ),
            const SizedBox(height: 16),

            // 제목
            const Text(
              '휴게시간 종료',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: GxColors.charcoal),
            ),
            const SizedBox(height: 12),

            // 내용
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: GxColors.successBg,
                borderRadius: BorderRadius.circular(GxRadius.md),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Text(
                    '$breakTypeName 종료',
                    style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      color: GxColors.success,
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    '작업을 재개해주세요.',
                    style: TextStyle(fontSize: 13, color: GxColors.slate),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // 재개하기 버튼
            SizedBox(
              width: double.infinity,
              height: 44,
              child: Container(
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF10B981), Color(0xFF34D399)],
                  ),
                  borderRadius: BorderRadius.circular(GxRadius.sm),
                  boxShadow: [
                    BoxShadow(
                      color: GxColors.success.withValues(alpha: 0.3),
                      blurRadius: 8,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: () async {
                      Navigator.of(context).pop();
                      await _handleResumeAll(context, ref);
                    },
                    borderRadius: BorderRadius.circular(GxRadius.sm),
                    child: const Center(
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.play_circle, size: 20, color: Colors.white),
                          SizedBox(width: 8),
                          Text(
                            '재개하기',
                            style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Colors.white),
                          ),
                        ],
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

  /// 일시정지된 모든 작업 재개 (POST /app/work/resume)
  Future<void> _handleResumeAll(BuildContext context, WidgetRef ref) async {
    try {
      final apiService = ref.read(apiServiceProvider);
      await apiService.post('/app/work/resume', data: {'resume_all': true});
    } catch (e) {
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
