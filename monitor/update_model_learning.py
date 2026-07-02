#!/usr/bin/env python3
"""
Build/update an intraday learning ledger from saved consortium snapshots.

This is intentionally simple on day 1:
- normalize all saved snapshot/model files into one CSV
- keep model parameters in JSON
- when final close is available, score every checkpoint forecast

The parameters are small, auditable knobs. They can be optimized later once
several days of checkpoint rows exist.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTEST = ROOT / "contest"
INTRADAY = CONTEST / "intraday"
CONSORTIUM = CONTEST / "consortium"
LEARN = CONTEST / "learning"
LEDGER = LEARN / "intraday_ledger.csv"
PARAMS = LEARN / "gate_rc_hybrid_params.json"


FIELDS = [
    "created_at_kst",
    "label",
    "snapshot_hash",
    "kospi_date",
    "kospi_open",
    "kospi_high",
    "kospi_low",
    "kospi_level",
    "kospi_prev_close",
    "foreign_million_krw",
    "institution_million_krw",
    "individual_million_krw",
    "d_sell",
    "sp500_pct",
    "nasdaq_pct",
    "sox_pct",
    "diode_close_pred",
    "mwrc_close_pred",
    "hybrid_close_pred",
    "hybrid_prob_up",
    "actual_close",
    "diode_abs_error",
    "mwrc_abs_error",
    "hybrid_abs_error",
]


DEFAULT_PARAMS = {
    "version": "Gate-RC Hybrid v1",
    "created_at_kst": None,
    "rules": {
        "d_sell_on_weights": {"diode": 0.70, "mwrc": 0.10, "naive": 0.20},
        "d_sell_off_weights": {"diode": 0.35, "mwrc": 0.60, "naive": 0.05},
        "risk_level": 8400.0,
        "risk_close_range": [8260.0, 8360.0],
    },
    "fit_status": {
        "n_scored_rows": 0,
        "best_model_so_far": None,
        "notes": "Day-1 seed. Do not overfit until multiple days are scored.",
    },
}


def now_kst() -> str:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def row_from_intraday(path: Path) -> dict[str, Any]:
    data = load_json(path)
    compact = data["compact"]
    models = data["models"]
    last = compact["kospi_last"]
    prev = compact["kospi_prev"]
    flow = compact["flow"]
    us = compact["us_market"]
    d_sell = bool(flow.get("d_sell", flow["foreign_million_krw"] < 0 and flow["institution_million_krw"] < 0))
    return {
        "created_at_kst": compact["created_at_kst"],
        "label": data["label"],
        "snapshot_hash": compact["snapshot_hash"],
        "kospi_date": last["date"],
        "kospi_open": last["open"],
        "kospi_high": last["high"],
        "kospi_low": last["low"],
        "kospi_level": last["close"],
        "kospi_prev_close": prev["close"],
        "foreign_million_krw": flow["foreign_million_krw"],
        "institution_million_krw": flow["institution_million_krw"],
        "individual_million_krw": flow["individual_million_krw"],
        "d_sell": d_sell,
        "sp500_pct": us["SP500"]["change_pct"],
        "nasdaq_pct": us["NASDAQ"]["change_pct"],
        "sox_pct": us["SOX"]["change_pct"],
        "diode_close_pred": models["diode_v5"]["close"],
        "mwrc_close_pred": models["mw_rc_v7"]["close"],
        "hybrid_close_pred": models["gate_rc_hybrid_v1"]["close"],
        "hybrid_prob_up": models["gate_rc_hybrid_v1"]["prob_up"],
        "actual_close": "",
        "diode_abs_error": "",
        "mwrc_abs_error": "",
        "hybrid_abs_error": "",
    }


def row_from_open_models(path: Path) -> dict[str, Any]:
    models = load_json(path)
    snap_path = path.with_name(path.name.replace("_models.json", "_snapshot.json"))
    snap = load_json(snap_path)
    compact = {
        "snapshot_hash": snap["snapshot_hash"],
        "created_at_kst": snap["created_at_kst"],
        "kospi_last": snap["kospi_daily"]["rows"][-1],
        "kospi_prev": snap["kospi_daily"]["rows"][-2],
        "flow": snap["flow"],
        "us_market": snap["us_market"],
    }
    last = compact["kospi_last"]
    prev = compact["kospi_prev"]
    flow = compact["flow"]
    us = compact["us_market"]
    d_sell = bool(flow.get("d_sell", flow["foreign_million_krw"] < 0 and flow["institution_million_krw"] < 0))
    return {
        "created_at_kst": compact["created_at_kst"],
        "label": "open_forecast",
        "snapshot_hash": compact["snapshot_hash"],
        "kospi_date": last["date"],
        "kospi_open": last["open"],
        "kospi_high": last["high"],
        "kospi_low": last["low"],
        "kospi_level": last["close"],
        "kospi_prev_close": prev["close"],
        "foreign_million_krw": flow["foreign_million_krw"],
        "institution_million_krw": flow["institution_million_krw"],
        "individual_million_krw": flow["individual_million_krw"],
        "d_sell": d_sell,
        "sp500_pct": us["SP500"]["change_pct"],
        "nasdaq_pct": us["NASDAQ"]["change_pct"],
        "sox_pct": us["SOX"]["change_pct"],
        "diode_close_pred": models["diode_v5"]["close"],
        "mwrc_close_pred": models["mw_rc_v7"]["close"],
        "hybrid_close_pred": models["gate_rc_hybrid_v1"]["close"],
        "hybrid_prob_up": models["gate_rc_hybrid_v1"]["prob_up"],
        "actual_close": "",
        "diode_abs_error": "",
        "mwrc_abs_error": "",
        "hybrid_abs_error": "",
    }


def build_rows(actual_close: float | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in sorted(CONSORTIUM.glob("*_open_models.json")):
        row = row_from_open_models(path)
        key = row["snapshot_hash"] + row["label"]
        if key not in seen:
            rows.append(row)
            seen.add(key)
    for path in sorted(INTRADAY.glob("*.json")):
        try:
            data = load_json(path)
            if "compact" not in data or "models" not in data:
                continue
        except Exception:
            continue
        row = row_from_intraday(path)
        key = row["snapshot_hash"] + row["label"]
        if key not in seen:
            rows.append(row)
            seen.add(key)
    rows.sort(key=lambda r: r["created_at_kst"])
    if actual_close is not None:
        for row in rows:
            row["actual_close"] = actual_close
            row["diode_abs_error"] = abs(float(row["diode_close_pred"]) - actual_close)
            row["mwrc_abs_error"] = abs(float(row["mwrc_close_pred"]) - actual_close)
            row["hybrid_abs_error"] = abs(float(row["hybrid_close_pred"]) - actual_close)
    return rows


def write_ledger(rows: list[dict[str, Any]]) -> None:
    LEARN.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def update_params(rows: list[dict[str, Any]]) -> dict[str, Any]:
    params = DEFAULT_PARAMS.copy()
    if PARAMS.exists():
        params = load_json(PARAMS)
    params["updated_at_kst"] = now_kst()
    scored = [r for r in rows if r["actual_close"] != ""]
    params["fit_status"]["n_scored_rows"] = len(scored)
    if scored:
        mae = {}
        for model, field in (
            ("diode_v5", "diode_abs_error"),
            ("mw_rc_v7", "mwrc_abs_error"),
            ("gate_rc_hybrid_v1", "hybrid_abs_error"),
        ):
            vals = [float(r[field]) for r in scored]
            mae[model] = sum(vals) / len(vals)
        params["fit_status"]["mae_points"] = mae
        params["fit_status"]["best_model_so_far"] = min(mae, key=mae.get)
    else:
        params["fit_status"]["best_model_so_far"] = None
    PARAMS.write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8")
    return params


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--actual-close", type=float)
    args = parser.parse_args()

    rows = build_rows(args.actual_close)
    write_ledger(rows)
    params = update_params(rows)
    print(f"ledger={LEDGER}")
    print(f"rows={len(rows)}")
    print(f"params={PARAMS}")
    print(json.dumps(params["fit_status"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
