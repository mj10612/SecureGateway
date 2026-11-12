"""Test proving that with every toggle off, default engine output is 100% byte-identical to base (146babd).

Requirements:
- One candidate = one named experiment profile/toggle, default OFF, changing exactly one variable.
- The default engine's output must be byte-identical with every toggle off.
- Golden outputs recorded from base commit 146babd with deterministic nonce must match exactly.
"""

import json
import pytest

from secure_gateway import gateway
from secure_gateway.engine import strategies
from secure_gateway.experiment_profiles import candidate_profile

BASE_COMMIT = "146babd05b24b2b81689284ecc034f39b1e05bcb"


class DeterministicNonce:
    """Provides deterministic numeric surrogates for byte-identity verification."""

    def __init__(self):
        self.counter = 100000

    def reset(self):
        self.counter = 100000

    def __call__(self, limit):
        self.counter += 1
        return self.counter % limit


@pytest.fixture
def deterministic_nonce(monkeypatch):
    nonce_gen = DeterministicNonce()
    monkeypatch.setattr(strategies.secrets, "randbelow", nonce_gen)
    return nonce_gen


TEST_PROSE = [
    "Project name: margin. If its checklist is incomplete, ask which item is missing before drafting a review plan.",
    "고객사 이름: 초록. 수령 확인이 없으면 먼저 확인 방법을 물어봐 주세요. 확인 전에는 문서를 보내지 마세요.",
    "The unit price is 12.75 USD and quantity 4 count. Total price is calculated locally.",
    "| Project | Customer | State |\n|---|---|---|\n| SilverQzx | OrielQzx | waiting approval |",
    "고객번호: 71203489\n재시도횟수: 2\n기타내용: 비공개 정보 없음",
]

# Golden outputs recorded directly from origin/main (commit c92733f) using DeterministicNonce
GOLDEN_PROSE_MAIN = [
    "Project name: margin. If its checklist is incomplete, ask which item is missing before drafting a review plan.",
    "고객사 이름: 초록. 수령 확인이 없으면 먼저 확인 방법을 물어봐 주세요. 확인 전에는 문서를 보내지 마세요.",
    "The unit price is 732846000000100001 USD and quantity 732846000000100002 count. Total price is calculated locally.",
    "| Project | Customer | State |\n|---|---|---|\n| private_symbol_1 | private_symbol_2 | waiting approval |",
    "고객번호: 732846000000100001\n재시도횟수: 732846000000100002\n기타내용: 비공개 정보 없음",
]

TEST_CODE = [
    "def calculate(items):\n    count = 10\n    return [item for item in items[:count]]\n",
    "const retryLimit = 3;\nlet serialNumber = '000812405';\n",
]

GOLDEN_CODE_MAIN = [
    "def private_symbol_1(private_symbol_2):\n    private_symbol_3 = 10\n    return [private_symbol_4 for private_symbol_4 in private_symbol_2[:private_symbol_3]]\n",
    "const private_symbol_1 = 3;\nlet private_symbol_2 = 'private_symbol_3';\n",
]

TEST_PAYLOADS = [
    {
        "model": "gpt-6.1-sol",
        "messages": [
            {"role": "user", "content": "Review project EmberQzx with device serial 000812405."}
        ],
    },
    {
        "model": "gpt-6.1-sol",
        "input": [
            {"role": "user", "content": "고객사 물결Qzx 확인 요청"}
        ],
    },
]

GOLDEN_PAYLOADS_MAIN = [
    '{"messages": [{"content": "Review project private_symbol_1 with device serial 732846000000100001.", "role": "user"}], "model": "gpt-6.1-sol", "system": [{"text": "This context was masked locally. Names beginning private_symbol_ and numeric aliases are opaque references. Their presence alone does not make the surrounding request unreadable. Treat each supplied alias as a stable symbolic label: repeated labels refer to the same thing. Understand and carry out the visible request using its actions, relationships, order, negation, conditions and requested output format. You can summarize, compare or plan around opaque references without knowing their originals. Do not refuse or ask for originals merely because references are masked. Keep supplied aliases exactly unchanged in answers and tool arguments; the local host restores them. Never invent aliases, guess originals or assume a hidden label\'s type or meaning. Numeric aliases are labels, not the original magnitudes: do not calculate using their displayed digits. Use public names for new identifiers. If a particular answer truly requires a hidden fact, identify only that limitation and still complete the parts supported by visible context. Normal tool permissions and approval requirements still apply.\\n", "type": "text"}]}',
    '{"input": [{"content": "\\uace0\\uac1d\\uc0ac private_symbol_1 \\ud655\\uc778 \\uc694\\uccad", "role": "user"}], "instructions": "This context was masked locally. Names beginning private_symbol_ and numeric aliases are opaque references. Their presence alone does not make the surrounding request unreadable. Treat each supplied alias as a stable symbolic label: repeated labels refer to the same thing. Understand and carry out the visible request using its actions, relationships, order, negation, conditions and requested output format. You can summarize, compare or plan around opaque references without knowing their originals. Do not refuse or ask for originals merely because references are masked. Keep supplied aliases exactly unchanged in answers and tool arguments; the local host restores them. Never invent aliases, guess originals or assume a hidden label\'s type or meaning. Numeric aliases are labels, not the original magnitudes: do not calculate using their displayed digits. Use public names for new identifiers. If a particular answer truly requires a hidden fact, identify only that limitation and still complete the parts supported by visible context. Normal tool permissions and approval requirements still apply.\\n", "model": "gpt-6.1-sol", "store": false}',
]


