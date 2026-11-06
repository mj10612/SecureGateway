# Local context-model evaluation — 2.4.0

Date: 2026-11-06. Tracked in [issue 292](https://github.com/mj10612/SecureGateway/issues/292);
the broader text-comprehension problem in [issue 291](https://github.com/mj10612/SecureGateway/issues/291)
remains unresolved. Exact model manifests, measurements, blinded inputs, interpreter
responses, grading evidence and gateway probe results are in
[context_model_2.4.0.json](context_model_2.4.0.json).

## Decision

Keep the guarded E5 integration optional and disabled by default. It recovers some
capitalized ordinary expressions, but the independent paragraph score remains
34/68. Do not enable arbitrary unknown-word disclosure: the unrestricted encoder
classifier incorrectly released an industry verb. A small embedding model is not
sufficient evidence that a new word is safe to disclose, or that the receiving
LLM understands the surrounding request.

The local development environment has the optional runtime and verified E5 assets
installed for repeatable testing. The user's gateway configuration is unchanged;
no alias reset, routing change or daemon restart was performed. Runtime setup and
removal are documented in [GATEWAY.md](../GATEWAY.md#optional-local-context-model-240).

## Models and procedure

Both encoders ran locally on CPU with pinned upstream INT8 ONNX weights. No prompt
text was sent to a model service. Runtime requests never install or download models.
The model revisions, licenses and file hashes are recorded in the JSON and
[attribution](../THIRD_PARTY_DATA.md). Upstream model cards describe general text
embeddings, not verified confidentiality detectors.

| Corrected comparison | Multilingual MiniLM L12 | Multilingual E5 small |
| --- | ---: | ---: |
| Downloaded encoder/tokenizer/config bytes | 127,536,559 | 135,430,652 |
| Calibration threshold | 0.906955 | 0.9 |
| Calibration ordinary candidates preserved / 170 | 35 | 92 |
| Calibration private candidates exposed / 170 | 0 | 0 |
| Test ordinary candidates preserved / 136 | 40 | 58 |
| Test private candidates exposed / 136 | 1 | 0 |
| Warm single-context median / p95 (ms) | 21.38 / 26.67 | 17.48 / 18.48 |

These are **raw classifier** measurements, not deployed gateway disclosure rates.
Selection used calibration rows. Zero on a small set does not establish safety:
E5 subsequently failed an independently authored industry-term probe.

The frozen encoder supplies complete target-token and context vectors, their
product and difference, to a 1,536-feature logistic classifier. The committed head
uses E5 with its `query: ` prefix. Coefficients use 680 training rows; threshold and
regularization selection use 340 calibration rows. The original classification
fixture contains 408 training, 204 calibration and 272 test examples. An additional
contrastive fixture contributes 272 training and 136 calibration examples, placing
ordinary actions and specialized industrial actions in comparable contexts.
No test rows were used to fit classifier coefficients.

The initial experiment was rejected for two separate reasons. Labels sometimes
covered a name stem while runtime classified the inflected whole word; a Bengali
name then became public. Variable INT8 inference shapes also made scores depend on
other batch members. The corrected pipeline uses complete lexical candidates and
fixed 1×128 inference per unique context. Training comparisons and runtime now use
the same shape. A preliminary leading-subword agreement heuristic was also rejected;
it did not solve unfamiliar technical predicates.

## Actual gateway checks

The 1,020 gateway probes span all seventeen supported languages: English,
Korean, Spanish, French, Portuguese, German, Indonesian, Turkish, Russian, Hindi,
Marathi, Bengali, Urdu, Telugu, Arabic, Chinese and Japanese. They combine the
272 classification test rows, 272 challenge rows, 204 morphology rows, 136
independently authored final-holdout rows and 136 new confirmation rows. Each compares the existing policy with
the actual assisted request path, including seeding, restoration and replay.

| Labelled gateway checks | Existing policy | Guarded E5 |
| --- | ---: | ---: |
| Ordinary target visible / 510 | 157 | 175 |
| Private target visible / 510 | 42 | 42 |
| Newly exposed private target or lexical component | — | 0 |
| Restoration failures | — | 0 |
| Repeated-request differences | — | 0 |

The 42 already visible private targets are real limitations of the baseline
heuristics, not successes. They require explicit private vocabulary rules. Nor
does a visible target mean that its whole sentence was preserved. Do not report
175/510 as full sentence accuracy.

The 136-row holdout first found `final-pt-07`: the unrestricted E5 path exposed
Portuguese `cemente`, an industry verb. The head was not retrained on this failure;
instead, the deployment policy stopped admitting unknown vocabulary. Because that
holdout informed the policy change, its guarded results are development evidence,
not untouched final-policy accuracy.

The additional 136 confirmation rows were independently authored after the
deployment guard was frozen, without access to source or previous evaluations.
They revealed the English possessive fragmentation bug described below. The fix
changed neither classifier coefficients nor confidence/eligibility selection.
After that correction, ordinary visibility is 22/68 without assistance and 32/68
with it, private visibility is 0/68 in both, and all restoration/replay checks pass.
These are regression results after diagnosing the bug, not a universal accuracy
estimate for a completely untouched final pipeline.

The deployed guard accepts only an existing public-vocabulary word at a real
sentence boundary with initial capitalization, and only with sufficient model
confidence. It checks the original occurrence, not every repetition of that word.
Code/skill-fragment boundaries and dotted identifiers cannot create new sentence
starts. Existing sensitive terms, source references, forced rules, identifier
shapes, numbers, code, strict data/tool values and aggressive mode retain priority.
Frequency vocabulary still has ambiguous name spellings; explicit forced rules
remain necessary. Case-free languages receive no new blanket exemption.

The ordinary-word improvements occur in the cased languages in this set. Korean,
Chinese, Japanese and the Indic/Arabic-script probes receive no extra preservation
from the capitalization guard. In particular, this release does not solve the
remaining Korean paragraph-comprehension failures through an embedding model.
Further promotion requires both improved independent paragraph interpretation and
privacy holdouts containing unfamiliar technical predicates; more word-level
passes alone are insufficient.

A separate French regression was fixed in the tokenizer: a sensitive-term split
must not turn `d'` or `d’` into a new private `d` mapping on successive requests.
Likewise, English possessive endings remain attached to private stems without
inventing an `s` mapping that changes unrelated words on replay. Previously private
whole suffixes or standalone `s` still override grammar preservation.
Source-origin metadata also keeps code and strict-data references private between
CJK characters. The additive flag preserves encrypted snapshot format 2; actual
2.3.1 wheel code restored and resaved a new snapshot, and 2.4.0 read that legacy
round trip with unknown origins handled conservatively.

## Independent LLM comprehension

Seventeen independently authored paragraphs contain synthetic private names and
reference codes, everyday tasks, order, negation, conditions and output limits.
Separate interpreters saw only masked inputs and the actual model-facing instruction.
A grader then compared their recorded answers with the original text: main intent
plus three conjunctive labelled constraints, four points per paragraph. Unknown
identities and object types are acceptable; missing actions or conditions fail.

| Variant | Intent / 17 | Constraint points / 51 | Total / 68 | All criteria / 17 |
| --- | ---: | ---: | ---: | ---: |
| Existing policy | 10 | 24 | 34 | 3 |
| Unrestricted E5 — rejected | 11 | 30 | 41 | 4 |
| Guarded E5 — optional | 10 | 24 | 34 | 3 |

The guarded comparison has zero paired criterion improvements and zero regressions.
This is one interpretation per variant, not a statistical provider-model benchmark.
After the possessive correction, sixteen runtime exports still matched the graded
inputs after alias normalization. English changed only its possessive representation
and was reinterpreted by a fresh blinded agent, then graded separately. Both new
English variants passed 4/4, leaving the paired totals unchanged at 34/68. Captured
before/after inputs and the English supplement are in the JSON. Local round-trip
tests are not counted as comprehension.

## Cost and validation

On this Windows AMD64 / Python 3.11.15 environment, the actual guarded runtime
loaded in 0.929 seconds with warm filesystem cache, adding 429,420,544 RSS bytes
(about 410 MiB). Thirty warmed requests for `final-en-01` measured median/p95
1.29/1.39 ms without the model and 19.61/25.84 ms with it. This single short request
does not represent maximum-budget or long-request latency. The optional encoder
is shared across sessions; inference is bounded to 32 candidates per fragment and
64 per request. No plaintext survives in a cross-request model cache.

The final frozen-source suite passed 4,138 tests with 280 platform/optional skips
and 92.12% coverage. Source/test/fixture/dependency hashes were checked before and
after that gate and remained unchanged. A further 257 focused passes cover the
possessive and alternate SQL-binding regressions. These runs include the actual encoder corpus
checks and native Codex tool-call/restoration checks. Ruff, mypy, locked dependency
validation and package consistency checks passed. Isolated wheel/sdist installs
verified bundled head data, CLI, MCP and package version 2.4.0. Existing MCP, tool
and skill workflow regression tests remain part of the full suite; this does not
claim every external MCP server or arbitrary skill was executed.

## Reproduction

Install the repository extras with `uv sync --locked --extra dev --extra
native-validation --extra context --extra context-eval`. Download the pinned assets
explicitly with `gateway model-install`; the comparison script also requires the
MiniLM revision recorded in its manifest, arranged as `MODELS/minilm` and `MODELS/e5`.

```bash
python scripts/benchmark_context_model.py --model e5 \
  --models-dir MODELS --data tests/fixtures/context_classification.json \
  --additional-data tests/fixtures/context_contrastive.json --output-dir RESULTS
# Repeat with --model minilm. Test rows never select the fitted coefficients.

# Set SECURE_GATEWAY_CONTEXT_MODEL_DIR to the verified E5 directory first.
python -m pytest tests/test_context_model.py -q
python scripts/export_semantic_context.py \
  --corpus tests/fixtures/context_paragraphs.json \
  --context-model E5_DIRECTORY --output blinded.json
```

For a new comprehension trial, provide only the export to a fresh interpreter,
record its answer, and then grade against the original. Keep failed probes and
policy-development data separate from any new untouched confirmation corpus.
