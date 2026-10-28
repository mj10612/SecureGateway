"""Conservative, local lexical adapters for additional source languages.

These scanners preserve source spans. They do not evaluate source, expand shell
variables, or load language packages. Unsupported literal forms fail closed.
"""

from __future__ import annotations

import re
import unicodedata

from secure_gateway.models import TokenType

Token = tuple[str, TokenType, str]

LANGUAGE_KEYWORDS = {
    "bash": set("if then else elif fi case esac for select while until do done in function time coproc break continue return export readonly local declare typeset unset shift source eval exec trap set test true false".split()),
    "csharp": set("abstract as base bool break byte case catch char checked class const continue decimal default delegate do double else enum event explicit extern false finally fixed float for foreach goto if implicit in int interface internal is lock long namespace new null object operator out override params private protected public readonly ref return sbyte sealed short sizeof stackalloc static string struct switch this throw true try typeof uint ulong unchecked unsafe ushort using virtual void volatile while add alias and ascending async await by descending dynamic equals file from get global group init into join let managed nameof not notnull on or orderby partial record remove required scoped select set unmanaged value var when where with yield".split()),
    "powershell": set("begin break catch class clean continue data define do dynamicparam else elseif end enum exit filter finally for foreach from function if in param process return switch throw trap try until using var while workflow parallel sequence configuration true false null".split()),
    "php": set("abstract and array as break callable case catch class clone const continue declare default die do echo else elseif empty enddeclare endfor endforeach endif endswitch endwhile enum eval exit extends final finally fn for foreach function global goto if implements include include_once instanceof insteadof interface isset list match namespace new null or print private protected public readonly require require_once return static switch throw trait try unset use var while xor yield true false".split()),
    "kotlin": set("as break class continue do else false for fun if in interface is null object package return super this throw true try typealias typeof val var when while by catch constructor delegate dynamic field file finally get import init param property receiver set setparam where actual abstract annotation companion const crossinline data enum expect external final infix inline inner internal lateinit noinline open operator out override private protected public reified sealed suspend tailrec vararg value".split()),
    "lua": set("and break do else elseif end false for function goto if in local nil not or repeat return then true until while".split()),
    "nasm": set("section segment global extern bits default org equ times db dw dd dq dt do dy dz resb resw resd resq incbin align alignb byte word dword qword tword oword yword zword rel abs strict near far short ptr lock rep repe repne mov lea push pop add sub mul imul div idiv xor or and not neg inc dec cmp test jmp je jne jz jnz ja jb call ret leave nop syscall int rax rbx rcx rdx rsi rdi rsp rbp eax ebx ecx edx esi edi esp ebp ax bx cx dx al ah bl bh cl ch dl dh".split()),
    "swift": set("associatedtype class deinit enum extension fileprivate func import init inout internal let open operator private precedencegroup protocol public rethrows static struct subscript typealias var break case catch continue default defer do else fallthrough for guard if in repeat return throw switch where while as Any catch false is nil rethrows self Self super throw throws true try actor async await borrowing consuming distributed dynamic final get indirect infix lazy left mutating nonisolated nonmutating optional override package postfix precedence prefix required right set some Type unowned weak willSet didSet".split()),
    "ruby": set("BEGIN END alias and begin break case class def defined do else elsif end ensure false for if in module next nil not or redo rescue retry return self super then true undef unless until when while yield __FILE__ __LINE__ __ENCODING__".split()),
    "dart": set("abstract as assert async await base break case catch class const continue covariant default deferred do dynamic else enum export extends extension external factory false final finally for Function get hide if implements import in interface is late library mixin new null of on operator part required rethrow return sealed set show static super switch sync this throw true try typedef var void when while with yield".split()),
    "r": set("if else repeat while function for in next break TRUE FALSE NULL Inf NaN NA NA_integer_ NA_real_ NA_complex_ NA_character_".split()),
    "nix": set("assert else if in inherit let or rec then with builtins true false null".split()),
    "gdscript": set("and as assert await break breakpoint class class_name const continue elif else enum extends false for func if in is match namespace not null or pass preload return self signal static super true var void when while yield int float bool String Vector2 Vector3 Array Dictionary".split()),
    "vbnet": set("addhandler addressof alias and andalso as boolean byref byte byval call case catch cbool cbyte cchar cdate cdbl cdec char cint class clng cobj const continue csbyte cshort csng cstr ctype cuint culng cushort date decimal declare default delegate dim directcast do double each else elseif end endif enum erase error event exit false finally for friend function get gettype getxmlnamespace global gosub goto handles if implements imports in inherits integer interface is isnot let lib like long loop me mod module mustinherit mustoverride mybase myclass namespace narrowing new next not nothing notinheritable notoverridable object of on operator option optional or orelse overloads overridable overrides paramarray partial private property protected public raiseevent readonly redim rem removehandler resume return sbyte select set shadows shared short single static step stop string structure sub synclock then throw to true try trycast typeof uinteger ulong ushort using variant wend when while widening with withevents writeonly xor async await iterator yield".split()),
    "vba": set("and as attribute boolean byref byte byval call case class const currency date declare defbool defbyte defcur defdate defdbl defdec defint deflng defobj defsng defstr defvar dim do double each else elseif empty end enum eqv erase error event exit false for friend function get global gosub goto if imp implements in input integer is let lib like line load lock long loop lset me mid mod new next not nothing null object on open option optional or output paramarray preserve print private property public put raiseevent random randomize read redim rem reset resume return rset seek select set shared single static step stop string sub then to true type typeof unload unlock until variant wend while width with withevents write xor".split()),
}
LANGUAGE_KEYWORDS["nasm"].update("adc sbb sal sar shl shr rol ror rcl rcr bsf bsr bswap bt btc btr bts cdq cdqe cqo clc cld cli cmc cpuid cwd cwde hlt in out lahf sahf lzcnt popcnt pushf pushfq popf popfq rdtsc rdtscp stc std sti stosb stosw stosd stosq lodsb lodsw lodsd lodsq movsb movsw movsd movsq cmpsb cmpsw cmpsd cmpsq scasb scasw scasd scasq movsx movsxd movzx movaps movups movapd movupd movdqa movdqu movss addsd addss addps addpd subsd subss subps subpd mulsd mulss mulps mulpd divsd divss divps divpd pxor xorps xorpd pand por paddb paddw paddd paddq syscall sysenter sysexit sysret ud2 xchg xadd cmpxchg cmpxchg8b cmpxchg16b imul jle jl jge jg jbe jae jc jnc jo jno js jns jp jnp loop loope loopne jrcxz jecxz sete setne setz setnz setg setl setge setle seta setae setb setbe cmove cmovne cmovg cmovl cmovge cmovle cmova cmovae cmovb cmovbe vzeroupper vzeroall vaddps vaddpd vsubps vsubpd vmulps vmulpd vdivps vdivpd vmovaps vmovups vmovdqa vmovdqu vxorps vpxor".split())
_GDSCRIPT_ANNOTATIONS = set("abstract export export_category export_group export_subgroup export_enum export_exp_easing export_file export_dir export_global_file export_global_dir export_multiline export_placeholder export_range export_color_no_alpha export_node_path export_flags export_flags_2d_physics export_flags_2d_render export_flags_2d_navigation export_flags_3d_physics export_flags_3d_render export_flags_3d_navigation export_storage export_custom icon onready rpc static_unload tool warning_ignore warning_ignore_start warning_ignore_restore".split())
ALIASES = {
    "sh": "bash", "shell": "bash", "cs": "csharp", "c#": "csharp",
    "ps1": "powershell", "pwsh": "powershell", "kt": "kotlin", "kts": "kotlin",
    "asm-nasm": "nasm", "rb": "ruby", "rscript": "r",
    "gd": "gdscript", "vb": "vbnet", "vb.net": "vbnet", "bas": "vba",
}
_CASE_INSENSITIVE = {"powershell", "nasm", "vbnet", "vba"}
_NUMBER = re.compile(r"(?:0[xX](?:[0-9a-fA-F_]+(?:\.[0-9a-fA-F_]*)?|\.[0-9a-fA-F_]+)(?:[pP][+-]?\d[\d_]*)?|0[bB][01_]+|0[oO][0-7_]+|(?:\d[\d_]*(?:\.\d[\d_]*)?|\.\d[\d_]*)(?:[eE][+-]?\d[\d_]*)?)[a-zA-Z0-9_]*")
_ESCAPE = {"powershell": "`", "vbnet": "", "vba": "", "nix": "\\"}
_CONTEXTUAL = {
    "csharp": set("add alias and ascending async await by descending dynamic equals file from get global group init into join let managed nameof not notnull on or orderby partial record remove required scoped select set unmanaged value var when where with yield".split()),
    "kotlin": {"by", "get", "set", "field"},
}


