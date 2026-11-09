"""Loader integrity/limits are distinct from actual language/privacy quality."""
from hashlib import sha256
import gzip
import json

import pytest

import secure_gateway.gateway_public_vocabulary as vocabulary


@pytest.fixture
def source(tmp_path, monkeypatch):
    data = {'schema_version': 1, 'data_version': 'unit', 'language': 'en',
            'words': ['compare', 'syntheticordinaryqzx'], 'name_exclusions': ['syntheticpersonqzx']}
    blob = gzip.compress(json.dumps(data).encode(), mtime=0)
    (tmp_path / 'en.json.gz').write_bytes(blob)
    metadata = {'file': 'en.json.gz', 'sha256': sha256(blob).hexdigest(), 'bytes': len(blob),
                'words': 2, 'name_exclusions': 1}
    (tmp_path / 'manifest.json').write_text(json.dumps({'schema_version': 1, 'data_version': 'unit',
        'languages': {lang: metadata for lang in vocabulary._LANGUAGES}}), encoding='utf8')
    monkeypatch.setattr(vocabulary, '_resource_root', lambda: tmp_path)
    vocabulary._manifest.cache_clear()
    vocabulary.lexicon.cache_clear()
    yield tmp_path
    vocabulary._manifest.cache_clear()
    vocabulary.lexicon.cache_clear()


def test_pinned_offline_words_and_name_exclusions_are_separate(source):
    result = vocabulary.lexicon('en')
    assert 'syntheticordinaryqzx' in result.words
    assert 'syntheticpersonqzx' not in result.words and 'syntheticpersonqzx' in result.names
    assert result is vocabulary.lexicon('en')


def test_corrupt_data_is_rejected_without_fallback(source):
    with (source / 'en.json.gz').open('ab') as stream:
        stream.write(b'corruption')
    with pytest.raises(ValueError, match='integrity'):
        vocabulary.lexicon('en')


def test_manifest_path_cannot_escape_language_resource(source):
    manifest = json.loads((source / 'manifest.json').read_bytes())
    manifest['languages']['en']['file'] = '../other.json.gz'
    (source / 'manifest.json').write_text(json.dumps(manifest), encoding='utf8')
    with pytest.raises(ValueError, match='resource name'):
        vocabulary.lexicon('en')


def test_decoded_data_limit_is_checked_before_json_loading(source, monkeypatch):
    monkeypatch.setattr(vocabulary, '_MAX_JSON', 8)
    with pytest.raises(ValueError, match='decoded limit'):
        vocabulary.lexicon('en')


def test_unknown_language_does_not_use_another_language(source):
    with pytest.raises(ValueError, match='Unsupported'):
        vocabulary.lexicon('zz')


def test_static_name_and_domain_lists_do_not_remove_public_words(tmp_path, monkeypatch):
    """Issue #323 policy: public words win over NAME_WORDS/ENGLISH_NAMES/DOMAIN_WORDS."""
    data = {'schema_version': 1, 'data_version': 'unit', 'language': 'en',
            'words': ['bank', 'compare', 'john'], 'name_exclusions': ['please', 'syntheticpersonqzx']}
    blob = gzip.compress(json.dumps(data).encode(), mtime=0)
    (tmp_path / 'en.json.gz').write_bytes(blob)
    metadata = {'file': 'en.json.gz', 'sha256': sha256(blob).hexdigest(), 'bytes': len(blob),
                'words': 3, 'name_exclusions': 2}
    (tmp_path / 'manifest.json').write_text(json.dumps({'schema_version': 1, 'data_version': 'unit',
        'languages': {lang: metadata for lang in vocabulary._LANGUAGES}}), encoding='utf8')
    monkeypatch.setattr(vocabulary, '_resource_root', lambda: tmp_path)
    vocabulary._manifest.cache_clear()
    vocabulary.lexicon.cache_clear()
    try:
        result = vocabulary.lexicon('en')
        assert {'bank', 'john', 'compare', 'please'} <= result.words   # domain word, common name, authored word
        assert result.names == frozenset({'syntheticpersonqzx'})       # evidence never removes a public word
        assert not result.words & result.names
    finally:
        vocabulary._manifest.cache_clear()
        vocabulary.lexicon.cache_clear()
