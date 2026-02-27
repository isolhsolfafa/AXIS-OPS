import 'package:flutter/material.dart';
import '../utils/design_system.dart';

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
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: isCompleted ? GxColors.success.withValues(alpha: 0.08) : GxColors.steel.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(GxRadius.sm),
        border: Border.all(
          color: isCompleted ? GxColors.success.withValues(alpha: 0.2) : GxColors.steel.withValues(alpha: 0.2),
          width: 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isCompleted ? Icons.check_circle : Icons.schedule,
            color: isCompleted ? GxColors.success : GxColors.steel,
            size: 14,
          ),
          const SizedBox(width: 5),
          Text(
            label,
            style: TextStyle(
              color: isCompleted ? GxColors.success : GxColors.steel,
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
