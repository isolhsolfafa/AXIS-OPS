import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../services/notice_service.dart';
import '../../utils/design_system.dart';

/// 공지사항 상세 화면
/// Sprint 20-B
class NoticeDetailScreen extends ConsumerStatefulWidget {
  final int noticeId;
  const NoticeDetailScreen({super.key, required this.noticeId});

  @override
  ConsumerState<NoticeDetailScreen> createState() => _NoticeDetailScreenState();
}

class _NoticeDetailScreenState extends ConsumerState<NoticeDetailScreen> {
  final NoticeService _noticeService = NoticeService();
  Map<String, dynamic>? _notice;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadDetail();
  }

  Future<void> _loadDetail() async {
    try {
      final result = await _noticeService.getNoticeDetail(widget.noticeId);
      setState(() {
        _notice = result;
        _loading = false;
      });
    } catch (e) {
      setState(() => _loading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('공지사항을 불러올 수 없습니다: $e')),
        );
      }
    }
  }

  Future<void> _deleteNotice() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('공지 삭제'),
        content: const Text('이 공지사항을 삭제하시겠습니까?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('취소')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('삭제', style: TextStyle(color: GxColors.danger)),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await _noticeService.deleteNotice(widget.noticeId);
        if (mounted) Navigator.pop(context, true);
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('삭제 실패: $e')),
          );
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final worker = ref.watch(authProvider).currentWorker;
    final isAdmin = worker?.isAdmin == true;

    return Scaffold(
      backgroundColor: GxColors.cloud,
      appBar: AppBar(
        title: const Text('공지사항', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: GxColors.charcoal)),
        backgroundColor: Colors.white,
        elevation: 0,
        iconTheme: const IconThemeData(color: GxColors.charcoal),
        actions: isAdmin && _notice != null
            ? [
                IconButton(
                  icon: const Icon(Icons.delete_outline, color: GxColors.danger),
                  onPressed: _deleteNotice,
                ),
              ]
            : null,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: GxColors.mist),
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _notice == null
              ? const Center(child: Text('공지사항을 찾을 수 없습니다.'))
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(20),
                    decoration: GxGlass.cardSm(radius: GxRadius.lg),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // 제목
                        Text(
                          _notice!['title'] ?? '',
                          style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w600,
                            color: GxColors.charcoal,
                          ),
                        ),
                        const SizedBox(height: 12),
                        // 메타 정보
                        Row(
                          children: [
                            if (_notice!['author_name'] != null) ...[
                              Text(
                                _notice!['author_name'],
                                style: const TextStyle(fontSize: 12, color: GxColors.steel),
                              ),
                              const SizedBox(width: 12),
                            ],
                            Text(
                              _formatDate(_notice!['created_at']),
                              style: const TextStyle(fontSize: 12, color: GxColors.steel),
                            ),
                            if (_notice!['version'] != null) ...[
                              const SizedBox(width: 8),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                                decoration: BoxDecoration(
                                  color: GxColors.accentSoft,
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Text(
                                  'v${_notice!['version']}',
                                  style: const TextStyle(fontSize: 10, color: GxColors.accent, fontWeight: FontWeight.w500),
                                ),
                              ),
                            ],
                            if (_notice!['is_pinned'] == true) ...[
                              const SizedBox(width: 8),
                              const Icon(Icons.push_pin, size: 14, color: GxColors.warning),
                            ],
                          ],
                        ),
                        const Padding(
                          padding: EdgeInsets.symmetric(vertical: 16),
                          child: Divider(height: 1, color: GxColors.mist),
                        ),
                        // 본문
                        Text(
                          _notice!['content'] ?? '',
                          style: const TextStyle(
                            fontSize: 14,
                            height: 1.6,
                            color: GxColors.graphite,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
    );
  }

  String _formatDate(String? isoDate) {
    if (isoDate == null) return '';
    final dt = DateTime.tryParse(isoDate)?.toLocal();
    if (dt == null) return '';
    return '${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')} ${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
  }
}
