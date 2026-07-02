#!/usr/bin/env python3
"""
Robust 12:30 KOSPI close forecaster.

Uses Naver realtime/integration endpoints that expose current index, open/high/low,
flows, program trend, and key enrolled stocks. Designed for low-token operation:
deterministic forecast first, optional local GLM audit second.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "contest" / "intraday"
HEAD = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}


def now_kst() -> dt.datetime:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))


def num(x: Any) -> float:
    if x is None:
        return 0.0
    return float(str(x).replace(",", "").replace("%", "").replace("+", "").strip() or 0)


def signed_num(x: Any) -> float:
    if x is None:
        return 0.0
    s = str(x).replace(",", "").replace("%", "").strip()
    return float(s or 0)


def fetch_realtime() -> dict[str, Any]:
    url = "https://polling.finance.naver.com/api/realtime/domestic/index/KOSPI"
    data = requests.get(url, headers=HEAD, timeout=15).json()
    item = (data.get("datas") or [{}])[0]
    return {
        "close": num(item.get("closePriceRaw") or item.get("closePrice")),
        "open": num(item.get("openPriceRaw") or item.get("openPrice")),
        "high": num(item.get("highPriceRaw") or item.get("highPrice")),
        "low": num(item.get("lowPriceRaw") or item.get("lowPrice")),
        "change_pct": signed_num(item.get("fluctuationsRatioRaw") or item.get("fluctuationsRatio")),
        "prev_delta": signed_num(item.get("compareToPreviousClosePriceRaw") or item.get("compareToPreviousClosePrice")),
        "volume_raw": num(item.get("accumulatedTradingVolumeRaw")),
        "trading_value_raw": num(item.get("accumulatedTradingValueRaw")),
        "market_status": item.get("marketStatus"),
        "local_traded_at": item.get("localTradedAt"),
    }


def fetch_integration() -> dict[str, Any]:
    url = "https://m.stock.naver.com/api/index/KOSPI/integration"
    data = requests.get(url, headers=HEAD, timeout=15).json()
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
            "code": row.get("itemCode"),
            "close": num(row.get("closePrice")),
            "change_pct": signed_num(row.get("fluctuationsRatio")),
            "delta": signed_num(row.get("compareToPreviousClosePrice")),
        }
    return {
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


def fetch_us() -> dict[str, Any]:
    out = {}
    for symbol, name in {".INX": "SP500", ".IXIC": "NASDAQ", ".SOX": "SOX", ".DJI": "DOW"}.items():
        try:
            b = requests.get(f"https://api.stock.naver.com/index/{symbol}/basic", headers=HEAD, timeout=10).json()
            out[name] = {
                "close": num(b.get("closePrice")),
                "change_pct": signed_num(b.get("fluctuationsRatio")),
                "market_status": b.get("marketStatus"),
            }
        except Exception as exc:
            out[name] = {"error": repr(exc)}
    return out


def deterministic_forecast(snapshot: dict[str, Any]) -> dict[str, Any]:
    rt = snapshot["realtime"]
    it = snapshot["integration"]
    us = snapshot["us"]
    close = rt["close"]
    prev = it["prev_close"] or 8476.48
    open_ = rt["open"]
    high = rt["high"]
    low = rt["low"]
    foreign = it["deal"]["foreign"]
    inst = it["deal"]["institution"]
    program_total = it["program"]["total"]
    rise = it["updown"]["rise"]
    fall = it["updown"]["fall"]
    breadth = (rise - fall) / max(rise + fall, 1)
    samsung_pct = it["stocks"].get("삼성전자", {}).get("change_pct", 0.0)
    hynix_pct = it["stocks"].get("SK하이닉스", {}).get("change_pct", 0.0)
    sox = us.get("SOX", {}).get("change_pct", 0.0) or 0.0
    nasdaq = us.get("NASDAQ", {}).get("change_pct", 0.0) or 0.0

    # Morning structure: big gap that failed quickly is bearish for the close
    # unless foreign/program flow turns strongly positive.
    gap_fail = max(0.0, open_ - close)
    low_recovery = close - low
    semis = 0.55 * samsung_pct + 0.45 * hynix_pct
    us_tailwind = 0.20 * sox + 0.10 * nasdaq
    flow_score = 0.000010 * foreign + 0.000008 * inst + 0.000005 * program_total
    breadth_score = 35.0 * breadth
    semi_score = 18.0 * semis
    us_score = 8.0 * us_tailwind
    gap_fail_penalty = 0.38 * gap_fail
    recovery_credit = 0.18 * low_recovery

    raw = (
        close
        - gap_fail_penalty
        + recovery_credit
        + breadth_score
        + semi_score
        + us_score
        + flow_score
    )

    # Clamp: normal days should not overreact to one print, but crash-continuation
    # days must be allowed to move far below the previous close.
    crash_continuation = (
        close <= prev * 0.97
        or (foreign <= -25000 and program_total <= -15000)
        or low <= prev * 0.94
    )
    if crash_continuation:
        lower = low - 45
        upper = min(high + 20, prev + 40)
    else:
        lower = max(low - 35, prev - 160)
        upper = min(high + 20, prev + 160)
    forecast = round(max(lower, min(upper, raw)))

    risk_flags = []
    if gap_fail > 80:
        risk_flags.append("gap_failed")
    if foreign < 0:
        risk_flags.append("foreign_sell")
    if program_total < 0:
        risk_flags.append("program_sell")
    if samsung_pct < 0:
        risk_flags.append("samsung_weak")
    if breadth > 0.5:
        risk_flags.append("broad_market_strong")
    if crash_continuation:
        risk_flags.append("crash_continuation")

    return {
        "forecast_close": forecast,
        "range": [round(forecast - 55), round(forecast + 60)],
        "confidence": 0.52 if len(risk_flags) >= 3 else 0.58,
        "risk_flags": risk_flags,
        "components": {
            "current": close,
            "prev_close": prev,
            "open": open_,
            "high": high,
            "low": low,
            "gap_fail": round(gap_fail, 2),
            "low_recovery": round(low_recovery, 2),
            "breadth": round(breadth, 3),
            "semis_pct_proxy": round(semis, 3),
            "flow_score": round(flow_score, 2),
            "breadth_score": round(breadth_score, 2),
            "semi_score": round(semi_score, 2),
            "us_score": round(us_score, 2),
            "gap_fail_penalty": round(gap_fail_penalty, 2),
            "recovery_credit": round(recovery_credit, 2),
            "raw": round(raw, 2),
            "crash_continuation": crash_continuation,
        },
    }


def local_glm_audit(snapshot: dict[str, Any], forecast: dict[str, Any]) -> dict[str, Any]:
    prompt = {
        "task": "Audit KOSPI close forecast. Return compact JSON only.",
        "snapshot": {
            "realtime": snapshot["realtime"],
            "deal": snapshot["integration"]["deal"],
            "program": snapshot["integration"]["program"],
            "updown": snapshot["integration"]["updown"],
            "key_stocks": {
                k: v for k, v in snapshot["integration"]["stocks"].items()
                if k in {"삼성전자", "SK하이닉스"}
            },
        },
        "deterministic": forecast,
        "schema": {
            "close_delta_pts": "integer -120..120",
            "reason_code": "gap_fail|flow_reversal|breadth_support|neutral",
            "confidence": "0..1",
        },
    }
    body = {
        "model": os.environ.get("CODEX_OLLAMA_MODEL", "glm4:9b"),
        "messages": [
            {"role": "system", "content": "You are a low-cost JSON audit function. Output valid JSON only."},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=True, separators=(",", ":"))},
        ],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.0, "num_ctx": 2048, "num_predict": 120, "keep_alive": "4h"},
    }
    try:
        r = requests.post(os.environ.get("OLLAMA_CHAT_URL", "http://127.0.0.1:11434/api/chat"), json=body, timeout=90)
        data = r.json()
        raw = (data.get("message") or {}).get("content", "")
        txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
        match = re.search(r"\{.*\}", txt, re.S)
        if not match:
            return {
                "response": raw,
                "valid": False,
                "error": "no_json_object_in_response",
                "prompt_eval_count": data.get("prompt_eval_count"),
                "eval_count": data.get("eval_count"),
                "total_duration": data.get("total_duration"),
            }
        parsed = json.loads(match.group(0))
        valid = (
            isinstance(parsed.get("close_delta_pts"), int)
            and -120 <= parsed["close_delta_pts"] <= 120
            and parsed.get("reason_code") in {"gap_fail", "flow_reversal", "breadth_support", "neutral"}
        )
        return {
            "response": raw,
            "parsed": parsed,
            "valid": valid,
            "prompt_eval_count": data.get("prompt_eval_count"),
            "eval_count": data.get("eval_count"),
            "total_duration": data.get("total_duration"),
        }
    except Exception as exc:
        return {"error": repr(exc)}


def collect(use_glm: bool) -> dict[str, Any]:
    snapshot = {
        "created_at_kst": now_kst().isoformat(timespec="seconds"),
        "realtime": fetch_realtime(),
        "integration": fetch_integration(),
        "us": fetch_us(),
    }
    forecast = deterministic_forecast(snapshot)
    result = {"snapshot": snapshot, "forecast": forecast}
    if use_glm:
        audit = local_glm_audit(snapshot, forecast)
        result["glm_audit"] = audit
        parsed = audit.get("parsed") or {}
        if audit.get("valid"):
            delta = int(parsed.get("close_delta_pts", 0))
            adjusted = forecast["forecast_close"] + delta
            result["glm_adjusted_close"] = round(adjusted)
    return result


def sleep_until(target: str) -> None:
    hh, mm = [int(x) for x in target.split(":")]
    now = now_kst()
    target_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if target_dt < now:
        target_dt += dt.timedelta(days=1)
    time.sleep((target_dt - now_kst()).total_seconds())


def save_result(result: dict[str, Any], label: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = now_kst().strftime("%Y%m%d_%H%M%S")
    path = OUT / f"{stamp}_{label}_robust_close_forecast.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def build_message(result: dict[str, Any], path: Path) -> str:
    fc = result["forecast"]
    rt = result["snapshot"]["realtime"]
    it = result["snapshot"]["integration"]
    lines = [
        f"[Codex] {now_kst().strftime('%H:%M')} KOSPI 종가 모니터",
        f"현재 {rt['close']:,.2f} / 시가 {rt['open']:,.2f} / 고가 {rt['high']:,.2f} / 저가 {rt['low']:,.2f}",
        f"수급 외국인 {it['deal']['foreign']:,.0f} / 기관 {it['deal']['institution']:,.0f} / 프로그램 {it['program']['total']:,.0f}",
        f"예상 종가 {fc['forecast_close']:,}  범위 {fc['range'][0]:,}~{fc['range'][1]:,}  신뢰 {fc['confidence']:.2f}",
        f"플래그: {', '.join(fc['risk_flags']) if fc['risk_flags'] else 'none'}",
    ]
    if result.get("glm_adjusted_close"):
        lines.append(f"GLM 보정 종가 {result['glm_adjusted_close']:,}")
    lines.append(f"저장: {path.name}")
    return "\n".join(lines)


def send_telegram(text: str) -> bool:
    token = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=20)
    r.raise_for_status()
    return bool((r.json() or {}).get("ok"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", help="KST HH:MM, e.g. 12:30")
    parser.add_argument("--label", default="now")
    parser.add_argument("--glm", action="store_true")
    parser.add_argument("--telegram", action="store_true")
    args = parser.parse_args()
    if args.target:
        sleep_until(args.target)
        args.label = args.target.replace(":", "")
    result = collect(args.glm)
    path = save_result(result, args.label)
    fc = result["forecast"]
    rt = result["snapshot"]["realtime"]
    it = result["snapshot"]["integration"]
    message = build_message(result, path)
    print(f"saved={path}")
    print(f"[{now_kst().strftime('%H:%M')} KST KOSPI close forecast]")
    print(f"current={rt['close']:,.2f} open={rt['open']:,.2f} high={rt['high']:,.2f} low={rt['low']:,.2f}")
    print(f"flow foreign={it['deal']['foreign']:,.0f} inst={it['deal']['institution']:,.0f} program={it['program']['total']:,.0f}")
    print(f"forecast_close={fc['forecast_close']:,} range={fc['range'][0]:,}~{fc['range'][1]:,} confidence={fc['confidence']:.2f}")
    if result.get("glm_adjusted_close"):
        print(f"glm_adjusted_close={result['glm_adjusted_close']:,} audit={result.get('glm_audit', {}).get('parsed')}")
    print(f"flags={','.join(fc['risk_flags'])}")
    if args.telegram:
        sent = send_telegram(message)
        print(f"telegram_sent={'OK' if sent else 'SKIPPED_NO_ENV'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
