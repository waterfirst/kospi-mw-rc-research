#!/usr/bin/env python3
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import statistics as stats
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "contest" / "backtests"
PRE_DUEL_JSON = OUT / "20260630_074108_3m_model_backtest.json"


def log(agent: str, msg: str) -> None:
    print(f"[{agent}] {msg}")


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


def coverage(rows: list[dict[str, Any]], pred_key: str) -> float:
    if not rows:
        return float("nan")
    return sum(r[pred_key] != "FLAT" for r in rows) / len(rows)


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
    sharpe = mean(strat) / sd * math.sqrt(252) if sd and not math.isnan(sd) and sd > 0 else float("nan")
    years = len(strat) / 252
    cagr = (curve[-1] ** (1 / years) - 1) * 100 if years and curve[-1] > 0 else float("nan")
    return {
        "total_pct": (curve[-1] - 1) * 100,
        "cagr_pct": cagr,
        "sharpe": sharpe,
        "mdd_pct": mdd * 100,
    }


def fmt_pct(x: float) -> str:
    return "nan" if x != x else f"{x*100:.1f}%"


def load_reference() -> dict[str, Any]:
    if PRE_DUEL_JSON.exists():
        return json.loads(PRE_DUEL_JSON.read_text(encoding="utf-8"))
    return {}


def build_records() -> list[dict[str, Any]]:
    log("Data Agent", "loading 2Y local price/flow data")
    price = parse_price_csv(DATA / "kospi_price.csv")
    flow = parse_flow_csv(DATA / "kospi_flow.csv")
    dates = sorted(set(price) & set(flow))
    closes = [price[d]["close"] for d in dates]
    rets = [0.0]
    for i in range(1, len(dates)):
        rets.append((closes[i] / closes[i - 1] - 1) * 100)

    records: list[dict[str, Any]] = []
    for i, d in enumerate(dates):
        f = flow[d]["foreign"]
        inst = flow[d]["institution"]
        indiv = flow[d]["individual"]
        rec = {
            "date": d,
            "open": price[d]["open"],
            "high": price[d]["high"],
            "low": price[d]["low"],
            "close": closes[i],
            "ret_pct": rets[i],
            "individual": indiv,
            "foreign": f,
            "institution": inst,
            "d_sell": f < 0 and inst < 0,
            "actual_dir": "UP" if rets[i] > 0.15 else ("DOWN" if rets[i] < -0.15 else "FLAT"),
        }
        rec["diode_diag_dir"] = "DOWN" if rec["d_sell"] else "UP"
        records.append(rec)
    log("Data Agent", f"matched rows={len(records)} period={records[0]['date']}~{records[-1]['date']}")
    return records


