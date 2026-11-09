# Issue #323 — vocabulary/morphology source and license review

Status: **read-only preparation, no adoption decision.** Collected 2026-11-09 against
worktree commit `a3f37d4` (package 2.6.1). This document records source evidence for
a later #323 implementation that must wait for the #324 evaluation-reliability gate.
It is not legal advice. Nothing here changes production code, tests, corpora,
dictionaries or the package version.

Machine-readable record: [`issue323-source-manifest.json`](issue323-source-manifest.json).

## 1. Method and boundaries

- Inspected the vocabulary interfaces only: `src/secure_gateway/gateway_vocabulary.py`,
  `gateway_indic_vocabulary.py` (header and structure), `gateway_name_vocabulary.py`
  (header), `engine/grammar_ko.py` (`decompose_token`), the vocabulary call site in
  `gateway.py` (`_mask_prose`) and `docs/THIRD_PARTY_DATA.md`/`DICTIONARY_SOURCES.md`.
- **Not opened:** `evaluation_corpus.json`, test fixtures, evaluation answers,
  holdout corpora, prior example paragraphs and the other worker's worktree. No list
  in this document was derived from or checked against example sentences.
- Installed-package evidence was read from the existing project environment
  (`wordfreq 3.1.1`, `jieba 0.42.1`, `tinysegmenter 0.4`). Upstream licensing was
  checked from primary repositories/licence pages. Where a primary page could not be
  retrieved, the point is listed as unverified (§9).
- Network use was read-only retrieval of licence pages, READMEs, GitHub/Hugging Face
  metadata and two line-count probes. One Wikidata SPARQL count was attempted and
  timed out on the public endpoint; no result from it is used.

## 2. Current implementation: fit and gaps

| Piece | Behaviour today | Consequence for #323 |
| --- | --- | --- |
| `ordinary_words(lang)` | Union of small authored lists + wordfreq buckets `bins[:cutoff+1]`; cutoff **550 → Zipf ≥ 3.5** for en/es/fr/pt/de/id/tr/ru, **500 → Zipf ≥ 4.0** for others. Alphabetic filter, NFC + casefold. `lru_cache(17)`. Raises if a language has neither wordfreq nor Indic lists. | Single exact-form set. A 30k–50k target is a cutoff change for languages where wordfreq is large, but not for mr/te (absent) or ko/id/hi/ur (small lists end near 23k–31k). |
| `reviewed_inflections` | mr/te only: strips a fixed suffix list and keeps the token if the remainder is in authored Indic/household roots minus names/domain words. | Correct shape (known-root gating). Root inventory is the bottleneck, not the suffix rule. |
| Korean (`decompose_token`) | Strips josa, plural 들 and copula endings; **no predicate conjugation**. Gateway then checks `stem in general`. | wordfreq ko entries are MeCab morphemes (e.g. bare stems such as `하`, `있`, `물려받`), so verb/adjective eojeol cannot reach a list entry without a reviewed conjugation analyser. Single-syllable morphemes in the list are a collision hazard. |
| `domain_terms` (ar) | Arabic proclitic stripping (`وال بال لل ال و ف ب ل ك`) used only to **protect** private/domain words. | Same prefix inventory could be reused for ordinary-word lookup only when the remainder is a reviewed root; never for disclosure of an unknown remainder. |
| Names | `NAME_WORDS` (authored starter given names), `ENGLISH_NAMES`, `DOMAIN_WORDS`; these remove items from disclosure. | Exclusion lists are tiny relative to a 30k–50k vocabulary; larger, source-backed name/place exclusion is required before raising cutoffs (§6). |

Observation for coordinator review (not verified against fixtures, which were not
opened): `_GENERAL_WORDS` and `ADDITIONAL_WORDS` in `gateway_vocabulary.py` are
written as sentence-like strings per language. If they were authored from reported
example prompts, they are the kind of fitted vocabulary this task must not extend.
A source-backed #323 list should be able to replace them, and their provenance should
be checked during #323.

