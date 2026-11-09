"""Build the packaged common-vocabulary data for issue #323 from pinned inputs.

Offline and deterministic: every input is verified by SHA-256 before use, and
nothing is downloaded. Raw inputs live outside the repository (see
docs/COMMON_VOCABULARY_SOURCES.md for their URLs/queries and byte hashes).

Sources:
  * 15 languages: frequency-ranked wordfreq 3.1.1 packaged lists (CC BY-SA 4.0).
  * mr, te: fastText Common Crawl vector vocabulary, which is sorted by frequency
    (CC BY-SA 3.0). Only words are read; vectors are discarded while streaming
    a pinned gzip prefix.
Name/place exclusions use exact, whole labels only, never split labels:
  * Wikidata (CC0) given-name (P735) and family-name (P734) items, each used by at
    least 100 Wikidata entities, so that rare one-off name items do not remove words.
  * Wikidata (CC0) country/sovereign-state labels and aliases in each language.
  * GeoNames (CC BY 4.0) cities with population >= 100000, plus country names;
    Latin-script languages also use alternate names of places in countries that
    list the language in countryInfo.
    mr/te additionally use GeoNames India alternate names tagged mr/te.
  * mr/te: Wikidata given/family-name class labels (prior reviewed memo).
  * zh: installed jieba dictionary multi-character person/place/organisation tags (MIT).
  * Existing authored SecureGateway name/domain denysets (Apache-2.0).
Frequency rank never exempts a name/place match. The only exemption is an exact
word in the independently authored closed-class grammar inventories already used
by the engines (grammar_en.CLOSED_CLASS_WORDS, grammar_ko.KOREAN_FUNCTION_WORDS,
natural_languages.CLOSED_CLASS_WORDS). Each exempted word is listed with its
matching name/place sources in the manifest. Authored name/domain denysets win.

Usage:
  python scripts/curate_common_vocabulary.py --cache-dir DIR [--legacy-cache-dir DIR]
  python scripts/curate_common_vocabulary.py --cache-dir DIR --check
"""
from __future__ import annotations

import argparse
from itertools import chain
from collections import defaultdict
from hashlib import sha256
import gzip
import io
import json
import re
import sys
import tempfile
import unicodedata
import zipfile
import zlib
from pathlib import Path

SCHEMA_VERSION = 1
DATA_VERSION = '1.0.0'
TARGET_WORDS = 50_000
BEARER_THRESHOLD = 100
PREDICATE_GATE = 1_000
# wordfreq lists that run out below 30k continue with the frequency-ordered fastText
# vocabulary of the same language; these languages target 30,000 rather than 50,000.
FALLBACK_TARGET = 30_000
FALLBACK_SCRIPTS = {
    'ko': ((0xAC00, 0xD7A3), (0x1100, 0x11FF), (0x3130, 0x318F)),
    'id': ((0x0041, 0x005A), (0x0061, 0x007A), (0x00C0, 0x024F), (0x0027, 0x0027), (0x2019, 0x2019)),
    'hi': ((0x0900, 0x097F), (0xA8E0, 0xA8FF)),
    # Arabic presentation forms (U+FB50-FDFF, U+FE70-FEFF) are compatibility ligatures, not running text.
    'ur': ((0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF)),
}
PREDICATE_EXCLUDED_SENSE_TAGS = frozenset({'form-of', 'alt-of', 'dialectal', 'archaic', 'obsolete'})
PLACE_POPULATION = 100_000
LANGUAGES = ('en', 'ko', 'es', 'fr', 'pt', 'de', 'id', 'tr', 'ru', 'hi', 'mr', 'bn', 'ur', 'te', 'ar', 'zh', 'ja')
WORDFREQ_LANGUAGES = tuple(language for language in LANGUAGES if language not in {'mr', 'te'})
LATIN = {'en', 'es', 'fr', 'pt', 'de', 'id', 'tr'}
SCRIPTS = {'mr': ((0x0900, 0x097F), (0xA8E0, 0xA8FF)), 'te': ((0x0C00, 0x0C7F),)}
JIEBA_NAME_TAGS = {'nr', 'nrt', 'nrfg', 'ns', 'nt'}
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / 'src' / 'secure_gateway' / 'data' / 'common_vocabulary'

