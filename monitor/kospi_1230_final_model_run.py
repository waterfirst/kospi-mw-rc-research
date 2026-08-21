#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import requests
from final_open_research import predict as predict_open_research


ROOT = Path(__file__).resolve().parents[1]
DAILY_LOG_DIR = ROOT / "contest" / "learning" / "daily_logs"
INTRADAY_DIR = ROOT / "contest" / "intraday"
HEAD = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}


class StaleMarketDataError(RuntimeError):
    pass


def now_kst() -> dt.datetime:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))


def num(x: Any) -> float:
    if x is None:
        return 0.0
    return float(str(x).replace(",", "").replace("%", "").replace("+", "").strip() or 0)


def signed_num(x: Any) -> float:
    if x is None:
        return 0.0
    return float(str(x).replace(",", "").replace("%", "").strip() or 0)


def sign_label(value: float) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "flat"


def fetch_realtime() -> dict[str, Any]:
    data = requests.get(
        "https://polling.finance.naver.com/api/realtime/domestic/index/KOSPI",
        headers=HEAD,
        timeout=20,
    ).json()
    item = (data.get("datas") or [{}])[0]
    return {
        "close": num(item.get("closePriceRaw") or item.get("closePrice")),
        "open": num(item.get("openPriceRaw") or item.get("openPrice")),
        "high": num(item.get("highPriceRaw") or item.get("highPrice")),
        "low": num(item.get("lowPriceRaw") or item.get("lowPrice")),
        "change_pct": signed_num(item.get("fluctuationsRatioRaw") or item.get("fluctuationsRatio")),
        "market_status": item.get("marketStatus"),
        "local_traded_at": item.get("localTradedAt"),
    }


def fetch_integration() -> dict[str, Any]:
    data = requests.get(
        "https://m.stock.naver.com/api/index/KOSPI/integration",
        headers=HEAD,
        timeout=20,
    ).json()
    totals = {x.get("code"): x.get("value") for x in data.get("totalInfos", [])}
    deal = data.get("dealTrendInfo", {}) or {}
    program = data.get("programTrendInfo", {}) or {}
    updown = data.get("upDownStockInfo", {}) or {}
    stocks = {}
    for row in data.get("enrollStocks", []) or []:
        name = row.get("stockName")
        if not name:
            continue
        stocks[name] = {
            "close": num(row.get("closePrice")),
            "change_pct": signed_num(row.get("fluctuationsRatio")),
            "local_traded_at": row.get("localTradedAt"),
        }
    return {
        "bizdate": str(deal.get("bizdate") or program.get("bizdate") or ""),
        "prev_close": num(totals.get("lastClosePrice")),
        "open": num(totals.get("openPrice")),
        "high": num(totals.get("highPrice")),
        "low": num(totals.get("lowPrice")),
        "deal": {
            "personal": signed_num(deal.get("personalValue")),
            "foreign": signed_num(deal.get("foreignValue")),
            "institution": signed_num(deal.get("institutionalValue")),
        },
        "program": {
            "index_diff": signed_num(program.get("indexDifferenceReal")),
            "non_index_diff": signed_num(program.get("indexBiDifferenceReal")),
            "total": signed_num(program.get("indexTotalReal")),
        },
        "updown": {
            "upper": int(num(updown.get("upperCount"))),
            "rise": int(num(updown.get("riseCount"))),
            "lower": int(num(updown.get("lowerCount"))),
            "fall": int(num(updown.get("fallCount"))),
            "steady": int(num(updown.get("steadyCount"))),
        },
        "stocks": stocks,
    }


def fetch_minute5(path: str, start: str, end: str) -> list[dict[str, Any]]:
    url = f"https://api.stock.naver.com/chart/{path}?startDateTime={start}&endDateTime={end}"
    return requests.get(url, headers=HEAD, timeout=20).json()


