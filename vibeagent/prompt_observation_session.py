from __future__ import annotations

from .prompt_observation_output import (
    format_session_output_contexts_observation,
    format_session_output_diagnostics_observation,
)
from .prompt_observation_utils import truncate


def format_verification_command_lines(label: str, commands: list[dict[str, object]], total: int) -> list[str]:
    if not commands:
        return [f"{label}: none"]
    lines = [f"{label}: {len(commands)}/{total}"]
    for command in commands:
        cwd = str(command.get("cwd") or ".")
        suffix = "" if cwd == "." else f" (cwd: {cwd})"
        reason = command.get("failureReason")
        reason_suffix = f" ({reason})" if isinstance(reason, str) and reason else ""
        lines.append(f"- {command.get('command') or ''}{suffix}{reason_suffix}")
    return lines


def format_selected_session_verification_command_lines(
    commands: list[dict[str, object]],
    total: int,
    ran_count: int,
    stopped_early: bool,
) -> list[str]:
    if not commands:
        return ["selectedCommands: none"]
    lines = [f"selectedCommands: {len(commands)}/{total}"]
    for index, command in enumerate(commands):
        cwd = str(command.get("cwd") or ".")
        cwd_suffix = "" if cwd == "." else f" (cwd: {cwd})"
        run_status = "ran" if index < ran_count else "notRun"
        reason = command.get("failureReason")
        reason_suffix = f" ({reason})" if isinstance(reason, str) and reason else ""
        status = str(command.get("status") or "").strip()
        status_suffix = f" source={status}" if status else ""
        lines.append(f"- {command.get('command') or ''}{cwd_suffix} [{run_status}{status_suffix}]{reason_suffix}")
    if stopped_early and len(commands) > ran_count:
        lines.append(f"selectedCommandsNotRun: {len(commands) - ran_count}")
    return lines


def format_file_reference_lines(
    references: object,
    file_count: int,
    shown_file_count: int,
    files_truncated: bool,
) -> list[str]:
    file_references = [
        item
        for item in references
        if isinstance(item, dict) and str(item.get("path") or "").strip()
    ] if isinstance(references, list) else []
    file_lines: list[str] = []
    if file_count or file_references:
        file_lines.append(f"files: {shown_file_count}/{file_count} truncated={str(files_truncated).lower()}")
        for item in file_references[:20]:
            path = str(item.get("path") or "").strip()
            uses = [
                str(use).strip()
                for use in item.get("uses", [])
                if isinstance(use, str) and str(use).strip()
            ]
            suffix = f" uses={','.join(uses)}" if uses else ""
            file_lines.append(f"file: {path}{suffix}")
    return file_lines


