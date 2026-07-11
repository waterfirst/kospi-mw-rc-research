#!/data/data/com.termux/files/usr/bin/bash
# Termux:Boot 용 — 재부팅 시 Tailscale 데몬 자동 기동
termux-wake-lock
pgrep -f tailscaled >/dev/null || \
  setsid tailscaled --tun=userspace-networking \
    --state=$HOME/.tailscale/tailscaled.state \
    </dev/null >~/.tailscale/tailscaled.log 2>&1 &
