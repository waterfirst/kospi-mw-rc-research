#!/usr/bin/env python3
"""
Claude Consortium 예측 오케스트레이터 (PC측 실행)
==================================================
🤝 구성: Ollama GLM(로컬 GPU) + Gemini(검색) + Z.ai GLM(정량) → 종합 → 텔레그램

【왜 PC측인가】
  원격 Claude는 당신 PC의 GPU/Ollama(localhost:11434)에 도달할 수 없다.
  로컬 GLM 호출은 이 스크립트가 *당신 PC에서* 직접 수행한다.
  각 모델은 선택적: 키/서버 없으면 건너뛰고 가능한 것만으로 종합한다.

【환경변수】
  OLLAMA_HOST     기본 http://localhost:11434, 모델 OLLAMA_MODEL(기본 glm4)
  GEMINI_API_KEY  Gemini (선택)
  ZAI_API_KEY     Z.ai GLM (선택, OpenAI 호환)
  TELEGRAM_TOKEN, TELEGRAM_CHAT_ID  결과 발송(선택)

【사용】 python consortium_forecast.py open   (또는 close)
"""

import os, sys, re, json, datetime
import requests

H = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "glm4")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
ZAI_API_KEY = os.environ.get("ZAI_API_KEY", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

W_SOX, W_SP, W_NQ, W_EWY = 0.40, 0.35, 0.10, 0.15  # EWY 추가(학습 반영)
OPEN_BETA = 0.45


def f(x):
    try: return float(str(x).replace(",", ""))
    except: return 0.0


def market_data():
    d = {}
    url = ("https://api.finance.naver.com/siseJson.naver?symbol=KOSPI"
           "&requestType=1&startTime=20260601&endTime=20260801&timeframe=day")
    rows = json.loads(requests.get(url, headers=H, timeout=15).text.strip().replace("'", '"'))
    closes = [(r[0], f(r[4])) for r in rows[1:]]
    d["last5"] = closes[-5:]
    d["prev_close"] = closes[-1][1]
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
    d["us"] = us
    return d


def diode_baseline(d):
    us = d["us"]
    blend = (W_SOX*us.get("SOX", 0) + W_SP*us.get("S&P", 0) +
             W_NQ*us.get("NASDAQ", 0) + W_EWY*us.get("EWY", 0)) / 100
    return d["prev_close"] * (1 + OPEN_BETA*blend), blend*100


def ask_ollama(prompt):
    try:
        r = requests.post(f"{OLLAMA_HOST}/api/generate",
                          json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
                          timeout=120)
        return r.json().get("response", "").strip()
    except Exception as e:
        return f"(Ollama GLM 불가: {e})"


def ask_gemini(prompt):
    if not GEMINI_API_KEY:
        return "(Gemini 키 없음 — 건너뜀)"
    try:
        url = ("https://generativelanguage.googleapis.com/v1beta/models/"
               f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}")
        r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        return f"(Gemini 불가: {e})"


def ask_zai(prompt):
    if not ZAI_API_KEY:
        return "(Z.ai 키 없음 — 건너뜀)"
    try:
        r = requests.post("https://api.z.ai/api/paas/v4/chat/completions",
                          headers={"Authorization": f"Bearer {ZAI_API_KEY}"},
                          json={"model": "glm-4.6",
                                "messages": [{"role": "user", "content": prompt}]}, timeout=60)
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"(Z.ai 불가: {e})"


def extract_number(text):
    nums = re.findall(r"\b([78]\d{3})(?:\.\d+)?\b", text.replace(",", ""))
    return float(nums[0]) if nums else None


def synthesize(d, base, opinions):
    pts = [base] + [extract_number(o) for _, o in opinions]
    pts = [p for p in pts if p]
    final = round(sum(pts)/len(pts)) if pts else round(base)
    direction = "UP(갭업)" if final >= d["prev_close"] else "DOWN(갭다운)"
    return final, direction, pts


def build_msg(target, d, base, blend, opinions, final, direction):
    us_line = " / ".join(f"{k} {v:+.2f}%" for k, v in d["us"].items())
    L = [f"[Claude] 🤝 컨소시엄 {target.upper()} 예측 — {datetime.datetime.now():%m/%d %H:%M}",
         f"전일 종가 {d['prev_close']:,.2f} | 오버나잇 美 {us_line}",
         f"가중블렌드 {blend:+.2f}% → 다이오드 baseline {base:,.0f}", ""]
    for name, op in opinions:
        n = extract_number(op)
        head = op.splitlines()[0][:55] if op else ""
        L.append(f"· {name}: {n if n else '—'}  {head}")
    L += ["", f"🎯 종합 {target} 예측: {final:,.0f} ({direction})",
          "※ 정보·연구용, 투자판단 본인 — Claude Consortium"]
    return "\n".join(L)


def send_telegram(text):
    if not (TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        print("[텔레그램 미설정] 콘솔:\n" + text); return
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      data={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=15)
        print("텔레그램 발송 완료")
    except Exception as e:
        print(f"발송 실패: {e}\n{text}")


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "open"
    d = market_data()
    base, blend = diode_baseline(d)
    last5 = " -> ".join(f"{c:.0f}" for _, c in d["last5"])
    prompt = (f"너는 KOSPI 정량 예측가다. 내일 KOSPI {target}(open=시가/close=종가)를 "
              f"숫자 하나로 예측하라.\n직전5일 종가: {last5}\n전일종가 {d['prev_close']:.2f}\n"
              f"오버나잇 美(%): {d['us']}\n형식: '예측: XXXX (방향, 한줄근거)'. 4자리 숫자 필수.")
    opinions = [("Ollama GLM(로컬GPU)", ask_ollama(prompt)),
                ("Gemini", ask_gemini(prompt)),
                ("Z.ai GLM", ask_zai(prompt))]
    final, direction, pts = synthesize(d, base, opinions)
    msg = build_msg(target, d, base, blend, opinions, final, direction)
    print(msg + f"\n\n[집계 점추정: {pts}]")
    send_telegram(msg)


if __name__ == "__main__":
    main()
