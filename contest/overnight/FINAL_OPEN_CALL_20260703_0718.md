# Final Open Call - 2026-07-03

Timestamp: 2026-07-03 07:18 KST

Research only. Not investment advice.

## Codex Final Call

| Item | Value |
|---|---:|
| Previous KOSPI close | 7,648.09 |
| Open forecast | 7,505 |
| Range | 7,450 - 7,570 |
| Implied open return | -1.87% |
| Regime | domestic_damage_continuation |

## Inputs

| Signal | Value |
|---|---:|
| S&P | +0.00% |
| Nasdaq | -0.80% |
| SOX | -5.45% |
| EWY | about -2.8% |
| MU | about -5.4% |
| NVDA | about -1.5% |
| META | about -4.9% |
| Prior foreign flow | -43,706 |
| Prior institution flow | -20,825 |
| Prior program flow | -22,447 |
| Defense strength | -65,125 |

## Rationale

Final value is lower than the EWY-only transformer result because semiconductor-specific voltage is still damaged: SOXX and MU remain deeply negative, prior KOSPI damage was extreme, and foreign/institution/program flows all stayed hostile.

The model keeps `D_panic` partially active, but does not force a second limit-style crash at open because EWY did not collapse as much as SOXX/MU and the prior day already priced a large part of the shock.

## Claude v7 Check

Claude v7 EWY transformer with `k = 0.58` and EWY around -2.8% implies roughly 7,520. Codex final is slightly lower at 7,505 because it separates EWY from memory/SOX damage.
