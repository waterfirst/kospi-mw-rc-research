#!/data/data/com.termux/files/usr/bin/bash
# 노트10을 KOSPI 모니터링 홈서버로 전환 (HOME_SERVER_SETUP.md 의 systemd → Termux cron 대응)
# 사용법: bash kospi_setup.sh
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY=/data/data/com.termux/files/usr/bin/python
WRAP="$REPO/phone_server/run_with_env.sh"
chmod +x "$WRAP"
mkdir -p "$REPO/logs"

echo "== [1/5] 패키지 =="
pkg install -y cronie termux-services python python-pillow >/dev/null
pip install -q requests

echo "== [2/5] .env (텔레그램) =="
if [ ! -f "$REPO/.env" ]; then
  cat > "$REPO/.env" <<'EOF'
TELEGRAM_TOKEN=여기에_봇토큰
TELEGRAM_CHAT_ID=여기에_챗ID
PYTHONUNBUFFERED=1
TZ=Asia/Seoul
EOF
  chmod 600 "$REPO/.env"
  echo "  ✘ $REPO/.env 를 열어 토큰을 채우세요: nano $REPO/.env"
else
  echo "  OK: .env 존재"
fi

echo "== [3/5] cron 등록 (평일 KST) =="
crontab - <<EOF
# KOSPI phone server — 자동 생성 (kospi_setup.sh)
30 7  * * 1-5 $WRAP $PY monitor/overnight_0730_strategy.py --now --telegram >> $REPO/logs/open_0730.log 2>&1
33 7  * * 1-5 $WRAP $PY monitor/forecast_watchdog.py --kind open --label 0730 --telegram >> $REPO/logs/watchdog.log 2>&1
30 12 * * 1-5 $WRAP $PY monitor/kospi_1230_close_forecast.py --telegram >> $REPO/logs/close_1230.log 2>&1
33 12 * * 1-5 $WRAP $PY monitor/forecast_watchdog.py --kind close --label 1230 --telegram >> $REPO/logs/watchdog.log 2>&1
# 출퇴근 날씨 카드 (매일 05:10, 출근 전)
10 5  * * * $WRAP $PY phone_server/weather_card.py --telegram >> $REPO/logs/weather.log 2>&1
# 뉴스 모니터 생존 확인(10분마다, 죽어 있으면 재기동)
*/10 * * * * pgrep -f news_shock_monitor >/dev/null || $WRAP $PY monitor/news_shock_monitor.py --interval 900 --telegram >> $REPO/logs/news.log 2>&1 &
# 대시보드 생존 확인
*/10 * * * * pgrep -f "server.py" >/dev/null || (cd $REPO/phone_server && $PY server.py 8080 >> $REPO/logs/dashboard.log 2>&1 &)
# Drop(기기간 전송, 8090) 생존 확인
*/10 * * * * pgrep -f "drop.py" >/dev/null || (cd $REPO/phone_server && $PY drop.py 8090 >> $REPO/logs/drop.log 2>&1 &)
EOF
crontab -l | head -3

echo "== [4/5] crond 서비스 활성화 =="
sv-enable crond 2>/dev/null || { crond; echo "  crond 직접 기동"; }
termux-wake-lock || true

echo "== [5/5] 텔레그램 발송 테스트 =="
set -a; . "$REPO/.env"; set +a
if [ "$TELEGRAM_TOKEN" != "여기에_봇토큰" ]; then
  curl -s "https://api.telegram.org/bot$TELEGRAM_TOKEN/sendMessage" \
    -d chat_id="$TELEGRAM_CHAT_ID" -d text="📱 노트10 KOSPI 서버 가동 시작" >/dev/null \
    && echo "  OK: 텔레그램 발송 성공" || echo "  ✘ 텔레그램 실패: 토큰/챗ID 확인"
else
  echo "  건너뜀: .env 토큰 미설정"
fi
echo
echo "완료. 로그 확인: tail -f $REPO/logs/*.log  /  등록 확인: crontab -l"
