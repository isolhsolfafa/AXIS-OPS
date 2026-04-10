import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../utils/design_system.dart';

/// ELEC 전용 체크리스트 화면
///
/// ELEC(전장) 작업 완료 후 검수하는 체크리스트
/// Phase 탭: 1차 배선 / 2차 배선 전환
/// 그룹별 ExpansionTile 구조
/// 각 항목: PASS / NA 2상태 토글 + 코멘트 입력
/// checker_role == 'QI' → GST 담당 전용 (일반 사용자 터치 불가)
/// phase1_na == true && phase==1 → "N.A (1차 해당없음)" 고정
class ElecChecklistScreen extends ConsumerStatefulWidget {
  final String serialNumber;
  final int? initialPhase;

  const ElecChecklistScreen({super.key, required this.serialNumber, this.initialPhase});

  @override
  ConsumerState<ElecChecklistScreen> createState() =>
      _ElecChecklistScreenState();
}

class _ElecChecklistScreenState extends ConsumerState<ElecChecklistScreen> {
  bool _isLoading = false;
  String? _errorMessage;

  // 제품 헤더 정보
  String? _salesOrder;

  // 현재 선택된 Phase (1 또는 2)
  late int _currentPhase;

  // 그룹별 체크리스트 데이터
  List<Map<String, dynamic>> _groups = [];

  // 현재 요청 중인 항목 ID 집합 (optimistic update 중복 방지)
  final Set<int> _updatingIds = {};

  // 그룹 접기/펼치기 상태 (기본: 모두 펼침)
  final Map<String, bool> _expanded = {};

