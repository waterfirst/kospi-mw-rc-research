#!/usr/bin/env python3
"""
시장 온도계 — 다요인 KOSPI 틸트 (Claude 강점: US 외 신호 종합)
================================================================
Codex의 US-베타 단일축을 넘어, 환율·금리·외인플로우·달러·원자재·뉴스/서사를
각각 점수화(-2..+2)해 KOSPI 시가/종가 틸트로 합성.

각 요인 score는 데이터로 채우거나(자동) 인자로 주입. 미국지수는 네이버 자동수집.
뉴스/서사 score는 orchestra research(Gemini) 또는 Claude 주입.

【사용】 python thermometer.py    (기본값=웹조사 스냅샷, 실행시 US만 갱신)
"""
import os, json, datetime
import requests

H = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}


def f(x):
    try: return float(str(x).replace(",", ""))
    except: return 0.0


def fetch_us_kospi():
    url = ("https://api.finance.naver.com/siseJson.naver?symbol=KOSPI"
           "&requestType=1&startTime=20260601&endTime=20260801&timeframe=day")
    rows = json.loads(requests.get(url, headers=H, timeout=15).text.strip().replace("'", '"'))
    prev = f(rows[-1][4])
    us = {}
    for s, n in [(".SOX", "SOX"), (".INX", "S&P"), (".IXIC", "NASDAQ")]:
        r = requests.get(f"https://api.stock.naver.com/index/{s}/price?pageSize=1&page=1",
                         headers=H, timeout=10).json()
        us[n] = f(r[0].get("fluctuationsRatio")) if r else 0.0
    return prev, us


def clamp(v, lo=-2, hi=2):
    return max(lo, min(hi, v))


# ── 요인 점수화 (-2 매우약세 ~ +2 매우강세, KOSPI 관점) ──
def score_us(us):
    blend = 0.5*us.get("SOX", 0) + 0.3*us.get("NASDAQ", 0) + 0.2*us.get("S&P", 0)
    return clamp(blend / 1.5)            # +1.5% -> +1.0점

def score_fx(usdkrw):
    # 원화 약세(고환율)=외인이탈=KOSPI 악재. 1,450 중립, 1,550+ 강한 악재
    return clamp(-(usdkrw - 1450) / 50)  # 1550 -> -2.0

def score_rategap(us_kr_gap_pp):
    return clamp(-us_kr_gap_pp / 1.0)    # 1.5%p -> -1.5

def score_foreign(flow_5d_avg):
    # 외국인 최근 평균 순매수(백만). 음수=매도=악재
    return clamp(flow_5d_avg / 20000)    # -40,000 -> -2.0

def score_dxy(dxy_chg_pct):
    return clamp(-dxy_chg_pct / 0.5)     # 달러강세=신흥국악재

def score_oil(oil_chg_pct):
    return clamp(oil_chg_pct / 3.0)      # 유가상승 약한 긍정(경기)

def score_news(news_tilt):
    return clamp(news_tilt)              # -2..+2, Claude/Gemini 주입


WEIGHTS = {"US": 0.34, "FX": 0.20, "RateGap": 0.10, "Foreign": 0.20,
           "DXY": 0.06, "Oil": 0.04, "News": 0.06}


def thermometer(prev, us, usdkrw, rategap, foreign5d, dxy_chg, oil_chg, news_tilt):
    s = {"US": score_us(us), "FX": score_fx(usdkrw), "RateGap": score_rategap(rategap),
         "Foreign": score_foreign(foreign5d), "DXY": score_dxy(dxy_chg),
         "Oil": score_oil(oil_chg), "News": score_news(news_tilt)}
    composite = sum(WEIGHTS[k] * s[k] for k in s)        # -2..+2
    tilt_pct = composite * 0.6                            # 점수 -> KOSPI 일중틸트%(±1.2% 캡)
    return s, composite, tilt_pct


if __name__ == "__main__":
    prev, us = fetch_us_kospi()
    # 웹조사 스냅샷(2026-06-30): 1차값. 07:30 최종땐 실측 갱신.
    usdkrw   = f(os.environ.get("USDKRW", "1554"))
    rategap  = f(os.environ.get("RATEGAP", "1.5"))    # US-KR %p
    foreign5d= f(os.environ.get("FOREIGN5D", "-38000"))
    dxy_chg  = f(os.environ.get("DXY_CHG", "0"))
    oil_chg  = f(os.environ.get("OIL_CHG", "0"))
    news_tilt= f(os.environ.get("NEWS_TILT", "-0.3"))  # 고환율·외인이탈 서사 약한 악재

    s, comp, tilt = thermometer(prev, us, usdkrw, rategap, foreign5d, dxy_chg, oil_chg, news_tilt)
    base_us = prev * (1 + 0.45 * (0.4*us["SOX"]+0.3*us["S&P"]+0.15*us["NASDAQ"]) / 100)
    final = base_us * (1 + tilt/100 * 0.5)   # US베타 + 온도계틸트 절반 반영
    print(f"[온도계] 6/30종가 {prev:,.0f} | USD/KRW {usdkrw:.0f} | 금리차 {rategap}%p")
    for k in s:
        print(f"  {k:8s} {s[k]:+.2f}  (w {WEIGHTS[k]})")
    print(f"종합점수 {comp:+.2f} -> 틸트 {tilt:+.2f}%")
    print(f"US베타 시가 {base_us:,.0f} -> 온도계 보정 최종 {final:,.0f} ({(final/prev-1)*100:+.2f}%)")
