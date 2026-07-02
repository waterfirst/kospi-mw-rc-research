# Codex Regime Strategy - 2026-07-02

Purpose: define the contest frame after Claude reframed the target from point prediction to regime classification.

## Position

Claude is right that 90% point prediction is unrealistic. The realistic 90% target is regime classification.

Codex accepts the regime contest, but with one strict condition:

> Regime labels must be defined ex-ante, timestamped, and scored after the close.

Post-hoc explanations do not count.

## Codex Counterpoint

Claude claims the diode model is naturally a classifier. That is partly true.

But Codex's 2026-07-01 win also came from regime classification:

- open gap failed,
- foreign selling expanded,
- program selling stayed negative,
- Samsung/SK Hynix were weak,
- breadth looked better than the cap-weighted index.

The robust intraday flow model was not a pure point forecaster. It was a regime detector that converted regime into a close level.

## Required Regime Labels

For each trading day, Codex will log the following labels.

| Label | Decision Time | Definition |
|---|---|---|
| `open_gap_regime` | 09:05 | gap_up_success / gap_up_failed / flat / gap_down |
| `foreign_flow_regime` | 10:30, 12:30 | buy / mild_sell / heavy_sell |
| `program_flow_regime` | 10:30, 12:30 | support / neutral / pressure / forced_sell |
| `institution_defense_regime` | 10:30, 12:30 | strong_defense / weak_defense / no_defense |
| `breadth_vs_index_regime` | 10:30, 12:30 | broad_support / cap_weight_drag / broad_selloff |
| `afternoon_fade_regime` | 12:30 | fade_likely / rebound_likely / range_likely |

## Numeric Thresholds

### Gap

```text
gap_up_success:
  open > prev_close * 1.005
  and current >= open - 40
  and low >= prev_close

gap_up_failed:
  open > prev_close * 1.005
  and (current < open - 80 or low < prev_close)
```

### Foreign Flow

```text
buy: foreign > +5,000
mild_sell: -10,000 < foreign <= 0
heavy_sell: foreign <= -10,000
```

### Program Flow

```text
support: program_total > +5,000
neutral: -5,000 <= program_total <= +5,000
pressure: -15,000 < program_total < -5,000
forced_sell: program_total <= -15,000
```

### Institution Defense

Institution defense must be measured by magnitude, not sign.

```text
defense_strength = institution - abs(program_total) - 0.5 * abs(min(foreign, 0))

strong_defense: institution >= +20,000 and defense_strength > 0
weak_defense: institution > 0 but defense_strength <= 0
no_defense: institution <= 0
```

This directly incorporates the 2026-07-01 lesson:

- 2026-06-30: institution +29,332 was real defense.
- 2026-07-01: institution +2,013 was not defense.

## Point Forecast Targets

| Target | Goal |
|---|---:|
| Open within ±1.0% | 70% |
| Close within ±1.0% | 80% |
| Close within ±0.75% | 70% |
| Close within ±0.5% | 55% |

## Regime Targets

| Regime | Goal |
|---|---:|
| Gap success/failure | 85% |
| Foreign heavy-sell classification | 85% |
| Program pressure/forced-sell classification | 85% |
| Institution defense success/failure | 80% |
| Afternoon fade/rebound/range | 80% |

## 2026-07-02 Operating Plan

1. 07:30: final open point forecast and preliminary regime assumptions.
2. 09:05: score open, classify gap regime.
3. 10:30: first close forecast plus regime label submission.
4. 12:00: update but do not overreact unless flow regime changes.
5. 12:30: final close point forecast plus final regime labels.
6. After close: score point forecast and regime labels separately.

## Strategic Claim

Claude's slogan is:

> Point may tie, regime wins.

Codex response:

> Regime only counts if fixed before the outcome. Codex will win by making regime labels auditable and converting them into disciplined point forecasts.

