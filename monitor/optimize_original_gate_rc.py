#!/usr/bin/env python3
"""
Optimize the original Gate-RC family parameters from the learning ledger.

This does NOT replace the electrical circuit model. It tunes the knobs inside it:
- blend weights between Diode, MW-RC and naive/current anchor
- Claude-style trim layer for local risk
- fade alpha after intraday low breach

Because day-1 has only one actual trading day, the script reports both:
1) raw best fit on all scored rows
2) conservative recommended params with shrinkage to the original defaults
"""

from __future__ import annotations

import csv
import itertools
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEARN = ROOT / "contest" / "learning"
LEDGER = LEARN / "intraday_ledger.csv"
OUT = LEARN / "original_gate_rc_optimization.json"


def load_rows():
    with LEDGER.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if r.get("actual_close")]


def f(row, key):
    return float(row[key])


def pred(row, w_diode, w_mwrc, w_naive, trim_base, foreign_trim, breach_trim, fade_alpha):
    diode = f(row, "diode_close_pred")
    mwrc = f(row, "mwrc_close_pred")
    naive = f(row, "kospi_level")
    p = w_diode * diode + w_mwrc * mwrc + w_naive * naive

    foreign = f(row, "foreign_million_krw")
    low = f(row, "kospi_low")
    level = f(row, "kospi_level")

    trim = trim_base
    if foreign <= -20000:
        trim += foreign_trim
    if low < 8400:
        trim += breach_trim
        p = p - fade_alpha * max(0.0, level - low)
    return p - trim


def mae(rows, params):
    errs = []
    for r in rows:
        y = f(r, "actual_close")
        yhat = pred(r, **params)
        errs.append(abs(yhat - y))
    return sum(errs) / len(errs)


def main():
    rows = load_rows()
    if not rows:
        raise SystemExit("No scored rows in ledger. Run update_model_learning.py --actual-close first.")

    candidates = []
    weight_grid = [
        (0.55, 0.20, 0.25),
        (0.50, 0.30, 0.20),
        (0.45, 0.35, 0.20),
        (0.40, 0.40, 0.20),
        (0.35, 0.60, 0.05),  # original v1
    ]
    for w_diode, w_mwrc, w_naive in weight_grid:
        for trim_base, foreign_trim, breach_trim, fade_alpha in itertools.product(
            [0, 10, 20, 30],
            [0, 20, 40, 60],
            [0, 20, 40, 60],
            [0.00, 0.05, 0.10, 0.13, 0.16],
        ):
            params = {
                "w_diode": w_diode,
                "w_mwrc": w_mwrc,
                "w_naive": w_naive,
                "trim_base": trim_base,
                "foreign_trim": foreign_trim,
                "breach_trim": breach_trim,
                "fade_alpha": fade_alpha,
            }
            candidates.append((mae(rows, params), params))
    candidates.sort(key=lambda x: x[0])
    best_mae, best = candidates[0]

    # Shrink toward the original model: day-1 data is too small.
    conservative = {
        "w_diode": 0.50,
        "w_mwrc": 0.30,
        "w_naive": 0.20,
        "trim_base": 10,
        "foreign_trim": 20,
        "breach_trim": 20,
        "fade_alpha": 0.05,
    }
    conservative_mae = mae(rows, conservative)

    original = {
        "w_diode": 0.35,
        "w_mwrc": 0.60,
        "w_naive": 0.05,
        "trim_base": 0,
        "foreign_trim": 0,
        "breach_trim": 0,
        "fade_alpha": 0,
    }
    original_mae = mae(rows, original)

    out = {
        "n_rows": len(rows),
        "warning": "Only one trading day is scored; raw optimum is overfit. Use conservative recommendation until >=5 days.",
        "original_v1": {"mae": original_mae, "params": original},
        "raw_best_fit": {"mae": best_mae, "params": best},
        "conservative_recommendation": {"mae": conservative_mae, "params": conservative},
        "interpretation": {
            "claude_differentiator": "trim layer: lower mechanical circuit output when foreign selling, intraday low breach, or fade risk appears",
            "keep_original_model": "RC/Diode blend stays; only blend weights and trim/fade knobs are tuned",
        },
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
