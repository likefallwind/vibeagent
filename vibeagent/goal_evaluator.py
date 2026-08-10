from __future__ import annotations

from dataclasses import dataclass
import json
import re

from .chat import complete_chat_with_retries
from .minimax import content_blocks_to_text
from .types import AssistantResponse, ChatClient, ChatMessage


MAX_GOAL_EVIDENCE_CHARS = 40_000
GOAL_EVALUATOR_MAX_TOKENS = 512
GOAL_EVALUATOR_PROMPT = """You are an independent completion evaluator for a coding agent.
Decide whether the stated goal is fully achieved using only the supplied conversation evidence.
Do not assume unreported work happened. A claim of completion without relevant verification is insufficient.
Return exactly one JSON object with keys achieved (boolean) and reason (short string).
You have no tools and cannot grant approvals or answer pending user questions."""


class GoalEvaluationError(ValueError):
    pass


@dataclass(frozen=True)
class GoalEvaluation:
    achieved: bool
    reason: str
    total_tokens: int = 0


def evaluate_goal(
    condition: str,
    evidence: str,
    *,
    client: ChatClient,
    model_retries: int = 1,
    model_retry_delay_ms: int = 250,
    model_timeout_ms: int = 120_000,
) -> GoalEvaluation:
    bounded = evidence[-MAX_GOAL_EVIDENCE_CHARS:]
    response = complete_chat_with_retries(
        client,
        [
            ChatMessage(role="system", content=GOAL_EVALUATOR_PROMPT),
            ChatMessage(
                role="user",
                content=f"Goal:\n{condition}\n\nConversation evidence:\n{bounded}",
            ),
        ],
        max_output_tokens=GOAL_EVALUATOR_MAX_TOKENS,
        model_retries=model_retries,
        model_retry_delay_ms=model_retry_delay_ms,
        model_timeout_ms=model_timeout_ms,
    )
    if isinstance(response, str):
        text = response
        total_tokens = 0
    elif isinstance(response, AssistantResponse):
        text = content_blocks_to_text(response.content)
        usage = response.usage
        total_tokens = usage.total_tokens or 0 if usage is not None else 0
    else:
        raise GoalEvaluationError("Goal evaluator returned an unsupported response.")
    payload = _parse_evaluation_json(text)
    achieved = payload.get("achieved")
    reason = payload.get("reason")
    if not isinstance(achieved, bool) or not isinstance(reason, str) or not reason.strip():
        raise GoalEvaluationError("Goal evaluator response must contain boolean achieved and non-empty reason.")
    return GoalEvaluation(achieved, reason.strip()[:4_000], total_tokens)


def _parse_evaluation_json(text: str) -> dict[str, object]:
    stripped = text.strip()
    candidates = [stripped]
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL | re.IGNORECASE)
    if fenced:
        candidates.append(fenced.group(1))
    first = stripped.find("{")
    last = stripped.rfind("}")
    if first >= 0 and last > first:
        candidates.append(stripped[first : last + 1])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise GoalEvaluationError("Goal evaluator did not return valid JSON.")
