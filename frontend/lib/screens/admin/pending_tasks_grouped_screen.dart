// Sprint 79 — 미종료 작업 분류 (메인 메뉴, admin only)
// 협력사별 + GST 공정별 그룹 catch
// BE: /api/admin/tasks/pending/grouped
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';

class PendingTasksGroupedScreen extends ConsumerStatefulWidget {
  const PendingTasksGroupedScreen({super.key});

  @override
  ConsumerState<PendingTasksGroupedScreen> createState() =>
      _PendingTasksGroupedScreenState();
}

class _PendingTasksGroupedScreenState
    extends ConsumerState<PendingTasksGroupedScreen> {
  int _total = 0;
  List<Map<String, dynamic>> _partners = [];
  List<Map<String, dynamic>> _gstProcesses = [];
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _fetch());
  }

  Future<void> _fetch() async {
    setState(() => _loading = true);
    try {
      final api = ref.read(apiServiceProvider);
      final res = await api.get('/admin/tasks/pending/grouped');
      if (mounted) {
        setState(() {
          _total = (res['total'] as int?) ?? 0;
          _partners = List<Map<String, dynamic>>.from(res['partners'] as List? ?? []);
          _gstProcesses =
              List<Map<String, dynamic>>.from(res['gst_processes'] as List? ?? []);
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('분류 조회 실패: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('미종료 작업 (전체)'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _fetch),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _fetch,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(12),
                children: [
                  _buildHeader(),
                  const SizedBox(height: 16),
                  _buildSectionTitle('🏭 협력사별'),
                  ..._partners.map(_buildPartnerRow),
                  if (_partners.isEmpty)
                    const Padding(
                      padding: EdgeInsets.all(16),
                      child: Center(child: Text('협력사 미종료 작업 없음')),
                    ),
                  const SizedBox(height: 16),
                  _buildSectionTitle('🏢 GST 공정별'),
                  ..._gstProcesses.map(_buildGstRow),
                  if (_gstProcesses.isEmpty)
                    const Padding(
                      padding: EdgeInsets.all(16),
                      child: Center(child: Text('GST 공정 미종료 작업 없음')),
                    ),
                ],
              ),
            ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.deepOrange.shade50,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          const Icon(Icons.warning_amber, color: Colors.deepOrange, size: 32),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '전체 미종료: $_total건',
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const Text(
                '협력사 + GST 공정 분류 catch',
                style: TextStyle(fontSize: 12, color: Colors.black54),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Text(
        title,
        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
      ),
    );
  }

  Widget _buildPartnerRow(Map<String, dynamic> p) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: _categoryColor(p['category'] as String?),
          child: Text(
            (p['category'] as String?)?.substring(0, 1) ?? '?',
            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
          ),
        ),
        title: Text(p['name'] ?? '-'),
        subtitle: Text('${p['category'] ?? '-'} 카테고리'),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: Colors.deepOrange.shade100,
            borderRadius: BorderRadius.circular(16),
          ),
          child: Text(
            '${p['count'] ?? 0}건',
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
        ),
      ),
    );
  }

  Widget _buildGstRow(Map<String, dynamic> g) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: Colors.blue.shade400,
          child: Text(
            (g['category'] as String?) ?? '?',
            style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
          ),
        ),
        title: Text(g['label'] ?? '-'),
        subtitle: Text('GST 영역 ${g['category'] ?? '-'} 공정'),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: Colors.blue.shade100,
            borderRadius: BorderRadius.circular(16),
          ),
          child: Text(
            '${g['count'] ?? 0}건',
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
        ),
      ),
    );
  }

  Color _categoryColor(String? cat) {
    switch (cat) {
      case 'MECH': return Colors.indigo;
      case 'ELEC': return Colors.amber.shade700;
      case 'TM':
      case 'TMS': return Colors.purple;
      default: return Colors.grey;
    }
  }
}
