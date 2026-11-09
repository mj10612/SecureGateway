# Common-vocabulary data sources (issue #323)

Data version **1.1.0**, schema **1**, built 2026-11-09. Data 1.0.0 was the first development candidate;
its bytes are preserved under `docs/evaluations/issue323-2.7.2/development-candidate-1/` by the root workflow.
This page covers **data only**. The files are not loaded by the gateway yet:
runtime integration, precedence and morphology are separate work. No task,
reference or evaluation text was read or used, and no entries were added by hand.

## Files and loader contract

**Location:** `src/secure_gateway/data/common_vocabulary/`

**`<lang>.json.gz`** — one file for each of the 17 languages: en ko es fr pt de id tr ru hi mr bn ur te ar zh ja.
- Gzip header: no file name, `mtime` 0, OS byte 255.
- Content: canonical UTF-8 JSON — sorted keys, no spaces, a single trailing LF.
- Keys:
  - `schema_version` = 1
  - `data_version` = "1.0.0"
  - `language`
  - `words`: sorted, unique, NFC + casefold
  - `name_exclusions`: sorted exact forms
  - `source_ids`
  - `predicate_lemmas`: **ko only**, optional, typed `{"verb": [...], "adjective": [...]}`

**`manifest.json`** (pinned LF):
- the generator hash and parameters
- every input hash and origin
- licences
- the provenance of the closed-class inventories
- per language:
  - file SHA-256 and bytes
  - counts and coverage status
  - per-source exclusion counts
  - processing statistics
  - the exact list of closed-class exceptions

**`NOTICE.md`:** the licence and attribution notice that must travel with the data.

Expected runtime use (owned by the runtime integration):
1. Explicit, private, code and domain protections keep precedence.
2. A token in `name_exclusions` is never disclosed as ordinary vocabulary.
3. Only tokens in `words` are ordinary-word candidates.

Frequency is not permission to disclose a private homonym. The existing natural-language
engines keep their own reviewed grammar inventories, so excluding a homonym here does
not make ordinary grammar private.

## Sources and licences

| Languages | Source | Licence | Pinned input |
| --- | --- | --- | --- |
| en ko es fr pt de id tr ru hi bn ur ar zh ja | wordfreq 3.1.1 packaged frequency lists (Robyn Speer et al.) | Data **CC BY-SA 4.0**, with credits for Google Books Ngrams, SUBTLEX, OpenSubtitles, Leeds, Wikipedia, ParaCrawl; code Apache-2.0 | Per-file SHA-256 of `large_*`/`small_*` msgpack in the manifest |
| mr te | fastText Common Crawl vectors `cc.{mr,te}.300.vec.gz`. The publisher states the words are "sorted by frequency in descending order". | **CC BY-SA 3.0** (publisher page). Cite Grave et al., LREC 2018 | Gzip prefix bytes 0–41,943,039 of each file, SHA-256 in the manifest. Content-Length, Last-Modified and ETag were recorded. Bytes 0–12,582,911 reused the earlier validated prefix. |
| exclusions | Wikidata `rdfs:label` and `skos:altLabel` (17 languages + `mul`, plus regional variants zh-hans/zh-hant/zh-cn/zh-tw/zh-hk/zh-sg/pt-br folded to the base language) of **every** given-name item (P735) and family-name item (P734) used by at least one entity | CC0 1.0 | 8 gzip query results: `wd_P73{5,4}_{label,altLabel}_{all,variants}.tsv.gz`, about 10.6M rows in total, with query hashes in the manifest (QLever, dump 2026-08-10) |
| exclusions | Wikidata labels and `skos:altLabel` aliases of country (Q6256) and sovereign-state (Q3624078) items | CC0 1.0 | `wd_countries.tsv`, `wd_country_aliases.tsv` (143,665 B) and their query hashes |
| exclusions | GeoNames `cities15000` (the whole file, population ≥ 15,000) and `countryInfo` | CC BY 4.0 (attribution: GeoNames) | `cities15000.zip`, `countryInfo.txt` |
| mr/te exclusions | GeoNames India alternate names tagged mr/te (non-historic). Wikidata given/family-name class labels from the reviewed prior memo. | CC BY 4.0 / CC0 | `geonames_alt_IN.zip`, `ql_labels_names_{mr,te}.tsv` (hashes match `docs/research/issue323-additional-source-manifest.json`) |
| zh exclusions | Installed jieba 0.42.1 `dict.txt` entries tagged `nr nrt nrfg ns nt` with at least 2 characters | MIT | `dict.txt` sha256 `7197c321…` |
| all | Authored `NAME_WORDS`, `ENGLISH_NAMES`, `DOMAIN_WORDS` (additive, always win) | Apache-2.0 | Module hashes in the manifest |
| ko `predicate_lemmas` | English Wiktionary Korean verb/adjective entries, extracted with wiktextract (commit `19f9a30`, extraction 2026-10-30 of the 2026-10-01 dump) and distributed by kaikki.org | **CC BY-SA 4.0** (Wiktionary text is dual-licensed CC BY-SA 4.0 and GFDL per `Wiktionary:Copyrights`) | `kaikki_ko_verb.jsonl.gz` (4,571,801 B), `kaikki_ko_adj.jsonl.gz` (1,482,065 B); SHA-256, Last-Modified and ETag in the manifest |
| exemptions | Authored closed-class grammar inventories: `engine.grammar_en.CLOSED_CLASS_WORDS` (en), `engine.grammar_ko.KOREAN_FUNCTION_WORDS` (ko), `engine.natural_languages.CLOSED_CLASS_WORDS[lang]` (all) | Apache-2.0 | File hashes in `manifest.inputs.closed_class` |