def load_daily_log(date_str: str) -> dict[str, Any]:
    path = DAILY_LOG_DIR / f"{date_str}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def restore_embedded_preopen_log(date_str: str) -> dict[str, Any] | None:
    target_date = dt.date.fromisoformat(date_str)
    prev_path = DAILY_LOG_DIR / f"{(target_date - dt.timedelta(days=1)).isoformat()}.json"
    if not prev_path.exists():
        return None
    prev_log = json.loads(prev_path.read_text(encoding="utf-8"))
    for key, block in prev_log.items():
        if not isinstance(block, dict):
            continue
        if key != "next_session_open_forecast" and not key.startswith("next_session_open_forecast"):
            continue
        session_date = block.get("session_date") or block.get("target_session_date")
        if session_date != date_str:
            continue
        pred = block.get("predictions") or block.get("prediction") or {}
        flags_map = block.get("predicate_view") or block.get("flags") or {}
        flags = [f"{name}_{str(value).lower()}" for name, value in flags_map.items()]
        return {
            "date": date_str,
            "as_of_kst": block.get("as_of_kst"),
            "record_mode": "restored_from_previous_session_embedded_preopen_forecast",
            "model_version": block.get("model_version"),
            "regime": "preopen_open_forecast_locked",
            "inputs": block.get("inputs", {}),
            "flags": flags,
            "components": block.get("components", {}),
            "predicate_view": flags_map,
            "predictions": {
                "open": pred.get("open", 0.0),
                "close": 0.0,
                "range_low": pred.get("range_low", 0.0),
                "range_high": pred.get("range_high", 0.0),
                "confidence": pred.get("confidence", 0.0),
            },
            "evaluation_status": "pending_actuals",
            "actuals": {"open": None, "close": None},
            "scores": {"open": None, "close": None, "direction": None, "regime": None, "total": None},
            "failure_tags": [],
            "reflection": {
                "summary": "전일 daily log에 내장된 next_session_open_forecast를 복원해 preopen daily log를 생성했다.",
                "next_candidates": [],
            },
            "comparison": block.get("comparison", {}),
            "message_ko": block.get("message_ko", ""),
            "rationale": block.get("rationale", []),
            "disclaimer": "투자자문이 아니라 연구·설명 목적입니다.",
        }
    return None


def ensure_daily_log(date_str: str) -> dict[str, Any]:
    path = DAILY_LOG_DIR / f"{date_str}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    restored = restore_embedded_preopen_log(date_str)
    if restored is not None:
        DAILY_LOG_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(restored, ensure_ascii=False, indent=2), encoding="utf-8")
        return restored

    open_result = predict_open_research()
    flags = []
    for key, value in (open_result.get("flags") or {}).items():
        flags.append(f"{key}_{str(value).lower()}")
    daily_log = {
        "date": date_str,
        "as_of_kst": open_result.get("as_of_kst"),
        "record_mode": "auto_generated_from_open_research_for_intraday_close_run",
        "model_version": open_result.get("model_version"),
        "regime": "preopen_generated_pending_intraday_close",
        "inputs": open_result.get("inputs", {}),
        "flags": flags,
        "components": open_result.get("components", {}),
        "predicate_view": open_result.get("flags", {}),
        "predictions": {
            "open": (open_result.get("prediction") or {}).get("open", 0.0),
            "close": 0.0,
            "range_low": (open_result.get("prediction") or {}).get("range_low", 0.0),
            "range_high": (open_result.get("prediction") or {}).get("range_high", 0.0),
            "confidence": (open_result.get("prediction") or {}).get("confidence", 0.0),
        },
        "evaluation_status": "pending_actuals",
        "actuals": {"open": None, "close": None},
        "scores": {"open": None, "close": None, "direction": None, "regime": None, "total": None},
        "failure_tags": [],
        "reflection": {
            "summary": "오늘 morning daily log가 없어서 open 연구 엔진 출력으로 기본 기록을 자동 생성했다.",
            "next_candidates": [
                "persist_preopen_daily_log_before_intraday_close_engine"
            ],
        },
        "rationale": open_result.get("rationale", []),
        "disclaimer": "투자자문이 아니라 연구·설명 목적입니다.",
    }
    DAILY_LOG_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(daily_log, ensure_ascii=False, indent=2), encoding="utf-8")
    return daily_log


def extract_market_date(value: str | None) -> str:
    if not value:
        return ""
    return str(value)[:10]


def assert_live_session_date(rt: dict[str, Any], it: dict[str, Any], expected_date: str) -> None:
    traded_date = extract_market_date(rt.get("local_traded_at"))
    bizdate = str(it.get("bizdate") or "")
    bizdate_dash = f"{bizdate[:4]}-{bizdate[4:6]}-{bizdate[6:8]}" if len(bizdate) == 8 else ""
    if traded_date == expected_date and bizdate_dash in {"", expected_date}:
        return
    raise StaleMarketDataError(
        f"stale intraday market data: expected {expected_date}, "
        f"realtime traded_date={traded_date or 'unknown'}, bizdate={bizdate_dash or bizdate or 'unknown'}"
    )


