# 폰서버 배포 가이드 (GitHub → 폰 자동 동기화)

내가(Claude) GitHub에 push하면 폰이 스스로 당겨와 반영하는 구조. 네트워크 직접 연결 불필요.

```
[Claude가 GitHub에 push]  →  [폰 sync.sh (5분 cron)]  →  [pageserve가 서빙]
```

## 핵심 원칙 (트러블슈팅에서 나온 규칙)

| 상황 | 처리 | 자동? |
|------|------|-------|
| 콘텐츠만 변경(HTML·이미지·음원·JS) | pageserve가 pages/ 를 라이브 서빙 → 재시작 불필요 | ✅ sync.sh |
| **서버 코드(*.py) 변경** | 실행 중인 옛 프로세스는 옛 코드로 계속 동작 → **재시작 필요** | ✅ sync.sh가 diff 감지해 재시작 |
| 폰 브랜치 divergent | `git reset --hard origin/BR` 로 강제 일치(폰은 배포전용) | ✅ sync.sh |
| 서버 죽음 | 생존 확인 후 기동 | ✅ sync.sh + cron |

> 과거 반복된 실수: pageserve.py 코드를 바꿨는데 폰의 옛 프로세스가 안 죽어서
> 404/옛 화면이 뜸. → sync.sh가 이제 `git diff`로 *.py 변경을 감지해 자동 재시작.

## 배포 방법 3가지

### A. GitHub 경유 (메인 · 네트워크 무관)
```
Claude가 push  →  폰 cron(5분) 또는 수동: bash phone_server/sync.sh
```
- 콘텐츠/코드 어느 것이 바뀌든 sync.sh가 알아서 pull + 필요한 재시작.

### B. Tailscale 직접 (우분투 → 폰, 즉시)
폰 Tailscale 앱 배터리 "제한 없음" 필요(inbound 유지). 그다음 우분투에서:
```bash
ssh -i ~/.ssh/note10 -p 8022 u0_a231@100.71.229.101 \
  'cd ~/kospi-mw-rc-research && bash phone_server/sync.sh'
```

### C. 완전 수동 (문제 생겼을 때 복구용) — 폰에서
```bash
cd ~/kospi-mw-rc-research
git fetch origin && git reset --hard origin/claude/smartphone-server-dashboard-sv4l50
bash phone_server/sync.sh
```

## 접속 URL

| | 집 WiFi | 집 밖(Tailscale) |
|---|---|---|
| 페이지 호스팅 | http://192.168.0.43:8095/ | http://100.71.229.101:8095/ |
| 스페인 여행 | …:8095/spain-trip.html | …:8095/spain-trip.html |
| 대시보드 | http://192.168.0.43:8080 | http://100.71.229.101:8080 |
| Drop | http://192.168.0.43:8090 | http://100.71.229.101:8090 |

## 접속·공유 방법 3가지 (용도별)

| 용도 | 방법 | 링크 |
|------|------|------|
| 🌍 **남한테 공유(카톡 등)** | GitHub Pages (공개 HTTPS) | `https://waterfirst.github.io/kospi-mw-rc-research/spain-trip.html` |
| 📱 **밖에서 내 기기** | Tailscale 앱(같은 계정·Connect) | `http://100.71.229.101:8095/spain-trip.html` |
| 🏠 **집에서** | 같은 WiFi | `http://192.168.0.43:8095/spain-trip.html` |

- **폰서버(192.168/100.x)는 사설망 전용** — Tailscale 없는 남의 폰/LTE에선 안 열림. 공유는 GitHub Pages.
- **다른 기기를 Tailscale로 추가**: 그 기기에 Tailscale 앱 설치 → **노트10과 같은 계정** 로그인 → Connect → 기기목록에 `note10` 보이면 100.x URL 접속 가능. (MagicDNS 켜면 `http://note10:8095/…`)
- 폰에선 CLI(Funnel/Serve)가 seccomp로 안 돼서, 공개 노출은 GitHub Pages가 정답.

## GitHub Pages (공개 링크) 관리

- 최초 1회 활성화: repo **Settings → Pages → Source: Deploy from a branch → `gh-pages` / (root) → Save**
- 공개 URL: `https://waterfirst.github.io/kospi-mw-rc-research/spain-trip.html`
- 콘텐츠 갱신(재배포): `bash phone_server/publish_pages.sh` → `gh-pages` 브랜치에 pages/ 를 다시 올림
- private repo면 Pages는 GitHub Pro 필요(또는 repo public 전환)

## 점검 원라이너 (폰)
```bash
git rev-parse --short HEAD                              # 현재 커밋
pgrep -af "pageserve.py|server.py|drop.py"             # 서버 생존
tail -n 5 logs/sync.log                                 # 최근 동기화
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8095/spain-trip.html
```

## 자주 난 문제 → 원인 → 해결

- **404 / 옛 화면** → pageserve가 옛 폴더·옛 코드 → `sync.sh`가 재시작(이제 자동). 수동은 `pkill -f pageserve.py` 후 재기동.
- **"No such file or directory (sync.sh)"** → 폰이 그 커밋을 안 받음 → 위 C(수동 reset --hard).
- **ssh 명령이 폰에서 비번 물음** → 그 명령은 우분투용(폰이 아님). 폰↔폰 ssh 아님.
- **Tailscale TCP timeout** → 폰 Tailscale 앱 배터리 "제한 없음" 안 됨 → 설정 후 재시도.
