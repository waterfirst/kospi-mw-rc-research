# Monday 07:30 Open Forecast Automation - 2026-07-04

정보·연구 목적. 투자자문 아님.

## Scheduled Task

| Item | Value |
|---|---|
| Task name | `Codex KOSPI Monday 0730 Open Forecast` |
| Host | local Windows PC |
| Next run | 2026-07-06 07:30 KST |
| Script | `monitor/run_monday_open_forecast.ps1` |
| Purpose | run 07:30 KOSPI open forecast, watchdog fallback, GitHub artifact push |

## Runner Behavior

1. Run `monitor/overnight_0730_strategy.py --now --glm --telegram`.
2. Run `monitor/forecast_watchdog.py --kind open --label 0730 --glm --telegram`.
3. Add forecast/news/learning artifacts.
4. Commit with `Record 2026-07-06 open forecast`.
5. Rebase and push to GitHub.

## Notes

- Telegram sends only if `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` exist in the execution environment.
- Secrets are not stored in the repository.
- This local scheduled task does not survive a powered-off PC. The home server plan remains the reliable production path.

