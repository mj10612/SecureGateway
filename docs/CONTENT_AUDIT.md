# Content audit: design and implementation (issue #343)

**Status: Phase 1 backend merged in v2.13.0; Phase 2 Admin UI screen implemented in v2.14.0.**
The opt-in content audit subsystem records selected payload stages from real gateway requests for
subsequent local review. It uses a dedicated AES-256-GCM encrypted store (`content-audit.sqlite3`),
passphrase-derived key-encryption keys, and local admin observability screens.
It does not transmit unmasked data to external models or telemetry.

## Purpose, consent and limits

The proposed opt-in store records selected fields from real gateway requests for
subsequent local review. It can hold private documents, passwords, source code,
and restored responses. Credential-pattern redaction is best effort: a password
or secret typed in ordinary prose may not be recognised and may be stored
(encrypted). The administrator must see this warning before enabling collection.
Choose only required providers/agents and kinds, exclude individual requests,
or pause collection. There is no retrospective capture. No external model or
tool is called for auditing; no cloud upload or telemetry is added.

Settings are authenticated with the existing encrypted admin-settings mechanism:
`enabled` defaults false, a pause flag, provider and agent allowlists, independent
`input`, `sent`, `response`, `tool_args` and `tool_result` switches, failure
policy and retention bounds. `X-SecureGateway-Audit: off` excludes one local
request; it is not forwarded. Image, binary and remote attachments are not
supported; record only their blocked fact as safe metadata. The gateway can
report only the tool communications it sees, not external tool activity.

Extract allowlisted content fields rather than serialising whole messages,
headers, URLs or raw error bodies. Never persist structural credential fields,
headers, cookies, API keys or the local token. Apply the engine's secret-pattern
detector to every selected text field independently of its normal tokenisation,
including inside code blocks and URLs; redact PEM private-key blocks as a whole.
Redact matched spans with a fixed placeholder, count removals and mark the
record. Patterns cannot prove that all free-form secrets were removed. Error
metadata uses fixed existing sanitised categories. The ordinary metadata view
must not show forced-rule originals, only safe policy identifiers.

## Cryptography and store

Use the existing `cryptography` dependency, AES-256-GCM with fresh random nonces,
and one randomly generated 256-bit data encryption key (DEK) per key generation.
Derive a key-encryption key from the admin passphrase using scrypt (N=131072,
r=8, p=1, approximately 128 MiB of working memory) with random salt, and wrap
each DEK with AEAD. Parameters are recorded per wrapped key; legacy N=16384
keys remain readable and are upgraded atomically when the passphrase changes.
New encrypted exports use the stronger profile and legacy exports remain readable. Opening an existing store adds key parameter columns; older builds cannot safely
write this migrated schema and cannot unlock rewrapped keys. Back up the store
before upgrading and restore that backup if reverting to an older build; do not
run older and newer writers against the same store. The passphrase is
never stored, logged, sent in URLs, put in command arguments or browser storage.
Retain old wrapped DEKs while records using them remain. A passphrase change
atomically rewraps every DEK; rotation adds a new DEK for subsequent records.
The admin must unlock again after daemon restart. Lost passphrases make the
associated records unrecoverable; backups of ciphertext alone do not recover
keys. Unlock, change and rotation failures must not destroy existing records.

Each event authenticates an unambiguous, versioned encoding of schema version,
request ID, sequence, kind and the previous event's GCM tag. Decryption verifies
sequence continuity, tags and authenticated completion markers before claiming a
complete request. A missing final marker denotes incomplete history, including
a crash or process kill; report it as such rather than guessing whether a final
event was deleted. An attacker can delete or roll back the entire store, or
replace it with an older valid copy, undetected without an external trust anchor.

Use a separate `content-audit.sqlite3` beside the gateway state, never
`logs.sqlite3`. Create an owner-only directory and file before opening SQLite;
restrict WAL and shared-memory sidecars too. POSIX mode 0700/0600 relies on the
filesystem honouring permissions and existing parent directory permissions.
**Windows limitation:** the existing platform helpers do not provide an owner-only
ACL, and Python mode bits do not create one. The prototype does not set or verify
a Windows DACL or fail closed when it is absent; configure and verify restrictive
permissions on the containing directory and its SQLite sidecars before use. This
limitation is unverified across Windows versions, and the experimental prototype
must not be used for real content. Encrypted data at rest protects against other
users and offline copies subject to these controls; it cannot protect against
the same logged-in user or malware running as that user while unlocked. The
passphrase and DEKs necessarily reside in process memory while in use; Python
cannot guarantee their byte-level zeroisation.