def _grammar(raw: str, kind: str = "syntax") -> Token:
    return raw, TokenType.GRAMMAR, kind


def _literal(raw: str, prefix: int = 0, suffix: int = 0) -> Token:
    return raw, TokenType.LITERAL, f"literal:{prefix}:{suffix}"


def _payload(raw: str) -> list[Token]:
    """Keep punctuation boundaries between content aliases and expansions."""
    chunks: list[Token] = []
    position = 0
    while position < len(raw):
        start = position
        if raw[position] in {"\\", "`"} and position + 1 < len(raw):
            escape = re.compile(r"\\(?:u\{[0-9a-fA-F]+\}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|x[0-9a-fA-F]{1,4}|.)|`.", re.DOTALL).match(raw, position)
            assert escape is not None
            position += len(escape[0])
            chunks.append(_grammar(raw[start:position]))
            continue
        word = raw[position].isalnum() or raw[position] == "_" or unicodedata.category(raw[position]).startswith("M")
        position += 1
        while position < len(raw) and (raw[position].isalnum() or raw[position] == "_" or unicodedata.category(raw[position]).startswith("M")) == word and raw[position] not in {"\\", "`"}:
            position += 1
        chunks.append(_literal(raw[start:position]) if word else _grammar(raw[start:position]))
    return chunks


def _identifier_end(code: str, start: int, language: str) -> int:
    end = start
    initial = True
    while end < len(code):
        if language == "bash" and code.startswith("\\\n", end):
            # Shell line continuations are removed before recognizing a name,
            # including inside $name expansions. Keep the raw source span.
            end += 2
            continue
        character = code[end]
        valid = character == "_" or (character.isidentifier() if initial else ("a" + character).isidentifier())
        valid |= language == "r" and character == "."
        valid |= language == "php" and ord(character) >= 128
        valid |= language == "swift" and unicodedata.category(character) in {"So", "Sk"}
        valid |= language == "csharp" and end > start and unicodedata.category(character) == "Cf"
        valid |= language in {"powershell", "nix"} and end > start and character in "-'"
        if not valid:
            break
        end += 1
        initial = False
    if initial:
        return start
    if language == "ruby" and end > start and end < len(code) and code[end] in "!?":
        end += 1
    return end


def _csharp_escaped_identifier(code: str, start: int) -> int:
    position = start + (code[start:start + 1] == "@")
    initial = position
    while position < len(code):
        character = code[position]
        end = position + 1
        if character == "\\":
            escape = re.compile(r"\\(?:u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8})").match(code, position)
            if escape is None:
                break
            number = int(escape[0][2:], 16)
            if number > 0x10FFFF:
                raise ValueError("Invalid C# identifier escape")
            character = chr(number)
            end = position + len(escape[0])
        valid = character.isidentifier() if position == initial else ("a" + character).isidentifier() or unicodedata.category(character) == "Cf"
        if not valid:
            break
        position = end
    return position if position > initial else start


def _variable(code: str, start: int, language: str) -> tuple[list[Token], int] | None:
    """Share variable name spans across quoted, plain and braced expansions."""
    if not code.startswith("$", start) or language not in {"powershell", "bash", "php"}:
        return None
    braced = code.startswith("${", start)
    position = start + (2 if braced else 1)
    chunks = [_grammar(code[start:position])]
    if language == "bash" and code[position:position + 1] and code[position] in "?#$!-@*0123456789":
        end = position + 1
        if code[position].isdigit():
            while end < len(code) and code[end].isdigit() and braced:
                end += 1
        if not braced or code[end:end + 1] == "}":
            end += int(braced)
            return [_grammar(code[start:end])], end
    if language == "bash" and braced and code[position:position + 1] in {"#", "!"}:
        chunks.append(_grammar(code[position]))
        position += 1
    scope = None
    if language == "powershell" and (scope := re.compile(r"(?i:script|global|local|private|using|env):").match(code, position)):
        chunks.append(_grammar(scope[0]))
        position += len(scope[0])
    name_start = position
    if language == "bash":
        position = _identifier_end(code, position, language)
    else:
        while position < len(code) and (code[position] == "_" or (code[position].isidentifier() if position == name_start else ("a" + code[position]).isidentifier())):
            position += 1
    if position == name_start:
        return None
    chunks.append((code[name_start:position], TokenType.IDENTIFIER, "identifier"))
    if braced:
        end = _balanced_end(code, position, "{", "}", language)
        tail = code[position:end]
        if tail:
            if language in {"powershell", "php"}:
                # Braced variables permit punctuation in their names. Keep it
                # within the same name token, not separate expansion payload.
                chunks[-1] = (code[name_start:end], TokenType.IDENTIFIER, "identifier")
            elif operator := re.match(r"(?::?[-+=?]|%%?|##?|//?|\^\^?|,,?)", tail):
                chunks.append(_grammar(operator[0]))
                chunks.extend(_interpolated_body(tail[len(operator[0]):], language, True))
            elif tail.startswith("["):
                chunks.extend(tokenize(tail, language))
            elif tail.startswith(":"):
                chunks.extend(tokenize(tail, language))
            else:
                raise ValueError("Unsupported shell parameter expansion")
        chunks.append(_grammar("}"))
        position = end + 1
    if language == "powershell" and (scope is None or scope[0].lower() != "env:"):
        # These are language constants, not variables named after private data.
        # Variable scopes retain them; environment entries are ordinary names.
        for index, (raw, kind, _) in enumerate(chunks):
            if kind == TokenType.IDENTIFIER and raw.lower() in {"true", "false", "null"}:
                chunks[index] = _grammar(raw, "keyword")
    return chunks, position


