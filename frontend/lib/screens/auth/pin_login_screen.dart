import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../utils/design_system.dart';

/// PIN 로그인 화면
///
/// PIN이 등록된 경우 앱 시작 시 표시
/// 3회 실패 시 잠금 → 이메일 로그인으로 리다이렉트
class PinLoginScreen extends ConsumerStatefulWidget {
  const PinLoginScreen({super.key});

  @override
  ConsumerState<PinLoginScreen> createState() => _PinLoginScreenState();
}

class _PinLoginScreenState extends ConsumerState<PinLoginScreen> {
  String _enteredPin = '';
  int _failCount = 0;
  bool _isLocked = false;
  bool _isLoading = false;
  String? _errorMessage;

  String? _workerName;
  String? _workerCompany;
  int? _workerId;

  @override
  void initState() {
    super.initState();
    _loadWorkerInfo();
  }

  Future<void> _loadWorkerInfo() async {
    // authProvider에 worker 정보가 있으면 사용
    final authState = ref.read(authProvider);
    if (authState.currentWorker != null) {
      setState(() {
        _workerName = authState.currentWorker!.name;
        _workerCompany = authState.currentWorker!.company;
        _workerId = authState.currentWorker!.id;
      });
      return;
    }
    // 없으면 secure storage에서 로드 (앱 재시작 시)
    final authService = ref.read(authProvider.notifier).authService;
    final workerData = await authService.getWorkerData();
    final workerId = await authService.getWorkerId();
    if (mounted && workerData != null) {
      setState(() {
        _workerName = workerData['name'] as String?;
        _workerCompany = workerData['company'] as String?;
        _workerId = workerId;
      });
    }
  }

  void _onKeyPress(String key) {
    if (_enteredPin.length >= 4 || _isLocked || _isLoading) return;
    setState(() {
      _enteredPin += key;
      _errorMessage = null;
    });
    if (_enteredPin.length == 4) {
      Future.delayed(const Duration(milliseconds: 150), _submitPin);
    }
  }

  void _onDelete() {
    if (_enteredPin.isEmpty || _isLocked) return;
    setState(() {
      _enteredPin = _enteredPin.substring(0, _enteredPin.length - 1);
      _errorMessage = null;
    });
  }

  Future<void> _submitPin() async {
    setState(() => _isLoading = true);
    try {
      final authNotifier = ref.read(authProvider.notifier);
      final apiService = ref.read(apiServiceProvider);
      final authService = authNotifier.authService;
      final deviceId = await authService.getDeviceId();
      final response = await apiService.post(
        '/auth/pin-login',
        data: {
          'worker_id': _workerId,
          'pin': _enteredPin,
          'device_id': deviceId,
        },
      );

      // PIN 로그인 성공 → 토큰 저장 + auth 상태 갱신
      if (response['access_token'] != null) {
        await authService.saveToken(response['access_token']);
      }
      if (response['refresh_token'] != null) {
        await authService.saveRefreshToken(response['refresh_token']);
      }

      // auth 상태 갱신 (worker 데이터 로드)
      await authNotifier.tryAutoLogin();

      if (mounted) {
        // 마지막 경로 복원 시도
        final lastRoute = await authService.getLastRoute();
        if (lastRoute != null && lastRoute['route'] != null) {
          final routeName = lastRoute['route'] as String;
          final args = lastRoute['args'] as Map<String, dynamic>?;
          if (routeName == '/home') {
            Navigator.of(context).pushReplacementNamed('/home');
          } else {
            Navigator.of(context).pushReplacementNamed('/home');
            Navigator.of(context).pushNamed(routeName, arguments: args);
          }
        } else {
          Navigator.of(context).pushReplacementNamed('/home');
        }
      }
    } catch (e) {
      final newFailCount = _failCount + 1;
      if (newFailCount >= 3) {
        setState(() {
          _isLocked = true;
          _failCount = newFailCount;
          _enteredPin = '';
          _isLoading = false;
          _errorMessage = 'PIN이 잠겼습니다. 이메일로 로그인해주세요.';
        });
      } else {
        setState(() {
          _failCount = newFailCount;
          _enteredPin = '';
          _isLoading = false;
          _errorMessage = 'PIN이 일치하지 않습니다 ($_failCount/3)';
        });
      }
    }
  }

