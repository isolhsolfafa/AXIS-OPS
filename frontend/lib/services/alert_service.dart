import 'api_service.dart';
import '../models/alert_log.dart';

/// Alert 서비스
///
/// 알림 목록 조회, 읽음 처리, 안읽은 알림 수 조회 등을 담당
class AlertService {
  final ApiService _apiService;

  AlertService({ApiService? apiService})
      : _apiService = apiService ?? ApiService();

  /// 알림 목록 조회
  ///
  /// [unreadOnly]: true일 경우 안읽은 알림만 조회
  ///
  /// Returns: AlertLog 객체 리스트
  ///
  /// API: GET /api/app/alerts?unread_only={unreadOnly}
  /// Response: [{"id": 1, "alert_type": "PROCESS_READY", ...}, ...]
  Future<List<AlertLog>> getAlerts({bool unreadOnly = false}) async {
    try {
      final queryParams = unreadOnly ? {'unread_only': 'true'} : null;
      final response = await _apiService.get(
        '/app/alerts',
        queryParameters: queryParams,
      );

      // BE 응답이 리스트인지 확인
      if (response is List) {
        return response.map((json) => AlertLog.fromJson(json)).toList();
      } else if (response is Map && response['alerts'] != null) {
        return (response['alerts'] as List)
            .map((json) => AlertLog.fromJson(json))
            .toList();
      }

      return [];
    } catch (e) {
      rethrow;
    }
  }

  /// 알림 읽음 처리
  ///
  /// [alertId]: 알림 ID
  ///
  /// Returns: 업데이트된 AlertLog 객체
  ///
  /// API: PUT /api/app/alerts/{id}/read
  /// Response: {"id": 1, "is_read": true, "read_at": "2026-02-16T10:00:00Z", ...}
  Future<AlertLog> markAsRead(int alertId) async {
    try {
      final response = await _apiService.put('/app/alerts/$alertId/read');
      return AlertLog.fromJson(response);
    } catch (e) {
      rethrow;
    }
  }

  /// 모든 알림 읽음 처리
  ///
  /// Returns: 업데이트된 알림 수
  ///
  /// API: PUT /api/app/alerts/read-all
  /// Response: {"updated_count": 5, "message": "5개 알림을 읽음 처리했습니다."}
  Future<int> markAllAsRead() async {
    try {
      final response = await _apiService.put('/app/alerts/read-all');
      return response['updated_count'] as int? ?? 0;
    } catch (e) {
      rethrow;
    }
  }

  /// 안읽은 알림 수 조회
  ///
  /// Returns: 안읽은 알림 수
  ///
  /// API: GET /api/app/alerts/unread-count
  /// Response: {"unread_count": 3}
  Future<int> getUnreadCount() async {
    try {
      final response = await _apiService.get('/app/alerts/unread-count');
      return response['unread_count'] as int? ?? 0;
    } catch (e) {
      rethrow;
    }
  }

  /// 알림 삭제 (관리자 전용)
  ///
  /// [alertId]: 알림 ID
  ///
  /// Returns: 삭제 성공 여부
  ///
  /// API: DELETE /api/app/alerts/{id}
  /// Response: {"message": "알림이 삭제되었습니다."}
  Future<bool> deleteAlert(int alertId) async {
    try {
      await _apiService.delete('/app/alerts/$alertId');
      return true;
    } catch (e) {
      rethrow;
    }
  }
}
