#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "contest" / "overnight"
HEAD = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}


def now_kst() -> dt.datetime:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))


def num(x: Any) -> float:
    if x in (None, ""):
        return 0.0
    return float(str(x).replace(",", "").replace("%", "").replace("+", "").strip() or 0)


def target_time(hhmm: str) -> dt.datetime:
    hh, mm = [int(x) for x in hhmm.split(":", 1)]
    n = now_kst()
    t = n.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if t < n:
        t += dt.timedelta(days=1)
    return t


def fetch_us() -> dict[str, Any]:
    symbols = {".INX": "SP500", ".IXIC": "NASDAQ", ".SOX": "SOX", ".DJI": "DOW"}
    out = {}
    for symbol, name in symbols.items():
        try:
            b = requests.get(f"https://api.stock.naver.com/index/{symbol}/basic", headers=HEAD, timeout=15).json()
            out[name] = {
                "symbol": symbol,
                "close": num(b.get("closePrice")),
                "change_pct": num(b.get("fluctuationsRatio")),
                "status": b.get("marketStatus"),
                "traded_at": b.get("localTradedAt"),
            }
        except Exception as exc:
            out[name] = {"symbol": symbol, "error": repr(exc)}
    for symbol in ["EWY", "MU", "NVDA", "META"]:
        try:
            b = requests.get(f"https://api.stock.naver.com/stock/{symbol}/basic", headers=HEAD, timeout=15).json()
            out[symbol] = {
                "symbol": symbol,
                "close": num(b.get("closePrice")),
                "change_pct": num(b.get("fluctuationsRatio")),
                "status": b.get("marketStatus"),
                "traded_at": b.get("localTradedAt"),
            }
        except Exception as exc:
            out[symbol] = {"symbol": symbol, "error": repr(exc)}
    return out


def fetch_kospi_day() -> dict[str, Any]:
    end = now_kst().strftime("%Y%m%d")
    start = (now_kst() - dt.timedelta(days=7)).strftime("%Y%m%d")
    url = (
        "https://api.finance.naver.com/siseJson.naver?symbol=KOSPI"
        f"&requestType=1&startTime={start}&endTime={end}&timeframe=day"
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
    return {"rows": clean, "last": clean[-1], "prev": clean[-2] if len(clean) >= 2 else None}


def fetch_domestic() -> dict[str, Any]:
    url = "https://m.stock.naver.com/api/index/KOSPI/integration"
    d = requests.get(url, headers=HEAD, timeout=20).json()
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
                "delta": num(row.get("compareToPreviousClosePrice")),
            }
    return {
        "prev_close": num(totals.get("lastClosePrice")),
        "open": num(totals.get("openPrice")),
        "high": num(totals.get("highPrice")),
        "low": num(totals.get("lowPrice")),
        "deal": {
            "date": deal.get("bizdate"),
            "personal": num(deal.get("personalValue")),
            "foreign": num(deal.get("foreignValue")),
            "institution": num(deal.get("institutionalValue")),
        },
        "program": {
            "date": program.get("bizdate"),
            "total": num(program.get("indexTotalReal")),
            "index": num(program.get("indexDifferenceReal")),
            "non_index": num(program.get("indexBiDifferenceReal")),
        },
        "updown": {
            "rise": int(num(updown.get("riseCount"))),
            "fall": int(num(updown.get("fallCount"))),
            "upper": int(num(updown.get("upperCount"))),
            "lower": int(num(updown.get("lowerCount"))),
        },
        "stocks": stocks,
    }


def fetch_news() -> dict[str, Any]:
    queries = [
        "Meta excess AI compute cloud business semiconductor stocks",
        "Meta AI compute capacity chip stocks Nvidia memory",
        "AI infrastructure oversupply semiconductor selloff Meta",
        "Samsung Electronics HBM Nvidia",
        "SK Hynix HBM Nvidia",
        "US stock market semiconductor Nasdaq Fed yields",
        "KOSPI foreign selling program trading",
    ]
    items = []
    for q in queries:
        url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(q) + "&hl=en-US&gl=US&ceid=US:en"
        try:
            text = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15).text
            root = ET.fromstring(text)
            for item in root.findall(".//item")[:3]:
                title = (item.findtext("title") or "").strip()
                pub = (item.findtext("pubDate") or "").strip()
                if title:
                    items.append({"query": q, "title": title, "pubDate": pub})
        except Exception as exc:
            items.append({"query": q, "error": repr(exc)})
    joined = " ".join((x.get("title") or "").lower() for x in items)
    pos_terms = ["rally", "surge", "record", "beat", "nvidia", "hbm", "ai"]
    neg_terms = ["selloff", "plunge", "tariff", "probe", "miss", "warning", "yield"]
    return {
        "items": items[:12],
        "positive_hits": [w for w in pos_terms if w in joined],
        "negative_hits": [w for w in neg_terms if w in joined],
        "source": "Google News RSS public search; SNS proxy only",
    }


