#!/usr/bin/env python3
"""
KOSPI 오전 모니터링 — 09:00 / 10:30 / 12:00 체크포인트 + 텔레그램 발송
======================================================================
스케줄러가 하루 3회 실행. 매번: 실시간 지수 + 장중 외국인·기관 잠정수급 +
오버나잇 美 → 다이오드 판정 → 텔레그램 발송 (12:00엔 종가 예측 포함).

【무인 자동발송 = 텔레그램】 (카카오 MemoChat은 매번 수동승인 필요 → 자동화 불가)
  환경변수: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID (필수)
            ANTHROPIC_API_KEY (선택, Claude 자연어 분석)

【사용】 python morning_monitor.py 0900   (라벨 생략 시 현재시각 자동)
"""

import os, sys, re, json, datetime
import requests

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
H = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}

C_FLOW, K_CASCADE, TAU = 0.017, 1.784, 2.319
BT_ON  = {"mean": -1.19, "down": 80.1}
BT_OFF = {"mean": +0.68, "down": 29.4}


def f(x):
    try: return float(str(x).replace(",", ""))
    except: return 0.0


def kospi_live():
    d = requests.get("https://m.stock.naver.com/api/index/KOSPI/basic",
                     headers=H, timeout=12).json()
    return (f(d.get("closePrice")), f(d.get("compareToPreviousClosePrice")),
            f(d.get("fluctuationsRatio")), d.get("marketStatus", ""))


def prev_close():
    url = ("https://api.finance.naver.com/siseJson.naver?symbol=KOSPI"
           "&requestType=1&startTime=20260601&endTime=20260801&timeframe=day")
    rows = json.loads(requests.get(url, headers=H, timeout=15).text.strip().replace("'", '"'))
    return f(rows[-2][4])


def intraday_flow():
    today = datetime.datetime.now().strftime("%Y%m%d")
    url = (f"https://finance.naver.com/sise/investorDealTrendDay.naver"
           f"?bizdate={today}&sosok=01&page=1")
    r = requests.get(url, headers=H, timeout=12); r.encoding = "euc-kr"
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", r.text, re.S):
        c = [re.sub(r"<[^>]+>", "", x).replace("&nbsp;", "").replace(",", "").strip()
             for x in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        if c and re.match(r"\d{2}\.\d{2}\.\d{2}$", c[0]):
            return "20" + c[0].replace(".", ""), int(c[1]), int(c[2]), int(c[3])
    return None, 0, 0, 0


def us_overnight():
    out = {}
    for s, name in [(".INX", "S&P"), (".IXIC", "나스닥"), (".SOX", "SOX")]:
        try:
            rows = requests.get(f"https://api.stock.naver.com/index/{s}/price?pageSize=1&page=1",
                                headers=H, timeout=10).json()
            out[name] = f(rows[0].get("fluctuationsRatio")) if rows else 0.0
        except Exception:
            out[name] = 0.0
    return out


def build_message(label, price, chg, chgpct, status, fdate, P, F, I, us, prevc):
    d_sell = (F < 0 and I < 0)
    st = BT_ON if d_sell else BT_OFF
    state = ("🔴 D_sell ON (외국인+기관 동반매도)" if d_sell
             else ("🟢 D_sell OFF (기관 매수 — 폭락방어)" if I > 0
                   else "🟡 D_sell OFF (기관 매도지만 외국인 단독)"))
    frgn = "매수" if F > 0 else "매도"
    inst = "매수" if I > 0 else ("매도" if I < 0 else "중립")
    us_line = " / ".join(f"{k} {v:+.2f}%" for k, v in us.items())
    lines = [
        f"📡 KOSPI 오전모니터 [{label}] — {datetime.datetime.now():%m/%d %H:%M}",
        f"지수 {price:,.2f} ({chg:+.2f}, {chgpct:+.2f}%) [{status}]",
        "", state,
        f"· 외국인 {F:+,}({frgn}) / 기관 {I:+,}({inst}) (백만, 잠정)",
        f"· 개인 {P:+,}",
        f"· 오버나잇 美: {us_line}",
        "",
        f"📊 이 상태 기대: 평균 {st['mean']:+.2f}%/일, 하락확률 {st['down']:.0f}% (604일)",
        ("⚠️ 동반매도 점화 — 과거 -5%↓ 폭락의 83%가 이 상태. 신규진입 보류·현금우위."
         if d_sell else
         "기관이 받치는 한 폭락 회피. 외국인 매도 단독으론 붕괴 안 함."),
    ]
    if label.startswith("12"):
        if d_sell:
            shock = K_CASCADE * (abs(F + I) / 1e6) / C_FLOW
            close_est = price - shock * 0.25
            note = f"동반매도 지속 시 오후 추가하방(-{shock*0.25:.0f}pt) 베이스"
        else:
            close_est = price
            note = "기관 방어 — 현수준 보합 베이스, 외국인 둔화 시 반등"
        lines += ["", f"🎯 종가 예측(12:00 기준): ~{close_est:,.0f}", f"   {note}"]
    lines += ["", "※ 동시점 진단·경보용(익일 점예측 제한). 투자판단 본인 — Claude 다이오드 v5"]
    return d_sell, "\n".join(lines)


def claude_analysis(ctx):
    if not ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic
        c = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        m = c.messages.create(model="claude-sonnet-4-6", max_tokens=400,
            messages=[{"role": "user", "content":
                "너는 KOSPI 다이오드 분석가다. 다음 장중 스냅샷으로 2~3문장, "
                "비대칭 베팅·손절선 관점 조언. 투자자문 아님 명시.\n\n" + ctx}])
        return m.content[0].text
    except Exception as e:
        return f"(Claude 분석 실패: {e})"


def send_telegram(text):
    if not (TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        print("[텔레그램 미설정] 콘솔 출력:\n" + text)
        return
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      data={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=15)
        print("텔레그램 발송 완료")
    except Exception as e:
        print(f"발송 실패: {e}\n{text}")


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else datetime.datetime.now().strftime("%H%M")
    try:
        price, chg, chgpct, status = kospi_live()
        prevc = prev_close()
        fdate, P, F, I = intraday_flow()
        us = us_overnight()
        d_sell, msg = build_message(label, price, chg, chgpct, status, fdate, P, F, I, us, prevc)
        if ANTHROPIC_API_KEY:
            ctx = (f"[{label}] KOSPI {price:.0f}({chgpct:+.2f}%), 외국인 {F:+}, 기관 {I:+}, "
                   f"D_sell={'ON' if d_sell else 'OFF'}, 美 {us}")
            ai = claude_analysis(ctx)
            if ai:
                msg += "\n\n🤖 Claude 분석:\n" + ai
        send_telegram(msg)
    except Exception as e:
        send_telegram(f"⚠️ 모니터 오류 [{label}]: {e}")


if __name__ == "__main__":
    main()
