import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../utils/validators.dart';
import '../../utils/design_system.dart';
import 'verify_email_screen.dart';

/// 회원가입 화면
///
/// G-AXIS Design System 적용
/// company 선택 → role 자동 필터링
class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;

  String? _selectedCompany;
  String? _selectedRole;

  /// 협력사 목록 (workers.company 7개 값)
  static const List<String> _companies = [
    'FNI',
    'BAT',
    'TMS(M)',
    'TMS(E)',
    'P&S',
    'C&A',
    'GST',
  ];

  /// 협력사별 허용 역할
  static const Map<String, List<Map<String, String>>> _companyRoles = {
    'FNI': [
      {'code': 'MECH', 'name': 'MECH - Mechanical'},
    ],
    'BAT': [
      {'code': 'MECH', 'name': 'MECH - Mechanical'},
    ],
    'TMS(M)': [
      {'code': 'MECH', 'name': 'MECH - Mechanical'},
    ],
    'TMS(E)': [
      {'code': 'ELEC', 'name': 'ELEC - Electrical'},
    ],
    'P&S': [
      {'code': 'ELEC', 'name': 'ELEC - Electrical'},
    ],
    'C&A': [
      {'code': 'ELEC', 'name': 'ELEC - Electrical'},
    ],
    'GST': [
      {'code': 'PI', 'name': 'PI - Pressure Inspection'},
      {'code': 'QI', 'name': 'QI - Process Inspection'},
      {'code': 'SI', 'name': 'SI - Shipping Inspection'},
      {'code': 'PM', 'name': 'PM - Production Manager'},
    ],
  };

  /// 현재 선택된 협력사에 맞는 역할 목록
  List<Map<String, String>> get _availableRoles {
    if (_selectedCompany == null) return [];
    return _companyRoles[_selectedCompany] ?? [];
  }

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  String? _validateCompany(String? value) {
    if (value == null || value.isEmpty) {
      return '협력사를 선택해주세요.';
    }
    return null;
  }

  String? _validateConfirmPassword(String? value) {
    if (value == null || value.isEmpty) {
      return '비밀번호 확인을 입력해주세요.';
    }
    if (value != _passwordController.text) {
      return '비밀번호가 일치하지 않습니다.';
    }
    return null;
  }

  String? _validateRole(String? value) {
    if (value == null || value.isEmpty) {
      return '역할을 선택해주세요.';
    }
    return null;
  }

  Future<void> _handleRegister() async {
    if (!_formKey.currentState!.validate()) return;
    FocusScope.of(context).unfocus();

    final authNotifier = ref.read(authProvider.notifier);
    final success = await authNotifier.register(
      name: _nameController.text.trim(),
      email: _emailController.text.trim(),
      password: _passwordController.text,
      role: _selectedRole!,
      company: _selectedCompany!,
    );

    if (!mounted) return;

    if (success) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (context) => VerifyEmailScreen(
            email: _emailController.text.trim(),
          ),
        ),
      );
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
              'Create Account',
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
          child: Container(
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
                          color: GxColors.infoBg,
                          borderRadius: BorderRadius.circular(GxRadius.md),
                        ),
                        child: const Icon(Icons.person_add_outlined, size: 14, color: GxColors.info),
                      ),
                      const SizedBox(width: 8),
                      const Text(
                        'Worker Registration',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: GxColors.charcoal,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // 이름
                  _buildLabel('NAME'),
                  const SizedBox(height: 5),
                  TextFormField(
                    controller: _nameController,
                    decoration: _inputDecoration('홍길동'),
                    textInputAction: TextInputAction.next,
                    style: const TextStyle(fontSize: 13, color: GxColors.charcoal),
                    validator: validateName,
                    enabled: !authState.isLoading,
                  ),
                  const SizedBox(height: 12),

                  // 이메일
                  _buildLabel('EMAIL'),
                  const SizedBox(height: 5),
                  TextFormField(
                    controller: _emailController,
                    decoration: _inputDecoration('worker@gst-in.com'),
                    keyboardType: TextInputType.emailAddress,
                    textInputAction: TextInputAction.next,
                    style: const TextStyle(fontSize: 13, color: GxColors.charcoal),
                    validator: validateEmail,
                    enabled: !authState.isLoading,
                  ),
                  const SizedBox(height: 12),

                  // 협력사 선택
                  _buildLabel('COMPANY'),
                  const SizedBox(height: 5),
                  DropdownButtonFormField<String>(
                    initialValue: _selectedCompany,
                    decoration: _inputDecoration('협력사 선택'),
                    style: const TextStyle(fontSize: 13, color: GxColors.charcoal),
                    items: _companies.map((company) {
                      return DropdownMenuItem<String>(
                        value: company,
                        child: Text(company),
                      );
                    }).toList(),
                    onChanged: authState.isLoading
                        ? null
                        : (value) {
                            setState(() {
                              _selectedCompany = value;
                              // 협력사 변경 시 역할 초기화
                              _selectedRole = null;
                              // 역할이 하나뿐이면 자동 선택
                              final roles = _companyRoles[value] ?? [];
                              if (roles.length == 1) {
                                _selectedRole = roles.first['code'];
                              }
                            });
                          },
                    validator: _validateCompany,
                  ),
                  const SizedBox(height: 12),

                  // 역할 선택 (협력사 선택 후 활성화)
                  _buildLabel('ROLE'),
                  const SizedBox(height: 5),
                  DropdownButtonFormField<String>(
                    initialValue: _selectedRole,
                    decoration: _inputDecoration(
                      _selectedCompany == null
                          ? '협력사를 먼저 선택하세요'
                          : 'Select role',
                    ),
                    style: const TextStyle(fontSize: 13, color: GxColors.charcoal),
                    items: _availableRoles.map((role) {
                      return DropdownMenuItem<String>(
                        value: role['code'],
                        child: Text(role['name']!),
                      );
                    }).toList(),
                    onChanged: (authState.isLoading || _selectedCompany == null)
                        ? null
                        : (value) => setState(() => _selectedRole = value),
                    validator: _validateRole,
                  ),
                  const SizedBox(height: 12),

                  // 비밀번호
                  _buildLabel('PASSWORD'),
                  const SizedBox(height: 5),
                  TextFormField(
                    controller: _passwordController,
                    decoration: _inputDecoration('최소 6자 이상').copyWith(
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
                    validator: validatePassword,
                    enabled: !authState.isLoading,
                  ),
                  const SizedBox(height: 12),

                  // 비밀번호 확인
                  _buildLabel('CONFIRM PASSWORD'),
                  const SizedBox(height: 5),
                  TextFormField(
                    controller: _confirmPasswordController,
                    decoration: _inputDecoration('비밀번호를 다시 입력하세요').copyWith(
                      suffixIcon: IconButton(
                        icon: Icon(
                          _obscureConfirmPassword ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                          size: 18,
                          color: GxColors.steel,
                        ),
                        onPressed: () => setState(() => _obscureConfirmPassword = !_obscureConfirmPassword),
                      ),
                    ),
                    obscureText: _obscureConfirmPassword,
                    textInputAction: TextInputAction.done,
                    style: const TextStyle(fontSize: 13, color: GxColors.charcoal),
                    validator: _validateConfirmPassword,
                    enabled: !authState.isLoading,
                    onFieldSubmitted: (_) => _handleRegister(),
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

                  // 회원가입 버튼
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
                            onTap: authState.isLoading ? null : _handleRegister,
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
                                      'Register',
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
      hintStyle: const TextStyle(fontSize: 13, color: GxColors.silver),
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
