#!/bin/bash
# G-AXIS BE/FE 재시작 스크립트
# 사용법:
#   ./restart.sh        → BE + FE 둘 다 재시작
#   ./restart.sh fe     → FE만 재시작
#   ./restart.sh be     → BE만 재시작

DIR="$(cd "$(dirname "$0")" && pwd)"

restart_be() {
  echo "[BE] 종료 중..."
  pkill -f "python.*run.py" 2>/dev/null
  lsof -ti:5001 | xargs kill -9 2>/dev/null
  sleep 1
  echo "[BE] 시작 중... (port 5001)"
  cd "$DIR/backend" && nohup python3 run.py > /tmp/backend-run.log 2>&1 &
  echo "[BE] PID: $!"
}

restart_fe() {
  echo "[FE] 종료 중..."
  pkill -f "flutter run" 2>/dev/null
  pkill -f "dart.*flutter" 2>/dev/null
  lsof -ti:8080 | xargs kill -9 2>/dev/null
  sleep 1
  echo "[FE] 시작 중... (port 8080)"
  cd "$DIR/frontend" && nohup flutter run -d chrome --web-port=8080 > /tmp/flutter-run.log 2>&1 &
  echo "[FE] PID: $!"
}

case "${1:-all}" in
  fe|FE)
    restart_fe
    ;;
  be|BE)
    restart_be
    ;;
  *)
    restart_be
    restart_fe
    ;;
esac

echo ""
echo "완료! 약 15초 후 브라우저에서 http://localhost:8080 확인"
