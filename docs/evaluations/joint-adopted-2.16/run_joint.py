"""Joint real-LLM evaluation of the adopted candidates #310, #316 B and #318 (2.16).

Arms: A (original text), C (all features off), J (contextual_name_spans on, plus
the case's own trusted #316/#318 policy when the case provides one). Inputs are
captured with the per-session feature flags of #354 (``GatewaySession(features=...)``),
not with the process-global experiment profiles. Transport: the #364 lean session
(``evaluation_batch.run_lean_worker``), one fresh call per interpretation, grading
batched by 2 with per-case quote verification and one single-case re-grade
(same logic as ``comprehension-2.11.1/plan/run_309_luna.py``).

    uv run --locked --all-extras python docs/evaluations/joint-adopted-2.16/run_joint.py --prepare
        captures, offline protection, CI compare, pre-checks, attack jobs; no model call
    uv run --locked --all-extras python docs/evaluations/joint-adopted-2.16/run_joint.py --freeze
        once, before any model call
    uv run --locked --all-extras python docs/evaluations/joint-adopted-2.16/run_joint.py --run
        resumable; stops cleanly (exit 3) on UsageLimitReached
    uv run --locked --all-extras python docs/evaluations/joint-adopted-2.16/run_joint.py --run-attack
        optional secondary #318 catalogue attack (descriptive, not in the decision rule)
    uv run --locked --all-extras python docs/evaluations/joint-adopted-2.16/run_joint.py --report

Plumbing check without any model call (fake adapter, outputs outside this directory):
    ... run_joint.py --dry-run <dir outside docs/> [--fake-limit-after N]
"""
import argparse
import concurrent.futures
import contextlib
import hashlib
import json
import random
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from secure_gateway import __version__, evaluation, gateway, evaluation_batch as eb
from secure_gateway.evaluation_worker import validate_request, validate_result
from secure_gateway.gateway_features import GatewayFeatures

HERE = Path(__file__).resolve().parent
EVAL = HERE.parent / "comprehension-2.11.1"
CI_BASELINE = HERE.parent / "issue324-2.7.0" / "legacy-privacy" / "report.json"
PREREG = HERE / "preregistration.json"
PLAN, CAPTURES, OFFLINE, ATTACK = HERE / "plan", HERE / "captures", HERE / "offline", HERE / "attack"
RUN_DIR = HERE / "run"
TAG = "joint-adopted-2.16"
SOURCES = (310, 316, 318)
PROTECTION_SETS = {310: "introducer-cases.json", 316: "protection-correction-sensitive.json",
                   318: "protection-bundle-table.json"}
ADOPT_OFFLINE = {310: "310/offline/310/summary.json", 316: "316/offline/316-correction-sensitive/summary.json",
                 318: "318/offline/318-bundle-table/summary.json"}
MODEL, EFFORT = eb.DEFAULT_EVAL_MODEL, "low"
ARMS = ("A", "C", "J")
GRADE_BATCH, WORKERS, SEED = 2, 3, 20261216
ATTACK_SEED = 20261216318
GRADE_SYSTEM = ("Grade each blinded response independently. Evidence must be a nonempty exact verbatim "
                "excerpt of the corresponding response, without added quotation marks; if a violation is "
                "absence, quote enough of that actual response to support the judgment. Do not use tools.")
RETRY = ("The previous quote validation failed. Supply only exact nonempty excerpts from the corresponding "
         "response for every verdict.")
ATTACK_SYSTEM = ("Use only the provided information. Return JSON only: {\"ranking\": [identifier, ...], "
                 "\"rationale\": string}. Rank at most three distinct catalogue identifiers. Use an empty "
                 "ranking to abstain. Do not use tools.")
ATTACK_QUESTION = ("Which catalogue identifier best matches the subject? Rank up to three identifiers, "
                   "or abstain if insufficient evidence.")
# Budget constants: lean fixed input measured in #364; per-item content as in run_309_luna.py.
FIXED_INPUT, INTERPRET_CONTENT, GRADE_CONTENT = 7070, 400, 2000


# Utilities -------------------------------------------------------------------

def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def fsha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def rows(path):
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def append(path, row):
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def rel(path):
    return path.resolve().relative_to(HERE.parents[2]).as_posix()


# Features --------------------------------------------------------------------

def policy_kind(policy):
    if not policy:
        return None
    if "trusted_project" in policy:
        return "scoped_corrections"
    if "document_sha256" in policy:
        return "attribute_bundle"
    raise ValueError("Unknown trusted policy kind")


def joint_features(policy):
    """All adopted features on; policy-bound ones take the case's own trusted policy."""
    kwargs = {"contextual_name_spans": True}
    kind = policy_kind(policy)
    if kind:
        kwargs[kind] = policy
    return GatewayFeatures(**kwargs)


def single_features(source, policy):
    if source == 310:
        return GatewayFeatures(contextual_name_spans=True)
    kind = policy_kind(policy)
    if kind != {316: "scoped_corrections", 318: "attribute_bundle"}[source]:
        raise ValueError("Case policy does not match its candidate")
    return GatewayFeatures(**{kind: policy})


def features_doc(features):
    return {"enabled": list(features.enabled_names())}


def capture(text, features, forced=()):
    session = gateway.GatewaySession(natural_language="auto", features=features)
    session.forced_rules = lambda: tuple(forced)
    payload = session.request({"model": "fixture", "input": [{"role": "user", "content": text}]})
    aliases = {m.surrogate: m.original for m in session.session.reverse_store.values()}
    return {"instructions": payload.get("instructions", ""), "input": payload["input"][0]["content"],
            "aliases": aliases}


