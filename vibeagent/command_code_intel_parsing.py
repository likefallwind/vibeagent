from __future__ import annotations

from .command_types import LocalCommand, make_local_command


def parse_code_intel_local_command(trimmed: str) -> LocalCommand | None:
    if trimmed == "/python-check" or trimmed.startswith("/python-check "):
        return make_local_command("python_check", trimmed[14:].strip() or None)
    if trimmed == "/python-deps" or trimmed.startswith("/python-deps "):
        return make_local_command("python_deps", trimmed[13:].strip() or None)
    if trimmed == "/python-defs" or trimmed.startswith("/python-defs "):
        return make_local_command("python_defs", trimmed[13:].strip() or None)
    if trimmed == "/python-refs" or trimmed.startswith("/python-refs "):
        return make_local_command("python_refs", trimmed[13:].strip() or None)
    if trimmed == "/python-ref-contexts" or trimmed.startswith("/python-ref-contexts "):
        return make_local_command("python_ref_contexts", trimmed[21:].strip() or None)
    if trimmed == "/python-calls" or trimmed.startswith("/python-calls "):
        return make_local_command("python_calls", trimmed[14:].strip() or None)
    if trimmed == "/python-call-graph" or trimmed.startswith("/python-call-graph "):
        return make_local_command("python_call_graph", trimmed[19:].strip() or None)
    if trimmed == "/python-rename-preview" or trimmed.startswith("/python-rename-preview "):
        return make_local_command("python_rename_preview", trimmed[23:].strip() or None)
    if trimmed == "/python-rename" or trimmed.startswith("/python-rename "):
        return make_local_command("python_rename", trimmed[15:].strip() or None)
    if trimmed == "/check-replace-python-def" or trimmed.startswith("/check-replace-python-def "):
        return make_local_command("check_replace_python_definition", trimmed[26:].strip() or None)
    if trimmed == "/replace-python-def" or trimmed.startswith("/replace-python-def "):
        return make_local_command("replace_python_definition", trimmed[20:].strip() or None)
    if trimmed == "/code-deps" or trimmed.startswith("/code-deps "):
        return make_local_command("code_deps", trimmed[11:].strip() or None)
    if trimmed == "/code-refs" or trimmed.startswith("/code-refs "):
        return make_local_command("code_refs", trimmed[11:].strip() or None)
    if trimmed == "/code-ref-contexts" or trimmed.startswith("/code-ref-contexts "):
        return make_local_command("code_ref_contexts", trimmed[19:].strip() or None)
    if trimmed == "/code-defs" or trimmed.startswith("/code-defs "):
        return make_local_command("code_defs", trimmed[11:].strip() or None)
    if trimmed == "/code-rename-preview" or trimmed.startswith("/code-rename-preview "):
        return make_local_command("code_rename_preview", trimmed[21:].strip() or None)
    if trimmed == "/code-rename" or trimmed.startswith("/code-rename "):
        return make_local_command("code_rename", trimmed[13:].strip() or None)
    return None