**GeoNames scope.**
- Non-Latin languages use primary and all alternate names.
- Latin-script languages use primary names, country names, and alternate names of places in countries whose `countryInfo` Languages column lists the language. Examples: de receives `münchen` and `wien`; es receives `méxico`. This avoids importing other languages' spellings.

**Redistribution.** Derived lists may be redistributed only as separate data files
carrying `NOTICE.md`, under the source's ShareAlike licence: BY-SA 4.0 for the
wordfreq languages, BY-SA 3.0 for mr/te. That ShareAlike licence does not extend to
the Apache-2.0 Python code. This is not legal advice.

**Not used:**
- IndicCorp text: its licence is a prose-only, future-tense CC0 statement.
- mecab-ko-dic and Sejong-derived lists: research-only, non-commercial terms.
- open-korean-text lists: undocumented provenance.

## Method (deterministic, offline)

1. **Read** ranked entries in source order: wordfreq frequency buckets, or fastText
   file order. For fastText, the header and vector values are discarded, and the
   incomplete final line of the prefix is ignored.
2. **Unicode rule.** Mirroring `ordinary_words`, every character must be a letter,
   a combining mark, an apostrophe, ZWNJ or ZWJ (`str.isalpha` alone is not
   sufficient for Indic scripts). Then apply NFC + casefold and drop duplicates.
   - mr and te must additionally be entirely in Devanagari (U+0900–097F, U+A8E0–A8FF)
     or Telugu (U+0C00–0C7F) script, or ZWNJ/ZWJ.
3. **Authored denysets.** Drop authored domain words. Always exclude authored names.
4. **Exact whole-label matching.** A candidate equal to any name or place label is
   excluded. Labels are never split into tokens.
   - **Country aliases** skip abbreviations: a form that is all uppercase (DE, USA,
     RF), one character long (CJK `中`, `米`), or ASCII and at most 3 characters
     (`in`, `tv`). This is a generic code filter; full labels are never filtered.
   - **No frequency-rank exemption.**
   - **The only exemption** is an exact word in the authored closed-class grammar
     inventories above. Example: en `the`, `for`, `will`; de `das`, `weil`; ko `이`.
     Every exempted word and its matching sources is listed in the manifest
     (`closed_class_exception_list`). Open-class nouns, adjectives and other frequent
     tokens are never exempted.