def forecast(snapshot: dict[str, Any]) -> dict[str, Any]:
    day = snapshot["kospi_day"]["last"]
    domestic = snapshot["domestic"]
    us = snapshot["us"]
    macro = snapshot["macro"]
    news = snapshot["news"]

    close = day["close"]
    spx = us.get("SP500", {}).get("change_pct", 0.0) or 0.0
    nasdaq = us.get("NASDAQ", {}).get("change_pct", 0.0) or 0.0
    sox = us.get("SOX", {}).get("change_pct", 0.0) or 0.0
    ewy = us.get("EWY", {}).get("change_pct", 0.0) or 0.0
    mu = us.get("MU", {}).get("change_pct", 0.0) or 0.0
    nvda = us.get("NVDA", {}).get("change_pct", 0.0) or 0.0
    meta = us.get("META", {}).get("change_pct", 0.0) or 0.0
    semi_impulse = 0.45 * sox + 0.25 * mu + 0.20 * nvda + 0.10 * meta
    us_impulse = 0.20 * spx + 0.20 * nasdaq + 0.30 * semi_impulse + 0.30 * ewy
    raw_gap = max(-0.020, min(0.020, us_impulse / 260.0))
    ewy_gap = max(-0.025, min(0.025, 0.58 * ewy / 100.0))

    foreign = domestic["deal"]["foreign"]
    inst = domestic["deal"]["institution"]
    program = domestic["program"]["total"]
    samsung = domestic["stocks"].get("삼성전자", {}).get("change_pct", 0.0)
    hynix = domestic["stocks"].get("SK하이닉스", {}).get("change_pct", 0.0)
    defense_strength = inst - abs(program) - 0.5 * abs(min(foreign, 0))

    domestic_damage = 0.0
    if day["open"] > 0 and day["close"] < day["open"]:
        domestic_damage += min(0.010, (day["open"] - day["close"]) / day["close"] * 0.25)
    if program <= -8000:
        domestic_damage += 0.003
    if defense_strength < 0:
        domestic_damage += 0.003
    if samsung <= -3 or hynix <= -3:
        domestic_damage += 0.003

    fx_drag = 0.0
    if macro["usdkrw"] >= 1545:
        fx_drag += 0.003
    if macro["dxy"] >= 101:
        fx_drag += 0.0015
    if macro["us10y"] >= 4.35:
        fx_drag += 0.001

    news_tilt = 0.0005 * len(news.get("positive_hits", [])) - 0.0005 * len(news.get("negative_hits", []))
    news_tilt = max(-0.002, min(0.002, news_tilt))

    prev_day = snapshot["kospi_day"].get("prev") or {}
    prev_close = prev_day.get("close") or 0.0
    prior_ret = (close / prev_close - 1.0) if prev_close else 0.0
    post_crash_relief = prior_ret <= -0.05 and ewy > -3.5 and len(news.get("negative_hits", [])) <= 2

    if post_crash_relief:
        domestic_damage *= 0.55
        raw_gap = 0.35 * raw_gap + 0.65 * ewy_gap
    else:
        raw_gap = 0.65 * raw_gap + 0.35 * ewy_gap

    open_ret = raw_gap - 0.45 * domestic_damage - 0.40 * fx_drag + news_tilt
    if sox >= 3.5 and us.get("NASDAQ", {}).get("change_pct", 0) >= 1.0:
        open_ret = max(open_ret, 0.010 - 0.25 * domestic_damage - 0.20 * fx_drag)
    if post_crash_relief:
        open_ret = max(open_ret, -0.015)
    open_pred = round(close * (1 + open_ret))

    if post_crash_relief:
        regime = "post_crash_relief_possible"
    elif domestic_damage >= 0.012 and raw_gap <= 0.002:
        regime = "domestic_damage_continuation"
    elif raw_gap > domestic_damage + fx_drag:
        regime = "overnight_relief"
    else:
        regime = "fade_risk"

    return {
        "open": open_pred,
        "range": [round(open_pred - 55), round(open_pred + 65)],
        "regime": regime,
        "prob_gap_up": round(0.50 + max(-0.18, min(0.18, open_ret * 15)), 2),
        "inputs": {
            "close": close,
            "us_impulse": round(us_impulse, 3),
            "semi_impulse": round(semi_impulse, 3),
            "ewy": round(ewy, 3),
            "ewy_gap": round(ewy_gap, 4),
            "raw_gap": round(raw_gap, 4),
            "prior_ret": round(prior_ret, 4),
            "post_crash_relief": post_crash_relief,
            "domestic_damage": round(domestic_damage, 4),
            "fx_drag": round(fx_drag, 4),
            "news_tilt": round(news_tilt, 4),
            "foreign": foreign,
            "institution": inst,
            "program": program,
            "defense_strength": round(defense_strength, 1),
            "samsung_pct": samsung,
            "hynix_pct": hynix,
        },
    }


