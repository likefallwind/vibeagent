from __future__ import annotations

from pathlib import Path
import re
import shlex


def node_one_liner_blocked_command_reason(command: str, depth: int) -> str | None:
    if depth >= 3:
        return None
    try:
        parts = shlex.split(command)
    except ValueError:
        return None
    while parts:
        executable = Path(parts[0]).name.lower()
        if executable in {"nohup", "setsid"}:
            parts = parts[1:]
            continue
        if executable == "env":
            parts = parts[1:]
            while parts and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", parts[0]):
                parts = parts[1:]
            continue
        break
    if len(parts) < 2 or Path(parts[0]).name.lower() not in {"node", "nodejs"}:
        return None

    script: str | None = None
    skip_next = False
    for index, token in enumerate(parts[1:], start=1):
        if skip_next:
            skip_next = False
            continue
        if token in {"-e", "--eval", "-p", "--print"}:
            if index + 1 < len(parts):
                script = parts[index + 1]
            break
        if token.startswith("--eval=") or token.startswith("--print="):
            script = token.split("=", 1)[1]
            break
        if (token.startswith("-e") or token.startswith("-p")) and len(token) > 2:
            script = token[2:]
            break
        if token in {"-r", "--require", "--import"}:
            skip_next = True
            continue
        if not token.startswith("-"):
            break
    if not script:
        return None
    return node_script_blocked_command_reason(script, depth)


