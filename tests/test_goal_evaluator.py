import unittest

from vibeagent.goal_evaluator import (
    MAX_GOAL_EVIDENCE_CHARS,
    GoalEvaluationError,
    evaluate_goal,
)
from vibeagent.goal_loop import goal_evidence, goal_turn_prompt
from vibeagent.goal_state import new_goal, record_goal_evaluation
from vibeagent.types import AssistantResponse, ModelUsage


class FakeClient:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = []

    def complete(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        return AssistantResponse(
            content=[{"type": "text", "text": self.text}],
            raw={},
            usage=ModelUsage(total_tokens=23),
        )


class GoalEvaluatorTests(unittest.TestCase):
    def test_evaluates_json_without_tools_and_counts_usage(self) -> None:
        client = FakeClient('{"achieved": false, "reason": "tests are missing"}')
        evaluation = evaluate_goal("ship", "evidence", client=client)
        self.assertFalse(evaluation.achieved)
        self.assertEqual(evaluation.reason, "tests are missing")
        self.assertEqual(evaluation.total_tokens, 23)
        messages, kwargs = client.calls[0]
        self.assertNotIn("tools", kwargs)
        self.assertIn("Goal:\nship", messages[1].content)

    def test_bounds_evidence_and_parses_fenced_json(self) -> None:
        client = FakeClient('```json\n{"achieved": true, "reason": "verified"}\n```')
        evaluate_goal("ship", "a" * (MAX_GOAL_EVIDENCE_CHARS + 100), client=client)
        content = client.calls[0][0][1].content
        self.assertLessEqual(len(content), MAX_GOAL_EVIDENCE_CHARS + 100)

    def test_rejects_malformed_or_incomplete_evaluation(self) -> None:
        for text in ("yes", '{"achieved": true}', '{"achieved": "yes", "reason": "ok"}'):
            with self.subTest(text=text), self.assertRaises(GoalEvaluationError):
                evaluate_goal("ship", "evidence", client=FakeClient(text), model_retries=0)

    def test_next_turn_includes_evaluator_reason(self) -> None:
        state = record_goal_evaluation(new_goal("ship", now=1), achieved=False, reason="lint fails")
        prompt = goal_turn_prompt(state, "focus on formatting")
        self.assertIn("focus on formatting", prompt)
        self.assertIn("lint fails", prompt)
        self.assertIn("ship", goal_evidence(state, "handoff", "latest"))


if __name__ == "__main__":
    unittest.main()
