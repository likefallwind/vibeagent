from __future__ import annotations

from .prompt_observation_output import (
    format_session_output_contexts_observation,
    format_session_output_diagnostics_observation,
)
from .prompt_observation_utils import truncate


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
        return "\n".join(
            [
                f"{index}. session_files {observation.run_id}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"files: {observation.shown_files}/{observation.file_count}",
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
        return "\n".join(
            [
                f"{index}. session_verification {observation.run_id}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"verification:\n{truncate(observation.verification)}",
            ]
        )

    if observation.kind == "session_audit":
        process_lines = [
            (
                f"active_process: {process.process_id} pid={process.pid} "
                f"cwd={process.cwd} command={process.command}"
            )
            for process in observation.active_background_processes[:20]
        ]
        return "\n".join(
            [
                f"{index}. session_audit {observation.run_id}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"ready: {str(observation.ready).lower()}",
                f"blockers: {len(observation.blockers)}",
                f"backgroundProcesses: started={observation.background_processes_started} active={len(observation.active_background_processes)}",
                *[f"blocker: {blocker}" for blocker in observation.blockers[:20]],
                *process_lines,
                f"audit:\n{truncate(observation.audit)}",
            ]
        )

    if observation.kind == "session_handoff":
        return "\n".join(
            [
                f"{index}. session_handoff {observation.run_id}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"handoff:\n{truncate(observation.handoff)}",
            ]
        )

    return None


__all__ = ["format_session_observation"]