WORDFREQ_VERSION = '3.1.1'
WORDFREQ_FILES = {
    'en': ('large_en.msgpack.gz', 'dffae8066b78dce0a6667cf5f58e567054f902674667090a7ac8a8a44628b05c'),
    'ko': ('small_ko.msgpack.gz', '01014287a9e779d232f965d054a9cb5eb10b0bc46ee464fbd42935a5df7c8319'),
    'es': ('large_es.msgpack.gz', '14f326b4f68d517f9b8b99c1e26ef56a508d2dc8d0ee7a9e6e8732ddab1aa65e'),
    'fr': ('large_fr.msgpack.gz', '6f16cd80b9b66c5698ed002becea83ae30d0584c3205f1cf01714ad562c00c8b'),
    'pt': ('large_pt.msgpack.gz', '7d764586bca6262f554d5fa77ad8e6841ef42534776e70558065140853660ce2'),
    'de': ('large_de.msgpack.gz', '8ef04d3f4a28fb48d800d25fa80a96d90a5f80c8496c9a453f99f887c6ad3c12'),
    'id': ('small_id.msgpack.gz', '6fd891027cd6395b5c038c0e6402fa7e107ffd8973f862053246b897beb1bcd3'),
    'tr': ('small_tr.msgpack.gz', '10980704ee3ac5b52f226579251905412a04ead57092a12182dd0b8be6a765df'),
    'ru': ('large_ru.msgpack.gz', '0440613cc765c14a20fb9483225f2fec4d85e66672809076bcec9b29119f9b43'),
    'hi': ('small_hi.msgpack.gz', '92ccbf70297d28e97af55a2a517b95c3d8b599e4cc943fb6d4612a3d44a86992'),
    'bn': ('large_bn.msgpack.gz', 'd10ed5ca1e61a6bf210324424ee25c53ff71175398833067d810ccc6c826d581'),
    'ur': ('small_ur.msgpack.gz', '2587f23e5974e940e4dbeff64e9d3c918b5bd81b5089020cb6803f3c09626ac6'),
    'ar': ('large_ar.msgpack.gz', 'aa12410764f1946f21d986a920c289c22accb069d9b287d71b61657005516eec'),
    'zh': ('large_zh.msgpack.gz', 'e079d7aaff1cfb92874850cb3ffbc7b611af939d9d671c1cbda932d968467cdd'),
    'ja': ('large_ja.msgpack.gz', 'e6ab743b939c1802fc03791f1d58dee2861e822ceecdcdee3f0e05b863ef26d8'),
}
JIEBA = ('dict.txt', '7197c3211ddd98962b036cdf40324d1ea2bfaa12bd028e68faa70111a88e12a8', '0.42.1')

