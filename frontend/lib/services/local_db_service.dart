import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';

// TODO: SQLite 로컬 DB 서비스 구현

class LocalDbService {
  static Database? _database;
  static const String dbName = 'gaxis_app.db';
  static const int dbVersion = 1;

  // 테이블명
  static const String tasksTable = 'tasks';
  static const String workersTable = 'workers';
  static const String alertsTable = 'alerts';
  static const String productsTable = 'products';

  /// DB 초기화
  Future<Database> initDb() async {
    if (_database != null) return _database!;

    try {
      // TODO: DB 경로 설정 및 생성
      final dbPath = await getDatabasesPath();
      final path = join(dbPath, dbName);

      _database = await openDatabase(
        path,
        version: dbVersion,
        onCreate: _createTables,
        onUpgrade: _onUpgrade,
      );

      return _database!;
    } catch (e) {
      rethrow;
    }
  }

  /// 테이블 생성
  Future<void> _createTables(Database db, int version) async {
    try {
      // TODO: 테이블 스키마 구현
      await db.execute('''
        CREATE TABLE IF NOT EXISTS $tasksTable (
          id TEXT PRIMARY KEY,
          taskId TEXT,
          qrDocId TEXT,
          processType TEXT,
          startedAt TEXT,
          completedAt TEXT,
          duration INTEGER,
          status TEXT,
          createdAt TEXT
        )
      ''');

      await db.execute('''
        CREATE TABLE IF NOT EXISTS $workersTable (
          id TEXT PRIMARY KEY,
          name TEXT,
          email TEXT,
          role TEXT,
          isApproved INTEGER,
          isAdmin INTEGER,
          createdAt TEXT
        )
      ''');

      await db.execute('''
        CREATE TABLE IF NOT EXISTS $alertsTable (
          id TEXT PRIMARY KEY,
          alertType TEXT,
          message TEXT,
          workerName TEXT,
          timestamp TEXT,
          isRead INTEGER
        )
      ''');

      await db.execute('''
        CREATE TABLE IF NOT EXISTS $productsTable (
          qrDocId TEXT PRIMARY KEY,
          serialNumber TEXT,
          model TEXT,
          productionDate TEXT,
          description TEXT
        )
      ''');
    } catch (e) {
      rethrow;
    }
  }

  /// DB 업그레이드
  Future<void> _onUpgrade(Database db, int oldVersion, int newVersion) async {
    // TODO: DB 마이그레이션 로직 구현
  }

  /// DB 인스턴스
  Future<Database> get database async {
    if (_database != null) return _database!;
    return await initDb();
  }

  /// 삽입
  Future<int> insert(String table, Map<String, dynamic> data) async {
    final db = await database;
    return await db.insert(table, data);
  }

  /// 조회
  Future<List<Map<String, dynamic>>> query(String table, {String? where, List<dynamic>? whereArgs}) async {
    final db = await database;
    return await db.query(table, where: where, whereArgs: whereArgs);
  }

  /// 업데이트
  Future<int> update(String table, Map<String, dynamic> data, {required String where, List<dynamic>? whereArgs}) async {
    final db = await database;
    return await db.update(table, data, where: where, whereArgs: whereArgs);
  }

  /// 삭제
  Future<int> delete(String table, {required String where, List<dynamic>? whereArgs}) async {
    final db = await database;
    return await db.delete(table, where: where, whereArgs: whereArgs);
  }

  /// DB 종료
  Future<void> closeDb() async {
    if (_database != null) {
      await _database!.close();
      _database = null;
    }
  }
}