def compute_nowcast(morning: dict[str, Any]) -> dict[str, Any]:
    x = morning["inputs"]
    split_semi_downside = (
        x["ewy_pct"] <= -0.40
        and x["skhynix_pct"] <= 0.30
        and x["program_flow_krw_bn"] <= 0
        and x["prior_kospi_ret_pct"] >= 1.5
        and x["prior_intraday_reversal_pct"] <= -0.6
    )
    post_extreme_unwind = (
        x["prior_kospi_ret_pct"] >= 5.0
        and x["prior_intraday_reversal_pct"] >= 2.0
        and x["breadth_rise_ratio"] >= 0.75
        and x["ewy_pct"] <= -2.0
        and x["sox_pct"] <= -1.5
        and x["samsung_pct"] >= 5.0
        and x["skhynix_pct"] >= 7.0
    )
    post_damage_rebound_rotation = (
        x["prior_kospi_ret_pct"] <= -5.0
        and x["prior_intraday_reversal_pct"] <= -1.5
        and x["breadth_rise_ratio"] <= 0.50
        and x["foreign_flow_krw_bn"] <= -100.0
        and x["inst_flow_krw_bn"] <= -150.0
        and x["program_flow_krw_bn"] <= -100.0
        and x["ewy_pct"] >= -1.0
        and x["sox_pct"] >= -2.0
        and x["samsung_pct"] <= -5.0
        and x["skhynix_pct"] <= -8.0
    )
    semi_meltup_institution_derisk = (
        x["foreign_flow_krw_bn"] >= 100.0
        and x["program_flow_krw_bn"] >= 80.0
        and x["breadth_rise_ratio"] >= 0.72
        and x["samsung_pct"] >= 2.5
        and x["skhynix_pct"] >= 3.5
        and x["inst_flow_krw_bn"] <= 20.0
    )
    broad_selloff_institution_derisk = (
        x["breadth_rise_ratio"] <= 0.35
        and x["foreign_flow_krw_bn"] <= -180.0
        and x["program_flow_krw_bn"] <= -180.0
        and x["samsung_pct"] <= -6.0
        and x["skhynix_pct"] <= -6.0
        and x["sp500_pct"] <= -1.0
        and x["nasdaq_pct"] <= -1.5
    )
    foreign_score = (
        0.60 * x["ewy_pct"]
        + 0.50 * x["sox_pct"]
        + 0.30 * x["nasdaq_pct"]
        + 0.20 * x["sp500_pct"]
        - 0.80 * x["usdkrw_pct"]
        + 0.15 * x["samsung_pct"]
        + 0.10 * x["skhynix_pct"]
    )
    inst_score = (
        0.55 * abs(min(x["prior_intraday_reversal_pct"], 0.0))
        + 0.10 * max(0.0, x["breadth_rise_ratio"] - 0.50) * 10.0
        + 0.04 * max(0.0, x["samsung_pct"])
        + 0.02 * abs(min(x["foreign_flow_krw_bn"], 0.0))
        - 0.01 * max(0.0, x["inst_flow_krw_bn"])
    )
    program_score = (
        0.35 * x["sox_pct"]
        + 0.25 * x["nasdaq_pct"]
        + 0.10 * x["sp500_pct"]
        - 0.45 * abs(min(x["ewy_pct"], 0.0))
        - 0.15 * abs(min(x["program_flow_krw_bn"], 0.0))
    )
    if split_semi_downside:
        foreign_score -= 0.75
        inst_score -= 0.90
    if post_extreme_unwind:
        inst_score -= 0.95
    if post_damage_rebound_rotation:
        foreign_score += 6.50
        inst_score -= 6.00
        program_score += 25.00
    if semi_meltup_institution_derisk:
        inst_score -= 2.80
        program_score += 2.40
    if broad_selloff_institution_derisk:
        inst_score -= 5.25
    return {
        "foreign": {"score": round(foreign_score, 4), "sign": sign_label(foreign_score)},
        "institution": {"score": round(inst_score, 4), "sign": sign_label(inst_score)},
        "program": {"score": round(program_score, 4), "sign": sign_label(program_score)},
    }


def last_price_change(minute_rows: list[dict[str, Any]], bars_back: int) -> float:
    if len(minute_rows) <= bars_back:
        return 0.0
    return float(minute_rows[-1]["currentPrice"]) - float(minute_rows[-(bars_back + 1)]["currentPrice"])


def detect_flow_reversal_squeeze(
    rt: dict[str, Any],
    it: dict[str, Any],
    mismatch_count: int,
    low_recovery_ratio: float,
    price_accel_10m: float,
    price_accel_20m: float,
) -> bool:
    return (
        mismatch_count >= 2
        and it["deal"]["foreign"] >= 2000
        and it["deal"]["institution"] >= 15000
        and it["program"]["total"] >= 2000
        and low_recovery_ratio >= 0.28
        and price_accel_10m >= 40
        and price_accel_20m >= 20
        and (rt["close"] - rt["low"]) >= 120
    )


