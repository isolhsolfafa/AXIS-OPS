import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../services/notice_service.dart';
import '../../utils/design_system.dart';

/// Admin 공지 작성/수정 화면
/// Sprint 20-B (작성), Sprint 22-C (수정 모드 추가)
class NoticeWriteScreen extends ConsumerStatefulWidget {
  /// 수정 모드일 때 기존 공지 데이터 전달
  final Map<String, dynamic>? existingNotice;

  const NoticeWriteScreen({super.key, this.existingNotice});

  bool get isEditMode => existingNotice != null;

  @override
  ConsumerState<NoticeWriteScreen> createState() => _NoticeWriteScreenState();
}

class _NoticeWriteScreenState extends ConsumerState<NoticeWriteScreen> {
  late final NoticeService _noticeService;
  final _titleController = TextEditingController();
  final _contentController = TextEditingController();
  final _versionController = TextEditingController();
  bool _isPinned = false;
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    final apiService = ref.read(apiServiceProvider);
    _noticeService = NoticeService(apiService: apiService);

    // 수정 모드: 기존 데이터 채우기
    if (widget.isEditMode) {
      final n = widget.existingNotice!;
      _titleController.text = n['title'] ?? '';
      _contentController.text = n['content'] ?? '';
      _versionController.text = n['version'] ?? '';
      _isPinned = n['is_pinned'] == true;
    }
  }

  @override
  void dispose() {
    _titleController.dispose();
    _contentController.dispose();
    _versionController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final title = _titleController.text.trim();
    final content = _contentController.text.trim();

    if (title.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('제목을 입력해주세요.')),
      );
      return;
    }
    if (content.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('내용을 입력해주세요.')),
      );
      return;
    }

    setState(() => _submitting = true);
    try {
      final versionText = _versionController.text.trim().isEmpty ? null : _versionController.text.trim();

      if (widget.isEditMode) {
        await _noticeService.updateNotice(
          widget.existingNotice!['id'],
          title: title,
          content: content,
          version: versionText,
          isPinned: _isPinned,
        );
      } else {
        await _noticeService.createNotice(
          title: title,
          content: content,
          version: versionText,
          isPinned: _isPinned,
        );
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(widget.isEditMode ? '공지사항이 수정되었습니다.' : '공지사항이 등록되었습니다.')),
        );
        Navigator.pop(context, true);
      }
    } catch (e) {
      setState(() => _submitting = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${widget.isEditMode ? '수정' : '등록'} 실패: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: GxColors.cloud,
      appBar: AppBar(
        title: Text(widget.isEditMode ? '공지 수정' : '공지 작성', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: GxColors.charcoal)),
        backgroundColor: Colors.white,
        elevation: 0,
        iconTheme: const IconThemeData(color: GxColors.charcoal),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: GxColors.mist),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: GxGlass.cardSm(radius: GxRadius.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextField(
                controller: _titleController,
                decoration: const InputDecoration(
                  labelText: '제목',
                  hintText: '공지 제목을 입력하세요',
                  border: OutlineInputBorder(),
                ),
                maxLength: 200,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _versionController,
                decoration: const InputDecoration(
                  labelText: '버전 (선택)',
                  hintText: '예: 1.4.0',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _contentController,
                decoration: const InputDecoration(
                  labelText: '내용',
                  hintText: '공지 내용을 입력하세요',
                  border: OutlineInputBorder(),
                  alignLabelWithHint: true,
                ),
                maxLines: 10,
                minLines: 5,
              ),
              const SizedBox(height: 12),
              SwitchListTile(
                title: const Text('상단 고정', style: TextStyle(fontSize: 14)),
                value: _isPinned,
                onChanged: (v) => setState(() => _isPinned = v),
                contentPadding: EdgeInsets.zero,
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                height: 48,
                child: ElevatedButton(
                  onPressed: _submitting ? null : _submit,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: GxColors.accent,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.md)),
                  ),
                  child: _submitting
                      ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : Text(widget.isEditMode ? '수정' : '등록', style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Colors.white)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