# Raw inputs outside the repository; (file, sha256, bytes, origin).
CACHE_INPUTS = {
    'fasttext_mr_prefix': ('ft_mr.part40.gz', '5d75a59c7bcb77f8cd7e8b39b919f66dfe0a1ef9916bef67e5ca876bdead5804', 41943040,
                           'HTTP Range bytes 0-41943039 of https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.mr.300.vec.gz '
                           '(Content-Length 504625644, Last-Modified 2019-01-18T15:52:18Z, ETag "522952dc4dd79dddf79dbd035c069117-61"); '
                           'bytes 0-12582911 reused from the validated prefix sha256 04fec5c0d60c2c69a3b08cacc5028a6d62838d8187a0bfdee8be807fa08b7d70'),
    'fasttext_te_prefix': ('ft_te.part40.gz', '32c7f6cd0b2a0604e3629f8cdf85c38fc8398d1de2b28a2080a709de1eb03f11', 41943040,
                           'HTTP Range bytes 0-41943039 of https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.te.300.vec.gz '
                           '(Content-Length 1117025794, Last-Modified 2019-01-18T16:14:29Z, ETag "e630536353eedf68d444a4cdc94b92f8-134"); '
                           'bytes 0-12582911 reused from the validated prefix sha256 a7e9399ac2886cb7a02ea1763df90f215e9a1a9f88697c3e8fd2857c929fdeae'),
    'fasttext_ko_prefix': ('ft_ko.part16.gz', '83d31d311f983b3860ec8bc8805e0ef166ff867cf2a2426ce4713f3ee46ef0d3', 16777216,
                           'HTTP Range bytes 0-16777215 of https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.ko.300.vec.gz '
                           '(Content-Length 1267506825, Last-Modified 2019-01-18T15:45:02Z, ETag "bd2b1735343ce7df16b94036b02369cf-152")'),
    'fasttext_id_prefix': ('ft_id.part32.gz', '38ee96948eb67d70a3f7b521ba23e20d162e41b5e32f6cc39a903442c652bd86', 33554432,
                           'HTTP Range bytes 0-33554431 (two ranges, 0-16777215 sha256 '
                           '6712cc8d8a208a6021bf454a44404a3f72d1478df7725ba4d1df42c6bb946938) of https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.id.300.vec.gz '
                           '(Content-Length 1227018698, Last-Modified 2019-01-18T15:38:40Z, ETag "6cf22a40c0e26a46e173491c006d1dde-147")'),
    'fasttext_hi_prefix': ('ft_hi.part32.gz', '77473d2c68fcf036e65afd1ae225d429e58727e894b2d004fef6210df428c5a6', 33554432,
                           'HTTP Range bytes 0-33554431 (two ranges, 0-16777215 sha256 '
                           '31cda85c87f224a0b6e8e7fd010973898e9796d7ff17bfd538485ef4f0581e93) of https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.hi.300.vec.gz '
                           '(Content-Length 1118942272, Last-Modified 2019-01-18T15:34:42Z, ETag "7c35e963de7f2c8b0fe892ea81a959d2-134")'),
    'fasttext_ur_prefix': ('ft_ur.part48.gz', '4ac930d37b7160e53228fd79bf977f953ada41e4ff3356c565e42aee32d02e0e', 50331648,
                           'HTTP Range bytes 0-50331647 (two ranges, 0-16777215 sha256 '
                           'bf31706cd4d2dcb6ced3ae197080f7750d82875ddd91326f48e6339c70824cb9) of https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.ur.300.vec.gz '
                           '(Content-Length 679221030, Last-Modified 2019-01-18T16:19:22Z, ETag "b8d36f371f3ca4248b0b6ab2c978637f-81")'),
    'cc_by_sa_30_legalcode': ('ccbysa30_legalcode.txt', '3f941b3b89cf7b8370ceb83cc76d2120d471b58735d8ca60238a751a48d7f72f', 22240,
                              'https://creativecommons.org/licenses/by-sa/3.0/legalcode.txt; Section 4(b)(ii) permits distributing an '
                              'Adaptation under a later version of this License with the same License Elements'),
    'wikidata_given_names': ('wd_P735_100.tsv', '0bfc4c428cf48fcf5e889a55136ef1974fcf2c10fc608f9bacd599e547f02d38', 901383,
                             'QLever Wikidata (latest-all 2026-08-10, updated live), retrieved 2026-11-09: DISTINCT labels in the 17 '
                             'languages + mul of items used as P735 (given name) by >= 100 entities; query sha256 '
                             'fc397c9351c35f970f1f4bd7a0f38b24d241af03ede92507753e0d0ddfde5089'),
    'wikidata_family_names': ('wd_P734_100.tsv', '22349a3b9cb4c45419ace60710746664a16df6a4c654d6136fac33fc62f6a52c', 1049690,
                              'QLever Wikidata, retrieved 2026-11-09: DISTINCT labels in the 17 languages + mul of items used as '
                              'P734 (family name) by >= 100 entities; query sha256 '
                              'c8456bb68f70781dc00d62880571e3160f0598162ba798270203afb1a3428e8f'),
    'wikidata_country_labels': ('wd_countries.tsv', '9a1ed1a2d7539e4f97ed94ae4a47111b126cfa01a6848577717f4e9c14373331', 78553,
                                'QLever Wikidata, retrieved 2026-11-09: DISTINCT labels in the 17 languages + mul of items that are '
                                'instances of country (Q6256) or sovereign state (Q3624078); query sha256 '
                                '856c5db5b033a27a7c1c3ba3baf08c0f9c7acce57a3d1c74fdab54e6d232ed9b'),
    'kaikki_ko_verb': ('kaikki_ko_verb.jsonl.gz', '4d46af72a43ef7783b924d9ff35f6f89654ccbfae04fa2b2307b5b9ae8212384', 4571801,
                       'https://kaikki.org/dictionary/Korean/pos-verb/kaikki.org-dictionary-Korean-by-pos-verb.jsonl.gz '
                       '(Last-Modified 2026-10-31T02:51:34Z, ETag "6ae557b6-45c299"); wiktextract commit 19f9a30 extraction '
                       '2026-10-30 of the enwiktionary dump dated 2026-10-01'),
    'kaikki_ko_adj': ('kaikki_ko_adj.jsonl.gz', 'fcb60238034632faf4dd60af926ed3f1a6679bb5d4d3b62e09d1860321d118d1', 1482065,
                      'https://kaikki.org/dictionary/Korean/pos-adj/kaikki.org-dictionary-Korean-by-pos-adj.jsonl.gz '
                      '(Last-Modified 2026-10-31T02:28:11Z, ETag "6ae5523b-169d51"); same extraction'),
    'wikidata_country_aliases': ('wd_country_aliases.tsv', 'e09cc8218018bc11025cba9dc5dfeb4bc3ee6e424c86766a62462ac125bfd07c', 143665,
                                 'QLever Wikidata, retrieved 2026-11-09: DISTINCT skos:altLabel aliases in the 17 languages + mul '
                                 'of country (Q6256) or sovereign-state (Q3624078) items; query sha256 '
                                 '081c90c59268a26e579683828859a5ac26c8132f6410530d4858ce4705a84453'),
    'geonames_cities15000': ('cities15000.zip', '955ad298b67a60996a15b4c4c84c8ca6923bafed195622227f24fd22a31042f4', 3366548,
                             'https://download.geonames.org/export/dump/cities15000.zip (Last-Modified 2026-11-09T02:43:24Z)'),
    'geonames_countryinfo': ('countryInfo.txt', '79f8f59ea01cbb40438bf1856dd6c2ff201f03f8fc72d0530b2646aaf603ef04', 32112,
                             'https://download.geonames.org/export/dump/countryInfo.txt (Last-Modified 2026-11-09T02:48:40Z)'),
}
LEGACY_INPUTS = {
    'geonames_alternatenames_in': ('geonames_alt_IN.zip', 'bec46181afef218540fbf271f39693d0d5b00432815b6efc5e9dc22fb3becb2b', 1371269,
                                   'https://download.geonames.org/export/dump/alternatenames/IN.zip (Last-Modified 2026-11-08T03:49:00Z)'),
    'wikidata_name_classes_mr': ('ql_labels_names_mr.tsv', 'f46e87dd13c79335b592239c90254a789163a8e74ccfc6bd27dff5b854138ca7', 13245,
                                 'QLever Wikidata mr labels of given-name (Q202444 and male/female/unisex subclasses) and family-name '
                                 '(Q101352) items; docs/research/issue323-additional-source-manifest.json'),
    'wikidata_name_classes_te': ('ql_labels_names_te.tsv', 'c81a04e491e350a767b041da3c7a61a030e4382b25e74f749063c6a288f8db21', 20272,
                                 'QLever Wikidata te labels of given-name and family-name class items; '
                                 'docs/research/issue323-additional-source-manifest.json'),
}
LICENCES = {
    'wordfreq': {'licence': 'CC-BY-SA-4.0', 'attribution': 'wordfreq 3.1.1 by Robyn Speer and contributors; includes data '
                 'from Google Books Ngrams, SUBTLEX (Brysbaert et al.), OpenSubtitles, the Leeds Internet Corpus, Wikipedia, '
                 'ParaCrawl and other sources credited in wordfreq README', 'url': 'https://github.com/rspeer/wordfreq'},
    'wiktionary': {'licence': 'CC-BY-SA-4.0', 'attribution': 'Wiktionary contributors (English Wiktionary, dual-licensed '
                   'CC BY-SA 4.0 and GFDL); extracted with wiktextract by Tatu Ylonen, distributed at kaikki.org',
                   'url': 'https://en.wiktionary.org/wiki/Wiktionary:Copyrights'},
    'fasttext_cc': {'licence': 'CC-BY-SA-3.0', 'attribution': 'E. Grave, P. Bojanowski, P. Gupta, A. Joulin, T. Mikolov. '
                    'Learning Word Vectors for 157 Languages. LREC 2018. fastText Common Crawl vectors',
                    'url': 'https://fasttext.cc/docs/en/crawl-vectors.html'},
    'wikidata': {'licence': 'CC0-1.0', 'attribution': 'Wikidata contributors', 'url': 'https://www.wikidata.org/wiki/Wikidata:Licensing'},
    'geonames': {'licence': 'CC-BY-4.0', 'attribution': 'GeoNames (www.geonames.org)', 'url': 'https://download.geonames.org/export/dump/readme.txt'},
    'jieba': {'licence': 'MIT', 'attribution': 'jieba 0.42.1 dictionary by Sun Junyi and contributors', 'url': 'https://github.com/fxsjy/jieba'},
    'secure_gateway_authored': {'licence': 'Apache-2.0', 'attribution': 'SecureGateway contributors (authored name/domain denysets)',
                                'url': 'https://github.com/mj10612/SecureGateway'},
}


