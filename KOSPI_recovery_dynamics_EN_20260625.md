# Recovery-Time Dynamics of the June 2026 KOSPI 9,000-Level Crash
## A Driven-RC (Maxwell–Wagner) Model with Parallel-Conductance Actor Decomposition

**Author:** Nakcho Choi · with Claude (analysis) · **Date:** 2026-06-25 · Working paper / research log
*Information and research purposes only. Not investment advice.*

---

### Abstract
We model the recovery after the 23 June 2026 KOSPI circuit-breaker crash (−9.99%) as a *driven RC relaxation* of the Maxwell–Wagner market-impedance framework. The index fell from a prior high of 9,114.55 to a trough of 8,203.84, then recovered ~80% of the drawdown in two trading sessions (8,471.02 on D+1, 8,930.30 on D+2). We show that the original model's reliance on a *foreign net-buy reversal* as the recovery gate is empirically false, and replace it with a parallel-conductance actor decomposition in which institutions, not foreigners, supplied the low-resistance discharge path. Calibrating capacitance from market value per index point and resistance from realized price impact, we find the fast recovery was driven by a collapse in the active-layer resistance R_fast — not by any growth in capacitance C. The realized relaxation time compressed from a ~20-day structural scale to a ~1.8-day active scale.

---

### 1. Event
| Date | Close | Daily | Foreign (T₩) | Institution | Individual |
|---|---|---|---|---|---|
| 6/22 | 9,114.55 | +0.69% | — | — | — |
| 6/23 (D+0) | 8,203.84 | **−9.99%** | −4.20 | −4.48 | +8.59 |
| 6/24 (D+1) | 8,471.02 | +3.26% | −4.65 | +1.91 | +2.63 |
| 6/25 (D+2) | 8,930.30 | +5.42% | −0.88 | +3.32 | −2.41 |

The crash was triggered by a global AI/semiconductor valuation shock (Micron −13.2%, SOX −7.6%) that propagated **bidirectionally** between Korea (SK Hynix, Samsung HBM) and the US, breaking the original model's assumption of one-way S&P→KOSPI transmission.

### 2. Failure of the foreign-gate model
The v1 model treated *foreign net-buy reversal* as a near-necessary condition for recovery (predictions P2 / H1). This is falsified by the data. Across 12 two-year round-number drawdown events:
- Foreign net-buy flip occurs at a **median of 4 trading days** after the trough (up to 18), and its timing correlates **−0.17** with recovery duration — uninformative to mildly perverse.
- Institutional net-buy flip occurs at a **median of 1 day**.
- Counterexample (2026-05-15): full recovery in 6 days while foreigners did not turn net buyers until day 18.

In the present episode foreigners net-sold on all three sessions, yet the index V-recovered. **Waiting for foreigners is a series-circuit fallacy.**

### 3. Revised model (v3): driven RC relaxation
Governing equation:
```
C_eff(t)·dV/dt = σ_total(t)·[V_target − V(t)] − I_forced_sell(t)
```
Homogeneous solution: `V(t) = V_target − (V_target − V₀)·exp(−t/τ)`, with `τ = C_eff / σ_total`.

**Conductance is a parallel sum** (key correction):
```
σ_total = σ_F + σ_I + σ_P + σ_ETF + σ_round + σ_program
```
When the foreign channel σ_F is off (high resistance), institutional (σ_I), ETF, round-number unwind (σ_round) and program channels keep σ_total high. Foreign net-buy is demoted from an entry gate to an **H2 signal** — whether the index can *hold* above 9,000.

**Effective capacitance discharges:**
```
C_eff = C_cap − C_retail_discharge − C_forced_unwind
```
Retail charged the capacitor on 6/23 (+8.59T absorption); the subsequent retail flip to net selling is a *discharge* that lowers ε_eff. τ = ε_eff/σ_total fell from both numerator and denominator.

### 4. RC calibration (numbers)
- **Structural capacitance:** C_struct = market value / index = 7,310.4T₩ / 8,930.30 = **0.819 T₩/pt** (≈ $0.593B/pt).
- **Active (flow) capacitance:** from 6/24, C_flow = (institution+individual net) / index gain = 4.5407T / 267.18 pt = **0.017 T₩/pt** (≈170억/pt). Only ~2.1% of structural cap actually transacted to move price.
- **Two-branch RC ladder** (each layer has its own R, C, τ):
  - Fast/active: C_fast = 0.017, τ_fast ≈ 1.25 d ⇒ R_fast ≈ 73.6 (thin → high R, tiny C).
  - Slow/structural: C_struct = 0.819, τ_slow ≈ 20.5 d ⇒ R_slow ≈ 25.0 (deep → low R, huge C).
- **Drivers of the R_fast collapse** (data): crisis→normal price impact λ fell ×1.8 (1.15→0.64 %/T); P4 down/up asymmetry λ_down/λ_up ≈ 1.47 (recovery is structurally lower-R than the crash); institutional parallel path switched on (+1.91→+3.32T).

### 5. Why the recovery was fast
The realized τ ≈ **1.77 days** (single-exponential fit to D+1, D+2 against the prior-high target; R²=0.90) is ~11.6× faster than KOSPI's ~20.5-day structural baseline and ~3× faster than the S&P. Decomposition: **capacitance did not grow** (KOSPI C remains ~1/15 of the S&P); rather **R_fast collapsed** while the retail capacitor discharged. In circuit terms, institutions opened a low-resistance parallel branch that bypassed the open foreign channel.

τ depends on the recovery target:
| Target | τ |
|---|---|
| 9,000 short retake | 0.8–1.5 d |
| prior high 9,114.55 (headline) | **1.77 d** |
| overshoot 9,253–9,385 | 2.2–2.6 d |

### 6. Cross-market comparison (S&P 500)
Using C_struct = market value / index and a 1,380 ₩/$ rate:
| Market | C_struct | τ | note |
|---|---|---|---|
| KOSPI | $0.593B/pt | 20.5 d (struct) / 1.77 d (active) | thin, R-driven |
| S&P 500 | $8.81B/pt | 5.5 d | deep, C-driven |

The S&P capacitance is ~14.9× larger — a slow, massive capacitor. KOSPI moves fast not because it is large but because its active-layer resistance can swing violently.

### 7. Real-time forecasts (registered for scoring)
Closed-loop leading indicator: overnight US semis (SOX/Micron) set next-day KOSPI foreign/program flow.
- **KOSPI 6/26 (D+3):** base 8,950 ± 60 (tests the 9,000 round-number barrier); bull (overnight SOX up) 9,030–9,100 breakout; bear (SOX down) 8,750–8,880 rejection.
- **S&P 6/26 (tonight's US session):** base ~7,400 (+0.7%, fear easing); bull 7,459; bear 7,261 (AI-derating persists).

### 8. Limitations
Small event sample (n≈12); scenario/simulation dataset possible; S&P capacitance relies on disclosed market-cap and the 3.7× τ ratio (no local S&P flow data); single-actor price-impact regressions are endogenous and used only for order-of-magnitude calibration; τ↔recovery partial circularity. Not investment advice.
