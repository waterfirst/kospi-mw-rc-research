#!/data/data/com.termux/files/usr/bin/bash
# 대시보드(8080)·Drop(8090)에 접근 토큰 설정 → 즐겨찾기 URL 발급.
# 편의: ?k=토큰 으로 한 번 접속하면 쿠키 저장되어 이후 무프롬프트.
# 사용:  bash phone_server/set_token.sh [원하는토큰]   (생략 시 랜덤 생성)
DIR="$(cd "$(dirname "$0")" && pwd)"
TOK="${1:-$(head -c 18 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 20)}"
echo "$TOK" > "$HOME/.phone_token"
chmod 600 "$HOME/.phone_token"
IP=$(ifconfig 2>/dev/null | grep -oE 'inet 192\.[0-9.]+' | head -1 | cut -d' ' -f2)
TS=100.71.229.101

echo "토큰 설정 완료 → 서버 재시작"
bash "$DIR/start_all.sh" >/dev/null 2>&1
echo
echo "이 주소를 즐겨찾기/홈화면에 추가하면 이후 한 번 탭으로 열립니다:"
echo "  [집]  대시보드  http://${IP:-192.168.0.43}:8080/?k=$TOK"
echo "  [집]  Drop      http://${IP:-192.168.0.43}:8090/?k=$TOK"
echo "  [밖]  대시보드  http://$TS:8080/?k=$TOK   (Tailscale)"
echo
echo "해제하려면:  rm ~/.phone_token && bash phone_server/start_all.sh"
echo "※ 페이지 호스팅(8095)은 토큰 없이 공개 유지(여행 페이지 등)."
