#!/data/data/com.termux/files/usr/bin/bash
# Tailscale on 노트10.
#
# ⚠️ 중요: Termux CLI(정적 바이너리)는 이 폰에서 동작하지 않음.
#   안드로이드 seccomp가 faccessat2 syscall을 차단 → 공식 정적 바이너리가
#   'SIGSYS: bad system call'로 즉사함. (Android용 미패치)
#   → 반드시 Play스토어 'Tailscale' 앱을 사용할 것. 아래는 안내만 출력.
set -e
cat <<'EOF'
================= Tailscale 설치 안내 (앱 방식) =================

CLI 정적 바이너리는 Android seccomp(faccessat2 차단)로 SIGSYS 크래시가 남.
네이티브 앱을 쓰면 이 문제가 전혀 없고 공식 지원됨.

1) Play스토어에서 'Tailscale' 앱 설치 → 로그인(구글 계정 가능)
2) 앱에서 Connect 토글 ON → 첫 화면에 100.x.y.z 주소 표시됨
3) 접속할 노트북/폰에도 같은 계정으로 Tailscale 설치
4) 이제 집 밖 어디서든:
     ssh u0_a231@100.x.y.z -p 8022      # 폰 SSH
     http://100.x.y.z:8080              # 대시보드
5) (선택) 앱 설정 > MagicDNS 켜면 IP 대신 'note10' 이름으로 접속

※ 앱이 VPN을 유지하므로 Termux 데몬 불필요. 배터리 최적화에서 Tailscale도 '제한 없음' 권장.
================================================================
EOF
