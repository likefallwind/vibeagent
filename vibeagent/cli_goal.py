from __future__ import annotations

from pathlib import Path

from .agent_result import AgentResult
from .config import ExecutionConfig
from .goal_evaluator import GoalEvaluation, evaluate_goal
from .goal_loop import goal_evidence
from .goal_state import GoalState, record_goal_evaluation, write_goal
from .workspace_core import create_local_workspace


def evaluate_and_store_goal(
    state: GoalState,
    result: AgentResult,
    resume_context: str | None,
    *,
    client: object,
    execution_config: ExecutionConfig,
    project_root: Path,
    agent_tokens: int = 0,
) -> tuple[GoalState, GoalEvaluation]:
    workspace = create_local_workspace(project_root, result.run_id)
    write_goal(workspace, state)
    evaluation = evaluate_goal(
        state.condition,
        goal_evidence(state, resume_context, result.message),
        client=client,  # type: ignore[arg-type]
        model_retries=execution_config.model_retries,
        model_retry_delay_ms=execution_config.model_retry_delay_ms,
        model_timeout_ms=execution_config.model_timeout_ms,
    )
    updated = record_goal_evaluation(
        state,
        achieved=evaluation.achieved,
        reason=evaluation.reason,
        total_tokens=max(0, agent_tokens) + evaluation.total_tokens,
    )
    write_goal(workspace, updated)
    return updated, evaluation
