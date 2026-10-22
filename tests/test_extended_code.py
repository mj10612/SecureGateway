"""Language adapters preserve lexical boundaries and exact restoration."""

import pytest
import os
from pathlib import Path
import shutil
import subprocess

from secure_gateway.engine import extended_code
from secure_gateway.engine.code_parser import CodeParser
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.models import SurrogateStrategy, TokenType
from secure_gateway.session import PrivacySession

SOURCES = {
    "bash": 'privateName=42\nprintf "%s" "$privateName"\n',
    "csharp": 'class PrivateType { string privateName = $"secret {privateValue}"; int privateCount = 42; }',
    "powershell": '$privateName = 42\nif ($privateName -eq 42) { Write-Output "secret $privateName" }',
    "php": '<?php $privateName = 42; echo "secret {$privateName}"; ?>',
    "kotlin": 'fun main() { val privateName = 42; val privateText = "secret ${privateName}" }',
    "lua": 'local privateName = 42\nlocal privateText = [=[secret]=]\n',
    "nasm": 'section .data\nprivateName: dq 42\nsection .text\nmov rax, privateName\n',
    "swift": 'let privateName = 42\nlet privateText = "secret \\(privateName)"\n',
    "ruby": 'privateName = 42\nprivateText = "secret #{privateName}"\n',
    "dart": 'void main() { var privateName = 42; var privateText = "secret ${privateName}"; }',
    "r": 'privateName <- 42\nprivateText <- "secret"\n',
    "nix": '{ privateName = 42; privateText = "secret ${privateValue}"; }',
    "gdscript": 'extends Node\nvar privateName = 42\nvar privateText = "secret"\n',
    "vbnet": 'Module PrivateModule\nDim privateName As Integer = 42\nDim privateText As String = "secret"\nEnd Module\n',
    "vba": 'Sub PrivateMethod()\nDim privateName As Integer\nprivateName = 42\nEnd Sub\n',
}


@pytest.mark.parametrize("language,source", SOURCES.items())
@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_all_adapters_mask_payload_and_restore_exactly(language, source, strategy):
    tokens = CodeParser.tokenize(source, language)
    assert "".join(raw for raw, _, _ in tokens) == source
    assert any(raw == "42" and kind == TokenType.NUMBER for raw, kind, _ in tokens)
    session = PrivacySession("extended-code", strategy=strategy)
    engine = MaskingEngine()
    result = engine.mask_code(source, session.session_id, session.generator, session.forward_store,
                              session.reverse_store, language=language)
    assert "privateName" not in result.masked_text
    assert "secret" not in result.masked_text
    assert any(raw == "42" and kind == TokenType.NUMBER for raw, kind, _ in CodeParser.tokenize(result.masked_text, language))
    assert engine.unmask(result.masked_text, session.session_id, session.reverse_store,
                         strategy, strict=True).unmasked_text == source


