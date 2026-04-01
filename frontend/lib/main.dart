import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'providers/auth_provider.dart';
import 'screens/auth/splash_screen.dart';
import 'screens/auth/approval_pending_screen.dart';
import 'screens/auth/forgot_password_screen.dart';
import 'screens/auth/reset_password_screen.dart';
import 'screens/auth/pin_login_screen.dart';
import 'screens/home/home_screen.dart';
import 'screens/admin/alert_list_screen.dart';
import 'screens/admin/admin_options_screen.dart';
import 'screens/qr/qr_scan_screen.dart';
import 'screens/task/task_management_screen.dart';
import 'screens/manager/manager_pending_tasks_screen.dart';
import 'screens/gst/gst_products_screen.dart';
import 'screens/checklist/checklist_screen.dart';
import 'screens/checklist/tm_checklist_screen.dart';
import 'screens/settings/profile_screen.dart';
import 'screens/settings/pin_settings_screen.dart';
import 'screens/progress/sn_progress_screen.dart';
import 'screens/notice/notice_list_screen.dart';
import 'screens/admin/notice_write_screen.dart';
import 'screens/admin/manager_delegation_screen.dart';
import 'utils/design_system.dart';

void main() {
  runApp(
    const ProviderScope(
      child: GAxisApp(),
    ),
  );
}

/// 저장 대상 경로 목록
const _saveableRoutes = {
  '/home',
  '/qr-scan',
  '/task-management',
  '/admin-options',
  '/alerts',
  '/gst-products',
  '/sn-progress',
  '/notices',
};

/// G-AXIS 앱 메인 클래스
///
/// G-AXIS Design System 적용
/// 인증 상태에 따라 적절한 화면으로 자동 라우팅
class GAxisApp extends ConsumerWidget {
  const GAxisApp({super.key});

  /// Global Navigator Key — 로그아웃 시 전체 스택 클리어용
  static final navigatorKey = GlobalKey<NavigatorState>();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // auth 상태 변경 감지: 로그아웃 시 초기 화면으로 강제 이동
    ref.listen<AuthState>(authProvider, (previous, next) {
      if (previous != null &&
          previous.isAuthenticated &&
          !next.isAuthenticated) {
        // 인증 → 비인증 전환 = 로그아웃 발생
        // Navigator 스택 전체 클리어 → AppStartup으로 교체
        navigatorKey.currentState?.pushAndRemoveUntil(
          MaterialPageRoute(
            builder: (_) => const AppStartup(),
          ),
          (route) => false,
        );
      }
    });

    return MaterialApp(
      title: 'G-AXIS',
      debugShowCheckedModeBanner: false,
      navigatorKey: navigatorKey,
      navigatorObservers: [
        _RouteTracker(ref),
      ],
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: GxColors.accent,
          surface: GxColors.cloud,
        ),
        useMaterial3: true,
        scaffoldBackgroundColor: GxColors.cloud,
        appBarTheme: const AppBarTheme(
          centerTitle: false,
          elevation: 0,
          backgroundColor: GxColors.white,
          foregroundColor: GxColors.charcoal,
          surfaceTintColor: Colors.transparent,
        ),
        cardTheme: CardThemeData(
          elevation: 0,
          color: GxColors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(GxRadius.lg),
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(GxRadius.sm),
            borderSide: const BorderSide(color: GxColors.mist, width: 1.5),
          ),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 12,
            vertical: 10,
          ),
          filled: true,
          fillColor: GxColors.white,
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: GxColors.accent,
            foregroundColor: Colors.white,
            elevation: 0,
            padding: const EdgeInsets.symmetric(vertical: 12),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(GxRadius.sm),
            ),
          ),
        ),
        textButtonTheme: TextButtonThemeData(
          style: TextButton.styleFrom(
            foregroundColor: GxColors.accent,
          ),
        ),
      ),
      home: const AppStartup(),
      routes: {
        '/alerts': (context) => const AlertListScreen(),
        '/qr-scan': (context) => const QrScanScreen(),
        '/task-management': (context) => const TaskManagementScreen(),
        '/admin-options': (context) => const AdminOptionsScreen(),
        '/manager-pending-tasks': (context) => const ManagerPendingTasksScreen(),
        '/home': (context) => const HomeScreen(),
        '/sn-progress': (context) => const SnProgressScreen(),
        '/forgot-password': (context) => const ForgotPasswordScreen(),
        '/profile': (context) => const ProfileScreen(),
        '/pin-settings': (context) => const PinSettingsScreen(),
        '/pin-login': (context) => const PinLoginScreen(),
        '/notices': (context) => const NoticeListScreen(),
        '/notice-write': (context) => const NoticeWriteScreen(),
        '/manager-delegation': (context) => const ManagerDelegationScreen(),
        '/reset-password': (context) {
          final args = ModalRoute.of(context)?.settings.arguments;
          final email = args is Map<String, dynamic>
              ? (args['email'] as String? ?? '')
              : '';
          return ResetPasswordScreen(email: email);
        },
        '/gst-products': (context) {
          final args = ModalRoute.of(context)?.settings.arguments;
          final category = args is Map<String, dynamic>
              ? (args['category'] as String? ?? 'PI')
              : 'PI';
          return GstProductsScreen(category: category);
        },
        '/checklist': (context) {
          final args = ModalRoute.of(context)?.settings.arguments;
          final serialNumber = args is Map<String, dynamic>
              ? (args['serial_number'] as String? ?? '')
              : '';
          final category = args is Map<String, dynamic>
              ? (args['category'] as String? ?? 'HOOKUP')
              : 'HOOKUP';
          return ChecklistScreen(
            serialNumber: serialNumber,
            category: category,
          );
        },
        '/tm-checklist': (context) {
          final args = ModalRoute.of(context)?.settings.arguments;
          final serialNumber = args is Map<String, dynamic>
              ? (args['serial_number'] as String? ?? '')
              : '';
          return TmChecklistScreen(serialNumber: serialNumber);
        },
      },
    );
  }
}

