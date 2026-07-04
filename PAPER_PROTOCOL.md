# KOSPI Circuit Model Duel Paper Protocol

Purpose: preserve all artifacts needed to write a reproducible paper after the July 2026 Codex vs Claude Fable 5 contest.

The repository is the source of truth. Do not rely on chat memory alone.

## Research Question

Can an event-aware electrical-circuit analogy model improve next-day KOSPI open/close forecasts versus a competing narrative/diode model over a July 2026 live contest?

## Contest Period

- Start: 2026-06-30 live preparation.
- Main campaign: 2026-07-01 to 2026-07-31 KST.
- Models: Codex Global Gate-RC vFinal vs Claude/Fable 5 Mythos lineage.

## Required Daily Records

Each trading day must preserve:

| Stage | Time KST | Required files |
|---|---:|---|
| Overnight/pre-open | 21:30-07:30 | `contest/overnight/*.json`, `contest/overnight/*.txt` |
| News shock monitor | continuous | `contest/news/*.json`, `contest/news/seen_news.json` |
| Open score | after 09:00 | `contest/overnight/OPEN_SCORE_*.md` or daily scoreboard |
| Intraday close forecasts | 09:05, 10:30, 12:30 | `contest/intraday/*_robust_close_forecast.json` |
| Final close score | after close | daily score/postmortem markdown |
| Parameter updates | after close only | `contest/learning/*.json`, `contest/learning/*.md` |

## Circuit Diagrams

Core diagrams:

- Codex final: `docs/assets/codex_final_global_gate_rc_vfinal.svg`
- Codex final page: `docs/codex_final_circuit.html`
- Three-model comparison: `docs/three_model_circuit_comparison.html`
- Claude v6 reference: `docs/assets/claude_circuit_v6.png`
- Claude v7 reference: `docs/assets/claude_circuit_v7.png`
- Codex earlier global-flow diagram: `docs/assets/codex_global_flow_v1.png`

Any structural model change must add a new diagram or explicit diff note.

## Model Lineage

1. Original Codex MW-RC / Gate-RC.
2. Claude Diode/RLC v5-v6 benchmark.
3. Codex Global Flow Circuit v1.
4. Codex Global Gate-RC vFinal.
5. Claude v7 EWY transformer + avalanche diode counter-model.

Lineage notes must explain why a change was made:

- miss class,
- newly detected event channel,
- backtest result,
- live forecast failure,
- Claude/Fable counter-strategy.

## Scoring

Point forecast score:

- <= 0.25% error: 5
- <= 0.50% error: 4
- <= 0.75% error: 3
- <= 1.00% error: 2
- <= 1.50% error: 1
- > 1.50% error: 0

Daily score:

- open score + close score.
- tie breaker: close score.

Regime score:

- A regime call only counts if timestamped before the relevant move.
- Post-hoc regime explanations do not count.

## Event Taxonomy

Primary July event classes:

- AI capacity / HBM / memory-cycle shock.
- US macro: CPI, PPI, employment, FOMC.
- Korea macro: BOK, USD/KRW, foreign flow.
- Mega-flow: ETF, passive, MSCI, ADR/listing, month-end rebalance.
- Intraday microstructure: program selling, institution defense, gap failure.

## Paper Outline Draft

1. Abstract.
2. Introduction: why KOSPI reacts as a coupled global-local circuit.
3. Related Ideas: electrical analogies, regime switching, flow-driven markets.
4. Model: Global Gate-RC vFinal.
5. Experimental Design: live July contest vs Claude/Fable 5.
6. Data: public market data, Naver endpoints, public news RSS, manual Claude values.
7. Results: open/close point score and regime score.
8. Case Studies: Meta AI capacity shock, CPI/FOMC weeks, month-end flow.
9. Failure Analysis: stale news, wrong resistance, weak/strong domestic capacitance.
10. Limitations: not investment advice, no direct X/SNS firehose, data quality risk.
11. Conclusion.

## Repository Rule

All material changes must be committed and pushed directly to GitHub. No PR workflow.

Before push:

- scan for tokens/secrets,
- keep code comments/docstrings minimal,
- prefer English inside code files,
- keep Korean explanations in final markdown/html documents.
