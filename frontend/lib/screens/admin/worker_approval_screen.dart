import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../utils/design_system.dart';

// TODO: 작업자 승인 화면 구현

class WorkerApprovalScreen extends ConsumerWidget {
  const WorkerApprovalScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      backgroundColor: GxColors.cloud,
      appBar: AppBar(
        backgroundColor: GxColors.white,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, size: 18, color: GxColors.accent),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 4, height: 20,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  begin: Alignment.topCenter, end: Alignment.bottomCenter,
                  colors: [GxColors.accent, GxColors.accentHover],
                ),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(width: 12),
            const Text('작업자 승인', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: GxColors.charcoal)),
          ],
        ),
        centerTitle: false,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: GxColors.mist),
        ),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 64, height: 64,
              decoration: BoxDecoration(
                color: GxColors.infoBg,
                borderRadius: BorderRadius.circular(GxRadius.lg),
              ),
              child: const Icon(Icons.how_to_reg, size: 32, color: GxColors.info),
            ),
            const SizedBox(height: 16),
            const Text('작업자 승인 화면 준비 중', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: GxColors.charcoal)),
            const SizedBox(height: 8),
            const Text('향후 업데이트에서 제공됩니다.', style: TextStyle(fontSize: 13, color: GxColors.steel)),
          ],
        ),
      ),
    );
  }
}
