# Server Monitoring Plan

Purpose: run KOSPI duel monitoring even when the local PC is off.

## Current State

Current Codex monitoring runs on the local Windows PC:

- working directory: `D:\nakcho\python\kospi-mw-rc-research`
- scripts: `monitor/*.py`
- output: `contest/*`
- Telegram alerts: environment variables on the local shell

If the PC sleeps or powers off, these processes stop.

## Target Architecture

Use an always-on Linux server as the execution host.

```text
GitHub repo
   |
   v
Linux server clone
   |
   +-- systemd service: continuous news shock monitor
   +-- systemd timers: 07:30 open, 09:05/10:30/12:30 close
   +-- watchdog: missing forecast file -> fallback run + Telegram warning
   |
   v
Telegram + GitHub artifacts
```

## Server Requirements

- Ubuntu 22.04+ or similar.
- Python 3.11+.
- Git.
- Network access to Naver Finance, Google News RSS, Telegram API, GitHub.
- Timezone: `Asia/Seoul`.

## Directory Layout

```text
/opt/kospi-mw-rc-research/
  monitor/
  contest/
  docs/
  .env
  logs/
```

Never commit `.env`.

## Environment

Server `.env`:

```bash
TELEGRAM_TOKEN=...
TELEGRAM_CHAT_ID=...
PYTHONUNBUFFERED=1
TZ=Asia/Seoul
```

Optional:

```bash
CODEX_USDKRW=...
CODEX_DXY=...
CODEX_US10Y=...
```

## Systemd Units

### Continuous News Monitor

`/etc/systemd/system/kospi-news.service`

```ini
[Unit]
Description=KOSPI news shock monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/kospi-mw-rc-research
EnvironmentFile=/opt/kospi-mw-rc-research/.env
ExecStart=/opt/kospi-mw-rc-research/.venv/bin/python monitor/news_shock_monitor.py --interval 900 --telegram
Restart=always
RestartSec=20

[Install]
WantedBy=multi-user.target
```

### Timed Forecast Runs

Use systemd timers for exact KST execution:

- `kospi-open-0730.timer`
- `kospi-close-0905.timer`
- `kospi-close-1030.timer`
- `kospi-close-1230.timer`
- `kospi-score-1635.timer`

Each service should run once and exit. Example:

`/etc/systemd/system/kospi-open-0730.service`

```ini
[Unit]
Description=KOSPI 07:30 open forecast
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/opt/kospi-mw-rc-research
EnvironmentFile=/opt/kospi-mw-rc-research/.env
ExecStart=/opt/kospi-mw-rc-research/.venv/bin/python monitor/overnight_0730_strategy.py --now --glm --telegram
```

`/etc/systemd/system/kospi-open-0730.timer`

```ini
[Unit]
Description=Run KOSPI open forecast at 07:30 KST

[Timer]
OnCalendar=Mon..Fri *-*-* 07:30:00 Asia/Seoul
Persistent=true

[Install]
WantedBy=timers.target
```

Close timer services call:

```bash
monitor/kospi_1230_close_forecast.py --label 0905 --glm --telegram
monitor/kospi_1230_close_forecast.py --label 1030 --glm --telegram
monitor/kospi_1230_close_forecast.py --label 1230 --glm --telegram
```

## Watchdog

Needed because 2026-07-03 close forecast failed operationally.

Watchdog logic:

```text
target + 3 minutes:
  check expected output file exists
  if missing:
    run immediate fallback forecast
    send Telegram warning
    save fallback with watchdog label
```

This should be implemented as a small script:

```text
monitor/forecast_watchdog.py
```

## GitHub Sync

Recommended:

- pull before daily run,
- commit/push forecast artifacts after each official run,
- never push secrets.

Possible command after each run:

```bash
git add contest docs PAPER_PROTOCOL.md
git commit -m "Record YYYY-MM-DD forecast artifacts" || true
git push origin master
```

Use a GitHub deploy key or token stored only on the server.

## Migration Steps

1. Provision server.
2. Set timezone:
   ```bash
   sudo timedatectl set-timezone Asia/Seoul
   ```
3. Clone repo:
   ```bash
   sudo mkdir -p /opt/kospi-mw-rc-research
   sudo chown $USER:$USER /opt/kospi-mw-rc-research
   git clone https://github.com/waterfirst/kospi-mw-rc-research.git /opt/kospi-mw-rc-research
   ```
4. Create venv:
   ```bash
   cd /opt/kospi-mw-rc-research
   python3 -m venv .venv
   .venv/bin/pip install requests
   ```
5. Add `.env`.
6. Install systemd services/timers.
7. Run:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now kospi-news.service
   sudo systemctl enable --now kospi-open-0730.timer
   sudo systemctl list-timers 'kospi-*'
   ```
8. Send Telegram test.
9. Verify files appear in `contest/`.

## Minimum Reliable Setup

For the July contest, the minimum server deployment is:

- continuous `news_shock_monitor.py`,
- 07:30 open service,
- 12:30 close service,
- watchdog for missing files,
- daily GitHub artifact push.

This is enough to avoid the local-PC-off failure class.
