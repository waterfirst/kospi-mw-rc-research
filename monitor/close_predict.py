#!/usr/bin/env python3
"""
종가 예측 — robust intraday flow 모델 (7/1 패배 교훈 반영)
==========================================================
교훈: D_sell OFF여도 기관방어 미약+외인/프로그램 매도면 하락.
     -> gap-failure 감지 + 수급 magnitude로 종가 추정.

규칙:
  gap_failure = 현재가 < 시가 - 80pt
  bearish = (외국인 < -10,000) or (프로그램 < -8,000)
  방어약함 = 기관 < +10,000
  · gap_failure & bearish -> 종가 ≈ 현재 - 0.40*(현재 - 저가)  # fade가 저점으로 이어짐
  · 그 외 & 강한기관(>+15,000) -> 종가 ≈ 현재 + 0.25*(고가 - 현재)  # 되돌림
  · 중립 -> 종가 ≈ 현재

【사용】 python close_predict.py    (장중 실행)
"""
import json, re, sys
import requests
H={"User-Agent":"Mozilla/5.0","Referer":"https://finance.naver.com/"}
def f(x):
    try:return float(str(x).replace(",",""))
    except:return 0.0

def snapshot(open_=None,cur=None,hi=None,lo=None,F=None,I=None,P=None):
    # 인자 주면 그걸 쓰고(백테스트), 없으면 라이브 수집
    if cur is None:
        d=requests.get("https://m.stock.naver.com/api/index/KOSPI/basic",headers=H,timeout=10).json()
        cur=f(d.get("closePrice"))
        url=("https://api.finance.naver.com/siseJson.naver?symbol=KOSPI"
             "&requestType=1&startTime=20260701&endTime=20260710&timeframe=day")
        r=json.loads(requests.get(url,headers=H,timeout=15).text.strip().replace("'",'"'))[-1]
        open_,hi,lo=f(r[1]),f(r[2]),f(r[3])
        import datetime
        today=datetime.datetime.now().strftime("%Y%m%d")
        u=f"https://finance.naver.com/sise/investorDealTrendDay.naver?bizdate={today}&sosok=01&page=1"
        rr=requests.get(u,headers=H,timeout=12); rr.encoding="euc-kr"
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>",rr.text,re.S):
            c=[re.sub(r"<[^>]+>","",x).replace("&nbsp;","").replace(",","").strip() for x in re.findall(r"<td[^>]*>(.*?)</td>",row,re.S)]
            if c and re.match(r"\d{2}\.\d{2}\.\d{2}$",c[0]):
                F=int(c[2]);I=int(c[3]);break
    P=P if P is not None else 0
    return open_,cur,hi,lo,F,I,P

def predict_close(open_,cur,hi,lo,F,I,P=0):
    gap_fail = cur < open_ - 80
    bearish = (F < -10000) or (P < -8000)
    strong_inst = I > 15000
    # 7/2 교훈: 외인 초대량매도는 기관매수를 압도 -> panic 지속(반등은 함정)
    panic = (F <= -30000) and ((F + I) <= -20000)
    if panic:
        return round(min(cur, lo) - 0.5*(cur - lo)), "panic지속(외인압도)", True, True
    if gap_fail and bearish:
        close = cur - 0.40*(cur - lo); mode="gap실패+매도우위(하방)"
    elif (not gap_fail) and strong_inst:
        close = cur + 0.25*(hi - cur); mode="강한기관방어(되돌림)"
    else:
        close = cur; mode="중립(현수준)"
    return round(close), mode, gap_fail, bearish

if __name__=="__main__":
    if len(sys.argv)>1 and sys.argv[1]=="backtest":
        # 7/1 13:43 스냅샷 소급검증 (실제 종가 8,303.41)
        o,c,hi,lo,F,I,P=8591.5,8402,8620.15,8143.33,-17123,2013,-14067
        close,mode,gf,be=predict_close(o,c,hi,lo,F,I,P)
        print(f"[7/1 백테스트] 예측종가 {close} | {mode} | 실제 8,303 | 오차 {abs(close-8303.41):.1f}pt")
    else:
        o,c,hi,lo,F,I,P=snapshot()
        close,mode,gf,be=predict_close(o,c,hi,lo,F,I,P)
        print(f"시가 {o:,.0f} 현재 {c:,.0f} 고 {hi:,.0f} 저 {lo:,.0f}")
        print(f"외인 {F:+,} 기관 {I:+,} 프로그램 {P:+,} | gap실패={gf} 매도우위={be}")
        print(f"종가 예측 {close:,} ({mode})")
