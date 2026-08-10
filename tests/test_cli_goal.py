import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from vibeagent.agent_result import AgentResult
from vibeagent.cli import main
from vibeagent.cli_context import OneShotPriorContext
from vibeagent.cli_interactive import run_interactive_loop
from vibeagent.cli_one_shot_code import _resolve_one_shot_goal
from vibeagent.goal_state import new_goal, read_session_goal, record_goal_evaluation, write_goal
from vibeagent.types import AssistantResponse
from vibeagent.workspace_core import create_run_workspace


class EvaluatorClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)
        self.calls = []

    def complete(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        return AssistantResponse(
            content=[{"type": "text", "text": next(self.responses)}],
            raw={},
        )


def agent_result(base: str, run_id: str = "goal-run") -> AgentResult:
    return AgentResult(
        success=True,
        message="turn complete",
        run_dir=Path(base) / ".vibeagent" / "sessions" / run_id,
        run_id=run_id,
        iterations=1,
        observations=[],
        steps=[],
    )


class CliGoalTests(unittest.TestCase):
    def test_one_shot_goal_continues_until_evaluator_accepts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-goal-") as base:
            client = EvaluatorClient(
                [
                    '{"achieved": false, "reason": "tests missing"}',
                    '{"achieved": true, "reason": "tests pass"}',
                ]
            )
            run_agent = Mock(return_value=agent_result(base))
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client", return_value=client),
                patch("vibeagent.cli.run_agent", run_agent),
                patch("vibeagent.cli.get_resume_context", return_value=("goal-run", "handoff", "ok")),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "/goal", "all tests pass"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(run_agent.call_count, 2)
            self.assertIn("all tests pass", run_agent.call_args_list[0].args[0])
            self.assertIn("tests missing", run_agent.call_args_list[1].args[0])
            self.assertNotIn("workspace", run_agent.call_args_list[0].kwargs)
            self.assertEqual(run_agent.call_args_list[1].kwargs["workspace"].run_id, "goal-run")
            self.assertNotIn("task_source_run_id", run_agent.call_args_list[1].kwargs)
            self.assertNotIn("tools", client.calls[0][1])
            stored = read_session_goal(base, "goal-run")
            self.assertEqual(stored.status, "achieved")  # type: ignore[union-attr]
            self.assertEqual(stored.evaluated_turns, 2)  # type: ignore[union-attr]

    def test_interactive_goal_runs_immediately_and_reports_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-goal-") as base:
            client = EvaluatorClient(['{"achieved": true, "reason": "verified"}'])
            run_agent = Mock(return_value=agent_result(base))
            stdout = io.StringIO()
            old_cwd = Path.cwd()
            try:
                import os

                os.chdir(base)
                with (
                    patch("builtins.input", side_effect=["/goal verified build", "/goal", "/exit"]),
                    patch("vibeagent.cli_interactive.prompt_project_permission_trust", return_value=False),
                    redirect_stdout(stdout),
                ):
                    exit_code = run_interactive_loop(
                        command_namespace={},
                        create_chat_client_func=lambda _env: client,
                        run_agent_func=run_agent,
                        get_resume_context_func=lambda _run_id: ("goal-run", "handoff", "ok"),
                    )
            finally:
                os.chdir(old_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(run_agent.call_count, 1)
            output = stdout.getvalue()
            self.assertIn("Goal achieved.", output)
            self.assertIn("Goal (achieved): verified build", output)

    def test_interactive_interruption_keeps_goal_active_until_clear(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-goal-") as base:
            client = EvaluatorClient(['{"achieved": false, "reason": "more work"}'])
            run_agent = Mock(side_effect=[agent_result(base), KeyboardInterrupt()])
            stdout = io.StringIO()
            old_cwd = Path.cwd()
            try:
                import os

                os.chdir(base)
                with (
                    patch(
                        "builtins.input",
                        side_effect=["/goal verified build", "/goal", "/goal clear", "/goal", "/exit"],
                    ),
                    patch("vibeagent.cli_interactive.prompt_project_permission_trust", return_value=False),
                    redirect_stdout(stdout),
                ):
                    exit_code = run_interactive_loop(
                        command_namespace={},
                        create_chat_client_func=lambda _env: client,
                        run_agent_func=run_agent,
                        get_resume_context_func=lambda _run_id: ("goal-run", "handoff", "ok"),
                    )
            finally:
                os.chdir(old_cwd)

            self.assertEqual(exit_code, 0)
            output = stdout.getvalue()
            self.assertIn("Interrupted. Goal remains active.", output)
            self.assertIn("Goal (active): verified build", output)
            self.assertIn("Goal cleared.", output)
            self.assertIn("No goal is set.", output)
            self.assertEqual(read_session_goal(base, "goal-run").status, "cleared")  # type: ignore[union-attr]

    def test_one_shot_restores_active_goal_only_for_explicit_resume(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-goal-") as base:
            workspace = create_run_workspace(base, run_id="source-run")
            state = record_goal_evaluation(
                new_goal("release ready", now=1),
                achieved=False,
                reason="tests pending",
                total_tokens=12,
            )
            write_goal(workspace, state)

            restored, steering = _resolve_one_shot_goal(
                "focus tests",
                OneShotPriorContext(source="resume", run_id="source-run"),
                Path(base),
            )
            self.assertEqual(steering, "focus tests")
            self.assertEqual(restored.condition, "release ready")  # type: ignore[union-attr]
            self.assertEqual(restored.evaluated_turns, 0)  # type: ignore[union-attr]
            self.assertEqual(restored.total_tokens, 0)  # type: ignore[union-attr]

            automatic, _ = _resolve_one_shot_goal(
                "new task",
                OneShotPriorContext(source="auto_compact", run_id="source-run"),
                Path(base),
            )
            self.assertIsNone(automatic)


if __name__ == "__main__":
    unittest.main()
