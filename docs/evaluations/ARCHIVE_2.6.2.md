# Historical upgrade archive correction — 2.6.2

The 2.6.1 CI run passed 21/22 jobs. The remaining Windows native lifecycle job
failed while installing the **previous 2.6.0 artifact**, before testing the new
version. Its dictionary hash check failed.

A direct reproduction showed that `git -c core.autocrlf=true archive 56e9883`
rewrites the historical defense dictionary to 462,760 CRLF lines. The original
blob contains no CRLF. Setting `core.autocrlf=false` on this archive command
preserves its exact raw blob hash. This does not modify the historical commit,
published tags or dictionary validation, and does not weaken the new LF policy.

The CI previous-artifact extraction now uses this explicit command setting.
Four actual Git conversion/checkout/archive regression tests pass. Both current
wheel and sdist pass the isolated 2.6.0→2.6.2 install, explicit domain-policy
preservation, tool roundtrip, restart and uninstall path, followed by four native
offline host tests per artifact (Claude Code 2.1.319, Codex CLI 0.167.0). Package,
CLI/MCP and health version reporting agree on 2.6.2. The final remote CI run is
reported separately; this local proof is not a claim that it already passed.
