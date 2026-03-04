import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../utils/design_system.dart';

/// 협력사별 S/N 작업 진행률 화면 (Sprint 18)
class SnProgressScreen extends ConsumerStatefulWidget {
  const SnProgressScreen({super.key});

  @override
  ConsumerState<SnProgressScreen> createState() => _SnProgressScreenState();
}

class _SnProgressScreenState extends ConsumerState<SnProgressScreen> {
  List<Map<String, dynamic>> _products = [];
  Map<String, dynamic> _summary = {};
  bool _loading = true;
  String? _error;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _fetchProgress();
      // 30초 자동 갱신
      _refreshTimer = Timer.periodic(
        const Duration(seconds: 30),
        (_) => _fetchProgress(),
      );
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetchProgress() async {
    try {
      final apiService = ref.read(apiServiceProvider);
      final response = await apiService.get('/app/product/progress');
      if (!mounted) return;

      final products = (response['products'] as List<dynamic>? ?? [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
      final summary = Map<String, dynamic>.from(
        response['summary'] as Map? ?? {},
      );

      setState(() {
        _products = products;
        _summary = summary;
        _loading = false;
        _error = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final worker = authState.currentWorker;
    final isGst = worker?.company == 'GST' || worker?.isAdmin == true;
    final title = isGst ? '전사 작업 진행현황' : '작업 진행현황';

    return Scaffold(
      backgroundColor: GxColors.cloud,
      appBar: AppBar(
        backgroundColor: GxColors.white,
        elevation: 0,
        title: Text(
          title,
          style: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w600,
            color: GxColors.charcoal,
          ),
        ),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: GxColors.mist),
        ),
      ),
      body: _loading
          ? const Center(
              child: CircularProgressIndicator(color: GxColors.accent),
            )
          : _error != null
              ? _buildError()
              : RefreshIndicator(
                  onRefresh: _fetchProgress,
                  color: GxColors.accent,
                  child: _products.isEmpty
                      ? _buildEmpty()
                      : _buildContent(),
                ),
    );
  }

  Widget _buildError() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 48, color: GxColors.silver),
            const SizedBox(height: 12),
            Text(
              _error ?? '오류 발생',
              style: const TextStyle(fontSize: 13, color: GxColors.steel),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            TextButton(
              onPressed: () {
                setState(() {
                  _loading = true;
                  _error = null;
                });
                _fetchProgress();
              },
              child: const Text('다시 시도'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmpty() {
    return ListView(
      children: const [
        SizedBox(height: 120),
        Center(
          child: Column(
            children: [
              Icon(Icons.inbox_outlined, size: 48, color: GxColors.silver),
              SizedBox(height: 12),
              Text(
                '담당 제품이 없습니다',
                style: TextStyle(fontSize: 13, color: GxColors.steel),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildContent() {
    final total = _summary['total'] ?? 0;
    final inProgress = _summary['in_progress'] ?? 0;
    final completedRecent = _summary['completed_recent'] ?? 0;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Summary 카드
        Container(
          padding: const EdgeInsets.all(14),
          decoration: GxGlass.cardSm(radius: GxRadius.lg),
          child: Row(
            children: [
              _buildSummaryChip('전체', '$total', GxColors.accent),
              const SizedBox(width: 10),
              _buildSummaryChip('진행 중', '$inProgress', GxColors.warning),
              const SizedBox(width: 10),
              _buildSummaryChip('최근 완료', '$completedRecent', GxColors.success),
            ],
          ),
        ),
        const SizedBox(height: 12),
        // 제품 카드 리스트
        ..._products.map(_buildProductCard),
      ],
    );
  }

  Widget _buildSummaryChip(String label, String value, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(GxRadius.sm),
        ),
        child: Column(
          children: [
            Text(
              value,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: color,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              label,
              style: const TextStyle(fontSize: 10, color: GxColors.steel),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProductCard(Map<String, dynamic> product) {
    final sn = product['serial_number'] as String? ?? '';
    final model = product['model'] as String? ?? '';
    final customer = product['customer'] as String? ?? '';
    final shipDate = product['ship_plan_date'] as String?;
    final allCompleted = product['all_completed'] as bool? ?? false;
    final overallPercent = product['overall_percent'] as int? ?? 0;
    final myCategory = product['my_category'] as String?;
    final categories =
        Map<String, dynamic>.from(product['categories'] as Map? ?? {});

    final bgColor = allCompleted ? GxColors.success.withValues(alpha: 0.04) : GxColors.white;
    final borderColor = allCompleted ? GxColors.success.withValues(alpha: 0.3) : Colors.transparent;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(GxRadius.md),
        border: Border.all(color: borderColor),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.03),
            blurRadius: 6,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 헤더: S/N + 모델 + 완료 뱃지
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      sn,
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: GxColors.charcoal,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '$model${customer.isNotEmpty ? ' · $customer' : ''}',
                      style: const TextStyle(fontSize: 11, color: GxColors.steel),
                    ),
                  ],
                ),
              ),
              if (allCompleted)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: GxColors.success.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Text(
                    '완료',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      color: GxColors.success,
                    ),
                  ),
                ),
              if (shipDate != null) ...[
                const SizedBox(width: 8),
                Text(
                  shipDate,
                  style: const TextStyle(fontSize: 10, color: GxColors.steel),
                ),
              ],
            ],
          ),
          const SizedBox(height: 10),
          // 전체 진행바
          _buildProgressBar('전체', overallPercent, GxColors.accent, false),
          const SizedBox(height: 6),
          // 카테고리별 미니 진행바
          ...categories.entries.map((entry) {
            final cat = entry.key;
            final data = Map<String, dynamic>.from(entry.value as Map);
            final percent = data['percent'] as int? ?? 0;
            final isMine = myCategory == cat;
            final color = _categoryColor(cat);
            return Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: _buildProgressBar(cat, percent, color, isMine),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildProgressBar(
    String label,
    int percent,
    Color color,
    bool highlight,
  ) {
    return Row(
      children: [
        SizedBox(
          width: 40,
          child: Text(
            label,
            style: TextStyle(
              fontSize: 10,
              fontWeight: highlight ? FontWeight.w700 : FontWeight.w500,
              color: highlight ? color : GxColors.slate,
            ),
          ),
        ),
        const SizedBox(width: 6),
        Expanded(
          child: Container(
            height: highlight ? 8 : 6,
            decoration: BoxDecoration(
              color: GxColors.mist,
              borderRadius: BorderRadius.circular(4),
            ),
            child: FractionallySizedBox(
              alignment: Alignment.centerLeft,
              widthFactor: percent / 100,
              child: Container(
                decoration: BoxDecoration(
                  color: color,
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
            ),
          ),
        ),
        const SizedBox(width: 6),
        SizedBox(
          width: 32,
          child: Text(
            '$percent%',
            style: TextStyle(
              fontSize: 10,
              fontWeight: highlight ? FontWeight.w700 : FontWeight.w500,
              color: highlight ? color : GxColors.steel,
            ),
            textAlign: TextAlign.right,
          ),
        ),
      ],
    );
  }

  Color _categoryColor(String category) {
    switch (category) {
      case 'MECH':
        return const Color(0xFFEA580C);
      case 'ELEC':
        return GxColors.info;
      case 'TMS':
        return const Color(0xFF0D9488);
      case 'PI':
        return GxColors.success;
      case 'QI':
        return const Color(0xFF7C3AED);
      case 'SI':
        return GxColors.accent;
      default:
        return GxColors.steel;
    }
  }
}
