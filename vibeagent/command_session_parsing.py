from __future__ import annotations

from .command_types import LocalCommand, make_local_command


def parse_session_local_command(trimmed: str) -> LocalCommand | None:
    if trimmed == "/rename" or trimmed.startswith("/rename "):
        return make_local_command("rename", trimmed[7:].strip() or None)
    if trimmed == "/export" or trimmed.startswith("/export "):
        return make_local_command("export", trimmed[7:].strip() or None)
    if trimmed == "/sessions":
        return make_local_command("sessions", None)
    if trimmed == "/last":
        return make_local_command("last", None)
    if trimmed == "/plan" or trimmed.startswith("/plan "):
        return make_local_command("plan", trimmed[6:].strip() or None)
    if trimmed == "/transcript" or trimmed.startswith("/transcript "):
        return make_local_command("transcript", trimmed[12:].strip() or None)
    if trimmed == "/session-search" or trimmed.startswith("/session-search "):
        return make_local_command("session_search", trimmed[15:].strip() or None)
    if trimmed == "/session-commands" or trimmed.startswith("/session-commands "):
        return make_local_command("session_commands", trimmed[17:].strip() or None)
    if trimmed == "/session-output-contexts" or trimmed.startswith("/session-output-contexts "):
        return make_local_command("session_output_contexts", trimmed[24:].strip() or None)
    if trimmed == "/session-output-diagnostics" or trimmed.startswith("/session-output-diagnostics "):
        return make_local_command("session_output_diagnostics", trimmed[28:].strip() or None)
    if trimmed == "/session-files" or trimmed.startswith("/session-files "):
        return make_local_command("session_files", trimmed[14:].strip() or None)
    if trimmed == "/session-failures" or trimmed.startswith("/session-failures "):
        return make_local_command("session_failures", trimmed[17:].strip() or None)
    if trimmed == "/session-verification" or trimmed.startswith("/session-verification "):
        return make_local_command("session_verification", trimmed[21:].strip() or None)
    if trimmed == "/run-session-verification" or trimmed.startswith("/run-session-verification "):
        prefix = "/run-session-verification"
        return make_local_command("run_session_verification", trimmed[len(prefix) :].strip() or None)
    if trimmed == "/session-audit" or trimmed.startswith("/session-audit "):
        return make_local_command("session_audit", trimmed[15:].strip() or None)
    if trimmed == "/session-handoff" or trimmed.startswith("/session-handoff "):
        return make_local_command("session_handoff", trimmed[17:].strip() or None)
    if trimmed == "/session" or trimmed.startswith("/session "):
        return make_local_command("session", trimmed[8:].strip() or None)
    return None