def _balanced_end(code: str, start: int, opening: str, closing: str, language: str) -> int:
    """Find an interpolation close while skipping quoted/commented braces."""
    depth = 1
    position = start
    while position < len(code):
        character = code[position]
        if character in "\"'`":
            _, position = _quoted(code, position, character, language, False)
            continue
        if language in {"csharp", "php", "kotlin", "swift", "dart", "nix"} and code.startswith("/*", position):
            position = _block_end(code, position, "/*", "*/", language in {"kotlin", "swift"})
            continue
        if language in {"csharp", "php", "kotlin", "swift", "dart"} and code.startswith("//", position):
            newline = code.find("\n", position)
            position = newline if newline >= 0 else len(code)
            continue
        if character == opening:
            depth += 1
        elif character == closing:
            depth -= 1
            if depth == 0:
                return position
        position += 1
    raise ValueError("Unterminated source interpolation")


def _block_end(code: str, start: int, opening: str, closing: str, nested: bool) -> int:
    position = start + len(opening)
    depth = 1
    while position < len(code):
        if code.startswith(closing, position):
            depth -= 1
            position += len(closing)
            if not depth:
                return position
        elif nested and code.startswith(opening, position):
            depth += 1
            position += len(opening)
        else:
            position += 1
    raise ValueError("Unterminated block comment")


def _quoted(code: str, start: int, delimiter: str, language: str, interpolate: bool,
            *, prefix_length: int = 0, raw: bool = False,
            interpolation_marker: str | None = None, closing: str | None = None) -> tuple[list[Token], int]:
    position = start + prefix_length + len(delimiter)
    content_start = position
    chunks: list[Token] = []
    escape = _ESCAPE.get(language, "\\")
    verbatim = language == "csharp" and "@" in code[start:position]
    closing = closing or delimiter
    regex_class = False
    while position < len(code):
        if language == "ruby" and delimiter == "/":
            if code[position] == "[":
                regex_class = True
            elif code[position] == "]":
                regex_class = False
        if language == "nix" and delimiter == "''" and code.startswith(("'''", "''${", "''\\"), position):
            position += 3
            continue
        if code.startswith(closing, position) and not regex_class:
            if (language in {"vbnet", "vba"} or verbatim) and code.startswith(delimiter * 2, position):
                position += len(delimiter) * 2
                continue
            end = position + len(closing)
            if not chunks:
                return [_literal(code[start:end], prefix_length + len(delimiter), len(closing))], end
            if position > content_start:
                chunks.extend(_payload(code[content_start:position]))
            chunks.append(_grammar(closing))
            return chunks, end
        if escape and code.startswith(escape, position) and not raw and not verbatim and not (language == "swift" and code.startswith("\\(", position)):
            position += 2
            continue
        marker = None
        if interpolate:
            variable = _variable(code, position, language)
            if variable:
                if not chunks:
                    chunks.append(_grammar(code[start:start + prefix_length + len(delimiter)]))
                if position > content_start:
                    chunks.extend(_payload(code[content_start:position]))
                variable_chunks, position = variable
                chunks.extend(variable_chunks)
                content_start = position
                continue
            if language in {"csharp", "vbnet"} and not raw and code.startswith("{{", position):
                position += 2
                continue
            candidates = {
                "kotlin": "${", "dart": "${", "php": "{$", "ruby": "#{",
                "nix": "${", "csharp": "{", "powershell": "$(", "swift": "\\(",
                "bash": "$(", "vbnet": "{",
            }
            marker = interpolation_marker or candidates.get(language)
            if marker and not code.startswith(marker, position):
                marker = None
        if marker:
            if not chunks:
                chunks.append(_grammar(code[start:start + prefix_length + len(delimiter)]))
            if position > content_start:
                chunks.extend(_payload(code[content_start:position]))
            opening = "(" if marker.endswith("(") else "{"
            expression_closing = ")" if opening == "(" else "}"
            expression_start = position + len(marker)
            if marker == "{$":
                expression_start -= 1
            end = _balanced_end(code, expression_start, opening, expression_closing, language)
            closing_count = len(marker) if language == "csharp" and raw else 1
            if not code.startswith(expression_closing * closing_count, end):
                raise ValueError("Invalid interpolation closing delimiter")
            chunks.append(_grammar(code[position:expression_start]))
            chunks.extend(tokenize(code[expression_start:end], language))
            chunks.append(_grammar(expression_closing * closing_count))
            position = content_start = end + closing_count
            continue
        if interpolate and language in {"kotlin", "dart", "php", "powershell", "bash"} and code[position] == "$":
            end = _identifier_end(code, position + 1, language)
            if end > position + 1:
                if not chunks:
                    chunks.append(_grammar(code[start:start + prefix_length + len(delimiter)]))
                if position > content_start:
                    chunks.extend(_payload(code[content_start:position]))
                chunks.append(_grammar("$"))
                chunks.append((code[position + 1:end], TokenType.IDENTIFIER, "identifier"))
                position = content_start = end
                continue
        position += 1
    raise ValueError("Unterminated string literal")


def _interpolated_body(body: str, language: str, interpolate: bool) -> list[Token]:
    """Scan a delimited body's expansion syntax without changing its quotes."""
    if not body:
        return []
    # Here-doc and here-string terminators must remain at a line boundary.
    # Preserve line separators as structural spans instead of aliasing them.
    if body.endswith("\n"):
        separator = "\r\n" if body.endswith("\r\n") else "\n"
        return [*_interpolated_body(body[:-len(separator)], language, interpolate), _grammar(separator, "whitespace")]
    if not interpolate:
        return _payload(body)
    chunks, _ = _quoted("\x00" + body + "\x00", 0, "\x00", language, True)
    if len(chunks) == 1:
        return _payload(body)
    return chunks[1:-1]


