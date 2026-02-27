import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/task_provider.dart';
import '../../providers/auth_provider.dart';
import '../../models/task_item.dart';
import '../../utils/design_system.dart';
import 'task_detail_screen.dart';

/// Task 관리 화면
///
/// QR 스캔 후 제품의 Task 목록을 표시하고 시작/완료 터치 UI 제공
class TaskManagementScreen extends ConsumerStatefulWidget {
  const TaskManagementScreen({Key? key}) : super(key: key);

  @override
  ConsumerState<TaskManagementScreen> createState() =>
      _TaskManagementScreenState();
}

class _TaskManagementScreenState extends ConsumerState<TaskManagementScreen> {
  String _filterStatus = 'all'; // all, pending, in_progress, completed

  @override
  Widget build(BuildContext context) {
    final taskState = ref.watch(taskProvider);
    final authState = ref.watch(authProvider);
    final currentProduct = taskState.currentProduct;
    final tasks = taskState.tasks;

    // 필터링된 Task 목록 (is_applicable=false인 비활성 task 제외)
    final filteredTasks = tasks.where((task) {
      if (!task.isApplicable) return false;
      if (_filterStatus == 'all') return true;
      return task.status == _filterStatus;
    }).toList();

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
            Flexible(
              child: Text(
                currentProduct?.serialNumber ?? 'Task 관리',
                style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: GxColors.charcoal),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        centerTitle: false,
        actions: [
          PopupMenuButton<String>(
            icon: const Icon(Icons.filter_list, color: GxColors.slate, size: 22),
            onSelected: (value) {
              setState(() {
                _filterStatus = value;
              });
            },
            itemBuilder: (context) => [
              const PopupMenuItem(value: 'all', child: Text('전체')),
              const PopupMenuItem(value: 'pending', child: Text('대기 중')),
              const PopupMenuItem(value: 'in_progress', child: Text('진행 중')),
              const PopupMenuItem(value: 'completed', child: Text('완료')),
            ],
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: GxColors.mist),
        ),
      ),
      body: taskState.isLoading
          ? Center(child: CircularProgressIndicator(color: GxColors.accent))
          : SafeArea(
              child: Column(
                children: [
                  // 제품 정보 헤더
                  if (currentProduct != null)
                    Container(
                      width: double.infinity,
                      margin: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                      padding: const EdgeInsets.all(16),
                      decoration: GxGlass.cardSm(radius: GxRadius.lg),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            currentProduct.serialNumber,
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w600,
                              color: GxColors.charcoal,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '모델: ${currentProduct.model} | QR: ${currentProduct.qrDocId}',
                            style: const TextStyle(fontSize: 13, color: GxColors.slate),
                          ),
                          if (currentProduct.locationQrId != null) ...[
                            const SizedBox(height: 4),
                            Row(
                              children: [
                                const Icon(Icons.location_on, size: 16, color: GxColors.accent),
                                const SizedBox(width: 4),
                                Text(
                                  currentProduct.locationQrId!,
                                  style: const TextStyle(fontSize: 13, color: GxColors.accent, fontWeight: FontWeight.w500),
                                ),
                              ],
                            ),
                          ],
                        ],
                      ),
                    ),

                  // 진행률 표시
                  Container(
                    margin: const EdgeInsets.all(16),
                    padding: const EdgeInsets.all(16),
                    decoration: GxGlass.cardSm(radius: GxRadius.lg),
                    child: Column(
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Builder(builder: (_) {
                              final applicable = tasks.where((t) => t.isApplicable).toList();
                              final completed = applicable.where((t) => t.status == 'completed').length;
                              final total = applicable.length;
                              final progress = total > 0 ? completed / total : 0.0;
                              return Text(
                                '진행률: ${(progress * 100).toStringAsFixed(0)}%',
                                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: GxColors.charcoal),
                              );
                            }),
                            Builder(builder: (_) {
                              final applicable = tasks.where((t) => t.isApplicable).toList();
                              final completed = applicable.where((t) => t.status == 'completed').length;
                              return Text(
                                '$completed/${applicable.length}',
                                style: const TextStyle(fontSize: 14, color: GxColors.slate),
                              );
                            }),
                          ],
                        ),
                        const SizedBox(height: 10),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(4),
                          child: Builder(builder: (_) {
                            final applicable = tasks.where((t) => t.isApplicable).toList();
                            final completed = applicable.where((t) => t.status == 'completed').length;
                            final total = applicable.length;
                            final progress = total > 0 ? completed / total : 0.0;
                            return LinearProgressIndicator(
                              value: progress,
                              minHeight: 8,
                              backgroundColor: GxColors.mist,
                              color: GxColors.accent,
                            );
                          }),
                        ),
                      ],
                    ),
                  ),

                  // Task 목록
                  Expanded(
                    child: filteredTasks.isEmpty
                        ? Center(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.task_alt, size: 64, color: GxColors.silver),
                                const SizedBox(height: 16),
                                Text(
                                  _filterStatus == 'all' ? 'Task가 없습니다.' : '필터에 맞는 Task가 없습니다.',
                                  style: const TextStyle(fontSize: 14, color: GxColors.steel),
                                ),
                              ],
                            ),
                          )
                        : ListView.builder(
                            padding: const EdgeInsets.symmetric(horizontal: 16),
                            itemCount: filteredTasks.length,
                            itemBuilder: (context, index) {
                              final task = filteredTasks[index];
                              return _buildTaskCard(context, task, authState.currentWorkerId ?? 0);
                            },
                          ),
                  ),
                ],
              ),
            ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          ref.read(taskProvider.notifier).clearCurrentProduct();
          Navigator.pushReplacementNamed(context, '/qr-scan');
        },
        tooltip: '새 QR 스캔',
        backgroundColor: GxColors.accent,
        foregroundColor: Colors.white,
        elevation: 2,
        child: const Icon(Icons.qr_code_scanner),
      ),
    );
  }

  Widget _buildTaskCard(BuildContext context, TaskItem task, int workerId) {
    Color statusColor;
    Color statusBg;
    IconData statusIcon;
    String statusText;

    // 일시정지 상태 우선 처리
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

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: GxGlass.cardSm(radius: GxRadius.lg),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(GxRadius.lg),
        child: InkWell(
          onTap: () {
            ref.read(taskProvider.notifier).selectTask(task);
            Navigator.push(
              context,
              MaterialPageRoute(builder: (context) => const TaskDetailScreen()),
            );
          },
          borderRadius: BorderRadius.circular(GxRadius.lg),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(statusIcon, color: statusColor, size: 22),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        task.taskName,
                        style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: GxColors.charcoal),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: statusBg,
                        borderRadius: BorderRadius.circular(GxRadius.sm),
                      ),
                      child: Text(
                        statusText,
                        style: TextStyle(fontSize: 11, color: statusColor, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Text('ID: ${task.taskId}', style: const TextStyle(fontSize: 12, color: GxColors.steel)),
                    const SizedBox(width: 16),
                    Text('카테고리: ${task.taskCategory}', style: const TextStyle(fontSize: 12, color: GxColors.steel)),
                  ],
                ),
                if (task.startedAt != null) ...[
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      const Icon(Icons.access_time, size: 14, color: GxColors.steel),
                      const SizedBox(width: 4),
                      Text('시작: ${_formatDateTime(task.startedAt!)}', style: const TextStyle(fontSize: 12, color: GxColors.steel)),
                    ],
                  ),
                ],
                if (task.completedAt != null) ...[
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      const Icon(Icons.check, size: 14, color: GxColors.steel),
                      const SizedBox(width: 4),
                      Text('완료: ${_formatDateTime(task.completedAt!)}', style: const TextStyle(fontSize: 12, color: GxColors.steel)),
                      const SizedBox(width: 8),
                      Text(
                        '소요: ${task.durationFormatted}',
                        style: TextStyle(
                          fontSize: 12,
                          color: task.hasAbnormalDuration ? GxColors.danger : GxColors.steel,
                          fontWeight: task.hasAbnormalDuration ? FontWeight.w600 : FontWeight.normal,
                        ),
                      ),
                    ],
                  ),
                ],
                const SizedBox(height: 12),
                Row(
                  children: [
                    if (task.status == 'pending')
                      Expanded(
                        child: SizedBox(
                          height: 38,
                          child: Container(
                            decoration: BoxDecoration(
                              gradient: GxGradients.accentButton,
                              borderRadius: BorderRadius.circular(GxRadius.sm),
                            ),
                            child: Material(
                              color: Colors.transparent,
                              child: InkWell(
                                onTap: () => _handleStartTask(task.id, workerId),
                                borderRadius: BorderRadius.circular(GxRadius.sm),
                                child: Center(
                                  child: Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: const [
                                      Icon(Icons.play_arrow, size: 18, color: Colors.white),
                                      SizedBox(width: 4),
                                      Text('시작', style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    // 일시정지 상태: "일시정지" 배지 + "재개" 버튼
                    if (task.status == 'in_progress' && task.isPaused) ...[
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        margin: const EdgeInsets.only(right: 8),
                        decoration: BoxDecoration(
                          color: GxColors.warningBg,
                          borderRadius: BorderRadius.circular(GxRadius.sm),
                          border: Border.all(color: GxColors.warning.withValues(alpha: 0.4), width: 1),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: const [
                            Icon(Icons.pause_circle, size: 14, color: GxColors.warning),
                            SizedBox(width: 4),
                            Text('일시정지', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: GxColors.warning)),
                          ],
                        ),
                      ),
                      Expanded(
                        child: SizedBox(
                          height: 38,
                          child: Container(
                            decoration: BoxDecoration(
                              gradient: GxGradients.accentButton,
                              borderRadius: BorderRadius.circular(GxRadius.sm),
                            ),
                            child: Material(
                              color: Colors.transparent,
                              child: InkWell(
                                onTap: () => _handleResumeTask(task.id),
                                borderRadius: BorderRadius.circular(GxRadius.sm),
                                child: Center(
                                  child: Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: const [
                                      Icon(Icons.play_circle, size: 18, color: Colors.white),
                                      SizedBox(width: 4),
                                      Text('재개', style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                    // 진행 중 (미일시정지): 일시정지 + 완료 버튼
                    if (task.status == 'in_progress' && !task.isPaused) ...[
                      // 일시정지 버튼
                      SizedBox(
                        width: 38,
                        height: 38,
                        child: Container(
                          decoration: BoxDecoration(
                            color: GxColors.cloud,
                            borderRadius: BorderRadius.circular(GxRadius.sm),
                            border: Border.all(color: GxColors.mist, width: 1.5),
                          ),
                          child: Material(
                            color: Colors.transparent,
                            child: InkWell(
                              onTap: () => _handlePauseTask(task.id),
                              borderRadius: BorderRadius.circular(GxRadius.sm),
                              child: const Center(
                                child: Icon(Icons.pause, size: 18, color: GxColors.slate),
                              ),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      // 완료 버튼
                      Expanded(
                        child: SizedBox(
                          height: 38,
                          child: Container(
                            decoration: BoxDecoration(
                              gradient: const LinearGradient(colors: [Color(0xFF10B981), Color(0xFF34D399)]),
                              borderRadius: BorderRadius.circular(GxRadius.sm),
                            ),
                            child: Material(
                              color: Colors.transparent,
                              child: InkWell(
                                onTap: () => _handleCompleteTask(task.id, workerId),
                                borderRadius: BorderRadius.circular(GxRadius.sm),
                                child: Center(
                                  child: Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: const [
                                      Icon(Icons.check_circle, size: 18, color: Colors.white),
                                      SizedBox(width: 4),
                                      Text('완료', style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                    if (task.status == 'completed')
                      Expanded(
                        child: Container(
                          height: 38,
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            color: GxColors.successBg,
                            borderRadius: BorderRadius.circular(GxRadius.sm),
                          ),
                          child: const Text(
                            '작업 완료됨',
                            style: TextStyle(color: GxColors.success, fontWeight: FontWeight.w600, fontSize: 13),
                          ),
                        ),
                      ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _handleStartTask(int taskId, int workerId) async {
    final taskNotifier = ref.read(taskProvider.notifier);
    final success = await taskNotifier.startTask(
      taskId: taskId,
      workerId: workerId,
    );

    if (mounted) {
      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('작업을 시작했습니다.'),
            backgroundColor: GxColors.accent,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
          ),
        );
      } else {
        final errorMessage = ref.read(taskProvider).errorMessage;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(errorMessage ?? '작업 시작에 실패했습니다.'),
            backgroundColor: GxColors.danger,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
          ),
        );
      }
    }
  }

  Future<void> _handlePauseTask(int taskId) async {
    final taskNotifier = ref.read(taskProvider.notifier);
    final success = await taskNotifier.pauseTask(taskDetailId: taskId);

    if (mounted) {
      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('작업이 일시정지되었습니다.'),
            backgroundColor: GxColors.warning,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
          ),
        );
      } else {
        final errorMessage = ref.read(taskProvider).errorMessage;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(errorMessage ?? '일시정지에 실패했습니다.'),
            backgroundColor: GxColors.danger,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
          ),
        );
      }
    }
  }

  Future<void> _handleResumeTask(int taskId) async {
    final taskNotifier = ref.read(taskProvider.notifier);
    final success = await taskNotifier.resumeTask(taskDetailId: taskId);

    if (mounted) {
      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('작업을 재개했습니다.'),
            backgroundColor: GxColors.accent,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
          ),
        );
      } else {
        final errorMessage = ref.read(taskProvider).errorMessage;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(errorMessage ?? '재개에 실패했습니다.'),
            backgroundColor: GxColors.danger,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
          ),
        );
      }
    }
  }

  Future<void> _handleCompleteTask(int taskId, int workerId) async {
    final taskNotifier = ref.read(taskProvider.notifier);
    final success = await taskNotifier.completeTask(
      taskId: taskId,
      workerId: workerId,
    );

    if (mounted) {
      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('작업을 완료했습니다.'),
            backgroundColor: GxColors.success,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
          ),
        );
      } else {
        final errorMessage = ref.read(taskProvider).errorMessage;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(errorMessage ?? '작업 완료에 실패했습니다.'),
            backgroundColor: GxColors.danger,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
          ),
        );
      }
    }
  }

  String _formatDateTime(DateTime dateTime) {
    final local = dateTime.toLocal();
    return '${local.month}/${local.day} ${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
  }
}
