// Flask 테스트 서버 주소 (CLAUDE.md 섹션 9.2 참조)
const String apiBaseUrl = 'http://localhost:5001/api';
const String webSocketUrl = 'ws://localhost:5001/ws';
const String appVersion = '0.1.0';

// API 엔드포인트
const String authLoginEndpoint = '/auth/login';
const String authRegisterEndpoint = '/auth/register';
const String authVerifyEmailEndpoint = '/auth/verify-email';
const String authLogoutEndpoint = '/auth/logout';

const String tasksEndpoint = '/tasks';
const String workersEndpoint = '/workers';
const String alertsEndpoint = '/alerts';
const String productsEndpoint = '/products';
