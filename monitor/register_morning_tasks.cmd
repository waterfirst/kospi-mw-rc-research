@echo off
REM KOSPI 오전 모니터 — 윈도우 작업 스케줄러 등록 (평일 09:00 / 10:30 / 12:00)
REM 관리자 권한 cmd에서 1회 실행. 등록 후 PC만 켜두면 자동 발송.
REM 먼저 run_morning.cmd 안의 TELEGRAM_TOKEN / CHAT_ID 를 채울 것.

set SCRIPT="%~dp0run_morning.cmd"

schtasks /create /tn "KOSPI_Monitor_0900" /tr "%SCRIPT% 0900" /sc weekly /d MON,TUE,WED,THU,FRI /st 09:00 /f
schtasks /create /tn "KOSPI_Monitor_1030" /tr "%SCRIPT% 1030" /sc weekly /d MON,TUE,WED,THU,FRI /st 10:30 /f
schtasks /create /tn "KOSPI_Monitor_1200" /tr "%SCRIPT% 1200" /sc weekly /d MON,TUE,WED,THU,FRI /st 12:00 /f

echo.
echo [완료] 3개 작업 등록됨. 확인: schtasks /query /tn "KOSPI_Monitor_0900"
echo 삭제: schtasks /delete /tn "KOSPI_Monitor_0900" /f  (1030,1200 동일)
echo.
echo ※ PC가 켜져 있어야 발송됩니다. 절전모드 진입 방지 권장.
pause
