"""Evidence for the 2.17.0 #310 predicate/premodifier guard (no model call).

(a) Re-captures the 144 frozen #310/#316/#318 comprehension cases with the current code
    (C = all off, J = adopted features + case policy) and compares them, alias-canonicalized,
    with the original frozen C and D1 inputs.
(b) Re-runs offline protection (baseline / single / joint) on the three ADOPT protection sets.

    uv run --locked --all-extras python docs/evaluations/defaults-2.17.0/verify_310_fix.py
"""
import importlib.util
import json
from pathlib import Path

from secure_gateway import __version__, evaluation
from secure_gateway.gateway_features import GatewayFeatures

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("run_joint", HERE.parent / "joint-adopted-2.16" / "run_joint.py")
rj = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rj)
OUT = HERE / "fix-310"


def comprehension_inputs():
    cases, _ = rj.source_cases()
    changed, per_source = [], {}
    for c in cases:
        new_c = rj.canonical(rj.capture(c["original"], GatewayFeatures(), c["forced_terms"]))
        new_j = rj.canonical(rj.capture(c["original"], rj.joint_features(c["trusted_local_policy"]), c["forced_terms"]))
        old_c, old_d = (rj.canonical(c["original_arms"][k]) for k in ("C", "D"))
        stats = per_source.setdefault(str(c["source"]), {"cases": 0, "C_equal": 0, "J_equal_original_D": 0})
        stats["cases"] += 1
        stats["C_equal"] += new_c == old_c
        stats["J_equal_original_D"] += new_j == old_d
        if new_c != old_c or new_j != old_d:
            changed.append({"case_id": c["case_id"], "C_changed": new_c != old_c, "J_vs_original_D_changed": new_j != old_d,
                            "J_differs_from_new_C": new_j != new_c,
                            "original_D_input": c["original_arms"]["D"]["input"],
                            "new_J": rj.canonical(rj.capture(c["original"], rj.joint_features(c["trusted_local_policy"]),
                                                             c["forced_terms"])).split("\n", 1)[1]})
    return {"per_source": per_source, "changed": changed}


def protection():
    result = {}
    for source in rj.SOURCES:
        cases = rj.load(rj.EVAL / str(source) / "plan" / rj.PROTECTION_SETS[source])["cases"]
        records = []
        for c in cases:
            policy = c.get("trusted_local_policy")
            inp = rj._makecase(c)
            rec = {}
            for arm, features in (("baseline", GatewayFeatures()), ("single", rj.single_features(source, policy)),
                                  ("joint", rj.joint_features(policy))):
                with rj.gateway_with(features):
                    rec[arm] = rj._encode(evaluation._capture_case(inp, max_seconds=40))
            records.append(rec)
        arms = {arm: {"exposed": sum(rj._exposed(s) for r in records for s in r[arm]["secrets"]),
                      "overmasked": sum(p["overmasked"] for r in records for p in r[arm]["public"]),
                      "exact_restore": sum(r[arm]["roundtrip"] for r in records)} for arm in ("baseline", "single", "joint")}
        result[str(source)] = {"cases": len(cases), "sensitive_spans": sum(len(r["baseline"]["secrets"]) for r in records),
                               "public_spans": sum(len(r["baseline"]["public"]) for r in records), "arms": arms,
                               "single_vs_baseline": rj._compare(records, "baseline", "single"),
                               "joint_vs_baseline": rj._compare(records, "baseline", "joint")}
    return result


def main():
    doc = {"secure_gateway_version": __version__, "comprehension_inputs": comprehension_inputs(),
           "protection": protection()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"per_source": doc["comprehension_inputs"]["per_source"],
                      "changed": [x["case_id"] for x in doc["comprehension_inputs"]["changed"]],
                      "protection": {k: {"single": v["single_vs_baseline"], "joint": v["joint_vs_baseline"],
                                         "arms": v["arms"]} for k, v in doc["protection"].items()}}, indent=1))


if __name__ == "__main__":
    main()
