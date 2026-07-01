#!/usr/bin/env python3
"""
시가 예측 v2 — 오버나잇 US + 전일 한국장 손상도 (Codex 대응)
============================================================
교훈: 미국지수만 보면 안 됨. 전일 국내 손상도(외인/프로그램 매도, 기관방어 크기)가
     시가 US-추종을 감쇠/증폭한다.
  open = prev * (1 + open_beta * US_blend * damage_mult)
  damage_mult<1 : 전일 외인+프로그램 대량매도 -> 상승 추종 약화
  EWY>=+1.5% : trim 해제(강세 풀반영)
【사용】 python open_predict_v2.py
"""
import requests
H = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}


def f(x):
    try: return float(str(x).replace(",", ""))
    except: return 0.0


def us_overnight():
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
    return us


def damage_mult(prev_ret, F, I, P):
    """전일 손상도 -> 상승추종 승수. 대량 외인+프로그램 매도 & 약한 기관 -> 감쇠."""
    m = 1.0
    if F <= -15000: m -= 0.15
    if P <= -10000: m -= 0.10
    if I < 5000:    m -= 0.05
    if prev_ret <= -1.5: m -= 0.05
    return max(0.55, m)


def predict(prev, us, prev_ret, F, I, P):
    blend = (0.40*us["SOX"] + 0.30*us["S&P"] + 0.15*us["NASDAQ"] + 0.15*us["EWY"]) / 100
    dm = damage_mult(prev_ret, F, I, P)
    if us["EWY"] >= 1.5:
        dm = min(1.0, dm + 0.15)
    eff_beta = 0.45 * dm if blend > 0 else 0.45   # 상승만 감쇠, 하락은 그대로
    return round(prev * (1 + eff_beta * blend)), blend*100, dm


if __name__ == "__main__":
    PREV = 8303.41
    prev_ret, F, I, P = -2.04, -17123, 2013, -14067   # 7/1 손상 상태
    us = us_overnight()
    o, b, dm = predict(PREV, us, prev_ret, F, I, P)
    print(f"[7/2 시가 v2] 전일종가 {PREV} | 美 " +
          " / ".join(f"{k} {v:+.2f}%" for k, v in us.items()))
    print(f"US블렌드 {b:+.2f}% | 손상승수 {dm:.2f} (외인{F:+,}/프로그램{P:+,}/기관{I:+,})")
    print(f"시가 예측 {o:,} ({(o/PREV-1)*100:+.2f}%)")
