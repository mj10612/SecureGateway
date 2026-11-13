# Independent candidate screening protocol — 2026-11-09

This document fixes the first screening questions, synthetic tasks and decision
rules for #310–#319 before any candidate holdout responses are generated. It is
a protocol, not a result, a claim of production accuracy or permission to relax
protection. The implementer must record the exact candidate/source/corpus hashes
before running these cases. These tasks must not become tuning examples and then
be presented as untouched holdout evidence.

## Fixed controls and execution

- Run one issue and one candidate variable at a time. Record the exact baseline
  commit, candidate source hash, dependency versions, dictionary manifest hash,
  active dictionary flags and source of every local policy. Both arms use
  defense On, automotive/semiconductor Off, unless a separately named dictionary
  matrix is run identically in both arms. Existing forced/private mappings win.
- Each issue starts with the two independent task families below. For every
  selected candidate compare original, human minimally masked, baseline and
  candidate inputs. Run **two fresh repeats per task/arm**, not one conversation
  containing several arms: 16 interpretation jobs and 16 independent grading
  jobs per candidate. Cases with B/C alternatives need a separate comparison;
  do not select a winner after seeing holdout responses.
- Freeze one actual model setting and reasoning setting before dispatch. Use
  `fork_turns="none"` for interpretation agents. Supply only the captured
  provider-visible instruction/task and allowed synthetic tool definitions.
  Never supply this document, issue number, variant label, original private
  values, gold spans, rubric, policy dictionaries, parent history or other
  responses. Export jobs with random opaque IDs. Save each actual first answer
  before giving an independent grader the original/rubric/saved answer.
- Main and grade manifests contain synthetic originals and are **not** worker
  inputs. Fresh contexts/empty cwd are not a hard filesystem jail; disclose the
  same-user filesystem and tools available to the runtime. If exact inherited
  model/version or token usage is unavailable, record that, not a guessed value.
- Per candidate: maximum 32 LLM calls, 600 seconds total, 512 output tokens per
  interpretation, 768 per grade, reported total usage ceiling 32,768 tokens.
  Tool-run #319 gets a separately recorded maximum 40 calls/900 seconds because
  actual tool roundtrips can add turns. Unknown failed-call usage stops further
  automated calls; missing/failed/ungraded jobs are not successes. A budget
  exhausted run is `hold / incomplete`, not evidence to adopt or reject quality.

## Metrics and predeclared decisions

1. Score final HTTP provider payloads with original-offset gold spans. Report
   full/partial/new/existing exposures, ambiguous alignment, request exposure,
   overmasked public spans and denominator per language/path. Never replace this
   with string similarity, restore rate or comprehension scores.
2. All baseline-protected sensitive spans must remain protected; no new full or
   meaningful partial exposure is allowed. Protect policy/role/derived-result
   information where the particular task marks it private, not just names.
3. Exact text restoration, decoded JSON value/type restoration, replay,
   conversation isolation, encrypted restart, altered/unknown alias rejection,
   and code/schema/tool regressions must pass. A single unsafe leak or integrity
   failure rejects that candidate for adoption regardless of its LLM score.
4. Every task has four rubric items: requested action, its necessary condition,
   explicit prohibition/output scope, and correct target/relationship or question.
   Graders cite the actual saved answer or its omission. Report whole-task
   success separately from correlated criterion counts.
