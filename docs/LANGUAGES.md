# Language support

SecureGateway provides **17 natural-language lexical adapters** and **24 code
lexers**. Select the language explicitly when the text or source is ambiguous.
These adapters support local masking and exact restoration; they do not promise
full morphology, named-entity recognition, compilation, or semantic equivalence.
The tests use synthetic fixtures, not a multilingual NER benchmark.

## Natural languages

| Language | Tag | Scope |
| --- | --- | --- |
| English | `en` | Existing English grammar classifier |
| Korean | `ko` | Existing Korean particles and copula handling |
| Chinese | `zh` | Local dictionary segmentation; original simplified/traditional spelling |
| Spanish | `es` | Closed-class words, accents and raw Unicode spelling |
| Hindi | `hi` | Devanagari marks and joining sequences kept with words |
| Arabic | `ar` | Conservative Modern Standard Arabic vocabulary; original diacritics and logical RTL order |
| French | `fr` | Closed-class words and apostrophe elisions, including `l’` and `d'` |
| Bengali | `bn` | Bengali marks and joining sequences kept with words |
| Portuguese | `pt` | Shared starter vocabulary for Brazilian/European text |
| Russian | `ru` | Cyrillic words and conservative grammar vocabulary |
| Urdu | `ur` | Arabic-script words, marks and joining controls |
| Indonesian | `id` | Conservative closed-class vocabulary |
| German | `de` | Shared vocabulary, original regional spelling retained |
| Japanese | `ja` | Local statistical segmentation; particles and raw spelling |
| Marathi | `mr` | Devanagari words and a separate Marathi grammar vocabulary |
| Telugu | `te` | Telugu marks and joining sequences kept with words |
| Turkish | `tr` | Turkish `I/ı` and `İ/i` grammar comparisons; original spelling retained |

Tags are case-insensitive. Regional/script tags resolve to the same base
adapter: for example `zh-Hans`, `zh-Hant-TW`, `pt-BR`, `pt-PT`, `de-DE`,
`de-AT`, `de-CH`, `es-MX` and `fr-CA`. Underscores are accepted as tag
separators. A regional tag does **not** select a separate regional dictionary,
translate text, or convert its spelling. Unsupported base tags raise an error.
This is base-language selection, not a complete BCP 47 validation service.

The 15 new adapters preserve reviewed closed-class words and mask unknown words
conservatively. In `entities_only`, unknown content words are also masked because
there is no reliable local proper-name cue for every script. This deliberately
favors masking over named-entity precision. `sensitive_terms` forces matching
terms to be masked even if grammar/custom-preserve rules would preserve them.
Do not rely on a short grammar vocabulary to identify every confidential name.

Token boundaries include combining marks, vowel signs, variation selectors and
joining controls. Input is not normalized for storage or restoration. Grammar
lookup uses NFC and case comparison; punctuation, spacing, RTL logical order and
raw accents remain available for exact restoration. This does not include a
full Unicode grapheme-break implementation or every language's morphology.

### Automatic and mixed text

`language="auto"` is a heuristic default, not a language-identification model.
Kana selects Japanese; Hangul selects Korean; Han defaults to Chinese;
Devanagari defaults to Hindi; Bengali, Telugu, Arabic-script and Cyrillic text
select Bengali, Telugu, Arabic and Russian respectively. Other text defaults
to English. Except for Kana precedence, script selection follows the first
recognized script. Hindi/Marathi, Arabic/Urdu and Han-only Chinese/Japanese
cannot be distinguished reliably by these rules. Latin-script languages also
require explicit selection for their own grammar vocabulary.

An explicit adapter processes mixed ordinary words conservatively. Existing
sensitive spans, URLs, email addresses and code blocks retain their protected
precedence. Korean tokens retain the existing Korean grammar path even in mixed
text. This is not per-sentence language detection or automatic code switching.

## Code languages

Use the canonical name or an alias in `mask_code(language=...)`, CLI
`--code-language`, or a supported fenced-code label. Code-language selection is
separate from the natural-language tag.

| Language | Canonical name / aliases | Lexical scope |
| --- | --- | --- |
| Python | `python`, `py` | Existing Python lexer, normalized identifier references |
| JavaScript | `javascript`, `js` | Existing lexer, contextual keywords and escaped identifiers |
| TypeScript | `typescript`, `ts` | Existing TypeScript/JavaScript keyword rules |
| Go | `go` | Existing Go lexer |
| Rust | `rust`, `rs` | Existing Rust lexer, raw identifier handling |
| Java | `java` | Existing Java lexer |
| C | `c` | Existing C lexer and preprocessing tokens |
| C++ | `cpp`, `c++` | Existing C++ lexer and raw strings |
| SQL | `sql` | Selected SQL dialect; quote/case policies are dialect-specific |
| Bash | `bash`, `sh`, `shell` | Bash-compatible common syntax, expansions and here-documents; not zsh/fish |
| C# | `csharp`, `cs`, `c#` | Common syntax including C# 11 raw/interpolated strings |
| PowerShell | `powershell`, `ps1`, `pwsh` | Common Windows PowerShell 5 / PowerShell 7 lexical forms |
| PHP | `php` | PHP 8 source; mixed PHP/HTML is rejected |
| Kotlin | `kotlin`, `kt`, `kts` | Common Kotlin 1.9/2 lexical forms, templates and nested comments |
| Lua | `lua` | Lua 5.4/5.5 lexical forms; not Luau/LuaJIT extensions |
| Assembly | `nasm`, `asm-nasm` | NASM x86 source; not GAS/MASM or arbitrary architectures; ambiguous `asm` is rejected |
| Swift | `swift` | Common Swift 5/6 strings, interpolation and comments |
| Ruby | `ruby`, `rb` | Common Ruby 3 literals, percent strings and here-documents |
| Dart | `dart` | Common Dart 3 lexical forms and templates |
| R | `r`, `rscript` | Common R 4 lexical forms including raw strings |
| Nix | `nix` | Nix expressions and string interpolation; no evaluation |
| GDScript | `gdscript`, `gd` | Godot 4 GDScript lexical forms |
| VB.NET | `vbnet`, `vb`, `vb.net` | Modern VB.NET source text |
| VBA | `vba`, `bas` | VBA source text; no Office binary extraction or Office compiler |

