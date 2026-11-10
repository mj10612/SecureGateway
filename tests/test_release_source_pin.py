"""The previous release tag must resolve to its reviewed immutable commit."""
import importlib.util
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_upgrade_source', ROOT / 'scripts/build_upgrade_source.py')
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_tag_movement_is_rejected(tmp_path):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(tmp_path), '-c', 'core.hooksPath=',
                                        '-c', 'commit.gpgsign=false', *args],
                                       stderr=subprocess.DEVNULL).decode().strip()

    git('init', '-q')
    git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        'commit', '--allow-empty', '-qm', 'fixture')
    git('tag', 'v-fixture')
    commit = git('rev-parse', 'HEAD')
    assert module.verify_tag(tmp_path, 'v-fixture', commit) == commit
    with pytest.raises(ValueError, match='Release tag does not match pinned commit'):
        module.verify_tag(tmp_path, 'v-fixture', '0' * 40)
