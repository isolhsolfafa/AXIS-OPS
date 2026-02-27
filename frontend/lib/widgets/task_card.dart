import 'package:flutter/material.dart';
import '../utils/design_system.dart';

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
    Color statusColor;
    Color statusBg;
    String statusLabel;

    switch (status) {
      case 'completed':
        statusColor = GxColors.success;
        statusBg = GxColors.successBg;
        statusLabel = '완료';
        break;
      case 'in_progress':
        statusColor = GxColors.warning;
        statusBg = GxColors.warningBg;
        statusLabel = '진행 중';
        break;
      default:
        statusColor = GxColors.steel;
        statusBg = GxColors.mist;
        statusLabel = '대기';
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: GxGlass.cardSm(radius: GxRadius.md),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(GxRadius.md),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(GxRadius.md),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '작업: $taskId',
                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: GxColors.charcoal),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '프로세스: $processType',
                        style: const TextStyle(fontSize: 12, color: GxColors.slate),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: statusBg,
                    borderRadius: BorderRadius.circular(GxRadius.sm),
                  ),
                  child: Text(
                    statusLabel,
                    style: TextStyle(fontSize: 11, color: statusColor, fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