def canonical(arm):
    """Model-visible text with every alias replaced by its bound original in brackets.

    Numeric aliases are random per capture, so arms are compared on this form
    (same masked set, same positions, same bindings) rather than on raw bytes.
    """
    aliases = arm["aliases"]
    if not aliases:
        return arm["instructions"] + "\n" + arm["input"]
    pattern = re.compile("|".join(re.escape(k) for k in sorted(aliases, key=len, reverse=True)))
    return arm["instructions"] + "\n" + pattern.sub(lambda m: "⟦" + aliases[m.group(0)] + "⟧", arm["input"])


@contextlib.contextmanager
def gateway_with(features):
    """Run evaluation._capture_case/run_privacy with a gateway constructed with ``features``.

    Uses the #354 constructor argument (``PrivacyGateway(features=...)``); no
    process-global profile is involved.
    """
    original = evaluation.PrivacyGateway

    class FeatureGateway(original):
        def __init__(self, *args, **kwargs):
            kwargs["features"] = features
            super().__init__(*args, **kwargs)

    evaluation.PrivacyGateway = FeatureGateway
    try:
        yield
    finally:
        evaluation.PrivacyGateway = original


# Cases and captures ----------------------------------------------------------

def source_cases():
    cases, provenance = [], {}
    for source in SOURCES:
        plan = EVAL / str(source) / "plan"
        manifest_path = EVAL / str(source) / "comprehension" / "manifest.json"
        frozen = load(plan / "cases.json")["cases"]
        manifest = load(manifest_path)
        if manifest["source_cases_sha256"] != sha(frozen):
            raise SystemExit(f"{source}: frozen cases differ from the comprehension manifest")
        by_id = {c["case_id"]: c for c in manifest["cases"]}
        provenance[str(source)] = {"cases_file": rel(plan / "cases.json"), "cases_sha256": fsha(plan / "cases.json"),
                                   "manifest": rel(manifest_path), "manifest_sha256": fsha(manifest_path),
                                   "rubric_sha256": manifest["rubric_sha256"], "cases": len(frozen),
                                   "negative_controls": sum(c["negative_control"] for c in frozen)}
        for c in frozen:
            original = by_id[c["id"]]
            for key in ("original", "expected", "negative_control", "applicable"):
                if original[key] != c[key]:
                    raise SystemExit(f"{source}:{c['id']}: manifest field differs: {key}")
            cases.append({"case_id": f"{source}:{c['id']}", "source": source, "source_case_id": c["id"],
                          "original": c["original"], "expected": c["expected"],
                          "negative_control": c["negative_control"], "applicable": c["applicable"],
                          "trusted_local_policy": c.get("trusted_local_policy"),
                          "forced_terms": c.get("forced_terms", []),
                          "original_arms": {"C": original["arms"]["C"], "D": original["arms"]["D1"]}})
    return cases, provenance


def criterion_definitions():
    merged = {}
    for source in SOURCES:
        for key, value in load(EVAL / str(source) / "comprehension" / "manifest.json")["criterion_definitions"].items():
            if key in merged and merged[key] != value:
                raise SystemExit("criterion definitions differ across candidates: " + key)
            merged[key] = value
    return merged


def build_captures(cases):
    entries = []
    for c in cases:
        base = capture(c["original"], GatewayFeatures(), c["forced_terms"])
        joint = capture(c["original"], joint_features(c["trusted_local_policy"]), c["forced_terms"])
        entries.append({"case_id": c["case_id"], "source": c["source"], "source_case_id": c["source_case_id"],
                        "original": c["original"], "expected": c["expected"],
                        "negative_control": c["negative_control"], "applicable": c["applicable"],
                        "joint_features": features_doc(joint_features(c["trusted_local_policy"])),
                        "arms": {"A": {"instructions": base["instructions"], "input": c["original"], "aliases": {}},
                                 "C": base, "J": joint}})
    return entries


def precheck(cases, entries):
    per_case, summary = [], {}
    for c, e in zip(cases, entries):
        orig_c, orig_d = (canonical(c["original_arms"][k]) for k in ("C", "D"))
        new_c, new_j = canonical(e["arms"]["C"]), canonical(e["arms"]["J"])
        per_case.append({"case_id": e["case_id"], "source": e["source"], "negative_control": e["negative_control"],
                         "original_D_differs_from_C": orig_d != orig_c, "J_differs_from_C": new_j != new_c,
                         "C_equals_original_C": new_c == orig_c, "J_equals_original_D": new_j == orig_d,
                         "instructions_equal": e["arms"]["C"]["instructions"] == e["arms"]["J"]["instructions"]})
    for key, subset in [(str(s), [x for x in per_case if x["source"] == s]) for s in SOURCES] + [("pooled", per_case)]:
        nc = [x for x in subset if not x["negative_control"]]
        summary[key] = {
            "cases": len(subset), "non_control": len(nc),
            "non_control_J_differs": sum(x["J_differs_from_C"] for x in nc),
            "non_control_J_differs_share": round(sum(x["J_differs_from_C"] for x in nc) / len(nc), 4) if nc else None,
            "controls_J_differs": sum(x["J_differs_from_C"] for x in subset if x["negative_control"]),
            "original_D_differs": sum(x["original_D_differs_from_C"] for x in subset),
            "mismatch_D_differed_J_does_not": [x["case_id"] for x in subset
                                               if x["original_D_differs_from_C"] and not x["J_differs_from_C"]],
            "extra_J_differs_D_did_not": [x["case_id"] for x in subset
                                          if x["J_differs_from_C"] and not x["original_D_differs_from_C"]],
            "C_drift_from_original_C": [x["case_id"] for x in subset if not x["C_equals_original_C"]],
            "J_not_equal_original_D": [x["case_id"] for x in subset if not x["J_equals_original_D"]],
            "instructions_differ": [x["case_id"] for x in subset if not x["instructions_equal"]],
        }
    return {"method": "Arms compared after replacing every alias with its bound original (numeric aliases are "
                      "random per capture); instructions included. original_* refers to the frozen 2.11.1 "
                      "comprehension manifests (C and D1).",
            "summary": summary, "cases": per_case}


