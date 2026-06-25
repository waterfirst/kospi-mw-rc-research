# Maxwell-Wagner RC Parallel-Conductance Model v7: Explaining the Fast KOSPI 9,000 Rebound and Forecasting 26 June 2026

Date: 25 June 2026  
Author: Codex  
Scope: KOSPI rebound after the 9,000 round-number break, S&P 500 night-session feedback, and ETF execution logic

## Abstract

This working paper records the model revision made after the KOSPI recovered from 8,203.84 to 8,930.30 within two trading days after the 23 June 2026 crash. The previous Maxwell-Wagner market model treated foreign net buying as the main recovery gate. That assumption failed in real time. On 24 June, KOSPI rebounded by 3.26% while foreign investors still sold about KRW 4.65 trillion. On 25 June, the index reached an intraday high of 9,044.04 and closed at 8,930.30 before foreign conductance had been confirmed. The v7 model therefore replaces the foreign-gate assumption with a parallel-conductance RC model. Foreign flow remains important, but it is no longer an entry condition. It becomes a durability signal after the 9,000 level is recovered. The realized entry time constant is estimated at 0.8-1.5 trading days for the 9,000 recovery and 1.77 trading days for the prior-high recovery. The central forecast for KOSPI on 26 June 2026 is 9,030, with a 62% probability of a 9,000 close. The central S&P 500 forecast is 7,375, reflecting a larger structural capacitance and weaker mega-cap feedback.

## 1. The Failure That Forced the Revision

The important error was waiting for foreign net buying. The old model behaved like a series circuit.

```text
shock -> R_foreign -> C_KOSPI -> price recovery
```

In a series circuit, if the foreign-resistance channel stays open, recovery must be slow. The market did not behave that way. Foreign flow stayed negative, but price recovered quickly. The correct structure is a parallel circuit.

```text
                         +-- R_domestic --+
shock well P0 -----------+-- R_ETF -------+--> V_KR recovery
                         +-- R_round -----+
                         +-- R_program ---+
                         +-- R_foreign ---+
```

In a parallel circuit, conductances add. The v7 model is therefore:

```text
C_eff(t) * dV_KR/dt = sigma_total(t) * [V_target(t) - V_KR(t)] - I_forced_sell(t)

tau_entry = C_eff / sigma_total

sigma_total = sigma_foreign + sigma_institution + sigma_individual
            + sigma_ETF + sigma_round + sigma_program
```

Foreign conductance is not removed. It is demoted. It is no longer the entry gate. It is the signal that decides whether a position can be held after the market closes above 9,000.

## 2. RC Calibration

### KOSPI Capacitance

FinanceDataReader reported the following KOSPI values for 25 June 2026.

```text
KOSPI close = 8,930.30
KOSPI market capitalization = KRW 7,310.4 trillion
```

The structural capacitance is defined as market capitalization per index point.

```text
C_KOSPI_struct = KRW 7,310.4T / 8,930.30
               = KRW 0.8186T per point
               = about KRW 818.6B per point
```

The short-run flow capacitance was much thinner. On 24 June, individual and institutional investors absorbed about KRW 4.5407 trillion, while KOSPI rose by 267.18 points.

```text
C_KOSPI_flow = KRW 4.5407T / 267.18 points
             = KRW 0.01699T per point
             = about KRW 17.0B per point
```

The market therefore had a large structural capacitor, but the actual fast-rebound layer was much thinner. That thin layer was the layer that mattered for the 1-2 day trade.

### Realized Time Constants

The crash trough was 8,203.84. The 25 June close of 8,930.30 recovered about 91.2% of the move toward 9,000.

```text
tau_9000 = 0.8-1.5 trading days
tau_prior_high = 1.77 trading days
tau_overshoot = 2.2-2.6 trading days
```

This is much faster than the previous Codex effective tau of 6.08 days and much faster than the slow-recovery 20-day regime. If the baseline recovery time constant is taken as 20.5 days, the effective total conductance rose by about 11.6 times.

```text
sigma_total / sigma_base ≈ 20.5 / 1.77 ≈ 11.6
```

The fast rebound was not caused by a small market capacitance alone. It was caused by two forces acting together: total conductance increased through parallel channels, and effective capacitance fell as the retail absorption capacitor began to discharge.

## 3. S&P 500 Versus KOSPI

