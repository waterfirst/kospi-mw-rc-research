#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import time
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "contest" / "news"
STATE = OUT / "seen_news.json"

QUERIES = [
    "Meta excess AI compute cloud business semiconductor stocks",
    "Meta AI compute capacity Nvidia HBM memory stocks",
    "AI infrastructure oversupply semiconductor selloff",
    "hyperscaler capex cuts Nvidia HBM Samsung SK Hynix",
    "Microsoft Google Amazon Meta AI capex Nvidia memory",
    "Samsung SK Hynix shares Meta AI compute selloff",
    "KOSPI semiconductor foreign selling program trading",
]

NEGATIVE_TERMS = [
    "excess compute",
    "excess capacity",
    "oversupply",
    "selloff",
    "plunge",
    "crash",
    "slump",
    "capex cuts",
    "capacity",
    "cloud business",
    "ai infrastructure",
]

POSITIVE_TERMS = [
    "buy",
    "deal",
    "partnership",
    "sold out",
    "surge",
    "record",
    "beat",
    "approval",
]

KEY_NAMES = ["meta", "nvidia", "samsung", "sk hynix", "hbm", "memory", "semiconductor", "kospi"]


def now_kst() -> dt.datetime:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))


def load_seen() -> set[str]:
    if not STATE.exists():
        return set()
    try:
        return set(json.loads(STATE.read_text(encoding="utf-8")))
    except Exception:
        return set()


def save_seen(seen: set[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(sorted(seen)[-2000:], ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_query(query: str) -> list[dict[str, Any]]:
    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(query) + "&hl=en-US&gl=US&ceid=US:en"
    text = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20).text
    root = ET.fromstring(text)
    items = []
    for item in root.findall(".//item")[:8]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        if not title:
            continue
        items.append({"query": query, "title": title, "link": link, "pubDate": pub})
    return items


def classify(item: dict[str, Any]) -> dict[str, Any]:
    title = item["title"].lower()
    neg = [t for t in NEGATIVE_TERMS if t in title]
    pos = [t for t in POSITIVE_TERMS if t in title]
    names = [t for t in KEY_NAMES if t in title]
    score = 2 * len(neg) - len(pos)
    if "meta" in names and ("excess" in title or "capacity" in title or "cloud" in title):
        score += 4
    if any(x in names for x in ["samsung", "sk hynix", "hbm", "memory"]) and score > 0:
        score += 2
    if score >= 5:
        severity = "HIGH"
    elif score >= 2:
        severity = "MEDIUM"
    elif score <= -2:
        severity = "POSITIVE"
    else:
        severity = "LOW"
    return {"negative_hits": neg, "positive_hits": pos, "names": names, "score": score, "severity": severity}


def send_telegram(text: str) -> bool:
    token = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": text}, timeout=20)
    r.raise_for_status()
    return bool((r.json() or {}).get("ok"))


def build_message(item: dict[str, Any], meta: dict[str, Any]) -> str:
    return "\n".join([
        f"[Codex] NEWS SHOCK {meta['severity']} score={meta['score']} {now_kst().strftime('%H:%M KST')}",
        item["title"],
        f"hits: neg={','.join(meta['negative_hits']) or '-'} names={','.join(meta['names']) or '-'}",
        item.get("link", ""),
    ])


def poll_once(send: bool) -> dict[str, Any]:
    seen = load_seen()
    new_alerts = []
    all_items = []
    for q in QUERIES:
        try:
            for item in fetch_query(q):
                key = item.get("link") or item["title"]
                all_items.append(item)
                if key in seen:
                    continue
                seen.add(key)
                meta = classify(item)
                item["classification"] = meta
                if meta["severity"] in {"HIGH", "MEDIUM", "POSITIVE"}:
                    new_alerts.append(item)
                    if send:
                        send_telegram(build_message(item, meta))
        except Exception as exc:
            all_items.append({"query": q, "error": repr(exc)})
    save_seen(seen)
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = now_kst().strftime("%Y%m%d_%H%M%S")
    path = OUT / f"{stamp}_news_poll.json"
    payload = {"created_at_kst": now_kst().isoformat(timespec="seconds"), "alerts": new_alerts, "items": all_items[:80]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved={path}")
    print(f"alerts={len(new_alerts)}")
    for item in new_alerts[:5]:
        print(build_message(item, item["classification"]))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, default=900)
    parser.add_argument("--telegram", action="store_true")
    args = parser.parse_args()

    if args.once:
        poll_once(args.telegram)
        return 0
    while True:
        poll_once(args.telegram)
        time.sleep(max(60, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