Current measured runtime cost (local, Python 3.11, this machine): decoding one wordfreq
file costs **0.3–0.7 s and a 30–80 MiB transient peak** today regardless of cutoff,
because `read_cBpack` decodes the whole file. The retained set grows from ≈0.9 MiB
(de, Zipf ≥ 4.0, 7.2k) to ≈4.3 MiB (de, Zipf ≥ 3.0, 39.9k) and ≈9.0 MiB (de, Zipf ≥ 2.5,
85k); ru Zipf ≥ 3.0 is 62k words / 7.3 MiB. Raising the cutoff therefore adds memory,
not startup download or network cost.

## 3. Coverage available from what is already installed (wordfreq 3.1.1)

Counts are alphabetic entries (same filter as `ordinary_words`) at or above each Zipf
value, computed from the installed files; file hashes are in the manifest.

| Lang | File | ≥4.0 (≈today for most) | ≥3.5 | ≥3.0 | ≥2.5 | 30k reached at Zipf | 50k at Zipf | Verdict for 30k–50k |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| en | large | 7,160 | 15,003 | 28,856 | 52,656 | 2.96 | 2.54 | Available |
| es | large | 7,230 | 16,691 | 35,155 | 66,903 | 3.11 | 2.73 | Available |
| fr | large | 6,753 | 15,476 | 31,593 | 58,560 | 3.03 | 2.63 | Available |
| pt | large | 7,463 | 16,855 | 33,498 | 58,431 | 3.08 | 2.64 | Available |
| de | large | 7,120 | 17,416 | 39,499 | 84,234 | 3.17 | 2.84 | Available as surface forms; compounds still need decomposition |
| ru | large | 9,824 | 26,489 | 61,947 | 130,647 | 3.43 | 3.13 | Available |
| ar | large | 11,285 | 27,906 | 57,157 | 108,192 | 3.45 | 3.10 | Available as clitic-attached surface forms |
| zh | large | 8,556 | 19,149 | 38,872 | 71,309 | 3.19 | 2.80 | Available; ≈12% name/place/org tagged (§6) |
| ja | large | 7,228 | 15,769 | 30,487 | 53,431 | 3.01 | 2.56 | Available as MeCab morphemes, not surface phrases |
| bn | large | 9,462 | 19,419 | 34,528 | 58,038 | 3.12 | 2.65 | Available |
| tr | small | 10,598 | 27,681 | 63,038 (all) | — | 3.45 | 3.15 | Available (small list ends at Zipf 3.0) |
| id | small | 7,594 | 16,087 | 30,814 (all) | — | 3.03 | — | **30k only, no 50k** |
| ko | small | 6,485 | 14,555 | 29,925 (all) | — | — | — | **Gap: <30k morphemes, not eojeol** |
| hi | small | 6,748 | 14,529 | 26,349 (all) | — | — | — | **Gap: <30k** |
| ur | small | 6,763 | 13,002 | 23,037 (all) | — | — | — | **Gap: <30k** |
| mr | — | — | — | — | — | — | — | **Gap: not in wordfreq** |
| te | — | — | — | — | — | — | — | **Gap: not in wordfreq** |

Mid-rank samples confirm contamination that a cutoff alone does not remove: the ko
list contains given/full names and place names (e.g. `이민호`, `원주시`, `로렌스`),
hi contains given names and profanity, ar contains transliterated given names. These
are illustrations from the installed list, not counts.

## 4. Candidate sources

Licence columns are separated into **code** and **data**. "Redistributable with this
Apache-2.0 repository" means: as a *separate data file* carrying its own notice,
which is how `DICTIONARY_SOURCES.md` already treats CC BY 4.0 / CC0 inputs. ShareAlike
then applies to that data file and its adaptations, not to the Apache code, provided
the data is kept as a distinct file rather than embedded in `.py` source.

### 4.1 Ranked candidates (usable)

