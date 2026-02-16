import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/task_provider.dart';
import '../../providers/auth_provider.dart';

/// Task 상세 화면
///
/// 선택된 Task의 상세 정보 표시 및 시작/완료 액션 제공
class TaskDetailScreen extends ConsumerWidget {
  const TaskDetailScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final taskState = ref.watch(taskProvider);
    final authState = ref.watch(authProvider);
    final task = taskState.selectedTask;
    final currentProduct = taskState.currentProduct;
    final workerId = authState.currentWorkerId ?? 0;

    if (task == null) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Task 상세'),
        ),
        body: const Center(
          child: Text('Task 정보를 불러올 수 없습니다.'),
        ),
      );
    }

    Color statusColor;
    IconData statusIcon;
    String statusText;

    switch (task.status) {
      case 'completed':
        statusColor = Colors.green;
        statusIcon = Icons.check_circle;
        statusText = '완료';
        break;
      case 'in_progress':
        statusColor = Colors.orange;
        statusIcon = Icons.play_circle;
        statusText = '진행 중';
        break;
      default:
        statusColor = Colors.grey;
        statusIcon = Icons.radio_button_unchecked;
        statusText = '대기';
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Task 상세'),
        centerTitle: true,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Task 상태 표시
              Card(
                elevation: 2,
                color: statusColor.withOpacity(0.1),
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    children: [
                      Icon(statusIcon, size: 64, color: statusColor),
                      const SizedBox(height: 12),
                      Text(
                        task.taskName,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 8),
                        decoration: BoxDecoration(
                          color: statusColor,
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          statusText,
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),

              // Task 정보
              const Text(
                'Task 정보',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      _buildInfoRow('Task ID', task.taskId),
                      _buildInfoRow('카테고리', task.taskCategory),
                      _buildInfoRow(
                        '적용 여부',
                        task.isApplicable ? '적용' : '미적용',
                      ),
                      _buildInfoRow(
                        'Location QR 확인',
                        task.locationQrVerified ? '확인됨' : '미확인',
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),

              // 제품 정보
              if (currentProduct != null) ...[
                const Text(
                  '제품 정보',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 12),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        _buildInfoRow('시리얼 번호', currentProduct.serialNumber),
                        _buildInfoRow('QR 문서 ID', currentProduct.qrDocId),
                        _buildInfoRow('모델', currentProduct.model),
                        if (currentProduct.locationQrId != null)
                          _buildInfoRow('위치', currentProduct.locationQrId!),
                        if (currentProduct.mechPartner != null)
                          _buildInfoRow('기구 협력사', currentProduct.mechPartner!),
                        if (currentProduct.moduleOutsourcing != null)
                          _buildInfoRow(
                              '모듈 외주', currentProduct.moduleOutsourcing!),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 24),
              ],

              // 작업 시간 정보
              const Text(
                '작업 시간',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      if (task.startedAt != null)
                        _buildInfoRow(
                          '시작 시간',
                          _formatFullDateTime(task.startedAt!),
                        ),
                      if (task.completedAt != null) ...[
                        _buildInfoRow(
                          '완료 시간',
                          _formatFullDateTime(task.completedAt!),
                        ),
                        _buildInfoRow(
                          '소요 시간',
                          task.durationFormatted,
                          valueColor: task.hasAbnormalDuration
                              ? Colors.red
                              : Colors.black,
                        ),
                        if (task.hasAbnormalDuration)
                          Padding(
                            padding: const EdgeInsets.only(top: 8),
                            child: Row(
                              children: [
                                Icon(Icons.warning,
                                    size: 16, color: Colors.red),
                                const SizedBox(width: 4),
                                Expanded(
                                  child: Text(
                                    '비정상 작업 시간 (14시간 초과)',
                                    style: TextStyle(
                                      fontSize: 12,
                                      color: Colors.red,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                      ],
                      if (task.startedAt == null && task.completedAt == null)
                        const Center(
                          child: Text(
                            '아직 시작하지 않은 작업입니다.',
                            style: TextStyle(
                              fontSize: 14,
                              color: Colors.grey,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 32),

              // 액션 버튼
              if (task.status == 'pending')
                ElevatedButton.icon(
                  onPressed: () => _handleStartTask(context, ref, task.id, workerId),
                  icon: const Icon(Icons.play_arrow),
                  label: const Text('작업 시작'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    textStyle: const TextStyle(fontSize: 18),
                    backgroundColor: Colors.blue,
                    foregroundColor: Colors.white,
                  ),
                ),
              if (task.status == 'in_progress')
                ElevatedButton.icon(
                  onPressed: () => _handleCompleteTask(context, ref, task.id, workerId),
                  icon: const Icon(Icons.check_circle),
                  label: const Text('작업 완료'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    textStyle: const TextStyle(fontSize: 18),
                    backgroundColor: Colors.green,
                    foregroundColor: Colors.white,
                  ),
                ),
              if (task.status == 'completed')
                Container(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: Colors.green.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.green.shade200, width: 2),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.check_circle, color: Colors.green.shade700),
                      const SizedBox(width: 8),
                      Text(
                        '작업 완료됨',
                        style: TextStyle(
                          color: Colors.green.shade700,
                          fontWeight: FontWeight.bold,
                          fontSize: 18,
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value, {Color? valueColor}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey[600],
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                fontSize: 14,
                color: valueColor ?? Colors.black,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _handleStartTask(
      BuildContext context, WidgetRef ref, int taskId, int workerId) async {
    final taskNotifier = ref.read(taskProvider.notifier);
    final success = await taskNotifier.startTask(
      taskId: taskId,
      workerId: workerId,
    );

    if (context.mounted) {
      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('작업을 시작했습니다.'),
            backgroundColor: Colors.blue,
          ),
        );
      } else {
        final errorMessage = ref.read(taskProvider).errorMessage;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(errorMessage ?? '작업 시작에 실패했습니다.'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _handleCompleteTask(
      BuildContext context, WidgetRef ref, int taskId, int workerId) async {
    final taskNotifier = ref.read(taskProvider.notifier);
    final success = await taskNotifier.completeTask(
      taskId: taskId,
      workerId: workerId,
    );

    if (context.mounted) {
      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('작업을 완료했습니다.'),
            backgroundColor: Colors.green,
          ),
        );
        Navigator.pop(context); // 목록 화면으로 돌아가기
      } else {
        final errorMessage = ref.read(taskProvider).errorMessage;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(errorMessage ?? '작업 완료에 실패했습니다.'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  String _formatFullDateTime(DateTime dateTime) {
    return '${dateTime.year}년 ${dateTime.month}월 ${dateTime.day}일 '
        '${dateTime.hour.toString().padLeft(2, '0')}:'
        '${dateTime.minute.toString().padLeft(2, '0')}';
  }
}
