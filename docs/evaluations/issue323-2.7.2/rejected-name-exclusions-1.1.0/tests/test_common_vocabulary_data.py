"""Invariants, provenance and licences of the packaged common-vocabulary data.

Data-only checks; the vocabulary is not activated by the gateway in these tests.
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
    assert b'\r' not in raw and raw.endswith(b'}\n')
    assert raw == (json.dumps(MANIFEST, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    assert tuple(sorted(MANIFEST['languages'])) == tuple(sorted(LANGUAGES))
    assert MANIFEST['schema_version'] == 1 and MANIFEST['data_version'] == '1.1.0'
    assert MANIFEST['generator']['canonical_lf_sha256'] == lf_sha256(ROOT / 'scripts' / 'curate_common_vocabulary.py')
    assert MANIFEST['generator']['fingerprint'].startswith('canonical-lf-sha256')


@pytest.mark.parametrize('language', LANGUAGES)
def test_file_bytes_hash_gzip_header_and_canonical_payload(language):
    raw, data = load(language)
    row = MANIFEST['languages'][language]
    assert sha256(raw).hexdigest() == row['sha256'] and len(raw) == row['bytes']
    assert raw[:4] == b'\x1f\x8b\x08\x00' and raw[4:8] == b'\0\0\0\0' and raw[9] == 255  # no name, mtime 0, OS unknown
    payload = gzip.decompress(raw)
    assert payload == (json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')
    core = {'schema_version', 'data_version', 'language', 'words', 'name_exclusions', 'source_ids'}
    # Only Korean carries the optional typed predicate_lemmas field.
    assert set(data) == (core | {'predicate_lemmas'} if language == 'ko' else core)
    assert data['schema_version'] == 1 and data['data_version'] == '1.1.0' and data['language'] == language
    assert data['source_ids'] == row['source_ids'] == sorted(set(data['source_ids']))
    assert set(data['source_ids']) <= set(MANIFEST['licences'])


@pytest.mark.parametrize('language', LANGUAGES)
def test_words_are_sorted_unique_normalized_letters_and_disjoint_from_exclusions(language):
    _, data = load(language)
    words, excluded = data['words'], data['name_exclusions']
    for values in (words, excluded):
        assert values == sorted(set(values))
        assert all(v == unicodedata.normalize('NFC', v).casefold() for v in values)
    assert all(all(c.isalpha() or unicodedata.category(c).startswith('M') or c in "’'‌‍" for c in w) for w in words)
    assert not set(words) & set(excluded)
    row = MANIFEST['languages'][language]
    target = 30_000 if language in FALLBACK else 50_000
    assert row['target_words'] == row['statistics']['target'] == target
    assert len(words) == row['words'] <= target and len(excluded) == row['name_exclusions']
    assert row['coverage'] == ('target_met' if len(words) == target else 'within_target_range' if len(words) >= 30_000 else 'below_target')
    assert row['coverage'] == 'target_met' or row['statistics']['source_exhausted'] is True  # Shortfalls only from exhaustion.
    assert sum(row['statistics']['words_by_source'].values()) == len(words)


def test_indic_combining_marks_are_accepted_and_mr_te_stay_in_script():
    for language, (low, high) in (('mr', (0x0900, 0x097F)), ('te', (0x0C00, 0x0C7F))):
        _, data = load(language)
        assert any(unicodedata.category(c).startswith('M') for w in data['words'] for c in w)
        assert all(all(c in '‌‍' or low <= ord(c) <= high or 0xA8E0 <= ord(c) <= 0xA8FF for c in w)
                   for w in data['words'])


def test_licences_and_attribution_are_recorded_per_language():
    notice = (DATA / 'NOTICE.md').read_text(encoding='utf-8')
    for phrase in ('Attribution-ShareAlike 4.0', 'Attribution-ShareAlike 3.0', 'Grave', 'SUBTLEX', 'GeoNames', 'Wikidata', 'jieba'):
        assert phrase in notice
    for language, row in MANIFEST['languages'].items():
        expected = ('fasttext_cc', 'CC-BY-SA-3.0') if language in {'mr', 'te'} else ('wordfreq', 'CC-BY-SA-4.0')
        assert (row['primary_source'], row['words_licence']) == expected
        assert MANIFEST['licences'][row['primary_source']]['licence'] == expected[1]
        if language in FALLBACK:
            # BY-SA 3.0 fastText entries adapted into a BY-SA 4.0 file (BY-SA 3.0 Section 4(b)(ii)).
            assert row['fallback_source'] == 'fasttext_cc' and 'fasttext_cc' in row['source_ids']
            assert '4(b)(ii)' in row['licence_note'] and 'wordfreq' in row['licence_note']
        else:
            assert row['fallback_source'] is None and row['licence_note'] is None
    legal = MANIFEST['inputs']['cache']['cc_by_sa_30_legalcode']
    assert 'later version' in legal['origin'] and len(legal['sha256']) == 64
    assert 'Section 4(b)(ii)' in notice
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
    # The packaged wordfreq data used for the 15 languages is the pinned one.
    import wordfreq
    for language, (name, digest) in module.WORDFREQ_FILES.items():
        assert sha256((Path(wordfreq.__file__).parent / 'data' / name).read_bytes()).hexdigest() == digest


def test_authored_denysets_are_never_ordinary_words():
    from secure_gateway.gateway_name_vocabulary import NAME_WORDS
    from secure_gateway.gateway_vocabulary import DOMAIN_WORDS, ENGLISH_NAMES
    for language in LANGUAGES:
        _, data = load(language)
        words = set(data['words'])
        names = {unicodedata.normalize('NFC', w).casefold() for w in NAME_WORDS.get(language, ())}
        if language == 'en':
            names |= set(ENGLISH_NAMES)
        domain = {unicodedata.normalize('NFC', w).casefold() for w in DOMAIN_WORDS.get(language, ())}
        assert not words & (names | domain)


def test_only_authored_closed_class_words_are_exempt_from_name_matches():
    """Frequency rank is never an exemption; only exact authored grammar words are."""
    from secure_gateway.engine.grammar_en import CLOSED_CLASS_WORDS as english
    from secure_gateway.engine.grammar_ko import KOREAN_FUNCTION_WORDS as korean
    from secure_gateway.engine.natural_languages import CLOSED_CLASS_WORDS as others
    assert 'core_rank' not in MANIFEST['parameters'] and 'No frequency-rank exemption' in MANIFEST['parameters']['name_exemption_policy']
    for name, digest in MANIFEST['inputs']['closed_class']['canonical_lf_sha256'].items():
        assert lf_sha256(ROOT / 'src' / 'secure_gateway' / name) == digest
    for language, row in MANIFEST['languages'].items():
        _, data = load(language)
        closed = {unicodedata.normalize('NFC', w).casefold() for w in others.get(language, ())}
        closed |= set(english) if language == 'en' else set(korean) if language == 'ko' else set()
        exceptions = row['closed_class_exception_list']
        assert len(exceptions) == row['closed_class_exceptions']
        assert all(item['word'] in closed and item['sources'] for item in exceptions)
        assert {item['word'] for item in exceptions} <= set(data['words'])


@pytest.mark.parametrize('language,places,names,grammar', [
    # Fresh synthetic data-review controls: widely published given/family names and
    # cities from the public sources themselves, never evaluation text. `grammar`
    # holds authored closed-class words that must stay ordinary.
    ('en', ('london', 'chicago', 'germany'), ('smith', 'johnson', 'mary', 'william', 'elizabeth'), ('the', 'and', 'of', 'with')),
    ('de', ('berlin', 'hamburg', 'deutschland', 'münchen', 'wien', 'köln'), ('müller', 'schmidt', 'hans', 'mann', 'klein'),
     ('und', 'der', 'die', 'das')),
    ('es', ('madrid', 'sevilla', 'españa'), ('garcía', 'martínez', 'josé'), ('de', 'la', 'que', 'el')),
    ('fr', ('paris', 'lyon', 'marseille'), ('dupont', 'marie', 'pierre'), ('le', 'la', 'et', 'de')),
    ('pt', ('lisboa',), ('silva', 'joão'), ()),
    ('ru', ('москва', 'россия'), ('иванов', 'сергей'), ()),
    ('ko', ('서울', '부산', '일본'), ('김', '박', '민준'), ()),
    ('ja', (), ('佐藤', '田中'), ()),
    ('zh', (), ('王', '李', '张', '刘', '陈'), ()),
    ('ar', ('القاهرة',), ('محمد', 'أحمد'), ()),
    ('hi', ('दिल्ली', 'मुंबई'), ('राहुल',), ()),
    ('tr', ('ankara', 'istanbul'), ('mehmet',), ()),
    ('id', ('jakarta', 'surabaya'), ('budi',), ()),
    ('bn', ('ঢাকা',), ('রহিম',), ()),
    ('ur', ('کراچی',), ('احمد',), ()),
    ('mr', ('पुणे', 'मुंबई'), (), ()),
    ('te', ('హైదరాబాద్',), (), ()),
])
def test_proper_place_and_name_controls_are_not_ordinary_words(language, places, names, grammar):
    _, data = load(language)
    words, excluded = set(data['words']), set(data['name_exclusions'])
    for form in places + names:
        assert form in excluded and form not in words, form
    for form in grammar:
        assert form in words, form


def test_name_sources_cover_every_attested_name_item_with_labels_and_aliases():
    params, cache = MANIFEST['parameters'], MANIFEST['inputs']['cache']
    assert params['wikidata_bearer_threshold'] == 1 and params['geonames_min_population'] == 15_000
    for key in ('wikidata_given_name_labels', 'wikidata_given_name_aliases', 'wikidata_family_name_labels',
                'wikidata_family_name_aliases', 'wikidata_given_name_labels_variants', 'wikidata_family_name_aliases_variants'):
        assert key in cache and '>= 1 entity' in cache[key]['origin'] and cache[key]['bytes'] > 0
    module = curator()
    # Regional label variants fold into their base language; aliases drop abbreviations.
    merged = module.merge_labels({'zh-hans': {'a'}, 'pt-br': {'b'}, 'mul': {'c'}})
    assert merged == {'zh': {'a'}, 'pt': {'b'}, 'mul': {'c'}}
    sample = '\n'.join(['?l', '"Smith"@en', '"SM"@en', '"J"@mul', '"张三"@zh-hans', '']).encode('utf-8')
    # Labels keep every attested form, preserving native characters (NFC + casefold only).
    assert module.read_wikidata_labels(sample) == {'en': {'smith', 'sm'}, 'mul': {'j'}, 'zh-hans': {'张三'}}
    # Aliases skip all-uppercase codes and single-character forms.
    assert module.read_wikidata_labels(sample, aliases=True) == {'en': {'smith'}, 'zh-hans': {'张三'}}
    assert module.read_wikidata_labels(gzip.compress(sample)) == module.read_wikidata_labels(sample)
    for language, row in MANIFEST['languages'].items():
        assert row['name_exclusions'] <= 100_000 and row['words'] <= 100_000 and row['bytes'] <= 4 * 1024 * 1024


def test_serialization_is_deterministic():
    module = curator()
    record = {'schema_version': 1, 'data_version': '1.0.0', 'language': 'xx', 'words': ['b', 'a'],
              'name_exclusions': [], 'source_ids': ['wordfreq']}
    first = module.gzip_bytes(module.canonical_json(record))
    assert first == module.gzip_bytes(module.canonical_json(dict(reversed(list(record.items())))))
    assert first[4:8] == b'\0\0\0\0' and first[9] == 255
    assert module.accepted('पुस्तक') and module.accepted("aujourd’hui") and module.accepted('a‍b')
    assert not module.accepted('abc1') and not module.accepted('') and not module.accepted('a-b')
    assert module.in_script('पुस्तक', 'mr') and not module.in_script('book', 'mr')


def test_korean_predicate_lemmas_are_typed_gated_and_sourced():
    _, data = load('ko')
    predicates = data['predicate_lemmas']
    assert set(predicates) == {'verb', 'adjective'}
    row = MANIFEST['languages']['ko']['predicate_lemmas']
    assert row['gate'] == 1000 and row['gate_candidates'] == 1000
    assert 'wiktionary' in data['source_ids'] and MANIFEST['licences']['wiktionary']['licence'] == 'CC-BY-SA-4.0'
    words, excluded = set(data['words']), set(data['name_exclusions'])
    from secure_gateway.gateway_name_vocabulary import NAME_WORDS
    from secure_gateway.gateway_vocabulary import DOMAIN_WORDS
    authored = set(NAME_WORDS.get('ko', ())) | set(DOMAIN_WORDS.get('ko', ()))
    for kind, lemmas in predicates.items():
        assert lemmas == sorted(set(lemmas)) and len(lemmas) == row[kind]['kept'] > 0
        for lemma in lemmas:
            assert lemma.endswith('다') and len(lemma) >= 2 and all('가' <= c <= '힣' for c in lemma)
            # Gate: the lemma or its bare stem is a generic frequency candidate (kept or excluded).
            assert lemma in words | excluded or lemma[:-1] in words | excluded
            assert lemma not in excluded and lemma not in authored
    # Ordinary predicates are typed separately; the bare-stem name homonyms stay excluded.
    assert {'하다', '주다'} <= set(predicates['verb']) and {'하', '주'} <= excluded
    for language in LANGUAGES:
        if language != 'ko':
            assert 'predicate_lemmas' not in load(language)[1]


def test_source_fingerprints_ignore_checkout_line_endings_but_data_hashes_stay_exact(tmp_path):
    module = curator()
    source = (ROOT / 'src' / 'secure_gateway' / 'engine' / 'grammar_en.py').read_bytes().replace(b'\r\n', b'\n')
    (tmp_path / 'lf.py').write_bytes(source)
    (tmp_path / 'crlf.py').write_bytes(source.replace(b'\n', b'\r\n'))
    assert b'\r\n' in (tmp_path / 'crlf.py').read_bytes()
    assert module.file_sha256(tmp_path / 'lf.py') != module.file_sha256(tmp_path / 'crlf.py')
    assert module.source_sha256(tmp_path / 'lf.py') == module.source_sha256(tmp_path / 'crlf.py') == sha256(source).hexdigest()
    # Every recorded source-code fingerprint matches this checkout whatever its line endings.
    inputs = MANIFEST['inputs']
    for name, digest in inputs['authored']['canonical_lf_sha256'].items():
        assert lf_sha256(ROOT / 'src' / 'secure_gateway' / name) == digest
    assert inputs['authored']['fingerprint'] == inputs['closed_class']['fingerprint'] == MANIFEST['generator']['fingerprint']
    # Downloaded inputs and generated data keep exact raw byte hashes.
    assert all(len(item['sha256']) == 64 and item['bytes'] > 0 for item in inputs['cache'].values())
    assert 'canonical_lf_sha256' not in inputs['cache']


def test_country_aliases_are_a_pinned_generic_source():
    alias = MANIFEST['inputs']['cache']['wikidata_country_aliases']
    assert alias['bytes'] > 0 and 'skos:altLabel' in alias['origin']
    _, korean = load('ko')
    assert '한국' in korean['name_exclusions'] and '한국' not in korean['words']
    # Abbreviation aliases (codes such as DE, ES, in, tv) are filtered by the alias reader itself;
    # the same strings may still be excluded through other sources, e.g. attested family names.
    module = curator()
    sample = '\n'.join(['?l', '"DE"@mul', '"in"@en', '"tv"@en', '"中"@zh', '"한국"@ko', '']).encode('utf-8')
    assert module.read_wikidata_labels(sample, aliases=True) == {'ko': {'한국'}}


@pytest.mark.parametrize('language', FALLBACK)
def test_fallback_languages_mix_ranked_sources_without_padding(language):
    row = MANIFEST['languages'][language]
    stats = row['statistics']
    assert row['words'] == 30_000 and row['coverage'] == 'target_met' and not stats['source_exhausted']
    assert set(stats['words_by_source']) == {'wordfreq', 'fasttext_cc'}
    assert stats['read_by_source']['wordfreq'] >= stats['words_by_source']['wordfreq']
    # Every wordfreq candidate is consumed before any fastText entry.
    wordfreq_entries = sum(1 for _ in curator().wordfreq_ranked(language))
    assert stats['read_by_source']['wordfreq'] == wordfreq_entries
    scripts = MANIFEST['parameters']['fallback_script_rule'][language]
    assert scripts and all(r.startswith('U+') for r in scripts)
    if language == 'ur':
        assert all(not ('U+FB50' in r or 'U+FE70' in r) for r in scripts)
        _, data = load('ur')
        assert not any(0xFB50 <= ord(c) <= 0xFDFF or 0xFE70 <= ord(c) <= 0xFEFF for w in data['words'] for c in w)


def test_letter_required_and_korean_name_inflection_rule():
    module = curator()
    assert not module.accepted("'") and not module.accepted('’') and not module.accepted('‌')
    assert module.accepted("don't")
    inflected = module.korean_name_inflection({'한국', '다'})
    assert inflected('한국은')          # two-syllable place + particle
    assert not inflected('다는')             # single-syllable form + particle is not matched
    assert not inflected('한국')             # the bare form is an exact-label matter, not inflection
    row = MANIFEST['languages']['ko']
    assert 'fallback (fastText) entries only' in MANIFEST['parameters']['korean_name_inflection_rule']
    assert row['statistics']['name_inflection_excluded'] > 0
    # The typed predicate gate still uses only the first 1,000 wordfreq candidates.
    assert row['predicate_lemmas']['gate_candidates'] == 1000
