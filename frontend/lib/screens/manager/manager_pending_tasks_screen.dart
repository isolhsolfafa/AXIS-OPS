import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../utils/design_system.dart';

/// 협력사 관리자 전용 미종료 작업 화면
///
/// is_manager = true, is_admin = false인 협력사 관리자가 접근
/// 본인 company의 미종료 작업만 표시
/// 강제 종료 기능 제공
class ManagerPendingTasksScreen extends ConsumerStatefulWidget {
  const ManagerPendingTasksScreen({super.key});

  @override
  ConsumerState<ManagerPendingTasksScreen> createState() =>
      _ManagerPendingTasksScreenState();
}

class _ManagerPendingTasksScreenState
    extends ConsumerState<ManagerPendingTasksScreen> {
  List<Map<String, dynamic>> _pendingTasks = [];
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _loadPendingTasks();
  }

  Future<void> _loadPendingTasks() async {
    setState(() => _isLoading = true);
    try {
      final authState = ref.read(authProvider);
      final company = authState.currentWorker?.company ?? '';
      final apiService = ref.read(apiServiceProvider);
      final response = await apiService.get(
        '/admin/tasks/pending',
        queryParameters: {'company': company},
      );
      if (mounted) {
        setState(() {
          _pendingTasks = List<Map<String, dynamic>>.from(
            response['tasks'] as List? ?? [],
          );
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
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
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(GxRadius.lg),
          ),
          title: Row(
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: GxColors.dangerBg,
                  borderRadius: BorderRadius.circular(GxRadius.md),
                ),
                child: const Icon(Icons.stop_circle,
                    color: GxColors.danger, size: 18),
              ),
              const SizedBox(width: 10),
              const Text('강제 종료',
                  style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      color: GxColors.danger)),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('완료 시각',
                  style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: GxColors.steel,
                      letterSpacing: 0.5)),
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
                      initialTime:
                          TimeOfDay.fromDateTime(selectedDateTime),
                    );
                    if (time != null) {
                      setDialogState(() {
                        selectedDateTime = DateTime(
                          date.year,
                          date.month,
                          date.day,
                          time.hour,
                          time.minute,
                        );
                      });
                    }
                  }
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(
                    border:
                        Border.all(color: GxColors.mist, width: 1.5),
                    borderRadius: BorderRadius.circular(GxRadius.sm),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.access_time,
                          size: 16, color: GxColors.steel),
                      const SizedBox(width: 8),
                      Text(
                        '${selectedDateTime.year}-${selectedDateTime.month.toString().padLeft(2, '0')}-${selectedDateTime.day.toString().padLeft(2, '0')} '
                        '${selectedDateTime.hour.toString().padLeft(2, '0')}:${selectedDateTime.minute.toString().padLeft(2, '0')}',
                        style: const TextStyle(
                            fontSize: 13, color: GxColors.charcoal),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 14),
              const Text('종료 사유',
                  style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: GxColors.steel,
                      letterSpacing: 0.5)),
              const SizedBox(height: 6),
              TextField(
                controller: reasonController,
                decoration: InputDecoration(
                  hintText: '예: 작업자 미처리, 연장 작업 미등록',
                  hintStyle: const TextStyle(
                      fontSize: 12, color: GxColors.silver),
                  contentPadding: const EdgeInsets.symmetric(
                      horizontal: 12, vertical: 10),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(GxRadius.sm),
                    borderSide:
                        const BorderSide(color: GxColors.mist, width: 1.5),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(GxRadius.sm),
                    borderSide:
                        const BorderSide(color: GxColors.mist, width: 1.5),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(GxRadius.sm),
                    borderSide: const BorderSide(
                        color: GxColors.accent, width: 1.5),
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
              child: const Text('취소',
                  style: TextStyle(color: GxColors.steel)),
            ),
            Container(
              height: 36,
              decoration: BoxDecoration(
                color: GxColors.danger,
                borderRadius: BorderRadius.circular(GxRadius.sm),
                boxShadow: [
                  BoxShadow(
                      color: GxColors.danger.withValues(alpha: 0.3),
                      blurRadius: 8,
                      offset: const Offset(0, 2)),
                ],
              ),
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: () => Navigator.pop(ctx, true),
                  borderRadius: BorderRadius.circular(GxRadius.sm),
                  child: const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 16),
                    child: Center(
                      child: Text('강제 종료',
                          style: TextStyle(
                              color: Colors.white,
                              fontSize: 13,
                              fontWeight: FontWeight.w600)),
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
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(GxRadius.sm)),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final company = authState.currentWorker?.company ?? '';

    return Scaffold(
      backgroundColor: GxColors.cloud,
      appBar: AppBar(
        backgroundColor: GxColors.white,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios,
              size: 18, color: GxColors.accent),
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
            Text(
              '$company 미종료 작업',
              style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  color: GxColors.charcoal),
            ),
          ],
        ),
        centerTitle: false,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: GxColors.slate, size: 20),
            onPressed: _loadPendingTasks,
            tooltip: '새로고침',
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: GxColors.mist),
        ),
      ),
      body: SafeArea(
        child: _isLoading
            ? const Center(
                child: CircularProgressIndicator(
                    color: GxColors.accent, strokeWidth: 2))
            : _pendingTasks.isEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.check_circle_outline,
                            size: 56, color: GxColors.success),
                        const SizedBox(height: 12),
                        Text(
                          '$company 미종료 작업이 없습니다.',
                          style: const TextStyle(
                              fontSize: 14, color: GxColors.steel),
                        ),
                      ],
                    ),
                  )
                : RefreshIndicator(
                    onRefresh: _loadPendingTasks,
                    color: GxColors.accent,
                    child: ListView.builder(
                      padding: const EdgeInsets.all(16),
                      itemCount: _pendingTasks.length,
                      itemBuilder: (context, index) =>
                          _buildTaskCard(_pendingTasks[index]),
                    ),
                  ),
      ),
    );
  }

  Widget _buildTaskCard(Map<String, dynamic> task) {
    final taskId = task['id'] as int;
    final taskName = task['task_name'] as String? ?? '';
    final workerName = task['worker_name'] as String? ?? '';
    final serialNumber = task['serial_number'] as String? ?? '';
    final taskCategory = task['task_category'] as String? ?? '';
    final startedAt = task['started_at'] != null
        ? DateTime.tryParse(task['started_at'] as String)?.toLocal()
        : null;

    Color categoryColor;
    switch (taskCategory) {
      case 'MECH':
        categoryColor = const Color(0xFFEA580C);
        break;
      case 'ELEC':
        categoryColor = GxColors.info;
        break;
      case 'TMS':
        categoryColor = const Color(0xFF0D9488);
        break;
      default:
        categoryColor = GxColors.steel;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: GxGlass.cardSm(radius: GxRadius.lg).copyWith(
        border: Border.all(
            color: GxColors.warning.withValues(alpha: 0.3), width: 1),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: categoryColor.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(GxRadius.sm),
                  ),
                  child: Text(
                    taskCategory,
                    style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: categoryColor),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    taskName,
                    style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: GxColors.charcoal),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: GxColors.warningBg,
                    borderRadius: BorderRadius.circular(GxRadius.sm),
                  ),
                  child: const Text(
                    '미종료',
                    style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                        color: GxColors.warning),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                const Icon(Icons.person_outline,
                    size: 14, color: GxColors.steel),
                const SizedBox(width: 4),
                Text(workerName,
                    style:
                        const TextStyle(fontSize: 12, color: GxColors.slate)),
                const SizedBox(width: 16),
                const Icon(Icons.qr_code, size: 14, color: GxColors.steel),
                const SizedBox(width: 4),
                Text(serialNumber,
                    style:
                        const TextStyle(fontSize: 12, color: GxColors.slate)),
              ],
            ),
            if (startedAt != null) ...[
              const SizedBox(height: 4),
              Row(
                children: [
                  const Icon(Icons.access_time,
                      size: 14, color: GxColors.steel),
                  const SizedBox(width: 4),
                  Text(
                    '시작: ${startedAt.year}-${startedAt.month.toString().padLeft(2, '0')}-${startedAt.day.toString().padLeft(2, '0')} '
                    '${startedAt.hour.toString().padLeft(2, '0')}:${startedAt.minute.toString().padLeft(2, '0')}',
                    style:
                        const TextStyle(fontSize: 12, color: GxColors.slate),
                  ),
                ],
              ),
            ],
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              height: 36,
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: [
                  GxColors.danger,
                  GxColors.danger.withValues(alpha: 0.8),
                ]),
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
                        Icon(Icons.stop_circle,
                            size: 16, color: Colors.white),
                        SizedBox(width: 6),
                        Text('강제 종료',
                            style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: Colors.white)),
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
