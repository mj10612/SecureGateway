"""Invariants, provenance and licences of the packaged common-vocabulary data.

Data-only checks; the vocabulary is not activated by the gateway in these tests.
Data 1.2.0 preserves general words: name/place evidence never removes a frequency word.
"""
from hashlib import sha256
import gzip
import importlib.util
import json
from pathlib import Path
import unicodedata

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'src' / 'secure_gateway' / 'data' / 'common_vocabulary'
LANGUAGES = ('en', 'ko', 'es', 'fr', 'pt', 'de', 'id', 'tr', 'ru', 'hi', 'mr', 'bn', 'ur', 'te', 'ar', 'zh', 'ja')
MANIFEST = json.loads((DATA / 'manifest.json').read_bytes())
FALLBACK = ('ko', 'id', 'hi', 'ur')


def curator():
    spec = importlib.util.spec_from_file_location('curate_common_vocabulary', ROOT / 'scripts' / 'curate_common_vocabulary.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lf_sha256(path):
    """Checkout-independent source fingerprint: CRLF -> LF, then SHA-256."""
    return sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def load(language):
    raw = (DATA / f'{language}.json.gz').read_bytes()
    return raw, json.loads(gzip.decompress(raw))


def test_manifest_covers_all_languages_and_is_canonical_lf_json():
    raw = (DATA / 'manifest.json').read_bytes()
    assert b'\r' not in raw and raw.endswith(b'}\n') and len(raw) <= 1024 * 1024
    assert raw == (json.dumps(MANIFEST, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    assert tuple(sorted(MANIFEST['languages'])) == tuple(sorted(LANGUAGES))
    assert MANIFEST['schema_version'] == 1 and MANIFEST['data_version'] == '1.3.0'
    assert MANIFEST['generator']['canonical_lf_sha256'] == lf_sha256(ROOT / 'scripts' / 'curate_common_vocabulary.py')
    assert MANIFEST['generator']['fingerprint'].startswith('canonical-lf-sha256')


@pytest.mark.parametrize('language', LANGUAGES)
def test_file_bytes_hash_gzip_header_and_canonical_payload(language):
    raw, data = load(language)
    row = MANIFEST['languages'][language]
    assert sha256(raw).hexdigest() == row['sha256'] and len(raw) == row['bytes'] <= 4 * 1024 * 1024
    assert raw[:4] == b'\x1f\x8b\x08\x00' and raw[4:8] == b'\0\0\0\0' and raw[9] == 255  # no name, mtime 0, OS unknown
    payload = gzip.decompress(raw)
    assert len(payload) <= 16 * 1024 * 1024
    assert payload == (json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')
    core = {'schema_version', 'data_version', 'language', 'words', 'name_exclusions', 'source_ids'}
    # Only Korean carries the optional typed predicate_lemmas field.
    assert set(data) == (core | {'predicate_lemmas'} if language == 'ko' else core)
    assert data['schema_version'] == 1 and data['data_version'] == '1.3.0' and data['language'] == language
    assert data['source_ids'] == row['source_ids'] == sorted(set(data['source_ids']))
    assert set(data['source_ids']) <= set(MANIFEST['licences'])


@pytest.mark.parametrize('language', LANGUAGES)
def test_word_shape_targets_and_disjoint_fallback_name_candidates(language):
    _, data = load(language)
    words, excluded = data['words'], data['name_exclusions']
    for values in (words, excluded):
        assert values == sorted(set(values)) and len(values) <= 100_000
        assert all(v and len(v) <= 256 and v == unicodedata.normalize('NFC', v).casefold() for v in values)
    # Safe shape: letters/marks/apostrophes/joiners only, at least one letter (no digits, code or punctuation).
    assert all(any(c.isalpha() for c in w) and all(c.isalpha() or unicodedata.category(c).startswith('M') or c in "’'‌‍"
                                                    for c in w) for w in words)
    predicates = set().union(*data.get('predicate_lemmas', {}).values()) if 'predicate_lemmas' in data else set()
    assert not set(words) & set(excluded) and not predicates & set(excluded)
    row, stats = MANIFEST['languages'][language], MANIFEST['languages'][language]['statistics']
    assert row['target_words'] == stats['target'] == 50_000 and MANIFEST['parameters']['minimum_words'] == 30_000
    assert len(words) == row['words'] and 30_000 <= len(words) <= 50_000 and len(excluded) == row['name_exclusions']
    assert row['coverage'] == ('target_met' if len(words) == 50_000 else 'within_target_range')
    assert row['coverage'] == 'target_met' or stats['source_exhausted'] is True  # Shortfalls only from exhaustion.
    assert sum(stats['words_by_source'].values()) == len(words)


def test_selection_never_removes_a_word_for_name_evidence():
    """Synthetic policy check: names are metadata; only outside-selection forms are fallback candidates."""
    module = curator()
    ranked = [(w, 'wordfreq', None) for w in ('the', 'Smith', 'London', 'bank', 'water', 'Paris', 'Jones', 'river')]
    words, fallback, stats = module.curate_language(
        'en', iter(ranked), {'wikidata_family_names': {'smith', 'jones'}, 'geonames_places': {'london', 'paris'}},
        authored_names={'smith', 'zelda'}, domain_words={'bank'}, target=4, evidence_window=10)
    assert words == ['bank', 'london', 'smith', 'the']        # names and the domain word kept as ordinary
    assert fallback == ['jones', 'paris', 'zelda']               # attested forms outside the selection only
    assert stats['name_attested_words'] == 2 and stats['domain_attested_words'] == 1
    assert stats['name_attested_words_by_source'] == {'geonames_places': 1, 'secure_gateway_authored_names': 1,
                                                      'wikidata_family_names': 1}


@pytest.mark.parametrize('language,preserved', [
    # Independent ordinary-source controls: everyday words and widely used public
    # names/places that are also frequent words. Not evaluation text.
    ('en', ('time', 'people', 'good', 'water', 'house', 'john', 'mary', 'london', 'smith')),
    ('de', ('nicht', 'sie', 'haus', 'liste', 'bücher', 'berlin', 'deutschland', 'müller')),
    ('es', ('casa', 'vida', 'trabajo', 'madrid', 'josé')),
    ('fr', ('est', 'il', 'maison', 'temps', 'paris', 'pierre')),
    ('ko', ('책', '정리', '사람', '서울', '한국')),
    ('zh', ('我', '人', '中国', '王')),
    ('ru', ('дом', 'работа', 'москва')),
])
def test_general_words_and_common_names_are_preserved(language, preserved):
    _, data = load(language)
    words, excluded = set(data['words']), set(data['name_exclusions'])
    for form in preserved:
        assert form in words and form not in excluded, form


def test_name_evidence_is_metadata_with_attested_sources():
    params, cache = MANIFEST['parameters'], MANIFEST['inputs']['cache']
    assert 'General-word preservation' in params['name_policy'] and 'not proof' in params['name_policy']
    assert params['wikidata_bearer_threshold'] == 1 and params['geonames_min_population'] == 15_000
    for key in ('wikidata_given_name_labels', 'wikidata_given_name_aliases', 'wikidata_family_name_labels',
                'wikidata_family_name_aliases', 'wikidata_given_name_labels_variants', 'wikidata_family_name_aliases_variants'):
        assert key in cache and '>= 1 entity' in cache[key]['origin'] and cache[key]['bytes'] > 0
    for language, row in MANIFEST['languages'].items():
        stats = row['statistics']
        assert stats['name_attested_words'] <= row['words'] and stats['evidence_candidates_scanned'] <= params['evidence_window']
    assert MANIFEST['languages']['en']['statistics']['name_attested_words'] > 10_000  # evidence retained, not applied
    module = curator()
    assert module.merge_labels({'zh-hans': {'a'}, 'pt-br': {'b'}, 'mul': {'c'}}) == {'zh': {'a'}, 'pt': {'b'}, 'mul': {'c'}}
    sample = '\n'.join(['?l', '"Smith"@en', '"SM"@en', '"J"@mul', '"张三"@zh-hans', '']).encode('utf-8')
    assert module.read_wikidata_labels(sample) == {'en': {'smith', 'sm'}, 'mul': {'j'}, 'zh-hans': {'张三'}}
    assert module.read_wikidata_labels(sample, aliases=True) == {'en': {'smith'}, 'zh-hans': {'张三'}}
    assert module.read_wikidata_labels(gzip.compress(sample)) == module.read_wikidata_labels(sample)


def test_indic_combining_marks_are_accepted_and_mr_te_stay_in_script():
    for language, (low, high) in (('mr', (0x0900, 0x097F)), ('te', (0x0C00, 0x0C7F))):
        _, data = load(language)
        assert any(unicodedata.category(c).startswith('M') for w in data['words'] for c in w)
        assert all(all(c in '‌‍' or low <= ord(c) <= high or 0xA8E0 <= ord(c) <= 0xA8FF for c in w)
                   for w in data['words'])


def test_licences_and_attribution_are_recorded_per_language():
    notice = (DATA / 'NOTICE.md').read_text(encoding='utf-8')
    for phrase in ('Attribution-ShareAlike 4.0', 'Attribution-ShareAlike 3.0', 'Grave', 'SUBTLEX', 'GeoNames', 'Wikidata',
                   'jieba', 'Section 4(b)(ii)'):
        assert phrase in notice
    for language, row in MANIFEST['languages'].items():
        expected = ('fasttext_cc', 'CC-BY-SA-3.0') if language in {'mr', 'te'} else ('wordfreq', 'CC-BY-SA-4.0')
        assert (row['primary_source'], row['words_licence']) == expected
        assert MANIFEST['licences'][row['primary_source']]['licence'] == expected[1]
        if language in FALLBACK:
            assert row['fallback_source'] == 'fasttext_cc' and 'fasttext_cc' in row['source_ids']
            assert '4(b)(ii)' in row['licence_note'] and 'wordfreq' in row['licence_note']
        else:
            assert row['fallback_source'] is None and row['licence_note'] is None
    assert 'later version' in MANIFEST['inputs']['cache']['cc_by_sa_30_legalcode']['origin']
    assert MANIFEST['licences']['geonames']['licence'] == 'CC-BY-4.0'
    assert MANIFEST['licences']['wikidata']['licence'] == 'CC0-1.0'
    third_party = (ROOT / 'docs' / 'THIRD_PARTY_DATA.md').read_text(encoding='utf-8')
    assert 'wordfreq 3.1.1' in third_party and 'common_vocabulary' in third_party


def test_pinned_inputs_are_hashes_not_runtime_downloads():
    inputs = MANIFEST['inputs']
    assert inputs['wordfreq']['version'] == '3.1.1' and len(inputs['wordfreq']['files']) == 15
    for group in ('cache', 'legacy_cache'):
        for item in inputs[group].values():
            assert len(item['sha256']) == 64 and item['bytes'] > 0
    module = curator()
    assert {k: v[1] for k, v in module.WORDFREQ_FILES.items()} == {k: v['sha256'] for k, v in inputs['wordfreq']['files'].items()}
    import wordfreq
    for language, (name, digest) in module.WORDFREQ_FILES.items():
        assert sha256((Path(wordfreq.__file__).parent / 'data' / name).read_bytes()).hexdigest() == digest


def test_static_domain_words_are_evidence_not_a_veto():
    """1.3.0: a frequent ordinary word is not removed for appearing in DOMAIN_WORDS."""
    from secure_gateway.gateway_vocabulary import DOMAIN_WORDS
    assert 'domain words are counted' in MANIFEST['parameters']['name_policy']
    for language in LANGUAGES:
        stats = MANIFEST['languages'][language]['statistics']
        assert 'domain_filtered' not in stats and stats['domain_attested_words'] >= 0
    _, english = load('en')
    domain = {unicodedata.normalize('NFC', w).casefold() for w in DOMAIN_WORDS['en']}
    assert {'bank', 'cancer', 'apple'} <= set(english['words']) & domain


def test_serialization_is_deterministic():
    module = curator()
    record = {'schema_version': 1, 'data_version': '1.3.0', 'language': 'xx', 'words': ['b', 'a'],
              'name_exclusions': [], 'source_ids': ['wordfreq']}
    first = module.gzip_bytes(module.canonical_json(record))
    assert first == module.gzip_bytes(module.canonical_json(dict(reversed(list(record.items())))))
    assert first[4:8] == b'\0\0\0\0' and first[9] == 255
    assert module.accepted('पुस्तक') and module.accepted("aujourd’hui") and module.accepted('a‍b') and module.accepted("don't")
    for bad in ('abc1', '', 'a-b', "'", '’', '‌', 'x.y', 'snake_case'):
        assert not module.accepted(bad), bad
    assert module.in_script('पुस्तक', 'mr') and not module.in_script('book', 'mr')


def test_korean_predicate_lemmas_are_typed_gated_and_sourced():
    _, data = load('ko')
    predicates = data['predicate_lemmas']
    assert set(predicates) == {'verb', 'adjective'}
    row = MANIFEST['languages']['ko']['predicate_lemmas']
    assert row['gate'] == 1000 and row['gate_candidates'] == 1000
    assert 'wiktionary' in data['source_ids'] and MANIFEST['licences']['wiktionary']['licence'] == 'CC-BY-SA-4.0'
    words, excluded = set(data['words']), set(data['name_exclusions'])
    for kind, lemmas in predicates.items():
        assert lemmas == sorted(set(lemmas)) and len(lemmas) == row[kind]['kept'] > 0
        for lemma in lemmas:
            assert lemma.endswith('다') and len(lemma) >= 2 and all('가' <= c <= '힣' for c in lemma)
            assert lemma in words or lemma[:-1] in words  # gate: lemma or bare stem is a frequency word
            assert lemma not in excluded
    # Ordinary predicates restored (name homonyms of their stems no longer veto them).
    assert {'하다', '주다', '정리하다'} & set(predicates['verb']) >= {'하다', '주다'}
    assert len(predicates['verb']) >= 139 and len(predicates['adjective']) >= 40
    for language in LANGUAGES:
        if language != 'ko':
            assert 'predicate_lemmas' not in load(language)[1]


def test_source_fingerprints_ignore_checkout_line_endings_but_data_hashes_stay_exact(tmp_path):
    module = curator()
    source = (ROOT / 'src' / 'secure_gateway' / 'engine' / 'grammar_en.py').read_bytes().replace(b'\r\n', b'\n')
    (tmp_path / 'lf.py').write_bytes(source)
    (tmp_path / 'crlf.py').write_bytes(source.replace(b'\n', b'\r\n'))
    assert module.file_sha256(tmp_path / 'lf.py') != module.file_sha256(tmp_path / 'crlf.py')
    assert module.source_sha256(tmp_path / 'lf.py') == module.source_sha256(tmp_path / 'crlf.py') == sha256(source).hexdigest()
    inputs = MANIFEST['inputs']
    for name, digest in inputs['authored']['canonical_lf_sha256'].items():
        assert lf_sha256(ROOT / 'src' / 'secure_gateway' / name) == digest
    assert inputs['authored']['fingerprint'] == MANIFEST['generator']['fingerprint']
    assert all(len(item['sha256']) == 64 and item['bytes'] > 0 for item in inputs['cache'].values())
    assert 'canonical_lf_sha256' not in inputs['cache']


def test_country_alias_reader_filters_abbreviations():
    alias = MANIFEST['inputs']['cache']['wikidata_country_aliases']
    assert alias['bytes'] > 0 and 'skos:altLabel' in alias['origin']
    module = curator()
    sample = '\n'.join(['?l', '"DE"@mul', '"in"@en', '"tv"@en', '"中"@zh', '"한국"@ko', '']).encode('utf-8')
    assert module.read_wikidata_labels(sample, aliases=True) == {'ko': {'한국'}}


@pytest.mark.parametrize('language', FALLBACK)
def test_fallback_languages_mix_ranked_sources_without_padding(language):
    row = MANIFEST['languages'][language]
    stats = row['statistics']
    assert row['words'] >= 30_000 and set(stats['words_by_source']) == {'wordfreq', 'fasttext_cc'}
    assert stats['read_by_source']['wordfreq'] >= stats['words_by_source']['wordfreq']
    # Every wordfreq candidate is consumed before any fastText entry.
    assert stats['read_by_source']['wordfreq'] == sum(1 for _ in curator().wordfreq_ranked(language))
    scripts = MANIFEST['parameters']['fallback_script_rule'][language]
    assert scripts and all(r.startswith('U+') for r in scripts)
    if language == 'ur':
        _, data = load('ur')
        assert not any(0xFB50 <= ord(c) <= 0xFDFF or 0xFE70 <= ord(c) <= 0xFEFF for w in data['words'] for c in w)
