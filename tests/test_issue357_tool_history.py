"""Assistant tool-only history keeps roles, call attribution and private arguments."""
import json

import pytest

from secure_gateway.gateway import GatewaySession


@pytest.mark.parametrize('content', ['omitted', None, ''])
@pytest.mark.parametrize('language', ['en', 'ko'])
def test_tool_only_assistant_role_and_parallel_call_ids_survive_replay(content, language):
    session = GatewaySession(natural_language=language)
    session.forced_rules = lambda: ('SyntheticPrivateLedger',)
    arguments = json.dumps({'path': '/tmp/SyntheticPrivateLedger.txt'})
    assistant = {'role': 'assistant', 'tool_calls': [
        {'id': call_id, 'type': 'function',
         'function': {'name': 'read_file', 'arguments': arguments}}
        for call_id in ('call_first', 'call_second')
    ]}
    if content != 'omitted':
        assistant['content'] = content
    messages = [assistant, *[
        {'role': 'tool', 'tool_call_id': call_id, 'content': result}
        for call_id, result in [('call_first', 'SyntheticPrivateLedger first result'),
                                ('call_second', 'SyntheticPrivateLedger second result')]
    ], {'role': 'user', 'content': 'Compare the second result with the first.'}]
    payload = {'model': 'fixture', 'messages': messages}
    for _ in range(2):
        forwarded = session.request(payload, dialect='chat_completions')
        history = forwarded['messages'][-4:]
        assert [message['role'] for message in history] == ['assistant', 'tool', 'tool', 'user']
        assert history[0]['tool_calls'][0]['id'] == history[1]['tool_call_id'] == 'call_first'
        assert history[0]['tool_calls'][1]['id'] == history[2]['tool_call_id'] == 'call_second'
        assert 'SyntheticPrivateLedger' not in json.dumps(forwarded, ensure_ascii=False)
        for call in history[0]['tool_calls']:
            assert json.loads(session.restore(call['function']['arguments'])) == json.loads(arguments)
        assert session.restore(history[1]['content']) == messages[1]['content']
        assert session.restore(history[2]['content']) == messages[2]['content']
        assert ('content' in history[0]) == ('content' in assistant)
        if 'content' in assistant:
            assert history[0]['content'] == content


def test_tool_call_shaped_data_does_not_gain_protocol_exceptions():
    session = GatewaySession(natural_language='en')
    session.forced_rules = lambda: ('assistant', 'SyntheticPrivateLedger')
    source = {'role': 'assistant', 'tool_calls': [{'id': 'SyntheticPrivateLedger'}]}
    masked = session.walk_data(source)
    assert 'assistant' not in json.dumps(masked)
    assert 'SyntheticPrivateLedger' not in json.dumps(masked)
