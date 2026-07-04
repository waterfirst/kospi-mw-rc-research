# Claude v8 전략 — Codex 해부 후 7/7 전쟁 계획

> 작성: 2026-07-04 | 정보·연구 목적. 투자자문 아님.

---

## 1. Codex 해부: 우리가 더 나은 것

### 구조적 우위 (유지)

| 항목 | Claude v7 | Codex vFinal | 왜 Claude가 이김 |
|---|---|---|---|
| **EWY 처리** | T_EWY 변압기 (k=0.58) — 독립 결합소자 | V_US 바스켓 내 1/4 입력 | EWY를 '희석'하지 않고 '직독'함 → 시가 3/3일 ≤20pt |
| **패닉 트리거** | 수급 정량 항복 (F≤-30k ∧ NET≤-20k) | 뉴스 게이트 (뉴스 탐지 실패=침묵) | 7/2 Meta 뉴스 놓쳐도 수급으로 발화 가능 |
| **기관 방어** | G_inst 가변 컨덕턴스 (크기 법칙) | C_domestic에 개인+기관 통합 | +29k와 +2k를 다르게 취급 |
| **수식 투명성** | RC/RLC 물리 방정식 명시 | 블랙박스 앙상블 가중치 | 실패 원인 추적·수정 속도 우위 |

### Codex가 더 나은 것 (차용 대상)

| 항목 | Codex | 차용 방법 |
|---|---|---|
| **Intraday ADC** | 09:05/10:30/12:30 피드백 루프를 회로 소자로 명시 | v8 회로에 S/H(표본-유지 소자) 추가 |
| **뉴스 폴러** | contest/news/ 실시간 Google News RSS | 하이퍼스케일러 쿼리 추가 (Meta/AWS/Azure) |
| **워치독** | 예정 (7/3 스케줄러 장애로 설계 중) | 우리도 동일하게 도입 필요 |
| **Telegram 실시간** | 실운용 체계 (7/2부터) | 우리 제출 타임스탬프 강화에 활용 |

---

## 2. 공통 실패 패턴 (양측 모두 0점이었던 날)

### 7/3 패러독스: SOX -5.45%인데 KOSPI +5.76%

**무엇이 일어났나:**
- SOX -5.45% → 모든 모델이 하락 예측
- 실제: 기관 +44,079억, 거래대금 45.5조, 삼성 +8.22%, 하이닉스 +10.88%
- 종가 고가 근처(8,088 vs 고가 8,136) 마감

**실패 원인:**
```
없는 회로 소자: panic_exhaustion_rebound (역방향 다이오드)

조건:
  prior_crash_return <= -5%       ✓ 7/2: -7.89%
  intraday_low_breach (7,378)    ✓
  EWY not collapsing same day    ✓ 7/3 EWY는 -2.8%뿐
  no fresh Korea-specific news   ✓ Meta 뉴스는 7/1~7/2 이슈
  institution_net_buy > +20k    ✓ 09:05 이미 기관 순매수 급증 관측 가능

→ 위 5개 중 3개 이상 충족 시: D_panic *= 0.4, EWY_weight *= 1.5
```

### 기관 흡수 볼록성 (13:00 이후)

```
7/3 실제 종가 흐름:
  09:05 현재가 8,459 → 12:30 예측 7,900~7,808 (0점)
  실제 종가 8,088 (고가 근처 마감)

→ 기관 순매수 가속 + 거래대금 증가 + 등락비율 개선이 13:00 이후 추가 상승 만들었음
→ 12:30 제출 후 최소 14:00 내부 업데이트 필요 (공식 제출은 변경 불가, 내부 정확도 개선용)
```

---

## 3. Claude v8 회로 설계

### 신규 소자

```
기존 v7: T_EWY → D_av → G_inst → RC → KOSPI

v8 추가:
  D_rev (역방향 다이오드) = panic_exhaustion_rebound
  C_absorb (기관 흡수 커패시터) = 장중 기관 순매수 누적
  W_VOL (거래대금 가속 게이트) = 거래대금 가속 시 신호 증폭
  ADC_1400 (14:00 표본기) = 13:00 이후 수급 재표본 (내부용)
```

