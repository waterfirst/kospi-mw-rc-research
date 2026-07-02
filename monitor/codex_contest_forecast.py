#!/usr/bin/env python3
"""
Codex KOSPI contest forecaster.

Runs under the 10-point contest rules:
  - 08:00 KST: forecast KOSPI open
  - 12:30 KST: forecast KOSPI close after morning checkpoints

The script is intentionally fail-closed:
  - API keys are read only from environment variables.
  - Local Ollama is used without API keys when available.
  - Market snapshots are saved with a SHA-256 hash.
  - Model outputs must be valid JSON and pass basic numeric validation.
  - Missing source data is recorded as missing, never filled by imagination.

Information/research purpose only. Not investment advice.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "contest" / "codex"
HEAD = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_GEMINI_MODEL = os.environ.get("CODEX_GEMINI_MODEL", "gemini-2.5-pro")
DEFAULT_GPT_MODEL = os.environ.get("CODEX_GPT_MODEL", "gpt-4.1-mini")
DEFAULT_OPENAI_URL = os.environ.get("OPENAI_CHAT_COMPLETIONS_URL", "https://api.openai.com/v1/chat/completions")
DEFAULT_ZAI_MODEL = os.environ.get("CODEX_ZAI_MODEL", "glm-5.2")
DEFAULT_ZAI_URL = os.environ.get(
    "ZAI_CHAT_COMPLETIONS_URL",
    "https://api.z.ai/api/paas/v4/chat/completions",
)
DEFAULT_OLLAMA_MODEL = os.environ.get("CODEX_OLLAMA_MODEL", "glm4:9b")
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_GENERATE_URL", "http://127.0.0.1:11434/api/generate")


def now_kst() -> dt.datetime:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))


def compact_hash(obj: Any) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _f(x: Any) -> float:
    if x in (None, ""):
        return 0.0
    return float(str(x).replace(",", "").replace("%", "").strip())


def fetch_kospi_daily() -> dict[str, Any]:
    end = (now_kst() + dt.timedelta(days=3)).strftime("%Y%m%d")
    start = (now_kst() - dt.timedelta(days=20)).strftime("%Y%m%d")
    url = (
        "https://api.finance.naver.com/siseJson.naver?symbol=KOSPI"
        f"&requestType=1&startTime={start}&endTime={end}&timeframe=day"
    )
    r = requests.get(url, headers=HEAD, timeout=20)
    r.raise_for_status()
    rows = json.loads(r.text.strip().replace("'", '"'))
    clean = []
    for row in rows:
        if isinstance(row, list) and row and str(row[0]).isdigit():
            clean.append(
                {
                    "date": str(row[0]),
                    "open": _f(row[1]),
                    "high": _f(row[2]),
                    "low": _f(row[3]),
                    "close": _f(row[4]),
                    "volume": _f(row[5]) if len(row) > 5 else 0,
                }
            )
    return {"source": "naver_siseJson_KOSPI_day", "rows": clean[-10:]}


def fetch_kospi_realtime() -> dict[str, Any]:
    url = "https://polling.finance.naver.com/api/realtime/domestic/index/KOSPI"
    r = requests.get(url, headers=HEAD, timeout=15)
    r.raise_for_status()
    data = r.json()
    areas = data.get("result", {}).get("areas", [])
    item = {}
    if areas and areas[0].get("datas"):
        item = areas[0]["datas"][0]
    return {
        "source": "naver_realtime_KOSPI",
        "close": _f(item.get("closePrice")),
        "open": _f(item.get("openPrice")),
        "high": _f(item.get("highPrice")),
        "low": _f(item.get("lowPrice")),
        "change_pct": _f(item.get("fluctuationsRatio")),
        "market_status": item.get("marketStatus"),
        "local_traded_at": item.get("localTradedAt"),
        "raw_keys": sorted(item.keys()) if item else [],
    }


def fetch_flow() -> dict[str, Any]:
    today = now_kst().strftime("%Y%m%d")
    url = f"https://finance.naver.com/sise/investorDealTrendDay.naver?bizdate={today}&sosok=01&page=1"
    r = requests.get(url, headers=HEAD, timeout=20)
    r.raise_for_status()
    r.encoding = "euc-kr"
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", r.text, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        c = [
            re.sub(r"<[^>]+>", "", x).replace("&nbsp;", "").replace(",", "").strip()
            for x in cells
        ]
        if c and re.match(r"\d{2}\.\d{2}\.\d{2}$", c[0]):
            return {
                "source": "naver_investorDealTrendDay",
                "date": "20" + c[0].replace(".", ""),
                "individual_million_krw": int(c[1]),
                "foreign_million_krw": int(c[2]),
                "institution_million_krw": int(c[3]),
            }
    return {"source": "naver_investorDealTrendDay", "error": "no_flow_row_found"}


def fetch_us_index(symbol: str) -> dict[str, Any]:
    url = f"https://api.stock.naver.com/index/{symbol}/basic"
    r = requests.get(url, headers=HEAD, timeout=15)
    r.raise_for_status()
    b = r.json()
    return {
        "symbol": symbol,
        "close": _f(b.get("closePrice")),
        "change_pct": _f(b.get("fluctuationsRatio")),
        "market_status": b.get("marketStatus"),
        "local_traded_at": b.get("localTradedAt"),
    }


def collect_snapshot(mode: str) -> dict[str, Any]:
    errors = []

    def safe(name: str, fn):
        try:
            return fn()
        except Exception as exc:
            errors.append({"name": name, "error": repr(exc)})
            return {"error": repr(exc)}

    us_symbols = {".SOX": "SOX", ".INX": "SP500", ".IXIC": "NASDAQ", ".DJI": "DOW"}
    us = {label: safe(f"us_{label}", lambda s=sym: fetch_us_index(s)) for sym, label in us_symbols.items()}
    snap = {
        "contestant": "Codex",
        "mode": mode,
        "created_at_kst": now_kst().isoformat(timespec="seconds"),
        "kospi_daily": safe("kospi_daily", fetch_kospi_daily),
        "kospi_realtime": safe("kospi_realtime", fetch_kospi_realtime),
        "flow": safe("flow", fetch_flow),
        "us_market": us,
        "errors": errors,
    }
    snap["snapshot_hash"] = compact_hash(snap)
    return snap


def system_prompt(mode: str) -> str:
    target = "KOSPI official open" if mode == "open" else "KOSPI official close"
    return f"""
