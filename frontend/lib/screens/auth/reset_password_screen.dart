import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../utils/constants.dart';
import '../../utils/design_system.dart';
import 'login_screen.dart';

/// 비밀번호 재설정 화면
///
/// 6자리 인증 코드 + 새 비밀번호 + 확인 입력 → POST /api/auth/reset-password
class ResetPasswordScreen extends ConsumerStatefulWidget {
  final String email;

  const ResetPasswordScreen({
    super.key,
    required this.email,
  });

  @override
  ConsumerState<ResetPasswordScreen> createState() => _ResetPasswordScreenState();
}

class _ResetPasswordScreenState extends ConsumerState<ResetPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _codeController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmController = TextEditingController();
  bool _isLoading = false;
  bool _obscurePassword = true;
  bool _obscureConfirm = true;
  String? _errorMessage;

  @override
  void dispose() {
    _codeController.dispose();
    _passwordController.dispose();
    _confirmController.dispose();
    super.dispose();
  }

  String? _validateCode(String? value) {
    if (value == null || value.isEmpty) {
      return '인증 코드를 입력해주세요.';
    }
    if (value.length != 6) {
      return '6자리 코드를 입력해주세요.';
    }
    if (!RegExp(r'^[0-9]+$').hasMatch(value)) {
      return '숫자만 입력 가능합니다.';
    }
    return null;
  }

  String? _validatePassword(String? value) {
    if (value == null || value.isEmpty) {
      return '새 비밀번호를 입력해주세요.';
    }
    if (value.length < 8) {
      return '비밀번호는 8자 이상이어야 합니다.';
    }
    return null;
  }

  String? _validateConfirm(String? value) {
    if (value == null || value.isEmpty) {
      return '비밀번호 확인을 입력해주세요.';
    }
    if (value != _passwordController.text) {
      return '비밀번호가 일치하지 않습니다.';
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
        authResetPasswordEndpoint,
        data: {
          'email': widget.email,
          'code': _codeController.text.trim(),
          'new_password': _passwordController.text,
        },
      );

      if (!mounted) return;

      // 성공 → 스낵바 표시 후 로그인 화면으로 이동
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('비밀번호가 재설정되었습니다. 다시 로그인해주세요.'),
          backgroundColor: GxColors.success,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(GxRadius.sm),
          ),
        ),
      );

      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const LoginScreen()),
        (route) => false,
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
              '비밀번호 재설정',
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
              const SizedBox(height: 16),

              // 이메일 안내
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                decoration: BoxDecoration(
                  color: GxColors.accentSoft,
                  borderRadius: BorderRadius.circular(GxRadius.md),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.email_outlined, size: 16, color: GxColors.accent),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        widget.email,
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: GxColors.accent,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                '위 이메일로 발송된 인증 코드와\n새 비밀번호를 입력해주세요.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 13, color: GxColors.slate),
              ),
              const SizedBox(height: 20),

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
                            child: const Icon(Icons.password_outlined, size: 14, color: GxColors.accent),
                          ),
                          const SizedBox(width: 8),
                          const Text(
                            '비밀번호 재설정',
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              color: GxColors.charcoal,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),

                      // 인증 코드 필드
                      _buildLabel('인증 코드'),
                      const SizedBox(height: 5),
                      TextFormField(
                        controller: _codeController,
                        decoration: _inputDecoration('6자리 숫자'),
                        keyboardType: TextInputType.number,
                        textInputAction: TextInputAction.next,
                        style: const TextStyle(
                          fontSize: 20,
                          letterSpacing: 4,
                          fontWeight: FontWeight.w600,
                          color: GxColors.charcoal,
                        ),
                        textAlign: TextAlign.center,
                        maxLength: 6,
                        inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                        validator: _validateCode,
                        enabled: !_isLoading,
                        buildCounter: (context, {required currentLength, required isFocused, maxLength}) => null,
                      ),
                      const SizedBox(height: 12),

                      // 새 비밀번호 필드
                      _buildLabel('새 비밀번호'),
                      const SizedBox(height: 5),
                      TextFormField(
                        controller: _passwordController,
                        decoration: _inputDecoration('8자 이상').copyWith(
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
                        textInputAction: TextInputAction.next,
                        style: const TextStyle(fontSize: 13, color: GxColors.charcoal),
                        validator: _validatePassword,
                        enabled: !_isLoading,
                      ),
                      const SizedBox(height: 12),

                      // 비밀번호 확인 필드
                      _buildLabel('비밀번호 확인'),
                      const SizedBox(height: 5),
                      TextFormField(
                        controller: _confirmController,
                        decoration: _inputDecoration('비밀번호를 다시 입력하세요').copyWith(
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscureConfirm ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                              size: 18,
                              color: GxColors.steel,
                            ),
                            onPressed: () => setState(() => _obscureConfirm = !_obscureConfirm),
                          ),
                        ),
                        obscureText: _obscureConfirm,
                        textInputAction: TextInputAction.done,
                        style: const TextStyle(fontSize: 13, color: GxColors.charcoal),
                        validator: _validateConfirm,
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
                                          '비밀번호 재설정',
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