def node_script_blocked_command_reason(script: str, depth: int) -> str | None:
    identifier = r"[A-Za-z_$][A-Za-z0-9_$]*"

    child_process_aliases = {"child_process"}
    child_process_methods = {"exec", "execSync", "spawn", "spawnSync", "execFile", "execFileSync"}
    child_process_methods_pattern = "|".join(sorted(child_process_methods, key=len, reverse=True))
    child_process_require_pattern = r"require\(\s*['\"](?:node:)?child_process['\"]\s*\)"
    child_process_dynamic_import_pattern = r"(?:await\s+)?import\(\s*['\"](?:node:)?child_process['\"]\s*\)"
    child_process_aliases.update(node_require_assignment_aliases(script, child_process_require_pattern, identifier))
    child_process_aliases.update(node_require_assignment_aliases(script, child_process_dynamic_import_pattern, identifier))
    child_process_aliases.update(node_import_default_aliases(script, r"(?:node:)?child_process", identifier))
    child_process_function_aliases = node_require_destructured_aliases(
        script,
        child_process_require_pattern,
        child_process_methods,
        identifier,
    )
    child_process_function_aliases.update(
        node_require_destructured_aliases(script, child_process_dynamic_import_pattern, child_process_methods, identifier),
    )
    child_process_function_aliases.update(node_import_named_aliases(script, r"(?:node:)?child_process", child_process_methods, identifier))

    shelljs_require_pattern = r"require\(\s*['\"]shelljs['\"]\s*\)"
    shelljs_dynamic_import_pattern = r"(?:await\s+)?import\(\s*['\"]shelljs['\"]\s*\)"
    shelljs_aliases = node_require_assignment_aliases(script, shelljs_require_pattern, identifier)
    shelljs_aliases.update(node_require_assignment_aliases(script, shelljs_dynamic_import_pattern, identifier))
    shelljs_aliases.update(node_import_default_aliases(script, "shelljs", identifier))
    shelljs_function_aliases = node_require_destructured_aliases(
        script,
        shelljs_require_pattern,
        {"exec"},
        identifier,
    )
    shelljs_function_aliases.update(node_require_destructured_aliases(script, shelljs_dynamic_import_pattern, {"exec"}, identifier))
    shelljs_function_aliases.update(node_import_named_aliases(script, "shelljs", {"exec"}, identifier))

    execa_require_pattern = r"require\(\s*['\"]execa['\"]\s*\)"
    execa_dynamic_import_pattern = r"(?:await\s+)?import\(\s*['\"]execa['\"]\s*\)"
    execa_methods = {"execa", "execaSync", "execaCommand", "execaCommandSync"}
    execa_methods_pattern = "|".join(sorted(execa_methods, key=len, reverse=True))
    execa_aliases = node_require_assignment_aliases(script, execa_require_pattern, identifier)
    execa_aliases.update(node_require_assignment_aliases(script, execa_dynamic_import_pattern, identifier))
    execa_aliases.update(node_import_default_aliases(script, "execa", identifier))
    execa_function_aliases = {alias: "execa" for alias in execa_aliases}
    execa_function_aliases.update(node_require_destructured_aliases(script, execa_require_pattern, execa_methods, identifier))
    execa_function_aliases.update(node_require_destructured_aliases(script, execa_dynamic_import_pattern, execa_methods, identifier))
    execa_function_aliases.update(node_import_named_aliases(script, "execa", execa_methods, identifier))

    call_patterns: list[tuple[re.Pattern[str], int]] = [
        (re.compile(rf"{child_process_require_pattern}\s*\.\s*({child_process_methods_pattern})\s*\("), 1),
        (re.compile(rf"\(?\s*{child_process_dynamic_import_pattern}\s*\)?\s*\.\s*({child_process_methods_pattern})\s*\("), 1),
        (re.compile(r"require\(\s*['\"]shelljs['\"]\s*\)\s*\.\s*(exec)\s*\("), 1),
        (re.compile(rf"\(?\s*{shelljs_dynamic_import_pattern}\s*\)?\s*\.\s*(exec)\s*\("), 1),
        (re.compile(rf"{execa_require_pattern}\s*\.\s*({execa_methods_pattern})\s*\("), 1),
        (re.compile(rf"\(?\s*{execa_dynamic_import_pattern}\s*\)?\s*\.\s*({execa_methods_pattern})\s*\("), 1),
    ]
    if child_process_aliases:
        aliases = "|".join(re.escape(alias) for alias in sorted(child_process_aliases, key=len, reverse=True))
        call_patterns.append((re.compile(rf"\b(?:{aliases})\s*\.\s*({child_process_methods_pattern})\s*\("), 1))
    if shelljs_aliases:
        aliases = "|".join(re.escape(alias) for alias in sorted(shelljs_aliases, key=len, reverse=True))
        call_patterns.append((re.compile(rf"\b(?:{aliases})\s*\.\s*(exec)\s*\("), 1))
    if execa_aliases:
        aliases = "|".join(re.escape(alias) for alias in sorted(execa_aliases, key=len, reverse=True))
        call_patterns.append((re.compile(rf"\b(?:{aliases})\s*\.\s*({execa_methods_pattern})\s*\("), 1))
    function_aliases = child_process_function_aliases | shelljs_function_aliases | execa_function_aliases
    if function_aliases:
        aliases = "|".join(re.escape(alias) for alias in sorted(function_aliases, key=len, reverse=True))
        call_patterns.append((re.compile(rf"\b({aliases})\s*\("), 1))

    for pattern, method_group in call_patterns:
        for match in pattern.finditer(script):
            method = match.group(method_group)
            if method in function_aliases:
                method = function_aliases[method]
            nested_command = node_child_process_nested_command(script, match.end(), method)
            if not nested_command:
                continue
            nested_blocked = _get_blocked_command_reason(nested_command, depth + 1)
            if nested_blocked:
                return nested_blocked
    return None


def node_require_assignment_aliases(script: str, require_pattern: str, identifier: str) -> set[str]:
    aliases: set[str] = set()
    for match in re.finditer(rf"(?:const|let|var)?\s*({identifier})\s*=\s*{require_pattern}", script):
        aliases.add(match.group(1))
    return aliases


