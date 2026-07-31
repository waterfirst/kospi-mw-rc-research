#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import requests


HEAD = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}
ROOT = Path(__file__).resolve().parents[1]
DAILY_LOG_DIR = ROOT / "contest" / "learning" / "daily_logs"


def now_kst() -> dt.datetime:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))


def num(x: Any) -> float:
    if x in (None, ""):
        return 0.0
    return float(str(x).replace(",", "").replace("%", "").replace("+", "").strip() or 0)


def fetch_us() -> dict[str, Any]:
    mapping = {".INX": "sp500", ".IXIC": "nasdaq", ".SOX": "sox", ".DJI": "dow"}
    out: dict[str, Any] = {}
    for symbol, name in mapping.items():
        d = requests.get(f"https://api.stock.naver.com/index/{symbol}/basic", headers=HEAD, timeout=20).json()
        out[name] = {
            "symbol": symbol,
            "close": num(d.get("closePrice")),
            "change_pct": num(d.get("fluctuationsRatio")),
            "status": d.get("marketStatus"),
            "traded_at": d.get("localTradedAt"),
        }
    d = requests.get("https://api.stock.naver.com/stock/EWY/basic", headers=HEAD, timeout=20).json()
    out["ewy"] = {
        "symbol": "EWY",
        "close": num(d.get("closePrice")),
        "change_pct": num(d.get("fluctuationsRatio")),
        "status": d.get("marketStatus"),
        "traded_at": d.get("localTradedAt"),
    }
    return out


