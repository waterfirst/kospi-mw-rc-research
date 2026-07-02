# July 2026 War Roadmap vs Claude Fable 5

Research only. Not investment advice.

## Objective

Beat Claude Fable 5/Mythos through July 2026 by combining daily point forecasts with timestamped regime forecasts.

Primary scoreboard:

- Open point error.
- Close point error.
- Regime label hit rate.
- Timestamp discipline.

Do not accept post-hoc regime credit. A regime call only counts if saved before the relevant market move.

## Strategic Frame

Claude Fable 5 likely has stronger narrative synthesis. Codex must win with operations:

- fresher data,
- lower-latency public news alerts,
- fixed scoring rules,
- hard overrides for shock regimes,
- fast local compute,
- small prompts and English code files.

Daily tactics matter, but July is a campaign. The goal is not to win one day; it is to improve the sensor/parameter stack each week and reduce repeated error classes.

## July Event Map

| Date KST | Event | Risk Channel | Codex Action |
|---|---|---|---|
| Jul 2 | US Employment Situation for June 2026, 08:30 ET | rates, USD/KRW, Nasdaq/SOX direction | Treat as first major post-crash macro validation. |
| Jul 3 | US Independence Day market holiday | thin liquidity, stale US signal | Reduce overnight beta; increase Korea domestic flow weight. |
| Jul 9 | BOK July monetary policy decision expected | KRW, rates, foreign flow | Add KRW/rate override before open and close. |
| Jul 10 | SK Hynix ADR/listing-related flow watch | mega-flow, passive demand/supply, Hynix volatility | Monitor Hynix-specific news and foreign flow separately from KOSPI. |
| Jul 14 | US CPI for June 2026, 08:30 ET | US yields, DXY, SOX valuation | Predefine hot/cool CPI branches before release. |
| Jul 15 | US PPI for June 2026, 08:30 ET; Fed Beige Book | rate path, capex narrative | Update macro risk coefficient after release. |
| Jul 22-29 | SK Hynix/Samsung Q2 earnings window watch | HBM/memory demand, supply, margin | Run semiconductor narrative monitor at higher frequency. |
| Jul 28-29 | FOMC meeting | global rates, USD/KRW, risk appetite | FOMC week: regime-first, wider forecast ranges. |
| Month-end | rebalance, passive/ETF flow, window dressing | program trading, foreign flow | Increase program/foreign flow weight from Jul 27 onward. |

Known official anchors:

- Fed FOMC: Jul 28-29.
- BLS CPI: Jul 14, 08:30 ET.
- BLS PPI: Jul 15, 08:30 ET.
- BOK 2026 monetary policy meetings include July; market sources point to Jul 9.

## Weekly Battle Plan

### Week 1: Jul 3-5

Theme: post-crash stabilization vs second-wave semiconductor deleveraging.

Mission:

- Do not overfit one rebound candle.
- Keep AI-capacity shock active until SOXX/EWY/MU/Hynix confirm stabilization.
- Score every forecast with error and regime label.

Key regimes:

- `panic_continuation`
- `relief_rebound`
- `dead_cat_bounce`
- `forced_deleveraging`

Hard rule:

- If foreign + program both remain negative and Samsung/Hynix breadth is weak, do not give full rebound credit.

### Week 2: Jul 6-12

Theme: Korea policy and Hynix mega-flow.

Mission:

- Separate index recovery from semiconductor-specific flow.
- Add BOK/FX sensor before Jul 9.
- Watch Hynix ADR/listing and capital-flow narratives around Jul 10.

Key regimes:

- `policy_fx_relief`
- `krw_stress`
- `hynix_flow_distortion`
- `semi_rebound_without_index`

Hard rule:

- If KRW weakens while SOXX rebounds, trim KOSPI open and close. Korea may not fully import US semi strength.

### Week 3: Jul 13-19

Theme: US CPI/PPI and rate repricing.

Mission:

- Pre-commit CPI branches before release.
- Use US10Y/DXY/SOX response, not headline CPI alone.
- Watch if hot CPI hurts high-duration AI hardware more than broader indices.

Branches:

- Cool CPI: lower yields, DXY down, SOXX/EWY up -> open beta allowed.
- Hot CPI: yields/DXY up, SOXX down -> gap-down or fade risk.
- Mixed CPI: wait for bond/SOX close, avoid early overconfidence.

