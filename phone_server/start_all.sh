#!/data/data/com.termux/files/usr/bin/bash
# 모든 폰서버 서비스를 SSH 세션과 분리(detach)해 기동.
# PC/SSH를 꺼도, 화면을 꺼도 유지됨. Termux:Boot 재부팅 자동시작에도 사용.
# 사용: bash start_all.sh
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY=/data/data/com.termux/files/usr/bin/python
mkdir -p "$REPO/logs"

# 1) Termux를 화면 꺼져도 살려둠 (핵심)
termux-wake-lock 2>/dev/null || true

# 2) 세션에 매달린 기존 프로세스 정리 후 detach 재기동
launch() {  # $1=이름/패턴  $2=명령
  pkill -f "$1" 2>/dev/null; sleep 1
  cd "$REPO/phone_server"
  setsid $PY $2 </dev/null >>"$REPO/logs/${3}.log" 2>&1 &
}
launch "server.py"    "server.py 8080"   "dashboard"
launch "drop.py"      "drop.py 8090"     "drop"
launch "pageserve.py" "pageserve.py 8095" "pageserve"

# 3) crond(자동 재기동 안전망) 살아있는지 확인
pgrep -x crond >/dev/null || { crond 2>/dev/null && echo "crond 기동"; }

sleep 2
echo "== 상태 =="
for p in "server.py" "drop.py" "pageserve.py" "crond"; do
  if pgrep -f "$p" >/dev/null; then echo "  ✔ $p"; else echo "  ✘ $p (미실행)"; fi
done
IP=$(ifconfig 2>/dev/null | grep -oE 'inet 192\.[0-9.]+' | head -1 | cut -d' ' -f2)
echo
echo "대시보드: http://${IP:-<폰IP>}:8080   Drop: http://${IP:-<폰IP>}:8090"
echo "이제 SSH 창을 닫고 PC를 꺼도 유지됩니다."