### v8 수식

**시가 (07:30 제출):**
```python
# Step 1: EWY 직독 (변압기, 핵심)
open_EWY = prev_close * (1 + k_ewy * EWY_pct/100)
k_ewy = 0.58  # 검증값

# Step 2: 역방향 다이오드 체크 (신규)
if (prior_crash <= -5% and EWY > -3.5% and no_fresh_news):
    D_rev = 1  # 패닉 소진 반등 레짐
    k_ewy *= 1.35
    D_panic_weight *= 0.4
else:
    D_rev = 0

# Step 3: 수급 항복 (뉴스 독립 안전장치 유지)
if (foreign <= -30k and NET <= -20k):
    D_av = 1  # 하방 다이오드 ON
    open_pred = open_EWY - shock_penalty
else:
    open_pred = open_EWY

# Step 4: FX 저항
open_pred -= R_fx * (USDKRW - 1400)  # 1400 기준선
```

**종가 (12:30 제출 + 14:00 내부 업데이트):**
```python
# 10:30 이후 장중 흐름 모델
robust_close = current
    - 0.38 * max(open - current, 0)   # 갭 실패 패널티
    + 0.18 * (current - low)           # 저가 회복 크레딧

# G_inst 기관 방어 (크기 법칙)
if institution >= 30000:
    G_inst_factor = 1.5   # 강한 기관 방어
elif institution >= 15000:
    G_inst_factor = 1.1
else:
    G_inst_factor = 0.8   # 기관 방어 부재

# 거래대금 가속 게이트 (신규)
if trading_value_acceleration:
    W_vol = 1.2
else:
    W_vol = 1.0

# 역방향 다이오드 (신규)
if D_rev and institution >= 30000 and advance_decline >= 1.5:
    close_rebound_credit = 0.8 * (high - current)
else:
    close_rebound_credit = 0

robust_close = (robust_close + close_rebound_credit) * G_inst_factor * W_vol
```

---

## 4. 7/7 (월) 전쟁 계획

### 상황 진단 (7/3 마감 기준)

| 항목 | 값 | 해석 |
|---|---:|---|
| KOSPI 종가 | 8,088.34 | 7/2 저점(7,648) 대비 +5.76% 반등 |
| 기관 | +44,079억 | 강한 국내 기관 방어 확인 |
| 외국인 | -21,750억 | 여전히 매도. 완전 전환 아님 |
| 거래대금 | 45.5조 | 패닉 소진 + 쇼트커버링 신호 |
| 삼성전자 | +8.22% | 반등 리더 |
| SK하이닉스 | +10.88% | 급반등 |
| SOX (미국) | -5.45% | 미국은 아직 약세 지속 |
| US 7/4 | 휴장 | 신선한 미국 데이터 없음 |

### 레짐 판단 프레임워크 (7/7 전용)

```
조건 A: D_rev 발동 여부
  - prior_crash (7/2): -7.89% ✓
  - EWY 7/3~7/4 수준: 확인 필요 (US 월요일 프리마켓)
  - 신선한 한국 특이 뉴스: 7/5~7/6 주말 확인

조건 B: AI_CAPEX_DEMAND_SHOCK 지속 여부
  - SOX 계속 -5%대면: 충격 지속
  - SOX 반등하면: 흡수 국면

조건 C: BOK (7/9) 선행 포지셔닝
  - 시장이 BOK 인하 기대 → KRW 강세 → 외국인 매도 완화 가능
  - 반대로 동결 우려 → KRW 약세 유지 → 외국인 매도 지속
```

### 시나리오 별 7/7 예측

| 시나리오 | 조건 | 시가 예측 | 종가 예측 |
|---|---|---|---|
| **A. 안정화** | SOX 보합, EWY+, 외국인 매도 완화 | +0.5~1.5% | 기관 방어 시 +1~2% |
| **B. 되돌림** | SOX 계속 약세, 외국인 매도 지속, 갭 하락 | -1~2% | 기관 있으면 부분 회복 |
| **C. 연속 충격** | 주말 신규 AI 뉴스 충격, EWY -3%↓ | -3~5% | D_panic 발동 |

