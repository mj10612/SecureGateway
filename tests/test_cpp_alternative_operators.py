"""C++ alternative operators remain syntax, with reversible identifiers."""
import shutil
import subprocess
from pathlib import Path

import pytest

from secure_gateway.engine.code_parser import CodeParser
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.models import SurrogateStrategy, TokenType
from secure_gateway.session import PrivacySession

OPERATORS = ('and', 'or', 'xor', 'bitand', 'bitor', 'not_eq', 'not', 'compl',
             'and_eq', 'or_eq', 'xor_eq')


def source_for(operator):
    if operator in {'not', 'compl'}:
        expression = f'return {operator} privateLeft;'
    elif operator.endswith('_eq') and operator != 'not_eq':
        expression = f'privateLeft {operator} privateRight; return privateLeft;'
    else:
        expression = f'return privateLeft {operator} privateRight;'
    return f'int privateCheck(int privateLeft, int privateRight) {{ {expression} }}'


@pytest.mark.parametrize('operator', OPERATORS)
@pytest.mark.parametrize('strategy', list(SurrogateStrategy))
def test_cpp_alternative_operator_masking_and_roundtrip(operator, strategy):
    source = source_for(operator)
    session = PrivacySession('cpp-operators', strategy=strategy)
    engine = MaskingEngine()
    masked = engine.mask_code(source, session.session_id, session.generator,
                              session.forward_store, session.reverse_store, language='cpp')
    tokens = CodeParser.tokenize(masked.masked_text, 'cpp')
    assert any(value == operator and subtype == 'keyword' for value, _, subtype in tokens)
    assert 'privateCheck' not in masked.masked_text
    assert engine.unmask(masked.masked_text, session.session_id, session.reverse_store,
                         strategy, strict=True).unmasked_text == source


@pytest.mark.parametrize('operator', OPERATORS)
def test_cpp_operator_words_are_still_c_identifiers(operator):
    tokens = CodeParser.tokenize(f'int {operator} = 1;', 'c')
    assert any(value == operator and kind == TokenType.IDENTIFIER
               for value, kind, _ in tokens)


@pytest.mark.parametrize('strategy', list(SurrogateStrategy))
def test_cpp_alternative_operators_pass_native_syntax(strategy):
    compiler = shutil.which('clang++') or shutil.which('clang')
    fallback = Path(r'C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Tools\Llvm\x64\bin\clang.exe')
    if compiler is None and fallback.is_file():
        compiler = str(fallback)
    if compiler is None:
        pytest.skip('Clang unavailable')
    for index, operator in enumerate(OPERATORS):
        source = source_for(operator).replace('privateCheck', f'privateCheck{index}')
        session = PrivacySession('native-cpp', strategy=strategy)
        engine = MaskingEngine()
        masked = engine.mask_code(source, session.session_id, session.generator,
                                  session.forward_store, session.reverse_store, language='cpp')
        for candidate in (source, masked.masked_text):
            result = subprocess.run([compiler, '-fsyntax-only', '-x', 'c++', '-'],
                                    input=candidate, capture_output=True, text=True, timeout=30)
            assert result.returncode == 0, result.stderr
