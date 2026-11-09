"""Bounded offline loader for the independently sourced prose vocabulary.

These are ordinary-word candidates, not privacy classifications. Gateway private,
code and explicit protections still take precedence. No source corpus is loaded
or downloaded at runtime.
"""
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from importlib.resources import files
from io import BytesIO
import gzip
import json
import unicodedata

from secure_gateway.engine.natural_languages import SUPPORTED_LANGUAGES
from secure_gateway.gateway_vocabulary import (
    GENERAL_WORDS, HOUSEHOLD_WORDS, INDIC_WORDS,
)

_LANGUAGES = SUPPORTED_LANGUAGES - {'auto'}
_MAX_COMPRESSED = 4 * 1024 * 1024
_MAX_JSON = 16 * 1024 * 1024


@dataclass(frozen=True)
class PublicLexicon:
    words: frozenset[str]
    names: frozenset[str]
    data_version: str
    predicates: frozenset[str] = frozenset()


def _resource_root():
    return files('secure_gateway').joinpath('data').joinpath('common_vocabulary')


@lru_cache(maxsize=1)
def _manifest():
    with _resource_root().joinpath('manifest.json').open('rb') as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('Common-vocabulary manifest exceeds limit.')
    manifest = json.loads(raw)
    if (manifest.get('schema_version') != 1 or not isinstance(manifest.get('data_version'), str)
            or not isinstance(manifest.get('languages'), dict) or set(manifest['languages']) != _LANGUAGES):
        raise ValueError('Invalid common-vocabulary manifest.')
    return manifest


def _word_set(value):
    if (not isinstance(value, list) or len(value) > 100_000
            or any(not isinstance(word, str) or not word or len(word) > 256
                   or unicodedata.normalize('NFC', word).casefold() != word for word in value)
            or value != sorted(set(value))):
        raise ValueError('Invalid common-vocabulary entries.')
    return frozenset(value)


@lru_cache(maxsize=17)
def lexicon(language: str) -> PublicLexicon:
    if language not in _LANGUAGES:
        raise ValueError('Unsupported common-vocabulary language.')
    manifest = _manifest()
    metadata = manifest['languages'][language]
    if metadata.get('file') != language + '.json.gz':
        raise ValueError('Invalid common-vocabulary resource name.')
    with _resource_root().joinpath(metadata['file']).open('rb') as stream:
        blob = stream.read(_MAX_COMPRESSED + 1)
    if (len(blob) > _MAX_COMPRESSED or len(blob) != metadata.get('bytes')
            or sha256(blob).hexdigest() != metadata.get('sha256')):
        raise ValueError('Common-vocabulary data failed integrity verification.')
    with gzip.GzipFile(fileobj=BytesIO(blob)) as stream:
        raw = stream.read(_MAX_JSON + 1)
    if len(raw) > _MAX_JSON:
        raise ValueError('Common-vocabulary data exceeds decoded limit.')
    data = json.loads(raw)
    if (data.get('schema_version') != 1 or data.get('data_version') != manifest['data_version']
            or data.get('language') != language):
        raise ValueError('Common-vocabulary data does not match manifest.')
    words, names = _word_set(data.get('words')), _word_set(data.get('name_exclusions'))
    if (len(words) != metadata.get('words') or len(names) != metadata.get('name_exclusions') or words & names):
        raise ValueError('Common-vocabulary counts or name exclusions disagree.')
    predicates: set[str] = set()
    if 'predicate_lemmas' in data:
        if language != 'ko' or not isinstance(data['predicate_lemmas'], dict) or set(data['predicate_lemmas']) != {'verb', 'adjective'}:
            raise ValueError('Invalid typed predicate inventory.')
        for kind, values in data['predicate_lemmas'].items():
            selected = _word_set(values)
            if (len(selected) != metadata.get('predicate_lemmas', {}).get(kind, {}).get('kept')
                    or any(not word.endswith('\ub2e4') for word in selected) or selected & names):
                raise ValueError('Typed predicate inventory does not match manifest.')
            predicates.update(selected)
    # Preserve the prior authored ordinary relations without extending those
    # lists from benchmark examples. Issue #323 public-word policy: a frequent
    # ordinary word or typed predicate is public even when it also appears in a
    # static name list (NAME_WORDS/ENGLISH_NAMES), a static DOMAIN_WORDS list or
    # the data's name evidence. `names` is retained as evidence only; actual
    # private registrations, forced rules and prior mappings decide privacy.
    authored = GENERAL_WORDS.get(language, frozenset()) | INDIC_WORDS.get(language, frozenset()) | HOUSEHOLD_WORDS.get(language, frozenset())
    merged = frozenset(words | {unicodedata.normalize('NFC', word).casefold() for word in authored})
    # Public words win: evidence never removes an authored ordinary word.
    return PublicLexicon(merged, frozenset(names - merged - predicates), manifest['data_version'], frozenset(predicates))


def ordinary_words(language: str) -> frozenset[str]:
    return lexicon(language).words
