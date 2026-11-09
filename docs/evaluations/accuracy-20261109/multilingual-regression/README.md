# Superseded adapter diagnostic

This run used a worker instruction ending with “Return only your interpretation
as plain text.” That could cause a paraphrase of the request while the independent
rubric required the requested plan, clarification or other actual response.
The resulting task-performance scores are **invalid as task-performance evidence**
and must not be used as a baseline or an engine-quality comparison.

The original requests, first responses, grades and metadata correction remain
unchanged for diagnosis. HTTP payload protection, exact restoration and replay
are separate local measurements; they do not establish model comprehension.

The corrected adapter explicitly requests the answer to the supplied task and
forbids merely paraphrasing its meaning. A new run is recorded in
[`../multilingual-task-response-retest/`](../multilingual-task-response-retest/).
The old responses/grades were not repaired, relabeled as a successful trial or
reused as the corrected run's first answers. This remains an existing regression
corpus, not an untouched holdout.
