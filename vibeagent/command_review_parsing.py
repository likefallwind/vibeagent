from __future__ import annotations

from .command_types import LocalCommand, make_local_command


def parse_review_local_command(trimmed: str) -> LocalCommand | None:
    if trimmed == "/status":
        return make_local_command("status", None)
    if trimmed == "/context":
        return make_local_command("context", None)
    if trimmed == "/init" or trimmed.startswith("/init "):
        return make_local_command("init", trimmed[6:].strip() or None)
    if trimmed == "/doctor":
        return make_local_command("doctor", None)
    if trimmed == "/review" or trimmed.startswith("/review "):
        return make_local_command("review", trimmed[8:].strip() or None)
    if trimmed == "/code-review" or trimmed.startswith("/code-review "):
        return make_local_command("code_review", trimmed[12:].strip() or None)
    if trimmed == "/handoff" or trimmed.startswith("/handoff "):
        return make_local_command("handoff", trimmed[9:].strip() or None)
    if trimmed == "/changes" or trimmed.startswith("/changes "):
        return make_local_command("changes", trimmed[9:].strip() or None)
    if trimmed == "/diff" or trimmed.startswith("/diff "):
        return make_local_command("diff", trimmed[6:].strip() or None)
    if trimmed == "/diff-hunks" or trimmed.startswith("/diff-hunks "):
        return make_local_command("diff_hunks", trimmed[12:].strip() or None)
    if trimmed == "/diff-contexts" or trimmed.startswith("/diff-contexts "):
        return make_local_command("diff_contexts", trimmed[14:].strip() or None)
    return None
