#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "contest" / "learning" / "daily_logs"
TEMPLATE_PATH = LOG_DIR / "_template.json"


def load_template() -> dict:
    if TEMPLATE_PATH.exists():
        return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    return {
        "date": "YYYY-MM-DD",
        "model_version": "vX.Y-name",
        "regime": "other",
        "inputs": {},
        "flags": [],
        "predictions": {"open": 0.0, "close": 0.0},
        "actuals": {"open": 0.0, "close": 0.0},
        "scores": {"open": 0, "close": 0, "direction": 0, "regime": 0, "total": 0},
        "failure_tags": [],
        "reflection": {"summary": "", "next_candidates": []},
    }


def deep_update(base: dict, patch: dict) -> dict:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = value
    return base


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Save or update KOSPI daily learning log.")
    parser.add_argument("--date", default=str(date.today()), help="Log date in YYYY-MM-DD")
    parser.add_argument("--payload", help="Inline JSON payload")
    parser.add_argument("--payload-file", help="Path to JSON payload file")
    parser.add_argument("--stdout", action="store_true", help="Print resulting JSON to stdout")
    return parser.parse_args()


def load_payload(args: argparse.Namespace) -> dict:
    if args.payload and args.payload_file:
        raise SystemExit("Use either --payload or --payload-file, not both.")
    if args.payload_file:
        return json.loads(Path(args.payload_file).read_text(encoding="utf-8"))
    if args.payload:
        return json.loads(args.payload)
    return {}


def main() -> int:
    args = parse_args()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{args.date}.json"

    template = deepcopy(load_template())
    template["date"] = args.date

    if log_path.exists():
        current = json.loads(log_path.read_text(encoding="utf-8"))
    else:
        current = template

    payload = load_payload(args)
    result = deep_update(current, payload)
    result["date"] = args.date

    log_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"[save_daily_log] wrote {log_path}")
    if args.stdout:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