def _heredoc(code: str, start: int, language: str) -> tuple[list[Token], int] | None:
    """Recognize shell/PHP heredoc headers and retain the matching delimiters."""
    if language == "bash":
        match = re.compile(r"<<(-?)[ \t]*(['\"]?)([A-Za-z_]\w*)\2[ \t]*\r?\n").match(code, start)
        if not match:
            return None
        name = match[3]
        tab = "\t*" if match[1] else ""
        terminator = re.compile(rf"(?m)^{tab}{re.escape(name)}\r?$")
        quoted = bool(match[2])
    else:
        match = re.compile(r"<<<[ \t]*(['\"]?)([A-Za-z_]\w*)\1[ \t]*\r?\n").match(code, start)
        if not match:
            return None
        name = match[2]
        terminator = re.compile(rf"(?m)^[ \t]*{re.escape(name)}(?=;?[ \t]*(?:\r?$))")
        quoted = match[1] == "'"
    body_start = start + len(match[0])
    ending = terminator.search(code, body_start)
    if ending is None:
        raise ValueError("Unterminated heredoc")
    body = code[body_start:ending.start()]
    return [_grammar(match[0]), *_interpolated_body(body, language, not quoted), _grammar(ending[0])], ending.end()


def _ruby_percent(code: str, start: int) -> tuple[list[Token], int] | None:
    match = re.compile(r"%([qQwWiIrxs]?)([^\w\s])").match(code, start)
    if match is None:
        return None
    opening = match[2]
    closing = {"(": ")", "[": "]", "{": "}", "<": ">"}.get(opening, opening)
    position = start + len(match[0])
    content_start = position
    depth = 1
    while position < len(code):
        if code[position] == "\\":
            position += 2
            continue
        if opening != closing and code[position] == opening:
            depth += 1
        elif code[position] == closing:
            depth -= 1
            if not depth:
                end = position + 1
                if match[1] == "r":
                    while end < len(code) and code[end] in "imxounes":
                        end += 1
                body = code[content_start:position]
                chunks = [_grammar(match[0]), *_interpolated_body(body, "ruby", match[1] not in {"q", "w", "i", "s"}), _grammar(code[position:end])]
                return chunks, end
        position += 1
    raise ValueError("Unterminated Ruby percent literal")


def _queued_heredocs(code: str, start: int, language: str) -> tuple[list[Token], int] | None:
    """Retain header order when a command queues several here-documents."""
    newline = code.find("\n", start)
    if newline < 0:
        return None
    pattern = re.compile(r"<<([-~]?)[ \t]*(['\"`]?)([A-Za-z_]\w*)\2")
    cursor = start
    segment = start
    headers: list[tuple[str, bool, bool]] = []
    chunks: list[Token] = []
    while cursor < newline:
        match = pattern.match(code, cursor)
        if match:
            if language == "bash" and match[1] == "~":
                raise ValueError("Unsupported Bash heredoc indentation")
            chunks.extend(tokenize(code[segment:cursor], language))
            chunks.append(_grammar(match[0]))
            headers.append((match[3], bool(match[1]), match[2] != "'" if language == "ruby" else not match[2]))
            cursor = segment = match.end()
        elif code[cursor] in "\"'`":
            _, cursor = _quoted(code, cursor, code[cursor], language, False)
        else:
            cursor += 1
    if not headers:
        return None
    chunks.extend(tokenize(code[segment:newline + 1], language))
    cursor = newline + 1
    for name, indented, interpolate in headers:
        whitespace = ("[ \\t]*" if language == "ruby" else "\\t*") if indented else ""
        ending = re.compile(rf"(?m)^{whitespace}{re.escape(name)}\r?$").search(code, cursor)
        if ending is None:
            raise ValueError("Unterminated queued heredoc")
        chunks.extend(_interpolated_body(code[cursor:ending.start()], language, interpolate))
        chunks.append(_grammar(ending[0]))
        cursor = ending.end()
        if cursor < len(code) and code[cursor] == "\n":
            chunks.append(_grammar("\n", "whitespace"))
            cursor += 1
    return chunks, cursor


def _contextual_keywords(tokens: list[Token], language: str) -> None:
    contextual = _CONTEXTUAL.get(language)
    if not contextual:
        return
    significant = [index for index, token in enumerate(tokens) if token[2] not in {"whitespace"} and token[1] != TokenType.LITERAL]
    words = [tokens[index][0] for index in significant]
    query = False
    property_declared = False
    accessor = False
    for offset, index in enumerate(significant):
        word = words[offset]
        previous = words[offset - 1] if offset else ""
        following = words[offset + 1] if offset + 1 < len(words) else ""
        after = words[offset + 2] if offset + 2 < len(words) else ""
        if word == ";":
            query = False
        if language == "kotlin" and word == "fun":
            property_declared = accessor = False
        if language == "kotlin" and word in {"val", "var"}:
            property_declared = True
            accessor = False
        if word not in contextual:
            continue
        structural = False
        if language == "kotlin":
            if previous == "@" and following == ":" and word in {"get", "set", "field"}:
                structural = True
            elif word == "by":
                structural = previous not in {"", "val", "var", ".", "fun", "(", ","} and following not in {"=", ":", ",", ")", ";", "}"}
            elif word in {"get", "set"}:
                gap = "".join(token[0] for token in tokens[significant[offset - 1] + 1:index]) if offset else ""
                structural = property_declared and following == "(" and "\n" in gap
                accessor |= structural
            elif word == "field":
                structural = accessor and previous != "."
        else:
            if word == "var":
                structural = bool(following) and tokens[significant[offset + 1]][1] == TokenType.IDENTIFIER
            elif word in {"get", "set", "init", "add", "remove"}:
                structural = previous in {"{", "}", ";", "private", "protected", "internal", "public"} and following in {"{", ";", "="}
            elif word == "from":
                structural = bool(following) and after == "in"
                query |= structural
            elif word in {"select", "where", "orderby", "join", "on", "equals", "into", "group", "by", "ascending", "descending", "let"}:
                structural = query and previous != "."
                if word == "where" and after == ":":
                    structural = True
            elif word in {"async", "partial", "required", "scoped", "file", "record", "dynamic", "notnull", "unmanaged"}:
                structural = following not in {"", "=", ";", ",", ")", ".", "}"} and previous != "."
            elif word == "await":
                structural = following not in {"", "=", ";", ",", ")", ".", "}"}
            elif word == "yield":
                structural = following in {"return", "break"}
            elif word == "global":
                structural = following == ":" and after == ":"
            elif word == "nameof":
                structural = following == "("
            elif word in {"when", "with"}:
                structural = following in {"(", "{"} and previous not in {".", "="}
            elif word in {"and", "or", "not"}:
                structural = previous not in {"", ".", "=", ";", "(", "{"} and following not in {"=", ";", "}", ")"}
                if word == "not" and previous == "(":
                    cursor = offset - 1
                    while cursor >= 0 and words[cursor] == "(":
                        cursor -= 1
                    structural = (cursor >= 0 and words[cursor] in {"is", "case", "not", "and", "or"}
                                  and tokens[significant[cursor]][1] == TokenType.GRAMMAR)
            elif word == "alias":
                structural = previous == "extern"
        tokens[index] = (word, TokenType.GRAMMAR if structural else TokenType.IDENTIFIER,
                         "keyword" if structural else "identifier")