Alternatives: the existing metadata ledger must remain content-free; a separate
store isolates policy, retention and backup. OS credential stores (DPAPI,
Keychain, Secret Service) can enable unattended startup but vary in same-user
access guarantees, availability, dependencies and daemon semantics. They are
deferred until each platform and unattended-start mode is verified. The chosen
passphrase protects a copied store but requires manual unlock on every restart.
No home-made encryption is acceptable.

## Capture, durability and states

`input` is selected pre-mask content. `sent` distinguishes a prepared masked
body from data actually handed to the connection, and marks transport outcomes
that cannot establish delivery as `전송 여부 불확실`. `response` records the
observed masked response and the restored content actually shown locally.
`tool_args` records observed model-produced masked arguments and the restored
arguments handed back; `tool_result` records observed results and whether they
were re-masked. Do not infer external execution or completion from a prepared
body. A stream uses parsed event boundaries and tracks partial events, rather
than treating arbitrary read chunks as complete messages.

Use a bounded in-memory queue of 256 records and one writer; queue operations do
not wait on disk or delay the first streamed token. At most 1 MiB per kind per
request and 2,000 stream events are retained; exceeding either marks `부분`
and records the omitted byte/event counts. Queue overflow and write failures
mark `기록 실패`; interruption or cancellation is not reported as complete.
Store enough authenticated lifecycle information to distinguish `완료`, `부분`,
`기록 실패` and `전송 여부 불확실`, including incomplete requests on restart.
A retry only retries audit persistence; it must never rerun an inference or tool.

Under `continue` (default), admission never waits for a content-store write:
locked, full, saturated or failing storage leaves a visible gap and the request
continues. Under `block`, before any upstream call the handler synchronously
writes and fsyncs a small opened record containing safe metadata and selected,
redacted input; a locked/full/failing store refuses with a fixed error and no
upstream call. Later events use the asynchronous queue. Later write failures
cannot undo an upstream call and must surface as gaps. This guarantees that an
unaudited request is not **started**, not that every later event is captured.
Measure and report preflight latency separately. Disk failure or process death
can also prevent persistence of a gap marker; such a limitation must be surfaced
as a failed or incomplete request using the metadata ledger where possible.

## Retention, deletion and export

Writer-enforced defaults are seven days, 1,000 requests and 256 MiB total;
delete oldest requests first under the same concurrency control used for writes.
Include database/WAL growth in the storage budget and address concurrent
admission, oversize individual records and active requests explicitly.
Authenticated operations delete selected requests, a bounded time range or all
requests and return counts and scope. Bulk deletion must checkpoint/truncate WAL
and run VACUUM, with failure surfaced. SSD wear levelling, snapshots, backups
and previously exported copies can retain deleted data. Session reset and
uninstall preserve content by default; deletion requires an explicit API flag.
Key retirement alone does not erase ciphertext or independent backups.

Export requires an explicit request/range and kind selection. Default export
uses a fresh random export key and AES-GCM, wrapped with a key derived from a
separate export passphrase using scrypt; authenticate schema, selection and
record ordering. Plaintext export requires a separate explicit confirmation and
warning. Neither format includes structural credentials; the same best-effort
redaction limit applies. Restore must authenticate the export and its complete
sequence before importing or showing content, reject a wrong passphrase or
modified file without partial import, and be tested using synthetic records.
The user is responsible for the selected destination and external backups.

## Admin and operation

All endpoints use existing local Host/Origin checks and token authentication;
responses are `no-store`. Define status, settings GET/PUT, unlock, lock, list,
explicit one-request decrypt, encrypted review status/memo, delete and export.
Unlock accepts a POST body, not a URL. Five failed attempts cause a 60-second
lockout; idle access locks after ten minutes. API clients must explicitly call
the lock endpoint before logout: the existing dashboard does not manage content
audit keys. A future content-audit UI must lock on logout and screen exit.
Status and list return safe metadata only. Review is either `정상` or `확인 필요`;
its encrypted memo is neither an assertion of protection nor proof of factual
accuracy. Fixed-category security events cover access, export, delete, settings,
unlock success/failure and write failure; no contents, credential, path,
exception text or traceback enter diagnostic logs.