SPECIAL_LITERALS = [
    ("bash", "cat <<'PRIVATE_END'\nsecret $privateName\nPRIVATE_END\n"),
    ("bash", 'cat <<PRIVATE_END\nsecret $privateName\nPRIVATE_END\n'),
    ("bash", 'cat <<FIRST <<-SECOND\nsecret $privateName\nFIRST\n\tsecret\n\tSECOND\n'),
    ("php", '<?php $privateText = <<<PRIVATE_END\nsecret $privateName\nPRIVATE_END;\n'),
    ("php", "<?php $privateText = <<<'PRIVATE_END'\nsecret $privateName\nPRIVATE_END;\n"),
    ("powershell", '$privateText = @"\nsecret $privateName\n"@\n'),
    ("powershell", "$privateText = @'\nsecret $privateName\n'@\n"),
    ("csharp", 'var privateText = $$"""secret {{privateName}}""";'),
    ("csharp", 'var privateText = @"secret ""quoted""";'),
    ("kotlin", 'val privateText = """secret ${privateName}"""'),
    ("swift", 'let privateText = #"secret \\#(privateName)"#'),
    ("ruby", 'privateText = %Q{secret #{privateName}}'),
    ("ruby", 'privateText = %q{secret {privateName}}'),
    ("ruby", 'privateText = <<~PRIVATE_END\nsecret #{privateName}\n  PRIVATE_END\n'),
    ("ruby", 'privateText = [<<FIRST, <<~SECOND]\nsecret #{privateName}\nFIRST\n  secret\n  SECOND\n'),
    ("r", 'privateText <- r"---(secret "quoted")---"'),
    ("nix", "{ privateText = ''secret ${privateName} ''; }"),
    ("lua", 'local privateText = [==[secret "quoted"]==]'),
    ("dart", 'var privateText = r"secret $privateName";'),
    ("gdscript", 'var privateText = """secret\nprivateName"""'),
    ("gdscript", '@export var privateName: int = 42\n@onready var privateNode = $PrivateNode/PrivateChild\n'),
    ("nasm", '%macro privateMacro 1\nmov r8, %1\njle .privateDone\n.privateDone:\n%endmacro\n'),
    ("vbnet", 'Module PrivateModule\nDim privateDate As Date = #10/22/2026#\nDim privateNumber As Integer = &H2A\nEnd Module\n'),
    ("powershell", '$script:privateName=42\n"$script:privateName"\n${script:privateName}\n'),
    ("bash", 'privateName=42\nprintf "%s" "${privateName:-secret}"'),
    ("bash", 'privateName=secret\nprintf "%s" "${privateName//secret/replacement}"'),
    ("vbnet", 'Module PrivateModule\nDim privateName As Integer = 42\nDim privateText As String = $"secret {privateName}"\nEnd Module\n'),
    ("ruby", 'privateName =~ /foo"bar/\n'),
    ("ruby", '__END__\nsecret "unterminated\n'),
    ("lua", 'local privateName = 0x1.fp2\n'),
    ("swift", 'let privateName = 0x1.fp2\n'),
    ("php", '<?php $privateName = 42; echo "${privateName}"; ?>'),
    ("nasm", 'cvtsi2ss xmm0, eax\n'),
    ("nasm", '%macro privateMacro 1\nmov eax, %1\n%endmacro\nprivateMacro eax\n'),
    ("nasm", '%define privateMacro cvtsi2ss\nprivateMacro xmm0, eax\n'),
    ("vbnet", 'Module PrivateModule\nDim privateName As Integer = 42\nDim privateXml = <tag attr="secret">don\'t leak secret<%= privateName %></tag>\nEnd Module\n'),
    ("vbnet", 'Module PrivateModule\nDim privateXml = <tag attr="secret"><%= "secret %>" %></tag>\nEnd Module\n'),
]


@pytest.mark.parametrize("language,source", SPECIAL_LITERALS)
@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
def test_delimiter_and_interpolation_variants(language, source, strategy):
    tokens = CodeParser.tokenize(source, language)
    assert "".join(raw for raw, _, _ in tokens) == source
    session = PrivacySession("extended-literals", strategy=strategy)
    engine = MaskingEngine()
    result = engine.mask_code(source, session.session_id, session.generator, session.forward_store,
                              session.reverse_store, language=language)
    assert "secret" not in result.masked_text
    CodeParser.tokenize(result.masked_text, language)
    assert engine.unmask(result.masked_text, session.session_id, session.reverse_store,
                         strategy, strict=True).unmasked_text == source


@pytest.mark.parametrize("language,source", [
    ("lua", 'local x = [==[secret'), ("powershell", '$x = @"\nsecret'),
    ("php", '<?php $x = <<<END\nsecret'), ("ruby", 'x = %Q{secret'),
    ("r", 'x <- r"---(secret'), ("nix", "{ x = ''secret; }"),
    ("kotlin", 'val x = "secret ${privateName"'),
])
def test_unterminated_constructs_fail_closed(language, source):
    with pytest.raises(ValueError, match="[Uu]nterminated"):
        extended_code.tokenize(source, language)


def test_kotlin_and_swift_nested_comments_hide_all_payload():
    for language in ("kotlin", "swift"):
        tokens = CodeParser.tokenize('/* secret /* nested */ secret */ val privateName = 42', language)
        assert tokens[0][1] == TokenType.LITERAL
        assert tokens[0][0] == '/* secret /* nested */ secret */'


@pytest.mark.parametrize("language,name", [("csharp", "@privateName"), ("csharp", r"\u0070rivateName"), ("csharp", r"private\u004eame"), ("kotlin", "`privateName`"), ("r", "`privateName`"), ("vbnet", "[privateName]")])
def test_escaped_names_are_single_identifiers(language, name):
    tokens = CodeParser.tokenize(name + " = 42", language)
    assert tokens[0] == (name, TokenType.IDENTIFIER, "identifier")


