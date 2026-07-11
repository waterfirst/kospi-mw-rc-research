#!/data/data/com.termux/files/usr/bin/bash
# 노트10 서버 안정화 + 외부 접근 설정 도우미
#   1) phantom process killer 비활성화 (장시간 서버가 죽는 것 방지)
#   2) Tailscale 안내 (외부에서 SSH/대시보드 접근)
# 사용: bash phone_extras.sh
set -e

echo "=================================================="
echo " 1. Phantom Process Killer 비활성화 (Android 12+)"
echo "=================================================="
CUR=$(settings get global settings_enable_monitor_phantom_procs 2>/dev/null || echo "확인불가(adb 필요)")
echo "현재 값: ${CUR}  (false 면 이미 완료)"
cat <<'EOF'

이 설정은 adb 권한이 필요합니다. 셋 중 하나를 선택:

[방법 A] PC + USB 케이블 (가장 확실, 권장)
  1) 폰: 설정 > 휴대전화 정보 > 소프트웨어 정보 > 빌드번호 7회 탭 (개발자 옵션 켜기)
  2) 폰: 개발자 옵션 > USB 디버깅 켜기
  3) PC(platform-tools 폴더)에서:
       adb devices          # 폰 화면 "USB 디버깅 허용?" → 허용
       adb shell settings put global settings_enable_monitor_phantom_procs false
       adb shell device_config put activity_manager max_phantom_processes 2147483647

[방법 B] 폰 단독 · 무선 디버깅 (케이블 불필요)
  1) 개발자 옵션 > 무선 디버깅 켜기
  2) "페어링 코드로 기기 페어링" → 팝업의 IP:포트 와 6자리 코드 확인
  3) 화면분할로 Termux 띄운 채 (팝업 유지!):
       adb pair <IP>:<페어링포트>     # 6자리 입력
  4) 팝업 닫고, 무선디버깅 메인화면의 IP:포트(다른 번호)로:
       adb connect <IP>:<연결포트>
       adb shell settings put global settings_enable_monitor_phantom_procs false
  ※ 코드/포트는 매번 바뀌고 금방 만료됨. 실패 시 무선디버깅 껐다 켜고 재시도.

[방법 C] 안 해도 됨 (차선책)
  cron이 10분마다 죽은 프로세스를 자동 재기동하므로, 설정 없이도
  최대 10분 공백으로 운영은 계속됨. 방법 A를 나중에 하면 완벽해짐.
EOF

echo
echo "=================================================="
echo " 2. Tailscale — 외부에서 폰 접근 (SSH/대시보드)"
echo "=================================================="
cat <<'EOF'
가장 쉬운 방법 = Tailscale '앱' 사용 (Termux 데몬보다 안정적):

  1) Play스토어에서 'Tailscale' 앱 설치 → 로그인(구글 계정 가능)
  2) 앱에서 Connect → 폰에 100.x.y.z 주소 부여됨
  3) 다른 기기에도 같은 계정으로 Tailscale 설치
  4) 이제 집 밖에서도:
       ssh u0_a231@100.x.y.z -p 8022        # 폰 SSH
       http://100.x.y.z:8080                # 대시보드
  5) (선택) MagicDNS 켜면 IP 대신 이름(note10)으로 접속

포트포워딩 불필요, 공유기 설정 불필요, 암호화됨.
※ 이걸 켜두면 다음 세션에서 Claude가 폰에 직접 SSH로 작업 가능.
EOF
echo
echo "완료. 위 안내대로 진행하세요."
