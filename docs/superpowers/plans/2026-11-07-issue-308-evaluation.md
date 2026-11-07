# Issue 308 evaluation implementation plan

**Goal:** Make privacy protection and actual LLM comprehension repeatable, separate measurements before testing accuracy candidates.

**Architecture:** A packaged, versioned synthetic corpus feeds the real HTTP gateway connected only to a loopback echo provider. Reports retain captured outbound payloads and separate leakage, overmasking, restoration and execution results. A second, explicitly enabled suite creates shuffled opaque jobs for original / human masking / baseline / candidate inputs. Fresh interpretation workers answer before separate grading workers receive gold criteria. External worker JSON and prepared-job import support native agent orchestration without pretending unit tests measure LLM understanding.

**Tech stack:** Existing Python >=3.10, Click, stdlib HTTP/subprocess/JSON; no new runtime dependencies.

**Spec:** https://github.com/mj10612/SecureGateway/issues/308 (including mandatory actual independent subagent evaluation).

## Constraints and definitions

- Never improve the masking engine in this change or inject corpus gold labels as engine knowledge. Only explicitly declared forced policies may be configured.
- Protection accuracy = fully protected annotated sensitive occurrences / all annotated occurrences. Report full and meaningful-fragment leakage separately and request-level leakage. Count execution failures as unmeasured, never protected successes.
- Overmasking = annotated public occurrences absent from their corresponding outbound field / all measured public occurrences; this is not comprehension.
- Comprehension = passed rubric criteria / all scheduled criteria, plus intent and all-required request counts; missing responses/grades remain in denominators and are separately counted. Do not aggregate the two quality axes.
- Same template groups cannot straddle development/holdout. Packaged materials are synthetic and versioned. Profiles select fixed subsets; reports expose case IDs and hashes.
- Capture actual gateway HTTP traffic. Restore echo responses, replay, session separation and snapshot restart separately. Flag dictionary toggles (#307) unavailable until implemented; no fabricated On/Off evidence.
- Actual LLM calls require --real-llm; no fallback provider. Bound calls, output tokens and wall time. Original and rubric are never interpreter input except the explicit original control; criteria are only delivered to graders after the actual first response is stored.
- Report versions, code SHA, environment, corpus/settings hashes, timing, errors and coverage limits. Compare only compatible reports; new leaks and comprehension regressions are separate outputs.
- v2.5.0 minor bump in pyproject, __init__, local uv.lock and current README references in the same final commit. Historical version references stay unchanged.
- Work in existing clean checkout; user explicitly requested commit and push. One release commit includes the implementation, tests, definitions and version.

## Tasks

- [x] Corpus and validation: ko/en across four domains, source offsets, public spans, meaningful partial probes and explicit-vs-contextual policy. Validate malformed/out-of-range spans, duplicate IDs and split leakage before any execution.
- [x] Privacy suite: real isolated loopback gateway/provider; per-case outbound captures; exact echo restoration and replay; session/snapshot invariants; bounded execution; atomic JSON and Markdown reports with unmeasured LLM state. Test known full/partial leakage and failed requests without false success.
- [x] Comprehension: opaque shuffled jobs, four arms, persisted-first responses, importable native subagent results and bounded executable worker; independent grading validation. Test missing/forged IDs, malformed grades, budget exhaustion and incompatible comparison.
- [x] CLI and automation: evaluate privacy/comprehension, prepare/import, compare; offline CI only. Add usage and metric/holdout/runner/isolation documentation. Test opt-in, report artifacts and nonzero regression exit status.
- [x] Execute fresh actual LLM subagents on the smoke task, independently grade their real responses, preserve auditable synthetic evidence and limitations. This does not claim evaluation of native client integrations or 17 languages.
- [x] Full pytest, Ruff, mypy, build/package smoke, CLI/MCP/metadata version checks; independent review; final fixes; commit/push and issue #308 implementation/results comment.

## Review focus

- Missing/failed requests and ungraded answers must not become successful privacy/comprehension samples.
- Partial/repeated secrets and private user keys must be inspected in final outbound traffic; source field paths can change under masking.
- Worker stdin/workspace must not contain original/gold labels for masked arms, nor inherit parent agent history.
- Candidate/baseline comparisons must reject incompatible corpus/case/model/policy settings and account for repeated trials at request level.
- Worker timeout/output overflow and interruptions must retain partial artifacts, close loopback servers and stop descendant processes.

## Review and verification record

- Initial repository baseline: 4033 passed, 441 skipped.
- Final focused suite: 65 passed, including automatic-worker phase/budget, exact alias-provenance and unchanged-mapping regressions. These fixture tests validate the harness, not LLM understanding.
- Fresh independent review found six Important items: ambiguous repeated-word alignment, omitted integrity regressions, incompatible report metadata/output budgets, ignored explicit resume settings, unknown token accounting after rejected inference, and stale current-version documentation. All were addressed; behavioral regressions were observed failing before their fixes.
- Native actual LLM run: four fresh interpreters, then four separate fresh graders; one synthetic task, four arms, 16/16 criteria, baseline/candidate identical engine. Exact inherited model/version and token usage unavailable; no broad accuracy claim.
- Release HTTP corpus: 57/66 protected, nine exposures, 30/117 public spans overmasked; exact restore31/32 with JSON whitespace-only mismatch, semantic restore32/32, replay32/32, isolation/restart passed.
- Ruff and mypy pass. Version2.5.0 verified across package metadata, uv.lock, CLI and MCP. Wheel/sdist independently installed and verified with bundled corpus.
- Full coverage run and final commit/push verification recorded in issue #308 after completion.

- Full project coverage command: 4095 passed, 441 skipped, 89.47% coverage (threshold85%). The final focused65 run includes three added regression cases after that full collection. No masking-engine behavior changed.
- Exact alias provenance now disambiguates identical private/public words where source reconstruction succeeds; fallback ambiguity remains conservative. Unchanged original/alias spellings never count as protection.
