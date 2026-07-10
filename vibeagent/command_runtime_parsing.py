from __future__ import annotations

from .command_types import LocalCommand, make_local_command


def parse_runtime_local_command(trimmed: str) -> LocalCommand | None:
    if trimmed == "/tools":
        return make_local_command("tools", None)
    if trimmed == "/tool" or trimmed.startswith("/tool "):
        return make_local_command("tool", trimmed[5:].strip() or None)
    if trimmed == "/tool-search" or trimmed.startswith("/tool-search "):
        return make_local_command("tool_search", trimmed[13:].strip() or None)
    if trimmed == "/permissions":
        return make_local_command("permissions", None)
    if trimmed == "/sandbox":
        return make_local_command("sandbox", None)
    if trimmed == "/checks" or trimmed.startswith("/checks "):
        return make_local_command("checks", trimmed[8:].strip() or None)
    if trimmed == "/check-suggested-checks" or trimmed.startswith("/check-suggested-checks "):
        return make_local_command("check_suggested_checks", trimmed[23:].strip() or None)
    if trimmed == "/run-suggested-checks" or trimmed.startswith("/run-suggested-checks "):
        return make_local_command("run_suggested_checks", trimmed[21:].strip() or None)
    if trimmed == "/commands" or trimmed.startswith("/commands "):
        return make_local_command("commands", trimmed[10:].strip() or None)
    if trimmed == "/related-tests" or trimmed.startswith("/related-tests "):
        return make_local_command("related_tests", trimmed[14:].strip() or None)
    if trimmed == "/focused-tests" or trimmed.startswith("/focused-tests "):
        return make_local_command("focused_test_commands", trimmed[15:].strip() or None)
    if trimmed == "/check-focused-tests" or trimmed.startswith("/check-focused-tests "):
        return make_local_command("check_focused_test_commands", trimmed[20:].strip() or None)
    if trimmed == "/run-focused-tests" or trimmed.startswith("/run-focused-tests "):
        return make_local_command("run_focused_test_commands", trimmed[18:].strip() or None)
    if trimmed == "/manifests" or trimmed.startswith("/manifests "):
        return make_local_command("manifests", trimmed[11:].strip() or None)
    if trimmed == "/instructions" or trimmed.startswith("/instructions "):
        return make_local_command("instructions", trimmed[14:].strip() or None)
    if trimmed == "/todos" or trimmed.startswith("/todos "):
        return make_local_command("todos", trimmed[7:].strip() or None)
    if trimmed == "/command" or trimmed.startswith("/command "):
        return make_local_command("command", trimmed[8:].strip() or None)
    if trimmed == "/run" or trimmed.startswith("/run "):
        return make_local_command("run", trimmed[5:].strip() or None)
    if trimmed == "/run-commands" or trimmed.startswith("/run-commands "):
        prefix = "/run-commands"
        return make_local_command("run_sequence", trimmed[len(prefix) :].strip() or None)
    if trimmed == "/run-seq" or trimmed.startswith("/run-seq "):
        return make_local_command("run_sequence", trimmed[9:].strip() or None)
    if trimmed == "/check-run-commands" or trimmed.startswith("/check-run-commands "):
        prefix = "/check-run-commands"
        return make_local_command("check_run_sequence", trimmed[len(prefix) :].strip() or None)
    if trimmed == "/check-run-seq" or trimmed.startswith("/check-run-seq "):
        return make_local_command("check_run_sequence", trimmed[15:].strip() or None)
    if trimmed == "/check-start" or trimmed.startswith("/check-start "):
        return make_local_command("check_start", trimmed[13:].strip() or None)
    if trimmed == "/start" or trimmed.startswith("/start "):
        return make_local_command("start", trimmed[7:].strip() or None)
    if trimmed == "/port" or trimmed.startswith("/port "):
        return make_local_command("port", trimmed[6:].strip() or None)
    if trimmed == "/http" or trimmed.startswith("/http "):
        return make_local_command("http", trimmed[6:].strip() or None)
    if trimmed == "/http-fetch" or trimmed.startswith("/http-fetch "):
        return make_local_command("http_fetch", trimmed[12:].strip() or None)
    return None
