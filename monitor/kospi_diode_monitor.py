#!/usr/bin/env python3
"""
KOSPI 다이오드 장중 모니터 — D_sell 점화 경보 + Claude 분석 알림
================================================================
2026-06-26 | Claude

【정직한 전제 — 누가 모니터링하는가】
  이 스크립트는 *첨물의 PC*에서 돌아간다. 원격 세션의 Claude는 임시
  컨테이너라 24시간 상주하지 못한다. 따라서 구조는:
    [첨물 PC: 이 스크립트 상주] → 수급 폴링 → D_sell 점화 감지
      → (선택) Claude API로 다이오드 분석 생성 → 텔레그램으로 첨물에게 발송
  즉 "Claude가 보내는 메시지"는 이 스크립트가 Claude API를 호출해
  생성한 분석을, 첨물의 텔레그램으로 전달하는 형태로 구현된다.

【설정】 환경변수 또는 아래 상수
  TELEGRAM_TOKEN, TELEGRAM_CHAT_ID : 텔레그램 봇 (필수, 알림용)
  ANTHROPIC_API_KEY                : Claude 자연어 분석 (선택)
  POLL_MINUTES                     : 폴링 주기 (기본 30분)

【사용】
  pip install requests anthropic
  set TELEGRAM_TOKEN=...   (Windows) / export (mac·linux)
  python kospi_diode_monitor.py

【한계 (백테스트 H3에서 입증)】
  · 일별 확정 수급은 장마감 후 정보 → 익일 점예측력 없음(평균회귀).
  · 따라서 본 모니터의 진짜 가치는 *장중 실시간 누적 수급*으로
    D_sell 점화 시점을 조기 포착하는 데 있다(가능한 범위 best-effort).
  · 장중 실시간 외국인·기관 순매수는 무료 소스가 지연/부정확할 수 있다.
    확정치는 장마감 후 재확인된다.
"""

import os, time, datetime, re, json
import requests

# ── 설정 ───────────────────────────────────────────────────────
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
POLL_MINUTES = int(os.environ.get("POLL_MINUTES", "30"))

# ── 실측 모델 파라미터 (604일 백테스트) ─────────────────────────
C_FLOW, K_CASCADE, TAU = 0.017, 1.784, 2.319
BT_ON  = {"mean": -1.19, "down": 80.1}   # D_sell ON 통계
BT_OFF = {"mean": +0.68, "down": 29.4}

HEAD = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}


# ── 데이터 수집 ─────────────────────────────────────────────────
def fetch_latest_close():
    """KOSPI 최근 종가."""
    url = ("https://api.finance.naver.com/siseJson.naver?symbol=KOSPI"
           "&requestType=1&startTime=20260601&endTime=20260701&timeframe=day")
    r = requests.get(url, timeout=20, headers=HEAD)
    rows = json.loads(r.text.strip().replace("'", '"'))
    last = rows[-1]
    return last[0], float(last[4])  # date, close


def fetch_latest_flow():
    """최근 영업일 외국인·기관·개인 순매매 (확정치, 장마감 후).
    장중에는 전일 확정치 + 당일 잠정치가 섞일 수 있음."""
    today = datetime.datetime.now().strftime("%Y%m%d")
    url = (f"https://finance.naver.com/sise/investorDealTrendDay.naver"
           f"?bizdate={today}&sosok=01&page=1")
    r = requests.get(url, timeout=20, headers=HEAD); r.encoding = "euc-kr"
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", r.text, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        c = [re.sub(r"<[^>]+>", "", x).replace("&nbsp;", "").replace(",", "").strip()
             for x in cells]
        if c and re.match(r"\d{2}\.\d{2}\.\d{2}$", c[0]):
            d = "20" + c[0].replace(".", "")
            return d, int(c[1]), int(c[2]), int(c[3])  # date, 개인, 외국인, 기관
    return None, 0, 0, 0


# ── 다이오드 모델 ───────────────────────────────────────────────
def diode_predict(v_prev, v_tgt, F, I):
    """F, I: 순매수 (양수=매수). 단위 무관(부호로 D_sell, 크기로 충격 스케일)."""
    d_sell = (F < 0 and I < 0)
    # 네이버 수급 단위(백만원)를 조원으로 환산: /1e6 (백만→조). 안전하게 절대비율로.
    net_trillion = abs(F + I) / 1e6 if d_sell else 0
    shock = K_CASCADE * net_trillion / C_FLOW
    restore = (v_tgt - v_prev) / TAU
    return d_sell, v_prev + restore - shock, shock, restore


