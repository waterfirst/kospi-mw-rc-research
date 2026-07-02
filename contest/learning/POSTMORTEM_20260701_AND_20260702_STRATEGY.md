# 2026-07-01 Postmortem and 2026-07-02 Strategy

Purpose: research/contest forecasting notes, not investment advice.

## Final Score

Official KOSPI 2026-07-01:

| Field | Actual |
|---|---:|
| Open | 8,591.50 |
| Close | 8,303.41 |

| Model | Open Pred | Open Score | Close Pred | Close Score | Total |
|---|---:|---:|---:|---:|---:|
| Claude | 8,525 | 2/5 | 8,420 | 1/5 | 3/10 |
| Codex | 8,525 | 2/5 | 8,320 | 5/5 | 7/10 |

Result: **Codex wins 7:3**.

## What Worked

The robust intraday flow model worked.

| Checkpoint | Current | Robust Close Pred | Actual Close | Error |
|---|---:|---:|---:|---:|
| 09:34 | 8,459.54 | 8,420 | 8,303.41 | 116.59 |
| 10:30 | 8,322.39 | 8,316 | 8,303.41 | 12.59 |
| 12:00 | 8,312.33 | 8,316 | 8,303.41 | 12.59 |
| 12:30 | 8,314.86 | 8,316 | 8,303.41 | 12.59 |
| 14:11 | 8,376.50 | 8,316 | 8,303.41 | 12.59 |

The close was forecast well because the model followed:

- gap failure,
- foreign selling,
- program selling,
- Samsung/SK Hynix weakness,
- low recovery after the morning washout.

## What Failed

The open model failed.

Both Claude and Codex predicted 8,525, but the actual open was 8,591.50. The miss was caused by over-trimming the overnight SOX/EWY impulse.

Rule update:

```text
If SOX >= +3.5% and EWY >= +2.0%, do not cap the open gap below +1.0%
unless there is fresh pre-open FX shock, futures weakness, or Korea-specific bad news.
```

## 2026-07-02 Open Strategy

Do not produce the final open call until US close and 07:30 KST data refresh.

Open model hierarchy:

1. Overnight US indices: S&P, Nasdaq, SOX.
2. Korea proxy: EWY and USD/KRW.
3. Prior Korea session damage: close below open by 288pt, Samsung -5.84%, SK Hynix -3.40%.
4. Flow memory: foreign -17,028, program -16,035.

Regime assumptions:

| Overnight Setup | 7/2 Open Bias |
|---|---|
| SOX/EWY rebound strongly | Relief gap up, but cap if USD/KRW remains high |
| US flat | Weak/flat open; prior domestic damage dominates |
| SOX down again | Gap down / continuation risk |

Open formula change:

```text
open_gap = US_impulse + EWY_proxy - FX_drag - domestic_damage_memory
```

Domestic damage memory must include Samsung/SK Hynix crash and program selling.

## 2026-07-02 Close Strategy

Use robust intraday flow model as primary from 10:30 onward.

Checkpoint process:

| Time | Action |
|---|---|
| 07:30 | Final open forecast, preliminary close scenario only |
| 09:05 | Score open, classify gap success/failure |
| 10:30 | First serious close forecast |
| 12:00 | Update close forecast |
| 12:30 | Submit final close forecast |

Close regime rules:

| Condition | Close Strategy |
|---|---|
| Gap up and current below open by >80pt | Treat as gap failure; fade model active |
| Foreign < -10k and program < -8k | Strong bearish close bias |
| Current below prior close after gap up | Bearish continuation unless breadth is very strong |
| Breadth strong but index heavyweights weak | Do not over-credit breadth |
| Foreign turns positive and program improves | Allow afternoon recovery |

Primary close model:

```text
robust_close = current
  - 0.38 * max(open - current, 0)
  + 0.18 * (current - low)
  + breadth_score
  + semiconductor_score
  + US_tailwind
  + flow_score
```

This model becomes the main close forecaster until it fails on multiple days.

## Operational Notes

- Telegram messages should start with `[Codex]`.
- If Telegram env is missing, still save files locally and report `SKIPPED_NO_ENV`.
- GLM should remain a low-cost validator only. Ignore invalid JSON.
- DeepSeek R1 should not be used for the morning fast path because it burns thinking tokens.
