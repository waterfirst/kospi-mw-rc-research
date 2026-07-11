#!/data/data/com.termux/files/usr/bin/bash
# Termux(root 없음)에서 Tailscale 설치·기동 — userspace 모드
# pkg에 tailscale이 없으므로 공식 정적 바이너리(arm64)를 직접 설치.
# 사용: bash tailscale_setup.sh   (그다음 안내되는 URL로 인증)
set -e
PREFIX=${PREFIX:-/data/data/com.termux/files/usr}

echo "== [1/4] 설치 =="
if command -v tailscale >/dev/null 2>&1; then
  echo "  이미 설치됨: $(tailscale version 2>/dev/null | head -1)"
elif pkg install -y tailscale 2>/dev/null && command -v tailscale >/dev/null; then
  echo "  pkg 설치 성공"
else
  echo "  pkg에 없음 → 공식 정적 바이너리 다운로드"
  ARCH=arm64
  case "$(uname -m)" in armv7l|arm) ARCH=arm;; x86_64) ARCH=amd64;; esac
  VER=$(curl -s 'https://pkgs.tailscale.com/stable/?mode=json' \
        | python -c "import sys,json;print(json.load(sys.stdin)['Version'])")
  echo "  버전 $VER ($ARCH) 받는 중..."
  cd ~
  curl -fL -o ts.tgz "https://pkgs.tailscale.com/stable/tailscale_${VER}_${ARCH}.tgz"
  tar xzf ts.tgz
  install -m755 "tailscale_${VER}_${ARCH}/tailscale"  "$PREFIX/bin/tailscale"
  install -m755 "tailscale_${VER}_${ARCH}/tailscaled" "$PREFIX/bin/tailscaled"
  rm -rf ts.tgz "tailscale_${VER}_${ARCH}"
  echo "  설치 완료: $(tailscale version | head -1)"
fi

echo "== [2/4] 데몬 기동 (SSH 끊겨도 유지: setsid) =="
mkdir -p ~/.tailscale
pkill -f tailscaled 2>/dev/null || true
sleep 1
setsid tailscaled --tun=userspace-networking \
  --state=$HOME/.tailscale/tailscaled.state \
  </dev/null >~/.tailscale/tailscaled.log 2>&1 &
sleep 3
if pgrep -f tailscaled >/dev/null; then
  echo "  OK: tailscaled 실행 중"
else
  echo "  ✘ 데몬 실패. 로그: cat ~/.tailscale/tailscaled.log"; exit 1
fi

echo "== [3/4] 로그인 =="
echo "  아래에 인증 URL이 나오면 폰 브라우저에서 열어 로그인/승인 하세요."
tailscale up --hostname=note10

echo "== [4/4] 부여된 주소 =="
IP=$(tailscale ip -4 2>/dev/null || echo "?")
echo "  Tailscale IP: $IP"
echo
echo "이제 집 밖에서도 접속 가능:"
echo "  ssh u0_a231@$IP -p 8022"
echo "  http://$IP:8080   (대시보드)"
echo
echo "재부팅에도 유지하려면 Termux:Boot 에 등록:"
echo "  mkdir -p ~/.termux/boot"
echo "  cp ~/kospi-mw-rc-research/phone_server/tailscale_boot.sh ~/.termux/boot/"