Operational sequence once implemented: review the warning and select minimum
scope and limits; initialise/unlock with a passphrase through authenticated
local admin; explicitly enable; pause or send the exclusion header as needed;
lock when finished. After restart unlock again. For a passphrase change, unlock
and rewrap all retained keys; for key rotation, add a new DEK and keep earlier
wrapped keys until their records expire. Test a backup and export restore with
synthetic content before relying on them. Lost passphrases have no recovery
bypass. Select deletion scope, confirm irreversibility and inspect the returned
count; remove independent exports and backups separately where desired.

## Phase 2 Admin UI screen (치환·복원 감사 화면)

Phase 2 adds the Admin Observability screen (`#audit`) and request row action integration:

1. **Request row integration (`치환·복원 감사`)**:
   - Each request row in the processing log list displays an action button.
   - It is enabled only when content audit holds data for that request.
   - When not enabled, it displays the specific reason:
     - `꺼짐` (Content audit is disabled)
     - `제외` (Excluded per-request via `X-SecureGateway-Audit: off`)
     - `일시 중지` (Content audit was paused when the request was processed)
     - `과거 기록 없음` (Recorded before content audit was enabled, or not audited)
     - `저장소 잠김` (Content audit store is currently locked; unlock required)
     - `삭제됨` (Record expired by retention bounds or deleted by administrator)
     - `기록 실패` (Capture failed or dropped due to queue saturation/errors)

2. **Settings & Unlock panel**:
   - Displays current state (`꺼짐`, `활성`, `일시 중지`, `저장소 잠김`), scope (providers, kinds), failure policy, and retention bounds.
   - **Explicit enablement flow**: Before `enabled` can be turned on, an explicit confirmation dialog/box displays the design doc warning (stored payloads, potential for ordinary secrets to be stored encrypted, retention limits) requiring user acknowledgement.
   - **Passphrase unlock**: Rate-limited unlock (5 failed attempts trigger a 60-second lockout). Passphrase is wiped from memory immediately after the request returns.
   - **Explicit lock & auto-lock**: Immediate lock button; 10-minute inactivity timer with real-time countdown display that automatically locks the store and purges decrypted content from UI/memory upon expiry.

3. **Stages & Grounded Comparison View**:
   - Displays recorded stages in chronological order with state badges (`완료`, `부분`, `기록 실패`, `전송 여부 불확실`) and omitted counts:
     - Input original ↔ Sent (masked; distinguishes `prepared` vs `sent`)
     - Model response received (masked) ↔ Local displayed response (restored)
     - Tool arguments (masked from model ↔ restored for local tool)
     - Tool results (original from tool ↔ re-masked for upstream)
   - Reuses `comparison.js` from #342: Server-derived verified spans computed from recorded pairs and alias mappings (`derive_spans`). If a pair cannot be verified (partial record, missing kind, redacted credential placeholder, no mapping), returns `uncertain: true` and displays an explicit notice ("대응 관계를 확인할 수 없음") without highlights.
   - Unrestored aliases in displayed text are highlighted with `[미복원]` badge and aria-label.

4. **Distinguishing notices & Metadata header**:
   - Always-visible notice card clearly distinguishes this screen from #342 preview (actual historical execution vs dry-run simulation).
   - Notices state that unobserved external tool traffic is not audited, and image/binary attachments are unsupported (blocked status only recorded).
   - Metadata header displays safe policy identifiers, request ID, start time, agent/provider, status, duration, language/mode (never forced-rule sensitive original text).

5. **Review, Deletion & Export**:
   - Review form: allows setting status (`정상`, `확인 필요`) and memo (stored encrypted in audit log); explicitly disclaims that it is a reviewer's note, not a system guarantee.
   - Deletion: supports single request, range, or all requests with irreversible-consequence warning dialog.
   - Export: encrypted export by default; plaintext JSON requires an explicit warning confirmation.

6. **Frontend Security & Accessibility**:
   - Strict `textContent` DOM construction (zero `innerHTML`).
   - Zero browser persistence (no `localStorage`, `sessionStorage`, or `IndexedDB`).
   - In-memory decrypted records cleared on lock, logout, page navigation away, auto-lock, and window unload.
   - Keyboard accessible, ARIA live region (`#audit-live-status`) for state announcements, responsive CSS layout.

## Acceptance mapping and verification status

Phase 1 backend merged in v2.13.0; Phase 2 UI screen implemented in v2.14.0.
Status mapped across the six issue #343 acceptance checkboxes:

