// Sprint 79 — SI 마무리 공정 (TabBar 3개)
// 탭 1 미종료 작업 | 탭 2 출하 확정 | 탭 3 출하 예정
// 권한 = 현재 SI 마무리공정 화면 RBAC 동일 (SI 인원 + admin + GST manager + 작업자)
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';

class SiFinishingScreen extends ConsumerStatefulWidget {
  const SiFinishingScreen({super.key});

  @override
  ConsumerState<SiFinishingScreen> createState() => _SiFinishingScreenState();
}

class _SiFinishingScreenState extends ConsumerState<SiFinishingScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  // 탭별 데이터 catch
  List<Map<String, dynamic>> _pendingTasks = [];
  List<Map<String, dynamic>> _confirmedShipments = [];
  List<Map<String, dynamic>> _plannedShipments = [];

  bool _loadingPending = false;
  bool _loadingConfirmed = false;
  bool _loadingPlanned = false;

  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _tabController.addListener(() {
      if (!_tabController.indexIsChanging) _refreshCurrentTab();
    });
    WidgetsBinding.instance.addPostFrameCallback((_) => _refreshCurrentTab());
  }

  @override
  void dispose() {
    _tabController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  void _refreshCurrentTab() {
    final idx = _tabController.index;
    if (idx == 0) {
      _fetchPendingTasks();
    } else if (idx == 1) {
      _fetchShipments(status: 'confirmed');
    } else {
      _fetchShipments(status: 'planned');
    }
  }

  Future<void> _fetchPendingTasks() async {
    setState(() => _loadingPending = true);
    try {
      final api = ref.read(apiServiceProvider);
      final res = await api.get('/admin/tasks/pending?category=SI');
      final tasks = List<Map<String, dynamic>>.from(res['tasks'] as List? ?? []);
      // SI_FINISHING 만 필터 (BE 영역 category=SI 영역 모든 SI task catch)
      final filtered = tasks.where((t) => t['task_id'] == 'SI_FINISHING').toList();
      if (mounted) setState(() => _pendingTasks = filtered);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('미종료 작업 조회 실패: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _loadingPending = false);
    }
  }

  Future<void> _fetchShipments({required String status}) async {
    final isConfirmed = status == 'confirmed';
    setState(() {
      if (isConfirmed) {
        _loadingConfirmed = true;
      } else {
        _loadingPlanned = true;
      }
    });
    try {
      final api = ref.read(apiServiceProvider);
      final query = StringBuffer('/admin/shipment/by-status?status=$status&per_page=200');
      if (!isConfirmed && _searchQuery.isNotEmpty) {
        query.write('&q=${Uri.encodeQueryComponent(_searchQuery)}');
      }
      final res = await api.get(query.toString());
      final items = List<Map<String, dynamic>>.from(res['items'] as List? ?? []);
      if (mounted) {
        setState(() {
          if (isConfirmed) {
            _confirmedShipments = items;
          } else {
            _plannedShipments = items;
          }
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('출하 list 조회 실패: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          if (isConfirmed) {
            _loadingConfirmed = false;
          } else {
            _loadingPlanned = false;
          }
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('SI 마무리 공정'),
        bottom: TabBar(
          controller: _tabController,
          tabs: [
            Tab(text: '미종료 (${_pendingTasks.length})'),
            Tab(text: '출하 확정 (${_confirmedShipments.length})'),
            Tab(text: '출하 예정 (${_plannedShipments.length})'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildPendingTab(),
          _buildShipmentTab(_confirmedShipments, _loadingConfirmed, isConfirmed: true),
          _buildShipmentTab(_plannedShipments, _loadingPlanned, isConfirmed: false),
        ],
      ),
    );
  }

  Widget _buildPendingTab() {
    if (_loadingPending) return const Center(child: CircularProgressIndicator());
    if (_pendingTasks.isEmpty) {
      return RefreshIndicator(
        onRefresh: _fetchPendingTasks,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: const [
            SizedBox(height: 200),
            Center(child: Text('미종료 SI 마무리공정 작업 없음')),
          ],
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _fetchPendingTasks,
      child: ListView.builder(
        physics: const AlwaysScrollableScrollPhysics(),
        itemCount: _pendingTasks.length,
        itemBuilder: (ctx, idx) {
          final t = _pendingTasks[idx];
          return Card(
            margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            child: ListTile(
              leading: const Icon(Icons.warning_amber, color: Colors.orange),
              title: Text('${t['serial_number'] ?? '-'} · ${t['sales_order'] ?? '-'}'),
              subtitle: Text(
                '시작: ${t['started_at'] ?? '-'} · 작업자: ${t['worker_name'] ?? '-'}',
                style: const TextStyle(fontSize: 12),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildShipmentTab(
    List<Map<String, dynamic>> items,
    bool loading,
    {required bool isConfirmed}
  ) {
    return Column(
      children: [
        if (!isConfirmed)
          Padding(
            padding: const EdgeInsets.all(8),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'S/N 또는 O/N 검색',
                prefixIcon: const Icon(Icons.search),
                border: const OutlineInputBorder(),
                isDense: true,
                suffixIcon: _searchQuery.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          setState(() => _searchQuery = '');
                          _fetchShipments(status: 'planned');
                        },
                      )
                    : null,
              ),
              onSubmitted: (v) {
                setState(() => _searchQuery = v.trim());
                _fetchShipments(status: 'planned');
              },
            ),
          ),
        Expanded(
          child: loading
              ? const Center(child: CircularProgressIndicator())
              : items.isEmpty
                  ? RefreshIndicator(
                      onRefresh: () => _fetchShipments(
                        status: isConfirmed ? 'confirmed' : 'planned',
                      ),
                      child: ListView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        children: [
                          const SizedBox(height: 200),
                          Center(
                            child: Text(isConfirmed ? '오늘 출하 예정 없음' : '미래 출하 예정 없음'),
                          ),
                        ],
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: () => _fetchShipments(
                        status: isConfirmed ? 'confirmed' : 'planned',
                      ),
                      child: ListView.builder(
                        physics: const AlwaysScrollableScrollPhysics(),
                        itemCount: items.length,
                        itemBuilder: (ctx, idx) => _buildShipmentCard(items[idx]),
                      ),
                    ),
        ),
      ],
    );
  }

  Widget _buildShipmentCard(Map<String, dynamic> item) {
    final inProgress = item['is_si_finishing_in_progress'] == true;
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: ListTile(
        leading: Icon(
          Icons.local_shipping,
          color: inProgress ? Colors.orange : Colors.green,
        ),
        title: Row(
          children: [
            Expanded(
              child: Text('${item['serial_number'] ?? '-'} · ${item['sales_order'] ?? '-'}'),
            ),
            if (inProgress)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.orange.shade100,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text(
                  '🔄 작업 진행 중',
                  style: TextStyle(fontSize: 10, color: Colors.deepOrange),
                ),
              ),
          ],
        ),
        subtitle: Text(
          '${item['model'] ?? '-'} · ${item['customer'] ?? '-'} · 출하 ${item['ship_plan_date'] ?? '-'}',
          style: const TextStyle(fontSize: 12),
        ),
      ),
    );
  }
}
