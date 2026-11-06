"""Offline gateway, local MCP tool and skill-text boundary checks."""
import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from secure_gateway.gateway import GatewaySession
from secure_gateway.server import app, vault


def test_mcp_stdio_client_can_call_mask_tool():
    async def run():
        params = StdioServerParameters(command=sys.executable, args=["-m", "secure_gateway.cli", "serve"])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                tools = await client.list_tools()
                assert any(tool.name == "mask_text" for tool in tools.tools)
                result = await client.call_tool("mask_text", {"text": "Maribel person@example.invalid", "language": "en"})
                assert not result.is_error
                output = json.loads(result.content[0].text)["masked_text"]
                assert "Maribel" not in output and "person@example.invalid" not in output
    asyncio.run(run())


def test_gateway_restores_mcp_tool_call_and_masks_the_real_local_tool_result():
    gateway = GatewaySession()
    private = "Maribel person@example.invalid"
    request = {
        "model": "fixture",
        "input": [{"role": "user", "content": f"Review {private}"}],
        "tools": [{"type": "function", "name": "mask_text", "parameters": {
            "type": "object", "properties": {"text": {"type": "string"}},
            "required": ["text"]}}],
    }
    forwarded = gateway.request(request, dialect="responses")
    tool = forwarded["tools"][0]
    parameter = next(iter(tool["parameters"]["properties"]))
    assert tool["parameters"]["required"] == [parameter]
    assert private not in json.dumps(forwarded, ensure_ascii=False)

    alias = gateway.mask(private)
    remote = {"output": [{"type": "function_call", "name": tool["name"],
                           "call_id": "fixture-call", "arguments": json.dumps({parameter: alias})}]}
    response = gateway.response(json.dumps(remote).encode(), "application/json", dialect="responses")
    call = json.loads(response)["output"][0]
    assert call["name"] == "mask_text"
    assert json.loads(call["arguments"]) == {"text": private}

    result = asyncio.run(app.call_tool(call["name"], json.loads(call["arguments"])))
    assert not result.is_error
    mcp_output = result.content[0].text
    mcp_data = json.loads(mcp_output)
    try:
        assert "Maribel" not in mcp_data["masked_text"]
        followup = gateway.request({"model": "fixture", "input": [{
            "type": "function_call_output", "call_id": "fixture-call", "output": mcp_output,
        }]}, dialect="responses")
        output = followup["input"][0]["output"]
        assert private not in output
        assert gateway.restore(output) == mcp_output
    finally:
        vault.clear_session(mcp_data["session_id"])


def test_skill_instructions_are_restorable_and_private_content_is_masked():
    gateway = GatewaySession()
    skill_text = "Read SKILL.md before using this skill. Follow the instructions for Maribel."
    payload = {"model": "fixture", "input": [{"role": "developer", "content": [
        {"type": "input_text", "text": skill_text},
    ]}]}
    forwarded = gateway.request(payload, dialect="responses")
    text = forwarded["input"][0]["content"][0]["text"]
    assert "Maribel" not in text
    for word in ("Read", "SKILL.md", "using", "skill", "Follow", "instructions"):
        assert word in text
    assert gateway.restore(text) == skill_text


def test_backtick_skill_filename_is_usable_and_restorable():
    gateway = GatewaySession()
    text = "Read `SKILL.md` before using this skill."
    masked = gateway.mask(text)
    assert "`SKILL.md`" in masked
    assert gateway.restore(masked) == text
