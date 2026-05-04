// Sprint 63-FE: MECH 체크리스트 화면 (mech_checklist_screen.dart)
// 등록일: 2026-05-04 KST
// 선행: Sprint 63-BE v2.11.0 + R2-1 patch v2.11.1 (tank_in_mech 응답 키 보장)
//
// 핵심 차이점 (vs ELEC):
//   1. INPUT type 입력 위젯 분기 (INLET 8 + Speed 2)
//   2. scope_rule disabled NA UI (DRAGON/GALLANT/SWS 외 모델은 13/14/19 회색)
//   3. WebSocket CHECKLIST_MECH_READY 토스트 핸들러 (alert_provider 레이어)
//   4. INLET 8개 Left/Right subgroup 시각 분리 (Q1-B)
//
// Codex 라운드 1+2+후속 정정 모두 반영:
//   - M1: phase1_applicable dead code 제거 (BE 가 이미 필터링)
//   - M2: scope_rule disabled UI 'N/A' 일관 (Q2-B)
//   - M3: judgment_phase role gate (is_manager OR is_admin, Q5-B)
//   - M4: SELECT onChanged 즉시 PUT (debounce 500ms, Q6-C)
//   - M5: INPUT + check_result 번들 PUT (Q3-B)
//   - R2-1: tank_in_mech BE 응답 활용 (FE _isScopeMatched)
//   - R2-2: _normalizeQrDocId Dart helper
//   - R2-3: _evaluateDualModel split-token 매칭 (M-R2-1+2 보강)
//   - R2-4: _checkResultMap + _getCurrentCheckResult helper
//   - R2-5: INLET Left/Right subgroup UI (_buildInletGroup)
//   - M-R2-3: _qrDocIdForItem (DRAGON+INPUT 만 hint 강제, 도면은 SINGLE-style)
//   - A4-F2: dispose() controller + timer 정리

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../utils/design_system.dart';

class MechChecklistScreen extends ConsumerStatefulWidget {
  final String serialNumber;
  final int? initialPhase;

  const MechChecklistScreen({
    super.key,
    required this.serialNumber,
    this.initialPhase,
  });

  @override
  ConsumerState<MechChecklistScreen> createState() =>
      _MechChecklistScreenState();
}

class _MechChecklistScreenState extends ConsumerState<MechChecklistScreen> {
  // ───────────────────────── State ─────────────────────────
  bool _isLoading = false;
  String? _errorMessage;

  // 제품 헤더
  String? _salesOrder;
  String? _productModel;
  bool _tankInMech = false; // R2-1: BE 응답에서 직접 받음
  bool _isDualModel = false; // R2-3: model 명에서 추론

  // Phase 토글 (1차 작업자 / 2차 관리자)
  late int _currentPhase;

  // 그룹 데이터 (group_name + items)
  List<Map<String, dynamic>> _groups = [];

  // 그룹 접기/펼치기 (기본 모두 펼침)
  final Map<String, bool> _expanded = {};

  // 진행 중 master_id (optimistic update 중복 방지)
  final Set<int> _updatingIds = {};

  // R2-4: 현재 PASS/NA 라디오 상태 (master_id → 'PASS'|'NA')
  final Map<int, String> _checkResultMap = {};

  // SELECT 드롭다운 현재 값 (master_id → option string)
  final Map<int, String> _selectValueMap = {};

  // INPUT TextField controller (master_id → controller)
  final Map<int, TextEditingController> _inputControllers = {};

  // Q6-C: debounce 500ms 타이머 (master_id 별 독립)
  final Map<int, Timer> _debounceTimers = {};