def glm_audit(snapshot: dict[str, Any], fc: dict[str, Any]) -> dict[str, Any]:
    body = {
        "model": os.environ.get("CODEX_OLLAMA_MODEL", "glm4:9b"),
        "messages": [
            {"role": "system", "content": "You are a compact JSON audit function. Output valid JSON only."},
            {
                "role": "user",
                "content": json.dumps({
                    "task": "Audit KOSPI open forecast. Return delta only.",
                    "forecast": fc,
                    "us": snapshot["us"],
                    "domestic": snapshot["domestic"],
                    "schema": {"open_delta_pts": "integer -80..80", "reason_code": "relief|trim|neutral"},
                }, ensure_ascii=True, separators=(",", ":")),
            },
        ],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.0, "num_ctx": 2048, "num_predict": 100, "keep_alive": "4h"},
    }
    try:
        d = requests.post(os.environ.get("OLLAMA_CHAT_URL", "http://127.0.0.1:11434/api/chat"), json=body, timeout=90).json()
        raw = (d.get("message") or {}).get("content", "")
        m = re.search(r"\{.*\}", raw, re.S)
        parsed = json.loads(m.group(0)) if m else None
        valid = isinstance(parsed, dict) and isinstance(parsed.get("open_delta_pts"), int) and -80 <= parsed["open_delta_pts"] <= 80
        return {"response": raw, "parsed": parsed, "valid": valid, "prompt_eval_count": d.get("prompt_eval_count"), "eval_count": d.get("eval_count")}
    except Exception as exc:
        return {"error": repr(exc)}


def build_message(result: dict[str, Any]) -> str:
    fc = result["forecast"]
    i = fc["inputs"]
    us = result["snapshot"]["us"]
    lines = [
        f"[Codex] {now_kst().strftime('%H:%M')} KST KOSPI 07:30 open monitor",
        f"US S&P {us.get('SP500', {}).get('change_pct', 0):+.2f}% / Nasdaq {us.get('NASDAQ', {}).get('change_pct', 0):+.2f}% / SOX {us.get('SOX', {}).get('change_pct', 0):+.2f}%",
        f"KOSPI close {i['close']:,.2f} / foreign {i['foreign']:,.0f} / inst {i['institution']:,.0f} / program {i['program']:,.0f}",
        f"damage {i['domestic_damage']:.4f} / fx_drag {i['fx_drag']:.4f} / defense {i['defense_strength']:,.0f}",
        f"Open forecast {fc['open']:,} range {fc['range'][0]:,}~{fc['range'][1]:,} regime {fc['regime']}",
        "Research only. Not investment advice.",
    ]
    if result.get("glm_adjusted_open"):
        lines.insert(-1, f"GLM adjusted open {result['glm_adjusted_open']:,}")
    return "\n".join(lines)


def send_telegram(text: str) -> bool:
    token = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": text}, timeout=20)
    r.raise_for_status()
    return bool((r.json() or {}).get("ok"))


def collect(use_glm: bool, telegram: bool, label: str) -> dict[str, Any]:
    snapshot = {
        "created_at_kst": now_kst().isoformat(timespec="seconds"),
        "us": fetch_us(),
        "kospi_day": fetch_kospi_day(),
        "domestic": fetch_domestic(),
        "news": fetch_news(),
        "macro": {
            "usdkrw": float(os.environ.get("CODEX_USDKRW", "1552.98")),
            "dxy": float(os.environ.get("CODEX_DXY", "101.36")),
            "us10y": float(os.environ.get("CODEX_US10Y", "4.365")),
        },
    }
    fc = forecast(snapshot)
    result = {"snapshot": snapshot, "forecast": fc}
    if use_glm:
        audit = glm_audit(snapshot, fc)
        result["glm_audit"] = audit
        if audit.get("valid"):
            result["glm_adjusted_open"] = fc["open"] + int(audit["parsed"].get("open_delta_pts", 0))
    result["message"] = build_message(result)

    OUT.mkdir(parents=True, exist_ok=True)
    stamp = now_kst().strftime("%Y%m%d_%H%M%S")
    path = OUT / f"{stamp}_{label}_0730_strategy.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / f"{stamp}_{label}_0730_strategy.txt").write_text(result["message"], encoding="utf-8")
    print(result["message"])
    print(f"saved={path}")
    if telegram:
        print(f"telegram_sent={'OK' if send_telegram(result['message']) else 'SKIPPED_NO_ENV'}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="07:30")
    parser.add_argument("--now", action="store_true")
    parser.add_argument("--poll", action="store_true")
    parser.add_argument("--glm", action="store_true")
    parser.add_argument("--telegram", action="store_true")
    args = parser.parse_args()

    if args.now:
        collect(args.glm, args.telegram, "now")
        return 0

    target = target_time(args.target)
    if args.poll:
        while now_kst() < target:
            collect(args.glm, args.telegram, "poll")
            time.sleep(min(3600, max(60, int((target - now_kst()).total_seconds()))))

    delay = (target - now_kst()).total_seconds()
    if delay > 0:
        time.sleep(delay)
    collect(args.glm, args.telegram, args.target.replace(":", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