# Offline protection ------------------------------------------------------------

def _encode(raw):
    return {"roundtrip": raw["roundtrip"],
            "payload_sha256": hashlib.sha256(json.dumps(raw["outbound"], sort_keys=True,
                                                        ensure_ascii=False).encode("utf-8")).hexdigest(),
            "secrets": [{"full": x["full_exposure"], "partial": x["partial_exposure"],
                         "ambiguous": x.get("alignment_ambiguous", False)} for x in raw["secrets"]],
            "public": [{"overmasked": x["overmasked"], "ambiguous": x.get("alignment_ambiguous", False)}
                       for x in raw["public"]]}


def _makecase(c):
    # Identical to comprehension-2.11.1/plan/offline_protection.py makecase.
    field = ["input", 0, "content"]
    secrets = [{"path": field, "start": s["start"], "end": s["end"],
                "fragments": sorted({s["text"][i:i + 2] for i in range(len(s["text"]) - 1)}),
                "label": "synthetic", "policy": "contextual", "severity": "standard"} for s in c["sensitive_spans"]]
    public = [{"path": field, "start": s["start"], "end": s["end"], "label": "synthetic-public"}
              for s in c["public_spans"]]
    return {"id": c["id"], "language": "en", "language_mode": "auto", "domain": "general", "dialect": "codex",
            "payload": {"model": "fixture", "input": [{"role": "user", "content": c["original"]}]},
            "echo_path": field, "task_path": field, "secrets": secrets, "public": public,
            "forced_terms": c.get("forced_terms", []), "rubric": [], "human_text": "", "smoke": True}


def _exposed(x):
    return x["full"] or x["partial"] or x["ambiguous"]


def _compare(records, a, b):
    newly_exposed = protected = 0
    for rec in records:
        for x, y in zip(rec[a]["secrets"], rec[b]["secrets"]):
            newly_exposed += (not _exposed(x)) and _exposed(y)
            protected += _exposed(x) and not _exposed(y)
    return {"newly_exposed": newly_exposed, "newly_protected": protected}


def offline_set(source):
    path = EVAL / str(source) / "plan" / PROTECTION_SETS[source]
    cases = load(path)["cases"]
    records = []
    for c in cases:
        policy = c.get("trusted_local_policy")
        inp = _makecase(c)
        rec = {"id": c["id"]}
        for arm, features in (("baseline", GatewayFeatures()), ("single", single_features(source, policy)),
                              ("joint", joint_features(policy))):
            with gateway_with(features):
                rec[arm] = _encode(evaluation._capture_case(inp, max_seconds=40))
        records.append(rec)
    stats = {}
    for arm in ("baseline", "single", "joint"):
        stats[arm] = {"exposed": sum(_exposed(s) for r in records for s in r[arm]["secrets"]),
                      "overmasked": sum(p["overmasked"] for r in records for p in r[arm]["public"]),
                      "exact_restore": sum(r[arm]["roundtrip"] for r in records)}
    single_vs_base, joint_vs_base = _compare(records, "baseline", "single"), _compare(records, "baseline", "joint")
    joint_vs_single = _compare(records, "single", "joint")
    adopted = load(EVAL / ADOPT_OFFLINE[source])
    summary = {
        "source": source, "dataset": rel(path), "dataset_sha256": fsha(path), "cases": len(cases),
        "sensitive_spans": sum(len(r["baseline"]["secrets"]) for r in records),
        "public_spans": sum(len(r["baseline"]["public"]) for r in records),
        "arms": stats,
        "single_vs_baseline": {**single_vs_base,
                               "overmask_increase": stats["single"]["overmasked"] - stats["baseline"]["overmasked"]},
        "joint_vs_baseline": {**joint_vs_base,
                              "overmask_increase": stats["joint"]["overmasked"] - stats["baseline"]["overmasked"]},
        "joint_vs_single": joint_vs_single,
        "joint_payload_differs_from_single": sum(r["single"]["payload_sha256"] != r["joint"]["payload_sha256"]
                                                 for r in records),
        "adopt_decision_reference": {"file": rel(EVAL / ADOPT_OFFLINE[source]),
                                     "newly_protected": adopted["newly_protected"],
                                     "newly_exposed": adopted["newly_exposed"],
                                     "baseline_overmasked": adopted["baseline_overmasked"],
                                     "candidate_overmasked": adopted["candidate_overmasked"],
                                     "baseline_exact_restore": adopted["baseline_exact_restore"],
                                     "candidate_exact_restore": adopted["candidate_exact_restore"]},
    }
    ref = summary["adopt_decision_reference"]
    summary["single_reproduces_adopt_numbers"] = (
        single_vs_base["newly_protected"] == ref["newly_protected"]
        and single_vs_base["newly_exposed"] == ref["newly_exposed"]
        and stats["baseline"]["overmasked"] == ref["baseline_overmasked"]
        and stats["single"]["overmasked"] == ref["candidate_overmasked"]
        and stats["baseline"]["exact_restore"] == ref["baseline_exact_restore"]
        and stats["single"]["exact_restore"] == ref["candidate_exact_restore"])
    summary["gate"] = {
        "zero_newly_exposed_vs_baseline": joint_vs_base["newly_exposed"] == 0,
        "no_interaction_loss": joint_vs_base["newly_protected"] >= single_vs_base["newly_protected"],
        "overmask_increase_le_2": summary["joint_vs_baseline"]["overmask_increase"] <= 2,
        "exact_restore_not_lower": (stats["joint"]["exact_restore"] >= stats["baseline"]["exact_restore"]
                                    and stats["joint"]["exact_restore"] >= stats["single"]["exact_restore"]),
    }
    summary["gate_passed"] = all(summary["gate"].values())
    write(OFFLINE / str(source) / "occurrences.json", {"cases": records})
    write(OFFLINE / str(source) / "summary.json", summary)
    return summary


