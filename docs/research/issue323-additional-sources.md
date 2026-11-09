# Issue #323: additional source evidence (mr/te gaps, Korean predicate roots)

Status: **read-only evidence collection. No vocabulary was implemented, adopted, or extracted into the repository.** Collected 2026-11-09 against worktree commit `a3f37d4`. This complements the root workspace's `docs/research/issue323-sources.md` and `issue323-source-manifest.json`; those files were read and not modified. It covers only the gaps they leave open (§9 there): mr/te frequency-list licensing and scale, mr/te proper-name exclusion counts, Leipzig, and the mecab-ko-dic Sejong provenance caveat. This is not legal advice.

Machine-readable record, including every URL, revision, byte count and SHA-256: [`issue323-additional-source-manifest.json`](issue323-additional-source-manifest.json).

## 1. Method and boundaries

- Only generic corpus, licence and metadata queries were run. No word, name or sentence from any authored evaluation task was used. No evaluation output or engine code was opened.
- Raw downloads are cached **outside the repository**, under the scratchpad path recorded in the manifest. The repository holds only counts, hashes, URLs and paraphrased licence terms. No corpus sentences, glosses, word lists or name lists are stored here.
- Network use was read-only: **62.0 MiB** transferred against a 100 MiB limit. That total counts every response body written to the cache, including HTTP Range probes and error pages.
- Each point below is labelled as one of:
  - **[verified]**: measured from bytes I downloaded and hashed.
  - **[publisher]**: the rights holder's or distributor's own licence statement, quoted or paraphrased.
  - **[unresolved]**: an upstream right or fact I could not settle from a primary source.

## 2. Large mr/te frequency sources

| Source | Licence evidence | Scale (mr / te) | Status |
| --- | --- | --- | --- |
| **IndicCorp v2** (`ai4bharat/IndicCorpV2`, rev `2d7285e6…`, 2025-03-10) | **[publisher]** The dataset card and the IndicBERT README (commit `48904419…`, LICENSE = MIT) both say datasets "will be released under a CC-0 license" (future tense). **[verified]** The Hugging Face revision has no machine-readable licence tag. | **[verified]** `data/mr.txt` 14,553,660,884 B (LFS sha256 `0b60f389…`); `data/te.txt` 15,760,603,733 B (`60693a4f…`); ungated | **[unresolved]** The CC0 statement is prose only and promissory; crawled source-text rights are not addressed. Full counts not computed (too large). |
| **fastText Common Crawl vectors** (`cc.mr.300.vec.gz`, `cc.te.300.vec.gz`, 2019-01-18) | **[publisher]** "distributed under the Creative Commons Attribution-Share-Alike License 3.0"; the text format lists words "sorted by frequency in descending order"; trained on Common Crawl and Wikipedia; citation requested | **[verified]** header vocabularies 845,805 (mr) and 1,878,288 (te); files 504.6 MB / 1,117.0 MB | Usable **rank** list (no counts) under BY-SA 3.0. Top 50k words ≈ 31 MiB of gzip each (measured). |
| **CC-100** (`data.statmt.org/cc-100/`) | **[publisher]** "No claims of intellectual property are made on the work of preparation of the corpus." | **[verified]** `mr.txt.xz` 349,785,844 B; `te.txt.xz` 561,820,568 B (HTTP headers) | **[unresolved]** Disclaims preparation only; no licence for the web text. Not downloaded. |
| **Leipzig Corpora Collection** | Primary usage and download pages return a JavaScript bot challenge, and the downloads index returns HTTP 403 | — | **[unresolved]** Still unverified (same as the root review). |
| **IlyaSemenov/wikipedia-word-frequency** (commit `d11c4fab…`, MIT) | n/a | **[verified]** Results exist only for af ar ceb de en es fa fr it ja nl pl pt ru sv sw uk vi zh | Not usable: no mr/te/hi/ur/ko. |

### 2.1 Verified probe measurements (counts only)

Tokens are maximal runs of Devanagari or Telugu script after NFC normalisation.