def detect_parabolic_exhaustion_risk(
    rt: dict[str, Any],
    it: dict[str, Any],
    breadth: float,
    semis_rel: float,
    low_recovery_ratio: float,
    price_accel_10m: float,
    price_accel_20m: float,
) -> bool:
    return (
        rt["change_pct"] >= 6.0
        and abs(rt["open"] - rt["low"]) <= 3.0
        and low_recovery_ratio >= 0.92
        and breadth >= 0.45
        and semis_rel >= 1.0
        and price_accel_10m >= 15.0
        and price_accel_20m >= 20.0
        and it["program"]["total"] >= 12000
    )


def detect_midday_blowoff_reversal_risk(
    rt: dict[str, Any],
    it: dict[str, Any],
    breadth: float,
    semis_rel: float,
    low_recovery_ratio: float,
    price_accel_10m: float,
    price_accel_20m: float,
) -> bool:
    prev_close = max(it["prev_close"], 1.0)
    gap_from_prev = rt["open"] / prev_close - 1.0
    fade_from_high = rt["high"] - rt["close"]
    return (
        gap_from_prev >= 0.040
        and rt["change_pct"] >= 4.0
        and low_recovery_ratio <= 0.42
        and breadth <= 0.60
        and semis_rel <= 1.0
        and price_accel_10m >= 12.0
        and price_accel_20m >= 45.0
        and fade_from_high >= 80.0
        and it["program"]["total"] >= 10000
    )


def detect_concentrated_rally_late_fade_risk(
    it: dict[str, Any],
    breadth: float,
    semis_rel: float,
    low_recovery_ratio: float,
    price_accel_10m: float,
    price_accel_20m: float,
) -> bool:
    """Flag a narrow, fully recovered noon rally that has faded late twice."""
    return (
        breadth <= 0.25
        and semis_rel >= 1.0
        and low_recovery_ratio >= 0.95
        and price_accel_10m > 0.0
        and price_accel_20m > 0.0
        and it["program"]["total"] >= 2500
    )


def compute_rebound_credit(rt: dict[str, Any], it: dict[str, Any]) -> float:
    credit = (
        max(0.0, rt["open"] - rt["close"]) * 0.55
        + max(0.0, rt["close"] - rt["low"]) * 0.40
        + max(0.0, it["deal"]["institution"]) * 0.003
        + max(0.0, it["deal"]["foreign"]) * 0.0015
        + max(0.0, it["program"]["total"]) * 0.002
    )
    return min(220.0, credit)


def compute_panic_stabilization_credit(
    rt: dict[str, Any],
    it: dict[str, Any],
    mismatch_count: int,
    avalanche_sell: bool,
    low_recovery_ratio: float,
    price_accel_20m: float,
) -> float:
    if not avalanche_sell:
        return 0.0
    if mismatch_count != 0:
        return 0.0
    if it["deal"]["institution"] <= 0:
        return 0.0
    if price_accel_20m < 10.0:
        return 0.0
    if low_recovery_ratio > 0.10:
        return 0.0
    credit = (
        92.0
        + max(0.0, price_accel_20m - 10.0) * 1.6
        + min(18.0, max(0.0, it["deal"]["institution"]) * 0.004)
        + min(14.0, max(0.0, rt["close"] - rt["low"]) * 0.35)
    )
    return min(140.0, credit)


def detect_crash_shortcover_support(
    rt: dict[str, Any],
    it: dict[str, Any],
    mismatch_count: int,
    avalanche_sell: bool,
    crash_continuation: bool,
    low_recovery_ratio: float,
    semis_rel: float,
) -> bool:
    return (
        crash_continuation
        and not avalanche_sell
        and mismatch_count <= 1
        and it["deal"]["institution"] >= 15000
        and it["program"]["total"] >= 2500
        and low_recovery_ratio <= 0.05
        and semis_rel <= -2.0
        and rt["close"] <= it["prev_close"] * 0.93
    )


def compute_crash_shortcover_credit(
    rt: dict[str, Any],
    it: dict[str, Any],
    low_recovery_ratio: float,
) -> float:
    oversold_gap = max(0.0, it["prev_close"] * 0.93 - rt["close"])
    credit = (
        100.0
        + min(32.0, max(0.0, it["deal"]["institution"]) * 0.0013)
        + min(28.0, max(0.0, it["program"]["total"]) * 0.005)
        + min(30.0, oversold_gap * 0.55)
        + min(18.0, max(0.0, 0.05 - low_recovery_ratio) * 180.0)
    )
    return min(190.0, credit)