**D_rev 발동 임계 (v8 신규):**
- EWY > -2.5% + 외국인 매도 완화 → **시나리오 A** 유리
- EWY -2.5% ~ -3.5% → **시나리오 B** (베이스케이스)
- EWY < -3.5% + 신규 쇼크 뉴스 → **시나리오 C**

---

## 5. 운영 계획 (7/7 타임라인)

| 시각 (KST) | 행동 | 담당 소자 |
|---|---|---|
| **월요일 07:00** | EWY 프리마켓 + SOX 주말 선물 + USD/KRW 확인 | T_EWY + R_fx |
| **07:30** | 시가 예측 고정 제출 | v8 open model |
| **09:05** | 시가 채점 + 갭 레짐 분류 + 기관/외국인 초기 수급 | ADC_0905 |
| **10:30** | 종가 1차 예측 (수급 업데이트) | robust_close v8 |
| **12:30** | 종가 제출 고정 | 워치독 확인 필수 |
| **14:00** | 내부 정확도 추적 (제출 변경 없음) | ADC_1400 (신규) |

### 워치독 규칙 (7/3 교훈)

```python
# 제출 후 +3분 이내 파일 없으면 폴백 자동실행
DEADLINES = {
    '0730_open': '07:30',
    '1230_close': '12:30',
}
for label, target in DEADLINES.items():
    if not file_exists(label, target, grace_minutes=3):
        run_fallback_forecast(label)
        send_telegram(f"⚠️ WATCHDOG: {label} 폴백 실행")
```

---

## 6. Codex 대비 전술

### Codex가 틀릴 가능성이 높은 상황

1. **역반등 레짐**: Codex D_panic이 뉴스 게이트 → 뉴스 없으면 과도하게 베어리시 유지 (7/3 재발 가능)
2. **기관 방어 식별**: C_domestic(통합)으로 기관 vs 개인 구분 못 함 → 기관 방어 장세 과소평가
3. **EWY 과소반영**: V_US 바스켓 속 1/4 → EWY 강세 때 시가 낮게 예측

### 우리가 집중해야 할 곳

```
7/7 핵심 엣지:
  EWY를 T_EWY(k=0.58)로 직독 → 시가에서 Codex 이김
  G_inst 크기 법칙 → 기관 방어 장세에서 종가 이김
  D_rev 신규 → 역반등 레짐에서 Codex가 베어리시할 때 강세 포착

7/7 위험:
  주말 신규 AI 뉴스 쇼크 (미확인)
  USD/KRW 급등 (BOK 전 포지셔닝)
  외국인 매도 가속 (아직 방향 전환 없음)
```

---

## 7. 누적 전적 + 다음 목표

| 날짜 | Claude | Codex | 승자 |
|---|:---:|:---:|---|
| 6/30 | **9** | 3 | 🟢 Claude |
| 7/1 | 3 | **7** | 🔴 Codex |
| 7/2 | 0 | 0 | 무승부 |
| 7/3 | n/a | 0 | 무승부 |
| **누적** | **12+** | **10** | 🟢 Claude 리드 |

**7월 목표 (JULY_2026_WAR_ROADMAP 기준):**
- 방향 정확도 ≥ 70%
- 시가 ≤1.0% 오차 60일 이상
- 종가 ≤1.0% 오차 60일 이상
- 타임스탬프 100% (워치독으로 보장)

---

## 8. v8 우선 구현 체크리스트

- [x] `D_rev` 역방향 다이오드 1차 로직 추가: `post_crash_relief_possible`
- [x] `G_inst` 1차 크기 법칙 추가: `institution_absorption`
- [ ] `W_vol` 거래대금 가속 게이트 추가
- [ ] `ADC_1400` 14:00 내부 표본기 (제출 변경 없이 내부 정확도 추적)
- [x] 워치독: 07:30 + 12:30 제출 파일 확인 + 폴백 스크립트 추가
- [x] 뉴스 쿼리 추가: "Meta cloud capacity", "AWS Azure AI compute", "hyperscaler AI demand"
- [x] EWY 데이터 수집 루틴 추가

*정보·연구 목적. 투자자문 아님.*
