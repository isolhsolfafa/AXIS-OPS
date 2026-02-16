import 'package:flutter/material.dart';

// TODO: 작업 카드 위젯 구현

class TaskCard extends StatelessWidget {
  final String taskId;
  final String processType;
  final String status;
  final String? qrDocId;
  final DateTime? startedAt;
  final Duration? duration;
  final VoidCallback? onTap;

  const TaskCard({
    Key? key,
    required this.taskId,
    required this.processType,
    required this.status,
    this.qrDocId,
    this.startedAt,
    this.duration,
    this.onTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    // TODO: 카드 배치 및 스타일링
    // TODO: 작업 ID, 프로세스 타입 표시
    // TODO: 상태 배지 표시 (대기, 진행 중, 완료)
    // TODO: 진행 시간 표시

    return Card(
      child: ListTile(
        title: Text('작업: $taskId'),
        subtitle: Text('프로세스: $processType'),
        trailing: Chip(
          label: Text(status),
        ),
        onTap: onTap,
      ),
    );
  }
}
