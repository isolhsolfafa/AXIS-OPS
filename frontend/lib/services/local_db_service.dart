import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

/// 웹 호환 로컬 저장소 서비스 (shared_preferences 기반)
///
/// CLAUDE.md PWA 전략에 따라 sqflite 대신 shared_preferences 사용
/// 오프라인 동기화 큐 및 로컬 캐시 역할
class LocalDbService {
  static SharedPreferences? _prefs;

  // 저장소 키 프리픽스
  static const String _tasksKey = 'local_tasks';
  static const String _workersKey = 'local_workers';
  static const String _alertsKey = 'local_alerts';
  static const String _productsKey = 'local_products';
  static const String _syncQueueKey = 'offline_sync_queue';

  /// 초기화
  Future<void> init() async {
    _prefs ??= await SharedPreferences.getInstance();
  }

  Future<SharedPreferences> get _storage async {
    if (_prefs == null) await init();
    return _prefs!;
  }

  // --- 범용 CRUD ---

  /// 테이블(키)에 아이템 목록 저장
  Future<void> _saveList(String key, List<Map<String, dynamic>> items) async {
    final prefs = await _storage;
    await prefs.setString(key, jsonEncode(items));
  }

  /// 테이블(키)에서 아이템 목록 조회
  Future<List<Map<String, dynamic>>> _getList(String key) async {
    final prefs = await _storage;
    final data = prefs.getString(key);
    if (data == null) return [];
    final list = jsonDecode(data) as List;
    return list.cast<Map<String, dynamic>>();
  }

  // --- Tasks ---

  Future<void> saveTasks(List<Map<String, dynamic>> tasks) async {
    await _saveList(_tasksKey, tasks);
  }

  Future<List<Map<String, dynamic>>> getTasks() async {
    return _getList(_tasksKey);
  }

  Future<void> addTask(Map<String, dynamic> task) async {
    final tasks = await getTasks();
    tasks.add(task);
    await saveTasks(tasks);
  }

  Future<void> updateTask(String id, Map<String, dynamic> updated) async {
    final tasks = await getTasks();
    final index = tasks.indexWhere((t) => t['id']?.toString() == id);
    if (index != -1) {
      tasks[index] = {...tasks[index], ...updated};
      await saveTasks(tasks);
    }
  }

  // --- Alerts ---

  Future<void> saveAlerts(List<Map<String, dynamic>> alerts) async {
    await _saveList(_alertsKey, alerts);
  }

  Future<List<Map<String, dynamic>>> getAlerts() async {
    return _getList(_alertsKey);
  }

  // --- Products ---

  Future<void> saveProducts(List<Map<String, dynamic>> products) async {
    await _saveList(_productsKey, products);
  }

  Future<List<Map<String, dynamic>>> getProducts() async {
    return _getList(_productsKey);
  }

  // --- 오프라인 동기화 큐 ---

  /// 오프라인 작업을 동기화 큐에 추가
  Future<void> addToSyncQueue(Map<String, dynamic> action) async {
    final queue = await getSyncQueue();
    action['queued_at'] = DateTime.now().toIso8601String();
    queue.add(action);
    await _saveList(_syncQueueKey, queue);
  }

  /// 동기화 큐 조회
  Future<List<Map<String, dynamic>>> getSyncQueue() async {
    return _getList(_syncQueueKey);
  }

  /// 동기화 큐 비우기
  Future<void> clearSyncQueue() async {
    final prefs = await _storage;
    await prefs.remove(_syncQueueKey);
  }

  // --- 전체 초기화 ---

  /// 모든 로컬 데이터 삭제
  Future<void> clearAll() async {
    final prefs = await _storage;
    await prefs.remove(_tasksKey);
    await prefs.remove(_workersKey);
    await prefs.remove(_alertsKey);
    await prefs.remove(_productsKey);
    await prefs.remove(_syncQueueKey);
  }
}
