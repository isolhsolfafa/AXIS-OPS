// Sprint 79 — 비활성 사용자 관리 (메인 메뉴, admin only)
// 비활성 사용자 (n일 미로그인) + 비활성화 계정 통합
// admin_options 영역 영역 분리 catch
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';

class InactiveUsersScreen extends ConsumerStatefulWidget {
  const InactiveUsersScreen({super.key});

  @override
  ConsumerState<InactiveUsersScreen> createState() => _InactiveUsersScreenState();
}

class _InactiveUsersScreenState extends ConsumerState<InactiveUsersScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  List<Map<String, dynamic>> _inactiveWorkers = [];
  List<Map<String, dynamic>> _deactivatedWorkers = [];
  bool _loadingInactive = false;
  bool _loadingDeactivated = false;
  int _inactiveDays = 30;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _fetchInactive();
      _fetchDeactivated();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _fetchInactive() async {
    setState(() => _loadingInactive = true);
    try {
      final api = ref.read(apiServiceProvider);
      final res = await api.get('/admin/inactive-workers?days=$_inactiveDays');
      final items = List<Map<String, dynamic>>.from(res['inactive_workers'] as List? ?? []);
      if (mounted) setState(() => _inactiveWorkers = items);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('비활성 사용자 조회 실패: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _loadingInactive = false);
    }
  }

  Future<void> _fetchDeactivated() async {
    setState(() => _loadingDeactivated = true);
    try {
      final api = ref.read(apiServiceProvider);
      final res = await api.get('/admin/deactivated-workers');
      final items = List<Map<String, dynamic>>.from(res['deactivated_workers'] as List? ?? []);
      if (mounted) setState(() => _deactivatedWorkers = items);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('비활성화 계정 조회 실패: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _loadingDeactivated = false);
    }
  }

  Future<void> _toggleActive(int workerId, String action) async {
    try {
      final api = ref.read(apiServiceProvider);
      await api.put('/admin/workers/$workerId/active', data: {'action': action});
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(action == 'deactivate' ? '비활성화 완료' : '재활성화 완료')),
        );
      }
      _fetchInactive();
      _fetchDeactivated();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('처리 실패: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('비활성 사용자 관리'),
        bottom: TabBar(
          controller: _tabController,
          tabs: [
            Tab(text: '미로그인 (${_inactiveWorkers.length})'),
            Tab(text: '비활성화 계정 (${_deactivatedWorkers.length})'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildInactiveTab(),
          _buildDeactivatedTab(),
        ],
      ),
    );
  }

  Widget _buildInactiveTab() {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(8),
          child: Row(
            children: [
              const Text('기간 (일):'),
              const SizedBox(width: 8),
              DropdownButton<int>(
                value: _inactiveDays,
                items: const [
                  DropdownMenuItem(value: 7, child: Text('7일')),
                  DropdownMenuItem(value: 14, child: Text('14일')),
                  DropdownMenuItem(value: 30, child: Text('30일')),
                  DropdownMenuItem(value: 60, child: Text('60일')),
                  DropdownMenuItem(value: 90, child: Text('90일')),
                ],
                onChanged: (v) {
                  if (v != null) {
                    setState(() => _inactiveDays = v);
                    _fetchInactive();
                  }
                },
              ),
              const Spacer(),
              IconButton(icon: const Icon(Icons.refresh), onPressed: _fetchInactive),
            ],
          ),
        ),
        Expanded(
          child: _loadingInactive
              ? const Center(child: CircularProgressIndicator())
              : _inactiveWorkers.isEmpty
                  ? const Center(child: Text('미로그인 사용자 없음'))
                  : ListView.builder(
                      itemCount: _inactiveWorkers.length,
                      itemBuilder: (ctx, idx) {
                        final w = _inactiveWorkers[idx];
                        return Card(
                          margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                          child: ListTile(
                            title: Text('${w['name'] ?? '-'} (${w['email'] ?? '-'})'),
                            subtitle: Text(
                              '${w['company'] ?? '-'} · ${w['role'] ?? '-'} · '
                              '마지막 로그인: ${w['last_login_at'] ?? '-'}',
                              style: const TextStyle(fontSize: 12),
                            ),
                            trailing: TextButton(
                              child: const Text('비활성화'),
                              onPressed: () => _toggleActive(w['id'] as int, 'deactivate'),
                            ),
                          ),
                        );
                      },
                    ),
        ),
      ],
    );
  }

  Widget _buildDeactivatedTab() {
    return RefreshIndicator(
      onRefresh: _fetchDeactivated,
      child: _loadingDeactivated
          ? const Center(child: CircularProgressIndicator())
          : _deactivatedWorkers.isEmpty
              ? ListView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  children: const [
                    SizedBox(height: 200),
                    Center(child: Text('비활성화된 계정 없음')),
                  ],
                )
              : ListView.builder(
                  physics: const AlwaysScrollableScrollPhysics(),
                  itemCount: _deactivatedWorkers.length,
                  itemBuilder: (ctx, idx) {
                    final w = _deactivatedWorkers[idx];
                    return Card(
                      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                      child: ListTile(
                        title: Text('${w['name'] ?? '-'} (${w['email'] ?? '-'})'),
                        subtitle: Text(
                          '${w['company'] ?? '-'} · ${w['role'] ?? '-'}',
                          style: const TextStyle(fontSize: 12),
                        ),
                        trailing: TextButton(
                          child: const Text('재활성화'),
                          onPressed: () => _toggleActive(w['id'] as int, 'reactivate'),
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}
