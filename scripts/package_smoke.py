"""Verify wheel and sdist installs from a clean directory and environment."""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist-dir", type=Path, default=root / "dist")
    args = parser.parse_args()
    directory = args.dist_dir.resolve()
    distributions = sorted(directory.glob("*.whl")) + sorted(directory.glob("*.tar.gz"))
    if len(distributions) != 2:
        raise SystemExit("Expected exactly one wheel and one source distribution.")
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
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
for name in ('index.html', 'app.js', 'style.css', 'favicon.svg'):
    assert files('secure_gateway').joinpath('admin', name).is_file(), name
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
print(__version__)
"""
    for distribution in distributions:
        with tempfile.TemporaryDirectory(prefix="securegateway-package-") as temporary:
            work = Path(temporary)
            venv = work / "environment"
            subprocess.run(["uv", "venv", str(venv), "--python", sys.executable],
                           cwd=work, env=env, check=True)
            python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            subprocess.run(["uv", "pip", "install", "--python", str(python), str(distribution)],
                           cwd=work, env=env, check=True)
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
            print(f"Verified {distribution.name}: {expected}")


if __name__ == "__main__":
    main()