def build_alert(date, close, F, I, v_tgt):
    d_sell, pred, shock, restore = diode_predict(close, v_tgt, F, I)
    st = BT_ON if d_sell else BT_OFF
    state = "🔴 D_sell ON (외국인+기관 동반매도)" if d_sell else "🟢 D_sell OFF"
    inst = "기관 매수" if I > 0 else ("기관 매도" if I < 0 else "기관 중립")
    frgn = "외국인 매수" if F > 0 else "외국인 매도"
    lines = [
        f"📡 KOSPI 다이오드 신호 — {date}",
        f"종가 {close:,.0f}",
        "",
        f"{state}",
        f"· {frgn} {F:+,} / {inst} {I:+,} (백만원)",
        f"· 다이오드 판정: {'점화(공황충격)' if d_sell else '차단(충격 없음)'}",
        "",
        f"백테스트 기대: 이 상태 평균 {st['mean']:+.2f}%/일, 하락확률 {st['down']:.0f}%",
        f"(604일 실측, ON평균 -1.19% / OFF +0.68%, t=9.55)",
        "",
        ("⚠️ 동반매도 점화. 과거 이 상태에서 -5%↓ 폭락의 83%가 발생."
         if d_sell else
         "기관이 받치는 한 회복 경로. 외국인 매도만으로는 폭락 안 함."),
        "",
        "※ 다이오드는 동시점 진단에 강함. 익일 점예측은 제한적(평균회귀).",
        "※ 정보·연구용, 투자판단은 본인. — Claude 다이오드 모델 v5",
    ]
    return d_sell, "\n".join(lines)


# ── Claude API 자연어 분석 (선택) ───────────────────────────────
def claude_analysis(context):
    if not ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            messages=[{"role": "user", "content":
                "너는 KOSPI 다이오드 모델 분석가다. 다음 장중 수급으로 투자 판단을 "
                "3문장 이내로, 비대칭 베팅·손절선 관점에서 조언하라. 투자자문 아님 명시.\n\n"
                + context}],
        )
        return msg.content[0].text
    except Exception as e:
        return f"(Claude 분석 실패: {e})"


# ── 텔레그램 발송 ───────────────────────────────────────────────
def send_telegram(text):
    if not (TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        print("[텔레그램 미설정] 콘솔 출력:\n" + text + "\n")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=15)
    except Exception as e:
        print(f"텔레그램 발송 실패: {e}")


# ── 메인 루프 ───────────────────────────────────────────────────
def estimate_vtarget(close):
    """V_target 추정: 미국신호 미연동 기본값(전고점 9114.55). v6에서 S&P·SOX 연동."""
    return 9114.55


def main():
    print(f"KOSPI 다이오드 모니터 시작 — 폴링 {POLL_MINUTES}분")
    print(f"텔레그램: {'ON' if TELEGRAM_TOKEN else 'OFF(콘솔출력)'} | "
          f"Claude분석: {'ON' if ANTHROPIC_API_KEY else 'OFF'}")
    last_state = None
    while True:
        try:
            date, close = fetch_latest_close()
            fdate, P, F, I = fetch_latest_flow()
            v_tgt = estimate_vtarget(close)
            d_sell, alert = build_alert(fdate or date, close, F, I, v_tgt)

            # 상태 변화 시에만 발송 (스팸 방지). 첫 실행은 항상 발송.
            if d_sell != last_state:
                if ANTHROPIC_API_KEY:
                    ctx = f"날짜 {fdate}, 종가 {close:.0f}, 외국인 {F:+}, 기관 {I:+}, D_sell={'ON' if d_sell else 'OFF'}"
                    ai = claude_analysis(ctx)
                    if ai:
                        alert += "\n\n🤖 Claude 분석:\n" + ai
                send_telegram(alert)
                last_state = d_sell
            else:
                print(f"[{datetime.datetime.now():%H:%M}] 상태 유지 "
                      f"({'ON' if d_sell else 'OFF'}), 종가 {close:.0f}")
        except Exception as e:
            print(f"폴링 오류: {e}")
        time.sleep(POLL_MINUTES * 60)


if __name__ == "__main__":
    main()