  @override
  void initState() {
    super.initState();
    _currentPhase = widget.initialPhase ?? 1;
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
        '/app/checklist/elec/${widget.serialNumber}?phase=$_currentPhase',
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
        final groupName = g['group_name'] as String? ?? '';
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

  /// Phase 전환
  void _switchPhase(int phase) {
    if (_currentPhase == phase) return;
    setState(() {
      _currentPhase = phase;
      _expanded.clear();
    });
    _fetchChecklist();
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
        final result =
            (item as Map<String, dynamic>)['check_result'] as String?;
        if (result == 'PASS' || result == 'NA') count++;
      }
    }
    return count;
  }

  double get _progress => _totalCount > 0 ? _checkedCount / _totalCount : 0;
  bool get _isAllDone => _totalCount > 0 && _checkedCount == _totalCount;

  /// PASS → NA → PASS 순환 토글 (2상태 루프)
  String _nextResult(String? current) {
    if (current == 'PASS') return 'NA';
    return 'PASS';
  }

  /// 항목이 QI 전용이고 현재 사용자가 QI가 아닌 경우 차단
  bool _isQiBlocked(Map<String, dynamic> item) {
    if (item['checker_role'] != 'QI') return false;
    final authState = ref.read(authProvider);
    final worker = authState.currentWorker;
    if (worker == null) return true;
    final role = worker.role;
    return role != 'QI';
  }

  /// 항목이 Phase 1 N.A인지 확인
  bool _isPhase1Na(Map<String, dynamic> item) {
    return item['phase1_na'] == true && _currentPhase == 1;
  }

  Future<void> _toggleResult(
    Map<String, dynamic> item,
    String groupName,
  ) async {
    // QI 전용 항목 차단
    if (_isQiBlocked(item)) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('GST QI 인원만 체크 가능합니다'),
            backgroundColor: GxColors.warning,
            duration: const Duration(seconds: 2),
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(GxRadius.sm),
            ),
          ),
        );
      }
      return;
    }

    // Phase 1 N.A 항목 차단
    if (_isPhase1Na(item)) return;

    final masterId = item['master_id'] as int?;
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
      final putData = <String, dynamic>{
        'serial_number': widget.serialNumber,
        'master_id': masterId,
        'check_result': nextResult,
        'note': item['note'],
        'judgment_phase': _currentPhase,
      };
      if (item['selected_value'] != null) {
        putData['selected_value'] = item['selected_value'];
      }
      await apiService.put(
        '/app/checklist/elec/check',
        data: putData,
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
    // QI 전용 또는 Phase1 NA 항목은 코멘트도 차단
    if (_isQiBlocked(item) || _isPhase1Na(item)) return;

    final masterId = item['master_id'] as int?;
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
              item['item_name'] as String? ?? '',
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
        '/app/checklist/elec/check',
        data: {
          'serial_number': widget.serialNumber,
          'master_id': masterId,
          'check_result': item['check_result'],
          'note': result.isEmpty ? null : result,
          'judgment_phase': _currentPhase,
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
        if (i['master_id'] == masterId) {
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
              'ELEC 체크리스트',
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
      return Column(
        children: [
          // Phase 탭은 빈 상태에서도 표시
          _buildPhaseTab(),
          const Expanded(
            child: Center(
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
                      '등록된 ELEC 체크리스트가 없습니다.\n관리자에게 문의하세요.',
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
            ),
          ),
        ],
      );
    }

    return Column(
      children: [
        // Phase 탭
        _buildPhaseTab(),

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

  /// Phase 전환 탭 (1차 배선 / 2차 배선)
  Widget _buildPhaseTab() {
    return Container(
      color: GxColors.white,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          Expanded(
            child: _buildPhaseButton(
              phase: 1,
              label: '1차 배선',
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _buildPhaseButton(
              phase: 2,
              label: '2차 배선',
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPhaseButton({required int phase, required String label}) {
    final isSelected = _currentPhase == phase;
    return GestureDetector(
      onTap: () => _switchPhase(phase),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: isSelected ? GxColors.accent : Colors.transparent,
          borderRadius: BorderRadius.circular(GxRadius.sm),
          border: Border.all(
            color: isSelected ? GxColors.accent : GxColors.mist,
            width: 1.5,
          ),
        ),
        alignment: Alignment.center,
        child: Text(
          label,
          style: TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w600,
            color: isSelected ? Colors.white : GxColors.steel,
          ),
        ),
      ),
    );
  }

  Widget _buildCompletionBanner() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 16),
      color: GxColors.success,
      child: const Row(
        children: [
          Icon(Icons.check_circle, color: Colors.white, size: 18),
          SizedBox(width: 8),
          Expanded(
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
    final groupName = group['group_name'] as String? ?? '';
    final items =
        (group['items'] as List? ?? []).cast<Map<String, dynamic>>();
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
              color: groupDone ? GxColors.successBg : GxColors.accentSoft,
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
    final masterId = item['master_id'] as int?;
    final checkName = item['item_name'] as String? ?? '-';
    final checkResult = item['check_result'] as String?;
    final note = item['note'] as String?;
    final description = item['description'] as String?;
    final isUpdating = masterId != null && _updatingIds.contains(masterId);
    final isQi = _isQiBlocked(item);
    final isNa = _isPhase1Na(item);
    final itemType = item['item_type'] as String?;
    final selectOptions = item['select_options'] as List?;
    final selectedValue = item['selected_value'] as String?;

    // Phase 1 N.A 항목 — 고정 표시
    if (isNa) {
      return Container(
        decoration: const BoxDecoration(
          border: Border(
            top: BorderSide(color: GxColors.mist, width: 1),
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          child: Row(
            children: [
              Container(
                width: 38,
                height: 24,
                decoration: BoxDecoration(
                  color: GxColors.mist,
                  borderRadius: BorderRadius.circular(GxRadius.sm),
                ),
                alignment: Alignment.center,
                child: const Text(
                  'N/A',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: GxColors.steel,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      checkName,
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                        color: GxColors.silver,
                      ),
                    ),
                    const SizedBox(height: 2),
                    const Text(
                      'N.A (1차 해당없음)',
                      style: TextStyle(
                        fontSize: 11,
                        color: GxColors.silver,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Container(
      decoration: BoxDecoration(
        color: isQi ? GxColors.cloud : Colors.transparent,
        border: const Border(
          top: BorderSide(color: GxColors.mist, width: 1),
        ),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: isUpdating ? null : () => _toggleResult(item, ''),
          onLongPress:
              (isQi || isUpdating) ? null : () => _showCommentDialog(item),
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
                // 항목 이름 + QI 뱃지
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Flexible(
                            child: Text(
                              checkName,
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w500,
                                color: isQi
                                    ? GxColors.steel
                                    : (checkResult != null
                                        ? GxColors.steel
                                        : GxColors.graphite),
                                decoration: checkResult == 'PASS'
                                    ? TextDecoration.lineThrough
                                    : null,
                                decorationColor: GxColors.silver,
                              ),
                            ),
                          ),
                          if (isQi) ...[
                            const SizedBox(width: 6),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 5, vertical: 1),
                              decoration: BoxDecoration(
                                color: GxColors.slate,
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: const Text(
                                'GST 담당',
                                style: TextStyle(
                                  fontSize: 9,
                                  fontWeight: FontWeight.w600,
                                  color: Colors.white,
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                      if (description != null && description.isNotEmpty) ...[
                        const SizedBox(height: 2),
                        Text(
                          description,
                          style: const TextStyle(
                            fontSize: 10,
                            color: GxColors.silver,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                      // SELECT 타입: 드롭다운 옵션 표시
                      if (itemType == 'SELECT' &&
                          selectOptions != null &&
                          selectOptions.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Container(
                          height: 32,
                          padding: const EdgeInsets.symmetric(horizontal: 8),
                          decoration: BoxDecoration(
                            color: GxColors.snow,
                            borderRadius:
                                BorderRadius.circular(GxRadius.sm),
                            border:
                                Border.all(color: GxColors.mist, width: 1),
                          ),
                          child: DropdownButton<String>(
                            value: selectedValue,
                            isExpanded: true,
                            underline: const SizedBox.shrink(),
                            hint: const Text(
                              '선택하세요',
                              style: TextStyle(
                                fontSize: 12,
                                color: GxColors.silver,
                              ),
                            ),
                            style: const TextStyle(
                              fontSize: 12,
                              color: GxColors.graphite,
                            ),
                            icon: const Icon(
                              Icons.arrow_drop_down,
                              size: 18,
                              color: GxColors.steel,
                            ),
                            items: selectOptions
                                .map((opt) => DropdownMenuItem<String>(
                                      value: opt.toString(),
                                      child: Text(opt.toString()),
                                    ))
                                .toList(),
                            onChanged: (isQi || isUpdating)
                                ? null
                                : (value) {
                                    if (value == null) return;
                                    setState(() {
                                      _updateItemInGroups(
                                        masterId!,
                                        {'selected_value': value},
                                      );
                                    });
                                  },
                          ),
                        ),
                      ],
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
                // 코멘트 아이콘 버튼 (QI 항목은 숨김)
                if (!isQi)
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
