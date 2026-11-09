# Common-vocabulary data sources (issue #323)

Data version **1.3.0**, schema **1**, built 2026-11-09. 1.3.0 stops skipping authored `DOMAIN_WORDS`
(evidence only, like names); 1.2.0 bytes are preserved in `docs/research/issue323-data-1.2.0/`.
Earlier versions are preserved by the root workflow:
- 1.0.0, the first development candidate: `docs/evaluations/issue323-2.7.2/development-candidate-1/`
- 1.1.0, the rejected name-exclusion policy: `docs/evaluations/issue323-2.7.2/rejected-name-exclusions-1.1.0/`
The gateway loads these lists for its public-word policy and morphology handling.
The data generation did not use task, reference or evaluation text, and no entries
were added by hand.

## Files and loader contract

**Location:** `src/secure_gateway/data/common_vocabulary/`

**`<lang>.json.gz`** — one file for each of the 17 languages: en ko es fr pt de id tr ru hi mr bn ur te ar zh ja.
- Gzip header: no file name, `mtime` 0, OS byte 255.
- Content: canonical UTF-8 JSON — sorted keys, no spaces, a single trailing LF.
- Keys:
  - `schema_version` = 1
  - `data_version` = "1.3.0"
  - `language`
  - `words`: sorted, unique, NFC + casefold
  - `name_exclusions`: sorted exact forms. Since 1.2.0 these are only name/place-attested
    **fallback lexical candidates outside** `words` and `predicate_lemmas`, not a veto and not
    proof of privacy. The field name is kept for loader compatibility.
  - `source_ids`
  - `predicate_lemmas`: **ko only**, optional, typed `{"verb": [...], "adjective": [...]}`

**`manifest.json`** (pinned LF):
- the generator hash and parameters
- every input hash and origin
- licences
- name-evidence statistics
- per language:
  - file SHA-256 and bytes
  - counts and coverage status
  - per-source exclusion counts
  - processing statistics
  - name-attested word counts by source and fallback-candidate counts

**`NOTICE.md`:** the licence and attribution notice that must travel with the data.

Runtime policy preserves public words and common names. Forced terms, existing
private mappings, and recognized sensitive formats retain precedence. Name evidence
is not itself a veto; unknown ordinary-looking prose can remain unmasked. A private
homonym or unregistered name therefore needs an explicit private rule or mapping.
See [the policy and validation limits](research/issue323-policy-validation.md).

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
| all | Authored `NAME_WORDS`, `ENGLISH_NAMES`, `DOMAIN_WORDS` (attestation only; public words can take precedence) | Apache-2.0 | Module hashes in the manifest |
| ko `predicate_lemmas` | English Wiktionary Korean verb/adjective entries, extracted with wiktextract (commit `19f9a30`, extraction 2026-10-30 of the 2026-10-01 dump) and distributed by kaikki.org | **CC BY-SA 4.0** (Wiktionary text is dual-licensed CC BY-SA 4.0 and GFDL per `Wiktionary:Copyrights`) | `kaikki_ko_verb.jsonl.gz` (4,571,801 B), `kaikki_ko_adj.jsonl.gz` (1,482,065 B); SHA-256, Last-Modified and ETag in the manifest |

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
3. **Authored domain words** (`DOMAIN_WORDS`) are counted as `domain_attested_words` evidence and
   are **not** removed (since 1.3.0; 1.2.0 skipped them).
4. **Name/place evidence (general-word preservation, 1.2.0).**
   - A candidate equal to a name or place label is **kept** as an ordinary word. The
     sources are Wikidata names, countries, GeoNames, jieba tags and authored
     `NAME_WORDS`/`ENGLISH_NAMES`.
   - The match is counted in the manifest (`name_attested_words`, by source).
   - Labels are never split into tokens.
   - **Country aliases** skip abbreviations: a form that is all uppercase (DE, USA,
     RF), one character long (CJK `中`, `米`), or ASCII and at most 3 characters
     (`in`, `tv`). This is a generic code filter; full labels are never filtered.
5. **Keep** the first 50,000 candidates, or all candidates if the cached sources end
   first, and write them sorted.
6. **Fallback name candidates.** Continue scanning the next 50,000 ranked candidates
   (`evidence_window`). Their name/place-attested forms, plus authored names not
   selected, become `name_exclusions`.
   - These are disjoint from `words` and from the Korean predicates by construction.
   - The Korean name + particle rule of 1.1.0 is removed.

### Policy history (data review)

