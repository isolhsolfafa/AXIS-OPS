import 'package:shared_preferences/shared_preferences.dart';
import '../utils/app_version.dart';
import 'notice_service.dart';

/// 버전 업데이트 감지 + 공지 조회
class UpdateService {
  final NoticeService _noticeService;
  static const _lastSeenVersionKey = 'last_seen_app_version';

  UpdateService(this._noticeService);

  /// 앱 시작 시 호출: 새 버전이면 해당 버전의 공지를 반환
  /// 새 버전이 아니거나 공지가 없으면 null 반환
  Future<Map<String, dynamic>?> checkForUpdateNotice() async {
    final prefs = await SharedPreferences.getInstance();
    final lastSeen = prefs.getString(_lastSeenVersionKey);

    // 같은 버전이면 스킵
    if (lastSeen == AppVersion.version) return null;

    // 새 버전 감지 → 버전 저장 (다음엔 안 뜨도록)
    await prefs.setString(_lastSeenVersionKey, AppVersion.version);

    // 해당 버전의 공지 조회
    try {
      final result = await _noticeService.getNotices(
        page: 1,
        limit: 1,
        version: AppVersion.version,
      );
      final notices = result['notices'] as List<dynamic>? ?? [];
      if (notices.isNotEmpty) {
        return notices.first as Map<String, dynamic>;
      }
    } catch (e) {
      // 네트워크 에러 시 무시 — 팝업 없이 진행
    }
    return null;
  }
}