| # | Source | Primary URL / revision | Code licence | Data licence & constraints | Derived list redistributable? | Langs (of 17) & size | Frequency? | Morph./norm. scope | Name contamination | Cost |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **wordfreq** (installed) | github.com/rspeer/wordfreq, PyPI 3.1.1 (pinned in `pyproject.toml`) | Apache-2.0 (`LICENSE.txt` in dist-info) | **CC BY-SA 4.0** for data; plus Google Books Ngrams acknowledgement, SUBTLEX credit condition, OpenSubtitles attribution (per installed METADATA “License”). Upstream README: data a snapshot through ≈2021, “unlikely to be updated again”. | Yes as a separate BY-SA data file with credits; current approach (read packaged file at runtime, no extracted copy) avoids redistribution entirely. | 15/17 (no mr, te); sizes in §3 | Yes (centibel bins → Zipf/rank) | Casefolded surface tokens from wordfreq’s own tokenizer; ko/ja via MeCab morphemes; no lemmas | Unfiltered; names/places/brands present | Already installed; 0 new download; +4–9 MiB/lang at Zipf ≥ 3.0 |
| 2 | **jieba `dict.txt`** (installed) | github.com/fxsjy/jieba, PyPI 0.42.1; sha256 `7197c321…12a8` (identical to `wordfreq/data/jieba_zh_orig.txt`) | MIT | MIT (same package). Upstream does not document corpus provenance (wordfreq README also notes unknown provenance). | Yes (MIT notice) | zh: 349,046 entries | Yes (count column) | Word + POS (ICTCLAS-style) | **Useful as exclusion**: `nr` 72,842, `nrt` 5,941, `nrfg` 484, `ns` 17,706, `nt` 4,713, `nz` 10,441 | Installed; 0 new cost |
| 3 | **Wikidata** given/family-name and settlement labels | wikidata.org, Wikidata:Licensing; classes `Q202444` given name, `Q101352` family name, `Q486972` human settlement | n/a | **CC0** for structured main-namespace data (already relied on in `DICTIONARY_SOURCES.md`) | Yes (no conditions; attribution kept voluntarily) | All 17 languages have labels; per-language counts **unverified** (SPARQL with `P279*` timed out) | No | Labels only | This *is* the exclusion source | Offline build-time query/dump only; no runtime network |
| 4 | **GeoNames** `cities1000`/`cities15000` + `alternateNamesV2` | download.geonames.org/export/dump/readme.txt | n/a | **CC BY 4.0** (readme licence line) | Yes with attribution | Multilingual alternate names keyed by ISO 639 (`isolanguage`) | Population (not word frequency) | Names; flags preferred/short/colloquial/historic | Exclusion source for places | Offline build; ≈130k (cities1000) / ≈25k (cities15000) records |
| 5 | **mecab-ko-dic** | bitbucket.org/eunjeon/mecab-ko-dic (COPYING = Apache-2.0); PyPI repackage `mecab-ko-dic 1.0.0` (LuminosoInsight) | Apache-2.0 | Apache-2.0 per COPYING/README. README states training and **part of the entry list use 21st-Century Sejong project outputs** — upstream Sejong redistribution terms not verified (§9). | Probably (Apache notice) but provenance caveat | ko; POS-tagged morpheme lexicon (NNG/NNP/VV/VA…) | No (cost weights only) | Morpheme roots with POS; **NNP separates proper nouns** | NNP usable for exclusion | Build-time only; do not add MeCab runtime |
| 6 | **IndicCorp v2** (AI4Bharat) | huggingface.co/datasets/ai4bharat/IndicCorpV2, revision `2d7285e6ce14fdb3fb2449c9f89427b9f582ac3f` (2025-03-10); github.com/AI4Bharat/IndicBERT | MIT (stated for code/models) | Card text: datasets “will be released under a **CC-0** license”; machine-readable licence tag absent; crawled source-text rights not addressed | Frequency counts (facts) derived offline are lower-risk than text; still flag | mr ≈27.8M rows, te ≈31M rows; also hi, bn, ur | Derivable by counting | Raw text; needs our tokenizer | Raw web text; must filter names | **Large offline download (GBs)**; build-time only, never runtime |
| 7 | **Wiktionary via kaikki.org/wiktextract** | kaikki.org/dictionary/rawdata.html — extraction 2026-10-30 from enwiktionary dump 2026-10-01 | wiktextract: “other” (not checked) | Wiktionary text **CC BY-SA 4.0** (+GFDL legacy dual licence; Wiktionary:Copyrights page self-marked outdated) | Headword/POS/inflection-form lists: yes as BY-SA data; **never copy glosses** | mr 5,351 forms (n 4,919 / v 1,025 / **proper 631** senses); te 21,818 forms (n 19,638 / v 3,292 / **proper 1,944**); per-language files deprecated on kaikki | No | POS + inflection tables (patchy) | `name` POS → exclusion | Offline; mr 27.6 MB, te 31.3 MB JSONL |
| 8 | **UniMorph** | github.com/unimorph/{tel,kor,ara,deu,spa}; tel commit `551f60f5…`; READMEs | n/a | **CC BY-SA 3.0** stated in ara/deu/spa READMEs; tel/kor READMEs state no licence (project-level licence assumed, unverified) | Yes as BY-SA data (where licence stated) | **No mr repo**; tel only **128 lemmas**; kor 2,686 predicate lemmas/241k forms (Wiktionary-derived); deu, spa large | No | Lemma→form paradigms | Low | Offline; MBs |
| 9 | **Universal Dependencies** (BY / BY-SA treebanks only) | github.com/UniversalDependencies; Marathi-UFAL commit `c02a0824…` | n/a | Marathi-UFAL **CC BY-SA 4.0**; Telugu-MTG **CC BY-SA 4.0**; Korean-Kaist/GSD **CC BY-SA 4.0**; German-GSD **CC BY-SA 4.0**; Spanish-AnCora **CC BY 4.0**; Chinese-GSD **CC BY-SA 4.0** | Yes (BY/BY-SA data) | mr 3,506 tokens; te 6,465 tokens — **too small for vocabulary**; useful only as morphology test references | Counts only | Lemma + features | Has PROPN tags | Small |
| 10 | **FrequencyWords** (OpenSubtitles 2018) | github.com/hermitdave/FrequencyWords, commit `525f9b56…` (2022-02-07) | MIT | **CC BY-SA 4.0** “for content” (README); underlying subtitle text rights belong to OpenSubtitles/rights holders | BY-SA data, attribution to OpenSubtitles | ko, ar, bn, id present; **te 12,857 lines; mr, hi, ur absent** | Yes | Raw subtitle tokens | Heavy (character names) | Offline; small |
| 11 | **Leipzig Corpora Collection** | wortschatz.uni-leipzig.de/en/usage | n/a | Secondary reports: downloadable corpora **CC BY**, other data/applications **CC BY-NC**. **Primary page blocked by bot-check; unverified.** | Only after primary confirmation | Reportedly mr/te corpora exist (unverified) | Yes (word lists) | Surface | Unfiltered | Offline |

