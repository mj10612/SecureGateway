# Text comprehension evaluation for 2.3.1

Tracked in [issue #291](https://github.com/mj10612/SecureGateway/issues/291).
The [captured evidence](semantic_context_2.3.1.json) contains model-facing
instructions, masked inputs, recorded interpretations, symbolic response outlines,
per-criterion grading and remaining failures. All content is synthetic.

## What was measured

Each corpus has seventeen languages and four-sentence requests. An interpreter
received only masked requests and the actual gateway instruction. A separate grader
then compared its recorded response with the original labels. Each paragraph earns
one intent point and three constraint points. A complete pass requires all four.
Unknown identities or category types are acceptable symbolic labels; missing
operations, order, negation and conditions fail. Round-trip restoration alone earns
no comprehension points. Every recorded response uses only aliases supplied in its
corresponding input; none invents a reserved alias.

| Corpus / phase | Intent | Constraints | Complete paragraphs |
| --- | ---: | ---: | ---: |
| Development, 2.3.0 baseline | 15/17 | 39/51 | 10/17 |
| Development, core operator changes | 17/17 | 51/51 | 17/17 |
| First complex holdout, before workflow expansion | 14/17 | 29/51 | 4/17 |
| Same corpus, after expansion; development diagnostic | 15/17 | 36/51 | 7/17 |
| Second new holdout, before Korean refinement | 15/17 | 34/51 | 6/17 |
| Korean supplement after predicate refinement | 1/1 | 3/3 | 1/1 |

The development prompts and first holdout informed fixes. The second holdout used
newly authored prompts with varied activities. After its masked Korean text was
inspected, reviewed conditional/negative predicate forms were added and that one
paragraph was interpreted again. This supplement is post-inspection evidence; it
does not change the frozen second-holdout score. Its original labelled criteria
were disclosed only to the grader after interpretation.

These are small, single-interpreter observations. Baseline and candidate evaluations
can use different interpreters; the numbers are descriptive, not statistical or
causal accuracy estimates. The first holdout's Hindi source-order label is stricter
than its source wording for the blocked subset; the evidence retains that caveat
and the original conservative score.

## Resulting behavior and limits

The Korean supplement correctly identifies comparison, evaluation against supplied
conditions, requesting missing evidence instead of choosing without support, and
the prohibition on committing arrangements or contacting participants. Names and
specific options remain aliases.

Independent evaluation still finds missing everyday predicates and relational
forms. Marathi and Telugu lose the main task in the second holdout; several other
languages retain intent while losing one or more conditions. These are recorded
failures, so issue #291 remains open. This release improves readable instructions
and symbolic reasoning; it does not establish universal text comprehension.

The privacy review separately checks explicit rules, prior source mappings, strict
schema data, opaque tool arguments, domain terms and aggressive mode. It caught and
fixed capitalized company-name false negatives and numeric-source restoration
errors. Native Codex tests use a fake upstream; MCP tests exercise local stdio and
schema/call/result restoration. These checks do not prove a live provider chose a
tool or executed a real skill.

## Repeat the procedure

```powershell
python scripts/export_semantic_context.py --corpus tests/fixtures/semantic_holdout2.json --output "$env:TEMP/semantic-blind.json"
```

Give only the exported file to a fresh interpreter and record its task, constraints
and symbolic response. Grade afterward against the corpus using the rubric above.
For an independent measurement, author new prompts without consulting the source,
vocabulary or existing fixtures. The committed corpora now serve as regression data.

The automated suite checks labelled-reference masking, exact restoration and replay
stability for all fifty-one paragraphs, plus targeted operation and privacy cases.
It does not invoke a model or automatically reproduce the subjective scores.