def ci_policies():
    # The earlier per-candidate CI runs used cases[0] of each replacement set as the frozen policy.
    return (load(EVAL / "316" / "plan" / PROTECTION_SETS[316])["cases"][0]["trusted_local_policy"],
            load(EVAL / "318" / "plan" / PROTECTION_SETS[318])["cases"][0]["trusted_local_policy"])


def ci_joint():
    scoped, bundle = ci_policies()
    features = GatewayFeatures(contextual_name_spans=True, scoped_corrections=scoped, attribute_bundle=bundle)
    out = OFFLINE / "ci-joint"
    out.mkdir(parents=True, exist_ok=True)
    with gateway_with(features):
        result = evaluation.run_privacy(evaluation.load_corpus(None), output_dir=out / "ci-candidate",
                                        profile="release", max_seconds=600)
    doc = {"features": features_doc(features),
           "policies": "cases[0] trusted_local_policy of the #316 and #318 replacement protection sets "
                       "(same convention as the single-candidate CI runs)",
           "report_status": result["status"]}
    if result["status"] != "completed":
        doc["status"] = "incomplete"
        return doc
    exe = shutil.which("secure-gateway")
    if not exe:
        doc.update(status="incomplete", error_category="CliUnavailable")
        return doc
    proc = subprocess.run([exe, "evaluate", "compare", "--baseline", str(CI_BASELINE),
                           "--candidate", str(out / "ci-candidate" / "report.json")], capture_output=True, timeout=120)
    try:
        comparison = json.loads(proc.stdout.decode("utf-8"))
    except (ValueError, UnicodeError):
        doc.update(status="incomplete", exit_code=proc.returncode, error_category="ComparisonOutputInvalid")
        return doc
    write(out / "ci-comparison.json", comparison)
    doc.update(status="passed" if proc.returncode == 0 and comparison.get("comparable")
               and not comparison.get("regression") else "failed",
               exit_code=proc.returncode, new_exposure_count=len(comparison.get("new_exposures", [])),
               integrity_regression_count=len(comparison.get("integrity_regressions", [])),
               command="secure-gateway evaluate compare --baseline docs/evaluations/issue324-2.7.0/legacy-privacy/"
                       "report.json --candidate docs/evaluations/joint-adopted-2.16/offline/ci-joint/ci-candidate/"
                       "report.json")
    return doc


# Jobs ------------------------------------------------------------------------

def build_jobs(manifest):
    jobs = []
    for case in manifest["cases"]:
        for arm in ARMS:
            a = case["arms"][arm]
            request = {"role": "interpret", "job_id": sha([TAG, case["case_id"], arm])[:32],
                       "model": MODEL, "max_output_tokens": 512, "reasoning_effort": EFFORT,
                       "messages": [{"role": "system", "content": a["instructions"]},
                                    {"role": "user", "content": a["input"]}]}
            jobs.append({"case_id": case["case_id"], "arm": arm, "request": request})
    random.Random(SEED).shuffle(jobs)
    return jobs


def build_attack(manifest):
    """#318 catalogue attack jobs on the joint captures (same protocol as run_inference_attack.py)."""
    frozen = {c["id"]: c for c in load(EVAL / "318" / "plan" / "cases.json")["cases"]}
    reference = load(EVAL / "318" / "inference-attack" / "manifest.json")["cases"]
    gold, jobs = {}, []
    for c in manifest["cases"]:
        if c["source"] != 318:
            continue
        case = frozen[c["source_case_id"]]
        catalogue = case["catalogue"]
        order = list(catalogue["rows"])
        # Same per-case permutation seed as the original attack, so row order matches it.
        random.Random(int(sha([318, c["source_case_id"], "catalogue"])[:16], 16)).shuffle(order)
        ids = [r[0] for r in order]
        if len(set(ids)) != 8 or case["target_id"] not in ids or ids != reference[c["source_case_id"]]["ids"]:
            raise SystemExit("attack catalogue permutation differs from the original attack")
        gold[c["case_id"]] = {"target": case["target_id"], "ids": ids}
        for arm in ("prior", "C", "J"):
            task = {"catalogue": {"columns": catalogue["columns"], "rows": order}, "question": ATTACK_QUESTION}
            if arm != "prior":
                task["provider_visible_payload"] = {k: c["arms"][arm][k] for k in ("instructions", "input")}
            request = {"role": "interpret", "job_id": sha([TAG, c["case_id"], "attack", arm])[:32], "model": MODEL,
                       "max_output_tokens": 512, "reasoning_effort": EFFORT,
                       "messages": [{"role": "system", "content": ATTACK_SYSTEM},
                                    {"role": "user", "content": json.dumps(task, ensure_ascii=False)}]}
            jobs.append({"case_id": c["case_id"], "arm": arm, "request": request})
    random.Random(ATTACK_SEED).shuffle(jobs)
    return {"seed": ATTACK_SEED, "cases": gold, "jobs": jobs, "status": "prepared; not run",
            "protocol": "catalogue-only prior and paired C/J; rows identically permuted per case (same permutation "
                        "as 318/inference-attack); gold never passed to attacker; secondary and descriptive only"}