def _csharp_accessor_values(tokens: list[Token]) -> None:
    """Preserve the implicit parameter only inside writable accessor bodies."""
    from secure_gateway.engine.code_identifiers import identifier_key

    significant = [i for i, token in enumerate(tokens)
                   if token[2] != "whitespace" and token[1] != TokenType.LITERAL]
    depth = 0
    active_depth: int | None = None
    expression_depth: int | None = None
    initializer_depths: set[int] = set()
    constructing = False
    parentheses = 0
    construction_parentheses = 0
    pending = False
    previous = ""
    for offset, i in enumerate(significant):
        raw, kind, subkind = tokens[i]
        following = tokens[significant[offset + 1]][0] if offset + 1 < len(significant) else ""
        if raw == "{":
            depth += 1
            if constructing:
                initializer_depths.add(depth)
                constructing = False
            if pending:
                active_depth = depth
                pending = False
        elif raw == "}":
            initializer_depths.discard(depth)
            if active_depth == depth:
                active_depth = None
            depth -= 1
        elif raw == "=" and pending:
            expression_depth = depth
            pending = False
        elif raw == ";":
            constructing = False
            if expression_depth == depth:
                expression_depth = None
            pending = False
        elif raw == "(":
            parentheses += 1
        elif raw == ")":
            parentheses -= 1
            if constructing and parentheses <= construction_parentheses and following != "{":
                constructing = False
        elif kind == TokenType.GRAMMAR and raw in {"set", "init", "add", "remove"}:
            pending = True
        elif kind == TokenType.GRAMMAR and raw == "new":
            constructing = True
            construction_parentheses = parentheses
        elif (kind == TokenType.IDENTIFIER and identifier_key(raw, "csharp") == "value"
              and (active_depth is not None or expression_depth is not None)
              and previous != "."
              and not (depth in initializer_depths and previous in {"{", ","} and following == "=")
              and not (following == ":" and previous in {"(", ",", "{"})):
            tokens[i] = (raw, TokenType.GRAMMAR, "keyword")
        previous = raw
    _csharp_inferred_accessor_members(tokens)


def _csharp_inferred_accessor_members(tokens: list[Token]) -> None:
    """Track local receivers whose anonymous projection retains implicit value.

    This changes no source text: both the inferred name and its established
    local receiver's member reference remain ``value``. Other members continue
    through normal identifier masking. Reassignment and lexical shadowing
    invalidate that receiver rather than preserving every member named value.
    """
    from secure_gateway.engine.code_identifiers import identifier_key

    significant = [i for i, token in enumerate(tokens)
                   if token[2] != "whitespace" and token[1] != TokenType.LITERAL]
    words = [tokens[i][0] for i in significant]
    delimiters: list[int] = []
    closing: dict[int, int] = {}
    for position, word in enumerate(words):
        if word in {"(", "[", "{"}:
            delimiters.append(position)
        elif word in {")", "]", "}"} and delimiters:
            opening = delimiters.pop()
            closing[opening] = position
    anonymous: dict[int, tuple[int, bool]] = {}
    for position, word in enumerate(words):
        if word != "new" or position + 1 >= len(words) or words[position + 1] != "{":
            continue
        end = closing.get(position + 1)
        if end is None:
            continue
        cursor = position + 2
        entry = cursor
        implicit = False
        while cursor <= end:
            current = words[cursor]
            if current in {"(", "[", "{"} and cursor in closing:
                cursor = closing[cursor] + 1
                continue
            if current == "," or cursor == end:
                if cursor == entry + 1:
                    token = tokens[significant[entry]]
                    implicit |= (identifier_key(token[0], "csharp") == "value"
                                 and token[1] == TokenType.GRAMMAR)
                entry = cursor + 1
            cursor += 1
        anonymous[position] = (end, implicit)

    scopes: list[dict[str, bool]] = [{}]
    openings = {end: start for start, end in closing.items()}

    def inferred_expression(start: int, end: int) -> bool:
        while start < end and words[start] == "(" and closing.get(start) == end - 1:
            start += 1
            end -= 1
        projection = anonymous.get(start)
        if projection is not None and projection[0] == end - 1:
            return projection[1]
        if (end == start + 1 and tokens[significant[start]][1] == TokenType.IDENTIFIER
                and (start == 0 or words[start - 1] != ".")):
            key = identifier_key(words[start], "csharp")
            return next((scope[key] for scope in reversed(scopes) if key in scope), False)
        return False

    for position, index in enumerate(significant):
        raw, kind, _ = tokens[index]
        previous = words[position - 1] if position else ""
        following = words[position + 1] if position + 1 < len(words) else ""
        if raw == "{":
            scopes.append({})
        elif raw == "}" and len(scopes) > 1:
            scopes.pop()
        elif kind == TokenType.IDENTIFIER and following == "=" and previous != ".":
            key = identifier_key(raw, "csharp")
            projection = anonymous.get(position + 2)
            inferred = bool(projection and projection[1])
            rhs = position + 2
            if projection is None and rhs < len(words):
                rhs_end = closing.get(rhs, rhs) + 1
                if rhs_end == len(words) or words[rhs_end] in {";", ",", ")"}:
                    inferred = inferred_expression(rhs, rhs_end)
            declaration = previous == "var" or (position > 0 and tokens[significant[position - 1]][1] == TokenType.IDENTIFIER)
            target = scopes[-1]
            if not declaration:
                target = next((scope for scope in reversed(scopes) if key in scope), target)
            target[key] = inferred
        elif (kind == TokenType.IDENTIFIER and identifier_key(raw, "csharp") == "value"
              and previous == "." and position >= 2):
            end = position - 1
            start = end - 1
            if words[start] == ")":
                start = openings.get(start, start)
            elif words[start] == "}":
                start = openings.get(start, start) - 1
            inferred = start >= 0 and inferred_expression(start, end)
            if inferred:
                tokens[index] = (raw, TokenType.GRAMMAR, "keyword")


def _xml_name(name: str) -> list[Token]:
    chunks: list[Token] = []
    for part in re.split("(:)", name):
        if part:
            chunks.append(_grammar(part) if part in {":", "xmlns"} else (part, TokenType.IDENTIFIER, "identifier"))
    return chunks


def _xml_text(text: str) -> list[Token]:
    chunks: list[Token] = []
    for part in re.split(r"(&(?:#[0-9]+|#x[0-9a-fA-F]+|[A-Za-z][\w.-]*);)", text):
        if part:
            chunks.extend([_grammar(part)] if part.startswith("&") and part.endswith(";") else _payload(part))
    return chunks


