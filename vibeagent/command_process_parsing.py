from __future__ import annotations

from .command_types import LocalCommand, make_local_command


def parse_process_local_command(trimmed: str) -> LocalCommand | None:
    if trimmed == "/env":
        return make_local_command("env", None)
    if trimmed == "/background-agents":
        return make_local_command("background_agents", None)
    if trimmed == "/background-agent-log" or trimmed.startswith("/background-agent-log "):
        return make_local_command("background_agent_log", trimmed[21:].strip() or None)
    if trimmed == "/stop-background-agent" or trimmed.startswith("/stop-background-agent "):
        return make_local_command("stop_background_agent", trimmed[22:].strip() or None)
    if trimmed == "/send-background-agent" or trimmed.startswith("/send-background-agent "):
        return make_local_command("send_background_agent", trimmed[23:].strip() or None)
    if trimmed == "/respawn-background-agent" or trimmed.startswith("/respawn-background-agent "):
        return make_local_command("respawn_background_agent", trimmed[26:].strip() or None)
    if trimmed == "/remove-background-agent" or trimmed.startswith("/remove-background-agent "):
        return make_local_command("remove_background_agent", trimmed[24:].strip() or None)
    if trimmed == "/processes":
        return make_local_command("processes", None)
    if trimmed == "/process" or trimmed.startswith("/process "):
        return make_local_command("process", trimmed[9:].strip() or None)
    if trimmed == "/process-output-contexts" or trimmed.startswith("/process-output-contexts "):
        return make_local_command("process_output_contexts", trimmed[24:].strip() or None)
    process_diagnostics_prefix = "/process-output-diagnostics"
    if trimmed == process_diagnostics_prefix or trimmed.startswith(process_diagnostics_prefix + " "):
        return make_local_command("process_output_diagnostics", trimmed[len(process_diagnostics_prefix) :].strip() or None)
    if trimmed == "/wait-process" or trimmed.startswith("/wait-process "):
        return make_local_command("wait_process", trimmed[13:].strip() or None)
    if trimmed == "/check-write-process" or trimmed.startswith("/check-write-process "):
        return make_local_command("check_write_process", trimmed[21:].strip() or None)
    if trimmed == "/write-process" or trimmed.startswith("/write-process "):
        return make_local_command("write_process", trimmed[14:].strip() or None)
    if trimmed == "/check-stop-process" or trimmed.startswith("/check-stop-process "):
        return make_local_command("check_stop_process", trimmed[20:].strip() or None)
    if trimmed == "/stop-process" or trimmed.startswith("/stop-process "):
        return make_local_command("stop_process", trimmed[13:].strip() or None)
    if trimmed == "/check-stop-processes" or trimmed == "/check-stop-all-processes":
        return make_local_command("check_stop_all_processes", None)
    if trimmed == "/stop-processes" or trimmed == "/stop-all-processes":
        return make_local_command("stop_all_processes", None)
    return None
