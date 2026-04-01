import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../utils/design_system.dart';

/// TM 전용 체크리스트 화면
///
/// TM(Tank Module) 작업 완료 후 관리자가 검수하는 체크리스트
/// 그룹별(BURNER, REACTOR, EXHAUST, TANK) ExpansionTile 구조
/// 각 항목: PASS / NA 3상태 토글 + 코멘트 입력
///
/// 진입 경로:
/// 1. complete_work 응답의 checklist_ready: true → 이동 다이얼로그
/// 2. 알림 탭 CHECKLIST_TM_READY 탭 → 해당 S/N으로 이동
/// 3. task_detail_screen TM 카테고리 완료 상태 → '체크리스트' 버튼
class TmChecklistScreen extends ConsumerStatefulWidget {
  final String serialNumber;

  const TmChecklistScreen({super.key, required this.serialNumber});

  @override
  ConsumerState<TmChecklistScreen> createState() => _TmChecklistScreenState();
}

class _TmChecklistScreenState extends ConsumerState<TmChecklistScreen> {
  bool _isLoading = false;
  String? _errorMessage;

  // 제품 헤더 정보
  String? _salesOrder;

  // 그룹별 체크리스트 데이터
  // [{group: 'BURNER', items: [{id, check_name, check_result, note, ...}]}]
  List<Map<String, dynamic>> _groups = [];

  // 현재 요청 중인 항목 ID 집합 (optimistic update 중복 방지)
  final Set<int> _updatingIds = {};

