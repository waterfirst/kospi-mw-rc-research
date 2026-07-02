# 2026-07-02 Postmortem - Meta News Miss

Purpose: research/contest postmortem, not investment advice.

## Official KOSPI

| Field | Actual |
|---|---:|
| Open | 7,933.10 |
| Close | 7,648.09 |

## Codex Forecast Score

| Part | Forecast | Actual | Error | Error % | Score |
|---|---:|---:|---:|---:|---:|
| Open | 8,135 | 7,933.10 | +201.90 | 2.55% | 0/5 |
| Close | 7,864 | 7,648.09 | +215.91 | 2.82% | 0/5 |

Total: **0/10**

## Why The Model Failed

The model correctly classified the direction and crash-continuation regime, but still under-estimated the magnitude.

Two caps were too conservative:

1. Open model did not allow a large enough crash gap after SOX -6%, prior Samsung -5.84%, prior program -16,035, and defense_strength -25,249.
2. Close model was revised for crash-continuation, but still over-credited intraday recovery and did not treat the Meta/AI capacity news as a structural multiple-compression shock.

## Meta News Miss

The actual catalyst was broader than a normal semiconductor selloff.

News reports connected the selloff to Meta Platforms considering selling excess AI compute/cloud capacity, which triggered concerns about AI infrastructure oversupply and pressure on chip/HBM names.

Our news proxy failed because queries were too supplier-centric:

```text
Samsung Electronics HBM Nvidia
SK Hynix HBM Nvidia
US stock market semiconductor Nasdaq Fed yields
KOSPI foreign selling program trading
```

Missing queries:

```text
Meta excess AI compute cloud business semiconductor stocks
Meta AI compute capacity chip stocks Nvidia memory
AI infrastructure oversupply semiconductor selloff Meta
```

## Rule Update

If a hyperscaler demand signal flips from "buying more chips" to "selling excess compute/capacity", treat it as:

```text
AI_CAPEX_DEMAND_SHOCK = true
```

Then:

```text
open_gap_floor <= -4.5%
close_recovery_credit *= 0.4
semiconductor_score *= 1.5
```

## Code Update

`monitor/overnight_0730_strategy.py` news queries now include Meta / AI compute / oversupply searches.

