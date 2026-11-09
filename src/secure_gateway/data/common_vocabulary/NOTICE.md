# Common-vocabulary data notice

The files in this directory are **data, not code**. They are licensed separately
from the Apache-2.0 SecureGateway source code. Redistribution must keep this notice
with the files.

## Ordinary-word lists (`words`)

**`en, ko, es, fr, pt, de, id, tr, ru, hi, bn, ur, ar, zh, ja`** — derived from
the frequency lists packaged in **wordfreq 3.1.1** (Robyn Speer and contributors,
<https://github.com/rspeer/wordfreq>).
- Licence: **Creative Commons Attribution-ShareAlike 4.0 International**
  (<https://creativecommons.org/licenses/by-sa/4.0/>).
- Credits from wordfreq's licence notice:
  - Google Books Ngrams (<http://books.google.com/ngrams>)
  - SUBTLEX word lists by Marc Brysbaert et al. (credit required; SUBTLEX is freely available data)
  - OPUS OpenSubtitles 2018 / OpenSubtitles (<http://www.opensubtitles.org/>)
  - the Leeds Internet Corpus
  - Wikipedia
  - ParaCrawl
  - and the other sources credited in the wordfreq README

**`mr, te`** — derived from the vocabulary of the fastText Common Crawl word
vectors `cc.mr.300.vec.gz` and `cc.te.300.vec.gz`
(<https://fasttext.cc/docs/en/crawl-vectors.html>).
- Licence: **Creative Commons Attribution-ShareAlike 3.0 Unported**
  (<https://creativecommons.org/licenses/by-sa/3.0/>).
- Cite: E. Grave, P. Bojanowski, P. Gupta, A. Joulin, T. Mikolov,
  *Learning Word Vectors for 157 Languages*, LREC 2018.
- Only the frequency-ordered words are used. No vectors are included.

**`ko, id, hi, ur` (mixed sources)** — the wordfreq lists for these languages run out
below 30,000 entries. After every wordfreq entry, the lists continue with the
frequency-ordered fastText vocabulary of the same language (`cc.ko/id/hi/ur.300.vec.gz`,
CC BY-SA 3.0, credits as above).
- These four files are adaptations licensed under **CC BY-SA 4.0**. CC BY-SA 3.0
  Unported Section 4(b)(ii) permits distributing an Adaptation under a later version
  of the license with the same License Elements
  (<https://creativecommons.org/licenses/by-sa/3.0/legalcode>).
- Both wordfreq and fastText are credited.
- `manifest.json` records the number of words from each source.

**Modifications** (all lists): the ranked entries were filtered by Unicode
letter/mark rules, normalised to NFC and case-folded, de-duplicated, and stripped of
listed name/place and domain forms. The first 50,000 remaining entries are kept,
sorted by code point. These modified lists are shared under the same licence as
their source.

## Korean predicate lemmas (`ko.json.gz` → `predicate_lemmas`)

Verb and adjective dictionary forms come from English Wiktionary entries.
- Licence: **Creative Commons Attribution-ShareAlike 4.0 International** (Wiktionary
  text is dual-licensed CC BY-SA 4.0 and GFDL).
- Credit: Wiktionary contributors, <https://en.wiktionary.org/wiki/Wiktionary:Copyrights>.
- Extraction: wiktextract (Tatu Ylonen), distributed at kaikki.org. Snapshot
  2026-10-30 of the 2026-10-01 dump, wiktextract commit 19f9a30.

Only lemma forms are kept; no glosses, examples or etymologies. A lemma is kept only
when it or its bare stem is among the first 1,000 Korean frequency candidates.

## Name/place evidence and fallback candidates (`name_exclusions`)

Exact whole forms matched against these sources. In data 1.2.0 this evidence never
removes a frequency word. `name_exclusions` holds only attested forms **outside**
the selected words and predicates. They are fallback lexical candidates, not proof
that an occurrence is private.

| Source | Licence | Attribution / link |
| --- | --- | --- |
| Wikidata labels and aliases of every attested given-name (P735) and family-name (P734) item, plus country labels/aliases | CC0 1.0 | Wikidata contributors, <https://www.wikidata.org/wiki/Wikidata:Licensing> |
| GeoNames city (population ≥ 15,000) and country names; India alternate names for mr/te | CC BY 4.0 | GeoNames, <https://www.geonames.org/> |
| jieba 0.42.1 dictionary (zh multi-character person/place/organisation tags) | MIT | Sun Junyi and contributors, <https://github.com/fxsjy/jieba> |
| SecureGateway authored name lists (evidence) and domain words (still not selected) | Apache-2.0 | SecureGateway contributors |

`manifest.json` records every input hash, the generator hash, licences and per-language statistics.
