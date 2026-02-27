import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/worker.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';

/// 인증 상태 클래스
///
/// 로그인 상태, 로딩 상태, 에러 메시지, 현재 사용자 정보 등을 관리
class AuthState {
  final bool isLoading;
  final bool isAuthenticated;
  final String? errorMessage;
  final Worker? currentWorker;

  const AuthState({
    this.isLoading = false,
    this.isAuthenticated = false,
    this.errorMessage,
    this.currentWorker,
  });

  AuthState copyWith({
    bool? isLoading,
    bool? isAuthenticated,
    String? errorMessage,
    Worker? currentWorker,
    bool clearError = false,
    bool clearWorker = false,
  }) {
    return AuthState(
      isLoading: isLoading ?? this.isLoading,
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
      currentWorker: clearWorker ? null : (currentWorker ?? this.currentWorker),
    );
  }

  /// 관리자 여부 확인
  bool get isAdmin => currentWorker?.isAdmin ?? false;

  /// 매니저 여부 확인
  bool get isManager => currentWorker?.isManager ?? false;

  /// 승인된 사용자 여부 확인
  bool get isApproved => currentWorker?.isApproved ?? false;

  /// 이메일 인증 여부 확인
  bool get isEmailVerified => currentWorker?.emailVerified ?? false;

  /// 현재 사용자 ID
  int? get currentWorkerId => currentWorker?.id;

  /// 현재 사용자 역할
  String? get currentRole => currentWorker?.role;

  @override
  String toString() {
    return 'AuthState(isLoading: $isLoading, isAuthenticated: $isAuthenticated, '
        'worker: ${currentWorker?.name}, error: $errorMessage)';
  }
}

/// 인증 상태 관리 Notifier
///
/// 로그인, 회원가입, 로그아웃, 이메일 인증 등의 인증 관련 비즈니스 로직 처리
class AuthNotifier extends StateNotifier<AuthState> {
  final AuthService _authService;

  AuthNotifier(this._authService) : super(const AuthState());

  /// AuthService 접근자 (route 저장 등 외부에서 사용)
  AuthService get authService => _authService;