### 4.2 Reviewed and excluded (or validation-only)

| Source | Reason |
| --- | --- |
| UD Arabic-PADT (CC BY-NC-SA 3.0), UD Hindi-HDTB (CC BY-NC-SA 4.0), UD Urdu-UDTB (CC BY-NC-SA 4.0) | **NonCommercial** — not compatible with unrestricted Apache-2.0 redistribution. |
| UniMorph `ara_atb` / `ara_new` | Built from Penn Arabic Treebank lemmas (LDC-licensed corpus); CC BY-SA 3.0 label on the README does not settle upstream LDC provenance. Use only the Wiktionary-derived `ara` file, if any. |
| LibreOffice/Hunspell de_DE_frami (GPL-2/3), es (GPL-3 / LGPL-3 / MPL-1.1 tri), ar Ayaspell (GPL-2 / LGPL-2.1 / MPL-1.1 tri); LibreOffice repo commit `c0865a85…` | Copyleft. es and ar *could* be taken under MPL-1.1 (file-level copyleft), but a derived word list is then MPL-covered data; de is GPL-only. Recommend **validation oracle at build time only** (e.g. “is this decomposition’s part a valid German word?”), not a shipped list. No ko/mr/te/hi in that repo. |
| JMdict / JMnedict (EDRDG) | **CC BY-SA 4.0**, but the EDRDG licence requires a procedure for **regularly updating** bundled data and on-screen/documentation acknowledgement. Ongoing obligation; ja is not a priority language. JMnedict would be a strong ja name-exclusion source if that obligation is accepted. |
| NIKL 우리말샘 (opendict.korean.go.kr) | Text **CC BY-SA 2.0 KR** (primary copyright-policy page), but **examples with cited sources are excluded** and multimedia is per-file. Headword + POS only would be admissible as BY-SA data; definitions/examples must not be copied. Standard Korean Dictionary (표준국어대사전) licence was not checked. No frequency. Treat as a root-validation source, second to mecab-ko-dic. |
| Korean defense terminology dataset (data.go.kr 3058147) | Already excluded in `DICTIONARY_SOURCES.md` (KOGL Type 4, NC/ND). |
| IndoWordNet / Hindi WordNet, CAMeL Tools morphology DBs, AraVec, kiwipiepy models | Not verified in this pass; licences reported as restricted/NC or model-bundled. Do not adopt without primary licence review. |

