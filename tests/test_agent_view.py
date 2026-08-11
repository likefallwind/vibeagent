from __future__ import annotations

import argparse
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from vibeagent.agent_view import (
    AgentViewOutcome,
    ProjectAgentViewBackend,
    run_agent_view,
)
from vibeagent.agent_view_render import render_agent_view
from vibeagent.agent_view_terminal import StandardAgentViewTerminal
from vibeagent.background_agent_types import BackgroundAgentRecord, BackgroundAgentView
from vibeagent.cli import main
from vibeagent.cli_agent_view import run_agent_view_from_cli
from vibeagent.cli_args import has_local_flag, parse_args


def _view(
    root: Path,
    agent_id: str,
    *,
    status: str,
    task: str,
) -> BackgroundAgentView:
    logs = root / ".vibeagent" / "background-agents" / "logs"
    return BackgroundAgentView(
        record=BackgroundAgentRecord(
            id=agent_id,
            project_root=root,
            invocation_root=root,
            pid=1234,
            start_ticks=77,
            started_at=f"2026-08-11T00:00:0{agent_id[-1]}+00:00",
            task_summary=task,
            session_name=f"background-{agent_id}",
            stdout_path=logs / f"{agent_id}.stdout.log",
            stderr_path=logs / f"{agent_id}.stderr.log",
            exit_code_path=logs / f"{agent_id}.exitcode",
            stopped_path=logs / f"{agent_id}.stopped",
        ),
        status=status,
        exit_code=0 if status == "completed" else None,
    )


class FakeTerminal:
    def __init__(self, keys: list[str | None], prompts: list[str | None] | None = None) -> None:
        self.keys = list(keys)
        self.prompts = list(prompts or [])
        self.frames: list[list[str]] = []
        self.prompt_labels: list[str] = []
        self.entered = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, *_args: object) -> None:
        self.entered = False

    def size(self) -> tuple[int, int]:
        return 100, 28

    def draw(self, lines: list[str]) -> None:
        self.frames.append(lines)

    def read_key(self, _timeout: float) -> str | None:
        return self.keys.pop(0)

    def prompt(self, label: str) -> str | None:
        self.prompt_labels.append(label)
        return self.prompts.pop(0)


class FakeBackend:
    def __init__(self, views: list[BackgroundAgentView]) -> None:
        self.views = views
        self.calls: list[tuple[str, ...]] = []

    def list(self) -> tuple[BackgroundAgentView, ...]:
        return tuple(self.views)

    def pending(self, agent_id: str) -> int:
        return 1 if agent_id == self.views[0].record.id else 0

    def logs(self, agent_id: str) -> tuple[str, str]:
        self.calls.append(("logs", agent_id))
        return "running focused tests\nall passed\n", ""

    def dispatch(self, task: str) -> BackgroundAgentView:
        self.calls.append(("dispatch", task))
        created = _view(
            self.views[0].record.project_root,
            "cccccccccccc",
            status="running",
            task=task,
        )
        self.views.insert(0, created)
        return created

    def reply(self, agent_id: str, message: str) -> str:
        self.calls.append(("reply", agent_id, message))
        return "reply queued"

    def stop(self, agent_id: str) -> str:
        self.calls.append(("stop", agent_id))
        return "stopped"

    def respawn(self, agent_id: str) -> str:
        self.calls.append(("respawn", agent_id))
        return "respawned"

    def remove(self, agent_id: str) -> str:
        self.calls.append(("remove", agent_id))
        self.views = [view for view in self.views if view.record.id != agent_id]
        return "removed"


