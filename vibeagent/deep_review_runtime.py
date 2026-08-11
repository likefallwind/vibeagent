from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from .deep_review_instructions import ReviewInstructions, read_review_instructions
from .deep_review_prompts import build_reviewer_action, build_verifier_action, review_system_prompt
from .redaction import redact_sensitive_text
from .types import (
    AgentLogger,
    ApprovalHandler,
    ApprovalPolicy,
    ChatClient,
    DeepReviewAction,
    DeepReviewObservation,
    DeepReviewPerspective,
    DeepReviewResult,
    DelegateTaskObservation,
)
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHooks
from .workspace_permissions import ProjectPermissions


DelegateExecutor = Callable[..., DelegateTaskObservation]

def execute_deep_review_action(
    workspace: RunWorkspace,
    action: DeepReviewAction,
    client: ChatClient,
    *,
    parent_iteration: int,
    max_output_tokens: int,
    model_retries: int,
    model_retry_delay_ms: int,
    model_timeout_ms: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    hooks: ProjectHooks,
    permissions: ProjectPermissions,
    tool_ceiling_names: frozenset[str] | None,
    review_id: str | None = None,
    delegate_executor: DelegateExecutor | None = None,
) -> DeepReviewObservation:
    instructions = read_review_instructions(workspace)
    if instructions.error is not None:
        return DeepReviewObservation(
            kind="deep_review",
            ok=False,
            results=[],
            verification_ok=False,
            summary="",
            base_ref=action.base_ref,
            target=action.target,
            instructions_path=instructions.path,
            message=instructions.error,
        )

    if delegate_executor is None:
        from .agent_delegate import execute_delegate_task_action

        delegate_executor = execute_delegate_task_action

    def run(perspective: DeepReviewPerspective) -> DeepReviewResult:
        delegate_action = build_reviewer_action(perspective, action)
        observation = delegate_executor(
            workspace,
            delegate_action,
            client,
            parent_iteration=parent_iteration,
            subagent_id=f"review-{review_id or parent_iteration}-{perspective}",
            max_output_tokens=max_output_tokens,
            model_retries=model_retries,
            model_retry_delay_ms=model_retry_delay_ms,
            model_timeout_ms=model_timeout_ms,
            command_timeout_ms=command_timeout_ms,
            logger=logger,
            approval_handler=approval_handler,
            approval_policy=approval_policy,
            hooks=hooks,
            permissions=permissions,
            tool_ceiling_names=tool_ceiling_names,
            additional_system_prompt=review_system_prompt(instructions),
        )
        return DeepReviewResult(
            perspective=perspective,
            ok=observation.ok,
            summary=observation.summary,
            iterations=observation.iterations,
            tool_calls=list(observation.tool_calls),
        )

    results_by_perspective: dict[str, DeepReviewResult] = {}
    with ThreadPoolExecutor(max_workers=len(action.perspectives)) as executor:
        futures = {executor.submit(run, perspective): perspective for perspective in action.perspectives}
        for future in as_completed(futures):
            perspective = futures[future]
            try:
                results_by_perspective[perspective] = future.result()
            except Exception as error:  # Keep one reviewer failure from discarding useful reports.
                results_by_perspective[perspective] = DeepReviewResult(
                    perspective=perspective,
                    ok=False,
                    summary=f"Reviewer failed: {redact_sensitive_text(str(error))[:2_000]}",
                    iterations=0,
                )

    results = [results_by_perspective[perspective] for perspective in action.perspectives]
    successful = sum(result.ok for result in results)
    try:
        verification = _verify_review_results(
            workspace,
            action,
            results,
            instructions,
            client,
            delegate_executor,
            parent_iteration=parent_iteration,
            review_id=review_id,
            max_output_tokens=max_output_tokens,
            model_retries=model_retries,
            model_retry_delay_ms=model_retry_delay_ms,
            model_timeout_ms=model_timeout_ms,
            command_timeout_ms=command_timeout_ms,
            logger=logger,
            approval_handler=approval_handler,
            approval_policy=approval_policy,
            hooks=hooks,
            permissions=permissions,
            tool_ceiling_names=tool_ceiling_names,
        )
    except Exception as error:
        verification = _failed_verification(
            f"Reviewer verification failed: {redact_sensitive_text(str(error))[:2_000]}"
        )
    return DeepReviewObservation(
        kind="deep_review",
        ok=successful == len(results) and verification.ok,
        results=results,
        verification_ok=verification.ok,
        summary=verification.summary,
        base_ref=action.base_ref,
        target=action.target,
        instructions_path=instructions.path,
        message=(
            f"Deep review completed: {successful}/{len(results)} reviewer(s) succeeded; "
            f"verification {'succeeded' if verification.ok else 'failed'}."
        ),
    )


def _verify_review_results(
    workspace: RunWorkspace,
    action: DeepReviewAction,
    results: list[DeepReviewResult],
    instructions: ReviewInstructions,
    client: ChatClient,
    delegate_executor: DelegateExecutor,
    *,
    parent_iteration: int,
    review_id: str | None,
    max_output_tokens: int,
    model_retries: int,
    model_retry_delay_ms: int,
    model_timeout_ms: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    hooks: ProjectHooks,
    permissions: ProjectPermissions,
    tool_ceiling_names: frozenset[str] | None,
) -> DelegateTaskObservation:
    candidates = [result for result in results if result.ok]
    if not candidates:
        return _failed_verification("No reviewer reports were available to verify.")
    verifier_action = build_verifier_action(action, candidates)
    return delegate_executor(
        workspace,
        verifier_action,
        client,
        parent_iteration=parent_iteration,
        subagent_id=f"review-{review_id or parent_iteration}-verifier",
        max_output_tokens=max_output_tokens,
        model_retries=model_retries,
        model_retry_delay_ms=model_retry_delay_ms,
        model_timeout_ms=model_timeout_ms,
        command_timeout_ms=command_timeout_ms,
        logger=logger,
        approval_handler=approval_handler,
        approval_policy=approval_policy,
        hooks=hooks,
        permissions=permissions,
        tool_ceiling_names=tool_ceiling_names,
        additional_system_prompt=review_system_prompt(instructions),
    )


def _failed_verification(summary: str) -> DelegateTaskObservation:
    return DelegateTaskObservation(
        kind="delegate_task",
        ok=False,
        task="Verify deep review findings",
        summary=summary,
        iterations=0,
        tool_calls=[],
        message="Deep review verification failed.",
    )


__all__ = ["execute_deep_review_action"]
