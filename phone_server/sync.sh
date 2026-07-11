#!/data/data/com.termux/files/usr/bin/bash
# 폰이 GitHub 최신을 당겨오고 서버를 유지 — 트러블슈팅 자동화 포함.
# cron 5분마다 실행. 내가 push하면 폰에 자동 반영.
#
# 자동 처리하는 것:
#  1) divergent 브랜치 → reset --hard 로 원격에 강제 일치 (폰은 배포전용)
#  2) *.py(pageserve/server/drop) 코드가 바뀌면 → 해당 서버 재시작
#     (콘텐츠 HTML/이미지/음원만 바뀌면 재시작 안 함 — pageserve가 dir 라이브 서빙)
#  3) 서버가 죽어 있으면 → 기동
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY=/data/data/com.termux/files/usr/bin/python
cd "$REPO" || exit 0
mkdir -p "$REPO/logs"
termux-wake-lock 2>/dev/null || true

BR=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo master)
OLD=$(git rev-parse HEAD 2>/dev/null || echo none)
git fetch -q origin "$BR" 2>/dev/null
git reset -q --hard "origin/$BR" 2>/dev/null   # divergent 자동 해소
NEW=$(git rev-parse HEAD 2>/dev/null || echo none)

# 코드가 바뀐 서버는 죽여서 아래 ensure가 새로 띄우게 함
if [ "$OLD" != "$NEW" ]; then
  CHG=$(git diff --name-only "$OLD" "$NEW" 2>/dev/null)
  echo "$CHG" | grep -q 'phone_server/pageserve.py' && pkill -f pageserve.py 2>/dev/null
  echo "$CHG" | grep -q 'phone_server/server.py'    && pkill -f "server.py"   2>/dev/null
  echo "$CHG" | grep -q 'phone_server/drop.py'      && pkill -f drop.py       2>/dev/null
  [ -n "$CHG" ] && echo "$(date '+%F %T') synced $OLD..$NEW" >> "$REPO/logs/sync.log"
fi
sleep 1

ensure(){  # $1=패턴  $2=스크립트+포트
  pgrep -f "$1" >/dev/null && return
  cd "$REPO/phone_server"
  setsid $PY $2 </dev/null >>"$REPO/logs/${1%%.*}.log" 2>&1 &
}
ensure pageserve.py "pageserve.py 8095"
ensure server.py    "server.py 8080"
ensure drop.py      "drop.py 8090"
