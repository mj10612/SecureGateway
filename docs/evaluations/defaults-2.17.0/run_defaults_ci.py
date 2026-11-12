"""CI privacy comparison: 2.17.0 gateway-setting defaults vs the old (all-off) default.

Both reports are generated in-process (release profile, legacy corpus) with a gateway
constructed from ``resolve_settings`` features, then compared with
``secure-gateway evaluate compare --baseline docs/evaluations/issue324-2.7.0/legacy-privacy/report.json``.

    uv run --locked --all-extras python docs/evaluations/defaults-2.17.0/run_defaults_ci.py
"""
import json
import shutil
import subprocess
from pathlib import Path

from secure_gateway import __version__, evaluation
from secure_gateway.gateway_features import resolve_settings

HERE = Path(__file__).resolve().parent
BASELINE = HERE.parent / "issue324-2.7.0" / "legacy-privacy" / "report.json"


def run(name, features):
    original = evaluation.PrivacyGateway

    class FeatureGateway(original):
        def __init__(self, *args, **kwargs):
            kwargs["features"] = features
            super().__init__(*args, **kwargs)

    out = HERE / name
    if out.exists():
        shutil.rmtree(out)
    evaluation.PrivacyGateway = FeatureGateway
    try:
        report = evaluation.run_privacy(evaluation.load_corpus(None), output_dir=out / "report",
                                        profile="release", max_seconds=600)
    finally:
        evaluation.PrivacyGateway = original
    proc = subprocess.run([shutil.which("secure-gateway"), "evaluate", "compare", "--baseline", str(BASELINE),
                           "--candidate", str(out / "report" / "report.json")], capture_output=True, timeout=120)
    comparison = json.loads(proc.stdout.decode("utf-8"))
    (out / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
    return {"features": list(features.enabled_names()), "report_status": report["status"],
            "compare_exit_code": proc.returncode, "comparable": comparison["comparable"],
            "regression": comparison["regression"], "new_exposures": len(comparison["new_exposures"]),
            "resolved_exposures": len(comparison["resolved_exposures"]),
            "integrity_regressions": len(comparison["integrity_regressions"]),
            "metrics": comparison["candidate_metrics"]}


def main():
    new, _ = resolve_settings({}, environ={})
    old, _ = resolve_settings({}, environ={}, all_off=True)
    result = {"secure_gateway_version": __version__, "baseline": "docs/evaluations/issue324-2.7.0/legacy-privacy/report.json",
              "new_default": run("new-default", new), "old_default": run("old-default", old)}
    (HERE / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: {x: v[x] for x in v if x != "metrics"} if isinstance(v, dict) else v
                      for k, v in result.items()}, indent=1))


if __name__ == "__main__":
    main()
