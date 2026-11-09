"""Verify wheel and sdist installs from a clean directory and environment."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


def isolated_environment(work):
    """Do not inherit user credentials, synchronized homes or startup folders."""
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("ANTHROPIC_", "CLAUDE_", "OPENAI_", "CODEX_", "ORCA_"))
           and key not in {"PYTHONPATH", "PYTHONHOME", "SECURE_GATEWAY_CONTEXT_MODEL_DIR"}}
    home = work / "home"
    env.update({"HOME": str(home), "USERPROFILE": str(home),
                "APPDATA": str(home / "AppData/Roaming"),
                "LOCALAPPDATA": str(home / "AppData/Local"),
                "XDG_CONFIG_HOME": str(home / ".config"),
                "CODEX_HOME": str(home / ".codex"),
                "CLAUDE_CONFIG_DIR": str(home / ".claude")})
    return env


def native_binaries(env):
    """A required native gate must fail before any misleading skip result."""
    result = {}
    for agent in ("CLAUDE", "CODEX"):
        key = f"SECURE_GATEWAY_{agent}_BINARY"
        value = env.get(key)
        binary = shutil.which(value) if value else None
        if not binary:
            raise SystemExit(f"Required native host unavailable: {key}. Configure a pinned executable.")
        result[agent.lower()] = binary
    return result


def verify_native(python, work, env, root, binaries):
    """Run the real host fixtures against this installed artifact, offline."""
    fixture = work / "test_native_release.py"
    fixture.write_bytes((root / "tests/test_gateway_hosts.py").read_bytes())
    subprocess.run(["uv", "pip", "install", "--python", str(python), "pytest"],
                   cwd=work, env=env, check=True, timeout=300)
    versions = {}
    for agent, binary in binaries.items():
        versions[agent] = subprocess.check_output([binary, "--version"], cwd=work,
                                                 env=env, text=True, timeout=30).strip()
    report = work / "native-release.xml"
    subprocess.run([str(python), "-I", "-m", "pytest", str(fixture), "-q",
                    "-k", "native_subscription_cli_gateway", f"--junitxml={report}"],
                   cwd=work, env=env, check=True, timeout=300)
    cases = ET.parse(report).findall(".//testcase")
    if len(cases) != 4 or any(case.find(tag) is not None
                              for case in cases for tag in ("skipped", "failure", "error")):
        raise SystemExit("Native release gate requires four completed host/tool cases and no skips.")
    print(f"Native offline versions: {versions}")


LIFECYCLE_PROOF = r'''
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from threading import Thread
import urllib.request

import tomlkit
from secure_gateway import __version__
from secure_gateway.gateway import PrivacyGateway
from secure_gateway.gateway_install import healthy, installation_path, load_config

work = Path.cwd().resolve()
# macOS /var and Windows runner short names can differ from the canonical paths
# recorded in the installation manifest. Classify host files by file identity.
home = Path(os.environ['USERPROFILE']).resolve()
config = home / 'state/config.json'
codex = home / '.codex/config.toml'
claude = home / '.claude/settings.json'
stage = sys.argv[1]
cli_base = [sys.executable, '-I', '-m', 'secure_gateway']

def cli(*args):
    return subprocess.check_output(cli_base + list(args), cwd=work, text=True, timeout=90)

def health_data(settings):
    request = urllib.request.Request(f"http://127.0.0.1:{settings['port']}/health",
                                    headers={'X-SecureGateway-Token': settings['token']})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=5) as response:
        return json.load(response)

if stage in ('setup', 'all'):
    codex.parent.mkdir(parents=True)
    claude.parent.mkdir(parents=True)
    codex.write_text('# artifact lifecycle\nmodel = "fixture"\n', encoding='utf-8')
    claude.write_text(json.dumps({'theme': 'original', 'env': {'OTHER': 'keep'}}), encoding='utf-8')
    for path in (codex.parent / 'auth.json', claude.parent / '.credentials.json'):
        path.write_bytes(b'synthetic-login-cache-do-not-change')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    try:
        cli('gateway', 'install', '--agent', 'both', '--config', str(config), '--port', str(port))
        settings = load_config(config)
        assert healthy(settings)
        manifest = json.loads(installation_path(config).read_text(encoding='utf-8'))
        for name in manifest['files']:
            assert Path(name).resolve().is_relative_to(home.resolve()), name
        cli('gateway', 'stop', '--config', str(config))
        assert not healthy(settings)
    finally:
        if config.exists():
            cli('gateway', 'stop', '--config', str(config))
    value = tomlkit.parse(codex.read_text(encoding='utf-8'))
    value['hooks'] = {'state': 'later-runtime-edit'}
    codex.write_text(tomlkit.dumps(value), encoding='utf-8')
    value = json.loads(claude.read_text(encoding='utf-8'))
    value['theme'] = 'later-user-edit'
    claude.write_text(json.dumps(value), encoding='utf-8')

if stage in ('finish', 'all'):
    settings = load_config(config)
    try:
        cli('gateway', 'ensure', '--config', str(config))
        assert health_data(settings)['version'] == __version__
        cli('gateway', 'stop', '--config', str(config))
        assert not healthy(settings)

        class Provider(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                self.server.payloads.append(payload)
                assert 'ConfidentialCustomer' not in json.dumps(payload)
                assert 'alice@example.invalid' not in json.dumps(payload)
                item = payload['input'][-1]
                if item.get('type') != 'function_call_output':
                    tool = payload['tools'][0]
                    properties = tool['parameters']['properties']
                    key = next(iter(properties))
                    result = {'output': [{'type': 'function_call', 'call_id': 'call_smoke',
                              'name': tool['name'], 'arguments': json.dumps({key: properties[key]['default']})}]}
                else:
                    assert item['type'] == 'function_call_output'
                    result = {'output': [{'type': 'message', 'role': 'assistant',
                              'content': [{'type': 'output_text', 'text': item['output']}]}]}
                data = json.dumps(result).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
        provider.payloads = []
        gateway = PrivacyGateway(('127.0.0.1', settings['port']), settings['token'],
                                 {'codex': f'http://127.0.0.1:{provider.server_port}'},
                                 state_dir=config.parent / 'sessions')
        threads = [Thread(target=server.serve_forever, daemon=True)
                   for server in (provider, gateway)]
        for thread in threads:
            thread.start()
        try:
            private_file = work / 'private/ConfidentialCustomer.py'
            private_file.parent.mkdir()
            private_file.write_text('ConfidentialCustomer alice@example.invalid', encoding='utf-8')
            payload = {'model': 'fixture', 'input': [
                {'role': 'user', 'content': 'Review ConfidentialCustomer.'}],
                'tools': [{'type': 'function', 'name': 'read_file', 'parameters': {
                    'type': 'object', 'properties': {'file_path': {'type': 'string', 'default': str(private_file)}},
                    'required': ['file_path']}}]}
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            def send(value):
                request = urllib.request.Request(f"http://127.0.0.1:{settings['port']}/codex/responses",
                    data=json.dumps(value).encode(), headers={'Content-Type': 'application/json',
                    'Authorization': 'Bearer eyJ-offline-fixture-only',
                    'X-SecureGateway-Token': settings['token']})
                with opener.open(request, timeout=20) as response:
                    return json.load(response)
            restored = send(payload)['output'][0]
            assert restored['name'] == 'read_file'
            actual_path = Path(json.loads(restored['arguments'])['file_path'])
            assert actual_path == private_file
            tool_output = actual_path.read_text(encoding='utf-8')
            payload['input'].extend([restored, {'type': 'function_call_output', 'call_id': 'call_smoke',
                                      'output': tool_output}])
            result = send(payload)
            assert result['output'][0]['content'][0]['text'] == tool_output
            assert len(provider.payloads) == 2
            cli('gateway', 'stop', '--config', str(config))
        finally:
            gateway.shutdown()
            gateway.server_close()
            provider.shutdown()
            provider.server_close()
            for thread in threads:
                thread.join(timeout=5)

        # Restart the real installed CLI daemon after the local provider proof.
        cli('gateway', 'ensure', '--config', str(config))
        assert health_data(settings)['version'] == __version__
        manifest = json.loads(installation_path(config).read_text(encoding='utf-8'))
        hosts = {codex.resolve(), claude.resolve()}
        startup = [Path(name) for name in manifest['files'] if Path(name).resolve() not in hosts]
        cli('gateway', 'uninstall', '--config', str(config))
        assert not healthy(settings)
        assert not installation_path(config).exists()
        assert all(not path.exists() for path in startup)
        value = tomlkit.parse(codex.read_text(encoding='utf-8'))
        assert 'model_provider' not in value
        assert 'secure_gateway_subscription' not in value.get('model_providers', {})
        assert value['hooks']['state'] == 'later-runtime-edit'
        value = json.loads(claude.read_text(encoding='utf-8'))
        assert value == {'theme': 'later-user-edit', 'env': {'OTHER': 'keep'}}
        for path in (codex.parent / 'auth.json', claude.parent / '.credentials.json'):
            assert path.read_bytes() == b'synthetic-login-cache-do-not-change'
        print(json.dumps({'stage': stage, 'version': __version__, 'provider_requests': 2,
                          'tool_roundtrip': True, 'user_edits_preserved': True}))
    finally:
        if config.exists():
            cli('gateway', 'stop', '--config', str(config))
'''


def verify_lifecycle(python, work, env, stage="all"):
    subprocess.run([str(python), "-I", "-c", LIFECYCLE_PROOF, stage], cwd=work,
                   env=env, check=True, timeout=360)


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist-dir", type=Path, default=root / "dist")
    parser.add_argument("--upgrade-from", type=Path,
                        help="Install this previous release first, then verify upgrade to each artifact.")
    parser.add_argument("--require-native", action="store_true",
                        help="Require both configured native binaries and four offline host/tool cases; no skips.")
    args = parser.parse_args()
    directory = args.dist_dir.resolve()
    distributions = sorted(directory.glob("*.whl")) + sorted(directory.glob("*.tar.gz"))
    if (len(distributions) != 2 or len(list(directory.glob("*.whl"))) != 1
            or len(list(directory.glob("*.tar.gz"))) != 1):
        raise SystemExit("Expected exactly one wheel and one source distribution.")
    binaries = native_binaries(os.environ) if args.require_native else None
    previous = args.upgrade_from.resolve() if args.upgrade_from else None
    if previous is not None and not previous.is_file():
        raise SystemExit("--upgrade-from must name an existing distribution.")
    proof = """
