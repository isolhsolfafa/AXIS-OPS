import 'dart:ui';
import 'package:flutter/material.dart';
import '../../services/api_service.dart';
import '../../utils/app_version.dart';
import '../../utils/design_system.dart';
import 'login_screen.dart';
import 'register_screen.dart';

/// 스플래시/랜딩 화면
///
/// 화이트 글래스모피즘 테마 — 그라디언트 배경 + 글래스 카드
/// 로고 플로팅 애니메이션, 기능 심볼, Login/Register 버튼
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _animController;
  late Animation<double> _floatAnimation;
  bool _isSystemOnline = false;
  bool _healthChecked = false;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      duration: const Duration(seconds: 3),
      vsync: this,
    )..repeat(reverse: true);

    _floatAnimation = Tween<double>(begin: 0, end: -10).animate(
      CurvedAnimation(parent: _animController, curve: Curves.easeInOut),
    );

    _checkSystemHealth();
  }

  Future<void> _checkSystemHealth() async {
    try {
      final apiService = ApiService();
      final response = await apiService.getPublic('/health');
      if (mounted) {
        setState(() {
          _isSystemOnline = response != null && response['status'] == 'ok';
          _healthChecked = true;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isSystemOnline = false;
          _healthChecked = true;
        });
      }
    }
  }

  @override
  void dispose() {
    _animController.dispose();
    super.dispose();
  }

  void _navigateToLogin(BuildContext context) {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (context) => const LoginScreen()),
    );
  }

  void _navigateToRegister(BuildContext context) {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (context) => const RegisterScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: GxGradients.background),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const SizedBox(height: 12),

                  // 로고 (플로팅 애니메이션)
                  AnimatedBuilder(
                    animation: _floatAnimation,
                    builder: (context, child) {
                      return Transform.translate(
                        offset: Offset(0, _floatAnimation.value),
                        child: child,
                      );
                    },
                    child: SizedBox(
                      width: 180,
                      child: Image.asset(
                        'assets/images/g-axis-2.png',
                        fit: BoxFit.contain,
                        errorBuilder: (context, error, stackTrace) {
                          return const Text(
                            'G-AXIS',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 32,
                              fontWeight: FontWeight.w300,
                              letterSpacing: 8,
                              color: Colors.white,
                            ),
                          );
                        },
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),

                  // MANUFACTURING OPERATIONS 서브타이틀
                  Text(
                    'MANUFACTURING OPERATIONS',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                      color: Colors.white.withValues(alpha: 0.65),
                      letterSpacing: 3,
                    ),
                  ),
                  const SizedBox(height: 28),

                  // 글래스 카드
                  Container(
                    width: double.infinity,
                    constraints: const BoxConstraints(maxWidth: 400),
                    decoration: GxGlass.card(),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(24),
                      child: BackdropFilter(
                        filter: ImageFilter.blur(sigmaX: 24, sigmaY: 24),
                        child: Padding(
                          padding: const EdgeInsets.fromLTRB(28, 36, 28, 32),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              // 카드 타이틀
                              const Text(
                                'Welcome',
                                style: TextStyle(
                                  fontSize: 22,
                                  fontWeight: FontWeight.w600,
                                  color: GxColors.charcoal,
                                ),
                              ),
                              const SizedBox(height: 4),
                              const Text(
                                'G-AXIS OPS에 오신 것을 환영합니다',
                                style: TextStyle(
                                  fontSize: 13,
                                  color: GxColors.steel,
                                ),
                              ),
                              const SizedBox(height: 32),

                              // Login 버튼 (그라디언트)
                              _buildGradientButton(
                                label: '로그인',
                                onPressed: () => _navigateToLogin(context),
                              ),
                              const SizedBox(height: 10),

                              // Register 버튼 (글래스 아웃라인)
                              _buildOutlineButton(
                                label: '회원가입',
                                onPressed: () => _navigateToRegister(context),
                              ),
                              const SizedBox(height: 28),

                              // 기능 심볼 3개
                              Container(
                                padding: const EdgeInsets.only(top: 22),
                                decoration: const BoxDecoration(
                                  border: Border(
                                    top: BorderSide(
                                      color: GxColors.mist,
                                      width: 1,
                                    ),
                                  ),
                                ),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                                  children: [
                                    _buildFeatureIcon(
                                      icon: Icons.qr_code_scanner_rounded,
                                      label: 'QR Scan',
                                      bgColor: GxColors.accentSoft,
                                      iconColor: GxColors.accent,
                                    ),
                                    _buildFeatureIcon(
                                      icon: Icons.assignment_outlined,
                                      label: 'Task Mgmt',
                                      bgColor: GxColors.successBg,
                                      iconColor: GxColors.success,
                                    ),
                                    _buildFeatureIcon(
                                      icon: Icons.schedule_rounded,
                                      label: 'Real-time',
                                      bgColor: GxColors.infoBg,
                                      iconColor: GxColors.info,
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 28),

                  // System Online 인디케이터 (실시간 /health 체크)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.35),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: GxGlass.borderColor, width: 1),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 6,
                          height: 6,
                          decoration: BoxDecoration(
                            color: !_healthChecked
                                ? GxColors.silver
                                : _isSystemOnline
                                    ? GxColors.success
                                    : GxColors.danger,
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: (!_healthChecked
                                        ? GxColors.silver
                                        : _isSystemOnline
                                            ? GxColors.success
                                            : GxColors.danger)
                                    .withValues(alpha: 0.4),
                                blurRadius: 4,
                                spreadRadius: 1,
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          !_healthChecked
                              ? 'Connecting...'
                              : _isSystemOnline
                                  ? 'System Online'
                                  : 'System Offline',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                            color: Colors.white.withValues(alpha: 0.6),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),

                  // 버전 정보 (중앙 관리)
                  Text(
                    AppVersion.display,
                    style: TextStyle(
                      fontSize: 11,
                      color: Colors.white.withValues(alpha: 0.35),
                      fontFamily: 'monospace',
                      letterSpacing: 1,
                    ),
                  ),
                  const SizedBox(height: 16),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  /// 그라디언트 로그인 버튼
  Widget _buildGradientButton({
    required String label,
    required VoidCallback onPressed,
  }) {
    return Container(
      height: 50,
      decoration: BoxDecoration(
        gradient: GxGradients.accentButton,
        borderRadius: BorderRadius.circular(GxRadius.lg),
        boxShadow: [
          BoxShadow(
            color: GxColors.accent.withValues(alpha: 0.35),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onPressed,
          borderRadius: BorderRadius.circular(GxRadius.lg),
          child: Center(
            child: Text(
              label,
              style: const TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w600,
                color: Colors.white,
                letterSpacing: 0.5,
              ),
            ),
          ),
        ),
      ),
    );
  }

  /// 글래스 아웃라인 버튼
  Widget _buildOutlineButton({
    required String label,
    required VoidCallback onPressed,
  }) {
    return Container(
      height: 50,
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(GxRadius.lg),
        border: Border.all(color: GxColors.mist, width: 1.5),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onPressed,
          borderRadius: BorderRadius.circular(GxRadius.lg),
          child: Center(
            child: Text(
              label,
              style: const TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w500,
                color: GxColors.slate,
                letterSpacing: 0.5,
              ),
            ),
          ),
        ),
      ),
    );
  }

  /// 기능 아이콘 심볼
  Widget _buildFeatureIcon({
    required IconData icon,
    required String label,
    required Color bgColor,
    required Color iconColor,
  }) {
    return Column(
      children: [
        Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: bgColor,
            borderRadius: BorderRadius.circular(GxRadius.md),
          ),
          child: Icon(icon, size: 20, color: iconColor),
        ),
        const SizedBox(height: 6),
        Text(
          label,
          style: const TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w600,
            color: GxColors.steel,
            letterSpacing: 0.3,
          ),
        ),
      ],
    );
  }
}