def fetch_usdkrw() -> dict[str, Any]:
    d = requests.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/KRW=X?range=5d&interval=1d",
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20,
    ).json()
    meta = ((d.get("chart") or {}).get("result") or [{}])[0].get("meta") or {}
    closes = ((((d.get("chart") or {}).get("result") or [{}])[0].get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    prev_close = next((float(x) for x in reversed(closes[:-1]) if x is not None), 0.0) if len(closes) >= 2 else 0.0
    current = float(meta.get("regularMarketPrice") or 0.0)
    return {
        "pair": meta.get("symbol", "KRW=X"),
        "current": current,
        "previous_close": prev_close,
        "change_pct": ((current / prev_close) - 1.0) * 100.0 if prev_close else 0.0,
        "market_time": meta.get("regularMarketTime"),
    }


def fetch_kospi_day() -> dict[str, Any]:
    today = now_kst().strftime("%Y%m%d")
    start = (now_kst() - dt.timedelta(days=10)).strftime("%Y%m%d")
    url = (
        "https://api.finance.naver.com/siseJson.naver?symbol=KOSPI"
        f"&requestType=1&startTime={start}&endTime={today}&timeframe=day"
    )
    rows = json.loads(requests.get(url, headers=HEAD, timeout=20).text.strip().replace("'", '"'))
    clean = []
    for row in rows:
        if isinstance(row, list) and row and str(row[0]).isdigit():
            clean.append({
                "date": str(row[0]),
                "open": num(row[1]),
                "high": num(row[2]),
                "low": num(row[3]),
                "close": num(row[4]),
                "volume": num(row[5]) if len(row) > 5 else 0.0,
            })
    return {"last": clean[-1], "prev": clean[-2] if len(clean) >= 2 else None, "rows": clean}


def select_open_reference(day: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None, str]:
    rows = day["rows"]
    if not rows:
        raise ValueError("No KOSPI daily rows available")
    today = now_kst().strftime("%Y%m%d")
    if rows[-1]["date"] == today and len(rows) >= 2:
        return rows[-2], rows[-3] if len(rows) >= 3 else None, "previous_completed_session"
    return rows[-1], rows[-2] if len(rows) >= 2 else None, "latest_completed_session"


def fetch_domestic() -> dict[str, Any]:
    d = requests.get("https://m.stock.naver.com/api/index/KOSPI/integration", headers=HEAD, timeout=20).json()
    totals = {x.get("code"): x.get("value") for x in d.get("totalInfos", [])}
    deal = d.get("dealTrendInfo", {}) or {}
    program = d.get("programTrendInfo", {}) or {}
    updown = d.get("upDownStockInfo", {}) or {}
    stocks = {}
    for row in d.get("enrollStocks", []) or []:
        name = row.get("stockName")
        if name in {"삼성전자", "SK하이닉스"}:
            stocks[name] = {
                "close": num(row.get("closePrice")),
                "change_pct": num(row.get("fluctuationsRatio")),
            }
    return {
        "prev_close": num(totals.get("lastClosePrice")),
        "open": num(totals.get("openPrice")),
        "high": num(totals.get("highPrice")),
        "low": num(totals.get("lowPrice")),
        "foreign": num(deal.get("foreignValue")),
        "institution": num(deal.get("institutionalValue")),
        "program": num(program.get("indexTotalReal")),
        "rise": int(num(updown.get("riseCount"))),
        "fall": int(num(updown.get("fallCount"))),
        "samsung_pct": stocks.get("삼성전자", {}).get("change_pct", 0.0),
        "skhynix_pct": stocks.get("SK하이닉스", {}).get("change_pct", 0.0),
    }


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def pct_text(x: float) -> str:
    return f"{x:+.2f}%"


def bn_text(x: float) -> str:
    return f"{x / 100.0:+.1f}bn"


def split_semi_risk(us: dict[str, Any], domestic: dict[str, Any], prior_ret: float, intraday_reversal: float) -> bool:
    return (
        us["ewy"]["change_pct"] <= -0.40
        and domestic["skhynix_pct"] <= 0.30
        and domestic["program"] <= 0
        and prior_ret >= 0.015
        and intraday_reversal <= -0.006
    )


def negative_extreme_unwind_risk(
    us: dict[str, Any],
    domestic: dict[str, Any],
    prior_ret: float,
    intraday_reversal: float,
    breadth: float,
) -> bool:
    return (
        prior_ret >= 0.050
        and intraday_reversal >= 0.020
        and breadth >= 0.75
        and us["ewy"]["change_pct"] <= -2.0
        and us["sox"]["change_pct"] <= -1.5
        and domestic["samsung_pct"] >= 5.0
        and domestic["skhynix_pct"] >= 7.0
    )


def semiconductor_super_gapup_risk(
    us: dict[str, Any],
    domestic: dict[str, Any],
) -> bool:
    return (
        us["ewy"]["change_pct"] >= 5.5
        and us["sox"]["change_pct"] >= 4.5
        and us["nasdaq"]["change_pct"] >= 1.0
        and us["sp500"]["change_pct"] >= 0.5
        and domestic["foreign"] > 0
        and domestic["program"] > 0
        and domestic["samsung_pct"] >= 4.0
        and domestic["skhynix_pct"] >= 5.0
    )


def post_crash_relief_gap_rebound(
    fx: dict[str, Any],
    prior_ret: float,
    intraday_reversal: float,
    breadth: float,
    defense_strength: float,
) -> bool:
    return (
        prior_ret <= -0.055
        and intraday_reversal <= -0.055
        and fx["change_pct"] <= -0.50
        and (defense_strength > 5000 or breadth >= 0.60)
    )


def build_daily_log_payload(result: dict[str, Any], date_str: str) -> dict[str, Any]:
    flags = [f"{key}_{str(value).lower()}" for key, value in (result.get("flags") or {}).items()]
    prediction = result.get("prediction") or {}
    return {
        "date": date_str,
        "as_of_kst": result.get("as_of_kst"),
        "record_mode": "persisted_from_final_open_research",
        "model_version": result.get("model_version"),
        "regime": "preopen_open_forecast_locked",
        "inputs": result.get("inputs", {}),
        "flags": flags,
        "components": result.get("components", {}),
        "predicate_view": result.get("flags", {}),
        "predictions": {
            "open": prediction.get("open", 0.0),
            "close": 0.0,
            "range_low": prediction.get("range_low", 0.0),
            "range_high": prediction.get("range_high", 0.0),
            "confidence": prediction.get("confidence", 0.0),
        },
        "actuals": {"open": 0.0, "close": 0.0},
        "scores": {"open": 0, "close": 0, "direction": 0, "regime": 0, "total": 0},
        "failure_tags": [],
        "reflection": {
            "summary": "final_open_research 실행 시 preopen daily log를 즉시 저장했다.",
            "next_candidates": [],
        },
        "comparison": result.get("comparison", {}),
        "summary_ko": result.get("summary_ko", {}),
        "message_ko": result.get("message_ko", ""),
        "rationale": result.get("rationale", []),
        "disclaimer": "투자자문이 아니라 연구·설명 목적입니다.",
    }


def persist_daily_log(result: dict[str, Any], date_str: str) -> Path:
    DAILY_LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = DAILY_LOG_DIR / f"{date_str}.json"
    payload = build_daily_log_payload(result, date_str)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def predict() -> dict[str, Any]:
    us = fetch_us()
    fx = fetch_usdkrw()
    day = fetch_kospi_day()
    domestic = fetch_domestic()

    reference_day, prior_day, reference_mode = select_open_reference(day)
    close = reference_day["close"]
    prior_close = (prior_day or {}).get("close") or 0.0
    prior_ret = (close / prior_close - 1.0) if prior_close else 0.0
    intraday_reversal = ((reference_day["close"] / reference_day["open"]) - 1.0) if reference_day["open"] else 0.0
    breadth = domestic["rise"] / max(1, domestic["rise"] + domestic["fall"])
    defense_strength = domestic["institution"] - abs(domestic["program"]) - 0.5 * abs(min(domestic["foreign"], 0.0))

    overnight_core = (
        0.30 * (us["ewy"]["change_pct"] / 100.0)
        + 0.22 * (us["sox"]["change_pct"] / 100.0)
        + 0.18 * (us["nasdaq"]["change_pct"] / 100.0)
        + 0.12 * (us["sp500"]["change_pct"] / 100.0)
        - 0.18 * (fx["change_pct"] / 100.0)
    )

    domestic_damage = 0.0
    domestic_damage += clamp(max(0.0, -intraday_reversal) * 0.35, 0.0, 0.0035)
    domestic_damage += 0.0015 if domestic["program"] <= -8000 else 0.0
    domestic_damage += 0.0010 if defense_strength < 0 else 0.0
    domestic_damage += 0.0008 if breadth < 0.52 else 0.0

    opening_semiconductor_lead = (
        us["sox"]["change_pct"] > -0.5
        and domestic["samsung_pct"] > 1.5
        and domestic["skhynix_pct"] > 0.3
        and domestic["samsung_pct"] >= domestic["skhynix_pct"]
    )
    fx_pressure_high = fx["current"] >= 1505.0 or fx["change_pct"] >= 0.35
    split_semi_downside = split_semi_risk(us, domestic, prior_ret, intraday_reversal)
    semiconductor_super_gapup = semiconductor_super_gapup_risk(us, domestic)
    positive_extreme_gapup = semiconductor_super_gapup or (
        us["ewy"]["change_pct"] >= 4.0
        and us["sox"]["change_pct"] >= 2.0
        and us["nasdaq"]["change_pct"] >= 0.5
        and fx["change_pct"] <= -0.35
        and domestic["foreign"] > 0
        and domestic["institution"] > 0
        and domestic["program"] > 0
    )
    negative_extreme_unwind = negative_extreme_unwind_risk(
        us,
        domestic,
        prior_ret,
        intraday_reversal,
        breadth,
    )
    relief_gap_rebound = post_crash_relief_gap_rebound(
        fx,
        prior_ret,
        intraday_reversal,
        breadth,
        defense_strength,
    )

    residual_correction = 0.0
    if defense_strength > 8000 and breadth > 0.80:
        residual_correction += 0.0013
    if opening_semiconductor_lead:
        residual_correction += 0.0008
    if fx["change_pct"] <= -0.40:
        residual_correction += 0.0009
    if semiconductor_super_gapup:
        residual_correction += 0.0105
    elif positive_extreme_gapup:
        residual_correction += 0.0045
    if negative_extreme_unwind:
        residual_correction -= 0.0260
    if prior_ret >= 0.020 and intraday_reversal < -0.008:
        residual_correction -= 0.0007
    if split_semi_downside:
        residual_correction -= 0.0012

    extreme_score = max(
        abs(us["ewy"]["change_pct"]),
        abs(us["sox"]["change_pct"]),
        abs(us["nasdaq"]["change_pct"]),
        abs(us["sp500"]["change_pct"]),
        abs(fx["change_pct"]) * 2.0,
    )
    raw_open_ret = overnight_core - domestic_damage + residual_correction
    if fx_pressure_high and not semiconductor_super_gapup:
        raw_open_ret -= 0.0015
    if split_semi_downside:
        raw_open_ret -= 0.0033

    compression = 1.0
    if semiconductor_super_gapup:
        compression = 0.99
    elif positive_extreme_gapup:
        compression = 0.96
    elif negative_extreme_unwind:
        compression = 1.05
    elif extreme_score >= 3.0:
        compression = 0.72
    elif extreme_score >= 2.0:
        compression = 0.84
    open_ret = raw_open_ret * compression

    if opening_semiconductor_lead and not fx_pressure_high:
        open_ret += 0.0007
    if positive_extreme_gapup and domestic["skhynix_pct"] >= 3.0:
        open_ret += 0.0012
    if semiconductor_super_gapup and domestic["skhynix_pct"] >= 5.0:
        open_ret += 0.0040
    if relief_gap_rebound:
        open_ret += 0.018
        if defense_strength > 12000:
            open_ret += 0.004
        if breadth >= 0.60:
            open_ret += 0.003

    upper_open_cap = 0.050 if semiconductor_super_gapup else 0.035 if positive_extreme_gapup else 0.018
    lower_open_cap = -0.050 if negative_extreme_unwind else -0.018
    open_ret = clamp(open_ret, lower_open_cap, upper_open_cap)
    open_pred = round(close * (1.0 + open_ret), 2)
    band = max(45.0, round(close * (0.0055 + 0.25 * abs(open_ret)), 2))
    claude_style_inferred_open = round(close * (1.0 + 0.58 * (us["ewy"]["change_pct"] / 100.0)), 2)

    confidence = 0.58
    confidence += 0.06 if not fx_pressure_high else -0.05
    confidence += 0.05 if defense_strength > 8000 else -0.03
    confidence += 0.04 if extreme_score < 1.2 else -0.04
    confidence = clamp(confidence, 0.35, 0.78)

    rationale = [
        (
            f"EWY {pct_text(us['ewy']['change_pct'])} 단독 추종이 아니라 "
            f"SOX {pct_text(us['sox']['change_pct'])}, Nasdaq {pct_text(us['nasdaq']['change_pct'])}, "
            f"S&P {pct_text(us['sp500']['change_pct'])}를 함께 반영"
        ),
        (
            f"USD/KRW {round(fx['current'], 2):,.2f}, 전일대비 {pct_text(fx['change_pct'])}로 "
            f"{'환율 압박 완화' if not fx_pressure_high else '환율 압박 지속'}"
        ),
        (
            f"전일 국내 손상도는 외인 {bn_text(domestic['foreign'])}, 기관 {bn_text(domestic['institution'])}, "
            f"프로그램 {bn_text(domestic['program'])}, 상승비율 {breadth:.3f}이며 "
            f"잔차보정 {pct_text(residual_correction * 100.0)} 반영"
        ),
    ]

    model_stamp = now_kst().strftime("%Y-%m-%d")

    return {
        "as_of_kst": now_kst().isoformat(timespec="seconds"),
        "model_version": f"vFinal-open-{model_stamp}-multi-anchor-residual-compress",
        "inputs": {
            "sp500_pct": round(us["sp500"]["change_pct"], 2),
            "nasdaq_pct": round(us["nasdaq"]["change_pct"], 2),
            "sox_pct": round(us["sox"]["change_pct"], 2),
            "ewy_pct": round(us["ewy"]["change_pct"], 2),
            "usdkrw": round(fx["current"], 2),
            "usdkrw_pct": round(fx["change_pct"], 3),
            "reference_mode": reference_mode,
            "reference_kospi_date": reference_day["date"],
            "prior_kospi_close_date": prior_day["date"] if prior_day else None,
            "prior_kospi_close": close,
            "prior_kospi_ret_pct": round(prior_ret * 100.0, 2),
            "prior_intraday_reversal_pct": round(intraday_reversal * 100.0, 2),
            "foreign_flow_krw_bn": round(domestic["foreign"] / 100.0, 1),
            "inst_flow_krw_bn": round(domestic["institution"] / 100.0, 1),
            "program_flow_krw_bn": round(domestic["program"] / 100.0, 1),
            "breadth_rise_ratio": round(breadth, 3),
            "samsung_pct": round(domestic["samsung_pct"], 2),
            "skhynix_pct": round(domestic["skhynix_pct"], 2),
        },
        "components": {
            "overnight_core_ret": round(overnight_core, 5),
            "domestic_damage_ret": round(domestic_damage, 5),
            "residual_correction_ret": round(residual_correction, 5),
            "compression": round(compression, 2),
            "raw_open_ret": round(raw_open_ret, 5),
            "final_open_ret": round(open_ret, 5),
            "defense_strength": round(defense_strength, 1),
            "extreme_score": round(extreme_score, 3),
            "relief_gap_rebound": relief_gap_rebound,
        },
        "flags": {
            "opening_semiconductor_lead": opening_semiconductor_lead,
            "fx_pressure_high": fx_pressure_high,
            "split_semi_downside": split_semi_downside,
            "semiconductor_super_gapup": semiconductor_super_gapup,
            "positive_extreme_gapup": positive_extreme_gapup,
            "negative_extreme_unwind": negative_extreme_unwind,
            "relief_gap_rebound": relief_gap_rebound,
        },
        "prediction": {
            "open": open_pred,
            "range_low": round(open_pred - band, 2),
            "range_high": round(open_pred + band, 2),
            "confidence": round(confidence, 2),
        },
        "comparison": {
            "duel_mode": "vs_claude",
            "claude_style_assumption": "EWY_direct_transformer_k_0.58",
            "claude_style_inferred_open": claude_style_inferred_open,
            "codex_edge_note": (
                "EWY 단독 앵커가 아니라 SOX·Nasdaq·S&P·USDKRW·전일 국내 손상도·잔차보정·"
                "극단값 압축을 함께 반영"
            ),
        },
        "summary_ko": {
            "forecast_open": open_pred,
            "range_low": round(open_pred - band, 2),
            "range_high": round(open_pred + band, 2),
            "confidence": round(confidence, 2),
            "opening_semiconductor_lead": opening_semiconductor_lead,
            "fx_pressure_high": fx_pressure_high,
        },
        "message_ko": (
            f"예측값 {open_pred:.2f} / 범위 {open_pred - band:.2f}~{open_pred + band:.2f} / "
            f"confidence {confidence:.2f}. opening_semiconductor_lead는 "
            f"{str(opening_semiconductor_lead).lower()}, fx_pressure_high는 "
            f"{str(fx_pressure_high).lower()}로 판단했다."
        ),
        "rationale": rationale,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run final open research model.")
    parser.add_argument("--save-log", action="store_true", help="Persist today's preopen daily log.")
    parser.add_argument("--date", help="Override log date for --save-log (YYYY-MM-DD).")
    args = parser.parse_args()
    result = predict()
    if args.save_log:
        date_str = args.date or now_kst().strftime("%Y-%m-%d")
        path = persist_daily_log(result, date_str)
        print(f"[save_daily_log] wrote {path}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
