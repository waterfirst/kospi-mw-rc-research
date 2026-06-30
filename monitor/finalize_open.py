#!/usr/bin/env python3
"""
07:30 시가 최종결정 — 자기완결 (런타임 Claude 토큰 0, 로컬, <1s)
================================================================
밤사이 미 종가 자동수집 -> Diode v5 + Codex MW-RC 즉시계산 -> 종합 -> [Claude] 텔레그램.
LLM 호출 없이 숫자 산출(고속/저비용). 스케줄러가 평일 07:30 실행.
설정: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
"""
import os, json, re, datetime
import requests

H = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}
TG_T = os.environ.get("TELEGRAM_TOKEN", ""); TG_C = os.environ.get("TELEGRAM_CHAT_ID", "")


def f(x):
    try: return float(str(x).replace(",", ""))
    except: return 0.0


def fetch():
    url = ("https://api.finance.naver.com/siseJson.naver?symbol=KOSPI"
           "&requestType=1&startTime=20260601&endTime=20260801&timeframe=day")
    rows = json.loads(requests.get(url, headers=H, timeout=15).text.strip().replace("'", '"'))
    prev = f(rows[-1][4])
    us = {}
    for s, n in [(".SOX", "SOX"), (".INX", "S&P"), (".IXIC", "NASDAQ"), (".DJI", "DOW")]:
        r = requests.get(f"https://api.stock.naver.com/index/{s}/price?pageSize=1&page=1",
                         headers=H, timeout=10).json()
        us[n] = f(r[0].get("fluctuationsRatio")) if r else 0.0
    try:
        us["EWY"] = f(requests.get("https://api.stock.naver.com/stock/EWY/basic",
                                   headers=H, timeout=8).json().get("fluctuationsRatio"))
    except Exception:
        us["EWY"] = 0.0
    F = 0
    try:
        today = datetime.datetime.now().strftime("%Y%m%d")
        r = requests.get(f"https://finance.naver.com/sise/investorDealTrendDay.naver"
                         f"?bizdate={today}&sosok=01&page=1", headers=H, timeout=10)
        r.encoding = "euc-kr"
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", r.text, re.S):
            c = [re.sub(r"<[^>]+>", "", x).replace("&nbsp;", "").replace(",", "").strip()
                 for x in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
            if c and re.match(r"\d{2}\.\d{2}\.\d{2}$", c[0]):
                F = int(c[2]); break
    except Exception:
        pass
    return prev, us, F


def main():
    prev, us, F = fetch()
    # Diode v5 (국내수급 앵커, beta 0.45, EWY 포함)
    bd = (0.40*us["SOX"] + 0.30*us["S&P"] + 0.15*us["NASDAQ"] + 0.15*us["EWY"]) / 100
    do = prev * (1 + 0.45 * bd)
    # Codex MW-RC (SOX가중, beta 0.42)
    bc = (0.45*us["SOX"] + 0.25*us["NASDAQ"] + 0.15*us["S&P"] + 0.10*us["EWY"] + 0.05*us["DOW"]) / 100
    co = prev * (1 + 0.42 * bc)
    # 종합: 7월 진입 월말드래그 완화 -> Diode 0.55 / Codex 0.45, 외인 강매도 지속 시 소폭 하향
    final = 0.55 * do + 0.45 * co
    if F <= -30000:
        final *= 0.9985
    final = round(final)
    direction = "UP(갭업)" if final >= prev else "DOWN(갭다운)"
    msg = "\n".join([
        f"[Claude] 7/1 시가 최종결정 - {datetime.datetime.now():%m/%d %H:%M}",
        f"전일 종가 {prev:,.2f} | 밤사이 美 " + " / ".join(f"{k} {v:+.2f}%" for k, v in us.items()),
        f"외국인 직전 {F:+,} (월말종료, 드래그 {'유지' if F<=-30000 else '완화'})",
        f"Diode v5 {do:,.0f} | Codex MW-RC {co:,.0f}",
        f"종합 시가 예측: {final:,.0f} ({direction}) | 범위 {final*0.993:,.0f}~{final*1.007:,.0f}",
        "정보/연구용, 투자판단 본인 - Claude",
    ])
    print(msg)
    if TG_T and TG_C:
        try:
            requests.post(f"https://api.telegram.org/bot{TG_T}/sendMessage",
                          data={"chat_id": TG_C, "text": msg}, timeout=15); print("발송 완료")
        except Exception as e:
            print("발송 실패:", e)


if __name__ == "__main__":
    main()
