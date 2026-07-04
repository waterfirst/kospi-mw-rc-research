#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]


def now_kst() -> dt.datetime:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))


def send_telegram(text: str) -> bool:
    token = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=20)
    r.raise_for_status()
    return bool((r.json() or {}).get("ok"))


def latest_exists(kind: str, label: str, date: str) -> bool:
    if kind == "open":
        base = ROOT / "contest" / "overnight"
        patterns = [f"{date}_*_{label}_0730_strategy.json", f"*FINAL_OPEN_CALL_{date}_*.md"]
    else:
        base = ROOT / "contest" / "intraday"
        patterns = [f"{date}_*_{label}_robust_close_forecast.json"]
    return any(any(base.glob(p)) for p in patterns)


def run_fallback(kind: str, label: str, use_glm: bool, telegram: bool) -> int:
    if kind == "open":
        cmd = [sys.executable, "monitor/overnight_0730_strategy.py", "--now"]
    else:
        cmd = [sys.executable, "monitor/kospi_1230_close_forecast.py", "--label", f"watchdog_{label}"]
    if use_glm:
        cmd.append("--glm")
    if telegram:
        cmd.append("--telegram")
    return subprocess.run(cmd, cwd=ROOT, timeout=180).returncode


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--kind", choices=["open", "close"], required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--glm", action="store_true")
    p.add_argument("--telegram", action="store_true")
    args = p.parse_args()

    date = now_kst().strftime("%Y%m%d")
    if latest_exists(args.kind, args.label, date):
        print(f"watchdog=OK kind={args.kind} label={args.label}")
        return 0

    msg = f"[Codex] WATCHDOG missing forecast kind={args.kind} label={args.label}; running fallback"
    print(msg)
    if args.telegram:
        send_telegram(msg)
    rc = run_fallback(args.kind, args.label, args.glm, args.telegram)
    print(f"fallback_rc={rc}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