def test_default_engine_output_byte_identical_to_base_commit(deterministic_nonce):
    """Verify default engine produces outputs 100% byte-identical to base commit (146babd)."""
    # #374 (2.18.0) made prose numbers public by default; the explicit
    # mask_numbers=True opt-in must still reproduce the base prose bytes.
    for text, golden in zip(TEST_PROSE, GOLDEN_PROSE_MAIN):
        deterministic_nonce.reset()
        s = gateway.GatewaySession(natural_language="auto", mask_numbers=True)
        res = s.mask(text)
        assert res == golden, f"Prose masking differed from base golden output on {text!r}"
        assert s.restore(res) == text

    for code, golden in zip(TEST_CODE, GOLDEN_CODE_MAIN):
        deterministic_nonce.reset()
        s = gateway.GatewaySession(natural_language="auto")
        res = s.mask(code, code=True)
        assert res == golden, f"Code masking differed from base golden output on {code!r}"
        assert s.restore(res) == code

    for payload, golden in zip(TEST_PAYLOADS, GOLDEN_PAYLOADS_MAIN):
        deterministic_nonce.reset()
        s = gateway.GatewaySession(mask_numbers=True)
        req = json.dumps(s.request(payload), sort_keys=True)
        assert req == golden, "Request transform differed from base golden output"


def test_default_prose_numbers_are_public_since_2_18(deterministic_nonce):
    """#374: the default forwards ordinary numbers; sensitive labelled numbers stay private."""
    s = gateway.GatewaySession(natural_language="auto")
    assert s.mask(TEST_PROSE[2]) == TEST_PROSE[2]
    masked = s.mask(TEST_PROSE[4])
    assert "71203489" not in masked and "재시도횟수: 2\n" in masked
    assert s.restore(masked) == TEST_PROSE[4]
    s = gateway.GatewaySession()
    content = s.request(TEST_PAYLOADS[0])["messages"][0]["content"]
    assert "000812405" not in content and s.restore(content) == TEST_PAYLOADS[0]["messages"][0]["content"]


def test_default_engine_output_byte_identity_across_runs(deterministic_nonce):
    """Verify default engine produces completely identical outputs across separate sessions."""
    for text in TEST_PROSE:
        deterministic_nonce.reset()
        s1 = gateway.GatewaySession(natural_language="auto")
        res1 = s1.mask(text)

        deterministic_nonce.reset()
        s2 = gateway.GatewaySession(natural_language="auto")
        res2 = s2.mask(text)

        assert res1 == res2
        assert s1.restore(res1) == text
        assert s2.restore(res2) == text

    for code in TEST_CODE:
        deterministic_nonce.reset()
        s1 = gateway.GatewaySession(natural_language="auto")
        res1 = s1.mask(code, code=True)

        deterministic_nonce.reset()
        s2 = gateway.GatewaySession(natural_language="auto")
        res2 = s2.mask(code, code=True)

        assert res1 == res2
        assert s1.restore(res1) == code
        assert s2.restore(res2) == code

    for payload in TEST_PAYLOADS:
        deterministic_nonce.reset()
        s1 = gateway.GatewaySession()
        req1 = json.dumps(s1.request(payload), sort_keys=True)

        deterministic_nonce.reset()
        s2 = gateway.GatewaySession()
        req2 = json.dumps(s2.request(payload), sort_keys=True)

        assert req1 == req2


def test_globals_restored_cleanly_after_every_profile(deterministic_nonce):
    """Proves that every candidate profile cleans up completely and leaves default engine byte-identical."""
    sample = "Project name: margin. device_serial: 000812405. retry_count: 3."

    deterministic_nonce.reset()
    base_session = gateway.GatewaySession()
    expected_default_masked = base_session.mask(sample)

    profiles = [
        ("doc_structure", None),
        ("doc_structure_policy", {"field_policy": {"Project": "always_mask"}}),
        ("numeric_context", None),
        ("instruction_concise", None),
        ("instruction_examples", None),
        ("local_arithmetic", None),
    ]

    for prof, pol in profiles:
        # Enter candidate profile
        with candidate_profile(prof, pol):
            c_session = gateway.GatewaySession()
            c_session.mask(sample)

        # After exiting candidate profile: verify default engine output is 100% byte-identical
        deterministic_nonce.reset()
        fresh_session = gateway.GatewaySession()
        after_masked = fresh_session.mask(sample)
        assert after_masked == expected_default_masked
        assert fresh_session.restore(after_masked) == sample


def test_default_baseline_unaffected_by_experiment_modules(deterministic_nonce):
    """Verify default engine behavior is completely unchanged when toggles are not activated."""
    sample = "| Customer | Amount |\n|---|---|\n| Acme Corp | 1234.56 |"

    deterministic_nonce.reset()
    s1 = gateway.GatewaySession()
    masked1 = s1.mask(sample)

    deterministic_nonce.reset()
    s2 = gateway.GatewaySession()
    masked2 = s2.mask(sample)

    assert masked1 == masked2
    assert s1.restore(masked1) == sample
    assert s2.restore(masked2) == sample
