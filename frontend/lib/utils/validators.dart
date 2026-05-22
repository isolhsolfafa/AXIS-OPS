// TODO: 추가 유효성 검사 로직 구현

/// v2.18.18 — 회원가입 인증 메일 발송 허용 도메인 (BE auth_service.py ALLOWED_EMAIL_DOMAINS 와 동기화)
/// KT Biz Office SMTP 외부 도메인 차단 catch — @gst-in.com / @naver.com / @gmail.com 만 발송 가능
const allowedEmailDomains = ['gst-in.com', 'naver.com', 'gmail.com'];

/// 이메일 유효성 검사
String? validateEmail(String? value) {
  if (value == null || value.isEmpty) {
    return '이메일을 입력해주세요.';
  }

  final emailRegex = RegExp(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
  );

  if (!emailRegex.hasMatch(value)) {
    return '유효한 이메일 형식을 입력해주세요.';
  }

  // v2.18.18 — 도메인 whitelist 검증
  final domain = value.split('@').last.toLowerCase();
  if (!allowedEmailDomains.contains(domain)) {
    final list = allowedEmailDomains.map((d) => '@$d').join(', ');
    return '지원 메일: $list';
  }

  return null;
}

/// 로그인 ID 유효성 검사 (이메일 또는 일반 계정명 허용)
String? validateLoginId(String? value) {
  if (value == null || value.isEmpty) {
    return '이메일 또는 계정명을 입력해주세요.';
  }
  if (value.length < 2) {
    return '2자 이상 입력해주세요.';
  }
  return null;
}

/// 비밀번호 유효성 검사
String? validatePassword(String? value) {
  if (value == null || value.isEmpty) {
    return '비밀번호를 입력해주세요.';
  }
  
  if (value.length < 6) {
    return '비밀번호는 최소 6자 이상이어야 합니다.';
  }
  
  return null;
}

/// 이름 유효성 검사
String? validateName(String? value) {
  if (value == null || value.isEmpty) {
    return '이름을 입력해주세요.';
  }
  
  if (value.length < 2) {
    return '이름은 최소 2자 이상이어야 합니다.';
  }
  
  return null;
}
