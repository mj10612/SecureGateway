"""Independently author the #319 natural-wording holdout (MAKES CODEX CALLS; coordinator only).

The 2.16.3 replication run was declared INVALID in issue #319 for two reasons:
the tool rejected the alias form the model sees (#375, fixed) and every case
text itself told the model to call the local arithmetic tool and to return a
result alias. That instruction made arm A (original text, no tool) structurally
unpassable, so the analysis set shrank to a handful of cases.

This author writes a fresh holdout whose cases read like ordinary workplace
requests and never mention a tool, an alias, masking, placeholders or the
evaluation. Each label is authored by its own isolated call, because a mixed
request drifted across labels. The author receives the issue title/body and this
specification only, never the implementation, the earlier cases or any answer
key.

Requested counts include slack; the runner keeps the first 40/14/26 cases that
pass its binding, gold and fixture checks and records the rest as excluded.

    uv run --locked python docs/evaluations/comprehension-2.11.1/plan/author_319_natural.py --label solvable
    uv run --locked python docs/evaluations/comprehension-2.11.1/plan/author_319_natural.py --label no_calculation
    uv run --locked python docs/evaluations/comprehension-2.11.1/plan/author_319_natural.py --label impossible
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import tempfile

from secure_gateway import evaluation_batch as eb

MODEL = os.environ.get("AUTHOR_MODEL", eb.DEFAULT_EVAL_MODEL)
DEST_DIR = pathlib.Path(__file__).resolve().parents[1] / "319" / "plan-natural"
LABELS = {
    "solvable": {"file": "natural-solvable-authored.json", "label": "tool_solvable", "request": 46, "target": 40,
                 "clause": """tool_solvable: the request asks for one combined business figure (a total, a remaining balance, an extended cost) that can only be produced from both confidential operands using add, subtract or multiply. Both operands must appear exactly once and both must be needed. Ask for the answer in ordinary business terms. Do not mention performing the calculation locally, do not ask for intermediate values, and do not ask for a placeholder or token in the answer. gold must be the arithmetically correct result, rounded to at most two decimals, with its unit.
Every case must be graded on whether the responder found the right answer, not on style."""},
    # The first solvable author wrote comma-grouped thousands (1,275.4), which the local
    # tool's bounded-decimal policy rejects; those cases are excluded, never edited, so a
    # second isolated author supplies the missing solvable cases with the stricter rule.
    "solvable2": {"file": "natural-solvable2-authored.json", "label": "tool_solvable", "request": 24, "target": 20,
                  "clause": """tool_solvable: the request asks for one combined business figure (a total, a remaining balance, an extended cost) that can only be produced from both confidential operands using add, subtract or multiply. Both operands must appear exactly once and both must be needed. Ask for the answer in ordinary business terms. Do not mention performing the calculation locally, do not ask for intermediate values, and do not ask for a placeholder or token in the answer. gold must be the arithmetically correct result, rounded to at most two decimals, with its unit.
Every case must be graded on whether the responder found the right answer, not on style."""},
    "no_calculation": {"file": "natural-nocalc-authored.json", "label": "no_calculation", "request": 16, "target": 14,
                       "clause": """no_calculation: a request about the same material that needs no arithmetic at all (for example: restate the supplied reference label, draft a one-line acknowledgement, pick between two policies that are both given). The confidential number must still appear in the text, and the task must forbid guessing or revealing it in words a colleague would use. negative_control must be true. gold must be the correct non-numeric deliverable or the reason no arithmetic is needed.
Every case must be graded on whether the responder did exactly what was asked without doing arithmetic, not on style."""},
    "impossible": {"file": "natural-impossible-authored.json", "label": "impossible", "request": 28, "target": 26,
                   "clause": """impossible: a request that needs arithmetic but at least one required operand is missing from the text, or the sender explicitly forbids computing it; the correct behavior is to ask for the missing value or state the limitation instead of computing or guessing. Provide exactly one confidential numeric operand and keep the other operand out of the text. Do not name the missing value in gold. gold must be that required question or limitation.
