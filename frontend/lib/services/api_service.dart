import 'package:dio/dio.dart';
import '../utils/constants.dart';

/// Dio 기반 HTTP 클라이언트 서비스
/// JWT 인터셉터를 통한 자동 토큰 첨부 및 401 에러 처리
class ApiService {
  late Dio _dio;
  String? _token;

  // 401 응답 시 무한 재시도 방지 플래그
  bool _isRefreshing = false;
  bool _isForceLogout = false;  // BUG-22: forceLogout 중복 실행 방지

  // auth 관련 경로는 401 재시도 하지 않음 (logout storm 방지)
  static const List<String> _authSkipPaths = [
    '/auth/logout',
    '/auth/refresh',
    '/auth/login',
  ];

  // 로그인/로그아웃 콜백 (AuthService에서 주입)
  Future<bool> Function()? onRefreshToken;
  void Function()? onRefreshFailed;

  /// ApiService 생성자
  /// [baseUrl]을 지정하지 않으면 constants.dart의 apiBaseUrl 사용
  ApiService({String? baseUrl}) {
    _dio = Dio(
      BaseOptions(
        baseUrl: baseUrl ?? apiBaseUrl,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 15),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    // JWT 인터셉터 추가
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          // 토큰이 있으면 Authorization 헤더에 자동 첨부
          if (_token != null) {
            options.headers['Authorization'] = 'Bearer $_token';
          }
          return handler.next(options);
        },
        onResponse: (response, handler) {
          return handler.next(response);
        },
        onError: (error, handler) async {
          // 401 Unauthorized 에러 처리 — refresh token으로 재시도
          if (error.response?.statusCode == 401 && !_isRefreshing) {
            final requestPath = error.requestOptions.path;
            // auth 관련 경로는 401 재시도 하지 않음 (logout storm 방지)
            if (_authSkipPaths.any((p) => requestPath.contains(p))) {
              return handler.next(error);
            }
            // 이미 강제 로그아웃 중이면 바로 reject
            if (_isForceLogout) {
              return handler.next(error);
            }

            _isRefreshing = true;
            try {
              // refresh token으로 새 access token 발급 시도
              final refreshSuccess = await onRefreshToken?.call() ?? false;
              if (refreshSuccess && _token != null) {
                // 원래 요청을 새 토큰으로 재시도
                final retryOptions = error.requestOptions;
                retryOptions.headers['Authorization'] = 'Bearer $_token';
                final retryResponse = await _dio.fetch(retryOptions);
                return handler.resolve(retryResponse);
              } else {
                _forceLogout();
                return handler.next(error);
              }
            } catch (e) {
              _forceLogout();
              return handler.next(error);
            } finally {
              _isRefreshing = false;
            }
          }
          return handler.next(error);
        },
      ),
    );

    // 로깅 인터셉터 추가 (디버그 모드)
    _dio.interceptors.add(
      LogInterceptor(
        requestBody: true,
        responseBody: true,
        error: true,
        logPrint: (obj) => print('[Dio] $obj'),
      ),
    );
  }

  /// BUG-22: refresh 실패 시 1회만 실행되는 강제 로그아웃
  void _forceLogout() {
    if (_isForceLogout) return;
    _isForceLogout = true;
    clearToken();
    onRefreshFailed?.call();
  }

  /// JWT 토큰 설정
  void setToken(String token) {
    _token = token;
    _isForceLogout = false;  // 로그인 성공 → 리셋
  }

  /// JWT 토큰 제거
  void clearToken() {
    _token = null;
  }

  /// 현재 토큰 반환
  String? get token => _token;

  /// GET 요청
  /// [path]: API 경로 (예: '/auth/login')
  /// [queryParameters]: 쿼리 파라미터
  Future<dynamic> get(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    try {
      final response = await _dio.get(
        path,
        queryParameters: queryParameters,
      );
      return response.data;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// POST 요청
  /// [path]: API 경로
  /// [data]: 요청 바디
  Future<dynamic> post(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
  }) async {
    try {
      final response = await _dio.post(
        path,
        data: data,
        queryParameters: queryParameters,
      );
      return response.data;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// PUT 요청
  /// [path]: API 경로
  /// [data]: 요청 바디
  Future<dynamic> put(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
  }) async {
    try {
      final response = await _dio.put(
        path,
        data: data,
        queryParameters: queryParameters,
      );
      return response.data;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// DELETE 요청
  /// [path]: API 경로
  Future<dynamic> delete(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    try {
      final response = await _dio.delete(
        path,
        queryParameters: queryParameters,
      );
      return response.data;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// 인증 없이 GET 요청 (health check 등)
  ///
  /// Dio의 baseUrl(/api)을 우회하여 루트 경로로 요청.
  /// [path]: 루트 기준 경로 (예: '/health')
  Future<Map<String, dynamic>?> getPublic(String path) async {
    try {
      // apiBaseUrl에서 /api 제거하여 루트 URL 추출
      final rootUrl = apiBaseUrl.replaceAll(RegExp(r'/api$'), '');
      final dio = Dio(BaseOptions(
        connectTimeout: const Duration(seconds: 5),
        receiveTimeout: const Duration(seconds: 5),
      ));
      final response = await dio.get('$rootUrl$path');
      if (response.statusCode == 200 && response.data is Map) {
        return Map<String, dynamic>.from(response.data as Map);
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  /// DioException을 사용자 친화적인 에러 메시지로 변환
  Exception _handleError(DioException error) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
        return Exception('연결 시간 초과: 서버에 연결할 수 없습니다.');
      case DioExceptionType.sendTimeout:
        return Exception('요청 시간 초과: 요청을 보낼 수 없습니다.');
      case DioExceptionType.receiveTimeout:
        return Exception('응답 시간 초과: 서버 응답을 받을 수 없습니다.');
      case DioExceptionType.badResponse:
        // 서버 응답이 있는 경우 (4xx, 5xx)
        final statusCode = error.response?.statusCode;
        final message = error.response?.data?['message'] ??
                       error.response?.data?['error'] ??
                       '서버 오류가 발생했습니다.';
        if (statusCode == 401) {
          return Exception(message is String ? message : '인증 실패: 다시 로그인해주세요.');
        } else if (statusCode == 400) {
          // 서버 에러 코드 보존 (LOCATION_QR_REQUIRED 등 FE 분기 필요)
          final errorCode = error.response?.data?['error'] ?? '';
          if (errorCode.isNotEmpty) {
            return Exception('[$errorCode] $message');
          }
          return Exception('요청 오류: $message');
        } else if (statusCode == 403) {
          // 서버 에러 코드 보존 (APPROVAL_PENDING, APPROVAL_REJECTED 등 분기 필요)
          final errorCode = error.response?.data?['error'] ?? '';
          return Exception('[$errorCode] $message');
        } else if (statusCode == 404) {
          return Exception(message);
        } else if (statusCode == 500) {
          return Exception('서버 오류: $message');
        }
        return Exception('오류 ($statusCode): $message');
      case DioExceptionType.cancel:
        return Exception('요청이 취소되었습니다.');
      case DioExceptionType.badCertificate:
        return Exception('보안 인증서 오류: 안전하지 않은 연결입니다.');
      case DioExceptionType.connectionError:
        return Exception('네트워크 연결 오류: 인터넷 연결을 확인해주세요.');
      default:
        return Exception('알 수 없는 오류가 발생했습니다: ${error.message}');
    }
  }
}