@pytest.mark.parametrize("language,source,names", [
    ("csharp", 'class PrivateType { int field = 42; int value = field; }', {"field", "value"}),
    ("kotlin", 'fun main() { val by = 42; val get = by; val set = get; val field = set }', {"by", "get", "set", "field"}),
])
def test_contextual_words_in_variable_positions_are_maskable(language, source, names):
    tokens = CodeParser.tokenize(source, language)
    assert all(kind == TokenType.IDENTIFIER for raw, kind, _ in tokens if raw in names)


def test_contextual_words_in_accessor_positions_remain_grammar():
    csharp = CodeParser.tokenize('class PrivateType { int privateName { get; set; } }', 'csharp')
    assert all(kind == "keyword" for raw, _, kind in csharp if raw in {"get", "set"})
    kotlin = CodeParser.tokenize('val privateName: Int\n    get() = field\n', 'kotlin')
    assert all(kind == "keyword" for raw, _, kind in kotlin if raw in {"get", "field"})


@pytest.mark.parametrize("language,source,count", [
    ("powershell", '$script:privateName=42\n"$script:privateName"\n${script:privateName}\n"${script:privateName}"', 4),
    ("bash", 'privateName=42\nprintf "%s" "${privateName:-secret}" "${privateName}"', 3),
    ("php", '<?php $privateName = 42; echo "${privateName}"; ?>', 2),
    ("vbnet", 'Module PrivateModule\nDim privateName = 42\nDim privateText = $"secret {privateName}"\nEnd Module\n', 2),
])
def test_scoped_and_braced_expansion_bindings_are_identical(language, source, count):
    session = PrivacySession("binding-proof")
    engine = MaskingEngine()
    result = engine.mask_code(source, session.session_id, session.generator, session.forward_store,
                              session.reverse_store, language=language)
    original_names = [raw for raw, kind, _ in CodeParser.tokenize(source, language) if kind == TokenType.IDENTIFIER]
    masked_names = [raw for raw, kind, _ in CodeParser.tokenize(result.masked_text, language) if kind == TokenType.IDENTIFIER]
    aliases = [masked for original, masked in zip(original_names, masked_names, strict=True) if original == 'privateName']
    assert len(aliases) == count
    assert len(set(aliases)) == 1
    if language == 'powershell':
        assert result.masked_text.count('script:') == count
    assert engine.unmask(result.masked_text, session.session_id, session.reverse_store, strict=True).unmasked_text == source


@pytest.mark.parametrize("language", ['lua', 'swift'])
def test_hexadecimal_float_is_preserved_as_one_number(language):
    tokens = CodeParser.tokenize('privateName = 0x1.fp2', language)
    assert ('0x1.fp2', TokenType.NUMBER, 'number') in tokens


def test_nasm_unlisted_instruction_field_is_structural():
    tokens = CodeParser.tokenize('cvtsi2ss xmm0, eax\n', 'nasm')
    assert tokens[0] == ('cvtsi2ss', TokenType.GRAMMAR, 'keyword')


@pytest.mark.parametrize('strategy', list(SurrogateStrategy))
@pytest.mark.parametrize('source', [
    '%macro privateMacro 1\nmov eax, %1\n%endmacro\nprivateMacro eax\n',
    '%define privateMacro cvtsi2ss\nprivateMacro xmm0, eax\n',
])
def test_nasm_macro_definition_and_instruction_field_use_one_alias(strategy, source, tmp_path):
    session = PrivacySession('nasm-macros', strategy=strategy)
    engine = MaskingEngine()
    original = CodeParser.tokenize(source, 'nasm')
    assert sum(raw == 'privateMacro' and kind == TokenType.IDENTIFIER for raw, kind, _ in original) == 2
    result = engine.mask_code(source, session.session_id, session.generator, session.forward_store,
                              session.reverse_store, language='nasm')
    masked = CodeParser.tokenize(result.masked_text, 'nasm')
    names = [new[0] for old, new in zip(original, masked, strict=True) if old[0] == 'privateMacro']
    assert len(names) == 2 and len(set(names)) == 1
    assert 'privateMacro' not in result.masked_text
    assert engine.unmask(result.masked_text, session.session_id, session.reverse_store, strategy, strict=True).unmasked_text == source
    if os.environ.get('SECURE_GATEWAY_NATIVE_PARSERS') == '1':
        nasm = os.environ.get('SECURE_GATEWAY_NASM') or shutil.which('nasm')
        assert nasm, 'Native-validation gate requires NASM (or SECURE_GATEWAY_NASM)'
        for index, text in enumerate((source, result.masked_text)):
            file = tmp_path / f'macro-{index}.asm'
            file.write_text('bits 64\n' + text, encoding='utf-8')
            completed = subprocess.run([nasm, '-f', 'elf64', '-o', str(tmp_path / f'macro-{index}.o'), str(file)], capture_output=True, text=True, timeout=30)
            assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(os.environ.get('SECURE_GATEWAY_NATIVE_PARSERS') != '1', reason='Enable the explicit native-validation gate')
