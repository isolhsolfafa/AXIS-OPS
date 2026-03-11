import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../utils/design_system.dart';

/// Manager 권한 부여 화면
/// Sprint 23: 같은 회사 소속 작업자에게 is_manager 권한 부여/해제
class ManagerDelegationScreen extends ConsumerStatefulWidget {
  const ManagerDelegationScreen({super.key});

  @override
  ConsumerState<ManagerDelegationScreen> createState() =>
      _ManagerDelegationScreenState();
}

class _ManagerDelegationScreenState
    extends ConsumerState<ManagerDelegationScreen> {
  List<Map<String, dynamic>> _workers = [];
  bool _loading = true;
  final Set<int> _toggling = {}; // 토글 진행 중인 worker id

  @override
  void initState() {
    super.initState();
    _loadWorkers();
  }

  Future<void> _loadWorkers() async {
    setState(() => _loading = true);
    try {
      final apiService = ref.read(apiServiceProvider);
      // Manager: BE에서 같은 company 자동 필터, Admin: 전체
      final response = await apiService.get('/admin/managers');
      final list = (response['workers'] as List?) ?? [];
      setState(() {
        _workers = list.cast<Map<String, dynamic>>();
        _loading = false;
      });
    } catch (e) {
      setState(() => _loading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('작업자 목록 조회 실패: $e')),
        );
      }
    }
  }

  Future<void> _toggleManager(int workerId, bool newValue) async {
    setState(() => _toggling.add(workerId));
    try {
      final apiService = ref.read(apiServiceProvider);
      await apiService.put(
        '/admin/workers/$workerId/manager',
        data: {'is_manager': newValue},
      );

      // 로컬 상태 업데이트
      setState(() {
        final idx = _workers.indexWhere((w) => w['id'] == workerId);
        if (idx >= 0) {
          _workers[idx] = {..._workers[idx], 'is_manager': newValue};
        }
        _toggling.remove(workerId);
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(newValue ? '관리자 지정 완료' : '관리자 해제 완료'),
            duration: const Duration(seconds: 1),
          ),
        );
      }
    } catch (e) {
      setState(() => _toggling.remove(workerId));
      if (mounted) {
        final msg = e.toString();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(
            msg.contains('FORBIDDEN') ? '권한이 없습니다 (다른 회사 또는 Admin 계정)' : '변경 실패: $msg',
          )),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final worker = ref.watch(authProvider).currentWorker;
    final isAdmin = worker?.isAdmin == true;

    return Scaffold(
      backgroundColor: GxColors.cloud,
      appBar: AppBar(
        title: const Text(
          '관리자 권한 부여',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
            color: GxColors.charcoal,
          ),
        ),
        backgroundColor: Colors.white,
        elevation: 0,
        iconTheme: const IconThemeData(color: GxColors.charcoal),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: GxColors.mist),
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _workers.isEmpty
              ? const Center(
                  child: Text(
                    '표시할 작업자가 없습니다.',
                    style: TextStyle(color: GxColors.steel),
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _loadWorkers,
                  child: ListView.separated(
                    padding: const EdgeInsets.all(16),
                    itemCount: _workers.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (context, index) {
                      final w = _workers[index];
                      final wId = w['id'] as int;
                      final isTargetAdmin = w['is_admin'] == true;
                      final isManager = w['is_manager'] == true;
                      final isTogglingNow = _toggling.contains(wId);

                      // Admin 계정은 토글 비활성화 (Manager가 변경 불가)
                      final canToggle = isAdmin || !isTargetAdmin;

                      return Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 12,
                        ),
                        decoration: GxGlass.cardSm(radius: GxRadius.md),
                        child: Row(
                          children: [
                            // 아이콘
                            Container(
                              width: 40,
                              height: 40,
                              decoration: BoxDecoration(
                                color: isTargetAdmin
                                    ? GxColors.warningBg
                                    : isManager
                                        ? const Color(0xFFEDE9FE)
                                        : GxColors.cloud,
                                borderRadius: BorderRadius.circular(20),
                              ),
                              child: Icon(
                                isTargetAdmin
                                    ? Icons.shield
                                    : isManager
                                        ? Icons.supervisor_account
                                        : Icons.person_outline,
                                size: 20,
                                color: isTargetAdmin
                                    ? GxColors.warning
                                    : isManager
                                        ? const Color(0xFF7C3AED)
                                        : GxColors.steel,
                              ),
                            ),
                            const SizedBox(width: 12),
                            // 정보
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Text(
                                        w['name'] ?? '',
                                        style: const TextStyle(
                                          fontSize: 14,
                                          fontWeight: FontWeight.w600,
                                          color: GxColors.charcoal,
                                        ),
                                      ),
                                      if (isTargetAdmin) ...[
                                        const SizedBox(width: 6),
                                        Container(
                                          padding: const EdgeInsets.symmetric(
                                            horizontal: 6,
                                            vertical: 1,
                                          ),
                                          decoration: BoxDecoration(
                                            color: GxColors.warningBg,
                                            borderRadius:
                                                BorderRadius.circular(8),
                                          ),
                                          child: const Text(
                                            'Admin',
                                            style: TextStyle(
                                              fontSize: 10,
                                              fontWeight: FontWeight.w500,
                                              color: GxColors.warning,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ],
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    '${w['company'] ?? '-'} · ${w['role'] ?? '-'}',
                                    style: const TextStyle(
                                      fontSize: 12,
                                      color: GxColors.steel,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            // 토글
                            if (isTogglingNow)
                              const SizedBox(
                                width: 24,
                                height: 24,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            else
                              Switch(
                                value: isManager,
                                onChanged: canToggle
                                    ? (val) => _toggleManager(wId, val)
                                    : null,
                                activeTrackColor: const Color(0xFFEDE9FE),
                                activeThumbColor: const Color(0xFF7C3AED),
                              ),
                          ],
                        ),
                      );
                    },
                  ),
                ),
    );
  }
}
