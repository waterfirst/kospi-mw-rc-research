# ChatGPT Close Forecast Note - 2026-07-03

Source: user-provided ChatGPT comparison text.

## Forecast

| Item | Value |
|---|---:|
| Forecast time | about 13:00 KST |
| Forecast close | 7,895 +/- 20 |
| Actual close | 8,088.34 |
| Error | 193.34 pt |
| Error rate | 2.39% |
| Tier score | 0/5 |

## Stated Failure Reason

ChatGPT attributed the miss to underestimating:

- institution net-buy persistence,
- foreign and retail sell absorption,
- trading-value acceleration,
- broad market breadth improvement.

Actual observed close context from the user text:

- institution: about +44,451,
- foreign: about -22,123,
- retail: about -22,942,
- trading value: about 45.2T KRW,
- advancers/decliners: 589 / 297,
- close near the daily high.

## Relevance To Event-RC

This supports the same repair path identified for Codex:

1. Institution flow must be modeled as magnitude + acceleration, not sign.
2. Trading-value acceleration should update close probability after noon.
3. Strong institution absorption can override prior panic decay.
4. Close model needs 14:00 and 15:00 update checkpoints, not only 12:30.

## Model Rule Candidate

If all conditions hold after 13:00:

```text
institution_net_buy > +30k
trading_value_accelerating = true
advance_decline_ratio > 1.5
index > open and near high
```

then:

```text
C_domestic *= 1.5
D_panic *= 0.5
close_rebound_credit += 0.8 * (high - current_gap_floor)
```

## Paper Note

This is a useful external-model comparison:

- Claude v7 emphasized EWY transformer + avalanche diode.
- ChatGPT emphasized intraday institutional absorption + volume acceleration.
- Codex should combine both: global open transformer, shock diode, and intraday absorption capacitor.
