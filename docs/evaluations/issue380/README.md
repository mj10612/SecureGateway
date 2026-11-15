# Issue #380: evaluation skill catalog isolation

On 2026-11-16, a local fake Responses endpoint captured requests from the real
Codex CLI 0.169.0 using the lean evaluation argv, an empty temporary workspace
and empty temporary `CODEX_HOME`. No account or real model was called. User
skill files were never modified, and raw requests containing their catalog
were not saved. Reproduce with:

```powershell
uv run --locked python docs/evaluations/issue380/probe_skills.py --write
```

Measured results are in [probe-results.json](probe-results.json):

| Per-call override | Request bytes | Skill catalog present |
| --- | ---: | --- |
| Existing lean flags | 34,417 | yes |
| `features.skip_host_skill_discovery=true` | 34,417 | yes |
| `skills.include_instructions=false` | 24,276 | no |

The setting is documented in the [official configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).
The failed discovery flag is retained as evidence rather than adopted. The
effective setting removes 10,141 bytes (29.5%) from this machine's fixed probe
request. These are **bytes, not token counts**; fake endpoint usage is synthetic.
No new paid inference or token-cost measurement was performed. Other machines'
catalog sizes and future CLI behavior can differ.

SecureGateway 2.19.2 adds the effective setting only to `evaluation_batch`'s child
process argv. The worker rejects CLI versions below 0.169.0 and unrecognized
version strings before inference because older clients may ignore unknown keys.
This is the first verified version, not a claim about when Codex introduced the
setting. Prerelease builds require separate verification. The probe checks both
successful completion and disappearance of catalog markers. It also reports
host skill path mentions, which fell from one to zero here.

This prevents automatic catalog instructions from being sent; it does not prove
the CLI never discovers or reads skills locally, or provide a filesystem jail.
The frozen `evaluation_codex_worker` retains its original bytes and limitations
for historical reproducibility. Use the lean adapter for new isolated text
evaluations. Historical native runners and frozen custom runners do not gain
this setting automatically.

## Historical evaluation correction

Before this correction, both native and lean sessions could send the user's
skill names/descriptions despite `--ignore-user-config`, `--ignore-rules`, an
empty workspace and prompts forbidding skills. In particular, the #364 fixed
input measurements (~15,100 native / ~7,070 lean tokens per call) included this
uncontrolled context; they must not be described as skill-free model overhead.
The interpreter and grader could see that catalog. Existing measurements are
not automatically invalidated, but their context isolation was weaker than
"only the task messages" and their raw cost depends on the host installation.
Keep historical scores, source hashes, prompts and frozen artifacts unchanged;
preregister new comparisons rather than mixing corrected and historical runs.

This change is confined to evaluation setup. It adds no masking of skill
contents or tool names, as required by the issue's owner comment, and leaves
normal gateway behavior, Codex configuration, skills and account settings unchanged.
