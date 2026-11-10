"""Build the reviewed prior release tag without altering the checkout."""
import argparse
import io
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

PREVIOUS_RELEASE_TAG = 'v2.4.0'
PREVIOUS_RELEASE_COMMIT = '42a6fed6adc510e1e547a8aac2f53be69ed23a38'


def verify_tag(root, tag, expected):
    """Resolve a release tag and require the reviewed commit identity."""
    try:
        actual = subprocess.check_output(
            ['git', '-C', str(root), 'rev-parse', '--verify', tag + '^{commit}'],
            stderr=subprocess.DEVNULL, timeout=30).decode('ascii').strip()
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise ValueError('Release tag could not be resolved') from None
    if actual != expected:
        raise ValueError('Release tag does not match pinned commit')
    return actual


def main():
    """Build a wheel from the immutable previous-release source archive."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--out-dir', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    commit = verify_tag(root, PREVIOUS_RELEASE_TAG, PREVIOUS_RELEASE_COMMIT)
    with tempfile.TemporaryDirectory(prefix='sg-previous-release-') as temporary:
        archive_bytes = subprocess.check_output(
            ['git', '-C', str(root), '-c', 'core.autocrlf=false', 'archive', commit],
            stderr=subprocess.DEVNULL, timeout=120)
        with tarfile.open(fileobj=io.BytesIO(archive_bytes)) as archive:
            archive.extractall(temporary, filter='data')
        subprocess.run(['uv', 'build', temporary, '--wheel', '--out-dir', str(args.out_dir.resolve())],
                       check=True, capture_output=True, timeout=600)
    print('Previous release source wheel built.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('Release source failure: ' + type(exc).__name__, file=sys.stderr)
        sys.exit(1)
