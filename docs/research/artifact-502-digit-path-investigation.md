# Artifact lifecycle HTTP 502 on digit-leading path segments (CI run 42561072234)

Status: **cause reproduced in released 2.7.1; tokenizer fix verified for 2.7.2 (see §§7–8).**
Investigated 2026-11-09 against released commit `60ffe54156307371b70ea904612ff382eece478c` (2.7.1). The root working tree's uncommitted vocabulary integration was not used to diagnose the release.

## 1. CI evidence

- **Run and job:** run 42561072234, job 128977385288, "Distribution smoke (windows-latest)", Python 3.11.9.
- **Wheel run passed:** the wheel clean lifecycle printed `{"stage": "all", ..., "provider_requests": 2, ...}`.
- **SDIST run failed:** the child `LIFECYCLE_PROOF` raised `HTTPError 502` at `<string>` line 147 (`restored = send(payload)['output'][0]`, the first tool-call request), about 19 s after start.
  - The traceback shows no fake-provider handler exception.
  - The work directory was `C:\Users\RUNNER~1\AppData\Local\Temp\securegateway-package-89_8lzey`.
  - The response body was not logged in 2.7.1.

## 2. Reproduction in installed released artifacts

- **Setup:** I built `secure_gateway-2.7.1.tar.gz` and the wheel from `git archive 60ffe54`. I installed each into a uv venv using CPython 3.11.15, in a retained workspace with the exact CI basename `%TEMP%\securegateway-package-89_8lzey`. Each run used a fresh disposable home and the released proof with a fake local provider. No network model calls were made.
- **Instrumentation:** content-free hooks recorded only exception classes and the gateway's fixed error strings.

| Artifact | Work basename | Result |
| --- | --- | --- |
| sdist 2.7.1 | `securegateway-package-89_8lzey` | **3 of 3 failed**: HTTP 502 `{"error":"Upstream response could not be safely restored"}`; provider requests = 1; restore raised `builtins.ValueError`; session save never reached |
| wheel 2.7.1 | `securegateway-package-89_8lzey` | **2 of 2 failed**, identically |
| sdist 2.7.1 | `securegateway-package-k3vqzpwa` | 2 of 2 passed |

**Conclusion:** the failure is **deterministic for the work-directory name** and independent of sdist versus wheel. The CI wheel run passed only because `tempfile` drew a different random basename.

The failing layer is **response restore** (`GatewaySession.response` raising `ValueError`). It is not upstream transport, not the provider (the request reached it), and not the session-save or filesystem path. A save failure would have returned 500 "local I/O".

## 3. Root cause (actual, reproduced)

Released `src/secure_gateway/engine/tokenizer.py`, `TOKEN_SPLIT_REGEX`, `NUMBER` alternative:

```
(?P<NUMBER>[$€£₩¥]?\d+(?:,\d{3})*(?:\.\d+)?%?(?:[A-Za-z]+)?)
```

1. **The tokenizer splits the segment.** The alternative has no right word boundary, so a digit-leading word that continues with `_` (or a digit after letters) splits into adjacent chunks: `89_8lzey` becomes `NUMBER '89'` + `WORD '_8lzey'`.
2. **The aliases are glued together.** When the gateway masks the tool schema's `default` path, each chunk gets its own surrogate: a numeric surrogate (`7328…`) and `private_symbol_13`. These are emitted with no separator, as one `\w+` run: `…-732846766110241283private_symbol_13\…`.
3. **The provider echoes it back.** The fake provider returns that masked default as the tool-call `arguments`.
4. **Strict restore rejects it.** `MaskingEngine.unmask` raises `ValueError: Unrecognized or altered surrogate tokens`, and the gateway maps that to 502 (`gateway.py` around line 2825 in 2.7.1).

**Rate:** over 1,000 random `tempfile`-style 8-character suffixes, 53 failed (about 5.3%), so the clean-lifecycle job flakes at roughly that rate per artifact. Every failing suffix starts with a digit.

**User impact (not only CI):** in the released restore path, these synthetic tool paths also fail:

- `D:\work\2024_report\notes.md`
- `/home/u/2024_report/notes.md`
- `/srv/3d_models/a.obj`

