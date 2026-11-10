"""Verify wheel and sdist installs from a clean directory and environment."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import xml.etree.ElementTree as ET


def isolated_environment(work):
    """Do not inherit user credentials, synchronized homes or startup folders."""
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("ANTHROPIC_", "CLAUDE_", "OPENAI_", "CODEX_", "ORCA_"))
           and key not in {"PYTHONPATH", "PYTHONHOME", "SECURE_GATEWAY_CONTEXT_MODEL_DIR"}}
    home = work / "home"
    if home.resolve() == Path.home().resolve() or not home.resolve().is_relative_to(work.resolve()):
        raise ValueError("Lifecycle home is not isolated.")
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
                   cwd=work, env=env, check=True, capture_output=True, timeout=300)
    versions = {}
    for agent, binary in binaries.items():
        versions[agent] = subprocess.check_output([binary, "--version"], cwd=work,
                                                 env=env, text=True, stderr=subprocess.DEVNULL, timeout=30).strip()
    report = work / "native-release.xml"
    subprocess.run([str(python), "-I", "-m", "pytest", str(fixture), "-q",
                    "-k", "native_subscription_cli_gateway", f"--junitxml={report}"],
                   cwd=work, env=env, check=True, capture_output=True, timeout=300)
    cases = ET.parse(report).findall(".//testcase")
    if len(cases) != 4 or any(case.find(tag) is not None
                              for case in cases for tag in ("skipped", "failure", "error")):
        raise SystemExit("Native release gate requires four completed host/tool cases and no skips.")
    print(f"Native offline versions: {versions}")


# Content-free failure summary for the child lifecycle proof. It is shared with
# tests so the child and the tested helper cannot drift apart. It reports the
# HTTP status, the gateway's fixed error string (never provider text or fixture
# content) and provider request count, without logging filesystem paths.
LIFECYCLE_DIAGNOSTICS = r'''
import json

LIFECYCLE_GATEWAY_ERRORS = frozenset((
    'Upstream response could not be safely restored',
    'Upstream transport unavailable',
    'Privacy gateway local I/O failed; request could not be completed',
    'Upstream response size limit exceeded',
))
LIFECYCLE_UPSTREAM_TYPES = frozenset((
    'invalid_request_error', 'authentication_error', 'permission_error',
    'not_found_error', 'rate_limit_error', 'api_error', 'overloaded_error',
))

def lifecycle_http_diagnostic(step, status, body, provider_requests, work_name):
    try:
        error = json.loads(body.decode('utf-8')).get('error')
    except (ValueError, AttributeError, UnicodeDecodeError):
        error = None
    if isinstance(error, dict):  # sanitized upstream rejection: keep only its type
        kind = error.get('type')
        error = 'upstream:' + kind if isinstance(kind, str) and kind in LIFECYCLE_UPSTREAM_TYPES else 'upstream'
    elif not isinstance(error, str) or error not in LIFECYCLE_GATEWAY_ERRORS:
        error = 'unavailable'
    return {'step': step, 'status': status, 'gateway_error': error,
            'provider_requests': provider_requests}
'''
exec(LIFECYCLE_DIAGNOSTICS)


LIFECYCLE_PROCESSES = r'''
import os
import time


def process_alive(pid):
    """Check whether the recorded daemon process is still executing."""
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x00100000, False, pid)
        if not handle:
            if ctypes.get_last_error() == 87:
                return False
            raise OSError('Cannot inspect daemon process.')
        try:
            status = kernel.WaitForSingleObject(handle, 0)
            if status == 0:
                return False
            if status == 258:
                return True
            raise OSError('Cannot inspect daemon process.')
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # A zombie is no longer executing, and cannot hold the port or files.
    stat = '/proc/' + str(pid) + '/stat'
    if os.path.isfile(stat):
        try:
            with open(stat, encoding='ascii') as stream:
                if stream.read().rsplit(') ', 1)[1].startswith('Z '):
                    return False
        except (OSError, IndexError):
            pass
    return True


def wait_process_exit(pid):
    """Require the recorded daemon to exit within a bounded interval."""
    deadline = time.monotonic() + 10
    while process_alive(pid) and time.monotonic() < deadline:
        time.sleep(.05)
    assert not process_alive(pid), 'Daemon process survived shutdown.'
'''


LIFECYCLE_PROOF = LIFECYCLE_DIAGNOSTICS + LIFECYCLE_PROCESSES + r'''
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import sysconfig
from threading import Thread
import urllib.request

import tomlkit
from secure_gateway import __version__
from secure_gateway.gateway_install import healthy, installation_path, load_config

work = Path.cwd().resolve()
# macOS /var and Windows runner short names can differ from the canonical paths
# recorded in the installation manifest. Classify host files by file identity.
home = Path(os.environ['USERPROFILE']).resolve()
config = home / 'state/config.json'
codex = home / '.codex/config.toml'
claude = home / '.claude/settings.json'
stage = sys.argv[1]
cli_base = [str(Path(sys.executable).parent / ('secure-gateway.exe' if os.name == 'nt' else 'secure-gateway'))]

def cli(*args):
    return subprocess.check_output(cli_base + list(args), cwd=work, text=True, timeout=90, stderr=subprocess.DEVNULL)

def health_data(settings):
    request = urllib.request.Request(f"http://127.0.0.1:{settings['port']}/health",
                                    headers={'X-SecureGateway-Token': settings['token']})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=5) as response:
        return json.load(response)

def domain_policy(settings, enabled=None):
    request = urllib.request.Request(f"http://127.0.0.1:{settings['port']}/admin/api/domain-policy",
        data=json.dumps({'enabled': enabled}).encode() if enabled is not None else None,
        headers={'X-SecureGateway-Token': settings['token'], 'Content-Type': 'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=5) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:  # Older supported upgrade sources have no dictionaries.
            return None
        raise

def configure_tracker(provider_origin=None):
    """Instrument the disposable venv daemon and optionally route its upstream."""
    sitecustomize = Path(sysconfig.get_path('purelib')) / 'sitecustomize.py'
    assert not sitecustomize.exists()
    pid_file = home / 'lifecycle-daemon.pid'
    sitecustomize.write_text(
        "import os\n"
        "if os.environ.get('SG_LIFECYCLE_PID'):\n"
        "    import pathlib, secure_gateway.gateway as gateway\n"
        "    if os.environ.get('SG_LIFECYCLE_PROVIDER'):\n"
        "        gateway.UPSTREAMS['codex'] = os.environ['SG_LIFECYCLE_PROVIDER']\n"
        "    original = gateway.PrivacyGateway.__init__\n"
        "    def tracked(self, *args, **kwargs):\n"
        "        original(self, *args, **kwargs)\n"
        "        pathlib.Path(os.environ['SG_LIFECYCLE_PID']).write_text(str(os.getpid()))\n"
        "    gateway.PrivacyGateway.__init__ = tracked\n",
        encoding='utf-8')
    os.environ['SG_LIFECYCLE_PID'] = str(pid_file)
    if provider_origin is not None:
        os.environ['SG_LIFECYCLE_PROVIDER'] = provider_origin
    return sitecustomize, pid_file


def exercise_provider(settings):
    """Round-trip tool calls through the installed daemon and fake provider."""
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

    class QuietProvider(ThreadingHTTPServer):
        """Suppress request and exception content in server diagnostics."""
        def handle_error(self, *_):
            """Report only a fixed failure category."""
            print('Lifecycle provider failure.', file=sys.stderr)

    provider = QuietProvider(('127.0.0.1', 0), Provider)
    provider.payloads = []
    # The daemon has fixed production origins. Inject the loopback origin only
    # into this disposable venv; the public CLI still starts the real daemon.
    home.mkdir(parents=True, exist_ok=True)
    sitecustomize, pid_file = configure_tracker(f'http://127.0.0.1:{provider.server_port}')
    thread = Thread(target=provider.serve_forever, daemon=True)
    thread.start()
    previous_directory = Path.cwd()
    os.chdir(home)
    try:
        cli('gateway', 'ensure', '--config', str(config))
        pid = int(pid_file.read_text())
        assert process_alive(pid)
        health = health_data(settings)
        if stage == 'setup' and 'version' not in health:
            print('Previous release daemon version not reported by its health endpoint.')
        else:
            assert health['version'] == __version__
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        def send(value, step):
            request = urllib.request.Request(f"http://127.0.0.1:{settings['port']}/codex/responses",
                data=json.dumps(value).encode(), headers={'Content-Type': 'application/json',
                'Authorization': 'Bearer eyJ-offline-fixture-only',
                'X-SecureGateway-Token': settings['token']})
            try:
                with opener.open(request, timeout=20) as response:
                    return json.load(response)
            except urllib.error.HTTPError as exc:
                try:
                    body = exc.read(4096)
                finally:
                    exc.close()
                summary = lifecycle_http_diagnostic(step, exc.code, body, len(provider.payloads), work.name)
                print('LIFECYCLE_DIAGNOSTIC ' + json.dumps(summary, sort_keys=True), file=sys.stderr, flush=True)
                raise
        cases = ['normal'] if stage == 'setup' else ['normal', '2024_report', '\uace0\uac1d \ud3f4\ub354']
        for case in cases:
            private_file = Path('fixture_workspace') / case / 'ConfidentialCustomer.py'
            private_file.parent.mkdir(parents=True, exist_ok=True)
            private_file.write_text('ConfidentialCustomer alice@example.invalid', encoding='utf-8')
            payload = {'model': 'fixture', 'input': [
                {'role': 'user', 'content': 'Review ConfidentialCustomer.'}],
                'tools': [{'type': 'function', 'name': 'read_file', 'parameters': {
                    'type': 'object', 'properties': {'file_path': {'type': 'string', 'default': str(private_file)}},
                    'required': ['file_path']}}]}
            restored = send(payload, 'tool_call')['output'][0]
            assert restored['name'] == 'read_file'
            actual_path = Path(json.loads(restored['arguments'])['file_path'])
            assert actual_path == private_file
            tool_output = actual_path.read_text(encoding='utf-8')
            payload['input'].extend([restored, {'type': 'function_call_output', 'call_id': 'call_smoke',
                                      'output': tool_output}])
            result = send(payload, 'tool_result')
            assert result['output'][0]['content'][0]['text'] == tool_output
        assert len(provider.payloads) == 2 * len(cases)
        cli('gateway', 'stop', '--config', str(config))
        wait_process_exit(pid)
    finally:
        try:
            cli('gateway', 'stop', '--config', str(config))
        finally:
            provider.shutdown()
            provider.server_close()
            thread.join(timeout=5)
            sitecustomize.unlink(missing_ok=True)
            del os.environ['SG_LIFECYCLE_PROVIDER']
            del os.environ['SG_LIFECYCLE_PID']
            pid_file.unlink(missing_ok=True)
            os.chdir(previous_directory)
            assert not thread.is_alive()


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
        if domain_policy(settings) is not None:
            enabled = {'defense': False, 'automotive': True, 'semiconductor': False}
            assert domain_policy(settings, enabled)['enabled'] == enabled
            (home / 'expected-domain-policy.json').write_text(json.dumps(enabled), encoding='utf-8')
        manifest = json.loads(installation_path(config).read_text(encoding='utf-8'))
        for name in manifest['files']:
            assert Path(name).resolve().is_relative_to(home.resolve()), name
        cli('gateway', 'stop', '--config', str(config))
        assert not healthy(settings)
        exercise_provider(settings)
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
        expected_policy = home / 'expected-domain-policy.json'
        if expected_policy.exists():
            assert domain_policy(settings)['enabled'] == json.loads(expected_policy.read_text(encoding='utf-8'))
        cli('gateway', 'stop', '--config', str(config))
        assert not healthy(settings)

        exercise_provider(settings)

        # Track the actual restarted daemon through uninstall, not just health.
        sitecustomize, pid_file = configure_tracker()
        try:
            cli('gateway', 'ensure', '--config', str(config))
            pid = int(pid_file.read_text())
            assert process_alive(pid)
            assert health_data(settings)['version'] == __version__
            manifest = json.loads(installation_path(config).read_text(encoding='utf-8'))
            hosts = {codex.resolve(), claude.resolve()}
            startup = [Path(name) for name in manifest['files'] if Path(name).resolve() not in hosts]
            cli('gateway', 'uninstall', '--config', str(config))
            assert not healthy(settings)
            wait_process_exit(pid)
            assert not installation_path(config).exists()
            assert all(not path.exists() for path in startup)
        finally:
            sitecustomize.unlink(missing_ok=True)
            os.environ.pop('SG_LIFECYCLE_PID', None)
            pid_file.unlink(missing_ok=True)
        value = tomlkit.parse(codex.read_text(encoding='utf-8'))
        assert 'model_provider' not in value
        assert 'secure_gateway_subscription' not in value.get('model_providers', {})
        assert value['hooks']['state'] == 'later-runtime-edit'
        value = json.loads(claude.read_text(encoding='utf-8'))
        assert value == {'theme': 'later-user-edit', 'env': {'OTHER': 'keep'}}
        for path in (codex.parent / 'auth.json', claude.parent / '.credentials.json'):
            assert path.read_bytes() == b'synthetic-login-cache-do-not-change'
        print(json.dumps({'stage': stage, 'version': __version__, 'provider_requests': 6,
                          'tool_roundtrip': True, 'user_edits_preserved': True}))
    finally:
        if config.exists():
            cli('gateway', 'stop', '--config', str(config))
'''


def sanitized_child_source(source):
    """Wrap child source so failures disclose only type and line number."""
    return ("import sys\ntry:\n" + textwrap.indent(source, "    ")
            + "\nexcept Exception as exc:\n"
              "    trace = exc.__traceback__\n"
              "    while trace.tb_next is not None:\n"
              "        trace = trace.tb_next\n"
              "    print('Lifecycle failure: ' + type(exc).__name__ + ' line=' + str(trace.tb_lineno), file=sys.stderr)\n"
              "    sys.exit(1)\n")


def verify_lifecycle(python, work, env, stage="all"):
    """Run the isolated installed-artifact lifecycle stage."""
    result = subprocess.run([str(python), "-I", "-c", sanitized_child_source(LIFECYCLE_PROOF), stage],
                            cwd=work, env=env, timeout=360)
    if result.returncode:
        raise SystemExit("Installed lifecycle proof failed.")


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
from secure_gateway.evaluation_cli import evaluate
from secure_gateway.evaluation_reliable import verify_reference_audit
from secure_gateway.evaluation_statistics import repeated_statistics
assert 'reliable' in evaluate.commands
assert 'supplement-grades' in evaluate.commands['reliable'].commands
assert callable(verify_reference_audit) and callable(repeated_statistics)
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
                           cwd=work, env=env, check=True, capture_output=True)
            python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            if previous is not None:
                subprocess.run(["uv", "pip", "install", "--python", str(python), str(previous)],
                               cwd=work, env=env, check=True, capture_output=True, timeout=600)
                previous_version = subprocess.check_output(
                    [str(python), "-I", "-c", "from importlib.metadata import version; print(version('secure-gateway'))"],
                    cwd=work, env=env, text=True, stderr=subprocess.DEVNULL, timeout=30).strip()
                verify_lifecycle(python, work, env, "setup")
            subprocess.run(["uv", "pip", "install", "--python", str(python), str(distribution)],
                           cwd=work, env=env, check=True, capture_output=True, timeout=600)
            expected = subprocess.check_output([str(python), "-I", "-c", proof],
                                               cwd=work, env=env, text=True, stderr=subprocess.DEVNULL).strip()
            executable = venv / ("Scripts/secure-gateway.exe" if os.name == "nt" else "bin/secure-gateway")
            reported = subprocess.check_output([str(executable), "--version"],
                                               cwd=work, env=env, text=True, stderr=subprocess.DEVNULL)
            if not reported.strip().endswith(expected):
                raise SystemExit("CLI version disagrees with installed package.")
            masked = subprocess.check_output(
                [str(executable), "mask", "--json-output"],
                input=b"ConfidentialCustomer", cwd=work, env=env, stderr=subprocess.DEVNULL,
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
    try:
        main()
    except Exception as exc:
        print("Package lifecycle failure: " + type(exc).__name__, file=sys.stderr)
        sys.exit(1)
