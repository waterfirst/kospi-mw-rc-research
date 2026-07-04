# Volatile SOX Prediction Note - 2026-07-04

Source: user-provided chart showing June 2026 SOX daily swings between de-risking and dip-buying.

## Core Problem

SOX is not a clean DC signal. In the current regime it behaves like a noisy AC source:

```text
large positive bars = dip-buying impulse
large negative bars = de-risking impulse
near-zero bars = unresolved regime
```

Using raw SOX one-day return as a direct KOSPI voltage source will overfit and whipsaw.

## Prediction Principle

Do not predict KOSPI from raw US chip-stock movement.

Predict through layers:

1. classify the US semiconductor regime,
2. filter the signal through EWY/Korea-specific price discovery,
3. check FX/rates resistance,
4. check news shock polarity,
5. wait for Korean intraday flow to update close forecast.

## Circuit Interpretation

SOX should enter the circuit as:

```text
V_SOX_AC -> rectifier -> low-pass filter -> gate -> KOSPI coupling
```

Meaning:

- `rectifier`: separate risk-on and risk-off impulses.
- `low-pass filter`: use 3-day/5-day state, not one bar.
- `gate`: news/FOMC/CPI/earnings can change the transmission.
- `KOSPI coupling`: EWY, USD/KRW, foreign flow decide how much is transmitted.

## Regime Classifier

| SOX Pattern | Regime | KOSPI Open Rule |
|---|---|---|
| big down after prior big down, EWY not collapsing | panic exhaustion possible | do not over-short open |
| big down with EWY down, MU/NVDA down, fresh negative news | shock continuation | keep D_panic active |
| big up after crash with EWY up | relief rebound | raise EWY weight |
| alternating +/- large bars | high-vol chop | widen range, reduce point confidence |
| SOX up but USD/KRW/DXY/rates hostile | blocked transmission | trim US beta |

## Close Forecast Rule

US data is less important after the Korean open.

After 09:05, close prediction should be dominated by:

- foreign flow,
- institution flow magnitude and acceleration,
- program trading,
- trading value acceleration,
- breadth,
- Samsung/Hynix behavior,
- whether current price stays above open.

## Practical Forecast Output

In volatile SOX regime, output must include:

```text
point forecast
wide range
regime probability
invalidating conditions
```

Example:

```text
Open 7,900, range 7,760-8,060
Regime: high-vol relief rebound 55%, shock continuation 30%, range 15%
Invalidation: EWY < -3.5% plus fresh HBM/capex negative news
```

## Lesson For July Contest

The model should stop treating SOX as a direct answer key. SOX is a high-volatility driver. EWY is closer to Korea price discovery, but EWY can miss sector-specific memory shocks.

Best stack:

```text
SOX/MU/NVDA/META = semiconductor voltage
EWY = Korea transformer
USD/KRW/DXY/US10Y = resistance
news = regime gate
foreign/program/institution = intraday current
```

This is why the final model must remain Global Gate-RC rather than EWY-only or SOX-only.
