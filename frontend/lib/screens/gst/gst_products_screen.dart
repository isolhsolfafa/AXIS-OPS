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

      setState(() {
        _products = products;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
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

    return RefreshIndicator(
      color: GxColors.accent,
      onRefresh: _fetchProducts,
      child: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: _products.length,
        separatorBuilder: (_, __) => const SizedBox(height: 8),
        itemBuilder: (context, index) {
          final product = _products[index];
          return _buildProductCard(product);
        },
      ),
    );
  }

  Widget _buildProductCard(Map<String, dynamic> product) {
    final status = product['task_status'] as String?;
    final statusColor = _getStatusColor(status);
    final serialNumber = product['serial_number'] as String? ?? '-';
    final model = product['model'] as String? ?? '-';
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
              ],
            ),
          ),
        ),
      ),
    );
  }
}
