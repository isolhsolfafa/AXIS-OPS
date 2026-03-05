import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../utils/design_system.dart';

/// Admin 옵션 화면
///
/// 기능:
/// 1. admin_settings 토글 (heating_jacket, phase_block)
/// 2. 협력사 관리자 지정/해제 (is_manager 토글, company 필터)
/// 3. 미종료 작업 목록 + 강제 종료
/// 4. 근무시간 설정 (휴게시간/점심/저녁 시간대 설정)
class AdminOptionsScreen extends ConsumerStatefulWidget {
  const AdminOptionsScreen({super.key});

  @override
  ConsumerState<AdminOptionsScreen> createState() => _AdminOptionsScreenState();
}

class _AdminOptionsScreenState extends ConsumerState<AdminOptionsScreen> {
  // admin_settings 상태
  bool _heatingJacketEnabled = false;
  bool _phaseBlockEnabled = false;
  bool _locationQrRequired = true; // Location QR 필수 여부 (기본: true)
  bool _isLoadingSettings = false;

  // 위치 보안 설정 (Sprint 19-D)
  bool _geolocationEnabled = false;
  bool _geoStrictMode = false;
  String _geoLat = '';
  String _geoLng = '';
  double _geoRadiusMeters = 500.0;

  // 위치 반경 옵션 (미터 단위)
  static const List<double> _radiusOptions = [100, 200, 300, 500, 1000, 2000];

  // lat/lng TextField 컨트롤러
  final TextEditingController _geoLatController = TextEditingController();
  final TextEditingController _geoLngController = TextEditingController();

  // 근무시간 설정 상태
  bool _autoPauseEnabled = false;
  String _breakMorningStart = '10:00';
  String _breakMorningEnd = '10:10';
  String _lunchStart = '12:00';
  String _lunchEnd = '13:00';
  String _breakAfternoonStart = '15:00';
  String _breakAfternoonEnd = '15:10';
  String _dinnerStart = '18:00';
  String _dinnerEnd = '19:00';

  // 협력사 관리자 목록
  List<Map<String, dynamic>> _managers = [];
  bool _isLoadingManagers = false;
  String? _selectedManagerCompany; // 필터

  // 가입 승인 대기 목록
  List<Map<String, dynamic>> _pendingWorkers = [];
  bool _isLoadingPendingWorkers = false;
  String? _selectedPendingCompany; // 가입 승인 대기 필터 (기본: 본인 company)

  // 미종료 작업 목록
  List<Map<String, dynamic>> _pendingTasks = [];
  bool _isLoadingTasks = false;

  static const List<String> _companies = [
    'FNI', 'BAT', 'TMS(M)', 'TMS(E)', 'P&S', 'C&A', 'GST',
  ];

  /// company 필터 적용된 가입 대기 목록
  List<Map<String, dynamic>> get _filteredPendingWorkers {
    if (_selectedPendingCompany == null) return _pendingWorkers;
    return _pendingWorkers.where((w) {
      final company = w['company'] as String? ?? '';
      return company == _selectedPendingCompany;
    }).toList();
  }

  @override
  void initState() {
    super.initState();
    // 가입 승인 대기: 기본 "전체" (null)
    // 협력사 관리자 목록: 첫 번째 company로 기본 필터
    _selectedManagerCompany = _companies.first; // FNI
    _loadAll();
  }

  @override
  void dispose() {
    _geoLatController.dispose();
    _geoLngController.dispose();
    super.dispose();
  }

  Future<void> _loadAll() async {
    await Future.wait([
      _loadSettings(),
      _loadManagers(),
      _loadPendingTasks(),
      _loadPendingWorkers(),
    ]);
  }

  /// 근무시간 설정값 업데이트 (PUT /admin/settings)
  Future<void> _updateBreakTimeSetting(String key, String value) async {
    try {
      final apiService = ref.read(apiServiceProvider);
      await apiService.put('/admin/settings', data: {key: value});
      if (mounted) {
        _showSnack('설정이 저장되었습니다.', isError: false);
      }
    } catch (e) {
      if (mounted) _showSnack('설정 저장에 실패했습니다.', isError: true);
    }
  }

  /// TimeOfDay를 HH:MM 문자열로 변환
  String _formatTime(TimeOfDay time) {
    final hh = time.hour.toString().padLeft(2, '0');
    final mm = time.minute.toString().padLeft(2, '0');
    return '$hh:$mm';
  }

  /// HH:MM 문자열을 TimeOfDay로 변환
  TimeOfDay _parseTime(String value) {
    final parts = value.split(':');
    if (parts.length == 2) {
      final h = int.tryParse(parts[0]) ?? 0;
      final m = int.tryParse(parts[1]) ?? 0;
      return TimeOfDay(hour: h, minute: m);
    }
    return const TimeOfDay(hour: 0, minute: 0);
  }

  /// 시간 선택 다이얼로그 → 즉시 PUT 저장
  Future<void> _pickTime({
    required String label,
    required String currentValue,
    required String settingKey,
    required void Function(String) onSaved,
  }) async {
    final picked = await showTimePicker(
      context: context,
      initialTime: _parseTime(currentValue),
      helpText: label,
      builder: (ctx, child) => MediaQuery(
        data: MediaQuery.of(ctx).copyWith(alwaysUse24HourFormat: true),
        child: child!,
      ),
    );
    if (picked != null && mounted) {
      final formatted = _formatTime(picked);
      setState(() => onSaved(formatted));
      await _updateBreakTimeSetting(settingKey, formatted);
    }
  }

