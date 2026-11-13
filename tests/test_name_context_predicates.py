"""#310 introducer guard (2.17.0): predicates and modifiers are never registered as names.

The name feature is on by default in gateway settings, so a prohibition or
condition after a name noun (``파일 이름은 바꾸지 말며``) must stay visible to the
model while a true introduction is still protected and restored exactly.
"""

import pytest

from secure_gateway import gateway
from secure_gateway.experiment_context import name_spans
from secure_gateway.gateway_features import GatewayFeatures, resolve_settings

ON = GatewayFeatures(contextual_name_spans=True)

PREDICATES = [
    ("파일 이름은 바꾸지 말고 요약해 주세요.", "바꾸지"),
    ("파일 이름은 바꾸지 말며 이유를 권고보다 앞에 적어 주세요.", "바꾸지"),
    ("프로젝트 이름은 수정하지 마세요.", "수정하지"),
    ("이유나 제품 이름은 덧붙이지 마세요.", "덧붙이지"),
    ("고객 이름은 바꿔 주세요.", "바꿔"),
    ("프로젝트 이름은 바꿀 수 없어요.", "바꿀"),
    ("회사 이름은 변경하면 안 됩니다.", "변경하면"),
    ("제품 이름은 공개하세요.", "공개하세요"),
    ("The file name must not change.", "must"),
    ("Name it later, after review.", "later"),
    ("Project name: to be decided later.", "to"),
    ("Customer name: must stay hidden until launch.", "must"),
]
INTRODUCERS = [
    ("프로젝트 이름은 흐름입니다. 흐름 일정은 비밀로 해 주세요.", "흐름"),
    ("프로젝트명은 구름; 회사명은 나무.", "구름"),
    ("고객명: 진흙. 진흙 관련 문서를 정리해.", "진흙"),
    ("Project name: drift. Review it.", "drift"),
    ("A project named Ember must ship quietly.", "Ember"),
    ("흐름 프로젝트를 검토해 주세요.", "흐름"),
]


def masked(text, features=ON):
    session = gateway.GatewaySession(natural_language="auto", features=features)
    output = session.request({"model": "fixture", "input": [{"role": "user", "content": text}]})["input"][0]["content"]
    assert session.restore(output) == text
    return output


@pytest.mark.parametrize(("text", "predicate"), PREDICATES)
def test_predicate_after_name_noun_stays_visible(text, predicate):
    start = text.index(predicate)
    assert all(not (a <= start < b) for a, b in name_spans(text))
    assert predicate in masked(text)
    # The default gateway selection behaves the same way.
    assert predicate in masked(text, resolve_settings({}, environ={})[0])


@pytest.mark.parametrize(("text", "name"), INTRODUCERS)
def test_true_introducer_is_still_protected(text, name):
    assert name not in masked(text)


def test_spaced_modifier_before_project_is_not_a_name():
    text = "가상 프로젝트 흐름의 문서 순서를 검토하고, 파일 이름은 바꾸지 말며 이유를 먼저 적어 주세요."
    spans = [text[a:b] for a, b in name_spans(text)]
    assert "가상" not in spans and "바꾸지" not in spans
    output = masked(text)
    assert output.startswith("가상 프로젝트") and "바꾸지 말며" in output
    vehicle = "가상 차량 프로젝트 자갈수레의 시험 일정을 정리해 주세요."
    assert "차량" not in [vehicle[a:b] for a, b in name_spans(vehicle)]


def test_forced_rules_and_existing_aliases_still_win():
    session = gateway.GatewaySession(natural_language="auto", features=ON)
    session.forced_rules = lambda: ("바꾸지",)
    text = "파일 이름은 바꾸지 말며 이유를 적어 주세요."
    output = session.request({"model": "fixture", "input": [{"role": "user", "content": text}]})["input"][0]["content"]
    assert "바꾸지" not in output and session.restore(output) == text
    # A name registered earlier in the conversation stays protected in a later prohibition.
    session = gateway.GatewaySession(natural_language="auto", features=ON)
    first = session.request({"model": "fixture", "input": [{"role": "user", "content": "프로젝트명은 흐름입니다."}]})
    assert "흐름" not in first["input"][0]["content"]
    later = "흐름 이름은 바꾸지 마세요."
    output = session.request({"model": "fixture", "input": [{"role": "user", "content": later}]})["input"][0]["content"]
    assert "흐름" not in output and "바꾸지 마세요" in output and session.restore(output) == later
