import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

// TODO: 관리자 대시보드 화면 구현

class AdminDashboard extends ConsumerWidget {
  const AdminDashboard({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // TODO: 관리자 전용 통계 및 리포트 표시
    // TODO: 작업자 관리 버튼
    // TODO: 작업 통계 표시
    // TODO: 시스템 모니터링 정보

    return Scaffold(
      appBar: AppBar(
        title: const Text('관리자 대시보드'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('관리자 대시보드'),
            // TODO: 대시보드 컨텐츠 구현
          ],
        ),
      ),
    );
  }
}
