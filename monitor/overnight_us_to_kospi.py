#!/usr/bin/env python3
"""
Overnight US-market monitor -> next KOSPI forecast.

Designed for low-token, fast operation:
- fetches compact market snapshots from Naver APIs
- uses a deterministic Codex Gate-RC v2 forecast
- estimates Claude's likely trimmed tactic
- optionally asks local Ollama glm4:9b for a short cross-check
- writes JSON/TXT artifacts and sends Telegram if env credentials are present

No API keys are embedded in this file.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "contest" / "overnight"
HEAD = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}

US_SYMBOLS = {
    ".INX": "SP500",
    ".IXIC": "NASDAQ",
    ".SOX": "SOX",
    ".DJI": "DOW",
}


def now_kst() -> dt.datetime:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))


def kst_target(hour: int, minute: int) -> dt.datetime:
    n = now_kst()
    target = n.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target < n:
        target = target + dt.timedelta(days=1)
    return target


def num(x: Any) -> float:
    if x in (None, ""):
        return 0.0
    return float(str(x).replace(",", "").replace("%", "").strip())


def fetch_us() -> dict[str, Any]:
    out = {}
    for symbol, name in US_SYMBOLS.items():
        url = f"https://api.stock.naver.com/index/{symbol}/basic"
        try:
            b = requests.get(url, headers=HEAD, timeout=15).json()
            out[name] = {
                "symbol": symbol,
                "close": num(b.get("closePrice")),
                "change_pct": num(b.get("fluctuationsRatio")),
                "market_status": b.get("marketStatus"),
                "local_traded_at": b.get("localTradedAt"),
            }
        except Exception as exc:
            out[name] = {"symbol": symbol, "error": repr(exc)}
    return out


def usable_us_snapshot(us: dict[str, Any]) -> bool:
    values = [
        abs(float((us.get(name) or {}).get("change_pct") or 0))
        for name in ("SP500", "NASDAQ", "SOX")
    ]
    return any(v > 0.001 for v in values)


def cached_us_snapshot() -> dict[str, Any] | None:
    if not OUT.exists():
        return None
    for path in sorted(OUT.glob("*_overnight_forecast.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            us = data.get("snapshot", {}).get("us", {})
            if usable_us_snapshot(us):
                us = dict(us)
                us["_cache_source"] = path.name
                return us
        except Exception:
            continue
    return None


def fetch_kospi_last() -> dict[str, Any]:
    end = now_kst().strftime("%Y%m%d")
    start = (now_kst() - dt.timedelta(days=10)).strftime("%Y%m%d")
    url = (
        "https://api.finance.naver.com/siseJson.naver?symbol=KOSPI"
        f"&requestType=1&startTime={start}&endTime={end}&timeframe=day"
    )
    text = requests.get(url, headers=HEAD, timeout=20).text.strip().replace("'", '"')
    rows = json.loads(text)
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


def fetch_flow() -> dict[str, Any]:
    import re

    today = now_kst().strftime("%Y%m%d")
    url = f"https://finance.naver.com/sise/investorDealTrendDay.naver?bizdate={today}&sosok=01&page=1"
    r = requests.get(url, headers=HEAD, timeout=20)
    r.encoding = "euc-kr"
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", r.text, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        c = [
            re.sub(r"<[^>]+>", "", x).replace("&nbsp;", "").replace(",", "").strip()
            for x in cells
        ]
        if c and re.match(r"\d{2}\.\d{2}\.\d{2}$", c[0]):
            foreign = int(c[2])
            institution = int(c[3])
            return {
                "date": "20" + c[0].replace(".", ""),
                "individual_million_krw": int(c[1]),
                "foreign_million_krw": foreign,
                "institution_million_krw": institution,
                "d_sell": foreign < 0 and institution < 0,
            }
    return {"error": "no_flow_row_found"}


def deterministic_forecast(snapshot: dict[str, Any]) -> dict[str, Any]:
    kospi = snapshot["kospi"]["last"]
    flow = snapshot["flow"]
    us = snapshot["us"]
    close = kospi["close"]
    high = kospi["high"]
    low = kospi["low"]
    foreign = float(flow.get("foreign_million_krw", 0))
    institution = float(flow.get("institution_million_krw", 0))
    d_sell = bool(flow.get("d_sell", False))
    spx = float(us.get("SP500", {}).get("change_pct", 0))
    nasdaq = float(us.get("NASDAQ", {}).get("change_pct", 0))
    sox = float(us.get("SOX", {}).get("change_pct", 0))

    us_strength = 0.30 * spx + 0.30 * nasdaq + 0.40 * sox
    raw_gap = max(-0.018, min(0.018, us_strength / 260.0))

    # Claude showed the right tactic: trim US extrapolation when local sell/fx
    # pressure is large. Keep this explicit and auditable.
    foreign_penalty = 0.0
    if foreign <= -20000:
        foreign_penalty += 0.004
    if foreign <= -35000:
        foreign_penalty += 0.004
    if low < 8400:
        foreign_penalty += 0.003

    # Macro drag is intentionally conservative. It encodes factors that the
    # old MW-RC v1 ignored: won weakness, dollar strength, rates, and forced
    # foreign outflow narratives. The monitor can run without live macro APIs;
    # these values are supplied from the evening research pass and can be
    # revised in the morning.
    macro = snapshot.get("macro", {})
    macro_drag = 0.0
    if float(macro.get("usdkrw", 0) or 0) >= 1545:
        macro_drag += 0.003
    if float(macro.get("dxy", 0) or 0) >= 101:
        macro_drag += 0.0015
    if float(macro.get("us10y", 0) or 0) >= 4.35:
        macro_drag += 0.001
    if macro.get("forced_outflow_risk"):
        macro_drag += 0.002

    month_end_relief = 0.002  # 6/30 month-end pressure partly rolls off on 7/1.
    if d_sell:
        regime = "risk"
        open_ret = raw_gap * 0.35 - 0.006 - macro_drag * 0.5
        close_ret = raw_gap * 0.20 - 0.010 - macro_drag
        prob_up = 0.35
    elif low < 8400 and foreign <= -20000:
        regime = "fade-risk"
        open_ret = raw_gap + month_end_relief - foreign_penalty * 0.55 - macro_drag * 0.35
        close_ret = raw_gap * 0.40 + month_end_relief - foreign_penalty - macro_drag
        prob_up = 0.50 if macro_drag else 0.52
    else:
        regime = "recovery"
        open_ret = raw_gap + month_end_relief - macro_drag * 0.35
        close_ret = raw_gap * 0.75 + month_end_relief * 0.5 - macro_drag
        prob_up = 0.57 if macro_drag else 0.60

    codex_open = round(close * (1 + open_ret))
    codex_close = round(close * (1 + close_ret))

    # Opponent tactic: Claude likely trims the deterministic value toward
    # Diode/naive when foreign selling and FX are ugly.
    claude_open = round(codex_open - (15 if foreign <= -20000 else 5))
    claude_close = round(codex_close - (5 if regime == "fade-risk" else 0))

    return {
        "regime": regime,
        "us_strength": round(us_strength, 3),
        "codex": {
            "open": codex_open,
            "close": codex_close,
            "prob_up": prob_up,
            "confidence": 0.54 if regime == "fade-risk" else 0.58,
        },
        "claude_tactic_estimate": {
            "open": claude_open,
            "close": claude_close,
            "note": "trim US momentum when local foreign-selling/fade risk is high",
        },
        "inputs": {
            "kospi_close": close,
            "kospi_high": high,
            "kospi_low": low,
            "foreign_million_krw": foreign,
            "institution_million_krw": institution,
            "d_sell": d_sell,
            "sp500_pct": spx,
            "nasdaq_pct": nasdaq,
            "sox_pct": sox,
            "foreign_penalty": foreign_penalty,
            "macro_drag": macro_drag,
            "macro": macro,
        },
    }


def local_glm_check(snapshot: dict[str, Any], forecast: dict[str, Any]) -> dict[str, Any]:
    inputs = forecast.get("inputs", {})
    macro = inputs.get("macro", {}) or {}
    codex = forecast.get("codex", {})
    claude = forecast.get("claude_tactic_estimate", {})
    data = {
        "close": inputs.get("kospi_close"),
        "foreign": inputs.get("foreign_million_krw"),
        "inst": inputs.get("institution_million_krw"),
        "us": forecast.get("us_strength"),
        "regime": forecast.get("regime"),
        "usdkrw": macro.get("usdkrw"),
        "dxy": macro.get("dxy"),
        "us10y": macro.get("us10y"),
        "drag": inputs.get("macro_drag"),
        "codex_open": codex.get("open"),
        "codex_close": codex.get("close"),
        "claude_open": claude.get("open"),
        "claude_close": claude.get("close"),
    }
    user_prompt = (
        "Audit KOSPI forecast. Return minified JSON only. "
        "Schema: {\"risk_flags\":[strings],\"open_delta_pts\":int,"
        "\"close_delta_pts\":int,\"confidence\":0.0,\"reason_code\":\"trim|follow_us|neutral|fade_risk\"}. "
        "Allowed flags: fx, foreign_flow, rates, overheat, us_momentum, none. "
        "open_delta_pts must be between -80 and 80. close_delta_pts must be between -160 and 160. "
        "Do not repeat input. If usdkrw high and foreign negative, close_delta_pts is usually negative. "
        f"Data={json.dumps(data, ensure_ascii=True, separators=(',', ':'))}"
    )
    body = {
        "model": os.environ.get("CODEX_OLLAMA_MODEL", "glm4:9b"),
        "messages": [
            {
                "role": "system",
                "content": "You are a low-cost JSON audit function. Output only valid JSON. No markdown.",
            },
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.0,
            "num_ctx": 2048,
            "num_predict": 120,
            "keep_alive": "4h",
        },
    }
    try:
        url = os.environ.get("OLLAMA_CHAT_URL", "http://127.0.0.1:11434/api/chat")
        r = requests.post(url, json=body, timeout=90)
        if r.status_code >= 400:
            return {"error": r.text[:500]}
        data = r.json()
        raw = (data.get("message") or {}).get("content", "")
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        parsed = None
        valid = False
        try:
            parsed = json.loads(cleaned)
            valid = (
                isinstance(parsed, dict)
                and isinstance(parsed.get("risk_flags"), list)
                and isinstance(parsed.get("open_delta_pts"), int)
                and isinstance(parsed.get("close_delta_pts"), int)
                and -80 <= parsed.get("open_delta_pts") <= 80
                and -160 <= parsed.get("close_delta_pts") <= 160
                and isinstance(parsed.get("confidence"), (int, float))
                and 0 <= float(parsed.get("confidence")) <= 1
                and parsed.get("reason_code") in {"trim", "follow_us", "neutral", "fade_risk"}
            )
        except Exception:
            parsed = None
        return {
            "model": body["model"],
            "response": raw,
            "parsed": parsed,
            "valid": valid,
            "prompt_eval_count": data.get("prompt_eval_count"),
            "eval_count": data.get("eval_count"),
            "total_duration": data.get("total_duration"),
            "prompt_eval_duration": data.get("prompt_eval_duration"),
            "eval_duration": data.get("eval_duration"),
        }
    except Exception as exc:
        return {"error": repr(exc)}


def make_message(result: dict[str, Any]) -> str:
    fc = result["forecast"]
    codex = fc["codex"]
    claude = fc["claude_tactic_estimate"]
    inp = fc["inputs"]
    created = result["created_at_kst"][11:16]
    us = result["snapshot"]["us"]
    return "\n".join([
        f"[{created} KST 7/1 KOSPI 예측]",
        f"US: S&P {us.get('SP500', {}).get('change_pct', 0):+.2f}%, Nasdaq {us.get('NASDAQ', {}).get('change_pct', 0):+.2f}%, SOX {us.get('SOX', {}).get('change_pct', 0):+.2f}%",
        f"KOSPI: 종가 {inp['kospi_close']:,.2f}, 외국인 {inp['foreign_million_krw']:,.0f}, 기관 {inp['institution_million_krw']:,.0f}, D_sell={inp['d_sell']}",
        f"Regime: {fc['regime']}, us_strength={fc['us_strength']}",
        "",
        f"Codex: 시가 {codex['open']:,}, 종가 {codex['close']:,}, 상승 {codex['prob_up']:.0%}, 신뢰 {codex['confidence']:.2f}",
        f"Claude 전술 추정: 시가 {claude['open']:,}, 종가 {claude['close']:,}",
        "",
        "07:30 최종 고정값은 이 파일 기준. 정보·연구 목적, 투자자문 아님.",
    ])


def send_telegram(text: str) -> None:
    token = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat, "text": text}, timeout=20).raise_for_status()


def collect_once(use_glm: bool, telegram: bool) -> dict[str, Any]:
    us = fetch_us()
    if not usable_us_snapshot(us):
        cached = cached_us_snapshot()
        if cached:
            us = cached
    snapshot = {
        "created_at_kst": now_kst().isoformat(timespec="seconds"),
        "us": us,
        "kospi": fetch_kospi_last(),
        "flow": fetch_flow(),
        "macro": {
            "usdkrw": float(os.environ.get("CODEX_USDKRW", "1552.98")),
            "dxy": float(os.environ.get("CODEX_DXY", "101.36")),
            "us10y": float(os.environ.get("CODEX_US10Y", "4.365")),
            "forced_outflow_risk": os.environ.get("CODEX_FORCED_OUTFLOW_RISK", "1") == "1",
            "source": "evening_research_override; refresh before final call",
        },
    }
    forecast = deterministic_forecast(snapshot)
    result = {
        "created_at_kst": snapshot["created_at_kst"],
        "snapshot": snapshot,
        "forecast": forecast,
    }
    if use_glm:
        result["local_glm_check"] = local_glm_check(snapshot, forecast)
    result["message"] = make_message(result)

    OUT.mkdir(parents=True, exist_ok=True)
    stamp = now_kst().strftime("%Y%m%d_%H%M%S")
    (OUT / f"{stamp}_overnight_forecast.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / f"{stamp}_overnight_forecast.txt").write_text(result["message"], encoding="utf-8")
    print(result["message"])
    if telegram:
        send_telegram(result["message"])
        print("telegram_sent=OK")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="07:30", help="KST target time HH:MM")
    parser.add_argument("--now", action="store_true", help="collect immediately")
    parser.add_argument("--poll", action="store_true", help="poll hourly until target, then final")
    parser.add_argument("--glm", action="store_true", help="use local Ollama glm4 cross-check")
    parser.add_argument("--telegram", action="store_true")
    args = parser.parse_args()

    if args.now:
        collect_once(args.glm, args.telegram)
        return 0

    h, m = [int(x) for x in args.target.split(":", 1)]
    target = kst_target(h, m)

    if args.poll:
        while now_kst() < target:
            collect_once(args.glm, args.telegram)
            sleep_s = min(3600, max(60, int((target - now_kst()).total_seconds())))
            time.sleep(sleep_s)

    delay = (target - now_kst()).total_seconds()
    if delay > 0:
        time.sleep(delay)
    collect_once(args.glm, args.telegram)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
