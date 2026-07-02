# 2026-07-01 KOSPI Open Forecast - 06:30 KST

Purpose: research/contest forecast, not investment advice.

## Inputs

Prior KOSPI close: 8,476.48

Overnight US market:

| Signal | Move |
|---|---:|
| S&P 500 | +0.79% |
| Nasdaq | +1.52% |
| SOX | +3.92% |
| EWY | about +2.19% |

Local risk:

| Signal | Reading |
|---|---:|
| Prior foreign flow | -37,992 million KRW |
| Prior institution flow | +29,332 million KRW |
| USD/KRW | high, around 1,550 |
| US 10Y | elevated, around 4.36~4.40 |

## Model Readings

| Model | Open |
|---|---:|
| Codex Gate-RC v2 | 8,494 |
| GLM audit adjustment | +18pt to Codex open |
| GLM-adjusted Codex | 8,512 |
| Claude tactic estimate | 8,479 |
| Market/EWY overlay | 8,520~8,550 |

## Final Call

Final KOSPI open forecast: **8,525**

Range: **8,500 ~ 8,555**

Interpretation:

- US semiconductor strength is too large to ignore; open should be positive.
- EWY strength argues for a larger gap than the raw Gate-RC output.
- High USD/KRW and prior foreign selling cap the opening gap.
- Best point estimate sits above GLM-adjusted Codex but below a full SOX-driven chase.

## Scoring Note

If actual open is:

- below 8,500: macro/foreign drag dominated.
- 8,500~8,555: final hybrid call is correct.
- above 8,555: SOX/EWY momentum dominated and the trim was too conservative.

## Actual Open

Actual KOSPI open: **8,591.50**

| Forecaster | Forecast | Error |
|---|---:|---:|
| Codex final | 8,525 | -66.50pt |
| Claude final | 8,525 | -66.50pt |

Actual opening gap: **+1.357%**

Postmortem:

- Both Claude and Codex correctly called the direction but under-called the gap.
- The trim for USD/KRW and prior foreign selling was too strong.
- SOX/EWY momentum dominated the open.
- Codex range 8,500~8,555 missed high by 36.5pt.
- Claude range 8,475~8,580 missed high by 11.5pt.

Rule update:

- When SOX is above +3.5% and EWY is above +2.0%, the open model must not cap the gap below +1.0% unless there is fresh pre-open FX shock or futures weakness.
