# Automatic subscription integration

SecureGateway 2.17.1 provides an experimental authenticated loopback gateway for Claude Code and
Codex. Set it up once, then use their normal commands. Requests are masked automatically;
replies and tool arguments are restored before the CLI displays or executes them. The next
request masks restored history again. No agent hooks are registered.

## Local administrator dashboard and SQLite logs

The gateway serves a local dashboard at `http://127.0.0.1:38117/admin` (use your
configured port). Open it with:

```bash
secure-gateway gateway admin
# For a custom config, including the isolated xAI API gateway:
secure-gateway gateway admin --config /path/to/config.json
# Print the URL without launching a browser:
secure-gateway gateway admin --no-open
```

Start or restart the updated gateway first. Sign in with the `token` in its local
`config.json`. This uses the existing gateway capability; there is no separate
admin password. The browser keeps the token only in tab memory, sends it in a
header, and clears it on logout. Reloading the page requires signing in again.
The dashboard loads no external scripts or fonts and provides read-only access.

Foreground and automatically started gateways store processing metadata in
`logs.sqlite3` beside their `config.json`. Subscription and xAI API installations
use their respective configuration directories. SQLite uses WAL and preserves
logs across restarts; only the newest 100,000 records are retained. Uninstalling
or resetting alias sessions does not delete this ledger. Back up the database
after stopping the gateway, or use SQLite's online backup API when it is running.

The dashboard includes summary totals, provider/authentication routes, automatic
refresh, agent/provider/subscription/result/account/time filters, pagination and
request details. Each fixed inference or token-count endpoint records UTC time,
request ID, agent, provider, authentication mode, model, destination, HTTP status,
processing outcome, upstream connection attempt, duration, byte counts and new
alias count. It excludes request/response bodies, query strings, error text,
raw headers, OAuth tokens and API keys. Model names are bounded metadata.

### Bounded audit export

Choose both start and end times (at most 31 days), then select **JSON 내보내기**.
Each file contains at most 1,000 allowlisted metadata rows. If more rows remain,
**다음 파일** downloads the next bounded page; the status shows the file number
and whether another page remains. Changing filters starts a new export.
Logout or another login discards pending export responses before they can
download a file or update the current dashboard.

The authenticated `GET /admin/api/logs/export` endpoint accepts the same filters
as log export, including mandatory timezone-aware `since` and `until`. Responses
include `rows`, `count`, `limit`, `truncated` and `next_cursor`. To continue, send
the exact same filters plus the URL-encoded `cursor=next_cursor`; stop when
`next_cursor` is null. Authentication and all range/field limits apply to every
page. Cursor tokens are signed and bound to the filters, page limit and current
gateway process. Invalid, changed-filter or expired cursors return HTTP 400;
restart the export after a gateway restart.

Pages traverse descending row IDs below a watermark established by the first
page, so concurrent insertions do not enter that export and identical timestamps
do not cause skipped or duplicate rows. This is an insertion watermark, not a
database backup: row metadata is read when each page is fetched, and retention
can remove rows that have not yet been downloaded. If the watermark row itself
is removed, the cursor is rejected instead of risking row-ID reuse. Use a
SQLite backup if an immutable historical snapshot is required. Export never
includes payloads, account/credential references or destination URLs.

`Claude Code → Anthropic → Claude subscription`, `Codex → OpenAI → ChatGPT
subscription`, and explicit `xAI → API key` paths are distinct. New Grok Build
installations and the Antigravity SDK transport attach an allowlisted source
label; other xAI clients are shown as `xAI client`. These labels describe the
client's reported source, not an independently verified executable. CLI flags
that bypass the gateway generate no gateway log.

Codex's supplied account ID is stored as a keyed anonymous reference. A separate
keyed credential reference identifies the presented token/key without storing it.
Both references are specific to this gateway token; credential references change
when OAuth tokens rotate. Claude does not supply an account ID, so its account is
shown as unavailable. These references cannot verify a billing identity or the
subscription tier (Plus/Pro/Max/etc.), and the dashboard does not invent one.

Logging starts before request processing. If the initial SQLite write fails,
the request is refused with HTTP 503 before forwarding. If completion logging
fails, the initial record remains incomplete and the dashboard reports a write
error count for the current daemon. An incomplete record can also represent an
active request or interrupted process. An upstream attempt records a connection
attempt, not proof that a provider received or billed a request. Administrative,
health, model-catalog and unsupported endpoints do not enter the request ledger.

### Masking preview and comparison (치환 결과 비교)

The admin dashboard includes a **치환 결과 비교** (Masking Preview) view for testing how forced rules, domain protection dictionaries, and language/code masking apply to text or files before sending prompts to models.

#### Supported formats and operational limits

- **Direct text & text files**: Supported formats include plain text and source files (UTF-8, including UTF-8 BOM, e.g., `.txt`, `.md`, `.csv`, `.json`, `.py`, `.js`, `.ts`, `.go`, `.rs`, `.c`, `.cpp`, `.java`, `.sql`, `.sh`, `.ps1`, `.log`).
- **File limits**: Phase 1 supports **one file at a time**. Maximum text size is **256 KiB UTF-8** (262,144 bytes). Files exceeding 256 KiB are rejected client-side and server-side with HTTP 413 (`oversize`).
- **Concurrency & deadline**: At most **2 previews** are processed concurrently (subsequent requests receive HTTP 429 `busy` immediately). Each preview has a **10-second processing deadline** (HTTP 504 `deadline_exceeded`).
- **Unsupported formats**: PDF, DOCX, images, compressed archives (`.zip`, `.tar.gz`), and binary files (detected by NUL bytes or UTF-8 decoding errors) are rejected with clear guidance. Remote URLs are not fetched.

#### Policy snapshot and operational isolation

- **Policy snapshot**: Previews use the exact policy snapshot active at request time: forced rules (`mask_rules`), domain policies (`defense`, `automotive`, `semiconductor`), and language/mode selection.
- **Independence from real conversations**: Preview sessions are short-lived, preview-only `GatewaySession` instances. They are never registered in the gateway's conversation table, never touch conversation locks, and never read or write encrypted snapshots. Generated aliases in previews are independent of existing conversation aliases.
- **Attachment non-support**: Inspecting a file in the preview page does **NOT** mean Claude/Codex attachments are protected. Gateway inference retains its strict boundary: attachments, images, and binary files remain unsupported and blocked.
- **Zero persistence & privacy guarantee**: Request text, masked output, alias mappings, and file names are never stored in SQLite logs, stdout/stderr, exception messages, URL queries, or browser storage (`localStorage`, `sessionStorage`, `IndexedDB`). In-memory data is discarded upon clearing the view, navigating away, or logging out. All text is rendered using safe `textContent`.

#### Measured processing times

Processing durations measured on local preview execution (CPython 3.14 / Windows):
- Empty input: ~0.1 ms
- Short sentence (~100 chars): ~0.8 ms
- Medium source file (~1 KB, 40 lines): ~2.5 ms
- Large text file (~100 KB, 3,000 lines): ~120 ms
- 256 KiB UTF-8 text boundary: ~2,000 ms (well within the 10-second processing deadline)

### Content audit observability (치환·복원 감사)

The admin dashboard provides an authenticated **치환·복원 감사** screen (`#audit`) for inspecting the actual recorded stages of historical gateway requests: original user input, upstream masked payload, model response, restored client text, and tool call arguments/results.

#### Operational overview and limits

- **Actual processing records**: Unlike the `#342` dry-run preview, this screen examines real historical executions stored in the dedicated AES-256-GCM encrypted database (`content-audit.sqlite3`).
- **Grounded span verification**: Diff highlighting is server-verified from recorded event pairs and active/historical alias bindings. Pairs with unverified alignment, credential redactions, or missing kinds display an explicit notice ("대응 관계를 확인할 수 없음") without highlights. Unrestored aliases are highlighted with a `[미복원]` badge.
- **Passphrase unlock & auto-lock**: Viewing decrypted content requires administrator passphrase unlock. Five consecutive incorrect attempts incur a 60-second rate-limit lockout. An idle countdown of 10 minutes automatically re-locks the store and purges decrypted content from memory upon timeout.
- **In-memory privacy**: Decrypted audit events and passphrases are strictly ephemeral. Passphrases are cleared immediately upon API return. Decrypted data is wiped from memory upon lock, logout, screen exit, auto-lock, and page reload. No web storage is used.
- **Explicit enablement flow**: Enabling content audit requires explicit acknowledgement of the sensitive data warning. Unobserved external tool traffic and unsupported attachments are not audited.

## Setup and existing logins

Keep your existing Claude/ChatGPT subscription login:

```bash
uv tool install .
secure-gateway gateway install
secure-gateway gateway status
```

Restart both agents. No per-prompt wrapper, file list or manual restoration is required.
If an earlier gateway is already running, update/restart it from the repository:

```bash
uv tool install --force .
secure-gateway gateway stop
secure-gateway gateway install
```

Then restart both agents. These steps are needed only when updating the installed gateway.
`--agent claude` / `--agent codex` limits setup to one host; default is `both`.
`--port` selects the initial port, and `--config` selects local state. Installation is user-wide.

| Agent | Settings changed | Authentication |
| --- | --- | --- |
| Claude Code | `$CLAUDE_CONFIG_DIR/settings.json`, default `~/.claude/settings.json`: base URL and local custom header | Existing OAuth and `anthropic-beta`; no API key/helper added |
| Codex | `$CODEX_HOME/config.toml`, default `~/.codex/config.toml`: provider with `requires_openai_auth = true`, HTTP transport, ChatGPT login selection | Existing CLI-owned ChatGPT OAuth and account header |