  // ───────────────────────── Lifecycle ─────────────────────────
  @override
  void initState() {
    super.initState();
    _currentPhase = widget.initialPhase ?? 1;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _fetchChecklist();
    });
  }

  @override
  void dispose() {
    // A4-F2: controller + timer 정리 (메모리 누수 방지)
    for (final t in _debounceTimers.values) {
      t.cancel();
    }
    _debounceTimers.clear();
    for (final c in _inputControllers.values) {
      c.dispose();
    }
    _inputControllers.clear();
    super.dispose();
  }

  // ───────────────────────── API ─────────────────────────
  Future<void> _fetchChecklist() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final apiService = ref.read(apiServiceProvider);
      final response = await apiService.get(
        '/app/checklist/mech/${widget.serialNumber}?phase=$_currentPhase',
      );

      String? salesOrder;
      String? model;
      bool tankInMech = false;
      List<Map<String, dynamic>> groups = [];

      if (response is Map<String, dynamic>) {
        salesOrder = response['sales_order'] as String?;
        model = response['model'] as String?;
        tankInMech = response['tank_in_mech'] as bool? ?? false; // R2-1
        final raw = response['groups'];
        if (raw is List) {
          groups = raw.cast<Map<String, dynamic>>();
        }
      }

      // 초기 expanded 상태
      final newExpanded = <String, bool>{};
      for (final g in groups) {
        final groupName = g['group_name'] as String? ?? '';
        newExpanded[groupName] = _expanded[groupName] ?? true;
      }

      // R2-4: 받은 record 의 PASS/NA 상태 _checkResultMap 에 sync
      final newCheckResultMap = <int, String>{};
      final newSelectValueMap = <int, String>{};
      for (final g in groups) {
        final items = g['items'] as List? ?? [];
        for (final item in items) {
          final mid = item['master_id'] as int?;
          if (mid == null) continue;
          final cr = item['check_result'] as String?;
          if (cr != null) newCheckResultMap[mid] = cr;
          final sv = item['selected_value'] as String?;
          if (sv != null) newSelectValueMap[mid] = sv;
          // INPUT controller 초기화 (input_value 기존 값 보존)
          final iv = item['input_value'] as String?;
          if (item['item_type'] == 'INPUT') {
            _inputControllers
                .putIfAbsent(mid, () => TextEditingController())
                .text = iv ?? '';
          }
        }
      }

      setState(() {
        _salesOrder = salesOrder;
        _productModel = model;
        _tankInMech = tankInMech;
        _isDualModel = _evaluateDualModel(model); // R2-3 (M-R2-1+2 split 매칭)
        _groups = groups;
        _expanded
          ..clear()
          ..addAll(newExpanded);
        _checkResultMap
          ..clear()
          ..addAll(newCheckResultMap);
        _selectValueMap
          ..clear()
          ..addAll(newSelectValueMap);
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  void _switchPhase(int phase) {
    if (_currentPhase == phase) return;
    setState(() {
      _currentPhase = phase;
      _expanded.clear();
    });
    _fetchChecklist();
  }

  // ───────────────────────── Helpers ─────────────────────────

  /// R2-3 (M-R2-1+2 보강): split-token 매칭으로 'DUAL-300' false-positive 차단
  bool _evaluateDualModel(String? model) {
    if (model == null) return false;
    final tokens = model.toUpperCase().split(RegExp(r'[\s\-]'));
    return tokens.contains('DUAL');
  }

  /// scope_rule 매칭 검사 (BE _resolve_active_master_ids 로직 정합)
  bool _isScopeMatched(String? scopeRule) {
    if (scopeRule == null || scopeRule == 'all') return true;
    if (scopeRule == 'tank_in_mech') return _tankInMech;
    // 직접 모델 매칭 (예: scope_rule='DRAGON')
    return _productModel?.toUpperCase().startsWith(scopeRule.toUpperCase()) ??
        false;
  }

  /// R2-2: qr_doc_id 정규화 (BE _normalize_qr_doc_id Dart 변환)
  String _normalizeQrDocId(String sn, {String? hint}) {
    if (sn.isEmpty) return '';
    final s = sn.trim();
    if (hint != null && hint.startsWith('DOC_$s')) return hint.trim();
    if (hint != null && (hint.toUpperCase() == 'L' || hint.toUpperCase() == 'R')) {
      return 'DOC_$s-${hint.toUpperCase()}';
    }
    return 'DOC_$s';
  }

  /// M-R2-3: master 의 scope+item_type 보고 hint 강제 여부 결정
  /// DRAGON+INPUT (DUAL INLET S/N 8개) 만 hint 강제, 도면 등은 SINGLE-style fallback
  String _qrDocIdForItem(Map<String, dynamic> item, {String? lrHint}) {
    final scopeRule = item['scope_rule'] as String?;
    final itemType = item['item_type'] as String?;
    final requiresLrHint =
        (scopeRule == 'DRAGON' && itemType == 'INPUT' && _isDualModel);
    if (requiresLrHint && (lrHint == null || lrHint.isEmpty)) {
      // 호출자 측 책임 — INLET S/N 입력 시 item_name 에서 'L'/'R' 추출 필수
      final name = (item['item_name'] as String? ?? '').toUpperCase();
      if (name.contains('LEFT')) {
        lrHint = 'L';
      } else if (name.contains('RIGHT')) {
        lrHint = 'R';
      } else {
        throw ArgumentError(
            'DUAL INLET S/N requires hint L/R (master_id=${item['master_id']})');
      }
    }
    return _normalizeQrDocId(widget.serialNumber, hint: lrHint);
  }

  /// R2-4: 현재 PASS/NA 상태 lookup
  String _getCurrentCheckResult(int masterId) {
    return _checkResultMap[masterId] ?? '';
  }

  // ───────────────────────── Upsert (Q6-C debounce 500ms) ─────────────────────────

  /// Q6-C: 모든 입력 (CHECK / SELECT / INPUT) 공통 debounce + 번들 PUT helper
  void _debouncedUpsert({
    required Map<String, dynamic> item,
    String? checkResult,
    String? selectedValue,
    String? inputValue,
    String? note,
  }) {
    final masterId = item['master_id'] as int?;
    if (masterId == null) return;

    // 기존 타이머 취소
    _debounceTimers[masterId]?.cancel();
    _debounceTimers[masterId] = Timer(const Duration(milliseconds: 500), () {
      _upsertNow(
        item: item,
        checkResult: checkResult,
        selectedValue: selectedValue,
        inputValue: inputValue,
        note: note,
      );
    });
  }

  Future<void> _upsertNow({
    required Map<String, dynamic> item,
    String? checkResult,
    String? selectedValue,
    String? inputValue,
    String? note,
  }) async {
    final masterId = item['master_id'] as int?;
    if (masterId == null) return;

    // ⭐ v2.11.3 Fix R1 (Root cause 1, ELEC _toggleResult 패턴 정합):
    //   BE upsert_mech_check 는 check_result 'PASS'/'NA' 만 허용 (None 거부, 400).
    //   PASS/NA 미선택 시 PUT skip — 사용자가 라디오 클릭 시점에 input/select+check_result 번들 PUT.
    final cr = checkResult ?? _getCurrentCheckResult(masterId);
    if (cr.isEmpty) {
      // INPUT/SELECT 만 입력 + PASS/NA 미선택 = state 갱신만 (PUT skip, 라디오 클릭 시점에 번들 PUT)
      return;
    }

    if (_updatingIds.contains(masterId)) return;
    setState(() => _updatingIds.add(masterId));

    try {
      final apiService = ref.read(apiServiceProvider);
      // M5 + Q3-B: input_value/selected_value + check_result 번들 PUT (BE upsert_mech_check 정합)
      final qrDocId = _qrDocIdForItem(item);

      final putData = <String, dynamic>{
        'serial_number': widget.serialNumber,
        'master_id': masterId,
        'check_result': cr,  // ⭐ v2.11.3: null 제거, 항상 'PASS' 또는 'NA' (위 cr.isEmpty 가드)
        'judgment_phase': _currentPhase,
        'qr_doc_id': qrDocId,
      };
      if (selectedValue != null) putData['selected_value'] = selectedValue;
      if (inputValue != null) putData['input_value'] = inputValue;
      if (note != null) putData['note'] = note;

      await apiService.put('/app/checklist/mech/check', data: putData);

      // 응답 후 fetchChecklist 호출 안 함 (낙관적 갱신 + 새로고침 시 동기화)
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('저장 실패: $e'),
            backgroundColor: GxColors.danger,
            duration: const Duration(seconds: 2),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _updatingIds.remove(masterId));
      }
    }
  }

  // ───────────────────────── Build ─────────────────────────
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: GxColors.cloud,
      appBar: AppBar(
        backgroundColor: GxColors.white,
        elevation: 0,
        title: Text(
          '기구 체크리스트 — ${widget.serialNumber}',
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        actions: [_buildPhaseToggle()],
      ),
      body: _buildBody(),
    );
  }

  /// M3 + Q5-B: role gate — is_manager 또는 is_admin 만 2차 토글 노출
  Widget _buildPhaseToggle() {
    // ELEC 패턴 정합: ref.watch(authProvider).currentWorker
    final authState = ref.watch(authProvider);
    final worker = authState.currentWorker;
    final canAccessPhase2 =
        (worker?.isManager ?? false) || (worker?.isAdmin ?? false);

    if (!canAccessPhase2) {
      // 작업자 — 1차 고정 (토글 비표시, 권한 위반 차단)
      return const Padding(
        padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Center(
          child: Text(
            '1차 (작업자)',
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
          ),
        ),
      );
    }

    // is_manager / is_admin — 1차/2차 토글 노출
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _phaseChip(1, '1차'),
          const SizedBox(width: 4),
          _phaseChip(2, '2차'),
        ],
      ),
    );
  }

  Widget _phaseChip(int phase, String label) {
    final isSelected = _currentPhase == phase;
    return InkWell(
      onTap: () => _switchPhase(phase),
      borderRadius: BorderRadius.circular(GxRadius.sm),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? GxColors.accent : GxColors.white,
          borderRadius: BorderRadius.circular(GxRadius.sm),
          border: Border.all(
            color: isSelected ? GxColors.accent : GxColors.mist,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: isSelected ? Colors.white : GxColors.steel,
          ),
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            '체크리스트 로드 실패\n$_errorMessage',
            textAlign: TextAlign.center,
            style: TextStyle(color: GxColors.danger),
          ),
        ),
      );
    }
    if (_groups.isEmpty) {
      return const Center(child: Text('체크리스트 항목이 없습니다'));
    }

    return RefreshIndicator(
      onRefresh: _fetchChecklist,
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(vertical: 8),
        itemCount: _groups.length + 1, // +1: header
        itemBuilder: (context, index) {
          if (index == 0) return _buildHeader();
          final group = _groups[index - 1];
          final groupName = group['group_name'] as String? ?? '';
          // R2-5: INLET 만 Left/Right subgroup 분리, 나머지는 일반
          if (groupName == 'INLET') return _buildInletGroup(group);
          return _buildStandardGroup(group);
        },
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: GxColors.white,
        borderRadius: BorderRadius.circular(GxRadius.md),
      ),
      child: Row(
        children: [
          const Icon(Icons.info_outline, size: 18, color: GxColors.steel),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              '${_salesOrder ?? "—"} · ${_productModel ?? "—"}'
              '${_tankInMech ? " · Tank Ass'y 적용" : ""}'
              '${_isDualModel ? " · DUAL" : ""}',
              style: const TextStyle(fontSize: 12, color: GxColors.steel),
            ),
          ),
        ],
      ),
    );
  }

  /// R2-5 (Q1-B): INLET Left/Right subgroup 시각 분리
  Widget _buildInletGroup(Map<String, dynamic> group) {
    final groupName = group['group_name'] as String? ?? 'INLET';
    final items = (group['items'] as List? ?? []).cast<Map<String, dynamic>>();

    final designItems =
        items.where((i) => i['item_type'] == 'CHECK').toList(); // 도면 1개
    final leftItems = items
        .where((i) =>
            i['item_type'] == 'INPUT' &&
            (i['item_name'] as String? ?? '').toUpperCase().contains('LEFT'))
        .toList();
    final rightItems = items
        .where((i) =>
            i['item_type'] == 'INPUT' &&
            (i['item_name'] as String? ?? '').toUpperCase().contains('RIGHT'))
        .toList();

    final isExpanded = _expanded[groupName] ?? true;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      decoration: BoxDecoration(
        color: GxColors.white,
        borderRadius: BorderRadius.circular(GxRadius.md),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _groupHeader(groupName, items.length, isExpanded),
          if (isExpanded) ...[
            ...designItems.map((item) => _buildItem(item)),
            if (leftItems.isNotEmpty) ...[
              _subgroupHeader('Left 측 배관 (#1 ~ #4)'),
              ...leftItems.map((item) => _buildItem(item)),
            ],
            if (rightItems.isNotEmpty) ...[
              _subgroupHeader('Right 측 배관 (#1 ~ #4)'),
              ...rightItems.map((item) => _buildItem(item)),
            ],
          ],
        ],
      ),
    );
  }

  Widget _buildStandardGroup(Map<String, dynamic> group) {
    final groupName = group['group_name'] as String? ?? '';
    final items = (group['items'] as List? ?? []).cast<Map<String, dynamic>>();
    final isExpanded = _expanded[groupName] ?? true;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      decoration: BoxDecoration(
        color: GxColors.white,
        borderRadius: BorderRadius.circular(GxRadius.md),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _groupHeader(groupName, items.length, isExpanded),
          if (isExpanded) ...items.map((item) => _buildItem(item)),
        ],
      ),
    );
  }

  Widget _groupHeader(String name, int count, bool isExpanded) {
    return InkWell(
      onTap: () {
        setState(() => _expanded[name] = !isExpanded);
      },
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: Row(
          children: [
            Icon(
              isExpanded ? Icons.expand_less : Icons.expand_more,
              size: 20,
              color: GxColors.steel,
            ),
            const SizedBox(width: 6),
            Text(
              name,
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: GxColors.charcoal,
              ),
            ),
            const SizedBox(width: 8),
            Text(
              '($count)',
              style: const TextStyle(fontSize: 11, color: GxColors.steel),
            ),
          ],
        ),
      ),
    );
  }

  Widget _subgroupHeader(String label) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 8, 14, 4),
      child: Text(
        label,
        style: const TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: GxColors.steel,
        ),
      ),
    );
  }

  /// 항목 위젯 분기 — scope/item_type
  /// (M1 정정: BE 가 phase=1 시 phase1_applicable=False 자동 필터링 → FE 분기 dead code 제거)
  Widget _buildItem(Map<String, dynamic> item) {
    final scopeRule = item['scope_rule'] as String?;
    if (!_isScopeMatched(scopeRule)) {
      // M2: scope_rule 비매칭 → disabled 'N/A' UI (Q2-B)
      return _buildScopeDisabledNA(item);
    }
    final itemType = item['item_type'] as String? ?? 'CHECK';
    switch (itemType) {
      case 'CHECK':
        return _buildCheckRadio(item);
      case 'SELECT':
        return _buildSelectDropdown(item);
      case 'INPUT':
        return _buildInputField(item);
      default:
        return _buildCheckRadio(item);
    }
  }

  /// M2 + Q2-B: scope_rule 비매칭 모델 — disabled 'N/A' 일관 표시
  Widget _buildScopeDisabledNA(Map<String, dynamic> item) {
    return Container(
      color: GxColors.cloud,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      child: Row(
        children: [
          const Icon(Icons.block, size: 14, color: GxColors.silver),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              item['item_name'] as String? ?? '',
              style: const TextStyle(
                color: GxColors.silver,
                decoration: TextDecoration.lineThrough,
                fontSize: 13,
              ),
            ),
          ),
          const Text(
            'N/A',
            style: TextStyle(fontSize: 11, color: GxColors.silver),
          ),
        ],
      ),
    );
  }

  /// CHECK type — PASS/NA 라디오
  Widget _buildCheckRadio(Map<String, dynamic> item) {
    final masterId = item['master_id'] as int?;
    if (masterId == null) return const SizedBox.shrink();
    final currentResult = _checkResultMap[masterId];

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      child: Row(
        children: [
          Expanded(
            child: Text(
              item['item_name'] as String? ?? '',
              style: const TextStyle(fontSize: 13),
            ),
          ),
          _resultRadio(item, 'PASS', currentResult),
          const SizedBox(width: 8),
          _resultRadio(item, 'NA', currentResult),
          if (_updatingIds.contains(masterId)) ...[
            const SizedBox(width: 8),
            const SizedBox(
              width: 12,
              height: 12,
              child: CircularProgressIndicator(strokeWidth: 1.5),
            ),
          ],
        ],
      ),
    );
  }

  Widget _resultRadio(
    Map<String, dynamic> item,
    String value,
    String? currentResult,
  ) {
    final isSelected = currentResult == value;
    final masterId = item['master_id'] as int?;
    return InkWell(
      onTap: masterId == null
          ? null
          : () {
              setState(() => _checkResultMap[masterId] = value);
              // M5: PASS/NA 라디오 변경 시 번들 PUT (현재 input_value / selected_value 동시 전송)
              _debouncedUpsert(
                item: item,
                checkResult: value,
                inputValue: _inputControllers[masterId]?.text,
                selectedValue: _selectValueMap[masterId],
              );
            },
      borderRadius: BorderRadius.circular(GxRadius.sm),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: isSelected
              ? (value == 'PASS' ? GxColors.success : GxColors.warning)
              : GxColors.white,
          borderRadius: BorderRadius.circular(GxRadius.sm),
          border: Border.all(
            color: isSelected
                ? (value == 'PASS' ? GxColors.success : GxColors.warning)
                : GxColors.mist,
          ),
        ),
        child: Text(
          value,
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w600,
            color: isSelected ? Colors.white : GxColors.steel,
          ),
        ),
      ),
    );
  }

  /// SELECT type — 드롭다운 (MFC / Flow Sensor)
  /// M4: onChanged 즉시 PUT (debounce 500ms)
  /// Q7-B: select_options 빈 master 시 '운영자 미설정 안내'
  Widget _buildSelectDropdown(Map<String, dynamic> item) {
    final masterId = item['master_id'] as int?;
    if (masterId == null) return const SizedBox.shrink();
    final options = ((item['select_options'] as List?) ?? []).cast<String>();

    if (options.isEmpty) {
      // Q7-B
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Row(
          children: [
            Expanded(
              child: Text(
                item['item_name'] as String? ?? '',
                style: const TextStyle(fontSize: 13),
              ),
            ),
            const Text(
              '운영자가 옵션을 설정하지 않았습니다',
              style: TextStyle(fontSize: 10, color: GxColors.warning),
            ),
          ],
        ),
      );
    }

    final currentValue = _selectValueMap[masterId];
    final currentResult = _checkResultMap[masterId];
    final isPhase2 = _currentPhase == 2;  // ⭐ v2.11.3 R2

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            item['item_name'] as String? ?? '',
            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
          ),
          const SizedBox(height: 6),
          DropdownButtonFormField<String>(
            value: options.contains(currentValue) ? currentValue : null,
            isExpanded: true,
            decoration: InputDecoration(
              border: const OutlineInputBorder(),
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              isDense: true,
              fillColor: isPhase2 ? GxColors.cloud : null,  // ⭐ v2.11.3 R2: 회색 배경
              filled: isPhase2,
            ),
            items: options
                .map((opt) => DropdownMenuItem(
                      value: opt,
                      child: Text(opt, overflow: TextOverflow.ellipsis),
                    ))
                .toList(),
            onChanged: isPhase2 ? null : (value) {  // ⭐ v2.11.3 R2: 2차 disabled
              if (value == null) return;
              setState(() => _selectValueMap[masterId] = value);
              // M4 + Q6-C: debounce + 번들 PUT (1차만)
              _debouncedUpsert(
                item: item,
                selectedValue: value,
                checkResult: _getCurrentCheckResult(masterId),
              );
            },
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              _resultRadio(item, 'PASS', currentResult),
              const SizedBox(width: 6),
              _resultRadio(item, 'NA', currentResult),
            ],
          ),
        ],
      ),
    );
  }

  /// INPUT type — TextField (INLET S/N + Speed Controller 수량)
  /// M5: 입력값 + check_result 번들 PUT
  /// v2.11.3 Fix R2: phase=2 시 readOnly + 회색 배경 (1차 입력값 read-only 표시)
  Widget _buildInputField(Map<String, dynamic> item) {
    final masterId = item['master_id'] as int?;
    if (masterId == null) return const SizedBox.shrink();
    final controller = _inputControllers.putIfAbsent(
      masterId,
      () => TextEditingController(text: item['input_value'] as String? ?? ''),
    );
    final currentResult = _checkResultMap[masterId];
    final isPhase2 = _currentPhase == 2;  // ⭐ v2.11.3 R2

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            item['item_name'] as String? ?? '',
            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
          ),
          const SizedBox(height: 6),
          TextField(
            controller: controller,
            readOnly: isPhase2,  // ⭐ v2.11.3 R2: 2차 검사인원 = 1차 입력값 read-only
            decoration: InputDecoration(
              hintText: 'S/N 또는 수량 입력',
              border: const OutlineInputBorder(),
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              isDense: true,
              fillColor: isPhase2 ? GxColors.cloud : null,  // ⭐ v2.11.3 R2: 회색 배경
              filled: isPhase2,
            ),
            onChanged: isPhase2 ? null : (value) {
              // M4 + M5 + Q6-C: debounce 500ms + check_result 번들 PUT (1차만)
              _debouncedUpsert(
                item: item,
                inputValue: value,
                checkResult: _getCurrentCheckResult(masterId),
              );
            },
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              _resultRadio(item, 'PASS', currentResult),
              const SizedBox(width: 6),
              _resultRadio(item, 'NA', currentResult),
            ],
          ),
        ],
      ),
    );
  }
}
