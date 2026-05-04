import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../../providers/alert_provider.dart';
import '../../models/alert_log.dart';
import '../../utils/design_system.dart';
import '../checklist/tm_checklist_screen.dart';
import '../checklist/mech_checklist_screen.dart';  // Sprint 63-FE

/// 알림 목록 화면
///
/// 관리자 및 모든 작업자가 접근 가능
/// 공정 경고, 비정상 duration, 작업자 승인/거부 등 시스템 알림 표시
class AlertListScreen extends ConsumerStatefulWidget {
  const AlertListScreen({Key? key}) : super(key: key);

  @override
  ConsumerState<AlertListScreen> createState() => _AlertListScreenState();
}

class _AlertListScreenState extends ConsumerState<AlertListScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isRefreshing = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);

    // 초기 알림 목록 로드
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadAlerts();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadAlerts() async {
    final isUnreadOnly = _tabController.index == 1;
    await ref.read(alertProvider.notifier).fetchAlerts(unreadOnly: isUnreadOnly);
  }

  Future<void> _handleRefresh() async {
    setState(() => _isRefreshing = true);
    await _loadAlerts();
    await ref.read(alertProvider.notifier).refreshUnreadCount();
    setState(() => _isRefreshing = false);
  }

  Future<void> _handleMarkAllAsRead() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.lg)),
        title: const Text('전체 읽음 처리', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: GxColors.charcoal)),
        content: const Text('모든 알림을 읽음 처리하시겠습니까?', style: TextStyle(fontSize: 14, color: GxColors.slate)),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('취소', style: TextStyle(color: GxColors.steel)),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('확인', style: TextStyle(color: GxColors.accent, fontWeight: FontWeight.w600)),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      final success = await ref.read(alertProvider.notifier).markAllAsRead();
      if (success && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('모든 알림을 읽음 처리했습니다.'),
            backgroundColor: GxColors.accent,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
          ),
        );
      }
    }
  }

  Future<void> _handleAlertTap(AlertLog alert) async {
    if (!alert.isRead) {
      await ref.read(alertProvider.notifier).markAsRead(alert.id);
    }

    if (!mounted) return;

    // CHECKLIST_TM_READY 알림 → TM 체크리스트 화면으로 이동
    if (alert.alertType == 'CHECKLIST_TM_READY') {
      final sn = alert.serialNumber;
      if (sn != null && sn.isNotEmpty) {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => TmChecklistScreen(serialNumber: sn),
          ),
        );
        return;
      }
    }

    // CHECKLIST_MECH_READY 알림 → MECH 체크리스트 화면 (Sprint 63-FE, A6-F1 정정)
    if (alert.alertType == 'CHECKLIST_MECH_READY') {
      final sn = alert.serialNumber;
      if (sn != null && sn.isNotEmpty) {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => MechChecklistScreen(serialNumber: sn),
          ),
        );
        return;
      }
    }

    // 나머지 알림 타입 → 상세 다이얼로그 표시
    showDialog(
      context: context,
      builder: (context) => _AlertDetailDialog(alert: alert),
    );
  }

  @override
  Widget build(BuildContext context) {
    final alertState = ref.watch(alertProvider);
    final alerts = alertState.sortedAlerts;

    // 탭별 필터링
    final filteredAlerts = _tabController.index == 1
        ? alerts.where((alert) => !alert.isRead).toList()
        : alerts;

    return Scaffold(
      backgroundColor: GxColors.cloud,
      appBar: AppBar(
        backgroundColor: GxColors.white,
        elevation: 0,
        foregroundColor: GxColors.charcoal,
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
            const Text('알림', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: GxColors.charcoal)),
          ],
        ),
        centerTitle: false,
        actions: [
          if (alertState.unreadCount > 0)
            IconButton(
              icon: const Icon(Icons.done_all, color: GxColors.accent, size: 22),
              onPressed: _handleMarkAllAsRead,
              tooltip: '전체 읽음',
            ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(49),
          child: Column(
            children: [
              Container(height: 1, color: GxColors.mist),
              TabBar(
                controller: _tabController,
                onTap: (_) => _loadAlerts(),
                labelColor: GxColors.accent,
                unselectedLabelColor: GxColors.steel,
                indicatorColor: GxColors.accent,
                indicatorWeight: 2,
                labelStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                unselectedLabelStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
                tabs: [
                  Tab(
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Text('전체'),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: GxColors.mist,
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(
                            '${alerts.length}',
                            style: const TextStyle(fontSize: 11, color: GxColors.slate),
                          ),
                        ),
                      ],
                    ),
                  ),
                  Tab(
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Text('안읽음'),
                        const SizedBox(width: 8),
                        if (alertState.unreadCount > 0)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: GxColors.danger,
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Text(
                              '${alertState.unreadCount}',
                              style: const TextStyle(fontSize: 11, color: Colors.white),
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
      ),
      body: RefreshIndicator(
        color: GxColors.accent,
        onRefresh: _handleRefresh,
        child: alertState.isLoading && !_isRefreshing
            ? Center(child: CircularProgressIndicator(color: GxColors.accent))
            : filteredAlerts.isEmpty
                ? _buildEmptyState()
                : ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: filteredAlerts.length,
                    itemBuilder: (context, index) {
                      final alert = filteredAlerts[index];
                      return _buildAlertTile(alert);
                    },
                  ),
      ),
    );
  }

  Widget _buildAlertTile(AlertLog alert) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: GxGlass.cardSm(radius: GxRadius.md).copyWith(
        color: alert.isRead ? GxGlass.cardBgLight : GxColors.accentSoft,
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(GxRadius.md),
        child: InkWell(
          onTap: () => _handleAlertTap(alert),
          borderRadius: BorderRadius.circular(GxRadius.md),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: _getAlertColor(alert.alertType).withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(GxRadius.md),
                  ),
                  child: Icon(
                    _getAlertIcon(alert.iconName),
                    color: _getAlertColor(alert.alertType),
                    size: 20,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              alert.message,
                              style: TextStyle(
                                fontWeight: alert.isRead ? FontWeight.w400 : FontWeight.w600,
                                fontSize: 13,
                                color: GxColors.charcoal,
                              ),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          if (!alert.isRead)
                            Container(
                              width: 8,
                              height: 8,
                              margin: const EdgeInsets.only(left: 8),
                              decoration: const BoxDecoration(
                                color: GxColors.accent,
                                shape: BoxShape.circle,
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          if (alert.serialNumber != null) ...[
                            Text(
                              alert.serialNumber!,
                              style: const TextStyle(fontSize: 11, color: GxColors.accent, fontWeight: FontWeight.w500),
                            ),
                            const SizedBox(width: 8),
                          ],
                          Text(
                            _formatDateTime(alert.createdAt),
                            style: const TextStyle(fontSize: 11, color: GxColors.steel),
                          ),
                        ],
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

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              color: GxColors.mist,
              borderRadius: BorderRadius.circular(GxRadius.lg),
            ),
            child: const Icon(Icons.notifications_none, size: 32, color: GxColors.silver),
          ),
          const SizedBox(height: 16),
          Text(
            _tabController.index == 1 ? '안읽은 알림이 없습니다' : '알림이 없습니다',
            style: const TextStyle(fontSize: 14, color: GxColors.steel),
          ),
        ],
      ),
    );
  }

  Color _getAlertColor(String alertType) {
    switch (alertType) {
      case 'DURATION_EXCEEDED':
      case 'REVERSE_COMPLETION':
        return GxColors.danger;
      case 'PROCESS_READY':
      case 'UNFINISHED_AT_CLOSING':
        return GxColors.warning;
      case 'WORKER_APPROVED':
        return GxColors.success;
      case 'WORKER_REJECTED':
        return GxColors.danger;
      case 'CHECKLIST_TM_READY':
      case 'CHECKLIST_MECH_READY':  // Sprint 63-FE
        return GxColors.accent;
      default:
        return GxColors.info;
    }
  }

  IconData _getAlertIcon(String iconName) {
    switch (iconName) {
      case 'notifications_active':
        return Icons.notifications_active;
      case 'warning':
        return Icons.warning;
      case 'timer_off':
        return Icons.timer_off;
      case 'error_outline':
        return Icons.error_outline;
      case 'qr_code_scanner':
        return Icons.qr_code_scanner;
      case 'check_circle':
        return Icons.check_circle;
      case 'cancel':
        return Icons.cancel;
      case 'checklist':
        return Icons.checklist;
      default:
        return Icons.info;
    }
  }

  String _formatDateTime(DateTime dateTime) {
    final local = dateTime.toLocal();
    final now = DateTime.now();
    final difference = now.difference(local);

    if (difference.inMinutes < 1) {
      return '방금 전';
    } else if (difference.inHours < 1) {
      return '${difference.inMinutes}분 전';
    } else if (difference.inDays < 1) {
      return '${difference.inHours}시간 전';
    } else if (difference.inDays < 7) {
      return '${difference.inDays}일 전';
    } else {
      return DateFormat('yyyy-MM-dd HH:mm').format(local);
    }
  }
}