When launched inside an Orca-managed Codex account, `CODEX_HOME` is a mirrored
account directory. Orca synchronizes its config from the canonical `~/.codex/config.toml`;
editing only the account copy is overwritten on synchronization. The installer detects
matching `CODEX_HOME`/`ORCA_CODEX_HOME` and the `.orca-managed-home` marker, and backs up
and configures both canonical and active account settings in the same transaction.
The canonical configuration is user-wide and can propagate to other Orca accounts.
Login files are not copied or edited. Restart existing agent sessions to load the new
provider. This handles config mirroring; it does not certify every Orca runtime's routing
or its command-line overrides. Verify a disposable inference request before relying on it.

`gateway status` checks authenticated server health and, when an installation record
exists, verifies installed settings against their recorded hashes. Missing/changed files
produce a nonzero exit with a routing-unverified message; even unrelated edits require
review. A healthy manually started server without a manifest reports that installation
routing cannot be verified. Server health and settings checks are not proof that an
already-running agent sent an inference request through this gateway.

These settings follow [Claude's subscription gateway documentation](https://code.claude.com/docs/en/llm-gateway#subscriptions-and-gateways)
and [Codex's proxy authentication option](https://learn.chatgpt.com/docs/auth#alternative-model-providers).
OAuth is forwarded to Anthropic's service / the ChatGPT Codex backend. API-key requests
are refused; there is no automatic switch to separately billed API usage. Existing plan
limits and provider acceptance still apply. Login caches/keychains and token refresh remain
CLI-owned; SecureGateway never reads or copies them. The local access header is stripped upstream.
Provider 401/403/429 statuses are retained with sanitized error bodies.

Unrelated hooks, permissions and model choices are preserved. Remove old project privacy
hooks before using this gateway: combining independent mapping tables can change references.
The installer removes old SecureGateway hooks in the Claude user settings it edits, does not
scan other repositories and does not register new hooks.

## Automatic startup and removal

Setup starts a detached process immediately and registers user-login startup:

| Platform | Registration |
| --- | --- |
| Windows | `Startup/SecureGateway.vbs`, hidden WScript launch |
| macOS | `~/Library/LaunchAgents/io.securegateway.gateway.plist`, `RunAtLoad` |
| Linux desktop | `$XDG_CONFIG_HOME/autostart/secure-gateway.desktop`, default `~/.config/autostart/`, `Terminal=false` |

No administrator access or agent lifecycle hook is needed. Linux autostart requires a
desktop login; headless hosts can run the foreground command under their own supervisor.

```bash
secure-gateway gateway status
secure-gateway gateway stop
secure-gateway gateway run       # foreground restart/diagnostics; Ctrl-C stops it
secure-gateway gateway uninstall
```

If the daemon stops, configured inference fails at the loopback endpoint. There is no raw
direct-provider fallback. `uninstall` stops it and restores exact backed-up files when
unchanged. For edited subscription settings, it restores only gateway-owned Codex provider/login
keys and Claude URL/token headers, preserving unrelated edits and user-replaced values.
It also removes matching gateway settings synchronized into other Orca account homes.
Startup files and API-mode settings retain strict ownership checks.
State remains in `~/.secure-gateway/gateway`
by default for recovery; remove this directory after stopping if you want to discard them.
Do not commit local state or reuse its access token for other services.

If `installation.json` is missing, use `secure-gateway gateway uninstall --force-clean`
(with `--config PATH` for a custom gateway). This scans the canonical/active Codex home,
Orca account homes and the configured Claude home for recognizable gateway keys. With a
gateway config present, only matching routes/tokens are removed. Without it, recovery
requires the reserved Codex provider with a loopback gateway URL/token, or the Claude
loopback route and token header together. Unknown previous provider, login and URL values
cannot be recovered without a backup. Authentication caches are never changed. Only the
default startup registration can be identified without its manifest; custom startup paths
must be removed manually if the installation record is lost.

## Shared aliases and automatic results

### Domain protection dictionaries (2.6.0)

The authenticated admin dashboard has independent **Defense / Automotive /
Semiconductor** toggles and paged term search. Defense is **On** for a fresh or
previously unconfigured installation; automotive and semiconductor are Off.
An explicitly saved Off survives restart and upgrade. Policy files are encrypted
in the gateway's state directory. Existing private aliases are retained when a
domain is disabled; Off stops additional dictionary matching, not all masking.
Requests in progress prevent policy updates. A failed save leaves the previous
policy active, and missing/corrupt packaged data blocks startup rather than
quietly switching protection off.

The packaged source-category policy protects **19,473 defense**, **6,510
automotive**, and **2,191 semiconductor** concepts. Defense includes named
platforms/models, **149 explicitly compiled subcomponent concepts** and **785
public project/program concepts**, including official DARPA programs and Korean
system/project labels. Counts distinguish concepts, translations/matching forms,
source labels and pending classification phrases. They are not counts of
independently specialist-certified concepts. Short model/acronym spellings use
case-sensitive boundaries; long phrases support separator/case normalization.
Original spellings and offsets are kept for exact restoration.

Examples of protected component categories include RF/sensors, seeker/radome,
actuators/servo drives, power distribution, processor/FPGA boards, connectors and
harnesses, navigation, structural parts, cooling, fuzes and data buses. Public
model/project labels include KF-21/IF-X, K9, F-16, LongShot and Manta Ray. An
unpublished internal project name cannot be obtained from public sources: add
it to the existing explicit local masking rules. A project named like an ordinary
word may still require an explicit rule outside recognized public-name context.

The dictionary describes a user-selected protection policy, not a legal secrecy
classification. Source category membership can contain translation or inclusion
errors; broad protection can overmask dual-use terms. Automatically extracted
incomplete CPC phrases remain browse-only. See [sources and exact counts](DICTIONARY_SOURCES.md)
for reuse terms, exclusions, category coverage and review limitations.

To prevent over-masking ordinary vocabulary while maintaining robust protection
for defense concepts, domain terms are classified at catalog build time as either
`distinctive` or `ambiguous-common` (issue #325):

- **Classification basis**: Single-word terms appearing in packaged ordinary
  or public vocabulary for their language (`gateway_vocabulary.ordinary_words()`,
  reviewed public vocabulary) are classified as `ambiguous-common`. Curated core
  subcomponents and programs (`active-editorial-core`) remain `distinctive`.
- **Distinctive terms**: Behavior is unchanged; they are unconditionally
  protected whenever their domain toggle is enabled.
- **Ambiguous-common terms**: Protected only when anchored within the same
  sentence or clause by:
  1. An adjacent alphanumeric model/part-number/designator token (such as
     `AN/APG-77`, `K2`, or digit-letter combinations).
  2. Another `distinctive` term of the same domain in the same clause.
  3. Membership in a multi-word dictionary term matching as a whole (e.g.
     `phased-array radar`, `사격 관제 레이더`).
  Otherwise, unanchored occurrences (e.g. `radar` or `레이더` in general prose)
  remain public.
- **Scope & Pipeline Interaction**:
  - *End-to-End Gateway Behavior*: Behavior for `radar` and `레이더` is consistent:
    both remain public in general prose unless a forced rule (`gateway.mask_rules`)
    or a multi-word/non-public term applies. In the gateway prose pipeline
    (`GatewaySession.mask`), the #323 prose rule skips single-word public domain
    terms; when an anchored designator is present (e.g. `AN/APG-77 radar`), the
    designator `AN/APG-77` is masked while the common word `radar` remains public
    for prose fluency. Multi-word terms (`tactical data link`, `사격 관제 레이더`)
    and distinctive non-public terms (`KF-21`, `radome`) are masked in prose.
  - *Direct Catalog / CLI / MCP Paths*: The anchor policy takes full effect in
    direct catalog calls (`DomainCatalog.spans(...)`), CLI commands, MCP tools,
    and non-prose chunking (`protect_chunks()`), matching anchored occurrences of
    terms such as English `radar`. Adding missing Korean counterparts (such as
    `레이더`) to the dictionary data is deferred because any change to dictionary
    manifest data changes `catalog().version`, requiring the owner to regenerate
    the privacy regression baseline.
- **Precedence**: Forced rules (`gateway.mask_rules`), sensitive patterns, and
  existing session aliases strictly override both domain and prose policies,
  masking terms regardless of context.
- **Cross-language consistency**: Decisions are made per concept rather than
  surface string; all existing language forms of a concept in the catalog share
  identical classification.
- **Performance & Startup Benchmarks**:
  - Measured with `scripts/benchmark_catalog.py` under identical conditions
    (imports excluded, default `defense` domain enabled, 5 runs median,
    tracemalloc disabled during timing):
    - Load duration: 1.188 s (`origin/main`) → 0.627 s (`fix/325`), ~47% faster.
    - Tracemalloc peak heap: 146.69 MB → 78.46 MB (pre-warmed vocab) / 95.00 MB (cold).
    - Retained memory: 142.03 MB → 37.55 MB (73.6% reduction).
  - *60 MB Target Analysis*: The 60 MB peak heap target is not met during cold load.
    CPython's standard `json.loads` parsing `defense.json` (2.7 MB, 19,566 entries)
    peaks at 66.15 MB on its own due to internal parser token buffers and intermediate
    dict/list allocations, plus 13–17 MB for frozen vocabulary tables. Cold load peak
    heap is therefore bound by the JSON format (~78–95 MB), but post-load retained
    memory is reduced to 37.55 MB once raw JSON structures are collected.
  - *Daemon Preload*: `PrivacyGateway` starts a background daemon thread to preload
    the catalog upon startup. Accessing `gateway.domain_catalog` or sessions blocks
    until the catalog is ready; if preload fails, it transparently falls back to
    synchronous load and logs `catalog_preload_failed`. Diagnostics report load
    duration, enabled term counts, and memory footprint without exposing term strings.

The shared read-only index is built once, then scans each original text using
bounded Aho–Corasick transitions and compact coordinate arrays. It never downloads
data or runs a model during a request. Overlapping protected spans form a union;
URL/email/source opaque spans retain their complete protection. Work-budget
exhaustion rejects a request rather than truncating protection. Only per-session
private alias/cache state is retained, and toggle changes invalidate those caches.

GET `/admin/api/domain-policy` returns effective/default/saved status and policy
version; POST the same endpoint with `{"enabled":{"defense":true,"automotive":false,
"semiconductor":false}}` replaces the policy. GET `/admin/api/domain-terms?domain=defense&query=radar&limit=25&offset=0`
returns at most 100 entries per page with source/review metadata. Existing token
and same-origin requirements apply. Term definitions, prompts and user secrets
are not included in audit logs.

### Conversation isolation and diagnostics (2.5.2)

Codex's `session_id` header selects an account-scoped conversation table. Other
clients may provide `X-SecureGateway-Session`; clients without either header keep
the legacy provider session and must not expect conversation isolation. Identifiers
are hashed with the local token before becoming snapshot names. Registry capacity
is bounded, and provider reset clears all its conversation snapshots/provenance.
Bearer refresh does not change aliases. Switching to scoped sessions intentionally
does not adopt legacy signed reasoning; start a new conversation after upgrading.

The authenticated `/admin/api/sessions` endpoint aggregates conversation mappings
and retains the last 32 request timing summaries in memory: masking, lock wait,
upstream headers/body, restore/save where applicable, first stream event and total.
It contains no prompts, paths, conversation headers, aliases or tokens. Timing
summaries disappear at restart. A 600-second socket timeout is distinct from a
total request deadline; heartbeat delivery does not accelerate upstream inference.

Validation 400s now include a stable `code` and fixed `guidance`, distinguishing
unsupported attachments, unsupported fields/Claude attribution, unknown reasoning
provenance and generic invalid requests. Existing signed conversations require a
new session rather than silently discarding reasoning/tool history. Images remain
blocked: unmasked passthrough is not introduced by this compatibility fix.

Restoration checks reserved spellings in the original response before substitution.
From 2.6.0, issued aliases with ASCII letter/underscore prefixes or suffixes are
restored inside derived identifiers (`test_<alias>`, `<alias>_v2`). Unknown full
alias numbers and unsupported numeric prefixes are still rejected. Restored originals are
not rescanned because legitimate paths/source literals can contain alias-looking
text. Exact registered alias 10 is never guessed to mean alias 1 plus `0`; model
selection of another valid issued alias remains a semantic error that cannot be
inferred from spelling alone. Whole-path tool aliases and lexical shell aliases
are both supported; malformed combinations fail rather than receiving guessed paths.

### Corrupt config and interrupted model downloads (2.5.2)

Uninstall can restore manifest-owned settings when runtime JSON/port/token is
invalid. New private manifests retain a validated runtime identity for selective
cleanup; older manifests without it only restore exactly owned files. A corrupt
runtime config cannot authenticate shutdown: a warning explicitly asks you to
stop the matching daemon using its original terminal or OS process manager after
checking its command/config path. No unrelated process is killed.

Model installation/removal shares a crash-released OS lock and an inode ownership
journal. Retry or remove safely cleans only the recorded interrupted download.
An unrecorded `.download` is preserved; stop installers, inspect and move that
file aside before retrying. The sibling `.model-install.lock` is persistent and
must not be deleted during active operations. Unknown or modified assets are
never silently removed.

A prompt referring to `A` and code containing `def A(...)` use the same identifier alias.
Function/variable names, strings and comments are masked; code numbers are preserved
by default and masked only with explicit opt-in. Filename aliases
are restored for native local tools; their results are masked in the next inference request.
English, Korean and mixed references reuse the multilingual engine.

Fenced code uses its language label; inline code is lexed and tool output uses language
detection. A fragment that cannot be lexed safely (for example a backtick span containing an
apostrophe) falls back to text masking instead of failing the request. Ordinary text uses
`content_words`, known terms and uppercase single-letter references. This remains heuristic:
ambiguous/unfenced or unsupported code needs clearer context. Grammar, syntax, public
built-in tool names and protocol IDs stay visible. Masking does not hide algorithms or
inferred meaning; it can reduce reasoning/edit quality.

Common review/task vocabulary is retained in ordinary instructions to keep requests usable;
known source identifiers take priority over that vocabulary. Code lexing has no identifier
preservation exception. Core tool descriptions use fixed public descriptions, and an explicit
privacy instruction tells the model to keep supplied aliases unchanged.

Gateway identifiers use `private_symbol_<number>`. A controlled live comparison found that
the previous `smcp_ID_` aliases caused Sonnet 5.5 to refuse benign masked requests, while
neutral aliases succeeded with the same masking. This does not establish the classifier's
internal cause. No safety filter is disabled and no raw-source fallback is used. Other
SecureGateway integrations retain their existing alias format.

Claude's first system attribution block (`x-anthropic-billing-header`) is protocol,
not source text. Its observed version, entry-point and optional hexadecimal fingerprint
fields are validated and preserved exactly in the first position, together with validated
cache-control tags. Unknown fields, extra text, moved/merged blocks and invalid cache tags
fail closed. Exact public Claude CLI/Agent SDK identity sentences also remain visible;
those sentences inside source literals are still masked. All other system context is
masked, and the privacy instruction is appended after the original blocks. Anthropic
[documents this positional attribution contract](https://code.claude.com/docs/en/llm-gateway-protocol#system-prompt-attribution-block).

JSON replies and SSE text/tool-argument deltas are restored. SSE headers and heartbeats
are sent immediately; ordinary Claude/Codex text streams at completed token boundaries.
Partial aliases, tool JSON, signed thinking and whitespace-bearing legacy aliases retain
bounded buffers. Chat Completions groups remain buffered until their finish reason.
Unknown/altered aliases fail rather than inventing originals. A stream validation or
storage failure closes the connection without a successful terminal event.
Schema properties and tool-argument JSON keys share aliases. Local `$ref` pointers keep
keywords and array indexes so masked schemas still resolve. Only pinned public Codex
`exec` / `apply_patch` grammars pass unchanged; other custom grammars are blocked. Claude's
safety classifier keeps public policy tags while private paths/rule operands are masked.
Recognized public JSON Schema dialect URIs in `$schema` stay unchanged; other
`$schema` values are masked like ordinary text. Schema descriptions and private properties
remain masked, including URI literals in source. `enum`/`const`/`default`/`examples` values
are treated as data: protocol-named keys such as `id`, `type` or `cache_control` inside
them are still masked. Operational schema fields and JSON scalar numeric parameters retain
their types; numbers in source text are preserved unless numeric masking is enabled. Registered numeric aliases returned as JSON
integers are restored only when their original is a valid JSON numeric literal. Precision-lost
float aliases and non-JSON originals are rejected. Character literals become opaque identifier
expressions in the review representation and restore with their original quotes and escapes.

Schema `minLength`, `maxLength`, `format`, and regex constraints are rejected explicitly:
private string aliases cannot reliably satisfy the original value constraints. Nested schema
positions, including additional/unevaluated items, follow the same rule. Local pointers decode
URI percent escapes and follow schema structure, so names equal to schema keywords stay valid.

SSE accepts LF, CRLF, CR and an initial UTF-8 BOM. Public refusal and reasoning summary text
are grouped separately by content/summary index before restoration; signed reasoning remains
opaque. Malformed upstream JSON/SSE returns 502, while malformed local requests remain 400.

Gateway JSON keys `max_active_requests` (default 32) and `max_provider_requests` (default 8)
must be positive integers. Capacity rejection occurs before reading the inference body, with
429 and Retry-After; shutdown rejects new work and drains admitted requests before deleting
mapping state. Health/admin remain independent of inference admission. `gateway diagnostics`
and authenticated `/admin/api/sessions` show aggregate mapping usage, activity, and expiry.
The logs API and dashboard accept `credential_ref` filters for accounts without an account ID.
Anonymous credential references may change on token refresh and do not prove account ownership.

Installation writes a recovery journal before changing any managed settings. Retry install or
uninstall to roll interrupted changes back when bytes match recorded original/applied states;
later user edits are refused. Antigravity has an independent journal. Native control requests
reject redirects, and `gateway stop` waits for health to disappear after a successful ACK.

The local recursive root reference `$ref: "#"` is supported unchanged. Named anchor
references (`#node`, `$anchor`) are not supported; use root or `#/...` pointers.
Ordinary content/tool blocks validate `cache_control` as public `ephemeral` controls
with optional `5m`/`1h` TTL; private extra fields are refused before forwarding.
Protocol-named extra fields in tool output are masked rather than copied verbatim.
Chat Completions supports validated `reasoning_effort` and `response_format` (`text`,
`json_object`, or `json_schema`); schema names, descriptions and private properties
still pass through masking. These controls are not accepted on Responses endpoints.

Client sockets have a 60-second idle timeout, including incomplete headers/bodies.
Upstream connection/read failures return sanitized 502 responses (504 for timeouts);
invalid requests remain 400. Standard `anthropic-ratelimit-*` and `x-ratelimit-*`
headers are forwarded along with retry guidance, without cookies or private headers.
The public query allowlist also accepts boolean `stream=true`/`stream=false`;
streaming behavior should still be specified in the provider's JSON request body.

Restoration scans aliases in the response and looks them up directly. Prose masking
uses an incremental index to select only existing originals present in the input,
so stable requests do not recompile the entire mapping inventory. Legacy bare
pseudoword snapshots retain a compatibility fallback. Mapping limits still bound
memory use; they are not a guarantee of latency for arbitrarily large input.

Signed Claude thinking (including `redacted_thinking`), and encrypted Codex reasoning remain
exactly masked and are not restored for display. Only blocks previously emitted by this
gateway can be replayed. Codex may omit an empty reasoning `content` list on replay; that
empty field is normalized for provenance checking. Ciphertext, summaries and nonempty
content remain validated.
Providers have separate tables. Codex session headers additionally select an
account-scoped conversation table; clients without a supported session header
share the legacy provider table. Masking/restoration lock only their own table;
upstream network waits do not hold that lock. Use separate configurations/ports
for separate trust domains.

Encrypted snapshots reuse SecureGateway's authenticated encryption and password KDF. They preserve
aliases across daemon restart. Reasoning provenance stores only hashes. Snapshots expire after
24 hours idle; the running daemon and a restarted daemon both drop expired aliases and
provenance. From 2.6.0, bounded startup/periodic maintenance authenticates old
snapshots before deleting expired snapshot/provenance files. Damaged or foreign
files are retained for explicit recovery. Expired/corrupt reasoning state blocks
replay; start a fresh conversation/reset state rather than bypass masking. POSIX private file
modes are applied; Windows uses inherited user ACLs. The key/local token resides alongside
snapshots, so this does not protect against another process with access to that user's files.

New snapshots also preserve the session's positive integer mapping limit and
reject payloads containing more mappings than that limit. Legacy snapshots
without a saved limit use 100,000; legacy payloads exceeding that default are
rejected. Gateway configuration can impose a smaller active budget as before.

Version 0.5.1 uses `<agent>-symbols-v2.enc` with a matching hash-only `.opaque.json` file.
Old `<agent>.enc` snapshots remain untouched for rollback; the snapshot reader still supports
legacy aliases. After upgrading from 0.5.0, start new Claude/Codex conversations once so
previous reasoning does not replay against the new alias table. Do not delete old state
until you no longer need rollback.


## Masking features and defaults (2.17.0, #354)

Five evaluated candidates are available as independent per-session features.
After the joint evaluation of the adopted candidates
([decision](evaluations/joint-adopted-2.16/DECISION.md): ADOPT-JOINT),
**gateway settings enable #310 by default from 2.17.0**. #316 B and #318 are
also on by default, but they are *policy-gated*: they act only when a trusted
local policy exists, and without one they are a byte-identical no-op that never
blocks gateway start. #309 and #319 stay opt-in.

| Feature key | Issue | Real-LLM decision | Gateway default (2.17.0) | Gateway-wide setting |
|---|---|---|---|---|
| `ko_conjugation_split` | #309 | reject | off | boolean |
| `contextual_name_spans` | #310 | adopt (joint) | **on** | boolean |
| `scoped_corrections` | #316 | adopt, protect-only condition B (joint) | on, active only with a configured records file | encrypted records file |
| `attribute_bundle` | #318 | adopt (joint) | on, active only with a per-session policy; gateway settings have no policy source, so it is inactive at gateway level | not available; per-session only |
| `local_arithmetic` | #319 | blocked by #363 | off | boolean |

These defaults apply to the gateway (`gateway run`, `gateway api-run`, auto-start).
The Python library default is unchanged: `GatewaySession()` and
`PrivacyGateway(...)` without `features` enable nothing.

### Upgrading to 2.17.0

- **Existing installs with no `features` key, or no `contextual_name_spans`
  key:** after the gateway restarts, a name introduced in direct, unquoted user
  prose (`Project name: drift`, `프로젝트명은 흐름`) and its later mentions in
  the same conversation are masked. Nothing else changes. On the frozen #310 sets,
  88 of 132 previously exposed name spans became protected with no new exposure,
  no public overmask and unchanged exact restoration. On the legacy CI privacy
  corpus, every metric equals the old default (57/66 protected, the same 9 known
  exposures, 0 new, 0 resolved, public overmask 3/117)
  ([evidence](evaluations/defaults-2.17.0/README.md)).
- **Predicates are never names (2.17.0 guard).** A verb, adjective or
  prohibition form after a name noun is not registered as a name and stays
  visible to the model. This covers Korean conjugated or negated forms
  (`파일 이름은 바꾸지 말며`, `프로젝트 이름은 수정하지 마세요`, `바꿔 주세요`,
  `바꿀 수 없어요`) and English modals (`Customer name: must stay hidden`). A
  spaced modifier in `<modifier> 프로젝트 <name>의` (`가상 프로젝트 흐름의`) is not
  a name either. Forced rules and names registered earlier in the conversation
  still win. Remaining ambiguity: a real name ending in an open vowel or in
  `-지` immediately followed by `말고`/`않` (`사과 말고`) is treated as a
  predicate and is not protected by this feature.
- **#316/#318:** nothing changes unless you configure a policy. A configured
  `scoped_corrections` records file is used as in 2.16 (and a missing password or
  unreadable file still stops the gateway).
- **Explicit settings are kept.** `"contextual_name_spans": false` (config),
  `SECURE_GATEWAY_FEATURE_CONTEXTUAL_NAME_SPANS=off` or
  `--feature contextual_name_spans=off` keeps 2.16 behaviour. Package upgrades and
  `gateway install` keep the existing `features` object. No migration writes a value.
- **Roll back:** set `"contextual_name_spans": false` (or use the environment
  variable) and restart, or run with `--features-off` to restore the complete
  2.15/2.16 default masking path. Aliases created while the feature was on stay in
  the encrypted snapshot and remain restorable.
- Diagnostics (`gateway features`, `gateway diagnostics`, `/admin/api/features`)
  show per feature `default` (on by default), `default_mode` (`on`, `policy`,
  `off`), `enabled` (requested), `active` (applied to sessions), `source`, and for
  an inactive policy-gated default an `inactive_reason` (`no-policy-configured`,
  `per-session-policy-only`). The top-level `enabled` list names only active features.

- `ko_conjugation_split` keeps reviewed Korean condition/negation/request
  endings public while the stem is judged by the normal policy. Forced rules,
  existing aliases and domain matches still win.
- `contextual_name_spans` protects a name introduced in direct, unquoted user
  prose (`Project name: drift`, `프로젝트명은 흐름`) and keeps protecting it in
  later turns of the same conversation. Quoted assertions and tool results do
  not register names.
- `scoped_corrections` adds protection for explicitly saved local correction
  records (`secure-gateway corrections save`) bound to one project and
  language, honouring expiry and revocation. Only the protect-only arm is a
  product feature; the evaluation-only public-exception arm (`public_records`)
  is accepted by the session API for frozen evaluations but never by gateway
  settings.
- `attribute_bundle` protects co-present form/table fields under a trusted
  policy bound to one document hash and scope. Such a policy cannot be a
  gateway-wide setting, so explicitly enabling it in gateway settings is refused
  at start (its policy-gated default is simply inactive); use
  `GatewaySession(features=GatewayFeatures(attribute_bundle=policy))`.
- `local_arithmetic` injects the `local_alias_arithmetic` tool and executes
  calls locally, returning only a result alias. Gateway settings provide no
  per-alias unit policy, so calls are refused (fail closed) until a policy
  path exists; real-model tool use is unmeasured and the feature remains
  blocked by #363. Since 2.16.3 (#371) the injected tool definition is
  trusted gateway data and is forwarded exactly as defined; earlier versions
  masked its `operation` enum, so a model could not name a valid operation.
  Client-supplied tool definitions are masked as before.
- #311, #312, #313, #314, #315 and #317 were rejected and remain
  evaluation-only `candidate_profile` arms; they are not settings.

### Enabling, disabling and rollback

Each feature has its own setting. Precedence is CLI > environment > config
file > default (see the table above):

```json
{"port": 38117, "token": "...",
 "features": {"ko_conjugation_split": true, "contextual_name_spans": true,
              "scoped_corrections": {"project": "alpha", "language": "en",
                                     "records_file": "C:/Users/me/corrections.enc"}}}
```

- Environment: `SECURE_GATEWAY_FEATURE_<KEY>=on|off` (also `1/0`, `true/false`),
  for example `SECURE_GATEWAY_FEATURE_CONTEXTUAL_NAME_SPANS=on`.
  `scoped_corrections` reads its records password from
  `SECURE_GATEWAY_CORRECTIONS_PASSWORD`; a missing password, wrong password,
  unsafe or missing records file stops the gateway with a fixed message rather
  than silently running without the requested protection. Only the
  policy-gated *default* without any configured records is a silent no-op;
  explicitly enabling `scoped_corrections` without records settings is refused.
- CLI: `secure-gateway gateway run --feature contextual_name_spans=on` (repeatable,
  also on `gateway api-run`).
- Disable everything: `secure-gateway gateway run --features-off` ignores the
  config file, environment and 2.17.0 defaults and runs the 2.15 default path.
- Rollback: remove the key (or set it to `false`) and restart the gateway.
  Aliases created while a feature was on stay in the encrypted conversation
  snapshot and remain restorable after the feature is turned off.

Package upgrades do not touch `config.json`, and `gateway install` reloads and
rewrites the existing object with all of its keys, so explicit `features`
values are preserved. A configuration without a `features` key uses the
2.17.0 defaults (#310 on, #316/#318 policy-gated, others off); no migration
writes a default into the file. Expiry of correction records is evaluated when the gateway starts.

### When changes apply

Feature settings are read once at gateway start and are fixed for the process.
Every conversation session created or restored from a snapshot after that start
uses the new settings; changing the file or environment has no effect until the
next restart. The selection is an immutable per-session value: two
conversations, providers or concurrent requests never share feature state or
aliases, and no module global is changed.

### Diagnostics

`secure-gateway gateway features [--config ...]` prints, without contacting the
gateway, the default and default mode, requested and active state, source
(`default`, `config`, `env`, `cli`, `cli-off`) and any `inactive_reason` that
the next start would use. The running gateway reports
the same fields under `features` in `secure-gateway gateway diagnostics` and in
the authenticated Admin endpoints `/admin/api/features` and
`/admin/api/sessions`. Diagnostics never include correction terms, document
hashes, file paths or other policy contents. The Admin masking preview uses the
running gateway's feature selection.

### Evaluation compatibility

`experiment_profiles.candidate_profile(309|310|316|318|319, policy)` is now a
thin wrapper that creates sessions with the equivalent `GatewayFeatures`. On
the candidates' own corpora and unit inputs (1,320 deterministic captures,
including the frozen #309/#310/#311/#313/#316/#318 evaluation cases and the #319
tool path), its masked output is byte-identical to the 2.15.0 profile
implementation. Profiles still cannot nest; direct `GatewaySession(features=...)`
has no such limit.

## Protection boundary and tests

Supported routes: Anthropic Messages/token counting, Codex Responses/model catalog.
Only IPv4 loopback can bind; a local access token is mandatory. Production upstreams are
fixed HTTPS origins; redirects and environment proxies are disabled when forwarding OAuth.
Requests/replies are bounded to 16 MiB; upstream socket operations time out after 600 seconds.

Explicit xAI API-key mode is **opt-in through separate API commands**:
`/xai/v1/responses` and `/xai/v1/chat/completions` forward the caller's own API key to the
fixed origin, and subscription tokens are refused there. The subscription installer never
enables API mode, and there is no automatic fallback in either direction. xAI subscription
reuse has not been verified. `gateway api-install --provider xai --model MODEL` adds
an explicitly selectable Grok custom model; `gateway api-run` runs it in the foreground,
and `gateway api-uninstall` restores the backed-up settings. API configuration, port,
token and encrypted state are separate from subscription mode. Only `https://api.x.ai`
is a production API origin. See the [Grok/API guide](GROK.md) and
[compatibility table](COMPATIBILITY.md) for the verified scope and API billing boundary.

Images, audio, binary/remote files, unknown request fields, WebSocket inference,
`previous_response_id`, background/server-side truncation and compaction endpoints are
unsupported and blocked. No raw pass-through exists. Telemetry, external MCP/browser/tool
traffic, cloud agents and manually overridden endpoints are outside this inference boundary.
This is not an OS-wide network filter or proof of anonymity.

Native **Claude Code 2.1.287** and **Codex 0.160.0** were tested on Windows with fake OAuth
and offline fixture providers. Tests verify masked prompts, split-response restoration,
restored filename tool arguments, actual file reads, masked source/email tool results,
stable mappings, OAuth forwarding and API-key refusal. Captured provider-bound requests
exclude the fixture function name and email. These fixture tests use no real subscription
credentials or model calls. Live tests also verify both agents in **English and Korean**,
using **Sonnet 5.5** and **gpt-6.1-sol** with existing subscription logins. Each test requires
a native file read, at least two inference requests, provider-bound source without the
fixture's function/parameter/email/comment, and a successful answer restored to the original
function name and email. The local file must remain unchanged. The former Claude 429 was
an attribution bug, not subscription exhaustion; neutral aliases also resolved the benign
masked-prompt refusal. No API keys were used, and host settings were not installed during
testing. Provider usage limits/entitlements still apply. macOS/Linux startup
registration has format tests, not real login tests. Windows' hidden WScript launcher was
also executed successfully with quoted paths; an actual OS login was not simulated.

Live tests are opt-in and consume the existing plan's allowance. Normal CI uses offline
fixtures. Set the native executable paths and run all four real-provider scenarios:

```powershell
$env:SECURE_GATEWAY_LIVE_SUBSCRIPTION = '1'
$env:SECURE_GATEWAY_CLAUDE_BINARY = 'C:/path/to/claude.exe'
$env:SECURE_GATEWAY_CODEX_BINARY = 'C:/path/to/codex.exe'
python -m pytest tests/test_gateway_live.py -v
```

The test uses temporary fixture files and process-local endpoint overrides. Codex's test
process has unrestricted access to that fixture directory to avoid Windows sandbox setup
interfering with file-read verification; the installer preserves users' permission settings.

## 한국어 안내

처음 `secure-gateway gateway install`을 실행한 뒤 두 CLI를 재시작하면, 이후에는 평소처럼
`claude` / `codex`를 사용합니다. 매번 별도 명령이나 파일 목록을 입력할 필요가 없습니다.
직접 입력·코드·도구 결과는 전송 전에 치환하고, 화면의 답변과 로컬 도구 인자는 자동 복원합니다.
함수명·변수명·문자열·숫자·주석도 코드 마스킹 대상이며 입력과 코드의 참조는 같은 치환표를 사용합니다.

기존 구독 로그인 파일·키체인은 변경하지 않습니다. 인증과 갱신은 각 CLI가 맡고, 게이트웨이는
OAuth를 원래 서비스로 전달합니다. API 키는 거부하므로 유료 API로 자동 전환하지 않습니다.
구독 한도는 그대로 적용됩니다. 두 CLI 모두 영어·한국어 질문으로 실제 파일 읽기,
코드 마스킹 전송, 정상 답변 생성과 원래 함수명·이메일 자동 복원까지 검증했습니다.
Claude의 기존 429는 식별 블록 처리 오류였고, 정상 요청의 거절은 치환명을 중립적인
`private_symbol_` 형식으로 바꾸어 해결했습니다. 안전 필터와 사용자 문맥·코드 마스킹은 유지합니다.
0.5.0에서 업데이트하면 기존 상태 파일은 보존하며, 새 치환표를 쓰도록 대화를 한 번 새로 시작하세요.

새 Hook을 등록하지 않습니다. 운영체제 사용자 로그인 시 백그라운드로 자동 실행합니다.
해제는 `secure-gateway gateway uninstall`이며, 설치 뒤 사용자가 수정한 설정은 덮어쓰지 않습니다.
텍스트 스트림은 별칭 경계를 확인하며 순차 복원하고, 도구 JSON은 완성·검증 후 전달합니다. 서명·암호화된 추론은 가명 상태를
유지합니다. 이미지·원격 첨부·미지원 요청은 차단합니다. 별도 도구 통신·텔레메트리는 보호 범위에
포함되지 않으며, 문법·코드 구조·알고리즘이 남으므로 완전한 익명성을 보장하지 않습니다.


## Recovery, concurrency, and supported constraints

Alias transformation and encrypted snapshot writes are serialized per conversation;
waiting for the upstream network does not hold the alias lock. Each conversation
keeps its own in-memory snapshot encryption context, deriving the key once;
ordinary encrypted files still decrypt with the configured token. Expiry/reset/shutdown
release that context. In-flight requests retain their alias table until restoration ends.

In 2.6.0 the 256-table memory bound evicts the least recently used idle table to
encrypted storage without extending its TTL. Resuming that conversation reloads
its mappings and reasoning provenance. Active requests are pinned before masking
and never evicted. Without persistent state, or if every table is active, the
fixed `conversation_capacity` diagnostic asks the caller to retry/reset idle
state rather than discarding mappings. Storage failure preserves the live table.
Conversation caching is a 4,096-entry/4MiB session-local LRU. New unrelated aliases
retain old entries; input-relevant private mappings, metadata and policy changes
invalidate affected interpretations. Cache budgets are retained-text accounting,
not a whole-process RSS guarantee.

The default mapping limit is 100,000. Set `mapping_limit` to a positive integer in the
local gateway JSON configuration, or use `gateway run --mapping-limit 200000` for a
foreground subscription daemon. The bound applies before allocating a new alias;
existing aliases remain usable at the limit. To recover deliberately:

```shell
secure-gateway gateway reset --agent claude
secure-gateway gateway reset --config /path/to/api-gateway.json --agent xai
```

Reset requires the local gateway token and refuses while the selected provider has
active requests. It deletes that provider's encrypted snapshot and reasoning provenance.
Start a new conversation afterwards: earlier conversation/tool arguments refer to the
old alias table. Other providers retain their mappings. Reset does not modify login files.

Native OS advisory locks release automatically after a process crash. Their marked
`.lock` files intentionally persist; do not delete them while writers may be running.
A legacy empty lock from the previous exclusive-create format is refused conservatively.
Stop **all old writers**, then remove only the confirmed legacy empty lock and retry.
Install/uninstall use the same configuration lock. An interrupted uninstall records
recovery state; retry uninstall to finish, preserving unexpected user edits.

JSON Schema named dependencies (`dependentRequired`, `dependentSchemas`, and legacy
`dependencies`) share aliases with `properties`. Regex `pattern` and `patternProperties`
constraints are rejected before forwarding because renaming private names cannot safely
preserve arbitrary regex semantics. Replace them with explicit supported properties.
Subscription controls and request envelopes are validated before private content is masked.

Upstream 400/401/403/404/408/413/422/429/500/502/503/504/529 statuses are preserved.
Only allowlisted public error types/codes are returned; provider messages, parameter names,
and other diagnostic content are discarded. Context-length errors receive a fixed
compaction hint. Unknown statuses and redirects become 502. Retry metadata remains bounded
to the existing public response-header allowlist. SSE retains a 16 MiB aggregate budget;
the 600-second socket timeout is a read timeout, **not a total request deadline**. These
limits can reject large or slow streams; reset is not a substitute for context compaction.


POST query metadata is forwarded without alteration after validation: `beta=true|false`,
`stream=true|false`, `client_version` with dotted numeric components, and date-shaped
`api-version` are supported.
Unknown, duplicate, or private query parameters are rejected before contacting the provider.

### Numeric constants in source code

Source fragments preserve numbers by default so indexes, loop bounds and boundary checks
retain their values. To mask sensitive numeric literals, set `"mask_numbers": true` in the
subscription/API gateway JSON configuration or use `gateway run --mask-numbers` /
`gateway api-run --mask-numbers`. The `--preserve-numbers` flag overrides configuration.
This setting affects source-code masking only: prose numbers and JSON protocol/control
fields retain their existing policies. Existing numeric aliases still restore; an actual
source number colliding with a saved numeric alias requires a new session/conversation.

## Operational limits and retention (1.1.0)

Restoration now checks UTF-8 input and output limits before returning or assembling
an expanded result. Defaults are 16 MiB each. `MaskingEngine` and
`LocalPrivacyClient` accept `max_restore_input_bytes` and `max_restore_output_bytes`.
The local `unmask` CLI provides `--restore-input-limit` and `--restore-output-limit`.
The selected input budget applies while reading both UTF-8 files and stdin;
it is independent of the masking input budget.
Subscription/API gateway JSON accepts the same engine option names. Existing
aliases and snapshots remain readable within the configured budgets; oversized
restoration fails with a fixed error rather than returning partial output.

Audit retention defaults to the latest 100,000 **completed** requests, with no age
limit. In-flight requests are never pruned. Gateway configuration accepts
`audit_max_records` (integer from 1 through 9223372036854775807) and optional `audit_max_age_days` (positive
integer). The daemon applies retention on request start/completion; the authenticated
admin API and dashboard report the active policy. To inspect candidates locally:

```sh
secure-gateway gateway audit-gc --config /path/to/config.json
secure-gateway gateway audit-gc --config /path/to/config.json --apply
```

The first command is dry-run; only `--apply` deletes completed candidates. Use the
same configuration file as the running daemon so policy and database agree.
Add `--cleanup-owners` to inspect stale owner lock files, and `--apply` to remove
them. Only valid UUID files with an obtainable OS lock and no remaining database
references are eligible. Live owners, uncertain files, symlinks and legacy
ownerless requests are protected. Recovery alone does not remove referenced owner
files: retention must first remove those requests. Inspection creates, modifies
and deletes no files; repeated cleanup is safe. New writers use exclusively
created UUID files, and applying cleanup serializes with request insertion and
recovery through SQLite's write transaction.
SQLite DELETE removes logical rows, not a secure wipe. WAL pages may retain old
bytes until SQLite reuses/checkpoints them. This command does not force VACUUM or
truncate WAL while the daemon is active; stop the daemon and take a backup before
performing optional SQLite checkpoint/VACUUM maintenance to reclaim physical space.

Version 1.2 adds interrupted-request recovery and non-mutating retention inspection.
See the [audit migration and rollback instructions](UPGRADE_1_2.md). The gateway
JSON accepts `natural_language` (default `auto`) and `sql_dialect` (default
`sqlite`); see [supported language profiles](LANGUAGES.md). These are local
masking controls and are not forwarded as provider request fields.

Installation ownership and recovery records are scoped to each configuration file.
The conventional `config.json` keeps `installation.json`; other filenames use
`<filename>.installation.json`. Nonstandard config filenames also get a separate `<filename>.state` runtime directory
for snapshots and audit logs. Distinct configurations should use distinct host
settings and startup registration targets. Old records belonging to nonstandard
configuration filenames must be reviewed/restored before reinstalling; no automatic
cross-configuration ownership transfer is performed.

## Offline metadata export (1.6.0)

The gateway need not be running. This command opens the existing audit database
read-only and never creates an input database or modifies owner files:

```sh
secure-gateway gateway audit-export --config /path/to/config.json \
  --since 2026-01-01T00:00:00Z --until 2026-01-02T00:00:00Z \
  --output audit.json
```

Dates require timezones and an interval of at most 31 days. Filters include
`--agent`, `--provider`, `--subscription`, `--account-ref`, `--credential-ref`,
and `--result`. Output is `{ "rows": [...], "count": N }` with the same metadata
allowlist as the admin export; it excludes payload, account/credential references
and destination. Pages contain at most 1,000 rows and are walked in one process.
Concurrent inserts after the first page are excluded; retention may remove unseen
rows. No cross-process cursor resume is provided.

Defaults are `--max-rows 100000` and `--max-bytes 67108864`; hard ceilings are
1,000,000 rows and 1 GiB. If a limit or another error occurs before publication, no partial output is
published. An existing output is never overwritten. Publication uses an exclusive
hard link in the output directory; filesystems without hard-link support fail
without publishing a partial file. Narrow the date range or use a supported local
filesystem. Temporary files are cleaned on normal exceptions and interruption.

## Selective ordinary vocabulary (1.6.0)

### Offline multilingual and integration checks

Run `python -m pytest tests/test_gateway_multilingual_corpus.py tests/test_gateway_tool_workflows.py tests/test_gateway_task_language.py -q` from the repository. The corpus contains 17 languages, ordinary passages and synthetic person, company, email and industry terms. Each case checks that the labelled terms are absent from the forwarded text and that local restoration reproduces the input. The checks use synthetic examples; they cannot establish that unlabelled sensitive terms are safe. Everyday words are deliberately disclosed and can also be names or sensitive industry terms. Register such values as forced masking rules before use.

Run `python scripts/evaluate_multilingual.py` for a stricter diagnostic: it reports whole-sentence preservation, labelled-value exposure and restoration by language, plus required skill-text words. A nonzero exit indicates at least one criterion failed. Whole-sentence equality is stricter than semantic understanding and should not be confused with a model evaluation. Test a fresh, independently prepared set of prompts blind with a model: show only the masked text first, record its interpretation, then compare with the original. Never send real confidential content to an external evaluator.

The integration suite exercises an MCP client and server over local stdio, and separately tests gateway tool schemas, calls and results using a local MCP server object. The `SKILL.md` case checks the forwarded instruction text and restoration; it does not execute a real skill. `tests/test_gateway_hosts.py` optionally runs a native Codex or Claude CLI against a local fake upstream when `SECURE_GATEWAY_CODEX_BINARY` or `SECURE_GATEWAY_CLAUDE_BINARY` is set. These checks do not establish that an actual model chose a tool or followed a skill. Live subscription tests in `tests/test_gateway_live.py` require explicit opt-in and can consume a subscription; they are not run by default.

Gateway automatic language selection is heuristic for scripts shared by several languages. Explicit `natural_language` remains available, and ambiguous words can be private names even when they appear in the ordinary vocabulary. Existing aliases, explicit rules and code masking take precedence; use a new conversation after resetting old mappings when testing a policy change.

The development corpus was used to choose initial vocabulary, so its results are not independent accuracy measurements. Before broad vocabulary support, a blind evaluator could not reliably identify both the subject and action in any of 17 new prompts. With the local frequency data and independently authored ordinary-word supplements, a second, newly authored set (`tests/fixtures/fresh_multilingual.json`) scored 12 complete, 4 partial and 1 failed interpretations on the subject/action criterion. Requiring important conditions and device details as well gives a more conservative 9 complete, 7 partial and 1 failed result. This is a small, single-evaluator comparison, not a statistical accuracy claim. A real model, MCP host or skill runtime must not be assumed to work merely because local round-trip tests pass.

### Broad local gateway prose vocabulary (2.3.0)

Gateway prose uses wordfreq's packaged frequency lists for fifteen languages and independently authored Marathi/Telugu forms, supplemented by reviewed household vocabulary. Unknown words still receive aliases. Matching uses exact normalized lookup keys; source spelling is restored unchanged. Frequency lookup uses existing tokenization, with no prompt uploads, runtime downloads or substitution of another language's dictionary. See [data attribution](THIRD_PARTY_DATA.md).

The default frequency cutoffs are Zipf 3.5 for languages with capitalization cues and 4.0 for other scripts. Capitalized words remain conservative, with narrow exceptions for skill verbs and reviewed German nouns. Reviewed person names and domain terms, explicit forced rules, and previously protected originals take priority. The lists are not exhaustive: common names can be ordinary words and frequent industry terms can look public. Register confidential vocabulary explicitly; automatic detection cannot promise to distinguish every such case.

Code continues to use its lexer, literal tool arguments and schema data keep stricter handling, and `aggressive` does not enable the new ordinary-word exceptions. An unclosed code fence or inline backtick is rejected before forwarding; close it before retrying. Existing multiword source aliases remain private across prose boundaries. These changes apply to gateway prose; the library/CLI text modes retain their separate policies.

### Optional local context model (2.4.0)

An optional CPU-only multilingual E5 encoder and a bundled linear classifier can
help distinguish sentence-initial ordinary expressions from capitalized names.
It uses the existing public vocabulary as an eligibility boundary; a high model
score alone **never discloses an unknown word**. This is limited assistance,
not a complete semantic or privacy classifier. The unrestricted experiment exposed
an industry verb and was rejected. Guarded assistance recovered eighteen labelled
ordinary expressions in 1,020 probes but did not improve the independent 17-paragraph
comprehension score. It remains disabled by default. See the
[comparison, independent tests and limitations](evaluations/CONTEXT_MODEL_2.4.0.md).

The helper is disabled when `context_model_path` is absent. To try it, install the
optional runtime dependencies in the same environment that runs the gateway,
then explicitly download the pinned, checksum-verified assets:

```bash
pip install '.[context]'  # from this checkout
secure-gateway gateway model-install
# Repository environment alternative:
uv sync --locked --extra dev --extra native-validation --extra context
```

`model-install` prints an absolute directory. Add that value as
`"context_model_path"` to the existing gateway `config.json`, retaining its other
settings. Finish active requests, stop the gateway and start it with the updated
environment (`gateway stop`, then `gateway ensure`; use the same `--config` for
both). API gateways use `gateway api-run` with their own configuration. The
installer changes neither routing nor configuration. It downloads approximately
136 MB; CPU execution additionally needs several hundred MB of memory. The
repository includes only the small classifier head, not upstream encoder weights.

Requests never download assets or upload text to a classifier. Missing dependencies,
invalid checksums and inference failures retain the existing masking policy;
authenticated `gateway diagnostics` reports `context_model.status` (`disabled`,
`ready`, `missing_dependencies` or `unavailable`). Runtime counters contain no text.
The encoder is shared across sessions, with bounded work and request-local caches.
It abstains for split Markdown/skill fragments, strict data/tool values, code,
`aggressive` mode, unsupported languages, long fragments and truncated candidates.
Forced rules, existing private references, domain/name guards, identifiers and
numbers retain priority. Matching an ordinary spelling can still be ambiguous;
register confidential vocabulary through the administrator's forced rules.

To disable and remove this helper:

1. Remove only `context_model_path` from the same `config.json`.
2. Finish active requests and restart the gateway in the same environment. Confirm
   diagnostics reports `disabled`; do not reset alias sessions.
3. Run `secure-gateway gateway model-remove --directory <the-printed-directory>`.
   It deletes only unchanged, verified upstream model files, retaining unrelated
   files. Modified assets cause removal to stop without deleting any model files.

Model removal does not restore CLI routing. For full removal, follow the existing
gateway uninstall procedure with the installation's configuration and account
scope. Neither model installation nor removal deletes encrypted sessions, logs,
forced rules or agent settings. Old snapshots without the new optional origin flag
remain conservative. An actual 2.3.1 installation also restored and resaved a 2.4.0
snapshot successfully; no snapshot format migration or alias reset is required.

### Text intent with opaque references (2.3.1)

The gateway preserves reviewed task operators, output words, sequencing and negative
instructions in all seventeen supported languages. Reviewed inflections are exact
forms, rather than an unrestricted prefix exemption. Sentence-initial capitalized
instructions require grammatical cues; the exception applies at that position only.
For example, `Compare the options and ask Compare` keeps the first instruction and
hides the later name. Forced rules, recognized sensitive terms and existing private
mappings continue to take priority. Ambiguous names still require explicit rules.

The model-facing instruction treats supplied aliases as stable symbolic references.
It asks the model to use visible actions, relations, order, conditions and output
structure, completing supported work even when it cannot identify a hidden name.
It prohibits guessing originals, inventing aliases or calculating with the displayed
digits of numeric aliases. Tool permissions and approval requirements still apply.
Repeated numeric references retain their aliases, and source numbers with separators
remain locally restorable when mentioned in prose.

For a reproducible blind evaluation with synthetic data, run:

```powershell
python scripts/export_semantic_context.py --corpus tests/fixtures/semantic_holdout.json --output "$env:TEMP/semantic-blind.json"
```

The exporter checks labelled-reference masking, exact restoration and replay stability.
Its output contains only language, the actual model-facing instruction and masked text.
Give that output alone to a separate interpreter and record its task interpretation,
conditions and symbolic response. Only afterward let a grader compare the recorded
answer with the original corpus: one point for the main intent and one for each of
three labelled constraints. Hidden names or category types are acceptable when their
roles remain clear; missing operations, negation, order or conditions fail. A local
round trip alone never earns a model-comprehension pass.

The development and independently authored holdout corpora each contain seventeen
multi-sentence requests with synthetic private references. These are small,
single-interpreter observations, not guarantees for every expression, language
variant or actual provider model. The exporter does not call a model or execute
tools. Native host and MCP checks remain separate from semantic evaluation.
See the [recorded results and remaining failures](evaluations/SEMANTIC_CONTEXT_2.3.1.md)
and its captured model inputs, responses and grading. The new seventeen-language
holdout recovers main intent in fifteen cases but retains all three constraints in
only six; the subsequent Korean predicate supplement scores all four criteria.
Universal comprehension remains unresolved, particularly for Marathi/Telugu and
less common predicate or relational forms.

The default prose policy remains `content_words`. To preserve a small local
ordinary vocabulary while masking unknown content, set these gateway JSON keys
and restart the gateway:

```json
{"prose_mode": "uncommon_words", "common_words": ["teamvocabulary"]}
```

`common_words` allows at most 10,000 nonempty strings of at most 256 characters.
`natural_language` still chooses the local prose language. This is a masking
control, never a provider protocol field. Source code continues to use its lexer
and default numeric preservation. See [plain-text policy](PLAIN_TEXT.md) for
vocabulary provenance, precedence and limitations.

Session diagnostics report the effective `mapping_limit`: the smaller of the
configured allocator limit and the policy retained by a restored encrypted
snapshot. An unloaded provider reports the configured limit for a new session.
Reset or expiry starts a fresh session with the current configured policy.

## Mapping and snapshot budgets (1.7.0)

Each session defaults to a **64 MiB logical mapping budget** in addition to the
mapping-count limit. For every forward mapping, the charge is UTF-8 bytes of the
original plus UTF-8 bytes of its forward lookup key plus 1,024 bytes of policy
overhead. A reused entry is charged once. This is a predictable logical budget,
not a Python heap/RSS limit or exact alias-size measurement. Public mapping
originals should not be mutated in place; saving revalidates their current size.

Snapshot plaintext defaults to at most **128 MiB**; configuration may lower this
limit, but cannot raise it. Encrypted snapshot reads and writes have a fixed
**192 MiB** ceiling. The loader reads at most that ceiling plus one byte before
rejecting an oversized file. Authentication/decryption still requires bounded
whole-buffer memory; this is not streaming decryption.

Gateway subscription/API JSON accepts `max_mapping_bytes` and
`max_snapshot_bytes`. `PrivacySession`, `SessionVault`, and `LocalPrivacyClient`
accept the same names. The local `mask` CLI can lower them with
`--max-mapping-bytes` / `--max-snapshot-bytes`; MCP `serve` accepts those flags
and `SECURE_GATEWAY_MAX_MAPPING_BYTES` / `SECURE_GATEWAY_MAX_SNAPSHOT_BYTES`.
MCP session stats and Gateway diagnostics expose only aggregate usage/policy.

Policies are saved as optional encrypted v2 payload fields. Older v1/v2 files
without them use the defaults and must fit them; oversized legacy files are
rejected rather than silently lifting limits. Gateway restart applies the smaller
of saved and current byte budgets. Existing aliases remain restorable within
input/output budgets. Use a fresh session/conversation if allocation is full.
On mapping-byte exhaustion, mappings and alias reservations newly allocated by
that text/code operation are rolled back; previous entries remain restorable.
Occurrence statistics on reused entries may count attempted operations. Snapshot
save failures preserve the previous file and publish no partial state.

Direct host-settings symlinks are rejected before settings transactions. Use
regular settings files for subscription and xAI installation; the installer does
not replace dotfile links. Recovery/uninstall also refuse a settings path changed
into a symlink. A symlinked parent directory is supported when resolved ownership
and actual writes refer to the same target.


### SDK mapping identity (2.0.0)

`TokenMapping` identity fields (original, surrogate, type, context, lookup key,
identifier metadata, format and literal flags) are read-only. Assigning or deleting
them raises a Pydantic validation error before changing the mapping, keeping
session byte accounting and search indexes consistent. `occurrence_count` remains
mutable for normal usage tracking. This is a breaking change for SDK callers that
mutated identity fields directly; create a new session for different bindings.
Allocator-private initialization methods are internal, not SDK mutation APIs.
Snapshot schemas and CLI commands remain compatible with earlier releases.


### Audit request admission (2.0.1)

Admission checks whether count or age retention is due while holding the SQLite
writer lock; any due maintenance and the request insert share one transaction.
This keeps checks accurate across concurrent stores and avoids a separate write
transaction when no records need removal. If maintenance or insertion fails,
the gateway refuses forwarding with HTTP 503 and increments its audit write-error
counter; it does not leave an unreachable request marked in progress.
Retrying admission after the storage failure clears creates one new request.
Existing live requests remain protected from retention and crash recovery.

Since 2.17.1, admission, completion and completion retries of one gateway enter
the SQLite writer lock in arrival order. SQLite's busy wait polls with growing
sleeps and no ordering, so on a slow disk an early request could lose every race
to later writers for seconds before it was forwarded. The ordered queue keeps
the same time limits (5 seconds for admission, 50 ms for completion, which is
retried in the background when the limit passes); writers in other processes
still wait through SQLite's busy timeout.


### Audit completion retries (2.1.0)

Transient completion-write failures enqueue a snapshot of the ledger's fixed
metadata fields in memory. Prompt/response bodies, arbitrary caller fields, and
provider credentials are not added to the queue. Inference is never replayed.
The original write failure still increments the gateway audit error counter.
Completion writes use a short SQLite lock wait before handing failures to the
queue; admission remains fail-closed. Post-completion maintenance also has a
short nonblocking budget so it cannot delay shutdown by the admission timeout.

Each audit store permits at most 256 queued completions and a 1 MiB logical queue
budget (UTF-8 metadata and request ID plus a 512-byte policy charge per item, not
exact Python heap usage). It retries at most five times, waiting 0.25, 0.5, 1, 2,
and 4 seconds before successive attempts. Short SQLite lock waits and a progress
budget bound each background write. Duplicate IDs retain the first queued
snapshot. Completed, deleted, or foreign-owner records are skipped; retry never
inserts a row or overwrites another completion.

A recovered completion commits before best-effort bounded retention. A retention
failure increments a separate maintenance counter and normal admission/completion
will run retention again. Active requests retain their existing protections.

Authenticated `gateway diagnostics`, `/admin/api/sessions`, and `/admin/api/logs`
include `audit_completion_retries`: pending count and logical bytes, attempts,
recovered writes, skipped records, retry errors, maintenance errors, dropped
entries, and limits. These diagnostics contain no queued metadata or request IDs.

Graceful shutdown waits for audited handlers to finish or enqueue their completion
before flushing the queue. Queue flushing allows one second, accelerates pending
attempts within the existing attempt cap, then counts unresolved entries as
dropped. Over-budget, exhausted, and abandoned entries also increment `dropped`.
The queue is not persisted: process termination can lose pending completion
metadata. Existing next-start crash recovery marks remaining orphaned requests
interrupted; it cannot reconstruct their original completion status.


### SQL type contexts and audit diagnostics (2.1.1)

The SQL lexer preserves CAST syntax and recognized built-in types at CAST and
CREATE TABLE type positions. Ordinary columns named integer, text, or cast remain
identifiers. Native SQLite tests compare execution results as well as exact
restoration, including INTEGER PRIMARY KEY rowid behavior. This is a contextual
lexer, not a complete SQL parser or a guarantee for external/user-defined types.

`audit_write_errors` remains the legacy aggregate of initial audit handler errors.
The new `audit_error_counts` fields distinguish `admission` (forwarding refused),
`completion` (record write failed; retries may recover), and `maintenance` (the
record is committed but bounded retention was deferred). The dashboard uses these
categories and queue diagnostics to show separate warnings. Background retry
maintenance errors are counted in `audit_completion_retries.maintenance_errors`;
that count must not simply be subtracted from the legacy aggregate. Older API
responses without categories retain the existing generic warning.


The 2.1.1 native protocol regressions also cover Claude mid-conversation system
messages with validated inline output effort, and Codex Responses reasoning
context, additional-tools namespaces, tool-call status, and replay item IDs.
Their contents and descriptions still pass through privacy transformation;
unknown control values remain rejected. The opt-in live-test wrappers now pass
through current method arguments instead of rejecting new keyword parameters.


### Windows readiness verification (2026-11-06, 2.1.1)

Claude Code 2.1.318 and Codex CLI 0.166.0 completed actual subscription fixture
round trips in English and Korean using process-local routing overrides, native
file reads, masked provider-bound source, and restored final function names and
email addresses. Fixture files stayed unchanged. No persistent user settings were
installed during those live tests. This checks small conversations, not arbitrary
long sessions, all tools, or all future client/model versions.

For UTF-8 source containing Korean identifiers, Windows PowerShell file reads
must select UTF-8 explicitly (`Get-Content -Encoding UTF8`). A host tool that
already decoded the source incorrectly sends damaged text into the gateway;
masking/restoration cannot recover bytes that the host tool discarded.

SSE text is restored incrementally; incomplete tokens and structured tool groups
can still wait for their safe completion boundary. Unsupported images/attachments
and unsupported protocol fields still fail closed. Lexical source masking can
remove semantic information needed for some analysis; a successful round trip is
not a guarantee that the model's code analysis is correct.

### Encoded tool argument numbers (2.4.2)

JSON encoded inside tool `arguments` strings follows the same finite-number
policy as the surrounding JSON. NaN, Infinity and overflowing exponents such
as `1e400` are rejected before forwarding local requests. Invalid arguments in
provider JSON or accumulated SSE tool deltas produce a safe HTTP 502 restoration
error. Finite exponents and arbitrary-precision JSON integers remain supported.


## Failed subscription setup

`gateway install` stages its runtime configuration while holding the installation lock, then waits for the authenticated local daemon to become healthy before publishing client routing and installation records. If startup fails (occupied port, invalid runtime options, or timeout), the transaction restores the exact prior configuration, host settings, startup file and ownership manifest. A fresh failed setup can be retried with another port.

If a later host-file write fails, setup stops and reaps the daemon it started and rolls back the owned changes. A healthy daemon that existed before setup is retained. The low-level Python `install_gateway()` API still prepares files without starting a daemon unless `start=True` is explicitly supplied; the public CLI enables it.

Setup rechecks file contents after waiting for startup. Detected user changes are preserved; a conflicting `installation.pending.json` remains for explicit merge/retry instead of overwriting them. Normal activation failure removes the journal after successful rollback. Ctrl+C stops a newly started child while retaining the journal for the existing interrupted-install recovery path. Startup diagnostics redact the configured local token, including a token split by the diagnostic capture limit. Only temporary synthetic host settings and local child processes are needed to test these paths; no model provider calls are involved.

## Forced numeric and date rules

Since 2.16.1 (#363) a forced rule containing a digit (an ISO date such as
`2032-02-28`, a signed or zero-padded number such as `-3.25`, `7.20` or `007`,
or mixes such as `03/04/2033` and `2037-11-01 01:15`) is replaced in prose as
one complete span before prose tokenization, so it maps to exactly one alias and
restores with its original spelling. Repeated occurrences reuse that alias.
A digit at the edge of a rule only matches a whole number: `4` does not bind
the 4 inside `12.40`, `1,234` or an existing numeric alias. Inline/fenced code
and source text keep their lexer, which already keeps such literals whole. JSON
numbers in tool arguments and data positions that equal a numeric rule become
numeric aliases and are restored as JSON numbers.

A protocol setting that merely equals a forced value (model name, token limits,
temperature, reasoning effort, type/role tags, pinned tool names) is forwarded
unchanged and no longer refuses the request; only user content is masked. The
request is still refused with the fixed `forced_rule_protocol_conflict` error
when a forced value appears as a whole token in a forwarded identifier
(`id`, `call_id`, `tool_use_id`, `tool_call_id`) or remains visible in forwarded
content outside aliases. The reason category is counted below without content.

## Operational failure diagnostics

Authenticated `GET /admin/api/sessions` and `GET /admin/api/logs` include `diagnostic_counts` for the current
gateway instance. Each fixed counter saturates at 2,147,483,647 and resets on
restart. Counters describe attempts/events, not unique files or production leak
rates. They are separate from the SQLite audit-write counters.

| Counter | Meaning |
| --- | --- |
| `snapshot_scan_io` | A maintenance directory iterator failed. |
| `snapshot_cleanup_io` | Inspecting or removing a maintenance candidate failed. |
| `snapshot_preserved` | An unreadable/foreign/corrupt maintenance candidate was preserved. |
| `snapshot_load_failed` | An active snapshot/provenance load was refused or failed. |
| `snapshot_recovered` | Active request recovery quarantined corrupt state. |
| `snapshot_recovery_io` | Quarantine failed; the existing safe request failure applies. |
| `upstream_error_body` | An upstream error body could not be read/parsed within the size limit. |
| `upstream_error_format` | Unexpected error formatter/cleanup failure required a fixed fallback. |
| `upstream_error_close` | Closing the error stream in that fallback also failed. |
| `upstream_error_stream_close` | Best-effort close of the sanitized upstream error stream failed. |
| `log_delivery_failed` | A warning delivery failed; counted quietly to prevent recursive logging. |
| `forced_rule_protocol_identifier` | A forced rule matched a forwarded call/message identifier as a whole token; the request was refused. |
| `forced_rule_unmasked_content` | A forced rule remained visible in forwarded content outside aliases; the request was refused. |

The `secure_gateway.gateway` logger emits one warning per actionable category per
instance; later events remain visible in the counters. Preserved maintenance
candidates increment a quiet counter because foreign state is not proof of
corruption. Authenticated expiry and files already removed during a scan are
normal maintenance, with no warning. Active proven-corrupt state retains the
existing quarantine policy; maintenance never deletes such files speculatively.

Gateway warning records contain only a fixed category and message: no snapshot path, token,
mapping, request, provider body or exception traceback. This bounds repeated
warning output. The counters remain available when a logging destination filters
warnings; they are not persistent forensic records. Normal client disconnect
cleanup failures log only the exception type. Antigravity SDK request logging reports only method, status class, and duration.

Both inference and model-catalog HTTP errors preserve sanitized allowlisted
statuses and captured retry headers. If the formatter itself fails, the gateway
closes its error stream and returns the fixed error schema instead of dropping
the client connection or exposing exception contents. Normal structured provider
errors retain their public allowlisted type/code. Standalone calls to
`sanitized_upstream_error()` attempt a best-effort fixed warning on read/parse failure unless an
explicit diagnostic callback is supplied; close failures also produce a fixed warning.
The gateway supplies bounded instance callbacks.

A warning-handler exception does not alter the sanitized response or snapshot policy.
Gateway instances count failed emission attempts in `log_delivery_failed` without
recursively logging them. The stateless sanitizer also tolerates such failures.

The foreground and daemon server entry points install a gateway-owned diagnostic
handler and isolate it from parent logger handlers while serving. A failed open or
write is counted once for the failed warning and is exposed in authenticated
diagnostics as a count only; its exception and path are never printed by that
handler. Delivery runs on a background thread through a bounded queue, so a slow
or failed destination does not delay the HTTP response. Counts become visible
after delivery is attempted; a full queue counts as failed delivery. Library use
keeps the caller's logging configuration and propagation; its handlers retain
their own error-handling behavior.

Gateway process logging is configured at startup with
`SECURE_GATEWAY_LOG_LEVEL` (default WARNING). Events contain fixed categories
and bounded metadata, never request content, credentials, paths, exception text,
or tracebacks. See [error handling](ERROR_HANDLING.md). CLI output is program
output and is not converted to logs.

If `invalid_config_uninstall_daemon_not_stopped` is reported, owned settings
were restored without confirming daemon shutdown. Stop only the known gateway
foreground terminal, or restore a verified configuration backup and use the
normal `gateway stop --config` command. Do not terminate an unrelated listener;
retain encrypted state until recovery is complete.

### Stopping during an active request

The subscription CLI daemon stops admitting new requests when shutdown starts.
Already-admitted inference may finish during a 30-second grace period. If it has
not drained by then, the dedicated daemon exits forcibly; affected clients see
a connection error and must retry. The stop command reports a content-free
`gateway_shutdown forced=true` diagnostic when it observes a forced timeout.
The next start uses the normal encrypted snapshot and audit recovery paths.
A gateway embedded in another process never terminates its host through this watchdog.
