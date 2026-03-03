import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../utils/validators.dart';
import '../../utils/design_system.dart';
import 'approval_pending_screen.dart';
import 'forgot_password_screen.dart';

/// 로그인 화면
///
/// G-AXIS Design System 적용: cloud 배경, 인디고 액센트, 카드 스타일 폼
class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    if (!_formKey.currentState!.validate()) return;
    FocusScope.of(context).unfocus();

    final authNotifier = ref.read(authProvider.notifier);
    final success = await authNotifier.login(
      _emailController.text.trim(),
      _passwordController.text,
    );

    if (!mounted) return;

    if (success) {
      // 로그인 성공 시 AuthGate가 자동으로 홈 화면으로 전환
      Navigator.of(context).popUntil((route) => route.isFirst);
    } else {
      // 에러 코드 분기: 승인 대기/거부 시 전용 화면으로 이동
      final errorMsg = ref.read(authProvider).errorMessage ?? '';
      if (errorMsg.contains('APPROVAL_PENDING')) {
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const ApprovalPendingScreen()),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);

    return Scaffold(
      backgroundColor: GxColors.cloud,
      appBar: AppBar(
        backgroundColor: GxColors.white,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, size: 18, color: GxColors.accent),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 4,
              height: 20,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [GxColors.accent, GxColors.accentHover],
                ),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(width: 12),
            const Text(
              'Login',
              style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w600,
                color: GxColors.charcoal,
              ),
            ),
          ],
        ),
        centerTitle: false,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: GxColors.mist),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              // 로그인 카드
              Container(
                padding: const EdgeInsets.all(16),
                decoration: GxGlass.cardSm(radius: GxRadius.lg),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // 카드 헤더
                      Row(
                        children: [
                          Container(
                            width: 28,
                            height: 28,
                            decoration: BoxDecoration(
                              color: GxColors.accentSoft,
                              borderRadius: BorderRadius.circular(GxRadius.md),
                            ),
                            child: const Icon(Icons.lock_outline, size: 14, color: GxColors.accent),
                          ),
                          const SizedBox(width: 8),
                          const Text(
                            'Worker Login',
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              color: GxColors.charcoal,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),

                      // 이메일/계정명 필드
                      _buildLabel('EMAIL / ID'),
                      const SizedBox(height: 5),
                      TextFormField(
                        controller: _emailController,
                        decoration: _inputDecoration('이메일 또는 계정명'),
                        keyboardType: TextInputType.text,
                        textInputAction: TextInputAction.next,
                        style: const TextStyle(fontSize: 13, color: GxColors.charcoal),
                        validator: validateLoginId,
                        enabled: !authState.isLoading,
                      ),
                      const SizedBox(height: 4),
                      const Text(
                        'Admin은 이메일 앞부분만 입력 가능',
                        style: TextStyle(
                          fontSize: 11,
                          color: GxColors.steel,
                        ),
                      ),
                      const SizedBox(height: 12),

                      // 비밀번호 필드
                      _buildLabel('PASSWORD'),
                      const SizedBox(height: 5),
                      TextFormField(
                        controller: _passwordController,
                        decoration: _inputDecoration('비밀번호를 입력하세요').copyWith(
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscurePassword ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                              size: 18,
                              color: GxColors.steel,
                            ),
                            onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                          ),
                        ),
                        obscureText: _obscurePassword,
                        textInputAction: TextInputAction.done,
                        style: const TextStyle(fontSize: 13, color: GxColors.charcoal),
                        validator: validatePassword,
                        enabled: !authState.isLoading,
                        onFieldSubmitted: (_) => _handleLogin(),
                      ),
                      const SizedBox(height: 16),

                      // 에러 메시지
                      if (authState.errorMessage != null) ...[
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                          decoration: BoxDecoration(
                            color: GxColors.dangerBg,
                            borderRadius: BorderRadius.circular(GxRadius.md),
                            border: Border.all(color: GxColors.danger.withValues(alpha: 0.2)),
                          ),
                          child: Row(
                            children: [
                              Container(
                                width: 6,
                                height: 6,
                                decoration: const BoxDecoration(
                                  color: GxColors.danger,
                                  shape: BoxShape.circle,
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  authState.errorMessage!,
                                  style: const TextStyle(
                                    color: Color(0xFFB91C1C),
                                    fontSize: 13,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 12),
                      ],

                      // 비밀번호 찾기 링크
                      Align(
                        alignment: Alignment.centerRight,
                        child: TextButton(
                          onPressed: authState.isLoading
                              ? null
                              : () {
                                  Navigator.of(context).push(
                                    MaterialPageRoute(
                                      builder: (_) => const ForgotPasswordScreen(),
                                    ),
                                  );
                                },
                          style: TextButton.styleFrom(
                            padding: EdgeInsets.zero,
                            minimumSize: Size.zero,
                            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                            foregroundColor: GxColors.accent,
                          ),
                          child: const Text(
                            '비밀번호를 잊으셨나요?',
                            style: TextStyle(
                              fontSize: 12,
                              color: GxColors.accent,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),

                      // 로그인 버튼
                      SizedBox(
                        height: 44,
                        child: Opacity(
                          opacity: authState.isLoading ? 0.6 : 1.0,
                          child: Container(
                            decoration: BoxDecoration(
                              gradient: GxGradients.accentButton,
                              borderRadius: BorderRadius.circular(GxRadius.sm),
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
                                onTap: authState.isLoading ? null : _handleLogin,
                                borderRadius: BorderRadius.circular(GxRadius.sm),
                                child: Center(
                                  child: authState.isLoading
                                      ? const SizedBox(
                                          height: 20,
                                          width: 20,
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2,
                                            valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                                          ),
                                        )
                                      : const Text(
                                          'Login',
                                          style: TextStyle(
                                            fontSize: 13,
                                            fontWeight: FontWeight.w600,
                                            color: Colors.white,
                                          ),
                                        ),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildLabel(String text) {
    return Text(
      text,
      style: const TextStyle(
        fontSize: 11,
        fontWeight: FontWeight.w600,
        color: GxColors.steel,
        letterSpacing: 0.5,
      ),
    );
  }

  InputDecoration _inputDecoration(String hint) {
    return InputDecoration(
      hintText: hint,
      hintStyle: TextStyle(fontSize: 13, color: GxColors.silver),
      filled: true,
      fillColor: GxColors.white,
      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(GxRadius.sm),
        borderSide: const BorderSide(color: GxColors.mist, width: 1.5),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(GxRadius.sm),
        borderSide: const BorderSide(color: GxColors.mist, width: 1.5),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(GxRadius.sm),
        borderSide: const BorderSide(color: GxColors.accent, width: 1.5),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(GxRadius.sm),
        borderSide: const BorderSide(color: GxColors.danger, width: 1.5),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(GxRadius.sm),
        borderSide: const BorderSide(color: GxColors.danger, width: 1.5),
      ),
    );
  }
}
