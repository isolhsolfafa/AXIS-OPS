// Sprint 79 — 미종료 작업 분류 (메인 메뉴)
// 협력사별 + GST 공정별 그룹 catch
// BE: /api/admin/tasks/pending/grouped
// v2.19.7: PI/QI 카드 디자인 컨셉 정합 — Card(elevation 0 + grey border + BorderRadius 12)
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
      backgroundColor: const Color(0xFFF9FAFB),
      appBar: AppBar(
        title: const Text('미종료 작업 (전체)'),
        elevation: 0,
        scrolledUnderElevation: 0,
        backgroundColor: Colors.white,
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
                padding: const EdgeInsets.symmetric(vertical: 8),
                children: [
                  _buildHeader(),
                  const SizedBox(height: 16),
                  _buildSectionTitle('🏭', '협력사별'),
                  ..._partners.map(_buildPartnerCard),
                  if (_partners.isEmpty) _buildEmpty('협력사 미종료 작업 없음'),
                  const SizedBox(height: 20),
                  _buildSectionTitle('🏢', 'GST 공정별'),
                  ..._gstProcesses.map(_buildGstCard),
                  if (_gstProcesses.isEmpty) _buildEmpty('GST 공정 미종료 작업 없음'),
                  const SizedBox(height: 16),
                ],
              ),
            ),
    );
  }

  Widget _buildHeader() {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: Color(0xFFFEDDB7)),
      ),
      color: const Color(0xFFFEF6E7),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            Container(
              width: 40, height: 40,
              decoration: BoxDecoration(
                color: const Color(0xFFFEF3C7),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(Icons.warning_amber_rounded,
                  color: Color(0xFFD97706), size: 22),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '전체 미종료 · $_total건',
                    style: const TextStyle(
                      fontSize: 16, fontWeight: FontWeight.bold,
                      color: Color(0xFF1F2937),
                    ),
                  ),
                  const SizedBox(height: 2),
                  const Text(
                    '협력사별 + GST 공정별 분류',
                    style: TextStyle(fontSize: 12, color: Color(0xFF6B7280)),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionTitle(String emoji, String title) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 6),
      child: Row(
        children: [
          Text(emoji, style: const TextStyle(fontSize: 14)),
          const SizedBox(width: 6),
          Text(
            title,
            style: const TextStyle(
              fontSize: 13, fontWeight: FontWeight.w600,
              color: Color(0xFF374151), letterSpacing: 0.3,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmpty(String label) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: Colors.grey.shade200),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 24),
        child: Center(
          child: Column(
            children: [
              Icon(Icons.check_circle_outline,
                  size: 32, color: Colors.grey.shade400),
              const SizedBox(height: 6),
              Text(label, style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPartnerCard(Map<String, dynamic> p) {
    final color = _categoryColor(p['category'] as String?);
    final colorSoft = _categoryColorSoft(p['category'] as String?);
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: Colors.grey.shade200),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: Row(
          children: [
            // 카테고리 chip
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: colorSoft,
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                p['category'] ?? '-',
                style: TextStyle(
                  fontSize: 10, fontWeight: FontWeight.w700, color: color,
                ),
              ),
            ),
            const SizedBox(width: 10),
            // 협력사 이름
            Expanded(
              child: Text(
                p['name'] ?? '-',
                style: const TextStyle(
                  fontSize: 14, fontWeight: FontWeight.w600,
                  color: Color(0xFF1F2937),
                ),
              ),
            ),
            // 카운트
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: const Color(0xFFFEF3C7),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                '${p['count'] ?? 0}건',
                style: const TextStyle(
                  fontSize: 12, fontWeight: FontWeight.w700,
                  color: Color(0xFFD97706),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildGstCard(Map<String, dynamic> g) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: Colors.grey.shade200),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: const Color(0xFFEDE9FE),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                g['category'] ?? '-',
                style: const TextStyle(
                  fontSize: 10, fontWeight: FontWeight.w700,
                  color: Color(0xFF6366F1),
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                g['label'] ?? '-',
                style: const TextStyle(
                  fontSize: 14, fontWeight: FontWeight.w600,
                  color: Color(0xFF1F2937),
                ),
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: const Color(0xFFEDE9FE),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                '${g['count'] ?? 0}건',
                style: const TextStyle(
                  fontSize: 12, fontWeight: FontWeight.w700,
                  color: Color(0xFF6366F1),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Color _categoryColor(String? cat) {
    switch (cat) {
      case 'MECH': return const Color(0xFFEA580C);
      case 'ELEC': return const Color(0xFF2563EB);
      case 'TM':
      case 'TMS': return const Color(0xFF0D9488);
      default: return const Color(0xFF6B7280);
    }
  }

  Color _categoryColorSoft(String? cat) {
    switch (cat) {
      case 'MECH': return const Color(0xFFFEF3C7);
      case 'ELEC': return const Color(0xFFDBEAFE);
      case 'TM':
      case 'TMS': return const Color(0xFFCCFBF1);
      default: return const Color(0xFFF3F4F6);
    }
  }
}
