# #364 validation — lean and batched Codex evaluation vs the individual #313 run

Preregistration: `preregistration.json` (thresholds fixed before any batched
call). Script: `run_validation.py`. Reference: `reference-313/` (the individual
native #313 run, hashes in `reference-313.sha256`). Machine-readable results:
`report.json`. Model `gpt-6.1-sol`, reasoning `low` for every stage (same as the
reference, so only the transport changes). Codex CLI 0.167.1, ChatGPT
subscription only.

## Fixed overhead per call

| Setting | Fixed input tokens (one-word prompt) |
|---|---|
| native adapter (reference) | 15,019–15,195 |
| + 20 tool features disabled | 11,206 |
| + one-line base instructions (`model_instructions_file`) | 7,074–7,078 |

`code_mode_host` stays enabled: disabling it emits a warning item that the
fail-closed event filter rejects.

## Stages

| Stage | Interpretation | Grading | Calls | Raw tokens | Raw tokens / case |
|---|---|---|---|---|---|
| Reference | native, 1 per item (264) | native, 1 per case (88) + regrades | ~352 | 5,561,605 | 63,200 |
| G | stored reference answers | lean, batch 4 | 28 | 442,188 | 5,025 (grading only) |
| G2 (fallback) | stored reference answers | lean, batch 2 | 49 | 593,843 | 6,748 (grading only) |
| I | lean, batch 8 per condition | lean, batch 2 | 83 | 925,406 | **10,516** |

Stage I interpretation: 264 answers in 33 calls, no split failure or retry
(327,526 raw tokens).

## Agreement with the reference

| Check (threshold) | G (batch 4) | G2 (batch 2) | I |
|---|---|---|---|
| criterion agreement (G1 ≥ 0.95) | **0.947 — fail** | 0.956 — pass | 0.942 |
| whole-task agreement (G2 ≥ 0.90 / I1 ≥ 0.85) | 0.924 — pass | 0.947 — pass | 0.924 — pass |
| per-arm passes within ±5 (I2) — A / C / D1 | 81 / 50 / 66 vs 83 / 61 / 71 | 83 / 51 / 67 | 84 / **54** / 69 — **C fails (−7)** |
| C vs D1 direction kept (D-only > C-only) | 16 > 0 — pass | 16 > 1 — pass | 16 > 1 — pass |
| tokens ≤ 18,960 per case | | | 10,516 — pass (−83%) |

Disagreements are one-sided: the new grader passes fewer items (G2: 59
reference-only vs 5 new-only criterion passes), most of them in arm C.

## Decision under the frozen #313 rule

| Run | A / C / D1 | D-only / C-only | p | prohibition C−D | Decision |
|---|---|---|---|---|---|
| Reference | 83 / 59 / 68 | 10 / 1 | 0.0059 | 2 | REJECT |
| G | 81 / 48 / 64 | 16 / 0 | 0.00002 | 1 | ADOPT |
| G2 | 83 / 50 / 65 | 16 / 1 | 0.0001 | 1 | ADOPT |
| I | 84 / 52 / 67 | 16 / 1 | 0.0001 | 0 | ADOPT |

The reference REJECT rested on exactly the 2-case prohibition margin. Under the
lean grader that margin is 0–1, so the decision flips. This does **not** change
#313's recorded decision: a run's transport is fixed in its preregistration and
results from different transports are never mixed.

## Outcome against the preregistration

- Grading batch 4: rejected (G1 0.947 < 0.95). Grading batch 2: **accepted**.
- Interpretation batch 8: **not accepted** — I2 fails for arm C (−7 > ±5).
  By the preregistered fallback, interpretation stays one call per item (lean
  session) and only grading is batched. Estimated cost of that configuration:
  about 22,800 (interpretation, 264 lean calls) + 6,748 (grading) ≈ 29,500 raw
  tokens per case, about −53% — **below the 70% target**.

## Exploratory observations (not preregistered — for the next decision only)

- The arm-C shift appears already when only the grader changes (G2: C 61→51 on
  the reference's own answers) and is smaller with batched interpretation (I:
  54). Comparing I with G2 (same grader), per-arm passes differ by +1 / +3 / +2,
  i.e. the I2 failure is attributable to the grader change, not to
  interpretation batching. Confirming this needs a preregistered run where both
  interpretation transports are graded by the same grader.
- Reading the 10 cases where the reference passed C and G2 failed it: in most,
  the baseline engine had masked a public word (`Pot`, `QA`, `Lantern` →
  `private_symbol_*`) and the answer kept the alias where the expected behaviour
  requires the public name. The lean grader's failures look justified there; the
  reference grader was more lenient. This is the coordinator's reading, not a
  measured result.

## Incidents

- `stage-G-attempt1-no-error-log/`: first G attempt, 16 of 22 batch calls failed
  without a recorded reason (the script did not yet store failure messages).
  Kept as evidence, not used.
- Stage G: 8 cases failed because the subscription account ran out of credits.
  The CLI exits non-zero on a limit, and the first adapter version raised a
  generic failure before reading the event stream. Fixed in 2.15.0
  (`capture_worker_process(check=False)` + classification →
  `UsageLimitReached`); the 8 cases were then resumed on another account.

## Limitations

No test–retest of the individual method exists, so part of every disagreement
is ordinary run-to-run variation. One task family (#313). Interpreter and grader
are the same model family. Accounts were selected per command with `CODEX_HOME`;
no user or Orca configuration was changed.
