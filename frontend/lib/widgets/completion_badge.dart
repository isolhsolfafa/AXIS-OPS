import 'package:flutter/material.dart';

// TODO: 완료 배지 위젯 구현

class CompletionBadge extends StatelessWidget {
  final String label;
  final bool isCompleted;
  final DateTime? completedAt;
  final Duration? duration;

  const CompletionBadge({
    Key? key,
    required this.label,
    required this.isCompleted,
    this.completedAt,
    this.duration,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    // TODO: 완료 상태에 따른 색상 변경
    // TODO: 완료 시간 표시 (선택사항)
    // TODO: 소요 시간 표시 (선택사항)

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: isCompleted ? Colors.green : Colors.grey,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isCompleted ? Icons.check_circle : Icons.schedule,
            color: Colors.white,
            size: 16,
          ),
          const SizedBox(width: 6),
          Text(
            label,
            style: const TextStyle(color: Colors.white, fontSize: 12),
          ),
        ],
      ),
    );
  }
}