  /// 앱 시작 시 자동 로그인 시도
  ///
  /// refresh_token으로 새 access_token 발급 → 성공 시 인증 상태 복원
  /// main.dart의 initState에서 호출
  Future<bool> tryAutoLogin() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final success = await _authService.tryAutoLogin();
      if (success) {
        final workerData = await _authService.getWorkerData();
        if (workerData != null) {
          state = state.copyWith(
            isLoading: false,
            isAuthenticated: true,
            currentWorker: Worker.fromJson(workerData),
          );
          return true;
        }
      }
      state = state.copyWith(isLoading: false);
      return false;
    } catch (e) {
      state = state.copyWith(isLoading: false);
      return false;
    }
  }

  /// 저장된 토큰으로 인증 상태 확인 (기존 access_token 기반)
  Future<void> checkAuthentication() async {
    try {
      final isLoggedIn = await _authService.isLoggedIn();
      if (isLoggedIn) {
        final workerData = await _authService.getWorkerData();
        if (workerData != null) {
          state = state.copyWith(
            isAuthenticated: true,
            currentWorker: Worker.fromJson(workerData),
          );
        }
      }
    } catch (e) {
      await logout();
    }
  }

  /// 로그인
  ///
  /// [email]: 사용자 이메일
  /// [password]: 비밀번호
  ///
  /// Returns: 로그인 성공 여부
  Future<bool> login(String email, String password) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final response = await _authService.login(email, password);
      // API 응답: {"access_token": "...", "worker": {...}}
      final workerData = response['worker'] as Map<String, dynamic>? ?? response;
      final worker = Worker.fromJson(workerData);

      state = state.copyWith(
        isLoading: false,
        isAuthenticated: true,
        currentWorker: worker,
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

  /// 회원가입
  ///
  /// [name]: 사용자 이름
  /// [email]: 이메일
  /// [password]: 비밀번호
  /// [role]: 역할 (MECH, ELEC, TM, PI, QI, SI)
  /// [company]: 협력사 (FNI, BAT, TMS(M), TMS(E), P&S, C&A, GST)
  ///
  /// Returns: 회원가입 성공 여부 (이메일 인증 필요)
  Future<bool> register({
    required String name,
    required String email,
    required String password,
    required String role,
    required String company,
  }) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      await _authService.register(
        name: name,
        email: email,
        password: password,
        role: role,
        company: company,
      );

      state = state.copyWith(isLoading: false);
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.toString(),
      );
      return false;
    }
  }

  /// 이메일 인증
  ///
  /// [email]: 사용자 이메일
  /// [code]: 6자리 인증 코드
  ///
  /// Returns: 인증 성공 여부
  Future<bool> verifyEmail({
    required String email,
    required String code,
  }) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      await _authService.verifyEmail(
        email: email,
        code: code,
      );

      state = state.copyWith(isLoading: false);
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.toString(),
      );
      return false;
    }
  }

  /// 로그아웃
  ///
  /// 서비스 로그아웃 실패 시에도 반드시 인증 상태를 초기화
  /// (토큰 삭제 실패는 무시 — 다음 자동 로그인에서 만료 처리됨)
  Future<void> logout() async {
    try {
      await _authService.logout();
    } catch (e) {
      // 토큰 삭제 실패해도 상태는 리셋
      debugPrint('[AuthNotifier] logout service error: $e');
    } finally {
      state = const AuthState(); // 항상 초기 상태로 리셋
    }
  }

  /// 에러 메시지 클리어
  void clearError() {
    state = state.copyWith(clearError: true);
  }

  /// 현재 사용자 정보 새로고침
  Future<void> refreshCurrentWorker() async {
    try {
      final workerData = await _authService.getWorkerData();
      if (workerData != null) {
        state = state.copyWith(
          currentWorker: Worker.fromJson(workerData),
        );
      }
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
    }
  }

  /// 서버에서 최신 사용자 정보 가져와 갱신
  Future<void> refreshFromServer() async {
    try {
      final workerData = await _authService.getMe();
      state = state.copyWith(
        currentWorker: Worker.fromJson(workerData),
      );
    } catch (e) {
      debugPrint('[AuthNotifier] refreshFromServer error: $e');
    }
  }

  /// GST 작업자 활성 역할 변경
  ///
  /// [role]: PI, QI, SI
  Future<bool> changeActiveRole(String role) async {
    try {
      final response = await _authService.changeActiveRole(role);
      final workerData = response['worker'] as Map<String, dynamic>?;
      if (workerData != null) {
        state = state.copyWith(
          currentWorker: Worker.fromJson(workerData),
        );
      } else {
        // worker 데이터가 없으면 현재 worker에 activeRole만 업데이트
        final current = state.currentWorker;
        if (current != null) {
          state = state.copyWith(
            currentWorker: current.copyWith(activeRole: role),
          );
        }
      }
      return true;
    } catch (e) {
      debugPrint('[AuthNotifier] changeActiveRole error: $e');
      return false;
    }
  }
}

/// 공유 ApiService Provider (싱글턴)
/// AuthService, TaskService 등 모든 서비스에서 동일한 인스턴스 사용
final apiServiceProvider = Provider<ApiService>((ref) {
  return ApiService();
});

/// AuthService Provider
final authServiceProvider = Provider<AuthService>((ref) {
  final apiService = ref.watch(apiServiceProvider);
  return AuthService(apiService: apiService);
});

/// AuthNotifier Provider
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  final authService = ref.watch(authServiceProvider);
  final notifier = AuthNotifier(authService);

  // refresh 실패 시 자동 로그아웃 콜백 주입
  authService.onRefreshFailed = () {
    notifier.logout();
  };

  return notifier;
});
