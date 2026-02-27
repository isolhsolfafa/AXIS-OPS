import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../utils/design_system.dart';

/// 관리자 승인 대기 화면
///
/// 회원가입 및 이메일 인증 완료 후, 관리자 승인을 기다리는 동안 표시되는 화면
class ApprovalPendingScreen extends ConsumerWidget {
  const ApprovalPendingScreen({Key? key}) : super(key: key);

  Future<void> _handleLogout(BuildContext context, WidgetRef ref) async {
    final authNotifier = ref.read(authProvider.notifier);
    await authNotifier.logout();
  }

  Future<void> _handleRefresh(WidgetRef ref) async {
    final authNotifier = ref.read(authProvider.notifier);
    await authNotifier.refreshCurrentWorker();
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final worker = authState.currentWorker;

    return Scaffold(
      backgroundColor: GxColors.cloud,
      appBar: AppBar(
        backgroundColor: GxColors.white,
        elevation: 0,
        foregroundColor: GxColors.charcoal,
        automaticallyImplyLeading: false,
        title: Row(
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
            const Text(
              '승인 대기',
              style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: GxColors.charcoal),
            ),
          ],
        ),
        centerTitle: false,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: GxColors.slate, size: 22),
            onPressed: () => _handleRefresh(ref),
            tooltip: '상태 새로고침',
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: GxColors.mist),
        ),
      ),
      body: SafeArea(
        child: RefreshIndicator(
          color: GxColors.accent,
          onRefresh: () => _handleRefresh(ref),
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(20.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 32),

                // 대기 아이콘
                Container(
                  width: 64,
                  height: 64,
                  margin: const EdgeInsets.symmetric(horizontal: 120),
                  decoration: BoxDecoration(
                    color: GxColors.accentSoft,
                    borderRadius: BorderRadius.circular(GxRadius.lg),
                  ),
                  child: const Icon(Icons.hourglass_empty, size: 32, color: GxColors.accent),
                ),
                const SizedBox(height: 20),

                // 제목
                const Text(
                  '관리자 승인 대기 중',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: GxColors.charcoal),
                ),
                const SizedBox(height: 20),

                // 사용자 정보 카드
                if (worker != null) ...[
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: GxGlass.cardSm(radius: GxRadius.lg),
                    child: Column(
                      children: [
                        _buildInfoRow(Icons.person, '이름', worker.name),
                        const Divider(height: 20, color: GxColors.mist),
                        _buildInfoRow(Icons.email, '이메일', worker.email),
                        const Divider(height: 20, color: GxColors.mist),
                        _buildInfoRow(Icons.work, '역할', '${worker.roleDisplayName} (${worker.role})'),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                ],

                // 안내 메시지
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: GxGlass.cardSm(radius: GxRadius.md),
                  child: Column(
                    children: [
                      Row(
                        children: [
                          Container(
                            width: 28,
                            height: 28,
                            decoration: BoxDecoration(
                              color: GxColors.accentSoft,
                              borderRadius: BorderRadius.circular(GxRadius.sm),
                            ),
                            child: const Icon(Icons.info_outline, color: GxColors.accent, size: 14),
                          ),
                          const SizedBox(width: 8),
                          const Expanded(
                            child: Text(
                              '계정이 생성되었습니다!',
                              style: TextStyle(color: GxColors.accent, fontWeight: FontWeight.w600, fontSize: 14),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      const Text(
                        '관리자의 승인이 완료되면\n앱 사용이 가능합니다.\n\n승인은 보통 영업일 기준\n1~2일 이내에 처리됩니다.',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: GxColors.slate, fontSize: 13),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),

                // 새로고침 안내
                const Text(
                  '위쪽의 새로고침 버튼을 눌러\n승인 상태를 확인할 수 있습니다.',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 12, color: GxColors.steel),
                ),
                const SizedBox(height: 24),

                // 로그아웃 버튼
                Container(
                  height: 44,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.5),
                    borderRadius: BorderRadius.circular(GxRadius.sm),
                    border: Border.all(color: GxColors.mist, width: 1.5),
                  ),
                  child: Material(
                    color: Colors.transparent,
                    child: InkWell(
                      onTap: () => _handleLogout(context, ref),
                      borderRadius: BorderRadius.circular(GxRadius.sm),
                      child: Center(
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.logout, size: 16, color: GxColors.slate),
                            const SizedBox(width: 6),
                            const Text(
                              '로그아웃',
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w500,
                                color: GxColors.slate,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildInfoRow(IconData icon, String label, String value) {
    return Row(
      children: [
        Icon(icon, color: GxColors.accent, size: 18),
        const SizedBox(width: 10),
        Text('$label: ', style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 13, color: GxColors.slate)),
        Expanded(child: Text(value, style: const TextStyle(fontSize: 13, color: GxColors.charcoal))),
      ],
    );
  }
}
