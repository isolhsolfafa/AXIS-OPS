import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/task_provider.dart';
import '../../providers/auth_provider.dart';
import '../../models/task_item.dart';
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

    // 필터링된 Task 목록
    final filteredTasks = tasks.where((task) {
      if (_filterStatus == 'all') return true;
      return task.status == _filterStatus;
    }).toList();

    return Scaffold(
      appBar: AppBar(
        title: Text(currentProduct?.serialNumber ?? 'Task 관리'),
        centerTitle: true,
        actions: [
          // 필터 버튼
          PopupMenuButton<String>(
            icon: const Icon(Icons.filter_list),
            onSelected: (value) {
              setState(() {
                _filterStatus = value;
              });
            },
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: 'all',
                child: Text('전체'),
              ),
              const PopupMenuItem(
                value: 'pending',
                child: Text('대기 중'),
              ),
              const PopupMenuItem(
                value: 'in_progress',
                child: Text('진행 중'),
              ),
              const PopupMenuItem(
                value: 'completed',
                child: Text('완료'),
              ),
            ],
          ),
        ],
      ),
      body: taskState.isLoading
          ? const Center(child: CircularProgressIndicator())
          : SafeArea(
              child: Column(
                children: [
                  // 제품 정보 헤더
                  if (currentProduct != null)
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(16),
                      color: Colors.blue.shade50,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            currentProduct.serialNumber,
                            style: const TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '모델: ${currentProduct.model} | QR: ${currentProduct.qrDocId}',
                            style: TextStyle(
                              fontSize: 14,
                              color: Colors.grey[700],
                            ),
                          ),
                          if (currentProduct.locationQrId != null) ...[
                            const SizedBox(height: 4),
                            Row(
                              children: [
                                Icon(Icons.location_on,
                                    size: 16, color: Colors.blue.shade700),
                                const SizedBox(width: 4),
                                Text(
                                  currentProduct.locationQrId!,
                                  style: TextStyle(
                                    fontSize: 14,
                                    color: Colors.blue.shade700,
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ],
                      ),
                    ),

                  // 진행률 표시
                  Container(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              '진행률: ${(taskState.taskProgress * 100).toStringAsFixed(0)}%',
                              style: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            Text(
                              '${taskState.completedTaskCount}/${tasks.length}',
                              style: TextStyle(
                                fontSize: 16,
                                color: Colors.grey[600],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        LinearProgressIndicator(
                          value: taskState.taskProgress,
                          minHeight: 8,
                          backgroundColor: Colors.grey.shade200,
                          borderRadius: BorderRadius.circular(4),
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
                                Icon(
                                  Icons.task_alt,
                                  size: 64,
                                  color: Colors.grey[300],
                                ),
                                const SizedBox(height: 16),
                                Text(
                                  _filterStatus == 'all'
                                      ? 'Task가 없습니다.'
                                      : '필터에 맞는 Task가 없습니다.',
                                  style: TextStyle(
                                    fontSize: 16,
                                    color: Colors.grey[600],
                                  ),
                                ),
                              ],
                            ),
                          )
                        : ListView.builder(
                            padding: const EdgeInsets.symmetric(horizontal: 16),
                            itemCount: filteredTasks.length,
                            itemBuilder: (context, index) {
                              final task = filteredTasks[index];
                              return _buildTaskCard(
                                context,
                                task,
                                authState.currentWorkerId ?? 0,
                              );
                            },
                          ),
                  ),
                ],
              ),
            ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          // 새 QR 스캔
          ref.read(taskProvider.notifier).clearCurrentProduct();
          Navigator.pushReplacementNamed(context, '/qr-scan');
        },
        tooltip: '새 QR 스캔',
        child: const Icon(Icons.qr_code_scanner),
      ),
    );
  }

  Widget _buildTaskCard(BuildContext context, TaskItem task, int workerId) {
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

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: () {
          // Task 상세 화면으로 이동
          ref.read(taskProvider.notifier).selectTask(task);
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => const TaskDetailScreen(),
            ),
          );
        },
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(statusIcon, color: statusColor, size: 24),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      task.taskName,
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: statusColor.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      statusText,
                      style: TextStyle(
                        fontSize: 12,
                        color: statusColor,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Text(
                    'ID: ${task.taskId}',
                    style: TextStyle(
                      fontSize: 14,
                      color: Colors.grey[600],
                    ),
                  ),
                  const SizedBox(width: 16),
                  Text(
                    '카테고리: ${task.taskCategory}',
                    style: TextStyle(
                      fontSize: 14,
                      color: Colors.grey[600],
                    ),
                  ),
                ],
              ),
              if (task.startedAt != null) ...[
                const SizedBox(height: 8),
                Row(
                  children: [
                    Icon(Icons.access_time, size: 16, color: Colors.grey[600]),
                    const SizedBox(width: 4),
                    Text(
                      '시작: ${_formatDateTime(task.startedAt!)}',
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey[600],
                      ),
                    ),
                  ],
                ),
              ],
              if (task.completedAt != null) ...[
                const SizedBox(height: 4),
                Row(
                  children: [
                    Icon(Icons.check, size: 16, color: Colors.grey[600]),
                    const SizedBox(width: 4),
                    Text(
                      '완료: ${_formatDateTime(task.completedAt!)}',
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey[600],
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      '소요: ${task.durationFormatted}',
                      style: TextStyle(
                        fontSize: 14,
                        color: task.hasAbnormalDuration
                            ? Colors.red
                            : Colors.grey[600],
                        fontWeight: task.hasAbnormalDuration
                            ? FontWeight.bold
                            : FontWeight.normal,
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
                      child: ElevatedButton.icon(
                        onPressed: () => _handleStartTask(task.id, workerId),
                        icon: const Icon(Icons.play_arrow),
                        label: const Text('시작'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.blue,
                          foregroundColor: Colors.white,
                        ),
                      ),
                    ),
                  if (task.status == 'in_progress')
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: () => _handleCompleteTask(task.id, workerId),
                        icon: const Icon(Icons.check_circle),
                        label: const Text('완료'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.green,
                          foregroundColor: Colors.white,
                        ),
                      ),
                    ),
                  if (task.status == 'completed')
                    Expanded(
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: Colors.green.shade50,
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          '작업 완료됨',
                          style: TextStyle(
                            color: Colors.green.shade700,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ],
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

  Future<void> _handleCompleteTask(int taskId, int workerId) async {
    final taskNotifier = ref.read(taskProvider.notifier);
    final success = await taskNotifier.completeTask(
      taskId: taskId,
      workerId: workerId,
    );

    if (mounted) {
      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('작업을 완료했습니다.'),
            backgroundColor: Colors.green,
          ),
        );
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

  String _formatDateTime(DateTime dateTime) {
    return '${dateTime.month}/${dateTime.day} ${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
  }
}
