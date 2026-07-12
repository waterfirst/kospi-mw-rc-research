# 폰서버 · 우분투 서버 보안 가이드

셀프호스팅 3계층(폰 / 우분투 / GitHub)의 해킹 위험 점검과 대응.

## 위험 요약

| # | 위험 | 심각도 | 조치 |
|---|------|--------|------|
| 1 | 폰 SSH 비밀번호 인증 (비번이 노출됐다면) | 🔴 높음 | 비번 교체 + **키 전용** 전환 |
| 2 | 대시보드(8080)·Drop(8090) 인증 없음, 0.0.0.0 바인딩 | 🔴 높음 | 신뢰망 한정 or 토큰 인증 추가 |
| 3 | Tailscale 계정(구글) 탈취 | 🟡 중간 | 계정 **2FA** 필수 |
| 4 | 공개 포트포워딩 | 🟢 없음 | 외부는 Tailscale로만 (양호) |
| 5 | GitHub 비밀정보 커밋 | 🟢 확인함 | .env·키 gitignore, 값 커밋 없음 |

## 즉시 할 일 (우선순위)

### ① 폰 SSH: 비번 교체 → 키 전용
우분투에 이미 키(`~/.ssh/note10`)가 있으니 안전하게 전환 가능.
```bash
# 폰(Termux)
passwd                                   # 비밀번호 변경
# 키 로그인이 되는지 먼저 확인(우분투에서): ssh -i ~/.ssh/note10 -p 8022 u0_a231@100.71.229.101 'echo ok'
echo 'PasswordAuthentication no' >> $PREFIX/etc/ssh/sshd_config
echo 'ChallengeResponseAuthentication no' >> $PREFIX/etc/ssh/sshd_config
pkill sshd; sshd                         # 재시작
```
> ⚠️ 키 로그인 확인 전에 password 끄지 말 것(잠길 수 있음).

### ② 대시보드/Drop 노출 축소
- 카메라 제어(8080)·파일(8090)은 **인증이 없다.** 같은 WiFi/tailnet 사용자에게 그대로 노출.
- **집 개인 WiFi**면 위험 낮음. **카페·공용 WiFi에선 반드시 끄기**:
  ```bash
  pkill -f 'server.py 8080'; pkill -f 'drop.py 8090'   # 페이지(8095)만 남김
  ```
- 근본 해결: 토큰 인증 추가(요청 시 구현) 또는 localhost 바인딩 + SSH 터널.

### ③ Tailscale 계정 보안
- 구글 계정 **2단계 인증** 켜기 (계정 뚫리면 tailnet 전체 노출).
- 관리 콘솔 → Machines 주기적 확인, 모르는 기기 삭제.
- 노드 공유(Share)는 신중히 — 공유하면 그 기기 전체 접근 허용됨.

## 우분투 서버 점검 (노트북에서 실행)
```bash
sudo ss -tlnp | grep LISTEN                 # 열린 포트 — 필요한 것만
grep -E '^PasswordAuthentication|^PermitRootLogin' /etc/ssh/sshd_config
sudo ufw status                             # 방화벽 (없으면 아래)
```
권장 하드닝:
```bash
sudo apt update && sudo apt install -y ufw fail2ban unattended-upgrades
sudo ufw default deny incoming; sudo ufw allow from 100.64.0.0/10  # tailnet만 허용(예)
sudo ufw enable
sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh
sudo systemctl enable --now fail2ban        # 무차별 대입 차단
sudo dpkg-reconfigure -plow unattended-upgrades   # 보안 자동 업데이트
```
- SSH 키 로그인만, root 로그인 금지, fail2ban, 자동 보안업데이트, 방화벽으로 tailnet만.

## GitHub
- ✅ `.env`·키파일 gitignore 확인됨, 실제 비밀값 커밋 없음.
- Pages는 공개 — pages/ 에 개인정보·좌표·비밀 넣지 말 것.
- 토큰 쓸 일 있으면 fine-grained PAT(이 repo만), 만료일 설정.

## 정기 점검
```bash
bash phone_server/security_check.sh    # 폰 자가점검
```
- 월 1회: pkg/apt upgrade, Tailscale 기기목록 확인, sshd 실패로그 확인.

## 핵심 원칙
- **공개 노출은 GitHub Pages(정적)만.** 폰/우분투 서버는 **Tailscale 뒤**에 두고 절대 포트포워딩하지 않기.
- 인증 없는 서비스(카메라·파일)는 **신뢰하는 개인망**에서만.
- SSH는 **키 전용**, 비번 로그인 끄기.
