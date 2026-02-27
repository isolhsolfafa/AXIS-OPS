import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/task_provider.dart';
import '../../providers/auth_provider.dart';
import '../../utils/design_system.dart';

/// Task 상세 화면
///
/// 선택된 Task의 상세 정보 표시 및 시작/완료/일시정지/재개 액션 제공
class TaskDetailScreen extends ConsumerStatefulWidget {
  const TaskDetailScreen({Key? key}) : super(key: key);

  @override
  ConsumerState<TaskDetailScreen> createState() => _TaskDetailScreenState();
}

class _TaskDetailScreenState extends ConsumerState<TaskDetailScreen> {
  bool _isActionLoading = false;

  @override
  Widget build(BuildContext context) {
    final taskState = ref.watch(taskProvider);
    final authState = ref.watch(authProvider);
    final task = taskState.selectedTask;
    final currentProduct = taskState.currentProduct;
    final workerId = authState.currentWorkerId ?? 0;

    if (task == null) {
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
              const Text('Task 상세', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: GxColors.charcoal)),
            ],
          ),
          centerTitle: false,
          bottom: PreferredSize(
            preferredSize: const Size.fromHeight(1),
            child: Container(height: 1, color: GxColors.mist),
          ),
        ),
        body: const Center(
          child: Text('Task 정보를 불러올 수 없습니다.', style: TextStyle(color: GxColors.steel, fontSize: 14)),
        ),
      );
    }

    Color statusColor;
    Color statusBg;
    IconData statusIcon;
    String statusText;

    if (task.isPaused) {
      statusColor = GxColors.warning;
      statusBg = GxColors.warningBg;
      statusIcon = Icons.pause_circle;
      statusText = '일시정지';
    } else {
      switch (task.status) {
        case 'completed':
          statusColor = GxColors.success;
          statusBg = GxColors.successBg;
          statusIcon = Icons.check_circle;
          statusText = '완료';
          break;
        case 'in_progress':
          statusColor = GxColors.accent;
          statusBg = GxColors.accentSoft;
          statusIcon = Icons.play_circle;
          statusText = '진행 중';
          break;
        default:
          statusColor = GxColors.steel;
          statusBg = GxColors.mist;
          statusIcon = Icons.radio_button_unchecked;
          statusText = '대기';
      }
    }

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
            const Text('Task 상세', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: GxColors.charcoal)),
          ],
        ),
        centerTitle: false,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: GxColors.mist),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Task 상태 표시
              Container(
                padding: const EdgeInsets.all(20),
                decoration: GxGlass.cardSm(radius: GxRadius.lg),
                child: Column(
                  children: [
                    Container(
                      width: 56,
                      height: 56,
                      decoration: BoxDecoration(
                        color: statusBg,
                        borderRadius: BorderRadius.circular(GxRadius.lg),
                      ),
                      child: Icon(statusIcon, size: 32, color: statusColor),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      task.taskName,
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: GxColors.charcoal),
                    ),
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                      decoration: BoxDecoration(
                        color: statusBg,
                        borderRadius: BorderRadius.circular(GxRadius.sm),
                      ),
                      child: Text(
                        statusText,
                        style: TextStyle(color: statusColor, fontWeight: FontWeight.w600, fontSize: 13),
                      ),
                    ),
                    // 일시정지 경과 시간 표시
                    if (task.isPaused && task.totalPauseMinutes > 0) ...[
                      const SizedBox(height: 8),
                      Text(
                        '누적 일시정지: ${_formatMinutes(task.totalPauseMinutes)}',
                        style: const TextStyle(fontSize: 12, color: GxColors.steel),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // Task 정보
              _buildSectionTitle('Task 정보'),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: GxGlass.cardSm(radius: GxRadius.lg),
                child: Column(
                  children: [
                    _buildInfoRow('Task ID', task.taskId),
                    const Divider(height: 20, color: GxColors.mist),
                    _buildInfoRow('카테고리', task.taskCategory),
                    const Divider(height: 20, color: GxColors.mist),
                    _buildInfoRow('적용 여부', task.isApplicable ? '적용' : '미적용'),
                    const Divider(height: 20, color: GxColors.mist),
                    _buildInfoRow('Location QR 확인', task.locationQrVerified ? '확인됨' : '미확인'),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // 제품 정보
              if (currentProduct != null) ...[
                _buildSectionTitle('제품 정보'),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: GxGlass.cardSm(radius: GxRadius.lg),
                  child: Column(
                    children: [
                      _buildInfoRow('시리얼 번호', currentProduct.serialNumber),
                      const Divider(height: 20, color: GxColors.mist),
                      _buildInfoRow('QR 문서 ID', currentProduct.qrDocId),
                      const Divider(height: 20, color: GxColors.mist),
                      _buildInfoRow('모델', currentProduct.model),
                      if (currentProduct.locationQrId != null) ...[
                        const Divider(height: 20, color: GxColors.mist),
                        _buildInfoRow('위치', currentProduct.locationQrId!),
                      ],
                      if (currentProduct.mechPartner != null) ...[
                        const Divider(height: 20, color: GxColors.mist),
                        _buildInfoRow('기구 협력사', currentProduct.mechPartner!),
                      ],
                      if (currentProduct.moduleOutsourcing != null) ...[
                        const Divider(height: 20, color: GxColors.mist),
                        _buildInfoRow('모듈 외주', currentProduct.moduleOutsourcing!),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 16),
              ],

              // 작업 시간 정보
              _buildSectionTitle('작업 시간'),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: GxGlass.cardSm(radius: GxRadius.lg),
                child: Column(
                  children: [
                    if (task.startedAt != null)
                      _buildInfoRow('시작 시간', _formatFullDateTime(task.startedAt!)),
                    if (task.completedAt != null) ...[
                      if (task.startedAt != null) const Divider(height: 20, color: GxColors.mist),
                      _buildInfoRow('완료 시간', _formatFullDateTime(task.completedAt!)),
                      const Divider(height: 20, color: GxColors.mist),
                      _buildInfoRow(
                        '소요 시간',
                        task.durationFormatted,
                        valueColor: task.hasAbnormalDuration ? GxColors.danger : GxColors.charcoal,
                      ),
                      if (task.hasAbnormalDuration)
                        Padding(
                          padding: const EdgeInsets.only(top: 10),
                          child: Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: GxColors.dangerBg,
                              borderRadius: BorderRadius.circular(GxRadius.sm),
                            ),
                            child: const Row(
                              children: [
                                Icon(Icons.warning, size: 16, color: GxColors.danger),
                                SizedBox(width: 6),
                                Expanded(
                                  child: Text(
                                    '비정상 작업 시간 (14시간 초과)',
                                    style: TextStyle(fontSize: 12, color: GxColors.danger, fontWeight: FontWeight.w600),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                    ],
                    if (task.totalPauseMinutes > 0) ...[
                      if (task.startedAt != null || task.completedAt != null)
                        const Divider(height: 20, color: GxColors.mist),
                      _buildInfoRow('누적 일시정지', _formatMinutes(task.totalPauseMinutes)),
                    ],
                    if (task.startedAt == null && task.completedAt == null)
                      const Center(
                        child: Text(
                          '아직 시작하지 않은 작업입니다.',
                          style: TextStyle(fontSize: 13, color: GxColors.steel),
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // 액션 버튼
              if (_isActionLoading)
                const Center(child: CircularProgressIndicator(color: GxColors.accent, strokeWidth: 2))
              else if (task.status == 'pending')
                _buildStartButton(task.id, workerId)
              else if (task.status == 'in_progress' && task.isPaused)
                _buildResumeRow(task.id)
              else if (task.status == 'in_progress' && !task.isPaused)
                _buildInProgressRow(task.id, workerId)
              else if (task.status == 'completed')
                _buildCompletedBadge(),
            ],
          ),
        ),
      ),
    );
  }

  // ===================== 액션 버튼 빌더 =====================

  Widget _buildStartButton(int taskId, int workerId) {
    return Container(
      height: 48,
      decoration: BoxDecoration(
        gradient: GxGradients.accentButton,
        borderRadius: BorderRadius.circular(GxRadius.sm),
        boxShadow: [BoxShadow(color: GxColors.accent.withValues(alpha: 0.35), blurRadius: 16, offset: const Offset(0, 4))],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => _handleStartTask(taskId, workerId),
          borderRadius: BorderRadius.circular(GxRadius.sm),
          child: Center(child: Row(mainAxisAlignment: MainAxisAlignment.center, children: const [
            Icon(Icons.play_arrow, size: 20, color: Colors.white),
            SizedBox(width: 8),
            Text('작업 시작', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Colors.white)),
          ])),
        ),
      ),
    );
  }

  /// 진행 중 (미일시정지): [일시정지] [작업 완료]
  Widget _buildInProgressRow(int taskId, int workerId) {
    return Row(
      children: [
        // 일시정지 버튼 (gray/mist bg)
        Expanded(
          child: Container(
            height: 48,
            decoration: BoxDecoration(
              color: GxColors.cloud,
              borderRadius: BorderRadius.circular(GxRadius.sm),
              border: Border.all(color: GxColors.mist, width: 1.5),
            ),
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: () => _handlePause(taskId),
                borderRadius: BorderRadius.circular(GxRadius.sm),
                child: Center(child: Row(mainAxisAlignment: MainAxisAlignment.center, children: const [
                  Icon(Icons.pause_circle, size: 20, color: GxColors.slate),
                  SizedBox(width: 6),
                  Text('일시정지', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: GxColors.slate)),
                ])),
              ),
            ),
          ),
        ),
        const SizedBox(width: 12),
        // 작업 완료 버튼 (green gradient)
        Expanded(
          child: Container(
            height: 48,
            decoration: BoxDecoration(
              gradient: LinearGradient(colors: [GxColors.success, GxColors.success.withValues(alpha: 0.8)]),
              borderRadius: BorderRadius.circular(GxRadius.sm),
              boxShadow: [BoxShadow(color: GxColors.success.withValues(alpha: 0.35), blurRadius: 16, offset: const Offset(0, 4))],
            ),
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: () => _handleCompleteTask(taskId, workerId),
                borderRadius: BorderRadius.circular(GxRadius.sm),
                child: Center(child: Row(mainAxisAlignment: MainAxisAlignment.center, children: const [
                  Icon(Icons.check_circle, size: 20, color: Colors.white),
                  SizedBox(width: 6),
                  Text('작업 완료', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Colors.white)),
                ])),
              ),
            ),
          ),
        ),
      ],
    );
  }

  /// 일시정지 상태: [재개] [완료(비활성화)]
  Widget _buildResumeRow(int taskId) {
    return Row(
      children: [
        // 재개 버튼 (accent gradient)
        Expanded(
          child: Container(
            height: 48,
            decoration: BoxDecoration(
              gradient: GxGradients.accentButton,
              borderRadius: BorderRadius.circular(GxRadius.sm),
              boxShadow: [BoxShadow(color: GxColors.accent.withValues(alpha: 0.35), blurRadius: 16, offset: const Offset(0, 4))],
            ),
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: () => _handleResume(taskId),
                borderRadius: BorderRadius.circular(GxRadius.sm),
                child: Center(child: Row(mainAxisAlignment: MainAxisAlignment.center, children: const [
                  Icon(Icons.play_circle, size: 20, color: Colors.white),
                  SizedBox(width: 6),
                  Text('재개', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Colors.white)),
                ])),
              ),
            ),
          ),
        ),
        const SizedBox(width: 12),
        // 완료 버튼 비활성화 (gray)
        Expanded(
          child: Container(
            height: 48,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: GxColors.mist,
              borderRadius: BorderRadius.circular(GxRadius.sm),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: const [
                Icon(Icons.check_circle_outline, size: 20, color: GxColors.silver),
                SizedBox(width: 6),
                Text('작업 완료', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: GxColors.silver)),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildCompletedBadge() {
    return Container(
      height: 48,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: GxColors.successBg,
        borderRadius: BorderRadius.circular(GxRadius.sm),
        border: Border.all(color: GxColors.success.withValues(alpha: 0.3), width: 1.5),
      ),
      child: const Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.check_circle, color: GxColors.success, size: 20),
          SizedBox(width: 8),
          Text('작업 완료됨', style: TextStyle(color: GxColors.success, fontWeight: FontWeight.w600, fontSize: 15)),
        ],
      ),
    );
  }

  // ===================== 액션 핸들러 =====================

  Future<void> _handleStartTask(int taskId, int workerId) async {
    setState(() => _isActionLoading = true);
    final taskNotifier = ref.read(taskProvider.notifier);
    final success = await taskNotifier.startTask(taskId: taskId, workerId: workerId);
    if (mounted) {
      setState(() => _isActionLoading = false);
      _showSnack(success, '작업을 시작했습니다.', '작업 시작에 실패했습니다.');
    }
  }

  Future<void> _handleCompleteTask(int taskId, int workerId) async {
    setState(() => _isActionLoading = true);
    final taskNotifier = ref.read(taskProvider.notifier);
    final success = await taskNotifier.completeTask(taskId: taskId, workerId: workerId);
    if (mounted) {
      setState(() => _isActionLoading = false);
      if (success) {
        _showSnack(true, '작업을 완료했습니다.', '');
        Navigator.pop(context);
      } else {
        _showSnack(false, '', '작업 완료에 실패했습니다.');
      }
    }
  }

  Future<void> _handlePause(int taskId) async {
    setState(() => _isActionLoading = true);
    final taskNotifier = ref.read(taskProvider.notifier);
    final success = await taskNotifier.pauseTask(taskDetailId: taskId);
    if (mounted) {
      setState(() => _isActionLoading = false);
      _showSnack(success, '작업이 일시정지되었습니다.', '일시정지에 실패했습니다.');
    }
  }

  Future<void> _handleResume(int taskId) async {
    setState(() => _isActionLoading = true);
    final taskNotifier = ref.read(taskProvider.notifier);
    final success = await taskNotifier.resumeTask(taskDetailId: taskId);
    if (mounted) {
      setState(() => _isActionLoading = false);
      _showSnack(success, '작업을 재개했습니다.', '재개에 실패했습니다.');
    }
  }

  void _showSnack(bool success, String successMsg, String errorMsg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(success ? successMsg : (ref.read(taskProvider).errorMessage ?? errorMsg)),
        backgroundColor: success ? GxColors.accent : GxColors.danger,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
      ),
    );
  }

  // ===================== 헬퍼 위젯 =====================

  Widget _buildSectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.only(left: 4),
      child: Text(
        title,
        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: GxColors.graphite),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value, {Color? valueColor}) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 110,
          child: Text(
            label,
            style: const TextStyle(fontSize: 13, color: GxColors.slate, fontWeight: FontWeight.w500),
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: TextStyle(fontSize: 13, color: valueColor ?? GxColors.charcoal, fontWeight: FontWeight.w500),
          ),
        ),
      ],
    );
  }

  String _formatFullDateTime(DateTime dateTime) {
    final local = dateTime.toLocal();
    return '${local.year}년 ${local.month}월 ${local.day}일 '
        '${local.hour.toString().padLeft(2, '0')}:'
        '${local.minute.toString().padLeft(2, '0')}';
  }

  String _formatMinutes(int minutes) {
    final h = minutes ~/ 60;
    final m = minutes % 60;
    if (h > 0) return '${h}시간 ${m}분';
    return '${m}분';
  }
}
