#!/usr/bin/env python3
"""미국 세션 폴러 — 개장~중반 추적, 로그 + JSON 스냅샷."""
import requests, datetime, json, time, sys

H = {"User-Agent": "Mozilla/5.0"}
SYMS = [(".SOX", "SOX"), (".INX", "S&P"), (".IXIC", "NASDAQ"), (".DJI", "DOW")]
STOCKS = [("EWY", "EWY"), ("MU", "MU")]
LOG = "monitor/live/us_session.log"
SNAP = "monitor/live/us_snapshot.json"


def f(x):
    try: return float(str(x).replace(",", ""))
    except: return 0.0


def poll():
    out = {}
    for s, name in SYMS:
        try:
            b = requests.get(f"https://api.stock.naver.com/index/{s}/basic",
                             headers=H, timeout=12).json()
            out[name] = {"close": f(b.get("closePrice")),
                         "chg": f(b.get("fluctuationsRatio")),
                         "status": b.get("marketStatus", ""),
                         "at": b.get("localTradedAt", "")}
        except Exception as e:
            out[name] = {"err": str(e)}
    for tk, name in STOCKS:
        try:
            b = requests.get(f"https://api.stock.naver.com/stock/{tk}/basic",
                             headers=H, timeout=12).json()
            out[name] = {"close": f(b.get("closePrice")),
                         "chg": f(b.get("fluctuationsRatio")),
                         "status": b.get("marketStatus", "")}
        except Exception as e:
            out[name] = {"err": str(e)}
    return out


def main():
    minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    interval = 360  # 6 min
    end = minutes * 60
    elapsed = 0
    while elapsed <= end:
        snap = poll()
        ts = datetime.datetime.now().strftime("%H:%M KST")
        line = ts + " | " + " | ".join(
            f"{n}:{d.get('chg',0):+.2f}%[{d.get('status','')[:4]}]"
            for n, d in snap.items())
        with open(LOG, "a") as fp:
            fp.write(line + "\n")
        with open(SNAP, "w") as fp:
            json.dump({"ts": ts, "data": snap}, fp, ensure_ascii=False, indent=2)
        print(line, flush=True)
        # 모두 CLOSE면 조기 종료
        if all(d.get("status") in ("CLOSE", "AFTERMARKET") for d in snap.values()):
            print("미 정규장 마감 감지 — 종료", flush=True)
            break
        time.sleep(interval)
        elapsed += interval


if __name__ == "__main__":
    main()
