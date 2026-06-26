#!/usr/bin/env python3
"""
월요일 아침 8시 KOSPI 예측보고서 생성기
=========================================
2026-06-26 | Claude 다이오드 모델 v5

【목적】
  금요일 밤(KST) 미국시장 종가가 확정되면(토 05:00 KST 이후) 실행.
  미국 종가 → V_target 환산 → 다이오드 모델로 월요일 KOSPI 시나리오 예측.
  → docs/monday_forecast.html (또는 지정 경로)로 보고서 HTML 생성.

【정직한 구조】
  · 익일 점예측은 불가능(백테스트 H3, 평균회귀). 그래서 "점 하나"가 아니라
    V_target 기반 베이스라인 + 수급 조건부 시나리오를 함께 제시한다.
  · V_target는 미국지표(SOX·S&P·나스닥)를 KOSPI 균형가로 환산한 휴리스틱.
    KOSPI 반도체 비중↑ 반영해 SOX 가중. v6에서 정밀 회귀로 교체.

【사용】
  pip install requests
  python monday_forecast.py            # docs/monday_forecast.html 생성
  python monday_forecast.py out.html   # 경로 지정

【권장 실행 시점】
  토요일 새벽(미국 금요일 종가 확정 후) 또는 월요일 아침 7~8시.
"""

import sys, json, datetime, re
import requests

HEAD = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}

# ── 실측 모델 파라미터 (604일 백테스트) ──
C_FLOW, K_CASCADE, TAU = 0.017, 1.784, 2.319
BT_ON  = {"mean": -1.19, "down": 80.1, "n": 151}
BT_OFF = {"mean": +0.68, "down": 29.4, "n": 453}

# ── 미국지표 → KOSPI 균형가 환산 가중 (휴리스틱; KOSPI 반도체 비중 반영) ──
W_SOX, W_SP, W_NQ = 0.45, 0.40, 0.15


# ── 데이터 수집 ──────────────────────────────────────────────
def _f(x):
    return float(str(x).replace(",", "")) if x not in (None, "") else 0.0


def fetch_us_index(symbol):
    """Naver 세계지수: 종가 + 등락률(%).
    basic 엔드포인트가 PREOPEN/0이면 price 히스토리의 최근 완결 세션으로 폴백."""
    b = requests.get(f"https://api.stock.naver.com/index/{symbol}/basic",
                     headers=HEAD, timeout=15).json()
    close = _f(b.get("closePrice"))
    chg = _f(b.get("fluctuationsRatio"))
    status = b.get("marketStatus", "")
    # 개장 전/0 등락이면 최근 완결 세션(price 히스토리 첫 행)으로 보강
    if status in ("PREOPEN", "") or abs(chg) < 1e-9:
        try:
            rows = requests.get(
                f"https://api.stock.naver.com/index/{symbol}/price?pageSize=2&page=1",
                headers=HEAD, timeout=15).json()
            if rows:
                close = _f(rows[0].get("closePrice")) or close
                chg = _f(rows[0].get("fluctuationsRatio"))
        except Exception:
            pass
    return {"close": close, "chg_pct": chg, "status": status,
            "at": b.get("localTradedAt", "")}


def fetch_us_market():
    syms = {".SOX": "필라델피아반도체", ".INX": "S&P500",
            ".IXIC": "나스닥", ".DJI": "다우"}
    out = {}
    for s, name in syms.items():
        try:
            d = fetch_us_index(s)
            d["name"] = name
            out[s] = d
        except Exception as e:
            out[s] = {"name": name, "close": 0, "chg_pct": 0,
                      "status": "ERR", "at": str(e)}
    return out


def fetch_kospi_latest():
    """최근 KOSPI 종가 (날짜, 종가)."""
    url = ("https://api.finance.naver.com/siseJson.naver?symbol=KOSPI"
           "&requestType=1&startTime=20260601&endTime=20260801&timeframe=day")
    r = requests.get(url, headers=HEAD, timeout=20)
    rows = json.loads(r.text.strip().replace("'", '"'))
    last = rows[-1]
    return last[0], float(last[4])


def fetch_kospi_flow():
    """최근 영업일 개인·외국인·기관 순매매(백만원)."""
    today = datetime.datetime.now().strftime("%Y%m%d")
    url = (f"https://finance.naver.com/sise/investorDealTrendDay.naver"
           f"?bizdate={today}&sosok=01&page=1")
    r = requests.get(url, headers=HEAD, timeout=20); r.encoding = "euc-kr"
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", r.text, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        c = [re.sub(r"<[^>]+>", "", x).replace("&nbsp;", "").replace(",", "").strip()
             for x in cells]
        if c and re.match(r"\d{2}\.\d{2}\.\d{2}$", c[0]):
            d = "20" + c[0].replace(".", "")
            return d, int(c[1]), int(c[2]), int(c[3])  # 개인, 외국인, 기관
    return None, 0, 0, 0


