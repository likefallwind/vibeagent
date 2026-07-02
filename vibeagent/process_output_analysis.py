from __future__ import annotations

from dataclasses import replace

from .output_conversion import output_context_results_from_dicts, output_diagnostics_from_dicts
from .types import CommandResult, ReadProcessObservation, RunCommandAction, RunCommandItem, WaitProcessObservation
from .workspace import read_output_contexts_result, read_output_diagnostics_result
from .workspace_core import RunWorkspace


def attach_output_analysis_to_command_result(
    workspace: RunWorkspace,
    action: RunCommandAction | RunCommandItem,
    result: CommandResult,
) -> CommandResult:
    auto_extract_diagnostics = (
        not action.extract_output_contexts
        and not action.extract_output_diagnostics
        and command_result_failed(result)
    )
    if not action.extract_output_contexts and not action.extract_output_diagnostics and not auto_extract_diagnostics:
        return result
    text = "\n".join(part for part in [result.stdout, result.stderr] if part)
    if not text.strip():
        return result
    if action.extract_output_diagnostics or auto_extract_diagnostics:
        try:
            diagnostics_result = read_output_diagnostics_result(
                workspace,
                text,
                context_lines=action.context_lines,
                max_diagnostics=action.max_diagnostics,
                max_contexts=action.max_contexts,
                max_bytes_per_context=action.max_bytes_per_context,
            )
        except ValueError:
            return result
        return replace(
            result,
            output_contexts=output_context_results_from_dicts(diagnostics_result["contexts"]),
            output_context_total_refs=int(diagnostics_result["total_refs"]),
            output_contexts_truncated=bool(diagnostics_result["contexts_truncated"]),
            output_diagnostics=output_diagnostics_from_dicts(diagnostics_result["diagnostics"]),
            output_diagnostic_total=int(diagnostics_result["total_diagnostics"]),
            output_diagnostics_truncated=bool(diagnostics_result["diagnostics_truncated"]),
        )
    if action.extract_output_contexts:
        try:
            contexts_result = read_output_contexts_result(
                workspace,
                text,
                context_lines=action.context_lines,
                max_contexts=action.max_contexts,
                max_bytes_per_context=action.max_bytes_per_context,
            )
        except ValueError:
            return result
        return replace(
            result,
            output_contexts=output_context_results_from_dicts(contexts_result["contexts"]),
            output_context_total_refs=int(contexts_result["total_refs"]),
            output_contexts_truncated=bool(contexts_result["truncated"]),
        )
    return result


def command_result_failed(result: CommandResult) -> bool:
    if result.timed_out:
        return True
    if result.exit_code is None:
        return True
    return result.exit_code != 0


def attach_output_analysis_to_process_observation(
    workspace: RunWorkspace,
    observation: ReadProcessObservation | WaitProcessObservation,
) -> ReadProcessObservation | WaitProcessObservation:
    if not process_observation_failed(observation):
        return observation
    text = "\n".join(part for part in [observation.stdout, observation.stderr] if part)
    if not text.strip():
        return observation
    try:
        diagnostics_result = read_output_diagnostics_result(
            workspace,
            text,
            context_lines=2,
            max_diagnostics=50,
            max_contexts=20,
            max_bytes_per_context=20_000,
        )
    except ValueError:
        return observation
    return replace(
        observation,
        output_contexts=output_context_results_from_dicts(diagnostics_result["contexts"]),
        output_context_total_refs=int(diagnostics_result["total_refs"]),
        output_contexts_truncated=bool(diagnostics_result["contexts_truncated"]),
        output_diagnostics=output_diagnostics_from_dicts(diagnostics_result["diagnostics"]),
        output_diagnostic_total=int(diagnostics_result["total_diagnostics"]),
        output_diagnostics_truncated=bool(diagnostics_result["diagnostics_truncated"]),
    )


def process_observation_failed(observation: ReadProcessObservation | WaitProcessObservation) -> bool:
    if not observation.ok:
        return False
    if observation.running:
        return False
    if observation.exit_code is None:
        return True
    return observation.exit_code != 0
