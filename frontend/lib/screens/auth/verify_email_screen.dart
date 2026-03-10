import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../utils/design_system.dart';
import 'login_screen.dart';

/// 이메일 인증 화면
///
/// 6자리 인증 코드를 입력받아 이메일 인증 처리
/// 10분 타이머 기능, 코드 재전송 기능 포함
class VerifyEmailScreen extends ConsumerStatefulWidget {
  final String email;

  const VerifyEmailScreen({
    Key? key,
    required this.email,
  }) : super(key: key);

  @override
  ConsumerState<VerifyEmailScreen> createState() =>
      _VerifyEmailScreenState();
}

class _VerifyEmailScreenState extends ConsumerState<VerifyEmailScreen> {
  final _formKey = GlobalKey<FormState>();
  final _codeController = TextEditingController();

  // 타이머 관련
  Timer? _timer;
  int _remainingSeconds = 180; // 3분 = 180초
  bool _canResend = false;
  bool _isResending = false;

  @override
  void initState() {
    super.initState();
    _startTimer();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _codeController.dispose();
    super.dispose();
  }

  void _startTimer() {
    _remainingSeconds = 180;
    _canResend = false;
    _timer?.cancel();

    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_remainingSeconds > 0) {
        setState(() {
          _remainingSeconds--;
        });
      } else {
        timer.cancel();
        setState(() {
          _canResend = true;
        });
      }
    });
  }

  String _formatTime(int seconds) {
    final minutes = seconds ~/ 60;
    final secs = seconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:${secs.toString().padLeft(2, '0')}';
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

  Future<void> _handleVerify() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    FocusScope.of(context).unfocus();

    final authNotifier = ref.read(authProvider.notifier);
    final success = await authNotifier.verifyEmail(
      email: widget.email,
      code: _codeController.text.trim(),
    );

    if (!mounted) return;

    if (success) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('이메일 인증 완료! 로그인해주세요.'),
          backgroundColor: GxColors.success,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
        ),
      );

      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(
          builder: (context) => const LoginScreen(),
        ),
        (route) => false,
      );
    }
  }

  /// Sprint 22-A: 실제 BE API 호출하여 인증 코드 재전송
  Future<void> _handleResend() async {
    if (!_canResend || _isResending) return;

    setState(() => _isResending = true);

    try {
      final authService = ref.read(authServiceProvider);
      await authService.resendVerification(email: widget.email);

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('새 인증 코드가 발송되었습니다. 이메일을 확인해주세요.'),
          backgroundColor: GxColors.success,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
        ),
      );

      _codeController.clear();
      _startTimer();
    } catch (e) {
      if (!mounted) return;
      final errMsg = e.toString().replaceFirst('Exception: ', '');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(errMsg),
          backgroundColor: GxColors.danger,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
        ),
      );
    } finally {
      if (mounted) setState(() => _isResending = false);
    }
  }

  /// 뒤로가기 시 확인 다이얼로그
  Future<bool> _onWillPop() async {
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.lg)),
        title: const Text('인증 중단', style: TextStyle(color: GxColors.charcoal, fontWeight: FontWeight.w600, fontSize: 16)),
        content: const Text(
          '이메일 인증을 중단하시겠습니까?\n로그인 화면에서 다시 인증할 수 있습니다.',
          style: TextStyle(color: GxColors.slate, fontSize: 13),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('계속 인증', style: TextStyle(color: GxColors.accent, fontWeight: FontWeight.w600)),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('나가기', style: TextStyle(color: GxColors.steel)),
          ),
        ],
      ),
    );
    return result ?? false;
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) async {
        if (didPop) return;
        final shouldPop = await _onWillPop();
        if (shouldPop && context.mounted) {
          Navigator.of(context).pop();
        }
      },
      child: Scaffold(
        backgroundColor: GxColors.cloud,
        appBar: AppBar(
          backgroundColor: GxColors.white,
          elevation: 0,
          foregroundColor: GxColors.charcoal,
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
                '이메일 인증',
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: GxColors.charcoal),
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
            padding: const EdgeInsets.all(20.0),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const SizedBox(height: 24),

                  // 이메일 아이콘
                  Container(
                    width: 64,
                    height: 64,
                    decoration: BoxDecoration(
                      color: GxColors.accentSoft,
                      borderRadius: BorderRadius.circular(GxRadius.lg),
                    ),
                    child: const Icon(Icons.email_outlined, size: 32, color: GxColors.accent),
                  ),
                  const SizedBox(height: 20),

                  // 안내 문구
                  const Text(
                    '이메일 인증',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: GxColors.charcoal),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    widget.email,
                    textAlign: TextAlign.center,
                    style: const TextStyle(fontSize: 14, color: GxColors.accent, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    '위 이메일로 전송된 6자리 인증 코드를\n입력해주세요.',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 13, color: GxColors.slate),
                  ),
                  const SizedBox(height: 24),

                  // 카드 컨테이너
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: GxGlass.cardSm(radius: GxRadius.lg),
                    child: Column(
                      children: [
                        // 인증 코드 입력 필드
                        TextFormField(
                          controller: _codeController,
                          decoration: InputDecoration(
                            labelText: '인증 코드',
                            labelStyle: const TextStyle(color: GxColors.steel, fontSize: 13),
                            hintText: '6자리 숫자',
                            hintStyle: const TextStyle(color: GxColors.silver),
                            prefixIcon: const Icon(Icons.verified_user, color: GxColors.accent),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(GxRadius.sm),
                              borderSide: const BorderSide(color: GxColors.mist),
                            ),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(GxRadius.sm),
                              borderSide: const BorderSide(color: GxColors.mist, width: 1.5),
                            ),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(GxRadius.sm),
                              borderSide: const BorderSide(color: GxColors.accent, width: 1.5),
                            ),
                            counterText: '',
                            filled: true,
                            fillColor: GxColors.white,
                          ),
                          style: const TextStyle(fontSize: 22, letterSpacing: 4, fontWeight: FontWeight.w600, color: GxColors.charcoal),
                          textAlign: TextAlign.center,
                          keyboardType: TextInputType.number,
                          maxLength: 6,
                          textInputAction: TextInputAction.done,
                          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                          validator: _validateCode,
                          enabled: !authState.isLoading,
                          onFieldSubmitted: (_) => _handleVerify(),
                        ),
                        const SizedBox(height: 16),

                        // 타이머 표시
                        Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: _remainingSeconds > 0 ? GxColors.accentSoft : GxColors.dangerBg,
                            borderRadius: BorderRadius.circular(GxRadius.sm),
                          ),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(
                                Icons.timer,
                                color: _remainingSeconds > 0 ? GxColors.accent : GxColors.danger,
                                size: 18,
                              ),
                              const SizedBox(width: 8),
                              Text(
                                _remainingSeconds > 0
                                    ? '남은 시간: ${_formatTime(_remainingSeconds)}'
                                    : '인증 코드가 만료되었습니다.',
                                style: TextStyle(
                                  color: _remainingSeconds > 0 ? GxColors.accent : GxColors.danger,
                                  fontWeight: FontWeight.w600,
                                  fontSize: 13,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),

                  // 에러 메시지 표시
                  if (authState.errorMessage != null)
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: GxColors.dangerBg,
                        borderRadius: BorderRadius.circular(GxRadius.sm),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.error, color: GxColors.danger, size: 18),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              authState.errorMessage!,
                              style: const TextStyle(color: GxColors.danger, fontSize: 13),
                            ),
                          ),
                        ],
                      ),
                    ),
                  if (authState.errorMessage != null) const SizedBox(height: 16),

                  // 인증 확인 버튼
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
                            onTap: authState.isLoading ? null : _handleVerify,
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
                                      '인증 완료',
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
                  const SizedBox(height: 12),

                  // 코드 재전송 버튼
                  Container(
                    height: 44,
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.5),
                      borderRadius: BorderRadius.circular(GxRadius.sm),
                      border: Border.all(color: GxGlass.borderColor, width: 1.5),
                    ),
                    child: Material(
                      color: Colors.transparent,
                      child: InkWell(
                        onTap: (_canResend && !authState.isLoading && !_isResending) ? _handleResend : null,
                        borderRadius: BorderRadius.circular(GxRadius.sm),
                        child: Center(
                          child: _isResending
                              ? const SizedBox(
                                  height: 16,
                                  width: 16,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: GxColors.accent,
                                  ),
                                )
                              : Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(
                                      Icons.refresh,
                                      size: 16,
                                      color: _canResend ? GxColors.slate : GxColors.silver,
                                    ),
                                    const SizedBox(width: 6),
                                    Text(
                                      _canResend ? '인증 코드 재전송' : '재전송 대기 중...',
                                      style: TextStyle(
                                        fontSize: 13,
                                        fontWeight: FontWeight.w500,
                                        color: _canResend ? GxColors.slate : GxColors.silver,
                                      ),
                                    ),
                                  ],
                                ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
