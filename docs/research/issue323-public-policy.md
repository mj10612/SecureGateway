# Issue #323: public-word prose policy (implementation notes)

Status: implemented in the root work-in-progress tree for review. It is **not** a release
claim and **not** an evaluation result. Root owns final independent evaluation, versioning
and release.

## User policy

1. **Ordinary public words are not masking targets.** This covers frequent vocabulary,
   typed ordinary predicates and widely used personal or place names.
2. **Weak signals are not private evidence.** Presence in a name or place database, a
   static domain list, or looking unfamiliar or specialist is not enough to mask a word.
3. **Mask definite private targets.** Explicit/forced private rules, existing private
   mappings (code, path and tool identifiers), sensitive formats, and identifier or path
   contexts.

## What changed (runtime)

| Area | Before (root WIP, data 1.2.0) | After |
| --- | --- | --- |
| `gateway_public_vocabulary.lexicon` | Public words minus `NAME_WORDS`, `ENGLISH_NAMES` and `DOMAIN_WORDS`. Those lists were added to `names`. | Public words plus authored ordinary words. Nothing is subtracted. `names` is data evidence minus public words and is no longer used as a veto. |
| `GatewaySession._mask_prose` static list hits (`domain_terms`) | Every `NAME_WORDS`/`ENGLISH_NAMES`/`DOMAIN_WORDS` hit was forced private. | Name-list hits, including affixed forms, are dropped. A domain-list hit is dropped when its surface is a public word or ordinary inflection. Only non-public domain-list terms keep the old default. |
| Name evidence | Name roots vetoed public forms in ko/ar/mr/te. Capitalised words were masked unless authored-public (de only). | No name veto. Public words are passed as `preserve_capitalized_words` in every language. |
| Words absent from the vocabulary | Masked as content words. | **Kept**, unless one of the narrow rules below applies. |
| Generic domain spans (`SharedEngine._chunks`) | Every catalog span was forced ENTITY. | During prose masking, a **single-word** span that is a public word or ordinary inflection, and not a private root, is skipped. Multi-word and non-public spans (e.g. `KF-21`, `Manta Ray`) are still masked. |

## Rules that still mask a prose word, in precedence order

1. **Forced private rules** (`_force_mask`) are applied after prose masking to every
   occurrence. This includes public spellings such as a forced `Berlin`.
2. **Existing private mappings** (`forward_store.originals_in`) and their ordinary
   inflections (`is_ordinary_form` with `private_root`). For example, a code identifier
   `bank` makes a later prose `bank` private in that session.
3. **Sensitive formats** recognised by the engine tokenizer (email, URL, secret/token,
   UUID, IP, phone, code block) are unchanged.
4. **Identifier/path context** (`_identifier_context`): a word of at least 2 characters
   - preceded by `/`, `\`, `_` or `@`
   - followed by `/`, `\` or `_`
   - or part of a dotted name (`config.yaml`)

   Examples: `src/radar/config.yaml`, `@john`, `C:\Users\…`.
5. **Identifier shape** (`_identifier_shaped`), applied only to non-public words: inner
   capitals (`KeplerQzx`) or all-capital words of two or more letters (`QZXLAB`).
6. **Narrow name fallback** (`_name_fallback`), applied only to non-public words:
   - the word is Title-case in a cased script
   - it is **not** at the start of a sentence, line or list item
   - the language is not German, whose nouns are capitalised

   Example: mid-sentence `Zorblax`. Case-free scripts (ko, ja, zh, ar, hi, …) never
   trigger it. Common names that are public vocabulary never reach this rule.
7. **Non-public static `DOMAIN_WORDS`** terms and multi-word or non-public domain-catalog
   spans keep their previous default masking.

## Data revision 1.3.0

Data 1.2.0 still skipped authored `DOMAIN_WORDS` during frequency selection, so a
domain-list ordinary word could never be public. Data **1.3.0** counts these words as
`domain_attested_words` metadata instead.
- **Size of the change:** 4–12 words per language, e.g. en `bank`, `cancer`, `apple`;
  zh `北京`, `银行`; ko `은행`, `암`.
- **Rebuild:** offline from the same cached inputs, with the same ranking and filters.
  `--check` is byte-identical.
- **Typed Korean predicates:** unchanged at 141 verbs / 40 adjectives.
- **Evidence:** the 1.2.0 bytes and curator are preserved in `docs/research/issue323-data-1.2.0/`
  with `SHA256SUMS.txt`.

## Tests

`tests/test_issue323_public_policy.py`, `tests/test_gateway_prose_vocabulary_integration.py`,
`tests/test_gateway_public_vocabulary.py` and `tests/test_common_vocabulary_data.py` cover:
- ordinary words, common names and places in normal prose (7 languages)
- static domain words
- capitals and NFC/NFD bytes
- Korean predicates and inflections
- German nouns and compounds
- unknown prose kept, plus the fallbacks
- the same public spellings when forced private, registered as code identifiers, or
  appearing in paths/handles — all masked
- sensitive formats
- generic domain spans
- grammar words in all 17 languages

The obsolete "Berlin is always private" assertion was replaced with:
- Berlin is public by default
- an explicit forced-Berlin control
- a registered-mapping control

The obsolete "name evidence vetoes a frequent inflected form" test was replaced with:
- name evidence is no veto
- a registered private root masks its inflection

## Policy exceptions vs regressions vs untested scope

- **Intentional public-policy exceptions:** words that earlier versions masked and that are
  now public.
  - common names and places (John, Smith, Berlin, Paris, 서울)
  - static domain-list words (bank, cancer)
  - unknown lowercase or sentence-initial words
  - unknown case-free-script words

  An unregistered private person, place or project whose name is a public word, or which
  appears only in a case-free script or at a sentence start, **will be disclosed**. Only an
  explicit private registration, forced rule or prior mapping protects it.
- **Old labels:** earlier privacy gates were scored under the old blanket labels. Their
  results are not relabelled. The prior "no new private exposure" holdout gate is **not**
  claimed as passed under its old labels.
- **Untested scope:**
  - real model comprehension/privacy measurement
  - stream paths (#332)
  - snapshot/opaque recovery (#338)
  - code tokenizer/identifier changes (#326/#330)
  - packaged domain catalog content (#325)
  - prose in `UNCOMMON_WORDS`/`ENTITIES_ONLY` modes. The policy applies when the public
    lexicon is active, i.e. outside `AGGRESSIVE` mode.
