#!/usr/bin/env python3
"""
월요일(6/29) 채점기 — Claude 다이오드 vs Codex MW-RC
=====================================================
월요일 장마감 후 실행. 실제 KOSPI 종가·수급을 가져와 루브릭으로 양측 채점.

【고정된 예측 (2026-06-26 미 개장 전, base-rate 정밀화)】
  Claude : 방향 UP(반등), 점 8,520, 밴드 8,360–8,700
           근거: -5%↓ 폭락 다음날 82%(9/11) 반등, 평균 +1.77%
  Codex  : 방향 DOWN(방어), 점 8,340, 밴드 8,250–8,430
  기준 종가(금) : 8,411.21

【사용】 python monitor/score_monday.py
"""

import json, datetime, re
import requests

HEAD = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}
PREV = 8411.21
CLAUDE = {"dir": "UP",   "pt": 8520, "lo": 8360, "hi": 8700}
CODEX  = {"dir": "DOWN", "pt": 8340, "lo": 8250, "hi": 8430}


def latest_close():
    url = ("https://api.finance.naver.com/siseJson.naver?symbol=KOSPI"
           "&requestType=1&startTime=20260626&endTime=20260710&timeframe=day")
    rows = json.loads(requests.get(url, headers=HEAD, timeout=20).text.strip().replace("'", '"'))
    return rows[-1][0], float(rows[-1][4])


def latest_flow():
    today = datetime.datetime.now().strftime("%Y%m%d")
    url = (f"https://finance.naver.com/sise/investorDealTrendDay.naver"
           f"?bizdate={today}&sosok=01&page=1")
    r = requests.get(url, headers=HEAD, timeout=20); r.encoding = "euc-kr"
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", r.text, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        c = [re.sub(r"<[^>]+>", "", x).replace("&nbsp;", "").replace(",", "").strip() for x in cells]
        if c and re.match(r"\d{2}\.\d{2}\.\d{2}$", c[0]):
            return "20" + c[0].replace(".", ""), int(c[1]), int(c[2]), int(c[3])
    return None, 0, 0, 0


def score(m, actual, dsell_on):
    s = 0; detail = []
    act_dir = "UP" if actual >= PREV else "DOWN"
    if m["dir"] == act_dir:
        s += 3; detail.append("방향 +3")
    err = abs(m["pt"] - actual)
    detail.append(f"점오차 {err:.0f}pt")
    if m["lo"] <= actual <= m["hi"]:
        s += 2; detail.append("밴드적중 +2")
    return s, err, detail


def main():
    kdate, close = latest_close()
    fdate, P, F, I = latest_flow()
    dsell_on = (F < 0 and I < 0)
    act_dir = "UP" if close >= PREV else "DOWN"
    print(f"\n=== 월요일 채점 — {kdate} 종가 {close:,.2f} (방향 {act_dir} vs {PREV}) ===")
    print(f"수급 {fdate}: 외국인 {F:+,} 기관 {I:+,} → D_sell {'ON' if dsell_on else 'OFF'}\n")

    cs, ce, cd = score(CLAUDE, close, dsell_on)
    xs, xe, xd = score(CODEX, close, dsell_on)
    # 점오차 비교 보너스
    if ce < xe: cs += 3; cd.append("점오차승 +3")
    elif xe < ce: xs += 3; xd.append("점오차승 +3")
    # 조건부 정합: 반등(UP)=Claude논리, 동반매도하락=Codex논리
    if act_dir == "UP" and not dsell_on: cs += 2; cd.append("조건부정합 +2")
    if act_dir == "DOWN" and dsell_on: xs += 2; xd.append("조건부정합 +2")

    print(f"Claude 다이오드: {cs}점  ({', '.join(cd)})")
    print(f"Codex  MW-RC  : {xs}점  ({', '.join(xd)})")
    print(f"\n🏁 승자: {'Claude' if cs>xs else 'Codex' if xs>cs else '무승부'}")


if __name__ == "__main__":
    main()