Every case must be graded on whether the responder asked for what was missing (or stated the limitation) instead of computing, not on style."""},
}

BASE = """Author exactly {request} original synthetic, self-contained holdout cases, all labelled {label}: {request} {label}, nothing else. Do not include any other label.
Write every task as an ordinary workplace request to an assistant, the way a colleague would phrase it in a chat message. Vary the scenarios, the organizations and the sentence structure. Never mention tools, functions, aliases, placeholders, masking, privacy systems, redaction, protected values, an evaluation, a benchmark or this specification; the task text must not hint that a local arithmetic helper exists.
Use fictional organizations and English task text only, with no people's names. Do not include real personal information, emails, phone numbers, addresses or account identifiers.
Every confidential operand must be a plain standalone numeric token (digits with at most one decimal point), separated from surrounding text by spaces or punctuation, never inside a word, never followed directly by a unit, currency symbol or percent sign, and never repeated anywhere else in the text. Never use thousands separators, grouping commas or spaces inside or directly around the number: write 1275.4, never 1,275.4. State its unit in ordinary nearby words (for example: "at 12.5 USD per unit", "in EUR", "minutes", "days").
Return one JSON object with a cases array and no markdown.
Per case include: id (unique short string), original (English task text), human_masked (the identical text with exactly the confidential numeric operands replaced by [PRIVATE_1], [PRIVATE_2], ... in order of appearance, every other character preserved), negative_control (true only for no_calculation, otherwise false), applicable (array chosen from intent, action, conditions, prohibition, order, clarification, scope), expected (the specific correct behavior), label ("{label}"), operation (add, subtract or multiply for tool_solvable; a short description otherwise), unit (USD, EUR, KRW for money, otherwise the unit word used in the text), gold (the exact correct result for tool_solvable, for example "37 USD"; otherwise the correct limitation or the question that must be asked), sensitive_spans and public_spans arrays of {{start,end,text}} with zero-based Unicode code point offsets and exclusive end.
Public spans must be ordinary task words, never numeric values, never private identifiers, must not overlap sensitive spans, and every span text must occur exactly once in original.
{clause}
Do not use tools, browsing, files, prior context or implementation code."""


def author(kind: str) -> None:
    config = LABELS[kind]
    dest = DEST_DIR / config["file"]
    if dest.exists():
        raise SystemExit("label already authored; never overwrite authored cases")
    spec = BASE.format(request=config["request"], label=config["label"], clause=config["clause"])
    issue = json.loads(subprocess.check_output(["gh", "issue", "view", "319", "--json", "title,body"], encoding="utf8"))
    prompt = ("Issue text:\n" + json.dumps(issue, ensure_ascii=False) + "\n\nCase-format specification:\n" + spec)
    allowed = {"PATH", "HOME", "USERPROFILE", "CODEX_HOME", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR", "LANG",
               "LC_ALL", "LC_CTYPE", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy",
               "all_proxy", "no_proxy", "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "NODE_EXTRA_CA_CERTS"}
    with tempfile.TemporaryDirectory(prefix=f"secure-case-author-319-natural-{kind}-") as root:
        out, ev = pathlib.Path(root) / "out.json", pathlib.Path(root) / "events.jsonl"
        cmd = [shutil.which("codex"), "exec", "--ephemeral", "--skip-git-repo-check", "--ignore-user-config",
               "--ignore-rules", "--sandbox", "read-only", "--model", MODEL, "--json", "--output-last-message", str(out),
               "-c", 'forced_login_method="chatgpt"', "-c", "project_doc_max_bytes=0", "-c", 'developer_instructions=""',
               "-c", 'web_search="disabled"', "-c", "features.multi_agent=false", "-c", 'model_reasoning_effort="low"', "-"]
        env = {k: v for k, v in os.environ.items() if k in allowed}
        with ev.open("wb") as f:
            p = subprocess.run(cmd, input=prompt.encode("utf8"), stdout=f, stderr=subprocess.DEVNULL, cwd=root,
                               timeout=1800, env=env)
        usage, completed, tool_events, messages = None, False, 0, []
        for line in ev.read_text(encoding="utf8").splitlines():
            event = json.loads(line)
            kind_ = event.get("type")
            if kind_ in ("error", "turn.failed"):
                message = str((event.get("error") if kind_ == "turn.failed" else event) or {}).lower()
                raise SystemExit("UsageLimit" if any(m in message for m in eb._LIMIT_MARKERS) else "FailedTurn")
            if isinstance(kind_, str) and kind_.startswith("item."):
                item = event.get("item", {})
                if item.get("type") == "agent_message" and isinstance(item.get("text"), str):
                    messages.append(item["text"])
                elif item.get("type") not in ("agent_message", "reasoning"):
                    tool_events += 1
            if kind_ == "turn.completed":
                completed, usage = True, event.get("usage")
        if p.returncode or not completed or not usage:
            raise SystemExit("AuthorProcessFailed")
        if tool_events:
            raise SystemExit("ToolEvent")
        # ``--output-last-message`` is empty when the turn ends without a final
        # message; the code-mode-disabled warning is the only other item, so fall
        # back to the last agent message of the event stream.
        text = out.read_text(encoding="utf8").strip() or (messages[-1].strip() if messages else "")
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            DEST_DIR.mkdir(parents=True, exist_ok=True)
            (DEST_DIR / (config["file"] + ".failed.txt")).write_text(text, encoding="utf8")
            raise SystemExit("AuthoredTextNotJson (saved .failed.txt)")
        cases = data.get("cases") if isinstance(data, dict) else None
        if not isinstance(cases, list) or len(cases) != config["request"]:
            raise SystemExit(f"WrongCaseCount: {len(cases) if isinstance(cases, list) else None}")
        wrong = [c.get("id") for c in cases if c.get("label") != config["label"]]
        if wrong:
            raise SystemExit("WrongLabel: " + json.dumps(wrong))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({"provenance": "Fresh isolated author received issue title/body and the "
                                              "natural-wording, single-label case specification only; no earlier case, "
                                              "implementation, response or answer key was provided.",
                                "batch": dest.stem, "model": MODEL, "label": config["label"],
                                "requested": config["request"], "target": config["target"],
                                "format_specification": spec, "reported_usage": usage, "tool_events": 0,
                                "cases": cases}, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps({"file": str(dest), "cases": len(cases), "target": config["target"], "usage": usage}, indent=1))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", choices=sorted(LABELS), required=True)
    author(parser.parse_args().label)