5. **Keep** the first 50,000 surviving candidates and write them sorted.

### Policy history (data review)

| Version | Name/place source | Outcome |
| --- | --- | --- |
| 1 | Raw Wikidata name-class labels, no usage threshold | Matched almost every function word (the, de, 是) |
| 2 | Names used ≥ 25 times; GeoNames ≥ 15,000 | Still excluded `peace`, `normal`, `husband` |
| 3 | Names used ≥ 100 times; GeoNames ≥ 100,000 | Kept every name/place match among the first 1,000 candidates as ordinary |
| 1.0.0 | Names used ≥ 100 times; GeoNames ≥ 100,000 | Exemption limited to authored closed-class words; country labels, aliases and local alternate names added. The first development privacy gate failed. |
| **1.1.0 (current)** | Every attested name item's labels and aliases (≥ 1 user), with regional variants; GeoNames ≥ 15,000 | Much larger exclusion sets. Frequent homonyms are excluded unless they are authored closed-class grammar words. |

**Why version 3 was rejected.** Data review found that the blanket rank exemption kept
proper place and name forms such as `berlin`, `hamburg` and `deutschland` in `de.words`.
Ordinary German noun capitalization would then disclose them.

**What the current policy changes:**
- German now excludes Berlin, Hamburg, Deutschland, München, Wien, Köln, Mann and Klein.
- Frequent open-class homonyms are now excluded too, toward masking: about 120 of
  wordfreq's top 1,000 en words, e.g. `good`, `day`, `way`, `said`, `house`, and 106 of
  the top 1,000 de words.

The thresholds are generic parameters recorded in the manifest. They were not tuned
against any evaluation text. The tests contain generic data-review controls drawn from
public place and name sources (e.g. Berlin, Hamburg, Mann, Klein, London, Madrid,
Москва), not from evaluation material.

### Korean predicate lemmas

**Why.** Morphology callbacks need dictionary-form predicates (stem + 다), while wordfreq
ko holds bare MeCab morphemes. Source-backed name exclusion correctly removes `하` and
`주` (attested surnames). A typed predicate list lets ordinary 하다/주다 be recognised
without any rank exemption for noun or name forms.

**Deterministic filter:**
1. Wiktionary `pos` must be verb or adj, with `lang_code` ko.
2. The lemma is NFC, Hangul syllables only, at least 2 characters, ending in 다.
3. At least one sense is not tagged form-of, alt-of, dialectal, archaic or obsolete.
4. The lemma **or its bare stem** is among the first 1,000 Korean wordfreq candidates
   after Unicode filtering and deduplication, before any exclusion.
5. Authored name/domain forms and any listed name exclusion win.

**Result:** 139 verbs (from 3,442 extract lemmas) and 40 adjectives (from 1,308).
- Some Wiktionary entries are themselves inflected forms with a standalone sense
  (e.g. `한다`, `했다`). A lemma can appear as both verb and adjective (e.g. `있다`).
- These lists are independently sourced grammatical-role information, not named
  examples added by hand.
- Network for this addition: 5.8 MiB of compressed extracts plus about 63 KB of
  licence pages.

### Fallback for ko, id, hi and ur

**Why.** The wordfreq lists for these four languages are the small lists and run out
below 30,000.

**How the lists are filled:**
1. Every wordfreq entry is processed first.
2. The lists then continue with the frequency-ordered fastText Common Crawl vocabulary
   of the same language. Words only are read; vectors are discarded.
3. The same Unicode, name/place and domain filters apply, plus a script rule for
   fastText entries:
   - ko: Hangul
   - id: Latin letters and apostrophes
   - hi: Devanagari
   - ur: Arabic blocks, without presentation-form ligatures
4. Processing stops at 30,000 words.

Every entry must also contain at least one letter, so a lone apostrophe is not a word.