def node_require_destructured_aliases(script: str, require_pattern: str, methods: set[str], identifier: str) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for match in re.finditer(rf"(?:const|let|var)\s*\{{([^}}]+)\}}\s*=\s*{require_pattern}", script):
        for binding in match.group(1).split(","):
            method_alias = node_destructured_binding_alias(binding, separator=":", identifier=identifier)
            if method_alias is None:
                continue
            method, alias = method_alias
            if method in methods:
                aliases[alias] = method
    return aliases


def node_import_default_aliases(script: str, module_pattern: str, identifier: str) -> set[str]:
    aliases: set[str] = set()
    pattern = rf"\bimport\s+({identifier})\s+from\s+['\"]{module_pattern}['\"]"
    for match in re.finditer(pattern, script):
        aliases.add(match.group(1))
    return aliases


def node_import_named_aliases(script: str, module_pattern: str, methods: set[str], identifier: str) -> dict[str, str]:
    aliases: dict[str, str] = {}
    pattern = rf"\bimport\s*\{{([^}}]+)\}}\s*from\s*['\"]{module_pattern}['\"]"
    for match in re.finditer(pattern, script):
        for binding in match.group(1).split(","):
            method_alias = node_destructured_binding_alias(binding, separator=r"\bas\b", identifier=identifier)
            if method_alias is None:
                continue
            method, alias = method_alias
            if method in methods:
                aliases[alias] = method
    return aliases


def node_destructured_binding_alias(binding: str, separator: str, identifier: str) -> tuple[str, str] | None:
    binding = binding.strip()
    if not binding:
        return None
    parts = [part.strip() for part in re.split(separator, binding, maxsplit=1)]
    method = parts[0].split("=", 1)[0].strip()
    alias = parts[-1].split("=", 1)[0].strip()
    if not re.fullmatch(identifier, method) or not re.fullmatch(identifier, alias):
        return None
    return method, alias


def node_child_process_nested_command(script: str, start: int, method: str) -> str | None:
    index = javascript_skip_ws(script, start)
    first, index = javascript_string_literal(script, index)
    if first is None:
        return None
    if method in {"exec", "execSync", "execaCommand", "execaCommandSync"}:
        return first
    index = javascript_skip_ws(script, index)
    if index >= len(script) or script[index] != ",":
        return shlex.join([first])
    argv, _ = javascript_string_array_literal(script, index + 1)
    if argv is None:
        return shlex.join([first])
    return shlex.join([first, *argv])


def javascript_string_array_literal(script: str, start: int) -> tuple[list[str] | None, int]:
    index = javascript_skip_ws(script, start)
    if index >= len(script) or script[index] != "[":
        return None, index
    index += 1
    values: list[str] = []
    while True:
        index = javascript_skip_ws(script, index)
        if index >= len(script):
            return None, index
        if script[index] == "]":
            return values, index + 1
        value, index = javascript_string_literal(script, index)
        if value is None:
            return None, index
        values.append(value)
        index = javascript_skip_ws(script, index)
        if index < len(script) and script[index] == ",":
            index += 1
            continue
        if index < len(script) and script[index] == "]":
            return values, index + 1
        return None, index


def javascript_string_literal(script: str, start: int) -> tuple[str | None, int]:
    index = javascript_skip_ws(script, start)
    if index >= len(script) or script[index] not in {"'", '"'}:
        return None, index
    quote = script[index]
    index += 1
    value: list[str] = []
    while index < len(script):
        character = script[index]
        if character == quote:
            return "".join(value), index + 1
        if character == "\\" and index + 1 < len(script):
            index += 1
            escaped = script[index]
            value.append({"n": "\n", "r": "\r", "t": "\t"}.get(escaped, escaped))
        else:
            value.append(character)
        index += 1
    return None, index


def javascript_skip_ws(script: str, start: int) -> int:
    index = start
    while index < len(script) and script[index].isspace():
        index += 1
    return index


def _get_blocked_command_reason(command: str, depth: int) -> str | None:
    from .command_safety import get_blocked_command_reason

    return get_blocked_command_reason(command, _depth=depth)
