import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

// TODO: 작업자 승인 화면 구현

class WorkerApprovalScreen extends ConsumerWidget {
  const WorkerApprovalScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // TODO: 대기 중인 작업자 목록 조회
    // TODO: 작업자 정보 표시
    // TODO: 승인 버튼
    // TODO: 거절 버튼
    // TODO: 작업자 역할 지정 기능

    return Scaffold(
      appBar: AppBar(
        title: const Text('작업자 승인'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('작업자 승인 화면'),
            // TODO: 작업자 승인 목록 구현
          ],
        ),
      ),
    );
  }
}
