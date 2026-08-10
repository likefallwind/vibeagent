from __future__ import annotations

from .goal_state import GoalState


def goal_turn_prompt(state: GoalState, steering_task: str | None = None) -> str:
    parts = [
        "Continue working autonomously until this goal is fully achieved:",
        state.condition,
    ]
    if steering_task and steering_task.strip() and steering_task.strip() != state.condition:
        parts.extend(["", "User steering for this turn:", steering_task.strip()])
    if state.last_reason:
        parts.extend(["", "The independent evaluator says the goal is not achieved yet:", state.last_reason])
    parts.extend(
        [
            "",
            "Use the available tools, preserve approval requirements, and report concrete verification evidence.",
        ]
    )
    return "\n".join(parts)


def goal_evidence(state: GoalState, resume_context: str | None, result_message: str) -> str:
    parts = [f"Goal condition: {state.condition}"]
    if resume_context:
        parts.extend(["", "Session handoff:", resume_context])
    parts.extend(["", "Latest agent report:", result_message])
    return "\n".join(parts)