## 5. Per-priority-language assessment

| Lang | Best defensible source today | 30k–50k? | Main gap / risk |
| --- | --- | --- | --- |
| **mr** | IndicCorp v2 counts (offline) + Wiktionary headwords (5.3k) for root review; UD Marathi only as morphology check | Plausible from IndicCorp after filtering; **not available offline today** | No installed source; licence tag on IndicCorp is prose-only; name filtering needs Wikidata/Wiktionary `name` entries |
| **te** | Same as mr (IndicCorp v2 te ≈31M rows); Wiktionary 21.8k forms; FrequencyWords te 12.9k (BY-SA, subtitle names) | Plausible from IndicCorp | Agglutinative; surface list will under-cover without reviewed suffix rules |
| **ar** | wordfreq ar large (57k at Zipf ≥ 3.0) | Yes | Surface forms carry clitics and names; reviewed proclitic stripping needed (§7) |
| **de** | wordfreq de large (39.5k at ≥3.0; 84k at ≥2.5) | Yes | Open compounds; bounded decomposition over the same list (§7) |
| **es** | wordfreq es large (35k at ≥3.0; 67k at ≥2.5) | Yes | Enclitic pronouns (`dámelo`) — optional, low risk |
| **zh** | wordfreq zh large (38.9k at ≥3.0) **minus** jieba `nr/nrt/nrfg/ns/nt` | Yes | ≈12% of Zipf ≥ 3.0 entries carry a name/place/org tag (4,843 of 39,057) |
| **ko** | wordfreq ko small (29.9k morphemes) ∩ mecab-ko-dic non-NNP roots; conjugation analyser required | **Root count <30k**; effective surface coverage depends on morphology | List is morphemes, includes names; Sejong provenance caveat on mecab-ko-dic |
| en, fr, pt, ru, bn, ja | wordfreq large | Yes | ja morphemes vs gateway segmentation must be checked |
| tr | wordfreq small (63k) | Yes | Agglutinative; surface only |
| id | wordfreq small (30.8k total) | 30k only | — |
| hi, ur | wordfreq small (26.3k / 23.0k) + IndicCorp v2 (offline) | Not from installed data | Same IndicCorp caveats; hi/ur NC treebanks excluded |