You are an advisory quant model for a KOSPI forecasting contest.
Use only the supplied JSON snapshot. If a field is missing, say it is missing.
Do not invent market data, news, flows, prices, or API results.
Target: {target}.
Return strict JSON only, with this schema:
{{
  "forecast": number,
  "direction_from_prev_close": "UP" | "DOWN" | "FLAT",
  "prob_up": number,
  "prob_down": number,
  "confidence": number,
  "evidence": [string, string, string],
  "missing_data": [string],
  "risk_notes": [string]
}}
""".strip()


def compact_market_digest(snapshot: dict[str, Any]) -> dict[str, Any]:
    daily_rows = snapshot.get("kospi_daily", {}).get("rows", [])
    last = daily_rows[-1] if daily_rows else {}
    prev = daily_rows[-2] if len(daily_rows) >= 2 else {}
    flow = snapshot.get("flow", {})
    rt = snapshot.get("kospi_realtime", {})
    us = snapshot.get("us_market", {})
    d_sell = (
        flow.get("foreign_million_krw", 0) < 0
        and flow.get("institution_million_krw", 0) < 0
        and "error" not in flow
    )
    return {
        "snapshot_hash": snapshot.get("snapshot_hash"),
        "mode": snapshot.get("mode"),
        "created_at_kst": snapshot.get("created_at_kst"),
        "kospi_last": last,
        "kospi_prev": prev,
        "kospi_realtime": {
            "close": rt.get("close"),
            "open": rt.get("open"),
            "high": rt.get("high"),
            "low": rt.get("low"),
            "change_pct": rt.get("change_pct"),
            "market_status": rt.get("market_status"),
            "local_traded_at": rt.get("local_traded_at"),
            "missing": [k for k in ("close", "open", "high", "low", "change_pct", "market_status") if not rt.get(k)],
        },
        "flow": {
            "date": flow.get("date"),
            "individual_million_krw": flow.get("individual_million_krw"),
            "foreign_million_krw": flow.get("foreign_million_krw"),
            "institution_million_krw": flow.get("institution_million_krw"),
            "d_sell": d_sell,
            "error": flow.get("error"),
        },
        "us_market": us,
        "source_errors": snapshot.get("errors", []),
    }


def agent_prompt(mode: str, role: str) -> str:
    base = system_prompt(mode)
    role_note = {
        "local_compressor": (
            "Role: local compressor on the user's NVIDIA GPU. Produce a conservative forecast "
            "and short evidence using only the compact digest. Prefer marking missing data over guessing."
        ),
        "gpt_verifier": (
            "Role: GPT verifier. Check consistency, missing data, and anti-hallucination risks. "
            "Give a conservative forecast if evidence is incomplete."
        ),
        "zai_quant": (
            "Role: Z.ai GLM quant. Focus on numeric point estimate, direction probability, and downside/upside risk."
        ),
        "gemini_crosscheck": (
            "Role: Gemini cross-check. Focus on whether the source snapshot supports the forecast. "
            "Do not use external facts unless they are in the supplied digest."
        ),
    }.get(role, "Role: advisory model.")
    return base + "\n\n" + role_note + "\nReturn one valid JSON object only."


def call_openai_gpt(compact: dict[str, Any], mode: str) -> dict[str, Any]:
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        return {"provider": "openai_gpt", "role": "gpt_verifier", "error": "OPENAI_API_KEY not set"}
    body = {
        "model": DEFAULT_GPT_MODEL,
        "messages": [
            {"role": "system", "content": agent_prompt(mode, "gpt_verifier")},
            {"role": "user", "content": json.dumps(compact, ensure_ascii=False)},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    r = requests.post(
        DEFAULT_OPENAI_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=body,
        timeout=60,
    )
    if r.status_code >= 400:
        return {"provider": "openai_gpt", "role": "gpt_verifier", "model": DEFAULT_GPT_MODEL, "error": r.text[:1000]}
    data = r.json()
    text = data["choices"][0]["message"]["content"]
    return {"provider": "openai_gpt", "role": "gpt_verifier", "model": DEFAULT_GPT_MODEL, "json": parse_forecast_json(text)}


def call_gemini(compact: dict[str, Any], mode: str) -> dict[str, Any]:
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        return {"provider": "gemini", "role": "gemini_crosscheck", "error": "GOOGLE_API_KEY not set"}
    model = DEFAULT_GEMINI_MODEL
    url = GEMINI_URL.format(model=model)
    body = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": agent_prompt(mode, "gemini_crosscheck")},
                    {"text": json.dumps(compact, ensure_ascii=False)},
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }
    r = requests.post(url, params={"key": key}, json=body, timeout=60)
    if r.status_code >= 400:
        return {"provider": "gemini", "role": "gemini_crosscheck", "model": model, "error": r.text[:1000]}
    data = r.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return {"provider": "gemini", "role": "gemini_crosscheck", "model": model, "json": parse_forecast_json(text)}


def call_zai(compact: dict[str, Any], mode: str) -> dict[str, Any]:
    key = os.environ.get("ZAI_API_KEY", "")
    if not key:
        return {"provider": "zai", "role": "zai_quant", "error": "ZAI_API_KEY not set"}
    body = {
        "model": DEFAULT_ZAI_MODEL,
        "messages": [
            {"role": "system", "content": agent_prompt(mode, "zai_quant")},
            {"role": "user", "content": json.dumps(compact, ensure_ascii=False)},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    r = requests.post(
        DEFAULT_ZAI_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=body,
        timeout=60,
    )
    if r.status_code >= 400:
        return {"provider": "zai", "role": "zai_quant", "model": DEFAULT_ZAI_MODEL, "error": r.text[:1000]}
    data = r.json()
    text = data["choices"][0]["message"]["content"]
    return {"provider": "zai", "role": "zai_quant", "model": DEFAULT_ZAI_MODEL, "json": parse_forecast_json(text)}


def call_ollama(compact: dict[str, Any], mode: str) -> dict[str, Any]:
    prompt = (
        agent_prompt(mode, "local_compressor")
        + "\n\nReturn one valid JSON object only. No markdown, no comments, no prose.\n\n"
        + json.dumps(compact, ensure_ascii=False)
    )
    body = {
        "model": DEFAULT_OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,
            "num_ctx": 8192,
        },
    }
    try:
        r = requests.post(DEFAULT_OLLAMA_URL, json=body, timeout=120)
    except requests.RequestException as exc:
        return {"provider": "ollama", "model": DEFAULT_OLLAMA_MODEL, "error": repr(exc)}
    if r.status_code >= 400:
        return {"provider": "ollama", "model": DEFAULT_OLLAMA_MODEL, "error": r.text[:1000]}
    data = r.json()
    text = data.get("response", "")
    return {
        "provider": "ollama",
        "role": "local_compressor",
        "model": DEFAULT_OLLAMA_MODEL,
        "json": parse_forecast_json(text),
        "eval_count": data.get("eval_count"),
        "eval_duration": data.get("eval_duration"),
    }


def parse_forecast_json(text: str) -> dict[str, Any]:
    parsed = json.loads(text)
    forecast = float(parsed["forecast"])
    prob_up = float(parsed.get("prob_up", 0))
    prob_down = float(parsed.get("prob_down", 0))
    confidence = float(parsed.get("confidence", 0))
    if forecast <= 0:
        raise ValueError("forecast must be positive")
    if not (0 <= prob_up <= 1 and 0 <= prob_down <= 1 and 0 <= confidence <= 1):
        raise ValueError("probabilities/confidence must be in [0,1]")
    if parsed["direction_from_prev_close"] not in ("UP", "DOWN", "FLAT"):
        raise ValueError("invalid direction")
    parsed["forecast"] = forecast
    parsed["prob_up"] = prob_up
    parsed["prob_down"] = prob_down
    parsed["confidence"] = confidence
    return parsed


def ensemble(snapshot: dict[str, Any], calls: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    valid = [c for c in calls if isinstance(c.get("json"), dict)]
    daily_rows = snapshot.get("kospi_daily", {}).get("rows", [])
    prev_close = daily_rows[-1]["close"] if daily_rows else 0.0
    realtime = snapshot.get("kospi_realtime", {})
    rt_close = realtime.get("close") or prev_close

    if valid:
        values = [float(c["json"]["forecast"]) for c in valid]
        forecast = sum(values) / len(values)
        prob_up = sum(float(c["json"].get("prob_up", 0.5)) for c in valid) / len(valid)
        prob_down = sum(float(c["json"].get("prob_down", 0.5)) for c in valid) / len(valid)
        confidence = sum(float(c["json"].get("confidence", 0.05)) for c in valid) / len(valid)
        evidence = []
        missing = []
        for c in valid:
            evidence.extend(c["json"].get("evidence", [])[:2])
            missing.extend(c["json"].get("missing_data", []))
    else:
        forecast = rt_close or prev_close
        prob_up = 0.5
        prob_down = 0.5
        confidence = 0.05
        evidence = ["AI advisory calls unavailable; used latest observed KOSPI as conservative anchor."]
        missing = ["gemini_valid_output", "zai_valid_output", "ollama_valid_output"]

    if prev_close > 0:
        if forecast > prev_close + 5:
            direction = "UP"
        elif forecast < prev_close - 5:
            direction = "DOWN"
        else:
            direction = "FLAT"
    else:
        direction = "FLAT"

    return {
        "contestant": "Codex",
        "mode": mode,
        "created_at_kst": snapshot["created_at_kst"],
        "snapshot_hash": snapshot["snapshot_hash"],
        "forecast": round(forecast, 2),
        "direction_from_prev_close": direction,
        "prob_up": round(prob_up, 4),
        "prob_down": round(prob_down, 4),
        "confidence": round(max(0.05, min(0.95, confidence)), 4),
        "evidence": evidence[:6],
        "missing_data": sorted(set(missing)),
        "token_strategy": "raw snapshot stored; compact digest sent to GPT/Z.ai/Gemini/Ollama agents",
        "provider_outputs": calls,
        "rules": {
            "score": "tier by abs(forecast - actual) / actual",
            "tiers": {
                "<=0.25%": 5,
                "<=0.50%": 4,
                "<=0.75%": 3,
                "<=1.00%": 2,
                "<=1.50%": 1,
                ">1.50%": 0,
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["open", "close"], required=True)
    parser.add_argument("--no-ai", action="store_true", help="collect snapshot only; skip GPT/Gemini/Z.ai/Ollama")
    parser.add_argument("--local-only", action="store_true", help="use only local Ollama GLM agent")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    snapshot = collect_snapshot(args.mode)
    stamp = now_kst().strftime("%Y%m%d_%H%M%S")
    snap_path = OUT / f"{stamp}_{args.mode}_snapshot.json"
    snap_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    compact = compact_market_digest(snapshot)
    compact_path = OUT / f"{stamp}_{args.mode}_compact.json"
    compact_path.write_text(json.dumps(compact, ensure_ascii=False, indent=2), encoding="utf-8")

    calls: list[dict[str, Any]] = []
    if not args.no_ai:
        callers = (call_ollama,) if args.local_only else (call_ollama, call_openai_gpt, call_zai, call_gemini)
        for caller in callers:
            try:
                calls.append(caller(compact, args.mode))
            except Exception as exc:
                calls.append({"provider": caller.__name__, "error": repr(exc)})

    forecast = ensemble(snapshot, calls, args.mode)
    out_path = OUT / f"{stamp}_{args.mode}_forecast.json"
    out_path.write_text(json.dumps(forecast, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(forecast, ensure_ascii=False, indent=2))
    print(f"\nSaved snapshot: {snap_path}")
    print(f"Saved compact: {compact_path}")
    print(f"Saved forecast: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
