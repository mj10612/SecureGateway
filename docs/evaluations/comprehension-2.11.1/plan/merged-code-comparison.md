# Candidate source comparison after rebase

Compared base `5b6dc62` to rebased `origin/main`. Candidate-specific `if issue == N` tests and bodies have byte-identical source text and identical Python ASTs for #312 (3 arms), #314 (1), #315 (2), and #317 (3). `numeric_context.py`, `structure_parser.py`, `gateway_vocabulary.py`, `gateway_name_vocabulary.py`, and `experiment_korean.py` have no Git diff.

This is not a claim that the complete shared `experiment_profiles.py` is byte-identical: it changed for other candidates and in shared methods. AST equality ignores formatting and does not by itself prove equivalent behavior of shared code; all previous results remain subject to that limitation. #310, #311, #316, and #318 were changed and prior evaluations of these candidates are withdrawn.
