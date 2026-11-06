"""Evaluate the local gateway on a small, labelled multilingual fixture.

Exit 1 when any everyday sentence changes, a labelled value remains visible,
restoration fails, or the skill instruction loses a required phrase.
This is a deterministic regression probe, not a statistical privacy benchmark.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

from secure_gateway.gateway import GatewaySession


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def main() -> int:
    everyday = json.loads((FIXTURES / "everyday_multilingual.json").read_text(encoding="utf-8"))
    additional = json.loads((FIXTURES / "everyday_additional.json").read_text(encoding="utf-8"))
    independent = json.loads((FIXTURES / "independent_multilingual.json").read_text(encoding="utf-8"))
    sensitive = json.loads((FIXTURES / "sensitive_multilingual.json").read_text(encoding="utf-8"))
    report = {}
    for language, passages in everyday.items():
        retained = leaks = restore_failures = 0
        sample = sensitive[language]
        for index, passage in enumerate(passages):
            session = GatewaySession(natural_language=language)
            forwarded = session.mask(passage)
            retained += forwarded == passage
            restore_failures += session.restore(forwarded) != passage
            values = (sample["person"], sample["company"], sample["terms"][index % 3],
                      f"person{index}@example.invalid")
            private_text = " | ".join(values)
            masked = session.mask(private_text)
            leaks += sum(value in masked for value in values)
            restore_failures += session.restore(masked) != private_text
        additional_session = GatewaySession(natural_language=language)
        additional_masked = additional_session.mask(additional[language])
        restore_failures += additional_session.restore(additional_masked) != additional[language]
        independent_session = GatewaySession(natural_language=language)
        independent_masked = independent_session.mask(independent[language])
        restore_failures += independent_session.restore(independent_masked) != independent[language]
        report[language] = {"passages": len(passages), "unchanged": retained,
                            "additional_unchanged": additional_masked == additional[language],
                            "independent_unchanged": independent_masked == independent[language],
                            "sensitive_values": len(passages) * 4,
                            "sensitive_visible": leaks, "restoration_failures": restore_failures}

    skill = "Read SKILL.md before using this skill. Follow its instructions."
    skill_session = GatewaySession(natural_language="en")
    skill_masked = skill_session.mask(skill)
    required = ("Read", "SKILL.md", "skill", "Follow", "instructions")
    lost = [word for word in required if word not in skill_masked]
    print(json.dumps({"languages": report, "skill_required_words_lost": lost}, ensure_ascii=False, indent=2))
    failed = bool(lost) or any(
        row["unchanged"] != row["passages"] or not row["additional_unchanged"] or not row["independent_unchanged"]
        or row["sensitive_visible"] or row["restoration_failures"]
        for row in report.values()
    )
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
