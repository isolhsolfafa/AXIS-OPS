import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../providers/auth_provider.dart';
import '../../services/api_service.dart';
import '../../services/notice_service.dart';
import '../../utils/design_system.dart';
import 'notice_detail_screen.dart';

/// 공지사항 목록 화면
/// Sprint 20-B
class NoticeListScreen extends ConsumerStatefulWidget {
  const NoticeListScreen({super.key});

  @override
  ConsumerState<NoticeListScreen> createState() => _NoticeListScreenState();
}

class _NoticeListScreenState extends ConsumerState<NoticeListScreen> {
  late final NoticeService _noticeService;
  List<Map<String, dynamic>> _notices = [];
  bool _loading = true;
  int _total = 0;
  int _page = 1;
  final int _limit = 10;

  @override
  void initState() {
    super.initState();
    // 토큰이 설정된 공유 ApiService 사용 (MISSING_TOKEN 방지)
    final apiService = ref.read(apiServiceProvider);
    _noticeService = NoticeService(apiService: apiService);
    _loadNotices();
  }

  Future<void> _loadNotices() async {
    setState(() => _loading = true);
    try {
      final result = await _noticeService.getNotices(page: _page, limit: _limit);
      setState(() {
        _notices = List<Map<String, dynamic>>.from(result['notices'] ?? []);
        _total = result['total'] ?? 0;
        _loading = false;
      });
      // 마지막 확인 공지 ID 저장 (안 읽은 뱃지 용도)
      if (_notices.isNotEmpty) {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setInt('last_seen_notice_id', _notices.first['id'] as int);
      }
    } catch (e) {
      setState(() => _loading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('공지사항을 불러올 수 없습니다: $e')),
        );
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
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: GxColors.mist),
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _notices.isEmpty
              ? const Center(
                  child: Text('등록된 공지사항이 없습니다.', style: TextStyle(color: GxColors.steel, fontSize: 14)),
                )
              : RefreshIndicator(
                  onRefresh: _loadNotices,
                  child: ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _notices.length + (_total > _page * _limit ? 1 : 0),
                    itemBuilder: (context, index) {
                      if (index == _notices.length) {
                        return Center(
                          child: TextButton(
                            onPressed: () {
                              setState(() => _page++);
                              _loadNotices();
                            },
                            child: const Text('더 보기'),
                          ),
                        );
                      }
                      return _buildNoticeItem(_notices[index]);
                    },
                  ),
                ),
      floatingActionButton: isAdmin
          ? FloatingActionButton(
              backgroundColor: GxColors.accent,
              onPressed: () => _navigateToWrite(),
              child: const Icon(Icons.edit, color: Colors.white),
            )
          : null,
    );
  }

  Widget _buildNoticeItem(Map<String, dynamic> notice) {
    final isPinned = notice['is_pinned'] == true;
    final version = notice['version'] as String?;
    final createdAt = notice['created_at'] as String?;
    final dateStr = createdAt != null
        ? DateTime.tryParse(createdAt)?.toLocal().toString().substring(0, 10) ?? ''
        : '';

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: GxGlass.cardSm(radius: GxRadius.md),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(GxRadius.md),
          onTap: () async {
            await Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => NoticeDetailScreen(noticeId: notice['id'] as int),
              ),
            );
            _loadNotices();
          },
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Row(
              children: [
                if (isPinned)
                  const Padding(
                    padding: EdgeInsets.only(right: 8),
                    child: Icon(Icons.push_pin, size: 16, color: GxColors.warning),
                  ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        notice['title'] ?? '',
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                          color: GxColors.charcoal,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          Text(
                            dateStr,
                            style: const TextStyle(fontSize: 11, color: GxColors.steel),
                          ),
                          if (version != null && version.isNotEmpty) ...[
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                              decoration: BoxDecoration(
                                color: GxColors.accentSoft,
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Text(
                                'v$version',
                                style: const TextStyle(fontSize: 10, color: GxColors.accent, fontWeight: FontWeight.w500),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ],
                  ),
                ),
                const Icon(Icons.chevron_right, color: GxColors.silver, size: 20),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _navigateToWrite() async {
    final result = await Navigator.pushNamed(context, '/notice-write');
    if (result == true) {
      _page = 1;
      _loadNotices();
    }
  }
}