| Probe | mr | te |
| --- | ---: | ---: |
| IndicCorp v2, first 12 MiB: documents (non-empty lines, blank-line separated) | 16,654 | 16,535 |
| … script tokens | 680,818 | 596,254 |
| … distinct types | 97,891 | 99,534 |
| … types with freq ≥ 2 / ≥ 5 / ≥ 10 / ≥ 50 | 38,881 / 15,509 / 8,152 / 1,844 | 38,399 / 15,519 / 8,219 / 1,694 |
| fastText, first 12 MiB (gzip): ranked entries | 19,147 | 19,271 |
| … entries consisting only of the language's script | 16,444 | 15,608 |
| … of those, also seen ≥ 2 times in the IndicCorp probe | 13,818 | 12,633 |

The IndicCorp slice is about 0.09% of each file and comes from the start of the file, not a random sample. Its counts show the format and density only, not corpus-wide frequencies. Even so, a slice this small already yields about 38k repeated types, so a full IndicCorp count would plausibly exceed 50k types at a conservative threshold. That is an inference, not a measurement.

## 3. mr/te proper-name exclusion sources

| Source | Licence | mr | te | Notes |
| --- | --- | ---: | ---: | --- |
| Wikidata given names (Q202444 + male/female/unisex subclasses), items with a label in the language **[verified, QLever]** | CC0 | 403 items / 374 labels | 206 / 197 | QLever index from the 2026-08-10 `latest-all.ttl` dump, updated live |
| Wikidata family names (Q101352) | CC0 | 215 / 214 | 597 / 593 | |
| Wikidata humans (Q5) with a label | CC0 | 28,297 / 28,066 | 49,384 / 48,975 | Full person names, not name tokens |
| Wikidata items in India with coordinates | CC0 | 8,020 / 7,673 | 33,387 / 30,082 | Places plus other located items |
| Distinct script tokens: given+family names / person labels / India places / union | CC0 | 530 / 24,022 / 6,127 / 29,515 | 677 / 37,533 / 26,319 / 61,501 | Computed from the cached label lists |
| GeoNames `alternatenames/IN.zip` (2026-11-08) non-historic names **[verified]** | CC BY 4.0 (readme lines 6–7) | 685 names / 689 places | 579 / 589 | Small for mr/te; Wikidata is the larger place source |
| Wiktionary `name` POS (root review) | CC BY-SA | 631 senses | 1,944 senses | Not re-measured here |

The public `query.wikidata.org` endpoint timed out on all four of these counts. The QLever endpoint, which serves the same CC0 data, completed them.

**Overlap with frequent words [verified].** Of the IndicCorp probe types with frequency ≥ 10:

- **Whole person-label tokens:** about 14–17% of those types also occur as tokens of whole person labels (mr 1,118 / 8,152; te 1,363 / 8,219).
- **Place-label tokens:** about 10–14% also occur as place-label tokens.
- **Given/family-name classes only:** about 1.3% (mr 113, te 102).
- **fastText top slice:** the same pattern holds (person-label overlap mr 2,443, te 2,625; given/family 212 / 220).

**Consequence:** tokenising whole Wikidata person or place labels sweeps in titles and ordinary nouns, so the resulting "name list" would over-remove common vocabulary. Exclusion should use the given/family-name classes, plus reviewed place lists, and keep the existing rule that homonyms of ordinary words are resolved toward masking with a recorded reason. Overlap counts are by surface form only; homonyms were not manually reviewed and no tokens are listed here.

## 4. Korean predicate roots and the Sejong caveat

### 4.1 mecab-ko-dic (Bitbucket `eunjeon/mecab-ko-dic`, commit `f0e76b67…`, 2025-07-03)

- **[verified]** `COPYING` is the Apache License 2.0.
- **[verified]** `seed/VV.csv` has 7,331 verb entries and `seed/VA.csv` has 2,360 adjective entries (distinct surfaces; POS column VV/VA).
- **[publisher]** The provenance statements conflict:
  - **Repository description:** corpus training **and the dictionary list all** use 21st-Century Sejong Project outputs (모두).
  - **Root `README.md`:** training and **part** of the dictionary list do (일부); 50 sentences were taken from every modern Sejong corpus (23,615 sentences).
  - **`seed/README.md`:** **all** (모두). `Wikipedia.csv` nouns were extracted from Korean Wikipedia to supplement proper names.