@pytest.mark.parametrize('strategy', list(SurrogateStrategy))
@pytest.mark.parametrize('source', [SOURCES['nasm'], 'cvtsi2ss xmm0, eax\n'])
def test_native_nasm_assembles_common_and_conversion_instruction_fixtures(strategy, source, tmp_path):
    nasm = os.environ.get('SECURE_GATEWAY_NASM') or shutil.which('nasm')
    assert nasm, 'Native-validation gate requires NASM (or SECURE_GATEWAY_NASM)'
    session = PrivacySession('nasm-native', strategy=strategy)
    result = MaskingEngine().mask_code(source, session.session_id, session.generator,
                                     session.forward_store, session.reverse_store, language='nasm')
    for index, text in enumerate((source, result.masked_text)):
        file = tmp_path / f'native-{index}.asm'
        file.write_text('bits 64\n' + text, encoding='utf-8')
        completed = subprocess.run([nasm, '-f', 'elf64', '-o', str(tmp_path / f'native-{index}.o'), str(file)], capture_output=True, text=True, timeout=30)
        assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize('strategy', list(SurrogateStrategy))
@pytest.mark.parametrize('source', [
    '%imacro privateMacro 1\nmov eax, %1\n%endmacro\nPRIVATEMACRO eax\n',
    '%idefine privateMacro cvtsi2ss\nPRIVATEMACRO xmm0, eax\n',
])
def test_nasm_case_insensitive_macros_keep_native_equivalent_aliases(strategy, source, tmp_path):
    original = CodeParser.tokenize(source, 'nasm')
    name_tokens = [token for token in original if token[0].lower() == 'privatemacro']
    assert len(name_tokens) == 2
    assert all(kind == 'case_insensitive_identifier' for _, _, kind in name_tokens)
    session = PrivacySession('nasm-insensitive-macros', strategy=strategy)
    engine = MaskingEngine()
    result = engine.mask_code(source, session.session_id, session.generator, session.forward_store,
                              session.reverse_store, language='nasm')
    masked = CodeParser.tokenize(result.masked_text, 'nasm')
    names = [new[0] for old, new in zip(original, masked, strict=True) if old[0].lower() == 'privatemacro']
    assert len(names) == 2 and names[0] != names[1]
    assert names[0].lower() == names[1].lower()
    assert engine.unmask(result.masked_text, session.session_id, session.reverse_store, strategy, strict=True).unmasked_text == source
    if os.environ.get('SECURE_GATEWAY_NATIVE_PARSERS') == '1':
        nasm = os.environ.get('SECURE_GATEWAY_NASM') or shutil.which('nasm')
        assert nasm, 'Native-validation gate requires NASM (or SECURE_GATEWAY_NASM)'
        for index, text in enumerate((source, result.masked_text)):
            file = tmp_path / f'insensitive-{index}.asm'
            file.write_text('bits 64\n' + text, encoding='utf-8')
            completed = subprocess.run([nasm, '-f', 'elf64', '-o', str(tmp_path / f'insensitive-{index}.o'), str(file)], capture_output=True, text=True, timeout=30)
            assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(os.environ.get("SECURE_GATEWAY_NATIVE_PARSERS") != "1", reason="Enable the explicit native-validation gate")
