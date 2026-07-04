# Postmortem - 2026-07-03 Codex Miss

Research only. Not investment advice.

## Result

| Part | Codex forecast | Actual | Error | Score |
|---|---:|---:|---:|---:|
| Open | 7,505 | 7,739.75 | 234.75 pt / 3.03% | 0/5 |
| Close | no official 12:30 submission | 8,088.34 | n/a | 0/5 |

Total: 0/10.

## What Went Wrong

### 1. Panic Decay Was Too Slow

The model kept `domestic_damage_continuation` active after the 2026-07-02 crash. That was directionally understandable but too rigid.

The prior day already priced a large AI-capacity and semiconductor shock. Overnight EWY was weak, but not a second-collapse signal. SOXX/MU weakness still mattered, yet the open model should have moved from pure crash continuation to a mixed state:

```text
post_crash_relief_possible
```

Instead, Codex stayed too bearish.

### 2. EWY Was Underweighted At The Open

Claude v7's EWY transformer was not enough by itself, but it caught an important point: EWY is the US-session Korea price-discovery instrument.

Codex correctly separated EWY from SOXX/MU damage, but after a one-day -7.89% KOSPI crash, EWY should have become a stronger anchor than normal. The model treated EWY as just one input instead of a post-crash stabilizer.

### 3. Rebound Convexity Was Missing

After a crash, rebound is not linear. If the market does not receive a second shock overnight, short-covering, institution buying, and bargain hunting can create convex rebound pressure.

The model had `D_panic`, but lacked a reverse path:

```text
panic_exhaustion_rebound
```

That missing reverse diode is the main open-model defect.

### 4. Close Forecast Was An Operations Failure

The scheduled 09:05, 10:30, and 12:30 close-forecast processes remained alive but did not write official forecast files. Therefore the close must be scored as non-submission.

This is worse than a bad model call because the contest requires timestamped submission. A model that does not submit has no scientific value.

### 5. Institution Absorption Was Under-modeled

Final market context showed strong institution buying and large trading value. The close finished near the daily high. The model's current close logic does not sufficiently detect:

- institution net-buy acceleration,
- trading-value acceleration,
- breadth recovery,
- failed continuation of panic selling,
- high-close behavior after a deep intraday low.

## Corrective Rules

### Open Model Fix

Add `post_crash_relief_possible` when:

```text
prior_kospi_return <= -5%
EWY > -3.5%
SOXX is weak but not paired with fresh Korea-specific negative news
foreign/program damage is prior-day, not new same-day data
```

Action:

```text
D_panic *= 0.55
EWY_weight *= 1.35
open_floor = prev_close * 0.985
```

### Close Model Fix

Add institution absorption branch after 13:00:

```text
institution_net_buy >= +30k
trading_value_accelerating
advance_decline_ratio >= 1.5
current > open
current >= midpoint(high, low)
```

Action:

```text
C_domestic *= 1.5
D_panic *= 0.5
close_rebound_credit += 0.8 * (high - current)
```

### Operations Fix

Add watchdog:

```text
target_time + 3 minutes:
  if expected forecast file missing:
      run immediate fallback
      send Telegram warning
      save fallback as official only if before cutoff
```

Close cutoffs:

- 09:05 monitor: valid until 09:15.
- 10:30 monitor: valid until 10:40.
- 12:30 final close call: valid until 12:40.

## Lesson

The 2026-07-03 failure was not just a bearish forecast error. It revealed two defects:

1. the circuit lacked a reverse diode for panic exhaustion,
2. the experiment lacked a watchdog for timestamped submissions.

Both must be fixed before the next trading day.
