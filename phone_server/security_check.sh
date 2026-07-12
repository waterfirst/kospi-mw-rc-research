#!/data/data/com.termux/files/usr/bin/bash
# 폰서버 보안 자가점검. 실행: bash phone_server/security_check.sh
PREFIX=${PREFIX:-/data/data/com.termux/files/usr}
ok(){ echo "  ✔ $1"; }
warn(){ echo "  ⚠ $1"; }
bad(){ echo "  ✘ $1"; }
echo "==================== 폰서버 보안 점검 ===================="

echo "[1] SSH 인증 방식"
SC="$PREFIX/etc/ssh/sshd_config"
if grep -qiE '^\s*PasswordAuthentication\s+no' "$SC" 2>/dev/null; then
  ok "비밀번호 로그인 꺼짐(키 전용) — 안전"
else
  bad "비밀번호 로그인 허용됨 → 유출·무차별 대입 위험. 키 전용 권장"
  echo "     해결: echo 'PasswordAuthentication no' >> $SC ; pkill sshd; sshd"
fi
if [ -s ~/.ssh/authorized_keys ]; then ok "authorized_keys 존재($(wc -l <~/.ssh/authorized_keys)개 키)";
else warn "등록된 공개키 없음 — 키 전용 전환 전 반드시 키부터 등록"; fi

echo "[2] 열린 포트 / 바인딩"
LIST=$( (command -v ss >/dev/null && ss -tlnp 2>/dev/null) || (command -v netstat >/dev/null && netstat -tlnp 2>/dev/null) )
if [ -n "$LIST" ]; then
  echo "$LIST" | grep -E ':(8022|8080|8090|8095)' | while read -r l; do
    echo "     $l" | grep -q '0.0.0.0\|\*:\|::' && warn "$(echo "$l"|awk '{print $4}') → 모든 네트워크 노출" \
      || ok "$(echo "$l"|awk '{print $4}')"
  done
else warn "ss/netstat 없음 → pkg install iproute2 net-tools 로 확인 권장"; fi
echo "     참고: 8080(카메라제어)·8090(파일)은 인증이 없으므로 신뢰망에서만 사용"

echo "[3] 무차별 대입 흔적 (sshd 로그)"
LOGF=$(ls -1 "$PREFIX/var/log/sv/sshd"/current 2>/dev/null | head -1)
if [ -n "$LOGF" ]; then
  N=$(grep -c -i 'failed\|invalid' "$LOGF" 2>/dev/null || echo 0)
  [ "$N" -gt 20 ] && warn "실패 로그인 $N건 — 공격 시도 가능" || ok "실패 로그인 $N건(정상 범위)"
else warn "sshd 로그 없음(서비스 미사용 또는 위치 다름)"; fi

echo "[4] 패키지 최신화"
warn "주기적으로: pkg update && pkg upgrade -y (보안 패치)"

echo "[5] 네트워크 노출"
ok "포트포워딩 안 했으면 외부 노출은 Tailscale(암호화)로만 — 양호"
warn "집/카페 공용 WiFi에선 8080·8090이 같은 망 사용자에게 보임. 공용WiFi에선 끄기 권장:"
echo "     pkill -f 'server.py 8080'; pkill -f 'drop.py 8090'"
echo "========================================================="
echo "요약: ① 비번→키전용 ② 대시보드/Drop 토큰인증(또는 신뢰망 한정)"
echo "      ③ Tailscale 계정 2FA ④ 정기 pkg upgrade"
