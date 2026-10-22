"""Validate nested property-name constraints against actual JSON Schema semantics."""
from copy import deepcopy

from jsonschema import Draft202012Validator
import pytest

from secure_gateway.gateway import GatewaySession


@pytest.mark.parametrize("name", ["command", "privateProperty"])
@pytest.mark.parametrize("constraint", [
    {"allOf": [{"enum": ["NAME"]}]},
    {"anyOf": [{"const": "NAME"}, {"const": "other"}]},
    {"oneOf": [{"enum": ["NAME"]}, {"const": "other"}]},
    {"not": {"not": {"const": "NAME"}}},
    {"if": {"const": "NAME"}, "then": {"enum": ["NAME"]}, "else": False},
])
def test_nested_name_constraints_preserve_acceptance(name, constraint):
    def substitute(value):
        if isinstance(value, str):
            return name if value == "NAME" else value
        if isinstance(value, list):
            return [substitute(item) for item in value]
        if isinstance(value, dict):
            return {key: substitute(item) for key, item in value.items()}
        return value
    schema = {"type": "object", "properties": {name: {"type": "integer"}},
              "required": [name], "propertyNames": substitute(constraint)}
    session = GatewaySession()
    masked = session.walk(schema)
    alias = masked["required"][0]
    assert Draft202012Validator(schema).is_valid({name: 1})
    assert Draft202012Validator(masked).is_valid({alias: 1})
    assert not Draft202012Validator(masked).is_valid({"unknownPrivateKey": 1})
    assert session.walk(masked, restore=True) == schema


@pytest.mark.parametrize("keyword", ["$ref", "$dynamicRef"])
def test_local_ref_shared_by_names_and_values_is_specialized_without_value_leak(keyword):
    schema = {
        "type": "object",
        "$defs": {"privateDefinition": {"allOf": [{"enum": ["command"]}]}},
        "properties": {"command": {keyword: "#/$defs/privateDefinition"}},
        "required": ["command"],
        "propertyNames": {keyword: "#/$defs/privateDefinition"},
    }
    original = deepcopy(schema)
    session = GatewaySession()
    masked = session.walk(schema)
    document = session.values({"command": "command"})
    assert document["command"] != "command"  # Ordinary data remains private.
    assert Draft202012Validator(schema).is_valid({"command": "command"})
    assert Draft202012Validator(masked).is_valid(document)
    assert not Draft202012Validator(masked).is_valid({"command": "command"})
    assert schema == original


def test_ref_siblings_are_conjoined_instead_of_overwriting_target_constraints():
    schema = {
        "$defs": {"allowed": {"enum": ["command", "privateName"]}},
        "propertyNames": {"$ref": "#/$defs/allowed", "not": {"const": "privateName"}},
    }
    session = GatewaySession()
    masked = session.walk(schema)
    validator = Draft202012Validator(masked)
    assert validator.is_valid({"command": 1})
    assert not validator.is_valid({session.schema_name("privateName"): 1})


def test_recursive_property_name_ref_fails_explicitly_and_regular_recursive_ref_survives():
    recursive = {"$defs": {"loop": {"$ref": "#/$defs/loop"}},
                 "propertyNames": {"$ref": "#/$defs/loop"}}
    with pytest.raises(ValueError, match="Recursive propertyNames"):
        GatewaySession().walk(recursive)
    ordinary = {"$defs": {"loop": {"$ref": "#/$defs/loop"}}, "$ref": "#/$defs/loop"}
    session = GatewaySession()
    assert session.walk(session.walk(ordinary), restore=True) == ordinary


def test_nonstring_name_enum_preserves_unsatisfiable_constraints():
    schema = {"propertyNames": {"allOf": [{"enum": [42, None]}]}}
    masked = GatewaySession().walk(schema)
    assert Draft202012Validator(masked).is_valid({})
    assert not Draft202012Validator(masked).is_valid({"command": 1})


def test_full_responses_request_nested_name_schema_is_usable():
    schema = {"type": "object", "properties": {"command": {"type": "string"}},
              "required": ["command"], "propertyNames": {"allOf": [{"enum": ["command"]}]}}
    payload = {"input": "hello", "tools": [{"type": "function", "name": "testTool", "parameters": schema}]}
    masked = GatewaySession().request(payload, dialect="responses")
    assert Draft202012Validator(masked["tools"][0]["parameters"]).is_valid({"command": "ok"})
