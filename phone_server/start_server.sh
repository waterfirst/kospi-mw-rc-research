#!/data/data/com.termux/files/usr/bin/bash
# 대시보드 서버를 SSH 세션과 분리(detach)해 실행.
# 노트북/SSH를 꺼도 폰에서 계속 살아있음.
# 사용: bash start_server.sh [포트]   (기본 8080)
PORT="${1:-8080}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY=/data/data/com.termux/files/usr/bin/python
mkdir -p "$REPO/logs"

# 1) Termux를 화면 꺼져도 살려둠 (이게 없으면 화면 끄면 다 죽음)
termux-wake-lock 2>/dev/null || true

# 2) 기존 프로세스 정리 (포트 중복 방지)
pkill -f "server.py $PORT" 2>/dev/null || true
sleep 1

# 3) SSH 세션과 완전 분리해 기동 (setsid + 표준입출력 차단)
cd "$REPO/phone_server"
setsid $PY server.py "$PORT" </dev/null >>"$REPO/logs/dashboard.log" 2>&1 &

sleep 2
if pgrep -f "server.py $PORT" >/dev/null; then
  IP=$(ifconfig 2>/dev/null | grep -oE 'inet 192\.[0-9.]+' | head -1 | cut -d' ' -f2)
  echo "OK: http://${IP:-<폰IP>}:$PORT  (노트북 꺼도 유지됨)"
  echo "이제 SSH 창을 닫아도 됩니다. 종료하려면: pkill -f server.py"
else
  echo "실패. 로그 확인: tail -n 20 $REPO/logs/dashboard.log"
fi
