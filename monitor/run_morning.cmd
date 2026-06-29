@echo off
REM KOSPI 오전 모니터 실행 래퍼 (Windows)
REM 사용: run_morning.cmd 0900   (라벨: 0900 / 1030 / 1200)

REM ── 설정: 본인 텔레그램 봇 토큰/챗ID 입력 ──
set TELEGRAM_TOKEN=여기에_봇_토큰
set TELEGRAM_CHAT_ID=여기에_챗ID
REM (선택) Claude 자연어 분석:
REM set ANTHROPIC_API_KEY=여기에_API키

cd /d "%~dp0"
python morning_monitor.py %1
