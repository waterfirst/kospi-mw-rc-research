#!/usr/bin/env python3
"""
시가 맞추기 대결 채점 — 2026-06-30 KOSPI 시가
=============================================
실제 6/30 시가 확정 후 실행. |예측−실제| 작은 쪽 승.

  Claude : 8,435  (band 8,400–8,480)
  Codex  : 8,477  (band 8,420–8,535)

【사용】 python monitor/score_open.py
"""
import json, requests

HEAD = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}
PREV = 8394.65
PRED = {"Claude": 8435, "Codex": 8477}


def kospi_open_0630():
    url = ("https://api.finance.naver.com/siseJson.naver?symbol=KOSPI"
           "&requestType=1&startTime=20260630&endTime=20260703&timeframe=day")
    rows = json.loads(requests.get(url, headers=HEAD, timeout=20).text.strip().replace("'", '"'))
    r = rows[-1]
    return r[0], float(r[1]), float(r[4])  # date, open, close


def main():
    date, o, c = kospi_open_0630()
    print(f"\n=== 시가 대결 채점 — {date} ===")
    print(f"실제 시가 {o:,.2f} (전일 {PREV} 대비 {(o/PREV-1)*100:+.2f}%) | 종가 {c:,.2f}\n")
    res = {}
    for name, p in PRED.items():
        err = abs(p - o)
        errpct = err / o * 100
        res[name] = err
        print(f"{name:7s} 예측 {p:,} → 오차 {err:6.1f}pt ({errpct:.2f}%)")
    win = min(res, key=res.get)
    print(f"\n🏁 시가 대결 승자: {win} (오차 {res[win]:.1f}pt)")


if __name__ == "__main__":
    main()
