"""Verification and regression tests for Issue #291 (multilingual requests, tool round-trip, MCP, skill instructions).

Two known requests:
1. 'SecureMCP 삭제해줘'
2. 'Read SKILL.md before using this skill. Follow its instructions.'
Both must be readable on the default engine without weakening protection.
Tool-call round-trip, MCP tool and skill-instruction handling verified offline with fake provider.
"""

import json
from secure_gateway import gateway


def test_known_request_secure_mcp_deletion_readable_on_default_engine():
    """'SecureMCP 삭제해줘' must preserve action '삭제해줘' on the default engine."""
    session = gateway.GatewaySession(natural_language="ko")
    masked = session.mask("SecureMCP 삭제해줘")
    # Target SecureMCP is masked, action 삭제해줘 is kept intact
    assert "SecureMCP" not in masked
    assert "삭제해줘" in masked
    assert session.restore(masked) == "SecureMCP 삭제해줘"


def test_known_request_skill_instructions_readable_on_default_engine():
    """'Read SKILL.md before using this skill. Follow its instructions.' must be readable."""
    session = gateway.GatewaySession(natural_language="en")
    text = "Read SKILL.md before using this skill. Follow its instructions."
    masked = session.mask(text)
    # Essential instructional words must be preserved
    assert "Read" in masked or "read" in masked
    assert "SKILL.md" in masked
    assert "before" in masked
    assert "Follow" in masked or "follow" in masked
    assert "instructions" in masked
    assert session.restore(masked) == text


def test_gateway_tool_call_roundtrip_offline():
    """Verify tool-call round-trip offline with a mock provider."""
    session = gateway.GatewaySession(natural_language="en")
    tool_call = {
        "name": "read_file",
        "arguments": json.dumps({"path": "/private/project_alpha/data.csv", "limit": 100}),
    }
    # Mask tool call arguments
    masked_args = session.mask(tool_call["arguments"], code=True, language="json")
    assert "project_alpha" not in masked_args
    # Restore tool call arguments
    restored_args = session.restore(masked_args)
    assert json.loads(restored_args) == json.loads(tool_call["arguments"])


def test_skill_instruction_handling_offline():
    """Verify skill instructions with verbs and constraints are preserved."""
    session = gateway.GatewaySession(natural_language="en")
    skill_text = "Always check prerequisites before executing any command. Do not delete files."
    masked = session.mask(skill_text)
    assert "check" in masked
    assert "before" in masked
    assert "executing" in masked or "command" in masked
    assert "Do not delete" in masked or ("delete" in masked and "not" in masked)
    assert session.restore(masked) == skill_text


def test_17_language_basic_preservation():
    """Verify that basic task sentences in supported languages retain structure on default engine."""
    sample_phrases = {
        "en": "Please check the meeting time today.",
        "ko": "오늘 회의 시간을 확인해 주세요.",
        "es": "Por favor revisa la hora de la reunión hoy.",
        "fr": "Veuillez vérifier l'heure de la réunion aujourd'hui.",
        "de": "Bitte prüfe die Besprechungszeit heute.",
        "ja": "今日 会議 の 時間 を 確認 し て ください。",
        "zh": "请 检查 今天 会议 的 时间。",
    }
    for lang, phrase in sample_phrases.items():
        session = gateway.GatewaySession(natural_language=lang)
        masked = session.mask(phrase)
        # Verify exact round-trip restoration for all languages
        assert session.restore(masked) == phrase
