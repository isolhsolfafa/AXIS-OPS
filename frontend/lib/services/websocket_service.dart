import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../utils/constants.dart';

/// WebSocket 서비스
///
/// 실시간 이벤트 수신 (공정 경고, 알림 등)
/// PWA 웹 호환: web_socket_channel 패키지 사용
///
/// 지원 이벤트:
/// - task_completed: 작업 완료 이벤트
/// - process_alert: 공정 경고 (다음 공정 준비 등)
/// - new_alert: 새 알림 생성
/// - duration_alert: 비정상 소요시간 경고
class WebSocketService {
  WebSocketChannel? _channel;
  final Map<String, List<Function(dynamic)>> _eventListeners = {};
  Timer? _reconnectTimer;
  Timer? _heartbeatTimer;
  bool _isConnected = false;
  bool _shouldReconnect = true;
  String? _authToken;
  int _reconnectAttempts = 0;
  static const int maxReconnectAttempts = 2;
  static const Duration reconnectDelay = Duration(seconds: 10);
  static const Duration heartbeatInterval = Duration(seconds: 30);

  /// 연결 상태 스트림
  final _connectionController = StreamController<bool>.broadcast();
  Stream<bool> get connectionStream => _connectionController.stream;

  /// 현재 연결 상태
  bool get isConnected => _isConnected;

  /// WebSocket 연결
  ///
  /// [token]: JWT 인증 토큰
  ///
  /// 연결 성공 시 자동으로 heartbeat 시작
  /// 연결 실패 시 자동 재연결 (최대 5회)
  Future<void> connect(String token) async {
    if (_isConnected) {
      print('[WebSocket] Already connected');
      return;
    }

    _authToken = token;
    _shouldReconnect = true;

    try {
      // WebSocket URL with JWT token
      final uri = Uri.parse('$webSocketUrl?token=$token');

      print('[WebSocket] Connecting to $uri');
      _channel = WebSocketChannel.connect(uri);

      // 연결 성공
      _isConnected = true;
      _reconnectAttempts = 0;
      _connectionController.add(true);
      print('[WebSocket] Connected successfully');

      // Heartbeat 시작
      _startHeartbeat();

      // 메시지 수신 리스너
      _channel!.stream.listen(
        _handleMessage,
        onError: (error) {
          print('[WebSocket] Error: $error');
          _handleDisconnect();
        },
        onDone: () {
          print('[WebSocket] Connection closed');
          _handleDisconnect();
        },
        cancelOnError: false,
      );
    } catch (e) {
      print('[WebSocket] Connection failed: $e');
      _handleDisconnect();
    }
  }

  /// WebSocket 연결 해제
  void disconnect() {
    _shouldReconnect = false;
    _cleanup();
  }

  /// 이벤트 리스너 등록
  ///
  /// [eventName]: 이벤트 이름 (task_completed, process_alert, new_alert 등)
  /// [callback]: 이벤트 콜백 함수
  ///
  /// Example:
  /// ```dart
  /// websocketService.on('process_alert', (data) {
  ///   final alert = AlertLog.fromJson(data);
  ///   // 경고 팝업 표시
  /// });
  /// ```
  void on(String eventName, Function(dynamic) callback) {
    if (!_eventListeners.containsKey(eventName)) {
      _eventListeners[eventName] = [];
    }
    _eventListeners[eventName]!.add(callback);
    print('[WebSocket] Listener registered for event: $eventName');
  }

  /// 이벤트 리스너 제거
  void off(String eventName, Function(dynamic) callback) {
    if (_eventListeners.containsKey(eventName)) {
      _eventListeners[eventName]!.remove(callback);
      print('[WebSocket] Listener removed for event: $eventName');
    }
  }

  /// 모든 이벤트 리스너 제거
  void removeAllListeners([String? eventName]) {
    if (eventName != null) {
      _eventListeners.remove(eventName);
    } else {
      _eventListeners.clear();
    }
  }

  /// 메시지 전송
  ///
  /// [eventName]: 이벤트 이름
  /// [data]: 전송할 데이터
  void emit(String eventName, dynamic data) {
    if (!_isConnected || _channel == null) {
      print('[WebSocket] Not connected. Cannot send message.');
      return;
    }

    try {
      final message = jsonEncode({
        'event': eventName,
        'data': data,
      });
      _channel!.sink.add(message);
      print('[WebSocket] Message sent: $eventName');
    } catch (e) {
      print('[WebSocket] Failed to send message: $e');
    }
  }

  /// 메시지 수신 처리
  void _handleMessage(dynamic message) {
    try {
      final data = jsonDecode(message as String);
      final eventName = data['event'] as String?;
      final payload = data['data'];

      if (eventName == null) {
        print('[WebSocket] Received message without event name');
        return;
      }

      print('[WebSocket] Received event: $eventName');

      // Pong 응답 처리 (heartbeat)
      if (eventName == 'pong') {
        return;
      }

      // 등록된 리스너 실행
      if (_eventListeners.containsKey(eventName)) {
        for (final callback in _eventListeners[eventName]!) {
          callback(payload);
        }
      }
    } catch (e) {
      print('[WebSocket] Failed to parse message: $e');
    }
  }

  /// 연결 해제 처리
  void _handleDisconnect() {
    _isConnected = false;
    _connectionController.add(false);
    _stopHeartbeat();

    // 자동 재연결
    if (_shouldReconnect && _reconnectAttempts < maxReconnectAttempts) {
      _reconnectAttempts++;
      print('[WebSocket] Reconnecting... (attempt $_reconnectAttempts/$maxReconnectAttempts)');

      _reconnectTimer = Timer(reconnectDelay, () {
        if (_authToken != null) {
          connect(_authToken!);
        }
      });
    } else if (_reconnectAttempts >= maxReconnectAttempts) {
      print('[WebSocket] Max reconnect attempts reached. Giving up.');
    }
  }

  /// Heartbeat 시작 (연결 유지)
  void _startHeartbeat() {
    _stopHeartbeat();
    _heartbeatTimer = Timer.periodic(heartbeatInterval, (timer) {
      if (_isConnected) {
        emit('ping', {});
      }
    });
  }

  /// Heartbeat 중지
  void _stopHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
  }

  /// 리소스 정리
  void _cleanup() {
    _isConnected = false;
    _connectionController.add(false);
    _stopHeartbeat();
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    _channel?.sink.close();
    _channel = null;
    print('[WebSocket] Cleaned up');
  }

  /// 서비스 종료
  void dispose() {
    _shouldReconnect = false;
    _cleanup();
    _connectionController.close();
    _eventListeners.clear();
  }
}
