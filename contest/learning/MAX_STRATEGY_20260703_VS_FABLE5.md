# Max Strategy for 2026-07-03 - Codex vs Claude Fable 5/Mythos

Purpose: maximize Codex odds for KOSPI open/close contest after Claude upgrades to Fable 5/Mythos.

Not investment advice.

## Current Regime

The market is in an AI-capacity / semiconductor de-rating shock.

Key observed facts on 2026-07-02:

- KOSPI open 7,933.10, close 7,648.09, -7.89%.
- Samsung Electronics -9.06%.
- SK Hynix -14.57%.
- Foreign -43,706.
- Institution -20,825.
- Program total -22,447.
- News catalyst: Meta excess AI compute / cloud capacity report triggered AI infrastructure oversupply concerns.
- US proxy during the evening: EWY and SOXX sharply weak, MU deeply weak, META strong.

## Strategic Principle

Claude Fable 5 may reason better, so Codex must win with:

1. better data freshness,
2. ex-ante regime labels,
3. continuous news shock monitoring,
4. hard overrides for narrative shocks,
5. no invalid GLM output in final ensemble.

## Regime Labels To Submit

At 07:30:

| Label | Options |
|---|---|
| `overnight_ai_regime` | shock_continuation / relief_rebound / stabilization |
| `korea_open_regime` | crash_gap_down / relief_gap_up / flat_after_crash |
| `semiconductor_regime` | forced_deleveraging / dead_cat_bounce / stabilization |

At 09:05:

| Label | Options |
|---|---|
| `gap_regime` | gap_down_success / gap_down_reversal / panic_continuation |

At 10:30 and 12:30:

| Label | Options |
|---|---|
| `close_regime` | forced_sell_close / rebound_close / range_close |
| `institution_defense` | strong / weak / absent |
| `program_pressure` | forced_sell / pressure / neutral / support |

## Open Forecast Logic

Use crash mode if any two are true:

```text
SOXX <= -3%
EWY <= -3%
MU <= -5%
prior KOSPI <= -5%
Samsung <= -7%
SK Hynix <= -10%
program <= -20,000
Meta/excess AI compute news severity HIGH
```

Crash mode:

```text
open_ret = US_Korea_proxy + semi_proxy - domestic_damage - narrative_shock
range_width = wide, at least ±120pt
```

Relief mode only if:

```text
SOXX > +2%
EWY > +2%
MU > +3%
and no new HIGH news shock
```

## Close Forecast Logic

Do not trust the overnight open model for the close.

From 10:30 onward, use robust intraday flow model with crash-continuation clamp:

```text
close_forecast = current
  - gap_fail_penalty
  + low_recovery_credit
  + breadth_score
  + semiconductor_score
  + US_tailwind
  + flow_score
```

But if AI_CAPEX_DEMAND_SHOCK remains active:

```text
low_recovery_credit *= 0.4
semiconductor_score *= 1.5
program/foreign penalties persist into close
```

## Data Operations

Running processes required:

1. `news_shock_monitor.py --interval 900 --telegram`
2. `overnight_0730_strategy.py --target 07:30 --poll --glm --telegram`
3. `kospi_1230_close_forecast.py --target 09:05 --glm --telegram`
4. `kospi_1230_close_forecast.py --target 10:30 --glm --telegram`
5. `kospi_1230_close_forecast.py --target 12:30 --glm --telegram`

## Claude Counter

Claude Fable 5 likely advantage:

- better narrative synthesis,
- less brittle news reasoning,
- stronger postmortem.

Codex counter:

- fixed thresholds,
- live process,
- auditable data files,
- direct Telegram alerts,
- no post-hoc regime credit unless timestamped.

## Scoring Discipline

If Codex fails, record it bluntly. No narrative rescue.

If Claude gives a better value, ingest the reason but do not copy it blindly; identify which sensor caught it.