`/srv/v2/a.py`, `/srv/2024/a.py` and `/srv/12ab34cd/a.py` round-trip correctly.

**Read-only check of the root working tree:** the same probe still fails for `89_8lzey` (8 of 200 random suffixes). `engine/tokenizer.py` is unchanged from 2.7.1.

**Fix layer:** `engine/tokenizer.py` `NUMBER` should not end inside a word. For example, add `(?!\w)`, or let a digit-leading `\w+` run fall through to `WORD`. An alternative is to have the masking layer guarantee that adjacent surrogates stay separable. A regression test should round-trip a tool-path default such as `…\2024_report\…` through `request` and `response`.

## 4. Hypotheses ruled out

| Hypothesis | Evidence against it |
| --- | --- |
| Stale daemon or Windows `SO_REUSEADDR` port sharing | Reproduced in-process with deterministic results; a closing daemon answers 503, not 502 |
| Fake-provider exception | No handler traceback in CI; the provider received the request and replied 200 |
| Filesystem save or short-path (`RUNNER~1`) resolution | Restore fails before save; the in-process reproducer uses a plain `runneradmin` path |
| sdist build difference | The wheel fails identically with the same basename |

## 5. Diagnostics-only change (does not fix the cause)

`scripts/package_smoke.py`: the child proof's `send()` now labels each request (`tool_call` or `tool_result`). On `HTTPError` it prints one stderr line, then re-raises:

```
LIFECYCLE_DIAGNOSTIC {"gateway_error": "...", "provider_requests": N, "status": S, "step": "...", "work_basename": "..."}
```

- **What it reports:** an allowlisted fixed gateway error string or an allowlisted upstream error type. Other strings and unknown upstream types are withheld. Arbitrary short error text is never copied into diagnostics.
- **Shared helper:** `LIFECYCLE_DIAGNOSTICS` is prepended to the child proof and also exec'd in the module, so tests cover the exact code the child runs.
- **Verified end to end:** against installed 2.7.1, the `89_8lzey` workspace emits `{"gateway_error": "Upstream response could not be safely restored", "provider_requests": 1, "status": 502, "step": "tool_call", "work_basename": "securegateway-package-89_8lzey"}`. The `k3vqzpwa` workspace still passes.
- **Tests:** the final `tests/test_package_lifecycle_diagnostics.py` has 13 cases, including arbitrary short text and unknown upstream-type rejection (Ruff clean).

No retry, timeout change or skip was added.

## 6. Retained evidence (outside the repository)

- **Workspaces:** `%TEMP%\securegateway-package-89_8lzey` (failing; `failure-*.log`) and `%TEMP%\securegateway-package-k3vqzpwa` (control).
- **Scripts:** `repro.py`, `minimal.py`, `probe2.py`, `impact.py` and `e2e.py`, in this session's scratchpad `diag327/`, plus the CI job log `ci327.log` (historical scratch names, not an issue reference).

**Limits:** the reproduction ran on local Windows 11 with CPython 3.11.15, not on the GitHub runner. The 8.3 short-path home was not reproduced, and it is not needed for the failure.

## 7. Fix evidence (2026-11-09, root working tree, uncommitted)

Sections 1–6 above are the historical reproduction and are left unchanged except for wording that no longer applies.

**Change:** `src/secure_gateway/engine/tokenizer.py` (sha256 `e2e19dab29ea984aca298875eb4c4b520690a6483607524090d46bcbc000ada5`). The `NUMBER` alternative of `TOKEN_SPLIT_REGEX` now ends with `(?!\w)`, so a number can never end inside a word. The diff is one changed line plus a three-line comment. No other production file was changed.

| Input | Before | After |
| --- | --- | --- |
| `89_8lzey`, `2024_report`, `3d_models` | `NUMBER` + `WORD` | one `WORD` |
| `12ab34cd` | two `NUMBER` chunks | one `WORD` |
| `3é4x`, `3é_x`, `5km²`, `१२_अ`, `٣_ب` | `NUMBER` + `WORD` | one `WORD` |
| `2024`, `१२`, `$5,000.00`, `₩1,000`, `100%`, `5kg`, `3.5x`, `100%abc` | `NUMBER` | `NUMBER` (unchanged) |
| `3개`; email, phone, IP and UUID formats | unchanged kind | unchanged kind |

