# Packaging-byte correction — 2.6.1

Windows CI found that Git's automatic LF→CRLF checkout conversion invalidated
the domain files' exact SHA-256 values. This affected startup and caused dependent
HTTP/installation tests to fail. Ubuntu's tests passed, but its offline comparison
found a settings-hash difference because the original Windows manifest writer
used CRLF while Git's stored manifest used LF.

The patch pins packaged dictionary JSON and the curator to LF, and writes the
manifest as explicit UTF-8 bytes. Data revision **1.0.1** records the corrected
curator provenance. Its manifest SHA-256 is
`acdace798275fc625d7947273d99363e21f7682f2f09d20b7123e3f9a2bf8d63`.
`dictionary-patch-equivalence.json` verifies that **every entry and count is
identical** to 1.0.0; only data version and curator provenance changed. Hash
validation remains strict. No matching rule or protection policy was relaxed.

Three actual Git-checkout tests cover the original broken CRLF conversion,
corrected dictionary hashes and exact frozen-evaluation-byte preservation.
Dictionary/admin/checkouts passed 28 tests before the final third checkout test,
which then passed independently (three checkout tests). Installed wheel and sdist
both passed 2.6.0→2.6.1 lifecycle upgrades and four native offline host tests each.
The lifecycle also saves explicit defense Off/automotive On through the previous
installed version and checks that policy after upgrading.

`privacy/report.json` is the fresh 32-request reference with the corrected
manifest: 57/66 fully protected occurrences, nine existing full exposures, zero
partial exposures, 30/117 overmasked public spans; all decoded JSON roundtrips,
replays, isolation and encrypted restart pass. Exact text is 31/32 because one
JSON string's whitespace differs. These unchanged baseline limitations remain
open work; this packaging patch is not an accuracy fix.

`performance.json` records the corrected catalog revision's matcher measurements.
The earlier 288-combination matrix remains historical evidence under
`../domains-2.6.0/` with its original manifest hash. In particular, its synthetic
100,000-string index memory and Unicode scan allocations are **not** the actual
catalog's full cold-load heap/RSS. Full catalog memory/startup and broad common
technical-word policy are tracked in #325; do not infer those values from the
synthetic index benchmark.

The task-response retests in `../accuracy-20261109/` are exploratory/regression
evidence. Under #324, vocabulary/morphology adoption needs independent
development/holdout separation, broader multilingual privacy measurement,
three or more repeats per language and the clarified information-deferral rubric.
