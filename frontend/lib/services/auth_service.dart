import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'api_service.dart';
import '../utils/constants.dart';

/// 인증 서비스
/// 로그인, 회원가입, 이메일 인증, 토큰 관리 등을 담당
class AuthService {
  final ApiService _apiService;
  final _secureStorage = const FlutterSecureStorage();

  static const String _tokenKey = 'auth_token';
  static const String _refreshTokenKey = 'refresh_token';
  static const String _workerIdKey = 'worker_id';
  static const String _workerRoleKey = 'worker_role';
  static const String _workerDataKey = 'worker_data';

  AuthService({ApiService? apiService})
      : _apiService = apiService ?? ApiService();

  /// 로그인
  ///
  /// [email]: 사용자 이메일
  /// [password]: 비밀번호
  ///
  /// Returns: 로그인 성공 시 worker 데이터 포함한 Map, 실패 시 Exception
  ///
  /// Response: {"access_token": str, "worker_id": int, "role": str, "name": str}
  Future<Map<String, dynamic>> login(String email, String password) async {
    try {
      final response = await _apiService.post(
        authLoginEndpoint,
        data: {
          'email': email,
          'password': password,
        },
      );

      // 토큰 저장
      if (response['access_token'] != null) {
        await _secureStorage.write(
          key: _tokenKey,
          value: response['access_token'],
        );
        _apiService.setToken(response['access_token']);
      }

      // Worker ID와 Role 저장
      if (response['worker_id'] != null) {
        await _secureStorage.write(
          key: _workerIdKey,
          value: response['worker_id'].toString(),
        );
      }

      if (response['role'] != null) {
        await _secureStorage.write(
          key: _workerRoleKey,
          value: response['role'],
        );
      }

      // Worker 전체 데이터 저장
      await _secureStorage.write(
        key: _workerDataKey,
        value: jsonEncode(response),
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
  /// [role]: 역할 (MM, EE, TM, PI, QI, SI)
  ///
  /// Returns: 회원가입 성공 시 worker_id, 실패 시 Exception
  ///
  /// Response: {"message": "회원가입 완료, 이메일 인증 필요", "worker_id": int}
  Future<Map<String, dynamic>> register({
    required String name,
    required String email,
    required String password,
    required String role,
  }) async {
    try {
      final response = await _apiService.post(
        authRegisterEndpoint,
        data: {
          'name': name,
          'email': email,
          'password': password,
          'role': role,
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

  /// 로그아웃
  ///
  /// 로컬 저장된 토큰 및 사용자 데이터 삭제
  Future<void> logout() async {
    try {
      // API 호출 (서버 측 토큰 무효화)
      // TODO: BE에서 logout 엔드포인트 구현 시 활성화
      // await _apiService.post(authLogoutEndpoint);

      // ApiService 토큰 제거
      _apiService.clearToken();

      // 로컬 저장소 데이터 삭제
      await _secureStorage.delete(key: _tokenKey);
      await _secureStorage.delete(key: _refreshTokenKey);
      await _secureStorage.delete(key: _workerIdKey);
      await _secureStorage.delete(key: _workerRoleKey);
      await _secureStorage.delete(key: _workerDataKey);
    } catch (e) {
      // 로그아웃은 실패해도 로컬 데이터 삭제
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
  /// TODO: Sprint 2에서 구현 예정
  /// BE의 /auth/refresh-token 엔드포인트 구현 후 활성화
  Future<bool> refreshToken() async {
    try {
      final refreshToken = await _secureStorage.read(key: _refreshTokenKey);
      if (refreshToken == null) {
        return false;
      }

      // TODO: Sprint 2에서 구현
      // final response = await _apiService.post(
      //   '/auth/refresh-token',
      //   data: {'refresh_token': refreshToken},
      // );
      //
      // if (response['access_token'] != null) {
      //   await saveToken(response['access_token']);
      //   return true;
      // }

      return false;
    } catch (e) {
      return false;
    }
  }
}