def budget(cases, attack_jobs):
    main = eb.estimate_budget(interpret_jobs=len(cases) * len(ARMS), grade_cases=len(cases), interpret_batch=1,
                              grade_batch=GRADE_BATCH, fixed_input_tokens=FIXED_INPUT,
                              interpret_content_tokens=INTERPRET_CONTENT, grade_content_tokens=GRADE_CONTENT)
    attack = eb.estimate_budget(interpret_jobs=attack_jobs, grade_cases=0, interpret_batch=1, grade_batch=1,
                                fixed_input_tokens=FIXED_INPUT, interpret_content_tokens=INTERPRET_CONTENT,
                                grade_content_tokens=0, regrade_rate=0)
    return {"comprehension": main, "optional_attack": attack,
            "inputs": {"fixed_input_tokens": FIXED_INPUT, "interpret_content_tokens": INTERPRET_CONTENT,
                       "grade_content_tokens": GRADE_CONTENT, "regrade_rate": 0.05,
                       "source": "lean fixed input from docs/EVALUATION_COST.md; content constants as run_309_luna.py"},
            "reference": "#309 luna run measured 30,173 raw tokens per case with 3 arms (339 calls)"}


# Prepare / freeze ----------------------------------------------------------------

def prepare():
    if (RUN_DIR / "freeze.json").exists():
        raise SystemExit("already frozen; prepared inputs are immutable")
    for path in (CAPTURES, OFFLINE, ATTACK):
        if path.exists():
            shutil.rmtree(path)
    cases, provenance = source_cases()
    write(PLAN / "cases.json", {
        "description": "Union of the frozen #310, #316 and #318 comprehension cases; case_id = '<source>:<id>'. "
                       "trusted_local_policy is each case's own frozen local policy (none for #310).",
        "provenance": provenance,
        "cases": [{k: v for k, v in c.items() if k != "original_arms"} for c in cases]})
    entries = build_captures(cases)
    manifest = {"schema_version": 1, "tag": TAG, "secure_gateway_version": __version__,
                "capture": "GatewaySession(natural_language='auto', features=GatewayFeatures(...)); "
                           "C = GatewayFeatures(); J = contextual_name_spans + the case's trusted policy",
                "cases_sha256": fsha(PLAN / "cases.json"), "criterion_definitions": criterion_definitions(),
                "cases": entries}
    write(CAPTURES / "manifest.json", manifest)
    pre = precheck(cases, entries)
    write(PLAN / "precheck.json", pre)
    offline = {str(s): offline_set(s) for s in SOURCES}
    ci = ci_joint()
    write(OFFLINE / "ci-joint" / "summary.json", ci)
    gate = {"per_set": {k: v["gate_passed"] for k, v in offline.items()}, "ci_passed": ci["status"] == "passed"}
    gate["passed"] = all(gate["per_set"].values()) and gate["ci_passed"]
    write(OFFLINE / "summary.json", {"sets": offline, "ci": ci, "gate": gate})
    attack = build_attack(load(CAPTURES / "manifest.json"))
    write(ATTACK / "manifest.json", attack)
    write(PLAN / "budget.json", budget(entries, len(attack["jobs"])))
    print(json.dumps({"cases": {str(s): sum(e["source"] == s for e in entries) for s in SOURCES},
                      "precheck": {k: {x: v[x] for x in ("non_control", "non_control_J_differs",
                                                         "non_control_J_differs_share")}
                                   for k, v in pre["summary"].items()},
                      "offline_gate": gate, "jobs": len(build_jobs(manifest))}, indent=1))


def frozen_files():
    return [PREREG, PLAN / "cases.json", PLAN / "precheck.json", PLAN / "budget.json", CAPTURES / "manifest.json",
            OFFLINE / "summary.json", ATTACK / "manifest.json", Path(__file__).resolve()]


def freeze(run_dir):
    if (run_dir / "freeze.json").exists():
        raise SystemExit("already frozen")
    if not all(p.exists() for p in frozen_files()):
        raise SystemExit("run --prepare first")
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = load(CAPTURES / "manifest.json")
    jobs = build_jobs(manifest)
    (run_dir / "frozen-preregistration.json").write_bytes(PREREG.read_bytes())
    doc = {"tag": TAG, "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "model": MODEL, "reasoning_effort": EFFORT, "arms": list(ARMS),
           "transport": {"adapter": "secure_gateway.evaluation_batch.run_lean_worker",
                         "adapter_source_sha256": eb.adapter_hash(), "secure_gateway_version": __version__,
                         "interpretation": "one fresh lean call per (case, arm)",
                         "grading": f"lean, batch {GRADE_BATCH}, per-case quote check, one single-case re-grade",
                         "disabled_features": list(eb.LEAN_DISABLED_FEATURES)},
           "files_sha256": {rel(p): fsha(p) for p in frozen_files()},
           "jobs_sha256": sha(jobs), "jobs": len(jobs), "cases": len(manifest["cases"]), "shuffle_seed": SEED,
           "budget_estimate": load(PLAN / "budget.json")}
    write(run_dir / "freeze.json", doc)
    print(json.dumps({"frozen": rel(run_dir / "freeze.json") if run_dir.is_relative_to(HERE.parents[2])
                      else str(run_dir / "freeze.json"), "jobs": len(jobs)}, indent=1))


def verified(run_dir):
    if not (run_dir / "freeze.json").exists():
        raise SystemExit("not frozen: run --freeze first")
    f = load(run_dir / "freeze.json")
    root = HERE.parents[2]
    for name, digest in f["files_sha256"].items():
        if fsha(root / name) != digest:
            raise SystemExit("frozen file changed: " + name)
    if fsha(run_dir / "frozen-preregistration.json") != f["files_sha256"][rel(PREREG)]:
        raise SystemExit("run copy of preregistration changed")
    if f["transport"]["adapter_source_sha256"] != eb.adapter_hash():
        raise SystemExit("adapter changed since freeze")
    manifest = load(CAPTURES / "manifest.json")
    jobs = build_jobs(manifest)
    if sha(jobs) != f["jobs_sha256"] or MODEL != f["model"]:
        raise SystemExit("jobs differ from freeze")
    return manifest, jobs


# Model calls -------------------------------------------------------------------

