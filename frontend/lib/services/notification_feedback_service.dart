// ignore_for_file: avoid_web_libraries_in_flutter
import 'dart:html' as html;
import 'dart:js_util' as js_util;
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// 알림 소리 + 진동 피드백 서비스 (Sprint 53)
///
/// Web Audio API + navigator.vibrate()를 dart:html로 직접 호출.
/// 패키지 추가 없이 PWA 환경에서 동작.
/// 싱글톤 패턴 — NotificationFeedbackService.instance 사용.
class NotificationFeedbackService {
  NotificationFeedbackService._();

  static final NotificationFeedbackService instance = NotificationFeedbackService._();

  /// 마지막 피드백 시각 (도배 방지)
  DateTime? _lastPlayedAt;

  // SharedPreferences 키
  static const _keySoundEnabled = 'alert_sound_enabled';
  static const _keyVibrationEnabled = 'alert_vibration_enabled';
  static const _keySoundType = 'alert_sound_type';

  /// 5가지 소리 타입
  static const List<Map<String, String>> soundOptions = [
    {'value': 'basic_beep', 'label': '기본 비프'},
    {'value': 'high_beep', 'label': '높은 비프'},
    {'value': 'double_beep', 'label': '더블 비프'},
    {'value': 'chime', 'label': '차임'},
    {'value': 'soft_alert', 'label': '소프트 알림'},
  ];

  /// 포그라운드 알림 피드백 재생
  ///
  /// [alertType]: WebSocket으로 받은 alert_type (선택적 — 추후 타입별 분기 확장 가능)
  ///
  /// 2초 도배 방지. SharedPreferences에서 사용자 설정을 읽어 소리/진동 제어.
  Future<void> playAlertFeedback({String? alertType}) async {
    // 2초 도배 방지
    final now = DateTime.now();
    if (_lastPlayedAt != null &&
        now.difference(_lastPlayedAt!) < const Duration(seconds: 2)) {
      debugPrint('[NotificationFeedback] 도배 방지 — 무시 (마지막: $_lastPlayedAt)');
      return;
    }
    _lastPlayedAt = now;

    try {
      final prefs = await SharedPreferences.getInstance();
      final soundEnabled = prefs.getBool(_keySoundEnabled) ?? true;
      final vibrationEnabled = prefs.getBool(_keyVibrationEnabled) ?? true;
      final soundType = prefs.getString(_keySoundType) ?? 'basic_beep';

      if (soundEnabled) {
        _playSound(soundType);
      }
      if (vibrationEnabled) {
        _vibrate();
      }
    } catch (e) {
      debugPrint('[NotificationFeedback] playAlertFeedback 실패: $e');
    }
  }

  /// 소리 미리듣기 (설정 화면 — 저장된 설정과 무관하게 즉시 재생)
  void previewSound(String soundType) {
    _playSound(soundType);
  }

  // ─────────────────────────────────────────
  // Web Audio API 소리 재생
  // ─────────────────────────────────────────

  /// [soundType] 에 맞는 소리를 Web Audio API로 재생
  void _playSound(String soundType) {
    try {
      switch (soundType) {
        case 'basic_beep':
          _playBasicBeep();
          break;
        case 'high_beep':
          _playHighBeep();
          break;
        case 'double_beep':
          _playDoubleBeep();
          break;
        case 'chime':
          _playChime();
          break;
        case 'soft_alert':
          _playSoftAlert();
          break;
        default:
          _playBasicBeep();
      }
    } catch (e) {
      debugPrint('[NotificationFeedback] _playSound 실패 ($soundType): $e');
    }
  }

  /// Web Audio API JS 코드를 ScriptElement로 주입하여 실행
  ///
  /// qr_scanner_web.dart의 ScriptElement 패턴과 동일한 방식 사용.
  void _execAudioScript(String jsCode) {
    final script = html.ScriptElement()..text = jsCode;
    html.document.head!.append(script);
    script.remove();
  }