**Korean particles.** Korean fastText entries are whitespace eojeol. A reviewed generic
rule therefore excludes a name/place form of at least two syllables followed by one
particle from `engine.grammar_ko.KOREAN_JOSA_LIST` (e.g. 한국은). The rule is not applied
to wordfreq morphemes, which already have their particles split. The typed Korean
predicate gate still uses only the first 1,000 wordfreq candidates.

**Pinned prefixes** (ETags match the full files):

| Language | Prefix | Ranges |
| --- | --- | --- |
| ko | 16 MiB | one |
| id | 32 MiB | two (0–16 MiB, 16–32 MiB) |
| hi | 32 MiB | two |
| ur | 48 MiB | two (0–16 MiB, 16–48 MiB) |

Network for this addition: 128 MiB of the 160 MiB allowed, plus 22 KB for the CC BY-SA
3.0 legal code.

**Licence.** CC BY-SA 3.0 Section 4(b)(ii), verified from the pinned legal code, allows
an Adaptation under a later version with the same License Elements. These four files
are therefore CC BY-SA 4.0 adaptations that credit both wordfreq and fastText. The
manifest records each language's target, its word count per source and its entries
read per source.

### Source-code fingerprints

Hashes of Python source inputs use **canonical LF SHA-256**: the UTF-8 text with every
CRLF replaced by LF, then SHA-256. This covers:
- the generator script
- the authored denyset modules
- the closed-class grammar modules

Git stores these files with LF, but a Windows checkout may contain CRLF. For example,
`engine/grammar_ko.py` and `engine/natural_languages.py` were CRLF in the build checkout.
The recorded values equal the SHA-256 of the committed Git blobs.

Downloaded and binary inputs, and the generated `.json.gz` files, keep exact raw-byte
SHA-256 and size checks.

## Results

| Lang | Source(s) | Target | Words | wordfreq / fastText words | Name exclusions (1.0.0 → 1.1.0) | Closed-class exceptions | Ranked entries read (wordfreq / fastText) | Unicode / script rejected | `.json.gz` bytes |
| --- | --- | ---: | ---: | --- | --- | ---: | --- | ---: | ---: |
| en | wordfreq | 50,000 | 50,000 | 50,000 / 0 | 7,834 → 28,017 | 109 | 79,691 / 0 | 1,627 / 0 | 228,857 |
| ko | wordfreq + fastText | 30,000 | 30,000 | 24,740 / 5,260 | 1,676 → 5,777 | 10 | 29,988 / 12,131 | 1,055 / 955 | 116,276 |
| es | wordfreq | 50,000 | 50,000 | 50,000 / 0 | 5,099 → 15,837 | 20 | 66,464 / 0 | 621 / 0 | 185,194 |
| fr | wordfreq | 50,000 | 50,000 | 50,000 / 0 | 5,781 → 19,729 | 21 | 70,532 / 0 | 797 / 0 | 197,844 |
| pt | wordfreq | 50,000 | 50,000 | 50,000 / 0 | 5,740 → 17,478 | 25 | 68,178 / 0 | 694 / 0 | 192,067 |
| de | wordfreq | 50,000 | 50,000 | 50,000 / 0 | 5,234 → 15,750 | 28 | 66,384 / 0 | 628 / 0 | 206,258 |
| id | wordfreq + fastText | 30,000 | 30,000 | 21,497 / 8,503 | 3,905 → 12,918 | 9 | 31,188 / 56,690 | 5,644 / 62 | 132,930 |
| tr | wordfreq | 50,000 | 50,000 | 50,000 / 0 | 2,949 → 9,063 | 13 | 59,357 / 0 | 287 / 0 | 166,169 |
| ru | wordfreq | 50,000 | 50,000 | 50,000 / 0 | 2,589 → 5,580 | 12 | 55,778 / 0 | 192 / 0 | 185,780 |
| hi | wordfreq + fastText | 30,000 | 30,000 | 23,941 / 6,059 | 1,013 → 2,636 | 2 | 26,653 / 33,947 | 2,130 / 4,455 | 124,289 |
| mr | fastText | 50,000 | 50,000 | 0 / 50,000 | 1,147 → 1,351 | 0 | 0 / 62,594 | 3,740 / 7,493 | 195,295 |
| bn | wordfreq | 50,000 | 50,000 | 50,000 / 0 | 1,616 → 3,410 | 0 | 53,727 / 0 | 312 / 0 | 194,808 |
| ur | wordfreq + fastText | 30,000 | 30,000 | 21,341 / 8,659 | 1,184 → 2,284 | 3 | 23,201 / 45,513 | 5,046 / 10,307 | 103,177 |
| te | fastText | 50,000 | 50,000 | 0 / 50,000 | 804 → 980 | 1 | 0 / 62,263 | 3,288 / 7,960 | 201,973 |
| ar | wordfreq | 50,000 | 50,000 | 50,000 / 0 | 2,712 → 5,553 | 4 | 55,749 / 0 | 191 / 0 | 168,898 |
| zh | wordfreq | 50,000 | 50,000 | 50,000 / 0 | 10,186 → 15,355 | 12 | 65,761 / 0 | 394 / 0 | 229,359 |
| ja | wordfreq | 50,000 | 50,000 | 50,000 / 0 | 4,280 → 15,292 | 1 | 65,713 / 0 | 410 / 0 | 226,287 |