def format_session_observation(index: int, observation: object) -> str | None:
    if observation.kind == "session_summary":
        return "\n".join(
            [
                f"{index}. session_summary {observation.run_id}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"summary:\n{truncate(observation.summary)}",
                f"recent:\n{truncate(chr(10).join(observation.recent_sessions))}",
            ]
        )

    if observation.kind == "session_plan":
        return "\n".join(
            [
                f"{index}. session_plan {observation.run_id}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"plan:\n{truncate(observation.plan)}",
            ]
        )

    if observation.kind == "session_transcript":
        return "\n".join(
            [
                f"{index}. session_transcript {observation.run_id}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"transcript:\n{truncate(observation.transcript)}",
            ]
        )

    if observation.kind == "session_search":
        return "\n".join(
            [
                f"{index}. session_search {observation.run_id}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"query: {observation.query}",
                f"matches: {observation.shown_matches}/{observation.total_matches}",
                f"timeline:\n{truncate(observation.matches)}",
            ]
        )

    if observation.kind == "session_commands":
        return "\n".join(
            [
                f"{index}. session_commands {observation.run_id}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"commands: {observation.shown_commands}/{observation.command_count}",
                f"results:\n{truncate(observation.commands)}",
            ]
        )

    if observation.kind == "session_output_contexts":
        return format_session_output_contexts_observation(index, observation)

    if observation.kind == "session_output_diagnostics":
        return format_session_output_diagnostics_observation(index, observation)

    if observation.kind == "session_files":
        file_lines = format_file_reference_lines(
            getattr(observation, "file_references", []),
            int(getattr(observation, "file_count", 0) or 0),
            int(getattr(observation, "shown_files", 0) or 0),
            bool(getattr(observation, "files_truncated", False)),
        )
        if not file_lines:
            file_lines = [f"files: {observation.shown_files}/{observation.file_count}"]
        return "\n".join(
            [
                f"{index}. session_files {observation.run_id}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                *file_lines,
                f"entries:\n{truncate(observation.files)}",
            ]
        )

    if observation.kind == "session_failures":
        return "\n".join(
            [
                f"{index}. session_failures {observation.run_id}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"failures: {observation.shown_failures}/{observation.failure_count}",
                f"entries:\n{truncate(observation.failures)}",
            ]
        )

    if observation.kind == "session_verification":
        verified_commands = getattr(observation, "verified_commands", [])
        pending_commands = getattr(observation, "pending_commands", [])
        failed_commands = getattr(observation, "failed_commands", [])
        verified_count = int(getattr(observation, "verified_count", len(verified_commands)) or 0)
        pending_count = int(getattr(observation, "pending_count", len(pending_commands)) or 0)
        failed_count = int(getattr(observation, "failed_count", len(failed_commands)) or 0)
        command_lines: list[str] = []
        command_lines.extend(format_verification_command_lines("verifiedCommands", verified_commands, verified_count))
        command_lines.extend(format_verification_command_lines("pendingCommands", pending_commands, pending_count))
        command_lines.extend(format_verification_command_lines("failedCommands", failed_commands, failed_count))
        return "\n".join(
            [
                f"{index}. session_verification {observation.run_id}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"truncated: {str(bool(getattr(observation, 'verification_truncated', False))).lower()}",
                "commands:",
                truncate("\n".join(command_lines)),
                f"verification:\n{truncate(observation.verification)}",
            ]
        )

    if observation.kind == "run_session_verification":
        selected_commands = [
            command
            for command in getattr(observation, "selected_commands", [])
            if isinstance(command, dict)
        ]
        selected_lines = format_selected_session_verification_command_lines(
            selected_commands,
            int(getattr(observation, "selected_count", len(selected_commands)) or 0),
            len(getattr(observation, "results", []) or []),
            bool(getattr(observation, "stopped_early", False)),
        )
        lines = [
            f"{index}. run_session_verification {observation.run_id}: {observation.message}",
            f"ok: {str(observation.ok).lower()}",
            f"selected: {observation.selected_count}",
            f"pendingTotal: {observation.pending_count}",
            f"failedTotal: {observation.failed_count}",
            f"stoppedEarly: {str(observation.stopped_early).lower()}",
            "commands:",
            truncate("\n".join(selected_lines)),
        ]
        for result in observation.results:
            lines.extend(
                [
                    f"command: {result.command}",
                    f"cwd: {result.cwd}",
                    f"exitCode: {result.exit_code}",
                    f"timedOut: {str(result.timed_out).lower()}",
                    f"stdout:\n{truncate(result.stdout)}",
                    f"stderr:\n{truncate(result.stderr)}",
                ]
            )
        return "\n".join(lines)

    if observation.kind == "session_audit":
        process_lines = [
            (
                f"active_process: {process.process_id} pid={process.pid} "
                f"cwd={process.cwd} command={process.command}"
            )
            for process in observation.active_background_processes[:20]
        ]
        completion_ready = getattr(observation, "completion_ready", None)
        completion_lines = []
        if completion_ready is not None:
            completion_lines.append(f"completionReady: {str(completion_ready).lower()}")
        completion_lines.extend(f"completionBlocker: {blocker}" for blocker in observation.completion_blockers[:20])
        completion_lines.extend(
            f"latestCompletionBlocker: {blocker}" for blocker in observation.latest_completion_blockers[:20]
        )
        file_lines = format_file_reference_lines(
            getattr(observation, "file_references", []),
            int(getattr(observation, "file_count", 0) or 0),
            int(getattr(observation, "shown_file_count", 0) or 0),
            bool(getattr(observation, "files_truncated", False)),
        )
        return "\n".join(
            [
                f"{index}. session_audit {observation.run_id}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"ready: {str(observation.ready).lower()}",
                f"blockers: {len(observation.blockers)}",
                f"backgroundProcesses: started={observation.background_processes_started} active={len(observation.active_background_processes)}",
                *[f"blocker: {blocker}" for blocker in observation.blockers[:20]],
                *file_lines,
                *completion_lines,
                *process_lines,
                f"audit:\n{truncate(observation.audit)}",
            ]
        )

    if observation.kind == "session_handoff":
        ready = getattr(observation, "ready", None)
        readiness_lines = []
        if ready is not None:
            readiness_lines.append(f"ready: {str(ready).lower()}")
        status = str(getattr(observation, "status", "") or "").strip()
        if status:
            readiness_lines.append(f"status: {status}")
        blockers = [str(blocker).strip() for blocker in getattr(observation, "blockers", []) if str(blocker).strip()]
        if blockers:
            readiness_lines.append(f"blockers: {len(blockers)}")
            readiness_lines.extend(f"blocker: {blocker}" for blocker in blockers[:20])
        active_processes = getattr(observation, "active_background_processes", [])
        background_processes_started = int(getattr(observation, "background_processes_started", 0) or 0)
        if background_processes_started or active_processes:
            readiness_lines.append(
                f"backgroundProcesses: started={background_processes_started} active={len(active_processes)}"
            )
            readiness_lines.extend(
                (
                    f"active_process: {process.process_id} pid={process.pid} "
                    f"cwd={process.cwd} command={process.command}"
                )
                for process in active_processes[:20]
            )
        verified_commands = getattr(observation, "verified_commands", [])
        pending_commands = getattr(observation, "pending_commands", [])
        failed_commands = getattr(observation, "failed_commands", [])
        verified_count = int(getattr(observation, "verified_count", len(verified_commands)) or 0)
        pending_count = int(getattr(observation, "pending_count", len(pending_commands)) or 0)
        failed_count = int(getattr(observation, "failed_count", len(failed_commands)) or 0)
        verification_lines: list[str] = []
        verification_lines.extend(format_verification_command_lines("verifiedCommands", verified_commands, verified_count))
        verification_lines.extend(format_verification_command_lines("pendingCommands", pending_commands, pending_count))
        verification_lines.extend(format_verification_command_lines("failedCommands", failed_commands, failed_count))
        pending_plan_items = [
            item
            for item in getattr(observation, "pending_plan_items", [])
            if isinstance(item, dict) and str(item.get("step") or "").strip()
        ]
        pending_plan_count = int(getattr(observation, "pending_plan_count", len(pending_plan_items)) or 0)
        plan_items_count = int(getattr(observation, "plan_items_count", 0) or 0)
        plan_lines: list[str] = []
        if plan_items_count or pending_plan_count:
            plan_lines.append(
                "plan: "
                f"items={plan_items_count} "
                f"pending={len(pending_plan_items)}/{pending_plan_count} "
                f"inProgress={str(bool(getattr(observation, 'plan_in_progress', False))).lower()}"
            )
            for item in pending_plan_items[:20]:
                plan_lines.append(f"plan_item: {item.get('status') or ''}: {item.get('step') or ''}")
        file_lines = format_file_reference_lines(
            getattr(observation, "file_references", []),
            int(getattr(observation, "file_count", 0) or 0),
            int(getattr(observation, "shown_file_count", 0) or 0),
            bool(getattr(observation, "files_truncated", False)),
        )
        completion_ready = getattr(observation, "completion_ready", None)
        if completion_ready is not None:
            readiness_lines.append(f"completionReady: {str(completion_ready).lower()}")
        completion_lines = [
            f"completionBlocker: {blocker}"
            for blocker in getattr(observation, "completion_blockers", [])[:20]
        ]
        completion_lines.extend(
            f"latestCompletionBlocker: {blocker}"
            for blocker in getattr(observation, "latest_completion_blockers", [])[:20]
        )
        return "\n".join(
            [
                f"{index}. session_handoff {observation.run_id}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                *readiness_lines,
                *plan_lines,
                *file_lines,
                "commands:",
                *verification_lines,
                *completion_lines,
                f"handoff:\n{truncate(observation.handoff)}",
            ]
        )

    return None


__all__ = ["format_session_observation"]
