# Local language data

The gateway uses the packaged word frequency lists in **wordfreq 3.1.1**, by
Robyn Speer and contributors, to recognize ordinary prose across fifteen of
the supported languages. The package is installed with the application; no
prompt text is sent to a dictionary service and no data is downloaded at runtime.

- Project and methodology: https://github.com/rspeer/wordfreq
- Code: Apache License 2.0 (upstream `LICENSE.txt`).
- Included frequency data: Creative Commons Attribution-ShareAlike 4.0, with
  upstream source attribution and license notices distributed in wordfreq.
- Frequency data sources and credits: https://github.com/rspeer/wordfreq/blob/master/README.md

SecureGateway reads these packaged lists without modifying or redistributing
an extracted copy. Wordfreq's tokenizer is not used: existing local gateway
tokenization preserves source spelling and avoids additional CJK dependencies.
Marathi and Telugu have independently authored starter vocabularies in
`gateway_indic_vocabulary.py`; the gateway never substitutes another language's
dictionary when a language is unavailable.

Frequency is a heuristic, not a privacy classification. Frequent domain terms
and names can be sensitive. Reviewed domain/name lists and explicit forced
masking rules take priority over ordinary vocabulary. The starter lists cannot
enumerate every person, organization, industry or inflected form.
