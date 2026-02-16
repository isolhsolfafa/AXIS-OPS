import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/worker.dart';
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

  AuthNotifier(this._authService) : super(const AuthState()) {
    // 앱 시작 시 저장된 토큰 확인
    _checkAuthentication();
  }

  /// 저장된 토큰으로 인증 상태 확인
  Future<void> _checkAuthentication() async {
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
      // 토큰이 유효하지 않으면 로그아웃
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
      final worker = Worker.fromJson(response);

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
  /// [role]: 역할 (MM, EE, TM, PI, QI, SI)
  ///
  /// Returns: 회원가입 성공 여부 (이메일 인증 필요)
  Future<bool> register({
    required String name,
    required String email,
    required String password,
    required String role,
  }) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      await _authService.register(
        name: name,
        email: email,
        password: password,
        role: role,
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
  Future<void> logout() async {
    try {
      await _authService.logout();
      state = const AuthState(); // 초기 상태로 리셋
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
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
}

/// AuthService Provider
final authServiceProvider = Provider<AuthService>((ref) {
  return AuthService();
});

/// AuthNotifier Provider
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  final authService = ref.watch(authServiceProvider);
  return AuthNotifier(authService);
});
