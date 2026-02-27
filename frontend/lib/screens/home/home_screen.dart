import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../providers/alert_provider.dart';
import '../../services/websocket_service.dart';
import '../../utils/design_system.dart';
import '../../widgets/break_time_popup.dart';
import '../../widgets/break_time_end_popup.dart';

/// 홈 화면 (메인 화면)
///
/// G-AXIS Design System 적용: cloud 배경, 인디고 액센트, 카드 스타일
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

/// 출퇴근 상태
enum AttendanceStatus { notCheckedIn, checkedIn, checkedOut }

class _HomeScreenState extends ConsumerState<HomeScreen> {
  final WebSocketService _websocketService = WebSocketService();
  bool _websocketInitialized = false;

  // 출퇴근 상태
  AttendanceStatus _attendanceStatus = AttendanceStatus.notCheckedIn;
  String? _checkInTime;
  bool _attendanceLoading = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _initializeAlerts();
      _fetchAttendanceStatus();
    });
  }

  @override
  void dispose() {
    _websocketService.disconnect();
    _websocketService.dispose();
    super.dispose();
  }

  Future<void> _initializeAlerts() async {
    final authService = ref.read(authServiceProvider);
    final token = await authService.getToken();

    if (token != null && !_websocketInitialized) {
      try {
        await _websocketService.connect(token);
        ref.read(alertProvider.notifier).subscribeToAlerts(_websocketService);
        _subscribeToBreakTimeEvents();
        await ref.read(alertProvider.notifier).fetchAlerts();
        await ref.read(alertProvider.notifier).refreshUnreadCount();
        _websocketInitialized = true;
      } catch (e) {
        debugPrint('[HomeScreen] Failed to initialize alerts: $e');
      }
    }
  }

  /// 휴게시간 WebSocket 이벤트 구독
  void _subscribeToBreakTimeEvents() {
    // BREAK_TIME_PAUSE: 휴게시간 시작 → 자동 일시정지 팝업
    _websocketService.on('BREAK_TIME_PAUSE', (data) {
      if (!mounted) return;
      final breakType = data['break_type'] as String? ?? 'morning';
      final breakTypeName = _breakTypeLabel(breakType);
      final endTime = data['end_time'] as String? ?? '';
      BreakTimePopup.show(
        context,
        breakType: breakType,
        breakTypeName: breakTypeName,
        endTime: endTime,
      );
    });

    // BREAK_TIME_END: 휴게시간 종료 → 작업 재개 팝업
    _websocketService.on('BREAK_TIME_END', (data) {
      if (!mounted) return;
      final breakType = data['break_type'] as String? ?? 'morning';
      final breakTypeName = _breakTypeLabel(breakType);
      BreakTimeEndPopup.show(
        context,
        breakTypeName: breakTypeName,
      );
    });
  }

  /// 휴게시간 유형 → 한국어 레이블
  String _breakTypeLabel(String breakType) {
    switch (breakType) {
      case 'morning': return '오전 휴게';
      case 'lunch': return '점심시간';
      case 'afternoon': return '오후 휴게';
      case 'dinner': return '저녁시간';
      default: return '휴게시간';
    }
  }

  /// 출퇴근 상태 조회
  Future<void> _fetchAttendanceStatus() async {
    final authState = ref.read(authProvider);
    final worker = authState.currentWorker;
    // 파트너사(협력사)만 출퇴근 기능 표시
    if (worker?.company == 'GST' || worker?.isAdmin == true) return;

    try {
      final apiService = ref.read(apiServiceProvider);
      final response = await apiService.get('/hr/attendance/today');
      if (!mounted) return;
      final status = response['status'] as String? ?? 'not_checked_in';
      final checkInAt = response['check_in_time'] as String?;
      setState(() {
        if (status == 'checked_in') {
          _attendanceStatus = AttendanceStatus.checkedIn;
          _checkInTime = checkInAt;
        } else if (status == 'checked_out') {
          _attendanceStatus = AttendanceStatus.checkedOut;
          _checkInTime = checkInAt;
        } else {
          _attendanceStatus = AttendanceStatus.notCheckedIn;
          _checkInTime = null;
        }
      });
    } catch (e) {
      debugPrint('[HomeScreen] fetchAttendanceStatus error: $e');
    }
  }

  /// 출근/퇴근 처리
  Future<void> _handleAttendance() async {
    setState(() => _attendanceLoading = true);
    try {
      final apiService = ref.read(apiServiceProvider);
      final checkType = _attendanceStatus == AttendanceStatus.notCheckedIn ? 'in' : 'out';
      await apiService.post('/hr/attendance/check', data: {'check_type': checkType});
      await _fetchAttendanceStatus();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('처리 실패: ${e.toString().replaceFirst('Exception: ', '')}'),
            backgroundColor: GxColors.danger,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _attendanceLoading = false);
    }
  }

  /// 출퇴근 카드 빌드
  Widget _buildAttendanceCard() {
    String statusLabel;
    Color statusColor;
    String buttonLabel;
    bool buttonDisabled = false;

    switch (_attendanceStatus) {
      case AttendanceStatus.notCheckedIn:
        statusLabel = '미출근';
        statusColor = GxColors.silver;
        buttonLabel = '출근하기';
        break;
      case AttendanceStatus.checkedIn:
        statusLabel = '출근 중';
        statusColor = GxColors.success;
        buttonLabel = '퇴근하기';
        break;
      case AttendanceStatus.checkedOut:
        statusLabel = '퇴근 완료';
        statusColor = GxColors.info;
        buttonLabel = '퇴근 완료';
        buttonDisabled = true;
        break;
    }

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: GxGlass.cardSm(radius: GxRadius.lg),
      child: Row(
        children: [
          Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(
              color: statusColor.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(GxRadius.md),
            ),
            child: Icon(
              _attendanceStatus == AttendanceStatus.notCheckedIn
                  ? Icons.login
                  : _attendanceStatus == AttendanceStatus.checkedIn
                      ? Icons.access_time
                      : Icons.logout,
              size: 16,
              color: statusColor,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      '근태',
                      style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: GxColors.graphite),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: statusColor.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        statusLabel,
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: statusColor),
                      ),
                    ),
                  ],
                ),
                if (_checkInTime != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    '출근: ${_formatTime(_checkInTime!)}',
                    style: const TextStyle(fontSize: 11, color: GxColors.steel),
                  ),
                ],
              ],
            ),
          ),
          if (!buttonDisabled)
            GestureDetector(
              onTap: _attendanceLoading ? null : _handleAttendance,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                decoration: BoxDecoration(
                  gradient: buttonDisabled ? null : GxGradients.accentButton,
                  color: buttonDisabled ? GxColors.mist : null,
                  borderRadius: BorderRadius.circular(GxRadius.sm),
                ),
                child: _attendanceLoading
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : Text(
                        buttonLabel,
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: buttonDisabled ? GxColors.silver : Colors.white,
                        ),
                      ),
              ),
            )
          else
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                color: GxColors.mist,
                borderRadius: BorderRadius.circular(GxRadius.sm),
              ),
              child: Text(
                buttonLabel,
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: GxColors.silver),
              ),
            ),
        ],
      ),
    );
  }

  /// 시간 포맷 (ISO string → 한국 로컬 시간 HH:mm)
  String _formatTime(String isoString) {
    try {
      final dt = DateTime.parse(isoString).toLocal();
      final h = dt.hour.toString().padLeft(2, '0');
      final m = dt.minute.toString().padLeft(2, '0');
      return '$h:$m';
    } catch (_) {
      return isoString;
    }
  }

  /// 역할별 컬러 반환
  Color _getRoleColor(String? role) {
    switch (role) {
      case 'MECH': return const Color(0xFFEA580C);
      case 'ELEC': return GxColors.info;
      case 'TM': return const Color(0xFF0D9488);
      case 'PI': return GxColors.success;
      case 'QI': return const Color(0xFF7C3AED);
      case 'SI': return GxColors.accent;
      case 'ADMIN': return GxColors.accent;
      default: return GxColors.accent;
    }
  }

  /// 활성 역할 한국어 레이블
  String _getActiveRoleLabel(String? role) {
    switch (role) {
      case 'PI': return 'PI 가압검사';
      case 'QI': return 'QI 공정검사';
      case 'SI': return 'SI 마무리공정';
      default: return role ?? '';
    }
  }

  /// 역할별 아이콘 반환
  IconData _getRoleIcon(String? role) {
    switch (role) {
      case 'MECH': return Icons.build;
      case 'ELEC': return Icons.electrical_services;
      case 'TM': return Icons.inventory;
      case 'PI': return Icons.compress;
      case 'QI': return Icons.verified;
      case 'SI': return Icons.local_shipping;
      case 'ADMIN': return Icons.admin_panel_settings;
      default: return Icons.person;
    }
  }

  /// GST 작업자 active_role 변경 다이얼로그
  Future<void> _showActiveRoleDialog(BuildContext context, WidgetRef ref, String? currentRole) async {
    final roles = [
      {'code': 'PI', 'label': 'PI 가압검사', 'icon': Icons.compress, 'color': GxColors.success},
      {'code': 'QI', 'label': 'QI 공정검사', 'icon': Icons.verified, 'color': const Color(0xFF7C3AED)},
      {'code': 'SI', 'label': 'SI 마무리공정', 'icon': Icons.local_shipping, 'color': GxColors.accent},
    ];

    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.lg)),
        title: const Text(
          '활성 역할 선택',
          style: TextStyle(color: GxColors.charcoal, fontWeight: FontWeight.w600, fontSize: 15),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: roles.map((r) {
            final isSelected = currentRole == r['code'];
            final color = r['color'] as Color;
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: InkWell(
                onTap: () async {
                  Navigator.of(ctx).pop();
                  await ref.read(authProvider.notifier).changeActiveRole(r['code'] as String);
                },
                borderRadius: BorderRadius.circular(GxRadius.md),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(
                    color: isSelected ? color.withValues(alpha: 0.1) : GxColors.cloud,
                    borderRadius: BorderRadius.circular(GxRadius.md),
                    border: Border.all(
                      color: isSelected ? color : GxColors.mist,
                      width: isSelected ? 1.5 : 1,
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(r['icon'] as IconData, size: 18, color: color),
                      const SizedBox(width: 10),
                      Text(
                        r['label'] as String,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                          color: isSelected ? color : GxColors.graphite,
                        ),
                      ),
                      if (isSelected) ...[
                        const Spacer(),
                        Icon(Icons.check_circle, size: 16, color: color),
                      ],
                    ],
                  ),
                ),
              ),
            );
          }).toList(),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('취소', style: TextStyle(color: GxColors.steel)),
          ),
        ],
      ),
    );
  }

  Future<void> _handleLogout(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.lg)),
        title: const Text('로그아웃', style: TextStyle(color: GxColors.charcoal, fontWeight: FontWeight.w600)),
        content: const Text('로그아웃 하시겠습니까?', style: TextStyle(color: GxColors.slate)),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
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
                onTap: () => Navigator.of(context).pop(true),
                borderRadius: BorderRadius.circular(GxRadius.sm),
                child: const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 16),
                  child: Center(
                    child: Text('로그아웃', style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await ref.read(authProvider.notifier).logout();
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final alertState = ref.watch(alertProvider);
    final worker = authState.currentWorker;
    final unreadCount = alertState.unreadCount;
    final roleColor = _getRoleColor(worker?.role);

    return Scaffold(
      backgroundColor: GxColors.cloud,
      appBar: AppBar(
        backgroundColor: GxColors.white,
        elevation: 0,
        title: Row(
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
              'AXIS-OPS',
              style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w600,
                color: GxColors.charcoal,
              ),
            ),
          ],
        ),
        actions: [
          // 설정 버튼
          IconButton(
            icon: const Icon(Icons.settings_outlined, color: GxColors.slate, size: 22),
            onPressed: () => Navigator.pushNamed(context, '/profile'),
          ),
          // 알림 버튼
          Stack(
            children: [
              IconButton(
                icon: const Icon(Icons.notifications_outlined, color: GxColors.slate, size: 22),
                onPressed: () => Navigator.pushNamed(context, '/alerts'),
              ),
              if (unreadCount > 0)
                Positioned(
                  right: 8,
                  top: 8,
                  child: Container(
                    padding: const EdgeInsets.all(3),
                    decoration: const BoxDecoration(
                      color: GxColors.danger,
                      shape: BoxShape.circle,
                    ),
                    constraints: const BoxConstraints(minWidth: 16, minHeight: 16),
                    child: Text(
                      unreadCount > 99 ? '99+' : '$unreadCount',
                      style: const TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.bold),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),
            ],
          ),
          IconButton(
            icon: const Icon(Icons.logout, color: GxColors.slate, size: 20),
            onPressed: () => _handleLogout(context, ref),
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: GxColors.mist),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Worker 정보 카드
            Container(
              padding: const EdgeInsets.all(16),
              decoration: GxGlass.cardSm(radius: GxRadius.lg),
              child: Column(
                children: [
                  Row(
                    children: [
                      // 역할 아이콘
                      Container(
                        width: 40,
                        height: 40,
                        decoration: BoxDecoration(
                          color: roleColor.withValues(alpha: 0.08),
                          borderRadius: BorderRadius.circular(GxRadius.md),
                        ),
                        child: Icon(_getRoleIcon(worker?.role), size: 20, color: roleColor),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              worker?.name ?? '사용자',
                              style: const TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.w600,
                                color: GxColors.charcoal,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              worker?.email ?? '',
                              style: const TextStyle(fontSize: 12, color: GxColors.steel),
                            ),
                          ],
                        ),
                      ),
                      // Worker 배지
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: roleColor.withValues(alpha: 0.08),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              width: 5,
                              height: 5,
                              decoration: BoxDecoration(
                                color: roleColor,
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Text(
                              worker?.roleDisplayName ?? '',
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: roleColor,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  // GST 작업자 active_role 표시
                  if (worker?.company == 'GST' || worker?.isAdmin == true) ...[
                    const SizedBox(height: 10),
                    const Divider(color: GxColors.mist, height: 1),
                    const SizedBox(height: 10),
                    InkWell(
                      onTap: () => _showActiveRoleDialog(context, ref, worker?.activeRole),
                      borderRadius: BorderRadius.circular(GxRadius.sm),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 2),
                        child: Row(
                          children: [
                            const Icon(Icons.swap_horiz, size: 14, color: GxColors.steel),
                            const SizedBox(width: 6),
                            const Text(
                              '활성 역할:',
                              style: TextStyle(fontSize: 12, color: GxColors.steel),
                            ),
                            const SizedBox(width: 6),
                            if (worker?.activeRole != null)
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                decoration: BoxDecoration(
                                  color: _getRoleColor(worker?.activeRole).withValues(alpha: 0.1),
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: Text(
                                  _getActiveRoleLabel(worker?.activeRole),
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                    color: _getRoleColor(worker?.activeRole),
                                  ),
                                ),
                              )
                            else
                              const Text(
                                '미설정 (탭하여 선택)',
                                style: TextStyle(fontSize: 11, color: GxColors.silver),
                              ),
                            const Spacer(),
                            const Icon(Icons.edit_outlined, size: 14, color: GxColors.silver),
                          ],
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 16),

            // 협력사 작업자 출퇴근 카드 (GST/Admin 제외)
            if (worker?.company != 'GST' && worker?.isAdmin != true) ...[
              _buildAttendanceCard(),
              const SizedBox(height: 12),
            ],

            // 주요 기능
            _buildFeatureCard(
              icon: Icons.qr_code_scanner,
              iconBg: GxColors.accentSoft,
              iconColor: GxColors.accent,
              title: 'QR Scan',
              subtitle: 'Worksheet / Location QR 스캔',
              onTap: () => Navigator.pushNamed(context, '/qr-scan'),
            ),
            const SizedBox(height: 8),

            _buildFeatureCard(
              icon: Icons.task_alt,
              iconBg: GxColors.successBg,
              iconColor: GxColors.success,
              title: '작업 관리',
              subtitle: '진행 중인 작업 확인 및 관리',
              onTap: () => Navigator.pushNamed(context, '/task-management'),
            ),
            const SizedBox(height: 8),

            // 관리자 전용: 관리자 옵션
            if (worker?.isAdmin == true) ...[
              _buildFeatureCard(
                icon: Icons.admin_panel_settings,
                iconBg: GxColors.warningBg,
                iconColor: GxColors.warning,
                title: '관리자 옵션',
                subtitle: '설정, 협력사 관리자, 미종료 작업 처리',
                onTap: () => Navigator.pushNamed(context, '/admin-options'),
              ),
              const SizedBox(height: 8),
            ],

            // 협력사 관리자 전용: 미종료 작업 (admin이 아닌 manager만)
            if (worker?.isManager == true && worker?.isAdmin != true) ...[
              _buildFeatureCard(
                icon: Icons.warning_amber,
                iconBg: GxColors.warningBg,
                iconColor: GxColors.warning,
                title: '미종료 작업',
                subtitle: '${worker?.company ?? ''} 미종료 작업 확인 및 강제 종료',
                onTap: () => Navigator.pushNamed(context, '/manager-pending-tasks'),
              ),
              const SizedBox(height: 8),
            ],

            _buildFeatureCard(
              icon: Icons.notifications_active_outlined,
              iconBg: GxColors.infoBg,
              iconColor: GxColors.info,
              title: '알림',
              subtitle: '공정 누락 및 이상 알림 확인',
              badge: unreadCount > 0 ? unreadCount : null,
              onTap: () => Navigator.pushNamed(context, '/alerts'),
            ),
            const SizedBox(height: 8),

            // GST 작업자 / Admin 전용: PI/QI/SI 메뉴
            if (worker?.company == 'GST' || worker?.isAdmin == true) ...[
              _buildFeatureCard(
                icon: Icons.compress,
                iconBg: GxColors.successBg,
                iconColor: GxColors.success,
                title: 'PI 가압검사',
                subtitle: 'PI 가압검사 진행 제품 현황',
                onTap: () => Navigator.pushNamed(
                  context,
                  '/gst-products',
                  arguments: {'category': 'PI'},
                ),
              ),
              const SizedBox(height: 8),
              _buildFeatureCard(
                icon: Icons.verified,
                iconBg: const Color(0xFFF3E8FF),
                iconColor: const Color(0xFF7C3AED),
                title: 'QI 공정검사',
                subtitle: 'QI 공정검사 진행 제품 현황',
                onTap: () => Navigator.pushNamed(
                  context,
                  '/gst-products',
                  arguments: {'category': 'QI'},
                ),
              ),
              const SizedBox(height: 8),
              _buildFeatureCard(
                icon: Icons.local_shipping,
                iconBg: GxColors.accentSoft,
                iconColor: GxColors.accent,
                title: 'SI 마무리공정',
                subtitle: 'SI 마무리공정 진행 제품 현황',
                onTap: () => Navigator.pushNamed(
                  context,
                  '/gst-products',
                  arguments: {'category': 'SI'},
                ),
              ),
              const SizedBox(height: 8),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildFeatureCard({
    required IconData icon,
    required Color iconBg,
    required Color iconColor,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
    int? badge,
  }) {
    return Container(
      decoration: GxGlass.cardSm(radius: GxRadius.md),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(GxRadius.md),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Row(
              children: [
                Container(
                  width: 34,
                  height: 34,
                  decoration: BoxDecoration(
                    color: iconBg,
                    borderRadius: BorderRadius.circular(GxRadius.md),
                  ),
                  child: Icon(icon, size: 16, color: iconColor),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            title,
                            style: const TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w500,
                              color: GxColors.graphite,
                            ),
                          ),
                          if (badge != null) ...[
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: GxColors.danger,
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: Text(
                                '$badge',
                                style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                              ),
                            ),
                          ],
                        ],
                      ),
                      const SizedBox(height: 1),
                      Text(
                        subtitle,
                        style: const TextStyle(fontSize: 11, color: GxColors.steel),
                      ),
                    ],
                  ),
                ),
                const Icon(Icons.chevron_right, color: GxColors.silver, size: 20),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
