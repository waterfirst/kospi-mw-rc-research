#!/data/data/com.termux/files/usr/bin/bash
# 갤럭시 노트10 Termux 폰서버 설치 스크립트
# 사용법: bash install.sh
set -e
echo "== [1/4] 패키지 설치 =="
pkg update -y
pkg install -y python termux-api termux-services openssh

echo "== [2/4] Termux:API 앱 확인 =="
if timeout 8 termux-battery-status >/dev/null 2>&1; then
  echo "  OK: Termux:API 응답함"
else
  echo "  ✘ Termux:API 앱이 없거나 응답 없음."
  echo "    → F-Droid(https://f-droid.org)에서 'Termux:API' 앱 설치."
  echo "    → 중요: Termux 본체와 같은 곳(F-Droid)에서 받아야 함. Play스토어 혼용 시 서명 불일치로 통신 불가."
fi

echo "== [3/4] 백그라운드 종료 방지 =="
termux-wake-lock || true
echo "  설정 > 앱 > Termux > 배터리 > '제한 없음' 으로 변경 권장"
echo "  Android 12+ 이면 PC에서:"
echo "    adb shell settings put global settings_enable_monitor_phantom_procs false"

echo "== [4/4] 서버 시작 =="
IP=$(ifconfig 2>/dev/null | grep -oE 'inet 192\.[0-9.]+' | head -1 | cut -d' ' -f2)
echo "  대시보드 주소: http://${IP:-<폰IP>}:8080"
cd "$(dirname "$0")"
exec python server.py 8080
