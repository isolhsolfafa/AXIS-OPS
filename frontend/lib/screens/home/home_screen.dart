// ignore_for_file: avoid_web_libraries_in_flutter
import 'dart:async';
import 'dart:html' as html;
import 'dart:js_util' as js_util;
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

  // 출퇴근 분류 (Sprint 17)
  String _selectedWorkSite = 'GST';
  String _selectedProductLine = 'SCR';

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
      // 마지막 IN 레코드의 work_site/product_line 복원
      final records = response['records'] as List<dynamic>? ?? [];
      String lastWorkSite = 'GST';
      String lastProductLine = 'SCR';
      for (final r in records.reversed) {
        if (r['check_type'] == 'in') {
          lastWorkSite = r['work_site'] as String? ?? 'GST';
          lastProductLine = r['product_line'] as String? ?? 'SCR';
          break;
        }
      }
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
        _selectedWorkSite = lastWorkSite;
        _selectedProductLine = lastProductLine;
      });
    } catch (e) {
      debugPrint('[HomeScreen] fetchAttendanceStatus error: $e');
    }
  }

  /// 현재 GPS 위치 조회 (Web Geolocation API — js_util 기반)
  ///
  /// 위치 권한 허용 시 {lat, lng} 반환, 거부 또는 오류 시 null 반환
  Future<Map<String, double>?> _getCurrentLocation() async {
    try {
      final geo = js_util.getProperty(
        js_util.getProperty(js_util.globalThis, 'navigator'),
        'geolocation',
      );
      if (geo == null) {
        debugPrint('[HomeScreen] Geolocation API not supported');
        return null;
      }

      final completer = Completer<Map<String, double>?>();

      final successCallback = js_util.allowInterop((dynamic pos) {
        if (completer.isCompleted) return;
        try {
          final coords = js_util.getProperty(pos as Object, 'coords');
          final lat = (js_util.getProperty(coords as Object, 'latitude') as num).toDouble();
          final lng = (js_util.getProperty(coords, 'longitude') as num).toDouble();
          completer.complete({'lat': lat, 'lng': lng});
        } catch (e) {
          completer.complete(null);
        }
      });

      final errorCallback = js_util.allowInterop((dynamic err) {
        if (completer.isCompleted) return;
        final code = js_util.getProperty(err as Object, 'code');
        final msg = js_util.getProperty(err, 'message');
        debugPrint('[HomeScreen] Geolocation error: $msg (code=$code)');
        completer.complete(null);
      });

      final options = js_util.jsify({'timeout': 10000, 'enableHighAccuracy': false});
      js_util.callMethod(geo as Object, 'getCurrentPosition', [successCallback, errorCallback, options]);

      // 12초 안에 응답 없으면 null 반환 (timeout 방어)
      return await completer.future.timeout(
        const Duration(seconds: 12),
        onTimeout: () => null,
      );
    } catch (e) {
      debugPrint('[HomeScreen] _getCurrentLocation exception: $e');
      return null;
    }
  }

  /// 출근/퇴근 처리
  Future<void> _handleAttendance() async {
    setState(() => _attendanceLoading = true);
    try {
      final apiService = ref.read(apiServiceProvider);
      final checkType = _attendanceStatus == AttendanceStatus.notCheckedIn ? 'in' : 'out';
      final Map<String, dynamic> body = {'check_type': checkType};
      // 출근 시만 work_site/product_line 전송 (퇴근 시 BE에서 자동 복사)
      if (checkType == 'in') {
        body['work_site'] = _selectedWorkSite;
        body['product_line'] = _selectedProductLine;
        // GPS 위치 조회 → latitude/longitude 추가 (권한 거부 시 서버가 geo_strict_mode에 따라 처리)
        final location = await _getCurrentLocation();
        if (location != null) {
          body['latitude'] = location['lat'];
          body['longitude'] = location['lng'];
        }
      }
      await apiService.post('/hr/attendance/check', data: body);
      await _fetchAttendanceStatus();
    } catch (e) {
      if (mounted) {
        final errMsg = e.toString().replaceFirst('Exception: ', '');
        // 위치 범위 벗어남 에러 처리
        if (errMsg.contains('OUT_OF_RANGE')) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: const Text('출근 불가: 허용된 위치 범위를 벗어났습니다.\n관리자에게 문의하세요.'),
              backgroundColor: GxColors.danger,
              behavior: SnackBarBehavior.floating,
              duration: const Duration(seconds: 5),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
            ),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('처리 실패: $errMsg'),
              backgroundColor: GxColors.danger,
              behavior: SnackBarBehavior.floating,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
            ),
          );
        }
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

    // 드롭다운 옵션 (work_site + product_line 조합)
    const siteLineOptions = <String, Map<String, String>>{
      'GST 공장 (SCR)': {'work_site': 'GST', 'product_line': 'SCR'},
      'GST 공장 (CHI)': {'work_site': 'GST', 'product_line': 'CHI'},
      '협력사 본사 (SCR)': {'work_site': 'HQ', 'product_line': 'SCR'},
      '협력사 본사 (CHI)': {'work_site': 'HQ', 'product_line': 'CHI'},
    };
    // 현재 선택값에 해당하는 레이블 찾기
    String currentLabel = siteLineOptions.entries
        .firstWhere(
          (e) => e.value['work_site'] == _selectedWorkSite && e.value['product_line'] == _selectedProductLine,
          orElse: () => siteLineOptions.entries.first,
        )
        .key;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: GxGlass.cardSm(radius: GxRadius.lg),
      child: Column(
        children: [
          Row(
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
                        const Text(
                          '근태',
                          style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: GxColors.graphite),
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
          // 출근 전 상태에서만 근무지/제품군 드롭다운 표시
          if (_attendanceStatus == AttendanceStatus.notCheckedIn) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              decoration: BoxDecoration(
                color: GxColors.cloud,
                borderRadius: BorderRadius.circular(GxRadius.sm),
                border: Border.all(color: GxColors.mist),
              ),
              child: DropdownButtonHideUnderline(
                child: DropdownButton<String>(
                  value: currentLabel,
                  isExpanded: true,
                  icon: const Icon(Icons.arrow_drop_down, color: GxColors.steel, size: 20),
                  style: const TextStyle(fontSize: 12, color: GxColors.graphite),
                  items: siteLineOptions.keys.map((label) {
                    return DropdownMenuItem<String>(value: label, child: Text(label));
                  }).toList(),
                  onChanged: (label) {
                    if (label != null && siteLineOptions.containsKey(label)) {
                      setState(() {
                        _selectedWorkSite = siteLineOptions[label]!['work_site']!;
                        _selectedProductLine = siteLineOptions[label]!['product_line']!;
                      });
                    }
                  },
                ),
              ),
            ),
          ],
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
            // 작업 진행현황 (Sprint 18) — 전체 사용자 표시
            _buildFeatureCard(
              icon: Icons.bar_chart_rounded,
              iconBg: const Color(0xFF0D9488).withValues(alpha: 0.08),
              iconColor: const Color(0xFF0D9488),
              title: worker?.company == 'GST' || worker?.isAdmin == true
                  ? '전사 작업 진행현황'
                  : '작업 진행현황',
              subtitle: '담당 S/N별 공정 진행률 조회',
              onTap: () => Navigator.pushNamed(context, '/sn-progress'),
            ),
            const SizedBox(height: 8),

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

            _buildFeatureCard(
              icon: Icons.campaign,
              iconBg: const Color(0xFFFEF3C7),
              iconColor: const Color(0xFFD97706),
              title: '공지사항',
              subtitle: '앱 업데이트 및 공지 확인',
              onTap: () => Navigator.pushNamed(context, '/notices'),
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
