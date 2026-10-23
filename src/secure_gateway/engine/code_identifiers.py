"""Binding-equivalent aliases with separate, exactly restorable spellings.

Languages can give different source spellings the same identifier. Distinct
aliases must remain equivalent under that language's own comparison rules;
otherwise preserving the spelling for restoration would split the binding.
"""

from __future__ import annotations

import re
import unicodedata


def ascii_lower(value: str) -> str:
    return value.translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'))


def identifier_key(raw: str, language: str, *, quoted: bool = False) -> str:
    if language == 'python':
        return unicodedata.normalize('NFKC', raw)
    if language in {'javascript', 'typescript'}:
        return re.sub(r'\\u(?:\{([0-9a-fA-F]+)\}|([0-9a-fA-F]{4}))',
                      lambda match: chr(int(match[1] or match[2], 16)), raw)
    if language == 'rust':
        return unicodedata.normalize('NFC', raw.removeprefix('r#'))
    if language == 'csharp':
        decoded = re.sub(r'\\(?:u([0-9a-fA-F]{4})|U([0-9a-fA-F]{8}))',
                         lambda match: chr(int(match[1] or match[2], 16)), raw.removeprefix('@'))
        return ''.join(char for char in decoded if unicodedata.category(char) != 'Cf')
    if language in {'kotlin', 'swift', 'r'} and raw.startswith('`') and raw.endswith('`'):
        return raw[1:-1]
    if language.startswith('sql:'):
        dialect = language.partition(':')[2]
        if dialect == 'sqlite' or not quoted:
            return ascii_lower(raw)
        return raw
    if language in {'powershell', 'vbnet', 'vba', 'nasm:macro'}:
        return ascii_lower(raw[1:-1] if language in {'vbnet', 'vba'} and raw.startswith('[') and raw.endswith(']') else raw)
    return raw


def equivalent_alias(base: str, language: str, variant: int) -> str:
    """Create a distinct spelling of the same native identifier, without data.

The finite spelling space is checked explicitly instead of splitting a binding
when it is exhausted. Allocation limits still bound total session state.
"""
    if not variant:
        return base
    def transform(char):
        if language == 'python':
            return chr(ord(char) + 0xFEE0)
        if language in {'javascript', 'typescript', 'csharp'}:
            return '\\u' + f'{ord(char):04x}'
        return char.swapcase()
    letters = [i for i, char in enumerate(base) if char.isascii() and char.isalpha()]
    if language == 'python':
        positions = [i for i, char in enumerate(base) if char.isascii() and char.isalnum()]
    elif language in {'javascript', 'typescript', 'csharp'}:
        positions = letters
    elif language.startswith('sql:') or language in {'powershell', 'vbnet', 'vba', 'nasm:macro'}:
        positions = letters
    elif language == 'rust' and variant == 1:
        return 'r#' + base
    elif language in {'kotlin', 'swift', 'r'} and variant == 1:
        return '`' + base + '`'
    else:
        raise ValueError('Equivalent identifier spelling capacity reached; use a new session.')
    if variant >= 1 << len(positions):
        raise ValueError('Equivalent identifier spelling capacity reached; use a new session.')
    indexes = {position: bit for bit, position in enumerate(positions)}
    return ''.join(transform(char) if i in indexes and variant & (1 << indexes[i]) else char
                   for i, char in enumerate(base))


def valid_identifier_alias(mapping) -> bool:
    """Validate extra spellings when reading encrypted snapshots."""
    from secure_gateway.engine.code_parser import LANGUAGE_KEYWORDS

    base = mapping.identifier_base
    language = mapping.identifier_language
    supported = (set(LANGUAGE_KEYWORDS) - {'sql'}) | {'sql:standard', 'sql:postgresql', 'sql:sqlite', 'nasm:macro'}
    return bool(base and language in supported and mapping.identifier_key is not None
                and mapping.context == 'code' and mapping.token_type.value == 'identifier'
                and re.fullmatch(r'(?:smcp_ID|private_symbol)_\d+', base)
                and identifier_key(mapping.surrogate, language, quoted=mapping.identifier_quoted)
                == identifier_key(base, language)
                and identifier_key(mapping.original, language, quoted=mapping.identifier_quoted)
                == mapping.identifier_key)