/// NavigatorObserver — 화면 전환 시 저장 대상 경로를 자동으로 SharedPreferences에 저장
class _RouteTracker extends NavigatorObserver {
  final WidgetRef ref;

  _RouteTracker(this.ref);

  void _saveRoute(Route<dynamic>? route) {
    if (route == null) return;
    final name = route.settings.name;
    if (name == null || !_saveableRoutes.contains(name)) return;

    final args = route.settings.arguments;
    Map<String, dynamic>? argsMap;
    if (args is Map<String, dynamic>) {
      argsMap = args;
    }

    // Future.microtask로 지연 — 빌드 중 provider 접근 충돌 방지
    Future.microtask(() {
      ref.read(authProvider.notifier).authService.saveLastRoute(name, argsMap);
    });
  }

  @override
  void didPush(Route<dynamic> route, Route<dynamic>? previousRoute) {
    _saveRoute(route);
  }

  @override
  void didReplace({Route<dynamic>? newRoute, Route<dynamic>? oldRoute}) {
    _saveRoute(newRoute);
  }
}

/// 앱 시작 진입점
///
/// 앱 시작 시 자동 로그인 시도 → 성공 시 마지막 경로 복원 또는 홈
/// 실패 시 SplashScreen으로 이동
class AppStartup extends ConsumerStatefulWidget {
  const AppStartup({super.key});

  @override
  ConsumerState<AppStartup> createState() => _AppStartupState();
}

class _AppStartupState extends ConsumerState<AppStartup> {
  bool _isInitializing = true;

  @override
  void initState() {
    super.initState();
    // addPostFrameCallback으로 지연 — initState 중 provider 수정 방지
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _initialize();
    });
  }

  Future<void> _initialize() async {
    try {
      final authNotifier = ref.read(authProvider.notifier);
      final authService = authNotifier.authService;

      // 1단계: refresh_token 존재 여부 확인
      final hasRefreshToken = await authService.hasRefreshToken();

      if (!mounted) return;

      if (!hasRefreshToken) {
        // refresh_token 없음 → 이메일/비밀번호 로그인 화면
        setState(() => _isInitializing = false);
        return;
      }

      // 2단계: PIN 등록 여부 확인 (로컬 캐시)
      final hasPinRegistered = await authService.hasPinRegistered();

      if (!mounted) return;

      if (hasPinRegistered) {
        // PIN 등록됨 → PIN 입력 화면으로 이동
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            settings: const RouteSettings(name: '/pin-login'),
            builder: (_) => const PinLoginScreen(),
          ),
        );
        return;
      }

      // 3단계: PIN 미등록 → refresh_token으로 자동 로그인 시도
      final success = await authNotifier.tryAutoLogin();

      if (!mounted) return;

      if (success) {
        // 자동 로그인 성공 → 마지막 경로 복원 시도
        final lastRoute = await authService.getLastRoute();

        if (!mounted) return;

        if (lastRoute != null && lastRoute['route'] != null) {
          final routeName = lastRoute['route'] as String;
          final args = lastRoute['args'] as Map<String, dynamic>?;

          if (routeName == '/home') {
            // 홈이면 단순 교체
            Navigator.of(context).pushReplacementNamed('/home');
          } else {
            // 홈이 아닌 화면 복원 → 홈을 먼저 스택에 깔고 위에 push
            // 이래야 뒤로가기(pop) 시 홈으로 돌아감
            Navigator.of(context).pushReplacement(
              MaterialPageRoute(
                settings: const RouteSettings(name: '/home'),
                builder: (_) => const HomeScreen(),
              ),
            );
            Navigator.of(context).pushNamed(routeName, arguments: args);
          }
          return;
        } else {
          Navigator.of(context).pushReplacement(
            MaterialPageRoute(
              settings: const RouteSettings(name: '/home'),
              builder: (_) => const HomeScreen(),
            ),
          );
          return;
        }
      }
    } catch (e) {
      debugPrint('[AppStartup] Auto login failed: $e');
    }

    // 자동 로그인 실패 또는 에러 → 스플래시 화면
    if (mounted) {
      setState(() => _isInitializing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isInitializing) {
      return const Scaffold(
        backgroundColor: GxColors.cloud,
        body: Center(
          child: CircularProgressIndicator(color: GxColors.accent),
        ),
      );
    }

    return const AuthGate();
  }
}

/// 인증 게이트
///
/// AuthProvider 상태에 따라 적절한 화면으로 라우팅
class AuthGate extends ConsumerWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);

    // 로딩 중 (초기 인증 확인 중)
    if (authState.isLoading) {
      return const Scaffold(
        backgroundColor: GxColors.cloud,
        body: Center(
          child: CircularProgressIndicator(color: GxColors.accent),
        ),
      );
    }

    // 인증되지 않음 → 스플래시 화면
    if (!authState.isAuthenticated) {
      return const SplashScreen();
    }

    // 인증됨 - 추가 검증
    final worker = authState.currentWorker;

    if (worker == null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(authProvider.notifier).logout();
      });
      return const SplashScreen();
    }

    // 이메일 인증 안됨 → 승인 대기 화면
    if (!worker.emailVerified) {
      return const ApprovalPendingScreen();
    }

    // 관리자 승인 대기 중 → 승인 대기 화면
    if (!worker.isApproved) {
      return const ApprovalPendingScreen();
    }

    // 모든 검증 통과 → 홈 화면
    return const HomeScreen();
  }
}