  Future<void> _loadPendingWorkers() async {
    setState(() => _isLoadingPendingWorkers = true);
    try {
      final apiService = ref.read(apiServiceProvider);
      final response = await apiService.get('/admin/workers/pending');
      if (mounted) {
        setState(() {
          _pendingWorkers = List<Map<String, dynamic>>.from(response['workers'] as List? ?? []);
          _isLoadingPendingWorkers = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _isLoadingPendingWorkers = false);
    }
  }

  Future<void> _approveWorker(int workerId, bool approved) async {
    final action = approved ? '승인' : '거부';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.lg)),
        title: Text('가입 $action', style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
        content: Text('이 작업자를 ${action}하시겠습니까?', style: const TextStyle(fontSize: 13, color: GxColors.slate)),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('취소', style: TextStyle(color: GxColors.steel)),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: ElevatedButton.styleFrom(
              backgroundColor: approved ? GxColors.success : GxColors.danger,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
            ),
            child: Text(action, style: const TextStyle(fontSize: 13)),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      final apiService = ref.read(apiServiceProvider);
      await apiService.post('/admin/workers/approve', data: {
        'worker_id': workerId,
        'approved': approved,
      });
      _showSnack('$action 처리되었습니다.', isError: false);
      await _loadPendingWorkers();
    } catch (e) {
      _showSnack('$action 처리에 실패했습니다.', isError: true);
    }
  }

