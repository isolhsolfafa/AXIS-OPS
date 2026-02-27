import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../utils/design_system.dart';

/// 체크리스트 화면
///
/// 제품 S/N과 카테고리별 체크리스트 항목을 표시 (기본: HOOKUP)
/// 항목 체크/해제 → PUT /app/checklist/check
class ChecklistScreen extends ConsumerStatefulWidget {
  final String serialNumber;
  final String category; // 기본값: HOOKUP

  const ChecklistScreen({
    super.key,
    required this.serialNumber,
    required this.category,
  });

  @override
  ConsumerState<ChecklistScreen> createState() => _ChecklistScreenState();
}

class _ChecklistScreenState extends ConsumerState<ChecklistScreen> {
  bool _isLoading = false;
  String? _errorMessage;
  List<Map<String, dynamic>> _items = [];
  // 체크 중인 항목 ID 집합
  final Set<int> _checkingIds = {};

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _fetchChecklist();
    });
  }

  Future<void> _fetchChecklist() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final apiService = ref.read(apiServiceProvider);
      final response = await apiService.get(
        '/app/checklist/${widget.serialNumber}/${widget.category}',
      );

      List<Map<String, dynamic>> items = [];
      if (response is List) {
        items = response.cast<Map<String, dynamic>>();
      } else if (response is Map && response['items'] != null) {
        items = (response['items'] as List).cast<Map<String, dynamic>>();
      }

      setState(() {
        _items = items;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _toggleCheck(Map<String, dynamic> item) async {
    final itemId = item['id'] as int?;
    if (itemId == null) return;
    if (_checkingIds.contains(itemId)) return;

    final currentChecked = item['is_checked'] as bool? ?? false;

    setState(() {
      _checkingIds.add(itemId);
      // optimistic update
      final index = _items.indexWhere((i) => i['id'] == itemId);
      if (index != -1) {
        _items[index] = Map<String, dynamic>.from(_items[index])
          ..['is_checked'] = !currentChecked;
      }
    });

    try {
      final apiService = ref.read(apiServiceProvider);
      await apiService.put(
        '/app/checklist/check',
        data: {
          'item_id': itemId,
          'is_checked': !currentChecked,
        },
      );
    } catch (e) {
      // 실패 시 롤백
      setState(() {
        final index = _items.indexWhere((i) => i['id'] == itemId);
        if (index != -1) {
          _items[index] = Map<String, dynamic>.from(_items[index])
            ..['is_checked'] = currentChecked;
        }
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('체크 업데이트 실패: $e'),
            backgroundColor: GxColors.danger,
            duration: const Duration(seconds: 2),
          ),
        );
      }
    } finally {
      setState(() {
        _checkingIds.remove(itemId);
      });
    }
  }

  int get _checkedCount => _items.where((i) => i['is_checked'] == true).length;
  int get _totalCount => _items.length;
  double get _progress => _totalCount > 0 ? _checkedCount / _totalCount : 0;

  String get _categoryLabel {
    switch (widget.category) {
      case 'HOOKUP': return 'HOOKUP';
      case 'PI': return 'PI 가압검사';
      case 'QI': return 'QI 공정검사';
      case 'SI': return 'SI 마무리공정';
      default: return widget.category;
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
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '체크리스트 — $_categoryLabel',
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: GxColors.charcoal,
              ),
            ),
            Text(
              widget.serialNumber,
              style: const TextStyle(fontSize: 11, color: GxColors.steel),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: GxColors.slate, size: 20),
            onPressed: _fetchChecklist,
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
              const Text(
                '데이터를 불러올 수 없습니다',
                style: TextStyle(
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
                onPressed: _fetchChecklist,
                child: const Text('다시 시도'),
              ),
            ],
          ),
        ),
      );
    }

    if (_items.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.checklist_outlined, size: 48, color: GxColors.silver),
              SizedBox(height: 12),
              Text(
                '등록된 체크리스트가 없습니다.\n관리자에게 문의하세요.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 14,
                  color: GxColors.steel,
                  fontWeight: FontWeight.w500,
                  height: 1.5,
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Column(
      children: [
        // 진행률 헤더
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          color: GxColors.white,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    '진행률',
                    style: const TextStyle(fontSize: 12, color: GxColors.steel),
                  ),
                  Text(
                    '$_checkedCount / $_totalCount',
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: GxColors.charcoal,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: _progress,
                  backgroundColor: GxColors.mist,
                  color: _progress >= 1.0 ? GxColors.success : GxColors.accent,
                  minHeight: 6,
                ),
              ),
            ],
          ),
        ),
        const Divider(color: GxColors.mist, height: 1),
        // 체크리스트 항목
        Expanded(
          child: RefreshIndicator(
            color: GxColors.accent,
            onRefresh: _fetchChecklist,
            child: ListView.separated(
              padding: const EdgeInsets.all(12),
              itemCount: _items.length,
              separatorBuilder: (_, __) => const SizedBox(height: 6),
              itemBuilder: (context, index) {
                return _buildChecklistItem(_items[index]);
              },
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildChecklistItem(Map<String, dynamic> item) {
    final itemId = item['id'] as int?;
    final isChecked = item['is_checked'] as bool? ?? false;
    final title = item['title'] as String? ?? item['item_name'] as String? ?? '-';
    final description = item['description'] as String?;
    final isChecking = itemId != null && _checkingIds.contains(itemId);

    return Container(
      decoration: GxGlass.cardSm(radius: GxRadius.md),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: isChecking ? null : () => _toggleCheck(item),
          borderRadius: BorderRadius.circular(GxRadius.md),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: Row(
              children: [
                // 체크박스
                if (isChecking)
                  const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: GxColors.accent,
                    ),
                  )
                else
                  Container(
                    width: 22,
                    height: 22,
                    decoration: BoxDecoration(
                      color: isChecked ? GxColors.success : Colors.transparent,
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(
                        color: isChecked ? GxColors.success : GxColors.silver,
                        width: 1.5,
                      ),
                    ),
                    child: isChecked
                        ? const Icon(Icons.check, size: 14, color: Colors.white)
                        : null,
                  ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                          color: isChecked ? GxColors.steel : GxColors.graphite,
                          decoration: isChecked ? TextDecoration.lineThrough : null,
                          decorationColor: GxColors.steel,
                        ),
                      ),
                      if (description != null && description.isNotEmpty) ...[
                        const SizedBox(height: 2),
                        Text(
                          description,
                          style: const TextStyle(fontSize: 11, color: GxColors.silver),
                        ),
                      ],
                    ],
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
