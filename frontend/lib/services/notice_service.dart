import 'api_service.dart';

/// 공지사항 서비스
/// Sprint 20-B: 공지사항 CRUD API 호출
class NoticeService {
  final ApiService _apiService;

  NoticeService({ApiService? apiService})
      : _apiService = apiService ?? ApiService();

  /// 공지 목록 조회
  Future<Map<String, dynamic>> getNotices({
    int page = 1,
    int limit = 10,
    String? version,
  }) async {
    final params = <String, dynamic>{
      'page': page.toString(),
      'limit': limit.toString(),
    };
    if (version != null) params['version'] = version;

    final response = await _apiService.get(
      '/notices',
      queryParameters: params,
    );
    return Map<String, dynamic>.from(response);
  }

  /// 공지 상세 조회
  Future<Map<String, dynamic>> getNoticeDetail(int noticeId) async {
    final response = await _apiService.get('/notices/$noticeId');
    return Map<String, dynamic>.from(response);
  }

  /// 공지 작성 (Admin)
  Future<Map<String, dynamic>> createNotice({
    required String title,
    required String content,
    String? version,
    bool isPinned = false,
  }) async {
    final response = await _apiService.post('/admin/notices', data: {
      'title': title,
      'content': content,
      if (version != null) 'version': version,
      'is_pinned': isPinned,
    });
    return Map<String, dynamic>.from(response);
  }

  /// 공지 수정 (Admin)
  Future<Map<String, dynamic>> updateNotice(
    int noticeId, {
    String? title,
    String? content,
    String? version,
    bool? isPinned,
  }) async {
    final data = <String, dynamic>{};
    if (title != null) data['title'] = title;
    if (content != null) data['content'] = content;
    if (version != null) data['version'] = version;
    if (isPinned != null) data['is_pinned'] = isPinned;

    final response = await _apiService.put(
      '/admin/notices/$noticeId',
      data: data,
    );
    return Map<String, dynamic>.from(response);
  }

  /// 공지 삭제 (Admin)
  Future<Map<String, dynamic>> deleteNotice(int noticeId) async {
    final response = await _apiService.delete('/admin/notices/$noticeId');
    return Map<String, dynamic>.from(response);
  }
}
