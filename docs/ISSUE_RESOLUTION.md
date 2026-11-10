# Issue review and resolution (0.2.0)

## Host expansion follow-up (2026-10-07)

| Issue | Implemented evidence | Remaining boundary |
| --- | --- | --- |
| [#67](https://github.com/mj10612/SecureGateway/issues/67) | Versioned host/OS/auth/cost/scope table; shared Claude/Codex/xAI contract checks actual reads, bilingual aliases, schemas, split SSE, status codes, refreshed credentials and isolated encrypted state; offline suite runs in CI | Unverified hosts remain explicit candidates; live inference is opt-in |
| [#66](https://github.com/mj10612/SecureGateway/issues/66) | Separate API install/run/uninstall, fixed xAI origin, original settings/login preservation, token/state/auth isolation; actual Grok 1.0.46 English/Korean file-read and split SSE fixtures; API control leakage and model-collision regression coverage | Live paid API checks require separate opt-in; browser subscription reuse is unverified and unsupported |
| [#65](https://github.com/mj10612/SecureGateway/issues/65) | Actual Antigravity CLI 1.3.0 stdio config, conflict/preservation/space-path tests, initialize/list/tools handshake; SDK 0.1.21 actual bilingual file reads through a context-owned authenticated xAI bridge, masked provider payloads and restored tools/answers | Explicit xAI API billing only; IDE/CLI subscription redirection remains unverified |

See [compatibility](COMPATIBILITY.md), [Antigravity](ANTIGRAVITY.md), and
[Grok/xAI](GROK.md) for setup and exact verification scope. These records describe
local implementation and evidence; they do not imply that GitHub issues were closed.

## Original masking issue resolution

All 55 issues were reviewed against the code. Previously resolved #1–8 retain regression
coverage, adjusted where the safer 0.2 API deliberately changes representations or the MCP
trust boundary. The 47 remaining reports are covered by these changes and tests.

| Issues | Change | Evidence in tests |
| --- | --- | --- |
| #9, #11 | Sensitive code spans and URLs are atomic entities, including entities_only. | `test_sensitive_spans_mask_as_one_unit_and_restore` |
| #10, #15, #22, #45 | Delimited random pseudowords, consistent alphabetic allocation, no ordinary-word scanning or adjacency ambiguity. | `test_pseudowords_never_rewrite_ordinary_names_and_report_only_delimited_candidates`, `test_numeric_units_roundtrip` |
| #12 | Aggressive uses a smaller structural subset and masks auxiliaries/adverbs/pronouns. | `test_aggressive_masks_auxiliaries_and_function_adverbs` |
| #13, #14, #16, #48, #49 | Bounded validated TTL, duplicate creation errors, last-used mode, public locked counts, invalid policy errors. | `test_invalid_ttl_is_rejected`, `test_duplicate_creation_does_not_mutate_live_session`, `test_invalid_policy_fails_before_allocating_session` |
| #17, #26 | Unicode text words and code identifiers remain atomic and are masked. | `test_unicode_tokenizer_keeps_words_atomic`, `test_language_literals_and_identifiers_do_not_leak` |
| #18 | Only a terminal possessive suffix is detached; apostrophes inside names are private. | `test_sensitive_spans_mask_as_one_unit_and_restore` |
| #19, #34, #51 | UUID/IP/phone spans are recognized before number/word splitting; classifier patterns share their definitions. | `test_sensitive_spans_mask_as_one_unit_and_restore` |
| #20, #25, #31, #38 | Language-specific literals/comments: backticks, raw delimiters, SQL escaping, multiline/nested strings and complete numeric forms. Malformed boundaries fail closed. | `test_language_literals_and_identifiers_do_not_leak`, `test_unterminated_literals_fail_closed`, `test_raw_braces_and_rust_lifetimes_are_supported` |
| #21 | Conservative Korean non-function-word masking in entities_only plus explicit sensitive terms. | Korean cases in `test_sensitive_spans_mask_as_one_unit_and_restore`, `test_bilingual_matrix` |
| #23, #36, #50 | Periodic idle cleanup; shared operation lock; purge waits and invalidates retained objects. Custom store writes require the operation context. | `test_idle_expiration_releases_mapping_references_without_a_read`, `test_concurrent_masks_preserve_bijection_and_counts`, `test_clear_waits_for_inflight_mask_and_prevents_post_purge_writes` |
| #24 | Trusted LocalPrivacyClient before provider calls; no model-invoked restoration tools; CLI network transports refused; confidentiality claims corrected. | `test_model_cannot_call_restoration_oracle`, `test_trusted_client_only_sends_masked_data_and_clears_on_provider_failure` |
| #27 | Shared secret prefix/JWT and conservative long mixed-case token detection; explicit terms for unknown formats. | Credential cases in `test_sensitive_spans_mask_as_one_unit_and_restore` |
| #28 | Random 96-bit hash nonces independent of public salts and originals. | `test_hash_nonces_are_independent_of_original_and_public_salt` |
| #29, #33 | Single-syllable suffixes require stem evidence; bare/ambiguous nouns and names stay whole. | `test_ambiguous_korean_bare_nouns_are_not_truncated` |
| #30, #32 | Latin stems keep attached Korean particles; opt-in generated-response allomorph normalization. Exact roundtrips keep original particles. | `test_known_and_alphanumeric_korean_stems_keep_particles`, `test_generated_response_particle_normalization_is_explicit` |
| #35, #37, #41 | Language-specific keyword tables, missing core keywords, builtin/user-name masking, contextual Python keywords. | `test_core_keywords_preserved_per_language`, `test_language_literals_and_identifiers_do_not_leak`, `test_python_floor_division_and_contextual_keywords_preserve_syntax` |
| #39, #47 | Examples/demo use actual masked payloads; mocked echo outputs restore the correct clinical facts and Korean amounts. No fabricated response IDs. | `test_examples_restore_correct_facts`, `test_cli_demo_uses_actual_allocations` |
| #40 | ASCII code names and literal contents; native numeric nonce constants. Review syntax is preserved while execution/types remain opaque. | `test_repository_python_code_is_parseable_after_masking`, `test_masked_python_numeric_patterns_compile`, `test_all_code_strategies_keep_python_bytes_and_literals_parseable`, `test_javascript_masked_source_passes_native_syntax_check` |
| #42 | Unicode punctuation and symbols, hyphens and Markdown structure preserved. | `test_punctuation_and_markdown_are_preserved` |
| #43 | Broader candidate scanner reports altered spelling/case/separators; strict restoration rejects unknowns. No unsafe fuzzy reconstruction. | `test_altered_surrogates_are_reported_and_strict_mode_rejects`, `test_empty_reverse_store_still_reports_unknown_tokens` |
| #44, #46 | Type/context-aware mapping keys; sentence-initial proper-name candidates classified consistently. | `test_same_original_gets_distinct_type_and_context_allocations`, existing English entity regression tests |
| #52 | Versioned payloads, persisted allocations without regeneration, legacy read/update support, clear unsupported-version errors, exclusive CLI transaction lock. | `test_schema_version_and_generator_change_do_not_destroy_snapshots`, `test_legacy_pseudoword_snapshot_can_be_read_updated_and_read_again`, `test_cli_file_lock_covers_read_modify_write`, subprocess roundtrip tests |
| #53, #54 | Accurate metric aliases, unique vs occurrence counts, validated requested strategy, exposed preserve/sensitive options, removed unused fields/dead branch and duplicate suffix entries. | `test_metrics_distinguish_occurrences_and_unique_allocations`, `test_explicit_terms_and_preserve_are_available_in_cli_and_mcp`; lint/type checks |
| #55 | CI lint/type checks, warnings as errors, meaningful regression tests and an 85% coverage floor. | `.github/workflows/ci.yml`, `pyproject.toml` |

Tests are in [test_issue_resolution.py](../tests/test_issue_resolution.py) and the existing suite.
The bilingual matrix exercises English, Korean, mixed input, four modes and four strategies.
No live provider was called: callbacks are mocked to verify the trust boundary and facts.

## Limits that remain intentional

This is a heuristic local masker, not universal NER or a full morphological/compiler frontend.
Unrecognized sensitive terms require explicit specification or broader masking. Korean unknown
ambiguous stems are preserved inside their masked whole word. Generated-response particle
correction is opt-in and does not guess foreign pronunciation. Arbitrary model deletions and
inventions cannot be reconstructed. Code output is for review, not execution or type checking.
Legacy bare pseudowords remain readable but retain their historic ambiguity; new sessions use
the safe format. Clearing references is not byte-level zeroization. These limits and migration
changes are documented in the English/Korean README rather than hidden behind absolute claims.

Unrelated sponsorship/marketing proposal content was removed. Generated caches and coverage
artifacts are excluded from the repository; the development environment remains available.


## October 2026 gateway follow-up

| Issues | Result | Regression evidence |
| --- | --- | --- |
| #68 | Empty/whitespace streamed tool argument fragments preserved | test_gateway_followups |
| #69 | Per-provider state locks released across network waits; per-owner cached encryption derivation | test_gateway_runtime, test_snapshot_encryption |
| #70 | Public statuses/codes preserved with sanitized context compaction hints; buffering limits documented | test_gateway_runtime, test_upstream_context_errors |
| #71, #83 | Allocation bound configurable; authenticated idle-provider reset; crash-released OS locks | test_gateway_runtime, test_lock_recovery |
| #72 | Contextual source detection; duplicate traversal cleanup; live-test flags documented | test_gateway_source |
| #73 | Named JSON Schema dependencies share aliases; unsafe regex schemas rejected | test_gateway_followups |
| #74, #79 | Typed controls and request envelopes validated before transformation | test_gateway_validation, test_gateway_followups |
| #75, #76 | Retryable uninstall recovery journal and shared installation lock | test_install_recovery |
| #77, #88 | Truncated health/shutdown response recovery | test_install_validation, test_install_recovery |
| #80 | Contextual C/C++ directives preserved; header delimiters retained with private content masked | test_preprocessor |
| #81 | Explicit multiword sensitive terms keep attached Korean particles and exact restoration | test_sensitive_particles |
| #82 | Validated public query metadata forwarded; unsupported queries rejected | test_gateway_runtime, test_gateway_hosts |
| #84, #89 | Uninstalled operations and malformed manifests handled before mutation | test_install_validation |
| #86 | Lookahead design evaluated with measured baseline; buffering retained to preserve protocol/error contracts | docs/STREAMING.md, test_host_contract |
| #85 | Authenticated bounded xAI model catalog with normalized public fields | test_gateway_catalog |

C/C++ system and custom header **contents** are both masked; angle/quote delimiters and
preprocessor syntax remain intact. Masked source is for model review and is not guaranteed
to compile or resolve headers before restoration. Explicit sensitive-term suffix support
uses the accepted particle vocabulary, not arbitrary Korean substring splitting.


Local acceptance checks (Windows/Python 3.11.15): full warnings-as-errors suite,
coverage gate 85%, Ruff and mypy; optional native offline Claude/Codex/Grok scenarios
6 passed, actual Antigravity SDK 0.1.21 suite 15 passed/1 live skipped. Provider paid/live
calls were not enabled. GitHub cross-platform results are reported separately in issue
comments after pushing. The #86 design review retains buffering and includes measured
performance/memory evidence; it does not claim incremental streaming was implemented.
# Release 0.6.0 review follow-up

The following open issues were rechecked against the released code and addressed together.
Earlier release notes and parser fixtures remain historical records.

| Issues | Resolution and proof |
| --- | --- |
| #105, #107, #108, #128 | Public safety/tool-choice/context tags validated in their protocol positions; custom grammar envelopes pinned completely. `test_batch_gateway` |
| #106, #122, #123, #138–#142 | Language-specific C keywords, JS regex/templates, Python soft keywords/PEP 701, Go/SQL escapes, Rust lifetimes/nested comments. `test_batch_parser` |
| #109 | Already fixed with byte-based constant-time token comparison; non-ASCII regression remains covered by admin tests. |
| #110, #111, #113, #135, #137 | Strict Korean alias detection, relevant mapping lookup, request pinning, nonblocking cleanup, private numeric tails. `test_batch_core` |
| #112, #117, #120, #129–#134, #143–#145, #151, #152 | Safe shutdown/admission, aggregate diagnostics, upstream errors, schema/ref and streaming/numeric restoration. `test_batch_gateway`, `test_batch_interfaces` |
| #114, #124, #125 | Current SDK/lock documentation, compatible asyncio minimum, wheel/sdist CI smoke outside source. `scripts/package_smoke.py` |
| #115, #116, #118, #126, #146, #149 | UTF-8 CLI input, configurable resource budgets, safe snapshot retirement, bounded binary command capture, Windows hook paths. `test_batch_core`, `test_batch_hooks`, `test_batch_exec_capture`, `test_batch_interfaces` |
| #119, #153 | SDK retry/rate headers and anonymous credential filtering through API/UI. `test_batch_interfaces` |
| #121, #127, #136, #147, #148, #150 | Ownership checks, exact Orca synchronized hashes, redirect rejection, validated settings, durable install recovery, completed stop. `test_batch_install`, `test_batch_antigravity_install` |

Character literals (#130) use opaque identifier expressions rather than invalid multi-character
quoted placeholders. Masked code remains a review representation, not executable anonymization.
Unsupported string schema constraints fail before forwarding. Hook GC retires old host IDs rather
than reallocating their aliases, and persistent OS lock files are preserved.

## Issue #302 coverage inventory

The following describes existing repository evidence, not a claim that the
release gate is complete. Entries marked partial retain the named gaps.

| Required automated test | Status | Existing evidence | Unmeasured / gap |
| --- | --- | --- | --- |
| Distribution lifecycle | Partial | `scripts/package_smoke.py`, `.github/workflows/ci.yml` `package`, `native-release` | Windows / Python 3.14.3: wheel and sdist pass installed-daemon tool roundtrips and upgrade from v2.4.0 source; the tracked daemon PID exits after stop and uninstall. Descendant-process termination, real-home invariance and other OSes remain 미측정. |
| Install failure atomicity | Partial | `tests/test_install_startup_transaction.py`, `tests/test_install_validation.py` | Invalid config and each failure need the full unchanged-state, no-child and retry proof. |
| Uninstall/recovery | Partial | `tests/test_gateway_selective_uninstall.py`, `tests/test_install_recovery.py` | Actual forced termination, corrupt/missing JSON and symlink preservation require full matrix proof. |
| Native offline compatibility | Partial | `tests/test_gateway_hosts.py`, `scripts/package_smoke.py`, `native-release` | Four native cases are required with no skips, but release-commit cross-platform results remain 미측정 until CI runs. |
| Long inference/concurrency | Partial | `tests/test_gateway_connection_close.py`, `tests/test_gateway_admin.py` | Silent slow SSE, concurrent conversation tool calls, retry and at least five-second active shutdown timing remain 미측정. |
| Conversation compatibility | Partial | `tests/test_gateway.py`, `tests/test_gateway_validation.py`, `tests/test_gateway_error_codes.py` | Existing conversation migration and full attachment/header compatibility remain 미측정. |
| Tool integrity | Partial | `tests/test_gateway_json_numbers.py`, `tests/test_host_contract.py`, `tests/test_gateway_lifecycle_12.py` | Full private-symbol prefix/suffix mutation and cross-platform path matrix remain 미측정. |
| Optional model | Partial | `tests/test_model_download_recovery.py`, `tests/test_context_model.py` | Separate CI job and real pinned model independent corpus remain 미측정. |

Manual subscription runs: **수동 확인 필요 — 미실행**; see
[release checklist](RELEASE_CHECKLIST.md).


## Experiments: Structure, Numbers, Instructions, Arithmetic (#312, #315, #317, #319 — v2.9.0)

Under the experimental umbrella protocol (`docs/EXPERIMENT_PROTOCOL_20261109.md`), issues #312, #315, #317, and #319 were implemented behind isolated candidate profile toggles (default OFF). Baseline engine output remains 100% byte-identical to base commit `146babd` when toggles are not active.

### Status and Decision Table

| Issue | Candidate | Profile / Toggle | Implemented Module | Status | Acceptance Bullets (Done / Not Done) | Evidence Directory | Toggle-Off Byte Identity | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| #312 | `numeric_context` (C)<br>*(B: mask all numbers control)* | `312` / `"numeric_context"` | `src/secure_gateway/numeric_context.py` | **부분 완료** | **Done:** Formats (Luhn, Korean RRN, Biz num), JSON key path sensitive detection, exact type/sign/leading-zero restore, protocol number exclusion, toggle-off byte-identity, evidence directory, decision entry.<br>**Not Done:** Real-LLM comprehension (미측정). | `docs/evaluations/issue312-2.9.0/` | `tests/test_toggle_off_byte_identity.py` (identical to base 146babd) | **hold — comprehension 미측정** (default OFF) |
| #315 | `instruction_concise` (B)<br>`instruction_examples` (C) | `315` / `"instruction_concise"`, `"instruction_examples"` | `src/secure_gateway/gateway.py` | **부분 완료** | **Done:** Wording replacement for `PRIVACY_INSTRUCTION`, byte-identical masked payloads and aliases asserted, synthetic disjoint examples, token delta measured, toggle-off byte-identity, evidence directory, decision entry.<br>**Not Done:** Real-LLM comprehension (미측정). | `docs/evaluations/issue315-2.9.0/` | `tests/test_instruction_wording.py`, `tests/test_toggle_off_byte_identity.py` | **hold — comprehension 미측정** (default OFF) |
| #317 | `doc_structure` (B: parse only)<br>`doc_structure_policy` (C: + per-field policy) | `317` / `"doc_structure"`, `"doc_structure_policy"` | `src/secure_gateway/structure_parser.py` | **부분 완료** | **Done:** Linear offset-preserving parser, `cells(text)` interface, reviewed public headers, local field policy, safe fallback, user keys never promoted to protocol, toggle-off byte-identity, evidence directory, decision entry.<br>**Not Done:** Real-LLM comprehension (미측정). | `docs/evaluations/issue317-2.9.0/` | `tests/test_structure_parser.py`, `tests/test_toggle_off_byte_identity.py` | **hold — comprehension 미측정** (default OFF) |
| #319 | `local_arithmetic` | `319` / `"local_arithmetic"` | `src/secure_gateway/private_arithmetic.py` | **부분 완료** | **Done:** Gateway dispatcher intercepts `local_alias_arithmetic`, Decimal/Date local math, new alias registration, tool removal from host view, zero leakage in errors/descriptions, user tool collision prevention, snapshot persistence, strict restore, toggle-off byte-identity, evidence directory, decision entry.<br>**Not Done:** Real-interpreter tool execution in LLM (미측정). | `docs/evaluations/issue319-2.9.0/` | `tests/test_local_arithmetic_dispatcher.py`, `tests/test_toggle_off_byte_identity.py` | **hold — comprehension 미측정** (default OFF) |

### Detailed Evaluation and Boundaries

#### #312: Format and field-context sensitive numbers/identifiers
- **Approach:** Protect numbers and identifiers when:
  1. Validated format: Luhn checksum (credit cards, IMEI), Korean Resident Registration Number (RRN) check formula, Korean business registration number 10-digit check digit. A failed checksum never implies public exposure.
  2. Original field name / label in source structure marks it as account, customer, device ID, contact, or credential (via JSON key path, structure parser field names, or adjacent label in prose).
  3. Original field names are strictly read from the original structure, never from aliased text.
- **Restoration:** Exact restoration of sign (negative numbers), leading zeros (e.g. `'000812405'`), precision (fixed decimal places), big integers, and JSON data types (numbers restored as numbers, strings as strings).
- **Protocol Envelopes:** Protocol parameters (e.g., `max_tokens`, `temperature`, `top_p`) are strictly excluded from user data masking.
- **Evidence:** Stored in `docs/evaluations/issue312-2.9.0/`. Protection accuracy maintained with 0 regressions. Warm transform p95 latency under 1.25x baseline. Real-LLM comprehension is recorded as **"미측정"** per protocol because real interpreter calls were not executed in this environment.
- **Status:** **부분 완료**.
- **Decision:** **hold — comprehension 미측정** (toggle default OFF).

#### #315: Masking-instruction wording
- **Approach:** Candidates `instruction_concise` (B) and `instruction_examples` (C) replace only the model-facing `PRIVACY_INSTRUCTION` text at session request dispatch.
- **Equivalence:** Masked payloads and alias bindings are 100% byte-identical across arms A, B, and C, verified deterministically in `tests/test_instruction_wording.py`. Examples in candidate C are synthetic and disjoint from evaluation corpora.
- **Token Delta:** Concise restatement reduces instruction length by ~15 tokens (~58 characters); examples candidate adds ~50 tokens (~193 characters).
- **Evidence:** Stored in `docs/evaluations/issue315-2.9.0/`. Real-LLM comprehension across bilingual task families is recorded as **"미측정"**.
- **Status:** **부분 완료**.
- **Decision:** **hold — comprehension 미측정** (toggle default OFF).

#### #317: Table and form field-vs-value handling
- **Approach:** Implemented a single linear-pass, offset-preserving parser in `src/secure_gateway/structure_parser.py` supporting Markdown tables and `항목: 값` form blocks without rewriting, reordering, or summarizing text.
- **Interface:** Exposes `cells(text) -> [(row, field_name, start, end)]` for future consumption by branch `exp/310-311-316-318-names-policy` (#318) at merge. Limits: 1000 rows, 64 columns, 4096 chars/cell.
- **Policy:** In Candidate B (`doc_structure`), reviewed public headers (`REVIEWED_PUBLIC_FIELDS`) remain public while cell values undergo normal protection. In Candidate C (`doc_structure_policy`), a local field policy maps specific field names to always-mask. Malformed or ambiguous tables safely fall back to the existing path and increment `fallback_count`. User-data keys such as `id`, `type`, `model`, or `system` inside cells are never promoted to protocol exceptions.
- **Evidence:** Stored in `docs/evaluations/issue317-2.9.0/`. Zero new exposures. Warm transform p95 latency meets < 1.25x baseline gate. Real-LLM comprehension is recorded as **"미측정"**.
- **Status:** **부분 완료**.
- **Decision:** **hold — comprehension 미측정** (toggle default OFF).

#### #319: Local arithmetic tool over masked numbers and dates
- **Approach:** Extended `src/secure_gateway/private_arithmetic.py` with `LocalArithmeticDispatcher`. The dispatcher intercepts tool calls named `local_alias_arithmetic` from upstream responses, executes Decimal addition, subtraction, multiplication, and ISO date difference locally without leaking originals or intermediate values, registers the result as a new alias, and returns only the alias to the model.
- **Protocol Contract:** The tool definition is injected into upstream requests only when the profile toggle is active and removed from host-visible responses. If a user defines a conflicting tool named `local_alias_arithmetic`, the dispatcher raises `ValueError` before forwarding.
- **Integrity & Bounds:** Operation allowlist (`decimal_add`, `decimal_subtract`, `decimal_multiply`, `date_difference`), maximum 18 operand digits, 28-digit precision, no `eval`, no network, no filesystem. Unknown, mutated, or foreign-session aliases are strictly rejected. Derived aliases cleanly persist and restore across snapshot serialization and replay.
- **Evidence:** Stored in `docs/evaluations/issue319-2.9.0/`. Dispatcher p95 latency is 0.08 ms (well under the 10.0 ms target). Real-LLM comprehension is recorded as **"미측정"** because ordinary test runners forbid tool execution and native MCP loopback was not active.
- **Status:** **부분 완료**.
- **Decision:** **hold — comprehension 미측정** (toggle default OFF).

## Language-side accuracy experiments (v2.10.0)

Five language-side accuracy issues were evaluated under the experiment protocol (`docs/EXPERIMENT_PROTOCOL_20261109.md`):
hypotheses #309, #313, #314, and umbrellas #306 and #291. All candidates are implemented behind isolated toggles (default OFF);
with all toggles OFF, output is verified byte-identical to the baseline engine.

| Issue | Candidate Profile | Description & Acceptance Status | Decision | Evidence Directory |
| :--- | :--- | :--- | :---: | :--- |
| **#309** | `ko_conjugation_split` | Rule-based Korean ending table (`-면/-으면`, `-기 전에/-ㄴ 뒤에`, `-지 말고/-지 마`, `-세요/-해줘`, `-ㄴ/-은/-된`) keeping grammatical endings public while stem is judged by policy; forced terms mask stem and keep endings; unseen holdout evaluated. | **Hold — comprehension 미측정** (default OFF) | `docs/evaluations/issue309-2.10.0/` |
| **#313** | `segment_language` | Per-sentence/quote/list segment language choice via `detect_natural_language()` evidence; floor inheritance (<8 chars); whole-text protected spans run first so boundaries never cut sensitive/code/forced spans; ko/en only. | **Hold — comprehension 미측정** (default OFF) | `docs/evaluations/issue313-2.10.0/` |
| **#314** | `vocab_calibrated` (C) / `vocab_conservative` (B) | Candidate C: per-language calibrated cutoff chosen on dev data (en: 450, ko: 400), ambiguous name-like words excluded. Candidate B: reviewed public vocabulary only (rejected due to excessive over-masking of unreviewed domain prose). | **Hold — comprehension 미측정** (C, default OFF), **Reject B** | `docs/evaluations/issue314-2.10.0/` |
| **#306** | Umbrella | Delivered sections 3 & 5: character-offset gold spans with separate FN/FP/partial/leak counts; separate denominators per language/domain/target; separate restore/protocol integrity (100%); 4 issue reproductions passing as regression cases. Real-LLM comparison reported as 미측정. Name-context referenced to `exp/310-311-316-318-names-policy`. | **Delivered (Sec 3 & 5)**; comprehension 미측정 | `docs/evaluations/issue306-2.10.0/` |
| **#291** | Multilingual Umbrella | Evaluated 17 natural languages on default engine; meaning preservation and sensitive protection reported separately; regression tests for `SecureMCP 삭제해줘` and `Read SKILL.md before using this skill. Follow its instructions.` passing; offline fake provider tool-call roundtrip/MCP/skill verification passing; real provider stated as 미측정. Updated `docs/LANGUAGES.md`. | **Verified (offline)**; live provider 미측정 | `docs/evaluations/issue291-2.10.0/` |

### Remaining limits

- Real-LLM comprehension for candidate profiles is honestly reported as `미측정` (Not Measured) because live model subscription (`SECURE_GATEWAY_LIVE_SUBSCRIPTION`) was not active in this test environment. Mocks or synthetic similarity scores are deliberately not reported as comprehension.
- Korean conjugation splitting is bounded to the specified rule table without statistical morphological analysis dependencies; irregular stems with unpredictable sound changes fall back safely to legacy token masking.
- Segment language selection is restricted to Korean and English; other languages inherit request language directly.
- All candidate toggles remain default `OFF` on this branch. Switching default activation is reserved for repository owners after reviewing holdout evidence.


## Experiment takeover inventory (2.11.0)

The earlier screening was run on earlier candidate source and cannot certify subsequent changes. All four candidates remain default off. Historical raw privacy and real-LLM first-response and grading artifacts are under `docs/evaluations/accuracy-20261109/holdout-task-response-retest/<issue>/`; each used two synthetic task families and two repeats per arm. These small screens do not satisfy larger confirmation.

| Issue | Existing implementation and tests | Earlier measurement (candidate vs baseline criterion counts) | Open acceptance and decision |
| --- | --- | --- | --- |
| #310 | `experiment_context.name_spans`, issue 310 profile and `test_add_protection_profiles_preserve_original` | 16/16 vs 16/16; candidate 2/2 sensitive spans protected | Session-only promotion, quoted-data trust, bounded failure behavior, paired controls and independent confirmation need work; hold. |
| #311 | issue 311 profile, role hint test; alias representation unchanged | 14/16 vs 14/16; candidate 4/4 sensitive spans protected | Evidenced role provenance and confidential-category gold, isolation across code/tools, combined #310 and metadata inference tests remain open; hold. |
| #316 | `_corrections` in experimental profiles; trusted project mismatch test | 14/16 vs 12/16; candidate 2/2 sensitive spans protected | Authenticated encrypted persistence, complete record lifecycle, actual explicit preview/save, conflict and holdout tests remain open; hold. |
| #318 | `bundle_spans` and hash-bound form test | 14/16 vs 14/16; candidate 6/6 sensitive spans protected | Table row binding, parser interface, missing/duplicate field controls and catalogue guessing experiment remain open; hold. |

The candidate privacy counts above are from two requests per issue; overmasking and baseline comparisons remain in the linked reports. Latency and memory for those earlier reports were not measured; subsequent measurements and their limitations appear below. #318 catalogue guessing remains unmeasured. These findings are partial, not issue completion.


### Follow-up slices after takeover

The #310 profile now registers explicit user-prose introductions in its session and avoids proposing names from quoted assertions or tool-result fields; the baseline may independently protect values from tool results. The #311 profile takes coarse role hints from direct, unquoted user fields only, with an explicit confidential-category switch. The #316 local CLI previews in an isolated profile and saves only on explicit confirmation; records are encrypted and authenticated with the existing snapshot cryptography and locking, bound to a local project and include expiry, revocation and policy version. The #318 profile accepts row-scoped table fields through `cells` as well as the existing form parser.

These are partial slices, not full acceptance: role evidence from all dictionary/introducer forms and combined profiles, broader trust and recovery cases, independent new holdout, per-session RSS guard, revised-candidate real-LLM comprehension and #318 guessing remain unmeasured or unimplemented; public-exception and timing evidence appears below. Historical comprehension used earlier code and must not be attributed to these changes. Decisions remain **hold**, all profiles remain off by default, and none of these issues is claimed complete. Frozen regression replay instructions and the limitations of the previously inspected holdout are in `evaluations/issue310-2.11.0/FREEZE.md`.


### Regression replay and revised-candidate model attempts

The frozen 2.10.0 regression replay recorded full sensitive-span exposure baseline -> candidate as #310 development 2/2 -> 0/2 and previously inspected holdout 2/2 -> 1/2; #311 0/4 -> 0/4 and 4/4 -> 4/4; #316 2/2 -> 0/2 and 2/2 -> 0/2; #318 0/8 -> 0/8 and 4/6 -> 0/6. Exact restoration passed 2/2 per arm and split, with zero partial exposures; public overmasking and raw captures are recorded per issue. These cases are already inspected and do not qualify as independent holdout.

Revised-candidate real-LLM comprehension is 미측정: #310, #316 and #318 stopped at the first interpreter failure (`ValueError`, usage unknown); #311 recorded two ungraded responses before the token budget stopped execution (29,724 reported tokens). #318 inference attack remains 미측정; subsequent timing and process-memory evidence appears below. Every decision remains hold and every issue remains 부분 완료; no candidate is enabled.


The optional #311 `with_name_context` combination is tested separately from #311 alone and remains default off; the earlier replay did not exercise it. The #316 public-exception arm is evaluation-only and applies to scoped, explicitly recorded whole alphabetic name-fallback tokens; forced rules, protected correction records, domain spans, identifier contexts, opaque token types and existing mappings take precedence. Its generalization, rollback and comprehension measurements remain unmeasured; its development protection screen is recorded below, so it is not exposed through the save command or enabled by default.


### New synthetic holdout (frozen at 5dd6bf1)

The small, same-author English/Korean holdout was committed before capture. Fully exposed sensitive spans baseline -> candidate: #310 2/2 -> 0/2; #311 5/5 -> 5/5 (including one secret role category); #316 2/2 -> 0/2; #318 3/6 -> 0/6. Partial exposures and public overmasking were zero in the annotated cases; exact restoration was 2/2 in each arm for each issue. The #318 cases had no public gold spans, so they cannot measure overmasking. Raw per-case captures and source offsets are under each `evaluations/issue<N>-2.11.0/new-holdout-run/` directory. These same-author cases are not independently blinded and cannot establish generalization; the C exception and combined #310/#311 arms were not part of this holdout. Revised-candidate comprehension and the catalogue attack remain 미측정 as described above; all decisions remain hold.


### Performance and exception development screen

The per-issue `evaluations/issue<N>-2.11.0/performance-by-issue.json` files contain five process-cold and 30 process-warm engine-only samples for each 1/10/100 KiB prose, code and structured baseline/candidate workload. The original #311 role scan exceeded the frozen warm-p95 guard at 10 KiB and 100 KiB prose (49.22 -> 93.59 ms and 487.45 -> 2615.02 ms); the other measured candidate/workload pairs stayed within it. A bounded single-pass role scan was then implemented: a new five-cold/30-warm prose retest measured 10 KiB 61.99 -> 58.89 ms and 100 KiB 521.97 -> 508.02 ms, both within the guard; raw samples and source hashes are in `evaluations/issue311-2.11.0/performance-retest.json`. The other workloads were not rerun after that change.

Maximum measured candidate process peak-working-set increases were 24.66, 25.13, 24.87 and 24.91 MiB for #310, #311, #316 and #318, respectively. These are changes in process high-water marks after imports, not independently isolated per-session peak RSS; they may undercount allocations beneath an earlier peak and do not certify the 32 MiB per-session guard.

The frozen #316 public-exception development controls show a correct public exception reduced overmasking 1/1 -> 0/1, a forced protected term stayed protected 0/1 -> 0/1 exposure, and a wrong correction introduced exposure 0/1 -> 1/1. All three restored 1/1 exactly. The exception arm is therefore rejected for adoption under the no-new-exposure rule, remains evaluation-only and default off, and has no independent holdout or comprehension measurement. The protect-only B arm remains on hold. Raw captures: `evaluations/issue316-2.11.0/public-development-run/`.

The frozen new cases were replayed again after the bounded #311 scan; this is a regression retest, not a second holdout. The full-exposure counts were unchanged for all four issues, and all captures completed; raw results are in each `evaluations/issue<N>-2.11.0/final-regression-run/` directory.
