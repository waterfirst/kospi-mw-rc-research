#!/usr/bin/env python3
"""
대결 채점기 v2 — Claude Consortium vs Codex (10점 만점)
=======================================================
Part 1 시가(5점) + Part 2 종가(5점). 각 모델 독립 정확도 티어 채점.

【룰】
  Part 1: 월 08:00 KST 이전 제출한 *시가* 점예측 → 실제 시가(09:00) 대비 채점
  Part 2: 오전 3회 모니터링(09:00·10:30·12:00) 후 12:30 제출한 *종가* 점예측
          → 실제 종가(15:30) 대비 채점
  티어(오차율=|예측-실제|/실제): ≤0.25%→5, ≤0.5%→4, ≤0.75%→3, ≤1.0%→2, ≤1.5%→1, >1.5%→0
  합산 10점, 총점 높은 쪽 승(동점 시 종가 Part 우선).

【사용】 python monitor/score_duel.py
  실행 전 아래 PRED 딕셔너리에 양측 예측을 채운다(시가는 08:00, 종가는 12:30에 고정).
"""

import json
import requests

HEAD = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}

# ── 예측 입력란 (월요일에 고정) ────────────────────────────────
# open_pred = 08:00 KST 제출 시가 / close_pred = 12:30 KST 제출 종가
#
# ⚠️ 6/29: 공식 시가/종가 분리 제출은 미실행(PC 미가동→오전 모니터링 부재).
#    아래는 *사전 고정된 단일 ex-ante 콜*을 시가·종가에 동일 대입한 대용 채점.
#    (Claude 8,470 = score_monday.py ex-ante / Codex 8,340)
PRED = {
    "Claude Consortium": {"open_pred": 8470, "close_pred": 8470},
    "Codex MW-RC":       {"open_pred": 8340, "close_pred": 8340},
}
# ──────────────────────────────────────────────────────────────


def kospi_ohlc():
    """월요일 일봉 OHLC 반환: (date, open, high, low, close)."""
    url = ("https://api.finance.naver.com/siseJson.naver?symbol=KOSPI"
           "&requestType=1&startTime=20260629&endTime=20260703&timeframe=day")
    rows = json.loads(requests.get(url, headers=HEAD, timeout=20).text.strip().replace("'", '"'))
    r = rows[-1]
    return r[0], float(r[1]), float(r[2]), float(r[3]), float(r[4])


def tier(pred, actual):
    """정확도 티어 점수(0~5)와 오차율(%) 반환."""
    if pred is None:
        return 0, None
    e = abs(pred - actual) / actual * 100
    for thr, pt in ((0.25, 5), (0.50, 4), (0.75, 3), (1.0, 2), (1.5, 1)):
        if e <= thr:
            return pt, e
    return 0, e


def main():
    date, o, h, l, c = kospi_ohlc()
    print(f"\n=== 대결 채점 — {date}  시가 {o:,.2f} / 종가 {c:,.2f} ===\n")

    totals = {}
    for name, p in PRED.items():
        s_open, e_open = tier(p["open_pred"], o)
        s_close, e_close = tier(p["close_pred"], c)
        tot = s_open + s_close
        totals[name] = (tot, s_close)  # 동점 타이브레이크용 종가점수
        eo = f"{e_open:.2f}%" if e_open is not None else "미제출"
        ec = f"{e_close:.2f}%" if e_close is not None else "미제출"
        print(f"[{name}]")
        print(f"  시가 예측 {p['open_pred']}  → 오차 {eo}  → {s_open}/5")
        print(f"  종가 예측 {p['close_pred']} → 오차 {ec} → {s_close}/5")
        print(f"  ▶ 합계 {tot}/10\n")

    (n1, (t1, c1)), (n2, (t2, c2)) = totals.items()
    if   (t1, c1) > (t2, c2): win = n1
    elif (t2, c2) > (t1, c1): win = n2
    else: win = "무승부"
    print(f"🏁 승자: {win}")


if __name__ == "__main__":
    main()