from importlib.metadata import version, distribution
from importlib.util import find_spec
from importlib.resources import files
from secure_gateway import __version__
from secure_gateway.server import app, get_privacy_status
from secure_gateway.command_capture import capture_command
import json
import sys
assert version('secure-gateway') == __version__ == app.version
assert app.name == 'SecureGateway'
assert find_spec('secure_mcp') is None
assert find_spec('secure_router') is None
assert any(e.name == 'secure-gateway' and e.value == 'secure_gateway.cli:main'
           for e in distribution('secure-gateway').entry_points)
assert json.loads(get_privacy_status())['version'] == __version__
from secure_gateway.evaluation import load_corpus, select_cases
assert len(select_cases(load_corpus(), 'smoke')) == 8
for name in ('index.html', 'app.js', 'style.css', 'favicon.svg'):
    assert files('secure_gateway').joinpath('admin', name).is_file(), name
assert files('secure_gateway').joinpath('data').joinpath('context_head.json').is_file()
from secure_gateway.context_assets import model_metadata
assert model_metadata()['download_bytes'] == 135430652
result = capture_command([sys.executable, '-c', "print('smoke')"],
                         timeout=5, max_output_bytes=128)
assert result.returncode == 0 and result.stdout.strip() == b'smoke'
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.engine.code_parser import LANGUAGE_KEYWORDS
from secure_gateway.session import PrivacySession
assert len(LANGUAGE_KEYWORDS) == 24
for language, text in [('zh', '\\u5f20\\u4f1f\\u5728\\u516c\\u53f8'),
                       ('ja', '\\u5c71\\u7530\\u306f\\u4f1a\\u793e'),
                       ('hi', '\\u0938\\u0940\\u092e\\u093e')]:
    session = PrivacySession('distribution-languages')
    engine = MaskingEngine()
    masked = engine.mask_text(text, session.session_id, session.generator,
                              session.forward_store, session.reverse_store, language=language)
    assert masked.masked_text != text
    assert engine.unmask(masked.masked_text, session.session_id, session.reverse_store,
                         strict=True).unmasked_text == text