## 6. Person/place-name exclusion and privacy safeguards

**Precedence (must not change):** explicit private/forced rules → prior private
mappings in the session → code/URL/source references and protected domain dictionaries
→ name/place exclusion → ordinary vocabulary. High frequency is never permission to
disclose a token that matches a private rule or a prior mapping; a private homonym of
an ordinary word (e.g. a project called with an ordinary noun) stays masked because the
earlier stages win.

Conservative exclusion sources, by evidence strength:

1. **Wikidata (CC0)** given names (`Q202444`), family names (`Q101352`), human
   settlements (`Q486972`) and countries/admin units — labels per language, built
   offline. Avoid `P279*` closure on the public endpoint (timed out); use `P31` plus
   enumerated subclasses or a dump.
2. **GeoNames (CC BY 4.0)** `cities15000` (≈25k) names + `alternateNamesV2` for the 17
   language codes; drop `isHistoric`, keep preferred/short.
3. **jieba POS tags (MIT)** for zh: drop `nr/nrt/nrfg/ns/nt` entries from the ordinary
   set (4,843 of 39,057 at Zipf ≥ 3.0). jieba tags are noisy; dropping is the safe
   direction.
4. **mecab-ko-dic NNP (Apache-2.0)** for ko; **Wiktionary `name` POS** for mr (631
   senses) and te (1,944 senses).
5. Existing authored `NAME_WORDS`/`ENGLISH_NAMES`/`DOMAIN_WORDS` remain.

Rules: exclusion only ever *removes* from the disclosed set; a word that is both an
ordinary word and a common name (e.g. Korean `하늘`, English `grace`, Arabic `أمل`)
is resolved toward **masking** unless a reviewer marks it ordinary-and-acceptable with
a recorded reason. Keep the exclusion source and reason per removed entry so reviews
are auditable.

