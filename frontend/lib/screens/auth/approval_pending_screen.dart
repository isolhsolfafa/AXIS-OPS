import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';

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
      appBar: AppBar(
        title: const Text('승인 대기'),
        centerTitle: true,
        automaticallyImplyLeading: false,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => _handleRefresh(ref),
            tooltip: '상태 새로고침',
          ),
        ],
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () => _handleRefresh(ref),
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(24.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 60),

                // 대기 아이콘
                const Icon(
                  Icons.hourglass_empty,
                  size: 100,
                  color: Colors.orange,
                ),
                const SizedBox(height: 32),

                // 제목
                const Text(
                  '관리자 승인 대기 중',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 16),

                // 사용자 정보
                if (worker != null) ...[
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.person, color: Colors.blue),
                              const SizedBox(width: 8),
                              const Text(
                                '이름: ',
                                style: TextStyle(fontWeight: FontWeight.bold),
                              ),
                              Text(worker.name),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              const Icon(Icons.email, color: Colors.blue),
                              const SizedBox(width: 8),
                              const Text(
                                '이메일: ',
                                style: TextStyle(fontWeight: FontWeight.bold),
                              ),
                              Expanded(child: Text(worker.email)),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              const Icon(Icons.work, color: Colors.blue),
                              const SizedBox(width: 8),
                              const Text(
                                '역할: ',
                                style: TextStyle(fontWeight: FontWeight.bold),
                              ),
                              Text('${worker.roleDisplayName} (${worker.role})'),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),
                ],

                // 안내 메시지
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.orange.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.orange.shade200),
                  ),
                  child: Column(
                    children: [
                      Row(
                        children: [
                          Icon(Icons.info, color: Colors.orange.shade700),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              '계정이 생성되었습니다!',
                              style: TextStyle(
                                color: Colors.orange.shade700,
                                fontWeight: FontWeight.bold,
                                fontSize: 16,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Text(
                        '관리자의 승인이 완료되면\n'
                        '앱 사용이 가능합니다.\n\n'
                        '승인은 보통 영업일 기준\n'
                        '1~2일 이내에 처리됩니다.',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: Colors.orange.shade700,
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 32),

                // 새로고침 안내
                const Text(
                  '위쪽의 새로고침 버튼을 눌러\n'
                  '승인 상태를 확인할 수 있습니다.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 14,
                    color: Colors.grey,
                  ),
                ),
                const SizedBox(height: 32),

                // 로그아웃 버튼
                SizedBox(
                  height: 56,
                  child: OutlinedButton.icon(
                    onPressed: () => _handleLogout(context, ref),
                    icon: const Icon(Icons.logout),
                    label: const Text(
                      '로그아웃',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.red,
                      side: const BorderSide(color: Colors.red),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
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
}
