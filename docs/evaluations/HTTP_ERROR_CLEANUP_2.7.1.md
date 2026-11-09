# Python 3.14 evaluation error-response cleanup - 2.7.1

CI run 42556982270 passed 19 jobs, including installed native artifact lifecycles
on all three platforms. The three Python 3.14 test jobs failed the injected
restore-failure evaluation case: both captured HTTPError 502 objects were left
for implicit cleanup. Python 3.14 reports this as ResourceWarning, and the
warnings-as-errors gate correctly rejected it.

The evaluator now closes HTTPError with its context manager, including the path
that re-raises a failure before any provider capture. Provider-payload privacy
measurement and failed-roundtrip accounting are unchanged. No warning is ignored.

Local proof in an isolated Python 3.14 environment: the existing regression failed
before the fix with the same two unraisable cleanup warnings; after the fix,
`test_reliable_evaluation.py` plus `test_evaluation.py` passed all 23 cases under
`-Werror`. Ruff and mypy pass, and CLI/module/MCP/package versions agree on 2.7.1.
Historical task answers, grades, hashes and reported results are preserved.
