from __future__ import annotations

from .prompt_observation_code_intel import format_code_intel_observation
from .prompt_observation_output import (
    format_output_contexts_observation,
    format_output_diagnostics_observation,
)
from .prompt_observation_checkpoint import format_checkpoint_observation
from .prompt_observation_edit import format_edit_observation
from .prompt_observation_git import format_git_observation
from .prompt_observation_project import format_project_observation
from .prompt_observation_read import format_read_observation
from .prompt_observation_review import format_review_observation
from .prompt_observation_runtime import format_runtime_observation
from .prompt_observation_session import format_session_observation
from .prompt_observation_utils import truncate
from .types import Observation


def format_observations(observations: list[Observation]) -> str:
    # Serialize prior observations in compact human-readable lines for next-turn reasoning.
    if not observations:
        return "No observations yet."

    lines: list[str] = []
    for index, observation in enumerate(observations, start=1):
        runtime_line = format_runtime_observation(index, observation)
        if runtime_line is not None:
            lines.append(runtime_line)
        elif (git_line := format_git_observation(index, observation)) is not None:
            lines.append(git_line)
        elif (review_line := format_review_observation(index, observation)) is not None:
            lines.append(review_line)
        elif (session_line := format_session_observation(index, observation)) is not None:
            lines.append(session_line)
        elif (checkpoint_line := format_checkpoint_observation(index, observation)) is not None:
            lines.append(checkpoint_line)
        elif (edit_line := format_edit_observation(index, observation)) is not None:
            lines.append(edit_line)
        elif (project_line := format_project_observation(index, observation)) is not None:
            lines.append(project_line)
        elif (read_line := format_read_observation(index, observation)) is not None:
            lines.append(read_line)
        elif observation.kind == "check_write_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_write_file {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "write_file":
            lines.append(f"{index}. write_file {observation.path}: {observation.message}")
        elif observation.kind == "check_write_files":
            parts = [f"{index}. check_write_files: {observation.message} ok={str(observation.ok).lower()}"]
            for file in observation.files:
                parts.append(
                    "\n".join(
                        [
                            f"file: {file.path} ok={str(file.ok).lower()} message={file.message}",
                            f"diff:\n{truncate(file.diff)}",
                        ]
                    )
                )
            lines.append("\n".join(parts))
        elif observation.kind == "write_files":
            parts = [f"{index}. write_files: {observation.message} ok={str(observation.ok).lower()}"]
            for file in observation.files:
                parts.append(f"file: {file.path} ok={str(file.ok).lower()} message={file.message}")
            lines.append("\n".join(parts))
        elif observation.kind == "output_contexts":
            lines.append(format_output_contexts_observation(index, observation))
        elif observation.kind == "output_diagnostics":
            lines.append(format_output_diagnostics_observation(index, observation))
        elif (code_intel_line := format_code_intel_observation(index, observation)) is not None:
            lines.append(code_intel_line)
        elif observation.kind == "finish":
            lines.append(f"{index}. finish: {observation.message}")
        elif observation.kind == "tool_error":
            lines.append(f"{index}. tool_error {observation.tool}: {observation.message}")
        elif observation.kind == "update_plan":
            lines.append(
                "\n".join(
                    [
                        f"{index}. update_plan: {observation.message}",
                        *[f"- {item.status}: {item.step}" for item in observation.plan],
                    ]
                )
            )
        else:
            lines.append(f"{index}. {observation.kind}: {getattr(observation, 'message', '')}")

    return "\n\n".join(lines)
