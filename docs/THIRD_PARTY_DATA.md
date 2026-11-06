# Local language data

## Optional context encoder (2.4.0)

The explicitly installed encoder is [intfloat/multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small),
upstream MIT license, revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`.
SecureGateway uses the upstream `onnx/model_qint8_avx512_vnni.onnx`, tokenizer and
configuration without changing their bytes. Exact file sizes and SHA-256 values
are pinned in `src/secure_gateway/context_assets.py`. Weights are downloaded from
the upstream revision only on an explicit install command, not redistributed in
the Python package. Preserve the upstream license when redistributing these assets.
The `query: ` prefix follows the upstream model card for non-retrieval tasks.
Model language coverage does not establish privacy classification accuracy.

The comparison also used [sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)
(Apache-2.0), revision `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`, with upstream
`onnx/model_quint8_avx2.onnx`. It is not the runtime encoder. Both experiments used
independently authored synthetic data committed with the tests. The small bundled
classifier head was trained locally on those labelled training/calibration splits;
held-out test rows were not used to train its coefficients.

## Packaged frequency vocabulary

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