**Exclusions by source** (a word can match more than one source) and the exact
closed-class exceptions:

| Lang | Wikidata given | Wikidata family | Wikidata country labels | Wikidata country aliases | GeoNames places | Other | Closed-class exceptions |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| en | 13,386 | 23,310 | 160 | 66 | 5,761 | — | the, to, and, of, a, in, i, for, you, on, with, this, was, be, as, are, have, at, he, not, by, but, from, my, or, we, an, all, so, his, they, me, one, can, will, just, like, about, out, what, has, more, do, no, were, had, her, been, would, she, how, some, them, other, its, our, than, only, him, into, over, any, then, us, well, most, much, very, even, may, too, off, still, many, never, down, while, such, both, every, am, does, under, during, must, ever, doing, few, done, everything, yet, less, along, else, past, rather, near, ones, mine, shall, via, nobody, nor, toward, anybody, fewer, ours, hers, amid |
| ko | 3,293 | 2,053 | 121 | 30 | 1,136 | name + particle 544 | 이, 더, 저, 이런, 참, 각, 아주, 매, 다만, 하다 |
| es | 7,159 | 13,382 | 159 | 46 | 3,370 | — | de, la, que, el, en, a, los, un, por, del, las, con, una, para, al, como, si, pero, o, sin |
| fr | 8,390 | 16,937 | 159 | 70 | 3,844 | — | de, la, le, les, en, des, un, que, une, du, pour, dans, au, sur, par, mais, ou, si, aux, sans, sous |
| pt | 8,479 | 14,206 | 156 | 52 | 3,265 | — | de, a, o, que, e, do, em, da, para, um, uma, no, se, na, por, os, as, dos, mas, ao, das, ou, nos, sem, nas |
| de | 6,044 | 14,048 | 149 | 38 | 2,353 | — | die, der, in, das, zu, den, von, ein, auf, für, im, eine, dem, des, an, dass, bei, aber, wenn, oder, einen, am, einer, zum, einem, zur, weil, eines |
| id | 6,466 | 10,714 | 163 | 44 | 2,461 | — | yang, dan, di, dari, adalah, pada, ke, karena, antara |
| tr | 4,938 | 7,496 | 109 | 14 | 1,385 | — | ve, bir, bu, de, da, ile, kadar, o, ama, ki, mi, mu, mü |
| ru | 2,548 | 3,892 | 102 | 20 | 1,340 | — | и, на, по, а, о, но, у, до, или, во, со, ко |
| hi | 890 | 1,354 | 108 | 29 | 917 | — | एक, तक |
| mr | 268 | 147 | 152 | 3 | 659 | GeoNames IN 280, Wikidata name classes 298 | — |
| bn | 1,690 | 1,998 | 144 | 34 | 836 | — | — |
| ur | 586 | 622 | 147 | 30 | 1,258 | — | اور, ایک, اگر |
| te | 246 | 305 | 119 | 13 | 224 | GeoNames IN 212, Wikidata name classes 327 | లేదా |
| ar | 3,072 | 3,137 | 137 | 45 | 1,295 | — | في, بين, دون, ال |
| zh | 4,957 | 6,930 | 105 | 122 | 2,623 | jieba 8,919 | 是, 在, 了, 和, 有, 为, 到, 被, 但, 从, 及, 那 |
| ja | 7,105 | 10,802 | 166 | 40 | 3,103 | — | ます |