# ── 다이오드 모델 ─────────────────────────────────────────────
def estimate_vtarget(v_prev, us):
    """미국 종가 등락률 → KOSPI 균형가."""
    sox = us.get(".SOX", {}).get("chg_pct", 0) / 100
    sp  = us.get(".INX", {}).get("chg_pct", 0) / 100
    nq  = us.get(".IXIC", {}).get("chg_pct", 0) / 100
    blend = W_SOX * sox + W_SP * sp + W_NQ * nq
    return v_prev * (1 + blend), blend


def diode_predict(v_prev, v_tgt, F, I):
    """F, I: 순매수(조원, 양수=매수)."""
    d_sell = (F < 0 and I < 0)
    net = abs(F + I) if d_sell else 0
    shock = K_CASCADE * net / C_FLOW
    restore = (v_tgt - v_prev) / TAU
    return d_sell, v_prev + restore - shock, shock, restore


# ── 보고서 생성 ───────────────────────────────────────────────
def build_report(us, kdate, kclose, fdate, F_mw, I_mw, P_mw):
    """F_mw, I_mw: 직전 영업일 순매매(백만원). 시나리오는 조원 단위로 가정."""
    v_prev = kclose
    v_tgt, blend = estimate_vtarget(v_prev, us)
    # 베이스라인: D_sell OFF (기관이 받친다고 가정) → 순수 RLC 복원
    _, base_pred, _, base_restore = diode_predict(v_prev, v_tgt, +1, +1)

    now = datetime.datetime.now()
    gen_time = now.strftime("%Y-%m-%d %H:%M KST")

    # 시나리오 (조원 단위 가정)
    scenarios = [
        ("🟢 회복", "기관 매수 지속", -1.0, +2.0, "off"),
        ("🟡 중립", "기관 관망·소폭", -1.5, +0.3, "off"),
        ("🔴 비관", "월말 동반매도", -3.0, -1.5, "on"),
        ("⚫ 공황", "레버리지 청산", -5.0, -3.0, "on"),
    ]
    srows = ""
    for emoji, desc, f, i, cls in scenarios:
        _, pred, shock, restore = diode_predict(v_prev, v_tgt, f, i)
        chg = pred - v_prev
        srows += (f'<tr><td>{emoji} {desc}</td><td>{f:+.1f}</td><td>{i:+.1f}</td>'
                  f'<td class="{"on" if cls=="on" else "off"}">{"ON" if cls=="on" else "OFF"}</td>'
                  f'<td><b>{pred:,.0f}</b></td>'
                  f'<td class="{"down" if chg<0 else "up"}">{chg:+.0f}pt</td></tr>')

    # 미국시장 표
    urows = ""
    for s in [".SOX", ".INX", ".IXIC", ".DJI"]:
        u = us.get(s, {})
        chg = u.get("chg_pct", 0)
        cls = "up" if chg >= 0 else "down"
        urows += (f'<tr><td>{u.get("name","")}</td>'
                  f'<td>{u.get("close",0):,.2f}</td>'
                  f'<td class="{cls}">{chg:+.2f}%</td>'
                  f'<td style="color:#8b949e">{u.get("status","")}</td></tr>')

    status_any = us.get(".INX", {}).get("status", "")
    warn = ("" if status_any in ("CLOSE", "AFTERMARKET") else
            f'<div class="warn">⚠️ 미국시장 상태={status_any}. '
            f'종가 미확정일 수 있음 — 토요일 새벽(미 금요일 종가 확정 후) 재실행 권장.</div>')

    blend_pct = blend * 100
    direction = "상승" if blend >= 0 else "하락"

    html = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>월요일 KOSPI 예측보고서 — 다이오드 모델 v5</title>