def file_sha256(path):
    """Exact bytes: used for downloaded/binary inputs and generated data."""
    return sha256(Path(path).read_bytes()).hexdigest()


SOURCE_FINGERPRINT = ('canonical-lf-sha256: SHA-256 of the UTF-8 source text after replacing every CRLF with LF '
                      '(Git stores these files with LF; a Windows checkout may contain CRLF)')


def source_sha256(path):
    """Checkout-independent fingerprint of a Python source file (CRLF -> LF)."""
    data = Path(path).read_bytes()
    data.decode('utf-8')  # source inputs must be UTF-8
    return sha256(data.replace(b'\r\n', b'\n')).hexdigest()


def verify(path, expected, size=None):
    path = Path(path)
    if not path.is_file():
        raise SystemExit(f'Missing pinned input: {path}')
    data = path.read_bytes()
    if sha256(data).hexdigest() != expected or (size is not None and len(data) != size):
        raise SystemExit(f'Pinned input hash/size mismatch: {path}')
    return data


def accepted(word):
    """Mirror gateway ordinary_words: letters, combining marks, apostrophes, ZWNJ/ZWJ.

    At least one letter is also required, so a lone apostrophe or joiner is not a word.
    """
    return any(char.isalpha() for char in word) and all(char.isalpha() or unicodedata.category(char).startswith('M') or char in "’'‌‍"
                              for char in word)


def in_script(word, language, ranges=None):
    ranges = ranges if ranges is not None else SCRIPTS.get(language)
    if ranges is None:
        return True
    # Marks and letters must belong to the language's own script block(s).
    return all(char in '‌‍' or any(a <= ord(char) <= b for a, b in ranges) for char in word)


def normal(word):
    return unicodedata.normalize('NFC', word).casefold()


def wordfreq_ranked(language):
    import wordfreq
    from importlib.metadata import version
    if version('wordfreq') != WORDFREQ_VERSION:
        raise SystemExit('wordfreq 3.1.1 is required')
    name, digest = WORDFREQ_FILES[language]
    path = Path(wordfreq.__file__).parent / 'data' / name
    verify(path, digest)
    for bucket in wordfreq.read_cBpack(str(path)):
        yield from bucket


