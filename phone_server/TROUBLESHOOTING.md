# 노트10 폰서버 운영 일지 · 트러블슈팅

갤럭시 노트10(Termux, Android 12, `u0_a231@192.168.0.43:8022`)을 홈서버로 구축하며
겪은 문제와 해결을 기록. 같은 삽질 반복 금지.

## 구축된 것 (요약)

| 기능 | 파일 | 상태 |
|------|------|------|
| 센서/카메라/토치 대시보드 (8080) | `server.py` + `dashboard.html` | ✅ cron이 24h 유지 |
| KOSPI 예측·watchdog·뉴스 모니터 | `kospi_setup.sh` → crontab | ✅ 평일 자동 |
| 출퇴근 날씨 카드 (텔레그램) | `weather_card.py` | ✅ 매일 05:10 |
| phantom killer / Tailscale 안내 | `phone_extras.sh` | 가이드 제공 |

## 시행착오 로그

| # | 증상 | 원인 | 해결 |
|---|------|------|------|
| 1 | 대시보드 센서/카메라가 계속 에러 | `pkg install termux-api`(CLI)만 하고 **Termux:API 앱(APK) 미설치** → 명령이 무한 대기 | F-Droid에서 Termux:API 앱 설치(Termux 본체와 **같은 출처**여야 서명 일치) |
| 2 | 브라우저 JS 센서 API 실패 | http LAN 페이지에선 브라우저 센서 API가 **HTTPS 필수** 제약으로 항상 실패 | 서버측 `termux-sensor`로 읽어 JSON 제공(현 구조) |
| 3 | `pip install adb` 빌드 실패 | 이름만 같은 구식 파이썬 패키지, Python 3.14에서 M2Crypto 컴파일 깨짐 | adb는 `pkg install android-tools`. phantom killer는 PC USB `adb` 권장 |
| 4 | 무선 디버깅 `adb pair` 실패 반복 | 페어링 코드/포트가 휘발성·즉시 만료, 자리표시자(`<포트>`)를 숫자로 안 바꿈 | PC+USB 방식이 확실. 안 되면 cron 자동재기동으로 대체(최대 10분 공백) |
| 5 | 날씨 카드 이모지가 □로 깨짐 | NanumGothic 등 폰트에 컬러 이모지 글리프 없음 | 날씨 아이콘을 **PIL 벡터로 직접 그림**(폰트 무관) |
| 6 | "텔레그램 안 옴" | `git pull` 미완료로 옛 `kospi_setup.sh` 실행(날씨 cron 없음). 성공한 메시지는 `[5/5]` 가동테스트였음 | `git pull` 후 `weather_card.py --telegram` 직접 실행으로 확인 |
| 7 | URL에서 카메라 촬영 안 됨 | 카메라는 정상(`termux-camera-photo` CLI로 1.3MB 촬영 성공). **`server.py`가 죽어 있었고**, `~/site/app.py`(옛 앱)가 8080 점유 의심 | `pkill -f app.py` → `server.py 8080` 재기동. cron이 이후 유지 |
| 8 | 노트북(SSH) 끄면 8080 대시보드가 죽음 | 서버를 SSH 세션 안에서 `&`로 띄워서, SSH 끊기면 SIGHUP으로 자식 프로세스 사망. 화면 꺼지면 wake-lock 없이 Termux 자체가 종료 | **`start_server.sh`**: `termux-wake-lock` + `setsid`로 세션 분리 기동. Termux:Boot로 재부팅 생존 |
| 9 | Tailscale CLI가 `SIGSYS: bad system call`로 즉사 | `pkg`에 tailscale 없어 공식 정적 바이너리 받았으나, **안드로이드 seccomp가 `faccessat2`(0x1b7) syscall 차단** → Android 미패치 Go 바이너리가 crash. root 없이는 회피 불가 | **CLI 포기. Play스토어 Tailscale 앱 사용**(네이티브라 seccomp 무관, 공식 지원). SSH(8022)·대시보드(8080)는 앱이 주는 100.x IP로 동일하게 접속됨 |
| 10 | 우분투→폰 Tailscale ping은 되는데 SSH/HTTP는 timeout | Tailscale IP ping은 tailscaled 자체 응답(서비스 접속 보장 아님). 앱이 배터리 절전으로 inbound 안 넘김 | 폰 **설정→앱→Tailscale→배터리→제한 없음**. 그 후 inbound TCP 정상 |
| 11 | 페이지 push했는데 폰에 404/옛 화면 | pageserve.py 코드를 바꿔도 **실행 중 옛 프로세스는 옛 코드**로 서빙(옛 폴더 등). 콘텐츠만 바뀌면 문제없지만 코드 변경 시 재시작 필요 | `sync.sh`가 `git diff`로 *.py 변경 감지해 **자동 재시작**하도록 개선. 수동은 `pkill -f pageserve.py` 후 재기동 |
| 12 | `phone_server/sync.sh: No such file` | 폰 repo가 그 커밋을 안 받음(behind) | 수동 복구: `git fetch && git reset --hard origin/<branch>` 후 재시도 |

## 핵심 교훈

- **CLI로 되는데 대시보드에서 안 되면 = 서버가 죽은 것.** 먼저 `pgrep -af server.py`(한 줄 나와야 정상).
- **포트 8080은 하나만.** 옛 `~/site/app.py`와 `server.py`가 동시에 8080을 잡으면 나중 것이 죽음. `pgrep -af python`으로 확인.
- **termux-camera-photo는 카메라를 독점.** 폰 카메라 앱/영상통화가 떠 있으면 실패. `pkill -f termux-camera`로 정리.
- **Termux:API는 "앱"과 "CLI"가 별개.** 둘 다 필요, 같은 출처(F-Droid).

## 상태 점검 원라이너

```bash
pgrep -af server.py                 # 대시보드 (1줄=정상)
pgrep -af news_shock_monitor        # 뉴스 모니터
crontab -l | grep -c '^[0-9*]'      # 등록된 cron 수
tail -n 5 ~/kospi-mw-rc-research/logs/weather.log   # 날씨 카드 최근 로그
curl -s localhost:8080/api/doctor | python -m json.tool  # 자가진단
```

## 남은 TODO

- [ ] phantom killer 비활성화(PC USB) — 장시간 안정성 완성
- [ ] Tailscale 앱 설치 — 외부 접근 + 다음 세션 Claude 직접 SSH
- [ ] (선택) 옛 `~/site/app.py` 기능을 `server.py`로 통합
