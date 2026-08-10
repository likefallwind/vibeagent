from __future__ import annotations

import unittest
from types import SimpleNamespace

from vibeagent.prompt_observation_mcp import format_mcp_observation
from vibeagent.prompt_observation_project import format_project_observation
from vibeagent.prompt_observations import format_observations
from vibeagent.prompt_observation_project_commands import format_command_metadata


class PromptObservationProjectTests(unittest.TestCase):
    def test_format_isolated_delegate_exposes_integration_location(self) -> None:
        result = SimpleNamespace(
            kind="delegate_task",
            task_id="delegate-2-1",
            task="Implement parser",
            message="Completed in an isolated worktree.",
            ok=True,
            mode="code",
            background=False,
            running=False,
            iterations=2,
            agent="writer",
            isolation="worktree",
            worktree_path="/repo/.vibeagent/worktrees/subagent-1",
            worktree_branch="vibeagent/subagent-1",
            worktree_preserved=True,
            summary="Implemented parser and tests.",
        )

        text = format_project_observation(1, result)
        task_output = format_observations(
            [
                SimpleNamespace(
                    kind="task_output",
                    task_id="delegate-2-1",
                    message="completed",
                    result=result,
                )
            ]
        )

        self.assertIn("worktree=/repo/.vibeagent/worktrees/subagent-1", text or "")
        self.assertIn("branch=vibeagent/subagent-1", text or "")
        self.assertIn("summary:\nImplemented parser and tests.", text or "")
        self.assertIn("preserved=true", task_output)

    def test_format_command_metadata_keeps_common_field_order(self) -> None:
        command = SimpleNamespace(
            cwd=".",
            command="npm test",
            available=True,
            missing_tool=None,
            source="scripts.test",
            reason="unit tests",
        )

        self.assertEqual(
            format_command_metadata("check", command, [("source", command.source), ("reason", command.reason)]),
            "check: cwd=. command=npm test available=true missingTool=. source=scripts.test reason=unit tests",
        )

    def test_format_command_metadata_preserves_pre_availability_fields(self) -> None:
        command = SimpleNamespace(
            cwd=".",
            command="python -m unittest tests.test_agent",
            available=False,
            missing_tool="python",
            test_path="tests/test_agent.py",
            source="vibeagent/agent.py",
            reason="related test",
        )

        self.assertEqual(
            format_command_metadata(
                "command",
                command,
                [("source", command.source), ("reason", command.reason)],
                pre_availability_fields=[("test", command.test_path)],
            ),
            (
                "command: cwd=. command=python -m unittest tests.test_agent "
                "test=tests/test_agent.py available=false missingTool=python "
                "source=vibeagent/agent.py reason=related test"
            ),
        )

    def test_project_observation_dispatches_command_observations(self) -> None:
        text = format_project_observation(
            2,
            SimpleNamespace(
                kind="suggest_checks",
                message="checks found",
                checks=[
                    SimpleNamespace(
                        cwd=".",
                        command="python3 -m unittest",
                        available=True,
                        missing_tool="",
                        source="unittest",
                        reason="full suite",
                    )
                ],
                total=1,
                truncated=False,
                changed_files=[],
            ),
        )

        self.assertEqual(
            text,
            (
                "2. suggest_checks: checks found shown=1/1 truncated=false\n"
                "check: cwd=. command=python3 -m unittest available=true missingTool=. source=unittest reason=full suite"
            ),
        )

    def test_format_mcp_call_includes_status_and_output(self) -> None:
        text = format_mcp_observation(
            3,
            SimpleNamespace(
                kind="mcp_call",
                server="docs",
                name="search",
                message="completed",
                ok=True,
                is_error=False,
                truncated=False,
                max_output_chars=4000,
                timeout_ms=2000,
                error="",
                output="result body",
            ),
        )

        self.assertEqual(
            text,
            (
                "3. mcp_call docs/search: completed\n"
                "ok: true isError=false truncated=false maxOutputChars=4000 timeoutMs=2000\n"
                "error: none\n"
                "output:\n"
                "result body"
            ),
        )

    def test_format_list_agents_includes_resume_metadata(self) -> None:
        text = format_project_observation(
            4,
            SimpleNamespace(
                kind="list_agents",
                message="Found 1 session agent.",
                ok=True,
                agents=[
                    SimpleNamespace(
                        id="delegate-1-1",
                        status="completed",
                        mode="explore",
                        agent="reviewer",
                        background=False,
                        runs=2,
                        resumable=True,
                        task="Inspect tests",
                    )
                ],
                total=1,
                invalid=0,
                truncated=False,
            ),
        )

        self.assertEqual(
            text,
            (
                "4. list_agents: Found 1 session agent. shown=1/1 invalid=0 truncated=false\n"
                "ok: true\n"
                "agent: id=delegate-1-1 status=completed mode=explore profile=reviewer "
                "background=false runs=2 resumable=true isolation=none worktree=. branch=. "
                "worktreePreserved=false task=Inspect tests"
            ),
        )


if __name__ == "__main__":
    unittest.main()
