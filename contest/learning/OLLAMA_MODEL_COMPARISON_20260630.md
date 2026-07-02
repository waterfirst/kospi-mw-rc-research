# Ollama Auditor Model Comparison - 2026-06-30 KST

Purpose: choose a low-token local model for KOSPI forecast auditing.

Hardware:
- GPU: NVIDIA GeForce RTX 5060 Laptop GPU, 8 GB VRAM
- Runtime: Ollama

Models tested:
- `glm4:9b` - already installed, 5.5 GB
- `deepseek-r1:8b` - downloaded for comparison, 5.2 GB

## Test Task

Both models were asked to audit a compact KOSPI forecast and return strict JSON:

```json
{
  "risk_flags": ["fx", "foreign_flow"],
  "open_delta_pts": -50,
  "close_delta_pts": -100,
  "confidence": 0.5,
  "reason_code": "fade_risk"
}
```

The desired role is not full forecasting. The model should act as a cheap local validator that suggests small deltas to Codex's deterministic Gate-RC forecast.

## Observations

| Model | Result | Token Behavior | Practical Judgment |
|---|---|---:|---|
| `glm4:9b` | Produces JSON-like output quickly, but sometimes violates bounds | About 200-250 input tokens and 45-50 output tokens after prompt tuning | Usable as a cheap auditor only with strict schema validation |
| `deepseek-r1:8b` | Mostly spends tokens in `thinking`; final `content` may be empty under short budgets | Reached 512 eval tokens without final JSON in the audit test | Poor fit for low-token KOSPI auditing |

## Key Finding

`deepseek-r1:8b` is not broken. It is the wrong shape for this job. It reasons internally and may need a larger output budget to reach a final answer. That defeats the goal: save tokens and return a compact, machine-checkable delta quickly.

`glm4:9b` is imperfect, but it reaches the output phase quickly. With validation gates, it is currently the better local helper.

## Operating Rule

Use local models only as validators:

1. Deterministic Codex model produces the forecast.
2. Ollama model proposes `open_delta_pts` and `close_delta_pts`.
3. Codex accepts the local model only if JSON is valid, bounded, and directionally plausible.
4. Invalid or excessive deltas are logged but ignored.

Current recommendation:

```text
Default local auditor: glm4:9b
Do not use deepseek-r1:8b for low-token JSON audit.
Consider testing Qwen-style instruct models later if JSON compliance becomes the bottleneck.
```