  Future<void> _loadSettings() async {
    setState(() => _isLoadingSettings = true);
    try {
      final apiService = ref.read(apiServiceProvider);
      final response = await apiService.get('/admin/settings');
      if (mounted) {
        setState(() {
          _heatingJacketEnabled = response['heating_jacket_enabled'] as bool? ?? false;
          _phaseBlockEnabled = response['phase_block_enabled'] as bool? ?? false;
          _locationQrRequired = response['location_qr_required'] as bool? ?? true;
          // 근무시간 설정도 같은 응답에서 파싱
          _autoPauseEnabled = response['auto_pause_enabled'] as bool? ?? false;
          _breakMorningStart = response['break_morning_start'] as String? ?? '10:00';
          _breakMorningEnd = response['break_morning_end'] as String? ?? '10:10';
          _lunchStart = response['lunch_start'] as String? ?? '12:00';
          _lunchEnd = response['lunch_end'] as String? ?? '13:00';
          _breakAfternoonStart = response['break_afternoon_start'] as String? ?? '15:00';
          _breakAfternoonEnd = response['break_afternoon_end'] as String? ?? '15:10';
          _dinnerStart = response['dinner_start'] as String? ?? '18:00';
          _dinnerEnd = response['dinner_end'] as String? ?? '19:00';
          // 위치 보안 설정 (Sprint 19-D)
          _geolocationEnabled = response['geo_check_enabled'] as bool? ?? false;
          _geoStrictMode = response['geo_strict_mode'] as bool? ?? false;
          _geoLat = response['geo_latitude'] as String? ?? '';
          _geoLng = response['geo_longitude'] as String? ?? '';
          final rawRadius = response['geo_radius_meters'];
          if (rawRadius != null) {
            _geoRadiusMeters = (rawRadius is int)
                ? rawRadius.toDouble()
                : (rawRadius as num).toDouble();
          }
          _geoLatController.text = _geoLat;
          _geoLngController.text = _geoLng;
          _isLoadingSettings = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _isLoadingSettings = false);
    }
  }

  Future<void> _updateSetting(String key, bool value) async {
    try {
      final apiService = ref.read(apiServiceProvider);
      await apiService.put('/admin/settings', data: {key: value});
      if (mounted) {
        setState(() {
          if (key == 'heating_jacket_enabled') _heatingJacketEnabled = value;
          if (key == 'phase_block_enabled') _phaseBlockEnabled = value;
          if (key == 'location_qr_required') _locationQrRequired = value;
          if (key == 'auto_pause_enabled') _autoPauseEnabled = value;
          if (key == 'geo_check_enabled') _geolocationEnabled = value;
          if (key == 'geo_strict_mode') _geoStrictMode = value;
        });
        _showSnack('설정이 저장되었습니다.', isError: false);
      }
    } catch (e) {
      if (mounted) _showSnack('설정 저장에 실패했습니다.', isError: true);
    }
  }

  /// 문자열/숫자 설정값 업데이트 (PUT /admin/settings)
  Future<void> _updateSettingValue(String key, dynamic value) async {
    try {
      final apiService = ref.read(apiServiceProvider);
      await apiService.put('/admin/settings', data: {key: value});
      if (mounted) {
        _showSnack('설정이 저장되었습니다.', isError: false);
      }
    } catch (e) {
      if (mounted) _showSnack('설정 저장에 실패했습니다.', isError: true);
    }
  }

  Future<void> _loadManagers() async {
    setState(() => _isLoadingManagers = true);
    try {
      final apiService = ref.read(apiServiceProvider);
      final queryParams = _selectedManagerCompany != null
          ? '?company=${Uri.encodeComponent(_selectedManagerCompany!)}'
          : '';
      final response = await apiService.get('/admin/managers$queryParams');
      if (mounted) {
        setState(() {
          _managers = List<Map<String, dynamic>>.from(response['workers'] as List? ?? []);
          _isLoadingManagers = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _isLoadingManagers = false);
    }
  }

  Future<void> _toggleManager(int workerId, bool isManager) async {
    try {
      final apiService = ref.read(apiServiceProvider);
      await apiService.put('/admin/workers/$workerId/manager', data: {'is_manager': isManager});
      _showSnack(isManager ? '관리자로 지정했습니다.' : '관리자 해제했습니다.', isError: false);
      await _loadManagers();
    } catch (e) {
      _showSnack('변경에 실패했습니다.', isError: true);
    }
  }

  Future<void> _loadPendingTasks() async {
    setState(() => _isLoadingTasks = true);
    try {
      final apiService = ref.read(apiServiceProvider);
      final response = await apiService.get('/admin/tasks/pending');
      if (mounted) {
        setState(() {
          _pendingTasks = List<Map<String, dynamic>>.from(response['tasks'] as List? ?? []);
          _isLoadingTasks = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _isLoadingTasks = false);
    }
  }

  Future<void> _forceCloseTask(int taskId) async {
    final reasonController = TextEditingController();
    DateTime selectedDateTime = DateTime.now();

    final confirmed = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.lg)),
          title: Row(
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: GxColors.dangerBg,
                  borderRadius: BorderRadius.circular(GxRadius.md),
                ),
                child: const Icon(Icons.stop_circle, color: GxColors.danger, size: 18),
              ),
              const SizedBox(width: 10),
              const Text('강제 종료', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: GxColors.danger)),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('완료 시각', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: GxColors.steel, letterSpacing: 0.5)),
              const SizedBox(height: 6),
              InkWell(
                onTap: () async {
                  final date = await showDatePicker(
                    context: ctx,
                    initialDate: selectedDateTime,
                    firstDate: DateTime(2026),
                    lastDate: DateTime.now().add(const Duration(days: 1)),
                  );
                  if (date != null) {
                    final time = await showTimePicker(
                      context: ctx,
                      initialTime: TimeOfDay.fromDateTime(selectedDateTime),
                    );
                    if (time != null) {
                      setDialogState(() {
                        selectedDateTime = DateTime(
                          date.year, date.month, date.day,
                          time.hour, time.minute,
                        );
                      });
                    }
                  }
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(
                    border: Border.all(color: GxColors.mist, width: 1.5),
                    borderRadius: BorderRadius.circular(GxRadius.sm),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.access_time, size: 16, color: GxColors.steel),
                      const SizedBox(width: 8),
                      Text(
                        '${selectedDateTime.year}-${selectedDateTime.month.toString().padLeft(2,'0')}-${selectedDateTime.day.toString().padLeft(2,'0')} '
                        '${selectedDateTime.hour.toString().padLeft(2,'0')}:${selectedDateTime.minute.toString().padLeft(2,'0')}',
                        style: const TextStyle(fontSize: 13, color: GxColors.charcoal),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 14),
              const Text('종료 사유', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: GxColors.steel, letterSpacing: 0.5)),
              const SizedBox(height: 6),
              TextField(
                controller: reasonController,
                decoration: InputDecoration(
                  hintText: '예: 작업자 미처리, 연장 작업 미등록',
                  hintStyle: const TextStyle(fontSize: 12, color: GxColors.silver),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(GxRadius.sm),
                    borderSide: const BorderSide(color: GxColors.mist, width: 1.5),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(GxRadius.sm),
                    borderSide: const BorderSide(color: GxColors.mist, width: 1.5),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(GxRadius.sm),
                    borderSide: const BorderSide(color: GxColors.accent, width: 1.5),
                  ),
                ),
                maxLines: 2,
                style: const TextStyle(fontSize: 13),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('취소', style: TextStyle(color: GxColors.steel)),
            ),
            Container(
              height: 36,
              decoration: BoxDecoration(
                color: GxColors.danger,
                borderRadius: BorderRadius.circular(GxRadius.sm),
                boxShadow: [BoxShadow(color: GxColors.danger.withValues(alpha: 0.3), blurRadius: 8, offset: const Offset(0, 2))],
              ),
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: () => Navigator.pop(ctx, true),
                  borderRadius: BorderRadius.circular(GxRadius.sm),
                  child: const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 16),
                    child: Center(
                      child: Text('강제 종료', style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
                    ),
                  ),
                ),
              ),
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
      final apiService = ref.read(apiServiceProvider);
      await apiService.put('/admin/tasks/$taskId/force-close', data: {
        'completed_at': selectedDateTime.toIso8601String(),
        'close_reason': reason,
      });
      _showSnack('작업을 강제 종료했습니다.', isError: false);
      await _loadPendingTasks();
    } catch (e) {
      _showSnack('강제 종료에 실패했습니다.', isError: true);
    }
  }

  void _showSnack(String message, {required bool isError}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError ? GxColors.danger : GxColors.success,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: GxColors.cloud,
      appBar: AppBar(
        backgroundColor: GxColors.white,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, size: 18, color: GxColors.accent),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 4,
              height: 20,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [GxColors.accent, GxColors.accentHover],
                ),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(width: 12),
            const Text(
              '관리자 옵션',
              style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: GxColors.charcoal),
            ),
          ],
        ),
        centerTitle: false,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: GxColors.slate, size: 20),
            onPressed: _loadAll,
            tooltip: '새로고침',
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: GxColors.mist),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ===== 섹션 0: 가입 승인 대기 =====
              _buildSectionHeader(
                icon: Icons.person_add,
                iconBg: GxColors.warningBg,
                iconColor: GxColors.warning,
                title: '가입 승인 대기',
                subtitle: '회원가입 후 승인 대기 중인 작업자 (company 필터)',
                trailing: Text(
                  '${_filteredPendingWorkers.length}명',
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: GxColors.warning),
                ),
              ),
              const SizedBox(height: 10),

              // company 필터 칩
              SizedBox(
                height: 36,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  children: [
                    _buildFilterChip(
                      label: '전체',
                      isSelected: _selectedPendingCompany == null,
                      onTap: () {
                        setState(() => _selectedPendingCompany = null);
                      },
                    ),
                    ..._companies.map((c) => _buildFilterChip(
                      label: c,
                      isSelected: _selectedPendingCompany == c,
                      onTap: () {
                        setState(() => _selectedPendingCompany = c);
                      },
                    )),
                  ],
                ),
              ),
              const SizedBox(height: 10),

              if (_isLoadingPendingWorkers)
                const Center(
                  child: Padding(
                    padding: EdgeInsets.all(20),
                    child: CircularProgressIndicator(color: GxColors.accent, strokeWidth: 2),
                  ),
                )
              else if (_filteredPendingWorkers.isEmpty)
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: GxGlass.cardSm(radius: GxRadius.lg),
                  child: const Center(
                    child: Column(
                      children: [
                        Icon(Icons.check_circle_outline, size: 40, color: GxColors.success),
                        SizedBox(height: 8),
                        Text('대기 중인 가입 요청이 없습니다.', style: TextStyle(fontSize: 13, color: GxColors.steel)),
                      ],
                    ),
                  ),
                )
              else
                Container(
                  constraints: const BoxConstraints(maxHeight: 300),
                  decoration: GxGlass.cardSm(radius: GxRadius.lg),
                  child: Scrollbar(
                    thumbVisibility: true,
                    child: ListView.separated(
                      shrinkWrap: true,
                      itemCount: _filteredPendingWorkers.length,
                      separatorBuilder: (_, __) => const Divider(height: 1, color: GxColors.mist),
                      itemBuilder: (context, idx) {
                        return _buildPendingWorkerRow(_filteredPendingWorkers[idx]);
                      },
                    ),
                  ),
                ),
              const SizedBox(height: 24),

              // ===== 섹션 1: Admin Settings =====
              _buildSectionHeader(
                icon: Icons.tune,
                iconBg: GxColors.accentSoft,
                iconColor: GxColors.accent,
                title: 'Admin Settings',
                subtitle: 'Task 활성화 옵션 제어',
              ),
              const SizedBox(height: 10),
              Container(
                decoration: GxGlass.cardSm(radius: GxRadius.lg),
                child: _isLoadingSettings
                    ? const Padding(
                        padding: EdgeInsets.all(20),
                        child: Center(child: CircularProgressIndicator(color: GxColors.accent, strokeWidth: 2)),
                      )
                    : Column(
                        children: [
                          _buildSettingToggle(
                            title: 'Heating Jacket',
                            subtitle: 'Heating Jacket task 활성화 (MECH)',
                            value: _heatingJacketEnabled,
                            onChanged: (v) => _updateSetting('heating_jacket_enabled', v),
                            isFirst: true,
                          ),
                          const Divider(height: 1, color: GxColors.mist),
                          _buildSettingToggle(
                            title: 'Phase Block',
                            subtitle: 'Tank Docking 완료 전 POST_DOCKING task 차단 (ELEC)',
                            value: _phaseBlockEnabled,
                            onChanged: (v) => _updateSetting('phase_block_enabled', v),
                          ),
                          const Divider(height: 1, color: GxColors.mist),
                          _buildSettingToggle(
                            title: 'Location QR 필수',
                            subtitle: 'OFF 시 Location QR 미등록 경고를 건너뜀',
                            value: _locationQrRequired,
                            onChanged: (v) => _updateSetting('location_qr_required', v),
                          ),
                        ],
                      ),
              ),
              const SizedBox(height: 24),

              // ===== 섹션 2: 협력사 관리자 지정/해제 =====
              _buildSectionHeader(
                icon: Icons.manage_accounts,
                iconBg: GxColors.infoBg,
                iconColor: GxColors.info,
                title: '협력사 관리자 관리',
                subtitle: 'is_manager 토글 (company 필터)',
              ),
              const SizedBox(height: 10),

              // 협력사 필터 칩
              SizedBox(
                height: 36,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  children: [
                    _buildFilterChip(
                      label: '전체',
                      isSelected: _selectedManagerCompany == null,
                      onTap: () {
                        setState(() => _selectedManagerCompany = null);
                        _loadManagers();
                      },
                    ),
                    ..._companies.map((c) => _buildFilterChip(
                      label: c,
                      isSelected: _selectedManagerCompany == c,
                      onTap: () {
                        setState(() => _selectedManagerCompany = c);
                        _loadManagers();
                      },
                    )),
                  ],
                ),
              ),
              const SizedBox(height: 10),

              Container(
                decoration: GxGlass.cardSm(radius: GxRadius.lg),
                child: _isLoadingManagers
                    ? const Padding(
                        padding: EdgeInsets.all(20),
                        child: Center(child: CircularProgressIndicator(color: GxColors.accent, strokeWidth: 2)),
                      )
                    : _managers.isEmpty
                        ? const Padding(
                            padding: EdgeInsets.all(20),
                            child: Center(
                              child: Text('작업자가 없습니다.', style: TextStyle(fontSize: 13, color: GxColors.steel)),
                            ),
                          )
                        : Column(
                            children: _managers.asMap().entries.map((entry) {
                              final idx = entry.key;
                              final worker = entry.value;
                              final isLast = idx == _managers.length - 1;
                              return Column(
                                children: [
                                  _buildManagerRow(worker),
                                  if (!isLast) const Divider(height: 1, color: GxColors.mist),
                                ],
                              );
                            }).toList(),
                          ),
              ),
              const SizedBox(height: 24),

              // ===== 섹션 3: 미종료 작업 목록 =====
              _buildSectionHeader(
                icon: Icons.warning_amber,
                iconBg: GxColors.warningBg,
                iconColor: GxColors.warning,
                title: '미종료 작업',
                subtitle: '강제 종료 처리 필요 작업 목록',
                trailing: Text(
                  '${_pendingTasks.length}건',
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: GxColors.warning),
                ),
              ),
              const SizedBox(height: 10),

              if (_isLoadingTasks)
                const Center(
                  child: Padding(
                    padding: EdgeInsets.all(20),
                    child: CircularProgressIndicator(color: GxColors.accent, strokeWidth: 2),
                  ),
                )
              else if (_pendingTasks.isEmpty)
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: GxGlass.cardSm(radius: GxRadius.lg),
                  child: const Center(
                    child: Column(
                      children: [
                        Icon(Icons.check_circle_outline, size: 40, color: GxColors.success),
                        SizedBox(height: 8),
                        Text('미종료 작업이 없습니다.', style: TextStyle(fontSize: 13, color: GxColors.steel)),
                      ],
                    ),
                  ),
                )
              else
                Column(
                  children: _pendingTasks.map((task) => _buildPendingTaskCard(task)).toList(),
                ),

              const SizedBox(height: 24),

              // ===== 섹션 4: 근무시간 설정 =====
              _buildSectionHeader(
                icon: Icons.schedule,
                iconBg: GxColors.infoBg,
                iconColor: GxColors.info,
                title: '근무시간 설정',
                subtitle: '휴게/점심/저녁 시간 자동 일시정지 설정',
              ),
              const SizedBox(height: 10),
              Container(
                decoration: GxGlass.cardSm(radius: GxRadius.lg),
                child: _isLoadingSettings
                    ? const Padding(
                        padding: EdgeInsets.all(20),
                        child: Center(child: CircularProgressIndicator(color: GxColors.accent, strokeWidth: 2)),
                      )
                    : Column(
                        children: [
                          // auto_pause_enabled 토글
                          _buildSettingToggle(
                            title: '자동 일시정지',
                            subtitle: '휴게시간 시작 시 진행 중인 작업을 자동으로 일시정지',
                            value: _autoPauseEnabled,
                            onChanged: (v) => _updateSetting('auto_pause_enabled', v),
                            isFirst: true,
                          ),
                          const Divider(height: 1, color: GxColors.mist),
                          // 오전 휴게
                          _buildBreakTimeRow(
                            label: '오전 휴게',
                            startValue: _breakMorningStart,
                            endValue: _breakMorningEnd,
                            onTapStart: () => _pickTime(
                              label: '오전 휴게 시작',
                              currentValue: _breakMorningStart,
                              settingKey: 'break_morning_start',
                              onSaved: (v) => _breakMorningStart = v,
                            ),
                            onTapEnd: () => _pickTime(
                              label: '오전 휴게 종료',
                              currentValue: _breakMorningEnd,
                              settingKey: 'break_morning_end',
                              onSaved: (v) => _breakMorningEnd = v,
                            ),
                          ),
                          const Divider(height: 1, color: GxColors.mist),
                          // 점심시간
                          _buildBreakTimeRow(
                            label: '점심시간',
                            startValue: _lunchStart,
                            endValue: _lunchEnd,
                            onTapStart: () => _pickTime(
                              label: '점심 시작',
                              currentValue: _lunchStart,
                              settingKey: 'lunch_start',
                              onSaved: (v) => _lunchStart = v,
                            ),
                            onTapEnd: () => _pickTime(
                              label: '점심 종료',
                              currentValue: _lunchEnd,
                              settingKey: 'lunch_end',
                              onSaved: (v) => _lunchEnd = v,
                            ),
                          ),
                          const Divider(height: 1, color: GxColors.mist),
                          // 오후 휴게
                          _buildBreakTimeRow(
                            label: '오후 휴게',
                            startValue: _breakAfternoonStart,
                            endValue: _breakAfternoonEnd,
                            onTapStart: () => _pickTime(
                              label: '오후 휴게 시작',
                              currentValue: _breakAfternoonStart,
                              settingKey: 'break_afternoon_start',
                              onSaved: (v) => _breakAfternoonStart = v,
                            ),
                            onTapEnd: () => _pickTime(
                              label: '오후 휴게 종료',
                              currentValue: _breakAfternoonEnd,
                              settingKey: 'break_afternoon_end',
                              onSaved: (v) => _breakAfternoonEnd = v,
                            ),
                          ),
                          const Divider(height: 1, color: GxColors.mist),
                          // 저녁시간
                          _buildBreakTimeRow(
                            label: '저녁시간',
                            startValue: _dinnerStart,
                            endValue: _dinnerEnd,
                            onTapStart: () => _pickTime(
                              label: '저녁 시작',
                              currentValue: _dinnerStart,
                              settingKey: 'dinner_start',
                              onSaved: (v) => _dinnerStart = v,
                            ),
                            onTapEnd: () => _pickTime(
                              label: '저녁 종료',
                              currentValue: _dinnerEnd,
                              settingKey: 'dinner_end',
                              onSaved: (v) => _dinnerEnd = v,
                            ),
                          ),
                        ],
                      ),
              ),

              const SizedBox(height: 24),

              // ===== 섹션 5: 위치 보안 =====
              _buildSectionHeader(
                icon: Icons.location_on_outlined,
                iconBg: GxColors.successBg,
                iconColor: GxColors.success,
                title: '위치 보안',
                subtitle: '출근 시 GPS 위치 검증 설정',
              ),
              const SizedBox(height: 10),
              Container(
                decoration: GxGlass.cardSm(radius: GxRadius.lg),
                child: _isLoadingSettings
                    ? const Padding(
                        padding: EdgeInsets.all(20),
                        child: Center(child: CircularProgressIndicator(color: GxColors.accent, strokeWidth: 2)),
                      )
                    : Column(
                        children: [
                          // 위치 검증 활성화 토글
                          _buildSettingToggle(
                            title: 'GPS 위치 검증',
                            subtitle: '출근 시 GPS 위치 확인 (비활성화 시 위치 무시)',
                            value: _geolocationEnabled,
                            onChanged: (v) => _updateSetting('geo_check_enabled', v),
                            isFirst: true,
                          ),
                          // 위치 검증 활성화 시 추가 설정 표시
                          if (_geolocationEnabled) ...[
                            const Divider(height: 1, color: GxColors.mist),
                            _buildSettingToggle(
                              title: '엄격 모드',
                              subtitle: 'ON: 위치 미전송 시 출근 거부 / OFF: 위치 없으면 경고만',
                              value: _geoStrictMode,
                              onChanged: (v) => _updateSetting('geo_strict_mode', v),
                            ),
                            const Divider(height: 1, color: GxColors.mist),
                            // 기준 위도
                            _buildTextFieldSetting(
                              title: '기준 위도 (Latitude)',
                              controller: _geoLatController,
                              hintText: '예: 35.123456',
                              onSaved: (v) {
                                setState(() => _geoLat = v);
                                _updateSettingValue('geo_latitude', v);
                              },
                            ),
                            const Divider(height: 1, color: GxColors.mist),
                            // 기준 경도
                            _buildTextFieldSetting(
                              title: '기준 경도 (Longitude)',
                              controller: _geoLngController,
                              hintText: '예: 128.654321',
                              onSaved: (v) {
                                setState(() => _geoLng = v);
                                _updateSettingValue('geo_longitude', v);
                              },
                            ),
                            const Divider(height: 1, color: GxColors.mist),
                            // 허용 반경 드롭다운
                            _buildDropdownSetting(
                              title: '허용 반경',
                              value: _geoRadiusMeters,
                              options: _radiusOptions,
                              labelBuilder: (v) => '${v.toInt()}m',
                              onChanged: (v) {
                                setState(() => _geoRadiusMeters = v);
                                _updateSettingValue('geo_radius_meters', v.toInt());
                              },
                            ),
                          ],
                        ],
                      ),
              ),

              const SizedBox(height: 32),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSectionHeader({
    required IconData icon,
    required Color iconBg,
    required Color iconColor,
    required String title,
    required String subtitle,
    Widget? trailing,
  }) {
    return Row(
      children: [
        Container(
          width: 32,
          height: 32,
          decoration: BoxDecoration(
            color: iconBg,
            borderRadius: BorderRadius.circular(GxRadius.md),
          ),
          child: Icon(icon, size: 16, color: iconColor),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: GxColors.charcoal)),
              Text(subtitle, style: const TextStyle(fontSize: 11, color: GxColors.steel)),
            ],
          ),
        ),
        if (trailing != null) trailing,
      ],
    );
  }

  Widget _buildSettingToggle({
    required String title,
    required String subtitle,
    required bool value,
    required ValueChanged<bool> onChanged,
    bool isFirst = false,
  }) {
    return Padding(
      padding: EdgeInsets.only(
        left: 16, right: 8,
        top: isFirst ? 14 : 10,
        bottom: 10,
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: GxColors.charcoal)),
                const SizedBox(height: 2),
                Text(subtitle, style: const TextStyle(fontSize: 11, color: GxColors.steel)),
              ],
            ),
          ),
          Switch(
            value: value,
            onChanged: onChanged,
            activeColor: GxColors.accent,
            activeTrackColor: GxColors.accentSoft,
          ),
        ],
      ),
    );
  }

  /// 휴게시간 행: 레이블 + 시작시각 + "~" + 종료시각
  Widget _buildBreakTimeRow({
    required String label,
    required String startValue,
    required String endValue,
    required VoidCallback onTapStart,
    required VoidCallback onTapEnd,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: GxColors.charcoal),
            ),
          ),
          // 시작 시각 버튼
          GestureDetector(
            onTap: onTapStart,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: GxColors.infoBg,
                borderRadius: BorderRadius.circular(GxRadius.sm),
                border: Border.all(color: GxColors.info.withValues(alpha: 0.3), width: 1),
              ),
              child: Text(
                startValue,
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: GxColors.info),
              ),
            ),
          ),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 6),
            child: Text('~', style: TextStyle(fontSize: 13, color: GxColors.steel, fontWeight: FontWeight.w500)),
          ),
          // 종료 시각 버튼
          GestureDetector(
            onTap: onTapEnd,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: GxColors.infoBg,
                borderRadius: BorderRadius.circular(GxRadius.sm),
                border: Border.all(color: GxColors.info.withValues(alpha: 0.3), width: 1),
              ),
              child: Text(
                endValue,
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: GxColors.info),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterChip({
    required String label,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(right: 8),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? GxColors.accent : GxGlass.cardBgLight,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isSelected ? GxColors.accent : GxColors.mist,
            width: 1.5,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w500,
            color: isSelected ? Colors.white : GxColors.slate,
          ),
        ),
      ),
    );
  }

  Widget _buildManagerRow(Map<String, dynamic> worker) {
    final isManager = worker['is_manager'] as bool? ?? false;
    final role = worker['role'] as String? ?? '';
    final company = worker['company'] as String? ?? '';

    Color roleColor;
    switch (role) {
      case 'MECH': roleColor = const Color(0xFFEA580C); break;
      case 'ELEC': roleColor = GxColors.info; break;
      case 'TM': roleColor = const Color(0xFF0D9488); break;
      default: roleColor = GxColors.accent;
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: roleColor.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(GxRadius.md),
            ),
            child: Center(
              child: Text(
                (worker['name'] as String? ?? '?').isNotEmpty
                    ? (worker['name'] as String).substring(0, 1)
                    : '?',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: roleColor),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  worker['name'] as String? ?? '',
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: GxColors.charcoal),
                ),
                const SizedBox(height: 2),
                Text(
                  '$company · $role',
                  style: const TextStyle(fontSize: 11, color: GxColors.steel),
                ),
              ],
            ),
          ),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (isManager)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  margin: const EdgeInsets.only(right: 8),
                  decoration: BoxDecoration(
                    color: GxColors.successBg,
                    borderRadius: BorderRadius.circular(GxRadius.sm),
                  ),
                  child: const Text(
                    '관리자',
                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: GxColors.success),
                  ),
                ),
              Switch(
                value: isManager,
                onChanged: (v) => _toggleManager(worker['id'] as int, v),
                activeColor: GxColors.success,
                activeTrackColor: GxColors.successBg,
                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildPendingWorkerRow(Map<String, dynamic> worker) {
    final workerId = worker['id'] as int;
    final name = worker['name'] as String? ?? '';
    final email = worker['email'] as String? ?? '';
    final role = worker['role'] as String? ?? '';
    final company = worker['company'] as String? ?? '';
    final createdAt = worker['created_at'] != null
        ? DateTime.tryParse(worker['created_at'] as String)
        : null;

    Color roleColor;
    switch (role) {
      case 'MECH': roleColor = const Color(0xFFEA580C); break;
      case 'ELEC': roleColor = GxColors.info; break;
      case 'TM': roleColor = const Color(0xFF0D9488); break;
      case 'PI': roleColor = const Color(0xFF7C3AED); break;
      case 'QI': roleColor = const Color(0xFF2563EB); break;
      case 'SI': roleColor = const Color(0xFF059669); break;
      default: roleColor = GxColors.accent;
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: roleColor.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(GxRadius.md),
            ),
            child: Center(
              child: Text(
                name.isNotEmpty ? name.substring(0, 1) : '?',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: roleColor),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: GxColors.charcoal)),
                const SizedBox(height: 2),
                Text(
                  '$company · $role · $email',
                  style: const TextStyle(fontSize: 11, color: GxColors.steel),
                  overflow: TextOverflow.ellipsis,
                ),
                if (createdAt != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    '가입: ${createdAt.year}-${createdAt.month.toString().padLeft(2, '0')}-${createdAt.day.toString().padLeft(2, '0')}',
                    style: const TextStyle(fontSize: 10, color: GxColors.silver),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: 8),
          // 거부 버튼
          GestureDetector(
            onTap: () => _approveWorker(workerId, false),
            child: Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: GxColors.dangerBg,
                borderRadius: BorderRadius.circular(GxRadius.sm),
              ),
              child: const Icon(Icons.close, size: 16, color: GxColors.danger),
            ),
          ),
          const SizedBox(width: 6),
          // 승인 버튼
          GestureDetector(
            onTap: () => _approveWorker(workerId, true),
            child: Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: GxColors.successBg,
                borderRadius: BorderRadius.circular(GxRadius.sm),
              ),
              child: const Icon(Icons.check, size: 16, color: GxColors.success),
            ),
          ),
        ],
      ),
    );
  }

  /// 텍스트 필드 설정 행 (좌표 입력 등)
  ///
  /// 포커스를 잃거나 완료(done) 시 onSaved 호출
  Widget _buildTextFieldSetting({
    required String title,
    required TextEditingController controller,
    required String hintText,
    required void Function(String) onSaved,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Row(
        children: [
          Expanded(
            flex: 2,
            child: Text(
              title,
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: GxColors.charcoal),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            flex: 3,
            child: TextField(
              controller: controller,
              keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: true),
              textInputAction: TextInputAction.done,
              style: const TextStyle(fontSize: 13, color: GxColors.charcoal),
              decoration: InputDecoration(
                hintText: hintText,
                hintStyle: const TextStyle(fontSize: 12, color: GxColors.silver),
                contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(GxRadius.sm),
                  borderSide: const BorderSide(color: GxColors.mist, width: 1.5),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(GxRadius.sm),
                  borderSide: const BorderSide(color: GxColors.mist, width: 1.5),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(GxRadius.sm),
                  borderSide: const BorderSide(color: GxColors.accent, width: 1.5),
                ),
                isDense: true,
              ),
              onSubmitted: (v) => onSaved(v.trim()),
              onEditingComplete: () => onSaved(controller.text.trim()),
            ),
          ),
        ],
      ),
    );
  }

  /// 드롭다운 설정 행 (반경 선택 등)
  Widget _buildDropdownSetting({
    required String title,
    required double value,
    required List<double> options,
    required String Function(double) labelBuilder,
    required void Function(double) onChanged,
  }) {
    // 현재 값이 옵션 목록에 없으면 가장 가까운 옵션으로 대체
    final safeValue = options.contains(value) ? value : options.first;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Row(
        children: [
          Expanded(
            flex: 2,
            child: Text(
              title,
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: GxColors.charcoal),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            flex: 3,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              decoration: BoxDecoration(
                color: GxColors.cloud,
                borderRadius: BorderRadius.circular(GxRadius.sm),
                border: Border.all(color: GxColors.mist, width: 1.5),
              ),
              child: DropdownButtonHideUnderline(
                child: DropdownButton<double>(
                  value: safeValue,
                  isExpanded: true,
                  icon: const Icon(Icons.arrow_drop_down, color: GxColors.steel, size: 20),
                  style: const TextStyle(fontSize: 13, color: GxColors.charcoal),
                  items: options.map((opt) {
                    return DropdownMenuItem<double>(
                      value: opt,
                      child: Text(labelBuilder(opt)),
                    );
                  }).toList(),
                  onChanged: (v) {
                    if (v != null) onChanged(v);
                  },
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPendingTaskCard(Map<String, dynamic> task) {
    final taskId = task['id'] as int;
    final taskName = task['task_name'] as String? ?? '';
    final workerName = task['worker_name'] as String? ?? '';
    final serialNumber = task['serial_number'] as String? ?? '';
    final taskCategory = task['task_category'] as String? ?? '';
    final startedAt = task['started_at'] != null
        ? DateTime.tryParse(task['started_at'] as String)
        : null;

    Color categoryColor;
    switch (taskCategory) {
      case 'MECH': categoryColor = const Color(0xFFEA580C); break;
      case 'ELEC': categoryColor = GxColors.info; break;
      case 'TMS': categoryColor = const Color(0xFF0D9488); break;
      default: categoryColor = GxColors.steel;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: GxGlass.cardSm(radius: GxRadius.lg).copyWith(
        border: Border.all(color: GxColors.warning.withValues(alpha: 0.3), width: 1),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: categoryColor.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(GxRadius.sm),
                  ),
                  child: Text(
                    taskCategory,
                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: categoryColor),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    taskName,
                    style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: GxColors.charcoal),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: GxColors.warningBg,
                    borderRadius: BorderRadius.circular(GxRadius.sm),
                  ),
                  child: const Text(
                    '미종료',
                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: GxColors.warning),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                const Icon(Icons.person_outline, size: 14, color: GxColors.steel),
                const SizedBox(width: 4),
                Text(workerName, style: const TextStyle(fontSize: 12, color: GxColors.slate)),
                const SizedBox(width: 16),
                const Icon(Icons.qr_code, size: 14, color: GxColors.steel),
                const SizedBox(width: 4),
                Text(serialNumber, style: const TextStyle(fontSize: 12, color: GxColors.slate)),
              ],
            ),
            if (startedAt != null) ...[
              const SizedBox(height: 4),
              Row(
                children: [
                  const Icon(Icons.access_time, size: 14, color: GxColors.steel),
                  const SizedBox(width: 4),
                  Text(
                    '시작: ${startedAt.year}-${startedAt.month.toString().padLeft(2,'0')}-${startedAt.day.toString().padLeft(2,'0')} '
                    '${startedAt.hour.toString().padLeft(2,'0')}:${startedAt.minute.toString().padLeft(2,'0')}',
                    style: const TextStyle(fontSize: 12, color: GxColors.slate),
                  ),
                ],
              ),
            ],
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              height: 36,
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: [GxColors.danger, GxColors.danger.withValues(alpha: 0.8)]),
                borderRadius: BorderRadius.circular(GxRadius.sm),
              ),
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: () => _forceCloseTask(taskId),
                  borderRadius: BorderRadius.circular(GxRadius.sm),
                  child: Center(
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: const [
                        Icon(Icons.stop_circle, size: 16, color: Colors.white),
                        SizedBox(width: 6),
                        Text('강제 종료', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.white)),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