  Future<void> _goToEmailLogin() async {
    // 로그아웃 후 루트로 이동 → AuthGate가 로그인 화면 표시
    await ref.read(authProvider.notifier).logout();
    if (mounted) {
      Navigator.of(context).pushNamedAndRemoveUntil('/', (route) => false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: GxColors.charcoal,
      body: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 60),

            // 사용자 정보
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              child: Column(
                children: [
                  Container(
                    width: 56,
                    height: 56,
                    decoration: BoxDecoration(
                      color: GxColors.graphite,
                      borderRadius: BorderRadius.circular(28),
                    ),
                    child: const Icon(Icons.person, color: GxColors.white, size: 28),
                  ),
                  const SizedBox(height: 12),
                  if (_workerName != null)
                    Text(
                      _workerName!,
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w600,
                        color: GxColors.white,
                      ),
                    ),
                  if (_workerCompany != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      _workerCompany!,
                      style: const TextStyle(fontSize: 13, color: GxColors.silver),
                    ),
                  ],
                ],
              ),
            ),

            const SizedBox(height: 24),

            // PIN 입력 안내
            const Text(
              'PIN 번호를 입력하세요',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w400,
                color: GxColors.white,
              ),
            ),

            const SizedBox(height: 16),

            // 에러 메시지
            if (_errorMessage != null)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 32),
                child: Text(
                  _errorMessage!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 13, color: GxColors.danger),
                ),
              ),

            const SizedBox(height: 20),

            // PIN 점 표시
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(4, (index) {
                final filled = index < _enteredPin.length;
                return Container(
                  margin: const EdgeInsets.symmetric(horizontal: 10),
                  width: 16,
                  height: 16,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: filled ? GxColors.white : Colors.transparent,
                    border: Border.all(
                      color: filled ? GxColors.white : GxColors.slate,
                      width: 2,
                    ),
                  ),
                );
              }),
            ),

            const Spacer(),

            // 키패드 (잠긴 경우 비활성화)
            if (!_isLocked)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 32),
                child: Column(
                  children: [
                    _buildKeyRow(['1', '2', '3']),
                    const SizedBox(height: 12),
                    _buildKeyRow(['4', '5', '6']),
                    const SizedBox(height: 12),
                    _buildKeyRow(['7', '8', '9']),
                    const SizedBox(height: 12),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      children: [
                        _buildEmptyKey(),
                        _buildNumberKey('0'),
                        _isLoading
                            ? const SizedBox(
                                width: 72,
                                height: 72,
                                child: Center(
                                  child: SizedBox(
                                    width: 24,
                                    height: 24,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      valueColor: AlwaysStoppedAnimation<Color>(GxColors.white),
                                    ),
                                  ),
                                ),
                              )
                            : _buildDeleteKey(),
                      ],
                    ),
                  ],
                ),
              ),

            const SizedBox(height: 24),

            // 이메일로 로그인 링크
            TextButton(
              onPressed: _goToEmailLogin,
              child: const Text(
                '이메일로 로그인',
                style: TextStyle(
                  fontSize: 14,
                  color: GxColors.silver,
                  decoration: TextDecoration.underline,
                  decorationColor: GxColors.silver,
                ),
              ),
            ),

            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  Widget _buildKeyRow(List<String> keys) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: keys.map((k) => _buildNumberKey(k)).toList(),
    );
  }

  Widget _buildNumberKey(String number) {
    return GestureDetector(
      onTap: () => _onKeyPress(number),
      child: Container(
        width: 72,
        height: 72,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: GxColors.graphite,
        ),
        child: Center(
          child: Text(
            number,
            style: const TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.w400,
              color: GxColors.white,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDeleteKey() {
    return GestureDetector(
      onTap: _onDelete,
      child: Container(
        width: 72,
        height: 72,
        decoration: const BoxDecoration(shape: BoxShape.circle),
        child: const Center(
          child: Icon(Icons.backspace_outlined, color: GxColors.white, size: 24),
        ),
      ),
    );
  }

  Widget _buildEmptyKey() {
    return const SizedBox(width: 72, height: 72);
  }
}