**What the change does and does not cover:**

- `natural_languages.tokenize` imports the same compiled regex, so the fix also covers its protected-`NUMBER` path.
- CJK `2024年` was already handled by zh segmentation into separate `private_symbol` aliases, which restore through the alias-run rule.
- No masking or restore code was changed.

**Regression proof (`tests/test_tokenizer_digit_paths.py`, 49 tests, sha256 `4cd12d9dad17773adbd24af0afa809e0a03952a25438852a24ecb86cea5fb499`):**

- **Chunk kinds:** digit-word segments become one `WORD`, while standalone numbers, currencies, percents, units and sensitive formats keep their kind.
- **Session round trip:** `GatewaySession.request` → `response` round-trips the tool-schema `default` paths (both CI basenames, `D:\work\2024_report\…`, `/srv/3d_models/…`, Unicode and native-digit segments, and controls), plus a prose mask/restore.
- **Fake HTTP:** a real `PrivacyGateway` and a fake provider run a tool call and then a `function_call_output` replay for `89_8lzey`, `2024_report`, `3d_models` and the control `k3vqzpwa`. Each run checks that there were two provider requests, that the provider never saw the private path or segment, and that the replayed output came back intact.

**Results:**

| Tree under test | Result |
| --- | --- |
| Released 2.7.1 source (old tokenizer) | 26 failed, 23 passed (deterministic) |
| Released 2.7.1 plus only this tokenizer change | 49 passed |
| Root working tree | 49 passed |

**Random basenames:** across 1,000 random `tempfile`-style suffixes, 0 failures with the fix (released-plus-fix tree and root tree), compared with 53 failures before.

**Installed artifacts:** I built sdist and wheel from released 2.7.1 plus only this change (sdist sha256 `93801a8d…a688e`, wheel `92179857…d784`). Each was installed into the retained `securegateway-package-89_8lzey` and `securegateway-package-k3vqzpwa` venvs and run with the root `scripts/package_smoke.py` `LIFECYCLE_PROOF`, using disposable homes and a fake provider.

- All four runs passed with `provider_requests: 2` and `tool_roundtrip: true`.
- Before the fix, the same `89_8lzey` workspace emitted `LIFECYCLE_DIAGNOSTIC {"gateway_error": "Upstream response could not be safely restored", "provider_requests": 1, "status": 502, ...}`.
- No real gateway installation, no retries and no skips were used.

**Wider regressions:** the targeted masking, natural-language, numeric, gateway, tool-workflow, session and HTTP suites (16 files) gave 63 failed and 788 passed. The **identical 63 failures** occur with the old tokenizer restored on a copy of the root tree, so they are pre-existing from the concurrent root vocabulary integration (for example `Unmasked hi/te/ur fixture`) and are not caused by this change. `test_code_parser`, `test_extended_code`, the new digit-path tests and the diagnostics tests gave 328 passed and 232 skipped (the skips are existing). Ruff and mypy are clean on the changed files.

**Limits:**

- Not run on GitHub runners.
- The version bump, changelog and commit are owned by root.
- The native-digit and CJK cases were checked only through the paths above, with no native-speaker review.

## 8. Final 2.7.2 checks

The root coordinator exported only the staged hotfix tree to a disposable
directory, excluding all uncommitted vocabulary and evaluation changes.
The final diagnostics helper uses explicit allowlists for fixed gateway errors
and upstream error types; it does not log arbitrary short error text.

- Final focused tests: 62 passed (49 tokenizer/path tests and 13 diagnostic cases).
- Ruff passed; mypy passed for the isolated release source.
- CLI, package metadata, module version, MCP server version and MCP status all
  report 2.7.2.
- Both the 2.7.2 wheel and sdist were built and independently installed. Each
  clean lifecycle passed with two fake-provider requests, tool round trip and
  preservation of user setting edits. These final artifact checks used Python
  3.14.7. They did not measure a cross-version upgrade or native Claude/Codex
  host compatibility; the previous targeted reproduction used released 2.7.1
  plus the tokenizer change as described above.
- A full isolated unit suite was started separately. Its result and the new
  GitHub CI result were still pending when this report was finalized.

No host gateway configuration was installed or changed.