The S&P 500 is a float-adjusted market-cap weighted index and covers roughly 80% of available U.S. large-cap market capitalization. Scaling the year-end 2025 aggregate market capitalization of about USD 61.1 trillion to the current index level gives a current estimate of about USD 64.8 trillion.

```text
S&P 500 level ≈ 7,348-7,350
Estimated S&P 500 market capitalization ≈ USD 64.8T

C_S&P_struct = USD 64.8T / 7,348.75
             = USD 0.00881T per point
             = about USD 8.81B per point
```

Using USD/KRW 1,380, the KOSPI structural capacitance is about USD 0.593B per point. The S&P structural capacitance is therefore roughly 14.9 times larger.

```text
C_KOSPI_struct ≈ USD 0.593B per point
C_S&P_struct   ≈ USD 8.81B per point
C_S&P / C_KOSPI ≈ 14.9
```

This explains why the S&P 500 is unlikely to mirror KOSPI's two-day rebound speed. The S&P 500 is a much larger capacitor. It can absorb more shock, but it also takes more conductance to move quickly. The 25 June U.S. session showed the same structure: EWY, SOXX and Micron were strong, but Nvidia remained weak and kept the broad index from fully recovering.

## 4. Forecast for 26 June 2026

### S&P 500

The U.S. session was still in its early phase at the time of this forecast. Semiconductor signals were mixed: memory and Korea-linked ETF feedback were strong, but Nvidia remained a drag on the broad index.

```text
Bearish S&P 500 path: 7,300-7,340
Base S&P 500 path:    7,360-7,395
Bullish S&P 500 path: 7,400-7,430
Central estimate:     7,375
```

The key signals are whether Nvidia falls below -3%, whether QQQ stays near flat or positive, and whether SOXX/SMH hold their gains.

### KOSPI

KOSPI has already recovered 91% of the move from the trough to 9,000. EWY strength and semiconductor ETF stabilization can feed back into the Korean session. The missing confirmation is a 9,000 close.

```text
Bearish retest: 8,820-8,930
Base Fast-V:    8,980-9,070
Bullish hold:   9,070-9,160
Central estimate: 9,030
```

The probability map is:

```text
Probability of a 9,000 close: about 62%
Probability of closing above the prior high at 9,114.55: about 25%
Probability of breaking below 8,800: about 18%
```

For execution, foreign net buying is not the key entry signal. The faster signals are 8,900 defense, 9,000 close, EWY strength, and SOXX/SMH holding their gains.

## 5. Work Log for 25 June 2026

The following work was completed today.

```text
1. Checked the actual KOSPI path for 24 and 25 June using FinanceDataReader.
2. Admitted the failure of the foreign-gate model and removed foreign net buying from the entry condition.
3. Wrote the v6 Fast-V parallel-conductance model.
4. Verified Claude's tau=1.77 day estimate as the prior-high recovery fit.
5. Fixed the v7 RC parallel-conductance equation.
6. Calculated KOSPI and S&P 500 structural capacitance, KOSPI flow capacitance, and implied resistance.
7. Updated the Telegram monitoring script to use v7 language and six-hour forecast logic.
8. Registered Windows scheduled tasks for pre-market, intraday, close, and U.S. session Telegram alerts.
9. Produced the 26 June 2026 forecast for S&P 500 and KOSPI.
```

The practical lesson is simple. A model that waits too long loses. Waiting for foreign net buying was not prudence; it was the wrong circuit diagram. The operating model must update `sigma_total` and `C_eff` every few hours and accept that price voltage can recover before foreign durability signals arrive.

## 6. Conclusion

The KOSPI rebound after the 9,000 break was not a foreign-flow recovery. It was a parallel-conductance recovery. Domestic institutions, retail flow, ETFs/ADRs, program trading and round-number reversion created low-resistance paths. Retail absorption also began to discharge, reducing effective capacitance. Together, these forces compressed the time constant into the 1-2 trading day range.

For 26 June 2026, the base case is a KOSPI attempt to close above 9,000. The S&P 500 should recover more slowly because of its much larger capacitance and the drag from Nvidia. The key levels are KOSPI 9,000, S&P 7,375, EWY strength, and SOXX/SMH trend preservation.

This document is a research record, not financial advice. The final investment decision belongs to the user.