def enrich_ex_ante(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    log("Forecast Agent", "building ex-ante proxy forecasts from prior-day information")
    rows: list[dict[str, Any]] = []
    for i in range(1, len(records)):
        prev = records[i - 1]
        cur = dict(records[i])

        # Pre-duel Codex proxy core
        cur["mwrc_next_dir"] = "DOWN" if prev["d_sell"] else "UP"
        prior_selloff = prev["ret_pct"] <= -1.0
        sigma_open = (
            prev["institution"] > 0
            or prev["individual"] < 0
            or prev["foreign"] > 0
        )
        cur["mwrc_recovery_dir"] = "UP" if prior_selloff and sigma_open else "FLAT"

        # Final-model daily-core proxy
        capitulation_bounce_floor = prev["ret_pct"] <= -4.0 and prev["institution"] > 0
        weak_rebound_trap = prev["ret_pct"] >= 2.0 and prev["foreign"] < 0 and prev["institution"] <= 0
        broad_weak_but_flow_supported = prev["ret_pct"] < 0 and prev["institution"] > 0 and prev["foreign"] < 0
        panic_carry = prev["foreign"] <= -15000 and prev["institution"] <= -5000

        if weak_rebound_trap or panic_carry:
            cur["vfinal_daily_core_dir"] = "DOWN"
        elif capitulation_bounce_floor or (prior_selloff and sigma_open) or broad_weak_but_flow_supported:
            cur["vfinal_daily_core_dir"] = "UP"
        else:
            cur["vfinal_daily_core_dir"] = "FLAT"

        # Simple point proxy: only uses prior-day daily variables
        if cur["vfinal_daily_core_dir"] == "UP":
            pred_pct = min(2.4, 0.35 * abs(prev["ret_pct"]) + max(prev["institution"], 0) / 20000 * 0.8)
        elif cur["vfinal_daily_core_dir"] == "DOWN":
            pred_pct = -min(2.4, 0.25 * abs(prev["ret_pct"]) + max(-prev["foreign"], 0) / 20000 * 0.8)
        else:
            pred_pct = 0.0
        cur["vfinal_daily_core_point"] = round(prev["close"] * (1 + pred_pct / 100.0), 2)
        cur["naive_point"] = prev["close"]

        rows.append(cur)
    return rows


def evaluate(records: list[dict[str, Any]], test_rows: list[dict[str, Any]]) -> dict[str, Any]:
    log("Scoring Agent", "computing baseline and final-proxy metrics")
    diode_on = [r["ret_pct"] for r in records if r["d_sell"]]
    diode_off = [r["ret_pct"] for r in records if not r["d_sell"]]
    big_down = [r for r in records if r["ret_pct"] <= -2.0]

    diode_positions = [1.0 if not records[i - 1]["d_sell"] else 0.0 for i in range(1, len(records))]
    mwrc_signal_positions = [1.0 if r["mwrc_recovery_dir"] == "UP" else 0.0 for r in test_rows]
    vfinal_long_positions = [1.0 if r["vfinal_daily_core_dir"] == "UP" else 0.0 for r in test_rows]
    vfinal_ls_positions = [1.0 if r["vfinal_daily_core_dir"] == "UP" else (-1.0 if r["vfinal_daily_core_dir"] == "DOWN" else 0.0) for r in test_rows]
    bh_positions = [1.0 for _ in test_rows]
    test_rets = [r["ret_pct"] for r in test_rows]

    mwrc_abs_err = [abs(r["vfinal_daily_core_point"] - r["close"]) / r["close"] * 100 for r in test_rows]
    naive_abs_err = [abs(r["naive_point"] - r["close"]) / r["close"] * 100 for r in test_rows]

    return {
        "period": {
            "start": records[0]["date"],
            "end": records[-1]["date"],
            "rows": len(records),
            "test_rows": len(test_rows),
        },
        "reference_pre_duel_3m": load_reference(),
        "diode_v5_2y": {
            "d_sell_days": len(diode_on),
            "d_sell_off_days": len(diode_off),
            "same_day_on_avg_ret_pct": mean(diode_on),
            "same_day_off_avg_ret_pct": mean(diode_off),
            "same_day_spread_off_minus_on_pct": mean(diode_off) - mean(diode_on),
            "same_day_direction_accuracy": accuracy(records, "diode_diag_dir"),
            "same_day_balanced_accuracy": balanced_accuracy(records, "diode_diag_dir"),
            "big_down_capture_rate": sum(r["d_sell"] for r in big_down) / len(big_down) if big_down else float("nan"),
            "big_down_count": len(big_down),
            "next_day_direction_accuracy": accuracy(test_rows, "mwrc_next_dir"),
            "next_day_balanced_accuracy": balanced_accuracy(test_rows, "mwrc_next_dir"),
            "strategy_on_avoid": summarize_strategy(test_rets, diode_positions),
        },
        "codex_mwrc_preduel_proxy_2y": {
            "signal_days": sum(r["mwrc_recovery_dir"] == "UP" for r in test_rows),
            "coverage": coverage(test_rows, "mwrc_recovery_dir"),
            "next_day_direction_accuracy": accuracy(test_rows, "mwrc_recovery_dir"),
            "next_day_balanced_accuracy": balanced_accuracy(test_rows, "mwrc_recovery_dir"),
            "signal_avg_next_ret_pct": mean([r["ret_pct"] for r in test_rows if r["mwrc_recovery_dir"] == "UP"]),
            "non_signal_avg_next_ret_pct": mean([r["ret_pct"] for r in test_rows if r["mwrc_recovery_dir"] != "UP"]),
            "strategy_signal_only": summarize_strategy(test_rets, mwrc_signal_positions),
        },
        "codex_vfinal_daily_core_proxy_2y": {
            "signal_days_up_or_down": sum(r["vfinal_daily_core_dir"] != "FLAT" for r in test_rows),
            "coverage": coverage(test_rows, "vfinal_daily_core_dir"),
            "next_day_direction_accuracy": accuracy(test_rows, "vfinal_daily_core_dir"),
            "next_day_balanced_accuracy": balanced_accuracy(test_rows, "vfinal_daily_core_dir"),
            "up_signal_avg_next_ret_pct": mean([r["ret_pct"] for r in test_rows if r["vfinal_daily_core_dir"] == "UP"]),
            "down_signal_avg_next_ret_pct": mean([r["ret_pct"] for r in test_rows if r["vfinal_daily_core_dir"] == "DOWN"]),
            "point_mae_pct": mean(mwrc_abs_err),
            "naive_point_mae_pct": mean(naive_abs_err),
            "strategy_long_only": summarize_strategy(test_rets, vfinal_long_positions),
            "strategy_long_short": summarize_strategy(test_rets, vfinal_ls_positions),
        },
        "buy_and_hold_2y": summarize_strategy(test_rets, bh_positions),
        "recent_rows": test_rows[-10:],
        "limitations": [
            "현재 최종 실전 모델의 EWY/SOX/뉴스/장중 수급/프로그램 입력은 2년 일봉 CSV에 없어 소급 불가",
            "따라서 이 검증은 final model 전체가 아니라 daily-core proxy 검증",
            "종가/시가 실전 점예측 성능과 1:1 동일시하면 안 됨",
        ],
    }


def render_markdown(result: dict[str, Any]) -> str:
    ref = result.get("reference_pre_duel_3m", {})
    d = result["diode_v5_2y"]
    m = result["codex_mwrc_preduel_proxy_2y"]
    v = result["codex_vfinal_daily_core_proxy_2y"]
    bh = result["buy_and_hold_2y"]

    ref_m = ref.get("mw_rc_v7_proxy", {})
    ref_d = ref.get("diode_v5", {})
    ref_period = ref.get("period", {})

    return f"""# 2년 코스피 오케스트레이션 백테스트 — Codex Final Proxy 검증

## 1. 목적

- **최초 대결 시작 전 백테스트 결과**를 참고하고
- **현재 Codex 최종 모델의 백테스트 가능한 핵심 주장**을
- 과거 2년치 KOSPI 일봉+수급 데이터로 다시 검증했다.

## 2. 검증 범위

- 구간: {result['period']['start']} ~ {result['period']['end']}
- 거래일 수: {result['period']['rows']}일
- ex-ante 테스트 행 수: {result['period']['test_rows']}일

## 3. 참고 기준(대결 시작 전)

### 3-1. Claude Diode v5 (기존 604일 기준)
- 당일 분류 강점이 핵심
- pre-duel 3M 참고:
  - 당일 ON 평균 {ref_d.get('same_day_on_avg_ret_pct', float('nan')):+.3f}%
  - 당일 OFF 평균 {ref_d.get('same_day_off_avg_ret_pct', float('nan')):+.3f}%
  - 익일 방향 정확도 {fmt_pct(ref_d.get('next_day_direction_accuracy', float('nan')))}

### 3-2. Codex MW-RC v7 proxy (대결 전 3개월)
- 기준 구간: {ref_period.get('start', 'na')}~{ref_period.get('end', 'na')}
- 회복 신호일 수: {ref_m.get('signal_days', 'na')}
- 신호 방향 정확도: {fmt_pct(ref_m.get('next_day_direction_accuracy_on_signals', float('nan')))}
- 점예측 MAE: {ref_m.get('point_mae_pct', float('nan')):.3f}% vs naive {ref_m.get('naive_point_mae_pct', float('nan')):.3f}%

## 4. 이번 2년 검증 결과

### 4-1. Diode v5 2Y
- D_sell ON {d['d_sell_days']}일 / OFF {d['d_sell_off_days']}일
- 당일 ON 평균 {d['same_day_on_avg_ret_pct']:+.3f}% vs OFF {d['same_day_off_avg_ret_pct']:+.3f}%
- 당일 방향 정확도 {fmt_pct(d['same_day_direction_accuracy'])}
- 당일 balanced accuracy {fmt_pct(d['same_day_balanced_accuracy'])}
- 급락(-2% 이하) 포착률 {fmt_pct(d['big_down_capture_rate'])} (n={d['big_down_count']})
- 익일 방향 정확도 {fmt_pct(d['next_day_direction_accuracy'])}
- 익일 balanced accuracy {fmt_pct(d['next_day_balanced_accuracy'])}

### 4-2. Codex MW-RC pre-duel proxy 2Y
- 회복 신호 커버리지 {fmt_pct(m['coverage'])}
- 신호 방향 정확도 {fmt_pct(m['next_day_direction_accuracy'])}
- balanced accuracy {fmt_pct(m['next_day_balanced_accuracy'])}
- 신호일 평균 익일수익률 {m['signal_avg_next_ret_pct']:+.3f}%
- 비신호일 평균 익일수익률 {m['non_signal_avg_next_ret_pct']:+.3f}%

### 4-3. Codex vFinal daily-core proxy 2Y
- 신호 커버리지 {fmt_pct(v['coverage'])}
- 방향 정확도 {fmt_pct(v['next_day_direction_accuracy'])}
- balanced accuracy {fmt_pct(v['next_day_balanced_accuracy'])}
- UP 신호 평균 익일수익률 {v['up_signal_avg_next_ret_pct']:+.3f}%
- DOWN 신호 평균 익일수익률 {v['down_signal_avg_next_ret_pct']:+.3f}%
- 점예측 MAE {v['point_mae_pct']:.3f}% vs naive {v['naive_point_mae_pct']:.3f}%

## 5. 전략 성과

### Diode ON 회피
- 총수익 {d['strategy_on_avoid']['total_pct']:+.2f}%
- Sharpe {d['strategy_on_avoid']['sharpe']:.2f}
- MDD {d['strategy_on_avoid']['mdd_pct']:.2f}%

### Codex MW-RC pre-duel signal only
- 총수익 {m['strategy_signal_only']['total_pct']:+.2f}%
- Sharpe {m['strategy_signal_only']['sharpe']:.2f}
- MDD {m['strategy_signal_only']['mdd_pct']:.2f}%

### Codex vFinal daily-core long only
- 총수익 {v['strategy_long_only']['total_pct']:+.2f}%
- Sharpe {v['strategy_long_only']['sharpe']:.2f}
- MDD {v['strategy_long_only']['mdd_pct']:.2f}%

### Codex vFinal daily-core long/short
- 총수익 {v['strategy_long_short']['total_pct']:+.2f}%
- Sharpe {v['strategy_long_short']['sharpe']:.2f}
- MDD {v['strategy_long_short']['mdd_pct']:.2f}%

### Buy & Hold
- 총수익 {bh['total_pct']:+.2f}%
- Sharpe {bh['sharpe']:.2f}
- MDD {bh['mdd_pct']:.2f}%

## 6. 해석

1. **Diode v5는 2년 구간에서도 “당일 위험 분류기”로서 유효한지**를 확인하는 기준선 역할을 한다.
2. **대결 전 MW-RC proxy**는 3개월 특수 국면보다 2년 전체에서 더 냉정하게 평가된다.
3. **vFinal daily-core proxy**는 현재 최종 Codex 모델의 전부가 아니라,  
   일봉 수급/전일 충격만으로 소급 가능한 핵심 사고를 검증한 것이다.
4. 따라서 이 결과는 **“최종 모델의 일봉 코어가 2년치에서 버티는가”**를 보는 검증이며,  
   실전 시가/종가 모델 전체 성능과 동일하다고 말하면 과장이다.

## 7. 한 줄 판정

- **Claude Diode**: 당일 위험 경보/급락 분류 기준선으로는 여전히 강함
- **Codex pre-duel proxy**: 3개월보다 2년에서 더 냉정하게 평가해야 함
- **Codex vFinal daily-core proxy**: 최종 모델의 일부 코어는 검증 가능하지만,  
  EWY/SOX/뉴스/장중 수급이 빠진 상태라 **완전한 최종 검증은 아님**

## 8. 한계

"""


def main() -> int:
    log("Conductor", "start 2Y orchestration backtest")
    records = build_records()
    test_rows = enrich_ex_ante(records)
    result = evaluate(records, test_rows)

    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%Y%m%d_%H%M%S")
    OUT.mkdir(parents=True, exist_ok=True)
    out_json = OUT / f"{stamp}_2y_orchestrated_backtest.json"
    out_md = OUT / f"{stamp}_2y_orchestrated_backtest.md"
    result["created_at_kst"] = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="seconds")
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md = render_markdown(result) + "\n".join(f"- {x}" for x in result["limitations"]) + "\n"
    out_md.write_text(md, encoding="utf-8")

    log("Review Agent", f"saved json={out_json.name}")
    log("Review Agent", f"saved md={out_md.name}")

    v = result["codex_vfinal_daily_core_proxy_2y"]
    print("\n=== 2Y orchestrated backtest summary ===")
    print(f"period: {result['period']['start']}~{result['period']['end']} rows={result['period']['rows']}")
    print(f"vFinal daily-core coverage: {fmt_pct(v['coverage'])}")
    print(f"vFinal daily-core direction acc: {fmt_pct(v['next_day_direction_accuracy'])}")
    print(f"vFinal daily-core balanced acc: {fmt_pct(v['next_day_balanced_accuracy'])}")
    print(f"vFinal point MAE: {v['point_mae_pct']:.3f}% vs naive {v['naive_point_mae_pct']:.3f}%")
    print(f"saved: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
