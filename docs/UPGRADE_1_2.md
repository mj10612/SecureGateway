# SecureGateway 1.2 upgrade and issue verification

This release adds 15 natural-language adapters and 15 source-language profiles.
The complete list, local dependencies, explicit language selection and syntax
limits are in [LANGUAGES.md](LANGUAGES.md). Existing English/Korean and nine code
profiles remain supported. Code numeric literals remain unchanged by default.

## Identifier spellings

Binding comparison and exact spelling restoration are separate. Python NFKC
equivalents, JavaScript/C# escaped names, raw/escaped identifiers and SQL case
variants retain the same native binding. Where originals use different spellings,
aliases can also have distinct but native-equivalent spellings: for example,
Python fullwidth letters or JavaScript Unicode escapes. Keep each alias exactly
as received; do not normalize it in the model response.

`sql_dialect` defaults to `sqlite`, preserving the prior quoted/unquoted SQLite
behavior. Select `standard` or `postgresql` for lowercase-folded unquoted names
and case-sensitive quoted names. The profile does not make this a complete SQL
dialect parser. Identifier spelling variants have finite capacity; exhaustion
raises an error instead of silently splitting a binding. Start a new session
when a bound is reached.

Existing encrypted snapshots remain readable. Snapshots containing the new
identifier metadata and Unicode/escaped alias variants require version 1.2 or
later. Stop the gateway and keep a copy of its encrypted state before downgrading;
do not replay a conversation against a different alias table.

## Audit database transition

Stop older gateway processes before upgrading. The writable audit store migrates
schema version 1 to 2 by adding a nullable owner column; request metadata is
preserved. Retries are idempotent. Journal mode changes from WAL to DELETE so a
read-only retention inspection does not create WAL/shared-memory sidecars.
This trades WAL concurrency for ordinary SQLite reader/writer locking.

The new gateway owns a unique OS-locked owner file for its lifetime. Startup
recovery marks requests from terminated owners as `interrupted`, without making
up an HTTP status. Active owners are protected even across multiple processes.
Interrupted records become eligible for the configured retention policy.

Ownerless records from old versions are protected by default because the new
process cannot prove that an old writer has terminated. After stopping all old
writers, inspect them explicitly, then apply only if the report is expected:

```sh
secure-gateway gateway audit-gc --config /path/to/config.json --recover-incomplete --include-legacy-incomplete
secure-gateway gateway audit-gc --config /path/to/config.json --recover-incomplete --include-legacy-incomplete --apply
```

The default inspection never creates directories/databases or changes an existing
database. A legacy WAL database must first be opened through normal writable
maintenance/startup; the read-only command reports that prerequisite without
creating sidecars or silently reading a stale immutable view. Retention age is
validated before filesystem work; unrepresentable dates are rejected.

Before migration, stop writers and back up the database using SQLite's backup
API (including committed WAL data). The rollback path is to stop version 1.2
and restore that pre-upgrade backup before starting an older gateway. This
restores the old schema without deleting columns from the live database.
Requests created after the backup remain in the retained version-2 database;
they are not silently merged into the old backup.

## Tracked issue groups

| Issues | Implementation / verification |
| --- | --- |
| #154 | Nested property-name schemas, combinators and specialized local references; JSON Schema document validation |
| #171 | Fixed-length catalog EOF checks using an actual loopback HTTP fixture |
| #187, #188 | Python/SQL binding-equivalent aliases, native Python/SQLite checks, encrypted reload and continued allocation |
| #189 | Incremental JavaScript contextual-keyword state; bounded scaling regression |
| #190, #191, #208 | Read-only retention, date bounds, owner locks, process termination/restart recovery and migration tests |
| #204–#207 | JavaScript escaped identifiers, Python annotated names, Rust raw identifiers and Hook lookalikes |
| #192–#197, #209–#219 | Natural-language adapters, CLI/MCP/Gateway propagation, four strategies and three modes |
| #198–#203, #220–#230 | Source-language adapters, literal/identifier/numeric boundaries, exact restoration and independent grammar fixtures |

The natural-language tests prove the tested lexical rules and exact restoration,
not complete morphological analysis or named-entity recognition. VBA validation
uses a shared VB grammar and synthetic module wrappers, not an installed Office
host. Native tools and grammar fixtures do not prove arbitrary program behavior
or complete language conformance. Missing validators fail the dedicated opt-in
grammar gate rather than being counted as a successful language check.