| Version | Name/place source | Outcome |
| --- | --- | --- |
| 1 | Raw Wikidata name-class labels, no usage threshold | Matched almost every function word (the, de, 是) |
| 2 | Names used ≥ 25 times; GeoNames ≥ 15,000 | Still excluded `peace`, `normal`, `husband` |
| 3 | Names used ≥ 100 times; GeoNames ≥ 100,000 | Kept every name/place match among the first 1,000 candidates as ordinary |
| 1.0.0 | Names used ≥ 100 times; GeoNames ≥ 100,000 | Exemption limited to authored closed-class words; country labels, aliases and local alternate names added. The first development privacy gate failed. |
| 1.1.0 (rejected) | Every attested name item's labels and aliases (≥ 1 user), with regional variants; GeoNames ≥ 15,000 | About half of the top 1,000 en/de words were excluded as homonyms. Rejected by the user policy update. |
| 1.2.0 | Same evidence as 1.1.0 | **General-word preservation:** name/place evidence is metadata and never removes a frequency word. `name_exclusions` holds only attested forms outside the selection. |
| **1.3.0 (current)** | Same evidence as 1.1.0 | As 1.2.0, and static `DOMAIN_WORDS` no longer remove ordinary frequency words (4–12 per language). Runtime policy: `docs/research/issue323-public-policy.md`. |

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
- the authored name/domain modules

Data 1.2.0 no longer reads the closed-class grammar modules, so their fingerprints are
no longer recorded.

Git stores these files with LF, but a Windows checkout may contain CRLF. The recorded
values equal the SHA-256 of the committed Git blobs.

Downloaded and binary inputs, and the generated `.json.gz` files, keep exact raw-byte
SHA-256 and size checks.

## Results (data 1.2.0; 1.3.0 differs only by restored domain-list words, see manifest)

| Lang | Source(s) | Words (1.1.0 → 1.2.0) | wordfreq / fastText words | Name-attested words kept | Fallback name candidates (`name_exclusions`, 1.1.0 → 1.2.0) | Coverage | `.json.gz` bytes |
| --- | --- | --- | --- | ---: | --- | --- | ---: |
| en | wordfreq | 50,000 → 50,000 | 50,000 / 0 | 17,406 | 28,017 → 19,413 | target_met | 202,151 |
| ko | wordfreq + fastText | 30,000 → 42,566 | 29,913 / 12,653 | 5,313 | 5,777 → 37 | within_target_range (source exhausted) | 136,363 |
| es | wordfreq | 50,000 → 50,000 | 50,000 / 0 | 12,133 | 15,837 → 12,118 | target_met | 175,834 |
| fr | wordfreq | 50,000 → 50,000 | 50,000 / 0 | 13,828 | 19,729 → 15,900 | target_met | 187,658 |
| pt | wordfreq | 50,000 → 50,000 | 50,000 / 0 | 12,932 | 17,478 → 12,926 | target_met | 180,013 |
| de | wordfreq | 50,000 → 50,000 | 50,000 / 0 | 12,480 | 15,750 → 10,125 | target_met | 185,121 |
| id | wordfreq + fastText | 30,000 → 50,000 | 30,808 / 19,192 | 15,046 | 12,918 → 1,242 | target_met | 156,014 |
| tr | wordfreq | 50,000 → 50,000 | 50,000 / 0 | 7,952 | 9,063 → 1,551 | target_met | 144,587 |
| ru | wordfreq | 50,000 → 50,000 | 50,000 / 0 | 5,001 | 5,580 → 5,078 | target_met | 183,561 |
| hi | wordfreq + fastText | 30,000 → 42,504 | 26,328 / 16,176 | 2,852 | 2,636 → 1 | within_target_range (source exhausted) | 159,412 |
| mr | fastText | 50,000 → 50,000 | 0 / 50,000 | 1,335 | 1,351 → 53 | target_met | 188,446 |
| bn | wordfreq | 50,000 → 50,000 | 50,000 / 0 | 3,230 | 3,410 → 2,270 | target_met | 187,942 |
| ur | wordfreq + fastText | 30,000 → 49,151 | 23,031 / 26,120 | 3,010 | 2,284 → 3 | within_target_range (source exhausted) | 155,602 |
| te | fastText | 50,000 → 50,000 | 0 / 50,000 | 973 | 980 → 26 | target_met | 196,558 |
| ar | wordfreq | 50,000 → 50,000 | 50,000 / 0 | 5,137 | 5,553 → 3,598 | target_met | 162,719 |
| zh | wordfreq | 50,000 → 50,000 | 50,000 / 0 | 11,126 | 15,355 → 13,996 | target_met | 227,548 |
| ja | wordfreq | 50,000 → 50,000 | 50,000 / 0 | 11,764 | 15,292 → 11,135 | target_met | 206,076 |

Korean typed predicates: 141 verbs and 40 adjectives. This compares with 136 / 39 in 1.1.0, where
name exclusion had blocked some, and 139 / 40 in 1.0.0.

**Size:** the 17 data files total about 3.04 MB of gzip, plus a 49 KB manifest.
Every set is within the loader limits of 4 MiB compressed, 16 MiB JSON and 100,000 entries.
A curator run still loads all name evidence (about 10M labels) and peaks at about 1.4 GiB.

## Data 1.1.0 trade-off (measured, rejected policy)

Kept as evidence for why 1.2.0 changed policy.

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
- **Policy delta in 1.2.0:**
  - Widely used names and places that are frequent words (e.g. `john`, `london`, `berlin`,
    `서울`, `王`) are ordinary words.
  - A private person or place with such a name is protected only by explicit or
    private rules, prior mappings and the runtime policy owned by root, not by this data.
  - Name evidence beyond the selection is not exhaustive. It covers only the ranked
    candidates within the evidence window and authored names.
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
