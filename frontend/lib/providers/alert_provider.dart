import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/alert_log.dart';
import '../services/alert_service.dart';
import '../services/notification_feedback_service.dart';
import '../services/websocket_service.dart';
import 'auth_provider.dart';

/// Alert 상태 클래스
///
/// 알림 목록, 안읽은 알림 수, 로딩 상태, 에러 메시지 등을 관리
class AlertState {
  final bool isLoading;
  final List<AlertLog> alerts;
  final String? errorMessage;
  final int unreadCount;

  const AlertState({
    this.isLoading = false,
    this.alerts = const [],
    this.errorMessage,
    this.unreadCount = 0,
  });

  AlertState copyWith({
    bool? isLoading,
    List<AlertLog>? alerts,
    String? errorMessage,
    int? unreadCount,
    bool clearError = false,
    bool clearAlerts = false,
  }) {
    return AlertState(
      isLoading: isLoading ?? this.isLoading,
      alerts: clearAlerts ? const [] : (alerts ?? this.alerts),
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
      unreadCount: unreadCount ?? this.unreadCount,
    );
  }

  /// 우선순위 높은 순으로 정렬된 알림 목록
  List<AlertLog> get sortedAlerts {
    final list = List<AlertLog>.from(alerts);
    list.sort((a, b) {
      // 1. 읽지 않은 알림 우선
      if (a.isRead != b.isRead) {
        return a.isRead ? 1 : -1;
      }
      // 2. 우선순위 높은 순
      if (a.priority != b.priority) {
        return b.priority.compareTo(a.priority);
      }
      // 3. 최신 순
      return b.createdAt.compareTo(a.createdAt);
    });
    return list;
  }

  @override
  String toString() {
    return 'AlertState(isLoading: $isLoading, alerts: ${alerts.length}, '
        'unreadCount: $unreadCount, error: $errorMessage)';
  }
}

/// Alert 상태 관리 Notifier
///
/// 알림 목록 조회, 읽음 처리, WebSocket 실시간 알림 구독 등의 비즈니스 로직 처리
class AlertNotifier extends StateNotifier<AlertState> {
  final AlertService _alertService;

  AlertNotifier(this._alertService) : super(const AlertState());

