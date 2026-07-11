# 갤럭시 노트10 폰서버 대시보드 (Termux)

스마트폰 센서 실시간 모니터링 + 카메라 원격 촬영 + 손전등/진동 제어 + 자가진단.
외부 라이브러리 0개(파이썬 표준 라이브러리만) — HTML 호스팅만 되던 환경에서 그대로 동작.

## 빠른 시작 (폰의 Termux에서)

```bash
pkg install -y git
git clone https://github.com/waterfirst/kospi-mw-rc-research.git
cd kospi-mw-rc-research/phone_server
bash install.sh          # 설치 + 진단 + 서버 시작
```

이후엔 `python server.py` 만으로 재시작. 브라우저에서 `http://192.168.0.43:8080` 접속.

## 계속 에러가 났던 원인 TOP 7 과 대책

| # | 증상 | 원인 | 대책 |
|---|------|------|------|
| 1 | `termux-sensor`, `termux-camera-photo` 가 **무한 대기** 후 실패 | **Termux:API "앱" 미설치**. `pkg install termux-api`(CLI)와 Termux:API 앱(APK)은 별개 | F-Droid에서 Termux:API 앱 설치. Termux 본체와 **같은 출처**여야 함(Play/F-Droid 혼용 → 서명 불일치로 IPC 차단) |
| 2 | 카메라만 실패 | Termux:API 앱에 카메라 권한 없음 | 설정→앱→Termux:API→권한→카메라 허용 |
| 3 | 서버가 몇 분 뒤 **저절로 죽음** | Android 12+ phantom process killer / 배터리 최적화 | ① `termux-wake-lock` 실행 ② Termux 배터리 "제한 없음" ③ PC에서 `adb shell settings put global settings_enable_monitor_phantom_procs false` |
| 4 | 브라우저에서 센서 API(JS `Accelerometer` 등) 오류 | 브라우저 센서 API는 **HTTPS 필수** — http LAN 페이지에선 항상 실패 | 브라우저 JS로 읽지 말 것. 이 서버처럼 **서버측 termux-sensor** 로 읽어 JSON 제공 (본 구조) |
| 5 | `Address already in use` | 죽은 프로세스가 포트 점유 | `pkill -f server.py` 후 재시작, 또는 `python server.py 8081` |
| 6 | 다른 기기에서 접속 불가 | `localhost` 로 안내했거나 AP isolation | 폰 IP(`ifconfig`)로 접속. 공유기 "AP 격리/게스트망" 해제. 셀룰러가 아닌 같은 Wi-Fi 확인 |
| 7 | 센서 이름 불일치로 빈 데이터 | 기기마다 센서 이름 다름 (`LSM6DSO Accelerometer` 등) | 서버가 시작 시 `termux-sensor -l` 로 실제 이름을 자동 해석 (하드코딩 금지) |

※ 외부(LTE 등)에서 접속하려면 포트포워딩 대신 **Tailscale**(`pkg install tailscale`) 권장.

## 구성

| 파일 | 역할 |
|------|------|
| `server.py` | HTTP 서버 + termux-api 래퍼(타임아웃/원인 힌트 내장) |
| `dashboard.html` | 다크테마 대시보드 (KPI·실시간 차트·카메라·자가진단) |
| `install.sh` | 패키지 설치 + 환경 점검 + 서버 기동 |

## API

| 엔드포인트 | 기능 |
|---|---|
| `GET /api/status` | 배터리 + 메모리/부하/가동시간 |
| `GET /api/sensors` | 가속도·자이로·조도·근접 등 1샷 |
| `GET /api/photo?cam=0` | 사진 촬영(0=후면, 1=전면), JPEG 반환 |
| `GET /api/torch?state=on\|off` | 손전등 |
| `GET /api/vibrate` | 진동 |
| `GET /api/doctor` | 설치/권한 자가진단 |

## 부팅 시 자동 시작 (선택)

Termux:Boot 앱(F-Droid) 설치 후:

```bash
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/start-server.sh <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
cd ~/kospi-mw-rc-research/phone_server && python server.py 8080
EOF
chmod +x ~/.termux/boot/start-server.sh
```
