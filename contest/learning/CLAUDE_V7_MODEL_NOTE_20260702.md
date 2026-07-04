# Claude v7 Model Note - 2026-07-02

Source artifact: `docs/assets/claude_circuit_v7.png`

## Observed Structural Changes

Claude v7 changed the diode/RLC model into a more explicit event-flow circuit:

1. `T_EWY` transformer:
   - open model uses EWY as a direct US-session Korea repricing transformer.
   - stated coefficient: `k = 0.58`.
   - implication: open forecast can be simplified to `V_open = V_prev * (1 + k * dEWY)`.

2. `D_av` avalanche diode:
   - close model has threshold-triggered downside conduction.
   - stated trigger: foreign <= -30k and net/program <= -20k.
   - if active, rebound is suppressed and low-side voltage becomes more likely.

3. `G_inst` variable conductance:
   - institution defense is not binary.
   - size and continuity matter.
   - strong defense keeps rebound path open; weak defense fails.

4. `R_eff(t)` variable resistance:
   - crash regime increases time constant and weakens rebound speed.
   - FX/rate regime remains a resistance term.

5. `SW_hyper` narrative switch:
   - hyperscaler capex story can reset `V_target` downward.
   - this is Claude's correction after the Meta compute shock.

## Competitive Assessment

Claude v7 is no longer just a conservative diode model. It has moved toward Codex's flow-aware circuit:

- EWY transformer overlaps with Codex `V_US` / EWY input.
- Avalanche diode overlaps with Codex `D_panic`.
- Institution conductance overlaps with Codex `C_domestic`.
- Hyperscaler switch overlaps with Codex `S_regime`.

The remaining difference is operational:

- Claude v7 compresses open into EWY transformer.
- Codex vFinal keeps multi-input global voltage: SOXX, EWY, MU, NVDA, META, S&P, Nasdaq.
- Claude v7 uses threshold avalanche.
- Codex vFinal should use threshold + magnitude + acceleration.

## Codex Counter

Do not copy the v7 point value. Adopt only valid sensors:

- Add explicit EWY transformer diagnostic to open reports.
- Keep SOXX/MU/NVDA as separate semiconductor voltage; do not let EWY dominate when memory-specific shock is active.
- For close, promote avalanche state when foreign/program selling breaches threshold and low recovery fails.
- Score institution defense by magnitude and continuity, not sign.

## Paper Relevance

Claude v7 is a major model lineage event. It should be treated as an opponent model update in the Methods and Case Study sections.

Potential figure:

- Figure: Claude v6 to v7 shift versus Codex Global Gate-RC vFinal.
- Claim to test: whether multi-voltage Codex detects sector-specific shock earlier than EWY-transform Claude.
