import 'package:dio/dio.dart';
import '../utils/constants.dart';

/// Dio 기반 HTTP 클라이언트 서비스
/// JWT 인터셉터를 통한 자동 토큰 첨부 및 401 에러 처리
class ApiService {
  late Dio _dio;
  String? _token;

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
          // 정상 응답 처리
          return handler.next(response);
        },
        onError: (error, handler) async {
          // 401 Unauthorized 에러 처리
          if (error.response?.statusCode == 401) {
            // 토큰 만료 또는 인증 실패 시 토큰 클리어
            clearToken();
            // TODO: Sprint 2에서 refresh token 구현 시 갱신 로직 추가
            // 현재는 로그아웃 처리만 수행 (AuthProvider에서 처리)
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

  /// JWT 토큰 설정
  void setToken(String token) {
    _token = token;
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
          return Exception('인증 실패: 다시 로그인해주세요.');
        } else if (statusCode == 403) {
          return Exception('권한 없음: 접근 권한이 없습니다.');
        } else if (statusCode == 404) {
          return Exception('찾을 수 없음: 요청한 리소스가 없습니다.');
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