**Size:** the 17 data files total about 3.06 MB of gzip, plus a 92 KB manifest.
The largest file is about 0.23 MB compressed. Name-exclusion sets are at most 28,017 entries, within the
loader limits of 4 MiB compressed, 16 MiB JSON and 100,000 entries. A local curator run of
data 1.1.0 peaked at about 1.4 GiB of Python allocations (tracemalloc), because about 10M
name labels are held in memory, and took about 100 s.

## Data 1.1.0 trade-off (measured)

Wikidata has family-name and given-name items, each used by at least one person, whose
labels equal a large share of ordinary words. For example, native English family-name
labels alone match 504 of wordfreq's top 1,000 English words.

**Measured attribution** (top 1,000 en words matched):

| Source | Native-language labels | `mul` labels |
| --- | ---: | ---: |
| Family-name labels | 504 | 425 |
| Given-name labels | 244 | 175 |

Aliases add few matches (en: 15–33).

**Effect.** As instructed, there is no frequency exemption, so these homonyms are
excluded. Share of wordfreq's top 1,000 words now in `name_exclusions`:

| Lang | en | de | fr | es | ko | ja | zh | ru | hi |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Excluded | 484 | 474 | 452 | 405 | 299 | 258 | 200 | 117 | 80 |

- Examples: en `time`, `people`, `good`; de `nicht`, `sie`, `es`.
- Ordinary lists still reach their targets by continuing the same source ranking deeper
  (en read 79,691 wordfreq entries). They therefore contain rarer words, and many
  common words are now masked.
- Only the authored closed-class inventories stay ordinary. Those inventories are small
  outside en and ko (e.g. de has 34 words), so frequent German, French and Spanish
  function words such as `nicht`, `sie`, `est` and `il` are excluded.
- Expanding reviewed closed-class grammar is a runtime/grammar decision for the root
  owners. It is not made here.

**Alternatives** for the root to evaluate on the development gate:
- a bearer threshold, which 1.0.0 used at ≥ 100 and was rejected
- native-label-only matching without `mul`
- larger reviewed grammar inventories

These are not applied here.

## Gaps and limitations

- **Fallback-filled languages.** ko, id, hi and ur reach their 30,000 target only by
  appending fastText entries after the exhausted wordfreq lists. The appended entries
  are surface forms from web-crawl vocabulary:
  - Korean eojeol with particles, and Hindi/Urdu inflected forms
  - English and taxonomy words in Indonesian (e.g. `animalia`, `powered`)
  - fully vowelled Arabic in Urdu
  - names absent from the exclusion sources
  Only generic rules filter them; no entries were invented. The other 13 languages
  target 50,000.
- **Korean entries are MeCab morphemes**, mostly stems and particles, not whitespace
  eojeol. Japanese entries are likewise MeCab units. Both need reviewed morphology.
- **mr/te lists are ranks only, with no counts.** They come from web-crawl vocabulary
  and include inflected forms, loanwords and residual names. Name coverage for mr/te
  is small.
- **Exclusions are exact-label and surface-form only.** Homonyms were not manually
  reviewed. Real names absent from these sources are not excluded. Many common
  open-class words are excluded as name/place homonyms, toward masking.
