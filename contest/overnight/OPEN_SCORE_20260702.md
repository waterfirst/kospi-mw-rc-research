# 2026-07-02 KOSPI Open Score

Purpose: research/contest postmortem, not investment advice.

## Actual Open

Official KOSPI open: **7,933.10**

Codex 07:31 forecast: **8,135**

Error:

| Metric | Value |
|---|---:|
| Point error | +201.90pt |
| Absolute error | 201.90pt |
| Error pct | 2.55% |
| Score tier | 0/5 |

## What Happened

The direction was right but the magnitude was badly under-estimated.

The model saw:

- SOX -6.27%,
- prior KOSPI damage,
- foreign -17,028,
- program -16,035,
- Samsung -5.84% and SK Hynix -3.40%.

But actual early-session flow was worse:

| 09:56 Signal | Value |
|---|---:|
| Current | 7,815.85 |
| Open | 7,933.10 |
| Low | 7,723.57 |
| Foreign | -30,157 |
| Institution | +3,697 |
| Program total | -25,245 |
| Samsung Electronics | -7.00% |

## Model Failure

The model capped domestic damage too tightly.

Previous cap:

```text
domestic_damage max roughly 1.77%
```

This was insufficient for a forced-sell continuation after:

- prior day semiconductor crash,
- SOX -6% overnight,
- program selling expansion,
- foreign selling acceleration.

## Rule Update

If all are true:

```text
SOX <= -5%
prior Samsung <= -5%
prior program <= -15,000
defense_strength < -20,000
```

then use crash-continuation mode:

```text
open_gap_floor = -4.5%
open_gap_center = raw_gap - domestic_damage * 1.2 - fx_drag * 0.5
```

Do not clamp the open near -2%.

