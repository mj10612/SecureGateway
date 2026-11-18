# #319 disposition: retain default off; do not adopt this candidate

Status clarification in 2.20.2, 2026-11-19. This closes the original experimental
proposal with a negative adoption disposition, not a claim that local arithmetic
accuracy or gateway-wide policy integration has been solved. The runtime,
explicit opt-in API, tool schema, default settings and frozen evidence are unchanged.

## Evidence and decision

The [natural-wording holdout report](comprehension-2.11.1/319/comprehension-natural/report.json)
and [run narrative](comprehension-2.11.1/319/plan-natural/README.md) already record
an actual `gpt-6-luna` experiment at 2.18.0. The local MCP fixture executed real
model-selected calls on synthetic aliases. These measurements replace the old
user-facing description of "unmeasured, blocked by #363"; the #363 numeric-binding
and #375 alias-spelling fixes were merged before this status correction.

| Recorded measurement | Result |
| --- | --- |
| Selected cases | 80 (40 tool-solvable, 14 no-calculation, 26 impossible) |
| A-eligible whole-task passes A / C / D | 52 / 12 / 32 |
| Eligible tool-solvable all-criteria passes | 23/35 = 65.7%, below the 80% gate |
| Eligible controls with a D tool call | 8/17, above the at-most-one gate |
| Tool call with issued aliases / local restore matching gold | 34/35 / 32/35 |
| C/D trajectories exposing an original or computed value | 0 observed |
| Calls / raw tokens in saved usage | 308 / 3,188,461 |
| Ungraded cases after the permitted re-grade | 7/80 |

The stored report labels the outcome **REJECT**, with rejection in all five
missing-grade sensitivity scenarios. Those scenarios do **not** fill in the seven
missing grades: the frozen protocol required incomplete grading to be treated as
INCOMPLETE. Accordingly this disposition does not certify a fully completed
protocol or upgrade those missing cases to measured results. Even among observed
eligible controls, eight tool calls already exceed the adoption ceiling of one.
There is no basis to enable this candidate by default. Keeping it off is a
conservative product decision under incomplete evidence, consistent with the
reported rejection, rather than a new efficacy result.

## Limits preserved

- The all-criteria gap includes grading problems: answer `scope` was assessed
  against a tool transcript only D possessed, and bare result aliases were not
  consistently resolved by the grader. Mechanical 32/35 restoration is not the
  same endpoint as 23/35 all-criteria success.
- Interpreter and grader share a model family. D's code-mode `exec` body was not
  fully auditable; only the allowed MCP trajectory was captured. The historical
  CLI also supplied user skill catalog context; see the
  [#380 isolation correction](issue380/README.md).
- This is a synthetic, forced-number, model/fixture-specific experiment. Ordinary
  numbers are public by default since #374. Zero observed C/D value disclosures
  does not establish a general privacy guarantee.
- Gateway configuration still has no per-alias numeric/unit authorization path:
  enabling the boolean alone injects the tool but its calls are refused without
  an explicit trusted policy. The local session API and compatibility profiles
  are retained for reproducibility; the feature stays default off.

## Deferred work

A different candidate needs a separately preregistered evaluation: neutral tool
instructions, answer-only scope grading, consistent bare/displayed alias handling,
new independent cases, complete grading, and an explicit call/time/token budget.
Do not rewrite this run's first responses, rubric, decision or historical scores
to make it pass. Such a future experiment and gateway policy design are not
delivered by this documentation correction. Default-feature planning remains
tracked by #354. Closing #319 records the disposition of the tested candidate;
it does not mark those deferred tasks complete.

No new model or provider call was made for this correction.