  /// basic_beep: 500Hz 0.3초 sine
  void _playBasicBeep() {
    _execAudioScript('''
      (function() {
        try {
          var ctx = new (window.AudioContext || window.webkitAudioContext)();
          var osc = ctx.createOscillator();
          var gain = ctx.createGain();
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.type = 'sine';
          osc.frequency.value = 500;
          gain.gain.setValueAtTime(0.4, ctx.currentTime);
          gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
          osc.start(ctx.currentTime);
          osc.stop(ctx.currentTime + 0.3);
          osc.onended = function() { ctx.close(); };
        } catch(e) { console.warn('[NotificationFeedback] basic_beep 실패:', e); }
      })();
    ''');
  }

  /// high_beep: 800Hz 0.2초 sine
  void _playHighBeep() {
    _execAudioScript('''
      (function() {
        try {
          var ctx = new (window.AudioContext || window.webkitAudioContext)();
          var osc = ctx.createOscillator();
          var gain = ctx.createGain();
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.type = 'sine';
          osc.frequency.value = 800;
          gain.gain.setValueAtTime(0.4, ctx.currentTime);
          gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2);
          osc.start(ctx.currentTime);
          osc.stop(ctx.currentTime + 0.2);
          osc.onended = function() { ctx.close(); };
        } catch(e) { console.warn('[NotificationFeedback] high_beep 실패:', e); }
      })();
    ''');
  }

  /// double_beep: 600Hz 0.15초 x2 (100ms 간격)
  void _playDoubleBeep() {
    _execAudioScript('''
      (function() {
        try {
          var ctx = new (window.AudioContext || window.webkitAudioContext)();
          function beep(startTime) {
            var osc = ctx.createOscillator();
            var gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.type = 'sine';
            osc.frequency.value = 600;
            gain.gain.setValueAtTime(0.4, startTime);
            gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.15);
            osc.start(startTime);
            osc.stop(startTime + 0.15);
          }
          beep(ctx.currentTime);
          beep(ctx.currentTime + 0.25);
          setTimeout(function() { ctx.close(); }, 600);
        } catch(e) { console.warn('[NotificationFeedback] double_beep 실패:', e); }
      })();
    ''');
  }

  /// chime: C5(523Hz) → E5(659Hz) → G5(784Hz) 각 0.15초 (150ms 간격)
  void _playChime() {
    _execAudioScript('''
      (function() {
        try {
          var ctx = new (window.AudioContext || window.webkitAudioContext)();
          var freqs = [523, 659, 784];
          freqs.forEach(function(freq, i) {
            var startTime = ctx.currentTime + i * 0.15;
            var osc = ctx.createOscillator();
            var gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.type = 'sine';
            osc.frequency.value = freq;
            gain.gain.setValueAtTime(0.35, startTime);
            gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.3);
            osc.start(startTime);
            osc.stop(startTime + 0.3);
          });
          setTimeout(function() { ctx.close(); }, 1000);
        } catch(e) { console.warn('[NotificationFeedback] chime 실패:', e); }
      })();
    ''');
  }

  /// soft_alert: 440Hz → 880Hz → 660Hz sweep 0.4초
  void _playSoftAlert() {
    _execAudioScript('''
      (function() {
        try {
          var ctx = new (window.AudioContext || window.webkitAudioContext)();
          var osc = ctx.createOscillator();
          var gain = ctx.createGain();
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.type = 'sine';
          osc.frequency.setValueAtTime(440, ctx.currentTime);
          osc.frequency.linearRampToValueAtTime(880, ctx.currentTime + 0.2);
          osc.frequency.linearRampToValueAtTime(660, ctx.currentTime + 0.4);
          gain.gain.setValueAtTime(0.3, ctx.currentTime);
          gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
          osc.start(ctx.currentTime);
          osc.stop(ctx.currentTime + 0.4);
          osc.onended = function() { ctx.close(); };
        } catch(e) { console.warn('[NotificationFeedback] soft_alert 실패:', e); }
      })();
    ''');
  }

  // ─────────────────────────────────────────
  // 진동
  // ─────────────────────────────────────────

  /// navigator.vibrate(200) — 미지원 환경(iOS Safari 등)에서는 무시
  void _vibrate() {
    try {
      js_util.callMethod(html.window.navigator, 'vibrate', [200]);
    } catch (e) {
      debugPrint('[NotificationFeedback] vibrate 미지원: $e');
    }
  }
}
