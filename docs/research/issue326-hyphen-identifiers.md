# Issue 326: atomic hyphen identifiers

Status: **fixed in 2.7.5**. This note records the local regression and its
limits; it is not a claim about model comprehension.

## Cause

The shared natural-language tokenizer previously emitted `TV-592` as a
`WORD`, punctuation, and `NUMBER`. The masking engine therefore allocated a
symbol alias for `TV` and handled `592` under the independent number policy.
A provider could receive two labels for one opaque part/model number, and a
strict replay could no longer preserve the intended lexical unit.

## Fix

The tokenizer now recognizes an ASCII part-number span before ordinary word
and number splitting. The span starts at an ASCII letter, contains letters or
digits before a hyphen, requires digits after the first hyphen, and permits
additional hyphen-separated alphanumeric components. Word boundaries are
required on both sides; a dotted numeric suffix is not absorbed. Existing
URL, email, secret, UUID, IP, phone, and code-block precedence remains ahead
of this rule. The span is one forced entity in prose/data/path masking, and
natural-language adapters retain it as one chunk.

Existing opaque code literals and comments already pass through the code lexer
as complete literal spans, so `"TV-592"` and a comment containing `ABC-12`
remain one restorable mapping. The code parser was intentionally not changed.
Unquoted executable expressions remain executable expressions: both `x - 1`
and `x-1` retain their subtraction operator, and unquoted `TV-592` in
`code=True` is not reinterpreted as an identifier. This is a deliberate
ambiguity boundary rather than a claim that every code-shaped string can be
normalized safely.

The 2.7.2 number right-boundary behavior remains unchanged: digit-leading
segments such as `2024_report` and `89_8lzey` stay one `WORD` span.

## Verification

`tests/test_hyphen_identifiers.py` covers:

- `TV-592`, `ABC-12`, `A1-234`, repeated values, and multi-component forms;
- lexical boundaries and Unicode punctuation separators;
- URL, email, secret, and code-block precedence;
- natural-language adapter spans and the 2.7.2 digit-leading path boundary;
- exact text round-trip and stable repeated aliases;
- code subtraction with both spaced and unspaced operators, both number-mask
  settings, and opaque string/comment literals;
- session request/response JSON types plus a fake local HTTP provider capture
  with tool arguments and result replay.

These are offline unit/fake-provider tests. They do not call a real model and
do not measure or infer model comprehension.

## Coordinator integration verification

Eight selected part-number/chunk/mapping regressions fail against released
2.7.2. In the combined 2.7.5 integration, dedicated identifiers, digit-leading
paths, masking, code parsers and gateway tool workflows pass **360 tests**;
232 existing optional native-grammar cases are skipped. Ruff and mypy pass.
CLI, module, installed metadata, MCP application and privacy-status agree on
**2.7.5**. Real-model comprehension and the new remote CI matrix are separate.