/// 알림 상세 다이얼로그
class _AlertDetailDialog extends StatelessWidget {
  final AlertLog alert;

  const _AlertDetailDialog({required this.alert});

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.lg)),
      title: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: _getAlertColor(alert.alertType).withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(GxRadius.md),
            ),
            child: Icon(
              _getAlertIcon(alert.iconName),
              color: _getAlertColor(alert.alertType),
              size: 20,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              _getAlertTitle(alert.alertType),
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: GxColors.charcoal),
            ),
          ),
        ],
      ),
      content: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              alert.message,
              style: const TextStyle(fontSize: 14, height: 1.5, color: GxColors.graphite),
            ),
            const SizedBox(height: 16),
            const Divider(color: GxColors.mist),
            const SizedBox(height: 8),
            _buildInfoRow('시간', _formatFullDateTime(alert.createdAt)),
            if (alert.serialNumber != null)
              _buildInfoRow('시리얼 번호', alert.serialNumber!),
            if (alert.targetRole != null)
              _buildInfoRow('대상', alert.targetRole!),
            _buildInfoRow('읽음 상태', alert.isRead ? '읽음' : '안읽음'),
            if (alert.readAt != null)
              _buildInfoRow('읽은 시간', _formatFullDateTime(alert.readAt!)),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('닫기', style: TextStyle(color: GxColors.accent, fontWeight: FontWeight.w600)),
        ),
      ],
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 80,
            child: Text(label, style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 13, color: GxColors.slate)),
          ),
          Expanded(
            child: Text(value, style: const TextStyle(fontSize: 13, color: GxColors.charcoal)),
          ),
        ],
      ),
    );
  }

  String _getAlertTitle(String alertType) {
    switch (alertType) {
      case 'PROCESS_READY':
        return '다음 공정 준비';
      case 'UNFINISHED_AT_CLOSING':
        return '미완료 작업';
      case 'DURATION_EXCEEDED':
        return '비정상 소요시간';
      case 'REVERSE_COMPLETION':
        return '역순 완료 경고';
      case 'DUPLICATE_COMPLETION':
        return '중복 완료 경고';
      case 'LOCATION_QR_FAILED':
        return 'Location QR 실패';
      case 'WORKER_APPROVED':
        return '작업자 승인';
      case 'WORKER_REJECTED':
        return '작업자 거부';
      case 'CHECKLIST_TM_READY':
        return 'TM 체크리스트 검수 요청';
      case 'CHECKLIST_MECH_READY':  // Sprint 63-FE
        return 'MECH 체크리스트 1차 입력 가능';
      default:
        return '알림';
    }
  }

  Color _getAlertColor(String alertType) {
    switch (alertType) {
      case 'DURATION_EXCEEDED':
      case 'REVERSE_COMPLETION':
        return GxColors.danger;
      case 'PROCESS_READY':
      case 'UNFINISHED_AT_CLOSING':
        return GxColors.warning;
      case 'WORKER_APPROVED':
        return GxColors.success;
      case 'WORKER_REJECTED':
        return GxColors.danger;
      case 'CHECKLIST_TM_READY':
      case 'CHECKLIST_MECH_READY':  // Sprint 63-FE
        return GxColors.accent;
      default:
        return GxColors.info;
    }
  }

  IconData _getAlertIcon(String iconName) {
    switch (iconName) {
      case 'notifications_active':
        return Icons.notifications_active;
      case 'warning':
        return Icons.warning;
      case 'timer_off':
        return Icons.timer_off;
      case 'error_outline':
        return Icons.error_outline;
      case 'qr_code_scanner':
        return Icons.qr_code_scanner;
      case 'check_circle':
        return Icons.check_circle;
      case 'cancel':
        return Icons.cancel;
      case 'checklist':
        return Icons.checklist;
      default:
        return Icons.info;
    }
  }

  String _formatFullDateTime(DateTime dateTime) {
    return DateFormat('yyyy-MM-dd HH:mm:ss').format(dateTime.toLocal());
  }
}
