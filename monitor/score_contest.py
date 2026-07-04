#!/usr/bin/env python3
"""
Score a locked KOSPI contest forecast under contest rules v2.

Usage:
  python monitor/score_contest.py --forecast contest/codex/..._open_forecast.json --actual 8450.12 --section open
  python monitor/score_contest.py --forecast contest/codex/..._close_forecast.json --actual 8520.34 --section close
  python monitor/score_contest.py --forecast ... --actual 8520.34 --section close --telegram
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def tier_score(forecast: float, actual: float) -> tuple[int, float]:
    """Return v2 tier score and percentage error."""
    if actual <= 0:
        raise ValueError("actual must be positive")
    error_pct = abs(forecast - actual) / actual * 100
    for threshold, points in ((0.25, 5), (0.50, 4), (0.75, 3), (1.00, 2), (1.50, 1)):
        if error_pct <= threshold:
            return points, error_pct
    return 0, error_pct


def send_telegram(text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN or TELEGRAM_TOKEN, plus TELEGRAM_CHAT_ID.")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=20)
    r.raise_for_status()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forecast", required=True)
    parser.add_argument("--actual", required=True, type=float)
    parser.add_argument("--section", choices=["open", "close"], required=True)
    parser.add_argument("--telegram", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = json.loads(Path(args.forecast).read_text(encoding="utf-8-sig"))
    forecast = float(data["forecast"])
    points, error_pct = tier_score(forecast, args.actual)
    result = {
        "section": args.section,
        "forecast": forecast,
        "actual": args.actual,
        "absolute_error": round(abs(forecast - args.actual), 2),
        "error_pct": round(error_pct, 4),
        "score": points,
        "max_score": 5,
        "snapshot_hash": data.get("snapshot_hash"),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    section_ko = "시가" if args.section == "open" else "종가"
    message = (
        f"⚔️ KOSPI 대결 개별 채점 — {section_ko}\n"
        f"예측 {forecast:,.2f} / 실제 {args.actual:,.2f}\n"
        f"오차 {result['absolute_error']:,.2f}pt ({result['error_pct']:.4f}%)\n"
        f"점수 {result['score']}/5\n"
        f"스냅샷 {result.get('snapshot_hash')}\n"
        "정보·연구 목적. 투자자문 아님."
    )
    if args.dry_run:
        print("\n--- Telegram message preview ---")
        print(message)
    if args.telegram:
        send_telegram(message)
        print("텔레그램 발송 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
