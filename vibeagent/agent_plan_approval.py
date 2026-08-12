from __future__ import annotations

from dataclasses import replace

from .agent_delegate_context import CODE_DELEGATE_SYSTEM_PROMPT, PLAN_DELEGATE_SYSTEM_PROMPT
from .subagent_transcripts import SubagentTranscript
from .types import ChatMessage, DelegateTaskAction


class PlanApprovalError(ValueError):
    pass


def prepare_plan_approval(
    transcript: SubagentTranscript,
    feedback: str,
) -> tuple[DelegateTaskAction, SubagentTranscript, str]:
    action = transcript.action
    if action.teammate_name is None:
        raise PlanApprovalError("Plan approval is only available for named teammates.")
    if action.mode != "plan":
        raise PlanApprovalError(
            f"Teammate {transcript.subagent_id} is not awaiting plan approval."
        )
    if transcript.status != "completed":
        raise PlanApprovalError(
            f"Teammate {transcript.subagent_id} plan cannot be approved while its status is {transcript.status}."
        )
    resumed_action = replace(action, mode="code", run_in_background=True)
    resumed_transcript = replace(
        transcript,
        action=resumed_action,
        messages=_code_mode_messages(transcript),
    )
    followup = (
        "The lead approved your plan. Continue with the same task and implement the approved plan now.\n\n"
        f"Lead approval note:\n{feedback}"
    )
    return resumed_action, resumed_transcript, followup


def _code_mode_messages(transcript: SubagentTranscript) -> list[ChatMessage]:
    messages = list(transcript.messages)
    if not messages or not isinstance(messages[0].content, str):
        raise PlanApprovalError(
            f"Teammate {transcript.subagent_id} plan transcript has no valid system prompt."
        )
    system_content = messages[0].content
    if not system_content.startswith(PLAN_DELEGATE_SYSTEM_PROMPT):
        raise PlanApprovalError(
            f"Teammate {transcript.subagent_id} plan transcript has an unexpected system prompt."
        )
    messages[0] = ChatMessage(
        role="system",
        content=f"{CODE_DELEGATE_SYSTEM_PROMPT}{system_content[len(PLAN_DELEGATE_SYSTEM_PROMPT):]}",
    )
    return messages