**How to evaluate (after #324 gate, with privacy controls):**

- Synthetic, independently authored probes only — not the reported example sentences.
- For each language, measure (a) **leak rate**: synthetic private rules/prior mappings
  whose spelling is also in the ordinary set must remain masked (target 0 leaks; any
  leak is a blocker); (b) **name leak**: held-out synthetic sentences containing
  names/places drawn from a *different* source than the exclusion source (e.g. test
  with GeoNames names when excluding with Wikidata) — report how many survive;
  (c) **overmasking** of ordinary text; (d) comprehension through the existing
  separate LLM comprehension suite, with provider calls only under that suite's rules.
- Report per language and per Zipf cutoff, so the cutoff is chosen from measured
  leak/overmask trade-offs, not from the 30k–50k target alone.

## 7. Candidate morphology approaches (proposals only)

All share one invariant: **a token is disclosed only if a reviewed root is found and
every stripped affix comes from a closed, reviewed inventory; otherwise the unknown
token falls back to masking.** No open-ended suffix stripping, no longest-match on
unknown stems, no fallback to another language’s list.

- **ko — reviewed-root conjugation.** Build a root inventory from wordfreq ko
  morphemes ∩ mecab-ko-dic VV/VA/NNG (minus NNP, minus single-syllable roots unless
  reviewed). For predicates, generate surface forms from a closed ending table
  (−다, −아/어요, −았/었다, −고, −는, −(으)ㄴ, −(으)면, −(으)세요 …) with explicit
  irregular classes (ㅂ, ㄷ, ㅅ, 르, 하다) rather than analysing unknown eojeol
  backwards. Existing `decompose_token` stays for josa/copula. UniMorph kor (2,686
  predicates) can serve as a conjugation test oracle, not a vocabulary.
- **de — bounded compound decomposition.** Split into ≤ 3 parts, each part ≥ 4
  characters and present in the wordfreq de set at a stricter cutoff (e.g. Zipf ≥ 3.0);
  linking elements limited to {∅, s, es, n, en, e, er, ens}; head (last part)
  determines acceptance; any part matching a name/domain/private rule blocks the
  whole compound. Hunspell de (GPL) may be used as a build-time check of split
  validity only.
- **ar — proclitics.** Closed inventory {و, ف} × {ب, ل, ك} × {ال} plus `لل`; enclitic
  pronouns (ـه، ـها، ـهم، ـك، ـكم، ـي، ـنا) as a separate closed set; accept only
  if the remainder is in the reviewed ordinary set and not a name. Remainders < 2
  letters reject. Normalise alef/hamza and tatweel identically to the gateway.
- **Indic (mr, te, hi, bn, ur) — case markers/postpositions.** Extend the existing
  `reviewed_inflections` pattern: per-language closed suffix tables (mr `−मध्ये, −ला,
  −चा/ची/चे, −ने …`; te `−లో, −ను, −కు, −తో, −లు …`; hi/ur mostly separate
  postpositions, so plural/oblique endings only), with oblique-stem rules where the
  root changes (e.g. mr `−ा` → `−्या`) listed explicitly per root class. Roots must
  come from the reviewed list built from IndicCorp/Wiktionary, never from the token.
- **es (optional).** Enclitic pronoun stripping on infinitive/gerund/imperative
  (`−me, −te, −lo, −la, −le, −nos, −se`, and doubled `−melo`), accent-restoring
  remainder lookup, remainder must be a known verb form.

## 8. Recommendation (evidence-ranked)

1. **Use installed wordfreq first** for en, es, fr, pt, de, ru, ar, zh, ja, bn, tr:
   reach 30k by lowering the cutoff to the per-language Zipf in §3 (≈2.96–3.45), with
   no new dependency, download or network call; cost ≈4–7 MiB retained per language.
   Keep reading the packaged file at runtime (no extracted copy) so no redistribution
   question arises. Strongest evidence: verified licences + measured counts.
2. **Pair every cutoff increase with source-backed name/place exclusion** (Wikidata
   CC0 + GeoNames CC BY 4.0 built offline; jieba POS for zh) and the privacy
   evaluation in §6 *before* enabling. Without this, ≈12% of zh entries (and visible
   ko/hi/ar names) would be disclosed.
3. **ar and de:** add the bounded morphology of §7 on top of wordfreq rather than
   seeking a new list.
4. **ko:** do not raise the ko cutoff alone (list is morphemes and ends at 29.9k);
   build a reviewed root list with mecab-ko-dic POS after confirming the Sejong
   provenance, plus a closed conjugation table.
5. **mr, te (and hi, ur to reach 30k):** the only defensible scale route found is an
   offline frequency count over IndicCorp v2 with our own tokenizer, shipped as a
   separate data file, after the licence point in §9 is confirmed in writing from
   a primary record. Until then, keep the authored starter lists and treat mr/te as
   documented gaps. Wiktionary (BY-SA) headwords are a smaller, cleaner root-review
   aid.
6. Leave id at its 30.8k ceiling; do not claim 50k.

## 9. Unverified points

- Leipzig Corpora Collection licence (CC BY vs CC BY-NC split) — primary page behind a
  bot check; secondary sources only.
- IndicCorp v2 machine-readable licence (only prose “will be released under CC-0”);
  copyright position of crawled source text for derived counts.
- 21st-Century Sejong outputs used in mecab-ko-dic’s entry list — redistribution terms.
- UniMorph tel/kor licence (no licence line in those READMEs).
- Wikidata per-language name/place label counts (query timed out).
- Wikimedia’s current Wiktionary text licence version (the fetched copyright page is
  self-marked outdated; CC BY-SA 4.0 + GFDL legacy assumed).
- wiktextract code licence (“other”).
- Whether gateway Japanese segmentation (tinysegmenter) aligns with wordfreq’s MeCab
  morpheme units; not measured here.
- Exact transient peak memory on other Python versions/platforms.
- Standard Korean Dictionary (표준국어대사전) licence.