def compute_forecast(morning: dict[str, Any]) -> dict[str, Any]:
    rt = fetch_realtime()
    it = fetch_integration()
    assert_live_session_date(rt, it, now_kst().strftime("%Y-%m-%d"))
    date_compact = now_kst().strftime("%Y%m%d")
    minute_kospi = fetch_minute5("domestic/index/KOSPI/minute5", f"{date_compact}0900", f"{date_compact}1235")
    minute_ss = fetch_minute5("domestic/item/005930/minute5", f"{date_compact}0900", f"{date_compact}1235")
    minute_sk = fetch_minute5("domestic/item/000660/minute5", f"{date_compact}0900", f"{date_compact}1235")

    nowcast = compute_nowcast(morning)
    actual_signs = {
        "foreign": sign_label(it["deal"]["foreign"]),
        "institution": sign_label(it["deal"]["institution"]),
        "program": sign_label(it["program"]["total"]),
    }
    mismatch = {
        key: nowcast[key]["sign"] != actual_signs[key]
        for key in ("foreign", "institution", "program")
    }
    mismatch_count = sum(1 for v in mismatch.values() if v)

    breadth = (it["updown"]["rise"] - it["updown"]["fall"]) / max(it["updown"]["rise"] + it["updown"]["fall"], 1)
    low_recovery_ratio = (rt["close"] - rt["low"]) / max(rt["high"] - rt["low"], 1.0)
    mid_price = (rt["high"] + rt["low"]) / 2.0
    samsung_pct = it["stocks"].get("삼성전자", {}).get("change_pct", 0.0)
    skhynix_pct = it["stocks"].get("SK하이닉스", {}).get("change_pct", 0.0)
    samsung_rel = samsung_pct - rt["change_pct"]
    skhynix_rel = skhynix_pct - rt["change_pct"]
    semis_rel = 0.45 * samsung_rel + 0.55 * skhynix_rel

    price_accel_10m = last_price_change(minute_kospi, 2)
    price_accel_20m = last_price_change(minute_kospi, 4)
    samsung_accel_10m = last_price_change(minute_ss, 2)
    skhynix_accel_10m = last_price_change(minute_sk, 2)

    institution_absorption = (
        it["deal"]["institution"] >= 8000
        and breadth >= -0.10
        and low_recovery_ratio >= 0.35
        and rt["close"] >= mid_price
    )
    avalanche_sell = (
        it["deal"]["foreign"] <= -15000
        and it["program"]["total"] <= -12000
        and breadth <= -0.25
        and low_recovery_ratio <= 0.18
    )
    crash_continuation = (
        avalanche_sell
        or (rt["close"] <= it["prev_close"] * 0.94 and not institution_absorption)
        or (breadth <= -0.35 and semis_rel <= -2.0 and low_recovery_ratio <= 0.20)
    )
    program_drag_risk = (
        it["program"]["total"] <= -10000
        and semis_rel < 0
        and price_accel_10m < 0
    )
    semis_defensive_rebound = (
        not avalanche_sell
        and not crash_continuation
        and not program_drag_risk
        and mismatch_count == 0
        and semis_rel >= 0.80
        and low_recovery_ratio >= 0.28
        and price_accel_20m >= -20.0
        and it["deal"]["institution"] >= 0
    )
    flow_reversal_squeeze = detect_flow_reversal_squeeze(
        rt,
        it,
        mismatch_count,
        low_recovery_ratio,
        price_accel_10m,
        price_accel_20m,
    )
    parabolic_exhaustion_risk = detect_parabolic_exhaustion_risk(
        rt,
        it,
        breadth,
        semis_rel,
        low_recovery_ratio,
        price_accel_10m,
        price_accel_20m,
    )
    midday_blowoff_reversal_risk = detect_midday_blowoff_reversal_risk(
        rt,
        it,
        breadth,
        semis_rel,
        low_recovery_ratio,
        price_accel_10m,
        price_accel_20m,
    )
    concentrated_rally_late_fade_risk = detect_concentrated_rally_late_fade_risk(
        it,
        breadth,
        semis_rel,
        low_recovery_ratio,
        price_accel_10m,
        price_accel_20m,
    )
    semis_meltup_continuation = (
        not avalanche_sell
        and not crash_continuation
        and not program_drag_risk
        and mismatch_count <= 1
        and semis_rel >= 6.0
        and low_recovery_ratio >= 0.78
        and rt["close"] >= it["prev_close"] * 1.12
        and it["deal"]["foreign"] >= 30000
        and it["program"]["total"] >= 20000
        and breadth >= 0.45
        and price_accel_20m >= 0.0
        and not parabolic_exhaustion_risk
        and not midday_blowoff_reversal_risk
    )

    foreign_drag = max(0.0, -it["deal"]["foreign"] - 10000.0) / 1000.0 * 1.6
    inst_support = max(0.0, it["deal"]["institution"]) / 1000.0 * 1.2
    program_drag = max(0.0, -it["program"]["total"] - 8000.0) / 1000.0 * 1.4
    breadth_drag = max(0.0, -breadth - 0.10) * 36.0
    semi_drag = max(0.0, -semis_rel - 0.50) * 4.5
    recovery_drag = max(0.0, 0.25 - low_recovery_ratio) * 42.0
    accel_drag = max(0.0, -price_accel_10m) * 0.80 + max(0.0, -price_accel_20m) * 0.45
    event_drag = (18.0 if avalanche_sell else 0.0) + (12.0 if crash_continuation else 0.0) + (8.0 if program_drag_risk else 0.0)
    raw_forecast = rt["close"] - foreign_drag - program_drag - breadth_drag - semi_drag - recovery_drag - accel_drag - event_drag + inst_support
    rebound_credit = compute_rebound_credit(rt, it) if flow_reversal_squeeze else 0.0
    raw_forecast += rebound_credit
    panic_stabilization_credit = compute_panic_stabilization_credit(
        rt,
        it,
        mismatch_count,
        avalanche_sell,
        low_recovery_ratio,
        price_accel_20m,
    )
    raw_forecast += panic_stabilization_credit
    crash_shortcover_support = detect_crash_shortcover_support(
        rt,
        it,
        mismatch_count,
        avalanche_sell,
        crash_continuation,
        low_recovery_ratio,
        semis_rel,
    )
    crash_shortcover_credit = 0.0
    if crash_shortcover_support:
        crash_shortcover_credit = compute_crash_shortcover_credit(
            rt,
            it,
            low_recovery_ratio,
        )
        raw_forecast += crash_shortcover_credit
    semis_defensive_credit = 0.0
    if semis_defensive_rebound:
        semis_defensive_credit = min(
            110.0,
            max(0.0, rt["open"] - rt["close"]) * 0.42
            + max(0.0, rt["close"] - rt["low"]) * 0.22
            + max(0.0, semis_rel - 0.75) * 24.0
            + max(0.0, it["deal"]["institution"]) * 0.004
        )
        raw_forecast += semis_defensive_credit
    semis_meltup_credit = 0.0
    if semis_meltup_continuation:
        semis_meltup_credit = min(
            220.0,
            max(0.0, rt["close"] - rt["open"]) * 0.22
            + max(0.0, rt["close"] - rt["low"]) * 0.10
            + max(0.0, semis_rel - 5.5) * 24.0
            + max(0.0, it["deal"]["foreign"] - 30000.0) * 0.0015
            + max(0.0, it["program"]["total"] - 20000.0) * 0.0012
        )
        raw_forecast += semis_meltup_credit
    exhaustion_drag = 0.0
    if parabolic_exhaustion_risk:
        exhaustion_drag = min(
            140.0,
            max(0.0, rt["close"] - rt["open"]) * 0.34
            + max(0.0, rt["close"] - it["prev_close"] * 1.06) * 0.10,
        )
        raw_forecast -= exhaustion_drag
    if midday_blowoff_reversal_risk:
        fade_from_high = max(0.0, rt["high"] - rt["close"])
        blowoff_drag = min(
            260.0,
            fade_from_high * 1.65
            + max(0.0, 0.45 - low_recovery_ratio) * 140.0
            + max(0.0, price_accel_20m - 45.0) * 1.10
            + max(0.0, (rt["open"] / max(it["prev_close"], 1.0) - 1.0) - 0.04) * 4000.0
            + max(0.0, it["program"]["total"] - 10000.0) * 0.009
        )
        exhaustion_drag = max(exhaustion_drag, round(blowoff_drag, 2))
        raw_forecast -= blowoff_drag
    concentrated_rally_fade_drag = 0.0
    if concentrated_rally_late_fade_risk:
        # Only two observations (2026-08-11/12): keep this a small, fixed
        # correction rather than fitting a level-specific formula.
        concentrated_rally_fade_drag = 55.0
        raw_forecast -= concentrated_rally_fade_drag

    upper_extension = (
        260.0 if flow_reversal_squeeze
        else 180.0 if crash_shortcover_support
        else 240.0 if semis_meltup_continuation
        else 95.0 if semis_defensive_rebound
        else 35.0
    )
    forecast_close = round(max(rt["low"] - 180.0, min(rt["close"] + upper_extension, raw_forecast)))
    range_low = round(min(
        forecast_close - (
            90.0 if flow_reversal_squeeze
            else 85.0 if crash_shortcover_support
            else 85.0 if semis_meltup_continuation
            else 75.0 if semis_defensive_rebound
            else 70.0
        ),
        rt["close"] - 10.0,
    ))
    range_high_cap = rt["close"] + (
        260.0 if flow_reversal_squeeze
        else 185.0 if crash_shortcover_support
        else 255.0 if semis_meltup_continuation
        else 105.0 if semis_defensive_rebound
        else 25.0
    )
    range_high = round(min(
        range_high_cap,
        forecast_close + (
            90.0 if flow_reversal_squeeze
            else 95.0 if crash_shortcover_support
            else 105.0 if semis_meltup_continuation
            else 80.0 if semis_defensive_rebound
            else 65.0
        ),
    ))
    if range_high <= range_low:
        range_high = range_low + 30

    regime = (
        "flow_reversal_squeeze" if flow_reversal_squeeze
        else "avalanche_sell" if avalanche_sell
        else "institution_absorption" if institution_absorption
        else "crash_continuation" if crash_continuation
        else "semis_meltup_continuation" if semis_meltup_continuation
        else "weak_drift"
    )
    confidence = 0.62
    confidence -= 0.08 * mismatch_count
    if flow_reversal_squeeze:
        confidence += 0.10
    if semis_meltup_continuation:
        confidence += 0.06
    if parabolic_exhaustion_risk:
        confidence -= 0.04
    if midday_blowoff_reversal_risk:
        confidence -= 0.04
    if concentrated_rally_late_fade_risk:
        confidence -= 0.03
    if crash_continuation:
        confidence -= 0.03
    if low_recovery_ratio <= 0.05:
        confidence -= 0.03
    if not minute_kospi:
        confidence -= 0.05
    confidence = round(max(0.25, min(0.82, confidence)), 2)

    flow_parts = []
    for label, value in (
        ("외국인", it["deal"]["foreign"]),
        ("기관", it["deal"]["institution"]),
        ("프로그램", it["program"]["total"]),
    ):
        if value > 0:
            flow_parts.append(f"{label} 순매수")
        elif value < 0:
            flow_parts.append(f"{label} 순매도")
        else:
            flow_parts.append(f"{label} 중립")
    reasons = [
        (
            "·".join(flow_parts) + f", nowcast 부호 일치 {3 - mismatch_count}/3로 신뢰도 조정"
            + (" / late flow reversal 감지" if flow_reversal_squeeze else "")
        ),
        (
            f"breadth {breadth:.2f}로 시장 전반은 약하지만 "
            f"삼성전자 상대강도 {samsung_rel:+.2f}pt, SK하이닉스 상대강도 {skhynix_rel:+.2f}pt로 반도체 내부 차별화가 큼"
        ),
        (
            f"저가 회복률 {low_recovery_ratio:.2f}, 최근 10~20분 가속도 "
            f"{price_accel_10m:+.1f}/{price_accel_20m:+.1f}pt, "
            f"institution_absorption={institution_absorption}, crash_continuation={crash_continuation}, "
            f"program_drag_risk={program_drag_risk}, crash_shortcover_support={crash_shortcover_support}, "
            f"flow_reversal_squeeze={flow_reversal_squeeze}, "
            f"parabolic_exhaustion_risk={parabolic_exhaustion_risk}"
        ),
    ]

    return {
        "as_of_kst": now_kst().isoformat(timespec="seconds"),
        "snapshot": {
            "realtime": rt,
            "integration": it,
        },
        "nowcast_check": {
            "predicted_signs": nowcast,
            "actual_signs": actual_signs,
            "mismatch": mismatch,
            "mismatch_count": mismatch_count,
        },
        "features": {
            "breadth": round(breadth, 4),
            "samsung_relative_strength": round(samsung_rel, 4),
            "skhynix_relative_strength": round(skhynix_rel, 4),
            "semis_relative_strength_weighted": round(semis_rel, 4),
            "low_recovery_ratio": round(low_recovery_ratio, 4),
            "institution_absorption": institution_absorption,
            "avalanche_sell": avalanche_sell,
            "crash_continuation": crash_continuation,
            "program_drag_risk": program_drag_risk,
            "semis_defensive_rebound": semis_defensive_rebound,
            "semis_meltup_continuation": semis_meltup_continuation,
            "crash_shortcover_support": crash_shortcover_support,
            "flow_reversal_squeeze": flow_reversal_squeeze,
            "parabolic_exhaustion_risk": parabolic_exhaustion_risk,
            "midday_blowoff_reversal_risk": midday_blowoff_reversal_risk,
            "concentrated_rally_late_fade_risk": concentrated_rally_late_fade_risk,
            "rebound_credit": round(rebound_credit, 2),
            "panic_stabilization_credit": round(panic_stabilization_credit, 2),
            "crash_shortcover_credit": round(crash_shortcover_credit, 2),
            "semis_defensive_credit": round(semis_defensive_credit, 2),
            "semis_meltup_credit": round(semis_meltup_credit, 2),
            "exhaustion_drag": round(exhaustion_drag, 2),
            "concentrated_rally_fade_drag": round(concentrated_rally_fade_drag, 2),
            "recent_price_acceleration_10m_pts": round(price_accel_10m, 2),
            "recent_price_acceleration_20m_pts": round(price_accel_20m, 2),
            "samsung_acceleration_10m_krw": round(samsung_accel_10m, 2),
            "skhynix_acceleration_10m_krw": round(skhynix_accel_10m, 2),
        },
        "prediction": {
            "model_version": "vFinal-close-2026-07-29-crash-shortcover-v3",
            "forecast_close": forecast_close,
            "range_low": range_low,
            "range_high": range_high,
            "regime": regime,
            "confidence": confidence,
            "reasons_top3": reasons,
        },
        "disclaimer": "투자자문이 아니라 연구·설명 목적입니다.",
    }