1. **Synthetic prose, code, multilingual, SSE, and tool round trips**: **Done (Verified)**
   - API verified spans tested for complete prose, tool calls, split SSE, partial records, missing kinds, redacted credentials, and unrestored aliases (`tests/test_content_audit_spans_api.py`).
   - Comparison UI rendering tested for custom labels, badges, unrestored alias markers, and uncertain notices (`tests/test_admin_content_audit.js`).

2. **Default off, opt-in scope, exclusion, pause, and zero regressions**: **Done (Verified)**
   - Default off enforced; provider/kind allowlists tested; `X-SecureGateway-Audit: off` tested.
   - Processing log list action button reasons verified across all 7 states (`test_admin_content_audit.js`).
   - All existing metadata queries and admin preview tests pass unchanged (`tests/test_admin_preview.py`, `tests/test_content_audit_admin.py`).

3. **Canary leak sweep, credentials, tampering, and session isolation**: **Done (Verified)**
   - Synthetic canary test confirms decrypted payloads and secrets do not appear in metadata DB, logs, or error responses (`tests/test_content_audit_spans_api.py`).
   - Unlock lockout, wrong passphrase (401), rate limiting (429), and store locked (423) verified.
   - Memory wipe (`clearAuditState()`) verified on lock, logout, navigation, and auto-lock.

4. **Failure policies, locked store, and crash safety**: **Done (Verified)**
   - `block` and `continue` failure policies tested with synchronous start and unblocked inference.
   - Locked store gracefully refuses decrypt without crashing or exposing plaintext.
   - Incomplete / process interruption records accurately labeled as `부분` or `기록 실패`.

5. **Retention bounds, deletion, export/restore, and OS limits**: **Done with documented limits**
   - Verified request deletion, range deletion, full wipe, and encrypted/plaintext export (`tests/test_content_audit_export.py`, `tests/test_content_audit_admin.py`).
   - Documented limits: SQLite VACUUM/WAL checkpointing does not guarantee physical SSD block zeroisation.
   - Windows limitation: Python mode bits do not establish Windows owner-only DACLs; this remains unverified across all Windows environments.

6. **Accessibility, comparison UI, documentation, and versioning**: **Done with documented limits**
   - Comparison UI tested with Node VM DOM unit tests (`tests/test_admin_content_audit.js`, `tests/test_admin_status.js`, `tests/test_admin_audit_phases.js`, `tests/test_admin_export.js`).
   - Responsive CSS, keyboard focusable controls, and ARIA live region implemented.
   - Documented limits: Testing was conducted via automated Node VM DOM and headless suites; real browser matrix and assistive screen reader hardware (e.g. JAWS, NVDA) were not physically tested.
   - Version bump to 2.14.0; all test suites pass.

## Phase 1 implementation evidence

The backend supports explicit request and time-range deletion and export, plus
authenticated offline restore into an empty unlocked store. A synthetic test
exercises a process exit with an unfinished record, and a separate canary test
checks the store and sidecars, diagnostic output and exports. These focused
checks do not prove secure deletion of SSD blocks, snapshots or backups, nor do
they establish complete credential detection in free-form text. The admin API
can rotate a data key and change the passphrase; restore remains an offline Python
operation. The comparison UI and browser-specific verification remain phase 2.

## Synthetic performance sample

Run `uv run python scripts/benchmark_content_audit.py --requests 20` for a
loopback-only SSE comparison. On Windows 11, Python 3.14.7, AMD64 Family 25
Model 33, one warmup and 20 sequential requests per mode produced the following
means (milliseconds); a regression suite ran concurrently, so these are a
noisy illustrative sample rather than a capacity or production guarantee.

| Mode | First SSE line | Total | CPU seconds | Disk bytes | RSS delta bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Off | 15.55 | 16.37 | 0.39 | 0 | 5632000 |
| Metadata | 19.99 | 25.83 | 0.44 | 24576 | -3788800 |
| Content | 24.16 | 31.40 | 1.75 | 180224 | -32768 |

Block-mode synchronous preflight averaged 18.26 ms in a separate synthetic
store operation. RSS is a before/after process delta, not peak memory; negative
values reflect process memory changes and are not memory savings claims. CPU
time is process-wide, and disk bytes are the remaining files after shutdown.

## Unlock cost

Five consecutive synthetic store unlocks using the new scrypt profile on Windows
11, Python 3.14.7, AMD64 Family 25 Model 33 took 305.6, 306.8, 305.9, 299.1
and 307.4 ms (mean 305.0 ms). The focused test suite ran concurrently; these
figures are illustrative and depend on hardware and load. Unlocking a store
with mixed legacy and current key profiles derives each distinct profile once.
