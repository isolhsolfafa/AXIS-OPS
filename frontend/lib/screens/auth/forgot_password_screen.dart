import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../utils/constants.dart';
import '../../utils/design_system.dart';
import 'reset_password_screen.dart';

/// 비밀번호 찾기 화면
///
/// 이메일 입력 → POST /api/auth/forgot-password → 비밀번호 재설정 화면으로 이동
class ForgotPasswordScreen extends ConsumerStatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  ConsumerState<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends ConsumerState<ForgotPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }

  String? _validateEmail(String? value) {
    if (value == null || value.trim().isEmpty) {
      return '이메일을 입력해주세요.';
    }
    final emailRegex = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');
    if (!emailRegex.hasMatch(value.trim())) {
      return '올바른 이메일 형식이 아닙니다.';
    }
    return null;
  }

  Future<void> _handleSubmit() async {
    if (!_formKey.currentState!.validate()) return;
    FocusScope.of(context).unfocus();

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final apiService = ref.read(apiServiceProvider);
      await apiService.post(
        authForgotPasswordEndpoint,
        data: {'email': _emailController.text.trim()},
      );

      if (!mounted) return;

      // 성공 → 비밀번호 재설정 화면으로 이동
      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => ResetPasswordScreen(
            email: _emailController.text.trim(),
          ),
        ),
      );
    } catch (e) {
      setState(() {
        _errorMessage = e.toString().replaceFirst('Exception: ', '');
      });
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
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
              '비밀번호 찾기',
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
              const SizedBox(height: 24),

              // 아이콘
              Container(
                width: 64,
                height: 64,
                decoration: BoxDecoration(
                  color: GxColors.accentSoft,
                  borderRadius: BorderRadius.circular(GxRadius.lg),
                ),
                child: const Icon(Icons.lock_reset_outlined, size: 32, color: GxColors.accent),
              ),
              const SizedBox(height: 20),

              // 안내 문구
              const Text(
                '비밀번호 찾기',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w600,
                  color: GxColors.charcoal,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                '가입한 이메일로 인증 코드를 발송합니다.\n코드를 입력하여 비밀번호를 재설정해주세요.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 13, color: GxColors.slate),
              ),
              const SizedBox(height: 24),

              // 입력 카드
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
                            child: const Icon(Icons.email_outlined, size: 14, color: GxColors.accent),
                          ),
                          const SizedBox(width: 8),
                          const Text(
                            '이메일 입력',
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              color: GxColors.charcoal,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),

                      // 이메일 필드
                      _buildLabel('EMAIL'),
                      const SizedBox(height: 5),
                      TextFormField(
                        controller: _emailController,
                        decoration: _inputDecoration('가입한 이메일을 입력하세요'),
                        keyboardType: TextInputType.emailAddress,
                        textInputAction: TextInputAction.done,
                        style: const TextStyle(fontSize: 13, color: GxColors.charcoal),
                        validator: _validateEmail,
                        enabled: !_isLoading,
                        onFieldSubmitted: (_) => _handleSubmit(),
                      ),
                      const SizedBox(height: 16),

                      // 에러 메시지
                      if (_errorMessage != null) ...[
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
                                  _errorMessage!,
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

                      // 제출 버튼
                      SizedBox(
                        height: 44,
                        child: Opacity(
                          opacity: _isLoading ? 0.6 : 1.0,
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
                                onTap: _isLoading ? null : _handleSubmit,
                                borderRadius: BorderRadius.circular(GxRadius.sm),
                                child: Center(
                                  child: _isLoading
                                      ? const SizedBox(
                                          height: 20,
                                          width: 20,
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2,
                                            valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                                          ),
                                        )
                                      : const Text(
                                          '인증 코드 발송',
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