These version labels describe fixture scope, not complete grammar conformance.
Malformed/unsupported literal forms can raise `ValueError`; do not catch that
error and forward the original source. Legacy shell backtick substitution is
currently rejected. The strict PHP code API rejects mixed HTML. Gateway prose
handling may instead mask an unrecognized fragment conservatively as text.

Code `auto` uses recognizable shebangs and syntax cues, then falls back to
Python. It does not recognize every language reliably. Explicit names are
recommended for short snippets, files without shebangs, VB variants and NASM.
Generated aliases are a review representation: preserving syntax in a fixture
does not establish that masked code behaves like the original.

**Numeric source constants are preserved by default.** `mask_numbers=True`
(or CLI `--mask-numbers`) opts into source-number masking. This default concerns
code literals; prose number masking follows the text mode's existing policy.

## Local usage

The offline [multilingual example](../examples/multilingual.py) exercises all 17
natural languages with all four surrogate strategies and restores locally:

```powershell
python examples/multilingual.py
secure-gateway mask "La empresa Álamo envía datos." --language es --json-output
secure-gateway mask --input-file example.ps1 --mode code_aware --code-language powershell --json-output
```

For restoration across separate CLI processes, use the same encrypted
`--session-file` and supply its password locally (for example through
`SECURE_GATEWAY_SESSION_PASSWORD`), then `unmask --strict`. See
[local integration](LOCAL_INTEGRATION.md). Keep restored responses and mappings
outside the provider/model context. Calling a model-visible MCP tool with raw
confidential text does not make that initial argument private.

The gateway config's `natural_language` selects prose handling for that gateway:

```json
{
  "natural_language": "pt-BR",
  "mask_numbers": false
}
```

Merge these fields into an existing gateway configuration; the snippet is not a
complete standalone gateway configuration. `gateway start --config PATH` reads
that setting. In the local API, use `GatewaySession(natural_language="pt-BR")`.
Source fences and code APIs continue to select their own source language.
`LocalPrivacyClient.request(..., language="fr")` chooses a prose adapter before
the provided callback receives the masked payload.

## Offline segmentation dependencies

| Option | Decision and tradeoff |
| --- | --- |
| jieba 0.42.1 | Chinese dictionary segmentation, MIT. Bundled dictionary/model resources; approximately 36.5 MiB installed, excluding bytecode in the measured distribution. Used with HMM disabled for conservative dictionary boundaries. |
| tinysegmenter 0.4 | Japanese statistical segmentation, New BSD. Approximately 29 KiB installed, excluding bytecode in the measured distribution; no external dictionary/model download. |
| ICU/PyICU | Not selected: a broader boundary engine and tailoring options, but native ICU builds/resources add platform packaging complexity. It would still need language-quality evaluation. |
| Character-only splitting | Not selected as the normal CJK path: lossless but weak word semantics and alias consistency. |

Both selected libraries load lazily. Package installation may fetch their
packages; **tokenization makes no network request**. No user dictionary or model
is downloaded at runtime. jieba may create a temporary local `jieba.cache` of its
bundled dictionary model. Original input is not written into that dictionary
cache. Sessions/mappings retain their existing lifecycle and storage rules.
Resource sizes vary by package build and Python installation.

Tokenizer output must concatenate to the exact original input. If a future
segmenter violates that contract, the adapter masks the original span as opaque
content instead of storing a model-normalized spelling. Broad dictionary
coverage and native-speaker assessment remain separate from exact restoration.

## Validation boundaries

`tests/test_natural_languages.py` checks lexical fixtures and Unicode boundaries;
`tests/test_language_interfaces_12.py` checks all 15 new languages across four
strategies and three text modes, plus CLI, MCP-local-call and gateway paths.
These are restoration and masking-contract checks, not proof of NER accuracy.

`tests/test_extended_code.py` checks new code fixtures and provides parse/compile
checks using available Bash (`-n`), PowerShell `Parser.ParseFile` and C# Roslyn
installations. These checks do not execute the fixture programs. Missing native
tools produce explicit skips. Its separate opt-in tree-sitter gate is enabled
with `SECURE_GATEWAY_NATIVE_PARSERS=1` and requires the declared development
grammar packages; missing grammars then fail the gate. Check the actual run
report before claiming a grammar has passed. VB grammar compatibility checks
are not a substitute for native Office VBA compilation. Syntax checks establish
only the tested fixture's syntax, not source behavior or runtime equivalence.