from secure_gateway.models import MaskMode
session = PrivacySession('distribution-uncommon')
engine = MaskingEngine()
masked = engine.mask_text('the meeting uses zorblyx', session.session_id,
                          session.generator, session.forward_store, session.reverse_store,
                          mode=MaskMode.UNCOMMON_WORDS)
assert 'meeting' in masked.masked_text and 'zorblyx' not in masked.masked_text
assert engine.unmask(masked.masked_text, session.session_id, session.reverse_store,
                     strict=True).unmasked_text == 'the meeting uses zorblyx'
from secure_gateway.gateway import GatewaySession
session = GatewaySession(natural_language='en')
text = 'Compare the options for Zorvexa. Then summarize the result without guessing.'
masked = session.mask(text)
assert masked.startswith('Compare the options') and 'Then summarize' in masked
assert 'Zorvexa' not in masked and session.restore(masked) == text
assert session.mask(text) == masked
print(__version__)
"""
    for distribution in distributions:
        with tempfile.TemporaryDirectory(prefix="securegateway-package-") as temporary:
            work = Path(temporary)
            env = isolated_environment(work)
            venv = work / "environment"
            subprocess.run(["uv", "venv", str(venv), "--python", sys.executable],
                           cwd=work, env=env, check=True)
            python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            if previous is not None:
                subprocess.run(["uv", "pip", "install", "--python", str(python), str(previous)],
                               cwd=work, env=env, check=True, timeout=600)
                previous_version = subprocess.check_output(
                    [str(python), "-I", "-c", "from importlib.metadata import version; print(version('secure-gateway'))"],
                    cwd=work, env=env, text=True, timeout=30).strip()
                verify_lifecycle(python, work, env, "setup")
            subprocess.run(["uv", "pip", "install", "--python", str(python), str(distribution)],
                           cwd=work, env=env, check=True, timeout=600)
            expected = subprocess.check_output([str(python), "-I", "-c", proof],
                                               cwd=work, env=env, text=True).strip()
            reported = subprocess.check_output([str(python), "-I", "-m", "secure_gateway", "--version"],
                                               cwd=work, env=env, text=True)
            if not reported.strip().endswith(expected):
                raise SystemExit("CLI version disagrees with installed package.")
            masked = subprocess.check_output(
                [str(python), "-I", "-m", "secure_gateway", "mask", "--json-output"],
                input=b"ConfidentialCustomer", cwd=work, env=env,
            )
            if b"ConfidentialCustomer" in masked:
                raise SystemExit("Installed CLI did not mask stdin.")
            if previous is not None:
                if previous_version == expected:
                    raise SystemExit("--upgrade-from must contain a different package version; same-version reinstall is not upgrade proof.")
                verify_lifecycle(python, work, env, "finish")
                print(f"Verified artifact upgrade {previous_version} -> {expected}")
            else:
                verify_lifecycle(python, work, env)
                print("Verified clean artifact lifecycle; cross-version upgrade not measured (use --upgrade-from).")
            if binaries is not None:
                verify_native(python, work, env, root, binaries)
            else:
                print("Native Claude/Codex host compatibility not measured (use --require-native).")
            print(f"Verified {distribution.name}: {expected}")


if __name__ == "__main__":
    main()