<style>
:root{{--bg:#0e1117;--card:#161b22;--bd:#30363d;--fg:#e6edf3;--mut:#8b949e;
--on:#f85149;--off:#3fb950;--accent:#58a6ff;--warn:#d29922;}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--fg);font-family:'Segoe UI','NanumGothic',sans-serif;
line-height:1.6;padding:20px;max-width:880px;margin:0 auto}}
h1{{font-size:1.5rem;margin-bottom:4px}}
.sub{{color:var(--mut);font-size:.85rem;margin-bottom:16px}}
.card{{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:18px;margin-bottom:16px}}
.card h2{{font-size:1.05rem;color:var(--accent);margin-bottom:12px;border-left:4px solid var(--accent);padding-left:9px}}
table{{width:100%;border-collapse:collapse;font-size:.85rem;margin:8px 0}}
th,td{{padding:6px 8px;text-align:right;border-bottom:1px solid var(--bd)}}
th:first-child,td:first-child{{text-align:left}}
th{{color:var(--mut);background:#0d1117}}
.up{{color:var(--off);font-weight:600}}.down{{color:var(--on);font-weight:600}}
.on{{color:var(--on);font-weight:700}}.off{{color:var(--off);font-weight:700}}
.big{{font-size:2rem;font-weight:800;text-align:center;margin:10px 0}}
.note{{font-size:.8rem;color:var(--mut);line-height:1.55;margin-top:8px}}
.warn{{background:rgba(210,153,34,.12);border:1px solid var(--warn);color:var(--warn);
border-radius:6px;padding:10px;font-size:.85rem;margin:10px 0}}
.foot{{color:var(--mut);font-size:.72rem;text-align:center;margin-top:20px;line-height:1.6}}
.kv{{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--bd);font-size:.88rem}}
.kv b{{color:var(--accent)}}
</style></head><body>

<h1>📅 월요일 KOSPI 예측보고서</h1>
<div class="sub">다이오드 모델 v5 · 생성 {gen_time} · 정보·연구용, 투자자문 아님</div>
{warn}

<div class="card">
<h2>1. 미국시장 (전일 종가 → KOSPI 신호)</h2>
<table>
<tr><th>지수</th><th>종가</th><th>등락률</th><th>상태</th></tr>
{urows}
</table>
<div class="note">KOSPI 반도체 비중 반영 가중 환산: SOX×{W_SOX} + S&amp;P×{W_SP} + 나스닥×{W_NQ}
= <b style="color:{'#3fb950' if blend>=0 else '#f85149'}">{blend_pct:+.2f}%</b> ({direction} 신호)</div>
</div>

<div class="card">
<h2>2. 균형가 &amp; 베이스라인 (D_sell OFF 가정)</h2>
<div class="kv"><span>직전 KOSPI 종가 ({kdate})</span><b>{kclose:,.2f}</b></div>
<div class="kv"><span>V_target (미국신호 균형가)</span><b>{v_tgt:,.0f}</b></div>
<div class="kv"><span>복원력 (V_target−V_prev)/τ</span><b>{base_restore:+.0f}pt</b></div>
<div class="big {'up' if base_pred>=v_prev else 'down'}">{base_pred:,.0f}</div>
<div class="note" style="text-align:center">베이스라인 = 기관이 받치는 경우(다이오드 차단)의 순수 RLC 복원 경로.
실제 경로는 아래 수급 시나리오에 따라 갈린다.</div>
</div>

<div class="card">
<h2>3. 수급 조건부 시나리오 (월요일 외국인·기관 순매수 가정)</h2>
<table>
<tr><th>시나리오</th><th>외국인(조)</th><th>기관(조)</th><th>다이오드</th><th>예측종가</th><th>변화</th></tr>
{srows}
</table>
<div class="note">충격 = K_cascade×|F+I|/C_flow (실측 K=1.784, C_flow=0.017).
<b>기관(I) 부호가 스위치</b> — 외국인이 팔아도 기관이 사면 OFF(회복).</div>
</div>

<div class="card">
<h2>4. 직전 영업일 수급 ({fdate}) &amp; 백테스트 기대</h2>
<div class="kv"><span>외국인 순매수</span><b class="{'up' if F_mw>=0 else 'down'}">{F_mw:+,}백만</b></div>
<div class="kv"><span>기관 순매수</span><b class="{'up' if I_mw>=0 else 'down'}">{I_mw:+,}백만</b></div>
<div class="kv"><span>개인 순매수</span><b>{P_mw:+,}백만</b></div>
<div class="note">D_sell ON 통계(604일): 평균 −1.19%/일, 하락확률 80.1%, t=9.55.
OFF 통계: 평균 +0.68%/일, 하락확률 29.4%.</div>
</div>

<div class="card">
<h2>5. 핵심 체크포인트 (월요일 장중)</h2>
<div class="note" style="font-size:.86rem;color:var(--fg)">
① <b>개장 직후 외국인·기관 동시 부호</b> — 둘 다 (−)면 D_sell 점화 → 폭락 경계.<br>
② <b>월말(6/30) 리밸런싱</b> — 외국인 월말 매도 패턴 점검.<br>
③ <b>미국 신호 방향</b> — 위 환산이 {direction} → V_target {('상회' if blend>=0 else '하회')} 압력.<br>
④ <b>기관 전환 시 회복</b> — 기관 매수 전환(I&gt;0)이 최우선 회복 트리거.
</div>
</div>

<div class="foot">
다이오드 모델 v5 · Claude × 첨물 · 데이터: 네이버 금융(미국 세계지수·KOSPI·투자자별 순매매)<br>
※ 익일 점예측은 구조적으로 제한(평균회귀). 본 보고서는 V_target 베이스라인 + 수급 시나리오 제시용.<br>
정보·연구 목적. 투자판단·책임은 본인. 거래비용·세금 미반영.
</div>
</body></html>"""
    return html, v_tgt, base_pred, blend


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "docs/monday_forecast.html"
    print("미국시장 수집...")
    us = fetch_us_market()
    for s, u in us.items():
        print(f"  {u['name']:16s} {u['close']:>12,.2f}  {u['chg_pct']:+.2f}%  [{u['status']}]")
    print("KOSPI 수집...")
    kdate, kclose = fetch_kospi_latest()
    fdate, P, F, I = fetch_kospi_flow()
    print(f"  KOSPI {kdate}: {kclose:,.2f} | 수급 {fdate} 외국인 {F:+,} 기관 {I:+,}")

    html, v_tgt, base, blend = build_report(us, kdate, kclose, fdate, F, I, P)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n✅ 보고서 생성: {out_path}")
    print(f"   V_target={v_tgt:,.0f} | 베이스라인={base:,.0f} | 미국신호={blend*100:+.2f}%")


if __name__ == "__main__":
    main()