def fasttext_ranked(data):
    """Words from a truncated .vec.gz prefix, in file (frequency) order; vectors discarded."""
    inflater = zlib.decompressobj(16 + zlib.MAX_WBITS)
    pending = b''
    header = None
    for start in range(0, len(data), 1 << 20):
        try:
            chunk = inflater.decompress(data[start:start + (1 << 20)])
        except zlib.error:
            break
        pending += chunk
        lines = pending.split(b'\n')
        pending = lines.pop()  # incomplete trailing line is never used
        for line in lines:
            if header is None:
                header = line.decode('ascii')
                continue
            word = line.split(b' ', 1)[0].decode('utf-8', errors='strict')
            yield word


def read_wikidata_labels(data, *, aliases=False):
    """Language-tagged Wikidata literals, normalised. Aliases drop abbreviations.

    Alias lists contain ISO/abbreviation codes (DE, ES, IL, USA, RF, in, tv) and
    one-character CJK abbreviations that collide with function words, so for aliases an
    all-uppercase cased form, a single-character form, or an ASCII form of at most three
    characters is skipped. Full labels are never filtered.
    """
    labels: dict[str, set[str]] = {}
    for line in data.decode('utf-8').splitlines():
        match = re.match(r'^"(.*)"@([a-z-]+)$', line.strip())
        if match:
            text = match.group(1).replace('\\"', '"').replace('\\\\', '\\')
            if aliases and (len(text) < 2 or text.isupper() or (len(text) <= 3 and text.isascii())):
                continue
            labels.setdefault(match.group(2), set()).add(normal(text))
    return labels


def read_geonames(cities, countries):
    """Primary names, all alternate names, and alternate names local to each language.

    countryInfo's Languages column decides locality, so a Latin-script language only
    receives alternate names of places in countries listing that language (de:
    München, Wien), avoiding collisions with other languages' place spellings.
    """
    primary, alternates, by_country = set(), set(), {}
    with zipfile.ZipFile(io.BytesIO(cities)) as archive:
        for line in io.TextIOWrapper(archive.open('cities15000.txt'), encoding='utf-8'):
            fields = line.rstrip('\n').split('\t')
            if int(fields[14] or 0) < PLACE_POPULATION:
                continue
            names = {normal(t) for t in fields[3].split(',') if t}
            primary.update(normal(t) for t in fields[1:3] if t)
            alternates.update(names)
            by_country.setdefault(fields[8], set()).update(names)
    spoken: dict[str, set[str]] = {}
    for line in countries.decode('utf-8').splitlines():
        if line and not line.startswith('#'):
            fields = line.split('\t')
            if len(fields) > 4 and fields[4]:
                primary.add(normal(fields[4]))
            if len(fields) > 15:
                for code in fields[15].split(','):
                    spoken.setdefault(code.split('-')[0].strip().lower(), set()).add(fields[0])
    local = {language: set().union(*(by_country.get(c, set()) for c in sorted(spoken.get(language, ()))))
             for language in LANGUAGES}
    return primary, alternates, local


def read_geonames_india(data, language):
    names = set()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for line in io.TextIOWrapper(archive.open('IN.txt'), encoding='utf-8'):
            fields = line.rstrip('\n').split('\t')
            if len(fields) > 8 and fields[2] == language and fields[8] != '1':
                names.add(normal(fields[3]))
    return names


def read_jieba_names():
    import jieba
    path = Path(jieba.__file__).parent / JIEBA[0]
    data = verify(path, JIEBA[1])
    names = set()
    for line in data.decode('utf-8').splitlines():
        parts = line.split()
        # Single characters tagged as names are mostly ordinary morphemes (e.g. common
        # characters with a surname reading); only whole multi-character entries count.
        if len(parts) == 3 and parts[2] in JIEBA_NAME_TAGS and len(parts[0]) >= 2:
            names.add(normal(parts[0]))
    return names


def authored_sets():
    sys.path.insert(0, str(ROOT / 'src'))
    from secure_gateway.gateway_name_vocabulary import NAME_WORDS
    from secure_gateway.gateway_vocabulary import DOMAIN_WORDS, ENGLISH_NAMES
    files = {name: source_sha256(ROOT / 'src' / 'secure_gateway' / name)
             for name in ('gateway_name_vocabulary.py', 'gateway_vocabulary.py')}
    names = {language: {normal(w) for w in NAME_WORDS.get(language, ())} for language in LANGUAGES}
    names['en'] |= {normal(w) for w in ENGLISH_NAMES}
    domains = {language: {normal(w) for w in DOMAIN_WORDS.get(language, ())} for language in LANGUAGES}
    return names, domains, files


def korean_name_inflection(names):
    """Reviewed generic rule: a known name/place form of >= 2 syllables plus one Korean particle.

    Applied only to whitespace-delimited fallback (fastText) entries. wordfreq ko entries are
    MeCab morphemes whose particles are already split, and single-syllable surnames plus
    particles would otherwise match grammatical endings such as 다는 or 지만.
    """
    sys.path.insert(0, str(ROOT / 'src'))
    from secure_gateway.engine.grammar_ko import KOREAN_JOSA_LIST
    particles = sorted({normal(p) for p in KOREAN_JOSA_LIST if p}, key=len, reverse=True)

    def inflected(word):
        return any(word.endswith(p) and len(word) - len(p) >= 2 and word[:-len(p)] in names for p in particles)
    return inflected


