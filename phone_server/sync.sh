#!/data/data/com.termux/files/usr/bin/bash
# 폰이 GitHub에서 최신 페이지·코드를 당겨오고 서버들을 유지.
# cron이 5분마다 실행 → 내가 push한 페이지가 폰에 자동 반영됨.
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY=/data/data/com.termux/files/usr/bin/python
cd "$REPO" || exit 0

BR=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo master)
git fetch -q origin "$BR" 2>/dev/null && git reset -q --hard "origin/$BR" 2>/dev/null

# pageserve 살아있게 유지
pgrep -f pageserve.py >/dev/null || {
  termux-wake-lock 2>/dev/null || true
  cd "$REPO/phone_server"
  setsid $PY pageserve.py 8095 </dev/null >>"$REPO/logs/pageserve.log" 2>&1 &
}
