#!/usr/bin/env python3
"""
KOSPI intraday monitor for the forecast duel.

Collects Naver snapshots at named checkpoints, stores raw/compact/model files,
and optionally sends Telegram messages.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import time
from pathlib import Path

import requests

import codex_contest_forecast as ccf
import kospi_consortium as kc


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "contest" / "intraday"


CHECKPOINTS = {
    "0900": (9, 0),
    "1030": (10, 30),
    "1200": (12, 0),
    "1230": (12, 30),
}


def now_kst() -> dt.datetime:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))


def checkpoint_time(name: str) -> dt.datetime:
    h, m = CHECKPOINTS[name]
    n = now_kst()
    return n.replace(hour=h, minute=m, second=0, microsecond=0)


def sleep_until(name: str) -> None:
    target = checkpoint_time(name)
    delay = (target - now_kst()).total_seconds()
    if delay > 0:
        time.sleep(delay)


def send_telegram(text: str) -> None:
    token = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=20)
    r.raise_for_status()


def collect(label: str, telegram: bool) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    snapshot = ccf.collect_snapshot("close")
    compact = ccf.compact_market_digest(snapshot)
    models = kc.compute_models(compact)
    message = kc.build_message("close", compact, models)
    stamp = now_kst().strftime("%Y%m%d_%H%M%S")
    payload = {
        "label": label,
        "snapshot": snapshot,
        "compact": compact,
        "models": models,
        "message": message,
    }
    out_path = OUT / f"{stamp}_{label}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / f"{stamp}_{label}.txt").write_text(message, encoding="utf-8")
    print(f"saved={out_path}")
    print(message)
    if telegram:
        send_telegram(f"[{label}]\n{message}")
        print("telegram_sent=OK")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", choices=list(CHECKPOINTS) + ["now"], default="now")
    parser.add_argument("--run-day", action="store_true", help="collect 0900/1030/1200/1230, sleeping until future checkpoints")
    parser.add_argument("--telegram", action="store_true")
    args = parser.parse_args()

    if args.run_day:
        for label in ("0900", "1030", "1200", "1230"):
            sleep_until(label)
            collect(label, args.telegram)
        return 0

    label = args.checkpoint
    if label != "now":
        sleep_until(label)
    collect(label, args.telegram)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
