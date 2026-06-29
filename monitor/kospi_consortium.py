#!/usr/bin/env python3
"""
KOSPI 컨소시엄 예측 — 첨물 PC의 orchestra.py 연동판
=====================================================
당신 PC에 이미 있는 멀티에이전트 CLI(orchestra.py: GPT-5.1/GLM/Gemini/로컬 glm4)를
그대로 호출해 KOSPI 시가/종가를 예측한다. (이미 설정된 키/GPU 재사용)

흐름:
  1) 시장데이터 수집(직전5일 KOSPI/美 오버나잇/EWY)  <- 이 스크립트
  2) orchestra.py 호출:
       quant    "<데이터+질문>"  -> GLM + 로컬 glm4 정량 예측
       ask-local "<질문>"        -> 로컬 glm4 (무료/GPU)
       research "<반도체 뉴스>"  -> Gemini 검색 그라운딩
  3) 각 응답에서 4자리 KOSPI 점추정 파싱 -> 다이오드 baseline과 종합
  4) [Claude] 머릿말로 텔레그램 발송

【설정 (환경변수)】
  ORCHESTRA_PY  = '<ai-env python> <orchestra.py 경로>'
  TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
  USE_AGENTS    = 'quant,ask-local,research'  (부를 명령만 쉼표구분)

【사용】 python kospi_consortium.py open    (또는 close)
"""

import os, sys, re, json, shlex, subprocess, datetime
import requests

H = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}

# 첨물 PC 기본 경로 (환경변수 ORCHESTRA_PY로 덮어쓰기 권장)
ORCHESTRA_PY = os.environ.get(
    "ORCHESTRA_PY",
    "D:/nakcho/python/ai-env/Scripts/python.exe D:/nakcho/python/orchestra/orchestra.py")
USE_AGENTS = os.environ.get("USE_AGENTS", "quant,ask-local,research").split(",")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

W_SOX, W_SP, W_NQ, W_EWY, OPEN_BETA = 0.40, 0.35, 0.10, 0.15, 0.45


def f(x):
    try: return float(str(x).replace(",", ""))
    except: return 0.0


def market_data():
    url = ("https://api.finance.naver.com/siseJson.naver?symbol=KOSPI"
           "&requestType=1&startTime=20260601&endTime=20260801&timeframe=day")
    rows = json.loads(requests.get(url, headers=H, timeout=15).text.strip().replace("'", '"'))
    closes = [(r[0], f(r[4])) for r in rows[1:]]
    us = {}
    for s, name in [(".SOX", "SOX"), (".INX", "S&P"), (".IXIC", "NASDAQ")]:
        try:
            r = requests.get(f"https://api.stock.naver.com/index/{s}/price?pageSize=1&page=1",
                             headers=H, timeout=10).json()
            us[name] = f(r[0].get("fluctuationsRatio")) if r else 0.0
        except Exception:
            us[name] = 0.0
    try:
        r = requests.get("https://api.stock.naver.com/stock/EWY/basic", headers=H, timeout=10).json()
        us["EWY"] = f(r.get("fluctuationsRatio"))
    except Exception:
        us["EWY"] = 0.0
    return {"last5": closes[-5:], "prev_close": closes[-1][1], "us": us}


def diode_baseline(d):
    us = d["us"]
    blend = (W_SOX*us.get("SOX", 0) + W_SP*us.get("S&P", 0) +
             W_NQ*us.get("NASDAQ", 0) + W_EWY*us.get("EWY", 0)) / 100
    return d["prev_close"] * (1 + OPEN_BETA*blend), blend*100


def call_orchestra(command, text):
    try:
        argv = shlex.split(ORCHESTRA_PY) + [command, text]
        r = subprocess.run(argv, capture_output=True, text=True, timeout=180,
                           encoding="utf-8", errors="replace")
        return (r.stdout or "").strip() or (r.stderr or "").strip()
    except Exception as e:
        return f"(orchestra {command} 불가: {e})"


def extract_number(text):
    nums = re.findall(r"\b([78]\d{3})(?:\.\d+)?\b", (text or "").replace(",", ""))
    return float(nums[0]) if nums else None


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "open"
    d = market_data()
    base, blend = diode_baseline(d)
    last5 = " -> ".join(f"{c:.0f}" for _, c in d["last5"])
    q = (f"내일 KOSPI {target}(open=시가/close=종가)를 숫자 하나로 예측. "
         f"직전5일 종가 {last5}, 전일종가 {d['prev_close']:.2f}, "
         f"오버나잇 美(%) {d['us']}. 형식 '예측: XXXX (방향, 한줄근거)', 4자리 숫자 필수.")

    opinions = []
    if "quant" in USE_AGENTS:
        opinions.append(("quant(GLM+local)", call_orchestra("quant", q)))
    if "ask-local" in USE_AGENTS:
        opinions.append(("local(glm4 GPU)", call_orchestra("ask-local", q)))
    if "research" in USE_AGENTS:
        opinions.append(("research(Gemini)",
                         call_orchestra("research", "오늘 미국 반도체/엔비디아/KOSPI 최신 뉴스 3줄 요약")))

    pts = [base] + [extract_number(o) for _, o in opinions]
    pts = [p for p in pts if p]
    final = round(sum(pts) / len(pts)) if pts else round(base)
    direction = "UP(갭업)" if final >= d["prev_close"] else "DOWN(갭다운)"

    us_line = " / ".join(f"{k} {v:+.2f}%" for k, v in d["us"].items())
    L = [f"[Claude] 컨소시엄 {target.upper()} 예측 - {datetime.datetime.now():%m/%d %H:%M}",
         f"전일 종가 {d['prev_close']:,.2f} | 오버나잇 美 {us_line}",
         f"가중블렌드 {blend:+.2f}% -> 다이오드 baseline {base:,.0f}", ""]
    for name, op in opinions:
        n = extract_number(op)
        head = (op.splitlines()[0][:55] if op else "")
        L.append(f"- {name}: {n if n else '-'}  {head}")
    L += ["", f"종합 {target} 예측: {final:,.0f} ({direction})",
          "정보/연구용, 투자판단 본인 - Claude Consortium"]
    msg = "\n".join(L)
    print(msg + f"\n\n[집계 점추정: {pts}]")

    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                          data={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=15)
            print("텔레그램 발송 완료")
        except Exception as e:
            print(f"발송 실패: {e}")


if __name__ == "__main__":
    main()
