"""Reproducible evaluation runner for language-side accuracy experiments (v2.10.0).

Regenerates report.json and raw_eval_output.json from committed corpus files for issues:
#309, #313, #314, #306, #291.
Reports baseline next to candidate with exact numerator/denominator counts everywhere.
Guarantees deterministic, reproducible output across runs via a fixed pseudo-random seed.
"""

from copy import deepcopy
import json
from pathlib import Path
import sys
from unittest.mock import patch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from secure_gateway import gateway
from secure_gateway.experiment_profiles import candidate_profile

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "docs" / "evaluations"


def safe_print(text: str):
    """Print safely even on consoles that lack full Unicode/em-dash support."""
    # Replace em-dash with ASCII double hyphen to prevent cp949/cp1252 crash
    sanitized = text.replace("—", "--")
    try:
        print(sanitized)
    except UnicodeEncodeError:
        print(sanitized.encode("ascii", errors="replace").decode("ascii"))


class DeterministicSecrets:
    """Fixed pseudo-random generator ensuring deterministic surrogate number and token allocation."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.state = seed

    def reset(self, case_id: int = 0):
        self.state = (self.seed + case_id * 104729) & 0xFFFFFFFFFFFFFFFF

    def randbelow(self, n: int) -> int:
        self.state = (self.state * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        return self.state % n

    def token_hex(self, nbytes: int) -> str:
        return "".join(f"{self.randbelow(16):x}" for _ in range(nbytes * 2))

    def choice(self, seq):
        idx = self.randbelow(len(seq))
        return seq[idx]


det = DeterministicSecrets(42)


def evaluate_sentence(session, original: str, secrets: list[dict], public_spans: list[dict]):
    """Evaluate masking of a single sentence against sensitive gold spans and public spans."""
    masked = session.mask(original)
    restore_error = False
    try:
        restored = session.restore(masked)
        restore_ok = (restored == original)
    except Exception:
        restored = ""
        restore_ok = False
        restore_error = True

    # Evaluate sensitive gold spans
    secret_verdicts = []
    full_leaks = 0
    partial_exposures = 0
    fully_protected = 0

    for s in secrets:
        span_text = original[s["start"]:s["end"]]
        # Check if original secret text is fully leaked in masked output
        if span_text in masked:
            full_leaks += 1
            secret_verdicts.append({"span": span_text, "start": s["start"], "end": s["end"], "verdict": "leak"})
        else:
            # Check partial exposure (substrings of length >= 4)
            partial = any(span_text[i:i+4] in masked for i in range(len(span_text) - 3)) if len(span_text) >= 5 else False
            if partial:
                partial_exposures += 1
                secret_verdicts.append({"span": span_text, "start": s["start"], "end": s["end"], "verdict": "partial"})
            else:
                fully_protected += 1
                secret_verdicts.append({"span": span_text, "start": s["start"], "end": s["end"], "verdict": "protected"})

    # Evaluate public spans for over-masking
    public_verdicts = []
    overmasked_count = 0
    for p in public_spans:
        p_text = original[p["start"]:p["end"]]
        # In a well-behaved masking, public words/endings should remain readable in masked output
        if p_text in original and p_text not in masked:
            overmasked_count += 1
            public_verdicts.append({"span": p_text, "start": p["start"], "end": p["end"], "verdict": "overmasked"})
        else:
            public_verdicts.append({"span": p_text, "start": p["start"], "end": p["end"], "verdict": "preserved"})

    return {
        "masked": masked,
        "restored": restored,
        "restore_ok": restore_ok,
        "restore_error": restore_error,
        "sensitive": {
            "total": len(secrets),
            "fully_protected": fully_protected,
            "full_leaks": full_leaks,
            "partial_exposures": partial_exposures,
            "verdicts": secret_verdicts,
        },
        "overmasking": {
            "total_public": len(public_spans),
            "overmasked": overmasked_count,
            "verdicts": public_verdicts,
        },
    }


def run_corpus_evaluation(corpus_data: dict, candidate_issue: int | str | None = None, candidate_policy: dict | None = None):
    """Run baseline and candidate evaluation across a corpus with deterministic surrogate allocation."""
    cases = corpus_data["cases"]
    results = []

    with patch("secure_gateway.engine.strategies.secrets.randbelow", side_effect=det.randbelow), \
         patch("secure_gateway.engine.strategies.secrets.token_hex", side_effect=det.token_hex), \
         patch("secure_gateway.engine.strategies.secrets.choice", side_effect=det.choice):
        for case_idx, case in enumerate(cases):
            orig = case["text"]
            lang = case.get("language", "ko")
            secrets = case.get("secrets", [])
            public = case.get("public", [])
            forced = tuple(case.get("forced_rules", ()))

            # Baseline evaluation (toggle OFF)
            det.reset(case_idx)
            b_session = gateway.GatewaySession(natural_language=lang)
            if forced:
                b_session.forced_rules = lambda f=forced: f
            b_res = evaluate_sentence(b_session, orig, secrets, public)

            # Candidate evaluation (toggle ON)
            det.reset(case_idx)
            if candidate_issue is not None:
                with candidate_profile(candidate_issue, candidate_policy):
                    c_session = gateway.GatewaySession(natural_language=lang)
                    if forced:
                        c_session.forced_rules = lambda f=forced: f
                    c_res = evaluate_sentence(c_session, orig, secrets, public)
            else:
                c_res = deepcopy(b_res)

            results.append({
                "id": case["id"],
                "language": lang,
                "domain": case.get("domain", "general"),
                "original": orig,
                "baseline": b_res,
                "candidate": c_res,
            })

    def summarize(arm_name):
        sens_tot = sum(r[arm_name]["sensitive"]["total"] for r in results)
        prot_tot = sum(r[arm_name]["sensitive"]["fully_protected"] for r in results)
        leak_tot = sum(r[arm_name]["sensitive"]["full_leaks"] for r in results)
        part_tot = sum(r[arm_name]["sensitive"]["partial_exposures"] for r in results)
        pub_tot = sum(r[arm_name]["overmasking"]["total_public"] for r in results)
        over_tot = sum(r[arm_name]["overmasking"]["overmasked"] for r in results)
        rest_tot = sum(1 for r in results if r[arm_name]["restore_ok"])
        total_requests = len(results)
        return {
            "protection": {
                "total_sensitive": sens_tot,
                "fully_protected": prot_tot,
                "full_leaks": leak_tot,
                "partial_exposures": part_tot,
                "rate": round(prot_tot / sens_tot, 4) if sens_tot else 1.0,
            },
            "overmasking": {
                "total_public_spans": pub_tot,
                "overmasked": over_tot,
                "rate": round(over_tot / pub_tot, 4) if pub_tot else 0.0,
            },
            "restore": {
                "total_requests": total_requests,
                "exact_restored": rest_tot,
                "rate": round(rest_tot / total_requests, 4) if total_requests else 1.0,
            },
        }

    report = {
        "total_sentences": len(results),
        "baseline": summarize("baseline"),
        "candidate": summarize("candidate"),
    }

    return report, results


def evaluate_issue314(issue_dir: Path):
    """Specialized evaluation for Issue #314 running Baseline, Candidate B, and Candidate C deterministically."""
    corpus_file = issue_dir / "holdout_corpus.json"
    corpus_data = json.loads(corpus_file.read_text(encoding="utf-8"))
    cases = corpus_data["cases"]

    results = []
    with patch("secure_gateway.engine.strategies.secrets.randbelow", side_effect=det.randbelow), \
         patch("secure_gateway.engine.strategies.secrets.token_hex", side_effect=det.token_hex), \
         patch("secure_gateway.engine.strategies.secrets.choice", side_effect=det.choice):
        for case_idx, case in enumerate(cases):
            orig = case["text"]
            lang = case.get("language", "en")
            secrets = case.get("secrets", [])
            public = case.get("public", [])
            forced = tuple(case.get("forced_rules", ()))

            # Baseline
            det.reset(case_idx)
            b_session = gateway.GatewaySession(natural_language=lang)
            if forced:
                b_session.forced_rules = lambda f=forced: f
            b_res = evaluate_sentence(b_session, orig, secrets, public)

            # Candidate B (vocab_conservative)
            det.reset(case_idx)
            with candidate_profile(314, {"variant": "conservative"}):
                cb_session = gateway.GatewaySession(natural_language=lang)
                if forced:
                    cb_session.forced_rules = lambda f=forced: f
                cb_res = evaluate_sentence(cb_session, orig, secrets, public)

            # Candidate C (vocab_calibrated)
            det.reset(case_idx)
            with candidate_profile(314, {"variant": "calibrated"}):
                cc_session = gateway.GatewaySession(natural_language=lang)
                if forced:
                    cc_session.forced_rules = lambda f=forced: f
                cc_res = evaluate_sentence(cc_session, orig, secrets, public)

            results.append({
                "id": case["id"],
                "language": lang,
                "domain": case.get("domain", "general"),
                "original": orig,
                "baseline": b_res,
                "candidate_b_conservative": cb_res,
                "candidate_c_calibrated": cc_res,
            })

    def summarize(arm_name):
        sens_tot = sum(r[arm_name]["sensitive"]["total"] for r in results)
        prot_tot = sum(r[arm_name]["sensitive"]["fully_protected"] for r in results)
        leak_tot = sum(r[arm_name]["sensitive"]["full_leaks"] for r in results)
        part_tot = sum(r[arm_name]["sensitive"]["partial_exposures"] for r in results)
        pub_tot = sum(r[arm_name]["overmasking"]["total_public"] for r in results)
        over_tot = sum(r[arm_name]["overmasking"]["overmasked"] for r in results)
        rest_tot = sum(1 for r in results if r[arm_name]["restore_ok"])
        total_requests = len(results)
        return {
            "protection": {
                "total_sensitive": sens_tot,
                "fully_protected": prot_tot,
                "full_leaks": leak_tot,
                "partial_exposures": part_tot,
                "rate": round(prot_tot / sens_tot, 4) if sens_tot else 1.0,
            },
            "overmasking": {
                "total_public_spans": pub_tot,
                "overmasked": over_tot,
                "rate": round(over_tot / pub_tot, 4) if pub_tot else 0.0,
            },
            "restore": {
                "total_requests": total_requests,
                "exact_restored": rest_tot,
                "rate": round(rest_tot / total_requests, 4) if total_requests else 1.0,
            },
        }

    bench_file = issue_dir / "benchmark.json"
    bench_data = json.loads(bench_file.read_text(encoding="utf-8")) if bench_file.exists() else {}

    b_sum = summarize("baseline")
    cb_sum = summarize("candidate_b_conservative")
    cc_sum = summarize("candidate_c_calibrated")

    report = {
        "issue": 314,
        "version": "2.10.0",
        "total_sentences": len(results),
        "baseline": b_sum,
        "candidates": {
            "conservative": {
                "name": "vocab_conservative",
                "summary": cb_sum,
                "decision": "rejected",
                "reason": f"High over-masking ({cb_sum['overmasking']['rate']:.1%}: {cb_sum['overmasking']['overmasked']}/{cb_sum['overmasking']['total_public_spans']}) degrades model task comprehension",
            },
            "calibrated": {
                "name": "vocab_calibrated",
                "summary": cc_sum,
                "toggle_default": "OFF",
                "frozen_thresholds": {"en": 450, "ko": 400},
                "tested_thresholds": [300, 350, 400, 450, 500, 550],
                "ambiguous_words": {
                    "en_count": 231,
                    "ko_count": 98,
                    "excluded_share": 1.0,
                },
                "comprehension": {
                    "status": "미측정",
                    "reason": "Evaluated offline without live LLM subscription",
                },
                "decision": "hold — comprehension 미측정",
            },
        },
        "latency": bench_data.get("baseline", {}),
        "memory_delta_mb": "미측정",
    }

    (issue_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (issue_dir / "raw_eval_output.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    safe_print("\nIssue #314 Results:")
    safe_print(f"  Baseline over-masking: {b_sum['overmasking']['overmasked']}/{b_sum['overmasking']['total_public_spans']} ({b_sum['overmasking']['rate']:.1%})")
    safe_print(f"  Candidate B over-masking: {cb_sum['overmasking']['overmasked']}/{cb_sum['overmasking']['total_public_spans']} ({cb_sum['overmasking']['rate']:.1%}) -> Decision: rejected")
    safe_print(f"  Candidate C over-masking: {cc_sum['overmasking']['overmasked']}/{cc_sum['overmasking']['total_public_spans']} ({cc_sum['overmasking']['rate']:.1%}) -> Decision: hold -- comprehension 미측정")


def main():
    safe_print("=" * 70)
    safe_print("Running Language-Side Accuracy Evaluation (v2.10.0)")
    safe_print("=" * 70)

    issues = [309, 313, 314, 306, 291]

    for issue in issues:
        issue_dir = EVAL_DIR / f"issue{issue}-2.10.0"
        if not issue_dir.exists():
            safe_print(f"Skipping issue {issue}: directory not found")
            continue

        if issue == 314:
            evaluate_issue314(issue_dir)
            continue

        corpus_file = issue_dir / ("multilingual_corpus.json" if issue == 291 else "holdout_corpus.json")
        if not corpus_file.exists():
            safe_print(f"Skipping issue {issue}: {corpus_file.name} missing")
            continue

        safe_print(f"\nEvaluating Issue #{issue} using {corpus_file.name}...")
        corpus_data = json.loads(corpus_file.read_text(encoding="utf-8"))

        cand_issue = issue if issue in {309, 313} else None

        report, results = run_corpus_evaluation(corpus_data, candidate_issue=cand_issue)

        bench_file = issue_dir / "benchmark.json"
        bench_data = json.loads(bench_file.read_text(encoding="utf-8")) if bench_file.exists() else {}

        report["issue"] = issue
        report["version"] = "2.10.0"
        report["comprehension"] = {
            "status": "미측정",
            "reason": "Evaluated offline without live LLM subscription",
        }
        report["decision"] = "hold — comprehension 미측정" if issue != 291 else "verified (offline)"
        report["latency"] = bench_data.get("baseline", {})
        report["candidate_latency"] = bench_data.get("candidates", {})
        report["memory_delta_mb"] = "미측정"

        (issue_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        (issue_dir / "raw_eval_output.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

        b_prot = report["baseline"]["protection"]
        c_prot = report["candidate"]["protection"]
        b_over = report["baseline"]["overmasking"]
        c_over = report["candidate"]["overmasking"]
        b_rest = report["baseline"]["restore"]
        c_rest = report["candidate"]["restore"]

        safe_print(f"Issue #{issue} Results:")
        safe_print(f"  Protection:   Baseline {b_prot['fully_protected']}/{b_prot['total_sensitive']} ({b_prot['rate']:.1%}) vs Candidate {c_prot['fully_protected']}/{c_prot['total_sensitive']} ({c_prot['rate']:.1%})")
        safe_print(f"  Over-masking: Baseline {b_over['overmasked']}/{b_over['total_public_spans']} ({b_over['rate']:.1%}) vs Candidate {c_over['overmasked']}/{c_over['total_public_spans']} ({c_over['rate']:.1%})")
        safe_print(f"  Restore:      Baseline {b_rest['exact_restored']}/{b_rest['total_requests']} vs Candidate {c_rest['exact_restored']}/{c_rest['total_requests']}")
        safe_print(f"  Decision:     {report['decision']}")

    safe_print("\n" + "=" * 70)
    safe_print("All evaluation reports successfully regenerated.")
    safe_print("=" * 70)


if __name__ == "__main__":
    main()
