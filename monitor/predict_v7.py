#!/usr/bin/env python3
"""
predict_v7 — 통합 필승 모델 (4일 대결 교훈 전부 반영)
======================================================
[시가] EWY-앵커: gap = 0.58 x EWY 오버나잇 등락
  근거: EWY = 미국시간 한국 가격발견. 소급 3/3일 <=20pt (6pt/17pt/20pt).
  보정: SOX와 방향 불일치(2%p+ 괴리)시 중간값. 한계 밴드 +-6%.
[종가] robust flow 사다리 (7/1: 4.4pt, 7/2: 73pt 소급검증)
  1. panic:   외인<=-30k AND (외인+기관)<=-20k -> 저가 아래로 continuation
  2. gap실패: 현재<시가-80pt AND (외인<-10k or 프로그램<-8k) -> 하방
  3. 강기관:  기관>+15k & 갭유지 -> 되돌림 상방
  4. 중립:    현수준
[서사] hyperscaler(Meta/MSFT/GOOG/AMZN) capex 악재 감지시 -> bearish 오버라이드(수동 플래그)
사용: python predict_v7.py open [--hyper-bear]   / python predict_v7.py close
"""
import json, re, sys, datetime
import requests
H={"User-Agent":"Mozilla/5.0","Referer":"https://finance.naver.com/"}
K_EWY=0.58
R_RESID=0.5  # 잔차 되돌림(7/3 소급 0.9, n=1이라 보수적 0.5)

def f(x):
    try:return float(str(x).replace(",",""))
    except:return 0.0

def prev_close():
    url=("https://api.finance.naver.com/siseJson.naver?symbol=KOSPI"
         "&requestType=1&startTime=20260601&endTime=20260801&timeframe=day")
    rows=json.loads(requests.get(url,headers=H,timeout=15).text.strip().replace("'",'"'))
    return f(rows[-1][4])

def overnight():
    out={}
    for s,n in [(".SOX","SOX"),(".INX","S&P"),(".IXIC","NASDAQ")]:
        r=requests.get(f"https://api.stock.naver.com/index/{s}/price?pageSize=1&page=1",headers=H,timeout=10).json()
        out[n]=f(r[0].get("fluctuationsRatio")) if r else 0.0
    try:
        out["EWY"]=f(requests.get("https://api.stock.naver.com/stock/EWY/basic",headers=H,timeout=8).json().get("fluctuationsRatio"))
    except Exception:
        out["EWY"]=0.0
    return out

def predict_open(prev,us,hyper_bear=False,prev_kospi_ret=None,prev_ewy=None):
    ewy=us["EWY"]; sox=us["SOX"]
    gap=K_EWY*ewy
    # 잔차항(7/3 교훈): 전일 KOSPI가 EWY-내재를 초과/미달하면 되돌림
    if prev_kospi_ret is not None and prev_ewy is not None:
        overshoot=prev_kospi_ret-K_EWY*prev_ewy
        gap+= -R_RESID*overshoot
    # SOX 교차검증: 방향 불일치+큰 괴리면 절충
    sox_gap=0.5*sox
    if abs(gap-sox_gap)>2.0:
        gap=(gap+sox_gap)/2
    if hyper_bear and gap>-1.0:
        gap=min(gap,-1.0)   # 서사 악재시 상방 차단
    gap=max(-6.0,min(6.0,gap))
    return round(prev*(1+gap/100)), gap

def intraday():
    d=requests.get("https://m.stock.naver.com/api/index/KOSPI/basic",headers=H,timeout=10).json()
    cur=f(d.get("closePrice"))
    url=("https://api.finance.naver.com/siseJson.naver?symbol=KOSPI"
         "&requestType=1&startTime="+datetime.datetime.now().strftime("%Y%m%d")+"&endTime=20991231&timeframe=day")
    r=json.loads(requests.get(url,headers=H,timeout=15).text.strip().replace("'",'"'))[-1]
    o,hi,lo=f(r[1]),f(r[2]),f(r[3])
    today=datetime.datetime.now().strftime("%Y%m%d")
    F=I=0
    rr=requests.get(f"https://finance.naver.com/sise/investorDealTrendDay.naver?bizdate={today}&sosok=01&page=1",headers=H,timeout=12)
    rr.encoding="euc-kr"
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>",rr.text,re.S):
        c=[re.sub(r"<[^>]+>","",x).replace("&nbsp;","").replace(",","").strip() for x in re.findall(r"<td[^>]*>(.*?)</td>",row,re.S)]
        if c and re.match(r"\d{2}\.\d{2}\.\d{2}$",c[0]):
            F,I=int(c[2]),int(c[3]);break
    return o,cur,hi,lo,F,I

def predict_close(o,cur,hi,lo,F,I,P=0,I_prev=0):
    # 하방 애벌란치
    if F<=-30000 and (F+I)<=-20000:
        return round(min(cur,lo)-0.5*(cur-lo)),"panic지속(외인압도)"
    # 상방 애벌란치 (7/3 교훈): 기관 폭주+가속 -> 고가캡 없이 모멘텀 연장
    if I>=20000 and I>=2*max(I_prev,1):
        return round(cur+0.8*(cur-o)),"기관폭주 상방연장(고가캡 해제)"
    if cur<o-80 and ((F<-10000) or (P<-8000)):
        return round(cur-0.40*(cur-lo)),"gap실패+매도(하방)"
    if cur>=o-80 and I>15000:
        return round(cur+0.35*(cur-o)),"강기관 드리프트 연장"
    # 고변동 레짐: 현재가 앵커 폐지 -> 장중 드리프트 1/4 연장
    return round(cur+0.25*(cur-o)),"드리프트 연장(앵커 폐지)"

if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "open"
    hyper="--hyper-bear" in sys.argv
    if mode=="open":
        prev=prev_close(); us=overnight()
        o,gap=predict_open(prev,us,hyper)
        print(f"전일종가 {prev:,.2f} | "+" / ".join(f"{k} {v:+.2f}%" for k,v in us.items()))
        print(f"[v7 시가] {o:,} ({gap:+.2f}%)  EWY-앵커 k={K_EWY}"+("  [서사 bearish]" if hyper else ""))
    else:
        o,cur,hi,lo,F,I=intraday()
        c,m=predict_close(o,cur,hi,lo,F,I)
        print(f"시가{o:,.0f} 현재{cur:,.0f} 고{hi:,.0f} 저{lo:,.0f} 외인{F:+,} 기관{I:+,}")
        print(f"[v7 종가] {c:,} ({m})")