  /// 알림 목록 조회
  ///
  /// [unreadOnly]: true일 경우 안읽은 알림만 조회
  ///
  /// Returns: 조회 성공 여부
  Future<bool> fetchAlerts({bool unreadOnly = false}) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final alerts = await _alertService.getAlerts(unreadOnly: unreadOnly);
      state = state.copyWith(
        isLoading: false,
        alerts: alerts,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.toString(),
      );
      return false;
    }
  }

  /// 알림 읽음 처리
  ///
  /// [alertId]: 알림 ID
  ///
  /// Returns: 읽음 처리 성공 여부
  Future<bool> markAsRead(int alertId) async {
    try {
      final updatedAlert = await _alertService.markAsRead(alertId);

      // 알림 목록 업데이트
      final updatedAlerts = state.alerts.map((alert) {
        return alert.id == alertId ? updatedAlert : alert;
      }).toList();

      // 안읽은 알림 수 감소
      final newUnreadCount = state.unreadCount > 0 ? state.unreadCount - 1 : 0;

      state = state.copyWith(
        alerts: updatedAlerts,
        unreadCount: newUnreadCount,
      );
      return true;
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
      return false;
    }
  }

  /// 모든 알림 읽음 처리
  ///
  /// Returns: 읽음 처리 성공 여부
  Future<bool> markAllAsRead() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      await _alertService.markAllAsRead();

      // 모든 알림을 읽음 상태로 업데이트
      final updatedAlerts = state.alerts.map((alert) {
        return alert.copyWith(
          isRead: true,
          readAt: DateTime.now(),
        );
      }).toList();

      state = state.copyWith(
        isLoading: false,
        alerts: updatedAlerts,
        unreadCount: 0,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.toString(),
      );
      return false;
    }
  }

  /// 안읽은 알림 수 조회
  ///
  /// Returns: 조회 성공 여부
  Future<bool> refreshUnreadCount() async {
    try {
      final count = await _alertService.getUnreadCount();
      state = state.copyWith(unreadCount: count);
      return true;
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
      return false;
    }
  }

  /// 알림 삭제 (관리자 전용)
  ///
  /// [alertId]: 알림 ID
  ///
  /// Returns: 삭제 성공 여부
  Future<bool> deleteAlert(int alertId) async {
    try {
      await _alertService.deleteAlert(alertId);

      // 알림 목록에서 제거
      final updatedAlerts = state.alerts.where((alert) => alert.id != alertId).toList();

      state = state.copyWith(alerts: updatedAlerts);
      return true;
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
      return false;
    }
  }

  /// WebSocket 실시간 알림 구독
  ///
  /// [websocketService]: WebSocket 서비스 인스턴스
  ///
  /// new_alert, process_alert, duration_alert 이벤트를 구독
  void subscribeToAlerts(WebSocketService websocketService) {
    // new_alert 이벤트 구독 (일반 알림)
    websocketService.on('new_alert', (data) {
      _handleNewAlert(data);
    });

    // process_alert 이벤트 구독 (공정 경고)
    websocketService.on('process_alert', (data) {
      _handleNewAlert(data);
    });

    // duration_alert 이벤트 구독 (비정상 소요시간 경고)
    websocketService.on('duration_alert', (data) {
      _handleNewAlert(data);
    });

    print('[AlertProvider] Subscribed to WebSocket alerts');
  }

  /// WebSocket 알림 구독 해제
  void unsubscribeFromAlerts(WebSocketService websocketService) {
    websocketService.removeAllListeners('new_alert');
    websocketService.removeAllListeners('process_alert');
    websocketService.removeAllListeners('duration_alert');
    print('[AlertProvider] Unsubscribed from WebSocket alerts');
  }

  /// 새 알림 수신 처리
  ///
  /// WebSocket으로부터 받은 알림 데이터를 state에 추가
  void _handleNewAlert(dynamic data) {
    try {
      final newAlert = AlertLog.fromJson(data as Map<String, dynamic>);

      // 중복 알림 체크 (같은 ID가 이미 존재하는지)
      final exists = state.alerts.any((alert) => alert.id == newAlert.id);
      if (exists) {
        print('[AlertProvider] Duplicate alert received: ${newAlert.id}');
        return;
      }

      // 알림 목록에 추가 (최신 알림이 앞에 오도록)
      final updatedAlerts = [newAlert, ...state.alerts];

      // 안읽은 알림 수 증가
      final newUnreadCount = state.unreadCount + 1;

      state = state.copyWith(
        alerts: updatedAlerts,
        unreadCount: newUnreadCount,
      );

      // 포그라운드 알림 피드백 (소리 + 진동)
      NotificationFeedbackService.instance.playAlertFeedback(
        alertType: newAlert.alertType,
      );

      print('[AlertProvider] New alert received: ${newAlert.alertType}');
    } catch (e) {
      print('[AlertProvider] Failed to handle new alert: $e');
    }
  }

  /// 에러 메시지 클리어
  void clearError() {
    state = state.copyWith(clearError: true);
  }

  /// 알림 목록 클리어
  void clearAlerts() {
    state = state.copyWith(clearAlerts: true, unreadCount: 0);
  }
}

/// AlertService Provider — 공유 ApiService 사용 (JWT 토큰 공유)
final alertServiceProvider = Provider<AlertService>((ref) {
  final apiService = ref.watch(apiServiceProvider);
  return AlertService(apiService: apiService);
});

/// AlertNotifier Provider
final alertProvider = StateNotifierProvider<AlertNotifier, AlertState>((ref) {
  final alertService = ref.watch(alertServiceProvider);
  return AlertNotifier(alertService);
});
