# KOSPI Forecast Contest Rules v2

Claude and Codex are scored independently under the same information cutoff.
Both sides may use Gemini and Z.ai as advisory models, but every submitted forecast
must be grounded in recorded market snapshots and locked before the cutoff.

Information/research purpose only. Not investment advice.

## Participants

- Claude Consortium: Claude plus Gemini, Z.ai, and optional local models.
- Codex Consortium: Codex plus GPT API, Gemini, Z.ai GLM 5.2 API, and local Ollama `glm4:9b` advisory calls.

The assistant named in the submission owns the final forecast. Advisory model output
does not replace source data, and it cannot be used to invent unavailable market data.

## Codex Agent Split

To minimize Codex/API token use, Codex stores the raw source snapshot but sends only
a compact digest to advisory agents.

| Agent | Runtime | Role |
|---|---|---|
| Local compressor | Ollama `glm4:9b` on NVIDIA GPU | First-pass compression and conservative local forecast |
| GPT verifier | OpenAI GPT API | Consistency check, missing-data check, anti-hallucination guard |
| Z.ai quant | Z.ai GLM 5.2 API | Numeric point estimate, probabilities, risk balance |
| Gemini cross-check | Gemini API | Source-support cross-check and scenario sanity check |
| Codex finalizer | Codex | Schema validation, ensemble, cutoff lock, record/Telegram |

Only valid JSON outputs that pass schema and numeric validation are eligible for the ensemble.

## Daily Score

Total: 10 points.

### Part 1. Open Forecast - 5 Points

- Cutoff: Monday 08:00 KST, one hour before market open.
- Submission: one fixed point forecast for the official KOSPI open.
- Target: actual KOSPI open at 09:00.

Required submission:

```text
forecast_open: number
direction_from_prev_close: UP | DOWN | FLAT
confidence: 0.00-1.00
evidence: short grounded notes
snapshot_hash: source snapshot hash
```

### Part 2. Close Forecast - 5 Points

- Morning monitoring: 09:00 open, 10:30, 12:00.
- At each checkpoint, record index level, foreign flow, institutional flow, US futures if available, and model state.
- Cutoff: 12:30 KST.
- Submission: one fixed point forecast for the official KOSPI close.
- Target: actual KOSPI close at 15:30.

Required submission:

```text
forecast_close: number
direction_from_prev_close: UP | DOWN | FLAT
prob_up: 0.00-1.00
prob_down: 0.00-1.00
confidence: 0.00-1.00
evidence: short grounded notes
monitoring_snapshots: 09:00, 10:30, 12:00 snapshot hashes
snapshot_hash: final source snapshot hash
```

## Accuracy Tiers

Error rate:

```text
abs(forecast - actual) / actual * 100
```

| Error rate | Score |
|---|---:|
| <= 0.25% | 5 |
| <= 0.50% | 4 |
| <= 0.75% | 3 |
| <= 1.00% | 2 |
| <= 1.50% | 1 |
| > 1.50% | 0 |

Total score:

```text
total = open_score + close_score
```

Higher total wins. If tied, the higher close score wins. If still tied, it is a draw.

## Anti-Hallucination Rules

1. Every market number in a forecast must come from a fetched source snapshot or be explicitly marked unavailable.
2. Gemini and Z.ai outputs are advisory only. The final submitted forecast must include source snapshot hashes.
3. If a source fetch fails, record the failure and continue conservatively. Do not invent missing prices, flows, futures, news, or API results.
4. Forecast JSON must pass schema and numeric validation before submission.
5. Forecasts cannot be edited after the cutoff. Later corrections must be logged as postmortem notes, not forecast updates.
6. The 08:00 open forecast cannot use post-08:00 data. The 12:30 close forecast cannot use post-12:30 data.

## Environment Variables

API keys must not be committed to the repository. Use environment variables only:

```powershell
$env:GOOGLE_API_KEY="..."
$env:OPENAI_API_KEY="..."
$env:ZAI_API_KEY="..."
```

Optional model overrides:

```powershell
$env:CODEX_GEMINI_MODEL="gemini-2.5-pro"
$env:CODEX_GPT_MODEL="gpt-4.1-mini"
$env:CODEX_ZAI_MODEL="glm-5.2"
$env:CODEX_OLLAMA_MODEL="glm4:9b"
$env:ZAI_CHAT_COMPLETIONS_URL="https://api.z.ai/api/paas/v4/chat/completions"
$env:OLLAMA_GENERATE_URL="http://127.0.0.1:11434/api/generate"
```

Run modes:

```powershell
python monitor/codex_contest_forecast.py --mode open --local-only
python monitor/codex_contest_forecast.py --mode open
python monitor/codex_contest_forecast.py --mode close
```

Telegram result delivery:

```powershell
$env:TELEGRAM_BOT_TOKEN="..."  # or TELEGRAM_TOKEN
$env:TELEGRAM_CHAT_ID="..."
python monitor/score_duel.py --telegram
```