def korean_predicates(extracts, head, blocked):
    """Dictionary-form verb/adjective lemmas from Wiktionary, gated by generic frequency.

    A lemma (stem + 다) is kept only if the lemma or its bare stem is among the first
    PREDICATE_GATE frequency candidates (before any exclusion), it is Hangul-only, and
    it has at least one sense not tagged form-of/alt-of/dialectal/archaic/obsolete.
    Authored name/domain forms and listed name exclusions always win. No glosses kept.
    """
    result, stats = {}, {'gate_candidates': len(head), 'gate': PREDICATE_GATE,
                         'excluded_sense_tags': sorted(PREDICATE_EXCLUDED_SENSE_TAGS)}
    for kind, data in extracts.items():
        entries: dict[str, bool] = defaultdict(bool)
        for line in gzip.decompress(data).decode('utf-8').splitlines():
            entry = json.loads(line)
            word = normal(entry.get('word', ''))
            if entry.get('lang_code') != 'ko' or not word.endswith('\ub2e4') or len(word) < 2:
                continue
            if not all('\uac00' <= char <= '\ud7a3' for char in word):
                continue
            ordinary = any(not PREDICATE_EXCLUDED_SENSE_TAGS & set(sense.get('tags', ())) for sense in entry.get('senses', ()))
            entries[word] |= ordinary
        lemmas = sorted(w for w, ordinary in entries.items()
                        if ordinary and (w in head or w[:-1] in head) and w not in blocked)
        result[kind] = lemmas
        stats[kind] = {'extract_lemmas': len(entries), 'ordinary_lemmas': sum(entries.values()), 'kept': len(lemmas)}
    return result, stats


CLOSED_CLASS_MODULES = ('engine/grammar_en.py', 'engine/grammar_ko.py', 'engine/natural_languages.py')


def closed_class_words(language):
    """Independently authored closed-class grammar words used by the engines."""
    sys.path.insert(0, str(ROOT / 'src'))
    from secure_gateway.engine.grammar_en import CLOSED_CLASS_WORDS as english
    from secure_gateway.engine.grammar_ko import KOREAN_FUNCTION_WORDS as korean
    from secure_gateway.engine.natural_languages import CLOSED_CLASS_WORDS as others
    words = set(others.get(language, ()))
    if language == 'en':
        words |= set(english)
    if language == 'ko':
        words |= set(korean)
    return {normal(word) for word in words}


def closed_class_provenance():
    return {'symbols': {'en': 'secure_gateway.engine.grammar_en.CLOSED_CLASS_WORDS',
                        'ko': 'secure_gateway.engine.grammar_ko.KOREAN_FUNCTION_WORDS',
                        'other': 'secure_gateway.engine.natural_languages.CLOSED_CLASS_WORDS[language]'},
            'fingerprint': SOURCE_FINGERPRINT,
            'canonical_lf_sha256': {name: source_sha256(ROOT / 'src' / 'secure_gateway' / name) for name in CLOSED_CLASS_MODULES}}


def gzip_bytes(payload):
    buffer = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=buffer, mtime=0, compresslevel=9) as stream:
        stream.write(payload)
    data = bytearray(buffer.getvalue())
    data[9] = 255  # OS byte: "unknown", independent of the build platform.
    return bytes(data)


def canonical_json(value, *, indent=None):
    separators = (',', ': ') if indent else (',', ':')
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=indent, separators=separators) + '\n').encode('utf-8')


def curate_language(language, ranked, name_sources, authored_names, domain_words, *, target=TARGET_WORDS,
                    name_inflection=None):
    """Select up to `target` ordinary words in rank order; exact-label exclusions only.

    `ranked` yields (raw entry, source id, script ranges or None) in source rank order.
    The predicate gate uses only the first source's first PREDICATE_GATE candidates.
    """
    seen, words, excluded, retained, head = set(), [], set(), [], []
    closed = closed_class_words(language)
    stats = {'ranked_entries_read': 0, 'unicode_rejected': 0, 'script_rejected': 0, 'duplicate_after_normalization': 0,
             'domain_filtered': 0, 'authored_name_excluded': 0, 'name_inflection_excluded': 0,
             'name_excluded_by_source': {}, 'candidates_scanned': 0, 'read_by_source': {}, 'words_by_source': {}}
    first_source = None
    for raw, source_id, ranges in ranked:
        first_source = first_source or source_id
        stats['ranked_entries_read'] += 1
        stats['read_by_source'][source_id] = stats['read_by_source'].get(source_id, 0) + 1
        if not accepted(raw):
            stats['unicode_rejected'] += 1
            continue
        if not in_script(raw, language, ranges):
            stats['script_rejected'] += 1
            continue
        word = normal(raw)
        if not accepted(word) or word in seen:
            stats['duplicate_after_normalization'] += 1
            continue
        seen.add(word)
        rank = stats['candidates_scanned']
        stats['candidates_scanned'] += 1
        if rank < PREDICATE_GATE and source_id == first_source:
            head.append(word)
        if word in domain_words:
            stats['domain_filtered'] += 1
            continue
        if word in authored_names:
            stats['authored_name_excluded'] += 1
            excluded.add(word)
            continue
        if name_inflection is not None and source_id != first_source and name_inflection(word):
            stats['name_inflection_excluded'] += 1
            excluded.add(word)
            continue
        hits = sorted(source for source, labels in name_sources.items() if word in labels)
        if hits:
            if word in closed:
                retained.append({'word': word, 'candidate_rank': rank, 'sources': hits})
            else:
                for source in hits:
                    stats['name_excluded_by_source'][source] = stats['name_excluded_by_source'].get(source, 0) + 1
                excluded.add(word)
                continue
        words.append(word)
        stats['words_by_source'][source_id] = stats['words_by_source'].get(source_id, 0) + 1
        if len(words) >= target:
            break
    stats['target'] = target
    stats['source_exhausted'] = len(words) < target
    stats['first_candidates'] = head  # Popped by the caller; used only as the predicate gate.
    return sorted(words), sorted(excluded), retained, stats