@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("expansion", [
    '"${privateName//secret/replacement}"',
    '${privateName//secret/replacement}',
    '"${privateName%/*}"',
    '"${privateName%%/*}"',
])
def test_bash_parameter_patterns_are_not_source_comments(expansion, strategy, tmp_path):
    source = 'privateName=secret\nprintf "%s" ' + expansion + '\n'
    session = PrivacySession('shell-patterns', strategy=strategy)
    engine = MaskingEngine()
    result = engine.mask_code(source, session.session_id, session.generator, session.forward_store,
                              session.reverse_store, language='bash')
    original_names = [raw for raw, kind, _ in CodeParser.tokenize(source, 'bash') if kind == TokenType.IDENTIFIER]
    masked_names = [raw for raw, kind, _ in CodeParser.tokenize(result.masked_text, 'bash') if kind == TokenType.IDENTIFIER]
    references = [masked for original, masked in zip(original_names, masked_names, strict=True) if original == 'privateName']
    assert len(references) == 2 and len(set(references)) == 1
    assert 'secret' not in result.masked_text
    assert engine.unmask(result.masked_text, session.session_id, session.reverse_store, strategy, strict=True).unmasked_text == source
    bash = shutil.which('bash')
    if os.name == 'nt':
        bash = str(Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Git/bin/bash.exe')
    assert bash and Path(bash).is_file(), 'Native shell pattern validation requires Bash'
    for index, text in enumerate((source, result.masked_text)):
        file = tmp_path / f'pattern-{index}.sh'
        file.write_text(text, encoding='utf-8')
        completed = subprocess.run([bash, '-n', str(file)], capture_output=True, text=True, timeout=30)
        assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize("language,source", [
    ("bash", 'privateName=42\nprintf "%s" "$privateName/path"'),
    ("powershell", '$privateName = 42; "$privateName/suffix"'),
    ("dart", 'var privateName = 42; var privateText = "$privateName!suffix";'),
])
def test_interpolation_adjacent_content_does_not_merge_alias_names(language, source):
    session = PrivacySession("adjacent-content")
    engine = MaskingEngine()
    result = engine.mask_code(source, session.session_id, session.generator, session.forward_store,
                              session.reverse_store, language=language)
    identifiers = [raw for raw, kind, _ in CodeParser.tokenize(result.masked_text, language) if kind == TokenType.IDENTIFIER]
    # One binding and one string interpolation must use precisely the same alias.
    assert identifiers.count(identifiers[0]) == 2
    assert engine.unmask(result.masked_text, session.session_id, session.reverse_store,
                         strict=True).unmasked_text == source


@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("language", ["bash", "powershell", "csharp"])
def test_native_syntax_parsers_accept_masked_fixtures(language, strategy, tmp_path):
    """Parse only; never execute the original or masked source."""
    executable = shutil.which({"bash": "bash", "powershell": "pwsh", "csharp": "dotnet"}[language])
    if language == "bash" and os.name == "nt":
        candidate = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe"
        executable = str(candidate) if candidate.is_file() else None
    if language == "powershell" and not executable:
        executable = shutil.which("powershell")
    if not executable:
        pytest.skip(f"Native {language} parser is not installed")
    source = SOURCES[language]
    if language == "csharp":
        source = 'class PrivateType { int privateName = 42; string privateText = $$"""secret {{42}}"""; }'
    session = PrivacySession("native-extended", strategy=strategy)
    result = MaskingEngine().mask_code(source, session.session_id, session.generator,
                                      session.forward_store, session.reverse_store, language=language)
    file = tmp_path / {"bash": "fixture.sh", "powershell": "fixture.ps1", "csharp": "fixture.cs"}[language]
    file.write_text(result.masked_text, encoding="utf-8")
    environment = os.environ.copy()
    if language == "bash":
        command = [executable, "-n", str(file)]
    elif language == "powershell":
        environment["SECURE_GATEWAY_PARSE_FIXTURE"] = str(file)
        command = [executable, "-NoProfile", "-NonInteractive", "-Command",
                   '$errors = $null; [void][System.Management.Automation.Language.Parser]::ParseFile($env:SECURE_GATEWAY_PARSE_FIXTURE, [ref]$null, [ref]$errors); if ($errors.Count) { $errors | Out-String | Write-Output; exit 1 }']
    else:
        root = Path(executable).resolve().parent
        compilers = sorted(root.glob("sdk/*/Roslyn/bincore/csc.dll"))
        references = sorted(root.glob("packs/Microsoft.NETCore.App.Ref/*/ref/net*/System.Runtime.dll"))
        if not compilers or not references:
            pytest.skip(".NET SDK Roslyn compiler/reference pack is not installed")
        command = [executable, str(compilers[-1]), "/nologo", "/target:library",
                   f"/out:{tmp_path / 'fixture.dll'}", f"/reference:{references[-1]}", str(file)]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", env=environment, timeout=30)
    assert completed.returncode == 0, completed.stdout + completed.stderr


def _native_vb_compile(source, tmp_path, basename):
    dotnet = shutil.which('dotnet')
    assert dotnet, 'Native XML validation requires the .NET SDK'
    root = Path(dotnet).resolve().parent
    compilers = sorted(root.glob('sdk/*/Roslyn/bincore/vbc.dll'))
    references = sorted(root.glob('packs/Microsoft.NETCore.App.Ref/*/ref/net*/Microsoft.VisualBasic.dll'))
    assert compilers and references, 'Native XML validation requires VB compiler/reference packs'
    reference_directory = references[-1].parent
    file = tmp_path / f'{basename}.vb'
    file.write_text(source, encoding='utf-8')
    command = [dotnet, str(compilers[-1]), '/nologo', '/noconfig', '/nostdlib+', '/target:library', '/define:_MYTYPE="Empty"',
               f'/out:{tmp_path / (basename + ".dll")}', f'/vbruntime:{references[-1]}',
               '/imports:System,System.Xml.Linq,Microsoft.VisualBasic',
               *[f'/reference:{reference}' for reference in reference_directory.glob('*.dll')], str(file)]
    completed = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.mark.skipif(os.environ.get("SECURE_GATEWAY_NATIVE_PARSERS") != "1", reason="Enable the explicit native-validation gate")
@pytest.mark.parametrize("strategy", list(SurrogateStrategy))
@pytest.mark.parametrize("language,source", [*SOURCES.items(), *SPECIAL_LITERALS])
def test_tree_sitter_grammar_gate(language, source, strategy, tmp_path):
    """The opt-in gate fails if a required parser or grammar is unavailable."""
    import tree_sitter_language_pack

    parser = tree_sitter_language_pack.get_parser("vb" if language in {"vbnet", "vba"} else language)
    original_parse_source = "Module ValidationModule\n" + source + "End Module\n" if language == "vba" else source
    original_tree = parser.parse(original_parse_source.encode("utf-8"))
    if language == 'vbnet' and '<tag' in source:
        # The community VB tree-sitter grammar omits XML literals entirely.
        # Use Roslyn to validate the actual source and its masked counterpart.
        _native_vb_compile(source, tmp_path, 'original-xml')
        session = PrivacySession('native-xml', strategy=strategy)
        result = MaskingEngine().mask_code(source, session.session_id, session.generator,
                                         session.forward_store, session.reverse_store, language=language)
        _native_vb_compile(result.masked_text, tmp_path, 'masked-xml')
        return
    if language == "bash" and source.count("<<") > 1:
        # The bundled tree-sitter Bash grammar rejects valid queued heredocs.
        # Verify this construct using Bash's authoritative parser instead.
        bash = shutil.which("bash")
        if os.name == "nt":
            bash = str(Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe")
        assert bash and Path(bash).is_file(), "The native-validation gate requires Bash"
        session = PrivacySession("queued-native", strategy=strategy)
        masked = MaskingEngine().mask_code(source, session.session_id, session.generator,
                                           session.forward_store, session.reverse_store, language=language).masked_text
        for index, text in enumerate((source, masked)):
            file = tmp_path / f"queued-{index}.sh"
            file.write_text(text, encoding="utf-8")
            result = subprocess.run([bash, "-n", str(file)], capture_output=True, text=True, timeout=30)
            assert result.returncode == 0, result.stderr
        return
    assert not original_tree.root_node.has_error, f"Original {language} fixture is invalid: {original_tree.root_node}"
    session = PrivacySession("grammar-extended", strategy=strategy)
    result = MaskingEngine().mask_code(source, session.session_id, session.generator,
                                      session.forward_store, session.reverse_store, language=language)
    masked_parse_source = "Module ValidationModule\n" + result.masked_text + "End Module\n" if language == "vba" else result.masked_text
    masked_tree = parser.parse(masked_parse_source.encode("utf-8"))
    assert not masked_tree.root_node.has_error, f"Masked {language} syntax error: {result.masked_text}\n{masked_tree.root_node}"
