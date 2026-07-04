@echo off
setlocal
set RUNNER=D:\python\kospi\run_kospi_telegram_monitor.cmd

schtasks /Create /TN "KOSPI_9000_FastV_Telegram_0755" /TR "\"%RUNNER%\"" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 07:55 /F
schtasks /Create /TN "KOSPI_9000_FastV_Telegram_0930" /TR "\"%RUNNER%\"" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 09:30 /F
schtasks /Create /TN "KOSPI_9000_FastV_Telegram_1130" /TR "\"%RUNNER%\"" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 11:30 /F
schtasks /Create /TN "KOSPI_9000_FastV_Telegram_1330" /TR "\"%RUNNER%\"" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 13:30 /F
schtasks /Create /TN "KOSPI_9000_FastV_Telegram_1545" /TR "\"%RUNNER%\"" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 15:45 /F
schtasks /Create /TN "KOSPI_9000_FastV_Telegram_2230" /TR "\"%RUNNER%\"" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 22:30 /F
schtasks /Create /TN "KOSPI_9000_FastV_Telegram_0030" /TR "\"%RUNNER%\"" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 00:30 /F
schtasks /Create /TN "KOSPI_9000_FastV_Telegram_0330" /TR "\"%RUNNER%\"" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 03:30 /F
schtasks /Create /TN "KOSPI_9000_FastV_Telegram_0630" /TR "\"%RUNNER%\"" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 06:30 /F

schtasks /Query /TN "KOSPI_9000_FastV_Telegram_0755"
schtasks /Query /TN "KOSPI_9000_FastV_Telegram_0930"
schtasks /Query /TN "KOSPI_9000_FastV_Telegram_1130"
schtasks /Query /TN "KOSPI_9000_FastV_Telegram_1330"
schtasks /Query /TN "KOSPI_9000_FastV_Telegram_1545"
schtasks /Query /TN "KOSPI_9000_FastV_Telegram_2230"
schtasks /Query /TN "KOSPI_9000_FastV_Telegram_0030"
schtasks /Query /TN "KOSPI_9000_FastV_Telegram_0330"
schtasks /Query /TN "KOSPI_9000_FastV_Telegram_0630"
