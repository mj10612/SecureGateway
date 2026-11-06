"""Export only masked requests for independent, blinded text-intent evaluation.

Use synthetic corpora. A passing local check proves labelled-reference masking,
round-trip restoration and replay stability, not model comprehension. Give only
the output to an interpreter; compare its recorded answer with the corpus later.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from secure_gateway.gateway import GatewaySession


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=Path(__file__).resolve().parents[1] / "tests/fixtures/semantic_paragraphs.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--context-model", type=Path, help="Verified local model directory; omit for the baseline.")
    args = parser.parse_args()
    if args.corpus.resolve() == args.output.resolve():
        parser.error("The blinded output must be separate from the original corpus.")
    rows = json.loads(args.corpus.read_text(encoding="utf-8"))
    model = None
    if args.context_model:
        from secure_gateway.context_model import load_context_model
        model, status = load_context_model(str(args.context_model.resolve()))
        if model is None:
            parser.error("Context model is not ready: " + status)
    blinded = []
    for row in rows:
        session = GatewaySession(context_model=model)
        payload = {"model": "fixture", "input": [{"role": "user", "content": row["text"]}]}
        request = session.request(payload)
        masked = request["input"][0]["content"]
        if any(reference in masked for reference in row["references"]):
            raise ValueError("A labelled reference remains visible: " + row["language"])
        if session.restore(masked) != row["text"]:
            raise ValueError("Restoration failed: " + row["language"])
        if session.request(payload)["input"][0]["content"] != masked:
            raise ValueError("Replay changed aliases: " + row["language"])
        blinded.append({"language": row["language"], "instructions": request["instructions"], "content": masked})
    args.output.write_text(json.dumps(blinded, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(blinded)} blinded requests; labelled references, restoration and replay checks passed.")


if __name__ == "__main__":
    main()