def build(cache_dir, legacy_dir, output):
    cache = {key: verify(Path(cache_dir) / name, digest, size) for key, (name, digest, size, _) in CACHE_INPUTS.items()}
    legacy = {key: verify(Path(legacy_dir) / name, digest, size) for key, (name, digest, size, _) in LEGACY_INPUTS.items()}
    given = read_wikidata_labels(cache['wikidata_given_names'])
    family = read_wikidata_labels(cache['wikidata_family_names'])
    geo_primary, geo_alternates, geo_local = read_geonames(cache['geonames_cities15000'], cache['geonames_countryinfo'])
    countries = read_wikidata_labels(cache['wikidata_country_labels'])
    country_aliases = read_wikidata_labels(cache['wikidata_country_aliases'], aliases=True)
    authored_names, domains, authored_files = authored_sets()
    jieba_names = read_jieba_names()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    languages = {}
    for language in LANGUAGES:
        sources = {'wikidata_given_names': given.get(language, set()) | given.get('mul', set()),
                   'wikidata_family_names': family.get(language, set()) | family.get('mul', set()),
                   'wikidata_country_labels': countries.get(language, set()) | countries.get('mul', set()),
                   'wikidata_country_aliases': country_aliases.get(language, set()) | country_aliases.get('mul', set()),
                   'geonames_places': geo_primary | (geo_local[language] if language in LATIN else geo_alternates)}
        source_ids = ['wikidata', 'geonames', 'secure_gateway_authored']
        target, fallback, inflection = TARGET_WORDS, None, None
        if language in {'mr', 'te'}:
            sources['wikidata_name_classes'] = read_wikidata_labels(legacy[f'wikidata_name_classes_{language}']).get(language, set())
            sources['geonames_alternatenames_in'] = read_geonames_india(legacy['geonames_alternatenames_in'], language)
            ranked = ((w, 'fasttext_cc', None) for w in fasttext_ranked(cache[f'fasttext_{language}_prefix']))
            primary = 'fasttext_cc'
        else:
            ranked = ((w, 'wordfreq', None) for w in wordfreq_ranked(language))
            primary = 'wordfreq'
        if language in FALLBACK_SCRIPTS:
            target, fallback = FALLBACK_TARGET, f'fasttext_{language}_prefix'
            ranked = chain(ranked, ((w, 'fasttext_cc', FALLBACK_SCRIPTS[language])
                                    for w in fasttext_ranked(cache[fallback])))
            source_ids.append('fasttext_cc')
        if language == 'ko':
            inflection = korean_name_inflection(set().union(*sources.values()) | authored_names[language])
        if language == 'zh':
            sources['jieba_name_tags'] = jieba_names
            source_ids.append('jieba')
        words, excluded, retained, stats = curate_language(language, ranked, sources, authored_names[language], domains[language],
                                                           target=target, name_inflection=inflection)
        head = set(stats.pop('first_candidates'))
        record = {'schema_version': SCHEMA_VERSION, 'data_version': DATA_VERSION, 'language': language,
                  'words': words, 'name_exclusions': excluded}
        predicate_stats = None
        if language == 'ko':
            blocked = authored_names[language] | domains[language] | set(excluded)
            record['predicate_lemmas'], predicate_stats = korean_predicates(
                {'verb': cache['kaikki_ko_verb'], 'adjective': cache['kaikki_ko_adj']}, head, blocked)
            source_ids.append('wiktionary')
        source_ids = sorted([primary] + source_ids)
        record['source_ids'] = source_ids
        data = gzip_bytes(canonical_json(record))
        filename = f'{language}.json.gz'
        (output / filename).write_bytes(data)
        languages[language] = {
            'file': filename, 'sha256': sha256(data).hexdigest(), 'bytes': len(data),
            'words': len(words), 'name_exclusions': len(excluded), 'source_ids': source_ids,
            'primary_source': primary, 'fallback_source': 'fasttext_cc' if fallback else None,
            'fallback_input': (CACHE_INPUTS[fallback][0] + ' sha256 ' + CACHE_INPUTS[fallback][1]) if fallback else None,
            'words_licence': LICENCES[primary]['licence'], 'target_words': target,
            'licence_note': ('CC BY-SA 4.0 adaptation combining wordfreq (CC BY-SA 4.0) and fastText (CC BY-SA 3.0); BY-SA 3.0 '
                             'Section 4(b)(ii) permits an Adaptation under a later version with the same License Elements')
            if fallback else None,
            'coverage': 'target_met' if len(words) >= target else ('within_target_range' if len(words) >= 30_000 else 'below_target'),
            'closed_class_exceptions': len(retained), 'closed_class_exception_list': retained, 'statistics': stats,
            **({'predicate_lemmas': predicate_stats} if predicate_stats else {}),
            'primary_input': (WORDFREQ_FILES[language][0] + ' sha256 ' + WORDFREQ_FILES[language][1]) if primary == 'wordfreq'
            else CACHE_INPUTS[f'fasttext_{language}_prefix'][0] + ' sha256 ' + CACHE_INPUTS[f'fasttext_{language}_prefix'][1],
        }
    manifest = {
        'schema_version': SCHEMA_VERSION, 'data_version': DATA_VERSION,
        'generator': {'script': 'scripts/curate_common_vocabulary.py', 'canonical_lf_sha256': source_sha256(Path(__file__)),
                      'fingerprint': SOURCE_FINGERPRINT},
        'parameters': {'target_words': TARGET_WORDS, 'wikidata_bearer_threshold': BEARER_THRESHOLD,
                       'name_exemption_policy': 'No frequency-rank exemption. Only exact authored closed-class grammar words '
                                                '(see inputs.closed_class) may stay ordinary despite a name/place match; '
                                                'each is listed per language. Authored name/domain denysets always win.',
                       'geonames_min_population': PLACE_POPULATION,
                       'fallback_target_words': FALLBACK_TARGET,
                       'fallback_languages': sorted(FALLBACK_SCRIPTS),
                       'fallback_script_rule': {k: [f'U+{a:04X}-U+{b:04X}' for a, b in v] for k, v in FALLBACK_SCRIPTS.items()},
                       'korean_name_inflection_rule': 'fallback (fastText) entries only: exclude a name/place form of >= 2 syllables followed by one '
                                                      'particle of engine.grammar_ko.KOREAN_JOSA_LIST',
                       'unicode_rule': 'letters, combining marks, apostrophes, ZWNJ/ZWJ; NFC + casefold',
                       'script_rule': {k: [f'U+{a:04X}-U+{b:04X}' for a, b in v] for k, v in SCRIPTS.items()},
                       'latin_geonames_scope': 'cities15000 name/asciiname, country names, and alternate names of places '
                                               'in countries whose countryInfo Languages list the language',
                       'other_geonames_scope': 'cities15000 name/asciiname/alternatenames and country names'},
        'inputs': {
            'wordfreq': {'version': WORDFREQ_VERSION, 'files': {k: {'file': v[0], 'sha256': v[1]} for k, v in WORDFREQ_FILES.items()}},
            'jieba': {'version': JIEBA[2], 'file': JIEBA[0], 'sha256': JIEBA[1], 'tags': sorted(JIEBA_NAME_TAGS), 'min_length': 2},
            'cache': {k: {'file': v[0], 'sha256': v[1], 'bytes': v[2], 'origin': v[3]} for k, v in CACHE_INPUTS.items()},
            'legacy_cache': {k: {'file': v[0], 'sha256': v[1], 'bytes': v[2], 'origin': v[3]} for k, v in LEGACY_INPUTS.items()},
            'authored': {'fingerprint': SOURCE_FINGERPRINT, 'canonical_lf_sha256': authored_files},
            'closed_class': closed_class_provenance(),
        },
        'licences': LICENCES,
        'languages': languages,
    }
    (output / 'manifest.json').write_bytes(canonical_json(manifest, indent=2))
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--cache-dir', required=True, type=Path)
    parser.add_argument('--legacy-cache-dir', type=Path, default=None,
                        help='Directory with the earlier validated cache (defaults to --cache-dir).')
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--check', action='store_true', help='Rebuild into a temporary directory and compare bytes.')
    args = parser.parse_args(argv)
    legacy = args.legacy_cache_dir or args.cache_dir
    if args.check:
        with tempfile.TemporaryDirectory() as directory:
            build(args.cache_dir, legacy, directory)
            names = ['manifest.json'] + [f'{language}.json.gz' for language in LANGUAGES]
            different = [name for name in names
                         if (Path(directory) / name).read_bytes() != (args.output / name).read_bytes()]
        if different:
            print('Differs: ' + ', '.join(different))
            return 1
        print('All common-vocabulary files reproduce byte-for-byte.')
        return 0
    manifest = build(args.cache_dir, legacy, args.output)
    for language, row in manifest['languages'].items():
        print(language, row['words'], row['name_exclusions'], row['coverage'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
