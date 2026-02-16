import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'providers/auth_provider.dart';
import 'screens/auth/login_screen.dart';
import 'screens/auth/approval_pending_screen.dart';
import 'screens/home/home_screen.dart';
import 'screens/admin/alert_list_screen.dart';
import 'screens/qr/qr_scan_screen.dart';
import 'screens/task/task_management_screen.dart';

void main() {
  runApp(
    const ProviderScope(
      child: GAxisApp(),
    ),
  );
}

/// G-AXIS 앱 메인 클래스
///
/// 인증 상태에 따라 적절한 화면으로 자동 라우팅
class GAxisApp extends ConsumerWidget {
  const GAxisApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp(
      title: 'G-AXIS',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
        appBarTheme: const AppBarTheme(
          centerTitle: true,
          elevation: 0,
        ),
        cardTheme: CardTheme(
          elevation: 2,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          border: const OutlineInputBorder(),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 16,
          ),
          filled: true,
          fillColor: Colors.grey.shade50,
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 16),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
          ),
        ),
      ),
      home: const AuthGate(),
      routes: {
        '/alerts': (context) => const AlertListScreen(),
        '/qr-scan': (context) => const QrScanScreen(),
        '/task-management': (context) => const TaskManagementScreen(),
      },
    );
  }
}

/// 인증 게이트
///
/// AuthProvider 상태에 따라 적절한 화면으로 라우팅
class AuthGate extends ConsumerWidget {
  const AuthGate({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);

    // 로딩 중 (초기 인증 확인 중)
    if (authState.isLoading) {
      return const Scaffold(
        body: Center(
          child: CircularProgressIndicator(),
        ),
      );
    }

    // 인증되지 않음 → 로그인 화면
    if (!authState.isAuthenticated) {
      return const LoginScreen();
    }

    // 인증됨 - 추가 검증
    final worker = authState.currentWorker;

    if (worker == null) {
      // Worker 정보 없음 (비정상 상태) → 로그아웃 처리
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(authProvider.notifier).logout();
      });
      return const LoginScreen();
    }

    // 이메일 인증 안됨 → 승인 대기 화면으로 이동
    // (이메일 인증은 회원가입 플로우에서 처리하므로, 여기서는 승인 상태만 확인)
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

