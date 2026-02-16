import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
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
  int _remainingSeconds = 600; // 10분 = 600초
  bool _canResend = false;

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
    _remainingSeconds = 600;
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
    // 폼 유효성 검사
    if (!_formKey.currentState!.validate()) {
      return;
    }

    // 키보드 닫기
    FocusScope.of(context).unfocus();

    // 이메일 인증 시도
    final authNotifier = ref.read(authProvider.notifier);
    final success = await authNotifier.verifyEmail(
      email: widget.email,
      code: _codeController.text.trim(),
    );

    if (!mounted) return;

    if (success) {
      // 인증 성공 - 로그인 화면으로 이동
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('이메일 인증 완료! 로그인해주세요.'),
          backgroundColor: Colors.green,
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

  Future<void> _handleResend() async {
    if (!_canResend) return;

    // TODO: Sprint 2에서 재전송 API 구현 시 활성화
    // final authService = ref.read(authServiceProvider);
    // await authService.resendVerificationCode(widget.email);

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('인증 코드를 재전송했습니다.'),
        backgroundColor: Colors.blue,
      ),
    );

    _startTimer();
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('이메일 인증'),
        centerTitle: true,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 40),

                // 이메일 아이콘
                const Icon(
                  Icons.email_outlined,
                  size: 80,
                  color: Colors.blue,
                ),
                const SizedBox(height: 24),

                // 안내 문구
                const Text(
                  '이메일 인증',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  widget.email,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 16,
                    color: Colors.blue,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  '위 이메일로 전송된 6자리 인증 코드를\n입력해주세요.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 16,
                    color: Colors.grey,
                  ),
                ),
                const SizedBox(height: 40),

                // 인증 코드 입력 필드 (큰 입력 필드)
                TextFormField(
                  controller: _codeController,
                  decoration: const InputDecoration(
                    labelText: '인증 코드',
                    hintText: '6자리 숫자',
                    prefixIcon: Icon(Icons.verified_user),
                    border: OutlineInputBorder(),
                    counterText: '',
                  ),
                  style: const TextStyle(
                    fontSize: 24,
                    letterSpacing: 4,
                    fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.center,
                  keyboardType: TextInputType.number,
                  maxLength: 6,
                  textInputAction: TextInputAction.done,
                  inputFormatters: [
                    FilteringTextInputFormatter.digitsOnly,
                  ],
                  validator: _validateCode,
                  enabled: !authState.isLoading,
                  onFieldSubmitted: (_) => _handleVerify(),
                ),
                const SizedBox(height: 16),

                // 타이머 표시
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: _remainingSeconds > 0
                        ? Colors.blue.shade50
                        : Colors.red.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: _remainingSeconds > 0
                          ? Colors.blue.shade200
                          : Colors.red.shade200,
                    ),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.timer,
                        color: _remainingSeconds > 0
                            ? Colors.blue.shade700
                            : Colors.red.shade700,
                        size: 20,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        _remainingSeconds > 0
                            ? '남은 시간: ${_formatTime(_remainingSeconds)}'
                            : '인증 코드가 만료되었습니다.',
                        style: TextStyle(
                          color: _remainingSeconds > 0
                              ? Colors.blue.shade700
                              : Colors.red.shade700,
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),

                // 에러 메시지 표시
                if (authState.errorMessage != null)
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.red.shade50,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.red.shade200),
                    ),
                    child: Row(
                      children: [
                        Icon(Icons.error, color: Colors.red.shade700, size: 20),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            authState.errorMessage!,
                            style: TextStyle(
                              color: Colors.red.shade700,
                              fontSize: 14,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                if (authState.errorMessage != null) const SizedBox(height: 16),

                // 인증 확인 버튼
                SizedBox(
                  height: 56,
                  child: ElevatedButton(
                    onPressed: authState.isLoading ? null : _handleVerify,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.blue,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                    child: authState.isLoading
                        ? const SizedBox(
                            height: 24,
                            width: 24,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              valueColor:
                                  AlwaysStoppedAnimation<Color>(Colors.white),
                            ),
                          )
                        : const Text(
                            '인증 완료',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                  ),
                ),
                const SizedBox(height: 16),

                // 코드 재전송 버튼
                TextButton.icon(
                  onPressed: (_canResend && !authState.isLoading)
                      ? _handleResend
                      : null,
                  icon: const Icon(Icons.refresh),
                  label: Text(
                    _canResend ? '인증 코드 재전송' : '재전송 대기 중...',
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
