from __future__ import annotations

import io
import os
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.agent_view import AgentViewOutcome
from vibeagent.agent_view_render import render_agent_view
from vibeagent.agent_view_terminal import ScreenReaderAgentViewTerminal
from vibeagent.cli import main
from vibeagent.cli_agent_view import run_agent_view_from_cli
from vibeagent.cli_args import parse_args
from vibeagent.cli_interactive import run_interactive_loop
from vibeagent.cli_startup_context import resolve_interactive_startup_context
from vibeagent.cli_validation import validate_cli_args
from vibeagent.interactive_background import (
    InteractiveBackgroundRequest,
    create_interactive_background_request,
)


class TtyBuffer(io.StringIO):
    def isatty(self) -> bool:
        return True


class ScreenReaderTests(unittest.TestCase):
    def test_cli_accepts_human_text_surfaces_and_rejects_machine_output(self) -> None:
        interactive = parse_args(["--ax-screen-reader"])
        dashboard = parse_args(["agents", "--ax-screen-reader"])
        machine = parse_args(["-p", "--json", "--ax-screen-reader", "inspect"])
        local = parse_args(["--tools", "--ax-screen-reader"])

        self.assertTrue(interactive.ax_screen_reader)
        self.assertIsNone(validate_cli_args(interactive))
        self.assertIsNone(validate_cli_args(dashboard))
        self.assertEqual(validate_cli_args(machine), "--ax-screen-reader requires text output.")
        self.assertIsNone(validate_cli_args(local))

    def test_interactive_startup_and_background_handoff_preserve_mode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-screen-reader-") as base:
            root = Path(base)
            context = resolve_interactive_startup_context(
                parse_args(["--ax-screen-reader"]),
                root,
            )
            request = create_interactive_background_request(
                root,
                "run-1",
                None,
                approval_policy="ask",
                model=None,
                agent=None,
                dynamic_agent_profiles=(),
                effort=None,
                autocompact_tokens=None,
                system_prompt=None,
                append_system_prompt=None,
                additional_directories=(),
                ax_screen_reader=True,
            )

        self.assertTrue(context.ax_screen_reader)
        self.assertIn("--ax-screen-reader", request.argv)

    def test_agent_view_uses_flat_terminal_and_rendering(self) -> None:
        stream = TtyBuffer()
        terminal = ScreenReaderAgentViewTerminal()
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("sys.stdout", stream),
            patch("builtins.input", side_effect=["next", "always", "respawn"]),
        ):
            with terminal:
                terminal.draw(["VibeAgent Agent View", "No agents"])
                commands = [terminal.read_key(0.5) for _ in range(3)]

        rendered = render_agent_view(
            Path("/project"),
            (),
            selected_id=None,
            pending_counts={},
            screen_reader=True,
        )
        text = "\n".join(rendered)
        self.assertEqual(commands, ["down", "A", "R"])
        self.assertNotIn("\x1b", stream.getvalue())
        self.assertIn("Agent view update", stream.getvalue())
        self.assertIn("Commands: next, previous", text)
        self.assertIn("Type refresh", text)
        self.assertNotIn("-" * 20, rendered)

    def test_dashboard_forwards_screen_reader_mode(self) -> None:
        args = parse_args(["agents", "--ax-screen-reader"])
        with (
            patch(
                "vibeagent.cli_agent_view.run_agent_view",
                return_value=AgentViewOutcome(attach_id="0123456789ab"),
            ) as dashboard,
            patch(
                "vibeagent.cli_agent_view.attach_background_agent_from_cli",
                return_value=0,
            ) as attach,
        ):
            result = run_agent_view_from_cli(
                args,
                run_interactive_func=lambda _value: 0,
            )

        self.assertEqual(result, 0)
        self.assertTrue(dashboard.call_args.kwargs["screen_reader"])
        self.assertTrue(attach.call_args.args[0].ax_screen_reader)

        with patch("vibeagent.cli.run_agent_view_from_cli", return_value=0) as route:
            self.assertEqual(main(["agents", "--ax-screen-reader"]), 0)
        self.assertTrue(route.call_args.args[0].ax_screen_reader)

    def test_interactive_background_command_propagates_screen_reader_mode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-screen-reader-") as base:
            previous = Path.cwd()
            try:
                os.chdir(base)
                with (
                    patch("builtins.input", return_value="/bg continue"),
                    patch(
                        "vibeagent.cli_interactive.prompt_project_permission_trust",
                        return_value=False,
                    ),
                    redirect_stdout(io.StringIO()),
                    self.assertRaises(InteractiveBackgroundRequest) as raised,
                ):
                    run_interactive_loop(
                        command_namespace={},
                        initial_resume_run_id="run-1",
                        initial_ax_screen_reader=True,
                    )
            finally:
                os.chdir(previous)

        self.assertIn("--ax-screen-reader", raised.exception.argv)


if __name__ == "__main__":
    unittest.main()