def render_report(result: dict[str, Any]) -> str:
    p = result["prediction"]
    n = result["nowcast_check"]
    f = result["features"]
    return "\n".join(
        [
            f"[Codex 최종모델] KOSPI 12:30 종가 예측 ({result['as_of_kst'][11:16]} KST)",
            f"예측 종가: {p['forecast_close']:,}",
            f"범위: {p['range_low']:,} ~ {p['range_high']:,}",
            f"레짐: {p['regime']}",
            f"confidence: {p['confidence']:.2f}",
            f"nowcast 부호 일치: {3 - n['mismatch_count']}/3",
            f"핵심 1: {p['reasons_top3'][0]}",
            f"핵심 2: {p['reasons_top3'][1]}",
            f"핵심 3: {p['reasons_top3'][2]}",
            "투자자문이 아니라 연구·설명 목적입니다.",
        ]
    )


def save_outputs(result: dict[str, Any]) -> tuple[Path, Path, Path]:
    DAILY_LOG_DIR.mkdir(parents=True, exist_ok=True)
    INTRADAY_DIR.mkdir(parents=True, exist_ok=True)
    date_dash = now_kst().strftime("%Y-%m-%d")
    date_compact = now_kst().strftime("%Y%m%d")

    daily_log_path = DAILY_LOG_DIR / f"{date_dash}.json"
    daily_log = load_daily_log(date_dash)
    daily_log["intraday_close_1230"] = result
    daily_log_path.write_text(json.dumps(daily_log, ensure_ascii=False, indent=2), encoding="utf-8")

    intraday_json = INTRADAY_DIR / f"{date_compact}_1230_final_model_forecast.json"
    intraday_txt = INTRADAY_DIR / f"{date_compact}_1230_final_model_forecast.txt"
    intraday_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    intraday_txt.write_text(render_report(result), encoding="utf-8")
    return daily_log_path, intraday_json, intraday_txt


def main() -> int:
    morning = ensure_daily_log(now_kst().strftime("%Y-%m-%d"))
    try:
        result = compute_forecast(morning)
    except StaleMarketDataError as e:
        print(json.dumps(
            {
                "status": "error",
                "reason": "stale_market_data",
                "message": str(e),
                "today_kst": now_kst().strftime("%Y-%m-%d"),
            },
            ensure_ascii=False,
            indent=2,
        ))
        return 1
    daily_log_path, intraday_json, intraday_txt = save_outputs(result)
    print(json.dumps(
        {
            "status": "ok",
            "daily_log": str(daily_log_path),
            "intraday_json": str(intraday_json),
            "intraday_txt": str(intraday_txt),
            "report": render_report(result),
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