def _xml_expression_end(code: str, start: int) -> int:
    position = start
    while position < len(code):
        if code.startswith("%>", position):
            return position
        if code[position] == '"':
            _, position = _quoted(code, position, '"', "vbnet", False)
        elif code[position] == "'":
            newline = code.find("\n", position)
            position = newline if newline >= 0 else len(code)
        else:
            position += 1
    raise ValueError("Unterminated XML interpolation")


def _xml_literal(code: str, start: int) -> tuple[list[Token], int]:
    """Read VB XML literal data separately from VB apostrophe comments."""
    chunks: list[Token] = []
    stack: list[str] = []
    position = start
    root_seen = False
    name_pattern = re.compile(r"[^\W\d][\w.:-]*", re.UNICODE)
    while position < len(code):
        if code.startswith("<%=", position):
            end = _xml_expression_end(code, position + 3)
            chunks.extend([_grammar("<%="), *tokenize(code[position + 3:end], "vbnet"), _grammar("%>")])
            position = end + 2
            continue
        special = next(((opening, closing) for opening, closing in (("<!--", "-->"), ("<![CDATA[", "]]>"), ("<?", "?>")) if code.startswith(opening, position)), None)
        if special:
            end = code.find(special[1], position + len(special[0]))
            if end < 0:
                raise ValueError("Unterminated XML literal data")
            end += len(special[1])
            chunks.append(_literal(code[position:end], len(special[0]), len(special[1])))
            position = end
            continue
        if code[position] == "<":
            closing = code.startswith("</", position)
            prefix = "</" if closing else "<"
            match = name_pattern.match(code, position + len(prefix))
            if match is None:
                raise ValueError("Unsupported XML literal declaration")
            name = match[0]
            chunks.extend([_grammar(prefix), *_xml_name(name)])
            position = match.end()
            if closing:
                if not stack or stack.pop() != name:
                    raise ValueError("Mismatched XML literal element")
            else:
                stack.append(name)
                root_seen = True
            while position < len(code):
                if code.startswith("/>", position):
                    if closing:
                        raise ValueError("Invalid XML closing tag")
                    stack.pop()
                    chunks.append(_grammar("/>"))
                    position += 2
                    break
                if code[position] == ">":
                    chunks.append(_grammar(">"))
                    position += 1
                    break
                if code[position].isspace() or code[position] == "=":
                    chunks.append(_grammar(code[position]))
                    position += 1
                    continue
                if code[position] in "\"'":
                    quote = code[position]
                    end = code.find(quote, position + 1)
                    if end < 0:
                        raise ValueError("Unterminated XML attribute value")
                    chunks.extend([_grammar(quote), *_xml_text(code[position + 1:end]), _grammar(quote)])
                    position = end + 1
                    continue
                attribute = name_pattern.match(code, position)
                if attribute:
                    chunks.extend(_xml_name(attribute[0]))
                    position = attribute.end()
                    continue
                if code.startswith("<%=", position):
                    end = _xml_expression_end(code, position + 3)
                    chunks.extend([_grammar("<%="), *tokenize(code[position + 3:end], "vbnet"), _grammar("%>")])
                    position = end + 2
                    continue
                raise ValueError("Unsupported XML attribute syntax")
            else:
                raise ValueError("Unterminated XML element")
            if root_seen and not stack:
                return chunks, position
            continue
        end = code.find("<", position)
        if end < 0:
            raise ValueError("Unterminated XML literal")
        chunks.extend(_xml_text(code[position:end]))
        position = end
    raise ValueError("Unterminated XML literal")


