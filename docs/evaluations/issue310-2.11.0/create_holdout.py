"""Create a small synthetic holdout; freeze its output before running it."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from secure_gateway.evaluation import validate_corpus, write_json


def policy_record(term, language):
    return {"term": term, "project": "local-A", "language": language,
            "source": "explicit-local-correction", "expires_at": 4102444800, "revoked": False}


def add(cases, issue, language, text, secret, *, public=(), policy=None, arm="B"):
    path = ["input", 0, "content"]
    spans = []
    for item in secret:
        start = text.index(item)
        spans.append({"path": path, "start": start, "end": start + len(item),
                      "label": "sensitive", "fragments": [], "policy": "contextual", "severity": "high"})
    public_spans = []
    for item in public:
        start = text.index(item)
        public_spans.append({"path": path, "start": start, "end": start + len(item), "label": "action"})
    identifier = f"holdout-new-{issue}-{language}-{arm}"
    human = text
    for index, item in enumerate(secret, 1):
        human = human.replace(item, f"private_symbol_{index}", 1)
    cases.append({"id": identifier, "issue_number": issue, "template_group": identifier,
                  "split": "holdout", "language": language, "domain": "general", "dialect": "codex",
                  "payload": {"model": "fixture", "input": [{"role": "user", "content": text}]},
                  "echo_path": path, "task_path": path, "secrets": spans, "public": public_spans,
                  "forced_terms": [], "rubric": [
                      {"id": "intent", "description": "Carry out the requested action."},
                      {"id": "condition", "description": "Respect the stated condition."},
                      {"id": "prohibition", "description": "Respect any stated prohibition."},
                      {"id": "scope", "description": "Keep the requested output scope."}],
                  "human_text": human, "smoke": True, "local_policy": policy or {}, "candidate_arm": arm})


def main():
    cases = []
    add(cases, 310, "en", "Project name: glimmer. Ask for receipt before drafting; do not publish.",
        ["glimmer"], public=["Ask for receipt"])
    add(cases, 310, "ko", "프로젝트명은 여울입니다. 승인 여부를 먼저 확인하고 발송하지 마세요.",
        ["여울"], public=["먼저 확인"])
    add(cases, 311, "en", "Reviewer: Taviq. Document: Corlin. Ask for approval; do not send.",
        ["Taviq", "Corlin"], public=["Ask for approval"], policy={"allow_roles": True})
    add(cases, 311, "ko", "담당자: 나래빛. 문서: 푸른별. 승인을 먼저 묻고 발송하지 마세요.",
        ["담당자", "나래빛", "푸른별"], public=["승인을 먼저"],
        policy={"allow_roles": True, "confidential_roles": True})
    for language, text, term, public in (
        ("en", "Review alder after confirmation; otherwise ask first and do not publish.", "alder", "ask first"),
        ("ko", "여울 항목은 승인 후 검토하고 미승인 상태에서는 먼저 물어보세요.", "여울", "먼저 물어보세요"),
    ):
        policy = {"trusted_project": "local-A", "workspace": "local-A", "language": language,
                  "policyrecords": [policy_record(term, language)]}
        add(cases, 316, language, text, [term], public=[public], policy=policy)
    for language, text, secret, fields in (
        ("en", "Customer: Luma; Site: EastBank; Due: 2038-06-21; State: wait",
         ["Luma", "EastBank", "2038-06-21"], ["Customer", "Site", "Due"]),
        ("ko", "고객: 다온; 장소: 새빛; 기한: 2038-06-21; 상태: 대기",
         ["다온", "새빛", "2038-06-21"], ["고객", "장소", "기한"]),
    ):
        policy = {"document_sha256": sha256(text.encode()).hexdigest(), "scope": [0, len(text)],
                  "required_fields": fields, "protect_fields": fields}
        add(cases, 318, language, text, secret, policy=policy)
    data = {"schema_version": 1, "corpus_version": "names-policy-holdout-2.10.0-v1",
            "synthetic": True, "cases": cases}
    validate_corpus(data)
    write_json(Path("docs/evaluations/issue310-2.11.0/new-holdout.json"), data)


if __name__ == "__main__":
    main()
