import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../providers/alert_provider.dart';
import '../../services/websocket_service.dart';

/// 홈 화면 (메인 화면)
///
/// Sprint 1: 기본 레이아웃 및 사용자 정보 표시
/// Sprint 2: 작업 목록, QR 스캔, 관리자 기능 추가
/// Sprint 3: 알림 배지, WebSocket 실시간 알림
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({Key? key}) : super(key: key);

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  final WebSocketService _websocketService = WebSocketService();
  bool _websocketInitialized = false;

  @override
  void initState() {
    super.initState();
    // WebSocket 연결 및 알림 초기화
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _initializeAlerts();
    });
  }

  @override
  void dispose() {
    _websocketService.disconnect();
    _websocketService.dispose();
    super.dispose();
  }

  Future<void> _initializeAlerts() async {
    final authState = ref.read(authProvider);
    final token = authState.token;

    if (token != null && !_websocketInitialized) {
      try {
        // WebSocket 연결
        await _websocketService.connect(token);

        // 알림 구독
        ref.read(alertProvider.notifier).subscribeToAlerts(_websocketService);

        // 초기 알림 로드
        await ref.read(alertProvider.notifier).fetchAlerts();
        await ref.read(alertProvider.notifier).refreshUnreadCount();

        _websocketInitialized = true;
      } catch (e) {
        print('[HomeScreen] Failed to initialize alerts: $e');
      }
    }
  }

  Future<void> _handleLogout(BuildContext context, WidgetRef ref) async {
    // 로그아웃 확인 다이얼로그
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('로그아웃'),
        content: const Text('로그아웃 하시겠습니까?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('취소'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('로그아웃'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      final authNotifier = ref.read(authProvider.notifier);
      await authNotifier.logout();
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final alertState = ref.watch(alertProvider);
    final worker = authState.currentWorker;
    final unreadCount = alertState.unreadCount;

    return Scaffold(
      appBar: AppBar(
        title: const Text('G-AXIS'),
        centerTitle: true,
        actions: [
          // 알림 버튼 (배지 포함)
          Stack(
            children: [
              IconButton(
                icon: const Icon(Icons.notifications_outlined),
                onPressed: () {
                  Navigator.pushNamed(context, '/alerts');
                },
                tooltip: '알림',
              ),
              if (unreadCount > 0)
                Positioned(
                  right: 8,
                  top: 8,
                  child: Container(
                    padding: const EdgeInsets.all(4),
                    decoration: const BoxDecoration(
                      color: Colors.red,
                      shape: BoxShape.circle,
                    ),
                    constraints: const BoxConstraints(
                      minWidth: 16,
                      minHeight: 16,
                    ),
                    child: Text(
                      unreadCount > 99 ? '99+' : '$unreadCount',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),
            ],
          ),
          // 로그아웃 버튼
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () => _handleLogout(context, ref),
            tooltip: '로그아웃',
          ),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // 사용자 정보 카드
              Card(
                elevation: 2,
                child: Padding(
                  padding: const EdgeInsets.all(20.0),
                  child: Column(
                    children: [
                      const CircleAvatar(
                        radius: 40,
                        backgroundColor: Colors.blue,
                        child: Icon(
                          Icons.person,
                          size: 50,
                          color: Colors.white,
                        ),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        worker?.name ?? '사용자',
                        style: const TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        worker?.roleDisplayName ?? '',
                        style: TextStyle(
                          fontSize: 16,
                          color: Colors.grey[600],
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        worker?.email ?? '',
                        style: TextStyle(
                          fontSize: 14,
                          color: Colors.grey[500],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),

              // 기능 버튼들 (Sprint 2에서 활성화)
              const Text(
                '주요 기능',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 16),

              _buildFeatureButton(
                context,
                icon: Icons.qr_code_scanner,
                title: 'QR 스캔',
                subtitle: 'Worksheet QR 또는 Location QR 스캔',
                onTap: () {
                  Navigator.pushNamed(context, '/qr-scan');
                },
              ),
              const SizedBox(height: 12),

              _buildFeatureButton(
                context,
                icon: Icons.task_alt,
                title: '작업 관리',
                subtitle: '진행 중인 작업 확인 및 관리',
                onTap: () {
                  Navigator.pushNamed(context, '/task-management');
                },
              ),
              const SizedBox(height: 12),

              if (worker?.isAdmin == true || worker?.isManager == true)
                _buildFeatureButton(
                  context,
                  icon: Icons.admin_panel_settings,
                  title: '관리자 대시보드',
                  subtitle: '작업자 승인, 작업 현황 관리',
                  color: Colors.orange,
                  onTap: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('관리자 기능은 Sprint 4에서 구현됩니다.')),
                    );
                  },
                ),
              const SizedBox(height: 32),

              // Sprint 2 완료 안내
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.green.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.green.shade200),
                ),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Icon(Icons.check_circle, color: Colors.green.shade700),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            'Sprint 2 완료',
                            style: TextStyle(
                              color: Colors.green.shade700,
                              fontWeight: FontWeight.bold,
                              fontSize: 16,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'QR 스캔 및 Task 관리 기능이\n'
                      '구현되었습니다.\n'
                      '공정 검증 및 알림 기능은\n'
                      'Sprint 3에서 추가됩니다.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: Colors.green.shade700,
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
    );
  }

  Widget _buildFeatureButton(
    BuildContext context, {
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
    Color? color,
  }) {
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: (color ?? Colors.blue).withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  icon,
                  size: 32,
                  color: color ?? Colors.blue,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      subtitle,
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey[600],
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: Colors.grey),
            ],
          ),
        ),
      ),
    );
  }
}

