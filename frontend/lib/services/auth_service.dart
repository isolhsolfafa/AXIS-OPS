import 'dart:convert';
import 'dart:math';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'api_service.dart';
import '../utils/constants.dart';

/// 인증 서비스
/// 로그인, 회원가입, 이메일 인증, 토큰 관리, 자동 로그인 등을 담당
class AuthService {
  final ApiService _apiService;
  final _secureStorage = const FlutterSecureStorage();

  static const String _tokenKey = 'auth_token';
  static const String _refreshTokenKey = 'refresh_token';
  static const String _workerIdKey = 'worker_id';
  static const String _workerRoleKey = 'worker_role';
  static const String _workerDataKey = 'worker_data';
  static const String _pinRegisteredKey = 'pin_registered';
  static const String _deviceIdKey = 'axis_device_id';

  /// SharedPreferences 키 — 마지막 방문 경로 복원용
  static const String _lastRouteKey = 'last_route';
  static const String _lastRouteArgsKey = 'last_route_args';

  AuthService({ApiService? apiService})
      : _apiService = apiService ?? ApiService() {
    // ApiService에 refresh 콜백 주입
    _apiService.onRefreshToken = refreshToken;
  }

  /// refresh 실패 시 호출될 콜백 설정 (AuthNotifier에서 로그아웃 트리거)
  set onRefreshFailed(void Function() callback) {
    _apiService.onRefreshFailed = callback;
  }

  /// Sprint 19-A: 기기 고유 ID 반환 (최초 생성 후 SharedPreferences에 영구 저장)
  Future<String> getDeviceId() async {
    final prefs = await SharedPreferences.getInstance();
    var id = prefs.getString(_deviceIdKey);
    if (id == null || id.isEmpty) {
      id = _generateUuid();
      await prefs.setString(_deviceIdKey, id);
    }
    return id;
  }

  /// UUID v4 생성 (외부 패키지 없이 dart:math 사용)
  static String _generateUuid() {
    final rng = Random.secure();
    final bytes = List<int>.generate(16, (_) => rng.nextInt(256));
    bytes[6] = (bytes[6] & 0x0f) | 0x40; // version 4
    bytes[8] = (bytes[8] & 0x3f) | 0x80; // variant 1
    final hex = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
    return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-'
        '${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
  }

  /// 로그인
  ///
  /// [email]: 사용자 이메일
  /// [password]: 비밀번호
  ///
  /// Returns: 로그인 성공 시 worker 데이터 포함한 Map, 실패 시 Exception
  ///
  /// Response: {"access_token": str, "refresh_token": str, "worker": {...}}
  Future<Map<String, dynamic>> login(String email, String password) async {
    try {
      final deviceId = await getDeviceId();
      final response = await _apiService.post(
        authLoginEndpoint,
        data: {
          'email': email,
          'password': password,
          'device_id': deviceId,
        },
      );

      // access_token 저장
      if (response['access_token'] != null) {
        await _secureStorage.write(
          key: _tokenKey,
          value: response['access_token'],
        );
        _apiService.setToken(response['access_token']);
      }

      // refresh_token 저장
      if (response['refresh_token'] != null) {
        await _secureStorage.write(
          key: _refreshTokenKey,
          value: response['refresh_token'],
        );
      }

      // Worker 데이터 추출 (응답: {"access_token": ..., "worker": {...}})
      final workerData = response['worker'] as Map<String, dynamic>? ?? response;

      // Worker ID와 Role 저장
      if (workerData['id'] != null) {
        await _secureStorage.write(
          key: _workerIdKey,
          value: workerData['id'].toString(),
        );
      }

      if (workerData['role'] != null) {
        await _secureStorage.write(
          key: _workerRoleKey,
          value: workerData['role'],
        );
      }

      // Worker 전체 데이터 저장
      await _secureStorage.write(
        key: _workerDataKey,
        value: jsonEncode(workerData),
      );

      return response;
    } catch (e) {
      rethrow;
    }
  }

  /// 회원가입
  ///
  /// [name]: 사용자 이름
  /// [email]: 이메일
  /// [password]: 비밀번호
  /// [role]: 역할 (MECH, ELEC, TM, PI, QI, SI)
  /// [company]: 협력사 (FNI, BAT, TMS(M), TMS(E), P&S, C&A, GST)
  ///
  /// Returns: 회원가입 성공 시 worker_id, 실패 시 Exception
  ///
  /// Response: {"message": "회원가입 완료, 이메일 인증 필요", "worker_id": int}
  Future<Map<String, dynamic>> register({
    required String name,
    required String email,
    required String password,
    required String role,
    required String company,
  }) async {
    try {
      final response = await _apiService.post(
        authRegisterEndpoint,
        data: {
          'name': name,
          'email': email,
          'password': password,
          'role': role,
          'company': company,
        },
      );

      return response;
    } catch (e) {
      rethrow;
    }
  }

