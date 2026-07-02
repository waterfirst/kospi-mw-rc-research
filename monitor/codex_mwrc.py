#!/usr/bin/env python3
"""
Codex MW-RC v7 에뮬레이터 (상대 전술 파악용)
=============================================
Codex 모델을 Claude가 역설계해 직접 구현. 관측된 Codex 예측으로 캘리브레이션:
  · 6/30 시가 8,477 (전일 8,394.65 -> +0.98%)  [당시 美 SOX +3.83% 등 강세]
  · 6/30 종가 8,690 (전일 대비 +3.5%)           [강한 모멘텀 증폭]

【파악된 Codex 전술 (핵심)】
  1. US-모멘텀 외삽: 오버나잇 美 등락을 KOSPI에 높은 beta로 투영.
     특히 SOXX(반도체) 가중 높음 -> 美 반도체 강세일수록 강하게 상승 예측.
  2. 종가는 sigma_total 증폭으로 *모멘텀 지속* 가정 -> 강세장 종가를 크게 부름.
  3. 국내 수급(외국인 월말매도) 드래그 미반영 -> 강한 美 날 *과대예측* 경향.
  강점: US가 주동인인 날 방향 정확(6/29 갭다운 적중).
  약점: 외국인 매도가 美강세를 상쇄하는 날 과열(6/30 시가·종가 모두 고예측).

【재현 파라미터 (역설계)】
  시가: open = prev * (1 + BETA_O * US_blend)         BETA_O=0.42 (SOX가중 블렌드)
  종가: close= prev * (1 + BETA_C * US_blend) + 모멘텀  BETA_C=1.0  (증폭)
"""

# Codex US 가중 (SOXX 비중 큼 — 반도체 중심 투영)
W = {"SOX": 0.45, "NASDAQ": 0.25, "S&P": 0.15, "EWY": 0.10, "DOW": 0.05}
BETA_OPEN = 0.42      # 시가 외삽 계수
BETA_CLOSE = 1.00     # 종가 증폭 계수 (모멘텀 지속 가정)


def us_blend(us):
    return sum(W.get(k, 0) * us.get(k, 0) for k in W) / 100.0


def codex_open(prev_close, us):
    b = us_blend(us)
    return prev_close * (1 + BETA_OPEN * b), b * 100


def codex_close(prev_close, us, intraday_momentum=0.0):
    """intraday_momentum: 장중 추가 모멘텀(%) 가정(강세장 지속). 기본 0."""
    b = us_blend(us)
    return prev_close * (1 + BETA_CLOSE * b + intraday_momentum / 100.0), b * 100


if __name__ == "__main__":
    # 검증: 6/30 재현 (월요일 美 종가)
    us_0630 = {"SOX": 3.83, "NASDAQ": 2.07, "S&P": 1.18, "EWY": 0.11, "DOW": 0.59}
    o, b = codex_open(8394.65, us_0630)
    c, _ = codex_close(8394.65, us_0630)
    print(f"[6/30 재현] US블렌드 {b:+.2f}%")
    print(f"  Codex 시가 에뮬 {o:,.0f} (실제 Codex콜 8,477 / 실제값 8,416.70)")
    print(f"  Codex 종가 에뮬 {c:,.0f} (실제 Codex콜 8,690 / 실제값 8,476.48)")