- **[verified]** `http://www.sejong.or.kr/` now serves a domain-parking page.
- **[publisher]** NIKL notice (kli.korean.go.kr, 2021-07-01): web distribution of Sejong outputs ended on 2021-06-30. The outputs are now distributed on DVD after a signed application and agreement.
- **[publisher]** The NIKL agreement form (attachment `file_id=711`, zip sha256 `413a6933723813185ef601747096ca7c42b71bdbabe779aaaf02c2a12caff6a4`; HWP member hashes in the manifest), paraphrased:
  - **Art. 1:** the data is provided for Korean information-processing and Korean-language research.
  - **Art. 2:** the recipient must not use it for commercial purposes beyond the original research-and-development use.
  - **Art. 3:** the recipient bears all civil and criminal liability for any leak.
  - **Art. 4:** derived results must state the kinds and sources of the data used.

  The NIKL portal's terms of service separately bar copying, distributing, sublicensing or commercial use of portal assets without explicit approval.
- **[unresolved]** Several questions remain open:
  - The terms that applied when mecab-ko-dic took the data (web distribution, about 2013–2018) were not found.
  - It is unclear whether a recipient-side contract binds downstream users of an Apache-licensed derivative.
  - It is unclear whether lexical entry lists inherit any restriction.

**Conclusion:** the provenance caveat is now **confirmed rather than resolved**. Under current primary terms, Sejong outputs are research-only and non-commercial, and mecab-ko-dic's own description says its dictionary list comes from them. Under this task's no-NC rule, mecab-ko-dic VV/VA/NNG entries should be treated as unresolved upstream rights. They are **not adoptable without legal review**, and its Apache-2.0 `COPYING` does not settle that.

### 4.2 open-korean-text (GitHub, commit `74cc4ae7…`)

- **[verified]** The LICENSE file and README are Apache-2.0. The project is the official fork of `twitter/twitter-korean-text`, which is also Apache-2.0.
- **[verified]** `verb.txt` has 3,242 entries, `adjective.txt` 2,518 and `eomi.txt` (endings) 1,236. The dictionaries were last updated in commit `4790277c` (2017-04-10, "Updated dictionaries to 1.3.1").
- **[unresolved]** Neither README documents where the entries came from, so the lists are not proven Sejong-free. There is no frequency information.

They could serve as a cleaner-licensed root inventory or a test oracle, but only after provenance is confirmed with the maintainers.

## 5. What changes relative to the root review

1. **mr/te frequency:** fastText cc vectors are a newly verified, primary-licensed (CC BY-SA 3.0), frequency-ranked mr/te vocabulary. Taking the top 50k needs only about 31 MiB per language, at build time. IndicCorp v2 remains the only source with counts, but its CC0 statement is still prose-only. Neither should be adopted before #324, and either needs the name filtering in §3.
2. **Names:** mr/te exclusion counts are now verified. Use the given/family-name classes (530 / 677 tokens). Do not use raw person/place label tokens, which overlap 10–17% of frequent words.
3. **Korean:** the mecab-ko-dic Sejong caveat is substantiated by a primary NIKL agreement (research-only, non-commercial). The fallback, open-korean-text, is Apache-2.0 but has undocumented provenance.
4. **Leipzig** remains unverified, and CC-100 has no licence for its text.

## 6. Remaining unresolved points

- IndicCorp v2: no machine-readable licence, future-tense CC0, and crawled-text rights not addressed. Full-file counts not computed.
- fastText: ShareAlike obligations would apply to any derived list. Common Crawl text rights are not addressed beyond the vector licence. The list gives ranks only.
- The NIKL/Sejong terms in force about 2013–2018, and whether they reach mecab-ko-dic's downstream users.
- open-korean-text dictionary provenance.
- Leipzig licence (bot challenge or HTTP 403); CC-100 text rights.
- Manual review of name/ordinary-word homonyms in mr/te (counts are surface-form only).
