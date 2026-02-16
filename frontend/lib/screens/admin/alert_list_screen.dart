import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../../providers/alert_provider.dart';
import '../../models/alert_log.dart';

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
        title: const Text('전체 읽음 처리'),
        content: const Text('모든 알림을 읽음 처리하시겠습니까?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('취소'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('확인'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      final success = await ref.read(alertProvider.notifier).markAllAsRead();
      if (success && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('모든 알림을 읽음 처리했습니다.')),
        );
      }
    }
  }

  Future<void> _handleAlertTap(AlertLog alert) async {
    if (!alert.isRead) {
      await ref.read(alertProvider.notifier).markAsRead(alert.id);
    }

    // 알림 상세 다이얼로그 표시
    if (mounted) {
      showDialog(
        context: context,
        builder: (context) => _AlertDetailDialog(alert: alert),
      );
    }
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
      appBar: AppBar(
        title: const Text('알림'),
        centerTitle: true,
        bottom: TabBar(
          controller: _tabController,
          onTap: (_) => _loadAlerts(),
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
                      color: Colors.grey.shade300,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      '${alerts.length}',
                      style: const TextStyle(fontSize: 12),
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
                        color: Colors.red,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        '${alertState.unreadCount}',
                        style: const TextStyle(
                          fontSize: 12,
                          color: Colors.white,
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          if (alertState.unreadCount > 0)
            IconButton(
              icon: const Icon(Icons.done_all),
              onPressed: _handleMarkAllAsRead,
              tooltip: '전체 읽음',
            ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _handleRefresh,
        child: alertState.isLoading && !_isRefreshing
            ? const Center(child: CircularProgressIndicator())
            : filteredAlerts.isEmpty
                ? _buildEmptyState()
                : ListView.separated(
                    padding: const EdgeInsets.all(8),
                    itemCount: filteredAlerts.length,
                    separatorBuilder: (context, index) => const Divider(height: 1),
                    itemBuilder: (context, index) {
                      final alert = filteredAlerts[index];
                      return _buildAlertTile(alert);
                    },
                  ),
      ),
    );
  }

  Widget _buildAlertTile(AlertLog alert) {
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      leading: Container(
        width: 48,
        height: 48,
        decoration: BoxDecoration(
          color: _getAlertColor(alert.alertType).withOpacity(0.1),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Icon(
          _getAlertIcon(alert.iconName),
          color: _getAlertColor(alert.alertType),
        ),
      ),
      title: Row(
        children: [
          Expanded(
            child: Text(
              alert.message,
              style: TextStyle(
                fontWeight: alert.isRead ? FontWeight.normal : FontWeight.bold,
                fontSize: 14,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (!alert.isRead)
            Container(
              width: 8,
              height: 8,
              decoration: const BoxDecoration(
                color: Colors.red,
                shape: BoxShape.circle,
              ),
            ),
        ],
      ),
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 4),
          if (alert.serialNumber != null)
            Text(
              '시리얼: ${alert.serialNumber}',
              style: const TextStyle(fontSize: 12),
            ),
          Text(
            _formatDateTime(alert.createdAt),
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey[600],
            ),
          ),
        ],
      ),
      trailing: Icon(
        Icons.chevron_right,
        color: Colors.grey[400],
      ),
      onTap: () => _handleAlertTap(alert),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.notifications_none,
            size: 80,
            color: Colors.grey[300],
          ),
          const SizedBox(height: 16),
          Text(
            _tabController.index == 1 ? '안읽은 알림이 없습니다' : '알림이 없습니다',
            style: TextStyle(
              fontSize: 16,
              color: Colors.grey[600],
            ),
          ),
        ],
      ),
    );
  }

  Color _getAlertColor(String alertType) {
    switch (alertType) {
      case 'DURATION_EXCEEDED':
      case 'REVERSE_COMPLETION':
        return Colors.red;
      case 'PROCESS_READY':
      case 'UNFINISHED_AT_CLOSING':
        return Colors.orange;
      case 'WORKER_APPROVED':
        return Colors.green;
      case 'WORKER_REJECTED':
        return Colors.red;
      default:
        return Colors.blue;
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
      default:
        return Icons.info;
    }
  }

  String _formatDateTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);

    if (difference.inMinutes < 1) {
      return '방금 전';
    } else if (difference.inHours < 1) {
      return '${difference.inMinutes}분 전';
    } else if (difference.inDays < 1) {
      return '${difference.inHours}시간 전';
    } else if (difference.inDays < 7) {
      return '${difference.inDays}일 전';
    } else {
      return DateFormat('yyyy-MM-dd HH:mm').format(dateTime);
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
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      title: Row(
        children: [
          Icon(
            _getAlertIcon(alert.iconName),
            color: _getAlertColor(alert.alertType),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              _getAlertTitle(alert.alertType),
              style: const TextStyle(fontSize: 18),
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
              style: const TextStyle(fontSize: 16, height: 1.5),
            ),
            const SizedBox(height: 16),
            const Divider(),
            const SizedBox(height: 8),
            _buildInfoRow('시간', _formatFullDateTime(alert.createdAt)),
            if (alert.serialNumber != null)
              _buildInfoRow('시리얼 번호', alert.serialNumber!),
            if (alert.qrDocId != null) _buildInfoRow('QR 문서', alert.qrDocId!),
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
          child: const Text('닫기'),
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
            child: Text(
              label,
              style: const TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 14,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontSize: 14),
            ),
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
      default:
        return '알림';
    }
  }

  Color _getAlertColor(String alertType) {
    switch (alertType) {
      case 'DURATION_EXCEEDED':
      case 'REVERSE_COMPLETION':
        return Colors.red;
      case 'PROCESS_READY':
      case 'UNFINISHED_AT_CLOSING':
        return Colors.orange;
      case 'WORKER_APPROVED':
        return Colors.green;
      case 'WORKER_REJECTED':
        return Colors.red;
      default:
        return Colors.blue;
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
      default:
        return Icons.info;
    }
  }

  String _formatFullDateTime(DateTime dateTime) {
    return DateFormat('yyyy-MM-dd HH:mm:ss').format(dateTime);
  }
}
