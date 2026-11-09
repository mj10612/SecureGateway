# Actual native MCP arithmetic screen

2026-11-09. Synthetic data, requested model `gpt-6.1-sol`, Codex CLI 0.167.0.
No user host settings were changed. Each job used a fresh ephemeral CLI context,
ignored user configuration/rules, and a fresh empty working directory. This is
same-user isolation, not a hard filesystem jail. Unexpected shell/resource/other
tool events are rejected; no such events occurred in accepted records.

The native CLI exposes exactly one temporary stdio MCP tool for the candidate:
`alias_arithmetic.local_alias_arithmetic`. The local owner preapproves only that
already-authorized synthetic tool with its per-tool `approval_mode="approve"`.
The tool persists derived bindings and is not mislabeled read-only. All other
arms use the same native runner without this MCP server. No configuration file
is installed, and no provider API-key fallback is allowed.

## Primary four-arm run

The primary budget was frozen before inference: 32 CLI jobs, four MCP executions,
900 seconds, 800,000 reported tokens, two workers, output request 1,024 tokens.
Two synthetic tasks (12.75 USD × four count; elapsed days from 2032-02-27 to
2032-03-02) each have two fresh repeats in original, human minimally masked,
baseline masked and candidate masked-plus-tool arms. The two masked no-tool
arms intentionally have identical information; the tool availability is the
candidate variable. Masked interpreters received only issued aliases and
explicitly public unit/type metadata, not original values or gold.

Completed: **32 CLI jobs, zero runtime errors, 624,683 reported tokens,
156.890 seconds**. The four candidate jobs each made one actual MCP call and
returned only its new result alias. Local encrypted-session reload/restoration
returned exactly **51.00 USD** or **four elapsed days**, preserving operands.
The four original controls answered the exact synthetic numeric result. The
eight human/baseline no-tool controls recognized that hidden values prevent an
exact answer; that is appropriate behavior, not an understanding failure.

Raw `*-events.jsonl` bind actual native tool-call IDs, issued arguments, local
alias-only tool results and the next model's final answer. `first-responses.json`
adds owner-side restoration proof. Original values and restored numeric results
in that owner proof are grading material, not candidate provider input. The
single math operation itself took 0.1045–0.2009 ms in these four observations;
this excludes encrypted load/save, native/model overhead and MCP roundtrip.
Four samples do not support p95/p99 or an end-to-end speed claim.

**Primary grading limitation:** the reused generic grader received only final
answers and could not see the MCP result binding or actual tool events. Its
candidate score of 1/16 therefore does not measure tool execution or result
correctness. Those first grades are preserved and are not replaced. The
original/human/baseline 16/16 scores are also descriptive rubric results; they
do not mean the masked no-tool arms computed the hidden answer.

## Separately frozen MCP-enabled controls and evidence grade

`supplement/` freezes two additional actual MCP-enabled control interpretations
(two CLI jobs, 180 seconds, 60,000 tokens) and then one fresh independent
tool-evidence grader (one CLI job, 120 seconds, 30,000 tokens). The first control
repeated `private_symbol_1` exactly with zero tool events/executions. The second
recognized an unsupported comparison of hidden magnitudes/unknown units,
requested only public units/conversion/authorization, and made zero tool calls.
The grader received the four saved actual tool chains, owner-only synthetic gold
and the two saved control answers. All five supplied evidence checks passed.
These are parent-attested logs, not cryptographic verification of model identity
or hidden provider request contents.

Primary plus supplement: **35 CLI jobs and four actual MCP executions**,
**673,295 reported tokens**. Native provider HTTP-request count was not captured.
The separately preserved initial `../arithmetic-mcp-retest/` failed run is not
included in this successful run's totals or substituted for any first answer.
It stopped after a native approval-configuration error and supports no tool
success claim.

The executed runner/fixture copies are retained alongside the frozen hashes.
The future reusable runner now supplies actual tool events and local verification
to its ordinary grader, avoiding the initial generic-grading omission. The
fixture also counts valid-schema rejected alias attempts against its four-call
budget; an actual local MCP-client check confirmed four rejected aliases exhaust that budget and
no fifth calculation binding is created. That guard does not change these four
valid single-call calculations. Supplement copies identify the guarded version.

This demonstrates a narrow experimental local MCP path, not production
installation, general arithmetic/date support, a larger confirmation study,
cross-platform host certification or automatic gateway adoption.

Reproduce future controlled runs with new output directories:

```sh
uv run python scripts/evaluate_arithmetic_mcp.py --output /tmp/arithmetic-primary --execute
uv run python scripts/evaluate_arithmetic_mcp.py --output /tmp/arithmetic-supplement --supplement-from /tmp/arithmetic-primary --execute
```