def call(request):
    started = time.monotonic()
    try:
        result = eb.run_lean_worker(request)
        return {"status": "completed", "result": result, "elapsed_seconds": time.monotonic() - started}
    except eb.UsageLimitReached:
        return {"status": "limit"}
    except ValueError as exc:
        return {"status": "failed", "error": str(exc), "elapsed_seconds": time.monotonic() - started}


def stop_for_limit():
    print("USAGE LIMIT reached - stopped cleanly; rerun the same command to resume.", flush=True)
    sys.exit(3)


def run_calls(jobs, path, failed_path, label):
    done = {}
    for r in rows(path):
        meta = r["result"]["metadata"]
        if (r["status"] != "completed" or meta.get("tool_events") != 0 or meta.get("fresh_session") is not True
                or meta.get("requested_model") != MODEL or r["result"]["job_id"] != r["job_id"]):
            raise SystemExit("invalid saved response")
        done[r["job_id"]] = r
    pending = [j for j in jobs if j["request"]["job_id"] not in done]
    print(label, "saved", len(done), "pending", len(pending), flush=True)
    for pos in range(0, len(pending), WORKERS):
        chunk = pending[pos:pos + WORKERS]
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
            results = list(pool.map(lambda j: call(j["request"]), chunk))
        limit = False
        for job, res in zip(chunk, results):
            row = {"job_id": job["request"]["job_id"], "case_id": job["case_id"], "arm": job["arm"], **res}
            if res["status"] == "completed":
                append(path, row)
            elif res["status"] == "limit":
                limit = True
            else:
                append(failed_path, row)
        if limit:
            stop_for_limit()
        if (pos // WORKERS) % 10 == 0 or pos + WORKERS >= len(pending):
            print(label, "done", min(pos + WORKERS, len(pending)), "of", len(pending), flush=True)
    answers = {(r["case_id"], r["arm"]): r["result"]["response"] for r in rows(path)}
    missing = [j for j in jobs if (j["case_id"], j["arm"]) not in answers]
    if missing:
        raise SystemExit(f"{len(missing)} {label} calls failed; rerun to retry them")
    return answers


def grade_request(m, case, answers):
    cid = case["case_id"]
    labels = list(ARMS)
    random.Random(int(sha([TAG, cid])[:16], 16)).shuffle(labels)
    blind = {f"R{i + 1}": x for i, x in enumerate(labels)}
    responses, criteria = {}, []
    for label, arm in blind.items():
        a = case["arms"][arm]
        responses[label] = {"response": answers[(cid, arm)], "model_visible_input": a["input"],
                            "synthetic_alias_mapping": a["aliases"]}
        for criterion in case["applicable"]:
            x = m["criterion_definitions"][criterion]
            criteria.append({"id": label + "::" + criterion, "description": "For " + label + ": " + x["pass"]
                             + " Failure: " + x["fail"] + " Positive example: " + x["positive_example"]
                             + " Negative example: " + x["negative_example"]})
    msg = {"original": case["original"], "expected_case_behavior": case["expected"], "responses": responses}
    request = {"role": "grade", "job_id": sha([TAG, cid, "grade"])[:32], "model": MODEL,
               "max_output_tokens": 2048, "reasoning_effort": EFFORT,
               "messages": [{"role": "system", "content": GRADE_SYSTEM},
                            {"role": "user", "content": json.dumps(msg, ensure_ascii=False)}],
               "criteria": criteria}
    return request, blind, responses


def quotes_valid(grades, responses):
    return all(g["id"].split("::", 1)[0] in responses
               and g["evidence"] in responses[g["id"].split("::", 1)[0]]["response"] for g in grades)


def grade(m, answers, run_dir):
    path = run_dir / "first-grades.jsonl"
    final = {r["case_id"] for r in rows(path) if r["kind"] == "case" and r["how"] != "failed"}
    order = list(m["cases"])
    random.Random(SEED + 1).shuffle(order)
    pending = [c for c in order if c["case_id"] not in final]
    print("grades saved", len(final), "pending", len(pending), flush=True)
    for pos in range(0, len(pending), GRADE_BATCH):
        chunk = pending[pos:pos + GRADE_BATCH]
        built = {c["case_id"]: grade_request(m, c, answers) for c in chunk}
        request, labels = eb.build_grade_batch({k: v[0] for k, v in built.items()},
                                               job_id=sha([TAG, "gb"] + sorted(built))[:32], seed=SEED + pos)
        res = call(request)
        if res["status"] == "limit":
            stop_for_limit()
        append(path, {"kind": "call", "role": "grade_batch", "cases": sorted(built),
                      "usage": res.get("result", {}).get("usage"), "status": res["status"],
                      "error": res.get("error")})
        split = {}
        if res["status"] == "completed":
            try:
                split = eb.split_grade_batch(res["result"]["grades"], labels)
            except ValueError:
                split = {}
        for cid, (req, blind, responses) in built.items():
            grades, how = split.get(cid), "batch"
            if not grades or not quotes_valid(grades, responses):
                retry = dict(req)
                retry["job_id"] = sha([TAG, cid, "regrade"])[:32]
                retry["messages"] = list(req["messages"]) + [{"role": "user", "content": RETRY}]
                single = call(retry)
                if single["status"] == "limit":
                    stop_for_limit()
                append(path, {"kind": "call", "role": "regrade_single", "cases": [cid],
                              "usage": single.get("result", {}).get("usage"), "status": single["status"],
                              "error": single.get("error")})
                if single["status"] == "completed":
                    grades, how = single["result"]["grades"], "regrade"
                else:
                    grades, how = None, "failed"  # transport failure: retried on resume
            expected = {x["id"] for x in req["criteria"]}
            ok = bool(grades) and quotes_valid(grades, responses) and {g["id"] for g in grades} == expected
            append(path, {"kind": "case", "case_id": cid, "how": how,
                          "status": "completed" if ok else ("ungraded" if how != "failed" else "failed"),
                          "blind_labels": blind, "grades": grades if ok else None})
        print("graded", min(pos + GRADE_BATCH, len(pending)), "of", len(pending), flush=True)


# Decision ------------------------------------------------------------------------

def evaluate(m, graded, offline, assign=None):
    """Preregistered rule. ``assign`` maps an ungraded case -> (A, C, J) whole-task passes."""
    allp, crit_arms = {}, {}
    for case in m["cases"]:
        cid = case["case_id"]
        rec = graded.get(cid)
        if rec and rec["status"] == "completed":
            arms = {}
            for g in rec["grades"]:
                label, criterion = g["id"].split("::", 1)
                arms.setdefault(rec["blind_labels"][label], {})[criterion] = g["passed"]
            if all(arms["A"].values()):
                allp[cid] = {k: all(v.values()) for k, v in arms.items()}
                crit_arms[cid] = arms
        elif assign and cid in assign and assign[cid][0]:
            allp[cid] = dict(zip(ARMS, assign[cid]))
    by_case = {c["case_id"]: c for c in m["cases"]}

    def tally(ids):
        c_only = sum(allp[c]["C"] and not allp[c]["J"] for c in ids)
        j_only = sum(allp[c]["J"] and not allp[c]["C"] for c in ids)
        return {"A_eligible": len(ids), "whole_task_passes": {k: sum(allp[c][k] for c in ids) for k in ARMS},
                "C_only": c_only, "J_only": j_only, "net_loss": c_only - j_only}

    per_source = {}
    for s in SOURCES:
        t = tally([c for c in allp if by_case[c]["source"] == s])
        t["passes"] = t["net_loss"] <= 2
        per_source[str(s)] = t
    pooled = tally(list(allp))
    pooled["passes"] = pooled["net_loss"] <= 3
    controls = tally([c for c in allp if by_case[c]["negative_control"]])
    controls["passes"] = controls["net_loss"] <= 0
    criterion = {}
    for cr in m["criterion_definitions"]:
        app = [c for c in crit_arms if cr in crit_arms[c]["C"] and cr in crit_arms[c]["J"]]
        if app:
            criterion[cr] = {k: sum(crit_arms[c][k].get(cr, False) for c in app) for k in ARMS}
            criterion[cr]["cases"] = len(app)
    failing = []
    if not offline["gate"]["passed"]:
        failing.append("(a) offline protection/CI")
    failing += [f"(b) comprehension non-inferiority #{s}" for s, v in per_source.items() if not v["passes"]]
    if not pooled["passes"]:
        failing.append("(b) pooled comprehension non-inferiority")
    if not controls["passes"]:
        failing.append("(c) negative controls")
    return {"decision": "ADOPT-JOINT" if not failing else "REJECT-JOINT", "failing_parts": failing,
            "offline_gate_passed": offline["gate"]["passed"], "per_source": per_source, "pooled": pooled,
            "negative_controls": controls, "per_criterion": criterion,
            "discriminating_A_eligible": sum(1 for c in allp if c in m.get("_differs", set()))}


def usage_totals(paths):
    usage = {"calls": 0, "raw_tokens": 0, "input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}
    for path, kind in paths:
        for r in rows(path):
            if kind == "responses":
                u = r["result"].get("usage")
            else:
                u = r.get("usage") if r["kind"] == "call" else None
            if not u:
                continue
            usage["calls"] += 1
            usage["raw_tokens"] += u.get("input_tokens", 0) + u.get("output_tokens", 0)
            for k in ("input_tokens", "cached_input_tokens", "output_tokens"):
                usage[k] += u.get(k, 0)
    return usage


def report(run_dir):
    m, _jobs = verified(run_dir)
    pre = load(PLAN / "precheck.json")
    m["_differs"] = {x["case_id"] for x in pre["cases"] if x["J_differs_from_C"]}
    graded = {r["case_id"]: r for r in rows(run_dir / "first-grades.jsonl") if r["kind"] == "case"}
    offline = load(OFFLINE / "summary.json")
    missing = [c["case_id"] for c in m["cases"]
               if graded.get(c["case_id"], {}).get("status") not in ("completed", "ungraded")]
    ungraded = sorted(c for c, r in graded.items() if r["status"] == "ungraded")
    usage = usage_totals([(run_dir / "first-responses.jsonl", "responses"), (run_dir / "first-grades.jsonl", "grades")])
    doc = {"tag": TAG, "model": MODEL, "arms": list(ARMS), "freeze_sha256": fsha(run_dir / "freeze.json"),
           "usage": usage, "raw_tokens_per_case": round(usage["raw_tokens"] / len(m["cases"])),
           "ungraded": ungraded, "offline_gate": offline["gate"]}
    if missing:
        doc.update(status="incomplete", missing=missing)
    else:
        doc["status"] = "completed"
        if ungraded:
            scenarios = {"ungraded_J_wins": (True, False, True), "ungraded_C_wins": (True, True, False),
                         "ungraded_both_fail": (True, False, False), "ungraded_both_pass": (True, True, True),
                         "ungraded_excluded": (False, False, False)}
            bounds = {name: evaluate(m, graded, offline, {c: value for c in ungraded})
                      for name, value in scenarios.items()}
            doc["bounds"] = {k: {"decision": v["decision"], "failing_parts": v["failing_parts"]}
                             for k, v in bounds.items()}
            decisions = {b["decision"] for b in bounds.values()}
            doc["result"] = bounds["ungraded_excluded"]
            doc["result"]["decision"] = decisions.pop() if len(decisions) == 1 else "UNDECIDED_RERUN_UNGRADED"
        else:
            doc["result"] = evaluate(m, graded, offline)
    attack = run_dir / "attack-report.json"
    if attack.exists():
        doc["secondary_attack"] = load(attack)["counts"]
    write(run_dir / "report.json", doc)
    print(json.dumps({k: v for k, v in doc.items() if k != "bounds"}, ensure_ascii=True, indent=1)[:5000])


def run_attack(run_dir):
    verified(run_dir)
    attack = load(ATTACK / "manifest.json")
    answers = run_calls(attack["jobs"], run_dir / "attack-responses.jsonl", run_dir / "attack-failed-calls.jsonl",
                        "attack")
    counts = {a: {"top1": 0, "top3": 0, "abstained": 0, "unsupported": 0, "malformed": 0} for a in ("prior", "C", "J")}
    for (cid, arm), raw in answers.items():
        case = attack["cases"][cid]
        try:
            parsed = json.loads(raw)
            ranking = parsed["ranking"]
            if (not isinstance(ranking, list) or len(ranking) > 3 or not all(isinstance(x, str) for x in ranking)
                    or len(set(ranking)) != len(ranking) or not isinstance(parsed["rationale"], str)):
                raise ValueError("InvalidRanking")
        except (ValueError, TypeError, KeyError):
            counts[arm]["malformed"] += 1
            continue
        if any(x not in case["ids"] for x in ranking):
            counts[arm]["unsupported"] += 1
            counts[arm]["malformed"] += 1
            continue
        counts[arm]["top1"] += bool(ranking and ranking[0] == case["target"])
        counts[arm]["top3"] += case["target"] in ranking
        counts[arm]["abstained"] += not ranking
    doc = {"status": "completed" if not any(v["malformed"] for v in counts.values()) else "has_malformed",
           "cases": len(attack["cases"]), "counts": counts,
           "usage": usage_totals([(run_dir / "attack-responses.jsonl", "responses")]),
           "note": "Secondary, descriptive; not part of the ADOPT-JOINT rule. Not comparable with the native-transport "
                   "318/inference-attack numbers."}
    write(run_dir / "attack-report.json", doc)
    print(json.dumps(doc, indent=1))


# Dry run (fake adapter, no model call) -----------------------------------------------

class FakeAdapter:
    """Deterministic stand-in for run_lean_worker. Exercises batch splitting, quote failures,
    the single-case re-grade, permanently ungraded cases and a usage-limit stop."""

    def __init__(self, limit_after=None):
        self.calls, self.limit_after, self.lock = 0, limit_after, threading.Lock()

    def __call__(self, request, *, batch=False):
        with self.lock:
            self.calls += 1
            if self.limit_after is not None and self.calls > self.limit_after:
                raise eb.UsageLimitReached()
        validate_request(request)
        h = int(sha([request["job_id"]])[:8], 16)
        result = {"job_id": request["job_id"], "model": request["model"],
                  "usage": {"input_tokens": 7000 + h % 900, "cached_input_tokens": 0, "output_tokens": 40,
                            "total_tokens": 7040 + h % 900},
                  "metadata": {"fresh_session": True, "tool_events": 0, "requested_model": request["model"],
                               "adapter": "FAKE-dry-run"}}
        user = request["messages"][1]["content"]
        if request["role"] == "interpret":
            if request["messages"][0]["content"] == ATTACK_SYSTEM:
                ids = [r[0] for r in json.loads(user)["catalogue"]["rows"]]
                result["response"] = json.dumps({"ranking": ids[: h % 4], "rationale": "fake"})
            else:
                result["response"] = "FAKE answer " + request["job_id"][:6] + ": " + user[:80]
            return validate_result(result, request)
        payload = json.loads(user)
        materials = ({x["case"]: json.loads(x["material"]) for x in payload["cases"]}
                     if "cases" in payload else {None: payload})
        retry = request["messages"][-1]["content"] == RETRY
        grades = []
        for criterion in request["criteria"]:
            parts = criterion["id"].split("::")
            case_label = parts[0] if len(parts) == 3 else None
            response = materials[case_label]["responses"][parts[-2]]["response"]
            gh = int(sha([criterion["id"], request["job_id"]])[:8], 16)
            original = materials[case_label]["original"]
            bad = (h % 5 == 0 and not retry) or (retry and int(sha([original])[:8], 16) % 3 == 0)
            grades.append({"id": criterion["id"], "passed": gh % 10 != 0,
                           "evidence": "NOT A QUOTE" if bad else response[:12]})
        result["grades"] = grades
        return validate_result(result, request)


def dry_run(run_dir, limit_after):
    run_dir = run_dir.resolve()
    if run_dir.is_relative_to(HERE.parents[1]):
        raise SystemExit("dry-run directory must be outside docs/")
    eb.run_lean_worker = FakeAdapter(limit_after)
    if not (run_dir / "freeze.json").exists():
        freeze(run_dir)
    m, jobs = verified(run_dir)
    answers = run_calls(jobs, run_dir / "first-responses.jsonl", run_dir / "failed-calls.jsonl", "interpretations")
    grade(m, answers, run_dir)
    run_attack(run_dir)
    report(run_dir)


def main():
    parser = argparse.ArgumentParser()
    for flag in ("--prepare", "--freeze", "--run", "--run-attack", "--report"):
        parser.add_argument(flag, action="store_true")
    parser.add_argument("--dry-run", type=Path, help="fake adapter; directory outside docs/")
    parser.add_argument("--fake-limit-after", type=int)
    args = parser.parse_args()
    if args.dry_run:
        return dry_run(args.dry_run, args.fake_limit_after)
    if args.prepare:
        prepare()
    if args.freeze:
        freeze(RUN_DIR)
    if args.run:
        m, jobs = verified(RUN_DIR)
        answers = run_calls(jobs, RUN_DIR / "first-responses.jsonl", RUN_DIR / "failed-calls.jsonl",
                            "interpretations")
        grade(m, answers, RUN_DIR)
        report(RUN_DIR)
    if args.run_attack:
        run_attack(RUN_DIR)
    if args.report and not args.run:
        report(RUN_DIR)


if __name__ == "__main__":
    main()
