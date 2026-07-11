#!/data/data/com.termux/files/usr/bin/bash
# .env 로드 후 명령 실행 (cron 용 래퍼)
cd "$(dirname "$0")/.."
set -a; [ -f .env ] && . ./.env; set +a
exec "$@"
