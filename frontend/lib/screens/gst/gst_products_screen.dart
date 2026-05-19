import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../utils/design_system.dart';

/// GST 제품 목록 화면
///
/// PI/QI/SI 카테고리별로 진행 중인 제품 목록을 표시
/// GST 작업자 및 관리자만 접근 가능
class GstProductsScreen extends ConsumerStatefulWidget {
  final String category; // PI, QI, SI

  const GstProductsScreen({super.key, required this.category});

  @override
  ConsumerState<GstProductsScreen> createState() => _GstProductsScreenState();
}

class _GstProductsScreenState extends ConsumerState<GstProductsScreen> {
  bool _isLoading = false;
  String? _errorMessage;
  List<Map<String, dynamic>> _products = [];
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _fetchProducts();
    });
  }

  Future<void> _fetchProducts() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final apiService = ref.read(apiServiceProvider);
      final response = await apiService.get(
        '/app/gst/products/${widget.category}',
      );

      List<Map<String, dynamic>> products = [];
      if (response is List) {
        products = response.cast<Map<String, dynamic>>();
      } else if (response is Map && response['products'] != null) {
        products = (response['products'] as List).cast<Map<String, dynamic>>();
      }

      if (!mounted) return;
      setState(() {
        _products = products;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  /// 출고 완료 — SI task 2개(마무리공정 + 출하완료) 완료 처리 (admin/manager)
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
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('취소'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: ElevatedButton.styleFrom(
              backgroundColor: GxColors.accent,
              foregroundColor: GxColors.white,
            ),
            child: const Text('출고 완료'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      final apiService = ref.read(apiServiceProvider);
      final resp = await apiService.post(
        '/app/work/ship-complete',
        data: {'serial_number': serialNumber},
      );
      if (!mounted) return;
      // Codex M-Q2: 멱등 응답(already_completed) 시 사실 기반 메시지
      final alreadyDone = resp is Map && resp['already_completed'] == true;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(alreadyDone
              ? '$serialNumber 은(는) 이미 출고 완료된 제품입니다.'
              : '$serialNumber 출고 완료 처리되었습니다.'),
          backgroundColor: GxColors.success,
        ),
      );
      _fetchProducts();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('출고 완료 실패: $e'),
          backgroundColor: GxColors.danger,
        ),
      );
    }
  }

  /// 내 작업 완료 — 본인의 해당 공정 작업만 완료 (relay 모드)
  Future<void> _completeMyWork(int taskDetailId) async {
    final workerId = ref.read(authProvider).currentWorker?.id;
    if (workerId == null) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('내 작업 완료'),
        content: Text('본인의 $_categoryLabel 작업을 완료 처리하시겠습니까?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('취소'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('완료'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      final apiService = ref.read(apiServiceProvider);
      await apiService.post(
        '/app/work/complete',
        data: {'task_id': taskDetailId, 'worker_id': workerId, 'finalize': false},
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('내 작업이 완료 처리되었습니다.'),
          backgroundColor: GxColors.success,
        ),
      );
      _fetchProducts();
    } catch (e) {
      if (!mounted) return;
      // Codex M-Q3: 권한 오류(403 FORBIDDEN)는 사용자 친화 메시지로 매핑
      final msg = e.toString().contains('FORBIDDEN')
          ? '본인이 시작한 작업만 완료할 수 있습니다.'
          : '작업 완료 실패: $e';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(msg),
          backgroundColor: GxColors.danger,
        ),
      );
    }
  }

  /// PI/QI 공정 종료 — admin/manager 정상 완료 (Sprint 69, 종료 시각 지정)
  Future<void> _adminComplete(String serialNumber) async {
    DateTime selected = DateTime.now();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: Text('$_categoryLabel 종료'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('$serialNumber 의 $_categoryLabel을(를) 종료 처리하시겠습니까?'),
              const SizedBox(height: 12),
              Row(
                children: [
                  const Text('종료 시각  ',
                      style: TextStyle(fontSize: 12, color: GxColors.steel)),
                  Expanded(
                    child: Text(
                      '${selected.month}/${selected.day} '
                      '${selected.hour.toString().padLeft(2, '0')}:'
                      '${selected.minute.toString().padLeft(2, '0')}',
                      style: const TextStyle(
                          fontSize: 13, fontWeight: FontWeight.w600),
                    ),
                  ),
                  TextButton(
                    onPressed: () async {
                      final d = await showDatePicker(
                        context: ctx,
                        initialDate: selected,
                        firstDate: DateTime(2020),
                        lastDate: DateTime.now(),
                      );
                      if (d == null) return;
                      final t = await showTimePicker(
                        context: ctx,
                        initialTime: TimeOfDay.fromDateTime(selected),
                      );
                      if (t == null) return;
                      setDialogState(() {
                        selected = DateTime(
                            d.year, d.month, d.day, t.hour, t.minute);
                      });
                    },
                    child: const Text('변경'),
                  ),
                ],
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('취소'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.pop(ctx, true),
              style: ElevatedButton.styleFrom(
                backgroundColor: _categoryColor,
                foregroundColor: GxColors.white,
              ),
              child: const Text('종료'),
            ),
          ],
        ),
      ),
    );
    if (confirmed != true) return;
    // Codex M-Q1: showTimePicker 는 시각 무제한 → 오늘 날짜 + 미래 시각 조합 차단
    if (selected.isAfter(DateTime.now())) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('종료 시각은 현재 시각보다 미래일 수 없습니다.'),
          backgroundColor: GxColors.danger,
        ),
      );
      return;
    }
    try {
      final apiService = ref.read(apiServiceProvider);
      final resp = await apiService.post(
        '/app/work/admin-complete',
        data: {
          'serial_number': serialNumber,
          'task_category': widget.category,
          'completed_at': selected.toIso8601String(),
        },
      );
      if (!mounted) return;
      final alreadyDone = resp is Map && resp['already_completed'] == true;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(alreadyDone
              ? '$serialNumber 은(는) 이미 $_categoryLabel이(가) 종료된 S/N 입니다.'
              : '$serialNumber $_categoryLabel 종료 처리되었습니다.'),
          backgroundColor: GxColors.success,
        ),
      );
      _fetchProducts();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('종료 처리 실패: $e'),
          backgroundColor: GxColors.danger,
        ),
      );
    }
  }

  /// O/N · S/N 검색 필터 (Sprint 69 FE-B)
  List<Map<String, dynamic>> get _filteredProducts {
    final q = _searchQuery.trim().toLowerCase();
    if (q.isEmpty) return _products;
    return _products.where((p) {
      final sn = (p['serial_number'] as String? ?? '').toLowerCase();
      final on = (p['sales_order'] as String? ?? '').toLowerCase();
      return sn.contains(q) || on.contains(q);
    }).toList();
  }

  /// 카테고리 한국어 레이블
  String get _categoryLabel {
    switch (widget.category) {
      case 'PI': return 'PI 가압검사';
      case 'QI': return 'QI 공정검사';
      case 'SI': return 'SI 마무리공정';
      default: return widget.category;
    }
  }

  /// 카테고리 아이콘
  IconData get _categoryIcon {
    switch (widget.category) {
      case 'PI': return Icons.compress;
      case 'QI': return Icons.verified;
      case 'SI': return Icons.local_shipping;
      default: return Icons.work_outline;
    }
  }

  /// 카테고리 색상
  Color get _categoryColor {
    switch (widget.category) {
      case 'PI': return GxColors.success;
      case 'QI': return const Color(0xFF7C3AED);
      case 'SI': return GxColors.accent;
      default: return GxColors.accent;
    }
  }

  /// 작업 상태 색상
  Color _getStatusColor(String? status) {
    switch (status) {
      case 'not_started': return GxColors.steel;
      case 'in_progress': return GxColors.info;
      case 'paused': return GxColors.warning;
      case 'completed': return GxColors.success;
      default: return GxColors.steel;
    }
  }

  /// 작업 상태 한국어 레이블
  String _getStatusLabel(String? status) {
    switch (status) {
      case 'not_started': return '미시작';
      case 'in_progress': return '진행중';
      case 'paused': return '일시정지';
      case 'completed': return '완료';
      default: return status ?? '-';
    }
  }

  /// 작업 상태 아이콘
  IconData _getStatusIcon(String? status) {
    switch (status) {
      case 'not_started': return Icons.radio_button_unchecked;
      case 'in_progress': return Icons.play_circle_outline;
      case 'paused': return Icons.pause_circle_outline;
      case 'completed': return Icons.check_circle_outline;
      default: return Icons.help_outline;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: GxColors.cloud,
      appBar: AppBar(
        backgroundColor: GxColors.white,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, size: 18, color: GxColors.slate),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: Row(
          children: [
            Container(
              width: 28,
              height: 28,
              decoration: BoxDecoration(
                color: _categoryColor.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(GxRadius.sm),
              ),
              child: Icon(_categoryIcon, size: 14, color: _categoryColor),
            ),
            const SizedBox(width: 10),
            Text(
              _categoryLabel,
              style: const TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w600,
                color: GxColors.charcoal,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: GxColors.slate, size: 20),
            onPressed: _fetchProducts,
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: GxColors.mist),
        ),
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(
        child: CircularProgressIndicator(color: GxColors.accent),
      );
    }

    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, color: GxColors.danger, size: 40),
              const SizedBox(height: 12),
              Text(
                '데이터를 불러올 수 없습니다',
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: GxColors.charcoal,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                _errorMessage!,
                style: const TextStyle(fontSize: 12, color: GxColors.steel),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _fetchProducts,
                child: const Text('다시 시도'),
              ),
            ],
          ),
        ),
      );
    }

    if (_products.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(_categoryIcon, size: 48, color: GxColors.silver),
            const SizedBox(height: 12),
            Text(
              '진행 중인 ${_categoryLabel} 작업이 없습니다',
              style: const TextStyle(
                fontSize: 14,
                color: GxColors.steel,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      );
    }

    final filtered = _filteredProducts;
    return Column(
      children: [
        // Sprint 69 FE-B: O/N · S/N 검색 칸
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
          child: TextField(
            onChanged: (v) => setState(() => _searchQuery = v),
            decoration: InputDecoration(
              hintText: 'O/N · S/N 검색',
              prefixIcon: const Icon(Icons.search, size: 18, color: GxColors.steel),
              isDense: true,
              contentPadding:
                  const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(GxRadius.sm),
                borderSide: const BorderSide(color: GxColors.mist),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(GxRadius.sm),
                borderSide: const BorderSide(color: GxColors.mist),
              ),
            ),
            style: const TextStyle(fontSize: 13),
          ),
        ),
        Expanded(
          child: filtered.isEmpty
              ? const Center(
                  child: Text(
                    '검색 결과가 없습니다',
                    style: TextStyle(fontSize: 13, color: GxColors.steel),
                  ),
                )
              : RefreshIndicator(
                  color: GxColors.accent,
                  onRefresh: _fetchProducts,
                  child: ListView.separated(
                    padding: const EdgeInsets.all(16),
                    itemCount: filtered.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (context, index) {
                      return _buildProductCard(filtered[index]);
                    },
                  ),
                ),
        ),
      ],
    );
  }

  Widget _buildProductCard(Map<String, dynamic> product) {
    final status = product['task_status'] as String?;
    final statusColor = _getStatusColor(status);
    final serialNumber = product['serial_number'] as String? ?? '-';
    final model = product['model'] as String? ?? '-';
    final customer = product['customer'] as String? ?? '';
    final salesOrder = product['sales_order'] as String? ?? '';
    final taskName = product['task_name'] as String? ?? '-';
    // 멀티 작업자 지원: workers 배열 우선, 없으면 worker_name fallback
    final workers = product['workers'] as List?;
    final workerName = (workers != null && workers.isNotEmpty)
        ? (workers.length > 1
            ? '${workers.first['worker_name']} 외 ${workers.length - 1}명'
            : workers.first['worker_name'] as String?)
        : product['worker_name'] as String?;
    final startedAt = product['started_at'] as String?;
    final taskDetailId = product['task_detail_id'] as int?;
    final auth = ref.read(authProvider);
    final canShip = auth.isAdmin || auth.isManager;

    String? formattedStartedAt;
    if (startedAt != null) {
      try {
        final dt = DateTime.parse(startedAt).toLocal();
        formattedStartedAt = '${dt.month}/${dt.day} ${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
      } catch (_) {
        formattedStartedAt = startedAt;
      }
    }

    return Container(
      decoration: GxGlass.cardSm(radius: GxRadius.md),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: taskDetailId != null
              ? () => Navigator.pushNamed(
                    context,
                    '/task-detail',
                    arguments: {'task_detail_id': taskDetailId},
                  )
              : null,
          borderRadius: BorderRadius.circular(GxRadius.md),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            serialNumber,
                            style: const TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              color: GxColors.charcoal,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            model,
                            style: const TextStyle(fontSize: 12, color: GxColors.slate),
                          ),
                          if (customer.isNotEmpty || salesOrder.isNotEmpty) ...[
                            const SizedBox(height: 2),
                            Text(
                              [
                                if (salesOrder.isNotEmpty) 'O/N $salesOrder',
                                if (customer.isNotEmpty) customer,
                              ].join('  ·  '),
                              style: const TextStyle(fontSize: 11, color: GxColors.steel),
                            ),
                          ],
                        ],
                      ),
                    ),
                    // 상태 배지
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: statusColor.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(GxRadius.sm),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(_getStatusIcon(status), size: 12, color: statusColor),
                          const SizedBox(width: 4),
                          Text(
                            _getStatusLabel(status),
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              color: statusColor,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                const Divider(color: GxColors.mist, height: 1),
                const SizedBox(height: 10),
                Row(
                  children: [
                    const Icon(Icons.assignment_outlined, size: 13, color: GxColors.steel),
                    const SizedBox(width: 5),
                    Expanded(
                      child: Text(
                        taskName,
                        style: const TextStyle(fontSize: 12, color: GxColors.graphite),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                if (workerName != null || formattedStartedAt != null) ...[
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      if (workerName != null) ...[
                        const Icon(Icons.person_outline, size: 13, color: GxColors.silver),
                        const SizedBox(width: 4),
                        Text(
                          workerName,
                          style: const TextStyle(fontSize: 11, color: GxColors.steel),
                        ),
                      ],
                      if (workerName != null && formattedStartedAt != null)
                        const SizedBox(width: 12),
                      if (formattedStartedAt != null) ...[
                        const Icon(Icons.access_time, size: 13, color: GxColors.silver),
                        const SizedBox(width: 4),
                        Text(
                          formattedStartedAt,
                          style: const TextStyle(fontSize: 11, color: GxColors.steel),
                        ),
                      ],
                    ],
                  ),
                ],
                // Sprint 68/69: 작업 완료 버튼 영역 ("진행중" 뱃지 아래)
                // [내 작업 완료] = 진행 중 task / SI=[출고 완료], PI·QI=[종료] (admin·manager)
                if (taskDetailId != null &&
                    (status == 'in_progress' || canShip)) ...[
                  const SizedBox(height: 12),
                  const Divider(color: GxColors.mist, height: 1),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      if (status == 'in_progress')
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: () => _completeMyWork(taskDetailId),
                            icon: const Icon(Icons.check, size: 15),
                            label: const Text('내 작업 완료', style: TextStyle(fontSize: 12)),
                            style: OutlinedButton.styleFrom(
                              foregroundColor: GxColors.info,
                              side: const BorderSide(color: GxColors.info),
                              padding: const EdgeInsets.symmetric(vertical: 8),
                            ),
                          ),
                        ),
                      if (status == 'in_progress' && canShip)
                        const SizedBox(width: 8),
                      if (canShip)
                        Expanded(
                          child: widget.category == 'SI'
                              ? ElevatedButton.icon(
                                  onPressed: () => _shipComplete(serialNumber),
                                  icon: const Icon(Icons.local_shipping, size: 15),
                                  label: const Text('출고 완료',
                                      style: TextStyle(fontSize: 12)),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: GxColors.accent,
                                    foregroundColor: GxColors.white,
                                    padding: const EdgeInsets.symmetric(vertical: 8),
                                  ),
                                )
                              : ElevatedButton.icon(
                                  onPressed: () => _adminComplete(serialNumber),
                                  icon: const Icon(Icons.task_alt, size: 15),
                                  label: const Text('종료',
                                      style: TextStyle(fontSize: 12)),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: _categoryColor,
                                    foregroundColor: GxColors.white,
                                    padding: const EdgeInsets.symmetric(vertical: 8),
                                  ),
                                ),
                        ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
