# Home Server Setup For KOSPI Monitoring

Purpose: run the KOSPI duel monitoring system on a home server PC so it continues even when the main desktop is off.

## Recommended Architecture

Use a dedicated always-on mini PC or desktop as the execution host.

```text
Home server PC
  Ubuntu Server
  wired LAN
  UPS
  systemd services/timers
  GitHub sync
  Telegram alerts
```

Main desktop remains for development and manual analysis. The home server runs production monitoring.

## Hardware

Minimum:

- CPU: recent Intel i3/i5, Ryzen 3/5, or efficient mini PC CPU.
- RAM: 16 GB.
- Storage: 500 GB NVMe SSD.
- Network: wired Ethernet.
- Power: UPS recommended.

Better:

- RAM: 32 GB.
- Storage: 1 TB NVMe.
- Low idle power mini PC or small desktop.
- BIOS option for auto power-on after outage.

GPU:

- Not required for baseline KOSPI monitoring.
- Useful only if running local Ollama/GLM models.
- For this contest, CPU server + API/lightweight model is more reliable than a hot GPU box.

## OS Choice

Recommended:

- Ubuntu Server 24.04 LTS or 22.04 LTS.

Avoid Windows for the always-on server unless necessary. Linux gives cleaner service/timer management through `systemd`.

## Network Setup

1. Use wired Ethernet.
2. Set DHCP reservation on the router so the server always gets the same LAN IP.
3. Enable SSH.
4. Do not expose SSH directly to the internet if unnecessary.
5. For remote access, prefer:
   - Tailscale,
   - WireGuard VPN,
   - Cloudflare Tunnel.

## BIOS Settings

Enable:

- restore power after AC loss,
- wake on LAN if needed,
- disable sleep/hibernate.

## Ubuntu Initial Setup

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git python3 python3-venv python3-pip curl jq
sudo timedatectl set-timezone Asia/Seoul
```

Create a dedicated user if desired:

```bash
sudo adduser kospi
sudo usermod -aG sudo kospi
```

## Repository Setup

```bash
sudo mkdir -p /opt/kospi-mw-rc-research
sudo chown $USER:$USER /opt/kospi-mw-rc-research
git clone https://github.com/waterfirst/kospi-mw-rc-research.git /opt/kospi-mw-rc-research
cd /opt/kospi-mw-rc-research
python3 -m venv .venv
.venv/bin/pip install requests
```

## Secret Setup

Create:

```bash
nano /opt/kospi-mw-rc-research/.env
```

Content:

```bash
TELEGRAM_TOKEN=...
TELEGRAM_CHAT_ID=...
PYTHONUNBUFFERED=1
TZ=Asia/Seoul
```

Permissions:

```bash
chmod 600 /opt/kospi-mw-rc-research/.env
```

Never commit `.env`.

## GitHub Push Setup

Use either:

- SSH deploy key,
- GitHub fine-grained token stored in server credential store,
- or manual pull/push from desktop if fully automated push is not needed.

Recommended for July contest:

- server can write/push forecast artifacts,
- token/key limited to this repository only.

## Systemd Services

### News Monitor

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

Enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now kospi-news.service
sudo systemctl status kospi-news.service
```

## Forecast Timers

Use one-shot services and timers.

Example open service:

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

Enable:

```bash
sudo systemctl enable --now kospi-open-0730.timer
```

Create similar timers for:

- 09:05 close monitor,
- 10:30 close monitor,
- 12:30 final close call,
- 16:35 score/postmortem helper if implemented.

## Watchdog Requirement

The 2026-07-03 Codex close miss was partly an operations failure. The home server must include a watchdog.

Rule:

```text
target time + 3 minutes:
  if expected forecast file is missing:
    run fallback immediately
    send Telegram warning
    save watchdog output
```

This is required before trusting the home server for official contest submissions.

Use:

```bash
monitor/forecast_watchdog.py --kind open --label 0730 --glm --telegram
monitor/forecast_watchdog.py --kind close --label 1230 --glm --telegram
```

Recommended watchdog timers:

- 07:33 KST open fallback check.
- 12:33 KST close fallback check.

## Reliability Checklist

- Server uses wired LAN.
- Sleep/hibernate disabled.
- BIOS auto power-on after outage enabled.
- UPS installed if possible.
- `systemctl list-timers 'kospi-*'` shows all timers.
- `journalctl -u kospi-news.service -f` shows active polling.
- Telegram test succeeds.
- Forecast output appears in `contest/`.
- GitHub push works without interactive prompt.
- Watchdog is active.

## Remote Access

Recommended:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Then access the server through Tailscale SSH or private IP.

## Backup

Daily:

- GitHub push for forecast artifacts.

Weekly:

- backup `.env` separately in a secure password manager,
- export systemd unit files,
- snapshot important configs.

## Operating Rule

Home server is production. Main PC is development.

Do not manually edit production files without committing the change back to GitHub.