def tokenize(code: str, language: str) -> list[Token]:
    """Tokenize a supported language without executing any input."""
    language = ALIASES.get(language.lower(), language.lower())
    if language not in LANGUAGE_KEYWORDS:
        raise ValueError(f"Unsupported code language: {language}")
    if "\x00" in code:
        raise ValueError("NUL is not valid source text")
    if language == "php" and "<?" in code and not code.lstrip().startswith("<?php"):
        raise ValueError("Mixed PHP/HTML is not supported")
    result: list[Token] = []
    position = 0
    nasm_macros: set[str] = set()
    nasm_insensitive_macros: set[str] = set()
    bash_declaration = False
    bash_command_start = True
    bash_binding_next = False
    bash_arithmetic_depth = 0
    if language == "nasm":
        for definition in re.finditer(r"(?im)^[ \t]*%(macro|imacro|define|idefine|xdefine|ixdefine)[ \t]+([A-Za-z_][\w.]*)", code):
            if definition[1].lower().startswith("i"):
                nasm_insensitive_macros.add(definition[2].lower())
            else:
                nasm_macros.add(definition[2])
    while position < len(code):
        start = position
        character = code[position]
        if language == "bash":
            if not bash_arithmetic_depth and code.startswith("((", position):
                bash_arithmetic_depth = 1
            elif bash_arithmetic_depth:
                if character == "(":
                    bash_arithmetic_depth += 1
                elif character == ")":
                    bash_arithmetic_depth -= 1
            if code.startswith("\\\n", position):
                result.append(_grammar("\\\n"))
                position += 2
                continue
            if character in "\n;|&(){}":
                bash_declaration = False
                bash_command_start = True
                bash_binding_next = False
        if language == "ruby" and code.startswith("__END__", position) and (position == 0 or code[position - 1] == "\n") and code[position + 7:position + 8] in {"", "\r", "\n"}:
            newline = code.find("\n", position)
            if newline < 0:
                result.append(_grammar(code[position:]))
            else:
                result.extend([_grammar(code[position:newline + 1]), _literal(code[newline + 1:])])
            break
        if character.isspace():
            position += 1
            while position < len(code) and code[position].isspace():
                position += 1
            result.append(_grammar(code[start:position], "whitespace"))
            continue
        if language == "vbnet" and character == "<" and re.compile(r"<[^\W\d]").match(code, position) and next((token[0] for token in reversed(result) if token[2] != "whitespace"), "") in {"=", "(", ",", "return", "Return"}:
            chunks, position = _xml_literal(code, position)
            result.extend(chunks)
            continue
        # PHP mixed HTML is deliberately refused: plaintext outside tags cannot
        # be classified as PHP identifiers without leaking or corrupting markup.
        if language == "php" and code.startswith("<?php", position):
            result.append(_grammar("<?php"))
            position += 5
            continue
        if language == "php" and code.startswith("?>", position):
            if code[position + 2:].strip():
                raise ValueError("Mixed PHP/HTML is not supported")
            result.append(_grammar("?>"))
            position += 2
            continue
        if language in {"bash", "ruby"} and code.startswith("<<", position):
            queued = _queued_heredocs(code, position, language)
            if queued:
                chunks, position = queued
                result.extend(chunks)
                continue
        if language in {"bash", "php"} and code.startswith("<<", position):
            heredoc = _heredoc(code, position, language)
            if heredoc:
                chunks, position = heredoc
                result.extend(chunks)
                continue
            if language == "bash":
                raise ValueError("Unsupported shell heredoc syntax")
        if language == "powershell" and code.startswith(("@'", '@"'), position):
            opener = code[position:position + 2]
            here_header = re.compile(r"@['\"][ \t]*\r?\n").match(code, position)
            if not here_header:
                raise ValueError("Invalid PowerShell here-string header")
            ending = re.compile(rf"(?m)^{re.escape(opener[1])}@(?=\r?$)").search(code, position + len(here_header[0]))
            if ending is None:
                raise ValueError("Unterminated PowerShell here-string")
            end = ending.end()
            body = code[position + len(here_header[0]):end - 2]
            result.extend([_grammar(here_header[0]), *_interpolated_body(body, language, opener == '@"'), _grammar(opener[1] + "@")])
            position = end
            continue
        if language == "lua" and (long := re.compile(r"(?:--)?\[(=*)\[").match(code, position)):
            lua_ending = "]" + long[1] + "]"
            end = code.find(lua_ending, position + len(long[0]))
            if end < 0:
                raise ValueError("Unterminated Lua long literal")
            end += len(lua_ending)
            result.append(_literal(code[position:end], len(long[0]), len(lua_ending)))
            position = end
            continue
        if language == "nix" and code.startswith("''", position):
            chunks, position = _quoted(code, position, "''", language, True, raw=True)
            result.extend(chunks)
            continue
        if language == "ruby" and character == "%":
            percent = _ruby_percent(code, position)
            if percent:
                chunks, position = percent
                result.extend(chunks)
                continue
        if language == "ruby" and (heredoc_ruby := re.compile(r"<<([-~]?)(['\"`]?)([A-Za-z_]\w*)\2[ \t]*\r?\n").match(code, position)):
            whitespace = "[ \\t]*" if heredoc_ruby[1] else ""
            ending = re.compile(rf"(?m)^{whitespace}{re.escape(heredoc_ruby[3])}\r?$").search(code, position + len(heredoc_ruby[0]))
            if ending is None:
                raise ValueError("Unterminated Ruby heredoc")
            content_start = position + len(heredoc_ruby[0])
            content_end = ending.start()
            end = ending.end()
            result.extend([_grammar(heredoc_ruby[0]), *_interpolated_body(code[content_start:content_end], language, heredoc_ruby[2] != "'"), _grammar(ending[0])])
            position = end
            continue
        if language == "r" and (raw_r := re.compile(r'[rR](["\'])(-*)([([{])').match(code, position)):
            closer = {"(": ")", "[": "]", "{": "}"}[raw_r[3]] + raw_r[2] + raw_r[1]
            end = code.find(closer, position + len(raw_r[0]))
            if end < 0:
                raise ValueError("Unterminated R raw string")
            end += len(closer)
            result.append(_literal(code[position:end], len(raw_r[0]), len(closer)))
            position = end
            continue
        block = None
        if language == "powershell" and code.startswith("<#", position):
            block = ("<#", "#>", False)
        elif language not in {"bash", "lua", "ruby", "r", "gdscript", "vbnet", "vba", "nasm"} and code.startswith("/*", position):
            block = ("/*", "*/", language in {"kotlin", "swift", "dart"})
        if block:
            position = _block_end(code, position, *block)
            result.append(_literal(code[start:position], len(block[0]), len(block[1])))
            continue
        if language == "nasm" and character == "%" and (directive := re.compile(r"%(?:define|xdefine|idefine|ixdefine|undef|assign|iassign|macro|imacro|endmacro|rep|endrep|if|ifdef|ifndef|ifidn|ifnidn|ifnum|elif|else|endif|include|push|pop|repl|rotate|error|warning|line|pragma|unmacro|exitmacro)\b", re.IGNORECASE).match(code, position)):
            result.append(_grammar(directive[0], "keyword"))
            position += len(directive[0])
            continue
        if language == "nasm" and character == "$" and position + 1 < len(code):
            end = _identifier_end(code, position + 1, language)
            if end > position + 1:
                result.append((code[position:end], TokenType.IDENTIFIER, "identifier"))
                position = end
                continue
        ruby_previous = next((token[0] for token in reversed(result) if token[2] != "whitespace"), "") if language == "ruby" else ""
        if language == "ruby" and character == "/" and ruby_previous in {"", "=", "(", "[", ",", ":", "return", "~", "!", "and", "or", "when"}:
            chunks, position = _quoted(code, position, "/", language, True, interpolation_marker="#{")
            result.extend(chunks)
            flags = re.compile(r"[imxounes]+").match(code, position)
            if flags:
                result.append(_grammar(flags[0]))
                position += len(flags[0])
            continue
        line_comment = (
            (character == "#" and language in {"bash", "powershell", "ruby", "r", "nix", "gdscript"})
            or (language in {"vbnet", "vba"} and character == "'")
            or (language == "nasm" and character == ";")
            or (language == "lua" and code.startswith("--", position))
            or (language in {"csharp", "php", "kotlin", "swift", "dart"} and code.startswith("//", position))
            or (language == "php" and character == "#" and not code.startswith("#[", position))
            or (language in {"vbnet", "vba"} and re.compile(r"(?i:rem)(?:\s|$)").match(code, position) and (position == 0 or code[position - 1] in "\r\n:"))
        )
        if line_comment:
            end = code.find("\n", position)
            position = end if end >= 0 else len(code)
            prefix = 2 if code.startswith(("//", "--"), start) else (3 if code[start:start + 3].lower() == "rem" else 1)
            result.append(_literal(code[start:position], prefix))
            continue
        if language == "csharp" and (raw_match := re.compile(r'\$*("{3,})').match(code, position)):
            delimiter = raw_match[1]
            dollars = len(raw_match[0]) - len(delimiter)
            chunks, position = _quoted(code, start, delimiter, language, bool(dollars), raw=True,
                                       prefix_length=dollars, interpolation_marker="{" * dollars if dollars else None)
            result.extend(chunks)
            continue
        if language == "swift" and (swift_raw := re.compile(r'(#+)("""|")').match(code, position)):
            chunks, position = _quoted(code, start, swift_raw[2], language, True, raw=True,
                                       prefix_length=len(swift_raw[1]), closing=swift_raw[2] + swift_raw[1],
                                       interpolation_marker="\\" + swift_raw[1] + "(")
            result.extend(chunks)
            continue
        prefix_length = 0
        if language == "csharp" and (string_prefix := re.compile(r'(?:\$@|@\$|\$|@)(?=")').match(code, position)):
            prefix_length = len(string_prefix[0])
        elif language == "vbnet" and code.startswith('$"', position):
            prefix_length = 1
        elif language == "dart" and character in "rR" and position + 1 < len(code) and code[position + 1] in "\"'":
            prefix_length = 1
        quote_position = position + prefix_length
        if quote_position < len(code) and code[quote_position] in "\"'`":
            quote = code[quote_position]
            if language == "bash" and quote == "`":
                raise ValueError("Legacy shell backtick substitutions are not supported")
            if language in {"kotlin", "r", "swift"} and quote == "`":
                end = code.find("`", quote_position + 1)
                if end < 0:
                    raise ValueError("Unterminated quoted identifier")
                result.append((code[start:end + 1], TokenType.IDENTIFIER, "identifier"))
                position = end + 1
                continue
            triple = code.startswith(quote * 3, quote_position) and language in {"kotlin", "swift", "dart", "gdscript"}
            delimiter = quote * (3 if triple else 1)
            interpolate = (
                (language in {"bash", "php", "powershell", "ruby", "kotlin", "nix", "swift"} and quote == '"')
                or (language == "csharp" and "$" in code[start:quote_position])
                or (language == "vbnet" and prefix_length == 1)
                or (language == "dart" and prefix_length == 0)
            )
            chunks, position = _quoted(code, start, delimiter, language, interpolate,
                                       prefix_length=prefix_length, raw=triple or (language == "dart" and prefix_length > 0) or (language in {"bash", "php", "powershell"} and quote == "'"))
            if language in {"csharp", "kotlin"} and quote == "'" and len(chunks) == 1:
                chunks = [(chunks[0][0], TokenType.LITERAL, "character")]
            result.extend(chunks)
            continue
        if language == "csharp" and character == "@":
            end = _csharp_escaped_identifier(code, position)
            if end > position + 1:
                result.append((code[position:end], TokenType.IDENTIFIER, "identifier"))
                position = end
                continue
        if language == "csharp" and character == "\\":
            end = _csharp_escaped_identifier(code, position)
            if end == position:
                raise ValueError("Invalid C# identifier escape")
            result.append((code[position:end], TokenType.IDENTIFIER, "identifier"))
            position = end
            continue
        if language in {"vbnet", "vba"} and character == "[":
            end = code.find("]", position + 1)
            if end < 0:
                raise ValueError("Unterminated VB escaped identifier")
            result.append((code[position:end + 1], TokenType.IDENTIFIER, "identifier"))
            position = end + 1
            continue
        variable = _variable(code, position, language)
        if variable:
            variable_chunks, position = variable
            result.extend(variable_chunks)
            continue
        if language == "powershell" and character == "-" and (operator := re.compile(r"-(?:eq|ne|gt|ge|lt|le|like|notlike|match|notmatch|contains|notcontains|in|notin|is|isnot|as|and|or|xor|not|band|bor|bxor|bnot|shl|shr|replace|split|join|f)\b", re.IGNORECASE).match(code, position)):
            result.append(_grammar(operator[0], "keyword"))
            position += len(operator[0])
            continue
        if language in {"vbnet", "vba"} and (vb_number := re.compile(r"&(?:[hH][0-9a-fA-F]+|[oO][0-7]+|[bB][01]+)[%&^]?").match(code, position)):
            result.append((vb_number[0], TokenType.NUMBER, "number"))
            position += len(vb_number[0])
            continue
        if language in {"vbnet", "vba"} and character == "#" and (date := re.compile(r"#[^#\r\n]+#").match(code, position)):
            result.append((date[0], TokenType.NUMBER, "number"))
            position += len(date[0])
            continue
        if character.isdigit() or (character == "." and position + 1 < len(code) and code[position + 1].isdigit()):
            number = _NUMBER.match(code, position)
            if number:
                position = number.end()
                result.append((code[start:position], TokenType.NUMBER, "number"))
                continue
        end = _identifier_end(code, position, language)
        if language == "csharp" and end > position and end < len(code) and code[end] == "\\":
            end = _csharp_escaped_identifier(code, position)
        if end > position:
            raw = code[position:end]
            key = raw.lower() if language in _CASE_INSENSITIVE else raw
            if language == "bash":
                key = raw.replace("\\\n", "")
            reserved = key in LANGUAGE_KEYWORDS[language]
            if language == "bash":
                assignment = code.startswith(("=", "+="), end)
                # A reserved word immediately followed by '[' is part of an
                # array word/lvalue, never a stand-alone control keyword.
                if assignment or code.startswith("[", end) or bash_declaration or bash_binding_next or bash_arithmetic_depth:
                    reserved = False
                bash_binding_next = reserved and key in {"for", "select"}
                if bash_command_start and not assignment:
                    bash_declaration = key in {"local", "export", "readonly", "declare", "typeset"}
                if not assignment:
                    bash_command_start = reserved and key in {"if", "then", "elif", "else", "do", "while", "until", "time", "coproc"}
            if position and code[position - 1] == "$" and language in {"php", "powershell", "bash"}:
                reserved = False
            if language in {"vbnet", "vba"} and raw == "_" and re.compile(r"[ \t]*\r?\n").match(code, end):
                reserved = True
            if language == "nasm" and re.fullmatch(r"(?:r(?:[8-9]|1[0-5])(?:[bwd])?|[xyz]mm\d+|[cdefgs]s|[cd]r\d+)", raw, re.IGNORECASE):
                reserved = True
            if language == "nasm" and re.fullmatch(r"v?cvt(?:pi|si|tt|ps|pd|ss|sd|dq|qq|udq|uqq)[a-z0-9]*", raw, re.IGNORECASE):
                reserved = True
            nasm_macro = language == "nasm" and (raw in nasm_macros or raw.lower() in nasm_insensitive_macros)
            if nasm_macro:
                reserved = False
            if language == "nasm" and not reserved and not nasm_macro:
                line_start = code.rfind("\n", 0, position) + 1
                line_end = code.find("\n", end)
                if line_end < 0:
                    line_end = len(code)
                indentation = re.compile(r"[ \t]*").match(code, line_start)
                assert indentation is not None
                at_instruction = indentation.end() == position
                operand = re.compile(r"[ \t]+([A-Za-z][A-Za-z0-9]*)\s*(?:,|$)").match(code, end, line_end)
                # An explicit instruction field followed by a register operand
                # is unambiguous even for newer ISA mnemonics absent our table.
                if at_instruction and operand and (operand[1].lower() in LANGUAGE_KEYWORDS["nasm"] or re.fullmatch(r"(?:[xyz]mm|r|st|mm|k)\d+", operand[1], re.IGNORECASE)):
                    reserved = True
            if language == "gdscript" and position and code[position - 1] == "@" and raw in _GDSCRIPT_ANNOTATIONS:
                reserved = True
            identifier_kind = "case_insensitive_identifier" if language == "nasm" and raw.lower() in nasm_insensitive_macros else "identifier"
            result.append((raw, TokenType.GRAMMAR if reserved else TokenType.IDENTIFIER, "keyword" if reserved else identifier_kind))
            position = end
            continue
        result.append(_grammar(character))
        position += 1
    _contextual_keywords(result, language)
    if language == "csharp":
        _csharp_accessor_values(result)
    return result