  /// 이메일 인증
  ///
  /// [email]: 사용자 이메일
  /// [code]: 6자리 인증 코드
  ///
  /// Returns: 인증 성공 시 true, 실패 시 Exception
  ///
  /// Response: {"message": "이메일 인증 완료"}
  Future<Map<String, dynamic>> verifyEmail({
    required String email,
    required String code,
  }) async {
    try {
      final response = await _apiService.post(
        authVerifyEmailEndpoint,
        data: {
          'email': email,
          'code': code,
        },
      );

      return response;
    } catch (e) {
      rethrow;
    }
  }

  /// 이메일 인증 코드 재전송 (Sprint 22-A)
  ///
  /// [email]: 사용자 이메일
  ///
  /// Returns: 성공 시 response map, 실패 시 Exception
  Future<Map<String, dynamic>> resendVerification({
    required String email,
  }) async {
    try {
      final response = await _apiService.post(
        authResendVerificationEndpoint,
        data: {'email': email},
      );
      return response;
    } catch (e) {
      rethrow;
    }
  }

  /// 로그아웃
  ///
  /// Sprint 19-B: 서버에 refresh_token 무효화 요청 후 로컬 데이터 삭제
  Future<void> logout() async {
    try {
      // 서버에 로그아웃 요청 (refresh_token 무효화)
      final storedRefreshToken = await _secureStorage.read(key: _refreshTokenKey);
      try {
        await _apiService.post(
          authLogoutEndpoint,
          data: {
            if (storedRefreshToken != null) 'refresh_token': storedRefreshToken,
          },
        );
      } catch (_) {
        // 서버 요청 실패해도 로컬 로그아웃은 계속 진행
      }

      _apiService.clearToken();

      await _secureStorage.delete(key: _tokenKey);
      await _secureStorage.delete(key: _refreshTokenKey);
      await _secureStorage.delete(key: _workerIdKey);
      await _secureStorage.delete(key: _workerRoleKey);
      await _secureStorage.delete(key: _workerDataKey);
      await _secureStorage.delete(key: _pinRegisteredKey);

      // 마지막 경로도 삭제
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_lastRouteKey);
      await prefs.remove(_lastRouteArgsKey);
    } catch (e) {
      await _secureStorage.deleteAll();
      rethrow;
    }
  }

  /// 저장된 토큰 가져오기
  Future<String?> getToken() async {
    final token = await _secureStorage.read(key: _tokenKey);
    if (token != null) {
      _apiService.setToken(token);
    }
    return token;
  }

  /// 저장된 Worker ID 가져오기
  Future<int?> getWorkerId() async {
    final id = await _secureStorage.read(key: _workerIdKey);
    return id != null ? int.tryParse(id) : null;
  }

  /// 저장된 Worker Role 가져오기
  Future<String?> getWorkerRole() async {
    return await _secureStorage.read(key: _workerRoleKey);
  }

  /// 저장된 Worker 데이터 가져오기
  Future<Map<String, dynamic>?> getWorkerData() async {
    final data = await _secureStorage.read(key: _workerDataKey);
    if (data != null) {
      return jsonDecode(data);
    }
    return null;
  }

  /// 토큰 존재 여부 확인 (로그인 상태 체크)
  Future<bool> isLoggedIn() async {
    final token = await getToken();
    return token != null && token.isNotEmpty;
  }

  /// 토큰 저장 (외부에서 직접 저장 시 사용)
  Future<void> saveToken(String token) async {
    await _secureStorage.write(key: _tokenKey, value: token);
    _apiService.setToken(token);
  }

  /// 리프레시 토큰 저장
  Future<void> saveRefreshToken(String refreshToken) async {
    await _secureStorage.write(key: _refreshTokenKey, value: refreshToken);
  }

  /// 토큰 갱신
  ///
  /// 저장된 refresh_token으로 새 access_token 발급
  /// 성공 시 새 토큰을 저장하고 true 반환, 실패 시 false 반환
  Future<bool> refreshToken() async {
    try {
      final storedRefreshToken = await _secureStorage.read(key: _refreshTokenKey);
      if (storedRefreshToken == null || storedRefreshToken.isEmpty) {
        return false;
      }

      final deviceId = await getDeviceId();
      final response = await _apiService.post(
        authRefreshEndpoint,
        data: {
          'refresh_token': storedRefreshToken,
          'device_id': deviceId,
        },
      );

      if (response['access_token'] != null) {
        await saveToken(response['access_token']);
        // 새 refresh_token이 응답에 포함되면 함께 저장
        if (response['refresh_token'] != null) {
          await saveRefreshToken(response['refresh_token']);
        }
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }

  // ── PIN 자동 로그인 분기 ──────────────────────────────────────────────

  /// refresh_token 존재 여부 확인 (자동 로그인 가능한 사용자인지)
  Future<bool> hasRefreshToken() async {
    final token = await _secureStorage.read(key: _refreshTokenKey);
    return token != null && token.isNotEmpty;
  }

  /// PIN 등록 여부 확인 (로컬 캐시)
  ///
  /// PIN 설정 시 savePinRegistered(true) 호출로 캐시됨
  /// 로그아웃 시 삭제됨
  Future<bool> hasPinRegistered() async {
    final value = await _secureStorage.read(key: _pinRegisteredKey);
    return value == 'true';
  }

  /// PIN 등록 상태 저장 (PIN 설정/해제 시 호출)
  Future<void> savePinRegistered(bool registered) async {
    await _secureStorage.write(
      key: _pinRegisteredKey,
      value: registered.toString(),
    );
  }

  /// 앱 시작 시 자동 로그인 시도
  ///
  /// 저장된 refresh_token으로 새 access_token을 발급받아 자동 로그인
  /// 성공 시 true, 실패(토큰 없음 또는 만료) 시 false 반환
  Future<bool> tryAutoLogin() async {
    try {
      final refreshTokenValue = await _secureStorage.read(key: _refreshTokenKey);
      if (refreshTokenValue == null || refreshTokenValue.isEmpty) {
        return false;
      }

      final success = await refreshToken();
      if (!success) {
        // refresh 실패 → 저장된 데이터 클리어
        await logout();
        return false;
      }
      return true;
    } catch (e) {
      return false;
    }
  }

  // ── 현재 사용자 정보 조회 ──────────────────────────────────────────────

  /// 현재 로그인 사용자 정보 조회 (서버에서 fresh data 가져오기)
  ///
  /// Response: {"worker": {...}}
  Future<Map<String, dynamic>> getMe() async {
    try {
      final response = await _apiService.get('/auth/me');
      final workerData = response['worker'] as Map<String, dynamic>? ?? response;
      // 최신 worker 데이터 저장
      await _secureStorage.write(
        key: _workerDataKey,
        value: jsonEncode(workerData),
      );
      return workerData;
    } catch (e) {
      rethrow;
    }
  }

  /// GST 작업자 활성 역할 변경
  ///
  /// [role]: 변경할 역할 (PI, QI, SI)
  ///
  /// Response: {"message": "...", "worker": {...}}
  Future<Map<String, dynamic>> changeActiveRole(String role) async {
    try {
      final response = await _apiService.put(
        '/auth/active-role',
        data: {'active_role': role},
      );
      final workerData = response['worker'] as Map<String, dynamic>?;
      if (workerData != null) {
        // 업데이트된 worker 데이터 저장
        await _secureStorage.write(
          key: _workerDataKey,
          value: jsonEncode(workerData),
        );
      }
      return response;
    } catch (e) {
      rethrow;
    }
  }

  // ── 마지막 경로 저장/복원 ──────────────────────────────────────────────

  /// 마지막 방문 경로 저장
  ///
  /// 로그인 필요 화면(/login, /register 등)은 저장하지 않음
  Future<void> saveLastRoute(String routeName, [Map<String, dynamic>? args]) async {
    // 저장 제외 경로
    const excludedRoutes = {
      '/login',
      '/register',
      '/verify-email',
      '/splash',
      '/forgot-password',
      '/reset-password',
    };
    if (excludedRoutes.contains(routeName)) return;

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_lastRouteKey, routeName);
    if (args != null) {
      await prefs.setString(_lastRouteArgsKey, jsonEncode(args));
    } else {
      await prefs.remove(_lastRouteArgsKey);
    }
  }

  /// 마지막 방문 경로 가져오기
  ///
  /// Returns: {route: String, args: Map?} 또는 null
  Future<Map<String, dynamic>?> getLastRoute() async {
    final prefs = await SharedPreferences.getInstance();
    final route = prefs.getString(_lastRouteKey);
    if (route == null) return null;

    final argsJson = prefs.getString(_lastRouteArgsKey);
    Map<String, dynamic>? args;
    if (argsJson != null) {
      args = jsonDecode(argsJson) as Map<String, dynamic>;
    }

    return {'route': route, 'args': args};
  }
}
