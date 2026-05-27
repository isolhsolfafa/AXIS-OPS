// Sprint 79 — SI 마무리 공정 (TabBar 3개 + action 버튼)
// 탭 1 미종료 작업 (강제 종료) | 탭 2 출하 확정 (내 작업 완료 / 출고 완료) | 탭 3 출하 예정 (catch 만)
// 권한 = 현재 SI 마무리공정 화면 RBAC 동일 (SI 인원 + admin + GST manager + 작업자)
// v2.19.2: 기존 gst_products_screen + admin_options 영역 동작 (내 작업 완료 / 출고 완료 / 강제 종료) catch
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
      _showSnack('미종료 작업 조회 실패: $e', isError: true);
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
      _showSnack('출하 list 조회 실패: $e', isError: true);
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

  // ─── 동작 함수 (gst_products_screen + admin_options 영역 carrier) ───

  Future<void> _completeMyWork(int taskDetailId) async {
    final workerId = ref.read(authProvider).currentWorker?.id;
    if (workerId == null) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('내 작업 완료'),
        content: const Text('본인의 SI 마무리공정 작업을 완료 처리하시겠습니까?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('취소')),
          ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('완료')),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      final api = ref.read(apiServiceProvider);
      await api.post('/app/work/complete', data: {
        'task_id': taskDetailId, 'worker_id': workerId, 'finalize': false,
      });
      _showSnack('내 작업이 완료 처리되었습니다.', isError: false);
      _refreshCurrentTab();
    } catch (e) {
      final msg = e.toString().contains('FORBIDDEN')
          ? '본인이 시작한 작업만 완료할 수 있습니다.' : '작업 완료 실패: $e';
      _showSnack(msg, isError: true);
    }
  }

  Future<void> _shipComplete(String serialNumber) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('출고 완료'),
        content: Text(
          '$serialNumber 을(를) 출고 완료 처리하시겠습니까?\n\n'
          'SI 마무리공정과 출하완료 작업이 모두 완료 처리됩니다.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('취소')),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.green, foregroundColor: Colors.white,
            ),
            child: const Text('출고 완료'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      final api = ref.read(apiServiceProvider);
      final resp = await api.post('/app/work/ship-complete', data: {'serial_number': serialNumber});
      final alreadyDone = resp is Map && resp['already_completed'] == true;
      _showSnack(
        alreadyDone
            ? '$serialNumber 은(는) 이미 출고 완료된 제품입니다.'
            : '$serialNumber 출고 완료 처리되었습니다.',
        isError: false,
      );
      _refreshCurrentTab();
    } catch (e) {
      _showSnack('출고 완료 실패: $e', isError: true);
    }
  }

  Future<void> _forceCloseTask(int taskId, String? serialNumber) async {
    final reasonController = TextEditingController();
    DateTime selectedDateTime = DateTime.now();

    final confirmed = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: Row(
            children: const [
              Icon(Icons.stop_circle, color: Colors.red, size: 20),
              SizedBox(width: 8),
              Text('강제 종료', style: TextStyle(color: Colors.red)),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (serialNumber != null) Text('S/N: $serialNumber', style: const TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 12),
              const Text('완료 시각', style: TextStyle(fontSize: 11, color: Colors.grey)),
              const SizedBox(height: 4),
              InkWell(
                onTap: () async {
                  final date = await showDatePicker(
                    context: ctx,
                    initialDate: selectedDateTime,
                    firstDate: DateTime(2026),
                    lastDate: DateTime.now().add(const Duration(days: 1)),
                  );
                  if (date == null) return;
                  final time = await showTimePicker(
                    context: ctx,
                    initialTime: TimeOfDay.fromDateTime(selectedDateTime),
                  );
                  if (time == null) return;
                  setDialogState(() {
                    selectedDateTime = DateTime(date.year, date.month, date.day, time.hour, time.minute);
                  });
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(border: Border.all(color: Colors.grey), borderRadius: BorderRadius.circular(4)),
                  child: Row(children: [
                    const Icon(Icons.access_time, size: 16),
                    const SizedBox(width: 8),
                    Text('${selectedDateTime.year}-${selectedDateTime.month.toString().padLeft(2,'0')}-${selectedDateTime.day.toString().padLeft(2,'0')} ${selectedDateTime.hour.toString().padLeft(2,'0')}:${selectedDateTime.minute.toString().padLeft(2,'0')}'),
                  ]),
                ),
              ),
              const SizedBox(height: 12),
              const Text('종료 사유 *', style: TextStyle(fontSize: 11, color: Colors.grey)),
              const SizedBox(height: 4),
              TextField(
                controller: reasonController,
                decoration: const InputDecoration(
                  hintText: '예: 작업자 미처리, 연장 작업 미등록',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
                maxLines: 2,
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('취소')),
            ElevatedButton(
              onPressed: () => Navigator.pop(ctx, true),
              style: ElevatedButton.styleFrom(backgroundColor: Colors.red, foregroundColor: Colors.white),
              child: const Text('강제 종료'),
            ),
          ],
        ),
      ),
    );
    if (confirmed != true) return;
    final reason = reasonController.text.trim();
    if (reason.isEmpty) {
      _showSnack('종료 사유를 입력해주세요.', isError: true);
      return;
    }
    try {
      final api = ref.read(apiServiceProvider);
      await api.put('/admin/tasks/$taskId/force-close', data: {
        'completed_at': selectedDateTime.toIso8601String(),
        'close_reason': reason,
      });
      _showSnack('작업을 강제 종료했습니다.', isError: false);
      _refreshCurrentTab();
    } catch (e) {
      _showSnack('강제 종료 실패: $e', isError: true);
    }
  }

  void _showSnack(String msg, {required bool isError}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), backgroundColor: isError ? Colors.red : Colors.green),
    );
  }

  bool get _canManage {
    final w = ref.read(authProvider).currentWorker;
    return (w?.isAdmin ?? false) || (w?.isManager ?? false);
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
          children: const [SizedBox(height: 200), Center(child: Text('미종료 SI 마무리공정 작업 없음'))],
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
          final taskId = t['id'] as int?;
          final sn = t['serial_number'] as String?;
          return Card(
            margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    const Icon(Icons.warning_amber, color: Colors.orange, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text('${sn ?? '-'} · ${t['sales_order'] ?? '-'}',
                          style: const TextStyle(fontWeight: FontWeight.w600)),
                    ),
                  ]),
                  const SizedBox(height: 6),
                  Text(
                    '시작: ${t['started_at'] ?? '-'} · 작업자: ${t['worker_name'] ?? '-'}',
                    style: const TextStyle(fontSize: 12, color: Colors.grey),
                  ),
                  if (_canManage && taskId != null) ...[
                    const SizedBox(height: 8),
                    Align(
                      alignment: Alignment.centerRight,
                      child: TextButton.icon(
                        icon: const Icon(Icons.stop_circle, size: 16),
                        label: const Text('강제 종료'),
                        style: TextButton.styleFrom(foregroundColor: Colors.red),
                        onPressed: () => _forceCloseTask(taskId, sn),
                      ),
                    ),
                  ],
                ],
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
                      onRefresh: () => _fetchShipments(status: isConfirmed ? 'confirmed' : 'planned'),
                      child: ListView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        children: [
                          const SizedBox(height: 200),
                          Center(child: Text(isConfirmed ? '오늘 출하 예정 없음' : '미래 출하 예정 없음')),
                        ],
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: () => _fetchShipments(status: isConfirmed ? 'confirmed' : 'planned'),
                      child: ListView.builder(
                        physics: const AlwaysScrollableScrollPhysics(),
                        itemCount: items.length,
                        itemBuilder: (ctx, idx) => _buildShipmentCard(items[idx], isConfirmed: isConfirmed),
                      ),
                    ),
        ),
      ],
    );
  }

  Widget _buildShipmentCard(Map<String, dynamic> item, {required bool isConfirmed}) {
    final inProgress = item['is_si_finishing_in_progress'] == true;
    final sn = item['serial_number'] as String?;
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(Icons.local_shipping, color: inProgress ? Colors.orange : Colors.green, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text('${sn ?? '-'} · ${item['sales_order'] ?? '-'}',
                    style: const TextStyle(fontWeight: FontWeight.w600)),
              ),
              if (inProgress)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: Colors.orange.shade100,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Text('🔄 작업 진행 중',
                      style: TextStyle(fontSize: 10, color: Colors.deepOrange)),
                ),
            ]),
            const SizedBox(height: 6),
            Text(
              '${item['model'] ?? '-'} · ${item['customer'] ?? '-'} · 출하 ${item['ship_plan_date'] ?? '-'}',
              style: const TextStyle(fontSize: 12, color: Colors.grey),
            ),
            // Tab 2 (출하 확정) 영역 만 [출고 완료] 버튼 (admin/manager)
            if (isConfirmed && _canManage && sn != null) ...[
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerRight,
                child: ElevatedButton.icon(
                  icon: const Icon(Icons.check_circle, size: 16),
                  label: const Text('출고 완료'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.green, foregroundColor: Colors.white,
                  ),
                  onPressed: () => _shipComplete(sn),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
