import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../utils/design_system.dart';

/// PIN 설정 화면
///
/// PIN 등록/변경 기능 제공
/// - 등록: 새 PIN 입력 → 확인 → 서버 저장
/// - 변경: 현재 PIN 입력 → 새 PIN 입력 → 확인 → 서버 저장
class PinSettingsScreen extends ConsumerStatefulWidget {
  const PinSettingsScreen({super.key});

  @override
  ConsumerState<PinSettingsScreen> createState() => _PinSettingsScreenState();
}

class _PinSettingsScreenState extends ConsumerState<PinSettingsScreen> {
  // 현재 입력 단계: 'current' | 'new' | 'confirm'
  String _step = 'new';
  bool _pinRegistered = false;

  String _currentPin = '';
  String _newPin = '';
  String _confirmPin = '';

  String _enteredPin = '';
  String? _errorMessage;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final args = ModalRoute.of(context)?.settings.arguments;
      if (args is Map<String, dynamic>) {
        final registered = args['pin_registered'] as bool? ?? false;
        setState(() {
          _pinRegistered = registered;
          _step = registered ? 'current' : 'new';
        });
      }
    });
  }

  String get _stepTitle {
    switch (_step) {
      case 'current': return '현재 PIN을 입력하세요';
      case 'new': return 'PIN 번호를 입력하세요';
      case 'confirm': return '다시 한번 입력하세요';
      default: return '';
    }
  }

  void _onKeyPress(String key) {
    if (_enteredPin.length >= 4) return;
    setState(() {
      _enteredPin += key;
      _errorMessage = null;
    });
    if (_enteredPin.length == 4) {
      Future.delayed(const Duration(milliseconds: 150), _processPin);
    }
  }

  void _onDelete() {
    if (_enteredPin.isEmpty) return;
    setState(() {
      _enteredPin = _enteredPin.substring(0, _enteredPin.length - 1);
      _errorMessage = null;
    });
  }

  Future<void> _processPin() async {
    final pin = _enteredPin;

    if (_step == 'current') {
      setState(() {
        _currentPin = pin;
        _enteredPin = '';
        _step = 'new';
      });
    } else if (_step == 'new') {
      setState(() {
        _newPin = pin;
        _enteredPin = '';
        _step = 'confirm';
      });
    } else if (_step == 'confirm') {
      setState(() {
        _confirmPin = pin;
      });

      if (_newPin != _confirmPin) {
        setState(() {
          _enteredPin = '';
          _newPin = '';
          _confirmPin = '';
          _step = 'new';
          _errorMessage = 'PIN이 일치하지 않습니다. 다시 시도해주세요.';
        });
        return;
      }

      // PIN 저장 API 호출
      await _submitPin();
    }
  }

  Future<void> _submitPin() async {
    setState(() => _isLoading = true);
    try {
      final apiService = ref.read(apiServiceProvider);

      if (_pinRegistered) {
        // PIN 변경
        await apiService.put(
          '/auth/change-pin',
          data: {
            'current_pin': _currentPin,
            'new_pin': _newPin,
          },
        );
      } else {
        // PIN 등록
        await apiService.post(
          '/auth/set-pin',
          data: {'pin': _newPin},
        );
      }

      // PIN 등록 상태 로컬 캐시 저장
      final authService = ref.read(authProvider.notifier).authService;
      await authService.savePinRegistered(true);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(_pinRegistered ? 'PIN이 변경되었습니다.' : 'PIN이 등록되었습니다.'),
            backgroundColor: GxColors.success,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.sm)),
          ),
        );
        Navigator.of(context).pop();
      }
    } catch (e) {
      setState(() {
        _enteredPin = '';
        _currentPin = '';
        _newPin = '';
        _confirmPin = '';
        _step = _pinRegistered ? 'current' : 'new';
        _errorMessage = e.toString().replaceFirst('Exception: ', '');
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: GxColors.charcoal,
      appBar: AppBar(
        backgroundColor: GxColors.charcoal,
        elevation: 0,
        foregroundColor: GxColors.white,
        title: Text(
          _pinRegistered ? 'PIN 변경' : 'PIN 등록',
          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: GxColors.white),
        ),
        centerTitle: true,
        iconTheme: const IconThemeData(color: GxColors.white),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: GxColors.white))
          : Column(
              children: [
                const SizedBox(height: 48),

                // 단계 표시
                Text(
                  _stepTitle,
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w500,
                    color: GxColors.white,
                  ),
                ),
                const SizedBox(height: 8),

                // 에러 메시지
                if (_errorMessage != null)
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 32),
                    child: Text(
                      _errorMessage!,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 13,
                        color: GxColors.danger,
                      ),
                    ),
                  ),

                const SizedBox(height: 32),

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

                // 숫자 키패드
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
                          _buildDeleteKey(),
                        ],
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 48),
              ],
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
