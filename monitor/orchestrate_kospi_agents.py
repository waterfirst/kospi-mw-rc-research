#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAVE_LOG_SCRIPT = ROOT / "monitor" / "save_daily_log.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Conductor skeleton for KOSPI multi-agent loop.")
    parser.add_argument("--date", default=str(date.today()))
    parser.add_argument(
        "--mode",
        choices=["morning", "close", "full"],
        default="full",
        help="Loop mode to orchestrate",
    )
    parser.add_argument("--model-version", default="v0.1-orchestrator")
    parser.add_argument("--payload-file", help="Optional JSON input for seeding the log")
    return parser.parse_args()


def run_step(name: str, detail: str) -> None:
    print(f"[conductor] {name}: {detail}")


def build_seed_payload(args: argparse.Namespace) -> dict:
    payload = {
        "model_version": args.model_version,
        "reflection": {
            "summary": f"orchestrator initialized in {args.mode} mode",
            "next_candidates": [],
        },
    }
    if args.payload_file:
        payload["orchestrator_seed_file"] = args.payload_file
    return payload


def save_seed_log(args: argparse.Namespace, payload: dict) -> None:
    cmd = [
        sys.executable,
        str(SAVE_LOG_SCRIPT),
        "--date",
        args.date,
        "--payload",
        json.dumps(payload, ensure_ascii=False),
    ]
    subprocess.run(cmd, check=True)


def main() -> int:
    args = parse_args()

    run_step("Conductor", "start orchestration")
    run_step("Data Agent", "collect market / FX / flow / news inputs")
    run_step("Forecast Agent", f"prepare {args.mode} prediction workflow")
    run_step("Scoring Agent", "reserved for actual-vs-predicted scoring after market data is available")
    run_step("Failure Agent", "reserved for failure tagging and rule candidate generation")
    run_step("Report Agent", "reserved for daily/weekly reporting")
    run_step("Review Agent", "reserved for cross-checking conclusions")

    payload = build_seed_payload(args)
    save_seed_log(args, payload)

    run_step("Conductor", f"log seeded for {args.date}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
