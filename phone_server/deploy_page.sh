#!/usr/bin/env bash
# 우분투 서버 등에서 실행 → 폰서버(노트10)에 HTML 페이지를 배포.
# Claude Code가 tailnet 안 우분투에서 이 스크립트로 폰에 웹페이지를 띄운다.
#
# 사용:  bash deploy_page.sh <파일.html> [폰IP]
# 예:    bash deploy_page.sh my_trip.html
set -e
FILE="$1"
PHONE="${2:-100.71.229.101}"
PORT_SSH=8022
USER=u0_a231
KEY="$HOME/.ssh/note10"

[ -f "$FILE" ] || { echo "파일 없음: $FILE"; exit 1; }
SSH="ssh -i $KEY -p $PORT_SSH $USER@$PHONE"
NAME=$(basename "$FILE")

echo "[1/3] ~/pages 준비"
$SSH 'mkdir -p ~/pages'

echo "[2/3] 업로드: $NAME"
scp -i "$KEY" -P $PORT_SSH "$FILE" "$USER@$PHONE:~/pages/$NAME"

echo "[3/3] pageserve(8095) 실행 확인"
$SSH 'pgrep -f pageserve.py >/dev/null || (termux-wake-lock; cd ~/kospi-mw-rc-research/phone_server && setsid python pageserve.py 8095 </dev/null >>~/kospi-mw-rc-research/logs/pageserve.log 2>&1 &)'
sleep 1
echo
echo "완료 →  http://$PHONE:8095/$NAME"
echo "        (집 WiFi면 http://192.168.0.43:8095/$NAME)"