  // 그룹 접기/펼치기 상태 (기본: 모두 펼침)
  final Map<String, bool> _expanded = {};

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
        '/app/checklist/tm/${widget.serialNumber}',
      );

      String? salesOrder;
      List<Map<String, dynamic>> groups = [];

      if (response is Map<String, dynamic>) {
        salesOrder = response['sales_order'] as String?;
        final raw = response['groups'];
        if (raw is List) {
          groups = raw.cast<Map<String, dynamic>>();
        }
      }

      // 초기 expanded 상태: 처음 로드 시 모두 펼침
      final newExpanded = <String, bool>{};
      for (final g in groups) {
        final groupName = g['group'] as String? ?? '';
        newExpanded[groupName] = _expanded[groupName] ?? true;
      }

      setState(() {
        _salesOrder = salesOrder;
        _groups = groups;
        _expanded.clear();
        _expanded.addAll(newExpanded);
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  /// 총 항목 수
  int get _totalCount {
    int total = 0;
    for (final g in _groups) {
      final items = g['items'] as List? ?? [];
      total += items.length;
    }
    return total;
  }

  /// 완료(PASS + NA) 항목 수
  int get _checkedCount {
    int count = 0;
    for (final g in _groups) {
      final items = g['items'] as List? ?? [];
      for (final item in items) {
        final result = (item as Map<String, dynamic>)['check_result'] as String?;
        if (result == 'PASS' || result == 'NA') count++;
      }
    }
    return count;
  }

  double get _progress => _totalCount > 0 ? _checkedCount / _totalCount : 0;
  bool get _isAllDone => _totalCount > 0 && _checkedCount == _totalCount;

  /// PASS → NA → null 순환 토글
  String? _nextResult(String? current) {
    if (current == null) return 'PASS';
    if (current == 'PASS') return 'NA';
    return null; // NA → null (미체크)
  }

  Future<void> _toggleResult(
    Map<String, dynamic> item,
    String groupName,
  ) async {
    final masterId = item['id'] as int?;
    if (masterId == null) return;
    if (_updatingIds.contains(masterId)) return;

    final currentResult = item['check_result'] as String?;
    final nextResult = _nextResult(currentResult);

    // optimistic update
    setState(() {
      _updatingIds.add(masterId);
      _updateItemInGroups(masterId, {'check_result': nextResult});
    });

    try {
      final apiService = ref.read(apiServiceProvider);
      await apiService.put(
        '/app/checklist/tm/check',
        data: {
          'serial_number': widget.serialNumber,
          'master_id': masterId,
          'check_result': nextResult,
          'note': item['note'],
        },
      );
    } catch (e) {
      // 실패 시 롤백
      setState(() {
        _updateItemInGroups(masterId, {'check_result': currentResult});
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('업데이트 실패: $e'),
            backgroundColor: GxColors.danger,
            duration: const Duration(seconds: 2),
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(GxRadius.sm),
            ),
          ),
        );
      }
    } finally {
      setState(() {
        _updatingIds.remove(masterId);
      });
    }
  }

  /// 코멘트(note) 입력 다이얼로그
  Future<void> _showCommentDialog(Map<String, dynamic> item) async {
    final masterId = item['id'] as int?;
    if (masterId == null) return;

    final currentNote = item['note'] as String? ?? '';
    final controller = TextEditingController(text: currentNote);

    final result = await showDialog<String?>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(GxRadius.lg),
        ),
        title: const Text(
          '코멘트 입력',
          style: TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w600,
            color: GxColors.charcoal,
          ),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              item['check_name'] as String? ?? '',
              style: const TextStyle(
                fontSize: 12,
                color: GxColors.steel,
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              maxLines: 3,
              autofocus: true,
              decoration: InputDecoration(
                hintText: '이슈 내용을 입력하세요 (선택)',
                hintStyle: const TextStyle(
                  fontSize: 13,
                  color: GxColors.silver,
                ),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(GxRadius.sm),
                  borderSide: const BorderSide(color: GxColors.mist),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(GxRadius.sm),
                  borderSide: const BorderSide(color: GxColors.mist),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(GxRadius.sm),
                  borderSide:
                      const BorderSide(color: GxColors.accent, width: 1.5),
                ),
                filled: true,
                fillColor: GxColors.snow,
                contentPadding: const EdgeInsets.all(10),
              ),
              style: const TextStyle(fontSize: 13, color: GxColors.graphite),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, null),
            child: const Text(
              '취소',
              style: TextStyle(color: GxColors.steel),
            ),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, controller.text.trim()),
            child: const Text(
              '저장',
              style: TextStyle(
                color: GxColors.accent,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );

    if (result == null) return; // 취소
    if (result == currentNote) return; // 변경 없음

    // optimistic update
    setState(() {
      _updateItemInGroups(masterId, {'note': result.isEmpty ? null : result});
    });

    try {
      final apiService = ref.read(apiServiceProvider);
      await apiService.put(
        '/app/checklist/tm/check',
        data: {
          'serial_number': widget.serialNumber,
          'master_id': masterId,
          'check_result': item['check_result'],
          'note': result.isEmpty ? null : result,
        },
      );
    } catch (e) {
      // 실패 시 롤백
      setState(() {
        _updateItemInGroups(
            masterId, {'note': currentNote.isEmpty ? null : currentNote});
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('코멘트 저장 실패: $e'),
            backgroundColor: GxColors.danger,
            duration: const Duration(seconds: 2),
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(GxRadius.sm),
            ),
          ),
        );
      }
    }
  }

  /// 그룹 내 특정 항목 필드 업데이트 (불변성 유지)
  void _updateItemInGroups(int masterId, Map<String, dynamic> fields) {
    _groups = _groups.map((g) {
      final items = (g['items'] as List? ?? []).map((item) {
        final i = item as Map<String, dynamic>;
        if (i['id'] == masterId) {
          return Map<String, dynamic>.from(i)..addAll(fields);
        }
        return i;
      }).toList();
      return Map<String, dynamic>.from(g)..['items'] = items;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: GxColors.cloud,
      appBar: AppBar(
        backgroundColor: GxColors.white,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(
            Icons.arrow_back_ios,
            size: 18,
            color: GxColors.slate,
          ),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'TM 체크리스트',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: GxColors.charcoal,
              ),
            ),
            Text(
              _salesOrder != null
                  ? 'O/N: $_salesOrder  |  S/N: ${widget.serialNumber}'
                  : 'S/N: ${widget.serialNumber}',
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
              const Icon(
                Icons.error_outline,
                color: GxColors.danger,
                size: 40,
              ),
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

    if (_groups.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.checklist_outlined,
                size: 48,
                color: GxColors.silver,
              ),
              SizedBox(height: 12),
              Text(
                '등록된 TM 체크리스트가 없습니다.\n관리자에게 문의하세요.',
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
        // 전체 완료 배너
        if (_isAllDone) _buildCompletionBanner(),

        // 진행률 헤더
        _buildProgressHeader(),

        const Divider(color: GxColors.mist, height: 1),

        // 그룹별 체크리스트
        Expanded(
          child: RefreshIndicator(
            color: GxColors.accent,
            onRefresh: _fetchChecklist,
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              itemCount: _groups.length,
              itemBuilder: (context, index) {
                return _buildGroupTile(_groups[index]);
              },
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildCompletionBanner() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 16),
      color: GxColors.success,
      child: Row(
        children: [
          const Icon(Icons.check_circle, color: Colors.white, size: 18),
          const SizedBox(width: 8),
          const Expanded(
            child: Text(
              '검수 완료 — 모든 항목이 확인되었습니다.',
              style: TextStyle(
                color: Colors.white,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProgressHeader() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      color: GxColors.white,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                '진행률',
                style: TextStyle(fontSize: 12, color: GxColors.steel),
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
              color: _isAllDone ? GxColors.success : GxColors.accent,
              minHeight: 6,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGroupTile(Map<String, dynamic> group) {
    final groupName = group['group'] as String? ?? '';
    final items = (group['items'] as List? ?? [])
        .cast<Map<String, dynamic>>();
    final isExpanded = _expanded[groupName] ?? true;

    // 그룹 내 완료 항목 수
    final groupChecked = items.where((i) {
      final r = i['check_result'] as String?;
      return r == 'PASS' || r == 'NA';
    }).length;
    final groupTotal = items.length;
    final groupDone = groupTotal > 0 && groupChecked == groupTotal;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: GxColors.white,
        borderRadius: BorderRadius.circular(GxRadius.md),
        border: Border.all(color: GxColors.mist, width: 1),
      ),
      child: Theme(
        // ExpansionTile 기본 divider 제거
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          initiallyExpanded: isExpanded,
          onExpansionChanged: (expanded) {
            setState(() {
              _expanded[groupName] = expanded;
            });
          },
          tilePadding:
              const EdgeInsets.symmetric(horizontal: 14, vertical: 2),
          childrenPadding: EdgeInsets.zero,
          leading: Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: groupDone
                  ? GxColors.successBg
                  : GxColors.accentSoft,
              borderRadius: BorderRadius.circular(GxRadius.sm),
            ),
            child: Icon(
              groupDone ? Icons.check_circle : Icons.list_alt,
              size: 16,
              color: groupDone ? GxColors.success : GxColors.accent,
            ),
          ),
          title: Row(
            children: [
              Text(
                groupName,
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: GxColors.charcoal,
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                decoration: BoxDecoration(
                  color: groupDone ? GxColors.successBg : GxColors.mist,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  '$groupChecked/$groupTotal',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: groupDone ? GxColors.success : GxColors.slate,
                  ),
                ),
              ),
              if (groupDone) ...[
                const SizedBox(width: 6),
                const Icon(Icons.check, size: 14, color: GxColors.success),
              ],
            ],
          ),
          children: items.map((item) => _buildCheckItem(item)).toList(),
        ),
      ),
    );
  }

  Widget _buildCheckItem(Map<String, dynamic> item) {
    final masterId = item['id'] as int?;
    final checkName = item['check_name'] as String? ?? '-';
    final checkResult = item['check_result'] as String?;
    final note = item['note'] as String?;
    final isUpdating = masterId != null && _updatingIds.contains(masterId);

    return Container(
      decoration: const BoxDecoration(
        border: Border(
          top: BorderSide(color: GxColors.mist, width: 1),
        ),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: isUpdating ? null : () => _toggleResult(item, ''),
          onLongPress: () => _showCommentDialog(item),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            child: Row(
              children: [
                // 상태 토글 버튼
                if (isUpdating)
                  const SizedBox(
                    width: 38,
                    height: 24,
                    child: Center(
                      child: SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: GxColors.accent,
                        ),
                      ),
                    ),
                  )
                else
                  _buildResultChip(checkResult),
                const SizedBox(width: 10),
                // 항목 이름
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        checkName,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                          color: checkResult != null
                              ? GxColors.steel
                              : GxColors.graphite,
                          decoration: checkResult == 'PASS'
                              ? TextDecoration.lineThrough
                              : null,
                          decorationColor: GxColors.silver,
                        ),
                      ),
                      if (note != null && note.isNotEmpty) ...[
                        const SizedBox(height: 2),
                        Row(
                          children: [
                            const Icon(
                              Icons.comment_outlined,
                              size: 11,
                              color: GxColors.silver,
                            ),
                            const SizedBox(width: 4),
                            Expanded(
                              child: Text(
                                note,
                                style: const TextStyle(
                                  fontSize: 11,
                                  color: GxColors.silver,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
                // 코멘트 아이콘 버튼
                GestureDetector(
                  onTap: () => _showCommentDialog(item),
                  child: Padding(
                    padding: const EdgeInsets.only(left: 8),
                    child: Icon(
                      note != null && note.isNotEmpty
                          ? Icons.comment
                          : Icons.comment_outlined,
                      size: 18,
                      color: note != null && note.isNotEmpty
                          ? GxColors.accent
                          : GxColors.silver,
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

  /// PASS / NA / 미체크 상태 칩
  Widget _buildResultChip(String? result) {
    if (result == 'PASS') {
      return Container(
        width: 38,
        height: 24,
        decoration: BoxDecoration(
          color: GxColors.success,
          borderRadius: BorderRadius.circular(GxRadius.sm),
        ),
        alignment: Alignment.center,
        child: const Text(
          'PASS',
          style: TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            color: Colors.white,
          ),
        ),
      );
    } else if (result == 'NA') {
      return Container(
        width: 38,
        height: 24,
        decoration: BoxDecoration(
          color: GxColors.silver,
          borderRadius: BorderRadius.circular(GxRadius.sm),
        ),
        alignment: Alignment.center,
        child: const Text(
          'N/A',
          style: TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            color: Colors.white,
          ),
        ),
      );
    } else {
      // 미체크 상태
      return Container(
        width: 38,
        height: 24,
        decoration: BoxDecoration(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(GxRadius.sm),
          border: Border.all(color: GxColors.silver, width: 1.5),
        ),
        alignment: Alignment.center,
        child: const Text(
          '---',
          style: TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w500,
            color: GxColors.silver,
          ),
        ),
      );
    }
  }
}