class AgentViewTests(unittest.TestCase):
    def test_renderer_groups_statuses_and_shows_bounded_peek(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-view-") as base:
            root = Path(base).resolve()
            running = _view(root, "aaaaaaaaaaaa", status="running", task="run tests")
            completed = _view(root, "bbbbbbbbbbbb", status="completed", task="review diff")

            lines = render_agent_view(
                root,
                (completed, running),
                selected_id=running.record.id,
                pending_counts={running.record.id: 2},
                peek_stdout="one\ntwo\nthree\n",
                width=72,
                height=20,
            )

        text = "\n".join(lines)
        self.assertIn("Working (1)", text)
        self.assertIn("Completed (1)", text)
        self.assertIn("> running", text)
        self.assertIn("pending=2", text)
        self.assertIn("Recent output", text)
        self.assertLessEqual(len(lines), 20)
        self.assertTrue(all(len(line) <= 72 for line in lines))

        compact = render_agent_view(
            root,
            (running,),
            selected_id=running.record.id,
            pending_counts={},
            peek_stdout="output",
            width=20,
            height=6,
        )
        self.assertEqual(len(compact), 6)
        self.assertIn("q quit", compact[-2])

    def test_controller_drives_peek_reply_respawn_stop_and_remove(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-view-") as base:
            root = Path(base).resolve()
            first = _view(root, "aaaaaaaaaaaa", status="running", task="run tests")
            second = _view(root, "bbbbbbbbbbbb", status="completed", task="review diff")
            backend = FakeBackend([first, second])
            terminal = FakeTerminal(
                ["down", "space", "m", "R", "s", "x", "q"],
                ["check the final diff", "y"],
            )

            outcome = run_agent_view(root, backend=backend, terminal=terminal)

        self.assertIsNone(outcome.attach_id)
        self.assertIn(("logs", second.record.id), backend.calls)
        self.assertIn(("reply", second.record.id, "check the final diff"), backend.calls)
        self.assertIn(("respawn", second.record.id), backend.calls)
        self.assertIn(("stop", second.record.id), backend.calls)
        self.assertIn(("remove", second.record.id), backend.calls)
        self.assertTrue(any("reply queued" in "\n".join(frame) for frame in terminal.frames))

    def test_controller_dispatches_and_returns_selected_attach(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-view-") as base:
            root = Path(base).resolve()
            backend = FakeBackend(
                [_view(root, "aaaaaaaaaaaa", status="completed", task="old")]
            )
            terminal = FakeTerminal(["n", "enter"], ["implement the parser"])

            outcome = run_agent_view(root, backend=backend, terminal=terminal)

        self.assertEqual(outcome.attach_id, "cccccccccccc")
        self.assertIn(("dispatch", "implement the parser"), backend.calls)

    def test_project_backend_dispatch_separates_task_from_cli_options(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-view-") as base:
            root = Path(base).resolve()
            backend = ProjectAgentViewBackend(root, root)
            launched = _view(root, "aaaaaaaaaaaa", status="running", task="task")
            with patch(
                "vibeagent.agent_view.launch_background_agent",
                return_value=launched,
            ) as launch:
                result = backend.dispatch("--model should remain task text")

        self.assertEqual(result, launched)
        self.assertEqual(
            launch.call_args.args[2],
            ["--background", "--", "--model should remain task text"],
        )

    def test_agents_command_routes_to_dashboard_without_becoming_a_task(self) -> None:
        args = parse_args(["agents", "--cwd", "."])
        self.assertTrue(args.agent_view)
        self.assertFalse(has_local_flag(args))
        self.assertEqual(args.task, [])

        with patch("vibeagent.cli.run_agent_view_from_cli", return_value=0) as dashboard:
            exit_code = main(["agents"])

        self.assertEqual(exit_code, 0)
        dashboard.assert_called_once()

    def test_cli_dashboard_result_switches_to_attach(self) -> None:
        args = parse_args(["agents", "--cwd", "."])
        interactive = Mock(return_value=0)
        with (
            patch(
                "vibeagent.cli_agent_view.run_agent_view",
                return_value=AgentViewOutcome(attach_id="0123456789ab"),
            ),
            patch(
                "vibeagent.cli_agent_view.attach_background_agent_from_cli",
                return_value=0,
            ) as attach,
        ):
            exit_code = run_agent_view_from_cli(
                args,
                run_interactive_func=interactive,
            )

        self.assertEqual(exit_code, 0)
        attached_args = attach.call_args.args[0]
        self.assertFalse(attached_args.agent_view)
        self.assertEqual(attached_args.attach_background_agent, "0123456789ab")

    def test_standard_terminal_requires_tty(self) -> None:
        with (
            patch("sys.stdin.isatty", return_value=False),
            patch("sys.stdout.isatty", return_value=False),
            self.assertRaisesRegex(ValueError, "interactive terminal"),
        ):
            StandardAgentViewTerminal().__enter__()

    def test_agent_view_rejects_task_and_machine_output(self) -> None:
        with patch("builtins.print"):
            task_exit = main(["--agent-view", "task"])
            json_exit = main(["agents", "--json"])
        self.assertEqual(task_exit, 2)
        self.assertEqual(json_exit, 2)


if __name__ == "__main__":
    unittest.main()
