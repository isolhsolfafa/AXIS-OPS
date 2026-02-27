import 'package:flutter/material.dart';

/// G-AXIS Design System Tokens
/// 참고: /dev/my_app/test_server/static/index.html 디자인 시스템 기반
class GxColors {
  // Core Brand (Gray Scale)
  static const charcoal = Color(0xFF2A2D35);
  static const graphite = Color(0xFF3D4150);
  static const slate = Color(0xFF5A5F72);
  static const steel = Color(0xFF8B90A0);
  static const silver = Color(0xFFB8BCC8);
  static const mist = Color(0xFFE8EAF0);
  static const cloud = Color(0xFFF3F4F7);
  static const snow = Color(0xFFFAFBFD);
  static const white = Color(0xFFFFFFFF);

  // Accent (Indigo Purple)
  static const accent = Color(0xFF6366F1);
  static const accentHover = Color(0xFF818CF8);
  static Color accentSoft = const Color(0xFF6366F1).withValues(alpha: 0.08);
  static Color accentMedium = const Color(0xFF6366F1).withValues(alpha: 0.15);
  static Color accentGlow = const Color(0xFF6366F1).withValues(alpha: 0.25);

  // Status
  static const success = Color(0xFF10B981);
  static Color successBg = const Color(0xFF10B981).withValues(alpha: 0.08);
  static const warning = Color(0xFFF59E0B);
  static Color warningBg = const Color(0xFFF59E0B).withValues(alpha: 0.08);
  static const danger = Color(0xFFEF4444);
  static Color dangerBg = const Color(0xFFEF4444).withValues(alpha: 0.08);
  static const info = Color(0xFF3B82F6);
  static Color infoBg = const Color(0xFF3B82F6).withValues(alpha: 0.08);
}

class GxRadius {
  static const double sm = 6;
  static const double md = 10;
  static const double lg = 14;
  static const double xl = 18;
}

class GxShadows {
  static List<BoxShadow> card = [
    BoxShadow(
      color: Colors.black.withValues(alpha: 0.04),
      blurRadius: 8,
      offset: const Offset(0, 2),
    ),
    BoxShadow(
      color: Colors.black.withValues(alpha: 0.04),
      spreadRadius: 1,
    ),
  ];

  static List<BoxShadow> md = [
    BoxShadow(
      color: Colors.black.withValues(alpha: 0.06),
      blurRadius: 12,
      offset: const Offset(0, 4),
    ),
    BoxShadow(
      color: Colors.black.withValues(alpha: 0.04),
      blurRadius: 3,
      offset: const Offset(0, 1),
    ),
  ];

  static List<BoxShadow> lg = [
    BoxShadow(
      color: Colors.black.withValues(alpha: 0.08),
      blurRadius: 24,
      offset: const Offset(0, 8),
    ),
    BoxShadow(
      color: Colors.black.withValues(alpha: 0.04),
      blurRadius: 6,
      offset: const Offset(0, 2),
    ),
  ];

  static List<BoxShadow> glass = [
    BoxShadow(
      color: const Color(0xFF6366F1).withValues(alpha: 0.18),
      blurRadius: 48,
      offset: const Offset(0, 16),
    ),
  ];

  static List<BoxShadow> glassSm = [
    BoxShadow(
      color: Colors.black.withValues(alpha: 0.06),
      blurRadius: 16,
      offset: const Offset(0, 4),
    ),
  ];
}

/// 글래스모피즘 그라디언트
class GxGradients {
  static const background = LinearGradient(
    begin: Alignment(-1, -1),
    end: Alignment(1, 1),
    colors: [
      Color(0xFF667EEA),
      Color(0xFF764BA2),
      Color(0xFFF093FB),
      Color(0xFF4FACFE),
    ],
    stops: [0.0, 0.33, 0.66, 1.0],
  );

  static const accentButton = LinearGradient(
    begin: Alignment(-1, -1),
    end: Alignment(1, 1),
    colors: [Color(0xFF6366F1), Color(0xFF818CF8)],
  );
}

/// 글래스모피즘 카드/보더 스타일
class GxGlass {
  static Color cardBg = Colors.white.withValues(alpha: 0.72);
  static Color cardBgLight = Colors.white.withValues(alpha: 0.5);
  static Color borderColor = Colors.white.withValues(alpha: 0.25);
  static Color borderLight = Colors.white.withValues(alpha: 0.5);

  static BoxDecoration card({double radius = 24}) => BoxDecoration(
    color: cardBg,
    borderRadius: BorderRadius.circular(radius),
    border: Border.all(color: borderColor, width: 1),
    boxShadow: GxShadows.glass,
  );

  static BoxDecoration cardSm({double radius = 10}) => BoxDecoration(
    color: cardBgLight,
    borderRadius: BorderRadius.circular(radius),
    border: Border.all(color: borderColor, width: 1),
    boxShadow: GxShadows.glassSm,
  );
}
