import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../providers/auth_provider.dart';
import '../../services/notification_feedback_service.dart';
import '../../utils/design_system.dart';
import '../../utils/app_version.dart';

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

  // ===== 알림 설정 상태 =====
  bool _soundEnabled = true;
  bool _vibrationEnabled = true;
  String _alertSoundType = 'basic_beep';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _checkPinStatus();
      _loadNotificationSettings();
    });
  }

  /// SharedPreferences에서 알림 설정 로드
  Future<void> _loadNotificationSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      if (mounted) {
        setState(() {
          _soundEnabled = prefs.getBool('alert_sound_enabled') ?? true;
          _vibrationEnabled = prefs.getBool('alert_vibration_enabled') ?? true;
          _alertSoundType = prefs.getString('alert_sound_type') ?? 'basic_beep';
        });
      }
    } catch (e) {
      debugPrint('[ProfileScreen] 알림 설정 로드 실패: $e');
    }
  }

  /// 알림 소리 ON/OFF 저장
  Future<void> _setSoundEnabled(bool value) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool('alert_sound_enabled', value);
      if (mounted) setState(() => _soundEnabled = value);
    } catch (e) {
      debugPrint('[ProfileScreen] 알림 소리 설정 저장 실패: $e');
    }
  }

  /// 알림 진동 ON/OFF 저장
  Future<void> _setVibrationEnabled(bool value) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool('alert_vibration_enabled', value);
      if (mounted) setState(() => _vibrationEnabled = value);
    } catch (e) {
      debugPrint('[ProfileScreen] 알림 진동 설정 저장 실패: $e');
    }
  }

  /// 알림 소리 타입 저장
  Future<void> _setSoundType(String value) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('alert_sound_type', value);
      if (mounted) setState(() => _alertSoundType = value);
    } catch (e) {
      debugPrint('[ProfileScreen] 알림 소리 타입 저장 실패: $e');
    }
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

                  // 담당공정 설정 (GST 작업자 또는 관리자만 표시)
                  if (worker?.company == 'GST' || worker?.isAdmin == true) ...[
                    _buildSectionHeader('담당공정'),
                    const SizedBox(height: 8),
                    Container(
                      decoration: GxGlass.cardSm(radius: GxRadius.lg),
                      child: Material(
                        color: Colors.transparent,
                        child: InkWell(
                          onTap: () => _showActiveRoleDialog(context, ref, worker?.activeRole),
                          borderRadius: BorderRadius.circular(GxRadius.lg),
                          child: Padding(
                            padding: const EdgeInsets.all(16),
                            child: Row(
                              children: [
                                Container(
                                  width: 36,
                                  height: 36,
                                  decoration: BoxDecoration(
                                    color: _getRoleColor(worker?.activeRole).withValues(alpha: 0.1),
                                    borderRadius: BorderRadius.circular(GxRadius.md),
                                  ),
                                  child: Icon(Icons.swap_horiz, size: 18, color: _getRoleColor(worker?.activeRole)),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      const Text(
                                        '담당공정 변경',
                                        style: TextStyle(
                                          fontSize: 14,
                                          fontWeight: FontWeight.w500,
                                          color: GxColors.graphite,
                                        ),
                                      ),
                                      const SizedBox(height: 2),
                                      Text(
                                        worker?.activeRole != null
                                            ? _getActiveRoleLabel(worker?.activeRole)
                                            : '미설정',
                                        style: TextStyle(
                                          fontSize: 12,
                                          color: worker?.activeRole != null
                                              ? _getRoleColor(worker?.activeRole)
                                              : GxColors.silver,
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
                                  child: const Text(
                                    '변경하기',
                                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: GxColors.accent),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),
                  ],

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
                  const SizedBox(height: 24),

                  // 알림 설정 섹션
                  _buildSectionHeader('알림 설정', Icons.notifications_active),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: GxGlass.cardSm(radius: GxRadius.lg),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // 알림 소리 드롭다운 + 미리듣기
                        Row(
                          children: [
                            Container(
                              width: 36,
                              height: 36,
                              decoration: BoxDecoration(
                                color: GxColors.accentSoft,
                                borderRadius: BorderRadius.circular(GxRadius.md),
                              ),
                              child: const Icon(Icons.music_note_outlined, size: 18, color: GxColors.accent),
                            ),
                            const SizedBox(width: 12),
                            const Expanded(
                              child: Text(
                                '알림음 종류',
                                style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w500,
                                  color: GxColors.graphite,
                                ),
                              ),
                            ),
                            DropdownButton<String>(
                              value: _alertSoundType,
                              underline: const SizedBox.shrink(),
                              style: const TextStyle(
                                fontSize: 12,
                                color: GxColors.graphite,
                              ),
                              items: NotificationFeedbackService.soundOptions
                                  .map((opt) => DropdownMenuItem<String>(
                                        value: opt['value'],
                                        child: Text(opt['label']!),
                                      ))
                                  .toList(),
                              onChanged: (v) {
                                if (v != null) _setSoundType(v);
                              },
                            ),
                            const SizedBox(width: 4),
                            // 미리듣기 버튼
                            IconButton(
                              icon: const Icon(Icons.play_arrow, size: 20, color: GxColors.accent),
                              tooltip: '미리듣기',
                              onPressed: () {
                                NotificationFeedbackService.instance.previewSound(_alertSoundType);
                              },
                              constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                              padding: EdgeInsets.zero,
                            ),
                          ],
                        ),
                        const Divider(color: GxColors.mist, height: 20),

                        // 알림 소리 ON/OFF
                        Row(
                          children: [
                            Container(
                              width: 36,
                              height: 36,
                              decoration: BoxDecoration(
                                color: _soundEnabled ? GxColors.accentSoft : GxColors.mist,
                                borderRadius: BorderRadius.circular(GxRadius.md),
                              ),
                              child: Icon(
                                _soundEnabled ? Icons.volume_up : Icons.volume_off,
                                size: 18,
                                color: _soundEnabled ? GxColors.accent : GxColors.silver,
                              ),
                            ),
                            const SizedBox(width: 12),
                            const Expanded(
                              child: Text(
                                '알림 소리',
                                style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w500,
                                  color: GxColors.graphite,
                                ),
                              ),
                            ),
                            Switch(
                              value: _soundEnabled,
                              activeColor: GxColors.accent,
                              onChanged: _setSoundEnabled,
                            ),
                          ],
                        ),
                        const Divider(color: GxColors.mist, height: 20),

                        // 알림 진동 ON/OFF
                        Row(
                          children: [
                            Container(
                              width: 36,
                              height: 36,
                              decoration: BoxDecoration(
                                color: _vibrationEnabled ? GxColors.accentSoft : GxColors.mist,
                                borderRadius: BorderRadius.circular(GxRadius.md),
                              ),
                              child: Icon(
                                Icons.vibration,
                                size: 18,
                                color: _vibrationEnabled ? GxColors.accent : GxColors.silver,
                              ),
                            ),
                            const SizedBox(width: 12),
                            const Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    '알림 진동',
                                    style: TextStyle(
                                      fontSize: 13,
                                      fontWeight: FontWeight.w500,
                                      color: GxColors.graphite,
                                    ),
                                  ),
                                  SizedBox(height: 2),
                                  Text(
                                    'iOS Safari는 진동 미지원',
                                    style: TextStyle(fontSize: 11, color: GxColors.silver),
                                  ),
                                ],
                              ),
                            ),
                            Switch(
                              value: _vibrationEnabled,
                              activeColor: GxColors.accent,
                              onChanged: _setVibrationEnabled,
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),

                  // 앱 정보 섹션
                  _buildSectionHeader('앱 정보'),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: GxGlass.cardSm(radius: GxRadius.lg),
                    child: Column(
                      children: [
                        _buildInfoRow(Icons.info_outline, '버전', AppVersion.version),
                        const Divider(color: GxColors.mist, height: 20),
                        _buildInfoRow(Icons.calendar_today_outlined, '빌드', AppVersion.buildDate),
                      ],
                    ),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _buildSectionHeader(String title, [IconData? icon]) {
    if (icon == null) {
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
    return Row(
      children: [
        Icon(icon, size: 14, color: GxColors.steel),
        const SizedBox(width: 6),
        Text(
          title,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: GxColors.steel,
            letterSpacing: 0.5,
          ),
        ),
      ],
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

  /// 담당공정 한국어 레이블
  String _getActiveRoleLabel(String? role) {
    switch (role) {
      case 'PI': return 'PI 가압검사';
      case 'QI': return 'QI 공정검사';
      case 'SI': return 'SI 마무리공정';
      default: return role ?? '미설정';
    }
  }

  /// 담당공정 색상
  Color _getRoleColor(String? role) {
    switch (role) {
      case 'PI': return GxColors.success;
      case 'QI': return const Color(0xFF7C3AED);
      case 'SI': return GxColors.accent;
      default: return GxColors.steel;
    }
  }

  /// 담당공정 선택 다이얼로그
  Future<void> _showActiveRoleDialog(BuildContext context, WidgetRef ref, String? currentRole) async {
    final roles = [
      {'code': 'PI', 'label': 'PI 가압검사', 'icon': Icons.compress, 'color': GxColors.success},
      {'code': 'QI', 'label': 'QI 공정검사', 'icon': Icons.verified, 'color': const Color(0xFF7C3AED)},
      {'code': 'SI', 'label': 'SI 마무리공정', 'icon': Icons.local_shipping, 'color': GxColors.accent},
      {'code': 'PM', 'label': 'PM 생산관리', 'icon': Icons.supervisor_account, 'color': const Color(0xFFEA580C)},
    ];

    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GxRadius.lg)),
        title: const Text(
          '담당공정 선택',
          style: TextStyle(color: GxColors.charcoal, fontWeight: FontWeight.w600, fontSize: 15),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: roles.map((r) {
            final isSelected = currentRole == r['code'];
            final color = r['color'] as Color;
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: InkWell(
                onTap: () async {
                  Navigator.of(ctx).pop();
                  await ref.read(authProvider.notifier).changeActiveRole(r['code'] as String);
                  if (mounted) setState(() {});
                },
                borderRadius: BorderRadius.circular(GxRadius.md),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(
                    color: isSelected ? color.withValues(alpha: 0.1) : GxColors.cloud,
                    borderRadius: BorderRadius.circular(GxRadius.md),
                    border: Border.all(
                      color: isSelected ? color : GxColors.mist,
                      width: isSelected ? 1.5 : 1,
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(r['icon'] as IconData, size: 18, color: color),
                      const SizedBox(width: 10),
                      Text(
                        r['label'] as String,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                          color: isSelected ? color : GxColors.graphite,
                        ),
                      ),
                      if (isSelected) ...[
                        const Spacer(),
                        Icon(Icons.check_circle, size: 16, color: color),
                      ],
                    ],
                  ),
                ),
              ),
            );
          }).toList(),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('닫기', style: TextStyle(color: GxColors.slate)),
          ),
        ],
      ),
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
