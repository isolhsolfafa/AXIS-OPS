import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../utils/design_system.dart';

/// 개인 설정 화면
///
/// 프로필 정보 (읽기 전용), PIN 설정, 생체인증 설정
class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  bool _pinRegistered = false;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _checkPinStatus();
    });
  }

  Future<void> _checkPinStatus() async {
    try {
      final apiService = ref.read(apiServiceProvider);
      final response = await apiService.get('/auth/pin-status');
      final registered = response['pin_registered'] as bool? ?? false;
      if (mounted) {
        setState(() {
          _pinRegistered = registered;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _pinRegistered = false;
          _isLoading = false;
        });
      }
    }
  }

  String _getRoleDisplayName(String? role) {
    switch (role) {
      case 'MECH': return '기구';
      case 'ELEC': return '전장';
      case 'TM': return 'TMS반제품';
      case 'PI': return '가압검사';
      case 'QI': return '공정검사';
      case 'SI': return '출하검사';
      case 'ADMIN': return '마스터 관리자';
      default: return role ?? '';
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final worker = authState.currentWorker;

    return Scaffold(
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
              '개인 설정',
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
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: GxColors.accent))
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // 프로필 정보 섹션
                  _buildSectionHeader('프로필 정보'),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: GxGlass.cardSm(radius: GxRadius.lg),
                    child: Column(
                      children: [
                        _buildInfoRow(Icons.person_outline, '이름', worker?.name ?? '-'),
                        const Divider(color: GxColors.mist, height: 20),
                        _buildInfoRow(Icons.email_outlined, '이메일', worker?.email ?? '-'),
                        const Divider(color: GxColors.mist, height: 20),
                        _buildInfoRow(
                          Icons.badge_outlined,
                          '역할',
                          _getRoleDisplayName(worker?.role),
                        ),
                        const Divider(color: GxColors.mist, height: 20),
                        _buildInfoRow(
                          Icons.business_outlined,
                          '소속',
                          worker?.company ?? '-',
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),

                  // PIN 설정 섹션
                  _buildSectionHeader('PIN 설정'),
                  const SizedBox(height: 8),
                  Container(
                    decoration: GxGlass.cardSm(radius: GxRadius.lg),
                    child: Material(
                      color: Colors.transparent,
                      child: InkWell(
                        onTap: () async {
                          await Navigator.pushNamed(
                            context,
                            '/pin-settings',
                            arguments: {'pin_registered': _pinRegistered},
                          );
                          // PIN 설정 후 돌아올 때 상태 새로고침
                          _checkPinStatus();
                        },
                        borderRadius: BorderRadius.circular(GxRadius.lg),
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Row(
                            children: [
                              Container(
                                width: 36,
                                height: 36,
                                decoration: BoxDecoration(
                                  color: GxColors.accentSoft,
                                  borderRadius: BorderRadius.circular(GxRadius.md),
                                ),
                                child: const Icon(Icons.pin_outlined, size: 18, color: GxColors.accent),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text(
                                      'PIN 번호',
                                      style: TextStyle(
                                        fontSize: 14,
                                        fontWeight: FontWeight.w500,
                                        color: GxColors.graphite,
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      _pinRegistered ? '등록됨' : '미등록',
                                      style: TextStyle(
                                        fontSize: 12,
                                        color: _pinRegistered ? GxColors.success : GxColors.silver,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                                decoration: BoxDecoration(
                                  color: GxColors.accentSoft,
                                  borderRadius: BorderRadius.circular(GxRadius.sm),
                                ),
                                child: Text(
                                  _pinRegistered ? '변경하기' : '등록하기',
                                  style: const TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w600,
                                    color: GxColors.accent,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),

                  // 생체인증 섹션
                  _buildSectionHeader('생체인증'),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: GxGlass.cardSm(radius: GxRadius.lg),
                    child: Column(
                      children: [
                        _buildBiometricRow(
                          Icons.fingerprint,
                          '지문 인식',
                        ),
                        const Divider(color: GxColors.mist, height: 20),
                        _buildBiometricRow(
                          Icons.face,
                          'Face ID',
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Text(
      title,
      style: const TextStyle(
        fontSize: 12,
        fontWeight: FontWeight.w600,
        color: GxColors.steel,
        letterSpacing: 0.5,
      ),
    );
  }

  Widget _buildInfoRow(IconData icon, String label, String value) {
    return Row(
      children: [
        Icon(icon, size: 18, color: GxColors.steel),
        const SizedBox(width: 10),
        Text(
          label,
          style: const TextStyle(fontSize: 13, color: GxColors.slate),
        ),
        const Spacer(),
        Text(
          value,
          style: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w500,
            color: GxColors.charcoal,
          ),
        ),
      ],
    );
  }

  Widget _buildBiometricRow(IconData icon, String title) {
    return Row(
      children: [
        Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            color: GxColors.mist,
            borderRadius: BorderRadius.circular(GxRadius.md),
          ),
          child: Icon(icon, size: 18, color: GxColors.silver),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: GxColors.steel,
                ),
              ),
              const SizedBox(height: 2),
              const Text(
                '추후 오픈 예정',
                style: TextStyle(fontSize: 12, color: GxColors.silver),
              ),
            ],
          ),
        ),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: GxColors.mist,
            borderRadius: BorderRadius.circular(GxRadius.sm),
          ),
          child: const Text(
            '준비 중',
            style: TextStyle(fontSize: 11, color: GxColors.silver),
          ),
        ),
      ],
    );
  }
}
