#!/usr/bin/env python3
"""
Recent 3-month KOSPI backtest for two explicit model rules.

Models
------
1) Diode v5
   - Diagnostic: D_sell[t] = foreign[t] < 0 and institution[t] < 0
   - Ex-ante: D_sell[t-1] predicts weaker next-day return.

2) MW-RC v7 proxy
   - Tests the usable core claim, not every narrative term:
     after a selloff, recovery is possible when parallel conductance is open.
   - Conductance proxy uses prior-day flows:
       sigma_open[t-1] = institution>0 OR individual<0 OR foreign>0
     because v7 says foreign is not the master switch and institution/retail
     discharge can create a fast recovery path.
   - Ex-ante UP signal:
       prior return <= -1.0% AND sigma_open[t-1]

All forecasts use only t-1 information. Same-day diode diagnostics are reported
separately because they are useful for intraday/close monitoring but not a
pure next-day forecast.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import os
import re
import statistics as stats
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "contest" / "backtests"
HEAD = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}


def kst_today() -> dt.date:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()


def ymd(d: dt.date) -> str:
    return d.strftime("%Y%m%d")


def parse_price_csv(path: Path) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if not row or not str(row[0]).isdigit():
                continue
            out[str(row[0])] = {
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]) if len(row) > 5 else 0.0,
            }
    return out


def parse_flow_csv(path: Path) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) < 4 or not row[0].isdigit():
                continue
            out[row[0]] = {
                "individual": int(row[1]),
                "foreign": int(row[2]),
                "institution": int(row[3]),
            }
    return out


def fetch_price(start: str, end: str) -> dict[str, dict[str, float]]:
    url = (
        "https://api.finance.naver.com/siseJson.naver?symbol=KOSPI"
        f"&requestType=1&startTime={start}&endTime={end}&timeframe=day"
    )
    r = requests.get(url, headers=HEAD, timeout=25)
    r.raise_for_status()
    rows = json.loads(r.text.strip().replace("'", '"'))
    out: dict[str, dict[str, float]] = {}
    for row in rows:
        if isinstance(row, list) and row and str(row[0]).isdigit():
            out[str(row[0])] = {
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]) if len(row) > 5 else 0.0,
            }
    return out


def fetch_flow(max_pages: int = 90) -> dict[str, dict[str, int]]:
    today = ymd(kst_today())
    session = requests.Session()
    session.headers.update(HEAD)
    out: dict[str, dict[str, int]] = {}
    empty = 0
    for page in range(1, max_pages + 1):
        url = (
            "https://finance.naver.com/sise/investorDealTrendDay.naver"
            f"?bizdate={today}&sosok=01&page={page}"
        )
        r = session.get(url, timeout=20)
        r.raise_for_status()
        r.encoding = "euc-kr"
        found = False
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", r.text, re.S):
            cells = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
            clean = [
                re.sub(r"<[^>]+>", "", x).replace("&nbsp;", "").replace(",", "").strip()
                for x in cells
            ]
            if clean and re.match(r"\d{2}\.\d{2}\.\d{2}$", clean[0]):
                try:
                    d = "20" + clean[0].replace(".", "")
                    out[d] = {
                        "individual": int(clean[1]),
                        "foreign": int(clean[2]),
                        "institution": int(clean[3]),
                    }
                    found = True
                except (ValueError, IndexError):
                    pass
        empty = 0 if found else empty + 1
        if empty >= 3:
            break
    return out


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def stdev(xs: list[float]) -> float:
    return stats.pstdev(xs) if len(xs) > 1 else float("nan")


def accuracy(rows: list[dict[str, Any]], pred_key: str) -> float:
    usable = [r for r in rows if r[pred_key] != "FLAT" and r["actual_dir"] != "FLAT"]
    if not usable:
        return float("nan")
    return sum(r[pred_key] == r["actual_dir"] for r in usable) / len(usable)


def balanced_accuracy(rows: list[dict[str, Any]], pred_key: str) -> float:
    vals = []
    for target in ("UP", "DOWN"):
        sub = [r for r in rows if r["actual_dir"] == target and r[pred_key] != "FLAT"]
        if sub:
            vals.append(sum(r[pred_key] == target for r in sub) / len(sub))
    return mean(vals) if vals else float("nan")


def summarize_strategy(returns: list[float], positions: list[float]) -> dict[str, float]:
    strat = [r * p for r, p in zip(returns, positions)]
    if not strat:
        return {}
    eq = 1.0
    curve = []
    for r in strat:
        eq *= 1 + r / 100.0
        curve.append(eq)
    peak = 1.0
    mdd = 0.0
    for x in curve:
        peak = max(peak, x)
        mdd = min(mdd, x / peak - 1)
    sd = stdev(strat)
    sharpe = mean(strat) / sd * math.sqrt(252) if sd and not math.isnan(sd) else float("nan")
    years = len(strat) / 252
    cagr = (curve[-1] ** (1 / years) - 1) * 100 if years and curve[-1] > 0 else float("nan")
    return {
        "total_pct": (curve[-1] - 1) * 100,
        "cagr_pct": cagr,
        "sharpe": sharpe,
        "mdd_pct": mdd * 100,
    }


def run(fetch: bool) -> dict[str, Any]:
    end_date = kst_today()
    start_date = end_date - dt.timedelta(days=94)
    if fetch:
        price = fetch_price(ymd(start_date), ymd(end_date))
        flow = fetch_flow()
    else:
        price = parse_price_csv(DATA / "kospi_price.csv")
        flow = parse_flow_csv(DATA / "kospi_flow.csv")

    dates = sorted(d for d in set(price) & set(flow) if ymd(start_date) <= d <= ymd(end_date))
    if len(dates) < 20:
        raise RuntimeError(f"not enough matched rows: {len(dates)}")

    records: list[dict[str, Any]] = []
    closes = [price[d]["close"] for d in dates]
    rets = [0.0]
    for i in range(1, len(dates)):
        rets.append((closes[i] / closes[i - 1] - 1) * 100)

    for i, d in enumerate(dates):
        f = flow[d]["foreign"]
        inst = flow[d]["institution"]
        indiv = flow[d]["individual"]
        d_sell = f < 0 and inst < 0
        actual_dir = "UP" if rets[i] > 0.15 else ("DOWN" if rets[i] < -0.15 else "FLAT")
        records.append({
            "date": d,
            "close": closes[i],
            "ret_pct": rets[i],
            "individual": indiv,
            "foreign": f,
            "institution": inst,
            "d_sell": d_sell,
            "actual_dir": actual_dir,
        })

    # Same-day diagnostic diode.
    for r in records:
        r["diode_diag_dir"] = "DOWN" if r["d_sell"] else "UP"

    # Ex-ante forecasts use previous day only.
    test_rows: list[dict[str, Any]] = []
    for i in range(1, len(records)):
        prev = records[i - 1]
        cur = dict(records[i])

        cur["diode_next_dir"] = "DOWN" if prev["d_sell"] else "UP"

        prior_selloff = prev["ret_pct"] <= -1.0
        sigma_open = (
            prev["institution"] > 0
            or prev["individual"] < 0
            or prev["foreign"] > 0
        )
        cur["mwrc_next_dir"] = "UP" if prior_selloff and sigma_open else "FLAT"

        # A point forecast proxy for MW-RC: relax toward previous 10-day high
        # after selloff when conductance is open. Otherwise naive previous close.
        window = records[max(0, i - 10):i]
        target = max(x["close"] for x in window) if window else prev["close"]
        tau = 1.2 if sigma_open else 20.0
        cur["mwrc_point"] = prev["close"] + (target - prev["close"]) / tau if prior_selloff else prev["close"]
        cur["naive_point"] = prev["close"]
        test_rows.append(cur)

    diode_on = [r["ret_pct"] for r in records if r["d_sell"]]
    diode_off = [r["ret_pct"] for r in records if not r["d_sell"]]
    big_down = [r for r in records if r["ret_pct"] <= -2.0]
    big_up = [r for r in records if r["ret_pct"] >= 2.0]

    diode_positions = [1.0 if not records[i - 1]["d_sell"] else 0.0 for i in range(1, len(records))]
    mwrc_positions = [1.0 if r["mwrc_next_dir"] == "UP" else 0.0 for r in test_rows]
    bh_positions = [1.0 for _ in test_rows]
    test_rets = [r["ret_pct"] for r in test_rows]

    mwrc_abs_err = [abs(r["mwrc_point"] - r["close"]) / r["close"] * 100 for r in test_rows]
    naive_abs_err = [abs(r["naive_point"] - r["close"]) / r["close"] * 100 for r in test_rows]

    result = {
        "created_at_kst": dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="seconds"),
        "fetch_live": fetch,
        "period": {"start": dates[0], "end": dates[-1], "rows": len(dates), "test_rows": len(test_rows)},
        "diode_v5": {
            "d_sell_days": len(diode_on),
            "d_sell_off_days": len(diode_off),
            "same_day_on_avg_ret_pct": mean(diode_on),
            "same_day_off_avg_ret_pct": mean(diode_off),
            "same_day_spread_off_minus_on_pct": mean(diode_off) - mean(diode_on),
            "same_day_direction_accuracy": accuracy(records, "diode_diag_dir"),
            "same_day_balanced_accuracy": balanced_accuracy(records, "diode_diag_dir"),
            "big_down_capture_rate": (
                sum(r["d_sell"] for r in big_down) / len(big_down) if big_down else float("nan")
            ),
            "big_down_count": len(big_down),
            "big_up_false_alarm_rate": (
                sum(r["d_sell"] for r in big_up) / len(big_up) if big_up else float("nan")
            ),
            "next_day_direction_accuracy": accuracy(test_rows, "diode_next_dir"),
            "next_day_balanced_accuracy": balanced_accuracy(test_rows, "diode_next_dir"),
            "strategy_on_avoid": summarize_strategy(test_rets, diode_positions),
        },
        "mw_rc_v7_proxy": {
            "signal_days": sum(r["mwrc_next_dir"] == "UP" for r in test_rows),
            "next_day_direction_accuracy_on_signals": accuracy(test_rows, "mwrc_next_dir"),
            "next_day_balanced_accuracy_on_signals": balanced_accuracy(test_rows, "mwrc_next_dir"),
            "signal_avg_next_ret_pct": mean([r["ret_pct"] for r in test_rows if r["mwrc_next_dir"] == "UP"]),
            "non_signal_avg_next_ret_pct": mean([r["ret_pct"] for r in test_rows if r["mwrc_next_dir"] != "UP"]),
            "point_mae_pct": mean(mwrc_abs_err),
            "naive_point_mae_pct": mean(naive_abs_err),
            "strategy_signal_only": summarize_strategy(test_rets, mwrc_positions),
        },
        "buy_and_hold": summarize_strategy(test_rets, bh_positions),
        "recent_rows": records[-8:],
    }
    return result


def fmt_pct(x: float) -> str:
    return "nan" if x != x else f"{x * 100:.1f}%"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true", help="fetch current 3-month data from Naver")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    result = run(args.fetch)
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%Y%m%d_%H%M%S")
    out_json = OUT / f"{stamp}_3m_model_backtest.json"
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    d = result["diode_v5"]
    m = result["mw_rc_v7_proxy"]
    bh = result["buy_and_hold"]
    print("=== 3M KOSPI model backtest ===")
    print(f"period: {result['period']['start']}~{result['period']['end']} rows={result['period']['rows']}")
    print()
    print("[Diode v5]")
    print(f"D_sell days: {d['d_sell_days']} / OFF {d['d_sell_off_days']}")
    print(f"same-day avg ON {d['same_day_on_avg_ret_pct']:+.3f}% vs OFF {d['same_day_off_avg_ret_pct']:+.3f}%")
    print(f"same-day direction acc: {fmt_pct(d['same_day_direction_accuracy'])}, balanced {fmt_pct(d['same_day_balanced_accuracy'])}")
    print(f"big-down capture(-2% or less): {fmt_pct(d['big_down_capture_rate'])} n={d['big_down_count']}")
    print(f"next-day direction acc: {fmt_pct(d['next_day_direction_accuracy'])}, balanced {fmt_pct(d['next_day_balanced_accuracy'])}")
    print(f"strategy avoid total {d['strategy_on_avoid']['total_pct']:+.2f}%, sharpe {d['strategy_on_avoid']['sharpe']:.2f}, mdd {d['strategy_on_avoid']['mdd_pct']:.2f}%")
    print()
    print("[MW-RC v7 proxy]")
    print(f"signal days: {m['signal_days']}")
    print(f"signal avg next ret {m['signal_avg_next_ret_pct']:+.3f}% vs non-signal {m['non_signal_avg_next_ret_pct']:+.3f}%")
    print(f"signal direction acc: {fmt_pct(m['next_day_direction_accuracy_on_signals'])}, balanced {fmt_pct(m['next_day_balanced_accuracy_on_signals'])}")
    print(f"point MAE {m['point_mae_pct']:.3f}% vs naive {m['naive_point_mae_pct']:.3f}%")
    print(f"strategy signal-only total {m['strategy_signal_only']['total_pct']:+.2f}%, sharpe {m['strategy_signal_only']['sharpe']:.2f}, mdd {m['strategy_signal_only']['mdd_pct']:.2f}%")
    print()
    print(f"[Buy&Hold] total {bh['total_pct']:+.2f}%, sharpe {bh['sharpe']:.2f}, mdd {bh['mdd_pct']:.2f}%")
    print(f"saved: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