Hard rule:

- CPI week uses wider ranges. Do not chase one futures print without bonds and dollar confirmation.

### Week 4: Jul 20-26

Theme: earnings and memory-cycle truth test.

Mission:

- Upgrade narrative monitor from general AI to memory/HBM-specific.
- Track Micron, Samsung, SK Hynix, Nvidia, hyperscaler capex, cloud utilization.
- Distinguish demand scare from valuation reset.

Key regimes:

- `earnings_validation`
- `margin_peak_fear`
- `capex_oversupply_shock`
- `hbmdemand_resilience`

Hard rule:

- If earnings beat but guide/capex language weakens, treat as bearish narrative even if headline numbers are strong.

### Week 5: Jul 27-31

Theme: FOMC and month-end flows.

Mission:

- FOMC week is not a normal regression week.
- Use regime-first scoring.
- Raise passive/month-end flow weight.

Key regimes:

- `fomc_risk_on`
- `fomc_hawkish_shock`
- `monthend_foreign_sell`
- `passive_rebalance_bid`

Hard rule:

- If FOMC is hawkish and KRW weakens, do not use simple US equity beta for KOSPI open.

## Daily Operating Protocol

### 21:30-23:30 KST

- Start overnight monitor.
- Check US futures/early session, SOXX, EWY, MU, NVDA, META.
- Run public news shock monitor.
- Save preliminary open regime.

### 05:00-07:30 KST

- Recompute after US close.
- Check US10Y, DXY, USD/KRW, EWY, SOXX, MU.
- Submit final open call at 07:30.

### 09:05 KST

- Score open.
- Capture actual open, gap, high/low, foreign/institution/program.
- Label gap regime.

### 10:30 KST

- First close model.
- If foreign/program pressure accelerates, activate close shock override.

### 12:30 KST

- Final close call.
- Save point value, range, regime labels, reason.

### After Close

- Score point forecasts.
- Score regime forecasts.
- Write one short postmortem.
- Update parameters only if the same error class appears or a hard threshold failed.

## Model Architecture For July

### Open Model

Inputs:

- S&P, Nasdaq, SOXX, Dow.
- EWY, MU, NVDA, META.
- USD/KRW, DXY, US10Y.
- prior KOSPI damage.
- Samsung/Hynix damage.
- Google News shock score.

Output:

- open point.
- wide range.
- `overnight_ai_regime`.
- `korea_open_regime`.

### Close Model

Inputs:

- actual open/gap.
- current index and high/low.
- foreign/institution/program.
- breadth.
- Samsung/Hynix intraday.
- news shock persistence.

Output:

- close point.
- range.
- `gap_regime`.
- `close_regime`.
- `institution_defense`.
- `program_pressure`.

## Parameter Governance

Only update parameters after market close.

Rules:

- One-day surprise can add a watch flag, not a permanent parameter.
- Two similar misses in five sessions justify threshold adjustment.
- Three similar misses justify model branch change.
- Do not copy Claude's number. Extract the sensor Claude used and add it if valid.

## Token Discipline

Code files:

- Use English identifiers and messages.
- Avoid Korean text in code.
- Avoid comments and long docstrings unless the code would become unsafe.
- Put explanations in markdown docs, not Python files.

Forecast messages:

- Maximum 8 lines for Telegram.
- Include point, range, regime, top 3 reasons.
- No long narrative unless postmortem.

## Win Conditions

By Jul 31:

- Beat Claude in total daily wins.
- Achieve at least 70% direction/regime accuracy.
- Achieve at least 60% open within 1.0%.
- Achieve at least 60% close within 1.0%.
- Maintain timestamped records for all official calls.

## Source Anchors

- Federal Reserve FOMC calendar: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
- Federal Reserve July 2026 calendar: https://www.federalreserve.gov/newsevents/2026-july.htm
- BLS selected release schedule: https://www.bls.gov/schedule/news_release/current_year.asp
- BLS CPI page: https://www.bls.gov/cpi/
- Bank of Korea 2026 MPB schedule notice: https://www.bok.or.kr/portal/bbs/B0000502/view.do?menuNo=201265&nttId=10094300
- Samsung IR disclosures: https://www.samsung.com/global/ir/reports-disclosures/public-disclosure/
- SK Hynix IR earnings page: https://www.skhynix.com/ir/UI-FR-IR06/
