"""Jieba's optional setuptools bridge varies warning category by environment."""

import builtins
import warnings

import pytest

from secure_gateway.engine import natural_languages


@pytest.mark.parametrize('category,message', [
    (DeprecationWarning, 'pkg_resources is deprecated as an API. See setuptools documentation'),
    (UserWarning, 'pkg_resources is deprecated as an API. See setuptools documentation'),
    (DeprecationWarning, r"invalid escape sequence '\.'"),
    (SyntaxWarning, r'"\." is an invalid escape sequence. Did you mean "\\."?'),
])
def test_jieba_optional_legacy_warning_is_scoped_and_category_independent(monkeypatch, category, message):
    real_import = builtins.__import__
    def legacy_import(name, *args, **kwargs):
        if name == 'jieba':
            warnings.warn(message, category)
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', legacy_import)
    natural_languages._segmenter.cache_clear()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            chunks = natural_languages.tokenize('北京公司的客户', 'zh')
        assert ''.join(chunk.text for chunk in chunks) == '北京公司的客户'
        assert len(chunks) > 1
    finally:
        natural_languages._segmenter.cache_clear()


def test_unrelated_import_warnings_are_not_suppressed(monkeypatch):
    real_import = builtins.__import__
    def unexpected_import(name, *args, **kwargs):
        if name == 'jieba':
            warnings.warn('Unexpected tokenizer compatibility failure', DeprecationWarning)
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', unexpected_import)
    natural_languages._segmenter.cache_clear()
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        with pytest.raises(DeprecationWarning, match='Unexpected tokenizer'):
            natural_languages._segmenter('zh')
