#!/usr/bin/env python3
from __future__ import annotations

import csv
import datetime as dt
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "contest" / "backtests"

K_EWY = 0.58
R_RESID = 0.50


def log(agent: str, msg: str) -> None:
    print(f"[{agent}] {msg}")


def load_kospi() -> pd.DataFrame:
    rows = []
    with open(DATA / "kospi_price.csv", encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        next(r, None)
        for row in r:
            if not row or not str(row[0]).isdigit():
                continue
            rows.append(
                {
                    "date": pd.to_datetime(row[0], format="%Y%m%d"),
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                }
            )
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    df["prev_close"] = df["close"].shift(1)
    df["kospi_ret_pct"] = (df["close"] / df["prev_close"] - 1.0) * 100.0
    df["open_gap_pct"] = (df["open"] / df["prev_close"] - 1.0) * 100.0
    df["close_ret_pct"] = (df["close"] / df["prev_close"] - 1.0) * 100.0
    return df


def download_us() -> pd.DataFrame:
    start = "2023-12-15"
    end = "2026-06-30"
    tickers = ["EWY", "^SOX", "^GSPC", "^IXIC", "KRW=X"]
    log("Data Agent", "downloading EWY/SOX/S&P/Nasdaq/KRW history")
    raw = yf.download(tickers, start=start, end=end, auto_adjust=False, progress=False)
    close = raw["Close"].copy()
    close = close.rename(
        columns={
            "EWY": "EWY",
            "^SOX": "SOX",
            "^GSPC": "SPX",
            "^IXIC": "IXIC",
            "KRW=X": "KRW",
        }
    )
    close = close.reset_index().rename(columns={"Date": "us_date"})
    close["EWY_pct"] = close["EWY"].pct_change() * 100.0
    close["SOX_pct"] = close["SOX"].pct_change() * 100.0
    close["SPX_pct"] = close["SPX"].pct_change() * 100.0
    close["IXIC_pct"] = close["IXIC"].pct_change() * 100.0
    close["KRW_pct"] = close["KRW"].pct_change() * 100.0
    return close


def merge_by_last_us_day(kospi: pd.DataFrame, us: pd.DataFrame) -> pd.DataFrame:
    left = kospi.sort_values("date").copy()
    right = us.sort_values("us_date").copy()
    left["date"] = pd.to_datetime(left["date"]).astype("datetime64[ns]")
    right["us_date"] = pd.to_datetime(right["us_date"]).astype("datetime64[ns]")
    merged = pd.merge_asof(left, right, left_on="date", right_on="us_date", direction="backward", allow_exact_matches=False)
    merged["prev_kospi_ret_pct"] = merged["kospi_ret_pct"].shift(1)
    merged["prev_ewy_pct"] = merged["EWY_pct"].shift(1)
    return merged


def predict_open(df: pd.DataFrame) -> pd.DataFrame:
    log("Open Agent", "running current open-model core proxy")
    out = df.copy()
    preds = []
    pred_gap_pcts = []
    for _, r in out.iterrows():
        if pd.isna(r["prev_close"]) or pd.isna(r["EWY_pct"]):
            preds.append(np.nan)
            pred_gap_pcts.append(np.nan)
            continue
        gap = K_EWY * float(r["EWY_pct"])
        if not pd.isna(r["prev_kospi_ret_pct"]) and not pd.isna(r["prev_ewy_pct"]):
            overshoot = float(r["prev_kospi_ret_pct"]) - K_EWY * float(r["prev_ewy_pct"])
            gap += -R_RESID * overshoot
        sox_gap = 0.5 * float(r["SOX_pct"]) if not pd.isna(r["SOX_pct"]) else gap
        if not pd.isna(sox_gap) and abs(gap - sox_gap) > 2.0:
            gap = (gap + sox_gap) / 2.0
        if not pd.isna(r["KRW_pct"]) and r["KRW_pct"] > 0.5:
            gap -= min(0.4, r["KRW_pct"] * 0.3)
        gap = max(-6.0, min(6.0, gap))
        pred_gap_pcts.append(gap)
        preds.append(float(r["prev_close"]) * (1.0 + gap / 100.0))
    out["pred_open"] = preds
    out["pred_open_gap_pct"] = pred_gap_pcts
    out["open_abs_err_pct"] = (out["pred_open"] - out["open"]).abs() / out["open"] * 100.0
    out["open_actual_dir"] = np.where(out["open_gap_pct"] > 0.15, "UP", np.where(out["open_gap_pct"] < -0.15, "DOWN", "FLAT"))
    out["open_pred_dir"] = np.where(out["pred_open_gap_pct"] > 0.15, "UP", np.where(out["pred_open_gap_pct"] < -0.15, "DOWN", "FLAT"))
    return out


def direction_accuracy(actual: pd.Series, pred: pd.Series) -> float:
    mask = (actual != "FLAT") & (pred != "FLAT")
    if mask.sum() == 0:
        return float("nan")
    return float((actual[mask] == pred[mask]).mean())


def balanced_accuracy(actual: pd.Series, pred: pd.Series) -> float:
    vals = []
    for target in ["UP", "DOWN"]:
        mask = (actual == target) & (pred != "FLAT")
        if mask.sum():
            vals.append(float((pred[mask] == target).mean()))
    return sum(vals) / len(vals) if vals else float("nan")


def walkforward_close_from_open(df: pd.DataFrame, min_train: int = 60) -> pd.DataFrame:
    log("Close-from-Open Agent", "running walk-forward regression using only open gap")
    out = df.copy()
    pred_close = [np.nan] * len(out)
    pred_close_ret = [np.nan] * len(out)
    pred_dir = ["FLAT"] * len(out)
    for i in range(min_train, len(out)):
        hist = out.iloc[1:i].dropna(subset=["open_gap_pct", "close_ret_pct"])
        if len(hist) < min_train:
            continue
        x = hist["open_gap_pct"].to_numpy()
        y = hist["close_ret_pct"].to_numpy()
        x_mean = x.mean()
        y_mean = y.mean()
        denom = ((x - x_mean) ** 2).sum()
        beta = 0.0 if denom == 0 else ((x - x_mean) * (y - y_mean)).sum() / denom
        alpha = y_mean - beta * x_mean
        x_t = float(out.iloc[i]["open_gap_pct"])
        y_hat = alpha + beta * x_t
        prev_close = float(out.iloc[i]["prev_close"])
        pred = prev_close * (1.0 + y_hat / 100.0)
        pred_close[i] = pred
        pred_close_ret[i] = y_hat
        pred_dir[i] = "UP" if y_hat > 0.15 else ("DOWN" if y_hat < -0.15 else "FLAT")
    out["pred_close_from_open"] = pred_close
    out["pred_close_ret_from_open_pct"] = pred_close_ret
    out["close_abs_err_pct"] = (out["pred_close_from_open"] - out["close"]).abs() / out["close"] * 100.0
    out["close_actual_dir"] = np.where(out["close_ret_pct"] > 0.15, "UP", np.where(out["close_ret_pct"] < -0.15, "DOWN", "FLAT"))
    out["close_pred_dir"] = pred_dir
    return out


def svg_line_chart(title: str, labels: list[str], series: list[tuple[str, str, list[float]]], width: int = 1100, height: int = 320) -> str:
    pad_l, pad_r, pad_t, pad_b = 60, 20, 30, 40
    vals = [v for _, _, arr in series for v in arr if v == v]
    ymin, ymax = min(vals), max(vals)
    if ymin == ymax:
        ymin -= 1
        ymax += 1
    ymin -= (ymax - ymin) * 0.05
    ymax += (ymax - ymin) * 0.05
    n = len(labels)
    def x_pos(i: int) -> float:
        return pad_l + (width - pad_l - pad_r) * (i / max(1, n - 1))
    def y_pos(v: float) -> float:
        return pad_t + (height - pad_t - pad_b) * (1 - (v - ymin) / (ymax - ymin))
    paths = []
    for name, color, arr in series:
        pts = []
        for i, v in enumerate(arr):
            if v == v:
                pts.append(f"{x_pos(i):.2f},{y_pos(v):.2f}")
        paths.append(f'<path d="M {" L ".join(pts)}" fill="none" stroke="{color}" stroke-width="2.5"/>')
    ticks = []
    for frac in [0, 0.25, 0.5, 0.75, 1]:
        v = ymin + (ymax - ymin) * frac
        y = y_pos(v)
        ticks.append(f'<line x1="{pad_l}" y1="{y:.2f}" x2="{width-pad_r}" y2="{y:.2f}" stroke="#e5e7eb"/><text x="8" y="{y+4:.2f}" font-size="11" fill="#6b7280">{v:,.0f}</text>')
    xlabels = []
    step = max(1, n // 10)
    for i in range(0, n, step):
        xlabels.append(f'<text x="{x_pos(i):.2f}" y="{height-10}" font-size="11" text-anchor="middle" fill="#6b7280">{labels[i]}</text>')
    legend = []
    lx = pad_l
    for name, color, _ in series:
        legend.append(f'<rect x="{lx}" y="6" width="10" height="10" fill="{color}"/><text x="{lx+15}" y="15" font-size="12" fill="#374151">{name}</text>')
        lx += 150
    return f'''<svg viewBox="0 0 {width} {height}" style="width:100%;height:auto;display:block;background:#fff;border:1px solid #e5e7eb;border-radius:12px">
<text x="{pad_l}" y="20" font-size="16" font-weight="700" fill="#111827">{title}</text>
{"".join(ticks)}
<line x1="{pad_l}" y1="{height-pad_b}" x2="{width-pad_r}" y2="{height-pad_b}" stroke="#9ca3af"/>
<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{height-pad_b}" stroke="#9ca3af"/>
{"".join(paths)}
{"".join(xlabels)}
{"".join(legend)}
</svg>'''


def render_html(df: pd.DataFrame, metrics: dict[str, float], out_html: Path) -> None:
    plot = df.dropna(subset=["pred_open", "pred_close_from_open"]).copy()
    labels = [d.strftime("%y-%m") for d in plot["date"]]
    open_chart = svg_line_chart(
        "2Y 시가: 실측 vs 모델예측",
        labels,
        [
            ("Actual Open", "#2563eb", plot["open"].tolist()),
            ("Pred Open", "#f97316", plot["pred_open"].tolist()),
        ],
    )
    close_chart = svg_line_chart(
        "2Y 종가: 실측 vs '시가만 사용' 예측",
        labels,
        [
            ("Actual Close", "#16a34a", plot["close"].tolist()),
            ("Pred Close from Open", "#dc2626", plot["pred_close_from_open"].tolist()),
        ],
    )
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Open and Close-from-Open Backtest</title>
  <style>
    body{{font-family:Arial,sans-serif;background:#f8fafc;color:#111827;max-width:1200px;margin:0 auto;padding:24px;line-height:1.6}}
    .card{{background:#fff;border:1px solid #e5e7eb;border-radius:16px;padding:20px;margin-bottom:18px}}
    .grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}}
    .kpi{{font-size:30px;font-weight:800}}
    .muted{{color:#6b7280}}
    @media(max-width:900px){{.grid{{grid-template-columns:1fr}}}}
    table{{width:100%;border-collapse:collapse}}
    th,td{{padding:8px 10px;border-bottom:1px solid #e5e7eb;text-align:right}}
    th:first-child,td:first-child{{text-align:left}}
  </style>
</head>
<body>
  <div class="card">
    <h1>시가 모델 / 시가→종가 백테스트</h1>
    <p class="muted">구간: {plot['date'].min().date()} ~ {plot['date'].max().date()} · 2년 KOSPI 일봉 + EWY/SOX/KRW 과거값 사용</p>
  </div>
  <div class="grid">
    <div class="card"><div class="muted">시가 모델 MAE</div><div class="kpi">{metrics['open_mae_pct']:.3f}%</div></div>
    <div class="card"><div class="muted">시가 모델 방향정확도</div><div class="kpi">{metrics['open_dir_acc']*100:.1f}%</div></div>
    <div class="card"><div class="muted">시가→종가 MAE</div><div class="kpi">{metrics['close_mae_pct']:.3f}%</div></div>
    <div class="card"><div class="muted">시가→종가 방향정확도</div><div class="kpi">{metrics['close_dir_acc']*100:.1f}%</div></div>
  </div>
  <div class="card">{open_chart}</div>
  <div class="card">{close_chart}</div>
  <div class="card">
    <h2>핵심 판정</h2>
    <ul>
      <li>시가 모델 balanced accuracy: {metrics['open_bal_acc']*100:.1f}%</li>
      <li>시가→종가 모델 balanced accuracy: {metrics['close_bal_acc']*100:.1f}%</li>
      <li>시가→종가 naive(전일종가 고정) MAE: {metrics['close_naive_mae_pct']:.3f}%</li>
    </ul>
  </div>
</body>
</html>
"""
    out_html.write_text(html, encoding="utf-8")


def main() -> int:
    log("Conductor", "start open / close-from-open analysis")
    kospi = load_kospi()
    us = download_us()
    merged = merge_by_last_us_day(kospi, us)
    with_open = predict_open(merged)
    final = walkforward_close_from_open(with_open)

    eval_df = final.dropna(subset=["pred_open", "pred_close_from_open"]).copy()
    metrics = {
        "open_mae_pct": float(eval_df["open_abs_err_pct"].mean()),
        "open_dir_acc": direction_accuracy(eval_df["open_actual_dir"], eval_df["open_pred_dir"]),
        "open_bal_acc": balanced_accuracy(eval_df["open_actual_dir"], eval_df["open_pred_dir"]),
        "close_mae_pct": float(eval_df["close_abs_err_pct"].mean()),
        "close_dir_acc": direction_accuracy(eval_df["close_actual_dir"], eval_df["close_pred_dir"]),
        "close_bal_acc": balanced_accuracy(eval_df["close_actual_dir"], eval_df["close_pred_dir"]),
        "close_naive_mae_pct": float((eval_df["prev_close"] - eval_df["close"]).abs().div(eval_df["close"]).mul(100).mean()),
    }

    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%Y%m%d_%H%M%S")
    OUT.mkdir(parents=True, exist_ok=True)
    out_csv = OUT / f"{stamp}_open_close_from_open_timeseries.csv"
    out_json = OUT / f"{stamp}_open_close_from_open_metrics.json"
    out_html = OUT / f"{stamp}_open_close_from_open_report.html"
    eval_df[[
        "date","prev_close","open","pred_open","close","pred_close_from_open",
        "open_gap_pct","pred_open_gap_pct","close_ret_pct","pred_close_ret_from_open_pct",
        "open_abs_err_pct","close_abs_err_pct"
    ]].to_csv(out_csv, index=False)
    out_json.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    render_html(final, metrics, out_html)

    print("\n=== summary ===")
    for k, v in metrics.items():
        if "acc" in k:
            print(k, f"{v*100:.2f}%")
        else:
            print(k, f"{v:.4f}")
    print("csv", out_csv)
    print("json", out_json)
    print("html", out_html)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
