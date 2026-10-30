# Plain-text uncommon-word policy

Version 1.6.0 adds the explicit `uncommon_words` text mode. Existing text modes
keep their meaning. `content_words` already masks unknown words as well as ordinary
content words; `entities_only` relies on entity cues and can leave lowercase
internal names unchanged. The new policy preserves reviewed ordinary vocabulary
and masks remaining content locally.

```sh
secure-gateway mask "the meeting uses zorblyx and nexvanta" \
  --mode uncommon_words --common-word nexvanta --json-output
```

With the bracket strategy the ordinary words and explicit ordinary word
`nexvanta` remain visible while `zorblyx` receives a reversible alias. All four
strategies use the same policy. CLI `--preserve` is an explicit override as in
existing modes, while `--sensitive-term` forces protection.

SDK `LocalPrivacyClient.request` accepts `mode=MaskMode.UNCOMMON_WORDS` and
`common_vocabulary={"nexvanta"}`. The local MCP `mask_text` tool accepts
`mode="uncommon_words"` and `common_vocabulary=["nexvanta"]`. MCP tool arguments
are provider-visible, so confidential text and dictionaries should be supplied
through a trusted local boundary. Gateway configuration uses `prose_mode` and
`common_words` as described in [GATEWAY.md](GATEWAY.md).

## Data and decisions

`engine/common_words.py` contains a small English/Korean starter vocabulary,
version `1`, authored for this Apache-2.0 project. It has no third-party corpus,
frequency model, downloads or external text-classification calls. A large corpus
or remote classifier could improve coverage but would add licensing, packaging
or confidentiality costs; this first implementation uses a reviewable starter
list and explicit organization vocabulary. It is deliberately incomplete, not a
statistical measure of commonness. Updating the list changes disclosure decisions
and requires review.

Lookups normalize NFC and casefold once for custom words; original spelling is
stored unchanged. Korean uses the existing conservative stem/particle rules and
known vocabulary, not a new morphological model. Other supported languages keep
the existing grammar/content distinction and mask unknown content; there is no
silent fallback to leaving unknown words clear. Explicit additional ordinary
words work in those languages too. There is no dictionary loading service that
can fail open: a missing packaged module fails import.

Existing sensitive patterns and explicit sensitive terms take precedence over
ordinary vocabulary. Proper-name capitalization cues, including mixed-case
English names, remain protected even if the name appears in ordinary vocabulary.
Explicit `custom_preserve` retains its existing override for unforced words.
A common lowercase word used as a private project name is intrinsically ambiguous;
put it in `sensitive_terms` when it must be protected. No dictionary proves a word
is safe to disclose. Hyphenated words are processed by their lexical components;
unknown components and mixed alphanumeric tokens remain protected. Numbers retain
their existing prose policy; this feature does not change source-number defaults.

## Verification and limits

Tests compare 16 ordinary and 13 unusual synthetic/hand-labelled English/Korean
words: the new mode masks all 13 unusual words with no ordinary-word false
positives in this small fixture. Existing content-word mode masks more ordinary
words; entity-only mode misses lowercase unusual words. These figures demonstrate
the policy distinction, not general-purpose privacy or NER accuracy.

Regression tests cover four strategies, exact strict restoration, encrypted
snapshot restart, forced/preserved words, CLI/MCP/SDK/Gateway paths, unsupported
language fallback, input/mapping limits and invalid dictionaries. Default text
tokenization also keeps combining marks attached to words. Reserved alias-shaped
source text stays opaque even beside letters or inside a URL/code/sensitive span.

A local Python 3.14.7 smoke measurement on 2,000 repetitions of
`the meeting uses zorblyx and nexvanta.` (78,000 UTF-8 bytes, 12,000 words)
with `tracemalloc` enabled gave:

| Mode | Masked words | Time | Peak traced allocation |
| --- | ---: | ---: | ---: |
| content_words | 8,000 | 0.379 s | 3.40 MB |
| entities_only | 0 | 0.295 s | 3.36 MB |
| uncommon_words | 4,000 | 0.377 s | 3.39 MB |

All three restored the original text exactly. In this sentence the new mode
retains the ordinary words and protects the two unusual words; punctuation,
spacing and word order are retained. Times include tracing overhead, are a
single local observation and are not throughput or semantic-quality guarantees.