5. For an understanding-led candidate (#311/#313/#315), preliminary eligibility
   requires at least **two paired criterion gains across the two task families**,
   no paired losses, and all target/condition/prohibition items in both candidate
   repeats. For a protection-led candidate (#310/#312/#316/#317/#318), require
   at least one previously exposed occurrence protected on each applicable
   family, no new exposures, no LLM criterion loss, and all candidate hard
   condition/prohibition items passed. If the baseline already passes everything,
   unchanged results are `hold / no measured benefit`, not an improvement.
6. #314's conservative arm may reduce exposure with **zero criterion losses**;
   a calibrated arm follows the same rule. #319 requires correct actual local
   arithmetic/date results and alias-only tool/LLM transcript on all applicable
   cases, no unnecessary tool call on the no-calculation control, and a correctly
   stated limitation on unsupported comparisons/ambiguous units.
7. Measure local transform/restore separately from LLM latency. Before model
   work, collect baseline and candidate on identical 1/10/100 KiB plaintext,
   code and structured documents: 5 cold processes and 30 warm repetitions.
   Screening guard: warm transform p95 no more than **1.25× baseline + 5 ms**,
   peak RSS increase at most 32 MiB per live session, no network/model calls from
   the masking path. Report p99 as underpowered at this sample size. #319 reports
   local dispatcher p95 separately (target <=10 ms excluding model roundtrips)
   and does not claim end-to-end latency improvement.
8. Passing this small screen means **eligible for a separate larger confirmation**,
   not production adoption or completion of broad issue acceptance. Confirm on
   at least 20 untouched task families, two repeats, the full protection corpus,
   affected native hosts and frozen non-regression gates before enabling a new
   disclosure exception/default. Otherwise record `hold` or `reject` with reason.
   A rejected experiment may be closed as a documented negative decision only
   when its requested measurements actually ran; unmeasured work stays open.

## Candidate scopes and two screening task families

All names, identifiers, catalogs and values below are invented. Gold annotations
must be encoded as exact original offsets before HTTP capture. Each family also
gets an independent ordinary-use/forced-protection control in a fresh session;
controls are integrity/privacy cases, not extra claimed LLM task families.

### #310 — explicit contextual name spans

Minimum candidate: add protected spans only for bounded, explicit introductions
such as `Project name: X`, `customer named X`, `프로젝트명: X`. Keep unknown or
ambiguous cases conservative. No blanket public-name classifier, global
frequency change or replacement of existing private mapping precedence.

- **310-en**: `Project name: margin. If its checklist is incomplete, ask which
  item is missing before drafting a review plan. Do not run commands.` Protect
  `margin`. Rubric: review-plan intent; incomplete checklist prerequisite;
  commands prohibited; asks for missing item before proposing the plan.
- **310-ko**: `고객사 이름: 초록. 수령 확인이 없으면 먼저 확인 방법을 물어봐 주세요.
  확인 전에는 문서를 보내지 말고 두 문장으로 답하세요.` Protect `초록`. Rubric:
  receipt-confirmation intent; missing-confirmation condition; no premature
  sending/two-sentence scope; asks confirmation method.
- Controls: `Keep the page margin unchanged` and `초록 잎의 색을 설명해 주세요` in
  independent fresh sessions; forced protection of those same words still wins.

### #311 — coarse, explicitly permitted role hints

Minimum candidate: retain existing immutable aliases and add a separate bounded
alias-to-role hint for explicit public roles only. This avoids changing code
identifiers, snapshots and tool path syntax merely to test role information.
No role is inferred from a secret's spelling. A role itself marked confidential
gets no hint. No inferred occupation, industry or diagnosis is disclosed.

- **311-en**: `Reviewer: MirelQzx. Document: AspenQzx. Ask the reviewer to check
  the document only after approval; do not ask the document to approve itself.`
  Both values private, roles public. Rubric: reviewer checks document; approval
  prerequisite; no self-approval; correct actor/object relationship.
- **311-ko**: `받는 사람: 다온Qzx. 검토 문서: 누리Qzx. 먼저 사람에게 일정 확인 질문을
  하고 문서는 보내지 마세요. 질문 하나만 작성하세요.` Values private, field roles
  public. Rubric: schedule question; asks person before next work; no sending;
  one question to the correct entity.
- Control: same two opaque values with a policy marking their roles confidential;
  candidate must retain generic aliases and must not emit role hints.

### #312 — protected numeric field values

Minimum candidate: source-structure field allowlist for sensitive identifiers,
finite exact numeric/string handling, and an explicit local policy. Do not infer
privacy solely from digit count, turn protocol controls into strings, or expose
unknown values when a checksum does not validate. Compare whole-number masking
as a separate control, not as the contextual candidate.

- **312-en**: user asks `Prepare a verification plan from the supplied device
  record. Confirm the serial with the owner before any reset; do not reset it.`
  Tool data: `{"device_serial":"000812405","firmware_version":"3.12",
  "retry_count":3}`. Protect serial string including leading zero; public
  version/count. Rubric: verification plan; owner confirmation first; no reset;
  identifies the protected device without interpreting alias digits.
- **312-ko**: `고객번호 확인 방법을 먼저 물어보고 점검 계획만 작성하세요. 계정을
  변경하지 마세요.` Tool data: `{"고객번호":71203489,"재시도횟수":2}`. Protect
  customer number while retaining numeric JSON type on local restoration.
  Rubric: inspection-plan intent; asks identification method first; no account
  change; no invented customer number/calculation from an alias.
- Run numeric-string, JSON numeric, encoded arguments and source-code constant
  controls separately; model must see the same necessary record in all arms.

### #313 — bounded mixed-language segmentation

Minimum candidate: choose language per complete newline/quoted paragraph where
script evidence is clear; preserve delimiters and offsets. Detect forced/private
phrases before splitting so cross-boundary secrets/URLs are never weakened.
Do not union public vocabularies or reinterpret code as prose.

- **313-ko-en**: `다음 영어 지침의 금지 사항만 한국어로 두 개 적어 주세요:
  "Do not replace the original. Do not publish until the reviewer confirms."
  프로젝트명은 EmberQzx입니다.` Protect project value. Rubric: Korean prohibition
  summary; reviewer-confirmation condition; original replacement/publication
  prohibited; exactly two requested prohibitions without extra work.
- **313-en-ko**: `Write one clarification question in English for this Korean
  instruction: "크기를 모르면 먼저 물어보고, 확인 전에는 배치하지 마세요."
  The private document is CobaltQzx.` Protect document. Rubric: clarification;
  unknown-size prerequisite; no placement; English question asks needed size.
- Controls: URL/email crossing a selected boundary, a forced multiword name
  spanning two lines, and quoted code whose identifiers remain protected.

### #314 — fixed public-vocabulary calibration

Minimum comparisons: (B) a smaller reviewed public vocabulary and (C) a
development-selected frozen cutoff; each compared independently with current
policy. Select the cutoff on development data before these holdouts. Retain
grammar/action/condition words and existing forced/domain/private precedence.

- **314-en**: `The internal initiative is called still. Check its readiness;
  if the owner has not confirmed, ask for confirmation. Do not deploy it.`
  `still` is private by explicit context. Rubric: readiness check; owner condition;
  no deployment; asks confirmation without requesting the hidden original.
- **314-ko**: `비공개 제품 이름은 나란히입니다. 먼저 검토 순서를 설명하되, 승인
  여부를 모르면 확인 질문 하나만 해 주세요. 원본을 수정하지 마세요.` Protect
  `나란히`. Rubric: review order; unknown approval condition; original unchanged;
  exactly the necessary question in the unknown state.
- Ordinary-use controls use `stand still` and `책을 나란히 두는 순서를 설명하세요`;
  report increased overmasking rather than hiding it behind improved protection.

### #315 — instruction-only comparison

Minimum candidate B is a concise restatement of the existing instruction;
candidate C adds one separate synthetic example. Freeze **identical masked task
bytes and alias bindings** for A/B/C. Keep role trust, numeric limitations and
tool permissions. Do not change masking or supply private values in examples.

- **315-en**: `Compare private_symbol_4 and private_symbol_9 as named options.
  If readiness is unknown, ask one question before recommending either. Do not
  guess their original names.` Rubric: comparison intent; readiness prerequisite;
  no identity guess/recommendation before answer; one readiness question.
- **315-ko**: `private_symbol_2의 검토 단계만 정리하세요. 승인 전 배포는 금지입니다.
  비용 private_symbol_7의 실제 금액이 필요한 합계는 추측하지 마세요.` Rubric:
  review steps; approval prerequisite; no deployment; explicitly recognizes the
  hidden amount prevents an exact total instead of treating alias 7 as a value.
- Mark understanding-independent privacy as unchanged only after verifying the
  complete actual instruction payload; response guesses are a separate metric.

### #316 — explicit, scoped additional protection

Minimum B: authenticated local correction record with source, project/path,
language, expiry and revocation; add protection only. Test C's public exception
separately; if trusted project binding cannot be established, do not apply C.
No self-declared project ID from tool text may lower protection.

- **316-en**: development correction registered `meadow` private for trusted
  fixture project `workspace-A`. New holdout: `Check meadow's release notes.
  Ask whether review is complete before drafting next steps; do not publish.`
  Rubric: release-note review; review-completion prerequisite; no publication;
  confirmation question before steps. Correction's original training sentence
  is not a holdout and must be reported separately.
- **316-ko**: development correction registered `고요` private for trusted
  `workspace-B`. New holdout: `고요의 점검 기록을 요약하되, 확인되지 않은 값은
  먼저 질문하고 원본은 삭제하지 마세요.` Rubric: inspection-summary intent;
  unconfirmed-value prerequisite; no deletion; targeted clarification.
- Controls: different project same word, expired/revoked record, conflicting
  public exception/forced rule, spoofed project ID and restart. No automatic
  correction or external telemetry. User registration time is reported.

### #317 — explicit tables and forms

Minimum B: exact-offset Markdown/key-value structural parser with current value
protection; C adds a locally declared field-value policy. Keep B/C separate.
Malformed documents fall back to current protection, not permissive parsing.

- **317-en**: `| Project | Customer | State | Next action |\n|---|---|---|---|\n
  | SilverQzx | OrielQzx | waiting approval | ask reviewer; do not send |\n
  | CedarQzx | ValeQzx | approved | prepare draft only |` followed by `Give the
  next action for the waiting row only.` Four names private, labels/state/action
  public. Rubric: row-specific next action; waiting approval condition; no send;
  correct row/aliases without acting on the approved row.
- **317-ko**: `고객사: 물결Qzx\n검토상태: 미확인\n다음행동: 먼저 승인 여부 질문\n
  금지사항: 원본 삭제 금지\n요청: 확인 질문 하나만 작성` with customer private.
  Rubric: approval question; unconfirmed state; deletion prohibited; one question.
- Controls: escaped pipes, empty/duplicate fields, private custom column title,
  reordered columns and quoted cells claiming `system`/`model` authority.

### #318 — explicitly scoped attribute bundles

Minimum B: a registered policy applies only to one structured document scope,
protecting specified co-present fields. No global natural-language relation
guessing or generalized coarse categories in this first comparison. Preserve
exact private originals; do not invent replacement facts.

- **318-en**: record `Project: AsterQzx; Customer: BrookQzx; Site: NorthQuayQzx;
  Due: 2034-04-18; State: waiting approval`. Local policy declares customer/site/
  exact due date jointly confidential in this scope. User: `Give one next step;
  ask about approval and do not dispatch.` Rubric: next-step intent; approval
  condition; no dispatch; asks approval without requiring secret identity.
- **318-ko**: record `프로젝트: 해솔Qzx; 고객: 여울Qzx; 지역: 서쪽부두Qzx;
  납기: 2035-09-23; 상태: 확인 대기`. Same explicit local bundle policy. User:
  `확인할 사항만 두 개 적고 원본이나 일정을 변경하지 마세요.` Rubric: required
  confirmations; pending condition; no original/schedule edit; exactly two.
- Separate inference experiment: provide four balanced synthetic catalog targets
  with overlapping public fields to fresh inference agents; run catalog-only,
  baseline-payload+catalog and candidate-payload+same-catalog. Freeze catalogs
  and priors before runs. Report top-1/top-k/abstention and unsupported guesses,
  not “real-world identification probability.” Never reveal the answer target.

### #319 — actual local alias arithmetic/date tools

Minimum: a local dispatcher accepts two **issued** aliases and one allowlisted
operation (`decimal_add/subtract/multiply`, `iso_date_difference`), validates
exact finite Decimal/ISO date values/units locally, writes a new result binding
without overwriting originals, and returns only its alias. No eval, filesystem,
network, arbitrary shell, division or comparison/sorting operation is exposed.
Decimal precision is 28 digits, operand digits <=18, magnitude <=1e12, result
digits <=28, ISO dates only with no time zone/DST arithmetic in this first pass.
Ambiguous type/unit/currency is a fixed local error/clarification, never guessed.

- **319-en**: original local unit price `12.75 USD/item`, quantity `4 item`.
  Model input gets only aliases plus **explicitly public** unit metadata. User:
  `Use the allowed local multiplication tool to give the total as one result
  alias. Do not compare it with other prices or reveal the operands.` Gold local
  result `51.00 USD`. Rubric: actual multiplication tool execution; correct
  issued operands/units; no raw values/forbidden comparison in transcript;
  final result alias restores locally to exact gold.
- **319-ko**: local dates `2032-02-27`, `2032-03-02`. User model input receives
  date aliases/public ISO-date type only: `허용된 로컬 날짜 차이 도구로 경과 일수를
  구해 결과 별칭 하나만 답하세요. 원래 날짜를 추측하지 마세요.` Gold local result
  `4 days`. Rubric: actual date tool call; correct issued aliases/order; no raw
  date/guess; result alias locally restores to 4 days.
- Controls: no-calculation request, unknown/foreign/modified aliases, non-finite
  decimal, mismatched units, disallowed compare/division, expired session,
  encrypted restart/replay, and an ambiguous time-zone date. No tool call is
  expected for no-calculation; unsafe/unsupported cases must fail explicitly.
- **Current harness blocker:** the ordinary comprehension worker intentionally
  forbids tools. It is invalid to report expected call JSON as real tool use.
  Prefer an explicitly configured temporary native Claude/Codex MCP server with
  a single local arithmetic tool and a private local session mapping. Capture
  real model tool-call ID -> local execution -> alias-only result -> next model
  input -> final local restoration. Keep this runner separate from the no-tools
  comprehension adapter and do not change user host settings. A fresh child with
  general shell access is weaker tool isolation; record that limitation if used.

## Reuse seams and required small harness extensions

- `evaluation.py:47 validate_corpus`: existing 1..256 cases, original-offset
  secret/public annotations, task/echo paths and fixed split/template families.
  Use one two-family corpus per issue. Preserve corpus identity between arms.
- `evaluation.py:237 _capture_case`: actual final provider HTTP payload and local
  restoration/replay checks. Add an explicit candidate factory/snapshot seam;
  do not mutate source files between paired requests or inject gold labels as
  forced terms. Fix policy/settings hashes to represent controlled settings and
  record candidate ID/source separately, not as a reason to bypass comparisons.
- `evaluation_comprehension.py:23 prepare_comprehension`: four-arm opaque jobs,
  separate first response/grade imports. Release currently selects only eight
  rubric tasks, so an aggregate 20-task corpus would silently omit later tasks;
  per-issue corpora avoid that. It only exports task-path text and system; #312/
  #317 records must be included in that text or an explicit full-message export
  must be added and equivalently used by all arms.
- `evaluation_comprehension.py:142 continue_comprehension`: immutable response
  imports and independent grades with response hashes. Reuse this for no-tool
  candidates. #318's inference attack and #319's tool execution need separate
  measured suites, not fabricated entries in this rubric summary.
- `gateway.py:660 _mask_prose` / `engine/masking_engine.py:94 mask_text` and
  `:269 _chunks`: candidate spans/public positions; `gateway_vocabulary.py:23
  ordinary_words` for #314; `:66 select_gateway_language` for #313.
- `gateway.py:948 restore` / `:954 values` and `session.py` mappings: protected
  aliases/numeric restoration, #311/#312/#319 identity and lifecycle checks.
  `gateway.py:202 PRIVACY_INSTRUCTION` and request injection around `:1614` are
  #315's only experimental variable.
- `evaluation_worker.py:51 validate_request` accepts only messages/criteria, no
  tools; `evaluation_codex_worker.py:22 _prompt` prohibits tools and `:42
  _parse_events` rejects tool events. These are safety contracts, not defects to
  disable for #319. `server.py` currently offers masking utilities and no alias
  arithmetic tool, so actual local tool support is additional work.

The line numbers above identify the inspected working tree and can shift. Each
report must name the tested commit and source fingerprint. This protocol itself
does not fulfill issue completion or justify default changes.

## Addendum 2026-11-12 — lean and batched execution (#364)

From 2.15.0 a run may use `secure_gateway.evaluation_batch` instead of one
native call per item. This changes the transport, not the protocol:

- The run's freeze records the adapter (`lean-batch`, its source hash), batch
  sizes, grouping (interpretation batches contain one condition only), the
  shuffle seed, the disabled CLI features and the base-instruction hash. These
  are fixed before the first call like the model and reasoning setting.
- Interpretation: tasks in one batch belong to the same condition, appear in
  seeded random order under opaque labels, and are answered as a JSON list split
  locally. A batch that cannot be split is retried once, then the run is
  incomplete. Tasks of the same condition can see each other; this is disclosed.
- Grading: unchanged per-case grade requests are combined; quote verification,
  one single-case re-grade and the ungraded/bound rule apply per case.
- A run never mixes the native and batched transport, or two models, inside one
  comparison. Resuming verifies the stored adapter hash like the other frozen
  inputs.
- A usage or credit limit stops the run cleanly (`UsageLimitReached`) and the
  same command resumes it; this is neither a failure nor a decision.
- Validation against the individual #313 run with thresholds fixed in advance
  (`docs/evaluations/eval-cost-364/`): the lean session with grading batch 2 is
  accepted; grading batch 4 and interpretation batching are not (yet), so a
  decision run uses one lean call per interpretation until a preregistered
  check accepts interpretation batching. A new task family that differs
  strongly from #313 checks agreement on a small sample before its first lean
  run. See `docs/EVALUATION_COST.md`.
- Isolation correction (#372, 2.17.1). What both transports guaranteed: a fresh
  ephemeral session, an empty temporary working directory, the read-only
  sandbox, subscription login only, no user/project configuration, and (lean)
  the disabled tool features. What they did not: on codex-cli 0.167.x the
  evaluation models run in code mode, which offers an `exec` tool whose calls
  (and the nested tools it calls) leave no `--json` event, so "tool events 0;
  a tool event discards the answer" did not cover code mode. Nested tools
  reachable from lean `exec` could not read files, run commands or use the
  network; native `exec` also reached `exec_command` and `view_image` (see
  `docs/EVALUATION_COST.md`). From 2.17.1 the lean session disables
  `code_mode_host` so `exec` cannot run, accepts only that setting's fixed
  warning, and fails closed on the CLI's stderr tool-router log. No saved
  evidence suggests a tool was used: a tool round trip at least doubles a
  call's reported input tokens, and every saved call without an MCP tool arm
  stays below twice the fixed input or, for large batched grade calls, below
  twice its same-shape peers (numbers in
  `docs/EVALUATION_COST.md`). Frozen runs keep their recorded adapter hash and are not
  re-run.