- **Country aliases include descriptive forms.** Examples: ar `المملكة` ("the
  kingdom") and `القمر` ("the moon"). These are excluded toward masking.
- **ko `한국`.** It is not the Wikidata label "대한민국". It is now excluded through
  the generic Wikidata country-alias source, not added by hand; it was a documented
  source-coverage gap and has no holdout or evaluation origin.
- **ShareAlike:** obligations apply to the derived data files. Common Crawl text
  rights are not addressed beyond the fastText vector licence.
- **Data 1.1.0 network:** about 71 MiB of the 150 MiB allowance, all gzip-transferred:
  - name labels/aliases: 41.4 MiB
  - regional variants: 13.1 MiB
  - an additional id fastText range: 16 MiB
  - plus a few KB of rate-limited or timed-out query responses, which are not used
- **Country labels/aliases are base-language only.** Regional variants were added for
  name items only.
- **Network transferred before 1.1.0:** about 124 MiB of the original 128 MiB allowance (including
  a 77 KB country-label query). Under a separate 64 MiB allowance: 5.8 MiB of
  Wiktionary extracts and a 144 KB country-alias query. The original total includes
  two query results that were later superseded and are not inputs:
  - all given/family-name class labels, 57.8 MiB
  - labels with ≥ 25 users, 5.2 MiB

  No whole 500 MB / 1 GB vector file was fetched.

## Typed POS evidence for all 17 languages (investigated, not downloaded)

Kaikki publishes per-language Wiktionary POS subsets (`pos-{verb,adv,intj}`, gzip
JSONL, extraction 2026-10-30). Measured `Content-Length` in MB, from HTTP HEAD only:

| Lang | verb | adv | intj |
| --- | ---: | ---: | ---: |
| English | 68.8 | 12.9 | 2.9 |
| Spanish | 55.1 | 1.6 | 0.2 |
| Arabic | 46.2 | 0.1 | 0.04 |
| Russian | 36.8 | 0.9 | 0.2 |
| Portuguese | 27.1 | 1.0 | 0.2 |
| French | 25.8 | 1.2 | 0.2 |
| German | 25.0 | 0.8 | 0.2 |
| Chinese | 23.6 | 3.1 | 0.4 |
| Turkish | 17.7 | 0.4 | 0.07 |
| Japanese | 9.9 | 0.6 | 0.2 |
| Hindi | 7.8 | 0.2 | 0.04 |
| Korean | 4.6 (already cached) | 0.3 | 0.07 |
| Indonesian | 1.2 | 0.1 | 0.05 |
| Urdu | 1.2 | 0.08 | 0.02 |
| Bengali | 0.7 | 0.08 | 0.02 |
| Marathi | 0.6 | 0.07 | 0.007 |
| Telugu | 0.4 | 0.05 | 0.006 |

**Totals:** verbs about 352 MB, adverbs about 24 MB, interjections about 5 MB. Together
this exceeds the 150 MiB task allowance. The files are alphabetical, so a byte prefix is
not a frequency-ranked subset.

**Not downloaded.** Per instructions, nothing larger was fetched. Options for the coordinator:
- all adverbs and interjections (about 29 MB) plus verbs only for languages under 10 MB
  (about 33 MB more)
- a separate larger allowance for the big verb files

The selection would mirror the Korean gate: lemma, or lemma with its regular inflection,
among the first 1,000 wordfreq candidates; no gloss shipping. The licence is the same
Wiktionary CC BY-SA 4.0 already verified.

## Reproduce

Raw inputs are not stored in the repository. With the cache directories that hold
the pinned files:

```sh
uv run python scripts/curate_common_vocabulary.py --cache-dir <cache2> --legacy-cache-dir <issue323-cache>
uv run python scripts/curate_common_vocabulary.py --cache-dir <cache2> --legacy-cache-dir <issue323-cache> --check
```

The curator verifies every input SHA-256 and byte size, and the wordfreq version
and file hashes. It refuses mismatches. `--check` rebuilds into a temporary
directory and requires byte-identical output.
