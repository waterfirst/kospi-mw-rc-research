@echo off
cd /d D:\python\kospi
"C:\Program Files\Python314\python.exe" -X utf8 "D:\python\kospi\krx_actor_verification_pipeline\us_market_telegram_monitor.py" >> "D:\python\kospi\krx_actor_verification_pipeline\outputs_predictive_extension\telegram_scheduler_stdout.log" 2>> "D:\python\kospi\krx_actor_verification_pipeline\outputs_predictive_extension\telegram_scheduler_stderr.log"
