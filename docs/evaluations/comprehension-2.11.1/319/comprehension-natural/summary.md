# #319 local arithmetic — REJECT (natural-wording holdout, `gpt-6-luna`, 2.18.0)

Frozen plan: [`../plan-natural/README.md`](../plan-natural/README.md). Evidence: `report.json`,
`first-responses.jsonl`, `first-grades.jsonl`, `frozen-rubric.json`, `frozen-decision.json`.

80 fresh cases (40 tool-solvable, 14 no-calculation, 26 impossible) whose text never mentions a tool
or alias; 240 interpretations, 308 counted calls, 3,188,461 raw tokens.

| Metric | Value |
|---|---|
| A-eligible cases / A, C, D whole-task passes | 52 / 52, 12, 32 |
| Tool-solvable A-eligible / correct locally restored (all criteria) | 35 / 23 (65.7%, gate 80%) |
| D tool use with issued aliases | 34 / 35 |
| D local restore equal to the gold | 32 / 35 (91.4%, mechanical check) |
| A `answer_value` / C `answer_value` | 35/35 / 0/35 |
| D-only / C-only discordant cases (one-sided p) | 23 / 0 (p = 1.2e-07) |
| A-eligible controls with a D tool call (gate <= 1) | 8 of 17 (29 of 40 overall) |
| C/D trajectories exposing an original or computed value | 0 |
| Ungraded after one re-grade | 7 (8.75%); decision identical under all five bounds |

**Frozen decision: REJECT.** The candidate still enables the masked arithmetic when the model uses
the tool (C cannot produce the value at all), and no original or computed value reached the
provider, but the end-to-end all-criteria rate is 65.7% and 8 eligible control cases made an
unnecessary or forbidden tool call. Most of the correctness gap is grading, not arithmetic: 9 of the
13 non-passes fail `scope` on the sanitized tool transcript that only D carries, and 3 fail
`restored_result` on an answer that used the bare `private_symbol_N` form that the grader did not
resolve although local restore did. The tool remains **default off**; the next preregistered run
needs a neutral D prompt, answer-only `scope` grading, and a fix for the bare-alias answer form.
